__FILENAME__ = admin
from django.contrib import admin
from django.contrib.admin.filterspecs import AllValuesFilterSpec, FilterSpec
from django.contrib.admin.util import unquote
from django.contrib.admin.views.main import ChangeList, Paginator
from django.core.cache import cache
from django.utils.encoding import force_unicode, smart_unicode
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django import forms

from djangodblog.helpers import ImprovedExceptionReporter
from djangodblog.models import ErrorBatch, Error
from djangodblog.settings import *

import base64
import re
import logging
import sys
try:
    import cPickle as pickle
except ImportError:
    import pickle

logger = logging.getLogger('dblog')

# Custom admin and pagination clauses for efficiency

class EfficientPaginator(Paginator):
    def _get_count(self):
        # because who really cares if theres a next page or not in the admin?
        return 1000
    count = property(_get_count)

class EfficientChangeList(ChangeList):
    def get_results(self, request):
        paginator = EfficientPaginator(self.query_set, self.list_per_page)
        result_count = paginator.count

        # Get the list of objects to display on this page.
        try:
            result_list = paginator.page(self.page_num+1).object_list
        except InvalidPage:
            result_list = ()

        self.full_result_count = result_count
        self.result_count = result_count
        self.result_list = result_list
        self.can_show_all = False
        self.multi_page = True
        self.paginator = paginator

class EfficientModelAdmin(admin.ModelAdmin):
    def get_changelist(self, request, **kwargs):
        return EfficientChangeList

class EfficientAllValuesFilterSpec(AllValuesFilterSpec):
    def __init__(self, f, request, params, model, model_admin):
        super(AllValuesFilterSpec, self).__init__(f, request, params, model, model_admin)
        self.lookup_val = request.GET.get(f.name, None)
        qs = model_admin.queryset(request).order_by(f.name)
        # self.lookup_choices = list(qs.values_list(f.name, flat=True).distinct())

        # We are asking for the unique set of values from the last 1000 recorded entries
        # so as to avoid a massive database hit.
        # We could do this as a subquery but mysql doesnt support LIMIT in subselects
        self.lookup_choices = list(qs.distinct()\
                                     .filter(pk__in=list(qs.values_list('pk', flat=True)[:1000]))
                                     .values_list(f.name, flat=True))

    def choices(self, cl):
        yield {'selected': self.lookup_val is None,
               'query_string': cl.get_query_string({}, [self.field.name]),
               'display': _('all')}
        for val in self.lookup_choices:
            val = smart_unicode(val)
            yield {'selected': self.lookup_val == val,
                   'query_string': cl.get_query_string({self.field.name: val}),
                   'display': val}
FilterSpec.filter_specs.insert(-1, (lambda f: hasattr(f, 'model') and f.model._meta.app_label == 'djangodblog', EfficientAllValuesFilterSpec))

UNDEFINED = object()

class FakeRequest(object):
    def build_absolute_uri(self): return self.url
    
# Custom forms/fields for the admin

class PreformattedText(forms.Textarea):
    input_type = 'textarea'
    
    def render(self, name, value, attrs=None):
        if value is None: value = ''
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            value = force_unicode(value)
        return mark_safe(u'<pre style="clear:left;display:block;padding-top:5px;white-space: pre-wrap;white-space: -moz-pre-wrap;white-space: -pre-wrap;white-space: -o-pre-wrap;word-wrap: break-word;">%s</pre>' % (escape(value),))

class Link(forms.TextInput):
    input_type = 'a'

    def render(self, name, value, attrs=None):
        if value is None: value = ''
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            value = force_unicode(value)
        return mark_safe(u'<a href="%s">%s</a>' % (value, escape(value)))

class ErrorBatchAdminForm(forms.ModelForm):
    traceback = forms.CharField(widget=PreformattedText())
    url = forms.CharField(widget=Link())
    
    class Meta:
        fields = ('url', 'logger', 'server_name', 'class_name', 'level', 'message', 'times_seen', 'first_seen', 'last_seen', 'traceback')
        model = ErrorBatch

class ErrorAdminForm(forms.ModelForm):
    traceback = forms.CharField(widget=PreformattedText())
    url = forms.CharField(widget=Link())
    
    class Meta:
        fields = ('url', 'logger', 'server_name', 'class_name', 'level', 'message', 'datetime', 'traceback')
        model = ErrorBatch

# Actual admin modules

class ErrorBatchAdmin(EfficientModelAdmin):
    form            = ErrorBatchAdminForm
    list_display    = ('shortened_url', 'logger', 'level', 'server_name', 'times_seen', 'last_seen')
    list_display_links = ('shortened_url',)
    list_filter     = ('status', 'server_name', 'logger', 'level', 'last_seen')
    ordering        = ('-last_seen',)
    actions         = ('resolve_errorbatch',)
    search_fields   = ('url', 'class_name', 'message', 'traceback', 'server_name')
    readonly_fields = ('class_name', 'message', 'times_seen', 'first_seen')
    fieldsets       = (
        (None, {
            'fields': ('class_name', 'message', 'times_seen', 'first_seen', 'traceback')
        }),
    )
    
    def resolve_errorbatch(self, request, queryset):
        rows_updated = queryset.update(status=1)
        
        if rows_updated == 1:
            message_bit = "1 error summary was"
        else:
            message_bit = "%s error summaries were" % rows_updated
        self.message_user(request, "%s resolved." % message_bit)
        
    resolve_errorbatch.short_description = 'Resolve selected error summaries'

    def change_view(self, request, object_id, extra_context={}):
        obj = self.get_object(request, unquote(object_id))
        recent_errors = Error.objects.filter(checksum=obj.checksum).order_by('-datetime')[0:5]
        extra_context.update({
            'instance': obj,
            'recent_errors': recent_errors,
        })
        return super(ErrorBatchAdmin, self).change_view(request, object_id, extra_context)

class ErrorAdmin(EfficientModelAdmin):
    form            = ErrorAdminForm
    list_display    = ('shortened_url', 'logger', 'level', 'server_name', 'datetime')
    list_display_links = ('shortened_url',)
    list_filter     = ('server_name', 'logger', 'level', 'datetime')
    ordering        = ('-datetime',)
    search_fields   = ('url', 'class_name', 'message', 'traceback', 'server_name')
    readonly_fields = ('class_name', 'message')
    fieldsets       = (
        (None, {
            'fields': ('class_name', 'message', 'traceback')
        }),
    )

    def change_view(self, request, object_id, extra_context={}):
        obj = self.get_object(request, unquote(object_id))
        has_traceback = ENHANCED_TRACEBACKS and 'exc' in obj.data
        show_traceback = has_traceback and 'raw' not in request.GET
        if show_traceback:
            try:
                extra_context.update(self.get_traceback_context(request, obj))
            except:
                exc_info = sys.exc_info()
                logger.exception(exc_info[1])
                has_traceback = False
                import traceback
                extra_context['tb_error'] = traceback.format_exc()
        extra_context.update({
            'has_traceback': has_traceback,
            'show_traceback': show_traceback,
            'instance': obj,
        })
        return super(ErrorAdmin, self).change_view(request, object_id, extra_context)
        
    def get_traceback_context(self, request, obj):
        """
        Create a technical server error response. The last three arguments are
        the values returned from sys.exc_info() and friends.
        """
        try:
            module, args, frames = pickle.loads(base64.b64decode(obj.data['exc']).decode('zlib'))
        except:
            module, args, frames = pickle.loads(base64.b64decode(obj.data['exc']))
        obj.class_name = str(obj.class_name)

        # We fake the exception class due to many issues with imports/builtins/etc
        exc_type = type(obj.class_name, (Exception,), {})
        exc_value = exc_type(obj.message)

        exc_value.args = args
        
        fake_request = FakeRequest()
        fake_request.META = obj.data.get('META', {})
        fake_request.GET = obj.data.get('GET', {})
        fake_request.POST = obj.data.get('POST', {})
        fake_request.FILES = obj.data.get('FILES', {})
        fake_request.COOKIES = obj.data.get('COOKIES', {})
        fake_request.url = obj.url
        if obj.url:
            fake_request.path_info = '/' + obj.url.split('/', 3)[-1]
        else:
            fake_request.path_info = ''

        reporter = ImprovedExceptionReporter(fake_request, exc_type, exc_value, frames)
        html = reporter.get_traceback_html()
        
        return {
            'error_body': mark_safe(html),
        }

