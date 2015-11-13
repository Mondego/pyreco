__FILENAME__ = admin
# -*- coding: utf-8 -
'''
Created on Mar 3, 2012

@author: Raul Garreta (raul@tryolabs.com)

Admin interface.
Based on django-chronograph.

'''

__author__      = "Raul Garreta (raul@tryolabs.com)"


import sys
import inspect
import pkgutil
import os.path
from datetime import datetime

from django import forms
from django.conf.urls.defaults import patterns, url
from django.contrib import admin
from django.core.management import get_commands
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db import models
from django.forms.util import flatatt
from django.http import HttpResponseRedirect, Http404
from django.template.defaultfilters import linebreaks
from django.utils import dateformat
from django.utils.datastructures import MultiValueDict
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.formats import get_format
from django.utils.text import capfirst
from django.utils.translation import ungettext, ugettext_lazy as _
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group

from kitsune.models import Job, Log, Host, NotificationUser, NotificationGroup
from kitsune.renderers import STATUS_OK, STATUS_WARNING, STATUS_CRITICAL, STATUS_UNKNOWN
from kitsune.base import BaseKitsuneCheck
 

def get_class(kls):
    parts = kls.split('.')
    module = ".".join(parts[:-1])
    m = __import__( module )
    for comp in parts[1:]:
        m = getattr(m, comp)            
    return m

class HTMLWidget(forms.Widget):
    def __init__(self,rel=None, attrs=None):
        self.rel = rel
        super(HTMLWidget, self).__init__(attrs)
    
    def render(self, name, value, attrs=None):
        if self.rel is not None:
            key = self.rel.get_related_field().name
            obj = self.rel.to._default_manager.get(**{key: value})
            related_url = '../../../%s/%s/%d/' % (self.rel.to._meta.app_label, self.rel.to._meta.object_name.lower(), value)
            value = "<a href='%s'>%s</a>" % (related_url, escape(obj))
            
        final_attrs = self.build_attrs(attrs, name=name)
        return mark_safe("<div%s>%s</div>" % (flatatt(final_attrs), linebreaks(value)))

