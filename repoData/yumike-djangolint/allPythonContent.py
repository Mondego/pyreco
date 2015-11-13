__FILENAME__ = fabfile
import json
import os

from datetime import datetime

from fabric.api import *
from fabric.contrib.files import append, exists, upload_template


@task
def vagrant():
    env.user = 'project'
    env.hosts = ['127.0.0.1:2222']
    env.project_env = 'production'


@task
def linode():
    env.user = 'project'
    env.hosts = ['djangolint.com']
    env.project_env = 'production'


@task
def bootstrap():
    with settings(user='root'):
        run('apt-get -q -y update')
        run('apt-get -q -y upgrade')
        run('apt-get -q -y install wget ssl-cert ruby ruby-dev '
            'libopenssl-ruby rdoc ri irb build-essential')
        with cd('/tmp'):
            run('wget -q http://production.cf.rubygems.org/rubygems/rubygems-1.7.2.tgz')
            run('tar xf rubygems-1.7.2.tgz')
            with cd('rubygems-1.7.2'):
                run('ruby setup.rb --no-format-executable')
            run('rm -rf rubygems-1.7.2*')
        run('gem install chef --no-ri --no-rdoc')


@task
def provision():
    project_root = os.path.dirname(env.real_fabfile)
    chef_root = os.path.join(project_root, 'chef')
    chef_name = 'chef-{0}'.format(datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%S'))
    chef_archive = '{0}.tar.gz'.format(chef_name)

    local('cp -r {0} /tmp/{1}'.format(chef_root, chef_name))

    with open('node.json') as f:
        data = json.load(f)
    project = data.setdefault('project', {})
    project['environment'] = env.project_env
    with open('/tmp/{0}/node.json'.format(chef_name), 'w') as f:
        json.dump(data, f)

    solo_rb = ('file_cache_path "/tmp/chef-solo"',
               'cookbook_path "/tmp/{0}/cookbooks"'.format(chef_name))
    with lcd('/tmp'):
        for line in solo_rb:
            local("echo '{0}' >> {1}/solo.rb".format(line, chef_name))
        local('tar czf {0} {1}'.format(chef_archive, chef_name))

    with settings(user='root'):
        put('/tmp/{0}'.format(chef_archive), '/tmp/{0}'.format(chef_archive))
        local('rm -rf /tmp/{0}*'.format(chef_name))
        with cd('/tmp'):
            run('tar xf {0}'.format(chef_archive))
        with cd('/tmp/{0}'.format(chef_name)):
            with settings(warn_only=True):
                run('chef-solo -c solo.rb -j node.json')
        run('rm -rf /tmp/{0}*'.format(chef_name))
    upload_public_key('project', 'root')
    prepare_env()


@task
def prepare_env():
    if not exists('.env'):
        run('wget https://raw.github.com/pypa/virtualenv/develop/virtualenv.py')
        run('python virtualenv.py --distribute --no-site-packages ~/.env')
        run("echo 'source ~/.env/bin/activate' >> .profile")
    if not exists('.git'):
        run('git init .git --bare')
        run('git clone .git project')
    local('git push ssh://{user}@{host}:{port}/~/.git master'.format(**env))
    with cd('project'):
        run('git pull ~/.git master')
        install_requirements()
        manage('syncdb --migrate --noinput')
        manage('collectstatic --noinput')
    with open('etc/supervisord.conf') as f:
        supervisor_config = f.read().format(**{'project_env': env.project_env})
        run('mkdir -p ~/etc/ && rm -f ~/etc/supervisord.conf')
        append('~/etc/supervisord.conf', supervisor_config)
    with settings(user='root', warn_only=True):
        with lcd('etc'):
            put('supervisor_upstart.conf', '/etc/init/supervisor.conf')
            run('stop supervisor')
            run('start supervisor')


@task
def deploy(update_all='yes'):
    local('git push ssh://{user}@{host}:{port}/~/.git master'.format(**env))
    with cd('project'):
        run('git pull ~/.git master')
        if update_all == 'yes':
            install_requirements()
            manage('syncdb --migrate --noinput')
            manage('collectstatic --noinput')
            upload_crontab()
    run('supervisorctl restart gunicorn')
    run('supervisorctl restart celery')


@task
def install_requirements():
    run('pip install -r requirements/{0}.txt'.format(env.project_env))


@task
def manage(command):
    run('python project/manage.py {0}'.format(command))


@task
def upload_public_key(to=None, user=None):
    with settings(user=user or env.user):
        to = to or env.user
        path = os.path.expanduser('~/.ssh/id_rsa.pub')
        if to and os.path.exists(path):
            key = ' '.join(open(path).read().strip().split(' ')[:2])
            run('mkdir -p /home/{0}/.ssh'.format(to))
            append('/home/{0}/.ssh/authorized_keys'.format(to), key, partial=True)
            run('chown {0}:{0} /home/{0}/.ssh/authorized_keys'.format(to))
            run('chmod 600 /home/{0}/.ssh/authorized_keys'.format(to))
            run('chown {0}:{0} /home/{0}/.ssh'.format(to))
            run('chmod 700 /home/{0}/.ssh'.format(to))


@task
def upload_crontab():
    project_root = os.path.dirname(env.real_fabfile)
    crontab_path = os.path.join('etc', 'crontab')
    if not os.path.exists(crontab_path):
        return
    upload_template(
        filename=crontab_path,
        destination='crontab.tmp',
        context={'environment': env.project_env},
    )
    run('crontab < crontab.tmp')
    run('rm crontab.tmp')

########NEW FILE########
__FILENAME__ = base
import ast
import os
from .context import Context


class BaseAnalyzer(object):
    """
    Base code analyzer class. Takes dict `file path => ast node` as first
    param and path to repository as second.

    Subclass this class and implement `analyze_file` method if you want to
    create new code analyzer.
    """

    surround_by = 2

    def __init__(self, code_dict, repo_path):
        self._file_lines = None
        self.code_dict = code_dict
        self.repo_path = repo_path

    def get_file_lines(self, filepath, start, stop):
        """
        Yield code snippet from file `filepath` for line number `lineno`
        as tuples `(<line number>, <importance>, <text>)` extending it by
        `surround_by` lines up and down if possible.

        If important part has blank lines at the bottom they will be removed.
        """

        if self._file_lines is None:
            with open(os.path.join(self.repo_path, filepath)) as f:
                self._file_lines = f.readlines()

        if stop is None:
            lines = self._file_lines[start - 1:]
        else:
            lines = self._file_lines[start - 1:stop]
        for i, line in enumerate(lines):
            lines[i] = [start + i, True, line.rstrip()]
        while lines and self.is_empty_line(lines[-1][-1]):
            lines.pop()

        if not lines:
            return []

        stop = lines[0][0]
        start = max(1, stop - self.surround_by)
        prefix_lines = []
        for i, line in enumerate(self._file_lines[start - 1:stop - 1], start=start):
            prefix_lines.append([i, False, line.rstrip()])

        start = lines[-1][0] + 1
        stop = start + self.surround_by
        suffix_lines = []
        for i, line in enumerate(self._file_lines[start - 1:stop - 1], start=start):
            suffix_lines.append([i, False, line.rstrip()])

        return prefix_lines + lines + suffix_lines

    def is_empty_line(self, line):
        return not line.split('#')[0].strip()

    def clear_file_lines_cache(self):
        self._file_lines = None

    def analyze_file(self, filepath, code):
        raise NotImplementedError

    def analyze(self):
        """
        Iterate over `code_dict` and yield all results from every file.
        """
        for filepath, code in self.code_dict.items():
            for result in self.analyze_file(filepath, code):
                yield result
            self.clear_file_lines_cache()


class CodeSnippet(list):
    """
    Represents code snippet as list of tuples `(<line number>, <importance>,
    <text>)`.

    Use `add_line` method to add new lines to the snippet.
    """

    def add_line(self, lineno, text, important=True):
        """
        Add new line to the end of snippet.
        """
        self.append((lineno, important, text))


class Result(object):
    """
    Represents the result of code analysis.
    """

    def __init__(self, description, path, line):
        self.description = description
        self.path = path
        self.line = line
        self.source = CodeSnippet()
        self.solution = CodeSnippet()


class AttributeVisitor(ast.NodeVisitor):
    """
    Process attribute node and build the name of the attribute if possible.

    Currently only simple expressions are supported (like `foo.bar.baz`).
    If it is not possible to get attribute name as string `is_usable` is
    set to `True`.

    After `visit()` method call `get_name()` method can be used to get
    attribute name if `is_usable` == `True`.
    """

    def __init__(self):
        self.is_usable = True
        self.name = []

    def get_name(self):
        """
        Get the name of the visited attribute.
        """
        return '.'.join(self.name)

    def visit_Attribute(self, node):
        self.generic_visit(node)
        self.name.append(node.attr)

    def visit_Name(self, node):
        self.name.append(node.id)

    def visit_Load(self, node):
        pass

    def generic_visit(self, node):
        # If attribute node consists not only from nodes of types `Attribute`
        # and `Name` mark it as unusable.
        if not isinstance(node, ast.Attribute):
            self.is_usable = False
        ast.NodeVisitor.generic_visit(self, node)


def set_lineno(meth):
    def decorator(self, node):
        self.push_lineno(node.lineno)
        result = meth(self, node)
        self.pop_lineno()
        return result
    decorator.__name__ = meth.__name__
    return decorator


class ModuleVisitor(ast.NodeVisitor):
    """
    Collect interesting imported names during module nodes visiting.
    """

    interesting = {}

    def __init__(self):
        self.names = Context()
        self.lineno = []
        self.found = {}

    def add_found(self, name, node):
        lineno_level = self.get_lineno_level()
        if lineno_level not in self.found:
            self.found[lineno_level] = []
        self.found[lineno_level].append([name, node, self.get_lineno(), None])

    def get_found(self):
        for level in self.found.values():
            for found in level:
                yield found

    def push_lineno(self, lineno):
        self.lineno.append(lineno)
        lineno_level = self.get_lineno_level()
        for level in self.found.keys():
            if level < lineno_level:
                return
            for found in self.found[level]:
                if found[-1] is None and lineno >= found[-2]:
                    found[-1] = max(lineno - 1, found[-2])

    def pop_lineno(self):
        return self.lineno.pop()

    def get_lineno(self):
        return self.lineno[-1]

    def get_lineno_level(self):
        return len(self.lineno)

    def update_names(self, aliases, get_path):
        """
        Update `names` context with interesting imported `aliases` using
        `get_path` function to get full path to the object by object name.
        """
        for alias in aliases:
            path = get_path(alias.name)
            if path not in self.interesting:
                continue
            if self.interesting[path]:
                for attr in self.interesting[path]:
                    name = '.'.join((alias.asname or alias.name, attr))
                    self.names[name] = '.'.join((path, attr))
            else:
                name = alias.asname or alias.name
                self.names[name] = path

    @set_lineno
    def visit_Import(self, node):
        self.update_names(node.names, lambda x: x)

    @set_lineno
    def visit_ImportFrom(self, node):
        self.update_names(node.names, lambda x: '.'.join((node.module, x)))

    @set_lineno
    def visit_FunctionDef(self, node):
        # Create new scope in `names` context if we are coming to function body
        self.names.push()
        self.generic_visit(node)
        self.names.pop()

    @set_lineno
    def visit_Assign(self, node):
        # Some assingments attach interesting imports to new names.
        # Trying to parse it.
        visitor = AttributeVisitor()
        visitor.visit(node.value)
        if not visitor.is_usable:
            # Seems on the right side is not an attribute. Let's visit
            # assignment as it also can contain interesting code.
            self.generic_visit(node)
            return

        name = visitor.get_name()
        # skipping assignment if value is not interesting
        if name not in self.names:
            return

        # trying to parse the left-side attribute name
        for target in node.targets:
            visitor = AttributeVisitor()
            visitor.visit(target)
            if not visitor.is_usable:
                continue
            target = visitor.get_name()
            self.names[target] = self.names[name]

    @set_lineno
    def visit_Call(self, node):
        self.generic_visit(node)

    @set_lineno
    def visit_List(self, node):
        self.generic_visit(node)

    @set_lineno
    def visit_Tuple(self, node):
        self.generic_visit(node)


class DeprecatedCodeVisitor(ModuleVisitor):

    def visit_Attribute(self, node):
        visitor = AttributeVisitor()
        visitor.visit(node)
        if visitor.is_usable:
            name = visitor.get_name()
            if name in self.names:
                self.add_found(self.names[name], node)

    def visit_Name(self, node):
        if node.id in self.names:
            self.add_found(self.names[node.id], node)

########NEW FILE########
__FILENAME__ = context
"""Inspired by django.template.Context"""


class ContextPopException(Exception):
    """pop() has been called more times than push()"""


class Context(object):
    """A stack container for imports and assignments."""

    def __init__(self):
        self.dicts = [{}]

    def push(self):
        d = {}
        self.dicts.append(d)
        return d

    def pop(self):
        if len(self.dicts) == 1:
            raise ContextPopException
        return self.dicts.pop()

    def __setitem__(self, key, value):
        self.dicts[-1][key] = value

    def __getitem__(self, key):
        for d in reversed(self.dicts):
            if key in d:
                return d[key]
        raise KeyError

    def __delitem__(self, key):
        del self.dicts[-1][key]

    def has_key(self, key):
        for d in self.dicts:
            if key in d:
                return True
        return False

    def has_value(self, value):
        dict_ = {}
        for d in self.dicts:
            dict_.update(d)
        return value in dict_.values()

    def __contains__(self, key):
        return self.has_key(key)

########NEW FILE########
__FILENAME__ = context_processors
import ast

from .base import BaseAnalyzer, ModuleVisitor, Result


DESCRIPTION = """
As of Django 1.4, ``{name}`` function has been deprecated and will be removed
in Django 1.5. Use ``{propose}`` instead.
"""


class ContextProcessorsVisitor(ast.NodeVisitor):

    def __init__(self):
        self.found = []

    deprecated_items = {
        'django.core.context_processors.auth':
            'django.contrib.auth.context_processors.auth',
        'django.core.context_processors.PermWrapper':
            'django.contrib.auth.context_processors.PermWrapper',
        'django.core.context_processors.PermLookupDict':
            'django.contrib.auth.context_processors.PermLookupDict',
    }

    def visit_Str(self, node):
        if node.s in self.deprecated_items.keys():
            self.found.append((node.s, node))


class ContextProcessorsAnalyzer(BaseAnalyzer):

    def analyze_file(self, filepath, code):
        if not isinstance(code, ast.AST):
            return
        visitor = ContextProcessorsVisitor()
        visitor.visit(code)
        for name, node in visitor.found:
            propose = visitor.deprecated_items[name]
            result = Result(
                description = DESCRIPTION.format(name=name, propose=propose),
                path = filepath,
                line = node.lineno)
            lines = self.get_file_lines(filepath, node.lineno, node.lineno)
            for lineno, important, text in lines:
                result.source.add_line(lineno, text, important)
                result.solution.add_line(lineno, text.replace(name, propose), important)
            yield result

########NEW FILE########
__FILENAME__ = db_backends
import ast

from .base import BaseAnalyzer, Result


DESCRIPTION = """
``{name}`` database backend has been deprecated in Django 1.2 and removed in 1.4.
Use ``{propose}`` instead.
"""


class DB_BackendsVisitor(ast.NodeVisitor):

    def __init__(self):
        self.found = []

    removed_items = {
        'django.db.backends.postgresql':
            'django.db.backends.postgresql_psycopg2',

    }

    def visit_Str(self, node):
        if node.s in self.removed_items.keys():
            self.found.append((node.s, node))


class DB_BackendsAnalyzer(BaseAnalyzer):

    def analyze_file(self, filepath, code):
        if not isinstance(code, ast.AST):
            return
        visitor = DB_BackendsVisitor()
        visitor.visit(code)
        for name, node in visitor.found:
            propose = visitor.removed_items[name]
            result = Result(
                description = DESCRIPTION.format(name=name, propose=propose),
                path = filepath,
                line = node.lineno)
            lines = self.get_file_lines(filepath, node.lineno, node.lineno)
            for lineno, important, text in lines:
                result.source.add_line(lineno, text, important)
                result.solution.add_line(lineno, text.replace(name, propose), important)
            yield result

########NEW FILE########
__FILENAME__ = formtools
import ast

from .base import BaseAnalyzer, Result, DeprecatedCodeVisitor


DESCRIPTION = """
``{name}`` function has been deprecated in Django 1.3 and will be removed in
1.5. Use ``django.contrib.formtools.utils.form_mac()`` instead.
"""


class FormToolsVisitor(DeprecatedCodeVisitor):

    interesting = {
        'django.contrib.formtools.utils': ['security_hash'],
        'django.contrib.formtools.utils.security_hash': None,
    }


class FormToolsAnalyzer(BaseAnalyzer):

    def analyze_file(self, filepath, code):
        if not isinstance(code, ast.AST):
            return
        visitor = FormToolsVisitor()
        visitor.visit(code)
        for name, node, start, stop in visitor.get_found():
            result = Result(
                description = DESCRIPTION.format(name=name),
                path = filepath,
                line = start)
            lines = self.get_file_lines(filepath, start, stop)
            for lineno, important, text in lines:
                result.source.add_line(lineno, text, important)
            yield result

########NEW FILE########
__FILENAME__ = generic_views
import ast

from .base import BaseAnalyzer, Result, DeprecatedCodeVisitor


DESCRIPTION = """
``{name}`` function has been deprecated in Django 1.3 and will be removed in
1.5.
"""


class GenericViewsVisitor(DeprecatedCodeVisitor):

    interesting = {
        'django.views.generic.simple': ['direct_to_template', 'redirect_to'],
        'django.views.generic.simple.direct_to_template': None,
        'django.views.generic.simple.redirect_to': None,

        'django.views.generic.date_based': [
            'archive_index', 'archive_year', 'archive_month', 'archive_week',
            'archive_day', 'archive_today', 'archive_detail'],
        'django.views.generic.date_based.archive_index': None,
        'django.views.generic.date_based.archive_year': None,
        'django.views.generic.date_based.archive_month': None,
        'django.views.generic.date_based.archive_week': None,
        'django.views.generic.date_based.archive_day': None,
        'django.views.generic.date_based.archive_today': None,
        'django.views.generic.date_based.archive_detail': None,

        'django.views.generic.list_detail': ['object_list', 'object_detail'],
        'django.views.generic.list_detail.object_list': None,
        'django.views.generic.list_detail.object_detail': None,

        'django.views.generic.create_update': [
            'create_object', 'update_object', 'delete_object'],
        'django.views.generic.create_update.create_object': None,
        'django.views.generic.create_update.update_object': None,
        'django.views.generic.create_update.delete_object': None,
    }


class GenericViewsAnalyzer(BaseAnalyzer):

    def analyze_file(self, filepath, code):
        if not isinstance(code, ast.AST):
            return
        visitor = GenericViewsVisitor()
        visitor.visit(code)
        for name, node, start, stop in visitor.get_found():
            result = Result(
                description = DESCRIPTION.format(name=name),
                path = filepath,
                line = start)
            lines = self.get_file_lines(filepath, start, stop)
            for lineno, important, text in lines:
                result.source.add_line(lineno, text, important)
            yield result

########NEW FILE########
__FILENAME__ = loader
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.importlib import import_module
from django.utils.functional import memoize


_analyzers_cache = {}


def clear_analyzers_cache():
    global _analyzers_cache
    _analyzers_cache.clear()


def load_analyzer(analyzer_name):
    module_name, attr = analyzer_name.rsplit('.', 1)
    try:
        module = import_module(module_name)
    except ImportError, e:
        raise ImproperlyConfigured(
            'Error importing analyzer %s: "%s"' % (analyzer_name, e))
    try:
        analyzer = getattr(module, attr)
    except AttributeError, e:
        raise ImproperlyConfigured(
            'Error importing analyzer %s: "%s"' % (analyzer_name, e))
    return analyzer


def get_analyzers():
    analyzers = []
    for analyzer_name in getattr(settings, 'LINT_ANALYZERS', ()):
        analyzers.append(load_analyzer(analyzer_name))
    return analyzers
get_analyzers = memoize(get_analyzers, _analyzers_cache, 0)

########NEW FILE########
__FILENAME__ = render_to_response
import ast

from .base import (
    BaseAnalyzer, Result, AttributeVisitor, ModuleVisitor, set_lineno)


class CallVisitor(ast.NodeVisitor):
    """
    Collects all usable attributes and names inside function call.
    """

    def __init__(self):
        self.names = set()

    def visit_Attribute(self, node):
        visitor = AttributeVisitor()
        visitor.visit(node)
        if visitor.is_usable:
            self.names.add(visitor.get_name())

    def visit_Name(self, node):
        self.names.add(node.id)


class RenderToResponseVisitor(ModuleVisitor):

    interesting = {
        'django.shortcuts': ['render_to_response'],
        'django.shortcuts.render_to_response': None,
        'django.template': ['RequestContext'],
        'django.template.RequestContext': None,
    }

    @set_lineno
    def visit_Call(self, node):
        # Check if calling attribute is usable...
        visitor = AttributeVisitor()
        visitor.visit(node.func)
        if not visitor.is_usable:
            return

        # ...and if interesting
        name = visitor.get_name()
        if name not in self.names:
            return

        # ... and also if it is actually `render_to_response` call.
        if self.names[name] != 'django.shortcuts.render_to_response':
            return

        # Check if it contains `RequestContext`. If so, add to `found`.
        visitor = CallVisitor()
        visitor.visit(node)
        for subname in visitor.names:
            if subname not in self.names:
                continue
            if self.names[subname] == 'django.template.RequestContext':
                self.add_found(name, node)


class RenderToResponseAnalyzer(BaseAnalyzer):

    def analyze_file(self, filepath, code):
        if not isinstance(code, ast.AST):
            return
        visitor = RenderToResponseVisitor()
        visitor.visit(code)
        for name, node, start, stop in visitor.get_found():
            result = Result(
                description = (
                    "this %r usage case can be replaced with 'render' "
                    "function from 'django.shortcuts' package." % name),
                path = filepath,
                line = start)
            lines = self.get_file_lines(filepath, start, stop)
            for lineno, important, text in lines:
                result.source.add_line(lineno, text, important)
            yield result

########NEW FILE########
__FILENAME__ = syntax_error
import os
from .base import BaseAnalyzer, Result


DESCRIPTION = 'Syntax error: {msg}.'


class SyntaxErrorAnalyzer(BaseAnalyzer):
    """
    Return notes for all fiels with syntax error.
    """

    def analyze_file(self, path, code):
        if not isinstance(code, SyntaxError):
            return
        result = Result(
            description=DESCRIPTION.format(msg=code.msg),
            path=path,
            line=code.lineno,
        )
        lines = self.get_file_lines(path, code.lineno, code.lineno)
        for i, important, line in lines:
            result.source.add_line(i, line, important)
        yield result

########NEW FILE########
__FILENAME__ = template_loaders
import ast

from .base import BaseAnalyzer, Result


DESCRIPTION = """
``{name}`` function has been deprecated in Django 1.2 and removed in 1.4. Use
``{propose}`` class instead.
"""


class TemplateLoadersVisitor(ast.NodeVisitor):

    def __init__(self):
        self.found = []

    removed_items = {
        'django.template.loaders.app_directories.load_template_source':
            'django.template.loaders.app_directories.Loader',
        'django.template.loaders.eggs.load_template_source':
            'django.template.loaders.eggs.Loader',
        'django.template.loaders.filesystem.load_template_source':
            'django.template.loaders.filesystem.Loader',
    }

    def visit_Str(self, node):
        if node.s in self.removed_items.keys():
            self.found.append((node.s, node))


class TemplateLoadersAnalyzer(BaseAnalyzer):

    def analyze_file(self, filepath, code):
        if not isinstance(code, ast.AST):
            return
        visitor = TemplateLoadersVisitor()
        visitor.visit(code)
        for name, node in visitor.found:
            propose = visitor.removed_items[name]
            result = Result(
                description = DESCRIPTION.format(name=name, propose=propose),
                path = filepath,
                line = node.lineno)
            lines = self.get_file_lines(filepath, node.lineno, node.lineno)
            for lineno, important, text in lines:
                result.source.add_line(lineno, text, important)
                result.solution.add_line(lineno, text.replace(name, propose), important)
            yield result

########NEW FILE########
__FILENAME__ = context_processors
def report_pk(request):
    report_pk = request.session.get('report_pk')
    return {'report_pk': report_pk}

########NEW FILE########
__FILENAME__ = forms
from django import forms
from .models import Report


class ReportForm(forms.ModelForm):

    url = forms.URLField(
        initial = 'https://github.com/',
        widget = forms.TextInput(attrs={'class': 'url-field'}),
    )

    class Meta:
        model = Report
        fields = ['url']

########NEW FILE########
__FILENAME__ = ghclone
import errno
import os
import shutil
import tempfile
from contextlib import contextmanager
from subprocess import Popen
from django.utils import simplejson as json
from github import Github, GithubException
from .settings import CONFIG


github = Github(timeout=CONFIG['GITHUB_TIMEOUT'])


class CloneError(Exception):
    pass


@contextmanager
def tempdir(root=None):
    if root is not None:
        try:
            os.makedirs(root)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
    path = tempfile.mkdtemp(dir=root)
    try:
        yield path
    finally:
        shutil.rmtree(path)


@contextmanager
def clone(url, hash=None):
    with tempdir(root=CONFIG['CLONES_ROOT']) as path:
        tarball_path = _download_tarball(url, path, hash)
        repo_path = _extract_tarball(tarball_path)
        yield repo_path


def _check_language(repo):
    if not 'Python' in repo.get_languages():
        raise CloneError("Repo language hasn't Python code")


def _get_tarball_url(repo, hash):
    return 'https://github.com/%s/%s/tarball/%s' % (
        repo.owner.login, repo.name, hash or repo.master_branch
    )


def _download_tarball(url, path, hash):
    repo_owner, repo_name = url.split('/')
    try:
        repo = github.get_user(repo_owner).get_repo(repo_name)
    except GithubException:
        raise CloneError('Not found')
    _check_language(repo)
    tarball_url = _get_tarball_url(repo, hash)
    tarball_path = os.path.join(path, 'archive.tar.gz')
    curl_string = 'curl %s --connect-timeout %d --max-filesize %d -L -s -o %s' % (
        tarball_url, CONFIG['GITHUB_TIMEOUT'], CONFIG['MAX_TARBALL_SIZE'], tarball_path
    )
    if Popen(curl_string.split()).wait():
        raise CloneError("Can't download tarball")
    return tarball_path


def _extract_tarball(tarball_path):
    repo_path = os.path.join(os.path.dirname(tarball_path), 'repo')
    os.makedirs(repo_path)
    if Popen(['tar', 'xf', tarball_path, '-C', repo_path]).wait():
        raise CloneError("Can't extract tarball")
    return repo_path

########NEW FILE########
__FILENAME__ = delete_expired_reports
from django.conf import settings
from django.core.management.base import BaseCommand

from lint.models import Report


class Command(BaseCommand):

    help = 'Deletes expired reports'

    def handle(self, *args, **kwargs):
        Report.objects.delete_expired()

########NEW FILE########
__FILENAME__ = managers
from datetime import datetime, timedelta
from django.db import models
from .settings import CONFIG


EXPIRATION_DAYS = CONFIG['REPORT_EXPIRATION_DAYS']


class ReportManager(models.Manager):

    def delete_expired(self):
        expiration_date = datetime.now() - timedelta(days=EXPIRATION_DAYS)
        expired = self.filter(created_on__lt=expiration_date)
        expired.delete()

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Report'
        db.create_table('lint_report', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('hash', self.gf('django.db.models.fields.CharField')(unique=True, max_length=40)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('stage', self.gf('django.db.models.fields.CharField')(default='waiting', max_length=10)),
            ('error', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('lint', ['Report'])


    def backwards(self, orm):
        
        # Deleting model 'Report'
        db.delete_table('lint_report')


    models = {
        'lint.report': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Report'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stage': ('django.db.models.fields.CharField', [], {'default': "'waiting'", 'max_length': '10'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['lint']

########NEW FILE########
__FILENAME__ = 0002_auto__add_fix
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Fix'
        db.create_table('lint_fix', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('report', self.gf('django.db.models.fields.related.ForeignKey')(related_name='fixes', to=orm['lint.Report'])),
            ('path', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('line', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('source', self.gf('django.db.models.fields.TextField')()),
            ('error', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('lint', ['Fix'])


    def backwards(self, orm):
        
        # Deleting model 'Fix'
        db.delete_table('lint_fix')


    models = {
        'lint.fix': {
            'Meta': {'object_name': 'Fix'},
            'error': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'report': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'fixes'", 'to': "orm['lint.Report']"}),
            'source': ('django.db.models.fields.TextField', [], {})
        },
        'lint.report': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Report'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stage': ('django.db.models.fields.CharField', [], {'default': "'waiting'", 'max_length': '10'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['lint']

########NEW FILE########
__FILENAME__ = 0003_auto__del_field_report_created__add_field_report_created_on
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Report.created'
        db.delete_column('lint_report', 'created')

        # Adding field 'Report.created_on'
        db.add_column('lint_report', 'created_on', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now), keep_default=False)


    def backwards(self, orm):
        
        # Adding field 'Report.created'
        db.add_column('lint_report', 'created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now), keep_default=False)

        # Deleting field 'Report.created_on'
        db.delete_column('lint_report', 'created_on')


    models = {
        'lint.fix': {
            'Meta': {'object_name': 'Fix'},
            'error': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'report': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'fixes'", 'to': "orm['lint.Report']"}),
            'source': ('django.db.models.fields.TextField', [], {})
        },
        'lint.report': {
            'Meta': {'ordering': "['-created_on']", 'object_name': 'Report'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stage': ('django.db.models.fields.CharField', [], {'default': "'waiting'", 'max_length': '10'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['lint']

########NEW FILE########
__FILENAME__ = 0004_auto__del_field_fix_error__add_field_fix_solution
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Fix.error'
        db.delete_column('lint_fix', 'error')

        # Adding field 'Fix.solution'
        db.add_column('lint_fix', 'solution', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)


    def backwards(self, orm):
        
        # User chose to not deal with backwards NULL issues for 'Fix.error'
        raise RuntimeError("Cannot reverse this migration. 'Fix.error' and its values cannot be restored.")

        # Deleting field 'Fix.solution'
        db.delete_column('lint_fix', 'solution')


    models = {
        'lint.fix': {
            'Meta': {'object_name': 'Fix'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'report': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'fixes'", 'to': "orm['lint.Report']"}),
            'solution': ('django.db.models.fields.TextField', [], {}),
            'source': ('django.db.models.fields.TextField', [], {})
        },
        'lint.report': {
            'Meta': {'ordering': "['-created_on']", 'object_name': 'Report'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stage': ('django.db.models.fields.CharField', [], {'default': "'waiting'", 'max_length': '10'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['lint']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_fix_description
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Fix.description'
        db.add_column('lint_fix', 'description', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Fix.description'
        db.delete_column('lint_fix', 'description')


    models = {
        'lint.fix': {
            'Meta': {'object_name': 'Fix'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'report': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'fixes'", 'to': "orm['lint.Report']"}),
            'solution': ('django.db.models.fields.TextField', [], {}),
            'source': ('django.db.models.fields.TextField', [], {})
        },
        'lint.report': {
            'Meta': {'ordering': "['-created_on']", 'object_name': 'Report'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stage': ('django.db.models.fields.CharField', [], {'default': "'waiting'", 'max_length': '10'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['lint']

########NEW FILE########
__FILENAME__ = 0006_auto__add_field_report_github_url
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Report.github_url'
        db.add_column('lint_report', 'github_url', self.gf('django.db.models.fields.CharField')(default='', max_length=255), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Report.github_url'
        db.delete_column('lint_report', 'github_url')


    models = {
        'lint.fix': {
            'Meta': {'ordering': "['path', 'line']", 'object_name': 'Fix'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'report': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'fixes'", 'to': "orm['lint.Report']"}),
            'solution': ('django.db.models.fields.TextField', [], {}),
            'source': ('django.db.models.fields.TextField', [], {})
        },
        'lint.report': {
            'Meta': {'ordering': "['-created_on']", 'object_name': 'Report'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'github_url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stage': ('django.db.models.fields.CharField', [], {'default': "'queue'", 'max_length': '10'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['lint']

########NEW FILE########
__FILENAME__ = 0007_github_url
# encoding: utf-8
import datetime
import re
from south.db import db
from south.v2 import DataMigration
from django.db import models

from ..models import GITHUB_REGEXP


class Migration(DataMigration):

    def forwards(self, orm):
        for report in orm.Report.objects.all():
            match = re.match(GITHUB_REGEXP, report.url)
            if match:
                report.github_url = match.group(1)
                report.save()

    def backwards(self, orm):
        pass


    models = {
        'lint.fix': {
            'Meta': {'ordering': "['path', 'line']", 'object_name': 'Fix'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'report': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'fixes'", 'to': "orm['lint.Report']"}),
            'solution': ('django.db.models.fields.TextField', [], {}),
            'source': ('django.db.models.fields.TextField', [], {})
        },
        'lint.report': {
            'Meta': {'ordering': "['-created_on']", 'object_name': 'Report'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'github_url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stage': ('django.db.models.fields.CharField', [], {'default': "'queue'", 'max_length': '10'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['lint']

########NEW FILE########
__FILENAME__ = 0008_add_fix_description_html_field
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Fix.description_html'
        db.add_column('lint_fix', 'description_html', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Fix.description_html'
        db.delete_column('lint_fix', 'description_html')


    models = {
        'lint.fix': {
            'Meta': {'ordering': "['path', 'line']", 'object_name': 'Fix'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'description_html': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'report': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'fixes'", 'to': "orm['lint.Report']"}),
            'solution': ('django.db.models.fields.TextField', [], {}),
            'source': ('django.db.models.fields.TextField', [], {})
        },
        'lint.report': {
            'Meta': {'ordering': "['-created_on']", 'object_name': 'Report'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'github_url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stage': ('django.db.models.fields.CharField', [], {'default': "'queue'", 'max_length': '10'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['lint']

########NEW FILE########
__FILENAME__ = 0009_fill_fix_description_html_field
# encoding: utf-8
import datetime

from south.db import db
from south.v2 import DataMigration

from django.db import models
from ..utils import rst2html


class Migration(DataMigration):

    def forwards(self, orm):
        for fix in orm.Fix.objects.all():
            fix.description_html = rst2html(fix.description)
            fix.save()

    def backwards(self, orm):
        pass

    models = {
        'lint.fix': {
            'Meta': {'ordering': "['path', 'line']", 'object_name': 'Fix'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'description_html': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'report': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'fixes'", 'to': "orm['lint.Report']"}),
            'solution': ('django.db.models.fields.TextField', [], {}),
            'source': ('django.db.models.fields.TextField', [], {})
        },
        'lint.report': {
            'Meta': {'ordering': "['-created_on']", 'object_name': 'Report'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'github_url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stage': ('django.db.models.fields.CharField', [], {'default': "'queue'", 'max_length': '10'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['lint']

########NEW FILE########
__FILENAME__ = models
import os
import random
import re
import shutil
import time

from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.dispatch import receiver
from django.utils.hashcompat import sha_constructor

from .managers import ReportManager
from .settings import CONFIG
from .utils import rst2html


STAGES = ('queue', 'cloning', 'parsing', 'analyzing', 'done')
EXPIRATION_DAYS = CONFIG['REPORT_EXPIRATION_DAYS']
GITHUB_REGEXP = re.compile(r'^https:\/\/github.com\/([-\w]+\/[-.\w]+?)(?:\.git|)$')


def github_validator(value):
    if not re.match(GITHUB_REGEXP, value):
        raise ValidationError('Invalid github repo url')
    return value


class Report(models.Model):

    created_on = models.DateTimeField(default=datetime.now)

    hash = models.CharField(unique=True, max_length=40)
    url = models.URLField(
        verify_exists=False, validators=[RegexValidator(GITHUB_REGEXP)]
    )
    github_url = models.CharField(max_length=255)
    stage = models.CharField(max_length=10, default='queue')
    error = models.TextField(blank=True, null=True)

    objects = ReportManager()

    class Meta:
        ordering = ['-created_on']

    def __unicode__(self):
        return self.url

    def save(self, *args, **kwargs):
        if not self.hash:
            salt = sha_constructor(str(random.random())).hexdigest()[:5]
            salt += str(time.time()) + self.url
            self.hash = sha_constructor(salt).hexdigest()
        if not self.github_url:
            match = re.match(GITHUB_REGEXP, self.url)
            if match:
                self.github_url = match.group(1)
        super(Report, self).save(*args, **kwargs)

    def expired(self):
        expiration_date = timedelta(days=EXPIRATION_DAYS) + self.created_on
        return datetime.now() > expiration_date

    @models.permalink
    def get_absolute_url(self):
        return ('lint_results', (), {'hash': self.hash})


class Fix(models.Model):

    report = models.ForeignKey(Report, related_name='fixes')
    description = models.TextField()
    description_html = models.TextField()
    path = models.CharField(max_length=255)
    line = models.PositiveIntegerField()
    source = models.TextField()
    solution = models.TextField()

    class Meta:
        ordering = ['path', 'line']

    def save(self, *args, **kwargs):
        self.description_html = rst2html(self.description)
        super(Fix, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = parsers
import ast
import os


class Parser(object):
    """
    Find all *.py files inside `repo_path` and parse its into ast nodes.

    If file has syntax errors SyntaxError object will be returned except
    ast node.
    """

    def __init__(self, repo_path):
        if not os.path.isabs(repo_path):
            raise ValueError('Repository path is not absolute: %s' % repo_path)
        self.repo_path = repo_path

    def walk(self):
        """
        Yield absolute paths to all *.py files inside `repo_path` directory.
        """
        for root, dirnames, filenames in os.walk(self.repo_path):
            for filename in filenames:
                if filename.endswith('.py'):
                    yield os.path.join(root, filename)

    def relpath(self, path):
        return os.path.relpath(path, self.repo_path)

    def parse_file(self, path):
        relpath = self.relpath(path)
        with open(path) as f:
            content = f.read()
        try:
            return (relpath, ast.parse(content, relpath))
        except SyntaxError, e:
            return (relpath, e)

    def parse(self):
        return dict(self.parse_file(filepath) for filepath in self.walk())

########NEW FILE########
__FILENAME__ = settings
import os
from django.conf import settings


CONFIG = {
    'REPORT_EXPIRATION_DAYS': 30,
    'CLONES_ROOT': os.path.join(settings.PROJECT_ROOT, 'cloned_repos'),
    'MAX_TARBALL_SIZE': 26214400,
    'GITHUB_TIMEOUT': 30.0,
}
CONFIG.update(getattr(settings, 'LINT_CONFIG', {}))

########NEW FILE########
__FILENAME__ = tasks
from celery.task import task
from django.conf import settings
from django.utils import simplejson as json
from .analyzers.loader import get_analyzers
from .ghclone import clone
from .models import Fix, Report
from .parsers import Parser


def parse(path):
    return Parser(path).parse()


def save_result(report, result):
    source = json.dumps(result.source)
    solution = json.dumps(result.solution)
    path = '/'.join(result.path.split('/')[1:]) # Remove archive dir name from result path
    Fix.objects.create(
        report=report, line=result.line, description=result.description,
        path=path, source=source, solution=solution
    )


def exception_handle(func):
    def decorator(report_pk, commit_hash=None):
        try:
            func(report_pk, commit_hash)
        except Exception, e:
            report = Report.objects.get(pk=report_pk)
            report.error = '%s: %s' % (e.__class__.__name__, unicode(e))
            report.save()
    decorator.__name__ = func.__name__
    return decorator


@task()
@exception_handle
def process_report(report_pk, commit_hash=None):
    report = Report.objects.get(pk=report_pk)
    report.stage = 'cloning'
    report.save()

    with clone(report.github_url, commit_hash) as path:
        report.stage = 'parsing'
        report.save()
        parsed_code = parse(path)

        report.stage = 'analyzing'
        report.save()
        for analyzer in get_analyzers():
            for result in analyzer(parsed_code, path).analyze():
                save_result(report, result)
        report.stage = 'done'
        report.save()

########NEW FILE########
__FILENAME__ = lint
from django.template import Library
from django.utils import simplejson as json

from ..forms import ReportForm
from ..models import Report


register = Library()


@register.inclusion_tag('lint/tags/report_create_form.html', takes_context=True)
def report_create_form(context):
    report_pk = context.get('report_pk')
    initial_data = {}
    if report_pk is not None:
        try:
            report = Report.objects.get(pk=report_pk)
        except Report.DoesNotExist:
            report = None
        else:
            initial_data['url'] = report.url
    return {'form': ReportForm(initial=initial_data)}


@register.inclusion_tag('lint/tags/results_fix.html')
def results_fix(fix):
    source_result, solution_result = [], []
    for line_info in json.loads(fix.source):
        source_result.append({
            'number': line_info[0],
            'is_significant': line_info[1],
            'text': line_info[2],
        })
    for line_info in json.loads(fix.solution):
        solution_result.append({
            'number': line_info[0],
            'is_significant': line_info[1],
            'text': line_info[2],
        })
    return {'source_result': source_result, 'fix': fix,
            'solution_result': solution_result}

########NEW FILE########
__FILENAME__ = base
import os


TESTS_ROOT = os.path.abspath(os.path.dirname(__file__))

EXAMPLE_PROJECT_FILES = [
    '__init__.py',
    'app/__init__.py',
    'app/admin.py',
    'app/forms.py',
    'app/models.py',
    'app/tests.py',
    'app/urls.py',
    'app/views.py',
    'bad_code.py',
    'good_code.py',
    'settings.py',
    'syntax_error.py',
]

########NEW FILE########
__FILENAME__ = admin

########NEW FILE########
__FILENAME__ = forms

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.patterns import patterns, url
from django.views.generic.simple import redirect_to


urlpatterns = patterns('',
    url(r'^redirect$', redirect_to, {'url': '/'}),
    url(r'^list$', 'messages.views.message_list'),
)

########NEW FILE########
__FILENAME__ = views
import django.views.generic.simple
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.generic import list_detail
from django.views.generic.list_detail import object_detail, object_list


def index(request):
    return django.views.generic.simple.direct_to_template(
        request,
        template_name='messages/index.html')


def redirect(request):
    view = django.views.generic.simple.redirect_to
    return view(request, url='/messages/list/')


def message_list(request):
    queryset = Message.objects.filter(site=request.site)
    return list_detail.object_list(request, queryset=queryset)


def message_detail(request, object_id):
    queryset = Message.objects.filter(site=request.site)
    return object_detail(request, queryset=queryset, object_id=object_id)


def create_message(request):
    from django.views.generic.create_update import create_object
    return create_object(request)


def fake_create_message(request):
    create_object = lambda x: x
    return create_object(request)


def random_message(request):
    message = Message.objects.order_by('?')[0]
    return render_to_response('messages/random.html', {'message': message},
                              context_instance=RequestContext(request))


@decorator('something')
def another_random_message(request):
    message = Message.objects.order_by('?')[0]
    return render_to_response('messages/random.html', {'message': message},
                              context_instance=RequestContext(request))


def random_message_without_request_context(request):
    message = Message.objects.order_by('?')[0]
    return render_to_response('messages/random.html', {'message': message})


def get_form_with_security_hash(request):
    from django.contrib.formtools.utils import security_hash
    form = MessageForm()
    hash = security_hash(request, form)
    return render_to_response('messages/form.html', {'form': form, 'hash': hash})


def request_context(request):
    request_context = RequestContext(request)

########NEW FILE########
__FILENAME__ = bad_code

########NEW FILE########
__FILENAME__ = good_code

########NEW FILE########
__FILENAME__ = settings
DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS


MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)


TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.PermWrapper',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.PermLookupDict',
    'django.contrib.messages.context_processors.messages',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'project',
    }
}

########NEW FILE########
__FILENAME__ = syntax_error
def main():
    syntax error


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_analyzers_result
from django.test import TestCase
from ..analyzers.base import Result, CodeSnippet


class ResultTests(TestCase):

    def test_init(self):
        result = Result('simple result', 'app/models.py', 2)
        self.assertEqual(result.description, 'simple result')
        self.assertEqual(result.path, 'app/models.py')
        self.assertEqual(result.line, 2)
        self.assertIsInstance(result.source, CodeSnippet)
        self.assertIsInstance(result.solution, CodeSnippet)

########NEW FILE########
__FILENAME__ = test_attribute_visitor
import ast
from django.test import TestCase
from ..analyzers.base import AttributeVisitor


class AttributeVisitorTests(TestCase):

    def get_attribute_node(self, source):
        return ast.parse(source).body[0].value

    def test_usable(self):
        visitor = AttributeVisitor()
        visitor.visit(self.get_attribute_node('foo.bar.baz'))
        self.assertEqual(visitor.is_usable, True)
        self.assertEqual(visitor.get_name(), 'foo.bar.baz')

    def test_unusable(self):
        visitor = AttributeVisitor()
        visitor.visit(self.get_attribute_node('(foo or bar).baz'))
        self.assertEqual(visitor.is_usable, False)

########NEW FILE########
__FILENAME__ = test_base_analyzer
import os
from django.test import TestCase
from .base import TESTS_ROOT, EXAMPLE_PROJECT_FILES

from ..analyzers.base import BaseAnalyzer
from ..parsers import Parser


class CustomAnalyzer(BaseAnalyzer):

    def analyze_file(self, filepath, code):
        yield filepath


class BaseAnalyzerTests(TestCase):

    def setUp(self):
        self.example_project = os.path.join(TESTS_ROOT, 'example_project')
        self.code_dict = Parser(self.example_project).parse()
        self.analyzer = BaseAnalyzer(self.code_dict, self.example_project)

    def test_init(self):
        self.assertEqual(self.analyzer.surround_by, 2)
        self.assertEqual(self.analyzer.code_dict, self.code_dict)
        self.assertEqual(self.analyzer.repo_path, self.example_project)

    def test_file_lines(self):
        lines = list(self.analyzer.get_file_lines('syntax_error.py', 1, 2))
        self.assertEqual(lines, [
            [1, True,  'def main():'],
            [2, True,  '    syntax error'],
            [3, False, ''],
            [4, False, ''],
        ])

        lines = list(self.analyzer.get_file_lines('syntax_error.py', 3, 3))
        self.assertEqual(lines, [])

        lines = list(self.analyzer.get_file_lines('syntax_error.py', 6, 6))
        self.assertEqual(lines, [
            [4, False, ''],
            [5, False, "if __name__ == '__main__':"],
            [6, True,  '    main()'],
        ])

    def test_analyze_file(self):
        with self.assertRaises(NotImplementedError):
            self.analyzer.analyze_file(*self.code_dict.items()[0])

    def test_analyze(self):
        results = CustomAnalyzer(self.code_dict, self.example_project).analyze()
        self.assertItemsEqual(list(results), EXAMPLE_PROJECT_FILES)

########NEW FILE########
__FILENAME__ = test_code_snippet
from django.test import TestCase
from ..analyzers.base import CodeSnippet


class CodeSnippetTests(TestCase):

    def test_add_line(self):
        snippet = CodeSnippet()
        snippet.add_line(1, 'first line')
        snippet.add_line(2, 'second line', important=False)
        self.assertItemsEqual(snippet, [
            (1, True, 'first line'),
            (2, False, 'second line'),
        ])

########NEW FILE########
__FILENAME__ = test_context_processors_analyzer
import os
from django.test import TestCase

from ..analyzers.context_processors import ContextProcessorsAnalyzer
from ..parsers import Parser

from .base import TESTS_ROOT


class ContextProcessorsAnalyzerTests(TestCase):

    def setUp(self):
        self.maxDiff = None
        self.example_project = os.path.join(TESTS_ROOT, 'example_project')
        self.code = Parser(self.example_project).parse()
        self.analyzer = ContextProcessorsAnalyzer(self.code, self.example_project)

    def test_analyze(self):
        results = list(self.analyzer.analyze())
        self.assertEqual(len(results), 3)
        self.assertItemsEqual(results[0].source, [
            (18, False, ""),
            (19, False, "TEMPLATE_CONTEXT_PROCESSORS = ("),
            (20, True,  "    'django.core.context_processors.auth',"),
            (21, False, "    'django.core.context_processors.debug',"),
            (22, False, "    'django.core.context_processors.i18n',"),
        ])
        self.assertItemsEqual(results[0].solution, [
            (18, False, ""),
            (19, False, "TEMPLATE_CONTEXT_PROCESSORS = ("),
            (20, True,  "    'django.contrib.auth.context_processors.auth',"),
            (21, False, "    'django.core.context_processors.debug',"),
            (22, False, "    'django.core.context_processors.i18n',"),
        ])

########NEW FILE########
__FILENAME__ = test_db_backends_analyzer
import os
from django.test import TestCase

from ..analyzers.db_backends import DB_BackendsAnalyzer
from ..parsers import Parser

from .base import TESTS_ROOT


class DB_BackendsAnalyzerTests(TestCase):

    def setUp(self):
        self.maxDiff = None
        self.example_project = os.path.join(TESTS_ROOT, 'example_project')
        self.code = Parser(self.example_project).parse()
        self.analyzer = DB_BackendsAnalyzer(self.code, self.example_project)

    def test_analyze(self):
        results = list(self.analyzer.analyze())
        self.assertEqual(len(results), 1)
        self.assertItemsEqual(results[0].source, [
            (35, False, "DATABASES = {"),
            (36, False, "    'default': {"),
            (37, True,  "        'ENGINE': 'django.db.backends.postgresql',"),
            (38, False, "        'NAME': 'project',"),
            (39, False, "    }"),
        ])
        self.assertItemsEqual(results[0].solution, [
            (35, False, "DATABASES = {"),
            (36, False, "    'default': {"),
            (37, True,  "        'ENGINE': 'django.db.backends.postgresql_psycopg2',"),
            (38, False, "        'NAME': 'project',"),
            (39, False, "    }"),
        ])

########NEW FILE########
__FILENAME__ = test_formtools_analyzer
import os
from django.test import TestCase

from ..analyzers.formtools import FormToolsAnalyzer
from ..parsers import Parser

from .base import TESTS_ROOT


class FormToolsAnalyzerTests(TestCase):

    def setUp(self):
        self.example_project = os.path.join(TESTS_ROOT, 'example_project')
        self.code = Parser(self.example_project).parse()
        self.analyzer = FormToolsAnalyzer(self.code, self.example_project)

    def test_analyze(self):
        results = list(self.analyzer.analyze())
        self.assertEqual(len(results), 1)
        self.assertItemsEqual(results[0].source, [
            (58, False, '    from django.contrib.formtools.utils import security_hash'),
            (59, False, '    form = MessageForm()'),
            (60, True,  '    hash = security_hash(request, form)'),
            (61, False, '    return render_to_response(\'messages/form.html\', {\'form\': form, \'hash\': hash})'),
            (62, False, ''),
        ])

########NEW FILE########
__FILENAME__ = test_generic_views_analyzer
import os
from django.test import TestCase

from ..analyzers.generic_views import GenericViewsAnalyzer
from ..parsers import Parser

from .base import TESTS_ROOT


class GenericViewsAnalyzerTests(TestCase):

    def setUp(self):
        self.example_project = os.path.join(TESTS_ROOT, 'example_project')
        self.code = Parser(self.example_project).parse()
        self.analyzer = GenericViewsAnalyzer(self.code, self.example_project)

    def test_analyze(self):
        results = list(self.analyzer.analyze())
        self.assertEqual(len(results), 6)
        self.assertItemsEqual(results[0].source, [
            (4, False, ''),
            (5, False, "urlpatterns = patterns('',"),
            (6, True,  "    url(r'^redirect$', redirect_to, {'url': '/'}),"),
            (7, False, "    url(r'^list$', 'messages.views.message_list'),"),
            (8, False, ')'),
        ])
        self.assertItemsEqual(results[1].source, [
            (7,  False, ''),
            (8,  False, 'def index(request):'),
            (9,  True,  '    return django.views.generic.simple.direct_to_template('),
            (10, True,  '        request,'),
            (11, True,  "        template_name='messages/index.html')"),
            (12, False, ''),
            (13, False, ''),
        ])
        self.assertItemsEqual(results[2].source, [
            (14, False, 'def redirect(request):'),
            (15, False, '    view = django.views.generic.simple.redirect_to'),
            (16, True,  "    return view(request, url='/messages/list/')"),
            (17, False, ''),
            (18, False, ''),
        ])

########NEW FILE########
__FILENAME__ = test_ghclone
from __future__ import with_statement

import errno
import os
import mock

from django.test import TestCase

from ..ghclone import CloneError, tempdir, clone
from ..models import Report


class TempDirTests(TestCase):

    def setUp(self):
        self.makedirs_patcher = mock.patch('os.makedirs')
        self.mkdtemp_patcher = mock.patch('tempfile.mkdtemp')
        self.rmtree_patcher = mock.patch('shutil.rmtree')

        self.makedirs = self.makedirs_patcher.start()
        self.mkdtemp = self.mkdtemp_patcher.start()
        self.rmtree = self.rmtree_patcher.start()

    def tearDown(self):
        self.makedirs_patcher.stop()
        self.mkdtemp_patcher.stop()
        self.rmtree_patcher.start()

    def test_creates_temp_dir(self):
        with tempdir(root='root') as path:
            pass
        self.mkdtemp.assert_called_once_with(dir='root')
        self.assertEqual(path, self.mkdtemp.return_value)

    def test_doesnt_require_explicit_root(self):
        with tempdir() as path:
            pass
        self.mkdtemp.assert_called_once_with(dir=None)

    def test_tries_to_create_root_if_passed(self):
        with tempdir(root='root') as path:
            pass
        self.makedirs.assert_called_once_with('root')

    def test_passes_silenty_if_root_already_exists(self):
        self.makedirs.side_effect = OSError(errno.EEXIST, 'File exists', 'root')
        with tempdir(root='root') as path:
            pass

    def test_raises_oserror_if_cannot_create_root(self):
        self.makedirs.side_effect = OSError(errno.EACCES, 'Permission denied', 'root')
        with self.assertRaises(OSError):
            with tempdir(root='root') as path:
                pass

    def test_doesnt_try_to_create_root_if_isnt_passed(self):
        with tempdir() as path:
            pass
        self.assertFalse(self.makedirs.called)

    def test_removes_dir_on_the_exit(self):
        with tempdir() as path:
            self.assertFalse(self.rmtree.called)
        self.rmtree.assert_called_once_with(path)

    def test_removes_dir_if_exception_is_raised(self):
        try:
            with tempdir() as path:
                raise Exception
        except Exception:
            pass
        self.rmtree.assert_called_once_with(path)


class CloneTests(TestCase):

    def setUp(self):
        self.report1 = Report.objects.create(url='https://github.com/yumike/djangolint')
        self.report2 = Report.objects.create(url='https://github.com/xobb1t/notexistentrepo')
        self.report3 = Report.objects.create(url='https://github.com/mirrors/linux')

    def test_clone(self):
        with clone(self.report1.github_url) as path:
            self.assertTrue(os.path.exists(path))
        with self.assertRaises(CloneError):
            with clone(self.report2.github_url):
                pass
        with self.assertRaises(CloneError):
            with clone(self.report3.github_url):
                pass

########NEW FILE########
__FILENAME__ = test_models
from datetime import datetime, timedelta

from django.test import TestCase

from ..models import Report, Fix
from ..settings import CONFIG


def create_fix(**kwargs):
    kwargs['line'] = 0
    kwargs['report'] = Report.objects.create(url='https://github.com/django/django')
    return Fix.objects.create(**kwargs)


class ReportTestCase(TestCase):

    def setUp(self):
        expiration_days = CONFIG['REPORT_EXPIRATION_DAYS']
        self.report1 = Report.objects.create(url='https://github.com/django/django')
        expired_datetime = datetime.now() - timedelta(days=expiration_days+1)
        self.report2 = Report.objects.create(
            url='https://github.com/yumike/djangolint', created_on=expired_datetime
        )

    def test_expired(self):
        self.assertFalse(self.report1.expired())
        self.assertTrue(self.report2.expired())

    def test_delete_expired(self):
        Report.objects.delete_expired()
        qs = Report.objects.all()

        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0].pk, 1)


class FixTestCase(TestCase):

    def setUp(self):
        self.fix = create_fix(description='Fix description.')

    def test_caches_description_html(self):
        self.assertEqual(self.fix.description_html, '<p>Fix description.</p>\n')

    def test_updates_description_html(self):
        self.fix.description = 'Updated fix description.'
        self.fix.save()
        self.assertEqual(self.fix.description_html, '<p>Updated fix description.</p>\n')

########NEW FILE########
__FILENAME__ = test_parsers
from __future__ import with_statement

import ast
import os

from django.test import TestCase
from .base import TESTS_ROOT, EXAMPLE_PROJECT_FILES
from ..parsers import Parser


class ParserTests(TestCase):

    def setUp(self):
        self.example_project = os.path.join(TESTS_ROOT, 'example_project')

    def test_init_with_absolute_path(self):
        parser = Parser(self.example_project)
        self.assertEqual(parser.repo_path, self.example_project)

    def test_init_with_relative_path(self):
        with self.assertRaises(ValueError):
            parser = Parser('relative/path')

    def test_walk(self):
        parser = Parser(self.example_project)
        self.assertItemsEqual(
            parser.walk(),
            [os.path.join(self.example_project, x) for x in EXAMPLE_PROJECT_FILES]
        )

    def test_relpath(self):
        parser = Parser(self.example_project)
        path = os.path.join(self.example_project, 'app/models.py')
        self.assertEqual(parser.relpath(path), 'app/models.py')

    def test_parse_file(self):
        parser = Parser(self.example_project)
        path = os.path.join(self.example_project, 'app/models.py')
        code = parser.parse_file(path)
        self.assertIsInstance(code, tuple)
        self.assertIsInstance(code[1], ast.Module)
        self.assertEqual(code[0], 'app/models.py')

    def test_parse_file_with_syntax_error(self):
        parser = Parser(self.example_project)
        path = os.path.join(self.example_project, 'syntax_error.py')
        code = parser.parse_file(path)
        self.assertIsInstance(code, tuple)

    def test_parse_non_existent_file(self):
        parser = Parser(self.example_project)
        path = os.path.join(self.example_project, 'non_existent.py')
        with self.assertRaises(IOError):
            code = parser.parse_file(path)

    def test_parse(self):
        parser = Parser(self.example_project)
        code = parser.parse()
        self.assertIsInstance(code, dict)
        self.assertItemsEqual(parser.parse(), EXAMPLE_PROJECT_FILES)

########NEW FILE########
__FILENAME__ = test_render_to_response_analyzer
import os
from django.test import TestCase

from ..analyzers.render_to_response import RenderToResponseAnalyzer
from ..parsers import Parser

from .base import TESTS_ROOT


class RenderToResponseAnalyzerTests(TestCase):

    def setUp(self):
        self.example_project = os.path.join(TESTS_ROOT, 'example_project')
        self.code = Parser(self.example_project).parse()
        self.analyzer = RenderToResponseAnalyzer(self.code, self.example_project)

    def test_analyze(self):
        results = list(self.analyzer.analyze())
        self.assertEqual(len(results), 2)
        self.assertIn("this 'render_to_response'", results[0].description)
        self.assertItemsEqual(results[0].source, [
            (39, False, 'def random_message(request):'),
            (40, False, "    message = Message.objects.order_by('?')[0]"),
            (41, True,  "    return render_to_response('messages/random.html', {'message': message},"),
            (42, True, '                              context_instance=RequestContext(request))'),
            (43, False, ''),
            (44, False, ''),
        ])
        self.assertItemsEqual(results[1].source, [
            (46, False, 'def another_random_message(request):'),
            (47, False, "    message = Message.objects.order_by('?')[0]"),
            (48, True,  "    return render_to_response('messages/random.html', {'message': message},"),
            (49, True, '                              context_instance=RequestContext(request))'),
            (50, False, ''),
            (51, False, ''),
        ])

########NEW FILE########
__FILENAME__ = test_syntax_error_analyzer
import os
from django.test import TestCase
from .base import TESTS_ROOT

from ..analyzers.syntax_error import SyntaxErrorAnalyzer
from ..parsers import Parser


class SyntaxErrorAnalyzerTests(TestCase):

    def setUp(self):
        self.example_project = os.path.join(TESTS_ROOT, 'example_project')
        self.code = Parser(self.example_project).parse()

    def test_analyze(self):
        analyzer = SyntaxErrorAnalyzer(self.code, self.example_project)
        results = list(analyzer.analyze())
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.description, 'Syntax error: invalid syntax.')
        self.assertEqual(result.path, 'syntax_error.py')
        self.assertEqual(result.line, 2)
        self.assertItemsEqual(result.source, [
            (1, False, 'def main():'),
            (2, True,  '    syntax error'),
            (3, False, ''),
            (4, False, ''),
        ])
        self.assertItemsEqual(result.solution, [])

########NEW FILE########
__FILENAME__ = test_template_loaders_analyzer
import os
from django.test import TestCase

from ..analyzers.template_loaders import TemplateLoadersAnalyzer
from ..parsers import Parser

from .base import TESTS_ROOT


class TemplateLoadersAnalyzerTests(TestCase):

    def setUp(self):
        self.maxDiff = None
        self.example_project = os.path.join(TESTS_ROOT, 'example_project')
        self.code = Parser(self.example_project).parse()
        self.analyzer = TemplateLoadersAnalyzer(self.code, self.example_project)

    def test_analyze(self):
        results = list(self.analyzer.analyze())
        self.assertEqual(len(results), 2)
        self.assertItemsEqual(results[0].source, [
            (29, False, ''),
            (30, False, 'TEMPLATE_LOADERS = ('),
            (31, True,  "    'django.template.loaders.filesystem.load_template_source',"),
            (32, False, "    'django.template.loaders.app_directories.load_template_source',"),
            (33, False, ')'),
        ])
        self.assertItemsEqual(results[0].solution, [
            (29, False, ''),
            (30, False, 'TEMPLATE_LOADERS = ('),
            (31, True,  "    'django.template.loaders.filesystem.Loader',"),
            (32, False, "    'django.template.loaders.app_directories.load_template_source',"),
            (33, False, ')'),
        ])

########NEW FILE########
__FILENAME__ = test_utils
# -*- coding: utf-8 -*-
from django.test import TestCase
from ..utils import rst2html


class RST2HTMLTests(TestCase):

    def test_converts_rst_to_html(self):
        result = rst2html('Fix *description*.')
        self.assertEqual(result, '<p>Fix <em>description</em>.</p>\n')

    def test_handles_unicode(self):
        result = rst2html(u'Описание фикса.')
        self.assertEqual(result, u'<p>Описание фикса.</p>\n')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('lint.views',
    url(r'^$', 'index', name='lint_create'),
    url(r'^create$', 'create', name='lint_report_create'),
    url(r'^get_status$', 'get_status', name='lint_report_get_status'),
    url(r'^results/(?P<hash>[a-f0-9]{40})$', 'results', name='lint_results'),
)
########NEW FILE########
__FILENAME__ = utils
from django.utils.encoding import force_unicode, smart_str
from docutils.core import publish_parts


def rst2html(text):
    parts = publish_parts(source=smart_str(text), writer_name='html4css1')
    return force_unicode(parts['fragment'])

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import simplejson as json
from django.views.decorators.http import require_POST

from .forms import ReportForm
from .models import Report, STAGES
from .tasks import process_report


def index(request):
    report = None
    report_pk = request.session.get('report_pk')
    if report_pk is not None:
        try:
            report = Report.objects.get(pk=report_pk)
        except Report.DoesNotExist:
            pass
    return render(request, 'lint/form.html', {'report': report})


@require_POST
def create(request):
    form = ReportForm(data=request.POST)
    report_pk = request.session.get('report_pk')
    try:
        report = Report.objects.get(pk=report_pk)
    except Report.DoesNotExist:
        report = None

    if not (report is None or report.stage == 'done' or report.error):
        data = {'status': 'error', 'error': 'You are already in the queue'}
    elif form.is_valid():
        report = form.save()
        request.session['report_pk'] = report.pk
        process_report.delay(report.pk)
        data = {'status': 'ok', 'url': report.get_absolute_url()}
    else:
        data = {'status': 'error', 'error': 'Invalid URL'}
    return HttpResponse(json.dumps(data), mimetype='application/json')


def get_status(request):
    pk = request.session.get('report_pk')
    if pk is not None:
        result = ['waiting', 'waiting', 'waiting', 'waiting']
        report = get_object_or_404(Report, pk=pk)
        stage = report.stage
        stage_index = STAGES.index(stage)
        for status in range(stage_index):
            result[status] = 'done'
        if stage != 'done':
            result[stage_index] = 'working'
        if report.error:
            result[stage_index] = 'error'
        data = {'queue': result[0], 'cloning': result[1],
                'parsing': result[2], 'analyzing': result[3]}
        return HttpResponse(json.dumps(data), mimetype='application/json')
    return HttpResponse()


def results(request, hash):
    qs = Report.objects.filter(stage='done')
    qs = qs.exclude(error='')
    report = get_object_or_404(qs, hash=hash)
    return render(request, 'lint/results.html', {'report': report})

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = context_processors
from .models import User


def user(request):
    return {'user': request.user}

########NEW FILE########
__FILENAME__ = middleware
from django.utils.functional import SimpleLazyObject
from .models import User, AnonymousUser


def get_user(request):
    user_id = request.session.get('user_id')
    if user_id is None:
        return AnonymousUser()
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class UserMiddleware(object):

    def process_request(self, request):
        request.user = SimpleLazyObject(lambda: get_user(request))

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'User'
        db.create_table('oauth_user', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('github_id', self.gf('django.db.models.fields.IntegerField')(unique=True)),
            ('github_access_token', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('username', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('full_name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=255)),
        ))
        db.send_create_signal('oauth', ['User'])


    def backwards(self, orm):
        
        # Deleting model 'User'
        db.delete_table('oauth_user')


    models = {
        'oauth.user': {
            'Meta': {'object_name': 'User'},
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '255'}),
            'full_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'github_access_token': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'github_id': ('django.db.models.fields.IntegerField', [], {'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['oauth']

########NEW FILE########
__FILENAME__ = models
from django.db import models
from github import Github


class AnonymousUser(object):

    def is_authenticated(self):
        return False

    def is_anonymous(self):
        return True


class User(models.Model):

    github_id = models.IntegerField(unique=True)
    github_access_token = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)

    def __unicode__(self):
        return self.full_name or self.username

    @property
    def github(self):
        return Github(self.github_access_token)

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

########NEW FILE########
__FILENAME__ = oauth
from django.conf import settings
from django.template import Library

from ..utils import get_oauth_handler, get_gravatar_url


register = Library()


@register.simple_tag
def github_auth_url():
    oauth_handler = get_oauth_handler()
    return oauth_handler.authorize_url(settings.GITHUB['SCOPES'])


@register.simple_tag
def gravatar_url(email, size):
    return get_gravatar_url(email, size)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import url, patterns
from .views import callback, logout


urlpatterns = patterns('',
    url(r'^callback/$', callback, name='oauth_callback'),
    url(r'^logout/$', logout, name='oauth_logout'),
)

########NEW FILE########
__FILENAME__ = utils
import hashlib
import urllib

from django.conf import settings
from github import Github
from requests_oauth2 import OAuth2

from .models import User


def get_oauth_handler():
    GITHUB = settings.GITHUB
    return OAuth2(
        GITHUB['CLIENT_ID'], GITHUB['CLIENT_SECRET'], GITHUB['AUTH_URL'],
        '', GITHUB['AUTHORIZE_URL'], GITHUB['TOKEN_URL']
    )


def get_user(access_token):
    api = Github(access_token)
    github_user = api.get_user()
    user, created = User.objects.get_or_create(
        github_id=github_user.id, defaults={
            'username': github_user.login,
            'full_name': github_user.name,
            'email': github_user.email,
            'github_access_token': access_token,
        }
    )
    if not created:
        #  Catch situation when user has changed his login
        user.username = github_user.login
        #  Or access token has been changed.
        user.github_access_token = access_token
        user.save()
    return user


def get_gravatar_url(email, size, default='identicon'):
    gravatar_url = 'http://www.gravatar.com/avatar/'
    hash = hashlib.md5(email.lower()).hexdigest()
    params = urllib.urlencode({'s': str(size), 'd': default})
    return gravatar_url + hash + '?' + params

########NEW FILE########
__FILENAME__ = views
from django.http import Http404
from django.shortcuts import redirect

from .utils import get_oauth_handler, get_user


def callback(request):
    oauth2_handler = get_oauth_handler()
    code = request.GET.get('code')
    if code is None:
        raise Http404
    response = oauth2_handler.get_token(code)
    if not response or response.get('access_token') is None:
        #  TODO: Show message to user, that something went wrong?
        return redirect('lint_create')
    access_token = response['access_token'][0]
    user = get_user(access_token)
    request.session['user_id'] = user.pk
    return redirect('lint_create')


def logout(request):
    if 'user_id' in request.session:
        del request.session['user_id']
    return redirect('lint_create')

########NEW FILE########
__FILENAME__ = common
# Django settings for project project.
import os
import string
from random import choice


PROJECT_ROOT = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..')

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
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

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'public', 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'public', 'static')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, 'static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

SECRET_KEY_FILE = os.path.join(PROJECT_ROOT, 'secret.txt')
if not os.path.exists(SECRET_KEY_FILE):
    SECRET_KEY = ''.join([choice(string.letters + string.digits + string.punctuation) for i in range(50)])
    with open(SECRET_KEY_FILE, 'w') as f:
        f.write(SECRET_KEY)
else:
    with open(SECRET_KEY_FILE) as f:
        SECRET_KEY = f.read()

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'oauth.middleware.UserMiddleware',
)


TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'lint.context_processors.report_pk',
    'oauth.context_processors.user',
)


ROOT_URLCONF = 'project.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'oauth',
    'lint',
    'south',
    'djcelery',
    'compressor',
    'webhooks',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

COMPRESS_CSS_FILTERS = (
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.CSSMinFilter',
)

LINT_ANALYZERS = (
    'lint.analyzers.context_processors.ContextProcessorsAnalyzer',
    'lint.analyzers.db_backends.DB_BackendsAnalyzer',
    'lint.analyzers.formtools.FormToolsAnalyzer',
    'lint.analyzers.generic_views.GenericViewsAnalyzer',
    'lint.analyzers.render_to_response.RenderToResponseAnalyzer',
    'lint.analyzers.syntax_error.SyntaxErrorAnalyzer',
    'lint.analyzers.template_loaders.TemplateLoadersAnalyzer',
)


import djcelery
djcelery.setup_loader()

CELERY_IGNORE_RESULT = True
CELERYD_MAX_TASKS_PER_CHILD = 1
CELERYD_CONCURRENCY = 2

GITHUB = {
    'CLIENT_ID': os.environ.get('GITHUB_ID'),
    'CLIENT_SECRET': os.environ.get('GITHUB_SECRET'),
    'AUTH_URL': 'https://github.com/login/',
    'SCOPES': 'public_repo',
    'AUTHORIZE_URL': 'oauth/authorize',
    'TOKEN_URL': 'oauth/access_token'
}

########NEW FILE########
__FILENAME__ = development
import os

from settings.common import *


DEBUG = True
TEMPLATE_DEBUG = DEBUG


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_ROOT, 'sqlite.db'),
    }
}


INSTALLED_APPS +=(
    'djkombu',
)


BROKER_BACKEND = "djkombu.transport.DatabaseTransport"
CELERY_RESULTS_BACKEND = "djkombu.transport.DatabaseTransport"

########NEW FILE########
__FILENAME__ = production
import os

from settings.common import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'project',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': '127.0.0.1:6379',
        'OPTIONS': {
            'DB': 1,
        },
    },
}

BROKER_BACKEND = 'redis'
BROKER_HOST = 'localhost'
BROKER_PORT = 6379
BROKER_VHOST = '0'

PUBLIC_ROOT = os.path.join(
    os.sep, 'usr', 'share', 'nginx', 'www', 'project', 'public'
)
STATIC_ROOT = os.path.join(PUBLIC_ROOT, 'static')
MEDIA_ROOT = os.path.join(PUBLIC_ROOT, 'media')

TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', TEMPLATE_LOADERS),
)

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import patterns, include, url


urlpatterns = patterns('',
    url(r'^oauth/', include('oauth.urls')),
    url(r'^webhooks/', include('webhooks.urls')),
    url(r'^', include('lint.urls')),
)

if settings.DEBUG:
    from django.views.generic import TemplateView
    urlpatterns += patterns(
        '',
        url(r'^404$', TemplateView.as_view(template_name='404.html')),
        url(r'^500$', TemplateView.as_view(template_name='500.html')),
    )

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Commit'
        db.create_table('webhooks_commit', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('hash', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('repo_url', self.gf('django.db.models.fields.URLField')(max_length=255)),
            ('repo_name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('repo_user', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('ref', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('compare_url', self.gf('django.db.models.fields.URLField')(max_length=255)),
            ('committer_name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('committer_email', self.gf('django.db.models.fields.EmailField')(max_length=255)),
            ('message', self.gf('django.db.models.fields.TextField')()),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('webhooks', ['Commit'])

        # Adding unique constraint on 'Commit', fields ['hash', 'repo_name', 'repo_user']
        db.create_unique('webhooks_commit', ['hash', 'repo_name', 'repo_user'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Commit', fields ['hash', 'repo_name', 'repo_user']
        db.delete_unique('webhooks_commit', ['hash', 'repo_name', 'repo_user'])

        # Deleting model 'Commit'
        db.delete_table('webhooks_commit')


    models = {
        'webhooks.commit': {
            'Meta': {'ordering': "['-created_on']", 'unique_together': "(['hash', 'repo_name', 'repo_user'],)", 'object_name': 'Commit'},
            'committer_email': ('django.db.models.fields.EmailField', [], {'max_length': '255'}),
            'committer_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'compare_url': ('django.db.models.fields.URLField', [], {'max_length': '255'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'ref': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'repo_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'repo_url': ('django.db.models.fields.URLField', [], {'max_length': '255'}),
            'repo_user': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['webhooks']

########NEW FILE########
__FILENAME__ = models
from django.db import models


class Commit(models.Model):

    hash = models.CharField(max_length=40)
    repo_url = models.URLField(max_length=255)
    repo_name = models.CharField(max_length=255)
    repo_user = models.CharField(max_length=255)

    ref = models.CharField(max_length=100)
    compare_url = models.URLField(max_length=255)
    committer_name = models.CharField(max_length=255)
    committer_email = models.EmailField(max_length=255)
    message = models.TextField()

    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['hash', 'repo_name', 'repo_user']
        ordering = ['-created_on']

    def __unicode__(self):
        return u'{0}/{1}@{2}'.format(self.repo_user, self.repo_name, self.hash)

########NEW FILE########
__FILENAME__ = tasks
from celery.task import task
from lint.models import Report
from lint.tasks import process_report
from .models import Commit


@task()
def process_commit(commit_pk):
    try:
        commit = Commit.objects.get(pk=commit_pk)
    except Commit.DoesNotExist:
        return
    if commit.report is None:
        commit.report = Report.objects.create(github_url=commit.repo_url)
        commit.save()
    process_report.delay(commit.report.pk, commit.hash)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import url, patterns

from .views import handler


urlpatterns = patterns('',
    url(r'^$', handler, name='webhooks_hook_handler'),
)

########NEW FILE########
__FILENAME__ = utils
def parse_hook_data(data):
    hash = data.get('after')
    compare_url = data.get('compare')
    ref = data.get('ref')
    repo = data.get('repository', {})
    repo_url = repo.get('url')
    repo_name = repo.get('name')
    repo_user = repo.get('owner', {}).get('name')

    commit = data.get('head_commit')
    committer = commit.get('committer')
    committer_name = committer.get('name')
    committer_email = committer.get('email')

    return {
        'hash': hash,
        'compare_url': compare_url,
        'ref': ref,
        'repo_url': repo_url,
        'repo_name': repo_name,
        'repo_user': repo_user,
        'committer_name': committer_name,
        'committer_email': committer_email,
        'message': commit['message'],
    }



########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import simplejson as json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Commit
from .tasks import process_commit
from .utils import parse_hook_data


@require_POST
@csrf_exempt
def handler(request):
    payload = request.POST.get('payload', '')
    try:
        payload_data = json.loads(payload)
    except ValueError:
        return HttpResponseBadRequest()
    hook_data = parse_hook_data(payload_data)
    hash = hook_data.pop('hash')
    repo_name = hook_data.pop('repo_name')
    repo_user = hook_data.pop('repo_user')

    commit, created = Commit.objects.get_or_create(
        hash=hash, repo_name=repo_name,
        repo_user=repo_user, defaults=hook_data
    )
    process_commit.delay(commit.pk)
    return HttpResponse(status=201 if created else 200)

########NEW FILE########