admin.site.register(ErrorBatch, ErrorBatchAdmin)
admin.site.register(Error, ErrorAdmin)

########NEW FILE########
__FILENAME__ = feeds
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.utils import feedgenerator
from django.utils.translation import ugettext_lazy as _

from djangodblog.models import Error, ErrorBatch

import logging

class ErrorFeed(object):
    def __call__(self, request):
        feed_dict = {
            'title': self.get_title(request),
            'link': request.build_absolute_uri(self.get_link(request)),
            'description': '',
            'language': u'en',
            'feed_url': request.build_absolute_uri(),
        }
        feed = feedgenerator.Rss201rev2Feed(**feed_dict)

        qs = self.get_query_set(request)

        for obj in qs[0:10]:
            link = self.get_item_url(request, obj)
            if link:
                link = request.build_absolute_uri(link)
            feed.add_item(
                title=str(obj or ''),
                link=link,
                description=obj.description() or '',
                pubdate=self.get_item_date(request, obj) or '',
            )

        return HttpResponse(feed.writeString('utf-8'), mimetype='application/xml')

    def get_title(self, request):
        return _('log messages')

    def get_link(self, request):
        return reverse('admin:djangodblog_error_changelist')

    def get_model(self, request):
        return Error

    def get_query_set(self, request):
        qs = self.get_model(request).objects.all().order_by(self.get_order_field(request))
        if request.GET.get('level') > 0:
            qs = qs.filter(level__gte=request.GET['level'])
        elif request.GET.get('server_name'):
            qs = qs.filter(server_name=request.GET['server_name'])
        elif request.GET.get('logger'):
            qs = qs.filter(logger=request.GET['logger'])
        return qs

    def get_order_field(self, request):
        return '-datetime'

    def get_item_url(self, request, obj):
        return reverse('admin:djangodblog_error_change', args=[obj.pk])

    def get_item_date(self, request, obj):
        return obj.datetime

class SummaryFeed(ErrorFeed):
    def get_title(self, request):
        return _('log summaries')

    def get_link(self, request):
        return reverse('admin:djangodblog_errorbatch_changelist')

    def get_model(self, request):
        return ErrorBatch

    def get_query_set(self, request):
        qs = super(SummaryFeed, self).get_query_set(request)
        return qs.filter(status=0)

    def get_order_field(self, request):
        return '-last_seen'

    def get_item_url(self, request, obj):
        return reverse('admin:djangodblog_errorbatch_change', args=[obj.pk])

    def get_item_date(self, request, obj):
        return obj.last_seen
########NEW FILE########
__FILENAME__ = handlers
import logging

class DBLogHandler(logging.Handler):
    def emit(self, record):
        from djangodblog.models import Error

        Error.objects.create_from_record(record)
########NEW FILE########
__FILENAME__ = helpers
from django.conf import settings
from django.template import (Template, Context, TemplateDoesNotExist,
    TemplateSyntaxError)
from django.utils.encoding import smart_unicode
from django.utils.hashcompat import md5_constructor
from django.views.debug import ExceptionReporter

class ImprovedExceptionReporter(ExceptionReporter):
    def __init__(self, request, exc_type, exc_value, frames):
        ExceptionReporter.__init__(self, request, exc_type, exc_value, None)
        self.frames = frames

    def get_traceback_frames(self):
        return self.frames

    def get_traceback_html(self):
        "Return HTML code for traceback."

        if issubclass(self.exc_type, TemplateDoesNotExist):
            self.template_does_not_exist = True
        if (settings.TEMPLATE_DEBUG and hasattr(self.exc_value, 'source') and
            isinstance(self.exc_value, TemplateSyntaxError)):
            self.get_template_exception_info()

        frames = self.get_traceback_frames()

        unicode_hint = ''
        if issubclass(self.exc_type, UnicodeError):
            start = getattr(self.exc_value, 'start', None)
            end = getattr(self.exc_value, 'end', None)
            if start is not None and end is not None:
                unicode_str = self.exc_value.args[1]
                unicode_hint = smart_unicode(unicode_str[max(start-5, 0):min(end+5, len(unicode_str))], 'ascii', errors='replace')
        t = Template(TECHNICAL_500_TEMPLATE, name='Technical 500 template')
        c = Context({
            'exception_type': self.exc_type.__name__,
            'exception_value': smart_unicode(self.exc_value, errors='replace'),
            'unicode_hint': unicode_hint,
            'frames': frames,
            'lastframe': frames[-1],
            'request': self.request,
            'template_info': self.template_info,
            'template_does_not_exist': self.template_does_not_exist,
        })
        return t.render(c)

def construct_checksum(error):
    checksum = md5_constructor(str(error.level))
    checksum.update(error.class_name or '')
    message = error.traceback or error.message
    if isinstance(message, unicode):
        message = message.encode('utf-8', 'replace')
    checksum.update(message)
    return checksum.hexdigest()

