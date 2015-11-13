__FILENAME__ = admin
# -*- coding: utf-8 -*-
from os.path import join

from django.contrib import admin
from django.db import models
from django.conf import settings

from djintegration.models import Repository, TestReport

admin.site.register(TestReport)
admin.site.register(Repository)

########NEW FILE########
__FILENAME__ = backends

import re
import os
import sys
import shlex
import shutil
from subprocess import Popen, PIPE, STDOUT
from datetime import datetime, timedelta

from djintegration.models import TestReport, Repository
from djintegration.settings import INT_DIR, COV_CANDIDATES, TESTED_APP_DIR
from djintegration.settings import MAX_RUNNING_TIME

MAX_RUN_DELTA = timedelta(seconds=MAX_RUNNING_TIME)


def with_dir(dirname, fun):
    cwd = os.getcwd()
    result = None
    try:
        os.chdir(dirname)
        result = fun()
    finally:
        os.chdir(cwd)
    return result

def line_that_starts_with(log, start):
    for line in log.split('\n'):
        if line.startswith(start):
            return line.split(start)[1].strip()

def is_virtualenv_command(cmd):
    if (cmd.startswith('easy_install') or
        cmd.startswith('pip') or
        cmd.startswith('python')):
        return True
    else:
        return False

class RepoBackend(object):

    use_virtualenv = False
    checkout_cmd = None
    update_cmd = None

    def __init__(self, repo, *args, **kwargs):
        self.repo = repo

    def system(self, commands):
        commands = str(commands)
        print "commands:", commands

        if ";" in commands:
            ret = os.system(commands)
            return "", ret
        else:
            args = shlex.split(commands)
            process = Popen(args, stdout=PIPE, stderr=STDOUT)
            output, errors = process.communicate()
        return output, process.returncode

    def dirname(self):
        return os.path.join(INT_DIR, self.repo.dirname() + '/')

    def app_dirname(self):
        return os.path.join(self.dirname(), TESTED_APP_DIR)

    def cov_dirname(self):
        return os.path.join(INT_DIR, self.repo.dirname() + '-cov/')

    def command_env(self, cmd):
        if is_virtualenv_command(cmd):
            cmd = 'bin/' + cmd
        def _command():
            return self.system(cmd)
        return with_dir(self.dirname(), _command)



    def command_app(self, cmd, use_test_subpath=False):
        if is_virtualenv_command(cmd):
            cmd = '../bin/' + cmd
        def _command():
            return self.system(cmd)
        command_dir = self.dirname() + TESTED_APP_DIR
        if use_test_subpath:
            command_dir += '/' + self.repo.test_subpath
        return with_dir(command_dir, _command)

    def setup_env(self):
        # trash the old virtual env
        try:
            shutil.rmtree(self.dirname())
        except OSError:
            pass

        virtual_env_commands = {
            'vs':'virtualenv --no-site-packages %s',
            'vd':'virtualenv --no-site-packages %s --distribute'
        }
        cmd = virtual_env_commands.get(self.repo.virtual_env_type, None)

        if cmd:
            self.system(cmd % self.dirname())
            self.use_virtualenv = True
        else:
            if not os.path.isdir(self.dirname()):
                os.makedirs(self.dirname())

        # it seems to be the only thing that work properly
        # ./bin/activate fails
        activate_this = self.dirname() + 'bin/activate_this.py'
        execfile(activate_this, dict(__file__=activate_this))

        return self.command_env(self.checkout_cmd %
            (self.repo.url, 'tested_app'))

    def run_tests(self):
        cmds = self.repo.get_test_command()
        cmds = cmds.replace('\r\n', ';;')
        log = ""
        for cmd in cmds.split(';;'):
            if len(cmd):
                out, ret = self.command_app(cmd, use_test_subpath=True)
                log = log + out
        return (log, ret)

    def install(self):
        cmds = self.repo.get_install_command()
        cmds = cmds.replace('\r\n', ';;')
        log = ""
        for cmd in cmds.split(';;'):
            if len(cmd):
                out, ret = self.command_app(cmd, use_test_subpath=True)
                log = log + out
        return (log, ret)

    def teardown_env(self):
        # search for coverage results directory
        cov_dir = None
        for directories in os.walk(self.app_dirname()):
            for candidate in COV_CANDIDATES:
                if candidate in directories[1]:
                    cov_dir = os.path.join(directories[0], candidate)
        if cov_dir:
            try:
                shutil.rmtree(self.cov_dirname())
            except OSError:
                pass
            shutil.move(cov_dir, self.cov_dirname())

    def make_report(self, force=False):
      
        report = self.repo.last_test_report()
        if report:
            delta = datetime.now() - report.creation_date
            if report.state == "running" and delta < MAX_RUN_DELTA:
                print "Last report is still running, running time is %s" % str(delta)
                return report
    
        self.setup_env()
        commit = self.last_commit()
        new_test = None
        
        if self.repo.last_commit == commit:
            print "No new commit since last test."

        if force or self.repo.last_commit != commit or len(commit) == 0:

            author = self.last_commit_author()

            new_test = TestReport(
                repository=self.repo,
                install="Running ...",
                result="Running ...",
                commit=commit,
                author=author,
                state='running',
            )
            new_test.save()
            
            try:
                install_result, returncodeinstall = self.install()
                # mysql text field has a limitation on how large a text field can be
                # 65,535 bytes ~64kb
                mysql_text_limit = 40000
                install_result = install_result[-mysql_text_limit:]

                test_result, returncode = self.run_tests()
                print test_result
                test_result = test_result[-mysql_text_limit:]

            except Exception as e:
                returncode = 1
                install_result = str(e)
                test_result = str(e)

            if returncode == 0:
                result_state = "pass"
            else:
                result_state = "fail"
            new_test.install=install_result
            new_test.result=test_result    
            new_test.state=result_state
            new_test.save()

            # this to avoid to override things that could have been modified in
            # the admin, we fetch the repo again.
            save_repo = Repository.objects.get(pk=self.repo.pk)
            save_repo.state = result_state
            save_repo.last_commit = commit
            save_repo.save()

        self.teardown_env()
        return new_test


    def last_commit(self):
        log, returncode = self.command_app(self.log_cmd)
        return self.get_commit(log)

    def last_commit_author(self):
        log, returncode = self.command_app(self.log_cmd)
        return self.get_author(log)