class NotificationUserInline(admin.TabularInline):
    model = NotificationUser
    extra = 1
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(is_staff=True)
        return super(NotificationUserInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
    
class NotificationGroupInline(admin.TabularInline):
    model = NotificationGroup
    extra = 1
    
#from django.contrib.admin import SimpleListFilter
#
#class StatusCodeListFilter(SimpleListFilter):
#    # Human-readable title which will be displayed in the
#    # right admin sidebar just above the filter options.
#    title = _('status_code')
#
#    # Parameter for the filter that will be used in the URL query.
#    parameter_name = 'status_code'
#
#    def lookups(self, request, model_admin):
#        """
#        Returns a list of tuples. The first element in each
#        tuple is the coded value for the option that will
#        appear in the URL query. The second element is the
#        human-readable name for the option that will appear
#        in the right sidebar.
#        """
#        return (
#            ('0', _('OK')),
#            ('1', _('WARNING')),
#            ('2', _('ERROR')),
#            ('3', _('UNKNOWN')),
#        )
#
#    def queryset(self, request, queryset):
#        """
#        Returns the filtered queryset based on the value
#        provided in the query string and retrievable via
#        `self.value()`.
#        """
#        # Compare the requested value (either '80s' or 'other')
#        # to decide how to filter the queryset.
#        return queryset.filter(last_result__stderr=self.value())

    
class JobAdmin(admin.ModelAdmin):
    inlines = (NotificationUserInline, NotificationGroupInline)
    actions = ['run_selected_jobs']
    list_display = ('name', 'host', 'last_run_with_link', 'get_timeuntil',
                    'get_frequency',  'is_running', 'run_button', 'view_logs_button', 'status_code', 'status_message')
    list_display_links = ('name', )
    list_filter = ('host',)
    fieldsets = (
        ('Job Details', {
            'classes': ('wide',),
            'fields': ('name', 'host', 'command', 'args', 'disabled', 'renderer')
        }),
        ('Scheduling options', {
            'classes': ('wide',),
            'fields': ('frequency', 'next_run', 'params',)
        }),
        ('Log options', {
            'classes': ('wide',),
            'fields': ('last_logs_to_keep',)
        }),     
    )
    search_fields = ('name', )
    
    def last_run_with_link(self, obj):
        format = get_format('DATE_FORMAT')
        value = capfirst(dateformat.format(obj.last_run, format))
        
        try:
            log_id = obj.log_set.latest('run_date').id
            try:
                # Old way
                url = reverse('kitsune_log_change', args=(log_id,))
            except NoReverseMatch:
                # New way
                url = reverse('admin:kitsune_log_change', args=(log_id,))
            return '<a href="%s">%s</a>' % (url, value)
        except:
            return value
    last_run_with_link.admin_order_field = 'last_run'
    last_run_with_link.allow_tags = True
    last_run_with_link.short_description = 'Last run'
    
    def get_timeuntil(self, obj):
        format = get_format('DATE_FORMAT')
        value = capfirst(dateformat.format(obj.next_run, format))
        return "%s<br /><span class='mini'>(%s)</span>" % (value, obj.get_timeuntil())
    get_timeuntil.admin_order_field = 'next_run'
    get_timeuntil.allow_tags = True
    get_timeuntil.short_description = _('next scheduled run')
    
    def get_frequency(self, obj):
        freq = capfirst(obj.frequency.lower())
        if obj.params:
            return "%s (%s)" % (freq, obj.params)
        return freq
    get_frequency.admin_order_field = 'frequency'
    get_frequency.short_description = 'Frequency'
    
    def run_button(self, obj):
        on_click = "window.location='%d/run/?inline=1';" % obj.id
        return '<input type="button" onclick="%s" value="Run" />' % on_click
    run_button.allow_tags = True
    run_button.short_description = 'Run'
    
    def status_code(self, obj):
        if obj.last_result is not None:
            Renderer = get_class(obj.renderer)
            return Renderer().get_html_status(obj.last_result)
        else:
            return '--'
    status_code.allow_tags = True
    status_code.short_description = 'Status Code'
    
    def status_message(self, obj):
        if obj.last_result is not None:
            Renderer = get_class(obj.renderer)
            return '<a href=' + obj.last_result.admin_link() + '>' + Renderer().get_html_message(obj.last_result) + '</a>'
        else:
            return '--'
    status_message.allow_tags = True
    status_message.short_description = 'Status Message'
        
    def view_logs_button(self, obj):
        on_click = "window.location='../log/?job=%d';" % obj.id
        return '<input type="button" onclick="%s" value="View Logs" />' % on_click
    view_logs_button.allow_tags = True
    view_logs_button.short_description = 'Logs'
    
    def run_job_view(self, request, pk):
        """
        Runs the specified job.
        """
        try:
            job = Job.objects.get(pk=pk)
        except Job.DoesNotExist:
            raise Http404
        # Rather than actually running the Job right now, we
        # simply force the Job to be run by the next cron job
        job.force_run = True
        job.save()
        request.user.message_set.create(message=_('The job "%(job)s" has been scheduled to run.') % {'job': job})        
        if 'inline' in request.GET:
            redirect = request.path + '../../'
        else:
            redirect = request.REQUEST.get('next', request.path + "../")
        return HttpResponseRedirect(redirect)
    
    def get_urls(self):
        urls = super(JobAdmin, self).get_urls()
        my_urls = patterns('',
            url(r'^(.+)/run/$', self.admin_site.admin_view(self.run_job_view), name="kitsune_job_run")
        )
        return my_urls + urls
    
    def run_selected_jobs(self, request, queryset):
        rows_updated = queryset.update(next_run=datetime.now())
        if rows_updated == 1:
            message_bit = "1 job was"
        else:
            message_bit = "%s jobs were" % rows_updated
        self.message_user(request, "%s successfully set to run." % message_bit)
    run_selected_jobs.short_description = "Run selected jobs"
    
    def formfield_for_dbfield(self, db_field, **kwargs):
        request = kwargs.pop("request", None)
        
        # Add a select field of available commands
        if db_field.name == 'command':
            choices_dict = MultiValueDict()
            #l = get_commands().items():
            #l = [('kitsune_base_check', 'kitsune')]
            l = get_kitsune_checks()
            for command, app in l:
                choices_dict.appendlist(app, command)
            
            choices = []
            for key in choices_dict.keys():
                #if str(key).startswith('<'):
                #    key = str(key)
                commands = choices_dict.getlist(key)
                commands.sort()
                choices.append([key, [[c,c] for c in commands]])
                
            kwargs['widget'] = forms.widgets.Select(choices=choices)
            return db_field.formfield(**kwargs)
        kwargs['request'] = request    
        return super(JobAdmin, self).formfield_for_dbfield(db_field, **kwargs)


def get_kitsune_checks():
    
    # Find the installed apps
    try:
        from django.conf import settings
        apps = settings.INSTALLED_APPS
    except (AttributeError, EnvironmentError, ImportError):
        apps = []

    paths = []
    choices = []
    
    for app in apps:
        paths.append((app, app + '.management.commands'))

    for app, package in paths:
        try:
            __import__(package)
            m = sys.modules[package]
            path = os.path.dirname(m.__file__)
            for _, name, _ in pkgutil.iter_modules([path]):
                pair = (name, app)
                __import__(package + '.' + name)
                m2 = sys.modules[package + '.' + name]
                for _, obj in inspect.getmembers(m2):
                    if inspect.isclass(obj) and issubclass(obj, BaseKitsuneCheck) and issubclass(obj, BaseCommand):
                        if not pair in choices:
                            choices.append(pair)
        except:
            pass
    return choices


class LogAdmin(admin.ModelAdmin):
    list_display = ('job_name', 'run_date', 'job_success', 'output', 'errors', )
    search_fields = ('stdout', 'stderr', 'job__name', 'job__command')
    date_hierarchy = 'run_date'
    fieldsets = (
        (None, {
            'fields': ('job',)
        }),
        ('Output', {
            'fields': ('stdout', 'stderr',)
        }),
    )
    
    def job_name(self, obj):
        return obj.job.name
    job_name.short_description = _(u'Name')

    def job_success(self, obj):
        return obj.success
    job_success.short_description = _(u'OK')
    job_success.boolean = True

    def output(self, obj):
        if obj.stdout is not None and obj.stdout != '':
            Renderer = get_class(obj.job.renderer)
            return Renderer().get_html_message(obj)
        else:
            return '--'
    output.allow_tags = True
    
    def errors(self, obj):
        if obj.stderr is not None:
            Renderer = get_class(obj.job.renderer)
            return Renderer().get_html_status(obj)
        else:
            return '--'
    errors.allow_tags = True
    
    def has_add_permission(self, request):
        return False
    
    def formfield_for_dbfield(self, db_field, **kwargs):
        request = kwargs.pop("request", None)
        
        if isinstance(db_field, models.TextField):
            kwargs['widget'] = HTMLWidget()
            return db_field.formfield(**kwargs)
        
        if isinstance(db_field, models.ForeignKey):
            kwargs['widget'] = HTMLWidget(db_field.rel)
            return db_field.formfield(**kwargs)
        
        return super(LogAdmin, self).formfield_for_dbfield(db_field, **kwargs)

try:
    admin.site.register(Job, JobAdmin)
except admin.sites.AlreadyRegistered:
    pass

admin.site.register(Log, LogAdmin)
#admin.site.register(Log)
admin.site.register(Host)




    
    
    

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -
'''
Created on Mar 5, 2012

@author: Raul Garreta (raul@tryolabs.com)

Defines base kitsune check.
All custom kitsune checks must define a Command class that extends BaseKitsuneCheck.

'''

__author__      = "Raul Garreta (raul@tryolabs.com)"

import sys
import traceback

from django.core.management.base import BaseCommand


# Exit status codes (also recognized by Nagios)
STATUS_OK = 0
STATUS_WARNING = 1
STATUS_CRITICAL = 2
STATUS_UNKNOWN = 3


class BaseKitsuneCheck(BaseCommand):
    
    def check(self):
        self.status_code = STATUS_OK
            
    def handle(self, *args, **options):
        try:
            self.check(*args, **options)
            #standard output to print status message
            print self.status_message,
            #standard error to print status code
            #note comma at the end to avoid printing a \n
            print >> sys.stderr, self.status_code,
        except Exception as e:
            trace = 'Trace: ' + traceback.format_exc()
            print str(e), trace, 'args:', args, 'options:', options
            print >> sys.stderr, STATUS_UNKNOWN,
########NEW FILE########
__FILENAME__ = html2text
#!/usr/bin/env python
"""html2text: Turn HTML into equivalent Markdown-structured text."""
__version__ = "2.39"
__author__ = "Aaron Swartz (me@aaronsw.com)"
__copyright__ = "(C) 2004-2008 Aaron Swartz. GNU GPL 3."
__contributors__ = ["Martin 'Joey' Schulze", "Ricardo Reyes", "Kevin Jay North"]

# TODO:
#   Support decoded entities with unifiable.

if not hasattr(__builtins__, 'True'): True, False = 1, 0
import re, sys, urllib, htmlentitydefs, codecs, StringIO, types
import sgmllib
import urlparse
sgmllib.charref = re.compile('&#([xX]?[0-9a-fA-F]+)[^0-9a-fA-F]')

try: from textwrap import wrap
except: pass

# Use Unicode characters instead of their ascii psuedo-replacements
UNICODE_SNOB = 0

# Put the links after each paragraph instead of at the end.
LINKS_EACH_PARAGRAPH = 0

# Wrap long lines at position. 0 for no wrapping. (Requires Python 2.3.)
BODY_WIDTH = 78

# Don't show internal links (href="#local-anchor") -- corresponding link targets
# won't be visible in the plain text file anyway.
SKIP_INTERNAL_LINKS = False

### Entity Nonsense ###

def name2cp(k):
    if k == 'apos': return ord("'")
    if hasattr(htmlentitydefs, "name2codepoint"): # requires Python 2.3
        return htmlentitydefs.name2codepoint[k]
    else:
        k = htmlentitydefs.entitydefs[k]
        if k.startswith("&#") and k.endswith(";"): return int(k[2:-1]) # not in latin-1
        return ord(codecs.latin_1_decode(k)[0])

unifiable = {'rsquo':"'", 'lsquo':"'", 'rdquo':'"', 'ldquo':'"', 
'copy':'(C)', 'mdash':'--', 'nbsp':' ', 'rarr':'->', 'larr':'<-', 'middot':'*',
'ndash':'-', 'oelig':'oe', 'aelig':'ae',
'agrave':'a', 'aacute':'a', 'acirc':'a', 'atilde':'a', 'auml':'a', 'aring':'a', 
'egrave':'e', 'eacute':'e', 'ecirc':'e', 'euml':'e', 
'igrave':'i', 'iacute':'i', 'icirc':'i', 'iuml':'i',
'ograve':'o', 'oacute':'o', 'ocirc':'o', 'otilde':'o', 'ouml':'o', 
'ugrave':'u', 'uacute':'u', 'ucirc':'u', 'uuml':'u'}

unifiable_n = {}

for k in unifiable.keys():
    unifiable_n[name2cp(k)] = unifiable[k]

def charref(name):
    if name[0] in ['x','X']:
        c = int(name[1:], 16)
    else:
        c = int(name)
    
    if not UNICODE_SNOB and c in unifiable_n.keys():
        return unifiable_n[c]
    else:
        return unichr(c)

def entityref(c):
    if not UNICODE_SNOB and c in unifiable.keys():
        return unifiable[c]
    else:
        try: name2cp(c)
        except KeyError: return "&" + c
        else: return unichr(name2cp(c))

def replaceEntities(s):
    s = s.group(1)
    if s[0] == "#": 
        return charref(s[1:])
    else: return entityref(s)

r_unescape = re.compile(r"&(#?[xX]?(?:[0-9a-fA-F]+|\w{1,8}));")
def unescape(s):
    return r_unescape.sub(replaceEntities, s)
    
def fixattrs(attrs):
    # Fix bug in sgmllib.py
    if not attrs: return attrs
    newattrs = []
    for attr in attrs:
        newattrs.append((attr[0], unescape(attr[1])))
    return newattrs

### End Entity Nonsense ###

def onlywhite(line):
    """Return true if the line does only consist of whitespace characters."""
    for c in line:
        if c is not ' ' and c is not '  ':
            return c is ' '
    return line

def optwrap(text):
    """Wrap all paragraphs in the provided text."""
    if not BODY_WIDTH:
        return text
    
    assert wrap, "Requires Python 2.3."
    result = ''
    newlines = 0
    for para in text.split("\n"):
        if len(para) > 0:
            if para[0] is not ' ' and para[0] is not '-' and para[0] is not '*':
                for line in wrap(para, BODY_WIDTH):
                    result += line + "\n"
                result += "\n"
                newlines = 2
            else:
                if not onlywhite(para):
                    result += para + "\n"
                    newlines = 1
        else:
            if newlines < 2:
                result += "\n"
                newlines += 1
    return result

def hn(tag):
    if tag[0] == 'h' and len(tag) == 2:
        try:
            n = int(tag[1])
            if n in range(1, 10): return n
        except ValueError: return 0

class _html2text(sgmllib.SGMLParser):
    def __init__(self, out=None, baseurl=''):
        sgmllib.SGMLParser.__init__(self)
        
        if out is None: self.out = self.outtextf
        else: self.out = out
        self.outtext = u''
        self.quiet = 0
        self.p_p = 0
        self.outcount = 0
        self.start = 1
        self.space = 0
        self.a = []
        self.astack = []
        self.acount = 0
        self.list = []
        self.blockquote = 0
        self.pre = 0
        self.startpre = 0
        self.lastWasNL = 0
        self.abbr_title = None # current abbreviation definition
        self.abbr_data = None # last inner HTML (for abbr being defined)
        self.abbr_list = {} # stack of abbreviations to write later
        self.baseurl = baseurl
    
    def outtextf(self, s): 
        self.outtext += s
    
    def close(self):
        sgmllib.SGMLParser.close(self)
        
        self.pbr()
        self.o('', 0, 'end')
        
        return self.outtext
        
    def handle_charref(self, c):
        self.o(charref(c))

    def handle_entityref(self, c):
        self.o(entityref(c))
            
    def unknown_starttag(self, tag, attrs):
        self.handle_tag(tag, attrs, 1)
    
    def unknown_endtag(self, tag):
        self.handle_tag(tag, None, 0)
        
    def previousIndex(self, attrs):
        """ returns the index of certain set of attributes (of a link) in the
            self.a list
 
            If the set of attributes is not found, returns None
        """
        if not attrs.has_key('href'): return None
        
        i = -1
        for a in self.a:
            i += 1
            match = 0
            
            if a.has_key('href') and a['href'] == attrs['href']:
                if a.has_key('title') or attrs.has_key('title'):
                        if (a.has_key('title') and attrs.has_key('title') and
                            a['title'] == attrs['title']):
                            match = True
                else:
                    match = True

            if match: return i

    def handle_tag(self, tag, attrs, start):
        attrs = fixattrs(attrs)
    
        if hn(tag):
            self.p()
            if start: self.o(hn(tag)*"#" + ' ')

        if tag in ['p', 'div']: self.p()
        
        if tag == "br" and start: self.o("  \n")

        if tag == "hr" and start:
            self.p()
            self.o("* * *")
            self.p()

        if tag in ["head", "style", 'script']: 
            if start: self.quiet += 1
            else: self.quiet -= 1

        if tag in ["body"]:
            self.quiet = 0 # sites like 9rules.com never close <head>
        
        if tag == "blockquote":
            if start: 
                self.p(); self.o('> ', 0, 1); self.start = 1
                self.blockquote += 1
            else:
                self.blockquote -= 1
                self.p()
        
        if tag in ['em', 'i', 'u']: self.o("_")
        if tag in ['strong', 'b']: self.o("**")
        if tag == "code" and not self.pre: self.o('`') #TODO: `` `this` ``
        if tag == "abbr":
            if start:
                attrsD = {}
                for (x, y) in attrs: attrsD[x] = y
                attrs = attrsD
                
                self.abbr_title = None
                self.abbr_data = ''
                if attrs.has_key('title'):
                    self.abbr_title = attrs['title']
            else:
                if self.abbr_title != None:
                    self.abbr_list[self.abbr_data] = self.abbr_title
                    self.abbr_title = None
                self.abbr_data = ''
        
        if tag == "a":
            if start:
                attrsD = {}
                for (x, y) in attrs: attrsD[x] = y
                attrs = attrsD
                if attrs.has_key('href') and not (SKIP_INTERNAL_LINKS and attrs['href'].startswith('#')): 
                    self.astack.append(attrs)
                    self.o("[")
                else:
                    self.astack.append(None)
            else:
                if self.astack:
                    a = self.astack.pop()
                    if a:
                        i = self.previousIndex(a)
                        if i is not None:
                            a = self.a[i]
                        else:
                            self.acount += 1
                            a['count'] = self.acount
                            a['outcount'] = self.outcount
                            self.a.append(a)
                        self.o("][" + `a['count']` + "]")
        
        if tag == "img" and start:
            attrsD = {}
            for (x, y) in attrs: attrsD[x] = y
            attrs = attrsD
            if attrs.has_key('src'):
                attrs['href'] = attrs['src']
                alt = attrs.get('alt', '')
                i = self.previousIndex(attrs)
                if i is not None:
                    attrs = self.a[i]
                else:
                    self.acount += 1
                    attrs['count'] = self.acount
                    attrs['outcount'] = self.outcount
                    self.a.append(attrs)
                self.o("![")
                self.o(alt)
                self.o("]["+`attrs['count']`+"]")
        
        if tag == 'dl' and start: self.p()
        if tag == 'dt' and not start: self.pbr()
        if tag == 'dd' and start: self.o('    ')
        if tag == 'dd' and not start: self.pbr()
        
        if tag in ["ol", "ul"]:
            if start:
                self.list.append({'name':tag, 'num':0})
            else:
                if self.list: self.list.pop()
            
            self.p()
        
        if tag == 'li':
            if start:
                self.pbr()
                if self.list: li = self.list[-1]
                else: li = {'name':'ul', 'num':0}
                self.o("  "*len(self.list)) #TODO: line up <ol><li>s > 9 correctly.
                if li['name'] == "ul": self.o("* ")
                elif li['name'] == "ol":
                    li['num'] += 1
                    self.o(`li['num']`+". ")
                self.start = 1
            else:
                self.pbr()
        
        if tag in ["table", "tr"] and start: self.p()
        if tag == 'td': self.pbr()
        
        if tag == "pre":
            if start:
                self.startpre = 1
                self.pre = 1
            else:
                self.pre = 0
            self.p()
            
    def pbr(self):
        if self.p_p == 0: self.p_p = 1

    def p(self): self.p_p = 2
    
    def o(self, data, puredata=0, force=0):
        if self.abbr_data is not None: self.abbr_data += data
        
        if not self.quiet: 
            if puredata and not self.pre:
                data = re.sub('\s+', ' ', data)
                if data and data[0] == ' ':
                    self.space = 1
                    data = data[1:]
            if not data and not force: return
            
            if self.startpre:
                #self.out(" :") #TODO: not output when already one there
                self.startpre = 0
            
            bq = (">" * self.blockquote)
            if not (force and data and data[0] == ">") and self.blockquote: bq += " "
            
            if self.pre:
                bq += "    "
                data = data.replace("\n", "\n"+bq)
            
            if self.start:
                self.space = 0
                self.p_p = 0
                self.start = 0

            if force == 'end':
                # It's the end.
                self.p_p = 0
                self.out("\n")
                self.space = 0


            if self.p_p:
                self.out(('\n'+bq)*self.p_p)
                self.space = 0
                
            if self.space:
                if not self.lastWasNL: self.out(' ')
                self.space = 0

            if self.a and ((self.p_p == 2 and LINKS_EACH_PARAGRAPH) or force == "end"):
                if force == "end": self.out("\n")

                newa = []
                for link in self.a:
                    if self.outcount > link['outcount']:
                        self.out("   ["+`link['count']`+"]: " + urlparse.urljoin(self.baseurl, link['href'])) 
                        if link.has_key('title'): self.out(" ("+link['title']+")")
                        self.out("\n")
                    else:
                        newa.append(link)

                if self.a != newa: self.out("\n") # Don't need an extra line when nothing was done.

                self.a = newa
            
            if self.abbr_list and force == "end":
                for abbr, definition in self.abbr_list.items():
                    self.out("  *[" + abbr + "]: " + definition + "\n")

            self.p_p = 0
            self.out(data)
            self.lastWasNL = data and data[-1] == '\n'
            self.outcount += 1

    def handle_data(self, data):
        if r'\/script>' in data: self.quiet -= 1
        self.o(data, 1)
    
    def unknown_decl(self, data): pass

def wrapwrite(text): sys.stdout.write(text.encode('utf8'))

def html2text_file(html, out=wrapwrite, baseurl=''):
    h = _html2text(out, baseurl)
    h.feed(html)
    h.feed("")
    return h.close()

def html2text(html, baseurl=''):
    return optwrap(html2text_file(html, None, baseurl))

if __name__ == "__main__":
    baseurl = ''
    if sys.argv[1:]:
        arg = sys.argv[1]
        if arg.startswith('http://') or arg.startswith('https://'):
            baseurl = arg
            j = urllib.urlopen(baseurl)
            try:
                from feedparser import _getCharacterEncoding as enc
            except ImportError:
                   enc = lambda x, y: ('utf-8', 1)
            text = j.read()
            encoding = enc(j.headers, text)[0]
            if encoding == 'us-ascii': encoding = 'utf-8'
            data = text.decode(encoding)

        else:
            encoding = 'utf8'
            if len(sys.argv) > 2:
                encoding = sys.argv[2]
            data = open(arg, 'r').read().decode(encoding)
    else:
        data = sys.stdin.read().decode('utf8')
    wrapwrite(html2text(data, baseurl))


########NEW FILE########
__FILENAME__ = mail
from django.core.mail import send_mail as django_send_mail
from django.core.mail import EmailMultiAlternatives
from datetime import datetime as dt
from time import sleep
import threading
 
def send_mail(subject, message, from_email, recipient_list,fail_silently=False, auth_user=None, auth_password=None):
    class Sender(threading.Thread):
        def run(self):
            django_send_mail(subject, message, from_email,recipient_list, fail_silently, auth_user, auth_password)
    s=Sender()
    s.start()
    return True

def send_multi_mail(subject, text_content, html_content, from_email, recipient_list, fail_silently=False):
    class Sender(threading.Thread):
        def run(self):
            msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
            msg.attach_alternative(html_content, "text/html")
            msg.send()
    s=Sender()
    s.start()
    
        
        
        
########NEW FILE########
__FILENAME__ = kitsune_cron
# -*- coding: utf-8 -
'''
Created on Mar 3, 2012

@author: Raul Garreta (raul@tryolabs.com)

Management command called by cron.
Calls run for all jobs.

Based on django-chronograph.

'''

__author__      = "Raul Garreta (raul@tryolabs.com)"


from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Runs all jobs that are due.'
    
    def handle(self, *args, **options):
        from kitsune.models import Job
        procs = []
        for job in Job.objects.all():
            p = job.run(False)
            if p is not None:
                procs.append(p)
        for p in procs:
            p.wait()
########NEW FILE########
__FILENAME__ = kitsune_cronserver
from django.core.management.base import BaseCommand
from kitsune.models import Job

import sys

from time import sleep

help_text = '''
Emulates a reoccurring cron call to run jobs at a specified interval.
This is meant primarily for development use.
'''

class Command(BaseCommand):
    help = help_text
    args = "time"
    
    def handle( self, *args, **options ):
        from django.core.management import call_command
        try:
            t_wait = int(args[0])
        except:
            t_wait = 60
        try:
            print "Starting cronserver.  Jobs will run every %d seconds." % t_wait
            print "Quit the server with CONTROL-C."
            
            # Run server untill killed
            while True:
                for job in Job.objects.all():
                    p = job.run(False)
                    if p is not None:
                        print "Running: %s" % job
                sleep(t_wait)
        except KeyboardInterrupt:
            print "Exiting..."
            sys.exit()
########NEW FILE########
__FILENAME__ = kitsune_cron_clean
from django.core.management.base import BaseCommand
import sys

class Command( BaseCommand ):
    help = 'Deletes old job logs.'
    
    def handle( self, *args, **options ):
        from kitsune.models import Log
        from datetime import datetime, timedelta
                
        if len( args ) != 2:
            sys.stderr.write('Command requires two arguments. Unit (weeks, days, hours or minutes) and interval.\n')
            return
        else:
            unit = str( args[ 0 ] )
            if unit not in [ 'weeks', 'days', 'hours', 'minutes' ]:
                sys.stderr.write('Valid units are weeks, days, hours or minutes.\n')
                return
            try:
                amount = int( args[ 1 ] ) 
            except ValueError:
                sys.stderr.write('Interval must be an integer.\n')
                return
        kwargs = { unit: amount }
        time_ago = datetime.now() - timedelta( **kwargs )
        Log.objects.filter( run_date__lte = time_ago ).delete()
########NEW FILE########
__FILENAME__ = kitsune_nagios_check
# -*- coding: utf-8 -
'''
Created on Mar 5, 2012

@author: Raul Garreta (raul@tryolabs.com)

Kitsune check that wrapps any Nagios check.
All necessary parameters must be passed through args field at admin interface.
A special option: "check" must be passed with the name of the Nagios check to run.
eg:
check=check_disk -u=GB -w=5 -c=2 -p=/

'''

__author__      = "Raul Garreta (raul@tryolabs.com)"


from kitsune.base import BaseKitsuneCheck
from kitsune.nagios import NagiosPoller
from kitsune.monitor import ArgSet


class Command(BaseKitsuneCheck):
    help = 'A Nagios check.'
    
    
    def check(self, *args, **options):
        poller = NagiosPoller()
        nagios_args = ArgSet()
        check = options['check']
        del options['check']
        del options['verbosity']
        
        new_args = []
        for arg in args:
            if arg != 'verbosity':
                new_args.append(arg)
        args = new_args
                
        for arg in args:
            nagios_args.add_argument(arg)
        for option in options:
            nagios_args.add_argument_pair(str(option), str(options[option]))
        res = poller.run_plugin(check, nagios_args)
        
        self.status_code = res.returncode
        self.status_message = " NAGIOS_OUT:  " + res.output + "<br>NAGIOS_ERR:  " + res.error
            
        
        

########NEW FILE########
__FILENAME__ = kitsune_run_job
import sys

from django.core.management import call_command
from django.core.management.base import BaseCommand

from kitsune.models import Job, Log

class Command(BaseCommand):
    help = 'Runs a specific job. The job will only run if it is not currently running.'
    args = "job.id"
    
    def handle(self, *args, **options):
        try:
            job_id = args[0]
        except IndexError:
            sys.stderr.write("This command requires a single argument: a job id to run.\n")
            return

        try:
            job = Job.objects.get(pk=job_id)
        except Job.DoesNotExist:
            sys.stderr.write("The requested Job does not exist.\n")
            return
        
        # Run the job and wait for it to finish
        job.handle_run()
        
########NEW FILE########
__FILENAME__ = kitsune_test_check
# -*- coding: utf-8 -
'''
Created on Mar 3, 2012

@author: Raul Garreta (raul@tryolabs.com)

Dummy check to test functionality.

'''

__author__      = "Raul Garreta (raul@tryolabs.com)"


from kitsune.renderers import STATUS_OK, STATUS_WARNING, STATUS_CRITICAL, STATUS_UNKNOWN
from kitsune.base import BaseKitsuneCheck


class Command(BaseKitsuneCheck):
    help = 'A simple test check.'
    
    
    def check(self, *args, **options):
        self.status_code = STATUS_OK
        
        if self.status_code == STATUS_OK:
            self.status_message = 'OK message'
        elif self.status_code == STATUS_WARNING:
            self.status_message = 'WARNING message'
        elif self.status_code == STATUS_CRITICAL:
            self.status_message = 'CRITICAL message'
        else:
            self.status_message = 'UNKNOWN message'
            

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Job'
        db.create_table('kitsune_job', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('frequency', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('params', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('command', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('args', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('disabled', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('next_run', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('last_run', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_running', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('last_run_successful', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('pid', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('force_run', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('host_name', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal('kitsune', ['Job'])

        # Adding M2M table for field subscribers on 'Job'
        db.create_table('kitsune_job_subscribers', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('job', models.ForeignKey(orm['kitsune.job'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('kitsune_job_subscribers', ['job_id', 'user_id'])

        # Adding model 'Log'
        db.create_table('kitsune_log', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('job', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['kitsune.Job'])),
            ('run_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('stdout', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('stderr', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('success', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('kitsune', ['Log'])


    def backwards(self, orm):
        
        # Deleting model 'Job'
        db.delete_table('kitsune_job')

        # Removing M2M table for field subscribers on 'Job'
        db.delete_table('kitsune_job_subscribers')

        # Deleting model 'Log'
        db.delete_table('kitsune_log')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'kitsune.job': {
            'Meta': {'ordering': "('disabled', 'next_run')", 'object_name': 'Job'},
            'args': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'command': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'force_run': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'host_name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_run_successful': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'next_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'kitsune_jobs'", 'blank': 'True', 'to': "orm['auth.User']"})
        },
        'kitsune.log': {
            'Meta': {'ordering': "('-run_date',)", 'object_name': 'Log'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kitsune.Job']"}),
            'run_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'stderr': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'stdout': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['kitsune']

########NEW FILE########
__FILENAME__ = 0002_auto__add_host
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Host'
        db.create_table('kitsune_host', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('ip', self.gf('django.db.models.fields.CharField')(max_length=15, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('kitsune', ['Host'])


    def backwards(self, orm):
        
        # Deleting model 'Host'
        db.delete_table('kitsune_host')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'kitsune.host': {
            'Meta': {'object_name': 'Host'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        'kitsune.job': {
            'Meta': {'ordering': "('disabled', 'next_run')", 'object_name': 'Job'},
            'args': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'command': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'force_run': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'host_name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_run_successful': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'next_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'kitsune_jobs'", 'blank': 'True', 'to': "orm['auth.User']"})
        },
        'kitsune.log': {
            'Meta': {'ordering': "('-run_date',)", 'object_name': 'Log'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kitsune.Job']"}),
            'run_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'stderr': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'stdout': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['kitsune']

########NEW FILE########
__FILENAME__ = 0003_auto__del_field_job_host_name
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Job.host_name'
        db.delete_column('kitsune_job', 'host_name')


    def backwards(self, orm):
        
        # Adding field 'Job.host_name'
        db.add_column('kitsune_job', 'host_name', self.gf('django.db.models.fields.CharField')(default=1, max_length=128), keep_default=False)


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'kitsune.host': {
            'Meta': {'object_name': 'Host'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        'kitsune.job': {
            'Meta': {'ordering': "('disabled', 'next_run')", 'object_name': 'Job'},
            'args': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'command': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'force_run': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_run_successful': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'next_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'kitsune_jobs'", 'blank': 'True', 'to': "orm['auth.User']"})
        },
        'kitsune.log': {
            'Meta': {'ordering': "('-run_date',)", 'object_name': 'Log'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kitsune.Job']"}),
            'run_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'stderr': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'stdout': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['kitsune']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_job_host
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Job.host'
        db.add_column('kitsune_job', 'host', self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['kitsune.Host']), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Job.host'
        db.delete_column('kitsune_job', 'host_id')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'kitsune.host': {
            'Meta': {'object_name': 'Host'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        'kitsune.job': {
            'Meta': {'ordering': "('disabled', 'next_run')", 'object_name': 'Job'},
            'args': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'command': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'force_run': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kitsune.Host']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_run_successful': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'next_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'kitsune_jobs'", 'blank': 'True', 'to': "orm['auth.User']"})
        },
        'kitsune.log': {
            'Meta': {'ordering': "('-run_date',)", 'object_name': 'Log'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kitsune.Job']"}),
            'run_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'stderr': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'stdout': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['kitsune']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_job_last_result
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Job.last_result'
        db.add_column('kitsune_job', 'last_result', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='running_job', null=True, to=orm['kitsune.Log']), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Job.last_result'
        db.delete_column('kitsune_job', 'last_result_id')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'kitsune.host': {
            'Meta': {'object_name': 'Host'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        'kitsune.job': {
            'Meta': {'ordering': "('disabled', 'next_run')", 'object_name': 'Job'},
            'args': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'command': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'force_run': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kitsune.Host']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_result': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'running_job'", 'null': 'True', 'to': "orm['kitsune.Log']"}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_run_successful': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'next_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'kitsune_jobs'", 'blank': 'True', 'to': "orm['auth.User']"})
        },
        'kitsune.log': {
            'Meta': {'ordering': "('-run_date',)", 'object_name': 'Log'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['kitsune.Job']"}),
            'run_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'stderr': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'stdout': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['kitsune']

########NEW FILE########
__FILENAME__ = 0006_auto__add_field_job_renderer
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Job.renderer'
        db.add_column('kitsune_job', 'renderer', self.gf('django.db.models.fields.CharField')(default='kitsune.models.JobRenderer', max_length=100), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Job.renderer'
        db.delete_column('kitsune_job', 'renderer')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'kitsune.host': {
            'Meta': {'object_name': 'Host'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        'kitsune.job': {
            'Meta': {'ordering': "('disabled', 'next_run')", 'object_name': 'Job'},
            'args': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'command': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'force_run': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kitsune.Host']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_result': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'running_job'", 'null': 'True', 'to': "orm['kitsune.Log']"}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_run_successful': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'next_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'renderer': ('django.db.models.fields.CharField', [], {'default': "'kitsune.models.JobRenderer'", 'max_length': '100'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'kitsune_jobs'", 'blank': 'True', 'to': "orm['auth.User']"})
        },
        'kitsune.log': {
            'Meta': {'ordering': "('-run_date',)", 'object_name': 'Log'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['kitsune.Job']"}),
            'run_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'stderr': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'stdout': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['kitsune']

########NEW FILE########
__FILENAME__ = 0007_auto__add_field_job_log_clean_freq_unit__add_field_job_log_clean_freq_
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Job.log_clean_freq_unit'
        db.add_column('kitsune_job', 'log_clean_freq_unit', self.gf('django.db.models.fields.CharField')(default='Hours', max_length=10), keep_default=False)

        # Adding field 'Job.log_clean_freq_value'
        db.add_column('kitsune_job', 'log_clean_freq_value', self.gf('django.db.models.fields.PositiveIntegerField')(default=1), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Job.log_clean_freq_unit'
        db.delete_column('kitsune_job', 'log_clean_freq_unit')

        # Deleting field 'Job.log_clean_freq_value'
        db.delete_column('kitsune_job', 'log_clean_freq_value')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'kitsune.host': {
            'Meta': {'object_name': 'Host'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        'kitsune.job': {
            'Meta': {'ordering': "('disabled', 'next_run')", 'object_name': 'Job'},
            'args': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'command': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'force_run': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kitsune.Host']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_result': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'running_job'", 'null': 'True', 'to': "orm['kitsune.Log']"}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_run_successful': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'log_clean_freq_unit': ('django.db.models.fields.CharField', [], {'default': "'Hours'", 'max_length': '10'}),
            'log_clean_freq_value': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'next_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'renderer': ('django.db.models.fields.CharField', [], {'default': "'kitsune.models.KitsuneJobRenderer'", 'max_length': '100'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'kitsune_jobs'", 'blank': 'True', 'to': "orm['auth.User']"})
        },
        'kitsune.log': {
            'Meta': {'ordering': "('-run_date',)", 'object_name': 'Log'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['kitsune.Job']"}),
            'run_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'stderr': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'stdout': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['kitsune']

########NEW FILE########
__FILENAME__ = 0008_auto__del_field_job_log_clean_freq_value__del_field_job_log_clean_freq
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Job.log_clean_freq_value'
        db.delete_column('kitsune_job', 'log_clean_freq_value')

        # Deleting field 'Job.log_clean_freq_unit'
        db.delete_column('kitsune_job', 'log_clean_freq_unit')

        # Adding field 'Job.last_logs_to_keep'
        db.add_column('kitsune_job', 'last_logs_to_keep', self.gf('django.db.models.fields.PositiveIntegerField')(default=20), keep_default=False)


    def backwards(self, orm):
        
        # Adding field 'Job.log_clean_freq_value'
        db.add_column('kitsune_job', 'log_clean_freq_value', self.gf('django.db.models.fields.PositiveIntegerField')(default=1), keep_default=False)

        # Adding field 'Job.log_clean_freq_unit'
        db.add_column('kitsune_job', 'log_clean_freq_unit', self.gf('django.db.models.fields.CharField')(default='Hours', max_length=10), keep_default=False)

        # Deleting field 'Job.last_logs_to_keep'
        db.delete_column('kitsune_job', 'last_logs_to_keep')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'kitsune.host': {
            'Meta': {'object_name': 'Host'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        'kitsune.job': {
            'Meta': {'ordering': "('disabled', 'next_run')", 'object_name': 'Job'},
            'args': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'command': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'force_run': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kitsune.Host']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_logs_to_keep': ('django.db.models.fields.PositiveIntegerField', [], {'default': '20'}),
            'last_result': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'running_job'", 'null': 'True', 'to': "orm['kitsune.Log']"}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_run_successful': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'next_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'renderer': ('django.db.models.fields.CharField', [], {'default': "'kitsune.models.KitsuneJobRenderer'", 'max_length': '100'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'kitsune_jobs'", 'blank': 'True', 'to': "orm['auth.User']"})
        },
        'kitsune.log': {
            'Meta': {'ordering': "('-run_date',)", 'object_name': 'Log'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['kitsune.Job']"}),
            'run_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'stderr': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'stdout': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['kitsune']

########NEW FILE########
__FILENAME__ = 0009_auto__add_notificationrule
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'NotificationRule'
        db.create_table('kitsune_notificationrule', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('job', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['kitsune.Job'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('last_notification', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('threshold', self.gf('django.db.models.fields.IntegerField')(max_length=10)),
            ('rule_type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('rule_N', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('rule_M', self.gf('django.db.models.fields.PositiveIntegerField')(default=2)),
            ('frequency_unit', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('frequency_value', self.gf('django.db.models.fields.PositiveIntegerField')(max_length=10)),
        ))
        db.send_create_signal('kitsune', ['NotificationRule'])

        # Removing M2M table for field subscribers on 'Job'
        db.delete_table('kitsune_job_subscribers')


    def backwards(self, orm):
        
        # Deleting model 'NotificationRule'
        db.delete_table('kitsune_notificationrule')

        # Adding M2M table for field subscribers on 'Job'
        db.create_table('kitsune_job_subscribers', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('job', models.ForeignKey(orm['kitsune.job'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('kitsune_job_subscribers', ['job_id', 'user_id'])


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'kitsune.host': {
            'Meta': {'object_name': 'Host'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        'kitsune.job': {
            'Meta': {'ordering': "('disabled', 'next_run')", 'object_name': 'Job'},
            'args': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'command': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'force_run': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kitsune.Host']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_logs_to_keep': ('django.db.models.fields.PositiveIntegerField', [], {'default': '20'}),
            'last_result': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'running_job'", 'null': 'True', 'to': "orm['kitsune.Log']"}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_run_successful': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'next_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'renderer': ('django.db.models.fields.CharField', [], {'default': "'kitsune.models.KitsuneJobRenderer'", 'max_length': '100'}),
            'subscribers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'kitsune_jobs'", 'blank': 'True', 'through': "orm['kitsune.NotificationRule']", 'to': "orm['auth.User']"})
        },
        'kitsune.log': {
            'Meta': {'ordering': "('-run_date',)", 'object_name': 'Log'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['kitsune.Job']"}),
            'run_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'stderr': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'stdout': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'kitsune.notificationrule': {
            'Meta': {'object_name': 'NotificationRule'},
            'frequency_unit': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'frequency_value': ('django.db.models.fields.PositiveIntegerField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kitsune.Job']"}),
            'last_notification': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'rule_M': ('django.db.models.fields.PositiveIntegerField', [], {'default': '2'}),
            'rule_N': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'rule_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'threshold': ('django.db.models.fields.IntegerField', [], {'max_length': '10'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['kitsune']

########NEW FILE########
__FILENAME__ = 0010_auto__chg_field_notificationrule_frequency_value
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'NotificationRule.frequency_value'
        db.alter_column('kitsune_notificationrule', 'frequency_value', self.gf('django.db.models.fields.PositiveIntegerField')())


    def backwards(self, orm):
        
        # Changing field 'NotificationRule.frequency_value'
        db.alter_column('kitsune_notificationrule', 'frequency_value', self.gf('django.db.models.fields.PositiveIntegerField')(max_length=10))


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'kitsune.host': {
            'Meta': {'object_name': 'Host'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        'kitsune.job': {
            'Meta': {'ordering': "('disabled', 'next_run')", 'object_name': 'Job'},
            'args': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'command': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'force_run': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kitsune.Host']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_logs_to_keep': ('django.db.models.fields.PositiveIntegerField', [], {'default': '20'}),
            'last_result': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'running_job'", 'null': 'True', 'to': "orm['kitsune.Log']"}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_run_successful': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'next_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'renderer': ('django.db.models.fields.CharField', [], {'default': "'kitsune.models.KitsuneJobRenderer'", 'max_length': '100'})
        },
        'kitsune.log': {
            'Meta': {'ordering': "('-run_date',)", 'object_name': 'Log'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['kitsune.Job']"}),
            'run_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'stderr': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'stdout': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'kitsune.notificationrule': {
            'Meta': {'object_name': 'NotificationRule'},
            'frequency_unit': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'frequency_value': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'subscribers'", 'to': "orm['kitsune.Job']"}),
            'last_notification': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'rule_M': ('django.db.models.fields.PositiveIntegerField', [], {'default': '2'}),
            'rule_N': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'rule_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'threshold': ('django.db.models.fields.IntegerField', [], {'max_length': '10'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['kitsune']

########NEW FILE########
__FILENAME__ = 0011_auto__add_field_notificationrule_enabled
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'NotificationRule.enabled'
        db.add_column('kitsune_notificationrule', 'enabled', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'NotificationRule.enabled'
        db.delete_column('kitsune_notificationrule', 'enabled')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'kitsune.host': {
            'Meta': {'object_name': 'Host'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        'kitsune.job': {
            'Meta': {'ordering': "('disabled', 'next_run')", 'object_name': 'Job'},
            'args': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'command': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'force_run': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kitsune.Host']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_logs_to_keep': ('django.db.models.fields.PositiveIntegerField', [], {'default': '20'}),
            'last_result': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'running_job'", 'null': 'True', 'to': "orm['kitsune.Log']"}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_run_successful': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'next_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'renderer': ('django.db.models.fields.CharField', [], {'default': "'kitsune.models.KitsuneJobRenderer'", 'max_length': '100'})
        },
        'kitsune.log': {
            'Meta': {'ordering': "('-run_date',)", 'object_name': 'Log'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['kitsune.Job']"}),
            'run_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'stderr': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'stdout': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'kitsune.notificationrule': {
            'Meta': {'object_name': 'NotificationRule'},
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'frequency_unit': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'frequency_value': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'subscribers'", 'to': "orm['kitsune.Job']"}),
            'last_notification': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'rule_M': ('django.db.models.fields.PositiveIntegerField', [], {'default': '2'}),
            'rule_N': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'rule_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'threshold': ('django.db.models.fields.IntegerField', [], {'max_length': '10'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['kitsune']

########NEW FILE########
__FILENAME__ = 0012_auto__del_field_notificationrule_frequency_unit__del_field_notificatio
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'NotificationRule.frequency_unit'
        db.delete_column('kitsune_notificationrule', 'frequency_unit')

        # Deleting field 'NotificationRule.frequency_value'
        db.delete_column('kitsune_notificationrule', 'frequency_value')

        # Adding field 'NotificationRule.interval_unit'
        db.add_column('kitsune_notificationrule', 'interval_unit', self.gf('django.db.models.fields.CharField')(default='Hours', max_length=10), keep_default=False)

        # Adding field 'NotificationRule.interval_value'
        db.add_column('kitsune_notificationrule', 'interval_value', self.gf('django.db.models.fields.PositiveIntegerField')(default=1), keep_default=False)


    def backwards(self, orm):
        
        # Adding field 'NotificationRule.frequency_unit'
        db.add_column('kitsune_notificationrule', 'frequency_unit', self.gf('django.db.models.fields.CharField')(default=1, max_length=10), keep_default=False)

        # Adding field 'NotificationRule.frequency_value'
        db.add_column('kitsune_notificationrule', 'frequency_value', self.gf('django.db.models.fields.PositiveIntegerField')(default=1), keep_default=False)

        # Deleting field 'NotificationRule.interval_unit'
        db.delete_column('kitsune_notificationrule', 'interval_unit')

        # Deleting field 'NotificationRule.interval_value'
        db.delete_column('kitsune_notificationrule', 'interval_value')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'kitsune.host': {
            'Meta': {'object_name': 'Host'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        'kitsune.job': {
            'Meta': {'ordering': "('disabled', 'next_run')", 'object_name': 'Job'},
            'args': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'command': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'force_run': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kitsune.Host']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_logs_to_keep': ('django.db.models.fields.PositiveIntegerField', [], {'default': '20'}),
            'last_result': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'running_job'", 'null': 'True', 'to': "orm['kitsune.Log']"}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_run_successful': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'next_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'renderer': ('django.db.models.fields.CharField', [], {'default': "'kitsune.models.KitsuneJobRenderer'", 'max_length': '100'})
        },
        'kitsune.log': {
            'Meta': {'ordering': "('-run_date',)", 'object_name': 'Log'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['kitsune.Job']"}),
            'run_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'stderr': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'stdout': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'kitsune.notificationrule': {
            'Meta': {'object_name': 'NotificationRule'},
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interval_unit': ('django.db.models.fields.CharField', [], {'default': "'Hours'", 'max_length': '10'}),
            'interval_value': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'subscribers'", 'to': "orm['kitsune.Job']"}),
            'last_notification': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'rule_M': ('django.db.models.fields.PositiveIntegerField', [], {'default': '2'}),
            'rule_N': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'rule_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'threshold': ('django.db.models.fields.IntegerField', [], {'max_length': '10'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['kitsune']

########NEW FILE########
__FILENAME__ = 0013_auto__del_notificationrule__add_notificationgroup__add_notificationuse
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'NotificationRule'
        db.delete_table('kitsune_notificationrule')

        # Adding model 'NotificationGroup'
        db.create_table('kitsune_notificationgroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('last_notification', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('threshold', self.gf('django.db.models.fields.IntegerField')(max_length=10)),
            ('rule_type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('rule_N', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('rule_M', self.gf('django.db.models.fields.PositiveIntegerField')(default=2)),
            ('interval_unit', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('interval_value', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('job', self.gf('django.db.models.fields.related.ForeignKey')(related_name='subscriber_groups', to=orm['kitsune.Job'])),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.Group'])),
        ))
        db.send_create_signal('kitsune', ['NotificationGroup'])

        # Adding model 'NotificationUser'
        db.create_table('kitsune_notificationuser', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('last_notification', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('threshold', self.gf('django.db.models.fields.IntegerField')(max_length=10)),
            ('rule_type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('rule_N', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('rule_M', self.gf('django.db.models.fields.PositiveIntegerField')(default=2)),
            ('interval_unit', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('interval_value', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('job', self.gf('django.db.models.fields.related.ForeignKey')(related_name='subscriber_users', to=orm['kitsune.Job'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('kitsune', ['NotificationUser'])


    def backwards(self, orm):
        
        # Adding model 'NotificationRule'
        db.create_table('kitsune_notificationrule', (
            ('interval_unit', self.gf('django.db.models.fields.CharField')(default='Hours', max_length=10)),
            ('job', self.gf('django.db.models.fields.related.ForeignKey')(related_name='subscribers', to=orm['kitsune.Job'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('threshold', self.gf('django.db.models.fields.IntegerField')(max_length=10)),
            ('last_notification', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('rule_type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('interval_value', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('rule_M', self.gf('django.db.models.fields.PositiveIntegerField')(default=2)),
            ('rule_N', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('kitsune', ['NotificationRule'])

        # Deleting model 'NotificationGroup'
        db.delete_table('kitsune_notificationgroup')

        # Deleting model 'NotificationUser'
        db.delete_table('kitsune_notificationuser')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'kitsune.host': {
            'Meta': {'object_name': 'Host'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        'kitsune.job': {
            'Meta': {'ordering': "('disabled', 'next_run')", 'object_name': 'Job'},
            'args': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'command': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'force_run': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['kitsune.Host']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_running': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_logs_to_keep': ('django.db.models.fields.PositiveIntegerField', [], {'default': '20'}),
            'last_result': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'running_job'", 'null': 'True', 'to': "orm['kitsune.Log']"}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_run_successful': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'next_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'pid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'renderer': ('django.db.models.fields.CharField', [], {'default': "'kitsune.models.KitsuneJobRenderer'", 'max_length': '100'})
        },
        'kitsune.log': {
            'Meta': {'ordering': "('-run_date',)", 'object_name': 'Log'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'logs'", 'to': "orm['kitsune.Job']"}),
            'run_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'stderr': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'stdout': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'kitsune.notificationgroup': {
            'Meta': {'object_name': 'NotificationGroup'},
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interval_unit': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'interval_value': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'subscriber_groups'", 'to': "orm['kitsune.Job']"}),
            'last_notification': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'rule_M': ('django.db.models.fields.PositiveIntegerField', [], {'default': '2'}),
            'rule_N': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'rule_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'threshold': ('django.db.models.fields.IntegerField', [], {'max_length': '10'})
        },
        'kitsune.notificationuser': {
            'Meta': {'object_name': 'NotificationUser'},
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interval_unit': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'interval_value': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'subscriber_users'", 'to': "orm['kitsune.Job']"}),
            'last_notification': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'rule_M': ('django.db.models.fields.PositiveIntegerField', [], {'default': '2'}),
            'rule_N': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'rule_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'threshold': ('django.db.models.fields.IntegerField', [], {'max_length': '10'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['kitsune']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -
'''
Created on Mar 3, 2012

@author: Raul Garreta (raul@tryolabs.com)

Kitsune models.
Based on django-chronograph.

'''

__author__ = "Raul Garreta (raul@tryolabs.com)"


import os
import re
import subprocess
import sys
import traceback
import inspect
from socket import gethostname
from dateutil import rrule
from StringIO import StringIO
from datetime import datetime, timedelta

from django.contrib.auth.models import User, Group
from django.conf import settings
from django.core.management import call_command
from django.db import models
from django.template import loader, Context
from django.utils.timesince import timeuntil
from django.utils.translation import ungettext, ugettext, ugettext_lazy as _
from django.utils.encoding import smart_str
from django.core import urlresolvers
from django.template.loader import render_to_string

from kitsune.utils import get_manage_py
from kitsune.renderers import KitsuneJobRenderer
from kitsune.base import (
    STATUS_OK, STATUS_WARNING, STATUS_CRITICAL, STATUS_UNKNOWN
)
from kitsune.mail import send_multi_mail
from kitsune.html2text import html2text


RRULE_WEEKDAY_DICT = {
    "MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6
}

THRESHOLD_CHOICES = (

    (STATUS_OK, 'Status OK'),
    (STATUS_WARNING, 'Status Warning'),
    (STATUS_CRITICAL, 'Status Critical'),
    (STATUS_UNKNOWN, 'Status Unknown'),

)

RULE_LAST = 'lt'
RULE_LAST_N = 'n_lt'
RULE_LAST_N_M = 'n_m_lt'

REPETITION_CHOICES = (

    (RULE_LAST, 'Last Time'),
    (RULE_LAST_N, 'N last times'),
    (RULE_LAST_N_M, 'M of N last times'),

)


class JobManager(models.Manager):
    def due(self):
        """
        Returns a ``QuerySet`` of all jobs waiting to be run.
        """
        return self.filter(
            next_run__lte=datetime.now(),
            disabled=False,
            is_running=False
        )

# A lot of rrule stuff is from django-schedule
freqs = (
    ("YEARLY", _("Yearly")),
    ("MONTHLY", _("Monthly")),
    ("WEEKLY", _("Weekly")),
    ("DAILY", _("Daily")),
    ("HOURLY", _("Hourly")),
    ("MINUTELY", _("Minutely")),
    ("SECONDLY", _("Secondly"))
)


NOTIF_INTERVAL_CHOICES = (
    ("Hours", _("Hours")),
    ("Minutes", _("Minutes")),
)


def get_render_choices():
    choices = []
    try:
        for kls in settings.KITSUNE_RENDERERS:
            __import__(kls)
            m = sys.modules[kls]
            for name, obj in inspect.getmembers(m):
                if inspect.isclass(obj) and issubclass(obj, KitsuneJobRenderer):
                    class_name = kls + '.' + name
                    if name != "KitsuneJobRenderer" and class_name not in choices:
                        choices.append((class_name, class_name))
    except:
        pass
    choices.append((
        "kitsune.models.KitsuneJobRenderer",
        "kitsune.models.KitsuneJobRenderer"
    ))
    return choices


class Job(models.Model):
    """
    A recurring ``django-admin`` command to be run.
    """
    name = models.CharField(_("name"), max_length=200)
    frequency = models.CharField(_("frequency"), choices=freqs, max_length=10)
    params = models.TextField(_("params"), null=True, blank=True,
        help_text=_('Comma-separated list of <a href="http://labix.org/python-dateutil" target="_blank">rrule parameters</a>. e.g: interval:15'))
    command = models.CharField(_("command"), max_length=200,
        help_text=_("A valid django-admin command to run."), blank=True)
    args = models.CharField(_("args"), max_length=200, blank=True,
        help_text=_("Space separated list; e.g: arg1 option1=True"))
    disabled = models.BooleanField(default=False, help_text=_('If checked this job will never run.'))
    next_run = models.DateTimeField(_("next run"), blank=True, null=True, help_text=_("If you don't set this it will be determined automatically"))
    last_run = models.DateTimeField(_("last run"), editable=False, blank=True, null=True)
    is_running = models.BooleanField(default=False, editable=False)
    last_run_successful = models.BooleanField(default=True, blank=False, null=False, editable=False)

    pid = models.IntegerField(blank=True, null=True, editable=False)
    force_run = models.BooleanField(default=False)
    host = models.ForeignKey('Host')
    last_result = models.ForeignKey('Log', related_name='running_job', null=True, blank=True)
    renderer = models.CharField(choices=get_render_choices(), max_length=100, default="kitsune.models.KitsuneJobRenderer")
    last_logs_to_keep = models.PositiveIntegerField(default=20)

    objects = JobManager()

    class Meta:
        ordering = ('disabled', 'next_run',)

    def __unicode__(self):
        if self.disabled:
            return _(u"%(name)s - disabled") % {'name': self.name}
        return u"%s - %s" % (self.name, self.timeuntil)

    def save(self, force_insert=False, force_update=False):
        if not self.disabled:
            if self.pk:
                j = Job.objects.get(pk=self.pk)
            else:
                j = self
            if not self.next_run or j.params != self.params:
                self.next_run = self.rrule.after(datetime.now())
        else:
            self.next_run = None

        super(Job, self).save(force_insert, force_update)

    def get_timeuntil(self):
        """
        Returns a string representing the time until the next
        time this Job will be run.
        """
        if self.disabled:
            return _('never (disabled)')

        delta = self.next_run - datetime.now()
        if delta.days < 0:
            # The job is past due and should be run as soon as possible
            return _('due')
        elif delta.seconds < 60:
            # Adapted from django.utils.timesince
            count = lambda n: ungettext('second', 'seconds', n)
            return ugettext('%(number)d %(type)s') % {'number': delta.seconds,
                                                      'type': count(delta.seconds)}
        return timeuntil(self.next_run)
    get_timeuntil.short_description = _('time until next run')
    timeuntil = property(get_timeuntil)

    def get_rrule(self):
        """
        Returns the rrule objects for this Job.
        """
        frequency = eval('rrule.%s' % self.frequency)
        return rrule.rrule(
            frequency, dtstart=self.last_run, **self.get_params()
        )
    rrule = property(get_rrule)

    def param_to_int(self, param_value):
        """
        Converts a valid rrule parameter to an integer if it is not already
        one, else raises a ``ValueError``.  The following are equivalent:

            >>> job = Job(params = "byweekday:1,2,4,5")
            >>> job = Job(params = "byweekday:TU,WE,FR,SA")
        """
        if param_value in RRULE_WEEKDAY_DICT:
            return RRULE_WEEKDAY_DICT[param_value]
        try:
            val = int(param_value)
        except ValueError:
            raise ValueError('rrule parameter should be integer or weekday constant (e.g. MO, TU, etc.). Error on: %s' % param_value)
        else:
            return val

    def get_params(self):
        """
        >>> job = Job(params = "count:1;bysecond:1;byminute:1,2,4,5")
        >>> job.get_params()
        {'count': 1, 'byminute': [1, 2, 4, 5], 'bysecond': 1}
        """
        if self.params is None:
            return {}
        params = self.params.split(';')
        param_dict = []
        for param in params:
            if param.strip() == "":
                continue  # skip blanks
            param = param.split(':')
            if len(param) == 2:
                param = (
                    str(param[0]).strip(),
                    [self.param_to_int(p.strip()) for p in param[1].split(',')]
                )
                if len(param[1]) == 1:
                    param = (param[0], param[1][0])
                param_dict.append(param)
        return dict(param_dict)

    def get_args(self):
        """
        Processes the args and returns a tuple or (args, options) for passing
        to ``call_command``.
        """
        args = []
        options = {}
        for arg in self.args.split():
            if arg.find('=') > -1:
                key, value = arg.split('=')
                options[smart_str(key)] = smart_str(value)
            else:
                args.append(arg)
        return (args, options)

    def is_due(self):
        reqs = (
            self.next_run <= datetime.now() and self.disabled is False
            and self.is_running is False
        )
        return (reqs or self.force_run)

    def run(self, wait=True):
        """
        Runs this ``Job``.  If ``wait`` is ``True`` any call to this function
        will not return untill the ``Job`` is complete (or fails).  This
        actually calls the management command ``kitsune_run_job`` via a
        subprocess. If you call this and want to wait for the process to
        complete, pass ``wait=True``.

        A ``Log`` will be created if there is any output from either
        stdout or stderr.

        Returns the process, a ``subprocess.Popen`` instance, or None.
        """
        if not self.disabled and self.host.name == gethostname():
            if not self.check_is_running() and self.is_due():
                p = subprocess.Popen([
                    'python', get_manage_py(), 'kitsune_run_job', str(self.pk)
                ])
                if wait:
                    p.wait()
                return p
        return None

    def handle_run(self):
        """
        This method implements the code to actually run a job. This is meant to
        be run, primarily, by the `kitsune_run_job` management command as a
        subprocess, which can be invoked by calling this job's ``run_job``
        method.
        """
        args, options = self.get_args()
        stdout = StringIO()
        stderr = StringIO()

        # Redirect output so that we can log it if there is any
        ostdout = sys.stdout
        ostderr = sys.stderr
        sys.stdout = stdout
        sys.stderr = stderr
        stdout_str, stderr_str = "", ""

        run_date = datetime.now()
        self.is_running = True
        self.pid = os.getpid()
        self.save()

        try:
            call_command(self.command, *args, **options)
            self.last_run_successful = True
        except Exception, e:
            # The command failed to run; log the exception
            t = loader.get_template('kitsune/error_message.txt')
            trace = ['\n'.join(traceback.format_exception(*sys.exc_info()))]
            c = Context({
                'exception': unicode(e),
                'traceback': trace
            })
            stderr_str += t.render(c)
            self.last_run_successful = False

        self.is_running = False
        self.pid = None
        self.last_run = run_date

        # If this was a forced run, then don't update the
        # next_run date
        if self.force_run:
            self.force_run = False
        else:
            self.next_run = self.rrule.after(run_date)

        # If we got any output, save it to the log
        stdout_str += stdout.getvalue()
        stderr_str += stderr.getvalue()

        if stderr_str:
            # If anything was printed to stderr, consider the run
            # unsuccessful
            self.last_run_successful = False

        if stdout_str or stderr_str:
            log = Log.objects.create(
                job=self,
                run_date=run_date,
                stdout=stdout_str,
                stderr=stderr_str
            )
            self.last_result = log

        self.save()
        self.delete_old_logs()
        self.email_subscribers()

        # Redirect output back to default
        sys.stdout = ostdout
        sys.stderr = ostderr

    def email_subscribers(self):
        from_email = settings.DEFAULT_FROM_EMAIL
        subject = 'Kitsune monitoring notification'

        user_ids = set([])
        for sub in self.subscriber_users.all():
            #notify subscribed users
            if sub.must_notify():
                sub.last_notification = datetime.now()
                sub.save()
                html_message = render_to_string(
                    'kitsune/mail_notification.html', {'log': self.last_result}
                )
                text_message = html2text(html_message)
                user_ids.add(sub.user.id)
                send_multi_mail(
                    subject, text_message, html_message, from_email,
                    [sub.user.email], fail_silently=False
                )

        for sub in self.subscriber_groups.all():
            if sub.must_notify():
                #notify subscribed groups
                sub.last_notification = datetime.now()
                sub.save()
                for user in sub.group.user_set.all():
                    if not (user.id in user_ids):
                        #notify users that have not already being notified
                        html_message = render_to_string(
                            'kitsune/mail_notification.html',
                            {'log': self.last_result}
                        )
                        text_message = html2text(html_message)
                        send_multi_mail(
                            subject, text_message, html_message, from_email,
                            [user.email], fail_silently=False
                        )

    def delete_old_logs(self):
        log = Log.objects.filter(job=self).order_by('-run_date')[self.last_logs_to_keep]
        Log.objects.filter(job=self, run_date__lte=log.run_date).delete()

    def check_is_running(self):
        """
        This function actually checks to ensure that a job is running.
        Currently, it only supports `posix` systems.  On non-posix systems
        it returns the value of this job's ``is_running`` field.
        """
        status = False
        if self.is_running and self.pid is not None:
            # The Job thinks that it is running, so
            # lets actually check
            if os.name == 'posix':
                # Try to use the 'ps' command to see if the process
                # is still running
                pid_re = re.compile(r'%d ([^\r\n]*)\n' % self.pid)
                p = subprocess.Popen(
                    ["ps", "-eo", "pid args"], stdout=subprocess.PIPE
                )
                p.wait()
                # If ``pid_re.findall`` returns a match it means that we have a
                # running process with this ``self.pid``. Now we must check for
                # the ``run_command`` process with the given ``self.pk``
                try:
                    pname = pid_re.findall(p.stdout.read())[0]
                except IndexError:
                    pname = ''
                if pname.find('kitsune_run_job %d' % self.pk) > -1:
                    # This Job is still running
                    return True
                else:
                    # This job thinks it is running, but really isn't.
                    self.is_running = False
                    self.pid = None
                    self.save()
            else:
                # TODO: add support for other OSes
                return self.is_running
        return False


class NotificationRule(models.Model):
    last_notification = models.DateTimeField(
        blank=True, null=True, editable=False
    )
    threshold = models.IntegerField(choices=THRESHOLD_CHOICES, max_length=10)
    rule_type = models.CharField(choices=REPETITION_CHOICES, max_length=10)
    rule_N = models.PositiveIntegerField(default=1)
    rule_M = models.PositiveIntegerField(default=2)
    interval_unit = models.CharField(
        choices=NOTIF_INTERVAL_CHOICES, max_length=10
    )
    interval_value = models.PositiveIntegerField(default=1)
    enabled = models.BooleanField(default=True)

    def __unicode__(self):
        return u'Notification to:'

    def must_notify(self):
        if self.enabled:

            if self.last_notification is not None:
                if self.interval_unit == 'Minutes':
                    dt = timedelta(minutes=self.interval_value)
                elif self.interval_unit == 'Hours':
                    dt = timedelta(hours=self.interval_value)
                else:
                    dt = timedelta(hours=1)

                threshold = self.last_notification + dt
                tt = datetime.now()
                if threshold > tt:
                    return False

            if self.rule_type == RULE_LAST:
                return self.job.last_result.get_status_code() >= self.threshold

            elif self.rule_type == RULE_LAST_N:
                n = 0
                logs = self.job.logs.order_by('-run_date')[:self.rule_N]
                for log in logs:
                    if log.get_status_code() < self.threshold:
                        break
                    else:
                        n += 1
                return n == self.rule_N

            elif self.rule_type == RULE_LAST_N_M:
                n = 0
                logs = self.job.logs.order_by('-run_date')[:self.rule_N]
                for log in logs:
                    if log.get_status_code() >= self.threshold:
                        n += 1
                return n >= self.rule_M
        return False

    class Meta:
        abstract = True


class NotificationUser(NotificationRule):
    job = models.ForeignKey('Job', related_name='subscriber_users')
    user = models.ForeignKey(User)


class NotificationGroup(NotificationRule):
    job = models.ForeignKey('Job', related_name='subscriber_groups')
    group = models.ForeignKey(Group)


class Log(models.Model):
    """
    A record of stdout and stderr of a ``Job``.
    """
    job = models.ForeignKey('Job', related_name='logs')
    run_date = models.DateTimeField(auto_now_add=True)
    stdout = models.TextField(blank=True)
    stderr = models.TextField(blank=True)
    success = models.BooleanField(default=True)  # , editable=False)

    class Meta:
        ordering = ('-run_date',)

    def __unicode__(self):
        return u"%s - %s" % (self.job.name, self.run_date)

    def admin_link(self):
        return urlresolvers.reverse(
            'admin:kitsune_' + self.__class__.__name__.lower() + '_change',
            args=(self.id,)
        )

    def get_status_code(self):
        return int(self.stderr)


class Host(models.Model):
    """
    The hosts to be checked.
    """
    name = models.CharField(blank=False, max_length=150)
    ip = models.CharField(blank=True, max_length=15)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = monitor
""" Utility interface classes for passing information off to pollers (ArgSet) or receiving results to be
published against existing Monitors."""

import simplejson
import dateutil.parser
import datetime
import re


class MonitoringPoller:
    """ Abstract base class for the pollers that Eyes runs. Each poller is expected to have
    the following functions:
      run_plugin(plugin_name, argset)
      plugin_help(plugin_name)
      plugin_list()
    """

    def run_plugin(self, plugin_name, argset=None):
        """ runs the plugin and returns the results in the form of a MonitorResult object"""
        raise NotImplementedError

    def plugin_help(self, plugin_name):
        """ runs the given plugin function to get interactive help results. Intended to
        return sufficient information to create an ArgSet object to run the poller properly."""
        raise NotImplementedError

    def plugin_list(self):
        """ returns a list of the plugins that this poller provides. And of the list of
        plugins should be able to be invoked with plugin_help(plugin_name) to get a response back
        that includes sufficient information to create an ArgSet and invoke the plugin
        to monitor a remote system."""
        return None

    def __init__(self):
        """default initialization"""
        self.poller_kind = "eyeswebapp.util.baseclass"


class MonitorResult:
    """
    A class representation of the dictionary structure that a monitor returns as it's
    combined result set. A MonitorResult can be serialized and deserialized into JSON
    and includes a structured segment to return multiple counts/values as a part of a monitor
    invocation, either active of passive. Initial structure of MonitorResult is based on the
    data that a Nagios plugin returns.

    The internal dictionary structure:
    ** command - string
    ** error - string or None
    ** returncode - integer
    ** timestamp - string of a datestamp (ISO format)
    ** output - string or None
    ** decoded - a dictionary
    ** decoded must have the following keys:
    *** human - a string
    *** 1 or more other keys, which are strings
    *** for each key other than human, the following keys must exist:
    **** UOM - a string of [] or None
    **** critvalue - string repr of a number, empty string, or None
    **** warnvalue - string repr of a number, empty string, or None
    **** label - string same as the key
    **** maxvalue - string repr of a number, empty string, or None
    **** minvalue - string repr of a number, empty string, or None
    **** minvalue - string repr of a number

    Here's an example:
    {'command': '/opt/local/libexec/nagios/check_ping -H localhost -w 1,99% -c 1,99%',
     'decoded': {'human': 'PING OK - Packet loss = 0%, RTA = 0.11 ms',
                 'pl': {'UOM': '%',
                        'critvalue': '99',
                        'label': 'pl',
                        'maxvalue': '',
                        'minvalue': '0',
                        'value': '0',
                        'warnvalue': '99'},
                 'rta': {'UOM': 'ms',
                         'critvalue': '1.000000',
                         'label': 'rta',
                         'maxvalue': '',
                         'minvalue': '0.000000',
                         'value': '0.113000',
                         'warnvalue': '1.000000'}},
     'error': None,
     'output': 'PING OK - Packet loss = 0%, RTA = 0.11 ms|rta=0.113000ms;1.000000;1.000000;0.000000 pl=0%;99;99;0',
     'returncode': 0,
     'timestamp': '2009-11-07T16:43:46.696214'}
    """
    UOM_PARSECODE = re.compile('([\d\.]+)([a-zA-Z%]*)')

    def __init__(self):
        self._initialize()
    # def __delitem__(self,key):
    #     del self._internal_dict[key]
    # def __setitem__(self,key,item):
    #     self._internal_dict[key]=item
    # def __getitem__(self,key):
    #     return self._internal_dict[key]
    # def __iter__(self):
    #     return self._internal_dict.__iter__()
    # def __repr__(self):
    #     return self._internal_dict.__repr__()
    # def has_key(self,key):
    #     return self._internal_dict.has_key(key)
    # def keys(self):
    #     return self._internal_dict.keys()

    def _initialize(self):
        self.command = ""
        self.output = ""
        self.error = ""
        self.returncode = 0
        self.timestamp = datetime.datetime.now()
        decoded_dict = {'human': ''}
        empty_label = '_'
        data_dict = {}
        data_dict['label'] = empty_label
        data_dict['value'] = 0
        data_dict['UOM'] = ''
        data_dict['warnvalue'] = ''
        data_dict['critvalue'] = ''
        data_dict['minvalue'] = ''
        data_dict['maxvalue'] = ''
        decoded_dict[empty_label] = data_dict
        self.decoded = decoded_dict

    @staticmethod
    def parse_nagios_output(nagios_output_string):
        """ parses the standard output of a nagios check command. The resulting dictionary as output
        will have at least one key: "human", indicating the human readable portion of what was parsed.
        There will be additional dictionaries of parsed data, each from a key based on the label of
        the performance data returned by the nagios check command.

        For notes on the guidelines for writing Nagios plugins and their expected output, see
        http://nagiosplug.sourceforge.net/developer-guidelines.html

        For example parse_nagios_output("PING OK - Packet loss = 0%, RTA = 0.18 ms|rta=0.182ms;1.00;1.00;0.00 pl=0%;99;99;0")
        should come back as
        {'human': 'PING OK - Packet loss = 0%, RTA = 0.18 ms',
         'pl': {'UOM': '%',
                'critvalue': '99',
                'label': 'pl',
                'maxvalue': '',
                'minvalue': '0',
                'value': '0',
                'warnvalue': '99'},
         'rta': {'UOM': 'ms',
                 'critvalue': '1.00',
                 'label': 'rta',
                 'maxvalue': '',
                 'minvalue': '0.00',
                 'value': '0.182',
                 'warnvalue': '1.00'}}

        Each parsed performance data dictionary should have the following keys:
        * label
        * value
        * UOM
            '' - assume a number (int or float) of things (eg, users, processes, load averages)
            s - seconds (also us, ms)
            % - percentage
            B - bytes (also KB, MB, TB)
            c - a continous counter (such as bytes transmitted on an interface)
        * warnvalue (content may be None)
        * critvalue (content may be None)
        * minvalue (content may be None)
        * maxvalue (content may be None)
        """
        if nagios_output_string is None:
            return None
        return_dict = {}
        try:
            (humandata, parsedata) = nagios_output_string.split('|')
        except ValueError:  # output not in expected format, bail out
            return None
        return_dict['human'] = humandata
        list_of_parsedata = parsedata.split()  # ['rta=0.182000ms;1.000000;1.000000;0.000000', 'pl=0%;99;99;0']
        for dataset in list_of_parsedata:
            parts = dataset.split(';', 5)
            if (len(parts) > 0):
                data_dict = {}
                try:
                    (label, uom_value) = parts[0].split('=')
                except ValueError:  # output not in expected format, bail out
                    return None
                data_dict['label'] = label
                result = MonitorResult.UOM_PARSECODE.match(uom_value)
                data_dict['value'] = result.groups()[0]
                data_dict['UOM'] = result.groups()[1]
                data_dict['warnvalue'] = ''
                data_dict['critvalue'] = ''
                data_dict['minvalue'] = ''
                data_dict['maxvalue'] = ''
                if len(parts) > 1:
                    data_dict['warnvalue'] = parts[1]
                if len(parts) > 2:
                    data_dict['critvalue'] = parts[2]
                if len(parts) > 3:
                    data_dict['minvalue'] = parts[3]
                if len(parts) > 4:
                    data_dict['maxvalue'] = parts[4]
                return_dict[label] = data_dict
        return return_dict

    @staticmethod
    def createMonitorResultFromNagios(nagios_output_string):
        """ creates a new MonitorResult object from a nagios output string """
        if nagios_output_string is None:
            raise ValueError("Empty nagios output string provided to initializer")
        parsed_dict = MonitorResult.parse_nagios_output(nagios_output_string)
        if parsed_dict is None:
            raise ValueError("Error parsing Nagios output")
        new_monitor_result = MonitorResult()
        new_monitor_result.decoded = parsed_dict
        return new_monitor_result

    def json(self):
        """ return MonitorResult as a JSON representation """
        dict_to_dump = {}
        dict_to_dump['command'] = self.command
        dict_to_dump['output'] = self.output
        dict_to_dump['error'] = self.error
        dict_to_dump['returncode'] = self.returncode
        dict_to_dump['timestamp'] = self.timestamp.isoformat()
        dict_to_dump['decoded'] = self.decoded
        return simplejson.dumps(dict_to_dump)

    # unicode_type = type(u'123')
    # string_type = type('123')
    # int_type = type(5)
    # dict_type = type({})
    # list_type = type([])
    # load using "isinstance" if isinstance(key,unicode_type...)

    def loadjson(self, json_string):
        """ load up an external JSON string into an ArgSet, overwriting the existing data here"""
        some_structure = simplejson.loads(json_string)
        # validate structure
        if not(isinstance(some_structure, type({}))):
            raise ValueError("json structure being loaded (%s) is not a dictionary" % some_structure)
        #
        # command validation
        if not('command' in some_structure):
            raise KeyError("dictionary must have a 'command' key")
        new_command = some_structure['command']
        if not(isinstance(new_command, type('123')) or isinstance(new_command, type(u'123'))):
            raise ValueError("command value must be a string or unicode")
        #
        # error validaton
        if not('error' in some_structure):
            raise KeyError("dictionary must have an 'error' key")
        new_error = some_structure['error']
        #
        # return code validaton
        if not('returncode' in some_structure):
            raise KeyError("dictionary must have a 'returncode' key")
        new_rc = some_structure['returncode']
        if not(isinstance(new_rc, type(5))):
            raise ValueError("returncode must be an integer")
        if ((new_rc < 0) or (new_rc > 3)):
            raise ValueError("returncode must be between 0 and 3")
        #
        # timestamp validation
        if not('timestamp' in some_structure):
            raise KeyError("dictionary must have a 'timestamp' key")
        new_timestamp = dateutil.parser.parse(some_structure['timestamp'])
        #
        # output validation
        if not('output' in some_structure):
            raise KeyError("dictionary must have an 'output' key")
        new_output = some_structure['output']
        #
        # decoded validation
        if not('decoded' in some_structure):
            raise KeyError("dictionary must have a 'decoded' key")
        #
        decoded_dict = some_structure['decoded']
        if not(isinstance(decoded_dict, type({}))):
            raise ValueError("decoded value must be a dictionary")
        if not('human' in decoded_dict):
            raise KeyError("decoded dictionary must have a 'human' key")
        if not(isinstance(decoded_dict['human'], type('123')) or isinstance(decoded_dict['human'], type(u'123'))):
            raise ValueError("value for 'human' key must be a string or unicode")
        #
        keylist = decoded_dict.keys()
        keylist.remove('human')
        if len(keylist) < 1:
            raise KeyError("decoded dictionary must have a key other than 'human' ")
        for key in keylist:
            keydict = decoded_dict[key]
            if not(isinstance(keydict, type({}))):
                raise ValueError("keydict must be a dictionary")
            #
            if not('UOM' in keydict):
                raise ValueError("key dictionary must have a 'UOM' key")
            #
            if not('label' in keydict):
                raise ValueError("key dictionary must have a 'label' key")
            #
            if not('maxvalue' in keydict):
                raise ValueError("key dictionary must have a 'maxvalue' key")
            #
            if not('minvalue' in keydict):
                raise ValueError("key dictionary must have a 'minvalue' key")
            #
            if not('critvalue' in keydict):
                raise ValueError("key dictionary must have a 'critvalue' key")
            #
            if not('warnvalue' in keydict):
                raise ValueError("key dictionary must have a 'warnvalue' key")
            #
            if not('value' in keydict):
                raise ValueError("key dictionary must have a 'value' key")
            floatval = float(keydict['value'])
        #
        # we made it through the validation gauntlet - set the structure into place
        self.command = new_command
        self.output = new_output
        self.error = new_error
        self.returncode = new_rc
        self.timestamp = new_timestamp
        self.decoded = decoded_dict


def validate_return_dictionary(result_struct):
    """
    The returning structure should:
    * be a dictionary with the following mandatory keys:
    ** command - string
    ** error - string or None
    ** returncode - integer
    ** timestamp - string of a datestamp (ISO format)
    ** output - string or None
    ** decoded - a dictionary
    ** decoded must have the following keys:
    *** human - a string
    *** 1 or more other keys, which are strings
    *** for each key other than human, the following keys must exist:
    **** UOM - a string of [] or None
    **** critvalue - string repr of a number, empty string, or None
    **** warnvalue - string repr of a number, empty string, or None
    **** label - string same as the key
    **** maxvalue - string repr of a number, empty string, or None
    **** minvalue - string repr of a number, empty string, or None
    **** minvalue - string repr of a number
    """
    if (result_struct.__class__ == {}.__class__):
        # command validation
        if not('command' in result_struct):
            return False
        if result_struct['command'] is None:
            return False
        if not((result_struct['command'].__class__ == '123'.__class__) or (result_struct['command'].__class__ == u'123'.__class__)):
            return False
        # error validaton
        if not('error' in result_struct):
            return False
        # return code validaton
        if not('returncode' in result_struct):
            return False
        if not((type(result_struct['returncode']) == type(3)) or type(result_struct['returncode']) == type(3.1)):
            return False
        if ((result_struct['returncode'] < 0) or (result_struct['returncode'] > 3)):
            return False
        # timestamp validation
        if not('timestamp' in result_struct):
            return False
        try:
            result = dateutil.parser.parse(result_struct['timestamp'])
        except ValueError:
            return False
        if not('output' in result_struct):
            return False
        if not('decoded' in result_struct):
            return False
        decoded_dict = result_struct['decoded']
        if type(decoded_dict) != type({}):
            return False
        if not('human' in decoded_dict):
            return False
        if len(decoded_dict.keys()) < 2:
            return False
        keylist = decoded_dict.keys()
        keylist.remove('human')
        if len(keylist) < 1:
            return False
        for key in keylist:
            keydict = decoded_dict[key]
            if type(keydict) != type({}):
                return False
            if not('UOM' in keydict):
                return False
            #
            if not('critvalue' in keydict):
                return False
            #
            if not('label' in keydict):
                return False
            #
            if not('maxvalue' in keydict):
                return False
            #
            if not('minvalue' in keydict):
                return False
            #
            if not('warnvalue' in keydict):
                return False
            #
            if not('value' in keydict):
                return False
            try:
                floatval = float(keydict['value'])
            except ValueError:
                return False
        #
        return True
    return False


def validate_poller_results(json_return_dict):
    """ validates a return set from a poller, returning True if the format is acceptable, False if not.
    This methods *expects* a JSON string as input
    """
    if json_return_dict is None:
        return False
    try:
        result_struct = simplejson.loads(json_return_dict)
        return validate_return_dictionary(result_struct)
    except:
        return False


class ArgSet:
    """
    a class representing the set of arguments to pass into a command invocation to trigger a poller.
    Expected to be able to be serialized into a JSON object and back again.
    Suitable for a message that can pass in a queue if needed.
    """
    def __init__(self):
        self._internal_list = []

    def list_of_arguments(self):
        """returns a flat list of arguments"""
        return self._internal_list

    def add_argument(self, argument):
        """method for adding a single argument, such as '--help' to a call"""
        self._internal_list.append(argument)

    def add_argument_pair(self, arg_key, arg_value):
        """method for adding a pair of arguments, such as '-H localhost' to a call"""
        new_string = "%s %s" % (arg_key, arg_value)
        self._internal_list.append(new_string)

    def json(self):
        """ return argset as a JSON representation """
        return simplejson.dumps(self._internal_list)

    def loadjson(self, json_string):
        """ load up an external JSON string into an ArgSet, overwriting the existing data here"""
        structure = simplejson.loads(json_string)
        # validate structure
        if (structure.__class__ == [].__class__):
            # outer shell is a list.. so far, so good
            for argument in structure:
                if (argument.__class__ == '123'.__class__) or (argument.__class__ == u'123'.__class__):
                    #argument is a string
                    pass
                else:
                    raise ValueError("argument (%s) is not a string" % argument)
        else:
            raise ValueError("json structure being loaded (%s) was not a list" % structure)
        self._internal_list = structure

    def __str__(self):
        if len(self._internal_list) < 1:
            return ""
        else:
            return " ".join(self._internal_list)

########NEW FILE########
__FILENAME__ = nagios
#!/usr/bin/env python
# encoding: utf-8
"""
nagios.py

Class to invoke nagios plugins and return the results in a structured format.

Created by Joseph Heck on 2009-10-24.

"""
import os
import sys
import re
import subprocess
import datetime
from monitor import ArgSet
from monitor import MonitorResult
from monitor import MonitoringPoller


class NagiosPoller(MonitoringPoller):
    """a class that invokes a Nagios plugin and returns the result"""
    def __init__(self):
        """default initialization"""
        MonitoringPoller.__init__(self)
        self.plugin_dir = "/usr/local/nagios/libexec"  # default - aiming for RHEL5 instance of nagios-plugins
        if os.path.exists("/usr/lib/nagios/plugins"):  # ubuntu's apt-get install nagios-plugins
            self.plugin_dir = "/usr/lib/nagios/plugins"
        if os.path.exists("/opt/local/libexec/nagios"):  # MacOS X port install nagios-plugins
            self.plugin_dir = "/opt/local/libexec/nagios"
        self._internal_plugin_list = []
        self._load_plugin_list()
        self.uom_parsecode = re.compile('([\d\.]+)([a-zA-Z%]*)')
        self.poller_kind = "eyeswebapp.util.nagios.NagiosPoller"

    def _load_plugin_list(self):
        """ load in the plugins from the directory 'plugin_dir' set on the poller..."""
        self._internal_plugin_list = []
        raw_list = os.listdir(self.plugin_dir)
        for potential in raw_list:
            if potential.startswith("check_"):
                self._internal_plugin_list.append(potential)

    def plugin_list(self):
        """ returns the internal list of plugins available to Nagios"""
        return self._internal_plugin_list

    def plugin_help(self, plugin_name):
        """invoke --help on the named plugin, return the results"""
        argset = ArgSet()
        argset.add_argument('--help')
        return self.run_plugin(plugin_name, argset)

    def _invoke(self, plugin_name, list_of_args=None):
        """parse and invoke the plugin. method accepts the plugin name and then a list of arguments to be invoked.
        The return value is either None or a dictionary with the following keys:
        * command - the command invoked on the command line from the poller
        * output - the standard output from the command, strip()'d
        * error - the standard error from the command, strip()'d
        """
        if plugin_name is None:
            return None
        monresult = MonitorResult()
        cmd = os.path.join(self.plugin_dir, plugin_name)
        if not os.path.exists(cmd):
            monresult.error = "No plugin named %s found." % plugin_name
            monresult.timestamp = datetime.datetime.now()
            monresult.returncode = 3
            return monresult
        if not(list_of_args is None):
            for arg in list_of_args:
                cmd += " %s" % arg
        monresult.command = cmd.strip()
        if sys.platform == 'win32':
            close_fds = False
        else:
            close_fds = True
        #
        process = subprocess.Popen(cmd, shell=True, close_fds=close_fds, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdoutput, stderror) = process.communicate()
        monresult.timestamp = datetime.datetime.now()
        monresult.returncode = process.returncode
        if (stdoutput):
            cleaned_out = stdoutput.strip()
            monresult.output = cleaned_out
            monresult.decoded = MonitorResult.parse_nagios_output(cleaned_out)
        if (stderror):
            cleaned_err = stderror.strip()
            monresult.error = cleaned_err
        return monresult

    def run_plugin(self, plugin_name, argset=None):
        """run_plugin is the primary means of invoking a Nagios plugin. It takes a plugin_name, such
        as 'check_ping' and an optional ArgSet object, which contains the arguments to run the plugin
        on the command line.

        Example results:
        >>> xyz = NagiosPoller()
        >>> ping_argset = ArgSet()
        >>> ping_argset.add_argument_pair("-H", "localhost")
        >>> ping_argset.add_argument_pair("-w", "1,99%")
        >>> ping_argset.add_argument_pair("-c", "1,99%")
        >>> monitor_result = xyz.run_plugin('check_ping', ping_argset)
        >>> print monitor_result.command
        /opt/local/libexec/nagios/check_ping -H localhost -w 1,99% -c 1,99%
        >>> print monitor_result.output
        PING OK - Packet loss = 0%, RTA = 0.14 ms|rta=0.137000ms;1.000000;1.000000;0.000000 pl=0%;99;99;0
        >>> print monitor_result.error

        >>> print monitor_result.returncode
        0
        >>> abc = NagiosPoller()
        >>> http_argset = ArgSet()
        >>> http_argset.add_argument_pair("-H", "www.google.com")
        >>> http_argset.add_argument_pair("-p", "80")
        >>> mon_result = abc.run_plugin('check_http', http_argset)
        >>> print monitor_result.command
        Traceback (most recent call last):
          File "<console>", line 1, in <module>
        NameError: name 'monitor_result' is not defined
        >>> print mon_result.command
        /opt/local/libexec/nagios/check_http -H www.google.com -p 80
        >>> print mon_result.output
        HTTP OK: HTTP/1.1 200 OK - 9047 bytes in 0.289 second response time |time=0.288865s;;;0.000000 size=9047B;;;0
        >>> print mon_result.error

        >>> print mon_result.returncode
        0
        """
        if argset is None:
            monitor_result = self._invoke(plugin_name)  # returns a MonitorResult object
        else:
            monitor_result = self._invoke(plugin_name, argset.list_of_arguments())  # returns a MonitorResult object
        return monitor_result

# if __name__ == '__main__':
#     import pprint
#     xyz = NagiosPoller()
#     ping_argset = ArgSet()
#     ping_argset.add_argument_pair("-H", "localhost")
#     ping_argset.add_argument_pair("-w", "1,99%")
#     ping_argset.add_argument_pair("-c", "1,99%")
#     ping_result = xyz.run_plugin('check_ping', ping_argset)
#     print ping_result.json()
#
#     abc = NagiosPoller()
#     http_argset = ArgSet()
#     http_argset.add_argument_pair("-H", "www.google.com")
#     http_argset.add_argument_pair("-p", "80")
#     http_result = abc.run_plugin('check_http', http_argset)
#     print http_result.json()

########NEW FILE########
__FILENAME__ = renderers
# -*- coding: utf-8 -
'''
Created on Mar 3, 2012

@author: Raul Garreta (raul@tryolabs.com)

Defines the base Kitsune job renderer.
All custom Kitsune job renderers must extend KitsuneJobRenderer.
'''

__author__      = "Raul Garreta (raul@tryolabs.com)"


from django.template.loader import render_to_string

from kitsune.base import STATUS_OK, STATUS_WARNING, STATUS_CRITICAL, STATUS_UNKNOWN



class KitsuneJobRenderer():
    
    def get_html_status(self, log):
        return render_to_string('kitsune/status_code.html', dictionary={'status_code':int(log.stderr)})
        
    def get_html_message(self, log):
        result = log.stdout
        if len(result) > 40:
            result = result[:40] + '...'
        return result
########NEW FILE########
__FILENAME__ = scripts
# -*- coding: utf-8 -
'''
Created on Mar 5, 2012

@author: Raul Garreta (raul@tryolabs.com)

Test scripts.

'''

__author__      = "Raul Garreta (raul@tryolabs.com)"


from nagios import NagiosPoller
from monitor import ArgSet


def check_http():
    poller = NagiosPoller()
    args = ArgSet()
    args.add_argument_pair("-H", "liukang.tryolabs.com")
    args.add_argument_pair("-p", "80")
    res = poller.run_plugin('check_http', args)
    print "\n",res.command,"\nRET CODE:\t",res.returncode,"\nOUT:\t\t",res.output,"\nERR:\t\t",res.error
    
    
def check_ping():
    poller = NagiosPoller()
    args = ArgSet()
    args.add_argument_pair("-H", "google.com")
    args.add_argument_pair("-w", "200.0,20%")
    args.add_argument_pair("-c", "500.0,60%")
    res = poller.run_plugin('check_ping', args)
    print "\n",res.command,"\nRET CODE:\t",res.returncode,"\nOUT:\t\t",res.output,"\nERR:\t\t",res.error
    
    
def check_disk():
    poller = NagiosPoller()
    args = ArgSet()
    args.add_argument_pair("-u", "GB")
    args.add_argument_pair("-w", "5")
    args.add_argument_pair("-c", "2")
    args.add_argument_pair("-p", "/")
    res = poller.run_plugin('check_disk', args)
    print "\n",res.command,"\nRET CODE:\t",res.returncode,"\nOUT:\t\t",res.output,"\nERR:\t\t",res.error
    
    
def check_pgsql():
    poller = NagiosPoller()
    args = ArgSet()
    args.add_argument_pair("-H", "localhost")
    args.add_argument_pair("-d", "daywatch_db")
    args.add_argument_pair("-p", "postgres")
    res = poller.run_plugin('check_pgsql', args)
    print "\n",res.command,"\nRET CODE:\t",res.returncode,"\nOUT:\t\t",res.output,"\nERR:\t\t",res.error
########NEW FILE########
__FILENAME__ = kitsune_tags
from django import template
from django.core.urlresolvers import reverse, NoReverseMatch

register = template.Library()

class RunJobURLNode(template.Node):
    def __init__(self, object_id):
        self.object_id = template.Variable(object_id)
        
    def render(self, context):
        object_id = self.object_id.resolve(context)
        #print object_id
        try:
            # Old way
            url = reverse('kitsune_job_run', args=(object_id,))
        except NoReverseMatch:
            # New way
            url = reverse('admin:kitsune_job_run', args=(object_id,))
        return url

def do_get_run_job_url(parser, token):
    """
    Returns the URL to the view that does the 'run_job' command.
    
    Usage::
    
        {% get_run_job_url [object_id] %}
    """
    try:
        # Splitting by None == splitting by spaces.
        tag_name, object_id = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires one argument" % token.contents.split()[0]
    return RunJobURLNode(object_id)

register.tag('get_run_job_url', do_get_run_job_url)
########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -
'''
Created on Mar 3, 2012

@author: Raul Garreta (raul@tryolabs.com)

Based on django-chronograph.

'''

__author__ = "Raul Garreta (raul@tryolabs.com)"


import os

import django
from django.conf import settings
from django.utils.importlib import import_module


def get_manage_py():
    module = import_module(settings.SETTINGS_MODULE)
    if django.get_version().startswith('1.3'):
        # This is dirty, but worked in django <= 1.3 ...
        from django.core.management import setup_environ
        return os.path.join(
            setup_environ(module, settings.SETTINGS_MODULE), 'manage.py'
        )
    else:
        # Dirty again, but this should work in django > 1.3
        # We should DEFINITELY do this in an elegant way ...
        settings_path = os.path.dirname(module.__file__)
        return os.path.join(settings_path, '..', 'manage.py')

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -
'''
Created on Mar 3, 2012

@author: Raul Garreta (raul@tryolabs.com)

Based on django-chronograph.

'''

__author__      = "Raul Garreta (raul@tryolabs.com)"


from django.contrib import admin
from django.contrib.auth.decorators import user_passes_test
from admin import JobAdmin
from models import Job

def job_run(request, pk):
    return JobAdmin(Job, admin.site).run_job_view(request, pk)
job_run = user_passes_test(lambda user: user.is_superuser)(job_run)
########NEW FILE########
