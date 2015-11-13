__FILENAME__ = admin
# -*- coding: utf-8 -*-

from codespeed.models import (Project, Revision, Executable, Benchmark, Branch,
                              Result, Environment, Report)

from django.contrib import admin


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'repo_type', 'repo_path', 'track')

admin.site.register(Project, ProjectAdmin)


class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'project')

admin.site.register(Branch, BranchAdmin)


class RevisionAdmin(admin.ModelAdmin):
    list_display = ('commitid', 'branch', 'tag', 'date')
    list_filter = ('branch', 'tag', 'date')
    search_fields = ('commitid', 'tag')

admin.site.register(Revision, RevisionAdmin)


class ExecutableAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'id', 'project')
    search_fields = ('name', 'description', 'project')

admin.site.register(Executable, ExecutableAdmin)


class BenchmarkAdmin(admin.ModelAdmin):
    list_display = ('name', 'benchmark_type', 'description', 'units_title',
                    'units', 'lessisbetter', 'default_on_comparison')
    ordering = ['name']
    search_fields = ('name', 'description')

admin.site.register(Benchmark, BenchmarkAdmin)


class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'cpu', 'memory', 'os', 'kernel')
    search_fields = ('name', 'cpu', 'memory', 'os', 'kernel')

admin.site.register(Environment, EnvironmentAdmin)


class ResultAdmin(admin.ModelAdmin):
    list_display = ('revision', 'benchmark', 'executable', 'environment',
                    'value', 'date', 'environment')
    list_filter = ('date', 'environment', 'executable', 'benchmark')

admin.site.register(Result, ResultAdmin)


class ReportAdmin(admin.ModelAdmin):
    list_display = ('revision', 'summary', 'colorcode')
    ordering = ['-revision']

admin.site.register(Report, ReportAdmin)

########NEW FILE########
__FILENAME__ = feeds
from django.contrib.syndication.views import Feed
from codespeed.models import Report
from django.conf import settings


class LatestEntries(Feed):
    title = settings.WEBSITE_NAME
    link = "/changes/"
    description = "Last benchmark runs"

    def items(self):
        return Report.objects.filter(
            revision__branch__name=settings.DEF_BRANCH
        ).order_by('-revision__date')[:10]

########NEW FILE########
__FILENAME__ = git
from subprocess import Popen, PIPE
import datetime
import os
import logging

from django.conf import settings


logger = logging.getLogger(__name__)


def updaterepo(project, update=True):
    if os.path.exists(project.working_copy):
        if not update:
            return

        p = Popen(['git', 'pull'], stdout=PIPE, stderr=PIPE,
                    cwd=project.working_copy)

        stdout, stderr = p.communicate()
        if p.returncode != 0:
            raise RuntimeError("git pull returned %s: %s" % (p.returncode,
                                                                stderr))
        else:
            return [{'error': False}]
    else:
        cmd = ['git', 'clone', project.repo_path, project.repo_name]
        p = Popen(cmd, stdout=PIPE, stderr=PIPE,
                    cwd=settings.REPOSITORY_BASE_PATH)
        logger.debug('Cloning Git repo {0} for project {1}'.format(
            project.repo_path, project))
        stdout, stderr = p.communicate()

        if p.returncode != 0:
            raise RuntimeError("%s returned %s: %s" % (
                " ".join(cmd), p.returncode, stderr))
        else:
            return [{'error': False}]


def getlogs(endrev, startrev):
    updaterepo(endrev.branch.project, update=False)

    cmd = ["git", "log",
            # NULL separated values delimited by 0x1e record separators
            # See PRETTY FORMATS in git-log(1):
            '--format=format:%h%x00%H%x00%at%x00%an%x00%ae%x00%s%x00%b%x1e']

    if endrev.commitid != startrev.commitid:
        cmd.append("%s...%s" % (startrev.commitid, endrev.commitid))
    else:
        cmd.append("-1")  # Only return one commit
        cmd.append(endrev.commitid)

    working_copy = endrev.branch.project.working_copy
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, cwd=working_copy)

    stdout, stderr = p.communicate()

    if p.returncode != 0:
        raise RuntimeError("%s returned %s: %s" % (
                            " ".join(cmd), p.returncode, stderr))
    logs = []
    for log in filter(None, stdout.split("\x1e")):
        (short_commit_id, commit_id, date_t, author_name, author_email,
            subject, body) = log.split("\x00", 7)

        date = datetime.datetime.fromtimestamp(
                                    int(date_t)).strftime("%Y-%m-%d %H:%M:%S")

        logs.append({'date': date, 'message': subject, 'commitid': commit_id,
                     'author': author_name, 'author_email': author_email,
                     'body': body, 'short_commit_id': short_commit_id})

    return logs

########NEW FILE########
__FILENAME__ = github
# encoding: utf-8
"""
Specialized Git backend which uses Github.com for all of the heavy work

Among other things, this means that the codespeed server doesn't need to have
git installed, the ability to write files, etc.
"""
import logging
import urllib
import re
import json

import isodate
from django.core.cache import cache

logger = logging.getLogger(__name__)

GITHUB_URL_RE = re.compile(
    r'^(?P<proto>\w+)://github.com/(?P<username>[^/]+)/(?P<project>[^/]+)([.]git)?$')

# We currently use a simple linear search of on a single parent to retrieve
# the history. This is often good enough, but might miss the actual starting
# point. Thus, we need to terminate the search after a resonable number of
# revisions.
GITHUB_REVISION_LIMIT = 10


def updaterepo(project, update=True):
    return


def retrieve_revision(commit_id, username, project, revision=None):
    commit_url = 'https://api.github.com/repos/%s/%s/git/commits/%s' % (
        username, project, commit_id)

    commit_json = cache.get(commit_url)

    if commit_json is None:
        try:
            commit_json = json.load(urllib.urlopen(commit_url))
        except IOError, e:
            logger.exception("Unable to load %s: %s",
                             commit_url, e, exc_info=True)
            raise e

        if commit_json["message"] in ("Not Found", "Server Error",):
            # We'll still cache these for a brief period of time to avoid making too many requests:
            cache.set(commit_url, commit_json, 300)
        else:
            # We'll cache successes for a very long period of time since
            # SCM diffs shouldn't change:
            cache.set(commit_url, commit_json, 86400 * 30)

    if commit_json["message"] in ("Not Found", "Server Error",):
         raise RuntimeError("Unable to load %s: %s" % (commit_url, commit_json["message"]))

    date = isodate.parse_datetime(commit_json['committer']['date'])

    if revision:
        # Overwrite any existing data we might have for this revision since
        # we never want our records to be out of sync with the actual VCS:

        # We need to convert the timezone-aware date to a naive (i.e.
        # timezone-less) date in UTC to avoid killing MySQL:
        revision.date = date.astimezone(isodate.tzinfo.Utc()).replace(tzinfo=None)
        revision.author = commit_json['author']['name']
        revision.message = commit_json['message']
        revision.full_clean()
        revision.save()

    return {'date':         date,
            'message':      commit_json['message'],
            'body':         "",   # TODO: pretty-print diffs
            'author':       commit_json['author']['name'],
            'author_email': commit_json['author']['email'],
            'commitid':     commit_json['sha'],
            'short_commit_id': commit_json['sha'][0:7],
            'parents':      commit_json['parents']}


def getlogs(endrev, startrev):
    if endrev != startrev:
        revisions = endrev.branch.revisions.filter(
                        date__lte=endrev.date, date__gte=startrev.date)
    else:
        revisions = [i for i in (startrev, endrev) if i.commitid]

    if endrev.branch.project.repo_path[-1] == '/':
        endrev.branch.project.repo_path = endrev.branch.project.repo_path[:-1]

    m = GITHUB_URL_RE.match(endrev.branch.project.repo_path)

    if not m:
        raise ValueError(
            "Unable to parse Github URL %s" % endrev.branch.project.repo_path)

    username = m.group("username")
    project = m.group("project")

    logs = []
    last_rev_data = None
    revision_count = 0
    ancestor_found = False
    #TODO: get all revisions between endrev and startrev,
    # not only those present in the Codespeed DB

    for revision in revisions:
        last_rev_data = retrieve_revision(revision.commitid, username, project, revision)
        logs.append(last_rev_data)
        revision_count += 1
        ancestor_found = (startrev.commitid in [rev['sha'] for rev in last_rev_data['parents']])

    # Simple approach to find the startrev, stop after found or after
    # #GITHUB_REVISION_LIMIT revisions are fetched
    while (revision_count < GITHUB_REVISION_LIMIT
            and not ancestor_found
            and len(last_rev_data['parents']) > 0):
        last_rev_data = retrieve_revision(last_rev_data['parents'][0]['sha'], username, project)
        logs.append(last_rev_data)
        revision_count += 1
        ancestor_found = (startrev.commitid in [rev['sha'] for rev in last_rev_data['parents']])

    return sorted(logs, key=lambda i: i['date'], reverse=True)

########NEW FILE########
__FILENAME__ = mercurial
import os
import datetime
from subprocess import Popen, PIPE
import logging

from django.conf import settings


logger = logging.getLogger(__name__)


def updaterepo(project, update=True):
    if os.path.exists(project.working_copy):
        if not update:
            return

        p = Popen(['hg', 'pull', '-u'], stdout=PIPE, stderr=PIPE,
                    cwd=project.working_copy)
        stdout, stderr = p.communicate()

        if p.returncode != 0 or stderr:
            raise RuntimeError("hg pull returned %s: %s" % (p.returncode,
                                                                stderr))
        else:
            return [{'error': False}]
    else:
        # Clone repo
        cmd = ['hg', 'clone', project.repo_path, project.repo_name]

        p = Popen(cmd, stdout=PIPE, stderr=PIPE,
                    cwd=settings.REPOSITORY_BASE_PATH)
        logger.debug('Cloning Mercurial repo {0} for project {1}'.format(
            project.repo_path, project))
        stdout, stderr = p.communicate()

        if p.returncode != 0:
            raise RuntimeError("%s returned %s: %s" % (" ".join(cmd),
                                                        p.returncode,
                                                        stderr))
        else:
            return [{'error': False}]