class GitBackend(RepoBackend):

    checkout_cmd = 'git clone %s %s'
    update_cmd = 'git pull'
    log_cmd = 'git log -n 1'

    def get_commit(self, log):
        return line_that_starts_with(log, 'commit ')

    def get_author(self, log):
        return line_that_starts_with(log, 'Author: ')

class SvnBackend(RepoBackend):

    checkout_cmd = 'svn checkout %s %s'
    update_cmd = 'svn up'
    log_cmd = 'svn info'

    def get_commit(self, log):
        return line_that_starts_with(log, 'Revision: ')

    def get_author(self, log):
        return line_that_starts_with(log, 'Last Changed Author: ')


class MercurialBackend(RepoBackend):

    checkout_cmd = 'hg clone %s %s'
    update_cmd = 'hg pull'
    log_cmd = 'hg log --limit 1'

    def get_commit(self, log):
        return line_that_starts_with(log, 'changeset: ')

    def get_author(self, log):
        return line_that_starts_with(log, 'user: ')


def get_backend(repo):
    if repo.type == 'git':
        return GitBackend(repo)
    elif repo.type == 'svn':
        return SvnBackend(repo)
    elif repo.type == 'hg':
        return MercurialBackend(repo)
        
    raise NotImplementedError("Unsuppoted backend %s", repo.type)
########NEW FILE########
__FILENAME__ = commands

from djintegration.models import Repository, TestReport
from djintegration.backends import get_backend
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

EMAILS = getattr(settings, 'DJANGO_INTEGRATION_MAILS', [])
FROM = getattr(settings, 'DJANGO_INTEGRATION_FROM_MAIL',
    'django-continuous-integration@noreply.com')
