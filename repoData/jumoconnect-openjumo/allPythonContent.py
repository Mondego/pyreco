__FILENAME__ = admin
from action.models import Action
from django.contrib import admin
from django.forms import ModelForm
from org.models import Org
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.db.models.fields.related import ManyToOneRel

class AdminActionForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(AdminActionForm, self).__init__(*args, **kwargs)
        try:
            entity_model = self.instance.content_type.model_class()
        except:
            entity_model = Org
        self.fields['entity_id'].widget = ForeignKeyRawIdWidget(rel=ManyToOneRel(entity_model, 'id'))


class ActionAdmin(admin.ModelAdmin):
    list_display = ('title', 'link', 'content_type', 'entity', 'rank')

#admin.site.register(Action, ActionAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

ACTION_TYPES = (
    ('link', 'Link'),
)

class Action(models.Model):
    id = models.AutoField(db_column='action_id', primary_key=True)
    title = models.CharField(max_length=255)
    link = models.URLField(verify_exists=False, blank=True)
    rank = models.PositiveIntegerField()
    type = models.CharField(max_length=25, choices=ACTION_TYPES, default=ACTION_TYPES[0][0])

    content_type = models.ForeignKey(ContentType, limit_choices_to={"model__in": ("Org", "Issue")},
                                    default=ContentType.objects.get(model='issue').id)
    object_id = models.PositiveIntegerField()
    entity = generic.GenericForeignKey()

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'actions'
        ordering = ('rank',)

    def __unicode__(self):
        return self.title

########NEW FILE########
__FILENAME__ = models
from unittest import TestCase

class ActionModelTests(TestCase):
    pass

########NEW FILE########
__FILENAME__ = views
from django.db.models import get_model
from etc.view_helpers import json_response, render_string

def action_list(request, entity_id, model_name):
    model = get_model(*model_name.split('.'))
    entity = model.objects.get(id=entity_id)
    actions = entity.actions.all()
    html = render_string(request, 'action/includes/action_list.html', {
        'entity': entity,
        'actions': actions,
    })

    return json_response({'html': html})

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from data.models import Test

########NEW FILE########
__FILENAME__ = api_v1
from django.conf.urls.defaults import patterns
from django.conf import settings
from issue.models import Issue
from org.models import Org
from tastypie import fields
from tastypie.api import Api
from tastypie.authentication import ApiKeyAuthentication
from tastypie.authorization import DjangoAuthorization
from tastypie.resources import ModelResource
from tastypie.throttle import CacheDBThrottle
from users.models import User

class JumoModelResource(ModelResource):
    class Meta:
        authentication = ApiKeyAuthentication()
        throttle = CacheDBThrottle(throttle_at=3600, timeframe=3600)


class IssueResource(JumoModelResource):
    follower_count = fields.IntegerField('get_num_followers')
    img_thumb_url = fields.CharField('get_image')
    img_url = fields.CharField('get_image_large')
    parent_issue_id = fields.IntegerField('parent_issue_id')
    parent_issue_uri = fields.ForeignKey('self', 'parent_issue')
    stats = fields.ListField('get_all_statistics')
    url = fields.CharField('get_url')

    class Meta(JumoModelResource.Meta):
        queryset = Issue.objects.filter(is_active=True)

        allowed_methods = ['get']
        fields = ['date_created', 'date_updated', 'description', 'follower_count', 'handle', 'id', 'img_url',
                  'img_thumb_url', 'name', 'orgs', 'parent_issue_id', 'parent_issue_uri', 'stats', 'url']
        resource_name = 'issue'


class OrgResource(ModelResource):
    accomplishments = fields.ListField('get_accomplishments')
    follower_count = fields.IntegerField('get_num_followers')
    img_thumb_url = fields.CharField('get_image')
    img_url = fields.CharField('get_image_large')
    issues = fields.ToManyField(IssueResource, 'issues')
    location = fields.CharField('location', default='')
    methods = fields.ListField('get_all_methods')
    org_url = fields.CharField('url')
    related_orgs = fields.ToManyField('self', 'related_orgs')
    social_mission = fields.CharField('social_mission', default='')
    url = fields.CharField('get_url')
    working_locations = fields.ListField('get_working_locations')

    class Meta(JumoModelResource.Meta):
        queryset = Org.objects.filter(is_active=True)

        allowed_methods = ['get']
        fields = ['accomplishments', 'blog_url', 'date_created', 'date_updated', 'donation_enabled',
                  'ein', 'facebook_id', 'follower_count', 'handle', 'id', 'img_thumb_url', 'img_url',
                  'issues', 'location', 'methods', 'mission_statement', 'name', 'org_url', 'recommended',
                  'revenue', 'size', 'social_mission', 'twitter_id', 'url', 'vision_statement',
                  'working_locations', 'year_founded', 'youtube_id']
        resource_name = 'org'


class UserResource(ModelResource):
    badges = fields.ListField('get_badges')
    img_thumb_url = fields.CharField('get_image')
    img_url = fields.CharField('get_image_large')
    location = fields.CharField('location', default='')
    followed_issues = fields.ToManyField(IssueResource, 'usertoissuefollow_set')
    followed_orgs = fields.ToManyField(OrgResource, 'usertoorgfollow_set')
    followed_users = fields.ToManyField('self', 'followers')
    following_users = fields.ToManyField('self', 'following_user')
    user_url = fields.CharField('url')
    url = fields.CharField('get_url')

    class Meta(JumoModelResource.Meta):
        queryset = User.objects.filter(is_active=True)

        allowed_methods = ['get']
        fields = ['badges', 'bio', 'first_name', 'facebook_id', 'followed_issues', 'followed_orgs',
                  'followed_users', 'following_users', 'id', 'img_url', 'img_thumb_url',
                  'last_name', 'location', 'twitter_id', 'user_url', 'url', 'username', 'youtube_id']
        resource_name = 'user'



def api_urls():
    api = Api(api_name=settings.API_VERSION)
    api.register(IssueResource())
    api.register(OrgResource())
    api.register(UserResource())
    return api.urls

########NEW FILE########
__FILENAME__ = forms
from django import forms
from commitment.models import Commitment

class CommitmentForm(forms.ModelForm):
    class Meta:
        model = Commitment
        fields = ['content_type', 'object_id']
        widgets = {
            'content_type': forms.HiddenInput(),
            'object_id': forms.HiddenInput(),
        }

########NEW FILE########
__FILENAME__ = models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.db import models
from users.models import User
from etc.gfk_manager import GFKQuerySet
from utils.query_set import QuerySet
from etc import cache

class CommitmentQuerySet(QuerySet, GFKQuerySet):
    def active(self):
        return self.filter(user__is_active=True)

    def with_orgs(self):
        org_type = ContentType.objects.get(app_label='org', model='org')
        return self.filter(content_type=org_type)

    def with_issues(self):
        issue_type = ContentType.objects.get(app_label='issue', model='issue')
        return self.filter(content_type=issue_type)

class Commitment(models.Model):
    PENDING = 'pending'
    COMPLETED = 'completed'
    STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (COMPLETED, 'Completed'),
    )

    id = models.AutoField(db_column='commitment_id', primary_key=True)
    user = models.ForeignKey(User, related_name='commitments')
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    entity = generic.GenericForeignKey()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    goal_date = models.DateTimeField(blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    objects = CommitmentQuerySet.as_manager()

    class Meta:
        db_table = 'commitments'
        unique_together = ('user', 'content_type', 'object_id')

    def save(self, *args, **kwargs):
        super(Commitment, self).save(*args, **kwargs)
        cache.bust(self)

    def delete(self, *args, **kwargs):
        super(Commitment, self).delete(*args, **kwargs)
        cache.bust(self)

########NEW FILE########
__FILENAME__ = commitment_tags
from django import template
from django.template.loader import render_to_string
from commitment.models import Commitment
from commitment.forms import CommitmentForm
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from etc.view_helpers import url_with_qs
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()

@register.inclusion_tag('commitment/includes/commitment_button.html', takes_context=True)
def commitment_button(context, entity, with_popup = 1): # using 1 & 0 as bool for the templates
    user = context['user']

    d = {'button_type': 'login',
         'with_popup': with_popup,
         'button_text': ('Help Out') # %s' % entity._meta.verbose_name),
         }
    if user.is_authenticated():
        try:
            entity_type = ContentType.objects.get_for_model(entity)
            d['commitment'] = Commitment.objects.get(content_type=entity_type, object_id=entity.id, user=user)
            d['button_type'] = 'delete'
            d['button_text'] = "view actions" #"you're committed"
            url_name = "%s_action_list" % entity._meta.object_name.lower()
            d['data_url'] = reverse(url_name, args=[entity.id])
        except Commitment.DoesNotExist:
            commitment = Commitment(entity=entity)
            d['form'] = CommitmentForm(instance=commitment)
            d['button_type'] = 'create'
        except Commitment.MultipleObjectsReturned:
            d['commitment'] = Commitment.objects.filter(content_type=entity_type, object_id=entity.id, user=user)[0]
            d['button_type'] = 'delete'
            d['button_text'] = "view actions" #"you're committed"
            url_name = "%s_action_list" % entity._meta.object_name.lower()
            d['data_url'] = reverse(url_name, args=[entity.id])
    return d

@register.simple_tag
def link_to_commitments(entity):
    url_name = "%s_commitments" % str.lower(entity.__class__.__name__)
    url = reverse(url_name, kwargs={'entity_id': entity.id})
    return '<a id="committed_users" data-title="People Committed to %s" data-url="%s">%s</a>' % (entity.get_name, url, intcomma(entity.get_num_followers))

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = views
from etc.decorators import PostOnly, AccountRequired
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect, get_object_or_404
from commitment.models import Commitment
from etc.view_helpers import json_error, json_response, render_inclusiontag, render_string
from django.core.exceptions import ValidationError
from django.db.models import get_model

@AccountRequired
@PostOnly
def create(request):
    entity_id = request.POST['object_id']
    entity_type = request.POST['content_type']
    content_type = ContentType.objects.get(id=entity_type)
    entity = content_type.get_object_for_this_type(id=entity_id)
    commitment = Commitment(entity=entity, user=request.user)

    response = redirect(entity)
    try:
        commitment.full_clean()
        commitment.save()
        if request.is_ajax():
            button = render_inclusiontag(request, "commitment_button entity", "commitment_tags",
                                         {'entity': entity})
            actions = render_string(request, "action/includes/action_list.html", {
                'entity': entity,
                'actions': entity.actions.all(),
            })
            response = json_response({'button': button, 'actions': actions})
    except ValidationError:
        if request.is_ajax():
            response = json_error(400, "You have already committed to this issue/org.")
    return response

@AccountRequired
@PostOnly
def delete(request, commitment_id):
    commitment = get_object_or_404(Commitment, user=request.user, id=commitment_id)
    commitment.delete()

    response = redirect(commitment.entity)
    if request.is_ajax():
        button = render_inclusiontag(request, "commitment_button entity", "commitment_tags",
                                     {'entity': commitment.entity})
        response = json_response({'button': button})
    return response

def list(request, entity_id, model_name):
    start = int(request.GET.get('start', 0))
    end = int(request.GET.get('end', 20))
    model = get_model(*model_name.split('.'))
    entity = get_object_or_404(model, id=entity_id)
    commitments = entity.commitments.active()[start:end].select_related()

    html = render_string(request, "commitment/includes/committer_list.html", {
        'commitments': commitments,
        'start_index': start,
    })

    return json_response({
        'html': html,
        'has_more': end < entity.commitments.count(),
    })

########NEW FILE########
__FILENAME__ = forms
from django import forms

class HiddenRankModelForm(forms.ModelForm):
    class Meta:
        widgets = {
            'rank': forms.HiddenInput,
            'position': forms.HiddenInput,
        }

########NEW FILE########
__FILENAME__ = models
from django.contrib import admin
from django.contrib.contenttypes.generic import GenericInlineModelAdmin

class LinkedInline(admin.options.InlineModelAdmin):
    template = ''
    admin_model_path = None
    admin_app_label = None

    def __init__(self, *args):
        super(LinkedInline, self).__init__(*args)
        if self.admin_model_path is None:
            self.admin_model_path = self.model._meta.object_name.lower()
        if self.admin_app_label is None:
            self.admin_app_label = self.model._meta.app_label

class LinkedStackedInline(LinkedInline):
    template = 'cust_admin/edit_inline/linked_stacked_inline.html'

class LinkedTabularInline(LinkedInline):
    template = 'cust_admin/edit_inline/linked_tabular_inline.html'

class LinkedGenericInline(GenericInlineModelAdmin):
    template = ''
    admin_model_path = None
    admin_app_label = None
    def __init__(self, *args):
        super(LinkedGenericInline, self).__init__(*args)
        if self.admin_model_path is None:
            self.admin_model_path = self.model._meta.object_name.lower()
        if self.admin_app_label is None:
            self.admin_app_label = self.model._meta.app_label

class LinkedGenericStackedInline(LinkedGenericInline):
    template = 'cust_admin/edit_inline/linked_stacked_inline.html'

class LinkedGenericTabularInline(LinkedGenericInline):
    template = 'cust_admin/edit_inline/linked_tabular_inline.html'

########NEW FILE########
__FILENAME__ = ext_admin_list
import datetime

from django.conf import settings
from django.contrib.admin.util import lookup_field, display_for_field, label_for_field
from django.contrib.admin.views.main import ALL_VAR, EMPTY_CHANGELIST_VALUE
from django.contrib.admin.views.main import ORDER_VAR, ORDER_TYPE_VAR, PAGE_VAR, SEARCH_VAR
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.forms.forms import pretty_name
from django.utils import formats
from django.template.defaultfilters import escapejs
from django.utils.html import escape, conditional_escape
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.translation import ugettext as _
from django.utils.encoding import smart_unicode, force_unicode
from django.template import Library
from django.contrib.admin.templatetags.admin_list import result_headers, result_hidden_fields

register = Library()

"""
All this was copy and pasted so the custDismissRelatedLookupPopup could be inserted here.
Do a find.
"""

def ext_items_for_result(cl, result, form):
    """
    Generates the actual list of data.
    """
    first = True
    pk = cl.lookup_opts.pk.attname
    for field_name in cl.list_display:
        row_class = ''
        try:
            f, attr, value = lookup_field(field_name, result, cl.model_admin)
        except (AttributeError, ObjectDoesNotExist):
            result_repr = EMPTY_CHANGELIST_VALUE
        else:
            if f is None:
                allow_tags = getattr(attr, 'allow_tags', False)
                boolean = getattr(attr, 'boolean', False)
                if boolean:
                    allow_tags = True
                    result_repr = _boolean_icon(value)
                else:
                    result_repr = smart_unicode(value)
                # Strip HTML tags in the resulting text, except if the
                # function has an "allow_tags" attribute set to True.
                if not allow_tags:
                    result_repr = escape(result_repr)
                else:
                    result_repr = mark_safe(result_repr)
            else:
                if value is None:
                    result_repr = EMPTY_CHANGELIST_VALUE
                if isinstance(f.rel, models.ManyToOneRel):
                    result_repr = escape(getattr(result, f.name))
                else:
                    result_repr = display_for_field(value, f)
                if isinstance(f, models.DateField) or isinstance(f, models.TimeField):
                    row_class = ' class="nowrap"'
        if force_unicode(result_repr) == '':
            result_repr = mark_safe('&nbsp;')
        # If list_display_links not defined, add the link tag to the first field
        if (first and not cl.list_display_links) or field_name in cl.list_display_links:
            table_tag = {True:'th', False:'td'}[first]
            first = False
            url = cl.url_for_result(result)
            # Convert the pk to something that can be used in Javascript.
            # Problem cases are long ints (23L) and non-ASCII strings.
            if cl.to_field:
                attr = str(cl.to_field)
            else:
                attr = pk
            value = result.serializable_value(attr)
            result_id = repr(force_unicode(value))[1:]

            #All this was copy and pasted so the custDismissRelatedLookupPopup could be inserted here.
            ext_attrib = ""
            if cl.is_popup:
                if cl.is_ext_popup:
                    ext_attrib = 'onclick="opener.custDismissRelatedLookupPopup(window, %s, \'%s\'); return false;"' % (result_id, escapejs(result_repr))
                else:
                    ext_attrib = ' onclick="opener.dismissRelatedLookupPopup(window, %s); return false;"' % result_id

            yield mark_safe(u'<%s%s><a href="%s" %s>%s</a></%s>' % \
                (table_tag, row_class, url, ext_attrib, result_repr, table_tag))
        else:
            # By default the fields come from ModelAdmin.list_editable, but if we pull
            # the fields out of the form instead of list_editable custom admins
            # can provide fields on a per request basis
            if form and field_name in form.fields:
                bf = form[field_name]
                result_repr = mark_safe(force_unicode(bf.errors) + force_unicode(bf))
            else:
                result_repr = conditional_escape(result_repr)
            yield mark_safe(u'<td%s>%s</td>' % (row_class, result_repr))
    if form and not form[cl.model._meta.pk.name].is_hidden:
        yield mark_safe(u'<td>%s</td>' % force_unicode(form[cl.model._meta.pk.name]))


def ext_results(cl):
    if cl.formset:
        for res, form in zip(cl.result_list, cl.formset.forms):
            yield list(ext_items_for_result(cl, res, form))
    else:
        for res in cl.result_list:
            yield list(ext_items_for_result(cl, res, None))



def ext_result_list(cl):
    """
    Displays the headers and data list together
    """
    return {'cl': cl,
            'result_hidden_fields': list(result_hidden_fields(cl)),
            'result_headers': list(result_headers(cl)),
            'results': list(ext_results(cl))}
ext_result_list = register.inclusion_tag("admin/change_list_results.html")(ext_result_list)

########NEW FILE########
__FILENAME__ = main
from django.contrib.admin.views.main import *


IS_EXT_POPUP_VAR = 'ext_pop'
class ExtChangeList(ChangeList):
    def __init__(self, request, model, list_display, list_display_links, list_filter, date_hierarchy, search_fields, list_select_related, list_per_page, list_editable, model_admin):
        self.is_ext_popup = IS_EXT_POPUP_VAR in request.GET
        super(ExtChangeList, self).__init__(request, model, list_display, list_display_links, list_filter, date_hierarchy, search_fields, list_select_related, list_per_page, list_editable, model_admin)
        
        
    def get_query_set(self):
        qs = self.root_query_set
        lookup_params = self.params.copy() # a dictionary of the query string
        for i in (ALL_VAR, ORDER_VAR, ORDER_TYPE_VAR, SEARCH_VAR, IS_POPUP_VAR, IS_EXT_POPUP_VAR):
            if i in lookup_params:
                del lookup_params[i]
        for key, value in lookup_params.items():
            if not isinstance(key, str):
                # 'key' will be used as a keyword argument later, so Python
                # requires it to be a string.
                del lookup_params[key]
                lookup_params[smart_str(key)] = value

            # if key ends with __in, split parameter into separate values
            if key.endswith('__in'):
                lookup_params[key] = value.split(',')

            # if key ends with __isnull, special case '' and false
            if key.endswith('__isnull'):
                if value.lower() in ('', 'false'):
                    lookup_params[key] = False
                else:
                    lookup_params[key] = True

        # Apply lookup parameters from the query string.
        try:
            qs = qs.filter(**lookup_params)
        # Naked except! Because we don't have any other way of validating "params".
        # They might be invalid if the keyword arguments are incorrect, or if the
        # values are not in the correct type, so we might get FieldError, ValueError,
        # ValicationError, or ? from a custom field that raises yet something else 
        # when handed impossible data.
        except:
            raise IncorrectLookupParameters

        # Use select_related() if one of the list_display options is a field
        # with a relationship and the provided queryset doesn't already have
        # select_related defined.
        if not qs.query.select_related:
            if self.list_select_related:
                qs = qs.select_related()
            else:
                for field_name in self.list_display:
                    try:
                        f = self.lookup_opts.get_field(field_name)
                    except models.FieldDoesNotExist:
                        pass
                    else:
                        if isinstance(f.rel, models.ManyToOneRel):
                            qs = qs.select_related()
                            break

        # Set ordering.
        if self.order_field:
            qs = qs.order_by('%s%s' % ((self.order_type == 'desc' and '-' or ''), self.order_field))

        # Apply keyword searches.
        def construct_search(field_name):
            if field_name.startswith('^'):
                return "%s__istartswith" % field_name[1:]
            elif field_name.startswith('='):
                return "%s__iexact" % field_name[1:]
            elif field_name.startswith('@'):
                return "%s__search" % field_name[1:]
            else:
                return "%s__icontains" % field_name

        if self.search_fields and self.query:
            for bit in self.query.split():
                or_queries = [models.Q(**{construct_search(str(field_name)): bit}) for field_name in self.search_fields]
                qs = qs.filter(reduce(operator.or_, or_queries))
            for field_name in self.search_fields:
                if '__' in field_name:
                    qs = qs.distinct()
                    break

        return qs
########NEW FILE########
__FILENAME__ = widgets
from django import forms
from django.conf import settings
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_unicode
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.contrib.admin.widgets import AdminFileWidget
from django.utils.safestring import mark_safe

class AdminImageFieldWithThumbWidget(AdminFileWidget):
    def render(self, name, value, attrs=None):
        thumb_html = ''
        if value and hasattr(value, "url"):
            thumb_html = '<img src="%s" width="60" width="60"/>' % value.url
        return mark_safe("%s%s" % (thumb_html, super(AdminImageFieldWithThumbWidget, self).render(name, value,attrs)))


class ForeignKeyToObjWidget(forms.TextInput):
    """
    This is used to get the __unicode__ representation of an object rather than just the ID.
    It has the benefit of doing a few things you expect like showing the changed object rather
    than just the changed ID when you change the related field before saving.
    """
    input_type = 'hidden'
    is_hidden = True

    def render_mini_model_inline(self, obj, name, change_url):
        return "<a id='name_id_%s' href='%s'>%s</a>" % (name, change_url, smart_unicode(obj))

    def __init__(self, rel, attrs=None, using=None):
        self.rel = rel
        self.db = using
        super(ForeignKeyToObjWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None):
        #Generate date for the lookup link
        if attrs is None:
            attrs = {}
        related_url = '../../../%s/%s/' % (self.rel.to._meta.app_label, self.rel.to._meta.object_name.lower())
        params = self.url_parameters()
        if params:
            url = '?' + '&amp;'.join(['%s=%s' % (k, v) for k, v in params.items()])
        else:
            url = ''
        if not attrs.has_key('class'):
            attrs['class'] = 'vForeignKeyRawIdAdminField' # The JavaScript looks for this hook.

        #Generate Link and Object for the render name.
        key = self.rel.get_related_field().name
        rendered_obj = "<a id='name_id_%s'><i>Nothing Selected</i></a>" % name
        try:
            obj = self.rel.to._default_manager.using(self.db).get(**{key: value})
            change_url = reverse(
                "admin:%s_%s_change" % (obj._meta.app_label, obj._meta.object_name.lower()),
                args=(obj.pk,)
            )
            rendered_obj = self.render_mini_model_inline(obj, name, change_url)
        except (ValueError, self.rel.to.DoesNotExist):
            pass

        output = [super(ForeignKeyToObjWidget, self).render(name, value, attrs)]
        output.append(rendered_obj)
        output.append('<a href="%s%s" class="related-lookup" id="lookup_id_%s" onclick="return custShowRelatedObjectLookupPopup(this);"> ' % (related_url, url, name))
        output.append('<img src="%simg/admin/selector-search.gif" width="16" height="16" alt="%s" /></a>' % (settings.ADMIN_MEDIA_PREFIX, _('Lookup')))
        return mark_safe(u''.join(output))

    def base_url_parameters(self):
        params = {}
        if self.rel.limit_choices_to and hasattr(self.rel.limit_choices_to, 'items'):
            items = []
            for k, v in self.rel.limit_choices_to.items():
                if isinstance(v, list):
                    v = ','.join([str(x) for x in v])
                else:
                    v = str(v)
                items.append((k, v))
            params.update(dict(items))
        return params

    def url_parameters(self):
        from django.contrib.admin.views.main import TO_FIELD_VAR
        params = self.base_url_parameters()
        params.update({TO_FIELD_VAR: self.rel.get_related_field().name})
        return params

########NEW FILE########
__FILENAME__ = export_fixtures_for_new_issues
#!/usr/bin/env python
# django environment setup

import sys,os
sys.path.append(os.path.realpath(os.sep.join([os.path.dirname(__file__), os.pardir])))

from django.core.management import setup_environ
from django.core import serializers
import settings
setup_environ(settings)

from django.contrib.contenttypes.models import ContentType
from discovery.models import TopCategory, SubCategory, DiscoveryItem
from org.models import Org
from issue.models import Issue


def output(obj,name):
    file = open('data/fixtures/%s.json' % name, 'w')
    file.write(serializers.serialize('json',objs,indent=1))
    file.close()

if __name__ == '__main__':
    issues = [{'name' : 'MALARIA_ISSUE', 'obj' : Issue.objects.get(name='Malaria')}]
    orgs = [{'name' : 'FREEDOM_ORG', 'obj' : Org.objects.get(name='Freedom to Marry')}, {'name' : 'HRW_ORG', 'obj' : Org.objects.get(name='Human Rights Watch')}]


    for iss in issues:
        i = iss['obj']
        content = [m for m in i.get_all_content]
        objs = [i] + [m for m in i.get_all_actions] + [m for m in i.get_all_advocates] + [m for m in i.get_all_media_items] + [m for m in i.get_all_timeline_items] + content + [m.get_media_item for m in content if m.get_media_item != None]
        output(objs,iss['name'])

    for org in orgs:
        i = org['obj']
        content = [m for m in i.get_all_content]
        objs = [i] + [m for m in i.get_all_actions] + [m for m in i.get_all_media_items] + [m for m in i.get_all_timeline_items] + content + [m.get_media_item for m in content if m.get_media_item != None]
        output(objs,org['name'])





########NEW FILE########
__FILENAME__ = gen_donation_data
#!/usr/bin/env python
# django environment setup

import sys,os
sys.path.append(os.path.realpath(os.sep.join([os.path.dirname(__file__), os.pardir])))

from django.core.management import setup_environ
import settings
setup_environ(settings)

# Have to do this cache._populate bit or get_model calls will try to do an import
# and cause circular import hell
from django.db.models.loading import cache
cache._populate()

import codecs
from django.core import serializers
from django.contrib.auth.models import User as AuthUser

from issue.models import Issue
from users.models import User
from org.models import Org
from users.models import Location
from donation.models import *
from message.models import Publication, Subscription, Message


donations = list(Donation.objects.all()[:5])


payments = Payment.objects.filter(donation__in=donations)

donors = Donor.objects.filter(donations__in=donations)
users = User.objects.filter(id__in = [d.user.id for d in donors if d])
beneficiaries = DonationBeneficiary.objects.filter(donation__in=donations)
donor_addresses = DonorAddress.objects.filter(donor__in=donors)
donor_phones = DonorPhone.objects.filter(donor__in=donors)
credit_cards = CreditCard.objects.filter(donor__in=donors)

attempting_donation = donations[0]
attempting_donation.charge_status = Donation.ChargeStatus.ATTEMPTING_PAYMENT
attempting_donation.id = 1
dontattempt_donation = donations[1]
dontattempt_donation.charge_status = Donation.ChargeStatus.DO_NOT_ATTEMPT
dontattempt_donation.id = 2
complete_donation = donations[2]
complete_donation.charge_status = Donation.ChargeStatus.PAYMENT_COMPLETE
complete_donation.id = 3
paid_donation = donations[3]
paid_donation.payment_status = Donation.PaymentStatus.PAID
paid_donation.id = 4
permafail_donation = donations[4]
permafail_donation.payment_status = Donation.PaymentStatus.PERMAFAILED
permafail_donation.id = 5



dons = [attempting_donation, dontattempt_donation, complete_donation, paid_donation, permafail_donation]

fixtures = list(dons) + list(users) + list(donors) + list(beneficiaries) + list(donor_addresses) + list(donor_phones) + list(credit_cards)

data = serializers.serialize('json', fixtures, indent=4)
data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures/donation_test_data.json")
fh = codecs.open(data_file, 'w', encoding='UTF-8')
fh.write(data)
fh.close()
print "Data written to %s" % data_file

########NEW FILE########
__FILENAME__ = load_discovery_data
#!/usr/bin/env python
# django environment setup
import sys,os
sys.path.append(os.path.realpath(os.sep.join([os.path.dirname(__file__), os.pardir])))

from django.core.management import setup_environ
import settings
setup_environ(settings)

from django.contrib.contenttypes.models import ContentType
from discovery.models import TopCategory, SubCategory, DiscoveryItem
from org.models import Org

ISSUE_TYPE = ContentType.objects.get(app_label='issue', model='issue')
ORG_TYPE = ContentType.objects.get(app_label='org', model='org')
ORGS = Org.objects.all()[:30]

CATEGORIES = [
    ("Arts & Culture", ["Artist Support", "Performing Arts", "Film", "Museums",]),
    ("Education", ["After School Programs", "Girls Education", "Charter Schools", "Teacher Training",]),
    ("Health", ["Early Childhood Health", "Malaria", "Mental Health", "Mobile Clinics",]),
    ("Human Rights", ["Child Slavery", "Legal Assistance", "Reproductive Rights", "Refugees' Rights",]),
    ("Peace & Governance", ["Democracy", "Citizen Participation", "Government Accountability", "Public Media",]),
    ("Poverty", ["Poverty Alleviation", "Microfinance", "Housing", "Small Business Support",]),
]

def load_discovery_data():
    for tc_rank, (tc_name, sub_categories) in enumerate(CATEGORIES):
        tc = TopCategory(name=tc_name, rank=tc_rank)
        tc.save()
        for sc_rank, sc_name in enumerate(sub_categories):
            sc = SubCategory(name=sc_name, parent=tc, rank=sc_rank)
            sc.save()
            for di_rank in range(4):
                di = DiscoveryItem(entity=ORGS[4*sc_rank+di_rank], parent=sc, rank=di_rank)
                di.save()

if __name__ == '__main__':
    load_discovery_data()

########NEW FILE########
__FILENAME__ = methods
from django.utils.encoding import smart_str
from django.core.cache import cache
from django.db.models.base import ModelBase
from django.db import transaction

def _cache_key(cls, id):
  if type(cls) == ModelBase:
    prefix = cls.__name__
  else:
    prefix = cls.__class__.__name__
  return '%s%s' % (prefix, id)

def _get(cls, id):
  if type(cls) == ModelBase:
    if type(id) == list:
      return cls().objects.get(id__in = [str(l) for l in id])
    else:
      return cls().objects.get(id = str(id))
  else:
    if type(id) == list:
      return cls.__class__.base__().objects.get(id__in = [str(l) for l in id])
    else:
      return cls.__class__.base__().objects.get(id = str(id))

def get(cls, id):
  if getattr(cls, '_cacheable', False):
    c = cache.get(cache_key(cls, str(id)))
    if c is not None:
      return c
  return _get(cls, id)

def multiget(cls, ids):
  if len(ids) == 1:
    return [get(ids[0])]
  if getattr(cls, '_cacheable', False):


  else:
    return _get(cls, ids)

@transaction.autocommit
def update(model):
  model.save()
  if model._cacheable:
    cache.set(cache_key(model, model.id), model)
  return model


########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django.contrib.contenttypes.generic import GenericTabularInline
from discovery.models import TopCategory, SubCategory, DiscoveryItem
from cust_admin.models import LinkedTabularInline
from cust_admin.forms import HiddenRankModelForm

class SubCategoryInline(LinkedTabularInline):
    model = SubCategory
    form = HiddenRankModelForm
    show_edit_link = True
    extra = 0
    sortable_field_name = "rank"
    fields = ('name', 'discovery_item_count', 'rank',)
    readonly_fields = ('discovery_item_count',)

class DiscoveryItemInline(admin.TabularInline):
    model = DiscoveryItem
    form = HiddenRankModelForm
    extra = 0
    sortable_field_name = "rank"

    related_lookup_fields = {
        'generic': [['content_type', 'object_id']],
    }

class TopCategoryAdmin(admin.ModelAdmin):
    inlines = [SubCategoryInline]
    list_display = ('name', 'rank', 'sub_category_count',)
    list_editable = ('rank',)
    ordering = ('rank',)

class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('parent', 'name', 'rank', 'discovery_item_count')
    list_display_links = ('name',)
    inlines = [DiscoveryItemInline]

    def get_changelist(self, request):
        from django.contrib.admin.views.main import ChangeList
        class MultipleOrderingChangelist(ChangeList):
            def get_query_set(self):
                qs = super(MultipleOrderingChangelist, self).get_query_set()
                return qs.order_by('parent', 'rank')
        return MultipleOrderingChangelist

admin.site.register(TopCategory, TopCategoryAdmin)
admin.site.register(SubCategory, SubCategoryAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from etc.gfk_manager import GFKManager

class TopCategory(models.Model):
    id = models.AutoField(db_column='top_category_id', primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    rank = models.PositiveIntegerField()

    class Meta:
        db_table = 'top_categories'
        verbose_name_plural = 'top categories'

    def __unicode__(self):
        return self.name

    def sub_category_count(self):
        return self.subcategory_set.count()

class SubCategory(models.Model):
    id = models.AutoField(db_column='sub_category_id', primary_key=True)
    name = models.CharField(max_length=50, blank=True)
    parent = models.ForeignKey(TopCategory, db_column='top_category_id')
    rank = models.PositiveIntegerField()

    class Meta:
        db_table = 'sub_categories'
        verbose_name_plural = 'sub categories'
        ordering = ['rank']

    def discovery_item_count(self):
        return self.discoveryitem_set.count()
    discovery_item_count.__name__ = 'Item Count'

class DiscoveryItem(models.Model):
    CONTENT_TYPE_CHOICES = (
        ContentType.objects.get(app_label='org', model='org').id,
        ContentType.objects.get(app_label='issue', model='issue').id,
    )

    id = models.AutoField(db_column='discovery_item_id', primary_key=True)
    parent = models.ForeignKey(SubCategory, db_column='sub_category_id')
    content_type = models.ForeignKey(ContentType, limit_choices_to={'id__in': CONTENT_TYPE_CHOICES},
                                     default=CONTENT_TYPE_CHOICES[0], related_name='content_type')
    object_id = models.PositiveIntegerField()
    entity = generic.GenericForeignKey()
    rank = models.PositiveIntegerField()

    objects = GFKManager()

    class Meta:
        db_table = 'discovery_items'
        ordering = ['rank']

class DiscoveryMap(object):
    @classmethod
    def get_map(cls):
        map = {}

        ''' Assumes all top categories and sub categories that we want displayed
            will have discovery items '''
        items = DiscoveryItem.objects.all().order_by('rank').select_related().fetch_generic_relations()
        for item in items:
            sub_category = item.parent
            top_category = sub_category.parent
            map.setdefault(top_category, {}).setdefault(sub_category, []).append(item)
        return map

    @classmethod
    def get_lists(cls):
        discovery_map = cls.get_map()
        top_categories = sorted(discovery_map.keys(), key=lambda tc: tc.rank)
        sub_category_groups = []
        discovery_item_groups = []
        for top_category, sub_category_map in discovery_map.iteritems():
            sorted_sub_cats = sorted(sub_category_map.keys(), key=lambda sc: sc.rank)
            sub_category_groups.append((sorted_sub_cats, top_category))
            for sub_category, discovery_items in sub_category_map.iteritems():
                discovery_item_groups.append((discovery_items, top_category, sub_category))

        # Sort sub category groups by ranking of parent
        sub_category_groups = sorted(sub_category_groups, key=lambda group: group[1].rank)
        # Sort discovery item groups by ranking of top_category first, and then sub_category
        discovery_item_groups = sorted(discovery_item_groups, key=lambda group: 10*group[1].rank+group[2].rank)

        return top_categories, sub_category_groups, discovery_item_groups

########NEW FILE########
__FILENAME__ = discovery_tags
from django import template

register = template.Library()

@register.simple_tag
def temp(adminform):
    print adminform.model_admin.opts
    return 'hello'

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = collectionsd
'''
Created on Apr 12, 2011

@author: al
'''

import sys, os
sys.path.append(os.path.realpath(os.sep.join([os.path.dirname(__file__), os.pardir])))

from django.core.management import setup_environ
import settings
setup_environ(settings)

from util.base_daemon import *
from donation.models import Donation
from donation.tasks import process_donation

class CollectionsDaemon(BaseDaemon):
    process_name = 'collectionsd'
    sleep_interval = 60*60 # 1 hour

    def run_iteration(self):
        donations_to_retry = Donation.get_retryable_donations()
        for donation in donations_to_retry:
            process_donation.delay(donation.id)
        return self.sleep_interval


if __name__ == '__main__':
    CollectionsDaemon.start(settings)
########NEW FILE########
__FILENAME__ = forms
from django.contrib.localflavor.us.us_states import STATE_CHOICES
from django.core.exceptions import ValidationError
from django import forms
from django.forms.util import ErrorList
from etc.country_field import COUNTRIES
from etc.credit_card_fields import CreditCardField, ExpiryDateField, VerificationValueField
#from utils.donations import nfg_api


"""
    Unused errors.
    InvalidCardOnFile, NpoNotFound, NpoNotEligible, InvalidDonorIpAddres,
    InvalidDonationType, NoChangeRequested, CountryNotSupported, InternationalDonationsNotSupported,
    COFNotFound, COFAlreadyDeleted, COFInUse, COFNoRefCode, UserNotFound, InvalidDonorToken
"""

class BaseDonationForm(forms.Form):

    CUST_STATE_CHOICES = list(STATE_CHOICES)
    CUST_STATE_CHOICES.insert(0,('', '---------'),)

    #FIELDS
    donor_email = forms.EmailField(label="Email", required=True)
    first_name = forms.CharField(label="First Name", max_length=30, required=True)
    last_name = forms.CharField(label="Last Name", max_length=30, required=True)
    address_line_one = forms.CharField(label="Address", required=True)
    address_line_two = forms.CharField(required=False)
    city = forms.CharField(label="City", required=True)
    state = forms.CharField(label="State", required=False, widget=forms.Select(choices=CUST_STATE_CHOICES))
    zip_code = forms.CharField(required=True, label="Zip Code")
    country = forms.ChoiceField(label="Country", choices=COUNTRIES, required=True)
    phone = forms.CharField(label="Phone", max_length=50, required=True)
    donation_amount = forms.DecimalField(label="Donation", required=True, min_value=10.0, max_value=20000.0,
                                         error_messages={"min_value":"The minimum donation amount is $10.00.",
                                                         "max_value":"The maximum donation amount is $20,000.",})
    jumo_amount = forms.DecimalField(label="Optional tip for Jumo", required=True, min_value=0.0)
    name_on_card = forms.CharField(label="Name On Card", max_length=60, required=True)
    card_number = CreditCardField(label="Credit Card Number", required=True)
    expiry_date = ExpiryDateField(label="Expiration Date", required=True)
    ccv_code = VerificationValueField(label="CCV", required=True)

    comment = forms.CharField(label="Why are you pledging?", max_length=300, required=False,
                              widget=forms.Textarea(attrs={"rows":3,"cols":72}))

    post_to_facebook = forms.BooleanField(label="Share this donation Facebook", initial=True, required=False)
    list_name_publicly = forms.BooleanField(label="Share this donation on Jumo", initial=True, required=False)

    def __init__(self, initial_user=None, initial_amount=None, *args, **kwargs):
        super(BaseDonationForm, self).__init__(*args, **kwargs)
        if initial_user and not self.is_bound:
            self.user_donating = initial_user
            self.fields["donor_email"].initial = initial_user.email
            self.fields["first_name"].initial = initial_user.first_name
            self.fields["last_name"].initial = initial_user.last_name
            self.user_donating = initial_user
        if initial_amount:
            self.fields["donation_amount"].initial = initial_amount

    def to_donation_data(self, donor_user=None, use_mock_nfg=False, sources=None):
        #pretty sure this will blow up if data isn't valid.
        return dict(firstname=self.cleaned_data["first_name"],
                    lastname=self.cleaned_data["last_name"],
                    email=self.cleaned_data["donor_email"],
                    user_donating=donor_user,
                    phone=self.cleaned_data["phone"],
                    street1=self.cleaned_data["address_line_one"],
                    street2=self.cleaned_data["address_line_two"],
                    city=self.cleaned_data["city"],
                    region=self.cleaned_data["state"],
                    postal_code=self.cleaned_data["zip_code"],
                    country=self.cleaned_data["country"],
                    name_on_card=self.cleaned_data["name_on_card"],
                    cc_number=self.cleaned_data["card_number"],
                    cc_type=self.cleaned_data["card_type"],
                    cc_exp_month=self.cleaned_data["expiry_date"].month,
                    cc_exp_year=self.cleaned_data["expiry_date"].year,
                    cc_csc=self.cleaned_data["ccv_code"],
                    amount=self.cleaned_data["donation_amount"],
                    jumo_amount=self.cleaned_data["jumo_amount"],
                    comment=self.cleaned_data["comment"],
                    list_publicly = self.cleaned_data["list_name_publicly"],
                    use_mock_nfg = use_mock_nfg,
                    sources = sources
                    )

    def handle_nfg_errors(self, nfg_errors):
        for nfg_err in nfg_errors:
            if nfg_err.get("error_code") and NFG_ERROR_TO_FIELD.get(nfg_err["error_code"]):
                fieldname = NFG_ERROR_TO_FIELD[nfg_err["error_code"]]
                if not self._errors.get(fieldname):
                    self._errors[fieldname] = ErrorList([nfg_err["error_data"]])
                else:
                    self._errors[fieldname].append(nfg_err["error_data"])
            else:
                self.handle_unknown_error()

    def handle_unknown_error(self):
        #We're just setting the error so the template knows it's there.
        #It doesn't actually use the error message.
        self._errors["unknown"] = ErrorList(["We're unable to process your donation. Ensure that the address and zipcode provided match the billing address on your credit card and that the CCV number is correct."])



class StandardDonationForm(BaseDonationForm):
    def to_donation_data(self, org, *args, **kwargs):
        data = super(StandardDonationForm, self).to_donation_data(*args, **kwargs)
        data["entity"] = org
        data["beneficiary"] = org
        return data



class StillDonateForm(forms.Form):
    still_donate = forms.BooleanField(required=False, widget=forms.RadioSelect(choices=((False, 'No'),(True, 'Yes'),)), initial=True)

    def handle_unknown_error(self):
        #We're just setting the error so the template knows it's there.
        #It doesn't actually use the error message.
        self._errors["unknown"] = ErrorList(["An Unknown Error Has Occurred"])

########NEW FILE########
__FILENAME__ = models
from datetime import datetime
from decimal import Decimal
from django.conf import settings
from django.contrib.contenttypes import generic
from django.db import models, transaction
from etc import cache
from etc.entities import EntityTypes, type_to_class, obj_to_type
from etc.func import crc32, salted_hash
import json
import logging
from org.models import Org
from sourcing.models import SourceTaggedItem
import sys
import urlparse
from users.models import User
#from utils.donations import nfg_api, mock_nfg_api
from utils.misc_helpers import send_admins_error_email


class Donor(models.Model):
    id = models.AutoField(db_column='donor_id', primary_key=True)
    user = models.ForeignKey(User, db_column='user_id', null=True)
    first_name = models.CharField(max_length=30, db_column='first_name')
    last_name = models.CharField(max_length=30, db_column='last_name')
    email = models.EmailField(db_column='email', max_length=200, unique=True)
    email_crc32 = models.IntegerField(db_column='email_crc32')

    class Meta:
        db_table = 'donors'

    @property
    def get_first_name(self):
        return self.first_name

    # For distinguishing in templates between Donors and Jumo users
    @property
    def is_jumo_user(self):
        return self.user and self.user.is_active

    def save(self, *args, **kw):
        self.email = self.email.lower()
        self.email_crc32 = crc32(self.email)
        super(Donor, self).save(*args, **kw)

    @property
    def email_hash(self):
        return salted_hash(self.email)

    @classmethod
    def get_or_create(cls, first_name, last_name, email, user=None):
        email = email.lower()
        d, created = Donor.objects.get_or_create(email=email, email_crc32=crc32(email))
        state_changed = False
        if user and user != d.user:
            d.user = user
            state_changed = True
        else:
            try:
                # For those donating anonymously
                # who are already registered (active) users
                existing_user = User.objects.get(email=email, is_active=True)
                d.user=existing_user
            except User.DoesNotExist:
                pass
        if d.first_name != first_name:
            d.first_name = first_name
            state_changed = True
        if d.last_name != last_name:
            d.last_name = last_name
            state_changed = True

        if state_changed:
            d.save()
        return d

    @classmethod
    def from_email(cls, email):
        try:
            email = email.lower()
            return Donor.objects.get(email=email, email_crc32=crc32(email))
        except Donor.DoesNotExist:
            return None
        except Exception, err:
            logging.exception("Error Retrieving Donor On Email")
            return None

    @classmethod
    def from_user(cls, user):
        try:
            return Donor.objects.get(user=user)
        except Donor.DoesNotExist:
            return None
        except Exception, err:
            logging.exception("Error Retrieving Donor From User")
            return None

    @classmethod
    def get_all_donors_for_entity(cls, entity):
        return Donor.objects.raw("""
        select do.*
        from donations d
        join donors do
            using(donor_id)
        where d.entity_type=%(entity_type)s
        and d.entity_id=%(entity_id)s
        """, {'entity_type': entity.type, 'entity_id': entity.id})

    class Meta:
        db_table = 'donors'

    def is_subscribed_to(self, pub_id):
        return len(self.subscriptions.filter(id=pub_id, subscription__subscribed=True).values_list('id')) > 0


class DonorPhone(models.Model):
    id = models.AutoField(db_column='donor_phone_id', primary_key=True)
    donor = models.ForeignKey(Donor, db_column='donor_id')
    phone = models.CharField(max_length=50)

    class Meta:
        db_table='donor_phone_numbers'


class DonorAddress(models.Model):
    id = models.AutoField(db_column='donor_address_id', primary_key=True)
    donor = models.ForeignKey(Donor, db_column='donor_id', related_name='addresses')
    street1 = models.CharField(max_length=255, db_column='street1')
    street2 = models.CharField(max_length=255, db_column='street2', blank=True)
    city = models.CharField(max_length=255, db_column='city')
    region = models.CharField(max_length=255, db_column='region', blank=True, default="")
    postal_code = models.CharField(max_length=14, db_column='postal_code')
    country = models.CharField(max_length=2, db_column='country', blank=True)
    is_billing = models.BooleanField(default=True, db_column='is_billing')
    is_shipping = models.BooleanField(default=True, db_column='is_shipping')

    class Meta:
        db_table = 'donor_addresses'

    @classmethod
    def get_or_create(cls, **kwargs):
        """
        EX: dict(donor=donor, street1='000 FakeTown', street2='', city='FakeyVille',
                 region='NY', postal_code=10012, country="United States of America")
        """
        da, created = DonorAddress.objects.get_or_create(donor=kwargs["donor"],
                                          street1=kwargs["street1"],
                                          street2=kwargs.get("street2"),
                                          city=kwargs["city"],
                                          region=kwargs["region"],
                                          postal_code=kwargs["postal_code"],
                                          country=kwargs["country"])
        return da


class CreditCard(models.Model):
    id = models.AutoField(db_column='credit_card_id', primary_key=True)
    donor = models.ForeignKey(Donor, db_column='donor_id', related_name='credit_cards')
    donor_address = models.ForeignKey(DonorAddress, db_column='donor_address_id')
    date_last_charged = models.DateTimeField(db_column='date_last_charged')
    status = models.CharField(max_length=50, db_column='status')
    nfg_card_on_file_id = models.IntegerField(db_column='nfg_card_on_file_id')
    nfg_cof_is_active = models.BooleanField(db_column='nfg_cof_is_active')

    class Meta:
        db_table = 'credit_cards'

    class CardStatus:
        """TODO: use statuses to avoid rebilling people we know are failures"""
        DECLINED = 'declined'

    def disable_cof(self):
        pass

class DonationProcessingFailed(Exception):
    pass

class Donation(models.Model):
    id = models.AutoField(db_column='donation_id', primary_key=True)
    donor = models.ForeignKey(Donor, db_column='donor_id', related_name='donations')
    credit_card = models.ForeignKey(CreditCard, db_column='credit_card_id')
    entity_type = models.CharField(max_length=100, db_column='entity_type')
    entity_id = models.IntegerField(db_column='entity_id')
    amount = models.DecimalField(max_digits=19, decimal_places=2, db_column='amount')
    jumo_amount = models.DecimalField(max_digits=19, decimal_places=2, db_column='jumo_amount')
    street1 = models.CharField(max_length=255, db_column='street1')
    street2 = models.CharField(max_length=255, db_column='street2', blank=True)
    city = models.CharField(max_length=255, db_column='city')
    region = models.CharField(max_length=255, blank=True, default="", db_column='region')
    postal_code = models.CharField(max_length=14, db_column='postal_code')
    country = models.CharField(max_length=2, db_column='country', blank=True)
    phone = models.CharField(max_length=50, db_column='phone')
    comment = models.CharField(max_length=2000, db_column='comment', blank=True)
    charge_id = models.IntegerField(db_column='charge_id', null=True, default=None)
    charge_status = models.CharField(max_length=100, db_column='charge_status')
    payment_status = models.CharField(max_length=100, db_column='payment_status')
    last_payment_attempt = models.DateTimeField(db_column='last_payment_attempt')
    date = models.DateTimeField(auto_now_add=True, db_column='donation_date')
    version = models.IntegerField(db_column='version', default=1)
    list_publicly = models.BooleanField(db_column='list_publicly')
    is_anonymous = models.BooleanField(db_column='is_anonymous')


    _source_tagged_items = generic.GenericRelation(SourceTaggedItem,
                                                   content_type_field='item_type',
                                                   object_id_field='item_id')

    class Meta:
        db_table = 'donations'

    class ChargeStatus:
        DO_NOT_ATTEMPT = "do_not_attempt"
        READY = "ready"
        ATTEMPTING_PAYMENT = "attempting_payment"
        PAYMENT_COMPLETE = "payment_complete"

    class PaymentStatus:
        UNPAID = "unpaid"
        PAID = "paid"
        FAILED = "failed"
        PERMAFAILED = "permafailed"

    @classmethod
    def get(cls, id, force_db=False):
        if force_db:
            obj = cls.objects.get(id=id)
            cache.bust(obj)
            return obj
        return cache.get(cls, id)

    @classmethod
    def multiget(cls, ids, force_db=False):
        if force_db:
            return Donation.objects.filter(id__in=ids)
        return cache.get(cls, ids)


    @classmethod
    def get_retryable_donations(cls):
        case_statement = ' '.join(["when %s then %s" % (idx+1,val) for idx, val in enumerate(settings.PAYMENT_RETRY_SCHEDULE) ])
        return Donation.objects.raw("""
        select
        do.*,
        do.last_payment_attempt + interval case count(p.donation_id) """ + case_statement + """ end day as min_retry_date
        from donations do
        join payments p
          on p.donation_id = do.payment_id
          and did_succeed=0
        where do.payment_status = %(failed)s
        and do.charge_status = %(ready)s
        group by do.donation_id
        having utc_timestamp() >= min_retry_date
        """ , {'failed': cls.PaymentStatus.FAILED,
               'ready': cls.ChargeStatus.READY
               })

    @classmethod
    def get_donations_for_entity(cls, entity):
        return Donation.objects.filter(entity_type=entity.type, entity_id=entity.id)

    @classmethod
    def get_processable_donations_for_entity(cls, entity):
        return Donation.objects.filter(entity_type=entity.type,
                                       entity_id=entity.id,
                                       charge_status=cls.ChargeStatus.READY,
                                       payment_status=cls.PaymentStatus.UNPAID)

    @property
    def get_source_tags(self):
        # @todo: not optimized
        return [item.tag for item in self._source_tagged_items.all()]

    @property
    def entity(self):
        return cache.get(type_to_class(self.entity_type), self.entity_id)

    @property
    def get_beneficiaries(self):
        return DonationBeneficiary.objects.filter(donation=self)

    def mark_attempting(self):
        # Optimistic locking
        affected = Donation.objects.filter(id=self.id, version=self.version).update(charge_status=self.ChargeStatus.ATTEMPTING_PAYMENT, version=self.version+1)

        if not affected:
            msg = "Tried optimistic lock of donation row with version %d, but a higher version existed. This is probably BAD. Unless somebody did an ad hoc update, there may be more than 1 instance of bill_campaignd running." % self.version
            send_admins_error_email("DONATION ERROR", msg, sys.exc_info())
            raise DonationProcessingFailed, msg

    def process(self):
        pass

    @transaction.commit_on_success()
    def _execute_payment(self, payment_fails):
        pass


    @classmethod
    def create_and_process(cls, **kwargs):
        pass


    @classmethod
    @transaction.commit_on_success()
    def _create_and_process(cls, **kwargs):
        pass


    @classmethod
    def create_and_store(cls, **kwargs):
        pass

    @classmethod
    @transaction.commit_on_success()
    def _create(cls, store_cc=False, **kwargs):
        pass

    def _to_nfg_dict(self):
        pass

    @classmethod
    def _cc_info_to_nfg_dict(cls, **kwargs):
        pass

    def add_source_tags(self, source_tags):
        pass

    def save(self, *args, **kwargs):
        pass


class DonationBeneficiary(models.Model):
    id = models.AutoField(db_column='donation_beneficiary_id', primary_key=True)
    donation = models.ForeignKey(Donation, db_column='donation_id', related_name='beneficiaries')
    org = models.ForeignKey(Org, db_column='org_id')
    amount = models.DecimalField(max_digits=19, decimal_places=2, db_column='amount')

    class Meta:
        db_table = 'donation_beneficiaries'
        unique_together = ('donation', 'org')

class Payment(models.Model):
    id = models.AutoField(db_column='payment_id', primary_key=True)
    status = models.CharField(max_length=255, db_column='status', blank=True)
    donation = models.ForeignKey(Donation, db_column='donation_id')
    did_succeed = models.BooleanField(db_column='did_succeed')
    error_data = models.CharField(max_length=2000, db_column='error_data')
    payment_date = models.DateTimeField(db_column='payment_date', default=datetime.utcnow)

    class Meta:
        db_table = 'payments'

########NEW FILE########
__FILENAME__ = tasks
from celery.task import task
from mailer.notification_tasks import EmailTypes, send_notification
from donation.models import Donation
#from utils.donations import nfg_api
import logging

@task
def process_donation(donation_id):
    pass

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = admin
from action.models import Action
from cust_admin.forms import HiddenRankModelForm
from cust_admin.models import LinkedGenericStackedInline
from cust_admin.widgets import ForeignKeyToObjWidget
from django import forms
from django.contrib import admin
from django.contrib.contenttypes.generic import GenericTabularInline, GenericStackedInline
from entity_items.models import Advocate, ContentItem, MediaItem, TimelineItem



class MediaItemInlineForm(forms.ModelForm):
    class Meta:
        model = MediaItem
        widgets = {
            'position': forms.HiddenInput,
        }
    media_info = forms.CharField(widget = forms.Textarea(), required=False)

    def __init__(self, *args, **kwargs):
        super(MediaItemInlineForm, self).__init__(*args, **kwargs)
        if kwargs.get('instance'):
            instance = kwargs.get('instance')
            if instance.media_type == MediaItem.MediaTypes.PULLQUOTE:
                self.fields['media_info'].initial = instance.get_pullquote
            elif instance.media_type == MediaItem.MediaTypes.VIDEO:
                self.fields['media_info'].initial = "http://www.youtube.com/watch?v=%s" % instance.get_youtube_id


    def save(self, force_insert=False, force_update=False, commit=True):
        model = super(MediaItemInlineForm, self).save(commit=False)
        if model.media_type == MediaItem.MediaTypes.PULLQUOTE:
            model.set_pullquote(self.cleaned_data["media_info"])
        elif model.media_type == MediaItem.MediaTypes.VIDEO:
            model.set_video_data(self.cleaned_data["media_info"])
        if commit:
            model.save()
        return model

class MediaItemInline(GenericStackedInline):
    model = MediaItem
    extra = 0
    classes = ('collapse closed',)
    form = MediaItemInlineForm
    fieldsets = (None, { 'fields': (
                    ('media_type', 'position',),
                    'img_url',
                    'thumbnail_url',
                    'media_info',
                    'caption','metadata',)}),

    sortable_field_name = 'position'
    def __init__(self, *args, **kwargs):
        super(MediaItemInline, self).__init__(*args, **kwargs)

class ActionInline(GenericTabularInline):
    model = Action
    form = HiddenRankModelForm
    extra = 0
    classes = ('collapse closed',)
    verbose_name = ""
    verbose_name_plural = "Actions"
    fields = ('title','link','type','rank')
    sortable_field_name = 'rank'


class AdvocateInline(GenericTabularInline):
    model = Advocate
    extra = 0
    classes = ('collapse closed',)
    verbose_name = "Advocate"
    verbose_name_plural = "Advocates"
    fieldsets = (None, {
        'fields': (('name', 'twitter_id', 'user',),)}),
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'user':
            kwargs['widget'] = ForeignKeyToObjWidget(rel=Advocate._meta.get_field('user').rel)
        return super(AdvocateInline,self).formfield_for_dbfield(db_field,**kwargs)


class TimelineInline(GenericStackedInline):
    model = TimelineItem
    extra = 0
    classes = ('collapse closed',)
    verbose_name = ""
    verbose_name_plural = "Timeline"


class DefaultContentItemInlineForm(forms.ModelForm):
    class Meta:
        model = ContentItem
        widgets = {'position':forms.HiddenInput}

    rich_text_body = forms.CharField(widget = forms.Textarea(attrs = {'class':'inlineEditor'}))

class DefaultContentItemInline(LinkedGenericStackedInline):
    model = ContentItem
    extra = 0
    classes = ('collapse closed',)
    sortable_field_name = 'position'
    fieldsets = (None, {
        'fields': (
            ('title', 'position', 'section',),
            'rich_text_body',)}),

    class Media:
        js = ['media/admin/tinymce/jscripts/tiny_mce/tiny_mce.js', 'media/admin/tinymce_setup/tinymce_setup.js']


class CenterContentItemInlineForm(DefaultContentItemInlineForm):
    section = forms.CharField(initial=ContentItem.ContentSection.CENTER, widget=forms.HiddenInput)

class CenterContentItemInline(DefaultContentItemInline):
    form = CenterContentItemInlineForm
    verbose_name = ""
    verbose_name_plural = "Center Content Items"
    def queryset(self, request):
        qs = super(CenterContentItemInline, self).queryset(request)
        return qs.filter(section = ContentItem.ContentSection.CENTER)


class LeftContentItemInlineForm(DefaultContentItemInlineForm):
    section = forms.CharField(initial=ContentItem.ContentSection.LEFT, widget=forms.HiddenInput)

class LeftContentItemInline(DefaultContentItemInline):
    form = LeftContentItemInlineForm
    verbose_name = ""
    verbose_name_plural = "Left Content Items"
    def queryset(self, request):
        qs = super(LeftContentItemInline, self).queryset(request)
        return qs.filter(section = ContentItem.ContentSection.LEFT)





class ContentItemForm(forms.ModelForm):
    class Meta:
        model = ContentItem
    rich_text_body = forms.CharField(widget = forms.Textarea(attrs = {'class':'mceEditor'}))

class ContentItemAdmin(admin.ModelAdmin):
    inlines = [MediaItemInline,]
    form = ContentItemForm
    fieldsets = (None, {
        'fields': (
            ('title', 'section',),
            'rich_text_body',)}),
    class Media:
        js = ['media/admin/tinymce/jscripts/tiny_mce/tiny_mce.js', 'media/admin/tinymce_setup/tinymce_setup.js']


admin.site.register(ContentItem, ContentItemAdmin)

########NEW FILE########
__FILENAME__ = advocate
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from users.models import User

class Advocate(models.Model):
    id = models.AutoField(db_column='advocate_id', primary_key=True)
    content_type = models.ForeignKey(ContentType, limit_choices_to={"model__in": ("Org", "Issue")},
                                    default=ContentType.objects.get(model='issue').id)
    object_id = models.PositiveIntegerField()
    entity = generic.GenericForeignKey()
    user = models.ForeignKey(User, null=True, blank=True)
    name = models.CharField(max_length=200) #In the event they don't have a jumo user.
    twitter_id = models.CharField(blank = True, max_length = 32)
    url = models.URLField(verify_exists=False, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Advocate"
        verbose_name_plural = "Advocates"
        app_label = "entity_items"
        db_table="advocates"

    def __str__(self):
        if self.user:
            return str(self.user)
        else:
            return self.name

########NEW FILE########
__FILENAME__ = content_item
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.html import strip_tags
from entity_items.models import MediaItem
from etc import cache
from utils.query_set import QuerySet

class ContentItemQS(QuerySet):
    def center(self):
        return self.filter(section=ContentItem.ContentSection.CENTER)

    def left(self):
        return self.filter(section=ContentItem.ContentSection.LEFT)

    def mission_statement(self):
        return self.get(title=ContentItem.MISSION_STATEMENT)

class ContentItem(models.Model):
    class ContentSection:
        LEFT = 'left'
        CENTER = 'center'

    MISSION_STATEMENT = 'Mission Statement'

    CONTENT_SECTION_CHOICES = (
        (ContentSection.LEFT, "Left"),
        (ContentSection.CENTER, "Center"),
    )

    id = models.AutoField(db_column='content_item_id', primary_key=True)
    content_type = models.ForeignKey(ContentType, limit_choices_to={"model__in": ("Org", "Issue")},
                                    default=ContentType.objects.get(model='issue').id)
    object_id = models.PositiveIntegerField()
    entity = generic.GenericForeignKey()
    section = models.CharField(max_length=100, choices=CONTENT_SECTION_CHOICES, default=ContentSection.CENTER)
    position = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    rich_text_body = models.TextField(blank=True)
    media_item = generic.GenericRelation(MediaItem)

    objects = ContentItemQS.as_manager()

    class Meta:
        verbose_name = "ContentItem"
        verbose_name_plural = "ContentItems"
        app_label = "entity_items"
        db_table = "content_items"
        ordering = ["position"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.body = strip_tags(self.rich_text_body)
        super(ContentItem, self).save(*args, **kwargs)
        cache.bust(self)


    @property
    def get_media_item(self):
        #Faking singular media item for possible future changes.
        media_items = self.media_item.all()
        return media_items[0] if media_items else None;

    def set_media_item(self, value):
        #Faking singular media item for possible future changes.
        self.media_item.clear()
        self.media_item.add(value)

########NEW FILE########
__FILENAME__ = location
import json
from hashlib import md5
from miner.classifiers.location_tagger import LocationClassifier

from django.db import models
from django.db import connections
from django.forms.models import model_to_dict

CLASSIFIER_CHOICES = (('US', 'United States'),
                      ('International', 'International')
                      )

class Location(models.Model):
    id = models.AutoField(primary_key = True, db_column='location_id')
    raw_geodata = models.TextField(blank = True)
    geodata_hash = models.CharField(max_length=32, null=False)
    longitude = models.FloatField(null = True)
    latitude = models.FloatField(null = True, blank = True)
    address = models.CharField(max_length = 255, blank = True)
    region = models.CharField(max_length = 255, blank = True)
    locality = models.CharField(max_length = 255, blank = True)
    postal_code = models.CharField(max_length = 255, blank = True)
    country_name = models.CharField(max_length = 255, blank = True)
    classification = models.CharField(max_length = 50, null = True, blank=True, choices=CLASSIFIER_CHOICES)

    class Meta:
        db_table = 'locations'

    @classmethod
    def get_or_create(cls, data):
        if not data:
            return None
        data = json.loads(data)

        l = Location()
        raw_geodata = data.get('raw_geodata', '')
        l.raw_geodata = json.dumps(raw_geodata) if isinstance(raw_geodata, dict) else raw_geodata
        l.latitude = float(data.get('latitude', 0.0))
        l.longitude = float(data.get('longitude', 0.0))
        l.address = data.get('address', '')
        l.region = data.get('region', '')
        l.locality = data.get('locality', '')
        l.postal_code = data.get('postal_code', '')
        l.country_name = data.get('country_name', '')

        hash = md5(l.raw_geodata) if raw_geodata else md5(''.join([l.address, l.region, l.locality, l.postal_code, l.country_name]))
        l.geodata_hash = hash.hexdigest()

        existing = Location.objects.filter(geodata_hash = l.geodata_hash)
        if len(list(existing)) > 0:
            return existing[0]

        classifier = LocationClassifier.classify(l)
        if classifier:
            l.classifier = classifier

        l.save()
        return l


    def get_raw(self):
        if self.raw_geodata:
            try:
                return json.loads(self.raw_geodata)
            except:
                return None

    @property
    def name(self):
        """ Temp until we fix up name"""
        name = None
        raw_data = self.get_raw()
        if raw_data and 'name' in raw_data:
            name = raw_data['name']
        elif raw_data and 'raw_geodata' in raw_data:
            try:
                raw = json.loads(raw_data['raw_geodata'])
            except TypeError:
                raw = raw_data['raw_geodata']
            name = raw.get('name', None)
        return name

    def __unicode__(self):
        values = []
        separator = ' '

        if self.address:
            values.append(self.address)
            values.append(separator)

        name = self.name
        has_name = name or self.locality.strip()
        has_region = self.region and self.region != name
        has_country = self.country_name and self.country_name != name

        if name and name != self.locality.strip():
            values.append(name)
        elif self.locality.strip():
            values.append(self.locality)
            separator = ', '


        if has_name and (has_region or has_country):
            values.append(separator)

        separator = ' '

        if has_region:
            values.append(self.region)
            values.append(separator)

        if has_country:
            values.append(self.country_name)

        return ''.join(values)

    def to_json(self):
        return json.dumps(model_to_dict(self))

########NEW FILE########
__FILENAME__ = media_item
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from lib.image_upload import ImageSize, ImageType, S3EnabledImageField
from utils.regex_tools import youtube_url_magic
import json
from etc import cache

class MediaItem(models.Model):
    class MediaTypes:
        VIDEO = 'video'
        PHOTO = 'photo'
        PULLQUOTE = 'pullquote'

    MEDIA_TYPE_CHOICES = (
        (MediaTypes.VIDEO, 'Video'),
        (MediaTypes.PHOTO, 'Photo'),
        (MediaTypes.PULLQUOTE, 'Pullquote')
    )

    id = models.AutoField(db_column='media_item_id', primary_key=True)
    content_type = models.ForeignKey(ContentType, limit_choices_to={"model__in": ("Org", "Issue", "ContentItem")},
                                     default=ContentType.objects.get(model='issue').id)
    object_id = models.PositiveIntegerField()
    media_type = models.CharField(max_length=100, choices=MEDIA_TYPE_CHOICES)
    entity = generic.GenericForeignKey()
    caption = models.TextField(blank=True)
    img_url = S3EnabledImageField(image_type=ImageType.MEDIAITEM, image_size=ImageSize.LARGE, blank=True)
    thumbnail_url = S3EnabledImageField(image_type=ImageType.MEDIAITEM, image_size=ImageSize.SMALL, blank=True)
    position = models.PositiveIntegerField(default=0)
    metadata = models.TextField(blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "MediaItem"
        verbose_name_plural = "MediaItems"
        app_label = "entity_items"
        db_table="media_items"

    def __str__(self):
        return str(self.media_type)


    def save(self):
        #Note: I want to move all this img stuff to the forms that set them...
        #not here on the model. This is a hack so we ensure the model id is
        #used in the filename.
        if not self.id and not self.img_url._committed:
            #most likely you need to watch small img too
            thumbnail_url_comm = self.img_url._committed
            self.img_url._committed = True
            self.thumbnail_url._committed = True
            super(MediaItem, self).save()
            self.img_url._committed = False
            self.thumbnail_url._committed = thumbnail_url_comm

        if not self.id and not self.thumbnail_url._committed:
            self.thumbnail_url._committed = True
            super(MediaItem, self).save()
            self.thumbnail_url._committed = False

        self.img_url.storage.inst_id = self.id
        self.thumbnail_url.storage.inst_id = self.id
        super(MediaItem, self).save()
        cache.bust(self)

    @property
    def get_image_small(self):
        if self.thumbnail_url:
            return self.thumbnail_url.url
        return ''

    @property
    def get_image_large(self):
        if self.img_url:
            return self.img_url.url
        return ''


    def set_pullquote(self, value):
        if self.media_type == self.MediaTypes.PULLQUOTE:
            self.metadata = json.dumps({"quote_text" : value})

    def set_video_data(self, value):
        if self.media_type == self.MediaTypes.VIDEO:
            yt_data = youtube_url_magic(value)
            if yt_data:
                self.metadata = json.dumps(yt_data)
            else:
                self.metadata = ""

    @property
    def get_pullquote(self):
        result = ""
        if self.media_type == self.MediaTypes.PULLQUOTE:
            try:
                result = json.loads(self.metadata)["quote_text"]
            except Exception:
                pass
        return result

    @property
    def get_youtube_id(self):
        result = ""
        if self.media_type == self.MediaTypes.VIDEO:
            try:
                result = json.loads(self.metadata)["source_id"]
            except Exception:
                pass
        return result

########NEW FILE########
__FILENAME__ = timeline_item
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from etc import cache

class TimelineItem(models.Model):
    id = models.AutoField(db_column='timeline_item_id', primary_key=True)
    content_type = models.ForeignKey(ContentType, limit_choices_to={"model__in": ("Org", "Issue")},
                                    default=ContentType.objects.get(model='issue').id)
    object_id = models.PositiveIntegerField()
    entity = generic.GenericForeignKey()
    year = models.IntegerField(max_length=4)
    description = models.TextField(null=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "TimelineItem"
        verbose_name_plural = "TimelineItems"
        app_label = "entity_items"
        db_table="timeline_items"

    def save(self, *args, **kwargs):
        super(TimelineItem, self).save(*args, **kwargs)
        cache.bust(self)

    def __str__(self):
        return str(self.year)

########NEW FILE########
__FILENAME__ = tests

########NEW FILE########
__FILENAME__ = views

########NEW FILE########
__FILENAME__ = auth
from etc.user import create_salt_cookie
from datetime import datetime, timedelta
from django.contrib.auth import authenticate
from etc.constants import ACCOUNT_COOKIE_SALT, ACCOUNT_COOKIE
from lib.facebook import GraphAPI
import logging
from users.models import User

def attempt_login(request, email_or_username, password):
    auth_user = authenticate(username=email_or_username, password=password)
    if auth_user is not None:
        user = User.objects.get(user_ptr=auth_user.id)
        login(request, user)
        return user
    return None

#Same as django's but with some fb magic and minus session work.
def login(request, user):
    user = user if user is not None else request.user
    user.last_login = datetime.now()
    user.save()

    if user.fb_access_token:
        #Update Facebook Friends
        try:
            fb = GraphAPI(user.fb_access_token)
            fb_friends = fb.request('/me/friends')
            user.update_fb_follows([item['id'] for item in fb_friends['data']])
        except Exception, err:
            logging.exception("Error importing facebook friends.")

    if hasattr(request, 'user'):
        request.user = user

#Same as django's minus session work
def logout(request):
    if hasattr(request, 'user'):
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()

def set_auth_cookies(response, user):
    response.set_cookie(ACCOUNT_COOKIE, user.id, expires = datetime.now() + timedelta(days=365), path='/')
    response.set_cookie(ACCOUNT_COOKIE_SALT, create_salt_cookie(user.id), expires = datetime.now() + timedelta(days=365), path='/')
    return response

def unset_auth_cookies(response):
    response.delete_cookie(ACCOUNT_COOKIE)
    response.delete_cookie(ACCOUNT_COOKIE_SALT)
    return response

########NEW FILE########
__FILENAME__ = backend
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import email_re
from etc.user import check_password

class JumoBackend:
    def authenticate(self, username=None, password=None):
        if email_re.match(username):
            try:
                _user = User.objects.get(email = username, is_active = True)
            except:
                return None
        else:
            try:
                _user = User.objects.get(username = username, is_active = True)
            except:
                return None
        if check_password(_user.password, password):
            return _user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id, is_active = True)
        except User.DoesNotExist:
            return None

########NEW FILE########
__FILENAME__ = cache
from collections import namedtuple
from django.core.cache import cache
from django.db.models.query import ValuesListQuerySet
from django.db.models.loading import get_model
from itertools import groupby


_process_cache = {}

def _cache_key(obj, id = None):
    class_name = obj.__name__ if hasattr(obj, "__name__") else obj.__class__.__name__
    if id is None:
        id = obj.id
    return '%s_%s' % (class_name, id)

TypedId = namedtuple('TypedId', 'cls,id')

def _split_cache_key(key):
    return TypedId(key.split('_'))

def put(obj):
    if type(obj) == list:
        cache.set_many(dict(zip([_cache_key(o) for o in obj], [o for o in obj])))
        for o in obj:
            _process_cache[_cache_key(o)] = obj
    else:
        cache.set(_cache_key(obj), obj)
        _process_cache[_cache_key(obj)] = obj

def get(cls, id, using_db=None):
    if type(id) == ValuesListQuerySet:
        id = list(id)
    if hasattr(id, '__iter__'):
        _pcresult = []
        for i in id:
            pcr = _process_cache.get(_cache_key(cls, i))
            if pcr is not None:
                _pcresult.append(pcr)

        if len(_pcresult) == len(id):
            return _pcresult

        _mcresult = cache.get_many([_cache_key(cls, i) for i in id])
        if len(_mcresult) == len(id):
            mc_result = map(lambda t: _mcresult[t], [_cache_key(cls, l) for l in id])
            for mc in mc_result:
                _process_cache[_cache_key(mc)] = mc
            return mc_result

        _id_diffs = set(id).difference([_mcresult[l].id for l in _mcresult])

        #There's probably a more "pythony" way of doing the following.
        _fetch = {}
        manager = cls.objects
        if using_db is not None:
            manager = manager.using(using_db)

        _db_results = list(manager.filter(id__in = _id_diffs))
        for l in _id_diffs:
            for fi in _db_results:
                if fi.id == l:
                    _fetch[_cache_key(cls, l)] = fi
                    break

        for _i in _fetch:
            put(_fetch[_i])
        _fetch.update(dict(zip(_mcresult, [_mcresult[l] for l in _mcresult])))

        results = []
        for l in id:
            if _fetch.has_key(_cache_key(cls, l)):
                results.append(_fetch[_cache_key(cls, l)])
        return results
    else:
        _obj = None
        try:
            _obj = _process_cache.get(_cache_key(cls, id))
            if _obj is None:
                _obj = cache.get(_cache_key(cls, id))
        except:
            pass
        if _obj is None:
            _obj = cls.objects.get(id = id)
            put(_obj)
        return _obj

def bust(obj, update = False):
    if type(obj) == list:
        cache.delete_many([_cache_key(o) for o in obj])
        for o in obj:
            if _cache_key(o) in _process_cache:
                del _process_cache[_cache_key(o)]
    else:
        _k = _cache_key(obj)
        cache.delete(_k)
        if _k in _process_cache:
            del _process_cache[_cache_key(obj)]
    if update:
        put(obj)


########### HANDLE CACHING ##############

def get_on_handle(cls, handle):
    id = cache.get(_cache_key(cls, handle))
    if id:
        return get(cls, id)
    return None

def put_on_handle(obj, handle):
    put(obj)
    cache.set(_cache_key(obj, handle), obj.id)

def bust_on_handle(obj, handle, update = False):
    bust(obj, False)
    cache.delete(_cache_key(obj, handle))
    if update:
        put_on_handle(obj, handle)


########### RELATION SET CACHING ##############
def _relation_cache_key(owner_obj, relation_obj, id):
    owner_class_name = owner_obj.__name__ if hasattr(owner_obj, "__name__") else owner_obj.__class__.__name__
    relation_class_name = relation_obj.__name__ if hasattr(relation_obj, "__name__") else relation_obj.__class__.__name__
    return '%s_%s_%s' % (owner_class_name, relation_class_name, id)

def relation_put(owner_obj, relation_obj, id, data):
    cache.set(_relation_cache_key(owner_obj, relation_obj, id), data)

def relation_get(owner_cls, relation_cls, id):
    return cache.get(_relation_cache_key(owner_cls, relation_cls, id))

def relation_bust(owner_obj, relation_obj, id):
    cache.delete(_relation_cache_key(owner_obj, relation_obj, id))


########### Decorator ################

def get_class_by_model_or_name(cls):
    collection_class = None
    if isinstance(cls, basestring):
        app_label, model_name = cls.split('.')
        try:
            collection_class=get_model(app_label, model_name)
        except ImportError:
            # This is a Django internal thing. If all the models are not yet loaded,
            # you can't get one out of the cache so it will try to do an import and then
            # you get circular dependencies. This just prepopulates the cache with all the models
            from django.db.models.loading import cache as app_cache
            app_cache._populate()
            # If it fails here you actually didn't specify a valid model class
            # remember it's "users.User" not just "User"
            collection_class=get_model(app_label, model_name)

    else:
        collection_class = cls
    return collection_class

def collection_cache(cls, local_var):
    """
    For use with properties or methods which take only the self argument.

    @param cls: a collection class (or Django-style model name such as "users.User" as the first argument.
    @param local_var: some variable name, conventionally a pseudo-private beginning with and underscore (e.g. "_list_ids")
                      This will store a dictionary on the object like {'cls': MyCollectionClass, 'ids': [1,2,3,4,5]}.
                      When the whole item is cached, it will only store the collection class and the ids
    """
    def _func(f):
        def _with_args(self):
            collection_class = get_class_by_model_or_name(cls)
            if not hasattr(self, local_var) or getattr(self, local_var, None) is None: # Just to be safe, you can define the local and set to None
                ret = f(self) or []
                setattr(self, local_var, {'cls': collection_class, 'ids': [item.id for item in ret]})
                put(self)
                return ret
            return list(get(collection_class, getattr(self, local_var)['ids']))
        return _with_args
    return _func

########NEW FILE########
__FILENAME__ = constants
ACCOUNT_COOKIE = 'acook'
ACCOUNT_COOKIE_SALT = 'acook_salt'

SOURCE_COOKIE = 'jusrc'

RESERVED_USERNAMES = [
    'campaign'
    'org',
    'orgname',
    'issue',
    'issuename',
    'user',
    'json',
    'about',
    'staff',
    'jumo',
    'faq',
    'blog',
    'jobs',
    'terms',
    'privacy',
    'login',
    'logout',
    'setup',
    'story',
    'publisher',
    'health_check',
    'email_test',
    'email',
    'error',
    'login',
    'logout',
    'forgot_password',
    'reset_password',
    'settings',
    'donate',
    'admin',
    'grappelli',
]

########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings

def general(request):
    return {
        'settings' : settings,
        'user' : request.user,
        'request' : request,
    }

########NEW FILE########
__FILENAME__ = country_field
from django.utils.translation import ugettext as _
from django.db import models

# http://djangosnippets.org/snippets/1476/
# ISO 3166-1 country names and codes adapted from http://opencountrycodes.appspot.com/python/
COUNTRIES = (
    ('US', _('United States')),
    ('GB', _('United Kingdom')),
    ('AF', _('Afghanistan')),
    ('AX', _('Aland Islands')),
    ('AL', _('Albania')),
    ('DZ', _('Algeria')),
    ('AS', _('American Samoa')),
    ('AD', _('Andorra')),
    ('AO', _('Angola')),
    ('AI', _('Anguilla')),
    ('AQ', _('Antarctica')),
    ('AG', _('Antigua and Barbuda')),
    ('AR', _('Argentina')),
    ('AM', _('Armenia')),
    ('AW', _('Aruba')),
    ('AU', _('Australia')),
    ('AT', _('Austria')),
    ('AZ', _('Azerbaijan')),
    ('BS', _('Bahamas')),
    ('BH', _('Bahrain')),
    ('BD', _('Bangladesh')),
    ('BB', _('Barbados')),
    ('BY', _('Belarus')),
    ('BE', _('Belgium')),
    ('BZ', _('Belize')),
    ('BJ', _('Benin')),
    ('BM', _('Bermuda')),
    ('BT', _('Bhutan')),
    ('BO', _('Bolivia')),
    ('BA', _('Bosnia and Herzegovina')),
    ('BW', _('Botswana')),
    ('BV', _('Bouvet Island')),
    ('BR', _('Brazil')),
    ('IO', _('British Indian Ocean Territory')),
    ('BN', _('Brunei Darussalam')),
    ('BG', _('Bulgaria')),
    ('BF', _('Burkina Faso')),
    ('BI', _('Burundi')),
    ('KH', _('Cambodia')),
    ('CM', _('Cameroon')),
    ('CA', _('Canada')),
    ('CV', _('Cape Verde')),
    ('KY', _('Cayman Islands')),
    ('CF', _('Central African Republic')),
    ('TD', _('Chad')),
    ('CL', _('Chile')),
    ('CN', _('China')),
    ('CX', _('Christmas Island')),
    ('CC', _('Cocos (Keeling) Islands')),
    ('CO', _('Colombia')),
    ('KM', _('Comoros')),
    ('CG', _('Congo')),
    ('CD', _('Congo, The Democratic Republic of the')),
    ('CK', _('Cook Islands')),
    ('CR', _('Costa Rica')),
    ('CI', _('Cote d\'Ivoire')),
    ('HR', _('Croatia')),
    ('CU', _('Cuba')),
    ('CY', _('Cyprus')),
    ('CZ', _('Czech Republic')),
    ('DK', _('Denmark')),
    ('DJ', _('Djibouti')),
    ('DM', _('Dominica')),
    ('DO', _('Dominican Republic')),
    ('EC', _('Ecuador')),
    ('EG', _('Egypt')),
    ('SV', _('El Salvador')),
    ('GQ', _('Equatorial Guinea')),
    ('ER', _('Eritrea')),
    ('EE', _('Estonia')),
    ('ET', _('Ethiopia')),
    ('FK', _('Falkland Islands (Malvinas)')),
    ('FO', _('Faroe Islands')),
    ('FJ', _('Fiji')),
    ('FI', _('Finland')),
    ('FR', _('France')),
    ('GF', _('French Guiana')),
    ('PF', _('French Polynesia')),
    ('TF', _('French Southern Territories')),
    ('GA', _('Gabon')),
    ('GM', _('Gambia')),
    ('GE', _('Georgia')),
    ('DE', _('Germany')),
    ('GH', _('Ghana')),
    ('GI', _('Gibraltar')),
    ('GR', _('Greece')),
    ('GL', _('Greenland')),
    ('GD', _('Grenada')),
    ('GP', _('Guadeloupe')),
    ('GU', _('Guam')),
    ('GT', _('Guatemala')),
    ('GG', _('Guernsey')),
    ('GN', _('Guinea')),
    ('GW', _('Guinea-Bissau')),
    ('GY', _('Guyana')),
    ('HT', _('Haiti')),
    ('HM', _('Heard Island and McDonald Islands')),
    ('VA', _('Holy See (Vatican City State)')),
    ('HN', _('Honduras')),
    ('HK', _('Hong Kong')),
    ('HU', _('Hungary')),
    ('IS', _('Iceland')),
    ('IN', _('India')),
    ('ID', _('Indonesia')),
    ('IR', _('Iran, Islamic Republic of')),
    ('IQ', _('Iraq')),
    ('IE', _('Ireland')),
    ('IM', _('Isle of Man')),
    ('IL', _('Israel')),
    ('IT', _('Italy')),
    ('JM', _('Jamaica')),
    ('JP', _('Japan')),
    ('JE', _('Jersey')),
    ('JO', _('Jordan')),
    ('KZ', _('Kazakhstan')),
    ('KE', _('Kenya')),
    ('KI', _('Kiribati')),
    ('KP', _('Korea, Democratic People\'s Republic of')),
    ('KR', _('Korea, Republic of')),
    ('KW', _('Kuwait')),
    ('KG', _('Kyrgyzstan')),
    ('LA', _('Lao People\'s Democratic Republic')),
    ('LV', _('Latvia')),
    ('LB', _('Lebanon')),
    ('LS', _('Lesotho')),
    ('LR', _('Liberia')),
    ('LY', _('Libyan Arab Jamahiriya')),
    ('LI', _('Liechtenstein')),
    ('LT', _('Lithuania')),
    ('LU', _('Luxembourg')),
    ('MO', _('Macao')),
    ('MK', _('Macedonia, The Former Yugoslav Republic of')),
    ('MG', _('Madagascar')),
    ('MW', _('Malawi')),
    ('MY', _('Malaysia')),
    ('MV', _('Maldives')),
    ('ML', _('Mali')),
    ('MT', _('Malta')),
    ('MH', _('Marshall Islands')),
    ('MQ', _('Martinique')),
    ('MR', _('Mauritania')),
    ('MU', _('Mauritius')),
    ('YT', _('Mayotte')),
    ('MX', _('Mexico')),
    ('FM', _('Micronesia, Federated States of')),
    ('MD', _('Moldova')),
    ('MC', _('Monaco')),
    ('MN', _('Mongolia')),
    ('ME', _('Montenegro')),
    ('MS', _('Montserrat')),
    ('MA', _('Morocco')),
    ('MZ', _('Mozambique')),
    ('MM', _('Myanmar')),
    ('NA', _('Namibia')),
    ('NR', _('Nauru')),
    ('NP', _('Nepal')),
    ('NL', _('Netherlands')),
    ('AN', _('Netherlands Antilles')),
    ('NC', _('New Caledonia')),
    ('NZ', _('New Zealand')),
    ('NI', _('Nicaragua')),
    ('NE', _('Niger')),
    ('NG', _('Nigeria')),
    ('NU', _('Niue')),
    ('NF', _('Norfolk Island')),
    ('MP', _('Northern Mariana Islands')),
    ('NO', _('Norway')),
    ('OM', _('Oman')),
    ('PK', _('Pakistan')),
    ('PW', _('Palau')),
    ('PS', _('Palestinian Territory, Occupied')),
    ('PA', _('Panama')),
    ('PG', _('Papua New Guinea')),
    ('PY', _('Paraguay')),
    ('PE', _('Peru')),
    ('PH', _('Philippines')),
    ('PN', _('Pitcairn')),
    ('PL', _('Poland')),
    ('PT', _('Portugal')),
    ('PR', _('Puerto Rico')),
    ('QA', _('Qatar')),
    ('RE', _('Reunion')),
    ('RO', _('Romania')),
    ('RU', _('Russian Federation')),
    ('RW', _('Rwanda')),
    ('BL', _('Saint Barthelemy')),
    ('SH', _('Saint Helena')),
    ('KN', _('Saint Kitts and Nevis')),
    ('LC', _('Saint Lucia')),
    ('MF', _('Saint Martin')),
    ('PM', _('Saint Pierre and Miquelon')),
    ('VC', _('Saint Vincent and the Grenadines')),
    ('WS', _('Samoa')),
    ('SM', _('San Marino')),
    ('ST', _('Sao Tome and Principe')),
    ('SA', _('Saudi Arabia')),
    ('SN', _('Senegal')),
    ('RS', _('Serbia')),
    ('SC', _('Seychelles')),
    ('SL', _('Sierra Leone')),
    ('SG', _('Singapore')),
    ('SK', _('Slovakia')),
    ('SI', _('Slovenia')),
    ('SB', _('Solomon Islands')),
    ('SO', _('Somalia')),
    ('ZA', _('South Africa')),
    ('GS', _('South Georgia and the South Sandwich Islands')),
    ('ES', _('Spain')),
    ('LK', _('Sri Lanka')),
    ('SD', _('Sudan')),
    ('SR', _('Suriname')),
    ('SJ', _('Svalbard and Jan Mayen')),
    ('SZ', _('Swaziland')),
    ('SE', _('Sweden')),
    ('CH', _('Switzerland')),
    ('SY', _('Syrian Arab Republic')),
    ('TW', _('Taiwan, Province of China')),
    ('TJ', _('Tajikistan')),
    ('TZ', _('Tanzania, United Republic of')),
    ('TH', _('Thailand')),
    ('TL', _('Timor-Leste')),
    ('TG', _('Togo')),
    ('TK', _('Tokelau')),
    ('TO', _('Tonga')),
    ('TT', _('Trinidad and Tobago')),
    ('TN', _('Tunisia')),
    ('TR', _('Turkey')),
    ('TM', _('Turkmenistan')),
    ('TC', _('Turks and Caicos Islands')),
    ('TV', _('Tuvalu')),
    ('UG', _('Uganda')),
    ('UA', _('Ukraine')),
    ('AE', _('United Arab Emirates')),
    ('UM', _('United States Minor Outlying Islands')),
    ('UY', _('Uruguay')),
    ('UZ', _('Uzbekistan')),
    ('VU', _('Vanuatu')),
    ('VE', _('Venezuela')),
    ('VN', _('Viet Nam')),
    ('VG', _('Virgin Islands, British')),
    ('VI', _('Virgin Islands, U.S.')),
    ('WF', _('Wallis and Futuna')),
    ('EH', _('Western Sahara')),
    ('YE', _('Yemen')),
    ('ZM', _('Zambia')),
    ('ZW', _('Zimbabwe')),
)

class CountryField(models.CharField):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 2)
        kwargs.setdefault('choices', COUNTRIES)

        super(CountryField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return "CharField"

########NEW FILE########
__FILENAME__ = credit_card_fields
import re
from datetime import date
from calendar import monthrange, IllegalMonthError
from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

# from - https://github.com/bryanchow/django-creditcard-fields

CREDIT_CARD_RE = r'^(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|6(?:011|5[0-9][0-9])[0-9]{12}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|(?:2131|1800|35\\d{3})\d{11})$'
MONTH_FORMAT = getattr(settings, 'MONTH_FORMAT', '%b')
VERIFICATION_VALUE_RE = r'^([0-9]{3,4})$'


class CreditCardField(forms.CharField):
    """
    Form field that validates credit card numbers.
    """

    default_error_messages = {
        'required': _(u'Please enter a credit card number.'),
        'invalid': _(u'The credit card number you entered is invalid.'),
    }

    def clean(self, value):
        value = value.replace(' ', '').replace('-', '')
        if self.required and not value:
            raise forms.util.ValidationError(self.error_messages['required'])
        if value and not re.match(CREDIT_CARD_RE, value):
            raise forms.util.ValidationError(self.error_messages['invalid'])
        return value


class ExpiryDateWidget(forms.MultiWidget):
    """
    Widget containing two select boxes for selecting the month and year.
    """

    def decompress(self, value):
        return [value.month, value.year] if value else [None, None]

    def format_output(self, rendered_widgets):
        return u'<div class="expirydatefield">%s</div>' % ' '.join(rendered_widgets)


class ExpiryDateField(forms.MultiValueField):
    """
    Form field that validates credit card expiry dates.
    """

    default_error_messages = {
        'invalid_month': _(u'Please enter a valid month.'),
        'invalid_year': _(u'Please enter a valid year.'),
        'date_passed': _(u'This expiry date has passed.'),
    }

    def __init__(self, *args, **kwargs):
        today = date.today()
        error_messages = self.default_error_messages.copy()
        if 'error_messages' in kwargs:
            error_messages.update(kwargs['error_messages'])
        if 'initial' not in kwargs:
            # Set default expiry date based on current month and year
            kwargs['initial'] = today
        months = [(x, '%02d (%s)' % (x, date(2000, x, 1).strftime(MONTH_FORMAT))) for x in xrange(1, 13)]
        years = [(x, x) for x in xrange(today.year, today.year + 15)]
        fields = (
            forms.ChoiceField(choices=months, error_messages={'invalid': error_messages['invalid_month']}),
            forms.ChoiceField(choices=years, error_messages={'invalid': error_messages['invalid_year']}),
        )
        super(ExpiryDateField, self).__init__(fields, *args, **kwargs)
        self.widget = ExpiryDateWidget(widgets=[fields[0].widget, fields[1].widget])

    def clean(self, value):
        expiry_date = super(ExpiryDateField, self).clean(value)
        if date.today() > expiry_date:
            raise forms.ValidationError(self.error_messages['date_passed'])
        return expiry_date

    def compress(self, data_list):
        if data_list:
            try:
                month = int(data_list[0])
            except (ValueError, TypeError):
                raise forms.ValidationError(self.error_messages['invalid_month'])
            try:
                year = int(data_list[1])
            except (ValueError, TypeError):
                raise forms.ValidationError(self.error_messages['invalid_year'])
            try:
                day = monthrange(year, month)[1] # last day of the month
            except IllegalMonthError:
                raise forms.ValidationError(self.error_messages['invalid_month'])
            except ValueError:
                raise forms.ValidationError(self.error_messages['invalid_year'])
            return date(year, month, day)
        return None


class VerificationValueField(forms.CharField):
    """
    Form field that validates credit card verification values (e.g. CVV2).
    See http://en.wikipedia.org/wiki/Card_Security_Code
    """

    widget = forms.TextInput(attrs={'maxlength': 4})
    default_error_messages = {
        'required': _(u'Please enter the three- or four-digit verification code for your credit card.'),
        'invalid': _(u'The verification value you entered is invalid.'),
    }

    def clean(self, value):
        value = value.replace(' ', '')
        if not value and self.required:
            raise forms.util.ValidationError(self.error_messages['required'])
        if value and not re.match(VERIFICATION_VALUE_RE, value):
            raise forms.util.ValidationError(self.error_messages['invalid'])
        return value

########NEW FILE########
__FILENAME__ = decorators

from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from etc.constants import ACCOUNT_COOKIE_SALT, ACCOUNT_COOKIE
from etc.user import check_cookie
from etc.view_helpers import json_error

def PostOnly(viewfunc):
    """returns HttpResponseBadRequest if request is not a post"""
    def posted(*args, **kwargs):
        request = args[0]
        if request.method == 'POST':
            return viewfunc(*args, **kwargs)
        return HttpResponseBadRequest()
    return posted

def AjaxPostOnly(viewfunc):
    """returns HttpResponseBadRequest if request is not a post"""
    def posted(*args, **kwargs):
        request = args[0]
        if request.method == 'POST':
            return viewfunc(*args, **kwargs)
        return HttpResponseBadRequest(json_error('Post only.'))
    return posted

def SimpleAjaxPostOnly(viewfunc):
    def posted(*args, **kwargs):
        request = args[0]
        if request.method == 'POST':
            if 'query' in request.POST:
                return viewfunc(*args, **kwargs)
            else:
                return HttpResponseBadRequest(json_error('Query missing.'))
        else:
            return HttpResponseBadRequest(json_error('Post only.'))
    return posted

def AccountRequired(viewfunc):
    def posted(*args, **kwargs):
        request = args[0]
        if ACCOUNT_COOKIE in request.COOKIES and ACCOUNT_COOKIE_SALT in request.COOKIES:
            if check_cookie(request.COOKIES[ACCOUNT_COOKIE], request.COOKIES[ACCOUNT_COOKIE_SALT]):
                return viewfunc(*args, **kwargs)
            else:
                return HttpResponseRedirect('/login?redirect_to=%s' % request.path)
        else:
            return HttpResponseRedirect('/login?redirect_to=%s' % request.path)
    return posted

def NotLoggedInRequired(viewfunc):
    def posted(*args, **kwargs):
        request = args[0]
        if ACCOUNT_COOKIE in request.COOKIES and ACCOUNT_COOKIE_SALT in request.COOKIES:
            if check_cookie(request.COOKIES[ACCOUNT_COOKIE], request.COOKIES[ACCOUNT_COOKIE_SALT]):
                return HttpResponseRedirect('/')
            else:
                return viewfunc(*args, **kwargs)
        else:
            return viewfunc(*args, **kwargs)
    return posted

########NEW FILE########
__FILENAME__ = entities
from users.models import User
from org.models import Org
from issue.models import Issue
import re
from etc.func import slugify
from etc.constants import RESERVED_USERNAMES

def create_handle(name):
    if isinstance(name, unicode):
        handle = slugify(name)[:25]
    elif isinstance(name, str):
        handle = slugify(unicode(name, 'utf-8'))[:25]
    else:
        raise Exception('Name must be instance of basestring')

    working = True
    found = False
    while working:
        try:
            test = User.objects.get(username = handle)
            found = True
        except Exception, inst:
            pass
        try:
            test = Org.objects.get(handle = handle)
            found = True
        except Exception, inst:
            pass

        if handle in RESERVED_USERNAMES:
            found = True

        if found:
            found = False
            handle = '%s_' % handle
            continue
        else:
            working = False
            break
    return handle


class EntityTypes:
    ORG = 'org'
    ISSUE = 'issue'
    USER = 'user'

_entity_types_to_models = {EntityTypes.ORG: Org,
                           EntityTypes.ISSUE: Issue,
                           EntityTypes.USER: User,
                         }

_models_to_entity_types = {Org: EntityTypes.ORG,
                           Issue: EntityTypes.ISSUE,
                           User: EntityTypes.USER,
                         }

def class_to_type(cls):
    return _models_to_entity_types.get(cls)

def obj_to_type(obj):
    return _models_to_entity_types.get(obj.__class__)

def type_to_class(type):
    return _entity_types_to_models.get(type)

def register_entity(type, entity):
    _models_to_entity_types[entity] = type
    _entity_types_to_models[type] = entity

########NEW FILE########
__FILENAME__ = errors

########NEW FILE########
__FILENAME__ = func
# -*- coding: utf8 -*-

import re
from unidecode import unidecode
import os, sys
from hashlib import md5 as hasher
import binascii
import settings


def gen_flattened_list(iterables):
    for item in iterables:
        if hasattr(item, '__iter__'):
            for i in item:
                yield i
        else:
            yield item

def crc32(val):
    return binascii.crc32(val) & 0xffffffff

# brennan added this
def wrap(text, width):
    """
    A word-wrap function that preserves existing line breaks
    and most spaces in the text. Expects that existing line
    breaks are posix newlines (\n).
    """
    return reduce(lambda line, word, width=width: '%s%s%s' %
                  (line,
                   ' \n'[(len(line)-line.rfind('\n')-1
                          + len(word.split('\n',1)[0]
                                ) >= width)],
                   word),
                  text.split(' ')
                  )

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.;:]+')

htmlCodes = (
    ('&amp;', '&'),
    ('&lt;', '<'),
    ('&gt;', '>'),
    ('&quot;', '"'),
    ('&#39;', "'"),
)

def escape_html(s):
    for bad, good in htmlCodes:
        s = s.replace(bad, good)
    return s

def slugify(text, delim='', lowercase=True):
    """ex: slugify(u'Шамиль Абетуллаев','')
    returns u'shamilabetullaev'"""
    text = escape_html(text)
    result = []
    if lowercase:
        text=text.lower()
    for word in _punct_re.split(text):
        decoded = _punct_re.split(unidecode(word))
        result.extend(decoded)
    result = unicode(delim.join(result))
    return result.lower() if lowercase else result


def salted_hash(val):
    hash = hasher(settings.CRYPTO_SECRET)
    hash.update(unicode(val, 'utf-8') if isinstance(val, str) else unicode(val))
    return hash.hexdigest()

########NEW FILE########
__FILENAME__ = gfk_manager
from django.db.models import Manager
from django.db.models.query import QuerySet
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey

# Adapted from django snippet 1773: http://djangosnippets.org/snippets/1773/
# Use this manager to eager load generic relations in 1 batch per content type (rather than n+1)
# Example: Model.objects.filter(...).fetch_generic_relations()

class GFKManager(Manager):
    def get_query_set(self):
        return GFKQuerySet(self.model)

class GFKQuerySet(QuerySet):
    def fetch_generic_relations(self):
        qs = self._clone()

        gfk_fields = [g for g in self.model._meta.virtual_fields if isinstance(g, GenericForeignKey)]

        ct_map = {}
        item_map = {}
        data_map = {}

        for item in qs:
            for gfk in gfk_fields:
                ct_id_field = self.model._meta.get_field(gfk.ct_field).column
                ct_id = getattr(item, ct_id_field)
                obj_id = getattr(item, gfk.fk_field)
                ct_map.setdefault(ct_id, []).append(obj_id)
            item_map[item.id] = item

        for ct_id, obj_ids in ct_map.iteritems():
            if ct_id:
                ct = ContentType.objects.get_for_id(ct_id)
                for o in ct.model_class().objects.select_related().filter(id__in=obj_ids).all():
                    data_map[(ct_id, o.id)] = o

        for item in qs:
            for gfk in gfk_fields:
                obj_id = getattr(item, gfk.fk_field)
                if obj_id != None:
                    ct_id_field = self.model._meta.get_field(gfk.ct_field).column
                    ct_id = getattr(item, ct_id_field)
                    setattr(item, gfk.name, data_map[(ct_id, obj_id)])

        return qs

########NEW FILE########
__FILENAME__ = profilejenkins
from django_jenkins.management.commands import jenkins
try:
    import cProfile as profile
except ImportError:
    import profile
import pstats

class Command(jenkins.Command):
    def handle(self, *test_labels, **options):
        profile.runctx('super(Command, self).handle(*test_labels, **options)',
                       {},
                       {'Command': Command, 'self': self, 'test_labels': test_labels, 'options': options},
                       'reports/jenkins.profile',
                       )
        p = pstats.Stats('reports/jenkins.profile')
        p.strip_dirs().sort_stats('cumulative')
        p.print_stats()

########NEW FILE########
__FILENAME__ = testserver
from django.core.management.base import BaseCommand
from optparse import make_option

from test.test_runner import JumoTestSuiteRunner

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--addrport', action='store', dest='addrport',
            type='string', default='',
            help='port number or ipaddr:port to run the server on'),
    )
    help = 'Runs a development server with data from the given fixture(s).'
    args = '[fixture ...]'

    requires_model_validation = False

    def handle(self, *fixture_labels, **options):
        from django.core.management import call_command
        #from django.db import connection
        from django.db import connections

        verbosity = int(options.get('verbosity', 1))
        addrport = options.get('addrport')

        #Not sure why django devs do this different than the test command
        #but using the same technique works for us.
        jtsr = JumoTestSuiteRunner()
        (old_names, mirrors) = jtsr.setup_databases()
        for db_data in old_names:
            print "Loading Fixture Data Into %s" % db_data[0].settings_dict["NAME"]
            call_command('loaddata', *fixture_labels, **{'verbosity': verbosity, "database":db_data[0].alias})

        # Create a test database.
        #db_name = connection.creation.create_test_db(verbosity=verbosity)

        # Import the fixture data into the test database.
        #call_command('loaddata', *fixture_labels, **{'verbosity': verbosity})

        # Run the development server. Turn off auto-reloading because it causes
        # a strange error -- it causes this handle() method to be called
        # multiple times.
        #shutdown_message = '\nServer stopped.\nNote that the test database, %r, has not been deleted. You can explore it on your own.' % db_name
        shutdown_message = '\nServer stopped.\nNote that the test databases have not been deleted. You can explore it on your own.'
        call_command('runserver', addrport=addrport, shutdown_message=shutdown_message, use_reloader=False)



########NEW FILE########
__FILENAME__ = middleware
from cStringIO import StringIO
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site
from django.core.urlresolvers import resolve, reverse
from django.db import connections
from django.http import Http404, HttpResponseRedirect, HttpResponsePermanentRedirect, get_host
from etc import cache
from etc.constants import ACCOUNT_COOKIE_SALT, ACCOUNT_COOKIE, SOURCE_COOKIE
from etc.user import check_cookie
import logging, os, sys, tempfile
import logging.handlers
import re
from users.models import User
from urlparse import urlsplit, urlunsplit

class DetectUserMiddleware(object):
    def process_request(self, request):
        if ACCOUNT_COOKIE in request.COOKIES and ACCOUNT_COOKIE_SALT in request.COOKIES:
            if check_cookie(request.COOKIES[ACCOUNT_COOKIE], request.COOKIES[ACCOUNT_COOKIE_SALT]):
                try:
                    request.user = cache.get(User, int(request.COOKIES[ACCOUNT_COOKIE]))
                    return None
                except:
                    pass

        request.user = AnonymousUser()
        return None

class AddExceptionMessageMiddleware(object):
    def process_exception(self, request, exception):
        request.exception = exception
        return None

class ConsoleExceptionMiddleware(object):
    """from http://www.djangosnippets.org/snippets/420/"""
    def process_exception(self, request, exception):
        # only process if we are in debug mode and this isn't a vanilla 404.
        if settings.DEBUG and not isinstance(exception, Http404):
            import traceback
            import sys
            exc_info = sys.exc_info()
            print "######################## Exception #############################"
            print '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
            print "################################################################"
            if getattr(settings, 'CONSOLE_MIDDLEWARE_DEBUGGER', False):
                # stop in the debugger with an exception post-mortem
                import pdb
                pdb.post_mortem(exc_info[2])

class MultipleProxyMiddleware(object):
    FORWARDED_FOR_FIELDS = [
        'HTTP_X_FORWARDED_FOR',
        'HTTP_X_FORWARDED_HOST',
        'HTTP_X_FORWARDED_SERVER',
    ]

    def process_request(self, request):
        """
        Rewrites the proxy headers so that only the most
        recent proxy is used.
        """
        for field in self.FORWARDED_FOR_FIELDS:
            if field in request.META:
                if ',' in request.META[field]:
                    parts = request.META[field].split(',')
                    request.META[field] = parts[-1].strip()

class LogExceptions(object):
    def __init__(self):
        log_file = getattr(settings, 'EXCEPTION_LOG_LOCATION', '/cloud/logs/django-exception-log')

        if not log_file:
            self.logger = None
            return

        log_file = log_file + '-' + str(os.getpid())

        self.logger = logging.getLogger('DjangoExceptionLogger')
        self.logger.setLevel(logging.ERROR)
        handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=1024*1024*20, backupCount=5)
        self.logger.addHandler(handler)

    def process_exception(self, request, exception):
        if not self.logger or isinstance(exception, Http404):
            return

        self.logger.error(
              "***************************************************\n"
              "Timestamp: %s\n"
              "Exception encountered in django request:\n\t %s \n"
              "GET params: %s\n"
              "POST params: %s\n"
              "Exception %s\n"
              "Message: %s\n"
              "Traceback: \n %s\n\n"
              "***************************************************\n",
              time.strftime("%Y-%m-%d %H:%M:%S"),
              request.get_full_path(),
              request.GET,
              request.POST,
              exception.__class__.__name__,
              getattr(exception, 'message', ''),
              traceback.format_exc()
         )


def secure(func):
    """ Decorator for secure views. """
    def _secure(*args, **kwargs):
        return func(*args, **kwargs)
    _secure.is_secure = True
    _secure.__name__ = func.__name__
    return _secure


HREF_PATTERN = re.compile(r"""(?P<attribute>href|src)\s*=\s*["'](?P<url>[^"']+)["']""", re.IGNORECASE)
class SSLMiddleware(object):

    def process_view(self, request, view_func, view_args, view_kwargs):
        is_secure = "https" == request.META.get("HTTP_X_FORWARDED_PROTO", "http")
        needs_secure = self._resolves_to_secure_view(request.path)
        if needs_secure != is_secure and not settings.IGNORE_HTTPS:
            return self._redirect(request, needs_secure)
        return None

    def process_response(self, request, response):
        if response['Content-Type'].find('html') >= 0:
            protocol = request.META.get("HTTP_X_FORWARDED_PROTO", "http")
            #Only deal with https.
            if protocol == "http":
                return response

            def rewrite_url(match):
                attribute = match.groupdict()["attribute"]
                split_url = urlsplit(match.groupdict()["url"])
                if split_url.scheme == 'javascript' and request.path.startswith(reverse('admin:index')):
                    return '%s="%s"' % (attribute, split_url.geturl())
                host = split_url.netloc if split_url.netloc else settings.HTTP_HOST
                request_path = request.path if request.path and request.path[-1] != "/" else request.path[:-1]
                path = split_url.path if split_url.path and split_url.path[0] == "/" else "%s/%s" % (request_path, split_url.path)
                new_url = urlunsplit((protocol, host, path, split_url[3],split_url[4]))
                return '%s="%s"' % (attribute, new_url)
            try:
                decoded_content = response.content.decode('utf-8')
            except UnicodeDecodeError:
                decoded_content = response.content
            response.content = \
                HREF_PATTERN.sub(rewrite_url, decoded_content).encode('utf-8')
        return response

    def _redirect(self, request, needs_secure):
        protocol = needs_secure and "https" or "http"
        new_url = self._add_protocol(request, protocol)
        if settings.DEBUG and request.method == "POST":
            raise RuntimeError, "CAN'T REDIRECT SSL WITH POST DATA!!"
        return HttpResponseRedirect(new_url)

    def _add_protocol(self, request, protocol):
        return "%s://%s%s" % (protocol, get_host(request), request.get_full_path())

    def _resolves_to_secure_view(self, url):
        try:
            view_func, args, kwargs = resolve(url)
        except:
            return None
        else:
            return getattr(view_func, 'is_secure', False)


class TerminalLogging:
    def process_response(self, request, response):
        from sys import stdout
        if stdout.isatty():
            for query in connections['default'].queries :
                print "\033[1;31m[%s]\033[0m \033[1m%s\033[0m" % (query['time'],
 " ".join(query['sql'].split()))
        return response

class SourceTagCollectionMiddleware:
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.GET.has_key('src'):      # This is a QueryDict, so src can be multiple GET params
            url_params = request.GET.copy() # Immutable
            sources = url_params.pop('src')
            new_qs = url_params.urlencode()
            redirect = HttpResponseRedirect('%s?%s' % (request.path, new_qs))
            redirect.set_cookie(SOURCE_COOKIE, request.GET.urlencode())
            return redirect
        return None

########NEW FILE########
__FILENAME__ = disqus_tags
from django import template
from django.conf import settings
from lib.disqus import get_sso_auth

from issue.models import Issue
from org.models import Org
from users.models import User

'''
        required context for template:
            # general disqus config
            forum_shortname (settings)
            dev_mode (settings)
            
            # page/thread specific
            thread_uid <settings.dev_mode>_<entity.type>_<entity.id>
            thread_ref_url # needs to be full qualified url
            thread_title
            
            # sso auth
            public_api_key (settings)
            sso_auth_msg (lib/disqus.get_sso_auth_msg)
            
            # sso display
            login_url
            logout_url
            small_logo_img
            sign_in_img
'''
register = template.Library()

@register.inclusion_tag("disqus/comment_thread.html", takes_context=True)
def disqus_comment_thread(context):    
    user = context['user']
    entity = context['entity']
    
    # add all the context needed for thread display code
    context['forum_name'] = settings.DISQUS_FORUM_NAME
    context['dev_mode'] = settings.DISQUS_DEV_MODE
    context['thread_uid'] = get_entity_thread_uid(entity)
    context['thread_ref_url'] = 'http://www.jumo.com%s' % (entity.get_url) 
    context['thread_title'] = '%s' % (entity.get_name)
    context['public_api_key'] = settings.DISQUS_PUBLIC_KEY
    context['sso_auth_msg'] = get_sso_auth( user )
    context['login_url'] = '/login?post_auth_action=close'
    context['logout_url'] = '/logout' # note, might need redirect to same page
    context['small_logo_img'] = 'favicon.png'
    context['sign_in_img'] = 'img/login.png'
    
    return context
    
@register.inclusion_tag("disqus/comment_count.html", takes_context=True)
def disqus_comment_count(context):
    entity = context['entity']
    
    # add all the context needed for comment count display code
    context['forum_name'] = settings.DISQUS_FORUM_NAME
    context['thread_uid'] = get_entity_thread_uid(entity)    
    
    return context


def get_entity_thread_uid(entity):
    entity_type = None
    if isinstance(entity, Issue):
        entity_type = 'issue'
    elif isinstance(entity, Org):
        entity_type = 'org'
    elif isinstance(entity, User):
        entity_type = 'user'
    
    # note: prefix comment thread unique id's in dev environments to
    # avoid conflicts with production threads
    devprefix = ''
    if settings.DISQUS_DEV_MODE == 1:
        devprefix = 'dev_'
    
    return '%s%s_%s' % (devprefix, entity_type, entity.id)

########NEW FILE########
__FILENAME__ = tags
from django import template
from django.conf import settings
try:
    import simplejson as json
except ImportError:
    import json

from etc.view_helpers import json_encode as _json_encode
from etc.view_helpers import render_string
from etc.func import wrap
#from textwrap import wrap << this thing is SO DUMB
from django.template.loader import render_to_string

from django.utils.encoding import force_unicode # brennan imported these for text truncation
from django.utils.functional import allow_lazy
from django.template.defaultfilters import stringfilter
register = template.Library()


@register.simple_tag
def url_target_blank(text):
    return text.replace('<a ', '<a target="_blank" ')
url_target_blank = register.filter(url_target_blank)
url_target_blank.is_safe = True

@register.simple_tag
def url_sans_http(text):
    return text.replace('>http://', '>').replace('>www.', '>').replace('.com/<', '.com<').replace('.org/<', '.org<')
url_sans_http = register.filter(url_sans_http)
url_sans_http.is_safe = True

def _create_static_url(token):
    return '%s/static%s%s?v=%s' % (
                                      settings.STATIC_URL,
                                      ('' if token[0] == '/' else '/'),
                                      token,
                                      settings.ASSET_HASH
                                  )

def contains(value, arg):
    return arg in value
register.filter('contains', contains)

@register.simple_tag
def get_fb_storyid(fb_story_id):
    if fb_story_id.find('_'):
        return fb_story_id.split('_')[1]
    return fb_story_id

@register.simple_tag
def static_url(token):
    return _create_static_url(token)

@register.simple_tag
def full_url(url):
    return "http://%s%s" % (settings.HTTP_HOST, url)

@register.simple_tag
def get_humanized_type(text):
    if text:
        ty = text.lower()
        if ty == "org":
            return "Organizations"
        elif ty == "user":
            return "People"
        elif ty == "issue":
            return "Issues"
    return text

@register.simple_tag
def json_encode(obj):
    return _json_encode(obj)

@register.simple_tag
def possessive(value):
    """
    Returns a possessive form of a name according to English rules
    Mike returns Mike's, while James returns James'
    """
    if value[-1] == 's':
        return "%s'" % value
    return "%s's" % value


def truncate_chars(s, num):
    """
    Template filter to truncate a string to at most num characters respecting word
    boundaries.
    """
    s = force_unicode(s)
    length = int(num)
    if len(s) > length:
        length = length - 3
        if s[length-1] == ' ' or s[length] == ' ':
            s = s[:length].strip()
        else:
            words = s[:length].split()
            if len(words) > 1:
                del words[-1]
            s = u' '.join(words)
        s += '...'
    return s
truncate_chars = allow_lazy(truncate_chars, unicode)

def truncatechars(value, arg):
    """
    Truncates a string after a certain number of characters, but respects word boundaries.

    Argument: Number of characters to truncate after.
    """
    try:
        length = int(arg)
    except ValueError: # If the argument is not a valid integer.
        return value # Fail silently.
    return truncate_chars(value, length)
truncatechars.is_safe = True
truncatechars = stringfilter(truncatechars)

register.filter(truncatechars)



# @register.filter("truncate_chars")
# def truncate_chars(value, max_length):
#         if len(value) <= max_length:
#                     return value

#         truncd_val = value[:max_length]
#         if value[max_length] != " ":
#             rightmost_space = truncd_val.rfind(" ")
#             if rightmost_space != -1:
#                 truncd_val = truncd_val[:rightmost_space]

#         return truncd_val + "..."



@register.filter
def partition(my_list, n):
    '''
    Partitions a list into sublists, each with n (or fewer) elements.
    my_list = [1,2,3,4,5]
    partion(my_list, 2) => [[1,2],[3,4],[5]]
    '''

    try:
        n = int(n)
        my_list = list(my_list)
    except ValueError:
        return [my_list]
    return [my_list[i:i+n] for i in range(0, len(my_list), n)]

########NEW FILE########
__FILENAME__ = tests
from data.gen_fixtures import BASIC_USER as FIXTURE_USER, NON_FB_USER as NON_FB_FIXTURE_USER
from django.core.urlresolvers import reverse
from django.test import TestCase

STAFF_USER = {'email':'nick@jumo.com', 'pwd':'tester01'}
BASIC_USER = {'email':FIXTURE_USER['email'], 'pwd':FIXTURE_USER['password']}
NON_FB_USER = {'email':NON_FB_FIXTURE_USER['email'], 'pwd':NON_FB_FIXTURE_USER['password']}
BASE_TEST_USER = 'nick@jumo.com'
BASE_TEST_PASS = 'tester01'

class JumoBaseTestCase(TestCase):
    pass

class ViewsBaseTestCase(JumoBaseTestCase):
    def login(self, user=STAFF_USER):
        redirect_to = "/"
        response = self.client.post("/login", data={"username":user['email'], "password":user['pwd'], "redirect_to":redirect_to})
        self.assertRedirects(response, redirect_to)

    def logout(self):
        redirect_to = reverse('index')
        response = self.client.get("/logout")
        self.assertRedirects(response, redirect_to)

    def basic_200_test(self, end_point, expected_template):
        response = self.client.get(end_point)
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 0)
        self.assertTemplateUsed(response, expected_template)

    def basic_404_test(self, end_point):
        response = self.client.get(end_point)
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'errors/error.html')

    def basic_500_test(self, end_point):
        response = self.client.get(end_point)
        self.assertEqual(response.status_code, 500)
        self.assertTemplateUsed(response, 'errors/error.html')

    def login_redirect_test(self, end_point, login=False):
        response = self.client.get(end_point)
        self.assertRedirects(response, "/login?redirect_to=%s" % end_point)
        if login: self.login()

    def form_succeeds_test(self, end_point, post_data, expected_template):
        response = self.client.post(end_point, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 0)
        self.assertTemplateUsed(response, expected_template)

    def form_fails_test(self, end_point, post_data, form_name, expected_template):
        #NOTE: assertFormError was dumb.
        #Also not sure if I like the fom_name thing...that was stole from django example.
        response = self.client.post(end_point, post_data)
        if form_name not in response.context:
            self.fail("The form '%s' was not used to render the response for %s" % (form_name, end_point))
        self.assertFalse(response.context[form_name].is_valid())
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 0)
        self.assertTemplateUsed(response, expected_template)

########NEW FILE########
__FILENAME__ = user

from datetime import datetime
from django.conf import settings
from django.core.cache import cache
from etc import errors, constants
import hashlib
from hashlib import sha256
from hmac import HMAC
import random

NUM_ITERATIONS = 1000

''' HELPER FUNCTIONS '''

def create_salt_cookie(user_id):
    salty = '%s%s' % (user_id, settings.SECRET_KEY)
    h = hashlib.sha1()
    h.update(salty)
    return h.hexdigest()

def check_cookie(user_id, salt):
    test = create_salt_cookie(user_id)
    if test == salt:
        return True
    return False


def hash_password(plain_password):
    salt = _random_bytes(8)
    hashed_password = _pbkdf_sha256(plain_password, salt)
    return salt.encode("base64").strip()+","+hashed_password.encode("base64").strip()


def check_password(saved_password, plain_password):
    salt, hashed_password = saved_password.split(",")
    salt = salt.decode("base64")
    hashed_password = hashed_password.decode("base64")
    return hashed_password == _pbkdf_sha256(plain_password, salt)



def _pbkdf_sha256(password, salt, iterations=NUM_ITERATIONS):
    result = password.encode("utf-8")
    for i in xrange(iterations):
        result = HMAC(result, salt, sha256).digest()
    return result


def _random_bytes(num_bytes):
    return "".join(chr(random.randrange(256)) for i in xrange(num_bytes))

########NEW FILE########
__FILENAME__ = views
from datetime import datetime
from django.core.cache import cache as django_cache
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect, HttpResponseServerError, Http404
from django.views.decorators.cache import cache_page
from etc import cache
from etc.view_helpers import render, render_string, json_error
from issue.models import Issue
import logging
from org.models import Org
from popularity.models import Section, Sections, TopList
import random
import re
import settings
from users.forms import LoginForm
from users.models import User
from users.views import home
from discovery.models import DiscoveryMap

def throw_error(request):
    r = HttpResponseRedirect('/')
    l = dir(r)
    heh = request.get_host()
    a = b

def return_org(request, org):
    if request.user.is_authenticated():
        related_orgs = org.get_related_orgs_for_user(request.user)[:5]
    else:
        related_orgs = org.get_all_related_orgs[:5]

    is_allowed_to_edit = org.is_editable_by(request.user)

    return render(request, 'org/profile.html', {
        'entity' : org,
        'title' : org.name,
        'related_orgs' : related_orgs,
        'is_allowed_to_edit': is_allowed_to_edit,
    })

def return_issue(request, issue):
    return render(request, 'issue/profile.html', {
        'entity' : issue,
        'title' : issue.name,
    })

def return_user(request, user):
    return render(request, 'user/profile.html', {
        'entity' : user,
        'title' : user.get_name,
    })

def clean_url(request, handle):
    org_id = None
    issue_id = None
    user_id = None
    org = None
    issue = None
    user = None

    handle = re.sub(r'[^a-zA-Z0-9\-_]+', '', handle).lower()

    # try first for cache!
    org_id = django_cache.get(cache._cache_key(Org, handle))
    if org_id:
        org = django_cache.get(cache._cache_key(Org, org_id))
        if org:
            return return_org(request, org)

    issue_id = django_cache.get(cache._cache_key(Issue, handle))
    if issue_id:
        issue = django_cache.get(cache._cache_key(issue, handle))
        if issue:
            return return_issue(request, issue)

    user_id = django_cache.get(cache._cache_key(user, handle))
    if user_id:
        user = django_cache.get(cache._cache_key(user, handle))
        if user:
            return return_user(request, user)

    # try second for db!
    org = None
    issue = None
    user = None


    try:
        org = Org.objects.get(handle = handle)
        cache.put_on_handle(org, handle)
        return return_org(request, org)
    except Org.DoesNotExist:
        logging.error("Org Handle %s doesn't exist." % handle)
    except:
        logging.exception("Org Handler Exception")

    try:
        user = User.objects.get(username = handle, is_active = True)
        cache.put_on_handle(user, handle)
        return return_user(request, user)
    except User.DoesNotExist:
        logging.error("User Username %s doesn't exist." % handle)
    except:
        logging.exception("User Handler Exception")

    try:
        issue = Issue.objects.get(handle = handle)
        cache.put_on_handle(issue, handle)
        return return_issue(request, issue)
    except Issue.DoesNotExist:
        logging.error("Issue Handle %s doesn't exist." % handle)
    except:
        logging.exception("Issue Handler Exception")

    raise Http404

def about(request):
    return render(request, 'etc/about.html', {
            "title": "About"
            })

def blog(request):
    return render(request, 'etc/blog.html', {
            "title": "Jumo and GOOD Combine Forces to Create Content and Social Engagement Platform"
            })

def contact(request):
    return render(request, 'etc/contact.html', {
            "title": "Contact Us"
            })

def team(request):
    return render(request, 'etc/team.html', {
            "title": "Our Team"
            })

def help(request):
    return render(request, 'etc/help.html', {
            "title": "Help"
            })

def jobs(request):
    return render(request, 'etc/jobs.html', {
            "title": "Jobs"
            })

def privacy(request):
    return render(request, 'etc/privacy.html', {
            "title": "Privacy Policy"
            })

def terms(request):
    return render(request, 'etc/terms.html', {
            "title": "Terms of Service"
            })

def signed_out_home(request):
    lists = Section.get_lists(Sections.HOME)
    list_ids = [l.id for l in lists]
    top_lists = TopList.get_entities_for_lists(list_ids)

    top_categories, sub_category_groups, discovery_item_groups = DiscoveryMap.get_lists()

    return render(request, 'etc/home.html', {
            'title' : None,
            'login_form':LoginForm(),
            'top_categories': top_categories,
            'sub_category_groups': sub_category_groups,
            'discovery_item_groups': discovery_item_groups,
            'top_lists': top_lists
        })

#if not settings.DEBUG:
#    signed_out_home = cache_page(signed_out_home, 60*15)


def index(request):
    if request.user.id:
        return home(request)

    return signed_out_home(request)

def error_404(request):
    if request.is_ajax():
        exception = getattr(request, 'exception', None)
        return json_error(404, exception)

    return HttpResponseNotFound(render_string(request, 'errors/error.html', {
            }))

def error_500(request):
    if request.is_ajax():
        exception = getattr(request, 'exception', None)
        return json_error(500, exception)

    return HttpResponseServerError(render_string(request, 'errors/error.html', {
            }))

def health_check(request):
    return HttpResponse('')

########NEW FILE########
__FILENAME__ = view_helpers
from django.template import RequestContext
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template.loader import render_to_string
try:
    import simplejson as json
except:
    import json

import datetime
from decimal import Decimal
from django.core.serializers.json import DateTimeAwareJSONEncoder
from django.db.models import ImageField, FileField
from django.db.models import Model
from django.db.models.query import QuerySet
from django.utils.encoding import smart_unicode
from urllib import urlencode
import logging
from django.template import Template


from django.conf import settings

def json_response(obj, status_code=200):
    """returns a HttpResponse wrapped with a json dump of the obj"""
    return HttpResponse(json.dumps({'result' : obj}), mimetype='application/json', status=status_code)

def json_error(status_code, error=None):
    if isinstance(error, Exception):
        error = error.message
    return HttpResponse(error, status=status_code, mimetype='application/json')

def json_encode(data):
    def _any(data):
        ret = None
        if isinstance(data, list):
            ret = _list(data)
        elif isinstance(data, dict):
            ret = _dict(data)
        elif isinstance(data, Decimal):
            ret = str(data)
        elif isinstance(data, QuerySet):
            ret = _list(data)
        elif isinstance(data, Model):
            ret = _model(data)
        elif isinstance(data, basestring):
            ret = smart_unicode(data, encoding='utf-8')
            #ret = unicode(data.decode('utf-8'))
        elif isinstance(data, datetime.datetime):
            ret = str(data).replace(' ', 'T')
        elif isinstance(data, datetime.date):
            ret = str(data)
        elif isinstance(data, datetime.time):
            ret = "T" + str(data)
        else:
            ret = data
        return ret

    def _model(data):
        ret = {}
        for f in data._meta.fields:
            if isinstance(f, ImageField) or isinstance(f, FileField):
                ret[f.attname] = unicode(getattr(data, f.attname))
            else:
                ret[f.attname] = _any(getattr(data, f.attname))
        fields = dir(data.__class__) + ret.keys()
        add_ons = [k for k in dir(data) if k not in fields and k not in ('delete', '_state',)]
        for k in add_ons:
            ret[k] = _any(getattr(data, k))
        return ret

    def _list(data):
        ret = []
        for v in data:
            ret.append(_any(v))
        return ret

    def _dict(data):
        ret = {}
        for k,v in data.items():
            ret[k] = _any(v)
        return ret

    ret = _any(data)
    return json.dumps(ret, cls=DateTimeAwareJSONEncoder)


def render(request, template, variables = {}):
    return render_to_response(template, variables, context_instance = RequestContext(request))

def render_string(request, template, variables = {}):
    return render_to_string(template, variables, context_instance = RequestContext(request))

def render_inclusiontag(request, tag_string, tag_file, dictionary=None):
    dictionary = dictionary or {}
    context_instance = RequestContext(request)
    context_instance.update(dictionary)
    t = Template("{%% load %s %%}{%% %s %%}" % (tag_file, tag_string))
    return t.render(context_instance)

def url_with_qs(path, **kwargs):
    return "%s?%s" % (path, urlencode(kwargs))

########NEW FILE########
__FILENAME__ = admin
from cust_admin.views.main import ExtChangeList
from cust_admin.widgets import ForeignKeyToObjWidget
from django import forms
from django.contrib import admin
from etc import cache
from entity_items.admin import MediaItemInline, ActionInline, AdvocateInline, TimelineInline, CenterContentItemInline, LeftContentItemInline
from issue.models import Issue, IssueRelation
from org.models import Org


######## INLINES ########
class IssueChildrenInline(admin.TabularInline):
    model = IssueRelation
    extra = 0
    classes = ('collapse closed',)
    fields = ('child', 'relation_type',)
    fk_name = "parent"
    verbose_name = "Related Issue"
    verbose_name_plural = "Related Issues"

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'child':
            kwargs['widget'] = ForeignKeyToObjWidget(rel=IssueRelation._meta.get_field('child').rel)
        return super(IssueChildrenInline,self).formfield_for_dbfield(db_field,**kwargs)


######## MODEL FORM AND ADMIN ########
class IssueAdminForm(forms.ModelForm):
    class Meta:
        model = Issue
        widgets = {'location': ForeignKeyToObjWidget(rel=Issue._meta.get_field('location').rel),
                   'summary': forms.Textarea(),}
    class Media:
        js = ['cust_admin/js/widgets.js']
        css = {'all':('cust_admin/css/extend_admin.css',)}

class IssueAdmin(admin.ModelAdmin):
    #Issue List Page Values
    form=IssueAdminForm
    search_fields = ['name','handle']
    search_fields_verbose = ["Name",]
    list_display = ('name', 'date_updated', 'is_active', 'content_upgraded')
    list_filter = ('is_active', 'content_upgraded',)
    ordering = ('name',)

    def get_changelist(self, request, **kwargs):
        return ExtChangeList

    change_list_template = "cust_admin/change_list.html"

    #Issue Change Page Values
    fieldsets = (
        ('Issue Profile', {
            'fields': (
                ('is_active','content_upgraded'),
                ('name', 'handle',),
                'img_small_url', 'img_large_url','summary','location',
                ('date_created','date_updated',),
        )
        }),
    )

    readonly_fields = ['date_created','date_updated',]
    inlines = [CenterContentItemInline, LeftContentItemInline, MediaItemInline, TimelineInline, ActionInline, AdvocateInline, IssueChildrenInline]

    def save_model(self, request, obj, form, change):
        cache.bust(obj, update=False)
        super(self.__class__, self).save_model(request, obj, form, change)


admin.site.register(Issue,IssueAdmin)

########NEW FILE########
__FILENAME__ = models
from action.models import Action
from django.contrib.contenttypes import generic
from django.db import models
from entity_items.models import Advocate, ContentItem, MediaItem, TimelineItem
from etc import cache
from etc.templatetags.tags import _create_static_url
from lib.image_upload import ImageSize, ImageType, S3EnabledImageField
from users.models import User, Location
from commitment.models import Commitment

class Issue(models.Model):

    #Public Properties
    id = models.AutoField(db_column='issue_id', primary_key=True)
    name = models.CharField(max_length=50, unique=True, db_index = True)
    handle = models.CharField(max_length=60, unique=True, db_index = True)
    summary = models.CharField(max_length=255, blank=True)
    img_small_url = S3EnabledImageField(image_type=ImageType.ISSUE, image_size=ImageSize.SMALL, blank=True)
    img_large_url = S3EnabledImageField(image_type=ImageType.ISSUE, image_size=ImageSize.LARGE, blank=True)

    #Internal Properties
    is_active = models.BooleanField(default = True)
    content_upgraded = models.BooleanField(default = False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    #Relationship Properties
    content = generic.GenericRelation(ContentItem)
    actions = generic.GenericRelation(Action, related_name='issue_actions')
    advocates = generic.GenericRelation(Advocate)
    timeline = generic.GenericRelation(TimelineItem)
    media = generic.GenericRelation(MediaItem)
    location = models.ForeignKey(Location, null=True, blank=True)
    commitments = generic.GenericRelation(Commitment)

    #This is legacy property.  Old data still used but no new follows allowed.
    followers = models.ManyToManyField(User, related_name='followed_issues', through='UserToIssueFollow')
    children_issues = models.ManyToManyField('self', symmetrical = False, through='IssueRelation')

    class Meta:
        verbose_name = "Issue"
        verbose_name_plural = "Issues"
        db_table="issues"

    def __str__(self):
        return self.name

    def save(self):
        #Note: I want to move all this img stuff to the forms that set them...
        #not here on the model. This is a hack so we ensure the model id is
        #used in the filename.
        if not self.id and not self.img_large_url._committed:
            #most likely you need to watch small img too
            small_url_comm = self.img_url._committed
            self.img_small_url._committed = True
            self.img_large_url._committed = True
            super(Issue, self).save()
            self.img_large_url._committed = False
            self.img_small_url._committed = small_url_comm

        if not self.id and not self.img_small_url._committed:
            self.img_small_url._committed = True
            super(Issue, self).save()
            self.img_small_url._committed = False

        self.img_large_url.storage.inst_id = self.id
        self.img_small_url.storage.inst_id = self.id
        super(Issue, self).save()
        cache.bust(self)


    @models.permalink
    def get_absolute_url(self):
        return ('entity_url', [self.handle])

    @classmethod
    def get(cls, id, force_db=False):
        if force_db:
            issue = Issue.objects.get(id=id)
            cache.bust(issue)
            return issue
        return cache.get(cls, id)

    @classmethod
    def multiget(cls, ids, force_db=False):
        if force_db:
            return Issue.objects.filter(id__in=ids)
        return cache.get(cls, ids)


    @property
    def get_image_small(self):
        if self.img_small_url:
            return self.img_small_url.url
        return ''

    @property
    def get_image_large(self):
        if self.img_large_url:
            return self.img_large_url.url
        return ''

    @property
    def get_name(self):
        return self.name

    @property
    def get_url(self):
        return '/%s' % self.handle

    @property
    @cache.collection_cache('issue.Issue', '_get_related_geo_children')
    def get_related_geo_children(self):
        return [i.child for i in IssueRelation.objects.filter(parent=self, relation_type=IssueRelation.IssueRelationType.GEO)]

    @property
    @cache.collection_cache('issue.Issue', '_get_related_type_children')
    def get_related_type_children(self):
        return [i.child for i in IssueRelation.objects.filter(parent=self, relation_type=IssueRelation.IssueRelationType.TYPE)]

    @property
    @cache.collection_cache(Action, '_all_actions')
    def get_all_actions(self):
        return self.actions.all().order_by('rank')

    @property
    @cache.collection_cache(Advocate, '_all_advocates')
    def get_all_advocates(self):
        return self.advocates.all()

    @property
    @cache.collection_cache(TimelineItem, '_all_timeline_items')
    def get_all_timeline_items(self):
        return self.timeline.all().order_by('year')

    @property
    @cache.collection_cache(MediaItem, '_all_media_items')
    def get_all_media_items(self):
        return self.media.all().order_by('position')

    @property
    @cache.collection_cache(MediaItem, '_photo_media_items')
    def get_all_photos(self):
        return self.media.filter(media_type="photo").order_by('position')

    @property
    @cache.collection_cache(ContentItem, '_all_content')
    def get_all_content(self):
        return self.content.all().order_by('position')

    @property
    def get_left_section_content(self):
        return [item for item in self.get_all_content if item.section == ContentItem.ContentSection.LEFT]

    @property
    def get_center_section_content(self):
        return [item for item in self.get_all_content if item.section == ContentItem.ContentSection.CENTER]

    @property
    @cache.collection_cache(User, '_all_followers')
    def get_all_followers(self):
        commitments = self.commitments.active().select_related()
        return [c.user for c in commitments]

    @property
    def get_all_followers_ids(self):
        return self.usertoissuefollow_set.filter(following = True).values_list('user', flat=True)

    @property
    def get_num_followers(self):
        return self.commitments.active().count()

    @property
    def get_sample_followers(self):
        commitments = self.commitments.active()[:16].select_related()
        return [c.user for c in commitments]

    @property
    @cache.collection_cache('org.Org', '_all_orgs_working_in')
    def get_all_orgs_working_in(self):
        return [rel.org for rel in OrgIssueRelationship.objects.filter(issue = self).order_by('-org__is_vetted')]

    @property
    def get_sample_orgs_working_in(self):
        from org.models import OrgIssueRelationship
        return [rel.org for rel in OrgIssueRelationship.objects.filter(issue = self).order_by('-org__is_vetted')[:3]]

    @property
    def get_all_orgs_working_in_ids(self):
        return OrgIssueRelationship.objects.filter(issue = self).order_by('-org__is_vetted').values_list('org', flat=True)

    def delete(self):
        cache.bust_on_handle(self, self.handle, False)
        return super(self.__class__, self).delete()


class UserToIssueFollow(models.Model):
    following = models.BooleanField(default = True, db_index = True)
    started_following = models.DateTimeField(auto_now_add = True)
    stopped_following = models.DateTimeField(blank = True, null = True)
    user = models.ForeignKey(User)
    issue = models.ForeignKey(Issue)

    class Meta:
        unique_together = (("user", "issue"),)

    def __unicode__(self):
        return "User '%s' following Issue '%s'" % (self.user, self.issue)


class IssueRelation(models.Model):
    class IssueRelationType:
        GEO = 'geo'
        TYPE = 'type'
    ISSUE_RELATION_TYPE_CHOICES = (
        (IssueRelationType.GEO, "Geo"),
        (IssueRelationType.TYPE, "Type"),
    )

    id = models.AutoField(db_column='issue_relation_id', primary_key=True)
    child = models.ForeignKey(Issue, related_name='child_issue')
    parent = models.ForeignKey(Issue, related_name='parent_issue')
    relation_type = models.CharField(max_length=100, choices=ISSUE_RELATION_TYPE_CHOICES, default=IssueRelationType.GEO)

    class Meta:
        db_table = 'issue_relations'

########NEW FILE########
__FILENAME__ = tests


########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.http import HttpResponsePermanentRedirect, Http404
from issue.models import Issue
from users.models import User
from django.shortcuts import get_object_or_404
from etc.view_helpers import json_error, json_response, render_inclusiontag, render_string

def old_issuename_permalink(request, issuename):
    try:
        i = Issue.objects.get(name = issuename)
        return HttpResponsePermanentRedirect(reverse('entity_url', args=[i.handle]))
    except:
        raise Http404


def old_issue_permalink(request, mongo_id):
    try:
        i = Issue.objects.get(mongo_id = mongo_id)
        return HttpResponsePermanentRedirect(reverse('entity_url', args=[i.handle]))
    except:
        raise Http404

def followed_issue_list(request, user_id):
    start = int(request.GET.get('start', 0))
    end = int(request.GET.get('end', 20))
    user = get_object_or_404(User, id=user_id)
    issue_commitments = user.commitments.with_issues()[start:end].fetch_generic_relations()
    issues = [commitment.entity for commitment in issue_commitments]
    num_issues = user.commitments.with_issues().count()

    html = render_string(request, "issue/includes/followed_issue_list.html", {
        'issues': issues,
        'start_index': start,
    })

    return json_response({
        'html': html,
        'has_more': end < num_issues,
    })

########NEW FILE########
__FILENAME__ = config
'''
Created on Jan 19, 2011

@author: al
'''

from util import *

"""
  <updateHandler class="solr.DirectUpdateHandler2" />

  <requestDispatcher handleSelect="true" >
    <requestParsers enableRemoteStreaming="false" multipartUploadLimitInKB="2048" />
  </requestDispatcher>
  
  <requestHandler name="standard" class="solr.StandardRequestHandler" default="true" />
  <requestHandler name="/update" class="solr.XmlUpdateRequestHandler" />
  <requestHandler name="/admin/" class="org.apache.solr.handler.admin.AdminHandlers" />
      
  <!-- config for the admin interface --> 
  <admin>
    <defaultQuery>solr</defaultQuery>
  </admin>
"""

class BaseConfigElement(BaseSolrXMLElement):
    required = {'solr_class': 'class'}    

class MainIndex(SingleValueTagsMixin):
    tag = 'mainIndex'
    def __init__(self,
                 use_compound_file=None,
                 merge_factor=None,
                 max_buffered_docs=None,
                 max_merge_docs=None,
                 max_field_length=None):
        SingleValueTagsMixin.__init__(locals().pop('self'),**locals())

class AutoCommit(SingleValueTagsMixin):
    def __init__(self,
                 max_docs = None,
                 max_time = None
                 ):
        SingleValueTagsMixin.__init__(locals().pop('self'),**locals())

class MergePolicy(BaseSolrXMLElement):
    tag='mergePolicy'
    required = {'class': 'solr_class'}
    
    solr_class = None
    
class LogByteSizeMergePolicy(MergePolicy):
    solr_class = "org.apache.lucene.index.LogByteSizeMergePolicy"

class LogDocMergePolicy(MergePolicy):
    solr_class = "org.apache.lucene.index.LogDocMergePolicy"

class MergeScheduler(BaseSolrXMLElement):
    tag = "mergeScheduler"
    required = {'class': 'solr_class'}
    
    solr_class = None
    
class ConcurrentMergeScheduler(MergeScheduler):
    solr_class = "org.apache.lucene.index.ConcurrentMergeScheduler"
    
class SerialMergeScheduler(MergeScheduler):
    solr_class = "org.apache.lucene.index.SerialMergeScheduler"

class IndexDefaults(SingleValueTagsMixin):
    def __init__(self,
                 use_compound_file=None,
                 merge_factor=None,
                 max_buffered_docs=None,
                 ram_buffer_size=None,
                 max_field_length=None,
                 write_lock_timeout=None,
                 commit_lock_timout=None,
                 lock_type=None,
                 term_index_interval=None
              ):
        SingleValueTagsMixin.__init__(locals().pop('self'),**locals())

class RequestHandler(BaseSolrXMLElement):
    tag = "requestHandler"
    required={'solr_class': 'class', 'name': 'name'}

class DirectUpdateHandler(RequestHandler):
    name = '/update'
    solr_class = 'solr.DirectUpdateHandler2'
    
    auto_commit = None

class SearchHandler(RequestHandler):
    solr_class = "solr.SearchHandler"
    default = False

class StandardRequestHandler(RequestHandler):
    name = 'standard'
    solr_class = "solr.SearchHandler"

class DismaxRequestHandler(RequestHandler):
    name = 'dismax'
    solr_class = 'solr.SearchHandler'
    
class SolrConfig(SingleValueTagsMixin):
    tag = 'config'
    def __init__(self, **kw):
        SingleValueTagsMixin.__init__(self, **kw)
        
StandardSolrConfig = SolrConfig(lucene_match_version='LUCENE_40',
                                update_handler = DirectUpdateHandler,
                                standard = StandardRequestHandler)

DismaxSolrConfig = SolrConfig(lucene_match_version='LUCENE_40',
                              update_handler = DirectUpdateHandler,
                              dismax = DismaxRequestHandler
                              )
    
def generate_config(config, path = 'solr/conf/solrconfig.xml'):
    ensure_dir(os.path.dirname(path))
    
    tree = etree.ElementTree(config.to_xml())
    tree.write(path, encoding='utf-8', xml_declaration=True, pretty_print=True)
    
    
class SolrCore(BaseSolrXMLElement):
    tag='core'
    name = None
    instance_dir = None
    
    required = dict((attr, attr) for attr in ['name', 'instance_dir'])
    
    def __init__(self, name, instance_dir):
        self.name = name
        self.instance_dir = instance_dir 
    
class SolrCores(BaseSolrXMLElement):
    tag='cores'
    
    options = ['admin_path']
    admin_path='/admin/cores'
    
    def __init__(self, admin_path=None, cores=None):
        if admin_path:
            self.admin_path = admin_path
        self.cores = cores
    
class SolrMulticoreXML(BaseSolrXMLElement):
    tag = 'solr'
    persistent=False
    
    def __init__(self, solr_cores=SolrCores(admin_path='/admin/cores',
                                            cores=[SolrCore('core0', 'core0')]), persistent=None):
        super(SolrMulticoreXML, self).__init__(solr_cores=solr_cores, 
                                               persistent=persistent if persistent is not None else self.persistent)
    
def get_multicore_conf(**indexes):
    core_xml = SolrMulticoreXML(solr_cores=SolrCores(admin_path='/admin/cores',
                                                     cores=[SolrCore(name=index, instance_dir=index)
                                                            for index in indexes.keys()]
                                                     )
                                )
    return core_xml
    

def generate_multicore_schema(conf=None, path_root='solr/', **indexes):
    core_xml = conf or get_multicore_conf(**indexes)
    
    ensure_dir(os.path.dirname(path_root))
    
    
    tree = etree.ElementTree(core_xml.to_xml())
    tree.write(os.path.join(path_root, 'solr.xml'), encoding='utf-8', xml_declaration=True, pretty_print=True)

    for index, index_specs in indexes.iteritems():
        conf, schema = index_specs['config'], index_specs['schema']
        ensure_dir(os.path.join(path_root, index, 'conf'))
        xml_schema = etree.ElementTree(schema.to_xml())
        xml_schema.write(os.path.join(path_root, index, 'conf', 'schema.xml'), encoding='utf-8', xml_declaration=True, pretty_print=True)
        xml_conf = etree.ElementTree(conf.to_xml())
        xml_conf.write(os.path.join(path_root, index, 'conf', 'solrconfig.xml'), encoding='utf-8', xml_declaration=True, pretty_print=True)     
########NEW FILE########
__FILENAME__ = connection
'''
Created on Feb 18, 2011

@author: al
'''

import pysolr

_solr_conns = {}

class Bebop(object):
    def __init__(self, host, port, solr_dir='solr', id='main'):   
        self._solr = _solr_conns[id] = _solr_conns.get(id) or pysolr.Solr('http://%s:%s/%s/' % (host, port, solr_dir))
      
    @property
    def raw_conn(self):
        return _solr_conns[self.id]
              
    def search(self, query, id='main'):
        return self._solr.search(query)
    
    def add(self, doc, commit=True):
        self._solr.add(doc._to_solr_doc(),commit=commit)

    def batch_add(self, docs, commit=False):
        self._solr.add([doc._to_solr_doc() for doc in docs], commit=commit)
        
    def commit(self):
        self._solr.commit()
        
    def optimize(self):
        self._solr.optimize()
        
    def rollback(self):
        self._solr.rollback()
########NEW FILE########
__FILENAME__ = data_import
'''
Created on Mar 7, 2011

@author: al
'''

class BatchIndexer(object):
    def __init__(self, solr_conn, db_conn, index_query, batch_size=1000):
        self.batch_size = batch_size
        self.solr_conn = solr_conn
        self.db_conn = db_conn
        self._index_cursor = db_conn.cursor()
        self.index_query = index_query

    def exec_query(self):
        self._index_cursor.execute(self.index_query)
        
    def next_batch(self):
        self.batch = self._index_cursor.fetchmany(self.batch_size)
        return self.batch
        
    def index_batch(self, batch):
        self.solr_conn.add(batch)
        
    def index_all(self):
        count = 0
        while self.next_batch():
            count += 1
            print "Indexing batch", count
            self.index_batch(self.batch)
        
if __name__ == '__main__':
    import MySQLdb
    from MySQLdb import cursors
    import pysolr
    
    solr_conn = pysolr.Solr('http://localhost:8983/solr')
    solr_conn.delete(q="*:*")

    db_conn = MySQLdb.connect(host='localhost', user='root', db='test',
                              cursorclass=cursors.SSDictCursor
                              )
    
    indexer = BatchIndexer(solr_conn, db_conn, "select * from solr_test", batch_size=1000)
    print "Executing query..."
    indexer.exec_query()
    print "Running indexer..."
    indexer.index_all()
########NEW FILE########
__FILENAME__ = model
'''
Created on Jan 21, 2011

@author: al
'''

from connection import *
from schema import *
from config import *

def SearchIndex(name, config=StandardSolrConfig, generate_schema=True):
    def _Index(cls):
        cls.__index__ = name
        if not hasattr(cls, '_target') or cls._target is None:
            raise Exception('Class "%s" must have attribute _target' % cls.__name__)
        fields = filter(lambda attr: isinstance(getattr(cls,attr), Field), dir(cls))
        cls._fields = fields
        cls._models_to_solr = dict([(field, getattr(cls, field).name) for field in fields])
        cls._solr_to_models = dict([(v,k) for k,v in cls._models_to_solr.iteritems()])
        
        cls.schema=None
        if generate_schema:
            field_types=set()
            schema_fields=[]
            for attr in fields:
                schema_fields.append(getattr(cls, attr))
                field_types.add(getattr(cls,attr)._type)
                
            cls.schema=SolrSchema(name=name, 
                                  fields=SolrSchemaFields(*schema_fields),
                                  field_types=SolrFieldTypes(*field_types)
                                  )        
        cls.config=config
        return cls
    return _Index

class SearchableModel(object):
    _target = None
    
    @classmethod
    def _to_solr_doc(cls, obj):
        return dict([(v, getattr(obj, k)) for k, v in cls._models_to_solr.iteritems()])

    @classmethod
    def _create_target(cls, doc):
        return cls._target(**dict([(k, v) for k,v in cls._solr_to_models.iteritems()]))

class Field(SolrSchemaField):
    def __init__(self, name, type, multi_valued=None, indexed=None, stored=None, model_attr=None):     
        super(Field, self).__init__(name=name, type=type)
        self._type = type
        if indexed is not None:
            self.indexed = indexed
        if stored is not None:
            self.stored = stored
        if multi_valued is not None:
            self.multi_valued = multi_valued
        if model_attr:
            self._model_attr = model_attr
    
    def _op(self, *components):
        # TODO: probably need some serialization crap in here
        components = [self.name,':'] + [unicode(component) for component in components]
        return ''.join(components)
    
    def __gt__(self, other):
        return self._op('[',other,' TO *]')

    def __lt__(self, other):
        return self._op('[* TO ',other,']')
    
    def __gte__(self, other):
        return self.__gt__(self, other)
    
    def __lte__(self, other):
        return self.__lt__(other)
    
    def __eq__(self, other):
        return self._op(other)

    def between(self, lower, upper):
        return self._op('[', lower, ' TO ', upper, ']')

    def exists(self):
        return self._op('[* TO *]')

def and_(*args):
    return '(' + ' AND '.join(args) + ')'

def or_(*args):
    return '(' + ' OR '.join(args) + ')' 

class DocumentId(Field):
    def __init__(self, name, type, model_attr=None):
        self.unique_key = UniqueKey(name)
        return super(DocumentId, self).__init__(name, type, model_attr=model_attr)
########NEW FILE########
__FILENAME__ = schema
'''
Created on Jan 15, 2011

@author: al
'''

import os
from util import *
from collections import deque

class SolrFieldType(BaseSolrXMLElement):
    tag = "fieldType"
    required = {'solr_class': 'class',
                 'type_name': 'name'}
    options = ['indexed', 'stored',
               'sort_missing_first', 'sort_missing_last',
               'omit_norms', 'term_vectors',
               'compressed', 'multi_valued',
               'position_increment_gap'
               ]

class String(SolrFieldType): 
    solr_class='solr.StrField'
    type_name='string'
    omit_norms = True
    sort_missing_last = True

class UniqueId(SolrFieldType):
    solr_class='solr.UUIDField'
    type_name='uuid'    

class Boolean(SolrFieldType):
    solr_class = 'solr.BoolField'
    type_name = 'boolean'
    omit_norms = True
    sort_missing_last = True

class Date(SolrFieldType):
    solr_class = 'solr.DateField'
    type_name = 'date'
    
class Random(SolrFieldType):
    solr_class = 'solr.RandomSortField'
    type_name = 'random'

""" 
Numeric types 
"""

class Integer(SolrFieldType):
    solr_class = 'solr.IntField'
    type_name = 'int'
    omit_norms = True
    
class Long(SolrFieldType):
    solr_class = 'solr.LongField'
    type_name = 'long'
    omit_norms = True
    
class Float(SolrFieldType):
    solr_class = 'solr.FloatField'
    type_name = 'float'
    omit_norms = True
    
class Double(SolrFieldType):
    solr_class = 'solr.DoubleField'
    type_name = 'double'
    omit_norms = True
    
class SortableInteger(SolrFieldType):
    solr_class = 'solr.SortableIntField'
    type_name = 'sint'
    omit_norms = True
    sort_missing_last = True

class SortableLong(SolrFieldType):
    solr_class = 'solr.SortableLongField'
    type_name = 'slong'
    omit_norms = True
    sort_missing_last = True
    
class SortableDouble(SolrFieldType):
    solr_class = 'solr.SortableDoubleField'
    type_name = 'sdouble'
    omit_norms = True
    sort_missing_last = True

class SortableFloat(SolrFieldType):
    solr_class = 'solr.SortableFloatField'
    type_name = 'sfloat'
    omit_norms = True
    sort_missing_last = True

"""
Tokenizers
"""
    
class Tokenizer(BaseSolrXMLElement):
    solr_class = None
    tag = "tokenizer"
    required = {'solr_class': 'class'}
    
class WhitespaceTokenizer(Tokenizer):
    solr_class = 'solr.WhitespaceTokenizerFactory'
       
class StandardTokenizer(Tokenizer):
    solr_class = 'solr.StandardTokenizerFactory'
    
class KeywordTokenizer(Tokenizer):
    solr_class = 'solr.KeywordTokenizerFactory'
    
class LetterTokenizer(Tokenizer):
    solr_class = 'solr.LetterTokenizerFactory'
    
class HTMLStripWhitespaceTokenizer(Tokenizer):
    solr_class = 'solr.HTMLStripWhitespaceTokenizerFactory'
    
class HTMLStripStandardTokenizer(Tokenizer):
    solr_class = 'solr.HTMLStripStandardTokenizerFactory'
    
class PatternTokenizer(Tokenizer):
    """ To be subclassed further as needed, for instance:
    
    class GroupingPatternTokenizer(PatternTokenizer):
        pattern= "\'([^\']+)\'"
        group = 1
        
    """
    solr_class = 'solr.PatternTokenizerFactory'
    options = ['pattern', 'group']
        
"""
Filter classes
"""
        
class Filter(BaseSolrXMLElement):
    solr_class = None
    tag = "filter"
    options = []
    required = {'solr_class': 'class'}
    
class LowerCaseFilter(Filter):
    solr_class = "solr.LowerCaseFilterFactory"
    
class StandardFilter(Filter):
    solr_class = 'solr.StandardFilterFactory'
    
class TrimFilter(Filter):
    solr_class = 'solr.TrimFilterFactory'
    options = ['update_offsets']
    
class LengthFilter(Filter):
    solr_class = 'solr.LengthFilterFactory'
    options = ['min', 'max']
    
class RemoveDuplicatesFilter(Filter):
    """ Add this as your last analysis step"""
    solr_class = 'solr.RemoveDuplicatesTokenFilterFactory'
    
class ISOLatin1AccentFilter(Filter):
    """ Normalize accented characters """
    solr_class = 'solr.ISOLatin1AccentFilterFactory'
    
class CapitalizationFilter(Filter):
    solr_class = 'solr.CapitalizationFilterFactory'

class PatternReplaceFilter(Filter):
    """ To be subclassed further as needed"""
    solr_class = 'solr.PatternReplaceFilterFactory'
    options = ['pattern', 'replacement', 'replace']    
    
""" 
CharFilterFactories are available only for Solr 1.4 and higher
"""

class MappingCharFilter(Filter):
    solr_class = 'solr.MappingCharFilterFactory'
    
class PatternReplaceCharFilter(Filter):
    """ To be subclassed further as needed"""
    solr_class = 'solr.PatternReplaceCharFilterFactory'
    options = ['pattern', 'replacement', 'replace']
    
class HTMLStripCharFilter(Filter):
    """ Strips out HTML embedded in text. Good for blog posts, etc.
    that are not HTML documents themselves but may contain HTML """
    solr_class = 'solr.HTMLStripCharFilterFactory'
    
"""
WordDelimiter - highly customizable, don't just use mine
"""
    
class WordDelimiterFilter(Filter):
    solr_class = 'solr.WordDelimiterFilterFactory'
    options = ['generate_word_parts',
                'generate_number_parts', 'catenate_words',
                'catenate_numbers', 'catenate_all', 
                'split_on_case_change', 'split_on_numerics',
                'stem_english_possessive', 'preserve_original']
        
class EnglishPorterFilter(Filter):
    solr_class = 'solr.EnglishPorterFilterFactory'
    options = ['protected']
    
class SnowballPorterFilter(Filter):
    solr_class = 'solr.SnowballPorterFilterFactory'
    options = ['language']
    
class SynonymFilter(Filter):
    solr_class = 'solr.SynonymFilterFactory'
    options = ['synonyms', 'ignore_case', 'expand']
    
class StopFilter(Filter):
    solr_class = 'solr.StopFilterFactory'
    options = ['words', 'ignore_case']
    
"""
Phonetic filters for sounds-like analysis
"""
    
class DoubleMetaphoneFilter(Filter):
    solr_class = 'solr.DoubleMetaphoneFilterFactory'
    options = ['inject', 'max_code_length']

class PhoneticFilter(Filter):
    solr_class = 'solr.PhoneticFilterFactory'
    options = ['encoder', 'inject']    
    
class MetaphoneFilter(PhoneticFilter):
    encoder = 'Metaphone'

class SoundexFilter(PhoneticFilter):
    encoder = 'Soundex'
    
class RefinedSoundexFilter(PhoneticFilter):
    encoder = 'RefinedSoundex'

"""
NGramFilter does substring matches based on a gram size that you specify.
Use with caution...
"""

class NGramFilter(Filter):
    solr_class = 'solr.NGramFilterFactory'
    options = ['min_gram_size', 'max_gram_size']
    min_gram_size = 2
    max_gram_size = 15
   
class EdgeNGramFilter(NGramFilter):
    solr_class = 'solr.EdgeNGramFilterFactory'
    options = NGramFilter.options + ['side']
    
""" 
Analyzer
"""
    
class Analyzer(BaseSolrXMLElement):
    INDEX = 'index'
    QUERY = 'query'
    
    tag = 'analyzer'
    options = ['type']
    
    tokenizer = WhitespaceTokenizer
    filters = ()


"""
All text-based field_types
"""

class BaseText(SolrFieldType):
    solr_class = 'solr.TextField'
    position_increment_gap = 100
    
class SimpleTokenizedText(BaseText):
    type_name = 'text_ws'
    anaylzer = Analyzer(tokenizer=WhitespaceTokenizer)

class Text(BaseText):
    type_name = 'text'
    
    index_analyzer = Analyzer(type=Analyzer.INDEX,
                              tokenizer = WhitespaceTokenizer,
                              filters = (StopFilter(ignore_case=True, words='stopwords.txt', enable_position_increments=True),
                                         WordDelimiterFilter(generate_word_parts=1, generate_number_parts=1, catenate_words=1, 
                                                             catenate_numbers=1, catenate_all=0, split_on_case_change=1),
                                         LowerCaseFilter,
                                         ISOLatin1AccentFilter,
                                         EnglishPorterFilter(protected='protwords.txt'),
                                         RemoveDuplicatesFilter
                                         )
                        )
    query_analyzer = Analyzer(type=Analyzer.QUERY,
                              tokenizer = WhitespaceTokenizer,
                              filters = (SynonymFilter(synonyms='synonyms.txt', ignore_case=True, expand=True),
                                         StopFilter(ignore_case=True, words='stopwords.txt'),
                                         WordDelimiterFilter(generate_word_parts=1, generate_number_parts=1, catenate_words=1, 
                                                             catenate_numbers=0, catenate_all=0, split_on_case_change=1),
                                         LowerCaseFilter,
                                         ISOLatin1AccentFilter,
                                         EnglishPorterFilter(protected='protwords.txt'),
                                         RemoveDuplicatesFilter
                                         )
                              
                              )
class TextTight(BaseText):
    type_name = 'textTight'
    
    analyzer = Analyzer(tokenizer = WhitespaceTokenizer,
                        filters = (SynonymFilter(synonyms='synonyms.txt', ignore_case=True, expand=False),
                                   StopFilter(ignore_case=True, words='stopwords.txt'),
                                   WordDelimiterFilter(generate_word_parts=0, generate_number_parts=0, catenate_words=1, catenate_numbers=1, catenate_all=0),
                                   LowerCaseFilter,
                                   EnglishPorterFilter(protected='protwords.txt'),
                                   RemoveDuplicatesFilter
                                   )
                        )

class Title(BaseText):
    type_name = 'title'
    
    analyzer = Analyzer(tokenizer = WhitespaceTokenizer,
                        filters = (StopFilter(ignore_case=True, words='stopwords.txt'),
                                   WordDelimiterFilter(generate_word_parts=0, generate_number_parts=0, catenate_words=1, catenate_numbers=1, catenate_all=0),
                                   LowerCaseFilter,
                                   ISOLatin1AccentFilter,
                                   RemoveDuplicatesFilter
                                   )
                        )

class TextSpell(BaseText):
    type_name = 'textSpell'
    stored = False
    multi_valued = True
    
    index_analyzer = Analyzer(type=Analyzer.INDEX,
                              tokenizer = StandardTokenizer,
                              filters = (LowerCaseFilter,
                                         SynonymFilter(synonyms='synonyms.txt', ignore_case=True, expand=True),
                                         StopFilter(ignore_case=True, words='stopwords.txt'),
                                         StandardFilter,
                                         RemoveDuplicatesFilter
                                         )
                              )
    query_analyzer = Analyzer(type=Analyzer.QUERY,
                              tokenizer=StandardTokenizer,
                              filters=(LowerCaseFilter,
                                       StopFilter(ignore_case=True, words='stopwords.txt'),
                                       StandardFilter,
                                       RemoveDuplicatesFilter
                                       )
                              )

class TextSpellPhrase(BaseText):
    type_name = 'textSpellPhrase'

    analyzer = Analyzer(tokenizer=KeywordTokenizer,
                        filters = (LowerCaseFilter,
                                   )
                        )

class AlphaOnlySort(BaseText):
    type_name = 'alphaOnlySort'
    omit_norms = True
    sort_missing_last = True
    
    analyzer = Analyzer(tokenizer = KeywordTokenizer,
                        filters = (LowerCaseFilter,
                                   TrimFilter,
                                   PatternReplaceFilter(pattern='([^a-z])', replacement='', replace='all')
                                   )
                        )


class Ignored(SolrFieldType):
    type_name = 'ignored'
    solr_class = 'solr.StrField'
    indexed = False
    stored = False

class SolrFieldTypes(BaseSolrXMLElement):
    tag = 'types'

    types = (String, Boolean, UniqueId,
             Integer, Long, Float, Double,
             SortableInteger, SortableLong,
             SortableFloat, SortableDouble,
             Date, Random, SimpleTokenizedText, 
             Text, TextTight, Title, TextSpell,
             TextSpellPhrase, AlphaOnlySort, Ignored)    
    
    def __init__(self, *args):
        self.types = tuple(args)

class SolrSchemaField(BaseSolrXMLElement):
    tag = 'field'
    required = dict([(attr, attr)
                    for attr in ['name', 'type']])
    options = ['indexed', 'stored', 'multi_valued', 'sort_missing_last',
               'sort_missing_first', 'compressed', 'term_vectors', 'omit_norms',
               'position_increment_gap']

    def __init__(self, name, type):
        super(SolrSchemaField, self).__init__(name=name, type=type.type_name)


class SolrSchemaFields(BaseSolrXMLElement):  
    tag = 'fields'
    fields = ()
    dependency = SolrFieldTypes
    
    def __init__(self, *args):
        super(SolrSchemaFields, self).__init__(fields=args)

class UniqueKey(BaseSolrXMLElement):
    tag = 'uniqueKey'
    dependency = SolrSchemaFields
    value = None

    def __init__(self, name=None):
        self.value = name

class SolrSchema(BaseSolrXMLElement):
    tag = 'schema'
    required = dict([(attr, attr)
                    for attr in ['name', 'version']])

    def __init__(self, name, version='1.1',
                    field_types=SolrFieldTypes(),
                    fields=SolrSchemaFields(), **kw):
        self.name = name
        self.version = version
        self.field_types = field_types
        self.names_to_fields = dict([(field_type.type_name, field_type)
                                     for field_type in field_types.types])
        self.fields = fields
        super(SolrSchema, self).__init__(**kw)

def generate_schema(schema, path = 'solr/conf/schema.xml'):
    ensure_dir(os.path.dirname(path))
    
    tree = etree.ElementTree(schema.to_xml())
    tree.write(path, encoding='utf-8', xml_declaration=True, pretty_print=True)                    
########NEW FILE########
__FILENAME__ = test_autodiscover
'''
Created on Mar 7, 2011

@author: al
'''

from bebop import autodiscover_indexes, generate_solr_configs
from unittest import TestCase

class TestModel(TestCase):
        
    def test_autodiscover(self):
        import bebop.test
        indexes = autodiscover_indexes(bebop.test)
        generate_solr_configs(indexes)
        self.assertTrue(True)
########NEW FILE########
__FILENAME__ = test_generate_config
from unittest import TestCase
from bebop import *

class TestGenerateConfig(TestCase):
    
    def test_generate_config(self):

        config = DismaxSolrConfig

        path = './test/unit_test_config.xml'
        generate_config(config, path=path)
    
        expected = open('./test/test_config.xml').read()
        generated = open(path).read()

        self.assertEqual(expected, generated)

########NEW FILE########
__FILENAME__ = test_generate_schema
from unittest import TestCase
from bebop import *

class TestGenerateSchema(TestCase):
    def test_schema(self):
        filename = './test/unit_test_schema.xml'
        schema = SolrSchema('test_schema',
                            field_types=SolrFieldTypes(Integer, Text),
                            fields = SolrSchemaFields(
                                Field('foo', Text),
                                DocumentId('bar', Integer)
                                )
                            )
        generate_schema(schema, path=filename)

        generated_file = open(filename).read()
        test_file = open('./test/test_schema.xml').read()
        
        self.assertEqual(generated_file, test_file)
########NEW FILE########
__FILENAME__ = test_model
'''
Created on Feb 14, 2011

@author: al
'''

from bebop import *
from unittest import TestCase

class FooDB(object):
    def __init__(self, **kw):
        for attr, val in kw.iteritems():
            setattr(self, attr, val)

class BarDB(object):
    def __init__(self, **kw):
        for attr, val in kw.iteritems():
            setattr(self, attr, val)


@SearchIndex('foo')
class Foo(SearchableModel):
    _target=FooDB
    id = DocumentId('id', Integer, model_attr='id')
    name = Field('name', Title, model_attr='name')
   
@SearchIndex('bar', config=DismaxSolrConfig)
class Bar(SearchableModel):
    _target=BarDB
    id = DocumentId('id', Integer, model_attr='id')
    name = Field('name', Title, model_attr='name')
        
        
class TestModel(TestCase):

    def test_internals(self):
        self.assertEquals(Foo.__index__, 'foo')
        self.assertEquals(Foo._fields, ['id', 'name'])

    def test_equals(self):
        clause = Foo.name == 'blah'
        self.assertEquals(clause, "name:blah")

    def test_boolean_clause(self):
        clause = and_(Foo.id > 5, or_(Foo.name=='blah', Foo.name=='blee'))
        self.assertEquals(clause, "(id:[5 TO *] AND (name:blah OR name:blee))")
########NEW FILE########
__FILENAME__ = util
'''
Created on Jan 19, 2011

@author: al
'''

from lxml import etree
from lxml import builder
from lxml import objectify
from collections import defaultdict, deque, MutableSet
import os
import inspect
        
__E = objectify.ElementMaker(annotate=False)

def ensure_dir(d):
    if not os.path.exists(d):
        os.makedirs(d)

    
def memoize(f):
    arg_cache = {}
    def _new_f(arg):
        cache_it = True
        try:
            cached = arg_cache.get(arg, None)
            if cached is not None:
                return cached
        except TypeError:
            cache_it = False
        uncached = f(arg)
        if cache_it:
            arg_cache[arg] = uncached
        return uncached
    return _new_f

class classproperty(property):
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()

def to_camelcase(s):
    return ''.join([token.title() if i > 0 else token.lower() 
                    for i, token in enumerate(s.split('_'))])
    
@memoize
def _stringify(obj):
    # TODO: write your own PyObject > string conversion
    # or find a better way to do this
    return __E._dummy_node(obj).text

def _sorted_update(elem, d):
    elem.attrib.update(sorted(d.iteritems()))    

def get_class(obj):
    if inspect.isclass(obj):
        return obj
    else:
        return obj.__class__

def _collect_dependencies(obj, deps=defaultdict(set), refs=defaultdict(int)):
    for attr, value in obj.__dict__.iteritems():
        # Dependencies are XML orderings, so we don't care about non-XMLable attributes
        if hasattr(value, 'dependency'):
            # deps[SolrFieldTypes]=set(UniqueKey('foo'))
            deps[get_class(value.dependency)].add(value)
            # ref_counts[elem]==1 means that elem is waiting on 1 node to complete
            refs[value]+=1
            
        if hasattr(value, 'to_xml'):
            deps, refs = _collect_dependencies(value, deps, refs)
        elif hasattr(value, '__iter__') and hasattr(iter(value).next(), 'to_xml'):
            for val in value:
                deps, refs = _collect_dependencies(val, deps, refs)
            
    return deps, refs
        
def _to_xml(node):
    root=None
    # Topsort: schedule items with no dependers
    # Queue items are a tuple of (obj, parent)
    q=deque([(node, None)])
    dependency_graph, ref_counts = _collect_dependencies(node)
     
    #[q.append((value,node)) for value in node.__dict__.itervalues() if hasattr(value, 'to_xml') and ref_counts[value] == 0]

    while q:
        obj, parent = q.popleft()

        element = etree.Element(obj.tag)
        if obj is node:
            root=element
        
        definitions = {}
        options = {}
        for attr, transformed in obj.required.iteritems():
            definitions[transformed] = _stringify(getattr(obj, attr))

        for attr, value in obj.__dict__.iteritems():
            if attr in obj.required:
                definitions[obj.required[attr]] = _stringify(value)
            elif attr in obj.optional:
                options[obj.optional[attr]] = _stringify(value)
            elif attr=='value':
                element.text=value
            # For referencing elements without throwing them in the schema, use an underscore
            elif attr.startswith('_'):
                continue
            # Append children (recursive, but we don't need many levels)
            elif hasattr(value, 'to_xml') and not hasattr(value, 'dependency'):
                q.append((value, element))
            # Example: filters
            # TODO: are there any use cases where this is not the expected behavior?
            elif hasattr(value, '__iter__'):
                i = iter(value)
                first = i.next()
                del(i)
                if hasattr(first, 'to_xml') and not hasattr(value, 'dependency'):
                    #parent_node = parent if hasattr(first, 'dependency') else element
                    q.extend([(child, element) for child in value])

                
        _sorted_update(element, definitions)
        _sorted_update(element, options)
        
        

        cls = get_class(obj)
        if cls in dependency_graph:
            for dep in dependency_graph[cls]:
                ref_counts[dep]-=1
                if ref_counts[dep]==0:
                    q.appendleft((dep, parent))
            del(dependency_graph[cls])
                
        if parent is not None:
            parent.append(element)
    

                        
    return root

class BaseSolrXMLElement(object):
    required = {}
    options = []
    tag = None
    ref_count = 0
        
    def __init__(self, **kw):
        for k, v in kw.iteritems():
            setattr(self, k, v)
            
        # So class.to_xml will call _to_xml(cls) and self.to_xml will call _to_xml(self)
        self.to_xml = self.instance_to_xml
    
    def instance_to_xml(self):
        return _to_xml(self)
    
    
    @classmethod
    def to_xml(cls):
        return _to_xml(cls)
    
    
    @classproperty
    @classmethod
    def optional(cls):
        return dict([(attr, to_camelcase(attr))
                     for attr in cls.options])    

def single_value_tag(tag, value):
    return BaseSolrXMLElement(tag=tag, value=value)

class SingleValueTagsMixin(BaseSolrXMLElement):
    def __init__(self, camelcase=True, **kw):
        for attr, val in kw.iteritems():
            if val is None:
                continue
            if hasattr(val, 'to_xml'):
                # Ignore XML elements so they can be mixed in freely
                setattr(self, attr, val)
                continue
            
            tag = to_camelcase(attr) if camelcase else attr
            element = single_value_tag(tag, val)
            setattr(self, attr, element)
            
        super(SingleValueTagsMixin, self).__init__()
        
# OrderedSet, generally useful collection

KEY, PREV, NEXT = range(3)

class OrderedSet(MutableSet):
    def __init__(self, iterable=None):
        self.end = end = [] 
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[PREV]
            curr[NEXT] = end[PREV] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:        
            key, prev, next = self.map.pop(key)
            prev[NEXT] = next
            next[PREV] = prev

    def __iter__(self):
        end = self.end
        curr = end[NEXT]
        while curr is not end:
            yield curr[KEY]
            curr = curr[NEXT]

    def __reversed__(self):
        end = self.end
        curr = end[PREV]
        while curr is not end:
            yield curr[KEY]
            curr = curr[PREV]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = next(reversed(self)) if last else next(iter(self))
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)

    def __del__(self):
        self.clear()                    # remove circular references

########NEW FILE########
__FILENAME__ = disqus
from django.conf import settings

import base64
import hashlib
import hmac
import time
import json
import logging

'''
  Commenting out DisqusAPI for current integration, 
  but for future features, like 'top comments', will need to install discus-python
  ref: https://github.com/disqus/disqus-python/blob/master/README.rst
'''
# from disqusapi import DisqusAPI

'''
    returns a user params json object base-64 encoded then hmac'd with our private API key (settings.DISQUS_SECRET_KEY)
    the disqus plugin requires this to exist on the integrating page as a JS var named 'remote_auth_s3'
    ref: http://docs.disqus.com/developers/sso/
    data obj 
    {
        id - any unique user ID number associated with that account within your user database. This will be used to generate a unique username to reference in the Disqus system.
        username - The displayed name for that account
        email - The registered email address for that account
        avatar (optional) - A link to that user's avatar
        url (optional) - A link to the user's website
    }
'''
def get_sso_auth(user):
    # avoid conflicts with production users
    devprefix = ''
    if settings.DISQUS_DEV_MODE == 1:
        devprefix = 'dev_'
        
    if user and user.is_authenticated():
        data = json.dumps({
            'id': '%s%s' % (devprefix, user.id),
            'username': user.get_name,
            'email': user.email,
            'avatar': user.get_image_small,
            # need FQDN with protocol for 'url' here b/c disqus has 
            # stupid parsing logic when displaying the link- they
            # simply cut off the first 7 characters of the the value always assuming that's 
            # the protocol and display the rest. wow. so, if you have a secure link https://,
            # which is 8 characters, they display the last forward slash, "/rest_of_url".. is it
            # that hard to parse for protocols in urls?  apparently.
            'url': "http://%s%s" % (settings.HTTP_HOST, user.get_url)
        })
    else:
        # sending empty json object logs out
        data = json.dumps({});
    
    # encode the data to base64
    message = base64.b64encode(data)
    # generate a timestamp for signing the message
    timestamp = int(time.time())
    # generate our hmac signature
    sig = hmac.HMAC(settings.DISQUS_SECRET_KEY, '%s %s' % (message, timestamp), hashlib.sha1).hexdigest()
    return "%(message)s %(sig)s %(timestamp)s" % dict(
        message=message,
        timestamp=timestamp,
        sig=sig,
    )
########NEW FILE########
__FILENAME__ = ec2metadata
#!/usr/bin/python
#
#    Query and display EC2 metadata related to the AMI instance
#    Copyright (c) 2009 Canonical Ltd. (Canonical Contributor Agreement 2.5)
#
#    Author: Alon Swartz <alon@turnkeylinux.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Query and display EC2 metadata

If no options are provided, all options will be displayed

Options:
    -h --help               show this help

    --kernel-id             display the kernel id
    --ramdisk-id            display the ramdisk id
    --reservation-id        display the reservation id

    --ami-id                display the ami id
    --ami-launch-index      display the ami launch index
    --ami-manifest-path     display the ami manifest path
    --ancestor-ami-id       display the ami ancestor id
    --product-codes         display the ami associated product codes
    --availability-zone     display the ami placement zone

    --instance-id           display the instance id
    --instance-type         display the instance type

    --local-hostname        display the local hostname
    --public-hostname       display the public hostname

    --local-ipv4            display the local ipv4 ip address
    --public-ipv4           display the public ipv4 ip address

    --block-device-mapping  display the block device id
    --security-groups       display the security groups

    --public-keys           display the openssh public keys
    --user-data             display the user data (not actually metadata)

"""

import sys
import time
import getopt
import urllib
import socket

METAOPTS = ['ami-id', 'ami-launch-index', 'ami-manifest-path',
            'ancestor-ami-id', 'availability-zone', 'block-device-mapping',
            'instance-id', 'instance-type', 'local-hostname', 'local-ipv4',
            'kernel-id', 'product-codes', 'public-hostname', 'public-ipv4',
            'public-keys', 'ramdisk-id', 'reserveration-id', 'security-groups',
            'user-data']

class Error(Exception):
    pass

class EC2Metadata:
    """Class for querying metadata from EC2"""

    def __init__(self, addr='169.254.169.254', api='2008-02-01'):
        self.addr = addr
        self.api = api

        if not self._test_connectivity(self.addr, 80):
            raise Error("could not establish connection to: %s" % self.addr)

    @staticmethod
    def _test_connectivity(addr, port):
        for i in range(6):
            s = socket.socket()
            try:
                s.connect((addr, port))
                s.close()
                return True
            except socket.error, e:
                time.sleep(1)

        return False

    def _get(self, uri):
        url = 'http://%s/%s/%s/' % (self.addr, self.api, uri)
        value = urllib.urlopen(url).read()
        if "404 - Not Found" in value:
            return None

        return value

    def get(self, metaopt):
        """return value of metaopt"""

        if metaopt not in METAOPTS:
            raise Error('unknown metaopt', metaopt, METAOPTS)

        if metaopt == 'availability-zone':
            return self._get('meta-data/placement/availability-zone')

        if metaopt == 'public-keys':
            data = self._get('meta-data/public-keys')
            keyids = [ line.split('=')[0] for line in data.splitlines() ]

            public_keys = []
            for keyid in keyids:
                uri = 'meta-data/public-keys/%d/openssh-key' % int(keyid)
                public_keys.append(self._get(uri).rstrip())

            return public_keys

        if metaopt == 'user-data':
            return self._get('user-data')

        return self._get('meta-data/' + metaopt)


def parse_jumo_user_data(data_string):
    user_data_args = {}
    try:
      #this could be smarter but it will also enforce our "pass simple small data rule"
      key_value_strings = data_string.split(',')
      for kvs in key_value_strings:
        (key, value) = kvs.split('=')
        user_data_args[key] = value
    except:
      pass
    return user_data_args

def get(metaopt):
    """primitive: return value of metaopt"""

    m = EC2Metadata()
    return m.get(metaopt)

def display(metaopts, prefix=False):
    """primitive: display metaopts (list) values with optional prefix"""

    m = EC2Metadata()
    for metaopt in metaopts:
        value = m.get(metaopt)
        if not value:
            value = "unavailable"

        if prefix:
            print "%s: %s" % (metaopt, value)
        else:
            print value

def usage(s=None):
    """display usage and exit"""

    if s:
        print >> sys.stderr, "Error:", s
    print >> sys.stderr, "Syntax: %s [options]" % sys.argv[0]
    print >> sys.stderr, __doc__
    sys.exit(1)

def main():
    """handle cli options"""

    try:
        getopt_metaopts = METAOPTS[:]
        getopt_metaopts.append('help')
        opts, args = getopt.gnu_getopt(sys.argv[1:], "h", getopt_metaopts)
    except getopt.GetoptError, e:
        usage(e)

    if len(opts) == 0:
        display(METAOPTS, prefix=True)
        return

    metaopts = []
    for opt, val in opts:
        if opt in ('-h', '--help'):
            usage()

        metaopts.append(opt.replace('--', ''))

    display(metaopts)


if __name__ == "__main__":
   main()
########NEW FILE########
__FILENAME__ = facebook
#!/usr/bin/env python
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Python client library for the Facebook Platform.

This client library is designed to support the Graph API and the official
Facebook JavaScript SDK, which is the canonical way to implement
Facebook authentication. Read more about the Graph API at
http://developers.facebook.com/docs/api. You can download the Facebook
JavaScript SDK at http://github.com/facebook/connect-js/.

If your application is using Google AppEngine's webapp framework, your
usage of this module might look like this:

    user = facebook.get_user_from_cookie(self.request.cookies, key, secret)
    if user:
        graph = facebook.GraphAPI(user["access_token"])
        profile = graph.get_object("me")
        friends = graph.get_connections("me", "friends")

"""

import cgi
import hashlib
import time
import urllib

# Find a JSON parser
try:
    import json
    _parse_json = lambda s: json.loads(s)
except ImportError:
    try:
        import simplejson
        _parse_json = lambda s: simplejson.loads(s)
    except ImportError:
        # For Google AppEngine
        from django.utils import simplejson
        _parse_json = lambda s: simplejson.loads(s)


class GraphAPI(object):
    """A client for the Facebook Graph API.

    See http://developers.facebook.com/docs/api for complete documentation
    for the API.

    The Graph API is made up of the objects in Facebook (e.g., people, pages,
    events, photos) and the connections between them (e.g., friends,
    photo tags, and event RSVPs). This client provides access to those
    primitive types in a generic way. For example, given an OAuth access
    token, this will fetch the profile of the active user and the list
    of the user's friends:

         graph = facebook.GraphAPI(access_token)
         user = graph.get_object("me")
         friends = graph.get_connections(user["id"], "friends")

    You can see a list of all of the objects and connections supported
    by the API at http://developers.facebook.com/docs/reference/api/.

    You can obtain an access token via OAuth or by using the Facebook
    JavaScript SDK. See http://developers.facebook.com/docs/authentication/
    for details.

    If you are using the JavaScript SDK, you can use the
    get_user_from_cookie() method below to get the OAuth access token
    for the active user from the cookie saved by the SDK.
    """
    def __init__(self, access_token=None):
        self.access_token = access_token

    def get_object(self, id, **args):
        """Fetchs the given object from the graph."""
        return self.request(id, args)

    def get_objects(self, ids, **args):
        """Fetchs all of the given object from the graph.

        We return a map from ID to object. If any of the IDs are invalid,
        we raise an exception.
        """
        args["ids"] = ",".join(ids)
        return self.request("", args)

    def get_connections(self, id, connection_name, **args):
        """Fetchs the connections for given object."""
        return self.request(id + "/" + connection_name, args)

    def put_object(self, parent_object, connection_name, **data):
        """Writes the given object to the graph, connected to the given parent.

        For example,

            graph.put_object("me", "feed", message="Hello, world")

        writes "Hello, world" to the active user's wall. Likewise, this
        will comment on a the first post of the active user's feed:

            feed = graph.get_connections("me", "feed")
            post = feed["data"][0]
            graph.put_object(post["id"], "comments", message="First!")

        See http://developers.facebook.com/docs/api#publishing for all of
        the supported writeable objects.

        Most write operations require extended permissions. For example,
        publishing wall posts requires the "publish_stream" permission. See
        http://developers.facebook.com/docs/authentication/ for details about
        extended permissions.
        """
        assert self.access_token, "Write operations require an access token"
        return self.request(parent_object + "/" + connection_name, post_args=data)

    def put_wall_post(self, message, attachment={}, profile_id="me"):
        """Writes a wall post to the given profile's wall.

        We default to writing to the authenticated user's wall if no
        profile_id is specified.

        attachment adds a structured attachment to the status message being
        posted to the Wall. It should be a dictionary of the form:

            {"name": "Link name"
             "link": "http://www.example.com/",
             "caption": "{*actor*} posted a new review",
             "description": "This is a longer description of the attachment",
             "picture": "http://www.example.com/thumbnail.jpg"}

        """
        return self.put_object(profile_id, "feed", message=message, **attachment)

    def put_comment(self, object_id, message):
        """Writes the given comment on the given post."""
        return self.put_object(object_id, "comments", message=message)

    def put_like(self, object_id):
        """Likes the given post."""
        return self.put_object(object_id, "likes")

    def delete_object(self, id):
        """Deletes the object with the given ID from the graph."""
        self.request(id, post_args={"method": "delete"})

    def request(self, path, args=None, post_args=None, skip = False):
        """Fetches the given path in the Graph API.

        We translate args to a valid query string. If post_args is given,
        we send a POST request to the given path with the given arguments.
        """
        if not args: args = {}
        if self.access_token:
            if post_args is not None:
                post_args["access_token"] = self.access_token
            else:
                args["access_token"] = self.access_token
        post_data = None if post_args is None else urllib.urlencode(post_args)
        if not skip:
            file = urllib.urlopen("https://graph.facebook.com/" + path + "?" +
                                urllib.urlencode(args), post_data)
        else:
            file = urllib.urlopen("https://graph.facebook.com/" + path)
        try:
            response = _parse_json(file.read())
        finally:
            file.close()
        if response.get("error"):
            raise GraphAPIError(response["error"]["type"],
                                response["error"]["message"])
        return response


class GraphAPIError(Exception):
    def __init__(self, type, message):
        Exception.__init__(self, message)
        self.type = type


def get_user_from_cookie(cookies, app_id, app_secret):
    """Parses the cookie set by the official Facebook JavaScript SDK.

    cookies should be a dictionary-like object mapping cookie names to
    cookie values.

    If the user is logged in via Facebook, we return a dictionary with the
    keys "uid" and "access_token". The former is the user's Facebook ID,
    and the latter can be used to make authenticated requests to the Graph API.
    If the user is not logged in, we return None.

    Download the official Facebook JavaScript SDK at
    http://github.com/facebook/connect-js/. Read more about Facebook
    authentication at http://developers.facebook.com/docs/authentication/.
    """
    cookie = cookies.get("fbs_" + app_id, "")
    if not cookie: return None
    args = dict((k, v[-1]) for k, v in cgi.parse_qs(cookie.strip('"')).items())
    payload = "".join(k + "=" + args[k] for k in sorted(args.keys())
                        if k != "sig")
    sig = hashlib.md5(payload + app_secret).hexdigest()
    expires = int(args["expires"])
    if sig == args.get("sig") and (expires == 0 or time.time() < expires):
        return args
    else:
        return None



########NEW FILE########
__FILENAME__ = image_upload
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from boto.s3 import connection, key as s3key
from django.conf import settings
from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.db import models
import Image
import os, math, re, tempfile
import uuid


class ImageType:
    USER = "user"
    ORG = "org"
    ISSUE = "issue"
    MEDIAITEM = "mediaitem"
    MISC = "misc"

class ImageSize:
    LARGE = "large"
    SMALL = "small"


MEDIAITEM_WIDTH_LARGE = 400
MEDIAITEM_WIDTH_SMALL = 161
EVERYTHING_ELSE_LARGE = 150
EVERYTHING_ELSE_SMALL = 50


#Leaving this for user model. We can change it to work like org issue later.
def upload_user_image(opened_image, id, size_name, width, height):
    file_path = '%s/%s/%s' % (ImageType.USER, id, size_name)
    crop = True if width == height else False
    image = _resize_image(opened_image, width, crop)
    url = _upload_photo(image, ImageType.USER, file_path=file_path)
    return (url, image.size[0], image.size[1])

#Temporarily adding this back in so upload_user_image can work. Will remove this
#when user img urls are refactored to use S3EnabledImageField
def _upload_photo(image, image_type, id=None, file_path=None):
    conn = connection.S3Connection(settings.AWS_ACCESS_KEY, settings.AWS_SECRET_KEY)
    s3bucket = conn.create_bucket(settings.AWS_PHOTO_UPLOAD_BUCKET)
    filename = str(uuid.uuid4())

    tmp = tempfile.NamedTemporaryFile('w+b', -1, '.jpg')
    image = image.convert("RGB")
    image.save(tmp.name)

    key = s3key.Key(s3bucket)
    if file_path:
      key.key = '%s.jpg' % file_path
    elif id:
      key.key = '%s/%s_%s.jpg' % (image_type, filename, id)
    else:
      key.key = '%s/%s.jpg' % (image_type, filename)
    try:
      key.set_contents_from_filename(tmp.name, None, True, None, 10, 'public-read', None)
    except:
      raise
    key.close()
    tmp.close()
    return "http://%s.s3.amazonaws.com/%s" % (settings.AWS_PHOTO_UPLOAD_BUCKET, key.key)

def _resize_image(image, max_width, crop = False):
    if max_width is None or max_width == 0:
        return image.convert('RGB')

    if crop:
        x = image.size[0]
        y = image.size[1]
        if x != y:
          box = (0, 0, x, y)
          if x > y:
            crop_1 = int(math.floor((x-y) / 2))
            crop_2 = int(math.ceil((x-y) / 2))
            box = (crop_1, 0, x - crop_2, y)
          else:
            crop_1 = int(math.floor((y-x) / 2))
            crop_2 = int(math.ceil((y-x) / 2))
            box = (0, crop_1, x, y - crop_2)
          image = image.crop(box)

    ratio = (max_width/float(image.size[0]))
    max_height = int((float(image.size[1]) * float(ratio)))
    image = image.convert('RGB')
    if image.size[0] > max_width:
        image = image.resize((max_width, max_height), Image.ANTIALIAS)
    return image




#I want to move all this to forms...not the model.
class S3ImageStorage(FileSystemStorage):
    inst_id = uuid.uuid4()
    def __init__(self, bucket_name=None, image_type = ImageType.MISC, image_size=ImageSize.LARGE):
        self.image_type = image_type
        self.image_size = image_size
        self.bucket_name = bucket_name
        self._bucket = None

    def _open(self, name, mode='rb'):
        class S3File(File):
            def __init__(self, key):
                self.key = key

            def size(self):
                return self.key.size

            def read(self, *args, **kwargs):
                return self.key.read(*args, **kwargs)

            def write(self, content):
                self.key.set_contents_from_string(content)

            def close(self):
                self.key.close()

        return S3File(Key(self.bucket, name))

    def _build_filepath(self):
        return "%s/%s_%s.jpg" % (self.image_type, self.inst_id, self.image_size)

    def _save(self, name, content):
        name = self._build_filepath()
        content.seek(0)
        image = _resize_image(Image.open(content), self.image_width, self.should_image_crop)
        tmp = tempfile.NamedTemporaryFile("w+b", -1, '.jpg')
        image.save(tmp.name)

        key = Key(self.bucket, name)
        key.set_contents_from_filename(tmp.name, None, True, None, 10, 'public-read', None)

        return name

    @property
    def bucket(self):
        if self._bucket == None:
            self.connection = S3Connection(settings.AWS_ACCESS_KEY, settings.AWS_SECRET_KEY)
            if not self.connection.lookup(self.bucket_name):
                self.connection.create_bucket(self.bucket_name)
            self._bucket = self.connection.get_bucket(self.bucket_name)
        return self._bucket

    @property
    def image_width(self):
        #Right now it's only determined by size but might be type and more later
        #We can do complicated mapping when that time comes.
        if self.image_size == ImageSize.LARGE:
            if self.image_type == ImageType.MEDIAITEM:
                return MEDIAITEM_WIDTH_LARGE
            else:
                return EVERYTHING_ELSE_LARGE

        if self.image_type == ImageType.MEDIAITEM:
            return MEDIAITEM_WIDTH_SMALL

        return EVERYTHING_ELSE_SMALL

    @property
    def should_image_crop(self):
        if self.image_type == ImageType.MEDIAITEM:
            return False
        if self.image_size == ImageSize.LARGE:
            return False
        return True

    def delete(self, name):
        self.bucket.delete_key(name)

    def exists(self, name):
        return Key(self.bucket, name).exists()

    def listdir(self, path):
        return [key.name for key in self.bucket.list()]

    def path(self, name):
        raise NotImplementedError

    def size(self, name):
        return self.bucket.get_key(name).size

    def url(self, name):
        try:
            return Key(self.bucket, name).generate_url(100000)
        except KeyError:
            return None
    
    def get_available_name(self, name):
        return name

class S3EnabledImageField(models.ImageField):
    def __init__(self, bucket_name=settings.AWS_PHOTO_UPLOAD_BUCKET, image_type=ImageType.MISC, image_size=ImageSize.LARGE, **kwargs):
        kwargs['storage'] = S3ImageStorage(bucket_name, image_type=image_type, image_size=image_size)
        kwargs['upload_to'] = "ignore_this"
        super(S3EnabledImageField, self).__init__(**kwargs)

########NEW FILE########
__FILENAME__ = simple_lock
import errno, os, socket, sys

class LockError(IOError):
    def __init__(self, errno, strerror, filename):
        IOError.__init__(self, errno, strerror, filename)

class LockHeld(LockError):
    def __init__(self, errno, filename, locker):
        LockError.__init__(self, errno, 'Lock held', filename)
        self.locker = locker

class LockUnavailable(LockError):
    pass


class SimpleLock:
    """Tried to find a simple pid locking mechanism on the web but
       everything was so over architected i did that thing I hate
       and wrote my own and I did it fast.  HATE BEING THAT GUY!"""

    def __init__(self, pid_file):
        self.pid_file = pid_file
        self.hostname = socket.gethostname()
        self.lockname = '%s:%s' % (self.hostname, os.getpid())
        self.lock()

    def lock(self):
        try:
            self.trylock()
            return True
        except LockHeld, err:
            #changed my mind about adding holding counts.
            #leaving this hear for future.
            raise

    def trylock(self):
        try:
            ln = os.symlink(self.lockname, self.pid_file)
        except (OSError, IOError), err:
            if err.errno == errno.EEXIST:
                locker = self.testlock()
                if locker is not None:
                    raise LockHeld(errno.EEXIST, self.pid_file, locker)
            else:
                raise LockUnavailable(err.errno, err.strerror, self.pid_file)


    def testlock(self):
        locker = None
        try:
            locker = os.readlink(self.pid_file)
            host, pid = locker.split(":", 1)
            pid = int(pid)
            if host != self.hostname:
                return locker

            if self.testpid(pid):
                return locker

            #Break lock by created new lock for race
            try:
                l = SimpleLock(self.pid_file + "breaking")
                os.unlink(self.pid_file)
                os.symlink(self.lockname, self.pid_file)
                l.release()
            except LockError:
                return locker
        except ValueError:
            return locker


    def testpid(self, pid):
        try:
            os.kill(pid, 0)
            return True
        except OSError, err:
            return err.errno != errno.ESRCH


    def release(self):
        try:
            os.unlink(self.pid_file)
        except OSError:
            pass

########NEW FILE########
__FILENAME__ = binding
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides classes for (WS) SOAP bindings.
"""

from logging import getLogger
from suds import *
from suds.sax import Namespace
from suds.sax.parser import Parser
from suds.sax.document import Document
from suds.sax.element import Element
from suds.sudsobject import Factory, Object
from suds.mx import Content
from suds.mx.literal import Literal as MxLiteral
from suds.umx.basic import Basic as UmxBasic
from suds.umx.typed import Typed as UmxTyped
from suds.bindings.multiref import MultiRef
from suds.xsd.query import TypeQuery, ElementQuery
from suds.xsd.sxbasic import Element as SchemaElement
from suds.options import Options
from suds.plugin import PluginContainer
from copy import deepcopy 

log = getLogger(__name__)

envns = ('SOAP-ENV', 'http://schemas.xmlsoap.org/soap/envelope/')


class Binding:
    """
    The soap binding class used to process outgoing and imcoming
    soap messages per the WSDL port binding.
    @cvar replyfilter: The reply filter function.
    @type replyfilter: (lambda s,r: r)
    @ivar wsdl: The wsdl.
    @type wsdl: L{suds.wsdl.Definitions}
    @ivar schema: The collective schema contained within the wsdl.
    @type schema: L{xsd.schema.Schema}
    @ivar options: A dictionary options.
    @type options: L{Options}
    """
    
    replyfilter = (lambda s,r: r)

    def __init__(self, wsdl):
        """
        @param wsdl: A wsdl.
        @type wsdl: L{wsdl.Definitions}
        """
        self.wsdl = wsdl
        self.multiref = MultiRef()
        
    def schema(self):
        return self.wsdl.schema
    
    def options(self):
        return self.wsdl.options
        
    def unmarshaller(self, typed=True):
        """
        Get the appropriate XML decoder.
        @return: Either the (basic|typed) unmarshaller.
        @rtype: L{UmxTyped}
        """
        if typed:
            return UmxTyped(self.schema())
        else:
            return UmxBasic()
        
    def marshaller(self):
        """
        Get the appropriate XML encoder.
        @return: An L{MxLiteral} marshaller.
        @rtype: L{MxLiteral}
        """
        return MxLiteral(self.schema(), self.options().xstq)
    
    def param_defs(self, method):
        """
        Get parameter definitions.  
        Each I{pdef} is a tuple (I{name}, L{xsd.sxbase.SchemaObject})
        @param method: A servic emethod.
        @type method: I{service.Method}
        @return: A collection of parameter definitions
        @rtype: [I{pdef},..]
        """
        raise Exception, 'not implemented'

    def get_message(self, method, args, kwargs):
        """
        Get the soap message for the specified method, args and soapheaders.
        This is the entry point for creating the outbound soap message.
        @param method: The method being invoked.
        @type method: I{service.Method}
        @param args: A list of args for the method invoked.
        @type args: list
        @param kwargs: Named (keyword) args for the method invoked.
        @type kwargs: dict
        @return: The soap envelope.
        @rtype: L{Document}
        """

        content = self.headercontent(method)
        header = self.header(content)
        content = self.bodycontent(method, args, kwargs)
        body = self.body(content)
        env = self.envelope(header, body)
        if self.options().prefixes:
            body.normalizePrefixes()
            env.promotePrefixes()
        else:
            env.refitPrefixes()
        return Document(env)
    
    def get_reply(self, method, reply):
        """
        Process the I{reply} for the specified I{method} by sax parsing the I{reply}
        and then unmarshalling into python object(s).
        @param method: The name of the invoked method.
        @type method: str
        @param reply: The reply XML received after invoking the specified method.
        @type reply: str
        @return: The unmarshalled reply.  The returned value is an L{Object} for a
            I{list} depending on whether the service returns a single object or a 
            collection.
        @rtype: tuple ( L{Element}, L{Object} )
        """
        reply = self.replyfilter(reply)
        sax = Parser()
        replyroot = sax.parse(string=reply)
        plugins = PluginContainer(self.options().plugins)
        plugins.message.parsed(reply=replyroot)
        soapenv = replyroot.getChild('Envelope')
        soapenv.promotePrefixes()
        soapbody = soapenv.getChild('Body')
        self.detect_fault(soapbody)
        soapbody = self.multiref.process(soapbody)
        nodes = self.replycontent(method, soapbody)
        rtypes = self.returned_types(method)
        if len(rtypes) > 1:
            result = self.replycomposite(rtypes, nodes)
            return (replyroot, result)
        if len(rtypes) == 1:
            if rtypes[0].unbounded():
                result = self.replylist(rtypes[0], nodes)
                return (replyroot, result)
            if len(nodes):
                unmarshaller = self.unmarshaller()
                resolved = rtypes[0].resolve(nobuiltin=True)
                result = unmarshaller.process(nodes[0], resolved)
                return (replyroot, result)
        return (replyroot, None)
    
    def detect_fault(self, body):
        """
        Detect I{hidden} soapenv:Fault element in the soap body.
        @param body: The soap envelope body.
        @type body: L{Element}
        @raise WebFault: When found.
        """
        fault = body.getChild('Fault', envns)
        if fault is None:
            return
        unmarshaller = self.unmarshaller(False)
        p = unmarshaller.process(fault)
        if self.options().faults:
            raise WebFault(p, fault)
        return self
        
    
    def replylist(self, rt, nodes):
        """
        Construct a I{list} reply.  This mehod is called when it has been detected
        that the reply is a list.
        @param rt: The return I{type}.
        @type rt: L{suds.xsd.sxbase.SchemaObject}
        @param nodes: A collection of XML nodes.
        @type nodes: [L{Element},...]
        @return: A list of I{unmarshalled} objects.
        @rtype: [L{Object},...]
        """
        result = []
        resolved = rt.resolve(nobuiltin=True)
        unmarshaller = self.unmarshaller()
        for node in nodes:
            sobject = unmarshaller.process(node, resolved)
            result.append(sobject)
        return result
    
    def replycomposite(self, rtypes, nodes):
        """
        Construct a I{composite} reply.  This method is called when it has been
        detected that the reply has multiple root nodes.
        @param rtypes: A list of known return I{types}.
        @type rtypes: [L{suds.xsd.sxbase.SchemaObject},...]
        @param nodes: A collection of XML nodes.
        @type nodes: [L{Element},...]
        @return: The I{unmarshalled} composite object.
        @rtype: L{Object},...
        """
        dictionary = {}
        for rt in rtypes:
            dictionary[rt.name] = rt
        unmarshaller = self.unmarshaller()
        composite = Factory.object('reply')
        for node in nodes:
            tag = node.name
            rt = dictionary.get(tag, None)
            if rt is None:
                if node.get('id') is None:
                    raise Exception('<%s/> not mapped to message part' % tag)
                else:
                    continue
            resolved = rt.resolve(nobuiltin=True)
            sobject = unmarshaller.process(node, resolved)
            value = getattr(composite, tag, None)
            if value is None:
                if rt.unbounded():
                    value = []
                    setattr(composite, tag, value)
                    value.append(sobject)
                else:
                    setattr(composite, tag, sobject)
            else:
                if not isinstance(value, list):
                    value = [value,]
                    setattr(composite, tag, value)
                value.append(sobject)          
        return composite
    
    def get_fault(self, reply):
        """
        Extract the fault from the specified soap reply.  If I{faults} is True, an
        exception is raised.  Otherwise, the I{unmarshalled} fault L{Object} is
        returned.  This method is called when the server raises a I{web fault}.
        @param reply: A soap reply message.
        @type reply: str
        @return: A fault object.
        @rtype: tuple ( L{Element}, L{Object} )
        """
        reply = self.replyfilter(reply)
        sax = Parser()
        faultroot = sax.parse(string=reply)
        soapenv = faultroot.getChild('Envelope')
        soapbody = soapenv.getChild('Body')
        fault = soapbody.getChild('Fault')
        unmarshaller = self.unmarshaller(False)
        p = unmarshaller.process(fault)
        if self.options().faults:
            raise WebFault(p, faultroot)
        return (faultroot, p.detail)
    
    def mkparam(self, method, pdef, object):
        """
        Builds a parameter for the specified I{method} using the parameter
        definition (pdef) and the specified value (object).
        @param method: A method name.
        @type method: str
        @param pdef: A parameter definition.
        @type pdef: tuple: (I{name}, L{xsd.sxbase.SchemaObject})
        @param object: The parameter value.
        @type object: any
        @return: The parameter fragment.
        @rtype: L{Element}
        """
        marshaller = self.marshaller()
        content = \
            Content(tag=pdef[0],
                    value=object, 
                    type=pdef[1], 
                    real=pdef[1].resolve())
        return marshaller.process(content)
    
    def mkheader(self, method, hdef, object):
        """
        Builds a soapheader for the specified I{method} using the header
        definition (hdef) and the specified value (object).
        @param method: A method name.
        @type method: str
        @param hdef: A header definition.
        @type hdef: tuple: (I{name}, L{xsd.sxbase.SchemaObject})
        @param object: The header value.
        @type object: any
        @return: The parameter fragment.
        @rtype: L{Element}
        """
        marshaller = self.marshaller()
        if isinstance(object, (list, tuple)):
            tags = []
            for item in object:
                tags.append(self.mkheader(method, hdef, item))
            return tags
        content = Content(tag=hdef[0], value=object, type=hdef[1])
        return marshaller.process(content)
            
    def envelope(self, header, body):
        """
        Build the B{<Envelope/>} for an soap outbound message.
        @param header: The soap message B{header}.
        @type header: L{Element}
        @param body: The soap message B{body}.
        @type body: L{Element}
        @return: The soap envelope containing the body and header.
        @rtype: L{Element}
        """
        env = Element('Envelope', ns=envns)
        env.addPrefix(Namespace.xsins[0], Namespace.xsins[1])
        env.append(header)
        env.append(body)
        return env
    
    def header(self, content):
        """
        Build the B{<Body/>} for an soap outbound message.
        @param content: The header content.
        @type content: L{Element}
        @return: the soap body fragment.
        @rtype: L{Element}
        """
        header = Element('Header', ns=envns)
        header.append(content)
        return header
    
    def bodycontent(self, method, args, kwargs):
        """
        Get the content for the soap I{body} node.
        @param method: A service method.
        @type method: I{service.Method}
        @param args: method parameter values
        @type args: list
        @param kwargs: Named (keyword) args for the method invoked.
        @type kwargs: dict
        @return: The xml content for the <body/>
        @rtype: [L{Element},..]
        """
        raise Exception, 'not implemented'
    
    def headercontent(self, method):
        """
        Get the content for the soap I{Header} node.
        @param method: A service method.
        @type method: I{service.Method}
        @return: The xml content for the <body/>
        @rtype: [L{Element},..]
        """
        n = 0
        content = []
        wsse = self.options().wsse
        if wsse is not None:
            content.append(wsse.xml())
        headers = self.options().soapheaders
        if not isinstance(headers, (tuple,list,dict)):
            headers = (headers,)
        if len(headers) == 0:
            return content
        pts = self.headpart_types(method)
        if isinstance(headers, (tuple,list)):
            for header in headers:
                if isinstance(header, Element):
                    content.append(deepcopy(header))
                    continue
                if len(pts) == n: break
                h = self.mkheader(method, pts[n], header)
                ns = pts[n][1].namespace('ns0')
                h.setPrefix(ns[0], ns[1])
                content.append(h)
                n += 1
        else:
            for pt in pts:
                header = headers.get(pt[0])
                if header is None:
                    continue
                h = self.mkheader(method, pt, header)
                ns = pt[1].namespace('ns0')
                h.setPrefix(ns[0], ns[1])
                content.append(h)
        return content
    
    def replycontent(self, method, body):
        """
        Get the reply body content.
        @param method: A service method.
        @type method: I{service.Method}
        @param body: The soap body
        @type body: L{Element}
        @return: the body content
        @rtype: [L{Element},...]
        """
        raise Exception, 'not implemented'
    
    def body(self, content):
        """
        Build the B{<Body/>} for an soap outbound message.
        @param content: The body content.
        @type content: L{Element}
        @return: the soap body fragment.
        @rtype: L{Element}
        """
        body = Element('Body', ns=envns)
        body.append(content)
        return body
    
    def bodypart_types(self, method, input=True):
        """
        Get a list of I{parameter definitions} (pdef) defined for the specified method.
        Each I{pdef} is a tuple (I{name}, L{xsd.sxbase.SchemaObject})
        @param method: A service method.
        @type method: I{service.Method}
        @param input: Defines input/output message.
        @type input: boolean
        @return:  A list of parameter definitions
        @rtype: [I{pdef},]
        """
        result = []
        if input:
            parts = method.soap.input.body.parts
        else:
            parts = method.soap.output.body.parts
        for p in parts:
            if p.element is not None:
                query = ElementQuery(p.element)
            else:
                query = TypeQuery(p.type)
            pt = query.execute(self.schema())
            if pt is None:
                raise TypeNotFound(query.ref)
            if p.type is not None:
                pt = PartElement(p.name, pt)
            if input:
                if pt.name is None:
                    result.append((p.name, pt))
                else:
                    result.append((pt.name, pt))
            else:
                result.append(pt)
        return result
    
    def headpart_types(self, method, input=True):
        """
        Get a list of I{parameter definitions} (pdef) defined for the specified method.
        Each I{pdef} is a tuple (I{name}, L{xsd.sxbase.SchemaObject})
        @param method: A service method.
        @type method: I{service.Method}
        @param input: Defines input/output message.
        @type input: boolean
        @return:  A list of parameter definitions
        @rtype: [I{pdef},]
        """
        result = []
        if input:
            headers = method.soap.input.headers
        else:
            headers = method.soap.output.headers
        for header in headers:
            part = header.part
            if part.element is not None:
                query = ElementQuery(part.element)
            else:
                query = TypeQuery(part.type)
            pt = query.execute(self.schema())
            if pt is None:
                raise TypeNotFound(query.ref)
            if part.type is not None:
                pt = PartElement(part.name, pt)
            if input:
                if pt.name is None:
                    result.append((part.name, pt))
                else:
                    result.append((pt.name, pt))
            else:
                result.append(pt)
        return result
    
    def returned_types(self, method):
        """
        Get the L{xsd.sxbase.SchemaObject} returned by the I{method}.
        @param method: A service method.
        @type method: I{service.Method}
        @return: The name of the type return by the method.
        @rtype: [I{rtype},..]
        """
        result = []
        for rt in self.bodypart_types(method, input=False):
            result.append(rt)
        return result


class PartElement(SchemaElement):
    """
    A part used to represent a message part when the part
    references a schema type and thus assumes to be an element.
    @ivar resolved: The part type.
    @type resolved: L{suds.xsd.sxbase.SchemaObject}
    """
    
    def __init__(self, name, resolved):
        """
        @param name: The part name.
        @type name: str
        @param resolved: The part type.
        @type resolved: L{suds.xsd.sxbase.SchemaObject}
        """
        root = Element('element', ns=Namespace.xsdns)
        SchemaElement.__init__(self, resolved.schema, root)
        self.__resolved = resolved
        self.name = name
        self.form_qualified = False
        
    def implany(self):
        return self
    
    def optional(self):
        return True
        
    def namespace(self, prefix=None):
        return Namespace.default
        
    def resolve(self, nobuiltin=False):
        if nobuiltin and self.__resolved.builtin():
            return self
        else:
            return self.__resolved
    
########NEW FILE########
__FILENAME__ = document
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides classes for the (WS) SOAP I{document/literal}.
"""

from logging import getLogger
from suds import *
from suds.bindings.binding import Binding
from suds.sax.element import Element

log = getLogger(__name__)


class Document(Binding):
    """
    The document/literal style.  Literal is the only (@use) supported
    since document/encoded is pretty much dead.
    Although the soap specification supports multiple documents within the soap
    <body/>, it is very uncommon.  As such, suds presents an I{RPC} view of
    service methods defined with a single document parameter.  This is done so
    that the user can pass individual parameters instead of one, single document.
    To support the complete specification, service methods defined with multiple documents
    (multiple message parts), must present a I{document} view for that method.
    """

    def bodycontent(self, method, args, kwargs):
        #
        # The I{wrapped} vs I{bare} style is detected in 2 ways.
        # If there is 2+ parts in the message then it is I{bare}.
        # If there is only (1) part and that part resolves to a builtin then
        # it is I{bare}.  Otherwise, it is I{wrapped}.
        #
        if not len(method.soap.input.body.parts):
            return ()
        wrapped = method.soap.input.body.wrapped
        if wrapped:
            pts = self.bodypart_types(method)
            root = self.document(pts[0])
        else:
            root = []
        n = 0
        for pd in self.param_defs(method):
            if n < len(args):
                value = args[n]
            else:
                value = kwargs.get(pd[0])
            n += 1
            p = self.mkparam(method, pd, value)
            if p is None:
                continue
            if not wrapped:
                ns = pd[1].namespace('ns0')
                p.setPrefix(ns[0], ns[1])
            root.append(p)
        return root

    def replycontent(self, method, body):
        wrapped = method.soap.output.body.wrapped
        if wrapped:
            return body[0].children
        else:
            return body.children

    def document(self, wrapper):
        """
        Get the document root.  For I{document/literal}, this is the
        name of the wrapper element qualifed by the schema tns.
        @param wrapper: The method name.
        @type wrapper: L{xsd.sxbase.SchemaObject}
        @return: A root element.
        @rtype: L{Element}
        """
        tag = wrapper[1].name
        ns = wrapper[1].namespace('ns0')
        d = Element(tag, ns=ns)
        return d

    def mkparam(self, method, pdef, object):
        #
        # Expand list parameters into individual parameters
        # each with the type information.  This is because in document
        # arrays are simply unbounded elements.
        #
        if isinstance(object, (list, tuple)):
            tags = []
            for item in object:
                tags.append(self.mkparam(method, pdef, item))
            return tags
        else:
            return Binding.mkparam(self, method, pdef, object)

    def param_defs(self, method):
        #
        # Get parameter definitions for document literal.
        # The I{wrapped} vs I{bare} style is detected in 2 ways.
        # If there is 2+ parts in the message then it is I{bare}.
        # If there is only (1) part and that part resolves to a builtin then
        # it is I{bare}.  Otherwise, it is I{wrapped}.
        #
        pts = self.bodypart_types(method)
        wrapped = method.soap.input.body.wrapped
        if not wrapped:
            return pts
        result = []
        # wrapped
        for p in pts:
            resolved = p[1].resolve()
            for child, ancestry in resolved:
                if child.isattr():
                    continue
                if self.bychoice(ancestry):
                    #log.debug(
                    #    '%s\ncontained by <choice/>, excluded as param for %s()',
                    #    child,
                    #    method.name)
                    continue
                result.append((child.name, child))
        return result

    def returned_types(self, method):
        result = []
        wrapped = method.soap.output.body.wrapped
        rts = self.bodypart_types(method, input=False)
        if wrapped:
            for pt in rts:
                resolved = pt.resolve(nobuiltin=True)
                for child, ancestry in resolved:
                    result.append(child)
                break
        else:
            result += rts
        return result

    def bychoice(self, ancestry):
        """
        The ancestry contains a <choice/>
        @param ancestry: A list of ancestors.
        @type ancestry: list
        @return: True if contains <choice/>
        @rtype: boolean
        """
        for x in ancestry:
            if x.choice():
                return True
        return False

########NEW FILE########
__FILENAME__ = multiref
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides classes for handling soap multirefs.
"""

from logging import getLogger
from suds import *
from suds.sax.element import Element

log = getLogger(__name__)

soapenc = (None, 'http://schemas.xmlsoap.org/soap/encoding/')

class MultiRef:
    """
    Resolves and replaces multirefs.
    @ivar nodes: A list of non-multiref nodes.
    @type nodes: list
    @ivar catalog: A dictionary of multiref nodes by id.
    @type catalog: dict
    """

    def __init__(self):
        self.nodes = []
        self.catalog = {}

    def process(self, body):
        """
        Process the specified soap envelope body and replace I{multiref} node
        references with the contents of the referenced node.
        @param body: A soap envelope body node.
        @type body: L{Element}
        @return: The processed I{body}
        @rtype: L{Element}
        """
        self.nodes = []
        self.catalog = {}
        self.build_catalog(body)
        self.update(body)
        body.children = self.nodes
        return body

    def update(self, node):
        """
        Update the specified I{node} by replacing the I{multiref} references with
        the contents of the referenced nodes and remove the I{href} attribute.
        @param node: A node to update.
        @type node: L{Element}
        @return: The updated node
        @rtype: L{Element}
        """
        self.replace_references(node)
        for c in node.children:
            self.update(c)
        return node

    def replace_references(self, node):
        """
        Replacing the I{multiref} references with the contents of the
        referenced nodes and remove the I{href} attribute.  Warning:  since
        the I{ref} is not cloned,
        @param node: A node to update.
        @type node: L{Element}
        """
        href = node.getAttribute('href')
        if href is None:
            return
        id = href.getValue()
        ref = self.catalog.get(id)
        if ref is None:
            log.error('soap multiref: %s, not-resolved', id)
            return
        node.append(ref.children)
        node.setText(ref.getText())
        for a in ref.attributes:
            if a.name != 'id':
                node.append(a)
        node.remove(href)

    def build_catalog(self, body):
        """
        Create the I{catalog} of multiref nodes by id and the list of
        non-multiref nodes.
        @param body: A soap envelope body node.
        @type body: L{Element}
        """
        for child in body.children:
            if self.soaproot(child):
                self.nodes.append(child)
            id = child.get('id')
            if id is None: continue
            key = '#%s' % id
            self.catalog[key] = child

    def soaproot(self, node):
        """
        Get whether the specified I{node} is a soap encoded root.
        This is determined by examining @soapenc:root='1'.
        The node is considered to be a root when the attribute
        is not specified.
        @param node: A node to evaluate.
        @type node: L{Element}
        @return: True if a soap encoded root.
        @rtype: bool
        """
        root = node.getAttribute('root', ns=soapenc)
        if root is None:
            return True
        else:
            return ( root.value == '1' )

########NEW FILE########
__FILENAME__ = rpc
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides classes for the (WS) SOAP I{rpc/literal} and I{rpc/encoded} bindings.
"""

from logging import getLogger
from suds import *
from suds.mx.encoded import Encoded as MxEncoded
from suds.umx.encoded import Encoded as UmxEncoded
from suds.bindings.binding import Binding, envns
from suds.sax.element import Element

log = getLogger(__name__)


encns = ('SOAP-ENC', 'http://schemas.xmlsoap.org/soap/encoding/')

class RPC(Binding):
    """
    RPC/Literal binding style.
    """
    
    def param_defs(self, method):
        return self.bodypart_types(method)
        
    def envelope(self, header, body):
        env = Binding.envelope(self, header, body)
        env.addPrefix(encns[0], encns[1])
        env.set('%s:encodingStyle' % envns[0], 
                'http://schemas.xmlsoap.org/soap/encoding/')
        return env
        
    def bodycontent(self, method, args, kwargs):
        n = 0
        root = self.method(method)
        for pd in self.param_defs(method):
            if n < len(args):
                value = args[n]
            else:
                value = kwargs.get(pd[0])
            p = self.mkparam(method, pd, value)
            if p is not None:
                root.append(p)
            n += 1
        return root
    
    def replycontent(self, method, body):
        return body[0].children
        
    def method(self, method):
        """
        Get the document root.  For I{rpc/(literal|encoded)}, this is the
        name of the method qualifed by the schema tns.
        @param method: A service method.
        @type method: I{service.Method}
        @return: A root element.
        @rtype: L{Element}
        """
        ns = method.soap.input.body.namespace
        if ns[0] is None:
            ns = ('ns0', ns[1])
        method = Element(method.name, ns=ns)
        return method
    

class Encoded(RPC):
    """
    RPC/Encoded (section 5)  binding style.
    """

    def marshaller(self):
        return MxEncoded(self.schema())

    def unmarshaller(self, typed=True):
        """
        Get the appropriate XML decoder.
        @return: Either the (basic|typed) unmarshaller.
        @rtype: L{UmxTyped}
        """
        if typed:
            return UmxEncoded(self.schema())
        else:
            return RPC.unmarshaller(self, typed)

########NEW FILE########
__FILENAME__ = builder
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The I{builder} module provides an wsdl/xsd defined types factory
"""

from logging import getLogger
from suds import *
from suds.sudsobject import Factory

log = getLogger(__name__)


class Builder:
    """ Builder used to construct an object for types defined in the schema """

    def __init__(self, resolver):
        """
        @param resolver: A schema object name resolver.
        @type resolver: L{resolver.Resolver}
        """
        self.resolver = resolver

    def build(self, name):
        """ build a an object for the specified typename as defined in the schema """
        if isinstance(name, basestring):
            type = self.resolver.find(name)
            if type is None:
                raise TypeNotFound(name)
        else:
            type = name
        cls = type.name
        if type.mixed():
            data = Factory.property(cls)
        else:
            data = Factory.object(cls)
        resolved = type.resolve()
        md = data.__metadata__
        md.sxtype = resolved
        md.ordering = self.ordering(resolved)
        history = []
        self.add_attributes(data, resolved)
        for child, ancestry in type.children():
            if self.skip_child(child, ancestry):
                continue
            self.process(data, child, history[:])
        return data

    def process(self, data, type, history):
        """ process the specified type then process its children """
        if type in history:
            return
        if type.enum():
            return
        history.append(type)
        resolved = type.resolve()
        value = None
        if type.unbounded():
            value = []
        else:
            if len(resolved) > 0:
                if resolved.mixed():
                    value = Factory.property(resolved.name)
                    md = value.__metadata__
                    md.sxtype = resolved
                else:
                    value = Factory.object(resolved.name)
                    md = value.__metadata__
                    md.sxtype = resolved
                    md.ordering = self.ordering(resolved)
        setattr(data, type.name, value)
        if value is not None:
            data = value
        if not isinstance(data, list):
            self.add_attributes(data, resolved)
            for child, ancestry in resolved.children():
                if self.skip_child(child, ancestry):
                    continue
                self.process(data, child, history[:])

    def add_attributes(self, data, type):
        """ add required attributes """
        for attr, ancestry in type.attributes():
            name = '_%s' % attr.name
            value = attr.get_default()
            setattr(data, name, value)

    def skip_child(self, child, ancestry):
        """ get whether or not to skip the specified child """
        if child.any(): return True
        for x in ancestry:
            if x.choice():
                return True
        return False

    def ordering(self, type):
        """ get the ordering """
        result = []
        for child, ancestry in type.resolve():
            name = child.name
            if child.name is None:
                continue
            if child.isattr():
                name = '_%s' % child.name
            result.append(name)
        return result

########NEW FILE########
__FILENAME__ = cache
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Contains basic caching classes.
"""

import os
import suds
from tempfile import gettempdir as tmp
from suds.transport import *
from suds.sax.parser import Parser
from suds.sax.element import Element
from datetime import datetime as dt
from datetime import timedelta
from cStringIO import StringIO
from logging import getLogger
try:
    import cPickle as pickle
except:
    import pickle

log = getLogger(__name__)


class Cache:
    """
    An object object cache.
    """

    def get(self, id):
        """
        Get a object from the cache by ID.
        @param id: The object ID.
        @type id: str
        @return: The object, else None
        @rtype: any
        """
        raise Exception('not-implemented')

    def getf(self, id):
        """
        Get a object from the cache by ID.
        @param id: The object ID.
        @type id: str
        @return: The object, else None
        @rtype: any
        """
        raise Exception('not-implemented')

    def put(self, id, object):
        """
        Put a object into the cache.
        @param id: The object ID.
        @type id: str
        @param object: The object to add.
        @type object: any
        """
        raise Exception('not-implemented')

    def putf(self, id, fp):
        """
        Write a fp into the cache.
        @param id: The object ID.
        @type id: str
        @param fp: File pointer.
        @type fp: file-like object.
        """
        raise Exception('not-implemented')

    def purge(self, id):
        """
        Purge a object from the cache by id.
        @param id: A object ID.
        @type id: str
        """
        raise Exception('not-implemented')

    def clear(self):
        """
        Clear all objects from the cache.
        """
        raise Exception('not-implemented')


class NoCache(Cache):
    """
    The passthru object cache.
    """

    def get(self, id):
        return None

    def getf(self, id):
        return None

    def put(self, id, object):
        pass

    def putf(self, id, fp):
        pass


class FileCache(Cache):
    """
    A file-based URL cache.
    @cvar fnprefix: The file name prefix.
    @type fnsuffix: str
    @ivar duration: The cached file duration which defines how
        long the file will be cached.
    @type duration: (unit, value)
    @ivar location: The directory for the cached files.
    @type location: str
    """
    fnprefix = 'suds'
    units = ('months', 'weeks', 'days', 'hours', 'minutes', 'seconds')

    def __init__(self, location=None, **duration):
        """
        @param location: The directory for the cached files.
        @type location: str
        @param duration: The cached file duration which defines how
            long the file will be cached.  A duration=0 means forever.
            The duration may be: (months|weeks|days|hours|minutes|seconds).
        @type duration: {unit:value}
        """
        if location is None:
            location = os.path.join(tmp(), 'suds')
        self.location = location
        self.duration = (None, 0)
        self.setduration(**duration)
        self.checkversion()

    def fnsuffix(self):
        """
        Get the file name suffix
        @return: The suffix
        @rtype: str
        """
        return 'gcf'

    def setduration(self, **duration):
        """
        Set the caching duration which defines how long the
        file will be cached.
        @param duration: The cached file duration which defines how
            long the file will be cached.  A duration=0 means forever.
            The duration may be: (months|weeks|days|hours|minutes|seconds).
        @type duration: {unit:value}
        """
        if len(duration) == 1:
            arg = duration.items()[0]
            if not arg[0] in self.units:
                raise Exception('must be: %s' % str(self.units))
            self.duration = arg
        return self

    def setlocation(self, location):
        """
        Set the location (directory) for the cached files.
        @param location: The directory for the cached files.
        @type location: str
        """
        self.location = location

    def mktmp(self):
        """
        Make the I{location} directory if it doesn't already exits.
        """
        try:
            if not os.path.isdir(self.location):
                os.makedirs(self.location)
        except:
            log.debug(self.location, exc_info=1)
        return self

    def put(self, id, bfr):
        try:
            fn = self.__fn(id)
            f = self.open(fn, 'w')
            f.write(bfr)
            f.close()
            return bfr
        except:
            log.debug(id, exc_info=1)
            return bfr

    def putf(self, id, fp):
        try:
            fn = self.__fn(id)
            f = self.open(fn, 'w')
            f.write(fp.read())
            fp.close()
            f.close()
            return open(fn)
        except:
            log.debug(id, exc_info=1)
            return fp

    def get(self, id):
        try:
            f = self.getf(id)
            bfr = f.read()
            f.close()
            return bfr
        except:
            pass

    def getf(self, id):
        try:
            fn = self.__fn(id)
            self.validate(fn)
            return self.open(fn)
        except:
            pass

    def validate(self, fn):
        """
        Validate that the file has not expired based on the I{duration}.
        @param fn: The file name.
        @type fn: str
        """
        if self.duration[1] < 1:
            return
        created = dt.fromtimestamp(os.path.getctime(fn))
        d = { self.duration[0]:self.duration[1] }
        expired = created+timedelta(**d)
        if expired < dt.now():
            #log.debug('%s expired, deleted', fn)
            os.remove(fn)

    def clear(self):
        for fn in os.listdir(self.location):
            if os.path.isdir(fn):
                continue
            if fn.startswith(self.fnprefix):
                #log.debug('deleted: %s', fn)
                os.remove(os.path.join(self.location, fn))

    def purge(self, id):
        fn = self.__fn(id)
        try:
            os.remove(fn)
        except:
            pass

    def open(self, fn, *args):
        """
        Open the cache file making sure the directory is created.
        """
        self.mktmp()
        return open(fn, *args)

    def checkversion(self):
        path = os.path.join(self.location, 'version')
        try:

            f = self.open(path)
            version = f.read()
            f.close()
            if version != suds.__version__:
                raise Exception()
        except:
            self.clear()
            f = self.open(path, 'w')
            f.write(suds.__version__)
            f.close()

    def __fn(self, id):
        name = id
        suffix = self.fnsuffix()
        fn = '%s-%s.%s' % (self.fnprefix, name, suffix)
        return os.path.join(self.location, fn)


class DocumentCache(FileCache):
    """
    Provides xml document caching.
    """

    def fnsuffix(self):
        return 'xml'

    def get(self, id):
        try:
            fp = FileCache.getf(self, id)
            if fp is None:
                return None
            p = Parser()
            return p.parse(fp)
        except:
            FileCache.purge(self, id)

    def put(self, id, object):
        if isinstance(object, Element):
            FileCache.put(self, id, str(object))
        return object


class ObjectCache(FileCache):
    """
    Provides pickled object caching.
    @cvar protocol: The pickling protocol.
    @type protocol: int
    """
    protocol = 2

    def fnsuffix(self):
        return 'px'

    def get(self, id):
        try:
            fp = FileCache.getf(self, id)
            if fp is None:
                return None
            else:
                return pickle.load(fp)
        except:
            FileCache.purge(self, id)

    def put(self, id, object):
        bfr = pickle.dumps(object, self.protocol)
        FileCache.put(self, id, bfr)
        return object

########NEW FILE########
__FILENAME__ = client
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The I{2nd generation} service proxy provides access to web services.
See I{README.txt}
"""

import suds
import suds.metrics as metrics
from cookielib import CookieJar
from suds import *
from suds.reader import DefinitionsReader
from suds.transport import TransportError, Request
from suds.transport.https import HttpAuthenticated
from suds.servicedefinition import ServiceDefinition
from suds import sudsobject
from sudsobject import Factory as InstFactory
from sudsobject import Object
from suds.resolver import PathResolver
from suds.builder import Builder
from suds.wsdl import Definitions
from suds.cache import ObjectCache
from suds.sax.document import Document
from suds.sax.parser import Parser
from suds.options import Options
from suds.properties import Unskin
from urlparse import urlparse
from copy import deepcopy
from suds.plugin import PluginContainer
from logging import getLogger

log = getLogger(__name__)


class Client(object):
    """
    A lightweight web services client.
    I{(2nd generation)} API.
    @ivar wsdl: The WSDL object.
    @type wsdl:L{Definitions}
    @ivar service: The service proxy used to invoke operations.
    @type service: L{Service}
    @ivar factory: The factory used to create objects.
    @type factory: L{Factory}
    @ivar sd: The service definition
    @type sd: L{ServiceDefinition}
    @ivar messages: The last sent/received messages.
    @type messages: str[2]
    """
    @classmethod
    def items(cls, sobject):
        """
        Extract the I{items} from a suds object much like the
        items() method works on I{dict}.
        @param sobject: A suds object
        @type sobject: L{Object}
        @return: A list of items contained in I{sobject}.
        @rtype: [(key, value),...]
        """
        return sudsobject.items(sobject)

    @classmethod
    def dict(cls, sobject):
        """
        Convert a sudsobject into a dictionary.
        @param sobject: A suds object
        @type sobject: L{Object}
        @return: A python dictionary containing the
            items contained in I{sobject}.
        @rtype: dict
        """
        return sudsobject.asdict(sobject)

    @classmethod
    def metadata(cls, sobject):
        """
        Extract the metadata from a suds object.
        @param sobject: A suds object
        @type sobject: L{Object}
        @return: The object's metadata
        @rtype: L{sudsobject.Metadata}
        """
        return sobject.__metadata__

    def __init__(self, url, **kwargs):
        """
        @param url: The URL for the WSDL.
        @type url: str
        @param kwargs: keyword arguments.
        @see: L{Options}
        """
        options = Options()
        options.transport = HttpAuthenticated()
        self.options = options
        options.cache = ObjectCache(days=1)
        self.set_options(**kwargs)
        reader = DefinitionsReader(options, Definitions)
        self.wsdl = reader.open(url)
        plugins = PluginContainer(options.plugins)
        plugins.init.initialized(wsdl=self.wsdl)
        self.factory = Factory(self.wsdl)
        self.service = ServiceSelector(self, self.wsdl.services)
        self.sd = []
        for s in self.wsdl.services:
            sd = ServiceDefinition(self.wsdl, s)
            self.sd.append(sd)
        self.messages = dict(tx=None, rx=None)

    def set_options(self, **kwargs):
        """
        Set options.
        @param kwargs: keyword arguments.
        @see: L{Options}
        """
        p = Unskin(self.options)
        p.update(kwargs)

    def add_prefix(self, prefix, uri):
        """
        Add I{static} mapping of an XML namespace prefix to a namespace.
        This is useful for cases when a wsdl and referenced schemas make heavy
        use of namespaces and those namespaces are subject to changed.
        @param prefix: An XML namespace prefix.
        @type prefix: str
        @param uri: An XML namespace URI.
        @type uri: str
        @raise Exception: when prefix is already mapped.
        """
        root = self.wsdl.root
        mapped = root.resolvePrefix(prefix, None)
        if mapped is None:
            root.addPrefix(prefix, uri)
            return
        if mapped[1] != uri:
            raise Exception('"%s" already mapped as "%s"' % (prefix, mapped))

    def last_sent(self):
        """
        Get last sent I{soap} message.
        @return: The last sent I{soap} message.
        @rtype: L{Document}
        """
        return self.messages.get('tx')

    def last_received(self):
        """
        Get last received I{soap} message.
        @return: The last received I{soap} message.
        @rtype: L{Document}
        """
        return self.messages.get('rx')

    def clone(self):
        """
        Get a shallow clone of this object.
        The clone only shares the WSDL.  All other attributes are
        unique to the cloned object including options.
        @return: A shallow clone.
        @rtype: L{Client}
        """
        class Uninitialized(Client):
            def __init__(self):
                pass
        clone = Uninitialized()
        clone.options = Options()
        cp = Unskin(clone.options)
        mp = Unskin(self.options)
        cp.update(deepcopy(mp))
        clone.wsdl = self.wsdl
        clone.factory = self.factory
        clone.service = ServiceSelector(clone, self.wsdl.services)
        clone.sd = self.sd
        clone.messages = dict(tx=None, rx=None)
        return clone

    def __str__(self):
        return unicode(self)

    def __unicode__(self):
        s = ['\n']
        build = suds.__build__.split()
        s.append('Suds ( https://fedorahosted.org/suds/ )')
        s.append('  version: %s' % suds.__version__)
        s.append(' %s  build: %s' % (build[0], build[1]))
        for sd in self.sd:
            s.append('\n\n%s' % unicode(sd))
        return ''.join(s)


class Factory:
    """
    A factory for instantiating types defined in the wsdl
    @ivar resolver: A schema type resolver.
    @type resolver: L{PathResolver}
    @ivar builder: A schema object builder.
    @type builder: L{Builder}
    """

    def __init__(self, wsdl):
        """
        @param wsdl: A schema object.
        @type wsdl: L{wsdl.Definitions}
        """
        self.wsdl = wsdl
        self.resolver = PathResolver(wsdl)
        self.builder = Builder(self.resolver)

    def create(self, name):
        """
        create a WSDL type by name
        @param name: The name of a type defined in the WSDL.
        @type name: str
        @return: The requested object.
        @rtype: L{Object}
        """
        timer = metrics.Timer()
        timer.start()
        type = self.resolver.find(name)
        if type is None:
            raise TypeNotFound(name)
        if type.enum():
            result = InstFactory.object(name)
            for e, a in type.children():
                setattr(result, e.name, e.name)
        else:
            try:
                result = self.builder.build(type)
            except Exception, e:
                log.error("create '%s' failed", name, exc_info=True)
                raise BuildError(name, e)
        timer.stop()
        #metrics.log.debug('%s created: %s', name, timer)
        return result

    def separator(self, ps):
        """
        Set the path separator.
        @param ps: The new path separator.
        @type ps: char
        """
        self.resolver = PathResolver(self.wsdl, ps)


class ServiceSelector:
    """
    The B{service} selector is used to select a web service.
    In most cases, the wsdl only defines (1) service in which access
    by subscript is passed through to a L{PortSelector}.  This is also the
    behavior when a I{default} service has been specified.  In cases
    where multiple services have been defined and no default has been
    specified, the service is found by name (or index) and a L{PortSelector}
    for the service is returned.  In all cases, attribute access is
    forwarded to the L{PortSelector} for either the I{first} service or the
    I{default} service (when specified).
    @ivar __client: A suds client.
    @type __client: L{Client}
    @ivar __services: A list of I{wsdl} services.
    @type __services: list
    """
    def __init__(self, client, services):
        """
        @param client: A suds client.
        @type client: L{Client}
        @param services: A list of I{wsdl} services.
        @type services: list
        """
        self.__client = client
        self.__services = services

    def __getattr__(self, name):
        """
        Request to access an attribute is forwarded to the
        L{PortSelector} for either the I{first} service or the
        I{default} service (when specified).
        @param name: The name of a method.
        @type name: str
        @return: A L{PortSelector}.
        @rtype: L{PortSelector}.
        """
        default = self.__ds()
        if default is None:
            port = self.__find(0)
        else:
            port = default
        return getattr(port, name)

    def __getitem__(self, name):
        """
        Provides selection of the I{service} by name (string) or
        index (integer).  In cases where only (1) service is defined
        or a I{default} has been specified, the request is forwarded
        to the L{PortSelector}.
        @param name: The name (or index) of a service.
        @type name: (int|str)
        @return: A L{PortSelector} for the specified service.
        @rtype: L{PortSelector}.
        """
        if len(self.__services) == 1:
            port = self.__find(0)
            return port[name]
        default = self.__ds()
        if default is not None:
            port = default
            return port[name]
        return self.__find(name)

    def __find(self, name):
        """
        Find a I{service} by name (string) or index (integer).
        @param name: The name (or index) of a service.
        @type name: (int|str)
        @return: A L{PortSelector} for the found service.
        @rtype: L{PortSelector}.
        """
        service = None
        if not len(self.__services):
            raise Exception, 'No services defined'
        if isinstance(name, int):
            try:
                service = self.__services[name]
                name = service.name
            except IndexError:
                raise ServiceNotFound, 'at [%d]' % name
        else:
            for s in self.__services:
                if name == s.name:
                    service = s
                    break
        if service is None:
            raise ServiceNotFound, name
        return PortSelector(self.__client, service.ports, name)

    def __ds(self):
        """
        Get the I{default} service if defined in the I{options}.
        @return: A L{PortSelector} for the I{default} service.
        @rtype: L{PortSelector}.
        """
        ds = self.__client.options.service
        if ds is None:
            return None
        else:
            return self.__find(ds)


class PortSelector:
    """
    The B{port} selector is used to select a I{web service} B{port}.
    In cases where multiple ports have been defined and no default has been
    specified, the port is found by name (or index) and a L{MethodSelector}
    for the port is returned.  In all cases, attribute access is
    forwarded to the L{MethodSelector} for either the I{first} port or the
    I{default} port (when specified).
    @ivar __client: A suds client.
    @type __client: L{Client}
    @ivar __ports: A list of I{service} ports.
    @type __ports: list
    @ivar __qn: The I{qualified} name of the port (used for logging).
    @type __qn: str
    """
    def __init__(self, client, ports, qn):
        """
        @param client: A suds client.
        @type client: L{Client}
        @param ports: A list of I{service} ports.
        @type ports: list
        @param qn: The name of the service.
        @type qn: str
        """
        self.__client = client
        self.__ports = ports
        self.__qn = qn

    def __getattr__(self, name):
        """
        Request to access an attribute is forwarded to the
        L{MethodSelector} for either the I{first} port or the
        I{default} port (when specified).
        @param name: The name of a method.
        @type name: str
        @return: A L{MethodSelector}.
        @rtype: L{MethodSelector}.
        """
        default = self.__dp()
        if default is None:
            m = self.__find(0)
        else:
            m = default
        return getattr(m, name)

    def __getitem__(self, name):
        """
        Provides selection of the I{port} by name (string) or
        index (integer).  In cases where only (1) port is defined
        or a I{default} has been specified, the request is forwarded
        to the L{MethodSelector}.
        @param name: The name (or index) of a port.
        @type name: (int|str)
        @return: A L{MethodSelector} for the specified port.
        @rtype: L{MethodSelector}.
        """
        default = self.__dp()
        if default is None:
            return self.__find(name)
        else:
            return default

    def __find(self, name):
        """
        Find a I{port} by name (string) or index (integer).
        @param name: The name (or index) of a port.
        @type name: (int|str)
        @return: A L{MethodSelector} for the found port.
        @rtype: L{MethodSelector}.
        """
        port = None
        if not len(self.__ports):
            raise Exception, 'No ports defined: %s' % self.__qn
        if isinstance(name, int):
            qn = '%s[%d]' % (self.__qn, name)
            try:
                port = self.__ports[name]
            except IndexError:
                raise PortNotFound, qn
        else:
            qn = '.'.join((self.__qn, name))
            for p in self.__ports:
                if name == p.name:
                    port = p
                    break
        if port is None:
            raise PortNotFound, qn
        qn = '.'.join((self.__qn, port.name))
        return MethodSelector(self.__client, port.methods, qn)

    def __dp(self):
        """
        Get the I{default} port if defined in the I{options}.
        @return: A L{MethodSelector} for the I{default} port.
        @rtype: L{MethodSelector}.
        """
        dp = self.__client.options.port
        if dp is None:
            return None
        else:
            return self.__find(dp)


class MethodSelector:
    """
    The B{method} selector is used to select a B{method} by name.
    @ivar __client: A suds client.
    @type __client: L{Client}
    @ivar __methods: A dictionary of methods.
    @type __methods: dict
    @ivar __qn: The I{qualified} name of the method (used for logging).
    @type __qn: str
    """
    def __init__(self, client, methods, qn):
        """
        @param client: A suds client.
        @type client: L{Client}
        @param methods: A dictionary of methods.
        @type methods: dict
        @param qn: The I{qualified} name of the port.
        @type qn: str
        """
        self.__client = client
        self.__methods = methods
        self.__qn = qn

    def __getattr__(self, name):
        """
        Get a method by name and return it in an I{execution wrapper}.
        @param name: The name of a method.
        @type name: str
        @return: An I{execution wrapper} for the specified method name.
        @rtype: L{Method}
        """
        return self[name]

    def __getitem__(self, name):
        """
        Get a method by name and return it in an I{execution wrapper}.
        @param name: The name of a method.
        @type name: str
        @return: An I{execution wrapper} for the specified method name.
        @rtype: L{Method}
        """
        m = self.__methods.get(name)
        if m is None:
            qn = '.'.join((self.__qn, name))
            raise MethodNotFound, qn
        return Method(self.__client, m)


class Method:
    """
    The I{method} (namespace) object.
    @ivar client: A client object.
    @type client: L{Client}
    @ivar method: A I{wsdl} method.
    @type I{wsdl} Method.
    """

    def __init__(self, client, method):
        """
        @param client: A client object.
        @type client: L{Client}
        @param method: A I{raw} method.
        @type I{raw} Method.
        """
        self.client = client
        self.method = method

    def __call__(self, *args, **kwargs):
        """
        Invoke the method.
        """
        clientclass = self.clientclass(kwargs)
        client = clientclass(self.client, self.method)
        if not self.faults():
            try:
                return client.invoke(args, kwargs)
            except WebFault, e:
                return (500, e)
        else:
            return client.invoke(args, kwargs)

    def faults(self):
        """ get faults option """
        return self.client.options.faults

    def clientclass(self, kwargs):
        """ get soap client class """
        if SimClient.simulation(kwargs):
            return SimClient
        else:
            return SoapClient


class SoapClient:
    """
    A lightweight soap based web client B{**not intended for external use}
    @ivar service: The target method.
    @type service: L{Service}
    @ivar method: A target method.
    @type method: L{Method}
    @ivar options: A dictonary of options.
    @type options: dict
    @ivar cookiejar: A cookie jar.
    @type cookiejar: libcookie.CookieJar
    """

    def __init__(self, client, method):
        """
        @param client: A suds client.
        @type client: L{Client}
        @param method: A target method.
        @type method: L{Method}
        """
        self.client = client
        self.method = method
        self.options = client.options
        self.cookiejar = CookieJar()

    def invoke(self, args, kwargs):
        """
        Send the required soap message to invoke the specified method
        @param args: A list of args for the method invoked.
        @type args: list
        @param kwargs: Named (keyword) args for the method invoked.
        @type kwargs: dict
        @return: The result of the method invocation.
        @rtype: I{builtin}|I{subclass of} L{Object}
        """
        timer = metrics.Timer()
        timer.start()
        result = None
        binding = self.method.binding.input
        soapenv = binding.get_message(self.method, args, kwargs)
        timer.stop()
        #metrics.log.debug(
        #        "message for '%s' created: %s",
        #        self.method.name,
        #        timer)
        timer.start()
        result = self.send(soapenv)
        timer.stop()
        #metrics.log.debug(
        #        "method '%s' invoked: %s",
        #        self.method.name,
        #        timer)
        return result

    def send(self, soapenv):
        """
        Send soap message.
        @param soapenv: A soap envelope to send.
        @type soapenv: L{Document}
        @return: The reply to the sent message.
        @rtype: I{builtin} or I{subclass of} L{Object}
        """
        result = None
        location = self.location()
        binding = self.method.binding.input
        transport = self.options.transport
        retxml = self.options.retxml
        prettyxml = self.options.prettyxml
        #log.debug('sending to (%s)\nmessage:\n%s', location, soapenv)
        try:
            self.last_sent(soapenv)
            plugins = PluginContainer(self.options.plugins)
            plugins.message.marshalled(envelope=soapenv.root())
            if prettyxml:
                soapenv = soapenv.str()
            else:
                soapenv = soapenv.plain()
            soapenv = soapenv.encode('utf-8')
            plugins.message.sending(envelope=soapenv)
            request = Request(location, soapenv)
            request.headers = self.headers()
            reply = transport.send(request)
            ctx = plugins.message.received(reply=reply.message)
            reply.message = ctx.reply
            if retxml:
                result = reply.message
            else:
                result = self.succeeded(binding, reply.message)
        except TransportError, e:
            if e.httpcode in (202,204):
                result = None
            else:
                log.error(self.last_sent())
                result = self.failed(binding, e)
        return result

    def headers(self):
        """
        Get http headers or the http/https request.
        @return: A dictionary of header/values.
        @rtype: dict
        """
        action = self.method.soap.action
        stock = { 'Content-Type' : 'text/xml; charset=utf-8', 'SOAPAction': action }
        result = dict(stock, **self.options.headers)
        #log.debug('headers = %s', result)
        return result

    def succeeded(self, binding, reply):
        """
        Request succeeded, process the reply
        @param binding: The binding to be used to process the reply.
        @type binding: L{bindings.binding.Binding}
        @param reply: The raw reply text.
        @type reply: str
        @return: The method result.
        @rtype: I{builtin}, L{Object}
        @raise WebFault: On server.
        """
        #log.debug('http succeeded:\n%s', reply)
        plugins = PluginContainer(self.options.plugins)
        if len(reply) > 0:
            reply, result = binding.get_reply(self.method, reply)
            self.last_received(reply)
        else:
            result = None
        ctx = plugins.message.unmarshalled(reply=result)
        result = ctx.reply
        if self.options.faults:
            return result
        else:
            return (200, result)

    def failed(self, binding, error):
        """
        Request failed, process reply based on reason
        @param binding: The binding to be used to process the reply.
        @type binding: L{suds.bindings.binding.Binding}
        @param error: The http error message
        @type error: L{transport.TransportError}
        """
        status, reason = (error.httpcode, tostr(error))
        reply = error.fp.read()
        #log.debug('http failed:\n%s', reply)
        if status == 500:
            if len(reply) > 0:
                r, p = binding.get_fault(reply)
                self.last_received(r)
                return (status, p)
            else:
                return (status, None)
        if self.options.faults:
            raise Exception((status, reason))
        else:
            return (status, None)

    def location(self):
        p = Unskin(self.options)
        return p.get('location', self.method.location)

    def last_sent(self, d=None):
        key = 'tx'
        messages = self.client.messages
        if d is None:
            return messages.get(key)
        else:
            messages[key] = d

    def last_received(self, d=None):
        key = 'rx'
        messages = self.client.messages
        if d is None:
            return messages.get(key)
        else:
            messages[key] = d


class SimClient(SoapClient):
    """
    Loopback client used for message/reply simulation.
    """

    injkey = '__inject'

    @classmethod
    def simulation(cls, kwargs):
        """ get whether loopback has been specified in the I{kwargs}. """
        return kwargs.has_key(SimClient.injkey)

    def invoke(self, args, kwargs):
        """
        Send the required soap message to invoke the specified method
        @param args: A list of args for the method invoked.
        @type args: list
        @param kwargs: Named (keyword) args for the method invoked.
        @type kwargs: dict
        @return: The result of the method invocation.
        @rtype: I{builtin} or I{subclass of} L{Object}
        """
        simulation = kwargs[self.injkey]
        msg = simulation.get('msg')
        reply = simulation.get('reply')
        fault = simulation.get('fault')
        if msg is None:
            if reply is not None:
                return self.__reply(reply, args, kwargs)
            if fault is not None:
                return self.__fault(fault)
            raise Exception('(reply|fault) expected when msg=None')
        sax = Parser()
        msg = sax.parse(string=msg)
        return self.send(msg)

    def __reply(self, reply, args, kwargs):
        """ simulate the reply """
        binding = self.method.binding.input
        msg = binding.get_message(self.method, args, kwargs)
        #log.debug('inject (simulated) send message:\n%s', msg)
        binding = self.method.binding.output
        return self.succeeded(binding, reply)

    def __fault(self, reply):
        """ simulate the (fault) reply """
        binding = self.method.binding.output
        if self.options.faults:
            r, p = binding.get_fault(reply)
            self.last_received(r)
            return (500, p)
        else:
            return (500, None)

########NEW FILE########
__FILENAME__ = metrics
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The I{metrics} module defines classes and other resources
designed for collecting and reporting performance metrics.
"""

import time
from logging import getLogger
from suds import *
from math import modf

log = getLogger(__name__)

class Timer:

    def __init__(self):
        self.started = 0
        self.stopped = 0

    def start(self):
        self.started = time.time()
        self.stopped = 0
        return self

    def stop(self):
        if self.started > 0:
            self.stopped = time.time()
        return self

    def duration(self):
        return ( self.stopped - self.started )

    def __str__(self):
        if self.started == 0:
            return 'not-running'
        if self.started > 0 and self.stopped == 0:
            return 'started: %d (running)' % self.started
        duration = self.duration()
        jmod = ( lambda m : (m[1], m[0]*1000) )
        if duration < 1:
            ms = (duration*1000)
            return '%d (ms)' % ms           
        if duration < 60:
            m = modf(duration)
            return '%d.%.3d (seconds)' % jmod(m)
        m = modf(duration/60)
        return '%d.%.3d (minutes)' % jmod(m)

########NEW FILE########
__FILENAME__ = appender
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides appender classes for I{marshalling}.
"""

from logging import getLogger
from suds import *
from suds.mx import *
from suds.sudsobject import footprint
from suds.sudsobject import Object, Property
from suds.sax.element import Element
from suds.sax.text import Text
from copy import deepcopy

log = getLogger(__name__)

class Matcher:
    """
    Appender matcher.
    @ivar cls: A class object.
    @type cls: I{classobj}
    """

    def __init__(self, cls):
        """
        @param cls: A class object.
        @type cls: I{classobj}
        """
        self.cls = cls

    def __eq__(self, x):
        if self.cls is None:
            return ( x is None )
        else:
            return isinstance(x, self.cls)


class ContentAppender:
    """
    Appender used to add content to marshalled objects.
    @ivar default: The default appender.
    @type default: L{Appender}
    @ivar appenders: A I{table} of appenders mapped by class.
    @type appenders: I{table}
    """

    def __init__(self, marshaller):
        """
        @param marshaller: A marshaller.
        @type marshaller: L{suds.mx.core.Core}
        """
        self.default = PrimativeAppender(marshaller)
        self.appenders = (
            (Matcher(None),
                NoneAppender(marshaller)),
            (Matcher(null),
                NoneAppender(marshaller)),
            (Matcher(Property),
                PropertyAppender(marshaller)),
            (Matcher(Object),
                ObjectAppender(marshaller)),
            (Matcher(Element), 
                ElementAppender(marshaller)),
            (Matcher(Text), 
                TextAppender(marshaller)),
            (Matcher(list), 
                ListAppender(marshaller)),
            (Matcher(tuple), 
                ListAppender(marshaller)),
            (Matcher(dict), 
                DictAppender(marshaller)),
        )
        
    def append(self, parent, content):
        """
        Select an appender and append the content to parent.
        @param parent: A parent node.
        @type parent: L{Element}
        @param content: The content to append.
        @type content: L{Content}
        """
        appender = self.default
        for a in self.appenders:
            if a[0] == content.value:
                appender = a[1]
                break
        appender.append(parent, content)


class Appender:
    """
    An appender used by the marshaller to append content.
    @ivar marshaller: A marshaller.
    @type marshaller: L{suds.mx.core.Core}
    """
    
    def __init__(self, marshaller):
        """
        @param marshaller: A marshaller.
        @type marshaller: L{suds.mx.core.Core}
        """
        self.marshaller  = marshaller
        
    def node(self, content):
        """
        Create and return an XML node that is qualified
        using the I{type}.  Also, make sure all referenced namespace
        prefixes are declared.
        @param content: The content for which proccessing has ended.
        @type content: L{Object}
        @return: A new node.
        @rtype: L{Element}
        """
        return self.marshaller.node(content)
    
    def setnil(self, node, content):
        """
        Set the value of the I{node} to nill.
        @param node: A I{nil} node.
        @type node: L{Element}
        @param content: The content for which proccessing has ended.
        @type content: L{Object}
        """
        self.marshaller.setnil(node, content)
        
    def setdefault(self, node, content):
        """
        Set the value of the I{node} to a default value.
        @param node: A I{nil} node.
        @type node: L{Element}
        @param content: The content for which proccessing has ended.
        @type content: L{Object}
        @return: The default.
        """
        return self.marshaller.setdefault(node, content)
    
    def optional(self, content):
        """
        Get whether the specified content is optional.
        @param content: The content which to check.
        @type content: L{Content}
        """
        return self.marshaller.optional(content)
        
    def suspend(self, content):
        """
        Notify I{marshaller} that appending this content has suspended.
        @param content: The content for which proccessing has been suspended.
        @type content: L{Object}
        """
        self.marshaller.suspend(content)
        
    def resume(self, content):
        """
        Notify I{marshaller} that appending this content has resumed.
        @param content: The content for which proccessing has been resumed.
        @type content: L{Object}
        """
        self.marshaller.resume(content)
    
    def append(self, parent, content):
        """
        Append the specified L{content} to the I{parent}.
        @param content: The content to append.
        @type content: L{Object}
        """
        self.marshaller.append(parent, content)

       
class PrimativeAppender(Appender):
    """
    An appender for python I{primative} types.
    """
        
    def append(self, parent, content):
        if content.tag.startswith('_'):
            attr = content.tag[1:]
            value = tostr(content.value)
            if value:
                parent.set(attr, value)
        else:
            child = self.node(content)
            child.setText(tostr(content.value))
            parent.append(child)


class NoneAppender(Appender):
    """
    An appender for I{None} values.
    """
        
    def append(self, parent, content):
        child = self.node(content)
        default = self.setdefault(child, content)
        if default is None:
            self.setnil(child, content)
        parent.append(child)


class PropertyAppender(Appender):
    """
    A L{Property} appender.
    """
        
    def append(self, parent, content):
        p = content.value
        child = self.node(content)
        child.setText(p.get())
        parent.append(child)
        for item in p.items():
            cont = Content(tag=item[0], value=item[1])
            Appender.append(self, child, cont)

            
class ObjectAppender(Appender):
    """
    An L{Object} appender.
    """
        
    def append(self, parent, content):
        object = content.value
        if self.optional(content) and footprint(object) == 0:
            return
        child = self.node(content)
        parent.append(child)
        for item in object:
            cont = Content(tag=item[0], value=item[1])
            Appender.append(self, child, cont)
            

class DictAppender(Appender):
    """
    An python I{dict} appender.
    """
        
    def append(self, parent, content):
        d = content.value
        if self.optional(content) and len(d) == 0:
            return
        child = self.node(content)
        parent.append(child)
        for item in d.items():
            cont = Content(tag=item[0], value=item[1])
            Appender.append(self, child, cont)
            

class ElementWrapper(Element):
    """
    Element wrapper.
    """
    
    def __init__(self, content):
        Element.__init__(self, content.name, content.parent)
        self.__content = content
        
    def str(self, indent=0):
        return self.__content.str(indent)


class ElementAppender(Appender):
    """
    An appender for I{Element} types.
    """

    def append(self, parent, content):
        if content.tag.startswith('_'):
            raise Exception('raw XML not valid as attribute value')
        child = ElementWrapper(content.value)
        parent.append(child)


class ListAppender(Appender):
    """
    A list/tuple appender.
    """

    def append(self, parent, content):
        collection = content.value
        if len(collection):
            self.suspend(content)
            for item in collection:
                cont = Content(tag=content.tag, value=item)
                Appender.append(self, parent, cont)
            self.resume(content)


class TextAppender(Appender):
    """
    An appender for I{Text} values.
    """

    def append(self, parent, content):
        if content.tag.startswith('_'):
            attr = content.tag[1:]
            value = tostr(content.value)
            if value:
                parent.set(attr, value)
        else:
            child = self.node(content)
            child.setText(content.value)
            parent.append(child)

########NEW FILE########
__FILENAME__ = basic
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides basic I{marshaller} classes.
"""

from logging import getLogger
from suds import *
from suds.mx import *
from suds.mx.core import Core

log = getLogger(__name__)


class Basic(Core):
    """
    A I{basic} (untyped) marshaller.
    """
    
    def process(self, value, tag=None):
        """
        Process (marshal) the tag with the specified value using the
        optional type information.
        @param value: The value (content) of the XML node.
        @type value: (L{Object}|any)
        @param tag: The (optional) tag name for the value.  The default is
            value.__class__.__name__
        @type tag: str
        @return: An xml node.
        @rtype: L{Element}
        """
        content = Content(tag=tag, value=value)
        result = Core.process(self, content)
        return result
########NEW FILE########
__FILENAME__ = core
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides I{marshaller} core classes.
"""

from logging import getLogger
from suds import *
from suds.mx import *
from suds.mx.appender import ContentAppender
from suds.sax.element import Element
from suds.sax.document import Document
from suds.sudsobject import Property


log = getLogger(__name__)


class Core:
    """
    An I{abstract} marshaller.  This class implement the core
    functionality of the marshaller.
    @ivar appender: A content appender.
    @type appender: L{ContentAppender}
    """

    def __init__(self):
        """
        """
        self.appender = ContentAppender(self)

    def process(self, content):
        """
        Process (marshal) the tag with the specified value using the
        optional type information.
        @param content: The content to process.
        @type content: L{Object}
        """
        #log.debug('processing:\n%s', content)
        self.reset()
        if content.tag is None:
            content.tag = content.value.__class__.__name__
        document = Document()
        if isinstance(content.value, Property):
            root = self.node(content)
            self.append(document, content)
        else:
            self.append(document, content)
        return document.root()

    def append(self, parent, content):
        """
        Append the specified L{content} to the I{parent}.
        @param parent: The parent node to append to.
        @type parent: L{Element}
        @param content: The content to append.
        @type content: L{Object}
        """
        #log.debug('appending parent:\n%s\ncontent:\n%s', parent, content)
        if self.start(content):
            self.appender.append(parent, content)
            self.end(parent, content)

    def reset(self):
        """
        Reset the marshaller.
        """
        pass

    def node(self, content):
        """
        Create and return an XML node.
        @param content: The content for which proccessing has been suspended.
        @type content: L{Object}
        @return: An element.
        @rtype: L{Element}
        """
        return Element(content.tag)

    def start(self, content):
        """
        Appending this content has started.
        @param content: The content for which proccessing has started.
        @type content: L{Content}
        @return: True to continue appending
        @rtype: boolean
        """
        return True

    def suspend(self, content):
        """
        Appending this content has suspended.
        @param content: The content for which proccessing has been suspended.
        @type content: L{Content}
        """
        pass

    def resume(self, content):
        """
        Appending this content has resumed.
        @param content: The content for which proccessing has been resumed.
        @type content: L{Content}
        """
        pass

    def end(self, parent, content):
        """
        Appending this content has ended.
        @param parent: The parent node ending.
        @type parent: L{Element}
        @param content: The content for which proccessing has ended.
        @type content: L{Content}
        """
        pass

    def setnil(self, node, content):
        """
        Set the value of the I{node} to nill.
        @param node: A I{nil} node.
        @type node: L{Element}
        @param content: The content to set nil.
        @type content: L{Content}
        """
        pass

    def setdefault(self, node, content):
        """
        Set the value of the I{node} to a default value.
        @param node: A I{nil} node.
        @type node: L{Element}
        @param content: The content to set the default value.
        @type content: L{Content}
        @return: The default.
        """
        pass

    def optional(self, content):
        """
        Get whether the specified content is optional.
        @param content: The content which to check.
        @type content: L{Content}
        """
        return False

########NEW FILE########
__FILENAME__ = encoded
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides encoded I{marshaller} classes.
"""

from logging import getLogger
from suds import *
from suds.mx import *
from suds.mx.literal import Literal
from suds.mx.typer import Typer
from suds.sudsobject import Factory, Object
from suds.xsd.query import TypeQuery

log = getLogger(__name__)

#
# Add encoded extensions
# aty = The soap (section 5) encoded array type.
#
Content.extensions.append('aty')


class Encoded(Literal):
    """
    A SOAP section (5) encoding marshaller.
    This marshaller supports rpc/encoded soap styles.
    """
    
    def start(self, content):
        #
        # For soap encoded arrays, the 'aty' (array type) information
        # is extracted and added to the 'content'.  Then, the content.value
        # is replaced with an object containing an 'item=[]' attribute
        # containing values that are 'typed' suds objects. 
        #
        start = Literal.start(self, content)
        if start and isinstance(content.value, (list,tuple)):
            resolved = content.type.resolve()
            for c in resolved:
                if hasattr(c[0], 'aty'):
                    content.aty = (content.tag, c[0].aty)
                    self.cast(content)
                    break
        return start
    
    def end(self, parent, content):
        #
        # For soap encoded arrays, the soapenc:arrayType attribute is
        # added with proper type and size information.
        # Eg: soapenc:arrayType="xs:int[3]"
        #
        Literal.end(self, parent, content)
        if content.aty is None:
            return
        tag, aty = content.aty
        ns0 = ('at0', aty[1])
        ns1 = ('at1', 'http://schemas.xmlsoap.org/soap/encoding/')
        array = content.value.item
        child = parent.getChild(tag)
        child.addPrefix(ns0[0], ns0[1])
        child.addPrefix(ns1[0], ns1[1])
        name = '%s:arrayType' % ns1[0]
        value = '%s:%s[%d]' % (ns0[0], aty[0], len(array)) 
        child.set(name, value)
        
    def encode(self, node, content):
        if content.type.any():
            Typer.auto(node, content.value)
            return
        if content.real.any():
            Typer.auto(node, content.value)
            return
        ns = None
        name = content.real.name
        if self.xstq:
            ns = content.real.namespace()
        Typer.manual(node, name, ns)
        
    def cast(self, content):
        """
        Cast the I{untyped} list items found in content I{value}.
        Each items contained in the list is checked for XSD type information.
        Items (values) that are I{untyped}, are replaced with suds objects and
        type I{metadata} is added.
        @param content: The content holding the collection.
        @type content: L{Content}
        @return: self
        @rtype: L{Encoded}
        """
        aty = content.aty[1]
        resolved = content.type.resolve()
        array = Factory.object(resolved.name)
        array.item = []
        query = TypeQuery(aty)
        ref = query.execute(self.schema)
        if ref is None:
            raise TypeNotFound(qref)
        for x in content.value:
            if isinstance(x, (list, tuple)):
                array.item.append(x)
                continue
            if isinstance(x, Object):
                md = x.__metadata__
                md.sxtype = ref
                array.item.append(x) 
                continue
            if isinstance(x, dict):
                x = Factory.object(ref.name, x)
                md = x.__metadata__
                md.sxtype = ref
                array.item.append(x) 
                continue
            x = Factory.property(ref.name, x)
            md = x.__metadata__
            md.sxtype = ref
            array.item.append(x)
        content.value = array
        return self

########NEW FILE########
__FILENAME__ = literal
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides literal I{marshaller} classes.
"""

from logging import getLogger
from suds import *
from suds.mx import *
from suds.mx.core import Core
from suds.mx.typer import Typer
from suds.resolver import GraphResolver, Frame
from suds.sax.element import Element
from suds.sudsobject import Factory

log = getLogger(__name__)


#
# Add typed extensions
# type = The expected xsd type
# real = The 'true' XSD type
# ancestry = The 'type' ancestry
#
Content.extensions.append('type')
Content.extensions.append('real')
Content.extensions.append('ancestry')



class Typed(Core):
    """
    A I{typed} marshaller.
    This marshaller is semi-typed as needed to support both
    I{document/literal} and I{rpc/literal} soap message styles.
    @ivar schema: An xsd schema.
    @type schema: L{xsd.schema.Schema}
    @ivar resolver: A schema type resolver.
    @type resolver: L{GraphResolver}
    """

    def __init__(self, schema, xstq=True):
        """
        @param schema: A schema object
        @type schema: L{xsd.schema.Schema}
        @param xstq: The B{x}ml B{s}chema B{t}ype B{q}ualified flag indicates
            that the I{xsi:type} attribute values should be qualified by namespace.
        @type xstq: bool
        """
        Core.__init__(self)
        self.schema = schema
        self.xstq = xstq
        self.resolver = GraphResolver(self.schema)

    def reset(self):
        self.resolver.reset()

    def start(self, content):
        #
        # Start marshalling the 'content' by ensuring that both the
        # 'content' _and_ the resolver are primed with the XSD type
        # information.  The 'content' value is both translated and
        # sorted based on the XSD type.  Only values that are objects
        # have their attributes sorted.
        #
        #log.debug('starting content:\n%s', content)
        if content.type is None:
            name = content.tag
            if name.startswith('_'):
                name = '@'+name[1:]
            content.type = self.resolver.find(name, content.value)
            if content.type is None:
                raise TypeNotFound(content.tag)
        else:
            known = None
            if isinstance(content.value, Object):
                known = self.resolver.known(content.value)
                if known is None:
                    #log.debug('object has no type information', content.value)
                    known = content.type
            frame = Frame(content.type, resolved=known)
            self.resolver.push(frame)
        frame = self.resolver.top()
        content.real = frame.resolved
        content.ancestry = frame.ancestry
        self.translate(content)
        self.sort(content)
        if self.skip(content):
            #log.debug('skipping (optional) content:\n%s', content)
            self.resolver.pop()
            return False
        else:
            return True

    def suspend(self, content):
        #
        # Suspend to process a list content.  Primarily, this
        # involves popping the 'list' content off the resolver's
        # stack so the list items can be marshalled.
        #
        self.resolver.pop()

    def resume(self, content):
        #
        # Resume processing a list content.  To do this, we
        # really need to simply push the 'list' content
        # back onto the resolver stack.
        #
        self.resolver.push(Frame(content.type))

    def end(self, parent, content):
        #
        # End processing the content.  Make sure the content
        # ending matches the top of the resolver stack since for
        # list processing we play games with the resolver stack.
        #
        #log.debug('ending content:\n%s', content)
        current = self.resolver.top().type
        if current == content.type:
            self.resolver.pop()
        else:
            raise Exception, \
                'content (end) mismatch: top=(%s) cont=(%s)' % \
                (current, content)

    def node(self, content):
        #
        # Create an XML node and namespace qualify as defined
        # by the schema (elementFormDefault).
        #
        ns = content.type.namespace()
        if content.type.form_qualified:
            node = Element(content.tag, ns=ns)
            node.addPrefix(ns[0], ns[1])
        else:
            node = Element(content.tag)
        self.encode(node, content)
        #log.debug('created - node:\n%s', node)
        return node

    def setnil(self, node, content):
        #
        # Set the 'node' nil only if the XSD type
        # specifies that it is permitted.
        #
        if content.type.nillable:
            node.setnil()

    def setdefault(self, node, content):
        #
        # Set the node to the default value specified
        # by the XSD type.
        #
        default = content.type.default
        if default is None:
            pass
        else:
            node.setText(default)
        return default

    def optional(self, content):
        if content.type.optional():
            return True
        for a in content.ancestry:
            if a.optional():
                return True
        return False

    def encode(self, node, content):
        # Add (soap) encoding information only if the resolved
        # type is derived by extension.  Further, the xsi:type values
        # is qualified by namespace only if the content (tag) and
        # referenced type are in different namespaces.
        if content.type.any():
            return
        if not content.real.extension():
            return
        if content.type.resolve() == content.real:
            return
        ns = None
        name = content.real.name
        if self.xstq:
            ns = content.real.namespace('ns1')
        Typer.manual(node, name, ns)

    def skip(self, content):
        """
        Get whether to skip this I{content}.
        Should be skipped when the content is optional
        and either the value=None or the value is an empty list.
        @param content: The content to skip.
        @type content: L{Object}
        @return: True if content is to be skipped.
        @rtype: bool
        """
        if self.optional(content):
            v = content.value
            if v is None:
                return True
            if isinstance(v, (list,tuple)) and len(v) == 0:
                return True
        return False

    def optional(self, content):
        if content.type.optional():
            return True
        for a in content.ancestry:
            if a.optional():
                return True
        return False

    def translate(self, content):
        """
        Translate using the XSD type information.
        Python I{dict} is translated to a suds object.  Most
        importantly, primative values are translated from python
        types to XML types using the XSD type.
        @param content: The content to translate.
        @type content: L{Object}
        @return: self
        @rtype: L{Typed}
        """
        v = content.value
        if v is None:
            return
        if isinstance(v, dict):
            cls = content.real.name
            content.value = Factory.object(cls, v)
            md = content.value.__metadata__
            md.sxtype = content.type
            return
        v = content.real.translate(v, False)
        content.value = v
        return self

    def sort(self, content):
        """
        Sort suds object attributes based on ordering defined
        in the XSD type information.
        @param content: The content to sort.
        @type content: L{Object}
        @return: self
        @rtype: L{Typed}
        """
        v = content.value
        if isinstance(v, Object):
            md = v.__metadata__
            md.ordering = self.ordering(content.real)
        return self

    def ordering(self, type):
        """
        Get the attribute ordering defined in the specified
        XSD type information.
        @param type: An XSD type object.
        @type type: SchemaObject
        @return: An ordered list of attribute names.
        @rtype: list
        """
        result = []
        for child, ancestry in type.resolve():
            name = child.name
            if child.name is None:
                continue
            if child.isattr():
                name = '_%s' % child.name
            result.append(name)
        return result


class Literal(Typed):
    """
    A I{literal} marshaller.
    This marshaller is semi-typed as needed to support both
    I{document/literal} and I{rpc/literal} soap message styles.
    """
    pass

########NEW FILE########
__FILENAME__ = typer
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides sx typing classes.
"""

from logging import getLogger
from suds import *
from suds.mx import *
from suds.sax import Namespace as NS
from suds.sax.text import Text

log = getLogger(__name__)


class Typer:
    """
    Provides XML node typing as either automatic or manual.
    @cvar types:  A dict of class to xs type mapping.
    @type types: dict
    """

    types = {
        int : ('int', NS.xsdns),
        long : ('long', NS.xsdns),
        float : ('float', NS.xsdns),
        str : ('string', NS.xsdns),
        unicode : ('string', NS.xsdns),
        Text : ('string', NS.xsdns),
        bool : ('boolean', NS.xsdns),
     }
                
    @classmethod
    def auto(cls, node, value=None):
        """
        Automatically set the node's xsi:type attribute based on either I{value}'s
        class or the class of the node's text.  When I{value} is an unmapped class,
        the default type (xs:any) is set.
        @param node: An XML node
        @type node: L{sax.element.Element}
        @param value: An object that is or would be the node's text.
        @type value: I{any}
        @return: The specified node.
        @rtype: L{sax.element.Element}
        """
        if value is None:
            value = node.getText()
        if isinstance(value, Object):
            known = cls.known(value)
            if known.name is None:
                return node
            tm = (known.name, known.namespace())
        else:
            tm = cls.types.get(value.__class__, cls.types.get(str))
        cls.manual(node, *tm)
        return node

    @classmethod
    def manual(cls, node, tval, ns=None):
        """
        Set the node's xsi:type attribute based on either I{value}'s
        class or the class of the node's text.  Then adds the referenced
        prefix(s) to the node's prefix mapping.
        @param node: An XML node
        @type node: L{sax.element.Element}
        @param tval: The name of the schema type.
        @type tval: str
        @param ns: The XML namespace of I{tval}.
        @type ns: (prefix, uri)
        @return: The specified node.
        @rtype: L{sax.element.Element}
        """
        xta = ':'.join((NS.xsins[0], 'type'))
        node.addPrefix(NS.xsins[0], NS.xsins[1])
        if ns is None:
            node.set(xta, tval)
        else:
            ns = cls.genprefix(node, ns)
            qname = ':'.join((ns[0], tval))
            node.set(xta, qname)
            node.addPrefix(ns[0], ns[1]) 
        return node
    
    @classmethod
    def genprefix(cls, node, ns):
        """
        Generate a prefix.
        @param node: An XML node on which the prefix will be used.
        @type node: L{sax.element.Element}
        @param ns: A namespace needing an unique prefix.
        @type ns: (prefix, uri)
        @return: The I{ns} with a new prefix.
        """
        for n in range(1, 1024):
            p = 'ns%d' % n
            u = node.resolvePrefix(p, default=None)
            if u is None or u == ns[1]:
                return (p, ns[1])
        raise Exception('auto prefix, exhausted')
    
    @classmethod
    def known(cls, object):
        try:
            md = object.__metadata__
            known = md.sxtype
            return known
        except:
            pass


########NEW FILE########
__FILENAME__ = options
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Suds basic options classes.
"""

from suds.properties import *
from suds.wsse import Security
from suds.xsd.doctor import Doctor
from suds.transport import Transport
from suds.cache import Cache, NoCache


class TpLinker(AutoLinker):
    """
    Transport (auto) linker used to manage linkage between
    transport objects Properties and those Properties that contain them.
    """
    
    def updated(self, properties, prev, next):
        if isinstance(prev, Transport):
            tp = Unskin(prev.options)
            properties.unlink(tp)
        if isinstance(next, Transport):
            tp = Unskin(next.options)
            properties.link(tp)


class Options(Skin):
    """
    Options:
        - B{cache} - The XML document cache.  May be set (None) for no caching.
                - type: L{Cache}
                - default: L{NoCache}
        - B{faults} - Raise faults raised by server,
            else return tuple from service method invocation as (httpcode, object).
                - type: I{bool}
                - default: True
        - B{service} - The default service name.
                - type: I{str}
                - default: None
        - B{port} - The default service port name, not tcp port.
                - type: I{str}
                - default: None
        - B{location} - This overrides the service port address I{URL} defined 
            in the WSDL.
                - type: I{str}
                - default: None
        - B{transport} - The message transport.
                - type: L{Transport}
                - default: None
        - B{soapheaders} - The soap headers to be included in the soap message.
                - type: I{any}
                - default: None
        - B{wsse} - The web services I{security} provider object.
                - type: L{Security}
                - default: None
        - B{doctor} - A schema I{doctor} object.
                - type: L{Doctor}
                - default: None
        - B{xstq} - The B{x}ml B{s}chema B{t}ype B{q}ualified flag indicates
            that the I{xsi:type} attribute values should be qualified by namespace.
                - type: I{bool}
                - default: True
        - B{prefixes} - Elements of the soap message should be qualified (when needed)
            using XML prefixes as opposed to xmlns="" syntax.
                - type: I{bool}
                - default: True
        - B{retxml} - Flag that causes the I{raw} soap envelope to be returned instead
            of the python object graph.
                - type: I{bool}
                - default: False
        - B{prettyxml} - Flag that causes I{pretty} xml to be rendered when generating
            the outbound soap envelope.
                - type: I{bool}
                - default: False
        - B{autoblend} - Flag that ensures that the schema(s) defined within the
            WSDL import each other.
                - type: I{bool}
                - default: False
        - B{cachingpolicy} - The caching policy.
                - type: I{int}
                  - 0 = Cache XML documents.
                  - 1 = Cache WSDL (pickled) object.
                - default: 0
        - B{plugins} - A plugin container.
                - type: I{list}
    """    
    def __init__(self, **kwargs):
        domain = __name__
        definitions = [
            Definition('cache', Cache, NoCache()),
            Definition('faults', bool, True),
            Definition('transport', Transport, None, TpLinker()),
            Definition('service', (int, basestring), None),
            Definition('port', (int, basestring), None),
            Definition('location', basestring, None),
            Definition('soapheaders', (), ()),
            Definition('wsse', Security, None),
            Definition('doctor', Doctor, None),
            Definition('xstq', bool, True),
            Definition('prefixes', bool, True),
            Definition('retxml', bool, False),
            Definition('prettyxml', bool, False),
            Definition('autoblend', bool, False),
            Definition('cachingpolicy', int, 0),
            Definition('plugins', (list, tuple), []),
        ]
        Skin.__init__(self, domain, definitions, kwargs)

########NEW FILE########
__FILENAME__ = plugin
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The plugin module provides classes for implementation
of suds plugins.
"""

from suds import *
from logging import getLogger

log = getLogger(__name__)


class Context(object):
    """
    Plugin context.
    """
    pass


class InitContext(Context):
    """
    Init Context.
    @ivar wsdl: The wsdl.
    @type wsdl: L{wsdl.Definitions}
    """
    pass


class DocumentContext(Context):
    """
    The XML document load context.
    @ivar url: The URL.
    @type url: str
    @ivar document: Either the XML text or the B{parsed} document root.
    @type document: (str|L{sax.element.Element})
    """
    pass

        
class MessageContext(Context):
    """
    The context for sending the soap envelope.
    @ivar envelope: The soap envelope to be sent.
    @type envelope: (str|L{sax.element.Element})
    @ivar reply: The reply.
    @type reply: (str|L{sax.element.Element}|object)
    """
    pass


class Plugin:
    """
    Plugin base.
    """
    pass


class InitPlugin(Plugin):
    """
    The base class for suds I{init} plugins.
    """
    
    def initialized(self, context):
        """
        Suds client initialization.
        Called after wsdl the has been loaded.  Provides the plugin
        with the opportunity to inspect/modify the WSDL.
        @param context: The init context.
        @type context: L{InitContext}
        """
        pass


class DocumentPlugin(Plugin):
    """
    The base class for suds I{document} plugins.
    """
    
    def loaded(self, context): 
        """
        Suds has loaded a WSDL/XSD document.  Provides the plugin 
        with an opportunity to inspect/modify the unparsed document. 
        Called after each WSDL/XSD document is loaded. 
        @param context: The document context. 
        @type context: L{DocumentContext} 
        """
        pass 
    
    def parsed(self, context):
        """
        Suds has parsed a WSDL/XSD document.  Provides the plugin
        with an opportunity to inspect/modify the parsed document.
        Called after each WSDL/XSD document is parsed.
        @param context: The document context.
        @type context: L{DocumentContext}
        """
        pass


class MessagePlugin(Plugin):
    """
    The base class for suds I{soap message} plugins.
    """
    
    def marshalled(self, context):
        """
        Suds will send the specified soap envelope.
        Provides the plugin with the opportunity to inspect/modify
        the envelope Document before it is sent.
        @param context: The send context.
            The I{envelope} is the envelope docuemnt.
        @type context: L{MessageContext}
        """
        pass
    
    def sending(self, context):
        """
        Suds will send the specified soap envelope.
        Provides the plugin with the opportunity to inspect/modify
        the message text it is sent.
        @param context: The send context.
            The I{envelope} is the envelope text.
        @type context: L{MessageContext}
        """
        pass
    
    def received(self, context):
        """
        Suds has received the specified reply.
        Provides the plugin with the opportunity to inspect/modify
        the received XML text before it is SAX parsed.
        @param context: The reply context.
            The I{reply} is the raw text.
        @type context: L{MessageContext}
        """
        pass
    
    def parsed(self, context):
        """
        Suds has sax parsed the received reply.
        Provides the plugin with the opportunity to inspect/modify
        the sax parsed DOM tree for the reply before it is unmarshalled.
        @param context: The reply context.
            The I{reply} is DOM tree.
        @type context: L{MessageContext}
        """
        pass
    
    def unmarshalled(self, context):
        """
        Suds has unmarshalled the received reply.
        Provides the plugin with the opportunity to inspect/modify
        the unmarshalled reply object before it is returned.
        @param context: The reply context.
            The I{reply} is unmarshalled suds object.
        @type context: L{MessageContext}
        """
        pass

    
class PluginContainer:
    """
    Plugin container provides easy method invocation.
    @ivar plugins: A list of plugin objects.
    @type plugins: [L{Plugin},]
    @cvar ctxclass: A dict of plugin method / context classes.
    @type ctxclass: dict
    """
    
    domains = {\
        'init': (InitContext, InitPlugin),
        'document': (DocumentContext, DocumentPlugin),
        'message': (MessageContext, MessagePlugin ),
    }
    
    def __init__(self, plugins):
        """
        @param plugins: A list of plugin objects.
        @type plugins: [L{Plugin},]
        """
        self.plugins = plugins
    
    def __getattr__(self, name):
        domain = self.domains.get(name)
        if domain:
            plugins = []
            ctx, pclass = domain
            for p in self.plugins:
                if isinstance(p, pclass):
                    plugins.append(p)
            return PluginDomain(ctx, plugins)
        else:
            raise Exception, 'plugin domain (%s), invalid' % name
        
        
class PluginDomain:
    """
    The plugin domain.
    @ivar ctx: A context.
    @type ctx: L{Context}
    @ivar plugins: A list of plugins (targets).
    @type plugins: list
    """
    
    def __init__(self, ctx, plugins):
        self.ctx = ctx
        self.plugins = plugins
    
    def __getattr__(self, name):
        return Method(name, self)


class Method:
    """
    Plugin method.
    @ivar name: The method name.
    @type name: str
    @ivar domain: The plugin domain.
    @type domain: L{PluginDomain}
    """

    def __init__(self, name, domain):
        """
        @param name: The method name.
        @type name: str
        @param domain: A plugin domain.
        @type domain: L{PluginDomain}
        """
        self.name = name
        self.domain = domain
            
    def __call__(self, **kwargs):
        ctx = self.domain.ctx()
        ctx.__dict__.update(kwargs)
        for plugin in self.domain.plugins:
            try:
                method = getattr(plugin, self.name, None)
                if method and callable(method):
                    method(ctx)
            except Exception, pe:
                log.exception(pe)
        return ctx

########NEW FILE########
__FILENAME__ = properties
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Properties classes.
"""

from logging import getLogger

log = getLogger(__name__)


class AutoLinker(object):
    """
    Base class, provides interface for I{automatic} link
    management between a L{Properties} object and the L{Properties}
    contained within I{values}.
    """
    def updated(self, properties, prev, next):
        """
        Notification that a values was updated and the linkage
        between the I{properties} contained with I{prev} need to
        be relinked to the L{Properties} contained within the
        I{next} value.
        """
        pass


class Link(object):
    """
    Property link object.
    @ivar endpoints: A tuple of the (2) endpoints of the link.
    @type endpoints: tuple(2)
    """
    def __init__(self, a, b):
        """
        @param a: Property (A) to link.
        @type a: L{Property}
        @param b: Property (B) to link.
        @type b: L{Property}
        """
        pA = Endpoint(self, a)
        pB = Endpoint(self, b)
        self.endpoints = (pA, pB)
        self.validate(a, b)
        a.links.append(pB)
        b.links.append(pA)
            
    def validate(self, pA, pB):
        """
        Validate that the two properties may be linked.
        @param pA: Endpoint (A) to link.
        @type pA: L{Endpoint}
        @param pB: Endpoint (B) to link.
        @type pB: L{Endpoint}
        @return: self
        @rtype: L{Link}
        """
        if pA in pB.links or \
           pB in pA.links:
            raise Exception, 'Already linked'
        dA = pA.domains()
        dB = pB.domains()
        for d in dA:
            if d in dB:
                raise Exception, 'Duplicate domain "%s" found' % d
        for d in dB:
            if d in dA:
                raise Exception, 'Duplicate domain "%s" found' % d
        kA = pA.keys()
        kB = pB.keys()
        for k in kA:
            if k in kB:
                raise Exception, 'Duplicate key %s found' % k
        for k in kB:
            if k in kA:
                raise Exception, 'Duplicate key %s found' % k
        return self
            
    def teardown(self):
        """
        Teardown the link.
        Removes endpoints from properties I{links} collection.
        @return: self
        @rtype: L{Link}
        """
        pA, pB = self.endpoints
        if pA in pB.links:
            pB.links.remove(pA)
        if pB in pA.links:
            pA.links.remove(pB)
        return self


class Endpoint(object):
    """
    Link endpoint (wrapper).
    @ivar link: The associated link.
    @type link: L{Link}
    @ivar target: The properties object.
    @type target: L{Property}
    """
    def __init__(self, link, target):
        self.link = link
        self.target = target
        
    def teardown(self):
        return self.link.teardown()

    def __eq__(self, rhs):
        return ( self.target == rhs )

    def __hash__(self):
        return hash(self.target)

    def __getattr__(self, name):
        return getattr(self.target, name)


class Definition:
    """
    Property definition.
    @ivar name: The property name.
    @type name: str
    @ivar classes: The (class) list of permitted values
    @type classes: tuple
    @ivar default: The default value.
    @ivar type: any
    """
    def __init__(self, name, classes, default, linker=AutoLinker()):
        """
        @param name: The property name.
        @type name: str
        @param classes: The (class) list of permitted values
        @type classes: tuple
        @param default: The default value.
        @type default: any
        """
        if not isinstance(classes, (list, tuple)):
            classes = (classes,)
        self.name = name
        self.classes = classes
        self.default = default
        self.linker = linker
        
    def nvl(self, value=None):
        """
        Convert the I{value} into the default when I{None}.
        @param value: The proposed value.
        @type value: any
        @return: The I{default} when I{value} is I{None}, else I{value}.
        @rtype: any
        """
        if value is None:
            return self.default
        else:
            return value
        
    def validate(self, value):
        """
        Validate the I{value} is of the correct class.
        @param value: The value to validate.
        @type value: any
        @raise AttributeError: When I{value} is invalid.
        """
        if value is None:
            return
        if len(self.classes) and \
            not isinstance(value, self.classes):
                msg = '"%s" must be: %s' % (self.name, self.classes)
                raise AttributeError,msg
                    
            
    def __repr__(self):
        return '%s: %s' % (self.name, str(self))
            
    def __str__(self):
        s = []
        if len(self.classes):
            s.append('classes=%s' % str(self.classes))
        else:
            s.append('classes=*')
        s.append("default=%s" % str(self.default))
        return ', '.join(s)


class Properties:
    """
    Represents basic application properties.
    Provides basic type validation, default values and
    link/synchronization behavior.
    @ivar domain: The domain name.
    @type domain: str
    @ivar definitions: A table of property definitions.
    @type definitions: {name: L{Definition}}
    @ivar links: A list of linked property objects used to create
        a network of properties.
    @type links: [L{Property},..]
    @ivar defined: A dict of property values.
    @type defined: dict 
    """
    def __init__(self, domain, definitions, kwargs):
        """
        @param domain: The property domain name.
        @type domain: str
        @param definitions: A table of property definitions.
        @type definitions: {name: L{Definition}}
        @param kwargs: A list of property name/values to set.
        @type kwargs: dict  
        """
        self.definitions = {}
        for d in definitions:
            self.definitions[d.name] = d
        self.domain = domain
        self.links = []
        self.defined = {}
        self.modified = set()
        self.prime()
        self.update(kwargs)
        
    def definition(self, name):
        """
        Get the definition for the property I{name}.
        @param name: The property I{name} to find the definition for.
        @type name: str
        @return: The property definition
        @rtype: L{Definition}
        @raise AttributeError: On not found.
        """
        d = self.definitions.get(name)
        if d is None:
            raise AttributeError(name)
        return d
    
    def update(self, other):
        """
        Update the property values as specified by keyword/value.
        @param other: An object to update from.
        @type other: (dict|L{Properties})
        @return: self
        @rtype: L{Properties}
        """
        if isinstance(other, Properties):
            other = other.defined
        for n,v in other.items():
            self.set(n, v)
        return self
    
    def notset(self, name):
        """
        Get whether a property has never been set by I{name}.
        @param name: A property name.
        @type name: str
        @return: True if never been set.
        @rtype: bool
        """
        self.provider(name).__notset(name)
            
    def set(self, name, value):
        """
        Set the I{value} of a property by I{name}.
        The value is validated against the definition and set
        to the default when I{value} is None.
        @param name: The property name.
        @type name: str
        @param value: The new property value.
        @type value: any
        @return: self
        @rtype: L{Properties}
        """
        self.provider(name).__set(name, value)
        return self
    
    def unset(self, name):
        """
        Unset a property by I{name}.
        @param name: A property name.
        @type name: str
        @return: self
        @rtype: L{Properties}
        """
        self.provider(name).__set(name, None)
        return self
            
    def get(self, name, *df):
        """
        Get the value of a property by I{name}.
        @param name: The property name.
        @type name: str
        @param df: An optional value to be returned when the value
            is not set
        @type df: [1].
        @return: The stored value, or I{df[0]} if not set.
        @rtype: any 
        """
        return self.provider(name).__get(name, *df)
    
    def link(self, other):
        """
        Link (associate) this object with anI{other} properties object 
        to create a network of properties.  Links are bidirectional.
        @param other: The object to link.
        @type other: L{Properties}
        @return: self
        @rtype: L{Properties}
        """
        Link(self, other)
        return self

    def unlink(self, *others):
        """
        Unlink (disassociate) the specified properties object.
        @param others: The list object to unlink.  Unspecified means unlink all.
        @type others: [L{Properties},..]
        @return: self
        @rtype: L{Properties}
        """
        if not len(others):
            others = self.links[:]
        for p in self.links[:]:
            if p in others:
                p.teardown()
        return self
    
    def provider(self, name, history=None):
        """
        Find the provider of the property by I{name}.
        @param name: The property name.
        @type name: str
        @param history: A history of nodes checked to prevent
            circular hunting.
        @type history: [L{Properties},..]
        @return: The provider when found.  Otherwise, None (when nested)
            and I{self} when not nested.
        @rtype: L{Properties}
        """
        if history is None:
            history = []
        history.append(self)
        if name in self.definitions:
            return self
        for x in self.links:
            if x in history:
                continue
            provider = x.provider(name, history)
            if provider is not None:
                return provider
        history.remove(self)
        if len(history):
            return None
        return self
    
    def keys(self, history=None):
        """
        Get the set of I{all} property names.
        @param history: A history of nodes checked to prevent
            circular hunting.
        @type history: [L{Properties},..]
        @return: A set of property names.
        @rtype: list
        """
        if history is None:
            history = []
        history.append(self)
        keys = set()
        keys.update(self.definitions.keys())
        for x in self.links:
            if x in history:
                continue
            keys.update(x.keys(history))
        history.remove(self)
        return keys
    
    def domains(self, history=None):
        """
        Get the set of I{all} domain names.
        @param history: A history of nodes checked to prevent
            circular hunting.
        @type history: [L{Properties},..]
        @return: A set of domain names.
        @rtype: list
        """
        if history is None:
            history = []
        history.append(self)
        domains = set()
        domains.add(self.domain)
        for x in self.links:
            if x in history:
                continue
            domains.update(x.domains(history))
        history.remove(self)
        return domains
 
    def prime(self):
        """
        Prime the stored values based on default values
        found in property definitions.
        @return: self
        @rtype: L{Properties}
        """
        for d in self.definitions.values():
            self.defined[d.name] = d.default
        return self
    
    def __notset(self, name):
        return not (name in self.modified)
    
    def __set(self, name, value):
        d = self.definition(name)
        d.validate(value)
        value = d.nvl(value)
        prev = self.defined[name]
        self.defined[name] = value
        self.modified.add(name)
        d.linker.updated(self, prev, value)
        
    def __get(self, name, *df):
        d = self.definition(name)
        value = self.defined.get(name)
        if value == d.default and len(df):
            value = df[0]
        return value
            
    def str(self, history):
        s = []
        s.append('Definitions:')
        for d in self.definitions.values():
            s.append('\t%s' % repr(d))
        s.append('Content:')
        for d in self.defined.items():
            s.append('\t%s' % str(d))
        if self not in history:
            history.append(self)
            s.append('Linked:')
            for x in self.links:
                s.append(x.str(history))
            history.remove(self)
        return '\n'.join(s)
            
    def __repr__(self):
        return str(self)
            
    def __str__(self):
        return self.str([])


class Skin(object):
    """
    The meta-programming I{skin} around the L{Properties} object.
    @ivar __pts__: The wrapped object.
    @type __pts__: L{Properties}.
    """
    def __init__(self, domain, definitions, kwargs):
        self.__pts__ = Properties(domain, definitions, kwargs)
        
    def __setattr__(self, name, value):
        builtin = name.startswith('__') and name.endswith('__')
        if builtin:
            self.__dict__[name] = value
            return
        self.__pts__.set(name, value)
        
    def __getattr__(self, name):
        return self.__pts__.get(name)
    
    def __repr__(self):
        return str(self)
    
    def __str__(self):
        return str(self.__pts__)
    
    
class Unskin(object):
    def __new__(self, *args, **kwargs):
        return args[0].__pts__
    
    
class Inspector:
    """
    Wrapper inspector.
    """
    def __init__(self, options):
        self.properties = options.__pts__
        
    def get(self, name, *df):
        """
        Get the value of a property by I{name}.
        @param name: The property name.
        @type name: str
        @param df: An optional value to be returned when the value
            is not set
        @type df: [1].
        @return: The stored value, or I{df[0]} if not set.
        @rtype: any 
        """
        return self.properties.get(name, *df)

    def update(self, **kwargs):
        """
        Update the property values as specified by keyword/value.
        @param kwargs: A list of property name/values to set.
        @type kwargs: dict
        @return: self
        @rtype: L{Properties}
        """
        return self.properties.update(**kwargs)

    def link(self, other):
        """
        Link (associate) this object with anI{other} properties object 
        to create a network of properties.  Links are bidirectional.
        @param other: The object to link.
        @type other: L{Properties}
        @return: self
        @rtype: L{Properties}
        """
        p = other.__pts__
        return self.properties.link(p)
    
    def unlink(self, other):
        """
        Unlink (disassociate) the specified properties object.
        @param other: The object to unlink.
        @type other: L{Properties}
        @return: self
        @rtype: L{Properties}
        """
        p = other.__pts__
        return self.properties.unlink(p)

########NEW FILE########
__FILENAME__ = reader
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Contains xml document reader classes.
"""


from suds.sax.parser import Parser
from suds.transport import Request
from suds.cache import Cache, NoCache
from suds.store import DocumentStore
from suds.plugin import PluginContainer
from logging import getLogger


log = getLogger(__name__)


class Reader:
    """
    The reader provides integration with cache.
    @ivar options: An options object.
    @type options: I{Options}
    """

    def __init__(self, options):
        """
        @param options: An options object.
        @type options: I{Options}
        """
        self.options = options
        self.plugins = PluginContainer(options.plugins)

    def mangle(self, name, x):
        """
        Mangle the name by hashing the I{name} and appending I{x}.
        @return: the mangled name.
        """
        h = abs(hash(name))
        return '%s-%s' % (h, x)


class DocumentReader(Reader):
    """
    The XML document reader provides an integration
    between the SAX L{Parser} and the document cache.
    """
    
    def open(self, url):
        """
        Open an XML document at the specified I{url}.
        First, the document attempted to be retrieved from
        the I{object cache}.  If not found, it is downloaded and
        parsed using the SAX parser.  The result is added to the
        cache for the next open().
        @param url: A document url.
        @type url: str.
        @return: The specified XML document.
        @rtype: I{Document}
        """
        cache = self.cache()
        id = self.mangle(url, 'document')
        d = cache.get(id)
        if d is None:
            d = self.download(url)
            cache.put(id, d)
        self.plugins.document.parsed(url=url, document=d.root())
        return d
    
    def download(self, url):
        """
        Download the docuemnt.
        @param url: A document url.
        @type url: str.
        @return: A file pointer to the docuemnt.
        @rtype: file-like
        """
        store = DocumentStore()
        fp = store.open(url)
        if fp is None:
            fp = self.options.transport.open(Request(url))
        content = fp.read()
        fp.close()
        ctx = self.plugins.document.loaded(url=url, document=content)
        content = ctx.document 
        sax = Parser()
        return sax.parse(string=content)
    
    def cache(self):
        """
        Get the cache.
        @return: The I{options} when I{cachingpolicy} = B{0}.
        @rtype: L{Cache}
        """
        if self.options.cachingpolicy == 0:
            return self.options.cache
        else:
            return NoCache()


class DefinitionsReader(Reader):
    """
    The WSDL definitions reader provides an integration
    between the Definitions and the object cache.
    @ivar fn: A factory function (constructor) used to
        create the object not found in the cache.
    @type fn: I{Constructor}
    """
    
    def __init__(self, options, fn):
        """
        @param options: An options object.
        @type options: I{Options}
        @param fn: A factory function (constructor) used to
            create the object not found in the cache.
        @type fn: I{Constructor}
        """
        Reader.__init__(self, options)
        self.fn = fn
    
    def open(self, url):
        """
        Open a WSDL at the specified I{url}.
        First, the WSDL attempted to be retrieved from
        the I{object cache}.  After unpickled from the cache, the
        I{options} attribute is restored.
        If not found, it is downloaded and instantiated using the 
        I{fn} constructor and added to the cache for the next open().
        @param url: A WSDL url.
        @type url: str.
        @return: The WSDL object.
        @rtype: I{Definitions}
        """
        cache = self.cache()
        id = self.mangle(url, 'wsdl')
        d = cache.get(id)
        if d is None:
            d = self.fn(url, self.options)
            cache.put(id, d)
        else:
            d.options = self.options
            for imp in d.imports:
                imp.imported.options = self.options
        return d

    def cache(self):
        """
        Get the cache.
        @return: The I{options} when I{cachingpolicy} = B{1}.
        @rtype: L{Cache}
        """
        if self.options.cachingpolicy == 1:
            return self.options.cache
        else:
            return NoCache()
########NEW FILE########
__FILENAME__ = resolver
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The I{resolver} module provides a collection of classes that
provide wsdl/xsd named type resolution.
"""

import re
from logging import getLogger
from suds import *
from suds.sax import splitPrefix, Namespace
from suds.sudsobject import Object
from suds.xsd.query import BlindQuery, TypeQuery, qualify

log = getLogger(__name__)


class Resolver:
    """
    An I{abstract} schema-type resolver.
    @ivar schema: A schema object.
    @type schema: L{xsd.schema.Schema}
    """

    def __init__(self, schema):
        """
        @param schema: A schema object.
        @type schema: L{xsd.schema.Schema}
        """
        self.schema = schema

    def find(self, name, resolved=True):
        """
        Get the definition object for the schema object by name.
        @param name: The name of a schema object.
        @type name: basestring
        @param resolved: A flag indicating that the fully resolved type
            should be returned.
        @type resolved: boolean
        @return: The found schema I{type}
        @rtype: L{xsd.sxbase.SchemaObject}
        """
        #log.debug('searching schema for (%s)', name)
        qref = qualify(name, self.schema.root, self.schema.tns)
        query = BlindQuery(qref)
        result = query.execute(self.schema)
        if result is None:
            #log.error('(%s) not-found', name)
            return None
        #log.debug('found (%s) as (%s)', name, Repr(result))
        if resolved:
            result = result.resolve()
        return result


class PathResolver(Resolver):
    """
    Resolveds the definition object for the schema type located at the specified path.
    The path may contain (.) dot notation to specify nested types.
    @ivar wsdl: A wsdl object.
    @type wsdl: L{wsdl.Definitions}
    """

    def __init__(self, wsdl, ps='.'):
        """
        @param wsdl: A schema object.
        @type wsdl: L{wsdl.Definitions}
        @param ps: The path separator character
        @type ps: char
        """
        Resolver.__init__(self, wsdl.schema)
        self.wsdl = wsdl
        self.altp = re.compile('({)(.+)(})(.+)')
        self.splitp = re.compile('({.+})*[^\%s]+' % ps[0])

    def find(self, path, resolved=True):
        """
        Get the definition object for the schema type located at the specified path.
        The path may contain (.) dot notation to specify nested types.
        Actually, the path separator is usually a (.) but can be redefined
        during contruction.
        @param path: A (.) separated path to a schema type.
        @type path: basestring
        @param resolved: A flag indicating that the fully resolved type
            should be returned.
        @type resolved: boolean
        @return: The found schema I{type}
        @rtype: L{xsd.sxbase.SchemaObject}
        """
        result = None
        parts = self.split(path)
        try:
            result = self.root(parts)
            if len(parts) > 1:
                result = result.resolve(nobuiltin=True)
                result = self.branch(result, parts)
                result = self.leaf(result, parts)
            if resolved:
                result = result.resolve(nobuiltin=True)
        except PathResolver.BadPath:
            log.error('path: "%s", not-found' % path)
        return result

    def root(self, parts):
        """
        Find the path root.
        @param parts: A list of path parts.
        @type parts: [str,..]
        @return: The root.
        @rtype: L{xsd.sxbase.SchemaObject}
        """
        result = None
        name = parts[0]
        #log.debug('searching schema for (%s)', name)
        qref = self.qualify(parts[0])
        query = BlindQuery(qref)
        result = query.execute(self.schema)
        if result is None:
            log.error('(%s) not-found', name)
            raise PathResolver.BadPath(name)
        else:
            pass#log.debug('found (%s) as (%s)', name, Repr(result))
        return result

    def branch(self, root, parts):
        """
        Traverse the path until the leaf is reached.
        @param parts: A list of path parts.
        @type parts: [str,..]
        @param root: The root.
        @type root: L{xsd.sxbase.SchemaObject}
        @return: The end of the branch.
        @rtype: L{xsd.sxbase.SchemaObject}
        """
        result = root
        for part in parts[1:-1]:
            name = splitPrefix(part)[1]
            #log.debug('searching parent (%s) for (%s)', Repr(result), name)
            result, ancestry = result.get_child(name)
            if result is None:
                log.error('(%s) not-found', name)
                raise PathResolver.BadPath(name)
            else:
                result = result.resolve(nobuiltin=True)
                #log.debug('found (%s) as (%s)', name, Repr(result))
        return result

    def leaf(self, parent, parts):
        """
        Find the leaf.
        @param parts: A list of path parts.
        @type parts: [str,..]
        @param parent: The leaf's parent.
        @type parent: L{xsd.sxbase.SchemaObject}
        @return: The leaf.
        @rtype: L{xsd.sxbase.SchemaObject}
        """
        name = splitPrefix(parts[-1])[1]
        if name.startswith('@'):
            result, path = parent.get_attribute(name[1:])
        else:
            result, ancestry = parent.get_child(name)
        if result is None:
            raise PathResolver.BadPath(name)
        return result

    def qualify(self, name):
        """
        Qualify the name as either:
          - plain name
          - ns prefixed name (eg: ns0:Person)
          - fully ns qualified name (eg: {http://myns-uri}Person)
        @param name: The name of an object in the schema.
        @type name: str
        @return: A qualifed name.
        @rtype: qname
        """
        m = self.altp.match(name)
        if m is None:
            return qualify(name, self.wsdl.root, self.wsdl.tns)
        else:
            return (m.group(4), m.group(2))

    def split(self, s):
        """
        Split the string on (.) while preserving any (.) inside the
        '{}' alternalte syntax for full ns qualification.
        @param s: A plain or qualifed name.
        @type s: str
        @return: A list of the name's parts.
        @rtype: [str,..]
        """
        parts = []
        b = 0
        while 1:
            m = self.splitp.match(s, b)
            if m is None:
                break
            b,e = m.span()
            parts.append(s[b:e])
            b = e+1
        return parts

    class BadPath(Exception): pass


class TreeResolver(Resolver):
    """
    The tree resolver is a I{stateful} tree resolver
    used to resolve each node in a tree.  As such, it mirrors
    the tree structure to ensure that nodes are resolved in
    context.
    @ivar stack: The context stack.
    @type stack: list
    """

    def __init__(self, schema):
        """
        @param schema: A schema object.
        @type schema: L{xsd.schema.Schema}
        """
        Resolver.__init__(self, schema)
        self.stack = Stack()

    def reset(self):
        """
        Reset the resolver's state.
        """
        self.stack = Stack()

    def push(self, x):
        """
        Push an I{object} onto the stack.
        @param x: An object to push.
        @type x: L{Frame}
        @return: The pushed frame.
        @rtype: L{Frame}
        """
        if isinstance(x, Frame):
            frame = x
        else:
            frame = Frame(x)
        self.stack.append(frame)
        #log.debug('push: (%s)\n%s', Repr(frame), Repr(self.stack))
        return frame

    def top(self):
        """
        Get the I{frame} at the top of the stack.
        @return: The top I{frame}, else None.
        @rtype: L{Frame}
        """
        if len(self.stack):
            return self.stack[-1]
        else:
            return Frame.Empty()

    def pop(self):
        """
        Pop the frame at the top of the stack.
        @return: The popped frame, else None.
        @rtype: L{Frame}
        """
        if len(self.stack):
            popped = self.stack.pop()
            #log.debug('pop: (%s)\n%s', Repr(popped), Repr(self.stack))
            return popped
        else:
            pass#log.debug('stack empty, not-popped')
        return None

    def depth(self):
        """
        Get the current stack depth.
        @return: The current stack depth.
        @rtype: int
        """
        return len(self.stack)

    def getchild(self, name, parent):
        """ get a child by name """
        #log.debug('searching parent (%s) for (%s)', Repr(parent), name)
        if name.startswith('@'):
            return parent.get_attribute(name[1:])
        else:
            return parent.get_child(name)


class NodeResolver(TreeResolver):
    """
    The node resolver is a I{stateful} XML document resolver
    used to resolve each node in a tree.  As such, it mirrors
    the tree structure to ensure that nodes are resolved in
    context.
    """

    def __init__(self, schema):
        """
        @param schema: A schema object.
        @type schema: L{xsd.schema.Schema}
        """
        TreeResolver.__init__(self, schema)

    def find(self, node, resolved=False, push=True):
        """
        @param node: An xml node to be resolved.
        @type node: L{sax.element.Element}
        @param resolved: A flag indicating that the fully resolved type should be
            returned.
        @type resolved: boolean
        @param push: Indicates that the resolved type should be
            pushed onto the stack.
        @type push: boolean
        @return: The found schema I{type}
        @rtype: L{xsd.sxbase.SchemaObject}
        """
        name = node.name
        parent = self.top().resolved
        if parent is None:
            result, ancestry = self.query(name, node)
        else:
            result, ancestry = self.getchild(name, parent)
        known = self.known(node)
        if result is None:
            return result
        if push:
            frame = Frame(result, resolved=known, ancestry=ancestry)
            pushed = self.push(frame)
        if resolved:
            result = result.resolve()
        return result

    def findattr(self, name, resolved=True):
        """
        Find an attribute type definition.
        @param name: An attribute name.
        @type name: basestring
        @param resolved: A flag indicating that the fully resolved type should be
            returned.
        @type resolved: boolean
        @return: The found schema I{type}
        @rtype: L{xsd.sxbase.SchemaObject}
        """
        name = '@%s'%name
        parent = self.top().resolved
        if parent is None:
            result, ancestry = self.query(name, node)
        else:
            result, ancestry = self.getchild(name, parent)
        if result is None:
            return result
        if resolved:
            result = result.resolve()
        return result

    def query(self, name, node):
        """ blindly query the schema by name """
        #log.debug('searching schema for (%s)', name)
        qref = qualify(name, node, node.namespace())
        query = BlindQuery(qref)
        result = query.execute(self.schema)
        return (result, [])

    def known(self, node):
        """ resolve type referenced by @xsi:type """
        ref = node.get('type', Namespace.xsins)
        if ref is None:
            return None
        qref = qualify(ref, node, node.namespace())
        query = BlindQuery(qref)
        return query.execute(self.schema)


class GraphResolver(TreeResolver):
    """
    The graph resolver is a I{stateful} L{Object} graph resolver
    used to resolve each node in a tree.  As such, it mirrors
    the tree structure to ensure that nodes are resolved in
    context.
    """

    def __init__(self, schema):
        """
        @param schema: A schema object.
        @type schema: L{xsd.schema.Schema}
        """
        TreeResolver.__init__(self, schema)

    def find(self, name, object, resolved=False, push=True):
        """
        @param name: The name of the object to be resolved.
        @type name: basestring
        @param object: The name's value.
        @type object: (any|L{Object})
        @param resolved: A flag indicating that the fully resolved type
            should be returned.
        @type resolved: boolean
        @param push: Indicates that the resolved type should be
            pushed onto the stack.
        @type push: boolean
        @return: The found schema I{type}
        @rtype: L{xsd.sxbase.SchemaObject}
        """
        known = None
        parent = self.top().resolved
        if parent is None:
            result, ancestry = self.query(name)
        else:
            result, ancestry = self.getchild(name, parent)
        if result is None:
            return None
        if isinstance(object, Object):
            known = self.known(object)
        if push:
            frame = Frame(result, resolved=known, ancestry=ancestry)
            pushed = self.push(frame)
        if resolved:
            if known is None:
                result = result.resolve()
            else:
                result = known
        return result

    def query(self, name):
        """ blindly query the schema by name """
        #log.debug('searching schema for (%s)', name)
        schema = self.schema
        wsdl = self.wsdl()
        if wsdl is None:
            qref = qualify(name, schema.root, schema.tns)
        else:
            qref = qualify(name, wsdl.root, wsdl.tns)
        query = BlindQuery(qref)
        result = query.execute(schema)
        return (result, [])

    def wsdl(self):
        """ get the wsdl """
        container = self.schema.container
        if container is None:
            return None
        else:
            return container.wsdl

    def known(self, object):
        """ get the type specified in the object's metadata """
        try:
            md = object.__metadata__
            known = md.sxtype
            return known
        except:
            pass


class Frame:
    def __init__(self, type, resolved=None, ancestry=()):
        self.type = type
        if resolved is None:
            resolved = type.resolve()
        self.resolved = resolved.resolve()
        self.ancestry = ancestry

    def __str__(self):
        return '%s\n%s\n%s' % \
            (Repr(self.type),
            Repr(self.resolved),
            [Repr(t) for t in self.ancestry])

    class Empty:
        def __getattr__(self, name):
            if name == 'ancestry':
                return ()
            else:
                return None


class Stack(list):
    def __repr__(self):
        result = []
        for item in self:
            result.append(repr(item))
        return '\n'.join(result)

########NEW FILE########
__FILENAME__ = attribute
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides XML I{attribute} classes.
"""

import suds.sax
from logging import getLogger
from suds import *
from suds.sax import *
from suds.sax.text import Text

log = getLogger(__name__)

class Attribute:
    """
    An XML attribute object.
    @ivar parent: The node containing this attribute
    @type parent: L{element.Element}
    @ivar prefix: The I{optional} namespace prefix.
    @type prefix: basestring
    @ivar name: The I{unqualified} name of the attribute
    @type name: basestring
    @ivar value: The attribute's value
    @type value: basestring
    """
    def __init__(self, name, value=None):
        """
        @param name: The attribute's name with I{optional} namespace prefix.
        @type name: basestring
        @param value: The attribute's value
        @type value: basestring 
        """
        self.parent = None
        self.prefix, self.name = splitPrefix(name)
        self.setValue(value)
        
    def clone(self, parent=None):
        """
        Clone this object.
        @param parent: The parent for the clone.
        @type parent: L{element.Element}
        @return: A copy of this object assigned to the new parent.
        @rtype: L{Attribute}
        """
        a = Attribute(self.qname(), self.value)
        a.parent = parent
        return a
    
    def qname(self):
        """
        Get the B{fully} qualified name of this attribute
        @return: The fully qualified name.
        @rtype: basestring
        """
        if self.prefix is None:
            return self.name
        else:
            return ':'.join((self.prefix, self.name))
        
    def setValue(self, value):
        """
        Set the attributes value
        @param value: The new value (may be None)
        @type value: basestring
        @return: self
        @rtype: L{Attribute}
        """
        if isinstance(value, Text):
            self.value = value
        else:
            self.value = Text(value)
        return self
        
    def getValue(self, default=Text('')):
        """
        Get the attributes value with optional default.
        @param default: An optional value to be return when the
            attribute's has not been set.
        @type default: basestring
        @return: The attribute's value, or I{default}
        @rtype: L{Text}
        """
        if self.hasText():
            return self.value
        else:
            return default
    
    def hasText(self):
        """
        Get whether the attribute has I{text} and that it is not an empty
        (zero length) string.
        @return: True when has I{text}.
        @rtype: boolean
        """
        return ( self.value is not None and len(self.value) )
        
    def namespace(self):
        """
        Get the attributes namespace.  This may either be the namespace
        defined by an optional prefix, or its parent's namespace.
        @return: The attribute's namespace
        @rtype: (I{prefix}, I{name})
        """
        if self.prefix is None:
            return Namespace.default
        else:
            return self.resolvePrefix(self.prefix)
        
    def resolvePrefix(self, prefix):
        """
        Resolve the specified prefix to a known namespace.
        @param prefix: A declared prefix
        @type prefix: basestring
        @return: The namespace that has been mapped to I{prefix}
        @rtype: (I{prefix}, I{name})
        """
        ns = Namespace.default
        if self.parent is not None:
            ns = self.parent.resolvePrefix(prefix)
        return ns
    
    def match(self, name=None, ns=None):
        """
        Match by (optional) name and/or (optional) namespace.
        @param name: The optional attribute tag name.
        @type name: str
        @param ns: An optional namespace.
        @type ns: (I{prefix}, I{name})
        @return: True if matched.
        @rtype: boolean
        """
        if name is None:
            byname = True
        else:
            byname = ( self.name == name )
        if ns is None:
            byns = True
        else:
            byns = ( self.namespace()[1] == ns[1] )
        return ( byname and byns )
    
    def __eq__(self, rhs):
        """ equals operator """
        return rhs is not None and \
            isinstance(rhs, Attribute) and \
            self.prefix == rhs.name and \
            self.name == rhs.name
            
    def __repr__(self):
        """ get a string representation """
        return \
            'attr (prefix=%s, name=%s, value=(%s))' %\
                (self.prefix, self.name, self.value)

    def __str__(self):
        """ get an xml string representation """
        return unicode(self).encode('utf-8')
    
    def __unicode__(self):
        """ get an xml string representation """
        n = self.qname()
        if self.hasText():
            v = self.value.escape()
        else:
            v = self.value
        return u'%s="%s"' % (n, v)

########NEW FILE########
__FILENAME__ = date
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Nathan Van Gheem (vangheem@gmail.com)

"""
The I{xdate} module provides classes for converstion
between XML dates and python objects.
"""

from logging import getLogger
from suds import *
from suds.xsd import *
import time
import datetime as dt
import re

log = getLogger(__name__)


class Date:
    """
    An XML date object.
    Supported formats:
        - YYYY-MM-DD
        - YYYY-MM-DD(z|Z)
        - YYYY-MM-DD+06:00
        - YYYY-MM-DD-06:00
    @ivar date: The object value.
    @type date: B{datetime}.I{date}
    """
    def __init__(self, date):
        """
        @param date: The value of the object.
        @type date: (date|str)
        @raise ValueError: When I{date} is invalid.
        """
        if isinstance(date, dt.date):
            self.date = date
            return
        if isinstance(date, basestring):
            self.date = self.__parse(date)
            return
        raise ValueError, type(date)
    
    def year(self):
        """
        Get the I{year} component.
        @return: The year.
        @rtype: int
        """
        return self.date.year
    
    def month(self):
        """
        Get the I{month} component.
        @return: The month.
        @rtype: int
        """
        return self.date.month
    
    def day(self):
        """
        Get the I{day} component.
        @return: The day.
        @rtype: int
        """
        return self.date.day
        
    def __parse(self, s):
        """
        Parse the string date.
        Supported formats:
            - YYYY-MM-DD
            - YYYY-MM-DD(z|Z)
            - YYYY-MM-DD+06:00
            - YYYY-MM-DD-06:00
        Although, the TZ is ignored because it's meaningless
        without the time, right?
        @param s: A date string.
        @type s: str
        @return: A date object.
        @rtype: I{date}
        """
        try:
            year, month, day = s[:10].split('-', 2)
            year = int(year)
            month = int(month)
            day = int(day)
            return dt.date(year, month, day)
        except:
            log.debug(s, exec_info=True)
            raise ValueError, 'Invalid format "%s"' % s
        
    def __str__(self):
        return unicode(self)
    
    def __unicode__(self):
        return self.date.isoformat()


class Time:
    """
    An XML time object.
    Supported formats:
        - HH:MI:SS
        - HH:MI:SS(z|Z)
        - HH:MI:SS.ms
        - HH:MI:SS.ms(z|Z)
        - HH:MI:SS(+|-)06:00
        - HH:MI:SS.ms(+|-)06:00
    @ivar tz: The timezone
    @type tz: L{Timezone}
    @ivar date: The object value.
    @type date: B{datetime}.I{time}
    """
    
    def __init__(self, time, adjusted=True):
        """
        @param time: The value of the object.
        @type time: (time|str)
        @param adjusted: Adjust for I{local} Timezone.
        @type adjusted: boolean
        @raise ValueError: When I{time} is invalid.
        """
        self.tz = Timezone()
        if isinstance(time, dt.time):
            self.time = time
            return
        if isinstance(time, basestring):
            self.time = self.__parse(time)
            if adjusted:
                self.__adjust()
            return
        raise ValueError, type(time)
    
    def hour(self):
        """
        Get the I{hour} component.
        @return: The hour.
        @rtype: int
        """
        return self.time.hour
    
    def minute(self):
        """
        Get the I{minute} component.
        @return: The minute.
        @rtype: int
        """
        return self.time.minute
    
    def second(self):
        """
        Get the I{seconds} component.
        @return: The seconds.
        @rtype: int
        """
        return self.time.second
    
    def microsecond(self):
        """
        Get the I{microsecond} component.
        @return: The microsecond.
        @rtype: int
        """
        return self.time.microsecond
    
    def __adjust(self):
        """
        Adjust for TZ offset.
        """
        if hasattr(self, 'offset'):
            today = dt.date.today()
            delta = self.tz.adjustment(self.offset)
            d = dt.datetime.combine(today, self.time)
            d = ( d + delta )
            self.time = d.time()
        
    def __parse(self, s):
        """
        Parse the string date.
        Patterns:
            - HH:MI:SS
            - HH:MI:SS(z|Z)
            - HH:MI:SS.ms
            - HH:MI:SS.ms(z|Z)
            - HH:MI:SS(+|-)06:00
            - HH:MI:SS.ms(+|-)06:00
        @param s: A time string.
        @type s: str
        @return: A time object.
        @rtype: B{datetime}.I{time}
        """
        try:
            offset = None
            part = Timezone.split(s)
            hour, minute, second = part[0].split(':', 2)
            hour = int(hour)
            minute = int(minute)
            second, ms = self.__second(second)
            if len(part) == 2:
                self.offset = self.__offset(part[1])
            if ms is None:
                return dt.time(hour, minute, second)
            else:
                return dt.time(hour, minute, second, ms)
        except:
            log.debug(s, exec_info=True)
            raise ValueError, 'Invalid format "%s"' % s
        
    def __second(self, s):
        """
        Parse the seconds and microseconds.
        The microseconds are truncated to 999999 due to a restriction in
        the python datetime.datetime object.
        @param s: A string representation of the seconds.
        @type s: str
        @return: Tuple of (sec,ms)
        @rtype: tuple.
        """
        part = s.split('.')
        if len(part) > 1:
            return (int(part[0]), int(part[1][:6]))
        else:
            return (int(part[0]), None)
        
    def __offset(self, s):
        """
        Parse the TZ offset.
        @param s: A string representation of the TZ offset.
        @type s: str
        @return: The signed offset in hours.
        @rtype: str
        """
        if len(s) == len('-00:00'):
            return int(s[:3])
        if len(s) == 0:
            return self.tz.local
        if len(s) == 1:
            return 0
        raise Exception()

    def __str__(self):
        return unicode(self)
    
    def __unicode__(self):
        time = self.time.isoformat()
        if self.tz.local:
            return '%s%+.2d:00' % (time, self.tz.local)
        else:
            return '%sZ' % time


class DateTime(Date,Time):
    """
    An XML time object.
    Supported formats:
        - YYYY-MM-DDB{T}HH:MI:SS
        - YYYY-MM-DDB{T}HH:MI:SS(z|Z)
        - YYYY-MM-DDB{T}HH:MI:SS.ms
        - YYYY-MM-DDB{T}HH:MI:SS.ms(z|Z)
        - YYYY-MM-DDB{T}HH:MI:SS(+|-)06:00
        - YYYY-MM-DDB{T}HH:MI:SS.ms(+|-)06:00
    @ivar datetime: The object value.
    @type datetime: B{datetime}.I{datedate}
    """
    def __init__(self, date):
        """
        @param date: The value of the object.
        @type date: (datetime|str)
        @raise ValueError: When I{tm} is invalid.
        """
        if isinstance(date, dt.datetime):
            Date.__init__(self, date.date())
            Time.__init__(self, date.time())
            self.datetime = \
                dt.datetime.combine(self.date, self.time)
            return
        if isinstance(date, basestring):
            part = date.split('T')
            Date.__init__(self, part[0])
            Time.__init__(self, part[1], 0)
            self.datetime = \
                dt.datetime.combine(self.date, self.time)
            self.__adjust()
            return
        raise ValueError, type(date)
    
    def __adjust(self):
        """
        Adjust for TZ offset.
        """
        if not hasattr(self, 'offset'):
            return
        delta = self.tz.adjustment(self.offset)
        try:
            d = ( self.datetime + delta )
            self.datetime = d
            self.date = d.date()
            self.time = d.time()
        except OverflowError:
            log.warn('"%s" caused overflow, not-adjusted', self.datetime)

    def __str__(self):
        return unicode(self)
    
    def __unicode__(self):
        s = []
        s.append(Date.__unicode__(self))
        s.append(Time.__unicode__(self))
        return 'T'.join(s)
    
    
class UTC(DateTime):
    """
    Represents current UTC time.
    """
    
    def __init__(self, date=None):
        if date is None:
            date = dt.datetime.utcnow()
        DateTime.__init__(self, date)
        self.tz.local = 0
    
    
class Timezone:
    """
    Timezone object used to do TZ conversions
    @cvar local: The (A) local TZ offset.
    @type local: int
    @cvar patten: The regex patten to match TZ.
    @type patten: re.Pattern
    """
    
    pattern = re.compile('([zZ])|([\-\+][0-9]{2}:[0-9]{2})')
    
    LOCAL = ( 0-time.timezone/60/60 )

    def __init__(self, offset=None):
        if offset is None:
            offset = self.LOCAL
        self.local = offset
    
    @classmethod
    def split(cls, s):
        """
        Split the TZ from string.
        @param s: A string containing a timezone
        @type s: basestring
        @return: The split parts.
        @rtype: tuple
        """
        m = cls.pattern.search(s)
        if m is None:
            return (s,)
        x = m.start(0)
        return (s[:x], s[x:])

    def adjustment(self, offset):
        """
        Get the adjustment to the I{local} TZ.
        @return: The delta between I{offset} and local TZ.
        @rtype: B{datetime}.I{timedelta}
        """
        delta = ( self.local - offset )
        return dt.timedelta(hours=delta)

########NEW FILE########
__FILENAME__ = document
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides XML I{document} classes.
"""

from logging import getLogger
from suds import *
from suds.sax import *
from suds.sax.element import Element

log = getLogger(__name__)

class Document(Element):
    """ simple document """
    
    DECL = '<?xml version="1.0" encoding="UTF-8"?>'

    def __init__(self, root=None):
        Element.__init__(self, 'document')
        if root is not None:
            self.append(root)
        
    def root(self):
        if len(self.children):
            return self.children[0]
        else:
            return None
        
    def str(self):
        s = []
        s.append(self.DECL)
        s.append('\n')
        s.append(self.root().str())
        return ''.join(s)
    
    def plain(self):
        s = []
        s.append(self.DECL)
        s.append(self.root().plain())
        return ''.join(s)

    def __str__(self):
        return unicode(self).encode('utf-8')
    
    def __unicode__(self):
        return self.str()
########NEW FILE########
__FILENAME__ = element
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides XML I{element} classes.
"""

from logging import getLogger
from suds import *
from suds.sax import *
from suds.sax.text import Text
from suds.sax.attribute import Attribute
import sys 
if sys.version_info < (2, 4, 0): 
    from sets import Set as set 
    del sys 

log = getLogger(__name__)

class Element:
    """
    An XML element object.
    @ivar parent: The node containing this attribute
    @type parent: L{Element}
    @ivar prefix: The I{optional} namespace prefix.
    @type prefix: basestring
    @ivar name: The I{unqualified} name of the attribute
    @type name: basestring
    @ivar expns: An explicit namespace (xmlns="...").
    @type expns: (I{prefix}, I{name})
    @ivar nsprefixes: A mapping of prefixes to namespaces.
    @type nsprefixes: dict
    @ivar attributes: A list of XML attributes.
    @type attributes: [I{Attribute},]
    @ivar text: The element's I{text} content.
    @type text: basestring
    @ivar children: A list of child elements.
    @type children: [I{Element},]
    @cvar matcher: A collection of I{lambda} for string matching.
    @cvar specialprefixes: A dictionary of builtin-special prefixes.
    """

    matcher = \
    {
        'eq': lambda a,b: a == b,
        'startswith' : lambda a,b: a.startswith(b),
        'endswith' : lambda a,b: a.endswith(b),
        'contains' : lambda a,b: b in a 
    }
    
    specialprefixes = { Namespace.xmlns[0] : Namespace.xmlns[1]  }
    
    @classmethod
    def buildPath(self, parent, path):
        """
        Build the specifed pat as a/b/c where missing intermediate nodes are built
        automatically.
        @param parent: A parent element on which the path is built.
        @type parent: I{Element}
        @param path: A simple path separated by (/).
        @type path: basestring
        @return: The leaf node of I{path}.
        @rtype: L{Element}
        """
        for tag in path.split('/'):
            child = parent.getChild(tag)
            if child is None:
                child = Element(tag, parent)
            parent = child
        return child

    def __init__(self, name, parent=None, ns=None):
        """
        @param name: The element's (tag) name.  May cotain a prefix.
        @type name: basestring
        @param parent: An optional parent element.
        @type parent: I{Element}
        @param ns: An optional namespace
        @type ns: (I{prefix}, I{name})
        """
        
        self.rename(name)
        self.expns = None
        self.nsprefixes = {}
        self.attributes = []
        self.text = None
        if parent is not None:
            if isinstance(parent, Element):
                self.parent = parent
            else:
                raise Exception('parent (%s) not-valid', parent.__class__.__name__)
        else:
            self.parent = None
        self.children = []
        self.applyns(ns)
        
    def rename(self, name):
        """
        Rename the element.
        @param name: A new name for the element.
        @type name: basestring 
        """
        if name is None:
            raise Exception('name (%s) not-valid' % name)
        else:
            self.prefix, self.name = splitPrefix(name)
            
    def setPrefix(self, p, u=None):
        """
        Set the element namespace prefix.
        @param p: A new prefix for the element.
        @type p: basestring 
        @param u: A namespace URI to be mapped to the prefix.
        @type u: basestring
        @return: self
        @rtype: L{Element}
        """
        self.prefix = p
        if p is not None and u is not None:
            self.addPrefix(p, u)
        return self

    def qname(self):
        """
        Get the B{fully} qualified name of this element
        @return: The fully qualified name.
        @rtype: basestring
        """
        if self.prefix is None:
            return self.name
        else:
            return '%s:%s' % (self.prefix, self.name)
        
    def getRoot(self):
        """
        Get the root (top) node of the tree.
        @return: The I{top} node of this tree.
        @rtype: I{Element}
        """
        if self.parent is None:
            return self
        else:
            return self.parent.getRoot()
        
    def clone(self, parent=None):
        """
        Deep clone of this element and children.
        @param parent: An optional parent for the copied fragment.
        @type parent: I{Element}
        @return: A deep copy parented by I{parent}
        @rtype: I{Element}
        """
        root = Element(self.qname(), parent, self.namespace())
        for a in self.attributes:
            root.append(a.clone(self))
        for c in self.children:
            root.append(c.clone(self))
        for item in self.nsprefixes.items():
            root.addPrefix(item[0], item[1])
        return root
    
    def detach(self):
        """
        Detach from parent.
        @return: This element removed from its parent's
            child list and I{parent}=I{None}
        @rtype: L{Element}
        """
        if self.parent is not None:
            if self in self.parent.children:
                self.parent.children.remove(self)
            self.parent = None
        return self
        
    def set(self, name, value):
        """
        Set an attribute's value.
        @param name: The name of the attribute.
        @type name: basestring
        @param value: The attribute value.
        @type value: basestring
        @see: __setitem__()
        """
        attr = self.getAttribute(name)
        if attr is None:
            attr = Attribute(name, value)
            self.append(attr)
        else:
            attr.setValue(value)
            
    def unset(self, name):
        """
        Unset (remove) an attribute.
        @param name: The attribute name.
        @type name: str
        @return: self
        @rtype: L{Element}
        """
        try:
            attr = self.getAttribute(name)
            self.attributes.remove(attr)
        except:
            pass
        return self
            
            
    def get(self, name, ns=None, default=None):
        """
        Get the value of an attribute by name.
        @param name: The name of the attribute.
        @type name: basestring
        @param ns: The optional attribute's namespace.
        @type ns: (I{prefix}, I{name})
        @param default: An optional value to be returned when either
            the attribute does not exist of has not value.
        @type default: basestring
        @return: The attribute's value or I{default}
        @rtype: basestring
        @see: __getitem__()
        """
        attr = self.getAttribute(name, ns)
        if attr is None or attr.value is None:
            return default
        else:
            return attr.getValue()   

    def setText(self, value):
        """
        Set the element's L{Text} content.
        @param value: The element's text value.
        @type value: basestring
        @return: self
        @rtype: I{Element}
        """
        if isinstance(value, Text):
            self.text = value
        else:
            self.text = Text(value)
        return self
        
    def getText(self, default=None):
        """
        Get the element's L{Text} content with optional default
        @param default: A value to be returned when no text content exists.
        @type default: basestring
        @return: The text content, or I{default}
        @rtype: L{Text}
        """
        if self.hasText():
            return self.text
        else:
            return default
    
    def trim(self):
        """
        Trim leading and trailing whitespace.
        @return: self
        @rtype: L{Element}
        """
        if self.hasText():
            self.text = self.text.trim()
        return self
    
    def hasText(self):
        """
        Get whether the element has I{text} and that it is not an empty
        (zero length) string.
        @return: True when has I{text}.
        @rtype: boolean
        """
        return ( self.text is not None and len(self.text) )
        
    def namespace(self):
        """
        Get the element's namespace.
        @return: The element's namespace by resolving the prefix, the explicit 
            namespace or the inherited namespace.
        @rtype: (I{prefix}, I{name})
        """
        if self.prefix is None:
            return self.defaultNamespace()
        else:
            return self.resolvePrefix(self.prefix)
        
    def defaultNamespace(self):
        """
        Get the default (unqualified namespace).  
        This is the expns of the first node (looking up the tree)
        that has it set.
        @return: The namespace of a node when not qualified.
        @rtype: (I{prefix}, I{name})
        """
        p = self
        while p is not None:
            if p.expns is not None:
                return (None, p.expns)
            else:
                p = p.parent
        return Namespace.default
            
    def append(self, objects):
        """
        Append the specified child based on whether it is an
        element or an attrbuite.
        @param objects: A (single|collection) of attribute(s) or element(s)
            to be added as children.
        @type objects: (L{Element}|L{Attribute})
        @return: self
        @rtype: L{Element}
        """
        if not isinstance(objects, (list, tuple)):
            objects = (objects,)
        for child in objects:
            if isinstance(child, Element):
                self.children.append(child)
                child.parent = self
                continue
            if isinstance(child, Attribute):
                self.attributes.append(child)
                child.parent = self
                continue
            raise Exception('append %s not-valid' % child.__class__.__name__)
        return self
    
    def insert(self, objects, index=0):
        """
        Insert an L{Element} content at the specified index.
        @param objects: A (single|collection) of attribute(s) or element(s)
            to be added as children.
        @type objects: (L{Element}|L{Attribute})
        @param index: The position in the list of children to insert.
        @type index: int
        @return: self
        @rtype: L{Element}
        """
        objects = (objects,)
        for child in objects:
            if isinstance(child, Element):
                self.children.insert(index, child)
                child.parent = self
            else:
                raise Exception('append %s not-valid' % child.__class__.__name__)
        return self
    
    def remove(self, child):
        """
        Remove the specified child element or attribute.
        @param child: A child to remove.
        @type child: L{Element}|L{Attribute}
        @return: The detached I{child} when I{child} is an element, else None.
        @rtype: L{Element}|None
        """
        if isinstance(child, Element):
            return child.detach()
        if isinstance(child, Attribute):
            self.attributes.remove(child)
        return None
            
    def replaceChild(self, child, content):
        """
        Replace I{child} with the specified I{content}.
        @param child: A child element.
        @type child: L{Element}
        @param content: An element or collection of elements.
        @type content: L{Element} or [L{Element},]
        """
        if child not in self.children:
            raise Exception('child not-found')
        index = self.children.index(child)
        self.remove(child)
        if not isinstance(content, (list, tuple)):
            content = (content,)
        for node in content:
            self.children.insert(index, node.detach())
            node.parent = self
            index += 1
            
    def getAttribute(self, name, ns=None, default=None):
        """
        Get an attribute by name and (optional) namespace
        @param name: The name of a contained attribute (may contain prefix).
        @type name: basestring
        @param ns: An optional namespace
        @type ns: (I{prefix}, I{name})
        @param default: Returned when attribute not-found.
        @type default: L{Attribute}
        @return: The requested attribute object.
        @rtype: L{Attribute}
        """
        if ns is None:
            prefix, name = splitPrefix(name)
            if prefix is None:
                ns = None
            else:
                ns = self.resolvePrefix(prefix)
        for a in self.attributes:
            if a.match(name, ns):
                return a
        return default

    def getChild(self, name, ns=None, default=None):
        """
        Get a child by (optional) name and/or (optional) namespace.
        @param name: The name of a child element (may contain prefix).
        @type name: basestring
        @param ns: An optional namespace used to match the child.
        @type ns: (I{prefix}, I{name})
        @param default: Returned when child not-found.
        @type default: L{Element}
        @return: The requested child, or I{default} when not-found.
        @rtype: L{Element}
        """
        if ns is None:
            prefix, name = splitPrefix(name)
            if prefix is None:
                ns = None
            else:
                ns = self.resolvePrefix(prefix)
        for c in self.children:
            if c.match(name, ns):
                return c
        return default
    
    def childAtPath(self, path):
        """
        Get a child at I{path} where I{path} is a (/) separated
        list of element names that are expected to be children.
        @param path: A (/) separated list of element names.
        @type path: basestring
        @return: The leaf node at the end of I{path}
        @rtype: L{Element}
        """
        result = None
        node = self
        for name in [p for p in path.split('/') if len(p) > 0]:
            ns = None
            prefix, name = splitPrefix(name)
            if prefix is not None:
                ns = node.resolvePrefix(prefix)
            result = node.getChild(name, ns)
            if result is None:
                break;
            else:
                node = result
        return result

    def childrenAtPath(self, path):
        """
        Get a list of children at I{path} where I{path} is a (/) separated
        list of element names that are expected to be children.
        @param path: A (/) separated list of element names.
        @type path: basestring
        @return: The collection leaf nodes at the end of I{path}
        @rtype: [L{Element},...]
        """
        parts = [p for p in path.split('/') if len(p) > 0]
        if len(parts) == 1:
            result = self.getChildren(path)
        else:
            result = self.__childrenAtPath(parts)
        return result
        
    def getChildren(self, name=None, ns=None):
        """
        Get a list of children by (optional) name and/or (optional) namespace.
        @param name: The name of a child element (may contain prefix).
        @type name: basestring
        @param ns: An optional namespace used to match the child.
        @type ns: (I{prefix}, I{name})
        @return: The list of matching children.
        @rtype: [L{Element},...]
        """
        if ns is None:
            if name is None:
                return self.children
            prefix, name = splitPrefix(name)
            if prefix is None:
                ns = None
            else:
                ns = self.resolvePrefix(prefix)
        return [c for c in self.children if c.match(name, ns)]
    
    def detachChildren(self):
        """
        Detach and return this element's children.
        @return: The element's children (detached).
        @rtype: [L{Element},...]
        """
        detached = self.children
        self.children = []
        for child in detached:
            child.parent = None
        return detached
        
    def resolvePrefix(self, prefix, default=Namespace.default):
        """
        Resolve the specified prefix to a namespace.  The I{nsprefixes} is
        searched.  If not found, it walks up the tree until either resolved or
        the top of the tree is reached.  Searching up the tree provides for
        inherited mappings.
        @param prefix: A namespace prefix to resolve.
        @type prefix: basestring
        @param default: An optional value to be returned when the prefix
            cannot be resolved.
        @type default: (I{prefix},I{URI})
        @return: The namespace that is mapped to I{prefix} in this context.
        @rtype: (I{prefix},I{URI})
        """
        n = self
        while n is not None:
            if prefix in n.nsprefixes:
                return (prefix, n.nsprefixes[prefix])
            if prefix in self.specialprefixes:
                return (prefix, self.specialprefixes[prefix])
            n = n.parent
        return default
    
    def addPrefix(self, p, u):
        """
        Add or update a prefix mapping.
        @param p: A prefix.
        @type p: basestring
        @param u: A namespace URI.
        @type u: basestring
        @return: self
        @rtype: L{Element}
        """
        self.nsprefixes[p] = u
        return self
 
    def updatePrefix(self, p, u):
        """
        Update (redefine) a prefix mapping for the branch. 
        @param p: A prefix.
        @type p: basestring
        @param u: A namespace URI.
        @type u: basestring
        @return: self
        @rtype: L{Element}
        @note: This method traverses down the entire branch!
        """
        if p in self.nsprefixes:
            self.nsprefixes[p] = u
        for c in self.children:
            c.updatePrefix(p, u)
        return self
            
    def clearPrefix(self, prefix):
        """
        Clear the specified prefix from the prefix mappings.
        @param prefix: A prefix to clear.
        @type prefix: basestring
        @return: self
        @rtype: L{Element}
        """
        if prefix in self.nsprefixes:
            del self.nsprefixes[prefix]
        return self
    
    def findPrefix(self, uri, default=None):
        """
        Find the first prefix that has been mapped to a namespace URI.
        The local mapping is searched, then it walks up the tree until
        it reaches the top or finds a match.
        @param uri: A namespace URI.
        @type uri: basestring
        @param default: A default prefix when not found.
        @type default: basestring
        @return: A mapped prefix.
        @rtype: basestring
        """
        for item in self.nsprefixes.items():
            if item[1] == uri:
                prefix = item[0]
                return prefix
        for item in self.specialprefixes.items():
            if item[1] == uri:
                prefix = item[0]
                return prefix      
        if self.parent is not None:
            return self.parent.findPrefix(uri, default)
        else:
            return default

    def findPrefixes(self, uri, match='eq'):
        """
        Find all prefixes that has been mapped to a namespace URI.
        The local mapping is searched, then it walks up the tree until
        it reaches the top collecting all matches.
        @param uri: A namespace URI.
        @type uri: basestring
        @param match: A matching function L{Element.matcher}.
        @type match: basestring
        @return: A list of mapped prefixes.
        @rtype: [basestring,...]
        """
        result = []
        for item in self.nsprefixes.items():
            if self.matcher[match](item[1], uri):
                prefix = item[0]
                result.append(prefix)
        for item in self.specialprefixes.items():
            if self.matcher[match](item[1], uri):
                prefix = item[0]
                result.append(prefix)
        if self.parent is not None:
            result += self.parent.findPrefixes(uri, match)
        return result
    
    def promotePrefixes(self):
        """
        Push prefix declarations up the tree as far as possible.  Prefix
        mapping are pushed to its parent unless the parent has the
        prefix mapped to another URI or the parent has the prefix.
        This is propagated up the tree until the top is reached.
        @return: self
        @rtype: L{Element}
        """
        for c in self.children:
            c.promotePrefixes()
        if self.parent is None:
            return
        for p,u in self.nsprefixes.items():
            if p in self.parent.nsprefixes:
                pu = self.parent.nsprefixes[p]
                if pu == u:
                    del self.nsprefixes[p]
                continue
            if p != self.parent.prefix:
                self.parent.nsprefixes[p] = u
                del self.nsprefixes[p]
        return self
    
    def refitPrefixes(self):
        """
        Refit namespace qualification by replacing prefixes
        with explicit namespaces. Also purges prefix mapping table.
        @return: self
        @rtype: L{Element}
        """
        for c in self.children:
            c.refitPrefixes()
        if self.prefix is not None:
            ns = self.resolvePrefix(self.prefix)
            if ns[1] is not None:
                self.expns = ns[1]
        self.prefix = None
        self.nsprefixes = {}
        return self
                
    def normalizePrefixes(self):
        """
        Normalize the namespace prefixes.
        This generates unique prefixes for all namespaces.  Then retrofits all
        prefixes and prefix mappings.  Further, it will retrofix attribute values
        that have values containing (:).
        @return: self
        @rtype: L{Element}
        """
        PrefixNormalizer.apply(self)
        return self

    def isempty(self, content=True):
        """
        Get whether the element has no children.
        @param content: Test content (children & text) only.
        @type content: boolean
        @return: True when element has not children.
        @rtype: boolean
        """
        noattrs = not len(self.attributes)
        nochildren = not len(self.children)
        notext = ( self.text is None )
        nocontent = ( nochildren and notext )
        if content:
            return nocontent
        else:
            return ( nocontent and noattrs )
            
            
    def isnil(self):
        """
        Get whether the element is I{nil} as defined by having
        an attribute in the I{xsi:nil="true"}
        @return: True if I{nil}, else False
        @rtype: boolean
        """
        nilattr = self.getAttribute('nil', ns=Namespace.xsins)
        if nilattr is None:
            return False
        else:
            return ( nilattr.getValue().lower() == 'true' )
        
    def setnil(self, flag=True):
        """
        Set this node to I{nil} as defined by having an
        attribute I{xsi:nil}=I{flag}.
        @param flag: A flag inidcating how I{xsi:nil} will be set.
        @type flag: boolean
        @return: self
        @rtype: L{Element}
        """
        p, u = Namespace.xsins
        name  = ':'.join((p, 'nil'))
        self.set(name, str(flag).lower())
        self.addPrefix(p, u)
        if flag:
            self.text = None
        return self
            
    def applyns(self, ns):
        """
        Apply the namespace to this node.  If the prefix is I{None} then
        this element's explicit namespace I{expns} is set to the
        URI defined by I{ns}.  Otherwise, the I{ns} is simply mapped.
        @param ns: A namespace.
        @type ns: (I{prefix},I{URI})
        """
        if ns is None:
            return
        if not isinstance(ns, (tuple,list)):
            raise Exception('namespace must be tuple')
        if ns[0] is None:
            self.expns = ns[1]
        else:
            self.prefix = ns[0]
            self.nsprefixes[ns[0]] = ns[1]
            
    def str(self, indent=0):
        """
        Get a string representation of this XML fragment.
        @param indent: The indent to be used in formatting the output.
        @type indent: int
        @return: A I{pretty} string.
        @rtype: basestring
        """
        tab = '%*s'%(indent*3,'')
        result = []
        result.append('%s<%s' % (tab, self.qname()))
        result.append(self.nsdeclarations())
        for a in [unicode(a) for a in self.attributes]:
            result.append(' %s' % a)
        if self.isempty():
            result.append('/>')
            return ''.join(result)
        result.append('>')
        if self.hasText():
            result.append(self.text.escape())
        for c in self.children:
            result.append('\n')
            result.append(c.str(indent+1))
        if len(self.children):
            result.append('\n%s' % tab)
        result.append('</%s>' % self.qname())
        result = ''.join(result)
        return result
    
    def plain(self):
        """
        Get a string representation of this XML fragment.
        @return: A I{plain} string.
        @rtype: basestring
        """
        result = []
        result.append('<%s' % self.qname())
        result.append(self.nsdeclarations())
        for a in [unicode(a) for a in self.attributes]:
            result.append(' %s' % a)
        if self.isempty():
            result.append('/>')
            return ''.join(result)
        result.append('>')
        if self.hasText():
            result.append(self.text.escape())
        for c in self.children:
            result.append(c.plain())
        result.append('</%s>' % self.qname())
        result = ''.join(result)
        return result

    def nsdeclarations(self):
        """
        Get a string representation for all namespace declarations
        as xmlns="" and xmlns:p="".
        @return: A separated list of declarations.
        @rtype: basestring
        """
        s = []
        myns = (None, self.expns)
        if self.parent is None:
            pns = Namespace.default
        else:
            pns = (None, self.parent.expns)
        if myns[1] != pns[1]:
            if self.expns is not None:
                d = ' xmlns="%s"' % self.expns
                s.append(d)
        for item in self.nsprefixes.items():
            (p,u) = item
            if self.parent is not None:
                ns = self.parent.resolvePrefix(p)
                if ns[1] == u: continue
            d = ' xmlns:%s="%s"' % (p, u)
            s.append(d)
        return ''.join(s)
    
    def match(self, name=None, ns=None):
        """
        Match by (optional) name and/or (optional) namespace.
        @param name: The optional element tag name.
        @type name: str
        @param ns: An optional namespace.
        @type ns: (I{prefix}, I{name})
        @return: True if matched.
        @rtype: boolean
        """
        if name is None:
            byname = True
        else:
            byname = ( self.name == name )
        if ns is None:
            byns = True
        else:
            byns = ( self.namespace()[1] == ns[1] )
        return ( byname and byns )
    
    def branch(self):
        """
        Get a flattened representation of the branch.
        @return: A flat list of nodes.
        @rtype: [L{Element},..]
        """
        branch = [self]
        for c in self.children:
            branch += c.branch()
        return branch
    
    def ancestors(self):
        """
        Get a list of ancestors.
        @return: A list of ancestors.
        @rtype: [L{Element},..]
        """
        ancestors = []
        p = self.parent
        while p is not None:
            ancestors.append(p)
            p = p.parent
        return ancestors
    
    def walk(self, visitor):
        """
        Walk the branch and call the visitor function
        on each node.
        @param visitor: A function.
        @return: self
        @rtype: L{Element}
        """
        visitor(self)
        for c in self.children:
            c.walk(visitor)
        return self
    
    def prune(self):
        """
        Prune the branch of empty nodes.
        """
        pruned = []
        for c in self.children:
            c.prune()
            if c.isempty(False):
                pruned.append(c)
        for p in pruned:
            self.children.remove(p)
                
            
    def __childrenAtPath(self, parts):
        result = []
        node = self
        last = len(parts)-1
        ancestors = parts[:last]
        leaf = parts[last]
        for name in ancestors:
            ns = None
            prefix, name = splitPrefix(name)
            if prefix is not None:
                ns = node.resolvePrefix(prefix)
            child = node.getChild(name, ns)
            if child is None:
                break
            else:
                node = child
        if child is not None:
            ns = None
            prefix, leaf = splitPrefix(leaf)
            if prefix is not None:
                ns = node.resolvePrefix(prefix)
            result = child.getChildren(leaf)
        return result
    
    def __len__(self):
        return len(self.children)
                
    def __getitem__(self, index):
        if isinstance(index, basestring):
            return self.get(index)
        else:
            if index < len(self.children):
                return self.children[index]
            else:
                return None
        
    def __setitem__(self, index, value):
        if isinstance(index, basestring):
            self.set(index, value)
        else:
            if index < len(self.children) and \
                isinstance(value, Element):
                self.children.insert(index, value)

    def __eq__(self, rhs):
        return  rhs is not None and \
            isinstance(rhs, Element) and \
            self.name == rhs.name and \
            self.namespace()[1] == rhs.namespace()[1]
        
    def __repr__(self):
        return \
            'Element (prefix=%s, name=%s)' % (self.prefix, self.name)
    
    def __str__(self):
        return unicode(self).encode('utf-8')
    
    def __unicode__(self):
        return self.str()
    
    def __iter__(self):
        return NodeIterator(self)
    

class NodeIterator:
    """
    The L{Element} child node iterator.
    @ivar pos: The current position
    @type pos: int
    @ivar children: A list of a child nodes.
    @type children: [L{Element},..] 
    """
    
    def __init__(self, parent):
        """
        @param parent: An element to iterate.
        @type parent: L{Element}
        """
        self.pos = 0
        self.children = parent.children
        
    def next(self):
        """
        Get the next child.
        @return: The next child.
        @rtype: L{Element}
        @raise StopIterator: At the end.
        """
        try:
            child = self.children[self.pos]
            self.pos += 1
            return child
        except:
            raise StopIteration()


class PrefixNormalizer:
    """
    The prefix normalizer provides namespace prefix normalization.
    @ivar node: A node to normalize.
    @type node: L{Element}
    @ivar branch: The nodes flattened branch.
    @type branch: [L{Element},..]
    @ivar namespaces: A unique list of namespaces (URI).
    @type namespaces: [str,]
    @ivar prefixes: A reverse dict of prefixes.
    @type prefixes: {u, p}
    """
    
    @classmethod
    def apply(cls, node):
        """
        Normalize the specified node.
        @param node: A node to normalize.
        @type node: L{Element}
        @return: The normalized node.
        @rtype: L{Element}
        """
        pn = PrefixNormalizer(node)
        return pn.refit()
    
    def __init__(self, node):
        """
        @param node: A node to normalize.
        @type node: L{Element}
        """
        self.node = node
        self.branch = node.branch()
        self.namespaces = self.getNamespaces()
        self.prefixes = self.genPrefixes()
        
    def getNamespaces(self):
        """
        Get the I{unique} set of namespaces referenced in the branch.
        @return: A set of namespaces.
        @rtype: set
        """
        s = set()
        for n in self.branch + self.node.ancestors():
            if self.permit(n.expns):
                s.add(n.expns)
            s = s.union(self.pset(n))
        return s
    
    def pset(self, n):
        """
        Convert the nodes nsprefixes into a set.
        @param n: A node.
        @type n: L{Element}
        @return: A set of namespaces.
        @rtype: set
        """
        s = set()
        for ns in n.nsprefixes.items():
            if self.permit(ns):
                s.add(ns[1])
        return s
            
    def genPrefixes(self):
        """
        Generate a I{reverse} mapping of unique prefixes for all namespaces.
        @return: A referse dict of prefixes.
        @rtype: {u, p}
        """
        prefixes = {}
        n = 0
        for u in self.namespaces:
            p = 'ns%d' % n
            prefixes[u] = p
            n += 1
        return prefixes
    
    def refit(self):
        """
        Refit (normalize) the prefixes in the node.
        """
        self.refitNodes()
        self.refitMappings()
    
    def refitNodes(self):
        """
        Refit (normalize) all of the nodes in the branch.
        """
        for n in self.branch:
            if n.prefix is not None:
                ns = n.namespace()
                if self.permit(ns):
                    n.prefix = self.prefixes[ns[1]]
            self.refitAttrs(n)
                
    def refitAttrs(self, n):
        """
        Refit (normalize) all of the attributes in the node.
        @param n: A node.
        @type n: L{Element}
        """
        for a in n.attributes:
            self.refitAddr(a)
    
    def refitAddr(self, a):
        """
        Refit (normalize) the attribute.
        @param a: An attribute.
        @type a: L{Attribute}
        """
        if a.prefix is not None:
            ns = a.namespace()
            if self.permit(ns):
                a.prefix = self.prefixes[ns[1]]
        self.refitValue(a)
    
    def refitValue(self, a):
        """
        Refit (normalize) the attribute's value.
        @param a: An attribute.
        @type a: L{Attribute}
        """
        p,name = splitPrefix(a.getValue())
        if p is None: return
        ns = a.resolvePrefix(p)
        if self.permit(ns):
            u = ns[1]
            p = self.prefixes[u]
            a.setValue(':'.join((p, name)))
            
    def refitMappings(self):
        """
        Refit (normalize) all of the nsprefix mappings.
        """
        for n in self.branch:
            n.nsprefixes = {}
        n = self.node
        for u, p in self.prefixes.items():
            n.addPrefix(p, u)
            
    def permit(self, ns):
        """
        Get whether the I{ns} is to be normalized.
        @param ns: A namespace.
        @type ns: (p,u)
        @return: True if to be included.
        @rtype: boolean
        """
        return not self.skip(ns)
            
    def skip(self, ns):
        """
        Get whether the I{ns} is to B{not} be normalized.
        @param ns: A namespace.
        @type ns: (p,u)
        @return: True if to be skipped.
        @rtype: boolean
        """
        return ns is None or \
            ( ns == Namespace.default ) or \
            ( ns == Namespace.xsdns ) or \
            ( ns == Namespace.xsins) or \
            ( ns == Namespace.xmlns )
########NEW FILE########
__FILENAME__ = enc
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides XML I{special character} encoder classes.
"""

import re

class Encoder:
    """
    An XML special character encoder/decoder.
    @cvar encodings: A mapping of special characters encoding.
    @type encodings: [(str,str)]
    @cvar decodings: A mapping of special characters decoding.
    @type decodings: [(str,str)]
    @cvar special: A list of special characters
    @type special: [char]
    """
    
    encodings = \
        (( '&(?!(amp|lt|gt|quot|apos);)', '&amp;' ),( '<', '&lt;' ),( '>', '&gt;' ),( '"', '&quot;' ),("'", '&apos;' ))
    decodings = \
        (( '&lt;', '<' ),( '&gt;', '>' ),( '&quot;', '"' ),( '&apos;', "'" ),( '&amp;', '&' ))
    special = \
        ('&', '<', '>', '"', "'")
    
    def needsEncoding(self, s):
        """
        Get whether string I{s} contains special characters.
        @param s: A string to check.
        @type s: str
        @return: True if needs encoding.
        @rtype: boolean
        """
        if isinstance(s, basestring):
            for c in self.special:
                if c in s:
                    return True
        return False
    
    def encode(self, s):
        """
        Encode special characters found in string I{s}.
        @param s: A string to encode.
        @type s: str
        @return: The encoded string.
        @rtype: str
        """
        if isinstance(s, basestring) and self.needsEncoding(s):
            for x in self.encodings:
                s = re.sub(x[0], x[1], s)
        return s
    
    def decode(self, s):
        """
        Decode special characters encodings found in string I{s}.
        @param s: A string to decode.
        @type s: str
        @return: The decoded string.
        @rtype: str
        """
        if isinstance(s, basestring) and '&' in s:
            for x in self.decodings:
                s = s.replace(x[0], x[1])
        return s

########NEW FILE########
__FILENAME__ = parser
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The sax module contains a collection of classes that provide a
(D)ocument (O)bject (M)odel representation of an XML document.
The goal is to provide an easy, intuative interface for managing XML
documents.  Although, the term, DOM, is used above, this model is
B{far} better.

XML namespaces in suds are represented using a (2) element tuple
containing the prefix and the URI.  Eg: I{('tns', 'http://myns')}

"""

from logging import getLogger
import suds.metrics
from suds import *
from suds.sax import *
from suds.sax.document import Document
from suds.sax.element import Element
from suds.sax.text import Text
from suds.sax.attribute import Attribute
from xml.sax import make_parser, InputSource, ContentHandler
from xml.sax.handler import feature_external_ges
from cStringIO import StringIO

log = getLogger(__name__)


class Handler(ContentHandler):
    """ sax hanlder """

    def __init__(self):
        self.nodes = [Document()]

    def startElement(self, name, attrs):
        top = self.top()
        node = Element(unicode(name), parent=top)
        for a in attrs.getNames():
            n = unicode(a)
            v = unicode(attrs.getValue(a))
            attribute = Attribute(n,v)
            if self.mapPrefix(node, attribute):
                continue
            node.append(attribute)
        node.charbuffer = []
        top.append(node)
        self.push(node)

    def mapPrefix(self, node, attribute):
        skip = False
        if attribute.name == 'xmlns':
            if len(attribute.value):
                node.expns = unicode(attribute.value)
            skip = True
        elif attribute.prefix == 'xmlns':
            prefix = attribute.name
            node.nsprefixes[prefix] = unicode(attribute.value)
            skip = True
        return skip

    def endElement(self, name):
        name = unicode(name)
        current = self.top()
        if len(current.charbuffer):
            current.text = Text(u''.join(current.charbuffer))
        del current.charbuffer
        if len(current):
            current.trim()
        currentqname = current.qname()
        if name == currentqname:
            self.pop()
        else:
            raise Exception('malformed document')

    def characters(self, content):
        text = unicode(content)
        node = self.top()
        node.charbuffer.append(text)

    def push(self, node):
        self.nodes.append(node)
        return node

    def pop(self):
        return self.nodes.pop()

    def top(self):
        return self.nodes[len(self.nodes)-1]


class Parser:
    """ SAX Parser """

    @classmethod
    def saxparser(cls):
        p = make_parser()
        p.setFeature(feature_external_ges, 0)
        h = Handler()
        p.setContentHandler(h)
        return (p, h)

    def parse(self, file=None, string=None):
        """
        SAX parse XML text.
        @param file: Parse a python I{file-like} object.
        @type file: I{file-like} object.
        @param string: Parse string XML.
        @type string: str
        """
        timer = metrics.Timer()
        timer.start()
        sax, handler = self.saxparser()
        if file is not None:
            sax.parse(file)
            timer.stop()
            #metrics.log.debug('sax (%s) duration: %s', file, timer)
            return handler.nodes[0]
        if string is not None:
            source = InputSource(None)
            source.setByteStream(StringIO(string))
            sax.parse(source)
            timer.stop()
            #metrics.log.debug('%s\nsax duration: %s', string, timer)
            return handler.nodes[0]

########NEW FILE########
__FILENAME__ = text
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Contains XML text classes.
"""

from suds import *
from suds.sax import *


class Text(unicode):
    """
    An XML text object used to represent text content.
    @ivar lang: The (optional) language flag.
    @type lang: bool
    @ivar escaped: The (optional) XML special character escaped flag.
    @type escaped: bool
    """
    __slots__ = ('lang', 'escaped',)
    
    @classmethod
    def __valid(cls, *args):
        return ( len(args) and args[0] is not None )
    
    def __new__(cls, *args, **kwargs):
        if cls.__valid(*args):
            lang = kwargs.pop('lang', None)
            escaped = kwargs.pop('escaped', False)
            result = super(Text, cls).__new__(cls, *args, **kwargs)
            result.lang = lang
            result.escaped = escaped
        else:
            result = None
        return result
    
    def escape(self):
        """
        Encode (escape) special XML characters.
        @return: The text with XML special characters escaped.
        @rtype: L{Text}
        """
        if not self.escaped:
            post = sax.encoder.encode(self)
            escaped = ( post != self )
            return Text(post, lang=self.lang, escaped=escaped)
        return self
    
    def unescape(self):
        """
        Decode (unescape) special XML characters.
        @return: The text with escaped XML special characters decoded.
        @rtype: L{Text}
        """
        if self.escaped:
            post = sax.encoder.decode(self)
            return Text(post, lang=self.lang)
        return self
    
    def trim(self):
        post = self.strip()
        return Text(post, lang=self.lang, escaped=self.escaped)
    
    def __add__(self, other):
        joined = u''.join((self, other))
        result = Text(joined, lang=self.lang, escaped=self.escaped)
        if isinstance(other, Text):
            result.escaped = ( self.escaped or other.escaped )
        return result
    
    def __repr__(self):
        s = [self]
        if self.lang is not None:
            s.append(' [%s]' % self.lang)
        if self.escaped:
            s.append(' <escaped>')
        return ''.join(s)
    
    def __getstate__(self):
        state = {}
        for k in self.__slots__:
            state[k] = getattr(self, k)
        return state
    
    def __setstate__(self, state):
        for k in self.__slots__:
            setattr(self, k, state[k])
    
    
class Raw(Text):
    """
    Raw text which is not XML escaped.
    This may include I{string} XML.
    """
    def escape(self):
        return self
    
    def unescape(self):
        return self
    
    def __add__(self, other):
        joined = u''.join((self, other))
        return Raw(joined, lang=self.lang)

########NEW FILE########
__FILENAME__ = servicedefinition
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The I{service definition} provides a textual representation of a service.
"""

from logging import getLogger
from suds import *
import suds.metrics as metrics
from suds.sax import Namespace

log = getLogger(__name__)

class ServiceDefinition:
    """
    A service definition provides an object used to generate a textual description
    of a service.
    @ivar wsdl: A wsdl.
    @type wsdl: L{wsdl.Definitions}
    @ivar service: The service object.
    @type service: L{suds.wsdl.Service}
    @ivar ports: A list of port-tuple: (port, [(method-name, pdef)])
    @type ports: [port-tuple,..]
    @ivar prefixes: A list of remapped prefixes.
    @type prefixes: [(prefix,uri),..]
    @ivar types: A list of type definitions
    @type types: [I{Type},..]
    """

    def __init__(self, wsdl, service):
        """
        @param wsdl: A wsdl object
        @type wsdl: L{Definitions}
        @param service: A service B{name}.
        @type service: str
        """
        self.wsdl = wsdl
        self.service = service
        self.ports = []
        self.params = []
        self.types = []
        self.prefixes = []
        self.addports()
        self.paramtypes()
        self.publictypes()
        self.getprefixes()
        self.pushprefixes()

    def pushprefixes(self):
        """
        Add our prefixes to the wsdl so that when users invoke methods
        and reference the prefixes, the will resolve properly.
        """
        for ns in self.prefixes:
            self.wsdl.root.addPrefix(ns[0], ns[1])

    def addports(self):
        """
        Look through the list of service ports and construct a list of tuples where
        each tuple is used to describe a port and it's list of methods as:
        (port, [method]).  Each method is tuple: (name, [pdef,..] where each pdef is
        a tuple: (param-name, type).
        """
        timer = metrics.Timer()
        timer.start()
        for port in self.service.ports:
            p = self.findport(port)
            for op in port.binding.operations.values():
                m = p[0].method(op.name)
                binding = m.binding.input
                method = (m.name, binding.param_defs(m))
                p[1].append(method)
                #metrics.log.debug("method '%s' created: %s", m.name, timer)
            p[1].sort()
        timer.stop()

    def findport(self, port):
        """
        Find and return a port tuple for the specified port.
        Created and added when not found.
        @param port: A port.
        @type port: I{service.Port}
        @return: A port tuple.
        @rtype: (port, [method])
        """
        for p in self.ports:
            if p[0] == p: return p
        p = (port, [])
        self.ports.append(p)
        return p

    def getprefixes(self):
        """
        Add prefixes foreach namespace referenced by parameter types.
        """
        namespaces = []
        for l in (self.params, self.types):
            for t,r in l:
                ns = r.namespace()
                if ns[1] is None: continue
                if ns[1] in namespaces: continue
                if Namespace.xs(ns) or Namespace.xsd(ns):
                    continue
                namespaces.append(ns[1])
                if t == r: continue
                ns = t.namespace()
                if ns[1] is None: continue
                if ns[1] in namespaces: continue
                namespaces.append(ns[1])
        i = 0
        namespaces.sort()
        for u in namespaces:
            p = self.nextprefix()
            ns = (p, u)
            self.prefixes.append(ns)

    def paramtypes(self):
        """ get all parameter types """
        for m in [p[1] for p in self.ports]:
            for p in [p[1] for p in m]:
                for pd in p:
                    if pd[1] in self.params: continue
                    item = (pd[1], pd[1].resolve())
                    self.params.append(item)

    def publictypes(self):
        """ get all public types """
        for t in self.wsdl.schema.types.values():
            if t in self.params: continue
            if t in self.types: continue
            item = (t, t)
            self.types.append(item)
        tc = lambda x,y: cmp(x[0].name, y[0].name)
        self.types.sort(cmp=tc)

    def nextprefix(self):
        """
        Get the next available prefix.  This means a prefix starting with 'ns' with
        a number appended as (ns0, ns1, ..) that is not already defined on the
        wsdl document.
        """
        used = [ns[0] for ns in self.prefixes]
        used += [ns[0] for ns in self.wsdl.root.nsprefixes.items()]
        for n in range(0,1024):
            p = 'ns%d'%n
            if p not in used:
                return p
        raise Exception('prefixes exhausted')

    def getprefix(self, u):
        """
        Get the prefix for the specified namespace (uri)
        @param u: A namespace uri.
        @type u: str
        @return: The namspace.
        @rtype: (prefix, uri).
        """
        for ns in Namespace.all:
            if u == ns[1]: return ns[0]
        for ns in self.prefixes:
            if u == ns[1]: return ns[0]
        raise Exception('ns (%s) not mapped'  % u)

    def xlate(self, type):
        """
        Get a (namespace) translated I{qualified} name for specified type.
        @param type: A schema type.
        @type type: I{suds.xsd.sxbasic.SchemaObject}
        @return: A translated I{qualified} name.
        @rtype: str
        """
        resolved = type.resolve()
        name = resolved.name
        if type.unbounded():
            name += '[]'
        ns = resolved.namespace()
        if ns[1] == self.wsdl.tns[1]:
            return name
        prefix = self.getprefix(ns[1])
        return ':'.join((prefix, name))

    def description(self):
        """
        Get a textual description of the service for which this object represents.
        @return: A textual description.
        @rtype: str
        """
        s = []
        indent = (lambda n :  '\n%*s'%(n*3,' '))
        s.append('Service ( %s ) tns="%s"' % (self.service.name, self.wsdl.tns[1]))
        s.append(indent(1))
        s.append('Prefixes (%d)' % len(self.prefixes))
        for p in self.prefixes:
            s.append(indent(2))
            s.append('%s = "%s"' % p)
        s.append(indent(1))
        s.append('Ports (%d):' % len(self.ports))
        for p in self.ports:
            s.append(indent(2))
            s.append('(%s)' % p[0].name)
            s.append(indent(3))
            s.append('Methods (%d):' % len(p[1]))
            for m in p[1]:
                sig = []
                s.append(indent(4))
                sig.append(m[0])
                sig.append('(')
                for p in m[1]:
                    sig.append(self.xlate(p[1]))
                    sig.append(' ')
                    sig.append(p[0])
                    sig.append(', ')
                sig.append(')')
                try:
                    s.append(''.join(sig))
                except:
                    pass
            s.append(indent(3))
            s.append('Types (%d):' % len(self.types))
            for t in self.types:
                s.append(indent(4))
                s.append(self.xlate(t[0]))
        s.append('\n\n')
        return ''.join(s)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        try:
            return self.description()
        except Exception, e:
            log.exception(e)
        return tostr(e)

########NEW FILE########
__FILENAME__ = serviceproxy
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The service proxy provides access to web services.

Replaced by: L{client.Client}
"""

from logging import getLogger
from suds import *
from suds.client import Client

log = getLogger(__name__)


class ServiceProxy(object):
    
    """ 
    A lightweight soap based web service proxy.
    @ivar __client__: A client.  
        Everything is delegated to the 2nd generation API.
    @type __client__: L{Client}
    @note:  Deprecated, replaced by L{Client}.
    """

    def __init__(self, url, **kwargs):
        """
        @param url: The URL for the WSDL.
        @type url: str
        @param kwargs: keyword arguments.
        @keyword faults: Raise faults raised by server (default:True),
                else return tuple from service method invocation as (http code, object).
        @type faults: boolean
        @keyword proxy: An http proxy to be specified on requests (default:{}).
                           The proxy is defined as {protocol:proxy,}
        @type proxy: dict
        """
        client = Client(url, **kwargs)
        self.__client__ = client
    
    def get_instance(self, name):
        """
        Get an instance of a WSDL type by name
        @param name: The name of a type defined in the WSDL.
        @type name: str
        @return: An instance on success, else None
        @rtype: L{sudsobject.Object}
        """
        return self.__client__.factory.create(name)
    
    def get_enum(self, name):
        """
        Get an instance of an enumeration defined in the WSDL by name.
        @param name: The name of a enumeration defined in the WSDL.
        @type name: str
        @return: An instance on success, else None
        @rtype: L{sudsobject.Object}
        """
        return self.__client__.factory.create(name)
 
    def __str__(self):
        return str(self.__client__)
        
    def __unicode__(self):
        return unicode(self.__client__)
    
    def __getattr__(self, name):
        builtin =  name.startswith('__') and name.endswith('__')
        if builtin:
            return self.__dict__[name]
        else:
            return getattr(self.__client__.service, name)
########NEW FILE########
__FILENAME__ = soaparray
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The I{soaparray} module provides XSD extensions for handling
soap (section 5) encoded arrays.
"""

from suds import *
from logging import getLogger
from suds.xsd.sxbasic import Factory as SXFactory
from suds.xsd.sxbasic import Attribute as SXAttribute


class Attribute(SXAttribute):
    """
    Represents an XSD <attribute/> that handles special
    attributes that are extensions for WSDLs.
    @ivar aty: Array type information.
    @type aty: The value of wsdl:arrayType.
    """

    def __init__(self, schema, root, aty):
        """
        @param aty: Array type information.
        @type aty: The value of wsdl:arrayType.
        """
        SXAttribute.__init__(self, schema, root)
        if aty.endswith('[]'):
            self.aty = aty[:-2]
        else:
            self.aty = aty
        
    def autoqualified(self):
        aqs = SXAttribute.autoqualified(self)
        aqs.append('aty')
        return aqs
    
    def description(self):
        d = SXAttribute.description(self)
        d = d+('aty',)
        return d

#
# Builder function, only builds Attribute when arrayType
# attribute is defined on root.
#
def __fn(x, y):
    ns = (None, "http://schemas.xmlsoap.org/wsdl/")
    aty = y.get('arrayType', ns=ns)
    if aty is None:
        return SXAttribute(x, y)
    else:
        return Attribute(x, y, aty)

#
# Remap <xs:attrbute/> tags to __fn() builder.
#
SXFactory.maptag('attribute', __fn)
########NEW FILE########
__FILENAME__ = store
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Contains XML text for documents to be distributed
with the suds lib.  Also, contains classes for accessing
these documents.
"""

from StringIO import StringIO
from logging import getLogger

log = getLogger(__name__)


#
# Soap section 5 encoding schema.
#
encoding = \
"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:tns="http://schemas.xmlsoap.org/soap/encoding/" targetNamespace="http://schemas.xmlsoap.org/soap/encoding/">
        
 <xs:attribute name="root">
   <xs:annotation>
     <xs:documentation>
       'root' can be used to distinguish serialization roots from other
       elements that are present in a serialization but are not roots of
       a serialized value graph 
     </xs:documentation>
   </xs:annotation>
   <xs:simpleType>
     <xs:restriction base="xs:boolean">
       <xs:pattern value="0|1"/>
     </xs:restriction>
   </xs:simpleType>
 </xs:attribute>

  <xs:attributeGroup name="commonAttributes">
    <xs:annotation>
      <xs:documentation>
        Attributes common to all elements that function as accessors or 
        represent independent (multi-ref) values.  The href attribute is
        intended to be used in a manner like CONREF.  That is, the element
        content should be empty iff the href attribute appears
      </xs:documentation>
    </xs:annotation>
    <xs:attribute name="id" type="xs:ID"/>
    <xs:attribute name="href" type="xs:anyURI"/>
    <xs:anyAttribute namespace="##other" processContents="lax"/>
  </xs:attributeGroup>

  <!-- Global Attributes.  The following attributes are intended to be usable via qualified attribute names on any complex type referencing them. -->
       
  <!-- Array attributes. Needed to give the type and dimensions of an array's contents, and the offset for partially-transmitted arrays. -->
   
  <xs:simpleType name="arrayCoordinate">
    <xs:restriction base="xs:string"/>
  </xs:simpleType>
          
  <xs:attribute name="arrayType" type="xs:string"/>
  <xs:attribute name="offset" type="tns:arrayCoordinate"/>
  
  <xs:attributeGroup name="arrayAttributes">
    <xs:attribute ref="tns:arrayType"/>
    <xs:attribute ref="tns:offset"/>
  </xs:attributeGroup>    
  
  <xs:attribute name="position" type="tns:arrayCoordinate"/> 
  
  <xs:attributeGroup name="arrayMemberAttributes">
    <xs:attribute ref="tns:position"/>
  </xs:attributeGroup>    

  <xs:group name="Array">
    <xs:sequence>
      <xs:any namespace="##any" minOccurs="0" maxOccurs="unbounded" processContents="lax"/>
    </xs:sequence>
  </xs:group>

  <xs:element name="Array" type="tns:Array"/>
  <xs:complexType name="Array">
    <xs:annotation>
      <xs:documentation>
       'Array' is a complex type for accessors identified by position 
      </xs:documentation>
    </xs:annotation>
    <xs:group ref="tns:Array" minOccurs="0"/>
    <xs:attributeGroup ref="tns:arrayAttributes"/>
    <xs:attributeGroup ref="tns:commonAttributes"/>
  </xs:complexType> 

  <!-- 'Struct' is a complex type for accessors identified by name. 
       Constraint: No element may be have the same name as any other,
       nor may any element have a maxOccurs > 1. -->
   
  <xs:element name="Struct" type="tns:Struct"/>

  <xs:group name="Struct">
    <xs:sequence>
      <xs:any namespace="##any" minOccurs="0" maxOccurs="unbounded" processContents="lax"/>
    </xs:sequence>
  </xs:group>

  <xs:complexType name="Struct">
    <xs:group ref="tns:Struct" minOccurs="0"/>
    <xs:attributeGroup ref="tns:commonAttributes"/>
  </xs:complexType> 

  <!-- 'Base64' can be used to serialize binary data using base64 encoding
       as defined in RFC2045 but without the MIME line length limitation. -->

  <xs:simpleType name="base64">
    <xs:restriction base="xs:base64Binary"/>
  </xs:simpleType>

 <!-- Element declarations corresponding to each of the simple types in the 
      XML Schemas Specification. -->

  <xs:element name="duration" type="tns:duration"/>
  <xs:complexType name="duration">
    <xs:simpleContent>
      <xs:extension base="xs:duration">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="dateTime" type="tns:dateTime"/>
  <xs:complexType name="dateTime">
    <xs:simpleContent>
      <xs:extension base="xs:dateTime">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>



  <xs:element name="NOTATION" type="tns:NOTATION"/>
  <xs:complexType name="NOTATION">
    <xs:simpleContent>
      <xs:extension base="xs:QName">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>
  

  <xs:element name="time" type="tns:time"/>
  <xs:complexType name="time">
    <xs:simpleContent>
      <xs:extension base="xs:time">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="date" type="tns:date"/>
  <xs:complexType name="date">
    <xs:simpleContent>
      <xs:extension base="xs:date">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="gYearMonth" type="tns:gYearMonth"/>
  <xs:complexType name="gYearMonth">
    <xs:simpleContent>
      <xs:extension base="xs:gYearMonth">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="gYear" type="tns:gYear"/>
  <xs:complexType name="gYear">
    <xs:simpleContent>
      <xs:extension base="xs:gYear">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="gMonthDay" type="tns:gMonthDay"/>
  <xs:complexType name="gMonthDay">
    <xs:simpleContent>
      <xs:extension base="xs:gMonthDay">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="gDay" type="tns:gDay"/>
  <xs:complexType name="gDay">
    <xs:simpleContent>
      <xs:extension base="xs:gDay">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="gMonth" type="tns:gMonth"/>
  <xs:complexType name="gMonth">
    <xs:simpleContent>
      <xs:extension base="xs:gMonth">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>
  
  <xs:element name="boolean" type="tns:boolean"/>
  <xs:complexType name="boolean">
    <xs:simpleContent>
      <xs:extension base="xs:boolean">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="base64Binary" type="tns:base64Binary"/>
  <xs:complexType name="base64Binary">
    <xs:simpleContent>
      <xs:extension base="xs:base64Binary">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="hexBinary" type="tns:hexBinary"/>
  <xs:complexType name="hexBinary">
    <xs:simpleContent>
     <xs:extension base="xs:hexBinary">
       <xs:attributeGroup ref="tns:commonAttributes"/>
     </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="float" type="tns:float"/>
  <xs:complexType name="float">
    <xs:simpleContent>
      <xs:extension base="xs:float">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="double" type="tns:double"/>
  <xs:complexType name="double">
    <xs:simpleContent>
      <xs:extension base="xs:double">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="anyURI" type="tns:anyURI"/>
  <xs:complexType name="anyURI">
    <xs:simpleContent>
      <xs:extension base="xs:anyURI">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="QName" type="tns:QName"/>
  <xs:complexType name="QName">
    <xs:simpleContent>
      <xs:extension base="xs:QName">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  
  <xs:element name="string" type="tns:string"/>
  <xs:complexType name="string">
    <xs:simpleContent>
      <xs:extension base="xs:string">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="normalizedString" type="tns:normalizedString"/>
  <xs:complexType name="normalizedString">
    <xs:simpleContent>
      <xs:extension base="xs:normalizedString">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="token" type="tns:token"/>
  <xs:complexType name="token">
    <xs:simpleContent>
      <xs:extension base="xs:token">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="language" type="tns:language"/>
  <xs:complexType name="language">
    <xs:simpleContent>
      <xs:extension base="xs:language">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="Name" type="tns:Name"/>
  <xs:complexType name="Name">
    <xs:simpleContent>
      <xs:extension base="xs:Name">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="NMTOKEN" type="tns:NMTOKEN"/>
  <xs:complexType name="NMTOKEN">
    <xs:simpleContent>
      <xs:extension base="xs:NMTOKEN">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="NCName" type="tns:NCName"/>
  <xs:complexType name="NCName">
    <xs:simpleContent>
      <xs:extension base="xs:NCName">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="NMTOKENS" type="tns:NMTOKENS"/>
  <xs:complexType name="NMTOKENS">
    <xs:simpleContent>
      <xs:extension base="xs:NMTOKENS">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="ID" type="tns:ID"/>
  <xs:complexType name="ID">
    <xs:simpleContent>
      <xs:extension base="xs:ID">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="IDREF" type="tns:IDREF"/>
  <xs:complexType name="IDREF">
    <xs:simpleContent>
      <xs:extension base="xs:IDREF">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="ENTITY" type="tns:ENTITY"/>
  <xs:complexType name="ENTITY">
    <xs:simpleContent>
      <xs:extension base="xs:ENTITY">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="IDREFS" type="tns:IDREFS"/>
  <xs:complexType name="IDREFS">
    <xs:simpleContent>
      <xs:extension base="xs:IDREFS">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="ENTITIES" type="tns:ENTITIES"/>
  <xs:complexType name="ENTITIES">
    <xs:simpleContent>
      <xs:extension base="xs:ENTITIES">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="decimal" type="tns:decimal"/>
  <xs:complexType name="decimal">
    <xs:simpleContent>
      <xs:extension base="xs:decimal">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="integer" type="tns:integer"/>
  <xs:complexType name="integer">
    <xs:simpleContent>
      <xs:extension base="xs:integer">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="nonPositiveInteger" type="tns:nonPositiveInteger"/>
  <xs:complexType name="nonPositiveInteger">
    <xs:simpleContent>
      <xs:extension base="xs:nonPositiveInteger">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="negativeInteger" type="tns:negativeInteger"/>
  <xs:complexType name="negativeInteger">
    <xs:simpleContent>
      <xs:extension base="xs:negativeInteger">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="long" type="tns:long"/>
  <xs:complexType name="long">
    <xs:simpleContent>
      <xs:extension base="xs:long">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="int" type="tns:int"/>
  <xs:complexType name="int">
    <xs:simpleContent>
      <xs:extension base="xs:int">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="short" type="tns:short"/>
  <xs:complexType name="short">
    <xs:simpleContent>
      <xs:extension base="xs:short">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="byte" type="tns:byte"/>
  <xs:complexType name="byte">
    <xs:simpleContent>
      <xs:extension base="xs:byte">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="nonNegativeInteger" type="tns:nonNegativeInteger"/>
  <xs:complexType name="nonNegativeInteger">
    <xs:simpleContent>
      <xs:extension base="xs:nonNegativeInteger">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="unsignedLong" type="tns:unsignedLong"/>
  <xs:complexType name="unsignedLong">
    <xs:simpleContent>
      <xs:extension base="xs:unsignedLong">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="unsignedInt" type="tns:unsignedInt"/>
  <xs:complexType name="unsignedInt">
    <xs:simpleContent>
      <xs:extension base="xs:unsignedInt">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="unsignedShort" type="tns:unsignedShort"/>
  <xs:complexType name="unsignedShort">
    <xs:simpleContent>
      <xs:extension base="xs:unsignedShort">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="unsignedByte" type="tns:unsignedByte"/>
  <xs:complexType name="unsignedByte">
    <xs:simpleContent>
      <xs:extension base="xs:unsignedByte">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="positiveInteger" type="tns:positiveInteger"/>
  <xs:complexType name="positiveInteger">
    <xs:simpleContent>
      <xs:extension base="xs:positiveInteger">
        <xs:attributeGroup ref="tns:commonAttributes"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="anyType"/>
</xs:schema>
"""


class DocumentStore:
    """
    The I{suds} document store provides a local repository
    for xml documnts.
    @cvar protocol: The URL protocol for the store.
    @type protocol: str
    @cvar store: The mapping of URL location to documents.
    @type store: dict
    """
    
    protocol = 'suds'
    
    store = {
        'schemas.xmlsoap.org/soap/encoding/' : encoding
    }
    
    def open(self, url):
        """
        Open a document at the specified url.
        @param url: A document URL.
        @type url: str
        @return: A file pointer to the document.
        @rtype: StringIO
        """
        protocol, location = self.split(url)
        if protocol == self.protocol:
            return self.find(location)
        else:
            return None
        
    def find(self, location):
        """
        Find the specified location in the store.
        @param location: The I{location} part of a URL.
        @type location: str
        @return: An input stream to the document.
        @rtype: StringIO
        """
        try:
            content = self.store[location]
            return StringIO(content)
        except:
            reason = 'location "%s" not in document store' % location
            raise Exception, reason
        
    def split(self, url):
        """
        Split the url into I{protocol} and I{location}
        @param url: A URL.
        @param url: str
        @return: (I{url}, I{location})
        @rtype: tuple
        """
        parts = url.split('://', 1)
        if len(parts) == 2:
            return parts
        else:
            return (None, url)
########NEW FILE########
__FILENAME__ = sudsobject
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The I{sudsobject} module provides a collection of suds objects
that are primarily used for the highly dynamic interactions with
wsdl/xsd defined types.
"""

from logging import getLogger
from suds import *
from new import classobj

log = getLogger(__name__)


def items(sobject):
    """
    Extract the I{items} from a suds object much like the
    items() method works on I{dict}.
    @param sobject: A suds object
    @type sobject: L{Object}
    @return: A list of items contained in I{sobject}.
    @rtype: [(key, value),...]
    """
    for item in sobject:
        yield item


def asdict(sobject):
    """
    Convert a sudsobject into a dictionary.
    @param sobject: A suds object
    @type sobject: L{Object}
    @return: A python dictionary containing the
        items contained in I{sobject}.
    @rtype: dict
    """
    return dict(items(sobject))

def merge(a, b):
    """
    Merge all attributes and metadata from I{a} to I{b}.
    @param a: A I{source} object
    @type a: L{Object}
    @param b: A I{destination} object
    @type b: L{Object}
    """
    for item in a:
        setattr(b, item[0], item[1])
        b.__metadata__ = b.__metadata__
    return b

def footprint(sobject):
    """
    Get the I{virtual footprint} of the object.
    This is really a count of the attributes in the branch with a significant value.
    @param sobject: A suds object.
    @type sobject: L{Object}
    @return: The branch footprint.
    @rtype: int
    """
    n = 0
    for a in sobject.__keylist__:
        v = getattr(sobject, a)
        if v is None: continue
        if isinstance(v, Object):
            n += footprint(v)
            continue
        if hasattr(v, '__len__'):
            if len(v): n += 1
            continue
        n +=1
    return n

    
class Factory:
    
    cache = {}
    
    @classmethod
    def subclass(cls, name, bases, dict={}):
        if not isinstance(bases, tuple):
            bases = (bases,)
        name = name.encode('utf-8')
        key = '.'.join((name, str(bases)))
        subclass = cls.cache.get(key)
        if subclass is None:
            subclass = classobj(name, bases, dict)
            cls.cache[key] = subclass
        return subclass
    
    @classmethod
    def object(cls, classname=None, dict={}):
        if classname is not None:
            subclass = cls.subclass(classname, Object)
            inst = subclass()
        else:
            inst = Object()
        for a in dict.items():
            setattr(inst, a[0], a[1])
        return inst
    
    @classmethod
    def metadata(cls):
        return Metadata()
    
    @classmethod
    def property(cls, name, value=None):
        subclass = cls.subclass(name, Property)
        return subclass(value)


class Object:

    def __init__(self):
        self.__keylist__ = []
        self.__printer__ = Printer()
        self.__metadata__ = Metadata()

    def __setattr__(self, name, value):
        builtin =  name.startswith('__') and name.endswith('__')
        if not builtin and \
            name not in self.__keylist__:
            self.__keylist__.append(name)
        self.__dict__[name] = value
        
    def __delattr__(self, name):
        try:
            del self.__dict__[name]
            builtin =  name.startswith('__') and name.endswith('__')
            if not builtin:
                self.__keylist__.remove(name)
        except:
            cls = self.__class__.__name__
            raise AttributeError, "%s has no attribute '%s'" % (cls, name)

    def __getitem__(self, name):
        if isinstance(name, int):
            name = self.__keylist__[int(name)]
        return getattr(self, name)
    
    def __setitem__(self, name, value):
        setattr(self, name, value)
        
    def __iter__(self):
        return Iter(self)

    def __len__(self):
        return len(self.__keylist__)
    
    def __contains__(self, name):
        return name in self.__keylist__
    
    def __repr__(self):
        return str(self)

    def __str__(self):
        return unicode(self).encode('utf-8')
    
    def __unicode__(self):
        return self.__printer__.tostr(self)


class Iter:

    def __init__(self, sobject):
        self.sobject = sobject
        self.keylist = self.__keylist(sobject)
        self.index = 0

    def next(self):
        keylist = self.keylist
        nkeys = len(self.keylist)
        while self.index < nkeys:
            k = keylist[self.index]
            self.index += 1
            if hasattr(self.sobject, k):
                v = getattr(self.sobject, k)
                return (k, v)
        raise StopIteration()
    
    def __keylist(self, sobject):
        keylist = sobject.__keylist__
        try:
            keyset = set(keylist)
            ordering = sobject.__metadata__.ordering
            ordered = set(ordering)
            if not ordered.issuperset(keyset):
                log.debug(
                    '%s must be superset of %s, ordering ignored',
                    keylist, 
                    ordering)
                raise KeyError()
            return ordering
        except:
            return keylist
        
    def __iter__(self):
        return self


class Metadata(Object):
    def __init__(self):
        self.__keylist__ = []
        self.__printer__ = Printer()


class Facade(Object):
    def __init__(self, name):
        Object.__init__(self)
        md = self.__metadata__
        md.facade = name

       
class Property(Object):

    def __init__(self, value):
        Object.__init__(self)
        self.value = value
        
    def items(self):
        for item in self:
            if item[0] != 'value':
                yield item
        
    def get(self):
        return self.value
    
    def set(self, value):
        self.value = value
        return self


class Printer:
    """ 
    Pretty printing of a Object object.
    """
    
    @classmethod
    def indent(cls, n): return '%*s'%(n*3,' ')

    def tostr(self, object, indent=-2):
        """ get s string representation of object """
        history = []
        return self.process(object, history, indent)
    
    def process(self, object, h, n=0, nl=False):
        """ print object using the specified indent (n) and newline (nl). """
        if object is None:
            return 'None'
        if isinstance(object, Object):
            if len(object) == 0:
                return '<empty>'
            else:
                return self.print_object(object, h, n+2, nl)
        if isinstance(object, dict):
            if len(object) == 0:
                return '<empty>'
            else:
                return self.print_dictionary(object, h, n+2, nl)
        if isinstance(object, (list,tuple)):
            if len(object) == 0:
                return '<empty>'
            else:
                return self.print_collection(object, h, n+2)
        if isinstance(object, basestring):
            return '"%s"' % tostr(object)
        return '%s' % tostr(object)
    
    def print_object(self, d, h, n, nl=False):
        """ print complex using the specified indent (n) and newline (nl). """
        s = []
        cls = d.__class__
        md = d.__metadata__
        if d in h:
            s.append('(')
            s.append(cls.__name__)
            s.append(')')
            s.append('...')
            return ''.join(s)
        h.append(d)
        if nl:
            s.append('\n')
            s.append(self.indent(n))
        if cls != Object:
            s.append('(')
            if isinstance(d, Facade):
                s.append(md.facade)
            else:
                s.append(cls.__name__)
            s.append(')')
        s.append('{')
        for item in d:
            if self.exclude(d, item):
                continue
            item = self.unwrap(d, item)
            s.append('\n')
            s.append(self.indent(n+1))
            if isinstance(item[1], (list,tuple)):            
                s.append(item[0])
                s.append('[]')
            else:
                s.append(item[0])
            s.append(' = ')
            s.append(self.process(item[1], h, n, True))
        s.append('\n')
        s.append(self.indent(n))
        s.append('}')
        h.pop()
        return ''.join(s)
    
    def print_dictionary(self, d, h, n, nl=False):
        """ print complex using the specified indent (n) and newline (nl). """
        if d in h: return '{}...'
        h.append(d)
        s = []
        if nl:
            s.append('\n')
            s.append(self.indent(n))
        s.append('{')
        for item in d.items():
            s.append('\n')
            s.append(self.indent(n+1))
            if isinstance(item[1], (list,tuple)):            
                s.append(tostr(item[0]))
                s.append('[]')
            else:
                s.append(tostr(item[0]))
            s.append(' = ')
            s.append(self.process(item[1], h, n, True))
        s.append('\n')
        s.append(self.indent(n))
        s.append('}')
        h.pop()
        return ''.join(s)

    def print_collection(self, c, h, n):
        """ print collection using the specified indent (n) and newline (nl). """
        if c in h: return '[]...'
        h.append(c)
        s = []
        for item in c:
            s.append('\n')
            s.append(self.indent(n))
            s.append(self.process(item, h, n-2))
            s.append(',')
        h.pop()
        return ''.join(s)
    
    def unwrap(self, d, item):
        """ translate (unwrap) using an optional wrapper function """
        nopt = ( lambda x: x )
        try:
            md = d.__metadata__
            pmd = getattr(md, '__print__', None)
            if pmd is None:
                return item
            wrappers = getattr(pmd, 'wrappers', {})
            fn = wrappers.get(item[0], nopt)
            return (item[0], fn(item[1]))
        except:
            pass
        return item
    
    def exclude(self, d, item):
        """ check metadata for excluded items """
        try:
            md = d.__metadata__
            pmd = getattr(md, '__print__', None)
            if pmd is None:
                return False
            excludes = getattr(pmd, 'excludes', [])
            return ( item[0] in excludes ) 
        except:
            pass
        return False
########NEW FILE########
__FILENAME__ = http
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Contains classes for basic HTTP transport implementations.
"""

import urllib2 as u2
import base64
import socket
from suds.transport import *
from suds.properties import Unskin
from urlparse import urlparse
from cookielib import CookieJar
from logging import getLogger

log = getLogger(__name__)


class HttpTransport(Transport):
    """
    HTTP transport using urllib2.  Provided basic http transport
    that provides for cookies, proxies but no authentication.
    """

    def __init__(self, **kwargs):
        """
        @param kwargs: Keyword arguments.
            - B{proxy} - An http proxy to be specified on requests.
                 The proxy is defined as {protocol:proxy,}
                    - type: I{dict}
                    - default: {}
            - B{timeout} - Set the url open timeout (seconds).
                    - type: I{float}
                    - default: 90
        """
        Transport.__init__(self)
        Unskin(self.options).update(kwargs)
        self.cookiejar = CookieJar()
        self.proxy = {}
        self.urlopener = None

    def open(self, request):
        try:
            url = request.url
            #log.debug('opening (%s)', url)
            u2request = u2.Request(url)
            self.proxy = self.options.proxy
            return self.u2open(u2request)
        except u2.HTTPError, e:
            raise TransportError(str(e), e.code, e.fp)

    def send(self, request):
        result = None
        url = request.url
        msg = request.message
        headers = request.headers
        try:
            u2request = u2.Request(url, msg, headers)
            self.addcookies(u2request)
            self.proxy = self.options.proxy
            request.headers.update(u2request.headers)
            #log.debug('sending:\n%s', request)
            fp = self.u2open(u2request)
            self.getcookies(fp, u2request)
            result = Reply(200, fp.headers.dict, fp.read())
            #log.debug('received:\n%s', result)
        except u2.HTTPError, e:
            if e.code in (202,204):
                result = None
            else:
                raise TransportError(e.msg, e.code, e.fp)
        return result

    def addcookies(self, u2request):
        """
        Add cookies in the cookiejar to the request.
        @param u2request: A urllib2 request.
        @rtype: u2request: urllib2.Requet.
        """
        self.cookiejar.add_cookie_header(u2request)

    def getcookies(self, fp, u2request):
        """
        Add cookies in the request to the cookiejar.
        @param u2request: A urllib2 request.
        @rtype: u2request: urllib2.Requet.
        """
        self.cookiejar.extract_cookies(fp, u2request)

    def u2open(self, u2request):
        """
        Open a connection.
        @param u2request: A urllib2 request.
        @type u2request: urllib2.Requet.
        @return: The opened file-like urllib2 object.
        @rtype: fp
        """
        tm = self.options.timeout
        url = self.u2opener()
        if self.u2ver() < 2.6:
            socket.setdefaulttimeout(tm)
            return url.open(u2request)
        else:
            return url.open(u2request, timeout=tm)

    def u2opener(self):
        """
        Create a urllib opener.
        @return: An opener.
        @rtype: I{OpenerDirector}
        """
        if self.urlopener is None:
            return u2.build_opener(*self.u2handlers())
        else:
            return self.urlopener

    def u2handlers(self):
        """
        Get a collection of urllib handlers.
        @return: A list of handlers to be installed in the opener.
        @rtype: [Handler,...]
        """
        handlers = []
        handlers.append(u2.ProxyHandler(self.proxy))
        return handlers

    def u2ver(self):
        """
        Get the major/minor version of the urllib2 lib.
        @return: The urllib2 version.
        @rtype: float
        """
        try:
            part = u2.__version__.split('.', 1)
            n = float('.'.join(part))
            return n
        except Exception, e:
            log.exception(e)
            return 0

    def __deepcopy__(self, memo={}):
        clone = self.__class__()
        p = Unskin(self.options)
        cp = Unskin(clone.options)
        cp.update(p)
        return clone


class HttpAuthenticated(HttpTransport):
    """
    Provides basic http authentication for servers that don't follow
    the specified challenge / response model.  This implementation
    appends the I{Authorization} http header with base64 encoded
    credentials on every http request.
    """

    def open(self, request):
        self.addcredentials(request)
        return HttpTransport.open(self, request)

    def send(self, request):
        self.addcredentials(request)
        return HttpTransport.send(self, request)

    def addcredentials(self, request):
        credentials = self.credentials()
        if not (None in credentials):
            encoded = base64.encodestring(':'.join(credentials))
            basic = 'Basic %s' % encoded[:-1]
            request.headers['Authorization'] = basic

    def credentials(self):
        return (self.options.username, self.options.password)

########NEW FILE########
__FILENAME__ = https
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Contains classes for basic HTTP (authenticated) transport implementations.
"""

import urllib2 as u2
from suds.transport import *
from suds.transport.http import HttpTransport
from logging import getLogger

log = getLogger(__name__)


class HttpAuthenticated(HttpTransport):
    """
    Provides basic http authentication that follows the RFC-2617 specification.
    As defined by specifications, credentials are provided to the server
    upon request (HTTP/1.0 401 Authorization Required) by the server only.
    @ivar pm: The password manager.
    @ivar handler: The authentication handler.
    """
    
    def __init__(self, **kwargs):
        """
        @param kwargs: Keyword arguments.
            - B{proxy} - An http proxy to be specified on requests.
                 The proxy is defined as {protocol:proxy,}
                    - type: I{dict}
                    - default: {}
            - B{timeout} - Set the url open timeout (seconds).
                    - type: I{float}
                    - default: 90
            - B{username} - The username used for http authentication.
                    - type: I{str}
                    - default: None
            - B{password} - The password used for http authentication.
                    - type: I{str}
                    - default: None
        """
        HttpTransport.__init__(self, **kwargs)
        self.pm = u2.HTTPPasswordMgrWithDefaultRealm()
        
    def open(self, request):
        self.addcredentials(request)
        return  HttpTransport.open(self, request)
    
    def send(self, request):
        self.addcredentials(request)
        return  HttpTransport.send(self, request)
    
    def addcredentials(self, request):
        credentials = self.credentials()
        if not (None in credentials):
            u = credentials[0]
            p = credentials[1]
            self.pm.add_password(None, request.url, u, p)
    
    def credentials(self):
        return (self.options.username, self.options.password)
    
    def u2handlers(self):
            handlers = HttpTransport.u2handlers(self)
            handlers.append(u2.HTTPBasicAuthHandler(self.pm))
            return handlers
    
    
class WindowsHttpAuthenticated(HttpAuthenticated):
    """
    Provides Windows (NTLM) http authentication.
    @ivar pm: The password manager.
    @ivar handler: The authentication handler.
    @author: Christopher Bess
    """
        
    def u2handlers(self):
        # try to import ntlm support  
        try:
            from ntlm import HTTPNtlmAuthHandler
        except ImportError:
            raise Exception("Cannot import python-ntlm module")
        handlers = HttpTransport.u2handlers(self)
        handlers.append(HTTPNtlmAuthHandler.HTTPNtlmAuthHandler(self.pm))
        return handlers

########NEW FILE########
__FILENAME__ = options
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Contains classes for transport options.
"""


from suds.transport import *
from suds.properties import *

   
class Options(Skin):
    """
    Options:
        - B{proxy} - An http proxy to be specified on requests.
             The proxy is defined as {protocol:proxy,}
                - type: I{dict}
                - default: {}
        - B{timeout} - Set the url open timeout (seconds).
                - type: I{float}
                - default: 90
        - B{headers} - Extra HTTP headers.
                - type: I{dict}
                    - I{str} B{http} - The I{http} protocol proxy URL.
                    - I{str} B{https} - The I{https} protocol proxy URL.
                - default: {}
        - B{username} - The username used for http authentication.
                - type: I{str}
                - default: None
        - B{password} - The password used for http authentication.
                - type: I{str}
                - default: None
    """    
    def __init__(self, **kwargs):
        domain = __name__
        definitions = [
            Definition('proxy', dict, {}),
            Definition('timeout', (int,float), 90),
            Definition('headers', dict, {}),
            Definition('username', basestring, None),
            Definition('password', basestring, None),
        ]
        Skin.__init__(self, domain, definitions, kwargs)
########NEW FILE########
__FILENAME__ = attrlist
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides filtered attribute list classes.
"""

from suds import *
from suds.umx import *
from suds.sax import Namespace


class AttrList:
    """
    A filtered attribute list.
    Items are included during iteration if they are in either the (xs) or
    (xml) namespaces.
    @ivar raw: The I{raw} attribute list.
    @type raw: list
    """
    def __init__(self, attributes):
        """
        @param attributes: A list of attributes
        @type attributes: list
        """
        self.raw = attributes
        
    def real(self):
        """
        Get list of I{real} attributes which exclude xs and xml attributes.
        @return: A list of I{real} attributes.
        @rtype: I{generator}
        """
        for a in self.raw:
            if self.skip(a): continue
            yield a
            
    def rlen(self):
        """
        Get the number of I{real} attributes which exclude xs and xml attributes.
        @return: A count of I{real} attributes. 
        @rtype: L{int}
        """
        n = 0
        for a in self.real():
            n += 1
        return n
            
    def lang(self):
        """
        Get list of I{filtered} attributes which exclude xs.
        @return: A list of I{filtered} attributes.
        @rtype: I{generator}
        """
        for a in self.raw:
            if a.qname() == 'xml:lang':
                return a.value
            return None

    def skip(self, attr):
        """
        Get whether to skip (filter-out) the specified attribute.
        @param attr: An attribute.
        @type attr: I{Attribute}
        @return: True if should be skipped.
        @rtype: bool
        """
        ns = attr.namespace()
        skip = (
            Namespace.xmlns[1],
            'http://schemas.xmlsoap.org/soap/encoding/',
            'http://schemas.xmlsoap.org/soap/envelope/',
            'http://www.w3.org/2003/05/soap-envelope',
        )
        return ( Namespace.xs(ns) or ns[1] in skip )

########NEW FILE########
__FILENAME__ = basic
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides basic unmarshaller classes.
"""

from logging import getLogger
from suds import *
from suds.umx import *
from suds.umx.core import Core


class Basic(Core):
    """
    A object builder (unmarshaller).
    """
        
    def process(self, node):
        """
        Process an object graph representation of the xml I{node}.
        @param node: An XML tree.
        @type node: L{sax.element.Element}
        @return: A suds object.
        @rtype: L{Object}
        """
        content = Content(node)
        return Core.process(self, content)
########NEW FILE########
__FILENAME__ = core
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides base classes for XML->object I{unmarshalling}.
"""

from logging import getLogger
from suds import *
from suds.umx import *
from suds.umx.attrlist import AttrList
from suds.sax.text import Text
from suds.sudsobject import Factory, merge


log = getLogger(__name__)

reserved = { 'class':'cls', 'def':'dfn', }

class Core:
    """
    The abstract XML I{node} unmarshaller.  This class provides the
    I{core} unmarshalling functionality.
    """
        
    def process(self, content):
        """
        Process an object graph representation of the xml I{node}.
        @param content: The current content being unmarshalled.
        @type content: L{Content}
        @return: A suds object.
        @rtype: L{Object}
        """
        self.reset()
        return self.append(content)
    
    def append(self, content):
        """
        Process the specified node and convert the XML document into
        a I{suds} L{object}.
        @param content: The current content being unmarshalled.
        @type content: L{Content}
        @return: A I{append-result} tuple as: (L{Object}, I{value})
        @rtype: I{append-result}
        @note: This is not the proper entry point.
        @see: L{process()}
        """
        self.start(content)
        self.append_attributes(content)
        self.append_children(content)
        self.append_text(content)
        self.end(content)
        return self.postprocess(content)
            
    def postprocess(self, content):
        """
        Perform final processing of the resulting data structure as follows:
          - Mixed values (children and text) will have a result of the I{content.node}.
          - Simi-simple values (attributes, no-children and text) will have a result of a
             property object.
          - Simple values (no-attributes, no-children with text nodes) will have a string 
             result equal to the value of the content.node.getText().
        @param content: The current content being unmarshalled.
        @type content: L{Content}
        @return: The post-processed result.
        @rtype: I{any}
        """
        node = content.node
        if len(node.children) and node.hasText():
            return node
        attributes = AttrList(node.attributes)
        if attributes.rlen() and \
            not len(node.children) and \
            node.hasText():
                p = Factory.property(node.name, node.getText())
                return merge(content.data, p)
        if len(content.data):
            return content.data
        lang = attributes.lang()
        if content.node.isnil():
            return None
        if not len(node.children) and content.text is None:
            if self.nillable(content):
                return None
            else:
                return Text('', lang=lang)
        if isinstance(content.text, basestring):
            return Text(content.text, lang=lang)
        else:
            return content.text
    
    def append_attributes(self, content):
        """
        Append attribute nodes into L{Content.data}.
        Attributes in the I{schema} or I{xml} namespaces are skipped.
        @param content: The current content being unmarshalled.
        @type content: L{Content}
        """
        attributes = AttrList(content.node.attributes)
        for attr in attributes.real():
            name = attr.name
            value = attr.value
            self.append_attribute(name, value, content)
            
    def append_attribute(self, name, value, content):
        """
        Append an attribute name/value into L{Content.data}.
        @param name: The attribute name
        @type name: basestring
        @param value: The attribute's value
        @type value: basestring
        @param content: The current content being unmarshalled.
        @type content: L{Content}
        """
        key = name
        key = '_%s' % reserved.get(key, key)
        setattr(content.data, key, value)
            
    def append_children(self, content):
        """
        Append child nodes into L{Content.data}
        @param content: The current content being unmarshalled.
        @type content: L{Content}
        """
        for child in content.node:
            cont = Content(child)
            cval = self.append(cont)
            key = reserved.get(child.name, child.name)
            if key in content.data:
                v = getattr(content.data, key)
                if isinstance(v, list):
                    v.append(cval)
                else:
                    setattr(content.data, key, [v, cval])
                continue
            if self.unbounded(cont):
                if cval is None:
                    setattr(content.data, key, [])
                else:
                    setattr(content.data, key, [cval,])
            else:
                setattr(content.data, key, cval)
    
    def append_text(self, content):
        """
        Append text nodes into L{Content.data}
        @param content: The current content being unmarshalled.
        @type content: L{Content}
        """
        if content.node.hasText():
            content.text = content.node.getText()
        
    def reset(self):
        pass

    def start(self, content):
        """
        Processing on I{node} has started.  Build and return
        the proper object.
        @param content: The current content being unmarshalled.
        @type content: L{Content}
        @return: A subclass of Object.
        @rtype: L{Object}
        """
        content.data = Factory.object(content.node.name)
    
    def end(self, content):
        """
        Processing on I{node} has ended.
        @param content: The current content being unmarshalled.
        @type content: L{Content}
        """
        pass
    
    def bounded(self, content):
        """
        Get whether the content is bounded (not a list).
        @param content: The current content being unmarshalled.
        @type content: L{Content}
        @return: True if bounded, else False
        @rtype: boolean
        '"""
        return ( not self.unbounded(content) )
    
    def unbounded(self, content):
        """
        Get whether the object is unbounded (a list).
        @param content: The current content being unmarshalled.
        @type content: L{Content}
        @return: True if unbounded, else False
        @rtype: boolean
        '"""
        return False
    
    def nillable(self, content):
        """
        Get whether the object is nillable.
        @param content: The current content being unmarshalled.
        @type content: L{Content}
        @return: True if nillable, else False
        @rtype: boolean
        '"""
        return False
########NEW FILE########
__FILENAME__ = encoded
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides soap encoded unmarshaller classes.
"""

from logging import getLogger
from suds import *
from suds.umx import *
from suds.umx.typed import Typed
from suds.sax import splitPrefix, Namespace

log = getLogger(__name__)

#
# Add encoded extensions
# aty = The soap (section 5) encoded array type.
#
Content.extensions.append('aty')


class Encoded(Typed):
    """
    A SOAP section (5) encoding unmarshaller.
    This marshaller supports rpc/encoded soap styles.
    """

    def start(self, content):
        #
        # Grab the array type and continue
        #
        self.setaty(content)
        Typed.start(self, content)
    
    def end(self, content):
        #
        # Squash soap encoded arrays into python lists.  This is
        # also where we insure that empty arrays are represented
        # as empty python lists.
        #
        aty = content.aty
        if aty is not None:
            self.promote(content)
        return Typed.end(self, content)
    
    def postprocess(self, content):
        #
        # Ensure proper rendering of empty arrays.
        #
        if content.aty is None:
            return Typed.postprocess(self, content)
        else:
            return content.data
    
    def setaty(self, content):
        """
        Grab the (aty) soap-enc:arrayType and attach it to the
        content for proper array processing later in end().
        @param content: The current content being unmarshalled.
        @type content: L{Content}
        @return: self
        @rtype: L{Encoded}
        """
        name = 'arrayType'
        ns = (None, 'http://schemas.xmlsoap.org/soap/encoding/')
        aty = content.node.get(name, ns)
        if aty is not None:
            content.aty = aty
            parts = aty.split('[')
            ref = parts[0]
            if len(parts) == 2:
                self.applyaty(content, ref)
            else:
                pass # (2) dimensional array
        return self
    
    def applyaty(self, content, xty):
        """
        Apply the type referenced in the I{arrayType} to the content
        (child nodes) of the array.  Each element (node) in the array 
        that does not have an explicit xsi:type attribute is given one
        based on the I{arrayType}.
        @param content: An array content.
        @type content: L{Content}
        @param xty: The XSI type reference.
        @type xty: str
        @return: self
        @rtype: L{Encoded}
        """
        name = 'type'
        ns = Namespace.xsins
        parent = content.node
        for child in parent.getChildren():
            ref = child.get(name, ns)
            if ref is None:
                parent.addPrefix(ns[0], ns[1])
                attr = ':'.join((ns[0], name))
                child.set(attr, xty)
        return self

    def promote(self, content):
        """
        Promote (replace) the content.data with the first attribute
        of the current content.data that is a I{list}.  Note: the 
        content.data may be empty or contain only _x attributes.
        In either case, the content.data is assigned an empty list.
        @param content: An array content.
        @type content: L{Content}
        """
        for n,v in content.data:
            if isinstance(v, list):
                content.data = v
                return
        content.data = []
########NEW FILE########
__FILENAME__ = typed
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
Provides typed unmarshaller classes.
"""

from logging import getLogger
from suds import *
from suds.umx import *
from suds.umx.core import Core
from suds.resolver import NodeResolver, Frame
from suds.sudsobject import Factory

log = getLogger(__name__)


#
# Add typed extensions
# type = The expected xsd type
# real = The 'true' XSD type
#
Content.extensions.append('type')
Content.extensions.append('real')


class Typed(Core):
    """
    A I{typed} XML unmarshaller
    @ivar resolver: A schema type resolver.
    @type resolver: L{NodeResolver}
    """

    def __init__(self, schema):
        """
        @param schema: A schema object.
        @type schema: L{xsd.schema.Schema}
        """
        self.resolver = NodeResolver(schema)

    def process(self, node, type):
        """
        Process an object graph representation of the xml L{node}.
        @param node: An XML tree.
        @type node: L{sax.element.Element}
        @param type: The I{optional} schema type.
        @type type: L{xsd.sxbase.SchemaObject}
        @return: A suds object.
        @rtype: L{Object}
        """
        content = Content(node)
        content.type = type
        return Core.process(self, content)

    def reset(self):
        #log.debug('reset')
        self.resolver.reset()

    def start(self, content):
        #
        # Resolve to the schema type; build an object and setup metadata.
        #
        if content.type is None:
            found = self.resolver.find(content.node)
            if found is None:
                log.error(self.resolver.schema)
                raise TypeNotFound(content.node.qname())
            content.type = found
        else:
            known = self.resolver.known(content.node)
            frame = Frame(content.type, resolved=known)
            self.resolver.push(frame)
        real = self.resolver.top().resolved
        content.real = real
        cls_name = real.name
        if cls_name is None:
            cls_name = content.node.name
        content.data = Factory.object(cls_name)
        md = content.data.__metadata__
        md.sxtype = real

    def end(self, content):
        self.resolver.pop()

    def unbounded(self, content):
        return content.type.unbounded()

    def nillable(self, content):
        resolved = content.type.resolve()
        return ( content.type.nillable or \
            (resolved.builtin() and resolved.nillable ) )

    def append_attribute(self, name, value, content):
        """
        Append an attribute name/value into L{Content.data}.
        @param name: The attribute name
        @type name: basestring
        @param value: The attribute's value
        @type value: basestring
        @param content: The current content being unmarshalled.
        @type content: L{Content}
        """
        type = self.resolver.findattr(name)
        if type is None:
            pass#log.warn('attribute (%s) type, not-found', name)
        else:
            value = self.translated(value, type)
        Core.append_attribute(self, name, value, content)

    def append_text(self, content):
        """
        Append text nodes into L{Content.data}
        Here is where the I{true} type is used to translate the value
        into the proper python type.
        @param content: The current content being unmarshalled.
        @type content: L{Content}
        """
        Core.append_text(self, content)
        known = self.resolver.top().resolved
        content.text = self.translated(content.text, known)

    def translated(self, value, type):
        """ translate using the schema type """
        if value is not None:
            resolved = type.resolve()
            return resolved.translate(value)
        else:
            return value

########NEW FILE########
__FILENAME__ = wsdl
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The I{wsdl} module provides an objectification of the WSDL.
The primary class is I{Definitions} as it represends the root element
found in the document.
"""

from logging import getLogger
from suds import *
from suds.sax import splitPrefix
from suds.sax.element import Element
from suds.bindings.document import Document
from suds.bindings.rpc import RPC, Encoded
from suds.xsd import qualify, Namespace
from suds.xsd.schema import Schema, SchemaCollection
from suds.xsd.query import ElementQuery
from suds.sudsobject import Object, Facade, Metadata
from suds.reader import DocumentReader, DefinitionsReader
from urlparse import urljoin
import re, soaparray

log = getLogger(__name__)

wsdlns = (None, "http://schemas.xmlsoap.org/wsdl/")
soapns = (None, 'http://schemas.xmlsoap.org/wsdl/soap/')
soap12ns = (None, 'http://schemas.xmlsoap.org/wsdl/soap12/')


class WObject(Object):
    """
    Base object for wsdl types.
    @ivar root: The XML I{root} element.
    @type root: L{Element}
    """

    def __init__(self, root, definitions=None):
        """
        @param root: An XML root element.
        @type root: L{Element}
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        """
        Object.__init__(self)
        self.root = root
        pmd = Metadata()
        pmd.excludes = ['root']
        pmd.wrappers = dict(qname=repr)
        self.__metadata__.__print__ = pmd

    def resolve(self, definitions):
        """
        Resolve named references to other WSDL objects.
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        """
        pass


class NamedObject(WObject):
    """
    A B{named} WSDL object.
    @ivar name: The name of the object.
    @type name: str
    @ivar qname: The I{qualified} name of the object.
    @type qname: (name, I{namespace-uri}).
    """

    def __init__(self, root, definitions):
        """
        @param root: An XML root element.
        @type root: L{Element}
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        """
        WObject.__init__(self, root, definitions)
        self.name = root.get('name')
        self.qname = (self.name, definitions.tns[1])
        pmd = self.__metadata__.__print__
        pmd.wrappers['qname'] = repr


class Definitions(WObject):
    """
    Represents the I{root} container of the WSDL objects as defined
    by <wsdl:definitions/>
    @ivar id: The object id.
    @type id: str
    @ivar options: An options dictionary.
    @type options: L{options.Options}
    @ivar url: The URL used to load the object.
    @type url: str
    @ivar tns: The target namespace for the WSDL.
    @type tns: str
    @ivar schema: The collective WSDL schema object.
    @type schema: L{SchemaCollection}
    @ivar children: The raw list of child objects.
    @type children: [L{WObject},...]
    @ivar imports: The list of L{Import} children.
    @type imports: [L{Import},...]
    @ivar messages: The dictionary of L{Message} children key'd by I{qname}
    @type messages: [L{Message},...]
    @ivar port_types: The dictionary of L{PortType} children key'd by I{qname}
    @type port_types: [L{PortType},...]
    @ivar bindings: The dictionary of L{Binding} children key'd by I{qname}
    @type bindings: [L{Binding},...]
    @ivar service: The service object.
    @type service: L{Service}
    """

    Tag = 'definitions'

    def __init__(self, url, options):
        """
        @param url: A URL to the WSDL.
        @type url: str
        @param options: An options dictionary.
        @type options: L{options.Options}
        """
        #log.debug('reading wsdl at: %s ...', url)
        reader = DocumentReader(options)
        d = reader.open(url)
        root = d.root()
        WObject.__init__(self, root)
        self.id = objid(self)
        self.options = options
        self.url = url
        self.tns = self.mktns(root)
        self.types = []
        self.schema = None
        self.children = []
        self.imports = []
        self.messages = {}
        self.port_types = {}
        self.bindings = {}
        self.services = []
        self.add_children(self.root)
        self.children.sort()
        pmd = self.__metadata__.__print__
        pmd.excludes.append('children')
        pmd.excludes.append('wsdl')
        pmd.wrappers['schema'] = repr
        self.open_imports()
        self.resolve()
        self.build_schema()
        self.set_wrapped()
        for s in self.services:
            self.add_methods(s)
        #log.debug("wsdl at '%s' loaded:\n%s", url, self)

    def mktns(self, root):
        """ Get/create the target namespace """
        tns = root.get('targetNamespace')
        prefix = root.findPrefix(tns)
        if prefix is None:
            #log.debug('warning: tns (%s), not mapped to prefix', tns)
            prefix = 'tns'
        return (prefix, tns)

    def add_children(self, root):
        """ Add child objects using the factory """
        for c in root.getChildren(ns=wsdlns):
            child = Factory.create(c, self)
            if child is None: continue
            self.children.append(child)
            if isinstance(child, Import):
                self.imports.append(child)
                continue
            if isinstance(child, Types):
                self.types.append(child)
                continue
            if isinstance(child, Message):
                self.messages[child.qname] = child
                continue
            if isinstance(child, PortType):
                self.port_types[child.qname] = child
                continue
            if isinstance(child, Binding):
                self.bindings[child.qname] = child
                continue
            if isinstance(child, Service):
                self.services.append(child)
                continue

    def open_imports(self):
        """ Import the I{imported} WSDLs. """
        for imp in self.imports:
            imp.load(self)

    def resolve(self):
        """ Tell all children to resolve themselves """
        for c in self.children:
            c.resolve(self)

    def build_schema(self):
        """ Process L{Types} objects and create the schema collection """
        container = SchemaCollection(self)
        for t in [t for t in self.types if t.local()]:
            for root in t.contents():
                schema = Schema(root, self.url, self.options, container)
                container.add(schema)
        if not len(container): # empty
            root = Element.buildPath(self.root, 'types/schema')
            schema = Schema(root, self.url, self.options, container)
            container.add(schema)
        self.schema = container.load(self.options)
        for s in [t.schema() for t in self.types if t.imported()]:
            self.schema.merge(s)
        return self.schema

    def add_methods(self, service):
        """ Build method view for service """
        bindings = {
            'document/literal' : Document(self),
            'rpc/literal' : RPC(self),
            'rpc/encoded' : Encoded(self)
        }
        for p in service.ports:
            binding = p.binding
            ptype = p.binding.type
            operations = p.binding.type.operations.values()
            for name in [op.name for op in operations]:
                m = Facade('Method')
                m.name = name
                m.location = p.location
                m.binding = Facade('binding')
                op = binding.operation(name)
                m.soap = op.soap
                key = '/'.join((op.soap.style, op.soap.input.body.use))
                m.binding.input = bindings.get(key)
                key = '/'.join((op.soap.style, op.soap.output.body.use))
                m.binding.output = bindings.get(key)
                op = ptype.operation(name)
                p.methods[name] = m

    def set_wrapped(self):
        """ set (wrapped|bare) flag on messages """
        for b in self.bindings.values():
            for op in b.operations.values():
                for body in (op.soap.input.body, op.soap.output.body):
                    body.wrapped = False
                    if len(body.parts) != 1:
                        continue
                    for p in body.parts:
                        if p.element is None:
                            continue
                        query = ElementQuery(p.element)
                        pt = query.execute(self.schema)
                        if pt is None:
                            raise TypeNotFound(query.ref)
                        resolved = pt.resolve()
                        if resolved.builtin():
                            continue
                        body.wrapped = True

    def __getstate__(self):
        nopickle = ('options',)
        state = self.__dict__.copy()
        for k in nopickle:
            if k in state:
                del state[k]
        return state

    def __repr__(self):
        return 'Definitions (id=%s)' % self.id


class Import(WObject):
    """
    Represents the <wsdl:import/>.
    @ivar location: The value of the I{location} attribute.
    @type location: str
    @ivar ns: The value of the I{namespace} attribute.
    @type ns: str
    @ivar imported: The imported object.
    @type imported: L{Definitions}
    """

    def __init__(self, root, definitions):
        """
        @param root: An XML root element.
        @type root: L{Element}
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        """
        WObject.__init__(self, root, definitions)
        self.location = root.get('location')
        self.ns = root.get('namespace')
        self.imported = None
        pmd = self.__metadata__.__print__
        pmd.wrappers['imported'] = repr

    def load(self, definitions):
        """ Load the object by opening the URL """
        url = self.location
        #log.debug('importing (%s)', url)
        if '://' not in url:
            url = urljoin(definitions.url, url)
        options = definitions.options
        d = Definitions(url, options)
        if d.root.match(Definitions.Tag, wsdlns):
            self.import_definitions(definitions, d)
            return
        if d.root.match(Schema.Tag, Namespace.xsdns):
            self.import_schema(definitions, d)
            return
        raise Exception('document at "%s" is unknown' % url)

    def import_definitions(self, definitions, d):
        """ import/merge wsdl definitions """
        definitions.types += d.types
        definitions.messages.update(d.messages)
        definitions.port_types.update(d.port_types)
        definitions.bindings.update(d.bindings)
        self.imported = d
        #log.debug('imported (WSDL):\n%s', d)

    def import_schema(self, definitions, d):
        """ import schema as <types/> content """
        if not len(definitions.types):
            types = Types.create(definitions)
            definitions.types.append(types)
        else:
            types = definitions.types[-1]
        types.root.append(d.root)
        #log.debug('imported (XSD):\n%s', d.root)

    def __gt__(self, other):
        return False


class Types(WObject):
    """
    Represents <types><schema/></types>.
    """

    @classmethod
    def create(cls, definitions):
        root = Element('types', ns=wsdlns)
        definitions.root.insert(root)
        return Types(root, definitions)

    def __init__(self, root, definitions):
        """
        @param root: An XML root element.
        @type root: L{Element}
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        """
        WObject.__init__(self, root, definitions)
        self.definitions = definitions

    def contents(self):
        return self.root.getChildren('schema', Namespace.xsdns)

    def schema(self):
        return self.definitions.schema

    def local(self):
        return ( self.definitions.schema is None )

    def imported(self):
        return ( not self.local() )

    def __gt__(self, other):
        return isinstance(other, Import)


class Part(NamedObject):
    """
    Represents <message><part/></message>.
    @ivar element: The value of the {element} attribute.
        Stored as a I{qref} as converted by L{suds.xsd.qualify}.
    @type element: str
    @ivar type: The value of the {type} attribute.
        Stored as a I{qref} as converted by L{suds.xsd.qualify}.
    @type type: str
    """

    def __init__(self, root, definitions):
        """
        @param root: An XML root element.
        @type root: L{Element}
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        """
        NamedObject.__init__(self, root, definitions)
        pmd = Metadata()
        pmd.wrappers = dict(element=repr, type=repr)
        self.__metadata__.__print__ = pmd
        tns = definitions.tns
        self.element = self.__getref('element', tns)
        self.type = self.__getref('type', tns)

    def __getref(self, a, tns):
        """ Get the qualified value of attribute named 'a'."""
        s = self.root.get(a)
        if s is None:
            return s
        else:
            return qualify(s, self.root, tns)


class Message(NamedObject):
    """
    Represents <message/>.
    @ivar parts: A list of message parts.
    @type parts: [I{Part},...]
    """

    def __init__(self, root, definitions):
        """
        @param root: An XML root element.
        @type root: L{Element}
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        """
        NamedObject.__init__(self, root, definitions)
        self.parts = []
        for p in root.getChildren('part'):
            part = Part(p, definitions)
            self.parts.append(part)

    def __gt__(self, other):
        return isinstance(other, (Import, Types))


class PortType(NamedObject):
    """
    Represents <portType/>.
    @ivar operations: A list of contained operations.
    @type operations: list
    """

    def __init__(self, root, definitions):
        """
        @param root: An XML root element.
        @type root: L{Element}
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        """
        NamedObject.__init__(self, root, definitions)
        self.operations = {}
        for c in root.getChildren('operation'):
            op = Facade('Operation')
            op.name = c.get('name')
            op.tns = definitions.tns
            input = c.getChild('input')
            if input is None:
                op.input = None
            else:
                op.input = input.get('message')
            output = c.getChild('output')
            if output is None:
                op.output = None
            else:
                op.output = output.get('message')
            faults = []
            for fault in c.getChildren('fault'):
                f = Facade('Fault')
                f.name = fault.get('name')
                f.message = fault.get('message')
                faults.append(f)
            op.faults = faults
            self.operations[op.name] = op

    def resolve(self, definitions):
        """
        Resolve named references to other WSDL objects.
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        """
        for op in self.operations.values():
            if op.input is None:
                op.input = Message(Element('no-input'), definitions)
            else:
                qref = qualify(op.input, self.root, definitions.tns)
                msg = definitions.messages.get(qref)
                if msg is None:
                    raise Exception("msg '%s', not-found" % op.input)
                else:
                    op.input = msg
            if op.output is None:
                op.output = Message(Element('no-output'), definitions)
            else:
                qref = qualify(op.output, self.root, definitions.tns)
                msg = definitions.messages.get(qref)
                if msg is None:
                    raise Exception("msg '%s', not-found" % op.output)
                else:
                    op.output = msg
            for f in op.faults:
                qref = qualify(f.message, self.root, definitions.tns)
                msg = definitions.messages.get(qref)
                if msg is None:
                    raise Exception, "msg '%s', not-found" % f.message
                f.message = msg

    def operation(self, name):
        """
        Shortcut used to get a contained operation by name.
        @param name: An operation name.
        @type name: str
        @return: The named operation.
        @rtype: Operation
        @raise L{MethodNotFound}: When not found.
        """
        try:
            return self.operations[name]
        except Exception, e:
            raise MethodNotFound(name)

    def __gt__(self, other):
        return isinstance(other, (Import, Types, Message))


class Binding(NamedObject):
    """
    Represents <binding/>
    @ivar operations: A list of contained operations.
    @type operations: list
    """

    def __init__(self, root, definitions):
        """
        @param root: An XML root element.
        @type root: L{Element}
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        """
        NamedObject.__init__(self, root, definitions)
        self.operations = {}
        self.type = root.get('type')
        sr = self.soaproot()
        if sr is None:
            self.soap = None
            #log.debug('binding: "%s" not a soap binding', self.name)
            return
        soap = Facade('soap')
        self.soap = soap
        self.soap.style = sr.get('style', default='document')
        self.add_operations(self.root, definitions)

    def soaproot(self):
        """ get the soap:binding """
        for ns in (soapns, soap12ns):
            sr =  self.root.getChild('binding', ns=ns)
            if sr is not None:
                return sr
        return None

    def add_operations(self, root, definitions):
        """ Add <operation/> children """
        dsop = Element('operation', ns=soapns)
        for c in root.getChildren('operation'):
            op = Facade('Operation')
            op.name = c.get('name')
            sop = c.getChild('operation', default=dsop)
            soap = Facade('soap')
            soap.action = '"%s"' % sop.get('soapAction', default='')
            soap.style = sop.get('style', default=self.soap.style)
            soap.input = Facade('Input')
            soap.input.body = Facade('Body')
            soap.input.headers = []
            soap.output = Facade('Output')
            soap.output.body = Facade('Body')
            soap.output.headers = []
            op.soap = soap
            input = c.getChild('input')
            if input is None:
                input = Element('input', ns=wsdlns)
            body = input.getChild('body')
            self.body(definitions, soap.input.body, body)
            for header in input.getChildren('header'):
                self.header(definitions, soap.input, header)
            output = c.getChild('output')
            if output is None:
                output = Element('output', ns=wsdlns)
            body = output.getChild('body')
            self.body(definitions, soap.output.body, body)
            for header in output.getChildren('header'):
                self.header(definitions, soap.output, header)
            faults = []
            for fault in c.getChildren('fault'):
                sf = fault.getChild('fault')
                if sf is None:
                    continue
                fn = fault.get('name')
                f = Facade('Fault')
                f.name = sf.get('name', default=fn)
                f.use = sf.get('use', default='literal')
                faults.append(f)
            soap.faults = faults
            self.operations[op.name] = op

    def body(self, definitions, body, root):
        """ add the input/output body properties """
        if root is None:
            body.use = 'literal'
            body.namespace = definitions.tns
            body.parts = ()
            return
        parts = root.get('parts')
        if parts is None:
            body.parts = ()
        else:
            body.parts = re.split('[\s,]', parts)
        body.use = root.get('use', default='literal')
        ns = root.get('namespace')
        if ns is None:
            body.namespace = definitions.tns
        else:
            prefix = root.findPrefix(ns, 'b0')
            body.namespace = (prefix, ns)

    def header(self, definitions, parent, root):
        """ add the input/output header properties """
        if root is None:
            return
        header = Facade('Header')
        parent.headers.append(header)
        header.use = root.get('use', default='literal')
        ns = root.get('namespace')
        if ns is None:
            header.namespace = definitions.tns
        else:
            prefix = root.findPrefix(ns, 'h0')
            header.namespace = (prefix, ns)
        msg = root.get('message')
        if msg is not None:
            header.message = msg
        part = root.get('part')
        if part is not None:
            header.part = part

    def resolve(self, definitions):
        """
        Resolve named references to other WSDL objects.  This includes
        cross-linking information (from) the portType (to) the I{soap}
        protocol information on the binding for each operation.
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        """
        self.resolveport(definitions)
        for op in self.operations.values():
            self.resolvesoapbody(definitions, op)
            self.resolveheaders(definitions, op)
            self.resolvefaults(definitions, op)

    def resolveport(self, definitions):
        """
        Resolve port_type reference.
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        """
        ref = qualify(self.type, self.root, definitions.tns)
        port_type = definitions.port_types.get(ref)
        if port_type is None:
            raise Exception("portType '%s', not-found" % self.type)
        else:
            self.type = port_type

    def resolvesoapbody(self, definitions, op):
        """
        Resolve soap body I{message} parts by
        cross-referencing with operation defined in port type.
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        @param op: An I{operation} object.
        @type op: I{operation}
        """
        ptop = self.type.operation(op.name)
        if ptop is None:
            raise Exception, \
                "operation '%s' not defined in portType" % op.name
        soap = op.soap
        parts = soap.input.body.parts
        if len(parts):
            pts = []
            for p in ptop.input.parts:
                if p.name in parts:
                    pts.append(p)
            soap.input.body.parts = pts
        else:
            soap.input.body.parts = ptop.input.parts
        parts = soap.output.body.parts
        if len(parts):
            pts = []
            for p in ptop.output.parts:
                if p.name in parts:
                    pts.append(p)
            soap.output.body.parts = pts
        else:
            soap.output.body.parts = ptop.output.parts

    def resolveheaders(self, definitions, op):
        """
        Resolve soap header I{message} references.
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        @param op: An I{operation} object.
        @type op: I{operation}
        """
        soap = op.soap
        headers = soap.input.headers + soap.output.headers
        for header in headers:
            mn = header.message
            ref = qualify(mn, self.root, definitions.tns)
            message = definitions.messages.get(ref)
            if message is None:
                raise Exception, "message'%s', not-found" % mn
            pn = header.part
            for p in message.parts:
                if p.name == pn:
                    header.part = p
                    break
            if pn == header.part:
                raise Exception, \
                    "message '%s' has not part named '%s'" % (ref, pn)

    def resolvefaults(self, definitions, op):
        """
        Resolve soap fault I{message} references by
        cross-referencing with operation defined in port type.
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        @param op: An I{operation} object.
        @type op: I{operation}
        """
        ptop = self.type.operation(op.name)
        if ptop is None:
            raise Exception, \
                "operation '%s' not defined in portType" % op.name
        soap = op.soap
        for fault in soap.faults:
            for f in ptop.faults:
                if f.name == fault.name:
                    fault.parts = f.message.parts
                    continue
            if hasattr(fault, 'parts'):
                continue
            raise Exception, \
                "fault '%s' not defined in portType '%s'" % (fault.name, self.type.name)

    def operation(self, name):
        """
        Shortcut used to get a contained operation by name.
        @param name: An operation name.
        @type name: str
        @return: The named operation.
        @rtype: Operation
        @raise L{MethodNotFound}: When not found.
        """
        try:
            return self.operations[name]
        except:
            raise MethodNotFound(name)

    def __gt__(self, other):
        return ( not isinstance(other, Service) )


class Port(NamedObject):
    """
    Represents a service port.
    @ivar service: A service.
    @type service: L{Service}
    @ivar binding: A binding name.
    @type binding: str
    @ivar location: The service location (url).
    @type location: str
    """

    def __init__(self, root, definitions, service):
        """
        @param root: An XML root element.
        @type root: L{Element}
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        @param service: A service object.
        @type service: L{Service}
        """
        NamedObject.__init__(self, root, definitions)
        self.__service = service
        self.binding = root.get('binding')
        address = root.getChild('address')
        if address is None:
            self.location = None
        else:
            self.location = address.get('location').encode('utf-8')
        self.methods = {}

    def method(self, name):
        """
        Get a method defined in this portType by name.
        @param name: A method name.
        @type name: str
        @return: The requested method object.
        @rtype: I{Method}
        """
        return self.methods.get(name)


class Service(NamedObject):
    """
    Represents <service/>.
    @ivar port: The contained ports.
    @type port: [Port,..]
    @ivar methods: The contained methods for all ports.
    @type methods: [Method,..]
    """

    def __init__(self, root, definitions):
        """
        @param root: An XML root element.
        @type root: L{Element}
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        """
        NamedObject.__init__(self, root, definitions)
        self.ports = []
        for p in root.getChildren('port'):
            port = Port(p, definitions, self)
            self.ports.append(port)

    def port(self, name):
        """
        Locate a port by name.
        @param name: A port name.
        @type name: str
        @return: The port object.
        @rtype: L{Port}
        """
        for p in self.ports:
            if p.name == name:
                return p
        return None

    def setlocation(self, url, names=None):
        """
        Override the invocation location (url) for service method.
        @param url: A url location.
        @type url: A url.
        @param names:  A list of method names.  None=ALL
        @type names: [str,..]
        """
        for p in self.ports:
            for m in p.methods.values():
                if names is None or m.name in names:
                    m.location = url

    def resolve(self, definitions):
        """
        Resolve named references to other WSDL objects.
        Ports without soap bindings are discarded.
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        """
        filtered = []
        for p in self.ports:
            ref = qualify(p.binding, self.root, definitions.tns)
            binding = definitions.bindings.get(ref)
            if binding is None:
                raise Exception("binding '%s', not-found" % p.binding)
            if binding.soap is None:
                #log.debug('binding "%s" - not a soap, discarded', binding.name)
                continue
            p.binding = binding
            filtered.append(p)
        self.ports = filtered

    def __gt__(self, other):
        return True


class Factory:
    """
    Simple WSDL object factory.
    @cvar tags: Dictionary of tag->constructor mappings.
    @type tags: dict
    """

    tags =\
    {
        'import' : Import,
        'types' : Types,
        'message' : Message,
        'portType' : PortType,
        'binding' : Binding,
        'service' : Service,
    }

    @classmethod
    def create(cls, root, definitions):
        """
        Create an object based on the root tag name.
        @param root: An XML root element.
        @type root: L{Element}
        @param definitions: A definitions object.
        @type definitions: L{Definitions}
        @return: The created object.
        @rtype: L{WObject}
        """
        fn = cls.tags.get(root.name)
        if fn is not None:
            return fn(root, definitions)
        else:
            return None

########NEW FILE########
__FILENAME__ = wsse
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The I{wsse} module provides WS-Security.
"""

from logging import getLogger
from suds import *
from suds.sudsobject import Object
from suds.sax.element import Element
from suds.sax.date import UTC
from datetime import datetime, timedelta

try:
    from hashlib import md5
except ImportError:
    # Python 2.4 compatibility
    from md5 import md5


dsns = \
    ('ds',
     'http://www.w3.org/2000/09/xmldsig#')
wssens = \
    ('wsse', 
     'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd')
wsuns = \
    ('wsu',
     'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd')
wsencns = \
    ('wsenc',
     'http://www.w3.org/2001/04/xmlenc#')


class Security(Object):
    """
    WS-Security object.
    @ivar tokens: A list of security tokens
    @type tokens: [L{Token},...]
    @ivar signatures: A list of signatures.
    @type signatures: TBD
    @ivar references: A list of references.
    @type references: TBD
    @ivar keys: A list of encryption keys.
    @type keys: TBD
    """
    
    def __init__(self):
        """ """
        Object.__init__(self)
        self.mustUnderstand = True
        self.tokens = []
        self.signatures = []
        self.references = []
        self.keys = []
        
    def xml(self):
        """
        Get xml representation of the object.
        @return: The root node.
        @rtype: L{Element}
        """
        root = Element('Security', ns=wssens)
        root.set('mustUnderstand', str(self.mustUnderstand).lower())
        for t in self.tokens:
            root.append(t.xml())
        return root


class Token(Object):
    """ I{Abstract} security token. """
    
    @classmethod
    def now(cls):
        return datetime.now()
    
    @classmethod
    def utc(cls):
        return datetime.utcnow()
    
    @classmethod
    def sysdate(cls):
        utc = UTC()
        return str(utc)
    
    def __init__(self):
            Object.__init__(self)


class UsernameToken(Token):
    """
    Represents a basic I{UsernameToken} WS-Secuirty token.
    @ivar username: A username.
    @type username: str
    @ivar password: A password.
    @type password: str
    @ivar nonce: A set of bytes to prevent reply attacks.
    @type nonce: str
    @ivar created: The token created.
    @type created: L{datetime}
    """

    def __init__(self, username=None, password=None):
        """
        @param username: A username.
        @type username: str
        @param password: A password.
        @type password: str
        """
        Token.__init__(self)
        self.username = username
        self.password = password
        self.nonce = None
        self.created = None
        
    def setnonce(self, text=None):
        """
        Set I{nonce} which is arbitraty set of bytes to prevent
        reply attacks.
        @param text: The nonce text value.
            Generated when I{None}.
        @type text: str
        """
        if text is None:
            s = []
            s.append(self.username)
            s.append(self.password)
            s.append(Token.sysdate())
            m = md5()
            m.update(':'.join(s))
            self.nonce = m.hexdigest()
        else:
            self.nonce = text
        
    def setcreated(self, dt=None):
        """
        Set I{created}.
        @param dt: The created date & time.
            Set as datetime.utc() when I{None}.
        @type dt: L{datetime}
        """
        if dt is None:
            self.created = Token.utc()
        else:
            self.created = dt
        
        
    def xml(self):
        """
        Get xml representation of the object.
        @return: The root node.
        @rtype: L{Element}
        """
        root = Element('UsernameToken', ns=wssens)
        u = Element('Username', ns=wssens)
        u.setText(self.username)
        root.append(u)
        p = Element('Password', ns=wssens)
        p.setText(self.password)
        root.append(p)
        if self.nonce is not None:
            n = Element('Nonce', ns=wssens)
            n.setText(self.nonce)
            root.append(n)
        if self.created is not None:
            n = Element('Created', ns=wsuns)
            n.setText(str(UTC(self.created)))
            root.append(n)
        return root


class Timestamp(Token):
    """
    Represents the I{Timestamp} WS-Secuirty token.
    @ivar created: The token created.
    @type created: L{datetime}
    @ivar expires: The token expires.
    @type expires: L{datetime}
    """

    def __init__(self, validity=90):
        """
        @param validity: The time in seconds.
        @type validity: int
        """
        Token.__init__(self)
        self.created = Token.utc()
        self.expires = self.created + timedelta(seconds=validity)
        
    def xml(self):
        root = Element("Timestamp", ns=wsuns)
        created = Element('Created', ns=wsuns)
        created.setText(str(UTC(self.created)))
        expires = Element('Expires', ns=wsuns)
        expires.setText(str(UTC(self.expires)))
        root.append(created)
        root.append(expires)
        return root
########NEW FILE########
__FILENAME__ = deplist
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The I{depsolve} module defines a class for performing dependancy solving.
"""

from logging import getLogger
from suds import *

log = getLogger(__name__)


class DepList:
    """
    Dependancy solving list.
    Items are tuples: (object, (deps,))
    @ivar raw: The raw (unsorted) items.
    @type raw: list
    @ivar index: The index of (unsorted) items.
    @type index: list
    @ivar stack: The sorting stack.
    @type stack: list
    @ivar pushed: The I{pushed} set tracks items that have been
        processed.
    @type pushed: set
    @ivar sorted: The sorted list of items.
    @type sorted: list
    """

    def __init__(self):
        """ """
        self.unsorted = []
        self.index = {}
        self.stack = []
        self.pushed = set()
        self.sorted = None

    def add(self, *items):
        """
        Add items to be sorted.
        @param items: One or more items to be added.
        @type items: I{item}
        @return: self
        @rtype: L{DepList}
        """
        for item in items:
            self.unsorted.append(item)
            key = item[0]
            self.index[key] = item
        return self

    def sort(self):
        """
        Sort the list based on dependancies.
        @return: The sorted items.
        @rtype: list
        """
        self.sorted = list()
        self.pushed = set()
        for item in self.unsorted:
            popped = []
            self.push(item)
            while len(self.stack):
                try:
                    top = self.top()
                    ref = top[1].next()
                    refd = self.index.get(ref)
                    if refd is None:
                        #log.debug('"%s" not found, skipped', Repr(ref))
                        continue
                    self.push(refd)
                except StopIteration:
                    popped.append(self.pop())
                    continue
            for p in popped:
                self.sorted.append(p)
        self.unsorted = self.sorted
        return self.sorted

    def top(self):
        """
        Get the item at the top of the stack.
        @return: The top item.
        @rtype: (item, iter)
        """
        return self.stack[-1]

    def push(self, item):
        """
        Push and item onto the sorting stack.
        @param item: An item to push.
        @type item: I{item}
        @return: The number of items pushed.
        @rtype: int
        """
        if item in self.pushed:
            return
        frame = (item, iter(item[1]))
        self.stack.append(frame)
        self.pushed.add(item)

    def pop(self):
        """
        Pop the top item off the stack and append
        it to the sorted list.
        @return: The popped item.
        @rtype: I{item}
        """
        try:
            frame = self.stack.pop()
            return frame[0]
        except:
            pass


if __name__ == '__main__':
    a = ('a', ('x',))
    b = ('b', ('a',))
    c = ('c', ('a','b'))
    d = ('d', ('c',))
    e = ('e', ('d','a'))
    f = ('f', ('e','c','d','a'))
    x = ('x', ())
    L = DepList()
    L.add(c, e, d, b, f, a, x)
    print [x[0] for x in L.sort()]

########NEW FILE########
__FILENAME__ = doctor
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The I{doctor} module provides classes for fixing broken (sick)
schema(s).
"""

from logging import getLogger
from suds.sax import splitPrefix, Namespace
from suds.sax.element import Element
from suds.plugin import DocumentPlugin, DocumentContext

log = getLogger(__name__)


class Doctor:
    """
    Schema Doctor.
    """
    def examine(self, root):
        """
        Examine and repair the schema (if necessary).
        @param root: A schema root element.
        @type root: L{Element}
        """
        pass


class Practice(Doctor):
    """
    A collection of doctors.
    @ivar doctors: A list of doctors.
    @type doctors: list
    """

    def __init__(self):
        self.doctors = []

    def add(self, doctor):
        """
        Add a doctor to the practice
        @param doctor: A doctor to add.
        @type doctor: L{Doctor}
        """
        self.doctors.append(doctor)

    def examine(self, root):
        for d in self.doctors:
            d.examine(root)
        return root


class TnsFilter:
    """
    Target Namespace filter.
    @ivar tns: A list of target namespaces.
    @type tns: [str,...]
    """

    def __init__(self, *tns):
        """
        @param tns: A list of target namespaces.
        @type tns: [str,...]
        """
        self.tns = []
        self.add(*tns)

    def add(self, *tns):
        """
        Add I{targetNamesapces} to be added.
        @param tns: A list of target namespaces.
        @type tns: [str,...]
        """
        self.tns += tns

    def match(self, root, ns):
        """
        Match by I{targetNamespace} excluding those that
        are equal to the specified namespace to prevent
        adding an import to itself.
        @param root: A schema root.
        @type root: L{Element}
        """
        tns = root.get('targetNamespace')
        if len(self.tns):
            matched = ( tns in self.tns )
        else:
            matched = 1
        itself = ( ns == tns )
        return ( matched and not itself )


class Import:
    """
    An <xs:import/> to be applied.
    @cvar xsdns: The XSD namespace.
    @type xsdns: (p,u)
    @ivar ns: An import namespace.
    @type ns: str
    @ivar location: An optional I{schemaLocation}.
    @type location: str
    @ivar filter: A filter used to restrict application to
        a particular schema.
    @type filter: L{TnsFilter}
    """

    xsdns = Namespace.xsdns

    def __init__(self, ns, location=None):
        """
        @param ns: An import namespace.
        @type ns: str
        @param location: An optional I{schemaLocation}.
        @type location: str
        """
        self.ns = ns
        self.location = location
        self.filter = TnsFilter()

    def setfilter(self, filter):
        """
        Set the filter.
        @param filter: A filter to set.
        @type filter: L{TnsFilter}
        """
        self.filter = filter

    def apply(self, root):
        """
        Apply the import (rule) to the specified schema.
        If the schema does not already contain an import for the
        I{namespace} specified here, it is added.
        @param root: A schema root.
        @type root: L{Element}
        """
        if not self.filter.match(root, self.ns):
            return
        if self.exists(root):
            return
        node = Element('import', ns=self.xsdns)
        node.set('namespace', self.ns)
        if self.location is not None:
            node.set('schemaLocation', self.location)
        #log.debug('inserting: %s', node)
        root.insert(node)

    def add(self, root):
        """
        Add an <xs:import/> to the specified schema root.
        @param root: A schema root.
        @type root: L{Element}
        """
        node = Element('import', ns=self.xsdns)
        node.set('namespace', self.ns)
        if self.location is not None:
            node.set('schemaLocation', self.location)
        #log.debug('%s inserted', node)
        root.insert(node)

    def exists(self, root):
        """
        Check to see if the <xs:import/> already exists
        in the specified schema root by matching I{namesapce}.
        @param root: A schema root.
        @type root: L{Element}
        """
        for node in root.children:
            if node.name != 'import':
                continue
            ns = node.get('namespace')
            if self.ns == ns:
                return 1
        return 0


class ImportDoctor(Doctor, DocumentPlugin):
    """
    Doctor used to fix missing imports.
    @ivar imports: A list of imports to apply.
    @type imports: [L{Import},...]
    """

    def __init__(self, *imports):
        """
        """
        self.imports = []
        self.add(*imports)

    def add(self, *imports):
        """
        Add a namesapce to be checked.
        @param imports: A list of L{Import} objects.
        @type imports: [L{Import},..]
        """
        self.imports += imports

    def examine(self, node):
        for imp in self.imports:
            imp.apply(node)

    def parsed(self, context):
        node = context.document
        # xsd root
        if node.name == 'schema' and Namespace.xsd(node.namespace()):
            self.examine(node)
            return
        # look deeper
        context = DocumentContext()
        for child in node:
            context.document = child
            self.parsed(context)

########NEW FILE########
__FILENAME__ = query
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The I{query} module defines a class for performing schema queries.
"""

from logging import getLogger
from suds import *
from suds.sudsobject import *
from suds.xsd import qualify, isqref
from suds.xsd.sxbuiltin import Factory

log = getLogger(__name__)


class Query(Object):
    """
    Schema query base class.
    """

    def __init__(self, ref=None):
        """
        @param ref: The schema reference being queried.
        @type ref: qref
        """
        Object.__init__(self)
        self.id = objid(self)
        self.ref = ref
        self.history = []
        self.resolved = False
        if not isqref(self.ref):
            raise Exception('%s, must be qref' % tostr(self.ref))

    def execute(self, schema):
        """
        Execute this query using the specified schema.
        @param schema: The schema associated with the query.  The schema
            is used by the query to search for items.
        @type schema: L{schema.Schema}
        @return: The item matching the search criteria.
        @rtype: L{sxbase.SchemaObject}
        """
        raise Exception, 'not-implemented by subclass'

    def filter(self, result):
        """
        Filter the specified result based on query criteria.
        @param result: A potential result.
        @type result: L{sxbase.SchemaObject}
        @return: True if result should be excluded.
        @rtype: boolean
        """
        if result is None:
            return True
        reject = ( result in self.history )
        if reject:
            pass#log.debug('result %s, rejected by\n%s', Repr(result), self)
        return reject

    def result(self, result):
        """
        Query result post processing.
        @param result: A query result.
        @type result: L{sxbase.SchemaObject}
        """
        if result is None:
            #log.debug('%s, not-found', self.ref)
            return
        if self.resolved:
            result = result.resolve()
        #log.debug('%s, found as: %s', self.ref, Repr(result))
        self.history.append(result)
        return result


class BlindQuery(Query):
    """
    Schema query class that I{blindly} searches for a reference in
    the specified schema.  It may be used to find Elements and Types but
    will match on an Element first.  This query will also find builtins.
    """

    def execute(self, schema):
        if schema.builtin(self.ref):
            name = self.ref[0]
            b = Factory.create(schema, name)
            #log.debug('%s, found builtin (%s)', self.id, name)
            return b
        result = None
        for d in (schema.elements, schema.types):
            result = d.get(self.ref)
            if self.filter(result):
                result = None
            else:
                break
        if result is None:
            eq = ElementQuery(self.ref)
            eq.history = self.history
            result = eq.execute(schema)
        return self.result(result)


class TypeQuery(Query):
    """
    Schema query class that searches for Type references in
    the specified schema.  Matches on root types only.
    """

    def execute(self, schema):
        if schema.builtin(self.ref):
            name = self.ref[0]
            b = Factory.create(schema, name)
            #log.debug('%s, found builtin (%s)', self.id, name)
            return b
        result = schema.types.get(self.ref)
        if self.filter(result):
            result = None
        return self.result(result)


class GroupQuery(Query):
    """
    Schema query class that searches for Group references in
    the specified schema.
    """

    def execute(self, schema):
        result = schema.groups.get(self.ref)
        if self.filter(result):
            result = None
        return self.result(result)


class AttrQuery(Query):
    """
    Schema query class that searches for Attribute references in
    the specified schema.  Matches on root Attribute by qname first, then searches
    deep into the document.
    """

    def execute(self, schema):
        result = schema.attributes.get(self.ref)
        if self.filter(result):
            result = self.__deepsearch(schema)
        return self.result(result)

    def __deepsearch(self, schema):
        from suds.xsd.sxbasic import Attribute
        result = None
        for e in schema.all:
            result = e.find(self.ref, (Attribute,))
            if self.filter(result):
                result = None
            else:
                break
        return result


class AttrGroupQuery(Query):
    """
    Schema query class that searches for attributeGroup references in
    the specified schema.
    """

    def execute(self, schema):
        result = schema.agrps.get(self.ref)
        if self.filter(result):
            result = None
        return self.result(result)


class ElementQuery(Query):
    """
    Schema query class that searches for Element references in
    the specified schema.  Matches on root Elements by qname first, then searches
    deep into the document.
    """

    def execute(self, schema):
        result = schema.elements.get(self.ref)
        if self.filter(result):
            result = self.__deepsearch(schema)
        return self.result(result)

    def __deepsearch(self, schema):
        from suds.xsd.sxbasic import Element
        result = None
        for e in schema.all:
            result = e.find(self.ref, (Element,))
            if self.filter(result):
                result = None
            else:
                break
        return result

########NEW FILE########
__FILENAME__ = schema
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The I{schema} module provides a intelligent representation of
an XSD schema.  The I{raw} model is the XML tree and the I{model}
is the denormalized, objectified and intelligent view of the schema.
Most of the I{value-add} provided by the model is centered around
tranparent referenced type resolution and targeted denormalization.
"""


import suds.metrics
from suds import *
from suds.xsd import *
from suds.xsd.sxbuiltin import *
from suds.xsd.sxbasic import Factory as BasicFactory
from suds.xsd.sxbuiltin import Factory as BuiltinFactory
from suds.xsd.sxbase import SchemaObject
from suds.xsd.deplist import DepList
from suds.sax.element import Element
from suds.sax import splitPrefix, Namespace
from logging import getLogger

log = getLogger(__name__)


class SchemaCollection:
    """
    A collection of schema objects.  This class is needed because WSDLs
    may contain more then one <schema/> node.
    @ivar wsdl: A wsdl object.
    @type wsdl: L{suds.wsdl.Definitions}
    @ivar children: A list contained schemas.
    @type children: [L{Schema},...]
    @ivar namespaces: A dictionary of contained schemas by namespace.
    @type namespaces: {str:L{Schema}}
    """

    def __init__(self, wsdl):
        """
        @param wsdl: A wsdl object.
        @type wsdl: L{suds.wsdl.Definitions}
        """
        self.wsdl = wsdl
        self.children = []
        self.namespaces = {}

    def add(self, schema):
        """
        Add a schema node to the collection.  Schema(s) within the same target
        namespace are consolidated.
        @param schema: A schema object.
        @type schema: (L{Schema})
        """
        key = schema.tns[1]
        existing = self.namespaces.get(key)
        if existing is None:
            self.children.append(schema)
            self.namespaces[key] = schema
        else:
            existing.root.children += schema.root.children
            existing.root.nsprefixes.update(schema.root.nsprefixes)

    def load(self, options):
        """
        Load the schema objects for the root nodes.
            - de-references schemas
            - merge schemas
        @param options: An options dictionary.
        @type options: L{options.Options}
        @return: The merged schema.
        @rtype: L{Schema}
        """
        if options.autoblend:
            self.autoblend()
        for child in self.children:
            child.build()
        for child in self.children:
            child.open_imports(options)
        for child in self.children:
            child.dereference()
        #log.debug('loaded:\n%s', self)
        merged = self.merge()
        #log.debug('MERGED:\n%s', merged)
        return merged

    def autoblend(self):
        """
        Ensure that all schemas within the collection
        import each other which has a blending effect.
        @return: self
        @rtype: L{SchemaCollection}
        """
        namespaces = self.namespaces.keys()
        for s in self.children:
            for ns in namespaces:
                tns = s.root.get('targetNamespace')
                if  tns == ns:
                    continue
                for imp in s.root.getChildren('import'):
                    if imp.get('namespace') == ns:
                        continue
                imp = Element('import', ns=Namespace.xsdns)
                imp.set('namespace', ns)
                s.root.append(imp)
        return self

    def locate(self, ns):
        """
        Find a schema by namespace.  Only the URI portion of
        the namespace is compared to each schema's I{targetNamespace}
        @param ns: A namespace.
        @type ns: (prefix,URI)
        @return: The schema matching the namesapce, else None.
        @rtype: L{Schema}
        """
        return self.namespaces.get(ns[1])

    def merge(self):
        """
        Merge the contained schemas into one.
        @return: The merged schema.
        @rtype: L{Schema}
        """
        if len(self):
            schema = self.children[0]
            for s in self.children[1:]:
                schema.merge(s)
            return schema
        else:
            return None

    def __len__(self):
        return len(self.children)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        result = ['\nschema collection']
        for s in self.children:
            result.append(s.str(1))
        return '\n'.join(result)


class Schema:
    """
    The schema is an objectification of a <schema/> (xsd) definition.
    It provides inspection, lookup and type resolution.
    @ivar root: The root node.
    @type root: L{sax.element.Element}
    @ivar baseurl: The I{base} URL for this schema.
    @type baseurl: str
    @ivar container: A schema collection containing this schema.
    @type container: L{SchemaCollection}
    @ivar children: A list of direct top level children.
    @type children: [L{SchemaObject},...]
    @ivar all: A list of all (includes imported) top level children.
    @type all: [L{SchemaObject},...]
    @ivar types: A schema types cache.
    @type types: {name:L{SchemaObject}}
    @ivar imports: A list of import objects.
    @type imports: [L{SchemaObject},...]
    @ivar elements: A list of <element/> objects.
    @type elements: [L{SchemaObject},...]
    @ivar attributes: A list of <attribute/> objects.
    @type attributes: [L{SchemaObject},...]
    @ivar groups: A list of group objects.
    @type groups: [L{SchemaObject},...]
    @ivar agrps: A list of attribute group objects.
    @type agrps: [L{SchemaObject},...]
    @ivar form_qualified: The flag indicating:
        (@elementFormDefault).
    @type form_qualified: bool
    """

    Tag = 'schema'

    def __init__(self, root, baseurl, options, container=None):
        """
        @param root: The xml root.
        @type root: L{sax.element.Element}
        @param baseurl: The base url used for importing.
        @type baseurl: basestring
        @param options: An options dictionary.
        @type options: L{options.Options}
        @param container: An optional container.
        @type container: L{SchemaCollection}
        """
        self.root = root
        self.id = objid(self)
        self.tns = self.mktns()
        self.baseurl = baseurl
        self.container = container
        self.children = []
        self.all = []
        self.types = {}
        self.imports = []
        self.elements = {}
        self.attributes = {}
        self.groups = {}
        self.agrps = {}
        if options.doctor is not None:
            options.doctor.examine(root)
        form = self.root.get('elementFormDefault')
        if form is None:
            self.form_qualified = False
        else:
            self.form_qualified = ( form == 'qualified' )
        if container is None:
            self.build()
            self.open_imports(options)
            #log.debug('built:\n%s', self)
            self.dereference()
            #log.debug('dereferenced:\n%s', self)

    def mktns(self):
        """
        Make the schema's target namespace.
        @return: The namespace representation of the schema's
            targetNamespace value.
        @rtype: (prefix, uri)
        """
        tns = [None, self.root.get('targetNamespace')]
        if tns[1] is not None:
            tns[0] = self.root.findPrefix(tns[1])
        return tuple(tns)

    def build(self):
        """
        Build the schema (object graph) using the root node
        using the factory.
            - Build the graph.
            - Collate the children.
        """
        self.children = BasicFactory.build(self.root, self)
        collated = BasicFactory.collate(self.children)
        self.children = collated[0]
        self.attributes = collated[2]
        self.imports = collated[1]
        self.elements = collated[3]
        self.types = collated[4]
        self.groups = collated[5]
        self.agrps = collated[6]

    def merge(self, schema):
        """
        Merge the contents from the schema.  Only objects not already contained
        in this schema's collections are merged.  This is to provide for bidirectional
        import which produce cyclic includes.
        @returns: self
        @rtype: L{Schema}
        """
        for item in schema.attributes.items():
            if item[0] in self.attributes:
                continue
            self.all.append(item[1])
            self.attributes[item[0]] = item[1]
        for item in schema.elements.items():
            if item[0] in self.elements:
                continue
            self.all.append(item[1])
            self.elements[item[0]] = item[1]
        for item in schema.types.items():
            if item[0] in self.types:
                continue
            self.all.append(item[1])
            self.types[item[0]] = item[1]
        for item in schema.groups.items():
            if item[0] in self.groups:
                continue
            self.all.append(item[1])
            self.groups[item[0]] = item[1]
        for item in schema.agrps.items():
            if item[0] in self.agrps:
                continue
            self.all.append(item[1])
            self.agrps[item[0]] = item[1]
        schema.merged = True
        return self

    def open_imports(self, options):
        """
        Instruct all contained L{sxbasic.Import} children to import
        the schema's which they reference.  The contents of the
        imported schema are I{merged} in.
        @param options: An options dictionary.
        @type options: L{options.Options}
        """
        for imp in self.imports:
            imported = imp.open(options)
            if imported is None:
                continue
            imported.open_imports(options)
            #log.debug('imported:\n%s', imported)
            self.merge(imported)

    def dereference(self):
        """
        Instruct all children to perform dereferencing.
        """
        all = []
        indexes = {}
        for child in self.children:
            child.content(all)
        deplist = DepList()
        for x in all:
            x.qualify()
            midx, deps = x.dependencies()
            item = (x, tuple(deps))
            deplist.add(item)
            indexes[x] = midx
        for x, deps in deplist.sort():
            midx = indexes.get(x)
            if midx is None: continue
            d = deps[midx]
            #log.debug('(%s) merging %s <== %s', self.tns[1], Repr(x), Repr(d))
            x.merge(d)

    def locate(self, ns):
        """
        Find a schema by namespace.  Only the URI portion of
        the namespace is compared to each schema's I{targetNamespace}.
        The request is passed to the container.
        @param ns: A namespace.
        @type ns: (prefix,URI)
        @return: The schema matching the namesapce, else None.
        @rtype: L{Schema}
        """
        if self.container is not None:
            return self.container.locate(ns)
        else:
            return None

    def custom(self, ref, context=None):
        """
        Get whether the specified reference is B{not} an (xs) builtin.
        @param ref: A str or qref.
        @type ref: (str|qref)
        @return: True if B{not} a builtin, else False.
        @rtype: bool
        """
        if ref is None:
            return True
        else:
            return ( not self.builtin(ref, context) )

    def builtin(self, ref, context=None):
        """
        Get whether the specified reference is an (xs) builtin.
        @param ref: A str or qref.
        @type ref: (str|qref)
        @return: True if builtin, else False.
        @rtype: bool
        """
        w3 = 'http://www.w3.org'
        try:
            if isqref(ref):
                ns = ref[1]
                return ( ref[0] in Factory.tags and ns.startswith(w3) )
            if context is None:
                context = self.root
            prefix = splitPrefix(ref)[0]
            prefixes = context.findPrefixes(w3, 'startswith')
            return ( prefix in prefixes and ref[0] in Factory.tags )
        except:
            return False

    def instance(self, root, baseurl, options):
        """
        Create and return an new schema object using the
        specified I{root} and I{url}.
        @param root: A schema root node.
        @type root: L{sax.element.Element}
        @param baseurl: A base URL.
        @type baseurl: str
        @param options: An options dictionary.
        @type options: L{options.Options}
        @return: The newly created schema object.
        @rtype: L{Schema}
        @note: This is only used by Import children.
        """
        return Schema(root, baseurl, options)

    def str(self, indent=0):
        tab = '%*s'%(indent*3, '')
        result = []
        result.append('%s%s' % (tab, self.id))
        result.append('%s(raw)' % tab)
        result.append(self.root.str(indent+1))
        result.append('%s(model)' % tab)
        for c in self.children:
            result.append(c.str(indent+1))
        result.append('')
        return '\n'.join(result)

    def __repr__(self):
        myrep = '<%s tns="%s"/>' % (self.id, self.tns[1])
        return myrep.encode('utf-8')

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return self.str()

########NEW FILE########
__FILENAME__ = sxbase
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The I{sxbase} module provides I{base} classes that represent
schema objects.
"""

from logging import getLogger
from suds import *
from suds.xsd import *
from suds.sax.element import Element
from suds.sax import Namespace

log = getLogger(__name__)


class SchemaObject(object):
    """
    A schema object is an extension to object object with
    with schema awareness.
    @ivar root: The XML root element.
    @type root: L{Element}
    @ivar schema: The schema containing this object.
    @type schema: L{schema.Schema}
    @ivar form_qualified: A flag that inidcates that @elementFormDefault
        has a value of I{qualified}.
    @type form_qualified: boolean
    @ivar nillable: A flag that inidcates that @nillable
        has a value of I{true}.
    @type nillable: boolean
    @ivar default: The default value.
    @type default: object
    @ivar rawchildren: A list raw of all children.
    @type rawchildren: [L{SchemaObject},...]
    """

    @classmethod
    def prepend(cls, d, s, filter=Filter()):
        """
        Prepend schema object's from B{s}ource list to
        the B{d}estination list while applying the filter.
        @param d: The destination list.
        @type d: list
        @param s: The source list.
        @type s: list
        @param filter: A filter that allows items to be prepended.
        @type filter: L{Filter}
        """
        i = 0
        for x in s:
            if x in filter:
                d.insert(i, x)
                i += 1

    @classmethod
    def append(cls, d, s, filter=Filter()):
        """
        Append schema object's from B{s}ource list to
        the B{d}estination list while applying the filter.
        @param d: The destination list.
        @type d: list
        @param s: The source list.
        @type s: list
        @param filter: A filter that allows items to be appended.
        @type filter: L{Filter}
        """
        for item in s:
            if item in filter:
                d.append(item)

    def __init__(self, schema, root):
        """
        @param schema: The containing schema.
        @type schema: L{schema.Schema}
        @param root: The xml root node.
        @type root: L{Element}
        """
        self.schema = schema
        self.root = root
        self.id = objid(self)
        self.name = root.get('name')
        self.qname = (self.name, schema.tns[1])
        self.min = root.get('minOccurs')
        self.max = root.get('maxOccurs')
        self.type = root.get('type')
        self.ref = root.get('ref')
        self.form_qualified = schema.form_qualified
        self.nillable = False
        self.default = root.get('default')
        self.rawchildren = []
        self.cache = {}

    def attributes(self, filter=Filter()):
        """
        Get only the attribute content.
        @param filter: A filter to constrain the result.
        @type filter: L{Filter}
        @return: A list of tuples (attr, ancestry)
        @rtype: [(L{SchemaObject}, [L{SchemaObject},..]),..]
        """
        result = []
        for child, ancestry in self:
            if child.isattr() and child in filter:
                result.append((child, ancestry))
        return result

    def children(self, filter=Filter()):
        """
        Get only the I{direct} or non-attribute content.
        @param filter: A filter to constrain the result.
        @type filter: L{Filter}
        @return: A list tuples: (child, ancestry)
        @rtype: [(L{SchemaObject}, [L{SchemaObject},..]),..]
        """
        result = []
        for child, ancestry in self:
            if not child.isattr() and child in filter:
                result.append((child, ancestry))
        return result

    def get_attribute(self, name):
        """
        Get (find) a I{non-attribute} attribute by name.
        @param name: A attribute name.
        @type name: str
        @return: A tuple: the requested (attribute, ancestry).
        @rtype: (L{SchemaObject}, [L{SchemaObject},..])
        """
        for child, ancestry in self.attributes():
            if child.name == name:
                return (child, ancestry)
        return (None, [])

    def get_child(self, name):
        """
        Get (find) a I{non-attribute} child by name.
        @param name: A child name.
        @type name: str
        @return: A tuple: the requested (child, ancestry).
        @rtype: (L{SchemaObject}, [L{SchemaObject},..])
        """
        for child, ancestry in self.children():
            if child.any() or child.name == name:
                return (child, ancestry)
        return (None, [])

    def namespace(self, prefix=None):
        """
        Get this properties namespace
        @param prefix: The default prefix.
        @type prefix: str
        @return: The schema's target namespace
        @rtype: (I{prefix},I{URI})
        """
        ns = self.schema.tns
        if ns[0] is None:
            ns = (prefix, ns[1])
        return ns

    def default_namespace(self):
        return self.root.defaultNamespace()

    def unbounded(self):
        """
        Get whether this node is unbounded I{(a collection)}
        @return: True if unbounded, else False.
        @rtype: boolean
        """
        max = self.max
        if max is None:
            max = '1'
        if max.isdigit():
            return (int(max) > 1)
        else:
            return ( max == 'unbounded' )

    def optional(self):
        """
        Get whether this type is optional.
        @return: True if optional, else False
        @rtype: boolean
        """
        min = self.min
        if min is None:
            min = '1'
        return ( min == '0' )

    def required(self):
        """
        Get whether this type is required.
        @return: True if required, else False
        @rtype: boolean
        """
        return ( not self.optional() )


    def resolve(self, nobuiltin=False):
        """
        Resolve and return the nodes true self.
        @param nobuiltin: Flag indicates that resolution must
            not continue to include xsd builtins.
        @return: The resolved (true) type.
        @rtype: L{SchemaObject}
        """
        return self.cache.get(nobuiltin, self)

    def sequence(self):
        """
        Get whether this is an <xs:sequence/>
        @return: True if <xs:sequence/>, else False
        @rtype: boolean
        """
        return False

    def xslist(self):
        """
        Get whether this is an <xs:list/>
        @return: True if any, else False
        @rtype: boolean
        """
        return False

    def all(self):
        """
        Get whether this is an <xs:all/>
        @return: True if any, else False
        @rtype: boolean
        """
        return False

    def choice(self):
        """
        Get whether this is n <xs:choice/>
        @return: True if any, else False
        @rtype: boolean
        """
        return False

    def any(self):
        """
        Get whether this is an <xs:any/>
        @return: True if any, else False
        @rtype: boolean
        """
        return False

    def builtin(self):
        """
        Get whether this is a schema-instance (xs) type.
        @return: True if any, else False
        @rtype: boolean
        """
        return False

    def enum(self):
        """
        Get whether this is a simple-type containing an enumeration.
        @return: True if any, else False
        @rtype: boolean
        """
        return False

    def isattr(self):
        """
        Get whether the object is a schema I{attribute} definition.
        @return: True if an attribute, else False.
        @rtype: boolean
        """
        return False

    def extension(self):
        """
        Get whether the object is an extension of another type.
        @return: True if an extension, else False.
        @rtype: boolean
        """
        return False

    def restriction(self):
        """
        Get whether the object is an restriction of another type.
        @return: True if an restriction, else False.
        @rtype: boolean
        """
        return False

    def mixed(self):
        """
        Get whether this I{mixed} content.
        """
        return False

    def find(self, qref, classes=()):
        """
        Find a referenced type in self or children.
        @param qref: A qualified reference.
        @type qref: qref
        @param classes: A list of classes used to qualify the match.
        @type classes: [I{class},...]
        @return: The referenced type.
        @rtype: L{SchemaObject}
        @see: L{qualify()}
        """
        if not len(classes):
            classes = (self.__class__,)
        if self.qname == qref and self.__class__ in classes:
            return self
        for c in self.rawchildren:
            p = c.find(qref, classes)
            if p is not None:
                return p
        return None

    def translate(self, value, topython=True):
        """
        Translate a value (type) to/from a python type.
        @param value: A value to translate.
        @return: The converted I{language} type.
        """
        return value

    def childtags(self):
        """
        Get a list of valid child tag names.
        @return: A list of child tag names.
        @rtype: [str,...]
        """
        return ()

    def dependencies(self):
        """
        Get a list of dependancies for dereferencing.
        @return: A merge dependancy index and a list of dependancies.
        @rtype: (int, [L{SchemaObject},...])
        """
        return (None, [])

    def autoqualified(self):
        """
        The list of I{auto} qualified attribute values.
        Qualification means to convert values into I{qref}.
        @return: A list of attibute names.
        @rtype: list
        """
        return ['type', 'ref']

    def qualify(self):
        """
        Convert attribute values, that are references to other
        objects, into I{qref}.  Qualfied using default document namespace.
        Since many wsdls are written improperly: when the document does
        not define a default namespace, the schema target namespace is used
        to qualify references.
        """
        defns = self.root.defaultNamespace()
        if Namespace.none(defns):
            defns = self.schema.tns
        for a in self.autoqualified():
            ref = getattr(self, a)
            if ref is None:
                continue
            if isqref(ref):
                continue
            qref = qualify(ref, self.root, defns)
            #log.debug('%s, convert %s="%s" to %s', self.id, a, ref, qref)
            setattr(self, a, qref)

    def merge(self, other):
        """
        Merge another object as needed.
        """
        other.qualify()
        for n in ('name',
                  'qname',
                  'min',
                  'max',
                  'default',
                  'type',
                  'nillable',
                  'form_qualified',):
            if getattr(self, n) is not None:
                continue
            v = getattr(other, n)
            if v is None:
                continue
            setattr(self, n, v)


    def content(self, collection=None, filter=Filter(), history=None):
        """
        Get a I{flattened} list of this nodes contents.
        @param collection: A list to fill.
        @type collection: list
        @param filter: A filter used to constrain the result.
        @type filter: L{Filter}
        @param history: The history list used to prevent cyclic dependency.
        @type history: list
        @return: The filled list.
        @rtype: list
        """
        if collection is None:
            collection = []
        if history is None:
            history = []
        if self in history:
            return collection
        history.append(self)
        if self in filter:
            collection.append(self)
        for c in self.rawchildren:
            c.content(collection, filter, history[:])
        return collection

    def str(self, indent=0, history=None):
        """
        Get a string representation of this object.
        @param indent: The indent.
        @type indent: int
        @return: A string.
        @rtype: str
        """
        if history is None:
            history = []
        if self in history:
            return '%s ...' % Repr(self)
        history.append(self)
        tab = '%*s'%(indent*3, '')
        result  = []
        result.append('%s<%s' % (tab, self.id))
        for n in self.description():
            if not hasattr(self, n):
                continue
            v = getattr(self, n)
            if v is None:
                continue
            result.append(' %s="%s"' % (n, v))
        if len(self):
            result.append('>')
            for c in self.rawchildren:
                result.append('\n')
                result.append(c.str(indent+1, history[:]))
                if c.isattr():
                    result.append('@')
            result.append('\n%s' % tab)
            result.append('</%s>' % self.__class__.__name__)
        else:
            result.append(' />')
        return ''.join(result)

    def description(self):
        """
        Get the names used for str() and repr() description.
        @return:  A dictionary of relavent attributes.
        @rtype: [str,...]
        """
        return ()

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return unicode(self.str())

    def __repr__(self):
        s = []
        s.append('<%s' % self.id)
        for n in self.description():
            if not hasattr(self, n):
                continue
            v = getattr(self, n)
            if v is None:
                continue
            s.append(' %s="%s"' % (n, v))
        s.append(' />')
        myrep = ''.join(s)
        return myrep.encode('utf-8')

    def __len__(self):
        n = 0
        for x in self: n += 1
        return n

    def __iter__(self):
        return Iter(self)

    def __getitem__(self, index):
        i = 0
        for c in self:
            if i == index:
                return c


class Iter:
    """
    The content iterator - used to iterate the L{Content} children.  The iterator
    provides a I{view} of the children that is free of container elements
    such as <sequence/> and <choice/>.
    @ivar stack: A stack used to control nesting.
    @type stack: list
    """

    class Frame:
        """ A content iterator frame. """

        def __init__(self, sx):
            """
            @param sx: A schema object.
            @type sx: L{SchemaObject}
            """
            self.sx = sx
            self.items = sx.rawchildren
            self.index = 0

        def next(self):
            """
            Get the I{next} item in the frame's collection.
            @return: The next item or None
            @rtype: L{SchemaObject}
            """
            if self.index < len(self.items):
                result = self.items[self.index]
                self.index += 1
                return result

    def __init__(self, sx):
        """
        @param sx: A schema object.
        @type sx: L{SchemaObject}
        """
        self.stack = []
        self.push(sx)

    def push(self, sx):
        """
        Create a frame and push the specified object.
        @param sx: A schema object to push.
        @type sx: L{SchemaObject}
        """
        self.stack.append(Iter.Frame(sx))

    def pop(self):
        """
        Pop the I{top} frame.
        @return: The popped frame.
        @rtype: L{Frame}
        @raise StopIteration: when stack is empty.
        """
        if len(self.stack):
            return self.stack.pop()
        else:
            raise StopIteration()

    def top(self):
        """
        Get the I{top} frame.
        @return: The top frame.
        @rtype: L{Frame}
        @raise StopIteration: when stack is empty.
        """
        if len(self.stack):
            return self.stack[-1]
        else:
            raise StopIteration()

    def next(self):
        """
        Get the next item.
        @return: A tuple: the next (child, ancestry).
        @rtype: (L{SchemaObject}, [L{SchemaObject},..])
        @raise StopIteration: A the end.
        """
        frame = self.top()
        while True:
            result = frame.next()
            if result is None:
                self.pop()
                return self.next()
            if isinstance(result, Content):
                ancestry = [f.sx for f in self.stack]
                return (result, ancestry)
            self.push(result)
            return self.next()

    def __iter__(self):
        return self


class XBuiltin(SchemaObject):
    """
    Represents an (xsd) schema <xs:*/> node
    """

    def __init__(self, schema, name):
        """
        @param schema: The containing schema.
        @type schema: L{schema.Schema}
        """
        root = Element(name)
        SchemaObject.__init__(self, schema, root)
        self.name = name
        self.nillable = True

    def namespace(self, prefix=None):
        return Namespace.xsdns

    def builtin(self):
        return True

    def resolve(self, nobuiltin=False):
        return self


class Content(SchemaObject):
    """
    This class represents those schema objects that represent
    real XML document content.
    """
    pass


class NodeFinder:
    """
    Find nodes based on flexable criteria.  The I{matcher} is
    may be any object that implements a match(n) method.
    @ivar matcher: An object used as criteria for match.
    @type matcher: I{any}.match(n)
    @ivar limit: Limit the number of matches.  0=unlimited.
    @type limit: int
    """
    def __init__(self, matcher, limit=0):
        """
        @param matcher: An object used as criteria for match.
        @type matcher: I{any}.match(n)
        @param limit: Limit the number of matches.  0=unlimited.
        @type limit: int
        """
        self.matcher = matcher
        self.limit = limit

    def find(self, node, list):
        """
        Traverse the tree looking for matches.
        @param node: A node to match on.
        @type node: L{SchemaObject}
        @param list: A list to fill.
        @type list: list
        """
        if self.matcher.match(node):
            list.append(node)
            self.limit -= 1
            if self.limit == 0:
                return
        for c in node.rawchildren:
            self.find(c, list)
        return self

########NEW FILE########
__FILENAME__ = sxbasic
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The I{sxbasic} module provides classes that represent
I{basic} schema objects.
"""

from logging import getLogger
from suds import *
from suds.xsd import *
from suds.xsd.sxbase import *
from suds.xsd.query import *
from suds.sax import splitPrefix, Namespace
from suds.transport import TransportError
from suds.reader import DocumentReader
from urlparse import urljoin


log = getLogger(__name__)


class RestrictionMatcher:
    """
    For use with L{NodeFinder} to match restriction.
    """
    def match(self, n):
        return isinstance(n, Restriction)


class TypedContent(Content):
    """
    Represents any I{typed} content.
    """
    def resolve(self, nobuiltin=False):
        qref = self.qref()
        if qref is None:
            return self
        key = 'resolved:nb=%s' % nobuiltin
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        result = self
        query = TypeQuery(qref)
        query.history = [self]
        #log.debug('%s, resolving: %s\n using:%s', self.id, qref, query)
        resolved = query.execute(self.schema)
        if resolved is None:
            #log.debug(self.schema)
            raise TypeNotFound(qref)
        self.cache[key] = resolved
        if resolved.builtin():
            if nobuiltin:
                result = self
            else:
                result = resolved
        else:
            result = resolved.resolve(nobuiltin)
        return result

    def qref(self):
        """
        Get the I{type} qualified reference to the referenced xsd type.
        This method takes into account simple types defined through
        restriction with are detected by determining that self is simple
        (len=0) and by finding a restriction child.
        @return: The I{type} qualified reference.
        @rtype: qref
        """
        qref = self.type
        if qref is None and len(self) == 0:
            ls = []
            m = RestrictionMatcher()
            finder = NodeFinder(m, 1)
            finder.find(self, ls)
            if len(ls):
                return ls[0].ref
        return qref


class Complex(SchemaObject):
    """
    Represents an (xsd) schema <xs:complexType/> node.
    @cvar childtags: A list of valid child node names
    @type childtags: (I{str},...)
    """

    def childtags(self):
        return (
            'attribute',
            'attributeGroup',
            'sequence',
            'all',
            'choice',
            'complexContent',
            'simpleContent',
            'any',
            'group')

    def description(self):
        return ('name',)

    def extension(self):
        for c in self.rawchildren:
            if c.extension():
                return True
        return False

    def mixed(self):
        for c in self.rawchildren:
            if isinstance(c, SimpleContent) and c.mixed():
                return True
        return False


class Group(SchemaObject):
    """
    Represents an (xsd) schema <xs:group/> node.
    @cvar childtags: A list of valid child node names
    @type childtags: (I{str},...)
    """

    def childtags(self):
        return ('sequence', 'all', 'choice')

    def dependencies(self):
        deps = []
        midx = None
        if self.ref is not None:
            query = GroupQuery(self.ref)
            g = query.execute(self.schema)
            if g is None:
                #log.debug(self.schema)
                raise TypeNotFound(self.ref)
            deps.append(g)
            midx = 0
        return (midx, deps)

    def merge(self, other):
        SchemaObject.merge(self, other)
        self.rawchildren = other.rawchildren

    def description(self):
        return ('name', 'ref',)


class AttributeGroup(SchemaObject):
    """
    Represents an (xsd) schema <xs:attributeGroup/> node.
    @cvar childtags: A list of valid child node names
    @type childtags: (I{str},...)
    """

    def childtags(self):
        return ('attribute', 'attributeGroup')

    def dependencies(self):
        deps = []
        midx = None
        if self.ref is not None:
            query = AttrGroupQuery(self.ref)
            ag = query.execute(self.schema)
            if ag is None:
                #log.debug(self.schema)
                raise TypeNotFound(self.ref)
            deps.append(ag)
            midx = 0
        return (midx, deps)

    def merge(self, other):
        SchemaObject.merge(self, other)
        self.rawchildren = other.rawchildren

    def description(self):
        return ('name', 'ref',)


class Simple(SchemaObject):
    """
    Represents an (xsd) schema <xs:simpleType/> node
    """

    def childtags(self):
        return ('restriction', 'any', 'list',)

    def enum(self):
        for child, ancestry in self.children():
            if isinstance(child, Enumeration):
                return True
        return False

    def mixed(self):
        return len(self)

    def description(self):
        return ('name',)

    def extension(self):
        for c in self.rawchildren:
            if c.extension():
                return True
        return False

    def restriction(self):
        for c in self.rawchildren:
            if c.restriction():
                return True
        return False


class List(SchemaObject):
    """
    Represents an (xsd) schema <xs:list/> node
    """

    def childtags(self):
        return ()

    def description(self):
        return ('name',)

    def xslist(self):
        return True


class Restriction(SchemaObject):
    """
    Represents an (xsd) schema <xs:restriction/> node
    """

    def __init__(self, schema, root):
        SchemaObject.__init__(self, schema, root)
        self.ref = root.get('base')

    def childtags(self):
        return ('enumeration', 'attribute', 'attributeGroup')

    def dependencies(self):
        deps = []
        midx = None
        if self.ref is not None:
            query = TypeQuery(self.ref)
            super = query.execute(self.schema)
            if super is None:
                #log.debug(self.schema)
                raise TypeNotFound(self.ref)
            if not super.builtin():
                deps.append(super)
                midx = 0
        return (midx, deps)

    def restriction(self):
        return True

    def merge(self, other):
        SchemaObject.merge(self, other)
        filter = Filter(False, self.rawchildren)
        self.prepend(self.rawchildren, other.rawchildren, filter)

    def description(self):
        return ('ref',)


class Collection(SchemaObject):
    """
    Represents an (xsd) schema collection node:
        - sequence
        - choice
        - all
    """

    def childtags(self):
        return ('element', 'sequence', 'all', 'choice', 'any', 'group')


class Sequence(Collection):
    """
    Represents an (xsd) schema <xs:sequence/> node.
    """
    def sequence(self):
        return True


class All(Collection):
    """
    Represents an (xsd) schema <xs:all/> node.
    """
    def all(self):
        return True

class Choice(Collection):
    """
    Represents an (xsd) schema <xs:choice/> node.
    """
    def choice(self):
        return True


class ComplexContent(SchemaObject):
    """
    Represents an (xsd) schema <xs:complexContent/> node.
    """

    def childtags(self):
        return ('attribute', 'attributeGroup', 'extension', 'restriction')

    def extension(self):
        for c in self.rawchildren:
            if c.extension():
                return True
        return False

    def restriction(self):
        for c in self.rawchildren:
            if c.restriction():
                return True
        return False


class SimpleContent(SchemaObject):
    """
    Represents an (xsd) schema <xs:simpleContent/> node.
    """

    def childtags(self):
        return ('extension', 'restriction')

    def extension(self):
        for c in self.rawchildren:
            if c.extension():
                return True
        return False

    def restriction(self):
        for c in self.rawchildren:
            if c.restriction():
                return True
        return False

    def mixed(self):
        return len(self)


class Enumeration(Content):
    """
    Represents an (xsd) schema <xs:enumeration/> node
    """

    def __init__(self, schema, root):
        Content.__init__(self, schema, root)
        self.name = root.get('value')

    def enum(self):
        return True


class Element(TypedContent):
    """
    Represents an (xsd) schema <xs:element/> node.
    """

    def __init__(self, schema, root):
        TypedContent.__init__(self, schema, root)
        a = root.get('form')
        if a is not None:
            self.form_qualified = ( a == 'qualified' )
        a = self.root.get('nillable')
        if a is not None:
            self.nillable = ( a in ('1', 'true') )
        self.implany()

    def implany(self):
        """
        Set the type as any when implicit.
        An implicit <xs:any/> is when an element has not
        body and no type defined.
        @return: self
        @rtype: L{Element}
        """
        if self.type is None and \
            self.ref is None and \
            self.root.isempty():
                self.type = self.anytype()
        return self

    def childtags(self):
        return ('attribute', 'simpleType', 'complexType', 'any',)

    def extension(self):
        for c in self.rawchildren:
            if c.extension():
                return True
        return False

    def restriction(self):
        for c in self.rawchildren:
            if c.restriction():
                return True
        return False

    def dependencies(self):
        deps = []
        midx = None
        if self.ref is not None:
            query = ElementQuery(self.ref)
            e = query.execute(self.schema)
            if e is None:
                #log.debug(self.schema)
                raise TypeNotFound(self.ref)
            deps.append(e)
            midx = 0
        return (midx, deps)

    def merge(self, other):
        SchemaObject.merge(self, other)
        self.rawchildren = other.rawchildren

    def description(self):
        return ('name', 'ref', 'type')

    def anytype(self):
        """ create an xsd:anyType reference """
        p,u = Namespace.xsdns
        mp = self.root.findPrefix(u)
        if mp is None:
            mp = p
            self.root.addPrefix(p, u)
        return ':'.join((mp, 'anyType'))


class Extension(SchemaObject):
    """
    Represents an (xsd) schema <xs:extension/> node.
    """

    def __init__(self, schema, root):
        SchemaObject.__init__(self, schema, root)
        self.ref = root.get('base')

    def childtags(self):
        return ('attribute',
                'attributeGroup',
                'sequence',
                'all',
                'choice',
                'group')

    def dependencies(self):
        deps = []
        midx = None
        if self.ref is not None:
            query = TypeQuery(self.ref)
            super = query.execute(self.schema)
            if super is None:
                #log.debug(self.schema)
                raise TypeNotFound(self.ref)
            if not super.builtin():
                deps.append(super)
                midx = 0
        return (midx, deps)

    def merge(self, other):
        SchemaObject.merge(self, other)
        filter = Filter(False, self.rawchildren)
        self.prepend(self.rawchildren, other.rawchildren, filter)

    def extension(self):
        return ( self.ref is not None )

    def description(self):
        return ('ref',)


class Import(SchemaObject):
    """
    Represents an (xsd) schema <xs:import/> node
    @cvar locations: A dictionary of namespace locations.
    @type locations: dict
    @ivar ns: The imported namespace.
    @type ns: str
    @ivar location: The (optional) location.
    @type location: namespace-uri
    @ivar opened: Opened and I{imported} flag.
    @type opened: boolean
    """

    locations = {}

    @classmethod
    def bind(cls, ns, location=None):
        """
        Bind a namespace to a schema location (URI).
        This is used for imports that don't specify a schemaLocation.
        @param ns: A namespace-uri.
        @type ns: str
        @param location: The (optional) schema location for the
            namespace.  (default=ns).
        @type location: str
        """
        if location is None:
            location = ns
        cls.locations[ns] = location

    def __init__(self, schema, root):
        SchemaObject.__init__(self, schema, root)
        self.ns = (None, root.get('namespace'))
        self.location = root.get('schemaLocation')
        if self.location is None:
            self.location = self.locations.get(self.ns[1])
        self.opened = False

    def open(self, options):
        """
        Open and import the refrenced schema.
        @param options: An options dictionary.
        @type options: L{options.Options}
        @return: The referenced schema.
        @rtype: L{Schema}
        """
        if self.opened:
            return
        self.opened = True
        #log.debug('%s, importing ns="%s", location="%s"', self.id, self.ns[1], self.location)
        result = self.locate()
        if result is None:
            if self.location is None:
                pass#log.debug('imported schema (%s) not-found', self.ns[1])
            else:
                result = self.download(options)
        #log.debug('imported:\n%s', result)
        return result

    def locate(self):
        """ find the schema locally """
        if self.ns[1] == self.schema.tns[1]:
            return None
        else:
            return self.schema.locate(self.ns)

    def download(self, options):
        """ download the schema """
        url = self.location
        try:
            if '://' not in url:
                url = urljoin(self.schema.baseurl, url)
            reader = DocumentReader(options)
            d = reader.open(url)
            root = d.root()
            root.set('url', url)
            return self.schema.instance(root, url, options)
        except TransportError:
            msg = 'imported schema (%s) at (%s), failed' % (self.ns[1], url)
            log.error('%s, %s', self.id, msg, exc_info=True)
            raise Exception(msg)

    def description(self):
        return ('ns', 'location')


class Include(SchemaObject):
    """
    Represents an (xsd) schema <xs:include/> node
    @ivar location: The (optional) location.
    @type location: namespace-uri
    @ivar opened: Opened and I{imported} flag.
    @type opened: boolean
    """

    locations = {}

    def __init__(self, schema, root):
        SchemaObject.__init__(self, schema, root)
        self.location = root.get('schemaLocation')
        if self.location is None:
            self.location = self.locations.get(self.ns[1])
        self.opened = False

    def open(self, options):
        """
        Open and include the refrenced schema.
        @param options: An options dictionary.
        @type options: L{options.Options}
        @return: The referenced schema.
        @rtype: L{Schema}
        """
        if self.opened:
            return
        self.opened = True
        #log.debug('%s, including location="%s"', self.id, self.location)
        result = self.download(options)
        #log.debug('included:\n%s', result)
        return result

    def download(self, options):
        """ download the schema """
        url = self.location
        try:
            if '://' not in url:
                url = urljoin(self.schema.baseurl, url)
            reader = DocumentReader(options)
            d = reader.open(url)
            root = d.root()
            root.set('url', url)
            self.__applytns(root)
            return self.schema.instance(root, url, options)
        except TransportError:
            msg = 'include schema at (%s), failed' % url
            log.error('%s, %s', self.id, msg, exc_info=True)
            raise Exception(msg)

    def __applytns(self, root):
        """ make sure included schema has same tns. """
        TNS = 'targetNamespace'
        tns = root.get(TNS)
        if tns is None:
            tns = self.schema.tns[1]
            root.set(TNS, tns)
        else:
            if self.schema.tns[1] != tns:
                raise Exception, '%s mismatch' % TNS


    def description(self):
        return ('location')


class Attribute(TypedContent):
    """
    Represents an (xsd) <attribute/> node
    """

    def __init__(self, schema, root):
        TypedContent.__init__(self, schema, root)
        self.use = root.get('use', default='')

    def childtags(self):
        return ('restriction',)

    def isattr(self):
        return True

    def get_default(self):
        """
        Gets the <xs:attribute default=""/> attribute value.
        @return: The default value for the attribute
        @rtype: str
        """
        return self.root.get('default', default='')

    def optional(self):
        return ( self.use != 'required' )

    def dependencies(self):
        deps = []
        midx = None
        if self.ref is not None:
            query = AttrQuery(self.ref)
            a = query.execute(self.schema)
            if a is None:
                #log.debug(self.schema)
                raise TypeNotFound(self.ref)
            deps.append(a)
            midx = 0
        return (midx, deps)

    def description(self):
        return ('name', 'ref', 'type')


class Any(Content):
    """
    Represents an (xsd) <any/> node
    """

    def get_child(self, name):
        root = self.root.clone()
        root.set('note', 'synthesized (any) child')
        child = Any(self.schema, root)
        return (child, [])

    def get_attribute(self, name):
        root = self.root.clone()
        root.set('note', 'synthesized (any) attribute')
        attribute = Any(self.schema, root)
        return (attribute, [])

    def any(self):
        return True


class Factory:
    """
    @cvar tags: A factory to create object objects based on tag.
    @type tags: {tag:fn,}
    """

    tags =\
    {
        'import' : Import,
        'include' : Include,
        'complexType' : Complex,
        'group' : Group,
        'attributeGroup' : AttributeGroup,
        'simpleType' : Simple,
        'list' : List,
        'element' : Element,
        'attribute' : Attribute,
        'sequence' : Sequence,
        'all' : All,
        'choice' : Choice,
        'complexContent' : ComplexContent,
        'simpleContent' : SimpleContent,
        'restriction' : Restriction,
        'enumeration' : Enumeration,
        'extension' : Extension,
        'any' : Any,
    }

    @classmethod
    def maptag(cls, tag, fn):
        """
        Map (override) tag => I{class} mapping.
        @param tag: An xsd tag name.
        @type tag: str
        @param fn: A function or class.
        @type fn: fn|class.
        """
        cls.tags[tag] = fn

    @classmethod
    def create(cls, root, schema):
        """
        Create an object based on the root tag name.
        @param root: An XML root element.
        @type root: L{Element}
        @param schema: A schema object.
        @type schema: L{schema.Schema}
        @return: The created object.
        @rtype: L{SchemaObject}
        """
        fn = cls.tags.get(root.name)
        if fn is not None:
            return fn(schema, root)
        else:
            return None

    @classmethod
    def build(cls, root, schema, filter=('*',)):
        """
        Build an xsobject representation.
        @param root: An schema XML root.
        @type root: L{sax.element.Element}
        @param filter: A tag filter.
        @type filter: [str,...]
        @return: A schema object graph.
        @rtype: L{sxbase.SchemaObject}
        """
        children = []
        for node in root.getChildren(ns=Namespace.xsdns):
            if '*' in filter or node.name in filter:
                child = cls.create(node, schema)
                if child is None:
                    continue
                children.append(child)
                c = cls.build(node, schema, child.childtags())
                child.rawchildren = c
        return children

    @classmethod
    def collate(cls, children):
        imports = []
        elements = {}
        attributes = {}
        types = {}
        groups = {}
        agrps = {}
        for c in children:
            if isinstance(c, (Import, Include)):
                imports.append(c)
                continue
            if isinstance(c, Attribute):
                attributes[c.qname] = c
                continue
            if isinstance(c, Element):
                elements[c.qname] = c
                continue
            if isinstance(c, Group):
                groups[c.qname] = c
                continue
            if isinstance(c, AttributeGroup):
                agrps[c.qname] = c
                continue
            types[c.qname] = c
        for i in imports:
            children.remove(i)
        return (children, imports, attributes, elements, types, groups, agrps)




#######################################################
# Static Import Bindings :-(
#######################################################
Import.bind(
    'http://schemas.xmlsoap.org/soap/encoding/',
    'suds://schemas.xmlsoap.org/soap/encoding/')
Import.bind(
    'http://www.w3.org/XML/1998/namespace',
    'http://www.w3.org/2001/xml.xsd')
Import.bind(
    'http://www.w3.org/2001/XMLSchema',
    'http://www.w3.org/2001/XMLSchema.xsd')

########NEW FILE########
__FILENAME__ = sxbuiltin
# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the 
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )

"""
The I{sxbuiltin} module provides classes that represent
XSD I{builtin} schema objects.
"""

from logging import getLogger
from suds import *
from suds.xsd import *
from suds.sax.date import *
from suds.xsd.sxbase import XBuiltin
import datetime as dt


log = getLogger(__name__)
    
    
class XString(XBuiltin):
    """
    Represents an (xsd) <xs:string/> node
    """
    pass

  
class XAny(XBuiltin):
    """
    Represents an (xsd) <any/> node
    """
    
    def __init__(self, schema, name):
        XBuiltin.__init__(self, schema, name)
        self.nillable = False
    
    def get_child(self, name):
        child = XAny(self.schema, name)
        return (child, [])
    
    def any(self):
        return True


class XBoolean(XBuiltin):
    """
    Represents an (xsd) boolean builtin type.
    """
    
    translation = (
        { '1':True,'true':True,'0':False,'false':False },
        { True:'true',1:'true',False:'false',0:'false' },
    )
        
    def translate(self, value, topython=True):
        if topython:
            if isinstance(value, basestring):
                return XBoolean.translation[0].get(value)
            else:
                return None
        else:
            if isinstance(value, (bool,int)):
                return XBoolean.translation[1].get(value)
            else:
                return value

   
class XInteger(XBuiltin):
    """
    Represents an (xsd) xs:int builtin type.
    """
        
    def translate(self, value, topython=True):
        if topython:
            if isinstance(value, basestring) and len(value):
                return int(value)
            else:
                return None
        else:
            if isinstance(value, int):
                return str(value)
            else:
                return value
            
class XLong(XBuiltin):
    """
    Represents an (xsd) xs:long builtin type.
    """
        
    def translate(self, value, topython=True):
        if topython:
            if isinstance(value, basestring) and len(value):
                return long(value)
            else:
                return None
        else:
            if isinstance(value, (int,long)):
                return str(value)
            else:
                return value

       
class XFloat(XBuiltin):
    """
    Represents an (xsd) xs:float builtin type.
    """
        
    def translate(self, value, topython=True):
        if topython:
            if isinstance(value, basestring) and len(value):
                return float(value)
            else:
                return None
        else:
            if isinstance(value, float):
                return str(value)
            else:
                return value
            

class XDate(XBuiltin):
    """
    Represents an (xsd) xs:date builtin type.
    """
        
    def translate(self, value, topython=True):
        if topython:
            if isinstance(value, basestring) and len(value):
                return Date(value).date
            else:
                return None
        else:
            if isinstance(value, dt.date):
                return str(Date(value))
            else:
                return value


class XTime(XBuiltin):
    """
    Represents an (xsd) xs:time builtin type.
    """
        
    def translate(self, value, topython=True):
        if topython:
            if isinstance(value, basestring) and len(value):
                return Time(value).time
            else:
                return None
        else:
            if isinstance(value, dt.date):
                return str(Time(value))
            else:
                return value


class XDateTime(XBuiltin):
    """
    Represents an (xsd) xs:datetime builtin type.
    """

    def translate(self, value, topython=True):
        if topython:
            if isinstance(value, basestring) and len(value):
                return DateTime(value).datetime
            else:
                return None
        else:
            if isinstance(value, dt.date):
                return str(DateTime(value))
            else:
                return value
            
            
class Factory:

    tags =\
    {
        # any
        'anyType' : XAny,
        # strings
        'string' : XString,
        'normalizedString' : XString,
        'ID' : XString,
        'Name' : XString,
        'QName' : XString,
        'NCName' : XString,
        'anySimpleType' : XString,
        'anyURI' : XString,
        'NOTATION' : XString,
        'token' : XString,
        'language' : XString,
        'IDREFS' : XString,
        'ENTITIES' : XString,
        'IDREF' : XString,
        'ENTITY' : XString,
        'NMTOKEN' : XString,
        'NMTOKENS' : XString,
        # binary
        'hexBinary' : XString,
        'base64Binary' : XString,
        # integers
        'int' : XInteger,
        'integer' : XInteger,
        'unsignedInt' : XInteger,
        'positiveInteger' : XInteger,
        'negativeInteger' : XInteger,
        'nonPositiveInteger' : XInteger,
        'nonNegativeInteger' : XInteger,
        # longs
        'long' : XLong,
        'unsignedLong' : XLong,
        # shorts
        'short' : XInteger,
        'unsignedShort' : XInteger,
        'byte' : XInteger,
        'unsignedByte' : XInteger,
        # floats
        'float' : XFloat,
        'double' : XFloat,
        'decimal' : XFloat,
        # dates & times
        'date' : XDate,
        'time' : XTime,
        'dateTime': XDateTime,
        'duration': XString,
        'gYearMonth' : XString,
        'gYear' : XString,
        'gMonthDay' : XString,
        'gDay' : XString,
        'gMonth' : XString,
        # boolean
        'boolean' : XBoolean,
    }
    
    @classmethod
    def maptag(cls, tag, fn):
        """
        Map (override) tag => I{class} mapping.
        @param tag: An xsd tag name.
        @type tag: str
        @param fn: A function or class.
        @type fn: fn|class.
        """
        cls.tags[tag] = fn

    @classmethod
    def create(cls, schema, name):
        """
        Create an object based on the root tag name.
        @param schema: A schema object.
        @type schema: L{schema.Schema}
        @param name: The name.
        @type name: str
        @return: The created object.
        @rtype: L{XBuiltin} 
        """
        fn = cls.tags.get(name)
        if fn is not None:
            return fn(schema, name)
        else:
            return XBuiltin(schema, name)

########NEW FILE########
__FILENAME__ = backend
from django.core.mail.backends.smtp import EmailBackend
from django.core.mail import get_connection
from django.conf import settings

class JumoEmailBackend(EmailBackend):
    def send_messages(self, email_messages):
        for msg in email_messages:
            super(JumoEmailBackend, self).send_messages([msg])
    def send(self, msg):
        super(JumoEmailBackend, self).send_messages([msg])



########NEW FILE########
__FILENAME__ = content
from mailer.models import Email

from etc.func import salted_hash
from etc.view_helpers import url_with_qs
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
import settings
import inspect
import random
import sys

class EmailTypes:
    JUMO_READER = 'news_email'
    FOLLOW = 'follow'
    MOST_ACTIVE = 'most_active'
    COMMENT = 'comment'
    RESET_PASSWORD = 'reset_password'
    CLAIM_ORG = 'claim_org'
    POSTED_ON_PROFILE = 'posted_on_profile'
    DONATION_FAILURE = 'donation_failure'

class EmailTextHTML(object):
    """Proxy to Email model"""
    headers = {}

    def __init__(self, type, user=None, email_address=None, subject='', update_next_email_time=False, **kw):
        hostname = settings.HTTP_HOST
        email_address = email_address if email_address else user.email
        unsub_code = salted_hash(email_address)
        kw.update(dict(hostname=hostname,
                       subject=subject,
                       user=user,
                       unsub_code=unsub_code))
        self.subject = subject
        self.template_args = kw
        self.text_content = render_to_string('email/txt/%s.txt' % type, kw)
        self.html_content = render_to_string('email/html/%s.html' % type, kw)
        self.user = user
        self.update_next_email_time=update_next_email_time

        # Lock that down
        if settings.EMAIL_REAL_PEOPLE or email_address.endswith('@jumo.com'):
            self.to = email_address
        else:
            self.to = 'jumodev@gmail.com'
        self.from_address = 'Jumo <no-reply@jumo.com>'

    def send(self):
        msg = Email(subject=self.subject, body=self.text_content, html=self.html_content,
                    user=self.user, recipient=self.to, from_address=self.from_address,
                    headers = self.headers)
        msg.send(self.update_next_email_time)

class JumoReaderEmail(EmailTextHTML):
    headers = {'X-SMTPAPI': '{"category": "Jumo Reader"}'}
    publication = 'reader'
    publication_id = 1
    user_sub_field = 'email_stream_frequency'

    def _get_random_stats(self, user):
        issues = [issue for issue in user.get_all_issues_following if issue.get_all_statistics]
        stats = [issue.get_all_statistics for issue in issues]
        flat_stats = [y for x in stats for y in x]

        random.shuffle(flat_stats)
        return flat_stats

    def __init__(self, user, **kw):
        random_stats = self._get_random_stats(user)[:1]
        super(JumoReaderEmail, self).__init__(type=EmailTypes.JUMO_READER,
                                              user=user,
                                              subject='Jumo Reader | Top News on the Issues You Care About',
                                              update_next_email_time=True,
                                              random_stats = random_stats,
                                              publication_id = self.publication_id,
                                              **kw)

class NotificationEmail(EmailTextHTML):
    """Important: make sure you add a type member to any subclasses"""
    publication = 'notifications'
    publication_id = 2

    def __init__(self, type, subject, user, entity, **kw):
        type='notifications/%s' % type
        super(NotificationEmail, self).__init__(type=type,
                                                user=user,
                                                subject=subject,
                                                entity=entity,
                                                publication_id = self.publication_id,
                                                **kw)

class FollowEmail(NotificationEmail):
    type = EmailTypes.FOLLOW

    def __init__(self, user, entity, **kw):
        super(FollowEmail, self).__init__(type = self.type,
                                          subject = '%s started following you on Jumo' % entity.get_name.title(),
                                          user = user,
                                          entity = entity)


class BadgeEmail(NotificationEmail):
    type = EmailTypes.MOST_ACTIVE
    def __init__(self, user, entity, **kw):
        super(BadgeEmail, self).__init__(type = self.type,
                                         subject = "You are now a top advocate for %s on Jumo" % entity.get_name.title(),
                                         user = user,
                                         entity = entity)

class CommentEmail(NotificationEmail):
    """
    e = EmailMessage('Jumo | %s commented on your Jumo story!' % request.user.get_name, 'Hi %s,\n\n%s commented on a story you posted on Jumo.\n\n"%s"\n\nView or reply by following the link below:\nhttp://jumo.com/story/%s\n\nThanks,\nThe Jumo Team' % (fi.poster.get_name, request.user.get_name, request.POST['comment'], fi.id), 'no-reply@jumo.com', [fi.poster.email])
                    e.send_now = True
                    e.send()
    """

    type = EmailTypes.COMMENT
    def __init__(self, user, entity, feed_item, comment):
        super(CommentEmail, self).__init__(type = self.type,
                                           subject = "%s commented on your Jumo story" % entity.get_name.title(),
                                           user = user,
                                           entity = entity,
                                           feed_item = feed_item,
                                           comment = comment)

class PostedOnProfileEmail(NotificationEmail):
    """
    Hi Kristen Titus,

    Matt Langer posted to your Jumo profile:

    "HEADLINE: Man eats hot dogs for dinner. Support childhood obesity."

    View or reply by following the link below:
    http://www.jumo.com/user/4cd8937ca70f66b06ac5b9d7

    Thanks,
    The Jumo Team
    """
    type = EmailTypes.POSTED_ON_PROFILE
    def __init__(self, user, entity, feed_item):
        super(PostedOnProfileEmail, self).__init__(type=self.type,
                                                   subject = "%s posted to your Jumo profile" % entity.get_name.title(),
                                                   user = user,
                                                   entity = entity,
                                                   feed_item = feed_item,
                                                   )


class ResetPasswordEmail(NotificationEmail):
    """"e = EmailMessage('Reset your password on Jumo.', 'Hi %s,\n\nClick the following link to be automatically logged into Jumo: http://jumo.com/reset_password/%s\n\nthe Jumo team' % (u.first_name, pr.uid), 'no-reply@jumo.com', [email])"""
    type = EmailTypes.RESET_PASSWORD
    def __init__(self, user, entity, password_reset_id):
        super(ResetPasswordEmail, self).__init__(type=self.type,
                                                 subject = "Reset your password on Jumo",
                                                 user = user,
                                                 entity = None,
                                                 password_reset_id = password_reset_id
                                                 )

class ClaimOrgEmail(NotificationEmail):
    """"e = EmailMessage('Become the administrator of %s on Jumo.' % o.get_name, 'Hi %s,\n\nClick the following link to verify your affiliation with %s: http://jumo.com/org/claim/%s/confirm/%s\n\nthe Jumo team' % (request.user.first_name, o.get_name, o.id, o.claim_token), 'no-reply@jumo.com', [info['email']])"""
    type = EmailTypes.CLAIM_ORG
    def __init__(self, user, entity, org_claim_token):
        super(ClaimOrgEmail, self).__init__(type=self.type,
                                                 subject = "Become the administrator of %s on Jumo" % entity.get_name.title(),
                                                 user = user,
                                                 entity = entity,
                                                 org_claim_token = org_claim_token,
                                                 )


class DonationFailureEmail(NotificationEmail):
    type = EmailTypes.DONATION_FAILURE
    def __init__(self, user, entity):
        super(DonationFailureEmail,self).__init__(type=self.type,
                                                  subject='Jumo Billing | Charge Unsucessful',
                                                  user = user,
                                                  entity = entity)


class JumoUpdateEmail(EmailTextHTML):
    publication = 'updates'
    publication_id = 3
    user_sub_field = 'enable_jumo_updates'


class UserDefinedEmail(EmailTextHTML):
    def __init__(self, type, user_or_donor, message, **kw):
        super(UserDefinedEmail, self).__init__(type=type,
                                               email_address=user_or_donor.email,
                                               subject=message.subject,
                                               publication_id = message.publication_id,
                                               message=message,
                                               **kw
                                               )


# Using inspect so we don't have to add new notifications manually
# Just make sure you add type to all new NotificationEmail classes
notifications = dict((cls.type, cls) for name, cls in inspect.getmembers(sys.modules[__name__])
                     if inspect.isclass(cls)
                     and issubclass(cls, NotificationEmail)
                     and hasattr(cls, 'type'))


pubs = dict((cls.publication, cls) for name, cls in inspect.getmembers(sys.modules[__name__])
                     if inspect.isclass(cls)
                     and issubclass(cls, EmailTextHTML)
                     and hasattr(cls, 'publication'))

########NEW FILE########
__FILENAME__ = jumoreader
from django.core.management.base import BaseCommand
from mailer.mgr import jumo_reader
from optparse import make_option


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
            make_option('--send',
                action='store_true',
                dest='send',
                default=False,
                help='Send emails or just show a log of pending emails (defaults to latter).'),
            make_option('-n',
                action='store',
                dest='num_users',
                default=None,
                help='Number of users to query'),
            )

    def handle(self, *args, **options):
        if not options.get('send'):
            pass
        else:
            jumo_reader(options.get('num_users'))

########NEW FILE########
__FILENAME__ = sendmail
from django.conf import settings
from django.core.management.base import BaseCommand
import logging
from mailer.models import Email
from optparse import make_option

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
            make_option('--send',
                action='store_true',
                dest='send',
                default=False,
                help='Send emails or just show a log of pending emails (defaults to latter).'),
            )

    def handle(self, *args, **options):
        if not options['send']:
            if settings.DEBUG:
                msgs = Email.objects.filter(sent = False).filter(recipient__icontains = '@jumo.com')
            else:
                msgs =[]
                #msgs = Email.objects.filter(sent = False)
            if not msgs:
                logging.info('No emails to send.')
                return
            for msg in msgs:
                logging.info('Emailing %s: %s' % (msg.recipient, msg.subject))
        else:
            pass
            #This isn't referencing anything...
            #send_mail()

########NEW FILE########
__FILENAME__ = messager_tasks
from celery.task import task
from donation.models import Donor
import logging
from message.models import Message, Publication
import socket


@task(ignore_result=True, rate_limit='10/s')
def _send_user_message(message_id, campaign_id):
    message = Message.get(message_id)
    pub_id = message.publication_id
    publication = Publication.get(pub_id)
    donor_ids = publication.get_subscribed_donor_ids()

    for donor_id in donor_ids:
        _email_donor.delay(donor_id, message.id)

def send_user_message(message_id):
    """ Make this call appear synchronous. Usage:

    send_user_message(1)

    Actually an asynchronous task
    """

    try:
        _send_user_message.delay(message_id)
    except socket.timeout:
        logging.error("Couldn't send message due to socket timeout. Rabbit may be down")

########NEW FILE########
__FILENAME__ = mgr
from datetime import datetime
from django.core.mail import EmailMessage
from django.conf import settings
import logging
from mailer.reader_tasks import send_jumo_reader_email
from users.models import User
"""
def send_mail():
    if settings.DEBUG:
        msgs = Email.objects.filter(sent = False).filter(recipient__icontains = '@jumo.com')
    else:
        msgs = Email.objects.filter(sent = False)
    if not msgs:
        logging.info('No email to send.')
    while True:
        if settings.DEBUG:
            try:
                msg = Email.objects.filter(sent = False).filter(recipient__icontains = '@jumo.com')[0]
                _mark_as_sent(msg)
                try:
                    e = EmailMessage(msg.subject, msg.body, 'no-reply@jumo.com', [msg.recipient])
                    send_msg(e)
                except:
                    continue
            except:
                break
        else:
            try:
                msg = Email.objects.filter(sent = False)[0]
                _mark_as_sent(msg)
                try:
                    e = EmailMessage(msg.subject, msg.body, 'no-reply@jumo.com', [msg.recipient])
                    send_msg(e)
                except:
                    continue
            except:
                break
"""


def jumo_reader(num_users=None):
    users_to_email =  User.objects.filter(is_active=True, next_email_time__lte=datetime.now(), email_stream_frequency__gt=0)
    if num_users is None:
        users_to_email = users_to_email.iterator()
    else:
        users_to_email = users_to_email.order_by('?')[:num_users]

    #for user in users_to_email.iterator():
    for user in users_to_email:
        try:
            send_jumo_reader_email.delay(user, [])
        except Exception, e:
            logging.error('Uh-oh, had an issue sending an e-mail to user %s' % user.id, e)

########NEW FILE########
__FILENAME__ = models
from datetime import datetime, timedelta
from django.core.mail import EmailMessage
from django.core.mail.message import EmailMultiAlternatives
from django.db import models, transaction
from users.models import User


class Unsubscribe(models.Model):
    email = models.CharField(max_length=200, db_column='email')
    publication_id = models.IntegerField(db_column='publication_id')
    date_created = models.DateTimeField(default=datetime.now(), db_column='date_created')

    class Meta:
        db_table = 'unsubscribes'

class Email(models.Model):
    sent = models.BooleanField(default = False, db_column='sent')
    user = models.ForeignKey(User, db_column='user_id', related_name='emails', null=True)
    from_address = None
    recipient = models.EmailField(db_column='recipient')
    headers = None
    subject = models.CharField(max_length = 255, db_column='subject')
    body = ""
    html = ""
    date_created = models.DateTimeField(default = datetime.now, db_column='date_created')
    date_sent = models.DateTimeField(blank = True, null = True, db_column='date_sent')

    _field_set = None

    @classmethod
    def get_field_set(cls):
        if not cls._field_set:
            cls._field_set = set([field.name for field in cls._meta.fields])
        return cls._field_set

    def __init__(self, **kw):
        """
        So the object's constructor can behave like a regular model but we don't have
        to actually write all the data to the DB
        """
        fields = self.get_field_set().intersection(kw)
        new_args = dict((field, kw.pop(field)) for field in fields)
        super(Email, self).__init__(**new_args)

        user_or_donor = kw.get('user')
        if hasattr(user_or_donor, 'user'):
            kw['user'] = kw['user'].user

        for k, v in kw.iteritems():
            setattr(self, k, v)


    class Meta:
        db_table = 'mailer_email'

    @transaction.commit_on_success()
    def send(self, update_next_email_time=False):
        msg = None
        if self.html:
            msg = EmailMultiAlternatives(self.subject, self.body, self.from_address, to=[self.recipient], headers = self.headers)
            msg.attach_alternative(self.html, "text/html")
        else:
            msg = EmailMessage(self.subject, self.body, self.from_address, [self.recipient])
        self.sent = True
        now = datetime.utcnow()
        self.date_sent=now
        if update_next_email_time:
            self.user.next_email_time = datetime.date(now + timedelta(seconds=self.user.email_stream_frequency))
            self.user.save()
        self.save()
        msg.send()

########NEW FILE########
__FILENAME__ = notification_tasks
from celery.task import task
from donation.models import Donor
import logging
from mailer.content import notifications, EmailTypes #This is being imported from this module by many others.
import socket

NOTIFICATIONS_PUB = 2

@task(ignore_result=True, default_retry_delay=10)
def _send_notification(type, user, entity, force_send=False, **kw):
    email_cls = notifications.get(type)

    # Both donor and user have this method
    if (force_send or user.is_subscribed_to(NOTIFICATIONS_PUB)) and (isinstance(user, Donor) or user.is_active):
        msg = email_cls(user=user, entity=entity, **kw)
        try:
            msg.send()
            logging.info("Sent message to %s" % user.email)
            return user.email
        except Exception, exc:
            logging.exception('Got an error while sending e-mail: %s' % exc)
            _send_notification.retry(exc=exc)

    else:
        logging.info("User is unsubscribed, not sending")

def send_notification(type, user, entity, **kw):
    try:
        _send_notification.delay(type, user, entity, **kw)
    except socket.timeout:
        logging.error("Couldn't send message due to socket timeout. Rabbit may be down")

########NEW FILE########
__FILENAME__ = reader_tasks
from celery.task import task
from datetime import datetime
import logging
from mailer.content import JumoReaderEmail

@task(rate_limit='100/s')
def send_jumo_reader_email(user, most_popular_stories):
    logging.debug('Getting feed stream for user: %s' % user.id)
    days_back = user.email_stream_frequency/86400

    logging.debug('Found %s feed items' % len(feed_items))
    if len(feed_items) < 3:
        # feed_items = (feed_items + most_popular_stories)[:3]
        logging.warning("You no give me three quality stories, I no send e-mail...")
        return

    logging.debug('Generating template for message...')
    msg = JumoReaderEmail(entity=user,
                          user=user,
                          current_user=user,
                          feed_items=[],
                          feed_stream=None,
                          current_time=datetime.now()
                          )

    logging.debug('Cool! Generated.')
    msg.send()
    logging.debug('Sent message to %s' % user.email)
    return user.email

########NEW FILE########
__FILENAME__ = tests

from etc.func import salted_hash
from etc.tests import ViewsBaseTestCase
from message.models import Subscription

class MailerTestCase(ViewsBaseTestCase):
    #Don't have campaign email subscribe/unsubscribe anymore.
    #Need to write new tests.
    pass

########NEW FILE########
__FILENAME__ = views
from datetime import datetime
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, Http404
from donation.models import Donor
from etc import cache
from etc.func import salted_hash
from etc.decorators import AccountRequired
from etc.view_helpers import render
from mailer.models import Unsubscribe, transaction
from mailer.content import pubs, JumoReaderEmail
from message.models import Publication, Subscription
from users.models import User


@transaction.commit_on_success()
def unsubscribe(request):
    id = request.GET['id']
    id_type = request.GET.get('id_type', 'user')
    code = request.GET['code']
    pub = request.GET.get('pub')
    pub_id = request.GET.get('pub_id')

    if id_type == 'user':
        try:
            user = User.objects.get(id=id, is_active=True)
        except ObjectDoesNotExist:
            raise Http404
    elif id_type == 'donor':
        try:
            user = Donor.objects.get(id=id)
        except ObjectDoesNotExist:
            raise Http404
    else:
        raise Http404

    expected_code = salted_hash(user.email)
    if code <> expected_code:
        raise Http404

    if pub:
        pub = pubs[pub]
        publication_id = pub.publication_id
    elif pub_id:
        publication_id = pub_id
    else:
        raise Http404

    pub = Publication.objects.get(id=publication_id)

    unsub, created = Unsubscribe.objects.get_or_create(email=user.email, publication_id=pub.id)

    if pub.user_settings_field:
        # Update user table anyway to allow for resubscription, etc.
        setattr(user, pub.user_settings_field, 0)
        user.save()
        cache.bust_on_handle(user, user.username)
    else:
        try:
            if id_type=='donor':
                sub = Subscription.objects.get(donor=user.id, publication=pub.id)
            elif id_type=='user':
                sub = Subscription.objects.get(user=user.id, publication=pub.id)
            sub.subscribed=False
            sub.save()
            #cache.bust([user, sub])
        except ObjectDoesNotExist:
            raise Http404

    return render(request, 'etc/unsubscribe.html', {'created': created,
                     'user': user,})

@AccountRequired
def jumo_reader(request, username):
    try:
        user = User.objects.get(username = username, is_active=True)
    except ObjectDoesNotExist:
        raise Http404

    if request.user.username <> user.username:
        raise Http404

    msg = JumoReaderEmail(entity=user,
                          user=user,
                          current_user=user,
                          feed_items=[],
                          feed_stream=None,
                          current_time=datetime.now()
                          )

    if 'text' in request.path:
        return HttpResponse(msg.text_content)
    else:
        return HttpResponse(msg.html_content)

@AccountRequired
def notification_email(request, username):
    user = User.objects.get(username = username, is_active=True)
    return render(request, "email/html/notifications/reset_password.html", {
            'hostname' : settings.HTTP_HOST,
            'subject': "You have just become a top advocate for FOO BAR on Jumo.",
            'user' : user,
            'entity' : user})

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
__FILENAME__ = models
from django.db import models
from users.models import User
from org.models import Org
from django.db import transaction
from django.db.models import Q
from etc import cache

from django.db.models.query import QuerySet
from django.db.models import F
from django.db.models.loading import get_model

from datetime import datetime

# Constant publication_id for notifications
NOTIFICATIONS_PUB = 2

class Subscription(models.Model):
    id = models.AutoField(db_column='subscription_id', primary_key=True)
    user = models.ForeignKey(User, db_column='user_id', null=True)
    donor = models.ForeignKey('donation.Donor', db_column='donor_id', null=True)
    publication = models.ForeignKey('message.Publication', db_column='publication_id')
    subscribed = models.BooleanField(db_column='subscribed')

    class Meta:
        db_table = 'subscriptions'

    @classmethod
    def get_or_create(cls, pub_id=None, donor=None, user=None):
        sub = None
        created = False
        try:
            if (user or donor.user) and donor:
                sub = Subscription.objects.get(Q(donor=donor) | Q(user=donor.user), publication=pub_id)
            elif user or donor.user:
                u = user or donor.user
                sub = Subscription.objects.get(user=u, publication=pub_id)
            else:
                sub = Subscription.objects.get(donor=donor, publication=pub_id)
        except Subscription.DoesNotExist:
            sub = Subscription(user=user or donor.user, donor=donor, publication_id=pub_id, subscribed=True)
            created = True
        else:
            # This is the reason I'm overriding get_or_create
            # The subscription exists, but set the user at least in case they've since become one
            sub.user = user or donor.user
        return sub, created

class NoMessagesRemaining(Exception):
    pass

class Publication(models.Model):
    id = models.AutoField(db_column='publication_id', primary_key=True)
    title = models.CharField(max_length=255, db_column='title')
    default_subject = models.CharField(max_length=255, db_column='default_subject')
    is_staff_pub = models.BooleanField(db_column='is_staff_publication')
    user_settings_field = models.CharField(max_length=255, db_column='user_settings_field', null=True)
    max_subscriber_emails = models.IntegerField(db_column='max_subscriber_emails')
    subscriber_emails_sent = models.IntegerField(db_column='subscriber_emails_sent', default=0)


    users = models.ManyToManyField(User, through='Subscription', null=True, related_name='subscriptions')
    donors = models.ManyToManyField('donation.Donor', through='Subscription', null=True, related_name='subscriptions')
    admins=models.ManyToManyField(User, through='PubAdmin', null=True, related_name='publications_admin_for')

    class Meta:
        db_table = 'publications'

    @classmethod
    def get(cls, id, force_db=False):
        if force_db:
            return Message.objects.get(id=id)
        return cache.get(cls, id)



    def subscribe(self, donor, resubscribe=False):
        # Check to see they're not already subscribed
        sub, created = Subscription.get_or_create(donor=donor, pub_id=self.id)
        # In case the user has since been created
        sub.user=donor.user

        if created or resubscribe:
            sub.subscribed=True  # Otherwise use whatever the previous subscription status was

        sub.save()
        return sub, created

    def get_subscribed_user_ids(self):
        """
        # Not using the user_settings_field part yet, just playing with the idea,
        # not sure I want the multiget to get every single user in one go for Jumo Reader though
        if self.user_settings_field:
            settings_field = self.user_settings_field
            val = True
            if settings_field == 'email_stream_frequency':
                settings_field = self.user_settings_field + '__gt'
                val = 0
            return User.objects.filter(**{settings_field: val, 'is_active': True}).iterator()
        """

        # Coerces the returned rows into a flat list, and returns an iterator over them.
        # so return value should be like [1, 2, 4, 4389, 23895,98359]
        return Subscription.objects.filter(publication=self,
                                           subscribed=True).values_list('user_id', flat=True).iterator()

    def get_subscribed_donor_ids(self):
        # Coerces the returned rows into a flat list, and returns an iterator over them.
        # so return value should be like [1, 2, 4, 4389, 23895,98359]
        return Subscription.objects.filter(publication=self,
                                           subscribed=True).values_list('donor_id', flat=True).iterator()

    @property
    @cache.collection_cache('users.User', '_admin_ids')
    def get_admins(self):
        return self.admins.all()

class PubAdmin(models.Model):
    id = models.AutoField(db_column='pub_admin_id', primary_key=True)
    user = models.ForeignKey(User, db_column='user_id')
    publication = models.ForeignKey(Publication, db_column='publication_id')

    class Meta:
        db_table = 'pub_admins'

class Message(models.Model):
    id = models.AutoField(db_column='message_id', primary_key=True)
    publication = models.ForeignKey(Publication, db_column='publication_id')
    subject = models.CharField(max_length=255, db_column='subject')
    confirmed = models.BooleanField(db_column='confirmed')
    sent = models.BooleanField(db_column='sent')
    date_created = models.DateTimeField(db_column='date_created', default=datetime.utcnow)

    class Meta:
        db_table = 'messages'

    @property
    def get_url(self):
        return '/message/%s' % self.subject


    @classmethod
    def get(cls, id, force_db=False):
        if force_db:
            return Message.objects.get(id=id)
        return cache.get(cls, id)

    @classmethod
    def multiget(cls, ids, force_db=False):
        if force_db:
            # For sorting
            message_dict = dict((message.id, message) for message in Message.objects.filter(id__in=ids))
            return [message_dict[id] for id in ids]
        return cache.get(cls, ids)

    @classmethod
    def create(cls, publication_id, subject, email=True):
        message = Message(publication_id=publication_id, subject=subject, confirmed=False, sent=False)
        if not email:
            # GAHHH do something different here
            message.confirmed = True
            message.sent = True
        message.save()
        return message

    @classmethod
    @transaction.commit_on_success()
    def confirm(cls, message_id):
        message = Message.objects.get(id=message_id)
        # Increment subscriber_emails_sent for the publication by 1 atomically
        # Return the rows affected by the update. Since we've included the "< max_subscriber_emails" condition
        # in the WHERE clause, the update would not change any rows for a campaign that has used up all its e-mails
        affected = Publication.objects.filter(id=message.publication_id, subscriber_emails_sent__lt=F('max_subscriber_emails')).update(subscriber_emails_sent = F('subscriber_emails_sent') + 1)
        if not affected:
            raise NoMessagesRemaining('This publication has no messages remaining')     # Rolls back the transaction
        cache.bust(message.publication)

        message.confirmed=True
        message.save()
        return message

########NEW FILE########
__FILENAME__ = tests


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = classifier
'''
Created on Jul 20, 2011

@author: al
'''

from collections import defaultdict, Hashable

features = defaultdict(set)
defined_features = set()

def register_feature(cls, obj):
    # properties
    if hasattr(obj, 'fget'):
        name = obj.fget.__name__
    # classmethods
    elif hasattr(obj, '__func__'):
        name = obj.__func__.__name__
    # instancemethods
    else:
        name = obj.__name__

    features[cls].add(name)

def feature(f):
    defined_features.add(f)
    return f

class ClassifierMeta(type):
    def __init__(cls, name, bases, dict):
        super(ClassifierMeta, cls).__init__(name, bases, dict)
        for name, obj in dict.iteritems():
            if isinstance(obj, Hashable) and obj in defined_features:
                register_feature(cls, obj)

class Classifier(object):
    __metaclass__ = ClassifierMeta

    @classmethod
    def get_features(cls):
        return features[cls].copy()

    @classmethod
    def select_feature(cls, instance, attr):
        try:
            val = getattr(instance, attr)
        except AttributeError:
            try:
                val = getattr(cls, attr)
            except AttributeError:
                raise Exception('Attribute "%s" was not found on either the training instance "%s" or class "%s"' % (attr, instance, cls))

        if callable(val):
            return val(instance)
        else:
            return val

    @classmethod
    def train(cls, data):
        training_instances = cls.prepare_data(data)
        cls.model = cls.create_model(training_instances)
        return cls.model

    @classmethod
    def prepare_data(cls, data):
        """ No-op, override as needed """
        return data

    @classmethod
    def create_model(cls, training_instances):
        raise NotImplementedError('Children must implement their own')

    @classmethod
    def get_model(cls):
        raise NotImplementedError('Children must implement their own')
########NEW FILE########
__FILENAME__ = decision_tree
'''
Created on Jul 15, 2011

@author: al
'''

from collections import defaultdict, deque, OrderedDict, Hashable
from itertools import chain
from classifier import *
import math
import logging
import os

log = logging.getLogger('miner.classifiers')


class nested_dict(dict):
    def __getitem__(self, keys):
        d = self
        if hasattr(keys, 'items'):
            keys = keys.items()
        if not hasattr(keys, '__iter__'):
            return dict.__getitem__(self, keys)
        keys = chain(*keys)
        for key in keys:
            d = dict.__getitem__(d, key)
        return d

    def __setitem__(self, keys, value):
        d = self
        if not hasattr(keys, '__iter__'):
            dict.__setitem__(self, keys, value)
            return

        if hasattr(keys, 'items'):
            keys = keys.items()

        keys = list(chain(*keys))

        for i, key in enumerate(keys[:-1]):
            try:
                d = d[key]
            except KeyError:
                dict.__setitem__(d, key, {})
                d = d[key]
                continue

        dict.__setitem__(d, keys[-1], value)

class DecisionTree(Classifier):

    @classmethod
    def create_model(cls, training_instances):
        Q = deque([None])
        working_set = []
        current_decision = None

        features = cls.get_features()

        def entropy(cat_totals):
            total = sum(cat_totals)
            return sum([ -(float(cat_total)/total) * math.log((float(cat_total)/total), 2)
                            for cat_total in cat_totals])

        ret = nested_dict()

        attr_index = defaultdict(lambda: defaultdict(set))
        for instance in training_instances:
            for attr in features:
                val = cls.select_feature(instance, attr)
                attr_index[attr][val].add(instance)

        # Iterative breadth-first search algorithm
        while Q:
            conditions = Q.popleft()
            # Initial node
            if conditions is None:
                conditions = OrderedDict()
                base_working_set = set(training_instances)

            if current_decision:
                features.remove(current_decision)

            if not features:
                break

            # Triple default dict OH YEAAAAAH
            classification_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

            # Working set would be all items given the conditions of this iteration (e.g. country_is_us=False, us_city=True)
            working_set = base_working_set
            for attr, val in conditions.iteritems():
                items = attr_index[attr][val]
                working_set = working_set & items

            for instance in working_set:
                for attr in features:
                    val = cls.select_feature(instance, attr)
                    classification_dict[attr][val][instance.label] += 1

            """
            classification_dict looks like this:

            {'country_is_us':
                {True: {'US': 9,
                        'International': 0
                        },
                 False: {'US': 1,
                         'International': 8}
                 }
            }
            """

            info_gains = defaultdict(float)

            for key, value_dict in classification_dict.iteritems():
                total_info = defaultdict(int)
                for distinct_value, class_dict in value_dict.iteritems():
                    info_gains[key] += entropy(class_dict.values())
                    for label, num in class_dict.iteritems():
                        total_info[label] += num

                total_info_gain = entropy(total_info.values())
                info_gains[key] = total_info_gain - info_gains[key]

            current_decision = sorted(info_gains, key=lambda attr: info_gains[attr], reverse=True)[0]

            for attr in attr_index[current_decision]:
                labels = classification_dict[current_decision][attr].keys()
                new_conditions = conditions.copy()
                new_conditions[current_decision] = attr
                if len(labels) > 1:
                    Q.append(new_conditions)
                elif len(labels) == 1:
                    ret[new_conditions] = labels[0]

        return ret


    @classmethod
    def classify(cls, node):
        if not hasattr(cls, 'decision_tree'):
            current_object = cls.get_model()
        else:
            current_object = cls.model

        if not current_object:
            log.warn("No decision tree model available, could not classify object '%s'" % unicode(node))
            return None

        node = cls(node)
        while True:
            attr = current_object.keys()[0]
            val = cls.select_feature(node, attr)
            current_object = current_object[attr].get(val)
            if current_object is None:
                log.info("Couldn't classify object: %s, attribute '%s' with value '%s' does not exist in decision tree" % (cls.__name__, attr, val))
                return None
            elif isinstance(current_object, basestring):
                log.debug("Successfully classified object: %s as '%s'" % (unicode(node), current_object))
                return current_object

__all__ = ['DecisionTree', 'feature', 'nested_dict']
########NEW FILE########
__FILENAME__ = issues_from_text
#!/usr/bin/env python

from django.core.management import setup_environ
import settings
setup_environ(settings)

from django.db.models.loading import cache as model_cache
model_cache._populate()

from issue.models import Issue
from related_search import RelatedSearchClassifier
    
def train_issue_classifier(results_file):
    issue_words = []
    
    active_issues = dict((i.id, i) for i in Issue.objects.filter(is_active=True))
        
    for row in results_file:
        row_values = [eval(value) for value in  row.split('\t')]
        issue_id, features = row_values[1], row_values[2:]
        if issue_id in active_issues:
            issue_words.append((features, active_issues[issue_id].name))
                
    id = 0
    word_to_id = {}
    id_to_word = {}
    
    corpus =  []
    classifications = []
    
    for features, classification in issue_words:
        row = []
        for word, cnt in features:
            if word not in word_to_id:
                word_to_id[word] = id
                id_to_word[id] = word
                id += 1

            row.append((word_to_id[word], cnt))
        corpus.append(row)
        classifications.append(classification)
        
    del issue_words
        
    classifier = RelatedSearchClassifier.train(corpus, classifications, id_to_word)       
                                
    return classifier

if __name__ == '__main__':
    import os, sys
    import cPickle as pickle
    
    if len(sys.argv) < 2:
        print """Usage: python issues_from_text.py results_file"""
        sys.exit()   
    results_file = sys.argv[1]
    classifier = train_issue_classifier(open(results_file, 'r'))
    classifier.save_model()
########NEW FILE########
__FILENAME__ = location_tagger
#!/usr/bin/env python
'''
Created on Jul 13, 2011

@author: al
'''

from decision_tree import *
from collections import defaultdict
import re
import cPickle as pickle

import logging
log = logging.getLogger('miner.classifiers')

Ambiguous = 'ambiguous'

class LocationClassifier(DecisionTree):
    cache_key = 'decision_trees/location_classifier'

    US = 'US'
    INTERNATIONAL = 'International'

    countries = set()

    us_cities = set()
    foreign_cities = set()

    us_states_verbose = set(['alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado', 'connecticut',
                             'delaware', 'district of columbia', 'florida', 'georgia', 'hawaii', 'idaho', 'illinois',
                             'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana', 'maine', 'maryland', 'massachusetts',
                             'michigan', 'minnesota', 'mississippi', 'missouri', 'montana', 'nebraska', 'nevada',
                             'new hampshire', 'new jersey', 'new mexico', 'new york', 'north carolina', 'north dakota',
                             'ohio', 'oklahoma', 'oregon', 'pennsylvania', 'rhode island', 'south carolina', 'south dakota',
                             'tennessee', 'texas', 'utah', 'vermont', 'virginia', 'washington', 'west virginia',
                             'wisconsin', 'wyoming'])

    us_states = set(['AK', 'AL', 'AR', 'AZ', 'CA', 'CO', 'CT', 'DC', 'DE',
              'FL', 'GA', 'HI', 'IA', 'ID', 'IN', 'IL', 'KS', 'KY',
              'LA', 'MA', 'MD', 'ME', 'MI', 'MN', 'MO', 'MS', 'MT',
              'NC', 'ND', 'NE', 'NH', 'NJ', 'NM', 'NV', 'NY', 'OH',
              'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT',
              'VA', 'VT', 'WA', 'WI', 'WV', 'WY'])

    us_postal_code_regex = re.compile('^[\d]{5}(-[\d]{4})?$')

    def __init__(self, inst):
        self.inst = inst

    @property
    def label(self):
        return self.inst.classification

    @feature
    @property
    def country_is_us(self):
        if self.inst.country_name == 'United States':
            return True
        elif self.inst.country_name:
            return False
        else:
            return None

    @feature
    @property
    def us_state(self):
        if self.inst.region and self.inst.region.strip().upper() in self.us_states:
            return True
        elif self.inst.region:
            return False
        else:
            return None

    @feature
    @property
    def us_city(self):
        if not self.inst.locality:
            return None

        is_us = self.inst.locality.strip().lower() in self.foreign_cities
        is_foreign = self.inst.locality.strip().lower() in self.foreign_cities

        if is_us and not is_foreign:
            return True
        elif is_foreign and not is_us:
            return False
        elif is_foreign and is_us:
            return Ambiguous
        else:
            return None

    @feature
    @property
    def us_postal_code(self):
        if not self.inst.postal_code:
            return None
        else:
            return self.us_postal_code_regex.match(self.inst.postal_code.strip()) is not None

    @feature
    @property
    def name_is_us(self):
        name = (self.inst.name or '').strip().lower()
        if not name:
            return None
        if name == 'united states' or name in self.us_states_verbose:
            return True
        elif name in self.countries:
            return False
        else:
            return None

    @classmethod
    def prepare_data(cls, data):
        for location in data:
            if location.classification == LocationClassifier.US and location.locality:
                cls.us_cities.add(location.locality.strip().lower())
            elif location.classification == LocationClassifier.INTERNATIONAL and location.locality:
                cls.foreign_cities.add(location.locality.strip().lower())

            if location.country_name:
                cls.countries.add(location.country_name.strip().lower())

        training_data = [LocationClassifier(location) for location in data]
        return training_data

    @classmethod
    def get_model(cls):
        from django.core.cache import cache
        return cache.get(cls.cache_key)

def tag_unknown_locations_and_publish():
    import sys, os
    sys.path.append(os.path.realpath(os.sep.join([os.path.dirname(__file__), os.pardir, os.pardir])))
    from django.core.management import setup_environ
    import settings
    setup_environ(settings)

    from django.db.models.loading import cache as model_cache
    model_cache._populate()

    from django.core.cache import cache

    from entity_items.models.location import Location
    classified = Location.objects.filter(classification__isnull=False)

    decision_tree = LocationClassifier.train(classified)
    log.info("Decision tree: %s" % decision_tree)
    if decision_tree:
        cache.set(LocationClassifier.cache_key, decision_tree.copy())    # Have to copy it so it's a normal dict again

    unclassified = Location.objects.filter(classification__isnull=True)
    for loc in unclassified:
        classification = LocationClassifier.classify(loc)
        if classification:
            log.info("Saving location")
            loc.classification = classification
            loc.save()

if __name__ == '__main__':
    log.setLevel(logging.INFO)
    tag_unknown_locations_and_publish()

########NEW FILE########
__FILENAME__ = related_search
import numpy

from scipy.sparse import coo_matrix, csc_matrix
from scikits.learn.naive_bayes import MultinomialNB
from scikits.learn.externals import joblib
from miner.text.util import search_features

import os

import settings
import urlparse
import hashlib
import cPickle as pickle
import itertools

parsed_cache_url = urlparse.urlparse(settings.CACHE_BACKEND)
cache_url = parsed_cache_url.netloc

import pylibmc

classification_dict_cache_key = 'miner/related_search/classifications'
num_features_key = 'miner/related_search/num_features'

def hash_key(feature):
    if hasattr(feature, '__iter__'):
        return 'miner/related_search/bigram_ids/%s' % hashlib.md5('|*|'.join(feature)).hexdigest()
    else:
        return 'miner/related_search/unigram_ids/%s' % hashlib.md5(feature).hexdigest()

def feature_cache_key(feature):
    if hasattr(feature, '__iter__'):
        return 'miner/related_search/bigram_ids/%s' % ''.join(feature)
    else:
        return 'miner/related_search/unigram_ids/%s' % feature
        
def get_cache():
    return pylibmc.Client([cache_url], binary=True,
                               behaviors={'tcp_nodelay': True,
                                          'ketama': True})    

class RelatedSearchClassifier(object):
    
    model_file = 'related_search_classifier.model'
    features_file = 'features.dict'
    classifications_file = 'classifications.dict'
    
    def create_model(self, corpus, classifications, id_to_feature):        
        self.id_to_feature = id_to_feature

        # This it the kind of odd way scikits.learn returns probability distributions
        # It will be a numpy array of probabilities of each class. Each index corresponds
        # to the same index in an array of alphanumerically-sorted classifications
        classification_dict = dict(enumerate(sorted(set(classifications))))
        feature_to_id = dict((hash_key(feature), id) for id, feature in id_to_feature.iteritems())
        self.num_features = len(feature_to_id)

        memcache = get_cache()

        # Cache the whole class dict, it's small (length = num_issues) and will be used every time
        memcache.set(classification_dict_cache_key, classification_dict)
        
        # Keep this count around since we'll only be pulling down the features we need from memcache (no len)
        memcache.set(num_features_key, self.num_features) 

        # These are important, and while memcache will be the primary store,
        # save them to disk so we can reload them later it memcache dies
        pickle.dump(feature_to_id, open(os.sep.join([settings.RELATED_SEARCH_MODEL_BASE_DIR, self.features_file ]), 'w'))
        pickle.dump(classification_dict, open(os.sep.join([settings.RELATED_SEARCH_MODEL_BASE_DIR, self.classifications_file ]), 'w'))

        memcache.set_multi(feature_to_id)

        num_docs = len(corpus)
        num_features = len(id_to_feature)
        num_nonzeros = sum([len(doc) for doc in corpus])
                
        current_position, index_pointer = 0, [0]
                
        indices = numpy.empty((num_nonzeros,), dtype=numpy.int32)
        data = numpy.empty((num_nonzeros,), dtype=numpy.int32)
        for doc_num, doc in enumerate(corpus):
            next_position = current_position + len(doc)
            indices[current_position : next_position] = [feature_id for feature_id, _ in doc]
            data[current_position : next_position] = [cnt for feature_id, cnt in doc]
            index_pointer.append(next_position)
            current_position = next_position

        del corpus

        matrix = csc_matrix((data, indices, index_pointer), shape=(num_features, num_docs), dtype=numpy.int32)
        
        matrix = matrix.transpose()
        
        # Since the number of news stories about a particular issue 
        #For the purposes of this, assume there is no prior probability
        # e.g. if we have published more stories about Democracy, that doesn't mean
        # that democracy is any more relevant to a user's search than the environment
        model = MultinomialNB(fit_prior=False)
        classifications = numpy.array(classifications)

        model.fit(matrix, classifications)
        
        del matrix
        
        self.model =  model
        return self
        
    @classmethod
    def train(cls, corpus, classifications, id_to_feature):
        return RelatedSearchClassifier().create_model(corpus, classifications, id_to_feature)
        
    def save_model(self):
        joblib.dump(self.model, os.sep.join([settings.RELATED_SEARCH_MODEL_BASE_DIR, self.model_file ]) )

    @classmethod
    def get_model(cls):
        classifier = RelatedSearchClassifier()
        classifier.model = joblib.load(os.sep.join([settings.RELATED_SEARCH_MODEL_BASE_DIR, cls.model_file]), mmap_mode='r')
        mc = get_cache()
        classifier.classification_dict = mc.get(classification_dict_cache_key)
        classifier.num_features = mc.get(num_features_key)
        return classifier

    def classify(self, words):
        memcache = get_cache()
        doc_features = search_features(words)
        row_vals = []
        
        cache_keys = [hash_key(feature) for feature in doc_features]
        row_vals.extend(memcache.get_multi(cache_keys).values())        
        
        # Words are unknown
        if not row_vals:
            return []
        rows = numpy.array(row_vals)
        cols = numpy.array([0 for row in row_vals])
        data = numpy.array([1 for row in row_vals])
        matrix = csc_matrix( (data, (rows, cols)), shape=(self.num_features, 1) )
        matrix = matrix.transpose()
        probs = self.model.predict_log_proba(matrix)
        if not probs.any() or len(probs)==0:
            return []

        return sorted( [(self.classification_dict.get(idx), prob) for idx, prob in enumerate(probs[0])], key=lambda item: item[1], reverse=True)[:5]

########NEW FILE########
__FILENAME__ = user_is_org
#!/usr/bin/env python

'''
Created on Jul 20, 2011

@author: al
'''

import sys, os
sys.path.append(os.path.realpath(os.sep.join([os.path.dirname(__file__), os.pardir, os.pardir])))
from django.core.management import setup_environ
import settings
setup_environ(settings)

from django.db.models.loading import cache as model_cache
model_cache._populate()

from nltk.classify import NaiveBayesClassifier
from org.models import Org
from users.models import User
import math
import logging

log = logging.getLogger('miner.classifiers')

def word_features(name):
    return dict((word.lower(), True) for word in name.split())

"""
Tuning constant
defined as the ratio: log2( (P(is_org) + tiny constant) / (P(is_user) + tiny_constant) )
Keep in mind that each time this is run, we exclude users
who have this probability or higher so by excluding more org users
you exclude all the words associated with them, which can boost
other users above the threshold
"""

# Since I'm doing log base 2 of the ratio (they can get rather large)
# the actual ratio we'd be working with is 2^n, so 8.0 with a min ratio of 3.0
MIN_RATIO = 3.0

# Use this bad boy as a pseudocount (added to both numerator and denominator) so we don't divide by 0
# Very small number so it's practically insignificant in the division
NORMALIZING_CONST = 0.0000001

def main():
    org_names = Org.objects.values_list('name', flat=True)

    users = User.objects.filter(likely_org=False)
    user_names = [user.get_name for user in users]
    # Exclude the users we know are orgs (exact same name). This mostly gets run the first time and for new users with org names
    non_org_user_names = set(user_names) - set(org_names)

    org_features = [(word_features(name), 'org') for name in org_names]
    user_features = [(word_features(name), 'user') for name in non_org_user_names]

    classifier = NaiveBayesClassifier.train(user_features + org_features)

    counter = 0

    likely_orgs = []

    for user in users:
        prediction = classifier.prob_classify(word_features(user.get_name))
        if prediction.max() == 'org':
            # Log probability ratio, so if P(org) == 2.4 and P(user) == 0.3 then log2(P(org)/P(user)) = log2(8.0) = 3.0
            ratio = math.log(((float(prediction.prob('org')) + NORMALIZING_CONST) / (float(prediction.prob('user')) + NORMALIZING_CONST)), 2)
            if ratio >= MIN_RATIO and user.likely_org == False and user.admin_classification != 'user':
                log.info('User ID %d with name "%s" is probably an org. Saving.' % (user.id, user.get_name))
                user.likely_org = True
                user.org_probability = ratio
                user.save()
                counter += 1

    log.info("Processed %d users with org-like names" % counter)
    
if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = fetch_facebook
#!/usr/bin/env python

from django.core.management import setup_environ
import settings
setup_environ(settings)

from django.db.models.loading import cache as model_cache
model_cache._populate()

import facebook
 
from django.db import connection
from django.db.models import Q

import settings
import urllib2
import urlparse

from fabric.api import local
from org.models import Org
from miner.web.crawler import WebCrawler
from miner.jobs.org_social_media import OrgSocialMediaMapper, reducer

class FacebookMapper(OrgSocialMediaMapper):
    last_updated_column = 'facebook_last_fetched'
    
    def get_api(self):
        self.api = facebook.GraphAPI(settings.FACEBOOK_ACCESS_TOKEN)
 
    def has_links(self, post):
        return post['type'] == 'link'

    def extract_links(self, post):
        return [post['link'].encode('utf-8')]
    
    def default_text(self, post):
        return ' '.join([post.get('name', ''), post.get('message', ''), post.get('description', '')])
    
    def get_batch(self, org, limit=200, page=1, since=None):
        params = dict(limit=limit, offset=(page-1)*limit )
        
        # This is being urlencoded in python-facebook-sdk
        # so don't include the param if it's None
        if since:
            params['since'] = since
            
        try:
            posts = self.api.get_connections(str(org.facebook_id), 'posts', fields='message,link,name,caption,description,type', **params)    
        except Exception:
            return [], None, None
    
        # Can use this but doesn't really account for not fetching data twice
        paging = posts.get('paging', {})
        
        next_page = None
        
        if len(posts.get('data', [])) == limit:
            next_page = page + 1
        
        new_last_fetched_date = None
    
        if page==1:
            parsed_query_string = urlparse.parse_qs(urlparse.urlparse(paging.get('previous', '')).query)
            new_last_fetched_date = parsed_query_string.get('since', [None])[0]
    
        return posts['data'], next_page, new_last_fetched_date

def runner(job):
    job.additer(FacebookMapper, reducer)

def starter(program):
    tempfile_path = '/tmp/facebook'
    input_path = '/miner/search/inputs/facebook'
    output_path = '/miner/search/outputs/facebook'
    
    with open(tempfile_path, 'w') as tempfile:
        orgs = Org.objects.filter(is_active=True, facebook_id__isnull=False)[:10]
        for org in orgs:
            tempfile.write('\t'.join([str(org.id), str(org.facebook_id), str(org.facebook_last_fetched or '')]) +'\n')

    local('if hadoop fs -test -e ' + input_path +' ;  then hadoop fs -rm ' + input_path + '; fi')
    local('if hadoop fs -test -e ' + output_path + ' ;  then hadoop fs -rmr ' + output_path + '; fi')
    
    local('hadoop fs -copyFromLocal ' + tempfile_path + ' ' + input_path)

    program.addopt('input', input_path)
    program.addopt('output', output_path)

if __name__ == '__main__':
    import dumbo
    dumbo.main(runner, starter)
########NEW FILE########
__FILENAME__ = fetch_twitter
#!/usr/bin/env python

from django.core.management import setup_environ
import settings
setup_environ(settings)

from django.db.models.loading import cache as model_cache
model_cache._populate()

from fabric.api import local
import twitter
from org.models import Org
from miner.jobs.org_social_media import OrgSocialMediaMapper, reducer

class TwitterMapper(OrgSocialMediaMapper):
    last_updated_column = 'twitter_last_status_id'

    # Delegate methods...okie I've been doing too much iOS
    def get_api(self):
        self.api = twitter.Api(use_gzip_compression=True)
    
    def has_links(self, post):
        return len(post.urls) > 0

    def extract_links(self, post):
        return [u.url for u in post.urls]
    
    def default_text(self, post):
        return ' '.join([post.text] + [h.text for h in post.hashtags] )
    
    def get_batch(self, org, limit=200, page=1, since=None):
        try:
            statuses = self.api.GetUserTimeline(org.twitter_id, since_id=since, count=limit, page=page, include_entities=True)
        except Exception:
            statuses = []

        last_status_id = statuses[0].id if page == 1 and len(statuses) > 0 else None
        next_page = None
        if len(statuses) == limit:
            next_page = page + 1

        return statuses, next_page, last_status_id

def starter(program):
    tempfile_path = '/tmp/twitter'
    input_path = '/miner/search/inputs/twitter'
    output_path = '/miner/search/outputs/twitter'
    
    with open(tempfile_path, 'w') as tempfile:
        orgs = Org.objects.filter(is_active=True, twitter_id__isnull=False).exclude(twitter_id='')[:10]
        for org in orgs:
            tempfile.write('\t'.join([str(org.id), org.twitter_id, str(org.twitter_last_status_id or '')]) +'\n')
    # Only way I could figure out to do a replace
    local('if hadoop fs -test -e ' + input_path +' ;  then hadoop fs -rm ' + input_path + '; fi')
    local('if hadoop fs -test -e ' + output_path + ' ;  then hadoop fs -rmr ' + output_path + '; fi')
    
    local('hadoop fs -copyFromLocal ' + tempfile_path + ' ' + input_path)

    program.addopt('input', input_path)
    program.addopt('output', output_path)

def runner(job):
    job.additer(TwitterMapper, reducer)


if __name__ == '__main__':
    import dumbo
    dumbo.main(runner, starter)
########NEW FILE########
__FILENAME__ = issues_words_from_stories
#!/usr/bin/env python
# django environment setup

from dumbo import *

import nltk
import settings
from miner.text.util import search_features
from miner.web.etl import html_to_story
import urllib2
import settings


def mapper1(key, value):
    """ Starting with input like:
    K=>row_id, V=>1\t<html>...Earthquake strikes in <b>Chile!<b>...</html>
    where 1 is the issue ID
    
    Output:
    K=>(row_id, 'earthquake', 1), V=>1
    K=>(row_id, 'strike', 1), V=>1
    K=>(row_id, 'chile', 1), V=>1
    ...
    """
    issue_id, doc = value.split('\t')
    
    doc = html_to_story(doc)
    
    for word in search_features(doc):
        yield (key, issue_id, word), 1
        
def reducer1(key, values):
    """ Output:
    
    K=>(row1, 'earthquake', 1), V=>10,
    K=>(row2, 'strike', 1), V=>5
    """
    yield (key, sum(values))

def mapper2(key, value):
    doc_num, issue_id, word = key
    occurences = value
    yield (doc_num, issue_id), (word, occurences)
    
def reducer2(key, values):
    # Pulls it all into memory but that should be ok
    word_occurences = list(values)
    yield key, word_occurences
    
def runner(job):
    job.additer(mapper1, reducer1)
    job.additer(mapper2, reducer2)
    
if __name__ == '__main__':
    """ Usage:  dumbo start issues_from_text.py -input /some/hdfs/input -output /some/hdfs/output -hadoop /path/to/hadoop """
    import dumbo
    dumbo.main(runner)
    
########NEW FILE########
__FILENAME__ = org_social_media
import urllib2

from collections import deque

from org.models import Org
from miner.web.etl import html_to_story

from miner.web.social_media import SocialMediaCrawler

import logging

log = logging.getLogger(__name__)

class OrgSocialMediaMapper():
    def __init__(self, batch_size=200):
        self.batch_size = batch_size
    
    # Delegate methods...okie I've been doing too much iOS
    def get_api(self):
        raise NotImplementedError('Children must implement')
    
    def has_links(self, post):
        raise NotImplementedError('Children must implement')

    def extract_links(self, post):
        raise NotImplementedError('Children must implement')
    
    def default_text(self, post):
        raise NotImplementedError('Children must implement')
    
    def get_batch(self, org, **kw):
        raise NotImplementedError('Children must implement')        
    
    def __call__(self, key, value):
        """
        K => line number
        V => '10188\tPIH\t1274838358735
        """
        org_id, social_id, last_status_pull = value.split('\t')
        api = self.get_api()

        org = Org.get(org_id)
        
        since = last_status_pull
        page = 1
        
        params = dict(limit=200)
        
        queue = deque([page])
        
        urls = []

        log.info("Creating pools")
         # URL crawlers, just use 20 greenlets for now
        crawler = SocialMediaCrawler(pool_size=20)
        
        while queue:
            page = queue.popleft()
            
            log.info("Got page %s" % page)
            
            posts, next_page, new_last_fetched = self.get_batch(org, limit=self.batch_size, page=page, since=since)
            
            log.info("Got %s posts, next page %s" % (len(posts), next_page ) )
            
            if new_last_fetched:
                setattr(org, self.last_updated_column, str(new_last_fetched))
                org.save()
                    
            if next_page:
                queue.append(next_page)
            
            for post in posts:
                if self.has_links(post):
                    log.info("Post has links")
                    # These are just URLs to crawl and get back HTML to throw in with the rest of the data
                    urls.extend( self.extract_links(post) )
                
                log.info("Yielding post data")
                
                yield (org_id, self.default_text(post))
                    
        
        log.info("Getting %s urls" % len(urls))
        for doc in crawler.crawl(urls):
            yield (org_id, doc)


def reducer(key, values):
    # Pull it all into memory
    values = list(values)
    yield (key, ' '.join(values))
    
########NEW FILE########
__FILENAME__ = gen_related_orgs
#!/usr/bin/env python
from django.core.management import setup_environ
import settings
setup_environ(settings)

from django.db.models.loading import cache as model_cache
model_cache._populate()

import os
import logging

from org.models import OrgIssueRelationship, RelatedOrg
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from etc import cache

from datetime import datetime
import logging
import logging.handlers
from issue.models import Issue
from org.models import Org
from users.models import Location
from functools import partial

import settings
import MySQLdb
from MySQLdb import cursors
from collections import defaultdict
from itertools import groupby
from operator import itemgetter
import math

import multiprocessing

import nltk
from numpy import zeros
from numpy import dot
from numpy.linalg import norm

from miner.text.util import porter, stopwords, tokenizer
import gensim

log = logging.getLogger()
CURSOR_BATCH_SIZE = 1000
LIMIT = 20
db_settings = settings.DATABASES['default']



# Non-profit specific
#'bring','together', 'mission',
#'organization', 'work', 'non-profit',
#'make', 'difference',
#'solution', 'grassroots', 'communities', 'provide',
#'support', 'people','live', 'program', 'promote',
#'service', 'life', 'build', 'improve', 'individual', 'resource',
#'opportunity', 'dedicated', 'empower','help', 'committed']) |


# Add org ids for testing the algorithm
test_orgs = set([10188, 1051, 6599, 5539, 3764, 5102, 9909, 3739,4856,2301,6448, 3108, 12601, 12600, 10187, 10154, 10122, 8773, 4187, 9347, 5837, 7112, 5754, 6083, 6011, 5684])


def get_db_connection():
    c = MySQLdb.connect(host=db_settings.get('HOST', 'localhost'),
                        port= int(db_settings.get('PORT') or 3306),
                        user=db_settings.get('USER', 'root'),
                        passwd=db_settings.get('PASSWORD', ''),
                        db=db_settings.get('NAME', 'jumodjango'),
                        use_unicode=True,
                        charset='utf8'
                        )
    return c

# Probably move this to a lib or use the bebop one
def batched_db_iter(cur, query, batch_size=CURSOR_BATCH_SIZE):
    cur.execute(query)
    while True:
        batch = cur.fetchmany(batch_size)
        if not batch:
            break
        for row in batch:
            yield row

def insert_related(org, similar):
    log.debug('Inserting some related orgs')
    # Note: doing this with an INSERT ON DUPLICATE KEY UPDATE
    # which is efficient but if we decide to change the number of items we store
    # we'll probably want to just clear the table first
    q = """
    insert into related_orgs
    values
    (null, %s, %s, %s, utc_timestamp(), utc_timestamp())
    on duplicate key update related_org_id = values(related_org_id),
    date_updated=utc_timestamp()
    """

    params = [(org, related_org, i+1) for i, related_org in enumerate(similar) if related_org != org]

    # Difficult to use a connection pool across multiple processes, so doing this
    conn = get_db_connection()
    cur = conn.cursor()

    cur.executemany(q, params)

    conn.commit()


def setup():
    # Grab some data from the DB so we can crunch it
    active_orgs = Org.objects.filter(is_active=True)
    org_content_type = ContentType.objects.get(model='org').id

    org_dict = dict((o.id, o) for o in active_orgs)

    # That's right, pulled out the double defaultdict what whAAAAt!
    features = defaultdict(lambda: defaultdict(list))
    term_frequencies = defaultdict(int)

    # There is no way in Django to use a server-side cursor
    conn = get_db_connection()
    cur = conn.cursor(cursors.SSDictCursor)
    # group_concat is one of the best things ever, but its default max length before it starts truncating is far
    # too low for our purposes. Crank that up.
    cur.execute("set group_concat_max_len=65535")

    all_content = {}
    # Text we'll be analyzing, all content items associated with every org
    content_query = "select o.org_id as org_id, group_concat(ci.body separator ' ') as content from orgs o join content_items ci on ci.content_type_id = " + str(org_content_type) + " and ci.object_id = o.org_id and ci.section='center' group by o.org_id"
    for row in batched_db_iter(cur, content_query):
        org = row['org_id']
        if org not in org_dict:
            continue
        all_content[org] = row['content']

    issue_query = "select org_id, group_concat(i.name) as issues from org_orgissuerelationship oi join issues i using(issue_id) group by org_id"

    # See upstairs for implementation of batched_db_iter
    for row in batched_db_iter(cur, issue_query):
        org = row['org_id']
        if org not in org_dict:
            continue
        issues = [issue for issue in row['issues'].split(',')]
        for issue in issues:
            features[org]['issues'].append(issue)

    location_query = "select org_id, l.* from org_org_working_locations o join users_location l on o.location_id = l.id"

    #for row in batched_db_iter(cur, location_query):
    #    org = row.pop('org_id')
    #    features[org]['locations'].append(unicode(Location(**row)))

    # Could include followers as a feature for the "people who follow org x also follow org y"

    #followers_query = "select org_id, group_concat(user_id) as followers from org_usertoorgfollow where following = 1 group by org_id"
    #for row in batched_db_iter(cur, followers_query):
    #    org = row['org_id']
    #    followers = [long(user) for user in row['followers'].split(',')]
    #    features[org]['followers'] = followers

    # Deletes the rows that have been read into the cursor
    cur.close()
    conn.close()

    for org, content in all_content.iteritems():
        if org not in org_dict:
            continue

        org_name = org_dict[org].name
        content = content.replace(org_name, '')
        all_tokens = nltk.regexp_tokenize(content, tokenizer)

        #stemmed_tokens = [porter.stem(t.lower()) for t in all_tokens if t.lower() not in stopwords]
        gram_tokens = [t.lower() for t in nltk.regexp_tokenize(content, tokenizer) if t.lower() not in stopwords]
        features[org]['unigrams'] = gram_tokens
        features[org]['bigrams'] = nltk.bigrams(gram_tokens)   # bigrams('The cat in the hat') => [('The', 'cat'), ('cat', 'in'), ('in', 'the'), ('the', 'hat')]
        features[org]['trigrams'] = nltk.trigrams(gram_tokens)

        # Tried these but they were expensive in terms of computation time
        # Besides, once we get out to three or more words it's probably better to start looking at
        # sentence structure with nltk, things like: (org name) (helps/provides) [x] with [y]

    for k,v in features.iteritems():           # {org_id: {'bigrams': [('a','b') ...], 'issues': ['fracking','environment']}}
        for type, words in v.iteritems():
            # Using set so we're calculating unique documents
            for word in set(words):
                term_frequencies[(type, word)] += 1

    # Eliminate words which only pertain to one document (names, etc.)
    to_delete = set()
    for k, v in term_frequencies.iteritems():
        # only 1 occurrence in the whole doc set
        if v==1:
            to_delete.add(k)

    for k in to_delete:
        del term_frequencies[k]

    word_ids = dict((k, i) for i, k in enumerate(term_frequencies.keys()))
    num_orgs = len(all_content)

    weights = dict(trigrams=1,
                   bigrams=2,
                   unigrams=1.5,
                   issues=.2,
                   locations=.1,
                   followers=.1,
                   )

    return features, word_ids, term_frequencies, num_orgs, weights, active_orgs

def write_mm_corpus(features, word_ids, term_frequencies, num_orgs, weights):
    corpus = []

    id_to_index = {}
    index = 0

    # Create TF-IDF model
    for org, doc in features.iteritems():
        doc_length = dict((k, len(v)) for k,v in doc.iteritems())
        doc_occurences = defaultdict(int)
        for type, words in doc.iteritems():
            for word in words:
                doc_occurences[(type,word)] += weights[type]

        row = []

        # Term-frequency * inverse document frequency: similar to what Solr uses
        # reference: http://en.wikipedia.org/wiki/Tf%E2%80%93idf
        for type, words in doc.iteritems():
            for word in words:
                if (type,word) not in term_frequencies:
                    continue
                term_freq = float(doc_occurences[(type,word)]) / doc_length[type]  # Normalize for shorter/longer documents
                inverse_doc_freq = math.log(float(num_orgs) / (term_frequencies[(type,word)] + 1))
                tfidf = term_freq * inverse_doc_freq
                row.append((word_ids[(type,word)], tfidf))

        corpus.append(row)

        id_to_index[org] = index
        index += 1

    fname = '/tmp/corpus.mm'
    gensim.corpora.MmCorpus.serialize(fname, corpus)
    return fname, id_to_index, corpus


def main():
    from optparse import OptionParser
    parser = OptionParser()

    parser.add_option('-l', '--log-level', dest='log_level', choices=['DEBUG', 'INFO', 'WARN', 'ERROR'], default='INFO')
    (options, args) = parser.parse_args()
    log_level = getattr(logging, options.log_level)

    if os.path.exists('/cloud/logs'):
        handler = logging.handlers.RotatingFileHandler('/cloud/logs/org_relation.log', backupCount=10)
        log.addHandler(handler)

    log.setLevel(log_level)

    log.info("Doing setup")
    features, word_ids, term_frequencies, num_orgs, weights, all_orgs = setup()

    org_dict = dict((o.id, o) for o in all_orgs)

    log.info("Creating Matrix Market format corpus and saving to disk")
    fname, id_to_index, corpus = write_mm_corpus(features, word_ids, term_frequencies, num_orgs, weights)

    mm = gensim.corpora.MmCorpus(fname)
    id2word = dict((v,k) for k,v in word_ids.iteritems())

    log.info("Ok, now building the LSI corpus")

    lsi = gensim.models.LsiModel(corpus=mm, num_topics=500,id2word=id2word)

    log.info("Yayyy got topics")

    """
    Programmatic access to gensim's print_debug

    import numpy

    id2token=lsi.id2word
    u=lsi.projection.u
    s=lsi.projection.s
    topics=range(100)
    num_words=10
    num_neg=0
    log.info('computing word-topic salience for %i topics' % len(topics))
    topics, result = set(topics), {}

    words_per_topic = {}

    for uvecno, uvec in enumerate(u):
        uvec = numpy.abs(numpy.asarray(uvec).flatten())
        udiff = uvec / numpy.sqrt(numpy.sum(numpy.dot(uvec, uvec)))
        for topic in topics:
            result.setdefault(topic, []).append((udiff[topic], uvecno))

    log.debug("printing %i+%i salient words" % (num_words, num_neg))
    for topic in sorted(result.iterkeys()):
        weights = sorted(result[topic], key=lambda x: -abs(x[0]))
        _, most = weights[0]
        if u[most, topic] < 0.0: # the most significant word has a negative sign => flip sign of u[most]
            normalize = -1.0
        else:
            normalize = 1.0

        # order features according to salience; ignore near-zero entries in u
        words = []
        for weight, uvecno in weights:
            if normalize * u[uvecno, topic] > 0.0001:
                words.append((id2token[uvecno], u[uvecno, topic]))
                if len(words) >= num_words:
                    break

        words_per_topic[topic] = words
    """

    index = gensim.similarities.MatrixSimilarity(lsi[corpus])

    index_to_id = dict((v, k) for k,v in id_to_index.iteritems())

    for idx, doc in enumerate(corpus):
        org_id = index_to_id[idx]
        #if org_id not in test_orgs:
        #    continue
        # Convert document to vector space
        vector_lsi = lsi[doc]
        sims = index[vector_lsi]
        sims = [index_to_id[k] for k, v in sorted(enumerate(sims), key = lambda item:item[1], reverse=True)[:21]]
        insert_related(org_id, sims)
        #log.info("Org %s similar to: %s" % (org_dict[org_id] , ', '.join([org_dict[org2_id].name for org2_id in sims]) ))


    #lda = gensim.models.LdaModel(corpus=mm, num_topics=100, id2word=id2word,
    #                             chunksize=10000, passes=1, update_every=1)

    # Nuke the orgs in memcache but don't block the high-concurrency section
    #all_orgs = list(Org.objects.all())
    #cache.bust(all_orgs)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = util
import nltk
import os
import string

# Fastest way to strip control characters in bulk

translations = {
    unicode: dict((ord(char), u' ') for char in u'\n\r\t'),
    str: string.maketrans('\n\t\r', '   ')
}

def strip_control_characters(s, translate_to=' '):
    return s.translate(translations[type(s)])
    
porter = nltk.PorterStemmer()

stopwords_path = os.path.realpath(os.path.dirname(__file__))

# Stopwords get filtered out before we do any analysis
stopwords = set([unicode(line.strip()).lower() for line in open(os.path.join(stopwords_path, 'stopwords.txt'))]) | set([unicode(word) for word in [
    # These are all technically tokens, filter them out too
    '.',',',';','"',"'",'?','(',')',':','-','_','`','...'
    ]])

# Regex pattern for splitting tokens
tokenizer = r'''(?x)
      ([A-Z]\.)+
    | \w+(-\w+)*
    | \$?\d+(\.\d+)?%?
    | \.\.\.
    | [][.,;"'?():-_`]
'''

def search_features(doc):
    words = [word.lower() for word in nltk.regexp_tokenize(doc, tokenizer) if word.lower() not in stopwords]
    unigrams = set([porter.stem(word) for word in words])
    bigrams = set(nltk.bigrams(words))
    return unigrams | bigrams

########NEW FILE########
__FILENAME__ = views
from etc.view_helpers import json_response
from classifiers.related_search import RelatedSearchClassifier

classifier = RelatedSearchClassifier.get_model()

def related_searches(request):
    q = request.GET.get('q')
    if not q:
        return []
    else:
        resp = classifier.classify(q)
        return json_response(resp)
########NEW FILE########
__FILENAME__ = crawler
import string
import urllib2

import logging
import httplib

# This is the kind of task where coroutines really shine

green_lib = None

try:
    import gevent
    import gevent.pool
    from gevent import monkey
    monkey.patch_all()
    green_lib = 'gevent'
except ImportError:
    import eventlet
    from eventlet import monkey_patch
    monkey_patch()
    green_lib = 'eventlet'
        
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('miner.web.crawler')

class WebCrawler(object):
    def __init__(self, pool_size=200):
        self.pool = None
        if green_lib == 'gevent':
            self.pool = gevent.pool.Pool(pool_size)
        elif green_lib == 'eventlet':
            self.pool = eventlet.greenpool.GreenPool(pool_size)

    def fetch_url(self, url):
        try:
            log.debug('Making request to %s' % url)
            request = urllib2.Request(url, headers={'User-Agent': 'Your Mom'})
            u = urllib2.urlopen(request)
            if u.headers.type=='text/html':
                data = u.read()
                log.debug('Success')
            else:
                data = ''
                log.debug('Non-HTML content type')
            return data
        except urllib2.URLError, e:
            log.warn('Boo, got a url error for %s: %s' % (url, e))
            return ''
        except httplib.HTTPException, e:
            log.warn('Boo, got an HTTP error for %s: %s' % (url, e))
            return ''            

    def crawl(self, urls):
        for result in self.pool.imap(self.fetch_url, urls):
            yield result
########NEW FILE########
__FILENAME__ = etl
import urllib2
import settings
import json
from miner.text.util import strip_control_characters

def html_to_story(doc, strip_control_chars=True):
    try:
        # Send the HTML over to Data Science Toolkit
        story = urllib2.urlopen( '/'.join([settings.DSTK_API_BASE, 'html2story']), data=doc).read()
        
        story = json.loads(story).get('story', '')
        
        if strip_control_chars:
            story = strip_control_characters(story)
        return story
    except urllib2.URLError, e:
        return ''
########NEW FILE########
__FILENAME__ = feed_items_to_hdfs
#!/usr/bin/env python

from crawler import WebCrawler, log

import logging
import os
import hashlib
from miner.text.util import strip_control_characters
import MySQLdb
from MySQLdb import cursors


class FeedItemWebCrawler(WebCrawler):
    temp_outfile_path = '/tmp/feed_items'
    outfile_base_path = '/tmp/scraped'
    hdfs_path = '/miner/classifiers/training_data/feed_items'
    
    def fetch_url(self, line):
        issue_id, url, data = line.split('\t')
        url = url.strip('"')
        
        outfile = os.sep.join([self.outfile_base_path, hashlib.md5(''.join([issue_id, url or data])).hexdigest()]) + '.out'
        
        if url and not os.path.exists(outfile):
            new_data = super(FeedItemWebCrawler, self).fetch_url(url)
            if new_data:
                data = new_data

        if not os.path.exists(outfile):            
            with open(outfile, 'w') as f:
                    f.write('\t'.join([issue_id, strip_control_characters(data)]))    
            return 'Wrote data'
        else:
            return 'Nada'
        
        
    @classmethod
    def write_to_temp(cls, temp_file, host, user, password, db):
        conn = MySQLdb.connect(host=host,
                               user=user,
                               passwd=password,
                               db=db)
                
        
        feed_item_query = """
        select target_id as issue_id, url, concat_ws(' ', replace(replace(replace(title, '\t', ' '), '\n', ' '), '\r', ' '), replace(replace(replace(description, '\t', ' '), '\n', ' '), '\r', ' ') ) as text
        into outfile '%s'
        fields terminated by '\t' optionally enclosed by '"'
        lines terminated by '\n'
        from feed_item fi
        join staff_users su
          on fi.origin_type='user'
          and fi.origin_id = su.user_id
        where fi.target_type='issue'
        and fi.item_type='user_story'    
        """ % temp_file
        
        cur = conn.cursor()
        cur.execute(feed_item_query)

if __name__ == '__main__':
    from fabric.api import local
    import time
    
    from optparse import OptionParser
    
    log.setLevel(logging.DEBUG)
    
    parser = OptionParser()

    parser.add_option('-d', '--hadoop-path', dest='hadoop_path')
    parser.add_option('-f', '--hdfs-path', dest='hdfs_path')
    
    parser.add_option('-t', '--temp-file-path', dest='tempfile_path', default=FeedItemWebCrawler.temp_outfile_path)
    parser.add_option('-m', '--mysql-host', dest='mysql_host', default='localhost')
    parser.add_option('-p', '--mysql-user', dest='mysql_user', default='root')
    parser.add_option('-w', '--mysql-password', dest='mysql_password', default='')
    parser.add_option('-b', '--mysql-database', dest='mysql_database', default='jumofeed')
    
    options, args = parser.parse_args()

    crawler = FeedItemWebCrawler()

    local('rm -f %s' % options.tempfile_path)
    crawler.write_to_temp(options.tempfile_path, options.mysql_host, options.mysql_user, options.mysql_password, options.mysql_database)

    log.info('Green pool time!')
    t1 = time.time()
    for result in crawler.crawl(open(options.tempfile_path, 'r')):
        log.info(result)
    t2 = time.time()
    
    log.info('DONE in %s seconds' % (t2 - t1))
    
    local('rm -f %s' % options.tempfile_path)
    local('for f in %(outfiles)s/*.out ; do cat $f >> %(final)s ; echo "" >> %(final)s ; done' % {'final': options.tempfile_path,
                                                                                                  'outfiles': FeedItemWebCrawler.outfile_base_path} )

    #local('rm -rf %s' % outfile_base_path)    
    local('%s dfs -copyFromLocal %s %s' % (options.hadoop_path, options.tempfile_path, options.hdfs_path))

########NEW FILE########
__FILENAME__ = ip_lookup
'''
Created on Jul 21, 2011

@author: al
'''

from miner.web import dstk

def ip_to_lat_lon(ip):
    if ip is None:
        return {}

    try:
        resp = dstk.ip2coordinates(ip)
    except Exception:
        return None

    if not resp.get(ip):
        return {}

    return resp[ip]

########NEW FILE########
__FILENAME__ = social_media
from crawler import WebCrawler
from miner.web.etl import html_to_story

class SocialMediaCrawler(WebCrawler):
    
    def fetch_url(self, url):
        data = super(SocialMediaCrawler, self).fetch_url(url) if url else ''
        if data:
            data = html_to_story(data)
        
        return data
########NEW FILE########
__FILENAME__ = admin
from django import forms
from django.contrib import admin
from etc import cache
from entity_items.admin import MediaItemInline, ActionInline, AdvocateInline, TimelineInline, CenterContentItemInline, LeftContentItemInline
from issue.models import Issue
from org.models import Org, RelatedOrg, OrgIssueRelationship, Alias
from users.models import User, Location
from cust_admin.views.main import ExtChangeList
from cust_admin.widgets import ForeignKeyToObjWidget

######## INLINES ########
class AliasInline(admin.TabularInline):
    model = Alias
    extra = 0
    classes = ('collapse closed',)
    verbose_name = "Alias"
    verbose_name_plural = "Aliases"

class AdminsInline(admin.TabularInline):
    model = Org.admins.through
    extra = 0
    classes = ('collapse closed',)
    related_field_lookups = {
        'fk': ['user']
    }
    verbose_name = "Admin"
    verbose_name_plural = "Admins"
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'user':
            kwargs['widget'] = ForeignKeyToObjWidget(rel=Org.admins.through._meta.get_field('user').rel)
        return super(AdminsInline,self).formfield_for_dbfield(db_field,**kwargs)

class IssuesInlineForm(forms.ModelForm):
    class Meta:
        model = Org.issues.through
        widgets = {'rank':forms.HiddenInput}

class IssuesInline(admin.TabularInline):
    model = Org.issues.through
    extra = 0
    form = IssuesInlineForm
    classes = ('collapse closed',)
    sortable_field_name = "rank"
    related_field_lookups = {
        'fk': ['issue']
    }
    verbose_name = ""
    verbose_name_plural = "Working On"
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'issue':
            kwargs['widget'] = ForeignKeyToObjWidget(rel=Org.issues.through._meta.get_field('issue').rel)
        return super(IssuesInline,self).formfield_for_dbfield(db_field,**kwargs)

class LocationsInline(admin.TabularInline):
    model = Org.working_locations.through
    extra = 0
    classes = ('collapse closed',)
    related_field_lookups = {
        'fk': ['location']
    }

    verbose_name = ''
    verbose_name_plural = 'Working In'
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'location':
            kwargs['widget'] = ForeignKeyToObjWidget(rel=Org.working_locations.through._meta.get_field('location').rel)
        return super(LocationsInline,self).formfield_for_dbfield(db_field,**kwargs)

######## MODEL FORM AND ADMIN ########

class OrgForm(forms.ModelForm):
    class Meta:
        model = Org
        widgets = {
            'location': ForeignKeyToObjWidget(rel=Org._meta.get_field('location').rel),
            'facebook_id' : forms.TextInput(attrs={'class':'vTextField'}),
            'summary': forms.Textarea(),
            }

    class Media:
        js = ['cust_admin/js/widgets.js']
        css = {'all':('cust_admin/css/extend_admin.css',)}


class OrgAdmin(admin.ModelAdmin):
    form = OrgForm

    #Org List Page Values
    search_fields = ['name','email', 'handle']
    search_fields_verbose = ['Name', 'Email']
    list_display = ('name', 'date_updated','is_active', 'is_vetted')
    list_filter = ('is_active',)
    ordering = ('name',)

    change_list_template = "cust_admin/change_list.html"

    def get_changelist(self, request, **kwargs):
        return ExtChangeList


    #Org Change Page Values
    fieldsets = (
      ('Org Profile', {
        'fields': (('name','handle',),
                   ('is_active', 'is_vetted', 'donation_enabled','is_claimed'),
                   ('email', 'ein',),
                   ('phone_number','year_founded','revenue','size',),
                   ('site_url', 'blog_url',),
                   'img_small_url', 'img_large_url','summary','location',
                   ('date_created','date_updated',),)
      }),
      ('Social Settings', {
        'fields':(
                    ('facebook_id', 'twitter_id', ),
                    ('youtube_id', 'flickr_id',),
                 )
      }),
      ("Extra Nonsense", {
        'classes': ('collapse closed',),
        'fields':('claim_token',),
      }),
    )

    readonly_fields = ['date_created','date_updated']
    inlines = [CenterContentItemInline, LeftContentItemInline, MediaItemInline, TimelineInline, ActionInline, AdvocateInline, AliasInline, AdminsInline, IssuesInline, LocationsInline, ]

    def save_model(self, request, obj, form, change):
        cache.bust(obj, update=False)
        super(self.__class__, self).save_model(request, obj, form, change)

admin.site.register(Org,OrgAdmin)

########NEW FILE########
__FILENAME__ = admin_views
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.admin.views.decorators import staff_member_required
from org.models import Org


def report(request):
    return render_to_response(
        "admin/org/report.html",
        {'org_list' : Org.objects.order_by('name'), 'title': 'List of Orgs'},
        RequestContext(request, {}),
    )
report = staff_member_required(report)

########NEW FILE########
__FILENAME__ = views
import datetime
from django.core.cache import cache as djcache
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import smart_str
from etc import cache
from etc.entities import create_handle
from etc.decorators import PostOnly, AccountRequired
from etc.view_helpers import json_response, json_error
from issue.models import Issue
import json
import logging
from etc.view_helpers import json_encode
from mailer.notification_tasks import send_notification, EmailTypes
from org.models import Org, UserToOrgFollow, OrgIssueRelationship
from users.models import Location
#from utils.donations import nfg_api
from utils.regex_tools import facebook_id_magic
from uuid import uuid4

@PostOnly
def fetch_org_by_centroid(request):
    try:
        lat = float(request.POST.get('lat'))
        lon = float(request.POST.get('lon'))
        limit = float(request.POST.get('limit', 20))
    except AttributeError:
        json_error(INVALID_CENTROID_ERROR)

    orgs = Org.objects.filter(location__latitude__range = (lat - limit, lat + limit)).filter(location__longitude__range = (lon - limit, lon + limit))[0:limit]
    return json_response(json_encode(orgs))


@PostOnly
def update_org(request):
    try:
        org = json.loads(request.POST.get('org', {}))
        org_id = int(org['id'])
    except AttributeError:
        json_error(INVALID_ORG_ID_ERROR)

    str_fields = [
                    'name', 'email', 'phone_number', 'url', 'img_url',
                    'revenue', 'size', 'vision_statement', 'mission_statement',
                    'blog_url', 'twitter_id', 'flickr_id', 'vimeo_id', 'youtube_id',
                 ]

    int_fields = [
                    'year_founded', 'facebook_id', # changed 'year' to 'year_founded' here -b
                 ]

    bool_fields = [
                    'fb_fetch_enabled', 'twitter_fetch_enabled',
                  ]

    original = Org.objects.get(id = org_id)


    if 'parent_orgs' in org:
        if org['parent_orgs']:
            original.parent_org = Org.objects.get(id = org['parent_orgs'][0])

    if 'ein' in org and org['ein'] != original.ein:
        original.donation_enabled = False
        if org['ein'] == '':
            original.ein = ''
        else:
            original.ein = org['ein']
            try:
                original.donation_enable = False
              #  if nfg_api.npo_is_donation_enabled(org['ein']):
              #      original.donation_enabled = True
            except Exception, inst:
                logging.exception("Error checking donation status with nfs")


    if 'child_orgs' in org:
        org['child_orgs'] = [int(o) for o in org['child_orgs']]
        for o in org['child_orgs']:
            if o not in [l.id for l in original.parentorg.all()]:
                original.parentorg.add(Org.objects.get(id = o))
        for o in original.parentorg.all():
            if o.id not in org['child_orgs']:
                original.parentorg.remove(Org.objects.get(id = o.id))

    # this probably needs to change down the road because i can't imagine this is very sustainable.
    for i in org['tags']['context']:
        iss = Issue.objects.get(name__iexact = i['name'])

        try:
            r = OrgIssueRelationship.objects.get(issue = iss, org = original)
            r.rank = i['tag_rank']
            r.date_updated = datetime.datetime.now()
            r.save()
        except:
            r = OrgIssueRelationship()
            r.issue = iss
            r.org = original
            r.date_created = datetime.datetime.now()
            r.date_updated = datetime.datetime.now()
            r.rank = i['tag_rank']
            r.save()

    '''
    {u'locality': u'New York', u'region': u'Brooklyn', u'longitude': u'-73.948883', u'country_name': u'United States', u'postal_code': u'', u'address': u'', u'latitude': u'40.655071', u'type': u'County', u'raw_geodata': {u'lang': u'en-US', u'popRank': u'0', u'name': u'Brooklyn', u'woeid': u'12589335', u'uri': u'http://where.yahooapis.com/v1/place/12589335', u'admin1': {u'content': u'New York', u'code': u'US-NY', u'type': u'State'}, u'admin3': None, u'admin2': {u'content': u'Brooklyn', u'code': u'', u'type': u'County'}, u'centroid': {u'latitude': u'40.655071', u'longitude': u'-73.948883'}, u'locality1': {u'content': u'New York', u'type': u'Town'}, u'locality2': None, u'country': {u'content': u'United States', u'code': u'US', u'type': u'Country'}, u'boundingBox': {u'northEast': {u'latitude': u'40.739471', u'longitude': u'-73.833359'}, u'southWest': {u'latitude': u'40.570679', u'longitude': u'-74.042068'}}, u'areaRank': u'5', u'postal': None, u'placeTypeName': {u'content': u'County', u'code': u'9'}}}
    '''

    if 'location' in org and org['location']:
        loc = org['location']
        raw_geodata = json.dumps(loc["raw_geodata"]) if isinstance(loc.get("raw_geodata"), dict) else loc.get("raw_geodata")
        #Until we fix duplicate locations we have to do the following...lame.
        _locs = Location.objects.filter(raw_geodata = raw_geodata,
            longitude = loc.get('longitude', None),
            latitude = loc.get('latitude', None),
            address = loc.get('address', ' '),
            region = loc.get('region', ' '),
            locality = loc.get('locality', ' '),
            postal_code = loc.get('postal_code', ' '),
            country_name = loc.get('country_name', ' '))

        if len(_locs) > 0:
            _loc = _locs[0]
        else:
            _loc = Location(raw_geodata = raw_geodata,
                longitude = loc.get('longitude', None),
                latitude = loc.get('latitude', None),
                address = loc.get('address', ' '),
                region = loc.get('region', ' '),
                locality = loc.get('locality', ' '),
                postal_code = loc.get('postal_code', ' '),
                country_name = loc.get('country_name', ' '),)
            _loc.save()
        original.location = _loc
    else:
        original.location = None

    if 'working_locations' in org:
        for loc in org['working_locations']:
            raw_geodata = json.dumps(loc["raw_geodata"]) if isinstance(loc.get("raw_geodata"), dict) else loc.get("raw_geodata")
            if raw_geodata not in [l.raw_geodata for l in original.working_locations.all()]:
                locs = Location.objects.filter(raw_geodata = raw_geodata,
                        longitude = loc.get('longitude', None),
                        latitude = loc.get('latitude', None),
                        address = loc.get('address', ' '),
                        region = loc.get('region', ' '),
                        locality = loc.get('locality', ' '),
                        postal_code = loc.get('postal_code', ' '),
                        country_name = loc.get('country_name', ' '),
                        )

                if len(locs) > 0:
                    new_l = locs[0]
                else:
                    new_l = Location(raw_geodata = raw_geodata,
                        longitude = loc.get('longitude', None),
                        latitude = loc.get('latitude', None),
                        address = loc.get('address', ' '),
                        region = loc.get('region', ' '),
                        locality = loc.get('locality', ' '),
                        postal_code = loc.get('postal_code', ' '),
                        country_name = loc.get('country_name', ' '),
                        )
                    new_l.save()


                #Until we clean up the location DB we can't use get.
                """
                new_l, created = Location.objects.get_or_create(
                        raw_geodata = json.dumps(loc["raw_geodata"]) if isinstance(loc.get("raw_geodata"), dict) else loc.get("raw_geodata"),
                        longitude = loc.get('longitude', None),
                        latitude = loc.get('latitude', None),
                        address = loc.get('address', ' '),
                        region = loc.get('region', ' '),
                        locality = loc.get('locality', ' '),
                        postal_code = loc.get('postal_code', ' '),
                        country_name = loc.get('country_name', ' '),
                        )
                """
                original.working_locations.add(new_l)
                original.save()

        raw_geos = []
        for new_loc in org['working_locations']:
            raw_geodata = json.dumps(new_loc["raw_geodata"]) if isinstance(new_loc.get("raw_geodata"), dict) else new_loc.get("raw_geodata")
            raw_geos.append(raw_geodata)

        for old_loc in original.working_locations.all():
            if old_loc.raw_geodata not in raw_geos:
                original.working_locations.remove(old_loc)



    for issue in original.issues.all():
        if issue.name.lower() not in [l['name'].lower() for l in org['tags']['context']]:
            r = OrgIssueRelationship.objects.get(issue = issue, org = original)
            r.delete()

    for f in str_fields:
        if f in org and org[f] != getattr(original, f):
            setattr(original, f, smart_str(org[f], encoding='utf-8'))

    for f in int_fields:
        if f in org and org[f] != getattr(original, f):
            if org[f]:
                setattr(original, f, int(org[f]))
            else:
                setattr(original, f, None)

    for f in bool_fields:
        if f in org and org[f] != getattr(original, f):
            setattr(original, f, org[f])

    if 'handle' in org and org['handle'] != original.handle:
        _handle = original.handle
        original.handle = create_handle(org['handle'])
        cache.bust_on_handle(original, _handle, False)

    if 'methods' in org:
        for method in org['methods']:
            if method not in [l.method for l in original.method_set.all()]:
                m = Method()
                m.method = method
                m.date_created = datetime.datetime.now()
                m.date_updated = datetime.datetime.now()
                m.org = original
                m.save()

        for method in original.method_set.all():
            if method.method not in org['methods']:
                method.delete()

    if 'accomplishments' in org:
        for acc in org['accomplishments']:
            if acc['text'] not in [l.description for l in original.accomplishment_set.all()]:
                a = Accomplishment()
                a.org = original
                a.header = acc.get('year', '')
                a.description = acc.get('text', '')
                a.save()

        for acc in original.accomplishment_set.all():
            acc_header = acc.header
            acc_description = acc.description
            delete = True
            for new_acc in org["accomplishments"]:
                if new_acc["year"] == acc_header and new_acc["text"] == acc_description:
                    delete = False
            if delete:
                acc.delete()

    original.save()
    try:
        cache.bust_on_handle(original, original.handle)
    except:
        pass
    return json_response({'result' : original.handle})


@PostOnly
def remove_org(request):
    try:
        id = getattr(request.POST, 'id')
        org = Org.objects.get(id = id)
    except AttributeError, ObjectDoesNotExist:
        return json_error(INVALID_ORG_ID_ERROR)

    # TODO: so, uh, we need to figure out if the current user is authorized to do this?

    org.delete()
    cache.bust_on_handle(org, org.handle, False)
    return json_response({'result' : 1})


@PostOnly
def flag_org(request):
    try:
        org_id = getattr(request.POST, 'org_id')
        org = Org.objects.get(id = org_id)
    except AttributeError, ObjectDoesNotExist:
        return json_error(CANNOT_FLAG_ERROR)

    # TODO: so, uh, we need to figure out if the current user is authorized to do this?
    org.flagged = True
    org.save()
    cache.bust_on_handle(org, org.handle, False)
    return json_response({'result' : True})

@PostOnly
@AccountRequired
def org_create(request):
    o = Org()
    o.name = request.POST['name'].encode('utf-8')
    o.handle = create_handle(request.POST['name'])
    o.vision_statement = request.POST['vision_statement'].encode('utf-8')
    if request.POST['social_mission'] == 'yes':
        o.social_mission = True
    else:
        o.social_mission = False
    if request.POST['profit'] == 'yes':
        o.profit_seeking = True
    else:
        o.profit_seeking = False

    o.save()
    if request.POST['admin'] == 'yes':
        o.admins.add(request.user)
        o.save()

    f, created = UserToOrgFollow.objects.get_or_create(user = request.user, org = o)
    f.following = True
    f.save()
    request.user.refresh_orgs_following()
    return json_response(json_encode(o))

#brennan added this one
@PostOnly
def normalize_facebook_id(request):
    facebook_id = request.POST['fbid']

    if facebook_id:
        try:
            facebook_id = facebook_id_magic(facebook_id)
        except:
            return json_error(123, 'Sorry, your Facebook ID is invalid')

    return json_response({"facebook_id": facebook_id })

########NEW FILE########
__FILENAME__ = forms
from django import forms
from etc.entities import create_handle
from entity_items.models import ContentItem
from org.models import Org, OrgIssueRelationship
from issue.models import Issue
from users.models import Location
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import ValidationError
from utils.widgets import MultipleLocationWidget, LocationWidget
import json

class OrgForm(forms.ModelForm):
    class Meta:
        model = Org
        widgets = {
            'location': LocationWidget(),
            'working_locations': MultipleLocationWidget(),
            'facebook_id': forms.TextInput(attrs={'placeholder':1234567890}),
            'site_url': forms.TextInput(attrs={'placeholder':'http://www.your.org'}),
            'email': forms.TextInput(attrs={'placeholder':'example@your.org'}),
            'phone_number': forms.TextInput(attrs={'placeholder':'(555) 555-5555'}),
            'twitter_id': forms.TextInput(attrs={'placeholder':'yourorg'}),
            'blog_url': forms.TextInput(attrs={'placeholder':'http://your.org/blog'}),
            'youtube_id': forms.TextInput(attrs={'placeholder':'yourorg'}),
            'flickr_id': forms.TextInput(attrs={'placeholder':'yourorg'}),
            'summary': forms.Textarea(attrs={'placeholder': 'Describe the organization\'s vision.'}),
        }

    class Media:
        css = {
            'all':['css/admin/widgets.css',]
        }
        js = ['/admin/jsi18n/',]

    def __init__(self, *args, **kwargs):
        super(OrgForm, self).__init__(*args, **kwargs)
        if 'working_locations' in self.fields:
            self.fields['working_locations'].help_text = ''
        if 'issues' in self.fields:
            self.fields['issues'].widget = FilteredSelectMultiple('Issues', False)
            self.fields['issues'].queryset = Issue.objects.order_by('name')
            self.fields['issues'].help_text = ''

    def save(self, commit=True):
        instance = super(OrgForm, self).save(commit=False)
        if 'issues' in self.fields:
            old_issues = instance.issues.all()
            new_issues = self.cleaned_data['issues']
            to_delete = set(old_issues) - set(new_issues)
            to_create = set(new_issues) - set(old_issues)

            OrgIssueRelationship.objects.filter(org=instance, issue__in=to_delete).delete()
            for issue in to_create:
                relationship = OrgIssueRelationship(org=instance, issue=issue)
                try:
                    relationship.full_clean()
                    relationship.save()
                except ValidationError, e:
                    pass
            del(self.cleaned_data['issues'])
        if commit:
            instance.save()
            self.save_m2m()
        return instance

class ManageOrgForm(OrgForm):
    mission = forms.CharField(label="Mission Statement", widget=forms.Textarea)

    class Meta(OrgForm.Meta):
        fields = ['name', 'handle', 'ein', 'location', 'summary', 'mission', 'issues', 'working_locations']

    def __init__(self, *args, **kwargs):
        super(ManageOrgForm, self).__init__(*args, **kwargs)
        try:
            content_item = self.instance.content.center().mission_statement()
            self.fields['mission'].initial = content_item.rich_text_body
        except ContentItem.DoesNotExist:
            pass

    def save(self, commit=True):
        instance = super(ManageOrgForm, self).save(False)
        try:
            content_item = instance.content.center().mission_statement()
        except ContentItem.DoesNotExist:
            content_item = ContentItem(entity=instance, section=ContentItem.ContentSection.CENTER, title=ContentItem.MISSION_STATEMENT)
        content_item.rich_text_body = self.cleaned_data['mission']
        content_item.save()

        if commit:
            instance.save()
            self.save_m2m()
        return instance

class ManageOrgConnectForm(OrgForm):
    class Meta(OrgForm.Meta):
        fields = ['facebook_id', 'site_url', 'email', 'phone_number', 'twitter_id',
                  'blog_url', 'youtube_id', 'flickr_id',]

class ManageOrgMoreForm(OrgForm):
    class Meta(OrgForm.Meta):
        fields = ['img_large_url', 'size', 'revenue', 'year_founded']

    def save(self, commit=True):
        from django.core.files.uploadedfile import InMemoryUploadedFile
        instance = super(ManageOrgMoreForm, self).save(False)
        if isinstance(self.cleaned_data['img_large_url'], InMemoryUploadedFile):
            instance.img_small_url = self.cleaned_data['img_large_url']

        if commit:
            instance.save()
            self.save_m2m()
        return instance

    def __init__(self, *args, **kwargs):
        super(ManageOrgMoreForm, self).__init__(*args, **kwargs)
        self.fields['img_large_url'].label = 'Image'

class CreateOrgForm(OrgForm):
    YES = 'yes'
    SOCIAL_MISSION_CHOICES = ((YES, 'Yes'), ('no', 'No'))

    social_mission = forms.ChoiceField(choices=SOCIAL_MISSION_CHOICES, widget=forms.RadioSelect)

    class Meta(OrgForm.Meta):
        fields = ['name', 'summary']

    def save(self, commit=True):
        instance = super(CreateOrgForm, self).save(False)
        instance.handle = create_handle(instance.name)

        if commit:
            instance.save()
            self.save_m2m()
        return instance

    def clean_social_mission(self):
        data = self.cleaned_data['social_mission']
        if data != self.YES:
            raise forms.ValidationError('''We appreciate your interest in Jumo. Unfortunately we cannot
                accept your organization on the platform. Jumo is a registered
                501(c)(3) and accepting organizations that are not mission-driven
                could violate our IRS status.''')
        return data

class DetailsOrgForm(OrgForm):
    class Meta(OrgForm.Meta):
        fields = ['working_locations', 'issues', 'facebook_id', 'twitter_id']

    def __init__(self, *args, **kwargs):
        super(DetailsOrgForm, self).__init__(*args, **kwargs)
        self.fields['working_locations'].help_text = "Please enter the cities or countries in which you work."
        self.fields['issues'].help_text = "Please choose up to six issues your organization works on."

########NEW FILE########
__FILENAME__ = models
from action.models import Action
from django.conf import settings
from django.contrib.contenttypes import generic
from django.db import models
from entity_items.models import Advocate, ContentItem, MediaItem, TimelineItem
from entity_items.models.location import Location
from etc import cache
from etc.templatetags.tags import _create_static_url
from issue.models import Issue
from lib.image_upload import ImageSize, ImageType, S3EnabledImageField
from users.models import User
from commitment.models import Commitment

REVENUE_CHOICES = (
    ("less than $100,000","less than $100,000",),
    ("$100,000 - $1,000,000","$100,000 - $1,000,000",),
    ("$1m - $5m","$1m - $5m",),
    ("$5m - $20m","$5m - $20m",),
    ("more than $20m","more than $20m",),
)

SIZE_CHOICES = (
    ("1-10","1-10"),
    ("10-50","10-50",),
    ("51-100","51-100",),
    ("100+","100+",),
)

class Org(models.Model):

    #Public Properties
    id = models.AutoField(db_column='org_id', primary_key=True)
    name = models.CharField(max_length=200, verbose_name="Organization Name")
    summary = models.CharField(max_length=255, verbose_name="Vision Statement")
    handle = models.CharField(max_length=210, unique=True, verbose_name="Organization Handle",
                help_text="Your organization's unique handle used for your public Jumo page: www.jumo.com/<b>HANDLE</b>")
    ein = models.CharField(max_length=12, blank=True, verbose_name="EIN",
            help_text="*Not required, but must be provided for 501(c)(3)'s that wish to receive donations on Jumo. Find your organization's EIN <a target='_blank' href='http://nccsdataweb.urban.org/PubApps/990search.php?a=a&bmf=1'>here</a>.")
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=50, blank=True, verbose_name="Phone")
    img_small_url = S3EnabledImageField(image_type=ImageType.ORG, image_size=ImageSize.SMALL, blank=True)
    img_large_url = S3EnabledImageField(image_type=ImageType.ORG, image_size=ImageSize.LARGE, blank=True)
    year_founded = models.IntegerField(max_length=4, blank=True, null=True, verbose_name="Year Founded")
    revenue = models.CharField(max_length=32, blank=True, choices=REVENUE_CHOICES, verbose_name="Revenue Size")
    size = models.CharField(max_length=32, blank=True, choices=SIZE_CHOICES, verbose_name="# of Employees")
    blog_url = models.URLField(verify_exists = False, blank=True, verbose_name="Blog")
    site_url = models.URLField(verify_exists = False, blank=True, verbose_name="Website")
    facebook_id = models.BigIntegerField(max_length=41, blank=True, null=True, verbose_name="Facebook ID")
    twitter_id = models.CharField(max_length=64, blank=True, verbose_name="Twitter Username")
    youtube_id = models.CharField(max_length=64, blank=True, verbose_name="YouTube Username")
    flickr_id = models.CharField(max_length=64, blank=True, verbose_name="Flickr Username")
    location = models.ForeignKey(Location, null=True, blank=True, related_name='location', verbose_name="Headquarters")

    #Internal Properties
    is_vetted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, verbose_name="Is Active") #Replaces the old ignore field.
    donation_enabled = models.BooleanField(default=False, verbose_name="Is Donation Enabled")
    claim_token = models.CharField(max_length = 32, blank = True, verbose_name="Claim Token")
    is_claimed = models.BooleanField(default=False, verbose_name="Is Claimed")
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Date Created")
    date_updated = models.DateTimeField(auto_now=True, verbose_name="Date Updated")

    facebook_last_fetched = models.CharField(max_length=24, null=True, blank=True, default=None, verbose_name='Facebook Last Fetched')
    twitter_last_status_id = models.BigIntegerField(null=True, verbose_name='Twitter Last Status ID')

    #Relationship Properties
    admins = models.ManyToManyField(User, related_name = 'admins', db_table='org_org_admins')
    content = generic.GenericRelation(ContentItem, related_name='content')
    actions = generic.GenericRelation(Action, related_name='org_actions')
    advocates = generic.GenericRelation(Advocate, related_name='advocates')
    timeline = generic.GenericRelation(TimelineItem, related_name='timeline')
    media = generic.GenericRelation(MediaItem, related_name='media')
    followers = models.ManyToManyField(User, symmetrical=False, through='UserToOrgFollow', related_name='followed_orgs')
    related_orgs = models.ManyToManyField('self', symmetrical = False, through='RelatedOrg', related_name="orgrelatedorgs")
    working_locations = models.ManyToManyField(Location, null=True, symmetrical=False, related_name="working_locations",
                                               db_table="org_working_locations", verbose_name="Working In")
    issues = models.ManyToManyField(Issue, through='OrgIssueRelationship', verbose_name="Working On")
    commitments = generic.GenericRelation(Commitment)
    #aliases

    class Meta:
        verbose_name = "Org"
        verbose_name_plural = "Orgs"
        db_table = "orgs"

    def __unicode__(self):
        return self.name

    def save(self):
        #Note: I want to move all this img stuff to the forms that set them...
        #not here on the model. This is a hack so we ensure the model id is
        #used in the filename.
        if not self.id and not self.img_large_url._committed:
            #most likely you need to watch small img too
            small_url_comm = self.img_url._committed
            self.img_small_url._committed = True
            self.img_large_url._committed = True
            super(Org, self).save()
            self.img_large_url._committed = False
            self.img_small_url._committed = small_url_comm

        if not self.id and not self.img_small_url._committed:
            self.img_small_url._committed = True
            super(Org, self).save()
            self.img_small_url._committed = False

        self.img_large_url.storage.inst_id = self.id
        self.img_small_url.storage.inst_id = self.id
        super(Org, self).save()
        cache.bust(self)

    @models.permalink
    def get_absolute_url(self):
        return ('entity_url', [self.handle])

    @classmethod
    def get(cls, id, force_db=False):
        if force_db:
            org = Org.objects.get(id=id)
            cache.bust(org)
            return org
        return cache.get(cls, id)

    @classmethod
    def multiget(cls, ids, force_db=False):
        if force_db:
            return Org.objects.filter(id__in=ids)
        return cache.get(cls, ids)

    @property
    def get_image_small(self):
        if self.img_small_url:
            return self.img_small_url.url
        if self.facebook_id:
            return 'http://graph.facebook.com/%s/picture?type=square' % self.facebook_id
        return ''

    @property
    def get_image_large(self):
        if self.img_large_url:
            return self.img_large_url.url
        if self.facebook_id:
            return 'http://graph.facebook.com/%s/picture?type=large' % self.facebook_id
        return ''

    @property
    def get_url(self):
        return '/%s' % self.handle

    @property
    def get_name(self):
        return self.name

    @property
    @cache.collection_cache(Action, '_all_actions')
    def get_all_actions(self):
        return self.actions.all().order_by('rank')

    @property
    @cache.collection_cache(Advocate, '_all_advocates')
    def get_all_advocates(self):
        return self.advocates.all()

    @property
    @cache.collection_cache(TimelineItem, '_all_timeline_items')
    def get_all_timeline_items(self):
        return self.timeline.all().order_by('year')

    @property
    @cache.collection_cache(MediaItem, '_all_media_items')
    def get_all_media_items(self):
        return self.media.all().order_by('position')

    @property
    @cache.collection_cache(MediaItem, '_photo_media_items')
    def get_all_photos(self):
        return self.media.filter(media_type="photo").order_by('position')

    @property
    @cache.collection_cache(ContentItem, '_all_content')
    def get_all_content(self):
        return self.content.all().order_by('position')

    @property
    def get_sub_heading_text(self):
        t = ""
        if self.year_founded:
            t += "Since %s" % self.year_founded

        if self.get_location:
            if self.year_founded:
                t += " // "
            print t
            t += str(self.get_location)
            print t

        if self.size:
            if self.year_founded or self.get_location:
                t += " // "
            t += "%s employees" % self.size

        if self.revenue:
            if self.year_founded or self.size or self.get_location:
                t += " // "
            t += "%s revenue" % self.revenue

        if self.site_url:
            if self.year_founded or self.revenue or self.get_location or self.size:
                t += " // "
            t += self.site_url

        return t

    @property
    def get_left_section_content(self):
        return [item for item in self.get_all_content if item.section == ContentItem.ContentSection.LEFT]

    @property
    def get_center_section_content(self):
        return [item for item in self.get_all_content if item.section == ContentItem.ContentSection.CENTER]

    _location = None
    @property
    def get_location(self):
        if self._location is not None:
            return self._location
        self._location = self.location
        cache.put_on_handle(self, self.handle)
        return self._location

    @property
    @cache.collection_cache(Location, '_working_locations')
    def get_working_locations(self):
        return self.working_locations.all()

    @property
    @cache.collection_cache(User, '_admins')
    def get_admins(self):
        return self.admins.all()

    @property
    @cache.collection_cache(User, '_all_followers')
    def get_all_followers(self):
        commitments = self.commitments.active().select_related()
        return [c.user for c in commitments]

    @property
    def get_all_follower_ids(self):
        return self.usertoorgfollow_set.filter(following = True).values_list('user', flat=True)

    @property
    def get_num_followers(self):
        return self.commitments.active().count()

    @property
    def get_sample_followers(self):
        commitments = self.commitments.active()[:16].select_related()
        return [c.user for c in commitments]

    @property
    @cache.collection_cache(Issue, '_all_issues')
    def get_all_issues(self):
        return Issue.objects.filter(id__in = self.get_all_issues_ids)

    @property
    def get_all_issues_ids(self):
        return self.orgissuerelationship_set.values_list('issue', flat = True)

    @property
    @cache.collection_cache('org.Org', '_all_related_orgs')
    def get_all_related_orgs(self):
        return self.related_orgs.all()

    def get_related_orgs_for_user(self, user):
        if not hasattr(self, '_all_related_orgs') or getattr(self, '_all_related_orgs') is None:
            self.get_all_related_orgs
        pos = dict((id, idx) for idx, id in enumerate(self._all_related_orgs['ids']))
        orgs = sorted(list(set(self._all_related_orgs['ids']).difference(user.get_orgs_following_ids)), key=lambda id: pos[id])
        return list(cache.get(Org, orgs[0:5]))

    def delete(self):
        cache.bust_on_handle(self, self.handle, False)
        return super(self.__class__, self).delete()

    def is_editable_by(self, user):
        return not self.is_vetted and (user.is_staff or user in self.admins.all())

class Alias(models.Model):
    """
    Another name an org might be known as.
    """
    org = models.ForeignKey(Org)
    alias = models.CharField(max_length=200)
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Date Created")
    date_updated = models.DateTimeField(auto_now=True, verbose_name="Date Updated")

    class Meta:
        unique_together = (("org", "alias"),)
        db_table = 'org_alias'

    def __unicode__(self):
        return self.alias

class UserToOrgFollow(models.Model):
    following = models.BooleanField(default = True, db_index = True)
    started_following = models.DateTimeField(auto_now_add = True)
    stopped_following = models.DateTimeField(blank = True, null = True)
    user = models.ForeignKey(User)
    org = models.ForeignKey(Org)

    class Meta:
        unique_together = (("user", "org"),)
        verbose_name = "User Following Org"
        verbose_name = "Users Following Orgs"
        db_table = 'org_usertoorgfollow'

    def __unicode__(self):
        return "User '%s' following Org '%s'" % (self.user, self.org)


class RelatedOrg(models.Model):
    org = models.ForeignKey(Org, related_name="org")
    related_org = models.ForeignKey(Org, related_name="related_org")
    rank = models.FloatField()  #Value determined by magic algo that generated this item.
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Date Created")
    date_updated = models.DateTimeField(auto_now=True, verbose_name="Date Updated")

    class Meta:
        db_table = 'related_orgs'
        ordering = ['rank']
        unique_together = (("org", "rank"),)
        verbose_name = "Org's Related Org"
        verbose_name_plural = "Org's Related Orgs"


    def __unicode__(self):
        return "%s" % self.related_org

class OrgIssueRelationship(models.Model):
    org = models.ForeignKey(Org)
    issue = models.ForeignKey(Issue)
    rank = models.IntegerField(default=0) #This is manually managed for each org:issues relations.
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Date Created")
    date_updated = models.DateTimeField(auto_now=True, verbose_name="Date Updated")

    class Meta:
        ordering = ['rank']
        unique_together = (("org", "issue"),)
        verbose_name = "Org's Issue"
        verbose_name_plural = "Org's Issues"
        db_table = 'org_orgissuerelationship'

    def __unicode__(self):
        return "%s" % self.issue

########NEW FILE########
__FILENAME__ = tests
from etc.tests import ViewsBaseTestCase, BASIC_USER
from org.models import Org
from django.core.urlresolvers import reverse

"""FOR LATER

urlpatterns += patterns('org.views',
    url(r'^donate/(?P<handle>[0-9a-zA-Z\-_].*)/?$', 'donate', name = 'donate'),
    url(r'^org/(?P<mongo_id>[a-zA-Z0-9\-_].*)/?$', 'old_org_permalink', name = 'old_org_permalink'),
    url(r'^orgname/(?P<orgname>[a-zA-Z0-9\-_\ ].*)/?$', 'old_orgname_permalink', name = 'old_orgname_permalink'),
)
"""


class PageTests(ViewsBaseTestCase):
    
    def test_create_org(self):
        url = reverse('create_org')
        template = 'org/create.html'

        #Redirect if not logged in
        self.login_redirect_test(url, True)

        #Show page after login
        self.basic_200_test(url, template)


    #This is in the process of getting converted to a django form.
    #def test_manage_org(self):
    #    org_id = Org.objects.all()[0].id
    #
    #    good_url = reverse('manage_org', kwargs={'org_id':org_id})
    #    template = 'common/entity/manage.html'
    #    bad_url = reverse('manage_org', kwargs={'org_id':-1})
    #
    #    self.login_redirect_test(good_url)
    #
    #    #Raise 404 on invalid org id
    #    self.login()
    #    self.basic_404_test(bad_url)
    #
    #    #Should render correctly since we're logged in as staff
    #    self.basic_200_test(good_url, template)
    #
    #    #Raise 404 since we're a basic user
    #    self.logout()
    #    self.login(BASIC_USER)
    #    self.basic_404_test(good_url)

    def test_donate(self):
        handle = Org.objects.all()[0].handle
        pass


    def test_claim_org(self):
        org_id = Org.objects.all()[0].id
        good_url = "/org/claim/%s" % org_id
        good_template = 'org/claim.html'
        bad_url = "/org/claim/-1"

        #Not logged in should redirect
        self.login_redirect_test(good_url)

        #Should work after logging in
        self.login()
        self.basic_200_test(good_url, good_template)

        #404 if Org doesn't exist
        self.basic_404_test(bad_url)

    def test_claim_org_confirm(self):
        org_id = Org.objects.filter()[0].id
        org_url = reverse('claim_org_confirm', kwargs={'org_id':org_id})
        bad_url = reverse('claim_org_confirm', kwargs={'org_id':-1})

        template = 'org/claimed.html'

        #Requires logged in user
        self.login_redirect_test(org_url, True)

        #Raise 404 on invalid org
        self.basic_404_test(bad_url)
        self.basic_200_test(org_url, template)

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponsePermanentRedirect, Http404
from donation.forms import StandardDonationForm
from donation.models import Donation
from etc import cache
from etc.view_helpers import render, render_string, json_error, json_response, render_inclusiontag
from etc.decorators import AccountRequired
from etc.middleware import secure
from issue.models import Issue
import json
import logging
from org.models import Org
from users.models import User
#from utils.donations.nfg_api import NFGException
from utils import fb_helpers
from utils.misc_helpers import send_admins_error_email
from org.forms import ManageOrgForm, ManageOrgConnectForm, ManageOrgMoreForm, CreateOrgForm, DetailsOrgForm
from django.shortcuts import get_object_or_404, redirect

def old_orgname_permalink(request, orgname):
    try:
        o = Org.objects.get(name__iexact = orgname.lower())
        return HttpResponsePermanentRedirect(reverse('entity_url', args=[o.handle]))
    except:
        raise Http404

def old_org_permalink(request, mongo_id):
    try:
        o = Org.objects.get(mongo_id = mongo_id)
        return HttpResponsePermanentRedirect(reverse('entity_url', args=[o.handle]))
    except:
        raise Http404


@AccountRequired
def create_org(request):
    if request.POST:
        form = CreateOrgForm(request.POST)
        if form.is_valid():
            org = form.save()
            org.admins.add(request.user)
            return redirect('details_org', org.id)
    else:
        form = CreateOrgForm()

    return render(request, 'org/create.html', {
        'title': 'Add an organization',
        'form': form,
    })

@AccountRequired
def details(request, org_id):
    org = get_object_or_404(Org, id=org_id)
    if not org.is_editable_by(request.user):
        raise Http404

    if request.POST:
        form = DetailsOrgForm(request.POST, instance=org)
        if form.is_valid():
            form.save()
            return redirect('manage_org', org.id)
    else:
        form = DetailsOrgForm(instance=org)

    return render(request, 'org/details.html', {
        'form': form,
        'org': org,
    })

@AccountRequired
def manage_org(request, org_id, tab='about'):
    try:
        org = cache.get(Org, org_id)
    except Exception, inst:
        raise Http404
    if not org.is_editable_by(request.user):
        raise Http404

    if tab == 'about':
        form_class = ManageOrgForm
        form_url = reverse('manage_org', args=[org_id])
    elif tab == 'connect':
        form_class = ManageOrgConnectForm
        form_url = reverse('manage_org_connect', args=[org_id])
    elif tab == 'more':
        form_class = ManageOrgMoreForm
        form_url = reverse('manage_org_more', args=[org_id])

    success = False
    if request.method == "POST":
        form = form_class(request.POST, request.FILES, instance=org)
        if form.is_valid():
            form.save()
            success = True
    else:
        form = form_class(instance=org)

    return render(request, 'org/manage.html', {
        'title': 'Manage',
        'entity': org,
        'form': form,
        'form_url': form_url,
        'tab': tab,
        'success': success,
    })

@secure
def donate(request, handle):
    initial_amount = int(request.GET.get("amount", 0))
    initial_user = request.user if not request.user.is_anonymous() else None
    org = Org.objects.get(handle = handle)
    form = StandardDonationForm(initial_amount=initial_amount,initial_user=initial_user)

    if request.POST:
        form = StandardDonationForm(data=request.POST)
        if form.is_valid():
            donation_data = form.to_donation_data(org)
            try:
                donation = Donation.create_and_process(**donation_data)

                try:
                    #Post To Facebook
                    if form.cleaned_data.get("post_to_facebook") and initial_user:
                        fb_helpers.post_donation_to_wall(initial_user, org)
                    #Post To Stream
                    #if form.cleaned_data.get("list_name_publicly") and initial_user:
                        #FeedStream.post_new_donation(actor=initial_user, target=org, donation_id=donation.id)

                except Exception, ex:
                    logging.exception("FAILED TO SEND DONATE NOTIFICATION")
                    send_admins_error_email("FAILED TO SEND DONATE NOTIFICATION", ex.message, sys.exc_info())

                share_url = reverse('donate_share', args=[org.id])
		return HttpResponseRedirect("%s?amount=%s" % (share_url, donation.amount))

            #except NFGException, err:
            #    logging.exception("NFG ERROR PROCESSING STANDARD DONATION")
            #    if err.message.get("error_details"):
            #        form.handle_nfg_errors(err.message["error_details"])
            #    else:
            #        form.handle_unknown_error()
            except Exception, err:
                logging.exception("ERROR PROCESSING STANDARD DONATION")
                form.handle_unknown_error()

    return render(request, 'org/donate.html', {
            'type':'org_donate',
            'form' : form,
            'org' : org,
            'title' : org.get_name
            })


def share(request, org_id):
    amount = request.GET.get('amount', None)
    org = Org.objects.get(id = org_id)

    return render(request, 'org/donate_success.html', {
            'amount':amount,
            'org':org,
            'title':'Share your donation to %s' % org.get_name
            })


@AccountRequired
def claim_org(request, org_id):
    try:
        org = Org.objects.get(id = org_id)
    except:
        raise Http404

    return render(request, 'org/claim.html', {'org' : org})

@AccountRequired
def claim_org_confirm(request, org_id):
    try:
        org = Org.objects.get(id = org_id)
    except:
        raise Http404

    return render(request, 'org/claimed.html', {'org' : org})


# cache this bad boy for 6 hours
#@cache_page(60*360)
def org_categories(request):
    categories = Issue.objects.filter(parent_issue__isnull = True).filter(is_active = True).order_by('name')

    js_cats = ['']
    js_subcats = []
    js_issues = []

    for cat in categories:
        if len(cat.issue_set.all()) == 0:
            continue
        # FIXME: delete the following line whenever the CMS gets cleaned up
        #cat.name = ' '.join(i.capitalize() for i in cat.name.split(' '))
        js_cats.append(cat.name)
        subcats = Issue.objects.filter(parent_issue = cat).filter(is_active = True).order_by('name')
        if not subcats:
            js_subcats.append({'text':cat.name, 'when':cat.name, 'value':cat.name.lower()})
            js_issues.append({'text':cat.name, 'when':cat.name.lower(), 'value':cat.name.lower()})
        else:
            js_subcats.append({'text':cat.name, 'when':cat.name, 'value':cat.name.lower()})
            js_issues.append({'text':cat.name, 'when':cat.name.lower(), 'value':cat.name.lower()})
            for subcat in subcats:
                # FIXME: delete the following line whenever the CMS gets cleaned up
                #subcat.name = ' '.join(i.capitalize() for i in subcat.name.split(' '))
                js_subcats.append({'text':subcat.name, 'when':cat.name.lower(), 'value':subcat.name.lower()})
                issues = Issue.objects.filter(parent_issue = subcat).filter(is_active = True).order_by('name')
                if not issues:
                    js_issues.append({'text':subcat.name, 'when':subcat.name.lower(), 'value':subcat.name.lower()})
                else:
                    js_issues.append({'text':subcat.name, 'when':subcat.name.lower(), 'value':subcat.name.lower()})
                    for issue in issues:
                        # FIXME: delete the following line whenever the CMS gets cleaned up
                        #issue.name = ' '.join(i.capitalize() for i in issue.name.split(' '))
                        js_issues.append({'text':issue.name, 'when':subcat.name.lower(), 'value':issue.name.lower()})


    r = HttpResponse('var TOP_LEVEL_CATEGORIES=%s,ORG_SUB_CATEGORIES=%s,ORG_ISSUES=%s;' % (json.dumps(js_cats), json.dumps(js_subcats), json.dumps(js_issues)))
    return r

def followed_org_list(request, user_id):
    start = int(request.GET.get('start', 0))
    end = int(request.GET.get('end', 20))
    user = get_object_or_404(User, id=user_id)
    org_commitments = user.commitments.with_orgs()[start:end].fetch_generic_relations()
    orgs = [commitment.entity for commitment in org_commitments]
    num_orgs = user.commitments.with_orgs().count()

    html = render_string(request, "org/includes/followed_org_list.html", {
        'orgs': orgs,
        'start_index': start,
    })

    return json_response({
        'html': html,
        'has_more': end < num_orgs,
    })

########NEW FILE########
__FILENAME__ = admin
from django import forms
from django.contrib import admin

from django.forms.models import BaseModelFormSet
from django.contrib.sites.models import Site
from popularity.models import TopList, TopListItem, Section
from etc.entities import obj_to_type
from cust_admin.views.main import ExtChangeList
from cust_admin.widgets import ForeignKeyToObjWidget
from cust_admin.forms import HiddenRankModelForm

#class TopListItemInline(admin.StackedInline):
#    model = TopListItem
#    extra = 0
#    verbose_name = 'List Item'
#    verbose_name_plural = 'List Items'

class TopListItemInline(admin.TabularInline):
    model = TopListItem
    extra = 0
    fields = ('entity_content_type', 'entity_id', 'rank')
    form = HiddenRankModelForm

    sortable_field_name = "rank"

    verbose_name = "Item"
    verbose_name_plural = "Items"

    related_lookup_fields = {
        'generic': [['entity_content_type', 'entity_id']],
    }

class TopListAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'is_current')
    list_editable = ('section', 'is_current',)
    inlines = [TopListItemInline]


class TopListInline(admin.TabularInline):
    model = TopList
    extra = 0
    fields = ('title', 'is_current', 'position')
    form = HiddenRankModelForm

    sortable_field_name = 'position'
    verbose_name = 'List'
    verbose_name_plural = 'Lists'

class SectionAdmin(admin.ModelAdmin):
    inlines = [TopListInline]

admin.site.register(TopList, TopListAdmin)
admin.site.register(Section, SectionAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models
import datetime
from etc.entities import type_to_class, obj_to_type
from etc import cache
from collections import defaultdict, OrderedDict
from itertools import groupby
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

class Sections:
    HOME = 1
    SIGNED_IN_HOME = 2

class TopListItem(models.Model):
    id = models.AutoField(db_column='list_item_id', primary_key=True)
    list = models.ForeignKey('popularity.TopList', db_column='list_id')
    entity_content_type = models.ForeignKey(ContentType, db_column='entity_content_type',
                                            default=ContentType.objects.get(model="Issue").id,
                                            limit_choices_to={"model__in": ("Org", "Issue", "User"), "app_label__in": ("org", "issue", "users")})
    entity_type = models.CharField(max_length=50, db_column='entity_type')
    entity_id = models.PositiveIntegerField(db_column='entity_id')
    entity = generic.GenericForeignKey('entity_content_type', 'entity_id')
    rank = models.PositiveIntegerField(db_column='rank')
    date_created = models.DateTimeField(db_column='date_created', auto_now_add=True)
    last_modified = models.DateTimeField(db_column='last_modified', auto_now=True)

    class Meta:
        db_table = 'top_list_items'
        ordering = ['rank']

    def __unicode__(self):
        return u' - '.join([unicode(self.rank), unicode(self.entity)])

    def save(self):
        if not self.entity_type:
            self.entity_type=obj_to_type(self.entity)
        self.last_modified = datetime.datetime.utcnow()
        super(TopListItem, self).save()

class ListType(models.Model):
    id = models.AutoField(db_column='list_type_id', primary_key=True)
    name = models.CharField(max_length=75, db_column='name')

    class Meta:
        db_table = 'top_list_types'

    def __unicode__(self):
        return self.name

class TopList(models.Model):
    id = models.AutoField(db_column='list_id', primary_key=True)
    title = models.CharField(max_length=75, db_column='title')
    valid_from = models.DateField(db_column='valid_from', default=datetime.date.today)
    valid_to = models.DateField(db_column='valid_to', default=datetime.date(9999,12,31))
    is_current = models.BooleanField(db_column='is_current', default=True)
    section = models.ForeignKey('popularity.Section', db_column='section_id', null=True, blank=True, default=Sections.HOME)
    position = models.PositiveIntegerField(db_column='position', default=0)
    date_created = models.DateTimeField(db_column='date_created', auto_now_add=True)
    last_modified = models.DateTimeField(db_column='last_modified', auto_now=True)

    class Meta:
        db_table='top_lists'

    def __unicode__(self):
        return self.title

    def save(self):
        self.last_modified = datetime.datetime.utcnow()
        cache.bust(self)
        super(TopList, self).save()

    @classmethod
    def get(cls, id, force_db=False):
        if force_db:
            top_list = TopList.objects.get(id=id)
            cache.bust(top_list)
            return top_list
        return cache.get(cls, id)

    @classmethod
    def multiget(cls, ids, force_db=False):
        if force_db:
            return TopList.objects.filter(id__in=ids)
        return cache.get(cls, ids)

    @property
    @cache.collection_cache(TopListItem, '_list_item_ids')
    def get_items(self):
        return list(TopListItem.objects.filter(list=self).order_by('rank'))

    @classmethod
    def multiget_items(cls, ids):
        return TopListItem.objects.filter(list__in=ids).order_by('list', 'rank')

    @classmethod
    def get_entities_for_lists(cls, ids):
        """ This method actually returns the orgs, etc. for some lists """

        lists = TopList.multiget(ids)
        list_names = dict((l.id, l.title) for l in lists)

        # list of lists, return value
        top_lists = OrderedDict()
        
        # item_id => entity
        item_id_dict = {}
        entity_dict = {}

        list_id_dict = defaultdict(list)
        
        all_items=TopList.multiget_items(ids)
        # Spits out a dict like {1: [TopListItem(...), TopListItem(...)] }
        [list_id_dict[item.list_id].append(item) for item in all_items]

        keyfunc = lambda item: item.entity_content_type_id

        # Can potentially have hybrid featured lists,
        # so use groupby
        for entity_type, list_items in groupby(sorted(all_items, key=keyfunc), keyfunc):
            item_entity_dict = dict((i.id, i.entity_id) for i in list_items)
            
            cls = ContentType.objects.get(id=entity_type).model_class()            
            entities = cls.multiget(set(item_entity_dict.values()))
            for ent in entities:
                entity_dict[(entity_type, ent.id)] = ent
 
        for list_id in ids:
            entities = [entity_dict[(item.entity_content_type_id, item.entity_id)] for item in list_id_dict[list_id]]
            top_lists[list_names[list_id]] = entities

        return top_lists

class Section(models.Model):
    id = models.AutoField(db_column='section_id', primary_key=True)
    name = models.CharField(max_length=100, db_column='name')

    class Meta:
        db_table='sections'

    def __unicode__(self):
        return self.name

    @classmethod
    def get_lists(cls, id):
        return list(TopList.objects.filter(section=id, is_current=True).order_by('position'))

########NEW FILE########
__FILENAME__ = tasks
'''
Created on Apr 28, 2011

@author: al
'''

from celery.task import Task
from contextlib import contextmanager
from django.core.cache import cache
from django.db import connections
from users.models import User
from issue.models import Issue
from org.models import Org
from collections import namedtuple
from popularity.models import TopList, TopListItem

LOCK_EXPIRE = 60*5

class TaskLockedException(Exception):
    pass

class BasePopularity(Task):
    name = None

    @property
    def cache_key(self):
        if self.name is None:
            raise Exception('Name your tasks fooool!')
        return '%s-lock' % self.name

    @contextmanager
    def task_lock(self):
        try:
            cache.add(self.cache_key, 'true', LOCK_EXPIRE)
            yield
        except Exception:
            raise TaskLockedException('This task is already locked')
        finally:
            cache.delete(self.cache_key)

    def get_items_for_list(self, limit):
        raise NotImplementedError('Children need to implement their own')

    def update_list(self, items):
        pass

    def run(self):
        with self.task_lock():
            # Do stuff
            items = self.get_items_for_list()
            self.update_list(items)

class OrgPopularity(BasePopularity):
    name = 'org.popularity'
    list_type_id = 2

    def get_items_for_list(self, limit):
        return Issue.objects.raw("""
        select o.id
        from org_org o
        join org_usertoorgfollow uo
          on uo.org_id = o.id
          and uo.following=1
        group by o.id
        order by count(*) desc
        limit %(limit)s
        """, {'limit': limit})


class IssuePopularity(BasePopularity):
    name = 'issue.popularity'
    list_type_id = 3

    def get_items_for_list(self, limit):
        return Issue.objects.raw("""
        select i.id
        from issue_issue i
        join issue_usertoissuefollow ui
          on ui.issue_id = i.id
          and ui.following=1
        group by i.id
        order by count(*) desc
        limit %(limit)s
        """, {'limit': limit})

########NEW FILE########
__FILENAME__ = tests


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = config
import bebop
import settings
from jumodjango import search

solr = bebop.Solr()
solr.add_connection(settings.SOLR_CONN)
solr.autodiscover_indexes(search)

########NEW FILE########
__FILENAME__ = indexes
from bebop import *
from django.db import models
import copy
import cPickle as pickle
from config import solr

@SearchIndex('autocomplete', config=config.DismaxSolrConfig)
class Autocomplete(object):
    id = model.StrField('id', document_id=True)
    type = model.StrField('type')
    exact_name = model.StrField('exact_name')
    name = model.TitleField('name', multi_valued=True)
    geo_location = model.GeoPointField('geo_location', stored=False)
    stored_issues = model.StrField('stored_issues', multi_valued=True, indexed=False)
    locations = model.TitleField('locations', multi_valued=True)
    is_vetted = model.BooleanField('is_vetted')
    location_classifiers = model.StrField('location_classifiers', stored=False, multi_valued=True)

    # Followers for now, used mainly for boosting
    popularity = model.IntegerField('popularity')
    # Stored not indexed, for display
    summary = model.StrField('summary', indexed=False)
    # Indexed but not stored, stick content and any other
    # words we want to search on in here
    keywords = model.TextField('keywords', stored=False)

    url = model.StrField('url', indexed=False, stored=True)
    image_url = model.StrField('image_url', indexed=False, stored=True)

    @property
    def get_name(self):
        return self.exact_name

    @property
    def get_url(self):
        return self.url

    @property
    def get_image_small(self):
        return self.image_url

    @property
    def get_all_issues(self):
        return [pickle.loads(str(issue)) for issue in self.stored_issues if issue]

    @classmethod
    def from_model(cls, entity):
        # TODO: declarative way to do this in bebop
        model_type = entity.__class__.__name__
        primary_location = None
        location_classes = set()
        for location in entity.search_all_locations:
            if location:
                if location.classification:
                    location_classes.add(location.classification)

                if not primary_location and location.latitude and location.longitude:
                    primary_location = location

        index = Autocomplete(id = ':'.join([model_type, str(entity.id)]),
                            type = model_type,
                            exact_name = entity.search_exact_name,
                            name = entity.search_all_names,
                            is_vetted = entity.search_jumo_vetted,
                            locations = [unicode(loc) for loc in entity.search_all_locations],
                            popularity = entity.search_popularity,
                            summary = getattr(entity, 'summary', None),
                            keywords = entity.search_keywords,
                            url = entity.get_url,
                            image_url = entity.get_image_small,
                            )
        if location_classes:
            index.location_classifiers = location_classes

        if hasattr(entity, 'search_all_issues'):
            index.stored_issues = [pickle.dumps(issue) for issue in entity.search_all_issues]

        if primary_location:
            index.geo_location = ','.join([str(primary_location.latitude), str(primary_location.longitude)])

        return index

    @classmethod
    def base_params(cls):
        return solr.search(Autocomplete)\
            .dismax_of(Autocomplete.name, Autocomplete.locations, Autocomplete.keywords**0.8)\
            .boost(func.log(Autocomplete.popularity)).default_query('*:*')\
            .boost(Autocomplete.is_vetted**5)\
            .phrase_boost(Autocomplete.name, Autocomplete.locations, Autocomplete.keywords**0.8)\
            
    @classmethod
    def autocomplete(cls, term, limit=10):
        term = term.rsplit(' ', 1)
        if len(term) > 1:
            term, prefix = term
        else:
            term, prefix = None, term[0]
        
        q = Autocomplete.base_params().limit(limit)
        if term:
            q = q.query(term)
            
        # @TODO: try to find a better way to do prefix faceting, these puppies are case sensitive
        prefix = prefix.lower()
        q.facet_prefix(Autocomplete.name, prefix)
        
        res = q.execute()
        return [' '.join([term, completion]) if term else completion for completion in res.facet_fields[Autocomplete.name]]

    @classmethod
    def near_me(cls, term, latitude, longitude, distance, limit = 5):
        q = Autocomplete.base_params().query(term).limit(limit).filter(or_(Autocomplete.type=='Org', Autocomplete.type=='Issue'))

        # TODO: bebop support for all this
        q.params['d'] = distance
        q.params['sfield'] = Autocomplete.geo_location
        q.params['pt'] = ','.join([str(latitude), str(longitude)])

        q.filter('{!geofilt}')
        q.boost('recip(geodist(),2,200,20)')

        return q.execute()

    @classmethod
    def search(cls, term, limit=20, offset=0, with_facets=True, restrict_type = None, restrict_location = None):
        q = Autocomplete.base_params().limit(limit).offset(offset)
        if term:
            q.query(term)
        else:
            q.filter(or_(Autocomplete.type=='Org', Autocomplete.type=='Issue'))

        do_exclusions = restrict_type and restrict_type != 'All Results'

        if with_facets:
            q.facet(Autocomplete.type, method='enum')
            if do_exclusions:
                # TODO: add tag exclusions to bebop's faceting
                tag = 'selected'
                q.filter((Autocomplete.type==restrict_type).tag(tag))
                q.params['facet.field'] = LuceneQuery(Autocomplete.type)
                q.params['facet.field'].local_params.add('ex', tag)
                q.params['facet.field'] = unicode(q.params['facet.field'])[:-1]

        if restrict_location and restrict_location != 'All':
            q.filter(Autocomplete.location_classifiers==restrict_location)

        results = q.execute()
        # Slight hack, TODO: implement facet exclusions in bebop
        if do_exclusions:
            results.all_results=sum(results.facet_fields['type'].values())
        else:
            results.all_results=results.hits
        return results
########NEW FILE########
__FILENAME__ = reindex_solr
#!/usr/bin/env python
# django environment setup
import sys, os
sys.path.append(os.path.realpath(os.sep.join([os.path.dirname(__file__), os.pardir])))

from django.core.management import setup_environ
import settings
setup_environ(settings)

from django.db.models.loading import cache
cache._populate()


from bebop import *

from django.contrib.contenttypes.models import ContentType
from django.db import models
from indexes import Autocomplete
from org.models import Org
from issue.models import Issue
from users.models import User, Location
from config import solr

import MySQLdb
from MySQLdb import cursors

# Get the content types up front for the queries
org_content_type = str(ContentType.objects.get(model='org').id)
issue_content_type = str(ContentType.objects.get(model='issue').id)
user_content_type = str(ContentType.objects.get(app_label='users',model='user').id)

queries = {Org: """
    select
    o.org_id,
    o.name as search_exact_name,
    o.name as search_all_names,
    o.handle,
    img_small_url,
    img_large_url,
    facebook_id,
    concat_ws(',', o.location_id, group_concat(distinct owl.location_id)) as location_ids,
    group_concat(oi.issue_id) as issue_ids,
    count(distinct c.user_id) as search_popularity,
    o.summary,
    o.is_vetted as search_jumo_vetted,
    group_concat(distinct ci.body separator ' ') as search_keywords
    from
    orgs o
    left join content_items ci
        on ci.content_type_id=""" + org_content_type + """
        and ci.object_id = o.org_id
    left join users_location l
        on o.location_id = l.id
    left join commitments c
        on c.content_type_id=""" + org_content_type + """
        and c.object_id = o.org_id
    left join org_working_locations owl
        using(org_id)
    left join org_orgissuerelationship oi
        using(org_id)
    where o.is_active=1
    group by o.org_id""",
    
Issue: """
    select
    i.issue_id,
    i.handle,
    i.name as search_exact_name,
    i.name as search_all_names,
    count(distinct c.user_id) as search_popularity,
    i.location_id as location_ids,
    i.summary,
    i.img_large_url,
    i.img_small_url,
    i.content_upgraded as search_jumo_vetted,
    group_concat(ci.body separator ' ') as search_keywords
    from
    issues i
    left join content_items ci
        on ci.content_type_id=""" + issue_content_type + """
        and ci.object_id = i.issue_id
    left join commitments c
        on c.content_type_id=""" + issue_content_type + """
        and c.object_id = i.issue_id
    where i.is_active = 1
    group by i.issue_id
    """,
User: """
    select
    au.id,
    au.username,
    u.thumb_img_url,
    u.facebook_id,
    concat_ws(' ', au.first_name, au.last_name) search_exact_name,
    case when u.likely_org = 1 and not u.admin_classification <=> 'user' then '' else concat_ws(' ', au.first_name, au.last_name) end as search_all_names,
    u.location_id as location_ids,
    count(distinct case when uu.is_following=1 then uu.follower_id end) as search_popularity,
    concat(rtrim(substring(bio, 1, 255)), if(char_length(bio) > 255, '...', '')) as summary,
    null as search_keywords,
    0 as search_jumo_vetted
    from
    auth_user au
    join users_user u
      on au.id = u.user_ptr_id
    left join users_usertouserfollow uu
      on uu.followed_id = u.user_ptr_id
    where au.is_active = 1
    group by u.user_ptr_id
    """
}


class JumoSolrIndexer(DBAPIBatchIndexer):
    def with_model(self, model):
        self.model = model
        self.model_mapper = dict((field.column, field.name) for field in model._meta.fields)
        return self

    def populate_issues(self):
        self.issue_dict = dict((i.id, i) for i in Issue.objects.only('id', 'name', 'handle', 'content_upgraded'))
        return self

    def populate_locations(self):
        # Keep an object cache of the locations so we're not issuing too many queries
        self.location_dict = dict((l.id, l) for l in Location.objects.all())
        return self

    def transform_locations(self, row):
        location_ids = row.pop('location_ids', [])
        if location_ids is None:
            location_ids = []
        else:
            location_ids = str(location_ids).split(',')
        if not hasattr(location_ids, '__iter__'):
            location_ids = [location_ids]

        # Preserve order but remove dupes
        location_ids = OrderedSet(location_ids)
        row['search_all_locations'] = [self.location_dict.get(int(location_id)) for location_id in location_ids if location_id]

    def transform_issues(self, row):
        issue_ids = row.pop('issue_ids', [])
        if issue_ids:
            issue_ids = str(issue_ids).split(',')
        elif issue_ids is None:
            issue_ids = []

        if not hasattr(issue_ids, '__iter__'):
            issue_ids = [issue_ids]

        issue_ids = OrderedSet(issue_ids)
        if issue_ids:
            row['search_all_issues'] = [self.issue_dict.get(int(issue_id)) for issue_id in issue_ids if issue_id]

    def transform_names(self, row):
        row['search_all_names'] = row['search_all_names'].split(',')

    def handle_row(self, row):
        if row.has_key('location_ids'):
            self.transform_locations(row)

        self.transform_names(row)
        self.transform_issues(row)
        # Again, write a nicer way to do this part and just call super
        model = self.model()
        [setattr(model, self.model_mapper.get(k, k), v) for k,v in row.iteritems()]

        return Autocomplete.from_model(model)

        #self.solr_conn.add(docs, commit=False)

    def commit(self):
        self.solr_conn.commit()

def main():
    database = settings.DATABASES['default']

    db_conn = MySQLdb.connect(
        host = database['HOST'],
        user = database['USER'],
        passwd = database['PASSWORD'],
        db = database['NAME'],
        cursorclass = cursors.SSDictCursor, # USE A SERVER-SIDE CURSOR FOR ETL!!! MUY IMPORTANTE!
        charset = 'utf8',
        use_unicode=True
    )
    cur = db_conn.cursor()

    indexer = solr.batch_index(Autocomplete, indexer=JumoSolrIndexer).populate_locations().populate_issues().cursor(cur)
    indexer.db_cursor.execute("set group_concat_max_len=65535")

    for model, query in queries.iteritems():
        indexer.with_model(model)

        print "Doing", model.__name__,"now..."
        indexer.execute(query)

        indexer.index_all()

    indexer.solr_conn.commit()

    db_conn.close()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = search
from users.models import User
from org.models import Org
from issue.models import Issue
import pysolr
import settings

class Search:
    @classmethod
    def search(cls, term, limit=20, restrict_type = None):
        results = []
        params = {'defType': 'dismax',
                  'rows': limit,
                  'start': 0,
                  'qf': 'name locations keywords^0.8',
                  'bf': 'social_score'}

        if restrict_type and restrict_type != 'all_orgtypes':
            params['qf'] = list(params['qf'])
            params['qf'].append('id:%s*' % restrict_type)

        solr = pysolr.Solr(settings.SOLR_CONN)
        results = solr.search(term, **params)

        return results
########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from etc.view_helpers import json_response
from etc.templatetags.tags import _create_static_url

import settings
import urllib
import urllib2
import json
from indexes import Autocomplete
from etc.view_helpers import render, render_string, json_response
from miner.web.ip_lookup import ip_to_lat_lon

DEFAULT_LIMIT = 20

def _get_orgs_near_me(request, query, lat=None, lon=None, distance=40, limit=3):
    orgs_near_me = []
    if not (lat and lon):
        location = ip_to_lat_lon(request.META.get('HTTP_X_FORWARDED_FOR'))
        lat, lon = location.get('latitude'), location.get('longitude')

    if lat and lon:
        # New York = 40.7834345, -73.9662495
        orgs_near_me = Autocomplete.near_me(query, lat, lon, distance, limit)

    return orgs_near_me

def _get_related_searches(query):
    if not query:
        return []

    try:        
        resp = urllib2.urlopen(settings.DATAMINE_BASE + '/related_searches?%s' % urllib.urlencode(dict(q=query)), timeout=2).read()
    
        result = json.loads(resp).get('result', [])
    except Exception, e:
        print 'EXCEPTION', e
        return []

    good_results = []
    for res, prob in result:
        if res.lower() != query.lower():
            good_results.append(res)
    return good_results
            
def ajax_search(request):
    search_results = []
    query = request.GET.get('q', None)

    selected_facet = request.GET.get('type', None)
    try:
        limit = int(request.GET.get('limit', DEFAULT_LIMIT))
    except ValueError:
        limit = DEFAULT_LIMIT

    try:
        offset = int(request.GET.get('offset', 0))
    except ValueError:
        offset = 0

    search_results = Autocomplete.search(query, restrict_type=selected_facet, limit=limit, offset=offset,
                                         restrict_location = request.GET.get('location', None))

    lat, lon = request.GET.get('lat', None), request.GET.get('lng', None)
    orgs_near_me = _get_orgs_near_me(request, query, lat, lon)
    more_results = (search_results.hits - int(offset)) > limit
    related_searches = _get_related_searches(query)

    if 'format' in request.GET and request.GET['format']=='html':
        ret = {'items': render_string(request, 'search/search_items.html', {'search_results' : search_results, 'query': query}),
               'facets': render_string(request, 'search/facets.html', {'search_results': search_results, 'selected_facet': selected_facet, 'query': query}),
               'related': render_string(request, 'search/related_searches.html', {'related_searches': related_searches}),
               'more_results': render_string(request, 'search/more_results.html', {'more_results': more_results})
               }

        if orgs_near_me:
            ret['nearMe'] = render_string(request, 'search/near_me.html', {'orgs_near_me': orgs_near_me})

        return json_response(ret)

def search_page(request):
    search_results = []
    orgs_near_me = []
    query = request.GET.get('q',None)
    search_results = Autocomplete.search(query)
    orgs_near_me = _get_orgs_near_me(request, query)
    more_results = search_results.hits > DEFAULT_LIMIT    
    related_searches = _get_related_searches(query)

    more_results = search_results.hits > DEFAULT_LIMIT

    title = "for %s" % query if query else ''

    return render(request, 'search/base.html', {
            'search_results' : search_results,
            'more_results': more_results,
            'query': query,
            'orgs_near_me': orgs_near_me,
            'related_searches': related_searches,
            'title' : "Search %s" % title
            })


def ajax_term_complete(request):
    """Term prefix autocomplete, Google-style, completes the phrase"""
    results = {}
    term = request.GET.get('q', None)
    results = Autocomplete.autocomplete(term)
    return json_response(results)

def autocomplete(request):
    """Legacy autocomplete, still used in the top search bar around the site"""
    def _format_search_result(res, idx):
        type, id = res.id.split(':')
        image_url = res.image_url
        if image_url and not image_url.startswith('http'):
            image_url=_create_static_url(image_url)

        return {'id' : id, 'index': idx, 'name' : res.name[0], 'type' : type, 'url' : res.url,
                'image_url' : image_url, 'num_followers' : res.popularity}

    results = Autocomplete.search(request.GET['search'])
    return json_response([_format_search_result(t, idx) for idx, t in enumerate(results)])

########NEW FILE########
__FILENAME__ = facebook
#!/usr/bin/env python
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Python client library for the Facebook Platform.

This client library is designed to support the Graph API and the official
Facebook JavaScript SDK, which is the canonical way to implement
Facebook authentication. Read more about the Graph API at
http://developers.facebook.com/docs/api. You can download the Facebook
JavaScript SDK at http://github.com/facebook/connect-js/.

If your application is using Google AppEngine's webapp framework, your
usage of this module might look like this:

    user = facebook.get_user_from_cookie(self.request.cookies, key, secret)
    if user:
        graph = facebook.GraphAPI(user["access_token"])
        profile = graph.get_object("me")
        friends = graph.get_connections("me", "friends")

"""

import cgi
import hashlib
import time
import urllib

# Find a JSON parser
try:
    import json
    _parse_json = lambda s: json.loads(s)
except ImportError:
    try:
        import simplejson
        _parse_json = lambda s: simplejson.loads(s)
    except ImportError:
        # For Google AppEngine
        from django.utils import simplejson
        _parse_json = lambda s: simplejson.loads(s)


class GraphAPI(object):
    """A client for the Facebook Graph API.

    See http://developers.facebook.com/docs/api for complete documentation
    for the API.

    The Graph API is made up of the objects in Facebook (e.g., people, pages,
    events, photos) and the connections between them (e.g., friends,
    photo tags, and event RSVPs). This client provides access to those
    primitive types in a generic way. For example, given an OAuth access
    token, this will fetch the profile of the active user and the list
    of the user's friends:

       graph = facebook.GraphAPI(access_token)
       user = graph.get_object("me")
       friends = graph.get_connections(user["id"], "friends")

    You can see a list of all of the objects and connections supported
    by the API at http://developers.facebook.com/docs/reference/api/.

    You can obtain an access token via OAuth or by using the Facebook
    JavaScript SDK. See http://developers.facebook.com/docs/authentication/
    for details.

    If you are using the JavaScript SDK, you can use the
    get_user_from_cookie() method below to get the OAuth access token
    for the active user from the cookie saved by the SDK.
    """
    def __init__(self, access_token=None):
        self.access_token = access_token

    def get_object(self, id, **args):
        """Fetchs the given object from the graph."""
        return self.request(id, args)

    def get_objects(self, ids, **args):
        """Fetchs all of the given object from the graph.

        We return a map from ID to object. If any of the IDs are invalid,
        we raise an exception.
        """
        args["ids"] = ",".join(ids)
        return self.request("", args)

    def get_connections(self, id, connection_name, **args):
        """Fetchs the connections for given object."""
        return self.request(id + "/" + connection_name, args)

    def put_object(self, parent_object, connection_name, **data):
        """Writes the given object to the graph, connected to the given parent.

        For example,

            graph.put_object("me", "feed", message="Hello, world")

        writes "Hello, world" to the active user's wall. Likewise, this
        will comment on a the first post of the active user's feed:

            feed = graph.get_connections("me", "feed")
            post = feed["data"][0]
            graph.put_object(post["id"], "comments", message="First!")

        See http://developers.facebook.com/docs/api#publishing for all of
        the supported writeable objects.

        Most write operations require extended permissions. For example,
        publishing wall posts requires the "publish_stream" permission. See
        http://developers.facebook.com/docs/authentication/ for details about
        extended permissions.
        """
        assert self.access_token, "Write operations require an access token"
        return self.request(parent_object + "/" + connection_name, post_args=data)

    def put_wall_post(self, message, attachment={}, profile_id="me"):
        """Writes a wall post to the given profile's wall.

        We default to writing to the authenticated user's wall if no
        profile_id is specified.

        attachment adds a structured attachment to the status message being
        posted to the Wall. It should be a dictionary of the form:

            {"name": "Link name"
             "link": "http://www.example.com/",
             "caption": "{*actor*} posted a new review",
             "description": "This is a longer description of the attachment",
             "picture": "http://www.example.com/thumbnail.jpg"}

        """
        return self.put_object(profile_id, "feed", message=message, **attachment)

    def put_comment(self, object_id, message):
        """Writes the given comment on the given post."""
        return self.put_object(object_id, "comments", message=message)

    def put_like(self, object_id):
        """Likes the given post."""
        return self.put_object(object_id, "likes")

    def delete_object(self, id):
        """Deletes the object with the given ID from the graph."""
        self.request(id, post_args={"method": "delete"})

    def request(self, path, args=None, post_args=None):
        """Fetches the given path in the Graph API.

        We translate args to a valid query string. If post_args is given,
        we send a POST request to the given path with the given arguments.
        """
        if not args: args = {}
        if self.access_token:
            if post_args is not None:
                post_args["access_token"] = self.access_token
            else:
                args["access_token"] = self.access_token
        post_data = None if post_args is None else urllib.urlencode(post_args)
        file = urllib.urlopen("https://graph.facebook.com/" + path + "?" +
                              urllib.urlencode(args), post_data)
        try:
            response = _parse_json(file.read())
        finally:
            file.close()
        if response.get("error"):
            raise GraphAPIError(response["error"]["type"],
                                response["error"]["message"])
        return response


class GraphAPIError(Exception):
    def __init__(self, type, message):
        Exception.__init__(self, message)
        self.type = type


def get_user_from_cookie(cookies, app_id, app_secret):
    """Parses the cookie set by the official Facebook JavaScript SDK.

    cookies should be a dictionary-like object mapping cookie names to
    cookie values.

    If the user is logged in via Facebook, we return a dictionary with the
    keys "uid" and "access_token". The former is the user's Facebook ID,
    and the latter can be used to make authenticated requests to the Graph API.
    If the user is not logged in, we return None.

    Download the official Facebook JavaScript SDK at
    http://github.com/facebook/connect-js/. Read more about Facebook
    authentication at http://developers.facebook.com/docs/authentication/.
    """
    cookie = cookies.get("fbs_" + app_id, "")
    if not cookie: return None
    args = dict((k, v[-1]) for k, v in cgi.parse_qs(cookie.strip('"')).items())
    payload = "".join(k + "=" + args[k] for k in sorted(args.keys())
                      if k != "sig")
    sig = hashlib.md5(payload + app_secret).hexdigest()
    expires = int(args["expires"])
    if sig == args.get("sig") and (expires == 0 or time.time() < expires):
        return args
    else:
        return None

########NEW FILE########
__FILENAME__ = volunteermatch
#!/usr/bin/env python
from httplib2 import Http
import md5
from hashlib import sha1,sha256
from base64 import b64encode
from urllib import quote
import json
import time
import random


class VolunteerMatch(object):
    """Volunteer Match API Class"""
    def __init__(self,username,password):
        self.username = username
        self.password = password
        self._authorize()
        self.http = Http()
        self.http.follow_all_redirects = True

    def _authorize(self):
        self._gen_auth_headers()

    def _gen_auth_headers(self):
        # generate the annoying wsse headers
        nonce = self._gen_nonce()
        create_time = self._gen_time()
        digest = self._gen_pass_digest(self.password,create_time,nonce)
        headers = {}
        headers['content-type'] = 'application/json'
        headers['Authorization'] = 'WSSE profile="UsernameToken"'
        headers['X-WSSE'] = 'UsernameToken Username="%s", PasswordDigest="%s", Nonce="%s", Created="%s"' % (self.username, digest, nonce, create_time)
        self.headers = headers

    def hello(self):
        return self._call_volmatch("helloWorld", {'name' : 'John' })

    def get_key_status(self):
        return self._call_volmatch('getKeyStatus',{})

    def get_metadata():
        # getMetaData
        pass

    def get_service_status():
        #getServiceStatus
        pass

    def search_volops(self,**kwargs):
        if kwargs.has_key('virtual') or kwargs.has_key('location'):
            return self._call_volmatch("searchOpportunities", kwargs)
        else:
            raise Exception, "Requires either virtual or location"
        #searchOpportunities

    def search_orgs(self,**kwargs):
        return self._call_volmatch('searchOrganizations',kwargs)
        #searchOrganizations

    def _gen_nonce(self):
        # lifted from httplib2
        dig = sha1("%s:%s" % (time.ctime(), ["0123456789"[random.randrange(0, 9)] for i in range(20)])).hexdigest()
        return dig[:20]

    def _gen_time(self):
        return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime())

    def _gen_pass_digest(self,api_key,pass_time,pass_nonce):
        key = pass_nonce + pass_time + api_key
        return b64encode(sha256(key).digest())

    def _call_volmatch(self,call, payload):
        js = json.dumps(payload,separators=(',',':'))
        js = quote(js)
        url = 'http://www.volunteermatch.org/api/call?action=%s&query=%s' % (call,js)
        print "hitting url %s" % url
        try:
            (resp,content) = self.http.request(url,headers=self.headers)
            returned_data = json.loads(content)
            if resp.status != 200:
                raise
            return returned_data
        except Exception:
            print Exception
            return None

if __name__ == '__main__':
    username = ""
    password = ""
    vm = VolunteerMatch(username,password)
    print vm.search_volops(orgNames=['Red Cross'],virtual=True,pageNumber=1)
    print vm.get_key_status()
    print vm.hello()
    print vm.search_orgs(location='New York')
    print vm.search_orgs(
        location="94108",
        nbOfResults= 10,
        pageNumber= 1,
        fieldsToDisplay=[ "name", "location" ],
        names=[ "red cross" ]
        )
    print vm.headers

########NEW FILE########
__FILENAME__ = settings
from celery.schedules import crontab
import djcelery
from django.conf.global_settings import EMAIL_BACKEND
import os, sys, logging
import subprocess



###############################
#            MISC            #
##############################
ROOT_PATH = os.path.dirname(__file__)


def to_absolute_path(path):
    return os.path.realpath(os.path.join(ROOT_PATH, path))

DEBUG = True
TEMPLATE_DEBUG = DEBUG
DONATION_DEBUG = True #So we don't have to rely on django's debug.
BLOCK_FB_POSTS = True
#ROOT_PATH = os.path.dirname(__file__)

EXTRA_PATHS = [
     'lib',
]

for path in EXTRA_PATHS:
    path = to_absolute_path(path)
    if path not in sys.path:
        sys.path.append(path)

PROXY_SERVER = "PROXY_SERVER"
IGNORE_HTTPS = False



###############################
#       CAMPAIGN SETTINGS     #
##############################
MAX_PAYMENT_RETRIES = 1
PAYMENT_RETRY_SCHEDULE = [1, 3, 7]
JUMOEIN = ""


###############################
#       ADMIN SETTINGS       #
##############################

ADMINS = (
    ('Jumo Site Error', 'EMAIL@HERE'),
)
MANAGERS = ADMINS



###############################
#       STATIC SETTINGS       #
##############################

SERVE_STATIC_FILES = False
STATIC_URL = ''

NO_STATIC_HASH = False


###############################
#         DB SETTINGS        #
##############################


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'jumodjango',
        'USER': 'jumo',
        'PASSWORD': 'DB_PASSWORD',
        'HOST': '',
        'PORT': '',
    },
}

#Map the db name to path of matching schema file.
DATABASE_CREATE_SCHEMAS = {
    'default':to_absolute_path('data/schema/jumodjango.schema'),
}

###############################
#       SOLR  SETTINGS       #
##############################
SOLR_CONN = 'http://SOLRSERVER:8983/solr'

###############################
#       DISQUS  SETTINGS     #
##############################
DISQUS_API_VERSION = '3.0'
DISQUS_FORUM_NAME = 'jumoprod'
DISQUS_SECRET_KEY = 'SOME_DISQUS_SECRET_KEY' #jumo_prod_app
DISQUS_PUBLIC_KEY = 'SOME_DISQUS_PUBLIC_KEY' #jumo_prod_app
DISQUS_DEV_MODE = 0 # 1 for dev, 0 for prod and stage

###############################
#       EMAIL SETTINGS       #
##############################

DEFAULT_FROM_EMAIL = 'FROM@USER'
EMAIL_HOST = ''
EMAIL_PORT = 25
EMAIL_HOST_USER = 'EMAIL@HOSTUSER'
EMAIL_HOST_PASSWORD = 'SOME_EMAIL_HOST_PASSWORD'
EMAIL_USER_TLS = False
CELERY_EMAIL_BACKEND = EMAIL_BACKEND

EMAIL_REAL_PEOPLE = False

CRYPTO_SECRET = r'CRYPTO_SECRET_HERE'


###############################
#      CELERY SETTINGS       #
##############################

# AMQP setup for Celery
BROKER_HOST = ""
BROKER_PORT = 5672
BROKER_USER = "jumo"
BROKER_PASSWORD = "SOME_BROKER_PASSWORD"
BROKER_VHOST = "/"

CELERY_DEFAULT_QUEUE = "now"
CELERY_QUEUES = {
    "now": {
        "binding_key": "task.#",
    },
    "deferred": {
        "binding_key": "deferred.#",
    },
    "billing": {
        "binding_key": "billing.#",
    },
}

CELERY_DEFAULT_EXCHANGE = "tasks"
CELERY_DEFAULT_EXCHANGE_TYPE = "topic"
CELERY_DEFAULT_ROUTING_KEY = "task.default"

CELERY_ROUTES = {"mailer.reader_tasks.send_jumo_reader_email":
                    {"queue": "deferred",
                    "routing_key": "deferred.reader"
                    },
                 "donation.tasks.process_donation":
                    {"queue": "billing",
                     "routing_key": "billing.process_donation"}
                 }

CELERY_IMPORTS = ('mailer.notification_tasks',
                  'mailer.reader_tasks',
                  'donation.tasks',
                  'mailer.messager_tasks',)

###############################
#      DJANGO SETTINGS       #
##############################

CONSOLE_MIDDLEWARE_DEBUGGER = True
APPEND_SLASH = False

#SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
CACHE_BACKEND = 'memcached://127.0.0.1:11211?timeout=86400'

AUTHENTICATION_BACKENDS = (
    'etc.backend.JumoBackend',
)

TIME_ZONE = 'America/New_York'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1337
USE_I18N = True
USE_L10N = True

MEDIA_ROOT = to_absolute_path('static')
MEDIA_URL = '/static/'
ADMIN_MEDIA_PREFIX = '/static/media/admin/'

HTTP_HOST = 'www.ogbon.com'

SECRET_KEY = 'SOME_SECRET_KEY_HERE'

MIDDLEWARE_CLASSES = (
    'etc.middleware.SSLMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    #'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.messages.middleware.MessageMiddleware',
    'etc.middleware.DetectUserMiddleware',
    'etc.middleware.SourceTagCollectionMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'etc.middleware.AddExceptionMessageMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_DIRS = (
    to_absolute_path('templates'),
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.debug',
    'django.core.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'etc.context_processors.general',
)

INSTALLED_APPS = (
    'grappelli',
    'djcelery',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    #'django.contrib.sessions',
    'django.contrib.sites',
    #'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.humanize',
    'cust_admin',
    'users',
    'issue',
    'org',
    'data',
    'cust_admin',
    'etc',
    'api',
    'lib',
    'search',
    'utils',
    'mailer',
    'donation',
    'message',
    'sourcing',
    'popularity',
    'django_jenkins',
    'tastypie',
    'action',
    'entity_items',
    'commitment',
    'debug_toolbar',
    'discovery',
)


###############################
#        API SETTINGS        #
##############################
API_VERSION = 'v1'



###############################
#      TESTING SETTINGS       #
##############################
FIXTURE_DIRS = ("data/fixtures/",)
TEST_RUNNER = 'jumodjango.test.test_runner.JumoTestSuiteRunner'
JENKINS_TEST_RUNNER = 'jumodjango.test.test_runner.JumoTestSuiteRunner'
EXCLUDED_TEST_PACKAGES = ['django',]
PROJECT_APPS = (
    'users',
    'issue',
    'org',
    'mailer',
    'donation',
    'message',
    'sourcing',
    'popularity',
)


###############################
#      API KEY SETTINGS       #
##############################

MIXPANEL_TOKEN = 'SOME_MIXPANEL_TOKEN'

FACEBOOK_APP_ID = 'SOME_FACEBOOK_APP_ID'
FACEBOOK_API_KEY = 'SOME_FACEBOOK_API_KEY'
FACEBOOK_SECRET = 'SOME_FACEBOOK_SECRET'
FACEBOOK_ACCESS_TOKEN = 'SOME_FACEBOOK_ACCESS_TOKEN'

AWS_ACCESS_KEY = 'SOME_AWS_ACCESS_KEY'
AWS_SECRET_KEY = 'SOME_AWS_SECRET'
AWS_PHOTO_UPLOAD_BUCKET = "jumoimgs"

###############################################################
# DATAMINE SETTINGS - serve miner.views if IS_DATAMINE is True
###############################################################

IS_DATAMINE = False

###############################
# DATA SCIENCE TOOLKIT SETTINGS
###############################

# Use their AMI in production,
DSTK_API_BASE = "http://DSTK_HOST"

##############################
# DATAMINE SERVER
##############################

DATAMINE_BASE = "http://DATAMINE_HOST"

##############################
# LOGGER SETTINGS
##############################

LOG_DIR = '/cloud/logs/'


###############################
# DEBUG TOOLBAR SETTINGS
###############################
INTERNAL_IPS = ('127.0.0.1',)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
    'SHOW_TOOLBAR_CALLBACK': lambda x: False
}

DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    'debug_toolbar.panels.sql.SQLDebugPanel',
    'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
)

###############################
#      LOCAL SETTINGS       #
##############################

try:
    from local_settings import *
except ImportError:
    pass

if NO_STATIC_HASH:
    ASSET_HASH = 'abcdefg'
else:
    import git

    repo = git.Repo(to_absolute_path('.'), odbt=git.GitCmdObjectDB)
    ASSET_HASH = repo.head.commit.hexsha[0:7]
    del(repo)




if IS_DATAMINE:
    INSTALLED_APPS += ('miner',
                       'gunicorn')

    RELATED_SEARCH_MODEL_BASE_DIR = '/cloud/data'

LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO
LOG_FORMAT = '%(asctime)s %(levelname)s %(message)s'
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
log = logging.getLogger('jumo')

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from etc.func import crc32

# Create your models here.

class SourceTag(models.Model):
    id = models.AutoField(db_column='source_tag_id', primary_key=True)
    tag = models.CharField(db_column='tag', max_length=255, null=True)
    tag_crc32 = models.PositiveIntegerField(db_column='tag_crc32')
    is_active = models.BooleanField(db_column='is_active', default=False)

    class Meta:
        db_table='source_tags'


class SourceTaggedItem(models.Model):
    id = models.AutoField(db_column='source_tagged_item_id', primary_key=True)
    item_type = models.ForeignKey(ContentType, db_column='item_type', null=True)
    item_id = models.PositiveIntegerField(db_column='item_id', null=True)
    object = generic.GenericForeignKey('item_type', 'item_id')
    tag = models.ForeignKey(SourceTag, db_column='tag_id', related_name='tags')

    class Meta:
        db_table = 'source_tagged_items'

    @classmethod
    def create(cls, obj, tag):
        tag, created = SourceTag.objects.get_or_create(tag=tag,
                                                       tag_crc32=crc32(tag))
        tagged_item = SourceTaggedItem(object=obj,
                                       tag=tag)
        tagged_item.save()
        return tagged_item
########NEW FILE########
__FILENAME__ = tests


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = compress
#!/usr/bin/env python
import os
import optparse
import subprocess
import sys

here = os.path.dirname(__file__)

def main():
    usage = "usage: %prog [file1..fileN]"
    description = """With no file paths given this script will automatically
compress all jQuery-based files of the admin app. Requires the Google Closure
Compiler library and Java version 6 or later."""
    parser = optparse.OptionParser(usage, description=description)
    parser.add_option("-c", dest="compiler", default="~/bin/compiler.jar",
                      help="path to Closure Compiler jar file")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose")
    (options, args) = parser.parse_args()

    compiler = os.path.expanduser(options.compiler)
    if not os.path.exists(compiler):
        sys.exit("Google Closure compiler jar file %s not found. Please use the -c option to specify the path." % compiler)

    if not args:
        if options.verbose:
            sys.stdout.write("No filenames given; defaulting to admin scripts\n")
        args = [os.path.join(here, f) for f in [
            "actions.js", "collapse.js", "inlines.js", "prepopulate.js"]]

    for arg in args:
        if not arg.endswith(".js"):
            arg = arg + ".js"
        to_compress = os.path.expanduser(arg)
        if os.path.exists(to_compress):
            to_compress_min = "%s.min.js" % "".join(arg.rsplit(".js"))
            cmd = "java -jar %s --js %s --js_output_file %s" % (compiler, to_compress, to_compress_min)
            if options.verbose:
                sys.stdout.write("Running: %s\n" % cmd)
            subprocess.call(cmd.split())
        else:
            sys.stdout.write("File %s not found. Sure it exists?\n" % to_compress)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_runner
from __future__ import with_statement
from django.conf import settings
from django.test.simple import DjangoTestSuiteRunner, dependency_ordered
from django_jenkins.runner import CITestSuiteRunner
import sys

EXCLUDED_APPS = getattr(settings, "EXCLUDED_TEST_PACKAGES", [])

def create_test_db(connection, verbosity, autoclobber=False):
    test_db_name = connection.creation._create_test_db(verbosity, autoclobber=autoclobber)
    connection.close()
    connection.settings_dict["NAME"] = test_db_name
    can_rollback = connection.creation._rollback_works()
    connection.settings_dict["SUPPORTS_TRANSACTIONS"] = can_rollback
    return test_db_name



class JumoTestSuiteRunner(CITestSuiteRunner):
    def setup_databases(self, **kwargs):
        from django.db import connections, DEFAULT_DB_ALIAS

        # First pass -- work out which databases actually need to be created,
        # and which ones are test mirrors or duplicate entries in DATABASES
        mirrored_aliases = {}
        test_databases = {}
        dependencies = {}
        for alias in connections:
            connection = connections[alias]
            if connection.settings_dict['TEST_MIRROR']:
                # If the database is marked as a test mirror, save
                # the alias.
                mirrored_aliases[alias] = connection.settings_dict['TEST_MIRROR']
            else:
                # Store the (engine, name) pair. If we have two aliases
                # with the same pair, we only need to create the test database
                # once.
                test_databases.setdefault((
                        connection.settings_dict['HOST'],
                        connection.settings_dict['PORT'],
                        connection.settings_dict['ENGINE'],
                        connection.settings_dict['NAME'],
                    ), []).append(alias)

                if 'TEST_DEPENDENCIES' in connection.settings_dict:
                    dependencies[alias] = connection.settings_dict['TEST_DEPENDENCIES']
                else:
                    if alias != 'default':
                        dependencies[alias] = connection.settings_dict.get('TEST_DEPENDENCIES', ['default'])

        # Second pass -- actually create the databases.
        old_names = []
        mirrors = []
        db_schemas = settings.DATABASE_CREATE_SCHEMAS
        for (host, port, engine, db_name), aliases in dependency_ordered(test_databases.items(), dependencies):
            # Actually create the database for the first connection
            connection = connections[aliases[0]]
            old_names.append((connection, db_name, True))
            #test_db_name = connection.creation._create_test_db(self.verbosity, autoclobber=not self.interactive)
            test_db_name = create_test_db(connection, self.verbosity, not self.interactive)

            #Create Tables Via Schema File
            try:

                schema_file = db_schemas[aliases[0]]
                schema_string = ""
                with open(schema_file) as fh:
                    schema_string = fh.read()

                print "Building Tables For %s from %s" % (test_db_name, schema_file)
                cursor = connection.cursor()
                connection.autocommit = True
                cursor.execute(schema_string)
                cursor.close()
            except Exception, e:
                sys.stderr.write("Got an loading the schema file database: %s\n" % e)
                print "Tests Canceled"
                sys.exit(1)

            for alias in aliases[1:]:
                connection = connections[alias]
                if db_name:
                    old_names.append((connection, db_name, False))
                    connection.settings_dict['NAME'] = test_db_name
                else:
                    # If settings_dict['NAME'] isn't defined, we have a backend where
                    # the name isn't important -- e.g., SQLite, which uses :memory:.
                    # Force create the database instead of assuming it's a duplicate.
                    old_names.append((connection, db_name, True))
                    connection.creation.create_test_db(self.verbosity, autoclobber=not self.interactive)

        from django.core.management import call_command
        from django.contrib.contenttypes.management import update_all_contenttypes
        update_all_contenttypes()

        call_command('loaddata', 'initial_data', verbosity=self.verbosity, database=DEFAULT_DB_ALIAS)

        for alias, mirror_alias in mirrored_aliases.items():
            mirrors.append((alias, connections[alias].settings_dict['NAME']))
            connections[alias].settings_dict['NAME'] = connections[mirror_alias].settings_dict['NAME']

        return old_names, mirrors

    def build_suite(self, *args, **kwargs):
        suite = super(JumoTestSuiteRunner, self).build_suite(*args, **kwargs)
        if not args[0]:
            tests = []
            for case in suite:
                pkg = case.__class__.__module__.split('.')[0]
                if pkg not in EXCLUDED_APPS:
                    tests.append(case)
            suite._tests = tests
        return suite

########NEW FILE########
__FILENAME__ = urls
from api.api_v1 import api_urls
from django.conf.urls.defaults import *
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
)

''' RANDOM URLs '''

urlpatterns += patterns('etc.views',
    url(r'^about/?$', 'about', name = 'about'),
    url(r'^help/?$', 'help', name = 'help'),
    url(r'^jobs/?$', 'jobs', name = 'jobs'),
    url(r'^team/?$', 'team', name = 'team'),
    url(r'^blog/?$', 'blog', name = 'blog'),
    url(r'^contact/?$', 'contact', name = 'contact'),
    url(r'^privacy/?$', 'privacy', name = 'privacy'),
    url(r'^terms/?$', 'terms', name = 'terms'),
    url(r'^/?$', 'index', name = 'index'),
    url(r'^error/?$', 'throw_error', name = 'throw_error'),
    url(r'^health_check/?$', 'health_check', name = 'health_check'),
)

''' END OF RANDOM URLs '''



''' API URLS '''

urlpatterns += patterns('',
    (r'^api/', include(api_urls())),
)

''' END API URLS '''


''' USER URLs '''

urlpatterns += patterns('users.views',
    url(r'^login/?$', 'login_permalink', name = 'login_permalink'),
    url(r'^logout/?$', 'logout_permalink', name = 'logout_permalink'),
    url(r'^setup/?$', 'setup', name = 'setup'),
    url(r'^discover/?$', 'discover', name = 'discover'),
    url(r'^user/(?P<mongo_id>[a-zA-Z0-9\-_].*)/?$', 'old_user_permalink', name = 'old_user_permalink'),
    url(r'^forgot_password/?$', 'forgot_password', name = 'forgot_password'),
    url(r'^reset_password/(?P<reset_id>[a-fA-F0-9].*)/?$', 'reset_password', name = 'reset_password'),
    url(r'^upload_photo/?$', 'upload_photo', name = 'upload_photo'),
    url(r'^settings/?$', 'settings', name='settings'),
    url(r'^settings/notifications/?$', 'notifications', name='settings_notifications'),
    url(r'^settings/connect/?$', 'connect', name='settings_connect'),
    url(r'^settings/developer/?$', 'developer', name='settings_developer'),
    url(r'^users/(?P<user_id>\d*)/follow/?$', 'follow', name='follow_user'),
    url(r'^users/(?P<user_id>\d*)/unfollow/?$', 'unfollow', name='unfollow_user'),
    url(r'^users/(?P<user_id>\d*)/followers/?$', 'follower_list', name='user_followers'),
    url(r'^users/(?P<user_id>\d*)/followings/?$', 'following_list', name='user_followings'),
    url(r'^remove/?$', 'remove_user', name='remove_user')
)

urlpatterns += patterns('users.ajax.views',
    url(r'^json/v1/user/fbid_check/?$', 'check_fbid', name = 'check_fbid'),
    url(r'^json/v1/user/fb_login/?$', 'fb_login', name = 'fb_login'),
    url(r'^json/v1/user/fbot_update/?$', 'fbot_update', name = 'fbot_update'),
    url(r'^json/v1/user/update/?$', 'update_user', name = 'update_user'),
    url(r'^json/v1/user/remove/?$', 'remove_user', name = 'remove_user'),
    url(r'^json/v1/user/reset_password/?$', 'reset_password', name = 'reset_password'),
    url(r'^json/v1/user/forgot_password/?$', 'forgot_password', name = 'forgot_password'),
    url(r'^json/v1/user/action/follow/?$', 'follow', name = 'follow'),
)

''' END OF USER URLs '''


''' ISSUE URLs '''
urlpatterns += patterns('issue.views',
    url(r'^issue/(?P<mongo_id>[a-zA-Z0-9\-_].*)/?$', 'old_issue_permalink', name = 'old_issue_permalink'),
    url(r'^issuename/(?P<issuename>[a-zA-Z0-9\-_\ ].*)/?$', 'old_issuename_permalink', name = 'old_issuename_permalink'),
    url(r'^users/(?P<user_id>\d*)/issues/?$', 'followed_issue_list', name='followed_issue_list')
)

''' ISSUE URLs '''


''' ORG URLs '''
urlpatterns += patterns('org.views',
    url(r'^org/categories.js$', 'org_categories', name = 'org_categories'),
    url(r'^org/claim/(?P<org_id>[0-9a-zA-Z\-_].*)/confirm/?$', 'claim_org_confirm', name = 'claim_org_confirm'),
    url(r'^org/claim/(?P<org_id>[0-9a-zA-Z\-_].*)/?$', 'claim_org', name = 'claim_org'),
    url(r'^org/create/?$', 'create_org', name = 'create_org'),
    url(r'^org/(?P<org_id>\d.*)/details/?$', 'details', name='details_org'),
    url(r'^org/(?P<org_id>[0-9a-zA-Z\-_].*)/manage/?$', 'manage_org', {'tab': 'about'}, name='manage_org'),
    url(r'^org/(?P<org_id>[0-9a-zA-Z\-_].*)/manage/connect/?$', 'manage_org', {'tab': 'connect'}, name='manage_org_connect'),
    url(r'^org/(?P<org_id>[0-9a-zA-Z\-_].*)/manage/more/?$', 'manage_org', {'tab': 'more'}, name='manage_org_more'),
    url(r'^org/(?P<mongo_id>[a-zA-Z0-9\-_].*)/?$', 'old_org_permalink', name = 'old_org_permalink'),
    url(r'^orgname/(?P<orgname>[a-zA-Z0-9\-_\ ].*)/?$', 'old_orgname_permalink', name = 'old_orgname_permalink'),
    url(r'^users/(?P<user_id>\d*)/orgs/?$', 'followed_org_list', name='followed_org_list')
)

urlpatterns += patterns('org.ajax.views',
    url(r'^json/v1/org/fetch_centroid/?$', 'fetch_org_by_centroid', name = 'fetch_org_by_centroid'),
    url(r'^json/v1/org/update/?$', 'update_org', name = 'update_org'),
    url(r'^json/v1/org/remove/?$', 'remove_org', name = 'remove_org'),
    url(r'^json/v1/org/flag/?$', 'flag_org', name = 'flag_org'),
    url(r'^json/v1/org/create/?$', 'org_create', name = 'org_create'),
    url(r'^json/v1/org/normalize_facebook_id/?$', 'normalize_facebook_id', name = 'normalize_facebook_id'),

)
''' END OF ORG URLs '''


''' COMMITMENT URLS '''
urlpatterns += patterns('commitment.views',
    url(r'^commitments/create/?$', 'create', name='create_commitment'),
    url(r'^commitments/(?P<commitment_id>\d*)/delete/?$', 'delete', name='delete_commitment'),
    url(r'^orgs/(?P<entity_id>\d*)/commitments/?$', 'list', {'model_name': 'org.Org'}, name='org_commitments'),
    url(r'^issues/(?P<entity_id>\d*)/commitments/?$', 'list', {'model_name': 'issue.Issue'}, name='issue_commitments'),
)

''' ACTION URLS '''
urlpatterns += patterns('action.views',
    url(r'^orgs/(?P<entity_id>\d*)/actions/?$', 'action_list', {'model_name': 'org.Org'}, name='org_action_list'),
    url(r'^issues/(?P<entity_id>\d*)/actions/?$', 'action_list', {'model_name': 'issue.Issue'}, name='issue_action_list'),
)

''' SEARCH URLS '''

urlpatterns += patterns('search.views',
                        url(r'^json/v1/search/onebox/?$', 'autocomplete', name = 'autocomplete'),
                        url(r'^search/?$', 'search_page', name='search_page'),
                        url(r'^json/v1/search/?$', 'ajax_search', name='ajax_search'),
                        url(r'^json/v1/autocomplete/?$', 'ajax_term_complete', name='ajax_term_complete')
                        )

''' MAILER URLS '''

urlpatterns += patterns('mailer.views',
    url(r'^unsubscribe/$', 'unsubscribe', name='unsubscribe'),
    url(r'^email/text/(?P<username>[a-zA-Z0-9\-_\ ].*)/?$', 'jumo_reader', name = 'jumo_reader'),
    url(r'^email/(?P<username>[a-zA-Z0-9\-_\ ].*)/?$', 'jumo_reader', name = 'jumo_reader'),
    #url(r'^notification/(?P<username>[a-zA-Z0-9\-_\ ].*)/?$', 'notification_email', name = 'notification_email'),
)

''' END MAILER URLS '''


''' ADMIN URLS '''
urlpatterns += patterns('',
    (r'^admin/org/report/$', 'org.admin_views.report'),
    (r'^grappelli/', include('grappelli.urls')),
    (r'^admin/', include(admin.site.urls)),
)

if settings.IS_DATAMINE:
    urlpatterns += patterns('miner.views',
                    url(r'^related_searches/?$', 'related_searches', name='related_searches')
                    )

#if settings.DEBUG:
if True:
    urlpatterns += patterns('django.views.static',
    (r'^static/(?P<path>.*)$',
        'serve', {
        'document_root': settings.MEDIA_ROOT,
        'show_indexes': True }),)


handler500 = 'etc.views.error_500'
handler404 = 'etc.views.error_404'

'''
#########################################################################################
### HEY         #########################################################################
################################################## SEE ALL THEM POUND SIGNS? ############
#########################################################################################
############### THAT MEANS THIS IS AN IMPORTANT MSG #####################################
#########################################################################################
################################# SO PAY ATTENTION OK? ##################################
#########################################################################################
####### EVERYTHING WILL BREAK IF THIS ISN'T THE LAST LINE OF CODE IN THIS FILE. #
#########################################################################################
################################## WE COOL? #############################################
#########################################################################################
'''

urlpatterns += patterns('etc.views',
    url(r'^([a-zA-Z0-9\-_].*)/?$', 'clean_url', name = 'entity_url'),
)

########NEW FILE########
__FILENAME__ = admin
from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group, User as DjangoUser
from django.contrib.sites.models import Site
from djcelery.models import TaskState, WorkerState, IntervalSchedule, CrontabSchedule, PeriodicTask
from etc import cache
from issue.models import UserToIssueFollow
from org.models import UserToOrgFollow
from users.models import User, UserToUserFollow, Location
from cust_admin.views.main import ExtChangeList


######## INLINES ########

class UserFollowingInline(admin.StackedInline):
    model = UserToUserFollow
    fk_name = "follower"
    extra = 0
    raw_id_fields = ('followed',)
    related_field_lookups = {
        'fk': ['followed']
    }
    verbose_name = "Followed Users"
    verbose_name_plural = "Followed Users"

class OrgFollowingInline(admin.StackedInline):
    model = UserToOrgFollow
    fk_name = "user"
    extra = 0
    raw_id_fields = ('org',)
    related_field_lookups = {
        'fk': ['org']
    }
    verbose_name = "Followed Org"
    verbose_name_plural = "Followed Orgs"

class IssueFollowingInline(admin.StackedInline):
    model = UserToIssueFollow
    fk_name = "user"
    extra = 0
    raw_id_fields = ('issue',)
    related_field_lookups = {
        'fk': ['issue']
    }
    verbose_name = "Followed Issue"
    verbose_name_plural = "Followed Issues"

######## MODEL FORM AND ADMIN ########

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        widgets = {
            'facebook_id' : forms.TextInput(attrs={'class':'vTextField'}),
        }

class UserAdmin(admin.ModelAdmin):
    form = UserForm

    #List Page Values
    search_fields = ['username','email', 'first_name', 'last_name']
    search_fields_verbose = ['Username', 'Email', 'First Name', 'Last Name']
    list_display = ('get_name', 'username', 'last_login','is_active', 'likely_org', 'org_probability', 'admin_classification')

    list_editable = ['admin_classification']
    list_filter = ('is_active', 'likely_org', 'admin_classification')
    ordering = ('username',)

    change_list_template = "cust_admin/change_list.html"

    raw_id_fields = ('location',)
    related_field_lookups = {
        'fk': ['location']
    }

    change_list_template = "cust_admin/change_list.html"

    def get_changelist(self, request, **kwargs):
        return ExtChangeList


    #Change Page Values
    fieldsets = (
      ('User Profile', {
        'fields': (
            ('username', 'is_active', 'is_superuser','is_staff'),
            ('first_name', 'last_name',),
            ('email',),
            ('date_joined', 'last_login',),
            'bio',
            'picture',
            ('url','blog_url',),
            'gender',
            'birth_year',
            'location',
        )}),
      ('Settings', {
        'fields':(('enable_jumo_updates',
                  'enable_followed_notification',
                  'email_stream_frequency',
                  'post_to_fb',),),
      }),
      ('Social Settings', {
        'fields':(
                    ('facebook_id','flickr_id','twitter_id',),
                    ('vimeo_id','youtube_id',),
                 )
      }),
      ("Extra Nonsense", {
        'classes': ('collapse closed',),
        'fields':('mongo_id','password','fb_access_token')
      }),
    )

    readonly_fields = ['mongo_id','fb_access_token','date_joined','last_login']
    inlines = [UserFollowingInline,OrgFollowingInline,IssueFollowingInline]

    def save_model(self, request, obj, form, change):
        cache.bust(obj, update=False)
        super(self.__class__, self).save_model(request, obj, form, change)


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location

class LocationAdmin(admin.ModelAdmin):
    form = LocationForm

    #List Page Values
    search_fields = ['locality', 'region', 'country_name', 'postal_code', 'raw_geodata', 'classification']
    search_fields_verbose = ['City', 'State', 'Country', 'ZIP code', 'Geodata', 'Classification']
    list_display = ('__unicode__', 'locality', 'region', 'country_name','postal_code', 'classification')

    list_editable = ['classification']

    def get_changelist(self, request, **kwargs):
        return ExtChangeList
    change_list_template = "cust_admin/change_list.html"


    #Change Page Values
    fieldsets = (
      ('Geography', {
        'fields': (
            ('__unicode__', 'locality', 'region', 'country_name','postal_code', 'classification'),
            )}
        ),
    )

    readonly_fields = ['__unicode__', 'locality', 'region', 'country_name','postal_code']

admin.site.unregister(Group)
admin.site.unregister(Site)
admin.site.unregister(DjangoUser)
admin.site.register(User, UserAdmin)
admin.site.register(Location, LocationAdmin)


# Unregister djcelery while we're at it

admin.site.unregister(TaskState)
admin.site.unregister(WorkerState)

admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(PeriodicTask)

########NEW FILE########
__FILENAME__ = views
from datetime import datetime, timedelta
from django.http import HttpResponseBadRequest
from etc import cache
from etc.auth import login, logout, set_auth_cookies, unset_auth_cookies
from etc.decorators import PostOnly, AccountRequired
from etc.entities import create_handle
from etc.view_helpers import json_response, json_error
from etc.user import hash_password
from issue.models import Issue, UserToIssueFollow
import json
from message.models import Subscription, NOTIFICATIONS_PUB
from mailer.notification_tasks import send_notification, EmailTypes
from org.models import Org, UserToOrgFollow
from users.models import User, Location, UserToUserFollow, PasswordResetRequest
from uuid import uuid4


@AccountRequired
@PostOnly
def fbot_update(request):
    if 'ot' not in request.POST:
        return HttpResponseBadRequest()
    request.user.fb_access_token = request.POST['ot']
    request.user.save()
    cache.bust_on_handle(request.user, request.user.username)
    return json_response({})

@PostOnly
def fb_login(request):
    if 'id' not in request.POST or 'ot' not in request.POST:
        return HttpResponseBadRequest()
    user = User.objects.get(facebook_id = request.POST['id'], is_active=True)
    if user.fb_access_token != request.POST['ot']:
        user.fb_access_token = request.POST['ot']
        user.save()
    cache.put_on_handle(user, user.username)
    #perform for all that login magic that happens under the covers
    login(request, user)
    response = {'user_id':user.id, 'fb_access_token':user.fb_access_token}
    return set_auth_cookies(json_response({'result' : response}), user)

@PostOnly
def check_fbid(request):
    if 'fbid' not in request.POST:
        return HttpResponseBadRequest()
    fbid = request.POST['fbid']
    if not fbid:
        return json_response({'exists' : 0})
    try:
        u = User.objects.get(facebook_id = fbid, is_active=True)
        return json_response({'exists' : 1})
    except:
        pass
    return json_response({'exists' : 0})

@AccountRequired
@PostOnly
def update_user(request):
    if 'user' not in request.POST:
        return HttpResponseBadRequest()
    user = json.loads(request.POST['user'])

    if 'location' in user and user['location']:
        loc = user['location']
        raw_geodata = json.dumps(loc["raw_geodata"]) if isinstance(loc.get("raw_geodata"), dict) else loc.get("raw_geodata")

        #Until we fix duplicate locations we have to do the following...lame.
        _locs = Location.objects.filter(raw_geodata = raw_geodata,
            longitude = loc.get('longitude', None),
            latitude = loc.get('latitude', None),
            address = loc.get('address', ' '),
            region = loc.get('region', ' '),
            locality = loc.get('locality', ' '),
            postal_code = loc.get('postal_code', ' '),
            country_name = loc.get('country_name', ' '))

        if len(_locs) > 0:
            _loc = _locs[0]
        else:
            _loc = Location(raw_geodata = raw_geodata,
                longitude = loc.get('longitude', None),
                latitude = loc.get('latitude', None),
                address = loc.get('address', ' '),
                region = loc.get('region', ' '),
                locality = loc.get('locality', ' '),
                postal_code = loc.get('postal_code', ' '),
                country_name = loc.get('country_name', ' '),)
            _loc.save()
        request.user.location = _loc
    else:
        request.user.location = None

    str_fields = [
                    'first_name', 'last_name', 'email', 'gender', 'bio',
                    'url', 'twitter_id', 'flickr_id', 'youtube_id', 'vimeo_id', 'blog_url',
                 ]

    settings_fields = [
                    'enable_jumo_updates', 'email_stream_frequency', 'post_to_fb',
                  ]

    int_fields = [
                    'birth_year',
                 ]

    if 'enable_followed_notification' in user:
        try:
            sub = request.user.subscriptions.get(id=NOTIFICATIONS_PUB)
        except Subscription.DoesNotExist:
            sub = Subscription.get_or_create(user=request.user, pub_id=NOTIFICATIONS_PUB)

        if sub.subscribed <> user['enable_follow_notification']:
            sub.subscribed = user['enable_follow_notification']
            sub.save()

    for f in str_fields:
        if f in user and user[f] != getattr(request.user, f):
            setattr(request.user, f, user[f])

    for f in settings_fields:
        settings = user['settings']
        if f in settings:
            setattr(request.user, f, settings[f])

    for f in int_fields:
        if f in user and user[f] != getattr(request.user, f):
            if user[f] == '':
                user[f] = None
            setattr(request.user, f, user[f])

    if 'password' in user and user['password'] != '':
        request.user.password = hash_password(user['password'])
    if 'username' in user and user['username'] != request.user.username:
        _username = request.user.username
        request.user.username = create_handle(user['username'])
        cache.bust_on_handle(request.user, _username, False)

    request.user.save()
    cache.bust_on_handle(request.user, request.user.username)
    return json_response({'result' : request.user.username})

@AccountRequired
@PostOnly
def follow(request):
    action = request.POST['action']
    item_type = request.POST['item_type']

    if 'items[]' in request.POST:
        try:
            items = request.POST.getlist('items[]')
        except:
            items = [request.POST['items[]']]
    elif 'items' in request.POST:
        try:
            items = list(json.loads(request.POST['items']))
        except:
            items = [request.POST['items']]

    for item in items:
        ent = None
        item_id_type = 'id'

        if len(item) == 24:
            item_id_type = 'mongo_id'

        if item_type == 'org':
            try:
                if item_id_type == 'id':
                    ent = Org.objects.get(id = item)
                else:
                    ent = Org.objects.get(mongo_id = item)
                f, created = UserToOrgFollow.objects.get_or_create(user = request.user, org = ent)
                if action == 'follow':
                    f.following = True
                else:
                    f.following = False
                    f.stopped_following = datetime.now()
                f.save()
                request.user.refresh_orgs_following()

                ent.refresh_users_following()
                #if created:
                #    FeedStream.post_new_follow(request.user, ent)
            except Exception, inst:
                log(inst)

        elif item_type == 'issue':
            try:
                if item_id_type == 'id':
                    ent = Issue.objects.get(id = item)
                else:
                    ent = Issue.objects.get(mongo_id = item)
                f, created = UserToIssueFollow.objects.get_or_create(user = request.user, issue = ent)
                if action == 'follow':
                    f.following = True
                else:
                    f.following = False
                    f.stopped_following = datetime.now()
                f.save()
                request.user.refresh_issues_following()
                ent.refresh_users_following()
                #if created:
                #    FeedStream.post_new_follow(request.user, ent)

            except Exception, inst:
                log(inst)

        else:
            try:
                if item_id_type == 'id':
                    ent = User.objects.get(id = item)
                else:
                    ent = User.objects.get(mongo_id = item)
                f, created = UserToUserFollow.objects.get_or_create(follower = request.user, followed = ent)
                if action == 'follow':
                    f.is_following = True
                else:
                    f.is_following = False
                    f.stopped_following = datetime.now()
                f.save()
                request.user.refresh_users_following()
                ent.refresh_followers()
                if created:
                    #FeedStream.post_new_follow(request.user, ent)
                    send_notification(type=EmailTypes.FOLLOW,
                                      user=ent,
                                      entity=request.user)
            except Exception, inst:
                log(inst)

        if not ent:
            continue
        else:
            cache.bust(ent)

    return json_response({'result' : 1})

@AccountRequired
@PostOnly
def remove_user(request):
    request.user.is_active = False
    request.user.save()
    cache.bust_on_handle(request.user, request.user.username)
    logout(request)
    return unset_auth_cookies(json_response({'result':1}))

@PostOnly
def forgot_password(request):
    email = request.POST['email'].strip()
    try:
        u = User.objects.get(email = email, is_active=True)
    except:
        return json_error(INVALID_EMAIL_ERROR, 'No user at that email address.')
    pr = PasswordResetRequest()
    pr.user = u
    pr.uid = str(uuid4().hex)
    pr.save()
    p = PasswordResetRequest.objects.all()
    send_notification(type=EmailTypes.RESET_PASSWORD,
                                  user=u,
                                  entity=u,
                                  password_reset_id=pr.uid)
    return json_response({'response' : 1})

#NEED TO WALK THROUGH OLD POINTLESS VIEWS WITH BRENNAN
@PostOnly
def request_password(request):
    pass

@PostOnly
def reset_password(request):
    pass

########NEW FILE########
__FILENAME__ = forms
import datetime
from django import forms
from django.core.exceptions import ValidationError
from users.models import User, GENDER_CHOICES

REQUIRE_FB_CONNECT = False

class CreateAccountForm(forms.Form):
    first_name = forms.CharField(max_length=50, required=True, label="First Name")
    last_name = forms.CharField(max_length=50, required=True, label="Last Name")
    email = forms.EmailField(required=True, label="Email")
    password = forms.CharField(required=True, min_length=7, max_length=50, widget=forms.PasswordInput, label="Password")
    location_input = forms.CharField(required=False, label="Location")
    location_data = forms.CharField(required=False)
    redirect_to = forms.CharField(required=False, widget=forms.HiddenInput)

    birth_year = forms.IntegerField(
        required=True,
        label="Year of Birth",
        max_value= datetime.date.today().year,
        min_value= datetime.date.today().year - 120
        )

    gender = forms.ChoiceField(
        required=True,
        label="Gender",
        choices=(('male', 'Male'),('female', 'Female'),),
        widget=forms.RadioSelect
        )

    fb_access_token = forms.CharField(required=REQUIRE_FB_CONNECT)
    fbid = forms.IntegerField(required=REQUIRE_FB_CONNECT)
    bio = forms.CharField(required=False)
    friends = forms.CharField(required=False)
    # if unchecked it returns false and fails the 'is_required' validation
    post_to_facebook = forms.BooleanField(initial=True, required=False )

    def clean(self):
        cleaned_data = self.cleaned_data
        email = cleaned_data.get("email")

        if email:
            try:
                user = User.objects.get(email = email)
                if user:
                    # email is no longer valid - remove it from the cleaned data.
                    self._errors["email"] = self.error_class(['An account with this email address already exists'])
                    del cleaned_data["email"]
            except:
                pass

        if REQUIRE_FB_CONNECT and (not cleaned_data.get('fbid', None) or not cleaned_data.get('fb_access_token', None)):
            self._errors["fbid"] = self.error_class(['Facebook error. Please re-authenticate with Facebook.'])

        if self.data['password'] and len(self.data['password']) < 6:
            self._errors['password'] = self.error_class(['Your password must be at least 6 characters.'])

        if self.data['birth_year']:
            birth_year = 0
            try:
                birth_year = int(self.data['birth_year'])
            except:
                self._errors['birth_year'] = self.error_class(['Please enter a valid year.'])

            max_birth_year = datetime.date.today().year
            min_birth_year = datetime.date.today().year - 120
            if birth_year > max_birth_year:
                self._errors['birth_year'] = self.error_class(['Please enter a year before %s.' % max_birth_year])
            elif birth_year < min_birth_year:
                self._errors['birth_year'] = self.error_class(['Please enter a year after %s.' % min_birth_year])

        return cleaned_data


class LoginForm(forms.Form):
    username = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': "Username"}))
    password = forms.CharField(required=True, widget=forms.PasswordInput(attrs={'placeholder': "Password"}))
    redirect_to = forms.CharField(required=False)
    post_auth_action = forms.CharField(required=False)

class UserSettingsForm(forms.ModelForm):
    email = forms.EmailField(required=True, label='E-mail')
    gender = forms.ChoiceField(choices=GENDER_CHOICES, widget=forms.RadioSelect)
    password = forms.CharField(required=False, min_length=7, max_length=50, label="Change Password",
                               widget=forms.PasswordInput(render_value=False), )
    username = forms.CharField(help_text='http://jumo.com/<b>handle</b>', label='Handle')
    profile_pic = forms.ImageField(required=False, label="Profile Picture")
    location_input = forms.CharField(required=False, label="Location")
    location_data = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = User
        fields = ['profile_pic', 'first_name', 'last_name', 'username', 'email', 'password', 'birth_year', 'location_input',
                  'gender', 'bio']

    def clean_email(self):
        try:
            u = User.objects.get(email=self.cleaned_data['email'])
        except User.DoesNotExist:
            return self.cleaned_data['email']

        if not self.instance or u.id != self.instance.id:
            raise ValidationError("An account with this email address already exists.")
        return self.cleaned_data['email']

class PhotoUploadForm(forms.ModelForm):
    profile_pic = forms.ImageField(required=False, label="Profile Picture")

class UserNotificationsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['enable_followed_notification', 'post_to_fb', 'enable_jumo_updates',]

class UserConnectForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['url', 'twitter_id', 'flickr_id', 'youtube_id', 'vimeo_id', 'blog_url']
        widgets = {
            'url': forms.TextInput(attrs={'placeholder':'http://www.joesmith.com'}),
            'twitter_id': forms.TextInput(attrs={'placeholder':'joesmith'}),
            'flickr_id': forms.TextInput(attrs={'placeholder':'joesmith'}),
            'youtube_id': forms.TextInput(attrs={'placeholder':'joesmith'}),
            'vimeo_id': forms.TextInput(attrs={'placeholder':'joesmith'}),
            'blog_url': forms.TextInput(attrs={'placeholder':'http://blog.joesmith.com'}),
        }

########NEW FILE########
__FILENAME__ = models
import datetime
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User as DjangoUser
from django.forms.models import model_to_dict
from etc import cache
from lib.image_upload import upload_user_image
from entity_items.models.location import Location
import Image
import json
from tastypie.models import ApiKey


GENDER_CHOICES = (
    ('male', 'Male'),
    ('female', 'Female'),
)

EMAIL_FREQ_CHOICES = (
    (86400,"once a day",),
    (604800,"once a week",),
    (1209600,"once every 2 weeks"),
    (0,"never"),
)

AGE_GROUPS = (
    (0, 11),
    (12, 17),
    (18, 24),
    (25, 35),
    (36, 45),
    (46, 65),
    (66, 110),
)

USER_OR_ORG = (
    ('org', 'Org'),
    ('user', 'User')
)

# User model must have corresponding field named: <size_name>_img_url
#
# Use 0 to say there's no limit on dimension. If setting limits on
# dimensions, image resizing currently only works for a square
# or when a max-width is set.
# (aka the dimensions should either be (x,x) or (x,0))

USER_IMAGE_SIZES = {
    'orig': (0,0),
    'thumb': (50,50),
    'large': (161,0),
}

class User(DjangoUser):
    type = 'user'
    # acct info
    fb_access_token = models.CharField(max_length = 128, blank=True)

    #Because overriding the django user email field was insane
    long_email = models.EmailField(max_length=200, unique=True, verbose_name="email")

    # settings stuff
    enable_jumo_updates = models.BooleanField(default = True, verbose_name="Feature Notifications",
                                              help_text="Email me with new features and functionality")
    enable_followed_notification = models.BooleanField(default = True, verbose_name="Notifications",
                                                       help_text="Email me when someone starts following me on Jumo")
    email_stream_frequency = models.PositiveIntegerField(default = 604800, choices=EMAIL_FREQ_CHOICES, verbose_name="Jumo Reader",)
    post_to_fb = models.BooleanField(default = True, verbose_name="Facebook Posting",
                                     help_text="Allow Jumo to post updates to my Facebook account")

    # profiley stuff
    mongo_id = models.CharField(max_length=24, blank=True, db_index = True) #For all those old urls out in the wild right now.
    bio = models.TextField(blank = True)
    picture = models.CharField(max_length = 32, blank=True)
    url = models.URLField(verify_exists = False, blank=True, verbose_name="Website URL")
    blog_url = models.URLField(verify_exists = False, blank=True, verbose_name="Blog URL")
    gender = models.CharField(max_length="6", blank = True, choices = GENDER_CHOICES)
    birth_year = models.PositiveSmallIntegerField(blank = True, null = True, verbose_name='Year of Birth')
    location = models.ForeignKey(Location, blank=True, null=True)
    thumb_img_url = models.URLField(verify_exists=False, blank=True)
    large_img_url = models.URLField(verify_exists=False, blank=True)
    orig_img_url = models.URLField(verify_exists=False, blank=True)

    #Internal stuff
    next_email_time = models.DateField(blank = True, null = True, db_index = True)

    #social web crap
    facebook_id = models.BigIntegerField(blank = True, null=True, db_index = True)
    twitter_id = models.CharField(blank = True, max_length = 32, verbose_name="Twitter Username")
    flickr_id = models.CharField(blank = True, max_length = 32, verbose_name="Flickr Username")
    vimeo_id = models.CharField(blank = True, max_length = 32, verbose_name="Vimeo Username")
    youtube_id = models.CharField(blank = True, max_length = 32, verbose_name="Youtube Username")

    # Org profile detection
    likely_org = models.BooleanField(default=False, verbose_name = 'Is Likely Org')
    org_probability = models.FloatField(default = 0.0, verbose_name = "Probability (is Org)")
    admin_classification = models.CharField(max_length=30, blank=True, null=True, choices=USER_OR_ORG, verbose_name = "Admin Override (User or Org)")

    # relationships
    followers = models.ManyToManyField('self', through = 'UserToUserFollow', symmetrical = False, related_name = 'followings')

    # static vars for saving ourselves db lookups...
    _location = None

    # For distinguishing in templates between Donors and Jumo users
    is_jumo_user = True

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __unicode__(self):
        return unicode(self.username)

    def save(self):
        super(User, self).save()
        cache.bust(self)

    @models.permalink
    def get_absolute_url(self):
        return ('entity_url', [self.username])

    @classmethod
    def get(cls, id, force_db=False):
        if force_db:
            org = User.objects.get(id=id)
            cache.bust(org)
            return org
        return cache.get(cls, id)

    @classmethod
    def multiget(cls, ids, force_db=False):
        if force_db:
            return User.objects.filter(id__in=ids)
        return cache.get(cls, ids)

    @property
    def get_type(self):
        return self.type

    @property
    def get_url(self):
        return '/%s' % self.username

    @property
    def get_name(self):
        return '%s %s' % (self.first_name, self.last_name)

    def get_active_followers(self):
        return self.followers.filter(following_user__is_following=True)

    def get_active_followings(self):
        return self.followings.filter(followed_user__is_following=True)

    @property
    @cache.collection_cache('users.user', '_all_followers')
    def get_all_followers(self):
        return self.get_active_followers()

    @property
    def get_all_follower_ids(self):
        return self.followed_user.filter(is_following = True).values_list('follower_id', flat = True)

    @property
    def get_num_followers(self):
        return self.get_active_followers().count()

    @property
    @cache.collection_cache('users.user', '_sample_followers')
    def get_sample_followers(self):
        return self.get_active_followers()[:16]


    @property
    @cache.collection_cache('users.user', '_all_users_following')
    def get_all_users_following(self):
        return self.get_active_followings()

    @property
    def get_users_following_ids(self):
        return self.following_user.filter(is_following = True).values_list('followed_id', flat = True)

    @property
    def get_num_users_following(self):
        return self.get_active_followings().count()

    @property
    #@cache.collection_cache('users.user', '_sample_users_following')
    def get_sample_users_following(self):
        return self.get_active_followings()[:16]


    def get_num_org_commitments(self):
        return self.commitments.with_orgs().count()

    @property
    @cache.collection_cache('org.Org', '_all_orgs_following')
    def get_all_orgs_following(self):
        org_commitments = self.commitments.with_orgs().fetch_generic_relations()
        return [commitment.entity for commitment in org_commitments]

    @property
    def get_orgs_following_ids(self):
        return self.commitments.with_orgs().values_list('object_id', flat=True)

    @property
    @cache.collection_cache('org.Org', '_sample_orgs_following')
    def get_sample_orgs_following(self):
        org_commitments = self.commitments.with_orgs()[:5].fetch_generic_relations()
        return [commitment.entity for commitment in org_commitments]

    @property
    @cache.collection_cache('org.Org', '_recommended_orgs')
    def get_recommended_orgs(self):
        []
#        from org.models import Org
#        ids = list(set(Org.objects.filter(recommended = True).values_list('id', flat = True)).difference(self.get_orgs_following_ids))[0:5]
#        return Org.objects.filter(id__in = ids)


    @property
    @cache.collection_cache('issue.Issue', '_all_issues_following')
    def get_all_issues_following(self):
        issue_commitments = self.commitments.with_issues().fetch_generic_relations()
        return [commitment.entity for commitment in issue_commitments]

    @property
    def get_issues_following_ids(self):
        return self.usertoissuefollow_set.filter(following = True).values_list('issue_id', flat = True)

    @property
    @cache.collection_cache('issue.Issue', '_sample_issues_following')
    def get_sample_issues_following(self):
        issue_commitments = self.commitments.with_issues()[:5].fetch_generic_relations()
        return [commitment.entity for commitment in issue_commitments]

    @property
    @cache.collection_cache('org.Org', '_get_orgs_admin_of')
    def get_orgs_admin_of(self):
        from org.models import Org
        return [o.org for o in Org.admins.through.objects.filter(user=self)]


    @property
    def get_age_group(self):
        if self.birth_year:
            current_year = datetime.datetime.now().year
            age = int(current_year) - int(self.birth_year)
            if age > 1:
                for age_group in AGE_GROUPS:
                    if age >= age_group[0] and age <= age_group[1]:
                        return '%s-%s' % (str(age_group[0]), str(age_group[1]))
        return ''

    @property
    def get_api_key(self):
        try:
            key = ApiKey.objects.get(user=self)
            return key.key
        except:
            return None

    @property
    def get_location(self):
        if self._location is not None:
            return self._location
        self._location = self.location
        cache.put_on_handle(self, self.username)
        return self._location


    @property
    def get_image_small(self):
        if self.thumb_img_url:
            return self.thumb_img_url
        elif self.facebook_id:
            return 'http://graph.facebook.com/%s/picture?type=square' % self.facebook_id
        else:
            return '%s/static/img/missing_profile_photo_small.png' % settings.STATIC_URL

    @property
    def get_image_large(self):
        if self.large_img_url:
            return self.large_img_url
        elif self.facebook_id:
            return 'http://graph.facebook.com/%s/picture?type=large' % self.facebook_id
        else:
            return '%s/static/img/missing_profile_photo_large.png' % settings.STATIC_URL


    def delete(self):
        cache.bust_on_handle(self, self.username, False)
        return super(self.__class__, self).delete()

    def update_fb_follows(self, fb_ids, send_notifications=True):
        accounts = User.objects.filter(facebook_id__in = fb_ids)
        for acc in accounts:
            uuf, created = UserToUserFollow.objects.get_or_create(followed = acc, follower = self)
            if created:
                uuf.is_following = True
                uuf.save()
                cache.bust_on_handle(acc, acc.username)
                if acc.enable_followed_notification and send_notifications:
                    from mailer.notification_tasks import send_notification, EmailTypes
                    send_notification(type=EmailTypes.FOLLOW, user=acc, entity=self)

    def is_subscribed_to(self, pub_id):
        return len(self.subscriptions.filter(id=pub_id, subscription__subscribed=True).values_list('id')) > 0

    def upload_profile_pic(self, image):
        if not image:
            return
        opened_image = Image.open(image)
        for size_name, (w, h) in USER_IMAGE_SIZES.iteritems():
            (url, width, height) = upload_user_image(opened_image, self.id, size_name, w, h)
            setattr(self, '%s_img_url' % size_name, url)

    def generate_new_api_key(self):
        key, created = ApiKey.objects.get_or_create(user = self)
        if not created:
            #DON'T TRY AND CHANGE THE KEY VALUE.  DELETE INSTEAD
            key.delete()
            key = ApiKey(user = self)
        key.save()
        return key.key

class ActiveManager(models.Manager):
    def get_query_set(self):
        return super(ActiveManager, self).get_query_set().filter(is_following=True)

class UserToUserFollow(models.Model):
    is_following = models.BooleanField(default = True, db_index = True)
    started_following = models.DateTimeField(auto_now_add = True)
    stopped_following = models.DateTimeField(blank = True, null = True)
    followed = models.ForeignKey('User', related_name = 'followed_user')
    follower = models.ForeignKey('User', related_name = 'following_user')
    objects = models.Manager()
    actives = ActiveManager()

    class Meta:
        unique_together = (("followed", "follower"),)

    def __unicode__(self):
        return "User '%s' following User '%s'" % (self.follower, self.followed)


class PasswordResetRequest(models.Model):
    user = models.ForeignKey(User)
    uid = models.CharField(max_length = 36, db_index = True)

########NEW FILE########
__FILENAME__ = users_tags
from django import template
from users.models import UserToUserFollow
from django.core.urlresolvers import reverse

register = template.Library()

@register.inclusion_tag('user/includes/follow_button.html', takes_context=True)
def follow_button(context, followed):
    user = context['user']

    button_class = "button"
    button_text = "Follow"
    post_url = ""
    if user.is_authenticated():
        if UserToUserFollow.actives.filter(follower=user, followed=followed).count():
            button_class += " unfollow"
            button_text = "Unfollow"
            post_url = reverse('unfollow_user', args=[followed.id])
        else:
            button_class += " follow"
            post_url = reverse('follow_user', args=[followed.id])
    else:
        button_class += " follow login"

    button = '<input class="%s" type="submit" value="%s" data-url="%s" />' % (button_class, button_text, post_url)

    return {
        'user': user,
        'post_url': post_url,
        'button': button,
    }

########NEW FILE########
__FILENAME__ = models
from django.core.exceptions import ValidationError
from django.test import TestCase
from users.models import User

REQUIRED_USER_FIELDS = {'username':'testing', 'long_email':'fake@fake.com', 'password':'fake'}

class UserTestCase(TestCase):
    fixtures = []

    def test_required_fields(self):
        # Test minimum set of fields required for new user to pass validations
        u = User(**REQUIRED_USER_FIELDS)
        u.full_clean()

        # Validation should fail when no username is provided
        u = User(**self._req_fields_without('username'))
        self.assertRaises(ValidationError, u.full_clean)

        # Validation should fail when no email is provided
        u = User(**self._req_fields_without('long_email'))
        self.assertRaises(ValidationError, u.full_clean)

        # Validation should fail when no password is provided
        u = User(**self._req_fields_without('password'))
        self.assertRaises(ValidationError, u.full_clean)

    def _req_fields_without(self, field_name):
        f = REQUIRED_USER_FIELDS.copy()
        f.update({field_name:''})
        return f

########NEW FILE########
__FILENAME__ = views
from django.core import mail
from etc.constants import ACCOUNT_COOKIE_SALT, ACCOUNT_COOKIE
from etc.tests import ViewsBaseTestCase, BASE_TEST_USER, BASE_TEST_PASS, NON_FB_USER
from django.core.urlresolvers import reverse


VALID_CREATE_USER_FORM_DATA = dict(first_name="Doktr", last_name="Nepharious", gender='male', password='tester01', email='notreal@ffffake.com',
                                   birth_year='1909', fbid='',
                                   fb_access_token='',
                                   friends='174800237,538431833,671896922,1626665502,100001197186897,100001739003909',
                                   location='New York, United States (Town)',
                                   location_data='{"name":"New York","latitude":"40.714550","longitude":"-74.007118","postal_code":"","address":"","type":"Town","raw_geodata":{"lang":"en-US","uri":"http://where.yahooapis.com/v1/place/2459115","woeid":"2459115","placeTypeName":{"code":"7","content":"Town"},"name":"New York","country":{"code":"US","type":"Country","content":"United States"},"admin1":{"code":"US-NY","type":"State","content":"New York"},"admin2":null,"admin3":null,"locality1":{"type":"Town","content":"New York"},"locality2":null,"postal":null,"centroid":{"latitude":"40.714550","longitude":"-74.007118"},"boundingBox":{"southWest":{"latitude":"40.495682","longitude":"-74.255653"},"northEast":{"latitude":"40.917622","longitude":"-73.689484"}},"areaRank":"4","popRank":"13"},"locality":"New York","region":"New York","country_name":"United States"}')

INVALID_CREATE_USER_FORM_DATA = dict()


class PageTests(ViewsBaseTestCase):

    def test_index(self):
        index_url = '/'
        index_template = 'etc/home.html'
        index_template_loggedin = 'user/home.html'

        #Logged Out Test
        self.basic_200_test(index_url, index_template)
        #Logged In Test
        self.login()
        self.basic_200_test(index_url, index_template_loggedin)


    def test_login(self):
        """More thorough version of what's being done in the base class"""
        #MAKE SURE COOKIES DON'T EXIST
        self.assertEqual(self.client.cookies.get(ACCOUNT_COOKIE, None), None)
        self.assertEqual(self.client.cookies.get(ACCOUNT_COOKIE_SALT, None), None)

        redirect_to = "/"
        response = self.client.post("/login", data={"username":BASE_TEST_USER, "password":BASE_TEST_PASS, "redirect_to":redirect_to})
        self.assertRedirects(response, redirect_to)
        #Make Sure Cookies Are There And Have Value
        self.assertNotEqual(self.client.cookies.get(ACCOUNT_COOKIE, None), None)
        self.assertNotEqual(self.client.cookies.get(ACCOUNT_COOKIE_SALT, None), None)
        self.assertNotEqual(self.client.cookies[ACCOUNT_COOKIE].value, "")
        self.assertNotEqual(self.client.cookies[ACCOUNT_COOKIE_SALT].value, "")

        #Make sure a non-fb user can log in as well.
        self.logout()
        response = self.client.post("/login", data={"username":NON_FB_USER['email'], "password":NON_FB_USER['pwd'], "redirect_to":redirect_to})
        self.assertRedirects(response, redirect_to)


    def test_logout(self):
        self.login()

        #Make Sure Cookies Are There And Have Value
        self.assertNotEqual(self.client.cookies.get(ACCOUNT_COOKIE, None), None)
        self.assertNotEqual(self.client.cookies.get(ACCOUNT_COOKIE_SALT, None), None)
        self.assertNotEqual(self.client.cookies[ACCOUNT_COOKIE].value, "")
        self.assertNotEqual(self.client.cookies[ACCOUNT_COOKIE_SALT].value, "")

        #Make Sure Cookies Are Gone
        self.client.get('/logout')
        self.assertEqual(self.client.cookies[ACCOUNT_COOKIE].value, "")
        self.assertEqual(self.client.cookies[ACCOUNT_COOKIE_SALT].value, "")

    def test_setup(self):
        setup_url = "/setup"
        setup_success_url = "/"
        setup_template = "user/setup.html"

        #Test Page Loads
        self.basic_200_test(setup_url, setup_template)
        #Test Invalid Post
        self.form_fails_test(setup_url, INVALID_CREATE_USER_FORM_DATA, "create_form", setup_template)
        #Test Valid Post (View Redirects so we don't do normal test here.)
        response = self.client.post(setup_url, VALID_CREATE_USER_FORM_DATA)
        self.assertRedirects(response, setup_success_url)

    def test_discover(self):
        discover_url = "/discover"
        discover_template = "user/discover.html"

        #Not logged in should redirect!
        self.login_redirect_test(discover_url)

        #Logged in should be good.
        self.login()
        self.basic_200_test(discover_url, discover_template)

    def test_settings(self):
        settings_url = reverse('settings')
        settings_template = "user/settings.html"

        #Not logged in should redirect!
        self.login_redirect_test(settings_url)

        #Logged in should be good.
        self.login()
        self.basic_200_test(settings_url, settings_template)

    def test_forgot_password(self):
        url = "/forgot_password"
        template = "user/forgot_password.html"
        template_success = "user/forgot_password_confirm.html"

        self.basic_200_test(url, template)

        #Failed Attempt Should Use the Same Template
        response = self.client.post(url, dict(email="adfasdfasdf"))
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 0)
        self.assertTemplateUsed(response, template)

        #Succesful Attempt Should Use the Success Template
        response = self.client.post(url, dict(email="brennan@jumo.com"))
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 0)
        self.assertTemplateUsed(response, template_success)

        self.assertEquals(len(mail.outbox), 1)

########NEW FILE########
__FILENAME__ = views
import datetime
from datetime import timedelta
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect, HttpResponse, Http404
from etc import cache
from etc.entities import create_handle
from etc.auth import attempt_login, logout, set_auth_cookies, unset_auth_cookies
from etc.decorators import NotLoggedInRequired, AccountRequired, PostOnly
from etc.user import hash_password
from etc.view_helpers import render, json_response, render_inclusiontag, render_string
from lib.image_upload import upload_user_image
import logging
from mailer.notification_tasks import send_notification, EmailTypes
from message.models import Subscription, NOTIFICATIONS_PUB
from popularity.models import Section, Sections, TopList
from users.forms import LoginForm, CreateAccountForm, UserSettingsForm, PhotoUploadForm, UserNotificationsForm, UserConnectForm
from users.models import User, PasswordResetRequest, UserToUserFollow
from entity_items.models.location import Location
from utils import fb_helpers
from uuid import uuid4
import json
from discovery.models import DiscoveryMap
from django.shortcuts import get_object_or_404, redirect

@AccountRequired
def upload_photo(request):
    if request.method == 'POST':
        form = PhotoUploadForm(request.POST, request.FILES, instance=request.user)

        if form.is_valid():
            u = form.save(commit=False)
            u.upload_profile_pic(form.cleaned_data['profile_pic'])
            u.save()
            return HttpResponseRedirect("/")
    else:
        form = PhotoUploadForm(instance=request.user)

    return render(request, 'user/photo_upload.html', {
            'user_photo_upload_form': form,
            'entity':request.user,
            'form': form,
    })

@NotLoggedInRequired
def login_permalink(request):
    form = LoginForm()
    post_auth_action = request.GET.get('post_auth_action', 'redirect');
    redirect_to = request.GET.get('redirect_to', None)
    redirect_to = redirect_to if redirect_to != "/login" else None
    if request.POST:
        form = LoginForm(request.POST)
        if form.is_valid():
            email_or_username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            redirect_to = form.cleaned_data['redirect_to']
            post_auth_action = form.cleaned_data['post_auth_action']

            if redirect_to == None or redirect_to == 'None':
                redirect_to = "/"

            user = attempt_login(request, email_or_username, password)
            if user is not None and user.is_active:
                response = HttpResponseRedirect(redirect_to)
                if post_auth_action == 'close':
                    response = render(request, 'util/closing_window.html')

                return set_auth_cookies(response, user)
            else:
                form._errors["username"] = form.error_class(['The username and password you entered are incorrect.'])

    return render(request, 'user/login.html', {
        'title' : 'Login',
        'redirect_to' : redirect_to,
        'post_auth_action' : post_auth_action,
        'login_form': form})

def logout_permalink(request):
    logout(request)
    return unset_auth_cookies(HttpResponseRedirect(reverse('index')))

@NotLoggedInRequired
def setup(request):
    sans_facebook = True if request.GET.has_key('sans_facebook') and request.GET['sans_facebook'] else False
    redirect_to = request.GET.get('redirect_to', "/")

    form = CreateAccountForm(initial={'redirect_to': redirect_to,})
    if request.POST:
        sans_facebook = True if request.POST.has_key('sans_facebook') and request.POST['sans_facebook'] else False
        form = CreateAccountForm(request.POST)
        if form.is_valid():
            u = User()
            u.bio = form.cleaned_data['bio']
            u.birth_year = form.cleaned_data['birth_year']
            u.email = u.long_email = form.cleaned_data['email']
            u.fb_access_token = form.cleaned_data['fb_access_token']
            u.gender = form.cleaned_data['gender']
            u.first_name = form.cleaned_data['first_name']
            u.last_name = form.cleaned_data['last_name']
            u.facebook_id = form.cleaned_data['fbid']
            u.bio = u.bio.encode('utf-8') if u.bio else ""
            u.first_name = u.first_name.encode('utf-8') if u.first_name else ""
            u.last_name = u.last_name.encode('utf-8') if u.last_name else ""
            if form.cleaned_data['location_data']:
                u.location = Location.get_or_create(form.cleaned_data['location_data'])
            u.next_email_time = datetime.datetime.now() + timedelta(days = 1)
            u.username = create_handle('%s%s' % (u.first_name, u.last_name))
            u.password = hash_password(form.cleaned_data['password'])
            u.save()

            Subscription.get_or_create(user = u, pub_id = NOTIFICATIONS_PUB)

            #Post to Facebook
            if form.cleaned_data['post_to_facebook']:
                fb_helpers.post_joined_to_wall(u)

            cache.put_on_handle(u, u.username)

            redirect_to = form.cleaned_data['redirect_to'] or '/'
            #perform for all that login magic that happens under the covers
            attempt_login(request, u.username, form.cleaned_data["password"])
            return set_auth_cookies(HttpResponseRedirect(redirect_to), u)

    return render(request, 'user/setup.html', {
        'title' : 'Setup your account',
        'create_form' : form,
        'sans_facebook': sans_facebook,
        })

@AccountRequired
def discover(request):
    return render(request, 'user/discover.html', {
        'title' : 'Discover'
        })

@AccountRequired
def home(request):
    top_categories, sub_category_groups, discovery_item_groups = DiscoveryMap.get_lists()
    list_ids = [l.id for l in Section.get_lists(Sections.SIGNED_IN_HOME)]
    lists = TopList.get_entities_for_lists(list_ids)
    if len(lists) > 0:
        recommended_orgs = lists.items()[0][1]
    else:
        recommended_orgs = []


    form = PhotoUploadForm(instance=request.user)

    return render(request, 'user/home.html', {
            'user_photo_upload_form': form,
            'title' : 'Home',
            'entity' : None,
            'top_categories': top_categories,
            'sub_category_groups': sub_category_groups,
            'discovery_item_groups': discovery_item_groups,
            'recommended_orgs': recommended_orgs
    })

@AccountRequired
def settings(request):
    success = False
    if request.method == 'POST':
        form = UserSettingsForm(request.POST, request.FILES, instance=request.user)

        old_pw_hash = request.user.password
        if form.is_valid():
            u = form.save(commit=False)
            if u.password:
                u.password = hash_password(u.password)
            else:
                u.password = old_pw_hash
            if form.cleaned_data['profile_pic']:
                u.upload_profile_pic(form.cleaned_data['profile_pic'])
            if form.cleaned_data['location_data']:
                u.location = Location.get_or_create(form.cleaned_data['location_data'])
            u.save()
            success = True
    else:
        if request.user.location:
            location_input = str(request.user.location)
            location_data = request.user.location.to_json()
        else:
            location_input = location_data = ''
        form = UserSettingsForm(instance=request.user, initial={'location_input':location_input,
                                                                'location_data':location_data,})

    return render(request, 'user/settings.html', {
            'success': success,  #to drop a little notice like "CONGRATS #WINNING"
            'entity':request.user,
            'form': form,
    })

@AccountRequired
def notifications(request):
    success = False
    if request.POST:
        form = UserNotificationsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            success = True
    else:
        form = UserNotificationsForm(instance=request.user)

    return render(request, 'user/notifications.html', {
        'form': form,
        'success': success,  #to drop a little notice like "CONGRATS #WINNING"
    })

@AccountRequired
def connect(request):
    success = False
    if request.POST:
        form = UserConnectForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            success = True
    else:
        form = UserConnectForm(instance=request.user)

    return render(request, 'user/connect.html', {
        'form': form,
        'success': success,  #to drop a little notice like "CONGRATS #WINNING"
    })

@AccountRequired
def developer(request):
    if request.POST:
        request.user.generate_new_api_key()
    return render(request, 'user/developer.html', {})

def old_user_permalink(request, mongo_id):
    try:
        user = User.objects.get(mongo_id = mongo_id)
        return HttpResponsePermanentRedirect(reverse('entity_url', args=[user.username]))
    except:
        raise Http404

def forgot_password(request):
    error = None
    if request.method == 'POST':
        if 'email' in request.POST:
            try:
                u = User.objects.get(email = request.POST['email'].strip(), is_active=True)
                pr = PasswordResetRequest()
                pr.user = u
                pr.uid = str(uuid4().hex)
                pr.save()
                send_notification(type=EmailTypes.RESET_PASSWORD,
                                  user=u,
                                  entity=u,
                                  password_reset_id=pr.uid)
                return render(request, 'user/forgot_password_confirm.html', {})
            except User.DoesNotExist:
                error = "Sorry, this user account does not exist."
            except Exception:
                logging.exception("Error In Forgot Password Post")
                error = "Sorry, an unknown error has occurred."
    return render(request, 'user/forgot_password.html', {
        'error' : error
    })


def reset_password(request, reset_id):
    error = None
    if request.method == 'POST' and 'password' in request.POST and request.POST['password']:
        try:
            p = PasswordResetRequest.objects.get(uid = reset_id)
            u = p.user
            u.password = hash_password(request.POST['password'].strip())
            u.save()

            #perform for all that login magic that happens under the covers
            user = attempt_login(request, u.username, request.POST['password'].strip())
            p.delete()
            return set_auth_cookies(HttpResponseRedirect('/'), user)
        except Exception:
            logging.exception("Error In Reset Password")
            error = 'There was an error resetting your password.'

    return render(request, 'user/reset_password.html', {
        'error' : error,
        'reset_token' : reset_id,
    })

@AccountRequired
@PostOnly
def follow(request, user_id):
    followed = get_object_or_404(User, pk=user_id)
    follow_instance, created = UserToUserFollow.objects.get_or_create(follower=request.user, followed=followed)
    if not follow_instance.is_following:
        follow_instance.is_following = True
        follow_instance.save()
    if created:
        send_notification(type=EmailTypes.FOLLOW,
                user=followed, entity=request.user)
    cache.bust(followed)

    if request.is_ajax():
        button = render_inclusiontag(request, "follow_button followed", "users_tags", {'followed': followed})
        return json_response({'button': button})
    else:
        return redirect(followed)

@AccountRequired
@PostOnly
def unfollow(request, user_id):
    followed = get_object_or_404(User, pk=user_id)
    try:
        follow_instance = UserToUserFollow.objects.get(follower=request.user, followed=followed)
        follow_instance.is_following = False
        follow_instance.stopped_following = datetime.datetime.now()
        follow_instance.save()
    except UserToUserFollow.DoesNotExist:
        pass
    cache.bust(followed)

    if request.is_ajax():
        button = render_inclusiontag(request, "follow_button followed", "users_tags", {'followed': followed})
        return json_response({'button': button})
    else:
        return redirect(followed)

def follower_list(request, user_id):
    start = int(request.GET.get('start', 0))
    end = int(request.GET.get('end', 20))
    user = get_object_or_404(User, id=user_id)
    followers = user.get_active_followers()[start:end]

    html = render_string(request, "user/includes/user_list.html", {
        'users': followers,
        'start_index': start,
        'list_type': 'followers',
    })

    return json_response({
        'html': html,
        'has_more': end < user.get_num_followers,
    })

def following_list(request, user_id):
    start = int(request.GET.get('start', 0))
    end = int(request.GET.get('end', 20))
    user = get_object_or_404(User, id=user_id)
    followings = user.get_active_followings()[start:end]

    html = render_string(request, "user/includes/user_list.html", {
        'users': followings,
        'start_index': start,
        'list_type': 'followings',
    })

    return json_response({
        'html': html,
        'has_more': end < user.get_num_users_following,
    })

@AccountRequired
@PostOnly
def remove_user(request):
    request.user.is_active = False
    request.user.save()
    cache.bust_on_handle(request.user, request.user.username)
    logout(request)
    return unset_auth_cookies(HttpResponseRedirect('/'))

########NEW FILE########
__FILENAME__ = base_daemon
'''
Created on Apr 13, 2011

@author: al
'''

from datetime import datetime

import sys
import os
import logging
import signal
import time
from contextlib import contextmanager
from optparse import OptionParser
from logging import StreamHandler
from logging.handlers import RotatingFileHandler

def get_logger(name, settings, console=False, log_file_name=None):
    """
    Defaults to set up logging to a file.
    If console==True also add a StreamHandler to log to console
    """
    if log_file_name is None:
        log_file_name = settings.LOG_DIR + name + '.log'
    os.path.isdir(settings.LOG_DIR) or os.makedirs(settings.LOG_DIR)

    log = logging.getLogger(name)
    log.setLevel(settings.LOG_LEVEL)
    handler = RotatingFileHandler(log_file_name)
    formatter = logging.Formatter(settings.LOG_FORMAT)
    handler.setFormatter(formatter)
    log.addHandler(handler)

    if console:
        foreground_handler = StreamHandler(sys.stdout)
        log.addHandler(foreground_handler)

    return log

class DaemonAlreadyRunningException(Exception):
    pass

class DaemonInterruptException(Exception):
    pass

@contextmanager
def pid_lock(lock_file_path):
    """ Usage:
    with pid_lock(some_file):
        # Do stuff
    """
    lock_dir = os.path.dirname(lock_file_path)
    if not os.path.exists(lock_dir):
        os.makedirs(lock_dir)

    has_lock = False
    try:
        if os.path.isfile(lock_file_path):
            lockfile = open(lock_file_path)
            pid = int(lockfile.readline())
            if pid == os.getpid():
                has_lock = True
            else:
                raise DaemonAlreadyRunningException('Daemon is already running with process id %d' % pid)
        else:
            with open(lock_file_path, 'w') as lock_file:
                pid = os.getpid()
                lock_file.write(str(pid)+'\n')
            has_lock = True
        yield pid
    finally:
        if has_lock:
            os.remove(lock_file_path)

class JumoDaemon(object):
    # Override this in subclass!
    process_name='jumo_daemon'
    sleep_interval=60
    max_sleep_interval = 60

    def __init__(self, settings, log_to_console=None, log_level='debug', sleep_interval=None):
        self.startup_time = datetime.now()
        # Allows for debugging when you want to run with a sleep of 1, etc.
        if sleep_interval is not None:
            self.sleep_interval = int(sleep_interval)
        else:
            self.sleep_interval = self.__class__.sleep_interval
        self.logger = get_logger(self.process_name, settings, console=log_to_console)
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        self.logger.info('%s started' % self.process_name)

    @classmethod
    def get_options_parser(cls):
        parser = OptionParser('usage: %prog [options]')
        parser.add_option('-l', '--log-level', dest='log_level', action='store', choices=('DEBUG','INFO','WARN','CRITICAL','ERROR'), help='log level [DEBUG,INFO,WARN,CRITICAL,ERROR]')
        parser.add_option('-v', '--verbose', dest='log_to_console', action='store_true', help='redirect log output to console')
        parser.add_option('-t', '--time_to_sleep', dest='sleep_interval', action='store', help='sleep interval in seconds')
        return parser

    def reset_sleep(self):
        self.sleep_interval = self.__class__.sleep_interval

    def increase_sleep(self):
        if self.sleep_interval <= self.max_sleep_interval:
            self.sleep_interval += 1

    def die(self):
        raise DaemonInterruptException()

    def run(self):
        signal.signal(signal.SIGINT, lambda sig,frm: self.die())
        signal.signal(signal.SIGTERM, lambda sig,frm: self.die())

        try:
            self.run_loop()
        except DaemonInterruptException:
            self.logger.warn('%s killed by outside process' % self.process_name)


    def run_loop(self):
        while True:
            sleep_interval = self.run_iteration()
            if sleep_interval:
                self.logger.info('Sleeping for %d seconds' % sleep_interval)
                time.sleep(sleep_interval)

    # Override this!!!!
    def run_iteration(self):
        sleep_interval = 1
        self.logger.warn("You didn't override run_iteraion!!!!")
        return sleep_interval

    @classmethod
    def start(cls, settings):
        parser = cls.get_options_parser()
        (options, args) = parser.parse_args()
        with pid_lock(os.path.join('/var/lock/jumo', cls.process_name + '.lock')):
            cls(settings, options.log_to_console, options.log_level, options.sleep_interval).run()

########NEW FILE########
__FILENAME__ = custom_validators
from django.core.exceptions import ValidationError
from django.db.models import get_model

class BlankUniqueValidator(object):
    def __init__(self, app_label, model_name, field_name):
        self.app_label = app_label
        self.model_name = model_name
        self.field_name = field_name

    def __call__(self, value):
        if value:
            model = get_model(self.app_label, self.model_name)
            if model.objects.filter(**{self.field_name: value}).count() > 0:
                verbose_name = model._meta.get_field_by_name(self.field_name)[0].verbose_name
                raise ValidationError('Another %s with this %s already exists.' % (
                    model.__name__, verbose_name))

########NEW FILE########
__FILENAME__ = db
from django.db import connections

def db_time(db='default'):
    cur = connections[db].cursor()
    cur.execute('select utc_timestamp()')
    return cur.fetchone()[0]
########NEW FILE########
__FILENAME__ = fb_helpers
from django.conf import settings
from lib.facebook import GraphAPI
import logging

DEFAULT_FB_IMAGE = '%s/static/img/logo-jumo_small.png' % settings.STATIC_URL

#FOR LOCAL DEV'ING
if settings.STATIC_URL == "":
    DEFAULT_FB_IMAGE = "http://jumostatic.s3.amazonaws.com/static/img/logo-jumo_small.png"

def post_donation_to_wall(user, entity):
    fb_name = "%s just donated to %s on Jumo" % (user.first_name, entity.get_name)
    fb_link = 'http://%s%s?utm_source=donate&utm_medium=facebook&utm_campaign=jumo' % (settings.HTTP_HOST, entity.get_url)
    _post_to_fb_wall(user.fb_access_token, '', {'name':fb_name,'link':fb_link,'picture':DEFAULT_FB_IMAGE})

def post_joined_to_wall(user):
    fb_name = '%s just joined Jumo.' % user.first_name
    fb_link = 'http://%s/%s?utm_source=newsignup&utm_medium=facebook&utm_campaign=jumo' % (settings.HTTP_HOST, user.username.encode('utf-8'))
    fb_desc = "Jumo connects individuals and organizations working to change the world."
    _post_to_fb_wall(user.fb_access_token, '', {'name':fb_name, 'link':fb_link, 'description':fb_desc, 'picture':DEFAULT_FB_IMAGE})


def _post_to_fb_wall(access_token, message='', attachments={}, profile_id=''):
    try:
        if not settings.BLOCK_FB_POSTS:
            GraphAPI(access_token).put_wall_post(message, attachments, profile_id)
        else:
            logging.info("This log is a simulated FB Wall Post. Params:\nmessage: %s\nattachments: %s\nprofile_id: %s" % (message, attachments, profile_id))
    except:
        logging.exception("FB WALL POST Exception")

########NEW FILE########
__FILENAME__ = misc_helpers
"""
Oh man, I started a misc module.  I can't wait to see what this turns
into in 3 years.  I'm sorry future me that this has become the dumping
ground you will now have to organize.  Have a beer on me.
"""

def send_admins_error_email(subject, msg, exc_info):
    from django.conf import settings
    from django.core.mail import mail_admins
    import sys
    import traceback

    if settings.DEBUG:
        return
    subject = "Error (CUSTOM): %s" % subject
    tb = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
    message = "%s\n\n%s" % (msg, tb)
    mail_admins(subject, message, fail_silently=True)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = query_set
from django.db import models

class QuerySet(models.query.QuerySet):
    @classmethod
    def as_manager(cls):
        class QuerySetManager(models.Manager):
            use_for_related_fields = True

            def __init__(self):
                super(QuerySetManager, self).__init__()
                self.queryset_class = cls

            def get_query_set(self):
                return self.queryset_class(self.model)

            def __getattr__(self, attr, *args):
                try:
                    return getattr(self.__class__, attr, *args)
                except AttributeError:
                    return getattr(self.get_query_set(), attr, *args)

        return QuerySetManager()

########NEW FILE########
__FILENAME__ = regex_tools
#!/usr/bin/python
import logging
import gdata.youtube.service
import json
import re
import time
import urllib
from urlparse import urlsplit, urlunsplit, parse_qs

YQL_URL = "http://query.yahooapis.com/v1/public/yql?"
YQL_PARAMS = {"q":"",
              "format":"json",
              "env":"store://datatables.org/alltableswithkeys",
             }


#All regex is evil magic cast with the devils own spells.
def do_voodoo_regex(subject, regex_spells):
  result = None
  for regex_match in regex_spells:
    res = regex_match.search(subject)
    if res and res.groups() and len(res.groups()) > 0:
      result = res.groups()[0]
      break
  return result


def do_yql_query_thang(query):
  return_value = None
  try:
    YQL_PARAMS["q"] = query
    params = urllib.urlencode(YQL_PARAMS)
    string_result = urllib.urlopen(YQL_URL+params).read()
    result = json.loads(string_result)
    if result.has_key('query') and result["query"].has_key('results') and result["query"]["results"]:
      return_value = result["query"]["results"]
  except Exception, err:
    logging.exception(query)
    raise err
  finally:
    #time.sleep(2.5) #enforce sleep
    pass

  return return_value

def facebook_id_magic(subject):
  graph_url = 'http://graph.facebook.com/%s'

  regex_spells = [re.compile('(?:www|).facebook.com/(?:pages|people)/.*/([0-9]+)'),
                  re.compile('(?:www|).facebook.com/profile.php\?id=([0-9]+)'),
                  re.compile('(?:www|).facebook.com/(?!pages|group|search|people)([a-zA-Z0-9]+)')]

  identifier = None
  #Did they give us a url?
  if subject.find("facebook.com") >= 0:
    identifier = do_voodoo_regex(subject, regex_spells)

  if not identifier:
    #Maybe they gave us something good.
    identifier = subject.replace(' ','')

  #No need to try catch as we WANT the exception if it fails.
  url = graph_url % identifier
  string_result = urllib.urlopen(url).read()
  result = json.loads(string_result)

  #time.sleep(1)
  if result and result.has_key('id'):
    return int(result['id']) #Evil wins again.
  #Fail
  return None


def twitter_id_magic(subject):
  screen_name_query = "SELECT * FROM twitter.users WHERE screen_name='%s'"
  id_query = "SELECT * FROM twitter.users WHERE id='%s'"

  regex_spells = [re.compile('twitter.com/#?!?/?([a-zA-Z0-9]+)(\/|\||$)')]

  identifier = None
  if subject.find("twitter.com") >= 0:
    identifier = do_voodoo_regex(subject, regex_spells)

  if not identifier:
    identifier = subject.replace(' ','')

  query = screen_name_query
  if identifier.isdigit():
    query = id_query

  result = do_yql_query_thang(query % identifier)
  if result:
    return result["user"]["screen_name"]
  return ""


def youtube_id_magic(subject):
  id_query = "SELECT * FROM youtube.user WHERE id='%s'"
  regex_spells = [re.compile('youtube.com/(?:user\/|)(?!watch|user)([a-zA-Z0-9]+)')]

  identifier = None
  if subject.find("youtube.com") >= 0:
    identifier = do_voodoo_regex(subject, regex_spells)

  if not identifier:
    identifier = subject.replace(' ', '')

  result = do_yql_query_thang(id_query % identifier)
  if result and result["user"]["id"]:
    return result["user"]["id"]
  return ""


def youtube_url_magic(url):
    try:
        return_data = {"title":"", "description":"", "url":url, "image":"", "image_choices":[], "source_id":""}
        main_url_split= urlsplit(url)
        if 'youtube.com' in main_url_split.netloc or 'youtube' in main_url_split.netloc:
            qparams = parse_qs(main_url_split.query)
            id = None
            re_query = "(?<=v=)[a-zA-Z0-9-]+(?=&)|(?<=[0-9]/)[^&\n]+|(?<=v=)[^&\n]+"
            re_result = re.findall(re_query, url)
            if len(re_result) > 0:
                id = re_result[0]

            if id is not None:
                yt_service = gdata.youtube.service.YouTubeService()
                yt_service.ssl = False
                entry = yt_service.GetYouTubeVideoEntry(video_id=id)
                vid = entry.media
                return_data = dict(title = vid.title.text,
                                   description = vid.description.text,
                                   url = vid.content[0].url,
                                   image_choices=[img.url for img in vid.thumbnail],
                                   source_id = id
                                   )
        return return_data
    except Exception as e:
        import logging
        logging.exception(e)
    return None



def flickr_id_magic(subject):
  url_query = "SELECT * FROM flickr.urls.lookupuser WHERE url='%s'"
  id_query = "SELECT * FROM flickr.people.getInfo WHERE user_id='%s'"
  username_query = "SELECT * FROM flickr.getidfromusername where username='%s'"
  username_query2 = "SELECT * FROM flickr.people.findbyusername WHERE username='%s'"  #Yes...there are two calls that behave differently.

  if subject.find("flickr.com") >= 0:
    result = do_yql_query_thang(url_query % subject)
  elif subject.find("@") >= 0: #flickr's got weird user ids
    result = do_yql_query_thang(id_query % subject)
  else:
    result = do_yql_query_thang(username_query % subject)
    if not result:
      print "Doing backup username query...so lame."
      result = do_yql_query_thang(username_query2 % subject)

  #Flickr's crazy...some of their usernames are sentences so we're taking id instead.
  if result:
    if result.has_key("user"):
      return result["user"]["id"]
    elif result.has_key("person"):
      return result["person"]["id"]
    elif result.has_key("user_id"):
      return result["user_id"]
  return ""


def vimeo_id_magic(subject):
  id_query = "SELECT * FROM vimeo.user.info WHERE username='%s'"
  regex_spells = [re.compile('vimeo.com/([a-zA-Z0-9]+)(/[a-zA-Z0-9]+)?')]

  identifier = None
  if subject.find("vimeo.com") >= 0:
    identifier = do_voodoo_regex(subject, regex_spells)

  if not identifier:
    identifier = subject.replace(' ','')

  result = do_yql_query_thang(id_query % identifier)
  #Vimeo doesn't actually include a username in their result so just use what we have
  if result and result.has_key("users") and result["users"].has_key("user"):
    return identifier
  return ""

########NEW FILE########
__FILENAME__ = share_helpers
import urllib

def get_twitter_share_url(url, text):
    twitter_params = urllib.urlencode({"url":url,"text":text})
    return "http://twitter.com/share?%s" % twitter_params

def get_facebook_share_url(url, text):
    facebook_params = urllib.urlencode({"u":url, "t":text})
    return "http://facebook.com/sharer.php?%s" % facebook_params

########NEW FILE########
__FILENAME__ = widgets
from django.forms.widgets import Widget
from django.template.loader import render_to_string
from entity_items.models.location import Location
from django.utils.encoding import force_unicode

class LocationWidget(Widget):
    def render(self, name, value, attrs=None):
        location_name = location_data = ''
        try:
            location = Location.objects.get(id=value)
            location_name = str(location)
            location_data = location.to_json()
        except Location.DoesNotExist:
            pass

        return render_to_string('widgets/location_widget.html', {
            'location_name': location_name,
            'location_data': location_data,
            'name': name,
        })

    def value_from_datadict(self, data, files, name):
        location_data = data.get(name)
        location = Location.get_or_create(location_data)
        if location:
            return location.id
        return None

class MultipleLocationWidget(Widget):
    def render(self, name, value, attrs=None):
        if value is None: value = []
        locations = Location.objects.in_bulk(value)
        location_data = []
        for (id, location) in locations.iteritems():
            location_data.append((str(location), location.to_json()))

        return render_to_string('widgets/working_locations.html', {
            'location_data': location_data,
            'name': name,
        })

    def value_from_datadict(self, data, files, name):
        location_data = data.getlist(name)
        location_ids = []
        for data in location_data:
            if not data: continue
            location = Location.get_or_create(data)
            location_ids.append(location.id)
        return location_ids

    def _has_changed(self, initial, data):
        if initial is None:
            initial = []
        if data is None:
            data = []
        if len(initial) != len(data):
            return True
        initial_set = set([force_unicode(value) for value in initial])
        data_set = set([force_unicode(value) for value in data])
        return data_set != initial_set

########NEW FILE########
__FILENAME__ = django_settings
##### DEV ######

import djcelery
###############################
#       CAMPAIGN SETTINGS     #
##############################


###############################
#       ADMIN SETTINGS       #
##############################
ADMIN_MEDIA_PREFIX = 'http://jumostatic.s3.amazonaws.com/static/media/admin/'


###############################
#       STATIC SETTINGS       #
##############################
STATIC_URL = "http://jumostatic.s3.amazonaws.com"


###############################
#         DB SETTINGS        #
##############################
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'jumodjango',
        'USER': 'jumo',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }

}


###############################
#       EMAIL SETTINGS       #
##############################
DEFAULT_FROM_EMAIL = 'no-reply@jumo.com'
EMAIL_HOST = ''
EMAIL_PORT = 25
EMAIL_HOST_USER = 'jumodev@jumo.com'
EMAIL_HOST_PASSWORD = ''
EMAIL_USER_TLS = False
EMAIL_BACKEND = 'mailer.backend.JumoEmailBackend'


###############################
#      CELERY SETTINGS       #
##############################

# AMQP setup for Celery
BROKER_HOST = ""
BROKER_PORT = 5672
BROKER_USER = "jumo"
BROKER_PASSWORD = ""
BROKER_VHOST = "/"

##############################
#      DSTK SETTINGS
##############################

DSTK_API_BASE = "http://DSTKHOST"

##############################
#      DATAMINE SETTINGS
##############################

IS_DATAMINE = True

###############################
#      DJANGO SETTINGS       #
##############################
CACHE_BACKEND = 'memcached://HOST:11211/?timeout=86400'
HTTP_HOST = "www.ogbon.com"


###############################
#      API KEY SETTINGS       #
##############################
#DEV FACEBOOK INFO
FACEBOOK_APP_ID = ''
FACEBOOK_API_KEY = ''
FACEBOOK_SECRET = ''

#DEV AWS INFO
AWS_ACCESS_KEY = ''
AWS_SECRET_KEY = ''
AWS_PHOTO_UPLOAD_BUCKET = ""

MIXPANEL_TOKEN = ''

djcelery.setup_loader()

########NEW FILE########
__FILENAME__ = django_settings
CACHE_BACKEND = 'memcached://HOSTNAME:11211/?timeout=86400'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'jumodjango',
        'USER': 'jumo',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

SOLR_CONN = "http://localhost:8983/solr"

#DEV FACEBOOK INFO
FACEBOOK_APP_ID = ''
FACEBOOK_API_KEY = ''
FACEBOOK_SECRET = ''

#DEV AWS INFO
AWS_ACCESS_KEY = ''
AWS_SECRET_KEY = ''
AWS_PHOTO_UPLOAD_BUCKET = ""

########NEW FILE########
__FILENAME__ = django_settings
##### DEV ######

import djcelery
###############################
#       CAMPAIGN SETTINGS     #
##############################


###############################
#       ADMIN SETTINGS       #
##############################
ADMIN_MEDIA_PREFIX = 'http://jumostatic.s3.amazonaws.com/static/media/admin/'


###############################
#       STATIC SETTINGS       #
##############################
STATIC_URL = "http://jumostatic.s3.amazonaws.com"


###############################
#         DB SETTINGS        #
##############################
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'jumodjango',
        'USER': 'jumo',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }

}

###############################
#       DISQUS  SETTINGS     #
##############################
DISQUS_API_VERSION = '3.0'
DISQUS_FORUM_NAME = ''
DISQUS_SECRET_KEY = '' # jumo_test_app
DISQUS_PUBLIC_KEY = '' # jumo_test_app
DISQUS_DEV_MODE = 1 # 1 for dev, 0 for prod and stage


###############################
#       EMAIL SETTINGS       #
##############################
DEFAULT_FROM_EMAIL = 'no-reply@jumo.com'
EMAIL_HOST = ''
EMAIL_PORT = 25
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USER_TLS = False
EMAIL_BACKEND = 'mailer.backend.JumoEmailBackend'


###############################
#      CELERY SETTINGS       #
##############################

# AMQP setup for Celery
BROKER_HOST = ""
BROKER_PORT = 5672
BROKER_USER = "jumo"
BROKER_PASSWORD = ""
BROKER_VHOST = "/"


###############################
#      DJANGO SETTINGS       #
##############################
CACHE_BACKEND = 'memcached://HOSTNAME:11211/?timeout=86400'
HTTP_HOST = "www.ogbon.com"

###############################
#      DATAMINE SETTINGS
###############################

DATAMINE_BASE = "http://DATAMINEBASE"

###############################
#      API KEY SETTINGS       #
##############################
#DEV FACEBOOK INFO
FACEBOOK_APP_ID = ''
FACEBOOK_API_KEY = ''
FACEBOOK_SECRET = ''

#DEV AWS INFO
AWS_ACCESS_KEY = ''
AWS_SECRET_KEY = ''
AWS_PHOTO_UPLOAD_BUCKET = ""

# DATA SCIENCE TOOLKIT
DSTK_API_BASE = "http://DSTK_HOST"

MIXPANEL_TOKEN = ''

djcelery.setup_loader()

########NEW FILE########
__FILENAME__ = django_settings
import djcelery
###############################
#       CAMPAIGN SETTINGS     #
##############################


###############################
#       ADMIN SETTINGS       #
##############################
ADMIN_MEDIA_PREFIX = 'http://ADMINHOST/static/media/admin/'


###############################
#       STATIC SETTINGS       #
##############################
STATIC_URL = "http://jumostatic.s3.amazonaws.com"
NO_STATIC_HASH = True

###############################
#         DB SETTINGS        #
##############################
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'jumodjango',
        'USER': 'jumo',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}


###############################
#       SOLR  SETTINGS       #
##############################
SOLR_CONN = "http://SOLRHOST:8983/solr"


###############################
#       EMAIL SETTINGS       #
##############################
DEFAULT_FROM_EMAIL = 'no-reply@jumo.com'
EMAIL_HOST = ''
EMAIL_PORT = 25
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USER_TLS = False


###############################
#      CELERY SETTINGS       #
##############################
BROKER_HOST = "localhost"


###############################
#      DJANGO SETTINGS       #
##############################
CACHE_BACKEND = 'memcached://HOSTNAME:11211/?timeout=86400'


###############################
#      API KEY SETTINGS       #
##############################
#DEV FACEBOOK INFO
FACEBOOK_APP_ID = ''
FACEBOOK_API_KEY = ''
FACEBOOK_SECRET = ''

#DEV AWS INFO
AWS_ACCESS_KEY = ''
AWS_SECRET_KEY = ''
AWS_PHOTO_UPLOAD_BUCKET = ""

djcelery.setup_loader()

########NEW FILE########
__FILENAME__ = local_settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'jumodjango',
        'USER': 'jumo',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '',
    },
}

PROXY_SERVER = ""
BROKER_HOST = ""
BROKER_PORT = 5672
BROKER_USER = ""
BROKER_PASSWORD = ""
BROKER_VHOST = "/"

#Facebook settings
FACEBOOK_APP_ID = ''
FACEBOOK_API_KEY = ''
FACEBOOK_SECRET = ''


STATIC_URL = "http://localhost:8000"
HTTP_HOST = "localhost:8000"
ADMIN_MEDIA_PREFIX = STATIC_URL + '/static/media/admin/'
#ADMIN_MEDIA_PREFIX = 'http://static.jumo.com/static/media/admin/'

IGNORE_HTTPS = True
CELERY_ALWAYS_EAGER=True

DSTK_API_BASE = "http://DSTKSERVER"

# Make sure to fill in S3 info
AWS_ACCESS_KEY = ''
AWS_SECRET_KEY = ''
AWS_PHOTO_UPLOAD_BUCKET = ""


########NEW FILE########