def getlogs(endrev, startrev):
    updaterepo(endrev.branch.project, update=False)

    cmd = ["hg", "log",
            "-r", "%s:%s" % (endrev.commitid, startrev.commitid),
            "-b", "default",
            "--template", "{rev}:{node|short}\n{node}\n{author|user}\n{author|email}\n{date}\n{desc}\n=newlog=\n"]

    working_copy = endrev.branch.project.working_copy
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, cwd=working_copy)
    stdout, stderr = p.communicate()

    if p.returncode != 0:
        raise RuntimeError(str(stderr))
    else:
        stdout = stdout.rstrip('\n')  # Remove last newline
        logs = []
        for log in stdout.split("=newlog=\n"):
            elements = []
            elements = log.split('\n')[:-1]
            if len(elements) < 6:
                # "Malformed" log
                logs.append(
                    {'date': '-', 'message': 'error parsing log', 'commitid': '-'})
            else:
                short_commit_id = elements.pop(0)
                commit_id = elements.pop(0)
                author_name = elements.pop(0)
                author_email = elements.pop(0)
                date = elements.pop(0)
                # All other newlines should belong to the description text. Join.
                message = '\n'.join(elements)

                # Parse date
                date = date.split('-')[0]
                date = datetime.datetime.fromtimestamp(float(date)).strftime("%Y-%m-%d %H:%M:%S")

                # Add changeset info
                logs.append({
                    'date': date, 'author': author_name,
                    'author_email': author_email, 'message': message,
                    'short_commit_id': short_commit_id, 'commitid': commit_id})
    # Remove last log here because mercurial saves the short hast as commitid now
    if len(logs) > 1 and logs[-1].get('short_commit_id') == startrev.commitid:
        logs.pop()
    return logs

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'Project'
        db.create_table('codespeed_project', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=30)),
            ('repo_type', self.gf('django.db.models.fields.CharField')(default='N', max_length=1)),
            ('repo_path', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('repo_user', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('repo_pass', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('track', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('codespeed', ['Project'])

        # Adding model 'Revision'
        db.create_table('codespeed_revision', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('commitid', self.gf('django.db.models.fields.CharField')(max_length=42)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(related_name='revisions', to=orm['codespeed.Project'])),
            ('tag', self.gf('django.db.models.fields.CharField')(max_length=20, blank=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('message', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('author', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
        ))
        db.send_create_signal('codespeed', ['Revision'])

        # Adding unique constraint on 'Revision', fields ['commitid', 'project']
        db.create_unique('codespeed_revision', ['commitid', 'project_id'])

        # Adding model 'Executable'
        db.create_table('codespeed_executable', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=30)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(related_name='executables', to=orm['codespeed.Project'])),
        ))
        db.send_create_signal('codespeed', ['Executable'])

        # Adding model 'Benchmark'
        db.create_table('codespeed_benchmark', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=30)),
            ('benchmark_type', self.gf('django.db.models.fields.CharField')(default='C', max_length=1)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('units_title', self.gf('django.db.models.fields.CharField')(default='Time', max_length=30)),
            ('units', self.gf('django.db.models.fields.CharField')(default='seconds', max_length=20)),
            ('lessisbetter', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('codespeed', ['Benchmark'])

        # Adding model 'Environment'
        db.create_table('codespeed_environment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=30)),
            ('cpu', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('memory', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('os', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('kernel', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
        ))
        db.send_create_signal('codespeed', ['Environment'])

        # Adding model 'Result'
        db.create_table('codespeed_result', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('value', self.gf('django.db.models.fields.FloatField')()),
            ('std_dev', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('val_min', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('val_max', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('revision', self.gf('django.db.models.fields.related.ForeignKey')(related_name='results', to=orm['codespeed.Revision'])),
            ('executable', self.gf('django.db.models.fields.related.ForeignKey')(related_name='results', to=orm['codespeed.Executable'])),
            ('benchmark', self.gf('django.db.models.fields.related.ForeignKey')(related_name='results', to=orm['codespeed.Benchmark'])),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='results', to=orm['codespeed.Environment'])),
        ))
        db.send_create_signal('codespeed', ['Result'])

        # Adding unique constraint on 'Result', fields ['revision', 'executable', 'benchmark', 'environment']
        db.create_unique('codespeed_result', ['revision_id', 'executable_id', 'benchmark_id', 'environment_id'])

        # Adding model 'Report'
        db.create_table('codespeed_report', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('revision', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reports', to=orm['codespeed.Revision'])),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reports', to=orm['codespeed.Environment'])),
            ('executable', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reports', to=orm['codespeed.Executable'])),
            ('summary', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('colorcode', self.gf('django.db.models.fields.CharField')(default='none', max_length=10)),
            ('_tablecache', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('codespeed', ['Report'])

        # Adding unique constraint on 'Report', fields ['revision', 'executable', 'environment']
        db.create_unique('codespeed_report', ['revision_id', 'executable_id', 'environment_id'])


    def backwards(self, orm):

        # Removing unique constraint on 'Report', fields ['revision', 'executable', 'environment']
        db.delete_unique('codespeed_report', ['revision_id', 'executable_id', 'environment_id'])

        # Removing unique constraint on 'Result', fields ['revision', 'executable', 'benchmark', 'environment']
        db.delete_unique('codespeed_result', ['revision_id', 'executable_id', 'benchmark_id', 'environment_id'])

        # Removing unique constraint on 'Revision', fields ['commitid', 'project']
        db.delete_unique('codespeed_revision', ['commitid', 'project_id'])

        # Deleting model 'Project'
        db.delete_table('codespeed_project')

        # Deleting model 'Revision'
        db.delete_table('codespeed_revision')

        # Deleting model 'Executable'
        db.delete_table('codespeed_executable')

        # Deleting model 'Benchmark'
        db.delete_table('codespeed_benchmark')

        # Deleting model 'Environment'
        db.delete_table('codespeed_environment')

        # Deleting model 'Result'
        db.delete_table('codespeed_result')

        # Deleting model 'Report'
        db.delete_table('codespeed_report')


    models = {
        'codespeed.benchmark': {
            'Meta': {'object_name': 'Benchmark'},
            'benchmark_type': ('django.db.models.fields.CharField', [], {'default': "'C'", 'max_length': '1'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lessisbetter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'units': ('django.db.models.fields.CharField', [], {'default': "'seconds'", 'max_length': '20'}),
            'units_title': ('django.db.models.fields.CharField', [], {'default': "'Time'", 'max_length': '30'})
        },
        'codespeed.environment': {
            'Meta': {'object_name': 'Environment'},
            'cpu': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'memory': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'os': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        },
        'codespeed.executable': {
            'Meta': {'object_name': 'Executable'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executables'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'repo_pass': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'repo_path': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_type': ('django.db.models.fields.CharField', [], {'default': "'N'", 'max_length': '1'}),
            'repo_user': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'track': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'codespeed.report': {
            'Meta': {'unique_together': "(('revision', 'executable', 'environment'),)", 'object_name': 'Report'},
            '_tablecache': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'colorcode': ('django.db.models.fields.CharField', [], {'default': "'none'", 'max_length': '10'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Revision']"}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        },
        'codespeed.result': {
            'Meta': {'unique_together': "(('revision', 'executable', 'benchmark', 'environment'),)", 'object_name': 'Result'},
            'benchmark': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Benchmark']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Revision']"}),
            'std_dev': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_max': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_min': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'codespeed.revision': {
            'Meta': {'unique_together': "(('commitid', 'project'),)", 'object_name': 'Revision'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'commitid': ('django.db.models.fields.CharField', [], {'max_length': '42'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'revisions'", 'to': "orm['codespeed.Project']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        }
    }

    complete_apps = ['codespeed']

########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_report_summary
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Report.summary'
        db.alter_column('codespeed_report', 'summary', self.gf('django.db.models.fields.CharField')(max_length=64))


    def backwards(self, orm):

        # Changing field 'Report.summary'
        db.alter_column('codespeed_report', 'summary', self.gf('django.db.models.fields.CharField')(max_length=30))


    models = {
        'codespeed.benchmark': {
            'Meta': {'object_name': 'Benchmark'},
            'benchmark_type': ('django.db.models.fields.CharField', [], {'default': "'C'", 'max_length': '1'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lessisbetter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'units': ('django.db.models.fields.CharField', [], {'default': "'seconds'", 'max_length': '20'}),
            'units_title': ('django.db.models.fields.CharField', [], {'default': "'Time'", 'max_length': '30'})
        },
        'codespeed.environment': {
            'Meta': {'object_name': 'Environment'},
            'cpu': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'memory': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'os': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        },
        'codespeed.executable': {
            'Meta': {'object_name': 'Executable'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executables'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'repo_pass': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'repo_path': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_type': ('django.db.models.fields.CharField', [], {'default': "'N'", 'max_length': '1'}),
            'repo_user': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'track': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'codespeed.report': {
            'Meta': {'unique_together': "(('revision', 'executable', 'environment'),)", 'object_name': 'Report'},
            '_tablecache': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'colorcode': ('django.db.models.fields.CharField', [], {'default': "'none'", 'max_length': '10'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Revision']"}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'codespeed.result': {
            'Meta': {'unique_together': "(('revision', 'executable', 'benchmark', 'environment'),)", 'object_name': 'Result'},
            'benchmark': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Benchmark']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Revision']"}),
            'std_dev': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_max': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_min': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'codespeed.revision': {
            'Meta': {'unique_together': "(('commitid', 'project'),)", 'object_name': 'Revision'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'commitid': ('django.db.models.fields.CharField', [], {'max_length': '42'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'revisions'", 'to': "orm['codespeed.Project']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        }
    }

    complete_apps = ['codespeed']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_revision_branch
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Revision.branch'
        db.add_column('codespeed_revision', 'branch', self.gf('django.db.models.fields.CharField')(default='', max_length=15, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Revision.branch'
        db.delete_column('codespeed_revision', 'branch')


    models = {
        'codespeed.benchmark': {
            'Meta': {'object_name': 'Benchmark'},
            'benchmark_type': ('django.db.models.fields.CharField', [], {'default': "'C'", 'max_length': '1'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lessisbetter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'units': ('django.db.models.fields.CharField', [], {'default': "'seconds'", 'max_length': '20'}),
            'units_title': ('django.db.models.fields.CharField', [], {'default': "'Time'", 'max_length': '30'})
        },
        'codespeed.environment': {
            'Meta': {'object_name': 'Environment'},
            'cpu': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'memory': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'os': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        },
        'codespeed.executable': {
            'Meta': {'object_name': 'Executable'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executables'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'repo_pass': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'repo_path': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_type': ('django.db.models.fields.CharField', [], {'default': "'N'", 'max_length': '1'}),
            'repo_user': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'track': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'codespeed.report': {
            'Meta': {'unique_together': "(('revision', 'executable', 'environment'),)", 'object_name': 'Report'},
            '_tablecache': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'colorcode': ('django.db.models.fields.CharField', [], {'default': "'none'", 'max_length': '10'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Revision']"}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'codespeed.result': {
            'Meta': {'unique_together': "(('revision', 'executable', 'benchmark', 'environment'),)", 'object_name': 'Result'},
            'benchmark': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Benchmark']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Revision']"}),
            'std_dev': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_max': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_min': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'codespeed.revision': {
            'Meta': {'unique_together': "(('commitid', 'project'),)", 'object_name': 'Revision'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'branch': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'commitid': ('django.db.models.fields.CharField', [], {'max_length': '42'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'revisions'", 'to': "orm['codespeed.Project']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        }
    }

    complete_apps = ['codespeed']

########NEW FILE########
__FILENAME__ = 0004_auto__add_branch
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Branch'
        db.create_table('codespeed_branch', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(related_name='branches', to=orm['codespeed.Project'])),
        ))
        db.send_create_signal('codespeed', ['Branch'])


    def backwards(self, orm):
        
        # Deleting model 'Branch'
        db.delete_table('codespeed_branch')


    models = {
        'codespeed.benchmark': {
            'Meta': {'object_name': 'Benchmark'},
            'benchmark_type': ('django.db.models.fields.CharField', [], {'default': "'C'", 'max_length': '1'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lessisbetter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'units': ('django.db.models.fields.CharField', [], {'default': "'seconds'", 'max_length': '20'}),
            'units_title': ('django.db.models.fields.CharField', [], {'default': "'Time'", 'max_length': '30'})
        },
        'codespeed.branch': {
            'Meta': {'object_name': 'Branch'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'branches'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.environment': {
            'Meta': {'object_name': 'Environment'},
            'cpu': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'memory': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'os': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        },
        'codespeed.executable': {
            'Meta': {'object_name': 'Executable'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executables'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'repo_pass': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'repo_path': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_type': ('django.db.models.fields.CharField', [], {'default': "'N'", 'max_length': '1'}),
            'repo_user': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'track': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'codespeed.report': {
            'Meta': {'unique_together': "(('revision', 'executable', 'environment'),)", 'object_name': 'Report'},
            '_tablecache': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'colorcode': ('django.db.models.fields.CharField', [], {'default': "'none'", 'max_length': '10'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Revision']"}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'codespeed.result': {
            'Meta': {'unique_together': "(('revision', 'executable', 'benchmark', 'environment'),)", 'object_name': 'Result'},
            'benchmark': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Benchmark']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Revision']"}),
            'std_dev': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_max': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_min': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'codespeed.revision': {
            'Meta': {'unique_together': "(('commitid', 'project'),)", 'object_name': 'Revision'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'branch': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'commitid': ('django.db.models.fields.CharField', [], {'max_length': '42'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'revisions'", 'to': "orm['codespeed.Project']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        }
    }

    complete_apps = ['codespeed']

########NEW FILE########
__FILENAME__ = 0005_auto__del_unique_revision_commitid_project__add_unique_revision_commit
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'Revision', fields ['commitid', 'project']
        db.delete_unique('codespeed_revision', ['commitid', 'project_id'])

        # Adding unique constraint on 'Revision', fields ['commitid', 'project', 'branch']
        db.create_unique('codespeed_revision', ['commitid', 'project_id', 'branch'])

        # Adding unique constraint on 'Branch', fields ['project', 'name']
        db.create_unique('codespeed_branch', ['project_id', 'name'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Branch', fields ['project', 'name']
        db.delete_unique('codespeed_branch', ['project_id', 'name'])

        # Removing unique constraint on 'Revision', fields ['commitid', 'project', 'branch']
        db.delete_unique('codespeed_revision', ['commitid', 'project_id', 'branch'])

        # Adding unique constraint on 'Revision', fields ['commitid', 'project']
        db.create_unique('codespeed_revision', ['commitid', 'project_id'])


    models = {
        'codespeed.benchmark': {
            'Meta': {'object_name': 'Benchmark'},
            'benchmark_type': ('django.db.models.fields.CharField', [], {'default': "'C'", 'max_length': '1'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lessisbetter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'units': ('django.db.models.fields.CharField', [], {'default': "'seconds'", 'max_length': '20'}),
            'units_title': ('django.db.models.fields.CharField', [], {'default': "'Time'", 'max_length': '30'})
        },
        'codespeed.branch': {
            'Meta': {'unique_together': "(('name', 'project'),)", 'object_name': 'Branch'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'branches'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.environment': {
            'Meta': {'object_name': 'Environment'},
            'cpu': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'memory': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'os': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        },
        'codespeed.executable': {
            'Meta': {'object_name': 'Executable'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executables'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'repo_pass': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'repo_path': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_type': ('django.db.models.fields.CharField', [], {'default': "'N'", 'max_length': '1'}),
            'repo_user': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'track': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'codespeed.report': {
            'Meta': {'unique_together': "(('revision', 'executable', 'environment'),)", 'object_name': 'Report'},
            '_tablecache': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'colorcode': ('django.db.models.fields.CharField', [], {'default': "'none'", 'max_length': '10'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Revision']"}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'codespeed.result': {
            'Meta': {'unique_together': "(('revision', 'executable', 'benchmark', 'environment'),)", 'object_name': 'Result'},
            'benchmark': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Benchmark']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Revision']"}),
            'std_dev': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_max': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_min': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'codespeed.revision': {
            'Meta': {'unique_together': "(('commitid', 'project', 'branch'),)", 'object_name': 'Revision'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'branch': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'commitid': ('django.db.models.fields.CharField', [], {'max_length': '42'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'revisions'", 'to': "orm['codespeed.Project']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        }
    }

    complete_apps = ['codespeed']

########NEW FILE########
__FILENAME__ = 0006_auto__chg_field_revision_branch
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding field 'Revision.branch_id'
        db.add_column('codespeed_revision', 'branch', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['codespeed.Branch']))
        # Removing unique constraint on 'Revision', fields ['commitid', 'project', branch']
        db.delete_unique('codespeed_revision', ['commitid', 'project_id', 'branch'])
        # Delete field 'Revision.branch'
        db.delete_column('codespeed_revision', 'branch')
        # Adding unique constraint on 'Revision', fields ['commitid', 'project_id', 'branch_id']
        db.create_unique('codespeed_revision', ['commitid', 'project_id', 'branch_id'])


        # Adding index on 'Revision', fields ['branch']
        # NOTE: commented out because it can cause an
        # "index codespeed_revision_d56253ba already exists"
        # db.create_index('codespeed_revision', ['branch_id'])


    def backwards(self, orm):

        # Removing index on 'Revision', fields ['branch']
        db.delete_index('codespeed_revision', ['branch_id'])

        # Renaming column for 'Revision.branch' to match new field type.
        db.rename_column('codespeed_revision', 'branch_id', 'branch')
        # Changing field 'Revision.branch'
        db.alter_column('codespeed_revision', 'branch', self.gf('django.db.models.fields.CharField')(max_length=15))


    models = {
        'codespeed.benchmark': {
            'Meta': {'object_name': 'Benchmark'},
            'benchmark_type': ('django.db.models.fields.CharField', [], {'default': "'C'", 'max_length': '1'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lessisbetter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'units': ('django.db.models.fields.CharField', [], {'default': "'seconds'", 'max_length': '20'}),
            'units_title': ('django.db.models.fields.CharField', [], {'default': "'Time'", 'max_length': '30'})
        },
        'codespeed.branch': {
            'Meta': {'unique_together': "(('name', 'project'),)", 'object_name': 'Branch'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'branches'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.environment': {
            'Meta': {'object_name': 'Environment'},
            'cpu': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'memory': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'os': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        },
        'codespeed.executable': {
            'Meta': {'object_name': 'Executable'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executables'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'repo_pass': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'repo_path': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_type': ('django.db.models.fields.CharField', [], {'default': "'N'", 'max_length': '1'}),
            'repo_user': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'track': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'codespeed.report': {
            'Meta': {'unique_together': "(('revision', 'executable', 'environment'),)", 'object_name': 'Report'},
            '_tablecache': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'colorcode': ('django.db.models.fields.CharField', [], {'default': "'none'", 'max_length': '10'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Revision']"}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'codespeed.result': {
            'Meta': {'unique_together': "(('revision', 'executable', 'benchmark', 'environment'),)", 'object_name': 'Result'},
            'benchmark': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Benchmark']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Revision']"}),
            'std_dev': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_max': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_min': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'codespeed.revision': {
            'Meta': {'unique_together': "(('commitid', 'project', 'branch'),)", 'object_name': 'Revision'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'branch': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'branch'", 'to': "orm['codespeed.Branch']"}),
            'commitid': ('django.db.models.fields.CharField', [], {'max_length': '42'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'revisions'", 'to': "orm['codespeed.Project']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        }
    }

    complete_apps = ['codespeed']

########NEW FILE########
__FILENAME__ = 0007_auto__del_unique_revision_commitid_project_branch__add_unique_revision
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'Revision', fields ['commitid', 'project', 'branch']
        db.delete_unique('codespeed_revision', ['commitid', 'project_id', 'branch_id'])

        # Adding unique constraint on 'Revision', fields ['commitid', 'branch']
        db.create_unique('codespeed_revision', ['commitid', 'branch_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Revision', fields ['commitid', 'branch']
        db.delete_unique('codespeed_revision', ['commitid', 'branch_id'])

        # Adding unique constraint on 'Revision', fields ['commitid', 'project', 'branch']
        db.create_unique('codespeed_revision', ['commitid', 'project_id', 'branch_id'])


    models = {
        'codespeed.benchmark': {
            'Meta': {'object_name': 'Benchmark'},
            'benchmark_type': ('django.db.models.fields.CharField', [], {'default': "'C'", 'max_length': '1'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lessisbetter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'units': ('django.db.models.fields.CharField', [], {'default': "'seconds'", 'max_length': '20'}),
            'units_title': ('django.db.models.fields.CharField', [], {'default': "'Time'", 'max_length': '30'})
        },
        'codespeed.branch': {
            'Meta': {'unique_together': "(('name', 'project'),)", 'object_name': 'Branch'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'branches'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.environment': {
            'Meta': {'object_name': 'Environment'},
            'cpu': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'memory': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'os': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        },
        'codespeed.executable': {
            'Meta': {'object_name': 'Executable'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executables'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'repo_pass': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'repo_path': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_type': ('django.db.models.fields.CharField', [], {'default': "'N'", 'max_length': '1'}),
            'repo_user': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'track': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'codespeed.report': {
            'Meta': {'unique_together': "(('revision', 'executable', 'environment'),)", 'object_name': 'Report'},
            '_tablecache': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'colorcode': ('django.db.models.fields.CharField', [], {'default': "'none'", 'max_length': '10'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Revision']"}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'codespeed.result': {
            'Meta': {'unique_together': "(('revision', 'executable', 'benchmark', 'environment'),)", 'object_name': 'Result'},
            'benchmark': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Benchmark']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Revision']"}),
            'std_dev': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_max': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_min': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'codespeed.revision': {
            'Meta': {'unique_together': "(('commitid', 'branch'),)", 'object_name': 'Revision'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'branch': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'revisions'", 'to': "orm['codespeed.Branch']"}),
            'commitid': ('django.db.models.fields.CharField', [], {'max_length': '42'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'revisions'", 'to': "orm['codespeed.Project']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        }
    }

    complete_apps = ['codespeed']

########NEW FILE########
__FILENAME__ = 0008_auto__chg_field_benchmark_description
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Benchmark.description'
        db.alter_column('codespeed_benchmark', 'description', self.gf('django.db.models.fields.CharField')(max_length=300))


    def backwards(self, orm):
        
        # Changing field 'Benchmark.description'
        db.alter_column('codespeed_benchmark', 'description', self.gf('django.db.models.fields.CharField')(max_length=200))


    models = {
        'codespeed.benchmark': {
            'Meta': {'object_name': 'Benchmark'},
            'benchmark_type': ('django.db.models.fields.CharField', [], {'default': "'C'", 'max_length': '1'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '300', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lessisbetter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'units': ('django.db.models.fields.CharField', [], {'default': "'seconds'", 'max_length': '20'}),
            'units_title': ('django.db.models.fields.CharField', [], {'default': "'Time'", 'max_length': '30'})
        },
        'codespeed.branch': {
            'Meta': {'unique_together': "(('name', 'project'),)", 'object_name': 'Branch'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'branches'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.environment': {
            'Meta': {'object_name': 'Environment'},
            'cpu': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'memory': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'os': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        },
        'codespeed.executable': {
            'Meta': {'object_name': 'Executable'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executables'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'repo_pass': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'repo_path': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_type': ('django.db.models.fields.CharField', [], {'default': "'N'", 'max_length': '1'}),
            'repo_user': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'track': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'codespeed.report': {
            'Meta': {'unique_together': "(('revision', 'executable', 'environment'),)", 'object_name': 'Report'},
            '_tablecache': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'colorcode': ('django.db.models.fields.CharField', [], {'default': "'none'", 'max_length': '10'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Revision']"}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'codespeed.result': {
            'Meta': {'unique_together': "(('revision', 'executable', 'benchmark', 'environment'),)", 'object_name': 'Result'},
            'benchmark': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Benchmark']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Revision']"}),
            'std_dev': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_max': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_min': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'codespeed.revision': {
            'Meta': {'unique_together': "(('commitid', 'branch'),)", 'object_name': 'Revision'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'branch': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'revisions'", 'to': "orm['codespeed.Branch']"}),
            'commitid': ('django.db.models.fields.CharField', [], {'max_length': '42'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'revisions'", 'blank': 'True', 'to': "orm['codespeed.Project']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        }
    }

    complete_apps = ['codespeed']

########NEW FILE########
__FILENAME__ = 0009_auto__chg_field_revision_project
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Revision.project'
        db.alter_column('codespeed_revision', 'project_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['codespeed.Project']))


    def backwards(self, orm):
        
        # Changing field 'Revision.project'
        db.alter_column('codespeed_revision', 'project_id', self.gf('django.db.models.fields.related.ForeignKey')(default=0, to=orm['codespeed.Project']))


    models = {
        'codespeed.benchmark': {
            'Meta': {'object_name': 'Benchmark'},
            'benchmark_type': ('django.db.models.fields.CharField', [], {'default': "'C'", 'max_length': '1'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '300', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lessisbetter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'units': ('django.db.models.fields.CharField', [], {'default': "'seconds'", 'max_length': '20'}),
            'units_title': ('django.db.models.fields.CharField', [], {'default': "'Time'", 'max_length': '30'})
        },
        'codespeed.branch': {
            'Meta': {'unique_together': "(('name', 'project'),)", 'object_name': 'Branch'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'branches'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.environment': {
            'Meta': {'object_name': 'Environment'},
            'cpu': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'memory': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'os': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        },
        'codespeed.executable': {
            'Meta': {'object_name': 'Executable'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executables'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'repo_pass': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'repo_path': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_type': ('django.db.models.fields.CharField', [], {'default': "'N'", 'max_length': '1'}),
            'repo_user': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'track': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'codespeed.report': {
            'Meta': {'unique_together': "(('revision', 'executable', 'environment'),)", 'object_name': 'Report'},
            '_tablecache': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'colorcode': ('django.db.models.fields.CharField', [], {'default': "'none'", 'max_length': '10'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Revision']"}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'codespeed.result': {
            'Meta': {'unique_together': "(('revision', 'executable', 'benchmark', 'environment'),)", 'object_name': 'Result'},
            'benchmark': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Benchmark']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Revision']"}),
            'std_dev': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_max': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_min': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'codespeed.revision': {
            'Meta': {'unique_together': "(('commitid', 'branch'),)", 'object_name': 'Revision'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'branch': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'revisions'", 'to': "orm['codespeed.Branch']"}),
            'commitid': ('django.db.models.fields.CharField', [], {'max_length': '42'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'revisions'", 'null': 'True', 'to': "orm['codespeed.Project']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        }
    }

    complete_apps = ['codespeed']

########NEW FILE########
__FILENAME__ = 0010_auto__add_field_benchmark_default_on_comparison
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    no_dry_run = True

    def forwards(self, orm):
        # Adding field 'Benchmark.default_on_comparison'
        db.add_column('codespeed_benchmark', 'default_on_comparison', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)
        for bench in orm.Benchmark.objects.all():
            bench.default_on_comparison = bench.benchmark_type == 'C'
            bench.save()


    def backwards(self, orm):
        # Deleting field 'Benchmark.default_on_comparison'
        db.delete_column('codespeed_benchmark', 'default_on_comparison')


    models = {
        'codespeed.benchmark': {
            'Meta': {'object_name': 'Benchmark'},
            'benchmark_type': ('django.db.models.fields.CharField', [], {'default': "'C'", 'max_length': '1'}),
            'default_on_comparison': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '300', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lessisbetter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'units': ('django.db.models.fields.CharField', [], {'default': "'seconds'", 'max_length': '20'}),
            'units_title': ('django.db.models.fields.CharField', [], {'default': "'Time'", 'max_length': '30'})
        },
        'codespeed.branch': {
            'Meta': {'unique_together': "(('name', 'project'),)", 'object_name': 'Branch'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'branches'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.environment': {
            'Meta': {'object_name': 'Environment'},
            'cpu': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'memory': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'os': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        },
        'codespeed.executable': {
            'Meta': {'object_name': 'Executable'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executables'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'repo_pass': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'repo_path': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_type': ('django.db.models.fields.CharField', [], {'default': "'N'", 'max_length': '1'}),
            'repo_user': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'track': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'codespeed.report': {
            'Meta': {'unique_together': "(('revision', 'executable', 'environment'),)", 'object_name': 'Report'},
            '_tablecache': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'colorcode': ('django.db.models.fields.CharField', [], {'default': "'none'", 'max_length': '10'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Revision']"}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'codespeed.result': {
            'Meta': {'unique_together': "(('revision', 'executable', 'benchmark', 'environment'),)", 'object_name': 'Result'},
            'benchmark': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Benchmark']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Revision']"}),
            'std_dev': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_max': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_min': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'codespeed.revision': {
            'Meta': {'unique_together': "(('commitid', 'branch'),)", 'object_name': 'Revision'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'branch': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'revisions'", 'to': "orm['codespeed.Branch']"}),
            'commitid': ('django.db.models.fields.CharField', [], {'max_length': '42'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'revisions'", 'null': 'True', 'to': "orm['codespeed.Project']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        }
    }

    complete_apps = ['codespeed']

########NEW FILE########
__FILENAME__ = 0011_auto__add_field_project_commit_browsing_url
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Project.commit_browsing_url'
        db.add_column('codespeed_project', 'commit_browsing_url', self.gf('django.db.models.fields.CharField')(default='', max_length=200, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Project.commit_browsing_url'
        db.delete_column('codespeed_project', 'commit_browsing_url')


    models = {
        'codespeed.benchmark': {
            'Meta': {'object_name': 'Benchmark'},
            'benchmark_type': ('django.db.models.fields.CharField', [], {'default': "'C'", 'max_length': '1'}),
            'default_on_comparison': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '300', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lessisbetter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'units': ('django.db.models.fields.CharField', [], {'default': "'seconds'", 'max_length': '20'}),
            'units_title': ('django.db.models.fields.CharField', [], {'default': "'Time'", 'max_length': '30'})
        },
        'codespeed.branch': {
            'Meta': {'unique_together': "(('name', 'project'),)", 'object_name': 'Branch'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'branches'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.environment': {
            'Meta': {'object_name': 'Environment'},
            'cpu': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'memory': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'os': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        },
        'codespeed.executable': {
            'Meta': {'object_name': 'Executable'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executables'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.project': {
            'Meta': {'object_name': 'Project'},
            'commit_browsing_url': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'repo_pass': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'repo_path': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_type': ('django.db.models.fields.CharField', [], {'default': "'N'", 'max_length': '1'}),
            'repo_user': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'track': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'codespeed.report': {
            'Meta': {'unique_together': "(('revision', 'executable', 'environment'),)", 'object_name': 'Report'},
            '_tablecache': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'colorcode': ('django.db.models.fields.CharField', [], {'default': "'none'", 'max_length': '10'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Revision']"}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'codespeed.result': {
            'Meta': {'unique_together': "(('revision', 'executable', 'benchmark', 'environment'),)", 'object_name': 'Result'},
            'benchmark': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Benchmark']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Revision']"}),
            'std_dev': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_max': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_min': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'codespeed.revision': {
            'Meta': {'unique_together': "(('commitid', 'branch'),)", 'object_name': 'Revision'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'branch': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'revisions'", 'to': "orm['codespeed.Branch']"}),
            'commitid': ('django.db.models.fields.CharField', [], {'max_length': '42'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'revisions'", 'null': 'True', 'to': "orm['codespeed.Project']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        }
    }

    complete_apps = ['codespeed']

########NEW FILE########
__FILENAME__ = 0011_auto__del_unique_executable_name__add_unique_executable_project_name
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'Executable', fields ['name']
        db.delete_unique('codespeed_executable', ['name'])

        # Adding unique constraint on 'Executable', fields ['project', 'name']
        db.create_unique('codespeed_executable', ['project_id', 'name'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Executable', fields ['project', 'name']
        db.delete_unique('codespeed_executable', ['project_id', 'name'])

        # Adding unique constraint on 'Executable', fields ['name']
        db.create_unique('codespeed_executable', ['name'])


    models = {
        'codespeed.benchmark': {
            'Meta': {'object_name': 'Benchmark'},
            'benchmark_type': ('django.db.models.fields.CharField', [], {'default': "'C'", 'max_length': '1'}),
            'default_on_comparison': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '300', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lessisbetter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'units': ('django.db.models.fields.CharField', [], {'default': "'seconds'", 'max_length': '20'}),
            'units_title': ('django.db.models.fields.CharField', [], {'default': "'Time'", 'max_length': '30'})
        },
        'codespeed.branch': {
            'Meta': {'unique_together': "(('name', 'project'),)", 'object_name': 'Branch'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'branches'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.environment': {
            'Meta': {'object_name': 'Environment'},
            'cpu': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'memory': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'os': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        },
        'codespeed.executable': {
            'Meta': {'unique_together': "(('name', 'project'),)", 'object_name': 'Executable'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executables'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'repo_pass': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'repo_path': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_type': ('django.db.models.fields.CharField', [], {'default': "'N'", 'max_length': '1'}),
            'repo_user': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'track': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'codespeed.report': {
            'Meta': {'unique_together': "(('revision', 'executable', 'environment'),)", 'object_name': 'Report'},
            '_tablecache': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'colorcode': ('django.db.models.fields.CharField', [], {'default': "'none'", 'max_length': '10'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Revision']"}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'codespeed.result': {
            'Meta': {'unique_together': "(('revision', 'executable', 'benchmark', 'environment'),)", 'object_name': 'Result'},
            'benchmark': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Benchmark']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Revision']"}),
            'std_dev': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_max': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_min': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'codespeed.revision': {
            'Meta': {'unique_together': "(('commitid', 'branch'),)", 'object_name': 'Revision'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'branch': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'revisions'", 'to': "orm['codespeed.Branch']"}),
            'commitid': ('django.db.models.fields.CharField', [], {'max_length': '42'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'revisions'", 'null': 'True', 'to': "orm['codespeed.Project']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        }
    }

    complete_apps = ['codespeed']

########NEW FILE########
__FILENAME__ = 0012_auto__add_field_benchmark_parent__add_field_project_commit_browsing_ur
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Benchmark.parent'
        db.add_column('codespeed_benchmark', 'parent',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['codespeed.Benchmark'], null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Benchmark.parent'
        db.delete_column('codespeed_benchmark', 'parent_id')

        # Deleting field 'Project.commit_browsing_url'
        db.delete_column('codespeed_project', 'commit_browsing_url')


    models = {
        'codespeed.benchmark': {
            'Meta': {'object_name': 'Benchmark'},
            'benchmark_type': ('django.db.models.fields.CharField', [], {'default': "'C'", 'max_length': '1'}),
            'default_on_comparison': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '300', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lessisbetter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['codespeed.Benchmark']", 'null': 'True'}),
            'units': ('django.db.models.fields.CharField', [], {'default': "'seconds'", 'max_length': '20'}),
            'units_title': ('django.db.models.fields.CharField', [], {'default': "'Time'", 'max_length': '30'})
        },
        'codespeed.branch': {
            'Meta': {'unique_together': "(('name', 'project'),)", 'object_name': 'Branch'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'branches'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.environment': {
            'Meta': {'object_name': 'Environment'},
            'cpu': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kernel': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'memory': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'os': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        },
        'codespeed.executable': {
            'Meta': {'unique_together': "(('name', 'project'),)", 'object_name': 'Executable'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'executables'", 'to': "orm['codespeed.Project']"})
        },
        'codespeed.project': {
            'Meta': {'object_name': 'Project'},
            'commit_browsing_url': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'repo_pass': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'repo_path': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'repo_type': ('django.db.models.fields.CharField', [], {'default': "'N'", 'max_length': '1'}),
            'repo_user': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'track': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'codespeed.report': {
            'Meta': {'unique_together': "(('revision', 'executable', 'environment'),)", 'object_name': 'Report'},
            '_tablecache': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'colorcode': ('django.db.models.fields.CharField', [], {'default': "'none'", 'max_length': '10'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reports'", 'to': "orm['codespeed.Revision']"}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'codespeed.result': {
            'Meta': {'unique_together': "(('revision', 'executable', 'benchmark', 'environment'),)", 'object_name': 'Result'},
            'benchmark': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Benchmark']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Environment']"}),
            'executable': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Executable']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'results'", 'to': "orm['codespeed.Revision']"}),
            'std_dev': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_max': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'val_min': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'codespeed.revision': {
            'Meta': {'unique_together': "(('commitid', 'branch'),)", 'object_name': 'Revision'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'branch': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'revisions'", 'to': "orm['codespeed.Branch']"}),
            'commitid': ('django.db.models.fields.CharField', [], {'max_length': '42'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'revisions'", 'null': 'True', 'to': "orm['codespeed.Project']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'})
        }
    }

    complete_apps = ['codespeed']
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
import os
import json

from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.conf import settings

from codespeed.github import GITHUB_URL_RE


class Project(models.Model):
    REPO_TYPES = (
        ('N', 'none'),
        ('G', 'git'),
        ('H', 'Github.com'),
        ('M', 'mercurial'),
        ('S', 'subversion'),
    )

    name = models.CharField(unique=True, max_length=30)
    repo_type = models.CharField(
        "Repository type", max_length=1, choices=REPO_TYPES, default='N')
    repo_path = models.CharField("Repository URL", blank=True, max_length=200)
    repo_user = models.CharField("Repository username",
                                 blank=True, max_length=100)
    repo_pass = models.CharField("Repository password",
                                 blank=True, max_length=100)
    commit_browsing_url = models.CharField("Commit browsing URL",
                                           blank=True, max_length=200)
    track = models.BooleanField("Track changes", default=False)

    def __unicode__(self):
        return self.name

    @property
    def repo_name(self):
        # name not defined for None, GitHub or Subversion
        if self.repo_type in ('N', 'H', 'S'):
            error = 'Not supported for %s project' % self.get_repo_type_display()
            raise AttributeError(error)

        return os.path.splitext(self.repo_path.split(os.sep)[-1])[0]

    @property
    def working_copy(self):
        # working copy exists for mercurial and git only
        if self.repo_type in ('N', 'H', 'S'):
            error = 'Not supported for %s project' % self.get_repo_type_display()
            raise AttributeError(error)

        return os.path.join(settings.REPOSITORY_BASE_PATH, self.repo_name)

    def save(self, *args, **kwargs):
        """Provide a default for commit browsing url in github repositories."""
        if not self.commit_browsing_url and self.repo_type == 'H':
            m = GITHUB_URL_RE.match(self.repo_path)
            if m:
                url = 'https://github.com/%s/%s/commit/{commitid}' % (
                    m.group('username'), m.group('project')
                )
                self.commit_browsing_url = url
        super(Project, self).save(*args, **kwargs)


class Branch(models.Model):
    name = models.CharField(max_length=20)
    project = models.ForeignKey(Project, related_name="branches")

    def __unicode__(self):
        return self.project.name + ":" + self.name

    class Meta:
        unique_together = ("name", "project")


class Revision(models.Model):
    # git and mercurial's SHA-1 length is 40
    commitid = models.CharField(max_length=42)
    tag = models.CharField(max_length=20, blank=True)
    date = models.DateTimeField(null=True)
    message = models.TextField(blank=True)
    project = models.ForeignKey(Project, related_name="revisions",
                                null=True, blank=True)
    author = models.CharField(max_length=30, blank=True)
    branch = models.ForeignKey(Branch, related_name="revisions")

    def get_short_commitid(self):
        return self.commitid[:10]

    def get_browsing_url(self):
        return self.branch.project.commit_browsing_url.format(**self.__dict__)

    def __unicode__(self):
        if self.date is None:
            date = None
        else:
            date = self.date.strftime("%b %d, %H:%M")
        string = " - ".join(filter(None, (date, self.commitid, self.tag)))
        if self.branch.name != settings.DEF_BRANCH:
            string += " - " + self.branch.name
        return string

    class Meta:
        unique_together = ("commitid", "branch")

    def clean(self):
        if not self.commitid or self.commitid == "None":
            raise ValidationError("Invalid commit id %s" % self.commitid)
        if self.branch.project.repo_type == "S":
            try:
                long(self.commitid)
            except ValueError:
                raise ValidationError("Invalid SVN commit id %s" % self.commitid)


class Executable(models.Model):
    name = models.CharField(max_length=30)
    description = models.CharField(max_length=200, blank=True)
    project = models.ForeignKey(Project, related_name="executables")

    class Meta:
        unique_together = ('name', 'project')

    def __unicode__(self):
        return self.name


class Benchmark(models.Model):
    B_TYPES = (
        ('C', 'Cross-project'),
        ('O', 'Own-project'),
    )

    name = models.CharField(unique=True, max_length=30)
    parent = models.ForeignKey(
        'self', verbose_name="parent",
        help_text="allows to group benchmarks in hierarchies",
        null=True, blank=True, default=None)
    benchmark_type = models.CharField(max_length=1, choices=B_TYPES, default='C')
    description = models.CharField(max_length=300, blank=True)
    units_title = models.CharField(max_length=30, default='Time')
    units = models.CharField(max_length=20, default='seconds')
    lessisbetter = models.BooleanField("Less is better", default=True)
    default_on_comparison = models.BooleanField(
        "Default on comparison page", default=True)

    def __unicode__(self):
        return self.name

    def clean(self):
        if self.default_on_comparison and self.benchmark_type != 'C':
            raise ValidationError("Only cross-project benchmarks are shown "
                                  "on the comparison page. Deactivate "
                                  "'default_on_comparison' first.")


class Environment(models.Model):
    name = models.CharField(unique=True, max_length=30)
    cpu = models.CharField(max_length=30, blank=True)
    memory = models.CharField(max_length=30, blank=True)
    os = models.CharField(max_length=30, blank=True)
    kernel = models.CharField(max_length=30, blank=True)

    def __unicode__(self):
        return self.name


class Result(models.Model):
    value = models.FloatField()
    std_dev = models.FloatField(blank=True, null=True)
    val_min = models.FloatField(blank=True, null=True)
    val_max = models.FloatField(blank=True, null=True)
    date = models.DateTimeField(blank=True, null=True)
    revision = models.ForeignKey(Revision, related_name="results")
    executable = models.ForeignKey(Executable, related_name="results")
    benchmark = models.ForeignKey(Benchmark, related_name="results")
    environment = models.ForeignKey(Environment, related_name="results")

    def __unicode__(self):
        return u"%s: %s" % (self.benchmark.name, self.value)

    class Meta:
        unique_together = ("revision", "executable", "benchmark", "environment")


class Report(models.Model):
    revision = models.ForeignKey(Revision, related_name="reports")
    environment = models.ForeignKey(Environment, related_name="reports")
    executable = models.ForeignKey(Executable, related_name="reports")
    summary = models.CharField(max_length=64, blank=True)
    colorcode = models.CharField(max_length=10, default="none")
    _tablecache = models.TextField(blank=True)

    def __unicode__(self):
        return u"Report for %s" % self.revision

    class Meta:
        unique_together = ("revision", "executable", "environment")

    def save(self, *args, **kwargs):
        tablelist = self.get_changes_table(force_save=True)
        max_change, max_change_ben, max_change_color = 0, None, "none"
        max_trend, max_trend_ben, max_trend_color = 0, None, "none"
        average_change, average_change_units, average_change_color = 0, None, "none"
        average_trend, average_trend_units, average_trend_color = 0, None, "none"

        # Get default threshold values
        change_threshold = 3.0
        trend_threshold = 5.0
        if (hasattr(settings, 'CHANGE_THRESHOLD') and
                settings.CHANGE_THRESHOLD is not None):
            change_threshold = settings.CHANGE_THRESHOLD
        if hasattr(settings, 'TREND_THRESHOLD') and settings.TREND_THRESHOLD:
            trend_threshold = settings.TREND_THRESHOLD

        # Fetch big changes for each unit type and each benchmark
        for units in tablelist:
            # Total change
            val = units['totals']['change']
            if val == "-":
                continue
            color = self.getcolorcode(val, units['lessisbetter'],
                                      change_threshold)
            if self.is_big_change(val, color, average_change, average_change_color):
                # Do update biggest total change
                average_change = val
                average_change_units = units['units_title']
                average_change_color = color
            # Total trend
            val = units['totals']['trend']
            if val != "-":
                color = self.getcolorcode(val, units['lessisbetter'],
                                          trend_threshold)
                if self.is_big_change(val, color, average_trend, average_trend_color):
                    # Do update biggest total trend change
                    average_trend = val
                    average_trend_units = units['units_title']
                    average_trend_color = color
            for row in units['rows']:
                # Single change
                val = row['change']
                if val == "-":
                    continue
                color = self.getcolorcode(val, units['lessisbetter'],
                                          change_threshold)
                if self.is_big_change(val, color, max_change, max_change_color):
                    # Do update biggest single change
                    max_change = val
                    max_change_ben = row['bench_name']
                    max_change_color = color
                # Single trend
                val = row['trend']
                if val == "-":
                    continue
                color = self.getcolorcode(val, units['lessisbetter'], trend_threshold)
                if self.is_big_change(val, color, max_trend, max_trend_color):
                    # Do update biggest single trend change
                    max_trend = val
                    max_trend_ben = row['bench_name']
                    max_trend_color = color
        # Reinitialize
        self.summary = ""
        self.colorcode = "none"

        # Save summary in order of priority
        # Average change
        if average_change_color != "none":
            #Substitute plus/minus with up/down
            direction = average_change >= 0 and "+" or "-"
            self.summary = "Average %s %s%.1f%%" % (
                average_change_units.lower(),
                direction,
                round(abs(average_change), 1))
            self.colorcode = average_change_color
        # Single benchmark change
        if max_change_color != "none" and self.colorcode != "red":
            #Substitute plus/minus with up/down
            direction = max_change >= 0 and "+" or "-"
            self.summary = "%s %s%.1f%%" % (
                max_change_ben, direction, round(abs(max_change), 1))
            self.colorcode = max_change_color

        # Average trend
        if average_trend_color != "none" and self.colorcode == "none":
            #Substitute plus/minus with up/down
            direction = average_trend >= 0 and "+" or ""
            self.summary = "Average %s trend %s%.1f%%" % (
                average_trend_units.lower(), direction, round(average_trend, 1))
            self.colorcode = average_trend_color == "red"\
                and "yellow" or average_trend_color
        # Single benchmark trend
        if max_trend_color != "none" and self.colorcode != "red":
            if (self.colorcode == "none" or
                    (self.colorcode == "green" and "trend" not in self.summary)):
                direction = max_trend >= 0 and "+" or ""
                self.summary = "%s trend %s%.1f%%" % (
                    max_trend_ben, direction, round(max_trend, 1))
                self.colorcode = max_trend_color == "red"\
                    and "yellow" or max_trend_color

        super(Report, self).save(*args, **kwargs)

    def is_big_change(self, val, color, current_val, current_color):
        if color == "red" and current_color != "red":
            return True
        elif color == "red" and abs(val) > abs(current_val):
            return True
        elif (color == "green" and current_color != "red"
              and abs(val) > abs(current_val)):
            return True
        else:
            return False

    def getcolorcode(self, val, lessisbetter, threshold):
        if lessisbetter:
            val = -val
        colorcode = "none"
        if val < -threshold:
            colorcode = "red"
        elif val > threshold:
            colorcode = "green"
        return colorcode

    def get_changes_table(self, trend_depth=10, force_save=False):
        # Determine whether required trend value is the default one
        default_trend = 10
        if hasattr(settings, 'TREND') and settings.TREND:
            default_trend = settings.TREND
        # If the trend is the default and a forced save is not required
        # just return the cached changes table
        if not force_save and trend_depth == default_trend:
            return self._get_tablecache()
        # Otherwise generate a new changes table
        # Get latest revisions for this branch (which also sets the project)
        try:
            lastrevisions = Revision.objects.filter(
                branch=self.revision.branch
            ).filter(
                date__lte=self.revision.date
            ).order_by('-date')[:trend_depth + 1]
            # Same as self.revision unless in a different branch
            lastrevision = lastrevisions[0]
        except:
            return []
        change_list = []
        pastrevisions = []
        if len(lastrevisions) > 1:
            changerevision = lastrevisions[1]
            change_list = Result.objects.filter(
                revision=changerevision
            ).filter(
                environment=self.environment
            ).filter(
                executable=self.executable
            )
            pastrevisions = lastrevisions[trend_depth - 2:trend_depth + 1]

        result_list = Result.objects.filter(
            revision=lastrevision
        ).filter(
            environment=self.environment
        ).filter(
            executable=self.executable
        )

        tablelist = []
        for units in Benchmark.objects.all().values('units').distinct():
            currentlist = []
            units_title = ""
            hasmin = False
            hasmax = False
            has_stddev = False
            smallest = 1000
            totals = {'change': [], 'trend': []}
            for bench in Benchmark.objects.filter(units=units['units']):
                units_title = bench.units_title
                lessisbetter = bench.lessisbetter
                resultquery = result_list.filter(benchmark=bench, value__gt=0)
                if not len(resultquery):
                    continue

                resobj = resultquery.filter(benchmark=bench)[0]

                std_dev = resobj.std_dev
                if std_dev is not None:
                    has_stddev = True
                else:
                    std_dev = "-"

                val_min = resobj.val_min
                if val_min is not None:
                    hasmin = True
                else:
                    val_min = "-"

                val_max = resobj.val_max
                if val_max is not None:
                    hasmax = True
                else:
                    val_max = "-"

                # Calculate percentage change relative to previous result
                result = resobj.value
                change = "-"
                if len(change_list):
                    c = change_list.filter(benchmark=bench)
                    if c.count() and c[0].value and result:
                        change = (result - c[0].value) * 100 / c[0].value
                        totals['change'].append(result / c[0].value)

                # Calculate trend:
                # percentage change relative to average of 3 previous results
                # Calculate past average
                average = 0
                averagecount = 0
                if len(pastrevisions):
                    for rev in pastrevisions:
                        past_rev = Result.objects.filter(
                            revision=rev
                        ).filter(
                            environment=self.environment
                        ).filter(
                            executable=self.executable
                        ).filter(benchmark=bench)
                        if past_rev.count():
                            average += past_rev[0].value
                            averagecount += 1
                trend = "-"
                if average:
                    average = average / averagecount
                    trend = (result - average) * 100 / average
                    totals['trend'].append(result / average)

                # Retain lowest number different than 0
                # to be used later for calculating significant digits
                if result < smallest and result:
                    smallest = result

                currentlist.append({
                    'bench_name': bench.name,
                    'bench_description': bench.description,
                    'result': result,
                    'std_dev': std_dev,
                    'val_min': val_min,
                    'val_max': val_max,
                    'change': change,
                    'trend': trend
                })

            # Compute Arithmetic averages
            for key in totals.keys():
                if len(totals[key]):
                    totals[key] = float(sum(totals[key]) / len(totals[key]))
                else:
                    totals[key] = "-"

            if totals['change'] != "-":
                # Transform ratio to percentage
                totals['change'] = (totals['change'] - 1) * 100
            if totals['trend'] != "-":
                # Transform ratio to percentage
                totals['trend'] = (totals['trend'] - 1) * 100

            # Calculate significant digits
            digits = 2
            while smallest < 1:
                smallest *= 10
                digits += 1

            tablelist.append({
                'units': units['units'],
                'units_title': units_title,
                'lessisbetter': lessisbetter,
                'has_stddev': has_stddev,
                'hasmin': hasmin,
                'hasmax': hasmax,
                'precission': digits,
                'totals': totals,
                'rows': currentlist
            })
        if force_save:
            self._save_tablecache(tablelist)
        return tablelist

    def get_absolute_url(self):
        return reverse("changes") + "?rev=%s&exe=%s&env=%s" % (
            self.revision.commitid, self.executable.id, self.environment.name)

    def item_description(self):
        if self.summary == "":
            return "no significant changes"
        else:
            return self.summary

    def _save_tablecache(self, data):
        self._tablecache = json.dumps(data)

    def _get_tablecache(self):
        if self._tablecache == '':
            return {}
        return json.loads(self._tablecache)

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
"""Default settings for Codespeed"""

## General default options ##
WEBSITE_NAME = "MySpeedSite" # This name will be used in the reports RSS feed

DEF_ENVIRONMENT = None #Name of the environment which should be selected as default

DEF_BRANCH = "default" # Defines the default branch to be used.
                       # In git projects, this branch is usually be calles
                       # "master"

DEF_BASELINE = None # Which executable + revision should be default as a baseline
                    # Given as the name of the executable and commitid of the revision
                    # Example: defaultbaseline = {'executable': 'myexe', 'revision': '21'}

TREND = 10 # Default value for the depth of the trend
           # Used by reports for the latest runs and changes view

# Threshold that determines when a performance change over the last result is significant
CHANGE_THRESHOLD = 3.0

# Threshold that determines when a performance change
# over a number of revisions is significant
TREND_THRESHOLD = 5.0

## Changes view options ##
DEF_EXECUTABLE = None # Executable that should be chosen as default in the changes view
                      # Given as the name of the executable.
                      # Example: defaultexecutable = "myexe"

SHOW_AUTHOR_EMAIL_ADDRESS = True # Whether to show the authors email address in the
                                 # changes log

## Timeline view options ##
DEF_BENCHMARK = None   # Default selected benchmark. Possible values:
                       #   None: will show a grid of plot thumbnails, or a
                       #       text message when the number of plots exceeds 30
                       #   "grid": will always show as default the grid of plots
                       #   "show_none": will show a text message (better
                       #       default when there are lots of benchmarks)
                       #   "mybench": will select benchmark named "mybench"

DEF_TIMELINE_LIMIT = 50  # Default number of revisions to be plotted
                         # Possible values 10,50,200,1000

#TIMELINE_BRANCHES = True # NOTE: Only the default branch is currently shown
                         # Get timeline results for specific branches
                         # Set to False if you want timeline plots and results only for trunk.

## Comparison view options ##
CHART_TYPE = 'normal bars' # The options are 'normal bars', 'stacked bars' and 'relative bars'

NORMALIZATION = False # True will enable normalization as the default selection
                      # in the Comparison view. The default normalization can be
                      # chosen in the defaultbaseline setting

CHART_ORIENTATION = 'vertical' # 'vertical' or 'horizontal can be chosen as
                              # default chart orientation

COMP_EXECUTABLES = None  # Which executable + revision should be checked as default
                         # Given as a list of tuples containing the
                         # name of an executable + commitid of a revision
                         # An 'L' denotes the last revision
                         # Example:
                         # COMP_EXECUTABLES = [
                         #     ('myexe', '21df2423ra'),
                         #     ('myexe', 'L'),]

########NEW FILE########
__FILENAME__ = subversion
# -*- coding: utf-8 -*-
'''Subversion commit logs support'''
from datetime import datetime


def updaterepo(project):
    """Not needed for a remote subversion repo"""
    return [{'error': False}]


def getlogs(newrev, startrev):
    import pysvn

    logs = []
    log_messages = []
    loglimit = 200

    def get_login(realm, username, may_save):
        return True, newrev.branch.project.repo_user, newrev.branch.project.repo_pass, False

    client = pysvn.Client()
    if newrev.branch.project.repo_user != "":
        client.callback_get_login = get_login

    try:
        log_messages = \
            client.log(
                newrev.branch.project.repo_path,
                revision_start=pysvn.Revision(
                        pysvn.opt_revision_kind.number, startrev.commitid
                ),
                revision_end=pysvn.Revision(
                    pysvn.opt_revision_kind.number, newrev.commitid
                )
            )
    except pysvn.ClientError as e:
        raise RuntimeError(e.args)
    except ValueError:
        raise RuntimeError(
            "'%s' is an invalid subversion revision number" % newrev.commitid)
    log_messages.reverse()
    s = len(log_messages)
    while s > loglimit:
        log_messages = log_messages[:s]
        s = len(log_messages) - 1

    for log in log_messages:
        try:
            author = log.author
        except AttributeError:
            author = ""
        date = datetime.fromtimestamp(log.date).strftime("%Y-%m-%d %H:%M:%S")
        message = log.message
        # Add log unless it is the last commit log, which has already been tested
        logs.append({
            'date': date, 'author': author, 'message': message,
            'commitid': log.revision.number})
    return logs

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import copy
import json
import os

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings

from codespeed.models import (Project, Benchmark, Revision, Branch, Executable,
                              Environment, Result, Report)
from codespeed.views import getbaselineexecutables
from codespeed import settings as default_settings


class TestAddResult(TestCase):

    def setUp(self):
        self.path = reverse('codespeed.views.add_result')
        self.e = Environment(name='Dual Core', cpu='Core 2 Duo 8200')
        self.e.save()
        temp = datetime.today()
        self.cdate = datetime(
            temp.year, temp.month, temp.day, temp.hour, temp.minute, temp.second)
        self.data = {
            'commitid': '23',
            'branch': 'default',
            'project': 'MyProject',
            'executable': 'myexe O3 64bits',
            'benchmark': 'float',
            'environment': 'Dual Core',
            'result_value': 456,
        }

    def test_add_correct_result(self):
        """Add correct result data"""
        response = self.client.post(self.path, self.data)

        # Check that we get a success response
        self.assertEquals(response.status_code, 202)
        self.assertEquals(response.content, "Result data saved successfully")

        # Check that the data was correctly saved
        e = Environment.objects.get(name='Dual Core')
        b = Benchmark.objects.get(name='float')
        self.assertEquals(b.benchmark_type, "C")
        self.assertEquals(b.units, "seconds")
        self.assertEquals(b.lessisbetter, True)
        p = Project.objects.get(name='MyProject')
        branch = Branch.objects.get(name='default', project=p)
        r = Revision.objects.get(commitid='23', branch=branch)
        i = Executable.objects.get(name='myexe O3 64bits')
        res = Result.objects.get(
            revision=r,
            executable=i,
            benchmark=b,
            environment=e
        )
        self.assertTrue(res.value, 456)

    def test_add_non_default_result(self):
        """Add result data with non-mandatory options"""
        modified_data = copy.deepcopy(self.data)
        revision_date = self.cdate - timedelta(minutes=2)
        modified_data['revision_date'] = revision_date
        result_date = self.cdate + timedelta(minutes=2)
        modified_data['result_date'] = result_date
        modified_data['std_dev'] = 1.11111
        modified_data['max'] = 2
        modified_data['min'] = 1.0
        response = self.client.post(self.path, modified_data)
        self.assertEquals(response.status_code, 202)
        self.assertEquals(response.content, "Result data saved successfully")
        e = Environment.objects.get(name='Dual Core')
        p = Project.objects.get(name='MyProject')
        branch = Branch.objects.get(name='default', project=p)
        r = Revision.objects.get(commitid='23', branch=branch)

        # Tweak the resolution down to avoid failing over very slight differences:
        self.assertEquals(r.date, revision_date)

        i = Executable.objects.get(name='myexe O3 64bits')
        b = Benchmark.objects.get(name='float')
        res = Result.objects.get(
            revision=r,
            executable=i,
            benchmark=b,
            environment=e
        )
        self.assertEquals(res.date, result_date)
        self.assertEquals(res.std_dev, 1.11111)
        self.assertEquals(res.val_max, 2)
        self.assertEquals(res.val_min, 1)

    def test_bad_environment(self):
        """Should return 400 when environment does not exist"""
        bad_name = '10 Core'
        self.data['environment'] = bad_name
        response = self.client.post(self.path, self.data)
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, "Environment " + bad_name + " not found")
        self.data['environment'] = 'Dual Core'

    def test_empty_argument(self):
        """Should respond 400 when a POST request has an empty argument"""
        for key in self.data:
            backup = self.data[key]
            self.data[key] = ""
            response = self.client.post(self.path, self.data)
            self.assertEquals(response.status_code, 400)
            self.assertEquals(
                response.content, 'Value for key "' + key + '" empty in request')
            self.data[key] = backup

    def test_missing_argument(self):
        """Should respond 400 when a POST request is missing an argument"""
        for key in self.data:
            backup = self.data[key]
            del(self.data[key])
            response = self.client.post(self.path, self.data)
            self.assertEquals(response.status_code, 400)
            self.assertEquals(
                response.content, 'Key "' + key + '" missing from request')
            self.data[key] = backup

    def test_report_is_not_created(self):
        '''Should not create a report when adding a single result'''
        response = self.client.post(self.path, self.data)
        number_of_reports = len(Report.objects.all())
        # After adding one result for one revision, there should be no reports
        self.assertEquals(number_of_reports, 0)

    def test_report_is_created(self):
        """Should create a report when adding a result for two revisions"""
        response = self.client.post(self.path, self.data)

        modified_data = copy.deepcopy(self.data)
        modified_data['commitid'] = "23233"
        response = self.client.post(self.path, modified_data)
        number_of_reports = len(Report.objects.all())
        # After adding a result for a second revision, a report should be created
        self.assertEquals(number_of_reports, 1)

    def test_submit_data_with_none_timestamp(self):
        """Should add a default revision date when timestamp is None"""
        modified_data = copy.deepcopy(self.data)
        # The value None will get urlencoded and converted to a "None" string
        modified_data['revision_date'] = None
        response = self.client.post(self.path, modified_data)
        self.assertEquals(response.status_code, 202)

    def test_add_result_with_no_project(self):
        """Should add a revision with the project"""
        modified_data = copy.deepcopy(self.data)
        modified_data['project'] = "My new project"
        modified_data['executable'] = "My new executable"
        response = self.client.post(self.path, modified_data)
        self.assertEquals(response.status_code, 202)
        self.assertEquals(response.content, "Result data saved successfully")


class TestAddJSONResults(TestCase):

    def setUp(self):
        self.path = reverse('codespeed.views.add_json_results')
        self.e = Environment(name='bigdog', cpu='Core 2 Duo 8200')
        self.e.save()
        temp = datetime.today()
        self.cdate = datetime(
            temp.year, temp.month, temp.day, temp.hour, temp.minute, temp.second)

        self.data = [
            {'commitid': '123',
             'project': 'pypy',
             'branch': 'default',
             'executable': 'pypy-c',
             'benchmark': 'Richards',
             'environment': 'bigdog',
             'result_value': 456},
            {'commitid': '456',
             'project': 'pypy',
             'branch': 'default',
             'executable': 'pypy-c',
             'benchmark': 'Richards',
             'environment': 'bigdog',
             'result_value': 457},
            {'commitid': '456',
             'project': 'pypy',
             'branch': 'default',
             'executable': 'pypy-c',
             'benchmark': 'Richards2',
             'environment': 'bigdog',
             'result_value': 34},
            {'commitid': '789',
             'project': 'pypy',
             'branch': 'default',
             'executable': 'pypy-c',
             'benchmark': 'Richards',
             'environment': 'bigdog',
             'result_value': 458},
        ]

    def test_add_correct_results(self):
        """Should add all results when the request data is valid"""
        response = self.client.post(self.path,
                                    {'json': json.dumps(self.data)})

        # Check that we get a success response
        self.assertEquals(response.status_code, 202)
        self.assertEquals(response.content,
                          "All result data saved successfully")

        # Check that the data was correctly saved
        e = Environment.objects.get(name='bigdog')
        b = Benchmark.objects.get(name='Richards')
        self.assertEquals(b.benchmark_type, "C")
        self.assertEquals(b.units, "seconds")
        self.assertEquals(b.lessisbetter, True)
        p = Project.objects.get(name='pypy')
        branch = Branch.objects.get(name='default', project=p)
        r = Revision.objects.get(commitid='123', branch=branch)
        i = Executable.objects.get(name='pypy-c')
        res = Result.objects.get(
            revision=r,
            executable=i,
            benchmark=b,
            environment=e
        )
        self.assertTrue(res.value, 456)
        resdate = res.date.strftime("%Y%m%dT%H%M%S")
        selfdate = self.cdate.strftime("%Y%m%dT%H%M%S")
        self.assertTrue(resdate, selfdate)

        r = Revision.objects.get(commitid='456', branch=branch)
        res = Result.objects.get(
            revision=r,
            executable=i,
            benchmark=b,
            environment=e
        )
        self.assertTrue(res.value, 457)

        r = Revision.objects.get(commitid='789', branch=branch)
        res = Result.objects.get(
            revision=r,
            executable=i,
            benchmark=b,
            environment=e
        )
        self.assertTrue(res.value, 458)

    def test_bad_environment(self):
        """Add result associated with non-existing environment.
           Only change one item in the list.
        """
        data = self.data[0]
        bad_name = 'bigdog1'
        data['environment'] = bad_name
        response = self.client.post(self.path,
                                    {'json': json.dumps(self.data)})

        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, "Environment " + bad_name + " not found")
        data['environment'] = 'bigdog'

    def test_empty_argument(self):
        '''Should return 400 when making a request with an empty argument'''
        data = self.data[1]
        for key in data:
            backup = data[key]
            data[key] = ""
            response = self.client.post(self.path,
                                        {'json': json.dumps(self.data)})
            self.assertEquals(response.status_code, 400)
            self.assertEquals(response.content, 'Value for key "' + key + '" empty in request')
            data[key] = backup

    def test_missing_argument(self):
        '''Should return 400 when making a request with a missing argument'''
        data = self.data[2]
        for key in data:
            backup = data[key]
            del(data[key])
            response = self.client.post(self.path,
                                        {'json': json.dumps(self.data)})
            self.assertEquals(response.status_code, 400)
            self.assertEquals(response.content, 'Key "' + key + '" missing from request')
            data[key] = backup

    def test_report_is_created(self):
        '''Should create a report when adding json results for two revisions
        plus a third revision with one result less than the last one'''
        response = self.client.post(self.path,
                                    {'json': json.dumps(self.data)})

        # Check that we get a success response
        self.assertEquals(response.status_code, 202)

        number_of_reports = len(Report.objects.all())
        # After adding 4 result for 3 revisions, only 2 reports should be created
        # The third revision will need an extra result for Richards2 in order
        # to trigger report creation
        self.assertEquals(number_of_reports, 1)


class TestTimeline(TestCase):
    fixtures = ["timeline_tests.json"]

    def test_fixture(self):
        """Test the loaded fixture data
        """
        env = Environment.objects.filter(name="Dual Core")
        self.assertEquals(len(env), 1)
        benchmarks = Benchmark.objects.filter(name="float")
        self.assertEquals(len(benchmarks), 1)
        self.assertEquals(benchmarks[0].units, "seconds")
        results = benchmarks[0].results.all()
        self.assertEquals(len(results), 8)

    def test_gettimelinedata(self):
        """Test that gettimelinedata returns correct timeline data
        """
        path = reverse('codespeed.views.gettimelinedata')
        data = {
            "exe":  "1,2",
            "base": "2+4",
            "ben":  "float",
            "env":  "1",
            "revs": 2
        }
        response = self.client.get(path, data)
        self.assertEquals(response.status_code, 200)
        responsedata = json.loads(response.content)
        self.assertEquals(
            responsedata['error'], "None", "there should be no errors")
        self.assertEquals(
            len(responsedata['timelines']), 1, "there should be 1 benchmark")
        self.assertEquals(
            len(responsedata['timelines'][0]['branches']['default']),
            2,
            "there should be 2 timelines")
        self.assertEquals(
            len(responsedata['timelines'][0]['branches']['default']['1']),
            2,
            "There are 2 datapoints")
        self.assertEquals(
            responsedata['timelines'][0]['branches']['default']['1'][1],
            [u'2011-04-13T17:04:22', 2000.0, 1.11111, u'2', u'default'],
            "Wrong data returned: ")


class TestCodespeedSettings(TestCase):
    """Test codespeed.settings
    """

    def setUp(self):
        self.cs_setting_keys = [key for key in dir(default_settings) if key.isupper()]

    def test_website_name(self):
        """See if WEBSITENAME is set
        """
        self.assertTrue(default_settings.WEBSITE_NAME)
        self.assertEqual(default_settings.WEBSITE_NAME, 'MySpeedSite',
                         "Change codespeed settings in project.settings")

    def test_keys_in_settings(self):
        """Check that all settings attributes from codespeed.settings exist
        in django.conf.settings
        """
        for k in self.cs_setting_keys:
            self.assertTrue(hasattr(settings, k),
                            "Key {0} is missing in settings.py.".format(k))

    def test_settings_attributes(self):
        """Check if all settings from codespeed.settings equals
        django.conf.settings
        """
        for k in self.cs_setting_keys:
            self.assertEqual(getattr(settings, k), getattr(default_settings, k))


class TestViewHelpers(TestCase):
    """Test helper functions in codespeed.views"""

    def setUp(self):
        self.project = Project.objects.create(name='Test')
        self.executable = Executable.objects.create(
            name='TestExecutable', project=self.project)
        self.branch = Branch.objects.create(name='master', project=self.project)

    def test_get_baseline_executables(self):
        # No revisions, no baseline
        result = getbaselineexecutables()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['executable'], 'none')

        # Check that a tagged revision will be included as baseline
        revision1 = Revision.objects.create(commitid='1', tag='0.1', branch=self.branch)
        result = getbaselineexecutables()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['executable'], 'none')
        self.assertEqual(result[1]['executable'], self.executable)
        self.assertEqual(result[1]['revision'], revision1)

        revision2 = Revision.objects.create(commitid='2', tag='0.2', branch=self.branch)
        result = getbaselineexecutables()
        self.assertEqual(len(result), 3)

        # An untagged revision will not be available as baseline
        Revision.objects.create(commitid='3', branch=self.branch)
        result = getbaselineexecutables()
        self.assertEqual(len(result), 3)


class TestProject(TestCase):

    def setUp(self):
        self.github_project = Project(repo_type='H',
                                      repo_path='https://github.com/tobami/codespeed.git')
        self.git_project = Project(repo_type='G', repo_path='/home/foo/codespeed')

    def test_repo_name(self):
        """Test that only projects with local repositories have a repo_name attribute
        """
        self.assertEqual(self.git_project.repo_name, 'codespeed')

        self.assertRaises(AttributeError, getattr, self.github_project, 'repo_name')

    def test_working_copy(self):
        """Test that only projects with local repositories have a working_copy attribute
        """
        self.assertEqual(self.git_project.working_copy,
                         os.path.join(settings.REPOSITORY_BASE_PATH,
                                      self.git_project.repo_name))

        self.assertRaises(
            AttributeError, getattr, self.github_project, 'working_copy')

    def test_github_browsing_url(self):
        """If empty, the commit browsing url will be filled in with a default
        value when using github repository.
        """

        # It should work with https:// as well as git:// urls
        self.github_project.save()
        self.assertEquals(self.github_project.commit_browsing_url,
                          'https://github.com/tobami/codespeed.git/'
                          'commit/{commitid}')

        self.github_project.repo_path = 'git://github.com/tobami/codespeed.git'
        self.github_project.save()
        self.assertEquals(self.github_project.commit_browsing_url,
                          'https://github.com/tobami/codespeed.git/'
                          'commit/{commitid}')

        # If filled in, commit browsing url should not change
        self.github_project.commit_browsing_url = 'https://example.com/{commitid}'
        self.github_project.save()
        self.assertEquals(self.github_project.commit_browsing_url,
                          'https://example.com/{commitid}')

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls import patterns, include, url
from django.core.urlresolvers import reverse
from django.views.generic import TemplateView

from codespeed.feeds import LatestEntries

feeds = {'latest': LatestEntries}

urlpatterns = patterns('',
    (r'^$', TemplateView.as_view(template_name='home.html')),
    (r'^about/$', TemplateView.as_view(template_name='about.html')),
    # RSS for reports
    (r'^feeds/(?P<url>.*)/$', LatestEntries()),
)

urlpatterns += patterns('codespeed.views',
    url(r'^reports/$', 'reports', name='reports'),
    url(r'^changes/$', 'changes', name='changes'),
    url(r'^changes/table/$', 'getchangestable', name='getchangestable'),
    url(r'^changes/logs/$', 'displaylogs', name='displaylogs'),
    url(r'^timeline/$', 'timeline', name='timeline'),
    url(r'^timeline/json/$', 'gettimelinedata', name='gettimelinedata'),
    url(r'^comparison/$', 'comparison', name='comparison'),
    url(r'^comparison/json/$', 'getcomparisondata', name='getcomparisondata'),
)

urlpatterns += patterns('codespeed.views',
    # URLs for adding results
    (r'^result/add/json/$', 'add_json_results'),
    (r'^result/add/$', 'add_result'),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from datetime import datetime
from itertools import chain
import json
import logging

from django.http import (HttpResponse, Http404, HttpResponseNotAllowed,
                         HttpResponseBadRequest)
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from codespeed.models import (Environment, Report, Project, Revision, Result,
                              Executable, Benchmark, Branch)


logger = logging.getLogger(__name__)


def no_environment_error(request):
    admin_url = reverse('admin:codespeed_environment_changelist')
    return render_to_response('codespeed/nodata.html', {
        'message': ('You need to configure at least one Environment. '
                    'Please go to the '
                    '<a href="%s">admin interface</a>' % admin_url)
    }, context_instance=RequestContext(request))


def no_default_project_error(request):
    admin_url = reverse('admin:codespeed_project_changelist')
    return render_to_response('codespeed/nodata.html', {
        'message': ('You need to configure at least one one Project as '
                    'default (checked "Track changes" field).<br />'
                    'Please go to the '
                    '<a href="%s">admin interface</a>' % admin_url)
    }, context_instance=RequestContext(request))


def no_executables_error(request):
    return render_to_response('codespeed/nodata.html', {
        'message': 'There needs to be at least one executable'
    }, context_instance=RequestContext(request))


def no_data_found(request):
    return render_to_response('codespeed/nodata.html', {
        'message': 'No data found'
    }, context_instance=RequestContext(request))


def getbaselineexecutables():
    baseline = [{
        'key': "none",
        'name': "None",
        'executable': "none",
        'revision': "none",
    }]
    executables = Executable.objects.select_related('project')
    revs = Revision.objects.exclude(tag="").select_related('branch__project')
    maxlen = 22
    for rev in revs:
        # Add executables that correspond to each tagged revision.
        for exe in [e for e in executables if e.project == rev.branch.project]:
            exestring = str(exe)
            if len(exestring) > maxlen:
                exestring = str(exe)[0:maxlen] + "..."
            name = exestring + " " + rev.tag
            key = str(exe.id) + "+" + str(rev.id)
            baseline.append({
                'key': key,
                'executable': exe,
                'revision': rev,
                'name': name,
            })
    # move default to first place
    if hasattr(settings, 'DEF_BASELINE') and settings.DEF_BASELINE is not None:
        try:
            exename = settings.DEF_BASELINE['executable']
            commitid = settings.DEF_BASELINE['revision']
            for base in baseline:
                if base['key'] == "none":
                    continue
                if (base['executable'].name == exename and
                        base['revision'].commitid == commitid):
                    baseline.remove(base)
                    baseline.insert(1, base)
                    break
        except KeyError:
            # TODO: write to server logs
            #error in settings.DEF_BASELINE
            pass
    return baseline


def get_default_environment(enviros, data, multi=False):
    """Returns the default environment. Preference level is:
        * Present in URL parameters (permalinks)
        * Value in settings.py
        * First Environment ID

    """
    defaultenviros = []
    # Use permalink values
    if 'env' in data:
        for env_value in data['env'].split(","):
            for env in enviros:
                try:
                    env_id = int(env_value)
                except ValueError:
                    # Not an int
                    continue
                for env in enviros:
                    if env_id == env.id:
                        defaultenviros.append(env)
            if not multi:
                break
    # Use settings.py value
    if not defaultenviros and not multi:
        if (hasattr(settings, 'DEF_ENVIRONMENT') and
                settings.DEF_ENVIRONMENT is not None):
            for env in enviros:
                if settings.DEF_ENVIRONMENT == env.name:
                    defaultenviros.append(env)
                    break
    # Last fallback
    if not defaultenviros:
        defaultenviros = enviros
    if multi:
        return defaultenviros
    else:
        return defaultenviros[0]


def getdefaultexecutable():
    default = None
    if hasattr(settings, 'DEF_EXECUTABLE') and settings.DEF_EXECUTABLE is not None:
        try:
            default = Executable.objects.get(name=settings.DEF_EXECUTABLE)
        except Executable.DoesNotExist:
            pass
    if default is None:
        execquery = Executable.objects.filter(project__track=True)
        if len(execquery):
            default = execquery[0]

    return default


def getcomparisonexes():
    all_executables = {}
    exekeys = []
    baselines = getbaselineexecutables()
    for proj in Project.objects.all():
        executables = []
        executablekeys = []
        maxlen = 20
        # add all tagged revs for any project
        for exe in baselines:
            if exe['key'] is not "none" and exe['executable'].project == proj:
                executablekeys.append(exe['key'])
                executables.append(exe)

        # add latest revs of the project
        branches = Branch.objects.filter(project=proj)
        for branch in branches:
            try:
                rev = Revision.objects.filter(branch=branch).latest('date')
            except Revision.DoesNotExist:
                continue
            # Now only append when tag == "",
            # because we already added tagged revisions
            if rev.tag == "":
                for exe in Executable.objects.filter(project=proj):
                    exestring = str(exe)
                    if len(exestring) > maxlen:
                        exestring = str(exe)[0:maxlen] + "..."
                    name = exestring + " latest"
                    if branch.name != 'default':
                        name += " in branch '" + branch.name + "'"
                    key = str(exe.id) + "+L+" + branch.name
                    executablekeys.append(key)
                    executables.append({
                        'key': key,
                        'executable': exe,
                        'revision': rev,
                        'name': name,
                    })
        all_executables[proj] = executables
        exekeys += executablekeys
    return all_executables, exekeys


def getcomparisondata(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed('GET')
    data = request.GET

    executables, exekeys = getcomparisonexes()
    benchmarks = Benchmark.objects.all()
    environments = Environment.objects.all()

    compdata = {}
    compdata['error'] = "Unknown error"
    for proj in executables:
        for exe in executables[proj]:
            compdata[exe['key']] = {}
            for env in environments:
                compdata[exe['key']][env.id] = {}

                # Load all results for this env/executable/revision in a dict
                # for fast lookup
                results = dict(Result.objects.filter(
                    environment=env,
                    executable=exe['executable'],
                    revision=exe['revision'],
                ).values_list('benchmark', 'value'))

                for bench in benchmarks:
                    compdata[exe['key']][env.id][bench.id] = results.get(bench.id, None)

    compdata['error'] = "None"

    return HttpResponse(json.dumps(compdata))


def comparison(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed('GET')
    data = request.GET

    # Configuration of default parameters
    enviros = Environment.objects.all()
    if not enviros:
        return no_environment_error(request)
    checkedenviros = get_default_environment(enviros, data, multi=True)

    if not len(Project.objects.all()):
        return no_default_project_error(request)

    # Check whether there exist appropiate executables
    if not getdefaultexecutable():
        return no_executables_error(request)

    executables, exekeys = getcomparisonexes()
    checkedexecutables = []
    if 'exe' in data:
        for i in data['exe'].split(","):
            if not i:
                continue
            if i in exekeys:
                checkedexecutables.append(i)
    elif hasattr(settings, 'COMP_EXECUTABLES') and settings.COMP_EXECUTABLES:
        for exe, rev in settings.COMP_EXECUTABLES:
            try:
                exe = Executable.objects.get(name=exe)
                key = str(exe.id) + "+"
                if rev == "L":
                    key += rev
                else:
                    rev = Revision.objects.get(commitid=rev)
                    key += str(rev.id)
                key += "+default"
                if key in exekeys:
                    checkedexecutables.append(key)
                else:
                    #TODO: log
                    pass
            except Executable.DoesNotExist:
                #TODO: log
                pass
            except Revision.DoesNotExist:
                #TODO: log
                pass
    if not checkedexecutables:
        checkedexecutables = exekeys

    units_titles = Benchmark.objects.filter(
        benchmark_type="C"
    ).values('units_title').distinct()
    units_titles = [unit['units_title'] for unit in units_titles]
    benchmarks = {}
    bench_units = {}
    for unit in units_titles:
        # Only include benchmarks marked as cross-project
        benchmarks[unit] = Benchmark.objects.filter(
            benchmark_type="C"
        ).filter(units_title=unit)
        units = benchmarks[unit][0].units
        lessisbetter = (benchmarks[unit][0].lessisbetter and
                        ' (less is better)' or ' (more is better)')
        bench_units[unit] = [
            [b.id for b in benchmarks[unit]], lessisbetter, units
        ]
    checkedbenchmarks = []
    if 'ben' in data:
        checkedbenchmarks = []
        for i in data['ben'].split(","):
            if not i:
                continue
            try:
                checkedbenchmarks.append(Benchmark.objects.get(id=int(i)))
            except Benchmark.DoesNotExist:
                pass
    if not checkedbenchmarks:
        # Only include benchmarks marked as cross-project
        checkedbenchmarks = Benchmark.objects.filter(
            benchmark_type="C", default_on_comparison=True)

    charts = ['normal bars', 'stacked bars', 'relative bars']
    # Don't show relative charts as an option if there is only one executable
    # Relative charts need normalization
    if len(executables) == 1:
        charts.remove('relative bars')

    selectedchart = charts[0]
    if 'chart' in data and data['chart'] in charts:
        selectedchart = data['chart']
    elif hasattr(settings, 'CHART_TYPE') and settings.CHART_TYPE in charts:
        selectedchart = settings.CHART_TYPE

    selectedbaseline = "none"
    if 'bas' in data and data['bas'] in exekeys:
        selectedbaseline = data['bas']
    elif 'bas' in data:
        # bas is present but is none
        pass
    elif (len(exekeys) > 1 and hasattr(settings, 'NORMALIZATION') and
            settings.NORMALIZATION):
        try:
            # TODO: Avoid calling twice getbaselineexecutables
            selectedbaseline = getbaselineexecutables()[1]['key']
            # Uncheck exe used for normalization
            try:
                checkedexecutables.remove(selectedbaseline)
            except ValueError:
                pass  # The selected baseline was not checked
        except:
            pass  # Keep "none" as default baseline

    selecteddirection = False
    if ('hor' in data and data['hor'] == "true" or
        hasattr(settings, 'CHART_ORIENTATION') and
            settings.CHART_ORIENTATION == 'horizontal'):
        selecteddirection = True

    return render_to_response('codespeed/comparison.html', {
        'checkedexecutables': checkedexecutables,
        'checkedbenchmarks': checkedbenchmarks,
        'checkedenviros': checkedenviros,
        'executables': executables,
        'benchmarks': benchmarks,
        'bench_units': json.dumps(bench_units),
        'enviros': enviros,
        'charts': charts,
        'selectedbaseline': selectedbaseline,
        'selectedchart': selectedchart,
        'selecteddirection': selecteddirection
    }, context_instance=RequestContext(request))


def gettimelinedata(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed('GET')
    data = request.GET

    timeline_list = {'error': 'None', 'timelines': []}

    executables = data.get('exe', "").split(",")
    if not filter(None, executables):
        timeline_list['error'] = "No executables selected"
        return HttpResponse(json.dumps(timeline_list))
    environment = None
    try:
        environment = get_object_or_404(Environment, id=data.get('env'))
    except ValueError:
        Http404()

    benchmarks = []
    number_of_revs = data.get('revs', 10)

    if data['ben'] == 'grid':
        benchmarks = Benchmark.objects.all().order_by('name')
        number_of_revs = 15
    elif data['ben'] == 'show_none':
        benchmarks = []
    else:
        benchmarks = [get_object_or_404(Benchmark, name=data['ben'])]

    baselinerev = None
    baselineexe = None
    if data.get('base') not in (None, 'none', 'undefined'):
        exeid, revid = data['base'].split("+")
        baselinerev = Revision.objects.get(id=revid)
        baselineexe = Executable.objects.get(id=exeid)
    for bench in benchmarks:
        lessisbetter = bench.lessisbetter and ' (less is better)' or ' (more is better)'
        timeline = {
            'benchmark':             bench.name,
            'benchmark_id':          bench.id,
            'benchmark_description': bench.description,
            'units':                 bench.units,
            'lessisbetter':          lessisbetter,
            'branches':              {},
            'baseline':              "None",
        }
        # Temporary
        trunks = []
        if Branch.objects.filter(name=settings.DEF_BRANCH):
            trunks.append(settings.DEF_BRANCH)
        # For now, we'll only work with trunk branches
        append = False
        for branch in trunks:
            append = False
            timeline['branches'][branch] = {}
            for executable in executables:
                resultquery = Result.objects.filter(
                    benchmark=bench
                ).filter(
                    environment=environment
                ).filter(
                    executable=executable
                ).filter(
                    revision__branch__name=branch
                ).select_related(
                    "revision"
                ).order_by('-revision__date')[:number_of_revs]
                if not len(resultquery):
                    continue

                results = []
                for res in resultquery:
                    std_dev = ""
                    if res.std_dev is not None:
                        std_dev = res.std_dev
                    results.append(
                        [
                            res.revision.date.isoformat(), res.value, std_dev,
                            res.revision.get_short_commitid(), branch
                        ]
                    )
                timeline['branches'][branch][executable] = results
                append = True
            if baselinerev is not None and append:
                try:
                    baselinevalue = Result.objects.get(
                        executable=baselineexe,
                        benchmark=bench,
                        revision=baselinerev,
                        environment=environment
                    ).value
                except Result.DoesNotExist:
                    timeline['baseline'] = "None"
                else:
                    # determine start and end revision (x axis)
                    # from longest data series
                    results = []
                    for exe in timeline['branches'][branch]:
                        if len(timeline['branches'][branch][exe]) > len(results):
                            results = timeline['branches'][branch][exe]
                    end = results[0][0]
                    start = results[len(results) - 1][0]
                    timeline['baseline'] = [
                        [str(start), baselinevalue],
                        [str(end), baselinevalue]
                    ]
        if append:
            timeline_list['timelines'].append(timeline)

    if not len(timeline_list['timelines']) and data['ben'] != 'show_none':
        response = 'No data found for the selected options'
        timeline_list['error'] = response
    return HttpResponse(json.dumps(timeline_list))


def timeline(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed('GET')
    data = request.GET

    ## Configuration of default parameters ##
    # Default Environment
    enviros = Environment.objects.all()
    if not enviros:
        return no_environment_error(request)
    defaultenviro = get_default_environment(enviros, data)

    # Default Project
    defaultproject = Project.objects.filter(track=True)
    if not len(defaultproject):
        return no_default_project_error(request)
    else:
        defaultproject = defaultproject[0]

    checkedexecutables = []
    if 'exe' in data:
        for i in data['exe'].split(","):
            if not i:
                continue
            try:
                checkedexecutables.append(Executable.objects.get(id=int(i)))
            except Executable.DoesNotExist:
                pass

    if not checkedexecutables:
        checkedexecutables = Executable.objects.filter(project__track=True)

    if not len(checkedexecutables):
        return no_executables_error(request)

    # TODO: we need branches for all tracked projects
    branch_list = [
        branch.name for branch in Branch.objects.filter(project=defaultproject)]
    branch_list.sort()

    defaultbranch = ""
    if "default" in branch_list:
        defaultbranch = settings.DEF_BRANCH
    if data.get('bran') in branch_list:
        defaultbranch = data.get('bran')

    baseline = getbaselineexecutables()
    defaultbaseline = None
    if len(baseline) > 1:
        defaultbaseline = str(baseline[1]['executable'].id) + "+"
        defaultbaseline += str(baseline[1]['revision'].id)
    if "base" in data and data['base'] != "undefined":
        try:
            defaultbaseline = data['base']
        except ValueError:
            pass

    lastrevisions = [10, 50, 200, 1000]
    defaultlast = settings.DEF_TIMELINE_LIMIT
    if 'revs' in data:
        if int(data['revs']) not in lastrevisions:
            lastrevisions.append(data['revs'])
        defaultlast = data['revs']

    benchmarks = Benchmark.objects.all()
    grid_limit = 30
    defaultbenchmark = "grid"
    if not len(benchmarks):
        return no_data_found(request)
    elif len(benchmarks) == 1:
        defaultbenchmark = benchmarks[0]
    elif hasattr(settings, 'DEF_BENCHMARK') and settings.DEF_BENCHMARK is not None:
        if settings.DEF_BENCHMARK in ['grid', 'show_none']:
            defaultbenchmark = settings.DEF_BENCHMARK
        else:
            try:
                defaultbenchmark = Benchmark.objects.get(
                    name=settings.DEF_BENCHMARK)
            except Benchmark.DoesNotExist:
                pass
    elif len(benchmarks) >= grid_limit:
        defaultbenchmark = 'show_none'

    if 'ben' in data and data['ben'] != defaultbenchmark:
        if data['ben'] == "show_none":
            defaultbenchmark = data['ben']
        else:
            defaultbenchmark = get_object_or_404(Benchmark, name=data['ben'])

    if 'equid' in data:
        defaultequid = data['equid']
    else:
        defaultequid = "off"

    # Information for template
    executables = {}
    for proj in Project.objects.filter(track=True):
        executables[proj] = Executable.objects.filter(project=proj)
    return render_to_response('codespeed/timeline.html', {
        'checkedexecutables': checkedexecutables,
        'defaultbaseline': defaultbaseline,
        'baseline': baseline,
        'defaultbenchmark': defaultbenchmark,
        'defaultenvironment': defaultenviro,
        'lastrevisions': lastrevisions,
        'defaultlast': defaultlast,
        'executables': executables,
        'benchmarks': benchmarks,
        'environments': enviros,
        'branch_list': branch_list,
        'defaultbranch': defaultbranch,
        'defaultequid': defaultequid
    }, context_instance=RequestContext(request))


def getchangestable(request):
    executable = get_object_or_404(Executable, pk=request.GET.get('exe'))
    environment = get_object_or_404(Environment, pk=request.GET.get('env'))
    try:
        trendconfig = int(request.GET.get('tre'))
    except TypeError:
        raise Http404()
    selectedrev = get_object_or_404(Revision, commitid=request.GET.get('rev'),
                                    branch__project=executable.project)

    report, created = Report.objects.get_or_create(
        executable=executable, environment=environment, revision=selectedrev
    )
    tablelist = report.get_changes_table(trendconfig)

    if not len(tablelist):
        return HttpResponse('<table id="results" class="tablesorter" '
                            'style="height: 232px;"></table>'
                            '<p class="errormessage">No results for this '
                            'parameters</p>')

    return render_to_response('codespeed/changes_table.html', {
        'tablelist': tablelist,
        'trendconfig': trendconfig,
        'rev': selectedrev,
        'exe': executable,
        'env': environment,
    }, context_instance=RequestContext(request))


def changes(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed('GET')
    data = request.GET

    # Configuration of default parameters
    defaultchangethres = 3.0
    defaulttrendthres = 4.0
    if (hasattr(settings, 'CHANGE_THRESHOLD') and
            settings.CHANGE_THRESHOLD is not None):
        defaultchangethres = settings.CHANGE_THRESHOLD
    if (hasattr(settings, 'TREND_THRESHOLD') and
            settings.TREND_THRESHOLD is not None):
        defaulttrendthres = settings.TREND_THRESHOLD

    defaulttrend = 10
    trends = [5, 10, 20, 50, 100]
    if 'tre' in data and int(data['tre']) in trends:
        defaulttrend = int(data['tre'])

    enviros = Environment.objects.all()
    if not enviros:
        return no_environment_error(request)
    defaultenv = get_default_environment(enviros, data)

    defaultexecutable = getdefaultexecutable()
    if not defaultexecutable:
        return no_executables_error(request)

    if "exe" in data:
        try:
            defaultexecutable = Executable.objects.get(id=int(data['exe']))
        except Executable.DoesNotExist:
            pass
        except ValueError:
            pass

    baseline = getbaselineexecutables()
    defaultbaseline = "+"
    if len(baseline) > 1:
        defaultbaseline = str(baseline[1]['executable'].id) + "+"
        defaultbaseline += str(baseline[1]['revision'].id)
    if "base" in data and data['base'] != "undefined":
        try:
            defaultbaseline = data['base']
        except ValueError:
            pass

    # Information for template
    revlimit = 20
    executables = {}
    revisionlists = {}
    projectlist = []
    for proj in Project.objects.filter(track=True):
        executables[proj] = Executable.objects.filter(project=proj)
        projectlist.append(proj)
        branch = Branch.objects.filter(name=settings.DEF_BRANCH, project=proj)
        revisionlists[proj.name] = Revision.objects.filter(
            branch=branch
        ).order_by('-date')[:revlimit]
    # Get lastest revisions for this project and it's "default" branch
    lastrevisions = revisionlists.get(defaultexecutable.project.name)
    if not len(lastrevisions):
        return no_data_found(request)
    selectedrevision = lastrevisions[0]

    if "rev" in data:
        commitid = data['rev']
        try:
            selectedrevision = Revision.objects.get(
                commitid__startswith=commitid, branch=branch
            )
            if not selectedrevision in lastrevisions:
                lastrevisions = list(chain(lastrevisions))
                lastrevisions.append(selectedrevision)
        except Revision.DoesNotExist:
            selectedrevision = lastrevisions[0]
    # This variable is used to know when the newly selected executable
    # belongs to another project (project changed) and then trigger the
    # repopulation of the revision selection selectbox
    projectmatrix = {}
    for proj in executables:
        for e in executables[proj]:
            projectmatrix[e.id] = e.project.name
    projectmatrix = json.dumps(projectmatrix)

    for project, revisions in revisionlists.items():
        revisionlists[project] = [
            (unicode(rev), rev.commitid) for rev in revisions
        ]
    revisionlists = json.dumps(revisionlists)

    return render_to_response('codespeed/changes.html', {
        'defaultenvironment': defaultenv,
        'defaultexecutable': defaultexecutable,
        'selectedrevision': selectedrevision,
        'defaulttrend': defaulttrend,
        'defaultchangethres': defaultchangethres,
        'defaulttrendthres': defaulttrendthres,
        'environments': enviros,
        'executables': executables,
        'projectmatrix': projectmatrix,
        'revisionlists': revisionlists,
        'trends': trends,
    }, context_instance=RequestContext(request))


def reports(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed('GET')

    return render_to_response('codespeed/reports.html', {
        'reports': Report.objects.filter(
            revision__branch__name=settings.DEF_BRANCH
        ).order_by('-revision__date')[:10],
    }, context_instance=RequestContext(request))


def displaylogs(request):
    rev = get_object_or_404(Revision, pk=request.GET.get('revisionid'))
    logs = []
    logs.append(
        {
            'date': str(rev.date), 'author': rev.author,
            'author_email': '', 'message': rev.message,
            'short_commit_id': rev.get_short_commitid(),
            'commitid': rev.commitid
        }
    )
    error = False
    try:
        startrev = Revision.objects.filter(
            branch=rev.branch
        ).filter(date__lt=rev.date).order_by('-date')[:1]
        if not len(startrev):
            startrev = rev
        else:
            startrev = startrev[0]

        remotelogs = getcommitlogs(rev, startrev)
        if len(remotelogs):
            try:
                if remotelogs[0]['error']:
                    error = remotelogs[0]['message']
            except KeyError:
                pass  # no errors
            logs = remotelogs
        else:
            error = 'no logs found'
    except (StandardError, RuntimeError) as e:
        logger.error(
            "Unhandled exception displaying logs for %s: %s",
            rev, e, exc_info=True)
        error = repr(e)

    # add commit browsing url to logs
    project = rev.branch.project
    for log in logs:
        log['commit_browse_url'] = project.commit_browsing_url.format(**log)

    return render_to_response(
        'codespeed/changes_logs.html',
        {'error': error, 'logs': logs,
         'show_email_address': settings.SHOW_AUTHOR_EMAIL_ADDRESS},
        context_instance=RequestContext(request))


def getcommitlogs(rev, startrev, update=False):
    logs = []

    if rev.branch.project.repo_type == 'S':
        from subversion import getlogs, updaterepo
    elif rev.branch.project.repo_type == 'M':
        from mercurial import getlogs, updaterepo
    elif rev.branch.project.repo_type == 'G':
        from git import getlogs, updaterepo
    elif rev.branch.project.repo_type == 'H':
        from github import getlogs, updaterepo
    else:
        if rev.branch.project.repo_type not in ("N", ""):
            logger.warning("Don't know how to retrieve logs from %s project",
                           rev.branch.project.get_repo_type_display())
        return logs

    if update:
        updaterepo(rev.branch.project)

    logs = getlogs(rev, startrev)

    # Remove last log because the startrev log shouldn't be shown
    if len(logs) > 1 and logs[-1].get('commitid') == startrev.commitid:
        logs.pop()

    return logs


def saverevisioninfo(rev):
    log = getcommitlogs(rev, rev, update=True)

    if log:
        log = log[0]
        rev.author = log['author']
        rev.date = log['date']
        rev.message = log['message']


def validate_result(item):
    """
    Validates that a result dictionary has all needed parameters

    It returns a tuple
        Environment, False  when no errors where found
        Errormessage, True  when there is an error
    """
    mandatory_data = [
        'commitid',
        'branch',
        'project',
        'executable',
        'benchmark',
        'environment',
        'result_value',
    ]

    response = {}
    error = True
    for key in mandatory_data:
        if not key in item:
            return 'Key "' + key + '" missing from request', error
        elif key in item and item[key] == "":
            return 'Value for key "' + key + '" empty in request', error

    # Check that the Environment exists
    try:
        e = Environment.objects.get(name=item['environment'])
        error = False
        return e, error
    except Environment.DoesNotExist:
        return "Environment %(environment)s not found" % item, error


def create_report_if_enough_data(rev, exe, e):
    """Triggers Report creation when there are enough results"""
    last_revs = Revision.objects.filter(
        branch=rev.branch
    ).order_by('-date')[:2]
    if len(last_revs) > 1:
        current_results = rev.results.filter(executable=exe, environment=e)
        last_results = last_revs[1].results.filter(
            executable=exe, environment=e)
        # If there is are at least as many results as in the last revision,
        # create new report
        if len(current_results) >= len(last_results):
            logger.debug("create_report_if_enough_data: About to create new report")
            report, created = Report.objects.get_or_create(
                executable=exe, environment=e, revision=rev
            )
            report.full_clean()
            report.save()
            logger.debug("create_report_if_enough_data: Created new report.")


def save_result(data):
    res, error = validate_result(data)
    if error:
        return res, True
    else:
        assert(isinstance(res, Environment))
        env = res

    p, created = Project.objects.get_or_create(name=data["project"])
    branch, created = Branch.objects.get_or_create(name=data["branch"],
                                                   project=p)
    b, created = Benchmark.objects.get_or_create(name=data["benchmark"])

    if created:
        if "description" in data:
            b.description = data["description"]
        if "units" in data:
            b.units = data["units"]
        if "units_title" in data:
            b.units_title = data["units_title"]
        if "lessisbetter" in data:
            b.lessisbetter = data["lessisbetter"]
        b.full_clean()
        b.save()

    try:
        rev = branch.revisions.get(commitid=data['commitid'])
    except Revision.DoesNotExist:
        rev_date = data.get("revision_date")
        # "None" (as string) can happen when we urlencode the POST data
        if not rev_date or rev_date in ["", "None"]:
            rev_date = datetime.today()
        rev = Revision(branch=branch, project=p, commitid=data['commitid'],
                       date=rev_date)
        try:
            rev.full_clean()
        except ValidationError as e:
            return str(e), True
        if p.repo_type not in ("N", ""):
            try:
                saverevisioninfo(rev)
            except RuntimeError as e:
                logger.warning("unable to save revision %s info: %s", rev, e,
                               exc_info=True)
        rev.save()

    exe, created = Executable.objects.get_or_create(
        name=data['executable'],
        project=p
    )

    try:
        r = Result.objects.get(
            revision=rev, executable=exe, benchmark=b, environment=env)
    except Result.DoesNotExist:
        r = Result(revision=rev, executable=exe, benchmark=b, environment=env)

    r.value = data["result_value"]
    if 'result_date' in data:
        r.date = data["result_date"]
    elif rev.date:
        r.date = rev.date
    else:
        r.date = datetime.now()

    r.std_dev = data.get('std_dev')
    r.val_min = data.get('min')
    r.val_max = data.get('max')

    r.full_clean()
    r.save()

    return (rev, exe, env), False


@csrf_exempt
def add_result(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed('POST')
    data = request.POST

    response, error = save_result(data)
    if error:
        logger.error("Could not save result: " + response)
        return HttpResponseBadRequest(response)
    else:
        create_report_if_enough_data(response[0], response[1], response[2])
        logger.debug("add_result: completed")
        return HttpResponse("Result data saved successfully", status=202)


@csrf_exempt
def add_json_results(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed('POST')
    if not request.POST.get('json'):
        return HttpResponseBadRequest("No key 'json' in POST payload")
    data = json.loads(request.POST['json'])
    logger.info("add_json_results request with %d entries." % len(data))

    unique_reports = set()
    i = 0
    for result in data:
        i += 1
        logger.debug("add_json_results: save item %d." % i)
        response, error = save_result(result)
        if error:
            logger.debug(
                "add_json_results: could not save item %d because %s" % (
                i, response))
            return HttpResponseBadRequest(response)
        else:
            unique_reports.add(response)

    logger.debug("add_json_results: about to create reports")
    for rep in unique_reports:
        create_report_if_enough_data(rep[0], rep[1], rep[2])

    logger.debug("add_json_results: completed")

    return HttpResponse("All result data saved successfully", status=202)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sample_project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = client
# encoding: utf-8

from urlparse import urljoin
import logging
import platform
import urllib
import sys


def save_to_speedcenter(url=None, project=None, commitid=None, executable=None,
                        benchmark=None, result_value=None, **kwargs):
    """Save a benchmark result to your speedcenter server

    Mandatory:

    :param url:
        Codespeed server endpoint
        (e.g. `http://codespeed.example.org/result/add/`)
    :param project:
        Project name
    :param commitid:
        VCS identifier
    :param executable:
        The executable name
    :param benchmark:
        The name of this particular benchmark
    :param float result_value:
        The benchmark result

    Optional:

    :param environment:
        System description
    :param date revision_date:
        Optional, default will be either VCS commit, if available, or the
        current date
    :param date result_date:
        Optional
    :param float std_dev:
        Optional
    :param float max:
        Optional
    :param float min:
        Optional
    """

    data = {
        'project': project,
        'commitid': commitid,
        'executable': executable,
        'benchmark': benchmark,
        'result_value': result_value,
    }

    data.update(kwargs)

    if not data.get('environment', None):
        data['environment'] = platform.platform(aliased=True)

    f = urllib.urlopen(url, urllib.urlencode(data))

    response = f.read()
    status = f.getcode()

    f.close()

    if status == 202:
        logging.debug("Server %s: HTTP %s: %s", url, status, response)
    else:
        raise IOError("Server %s returned HTTP %s" % (url, status))


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("--benchmark")
    parser.add_option("--commitid")
    parser.add_option("--environment",
        help="Use a custom Codespeed environment")
    parser.add_option("--executable")
    parser.add_option("--max", type="float")
    parser.add_option("--min", type="float")
    parser.add_option("--project")
    parser.add_option("--branch")
    parser.add_option("--result-date")
    parser.add_option("--result-value", type="float")
    parser.add_option("--revision_date")
    parser.add_option("--std-dev", type="float")
    parser.add_option("--url",
        help="URL of your Codespeed server (e.g. http://codespeed.example.org)")

    (options, args) = parser.parse_args()

    if args:
        parser.error("All arguments must be provided as command-line options")

    # Yes, the optparse manpage has a snide comment about "required options"
    # being gramatically dubious. Yes, it's still wrong about not needing to
    # do this.
    required = ('url', 'environment', 'project', 'commitid', 'executable',
                'benchmark', 'result_value')

    if not all(getattr(options, i) for i in required):
        parser.error("The following parameters must be provided:\n\t%s" % "\n\t".join(
            "--%s".replace("_", "-") % i for i in required))

    kwargs = {}
    for k, v in options.__dict__.items():
        if v is not None:
            kwargs[k] = v
    kwargs.setdefault('branch', 'default')

    if not kwargs['url'].endswith("/result/add/"):
        kwargs['url'] = urljoin(kwargs['url'], '/result/add/')

    try:
        save_to_speedcenter(**kwargs)
        sys.exit(0)
    except StandardError, e:
        logging.error("Error saving results: %s", e)
        sys.exit(1)

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
# Django settings for a speedcenter project.
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

BASEDIR = os.path.abspath(os.path.dirname(__file__))
TOPDIR = os.path.split(BASEDIR)[1]

#: The directory which should contain checked out source repositories:
REPOSITORY_BASE_PATH = os.path.join(BASEDIR, "repos")

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASEDIR, 'data.db'),
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
USE_I18N = False

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(BASEDIR, "media")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'as%n_m#)^vee2pe91^^@c))sl7^c6t-9r8n)_69%)2yt+(la2&'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # 'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

if DEBUG:
    import traceback
    import logging

    # Define a class that logs unhandled errors
    class LogUncatchedErrors:
        def process_exception(self, request, exception):
            logging.error("Unhandled Exception on request for %s\n%s" %
                                 (request.build_absolute_uri(),
                                  traceback.format_exc()))
    # And add it to the middleware classes
    MIDDLEWARE_CLASSES += ('sample_project.settings.LogUncatchedErrors',)

    # set shown level of logging output to debug
    logging.basicConfig(level=logging.DEBUG)

ROOT_URLCONF = '{0}.urls'.format(TOPDIR)

TEMPLATE_DIRS = (
    os.path.join(BASEDIR, 'templates'),
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.request',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'codespeed',
    'south',
)
SOUTH_TESTS_MIGRATE = False

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASEDIR, "sitestatic")
STATICFILES_DIRS = (
    os.path.join(BASEDIR, 'static'),
)

# Codespeed settings that can be overwritten here.
from codespeed.settings import *

## General default options ##
WEBSITE_NAME = "MySpeedSite" # This name will be used in the reports RSS feed

#DEF_ENVIRONMENT = None #Name of the environment which should be selected as default


#DEF_BASELINE = None # Which executable + revision should be default as a baseline
                    # Given as the name of the executable and commitid of the revision
                    # Example: defaultbaseline = {'executable': 'myexe', 'revision': '21'}

#TREND = 10 # Default value for the depth of the trend
           # Used by reports for the latest runs and changes view

# Threshold that determines when a performance change over the last result is significant
#CHANGE_THRESHOLD = 3.0

# Threshold that determines when a performance change
# over a number of revisions is significant
#TREND_THRESHOLD  = 5.0

## Changes view options ##
#DEF_EXECUTABLE = None # Executable that should be chosen as default in the changes view
                      # Given as the name of the executable.
                      # Example: defaultexecutable = "myexe"

#SHOW_AUTHOR_EMAIL_ADDRESS = True # Whether to show the authors email address in the
                                 # changes log

## Timeline view options ##
#DEF_BENCHMARK = "grid" # Default selected benchmark. Possible values:
                       #   "grid": will show the grid of plots
                       #   "show_none": will just show a text message
                       #   "mybench": will select benchmark "mybench"

#DEF_TIMELINE_LIMIT = 50  # Default number of revisions to be plotted
                         # Possible values 10,50,200,1000

#TIMELINE_BRANCHES = True # NOTE: Only the default branch is currently shown
                         # Get timeline results for specific branches
                         # Set to False if you want timeline plots and results only for trunk.

## Comparison view options ##
#CHART_TYPE = 'normal bars' # The options are 'normal bars', 'stacked bars' and 'relative bars'

#NORMALIZATION = False # True will enable normalization as the default selection
                      # in the Comparison view. The default normalization can be
                      # chosen in the defaultbaseline setting

#CHART_ORIENTATION = 'vertical' # 'vertical' or 'horizontal can be chosen as
                              # default chart orientation

#COMP_EXECUTABLES = None  # Which executable + revision should be checked as default
                         # Given as a list of tuples containing the
                         # name of an executable + commitid of a revision
                         # An 'L' denotes the last revision
                         # Example:
                         # COMP_EXECUTABLES = [
                         #     ('myexe', '21df2423ra'),
                         #     ('myexe', 'L'),]

#DEF_BRANCH = "default" # Defines the default branch to be used.
                       # In git projects, this branch is usually be calles
                       # "master"

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-

import os.path

from django.conf import settings
from django.conf.urls import patterns, include
from django.views.generic import RedirectView
from django.core.urlresolvers import reverse
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^', include('codespeed.urls')),
)

if settings.DEBUG:
    # needed for development server
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
__FILENAME__ = create_environment
#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""
Check if an environment exists, create otherwise
"""
import json
import urllib2
from optparse import OptionParser, OptionError
from django.utils import simplejson

CODESPEED_URL='http://speedcenter'

def get_options():
    """Get the options and arguments
    """
    parser = OptionParser()

    parser.add_option("-e", "--environment", dest="environment",
                      help="name of the environment to create")

    (options, args) = parser.parse_args()

    if not options.environment:
        parser.error("No environment given")

    return options, args

def is_environment(environment):
    """check if environment does exist

        return:
            True if it exist
            False if it doesn't exist
    """
    url = CODESPEED_URL + '/api/v1/environment/'
    request = urllib2.Request(url)
    opener = urllib2.build_opener()
    try:
        raw_data = opener.open(request)
    except urllib2.HTTPError as e:
        raise e
    data = simplejson.load(raw_data)
    if environment in [ env['name'] for env in data['objects']]:
        return True
    return False

def create_environment(environment):
    """create the environment

        return:
            True if success
            False if not created
    """
    url = CODESPEED_URL + '/api/v1/environment/'
    data = json.dumps({'name': environment})
    request = urllib2.Request(url, data, {'Content-Type': 'application/json'})
    try:
        f = urllib2.urlopen(request)
        response = f.read()
        f.close()
    except urllib2.HTTPError as e:
        raise e
    return response

def main():
    (options, args) = get_options()
    if is_environment(options.environment):
        print "Found environment, doing nothing."
    else:
        print create_environment(options.environment)

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = create_trunks
# -*- coding: utf-8 -*-
"""
Create the default branch for all existing projects
Starting v 0.8.0 that is mandatory.

Note: This file is assumed to be in the same directory
as the project settings.py. Otherwise you have to set the
shell environment DJANGO_SETTINGS_MODULE
"""
import sys
import os


## Setup to import models from Django app ##
def import_from_string(name):
    """helper to import module from a given string"""
    components = name.split('.')[1:]
    return reduce(lambda mod, y: getattr(mod, y), components, __import__(name))


sys.path.append(os.path.abspath('..'))


if 'DJANGO_SETTINGS_MODULE' in os.environ:
    settings = import_from_string(os.environ['DJANGO_SETTINGS_MODULE'])
else:
    try:
        import settings  # Assumed to be in the same directory.
    except ImportError:
        import sys
        sys.stderr.write(
            "Error: Can't find the file 'settings.py' in the directory "
            "containing %r. It appears you've customized things.\nYou'll have "
            "to run django-admin.py, passing it your settings module.\n(If the"
            " file settings.py does indeed exist, it's causing an ImportError "
            "somehow.)\n" % __file__)
        sys.exit(1)

from django.core.management import setup_environ
setup_environ(settings)
from codespeed.models import Branch, Project


def main():
    """Add Branch default to projects if not there"""
    projects = Project.objects.all()

    for proj in projects:
        if not proj.branches.filter(name='default'):
            trunk = Branch(name='default', project=proj)
            trunk.save()
            print "Created branch 'default' for project {0}".format(proj)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = migrate_script
# -*- coding: utf-8 -*-
"""Adds the default branch to all existing revisions

Note: This file is assumed to be in the same directory
as the project settings.py. Otherwise you have to set the
shell environment DJANGO_SETTINGS_MODULE
"""
import sys
import os


## Setup to import models from Django app ##
def import_from_string(name):
    """helper to import module from a given string"""

    components = name.split('.')[1:]
    return reduce(lambda mod, y: getattr(mod, y), components, __import__(name))

sys.path.append(os.path.abspath('..'))

if 'DJANGO_SETTINGS_MODULE' in os.environ:
    settings = import_from_string(os.environ['DJANGO_SETTINGS_MODULE'])
else:
    try:
        import settings  # Assumed to be in the same directory.
    except ImportError:
        import sys
        sys.stderr.write(
            "Error: Can't find the file 'settings.py' in the directory "
            "containing %r. It appears you've customized things.\nYou'll have "
            "to run django-admin.py, passing it your settings module.\n(If the"
            " file settings.py does indeed exist, it's causing an ImportError "
            "somehow.)\n" % __file__)
        sys.exit(1)

from django.core.management import setup_environ
setup_environ(settings)

from codespeed.models import Revision, Branch


def main():
    """add default branch to revisions"""
    branches = Branch.objects.filter(name='default')

    for branch in branches:
        for rev in Revision.objects.filter(project=branch.project):
            rev.branch = branch
            rev.save()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = import_from_json
# -*- coding: utf-8 -*-
################################################################################
# This script imports PyPy's result data from json files located on the server #
################################################################################
import simplejson, urllib2
import sys
from xml.dom.minidom import parse
from datetime import datetime
import saveresults, savecpython

RESULTS_URLS = {
    'pypy-c-jit': 'http://buildbot.pypy.org/bench_results/',
    'pypy-c':  'http://buildbot.pypy.org/bench_results_nojit/',
}
START_REV = 79485
END_REV = 79485
PROJECT = "PyPy"

for INTERP in RESULTS_URLS:
    RESULTS_URL = RESULTS_URLS[INTERP]
    # get json filenames
    filelist = []
    try:
        datasource = urllib2.urlopen(RESULTS_URL)
        dom = parse(datasource)
        for elem in dom.getElementsByTagName('td'):
            for e in elem.childNodes:
                if len(e.childNodes):
                    filename = e.firstChild.toxml()
                    if e.tagName == "a" and ".json" in filename:
                        if int(filename.replace(".json", "")) >= START_REV and\
                            int(filename.replace(".json", "")) <= END_REV:
                            filelist.append(filename)
    except urllib2.URLError, e:
        response = "None"
        if hasattr(e, 'reason'):
            response = '\n  We failed to reach ' + RESULTS_URL + '\n'
            response += '  Reason: ' + str(e.reason)
        elif hasattr(e, 'code'):
            response = '\n  The server couldn\'t fulfill the request\n'
            response += '  Error code: ' + str(e)
        print "Results Server (%s) response: %s\n" % (RESULTS_URL, response)
        sys.exit(1)
    finally:
        datasource.close()

    # read json result and save to speed.pypy.org
    for filename in filelist:
        print "Reading %s..." % filename
        f = urllib2.urlopen(RESULTS_URL + filename)
        result = simplejson.load(f)
        f.close()
        proj = PROJECT
        revision = result['revision']
        interpreter = INTERP
        int_options = ""
        options = ""
        if 'options' in result:
            options = result['options']

        host = 'tannit'
        #saveresults.save(proj, revision, result['results'], options, interpreter, host)
        if filename == filelist[len(filelist)-1]:
            savecpython.save('cpython', '100', result['results'], options, 'cpython', host)
print "\nOK"

########NEW FILE########
__FILENAME__ = savecpython
# -*- coding: utf-8 -*-
import urllib, urllib2
from datetime import datetime

SPEEDURL = 'http://127.0.0.1:8000/'
#SPEEDURL = 'http://speed.pypy.org/'

def save(project, revision, results, options, executable, host, testing=False):
    testparams = []
    #Parse data
    data = {}
    current_date = datetime.today()

    for b in results:
        bench_name = b[0]
        res_type = b[1]
        results = b[2]
        value = 0
        if res_type == "SimpleComparisonResult":
            value = results['base_time']
        elif res_type == "ComparisonResult":
            value = results['avg_base']
        else:
            print("ERROR: result type unknown " + b[1])
            return 1
        data = {
            'commitid': revision,
            'project': project,
            'executable': executable,
            'benchmark': bench_name,
            'environment': host,
            'result_value': value,
            'result_date': current_date,
        }
        if res_type == "ComparisonResult":
            data['std_dev'] = results['std_changed']
        if testing: testparams.append(data)
        else: send(data)
    if testing: return testparams
    else: return 0

def send(data):
    #save results
    params = urllib.urlencode(data)
    f = None
    response = "None"
    info = str(datetime.today()) + ": Saving result for " + data['executable'] + " revision "
    info += str(data['commitid']) + ", benchmark " + data['benchmark']
    print(info)
    try:
        f = urllib2.urlopen(SPEEDURL + 'result/add/', params)
        response = f.read()
        f.close()
    except urllib2.URLError, e:
        if hasattr(e, 'reason'):
            response = '\n  We failed to reach a server\n'
            response += '  Reason: ' + str(e.reason)
        elif hasattr(e, 'code'):
            response = '\n  The server couldn\'t fulfill the request\n'
            response += '  Error code: ' + str(e)
        print("Server (%s) response: %s\n" % (SPEEDURL, response))
        return 1
    return 0

########NEW FILE########
__FILENAME__ = saveresults
# -*- coding: utf-8 -*-
#######################################################
# This script saves result data                       #
# It expects the format of unladen swallow's perf.py  #
#######################################################
import urllib, urllib2
from datetime import datetime

#SPEEDURL = 'http://127.0.0.1:8000/'
SPEEDURL = 'http://speed.pypy.org/'

def save(project, revision, results, options, executable, environment, testing=False):
    testparams = []
    #Parse data
    data = {}
    current_date = datetime.today()
    for b in results:
        bench_name = b[0]
        res_type = b[1]
        results = b[2]
        value = 0
        if res_type == "SimpleComparisonResult":
            value = results['changed_time']
        elif res_type == "ComparisonResult":
            value = results['avg_changed']
        else:
            print("ERROR: result type unknown " + b[1])
            return 1
        data = {
            'commitid': revision,
            'project': project,
            'executable': executable,
            'benchmark': bench_name,
            'environment': environment,
            'result_value': value,
        }
        if res_type == "ComparisonResult":
            data['std_dev'] = results['std_changed']
        if testing: testparams.append(data)
        else: send(data)
    if testing: return testparams
    else: return 0

def send(data):
    #save results
    params = urllib.urlencode(data)
    f = None
    response = "None"
    info = str(datetime.today()) + ": Saving result for " + data['executable']
    info += " revision " + " " + str(data['commitid']) + ", benchmark "
    info += data['benchmark']
    print(info)
    try:
        f = urllib2.urlopen(SPEEDURL + 'result/add/', params)
        response = f.read()
        f.close()
    except urllib2.URLError, e:
        if hasattr(e, 'reason'):
            response = '\n  We failed to reach a server\n'
            response += '  Reason: ' + str(e.reason)
        elif hasattr(e, 'code'):
            response = '\n  The server couldn\'t fulfill the request\n'
            response += '  Error code: ' + str(e)
        print("Server (%s) response: %s\n" % (SPEEDURL, response))
        return 1
    return 0

########NEW FILE########
__FILENAME__ = test_saveresults
# -*- coding: utf-8 -*-
import saveresults
import unittest

class testSaveresults(unittest.TestCase):
    '''Tests Saveresults script for saving data to speed.pypy.org'''
    fixture = [
        ['ai', 'ComparisonResult', {'avg_base': 0.42950453758219992, 'timeline_link': None, 'avg_changed': 0.43322672843939997, 'min_base': 0.42631793022199999, 'delta_min': '1.0065x faster', 'delta_avg': '1.0087x slower', 'std_changed': 0.0094009621054567376, 'min_changed': 0.423564910889, 'delta_std': '2.7513x larger', 'std_base': 0.0034169249420902843, 't_msg': 'Not significant\n'}],
        ['chaos', 'ComparisonResult', {'avg_base': 0.41804099082939999, 'timeline_link': None, 'avg_changed': 0.11744904518135998, 'min_base': 0.41700506210299998, 'delta_min': '9.0148x faster', 'delta_avg': '3.5593x faster', 'std_changed': 0.14350186143481433, 'min_changed': 0.046257972717299999, 'delta_std': '108.8162x larger', 'std_base': 0.0013187546718754512, 't_msg': 'Significant (t=4.683672, a=0.95)\n'}],
        ['django', 'ComparisonResult', {'avg_base': 0.83651852607739996, 'timeline_link': None, 'avg_changed': 0.48571481704719999, 'min_base': 0.82990884780899998, 'delta_min': '1.7315x faster', 'delta_avg': '1.7222x faster', 'std_changed': 0.006386606999421761, 'min_changed': 0.47929787635799997, 'delta_std': '1.7229x smaller', 'std_base': 0.011003382690633789, 't_msg': 'Significant (t=61.655971, a=0.95)\n'}],
        ['fannkuch', 'ComparisonResult', {'avg_base': 1.8561528205879998, 'timeline_link': None, 'avg_changed': 0.38401727676399999, 'min_base': 1.84801197052, 'delta_min': '5.0064x faster', 'delta_avg': '4.8335x faster', 'std_changed': 0.029594360755246251, 'min_changed': 0.36913013458299998, 'delta_std': '3.2353x larger', 'std_base': 0.0091472519207758066, 't_msg': 'Significant (t=106.269998, a=0.95)\n'}],
        ['float', 'ComparisonResult', {'avg_base': 0.50523018836940004, 'timeline_link': None, 'avg_changed': 0.15490598678593998, 'min_base': 0.49911379814099999, 'delta_min': '6.2651x faster', 'delta_avg': '3.2615x faster', 'std_changed': 0.057739598339608837, 'min_changed': 0.079665899276699995, 'delta_std': '7.7119x larger', 'std_base': 0.007487037523761327, 't_msg': 'Significant (t=13.454285, a=0.95)\n'}], ['gcbench', 'SimpleComparisonResult', {'base_time': 27.236408948899999, 'changed_time': 5.3500790595999996, 'time_delta': '5.0908x faster'}],
        ['html5lib', 'SimpleComparisonResult', {'base_time': 11.666918992999999, 'changed_time': 12.6703209877, 'time_delta': '1.0860x slower'}],
        ['richards', 'ComparisonResult', {'avg_base': 0.29083266258220003, 'timeline_link': None, 'avg_changed': 0.029299402236939998, 'min_base': 0.29025602340700002, 'delta_min': '10.7327x faster', 'delta_avg': '9.9262x faster', 'std_changed': 0.0033452973342946888, 'min_changed': 0.027044057846099999, 'delta_std': '5.6668x larger', 'std_base': 0.00059033067516221327, 't_msg': 'Significant (t=172.154488, a=0.95)\n'}],
        ['rietveld', 'ComparisonResult', {'avg_base': 0.46909418106079998, 'timeline_link': None, 'avg_changed': 1.312631273269, 'min_base': 0.46490097045899997, 'delta_min': '2.1137x slower', 'delta_avg': '2.7982x slower', 'std_changed': 0.44401595627955542, 'min_changed': 0.98267102241500004, 'delta_std': '76.0238x larger', 'std_base': 0.0058404831974135556, 't_msg': 'Significant (t=-4.247692, a=0.95)\n'}],
        ['slowspitfire', 'ComparisonResult', {'avg_base': 0.66740002632140005, 'timeline_link': None, 'avg_changed': 1.6204295635219998, 'min_base': 0.65965509414699997, 'delta_min': '1.9126x slower', 'delta_avg': '2.4280x slower', 'std_changed': 0.27415559151786589, 'min_changed': 1.26167798042, 'delta_std': '20.1860x larger', 'std_base': 0.013581457669479846, 't_msg': 'Significant (t=-7.763579, a=0.95)\n'}],
        ['spambayes', 'ComparisonResult', {'avg_base': 0.279049730301, 'timeline_link': None, 'avg_changed': 1.0178018569945999, 'min_base': 0.27623891830399999, 'delta_min': '3.3032x slower', 'delta_avg': '3.6474x slower', 'std_changed': 0.064953583956645466, 'min_changed': 0.91246294975300002, 'delta_std': '28.9417x larger', 'std_base': 0.0022442880892229711, 't_msg': 'Significant (t=-25.416839, a=0.95)\n'}],
        ['spectral-norm', 'ComparisonResult', {'avg_base': 0.48315834999099999, 'timeline_link': None, 'avg_changed': 0.066225481033300004, 'min_base': 0.476922035217, 'delta_min': '8.0344x faster', 'delta_avg': '7.2957x faster', 'std_changed': 0.013425108838933627, 'min_changed': 0.059360027313200003, 'delta_std': '1.9393x larger', 'std_base': 0.0069225510731835901, 't_msg': 'Significant (t=61.721418, a=0.95)\n'}],
        ['spitfire', 'ComparisonResult', {'avg_base': 7.1179999999999994, 'timeline_link': None, 'avg_changed': 7.2780000000000005, 'min_base': 7.04, 'delta_min': '1.0072x faster', 'delta_avg': '1.0225x slower', 'std_changed': 0.30507376157250898, 'min_changed': 6.9900000000000002, 'delta_std': '3.4948x larger', 'std_base': 0.08729261137118062, 't_msg': 'Not significant\n'}],
        ['twisted_iteration', 'SimpleComparisonResult', {'base_time': 0.148289627437, 'changed_time': 0.035354803126799998, 'time_delta': '4.1943x faster'}],
        ['twisted_web', 'SimpleComparisonResult', {'base_time': 0.11312217194599999, 'changed_time': 0.625, 'time_delta': '5.5250x slower'}]
    ]

    def testGoodInput(self):
        '''Given correct result data, check that every result being saved has the right parameters'''
        for resultparams in saveresults.save("pypy", 71212, self.fixture, "", "pypy-c-jit", "tannit", True):
            self.assertEqual(resultparams['project'], "pypy")
            self.assertEqual(resultparams['commitid'], 71212)
            self.assertEqual(resultparams['executable'], "pypy-c-jit")
            # get dict with correct data for this benchmark
            fixturedata = []
            benchfound = False
            for res in self.fixture:
                if res[0] == resultparams['benchmark']:
                    fixturedata = res
                    benchfound = True
                    break
            self.assertTrue(benchfound)
            # get correct result value depending on the type of result
            fixturevalue = 0
            if fixturedata[1] == "SimpleComparisonResult":
                fixturevalue = fixturedata[2]['changed_time']
            else:
                fixturevalue = fixturedata[2]['avg_changed']
            self.assertEqual(resultparams['result_value'], fixturevalue)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = save_multiple_results
# -*- coding: utf-8 -*-
####################################################
# Sample script that shows how to save result data using json #
####################################################
import urllib
import urllib2
import json


# You need to enter the real URL and have the server running
CODESPEED_URL = 'http://localhost:8000/'

sample_data = [
    {
        "commitid": "8",
        "project": "MyProject",
        "branch": "default",
        "executable": "myexe O3 64bits",
        "benchmark": "float",
        "environment": "Dual Core",
        "result_value": 2500.0
    },
    {
        "commitid": "8",
        "project": "MyProject",
        "branch": "default",
        "executable": "myexe O3 64bits",
        "benchmark": "int",
        "environment": "Dual Core",
        "result_value": 1100
    }
]


def add(data):
    #params = urllib.urlencode(data)
    response = "None"
    try:
        f = urllib2.urlopen(
            CODESPEED_URL + 'result/add/json/', urllib.urlencode(data))
    except urllib2.HTTPError as e:
        print str(e)
        print e.read()
        return
    response = f.read()
    f.close()
    print "Server (%s) response: %s\n" % (CODESPEED_URL, response)


if __name__ == "__main__":
    data = {'json': json.dumps(sample_data)}
    add(data)

########NEW FILE########
__FILENAME__ = save_single_result
# -*- coding: utf-8 -*-
####################################################
# Sample script that shows how to save result data #
####################################################
from datetime import datetime
import urllib
import urllib2

# You need to enter the real URL and have the server running
CODESPEED_URL = 'http://localhost:8000/'

current_date = datetime.today()

# Mandatory fields
data = {
    'commitid': '14',
    'branch': 'default',  # Always use default for trunk/master/tip
    'project': 'MyProject',
    'executable': 'myexe O3 64bits',
    'benchmark': 'float',
    'environment': "Dual Core",
    'result_value': 4000,
}

# Optional fields
data.update({
    'revision_date': current_date,  # Optional. Default is taken either
                                    # from VCS integration or from current date
    'result_date': current_date,  # Optional, default is current date
    'std_dev': 1.11111,  # Optional. Default is blank
    'max': 4001.6,  # Optional. Default is blank
    'min': 3995.1,  # Optional. Default is blank
})


def add(data):
    params = urllib.urlencode(data)
    response = "None"
    print "Saving result for executable %s, revision %s, benchmark %s" % (
        data['executable'], data['commitid'], data['benchmark'])
    try:
        f = urllib2.urlopen(CODESPEED_URL + 'result/add/', params)
    except urllib2.HTTPError as e:
        print str(e)
        print e.read()
        return
    response = f.read()
    f.close()
    print "Server (%s) response: %s\n" % (CODESPEED_URL, response)

if __name__ == "__main__":
    add(data)

########NEW FILE########
__FILENAME__ = save_single_result_via_api
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Submit a single result via the RESTful API using requests

Note, that is just an example. You need to add an user
to get the apikey via the /admin
All resources in the result_data dict need to exist.
"""
import json
import requests


def get_data():
    """Helper function to build a valid POST request to save a result"""
    result_data = {
        'commitid': '/api/v1/revision/2/',
        'branch': '/api/v1/branch/1/', # Always use default for trunk/master/tip
        'project': '/api/v1/project/2/',
        'executable': '/api/v1/executable/1/',
        'benchmark': '/api/v1/benchmark/1/',
        'environment': '/api/v1/environment/2/',
        'result_value': 4000,
        }
    headers = {'content-type': 'application/json',
               'Authorization': 'ApiKey apiuser2:2ee0fa1a175ccc3b88b245e799d70470e5d53430'}
    url = 'http://localhost:8000/api/v1/benchmark-result/'
    return(url, result_data, headers)


def main():
    url, result_data, headers = get_data()
    print "{0}: {1}".format(url, result_data)
    r = requests.post(url, data=json.dumps(result_data), headers=headers)
    print r


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = test_performance
import timeit
import urllib
import sys


SPEEDURL = 'http://localhost:8000/'

benchmarks = ['ai', 'django',  'spambayes', 'grid']


def test_overview():
    data = {
        "trend": 10,
        "baseline": 1,
        "revision": 73893,
        "executable": "1",
        "host": "bigdog",
    }
    params = urllib.urlencode(data)
    page = urllib.urlopen(SPEEDURL + 'overview/table/?' + params)
    jsonstring = page.read()
    page.close()
    if not '<table id="results" class="tablesorter">' in jsonstring:
        print "bad overview response"
        sys.exit(1)


def test_timeline(bench):
    data = {
        "executables": "1,2,6",
        "baseline": "true",
        "benchmark": bench,
        "host": "bigdog",
        "revisions": 200
    }
    params = urllib.urlencode(data)
    page = urllib.urlopen(SPEEDURL + 'timeline/json/?' + params)
    jsonstring = page.read()
    #print jsonstring
    page.close()
    if not '"lessisbetter": " (less is better)", "baseline":' in jsonstring \
        or not', "error": "None"}' in jsonstring:
        print "bad timeline response"
        sys.exit(1)

if __name__ == "__main__":
    t = timeit.Timer('test_overview()', 'from __main__ import test_overview')
    results = t.repeat(20, 1)
    print
    print "OVERVIEW RESULTS"
    print "min:", min(results)
    print "avg:", sum(results) / len(results)
    print
    print "TIMELINE RESULTS"
    for bench in benchmarks:
        t = timeit.Timer('test_timeline("' + bench + '")',
            'from __main__ import test_timeline')
        results = t.repeat(20, 1)
        print "benchmark =", bench
        print "min:", min(results)
        print "avg:", sum(results) / len(results)
    print

########NEW FILE########