TITLE = getattr(settings, 'DJANGO_INTEGRATION_MAIL_TITLE',
    '%s latest tests didn\'t passed')


def make_test_reports(force=False):

    tests_to_report = []

    for repo in Repository.objects.all():
        print "Making test report for %s (%s)" % (repo.name, repo.url)
        backend = get_backend(repo)

        new_test = backend.make_report(force)
        if new_test and new_test.fail():
            tests_to_report.append(new_test)


    for test in tests_to_report:

        repo = test.repository

        if repo.emails:
            emails = repo.emails.split(',')
        else:
            emails = EMAILS

        title = TITLE % repo.url
        message = render_to_string('djintegration/error_email.html',
            {'test':test})

        send_mail(
            title,
            message,
            FROM,
            emails,
            fail_silently=True
        )

########NEW FILE########
__FILENAME__ = forcetestreports
# -*- coding: utf-8 -*-
from django.core.management.base import NoArgsCommand
from django.conf import settings
from djintegration.commands import make_test_reports

class Command(NoArgsCommand):
    """Generate the test reports from the latest commits."""

    help = "Generate the test reports from the latest commits."

    def handle_noargs(self, **options):
        make_test_reports(force=True)

########NEW FILE########
__FILENAME__ = maketestreports
# -*- coding: utf-8 -*-
from django.core.management.base import NoArgsCommand
from django.conf import settings
from djintegration.commands import make_test_reports

class Command(NoArgsCommand):
    """Generate the test reports from the latest commits."""

    help = "Generate the test reports from the latest commits."

    def handle_noargs(self, **options):
        make_test_reports()

########NEW FILE########
__FILENAME__ = models
"""Repositories ``models``."""
from djintegration.settings import INT_DIR

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from datetime import datetime
import string
import hashlib
import os

try:
    from djintegration.tasks import MakeTestReportsTask
except:
    pass

REPOS = (
    ('git', 'Git'),
    ('svn', 'Subversion'),
    ('hg', 'Mercurial'),
)


STATE = (
    ('fail', 'Fail'),
    ('pass', 'Pass'),
    ('running', 'Running'),
)

VIRTUAL_ENV = (
    ('vs', 'Virtualenv with Setuptools'),
    ('vd', 'Virtualenv with Distribute >= 1.4.4'),
    #('bs', 'Buildout with Setuptools'),
    #('bd', 'Buildout with Distribute'),
    ('no', 'No virtual environnement'),
)


class Repository(models.Model):
    """Represent a repository"""

    name = models.CharField(_('Project Name'), blank=False, max_length=100, unique=True)
    url = models.CharField(_('URL'), blank=False, max_length=250)
    type = models.CharField(_('Type'), choices=REPOS, max_length=10, default='git')
    last_commit = models.CharField(_('Last commit'), max_length=100,
        blank=True)
    creation_date = models.DateTimeField(_('creation date'), editable=False,
        default=datetime.now)

    virtual_env_type = models.CharField(_('Virtual environnement'),
        choices=VIRTUAL_ENV, max_length=16, default="vs")

    install_command = models.TextField(_('Install command'),
        blank=True,
        help_text='Default: "python setup.py install"')

    test_subpath = models.CharField(_('Test subpath'), blank=True, max_length=200,
        help_text="Optional subpath to run the test command. Default is '.'")

    test_command = models.TextField(_('Test command'),
        blank=True,
        help_text='Default: "python setup.py test"')

    state = models.CharField(_('State'), choices=STATE, max_length=10, default='fail')

    emails = models.TextField(_('Notification emails'),
        blank=True,
        help_text='Default: settings.DJANGO_INTEGRATION_MAILS, comma separated.')

    def fail(self):
        latest = self.last_test_report()
        if not latest:
            return False
        return latest.state == 'fail'

    def running(self):
        latest = self.last_test_report()
        if not latest:
            return False
        return latest.state == 'running'

    def last_test_report(self):
        try:
            return TestReport.objects.filter(repository=self).latest('creation_date')
        except:
            return None

    def get_install_command(self):
        return self.install_command or 'python setup.py install'

    def get_test_command(self):
        return self.test_command or 'python setup.py test'

    def has_coverage(self):
        cov_dir = os.path.join(INT_DIR, self.dirname() + '-cov/')
        return os.path.exists(cov_dir)

    def dirname(self):
        m = hashlib.md5()
        label = "%s%s" % (self.name, self.url)
        m.update(label)
        return m.hexdigest()

    def coverage_url(self):
        return self.dirname() + '-cov/index.html'

    class Meta:
        get_latest_by = 'creation_date'
        verbose_name = _('Repository')
        verbose_name_plural = _('Repositories')

    def __unicode__(self):
        return "%s" % (self.name)


