__FILENAME__ = admin
from django.contrib import admin
from privatebeta.models import InviteRequest

class InviteRequestAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ('email', 'created', 'invited',)
    list_filter = ('created', 'invited',)

admin.site.register(InviteRequest, InviteRequestAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from privatebeta.models import InviteRequest

class InviteRequestForm(forms.ModelForm):
    class Meta:
        model = InviteRequest
        fields = ['email']

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings
from django.http import HttpResponseRedirect

class PrivateBetaMiddleware(object):
    """
    Add this to your ``MIDDLEWARE_CLASSES`` make all views except for
    those in the account application require that a user be logged in.
    This can be a quick and easy way to restrict views on your site,
    particularly if you remove the ability to create accounts.
    
    **Settings:**
    
    ``PRIVATEBETA_ENABLE_BETA``
        Whether or not the beta middleware should be used. If set to `False` 
        the PrivateBetaMiddleware middleware will be ignored and the request 
        will be returned. This is useful if you want to disable privatebeta 
        on a development machine. Default is `True`.
    
    ``PRIVATEBETA_NEVER_ALLOW_VIEWS``
        A list of full view names that should *never* be displayed.  This
        list is checked before the others so that this middleware exhibits
        deny then allow behavior.
    
    ``PRIVATEBETA_ALWAYS_ALLOW_VIEWS``
        A list of full view names that should always pass through.

    ``PRIVATEBETA_ALWAYS_ALLOW_MODULES``
        A list of modules that should always pass through.  All
        views in ``django.contrib.auth.views``, ``django.views.static``
        and ``privatebeta.views`` will pass through unless they are
        explicitly prohibited in ``PRIVATEBETA_NEVER_ALLOW_VIEWS``
    
    ``PRIVATEBETA_REDIRECT_URL``
        The URL to redirect to.  Can be relative or absolute.
    """

    def __init__(self):
        self.enable_beta = getattr(settings, 'PRIVATEBETA_ENABLE_BETA', True)
        self.never_allow_views = getattr(settings, 'PRIVATEBETA_NEVER_ALLOW_VIEWS', [])
        self.always_allow_views = getattr(settings, 'PRIVATEBETA_ALWAYS_ALLOW_VIEWS', [])
        self.always_allow_modules = getattr(settings, 'PRIVATEBETA_ALWAYS_ALLOW_MODULES', [])
        self.redirect_url = getattr(settings, 'PRIVATEBETA_REDIRECT_URL', '/invite/')

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.user.is_authenticated() or not self.enable_beta:
            # User is logged in, no need to check anything else.
            return
        whitelisted_modules = ['django.contrib.auth.views', 'django.views.static', 'privatebeta.views']
        if self.always_allow_modules:
            whitelisted_modules += self.always_allow_modules

        full_view_name = '%s.%s' % (view_func.__module__, view_func.__name__)

        if full_view_name in self.never_allow_views:
            return HttpResponseRedirect(self.redirect_url)

        if full_view_name in self.always_allow_views:
            return
        if '%s' % view_func.__module__ in whitelisted_modules:
            return
        else:
            return HttpResponseRedirect(self.redirect_url)

########NEW FILE########
__FILENAME__ = 0001_initial

from south.db import db
from django.db import models
from privatebeta.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'InviteRequest'
        db.create_table('privatebeta_inviterequest', (
            ('id', orm['privatebeta.InviteRequest:id']),
            ('email', orm['privatebeta.InviteRequest:email']),
            ('created', orm['privatebeta.InviteRequest:created']),
        ))
        db.send_create_signal('privatebeta', ['InviteRequest'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'InviteRequest'
        db.delete_table('privatebeta_inviterequest')
        
    
    
    models = {
        'privatebeta.inviterequest': {
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }
    
    complete_apps = ['privatebeta']

########NEW FILE########
__FILENAME__ = 0002_add_invited_field

from south.db import db
from django.db import models
from privatebeta.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding field 'InviteRequest.invited'
        db.add_column('privatebeta_inviterequest', 'invited', orm['privatebeta.inviterequest:invited'])
        
    
    
    def backwards(self, orm):
        
        # Deleting field 'InviteRequest.invited'
        db.delete_column('privatebeta_inviterequest', 'invited')
        
    
    
    models = {
        'privatebeta.inviterequest': {
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invited': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'})
        }
    }
    
    complete_apps = ['privatebeta']

########NEW FILE########
__FILENAME__ = models
import datetime
from django.db import models
from django.utils.translation import ugettext_lazy as _

class InviteRequest(models.Model):
    email = models.EmailField(_('Email address'), unique=True)
    created = models.DateTimeField(_('Created'), default=datetime.datetime.now)
    invited = models.BooleanField(_('Invited'), default=False)

    def __unicode__(self):
        return _('Invite for %(email)s') % {'email': self.email}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'privatebeta.views.invite', name='privatebeta_invite'),
    url(r'^sent/$', 'privatebeta.views.sent', name='privatebeta_sent'),
)

########NEW FILE########
__FILENAME__ = views
from django.views.generic.simple import direct_to_template
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from privatebeta.forms import InviteRequestForm

def invite(request, form_class=InviteRequestForm, template_name="privatebeta/invite.html", extra_context=None):
    """
    Allow a user to request an invite at a later date by entering their email address.
    
    **Arguments:**
    
    ``template_name``
        The name of the tempalte to render.  Optional, defaults to
        privatebeta/invite.html.

    ``extra_context``
        A dictionary to add to the context of the view.  Keys will become
        variable names and values will be accessible via those variables.
        Optional.
    
    **Context:**
    
    The context will contain an ``InviteRequestForm`` that represents a
    :model:`invitemelater.InviteRequest` accessible via the variable ``form``.
    If ``extra_context`` is provided, those variables will also be accessible.
    
    **Template:**
    
    :template:`privatebeta/invite.html` or the template name specified by
    ``template_name``.
    """
    form = form_class(request.POST or None)
    if form.is_valid():
        form.save()
        return HttpResponseRedirect(reverse('privatebeta_sent'))

    context = {'form': form}

    if extra_context is not None:
        context.update(extra_context)

    return render_to_response(template_name, context,
        context_instance=RequestContext(request))

def sent(request, template_name="privatebeta/sent.html", extra_context=None):
    """
    Display a message to the user after the invite request is completed
    successfully.
    
    **Arguments:**
    
    ``template_name``
        The name of the tempalte to render.  Optional, defaults to
        privatebeta/sent.html.

    ``extra_context``
        A dictionary to add to the context of the view.  Keys will become
        variable names and values will be accessible via those variables.
        Optional.
    
    **Context:**
    
    There will be nothing in the context unless a dictionary is passed to
    ``extra_context``.
    
    **Template:**
    
    :template:`privatebeta/sent.html` or the template name specified by
    ``template_name``.
    """
    return direct_to_template(request, template=template_name, extra_context=extra_context)

########NEW FILE########
