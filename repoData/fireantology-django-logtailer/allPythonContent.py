__FILENAME__ = admin
from django.contrib import admin
from django.conf import settings
from logtailer.models import LogFile, Filter, LogsClipboard

class LogFileAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'path')
    
    class Media:
        js = (settings.STATIC_URL+'logtailer/js/jquery.colorbox-min.js',)
        css = {
            'all': (settings.STATIC_URL+'logtailer/css/colorbox.css',)
        }
        
class FilterAdmin(admin.ModelAdmin):
    list_display = ('name', 'regex')   

class LogsClipboardAdmin(admin.ModelAdmin):
    list_display = ('name', 'notes', 'log_file')
    readonly_fields = ('name', 'notes', 'logs', 'log_file')
    
admin.site.register(LogFile, LogFileAdmin)
admin.site.register(Filter, FilterAdmin)
admin.site.register(LogsClipboard, LogsClipboardAdmin)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _

class LogFile(models.Model):
    name = models.CharField(_('name'), max_length=180)
    path = models.CharField(_('path'), max_length=500)
    
    def __unicode__(self):
        return '%s' % self.name
    
    class Meta:
        verbose_name = _('log_file')
        verbose_name_plural = _('log_files')
        
class Filter(models.Model):
    name = models.CharField(_('name'), max_length=180)
    regex = models.CharField(_('regex'), max_length=500)
    
    def __unicode__(self):
        return '%s | %s: %s ' % (self.name, _('pattern'), self.regex)
    
    class Meta:
        verbose_name = _('filter')
        verbose_name_plural = _('filters')
        
class LogsClipboard(models.Model):
    name = models.CharField(_('name'), max_length=180)
    notes = models.TextField(_('notes'), blank=True, null=True)
    logs = models.TextField(_('logs'))
    log_file = models.ForeignKey(LogFile, verbose_name=_('log_file'))
    
    def __unicode__(self):
        return "%s" % self.name
    
    class Meta:
        verbose_name = _('logs_clipboard')
        verbose_name_plural = _('logs_clipboard')
########NEW FILE########
__FILENAME__ = logtailer_utils
from django import template
from logtailer.models import Filter

register = template.Library()

@register.inclusion_tag('logtailer/templatetags/filters.html')
def filters_select():
    filters = Filter.objects.all()
    return {'filters': filters}
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns
from django.conf.urls.defaults import url

urlpatterns = patterns('logtailer.views',
    url(r'^readlogs/$', 'read_logs'),
    url(r'^get-log-line/(?P<file_id>\d+)/$', 'get_log_lines', name='logtailer_get_log_lines'),
    url(r'^get-history/(?P<file_id>\d+)/$', 'get_log_lines', {'history': True}, name='logtailer_get_history'),
    url(r'^save-to-clipboard/$', 'save_to_cliboard', name="logtailer_save_to_clipboard"),
)

########NEW FILE########
__FILENAME__ = views
import os
import json
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from logtailer.models import LogsClipboard, LogFile
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required

from django.conf import settings

HISTORY_LINES = getattr(settings, 'LOGTAILER_HISTORY_LINES', 0)

def read_logs(request):
    context = {}
    return render_to_response('logtailer/log_reader.html',
                              context, 
                              RequestContext(request, {}),)


def get_history(f, lines=HISTORY_LINES):
    BUFSIZ = 1024
    f.seek(0, os.SEEK_END)
    bytes = f.tell()
    size = lines
    block = -1
    data = []
    while size > 0 and bytes > 0:
        if (bytes - BUFSIZ > 0):
            # Seek back one whole BUFSIZ
            f.seek(block*BUFSIZ, 2)
            # read BUFFER
            data.append(f.read(BUFSIZ))
        else:
            # file too small, start from beginning
            f.seek(0,0)
            # only read what was not read
            data.append(f.read(bytes))
        linesFound = data[-1].count('\n')
        size -= linesFound
        bytes -= BUFSIZ
        block -= 1
    return ''.join(data).splitlines(True)[-lines:]

@staff_member_required
def get_log_lines(request,file_id, history=False):
    try:
        file_record = LogFile.objects.get(id=file_id)
    except LogFile.DoesNotExist:
        return HttpResponse(json.dumps([_('error_logfile_notexist')]),
                            mimetype = 'text/html')
    content = []
    file = open(file_record.path, 'r')

    if history:
        content = get_history(file)
        content = [line.replace('\n','<br/>') for line in content]
    else:
        last_position = request.session.get('file_position_%s' % file_id)

        file.seek(0, os.SEEK_END)
        if last_position and last_position<=file.tell():
            file.seek(last_position)

        for line in file:
            content.append('%s' % line.replace('\n','<br/>'))

    request.session['file_position_%s' % file_id] = file.tell()
    file.close()
    return HttpResponse(json.dumps(content), mimetype = 'application/json')

@csrf_exempt
def save_to_cliboard(request):
    object = LogsClipboard(name = request.POST['name'],
                           notes = request.POST['notes'],
                           logs = request.POST['logs'],
                           log_file = LogFile.objects\
                           .get(id=int(request.POST['file'])))
    object.save()
    return HttpResponse(_('loglines_saved'), mimetype = 'text/html')
    
  
    
staff_member_required(read_logs)

########NEW FILE########
