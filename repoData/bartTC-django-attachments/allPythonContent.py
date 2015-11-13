__FILENAME__ = admin
from attachments.models import Attachment
from django.contrib.contenttypes import generic

class AttachmentInlines(generic.GenericStackedInline):
    model = Attachment
    extra = 1
########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from attachments.models import Attachment

class AttachmentForm(forms.ModelForm):
    attachment_file = forms.FileField(label=_('Upload attachment'))

    class Meta:
        model = Attachment
        fields = ('attachment_file',)

    def save(self, request, obj, *args, **kwargs):
        self.instance.creator = request.user
        self.instance.content_type = ContentType.objects.get_for_model(obj)
        self.instance.object_id = obj.id
        super(AttachmentForm, self).save(*args, **kwargs)
########NEW FILE########
__FILENAME__ = models
from datetime import datetime
import os
from django.db import models
from django.conf import settings 
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils.translation import ugettext_lazy as _

# From https://github.com/etianen/django-reversion/pull/206/files
UserModel = getattr(settings, 'AUTH_USER_MODEL', 'auth.User') 

class AttachmentManager(models.Manager):
    def attachments_for_object(self, obj):
        object_type = ContentType.objects.get_for_model(obj)
        return self.filter(content_type__pk=object_type.id,
                           object_id=obj.id)

class Attachment(models.Model):
    def attachment_upload(instance, filename):
        """Stores the attachment in a "per module/appname/primary key" folder"""
        return 'attachments/%s/%s/%s' % (
            '%s_%s' % (instance.content_object._meta.app_label,
                       instance.content_object._meta.object_name.lower()),
                       instance.content_object.pk,
                       filename)

    objects = AttachmentManager()

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    creator = models.ForeignKey(UserModel, related_name="created_attachments", verbose_name=_('creator'))
    attachment_file = models.FileField(_('attachment'), upload_to=attachment_upload)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    modified = models.DateTimeField(_('modified'), auto_now=True)

    class Meta:
        ordering = ['-created']
        permissions = (
            ('delete_foreign_attachments', 'Can delete foreign attachments'),
        )

    def __unicode__(self):
        return '%s attached %s' % (self.creator.get_username(), self.attachment_file.name)

    @property
    def filename(self):
        return os.path.split(self.attachment_file.name)[1]

########NEW FILE########
__FILENAME__ = attachments_tags
from django.template import Library, Node, Variable
from attachments.forms import AttachmentForm
from attachments.views import add_url_for_obj
from django.core.urlresolvers import reverse
from attachments.models import Attachment

register = Library()

@register.inclusion_tag('attachments/add_form.html', takes_context=True)
def attachment_form(context, obj):
    """
    Renders a "upload attachment" form.
    
    The user must own ``attachments.add_attachment permission`` to add
    attachments.
    """
    if context['user'].has_perm('attachments.add_attachment'):
        return {
            'form': AttachmentForm(),
            'form_url': add_url_for_obj(obj),
            'next': context['request'].build_absolute_uri(),
        }
    else:
        return {
            'form': None,
        }

@register.inclusion_tag('attachments/delete_link.html', takes_context=True)
def attachment_delete_link(context, attachment):
    """
    Renders a html link to the delete view of the given attachment. Returns
    no content if the request-user has no permission to delete attachments.
    
    The user must own either the ``attachments.delete_attachment`` permission
    and is the creator of the attachment, that he can delete it or he has
    ``attachments.delete_foreign_attachments`` which allows him to delete all
    attachments.
    """
    if context['user'].has_perm('delete_foreign_attachments') \
       or (context['user'] == attachment.creator and \
           context['user'].has_perm('attachments.delete_attachment')):
        return {
            'next': context['request'].build_absolute_uri(),
            'delete_url': reverse('delete_attachment', kwargs={'attachment_pk': attachment.pk})
        }
    return {'delete_url': None,}



class AttachmentsForObjectNode(Node):
    def __init__(self, obj, var_name):
        self.obj = obj
        self.var_name = var_name

    def resolve(self, var, context):
        """Resolves a variable out of context if it's not in quotes"""
        if var[0] in ('"', "'") and var[-1] == var[0]:
            return var[1:-1]
        else:
            return Variable(var).resolve(context)

    def render(self, context):
        obj = self.resolve(self.obj, context)
        var_name = self.resolve(self.var_name, context)
        context[var_name] = Attachment.objects.attachments_for_object(obj)
        return ''

@register.tag
def get_attachments_for(parser, token):
    """
    Resolves attachments that are attached to a given object. You can specify
    the variable name in the context the attachments are stored using the `as`
    argument. Default context variable name is `attachments`.

    Syntax::

        {% get_attachments_for obj %}
        {% for att in attachments %}
            {{ att }}
        {% endfor %}

        {% get_attachments_for obj as "my_attachments" %}

    """
    def next_bit_for(bits, key, if_none=None):
        try:
            return bits[bits.index(key)+1]
        except ValueError:
            return if_none

    bits = token.contents.split()
    args = {
        'obj': next_bit_for(bits, 'get_attachments_for'),
        'var_name': next_bit_for(bits, 'as', '"attachments"'),
    }
    return AttachmentsForObjectNode(**args)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *

urlpatterns = patterns('',
    url(r'^add-for/(?P<app_label>[\w\-]+)/(?P<module_name>[\w\-]+)/(?P<pk>\d+)/$', 'attachments.views.add_attachment', name="add_attachment"),
    url(r'^delete/(?P<attachment_pk>\d+)/$', 'attachments.views.delete_attachment', name="delete_attachment"),
)
########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpResponseRedirect
from django.db.models.loading import get_model
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext, ugettext_lazy as _
from django.template.context import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from attachments.models import Attachment
from attachments.forms import AttachmentForm

def add_url_for_obj(obj):
    return reverse('add_attachment', kwargs={
                        'app_label': obj._meta.app_label,
                        'module_name': obj._meta.module_name,
                        'pk': obj.pk
                    })

@require_POST
@login_required
def add_attachment(request, app_label, module_name, pk,
                   template_name='attachments/add.html', extra_context={}):

    next = request.POST.get('next', '/')
    model = get_model(app_label, module_name)
    if model is None:
        return HttpResponseRedirect(next)
    obj = get_object_or_404(model, pk=pk)
    form = AttachmentForm(request.POST, request.FILES)

    if form.is_valid():
        form.save(request, obj)
        messages.success(request, ugettext('Your attachment was uploaded.'))
        return HttpResponseRedirect(next)
    else:
        template_context = {
            'form': form,
            'form_url': add_url_for_obj(obj),
            'next': next,
        }
        template_context.update(extra_context)
        return render_to_response(template_name, template_context,
                                  RequestContext(request))

@login_required
def delete_attachment(request, attachment_pk):
    g = get_object_or_404(Attachment, pk=attachment_pk)
    if request.user.has_perm('delete_foreign_attachments') \
       or request.user == g.creator:
        g.delete()
        messages.success(request, ugettext('Your attachment was deleted.'))
    next = request.REQUEST.get('next') or '/'
    return HttpResponseRedirect(next)

########NEW FILE########