class TestReport(models.Model):
    """Test report"""
    repository = models.ForeignKey(Repository)
    creation_date = models.DateTimeField(_('creation date'), editable=False,
        default=datetime.now)

    commit = models.CharField(_('Commit'), max_length=100, blank=False)

    install = models.TextField(blank=True)

    result = models.TextField(blank=True)

    author = models.CharField(_('Author'), max_length=100, blank=True)

    state = models.CharField(_('State'), choices=STATE, max_length=10)

    def fail(self):
        return self.state == 'fail'
        
    def running(self):
        return self.state == 'running'

    class Meta:
        verbose_name = _('Test report')
        verbose_name_plural = _('Test reports')

    def __unicode__(self):
        return "Test on %s for %s: %s" % (self.creation_date.strftime("%c"), 
          self.repository.name, self.state)

    def result_summary(self):
        return "<br>".join(self.result.split("\n")[-6:])


########NEW FILE########
__FILENAME__ = settings
# To keep tests running
from django.conf import settings
    
INT_DIR = getattr(settings, 'DJANGO_INTEGRATION_DIRECTORY', '/tmp/dji/')
COV_CANDIDATES = getattr(settings, 'DJANGO_INTEGRATION_COV_CANDIDATES',
        ['htmlcov', 'covhtml', 'cov', 'coverage'])
TESTED_APP_DIR = getattr(settings, 'DJANGO_TESTED_APP_DIR', 'tested_app/')

# 20 minutes max running time for the tests
MAX_RUNNING_TIME = getattr(settings, 'MAX_RUNNING_TIME', 20 * 60)
########NEW FILE########
__FILENAME__ = tasks
import os, datetime
from celery.task import Task
from celery.registry import tasks
from djintegration.models import TestReport
from djintegration.commands import make_test_reports
from djintegration.backends import get_backend

fname = '/tmp/making_reports'



class MakeTestReportsTask(Task):

    def run(self, **kwargs):
        numreports = TestReport.objects.count()
        make_test_reports()

class ForceTestReportsTask(Task):

    def run(self, **kwargs):
        numreports = TestReport.objects.count()
        make_test_reports(force=True)
        
class MakeTestReportTask(Task):

    def run(self, repository, force, **kwargs):

        backend = get_backend(repository)
        backend.make_report(force)
        
########NEW FILE########
__FILENAME__ = djintegration_tags
import datetime
from django.utils.translation import ungettext, ugettext as _
from django import template
register = template.Library()

@register.filter
def date_diff(d):
    if not d:
        return ''

    now = datetime.datetime.now()
    today = datetime.datetime(now.year, now.month, now.day)
    delta = now - d
    delta_midnight = today - d
    days = delta.days
    hours = round(delta.seconds / 3600., 0)
    minutes = round(delta.seconds / 60., 0)
    chunks = (
        (365.0, lambda n: ungettext('year', 'years', n)),
        (30.0, lambda n: ungettext('month', 'months', n)),
        (7.0, lambda n: ungettext('week', 'weeks', n)),
        (1.0, lambda n: ungettext('day', 'days', n)),
    )

    if days < 0:
        return _("just now")

    if days == 0:
        if hours == 0:
            if minutes > 0:
                return ungettext('1 minute ago', \
                    '%(minutes)d minutes ago', minutes) % \
                    {'minutes': minutes}
            else:
                return _("just now")
        else:
            return ungettext('1 hour ago', '%(hours)d hours ago', hours) \
            % {'hours': hours}

    if delta_midnight.days == 0:
        return _("yesterday at %s") % d.strftime("%H:%M")

    count = 0
    for i, (chunk, name) in enumerate(chunks):
        if days >= chunk:
            count = round((delta_midnight.days + 1)/chunk, 0)
            break

    return _('%(number)d %(type)s ago') % \
        {'number': count, 'type': name(count)}

