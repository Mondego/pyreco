__FILENAME__ = admin
from django.contrib import admin

from django_vcs.models import CodeRepository

class CodeRepositoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {
        'slug': ('name',)
    }

admin.site.register(CodeRepository, CodeRepositoryAdmin)

########NEW FILE########
__FILENAME__ = diff
"""
Most of this code is taken right out of lodgit:
http://dev.pocoo.org/projects/lodgeit/
"""

import re

from django.utils.html import escape

def prepare_udiff(udiff):
    return DiffRenderer(udiff).prepare()

class DiffRenderer(object):
    _chunk_re = re.compile(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')

    def __init__(self, udiff):
        self.lines = [escape(line) for line in udiff.splitlines()]

    def prepare(self):
        return self._parse_udiff()

    def _parse_udiff(self):
        info = self._parse_info()

        in_header = True
        header = []
        lineiter = iter(self.lines)
        files = []
        try:
            line = lineiter.next()
            while True:
                if not line.startswith('--- '):
                    if in_header:
                        header.append(line)
                    line = lineiter.next()
                    continue

                if header and all(o.strip() for o in header):
                    files.append({'is_header': True, 'lines': header})
                    header = []

                in_header = []
                chunks = []
                old, new = self._extract_rev(line, lineiter.next())
                files.append({
                    'is_header': False,
                    'old_filename': old[0],
                    'old_revision': old[1],
                    'new_filename': new[0],
                    'new_revision': new[1],
                    'chunks': chunks,
                })

                line = lineiter.next()
                while line:
                    match = self._chunk_re.match(line)
                    if not match:
                        in_header = False
                        break

                    lines = []
                    chunks.append(lines)

                    old_line, old_end, new_line, new_end = [int(o or 1) for o in match.groups()]
                    old_line -= 1
                    new_line -= 1
                    old_end += old_line
                    new_end += new_line
                    line = lineiter.next()

                    while old_line < old_end or new_line < new_end:
                        if line:
                            command, line = line[0], line[1:]
                        else:
                            command = ' '
                        affects_old = affects_new = False

                        if command == '+':
                            affects_new = True
                            action = 'add'
                        elif command == '-':
                            affects_old = True
                            action = 'del'
                        else:
                            affects_old = affects_new = True
                            action = 'unmod'

                        old_line += affects_old
                        new_line += affects_new
                        lines.append({
                            'old_lineno': affects_old and old_line or u'',
                            'new_lineno': affects_new and new_line or u'',
                            'action': action,
                            'line': line,
                        })
                        line = lineiter.next()
        except StopIteration:
            pass

        for file in files:
            if file['is_header']:
                continue
            for chunk in file['chunks']:
                lineiter = iter(chunk)
                first = True
                try:
                    while True:
                        line = lineiter.next()
                        if line['action'] != 'unmod':
                            nextline = lineiter.next()
                            if nextline['action'] == 'unmod' or nextline['action'] == line['action']:
                                continue
                            self._highlight_line(line, nextline)
                except StopIteration:
                    pass

        return files, info

    def _parse_info(self):
        nlines = len(self.lines)
        if not nlines:
            return
        firstline = self.lines[0]
        info = []

        # todo copy the HG stuff

        return info

    def _extract_rev(self, line1, line2):
        def _extract(line):
            parts = line.split(None, 1)
            return parts[0], (len(parts) == 2 and parts[1] or None)

        try:
            if line1.startswith('--- ') and line2.startswith('+++ '):
                return _extract(line1[4:]), _extract(line2[4:])
        except (ValueError, IndexError):
            pass
        return (None, None), (None, None)

    def _highlight_line(self, line, next):
        start = 0
        limit = min(len(line['line']), len(next['line']))
        while start < limit and line['line'][start] == next['line'][start]:
            start += 1
        end = -1
        limit -= start
        while -end <= limit and line['line'][end] == next['line'][end]:
            end -= 1
        end += 1
        if start or end:
            def do(l):
                last = end + len(l['line'])
                if l['action'] == 'add':
                    tag = 'ins'
                else:
                    tag = 'del'
                l['line'] = u'%s<%s>%s</%s>%s' % (
                    l['line'][:start],
                    tag,
                    l['line'][start:last],
                    tag,
                    l['line'][last:],
                )
            do(line)
            do(next)

########NEW FILE########
__FILENAME__ = models
from itertools import count

from django.db import models

from pyvcs.backends import AVAILABLE_BACKENDS, get_backend
from pyvcs.exceptions import CommitDoesNotExist, FileDoesNotExist, FolderDoesNotExist


REPOSITORY_TYPES = zip(count(), AVAILABLE_BACKENDS.keys())

class CodeRepository(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField()

    repository_type = models.IntegerField(choices=REPOSITORY_TYPES)

    location = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Code Repositories"

    def __unicode__(self):
        return "%s: %s" % (self.get_repository_type_display(), self.name)

    @models.permalink
    def get_absolute_url(self):
        return ('recent_commits', (), {'slug': self.slug})

    @property
    def repo(self):
        if hasattr(self, '_repo'):
            return self._repo
        self._repo = get_backend(self.get_repository_type_display()).Repository(self.location)
        return self._repo

    def get_commit(self, commit_id):
        try:
            return self.repo.get_commit_by_id(str(commit_id))
        except CommitDoesNotExist:
            return None

    def get_recent_commits(self, since=None):
        return self.repo.get_recent_commits(since=since)

    def get_folder_contents(self, path, rev=None):
        try:
            if rev is not None:
                rev = str(rev)
            return self.repo.list_directory(path, rev)
        except FolderDoesNotExist:
            return None

    def get_file_contents(self, path, rev=None):
        try:
            if rev is not None:
                rev = str(rev)
            return self.repo.file_contents(path, rev)
        except FileDoesNotExist:
            return None

########NEW FILE########
__FILENAME__ = highlight
from django import template
from django.utils.safestring import mark_safe

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import guess_lexer_for_filename, TextLexer
from pygments.util import ClassNotFound

register = template.Library()

@register.filter('highlight')
def highlight_filter(text, filename):
    try:
        lexer = guess_lexer_for_filename(filename, text)
    except ClassNotFound:
        lexer = TextLexer()

    return mark_safe(highlight(
        text,
        lexer,
        HtmlFormatter(linenos="table", lineanchors="line")
    ))


@register.simple_tag
def highlight_css():
    return HtmlFormatter(linenos="table", lineanchors="line").get_style_defs()

########NEW FILE########
__FILENAME__ = udiff
from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from django_vcs.diff import prepare_udiff

register = template.Library()

@register.filter
def render_diff(text):
    diffs, info = prepare_udiff(text)
    return render_to_string('django_vcs/udiff.html', {'diffs': diffs, 'info': info})

@register.inclusion_tag('django_vcs/diff_css.html')
def diff_css():
    return {}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

urlpatterns = patterns('django_vcs.views',
    url('^$', 'repo_list', name='repo_list'),
    url('^(?P<slug>[\w-]+)/$', 'recent_commits', name='recent_commits'),
    url('^(?P<slug>[\w-]+)/browser/(?P<path>.*)$', 'code_browser', name='code_browser'),
    url('^(?P<slug>[\w-]+)/commit/(?P<commit_id>.*)/$', 'commit_detail', name='commit_detail'),
)

########NEW FILE########
__FILENAME__ = views
import os

from django.http import Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from django_vcs.models import CodeRepository

def repo_list(request):
    repos = CodeRepository.objects.all()
    return render_to_response('django_vcs/repo_list.html', {'repos': repos}, context_instance=RequestContext(request))

def recent_commits(request, slug):
    repo = get_object_or_404(CodeRepository, slug=slug)
    commits = repo.get_recent_commits()
    return render_to_response([
        'django_vcs/%s/recent_commits.html' % repo.name,
        'django_vcs/recent_commits.html',
    ], {'repo': repo, 'commits': commits}, context_instance=RequestContext(request))

def code_browser(request, slug, path):
    repo = get_object_or_404(CodeRepository, slug=slug)
    rev = request.GET.get('rev') or None
    context = {'repo': repo, 'path': path}
    file_contents = repo.get_file_contents(path, rev)
    if file_contents is None:
        folder_contents = repo.get_folder_contents(path, rev)
        if folder_contents is None:
            raise Http404
        context['files'], context['folders'] = folder_contents
        context['files'] = [(os.path.join(path, o), o) for o in context['files']]
        context['folders'] = [(os.path.join(path, o), o) for o in context['folders']]
        return render_to_response([
            'django_vcs/%s/folder_contents.html' % repo.name,
            'django_vcs/folder_contents.html',
        ], context, context_instance=RequestContext(request))
    context['file'] = file_contents
    return render_to_response([
        'django_vcs/%s/file_contents.html' % repo.name,
        'django_vcs/file_contents.html',
    ], context, context_instance=RequestContext(request))

def commit_detail(request, slug, commit_id):
    repo = get_object_or_404(CodeRepository, slug=slug)
    commit = repo.get_commit(commit_id)
    if commit is None:
        raise Http404
    return render_to_response([
        'django_vcs/%s/commit_detail.html' % repo.name,
        'django_vcs/commit_detail.html',
    ], {'repo': repo, 'commit': commit}, context_instance=RequestContext(request))

########NEW FILE########