TECHNICAL_500_TEMPLATE = """
<div id="summary">
  <h1>{{ exception_type }} at {{ request.path_info|escape }}</h1>
  <pre class="exception_value">{{ exception_value|escape }}</pre>
  <table class="meta">
    <tr>
      <th>Request Method:</th>
      <td>{{ request.META.REQUEST_METHOD }}</td>
    </tr>
    <tr>
      <th>Request URL:</th>
      <td>{{ request.build_absolute_uri|escape }}</td>
    </tr>
    <tr>
      <th>Exception Type:</th>
      <td>{{ exception_type }}</td>
    </tr>
    <tr>
      <th>Exception Value:</th>
      <td><pre>{{ exception_value|escape }}</pre></td>
    </tr>
    <tr>
      <th>Exception Location:</th>
      <td>{{ lastframe.filename|escape }} in {{ lastframe.function|escape }}, line {{ lastframe.lineno }}</td>
    </tr>
  </table>
</div>
{% if unicode_hint %}
<div id="unicode-hint">
    <h2>Unicode error hint</h2>
    <p>The string that could not be encoded/decoded was: <strong>{{ unicode_hint|escape }}</strong></p>
</div>
{% endif %}
{% if template_info %}
<div id="template">
   <h2>Template error</h2>
   <p>In template <code>{{ template_info.name }}</code>, error at line <strong>{{ template_info.line }}</strong></p>
   <h3>{{ template_info.message }}</h3>
   <table class="source{% if template_info.top %} cut-top{% endif %}{% ifnotequal template_info.bottom template_info.total %} cut-bottom{% endifnotequal %}">
   {% for source_line in template_info.source_lines %}
   {% ifequal source_line.0 template_info.line %}
       <tr class="error"><th>{{ source_line.0 }}</th>
       <td>{{ template_info.before }}<span class="specific">{{ template_info.during }}</span>{{ template_info.after }}</td></tr>
   {% else %}
      <tr><th>{{ source_line.0 }}</th>
      <td>{{ source_line.1 }}</td></tr>
   {% endifequal %}
   {% endfor %}
   </table>
</div>
{% endif %}
<div id="traceback">
  <h2>Traceback <span class="commands"><a href="#" onclick="return switchPastebinFriendly(this);">Switch to copy-and-paste view</a></span></h2>
  {% autoescape off %}
  <div id="browserTraceback">
    <ul class="traceback">
      {% for frame in frames %}
        <li class="frame">
          <code>{{ frame.filename|escape }}</code> in <code>{{ frame.function|escape }}</code>

          {% if frame.context_line %}
            <div class="context" id="c{{ frame.id }}">
              {% if frame.pre_context %}
                <ol start="{{ frame.pre_context_lineno }}" class="pre-context" id="pre{{ frame.id }}">{% for line in frame.pre_context %}<li onclick="toggle('pre{{ frame.id }}', 'post{{ frame.id }}')">{{ line|escape }}</li>{% endfor %}</ol>
              {% endif %}
              <ol start="{{ frame.lineno }}" class="context-line"><li onclick="toggle('pre{{ frame.id }}', 'post{{ frame.id }}')">{{ frame.context_line|escape }} <span>...</span></li></ol>
              {% if frame.post_context %}
                <ol start='{{ frame.lineno|add:"1" }}' class="post-context" id="post{{ frame.id }}">{% for line in frame.post_context %}<li onclick="toggle('pre{{ frame.id }}', 'post{{ frame.id }}')">{{ line|escape }}</li>{% endfor %}</ol>
              {% endif %}
            </div>
          {% endif %}

          {% if frame.vars %}
            <div class="commands">
                <a href="#" onclick="return varToggle(this, '{{ frame.id }}')"><span>&#x25b6;</span> Local vars</a>
            </div>
            <table class="vars" id="v{{ frame.id }}">
              <thead>
                <tr>
                  <th>Variable</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {% for var in frame.vars|dictsort:"0" %}
                  <tr>
                    <td>{{ var.0|escape }}</td>
                    <td class="code"><div>{{ var.1|pprint|escape }}</div></td>
                  </tr>
                {% endfor %}
              </tbody>
            </table>
          {% endif %}
        </li>
      {% endfor %}
    </ul>
  </div>
  {% endautoescape %}
  <div id="pastebinTraceback" class="pastebin">
    <textarea id="traceback_area" cols="140" rows="25">
Environment:

{% if request.META %}Request Method: {{ request.META.REQUEST_METHOD }}{% endif %}
Request URL: {{ request.build_absolute_uri|escape }}
Python Version: {{ sys_version_info }}

{% if template_does_not_exist %}Template Loader Error: (Unavailable in db-log)
{% endif %}{% if template_info %}
Template error:
In template {{ template_info.name }}, error at line {{ template_info.line }}
   {{ template_info.message }}{% for source_line in template_info.source_lines %}{% ifequal source_line.0 template_info.line %}
   {{ source_line.0 }} : {{ template_info.before }} {{ template_info.during }} {{ template_info.after }}
{% else %}
   {{ source_line.0 }} : {{ source_line.1 }}
{% endifequal %}{% endfor %}{% endif %}
Traceback:
{% for frame in frames %}File "{{ frame.filename|escape }}" in {{ frame.function|escape }}
{% if frame.context_line %}  {{ frame.lineno }}. {{ frame.context_line|escape }}{% endif %}
{% endfor %}
Exception Type: {{ exception_type|escape }} at {{ request.path_info|escape }}
Exception Value: {{ exception_value|escape }}
</textarea>
  </div>
</div>
{% if request %}
<div id="requestinfo">
  <h2>Request information</h2>

  <h3 id="get-info">GET</h3>
  {% if request.GET %}
    <table class="req">
      <thead>
        <tr>
          <th>Variable</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        {% for var in request.GET.items %}
          <tr>
            <td>{{ var.0 }}</td>
            <td class="code"><div>{{ var.1|pprint }}</div></td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p>No GET data</p>
  {% endif %}

  <h3 id="post-info">POST</h3>
  {% if request.POST %}
    <table class="req">
      <thead>
        <tr>
          <th>Variable</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        {% for var in request.POST.items %}
          <tr>
            <td>{{ var.0 }}</td>
            <td class="code"><div>{{ var.1|pprint }}</div></td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p>No POST data</p>
  {% endif %}

  <h3 id="cookie-info">COOKIES</h3>
  {% if request.COOKIES %}
    <table class="req">
      <thead>
        <tr>
          <th>Variable</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        {% for var in request.COOKIES.items %}
          <tr>
            <td>{{ var.0 }}</td>
            <td class="code"><div>{{ var.1|pprint }}</div></td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p>No cookie data</p>
  {% endif %}

  <h3 id="meta-info">META</h3>
  {% if request.META %}
  <table class="req">
    <thead>
      <tr>
        <th>Variable</th>
        <th>Value</th>
      </tr>
    </thead>
    <tbody>
      {% for var in request.META.items|dictsort:"0" %}
        <tr>
          <td>{{ var.0 }}</td>
          <td class="code"><div>{{ var.1|pprint }}</div></td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
    <p>No META data</p>
  {% endif %}
</div>
{% endif %}
"""
########NEW FILE########
__FILENAME__ = cleanup_dblog
from django.core.management.base import CommandError, BaseCommand

from djangodblog.models import Error, ErrorBatch

from optparse import make_option

import datetime

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--days', action='store', dest='days'),
        make_option('--logger', action='store', dest='logger')
    )
    
    help = 'Cleans up old entries in the log.'

    def handle(self, *args, **options):
        ts = datetime.datetime.now() - datetime.timedelta(days=options.get('days', 30))
        
        base_kwargs = {}
        if options.get('logger'):
            base_kwargs['logger'] = options['logger']
        
        ErrorBatch.objects.filter(last_seen__lte=ts, **base_kwargs).delete()
        Error.objects.filter(datetime__lte=ts, **base_kwargs).delete()
########NEW FILE########
__FILENAME__ = manager
# Multi-db support based on http://www.eflorenzano.com/blog/post/easy-multi-database-support-django/
# TODO: is there a way to use the traceback module based on an exception variable?

import traceback as traceback_mod
import logging
import socket
import warnings
import datetime
import django
import base64
import sys
try:
    import cPickle as pickle
except ImportError:
    import pickle

from django.core.cache import cache
from django.db import models
from django.utils.encoding import smart_unicode
from django.views.debug import ExceptionReporter

from djangodblog import settings
from djangodblog.helpers import construct_checksum

assert not settings.DATABASE_USING or django.VERSION >= (1, 2), 'The `DBLOG_DATABASE_USING` setting requires Django >= 1.2'

logger = logging.getLogger('dblog')