########NEW FILE########
__FILENAME__ = source_control
"""
Django continuous integration test suite.
"""
from djintegration.backends import GitBackend, SvnBackend, MercurialBackend

import unittest
import os
TEST_DIR = os.path.dirname(__file__)

class SourceControlTestCase(unittest.TestCase):
    """Django continuous integration test suite. class"""

    def test_backends(self):

        git = GitBackend('fake')
        log = open(TEST_DIR+'/gitlog.txt').read()
        self.assertEqual(git.get_commit(log),
            '0873bdde7f216304800fe1a22325cb60ee492f54')
        self.assertEqual(git.get_author(log),
            'Batiste Bieler <batisteb@opera.com>')

        svn = SvnBackend('fake')
        log = open(TEST_DIR+'/svninfo.txt').read()
        self.assertEqual(svn.get_commit(log), '466')
        self.assertEqual(svn.get_author(log), 'sehmaschine')

        svn = MercurialBackend('fake')
        log = open(TEST_DIR+'/hglog.txt').read()
        self.assertEqual(svn.get_commit(log), '164:7bc186caa7dc')
        self.assertEqual(svn.get_author(log), 'Tata Toto <toto@toto.com>')
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from djintegration.settings import INT_DIR
from django.views.static import serve

urlpatterns = patterns('djintegration.views',
    url(r'^$', 'latest_reports', name="latest-reports"),
    url(r'^repo/(?P<repo_id>[0-9]+)$', 'repository', name="repository"),
    url(r'^repopart/(?P<repo_id>[0-9]+)$', 'repository_partial', name="repository-partial"),
    url(r'^code/(?P<path>.*)$', serve,
        {'document_root': INT_DIR,  'show_indexes': True}, name='serve-integration-dir'),
    url(r'^makeall$', 'make_reports', name="make-reports"),
    url(r'^forceall$', 'force_reports', name="force-reports"),
    url(r'^make/(?P<repo_id>[0-9]+)$', 'make_report', name="make-report"),
    url(r'^taskstatus/(?P<task_id>[0-9a-zA-Z\-]+)$', 'task_status', name="task-status"),
)

########NEW FILE########
__FILENAME__ = views
import sys
from djintegration.models import Repository, TestReport
from djintegration.tasks import MakeTestReportsTask
from djintegration.tasks import ForceTestReportsTask, MakeTestReportTask
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django import http
from celery.result import AsyncResult

def latest_reports(request):

    repos = list(Repository.objects.filter(state='fail')) + \
        list(Repository.objects.filter(state='pass'))
    
    return render_to_response('djintegration/latest_reports.html',
        RequestContext(request, locals()))
        
def repository(request, repo_id):

    repo = Repository.objects.get(pk=int(repo_id))
    tests = TestReport.objects.filter(repository=repo).order_by('-creation_date')[0:30]

    return render_to_response('djintegration/repository.html',
        RequestContext(request, locals()))
        
def repository_partial(request, repo_id):
    repo = Repository.objects.get(pk=int(repo_id))
    return render_to_response('djintegration/repository_partial.html',
        RequestContext(request, {"repo":repo}))

def make_reports(request):
    if not request.user.is_staff:
        http.HttpResponse("Not allowed")
        
    MakeTestReportsTask.delay()
    response = latest_reports(request)   
    return redirect('/')

def force_reports(request):
    if not request.user.is_staff:
        http.HttpResponse("Not allowed")
        
    ForceTestReportsTask.delay()
    response = latest_reports(request)
    return redirect('/')

