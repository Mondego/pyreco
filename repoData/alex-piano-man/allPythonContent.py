__FILENAME__ = backstage
import os

from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

from django_vcs.models import CodeRepository

register = template.Library()

class OtherRepos(template.Node):
    def __init__(self, repo, varname):
        self.repo = repo
        self.varname = varname

    def render(self, context):
        repo = self.repo.resolve(context)
        if repo:
            repo = repo.id
        else:
            repo = None
        context[self.varname] = CodeRepository.objects.exclude(id=repo)
        return ''

@register.tag
def get_other_repos(parser, token):
    bits = token.split_contents()
    bits.pop(0)
    repo = parser.compile_filter(bits.pop(0))
    varname = bits.pop()
    return OtherRepos(repo, varname)

@register.filter
def urlize_path(path, repo):
    bits = path.split(os.path.sep)
    parts = []
    for i, bit in enumerate(bits[:-1]):
        parts.append('<a href="%(url)s">%(path)s</a>' % {
            'url': reverse('code_browser', kwargs={
                'path': '/'.join(bits[:i+1])+'/',
                'slug': repo.slug
            }),
            'path': bit,
        })
    return ' / '.join(parts + bits[-1:])

@register.inclusion_tag('backstage/nav_bar_urls.html')
def nav_bar_urls(repo, nested):
    return {'repo': repo, 'nested': nested}

@register.inclusion_tag('backstage/chartlist.html', takes_context=True)
def chartlist(context, data, total, option):
    new_context = {
        'data': data,
        'total': total,
        'option': option,
        'request': context['request'],
        'repo': context['repo'],
    }
    return new_context

@register.inclusion_tag('backstage/form.html')
def render_form(form):
    return {'form': form}

########NEW FILE########
__FILENAME__ = utils
from functools import wraps

def cached_attribute(func):
    cache_name = '_%s' % func.__name__
    @wraps(func)
    def inner(self, *args, **kwargs):
        if hasattr(self, cache_name):
            return getattr(self, cache_name)
        val = func(self, *args, **kwargs)
        setattr(self, cache_name, val)
        return val
    return inner

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
__FILENAME__ = settings
# Django settings for a project.

import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

PROJECT_ROOT = os.path.normpath(os.path.dirname(__file__))

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = os.path.join(PROJECT_ROOT, 'dev.db')             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'static')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'ium@3m7noo)t6c!)8nq6d_3110=r)hj0g7qo2t)94f6+#f9&!!'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
#    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
)

INTERNAL_IPS = ('127.0.0.1',)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

def repo_get_absolute_url(obj):
    from django.core.urlresolvers import reverse
    return reverse('timeline', kwargs={'slug': obj.slug})

ABSOLUTE_URL_OVERRIDES = {
    'django_vcs.coderepository': repo_get_absolute_url,
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
#    'debug_toolbar',
    'django_vcs',
    'tickets',
    'timeline',
    'backstage',
)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from tickets.models import *

class TicketOptionInline(admin.TabularInline):
    model = TicketOption

class TicketAdmin(admin.ModelAdmin):
    pass

class TicketChangeItemInline(admin.TabularInline):
    model = TicketChangeItem

class TicketChangeAdmin(admin.ModelAdmin):
    inlines = [
        TicketChangeItemInline,
    ]

class TicketOptionChoiceInline(admin.TabularInline):
    model = TicketOptionChoice

class TicketOptionAdmin(admin.ModelAdmin):
    inlines = [
        TicketOptionChoiceInline
    ]

admin.site.register(TicketOption, TicketOptionAdmin)
admin.site.register(Ticket, TicketAdmin)
admin.site.register(TicketChange, TicketChangeAdmin)

########NEW FILE########
__FILENAME__ = filters
from django.db.models import Q
from django.forms import CheckboxSelectMultiple

from django_filters import FilterSet, MultipleChoiceFilter, BooleanFilter

from tickets.models import Ticket

class TicketChoiceFilter(MultipleChoiceFilter):
    def filter(self, qs, value):
        q = Q()
        for val in value:
            q |= Q(**{
                'selections__option__name': self.name,
                'selections__choice': val
            })
        return qs.filter(q).distinct()


