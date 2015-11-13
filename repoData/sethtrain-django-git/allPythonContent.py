__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = repositories
from datetime import datetime
import os

from django import template
register = template.Library()
 
@register.filter("name")
def name(value):
    return value.split(os.sep)[-2]

@register.filter("first_eight")
def first_eight(value):
    return "".join(list(str(value))[:8])

@register.filter("tuple_to_date")
def tuple_to_date(value):
    return datetime(value[0], value[1], value[2], value[3], value[4], value[5], value[6])
########NEW FILE########
__FILENAME__ = stylize
from django.template import Library, Node, resolve_variable
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

register = Library()

# usage: {% stylize "language" %}...language text...{% endstylize %}
class StylizeNode(Node):
	def __init__(self, nodelist, *varlist):
		self.nodelist, self.vlist = (nodelist, varlist)

	def render(self, context):
		style = 'text'
		if len(self.vlist) > 0:
			style = resolve_variable(self.vlist[0], context)
		return highlight(self.nodelist.render(context),
				get_lexer_by_name(style, encoding='UTF-8'), HtmlFormatter(cssclass="pygment_highlight"))

def stylize(parser, token):
	nodelist = parser.parse(('endstylize',))
	parser.delete_first_token()
	return StylizeNode(nodelist, *token.contents.split()[1:])

stylize = register.tag(stylize)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = []

urlpatterns += patterns('django_git.views',
    url(r'^(?P<repo>[\w_-]+)/commit/(?P<commit>[\w\d]+)/blob/$', 'blob', name='django-git-blob'),
    url(r'^(?P<repo>[\w_-]+)/commit/(?P<commit>[\w\d]+)/$', 'commit', name='django-git-commit'),
    url(r'^(?P<repo>[\w_-]+)/$', 'repo', name='django-git-repo'),
    url(r'^$', 'index', name='django-git-index'),
)

########NEW FILE########
__FILENAME__ = utils
import os
from git import *

from django.conf import settings

def get_repos():
    repos = [get_repo(dir) for dir in os.listdir(settings.REPOS_ROOT)]
    return [r for r in repos if not (r is None)]

def get_repo(name):
    repo_path = os.path.join(settings.REPOS_ROOT, name)
    if os.path.isdir(repo_path):
        try:
            return Repo(repo_path)
        except Exception:
            pass
    return None

def get_commit(name, commit):
    repo = get_repo(name)
    commit = repo.commit(commit)
    return commit

def get_blob(repo, commit, file):
    repo = get_repo(repo)
    commit = repo.commit(commit)
    tree = commit.tree
    for path_seg in file.split(os.sep):
        t = tree.get(path_seg)
        if isinstance(t, Tree):
            tree = t
        else:
            blob = t
    return blob



###########################################
# http://djangosnippets.org/snippets/559/ #
###########################################


from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

def auto_render(func):
    """Decorator that automaticaly call the render_to_response shortcut.

    The view must return a tuple with two items : a template filename and the desired context.
    HttpResponse object could be also returned. it's possible to override the default 
    template filename by calling a decorated view with an "template_name" parameter
    or to get only the context dictionary via "only_context" parameter.

    >>> from utils.utils import auto_render
    >>> @auto_render
    ... def test(request):
    ...     return 'base.html', {'oki':1}
    ...
    >>> from django.http import HttpRequest, HttpResponse
    >>> response = test(HttpRequest())
    >>> assert type(response) is HttpResponse
    >>> response = test(HttpRequest(), only_context=True)
    >>> assert response['oki'] == 1
    >>> try:
    ...     response = test(HttpRequest(), template_name='fake_template.html')
    ... except Exception, e:
    ...     e.message
    'fake_template.html'
    """

    def _dec(request, *args, **kwargs):

        if kwargs.get('only_context', False):
            # return only context dictionary
            del(kwargs['only_context'])
            response = func(request, *args, **kwargs)
            if isinstance(response, HttpResponse) or isinstance(response, HttpResponseRedirect):
                raise Except("cannot return context dictionary because a HttpResponseRedirect as been found")
            (template_name, context) = response
            return context

        if kwargs.get('template_name', False):
            overriden_template_name = kwargs['template_name']
            del(kwargs['template_name'])
        else:
            overriden_template_name = None

        response = func(request, *args, **kwargs)

        if isinstance(response, HttpResponse) or isinstance(response, HttpResponseRedirect):
            return response
        (template_name, context) = response
        if overriden_template_name:
            template_name = overriden_template_name

        return render_to_response(template_name, context, context_instance=RequestContext(request))
    return _dec

########NEW FILE########
__FILENAME__ = views
from pygments import highlight
from pygments.lexers import guess_lexer_for_filename
from pygments.formatters import HtmlFormatter

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, get_list_or_404

from django_git.utils import *

@auto_render
def index(request, template_name='django_git/index.html'):
    return template_name,{'repos': get_repos()}

@auto_render
def repo(request, repo, template_name='django_git/repo.html'):
    return template_name, {'repo': get_repo(repo)}

@auto_render
def commit(request, repo, commit, template_name='django_git/commit.html'):
    return template_name,{'diffs': get_commit(repo, commit).diffs, 'repo': get_repo(repo), 'commit': commit }

def blob(request, repo, commit):
    file = request.GET.get('file', '')
    blob = get_blob(repo, commit, file)
    lexer = guess_lexer_for_filename(blob.basename, blob.data)
    return HttpResponse(highlight(blob.data, lexer, HtmlFormatter(cssclass="pygment_highlight", linenos='inline')))

########NEW FILE########