def make_report(request, repo_id):
  
    force = request.GET.get("force") == "true"
  
    if not request.user.is_staff:
        http.HttpResponse("Not allowed")

    repo = Repository.objects.get(pk=int(repo_id))
    task = MakeTestReportTask()
    result = task.delay(repo, force)
    
    return http.HttpResponse(result.id)
    
def task_status(request, task_id):

    res = AsyncResult(task_id)
    return http.HttpResponse(str(res.ready()))
    
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
import sys
import os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
sys.path.insert(0, "../")
import djintegration

from django.conf import settings
if not settings.configured:
    settings.configure()

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings.
# They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'djintegration'
copyright = u'2009, Opera Softare (WebTeam)'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ".".join(map(str, djintegration.VERSION[0:2]))
# The full version, including alpha/beta/rc tags.
release = djintegration.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['.build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'trac'

#html_translator_class = "djangodocs.DjangoHTMLTranslator"


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
#html_style = 'agogo.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['.static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
html_use_modindex = True

# If false, no index is generated.
html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'djintegrationdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class
# [howto/manual]).
latex_documents = [
  ('index', 'djintegration.tex', ur'djintegration Documentation',
   ur'Ask Solem', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

html_theme = "nature"
html_theme_path = ["_theme"]

########NEW FILE########
__FILENAME__ = applyxrefs
"""Adds xref targets to the top of files."""

import sys
import os

testing = False

DONT_TOUCH = (
        './index.txt',
        )


def target_name(fn):
    if fn.endswith('.txt'):
        fn = fn[:-4]
    return '_' + fn.lstrip('./').replace('/', '-')


def process_file(fn, lines):
    lines.insert(0, '\n')
    lines.insert(0, '.. %s:\n' % target_name(fn))
    try:
        f = open(fn, 'w')
    except IOError:
        print("Can't open %s for writing. Not touching it." % fn)
        return
    try:
        f.writelines(lines)
    except IOError:
        print("Can't write to %s. Not touching it." % fn)
    finally:
        f.close()


def has_target(fn):
    try:
        f = open(fn, 'r')
    except IOError:
        print("Can't open %s. Not touching it." % fn)
        return (True, None)
    readok = True
    try:
        lines = f.readlines()
    except IOError:
        print("Can't read %s. Not touching it." % fn)
        readok = False
    finally:
        f.close()
        if not readok:
            return (True, None)

    #print fn, len(lines)
    if len(lines) < 1:
        print("Not touching empty file %s." % fn)
        return (True, None)
    if lines[0].startswith('.. _'):
        return (True, None)
    return (False, lines)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    if len(argv) == 1:
        argv.extend('.')

    files = []
    for root in argv[1:]:
        for (dirpath, dirnames, filenames) in os.walk(root):
            files.extend([(dirpath, f) for f in filenames])
    files.sort()
    files = [os.path.join(p, fn) for p, fn in files if fn.endswith('.txt')]
    #print files

    for fn in files:
        if fn in DONT_TOUCH:
            print("Skipping blacklisted file %s." % fn)
            continue

        target_found, lines = has_target(fn)
        if not target_found:
            if testing:
                print '%s: %s' % (fn, lines[0]),
            else:
                print "Adding xref to %s" % fn
                process_file(fn, lines)
        else:
            print "Skipping %s: already has a xref" % fn

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = literals_to_xrefs
"""
Runs through a reST file looking for old-style literals, and helps replace them
with new-style references.
"""

import re
import sys
import shelve

refre = re.compile(r'``([^`\s]+?)``')

ROLES = (
    'attr',
    'class',
    "djadmin",
    'data',
    'exc',
    'file',
    'func',
    'lookup',
    'meth',
    'mod',
    "djadminopt",
    "ref",
    "setting",
    "term",
    "tfilter",
    "ttag",

    # special
    "skip",
)

ALWAYS_SKIP = [
    "NULL",
    "True",
    "False",
]


def fixliterals(fname):
    data = open(fname).read()

    last = 0
    new = []
    storage = shelve.open("/tmp/literals_to_xref.shelve")
    lastvalues = storage.get("lastvalues", {})

    for m in refre.finditer(data):

        new.append(data[last:m.start()])
        last = m.end()

        line_start = data.rfind("\n", 0, m.start())
        line_end = data.find("\n", m.end())
        prev_start = data.rfind("\n", 0, line_start)
        next_end = data.find("\n", line_end + 1)

        # Skip always-skip stuff
        if m.group(1) in ALWAYS_SKIP:
            new.append(m.group(0))
            continue

        # skip when the next line is a title
        next_line = data[m.end():next_end].strip()
        if next_line[0] in "!-/:-@[-`{-~" and \
                all(c == next_line[0] for c in next_line):
            new.append(m.group(0))
            continue

        sys.stdout.write("\n"+"-"*80+"\n")
        sys.stdout.write(data[prev_start+1:m.start()])
        sys.stdout.write(colorize(m.group(0), fg="red"))
        sys.stdout.write(data[m.end():next_end])
        sys.stdout.write("\n\n")

        replace_type = None
        while replace_type is None:
            replace_type = raw_input(
                colorize("Replace role: ", fg="yellow")).strip().lower()
            if replace_type and replace_type not in ROLES:
                replace_type = None

        if replace_type == "":
            new.append(m.group(0))
            continue

        if replace_type == "skip":
            new.append(m.group(0))
            ALWAYS_SKIP.append(m.group(1))
            continue

        default = lastvalues.get(m.group(1), m.group(1))
        if default.endswith("()") and \
                replace_type in ("class", "func", "meth"):
            default = default[:-2]
        replace_value = raw_input(
            colorize("Text <target> [", fg="yellow") + default + \
                    colorize("]: ", fg="yellow")).strip()
        if not replace_value:
            replace_value = default
        new.append(":%s:`%s`" % (replace_type, replace_value))
        lastvalues[m.group(1)] = replace_value

    new.append(data[last:])
    open(fname, "w").write("".join(new))

    storage["lastvalues"] = lastvalues
    storage.close()

#
# The following is taken from django.utils.termcolors and is copied here to
# avoid the dependancy.
#


def colorize(text='', opts=(), **kwargs):
    """
    Returns your text, enclosed in ANSI graphics codes.

    Depends on the keyword arguments 'fg' and 'bg', and the contents of
    the opts tuple/list.

    Returns the RESET code if no parameters are given.

    Valid colors:
        'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'

    Valid options:
        'bold'
        'underscore'
        'blink'
        'reverse'
        'conceal'
        'noreset' - string will not be auto-terminated with the RESET code

    Examples:
        colorize('hello', fg='red', bg='blue', opts=('blink',))
        colorize()
        colorize('goodbye', opts=('underscore',))
        print colorize('first line', fg='red', opts=('noreset',))
        print 'this should be red too'
        print colorize('and so should this')
        print 'this should not be red'
    """
    color_names = ('black', 'red', 'green', 'yellow',
                   'blue', 'magenta', 'cyan', 'white')
    foreground = dict([(color_names[x], '3%s' % x) for x in range(8)])
    background = dict([(color_names[x], '4%s' % x) for x in range(8)])

    RESET = '0'
    opt_dict = {'bold': '1',
                'underscore': '4',
                'blink': '5',
                'reverse': '7',
                'conceal': '8'}

    text = str(text)
    code_list = []
    if text == '' and len(opts) == 1 and opts[0] == 'reset':
        return '\x1b[%sm' % RESET
    for k, v in kwargs.iteritems():
        if k == 'fg':
            code_list.append(foreground[v])
        elif k == 'bg':
            code_list.append(background[v])
    for o in opts:
        if o in opt_dict:
            code_list.append(opt_dict[o])
    if 'noreset' not in opts:
        text = text + '\x1b[%sm' % RESET
    return ('\x1b[%sm' % ';'.join(code_list)) + text

if __name__ == '__main__':
    try:
        fixliterals(sys.argv[1])
    except (KeyboardInterrupt, SystemExit):
        print

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys
example_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(example_dir, '..'))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = middleware
import sys
from django.http import HttpResponseForbidden
from django.conf import settings

class RestrictMiddleware(object):
    """
    Reject all requests from IP addresses that are not on the whitelist.
    (We allow one exception for the sake of an unfuddle commit callback.)
    """
    IP_WHITELIST = []  				# override this with IP_WHITELIST in settings
    ACCESS_DENIED_MESSAGE = 'Access Denied'
    REQUIRED_CALLBACK_STRING = 'repository'   			# 'repository' is a good one for unfuddle
    CONFIRM_CALLBACK_STRINGS = ['my_company_domain.com',]	# override this in settings

    def process_request(self, request):
        """
        Check the request to see if access should be granted.
        """
        ipw = getattr(settings, 'IP_WHITELIST', self.IP_WHITELIST)
        if request.META['REMOTE_ADDR'] in ipw:
            # all requests from whitelisted IPs are allowed.
            return None

        # For now we just report some stuff.
        # Later we will add some explicit checks to
        #   restrict this to unfuddle commit callbacks..
        print request.method
        print "|%s|" % (request.path)
        for key, value in request.REQUEST.iteritems():
            print key, "::", value
        sys.stdout.flush()
        if request.method == "POST":
            if request.path == "/make":
                required_string = getattr(settings, 'REQUIRED_CALLBACK_STRING', self.REQUIRED_CALLBACK_STRING)
                callback_strings = getattr(settings, 'CONFIRM_CALLBACK_STRINGS', self.CONFIRM_CALLBACK_STRINGS)
                for key, value in request.REQUEST.iteritems():
                    if required_string in value:
                        for callback_string in callback_strings:
                            if callback_string in value:
                                return None

        # Unexpected request - deny!
        m = getattr(settings, 'RESTRICT_ACCESS_DENIED_MESSAGE', self.ACCESS_DENIED_MESSAGE)
        return HttpResponseForbidden(m)


########NEW FILE########
__FILENAME__ = settings
# Django settings for test_proj project.
import os
PROJECT_DIR = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('somebody', 'somebody@gmail.com'),
)

DJANGO_INTEGRATION_DIRECTORY = '/tmp/dci'

MANAGERS = ADMINS

# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'dci.db'
    }
}

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