def filter_for_repo(repo, exclude=None):
    filters = {}
    filters['Meta'] = type('Meta', (object,), {'model': Ticket, 'fields': []})
    filters['closed'] = MultipleChoiceFilter(
        label='Status', choices=[(0, 'open',), (1, 'closed')],
        widget=CheckboxSelectMultiple, initial=[0]
    )
    for option in repo.ticketoption_set.all():
        if exclude is None or (option.name not in exclude):
            filters[option.name] = TicketChoiceFilter(
                choices=[(o.id, o.text) for o in option.choices.all()],
                widget=CheckboxSelectMultiple
            )
    return type('TicketFilterSet', (FilterSet,), filters)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.datastructures import SortedDict

from tickets.models import (Ticket, TicketOption, TicketOptionChoice,
    TicketOptionSelection, TicketChange, TicketAttachment)

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'description']

class TicketDetailForm(forms.Form):
    extra_fields = set(['comment', 'closed'])
    def save(self, ticket, new=True, user=None, extra_changes=None, commit=True):
        if not new:
            changes = []
        for option in set(self.fields) - self.extra_fields:
            option = TicketOption.objects.get(name=option)
            choice = self.cleaned_data[option.name]
            if choice:
                choice = TicketOptionChoice.objects.get(pk=choice, option=option)
            else:
                choice = None
            if new:
                TicketOptionSelection.objects.create(ticket=ticket, option=option, choice=choice)
            else:
                try:
                    from_text = ticket.selections.get(option=option).choice.text
                except (AttributeError, TicketOptionSelection.DoesNotExist):
                    from_text = ''
                to_text = choice and choice.text or ''
                if from_text != to_text:
                    changes.append((option, from_text, to_text))
                updated = TicketOptionSelection.objects.filter(ticket=ticket, option=option).update(choice=choice)
                if not updated:
                    TicketOptionSelection.objects.create(ticket=ticket, option=option, choice=choice)
        if not new and (changes or self.cleaned_data['comment'] or
            extra_changes or self.cleaned_data['closed'] != ticket.closed):
            change = TicketChange.objects.create(ticket=ticket, user=user, text=self.cleaned_data['comment'])
            for option, from_text, to_text in changes:
                change.changes.create(option=option.name, from_text=from_text, to_text=to_text)
            if extra_changes:
                for option, (from_text, to_text) in extra_changes.iteritems():
                    change.changes.create(option=option, from_text=from_text, to_text=to_text)
            if self.cleaned_data['closed'] != ticket.closed:
                status = lambda s: s and "Closed" or "Open"
                change.changes.create(option="Status",
                    from_text=status(ticket.closed),
                    to_text=status(self.cleaned_data['closed'])
                )
                ticket.closed = self.cleaned_data['closed']

def get_ticket_form(repo, edit=False):
    fields = SortedDict()
    if edit:
        fields['comment'] = forms.CharField(widget=forms.Textarea, required=False)
    for option in TicketOption.objects.filter(repo=repo):
        fields[option.name] = forms.ChoiceField(
            choices=[('', 'None')]+[(o.id, o.text) for o in option.choices.all()],
            required=False
        )
    if edit:
        fields['closed'] = forms.BooleanField(required=False)
    return type('TicketForm', (TicketDetailForm,), fields)

class TicketAttachmentForm(forms.ModelForm):
    description = forms.CharField()

    class Meta:
        model = TicketAttachment
        fields = ('file', 'description')

########NEW FILE########
__FILENAME__ = managers
from django.db import models

class TicketManager(models.Manager):
    def open(self):
        return self.filter(closed=False)

########NEW FILE########
__FILENAME__ = models
import datetime

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models

from backstage.utils import cached_attribute
from django_vcs.models import CodeRepository

from tickets.managers import TicketManager

class Ticket(models.Model):
    repo = models.ForeignKey(CodeRepository, related_name="tickets")
    creator = models.ForeignKey(User)
    created_at = models.DateTimeField(default=datetime.datetime.now)
    closed = models.BooleanField(default=False)

    title = models.CharField(max_length=150)
    description = models.TextField()

    objects = TicketManager()

    def __unicode__(self):
        return "%s filed by %s" % (self.title, self.creator)

    @models.permalink
    def get_absolute_url(self):
        return ('ticket_detail', (), {'slug': self.repo.slug, 'ticket_id': self.pk})

