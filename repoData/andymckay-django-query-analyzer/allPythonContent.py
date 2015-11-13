__FILENAME__ = decorators
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.utils import simplejson
from functools import wraps

def json_view(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        content = func(*args, **kwargs)
        response = HttpResponse(content_type="application/json")
        simplejson.dump(content, response)
        return response
    return wrapper

def html_view(template):
    def renderer(func):
        def wrapper(request, *args, **kw):
            output = func(request, *args, **kw)
            if isinstance(output, (list, tuple)):
                return render_to_response(output[1], output[0], RequestContext(request))
            elif isinstance(output, dict):
                return render_to_response(template, output, RequestContext(request))
            return output
        return wrapper
    return renderer

########NEW FILE########
__FILENAME__ = forms
from query_analyzer.shortcuts import list_models

from django import forms
#from django.contrib.admin.helpers import AdminForm
from django.conf import settings

class PythonForm(forms.Form):
    model = forms.ChoiceField(choices=list_models(), label="Choose a model")
    python = forms.CharField(label="Enter some python", required=False, 
        widget=forms.Textarea(attrs={"rows":"2"}))
    
def FieldsForm(model):
    form = type("FieldsForm", (forms.ModelForm,), dict(Meta=type("Meta", (object,), dict(model=model))))
    return form()
    

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = shortcuts
from django.conf import settings
from django.db import connections
from django.db.backends.sqlite3.base import DatabaseWrapper as sqlite3
from django.db.backends.postgresql_psycopg2.base import DatabaseWrapper as postgresql_psycopg2
from django.db.models import get_model as django_get_model
from django.db.models import get_models as django_get_models
from django.db.models.fields.related import ForeignKey

from itertools import chain
from query_analyzer.decorators import json_view

try:
    from pygments import highlight
    from pygments.lexers import PythonLexer, SqlLexer
    from pygments.formatters import HtmlFormatter
    has_pygments = True
except ImportError:
    has_pygments = False

class InvalidSQLError(Exception):
    def __init__(self, value):
        self.value = value
        
    def __str__(self):
        return repr(self.value)

class Analyzer(object):
    def explain(self, connection):
        cursor = connection.cursor()
        if isinstance(connection, postgresql_psycopg2):
            explain_sql = "EXPLAIN %s" % self.sql
        else:
            explain_sql = "EXPLAIN %sPLAN %s" % (isinstance(connection, sqlite3) and "QUERY " or "", self.sql)
        try:
            cursor.execute(explain_sql, self.params)
            explain_headers = [d[0] for d in cursor.description]
            explain_result = cursor.fetchall()
            sql = connection.ops.last_executed_query(cursor, self.sql, self.params),
        finally:
            cursor.close()
        return explain_headers, explain_result, sql

class AnalyzeSQL(Analyzer):
    def __init__(self, sql, params):
        self.sql = sql
        self.params = params
        
    def __call__(self):
        if not self.sql:
            context = {}
        else:
            if self.sql.lower().strip().startswith('select'):
                if self.params:
                    self.params = simplejson.loads(self.params)
                else:
                    self.params = {}

                connection = connections['default']
                cursor = connection.cursor()
                try:
                    cursor.execute(sql, params)
                    select_headers = [d[0] for d in cursor.description]
                    select_result = cursor.fetchall()
                finally:
                    cursor.close()

                explain_headers, explain_result, sql_result = _explain(connection)
                # not sure what to do with sql_result in this case...
                context = {
                    'select_result': select_result,
                    'explain_result': explain_result,
                    'sql': sql,
                    'duration': request.GET.get('duration', 0.0),
                    'select_headers': select_headers,
                    'explain_headers': explain_headers,
                }
            else:
                raise InvalidSQLError("Only 'select' queries are allowed.")

class AnalyzePython(Analyzer):
    def __init__(self, model, python):
        self.model = model
        self.manager = model.objects
        self.nice_python = self.python = "%s.objects.%s" % (model.__name__, python.strip())
        if has_pygments:
            self.nice_python = highlight(self.python, PythonLexer(), HtmlFormatter())
        try:
            self.queryset = eval(self.python, dict_models())
        except:
            raise SyntaxError
    
    def __call__(self):
        connection = connections[self.queryset.db]

        self.sql, self.params = self.queryset._as_sql(connection)
        headers, result, sql = self.explain(connection)

        nice_sql = "\n".join(sql)
        if has_pygments:
            nice_sql = highlight(nice_sql, SqlLexer(), HtmlFormatter())
        
        context = {
            'select_result': self.queryset.values_list(),
            'explain_result': result,
            'sql': sql,
            'nice_sql': nice_sql,
            'nice_python': self.nice_python,
            'duration': settings.DEBUG and connection.queries[-1]['time'] or 0.0,
            'select_headers': [f.name for f in self.model._meta.fields], #maybe local_fields is better.
            'explain_headers': headers,
        }
        return context
        

class AnalyzeQueryset(Analyzer):
    def __init__(self, model, manager, filters, excludes):
        self.model = model
        self.manager = manager
        self.filters = filters
        self.excludes = excludes
        self.sql = None
        self.params = None
        
    def __call__(self):
        queryset = manager.all()
    
        for filter in filters:
            queryset = queryset.filter(**filter)
    
        for exclude in excludes:
            queryset = queryset.exclude(**exclude)

        connection = connections[queryset.db]
        
        self.sql, self.params = queryset._as_sql(connection)
        headers, result, sql = _explain(connection)

        context = {
            'select_result': queryset.values_list(),
            'explain_result': result,
            'sql': sql,
            'duration': settings.DEBUG and connection.queries[-1]['time'] or 0.0,
            'select_headers': [f.name for f in model._meta.fields], #maybe local_fields is better.
            'explain_headers': headers,
        }
        return context


def dict_models():
    return dict([(model.__name__, model) for model in django_get_models()])

def list_models():
    return [["%s|%s" % (model._meta.app_label, model._meta.module_name), 
             "%s - %s" % (model._meta.app_label, model._meta.module_name)] 
                for model in django_get_models() ]

def get_model(model_string):
    return django_get_model(*model_string.split("|"))
        
def detail_model(model):
    managers = [name for id, name, manager in chain(model._meta.concrete_managers,
                                                    model._meta.abstract_managers)
                if not name.startswith('_')]
    fields = [field.name for field in model._meta.local_fields
              if not isinstance(field, ForeignKey)]
    # handle fields with relation (fk, m2m)
    related_fields = [field for field in model._meta.local_fields
                      if isinstance(field, ForeignKey)]
    related_fields = [(field.name, field.rel.to._meta.app_label, field.rel.to._meta.module_name) \
                      for field in chain(model._meta.many_to_many, related_fields)]
    return dict(managers=managers, fields=fields, related_fields=related_fields)
    
########NEW FILE########
__FILENAME__ = query_analyzer_tags
from django import template
from django.template.loaders.app_directories import load_template_source

register = template.Library()

def do_include_raw(parser, token):
    """
    Performs a template include without parsing the context, just dumps the template in.
    """
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError, "%r tag takes one argument: the name of the template to be included" % bits[0]

    template_name = bits[1]
    if template_name[0] in ('"', "'") and template_name[-1] == template_name[0]:
        template_name = template_name[1:-1]

    source, path = load_template_source(template_name)

    return template.TextNode(source)
register.tag("include_raw", do_include_raw)


########NEW FILE########
__FILENAME__ = tests
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import simplejson


class TestViews(TestCase):
    fixtures = ['testdata']

    def test_model_select(self):
        response = self.client.get(reverse('models'))
        assert response.status_code == 200
        models = simplejson.loads(response.content)
        assert models == {"models": [["contenttypes", "contenttype"], ["auth", "permission"], \
                                    ["auth", "group"], ["auth", "user"], ["auth", "message"], \
                                    ["sessions", "session"], ["sites", "site"]]}

    def test_model_details(self):
        response = self.client.get(reverse('model.details', kwargs={'app_label':'auth', \
                                                                    'model_name':'user'}))
        assert response.status_code == 200
        details = simplejson.loads(response.content)
        assert details == {"fields": [u'id', u'username', u'first_name', u'last_name', u'email',
                                      u'password', u'is_staff', u'is_active', u'is_superuser',
                                      u'last_login', u'date_joined'],
                          "managers": ["objects"],
                          "related_fields": [[u'groups', u'auth', u'group'],
                                             [u'user_permissions', u'auth', u'permission']]
                          }

        response = self.client.get(reverse('model.details', kwargs={'app_label':'auth', \
                                                                    'model_name':'permission'}))
        assert response.status_code == 200
        details = simplejson.loads(response.content)
        assert details == {"fields": [u'id', u'name', u'codename'],
                          "managers": ["objects"],
                          "related_fields": [[u'content_type', u'contenttypes', u'contenttype']]
                          }

    def test_queryset_analyzer(self):
        queries = (dict(app='auth', model='user', filters=[{'username__contains':'e'}]),
                   dict(app='auth', model='user', excludes=[{'username__contains':'e'}]),
                   )
        for query in queries:
            response = self.client.post(reverse('analyze.queryset'),
                                        dict(query=simplejson.dumps(query)))
            assert response.status_code == 200

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('query_analyzer.views',
#    url(r'^$', 'analyze'),
    url(r'^basic/$', 'basic_analyze'),    
#    url(r'^api/models/$', 'model_select', name='models'),
#    url(r'^api/model/(?P<app_label>\w+)/(?P<model_name>\w+)/$', 'model_details', name='model.details'),
)

########NEW FILE########
__FILENAME__ = views
from query_analyzer.decorators import json_view, html_view
from query_analyzer.forms import FieldsForm, PythonForm
from query_analyzer.shortcuts import AnalyzePython, list_models, detail_model, get_model

from django.db import transaction

@html_view("query_analyzer/basic_analyze.html")
@transaction.commit_manually
def basic_analyze(request):
    form = PythonForm(request.POST or None, initial={"python":"all"})
    result = None
    data = { "form": form, }
    if form.is_valid():
        clean = form.cleaned_data
        if clean.get("python"):
            try:
                analyzer = AnalyzePython(
                    model=get_model(clean.get("model")),
                    python=clean.get("python")
                    )
                data.update(analyzer())
            except SyntaxError:
                form._errors["python"] = ["There is an error with that code",]

    transaction.rollback()
    return data

@json_view
def model_select(request):
    return list_models()

@json_view
def model_details(request, app_label, model_name):
    return detail_model(app_label, model_name)
########NEW FILE########