MEDIA_ROOT = STATIC_ROOT = os.path.join(PROJECT_DIR, 'media')
MEDIA_URL = '/media/'

STATIC_ROOT = os.path.join(PROJECT_DIR, 'static')
STATIC_URL = '/static/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'kwjdckjwdcl0@ku!3&wi4kx4$yqnwctw*cf2kmi(0p=#3n!jl!0kp!o18wn^'

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware'
    #'testproj.middleware.RestrictMiddleware',
)

ROOT_URLCONF = 'testproj.urls'

DJANGO_INTEGRATION_MAILS = ['batisteb@opera.com']

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'djcelery',
    'djkombu',
    'djintegration',
)

# commit hook callback settings
# Your commit hook must send a POST request to /make
# Some value in the post REQUEST must include the REQUIRED_CALLBACK_STRING as well
#   as one of the CONFRIM_CALLBACK_STRINGS. (The IP address of the callback sender
#   does not need to be in the IP_WHITELIST.)
# To change this behaviour, reqork the middleware.py file.
# This stuff was tested with unfuddle.com.

# IP_WHITELIST = ['127.0.0.1']
# REQUIRED_CALLBACK_STRING = 'repository'
# CONFIRM_CALLBACK_STRINGS = ['mycompany.com']

# celery settings

import djcelery
djcelery.setup_loader()

BROKER_BACKEND  = 'djkombu.transport.DatabaseTransport'
BROKER_HOST     = 'localhost'
BROKER_PORT     = 5672
BROKER_USER     = 'someuser'
BROKER_PASSWORD = 'somepass'
BROKER_VHOST    = '/'


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^test_proj/', include('test_proj.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
    (r'^', include('djintegration.urls')),
)

########NEW FILE########