class TicketOption(models.Model):
    name = models.CharField(max_length=100)
    repo = models.ForeignKey(CodeRepository)

    def __unicode__(self):
        return self.name

class TicketOptionChoice(models.Model):
    option = models.ForeignKey(TicketOption, related_name="choices")
    text = models.CharField(max_length=100)

    def __unicode__(self):
        return "%s for %s" % (self.text, self.option)

class TicketOptionSelection(models.Model):
    ticket = models.ForeignKey(Ticket, related_name="selections")
    option = models.ForeignKey(TicketOption)
    choice = models.ForeignKey(TicketOptionChoice, null=True)

    def __unicode__(self):
        return "%s for %s for %s" % (self.choice, self.option, self.ticket)

    class Meta:
        unique_together = (
            ('ticket', 'option'),
        )

class TicketChange(models.Model):
    ticket = models.ForeignKey(Ticket, related_name="changes")
    user = models.ForeignKey(User)
    at = models.DateTimeField(default=datetime.datetime.now)
    text = models.TextField()

    def get_absolute_url(self):
        if self.is_attachment():
            return TicketAttachment.objects.get(
                ticket=self.ticket, uploaded_by=self.user, uploaded_at=self.at,
                description=self.text
            ).get_absolute_url()
        # TODO: return this with an anchor to this item
        return self.ticket.get_absolute_url()

    @cached_attribute
    def closes_ticket(self):
        """
        Returns whether this change closes it's ticket.
        """
        try:
            changes = self.changes.get(option="Status")
            if changes.to_text == "Closed":
                return True
        except TicketChangeItem.DoesNotExist:
            return False

    @cached_attribute
    def is_attachment(self):
        """
        Returns whether this change is actually an attachment.
        """
        try:
            self.changes.get(option="Attachment")
            return True
        except TicketChangeItem.DoesNotExist:
            return False

class TicketChangeItem(models.Model):
    ticket_change = models.ForeignKey(TicketChange, related_name="changes")

    option = models.CharField(max_length=100)
    from_text = models.TextField()
    to_text = models.TextField()

    def as_text(self):
        if self.option == 'Attachment':
            return 'Added attachment %s' % self.to_text
        return '%s changed from %s to %s' % (self.option, self.from_text or None, self.to_text or None)


class TicketReport(models.Model):
    repo = models.ForeignKey(CodeRepository, related_name='reports')
    name = models.CharField(max_length=100)
    query_string = models.CharField(max_length=255)

    def get_absolute_url(self):
        return "%s?%s" % (
            reverse('ticket_list', kwargs={'slug': self.repo.slug}),
            self.query_string
        )

class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket, related_name='attachments')
    file = models.FileField(upload_to='attachments/')
    uploaded_by = models.ForeignKey(User)
    uploaded_at = models.DateTimeField(default=datetime.datetime.now)
    description = models.TextField()

    @models.permalink
    def get_absolute_url(self):
        return ('ticket_attachment', (), {
            'slug': self.ticket.repo.slug,
            'ticket_id': self.ticket.pk,
            'attachment_id': self.pk
        })

    def file_name(self):
        return self.file.name[len('attachments/'):]

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

ticket_urls = patterns('tickets.views',
    url(r'^$', 'ticket_list', name='ticket_list'),
    url(r'^new/$', 'new_ticket', name='new_ticket'),
    url(r'^(?P<ticket_id>\d+)/$', 'ticket_detail', name='ticket_detail'),
    url(r'^(?P<ticket_id>\d+)/attachment/(?P<attachment_id>\d+)/$', 'ticket_attachment', name='ticket_attachment'),
    url(r'^(?P<ticket_id>\d+)/attachment/new/$', 'ticket_new_attachment', name='ticket_new_attachment'),
    url(r'^reports/$', 'ticket_reports', name='ticket_reports'),
    url(r'^charts/$', 'ticket_option_charts', name='ticket_option_charts'),
    url(r'^charts/(?P<option>[\w-]+)/$', 'ticket_option_chart', name='ticket_option_chart')
)

urlpatterns = patterns('',
    (r'^(?P<slug>[\w-]+)/', include(ticket_urls)),
)

########NEW FILE########
__FILENAME__ = views
from datetime import datetime

