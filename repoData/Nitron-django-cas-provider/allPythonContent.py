__FILENAME__ = admin
from django.contrib import admin

from models import ServiceTicket, LoginTicket

class ServiceTicketAdmin(admin.ModelAdmin):
    pass
admin.site.register(ServiceTicket, ServiceTicketAdmin)

class LoginTicketAdmin(admin.ModelAdmin):
    pass
admin.site.register(LoginTicket, LoginTicketAdmin)
########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate

from utils import create_login_ticket

class LoginForm(forms.Form):
    username = forms.CharField(max_length=30)
    password = forms.CharField(widget=forms.PasswordInput)
    #warn = forms.BooleanField(required=False)  # TODO: Implement
    lt = forms.CharField(widget=forms.HiddenInput, initial=create_login_ticket)
    def __init__(self, service=None, renew=None, gateway=None, request=None, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.request = request
        if service is not None:
            self.fields['service'] = forms.CharField(widget=forms.HiddenInput, initial=service)
########NEW FILE########
__FILENAME__ = cleanuptickets
"""
A management command which deletes expired service tickets (e.g.,
from the database.

Calls ``ServiceTickets.objects.delete_expired_users()``, which
contains the actual logic for determining which accounts are deleted.

"""

from django.core.management.base import NoArgsCommand
from django.core.management.base import CommandError
from django.conf import settings

import datetime

from cas_provider.models import ServiceTicket, LoginTicket

class Command(NoArgsCommand):
    help = "Delete expired service tickets from the database"

    def handle_noargs(self, **options):
        print "Service tickets:"
        tickets = ServiceTicket.objects.all()
        for ticket in tickets:
            expiration = datetime.timedelta(minutes=settings.CAS_TICKET_EXPIRATION)
            if datetime.datetime.now() > ticket.created + expiration:
                print "Deleting %s..." % ticket.ticket
                ticket.delete()
            else:
                print "%s not expired..." % ticket.ticket
        tickets = LoginTicket.objects.all()
        print "Login tickets:"
        for ticket in tickets:
            expiration = datetime.timedelta(minutes=settings.CAS_TICKET_EXPIRATION)
            if datetime.datetime.now() > ticket.created + expiration:
                print "Deleting %s..." % ticket.ticket
                ticket.delete()
            else:
                print "%s not expired..." % ticket.ticket
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User

class ServiceTicket(models.Model):
    user = models.ForeignKey(User)
    service = models.URLField(verify_exists=False)
    ticket = models.CharField(max_length=256)
    created = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return "%s (%s) - %s" % (self.user.username, self.service, self.created)
        
class LoginTicket(models.Model):
    ticket = models.CharField(max_length=32)
    created = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return "%s - %s" % (self.ticket, self.created)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from views import *

urlpatterns = patterns('',
    url(r'^login/', login),
    url(r'^validate/', validate),
    url(r'^logout/', logout),
)
########NEW FILE########
__FILENAME__ = utils
from random import Random
import string

from models import ServiceTicket, LoginTicket

def _generate_string(length=8, chars=string.ascii_letters + string.digits):
    """ Generates a random string of the requested length. Used for creation of tickets. """
    return ''.join(Random().sample(chars, length))

def create_service_ticket(user, service):
    """ Creates a new service ticket for the specified user and service.
        Uses _generate_string.
    """
    ticket_string = 'ST-' + _generate_string(29) # Total ticket length = 29 + 3 = 32
    ticket = ServiceTicket(service=service, user=user, ticket=ticket_string)
    ticket.save()
    return ticket

def create_login_ticket():
    """ Creates a new login ticket for the login form. Uses _generate_string. """
    ticket_string = 'LT-' + _generate_string(29)
    ticket = LoginTicket(ticket=ticket_string)
    ticket.save()
    return ticket_string
########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.conf import settings

from forms import LoginForm
from models import ServiceTicket, LoginTicket
from utils import create_service_ticket

__all__ = ['login', 'validate', 'logout']

def login(request, template_name='cas/login.html', success_redirect=None ):
    if not success_redirect:
        success_redirect = settings.LOGIN_REDIRECT_URL
    if not success_redirect:
        success_redirect = '/accounts/profile/'
    service = request.GET.get('service', None)
    if request.user.is_authenticated():
        if service is not None:
            ticket = create_service_ticket(request.user, service)
            if service.find('?') == -1:
                return HttpResponseRedirect(service + '?ticket=' + ticket.ticket)
            else:
                return HttpResponseRedirect(service + '&ticket=' + ticket.ticket)
        else:
            return HttpResponseRedirect(success_redirect)
    errors = []
    if request.method == 'POST':
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)
        service = request.POST.get('service', None)
        lt = request.POST.get('lt', None)
        
        try:
            login_ticket = LoginTicket.objects.get(ticket=lt)
        except:
            errors.append('Login ticket expired. Please try again.')
        else:
            login_ticket.delete()
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    auth_login(request, user)
                    if service is not None:
                        ticket = create_service_ticket(user, service)

                        # Check to see if we already have a query string
                        if service.find('?') == -1:
                            return HttpResponseRedirect(service + '?ticket=' + ticket.ticket)
                        else:
                            return HttpResponseRedirect(service + '&ticket=' + ticket.ticket)
                    else:
                        return HttpResponseRedirect(success_redirect)
                else:
                    errors.append('This account is disabled.')
            else:
                    errors.append('Incorrect username and/or password.')
    form = LoginForm(service)
    return render_to_response(template_name, {'form': form, 'errors': errors}, context_instance=RequestContext(request))
    
def validate(request):
    service = request.GET.get('service', None)
    ticket_string = request.GET.get('ticket', None)
    if service is not None and ticket_string is not None:
        try:
            ticket = ServiceTicket.objects.get(ticket=ticket_string)
            username = ticket.user.username
            ticket.delete()
            return HttpResponse("yes\n%s\n" % username)
        except:
            pass
    return HttpResponse("no\n\n")
    
def logout(request, template_name='cas/logout.html'):
    url = request.GET.get('url', None)
    auth_logout(request)
    return render_to_response(template_name, {'url': url}, context_instance=RequestContext(request))

########NEW FILE########