class DBLogManager(models.Manager):
    use_for_related_fields = True

    def get_query_set(self):
        qs = super(DBLogManager, self).get_query_set()
        if settings.DATABASE_USING:
            qs = qs.using(settings.DATABASE_USING)
        return qs

    def _create(self, **defaults):
        from models import Error, ErrorBatch
        
        URL_MAX_LENGTH = Error._meta.get_field_by_name('url')[0].max_length
        
        server_name = socket.gethostname()
        class_name  = defaults.pop('class_name', None)
        
        data = defaults.pop('data', {}) or {}
        if defaults.get('url'):
            data['url'] = defaults['url']
            defaults['url'] = defaults['url'][:URL_MAX_LENGTH]

        instance = Error(
            class_name=class_name,
            server_name=server_name,
            data=data,
            **defaults
        )
        instance.checksum = construct_checksum(instance)
        
        if settings.THRASHING_TIMEOUT and settings.THRASHING_LIMIT:
            cache_key = 'djangodblog:%s:%s' % (instance.class_name, instance.checksum)
            added = cache.add(cache_key, 1, settings.THRASHING_TIMEOUT)
            if not added and cache.incr(cache_key) > settings.THRASHING_LIMIT:
                return

        try:
            instance.save()
            batch, created = ErrorBatch.objects.get_or_create(
                class_name = class_name,
                server_name = server_name,
                checksum = instance.checksum,
                defaults = defaults
            )
            if not created:
                ErrorBatch.objects.filter(pk=batch.pk).update(
                    times_seen=models.F('times_seen') + 1,
                    status=0,
                    last_seen=datetime.datetime.now(),
                )
        except Exception, exc:
            try:
                logger.exception(u'Unable to process log entry: %s' % (exc,))
            except Exception, exc:
                warnings.warn(u'Unable to process log entry: %s' % (exc,))
        else:
            return instance
    
    def create_from_record(self, record, **kwargs):
        """
        Creates an error log for a `logging` module `record` instance.
        """
        for k in ('url', 'data'):
            if k not in kwargs:
                kwargs[k] = record.__dict__.get(k)
        kwargs.update({
            'logger': record.name,
            'level': record.levelno,
            'message': record.getMessage(),
        })
        if record.exc_info:
            return self.create_from_exception(*record.exc_info[1:2], **kwargs)

        return self._create(
            traceback=record.exc_text,
            **kwargs
        )

    def create_from_text(self, message, **kwargs):
        """
        Creates an error log for from ``type`` and ``message``.
        """
        return self._create(
            message=message,
            **kwargs
        )

    def create_from_exception(self, exception=None, traceback=None, **kwargs):
        """
        Creates an error log from an exception.
        """
        if not exception:
            exc_type, exc_value, traceback = sys.exc_info()
        elif not traceback:
            warnings.warn('Using just the ``exception`` argument is deprecated, send ``traceback`` in addition.', DeprecationWarning)
            exc_type, exc_value, traceback = sys.exc_info()
        else:
            exc_type = exception.__class__
            exc_value = exception

        def to_unicode(f):
            if isinstance(f, dict):
                nf = dict()
                for k, v in f.iteritems():
                    nf[str(k)] = to_unicode(v)
                f = nf
            elif isinstance(f, (list, tuple)):
                f = [to_unicode(f) for f in f]
            else:
                try:
                    f = smart_unicode(f)
                except (UnicodeEncodeError, UnicodeDecodeError):
                    f = '(Error decoding value)'
            return f

        reporter = ExceptionReporter(None, exc_type, exc_value, traceback)
        frames = reporter.get_traceback_frames()

        data = kwargs.pop('data', {}) or {}
        data['exc'] = base64.b64encode(pickle.dumps(map(to_unicode, [exc_type.__class__.__module__, exc_value.args, frames])).encode('zlib'))

        tb_message = '\n'.join(traceback_mod.format_exception(exc_type, exc_value, traceback))

        kwargs.setdefault('message', to_unicode(exc_value))

        return self._create(
            class_name=exc_type.__name__,
            traceback=tb_message,
            data=data,
            **kwargs
        )

class ErrorBatchManager(DBLogManager):
    def get_by_natural_key(self, logger, server_name, checksum):
        return self.get(logger=logger, server_name=server_name, checksum=checksum)
########NEW FILE########
__FILENAME__ = middleware
import warnings

__all__ = ('DBLogMiddleware',)