from django.db.models import Count
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template import RequestContext

from django_vcs.models import CodeRepository

from tickets.filters import filter_for_repo
from tickets.forms import TicketForm, get_ticket_form, TicketAttachmentForm
from tickets.models import Ticket, TicketReport

def ticket_list(request, slug):
    repo = get_object_or_404(CodeRepository, slug=slug)
    if request.method == "POST":
        if not request.POST.get('report_name'):
            return redirect(request.get_full_path())
        TicketReport.objects.create(
            name=request.POST['report_name'],
            query_string=request.GET.urlencode(),
            repo=repo
        )
        return redirect('ticket_reports', slug=repo.slug)
    tickets = repo.tickets.all()
    filter = filter_for_repo(repo)(request.GET or None, queryset=tickets)
    return render_to_response([
        'tickets/%s/ticket_list.html' % repo.name,
        'tickets/ticket_list.html',
    ], {'repo': repo, 'filter': filter}, context_instance=RequestContext(request))

def new_ticket(request, slug):
    repo = get_object_or_404(CodeRepository, slug=slug)
    TicketDetailForm = get_ticket_form(repo)
    if request.method == "POST":
        form = TicketForm(request.POST)
        detail_form = TicketDetailForm(request.POST)
        if form.is_valid() and detail_form.is_valid():
            ticket = form.save(commit=False)
            ticket.repo = repo
            ticket.creator = request.user
            ticket.created_at = datetime.now()
            ticket.save()
            detail_form.save(ticket)
            return redirect(ticket)
    else:
        form = TicketForm()
        detail_form = TicketDetailForm()
    return render_to_response([
        'tickets/%s/new_ticket.html' % repo.name,
        'tickets/new_ticket.html',
    ], {'repo': repo, 'form': form, 'detail_form': detail_form}, context_instance=RequestContext(request))

def ticket_detail(request, slug, ticket_id):
    repo = get_object_or_404(CodeRepository, slug=slug)
    ticket = get_object_or_404(repo.tickets.all(), pk=ticket_id)
    TicketDetailForm = get_ticket_form(repo, edit=True)
    if request.method == "POST":
        detail_form = TicketDetailForm(request.POST)
        if detail_form.is_valid():
            detail_form.save(ticket, new=False, user=request.user)
            ticket.save()
            return redirect(ticket)
    else:
        detail_form = TicketDetailForm(initial=dict([
            (selection.option.name, selection.choice_id) for selection in ticket.selections.all()
        ] + [('closed', ticket.closed)]))
    return render_to_response([
        'tickets/%s/ticket_detail.html' % repo.name,
        'tickets/ticket_detail.html',
    ], {'repo': repo, 'ticket': ticket, 'detail_form': detail_form}, context_instance=RequestContext(request))

def nums_for_option(option, qs=None):
    if qs is None:
        qs = option.choices.all()
    qs = qs.annotate(c=Count('ticketoptionselection')).values_list('text', 'c')
    data = sorted(qs, key=lambda o: o[1], reverse=True)
    total = sum([o[1] for o in data])
    return data, total

def ticket_reports(request, slug):
    repo = get_object_or_404(CodeRepository, slug=slug)
    reports = repo.reports.all()
    return render_to_response([
        'tickets/%s/ticket_reoprts.html' % repo.name,
        'tickets/ticket_reports.html',
    ], {'repo': repo, 'reports': reports}, context_instance=RequestContext(request))

def ticket_attachment(request, slug, ticket_id, attachment_id):
    repo = get_object_or_404(CodeRepository, slug=slug)
    ticket = get_object_or_404(repo.tickets.all(), pk=ticket_id)
    attachment = get_object_or_404(ticket.attachments.all(), pk=attachment_id)
    return render_to_response([
        'tickets/%s/ticket_attachment.html' % repo.name,
        'tickets/ticket_attachment.html',
    ], {'repo': repo, 'ticket': ticket, 'attachment': attachment}, context_instance=RequestContext(request))

def ticket_new_attachment(request, slug, ticket_id):
    repo = get_object_or_404(CodeRepository, slug=slug)
    ticket = get_object_or_404(repo.tickets.all(), pk=ticket_id)
    if request.method == "POST":
        form = TicketAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.ticket = ticket
            attachment.uploaded_by = request.user
            attachment.save()
            changes = ticket.changes.create(
                user=request.user,
                text=attachment.description,
                at=attachment.uploaded_at
            )
            changes.changes.create(option="Attachment", to_text=attachment.file_name())
            return redirect(attachment)
    else:
        form = TicketAttachmentForm()
    return render_to_response([
        'tickets/%s/new_attachment.html' % repo.name,
        'tickets/new_attachment.html',
    ], {'repo': repo, 'ticket': ticket, 'form': form}, context_instance=RequestContext(request))

def ticket_option_charts(request, slug):
    repo = get_object_or_404(CodeRepository, slug=slug)
    options = repo.ticketoption_set.all()
    data = {}
    for option in options:
        data[option.name] = nums_for_option(option)
    return render_to_response([
        'tickets/%s/ticket_option_charts.html' % repo.name,
        'tickets/ticket_option_charts.html'
    ], {'repo': repo, 'data': data}, context_instance=RequestContext(request))

def ticket_option_chart(request, slug, option):
    repo = get_object_or_404(CodeRepository, slug=slug)
    option = get_object_or_404(repo.ticketoption_set, name__iexact=option)
    filter_class = filter_for_repo(repo, exclude=[option.name])
    filter = filter_class(request.GET or None, queryset=repo.tickets.all())
    data, total = nums_for_option(option,
        option.choices.filter(ticketoptionselection__ticket__in=filter.qs)
    )
    context = {
        'repo': repo,
        'option': option,
        'data': data,
        'total': total,
        'options': repo.ticketoption_set.exclude(id=option.id),
        'filter': filter
    }
    return render_to_response([
        'tickets/%s/ticket_option_chart.html' % repo.name,
        'tickets/ticket_option_chart.html',
    ], context, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = timeline
from django import template
from django.template.loader import render_to_string

register = template.Library()

@register.simple_tag
def timeline_item(item, repo, media_url):
    return render_to_string(
        'timeline/%s_obj.html' % type(item).__name__.lower(),
        {'item': item, 'repo': repo, 'MEDIA_URL': media_url}
    )

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('timeline.views',
    url(r'^(?P<slug>[\w-]+)/$', 'timeline', name='timeline'),
)

########NEW FILE########
__FILENAME__ = utils
def normalize_attr(objs, new_attr, keys):
    def key_func(o):
        return getattr(o, keys[type(o)])
    for obj in objs:
        setattr(obj, new_attr, key_func(obj))

########NEW FILE########
__FILENAME__ = views
from datetime import datetime, timedelta
from itertools import chain
from operator import attrgetter

from django.db.models import Max, Q
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from django_vcs.models import CodeRepository
from tickets.models import Ticket, TicketChange
from pyvcs.commit import Commit

from timeline.utils import normalize_attr

def timeline(request, slug):
    repo = get_object_or_404(CodeRepository, slug=slug)
    since = datetime.now() - timedelta(days=5)
    items = list(chain(
        Ticket.objects.filter(repo=repo, created_at__gte=since).order_by('-created_at'),
        TicketChange.objects.filter(ticket__repo=repo, at__gte=since).order_by('-at'),
        repo.get_recent_commits(since),
    ))
    normalize_attr(items, 'canonical_date',
        keys={Ticket: 'created_at', Commit: 'time', TicketChange: 'at'})
    items = sorted(items, key=attrgetter('canonical_date'), reverse=True)
    return render_to_response([
        'timeline/%s/timeline.html' % repo.name,
        'timeline/timeline.html',
    ], {'repo': repo, 'items': items}, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin

from tickets.urls import ticket_urls

admin.autodiscover()


repo_urls = patterns('',
    url(r'^timeline/$', 'timeline.views.timeline', name='timeline'),
    url(r'^tickets/', include(ticket_urls)),
    url(r'^commit/(?P<commit_id>.*)/$', 'django_vcs.views.commit_detail', name='commit_detail'),
    url(r'^browser/(?P<path>.*)$', 'django_vcs.views.code_browser', name='code_browser'),
)


urlpatterns = patterns('',
    url(r'^$', 'django_vcs.views.repo_list', name='repo_list'),
    url(r'^(?P<slug>[\w-]+)/', include(repo_urls)),
    url(r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    )

########NEW FILE########