class DBLogMiddleware(object):
    """We now use signals"""
    def process_exception(self, request, exception):
        warnings.warn("DBLogMiddleware is no longer used.", DeprecationWarning)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding model 'ErrorBatch'
        db.create_table('djangodblog_errorbatch', (
            ('status', self.gf('django.db.models.fields.PositiveIntegerField')(default=0, db_column='is_resolved')),
            ('first_seen', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('server_name', self.gf('django.db.models.fields.CharField')(max_length=128, db_index=True)),
            ('level', self.gf('django.db.models.fields.PositiveIntegerField')(default=40, db_index=True, blank=True)),
            ('class_name', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=128, null=True, blank=True)),
            ('checksum', self.gf('django.db.models.fields.CharField')(max_length=32, db_index=True)),
            ('times_seen', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('traceback', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('logger', self.gf('django.db.models.fields.CharField')(default='root', max_length=64, db_index=True, blank=True)),
            ('message', self.gf('django.db.models.fields.TextField')()),
            ('last_seen', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal('djangodblog', ['ErrorBatch'])

        # Adding unique constraint on 'ErrorBatch', fields ['logger', 'server_name', 'checksum']
        db.create_unique('djangodblog_errorbatch', ['logger', 'server_name', 'checksum'])

        # Adding model 'Error'
        db.create_table('djangodblog_error', (
            ('server_name', self.gf('django.db.models.fields.CharField')(max_length=128, db_index=True)),
            ('level', self.gf('django.db.models.fields.PositiveIntegerField')(default=40, db_index=True, blank=True)),
            ('class_name', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
            ('traceback', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('logger', self.gf('django.db.models.fields.CharField')(default='root', max_length=64, db_index=True, blank=True)),
            ('datetime', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('data', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('message', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('djangodblog', ['Error'])
    
    
    def backwards(self, orm):
        
        # Deleting model 'ErrorBatch'
        db.delete_table('djangodblog_errorbatch')

        # Removing unique constraint on 'ErrorBatch', fields ['logger', 'server_name', 'checksum']
        db.delete_unique('djangodblog_errorbatch', ['logger', 'server_name', 'checksum'])

        # Deleting model 'Error'
        db.delete_table('djangodblog_error')
    
    
    models = {
        'djangodblog.error': {
            'Meta': {'object_name': 'Error'},
            'class_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'default': '40', 'db_index': 'True', 'blank': 'True'}),
            'logger': ('django.db.models.fields.CharField', [], {'default': "'root'", 'max_length': '64', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'server_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        'djangodblog.errorbatch': {
            'Meta': {'unique_together': "(('logger', 'server_name', 'checksum'),)", 'object_name': 'ErrorBatch'},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '32', 'db_index': 'True'}),
            'class_name': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'first_seen': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_seen': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'default': '40', 'db_index': 'True', 'blank': 'True'}),
            'logger': ('django.db.models.fields.CharField', [], {'default': "'root'", 'max_length': '64', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'server_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'db_column': "'is_resolved'"}),
            'times_seen': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['djangodblog']

########NEW FILE########
__FILENAME__ = 0002_update_indexes
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding index on 'Error', fields ['class_name']
        db.create_index('djangodblog_error', ['class_name'])

        # Adding index on 'Error', fields ['datetime']
        db.create_index('djangodblog_error', ['datetime'])

        # Adding index on 'ErrorBatch', fields ['first_seen']
        db.create_index('djangodblog_errorbatch', ['first_seen'])

        # Adding index on 'ErrorBatch', fields ['last_seen']
        db.create_index('djangodblog_errorbatch', ['last_seen'])
    
    
    def backwards(self, orm):
        
        # Removing index on 'Error', fields ['class_name']
        db.delete_index('djangodblog_error', ['class_name'])

        # Removing index on 'Error', fields ['datetime']
        db.delete_index('djangodblog_error', ['datetime'])

        # Removing index on 'ErrorBatch', fields ['first_seen']
        db.delete_index('djangodblog_errorbatch', ['first_seen'])

        # Removing index on 'ErrorBatch', fields ['last_seen']
        db.delete_index('djangodblog_errorbatch', ['last_seen'])
    
    
    models = {
        'djangodblog.error': {
            'Meta': {'object_name': 'Error'},
            'class_name': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'default': '40', 'db_index': 'True', 'blank': 'True'}),
            'logger': ('django.db.models.fields.CharField', [], {'default': "'root'", 'max_length': '64', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'server_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        'djangodblog.errorbatch': {
            'Meta': {'unique_together': "(('logger', 'server_name', 'checksum'),)", 'object_name': 'ErrorBatch'},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '32', 'db_index': 'True'}),
            'class_name': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'first_seen': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_seen': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'default': '40', 'db_index': 'True', 'blank': 'True'}),
            'logger': ('django.db.models.fields.CharField', [], {'default': "'root'", 'max_length': '64', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'server_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'db_column': "'is_resolved'"}),
            'times_seen': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['djangodblog']

########NEW FILE########
__FILENAME__ = 0003_add_error_checksum
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Error.checksum'
        db.add_column('djangodblog_error', 'checksum', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, db_index=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Error.checksum'
        db.delete_column('djangodblog_error', 'checksum')


    models = {
        'djangodblog.error': {
            'Meta': {'object_name': 'Error'},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'db_index': 'True'}),
            'class_name': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'default': '40', 'db_index': 'True', 'blank': 'True'}),
            'logger': ('django.db.models.fields.CharField', [], {'default': "'root'", 'max_length': '64', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'server_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        'djangodblog.errorbatch': {
            'Meta': {'unique_together': "(('logger', 'server_name', 'checksum'),)", 'object_name': 'ErrorBatch'},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '32', 'db_index': 'True'}),
            'class_name': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'first_seen': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_seen': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'default': '40', 'db_index': 'True', 'blank': 'True'}),
            'logger': ('django.db.models.fields.CharField', [], {'default': "'root'", 'max_length': '64', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'server_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'db_column': "'is_resolved'"}),
            'times_seen': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['djangodblog']

########NEW FILE########
__FILENAME__ = 0004_fill_error_checksums
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."

        from djangodblog.helpers import construct_checksum

        for e in orm.Error.objects.all():
            orm.Error.objects.filter(pk=e.pk).update(checksum=construct_checksum(e))

        for e in orm.ErrorBatch.objects.all():
            orm.ErrorBatch.objects.filter(pk=e.pk).update(checksum=construct_checksum(e))

        
    def backwards(self, orm):
        "Write your backwards methods here."


    models = {
        'djangodblog.error': {
            'Meta': {'object_name': 'Error'},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'db_index': 'True'}),
            'class_name': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'default': '40', 'db_index': 'True', 'blank': 'True'}),
            'logger': ('django.db.models.fields.CharField', [], {'default': "'root'", 'max_length': '64', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'server_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        'djangodblog.errorbatch': {
            'Meta': {'unique_together': "(('logger', 'server_name', 'checksum'),)", 'object_name': 'ErrorBatch'},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '32', 'db_index': 'True'}),
            'class_name': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'first_seen': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_seen': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'default': '40', 'db_index': 'True', 'blank': 'True'}),
            'logger': ('django.db.models.fields.CharField', [], {'default': "'root'", 'max_length': '64', 'db_index': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'server_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'db_column': "'is_resolved'"}),
            'times_seen': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['djangodblog']

########NEW FILE########
__FILENAME__ = models
from django.conf import settings as dj_settings
from django.db import models, transaction
from django.core.signals import got_request_exception
from django.http import Http404
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _

from djangodblog import settings
from djangodblog.manager import DBLogManager, ErrorBatchManager
from djangodblog.utils import JSONDictField
from djangodblog.helpers import construct_checksum

import datetime
import warnings
import logging
import sys

try:
    from idmapper.models import SharedMemoryModel as Model
except ImportError:
    Model = models.Model

logger = logging.getLogger('dblog')

__all__ = ('Error', 'ErrorBatch')

LOG_LEVELS = (
    (logging.INFO, _('info')),
    (logging.WARNING, _('warning')),
    (logging.DEBUG, _('debug')),
    (logging.ERROR, _('error')),
    (logging.FATAL, _('fatal')),
)

STATUS_LEVELS = (
    (0, _('unresolved')),
    (1, _('resolved')),
)

class ErrorBase(Model):
    logger          = models.CharField(max_length=64, blank=True, default='root', db_index=True)
    class_name      = models.CharField(_('type'), max_length=128, blank=True, null=True, db_index=True)
    level           = models.PositiveIntegerField(choices=LOG_LEVELS, default=logging.ERROR, blank=True, db_index=True)
    message         = models.TextField()
    traceback       = models.TextField(blank=True, null=True)
    url             = models.URLField(verify_exists=False, null=True, blank=True)
    server_name     = models.CharField(max_length=128, db_index=True)
    checksum        = models.CharField(max_length=32, db_index=True)

    objects         = DBLogManager()

    class Meta:
        abstract = True

    def get_absolute_url(self):
        return self.url
    
    def shortened_url(self):
        if not self.url:
            return _('no data')
        url = self.url
        if len(url) > 60:
            url = url[:60] + '...'
        return url
    shortened_url.short_description = _('url')
    shortened_url.admin_order_field = 'url'
    
    def full_url(self):
        return self.data.get('url') or self.url
    full_url.short_description = _('url')
    full_url.admin_order_field = 'url'
    
    def error(self):
        message = smart_unicode(self.message)
        if len(message) > 100:
            message = message[:97] + '...'
        if self.class_name:
            return "%s: %s" % (self.class_name, message)
        return message
    error.short_description = _('error')

    def description(self):
        return self.traceback or ''
    description.short_description = _('description')

class ErrorBatch(ErrorBase):
    # XXX: We're using the legacy column for `is_resolved` for status
    status          = models.PositiveIntegerField(default=0, db_column="is_resolved", choices=STATUS_LEVELS)
    times_seen      = models.PositiveIntegerField(default=1)
    last_seen       = models.DateTimeField(default=datetime.datetime.now, db_index=True)
    first_seen      = models.DateTimeField(default=datetime.datetime.now, db_index=True)

    objects         = ErrorBatchManager()

    class Meta:
        unique_together = (('logger', 'server_name', 'checksum'),)
        verbose_name_plural = _('summaries')
        verbose_name = _('summary')
    
    def __unicode__(self):
        return "(%s) %s: %s" % (self.times_seen, self.class_name, self.error())

    def natural_key(self):
        return (self.logger, self.server_name, self.checksum)

    @staticmethod
    @transaction.commit_on_success
    def handle_exception(sender, request=None, **kwargs):
        try:
            exc_type, exc_value, traceback = sys.exc_info()
        
            if not settings.CATCH_404_ERRORS \
                    and issubclass(exc_type, Http404):
                return

            if dj_settings.DEBUG or getattr(exc_type, 'skip_dblog', False):
                return

            if transaction.is_dirty():
                transaction.rollback()

            if request:
                data = dict(
                    META=request.META,
                    POST=request.POST,
                    GET=request.GET,
                    COOKIES=request.COOKIES,
                )
            else:
                data = dict()

            extra = dict(
                url=request and request.build_absolute_uri() or None,
                data=data,
            )

            if settings.USE_LOGGING:
                logging.getLogger('dblog').critical(exc_value, exc_info=sys.exc_info(), extra=extra)
            else:
                Error.objects.create_from_exception(**extra)
        except Exception, exc:
            try:
                logger.exception(u'Unable to process log entry: %s' % (exc,))
            except Exception, exc:
                warnings.warn(u'Unable to process log entry: %s' % (exc,))

class Error(ErrorBase):
    datetime        = models.DateTimeField(default=datetime.datetime.now, db_index=True)
    data            = JSONDictField(blank=True, null=True)

    class Meta:
        verbose_name = _('message')
        verbose_name_plural = _('messages')

    def __unicode__(self):
        return "%s: %s" % (self.class_name, smart_unicode(self.message))

    def save(self, *args, **kwargs):
        if not self.checksum:
            self.checksum = construct_checksum(self)
        super(Error, self).save(*args, **kwargs)

   
got_request_exception.connect(ErrorBatch.handle_exception)
########NEW FILE########
__FILENAME__ = routers
from djangodblog import settings

class DBLogRouter(object):
    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'djangodblog':
            return settings.DATABASE_USING

    def db_for_read(self, model, **hints):
        return self.db_for_write(model, **hints)

    def allow_syncdb(self, db, model):
        dblog_db = settings.DATABASE_USING
        if not dblog_db:
            return None
        if model._meta.app_label == 'djangodblog' and db != dblog_db:
            return False
########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

CATCH_404_ERRORS = getattr(settings, 'DBLOG_CATCH_404_ERRORS', False)

ENHANCED_TRACEBACKS = getattr(settings, 'DBLOG_ENHANCED_TRACEBACKS', True)

DATABASE_USING = getattr(settings, 'DBLOG_DATABASE_USING', None)

USE_LOGGING = getattr(settings, 'DBLOG_USE_LOGGING', False)

THRASHING_TIMEOUT = getattr(settings, 'DBLOG_THRASHING_TIMEOUT', 60)
THRASHING_LIMIT = getattr(settings, 'DBLOG_THRASHING_LIMIT', 10)

########NEW FILE########
__FILENAME__ = dblog_admin
from django.contrib.admin.templatetags.admin_list import result_headers, items_for_result
from django import template
register = template.Library()

def better_results(cl):
    for res in cl.result_list:
        cells = list(items_for_result(cl, res, None))
        yield dict(
            cells=cells,
            instance=res,
            num_real_cells=len(cells) - 1,
        )

def result_list(cl):
    return {'cl': cl,
            'result_headers': list(result_headers(cl)),
            'results': list(better_results(cl))}
result_list = register.inclusion_tag("admin/djangodblog/errorbatch/change_list_results.html")(result_list)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from djangodblog.utils import JSONDictField

class JSONDictModel(models.Model):
    data = JSONDictField(blank=True, null=True)
    
    def __unicode__(self):
        return unicode(self.data)

class DuplicateKeyModel(models.Model):
    foo = models.IntegerField(unique=True, default=1)
    
    def __unicode__(self):
        return unicode(self.foo)
    
########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-

from django.core.handlers.wsgi import WSGIRequest
from django.core.urlresolvers import reverse
from django.core.signals import got_request_exception
from django.test.client import Client
from django.test import TestCase
from django.utils.encoding import smart_unicode

from djangodblog.middleware import DBLogMiddleware
from djangodblog.models import Error, ErrorBatch
from djangodblog.tests.models import JSONDictModel, DuplicateKeyModel
from djangodblog import settings

import logging
import sys

def conditional_on_module(module):
    def wrapped(func):
        def inner(self, *args, **kwargs):
            try:
                __import__(module)
            except ImportError:
                print "Skipping test: %s.%s" % (self.__class__.__name__, func.__name__)
            else:
                return func(self, *args, **kwargs)
        return inner
    return wrapped

class RequestFactory(Client):
    # Used to generate request objects.
    def request(self, **request):
        environ = {
            'HTTP_COOKIE': self.cookies,
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }
        environ.update(self.defaults)
        environ.update(request)
        return WSGIRequest(environ)
 
RF = RequestFactory()

class JSONDictTestCase(TestCase):
    def testField(self):
        # Let's make sure the default value is correct
        instance = JSONDictModel()
        self.assertEquals(instance.data, {})
        
        instance = JSONDictModel.objects.create(data={'foo': 'bar'})
        self.assertEquals(instance.data.get('foo'), 'bar')
        
        instance = JSONDictModel.objects.get()
        self.assertEquals(instance.data.get('foo'), 'bar')

class DBLogTestCase(TestCase):
    def setUp(self):
        settings.DATABASE_USING = None
        self._handlers = None
        self._level = None
        settings.DEBUG = False
        self.logger = logging.getLogger('dblog')
        self.logger.addHandler(logging.StreamHandler())
    
    def tearDown(self):
        self.tearDownHandler()
        
    def setUpHandler(self):
        self.tearDownHandler()
        from djangodblog.handlers import DBLogHandler
        
        logger = logging.getLogger()
        self._handlers = logger.handlers
        self._level = logger.level

        for h in self._handlers:
            # TODO: fix this, for now, I don't care.
            logger.removeHandler(h)
    
        logger.setLevel(logging.DEBUG)
        dblog_handler = DBLogHandler()
        logger.addHandler(dblog_handler)
    
    def tearDownHandler(self):
        if self._handlers is None:
            return
        
        logger = logging.getLogger()
        logger.removeHandler(logger.handlers[0])
        for h in self._handlers:
            logger.addHandler(h)
        
        logger.setLevel(self._level)
        self._handlers = None
        
    def testLogger(self):
        logger = logging.getLogger()
        
        Error.objects.all().delete()
        ErrorBatch.objects.all().delete()

        self.setUpHandler()

        logger.error('This is a test error')
        cur = (Error.objects.count(), ErrorBatch.objects.count())
        self.assertEquals(cur, (1, 1), 'Assumed logs failed to save. %s' % (cur,))
        last = Error.objects.all().order_by('-id')[0:1].get()
        self.assertEquals(last.logger, 'root')
        self.assertEquals(last.level, logging.ERROR)
        self.assertEquals(last.message, 'This is a test error')

        logger.warning('This is a test warning')
        cur = (Error.objects.count(), ErrorBatch.objects.count())
        self.assertEquals(cur, (2, 2), 'Assumed logs failed to save. %s' % (cur,))
        last = Error.objects.all().order_by('-id')[0:1].get()
        self.assertEquals(last.logger, 'root')
        self.assertEquals(last.level, logging.WARNING)
        self.assertEquals(last.message, 'This is a test warning')
        
        logger.error('This is a test error')
        cur = (Error.objects.count(), ErrorBatch.objects.count())
        self.assertEquals(cur, (3, 2), 'Assumed logs failed to save. %s' % (cur,))
        last = Error.objects.all().order_by('-id')[0:1].get()
        self.assertEquals(last.logger, 'root')
        self.assertEquals(last.level, logging.ERROR)
        self.assertEquals(last.message, 'This is a test error')
    
        logger = logging.getLogger('test')
        logger.info('This is a test info')
        cur = (Error.objects.count(), ErrorBatch.objects.count())
        self.assertEquals(cur, (4, 3), 'Assumed logs failed to save. %s' % (cur,))
        last = Error.objects.all().order_by('-id')[0:1].get()
        self.assertEquals(last.logger, 'test')
        self.assertEquals(last.level, logging.INFO)
        self.assertEquals(last.message, 'This is a test info')
        
        logger.info('This is a test info with a url', extra=dict(url='http://example.com'))
        cur = (Error.objects.count(), ErrorBatch.objects.count())
        self.assertEquals(cur, (5, 4), 'Assumed logs failed to save. %s' % (cur,))
        last = Error.objects.all().order_by('-id')[0:1].get()
        self.assertEquals(last.url, 'http://example.com')
        
        try:
            raise ValueError('This is a test ValueError')
        except ValueError:
            logger.info('This is a test info with an exception', exc_info=sys.exc_info())
            cur = (Error.objects.count(), ErrorBatch.objects.count())
            self.assertEquals(cur, (6, 5), 'Assumed logs failed to save. %s' % (cur,))
            last = Error.objects.all().order_by('-id')[0:1].get()
            self.assertEquals(last.class_name, 'ValueError')
            self.assertEquals(last.message, 'This is a test info with an exception')
            self.assertTrue(last.data.get('exc'))
    
        self.tearDownHandler()
    
    def testMiddleware(self):
        Error.objects.all().delete()
        ErrorBatch.objects.all().delete()
        
        request = RF.get("/", REMOTE_ADDR="127.0.0.1:8000")

        try:
            Error.objects.get(id=999999999)
        except Error.DoesNotExist, exc:
            ErrorBatch.handle_exception(request=request, sender=self)
        else:
            self.fail('Unable to create `Error` entry.')
        
        cur = (Error.objects.count(), ErrorBatch.objects.count())
        self.assertEquals(cur, (1, 1), 'Assumed logs failed to save. %s' % (cur,))
        last = Error.objects.all().order_by('-id')[0:1].get()
        self.assertEquals(last.logger, 'root')
        self.assertEquals(last.class_name, 'DoesNotExist')
        self.assertEquals(last.level, logging.ERROR)
        self.assertEquals(last.message, smart_unicode(exc))
        
    def testAPI(self):
        Error.objects.all().delete()
        ErrorBatch.objects.all().delete()

        try:
            Error.objects.get(id=999999989)
        except Error.DoesNotExist, exc:
            Error.objects.create_from_exception(exc)
        else:
            self.fail('Unable to create `Error` entry.')

        try:
            Error.objects.get(id=999999989)
        except Error.DoesNotExist, exc:
            error = Error.objects.create_from_exception()
            self.assertTrue(error.data.get('exc'))
        else:
            self.fail('Unable to create `Error` entry.')

        
        cur = (Error.objects.count(), ErrorBatch.objects.count())
        self.assertEquals(cur, (2, 2), 'Assumed logs failed to save. %s' % (cur,))
        last = Error.objects.all().order_by('-id')[0:1].get()
        self.assertEquals(last.logger, 'root')
        self.assertEquals(last.class_name, 'DoesNotExist')
        self.assertEquals(last.level, logging.ERROR)
        self.assertEquals(last.message, smart_unicode(exc))
        
        Error.objects.create_from_text('This is an error', level=logging.DEBUG)
        
        cur = (Error.objects.count(), ErrorBatch.objects.count())
        self.assertEquals(cur, (3, 3), 'Assumed logs failed to save. %s' % (cur,))
        last = Error.objects.all().order_by('-id')[0:1].get()
        self.assertEquals(last.logger, 'root')
        self.assertEquals(last.level, logging.DEBUG)
        self.assertEquals(last.message, 'This is an error')
        
    def testAlternateDatabase(self):
        settings.DATABASE_USING = 'default'
        
        Error.objects.all().delete()
        ErrorBatch.objects.all().delete()

        try:
            Error.objects.get(id=999999979)
        except Error.DoesNotExist, exc:
            Error.objects.create_from_exception(exc)
        else:
            self.fail('Unable to create `Error` entry.')
            
        cur = (Error.objects.count(), ErrorBatch.objects.count())
        self.assertEquals(cur, (1, 1), 'Assumed logs failed to save. %s' % (cur,))
        last = Error.objects.all().order_by('-id')[0:1].get()
        self.assertEquals(last.logger, 'root')
        self.assertEquals(last.class_name, 'DoesNotExist')
        self.assertEquals(last.level, logging.ERROR)
        self.assertEquals(last.message, smart_unicode(exc))

        settings.DATABASE_USING = None
    
    def testIncorrectUnicode(self):
        self.setUpHandler()
        
        cnt = Error.objects.count()
        value = 'רונית מגן'

        error = Error.objects.create_from_text(value)
        self.assertEquals(Error.objects.count(), cnt+1)
        self.assertEquals(error.message, value)

        logging.info(value)
        self.assertEquals(Error.objects.count(), cnt+2)

        x = JSONDictModel.objects.create(data={'value': value})
        logging.warn(x)
        self.assertEquals(Error.objects.count(), cnt+3)

        try:
            raise SyntaxError(value)
        except Exception, exc:
            logging.exception(exc)
            logging.info('test', exc_info=sys.exc_info())
        self.assertEquals(Error.objects.count(), cnt+5)
        
        self.tearDownHandler()

    def testCorrectUnicode(self):
        self.setUpHandler()
        
        cnt = Error.objects.count()
        value = 'רונית מגן'.decode('utf-8')

        error = Error.objects.create_from_text(value)
        self.assertEquals(Error.objects.count(), cnt+1)
        self.assertEquals(error.message, value)

        logging.info(value)
        self.assertEquals(Error.objects.count(), cnt+2)

        x = JSONDictModel.objects.create(data={'value': value})
        logging.warn(x)
        self.assertEquals(Error.objects.count(), cnt+3)

        try:
            raise SyntaxError(value)
        except Exception, exc:
            logging.exception(exc)
            logging.info('test', exc_info=sys.exc_info())
        self.assertEquals(Error.objects.count(), cnt+5)
        
        self.tearDownHandler()
    
    def testLongURLs(self):
        # Fix: #6 solves URLs > 200 characters
        error = Error.objects.create_from_text('hello world', url='a'*210)
        self.assertEquals(error.url, 'a'*200)
        self.assertEquals(error.data['url'], 'a'*210)
    
    def testUseLogging(self):
        Error.objects.all().delete()
        ErrorBatch.objects.all().delete()
        
        request = RF.get("/", REMOTE_ADDR="127.0.0.1:8000")

        try:
            Error.objects.get(id=999999999)
        except Error.DoesNotExist, exc:
            ErrorBatch.handle_exception(request=request, sender=self)
        else:
            self.fail('Expected an exception.')
        
        cur = (Error.objects.count(), ErrorBatch.objects.count())
        self.assertEquals(cur, (1, 1), 'Assumed logs failed to save. %s' % (cur,))
        last = Error.objects.all().order_by('-id')[0:1].get()
        self.assertEquals(last.logger, 'root')
        self.assertEquals(last.class_name, 'DoesNotExist')
        self.assertEquals(last.level, logging.ERROR)
        self.assertEquals(last.message, smart_unicode(exc))
        
        settings.USE_LOGGING = True
        
        logger = logging.getLogger('dblog')
        for h in logger.handlers:
            logger.removeHandler(h)
        logger.addHandler(logging.StreamHandler())
        
        try:
            Error.objects.get(id=999999999)
        except Error.DoesNotExist, exc:
            ErrorBatch.handle_exception(request=request, sender=self)
        else:
            self.fail('Expected an exception.')
        
        cur = (Error.objects.count(), ErrorBatch.objects.count())
        self.assertEquals(cur, (1, 1), 'Assumed logs failed to save. %s' % (cur,))
        
        settings.USE_LOGGING = False
    
    def testThrashing(self):
        settings.THRASHING_LIMIT = 10
        settings.THRASHING_TIMEOUT = 60
        
        Error.objects.all().delete()
        ErrorBatch.objects.all().delete()
        
        for i in range(0, 50):
            Error.objects.create_from_text('hi')
        
        self.assertEquals(Error.objects.count(), settings.THRASHING_LIMIT)
    
    def testSignals(self):
        Error.objects.all().delete()
        ErrorBatch.objects.all().delete()

        request = RF.get("/", REMOTE_ADDR="127.0.0.1:8000")

        try:
            Error.objects.get(id=999999999)
        except Error.DoesNotExist, exc:
            got_request_exception.send(sender=self.__class__, request=request)
        else:
            self.fail('Expected an exception.')
            
        cur = (Error.objects.count(), ErrorBatch.objects.count())
        self.assertEquals(cur, (1, 1), 'Assumed logs failed to save. %s' % (cur,))
        last = Error.objects.all().order_by('-id')[0:1].get()
        self.assertEquals(last.logger, 'root')
        self.assertEquals(last.class_name, 'DoesNotExist')
        self.assertEquals(last.level, logging.ERROR)
        self.assertEquals(last.message, smart_unicode(exc))        

    def testSignalsWithoutRequest(self):
        Error.objects.all().delete()
        ErrorBatch.objects.all().delete()

        request = RF.get("/", REMOTE_ADDR="127.0.0.1:8000")

        try:
            Error.objects.get(id=999999999)
        except Error.DoesNotExist, exc:
            got_request_exception.send(sender=self.__class__, request=None)
        else:
            self.fail('Expected an exception.')
            
        cur = (Error.objects.count(), ErrorBatch.objects.count())
        self.assertEquals(cur, (1, 1), 'Assumed logs failed to save. %s' % (cur,))
        last = Error.objects.all().order_by('-id')[0:1].get()
        self.assertEquals(last.logger, 'root')
        self.assertEquals(last.class_name, 'DoesNotExist')
        self.assertEquals(last.level, logging.ERROR)
        self.assertEquals(last.message, smart_unicode(exc))

    def testNoThrashing(self):
        prev = settings.THRASHING_LIMIT
        settings.THRASHING_LIMIT = 0
        
        Error.objects.all().delete()
        ErrorBatch.objects.all().delete()
        
        for i in range(0, 50):
            Error.objects.create_from_text('hi')
        
        self.assertEquals(Error.objects.count(), 50)

        settings.THRASHING_LIMIT = prev

    def testDatabaseError(self):
        from django.db import connection
        
        try:
            cursor = connection.cursor()
            cursor.execute("select foo")
        except:
            got_request_exception.send(sender=self.__class__)

        self.assertEquals(Error.objects.count(), 1)
        self.assertEquals(ErrorBatch.objects.count(), 1)

    def testIntegrityError(self):
        DuplicateKeyModel.objects.create()
        try:
            DuplicateKeyModel.objects.create()
        except:
            got_request_exception.send(sender=self.__class__)
        else:
            self.fail('Excepted an IntegrityError to be raised.')

        self.assertEquals(Error.objects.count(), 1)
        self.assertEquals(ErrorBatch.objects.count(), 1)

class DBLogViewsTest(TestCase):
    urls = 'djangodblog.tests.urls'
    
    def setUp(self):
        settings.DATABASE_USING = None
        self._handlers = None
        self._level = None
        settings.DEBUG = False
    
    def tearDown(self):
        self.tearDownHandler()
        
    def setUpHandler(self):
        self.tearDownHandler()
        from djangodblog.handlers import DBLogHandler
        
        logger = logging.getLogger()
        self._handlers = logger.handlers
        self._level = logger.level

        for h in self._handlers:
            # TODO: fix this, for now, I don't care.
            logger.removeHandler(h)
    
        logger.setLevel(logging.DEBUG)
        dblog_handler = DBLogHandler()
        logger.addHandler(dblog_handler)
    
    def tearDownHandler(self):
        if self._handlers is None:
            return
        
        logger = logging.getLogger()
        logger.removeHandler(logger.handlers[0])
        for h in self._handlers:
            logger.addHandler(h)
        
        logger.setLevel(self._level)
        self._handlers = None

    def testSignals(self):
        Error.objects.all().delete()
        ErrorBatch.objects.all().delete()

        self.assertRaises(Exception, self.client.get, '/')
        
        cur = (Error.objects.count(), ErrorBatch.objects.count())
        self.assertEquals(cur, (1, 1), 'Assumed logs failed to save. %s' % (cur,))
        last = Error.objects.all().order_by('-id')[0:1].get()
        self.assertEquals(last.logger, 'root')
        self.assertEquals(last.class_name, 'Exception')
        self.assertEquals(last.level, logging.ERROR)
        self.assertEquals(last.message, 'view exception')

class DBLogFeedsTest(TestCase):
    fixtures = ['djangodblog/tests/fixtures/feeds.json']
    urls = 'djangodblog.tests.urls'
    
    def testErrorFeed(self):
        response = self.client.get(reverse('dblog-feed-messages'))
        self.assertEquals(response.status_code, 200)
        self.assertTrue(response.content.startswith('<?xml version="1.0" encoding="utf-8"?>'))
        self.assertTrue('<link>http://testserver/admin/djangodblog/error/</link>' in response.content)
        self.assertTrue('<title>log messages</title>' in response.content)
        self.assertTrue('<link>http://testserver/admin/djangodblog/error/1/</link>' in response.content)
        self.assertTrue('<title>TypeError: exceptions must be old-style classes or derived from BaseException, not NoneType</title>' in response.content)

    def testSummaryFeed(self):
        response = self.client.get(reverse('dblog-feed-summaries'))
        self.assertEquals(response.status_code, 200)
        self.assertTrue(response.content.startswith('<?xml version="1.0" encoding="utf-8"?>'))
        self.assertTrue('<link>http://testserver/admin/djangodblog/errorbatch/</link>' in response.content)
        self.assertTrue('<title>log summaries</title>' in response.content)
        self.assertTrue('<link>http://testserver/admin/djangodblog/errorbatch/1/</link>' in response.content)
        self.assertTrue('<title>(1) TypeError: TypeError: exceptions must be old-style classes or derived from BaseException, not NoneType</title>' in response.content)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', 'djangodblog.tests.views.raise_exc', name='dblog-raise-exc'),
    url(r'', include('djangodblog.urls')),
)
########NEW FILE########
__FILENAME__ = views
def raise_exc(request):
    raise Exception('view exception')
########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import *
from django.utils.hashcompat import md5_constructor

from feeds import ErrorFeed, SummaryFeed

hashed_secret = md5_constructor(settings.SECRET_KEY).hexdigest()

urlpatterns = patterns('',
    url(r'feeds/%s/messages.xml' % hashed_secret, ErrorFeed(), name='dblog-feed-messages'),
    url(r'feeds/%s/summaries.xml' % hashed_secret, SummaryFeed(), name='dblog-feed-summaries'),
)

########NEW FILE########
__FILENAME__ = utils
from django.utils import simplejson as json
from django.utils.encoding import smart_unicode
from django.db import models
from django import forms
from django.core.serializers.json import DjangoJSONEncoder

import uuid

class BetterJSONEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return obj.hex
        elif not isinstance(obj, (basestring, tuple, list, dict, int, bool)):
            return unicode(obj)
        else:
            return super(BetterJSONEncoder, self).default(obj)

def json_dumps(value, **kwargs):
    return json.dumps(value, cls=BetterJSONEncoder, **kwargs)

class JSONDictWidget(forms.Textarea):
    def render(self, name, value, attrs=None):
        if not isinstance(value, basestring):
            value = json_dumps(value, indent=2)
        return super(JSONDictWidget, self).render(name, value, attrs)

class JSONDictFormField(forms.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['widget'] = kwargs.get('widget', JSONDictWidget)
        super(JSONDictFormField, self).__init__(*args, **kwargs)
 
    def clean(self, value):
        if not value: return
        try:
            return json.loads(value)
        except Exception, exc:
            raise forms.ValidationError(u'JSONDict decode error: %s' % (smart_unicode(exc),))

class JSONDictField(models.TextField):
    """
    Slightly different from a JSONField in the sense that the default
    value is a dictionary.
    """
    __metaclass__ = models.SubfieldBase
 
    def formfield(self, **kwargs):
        return super(JSONDictField, self).formfield(form_class=JSONDictFormField, **kwargs)
 
    def to_python(self, value):
        if isinstance(value, basestring) and value:
            value = json.loads(value)
        elif not value:
            return {}
        return value
 
    def get_db_prep_save(self, value):
        if value is None: return
        return json_dumps(value)
 
    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.TextField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)
########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys

from os.path import dirname, abspath

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASE_ENGINE='sqlite3',
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.admin',
            'django.contrib.sessions',

            # Included to fix Disqus' test Django which solves IntegrityError case
            'django.contrib.contenttypes',

            'djangodblog',

            # No fucking idea why I have to do this
            'djangodblog.tests',
        ],
        ROOT_URLCONF='',
    )

from django.test.simple import run_tests


def runtests(*test_args):
    if not test_args:
        test_args = ['djangodblog']
    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)
    failures = run_tests(test_args, verbosity=1, interactive=True)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])
########NEW FILE########
