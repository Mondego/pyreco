__FILENAME__ = auth
from flask import session, request
from functools import wraps

from changes.models import User


NOT_SET = object()


def requires_auth(method):
    """
    Require an authenticated user on given method.

    Return a 401 Unauthorized status on failure.

    >>> @requires_admin
    >>> def post(self):
    >>>     # ...
    """
    @wraps(method)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return '', 401
        return method(*args, **kwargs)
    return wrapped


def requires_admin(method):
    """
    Require an authenticated user with admin privileges.

    Return a 401 Unauthorized if the user is not authenticated, or a
    403 Forbidden if the user is lacking permissions.

    >>> @requires_admin
    >>> def post(self):
    >>>     # ...
    """
    @wraps(method)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return '', 401
        if not user.is_admin:
            return '', 403
        return method(*args, **kwargs)
    return wrapped


def get_current_user():
    """
    Return the currently authenticated user based on their active session.
    """
    if getattr(request, 'current_user', NOT_SET) is NOT_SET:
        if session.get('uid') is None:
            request.gcurrent_user = None
        else:
            request.gcurrent_user = User.query.get(session['uid'])
            if request.gcurrent_user is None:
                del session['uid']
    return request.gcurrent_user

########NEW FILE########
__FILENAME__ = author_build_index
from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload
from uuid import UUID

from changes.api.base import APIView
from changes.api.auth import get_current_user
from changes.models import Author, Build


class AuthorBuildIndexAPIView(APIView):
    def _get_author(self, author_id):
        if author_id == 'me':
            user = get_current_user()
            if user is None:
                return None

            return Author.query.filter_by(email=user.email).first()
        try:
            author_id = UUID(author_id)
        except ValueError:
            return None
        return Author.query.get(author_id)

    def get(self, author_id):
        if author_id == 'me' and not get_current_user():
            return '', 401

        author = self._get_author(author_id)
        if not author:
            return '', 404

        queryset = Build.query.options(
            joinedload('project'),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).filter(
            Build.author_id == author.id,
        ).order_by(Build.date_created.desc(), Build.date_started.desc())

        return self.paginate(queryset)

    def get_stream_channels(self, author_id):
        author = self._get_author(author_id)
        if not author:
            return []
        return ['authors:{0}:builds'.format(author.id.hex)]

########NEW FILE########
__FILENAME__ = auth_index
from __future__ import absolute_import, division, unicode_literals

from flask import session

from changes.api.base import APIView


class AuthIndexAPIView(APIView):
    def get(self):
        """
        Return information on the currently authenticated user.
        """
        if session.get('uid'):
            context = {
                'authenticated': True,
                'user': {
                    'id': session['uid'],
                    'email': session['email'],
                },
            }
        else:
            context = {
                'authenticated': False,
            }

        return self.respond(context)

########NEW FILE########
__FILENAME__ = base
import json

from functools import wraps
from urllib import quote

from flask import Response, current_app, request
from flask.ext.restful import Resource

from changes.api.serializer import serialize as serialize_func
from changes.config import db

LINK_HEADER = '<{uri}&page={page}>; rel="{name}"'


def as_json(context):
    return json.dumps(serialize_func(context))


def param(key, validator=lambda x: x, required=True, dest=None):
    def wrapped(func):
        @wraps(func)
        def _wrapped(*args, **kwargs):
            if key in kwargs:
                value = kwargs.pop(key, '')
            elif request.method == 'POST':
                value = request.form.get(key) or ''
            else:
                value = ''

            dest_key = str(dest or key)

            value = value.strip()
            if not value:
                if required:
                    raise ParamError(key, 'value is required')
                return func(*args, **kwargs)

            try:
                value = validator(value)
            except ParamError:
                raise
            except Exception:
                raise ParamError(key, 'invalid value')

            kwargs[dest_key] = value

            return func(*args, **kwargs)

        return _wrapped
    return wrapped


class APIError(Exception):
    pass


class ParamError(APIError):
    def __init__(self, key, msg):
        self.key = key
        self.msg = msg

    def __unicode__(self):
        return '{0} is not valid: {1}'.format(self.key, self.msg)


class APIView(Resource):
    def dispatch_request(self, *args, **kwargs):
        response = super(APIView, self).dispatch_request(*args, **kwargs)
        db.session.commit()
        return response

    def paginate(self, queryset, max_per_page=100, **kwargs):
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 25) or 0)
        if max_per_page:
            assert per_page <= max_per_page
        assert page > 0

        if per_page:
            offset = (page - 1) * per_page
            result = list(queryset[offset:offset + per_page + 1])
        else:
            offset = 0
            page = 1
            result = list(queryset)

        links = []
        if page > 1:
            links.append(('previous', page - 1))
        if per_page and len(result) > per_page:
            links.append(('next', page + 1))
            result = result[:per_page]

        response = self.respond(result, **kwargs)

        querystring = u'&'.join(
            u'{0}={1}'.format(quote(k), quote(v))
            for k, v in request.args.iteritems()
            if k != 'page'
        )
        if querystring:
            base_url = '{0}?{1}'.format(request.base_url, querystring)
        else:
            base_url = request.base_url + '?'

        link_values = []
        for name, page_no in links:
            link_values.append(LINK_HEADER.format(
                uri=base_url,
                page=page_no,
                name=name,
            ))
        if link_values:
            response.headers['Link'] = ', '.join(link_values)
        return response

    def respond(self, context, status_code=200, serialize=True, serializers=None):
        if serialize:
            data = self.serialize(context, serializers)
        else:
            data = context

        return Response(
            as_json(data),
            mimetype='application/json',
            status=status_code)

    def serialize(self, *args, **kwargs):
        return serialize_func(*args, **kwargs)

    def as_json(self, context):
        return json.dumps(context)

    def get_backend(self, app=current_app):
        # TODO this should be automatic via a project
        from changes.backends.jenkins.builder import JenkinsBuilder
        return JenkinsBuilder(app=current_app, base_url=app.config['JENKINS_URL'])

########NEW FILE########
__FILENAME__ = build_cancel
from sqlalchemy.orm import joinedload, subqueryload_all

from changes.api.base import APIView
from changes.config import db
from changes.constants import Result, Status
from changes.models import Build, JobPlan, Plan


class BuildCancelAPIView(APIView):
    def post(self, build_id):
        build = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).get(build_id)
        if build is None:
            return '', 404

        if build.status == Status.finished:
            return '', 204

        cancelled = []

        # find any active/pending jobs
        for job in filter(lambda x: x.status != Status.finished, build.jobs):
            # TODO(dcramer): we make an assumption that there is a single step
            job_plan = JobPlan.query.options(
                subqueryload_all('plan.steps')
            ).filter(
                JobPlan.job_id == job.id,
            ).join(Plan).first()
            if not job_plan:
                continue

            try:
                step = job_plan.plan.steps[0]
            except IndexError:
                continue

            implementation = step.get_implementation()
            implementation.cancel(job=job)
            cancelled.append(job)

        if not cancelled:
            return '', 204

        build.status = Status.finished
        build.result = Result.aborted
        db.session.add(build)

        return self.respond(build)

########NEW FILE########
__FILENAME__ = build_comment_index
from flask import session
from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.config import db
from changes.models import Build, Comment, User


class BuildCommentIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('text', type=unicode, required=True)

    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        comments = list(Comment.query.filter(
            Comment.build == build,
        ).order_by(Comment.date_created.asc()))

        return self.respond(comments)

    def post(self, build_id):
        if not session.get('uid'):
            return '', 401

        user = User.query.get(session['uid'])
        if user is None:
            return '', 401

        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        args = self.parser.parse_args()

        # TODO(dcramer): ensure this comment wasnt just created
        comment = Comment(
            build=build,
            user=user,
            text=args.text,
        )
        db.session.add(comment)

        return self.respond(comment)

########NEW FILE########
__FILENAME__ = build_coverage
from changes.api.base import APIView

from changes.lib.coverage import get_coverage_by_build_id

from changes.models import Build


class BuildTestCoverageAPIView(APIView):
    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        coverage = {
            c.filename: c.data
            for c in get_coverage_by_build_id(build.id)
        }

        return self.respond(coverage)

########NEW FILE########
__FILENAME__ = build_coverage_stats
from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.lib.coverage import get_coverage_by_build_id
from changes.models import Build
from changes.utils.diff_parser import DiffParser


class BuildTestCoverageStatsAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('diff', action='store_true', default=False)

    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        args = self.parser.parse_args()

        results = get_coverage_by_build_id(build.id)

        if args.diff:
            diff = build.source.generate_diff()
            if not diff:
                return self.respond({})

            diff_parser = DiffParser(diff)
            parsed_diff = diff_parser.parse()

            files_in_diff = set(
                d['new_filename'][2:] for d in parsed_diff
                if d['new_filename']
            )

            results = [r for r in results if r.filename in files_in_diff]

        coverage = {
            c.filename: {
                'linesCovered': c.lines_covered,
                'linesUncovered': c.lines_uncovered,
                'diffLinesCovered': c.diff_lines_covered,
                'diffLinesUncovered': c.diff_lines_uncovered,
            }
            for c in results
        }

        return self.respond(coverage)

########NEW FILE########
__FILENAME__ = build_details
from __future__ import absolute_import

from collections import defaultdict
from sqlalchemy.orm import contains_eager, joinedload
from uuid import UUID

from changes.api.base import APIView
from changes.api.serializer.models.testcase import TestCaseWithOriginSerializer
from changes.config import db
from changes.constants import Result, Status, NUM_PREVIOUS_RUNS
from changes.models import Build, Source, Event, Job, TestCase, BuildSeen, User
from changes.utils.originfinder import find_failure_origins


def find_changed_tests(current_build, previous_build, limit=25):
    current_job_ids = [j.id.hex for j in current_build.jobs]
    previous_job_ids = [j.id.hex for j in previous_build.jobs]

    if not (current_job_ids and previous_job_ids):
        return []

    current_job_clause = ', '.join(
        ':c_job_id_%s' % i for i in range(len(current_job_ids))
    )
    previous_job_clause = ', '.join(
        ':p_job_id_%s' % i for i in range(len(previous_job_ids))
    )

    params = {}
    for idx, job_id in enumerate(current_job_ids):
        params['c_job_id_%s' % idx] = job_id
    for idx, job_id in enumerate(previous_job_ids):
        params['p_job_id_%s' % idx] = job_id

    # find all tests that have appeared in one job but not the other
    # we have to build this query up manually as sqlalchemy doesnt support
    # the FULL OUTER JOIN clause
    query = """
        SELECT c.id AS c_id,
               p.id AS p_id
        FROM (
            SELECT label_sha, id
            FROM test
            WHERE job_id IN (%(current_job_clause)s)
        ) as c
        FULL OUTER JOIN (
            SELECT label_sha, id
            FROM test
            WHERE job_id IN (%(previous_job_clause)s)
        ) as p
        ON c.label_sha = p.label_sha
        WHERE (c.id IS NULL OR p.id IS NULL)
    """ % {
        'current_job_clause': current_job_clause,
        'previous_job_clause': previous_job_clause
    }

    total = db.session.query(
        'count'
    ).from_statement(
        'SELECT COUNT(*) FROM (%s) as a' % (query,)
    ).params(**params).scalar()

    if not total:
        return {
            'total': 0,
            'changes': [],
        }

    results = db.session.query(
        'c_id', 'p_id'
    ).from_statement(
        '%s LIMIT %d' % (query, limit)
    ).params(**params)

    all_test_ids = set()
    for c_id, p_id in results:
        if c_id:
            all_test_ids.add(c_id)
        else:
            all_test_ids.add(p_id)

    test_map = dict(
        (t.id, t) for t in TestCase.query.filter(
            TestCase.id.in_(all_test_ids),
        ).options(
            joinedload('job', innerjoin=True),
        )
    )

    diff = []
    for c_id, p_id in results:
        if p_id:
            diff.append(('-', test_map[UUID(p_id)]))
        else:
            diff.append(('+', test_map[UUID(c_id)]))

    return {
        'total': total,
        'changes': sorted(diff, key=lambda x: (x[1].package, x[1].name)),
    }


class BuildDetailsAPIView(APIView):
    def get(self, build_id):
        build = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).get(build_id)
        if build is None:
            return '', 404

        previous_runs = Build.query.filter(
            Build.project == build.project,
            Build.date_created < build.date_created,
            Build.status == Status.finished,
            Build.id != build.id,
            Source.patch_id == None,  # NOQA
        ).join(
            Source, Build.source_id == Source.id,
        ).options(
            contains_eager('source').joinedload('revision'),
            joinedload('author'),
        ).order_by(Build.date_created.desc())[:NUM_PREVIOUS_RUNS]

        if previous_runs:
            most_recent_run = previous_runs[0]
        else:
            most_recent_run = None

        jobs = list(Job.query.filter(
            Job.build_id == build.id,
        ))

        # identify failures
        test_failures = TestCase.query.options(
            joinedload('job', innerjoin=True),
        ).filter(
            TestCase.job_id.in_([j.id for j in jobs]),
            TestCase.result == Result.failed,
        ).order_by(TestCase.name.asc())
        num_test_failures = test_failures.count()
        test_failures = test_failures[:25]

        failures_by_job = defaultdict(list)
        for failure in test_failures:
            failures_by_job[failure.job].append(failure)

        failure_origins = find_failure_origins(
            build, test_failures)
        for test_failure in test_failures:
            test_failure.origin = failure_origins.get(test_failure)

        # identify added/removed tests
        if most_recent_run and build.status == Status.finished:
            changed_tests = find_changed_tests(build, most_recent_run)
        else:
            changed_tests = []

        seen_by = list(User.query.join(
            BuildSeen, BuildSeen.user_id == User.id,
        ).filter(
            BuildSeen.build_id == build.id,
        ))

        extended_serializers = {
            TestCase: TestCaseWithOriginSerializer(),
        }

        event_list = list(Event.query.filter(
            Event.item_id == build.id,
        ).order_by(Event.date_created.desc()))

        context = self.serialize(build)
        context.update({
            'jobs': jobs,
            'previousRuns': previous_runs,
            'seenBy': seen_by,
            'events': event_list,
            'testFailures': {
                'total': num_test_failures,
                'tests': self.serialize(test_failures, extended_serializers),
            },
            'testChanges': self.serialize(changed_tests, extended_serializers),
        })

        return self.respond(context)

    def get_stream_channels(self, build_id):
        return [
            'builds:{0}'.format(build_id),
            'builds:{0}:jobs'.format(build_id),
        ]

########NEW FILE########
__FILENAME__ = build_index
from __future__ import absolute_import, division, unicode_literals

import json
import logging

from cStringIO import StringIO
from flask.ext.restful import reqparse
from sqlalchemy.orm import joinedload, subqueryload_all
from werkzeug.datastructures import FileStorage

from changes.api.base import APIView
from changes.api.validators.author import AuthorValidator
from changes.config import db
from changes.constants import Status, ProjectStatus
from changes.db.utils import get_or_create
from changes.jobs.create_job import create_job
from changes.jobs.sync_build import sync_build
from changes.models import (
    Project, Build, Job, JobPlan, Repository, Patch, ProjectOption,
    ItemOption, Source, ProjectPlan, Revision
)


def identify_revision(repository, treeish):
    """
    Attempt to transform a a commit-like reference into a valid revision.
    """
    # try to find it from the database first
    if len(treeish) == 40:
        revision = Revision.query.filter(Revision.sha == treeish).first()
        if revision:
            return revision

    vcs = repository.get_vcs()
    if not vcs:
        return

    try:
        commit = list(vcs.log(parent=treeish, limit=1))[0]
    except IndexError:
        # fall back to HEAD/tip when a matching revision isn't found
        # this case happens frequently with gateways like hg-git
        # TODO(dcramer): it's possible to DOS the endpoint by passing invalid
        # commits so we should really cache the failed lookups
        try:
            commit = list(vcs.log(limit=1))[0]
        except Exception:
            logging.exception('Failed to find commit: %s', treeish)
            return
    except Exception:
        logging.exception('Failed to find commit: %s', treeish)
        return

    revision, _ = commit.save(repository)

    return revision


def create_build(project, label, target, message, author, change=None,
                 patch=None, cause=None, source=None, sha=None,
                 source_data=None):
    assert sha or source

    repository = project.repository

    if source is None:
        source, _ = get_or_create(Source, where={
            'repository': repository,
            'patch': patch,
            'revision_sha': sha,
            'data': source_data or {},
        })

    build = Build(
        project=project,
        project_id=project.id,
        source=source,
        source_id=source.id if source else None,
        status=Status.queued,
        author=author,
        author_id=author.id if author else None,
        label=label,
        target=target,
        message=message,
        cause=cause,
    )

    db.session.add(build)
    db.session.commit()

    execute_build(build=build)

    return build


def execute_build(build):
    # TODO(dcramer): most of this should be abstracted into sync_build as if it
    # were a "im on step 0, create step 1"
    project = build.project

    jobs = []
    for plan in project.plans:
        job = Job(
            build=build,
            build_id=build.id,
            project=project,
            project_id=project.id,
            source=build.source,
            source_id=build.source_id,
            status=build.status,
            label=plan.label,
        )

        db.session.add(job)

        jobplan = JobPlan(
            project=project,
            job=job,
            build=build,
            plan=plan,
        )

        db.session.add(jobplan)

        jobs.append(job)

    db.session.commit()

    for job in jobs:
        create_job.delay(
            job_id=job.id.hex,
            task_id=job.id.hex,
            parent_task_id=job.build_id.hex,
        )

    db.session.commit()

    sync_build.delay(
        build_id=job.build_id.hex,
        task_id=job.build_id.hex,
    )

    return build


class BuildIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('sha', type=str, required=True)
    parser.add_argument('project', type=lambda x: Project.query.filter(
        Project.slug == x,
        Project.status == ProjectStatus.active,
    ).first())
    parser.add_argument('repository', type=lambda x: Repository.query.filter_by(url=x).first())
    parser.add_argument('author', type=AuthorValidator())
    parser.add_argument('label', type=unicode)
    parser.add_argument('target', type=unicode)
    parser.add_argument('message', type=unicode)
    parser.add_argument('patch', type=FileStorage, dest='patch_file', location='files')
    parser.add_argument('patch[data]', type=unicode, dest='patch_data')

    def get(self):
        queryset = Build.query.options(
            joinedload('project'),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).order_by(Build.date_created.desc(), Build.date_started.desc())

        return self.paginate(queryset)

    def post(self):
        args = self.parser.parse_args()

        if not (args.project or args.repository):
            return '{"error": "Need project or repository"}', 400

        if args.patch_data:
            try:
                patch_data = json.loads(args.patch_data)
            except Exception:
                return '{"error": "Invalid patch data (must be JSON dict)"}', 400

            if not isinstance(patch_data, dict):
                return '{"error": "Invalid patch data (must be JSON dict)"}', 400
        else:
            patch_data = None

        if args.project:
            projects = [args.project]
            repository = Repository.query.get(args.project.repository_id)
        else:
            repository = args.repository
            projects = list(Project.query.options(
                subqueryload_all(Project.project_plans, ProjectPlan.plan),
            ).filter(
                Project.status == ProjectStatus.active,
                Project.repository_id == repository.id,
            ))

        if not projects:
            return '{"error": "Unable to find project(s)."}', 400

        if args.patch_file:
            # eliminate projects without diff builds
            options = dict(
                db.session.query(
                    ProjectOption.project_id, ProjectOption.value
                ).filter(
                    ProjectOption.project_id.in_([p.id for p in projects]),
                    ProjectOption.name.in_([
                        'build.allow-patches',
                    ])
                )
            )

            projects = [
                p for p in projects
                if options.get(p.id, '1') == '1'
            ]

            if not projects:
                return self.respond([])

        label = args.label
        author = args.author
        message = args.message

        revision = identify_revision(repository, args.sha)
        if revision:
            if not author:
                author = revision.author
            if not label:
                label = revision.subject
            # only default the message if its absolutely not set
            if message is None:
                message = revision.message
            sha = revision.sha
        else:
            sha = args.sha

        if not args.target:
            target = sha[:12]
        else:
            target = args.target[:128]

        if not label:
            if message:
                label = message.splitlines()[0]
            if not label:
                label = 'A homeless build'
        label = label[:128]

        if args.patch_file:
            fp = StringIO()
            for line in args.patch_file:
                fp.write(line)
            patch_file = fp
        else:
            patch_file = None

        builds = []
        for project in projects:
            plan_list = list(project.plans)
            if not plan_list:
                logging.warning('No plans defined for project %s', project.slug)
                continue

            if plan_list and patch_file:
                options = dict(
                    db.session.query(
                        ItemOption.item_id, ItemOption.value
                    ).filter(
                        ItemOption.item_id.in_([p.id for p in plan_list]),
                        ItemOption.name.in_([
                            'build.allow-patches',
                        ])
                    )
                )
                plan_list = [
                    p for p in plan_list
                    if options.get(p.id, '1') == '1'
                ]

                # no plans remained
                if not plan_list:
                    continue

            if patch_file:
                patch = Patch(
                    repository=repository,
                    project=project,
                    parent_revision_sha=args.sha,
                    diff=patch_file.getvalue(),
                )
                db.session.add(patch)
            else:
                patch = None

            builds.append(create_build(
                project=project,
                sha=sha,
                target=target,
                label=label,
                message=message,
                author=author,
                patch=patch,
                source_data=patch_data,
            ))

        return self.respond(builds)

    def get_stream_channels(self):
        return ['builds:*']

########NEW FILE########
__FILENAME__ = build_mark_seen
from flask import session

from changes.api.base import APIView
from changes.db.utils import try_create
from changes.models import Build, BuildSeen


class BuildMarkSeenAPIView(APIView):
    def post(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        if not session.get('uid'):
            return '', 401

        try_create(BuildSeen, where={
            'build_id': build.id,
            'user_id': session['uid'],
        })

        return '', 200

########NEW FILE########
__FILENAME__ = build_restart
from sqlalchemy.orm import joinedload

from datetime import datetime

from changes.api.base import APIView
from changes.api.build_index import execute_build
from changes.config import db
from changes.constants import Result, Status
from changes.models import Build, Job, JobStep, ItemStat


class BuildRestartAPIView(APIView):
    def post(self, build_id):
        build = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).get(build_id)
        if build is None:
            return '', 404

        if build.status != Status.finished:
            return '', 400

        # ItemStat doesnt cascade by itself
        stat_ids = [build.id]
        job_ids = [
            j[0] for j in
            db.session.query(Job.id).filter(Job.build_id == build.id)
        ]
        if job_ids:
            step_ids = [
                s[0] for s in
                db.session.query(JobStep.id).filter(JobStep.job_id.in_(job_ids))
            ]
            stat_ids.extend(job_ids)
            stat_ids.extend(step_ids)

        if stat_ids:
            ItemStat.query.filter(
                ItemStat.item_id.in_(stat_ids),
            ).delete(synchronize_session=False)

        # remove any existing job data
        # TODO(dcramer): this is potentially fairly slow with cascades
        Job.query.filter(
            Job.build_id == build.id
        ).delete(synchronize_session=False)

        build.date_started = datetime.utcnow()
        build.date_modified = build.date_started
        build.date_finished = None
        build.duration = None
        build.status = Status.queued
        build.result = Result.unknown
        db.session.add(build)

        execute_build(build=build)

        return self.respond(build)

########NEW FILE########
__FILENAME__ = build_retry
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.build_index import create_build
from changes.constants import Cause
from changes.models import Build


class BuildRetryAPIView(APIView):
    def post(self, build_id):
        build = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).get(build_id)
        if build is None:
            return '', 404

        new_build = create_build(
            project=build.project,
            label=build.label,
            target=build.target,
            message=build.message,
            author=build.author,
            source=build.source,
            cause=Cause.retry,
        )

        return '', 302, {'Location': '/api/0/builds/{0}/'.format(new_build.id.hex)}

########NEW FILE########
__FILENAME__ = build_test_index
from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse
from sqlalchemy.orm import contains_eager
from sqlalchemy.sql import func

from changes.api.base import APIView
from changes.models import Build, TestCase, Job


SORT_CHOICES = (
    'duration',
    'name',
    'retries'
)


class BuildTestIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('query', type=unicode, location='args')
    parser.add_argument('sort', type=unicode, location='args',
                        choices=SORT_CHOICES, default='duration')

    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        args = self.parser.parse_args()

        test_list = TestCase.query.options(
            contains_eager('job')
        ).join(
            Job, TestCase.job_id == Job.id,
        ).filter(
            Job.build_id == build.id,
        )

        if args.query:
            test_list = test_list.filter(
                func.lower(TestCase.name).contains(args.query.lower()),
            )

        if args.sort == 'duration':
            sort_by = TestCase.duration.desc()
        elif args.sort == 'name':
            sort_by = TestCase.name.asc()
        elif args.sort == 'retries':
            sort_by = TestCase.reruns.desc()

        test_list = test_list.order_by(sort_by)

        return self.paginate(test_list, max_per_page=None)

########NEW FILE########
__FILENAME__ = build_test_index_counts
from sqlalchemy.orm import contains_eager

from changes.api.base import APIView
from changes.constants import Result
from changes.models import Build, TestCase, Job


class BuildTestIndexCountsAPIView(APIView):

    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        test_list = TestCase.query.options(
            contains_eager('job')
        ).join(
            Job, TestCase.job_id == Job.id,
        ).filter(
            Job.build_id == build.id,
        )

        count_dict = {result.name: 0 for result in Result}

        for test in test_list:
            count_dict[test.result.name] += 1

        return self.respond(count_dict)

########NEW FILE########
__FILENAME__ = build_test_index_failures
from sqlalchemy.orm import contains_eager

from changes.api.base import APIView
from changes.constants import Result
from changes.models import Build, TestCase, Job


class BuildTestIndexFailuresAPIView(APIView):

    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        test_list = TestCase.query.options(
            contains_eager('job')
        ).join(
            Job, TestCase.job_id == Job.id,
        ).filter(
            Job.build_id == build.id,
            TestCase.result != Result.passed,
        )

        result_list = []

        for test in test_list:
            test_info = dict()
            test_info['name'] = test.name
            test_info['result'] = test.result.name
            test_info['job_id'] = test.job_id
            test_info['test_id'] = test.id

            result_list.append(test_info)

        return self.respond(result_list)

########NEW FILE########
__FILENAME__ = change_details
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Change


class ChangeDetailsAPIView(APIView):
    def get(self, change_id):
        change = Change.query.options(
            joinedload(Change.project),
            joinedload(Change.author),
        ).get(change_id)

        return self.respond(change)

    def get_stream_channels(self, change_id):
        return ['changes:{0}'.format(change_id)]

########NEW FILE########
__FILENAME__ = change_index
from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.base import APIView, param
from changes.api.validators.author import AuthorValidator
from changes.config import db
from changes.models import Change, Job, Project, Repository


class ChangeIndexAPIView(APIView):
    def get(self):
        change_list = list(
            Change.query.options(
                joinedload(Change.project),
                joinedload(Change.author),
            ).order_by(Change.date_modified.desc())
        )[:100]

        # TODO(dcramer): denormalize this
        for change in change_list:
            try:
                change.last_job = Job.query.filter_by(
                    change=change,
                ).order_by(
                    Job.date_created.desc(),
                    Job.date_started.desc()
                )[0]
            except IndexError:
                change.last_job = None

        return self.paginate(change_list)

    @param('project', lambda x: Project.query.filter_by(slug=x)[0])
    @param('label')
    @param('key', required=False)
    @param('author', AuthorValidator(), required=False)
    @param('message', required=False)
    @param('date_created', required=False)
    @param('date_modified', required=False)
    def post(self, project, label, key=None, author=None, message=None,
             date_created=None, date_modified=None):
        repository = Repository.query.get(project.repository_id)

        change = Change(
            project=project,
            repository=repository,
            author=author,
            label=label,
        )
        db.session.add(change)

        return self.respond(change)

    def get_stream_channels(self):
        return ['changes:*']

########NEW FILE########
__FILENAME__ = client
import json

from flask import current_app


class APIError(Exception):
    pass


class APIClient(object):
    """
    An internal API client.

    >>> client = APIClient(version=0)
    >>> response = client.get('/projects/')
    >>> print response
    """
    def __init__(self, version):
        self.version = version

    def dispatch(self, url, method, data=None):
        url = '%s/api/%d/%s' % (current_app.config['BASE_URI'], self.version, url.lstrip('/'))
        with current_app.test_client() as client:
            response = client.open(path=url, method=method, data=data)
        if not (200 <= response.status_code < 300):
            raise APIError('Request returned invalid status code: %d' % (response.status_code,))
        if response.headers['Content-Type'] != 'application/json':
            raise APIError('Request returned invalid content type: %s' % (response.headers['Content-Type'],))
        # TODO(dcramer): ideally we wouldn't encode + decode this
        return json.loads(response.data)

    def delete(self, *args, **kwargs):
        return self.dispatch(method='DELETE', *args, **kwargs)

    def get(self, *args, **kwargs):
        return self.dispatch(method='GET', *args, **kwargs)

    def head(self, *args, **kwargs):
        return self.dispatch(method='HEAD', *args, **kwargs)

    def options(self, *args, **kwargs):
        return self.dispatch(method='OPTIONS', *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self.dispatch(method='PATCH', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.dispatch(method='POST', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self.dispatch(method='PUT', *args, **kwargs)

api_client = APIClient(version=0)

########NEW FILE########
__FILENAME__ = cluster_details
from __future__ import absolute_import

from changes.api.base import APIView
from changes.models import Cluster, Node


class ClusterDetailsAPIView(APIView):
    def get(self, cluster_id):
        cluster = Cluster.query.get(cluster_id)
        if cluster is None:
            return '', 404

        node_count = Node.query.filter(
            Node.clusters.contains(cluster),
        ).count()

        context = self.serialize(cluster)
        context['numNodes'] = node_count

        return self.respond(context, serialize=False)

########NEW FILE########
__FILENAME__ = cluster_index
from __future__ import absolute_import

from changes.api.base import APIView
from changes.models import Cluster


class ClusterIndexAPIView(APIView):
    def get(self):
        queryset = Cluster.query.order_by(Cluster.label.asc())

        return self.paginate(queryset)

########NEW FILE########
__FILENAME__ = cluster_nodes
from __future__ import absolute_import

from datetime import datetime, timedelta
from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.models import Cluster, JobStep, Node


class ClusterNodesAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('since', type=int, location='args')

    def get(self, cluster_id):
        cluster = Cluster.query.get(cluster_id)
        if cluster is None:
            return '', 404

        queryset = Node.query.filter(
            Node.clusters.contains(cluster),
        )

        args = self.parser.parse_args()
        if args.since:
            cutoff = datetime.utcnow() - timedelta(days=args.since)

            queryset = queryset.join(
                JobStep, JobStep.node_id == Node.id,
            ).filter(
                JobStep.date_created > cutoff,
            ).group_by(Node)

        return self.paginate(queryset)

########NEW FILE########
__FILENAME__ = controller
from flask.signals import got_request_exception
from flask.ext.restful import Api


class APIController(Api):
    def handle_error(self, e):
        """
        Almost identical to Flask-Restful's handle_error, but fixes some minor
        issues.

        Specifically, this fixes exceptions so they get propagated correctly
        when ``propagate_exceptions`` is set.
        """
        if not hasattr(e, 'code') and self.app.propagate_exceptions:
            got_request_exception.send(self.app, exception=e)
            raise

        return super(APIController, self).handle_error(e)

########NEW FILE########
__FILENAME__ = jobphase_index
from __future__ import absolute_import

from sqlalchemy.orm import joinedload, subqueryload_all

from changes.api.base import APIView
from changes.models import Job, JobPhase, JobStep


class JobPhaseIndexAPIView(APIView):
    def get(self, job_id):
        job = Job.query.options(
            subqueryload_all(Job.phases),
            joinedload('project', innerjoin=True),
        ).get(job_id)
        if job is None:
            return '', 404

        phase_list = list(JobPhase.query.options(
            subqueryload_all(JobPhase.steps, JobStep.node),
            subqueryload_all(JobPhase.steps, JobStep.logsources)
        ).filter(
            JobPhase.job_id == job.id,
        ).order_by(JobPhase.date_started.asc(), JobPhase.date_created.asc()))

        context = []
        for phase, phase_data in zip(phase_list, self.serialize(phase_list)):
            phase_data['steps'] = []
            for step, step_data in zip(phase.steps, self.serialize(list(phase.steps))):
                step_data['logSources'] = self.serialize(list(step.logsources))
                phase_data['steps'].append(step_data)
            context.append(phase_data)

        return self.respond(context, serialize=False)

    def get_stream_channels(self, job_id):
        return [
            'jobs:{0}'.format(job_id),
            'testgroups:{0}:*'.format(job_id),
            'logsources:{0}:*'.format(job_id),
        ]

########NEW FILE########
__FILENAME__ = job_details
from __future__ import absolute_import

from sqlalchemy.orm import joinedload, subqueryload_all

from changes.api.base import APIView
from changes.api.serializer.models.testcase import TestCaseWithOriginSerializer
from changes.constants import Result, Status, NUM_PREVIOUS_RUNS
from changes.models import Job, TestCase, LogSource
from changes.utils.originfinder import find_failure_origins


class JobDetailsAPIView(APIView):
    def get(self, job_id):
        job = Job.query.options(
            subqueryload_all(Job.phases),
            joinedload('project', innerjoin=True),
        ).get(job_id)
        if job is None:
            return '', 404

        previous_runs = Job.query.filter(
            Job.project == job.project,
            Job.date_created < job.date_created,
            Job.status == Status.finished,
            Job.id != job.id,
        ).order_by(Job.date_created.desc())[:NUM_PREVIOUS_RUNS]

        test_failures = TestCase.query.filter(
            TestCase.job_id == job.id,
            TestCase.result == Result.failed,
        ).order_by(TestCase.name.asc())
        num_test_failures = test_failures.count()
        test_failures = test_failures[:25]

        if test_failures:
            failure_origins = find_failure_origins(
                job, test_failures)
            for test_failure in test_failures:
                test_failure.origin = failure_origins.get(test_failure)

        extended_serializers = {
            TestCase: TestCaseWithOriginSerializer(),
        }

        log_sources = list(LogSource.query.options(
            joinedload('step'),
        ).filter(
            LogSource.job_id == job.id,
        ).order_by(LogSource.date_created.asc()))

        context = self.serialize(job)
        context.update({
            'phases': job.phases,
            'testFailures': {
                'total': num_test_failures,
                'tests': self.serialize(test_failures, extended_serializers),
            },
            'logs': log_sources,
            'previousRuns': previous_runs,
        })

        return self.respond(context)

    def get_stream_channels(self, job_id):
        return [
            'jobs:{0}'.format(job_id),
            'testgroups:{0}:*'.format(job_id),
            'logsources:{0}:*'.format(job_id),
        ]

########NEW FILE########
__FILENAME__ = job_log_details
from __future__ import absolute_import, division, unicode_literals

from flask import Response, request

from changes.api.base import APIView
from changes.models import LogSource, LogChunk


LOG_BATCH_SIZE = 50000  # in length of chars


class JobLogDetailsAPIView(APIView):
    def get(self, job_id, source_id):
        """
        Return chunks for a LogSource.
        """
        source = LogSource.query.get(source_id)
        if source is None or source.job_id != job_id:
            return '', 404

        offset = int(request.args.get('offset', -1))
        limit = int(request.args.get('limit', LOG_BATCH_SIZE))

        queryset = LogChunk.query.filter(
            LogChunk.source_id == source.id,
        ).order_by(LogChunk.offset.desc())

        if offset == -1:
            # starting from the end so we need to know total size
            tail = queryset.limit(1).first()

            if tail is None:
                logchunks = []
            else:
                if limit:
                    queryset = queryset.filter(
                        (LogChunk.offset + LogChunk.size) >= max(tail.offset + tail.size - limit, 0),
                    )
                logchunks = list(queryset)
        else:
            queryset = queryset.filter(
                (LogChunk.offset + LogChunk.size) >= offset,
            )
            if limit:
                queryset = queryset.filter(
                    LogChunk.offset <= offset + limit,
                )
            logchunks = list(queryset)

        logchunks.sort(key=lambda x: x.date_created)

        if logchunks:
            next_offset = logchunks[-1].offset + logchunks[-1].size
        else:
            next_offset = 0

        context = self.serialize({
            'source': source,
            'chunks': logchunks,
            'nextOffset': next_offset,
        })
        context['source']['step'] = self.serialize(source.step)

        return self.respond(context, serialize=False)

    def get_stream_channels(self, job_id, source_id):
        source = LogSource.query.get(source_id)
        if source is None or source.job_id != job_id:
            return Response(status=404)

        return ['logsources:{0}:{1}'.format(job_id, source.id.hex)]

########NEW FILE########
__FILENAME__ = node_details
from __future__ import absolute_import

from changes.api.base import APIView
from changes.models import Node


class NodeDetailsAPIView(APIView):
    def get(self, node_id):
        node = Node.query.get(node_id)
        if node is None:
            return '', 404

        context = self.serialize(node)
        context['clusters'] = self.serialize(list(node.clusters))

        return self.respond(context, serialize=False)

########NEW FILE########
__FILENAME__ = node_index
from __future__ import absolute_import

from datetime import datetime, timedelta
from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.models import Node, JobStep


class NodeIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('since', type=int, location='args')

    def get(self):
        args = self.parser.parse_args()
        if args.since:
            cutoff = datetime.utcnow() - timedelta(days=args.since)

            queryset = Node.query.join(
                JobStep, JobStep.node_id == Node.id,
            ).filter(
                JobStep.date_created > cutoff,
            ).group_by(Node)
        else:
            queryset = Node.query

        queryset = queryset.order_by(Node.label.asc())

        return self.paginate(queryset)

########NEW FILE########
__FILENAME__ = node_job_index
from __future__ import absolute_import

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.serializer.models.job import JobWithBuildSerializer
from changes.models import Job, JobStep, Node


class NodeJobIndexAPIView(APIView):
    def get(self, node_id):
        node = Node.query.get(node_id)
        if node is None:
            return '', 404

        jobs = Job.query.join(
            JobStep, JobStep.job_id == Job.id,
        ).options(
            joinedload(Job.build, innerjoin=True),
        ).filter(
            JobStep.node_id == node.id,
        ).order_by(Job.date_created.desc())

        return self.paginate(jobs, serializers={
            Job: JobWithBuildSerializer(),
        })

########NEW FILE########
__FILENAME__ = patch_details
from __future__ import absolute_import

from flask import request, Response

from changes.api.base import APIView
from changes.models import Patch


class PatchDetailsAPIView(APIView):
    def get(self, patch_id):
        patch = Patch.query.get(patch_id)
        if patch is None:
            return '', 404

        if request.args.get('raw'):
            return Response(patch.diff, mimetype='text/plain')

        return self.respond(patch)

########NEW FILE########
__FILENAME__ = plan_details
from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.models import Plan


class PlanDetailsAPIView(APIView):
    def get(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return '', 404

        context = self.serialize(plan)
        context['projects'] = list(plan.projects)
        context['steps'] = list(plan.steps)

        return self.respond(context)

########NEW FILE########
__FILENAME__ = plan_index
from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.auth import requires_admin
from changes.api.base import APIView
from changes.config import db
from changes.models import Plan


class PlanIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('name', required=True)

    def get(self):
        queryset = Plan.query.order_by(Plan.label.asc())
        return self.paginate(queryset)

    @requires_admin
    def post(self):
        args = self.parser.parse_args()

        plan = Plan(label=args.name)
        db.session.add(plan)

        return self.respond(plan)

########NEW FILE########
__FILENAME__ = plan_project_index
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime
from flask.ext.restful import reqparse

from changes.api.auth import requires_admin
from changes.api.base import APIView
from changes.config import db
from changes.models import Plan, Project


class PlanProjectIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('id', required=True)

    def get(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return '', 404

        return self.respond(list(plan.projects))

    @requires_admin
    def post(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return '', 404

        args = self.parser.parse_args()

        project = Project.query.filter(Project.slug == args.id).first()
        if project is None:
            project = Project.query.get(args.id)
            if project is None:
                return '', 400

        plan.projects.append(project)

        plan.date_modified = datetime.utcnow()
        db.session.add(plan)

        db.session.commit()

        return self.respond(project)

    @requires_admin
    def delete(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return '', 404

        args = self.parser.parse_args()

        project = Project.query.filter(Project.slug == args.id).first()
        if project is None:
            project = Project.query.get(args.id)
            if project is None:
                return '', 400

        plan.projects.remove(project)

        plan.date_modified = datetime.utcnow()
        db.session.add(plan)

        db.session.commit()

        return '', 200

########NEW FILE########
__FILENAME__ = plan_step_index
from __future__ import absolute_import, division, unicode_literals

import json

from flask.ext.restful import reqparse

from changes.api.auth import requires_admin
from changes.api.base import APIView
from changes.config import db
from changes.constants import IMPLEMENTATION_CHOICES
from changes.models import Step, Plan


class PlanStepIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('data', default='{}')
    parser.add_argument('implementation', choices=IMPLEMENTATION_CHOICES,
                        required=True)
    parser.add_argument('order', type=int, default=0)

    def get(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return {"message": "plan not found"}, 404

        return self.respond(list(plan.steps))

    @requires_admin
    def post(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return {"message": "plan not found"}, 404

        args = self.parser.parse_args()

        step = Step(
            plan=plan,
            order=args.order,
            implementation=args.implementation,
        )

        data = json.loads(args.data)
        if not isinstance(data, dict):
            return {"message": "data must be a JSON mapping"}, 400

        impl_cls = step.get_implementation(load=False)
        if impl_cls is None:
            return {"message": "unable to load build step implementation"}, 400

        try:
            impl_cls(**data)
        except Exception:
            return {"message": "unable to create build step provided data"}, 400

        step.data = data
        step.order = args.order
        db.session.add(step)

        plan.date_modified = step.date_modified
        db.session.add(plan)

        db.session.commit()

        return self.serialize(step), 201

########NEW FILE########
__FILENAME__ = project_build_index
from __future__ import absolute_import, division, unicode_literals

from flask import Response, request
from sqlalchemy.orm import contains_eager, joinedload

from changes.api.base import APIView
from changes.models import Project, Source, Build


class ProjectBuildIndexAPIView(APIView):
    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        include_patches = request.args.get('include_patches') or '1'

        queryset = Build.query.options(
            joinedload('project'),
            joinedload('author'),
            contains_eager('source').joinedload('revision'),
        ).join(
            Source, Source.id == Build.source_id,
        ).filter(
            Build.project_id == project.id,
        ).order_by(Build.date_created.desc())

        if include_patches == '0':
            queryset = queryset.filter(
                Source.patch_id == None,  # NOQA
            )

        return self.paginate(queryset)

    def get_stream_channels(self, project_id=None):
        project = Project.get(project_id)
        if not project:
            return Response(status=404)
        return ['projects:{0}:builds'.format(project.id.hex)]

########NEW FILE########
__FILENAME__ = project_build_search
from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.constants import Result
from changes.models import Project, Build


class ProjectBuildSearchAPIView(APIView):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('query', type=unicode, location='args')
    get_parser.add_argument('source', type=unicode, location='args')
    get_parser.add_argument('result', type=unicode, location='args',
                            choices=('failed', 'passed', 'aborted', 'unknown'))

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        args = self.get_parser.parse_args()

        filters = []

        if args.source:
            filters.append(Build.target.startswith(args.source))

        if args.query:
            filters.append(or_(
                Build.label.contains(args.query),
                Build.target.startswith(args.query),
            ))

        if args.result:
            filters.append(Build.result == Result[args.result])

        queryset = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).filter(
            Build.project_id == project.id,
            *filters
        ).order_by(Build.date_created.desc())

        return self.paginate(queryset)

########NEW FILE########
__FILENAME__ = project_commit_details
from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload, contains_eager

from changes.api.base import APIView
from changes.models import Build, Project, Revision, Source


class ProjectCommitDetailsAPIView(APIView):
    def get(self, project_id, commit_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        repo = project.repository
        revision = Revision.query.filter(
            Revision.repository_id == repo.id,
            Revision.sha == commit_id,
        ).join(Revision.author).first()
        if not revision:
            return '', 404

        build_list = list(Build.query.options(
            joinedload('author'),
            contains_eager('source').joinedload('revision'),
        ).join(
            Source, Build.source_id == Source.id,
        ).filter(
            Build.project_id == project.id,
            Source.revision_sha == revision.sha,
            Source.patch == None,  # NOQA
        ).order_by(Build.date_created.desc()))[:100]

        context = self.serialize(revision)

        context.update({
            'repository': repo,
            'builds': build_list,
        })

        return self.respond(context)

    def get_stream_channels(self, project_id, commit_id):
        return [
            'revisions:{0}:*'.format(commit_id),
        ]

########NEW FILE########
__FILENAME__ = project_commit_index
from __future__ import absolute_import, division, unicode_literals

import itertools

from sqlalchemy.orm import joinedload, contains_eager

from changes.api.base import APIView
from changes.constants import Status
from changes.models import Build, Project, Revision, Source


COMMITS_PER_PAGE = 50


class ProjectCommitIndexAPIView(APIView):
    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        repo = project.repository
        vcs = repo.get_vcs()

        if vcs:
            vcs_log = list(vcs.log(limit=COMMITS_PER_PAGE))

            if vcs_log:
                revisions_qs = list(Revision.query.options(
                    joinedload('author'),
                ).filter(
                    Revision.repository_id == repo.id,
                    Revision.sha.in_(c.id for c in vcs_log)
                ))

                revisions_map = dict(
                    (c.sha, d)
                    for c, d in itertools.izip(revisions_qs, self.serialize(revisions_qs))
                )

                commits = []
                for commit in vcs_log:
                    if commit.id in revisions_map:
                        result = revisions_map[commit.id]
                    else:
                        result = self.serialize(commit)
                    commits.append(result)
            else:
                commits = []
        else:
            commits = self.serialize(list(
                Revision.query.options(
                    joinedload('author'),
                ).filter(
                    Revision.repository_id == repo.id,
                ).order_by(Revision.date_created.desc())[:COMMITS_PER_PAGE]
            ))

        if commits:
            builds_qs = list(Build.query.options(
                joinedload('author'),
                contains_eager('source'),
            ).join(
                Source, Source.id == Build.source_id,
            ).filter(
                Build.source_id == Source.id,
                Build.project_id == project.id,
                Build.status.in_([Status.finished, Status.in_progress, Status.queued]),
                Source.revision_sha.in_(c['id'] for c in commits),
                Source.patch == None,  # NOQA
            ).order_by(Build.date_created.asc()))

            builds_map = dict(
                (b.source.revision_sha, d)
                for b, d in itertools.izip(builds_qs, self.serialize(builds_qs))
            )
        else:
            builds_map = {}

        results = []
        for result in commits:
            result['build'] = builds_map.get(result['id'])
            results.append(result)

        return self.respond(results)

########NEW FILE########
__FILENAME__ = project_coverage_group_index
from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.config import db
from changes.constants import Result, Status
from changes.models import Build, Job, FileCoverage, Project, Source
from changes.utils.trees import build_tree


SORT_CHOICES = (
    'lines_covered',
    'lines_uncovered',
    'name',
)


class ProjectCoverageGroupIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('parent', type=unicode, location='args')

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        args = self.parser.parse_args()

        latest_build = Build.query.join(
            Source, Source.id == Build.source_id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Build.project_id == project.id,
            Build.result == Result.passed,
            Build.status == Status.finished,
        ).order_by(
            Build.date_created.desc(),
        ).limit(1).first()

        if not latest_build:
            return self.respond([])

        # use the most recent coverage
        cover_list = FileCoverage.query.filter(
            FileCoverage.job_id.in_(
                db.session.query(Job.id).filter(
                    Job.build_id == latest_build.id,
                )
            )
        )

        if args.parent:
            cover_list = cover_list.filter(
                FileCoverage.filename.startswith(args.parent),
            )

        cover_list = list(cover_list)

        groups = build_tree(
            [c.filename for c in cover_list],
            sep='/',
            min_children=2,
            parent=args.parent,
        )

        results = []
        for group in groups:
            num_files = 0
            total_lines_covered = 0
            total_lines_uncovered = 0
            for file_coverage in cover_list:
                filename = file_coverage.filename
                if filename == group or filename.startswith(group + '/'):
                    num_files += 1
                    total_lines_covered += file_coverage.lines_covered
                    total_lines_uncovered += file_coverage.lines_uncovered

            if args.parent:
                filename = group[len(args.parent) + len('/'):]
            else:
                filename = group

            data = {
                'filename': filename,
                'path': group,
                'totalLinesCovered': total_lines_covered,
                'totalLinesUncovered': total_lines_uncovered,
                'numFiles': num_files,
            }
            results.append(data)
        results.sort(key=lambda x: x['totalLinesUncovered'], reverse=True)

        trail = []
        context = []
        if args.parent:
            for chunk in args.parent.split('/'):
                context.append(chunk)
                trail.append({
                    'path': '/'.join(context),
                    'name': chunk,
                })

        data = {
            'groups': results,
            'trail': trail,
        }

        return self.respond(data, serialize=False)

########NEW FILE########
__FILENAME__ = project_coverage_index
from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.constants import Result, Status
from changes.models import Build, Job, FileCoverage, Project, Source

SORT_CHOICES = (
    'lines_covered',
    'lines_uncovered',
    'name',
)


class ProjectCoverageIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('query', type=unicode, location='args')
    parser.add_argument('sort', type=unicode, location='args',
                        choices=SORT_CHOICES, default='name')

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        args = self.parser.parse_args()

        latest_build = Build.query.join(
            Source, Source.id == Build.source_id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Build.project_id == project.id,
            Build.result == Result.passed,
            Build.status == Status.finished,
        ).order_by(
            Build.date_created.desc(),
        ).limit(1).first()

        if not latest_build:
            return self.respond([])

        # use the most recent coverage
        cover_list = FileCoverage.query.filter(
            FileCoverage.job_id.in_(
                Job.query.filter(Job.build_id == latest_build.id)
            )
        )

        if args.query:
            cover_list = cover_list.filter(
                FileCoverage.filename.startswith(args.query),
            )

        if args.sort == 'lines_covered':
            sort_by = FileCoverage.lines_covered.desc()
        elif args.sort == 'lines_covered':
            sort_by = FileCoverage.lines_uncovered.desc()
        elif args.sort == 'name':
            sort_by = FileCoverage.name.asc()

        cover_list = cover_list.order_by(sort_by)

        return self.paginate(cover_list)

########NEW FILE########
__FILENAME__ = project_details
from flask import request
from sqlalchemy.orm import contains_eager, joinedload, subqueryload_all

from changes.api.base import APIView
from changes.config import db
from changes.models import (
    Project, Plan, Build, Source, Status, Result, ProjectOption
)


class ValidationError(Exception):
    pass


class Validator(object):
    fields = ()

    def __init__(self, data=None, initial=None):
        self.data = data or {}
        self.initial = initial or {}

    def clean(self):
        result = {}
        for name in self.fields:
            value = self.data.get(name, self.initial.get(name))
            if isinstance(value, basestring):
                value = value.strip()
            result[name] = value

        for key, value in result.iteritems():
            if not value:
                raise ValidationError('%s is required' % (key,))

        return result

OPTION_DEFAULTS = {
    'green-build.notify': '0',
    'green-build.project': '',
    'mail.notify-author': '1',
    'mail.notify-addresses': '',
    'mail.notify-addresses-revisions': '',
    'build.allow-patches': '1',
    'build.commit-trigger': '1',
    'ui.show-coverage': '1',
    'ui.show-tests': '1',
}


class ProjectValidator(Validator):
    fields = (
        'name',
        'slug',
    )


class ProjectDetailsAPIView(APIView):
    def get(self, project_id):
        project = Project.get(project_id)
        if project is None:
            return '', 404

        plans = Plan.query.options(
            subqueryload_all(Plan.steps),
        ).filter(
            Plan.projects.contains(project),
        )

        last_build = Build.query.options(
            joinedload('author'),
            contains_eager('source')
        ).join(
            Source, Build.source_id == Source.id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Build.project == project,
            Build.status == Status.finished,
        ).order_by(
            Build.date_created.desc(),
        ).first()
        if not last_build or last_build.result == Result.passed:
            last_passing_build = last_build
        else:
            last_passing_build = Build.query.options(
                joinedload('author'),
                contains_eager('source')
            ).join(
                Source, Build.source_id == Source.id,
            ).filter(
                Source.patch_id == None,  # NOQA
                Build.project == project,
                Build.result == Result.passed,
                Build.status == Status.finished,
            ).order_by(
                Build.date_created.desc(),
            ).first()

        options = dict(
            (o.name, o.value) for o in ProjectOption.query.filter(
                ProjectOption.project_id == project.id,
            )
        )
        for key, value in OPTION_DEFAULTS.iteritems():
            options.setdefault(key, value)

        data = self.serialize(project)
        data['lastBuild'] = last_build
        data['lastPassingBuild'] = last_passing_build
        data['repository'] = project.repository
        data['plans'] = list(plans)
        data['options'] = options

        return self.respond(data)

    def post(self, project_id):
        project = Project.get(project_id)
        if project is None:
            return '', 404

        validator = ProjectValidator(
            data=request.form,
            initial={
                'name': project.name,
                'slug': project.slug,
            },
        )
        try:
            result = validator.clean()
        except ValidationError:
            return '', 400

        project.name = result['name']
        project.slug = result['slug']
        db.session.add(project)

        return self.respond(project)

########NEW FILE########
__FILENAME__ = project_index
from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.auth import requires_auth
from changes.config import db
from changes.constants import Result, Status, ProjectStatus
from changes.models import Project, Repository, Build, Source


def get_latest_builds_query(project_list, result=None):
    build_query = db.session.query(
        Build.id,
    ).join(
        Source, Build.source_id == Source.id,
    ).filter(
        Source.patch_id == None,  # NOQA
        Build.status == Status.finished,
    ).order_by(
        Build.date_created.desc(),
    )

    if result:
        build_query = build_query.filter(
            Build.result == result,
        )

    # TODO(dcramer): we dont actually need the project table here
    build_map = dict(db.session.query(
        Project.id,
        build_query.filter(
            Build.project_id == Project.id,
        ).limit(1).as_scalar(),
    ).filter(
        Project.id.in_(p.id for p in project_list),
    ))

    return list(Build.query.filter(
        Build.id.in_(build_map.values()),
    ).options(
        joinedload('author'),
        joinedload('source').joinedload('revision'),
    ))


class ProjectIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('name', type=unicode, required=True)
    parser.add_argument('slug', type=str)
    parser.add_argument('repository', type=unicode, required=True)

    def get(self):
        queryset = Project.query.filter(
            Project.status == ProjectStatus.active,
        ).order_by(Project.name.asc())

        project_list = list(queryset)

        context = []

        latest_build_results = get_latest_builds_query(project_list)
        latest_build_map = dict(
            zip([b.project_id for b in latest_build_results],
                self.serialize(latest_build_results))
        )

        passing_build_map = {}
        missing_passing_builds = set()
        for build in latest_build_results:
            if build.result == Result.passed:
                passing_build_map[build.project_id] = build
            else:
                passing_build_map[build.project_id] = None
                missing_passing_builds.add(build.project_id)

        if missing_passing_builds:
            passing_build_results = get_latest_builds_query(
                project_list, result=Result.passed,
            )
            passing_build_map.update(dict(
                zip([b.project_id for b in passing_build_results],
                    self.serialize(passing_build_results))
            ))

        for project, data in zip(project_list, self.serialize(project_list)):
            # TODO(dcramer): build serializer is O(N) for stats
            data['lastBuild'] = latest_build_map.get(project.id)
            data['lastPassingBuild'] = passing_build_map.get(project.id)
            context.append(data)

        return self.paginate(context)

    @requires_auth
    def post(self):
        args = self.parser.parse_args()

        slug = str(args.slug or args.name.replace(' ', '-').lower())

        match = Project.query.filter(
            Project.slug == slug,
        ).first()
        if match:
            return '{"error": "Project with slug %r already exists"}' % (slug,), 400

        repository = Repository.get(args.repository)
        if repository is None:
            repository = Repository(
                url=args.repository,
            )
            db.session.add(repository)

        project = Project(
            name=args.name,
            slug=slug,
            repository=repository,
        )
        db.session.add(project)
        db.session.commit()

        return self.respond(project)

    def get_stream_channels(self):
        return ['builds:*']

########NEW FILE########
__FILENAME__ = project_options_index
from flask.ext.restful import reqparse
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.auth import requires_auth
from changes.db.utils import create_or_update
from changes.models import Project, ProjectOption


class ProjectOptionsIndexAPIView(APIView):
    # TODO(dcramer): these shouldn't be static
    parser = reqparse.RequestParser()
    parser.add_argument('green-build.notify')
    parser.add_argument('green-build.project')
    parser.add_argument('mail.notify-author')
    parser.add_argument('mail.notify-addresses')
    parser.add_argument('mail.notify-addresses-revisions')
    parser.add_argument('build.allow-patches')
    parser.add_argument('build.branch-names')
    parser.add_argument('build.commit-trigger')
    parser.add_argument('build.expect-tests')
    parser.add_argument('build.test-duration-warning')
    parser.add_argument('hipchat.notify')
    parser.add_argument('hipchat.room')
    parser.add_argument('ui.show-coverage')
    parser.add_argument('ui.show-tests')

    def _get_project(self, project_id):
        project = Project.query.options(
            joinedload(Project.repository, innerjoin=True),
        ).filter_by(slug=project_id).first()
        if project is None:
            project = Project.query.options(
                joinedload(Project.repository, innerjoin=True),
            ).get(project_id)
        return project

    @requires_auth
    def post(self, project_id):
        project = self._get_project(project_id)
        if project is None:
            return '', 404

        args = self.parser.parse_args()

        for name, value in args.iteritems():
            if value is None:
                continue
            create_or_update(ProjectOption, where={
                'project': project,
                'name': name,
            }, values={
                'value': value,
            })

        return '', 200

########NEW FILE########
__FILENAME__ = project_source_build_index
from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Build, Project, Source


class ProjectSourceBuildIndexAPIView(APIView):
    def get(self, project_id, source_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        repo = project.repository
        source = Source.query.filter(
            Source.id == source_id,
            Source.repository_id == repo.id,
        ).first()
        if source is None:
            return '', 404

        build_list = list(Build.query.options(
            joinedload('author'),
        ).filter(
            Build.source_id == source.id,
        ).order_by(Build.date_created.desc()))[:100]

        return self.respond(build_list)

########NEW FILE########
__FILENAME__ = project_source_details
from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.models import Project, Source
from changes.lib.coverage import get_coverage_by_source_id
import logging


class ProjectSourceDetailsAPIView(APIView):
    def get(self, project_id, source_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        repo = project.repository
        source = Source.query.filter(
            Source.id == source_id,
            Source.repository_id == repo.id,
        ).first()
        if source is None:
            return '', 404

        context = self.serialize(source)

        diff = source.generate_diff()

        if diff:
            files = self._get_files_from_raw_diff(diff)

            coverage = {
                c.filename: c.data
                for c in get_coverage_by_source_id(source_id)
                if c.filename in files
            }

            coverage_for_added_lines = self._filter_coverage_for_added_lines(diff, coverage)

            tails_info = dict(source.data)
        else:
            coverage = None
            coverage_for_added_lines = None
            tails_info = None

        context['diff'] = diff
        context['coverage'] = coverage
        context['coverageForAddedLines'] = coverage_for_added_lines
        context['tailsInfo'] = tails_info

        return self.respond(context)

    def _filter_coverage_for_added_lines(self, diff, coverage):
        """
        This function takes a diff (text based) and a map of file names to the coverage for those files and
        returns an ordered list of the coverage for each "addition" line in the diff.

        If we don't have coverage for a specific file, we just mark the lines in those files as unknown or 'N'.
        """
        if not diff:
            return None

        # Let's just encode it as utf-8 just in case
        diff_lines = diff.encode('utf-8').splitlines()

        current_file = None
        line_number = None
        coverage_by_added_line = []

        for line in diff_lines:
            if line.startswith('diff'):
                # We're about to start a new file.
                current_file = None
                line_number = None
            elif current_file is None and line_number is None and (line.startswith('+++') or line.startswith('---')):
                # We're starting a new file
                if line.startswith('+++ b/'):
                    line = line.split('\t')[0]
                    current_file = unicode(line[6:])
            elif line.startswith('@@'):
                # Jump to new lines within the file
                line_num_info = line.split('+')[1]
                line_number = int(line_num_info.split(',')[0]) - 1
            elif current_file is not None and line_number is not None:
                # Iterate through the file.
                if line.startswith('+'):
                    # Make sure we have coverage for this line.  Else just tag it as unknown.
                    cov = 'N'
                    if current_file in coverage:
                        try:
                            cov = coverage[current_file][line_number]
                        except IndexError:
                            logger = logging.getLogger('coverage')
                            logger.info('Missing code coverage for line %d of file %s' % (line_number, current_file))

                    coverage_by_added_line.append(cov)

                if not line.startswith('-'):
                    # Up the line count (assuming we aren't at a remove line)
                    line_number += 1

        return coverage_by_added_line

    def _get_files_from_raw_diff(self, diff):
        """
        Returns a list of filenames from a diff.
        """
        files = set()
        diff_lines = diff.encode('utf-8').split('\n')
        for line in diff_lines:
            if line.startswith('+++ b/'):
                line = line.split('\t')[0]
                files.add(unicode(line[6:]))

        return files

########NEW FILE########
__FILENAME__ = project_stats
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime, timedelta
from flask.ext.restful import reqparse
from sqlalchemy.sql import func

from changes.api.base import APIView
from changes.config import db
from changes.models import Project, Build, ItemStat


STAT_CHOICES = (
    'test_count',
    'test_duration',
    'test_failures',
    'test_rerun_count',
    'tests_missing',
    'lines_covered',
    'lines_uncovered',
    'diff_lines_covered',
    'diff_lines_uncovered',
)

RESOLUTION_CHOICES = (
    '1h',
    '1d',
    '1w',
    '1m',
)

AGG_CHOICES = (
    'sum',
    'avg',
)

POINTS_DEFAULT = {
    '1h': 24,
    '1d': 30,
    '1w': 26,
    '1m': 12,
}


def decr_month(dt):
    if dt.month == 1:
        return dt.replace(month=12, year=dt.year - 1)
    return dt.replace(month=dt.month - 1)


def decr_week(dt):
    return dt - timedelta(days=7)


class ProjectStatsAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('resolution', type=unicode, location='args',
                        choices=RESOLUTION_CHOICES, default='1d')
    parser.add_argument('stat', type=unicode, location='args',
                        choices=STAT_CHOICES, required=True)
    parser.add_argument('agg', type=unicode, location='args',
                        choices=AGG_CHOICES)
    parser.add_argument('points', type=int, location='args')
    parser.add_argument('from', type=int, location='args',
                        dest='from_date')

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        args = self.parser.parse_args()

        points = args.points or POINTS_DEFAULT[args.resolution]

        if args.from_date:
            date_end = datetime.fromtimestamp(args.from_date)
        else:
            date_end = datetime.now()

        date_end = date_end.replace(
            minute=0, second=0, microsecond=0)

        if args.resolution == '1h':
            grouper = func.date_trunc('hour', Build.date_created)
            decr_res = lambda x: x - timedelta(hours=1)
        elif args.resolution == '1d':
            grouper = func.date_trunc('day', Build.date_created)
            date_end = date_end.replace(hour=0)
            decr_res = lambda x: x - timedelta(days=1)
        elif args.resolution == '1w':
            grouper = func.date_trunc('week', Build.date_created)
            date_end = date_end.replace(hour=0)
            date_end -= timedelta(days=date_end.weekday())
            decr_res = decr_week
        elif args.resolution == '1m':
            grouper = func.date_trunc('month', Build.date_created)
            date_end = date_end.replace(hour=0, day=1)
            decr_res = decr_month

        if args.agg:
            value = getattr(func, args.agg)(ItemStat.value)
        else:
            value = func.avg(ItemStat.value)

        date_begin = date_end.replace()
        for _ in xrange(points):
            date_begin = decr_res(date_begin)

        # TODO(dcramer): put minimum date bounds
        results = dict(db.session.query(
            grouper.label('grouper'),
            value.label('value'),
        ).filter(
            ItemStat.item_id == Build.id,
            ItemStat.name == args.stat,
            Build.project_id == project.id,
            Build.date_created >= date_begin,
            Build.date_created < date_end,
        ).group_by('grouper'))

        data = []
        cur_date = date_end.replace()
        for _ in xrange(points):
            cur_date = decr_res(cur_date)
            data.append({
                'time': int(float(cur_date.strftime('%s.%f')) * 1000),
                'value': int(float(results.get(cur_date, 0))),
            })
        data.reverse()

        return self.respond(data, serialize=False)

########NEW FILE########
__FILENAME__ = project_test_details
from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import contains_eager, joinedload

from changes.api.base import APIView
from changes.api.serializer.models.testcase import GeneralizedTestCase
from changes.constants import Status
from changes.models import Build, Project, TestCase, Job, Source


class ProjectTestDetailsAPIView(APIView):
    def get(self, project_id, test_hash):
        project = Project.get(project_id)
        if not project:
            return '', 404

        # use the most recent test run to find basic details
        test = TestCase.query.filter(
            TestCase.project_id == project_id,
            TestCase.name_sha == test_hash,
        ).order_by(TestCase.date_created.desc()).limit(1).first()
        if not test:
            return '', 404

        # restrict the join to the last 1000 jobs otherwise this can get
        # significantly expensive as we have to seek quite a ways
        job_sq = Job.query.filter(
            Job.status == Status.finished,
            Job.project_id == project_id,
        ).order_by(Job.date_created.desc()).limit(1000).subquery()

        recent_runs = list(TestCase.query.options(
            contains_eager('job', alias=job_sq),
            contains_eager('job.source'),
            joinedload('job.build'),
            joinedload('job.build.author'),
            joinedload('job.build.source'),
            joinedload('job.build.source.revision'),
        ).join(
            job_sq, TestCase.job_id == job_sq.c.id,
        ).join(
            Source, job_sq.c.source_id == Source.id,
        ).filter(
            Source.repository_id == project.repository_id,
            Source.patch_id == None,  # NOQA
            Source.revision_sha != None,  # NOQA
            TestCase.name_sha == test.name_sha,
        ).order_by(job_sq.c.date_created.desc())[:25])

        first_test = TestCase.query.filter(
            TestCase.project_id == project_id,
            TestCase.name_sha == test_hash,
        ).order_by(TestCase.date_created.asc()).limit(1).first()
        first_build = Build.query.options(
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).filter(
            Build.id == first_test.job.build_id,
        ).first()

        jobs = set(r.job for r in recent_runs)
        builds = set(j.build for j in jobs)

        serialized_jobs = dict(zip(jobs, self.serialize(jobs)))
        serialized_builds = dict(zip(builds, self.serialize(builds)))

        results = []
        for recent_run, s_recent_run in zip(recent_runs, self.serialize(recent_runs)):
            s_recent_run['job'] = serialized_jobs[recent_run.job]
            s_recent_run['job']['build'] = serialized_builds[recent_run.job.build]
            results.append(s_recent_run)

        context = self.serialize(test, {
            TestCase: GeneralizedTestCase(),
        })
        context.update({
            'results': results,
            'firstBuild': first_build,
        })

        return self.respond(context, serialize=False)

########NEW FILE########
__FILENAME__ = project_test_group_index
from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.config import db
from changes.constants import Result, Status
from changes.models import Project, ProjectOption, TestCase, Job, Source
from changes.utils.trees import build_tree


class ProjectTestGroupIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('parent', type=unicode, location='args')

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        args = self.parser.parse_args()

        latest_job = Job.query.join(
            Source, Source.id == Job.source_id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Job.project_id == project.id,
            Job.result == Result.passed,
            Job.status == Status.finished,
        ).order_by(
            Job.date_created.desc(),
        ).limit(1).first()

        if not latest_job:
            return self.respond([])

        # use the most recent test
        test_list = db.session.query(
            TestCase.name, TestCase.duration
        ).filter(
            TestCase.project_id == project_id,
            TestCase.job_id == latest_job.id,
        )
        if args.parent:
            test_list = test_list.filter(
                TestCase.name.startswith(args.parent),
            )
        test_list = list(test_list)

        if test_list:
            sep = TestCase(name=test_list[0][0]).sep

            groups = build_tree(
                [t[0] for t in test_list],
                sep=sep,
                min_children=2,
                parent=args.parent,
            )

            results = []
            for group in groups:
                num_tests = 0
                total_duration = 0
                for name, duration in test_list:
                    if name == group or name.startswith(group + sep):
                        num_tests += 1
                        total_duration += duration

                if args.parent:
                    name = group[len(args.parent) + len(sep):]
                else:
                    name = group
                data = {
                    'name': name,
                    'path': group,
                    'totalDuration': total_duration,
                    'numTests': num_tests,
                }
                results.append(data)
            results.sort(key=lambda x: x['totalDuration'], reverse=True)

            trail = []
            context = []
            if args.parent:
                for chunk in args.parent.split(sep):
                    context.append(chunk)
                    trail.append({
                        'path': sep.join(context),
                        'name': chunk,
                    })
        else:
            results = []
            trail = []

        options = dict(
            (o.name, o.value) for o in ProjectOption.query.filter(
                ProjectOption.project_id == project.id,
                ProjectOption.name == 'build.test-duration-warning',
            )
        )

        over_threshold_duration = options.get('build.test-duration-warning')
        if over_threshold_duration:
            over_threshold_count = TestCase.query.filter(
                TestCase.project_id == project_id,
                TestCase.job_id == latest_job.id,
                TestCase.duration >= over_threshold_duration,
            ).count()
        else:
            over_threshold_count = 0

        data = {
            'groups': results,
            'trail': trail,
            'overThreshold': {
                'count': over_threshold_count,
                'duration': over_threshold_duration,
            }
        }

        return self.respond(data, serialize=False)

########NEW FILE########
__FILENAME__ = project_test_index
from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.api.serializer.models.testcase import GeneralizedTestCase
from changes.constants import Result, Status
from changes.models import Project, TestCase, Job, Source


SORT_CHOICES = (
    'duration',
    'name',
)


class ProjectTestIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('min_duration', type=int, location='args')
    parser.add_argument('query', type=unicode, location='args')
    parser.add_argument('sort', type=unicode, location='args',
                        choices=SORT_CHOICES, default='duration')

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        args = self.parser.parse_args()

        latest_job = Job.query.join(
            Source, Source.id == Job.source_id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Job.project_id == project.id,
            Job.result == Result.passed,
            Job.status == Status.finished,
        ).order_by(
            Job.date_created.desc(),
        ).limit(1).first()

        if not latest_job:
            return self.respond([])

        # use the most recent test
        test_list = TestCase.query.filter(
            TestCase.project_id == project_id,
            TestCase.job_id == latest_job.id,
        )

        if args.min_duration:
            test_list = test_list.filter(
                TestCase.duration >= args.min_duration,
            )

        if args.query:
            test_list = test_list.filter(
                TestCase.name.startswith(args.query),
            )

        if args.sort == 'duration':
            sort_by = TestCase.duration.desc()
        elif args.sort == 'name':
            sort_by = TestCase.name.asc()

        test_list = test_list.order_by(sort_by)

        return self.paginate(test_list, serializers={
            TestCase: GeneralizedTestCase(),
        })

########NEW FILE########
__FILENAME__ = base
from datetime import datetime
from enum import Enum
from uuid import UUID

_registry = {}


def register(type):
    def wrapped(cls):
        _registry[type] = cls()
        return cls
    return wrapped


def get_serializer(item, registry):
    item_type = type(item)

    serializer = registry.get(item_type, _registry.get(item_type))

    if serializer is None:
        for cls, _serializer in _registry.iteritems():
            if issubclass(item_type, cls):
                serializer = _serializer
                break

    return serializer


def serialize(data, extended_registry=None):
    if extended_registry is None:
        extended_registry = {}

    if data is None:
        return None

    if isinstance(data, (basestring, int, long, float, bool)):
        return data

    if isinstance(data, dict):
        return dict(
            (k, v) for k, v
            in zip(serialize(data.keys(), extended_registry),
                   serialize(data.values(), extended_registry))
        )

    if isinstance(data, (list, tuple, set, frozenset)):
        if not data:
            return []

        if len(set(type(g) for g in data)) == 1:
            data = list(data)

            serializer = get_serializer(data[0], extended_registry)

            if serializer:
                attrs = serializer.get_attrs(data)

                data = [serializer(o, attrs=attrs.get(o)) for o in data]

        return [serialize(j, extended_registry) for j in data]

    serializer = get_serializer(data, extended_registry)

    if serializer is None:
        return data

    attrs = serializer.get_attrs([data])

    data = serializer(data, attrs=attrs.get(data))

    return serialize(data, extended_registry)


class Serializer(object):
    def __call__(self, item, attrs):
        return self.serialize(item, attrs)

    def get_attrs(self, item_list):
        return {}

    def serialize(self, item, attrs):
        return {}


@register(datetime)
class DateTimeSerializer(Serializer):
    def serialize(self, item, attrs):
        return item.isoformat()


@register(Enum)
class EnumSerializer(Serializer):
    def serialize(self, item, attrs):
        return {
            'id': item.name,
            'name': unicode(item),
        }


@register(UUID)
class UUIDSerializer(Serializer):
    def serialize(self, item, attrs):
        return item.hex

########NEW FILE########
__FILENAME__ = author
from changes.api.serializer import Serializer, register
from changes.api.serializer.models.user import get_gravatar_url
from changes.models.author import Author


@register(Author)
class AuthorSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.name,
            'email': instance.email,
            'avatar': get_gravatar_url(instance.email),
            'dateCreated': instance.date_created,
        }

########NEW FILE########
__FILENAME__ = build
from changes.api.serializer import Serializer, register
from changes.models import Build, ItemStat
from changes.utils.http import build_uri


@register(Build)
class BuildSerializer(Serializer):
    def get_attrs(self, item_list):
        stat_list = ItemStat.query.filter(
            ItemStat.item_id.in_(r.id for r in item_list),
        )
        stats_by_item = {}
        for stat in stat_list:
            stats_by_item.setdefault(stat.item_id, {})
            stats_by_item[stat.item_id][stat.name] = stat.value

        result = {}
        for item in item_list:
            result[item] = {'stats': stats_by_item.get(item.id, {})}

        return result

    def serialize(self, item, attrs):
        if item.project_id:
            avg_build_time = item.project.avg_build_time
        else:
            avg_build_time = None

        target = item.target
        if target is None and item.source and item.source.revision_sha:
            target = item.source.revision_sha[:12]

        return {
            'id': item.id.hex,
            'number': item.number,
            'name': item.label,
            'target': target,
            'result': item.result,
            'status': item.status,
            'project': item.project,
            'cause': item.cause,
            'author': item.author,
            'source': item.source,
            'message': item.message,
            'duration': item.duration,
            'estimatedDuration': avg_build_time,
            'dateCreated': item.date_created.isoformat(),
            'dateModified': item.date_modified.isoformat() if item.date_modified else None,
            'dateStarted': item.date_started.isoformat() if item.date_started else None,
            'dateFinished': item.date_finished.isoformat() if item.date_finished else None,
            'stats': attrs['stats'],
            'link': build_uri('/projects/{0}/builds/{1}/'.format(
                item.project.slug, item.id.hex)),
        }

########NEW FILE########
__FILENAME__ = change
from changes.api.serializer import Serializer, register
from changes.models.change import Change
from changes.utils.http import build_uri


@register(Change)
class ChangeSerializer(Serializer):
    def serialize(self, instance, attrs):
        result = {
            'id': instance.id.hex,
            'name': instance.label,
            'project': instance.project,
            'author': instance.author,
            'message': instance.message,
            'link': build_uri('/changes/%s/' % (instance.id.hex,)),
            'dateCreated': instance.date_created.isoformat(),
            'dateModified': instance.date_modified.isoformat(),
        }
        if hasattr(instance, 'last_job'):
            result['lastBuild'] = instance.last_job
        return result

########NEW FILE########
__FILENAME__ = cluster
from changes.api.serializer import Serializer, register
from changes.models import Cluster


@register(Cluster)
class ClusterSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'dateCreated': instance.date_created,
        }

########NEW FILE########
__FILENAME__ = comment
from changes.api.serializer import Serializer, register
from changes.models import Comment


@register(Comment)
class CommentSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'user': instance.user,
            'text': instance.text,
            'dateCreated': instance.date_created.isoformat(),
        }

########NEW FILE########
__FILENAME__ = event
from changes.api.serializer import Serializer, register
from changes.models import Event


@register(Event)
class EventSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'type': instance.type,
            'itemId': instance.item_id.hex,
            'data': dict(instance.data),
            'dateCreated': instance.date_created.isoformat(),
            'dateModified': instance.date_modified.isoformat(),
        }

########NEW FILE########
__FILENAME__ = job
from sqlalchemy.orm import joinedload

from changes.api.serializer import Serializer, register, serialize
from changes.models import Build, Job


@register(Job)
class JobSerializer(Serializer):
    def serialize(self, instance, attrs):
        if instance.project_id:
            avg_build_time = instance.project.avg_build_time
        else:
            avg_build_time = None

        data = instance.data or {}
        backend_details = data.get('backend')
        if backend_details:
            external = {
                'link': backend_details['uri'],
                'label': backend_details['label'],
            }
        else:
            external = None

        data = {
            'id': instance.id.hex,
            'number': instance.number,
            'name': instance.label,
            'result': instance.result,
            'status': instance.status,
            'project': instance.project,
            'duration': instance.duration,
            'estimatedDuration': avg_build_time,
            'external': external,
            'dateCreated': instance.date_created.isoformat(),
            'dateModified': instance.date_modified.isoformat() if instance.date_modified else None,
            'dateStarted': instance.date_started.isoformat() if instance.date_started else None,
            'dateFinished': instance.date_finished.isoformat() if instance.date_finished else None,
        }
        if instance.build_id:
            data['build'] = {'id': instance.build_id.hex}
        return data


class JobWithBuildSerializer(JobSerializer):
    def get_attrs(self, item_list):
        build_list = list(Build.query.options(
            joinedload('project'),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).filter(
            Build.id.in_(j.build_id for j in item_list),
        ))
        build_map = dict(
            (b.id, d) for b, d in zip(build_list, serialize(build_list))
        )

        result = {}
        for item in item_list:
            result[item] = {'build': build_map.get(item.build_id)}

        return result

    def serialize(self, instance, attrs):
        data = super(JobWithBuildSerializer, self).serialize(instance, attrs)
        # TODO(dcramer): this is O(N) queries due to the attach helpers
        data['build'] = attrs['build']
        return data

########NEW FILE########
__FILENAME__ = jobphase
from changes.api.serializer import Serializer, register
from changes.models import JobPhase


@register(JobPhase)
class JobPhaseSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'result': instance.result,
            'status': instance.status,
            'duration': instance.duration,
            'dateCreated': instance.date_created,
            'dateStarted': instance.date_started,
            'dateFinished': instance.date_finished,
        }


class JobPhaseWithStepsSerializer(JobPhaseSerializer):
    def serialize(self, instance, attrs):
        data = super(JobPhaseWithStepsSerializer, self).serialize(instance, attrs)
        data['steps'] = list(instance.steps)
        return data

########NEW FILE########
__FILENAME__ = jobstep
from changes.api.serializer import Serializer, register
from changes.models import JobStep


@register(JobStep)
class JobStepSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'phase': {
                'id': instance.phase_id.hex,
            },
            'result': instance.result,
            'status': instance.status,
            'node': instance.node,
            'duration': instance.duration,
            'dateCreated': instance.date_created,
            'dateStarted': instance.date_started,
            'dateFinished': instance.date_finished,
        }

########NEW FILE########
__FILENAME__ = logchunk
from ansi2html import Ansi2HTMLConverter

from changes.api.serializer import Serializer, register
from changes.models.log import LogChunk


@register(LogChunk)
class LogChunkSerializer(Serializer):
    def serialize(self, instance, attrs):
        conv = Ansi2HTMLConverter()
        formatted_text = conv.convert(instance.text, full=False)

        return {
            'id': instance.id.hex,
            'source': {
                'id': instance.source.id.hex,
            },
            'text': formatted_text,
            'offset': instance.offset,
            'size': instance.size,
        }

########NEW FILE########
__FILENAME__ = logsource
from changes.api.serializer import Serializer, register
from changes.models.log import LogSource


@register(LogSource)
class LogSourceSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'job': {
                'id': instance.job_id.hex,
            },
            'name': instance.name,
            'step': instance.step,
            'dateCreated': instance.date_created,
        }

########NEW FILE########
__FILENAME__ = node
from changes.api.serializer import Serializer, register
from changes.models import Node


@register(Node)
class NodeSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'dateCreated': instance.date_created,
        }

########NEW FILE########
__FILENAME__ = patch
from changes.api.serializer import Serializer, register
from changes.models.patch import Patch
from changes.utils.http import build_uri


@register(Patch)
class PatchSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'diff': instance.diff,
            'link': build_uri('/patches/{0}/'.format(instance.id.hex)),
            'parentRevision': {
                'sha': instance.parent_revision_sha,
            },
            'dateCreated': instance.date_created,
        }

########NEW FILE########
__FILENAME__ = plan
import json

from changes.api.serializer import Serializer, register
from changes.models import Plan, Step


@register(Plan)
class PlanSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'name': instance.label,
            'steps': list(instance.steps),
            'dateCreated': instance.date_created,
            'dateModified': instance.date_modified,
        }


@register(Step)
class StepSerializer(Serializer):
    def serialize(self, instance, attrs):
        implementation = instance.get_implementation()

        return {
            'id': instance.id.hex,
            'implementation': instance.implementation,
            'order': instance.order,
            'name': implementation.get_label() if implementation else '',
            'data': json.dumps(dict(instance.data or {})),
            'dateCreated': instance.date_created,
        }

########NEW FILE########
__FILENAME__ = project
from changes.api.serializer import Serializer, register
from changes.models.project import Project
from changes.utils.http import build_uri


@register(Project)
class ProjectSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'slug': instance.slug,
            'name': instance.name,
            'repository': {
                'id': instance.repository_id,
            },
            'dateCreated': instance.date_created,
            'link': build_uri('/projects/{0}/'.format(instance.slug)),
        }

########NEW FILE########
__FILENAME__ = repository
from changes.api.serializer import Serializer, register
from changes.models.repository import Repository, RepositoryBackend


@register(Repository)
class RepositorySerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'url': instance.url,
            'backend': instance.backend,
        }


@register(RepositoryBackend)
class RepositoryBackendSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.name,
            'name': unicode(instance),
        }

########NEW FILE########
__FILENAME__ = revision
from changes.api.serializer import Serializer, register
from changes.models.revision import Revision


@register(Revision)
class RevisionSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.sha,
            'repository': {
                'id': instance.repository_id,
            },
            'sha': instance.sha,
            'message': instance.message,
            'author': instance.author,
            'parents': instance.parents,
            'branches': instance.branches,
            'dateCreated': instance.date_created,
        }

########NEW FILE########
__FILENAME__ = revisionresult
from changes.api.serializer import Serializer, register
from changes.vcs.base import RevisionResult


@register(RevisionResult)
class RevisionSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id,
            'message': instance.message,
            'author': None,  # We don't return author information
            'dateCreated': instance.author_date,
            'branches': instance.branches,
        }

########NEW FILE########
__FILENAME__ = source
from changes.api.serializer import Serializer, register
from changes.models import Source


@register(Source)
class SourceSerializer(Serializer):
    def serialize(self, instance, attrs):
        if instance.patch_id:
            patch = {
                'id': instance.patch_id.hex,
            }
        else:
            patch = None

        return {
            'id': instance.id.hex,
            'patch': patch,
            'revision': instance.revision,
            'isCommit': instance.is_commit(),
            'dateCreated': instance.date_created,
            'data': dict(instance.data or {}),
        }

########NEW FILE########
__FILENAME__ = task
from changes.api.serializer import Serializer, register
from changes.models import Task


@register(Task)
class TaskSerializer(Serializer):
    def serialize(self, instance, attrs):
        if instance.data:
            args = instance.data.get('kwargs') or {}
        else:
            args = {}

        return {
            'id': instance.id.hex,
            'objectID': instance.task_id,
            'parentObjectID': instance.parent_id,
            'name': instance.task_name,
            'args': args,
            'attempts': instance.num_retries + 1,
            'status': instance.status,
            'result': instance.result,
            'dateCreated': instance.date_created,
            'dateStarted': instance.date_started,
            'dateFinished': instance.date_finished,
            'dateModified': instance.date_modified,
        }

########NEW FILE########
__FILENAME__ = testcase
from changes.api.serializer import Serializer, register
from changes.models.test import TestCase


@register(TestCase)
class TestCaseSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'hash': instance.name_sha,
            'job': {'id': instance.job_id.hex},
            'project': {'id': instance.project_id.hex},
            'name': instance.name,
            'package': instance.package,
            'shortName': instance.short_name,
            'duration': instance.duration or 0,
            'result': instance.result,
            'numRetries': instance.reruns or 0,
            'dateCreated': instance.date_created,
        }


class TestCaseWithJobSerializer(TestCaseSerializer):
    def serialize(self, instance, attrs):
        data = super(TestCaseWithJobSerializer, self).serialize(instance, attrs)
        data['job'] = instance.job
        return data


class TestCaseWithOriginSerializer(TestCaseSerializer):
    def serialize(self, instance, attrs):
        data = super(TestCaseWithOriginSerializer, self).serialize(instance, attrs)
        data['origin'] = getattr(instance, 'origin', None)
        return data


class GeneralizedTestCase(Serializer):
    def serialize(self, instance, attrs):
        return {
            'hash': instance.name_sha,
            'project': {'id': instance.project_id.hex},
            'duration': instance.duration or 0,
            'name': instance.name,
            'package': instance.package,
            'shortName': instance.short_name,
        }

########NEW FILE########
__FILENAME__ = user
from hashlib import md5
from urllib import urlencode

from changes.api.serializer import Serializer, register
from changes.models import User


def get_gravatar_url(email, size=None, default='mm'):
    gravatar_url = "https://secure.gravatar.com/avatar/%s" % (
        md5(email.lower()).hexdigest())

    properties = {}
    if size:
        properties['s'] = str(size)
    if default:
        properties['d'] = default
    if properties:
        gravatar_url += "?" + urlencode(properties)

    return gravatar_url


@register(User)
class UserSerializer(Serializer):
    def serialize(self, instance, attrs):
        return {
            'id': instance.id.hex,
            'isAdmin': instance.is_admin,
            'email': instance.email,
            'avatar': get_gravatar_url(instance.email),
            'dateCreated': instance.date_created,
        }

########NEW FILE########
__FILENAME__ = step_details
from __future__ import absolute_import, division, unicode_literals

import json

from datetime import datetime
from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.api.auth import requires_admin
from changes.config import db
from changes.constants import IMPLEMENTATION_CHOICES
from changes.models import Step


class StepDetailsAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('data')
    parser.add_argument('implementation', choices=IMPLEMENTATION_CHOICES)
    parser.add_argument('order', type=int, default=0)

    def get(self, step_id):
        step = Step.query.get(step_id)
        if step is None:
            return {"message": "step not found"}, 404

        return self.respond(step)

    @requires_admin
    def post(self, step_id):
        step = Step.query.get(step_id)
        if step is None:
            return {"message": "step not found"}, 404

        args = self.parser.parse_args()

        if args.implementation is not None:
            step.implementation = args.implementation

        if args.data is not None:
            data = json.loads(args.data)
            if not isinstance(data, dict):
                return {"message": "data must be a JSON mapping"}, 400

            impl_cls = step.get_implementation(load=False)
            if impl_cls is None:
                return {"message": "unable to load build step implementation"}, 400

            try:
                impl_cls(**data)
            except Exception:
                return {"message": "unable to create build step mapping provided data"}, 400
            step.data = data

        if args.order is not None:
            step.order = args.order

        step.date_modified = datetime.utcnow()
        db.session.add(step)

        plan = step.plan
        plan.date_modified = step.date_modified
        db.session.add(plan)

        db.session.commit()

        return self.serialize(step), 200

    @requires_admin
    def delete(self, step_id):
        step = Step.query.get(step_id)
        if step is None:
            return '', 404

        Step.query.filter(
            Step.id == step.id,
        ).delete(
            synchronize_session=False,
        )
        db.session.commit()

        return '', 200

########NEW FILE########
__FILENAME__ = task_details
from __future__ import absolute_import

from changes.api.base import APIView
from changes.models import Task


class TaskDetailsAPIView(APIView):
    def _collect_children(self, task):
        children = Task.query.filter(
            Task.parent_id == task.task_id,
        )
        results = []
        for child in children:
            child_data = self.serialize(child)
            child_data['children'] = self._collect_children(child)
            results.append(child_data)

        return results

    def get(self, task_id):
        task = Task.query.get(task_id)
        if task is None:
            return '', 404

        context = self.serialize(task)
        context['children'] = self._collect_children(task)

        return self.respond(context)

########NEW FILE########
__FILENAME__ = task_index
from __future__ import absolute_import

from changes.api.base import APIView
from changes.models import Task


class TaskIndexAPIView(APIView):
    def get(self):
        queryset = Task.query.order_by(Task.date_created.desc())

        return self.paginate(queryset)

########NEW FILE########
__FILENAME__ = testcase_details
from changes.api.base import APIView
from changes.models import TestCase


class TestCaseDetailsAPIView(APIView):
    def get(self, test_id):
        testcase = TestCase.query.get(test_id)
        if testcase is None:
            return '', 404

        context = self.serialize(testcase)
        context['message'] = testcase.message

        return self.respond(context)

########NEW FILE########
__FILENAME__ = author
from changes.models.author import Author
from changes.db.utils import get_or_create


class AuthorValidator(object):
    def __call__(self, value):
        parsed = self.parse(value)
        if not parsed:
            raise ValueError(value)

        name, email = parsed
        author, _ = get_or_create(Author, where={
            'email': email,
        }, defaults={
            'name': name,
        })
        return author

    def parse(self, value):
        import re
        match = re.match(r'^(.+) <([^>]+)>$', value)

        if not match:
            if '@' in value:
                name, email = value, value
            else:
                raise ValueError(value)
        else:
            name, email = match.group(1), match.group(2)
        return name, email

########NEW FILE########
__FILENAME__ = app
"""
This file acts as a default entry point for app creation.
"""

from changes.config import create_app, queue

app = create_app()

# HACK(dcramer): this allows Celery to detect itself -.-
celery = queue.celery

########NEW FILE########
__FILENAME__ = base
class UnrecoverableException(Exception):
    pass


class BaseBackend(object):
    def __init__(self, app):
        self.app = app

    def create_job(self, job):
        raise NotImplementedError

    def sync_job(self, job):
        raise NotImplementedError

    def sync_step(self, step):
        raise NotImplementedError

    def cancel_job(self, job):
        raise NotImplementedError

    def cancel_step(self, step):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = builder
from __future__ import absolute_import, division

import json
import logging
import re
import requests
import time

from cStringIO import StringIO
from datetime import datetime
from flask import current_app
from lxml import etree, objectify

from changes.backends.base import BaseBackend, UnrecoverableException
from changes.config import db
from changes.constants import Result, Status
from changes.db.utils import create_or_update, get_or_create
from changes.jobs.sync_artifact import sync_artifact
from changes.jobs.sync_job_step import sync_job_step
from changes.models import (
    Artifact, Cluster, ClusterNode, TestResult, TestResultManager,
    LogSource, LogChunk, Node, JobPhase, JobStep
)
from changes.handlers.coverage import CoverageHandler
from changes.handlers.xunit import XunitHandler
from changes.utils.agg import safe_agg
from changes.utils.http import build_uri

LOG_CHUNK_SIZE = 4096

RESULT_MAP = {
    'SUCCESS': Result.passed,
    'ABORTED': Result.aborted,
    'FAILURE': Result.failed,
    'REGRESSION': Result.failed,
    'UNSTABLE': Result.failed,
}

QUEUE_ID_XPATH = '/queue/item[action/parameter/name="CHANGES_BID" and action/parameter/value="{job_id}"]/id'
BUILD_ID_XPATH = '/freeStyleProject/build[action/parameter/name="CHANGES_BID" and action/parameter/value="{job_id}"]/number'

XUNIT_FILENAMES = ('junit.xml', 'xunit.xml', 'nosetests.xml')
COVERAGE_FILENAMES = ('coverage.xml',)

ID_XML_RE = re.compile(r'<id>(\d+)</id>')


def chunked(iterator, chunk_size):
    """
    Given an iterator, chunk it up into ~chunk_size, but be aware of newline
    termination as an intended goal.
    """
    result = ''
    for chunk in iterator:
        result += chunk
        while len(result) >= chunk_size:
            newline_pos = result.rfind('\n', 0, chunk_size)
            if newline_pos == -1:
                newline_pos = chunk_size
            else:
                newline_pos += 1
            yield result[:newline_pos]
            result = result[newline_pos:]
    if result:
        yield result


class NotFound(Exception):
    pass


class JenkinsBuilder(BaseBackend):
    provider = 'jenkins'

    def __init__(self, base_url=None, job_name=None, token=None, auth=None,
                 *args, **kwargs):
        super(JenkinsBuilder, self).__init__(*args, **kwargs)
        self.base_url = base_url or self.app.config['JENKINS_URL']
        self.token = token or self.app.config['JENKINS_TOKEN']
        self.auth = auth or self.app.config['JENKINS_AUTH']
        self.logger = logging.getLogger('jenkins')
        self.job_name = job_name
        # disabled by default as it's expensive
        self.sync_log_artifacts = self.app.config.get('JENKINS_SYNC_LOG_ARTIFACTS', False)
        self.sync_xunit_artifacts = self.app.config.get('JENKINS_SYNC_XUNIT_ARTIFACTS', True)
        self.sync_coverage_artifacts = self.app.config.get('JENKINS_SYNC_COVERAGE_ARTIFACTS', True)

    def _get_raw_response(self, path, method='GET', params=None, **kwargs):
        url = '{}/{}'.format(self.base_url, path.lstrip('/'))

        kwargs.setdefault('allow_redirects', False)
        kwargs.setdefault('timeout', 5)
        kwargs.setdefault('auth', self.auth)

        if params is None:
            params = {}

        params.setdefault('token', self.token)

        self.logger.info('Fetching %r', url)
        resp = getattr(requests, method.lower())(url, params=params, **kwargs)

        if resp.status_code == 404:
            raise NotFound
        elif not (200 <= resp.status_code < 400):
            raise Exception('Invalid response. Status code was %s' % resp.status_code)

        return resp.text

    def _get_json_response(self, path, *args, **kwargs):
        path = '{}/api/json/'.format(path.strip('/'))

        data = self._get_raw_response(path, *args, **kwargs)
        if not data:
            return

        try:
            return json.loads(data)
        except ValueError:
            raise Exception('Invalid JSON data')

    _get_response = _get_json_response

    def _parse_parameters(self, json):
        params = {}
        for action in json['actions']:
            params.update(
                (p['name'], p.get('value'))
                for p in action.get('parameters', [])
            )
        return params

    def _create_job_step(self, phase, job_name=None, build_no=None,
                         label=None, **kwargs):
        # TODO(dcramer): we make an assumption that the job step label is unique
        # but its not guaranteed to be the case. We can ignore this assumption
        # by guaranteeing that the JobStep.id value is used for builds instead
        # of the Job.id value.
        defaults = {
            'data': {
                'job_name': job_name,
                'build_no': build_no,
            },
        }
        defaults.update(kwargs)

        data = defaults['data']
        if data['job_name'] and not label:
            label = '{0} #{1}'.format(data['job_name'], data['build_no'] or data['item_id'])

        assert label

        step, created = get_or_create(JobStep, where={
            'job': phase.job,
            'project': phase.project,
            'phase': phase,
            'label': label,
        }, defaults=defaults)

        return step

    def fetch_artifact(self, jobstep, artifact):
        url = '{base}/job/{job}/{build}/artifact/{artifact}'.format(
            base=self.base_url,
            job=jobstep.data['job_name'],
            build=jobstep.data['build_no'],
            artifact=artifact['relativePath'],
        )
        return requests.get(url, stream=True, timeout=15)

    def _sync_artifact_as_xunit(self, jobstep, artifact):
        resp = self.fetch_artifact(jobstep, artifact)

        # TODO(dcramer): requests doesnt seem to provide a non-binary file-like
        # API, so we're stuffing it into StringIO
        try:
            handler = XunitHandler(jobstep)
            handler.process(StringIO(resp.content))
        except Exception:
            db.session.rollback()
            self.logger.exception(
                'Failed to sync test results for job step %s', jobstep.id)
        else:
            db.session.commit()

    def _sync_artifact_as_coverage(self, jobstep, artifact):
        resp = self.fetch_artifact(jobstep, artifact)

        # TODO(dcramer): requests doesnt seem to provide a non-binary file-like
        # API, so we're stuffing it into StringIO
        try:
            handler = CoverageHandler(jobstep)
            handler.process(StringIO(resp.content))
        except Exception:
            db.session.rollback()
            self.logger.exception(
                'Failed to sync test results for job step %s', jobstep.id)
        else:
            db.session.commit()

    def _sync_artifact_as_log(self, jobstep, artifact):
        job = jobstep.job
        logsource, created = get_or_create(LogSource, where={
            'name': artifact['displayPath'],
            'job': job,
            'step': jobstep,
        }, defaults={
            'project': job.project,
            'date_created': job.date_started,
        })

        job_name = jobstep.data['job_name']
        build_no = jobstep.data['build_no']

        url = '{base}/job/{job}/{build}/artifact/{artifact}'.format(
            base=self.base_url, job=job_name,
            build=build_no, artifact=artifact['relativePath'],
        )

        offset = 0
        resp = requests.get(url, stream=True, timeout=15)
        iterator = resp.iter_content()
        for chunk in chunked(iterator, LOG_CHUNK_SIZE):
            chunk_size = len(chunk)
            chunk, _ = create_or_update(LogChunk, where={
                'source': logsource,
                'offset': offset,
            }, values={
                'job': job,
                'project': job.project,
                'size': chunk_size,
                'text': chunk,
            })
            offset += chunk_size

    def _sync_console_log(self, jobstep):
        job = jobstep.job
        return self._sync_log(
            jobstep=jobstep,
            name='console',
            job_name=job.data['job_name'],
            build_no=job.data['build_no'],
        )

    def _sync_log(self, jobstep, name, job_name, build_no):
        job = jobstep.job
        # TODO(dcramer): this doesnt handle concurrency
        logsource, created = get_or_create(LogSource, where={
            'name': name,
            'job': job,
        }, defaults={
            'step': jobstep,
            'project': jobstep.project,
            'date_created': jobstep.date_started,
        })
        if created:
            offset = 0
        else:
            offset = jobstep.data.get('log_offset', 0)

        url = '{base}/job/{job}/{build}/logText/progressiveHtml/'.format(
            base=self.base_url,
            job=job_name,
            build=build_no,
        )

        resp = requests.get(
            url, params={'start': offset}, stream=True, timeout=15)
        log_length = int(resp.headers['X-Text-Size'])
        # When you request an offset that doesnt exist in the build log, Jenkins
        # will instead return the entire log. Jenkins also seems to provide us
        # with X-Text-Size which indicates the total size of the log
        if offset > log_length:
            return

        iterator = resp.iter_content()
        # XXX: requests doesnt seem to guarantee chunk_size, so we force it
        # with our own helper
        for chunk in chunked(iterator, LOG_CHUNK_SIZE):
            chunk_size = len(chunk)
            chunk, _ = create_or_update(LogChunk, where={
                'source': logsource,
                'offset': offset,
            }, values={
                'job': job,
                'project': job.project,
                'size': chunk_size,
                'text': chunk,
            })
            offset += chunk_size

        # We **must** track the log offset externally as Jenkins embeds encoded
        # links and we cant accurately predict the next `start` param.
        jobstep.data['log_offset'] = log_length
        db.session.add(jobstep)

        # Jenkins will suggest to us that there is more data when the job has
        # yet to complete
        return True if resp.headers.get('X-More-Data') == 'true' else None

    def _process_test_report(self, step, test_report):
        test_list = []

        if not test_report:
            return test_list

        for suite_data in test_report['suites']:
            for case in suite_data['cases']:
                message = []
                if case['errorDetails']:
                    message.append('Error\n-----')
                    message.append(case['errorDetails'] + '\n')
                if case['errorStackTrace']:
                    message.append('Stacktrace\n----------')
                    message.append(case['errorStackTrace'] + '\n')
                if case['skippedMessage']:
                    message.append(case['skippedMessage'] + '\n')

                if case['status'] in ('PASSED', 'FIXED'):
                    result = Result.passed
                elif case['status'] in ('FAILED', 'REGRESSION'):
                    result = Result.failed
                elif case['status'] == 'SKIPPED':
                    result = Result.skipped
                else:
                    raise ValueError('Invalid test result: %s' % (case['status'],))

                test_result = TestResult(
                    step=step,
                    name=case['name'],
                    package=case['className'] or None,
                    duration=int(case['duration'] * 1000),
                    message='\n'.join(message).strip(),
                    result=result,
                )
                test_list.append(test_result)
        return test_list

    def _sync_test_results(self, step, job_name, build_no):
        try:
            test_report = self._get_response('/job/{}/{}/testReport/'.format(
                job_name, build_no))
        except NotFound:
            return

        test_list = self._process_test_report(step, test_report)

        manager = TestResultManager(step)
        manager.save(test_list)

    def _find_job(self, job_name, job_id):
        """
        Given a job identifier, we attempt to poll the various endpoints
        for a limited amount of time, trying to match up either a queued item
        or a running job that has the CHANGES_BID parameter.

        This is nescesary because Jenkins does not give us any identifying
        information when we create a job initially.

        The job_id parameter should be the corresponding value to look for in
        the CHANGES_BID parameter.

        The result is a mapping with the following keys:

        - queued: is it currently present in the queue
        - item_id: the queued item ID, if available
        - build_no: the build number, if available
        """
        # Check the queue first to ensure that we don't miss a transition
        # from queue -> active jobs
        item = self._find_job_in_queue(job_name, job_id)
        if item:
            return item
        return self._find_job_in_active(job_name, job_id)

    def _find_job_in_queue(self, job_name, job_id):
        xpath = QUEUE_ID_XPATH.format(
            job_id=job_id,
        )
        try:
            response = self._get_raw_response('/queue/api/xml/', params={
                'xpath': xpath,
                'wrapper': 'x',
            })
        except NotFound:
            return

        # it's possible that we managed to create multiple jobs in certain
        # situations, so let's just get the newest one
        try:
            match = etree.fromstring(response).iter('id').next()
        except StopIteration:
            return
        item_id = match.text

        # TODO: it's possible this isnt queued when this gets run
        return {
            'job_name': job_name,
            'queued': True,
            'item_id': item_id,
            'build_no': None,
        }

    def _find_job_in_active(self, job_name, job_id):
        xpath = BUILD_ID_XPATH.format(
            job_id=job_id,
        )
        try:
            response = self._get_raw_response('/job/{job_name}/api/xml/'.format(
                job_name=job_name,
            ), params={
                'depth': 1,
                'xpath': xpath,
                'wrapper': 'x',
            })
        except NotFound:
            return

        # it's possible that we managed to create multiple jobs in certain
        # situations, so let's just get the newest one
        try:
            match = etree.fromstring(response).iter('number').next()
        except StopIteration:
            return
        build_no = match.text

        return {
            'job_name': job_name,
            'queued': False,
            'item_id': None,
            'build_no': build_no,
        }

    def _get_node(self, label):
        node, created = get_or_create(Node, {'label': label})
        if not created:
            return node

        try:
            response = self._get_raw_response('/computer/{}/config.xml'.format(
                label
            ))
        except NotFound:
            return node

        # lxml expects the response to be in bytes, so let's assume it's utf-8
        # and send it back as the original format
        response = response.encode('utf-8')

        xml = objectify.fromstring(response)
        cluster_names = xml.label.text.split(' ')

        for cluster_name in cluster_names:
            # remove swarm client as a cluster label as its not useful
            if cluster_name == 'swarm':
                continue
            cluster, _ = get_or_create(Cluster, {'label': cluster_name})
            get_or_create(ClusterNode, {'node': node, 'cluster': cluster})

        return node

    def _sync_step_from_queue(self, step):
        # TODO(dcramer): when we hit a NotFound in the queue, maybe we should
        # attempt to scrape the list of jobs for a matching CHANGES_BID, as this
        # doesnt explicitly mean that the job doesnt exist
        try:
            item = self._get_response('/queue/item/{}'.format(
                step.data['item_id']))
        except NotFound:
            step.status = Status.finished
            step.result = Result.unknown
            db.session.add(step)
            return

        if item.get('executable'):
            build_no = item['executable']['number']
            step.data['queued'] = False
            step.data['build_no'] = build_no
            db.session.add(step)

        if item['blocked']:
            step.status = Status.queued
            db.session.add(step)
        elif item.get('cancelled') and not step.data.get('build_no'):
            step.status = Status.finished
            step.result = Result.aborted
            db.session.add(step)
        elif item.get('executable'):
            return self._sync_step_from_active(step)

    def _sync_step_from_active(self, step):
        try:
            job_name = step.data['job_name']
            build_no = step.data['build_no']
        except KeyError:
            raise UnrecoverableException('Missing Jenkins job information')

        try:
            item = self._get_response('/job/{}/{}'.format(
                job_name, build_no))
        except NotFound:
            raise UnrecoverableException('Unable to find job in Jenkins')

        # TODO(dcramer): we're doing a lot of work here when we might
        # not need to due to it being sync'd previously
        node = self._get_node(item['builtOn'])

        step.node = node
        step.date_started = datetime.utcfromtimestamp(
            item['timestamp'] / 1000)

        if item['building']:
            step.status = Status.in_progress
        else:
            step.status = Status.finished
            step.result = RESULT_MAP[item['result']]
            # values['duration'] = item['duration'] or None
            step.date_finished = datetime.utcfromtimestamp(
                (item['timestamp'] + item['duration']) / 1000)

        # step.data.update({
        #     'backend': {
        #         'uri': item['url'],
        #         'label': item['fullDisplayName'],
        #     }
        # })
        db.session.add(step)
        db.session.commit()

        # TODO(dcramer): we should abstract this into a sync_phase
        phase = step.phase
        phase_steps = list(phase.steps)

        if phase.date_started is None:
            phase.date_started = safe_agg(
                min, (s.date_started for s in phase_steps), step.date_started)
            db.session.add(phase)

        if phase.status == Status.queued != step.status:
            phase.status = Status.in_progress
            db.session.add(phase)

        if db.session.is_modified(phase):
            db.session.commit()

        if step.status != Status.finished:
            return

        if all(s.status == Status.finished for s in phase_steps):
            phase.status = Status.finished
            phase.date_finished = safe_agg(
                max, (s.date_finished for s in phase_steps), step.date_finished)

            if any(s.result is Result.failed for s in phase_steps):
                phase.result = Result.failed
            else:
                phase.result = safe_agg(
                    max, (s.result for s in phase.steps), Result.unknown)

            db.session.add(phase)

        if db.session.is_modified(phase):
            db.session.commit()

        # sync artifacts
        for artifact in item.get('artifacts', ()):
            artifact, created = get_or_create(Artifact, where={
                'step': step,
                'name': artifact['fileName'],
            }, defaults={
                'project': step.project,
                'job': step.job,
                'data': artifact,
            })
            db.session.commit()
            sync_artifact.delay_if_needed(
                artifact_id=artifact.id.hex,
                task_id=artifact.id.hex,
                parent_task_id=step.id.hex,
            )

        # sync test results
        try:
            self._sync_test_results(
                step=step,
                job_name=job_name,
                build_no=build_no,
            )
        except Exception:
            db.session.rollback()
            self.logger.exception(
                'Failed to sync test results for %s #%s', job_name, build_no)
        else:
            db.session.commit()

        # sync console log
        try:
            result = True
            while result:
                result = self._sync_log(
                    jobstep=step,
                    name=step.label,
                    job_name=job_name,
                    build_no=build_no,
                )

        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                'Unable to sync console log for job step %r',
                step.id.hex)

    def sync_job(self, job):
        """
        Steps get created during the create_job and sync_step phases so we only
        rely on those steps syncing.
        """

    def sync_step(self, step):
        if step.data.get('queued'):
            self._sync_step_from_queue(step)
        else:
            self._sync_step_from_active(step)

    def sync_artifact(self, step, artifact):
        if self.sync_log_artifacts and artifact['fileName'].endswith('.log'):
            self._sync_artifact_as_log(step, artifact)
        if self.sync_xunit_artifacts and artifact['fileName'].endswith(XUNIT_FILENAMES):
            self._sync_artifact_as_xunit(step, artifact)
        if self.sync_coverage_artifacts and artifact['fileName'].endswith(COVERAGE_FILENAMES):
            self._sync_artifact_as_coverage(step, artifact)
        db.session.commit()

    def cancel_job(self, job):
        active_steps = JobStep.query.filter(
            JobStep.job == job,
            JobStep.status != Status.finished,
        )
        for step in active_steps:
            try:
                self.cancel_step(step)
            except UnrecoverableException:
                # assume the job no longer exists
                pass

        job.status = Status.finished
        job.result = Result.aborted
        db.session.add(job)

    def cancel_step(self, step):
        if step.data.get('build_no'):
            url = '/job/{}/{}/stop/'.format(
                step.data['job_name'], step.data['build_no'])
        else:
            url = '/queue/cancelItem?id={}'.format(step.data['item_id'])

        try:
            self._get_raw_response(url)
        except NotFound:
            raise UnrecoverableException('Unable to find job in Jenkins')

        step.status = Status.finished
        step.result = Result.aborted
        db.session.add(step)

    def get_job_parameters(self, job, target_id=None):
        if target_id is None:
            target_id = job.id.hex

        params = [
            {'name': 'CHANGES_BID', 'value': target_id},
        ]

        if job.build.source.revision_sha:
            params.append(
                {'name': 'REVISION', 'value': job.build.source.revision_sha},
            )

        if job.build.source.patch:
            params.append(
                {
                    'name': 'PATCH_URL',
                    'value': build_uri('/api/0/patches/{0}/?raw=1'.format(
                        job.build.source.patch.id.hex)),
                }
            )
        return params

    def create_job_from_params(self, target_id, params, job_name=None):
        if job_name is None:
            job_name = self.job_name

        if not job_name:
            raise UnrecoverableException('Missing Jenkins project configuration')

        json_data = {
            'parameter': params
        }

        # TODO: Jenkins will return a 302 if it cannot queue the job which I
        # believe implies that there is already a job with the same parameters
        # queued.
        self._get_response('/job/{}/build'.format(job_name), method='POST', data={
            'json': json.dumps(json_data),
        })

        # we retry for a period of time as Jenkins doesn't have strong consistency
        # guarantees and the job may not show up right away
        t = time.time() + 5
        job_data = None
        while time.time() < t:
            job_data = self._find_job(job_name, target_id)
            if job_data:
                break
            time.sleep(0.3)

        if job_data is None:
            raise Exception('Unable to find matching job after creation. GLHF')

        return job_data

    def get_default_job_phase_label(self, job, job_data):
        return 'Build {0}'.format(job_data['job_name'])

    def create_job(self, job):
        """
        Creates a job within Jenkins.

        Due to the way the API works, this consists of two steps:

        - Submitting the job
        - Polling for the newly created job to associate either a queue ID
          or a finalized build number.
        """
        params = self.get_job_parameters(job)
        job_data = self.create_job_from_params(
            target_id=job.id.hex,
            params=params,
        )

        if job_data['queued']:
            job.status = Status.queued
        else:
            job.status = Status.in_progress
        db.session.add(job)

        phase, created = get_or_create(JobPhase, where={
            'job': job,
            'label': self.get_default_job_phase_label(job, job_data),
            'project': job.project,
        }, defaults={
            'status': job.status,
        })

        if not created:
            return

        # TODO(dcramer): due to no unique constraints this section of code
        # presents a race condition when run concurrently
        step = self._create_job_step(
            phase=phase,
            status=job.status,
            data=job_data,
        )
        db.session.commit()

        sync_job_step.delay(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=job.id.hex,
        )

########NEW FILE########
__FILENAME__ = buildstep
from __future__ import absolute_import

from datetime import datetime, timedelta
from flask import current_app

from changes.backends.base import UnrecoverableException
from changes.buildsteps.base import BuildStep

from .builder import JenkinsBuilder
from .factory_builder import JenkinsFactoryBuilder
from .generic_builder import JenkinsGenericBuilder


class JenkinsBuildStep(BuildStep):
    def __init__(self, job_name=None):
        self.job_name = job_name

    def get_builder(self, app=current_app):
        return JenkinsBuilder(app=app, job_name=self.job_name)

    def get_label(self):
        return 'Execute job "{0}" on Jenkins'.format(self.job_name)

    def execute(self, job):
        builder = self.get_builder()
        builder.create_job(job)

    def update(self, job):
        builder = self.get_builder()
        builder.sync_job(job)

    def update_step(self, step):
        builder = self.get_builder()
        try:
            builder.sync_step(step)
        except UnrecoverableException:
            # bail if the step has been pending for too long as its likely
            # Jenkins fell over
            if step.date_created < datetime.utcnow() - timedelta(minutes=5):
                return
            raise

    def cancel(self, job):
        builder = self.get_builder()
        builder.cancel_job(job)

    def fetch_artifact(self, step, artifact):
        builder = self.get_builder()
        builder.sync_artifact(step, artifact)


class JenkinsFactoryBuildStep(JenkinsBuildStep):
    def __init__(self, job_name=None, downstream_job_names=()):
        self.job_name = job_name
        self.downstream_job_names = downstream_job_names

    def get_builder(self, app=current_app):
        return JenkinsFactoryBuilder(
            app=app,
            job_name=self.job_name,
            downstream_job_names=self.downstream_job_names,
        )


class JenkinsGenericBuildStep(JenkinsBuildStep):
    def __init__(self, job_name, script, cluster, path=''):
        self.job_name = job_name
        self.script = script
        self.cluster = cluster
        self.path = path

    def get_builder(self, app=current_app):
        return JenkinsGenericBuilder(
            app=app,
            job_name=self.job_name,
            script=self.script,
            cluster=self.cluster,
            path=self.path,
        )

########NEW FILE########
__FILENAME__ = collector
from __future__ import absolute_import

from flask import current_app
from hashlib import md5

from changes.backends.jenkins.buildstep import JenkinsBuildStep
from changes.backends.jenkins.generic_builder import JenkinsGenericBuilder
from changes.config import db
from changes.constants import Status
from changes.db.utils import get_or_create
from changes.jobs.sync_job_step import sync_job_step
from changes.models import JobPhase, JobStep


class JenkinsCollectorBuilder(JenkinsGenericBuilder):
    def get_default_job_phase_label(self, job, job_data):
        return 'Collect Jobs'


class JenkinsCollectorBuildStep(JenkinsBuildStep):
    """
    Fires off a generic job with parameters:

        CHANGES_BID = UUID
        CHANGES_PID = project slug
        REPO_URL    = repository URL
        REPO_VCS    = hg/git
        REVISION    = sha/id of revision
        PATCH_URL   = patch to apply, if available
        SCRIPT      = command to run

    A "jobs.json" is expected to be collected as an artifact with the following
    values:

        {
            "phase": "Name of phase",
            "jobs": [
                {"name": "Optional name",
                 "cmd": "echo 1"},
                {"cmd": "py.test --junit=junit.xml"}
            ]
        }

    For each job listed, a new generic task will be executed grouped under the
    given phase name.
    """
    # TODO(dcramer): longer term we'd rather have this create a new phase which
    # actually executes a different BuildStep (e.g. of order + 1), but at the
    # time of writing the system only supports a single build step.

    def __init__(self, job_name=None, script=None, cluster=None):
        self.job_name = job_name
        self.script = script
        self.cluster = cluster

    def get_label(self):
        return 'Collect jobs from job "{0}" on Jenkins'.format(self.job_name)

    def get_builder(self, app=current_app):
        return JenkinsCollectorBuilder(
            app=app,
            job_name=self.job_name,
            script=self.script,
            cluster=self.cluster,
        )

    def fetch_artifact(self, step, artifact):
        if artifact['fileName'] == 'jobs.json':
            self._expand_jobs(step, artifact)
        else:
            builder = self.get_builder()
            builder.sync_artifact(step, artifact)

    def _expand_jobs(self, step, artifact):
        builder = self.get_builder()
        artifact_data = builder.fetch_artifact(step, artifact)
        phase_config = artifact_data.json()

        assert phase_config['phase']
        assert phase_config['jobs']

        phase, created = get_or_create(JobPhase, where={
            'job': step.job,
            'project': step.project,
            'label': phase_config['phase'],
        }, defaults={
            'status': Status.queued,
        })

        for job_config in phase_config['jobs']:
            assert job_config['cmd']
            self._expand_job(phase, job_config)

    def _expand_job(self, phase, job_config):
        label = job_config.get('name') or md5(job_config['cmd']).hexdigest()

        step, created = get_or_create(JobStep, where={
            'job': phase.job,
            'project': phase.project,
            'phase': phase,
            'label': label,
        }, defaults={
            'data': {
                'cmd': job_config['cmd'],
                'job_name': self.job_name,
                'build_no': None,
            },
            'status': Status.queued,
        })

        # TODO(dcramer): due to no unique constraints this section of code
        # presents a race condition when run concurrently
        if not step.data.get('build_no'):
            builder = self.get_builder()
            params = builder.get_job_parameters(
                step.job, script=step.data['cmd'], target_id=step.id.hex)

            job_data = builder.create_job_from_params(
                target_id=step.id.hex,
                params=params,
                job_name=step.data['job_name'],
            )
            step.data.update(job_data)
            db.session.add(step)
            db.session.commit()

        sync_job_step.delay_if_needed(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=phase.job.id.hex,
        )

########NEW FILE########
__FILENAME__ = test_collector
from __future__ import absolute_import

from collections import defaultdict
from flask import current_app
from hashlib import md5
from operator import itemgetter

from changes.api.client import api_client
from changes.backends.jenkins.buildsteps.collector import (
    JenkinsCollectorBuilder, JenkinsCollectorBuildStep
)
from changes.config import db
from changes.constants import Status
from changes.db.utils import get_or_create
from changes.jobs.sync_job_step import sync_job_step
from changes.models import JobPhase, JobStep


class JenkinsTestCollectorBuilder(JenkinsCollectorBuilder):
    def get_default_job_phase_label(self, job, job_data):
        return 'Collect Tests'


class JenkinsTestCollectorBuildStep(JenkinsCollectorBuildStep):
    """
    Fires off a generic job with parameters:

        CHANGES_BID = UUID
        CHANGES_PID = project slug
        REPO_URL    = repository URL
        REPO_VCS    = hg/git
        REVISION    = sha/id of revision
        PATCH_URL   = patch to apply, if available
        SCRIPT      = command to run

    A "tests.json" is expected to be collected as an artifact with the following
    values:

        {
            "phase": "optional phase name",
            "cmd": "py.test --junit=junit.xml {test_names}",
            "path": "",
            "tests": [
                "foo.bar.test_baz",
                "foo.bar.test_bar"
            ]
        }

    The collected tests will be sorted and partitioned evenly across a set number
    of shards with the <cmd> value being passed a space-delimited list of tests.
    """
    # TODO(dcramer): longer term we'd rather have this create a new phase which
    # actually executes a different BuildStep (e.g. of order + 1), but at the
    # time of writing the system only supports a single build step.
    def __init__(self, job_name=None, script=None, cluster=None, max_shards=10):
        self.job_name = job_name
        self.script = script
        self.cluster = cluster
        self.max_shards = max_shards

    def get_builder(self, app=current_app):
        return JenkinsTestCollectorBuilder(
            app=app,
            job_name=self.job_name,
            script=self.script,
            cluster=self.cluster,
        )

    def get_label(self):
        return 'Collect tests from job "{0}" on Jenkins'.format(self.job_name)

    def fetch_artifact(self, step, artifact):
        if artifact['fileName'].endswith('tests.json'):
            self._expand_jobs(step, artifact)
        else:
            builder = self.get_builder()
            builder.sync_artifact(step, artifact)

    def get_test_stats(self, project):
        response = api_client.get('/projects/{project}/'.format(
            project=project.slug))
        last_build = response['lastPassingBuild']

        if not last_build:
            return {}, 0

        response = api_client.get('/builds/{build}/tests/?per_page='.format(
            build=last_build['id']))

        results = defaultdict(int)
        total_duration = 0
        test_count = 0
        for test in response:
            results[test['name']] += test['duration']
            results[test['package']] += test['duration']
            total_duration += test['duration']
            test_count += 1

        # the build report can contain different test suites so this isnt the
        # most accurate
        if total_duration > 0:
            avg_test_time = int(total_duration / test_count)
        else:
            avg_test_time = 0

        return results, avg_test_time

    def _expand_jobs(self, step, artifact):
        builder = self.get_builder()
        artifact_data = builder.fetch_artifact(step, artifact)
        phase_config = artifact_data.json()

        assert phase_config['cmd']
        assert '{test_names}' in phase_config['cmd']
        assert phase_config['tests']

        test_stats, avg_test_time = self.get_test_stats(step.project)

        def get_test_duration(test):
            return test_stats.get(test, avg_test_time)

        groups = [[] for _ in range(self.max_shards)]
        weights = [0] * self.max_shards
        weighted_tests = [(get_test_duration(t), t) for t in phase_config['tests']]
        for weight, test in sorted(weighted_tests, reverse=True):
            low_index, _ = min(enumerate(weights), key=itemgetter(1))
            weights[low_index] += 1 + weight
            groups[low_index].append(test)

        phase, created = get_or_create(JobPhase, where={
            'job': step.job,
            'project': step.project,
            'label': phase_config.get('phase') or 'Test',
        }, defaults={
            'status': Status.queued,
        })
        db.session.commit()

        for test_list in groups:
            self._expand_job(phase, {
                'tests': test_list,
                'cmd': phase_config['cmd'],
                'path': phase_config.get('path', ''),
            })

    def _expand_job(self, phase, job_config):
        assert job_config['tests']

        test_names = ' '.join(job_config['tests'])
        label = md5(test_names).hexdigest()

        step, created = get_or_create(JobStep, where={
            'job': phase.job,
            'project': phase.project,
            'phase': phase,
            'label': label,
        }, defaults={
            'data': {
                'cmd': job_config['cmd'],
                'path': job_config['path'],
                'tests': job_config['tests'],
                'job_name': self.job_name,
                'build_no': None,
            },
            'status': Status.queued,
        })

        # TODO(dcramer): due to no unique constraints this section of code
        # presents a race condition when run concurrently
        if not step.data.get('build_no'):
            builder = self.get_builder()
            params = builder.get_job_parameters(
                step.job,
                script=step.data['cmd'].format(
                    test_names=test_names,
                ),
                target_id=step.id.hex,
                path=step.data['path'],
            )

            job_data = builder.create_job_from_params(
                target_id=step.id.hex,
                params=params,
                job_name=step.data['job_name'],
            )
            step.data.update(job_data)
            db.session.add(step)

        db.session.commit()

        sync_job_step.delay_if_needed(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=phase.job.id.hex,
        )

########NEW FILE########
__FILENAME__ = factory_builder
from __future__ import absolute_import, division

import re

from changes.config import db
from changes.db.utils import get_or_create
from changes.jobs.sync_job_step import sync_job_step
from changes.models import JobPhase

from .builder import JenkinsBuilder

BASE_XPATH = '/freeStyleProject/build[action/cause/upstreamProject="{upstream_job}" and action/cause/upstreamBuild="{build_no}"]/number'
DOWNSTREAM_XML_RE = re.compile(r'<number>(\d+)</number>')


class JenkinsFactoryBuilder(JenkinsBuilder):
    def __init__(self, *args, **kwargs):
        self.downstream_job_names = kwargs.pop('downstream_job_names', ())
        super(JenkinsFactoryBuilder, self).__init__(*args, **kwargs)

    def _get_downstream_jobs(self, step, downstream_job_name):
        xpath = BASE_XPATH.format(
            upstream_job=step.data['job_name'],
            build_no=step.data['build_no']
        )
        response = self._get_raw_response('/job/{job_name}/api/xml/'.format(
            job_name=downstream_job_name,
        ), params={
            'depth': 1,
            'xpath': xpath,
            'wrapper': 'a',
        })
        if not response:
            return []

        return map(int, DOWNSTREAM_XML_RE.findall(response))

    def sync_step(self, step):
        if step.data.get('job_name') != self.job_name:
            return super(JenkinsFactoryBuilder, self).sync_step(step)

        job = step.job

        # for any downstream jobs, pull their results using xpath magic
        for downstream_job_name in self.downstream_job_names:
            downstream_build_nos = self._get_downstream_jobs(step, downstream_job_name)

            if not downstream_build_nos:
                continue

            phase, created = get_or_create(JobPhase, where={
                'job': job,
                'label': downstream_job_name,
            }, defaults={
                'project_id': job.project_id,
            })
            db.session.commit()

            for build_no in downstream_build_nos:
                # XXX(dcramer): ideally we would grab this with the first query
                # but because we dont want to rely on an XML parser, we're doing
                # a second http request for build details
                downstream_step = self._create_job_step(
                    phase, downstream_job_name, build_no)

                db.session.commit()

                sync_job_step.delay_if_needed(
                    step_id=downstream_step.id.hex,
                    task_id=downstream_step.id.hex,
                    parent_task_id=job.id.hex,
                )

        return super(JenkinsFactoryBuilder, self).sync_step(step)

########NEW FILE########
__FILENAME__ = generic_builder
from .builder import JenkinsBuilder


class JenkinsGenericBuilder(JenkinsBuilder):
    def __init__(self, *args, **kwargs):
        self.script = kwargs.pop('script')
        self.cluster = kwargs.pop('cluster')
        self.path = kwargs.pop('path', '')
        super(JenkinsGenericBuilder, self).__init__(*args, **kwargs)

    def get_job_parameters(self, job, script=None, target_id=None, path=None):
        params = super(JenkinsGenericBuilder, self).get_job_parameters(
            job, target_id=target_id)

        if path is None:
            path = self.path

        if script is None:
            script = self.script

        project = job.project
        repository = project.repository

        vcs = repository.get_vcs()
        if vcs:
            repo_url = vcs.remote_url
        else:
            repo_url = repository.url

        params.extend([
            {'name': 'CHANGES_PID', 'value': project.slug},
            {'name': 'REPO_URL', 'value': repo_url},
            {'name': 'SCRIPT', 'value': script},
            {'name': 'REPO_VCS', 'value': repository.backend.name},
            {'name': 'CLUSTER', 'value': self.cluster},
            {'name': 'WORK_PATH', 'value': path},
        ])

        return params

########NEW FILE########
__FILENAME__ = base
from __future__ import absolute_import


class BuildStep(object):
    def get_label(self):
        raise NotImplementedError

    def execute(self, job):
        """
        Given a new job, execute it (either sync or async), and report the
        results or yield to an update step.
        """
        raise NotImplementedError

    def update(self, job):
        raise NotImplementedError

    def update_step(self, step):
        raise NotImplementedError

    def cancel(self, job):
        raise NotImplementedError

    def fetch_artifact(self, step, artifact):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = dummy
from __future__ import absolute_import

from changes.buildsteps.base import BuildStep
from changes.config import db
from changes.constants import Status, Result


class DummyBuildStep(BuildStep):
    def get_label(self):
        return 'do nothing'

    def execute(self, job):
        job.status = Status.finished
        job.result = Result.aborted
        db.session.add(job)

    def update(self, job):
        job.status = Status.finished
        job.result = Result.aborted
        db.session.add(job)

    def update_step(self, step):
        step.status = Status.finished
        step.result = Result.aborted
        db.session.add(step)

    def cancel(self, job):
        job.status = Status.finished
        job.result = Result.aborted
        db.session.add(job)

########NEW FILE########
__FILENAME__ = config
import changes
import logging
import flask
import os
import os.path
import warnings

from celery.signals import task_postrun
from datetime import timedelta
from flask import request, session
from flask.ext.sqlalchemy import SQLAlchemy
from flask_debugtoolbar import DebugToolbarExtension
from flask_mail import Mail
from kombu import Exchange, Queue
from raven.contrib.flask import Sentry
from urlparse import urlparse
from werkzeug.contrib.fixers import ProxyFix

from changes.constants import PROJECT_ROOT
from changes.api.controller import APIController
from changes.ext.celery import Celery
from changes.ext.redis import Redis
from changes.url_converters.uuid import UUIDConverter

# because foo.in_([]) ever executing is a bad idea
from sqlalchemy.exc import SAWarning
warnings.simplefilter('error', SAWarning)


class ChangesDebugToolbarExtension(DebugToolbarExtension):
    def _show_toolbar(self):
        if '__trace__' in request.args:
            return True
        return super(ChangesDebugToolbarExtension, self)._show_toolbar()

    def process_response(self, response):
        real_request = request._get_current_object()

        # If the http response code is 200 then we process to add the
        # toolbar to the returned html response.
        if '__trace__' in real_request.args:
            for panel in self.debug_toolbars[real_request].panels:
                panel.process_response(real_request, response)

            if response.is_sequence:
                toolbar_html = self.debug_toolbars[real_request].render_toolbar()
                response.headers['content-type'] = 'text/html'
                response.response = [toolbar_html]
                response.content_length = len(toolbar_html)

        return response

db = SQLAlchemy(session_options={})
api = APIController(prefix='/api/0')
mail = Mail()
queue = Celery()
redis = Redis()
sentry = Sentry(logging=True, level=logging.ERROR)


def create_app(_read_config=True, **config):
    app = flask.Flask(__name__,
                      static_folder=None,
                      template_folder=os.path.join(PROJECT_ROOT, 'templates'))

    app.wsgi_app = ProxyFix(app.wsgi_app)
    # app.wsgi_app = TracerMiddleware(app.wsgi_app, app)

    # This key is insecure and you should override it on the server
    app.config['SECRET_KEY'] = 't\xad\xe7\xff%\xd2.\xfe\x03\x02=\xec\xaf\\2+\xb8=\xf7\x8a\x9aLD\xb1'

    app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///changes'
    app.config['SQLALCHEMY_POOL_SIZE'] = 60
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = 20
    # required for flask-debugtoolbar
    app.config['SQLALCHEMY_RECORD_QUERIES'] = True

    app.config['REDIS_URL'] = 'redis://localhost/0'
    app.config['DEBUG'] = True
    app.config['HTTP_PORT'] = 5000
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    app.config['API_TRACEBACKS'] = True

    app.config['CELERY_ACCEPT_CONTENT'] = ['changes_json']
    app.config['CELERY_ACKS_LATE'] = True
    app.config['CELERY_BROKER_URL'] = 'redis://localhost/0'
    app.config['CELERY_DEFAULT_QUEUE'] = "default"
    app.config['CELERY_DEFAULT_EXCHANGE'] = "default"
    app.config['CELERY_DEFAULT_EXCHANGE_TYPE'] = "direct"
    app.config['CELERY_DEFAULT_ROUTING_KEY'] = "default"
    app.config['CELERY_DISABLE_RATE_LIMITS'] = True
    app.config['CELERY_IGNORE_RESULT'] = True
    app.config['CELERY_RESULT_BACKEND'] = None
    app.config['CELERY_RESULT_SERIALIZER'] = 'changes_json'
    app.config['CELERY_SEND_EVENTS'] = False
    app.config['CELERY_TASK_RESULT_EXPIRES'] = 1
    app.config['CELERY_TASK_SERIALIZER'] = 'changes_json'
    app.config['CELERYD_PREFETCH_MULTIPLIER'] = 1
    app.config['CELERYD_MAX_TASKS_PER_CHILD'] = 10000

    app.config['CELERY_QUEUES'] = (
        Queue('job.sync', routing_key='job.sync'),
        Queue('job.create', routing_key='job.create'),
        Queue('celery', routing_key='celery'),
        Queue('events', routing_key='events'),
        Queue('default', routing_key='default'),
        Queue('repo.sync', Exchange('fanout', 'fanout'), routing_key='repo.sync'),
    )
    app.config['CELERY_ROUTES'] = {
        'create_job': {
            'queue': 'job.create',
            'routing_key': 'job.create',
        },
        'sync_job': {
            'queue': 'job.sync',
            'routing_key': 'job.sync',
        },
        'sync_job_step': {
            'queue': 'job.sync',
            'routing_key': 'job.sync',
        },
        'sync_build': {
            'queue': 'job.sync',
            'routing_key': 'job.sync',
        },
        'check_repos': {
            'queue': 'repo.sync',
            'routing_key': 'repo.sync',
        },
        'sync_repo': {
            'queue': 'repo.sync',
            'routing_key': 'repo.sync',
        },
        'run_event_listener': {
            'queue': 'events',
            'routing_key': 'events',
        },
        'fire_signal': {
            'queue': 'events',
            'routing_key': 'events',
        },
    }

    app.config['EVENT_LISTENERS'] = (
        ('changes.listeners.mail.job_finished_handler', 'job.finished'),
        ('changes.listeners.green_build.build_finished_handler', 'build.finished'),
        ('changes.listeners.hipchat.build_finished_handler', 'build.finished'),
        ('changes.listeners.build_revision.revision_created_handler', 'revision.created'),
    )

    app.config['DEBUG_TB_ENABLED'] = True

    # celerybeat must be running for our cleanup tasks to execute
    # e.g. celery worker -B
    app.config['CELERYBEAT_SCHEDULE'] = {
        'cleanup-tasks': {
            'task': 'cleanup_tasks',
            'schedule': timedelta(minutes=1),
        },
        'check-repos': {
            'task': 'check_repos',
            'schedule': timedelta(minutes=5),
        },
    }
    app.config['CELERY_TIMEZONE'] = 'UTC'

    app.config['SENTRY_DSN'] = None

    app.config['JENKINS_AUTH'] = None
    app.config['JENKINS_URL'] = None
    app.config['JENKINS_TOKEN'] = None

    app.config['KOALITY_URL'] = None
    app.config['KOALITY_API_KEY'] = None

    app.config['GOOGLE_CLIENT_ID'] = None
    app.config['GOOGLE_CLIENT_SECRET'] = None
    app.config['GOOGLE_DOMAIN'] = None

    app.config['REPO_ROOT'] = None

    app.config['MAIL_DEFAULT_SENDER'] = 'changes@localhost'
    app.config['BASE_URI'] = None

    app.config.update(config)

    if _read_config:
        if os.environ.get('CHANGES_CONF'):
            # CHANGES_CONF=/etc/changes.conf.py
            app.config.from_envvar('CHANGES_CONF')
        else:
            # Look for ~/.changes/changes.conf.py
            path = os.path.normpath(os.path.expanduser('~/.changes/changes.conf.py'))
            app.config.from_pyfile(path, silent=True)

    if not app.config['BASE_URI']:
        raise ValueError('You must set ``BASE_URI`` in your configuration.')

    parsed_url = urlparse(app.config['BASE_URI'])
    app.config.setdefault('SERVER_NAME', parsed_url.netloc)
    app.config.setdefault('PREFERRED_URL_SCHEME', parsed_url.scheme)

    if app.debug:
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    else:
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 30

    app.url_map.converters['uuid'] = UUIDConverter

    # init sentry first
    sentry.init_app(app)

    @app.before_request
    def capture_user(*args, **kwargs):
        if 'uid' in session:
            sentry.client.user_context({
                'id': session['uid'],
                'email': session['email'],
            })

    api.init_app(app)
    db.init_app(app)
    mail.init_app(app)
    queue.init_app(app)
    redis.init_app(app)
    configure_debug_toolbar(app)

    from raven.contrib.celery import register_signal, register_logger_signal
    register_signal(sentry.client)
    register_logger_signal(sentry.client)

    # configure debug routes first
    if app.debug:
        configure_debug_routes(app)

    configure_templates(app)

    # TODO: these can be moved to wsgi app entrypoints
    configure_api_routes(app)
    configure_web_routes(app)

    configure_jobs(app)

    return app


def configure_debug_toolbar(app):
    toolbar = ChangesDebugToolbarExtension(app)
    return toolbar


def configure_templates(app):
    from changes.utils.times import duration

    app.jinja_env.filters['duration'] = duration


def configure_api_routes(app):
    from changes.api.auth_index import AuthIndexAPIView
    from changes.api.author_build_index import AuthorBuildIndexAPIView
    from changes.api.build_comment_index import BuildCommentIndexAPIView
    from changes.api.build_details import BuildDetailsAPIView
    from changes.api.build_index import BuildIndexAPIView
    from changes.api.build_mark_seen import BuildMarkSeenAPIView
    from changes.api.build_cancel import BuildCancelAPIView
    from changes.api.build_coverage import BuildTestCoverageAPIView
    from changes.api.build_coverage_stats import BuildTestCoverageStatsAPIView
    from changes.api.build_restart import BuildRestartAPIView
    from changes.api.build_retry import BuildRetryAPIView
    from changes.api.build_test_index import BuildTestIndexAPIView
    from changes.api.build_test_index_failures import BuildTestIndexFailuresAPIView
    from changes.api.build_test_index_counts import BuildTestIndexCountsAPIView
    from changes.api.change_details import ChangeDetailsAPIView
    from changes.api.change_index import ChangeIndexAPIView
    from changes.api.cluster_details import ClusterDetailsAPIView
    from changes.api.cluster_index import ClusterIndexAPIView
    from changes.api.cluster_nodes import ClusterNodesAPIView
    from changes.api.job_details import JobDetailsAPIView
    from changes.api.job_log_details import JobLogDetailsAPIView
    from changes.api.jobphase_index import JobPhaseIndexAPIView
    from changes.api.node_details import NodeDetailsAPIView
    from changes.api.node_index import NodeIndexAPIView
    from changes.api.node_job_index import NodeJobIndexAPIView
    from changes.api.patch_details import PatchDetailsAPIView
    from changes.api.plan_details import PlanDetailsAPIView
    from changes.api.plan_index import PlanIndexAPIView
    from changes.api.plan_project_index import PlanProjectIndexAPIView
    from changes.api.plan_step_index import PlanStepIndexAPIView
    from changes.api.project_build_index import ProjectBuildIndexAPIView
    from changes.api.project_build_search import ProjectBuildSearchAPIView
    from changes.api.project_commit_details import ProjectCommitDetailsAPIView
    from changes.api.project_commit_index import ProjectCommitIndexAPIView
    from changes.api.project_coverage_group_index import ProjectCoverageGroupIndexAPIView
    from changes.api.project_index import ProjectIndexAPIView
    from changes.api.project_options_index import ProjectOptionsIndexAPIView
    from changes.api.project_stats import ProjectStatsAPIView
    from changes.api.project_test_details import ProjectTestDetailsAPIView
    from changes.api.project_test_group_index import ProjectTestGroupIndexAPIView
    from changes.api.project_test_index import ProjectTestIndexAPIView
    from changes.api.project_details import ProjectDetailsAPIView
    from changes.api.project_source_details import ProjectSourceDetailsAPIView
    from changes.api.project_source_build_index import ProjectSourceBuildIndexAPIView
    from changes.api.step_details import StepDetailsAPIView
    from changes.api.task_details import TaskDetailsAPIView
    from changes.api.task_index import TaskIndexAPIView
    from changes.api.testcase_details import TestCaseDetailsAPIView

    api.add_resource(AuthIndexAPIView, '/auth/')
    api.add_resource(BuildIndexAPIView, '/builds/')
    api.add_resource(AuthorBuildIndexAPIView, '/authors/<author_id>/builds/')
    api.add_resource(BuildCommentIndexAPIView, '/builds/<uuid:build_id>/comments/')
    api.add_resource(BuildDetailsAPIView, '/builds/<uuid:build_id>/')
    api.add_resource(BuildMarkSeenAPIView, '/builds/<uuid:build_id>/mark_seen/')
    api.add_resource(BuildCancelAPIView, '/builds/<uuid:build_id>/cancel/')
    api.add_resource(BuildRestartAPIView, '/builds/<uuid:build_id>/restart/')
    api.add_resource(BuildRetryAPIView, '/builds/<uuid:build_id>/retry/')
    api.add_resource(BuildTestIndexAPIView, '/builds/<uuid:build_id>/tests/')
    api.add_resource(BuildTestIndexFailuresAPIView, '/builds/<uuid:build_id>/tests/failures')
    api.add_resource(BuildTestIndexCountsAPIView, '/builds/<uuid:build_id>/tests/counts')
    api.add_resource(BuildTestCoverageAPIView, '/builds/<uuid:build_id>/coverage/')
    api.add_resource(BuildTestCoverageStatsAPIView, '/builds/<uuid:build_id>/stats/coverage/')
    api.add_resource(ClusterIndexAPIView, '/clusters/')
    api.add_resource(ClusterDetailsAPIView, '/clusters/<uuid:cluster_id>/')
    api.add_resource(ClusterNodesAPIView, '/clusters/<uuid:cluster_id>/nodes/')
    api.add_resource(JobDetailsAPIView, '/jobs/<uuid:job_id>/')
    api.add_resource(JobLogDetailsAPIView, '/jobs/<uuid:job_id>/logs/<uuid:source_id>/')
    api.add_resource(JobPhaseIndexAPIView, '/jobs/<uuid:job_id>/phases/')
    api.add_resource(ChangeIndexAPIView, '/changes/')
    api.add_resource(ChangeDetailsAPIView, '/changes/<uuid:change_id>/')
    api.add_resource(NodeDetailsAPIView, '/nodes/<uuid:node_id>/')
    api.add_resource(NodeIndexAPIView, '/nodes/')
    api.add_resource(NodeJobIndexAPIView, '/nodes/<uuid:node_id>/jobs/')
    api.add_resource(PatchDetailsAPIView, '/patches/<uuid:patch_id>/')
    api.add_resource(PlanIndexAPIView, '/plans/')
    api.add_resource(PlanDetailsAPIView, '/plans/<uuid:plan_id>/')
    api.add_resource(PlanProjectIndexAPIView, '/plans/<uuid:plan_id>/projects/')
    api.add_resource(PlanStepIndexAPIView, '/plans/<uuid:plan_id>/steps/')
    api.add_resource(ProjectIndexAPIView, '/projects/')
    api.add_resource(ProjectDetailsAPIView, '/projects/<project_id>/')
    api.add_resource(ProjectBuildIndexAPIView, '/projects/<project_id>/builds/')
    api.add_resource(ProjectBuildSearchAPIView, '/projects/<project_id>/builds/search/')
    api.add_resource(ProjectCommitIndexAPIView, '/projects/<project_id>/commits/')
    api.add_resource(ProjectCommitDetailsAPIView, '/projects/<project_id>/commits/<commit_id>/')
    api.add_resource(ProjectCoverageGroupIndexAPIView, '/projects/<project_id>/coveragegroups/')
    api.add_resource(ProjectOptionsIndexAPIView, '/projects/<project_id>/options/')
    api.add_resource(ProjectStatsAPIView, '/projects/<project_id>/stats/')
    api.add_resource(ProjectTestIndexAPIView, '/projects/<project_id>/tests/')
    api.add_resource(ProjectTestGroupIndexAPIView, '/projects/<project_id>/testgroups/')
    api.add_resource(ProjectTestDetailsAPIView, '/projects/<project_id>/tests/<test_hash>/')
    api.add_resource(ProjectSourceDetailsAPIView, '/projects/<project_id>/sources/<source_id>/')
    api.add_resource(ProjectSourceBuildIndexAPIView, '/projects/<project_id>/sources/<source_id>/builds/')
    api.add_resource(StepDetailsAPIView, '/steps/<uuid:step_id>/')
    api.add_resource(TestCaseDetailsAPIView, '/tests/<uuid:test_id>/')
    api.add_resource(TaskIndexAPIView, '/tasks/')
    api.add_resource(TaskDetailsAPIView, '/tasks/<uuid:task_id>/')


def configure_web_routes(app):
    from changes.web.auth import AuthorizedView, LoginView, LogoutView
    from changes.web.index import IndexView
    from changes.web.static import StaticView

    if app.debug:
        static_root = os.path.join(PROJECT_ROOT, 'static')
        revision = '0'
    else:
        static_root = os.path.join(PROJECT_ROOT, 'static-built')
        revision = changes.get_revision() or '0'

    app.add_url_rule(
        '/static/' + revision + '/<path:filename>',
        view_func=StaticView.as_view('static', root=static_root))
    app.add_url_rule(
        '/partials/<path:filename>',
        view_func=StaticView.as_view('partials', root=os.path.join(PROJECT_ROOT, 'partials')))

    app.add_url_rule(
        '/auth/login/', view_func=LoginView.as_view('login', authorized_url='authorized'))
    app.add_url_rule(
        '/auth/logout/', view_func=LogoutView.as_view('logout', complete_url='index'))
    app.add_url_rule(
        '/auth/complete/', view_func=AuthorizedView.as_view('authorized', authorized_url='authorized', complete_url='index'))

    app.add_url_rule(
        '/<path:path>', view_func=IndexView.as_view('index-path'))
    app.add_url_rule(
        '/', view_func=IndexView.as_view('index'))


def configure_debug_routes(app):
    from changes.debug.reports.build import BuildReportMailView
    from changes.debug.mail.job_result import JobResultMailView

    app.add_url_rule(
        '/debug/mail/report/build/', view_func=BuildReportMailView.as_view('debug-build-report'))
    app.add_url_rule(
        '/debug/mail/result/job/<job_id>/', view_func=JobResultMailView.as_view('debug-build-result'))


def configure_jobs(app):
    from changes.jobs.check_repos import check_repos
    from changes.jobs.cleanup_tasks import cleanup_tasks
    from changes.jobs.create_job import create_job
    from changes.jobs.signals import (
        fire_signal, run_event_listener
    )
    from changes.jobs.sync_artifact import sync_artifact
    from changes.jobs.sync_build import sync_build
    from changes.jobs.sync_job import sync_job
    from changes.jobs.sync_job_step import sync_job_step
    from changes.jobs.sync_repo import sync_repo
    from changes.jobs.update_project_stats import (
        update_project_stats, update_project_plan_stats)

    queue.register('check_repos', check_repos)
    queue.register('cleanup_tasks', cleanup_tasks)
    queue.register('create_job', create_job)
    queue.register('fire_signal', fire_signal)
    queue.register('run_event_listener', run_event_listener)
    queue.register('sync_artifact', sync_artifact)
    queue.register('sync_build', sync_build)
    queue.register('sync_job', sync_job)
    queue.register('sync_job_step', sync_job_step)
    queue.register('sync_repo', sync_repo)
    queue.register('update_project_stats', update_project_stats)
    queue.register('update_project_plan_stats', update_project_plan_stats)

    @task_postrun.connect
    def cleanup_session(*args, **kwargs):
        """
        Emulate a request cycle for each task to ensure the session objects
        get cleaned up as expected.
        """
        db.session.commit()
        db.session.remove()

    def register_changes_json():
        from kombu.serialization import register
        from kombu.utils.encoding import bytes_t
        from json import dumps, loads
        from uuid import UUID

        def _loads(obj):
            if isinstance(obj, UUID):
                obj = obj.hex
            elif isinstance(obj, bytes_t):
                obj = obj.decode()
            elif isinstance(obj, buffer):
                obj = bytes(obj).decode()
            return loads(obj)

        register('changes_json', dumps, _loads,
                 content_type='application/json',
                 content_encoding='utf-8')

    register_changes_json()

########NEW FILE########
__FILENAME__ = constants
import os
from enum import Enum

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

NUM_PREVIOUS_RUNS = 50


class OrderedEnum(Enum):
    def __ge__(self, other):
        if type(self) is type(other):
            return self._value_ >= other._value_
        return NotImplemented

    def __gt__(self, other):
        if type(self) is type(other):
            return self._value_ > other._value_
        return NotImplemented

    def __le__(self, other):
        if type(self) is type(other):
            return self._value_ <= other._value_
        return NotImplemented

    def __lt__(self, other):
        if type(self) is type(other):
            return self._value_ < other._value_
        return NotImplemented


class Status(Enum):
    unknown = 0
    queued = 1
    in_progress = 2
    finished = 3
    collecting_results = 4

    def __str__(self):
        return STATUS_LABELS[self]


class Result(OrderedEnum):
    unknown = 0
    aborted = 5
    passed = 1
    skipped = 3
    failed = 2

    def __str__(self):
        return RESULT_LABELS[self]


class Provider(Enum):
    unknown = 0
    koality = 'koality'


class Cause(Enum):
    unknown = 0
    manual = 1
    push = 2
    retry = 3

    def __str__(self):
        return CAUSE_LABELS[self]


class ProjectStatus(Enum):
    unknown = 0
    active = 1
    inactive = 2


STATUS_LABELS = {
    Status.unknown: 'Unknown',
    Status.queued: 'Queued',
    Status.in_progress: 'In progress',
    Status.finished: 'Finished'
}

RESULT_LABELS = {
    Result.unknown: 'Unknown',
    Result.passed: 'Passed',
    Result.failed: 'Failed',
    Result.skipped: 'Skipped',
    Result.aborted: 'Aborted',
}

CAUSE_LABELS = {
    Cause.unknown: 'Unknown',
    Cause.manual: 'Manual',
    Cause.push: 'Code Push',
    Cause.retry: 'Retry',
}

IMPLEMENTATION_CHOICES = (
    'changes.buildsteps.dummy.DummyBuildStep',
    'changes.backends.jenkins.buildstep.JenkinsBuildStep',
    'changes.backends.jenkins.buildstep.JenkinsFactoryBuildStep',
    'changes.backends.jenkins.buildstep.JenkinsGenericBuildStep',
    'changes.backends.jenkins.buildsteps.collector.JenkinsCollectorBuildStep',
    'changes.backends.jenkins.buildsteps.test_collector.JenkinsTestCollectorBuildStep',
)

########NEW FILE########
__FILENAME__ = coalesce
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FunctionElement


class coalesce(FunctionElement):
    name = 'coalesce'


@compiles(coalesce, 'postgresql')
def compile(element, compiler, **kw):
    return "coalesce(%s)" % compiler.process(element.clauses)

########NEW FILE########
__FILENAME__ = enum
from sqlalchemy.types import TypeDecorator, INT


class Enum(TypeDecorator):
    impl = INT

    def __init__(self, enum=None, *args, **kwargs):
        self.enum = enum
        super(Enum, self).__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return value.value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif self.enum:
            return self.enum(value)
        return value

########NEW FILE########
__FILENAME__ = guid
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID
import uuid


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses Postgresql's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.

    """
    impl = CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value)
            else:
                # hexstring
                return "%.32x" % value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return uuid.UUID(value)

########NEW FILE########
__FILENAME__ = json
from __future__ import absolute_import

import json

from collections import MutableMapping

from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import TypeDecorator, Unicode


class MutableDict(Mutable, MutableMapping):
    def __init__(self, value):
        self.value = value or {}

    def __setitem__(self, key, value):
        self.value[key] = value
        self.changed()

    def __delitem__(self, key):
        del self.value[key]
        self.changed()

    def __getitem__(self, key):
        return self.value[key]

    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return iter(self.value)

    def __repr__(self):
        return repr(self.value)

    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to MutableDict."
        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value


class JSONEncodedDict(TypeDecorator):
    impl = Unicode

    def process_bind_param(self, value, dialect):
        if value:
            if isinstance(value, MutableDict):
                value = value.value
            return unicode(json.dumps(value))

        return u'{}'

    def process_result_value(self, value, dialect):
        if value:
            return json.loads(value)

        return {}

MutableDict.associate_with(JSONEncodedDict)

########NEW FILE########
__FILENAME__ = utils
from changes.config import db

from sqlalchemy.exc import IntegrityError


def try_create(model, where, defaults=None):
    if defaults is None:
        defaults = {}

    instance = model()
    for key, value in defaults.iteritems():
        setattr(instance, key, value)
    for key, value in where.iteritems():
        setattr(instance, key, value)
    try:
        with db.session.begin_nested():
            db.session.add(instance)
    except IntegrityError:
        return
    return instance


def try_update(model, where, values):
    result = db.session.query(type(model)).filter_by(
        **where
    ).update(values, synchronize_session=False)
    return result.rowcount > 0


def get_or_create(model, where, defaults=None):
    if defaults is None:
        defaults = {}

    created = False

    instance = model.query.filter_by(**where).limit(1).first()
    if instance is not None:
        return instance, created

    instance = try_create(model, where, defaults)
    if instance is None:
        instance = model.query.filter_by(**where).limit(1).first()
    else:
        created = True

    if instance is None:
        # this should never happen unless everything is broken
        raise Exception('Unable to get or create instance')

    return instance, created


def create_or_update(model, where, values=None):
    if values is None:
        values = {}

    created = False

    instance = model.query.filter_by(**where).limit(1).first()
    if instance is None:
        instance = try_create(model, where, values)
        if instance is None:
            instance = model.query.filter_by(**where).limit(1).first()
            if instance is None:
                raise Exception('Unable to create or update instance')
            update(instance, values)
        else:
            created = True
    else:
        update(instance, values)

    return instance, created


def create_or_get(model, where, values=None):
    if values is None:
        values = {}

    created = False

    instance = model.query.filter_by(**where).limit(1).first()
    if instance is None:
        instance = try_create(model, where, values)
        if instance is None:
            instance = model.query.filter_by(**where).limit(1).first()
        else:
            created = True

        if instance is None:
            raise Exception('Unable to get or create instance')

    return instance, created


def update(instance, values):
    for key, value in values.iteritems():
        if getattr(instance, key) != value:
            setattr(instance, key, value)
    db.session.add(instance)


def model_repr(*attrs):
    if 'id' not in attrs and 'pk' not in attrs:
        attrs = ('id',) + attrs

    def _repr(self):
        cls = type(self).__name__

        pairs = (
            '%s=%s' % (a, repr(getattr(self, a, None)))
            for a in attrs)

        return u'<%s at 0x%x: %s>' % (cls, id(self), ', '.join(pairs))

    return _repr

########NEW FILE########
__FILENAME__ = job_result
import toronado

from flask import render_template
from flask.views import MethodView
from jinja2 import Markup

from changes.models import Job
from changes.listeners.mail import MailNotificationHandler


class JobResultMailView(MethodView):
    def get(self, job_id):
        job = Job.query.get(job_id)

        assert job

        handler = MailNotificationHandler()

        parent = handler.get_parent(job)
        context = handler.get_context(job, parent)

        html_content = Markup(toronado.from_string(
            render_template('listeners/mail/notification.html', **context)
        ))

        return render_template('debug/email.html', html_content=html_content)

########NEW FILE########
__FILENAME__ = build
import toronado

from flask import render_template
from flask.views import MethodView
from jinja2 import Markup

from changes.models import Project
from changes.reports.build import BuildReport


class BuildReportMailView(MethodView):
    def get(self, path=''):
        projects = Project.query.all()

        report = BuildReport(projects)

        context = report.generate()

        html_content = Markup(toronado.from_string(
            render_template('email/build_report.html', **context)
        ))

        return render_template('debug/email.html', html_content=html_content)

########NEW FILE########
__FILENAME__ = celery
from __future__ import absolute_import

import logging

from celery import Celery as CeleryApp
from uuid import uuid4

from .container import Container


class _Celery(object):
    def __init__(self, app, options):
        celery = CeleryApp(app.import_name, broker=app.config['CELERY_BROKER_URL'])
        celery.conf.update(app.config)
        TaskBase = celery.Task

        class ContextTask(TaskBase):
            abstract = True

            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return TaskBase.__call__(self, *args, **kwargs)

        celery.Task = ContextTask

        self.app = app
        self.celery = celery
        self.tasks = {}
        self.logger = logging.getLogger(app.name + '.celery')

    def delay(self, name, args=None, kwargs=None, *fn_args, **fn_kwargs):
        # We don't assume the task is registered at this point, so manually
        # publish it
        self.logger.debug('Firing task %r args=%r kwargs=%r', name, args, kwargs)
        celery = self.celery
        if celery.conf.CELERY_ALWAYS_EAGER:
            task_id = uuid4()
            # we dont call out to delay() as it causes db rollbacks/etc
            celery.tasks[name].run(*args or (), **kwargs or {})
        else:
            with celery.producer_or_acquire() as P:
                task_id = P.publish_task(
                    task_name=name,
                    task_args=args,
                    task_kwargs=kwargs,
                    *fn_args, **fn_kwargs
                )
        return task_id

    def retry(self, name, *args, **kwargs):
        # unlike delay, we actually want to rely on Celery's retry logic
        # and because we can only execute this within a task, it's safe
        # to say that the task is actually registered
        kwargs.setdefault('throw', False)
        self.tasks[name].retry(*args, **kwargs)

    def get_task(self, name):
        return self.tasks[name]

    def register(self, name, func, **kwargs):
        # XXX(dcramer): hacky way to ensure the task gets registered so
        # celery knows how to execute it
        for key, value in self.app.config['CELERY_ROUTES'].get(name, {}).iteritems():
            kwargs.setdefault(key, value)

        self.tasks[name] = self.celery.task(func, name=name, **kwargs)


Celery = lambda **o: Container(_Celery, o, name='celery')

########NEW FILE########
__FILENAME__ = container
from flask import _app_ctx_stack


class ContainerState(object):
    def __init__(self, app, callback, options):
        self.app = app
        self.instance = callback(app, options)

    def __getattr__(self, name):
        return getattr(self.instance, name)


class ContainerMethod(object):
    """
    Proxies a method to an extension allowing us to bind the result
    to the correct application state.
    """
    def __init__(self, ext, name):
        self.ext = ext
        self.name = name

    def __call__(self, *args, **kwargs):
        state = self.ext.get_state()
        return getattr(state, self.name)(*args, **kwargs)


class Container(object):
    """
    Creates an extension container for app-bound execution of an object.

    >>> redis = Container(
    >>>     lambda app, kwargs: redis.StrictClient(**kwargs),
    >>>     {'host': 'localhost'})
    """
    def __init__(self, callback, options=None, name=None):
        self.callback = callback
        self.options = options or {}
        self.ident = name or id(self)
        self.app = None

    def __getattr__(self, name):
        state = self.get_state()
        attr = getattr(state, name)
        if callable(attr):
            method = ContainerMethod(self, name)
            method.__name__ = name
            method.__doc__ = name.__doc__
            return method
        return attr

    def init_app(self, app):
        self.app = app
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions[self.ident] = ContainerState(
            app=app,
            callback=self.callback,
            options=self.options,
        )

    def get_state(self, app=None):
        """Gets the state for the application"""
        if app is None:
            app = self.get_app()
        assert self.ident in app.extensions, \
            'The extension was not registered to the current ' \
            'application.  Please make sure to call init_app() first.'
        return app.extensions[self.ident]

    def get_app(self, reference_app=None):
        if reference_app is not None:
            return reference_app
        if self.app is not None:
            return self.app
        ctx = _app_ctx_stack.top
        if ctx is not None:
            return ctx.app
        raise RuntimeError('application not registered on '
                           'instance and no application bound '
                           'to current context')

########NEW FILE########
__FILENAME__ = redis
from __future__ import absolute_import

import logging
import redis

from contextlib import contextmanager
from random import random
from time import sleep

from .container import Container


class UnableToGetLock(Exception):
    pass


class _Redis(object):
    UnableToGetLock = UnableToGetLock

    def __init__(self, app, options):
        self.app = app
        self.redis = redis.from_url(app.config['REDIS_URL'])
        self.logger = logging.getLogger(app.name + '.redis')

    def __getattr__(self, name):
        return getattr(self.redis, name)

    @contextmanager
    def lock(self, lock_key, timeout=3, expire=None, nowait=False):
        conn = self.redis

        if expire is None:
            expire = timeout

        delay = 0.01 + random() / 10
        attempt = 0
        max_attempts = timeout / delay
        got_lock = None
        while not got_lock and attempt < max_attempts:
            pipe = conn.pipeline()
            pipe.setnx(lock_key, '')
            pipe.expire(lock_key, expire)
            got_lock = pipe.execute()[0]
            if not got_lock:
                if nowait:
                    break
                sleep(delay)
                attempt += 1

        self.logger.info('Acquiring lock on %s', lock_key)

        if not got_lock:
            raise self.UnableToGetLock('Unable to fetch lock on %s' % (lock_key,))

        try:
            yield
        finally:
            self.logger.info('Releasing lock on %s', lock_key)

            try:
                conn.delete(lock_key)
            except Exception as e:
                self.logger.exception(e)


Redis = lambda **o: Container(_Redis, o, name='redis')

########NEW FILE########
__FILENAME__ = base
class ArtifactHandler(object):
    def __init__(self, step):
        self.step = step

########NEW FILE########
__FILENAME__ = coverage
from __future__ import absolute_import, division

from collections import defaultdict
from hashlib import md5
from lxml import etree
from sqlalchemy.exc import IntegrityError

from changes.config import db, redis
from changes.models.filecoverage import FileCoverage
from changes.utils.diff_parser import DiffParser

from .base import ArtifactHandler


class CoverageHandler(ArtifactHandler):
    def process(self, fp):
        results = self.get_coverage(fp)

        for result in results:
            try:
                with db.session.begin_nested():
                    db.session.add(result)
            except IntegrityError:
                lock_key = 'coverage:{job_id}:{file_hash}'.format(
                    job_id=result.job_id.hex,
                    file_hash=md5(result.filename).hexdigest(),
                )
                with redis.lock(lock_key):
                    result = self.merge_coverage(result)
                    db.session.add(result)
            db.session.commit()

        return results

    def merge_coverage(self, new):
        existing = FileCoverage.query.filter(
            FileCoverage.job_id == new.job_id,
            FileCoverage.filename == new.filename,
        ).first()

        cov_data = []
        for lineno in range(max(len(existing.data), len(new.data))):
            try:
                old_cov = existing.data[lineno]
            except IndexError:
                pass

            try:
                new_cov = new.data[lineno]
            except IndexError:
                pass

            if old_cov == 'C' or new_cov == 'C':
                cov_data.append('C')
            elif old_cov == 'U' or new_cov == 'U':
                cov_data.append('U')
            else:
                cov_data.append('N')

        existing.data = ''.join(cov_data)

        self.add_file_stats(existing)

        return existing

    def process_diff(self):
        lines_by_file = defaultdict(set)
        try:
            source = self.step.job.build.source
        except AttributeError:
            return lines_by_file

        diff = source.generate_diff()

        if not diff:
            return lines_by_file

        diff_parser = DiffParser(diff)
        parsed_diff = diff_parser.parse()

        for file_diff in parsed_diff:
            for diff_chunk in file_diff['chunks']:
                if not file_diff['new_filename']:
                    continue

                lines_by_file[file_diff['new_filename'][2:]].update(
                    d['new_lineno'] for d in diff_chunk if d['action'] in ('add', 'del')
                )
        return lines_by_file

    def get_processed_diff(self):
        if not hasattr(self, '_processed_diff'):
            self._processed_diff = self.process_diff()
        return self._processed_diff

    def add_file_stats(self, result):
        diff_lines = self.get_processed_diff()[result.filename]

        lines_covered = 0
        lines_uncovered = 0
        diff_lines_covered = 0
        diff_lines_uncovered = 0

        for lineno, code in enumerate(result.data):
            # lineno is 1-based in diff
            line_in_diff = bool((lineno + 1) in diff_lines)
            if code == 'C':
                lines_covered += 1
                if line_in_diff:
                    diff_lines_covered += 1
            elif code == 'U':
                lines_uncovered += 1
                if line_in_diff:
                    diff_lines_uncovered += 1

        result.lines_covered = lines_covered
        result.lines_uncovered = lines_uncovered
        result.diff_lines_covered = diff_lines_covered
        result.diff_lines_uncovered = diff_lines_uncovered

    def get_coverage(self, fp):
        """
        Return a phabricator-capable coverage mapping.

        >>> {
        >>>     'foo.py': 'NNNUUUUUUUUUUUUCCCUUUUUCCCCCCCCCNNCNCNCCCNNNN',
        >>> }

        Line flags consists of a single character coverage indicator for each line in the file.

        - N: no coverage available
        - U: uncovered
        - C: covered
        """
        step = self.step
        job = self.step.job

        root = etree.fromstring(fp.read())

        results = []
        for node in root.iter('class'):
            filename = node.get('filename')
            file_coverage = []
            for lineset in node.iterchildren('lines'):
                lineno = 0
                for line in lineset.iterchildren('line'):
                    number, hits = int(line.get('number')), int(line.get('hits'))
                    if lineno < number - 1:
                        for lineno in range(lineno, number - 1):
                            file_coverage.append('N')
                    if hits > 0:
                        file_coverage.append('C')
                    else:
                        file_coverage.append('U')
                    lineno = number

            result = FileCoverage(
                step_id=step.id,
                job_id=job.id,
                project_id=job.project_id,
                filename=filename,
                data=''.join(file_coverage),
            )
            self.add_file_stats(result)

            results.append(result)

        return results

########NEW FILE########
__FILENAME__ = xunit
from __future__ import absolute_import, division

import logging

from lxml import etree

from changes.constants import Result
from changes.models import TestResult, TestResultManager

from .base import ArtifactHandler


class XunitHandler(ArtifactHandler):
    logger = logging.getLogger('xunit')

    def process(self, fp):
        test_list = self.get_tests(fp)

        manager = TestResultManager(self.step)
        manager.save(test_list)

        return test_list

    def get_tests(self, fp):
        try:
            root = etree.fromstring(fp.read())
        except Exception:
            self.logger.exception('Failed to parse XML')
            return []

        if root.tag == 'unittest-results':
            return self.get_bitten_tests(root)
        return self.get_xunit_tests(root)

    def get_bitten_tests(self, root):
        step = self.step

        results = []

        # XXX(dcramer): bitten xml syntax, no clue what this
        for node in root.iter('test'):
            # classname, name, time
            attrs = dict(node.items())
            # AFAIK the spec says only one tag can be present
            # http://windyroad.com.au/dl/Open%20Source/JUnit.xsd
            if attrs['status'] == 'success':
                result = Result.passed
            elif attrs['status'] == 'skipped':
                result = Result.skipped
            elif attrs['status'] in ('error', 'failure'):
                result = Result.failed
            else:
                result = None

            try:
                message = list(node.iter('traceback'))[0].text
            except IndexError:
                message = ''

            # no matching status tags were found
            if result is None:
                result = Result.passed

            results.append(TestResult(
                step=step,
                name=attrs['name'],
                package=attrs.get('fixture') or None,
                duration=float(attrs['duration']) * 1000,
                result=result,
                message=message,
            ))

        return results

    def get_xunit_tests(self, root):
        step = self.step

        results = []
        for node in root.iter('testcase'):
            # classname, name, time
            attrs = dict(node.items())
            # AFAIK the spec says only one tag can be present
            # http://windyroad.com.au/dl/Open%20Source/JUnit.xsd
            try:
                r_node = list(node.iterchildren())[0]
            except IndexError:
                result = Result.passed
                message = ''
            else:
                # TODO(cramer): whitelist tags that are not statuses
                if r_node.tag == 'failure':
                    result = Result.failed
                elif r_node.tag == 'skipped':
                    result = Result.skipped
                elif r_node.tag == 'error':
                    result = Result.failed
                else:
                    result = None

                message = r_node.text

            # no matching status tags were found
            if result is None:
                result = Result.passed

            if attrs.get('time'):
                duration = float(attrs['time']) * 1000
            else:
                duration = None

            results.append(TestResult(
                step=step,
                name=attrs['name'],
                package=attrs.get('classname') or None,
                duration=duration,
                result=result,
                message=message,
                reruns=int(attrs.get('rerun')) if attrs.get('rerun') else None
            ))

        return results

########NEW FILE########
__FILENAME__ = check_repos
from datetime import datetime, timedelta

from changes.models import Repository, RepositoryBackend
from changes.jobs.sync_repo import sync_repo


def check_repos():
    """
    Looks for any repositories which haven't checked in within several minutes
    and creates `sync_repo` tasks for them.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=5)

    repo_list = list(Repository.query.filter(
        Repository.backend != RepositoryBackend.unknown,
    ))

    for repo in repo_list:
        sync_repo.delay_if_needed(
            task_id=repo.id.hex,
            repo_id=repo.id.hex,
        )

########NEW FILE########
__FILENAME__ = cleanup_tasks
from __future__ import absolute_import

from datetime import datetime, timedelta

from changes.config import queue
from changes.constants import Status
from changes.models import Task
from changes.queue.task import TrackedTask, tracked_task

CHECK_TIME = timedelta(minutes=5)


@tracked_task
def cleanup_tasks():
    """
    Find any tasks which haven't checked in within a reasonable time period and
    requeue them if nescessary.
    """
    now = datetime.utcnow()
    cutoff = now - CHECK_TIME

    pending_tasks = Task.query.filter(
        Task.status != Status.finished,
        Task.date_modified < cutoff,
    )

    for task in pending_tasks:
        task_func = TrackedTask(queue.get_task(task.task_name))
        task_func.delay_if_needed(
            task_id=task.task_id.hex,
            parent_task_id=task.parent_id.hex if task.parent_id else None,
            **task.data['kwargs']
        )

########NEW FILE########
__FILENAME__ = create_job
from flask import current_app
from sqlalchemy.orm import subqueryload_all

from changes.backends.base import UnrecoverableException
from changes.config import db
from changes.constants import Status, Result
from changes.jobs.sync_job import sync_job
from changes.models import Job, JobPlan, Plan
from changes.queue.task import tracked_task


def abort_create(task):
    job = Job.query.get(task.kwargs['job_id'])
    job.status = Status.finished
    job.result = Result.aborted
    db.session.add(job)
    db.session.commit()
    current_app.logger.exception('Unrecoverable exception creating job %s', job.id)


@tracked_task(on_abort=abort_create, max_retries=10)
def create_job(job_id):
    job = Job.query.get(job_id)
    if not job:
        return

    job_plan = JobPlan.query.options(
        subqueryload_all('plan.steps')
    ).filter(
        JobPlan.job_id == job.id,
    ).join(Plan).first()

    try:
        if not job_plan:
            raise UnrecoverableException('Got create_job task without job plan: %s' % (job_id,))
        try:
            step = job_plan.plan.steps[0]
        except IndexError:
            raise UnrecoverableException('Missing steps for plan')

        implementation = step.get_implementation()
        implementation.execute(job=job)

    except UnrecoverableException:
        job.status = Status.finished
        job.result = Result.aborted
        current_app.logger.exception('Unrecoverable exception creating %s', job_id)
        return

    sync_job.delay(
        job_id=job.id.hex,
        task_id=job.id.hex,
        parent_task_id=job.build_id.hex,
    )

########NEW FILE########
__FILENAME__ = generate_report

########NEW FILE########
__FILENAME__ = signals
from flask import current_app

from changes.queue.task import tracked_task
from changes.utils.imports import import_string


class SuspiciousOperation(Exception):
    pass


@tracked_task
def fire_signal(signal, kwargs):
    for listener, l_signal in current_app.config['EVENT_LISTENERS']:
        if l_signal == signal:
            run_event_listener.delay(
                listener=listener,
                signal=signal,
                kwargs=kwargs,
            )


@tracked_task
def run_event_listener(listener, signal, kwargs):
    # simple check to make sure this is registered
    if not any(l == listener for l, _ in current_app.config['EVENT_LISTENERS']):
        raise SuspiciousOperation('%s is not a registered event listener' % (listener,))

    func = import_string(listener)
    func(**kwargs)

########NEW FILE########
__FILENAME__ = sync_artifact
from flask import current_app

from sqlalchemy.orm import subqueryload_all

from changes.backends.base import UnrecoverableException
from changes.models import Artifact, JobPlan, Plan
from changes.queue.task import tracked_task


def get_build_step(job_id):
    job_plan = JobPlan.query.options(
        subqueryload_all('plan.steps')
    ).filter(
        JobPlan.job_id == job_id,
    ).join(Plan).first()
    if not job_plan:
        raise UnrecoverableException('Missing job plan for job: %s' % (job_id,))

    try:
        step = job_plan.plan.steps[0]
    except IndexError:
        raise UnrecoverableException('Missing steps for plan: %s' % (job_plan.plan.id))

    implementation = step.get_implementation()
    return implementation


@tracked_task
def sync_artifact(artifact_id=None):
    if artifact_id:
        artifact = Artifact.query.get(artifact_id)

    if artifact is None:
        return

    step = artifact.step
    data = artifact.data

    try:
        implementation = get_build_step(step.job_id)
        implementation.fetch_artifact(step=step, artifact=data)

    except UnrecoverableException:
        current_app.logger.exception(
            'Unrecoverable exception fetching artifact %s: %s',
            step.id, artifact)

########NEW FILE########
__FILENAME__ = sync_build
from datetime import datetime
from flask import current_app
from sqlalchemy.sql import func

from changes.config import db, queue
from changes.constants import Result, Status
from changes.db.utils import try_create
from changes.jobs.signals import fire_signal
from changes.models import Build, ItemStat, Job
from changes.utils.agg import safe_agg
from changes.queue.task import tracked_task


def aggregate_build_stat(build, name, func_=func.sum):
    value = db.session.query(
        func.coalesce(func_(ItemStat.value), 0),
    ).filter(
        ItemStat.item_id.in_(
            db.session.query(Job.id).filter(
                Job.build_id == build.id,
            )
        ),
        ItemStat.name == name,
    ).as_scalar()

    try_create(ItemStat, where={
        'item_id': build.id,
        'name': name,
    }, defaults={
        'value': value
    })


def abort_build(task):
    build = Build.query.get(task.kwargs['build_id'])
    build.status = Status.finished
    build.result = Result.aborted
    db.session.add(build)
    db.session.commit()
    current_app.logger.exception('Unrecoverable exception syncing build %s', build.id)


@tracked_task(on_abort=abort_build)
def sync_build(build_id):
    """
    Synchronizing the build happens continuously until all jobs have reported in
    as finished or have failed/aborted.

    This task is responsible for:
    - Checking in with jobs
    - Aborting/retrying them if they're beyond limits
    - Aggregating the results from jobs into the build itself
    """
    build = Build.query.get(build_id)
    if not build:
        return

    if build.status == Status.finished:
        return

    all_jobs = list(Job.query.filter(
        Job.build_id == build_id,
    ))

    is_finished = sync_build.verify_all_children() == Status.finished

    build.date_started = safe_agg(
        min, (j.date_started for j in all_jobs if j.date_started))

    if is_finished:
        build.date_finished = safe_agg(
            max, (j.date_finished for j in all_jobs if j.date_finished))
    else:
        build.date_finished = None

    if build.date_started and build.date_finished:
        build.duration = int((build.date_finished - build.date_started).total_seconds() * 1000)
    else:
        build.duration = None

    if any(j.result is Result.failed for j in all_jobs):
        build.result = Result.failed
    elif is_finished:
        build.result = safe_agg(
            max, (j.result for j in all_jobs), Result.unknown)
    else:
        build.result = Result.unknown

    if is_finished:
        build.status = Status.finished
    elif any(j.status is not Status.queued for j in all_jobs):
        build.status = Status.in_progress
    else:
        build.status = Status.queued

    if db.session.is_modified(build):
        build.date_modified = datetime.utcnow()
        db.session.add(build)
        db.session.commit()

    if not is_finished:
        raise sync_build.NotFinished

    try:
        aggregate_build_stat(build, 'test_count')
        aggregate_build_stat(build, 'test_duration')
        aggregate_build_stat(build, 'test_failures')
        aggregate_build_stat(build, 'test_rerun_count')
        aggregate_build_stat(build, 'tests_missing')
        aggregate_build_stat(build, 'lines_covered')
        aggregate_build_stat(build, 'lines_uncovered')
        aggregate_build_stat(build, 'diff_lines_covered')
        aggregate_build_stat(build, 'diff_lines_uncovered')
    except Exception:
        current_app.logger.exception('Failing recording aggregate stats for build %s', build.id)

    fire_signal.delay(
        signal='build.finished',
        kwargs={'build_id': build.id.hex},
    )

    queue.delay('update_project_stats', kwargs={
        'project_id': build.project_id.hex,
    }, countdown=1)

########NEW FILE########
__FILENAME__ = sync_job
from datetime import datetime
from flask import current_app
from sqlalchemy.orm import subqueryload_all
from sqlalchemy.sql import func

from changes.backends.base import UnrecoverableException
from changes.config import db, queue
from changes.constants import Status, Result
from changes.db.utils import try_create
from changes.jobs.signals import fire_signal
from changes.models import (
    ItemStat, Job, JobStep, JobPlan, Plan, TestCase
)
from changes.queue.task import tracked_task
from changes.utils.agg import safe_agg


def aggregate_job_stat(job, name, func_=func.sum):
    value = db.session.query(
        func.coalesce(func_(ItemStat.value), 0),
    ).filter(
        ItemStat.item_id.in_(
            db.session.query(JobStep.id).filter(
                JobStep.job_id == job.id,
            )
        ),
        ItemStat.name == name,
    ).as_scalar()

    try_create(ItemStat, where={
        'item_id': job.id,
        'name': name,
    }, defaults={
        'value': value
    })


def abort_job(task):
    job = Job.query.get(task.kwargs['job_id'])
    job.status = Status.finished
    job.result = Result.aborted
    db.session.add(job)
    db.session.commit()
    current_app.logger.exception('Unrecoverable exception syncing job %s', job.id)


@tracked_task(on_abort=abort_job)
def sync_job(job_id):
    job = Job.query.get(job_id)
    if not job:
        return

    if job.status == Status.finished:
        return

    # TODO(dcramer): we make an assumption that there is a single step
    job_plan = JobPlan.query.options(
        subqueryload_all('plan.steps')
    ).filter(
        JobPlan.job_id == job.id,
    ).join(Plan).first()
    try:
        if not job_plan:
            raise UnrecoverableException('Got sync_job task without job plan: %s' % (job.id,))

        try:
            step = job_plan.plan.steps[0]
        except IndexError:
            raise UnrecoverableException('Missing steps for plan')

        implementation = step.get_implementation()
        implementation.update(job=job)

    except UnrecoverableException:
        job.status = Status.finished
        job.result = Result.aborted
        current_app.logger.exception('Unrecoverable exception syncing %s', job.id)

    is_finished = sync_job.verify_all_children() == Status.finished
    if is_finished:
        job.status = Status.finished

    all_phases = list(job.phases)

    job.date_started = safe_agg(
        min, (j.date_started for j in all_phases if j.date_started))

    if is_finished:
        job.date_finished = safe_agg(
            max, (j.date_finished for j in all_phases if j.date_finished))
    else:
        job.date_finished = None

    if job.date_started and job.date_finished:
        job.duration = int((job.date_finished - job.date_started).total_seconds() * 1000)
    else:
        job.duration = None

    # if any phases are marked as failing, fail the build
    if any(j.result is Result.failed for j in all_phases):
        job.result = Result.failed
    # if any test cases were marked as failing, fail the build
    elif TestCase.query.filter(TestCase.result == Result.failed, TestCase.job_id == job.id).first():
        job.result = Result.failed
    # if we've finished all phases, use the best result available
    elif is_finished:
        job.result = safe_agg(
            max, (j.result for j in all_phases), Result.unknown)
    else:
        job.result = Result.unknown

    if is_finished:
        job.status = Status.finished
    elif any(j.status is not Status.queued for j in all_phases):
        job.status = Status.in_progress
    else:
        job.status = Status.queued

    if db.session.is_modified(job):
        job.date_modified = datetime.utcnow()

        db.session.add(job)
        db.session.commit()

    if not is_finished:
        raise sync_job.NotFinished

    try:
        aggregate_job_stat(job, 'test_count')
        aggregate_job_stat(job, 'test_duration')
        aggregate_job_stat(job, 'test_failures')
        aggregate_job_stat(job, 'test_rerun_count')
        aggregate_job_stat(job, 'tests_missing')
        aggregate_job_stat(job, 'lines_covered')
        aggregate_job_stat(job, 'lines_uncovered')
        aggregate_job_stat(job, 'diff_lines_covered')
        aggregate_job_stat(job, 'diff_lines_uncovered')
    except Exception:
        current_app.logger.exception('Failing recording aggregate stats for job %s', job.id)

    fire_signal.delay(
        signal='job.finished',
        kwargs={'job_id': job.id.hex},
    )

    if job_plan:
        queue.delay('update_project_plan_stats', kwargs={
            'project_id': job.project_id.hex,
            'plan_id': job_plan.plan_id.hex,
        }, countdown=1)

########NEW FILE########
__FILENAME__ = sync_job_step
from flask import current_app
from sqlalchemy.orm import subqueryload_all
from sqlalchemy.sql import func

from changes.backends.base import UnrecoverableException
from changes.constants import Status, Result
from changes.config import db
from changes.db.utils import try_create
from changes.models import (
    JobStep, JobPlan, Plan, ProjectOption, TestCase, ItemStat, FileCoverage
)
from changes.queue.task import tracked_task


def get_build_step(job_id):
    job_plan = JobPlan.query.options(
        subqueryload_all('plan.steps')
    ).filter(
        JobPlan.job_id == job_id,
    ).join(Plan).first()
    if not job_plan:
        raise UnrecoverableException('Missing job plan for job: %s' % (job_id,))

    try:
        step = job_plan.plan.steps[0]
    except IndexError:
        raise UnrecoverableException('Missing steps for plan: %s' % (job_plan.plan.id))

    implementation = step.get_implementation()
    return implementation


def abort_step(task):
    step = JobStep.query.get(task.kwargs['step_id'])
    step.status = Status.finished
    step.result = Result.aborted
    db.session.add(step)
    db.session.commit()
    current_app.logger.exception('Unrecoverable exception syncing step %s', step.id)


def is_missing_tests(step):
    query = ProjectOption.query.filter(
        ProjectOption.project_id == step.project_id,
        ProjectOption.name == 'build.expect-tests',
        ProjectOption.value == '1',
    )
    if not db.session.query(query.exists()).scalar():
        return False

    has_tests = db.session.query(TestCase.query.filter(
        TestCase.step_id == step.id,
    ).exists()).scalar()

    return not has_tests


def record_coverage_stats(step):
    coverage_stats = db.session.query(
        func.sum(FileCoverage.lines_covered).label('lines_covered'),
        func.sum(FileCoverage.lines_uncovered).label('lines_uncovered'),
        func.sum(FileCoverage.diff_lines_covered).label('diff_lines_covered'),
        func.sum(FileCoverage.diff_lines_uncovered).label('diff_lines_uncovered'),
    ).filter(
        FileCoverage.step_id == step.id,
    ).group_by(
        FileCoverage.step_id,
    ).first()

    stat_list = (
        'lines_covered', 'lines_uncovered',
        'diff_lines_covered', 'diff_lines_uncovered',
    )
    for stat_name in stat_list:
        try_create(ItemStat, where={
            'item_id': step.id,
            'name': stat_name,
        }, defaults={
            'value': getattr(coverage_stats, stat_name, 0) or 0,
        })


@tracked_task(on_abort=abort_step, max_retries=100)
def sync_job_step(step_id):
    step = JobStep.query.get(step_id)
    if not step:
        return

    implementation = get_build_step(step.job_id)
    implementation.update_step(step=step)

    if step.status != Status.finished:
        is_finished = False
    else:
        is_finished = sync_job_step.verify_all_children() == Status.finished

    if not is_finished:
        raise sync_job_step.NotFinished

    missing_tests = is_missing_tests(step)

    try_create(ItemStat, where={
        'item_id': step.id,
        'name': 'tests_missing',
    }, defaults={
        'value': int(missing_tests)
    })

    try:
        record_coverage_stats(step)
    except Exception:
        current_app.logger.exception('Failing recording coverage stats for step %s', step.id)

    if step.result == Result.passed and missing_tests:
        step.result = Result.failed
        db.session.add(step)
        db.session.commit()

########NEW FILE########
__FILENAME__ = sync_repo
from __future__ import absolute_import, print_function

from datetime import datetime

from changes.config import db
from changes.jobs.signals import fire_signal
from changes.models import Repository
from changes.queue.task import tracked_task


@tracked_task(max_retries=None)
def sync_repo(repo_id, continuous=True):
    repo = Repository.query.get(repo_id)
    if not repo:
        print('Repository not found')
        return

    vcs = repo.get_vcs()
    if vcs is None:
        print('No VCS backend available')
        return

    Repository.query.filter(
        Repository.id == repo.id,
    ).update({
        'last_update_attempt': datetime.utcnow(),
    }, synchronize_session=False)
    db.session.commit()

    if vcs.exists():
        vcs.update()
    else:
        vcs.clone()

    # TODO(dcramer): this doesnt scrape everything, and really we wouldn't
    # want to do this all in a single job so we should split this into a
    # backfill task
    # TODO(dcramer): this doesn't collect commits in non-default branches
    might_have_more = True
    parent = None
    while might_have_more:
        might_have_more = False
        for commit in vcs.log(parent=parent):
            revision, created = commit.save(repo)
            db.session.commit()
            if not created:
                break
            might_have_more = True
            parent = commit.id

            fire_signal.delay(
                signal='revision.created',
                kwargs={'repository_id': repo.id.hex,
                        'revision_sha': revision.sha},
            )

    Repository.query.filter(
        Repository.id == repo.id,
    ).update({
        'last_update': datetime.utcnow(),
    }, synchronize_session=False)
    db.session.commit()

    if continuous:
        raise sync_repo.NotFinished

########NEW FILE########
__FILENAME__ = update_project_stats
from sqlalchemy import and_

from changes.config import db
from changes.constants import Result, Status
from changes.models import Project, ProjectPlan, Build, Job, JobPlan
from changes.utils.locking import lock


@lock
def update_project_stats(project_id):
    last_5_builds = Build.query.filter_by(
        result=Result.passed,
        status=Status.finished,
        project_id=project_id,
    ).order_by(Build.date_finished.desc())[:5]
    if last_5_builds:
        avg_build_time = sum(
            b.duration for b in last_5_builds
            if b.duration
        ) / len(last_5_builds)
    else:
        avg_build_time = None

    db.session.query(Project).filter(
        Project.id == project_id
    ).update({
        Project.avg_build_time: avg_build_time,
    }, synchronize_session=False)


@lock
def update_project_plan_stats(project_id, plan_id):
    job_plan = JobPlan.query.filter(
        JobPlan.project_id == project_id,
        JobPlan.plan_id == plan_id,
    ).first()
    if not job_plan:
        return

    last_5_builds = Job.query.filter(
        Job.result == Result.passed,
        Job.status == Status.finished,
        Job.project_id == project_id,
    ).join(
        JobPlan,
        and_(
            JobPlan.id == job_plan.id,
            JobPlan.job_id == Job.id,
        )
    ).order_by(Job.date_finished.desc())[:5]
    if last_5_builds:
        avg_build_time = sum(
            b.duration for b in last_5_builds
            if b.duration
        ) / len(last_5_builds)
    else:
        avg_build_time = None

    db.session.query(ProjectPlan).filter(
        ProjectPlan.project_id == job_plan.project_id,
        ProjectPlan.plan_id == job_plan.plan_id,
    ).update({
        ProjectPlan.avg_build_time: avg_build_time,
    }, synchronize_session=False)

########NEW FILE########
__FILENAME__ = coverage
from changes.config import db

from changes.constants import Status

from changes.models import Build, FileCoverage, Job, Project, Source


def get_coverage_by_source_id(source_id):
    """
    Takes a source_id and returns a dictionary of coverage for that source_id.  The
    coverage is generated for the most recently finished builds for each project.

    The dictionary maps file names to a string of the form 'UNCCCNCU', where U means
    'uncovered', C means 'covered' and 'N' means 'no coverage info'.
    """
    source = Source.query.get(source_id)

    projects = Project.query.filter(
        Project.repository_id == source.repository_id
    )

    newest_build_ids = set()
    for project in projects:
        b_id = db.session.query(Build.id).filter(
            Build.project_id == project.id,
            Build.source_id == source_id,
            Build.status == Status.finished
        ).order_by(Build.date_created.desc()).first()
        if b_id:
            newest_build_ids.add(b_id[0])

    return get_coverage_by_build_ids(newest_build_ids)


def get_coverage_by_build_id(build_id):
    return get_coverage_by_build_ids([build_id])


def get_coverage_by_build_ids(build_ids):
    """
    Returns the coverage associated with some builds.

    The dictionary maps file names to a string of the form 'UNCCCNCU', where U means
    'uncovered', C means 'covered' and 'N' means 'no coverage info'.
    """
    if not build_ids:
        return {}

    all_job_ids = db.session.query(Job.id).filter(
        Job.build_id.in_(build_ids)
    )

    return get_coverage_by_job_ids(all_job_ids)


def get_coverage_by_job_ids(job_ids):
    """
    Returns the coverage associated with some jobs.

    The dictionary maps file names to a string of the form 'UNCCCNCU', where U means
    'uncovered', C means 'covered' and 'N' means 'no coverage info'.
    """
    if not job_ids:
        return {}

    return FileCoverage.query.filter(
        FileCoverage.job_id.in_(job_ids)
    )

########NEW FILE########
__FILENAME__ = build_revision
import logging

from collections import defaultdict
from flask import current_app
from fnmatch import fnmatch

from changes.api.build_index import BuildIndexAPIView
from changes.config import db
from changes.models import ProjectOption, Project, Revision


logger = logging.getLogger('build_revision')


def should_build_branch(revision, allowed_branches):
    if not revision.branches and '*' in allowed_branches:
        return True

    for branch in revision.branches:
        if any(fnmatch(branch, pattern) for pattern in allowed_branches):
            return True
    return False


def revision_created_handler(revision_sha, repository_id, **kwargs):
    revision = Revision.query.filter(
        Revision.sha == revision_sha,
        Revision.repository_id == repository_id,
    ).first()
    if revision is None:
        return

    project_list = list(Project.query.filter(
        Project.repository_id == revision.repository_id,
    ))
    if not project_list:
        return

    options_query = db.session.query(
        ProjectOption.project_id, ProjectOption.name, ProjectOption.value
    ).filter(
        ProjectOption.project_id.in_(p.id for p in project_list),
        ProjectOption.name.in_([
            'build.branch-names',
            'build.commit-trigger',
        ])
    )

    options = defaultdict(dict)
    for project_id, option_name, option_value in options_query:
        options[project_id][option_name] = option_value

    for project in project_list:
        if options[project.id].get('build.commit-trigger', '1') != '1':
            continue

        branch_names = filter(bool, options[project.id].get('build.branch-names', '*').split(' '))
        if not should_build_branch(revision, branch_names):
            continue

        data = {
            'sha': revision.sha,
            'project': project.slug,
        }
        with current_app.test_request_context('/api/0/builds/', method='POST', data=data):
            try:
                response = BuildIndexAPIView().post()
            except Exception:
                logger.exception('Failed to create build: %s' % (response,))
            else:
                if isinstance(response, (list, tuple)):
                    response, status = response
                    if status != 200:
                        logger.error('Failed to create build: %s' % (response,), extra={
                            'data': data,
                        })

########NEW FILE########
__FILENAME__ = green_build
import logging
import requests

from datetime import datetime
from flask import current_app

from changes.config import db
from changes.constants import Result
from changes.db.utils import create_or_update
from changes.models import (
    Build, Event, EventType, ProjectOption, RepositoryBackend
)
from changes.utils.http import build_uri
from changes.utils.locking import lock

logger = logging.getLogger('green_build')


def get_options(project_id):
    return dict(
        db.session.query(
            ProjectOption.name, ProjectOption.value
        ).filter(
            ProjectOption.project_id == project_id,
            ProjectOption.name.in_([
                'green-build.notify', 'green-build.project',
            ])
        )
    )


@lock
def build_finished_handler(build_id, **kwargs):
    build = Build.query.get(build_id)
    if build is None:
        return

    if build.result != Result.passed:
        return

    url = current_app.config.get('GREEN_BUILD_URL')
    if not url:
        logger.info('GREEN_BUILD_URL not set')
        return

    auth = current_app.config['GREEN_BUILD_AUTH']
    if not auth:
        logger.info('GREEN_BUILD_AUTH not set')
        return

    source = build.source

    # we only want to identify stable revisions
    if not source.is_commit():
        logger.debug('Ignoring build due to non-commit: %s', build.id)
        return

    options = get_options(build.project_id)

    if options.get('green-build.notify', '1') != '1':
        logger.info('green-build.notify disabled for project: %s', build.project_id)
        return

    if source.repository.backend != RepositoryBackend.hg:
        logger.info('Repository backend is not supported: %s', source.repository.id)
        return

    vcs = source.repository.get_vcs()
    if vcs is None:
        logger.info('Repository has no VCS set: %s', source.repository.id)
        return

    # ensure we have the latest changes
    if vcs.exists():
        vcs.update()
    else:
        vcs.clone()

    release_id = vcs.run(['log', '-r %s' % (source.revision_sha,), '--limit=1', '--template={rev}:{node|short}'])

    project = options.get('green-build.project') or build.project.slug

    logging.info('Making green_build request to %s', url)
    try:
        requests.post(url, auth=auth, data={
            'project': project,
            'id': release_id,
            'build_url': build_uri('/projects/{0}/builds/{1}/'.format(
                build.project.slug, build.id.hex)),
            'build_server': 'changes',
        })
    except Exception:
        logger.exception('Failed to report green build')
        status = 'fail'
    else:
        status = 'success'

    create_or_update(Event, where={
        'type': EventType.green_build,
        'item_id': build.id,
    }, values={
        'data': {
            'status': status,
        },
        'date_modified': datetime.utcnow(),
    })

########NEW FILE########
__FILENAME__ = hipchat
import json
import logging
import requests

from flask import current_app

from changes.config import db
from changes.constants import Result, Status
from changes.models import Build, ProjectOption, Source
from changes.utils.http import build_uri

logger = logging.getLogger('hipchat')

DEFAULT_TIMEOUT = 1
API_ENDPOINT = 'https://api.hipchat.com/v1/rooms/message'


def get_options(project_id):
    return dict(
        db.session.query(
            ProjectOption.name, ProjectOption.value
        ).filter(
            ProjectOption.project_id == project_id,
            ProjectOption.name.in_([
                'hipchat.notify', 'hipchat.room',
            ])
        )
    )


def should_notify(build):
    if build.result not in (Result.failed, Result.passed):
        return

    parent = Build.query.join(
        Source, Source.id == Build.source_id,
    ).filter(
        Source.patch_id == None,  # NOQA
        Source.revision_sha != build.source.revision_sha,
        Build.project == build.project,
        Build.date_created < build.date_created,
        Build.status == Status.finished,
        Build.result.in_([Result.passed, Result.failed]),
    ).order_by(Build.date_created.desc()).first()

    if parent is None:
        return build.result == Result.failed

    if parent.result == build.result:
        return False

    return True


def build_finished_handler(build_id, **kwargs):
    build = Build.query.get(build_id)
    if build is None:
        return

    if build.source.patch_id:
        return

    if not current_app.config.get('HIPCHAT_TOKEN'):
        return

    if not should_notify(build):
        return

    options = get_options(build.project_id)

    if options.get('hipchat.notify', '0') != '1':
        return

    if not options.get('hipchat.room'):
        return

    message = u'Build {result} - <a href="{link}">{project} #{number}</a> ({target})'.format(
        number='{0}'.format(build.number),
        result=unicode(build.result),
        target=build.target or build.source.revision_sha or 'Unknown',
        project=build.project.name,
        link=build_uri('/projects/{0}/builds/{1}/'.format(
            build.project.slug, build.id.hex))
    )
    if build.author:
        message += ' - {author}'.format(
            author=build.author.email,
        )

    send_payload(
        token=current_app.config['HIPCHAT_TOKEN'],
        room=options['hipchat.room'],
        message=message,
        notify=True,
        color='green' if build.result == Result.passed else 'red',
    )


def send_payload(token, room, message, notify, color='red',
                 timeout=DEFAULT_TIMEOUT):
    data = {
        'auth_token': token,
        'room_id': room,
        'from': 'Changes',
        'message': message,
        'notify': int(notify),
        'color': color,
    }
    response = requests.post(API_ENDPOINT, data=data, timeout=timeout)
    response_data = json.loads(response.content)

    if 'status' not in response_data:
        logger.error('Unexpected response: %s', response_data)

    if response_data['status'] != 'sent':
        logger.error('Event could not be sent to hipchat')

########NEW FILE########
__FILENAME__ = mail
from __future__ import absolute_import, print_function

import toronado

from flask import render_template
from flask_mail import Message, sanitize_address
from jinja2 import Markup

from changes.config import db, mail
from changes.constants import Result
from changes.db.utils import try_create
from changes.listeners.notification_base import NotificationHandler
from changes.models import Event, EventType, JobPlan, ProjectOption, ItemOption
from changes.utils.http import build_uri


class MailNotificationHandler(NotificationHandler):
    def get_context(self, job, parent=None):
        test_failures = self.get_test_failures(job)
        num_test_failures = test_failures.count()
        test_failures = test_failures[:25]

        build = job.build

        result_label = self.get_result_label(job, parent)

        subject = u"{target} {result} - {project} #{number}".format(
            number='{0}.{1}'.format(job.build.number, job.number),
            result=result_label,
            target=build.target or build.source.revision_sha or 'Build',
            project=job.project.name,
        )

        build.uri = build_uri('/projects/{0}/builds/{1}/'.format(
            build.project.slug, build.id.hex))
        job.uri = build.uri + 'jobs/{0}/'.format(job.id.hex)

        for testgroup in test_failures:
            testgroup.uri = job.uri + 'tests/{0}/'.format(testgroup.id.hex)

        is_failure = job.result == Result.failed

        context = {
            'title': subject,
            'job': job,
            'build': job.build,
            'is_failure': is_failure,
            'is_passing': job.result == Result.passed,
            'result_label': result_label,
            'total_test_failures': num_test_failures,
            'test_failures': test_failures,
        }

        if is_failure:
            # try to find the last failing log
            log_sources = self.get_failing_log_sources(job)
            if len(log_sources) == 1:
                log_clipping = self.get_log_clipping(
                    log_sources[0], max_size=5000, max_lines=25)

                context['build_log'] = {
                    'text': log_clipping,
                    'name': log_sources[0].name,
                    'uri': '{0}logs/{1}/'.format(job.uri, log_sources[0].id.hex),
                }
            elif log_sources:
                context['relevant_logs'] = [
                    {
                        'name': source.name,
                        'uri': '{0}logs/{1}/'.format(job.uri, source.id.hex),
                    } for source in log_sources
                ]

        return context

    def send(self, job, parent=None):
        # TODO(dcramer): we should send a clipping of a relevant job log
        recipients = self.get_recipients(job)
        if not recipients:
            return

        event = try_create(Event, where={
            'type': EventType.email,
            'item_id': job.build_id,
            'data': {
                'recipients': recipients,
            }
        })
        if not event:
            # We've already sent out notifications for this build
            return

        context = self.get_context(job, parent)

        msg = Message(context['title'], recipients=recipients, extra_headers={
            'Reply-To': ', '.join(sanitize_address(r) for r in recipients),
        })
        msg.body = render_template('listeners/mail/notification.txt', **context)
        msg.html = Markup(toronado.from_string(
            render_template('listeners/mail/notification.html', **context)
        ))

        mail.send(msg)

    def get_job_options(self, job):
        option_names = [
            'mail.notify-author',
            'mail.notify-addresses',
            'mail.notify-addresses-revisions',
        ]

        # get relevant options
        options = dict(
            db.session.query(
                ProjectOption.name, ProjectOption.value
            ).filter(
                ProjectOption.project_id == job.project_id,
                ProjectOption.name.in_(option_names),
            )
        )

        # if a plan was specified, it's options override the project's
        job_plan = JobPlan.query.filter(
            JobPlan.job_id == job.id,
        ).first()
        if job_plan:
            plan_options = db.session.query(
                ItemOption.name, ItemOption.value
            ).filter(
                ItemOption.item_id == job_plan.plan_id,
                ItemOption.name.in_(option_names),
            )
            # determine plan options
            for key, value in plan_options:
                options[key] = value

        return options

    def get_recipients(self, job):
        options = self.get_job_options(job)

        recipients = []
        if options.get('mail.notify-author', '1') == '1':
            author = job.build.author
            if author:
                recipients.append(u'%s <%s>' % (author.name, author.email))

        if options.get('mail.notify-addresses'):
            recipients.extend(
                # XXX(dcramer): we dont have option validators so lets assume people
                # enter slightly incorrect values
                [x.strip() for x in options['mail.notify-addresses'].split(',')]
            )

        if not job.build.source.patch_id:
            if options.get('mail.notify-addresses-revisions'):
                recipients.extend(
                    [x.strip() for x in options['mail.notify-addresses-revisions'].split(',')]
                )

        return recipients


def job_finished_handler(*args, **kwargs):
    instance = MailNotificationHandler()
    instance.job_finished_handler(*args, **kwargs)

########NEW FILE########
__FILENAME__ = notification_base
from __future__ import absolute_import, print_function

from changes.constants import Result, Status
from changes.models import Job, JobStep, TestCase, LogSource, LogChunk, Source

UNSET = object()


class NotificationHandler(object):
    def get_test_failures(self, job):
        return TestCase.query.filter(
            TestCase.job_id == job.id,
            TestCase.result == Result.failed,
        ).order_by(TestCase.name.asc())

    def get_parent(self, job):
        return Job.query.join(
            Source, Source.id == Job.source_id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Source.revision_sha != job.build.source.revision_sha,
            Job.project == job.project,
            Job.date_created < job.date_created,
            Job.status == Status.finished,
            Job.result.in_([Result.passed, Result.failed]),
        ).order_by(Job.date_created.desc()).first()

    def get_failing_log_sources(self, job):
        return list(LogSource.query.filter(
            LogSource.job_id == job.id,
        ).join(
            JobStep, LogSource.step_id == JobStep.id,
        ).filter(
            JobStep.result == Result.failed,
        ).order_by(JobStep.date_created))

    def should_notify(self, job, parent=UNSET):
        """
        Compare with parent job (previous job) and confirm if current
        job provided any change in state (e.g. new failures).
        """
        if job.result not in (Result.failed, Result.passed):
            return

        if parent is UNSET:
            parent = self.get_parent(job)

        # if theres no parent, this job must be at fault
        if parent is None:
            return job.result == Result.failed

        if job.result == Result.passed == parent.result:
            return False

        current_failures = set([t.name_sha for t in self.get_test_failures(job)])
        # if we dont have any testgroup failures, then we cannot identify the cause
        # so we must notify the individual
        if not current_failures:
            return True

        parent_failures = set([t.name_sha for t in self.get_test_failures(parent)])
        if parent_failures != current_failures:
            return True

        return False

    def get_log_clipping(self, logsource, max_size=5000, max_lines=25):
        queryset = LogChunk.query.filter(
            LogChunk.source_id == logsource.id,
        )
        tail = queryset.order_by(LogChunk.offset.desc()).limit(1).first()

        chunks = list(queryset.filter(
            (LogChunk.offset + LogChunk.size) >= max(tail.offset - max_size, 0),
        ).order_by(LogChunk.offset.asc()))

        clipping = ''.join(l.text for l in chunks).strip()[-max_size:]
        # only return the last 25 lines
        clipping = '\r\n'.join(clipping.splitlines()[-max_lines:])

        return clipping

    def get_result_label(self, job, parent):
        if parent:
            if parent.result == Result.failed and job.result == Result.passed:
                result_label = u'Fixed'
            else:
                result_label = unicode(job.result)
        else:
            result_label = unicode(job.result)

        return result_label

    def job_finished_handler(self, job_id, **kwargs):
        job = Job.query.get(job_id)
        if job is None:
            return

        parent = self.get_parent(job)

        if not self.should_notify(job, parent):
            return

        self.send(job, parent)

    def send(self, job, parent):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = mock
# TODO(dcramer): make the API queryable internally so we dont have to have
# multiple abstractions to creating objects
import itertools
import random

from hashlib import sha1
from loremipsum import get_paragraphs, get_sentences
from uuid import uuid4

from changes.config import db
from changes.constants import Status, Result
from changes.db.utils import get_or_create
from changes.models import (
    Project, Repository, Author, Revision, Job, JobPhase, JobStep, Node,
    TestResult, Change, LogChunk, Build, JobPlan, Plan, Source,
    Patch, FileCoverage, Event, EventType, Cluster, ClusterNode
)
from changes.testutils.fixtures import SAMPLE_DIFF
from changes.utils.slugs import slugify


TEST_PACKAGES = itertools.cycle([
    'tests/changes/handlers/test_xunit.py',
    'tests/changes/handlers/test_coverage.py',
    'tests/changes/backends/koality/test_backend.py',
    'tests/changes/backends/koality/test_backend.py',
])

TEST_NAMES = itertools.cycle([
    'ListBuildsTest.test_simple',
    'SyncBuildDetailsTest.test_simple',
])

TEST_STEP_LABELS = itertools.cycle([
    'tests/changes/web/frontend/test_build_list.py',
    'tests/changes/web/frontend/test_build_details.py',
    'tests/changes/backends/koality/test_backend.py',
    'tests/changes/handlers/test_coverage.py',
    'tests/changes/handlers/test_xunit.py',
])

PROJECT_NAMES = itertools.cycle([
    'Earth',
    'Wind',
    'Fire',
    'Water',
    'Heart',
])

PLAN_NAMES = itertools.cycle([
    'Build Foo',
    'Build Bar',
])


def repository(**kwargs):
    if 'url' not in kwargs:
        kwargs['url'] = 'https://github.com/example-{0}/example.git'.format(
            random.randint(1, 100000))

    try:
        result = Repository.query.filter_by(url=kwargs['url'])[0]
    except IndexError:
        result = Repository(**kwargs)
        db.session.add(result)
    return result


def project(repository, **kwargs):
    if 'name' not in kwargs:
        kwargs['name'] = PROJECT_NAMES.next()

    project = Project.query.filter(
        Project.name == kwargs['name'],
    ).first()
    if project:
        return project

    result = Project(repository=repository, **kwargs)
    db.session.add(result)
    return result


def author(**kwargs):
    if 'name' not in kwargs:
        kwargs['name'] = ' '.join(get_sentences(1)[0].split(' ')[0:2])
    if 'email' not in kwargs:
        kwargs['email'] = '{0}@example.com'.format(slugify(kwargs['name']))
    try:
        result = Author.query.filter_by(email=kwargs['email'])[0]
    except IndexError:
        result = Author(**kwargs)
        db.session.add(result)
    return result


def change(project, **kwargs):
    if 'message' not in kwargs:
        kwargs['message'] = '\n\n'.join(get_paragraphs(2))

    if 'label' not in kwargs:
        diff_id = 'D{0}'.format(random.randint(1000, 1000000000000))
        kwargs['label'] = '{0}: {1}'.format(
            diff_id, kwargs['message'].splitlines()[0]
        )[:128]
    else:
        diff_id = None

    if 'hash' not in kwargs:
        kwargs['hash'] = sha1(diff_id or uuid4().hex).hexdigest()

    kwargs.setdefault('repository', project.repository)

    result = Change(project=project, **kwargs)
    db.session.add(result)
    return result


def build(project, **kwargs):
    kwargs.setdefault('label', get_sentences(1)[0][:128])
    kwargs.setdefault('status', Status.finished)
    kwargs.setdefault('result', Result.passed)
    kwargs.setdefault('duration', random.randint(10000, 100000))
    kwargs.setdefault('target', uuid4().hex)

    if 'source' not in kwargs:
        kwargs['source'] = source(project.repository)

    kwargs['project'] = project
    kwargs['project_id'] = kwargs['project'].id
    kwargs['author_id'] = kwargs['author'].id

    build = Build(**kwargs)
    db.session.add(build)

    event = Event(
        type=EventType.green_build,
        item_id=build.id,
        data={'status': 'success'}
    )
    db.session.add(event)

    return build


def plan(**kwargs):
    if 'label' not in kwargs:
        kwargs['label'] = PLAN_NAMES.next()

    plan = Plan.query.filter(
        Plan.label == kwargs['label'],
    ).first()
    if plan:
        return plan

    result = Plan(**kwargs)
    db.session.add(result)

    return result


def job(build, change=None, **kwargs):
    kwargs.setdefault('project', build.project)
    kwargs.setdefault('label', get_sentences(1)[0][:128])
    kwargs.setdefault('status', Status.finished)
    kwargs.setdefault('result', Result.passed)
    kwargs.setdefault('duration', random.randint(10000, 100000))
    kwargs['source'] = build.source

    kwargs['source_id'] = kwargs['source'].id
    kwargs['project_id'] = kwargs['project'].id
    kwargs['build_id'] = build.id
    if change:
        kwargs['change_id'] = change.id

    job = Job(
        build=build,
        change=change,
        **kwargs
    )
    db.session.add(job)

    node, created = get_or_create(Node, where={
        'label': get_sentences(1)[0][:32],
    })

    if created:
        cluster, _ = get_or_create(Cluster, where={
            'label': get_sentences(1)[0][:32],
        })

        clusternode = ClusterNode(cluster=cluster, node=node)
        db.session.add(clusternode)

    jobplan = JobPlan(
        plan=plan(),
        build=build,
        project=job.project,
        job=job,
    )
    db.session.add(jobplan)

    phase1_setup = JobPhase(
        project=job.project, job=job,
        date_started=job.date_started,
        date_finished=job.date_finished,
        status=Status.finished, result=Result.passed, label='Setup',
    )
    db.session.add(phase1_setup)

    phase1_compile = JobPhase(
        project=job.project, job=job,
        date_started=job.date_started,
        date_finished=job.date_finished,
        status=Status.finished, result=Result.passed, label='Compile',
    )
    db.session.add(phase1_compile)

    phase1_test = JobPhase(
        project=job.project, job=job,
        date_started=job.date_started,
        date_finished=job.date_finished,
        status=kwargs['status'], result=kwargs['result'], label='Test',
    )
    db.session.add(phase1_test)

    step = JobStep(
        project=job.project, job=job,
        phase=phase1_setup, status=phase1_setup.status, result=phase1_setup.result,
        label='Setup', node=node,
    )
    db.session.add(step)

    step = JobStep(
        project=job.project, job=job,
        phase=phase1_compile, status=phase1_compile.status, result=phase1_compile.result,
        label='Compile', node=node,
    )
    db.session.add(step)

    step = JobStep(
        project=job.project, job=job,
        phase=phase1_test, status=phase1_test.status, result=phase1_test.result,
        label=TEST_STEP_LABELS.next(), node=node,
    )
    db.session.add(step)
    step = JobStep(
        project=job.project, job=job,
        phase=phase1_test, status=phase1_test.status, result=phase1_test.result,
        label=TEST_STEP_LABELS.next(), node=node,
    )
    db.session.add(step)

    return job


def logchunk(source, **kwargs):
    # TODO(dcramer): we should default offset to previosu entry in LogSource
    kwargs.setdefault('offset', 0)

    text = kwargs.pop('text', None) or '\n'.join(get_sentences(4))

    logchunk = LogChunk(
        source=source,
        job=source.job,
        project=source.project,
        text=text,
        size=len(text),
        **kwargs
    )
    db.session.add(logchunk)
    return logchunk


def revision(repository, author):
    result = Revision(
        repository=repository, sha=uuid4().hex, author=author,
        repository_id=repository.id, author_id=author.id,
        message='\n\n'.join(get_paragraphs(2)),
        branches=['default', 'foobar'],
    )
    db.session.add(result)

    return result


def _generate_random_coverage_string(num_lines):
    cov_str = ''
    for i in range(num_lines):
        rand_int = random.randint(0, 2)
        if rand_int == 0:
            cov_str += 'U'
        elif rand_int == 1:
            cov_str += 'N'
        elif rand_int == 2:
            cov_str += 'C'

    return cov_str


def _generate_sample_coverage_data(diff):
    diff_lines = diff.splitlines()

    cov_data = {}
    current_file = None
    line_number = None
    max_line_for_current_file = 0

    for line in diff_lines:
        if line.startswith('diff'):
            if current_file is not None:
                cov_data[current_file] = _generate_random_coverage_string(max_line_for_current_file)
            max_line_for_current_file = 0
            current_file = None
            line_number = None
        elif current_file is None and line_number is None and (line.startswith('+++') or line.startswith('---')):
            if line.startswith('+++ b/'):
                line = line.split('\t')[0]
                current_file = unicode(line[6:])
        elif line.startswith('@@'):
            line_num_info = line.split('+')[1]
            line_number = int(line_num_info.split(',')[0])
            additional_lines = int(line_num_info.split(',')[1].split(' ')[0])
            max_line_for_current_file = line_number + additional_lines
        else:
            # Just keep truckin...
            pass

    cov_data[current_file] = _generate_random_coverage_string(max_line_for_current_file)
    return cov_data


def file_coverage(project, job, patch):
    file_cov = _generate_sample_coverage_data(patch.diff)

    for file, coverage in file_cov.iteritems():
        file_coverage = FileCoverage(
            project_id=project.id,
            job_id=job.id,
            filename=file,
            data=coverage,
            lines_covered=5,
            lines_uncovered=8,
            diff_lines_covered=3,
            diff_lines_uncovered=5,
        )
        db.session.add(file_coverage)

    return file_coverage


def patch(project, **kwargs):
    kwargs.setdefault('diff', SAMPLE_DIFF)

    patch = Patch(
        repository=project.repository,
        project=project,
        **kwargs
    )
    db.session.add(patch)

    return patch


def source(repository, **kwargs):
    if not kwargs.get('revision_sha'):
        kwargs['revision_sha'] = revision(repository, author()).sha

    source = Source(repository=repository, **kwargs)
    db.session.add(source)

    return source


def test_result(jobstep, **kwargs):
    if 'package' not in kwargs:
        kwargs['package'] = TEST_PACKAGES.next()

    if 'name' not in kwargs:
        kwargs['name'] = TEST_NAMES.next() + '_' + uuid4().hex

    if 'duration' not in kwargs:
        kwargs['duration'] = random.randint(0, 3000)

    kwargs.setdefault('result', Result.passed)

    result = TestResult(step=jobstep, **kwargs)

    return result

########NEW FILE########
__FILENAME__ = artifact
import uuid

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict


class Artifact(db.Model):
    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    step_id = Column(GUID, ForeignKey('jobstep.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    name = Column(String(128), nullable=False)
    date_created = Column(DateTime, nullable=False, default=datetime.utcnow)
    data = Column(JSONEncodedDict)

    job = relationship('Job', backref=backref('artifacts'))
    project = relationship('Project')
    step = relationship('JobStep', backref=backref('artifacts'))

    __tablename__ = 'artifact'
    __table_args__ = (
        UniqueConstraint('step_id', 'name', name='unq_artifact_name'),
    )

    def __init__(self, **kwargs):
        super(Artifact, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.data is None:
            self.data = {}

########NEW FILE########
__FILENAME__ = author
import uuid

from datetime import datetime
from sqlalchemy import Column, String, DateTime

from changes.config import db
from changes.db.types.guid import GUID


class Author(db.Model):
    __tablename__ = 'author'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(128), nullable=False)
    email = Column(String(128), unique=True)
    date_created = Column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(Author, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()

########NEW FILE########
__FILENAME__ = build
from __future__ import absolute_import

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index, UniqueConstraint
from sqlalchemy.sql import func, select

from changes.config import db
from changes.constants import Status, Result, Cause
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr


class Build(db.Model):
    """
    Represents a collection of builds for a single target, as well as the sum
    of their results.

    Each Build contains many Jobs (usually linked to a JobPlan).
    """
    __tablename__ = 'build'
    __table_args__ = (
        Index('idx_buildfamily_project_id', 'project_id'),
        Index('idx_buildfamily_author_id', 'author_id'),
        Index('idx_buildfamily_source_id', 'source_id'),
        UniqueConstraint('project_id', 'number', name='unq_build_number'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    number = Column(Integer)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    source_id = Column(GUID, ForeignKey('source.id', ondelete="CASCADE"))
    author_id = Column(GUID, ForeignKey('author.id', ondelete="CASCADE"))
    cause = Column(Enum(Cause), nullable=False, default=Cause.unknown)
    label = Column(String(128), nullable=False)
    target = Column(String(128))
    status = Column(Enum(Status), nullable=False, default=Status.unknown)
    result = Column(Enum(Result), nullable=False, default=Result.unknown)
    message = Column(Text)
    duration = Column(Integer)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONEncodedDict)

    project = relationship('Project', innerjoin=True)
    source = relationship('Source', innerjoin=True)
    author = relationship('Author')

    __repr__ = model_repr('label', 'target')

    def __init__(self, **kwargs):
        super(Build, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.status is None:
            self.status = Status.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created
        if self.date_started and self.date_finished and not self.duration:
            self.duration = (self.date_finished - self.date_started).total_seconds() * 1000
        if self.number is None and self.project:
            self.number = select([func.next_item_value(self.project.id.hex)])

########NEW FILE########
__FILENAME__ = buildphase
import uuid

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.constants import Status, Result
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID


class BuildPhase(db.Model):
    """
    A build phase represents a grouping of jobs.

    For example, a common situation for a build is that it has a "test" and a
    "release" phase. In this case, we'd have one or more jobs under test, and
    one or more jobs under release. These test jobs may be things like "Windows"
    and "Linux", whereas the release may simply be "Upload Tarball".

    The build phase represents the aggregate result of all jobs under it.
    """
    __tablename__ = 'buildphase'
    __table_args__ = (
        UniqueConstraint('build_id', 'label', name='unq_buildphase_key'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    label = Column(String(128), nullable=False)
    status = Column(Enum(Status), nullable=False, default=Status.unknown,
                    server_default='0')
    result = Column(Enum(Result), nullable=False, default=Result.unknown,
                    server_default='0')
    order = Column(Integer, nullable=False, default=0, server_default='0')
    duration = Column(Integer)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False,
                          server_default='now()')

    build = relationship('Build', backref=backref('phases', order_by='BuildPhase.date_started'))
    project = relationship('Project')

    def __init__(self, **kwargs):
        super(BuildPhase, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.status is None:
            self.status = Result.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_started and self.date_finished and not self.duration:
            self.duration = (self.date_finished - self.date_started).total_seconds() * 1000

########NEW FILE########
__FILENAME__ = buildseen
from __future__ import absolute_import

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.utils import model_repr


class BuildSeen(db.Model):
    __tablename__ = 'buildseen'
    __table_args__ = (
        UniqueConstraint('build_id', 'user_id', name='unq_buildseen_entity'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    build_id = Column(GUID, ForeignKey('build.id', ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    build = relationship('Build')
    user = relationship('User')

    __repr__ = model_repr('build_id', 'user_id')

    def __init__(self, **kwargs):
        super(BuildSeen, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()

########NEW FILE########
__FILENAME__ = change

from datetime import datetime
from hashlib import sha1
from sqlalchemy import (
    Column, DateTime, ForeignKey, String, Text
)
from sqlalchemy.orm import relationship, backref
from uuid import uuid4

from changes.config import db
from changes.db.types.guid import GUID


class Change(db.Model):
    """
    A change represents an independent change (eventually a single, finalized
    patch) and may contain many revisions of the same patch (which may be
    represented as many builds).

    Take for example a code review system like Phabricator. You submit a patch
    which is called a 'Revision', and inside of it there may be many 'diffs'. We
    attempt to represent the top level Revision as a singular Change.

    The primary component is the hash, which is determined by the backend and
    generally consists of something like SHA1(REVISION_ID).
    """
    __tablename__ = 'change'

    id = Column(GUID, primary_key=True, default=uuid4)
    hash = Column(String(40), unique=True, nullable=False)
    repository_id = Column(GUID, ForeignKey('repository.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    author_id = Column(GUID, ForeignKey('author.id', ondelete="CASCADE"))
    label = Column(String(128), nullable=False)
    message = Column(Text)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow)

    repository = relationship('Repository')
    project = relationship('Project', backref=backref('changes', order_by='Change.date_created'))
    author = relationship('Author')

    def __init__(self, **kwargs):
        super(Change, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.hash is None:
            self.hash = sha1(uuid4().hex).hexdigest()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = datetime.utcnow()

########NEW FILE########
__FILENAME__ = comment
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from uuid import uuid4

from changes.config import db
from changes.db.types.guid import GUID


class Comment(db.Model):
    __tablename__ = 'comment'

    id = Column(GUID, primary_key=True, default=uuid4)
    build_id = Column(GUID, ForeignKey('build.id', ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"))
    text = Column(Text)
    date_created = Column(DateTime, default=datetime.utcnow)

    build = relationship('Build')
    user = relationship('User')
    job = relationship('Job')

    def __init__(self, **kwargs):
        super(Comment, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()

########NEW FILE########
__FILENAME__ = event
from __future__ import absolute_import

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, String
from sqlalchemy.schema import Index, UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr


class EventType(object):
    email = 'email_notification'
    hipchat = 'hipchat_notification'
    green_build = 'green_build_notification'
    aborted_build = 'aborted_build'


class Event(db.Model):
    __tablename__ = 'event'
    __table_args__ = (
        Index('idx_event_item_id', 'item_id'),
        # Having this as unique prevents duplicate events, but in the future
        # we may want to allow duplicates
        # e.g. we can have a "sent email notification" event, but maybe
        # we'd want to have multiple of those
        UniqueConstraint('type', 'item_id', name='unq_event_key'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    type = Column(String(32), nullable=False)
    item_id = Column('item_id', GUID, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONEncodedDict)

    __repr__ = model_repr('type', 'item_id')

    def __init__(self, **kwargs):
        super(Event, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created

########NEW FILE########
__FILENAME__ = filecoverage
from __future__ import absolute_import, division

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index, UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID


class FileCoverage(db.Model):
    __tablename__ = 'filecoverage'
    __table_args__ = (
        Index('idx_filecoverage_job_id', 'job_id'),
        Index('idx_filecoverage_project_id', 'project_id'),
        UniqueConstraint('job_id', 'filename', name='unq_job_filname'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    step_id = Column(GUID, ForeignKey('jobstep.id', ondelete="CASCADE"))
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    filename = Column(String(256), nullable=False, primary_key=True)
    data = Column(Text)
    date_created = Column(DateTime, default=datetime.utcnow)

    lines_covered = Column(Integer)
    lines_uncovered = Column(Integer)
    diff_lines_covered = Column(Integer)
    diff_lines_uncovered = Column(Integer)

    step = relationship('JobStep')
    job = relationship('Job')
    project = relationship('Project')

    def __init__(self, **kwargs):
        super(FileCoverage, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()

########NEW FILE########
__FILENAME__ = itemsequence
from sqlalchemy import Column, Integer

from changes.config import db
from changes.db.types.guid import GUID


class ItemSequence(db.Model):
    __tablename__ = 'itemsequence'

    parent_id = Column(GUID, nullable=False, primary_key=True)
    value = Column(Integer, default=0, server_default='0', nullable=False,
                   primary_key=True)

########NEW FILE########
__FILENAME__ = itemstat
from uuid import uuid4

from sqlalchemy import Column, String, Integer
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID


class ItemStat(db.Model):
    __tablename__ = 'itemstat'
    __table_args__ = (
        UniqueConstraint('item_id', 'name', name='unq_itemstat_name'),
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    item_id = Column(GUID, nullable=False)
    name = Column(String(64), nullable=False)
    value = Column(Integer, nullable=False)

    def __init__(self, **kwargs):
        super(ItemStat, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()

########NEW FILE########
__FILENAME__ = job
import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Integer
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import Index, UniqueConstraint
from sqlalchemy.sql import func, select

from changes.config import db
from changes.constants import Status, Result
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr


class Job(db.Model):
    __tablename__ = 'job'
    __table_args__ = (
        Index('idx_build_project_id', 'project_id'),
        Index('idx_build_change_id', 'change_id'),
        Index('idx_build_source_id', 'source_id'),
        Index('idx_build_family_id', 'build_id'),
        UniqueConstraint('build_id', 'number', name='unq_job_number'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    number = Column(Integer)
    # TODO(dcramer): change should be removed in favor of an m2m between
    # Change and Source
    build_id = Column(GUID, ForeignKey('build.id', ondelete="CASCADE"))
    change_id = Column(GUID, ForeignKey('change.id', ondelete="CASCADE"))
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    source_id = Column(GUID, ForeignKey('source.id', ondelete="CASCADE"))
    label = Column(String(128), nullable=False)
    status = Column(Enum(Status), nullable=False, default=Status.unknown)
    result = Column(Enum(Result), nullable=False, default=Result.unknown)
    duration = Column(Integer)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONEncodedDict)

    change = relationship('Change')
    build = relationship('Build',
                         backref=backref('jobs', order_by='Job.number'),
                         innerjoin=True)
    project = relationship('Project')
    source = relationship('Source')

    __repr__ = model_repr('label', 'target')

    def __init__(self, **kwargs):
        super(Job, self).__init__(**kwargs)
        if self.data is None:
            self.data = {}
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.status is None:
            self.status = Status.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created
        if self.date_started and self.date_finished and not self.duration:
            self.duration = (self.date_finished - self.date_started).total_seconds() * 1000
        if self.number is None and self.build:
            self.number = select([func.next_item_value(self.build.id.hex)])

########NEW FILE########
__FILENAME__ = jobphase
import uuid

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.constants import Status, Result
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID


class JobPhase(db.Model):
    # TODO(dcramer): add order column rather than implicity date_started ordering
    # TODO(dcramer): make duration a column
    __tablename__ = 'jobphase'
    __table_args__ = (
        UniqueConstraint('job_id', 'label', name='unq_jobphase_key'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    label = Column(String(128), nullable=False)
    status = Column(Enum(Status), nullable=False, default=Status.unknown)
    result = Column(Enum(Result), nullable=False, default=Result.unknown)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)

    job = relationship('Job', backref=backref('phases', order_by='JobPhase.date_started'))
    project = relationship('Project')

    def __init__(self, **kwargs):
        super(JobPhase, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.status is None:
            self.status = Result.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()

    @property
    def duration(self):
        """
        Return the duration (in milliseconds) that this item was in-progress.
        """
        if self.date_started and self.date_finished:
            duration = (self.date_finished - self.date_started).total_seconds() * 1000
        else:
            duration = None
        return duration

########NEW FILE########
__FILENAME__ = jobplan
from __future__ import absolute_import

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.utils import model_repr


class JobPlan(db.Model):
    """
    A link to all Job + Plan's for a Build.

    TODO(dcramer): this should include a snapshot of the plan at build time.
    """
    __tablename__ = 'jobplan'
    __table_args__ = (
        Index('idx_buildplan_project_id', 'project_id'),
        Index('idx_buildplan_family_id', 'build_id'),
        Index('idx_buildplan_plan_id', 'plan_id'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    build_id = Column(GUID, ForeignKey('build.id', ondelete="CASCADE"), nullable=False)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False, unique=True)
    plan_id = Column(GUID, ForeignKey('plan.id', ondelete="CASCADE"), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow)

    project = relationship('Project')
    build = relationship('Build')
    job = relationship('Job')
    plan = relationship('Plan')

    __repr__ = model_repr('build_id', 'job_id', 'plan_id')

    def __init__(self, **kwargs):
        super(JobPlan, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created

########NEW FILE########
__FILENAME__ = jobstep
import uuid

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref

from changes.config import db
from changes.constants import Status, Result
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict


class JobStep(db.Model):
    # TODO(dcramer): make duration a column
    __tablename__ = 'jobstep'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    phase_id = Column(GUID, ForeignKey('jobphase.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    label = Column(String(128), nullable=False)
    status = Column(Enum(Status), nullable=False, default=Status.unknown)
    result = Column(Enum(Result), nullable=False, default=Result.unknown)
    node_id = Column(GUID, ForeignKey('node.id', ondelete="CASCADE"))
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONEncodedDict)

    job = relationship('Job')
    project = relationship('Project')
    node = relationship('Node')
    phase = relationship('JobPhase', backref=backref('steps', order_by='JobStep.date_started'))

    def __init__(self, **kwargs):
        super(JobStep, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.status is None:
            self.status = Result.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.data is None:
            self.data = {}

    @property
    def duration(self):
        """
        Return the duration (in milliseconds) that this item was in-progress.
        """
        if self.date_started and self.date_finished:
            duration = (self.date_finished - self.date_started).total_seconds() * 1000
        else:
            duration = None
        return duration

########NEW FILE########
__FILENAME__ = log
import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import Index, UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID


class LogSource(db.Model):
    __tablename__ = 'logsource'
    __table_args__ = (
        UniqueConstraint('job_id', 'name', name='unq_logsource_key'),
        # TODO: this should be unique based on the step, or if theres no
        # step it should be unique based on the job
        # UniqueConstraint('step_id', 'name', name='unq_logsource_key'),
        Index('idx_build_project_id', 'project_id'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    step_id = Column(GUID, ForeignKey('jobstep.id', ondelete="CASCADE"))
    name = Column(String(64), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)

    job = relationship('Job')
    project = relationship('Project')
    step = relationship('JobStep', backref=backref('logsources', order_by='LogSource.date_created'))

    def __init__(self, **kwargs):
        super(LogSource, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()


class LogChunk(db.Model):
    __tablename__ = 'logchunk'
    __table_args__ = (
        Index('idx_logchunk_project_id', 'project_id'),
        Index('idx_logchunk_build_id', 'job_id'),
        Index('idx_logchunk_source_id', 'source_id'),
        UniqueConstraint('source_id', 'offset', name='unq_logchunk_source_offset'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    source_id = Column(GUID, ForeignKey('logsource.id', ondelete="CASCADE"), nullable=False)
    # offset is sum(c.size for c in chunks_before_this)
    offset = Column(Integer, nullable=False)
    # size is len(text)
    size = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)

    job = relationship('Job')
    project = relationship('Project')
    source = relationship('LogSource')

    def __init__(self, **kwargs):
        super(LogChunk, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()

########NEW FILE########
__FILENAME__ = node
import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import backref, relationship

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr


class Cluster(db.Model):
    __tablename__ = 'cluster'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    label = Column(String(128), unique=True)
    date_created = Column(DateTime, default=datetime.utcnow)

    plans = association_proxy('cluster_nodes', 'node')

    __repr__ = model_repr('label')


class ClusterNode(db.Model):
    __tablename__ = 'cluster_node'

    cluster_id = Column(GUID, ForeignKey('cluster.id', ondelete="CASCADE"),
                        nullable=False, primary_key=True)
    node_id = Column(GUID, ForeignKey('node.id', ondelete="CASCADE"),
                     nullable=False, primary_key=True)
    date_created = Column(DateTime, default=datetime.utcnow)

    cluster = relationship('Cluster', backref=backref(
        "cluster_nodes", cascade="all, delete-orphan"))
    node = relationship('Node', backref=backref(
        "node_clusters", cascade="all, delete-orphan"))

    def __init__(self, cluster=None, node=None, **kwargs):
        kwargs.setdefault('cluster', cluster)
        kwargs.setdefault('node', node)
        super(ClusterNode, self).__init__(**kwargs)


class Node(db.Model):
    __tablename__ = 'node'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    label = Column(String(128), unique=True)
    data = Column(JSONEncodedDict)
    date_created = Column(DateTime, default=datetime.utcnow)

    clusters = association_proxy('node_clusters', 'cluster')

    __repr__ = model_repr('label')

    def __init__(self, *args, **kwargs):
        super(Node, self).__init__(*args, **kwargs)
        if not self.id:
            self.id = uuid.uuid4()

########NEW FILE########
__FILENAME__ = option
from uuid import uuid4

from datetime import datetime
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID


class ItemOption(db.Model):
    __tablename__ = 'itemoption'
    __table_args__ = (
        UniqueConstraint('item_id', 'name', name='unq_itemoption_name'),
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    item_id = Column(GUID, nullable=False)
    name = Column(String(64), nullable=False)
    value = Column(Text, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, **kwargs):
        super(ItemOption, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()

########NEW FILE########
__FILENAME__ = patch
from uuid import uuid4

from datetime import datetime
from sqlalchemy import (
    Column, DateTime, ForeignKey, String, Text
)
from sqlalchemy.orm import relationship

from changes.config import db
from changes.db.types.guid import GUID


class Patch(db.Model):
    # TODO(dcramer): a patch is repo specific, not project specific, and the
    # label/message/etc aren't super useful
    __tablename__ = 'patch'

    id = Column(GUID, primary_key=True, default=uuid4)
    change_id = Column(GUID, ForeignKey('change.id', ondelete="CASCADE"))
    repository_id = Column(GUID, ForeignKey('repository.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    parent_revision_sha = Column(String(40))
    diff = Column(Text)
    date_created = Column(DateTime, default=datetime.utcnow)

    change = relationship('Change')
    repository = relationship('Repository')
    project = relationship('Project')

    def __init__(self, **kwargs):
        super(Patch, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()

########NEW FILE########
__FILENAME__ = plan
from uuid import uuid4

from datetime import datetime
from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.associationproxy import association_proxy

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr


class Plan(db.Model):
    """
    Represents one of N build plans for a project.
    """
    id = Column(GUID, primary_key=True, default=uuid4)
    label = Column(String(128), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_modified = Column(DateTime, default=datetime.utcnow, nullable=False)
    data = Column(JSONEncodedDict)

    projects = association_proxy('plan_projects', 'project')

    __repr__ = model_repr('label')
    __tablename__ = 'plan'

    def __init__(self, **kwargs):
        super(Plan, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created

########NEW FILE########
__FILENAME__ = project
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import backref, relationship, joinedload
from sqlalchemy.schema import UniqueConstraint
from uuid import uuid4

from changes.config import db
from changes.constants import ProjectStatus
from changes.db.types.guid import GUID
from changes.db.types.enum import Enum
from changes.utils.slugs import slugify


class Project(db.Model):
    __tablename__ = 'project'

    id = Column(GUID, primary_key=True, default=uuid4)
    slug = Column(String(64), unique=True, nullable=False)
    repository_id = Column(GUID, ForeignKey('repository.id', ondelete="RESTRICT"), nullable=False)
    name = Column(String(64))
    date_created = Column(DateTime, default=datetime.utcnow)
    avg_build_time = Column(Integer)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.active,
                    server_default='1')

    repository = relationship('Repository')
    plans = association_proxy('project_plans', 'plan')

    def __init__(self, **kwargs):
        super(Project, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid4()
        if not self.slug:
            self.slug = slugify(self.name)

    @classmethod
    def get(cls, id):
        project = cls.query.options(
            joinedload(cls.repository, innerjoin=True),
        ).filter_by(slug=id).first()
        if project is None and len(id) == 32:
            project = cls.query.options(
                joinedload(cls.repository),
            ).get(id)
        return project


class ProjectOption(db.Model):
    __tablename__ = 'projectoption'
    __table_args__ = (
        UniqueConstraint('project_id', 'name', name='unq_projectoption_name'),
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    name = Column(String(64), nullable=False)
    value = Column(Text, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship('Project')

    def __init__(self, **kwargs):
        super(ProjectOption, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()


class ProjectPlan(db.Model):
    __tablename__ = 'project_plan'

    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"),
                        nullable=False, primary_key=True)
    plan_id = Column(GUID, ForeignKey('plan.id', ondelete="CASCADE"),
                     nullable=False, primary_key=True)
    avg_build_time = Column(Integer)

    project = relationship('Project', backref=backref(
        "project_plans", cascade="all, delete-orphan"))
    plan = relationship('Plan', backref=backref(
        "plan_projects", cascade="all, delete-orphan"))

    def __init__(self, project=None, plan=None, **kwargs):
        kwargs.setdefault('project', project)
        kwargs.setdefault('plan', plan)
        super(ProjectPlan, self).__init__(**kwargs)

########NEW FILE########
__FILENAME__ = remoteentity
import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, String, UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict


class RemoteEntity(db.Model):
    __tablename__ = 'remoteentity'
    __table_args__ = (
        UniqueConstraint('provider', 'remote_id', 'type', name='remote_identifier'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    type = Column(String, nullable=False)
    provider = Column(String(128), nullable=False)
    remote_id = Column(String(128), nullable=False)
    internal_id = Column(GUID, nullable=False)
    data = Column(JSONEncodedDict, default=dict)
    date_created = Column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(RemoteEntity, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
        if not self.data:
            self.data = {}

    def fetch_instance(self):
        return self.type.model.query.get(self.internal_id)

########NEW FILE########
__FILENAME__ = repository
import os.path
from uuid import uuid4

from datetime import datetime
from enum import Enum
from flask import current_app
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from changes.config import db
from changes.db.types.enum import Enum as EnumType
from changes.db.types.guid import GUID


class RepositoryBackend(Enum):
    unknown = 0
    git = 1
    hg = 2

    def __str__(self):
        return BACKEND_LABELS[self]


BACKEND_LABELS = {
    RepositoryBackend.unknown: 'Unknown',
    RepositoryBackend.git: 'git',
    RepositoryBackend.hg: 'hg',
}


class Repository(db.Model):
    __tablename__ = 'repository'

    id = Column(GUID, primary_key=True, default=uuid4)
    url = Column(String(200), nullable=False, unique=True)
    backend = Column(EnumType(RepositoryBackend),
                     default=RepositoryBackend.unknown, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)

    last_update = Column(DateTime)
    last_update_attempt = Column(DateTime)

    def __init__(self, **kwargs):
        super(Repository, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid4()
        if not self.date_created:
            self.date_created = datetime.utcnow()

    def get_vcs(self):
        from changes.vcs.git import GitVcs
        from changes.vcs.hg import MercurialVcs

        options = dict(
            db.session.query(
                RepositoryOption.name, RepositoryOption.value
            ).filter(
                RepositoryOption.repository_id == self.id,
                RepositoryOption.name.in_([
                    'auth.username',
                ])
            )
        )

        kwargs = {
            'path': os.path.join(current_app.config['REPO_ROOT'], self.id.hex),
            'url': self.url,
            'username': options.get('auth.username'),
        }

        if self.backend == RepositoryBackend.git:
            return GitVcs(**kwargs)
        elif self.backend == RepositoryBackend.hg:
            return MercurialVcs(**kwargs)
        else:
            return None

    @classmethod
    def get(cls, id):
        result = cls.query.filter_by(url=id).first()
        if result is None and len(id) == 32:
            result = cls.query.get(id)
        return result


class RepositoryOption(db.Model):
    __tablename__ = 'repositoryoption'
    __table_args__ = (
        UniqueConstraint('repository_id', 'name', name='unq_repositoryoption_name'),
    )

    id = Column(GUID, primary_key=True, default=uuid4)
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    name = Column(String(64), nullable=False)
    value = Column(Text, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)

    repository = relationship('Repository')

########NEW FILE########
__FILENAME__ = revision
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from changes.config import db
from changes.db.types.guid import GUID


class Revision(db.Model):
    __tablename__ = 'revision'

    repository_id = Column(GUID, ForeignKey('repository.id'), primary_key=True)
    sha = Column(String(40), primary_key=True)
    author_id = Column(GUID, ForeignKey('author.id'))
    committer_id = Column(GUID, ForeignKey('author.id'))
    message = Column(Text)
    parents = Column(ARRAY(String(40)))
    branches = Column(ARRAY(String(128)))
    date_created = Column(DateTime, default=datetime.utcnow)
    date_committed = Column(DateTime, default=datetime.utcnow)

    repository = relationship('Repository')
    author = relationship('Author', foreign_keys=[author_id])
    committer = relationship('Author', foreign_keys=[committer_id])

    def __init__(self, **kwargs):
        super(Revision, self).__init__(**kwargs)
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_committed is None:
            self.date_committed = self.date_created

    @property
    def subject(self):
        return self.message.splitlines()[0]

########NEW FILE########
__FILENAME__ = source

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint, ForeignKeyConstraint
from uuid import uuid4

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict


class Source(db.Model):
    """
    A source represents the canonical parameters that a build is running against.

    It always implies a revision to build off (though until we have full repo
    integration this is considered optional, and defaults to tip/master), and
    an optional patch_id to apply on top of it.
    """
    id = Column(GUID, primary_key=True, default=uuid4)
    repository_id = Column(GUID, ForeignKey('repository.id'), nullable=False)
    patch_id = Column(GUID, ForeignKey('patch.id'))
    revision_sha = Column(String(40))
    date_created = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONEncodedDict)

    repository = relationship('Repository')
    patch = relationship('Patch')
    revision = relationship('Revision',
                            foreign_keys=[repository_id, revision_sha],
                            innerjoin=True)

    __tablename__ = 'source'
    __table_args__ = (
        ForeignKeyConstraint(
            ('repository_id', 'revision_sha'),
            ('revision.repository_id', 'revision.sha')
        ),
        UniqueConstraint(
            'repository_id', 'revision_sha', name='unq_source_revision',
            # postgresql_where=(patch_id == None)
        ),
        UniqueConstraint(
            'patch_id', name='unq_source_patch_id',
            # postgresql_where=(patch_id != None),
        ),
    )

    def __init__(self, **kwargs):
        super(Source, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()

    def generate_diff(self):
        if self.patch:
            return self.patch.diff

        vcs = self.repository.get_vcs()
        if vcs:
            try:
                return vcs.export(self.revision_sha)
            except Exception:
                pass

        return None

    def is_commit(self):
        return self.patch_id is None and self.revision_sha

########NEW FILE########
__FILENAME__ = step
from uuid import uuid4

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Integer
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import UniqueConstraint, CheckConstraint

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr
from changes.utils.imports import import_string


class Step(db.Model):
    """
    Represents one of N build steps for a plan.
    """
    # TODO(dcramer): only a single step is currently supported
    id = Column(GUID, primary_key=True, default=uuid4)
    plan_id = Column(GUID, ForeignKey('plan.id', ondelete='CASCADE'), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_modified = Column(DateTime, default=datetime.utcnow, nullable=False)
    # implementation should be class path notation
    implementation = Column(String(128), nullable=False)
    order = Column(Integer, nullable=False)
    data = Column(JSONEncodedDict)

    plan = relationship('Plan', backref=backref('steps', order_by='Step.order'))

    __repr__ = model_repr('plan_id', 'implementation')
    __tablename__ = 'step'
    __table_args__ = (
        UniqueConstraint('plan_id', 'order', name='unq_plan_key'),
        CheckConstraint(order >= 0, name='chk_step_order_positive'),
    )

    def __init__(self, **kwargs):
        super(Step, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created

    def get_implementation(self, load=True):
        try:
            cls = import_string(self.implementation)
        except Exception:
            return None

        if not load:
            return cls

        try:
            return cls(**self.data)
        except Exception:
            return None

########NEW FILE########
__FILENAME__ = task
from __future__ import absolute_import

import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, String, Integer
from sqlalchemy.schema import Index, UniqueConstraint

from changes.config import db
from changes.constants import Result, Status
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr


class Task(db.Model):
    __tablename__ = 'task'
    __table_args__ = (
        Index('idx_task_parent_id', 'parent_id', 'task_name'),
        Index('idx_task_child_id', 'child_id', 'task_name'),
        UniqueConstraint('task_name', 'parent_id', 'child_id', name='unq_task_entity'),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    task_name = Column(String(128), nullable=False)
    task_id = Column('child_id', GUID, nullable=False)
    parent_id = Column(GUID)
    status = Column(Enum(Status), nullable=False, default=Status.unknown)
    result = Column(Enum(Result), nullable=False, default=Result.unknown)
    num_retries = Column(Integer, nullable=False, default=0)
    date_started = Column(DateTime)
    date_finished = Column(DateTime)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow)
    data = Column(JSONEncodedDict)

    __repr__ = model_repr('task_name', 'parent_id', 'child_id', 'status')

    def __init__(self, **kwargs):
        super(Task, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()
        if self.date_modified is None:
            self.date_modified = self.date_created

    @classmethod
    def check(cls, task_name, parent_id):
        """
        >>> if Task.check('my_task', parent_item.id) == Status.finished:
        >>>     print "all child tasks done!"
        """
        # XXX(dcramer): we could make this fast if we're concerneda bout # of
        # rows by doing two network hops (first check for in progress, then
        # report result)
        child_tasks = list(db.session.query(
            cls.result, Task.status
        ).filter(
            cls.task_name == task_name,
            cls.parent_id == parent_id,
        ))
        if any(r.status != Status.finished for r in child_tasks):
            return Status.in_progress
        return Status.finished

########NEW FILE########
__FILENAME__ = test
from __future__ import absolute_import, division

import re
import uuid

from datetime import datetime
from hashlib import sha1
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.event import listen
from sqlalchemy.orm import deferred, relationship
from sqlalchemy.schema import UniqueConstraint, Index

from changes.config import db
from changes.constants import Result
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID
from changes.db.utils import model_repr


class TestCase(db.Model):
    """
    An individual test result.
    """
    __tablename__ = 'test'
    __table_args__ = (
        UniqueConstraint('job_id', 'label_sha', name='unq_test_name'),
        Index('idx_test_step_id', 'step_id'),
        Index('idx_test_project_key', 'project_id', 'label_sha'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    step_id = Column(GUID, ForeignKey('jobstep.id', ondelete="CASCADE"))
    name_sha = Column('label_sha', String(40), nullable=False)
    name = Column(Text, nullable=False)
    _package = Column('package', Text, nullable=True)
    result = Column(Enum(Result), default=Result.unknown, nullable=False)
    duration = Column(Integer, default=0)
    message = deferred(Column(Text))
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)
    reruns = Column(Integer)

    job = relationship('Job')
    step = relationship('JobStep')
    project = relationship('Project')

    __repr__ = model_repr('name', '_package', 'result')

    def __init__(self, **kwargs):
        super(TestCase, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.result is None:
            self.result = Result.unknown
        if self.date_created is None:
            self.date_created = datetime.utcnow()

    @classmethod
    def calculate_name_sha(self, name):
        if name:
            return sha1(name).hexdigest()
        raise ValueError

    @property
    def sep(self):
        name = (self._package or self.name)
        # handle the case where it might begin with some special character
        if not re.match(r'^[a-zA-Z0-9]', name):
            return '/'
        elif '/' in name:
            return '/'
        return '.'

    def _get_package(self):
        if not self._package:
            try:
                package, _ = self.name.rsplit(self.sep, 1)
            except ValueError:
                package = None
        else:
            package = self._package
        return package

    def _set_package(self, value):
        self._package = value

    package = property(_get_package, _set_package)

    @property
    def short_name(self):
        name, package = self.name, self.package
        if package and name.startswith(package) and name != package:
            return name[len(package) + 1:]
        return name


def set_name_sha(target, value, oldvalue, initiator):
    if not value:
        return value

    new_sha = sha1(value).hexdigest()
    if new_sha != target.name_sha:
        target.name_sha = new_sha
    return value


listen(TestCase.name, 'set', set_name_sha, retval=False)

########NEW FILE########
__FILENAME__ = testresult
from __future__ import absolute_import, division

import logging
import re

from datetime import datetime
from sqlalchemy.sql import func

from changes.config import db
from changes.constants import Result
from changes.db.utils import create_or_update
from changes.models import ItemStat, TestCase

logger = logging.getLogger('changes.testresult')


class TestResult(object):
    """
    A helper class which ensures that TestSuite instances are
    managed correctly when TestCase's are created.
    """
    def __init__(self, step, name, message=None, package=None,
                 result=None, duration=None, date_created=None,
                 reruns=None):
        self.step = step
        self._name = name
        self._package = package
        self.message = message
        self.result = result or Result.unknown
        self.duration = duration  # ms
        self.date_created = date_created or datetime.utcnow()
        self.reruns = reruns or 0

    @property
    def sep(self):
        name = (self._package or self._name)
        # handle the case where it might begin with some special character
        if not re.match(r'^[a-zA-Z0-9]', name):
            return '/'
        elif '/' in name:
            return '/'
        return '.'

    @property
    def name_sha(self):
        return TestCase.calculate_name_sha(self.name)

    @property
    def package(self):
        return None

    @property
    def name(self):
        if self._package:
            return "%s%s%s" % (self._package, self.sep, self._name)
        return self._name
    id = name


class TestResultManager(object):
    def __init__(self, step):
        self.step = step

    def clear(self):
        """
        Removes all existing test data from this job.
        """
        TestCase.query.filter(
            TestCase.step_id == self.step.id,
        ).delete(synchronize_session=False)

    def save(self, test_list):
        if not test_list:
            return

        step = self.step
        job = step.job
        project = job.project
        # agg_groups_by_id = {}

        # create all test cases
        for test in test_list:
            testcase = TestCase(
                job=job,
                step=step,
                name_sha=test.name_sha,
                project=project,
                name=test.name,
                duration=test.duration,
                message=test.message,
                result=test.result,
                date_created=test.date_created,
                reruns=test.reruns
            )
            db.session.add(testcase)

        db.session.commit()

        try:
            self._record_test_counts(test_list)
            self._record_test_failures(test_list)
            self._record_test_duration(test_list)
            self._record_test_rerun_counts(test_list)
        except Exception:
            logger.exception('Failed to record aggregate test statistics')

    def _record_test_counts(self, test_list):
        create_or_update(ItemStat, where={
            'item_id': self.step.id,
            'name': 'test_count',
        }, values={
            'value': db.session.query(func.count(TestCase.id)).filter(
                TestCase.step_id == self.step.id,
            ).as_scalar(),
        })
        db.session.commit()

    def _record_test_failures(self, test_list):
        create_or_update(ItemStat, where={
            'item_id': self.step.id,
            'name': 'test_failures',
        }, values={
            'value': db.session.query(func.count(TestCase.id)).filter(
                TestCase.step_id == self.step.id,
                TestCase.result == Result.failed,
            ).as_scalar(),
        })
        db.session.commit()

    def _record_test_duration(self, test_list):
        create_or_update(ItemStat, where={
            'item_id': self.step.id,
            'name': 'test_duration',
        }, values={
            'value': db.session.query(func.coalesce(func.sum(TestCase.duration), 0)).filter(
                TestCase.step_id == self.step.id,
            ).as_scalar(),
        })

    def _record_test_rerun_counts(self, test_list):
        create_or_update(ItemStat, where={
            'item_id': self.step.id,
            'name': 'test_rerun_count',
        }, values={
            'value': db.session.query(func.count(TestCase.id)).filter(
                TestCase.step_id == self.step.id,
                TestCase.reruns > 0,
            ).as_scalar(),
        })

########NEW FILE########
__FILENAME__ = user
import uuid

from datetime import datetime
from sqlalchemy import Boolean, Column, String, DateTime

from changes.config import db
from changes.db.types.guid import GUID


class User(db.Model):
    __tablename__ = 'user'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    email = Column(String(128), unique=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if not self.id:
            self.id = uuid.uuid4()
        if not self.date_created:
            self.date_created = datetime.utcnow()

########NEW FILE########
__FILENAME__ = task
from __future__ import absolute_import

import logging

from datetime import datetime, timedelta
from functools import wraps
from threading import local, Lock
from uuid import uuid4

from changes.config import db, queue
from changes.constants import Result, Status
from changes.db.utils import get_or_create
from changes.models import Task
from changes.utils.locking import lock


BASE_RETRY_COUNTDOWN = 60
CONTINUE_COUNTDOWN = 5

RUN_TIMEOUT = timedelta(minutes=5)
EXPIRE_TIMEOUT = timedelta(minutes=30)
HARD_TIMEOUT = timedelta(hours=12)

MAX_RETRIES = 10


class NotFinished(Exception):
    pass


class TooManyRetries(Exception):
    pass


class TrackedTask(local):
    """
    Tracks the state of the given Task and it's children.

    Tracked tasks **never** return a result.

    >>> @tracked_task
    >>> def func(foo):
    >>>    if random.randint(0, 1) == 1:
    >>>        # re-queue for further results
    >>>        raise func.NotFinished
    >>>
    >>>    elif random.randint(0, 1) == 1:
    >>>        # cause an exception to retry
    >>>        raise Exception
    >>>
    >>>    # finish normally to update Status
    >>>    print "func", foo
    >>> foo.delay(foo='bar', task_id='bar')
    """
    NotFinished = NotFinished

    def __init__(self, func, max_retries=MAX_RETRIES, on_abort=None):
        self.func = lock(func)
        self.task_name = func.__name__
        self.parent_id = None
        self.task_id = None
        self.lock = Lock()
        self.logger = logging.getLogger('jobs.{0}'.format(self.task_name))

        self.max_retries = max_retries
        self.on_abort = on_abort

        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
        self.__wraps__ = getattr(func, '__wraps__', func)
        self.__code__ = getattr(func, '__code__', None)

    def __call__(self, **kwargs):
        with self.lock:
            self._run(kwargs)

    def __repr__(self):
        return '<%s: task_name=%s>' % (type(self), self.task_name)

    def _run(self, kwargs):
        self.task_id = kwargs.pop('task_id', None)
        if self.task_id is None:
            self.task_id = uuid4().hex

        self.parent_id = kwargs.pop('parent_task_id', None)
        self.kwargs = kwargs

        date_started = datetime.utcnow()

        try:
            self.func(**kwargs)

        except NotFinished:
            self.logger.info(
                'Task marked as not finished: %s %s', self.task_name, self.task_id)

            self._continue(kwargs)

        except Exception as exc:
            db.session.rollback()

            self.logger.exception(unicode(exc))

            try:
                self._retry()
            except TooManyRetries as exc:
                date_finished = datetime.utcnow()

                self._update({
                    Task.date_finished: date_finished,
                    Task.date_modified: date_finished,
                    Task.status: Status.finished,
                    Task.result: Result.failed,
                })
                self.logger.exception(unicode(exc))

                if self.on_abort:
                    self.on_abort(self)
            except Exception as exc:
                self.logger.exception(unicode(exc))
                raise

        else:
            date_finished = datetime.utcnow()

            try:
                self._update({
                    Task.date_started: date_started,
                    Task.date_finished: date_finished,
                    Task.date_modified: date_finished,
                    Task.status: Status.finished,
                    Task.result: Result.passed,
                })
            except Exception as exc:
                self.logger.exception(unicode(exc))
                raise

            db.session.commit()
        finally:
            db.session.expire_all()

            self.task_id = None
            self.parent_id = None
            self.kwargs = kwargs

    def _update(self, kwargs):
        """
        Update's the state of this Task.

        >>> task._update(status=Status.finished)
        """
        assert self.task_id

        Task.query.filter(
            Task.task_name == self.task_name,
            Task.task_id == self.task_id,
        ).update(kwargs, synchronize_session=False)

    def _continue(self, kwargs):
        kwargs['task_id'] = self.task_id
        kwargs['parent_task_id'] = self.parent_id

        self._update({
            Task.date_modified: datetime.utcnow(),
            Task.status: Status.in_progress,
        })

        db.session.commit()

        queue.delay(
            self.task_name,
            kwargs=kwargs,
            countdown=CONTINUE_COUNTDOWN,
        )

    def _retry(self):
        """
        Retry this task and update it's state.

        >>> task.retry()
        """
        # TODO(dcramer): this needs to handle too-many-retries itself
        assert self.task_id

        task = Task.query.filter(
            Task.task_name == self.task_name,
            Task.task_id == self.task_id,
        ).first()
        if task and self.max_retries and task.num_retries > self.max_retries:
            date_finished = datetime.utcnow()
            self._update({
                Task.date_finished: date_finished,
                Task.date_modified: date_finished,
                Task.status: Status.finished,
                Task.result: Result.failed,
            })
            db.session.commit()

            raise TooManyRetries

        self._update({
            Task.date_modified: datetime.utcnow(),
            Task.status: Status.in_progress,
            Task.num_retries: Task.num_retries + 1,
        })

        db.session.commit()

        kwargs = self.kwargs.copy()
        kwargs['task_id'] = self.task_id
        kwargs['parent_task_id'] = self.parent_id

        retry_number = db.session.query(Task.num_retries).filter(
            Task.task_name == self.task_name,
            Task.task_id == self.task_id,
        ).scalar() or 0

        retry_countdown = min(BASE_RETRY_COUNTDOWN + (retry_number ** 3), 3600)

        queue.delay(
            self.task_name,
            kwargs=kwargs,
            countdown=retry_countdown,
        )

    def needs_requeued(self, task):
        if self.max_retries and task.num_retries >= self.max_retries:
            return False

        current_datetime = datetime.utcnow()

        timeout_datetime = current_datetime - HARD_TIMEOUT
        if task.date_created < timeout_datetime:
            return False

        run_datetime = current_datetime - RUN_TIMEOUT
        return task.date_modified < run_datetime

    def needs_expired(self, task):
        if self.max_retries and task.num_retries >= self.max_retries:
            return True

        current_datetime = datetime.utcnow()

        timeout_datetime = current_datetime - HARD_TIMEOUT
        if task.date_created < timeout_datetime:
            return True

        expire_datetime = current_datetime - EXPIRE_TIMEOUT
        if task.date_modified < expire_datetime:
            return True

        return False

    def delay_if_needed(self, **kwargs):
        """
        Enqueue this task if it's new or hasn't checked in in a reasonable
        amount of time.

        >>> task.delay_if_needed(
        >>>     task_id='33846695b2774b29a71795a009e8168a',
        >>>     parent_task_id='659974858dcf4aa08e73a940e1066328',
        >>> )
        """
        kwargs.setdefault('task_id', uuid4().hex)

        fn_kwargs = dict(
            (k, v) for k, v in kwargs.iteritems()
            if k not in ('task_id', 'parent_task_id')
        )

        task, created = get_or_create(Task, where={
            'task_name': self.task_name,
            'task_id': kwargs['task_id'],
        }, defaults={
            'parent_id': kwargs.get('parent_task_id'),
            'data': {
                'kwargs': fn_kwargs,
            },
            'status': Status.queued,
        })

        if created or self.needs_requeued(task):
            if not created:
                task.date_modified = datetime.utcnow()
                db.session.add(task)

            db.session.commit()

            queue.delay(
                self.task_name,
                kwargs=kwargs,
                countdown=CONTINUE_COUNTDOWN,
            )

    def delay(self, **kwargs):
        """
        Enqueue this task.

        >>> task.delay(
        >>>     task_id='33846695b2774b29a71795a009e8168a',
        >>>     parent_task_id='659974858dcf4aa08e73a940e1066328',
        >>> )
        """
        kwargs.setdefault('task_id', uuid4().hex)

        fn_kwargs = dict(
            (k, v) for k, v in kwargs.iteritems()
            if k not in ('task_id', 'parent_task_id')
        )

        task, created = get_or_create(Task, where={
            'task_name': self.task_name,
            'task_id': kwargs['task_id'],
        }, defaults={
            'parent_id': kwargs.get('parent_task_id'),
            'data': {
                'kwargs': fn_kwargs,
            },
            'status': Status.queued,
        })

        if not created:
            task.date_modified = datetime.utcnow()
            db.session.add(task)

        db.session.commit()

        queue.delay(
            self.task_name,
            kwargs=kwargs,
            countdown=CONTINUE_COUNTDOWN,
        )

    def verify_all_children(self):
        task_list = list(Task.query.filter(
            Task.parent_id == self.task_id
        ))

        current_datetime = datetime.utcnow()

        need_expire = set()
        need_run = set()

        has_pending = False

        for task in task_list:
            if task.status == Status.finished:
                continue

            if self.needs_expired(task):
                need_expire.add(task)
                continue

            has_pending = True

            if self.needs_requeued(task) and 'kwargs' in task.data:
                need_run.add(task)

        if need_expire:
            Task.query.filter(
                Task.id.in_([n.id for n in need_expire]),
            ).update({
                Task.date_modified: current_datetime,
                Task.date_finished: current_datetime,
                Task.status: Status.finished,
                Task.result: Result.aborted,
            }, synchronize_session=False)
            db.session.commit()

        if need_run:
            for task in need_run:
                child_kwargs = task.data['kwargs'].copy()
                child_kwargs['parent_task_id'] = task.parent_id.hex
                child_kwargs['task_id'] = task.task_id.hex
                queue.delay(task.task_name, kwargs=child_kwargs)

            Task.query.filter(
                Task.id.in_([n.id for n in need_run]),
            ).update({
                Task.date_modified: current_datetime,
            }, synchronize_session=False)
            db.session.commit()

        if has_pending:
            status = Status.in_progress

        else:
            status = Status.finished

        return status


# bind to a decorator-like naming scheme
def tracked_task(func=None, **kwargs):
    def wrapped(func):
        return wraps(func)(TrackedTask(func, **kwargs))

    if func:
        return wraps(func)(wrapped(func))
    return wrapped

########NEW FILE########
__FILENAME__ = build
from __future__ import absolute_import, division

from collections import defaultdict
from datetime import datetime, timedelta
from sqlalchemy.sql import func

from changes.config import db
from changes.constants import Status, Result
from changes.models import Build, TestCase, Source
from changes.utils.http import build_uri


SLOW_TEST_THRESHOLD = 3000  # ms

ONE_DAY = 60 * 60 * 24


class BuildReport(object):
    def __init__(self, projects):
        self.projects = set(projects)

    def generate(self, end_period=None, days=7):
        if end_period is None:
            end_period = datetime.utcnow()

        days_delta = timedelta(days=days)
        start_period = end_period - days_delta

        current_results = self.get_project_stats(
            start_period, end_period)
        previous_results = self.get_project_stats(
            start_period - days_delta, start_period)

        for project, stats in current_results.iteritems():
            previous_stats = previous_results.get(project)
            if not previous_stats:
                green_change = None
                duration_change = None
            elif stats['green_percent'] is None:
                green_change = None
                duration_change = None
            elif previous_stats['green_percent'] is None:
                green_change = None
                duration_change = None
            else:
                green_change = stats['green_percent'] - previous_stats['green_percent']
                duration_change = stats['avg_duration'] - previous_stats['avg_duration']

            stats['avg_duration'] = stats['avg_duration']

            stats['percent_change'] = green_change
            stats['duration_change'] = duration_change

        projects_by_green_builds = sorted(
            current_results.items(), key=lambda x: (
                -abs(x[1]['green_percent'] or 0), -(x[1]['percent_change'] or 0),
                x[0].name,
            ))

        projects_by_build_time = sorted(
            current_results.items(), key=lambda x: (
                -abs(x[1]['avg_duration'] or 0), (x[1]['duration_change'] or 0),
                x[0].name,
            ))

        slow_tests = self.get_slow_tests(start_period, end_period)
        # flakey_tests = self.get_frequent_failures(start_period, end_period)
        flakey_tests = []

        title = 'Build Report ({0} through {1})'.format(
            start_period.strftime('%b %d, %Y'),
            end_period.strftime('%b %d, %Y'),
        )

        return {
            'title': title,
            'period': [start_period, end_period],
            'projects_by_build_time': projects_by_build_time,
            'projects_by_green_builds': projects_by_green_builds,
            'tests': {
                'slow_list': slow_tests,
                'flakey_list': flakey_tests,
            },
        }

    def get_project_stats(self, start_period, end_period):
        projects_by_id = dict((p.id, p) for p in self.projects)
        project_ids = projects_by_id.keys()

        # fetch overall build statistics per project
        query = db.session.query(
            Build.project_id, Build.result,
            func.count(Build.id).label('num'),
            func.avg(Build.duration).label('duration'),
        ).join(
            Source, Source.id == Build.source_id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Build.project_id.in_(project_ids),
            Build.status == Status.finished,
            Build.result.in_([Result.failed, Result.passed]),
            Build.date_created >= start_period,
            Build.date_created < end_period,
        ).group_by(Build.project_id, Build.result)

        project_results = {}
        for project in self.projects:
            project_results[project] = {
                'total_builds': 0,
                'green_builds': 0,
                'green_percent': None,
                'avg_duration': 0,
                'link': build_uri('/projects/{0}/'.format(project.slug)),
            }

        for project_id, result, num_builds, duration in query:
            if duration is None:
                duration = 0

            project = projects_by_id[project_id]

            if result == Result.passed:
                project_results[project]['avg_duration'] = duration

            project_results[project]['total_builds'] += num_builds
            if result == Result.passed:
                project_results[project]['green_builds'] += num_builds

        for project, stats in project_results.iteritems():
            if stats['total_builds']:
                stats['green_percent'] = int(stats['green_builds'] / stats['total_builds'] * 100)
            else:
                stats['green_percent'] = None

        return project_results

    def get_slow_tests(self, start_period, end_period):
        slow_tests = []
        for project in self.projects:
            slow_tests.extend(self.get_slow_tests_for_project(
                project, start_period, end_period))
        slow_tests.sort(key=lambda x: x['duration_raw'], reverse=True)
        return slow_tests[:10]

    def get_slow_tests_for_project(self, project, start_period, end_period):
        latest_build = Build.query.filter(
            Build.project == project,
            Build.status == Status.finished,
            Build.result == Result.passed,
            Build.date_created >= start_period,
            Build.date_created < end_period,
        ).order_by(
            Build.date_created.desc(),
        ).limit(1).first()

        if not latest_build:
            return []

        job_list = list(latest_build.jobs)
        if not job_list:
            return []

        queryset = db.session.query(
            TestCase.name, TestCase.duration,
        ).filter(
            TestCase.job_id.in_(j.id for j in job_list),
            TestCase.result == Result.passed,
            TestCase.date_created > start_period,
            TestCase.date_created <= end_period,
        ).group_by(
            TestCase.name, TestCase.duration,
        ).order_by(TestCase.duration.desc())

        slow_list = []
        for name, duration in queryset[:10]:
            slow_list.append({
                'project': project,
                'name': name,
                'package': '',  # TODO
                'duration': '%.2f s' % (duration / 1000.0,),
                'duration_raw': duration,
                # 'link': build_uri('/projects/{0}/tests/{1}/'.format(
                #     project.slug, agg_id.hex)),
            })

        return slow_list

    def get_frequent_failures(self, start_period, end_period):
        projects_by_id = dict((p.id, p) for p in self.projects)
        project_ids = projects_by_id.keys()

        queryset = db.session.query(
            TestCase.name,
            TestCase.project_id,
            TestCase.result,
            func.count(TestCase.id).label('num'),
        ).filter(
            TestCase.project_id.in_(project_ids),
            TestCase.result.in_([Result.passed, Result.failed]),
            TestCase.date_created > start_period,
            TestCase.date_created <= end_period,
        ).group_by(
            TestCase.name,
            TestCase.project_id,
            TestCase.result,
        )

        test_results = defaultdict(lambda: {
            'passed': 0,
            'failed': 0,
        })
        for name, project_id, result, count in queryset:
            # TODO: parent name
            test_results[(name, '', project_id)][result.name] += count

        if not test_results:
            return []

        tests_with_pct = []
        for test_key, counts in test_results.iteritems():
            total = counts['passed'] + counts['failed']
            if counts['failed'] == 0:
                continue
            # exclude tests which haven't been seen frequently
            elif total < 5:
                continue
            else:
                pct = counts['failed'] / total * 100
            # if the test has failed 100% of the time, it's not flakey
            if pct == 100:
                continue
            tests_with_pct.append((test_key, pct, total, counts['failed']))
        tests_with_pct.sort(key=lambda x: x[1], reverse=True)

        flakiest_tests = tests_with_pct[:10]

        if not flakiest_tests:
            return []

        results = []
        for test_key, pct, total, fail_count in flakiest_tests:
            (name, parent_name, project_id) = test_key

            if parent_name:
                name = name[len(parent_name) + 1:]

            # project = projects_by_id[project_id]

            results.append({
                'name': name,
                'package': parent_name,
                'fail_pct': int(pct),
                'fail_count': fail_count,
                'total_count': total,
                # 'link': build_uri('/projects/{0}/tests/{1}/'.format(
                #     project.slug, agg.id.hex)),
            })

        return results

    def _date_to_key(self, dt):
        return int(dt.replace(
            minute=0, hour=0, second=0, microsecond=0
        ).strftime('%s'))

########NEW FILE########
__FILENAME__ = cases
from __future__ import absolute_import

import mock
import json
import unittest

from exam import Exam, fixture
from flask import current_app as app

from changes.config import db, mail
from changes.models import User
from changes.testutils.fixtures import Fixtures


class AuthMixin(object):
    @fixture
    def default_user(self):
        user = User(
            email='foo@example.com',
        )
        db.session.add(user)
        db.session.commit()

        return user

    @fixture
    def default_admin(self):
        user = User(
            email='bar@example.com',
            is_admin=True,
        )
        db.session.add(user)
        db.session.commit()

        return user

    def login(self, user):
        with self.client.session_transaction() as session:
            session['uid'] = user.id.hex
            session['email'] = user.email

    def login_default(self):
        return self.login(self.default_user)

    def login_default_admin(self):
        return self.login(self.default_admin)


class TestCase(Exam, unittest.TestCase, Fixtures, AuthMixin):
    def setUp(self):
        self.repo = self.create_repo(
            url='https://github.com/dropbox/changes.git',
        )
        self.project = self.create_project(
            repository=self.repo,
            name='test',
            slug='test'
        )
        self.project2 = self.create_project(
            repository=self.repo,
            name='test2',
            slug='test2',
        )

        self.plan = self.create_plan()
        self.plan.projects.append(self.project)
        db.session.commit()

        # mock out mail
        mail_context = mail.record_messages()
        self.outbox = mail_context.__enter__()
        self.addCleanup(lambda: mail_context.__exit__(None, None, None))

        self.client = app.test_client()

        super(TestCase, self).setUp()

    def unserialize(self, response):
        assert response.headers['Content-Type'] == 'application/json'
        return json.loads(response.data)


class BackendTestCase(TestCase):
    backend_cls = None
    backend_options = {}
    provider = None

    def get_backend(self):
        return self.backend_cls(
            app=app, **self.backend_options
        )


class APITestCase(TestCase):
    def setUp(self):
        from changes.backends.base import BaseBackend

        super(APITestCase, self).setUp()

        self.mock_backend = mock.Mock(
            spec=BaseBackend(app=app),
        )
        self.patcher = mock.patch(
            'changes.api.base.APIView.get_backend',
            mock.Mock(return_value=self.mock_backend))
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

########NEW FILE########
__FILENAME__ = fixtures
from __future__ import absolute_import

__all__ = ('Fixtures', 'SAMPLE_COVERAGE', 'SAMPLE_DIFF', 'SAMPLE_XUNIT')

from loremipsum import get_paragraphs, get_sentences
from uuid import uuid4

from changes.config import db
from changes.models import (
    Repository, Job, JobPlan, Project, Revision, Change, Author,
    Patch, Plan, Step, Build, Source, Node, JobPhase, JobStep, Task,
    Artifact, TestCase, LogChunk, LogSource, Cluster, ClusterNode
)
from changes.utils.slugs import slugify


SAMPLE_COVERAGE = """<?xml version="1.0" ?>
<!DOCTYPE coverage
  SYSTEM 'http://cobertura.sourceforge.net/xml/coverage-03.dtd'>
<coverage branch-rate="0" line-rate="0.4483" timestamp="1375818307337" version="3.6">
    <!-- Generated by coverage.py: http://nedbatchelder.com/code/coverage -->
    <packages>
        <package branch-rate="0" complexity="0" line-rate="0.4483" name="">
            <classes>
                <class branch-rate="0" complexity="0" filename="setup.py" line-rate="0" name="setup">
                    <methods/>
                    <lines>
                        <line hits="0" number="2"/>
                        <line hits="0" number="12"/>
                        <line hits="1" number="13"/>
                        <line hits="1" number="14"/>
                        <line hits="0" number="16"/>
                    </lines>
                </class>
                <class branch-rate="0" complexity="0" filename="src/pytest_phabricator/plugin.py" line-rate="0.1875" name="src/pytest_phabricator/plugin">
                    <methods/>
                    <lines>
                        <line hits="1" number="1"/>
                        <line hits="1" number="2"/>
                        <line hits="1" number="3"/>
                        <line hits="0" number="7"/>
                    </lines>
                </class>
            </classes>
        </package>
    </packages>
</coverage>"""

with open('sample.diff', 'r') as f:
    SAMPLE_DIFF = f.read()

SAMPLE_XUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuite errors="1" failures="0" name="" skips="0" tests="0" time="0.077">
    <testcase classname="" name="tests.test_report" time="0">
        <failure message="collection failure">tests/test_report.py:1: in &lt;module&gt;
&gt;   import mock
E   ImportError: No module named mock</failure>
    </testcase>
    <testcase classname="tests.test_report.ParseTestResultsTest" name="test_simple" time="0.00165796279907" rerun="1"/>
</testsuite>"""


class Fixtures(object):
    def create_repo(self, **kwargs):
        kwargs.setdefault('url', 'http://example.com/{0}'.format(uuid4().hex))

        repo = Repository(**kwargs)
        db.session.add(repo)
        db.session.commit()

        return repo

    def create_node(self, cluster=None, **kwargs):
        kwargs.setdefault('label', uuid4().hex)

        node = Node(**kwargs)
        db.session.add(node)

        if cluster:
            db.session.add(ClusterNode(cluster=cluster, node=node))

        db.session.commit()

        return node

    def create_cluster(self, **kwargs):
        kwargs.setdefault('label', uuid4().hex)

        cluster = Cluster(**kwargs)
        db.session.add(cluster)
        db.session.commit()

        return cluster

    def create_project(self, **kwargs):
        if not kwargs.get('repository'):
            kwargs['repository'] = self.create_repo()
        kwargs['repository_id'] = kwargs['repository'].id
        kwargs.setdefault('name', uuid4().hex)
        kwargs.setdefault('slug', kwargs['name'])

        project = Project(**kwargs)
        db.session.add(project)
        db.session.commit()

        return project

    def create_change(self, project, **kwargs):
        kwargs.setdefault('label', 'Sample')

        change = Change(
            hash=uuid4().hex,
            repository=project.repository,
            project=project,
            **kwargs
        )
        db.session.add(change)
        db.session.commit()

        return change

    def create_test(self, job, **kwargs):
        kwargs.setdefault('name', uuid4().hex)

        case = TestCase(
            job=job,
            project=job.project,
            project_id=job.project_id,
            job_id=job.id,
            **kwargs
        )
        db.session.add(case)
        db.session.commit()

        return case

    def create_job(self, build, **kwargs):
        project = build.project

        kwargs.setdefault('label', build.label)
        kwargs.setdefault('status', build.status)
        kwargs.setdefault('result', build.result)
        kwargs.setdefault('duration', build.duration)
        kwargs.setdefault('date_started', build.date_started)
        kwargs.setdefault('date_finished', build.date_finished)
        kwargs.setdefault('source', build.source)

        if kwargs.get('change', False) is False:
            kwargs['change'] = self.create_change(project)

        job = Job(
            build=build,
            build_id=build.id,
            project=project,
            project_id=project.id,
            **kwargs
        )
        db.session.add(job)
        db.session.commit()

        return job

    def create_job_plan(self, job, plan):
        job_plan = JobPlan(
            project_id=job.project_id,
            build_id=job.build_id,
            plan_id=plan.id,
            job_id=job.id,
        )
        db.session.add(job_plan)
        db.session.commit()

        return job_plan

    def create_source(self, project, **kwargs):
        if 'revision_sha' not in kwargs:
            revision = self.create_revision(repository=project.repository)
            kwargs['revision_sha'] = revision.sha

        source = Source(
            repository_id=project.repository_id,
            **kwargs
        )
        db.session.add(source)
        db.session.commit()

        return source

    def create_build(self, project, **kwargs):
        if 'source' not in kwargs:
            kwargs['source'] = self.create_source(project)

        kwargs['source_id'] = kwargs['source'].id

        kwargs.setdefault('label', 'Sample')

        build = Build(
            project_id=project.id,
            project=project,
            **kwargs
        )
        db.session.add(build)
        db.session.commit()

        return build

    def create_patch(self, project, **kwargs):
        kwargs.setdefault('diff', SAMPLE_DIFF)
        kwargs.setdefault('parent_revision_sha', uuid4().hex)
        if not kwargs.get('repository'):
            kwargs['repository'] = self.create_repo()
        kwargs['repository_id'] = kwargs['repository'].id

        patch = Patch(
            project=project,
            project_id=project.id,
            **kwargs
        )
        db.session.add(patch)
        db.session.commit()

        return patch

    def create_revision(self, **kwargs):
        kwargs.setdefault('sha', uuid4().hex)
        if not kwargs.get('repository'):
            kwargs['repository'] = self.create_repo()
        kwargs['repository_id'] = kwargs['repository'].id

        if not kwargs.get('author'):
            kwargs['author'] = self.create_author()
        kwargs['author_id'] = kwargs['author'].id

        if not kwargs.get('message'):
            message = get_sentences(1)[0][:128] + '\n'
            message += '\n\n'.join(get_paragraphs(2))
            kwargs['message'] = message

        revision = Revision(**kwargs)
        db.session.add(revision)
        db.session.commit()

        return revision

    def create_author(self, email=None, **kwargs):
        if not kwargs.get('name'):
            kwargs['name'] = ' '.join(get_sentences(1)[0].split(' ')[0:2])

        if not email:
            email = '{0}-{1}@example.com'.format(
                slugify(kwargs['name']), uuid4().hex)

        kwargs.setdefault('name', 'Test Case')

        author = Author(email=email, **kwargs)
        db.session.add(author)
        db.session.commit()

        return author

    def create_plan(self, **kwargs):
        kwargs.setdefault('label', 'test')

        plan = Plan(**kwargs)
        db.session.add(plan)
        db.session.commit()

        return plan

    def create_step(self, plan, **kwargs):
        kwargs.setdefault('implementation', 'changes.backends.buildstep.BuildStep')
        kwargs.setdefault('order', 0)

        step = Step(plan=plan, **kwargs)
        db.session.add(step)
        db.session.commit()

        return step

    def create_jobphase(self, job, **kwargs):
        kwargs.setdefault('label', 'test')
        kwargs.setdefault('result', job.result)
        kwargs.setdefault('status', job.status)

        phase = JobPhase(
            job=job,
            project=job.project,
            **kwargs
        )
        db.session.add(phase)
        db.session.commit()

        return phase

    def create_jobstep(self, phase, **kwargs):
        kwargs.setdefault('label', phase.label)
        kwargs.setdefault('result', phase.result)
        kwargs.setdefault('status', phase.status)

        step = JobStep(
            job=phase.job,
            project=phase.project,
            phase=phase,
            **kwargs
        )
        db.session.add(step)
        db.session.commit()

        return step

    def create_task(self, **kwargs):
        kwargs.setdefault('task_id', uuid4())

        task = Task(**kwargs)
        db.session.add(task)
        db.session.commit()

        return task

    def create_artifact(self, step, **kwargs):
        artifact = Artifact(
            step=step,
            project=step.project,
            job=step.job,
            **kwargs
        )
        db.session.add(artifact)
        db.session.commit()

        return artifact

    def create_logsource(self, step=None, **kwargs):
        if step:
            kwargs['job'] = step.job
        kwargs['project'] = kwargs['job'].project

        logsource = LogSource(
            step=step,
            **kwargs
        )
        db.session.add(logsource)
        db.session.commit()

        return logsource

    def create_logchunk(self, source, text=None, **kwargs):
        # TODO(dcramer): we should default offset to previosu entry in LogSource
        kwargs.setdefault('offset', 0)
        kwargs['job'] = source.job
        kwargs['project'] = source.project

        if text is None:
            text = '\n'.join(get_sentences(4))

        logchunk = LogChunk(
            source=source,
            text=text,
            size=len(text),
            **kwargs
        )
        db.session.add(logchunk)
        db.session.commit()

        return logchunk

########NEW FILE########
__FILENAME__ = helpers
from functools import wraps
from mock import patch

from changes.config import queue
from changes.queue.task import TooManyRetries


def eager_tasks(func):
    @wraps(func)
    # prevent retries due to recursion issues
    def wrapped(*args, **kwargs):
        with patch('changes.queue.task.TrackedTask._retry', side_effect=TooManyRetries()):
            queue.celery.conf.CELERY_ALWAYS_EAGER = True
            try:
                return func(*args, **kwargs)
            finally:
                queue.celery.conf.CELERY_ALWAYS_EAGER = False
    return wrapped

########NEW FILE########
__FILENAME__ = uuid
from __future__ import absolute_import

from uuid import UUID
from werkzeug.routing import BaseConverter, ValidationError


class UUIDConverter(BaseConverter):
    """
    UUID converter for the Werkzeug routing system.
    """
    def to_python(self, value):
        try:
            return UUID(value)
        except ValueError:
            raise ValidationError

    def to_url(self, value):
        return str(value)

########NEW FILE########
__FILENAME__ = agg
def safe_agg(func, sequence, default=None):
    m = default
    for item in sequence:
        if item is None:
            continue
        elif m is None:
            m = item
        elif item:
            m = func(m, item)
    return m

########NEW FILE########
__FILENAME__ = diff_parser
# Copyright (c) 2007, Armin Ronacher
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. All advertising materials mentioning features or use of this software
#    must display the following acknowledgement:
#    This product includes software developed by the <organization>.
# 4. Neither the name of the <organization> nor the
#    names of its contributors may be used to endorse or promote products
#    derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY <COPYRIGHT HOLDER> ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import re


class DiffParser(object):
    """
    This is based on code from the open source project, "lodgeit".
    """
    _chunk_re = re.compile(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')

    def __init__(self, udiff):
        """:param udiff:   a text in udiff format"""
        self.lines = udiff.splitlines()

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

    def parse(self):
        in_header = True
        header = []
        lineiter = iter(self.lines)
        files = []
        try:
            line = lineiter.next()
            while 1:
                # continue until we found the old file
                if not line.startswith('--- '):
                    if in_header:
                        header.append(line)
                    line = lineiter.next()
                    continue

                if header and all(x.strip() for x in header):
                    # files.append({'is_header': True, 'lines': header})
                    header = []

                in_header = False
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
                        in_header = True
                        break

                    lines = []
                    chunks.append(lines)

                    old_line, old_end, new_line, new_end = [
                        int(x or 1) for x in match.groups()
                    ]
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

        return files

########NEW FILE########
__FILENAME__ = http
from __future__ import absolute_import, print_function

from flask import current_app


def build_uri(path, app=current_app):
    return str('{base_uri}/{path}'.format(
        base_uri=app.config['BASE_URI'].rstrip('/'),
        path=path.lstrip('/'),
    ))

########NEW FILE########
__FILENAME__ = imports
import pkgutil
import sys


class ModuleProxyCache(dict):
    def __missing__(self, key):
        if '.' not in key:
            return __import__(key)

        module_name, class_name = key.rsplit('.', 1)

        module = __import__(module_name, {}, {}, [class_name], -1)
        handler = getattr(module, class_name)

        # We cache a NoneType for missing imports to avoid repeated lookups
        self[key] = handler

        return handler

_cache = ModuleProxyCache()


def import_string(path):
    """
    Path must be module.path.ClassName

    >>> cls = import_string('sentry.models.Group')
    """
    result = _cache[path]
    return result


def import_submodules(context, root_module, path):
    for loader, module_name, is_pkg in pkgutil.walk_packages(path):
        module = loader.find_module(module_name).load_module(module_name)
        for k, v in vars(module).iteritems():
            if not k.startswith('_'):
                context[k] = v
        sys.modules['{0}.{1}'.format(root_module, module_name)] = module

########NEW FILE########
__FILENAME__ = locking
from flask import current_app
from functools import wraps
from hashlib import md5

from changes.ext.redis import UnableToGetLock
from changes.config import redis


def lock(func):
    @wraps(func)
    def wrapped(**kwargs):
        key = '{0}:{1}'.format(
            func.__name__,
            md5(
                '&'.join('{0}={1}'.format(k, repr(v))
                for k, v in sorted(kwargs.iteritems()))
            ).hexdigest()
        )
        try:
            with redis.lock(key, timeout=1, expire=300, nowait=True):
                return func(**kwargs)
        except UnableToGetLock:
            current_app.logger.warn('Unable to get lock for %s', key)

    return wrapped

########NEW FILE########
__FILENAME__ = originfinder
from __future__ import absolute_import

from collections import defaultdict

from changes.config import db
from changes.constants import Result, Status
from changes.models import Build, Job, TestCase, Source


def first(key, iterable):
    for x in iterable:
        if key(x):
            return x
    return None


def find_failure_origins(build, test_failures):
    """
    Attempt to find originating causes of failures.

    Returns a mapping of {TestCase.name_sha: Job}.
    """
    project = build.project

    if not test_failures:
        return {}

    # find any existing failures in the previous runs
    # to do this we first need to find the last passing job
    last_pass = Build.query.join(
        Source, Source.id == Build.source_id,
    ).filter(
        Build.project == project,
        Build.date_created <= build.date_created,
        Build.status == Status.finished,
        Build.result == Result.passed,
        Build.id != build.id,
        Source.patch == None,  # NOQA
    ).order_by(Build.date_created.desc()).first()

    if last_pass is None:
        return {}

    # We have to query all runs between build and last_pass. Because we're
    # paranoid about performance, we limit this to 100 results.
    previous_runs = Build.query.join(
        Source, Source.id == build.source_id,
    ).filter(
        Build.project == project,
        Build.date_created <= build.date_created,
        Build.date_created >= last_pass.date_created,
        Build.status == Status.finished,
        Build.result.in_([Result.failed, Result.passed]),
        Build.id != build.id,
        Build.id != last_pass.id,
        Source.patch == None,  # NOQA
    ).order_by(Build.date_created.desc())[:100]

    if not previous_runs:
        return {}

    # we now have a list of previous_runs so let's find all test failures in
    # these runs
    queryset = db.session.query(
        TestCase.name_sha, Job.build_id,
    ).join(
        Job, Job.id == TestCase.job_id,
    ).filter(
        Job.build_id.in_(b.id for b in previous_runs),
        Job.status == Status.finished,
        Job.result == Result.failed,
        TestCase.result == Result.failed,
        TestCase.name_sha.in_(t.name_sha for t in test_failures),
    ).group_by(
        TestCase.name_sha, Job.build_id
    )

    previous_test_failures = defaultdict(set)
    for name_sha, build_id in queryset:
        previous_test_failures[build_id].add(name_sha)

    failures_at_build = dict()
    searching = set(t for t in test_failures)
    last_checked_run = build

    for p_build in previous_runs:
        p_build_failures = previous_test_failures[p_build.id]
        # we have to copy the set as it might change size during iteration
        for f_test in list(searching):
            if f_test.name_sha not in p_build_failures:
                failures_at_build[f_test] = last_checked_run
                searching.remove(f_test)
        last_checked_run = p_build

    for f_test in searching:
        failures_at_build[f_test] = last_checked_run

    return failures_at_build

########NEW FILE########
__FILENAME__ = slugs
import re
import unicodedata

# Extra characters outside of alphanumerics that we'll allow.
SLUG_OK = '-_~'


def slugify(s, ok=SLUG_OK, lower=True, spaces=False):
    # L and N signify letter/number.
    # http://www.unicode.org/reports/tr44/tr44-4.html#GC_Values_Table
    rv = []
    for c in unicodedata.normalize('NFKC', unicode(s)):
        cat = unicodedata.category(c)[0]
        if cat in 'LN' or c in ok:
            rv.append(c)
        if cat == 'Z':  # space
            rv.append(' ')
    new = ''.join(rv).strip()
    if not spaces:
        new = re.sub('[-\s]+', '-', new)
    return new.lower() if lower else new

########NEW FILE########
__FILENAME__ = times
def duration(value):
    ONE_SECOND = 1000
    ONE_MINUTE = ONE_SECOND * 60

    if not value:
        return '0 s'

    abs_value = abs(value)

    if abs_value < 3 * ONE_SECOND:
        return '%d ms' % (value,)
    elif abs_value < 5 * ONE_MINUTE:
        return '%d s' % (value / ONE_SECOND,)
    else:
        return '%d m' % (value / ONE_MINUTE,)

########NEW FILE########
__FILENAME__ = trees
from collections import defaultdict


def build_tree(tests, sep='.', min_children=1, parent=''):
    h = defaultdict(set)

    # Build a mapping of prefix => set(children)
    for test in tests:
        segments = test.split(sep)
        for i in xrange(len(segments)):
            prefix = sep.join(segments[:i])
            h[prefix].add(sep.join(segments[:i + 1]))

    # This method expands each node if it has fewer than min_children children.
    # "Expand" here means replacing a node with its children.
    def expand(node='', sep='.', min_children=1):
        # Leave leaf nodes alone.
        if node in h:

            # Expand each child node (depth-first traversal).
            for child in list(h[node]):
                expand(child, sep, min_children)

            # If this node isn't big enough by itself...
            if len(h[node]) < min_children and node:
                parent = h[sep.join(node.split(sep)[:-1])]

                # Replace this node with its expansion.
                parent.remove(node)
                parent.update(h[node])

                del h[node]

    # Expand the tree, starting at the root.
    expand(sep=sep, min_children=min_children)

    if parent:
        return h[parent]
    return h['']

########NEW FILE########
__FILENAME__ = base
from __future__ import absolute_import, division, print_function

import os
import os.path
import re
from subprocess import Popen, PIPE

from changes.constants import PROJECT_ROOT
from changes.db.utils import create_or_update, get_or_create
from changes.models import Author, Revision


class CommandError(Exception):
    def __init__(self, cmd, retcode, stdout=None, stderr=None):
        self.cmd = cmd
        self.retcode = retcode
        self.stdout = stdout
        self.stderr = stderr

    def __unicode__(self):
        return '%s returned %d:\nSTDOUT: %r\nSTDERR: %r' % (
            self.cmd, self.retcode, self.stdout, self.stderr)


class BufferParser(object):
    def __init__(self, fp, delim):
        self.fp = fp
        self.delim = delim

    def __iter__(self):
        chunk_buffer = []
        for chunk in self.fp:
            while chunk.find(self.delim) != -1:
                d_pos = chunk.find(self.delim)

                chunk_buffer.append(chunk[:d_pos])

                yield ''.join(chunk_buffer)
                chunk_buffer = []

                chunk = chunk[d_pos + 1:]

            if chunk:
                chunk_buffer.append(chunk)

        if chunk_buffer:
            yield ''.join(chunk_buffer)


class Vcs(object):
    ssh_connect_path = os.path.join(PROJECT_ROOT, 'bin', 'ssh-connect')

    def __init__(self, path, url, username=None):
        self.path = path
        self.url = url
        self.username = username

        self._path_exists = None

    def get_default_env(self):
        return {}

    def run(self, *args, **kwargs):
        if self.exists():
            kwargs.setdefault('cwd', self.path)

        env = os.environ.copy()

        for key, value in self.get_default_env().iteritems():
            env.setdefault(key, value)

        env.setdefault('CHANGES_SSH_REPO', self.url)

        for key, value in kwargs.pop('env', {}):
            env[key] = value

        kwargs['env'] = env
        kwargs['stdout'] = PIPE
        kwargs['stderr'] = PIPE

        proc = Popen(*args, **kwargs)
        (stdout, stderr) = proc.communicate()
        if proc.returncode != 0:
            raise CommandError(args[0], proc.returncode, stdout, stderr)
        return stdout

    def exists(self):
        return os.path.exists(self.path)

    def clone(self):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError

    def log(self, parent=None, limit=100):
        raise NotImplementedError

    def export(self, id):
        raise NotImplementedError

    def get_revision(self, id):
        """
        Return a ``Revision`` given by ``id`.
        """
        return self.log(parent=id, limit=1).next()


class RevisionResult(object):
    def __init__(self, id, message, author, author_date, committer=None,
                 committer_date=None, parents=None, branches=None):
        self.id = id
        self.message = message
        self.author = author
        self.author_date = author_date
        self.committer = committer or author
        self.committer_date = committer_date or author_date
        self.parents = parents
        self.branches = branches

    def __repr__(self):
        return '<%s: id=%r author=%r subject=%r>' % (
            type(self).__name__, self.id, self.author, self.subject)

    def _get_author(self, value):
        match = re.match(r'^(.+) <([^>]+)>$', value)
        if not match:
            if '@' in value:
                name, email = value, value
            else:
                name, email = value, '{0}@localhost'.format(value)
        else:
            name, email = match.group(1), match.group(2)

        author, _ = get_or_create(Author, where={
            'email': email,
        }, defaults={
            'name': name,
        })

        return author

    @property
    def subject(self):
        return self.message.splitlines()[0]

    def save(self, repository):
        author = self._get_author(self.author)
        if self.author == self.committer:
            committer = author
        else:
            committer = self._get_author(self.committer)

        revision, created = create_or_update(Revision, where={
            'repository': repository,
            'sha': self.id,
        }, values={
            'author': author,
            'committer': committer,
            'message': self.message,
            'parents': self.parents,
            'branches': self.branches,
            'date_created': self.author_date,
            'date_committed': self.committer_date,
        })

        return (revision, created)

########NEW FILE########
__FILENAME__ = git
from __future__ import absolute_import, division, print_function

from datetime import datetime
from urlparse import urlparse

from .base import Vcs, RevisionResult, BufferParser

LOG_FORMAT = '%H\x01%an <%ae>\x01%at\x01%cn <%ce>\x01%ct\x01%P\x01%B\x02'

ORIGIN_PREFIX = 'remotes/origin/'


class GitVcs(Vcs):
    binary_path = 'git'

    def get_default_env(self):
        return {
            'GIT_SSH': self.ssh_connect_path,
        }

    @property
    def remote_url(self):
        if self.url.startswith(('ssh:', 'http:', 'https:')):
            parsed = urlparse(self.url)
            url = '%s://%s@%s/%s' % (
                parsed.scheme,
                parsed.username or self.username or 'git',
                parsed.hostname + (':%s' % (parsed.port,) if parsed.port else ''),
                parsed.path.lstrip('/'),
            )
        else:
            url = self.url
        return url

    def branches_for_commit(self, id):
        results = []
        output = self.run(['branch', '-a', '--contains', id])
        for result in output.splitlines():
            # HACK(dcramer): is there a better way around removing the prefix?
            result = result[2:].strip()
            if result.startswith(ORIGIN_PREFIX):
                result = result[len(ORIGIN_PREFIX):]
            if result == 'HEAD':
                continue
            results.append(result)
        return list(set(results))

    def run(self, cmd, **kwargs):
        cmd = [self.binary_path] + cmd
        return super(GitVcs, self).run(cmd, **kwargs)

    def clone(self):
        self.run(['clone', '--mirror', self.remote_url, self.path])

    def update(self):
        self.run(['fetch', '--all'])

    def log(self, parent=None, limit=100):
        # TODO(dcramer): we should make this streaming
        cmd = ['log', '--all', '--pretty=format:%s' % (LOG_FORMAT,)]
        if parent:
            cmd.append(parent)
        if limit:
            cmd.append('-n %d' % (limit,))
        result = self.run(cmd)

        for chunk in BufferParser(result, '\x02'):
            (sha, author, author_date, committer, committer_date,
             parents, message) = chunk.split('\x01')

            # sha may have a trailing newline due to git log adding it
            sha = sha.lstrip('\n')

            parents = filter(bool, parents.split(' '))

            author_date = datetime.utcfromtimestamp(float(author_date))
            committer_date = datetime.utcfromtimestamp(float(committer_date))

            yield RevisionResult(
                id=sha,
                author=author,
                committer=committer,
                author_date=author_date,
                committer_date=committer_date,
                parents=parents,
                branches=self.branches_for_commit(sha),
                message=message,
            )

    def export(self, id):
        cmd = ['log', '-n 1', '-p', '--pretty="%b"', id]
        result = self.run(cmd)[4:]
        return result

########NEW FILE########
__FILENAME__ = hg
from __future__ import absolute_import, division, print_function

from datetime import datetime
from rfc822 import parsedate_tz, mktime_tz
from urlparse import urlparse

from .base import Vcs, RevisionResult, BufferParser

LOG_FORMAT = '{node}\x01{author}\x01{date|rfc822date}\x01{p1node} {p2node}\x01{branches}\x01{desc}\x02'


class MercurialVcs(Vcs):
    binary_path = 'hg'

    def get_default_env(self):
        return {
            'HGPLAIN': '1',
        }

    @property
    def remote_url(self):
        if self.url.startswith(('ssh:', 'http:', 'https:')):
            parsed = urlparse(self.url)
            url = '%s://%s@%s/%s' % (
                parsed.scheme,
                parsed.username or self.username or 'hg',
                parsed.hostname + (':%s' % (parsed.port,) if parsed.port else ''),
                parsed.path.lstrip('/'),
            )
        else:
            url = self.url
        return url

    def run(self, cmd, **kwargs):
        cmd = [
            self.binary_path,
            '--config',
            'ui.ssh={0}'.format(self.ssh_connect_path)
        ] + cmd
        return super(MercurialVcs, self).run(cmd, **kwargs)

    def clone(self):
        self.run(['clone', '--uncompressed', self.remote_url, self.path])

    def update(self):
        self.run(['pull'])

    def log(self, parent=None, limit=100):
        # TODO(dcramer): we should make this streaming
        cmd = ['log', '--template=%s' % (LOG_FORMAT,)]
        if parent:
            cmd.append('-r reverse(ancestors(%s))' % (parent,))
        if limit:
            cmd.append('--limit=%d' % (limit,))
        result = self.run(cmd)

        for chunk in BufferParser(result, '\x02'):
            (sha, author, author_date, parents, branches, message) = chunk.split('\x01')

            branches = filter(bool, branches.split(' ')) or ['default']
            parents = filter(lambda x: x and x != '0' * 40, parents.split(' '))

            author_date = datetime.utcfromtimestamp(
                mktime_tz(parsedate_tz(author_date)))

            yield RevisionResult(
                id=sha,
                author=author,
                author_date=author_date,
                message=message,
                parents=parents,
                branches=branches,
            )

    def export(self, id):
        cmd = ['diff', '-g', '-c %s' % (id,)]
        result = self.run(cmd)
        return result

########NEW FILE########
__FILENAME__ = auth
import changes
import sys

from flask import current_app, redirect, request, session, url_for
from flask.views import MethodView
from oauth2client.client import OAuth2WebServerFlow

from changes.db.utils import get_or_create
from changes.models import User


def get_auth_flow(redirect_uri=None):
    # XXX(dcramer): we have to generate this each request because oauth2client
    # doesn't want you to set redirect_uri as part of the request, which causes
    # a lot of runtime issues.
    return OAuth2WebServerFlow(
        client_id=current_app.config['GOOGLE_CLIENT_ID'],
        client_secret=current_app.config['GOOGLE_CLIENT_SECRET'],
        scope='https://www.googleapis.com/auth/userinfo.email',
        redirect_uri=redirect_uri,
        user_agent='changes/{0} (python {1})'.format(
            changes.VERSION,
            sys.version,
        )
    )


class LoginView(MethodView):
    def __init__(self, authorized_url):
        self.authorized_url = authorized_url
        super(LoginView, self).__init__()

    def get(self):
        redirect_uri = url_for(self.authorized_url, _external=True)
        flow = get_auth_flow(redirect_uri=redirect_uri)
        auth_uri = flow.step1_get_authorize_url()
        return redirect(auth_uri)


class AuthorizedView(MethodView):
    def __init__(self, complete_url, authorized_url):
        self.complete_url = complete_url
        self.authorized_url = authorized_url
        super(AuthorizedView, self).__init__()

    def get(self):
        redirect_uri = url_for(self.authorized_url, _external=True)
        flow = get_auth_flow(redirect_uri=redirect_uri)
        resp = flow.step2_exchange(request.args['code'])

        if current_app.config['GOOGLE_DOMAIN']:
            # TODO(dcramer): confirm this is actually what this value means
            if resp.id_token.get('hd') != current_app.config['GOOGLE_DOMAIN']:
                # TODO(dcramer): this should show some kind of error
                return redirect(url_for(self.complete_url))

        user, _ = get_or_create(User, where={
            'email': resp.id_token['email'],
        })

        session['uid'] = user.id.hex
        session['access_token'] = resp.access_token
        session['email'] = resp.id_token['email']

        return redirect(url_for(self.complete_url))


class LogoutView(MethodView):
    def __init__(self, complete_url):
        self.complete_url = complete_url
        super(LogoutView, self).__init__()

    def get(self):
        session.pop('uid', None)
        session.pop('access_token', None)
        session.pop('email', None)
        return redirect(url_for(self.complete_url))

########NEW FILE########
__FILENAME__ = index
import changes
import urlparse

from flask import render_template, current_app
from flask.views import MethodView


class IndexView(MethodView):
    def get(self, path=''):
        if current_app.config['SENTRY_DSN'] and False:
            parsed = urlparse.urlparse(current_app.config['SENTRY_DSN'])
            dsn = '%s://%s@%s/%s' % (
                parsed.scheme.rsplit('+', 1)[-1],
                parsed.username,
                parsed.hostname + (':%s' % (parsed.port,) if parsed.port else ''),
                parsed.path,
            )
        else:
            dsn = None

        return render_template('index.html', **{
            'SENTRY_PUBLIC_DSN': dsn,
            'VERSION': changes.get_version(),
        })

########NEW FILE########
__FILENAME__ = static
from flask import current_app as app
from flask.helpers import send_from_directory
from flask.views import MethodView


class StaticView(MethodView):
    def __init__(self, root, cache_timeout=0):
        self.root = root
        self.cache_timeout = app.config['SEND_FILE_MAX_AGE_DEFAULT']

    def get(self, filename):
        return send_from_directory(
            self.root, filename, cache_timeout=self.cache_timeout)

########NEW FILE########
__FILENAME__ = conftest
import os
import pytest
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

from alembic.config import Config
from alembic import command
from sqlalchemy import event
from sqlalchemy.orm import Session

alembic_cfg = Config(os.path.join(root, 'alembic.ini'))

from changes.config import create_app, db


@pytest.fixture(scope='session')
def session_config(request):
    db_name = 'test_changes'

    return {
        'db_name': db_name,
        # TODO(dcramer): redis db is shared
        'redis_db': '9',
    }


@pytest.fixture(scope='session')
def app(request, session_config):
    app = create_app(
        _read_config=False,
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='postgresql:///' + session_config['db_name'],
        REDIS_URL='redis://localhost/' + session_config['redis_db'],
        BASE_URI='http://example.com',
        REPO_ROOT='/tmp',
        GREEN_BUILD_URL='https://foo.example.com',
        GREEN_BUILD_AUTH=('username', 'password'),
        JENKINS_URL='http://jenkins.example.com',
        JENKINS_SYNC_LOG_ARTIFACTS=True,
        GOOGLE_CLIENT_ID='a' * 12,
        GOOGLE_CLIENT_SECRET='b' * 40,
        HIPCHAT_TOKEN='abc',
    )
    app_context = app.test_request_context()
    context = app_context.push()

    # request.addfinalizer(app_context.pop)
    return app


@pytest.fixture(scope='session', autouse=True)
def setup_db(request, app, session_config):
    db_name = session_config['db_name']
    # 9.1 does not support --if-exists
    if os.system("psql -l | grep '%s'" % db_name) == 0:
        assert not os.system('dropdb %s' % db_name)
    assert not os.system('createdb -E utf-8 %s' % db_name)

    command.upgrade(alembic_cfg, 'head')

    @event.listens_for(Session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    # TODO: find a way to kill db connections so we can dropdob
    # def teardown():
    #     os.system('dropdb %s' % db_name)

    # request.addfinalizer(teardown)


@pytest.fixture(autouse=True)
def db_session(request):
    request.addfinalizer(db.session.remove)

    db.session.begin_nested()


@pytest.fixture(autouse=True)
def redis_session(request, app):
    import redis
    conn = redis.from_url(app.config['REDIS_URL'])
    conn.flushdb()

########NEW FILE########
__FILENAME__ = 10_changes_conf_from_env
#!/usr/bin/env python3

import json
import os
import re
import shutil

def setup_ssh_authorized_keys(env):
    DEST_DIR = "/etc/ssh/authorized_keys.env.d"

    lines_by_user = {}
    for name in env:
        if not name.startswith("authorized_keys:"):
            continue
        try:
            ak, user, n = name.split(":")
            int(n)
        except ValueError:
            continue
        else:
            if ak != "authorized_keys":
                continue

        if user not in lines_by_user:
            lines_by_user[user] = []

        try:
            for line in env[name].split("\n"):
                line = line.rstrip()
                lines_by_user[user].append(line)
        except Exception:
            continue

    # Clear the destination directory
    if os.path.exists(DEST_DIR):
        shutil.rmtree(DEST_DIR)
    os.mkdir(DEST_DIR)

    # Write new keys
    for user, lines in lines_by_user.items():
        with open(os.path.join(DEST_DIR, user), "w") as f:
            for line in lines:
                print(line, file=f)

def update_changes_conf(env):
    replace_vars = ('BASE_URI', 'SERVER_NAME', 'REPO_ROOT', 'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET')
    replace_regexes = tuple(re.compile("^(" + re.escape(n) + ")\s*=") for n in replace_vars)
    conf_filename = env['CHANGES_CONF']
    backup_filename = conf_filename + "~"
    temp_filename = conf_filename + ".tmp"

    # Save a backup
    shutil.copy2(conf_filename, backup_filename)

    # Replace vars and write to temp file
    with open(conf_filename, "r") as infile:
        with open(temp_filename, "w") as outfile:
            shutil.copystat(conf_filename, temp_filename)
            for line in infile:
                line = line.rstrip()
                for r in replace_regexes:
                    m = r.search(line)
                    if m:
                        name = m.group(1)
                        if name in env:
                            line = "{0} = {1!r}".format(name, env[name])
                            break
                print(line, file=outfile)

    # Rename-replace.  Hopefully, this wasn't a symlink.
    os.rename(temp_filename, conf_filename)

def main():
    with open("/etc/container_environment.json", "rb") as f:
        env = json.loads(f.read().decode('utf-8'))

    setup_ssh_authorized_keys(env)
    update_changes_conf(env)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Changes documentation build configuration file, created by
# sphinx-quickstart on Thu Dec 19 15:05:39 2013.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Changes'
copyright = u'2013, Dropbox, Inc.'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = __import__('pkg_resources').get_distribution('changes').version
# The full version, including alpha/beta/rc tags.
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'kr'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

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
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Changesdoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    ('index', 'Changes.tex', u'Changes Documentation',
     u'Dropbox, Inc.', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'changes', u'Changes Documentation',
     [u'Dropbox, Inc.'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'Changes', u'Changes Documentation',
     u'Dropbox, Inc.', 'Changes', 'One line description of project.',
     'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
__FILENAME__ = changes.conf
# ~/.changes/changes.conf.py
BASE_URI = 'http://localhost:5000'
SERVER_NAME = 'localhost:5000'

REPO_ROOT = '/tmp'

# You can obtain these values via the Google Developers Console:
# https://console.developers.google.com/
# Example 'Authorized JavaScript Origins': http://localhost:5000
# Example 'Authorized Redirect URIs': http://localhost:5000/auth/complete/
GOOGLE_CLIENT_ID = None
GOOGLE_CLIENT_SECRET = None

########NEW FILE########
__FILENAME__ = env
from __future__ import with_statement
from alembic import context
from logging.config import fileConfig

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

import sqlalchemy as sa
from changes.db.types.enum import Enum
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
sa.Enum = Enum
sa.GUID = GUID
sa.JSONEncodedDict = JSONEncodedDict

# add your model's MetaData object here
# for 'autogenerate' support
from flask import current_app
from changes.config import create_app, db

import warnings
from sqlalchemy.exc import SAWarning
warnings.simplefilter("ignore", SAWarning)

if not current_app:
    app = create_app()
else:
    app = current_app
app.app_context().push()
target_metadata = db.metadata

# force registration of models
import changes.models  # NOQA


def run_migrations():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connection = db.engine.connect()
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()

run_migrations()

########NEW FILE########
__FILENAME__ = 102eea94977e_set_on_delete_cascad
"""Set ON DELETE CASCADE on BuildStep.*

Revision ID: 102eea94977e
Revises: 469bba60eb50
Create Date: 2013-12-23 16:01:57.926119

"""

# revision identifiers, used by Alembic.
revision = '102eea94977e'
down_revision = '469bba60eb50'

from alembic import op


def upgrade():
    op.drop_constraint('buildstep_build_id_fkey', 'buildstep')
    op.create_foreign_key('buildstep_build_id_fkey', 'buildstep', 'build', ['build_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildstep_node_id_fkey', 'buildstep')
    op.create_foreign_key('buildstep_node_id_fkey', 'buildstep', 'node', ['node_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildstep_phase_id_fkey', 'buildstep')
    op.create_foreign_key('buildstep_phase_id_fkey', 'buildstep', 'buildphase', ['phase_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildstep_project_id_fkey', 'buildstep')
    op.create_foreign_key('buildstep_project_id_fkey', 'buildstep', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildstep_repository_id_fkey', 'buildstep')
    op.create_foreign_key('buildstep_repository_id_fkey', 'buildstep', 'repository', ['repository_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 105d4dd82a0a_date_indexes_on_test
"""Date indexes on TestGroup

Revision ID: 105d4dd82a0a
Revises: 2d9df8a3103c
Create Date: 2013-11-19 12:24:02.607191

"""

# revision identifiers, used by Alembic.
revision = '105d4dd82a0a'
down_revision = '2d9df8a3103c'

from alembic import op


def upgrade():
    op.create_index('idx_testgroup_project_date', 'testgroup', ['project_id', 'date_created'])


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 1109e724859f_add_itemoption
"""Add ItemOption

Revision ID: 1109e724859f
Revises: 3d9067f21201
Create Date: 2013-12-18 16:50:30.093508

"""

# revision identifiers, used by Alembic.
revision = '1109e724859f'
down_revision = '3d9067f21201'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'itemoption',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('item_id', sa.GUID(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('item_id', 'name', name='unq_itemoption_name')
    )


def downgrade():
    op.drop_table('itemoption')

########NEW FILE########
__FILENAME__ = 11a7a7f2652f_add_itemstat
"""Add ItemStat

Revision ID: 11a7a7f2652f
Revises: 4276d58dd1e6
Create Date: 2014-03-13 13:33:32.840399

"""

# revision identifiers, used by Alembic.
revision = '11a7a7f2652f'
down_revision = '4276d58dd1e6'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'itemstat',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('item_id', sa.GUID(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('value', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('item_id', 'name', name='unq_itemstat_name')
    )


def downgrade():
    op.drop_table('itemstat')

########NEW FILE########
__FILENAME__ = 139e272152de_index_jobphase
"""Index JobPhase

Revision ID: 139e272152de
Revises: 2f4637448764
Create Date: 2014-01-02 22:03:22.957636

"""

# revision identifiers, used by Alembic.
revision = '139e272152de'
down_revision = '2f4637448764'

from alembic import op


def upgrade():
    op.create_index('idx_jobphase_job_id', 'jobphase', ['job_id'])
    op.create_index('idx_jobphase_project_id', 'jobphase', ['project_id'])
    op.create_index('idx_jobphase_repository_id', 'jobphase', ['repository_id'])


def downgrade():
    op.drop_index('idx_jobphase_job_id', 'jobphase')
    op.drop_index('idx_jobphase_project_id', 'jobphase')
    op.drop_index('idx_jobphase_repository_id', 'jobphase')

########NEW FILE########
__FILENAME__ = 14491da59392_add_build_revision_s
"""Add Build.revision-sha

Revision ID: 14491da59392
Revises: 32274e97552
Create Date: 2013-10-29 11:43:47.367799

"""

# revision identifiers, used by Alembic.
revision = '14491da59392'
down_revision = '32274e97552'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('build', sa.Column('revision_sha', sa.String(length=40), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('build', 'revision_sha')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 152c9c780e_add_repositoryoption
"""Add RepositoryOption

Revision ID: 152c9c780e
Revises: 4d302aa44bc8
Create Date: 2013-11-26 17:48:21.180630

"""

# revision identifiers, used by Alembic.
revision = '152c9c780e'
down_revision = '4d302aa44bc8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('repositoryoption',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('repository_id', sa.GUID(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['repository_id'], ['repository.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('repository_id','name', name='unq_repositoryoption_name')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('repositoryoption')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 153b703a46ea_replace_step_phase_w
"""Replace Step/Phase with BuildStep/BuildPhase

Revision ID: 153b703a46ea
Revises: 2dfac13a4c78
Create Date: 2013-12-11 12:12:16.351785

"""

# revision identifiers, used by Alembic.
revision = '153b703a46ea'
down_revision = '2dfac13a4c78'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(
        'buildphase',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('repository_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=False),
        sa.Column('status', sa.Enum(), nullable=False),
        sa.Column('result', sa.Enum(), nullable=False),
        sa.Column('date_started', sa.DateTime(), nullable=True),
        sa.Column('date_finished', sa.DateTime(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.ForeignKeyConstraint(['repository_id'], ['repository.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'buildstep',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('phase_id', sa.GUID(), nullable=False),
        sa.Column('repository_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=False),
        sa.Column('status', sa.Enum(), nullable=False),
        sa.Column('result', sa.Enum(), nullable=False),
        sa.Column('node_id', sa.GUID(), nullable=True),
        sa.Column('date_started', sa.DateTime(), nullable=True),
        sa.Column('date_finished', sa.DateTime(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(['node_id'], ['node.id'], ),
        sa.ForeignKeyConstraint(['phase_id'], ['buildphase.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.ForeignKeyConstraint(['repository_id'], ['repository.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.drop_table(u'step')
    op.drop_table(u'phase')


def downgrade():
    op.create_table(
        u'step',
        sa.Column(u'id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'build_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'phase_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'repository_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'project_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'label', sa.VARCHAR(length=128), autoincrement=False, nullable=False),
        sa.Column(u'status', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(u'result', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(u'node_id', postgresql.UUID(), autoincrement=False, nullable=True),
        sa.Column(u'date_started', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column(u'date_finished', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column(u'date_created', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['build_id'], [u'build.id'], name=u'step_build_id_fkey'),
        sa.ForeignKeyConstraint(['node_id'], [u'node.id'], name=u'step_node_id_fkey'),
        sa.ForeignKeyConstraint(['phase_id'], [u'phase.id'], name=u'step_phase_id_fkey'),
        sa.ForeignKeyConstraint(['project_id'], [u'project.id'], name=u'step_project_id_fkey'),
        sa.ForeignKeyConstraint(['repository_id'], [u'repository.id'], name=u'step_repository_id_fkey'),
        sa.PrimaryKeyConstraint(u'id', name=u'step_pkey')
    )
    op.create_table(
        u'phase',
        sa.Column(u'id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'build_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'repository_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'project_id', postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column(u'label', sa.VARCHAR(length=128), autoincrement=False, nullable=False),
        sa.Column(u'status', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(u'result', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(u'date_started', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column(u'date_finished', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column(u'date_created', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['build_id'], [u'build.id'], name=u'phase_build_id_fkey'),
        sa.ForeignKeyConstraint(['project_id'], [u'project.id'], name=u'phase_project_id_fkey'),
        sa.ForeignKeyConstraint(['repository_id'], [u'repository.id'], name=u'phase_repository_id_fkey'),
        sa.PrimaryKeyConstraint(u'id', name=u'phase_pkey')
    )
    op.drop_table('buildstep')
    op.drop_table('buildphase')

########NEW FILE########
__FILENAME__ = 15bd4b7e6622_add_filecoverage_unique_constraint
"""Add FileCoverage unique constraint

Revision ID: 15bd4b7e6622
Revises: 3d8177efcfe1
Create Date: 2014-05-09 11:06:50.845168

"""

# revision identifiers, used by Alembic.
revision = '15bd4b7e6622'
down_revision = '3d8177efcfe1'

from alembic import op


def upgrade():
    op.create_unique_constraint('unq_job_filname', 'filecoverage', ['job_id', 'filename'])


def downgrade():
    op.drop_constraint('unq_job_filname', 'filecoverage')

########NEW FILE########
__FILENAME__ = 166d65e5a7e3_add_aggregatetest_gr
"""Add AggregateTest{Group,Suite}

Revision ID: 166d65e5a7e3
Revises: 21b7c3b2ce88
Create Date: 2013-12-04 13:19:26.702555

"""

# revision identifiers, used by Alembic.
revision = '166d65e5a7e3'
down_revision = '21b7c3b2ce88'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'aggtestsuite',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('name_sha', sa.String(length=40), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('first_build_id', sa.GUID(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['first_build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'project_id', 'name_sha', name='unq_aggtestsuite_key')
    )
    op.create_index('idx_aggtestsuite_first_build_id', 'aggtestsuite', ['first_build_id'])

    op.create_table(
        'aggtestgroup',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('suite_id', sa.GUID(), nullable=True),
        sa.Column('parent_id', sa.GUID(), nullable=True),
        sa.Column('name_sha', sa.String(length=40), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('first_build_id', sa.GUID(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['first_build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(['parent_id'], ['aggtestgroup.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.ForeignKeyConstraint(['suite_id'], ['aggtestsuite.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'project_id', 'suite_id', 'name_sha', name='unq_aggtestgroup_key')
    )
    op.create_index('idx_aggtestgroup_suite_id', 'aggtestgroup', ['suite_id'])
    op.create_index('idx_aggtestgroup_parent_id', 'aggtestgroup', ['parent_id'])
    op.create_index('idx_aggtestgroup_first_build_id', 'aggtestgroup', ['first_build_id'])


def downgrade():
    op.drop_table('aggtestgroup')
    op.drop_table('aggtestsuite')

########NEW FILE########
__FILENAME__ = 18c045b75331_add_various_build_in
"""Add various Build indexes

Revision ID: 18c045b75331
Revises: d324e8fc580
Create Date: 2013-11-04 17:14:33.455855

"""

# revision identifiers, used by Alembic.
revision = '18c045b75331'
down_revision = 'd324e8fc580'

from alembic import op


def upgrade():
    op.create_index('idx_build_project_id', 'build', ['project_id'])
    op.create_index('idx_build_repository_id', 'build', ['repository_id'])
    op.create_index('idx_build_author_id', 'build', ['author_id'])
    op.create_index('idx_build_patch_id', 'build', ['patch_id'])
    op.create_index('idx_build_change_id', 'build', ['change_id'])


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 1ad857c78a0d_family_id_build_id
"""*.family_id => build_id

Revision ID: 1ad857c78a0d
Revises: 545ba163595
Create Date: 2013-12-26 01:57:32.211057

"""

# revision identifiers, used by Alembic.
revision = '1ad857c78a0d'
down_revision = '545ba163595'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE job RENAME COLUMN family_id TO build_id')
    op.execute('ALTER TABLE jobplan RENAME COLUMN family_id TO build_id')


def downgrade():
    op.execute('ALTER TABLE job RENAME COLUMN build_id TO family_id')
    op.execute('ALTER TABLE jobplan RENAME COLUMN build_id TO family_id')

########NEW FILE########
__FILENAME__ = 1b2fa9c97090_expand_node_information
"""Expand node information

Revision ID: 1b2fa9c97090
Revises: 30b9f619c3b2
Create Date: 2014-05-13 11:54:21.124565

"""

# revision identifiers, used by Alembic.
revision = '1b2fa9c97090'
down_revision = '30b9f619c3b2'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'cluster',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('label')
    )
    op.create_table(
        'cluster_node',
        sa.Column('cluster_id', sa.GUID(), nullable=False),
        sa.Column('node_id', sa.GUID(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cluster_id'], ['cluster.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['node_id'], ['node.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('cluster_id', 'node_id')
    )
    op.add_column('node', sa.Column('data', sa.JSONEncodedDict(), nullable=True))


def downgrade():
    op.drop_column('node', 'data')
    op.drop_table('cluster_node')
    op.drop_table('cluster')

########NEW FILE########
__FILENAME__ = 1b53d33197bf_add_build_cause_and_
"""Add Build.cause and Buld.parent

Revision ID: 1b53d33197bf
Revises: 2b8459f1e2d6
Create Date: 2013-10-25 14:33:55.401260

"""

# revision identifiers, used by Alembic.
revision = '1b53d33197bf'
down_revision = '2b8459f1e2d6'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('build', sa.Column('cause', sa.Enum(), server_default='0', nullable=False))
    op.add_column('build', sa.Column('parent', sa.GUID(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('build', 'parent')
    op.drop_column('build', 'cause')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 1caf0d25843b_set_on_delete_cascad
"""Set ON DELETE CASCADE on AggregateTestSuite.*

Revision ID: 1caf0d25843b
Revises: 4d5d239d53b4
Create Date: 2013-12-23 16:15:27.526777

"""

# revision identifiers, used by Alembic.
revision = '1caf0d25843b'
down_revision = '4d5d239d53b4'

from alembic import op


def upgrade():
    op.drop_constraint('aggtestsuite_project_id_fkey', 'aggtestsuite')
    op.create_foreign_key('aggtestsuite_project_id_fkey', 'aggtestsuite', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('aggtestsuite_first_build_id_fkey', 'aggtestsuite')
    op.create_foreign_key('aggtestsuite_first_build_id_fkey', 'aggtestsuite', 'build', ['first_build_id'], ['id'], ondelete='CASCADE')

    op.create_foreign_key('aggtestsuite_last_build_id_fkey', 'aggtestsuite', 'build', ['last_build_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint('aggtestsuite_last_build_id_fkey', 'aggtestsuite')

########NEW FILE########
__FILENAME__ = 1d1f467bdf3d_add_projectoption
"""Add ProjectOption

Revision ID: 1d1f467bdf3d
Revises: 105d4dd82a0a
Create Date: 2013-11-20 16:04:25.408018

"""

# revision identifiers, used by Alembic.
revision = '1d1f467bdf3d'
down_revision = '105d4dd82a0a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'projectoption',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'name', name='unq_projectoption_name')
    )


def downgrade():
    op.drop_table('projectoption')

########NEW FILE########
__FILENAME__ = 1d806848a73f_unique_buildplan_bui
"""Unique BuildPlan.build

Revision ID: 1d806848a73f
Revises: ff220d76c11
Create Date: 2013-12-13 13:37:37.833620

"""

# revision identifiers, used by Alembic.
revision = '1d806848a73f'
down_revision = 'ff220d76c11'

from alembic import op


def upgrade():
    op.create_unique_constraint('unq_buildplan_build', 'buildplan', ['build_id'])
    op.drop_index('idx_buildplan_build_id', 'buildplan')


def downgrade():
    op.create_index('idx_buildplan_build_id', 'buildplan', ['build_id'])
    op.drop_constraint('unq_buildplan_build', 'buildplan')

########NEW FILE########
__FILENAME__ = 1db7a1ab95db_fix_filecoverage_pro
"""Fix FileCoverage.project_id

Revision ID: 1db7a1ab95db
Revises: 36becb086fcb
Create Date: 2014-03-21 15:47:41.430619

"""

# revision identifiers, used by Alembic.
revision = '1db7a1ab95db'
down_revision = '36becb086fcb'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('filecoverage', 'project_id')
    op.add_column('filecoverage', sa.Column('project_id', sa.GUID(), nullable=False))


def downgrade():
    raise NotImplementedError

########NEW FILE########
__FILENAME__ = 1eefd7dfedb2_update_on_delete_cas
"""Update ON DELETE CASCADE to Test*

Revision ID: 1eefd7dfedb2
Revises: 2f3ba1e84a6f
Create Date: 2013-12-23 15:39:12.877828

"""

# revision identifiers, used by Alembic.
revision = '1eefd7dfedb2'
down_revision = '2f3ba1e84a6f'

from alembic import op


def upgrade():
    # Test
    op.drop_constraint('test_build_id_fkey', 'test')
    op.create_foreign_key('test_build_id_fkey', 'test', 'build', ['build_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('test_project_id_fkey', 'test')
    op.create_foreign_key('test_project_id_fkey', 'test', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    # TestGroup
    op.drop_constraint('testgroup_build_id_fkey', 'testgroup')
    op.create_foreign_key('testgroup_build_id_fkey', 'testgroup', 'build', ['build_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('testgroup_project_id_fkey', 'testgroup')
    op.create_foreign_key('testgroup_project_id_fkey', 'testgroup', 'project', ['project_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('testgroup_parent_id_fkey', 'testgroup')
    op.create_foreign_key('testgroup_parent_id_fkey', 'testgroup', 'testgroup', ['parent_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('testgroup_suite_id_fkey', 'testgroup')
    op.create_foreign_key('testgroup_suite_id_fkey', 'testgroup', 'testsuite', ['suite_id'], ['id'], ondelete='CASCADE')

    # TestGroup <=> Test m2m
    op.drop_constraint('testgroup_test_group_id_fkey', 'testgroup_test')
    op.create_foreign_key('testgroup_test_group_id_fkey', 'testgroup_test', 'testgroup', ['group_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('testgroup_test_test_id_fkey', 'testgroup_test')
    op.create_foreign_key('testgroup_test_test_id_fkey', 'testgroup_test', 'test', ['test_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 1f5caa34d9c2_add_itemsequence
"""Add ItemSequence

Revision ID: 1f5caa34d9c2
Revises: bb141e41aab
Create Date: 2014-03-31 22:44:32.721446

"""

# revision identifiers, used by Alembic.
revision = '1f5caa34d9c2'
down_revision = 'bb141e41aab'

from alembic import op
import sqlalchemy as sa


NEXT_ITEM_VALUE_FUNCTION = """
CREATE OR REPLACE FUNCTION next_item_value(uuid) RETURNS int AS $$
DECLARE
  cur_parent_id ALIAS FOR $1;
  next_value int;
BEGIN
  LOOP
    UPDATE itemsequence SET value = value + 1 WHERE parent_id = cur_parent_id
    RETURNING value INTO next_value;
    IF FOUND THEN
      RETURN next_value;
    END IF;

    BEGIN
        INSERT INTO itemsequence (parent_id, value) VALUES (cur_parent_id, 1)
        RETURNING value INTO next_value;
        RETURN next_value;
    EXCEPTION WHEN unique_violation THEN
        -- do nothing
    END;
  END LOOP;
END;
$$ LANGUAGE plpgsql
"""

ADD_BUILD_SEQUENCES = """
INSERT INTO itemsequence (parent_id, value)
SELECT project_id, max(number) FROM build GROUP BY project_id
"""

ADD_JOB_SEQUENCES = """
INSERT INTO itemsequence (parent_id, value)
SELECT build_id, count(*) FROM job WHERE build_id IS NOT NULL GROUP BY build_id
"""


def upgrade():
    op.create_table('itemsequence',
        sa.Column('parent_id', sa.GUID(), nullable=False),
        sa.Column('value', sa.Integer(), server_default='1', nullable=False),
        sa.PrimaryKeyConstraint('parent_id', 'value')
    )
    op.execute(NEXT_ITEM_VALUE_FUNCTION)
    op.execute(ADD_BUILD_SEQUENCES)
    op.execute(ADD_JOB_SEQUENCES)


def downgrade():
    op.drop_table('itemsequence')
    op.execute('DROP FUNCTION IF EXISTS next_item_value(uuid)')

########NEW FILE########
__FILENAME__ = 208224023555_add_repository_backe
"""Add Repository.backend

Revision ID: 208224023555
Revises: 1d1f467bdf3d
Create Date: 2013-11-25 15:12:30.867388

"""

# revision identifiers, used by Alembic.
revision = '208224023555'
down_revision = '1d1f467bdf3d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('repository', sa.Column('backend', sa.Enum(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('repository', 'backend')

########NEW FILE########
__FILENAME__ = 215db24a630a_add_repository_last_
"""Add Repository.last_update, last_update_attempt

Revision ID: 215db24a630a
Revises: 208224023555
Create Date: 2013-11-25 15:41:16.798396

"""

# revision identifiers, used by Alembic.
revision = '215db24a630a'
down_revision = '208224023555'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('repository', sa.Column('last_update', sa.DateTime(), nullable=True))
    op.add_column('repository', sa.Column('last_update_attempt', sa.DateTime(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('repository', 'last_update_attempt')
    op.drop_column('repository', 'last_update')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 218e84b10a0e_set_on_delete_cascad
"""Set ON DELETE CASCADE on Log*

Revision ID: 218e84b10a0e
Revises: 54a5c0c8793b
Create Date: 2013-12-23 16:39:13.642754

"""

# revision identifiers, used by Alembic.
revision = '218e84b10a0e'
down_revision = '54a5c0c8793b'

from alembic import op


def upgrade():
    op.drop_constraint('logsource_project_id_fkey', 'logsource')
    op.create_foreign_key('logsource_project_id_fkey', 'logsource', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('logsource_build_id_fkey', 'logsource')
    op.create_foreign_key('logsource_build_id_fkey', 'logsource', 'build', ['build_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('logchunk_project_id_fkey', 'logchunk')
    op.create_foreign_key('logchunk_project_id_fkey', 'logchunk', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('logchunk_build_id_fkey', 'logchunk')
    op.create_foreign_key('logchunk_build_id_fkey', 'logchunk', 'build', ['build_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('logchunk_source_id_fkey', 'logchunk')
    op.create_foreign_key('logchunk_source_id_fkey', 'logchunk', 'logsource', ['source_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 21b7c3b2ce88_index_build_project_
"""Index Build.project_id,patch_id,date_created

Revision ID: 21b7c3b2ce88
Revises: 4134b4818694
Create Date: 2013-12-03 16:19:11.794912

"""

# revision identifiers, used by Alembic.
revision = '21b7c3b2ce88'
down_revision = '4134b4818694'

from alembic import op


def upgrade():
    op.create_index('idx_build_project_patch_date', 'build', ['project_id', 'patch_id', 'date_created'])


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 21c9439330f_add_cascade_to_filec
"""Add cascade to FileCoverage

Revision ID: 21c9439330f
Revises: 1f5caa34d9c2
Create Date: 2014-04-01 15:29:26.765288

"""

# revision identifiers, used by Alembic.
revision = '21c9439330f'
down_revision = '1f5caa34d9c2'

from alembic import op


def upgrade():
    op.create_index('idx_filecoverage_job_id', 'filecoverage', ['job_id'])
    op.create_index('idx_filecoverage_project_id', 'filecoverage', ['project_id'])

    op.drop_constraint('filecoverage_build_id_fkey', 'filecoverage')
    op.create_foreign_key('filecoverage_job_id_fkey', 'filecoverage', 'job', ['job_id'], ['id'], ondelete='CASCADE')

    op.create_foreign_key('filecoverage_project_id_fkey', 'filecoverage', 'project', ['project_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 24ffd1984588_add_buildseen
"""Add BuildSeen

Revision ID: 24ffd1984588
Revises: 97786e74292
Create Date: 2014-01-22 11:13:41.168990

"""

# revision identifiers, used by Alembic.
revision = '24ffd1984588'
down_revision = '97786e74292'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'buildseen',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('user_id', sa.GUID(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('build_id', 'user_id', name='unq_buildseen_entity')
    )
    op.create_foreign_key('buildseen_build_id_fkey', 'buildseen', 'build', ['build_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('buildseen_user_id_fkey', 'buildseen', 'user', ['user_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_table('buildseen')

########NEW FILE########
__FILENAME__ = 250341e605b7_set_on_delete_cascad
"""Set ON DELETE CASCADE on BuildPlan.*

Revision ID: 250341e605b7
Revises: 1eefd7dfedb2
Create Date: 2013-12-23 15:59:44.408248

"""

# revision identifiers, used by Alembic.
revision = '250341e605b7'
down_revision = '1eefd7dfedb2'

from alembic import op


def upgrade():
    op.drop_constraint('buildplan_build_id_fkey', 'buildplan')
    op.create_foreign_key('buildplan_build_id_fkey', 'buildplan', 'build', ['build_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildplan_family_id_fkey', 'buildplan')
    op.create_foreign_key('buildplan_family_id_fkey', 'buildplan', 'buildfamily', ['family_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildplan_plan_id_fkey', 'buildplan')
    op.create_foreign_key('buildplan_plan_id_fkey', 'buildplan', 'plan', ['plan_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildplan_project_id_fkey', 'buildplan')
    op.create_foreign_key('buildplan_project_id_fkey', 'buildplan', 'project', ['project_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 256ab638deaa_filecoverage_build_i
"""FileCoverage.build_id => job_id

Revision ID: 256ab638deaa
Revises: 37244bf4e3f5
Create Date: 2013-12-26 01:47:50.855439

"""

# revision identifiers, used by Alembic.
revision = '256ab638deaa'
down_revision = '37244bf4e3f5'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE filecoverage RENAME COLUMN build_id TO job_id')


def downgrade():
    op.execute('ALTER TABLE filecoverage RENAME COLUMN job_id TO build_id')

########NEW FILE########
__FILENAME__ = 2596f21c6f58_add_project_status
"""Add Project.status

Revision ID: 2596f21c6f58
Revises: 4e68c2a3d269
Create Date: 2014-02-18 17:34:59.432346

"""

# revision identifiers, used by Alembic.
revision = '2596f21c6f58'
down_revision = '4e68c2a3d269'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('project', sa.Column('status', sa.Enum(), server_default='1', nullable=True))


def downgrade():
    op.drop_column('project', 'status')

########NEW FILE########
__FILENAME__ = 25d63e09ea3b_add_build_job_number
"""Add Build/Job numbers

Revision ID: 25d63e09ea3b
Revises: 1ad857c78a0d
Create Date: 2013-12-26 02:36:58.663362

"""

# revision identifiers, used by Alembic.
revision = '25d63e09ea3b'
down_revision = '1ad857c78a0d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('build', sa.Column('number', sa.Integer(), nullable=True))
    op.add_column('job', sa.Column('number', sa.Integer(), nullable=True))
    op.create_unique_constraint('unq_build_number', 'build', ['project_id', 'number'])
    op.create_unique_constraint('unq_job_number', 'job', ['build_id', 'number'])


def downgrade():
    op.drop_column('build', 'number')
    op.drop_column('job', 'number')
    op.drop_constraint('unq_build_number', 'build')
    op.drop_constraint('unq_job_number', 'job')

########NEW FILE########
__FILENAME__ = 2622a69cd25a_unique_node_label
"""Unique Node.label

Revision ID: 2622a69cd25a
Revises: 2c7cbd9b7e54
Create Date: 2013-12-18 12:42:30.583085

"""

# revision identifiers, used by Alembic.
revision = '2622a69cd25a'
down_revision = '2c7cbd9b7e54'

from alembic import op


def upgrade():
    op.create_unique_constraint('unq_node_label', 'node', ['label'])


def downgrade():
    op.drop_constraint('unq_node_label', 'node')

########NEW FILE########
__FILENAME__ = 26c0affcb18a_add_jobstep_data
"""Add JobStep.data

Revision ID: 26c0affcb18a
Revises: 4114cbbd0573
Create Date: 2014-01-07 16:44:48.524027

"""

# revision identifiers, used by Alembic.
revision = '26c0affcb18a'
down_revision = '4114cbbd0573'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('jobstep', sa.Column('data', sa.JSONEncodedDict(), nullable=True))


def downgrade():
    op.drop_column('jobstep', 'data')

########NEW FILE########
__FILENAME__ = 26dbd6ff063c_add_task
"""Add Task

Revision ID: 26dbd6ff063c
Revises: 26c0affcb18a
Create Date: 2014-01-09 17:03:39.051795

"""

# revision identifiers, used by Alembic.
revision = '26dbd6ff063c'
down_revision = '26c0affcb18a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'task',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('task_name', sa.String(length=128), nullable=False),
        sa.Column('parent_id', sa.GUID(), nullable=False),
        sa.Column('child_id', sa.GUID(), nullable=False),
        sa.Column('status', sa.Enum(), nullable=False),
        sa.Column('result', sa.Enum(), nullable=False),
        sa.Column('num_retries', sa.Integer(), nullable=False),
        sa.Column('date_started', sa.DateTime(), nullable=True),
        sa.Column('date_finished', sa.DateTime(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.Column('date_modified', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_name', 'parent_id', 'child_id', name='unq_task_entity')
    )

    op.create_index('idx_task_parent_id', 'task', ['parent_id', 'task_name'])
    op.create_index('idx_task_child_id', 'task', ['child_id', 'task_name'])


def downgrade():
    op.drop_table('task')

########NEW FILE########
__FILENAME__ = 26f665189ca0_remove_jobstep_jobph
"""Remove JobStep/JobPhase repository_id

Revision ID: 26f665189ca0
Revises: 524b3c27203b
Create Date: 2014-01-05 22:01:02.648719

"""

# revision identifiers, used by Alembic.
revision = '26f665189ca0'
down_revision = '524b3c27203b'

from alembic import op


def upgrade():
    op.drop_column('jobstep', 'repository_id')
    op.drop_column('jobphase', 'repository_id')


def downgrade():
    raise NotImplementedError

########NEW FILE########
__FILENAME__ = 2b4219a6cf46_jobphase_build_id_jo
"""JobPhase.build_id => job_id

Revision ID: 2b4219a6cf46
Revises: f26b6cb3c9c
Create Date: 2013-12-26 00:16:20.974336

"""

# revision identifiers, used by Alembic.
revision = '2b4219a6cf46'
down_revision = 'f26b6cb3c9c'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE jobphase RENAME COLUMN build_id TO job_id')


def downgrade():
    op.execute('ALTER TABLE jobphase RENAME COLUMN job_id TO build_id')

########NEW FILE########
__FILENAME__ = 2b71d67ef04d_backfill_testcase_le
"""Backfill TestCase leaves

Revision ID: 2b71d67ef04d
Revises: 3edf6ec6abd5
Create Date: 2013-11-07 12:48:43.717544

"""

from __future__ import absolute_import, print_function

# revision identifiers, used by Alembic.
revision = '2b71d67ef04d'
down_revision = '3edf6ec6abd5'

from alembic import op
from uuid import uuid4
from sqlalchemy.sql import table
import sqlalchemy as sa


def upgrade():
    from changes.constants import Result

    connection = op.get_bind()

    testgroups_table = table(
        'testgroup',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('parent_id', sa.GUID(), nullable=True),
        sa.Column('name_sha', sa.String(length=40), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('num_tests', sa.Integer(), nullable=True),
        sa.Column('num_failed', sa.Integer(), nullable=True),
        sa.Column('result', sa.Enum(), nullable=True),
        sa.Column('name', sa.Text(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
    )
    testgroups_m2m_table = table(
        'testgroup_test',
        sa.Column('group_id', sa.GUID(), nullable=False),
        sa.Column('test_id', sa.GUID(), nullable=False),
    )
    testcases_table = table(
        'test',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('package', sa.Text(), nullable=True),
        sa.Column('name', sa.Text(), nullable=True),
        sa.Column('label_sha', sa.String(length=40), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('result', sa.Enum(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
    )

    for testcase in connection.execute(testcases_table.select()):
        print("Migrating TestCase %s" % (testcase.id,))

        if testcase.package:
            full_name = testcase.package + '.' + testcase.name
        else:
            full_name = testcase.name
        group_id = uuid4()

        # find the parent
        result = connection.execute(testgroups_table.select().where(sa.and_(
            testgroups_table.c.build_id == testcase.build_id,
            testgroups_table.c.name == (testcase.package or testcase.name.rsplit('.', 1)[0]),
        )).limit(1)).fetchone()

        connection.execute(
            testgroups_table.insert().values(
                id=group_id,
                build_id=testcase.build_id,
                project_id=testcase.project_id,
                name=full_name,
                name_sha=testcase.label_sha,
                date_created=testcase.date_created,
                duration=testcase.duration,
                parent_id=result.id,
                result=Result(testcase.result),
                num_tests=1,
                num_failed=1 if testcase.result == Result.failed else 0,
            )
        )

        connection.execute(
            testgroups_m2m_table.insert().values(
                group_id=group_id,
                test_id=testcase.id,
            )
        )


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 2b8459f1e2d6_initial_schema
"""Initial schema

Revision ID: 2b8459f1e2d6
Revises: None
Create Date: 2013-10-22 14:31:32.654367

"""

# revision identifiers, used by Alembic.
revision = '2b8459f1e2d6'
down_revision = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('repository',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('url', sa.String(length=200), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('url')
    )
    op.create_table('node',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('label', sa.String(length=128), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('author',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('email', sa.String(length=128), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('name')
    )
    op.create_table('remoteentity',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('type', sa.String(), nullable=False),
    sa.Column('provider', sa.String(length=128), nullable=False),
    sa.Column('remote_id', sa.String(length=128), nullable=False),
    sa.Column('internal_id', sa.GUID(), nullable=False),
    sa.Column('data', sa.JSONEncodedDict(), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('provider','remote_id','type', name='remote_identifier')
    )
    op.create_table('project',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('slug', sa.String(length=64), nullable=False),
    sa.Column('repository_id', sa.GUID(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('avg_build_time', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['repository_id'], ['repository.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    op.create_table('revision',
    sa.Column('repository_id', sa.GUID(), nullable=False),
    sa.Column('sha', sa.String(length=40), nullable=False),
    sa.Column('author_id', sa.GUID(), nullable=True),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('parents', postgresql.ARRAY(sa.String(length=40)), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['author_id'], ['author.id'], ),
    sa.ForeignKeyConstraint(['repository_id'], ['repository.id'], ),
    sa.PrimaryKeyConstraint('repository_id', 'sha')
    )
    op.create_table('change',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('hash', sa.String(length=40), nullable=False),
    sa.Column('repository_id', sa.GUID(), nullable=False),
    sa.Column('project_id', sa.GUID(), nullable=False),
    sa.Column('author_id', sa.GUID(), nullable=True),
    sa.Column('label', sa.String(length=128), nullable=False),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('date_modified', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['author_id'], ['author.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['repository_id'], ['repository.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('hash')
    )
    op.create_table('patch',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('change_id', sa.GUID(), nullable=True),
    sa.Column('repository_id', sa.GUID(), nullable=False),
    sa.Column('project_id', sa.GUID(), nullable=False),
    sa.Column('parent_revision_sha', sa.String(length=40), nullable=False),
    sa.Column('label', sa.String(length=64), nullable=False),
    sa.Column('url', sa.String(length=200), nullable=True),
    sa.Column('diff', sa.Text(), nullable=True),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['change_id'], ['change.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['repository_id'], ['repository.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('build',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('change_id', sa.GUID(), nullable=True),
    sa.Column('repository_id', sa.GUID(), nullable=False),
    sa.Column('project_id', sa.GUID(), nullable=False),
    sa.Column('parent_revision_sha', sa.String(length=40), nullable=True),
    sa.Column('patch_id', sa.GUID(), nullable=True),
    sa.Column('author_id', sa.GUID(), nullable=True),
    sa.Column('label', sa.String(length=128), nullable=False),
    sa.Column('status', sa.Enum(), nullable=False),
    sa.Column('result', sa.Enum(), nullable=False),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.Column('date_started', sa.DateTime(), nullable=True),
    sa.Column('date_finished', sa.DateTime(), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('date_modified', sa.DateTime(), nullable=True),
    sa.Column('data', sa.JSONEncodedDict(), nullable=True),
    sa.ForeignKeyConstraint(['author_id'], ['author.id'], ),
    sa.ForeignKeyConstraint(['change_id'], ['change.id'], ),
    sa.ForeignKeyConstraint(['patch_id'], ['patch.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['repository_id'], ['repository.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('filecoverage',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('build_id', sa.GUID(), nullable=False),
    sa.Column('filename', sa.String(length=256), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('data', sa.Text(), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
    sa.PrimaryKeyConstraint('id', 'filename')
    )
    op.create_table('test',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('build_id', sa.GUID(), nullable=False),
    sa.Column('project_id', sa.GUID(), nullable=False),
    sa.Column('group_sha', sa.String(length=40), nullable=False),
    sa.Column('label_sha', sa.String(length=40), nullable=False),
    sa.Column('group', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('package', sa.Text(), nullable=True),
    sa.Column('result', sa.Enum(), nullable=True),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('build_id','group_sha','label_sha', name='_test_key')
    )
    op.create_table('phase',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('build_id', sa.GUID(), nullable=False),
    sa.Column('repository_id', sa.GUID(), nullable=False),
    sa.Column('project_id', sa.GUID(), nullable=False),
    sa.Column('label', sa.String(length=128), nullable=False),
    sa.Column('status', sa.Enum(), nullable=False),
    sa.Column('result', sa.Enum(), nullable=False),
    sa.Column('date_started', sa.DateTime(), nullable=True),
    sa.Column('date_finished', sa.DateTime(), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['repository_id'], ['repository.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('step',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('build_id', sa.GUID(), nullable=False),
    sa.Column('phase_id', sa.GUID(), nullable=False),
    sa.Column('repository_id', sa.GUID(), nullable=False),
    sa.Column('project_id', sa.GUID(), nullable=False),
    sa.Column('label', sa.String(length=128), nullable=False),
    sa.Column('status', sa.Enum(), nullable=False),
    sa.Column('result', sa.Enum(), nullable=False),
    sa.Column('node_id', sa.GUID(), nullable=True),
    sa.Column('date_started', sa.DateTime(), nullable=True),
    sa.Column('date_finished', sa.DateTime(), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
    sa.ForeignKeyConstraint(['node_id'], ['node.id'], ),
    sa.ForeignKeyConstraint(['phase_id'], ['phase.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['repository_id'], ['repository.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('step')
    op.drop_table('phase')
    op.drop_table('test')
    op.drop_table('filecoverage')
    op.drop_table('build')
    op.drop_table('patch')
    op.drop_table('change')
    op.drop_table('revision')
    op.drop_table('project')
    op.drop_table('remoteentity')
    op.drop_table('author')
    op.drop_table('node')
    op.drop_table('repository')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 2c380be0a31e_add_event
"""Add Event

Revision ID: 2c380be0a31e
Revises: 3265d2120c82
Create Date: 2014-04-04 13:06:03.094082

"""

# revision identifiers, used by Alembic.
revision = '2c380be0a31e'
down_revision = '3265d2120c82'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'event',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('item_id', sa.GUID(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.Column('date_modified', sa.DateTime(), nullable=True),
        sa.Column('data', sa.JSONEncodedDict(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('type', 'item_id', name='unq_event_key')
    )


def downgrade():
    op.drop_table('event')

########NEW FILE########
__FILENAME__ = 2c7cbd9b7e54_add_source
"""Add Source

Revision ID: 2c7cbd9b7e54
Revises: 380d20771802
Create Date: 2013-12-17 13:53:19.836264

"""

# revision identifiers, used by Alembic.
revision = '2c7cbd9b7e54'
down_revision = '380d20771802'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'source',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('repository_id', sa.GUID(), nullable=False),
        sa.Column('patch_id', sa.GUID(), nullable=True),
        sa.Column('revision_sha', sa.String(length=40), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['patch_id'], ['patch.id']),
        sa.ForeignKeyConstraint(['repository_id'], ['repository.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.add_column('build', sa.Column('source_id', sa.GUID(), nullable=True))
    op.add_column('buildfamily', sa.Column('source_id', sa.GUID(), nullable=True))
    op.create_index('idx_build_source_id', 'build', ['source_id'])
    op.create_index('idx_buildfamily_source_id', 'buildfamily', ['source_id'])


def downgrade():
    op.drop_index('idx_build_source_id', 'build')
    op.drop_index('idx_buildfamily_source_id', 'buildfamily')
    op.drop_column('buildfamily', 'source_id')
    op.drop_column('build', 'source_id')
    op.drop_table('source')

########NEW FILE########
__FILENAME__ = 2d82db02b3ef_fill_testgroup_num_l
"""Fill TestGroup.num_leaves

Revision ID: 2d82db02b3ef
Revises: 4640ecd97c82
Create Date: 2013-11-08 13:14:05.257558

"""

# revision identifiers, used by Alembic.
revision = '2d82db02b3ef'
down_revision = '4640ecd97c82'

from alembic import op


def upgrade():
    op.execute("""
        update testgroup as a
        set num_leaves = (
            select count(*)
            from testgroup as b
            where a.id = b.parent_id
        )
    """)


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 2d8acbec66df_add_build_target
"""Add Build.target

Revision ID: 2d8acbec66df
Revises: 5aad6f742b77
Create Date: 2013-11-11 17:07:11.624071

"""

# revision identifiers, used by Alembic.
revision = '2d8acbec66df'
down_revision = '5aad6f742b77'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('build', sa.Column('target', sa.String(length=128), nullable=True))
    op.drop_column('build', u'parent_revision_sha')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('build', sa.Column(u'parent_revision_sha', sa.VARCHAR(length=40), nullable=True))
    op.drop_column('build', 'target')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 2d9df8a3103c_add_logchunk_unique_
"""Add LogChunk unique constraint

Revision ID: 2d9df8a3103c
Revises: 393be9b08e4c
Create Date: 2013-11-13 17:12:48.662009

"""

# revision identifiers, used by Alembic.
revision = '2d9df8a3103c'
down_revision = '393be9b08e4c'

from alembic import op


def upgrade():
    op.create_unique_constraint('unq_logchunk_source_offset', 'logchunk', ['source_id', 'offset'])


def downgrade():
    op.drop_constraint('unq_logchunk_source_offset', 'logchunk')

########NEW FILE########
__FILENAME__ = 2dfac13a4c78_add_logsource_unique
"""Add LogSource unique constraint on name

Revision ID: 2dfac13a4c78
Revises: 5896e31725d
Create Date: 2013-12-06 10:56:15.727933

"""

from __future__ import absolute_import, print_function

# revision identifiers, used by Alembic.
revision = '2dfac13a4c78'
down_revision = '5896e31725d'

from alembic import op
from sqlalchemy.sql import table, select
import sqlalchemy as sa


def upgrade():
    connection = op.get_bind()

    logsources_table = table(
        'logsource',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('name', sa.String(64), nullable=True),
    )
    logchunks_table = table(
        'logchunk',
        sa.Column('source_id', sa.GUID(), nullable=False),
    )

    done = set()

    for logsource in connection.execute(logsources_table.select()):
        # migrate group to suite
        key = (logsource.build_id, logsource.name)
        if key in done:
            continue

        print("Checking LogSource %s - %s" % (
            logsource.build_id, logsource.name))
        query = logchunks_table.delete().where(
            logchunks_table.c.source_id.in_(select([logchunks_table]).where(
                sa.and_(
                    logsources_table.c.build_id == logsource.build_id,
                    logsources_table.c.name == logsource.name,
                    logsources_table.c.id != logsource.id,
                ),
            ))
        )
        connection.execute(query)

        query = logsources_table.delete().where(
            sa.and_(
                logsources_table.c.build_id == logsource.build_id,
                logsources_table.c.name == logsource.name,
                logsources_table.c.id != logsource.id,
            )
        )

        connection.execute(query)

        done.add(key)

    op.create_unique_constraint(
        'unq_logsource_key', 'logsource', ['build_id', 'name'])
    op.drop_index('idx_logsource_build_id', 'logsource')


def downgrade():
    op.drop_constraint('unq_logsource_key', 'logsource')
    op.create_index('idx_logsource_build_id', 'logsource', ['build_id'])

########NEW FILE########
__FILENAME__ = 2f3ba1e84a6f_update_source_constr
"""Update Source constraints

Revision ID: 2f3ba1e84a6f
Revises: cb99fdfb903
Create Date: 2013-12-23 14:46:38.140915

"""

# revision identifiers, used by Alembic.
revision = '2f3ba1e84a6f'
down_revision = 'cb99fdfb903'

from alembic import op


def upgrade():
    op.execute('CREATE UNIQUE INDEX unq_source_revision ON source (repository_id, revision_sha) WHERE patch_id IS NULL')
    op.execute('CREATE UNIQUE INDEX unq_source_patch_id ON source (patch_id) WHERE patch_id IS NOT NULL')


def downgrade():
    op.drop_constraint('unq_source_revision', 'source')
    op.drop_constraint('unq_source_patch_id', 'source')

########NEW FILE########
__FILENAME__ = 2f4637448764_index_jobstep
"""Index JobStep

Revision ID: 2f4637448764
Revises: 34157be0e8a2
Create Date: 2014-01-02 22:01:33.969503

"""

# revision identifiers, used by Alembic.
revision = '2f4637448764'
down_revision = '34157be0e8a2'

from alembic import op


def upgrade():
    op.create_index('idx_jobstep_job_id', 'jobstep', ['job_id'])
    op.create_index('idx_jobstep_project_id', 'jobstep', ['project_id'])
    op.create_index('idx_jobstep_phase_id', 'jobstep', ['phase_id'])
    op.create_index('idx_jobstep_repository_id', 'jobstep', ['repository_id'])
    op.create_index('idx_jobstep_node_id', 'jobstep', ['node_id'])


def downgrade():
    op.drop_index('idx_jobstep_job_id', 'jobstep')
    op.drop_index('idx_jobstep_project_id', 'jobstep')
    op.drop_index('idx_jobstep_phase_id', 'jobstep')
    op.drop_index('idx_jobstep_repository_id', 'jobstep')
    op.drop_index('idx_jobstep_node_id', 'jobstep')

########NEW FILE########
__FILENAME__ = 3042d0ca43bf_index_job_project_id
"""Index Job(project_id, status, date_created) where patch_id IS NULL

Revision ID: 3042d0ca43bf
Revises: 3a3366fb7822
Create Date: 2014-01-03 15:24:39.947813

"""

# revision identifiers, used by Alembic.
revision = '3042d0ca43bf'
down_revision = '3a3366fb7822'

from alembic import op


def upgrade():
    op.execute('CREATE INDEX idx_job_previous_runs ON job (project_id, status, date_created) WHERE patch_id IS NULL')


def downgrade():
    op.drop_index('idx_job_previous_runs', 'job')

########NEW FILE########
__FILENAME__ = 306fefe51dc6_set_on_delete_cascad
"""Set ON DELETE CASCADE on Project Plan m2m

Revision ID: 306fefe51dc6
Revises: 37e782a55ca6
Create Date: 2013-12-23 16:44:37.119363

"""

# revision identifiers, used by Alembic.
revision = '306fefe51dc6'
down_revision = '37e782a55ca6'

from alembic import op


def upgrade():
    op.drop_constraint('project_plan_plan_id_fkey', 'project_plan')
    op.create_foreign_key('project_plan_plan_id_fkey', 'project_plan', 'plan', ['plan_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('project_plan_project_id_fkey', 'project_plan')
    op.create_foreign_key('project_plan_project_id_fkey', 'project_plan', 'project', ['project_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 30b9f619c3b2_remove_test_suite
"""Remove test suite

Revision ID: 30b9f619c3b2
Revises: 3b55ff8856f5
Create Date: 2014-05-09 14:36:41.548924

"""

# revision identifiers, used by Alembic.
revision = '30b9f619c3b2'
down_revision = '3b55ff8856f5'

from alembic import op


def upgrade():
    op.create_unique_constraint('unq_test_name', 'test', ['job_id', 'label_sha'])
    op.drop_column('test', 'suite_id')

    op.drop_table('testsuite')


def downgrade():
    raise NotImplementedError

########NEW FILE########
__FILENAME__ = 315e787e94bf_add_source_data
"""Add Source.data

Revision ID: 315e787e94bf
Revises: 3f289637f530
Create Date: 2014-05-06 18:25:11.223951

"""

# revision identifiers, used by Alembic.
revision = '315e787e94bf'
down_revision = '3f289637f530'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('source', sa.Column('data', sa.JSONEncodedDict(), nullable=True))


def downgrade():
    op.drop_column('source', 'data')

########NEW FILE########
__FILENAME__ = 32274e97552_build_parent_build_p
"""Build.parent -> Build.parent_id

Revision ID: 32274e97552
Revises: 1b53d33197bf
Create Date: 2013-10-25 15:41:21.120737

"""

# revision identifiers, used by Alembic.
revision = '32274e97552'
down_revision = '1b53d33197bf'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('build', sa.Column('parent_id', sa.GUID(), nullable=True))
    op.drop_column('build', u'parent')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('build', sa.Column(u'parent', postgresql.UUID(), nullable=True))
    op.drop_column('build', 'parent_id')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 3265d2120c82_add_testcase_step_id
"""Add TestCase.step_id

Revision ID: 3265d2120c82
Revises: 21c9439330f
Create Date: 2014-04-02 15:26:58.967387

"""

# revision identifiers, used by Alembic.
revision = '3265d2120c82'
down_revision = '21c9439330f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('test', sa.Column('step_id', sa.GUID(), nullable=True))
    op.create_foreign_key('test_step_id_fkey', 'test', 'jobstep', ['step_id'], ['id'], ondelete='CASCADE')
    op.create_index('idx_test_step_id', 'test', ['step_id'])


def downgrade():
    op.drop_column('test', 'step_id')

########NEW FILE########
__FILENAME__ = 34157be0e8a2_index_patch_project_
"""Index Patch.project_id

Revision ID: 34157be0e8a2
Revises: f8ed1f99eb1
Create Date: 2014-01-02 21:59:37.076886

"""

# revision identifiers, used by Alembic.
revision = '34157be0e8a2'
down_revision = 'f8ed1f99eb1'

from alembic import op


def upgrade():
    op.create_index('idx_patch_project_id', 'patch', ['project_id'])


def downgrade():
    op.drop_index('idx_patch_project_id', 'patch')

########NEW FILE########
__FILENAME__ = 346c011ca77a_optional_parent_revi
"""Optional parent_revision_sha

Revision ID: 346c011ca77a
Revises: 2d8acbec66df
Create Date: 2013-11-11 17:08:40.087545

"""

# revision identifiers, used by Alembic.
revision = '346c011ca77a'
down_revision = '2d8acbec66df'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('patch', 'parent_revision_sha',
               existing_type=sa.VARCHAR(length=40),
               nullable=True)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('patch', 'parent_revision_sha',
               existing_type=sa.VARCHAR(length=40),
               nullable=False)
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 35af40cebcde_jobplan_build_id_job
"""JobPlan.build_id => job_id

Revision ID: 35af40cebcde
Revises: 2b4219a6cf46
Create Date: 2013-12-26 00:18:58.945167

"""

# revision identifiers, used by Alembic.
revision = '35af40cebcde'
down_revision = '2b4219a6cf46'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE jobplan RENAME COLUMN build_id TO job_id')


def downgrade():
    op.execute('ALTER TABLE jobplan RENAME COLUMN job_id TO build_id')

########NEW FILE########
__FILENAME__ = 36becb086fcb_add_revision_branche
"""Add Revision.branches

Revision ID: 36becb086fcb
Revises: 11a7a7f2652f
Create Date: 2014-03-18 17:48:37.484301

"""

# revision identifiers, used by Alembic.
revision = '36becb086fcb'
down_revision = '11a7a7f2652f'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.add_column('revision', sa.Column('branches', postgresql.ARRAY(sa.String(length=128)), nullable=True))


def downgrade():
    op.drop_column('revision', 'branches')

########NEW FILE########
__FILENAME__ = 37244bf4e3f5_aggregatetest_build_
"""AggregateTest*.build_id => job_id

Revision ID: 37244bf4e3f5
Revises: 57e24a9f2290
Create Date: 2013-12-26 01:24:37.395827

"""

# revision identifiers, used by Alembic.
revision = '37244bf4e3f5'
down_revision = '57e24a9f2290'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE aggtestsuite RENAME COLUMN first_build_id to first_job_id')
    op.execute('ALTER TABLE aggtestsuite RENAME COLUMN last_build_id to last_job_id')

    op.execute('ALTER TABLE aggtestgroup RENAME COLUMN first_build_id to first_job_id')
    op.execute('ALTER TABLE aggtestgroup RENAME COLUMN last_build_id to last_job_id')


def downgrade():
    op.execute('ALTER TABLE aggtestsuite RENAME COLUMN first_job_id to first_build_id')
    op.execute('ALTER TABLE aggtestsuite RENAME COLUMN last_job_id to last_build_id')

    op.execute('ALTER TABLE aggtestgroup RENAME COLUMN first_job_id to first_build_id')
    op.execute('ALTER TABLE aggtestgroup RENAME COLUMN last_job_id to last_build_id')

########NEW FILE########
__FILENAME__ = 37e782a55ca6_set_on_delete_cascad
"""Set ON DELETE CASCADE on Project*

Revision ID: 37e782a55ca6
Revises: 218e84b10a0e
Create Date: 2013-12-23 16:41:27.462599

"""

# revision identifiers, used by Alembic.
revision = '37e782a55ca6'
down_revision = '218e84b10a0e'

from alembic import op


def upgrade():
    op.drop_constraint('project_repository_id_fkey', 'project')
    op.create_foreign_key('project_repository_id_fkey', 'project', 'repository', ['repository_id'], ['id'], ondelete='RESTRICT')

    op.drop_constraint('projectoption_project_id_fkey', 'projectoption')
    op.create_foreign_key('projectoption_project_id_fkey', 'projectoption', 'project', ['project_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 380d20771802_project_plan
"""Project <=> Plan

Revision ID: 380d20771802
Revises: 1d806848a73f
Create Date: 2013-12-16 14:38:39.941404

"""

# revision identifiers, used by Alembic.
revision = '380d20771802'
down_revision = '1d806848a73f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'project_plan',
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('plan_id', sa.GUID(), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['plan.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.PrimaryKeyConstraint('project_id', 'plan_id')
    )


def downgrade():
    op.drop_table('project_plan')

########NEW FILE########
__FILENAME__ = 393be9b08e4c_add_logsource_and_lo
"""Add LogSource and LogChunk

Revision ID: 393be9b08e4c
Revises: 4901f27ade8e
Create Date: 2013-11-12 11:05:50.757171

"""

# revision identifiers, used by Alembic.
revision = '393be9b08e4c'
down_revision = '4901f27ade8e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'logsource',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_logsource_project_id', 'logsource', ['project_id'])
    op.create_index('idx_logsource_build_id', 'logsource', ['build_id'])

    op.create_table(
        'logchunk',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('source_id', sa.GUID(), nullable=False),
        sa.Column('offset', sa.Integer(), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.ForeignKeyConstraint(['source_id'], ['logsource.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_logchunk_project_id', 'logchunk', ['project_id'])
    op.create_index('idx_logchunk_build_id', 'logchunk', ['build_id'])
    op.create_index('idx_logchunk_source_id', 'logchunk', ['source_id'])


def downgrade():
    op.drop_table('logchunk')
    op.drop_table('logsource')

########NEW FILE########
__FILENAME__ = 3a3366fb7822_index_testgroup_test
"""Index testgroup_test.test_id

Revision ID: 3a3366fb7822
Revises: 139e272152de
Create Date: 2014-01-02 22:20:55.132222

"""

# revision identifiers, used by Alembic.
revision = '3a3366fb7822'
down_revision = '139e272152de'

from alembic import op


def upgrade():
    op.create_index('idx_testgroup_test_test_id', 'testgroup_test', ['test_id'])


def downgrade():
    op.drop_index('idx_testgroup_test_test_id', 'testgroup_test')

########NEW FILE########
__FILENAME__ = 3b55ff8856f5_add_filecoverage_stats_to_model
"""Add FileCoverage stats to model

Revision ID: 3b55ff8856f5
Revises: 15bd4b7e6622
Create Date: 2014-05-09 11:35:19.758338

"""

# revision identifiers, used by Alembic.
revision = '3b55ff8856f5'
down_revision = '15bd4b7e6622'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('filecoverage', sa.Column('diff_lines_covered', sa.Integer(), nullable=True))
    op.add_column('filecoverage', sa.Column('diff_lines_uncovered', sa.Integer(), nullable=True))
    op.add_column('filecoverage', sa.Column('lines_covered', sa.Integer(), nullable=True))
    op.add_column('filecoverage', sa.Column('lines_uncovered', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('filecoverage', 'lines_uncovered')
    op.drop_column('filecoverage', 'lines_covered')
    op.drop_column('filecoverage', 'diff_lines_uncovered')
    op.drop_column('filecoverage', 'diff_lines_covered')

########NEW FILE########
__FILENAME__ = 3bef10ab5088_add_various_testgrou
"""Add various TestGroup indexes

Revision ID: 3bef10ab5088
Revises: fd1a52fe89f
Create Date: 2013-11-04 17:10:52.057285

"""

# revision identifiers, used by Alembic.
revision = '3bef10ab5088'
down_revision = 'fd1a52fe89f'

from alembic import op


def upgrade():
    op.create_index('idx_testgroup_project_id', 'testgroup', ['project_id'])
    op.create_index('idx_testgroup_suite_id', 'testgroup', ['suite_id'])
    op.create_index('idx_testgroup_parent_id', 'testgroup', ['parent_id'])


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 3d8177efcfe1_add_filecoverage_step_id
"""Add FileCoverage.step_id

Revision ID: 3d8177efcfe1
Revises: 3df65ebfa27e
Create Date: 2014-05-08 11:19:04.251803

"""

# revision identifiers, used by Alembic.
revision = '3d8177efcfe1'
down_revision = '3df65ebfa27e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('filecoverage', sa.Column('step_id', sa.GUID(), nullable=True))


def downgrade():
    op.drop_column('filecoverage', 'step_id')

########NEW FILE########
__FILENAME__ = 3d9067f21201_unique_step_order
"""Unique Step.order

Revision ID: 3d9067f21201
Revises: 2622a69cd25a
Create Date: 2013-12-18 15:06:47.035804

"""

# revision identifiers, used by Alembic.
revision = '3d9067f21201'
down_revision = '2622a69cd25a'

from alembic import op


def upgrade():
    op.create_unique_constraint('unq_step_key', 'step', ['plan_id', 'order'])
    op.drop_index('idx_step_plan_id', 'step')


def downgrade():
    op.create_index('idx_step_plan_id', 'step', ['plan_id'])
    op.drop_constraint('unq_step_key', 'step')

########NEW FILE########
__FILENAME__ = 3df65ebfa27e_remove_patch_label_and_message
"""Remove Patch label and message

Revision ID: 3df65ebfa27e
Revises: 315e787e94bf
Create Date: 2014-05-06 18:41:16.245897

"""

# revision identifiers, used by Alembic.
revision = '3df65ebfa27e'
down_revision = '315e787e94bf'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('patch', 'message')
    op.drop_column('patch', 'label')


def downgrade():
    op.add_column('patch', sa.Column('label', sa.VARCHAR(length=64), nullable=False))
    op.add_column('patch', sa.Column('message', sa.TEXT(), nullable=True))

########NEW FILE########
__FILENAME__ = 3edf6ec6abd5_fill_testgroup_resul
"""Fill TestGroup.result

Revision ID: 3edf6ec6abd5
Revises: 47e23df5a7ed
Create Date: 2013-11-05 14:08:23.068195

"""

from __future__ import absolute_import, print_function

# revision identifiers, used by Alembic.
revision = '3edf6ec6abd5'
down_revision = '47e23df5a7ed'

from alembic import op
from sqlalchemy.sql import select, table
import sqlalchemy as sa


def upgrade():
    from changes.constants import Result

    connection = op.get_bind()

    testgroups_table = table(
        'testgroup',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('result', sa.Enum(), nullable=True),
    )
    testgroups_m2m_table = table(
        'testgroup_test',
        sa.Column('group_id', sa.GUID(), nullable=False),
        sa.Column('test_id', sa.GUID(), nullable=False),
    )
    testcases_table = table(
        'test',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('result', sa.Enum(), nullable=True),
    )

    # perform data migrations
    for testgroup in connection.execute(testgroups_table.select()):
        # migrate group to suite
        print("Migrating TestGroup %s" % (testgroup.id,))

        query = select([testcases_table]).where(
            sa.and_(
                testgroups_m2m_table.c.test_id == testcases_table.c.id,
                testgroups_m2m_table.c.group_id == testgroup.id,
            )
        )

        result = Result.unknown
        for testcase in connection.execute(query):
            result = max(result, Result(testcase.result))

        connection.execute(
            testgroups_table.update().where(
                testgroups_table.c.id == testgroup.id,
            ).values({
                testgroups_table.c.result: result,
            })
        )


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 3f289637f530_remove_unused_models
"""Remove unused models

Revision ID: 3f289637f530
Revises: 4ba1dd8c3080
Create Date: 2014-04-17 11:08:50.963964

"""

# revision identifiers, used by Alembic.
revision = '3f289637f530'
down_revision = '4ba1dd8c3080'

from alembic import op


def upgrade():
    op.drop_table('aggtestgroup')
    op.drop_table('testgroup_test')
    op.drop_table('testgroup')
    op.drop_table('aggtestsuite')


def downgrade():
    raise NotImplementedError

########NEW FILE########
__FILENAME__ = 403b3fb41569_set_on_delete_cascad
"""Set ON DELETE CASCADE on Build.*

Revision ID: 403b3fb41569
Revises: 4732741c7696
Create Date: 2013-12-23 16:07:02.202873

"""

# revision identifiers, used by Alembic.
revision = '403b3fb41569'
down_revision = '4732741c7696'

from alembic import op


def upgrade():
    op.drop_constraint('build_author_id_fkey', 'build')
    op.create_foreign_key('build_author_id_fkey', 'build', 'author', ['author_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('build_change_id_fkey', 'build')
    op.create_foreign_key('build_change_id_fkey', 'build', 'change', ['change_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('build_patch_id_fkey', 'build')
    op.create_foreign_key('build_patch_id_fkey', 'build', 'patch', ['patch_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('build_project_id_fkey', 'build')
    op.create_foreign_key('build_project_id_fkey', 'build', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('build_repository_id_fkey', 'build')
    op.create_foreign_key('build_repository_id_fkey', 'build', 'repository', ['repository_id'], ['id'], ondelete='CASCADE')

    # add missing constraints
    op.create_foreign_key('build_family_id_fkey', 'build', 'buildfamily', ['family_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('build_source_id_fkey', 'build', 'source', ['source_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('build_parent_id_fkey', 'build', 'build', ['parent_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint('build_family_id_fkey', 'build')
    op.drop_constraint('build_source_id_fkey', 'build')
    op.drop_constraint('build_parent_id_fkey', 'build')

########NEW FILE########
__FILENAME__ = 4114cbbd0573_index_job_status_dat
"""Index Job.{status,date_created}

Revision ID: 4114cbbd0573
Revises: 5508859bed73
Create Date: 2014-01-06 11:28:15.691391

"""

# revision identifiers, used by Alembic.
revision = '4114cbbd0573'
down_revision = '5508859bed73'

from alembic import op


def upgrade():
    op.create_index('idx_job_status_date_created', 'job', ['status', 'date_created'])


def downgrade():
    op.drop_index('idx_job_status_date_created', 'job')

########NEW FILE########
__FILENAME__ = 4134b4818694_remove_index_build_p
"""Remove index Build.project_id

Revision ID: 4134b4818694
Revises: f2c8d15416b
Create Date: 2013-12-03 16:18:03.550867

"""

# revision identifiers, used by Alembic.
revision = '4134b4818694'
down_revision = 'f2c8d15416b'

from alembic import op


def upgrade():
    op.drop_index('idx_build_project_id', 'build')


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 4276d58dd1e6_add_buildphase
"""Add BuildPhase

Revision ID: 4276d58dd1e6
Revises: 2596f21c6f58
Create Date: 2014-02-24 14:06:16.379028

"""

# revision identifiers, used by Alembic.
revision = '4276d58dd1e6'
down_revision = '2596f21c6f58'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'buildphase',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=False),
        sa.Column('status', sa.Enum(), server_default='0', nullable=False),
        sa.Column('result', sa.Enum(), server_default='0', nullable=False),
        sa.Column('order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('date_started', sa.DateTime(), nullable=True),
        sa.Column('date_finished', sa.DateTime(), nullable=True),
        sa.Column('date_created', sa.DateTime(), server_default='now()', nullable=False),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('build_id', 'label', name='unq_buildphase_key')
    )


def downgrade():
    op.drop_table('buildphase')

########NEW FILE########
__FILENAME__ = 4289d4c9dac6_set_on_delete_cascad
"""Set ON DELETE CASCADE on AggregateTestGroup.*

Revision ID: 4289d4c9dac6
Revises: 1caf0d25843b
Create Date: 2013-12-23 16:15:30.023843

"""

# revision identifiers, used by Alembic.
revision = '4289d4c9dac6'
down_revision = '1caf0d25843b'

from alembic import op


def upgrade():
    op.drop_constraint('aggtestgroup_project_id_fkey', 'aggtestgroup')
    op.create_foreign_key('aggtestgroup_project_id_fkey', 'aggtestgroup', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('aggtestgroup_suite_id_fkey', 'aggtestgroup')
    op.create_foreign_key('aggtestgroup_suite_id_fkey', 'aggtestgroup', 'aggtestsuite', ['suite_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('aggtestgroup_parent_id_fkey', 'aggtestgroup')
    op.create_foreign_key('aggtestgroup_parent_id_fkey', 'aggtestgroup', 'aggtestgroup', ['suite_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('aggtestgroup_first_build_id_fkey', 'aggtestgroup')
    op.create_foreign_key('aggtestgroup_first_build_id_fkey', 'aggtestgroup', 'build', ['first_build_id'], ['id'], ondelete='CASCADE')

    op.create_foreign_key('aggtestgroup_last_build_id_fkey', 'aggtestgroup', 'build', ['last_build_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint('aggtestgroup_last_build_id_fkey', 'aggtestgroup')

########NEW FILE########
__FILENAME__ = 42e9d35a4098_rename_buildstep_job
"""Rename BuildStep -> JobStep

Revision ID: 42e9d35a4098
Revises: 516f04a1a754
Create Date: 2013-12-25 23:44:30.776610

"""

# revision identifiers, used by Alembic.
revision = '42e9d35a4098'
down_revision = '516f04a1a754'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE buildstep RENAME TO jobstep')


def downgrade():
    op.execute('ALTER TABLE jobstep RENAME TO buildstep')

########NEW FILE########
__FILENAME__ = 45e1cfacfc7d_task_parent_id_is_op
"""Task.parent_id is optional

Revision ID: 45e1cfacfc7d
Revises: 26dbd6ff063c
Create Date: 2014-01-13 16:23:03.890537

"""

# revision identifiers, used by Alembic.
revision = '45e1cfacfc7d'
down_revision = '26dbd6ff063c'

from alembic import op
from sqlalchemy.dialects import postgresql


def upgrade():
    op.alter_column('task', 'parent_id', existing_type=postgresql.UUID(),
                    nullable=True)


def downgrade():
    op.alter_column('task', 'parent_id', existing_type=postgresql.UUID(),
                    nullable=False)

########NEW FILE########
__FILENAME__ = 4640ecd97c82_add_testgroup_num_le
"""Add TestGroup.num_leaves

Revision ID: 4640ecd97c82
Revises: 48a922151dd4
Create Date: 2013-11-08 13:11:18.802332

"""

# revision identifiers, used by Alembic.
revision = '4640ecd97c82'
down_revision = '48a922151dd4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('testgroup', sa.Column('num_leaves', sa.Integer(), nullable=False, server_default='0'))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('testgroup', 'num_leaves')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 469bba60eb50_set_on_delete_cascad
"""Set ON DELETE CASCADE on BuildPhase.*

Revision ID: 469bba60eb50
Revises: 250341e605b7
Create Date: 2013-12-23 16:01:52.586436

"""

# revision identifiers, used by Alembic.
revision = '469bba60eb50'
down_revision = '250341e605b7'

from alembic import op


def upgrade():
    op.drop_constraint('buildphase_build_id_fkey', 'buildphase')
    op.create_foreign_key('buildphase_build_id_fkey', 'buildphase', 'build', ['build_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildphase_project_id_fkey', 'buildphase')
    op.create_foreign_key('buildphase_project_id_fkey', 'buildphase', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildphase_repository_id_fkey', 'buildphase')
    op.create_foreign_key('buildphase_repository_id_fkey', 'buildphase', 'repository', ['repository_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 4732741c7696_set_on_delete_cascad
"""Set ON DELETE CASCADE on BuildFamily.*

Revision ID: 4732741c7696
Revises: 102eea94977e
Create Date: 2013-12-23 16:05:01.655149

"""

# revision identifiers, used by Alembic.
revision = '4732741c7696'
down_revision = '102eea94977e'

from alembic import op


def upgrade():
    op.drop_constraint('buildfamily_author_id_fkey', 'buildfamily')
    op.create_foreign_key('buildfamily_author_id_fkey', 'buildfamily', 'author', ['author_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildfamily_patch_id_fkey', 'buildfamily')
    op.create_foreign_key('buildfamily_patch_id_fkey', 'buildfamily', 'patch', ['patch_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildfamily_project_id_fkey', 'buildfamily')
    op.create_foreign_key('buildfamily_project_id_fkey', 'buildfamily', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('buildfamily_repository_id_fkey', 'buildfamily')
    op.create_foreign_key('buildfamily_repository_id_fkey', 'buildfamily', 'repository', ['repository_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 47e23df5a7ed_add_testgroup_result
"""Add TestGroup.result

Revision ID: 47e23df5a7ed
Revises: 520eba1ce36e
Create Date: 2013-11-05 14:01:08.310862

"""

# revision identifiers, used by Alembic.
revision = '47e23df5a7ed'
down_revision = '520eba1ce36e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('testgroup', sa.Column('result', sa.Enum(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('testgroup', 'result')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 48a922151dd4_correct_test_schemas
"""Correct Test schemas

Revision ID: 48a922151dd4
Revises: 2b71d67ef04d
Create Date: 2013-11-07 13:12:14.375337

"""

# revision identifiers, used by Alembic.
revision = '48a922151dd4'
down_revision = '2b71d67ef04d'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.execute('UPDATE testgroup SET result = 0 WHERE result IS NULL')
    op.execute('UPDATE test SET result = 0 WHERE result IS NULL')
    op.execute('UPDATE testgroup SET num_failed = 0 WHERE num_failed IS NULL')
    op.execute('UPDATE testgroup SET num_tests = 0 WHERE num_tests IS NULL')

    op.alter_column('test', 'date_created',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('test', 'result',
               existing_type=sa.INTEGER(),
               server_default=text('0'),
               nullable=False)
    op.alter_column('testgroup', 'date_created',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('testgroup', 'name',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('testgroup', 'num_failed',
               existing_type=sa.INTEGER(),
               server_default=text('0'),
               nullable=False)
    op.alter_column('testgroup', 'num_tests',
               existing_type=sa.INTEGER(),
               server_default=text('0'),
               nullable=False)
    op.alter_column('testgroup', 'result',
               existing_type=sa.INTEGER(),
               server_default=text('0'),
               nullable=False)
    op.alter_column('testsuite', 'date_created',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('testsuite', 'name',
               existing_type=sa.TEXT(),
               nullable=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('testsuite', 'name',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('testsuite', 'date_created',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('testgroup', 'result',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('testgroup', 'num_tests',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('testgroup', 'num_failed',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('testgroup', 'name',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('testgroup', 'date_created',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('test', 'result',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('test', 'date_created',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 4901f27ade8e_fill_target
"""Fill target

Revision ID: 4901f27ade8e
Revises: 52bcea82b482
Create Date: 2013-11-11 17:25:38.930307

"""

# revision identifiers, used by Alembic.
revision = '4901f27ade8e'
down_revision = '52bcea82b482'

from alembic import op


def upgrade():
    op.execute("update build set target = substr(revision_sha, 0, 12) where target is null and revision_sha is not null")


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 4a12e7f0159d_remove_build_repository_id_revision_sha_
"""Remove Build.{repository_id,revision_sha,patch_id}

Revision ID: 4a12e7f0159d
Revises: 1b2fa9c97090
Create Date: 2014-05-15 12:12:19.106724

"""

# revision identifiers, used by Alembic.
revision = '4a12e7f0159d'
down_revision = '1b2fa9c97090'

from alembic import op


def upgrade():
    op.drop_column('build', 'revision_sha')
    op.drop_column('build', 'repository_id')
    op.drop_column('build', 'patch_id')


def downgrade():
    raise NotImplementedError

########NEW FILE########
__FILENAME__ = 4ae598236ef1_unused_indexes_on_jo
"""Unused indexes on Job

Revision ID: 4ae598236ef1
Revises: 4ffb7e1df217
Create Date: 2014-01-21 14:19:27.134472

"""

# revision identifiers, used by Alembic.
revision = '4ae598236ef1'
down_revision = '4ffb7e1df217'

from alembic import op


def upgrade():
    op.drop_index('idx_build_source_id', 'job')
    op.drop_index('idx_build_family_id', 'job')


def downgrade():
    raise NotImplementedError

########NEW FILE########
__FILENAME__ = 4ba1dd8c3080_add_index_for_projec
"""Add index for project test list

Revision ID: 4ba1dd8c3080
Revises: 2c380be0a31e
Create Date: 2014-04-14 11:08:05.598439

"""

# revision identifiers, used by Alembic.
revision = '4ba1dd8c3080'
down_revision = '2c380be0a31e'

from alembic import op


def upgrade():
    op.create_index('idx_test_project_key', 'test', ['project_id', 'label_sha'])


def downgrade():
    op.drop_index('idx_test_project_key', 'test')

########NEW FILE########
__FILENAME__ = 4d302aa44bc8_add_additional_revis
"""Add additional revision data

Revision ID: 4d302aa44bc8
Revises: 215db24a630a
Create Date: 2013-11-26 16:20:59.454360

"""

# revision identifiers, used by Alembic.
revision = '4d302aa44bc8'
down_revision = '215db24a630a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('revision', sa.Column('committer_id', sa.GUID(), nullable=True))
    op.add_column('revision', sa.Column('date_committed', sa.DateTime(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('revision', 'date_committed')
    op.drop_column('revision', 'committer_id')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 4d5d239d53b4_set_on_delete_cascad
"""Set ON DELETE CASCADE on TestSuite.*

Revision ID: 4d5d239d53b4
Revises: 501983249c94
Create Date: 2013-12-23 16:14:08.812850

"""

# revision identifiers, used by Alembic.
revision = '4d5d239d53b4'
down_revision = '501983249c94'

from alembic import op


def upgrade():
    op.drop_constraint('testsuite_project_id_fkey', 'testsuite')
    op.create_foreign_key('testsuite_project_id_fkey', 'testsuite', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('testsuite_build_id_fkey', 'testsuite')
    op.create_foreign_key('testsuite_build_id_fkey', 'testsuite', 'build', ['build_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 4e68c2a3d269_add_artifact
"""Add Artifact

Revision ID: 4e68c2a3d269
Revises: 586238e1375a
Create Date: 2014-02-06 10:24:04.343490

"""

# revision identifiers, used by Alembic.
revision = '4e68c2a3d269'
down_revision = '586238e1375a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'artifact',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('job_id', sa.GUID(), nullable=False),
        sa.Column('step_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.Column('data', sa.JSONEncodedDict(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['job.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['step_id'], ['jobstep.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('step_id', 'name', name='unq_artifact_name'),
    )


def downgrade():
    op.drop_table('artifact')

########NEW FILE########
__FILENAME__ = 4f955feb6d07_rename_build_job
"""Rename Build -> Job

Revision ID: 4f955feb6d07
Revises: 554f414d4c46
Create Date: 2013-12-25 23:17:26.666301

"""

# revision identifiers, used by Alembic.
revision = '4f955feb6d07'
down_revision = '554f414d4c46'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE build RENAME TO job')


def downgrade():
    op.execute('ALTER TABLE job RENAME TO build')

########NEW FILE########
__FILENAME__ = 4ffb7e1df217_unique_jobphase_job_
"""Unique JobPhase.{job_id,label}

Revision ID: 4ffb7e1df217
Revises: 545e104c5f5a
Create Date: 2014-01-21 11:12:10.408310

"""

# revision identifiers, used by Alembic.
revision = '4ffb7e1df217'
down_revision = '545e104c5f5a'

from alembic import op


def upgrade():
    op.create_unique_constraint('unq_jobphase_key', 'jobphase', ['job_id', 'label'])


def downgrade():
    op.drop_constraint('unq_jobphase_key', 'jobphase')

########NEW FILE########
__FILENAME__ = 501983249c94_set_on_delete_cascad
"""Set ON DELETE CASCADE on Patch.*

Revision ID: 501983249c94
Revises: 403b3fb41569
Create Date: 2013-12-23 16:12:13.610366

"""

# revision identifiers, used by Alembic.
revision = '501983249c94'
down_revision = '403b3fb41569'

from alembic import op


def upgrade():
    op.drop_constraint('patch_change_id_fkey', 'patch')
    op.create_foreign_key('patch_change_id_fkey', 'patch', 'change', ['change_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('patch_project_id_fkey', 'patch')
    op.create_foreign_key('patch_project_id_fkey', 'patch', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('patch_repository_id_fkey', 'patch')
    op.create_foreign_key('patch_repository_id_fkey', 'patch', 'repository', ['repository_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 5026dbcee21d_test_build_id_job_id
"""Test*.build_id => job_id

Revision ID: 5026dbcee21d
Revises: 42e9d35a4098
Create Date: 2013-12-25 23:50:12.762986

"""

# revision identifiers, used by Alembic.
revision = '5026dbcee21d'
down_revision = '42e9d35a4098'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE test RENAME COLUMN build_id TO job_id')
    op.execute('ALTER TABLE testgroup RENAME COLUMN build_id TO job_id')
    op.execute('ALTER TABLE testsuite RENAME COLUMN build_id TO job_id')


def downgrade():
    op.execute('ALTER TABLE test RENAME COLUMN job_id TO build_id')
    op.execute('ALTER TABLE testgroup RENAME COLUMN job_id TO build_id')
    op.execute('ALTER TABLE testsuite RENAME COLUMN job_id TO build_id')

########NEW FILE########
__FILENAME__ = 516f04a1a754_rename_buildphase_jo
"""Rename BuildPhase -> JobPhase

Revision ID: 516f04a1a754
Revises: 6483270c001
Create Date: 2013-12-25 23:40:42.892745

"""

# revision identifiers, used by Alembic.
revision = '516f04a1a754'
down_revision = '6483270c001'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE buildphase RENAME TO jobphase')


def downgrade():
    op.execute('ALTER TABLE jobphase RENAME TO buildphase')

########NEW FILE########
__FILENAME__ = 5177cfff57d7_add_testgroup_and_te
"""Add TestGroup and TestSuite

Revision ID: 5177cfff57d7
Revises: 14491da59392
Create Date: 2013-11-04 12:42:37.249656

"""

from __future__ import absolute_import, print_function

# revision identifiers, used by Alembic.
revision = '5177cfff57d7'
down_revision = '14491da59392'

from alembic import op
from datetime import datetime
from hashlib import sha1
from sqlalchemy.sql import table
from uuid import uuid4
import sqlalchemy as sa


def upgrade():
    from changes.constants import Result

    testsuites_table = table(
        'testsuite',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('name_sha', sa.String(length=40), nullable=False),
        sa.Column('name', sa.Text(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
    )
    testgroups_table = table(
        'testgroup',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('name_sha', sa.String(length=40), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('num_tests', sa.Integer(), nullable=True),
        sa.Column('num_failed', sa.Integer(), nullable=True),
        sa.Column('name', sa.Text(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
    )
    testgroups_m2m_table = table(
        'testgroup_test',
        sa.Column('group_id', sa.GUID(), nullable=False),
        sa.Column('test_id', sa.GUID(), nullable=False),
    )
    testcases_table = table(
        'test',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('package', sa.Text(), nullable=True),
        sa.Column('name', sa.Text(), nullable=True),
        sa.Column('group', sa.Text(), nullable=True),
        sa.Column('suite_id', sa.GUID(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('result', sa.Enum(), nullable=True),
    )

    connection = op.get_bind()

    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('testsuite',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('build_id', sa.GUID(), nullable=False),
    sa.Column('project_id', sa.GUID(), nullable=False),
    sa.Column('name_sha', sa.String(length=40), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('build_id','name_sha', name='_suite_key')
    )
    op.create_table('testgroup',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('build_id', sa.GUID(), nullable=False),
    sa.Column('project_id', sa.GUID(), nullable=False),
    sa.Column('suite_id', sa.GUID(), nullable=True),
    sa.Column('parent_id', sa.GUID(), nullable=True),
    sa.Column('name_sha', sa.String(length=40), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('duration', sa.Integer(), default=0, nullable=True),
    sa.Column('num_tests', sa.Integer(), default=0, nullable=True),
    sa.Column('num_failed', sa.Integer(), default=0, nullable=True),
    sa.Column('data', sa.JSONEncodedDict(), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
    sa.ForeignKeyConstraint(['parent_id'], ['testgroup.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['suite_id'], ['testsuite.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('build_id','suite_id','name_sha', name='_group_key')
    )
    op.create_table('testgroup_test',
    sa.Column('group_id', sa.GUID(), nullable=False),
    sa.Column('test_id', sa.GUID(), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['testgroup.id'], ),
    sa.ForeignKeyConstraint(['test_id'], ['test.id'], ),
    sa.PrimaryKeyConstraint('group_id', 'test_id')
    )
    op.add_column(u'test', sa.Column('suite_id', sa.GUID(), nullable=True))

    # perform data migrations
    for testcase in connection.execute(testcases_table.select()):
        # migrate group to suite
        print("Migrating TestCase %s" % (testcase.id,))

        suite_name = testcase.group or 'default'
        suite_sha = sha1(suite_name).hexdigest()

        result = connection.execute(testsuites_table.select().where(sa.and_(
            testsuites_table.c.build_id == testcase.build_id,
            testsuites_table.c.name_sha == suite_sha,
        )).limit(1)).fetchone()
        if not result:
            suite_id = uuid4()
            connection.execute(
                testsuites_table.insert().values(
                    id=suite_id,
                    build_id=testcase.build_id,
                    project_id=testcase.project_id,
                    name=suite_name,
                    name_sha=suite_sha,
                    date_created=datetime.utcnow(),
                )
            )
        else:
            suite_id = result[0]

        connection.execute(
            testcases_table.update().where(
                testcases_table.c.id == testcase.id,
            ).values({
                testcases_table.c.suite_id: suite_id,
            })
        )
        # add package as group
        group_name = testcase.package or testcase.name.rsplit('.', 1)[1]
        group_sha = sha1(group_name).hexdigest()

        result = connection.execute(testgroups_table.select().where(sa.and_(
            testgroups_table.c.build_id == testcase.build_id,
            testgroups_table.c.name_sha == group_sha,
        )).limit(1)).fetchone()

        if not result:
            group_id = uuid4()
            connection.execute(
                testgroups_table.insert().values(
                    id=group_id,
                    build_id=testcase.build_id,
                    project_id=testcase.project_id,
                    name=group_name,
                    name_sha=group_sha,
                    date_created=datetime.utcnow(),
                    duration=0,
                    num_tests=0,
                    num_failed=0,
                )
            )
        else:
            group_id = result[0]

        update_values = {
            testgroups_table.c.num_tests: testgroups_table.c.num_tests + 1,
            testgroups_table.c.duration: testgroups_table.c.duration + testcase.duration,
        }
        if testcase.result == Result.failed.value:
            update_values[testgroups_table.c.num_failed] = testgroups_table.c.num_failed + 1

        connection.execute(testgroups_m2m_table.insert().values({
            testgroups_m2m_table.c.group_id: group_id,
            testgroups_m2m_table.c.test_id: testcase.id,
        }))

        connection.execute(testgroups_table.update().where(
            testgroups_table.c.id == group_id,
        ).values(update_values))

    op.drop_column(u'test', u'group')
    op.drop_column(u'test', u'group_sha')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column(u'test', sa.Column(u'group_sha', sa.VARCHAR(length=40), nullable=True))
    op.add_column(u'test', sa.Column(u'group', sa.TEXT(), nullable=True))
    op.drop_column(u'test', 'suite_id')
    op.drop_table('testgroup_test')
    op.drop_table('testgroup')
    op.drop_table('testsuite')
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 520eba1ce36e_remove_author_name_u
"""Remove Author.name unique constraint

Revision ID: 520eba1ce36e
Revises: 18c045b75331
Create Date: 2013-11-04 19:20:04.277883

"""

# revision identifiers, used by Alembic.
revision = '520eba1ce36e'
down_revision = '18c045b75331'

from alembic import op


def upgrade():
    op.drop_constraint('author_name_key', 'author')


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 524b3c27203b_remove_job_author_id
"""Remove Job.{author_id,repository_id,patch_id,revision_sha,message,target,cause,parent_id}

Revision ID: 524b3c27203b
Revises: 3042d0ca43bf
Create Date: 2014-01-05 16:36:43.476520

"""

# revision identifiers, used by Alembic.
revision = '524b3c27203b'
down_revision = '3042d0ca43bf'

from alembic import op


def upgrade():
    op.drop_column('job', 'revision_sha')
    op.drop_column('job', 'patch_id')
    op.drop_column('job', 'author_id')
    op.drop_column('job', 'repository_id')
    op.drop_column('job', 'message')
    op.drop_column('job', 'target')
    op.drop_column('job', 'cause')
    op.drop_column('job', 'parent_id')


def downgrade():
    raise NotImplementedError

########NEW FILE########
__FILENAME__ = 52bcea82b482_remove_patch_url
"""Remove Patch.url

Revision ID: 52bcea82b482
Revises: 346c011ca77a
Create Date: 2013-11-11 17:17:49.008228

"""

# revision identifiers, used by Alembic.
revision = '52bcea82b482'
down_revision = '346c011ca77a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('patch', u'url')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('patch', sa.Column(u'url', sa.VARCHAR(length=200), nullable=True))
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = 545ba163595_rename_buildfamily_b
"""Rename BuildFamily => Build

Revision ID: 545ba163595
Revises: 256ab638deaa
Create Date: 2013-12-26 01:51:58.807080

"""

# revision identifiers, used by Alembic.
revision = '545ba163595'
down_revision = '256ab638deaa'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE buildfamily RENAME TO build')


def downgrade():
    op.execute('ALTER TABLE build RENAME TO buildfamily')

########NEW FILE########
__FILENAME__ = 545e104c5f5a_add_logsource_step_i
"""Add LogSource.step_id

Revision ID: 545e104c5f5a
Revises: 5677ef75c712
Create Date: 2014-01-15 17:18:53.402012

"""

# revision identifiers, used by Alembic.
revision = '545e104c5f5a'
down_revision = '5677ef75c712'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('logsource', sa.Column('step_id', sa.GUID(), nullable=True))


def downgrade():
    op.drop_column('logsource', 'step_id')

########NEW FILE########
__FILENAME__ = 54a5c0c8793b_set_on_delete_cascad
"""Set ON DELETE CASCADE on Change.*

Revision ID: 54a5c0c8793b
Revises: 4289d4c9dac6
Create Date: 2013-12-23 16:36:32.007578

"""

# revision identifiers, used by Alembic.
revision = '54a5c0c8793b'
down_revision = '4289d4c9dac6'

from alembic import op


def upgrade():
    op.drop_constraint('change_project_id_fkey', 'change')
    op.create_foreign_key('change_project_id_fkey', 'change', 'project', ['project_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('change_author_id_fkey', 'change')
    op.create_foreign_key('change_author_id_fkey', 'change', 'author', ['author_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('change_repository_id_fkey', 'change')
    op.create_foreign_key('change_repository_id_fkey', 'change', 'repository', ['repository_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 5508859bed73_index_source_patch_i
"""Index Source.patch_id

Revision ID: 5508859bed73
Revises: 26f665189ca0
Create Date: 2014-01-06 11:14:19.109932

"""

# revision identifiers, used by Alembic.
revision = '5508859bed73'
down_revision = '26f665189ca0'

from alembic import op


def upgrade():
    op.create_index('idx_source_patch_id', 'source', ['patch_id'])


def downgrade():
    op.drop_index('idx_source_patch_id', 'source')

########NEW FILE########
__FILENAME__ = 554f414d4c46_set_on_delete_cascad
"""Set ON DELETE CASCADE on Step.*

Revision ID: 554f414d4c46
Revises: 306fefe51dc6
Create Date: 2013-12-23 16:46:05.137414

"""

# revision identifiers, used by Alembic.
revision = '554f414d4c46'
down_revision = '306fefe51dc6'

from alembic import op


def upgrade():
    op.drop_constraint('step_plan_id_fkey', 'step')
    op.create_foreign_key('step_plan_id_fkey', 'step', 'plan', ['plan_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 5677ef75c712_add_user
"""Add User

Revision ID: 5677ef75c712
Revises: 45e1cfacfc7d
Create Date: 2014-01-15 11:06:25.217408

"""

# revision identifiers, used by Alembic.
revision = '5677ef75c712'
down_revision = '45e1cfacfc7d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'user',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('email', sa.String(length=128), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )


def downgrade():
    op.drop_table('user')

########NEW FILE########
__FILENAME__ = 57e24a9f2290_log_build_id_job_id
"""Log*.build_id => job_id

Revision ID: 57e24a9f2290
Revises: 35af40cebcde
Create Date: 2013-12-26 01:03:06.812123

"""

# revision identifiers, used by Alembic.
revision = '57e24a9f2290'
down_revision = '35af40cebcde'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE logsource RENAME COLUMN build_id TO job_id')
    op.execute('ALTER TABLE logchunk RENAME COLUMN build_id TO job_id')


def downgrade():
    op.execute('ALTER TABLE logsource RENAME COLUMN job_id TO build_id')
    op.execute('ALTER TABLE logchunk RENAME COLUMN job_id TO build_id')

########NEW FILE########
__FILENAME__ = 586238e1375a_add_comment
"""Add Comment

Revision ID: 586238e1375a
Revises: 24ffd1984588
Create Date: 2014-01-30 12:52:35.146236

"""

# revision identifiers, used by Alembic.
revision = '586238e1375a'
down_revision = '24ffd1984588'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'comment',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('user_id', sa.GUID(), nullable=False),
        sa.Column('job_id', sa.GUID(), nullable=True),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['job.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('comment')

########NEW FILE########
__FILENAME__ = 5896e31725d_add_aggregate_last_b
"""Add Aggregate*.last_build_id

Revision ID: 5896e31725d
Revises: 166d65e5a7e3
Create Date: 2013-12-05 13:50:57.818995

"""

# revision identifiers, used by Alembic.
revision = '5896e31725d'
down_revision = '166d65e5a7e3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('aggtestgroup', sa.Column('last_build_id', sa.GUID()))
    op.add_column('aggtestsuite', sa.Column('last_build_id', sa.GUID()))

    op.execute("update aggtestgroup set last_build_id = first_build_id where first_build_id is null")
    op.execute("update aggtestsuite set last_build_id = first_build_id where first_build_id is null")

    op.alter_column('aggtestgroup', sa.Column('last_build_id', sa.GUID(), nullable=False))
    op.alter_column('aggtestsuite', sa.Column('last_build_id', sa.GUID(), nullable=False))


def downgrade():
    op.drop_column('aggtestsuite', 'last_build_id')
    op.drop_column('aggtestgroup', 'last_build_id')

########NEW FILE########
__FILENAME__ = 5aad6f742b77_parent_revision_sha_
"""parent_revision_sha => revision_sha

Revision ID: 5aad6f742b77
Revises: 2d82db02b3ef
Create Date: 2013-11-11 17:05:31.671178

"""

# revision identifiers, used by Alembic.
revision = '5aad6f742b77'
down_revision = '2d82db02b3ef'

from alembic import op


def upgrade():
    op.execute("update build set revision_sha = parent_revision_sha")


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = 6483270c001_rename_buildplan_job
"""Rename BuildPlan -> JobPlan

Revision ID: 6483270c001
Revises: 4f955feb6d07
Create Date: 2013-12-25 23:37:07.896471

"""

# revision identifiers, used by Alembic.
revision = '6483270c001'
down_revision = '4f955feb6d07'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE buildplan RENAME TO jobplan')


def downgrade():
    op.execute('ALTER TABLE jobplan RENAME TO buildplan')

########NEW FILE########
__FILENAME__ = 97786e74292_add_task_data
"""Add Task.data

Revision ID: 97786e74292
Revises: 4ae598236ef1
Create Date: 2014-01-21 17:40:42.013002

"""

# revision identifiers, used by Alembic.
revision = '97786e74292'
down_revision = '4ae598236ef1'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('task', sa.Column('data', sa.JSONEncodedDict(), nullable=True))


def downgrade():
    op.drop_column('task', 'data')

########NEW FILE########
__FILENAME__ = bb141e41aab_add_rerun_count_to_t
"""add rerun count to tests

Revision ID: bb141e41aab
Revises: f8f72eecc7f
Create Date: 2014-03-28 13:57:17.364930

"""

# revision identifiers, used by Alembic.
revision = 'bb141e41aab'
down_revision = 'f8f72eecc7f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(u'test', sa.Column('reruns', sa.INTEGER(), nullable=True))


def downgrade():
    op.drop_column(u'test', 'reruns')

########NEW FILE########
__FILENAME__ = cb99fdfb903_add_build_family_id
"""Add Build.family_id

Revision ID: cb99fdfb903
Revises: 1109e724859f
Create Date: 2013-12-23 11:32:17.060863

"""

# revision identifiers, used by Alembic.
revision = 'cb99fdfb903'
down_revision = '1109e724859f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('build', sa.Column('family_id', sa.GUID(), nullable=True))
    op.create_index('idx_build_family_id', 'build', ['family_id'])


def downgrade():
    op.drop_index('idx_build_family_id', 'build')
    op.drop_column('build', 'family_id')

########NEW FILE########
__FILENAME__ = d324e8fc580_add_various_testsuit
"""Add various TestSuite indexes

Revision ID: d324e8fc580
Revises: 3bef10ab5088
Create Date: 2013-11-04 17:12:09.353301

"""

# revision identifiers, used by Alembic.
revision = 'd324e8fc580'
down_revision = '3bef10ab5088'

from alembic import op


def upgrade():
    op.create_index('idx_testsuite_project_id', 'testsuite', ['project_id'])


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = f26b6cb3c9c_jobstep_build_id_job
"""JobStep.build_id => job_id

Revision ID: f26b6cb3c9c
Revises: 5026dbcee21d
Create Date: 2013-12-26 00:11:38.414155

"""

# revision identifiers, used by Alembic.
revision = 'f26b6cb3c9c'
down_revision = '5026dbcee21d'

from alembic import op


def upgrade():
    op.execute('ALTER TABLE jobstep RENAME COLUMN build_id TO job_id')


def downgrade():
    op.execute('ALTER TABLE jobstep RENAME COLUMN job_id TO build_id')

########NEW FILE########
__FILENAME__ = f2c8d15416b_index_build_project_
"""Index Build.project_id,date_created

Revision ID: f2c8d15416b
Revises: 152c9c780e
Create Date: 2013-12-03 15:54:09.488066

"""

# revision identifiers, used by Alembic.
revision = 'f2c8d15416b'
down_revision = '152c9c780e'

from alembic import op


def upgrade():
    op.create_index('idx_build_project_date', 'build', ['project_id', 'date_created'])


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = f8ed1f99eb1_add_projectplan_avg_
"""Add ProjectPlan.avg_build_time

Revision ID: f8ed1f99eb1
Revises: 25d63e09ea3b
Create Date: 2014-01-02 16:12:43.339060

"""

# revision identifiers, used by Alembic.
revision = 'f8ed1f99eb1'
down_revision = '25d63e09ea3b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('project_plan', sa.Column('avg_build_time', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('project_plan', 'avg_build_time')

########NEW FILE########
__FILENAME__ = f8f72eecc7f_remove_idx_testgroup
"""Remove idx_testgroup_project_id

Revision ID: f8f72eecc7f
Revises: 1db7a1ab95db
Create Date: 2014-03-27 12:12:15.548413

"""

# revision identifiers, used by Alembic.
revision = 'f8f72eecc7f'
down_revision = '1db7a1ab95db'

from alembic import op


def upgrade():
    op.drop_index('idx_testgroup_project_id', 'testgroup')


def downgrade():
    op.create_index('idx_testgroup_project_id', 'testgroup', ['project_id'])

########NEW FILE########
__FILENAME__ = fd1a52fe89f_add_various_test_ind
"""Add various TestCase indexes

Revision ID: fd1a52fe89f
Revises: 5177cfff57d7
Create Date: 2013-11-04 17:03:03.005904

"""

# revision identifiers, used by Alembic.
revision = 'fd1a52fe89f'
down_revision = '5177cfff57d7'

from alembic import op


def upgrade():
    # TestCase
    op.create_index('idx_test_project_id', 'test', ['project_id'])
    op.create_index('idx_test_suite_id', 'test', ['suite_id'])
    op.create_unique_constraint('unq_test_key', 'test', ['build_id', 'suite_id', 'label_sha'])


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###

########NEW FILE########
__FILENAME__ = ff220d76c11_add_build_plans
"""Add build plans

Revision ID: ff220d76c11
Revises: 153b703a46ea
Create Date: 2013-12-11 16:12:18.309606

"""

# revision identifiers, used by Alembic.
revision = 'ff220d76c11'
down_revision = '153b703a46ea'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'plan',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.Column('date_modified', sa.DateTime(), nullable=False),
        sa.Column('data', sa.JSONEncodedDict(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'step',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('plan_id', sa.GUID(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.Column('date_modified', sa.DateTime(), nullable=False),
        sa.Column('implementation', sa.String(length=128), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('data', sa.JSONEncodedDict(), nullable=True),
        sa.CheckConstraint('step."order" >= 0', name='chk_step_order_positive'),
        sa.ForeignKeyConstraint(['plan_id'], ['plan.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_step_plan_id', 'step', ['plan_id'])
    op.create_table(
        'buildfamily',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('repository_id', sa.GUID(), nullable=False),
        sa.Column('revision_sha', sa.String(length=40), nullable=True),
        sa.Column('patch_id', sa.GUID(), nullable=True),
        sa.Column('author_id', sa.GUID(), nullable=True),
        sa.Column('cause', sa.Enum(), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=False),
        sa.Column('target', sa.String(length=128), nullable=True),
        sa.Column('status', sa.Enum(), nullable=False),
        sa.Column('result', sa.Enum(), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('date_started', sa.DateTime(), nullable=True),
        sa.Column('date_finished', sa.DateTime(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.Column('date_modified', sa.DateTime(), nullable=True),
        sa.Column('data', sa.JSONEncodedDict(), nullable=True),
        sa.ForeignKeyConstraint(['author_id'], ['author.id'], ),
        sa.ForeignKeyConstraint(['patch_id'], ['patch.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.ForeignKeyConstraint(['repository_id'], ['repository.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_buildfamily_project_id', 'buildfamily', ['project_id'])
    op.create_index('idx_buildfamily_repository_revision', 'buildfamily', ['repository_id', 'revision_sha'])
    op.create_index('idx_buildfamily_patch_id', 'buildfamily', ['patch_id'])
    op.create_index('idx_buildfamily_author_id', 'buildfamily', ['author_id'])

    op.create_table(
        'buildplan',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('family_id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('plan_id', sa.GUID(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=True),
        sa.Column('date_modified', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
        sa.ForeignKeyConstraint(['family_id'], ['buildfamily.id'], ),
        sa.ForeignKeyConstraint(['plan_id'], ['plan.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_buildplan_project_id', 'buildplan', ['project_id'])
    op.create_index('idx_buildplan_family_id', 'buildplan', ['family_id'])
    op.create_index('idx_buildplan_build_id', 'buildplan', ['build_id'])
    op.create_index('idx_buildplan_plan_id', 'buildplan', ['plan_id'])


def downgrade():
    op.drop_table('buildplan')
    op.drop_table('buildfamily')
    op.drop_table('step')
    op.drop_table('plan')

########NEW FILE########
__FILENAME__ = stream_data
#!/usr/bin/env python

import random
import time

from datetime import datetime

from changes import mock
from changes.config import db, create_app
from changes.constants import Result, Status
from changes.db.utils import get_or_create
from changes.models import (
    Change, Job, JobStep, LogSource, TestResultManager, ProjectPlan,
    ItemStat
)
from changes.testutils.fixtures import Fixtures

app = create_app()
app_context = app.app_context()
app_context.push()

fixtures = Fixtures()


def create_new_change(project, **kwargs):
    return mock.change(project=project, **kwargs)


def create_new_entry(project):
    new_change = (random.randint(0, 2) == 5)
    if not new_change:
        try:
            change = Change.query.all()[0]
        except IndexError:
            new_change = True

    if new_change:
        author = mock.author()
        revision = mock.revision(project.repository, author)
        change = create_new_change(
            project=project,
            author=author,
            message=revision.message,
        )
    else:
        change.date_modified = datetime.utcnow()
        db.session.add(change)
        revision = mock.revision(project.repository, change.author)

    if random.randint(0, 1) == 1:
        patch = mock.patch(project)
    else:
        patch = None
    source = mock.source(
        project.repository, revision_sha=revision.sha, patch=patch)

    date_started = datetime.utcnow()

    build = mock.build(
        author=change.author,
        project=project,
        source=source,
        message=change.message,
        result=Result.unknown,
        status=Status.in_progress,
        date_started=date_started,
    )

    build_task = fixtures.create_task(
        task_id=build.id,
        task_name='sync_build',
        data={'kwargs': {'build_id': build.id.hex}},
    )

    db.session.add(ItemStat(item_id=build.id, name='lines_covered', value='5'))
    db.session.add(ItemStat(item_id=build.id, name='lines_uncovered', value='5'))
    db.session.add(ItemStat(item_id=build.id, name='diff_lines_covered', value='5'))
    db.session.add(ItemStat(item_id=build.id, name='diff_lines_uncovered', value='5'))

    db.session.commit()

    for x in xrange(0, random.randint(1, 3)):
        job = mock.job(
            build=build,
            change=change,
            status=Status.in_progress,
        )
        fixtures.create_task(
            task_id=job.id.hex,
            parent_id=build_task.task_id,
            task_name='sync_job',
            data={'kwargs': {'job_id': job.id.hex}},
        )

        db.session.commit()
        if patch:
            mock.file_coverage(project, job, patch)

        for step in JobStep.query.filter(JobStep.job == job):
            logsource = LogSource(
                job=job,
                project=job.project,
                step=step,
                name=step.label,
            )
            db.session.add(logsource)
            db.session.commit()

            offset = 0
            for x in xrange(30):
                lc = mock.logchunk(source=logsource, offset=offset)
                db.session.commit()
                offset += lc.size

    return build


def update_existing_entry(project):
    try:
        job = Job.query.filter(
            Job.status == Status.in_progress,
        )[0]
    except IndexError:
        return create_new_entry(project)

    job.date_modified = datetime.utcnow()
    job.status = Status.finished
    job.result = Result.failed if random.randint(0, 3) == 1 else Result.passed
    job.date_finished = datetime.utcnow()
    db.session.add(job)

    jobstep = JobStep.query.filter(JobStep.job == job).first()
    if jobstep:
        test_results = []
        for _ in xrange(50):
            if job.result == Result.failed:
                result = Result.failed if random.randint(0, 3) == 1 else Result.passed
            else:
                result = Result.passed
            test_results.append(mock.test_result(jobstep, result=result))
        TestResultManager(jobstep).save(test_results)

    if job.status == Status.finished:
        job.build.status = job.status
        job.build.result = job.result
        job.build.date_finished = job.date_finished
        job.build.date_modified = job.date_finished
        db.session.add(job.build)

    return job


def gen(project):
    if random.randint(0, 5) == 1:
        build = create_new_entry(project)
    else:
        build = update_existing_entry(project)

    db.session.commit()

    return build


def loop():
    repository = mock.repository()
    project = mock.project(repository)
    plan = mock.plan()
    get_or_create(ProjectPlan, where={
        'plan': plan,
        'project': project,
    })

    while True:
        build = gen(project)
        print 'Pushed build {0} on {1}'.format(build.id, project.slug)
        time.sleep(0.1)


if __name__ == '__main__':
    loop()

########NEW FILE########
__FILENAME__ = test_build
from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models import Build, Project, Source


def test_simple():
    build = Build(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        label='Hello world',
        target='D1234',
        message='Foo bar',
        project=Project(
            slug='test', name='test', id=UUID('1e7958a368f44b0eb5a57372a9910d50'),
        ),
        project_id=UUID('1e7958a368f44b0eb5a57372a9910d50'),
        source=Source(
            revision_sha='1e7958a368f44b0eb5a57372a9910d50',
        ),
        date_created=datetime(2013, 9, 19, 22, 15, 22),
        date_started=datetime(2013, 9, 19, 22, 15, 23),
        date_finished=datetime(2013, 9, 19, 22, 15, 33),
    )
    result = serialize(build)
    assert result['name'] == 'Hello world'
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['source']['id'] == build.source.id.hex
    assert result['target'] == 'D1234'
    assert result['message'] == 'Foo bar'
    assert result['dateCreated'] == '2013-09-19T22:15:22'
    assert result['dateStarted'] == '2013-09-19T22:15:23'
    assert result['dateFinished'] == '2013-09-19T22:15:33'
    assert result['duration'] == 10000
    assert result['link'] == 'http://example.com/projects/test/builds/{0}/'.format(build.id.hex)

########NEW FILE########
__FILENAME__ = test_cause
from changes.api.serializer import serialize
from changes.constants import Cause


def test_simple():
    result = serialize(Cause.retry)
    assert result['id'] == 'retry'
    assert result['name'] == 'Retry'

########NEW FILE########
__FILENAME__ = test_change
from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models import Project, Change


def test_simple():
    change = Change(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        label='Hello world',
        project=Project(slug='test', name='test'),
        date_created=datetime(2013, 9, 19, 22, 15, 22),
        date_modified=datetime(2013, 9, 19, 22, 15, 23),
    )
    result = serialize(change)
    assert result['name'] == 'Hello world'
    assert result['link'] == 'http://example.com/changes/33846695b2774b29a71795a009e8168a/'
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['dateCreated'] == '2013-09-19T22:15:22'
    assert result['dateModified'] == '2013-09-19T22:15:23'

########NEW FILE########
__FILENAME__ = test_job
from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models import Job, Project, Build, Change


def test_simple():
    job = Job(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        label='Hello world',
        project=Project(slug='test', name='test'),
        date_created=datetime(2013, 9, 19, 22, 15, 22),
        date_started=datetime(2013, 9, 19, 22, 15, 23),
        date_finished=datetime(2013, 9, 19, 22, 15, 33),
        build=Build(
            id=UUID('1e7958a368f44b0eb5a57372a9910d50'),
        ),
        build_id=UUID('1e7958a368f44b0eb5a57372a9910d50'),
        change=Change(
            id=UUID(hex='2e18a7cbc0c24316b2ef9d41fea191d6'),
            label='Hello world',
        ),
    )
    result = serialize(job)
    assert result['name'] == 'Hello world'
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['dateCreated'] == '2013-09-19T22:15:22'
    assert result['dateStarted'] == '2013-09-19T22:15:23'
    assert result['dateFinished'] == '2013-09-19T22:15:33'
    assert result['duration'] == 10000

########NEW FILE########
__FILENAME__ = test_logchunk
from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models import LogSource, LogChunk


def test_simple():
    logchunk = LogChunk(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        source_id=UUID(hex='0b61b8a47ec844918d372d5741187b1c'),
        source=LogSource(id=UUID(hex='0b61b8a47ec844918d372d5741187b1c')),
        offset=10,
        size=7,
        text='\x1b[0;36mnotice: foo bar',
        date_created=datetime(2013, 9, 19, 22, 15, 22),
    )
    result = serialize(logchunk)
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['source']['id'] == '0b61b8a47ec844918d372d5741187b1c'
    assert result['text'] == '<span class="ansi36">notice: foo bar</span>'
    assert result['size'] == 7
    assert result['offset'] == 10

########NEW FILE########
__FILENAME__ = test_logsource
from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models import LogSource, Job, JobStep


def test_simple():
    logsource = LogSource(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        job_id=UUID(hex='2e18a7cbc0c24316b2ef9d41fea191d6'),
        job=Job(id=UUID(hex='2e18a7cbc0c24316b2ef9d41fea191d6')),
        step=JobStep(
            id=UUID(hex='36c7af5e56aa4a7fbf076e13ac00a866'),
            phase_id=UUID(hex='46c7af5e56aa4a7fbf076e13ac00a866')
        ),
        name='console',
        date_created=datetime(2013, 9, 19, 22, 15, 22),
    )
    result = serialize(logsource)
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['name'] == 'console'
    assert result['dateCreated'] == '2013-09-19T22:15:22'
    assert result['step']['id'] == '36c7af5e56aa4a7fbf076e13ac00a866'

########NEW FILE########
__FILENAME__ = test_patch
from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models import Patch, Project
from changes.testutils import SAMPLE_DIFF


def test_simple():
    patch = Patch(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        diff=SAMPLE_DIFF,
        project=Project(slug='test', name='test'),
        parent_revision_sha='1e7958a368f44b0eb5a57372a9910d50',
        date_created=datetime(2013, 9, 19, 22, 15, 22),
    )
    result = serialize(patch)
    assert result['link'] == 'http://example.com/patches/33846695b2774b29a71795a009e8168a/'
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['parentRevision'] == {
        'sha': '1e7958a368f44b0eb5a57372a9910d50',
    }
    assert result['dateCreated'] == '2013-09-19T22:15:22'
    assert result['diff'] == SAMPLE_DIFF

########NEW FILE########
__FILENAME__ = test_project
from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models import Project


def test_simple():
    project = Project(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        slug='hello-world',
        name='Hello world',
        date_created=datetime(2013, 9, 19, 22, 15, 22),
    )
    result = serialize(project)
    assert result['name'] == 'Hello world'
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['slug'] == 'hello-world'
    assert result['dateCreated'] == '2013-09-19T22:15:22'

########NEW FILE########
__FILENAME__ = test_revision
from datetime import datetime

from changes.api.serializer import serialize
from changes.models import Revision, Repository, Author


def test_simple():
    revision = Revision(
        sha='33846695b2774b29a71795a009e8168a',
        repository=Repository(),
        author=Author(
            name='Foo Bar',
            email='foo@example.com',
        ),
        parents=['a' * 40],
        branches=['master'],
        message='hello world',
        date_created=datetime(2013, 9, 19, 22, 15, 22),
    )
    result = serialize(revision)
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['author']['name'] == 'Foo Bar'
    assert result['author']['email'] == 'foo@example.com'
    assert result['message'] == 'hello world'
    assert result['dateCreated'] == '2013-09-19T22:15:22'
    assert result['parents'] == ['a' * 40]
    assert result['branches'] == ['master']

########NEW FILE########
__FILENAME__ = test_source
from datetime import datetime

from changes.api.serializer import serialize
from changes.config import db
from changes.models import Source
from changes.testutils import TestCase


class SourceSerializerTest(TestCase):
    def test_simple(self):
        repo = self.create_repo()
        revision = self.create_revision(repository=repo)
        source = Source(
            repository=repo,
            repository_id=repo.id,
            revision=revision,
            revision_sha=revision.sha,
            date_created=datetime(2013, 9, 19, 22, 15, 22),
        )
        db.session.add(source)
        result = serialize(source)
        assert result['id'] == source.id.hex
        assert result['dateCreated'] == '2013-09-19T22:15:22'
        assert result['revision']['id'] == revision.sha

########NEW FILE########
__FILENAME__ = test_testcase
from datetime import datetime

from changes.api.serializer import serialize
from changes.api.serializer.models.testcase import (
    TestCaseWithJobSerializer, TestCaseWithOriginSerializer, GeneralizedTestCase
)
from changes.constants import Result
from changes.testutils import TestCase


class TestCaseSerializerTestCase(TestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)
        testcase = self.create_test(
            package='test.group.ClassName',
            name='test_foo',
            job=job,
            duration=134,
            result=Result.failed,
            date_created=datetime(2013, 9, 19, 22, 15, 22),
            reruns=1,
        )
        result = serialize(testcase)
        assert result['id'] == str(testcase.id.hex)
        assert result['job']['id'] == str(job.id.hex)
        assert result['project']['id'] == str(project.id.hex)
        assert result['shortName'] == 'test_foo'
        assert result['name'] == 'test_foo'
        assert result['package'] == 'test.group.ClassName'
        assert result['dateCreated'] == '2013-09-19T22:15:22'
        assert result['result']['id'] == 'failed'
        assert result['duration'] == 134
        assert result['numRetries'] == 1

    def test_implicit_package(self):
        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)
        testcase = self.create_test(
            name='test.group.ClassName.test_foo',
            package=None,
            job=job,
        )

        result = serialize(testcase)

        assert result['shortName'] == 'test_foo'
        assert result['name'] == 'test.group.ClassName.test_foo'
        assert result['package'] == 'test.group.ClassName'

    def test_implicit_package_only_name(self):
        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)
        testcase = self.create_test(
            name='test_foo',
            package=None,
            job=job
        )
        result = serialize(testcase)
        assert result['shortName'] == 'test_foo'
        assert result['name'] == 'test_foo'
        assert result['package'] is None


class TestCaseWithJobSerializerTestCase(TestCase):
    def test_simple(self):
        from changes.models import TestCase

        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)
        testcase = self.create_test(
            job=job,
        )
        result = serialize(testcase, {TestCase: TestCaseWithJobSerializer()})
        assert result['job']['id'] == str(job.id.hex)


class TestCaseWithOriginSerializerTestCase(TestCase):
    def test_simple(self):
        from changes.models import TestCase

        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)
        testcase = self.create_test(
            job=job,
        )

        result = serialize(testcase, {TestCase: TestCaseWithOriginSerializer()})
        assert result['origin'] is None

        testcase.origin = 'foobar'
        result = serialize(testcase, {TestCase: TestCaseWithOriginSerializer()})
        assert result['origin'] == 'foobar'


class GeneralizedTestCaseSerializerTestCase(TestCase):
    def test_simple(self):
        from changes.models import TestCase

        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)
        testcase = self.create_test(
            job=job,
            package='test.group.ClassName',
            name='test_foo',
            duration=43,
        )
        result = serialize(testcase, {TestCase: GeneralizedTestCase()})
        assert result['hash'] == testcase.name_sha
        assert result['project']['id'] == str(project.id.hex)
        assert result['shortName'] == testcase.short_name
        assert result['name'] == testcase.name
        assert result['package'] == testcase.package
        assert result['duration'] == testcase.duration

########NEW FILE########
__FILENAME__ = test_author_build_index
from uuid import uuid4

from changes.config import db
from changes.models import Author
from changes.testutils import APITestCase


class AuthorBuildListTest(APITestCase):
    def test_simple(self):
        fake_author_id = uuid4()

        self.create_build(self.project)

        path = '/api/0/authors/{0}/builds/'.format(fake_author_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404
        data = self.unserialize(resp)
        assert len(data) == 0

        author = Author(email=self.default_user.email, name='Foo Bar')
        db.session.add(author)
        build = self.create_build(self.project, author=author)

        path = '/api/0/authors/{0}/builds/'.format(author.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex

        path = '/api/0/authors/me/builds/'

        resp = self.client.get(path)
        assert resp.status_code == 401

        self.login(self.default_user)

        path = '/api/0/authors/me/builds/'

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex

########NEW FILE########
__FILENAME__ = test_auth_index
from changes.testutils import APITestCase


class AuthIndexTest(APITestCase):
    path = '/api/0/auth/'

    def test_anonymous(self):
        resp = self.client.get(self.path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['authenticated'] is False

    def test_authenticated(self):
        self.login_default()

        resp = self.client.get(self.path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['authenticated'] is True
        assert data['user'] == {
            'id': self.default_user.id.hex,
            'email': self.default_user.email,
        }

########NEW FILE########
__FILENAME__ = test_build_cancel
import mock

from changes.constants import Result, Status
from changes.models import Build, Step
from changes.testutils import APITestCase


class BuildCancelTest(APITestCase):
    @mock.patch.object(Step, 'get_implementation')
    def test_simple(self, get_implementation):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        build = self.create_build(
            project=self.project, status=Status.in_progress)
        job = self.create_job(build=build, status=Status.in_progress)
        plan = self.create_plan()
        self.create_step(plan)
        self.create_job_plan(job, plan)

        path = '/api/0/builds/{0}/cancel/'.format(build.id.hex)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert data['id'] == build.id.hex

        implementation.cancel.assert_called_once_with(job=job)

        build = Build.query.get(build.id)

        assert build.status == Status.finished
        assert build.result == Result.aborted

########NEW FILE########
__FILENAME__ = test_build_comment_index
from changes.config import db
from changes.models import Comment
from changes.testutils import APITestCase


class BuildCommentIndexTest(APITestCase):
    def test_get(self):
        build = self.create_build(project=self.project)

        comment = Comment(
            build=build,
            user=self.default_user,
            text='Hello world!',
        )
        db.session.add(comment)
        db.session.commit()

        path = '/api/0/builds/{0}/comments/'.format(build.id.hex)
        resp = self.client.get(path)

        assert resp.status_code == 200, resp.data

        data = self.unserialize(resp)

        assert len(data) == 1

        assert data[0]['id'] == comment.id.hex

    def test_post(self):
        self.login_default()

        build = self.create_build(project=self.project)

        path = '/api/0/builds/{0}/comments/'.format(build.id.hex)
        resp = self.client.post(path, data={
            'text': 'Hello world!',
        })

        assert resp.status_code == 200, resp.data

        data = self.unserialize(resp)

        assert data['id']

        comment = Comment.query.get(data['id'])

        assert comment.user == self.default_user
        assert comment.text == 'Hello world!'
        assert comment.build == build

########NEW FILE########
__FILENAME__ = test_build_coverage_stats
from datetime import datetime
from mock import patch

from changes.config import db
from changes.constants import Status
from changes.models import FileCoverage
from changes.testutils import APITestCase
from changes.testutils.fixtures import SAMPLE_DIFF


class BuildDetailsTest(APITestCase):
    @patch('changes.models.Source.generate_diff')
    def test_simple(self, generate_diff):
        build = self.create_build(
            self.project, date_created=datetime(2013, 9, 19, 22, 15, 24),
            status=Status.finished)
        job1 = self.create_job(build)
        job2 = self.create_job(build)

        db.session.add(FileCoverage(
            project_id=self.project.id,
            job_id=job1.id, filename='ci/run_with_retries.py', lines_covered=4,
            lines_uncovered=5, diff_lines_covered=2, diff_lines_uncovered=3,
        ))
        db.session.add(FileCoverage(
            project_id=self.project.id,
            job_id=job2.id, filename='foobar.py', lines_covered=4,
            lines_uncovered=5, diff_lines_covered=2, diff_lines_uncovered=3,
        ))
        db.session.commit()

        path = '/api/0/builds/{0}/stats/coverage/'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data['ci/run_with_retries.py'] == {
            'linesCovered': 4,
            'linesUncovered': 5,
            'diffLinesCovered': 2,
            'diffLinesUncovered': 3,
        }
        assert data['foobar.py'] == {
            'linesCovered': 4,
            'linesUncovered': 5,
            'diffLinesCovered': 2,
            'diffLinesUncovered': 3,
        }

        generate_diff.return_value = None

        resp = self.client.get(path + '?diff=1')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

        generate_diff.return_value = SAMPLE_DIFF

        resp = self.client.get(path + '?diff=1')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data['ci/run_with_retries.py'] == {
            'linesCovered': 4,
            'linesUncovered': 5,
            'diffLinesCovered': 2,
            'diffLinesUncovered': 3,
        }

########NEW FILE########
__FILENAME__ = test_build_details
from datetime import datetime

from changes.config import db
from changes.constants import Status
from changes.models import Event, TestCase
from changes.testutils import APITestCase, TestCase as BaseTestCase
from changes.api.build_details import find_changed_tests


class FindChangedTestsTest(BaseTestCase):
    def test_simple(self):
        previous_build = self.create_build(self.project)
        previous_job = self.create_job(previous_build)

        changed_test = TestCase(
            job=previous_job,
            project=previous_job.project,
            name='unchanged test',
        )
        removed_test = TestCase(
            job=previous_job,
            project=previous_job.project,
            name='removed test',
        )
        db.session.add(removed_test)
        db.session.add(changed_test)

        current_build = self.create_build(self.project)
        current_job = self.create_job(current_build)
        added_test = TestCase(
            job=current_job,
            project=current_job.project,
            name='added test',
        )

        db.session.add(added_test)
        db.session.add(TestCase(
            job=current_job,
            project=current_job.project,
            name='unchanged test',
        ))
        db.session.commit()

        results = find_changed_tests(current_build, previous_build)

        assert results['total'] == 2

        assert ('-', removed_test) in results['changes']
        assert ('+', added_test) in results['changes']

        assert len(results['changes']) == 2


class BuildDetailsTest(APITestCase):
    def test_simple(self):
        previous_build = self.create_build(
            self.project, date_created=datetime(2013, 9, 19, 22, 15, 23),
            status=Status.finished)
        build = self.create_build(
            self.project, date_created=datetime(2013, 9, 19, 22, 15, 24))
        job1 = self.create_job(build)
        job2 = self.create_job(build)
        db.session.add(Event(
            item_id=build.id,
            type='green_build_notification',
        ))
        db.session.commit()

        path = '/api/0/builds/{0}/'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == build.id.hex
        assert len(data['jobs']) == 2
        assert data['jobs'][0]['id'] == job1.id.hex
        assert data['jobs'][1]['id'] == job2.id.hex
        assert len(data['previousRuns']) == 1
        assert data['previousRuns'][0]['id'] == previous_build.id.hex
        assert data['seenBy'] == []
        assert data['testFailures']['total'] == 0
        assert data['testFailures']['tests'] == []
        assert data['testChanges'] == []
        assert len(data['events']) == 1

########NEW FILE########
__FILENAME__ = test_build_index
from cStringIO import StringIO

from changes.config import db
from changes.models import Job, JobPlan, ProjectOption
from changes.testutils import APITestCase, SAMPLE_DIFF


class BuildListTest(APITestCase):
    path = '/api/0/builds/'

    def test_simple(self):
        build = self.create_build(self.project)
        build2 = self.create_build(self.project2)

        resp = self.client.get(self.path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == build2.id.hex
        assert data[1]['id'] == build.id.hex


class BuildCreateTest(APITestCase):
    path = '/api/0/builds/'

    def test_minimal(self):
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build
        source = build.source

        assert job.project == self.project

        assert source.repository_id == self.project.repository_id
        assert source.revision_sha == 'a' * 40

    def test_defaults_to_revision(self):
        revision = self.create_revision(sha='a' * 40)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build
        source = build.source

        assert build.message == revision.message
        assert build.author == revision.author
        assert build.label == revision.subject

        assert job.project == self.project

        assert source.repository_id == self.project.repository_id
        assert source.revision_sha == 'a' * 40

    def test_with_full_params(self):
        resp = self.client.post(self.path, data={
            'project': self.project.slug,
            'sha': 'a' * 40,
            'target': 'D1234',
            'label': 'Foo Bar',
            'message': 'Hello world!',
            'author': 'David Cramer <dcramer@example.com>',
            'patch': (StringIO(SAMPLE_DIFF), 'foo.diff'),
            'patch[data]': '{"foo": "bar"}',
        })
        assert resp.status_code == 200, resp.data

        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build
        source = build.source

        assert build.author.name == 'David Cramer'
        assert build.author.email == 'dcramer@example.com'
        assert build.message == 'Hello world!'
        assert build.label == 'Foo Bar'
        assert build.target == 'D1234'

        assert job.project == self.project
        assert job.label == self.plan.label

        assert source.repository_id == self.project.repository_id
        assert source.revision_sha == 'a' * 40
        assert source.data == {'foo': 'bar'}

        patch = source.patch
        assert patch.diff == SAMPLE_DIFF
        assert patch.parent_revision_sha == 'a' * 40

        jobplans = list(JobPlan.query.filter(
            JobPlan.build_id == build.id,
        ))

        assert len(jobplans) == 1

        assert jobplans[0].plan_id == self.plan.id
        assert jobplans[0].project_id == self.project.id

    def test_with_repository(self):
        plan = self.create_plan()
        repo = self.create_repo()

        project1 = self.create_project(repository=repo)
        project2 = self.create_project(repository=repo)
        plan.projects.append(project1)
        plan.projects.append(project2)
        db.session.commit()

        resp = self.client.post(self.path, data={
            'repository': repo.url,
            'sha': 'a' * 40,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2

    def test_with_patch_without_diffs_enabled(self):
        po = ProjectOption(
            project=self.project,
            name='build.allow-patches',
            value='0',
        )
        db.session.add(po)
        db.session.commit()

        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'patch': (StringIO(SAMPLE_DIFF), 'foo.diff'),
            'patch[label]': 'D1234',
        })
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 0

########NEW FILE########
__FILENAME__ = test_build_mark_seen
from changes.models import BuildSeen
from changes.testutils import APITestCase


class BuildMarkSeenTest(APITestCase):
    def test_simple(self):
        build = self.create_build(project=self.project)

        self.login_default()

        path = '/api/0/builds/{0}/mark_seen/'.format(build.id.hex)
        resp = self.client.post(path)

        assert resp.status_code == 200

        buildseen = BuildSeen.query.filter(
            BuildSeen.user_id == self.default_user.id,
            BuildSeen.build_id == build.id,
        ).first()

        assert buildseen

########NEW FILE########
__FILENAME__ = test_build_restart
import mock

from changes.config import db
from changes.constants import Result, Status
from changes.models import Build, Job, JobStep, ItemStat
from changes.testutils import APITestCase


class BuildRestartTest(APITestCase):
    @mock.patch('changes.api.build_restart.execute_build')
    def test_simple(self, execute_build):
        build = self.create_build(
            project=self.project, status=Status.in_progress)
        job = self.create_job(build=build)
        phase = self.create_jobphase(job=job)
        step = self.create_jobstep(phase=phase)

        db.session.add(ItemStat(item_id=build.id.hex, name='test', value=1))
        db.session.add(ItemStat(item_id=job.id.hex, name='test', value=1))
        db.session.add(ItemStat(item_id=step.id.hex, name='test', value=1))
        db.session.commit()

        path = '/api/0/builds/{0}/restart/'.format(build.id.hex)

        # build isnt finished
        resp = self.client.post(path, follow_redirects=True)
        assert resp.status_code == 400

        build.status = Status.finished
        db.session.add(build)

        resp = self.client.post(path, follow_redirects=True)
        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert data['id'] == build.id.hex

        execute_build.assert_called_once_with(build=build)

        build = Build.query.get(build.id)

        assert build.status == Status.queued
        assert build.result == Result.unknown
        assert build.date_finished is None
        assert build.duration is None

        assert not Job.query.filter(Job.id == job.id).first()
        assert not JobStep.query.filter(JobStep.id == step.id).first()
        assert not ItemStat.query.filter(ItemStat.item_id.in_([
            build.id, job.id, step.id
        ])).first()

########NEW FILE########
__FILENAME__ = test_build_retry
from changes.constants import Cause
from changes.models import Build, Job
from changes.testutils import APITestCase


class BuildRetryTest(APITestCase):
    def test_simple(self):
        build = self.create_build(project=self.project)
        job = self.create_job(build=build)

        path = '/api/0/builds/{0}/retry/'.format(build.id.hex)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert data['id']

        new_build = Build.query.get(data['id'])

        assert new_build.id != build.id
        assert new_build.project_id == self.project.id
        assert new_build.cause == Cause.retry
        assert new_build.author_id == build.author_id
        assert new_build.source_id == build.source_id
        assert new_build.label == build.label
        assert new_build.message == build.message
        assert new_build.target == build.target

        jobs = list(Job.query.filter(
            Job.build_id == new_build.id,
        ))

        assert len(jobs) == 1

        new_job = jobs[0]
        assert new_job.id != job.id

########NEW FILE########
__FILENAME__ = test_build_test_index
from uuid import uuid4

from changes.config import db
from changes.constants import Status
from changes.models import TestCase
from changes.testutils import APITestCase


class BuildTestIndexTest(APITestCase):
    def test_simple(self):
        fake_id = uuid4()

        build = self.create_build(self.project)
        job = self.create_job(build, status=Status.finished)

        test = TestCase(
            job=job,
            project=self.project,
            name='foo',
            name_sha='a' * 40,
        )
        db.session.add(test)

        path = '/api/0/builds/{0}/tests/'.format(fake_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        # test each sort option just to ensure it doesnt straight up fail
        path = '/api/0/builds/{0}/tests/?sort=duration'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == test.id.hex

        path = '/api/0/builds/{0}/tests/?sort=name'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == test.id.hex

        path = '/api/0/builds/{0}/tests/?sort=retries'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == test.id.hex

        path = '/api/0/builds/{0}/tests/?per_page='.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == test.id.hex

        path = '/api/0/builds/{0}/tests/?query=foo'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == test.id.hex

        path = '/api/0/builds/{0}/tests/?query=bar'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

########NEW FILE########
__FILENAME__ = test_change_details
from changes.testutils import APITestCase


class ChangeDetailsTest(APITestCase):
    def test_simple(self):
        change = self.create_change(self.project)

        path = '/api/0/changes/{0}/'.format(change.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == change.id.hex

########NEW FILE########
__FILENAME__ = test_change_index
from changes.models import Change
from changes.testutils import APITestCase


class ChangeListTest(APITestCase):
    def test_simple(self):
        change = self.create_change(self.project)
        change2 = self.create_change(self.project2)

        resp = self.client.get('/api/0/changes/')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == change2.id.hex
        assert data[1]['id'] == change.id.hex


class ChangeCreateTest(APITestCase):
    def test_simple(self):
        change = self.create_change(self.project)
        path = '/api/0/changes/'.format(change.id.hex)
        resp = self.client.post(path, data={
            'project': self.project.slug,
            'label': 'D1234',
            'author': 'David Cramer <dcramer@example.com>',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id']
        change = Change.query.get(data['id'])
        assert change.project == self.project
        assert change.label == 'D1234'
        assert change.author.name == 'David Cramer'
        assert change.author.email == 'dcramer@example.com'

########NEW FILE########
__FILENAME__ = test_client
from changes.api.client import api_client
from changes.testutils import TestCase


class APIClientTest(TestCase):
    def test_simple(self):
        # HACK: relies on existing endpoint
        result = api_client.get('/projects/')
        assert type(result) == list

########NEW FILE########
__FILENAME__ = test_cluster_details
from changes.testutils import APITestCase


class ClusterIndexTest(APITestCase):
    def test_simple(self):
        cluster_1 = self.create_cluster(label='bar')
        path = '/api/0/clusters/{0}/'.format(cluster_1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == cluster_1.id.hex

########NEW FILE########
__FILENAME__ = test_cluster_index
from changes.testutils import APITestCase


class ClusterIndexTest(APITestCase):
    def test_simple(self):
        cluster_1 = self.create_cluster(label='bar')
        cluster_2 = self.create_cluster(label='foo')
        path = '/api/0/clusters/'

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == cluster_1.id.hex
        assert data[1]['id'] == cluster_2.id.hex

########NEW FILE########
__FILENAME__ = test_cluster_nodes
from changes.testutils import APITestCase


class ClusterNodesTest(APITestCase):
    def test_simple(self):
        cluster_1 = self.create_cluster(label='bar')
        node_1 = self.create_node(cluster=cluster_1, label='foo')
        node_2 = self.create_node(cluster=cluster_1, label='test')

        path = '/api/0/clusters/{0}/nodes/'.format(cluster_1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == node_1.id.hex
        assert data[1]['id'] == node_2.id.hex

########NEW FILE########
__FILENAME__ = test_jobphase_index
from datetime import datetime
from uuid import uuid4

from changes.config import db
from changes.constants import Result, Status
from changes.models import JobPhase, JobStep, LogSource
from changes.testutils import APITestCase


class JobPhaseIndexTest(APITestCase):
    def test_invalid_job_id(self):
        path = '/api/0/jobs/{0}/phases/'.format(uuid4().hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

    def test_simple(self):
        project = self.project
        build = self.create_build(project)
        job = self.create_job(build)

        phase_1 = JobPhase(
            job_id=job.id,
            project_id=job.project_id,
            label='Setup',
            status=Status.finished,
            result=Result.passed,
            date_created=datetime(2013, 9, 19, 22, 15, 22),
            date_started=datetime(2013, 9, 19, 22, 15, 23),
            date_finished=datetime(2013, 9, 19, 22, 15, 25),
        )
        db.session.add(phase_1)

        step_1 = JobStep(
            job_id=job.id,
            phase_id=phase_1.id,
            project_id=job.project_id,
            label='ci/setup',
            status=Status.finished,
            result=Result.passed,
            date_created=datetime(2013, 9, 19, 22, 15, 22),
            date_started=datetime(2013, 9, 19, 22, 15, 23),
            date_finished=datetime(2013, 9, 19, 22, 15, 25),
        )
        db.session.add(step_1)

        phase_2 = JobPhase(
            job_id=job.id,
            project_id=job.project_id,
            label='Test',
            status=Status.finished,
            result=Result.failed,
            date_created=datetime(2013, 9, 19, 22, 15, 23),
            date_started=datetime(2013, 9, 19, 22, 15, 24),
            date_finished=datetime(2013, 9, 19, 22, 15, 26),
        )
        db.session.add(phase_2)

        step_2_a = JobStep(
            job_id=job.id,
            phase_id=phase_2.id,
            project_id=job.project_id,
            label='test_foo.py',
            status=Status.finished,
            result=Result.passed,
            date_created=datetime(2013, 9, 19, 22, 15, 23),
            date_started=datetime(2013, 9, 19, 22, 15, 23),
            date_finished=datetime(2013, 9, 19, 22, 15, 25),
        )
        db.session.add(step_2_a)

        step_2_b = JobStep(
            job_id=job.id,
            phase_id=phase_2.id,
            project_id=job.project_id,
            label='test_bar.py',
            status=Status.finished,
            result=Result.failed,
            date_created=datetime(2013, 9, 19, 22, 15, 24),
            date_started=datetime(2013, 9, 19, 22, 15, 24),
            date_finished=datetime(2013, 9, 19, 22, 15, 26),
        )
        db.session.add(step_2_b)
        db.session.commit()

        logsource_1 = LogSource(
            job_id=job.id,
            step_id=step_1.id,
            project_id=job.project_id,
            name='test_bar.py',
            date_created=datetime(2013, 9, 19, 22, 15, 24),
        )
        db.session.add(logsource_1)
        db.session.commit()

        path = '/api/0/jobs/{0}/phases/'.format(job.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == phase_1.id.hex
        assert len(data[0]['steps']) == 1
        assert data[0]['steps'][0]['id'] == step_1.id.hex
        assert len(data[0]['steps'][0]['logSources']) == 1
        assert data[0]['steps'][0]['logSources'][0]['id'] == logsource_1.id.hex
        assert data[1]['id'] == phase_2.id.hex
        assert len(data[1]['steps']) == 2
        assert data[1]['steps'][0]['id'] == step_2_a.id.hex
        assert len(data[1]['steps'][0]['logSources']) == 0
        assert data[1]['steps'][1]['id'] == step_2_b.id.hex
        assert len(data[1]['steps'][1]['logSources']) == 0

########NEW FILE########
__FILENAME__ = test_job_details
from changes.config import db
from changes.models import LogSource
from changes.testutils import APITestCase


class JobDetailsTest(APITestCase):
    def test_simple(self):
        build = self.create_build(self.project)
        job = self.create_job(build)

        ls1 = LogSource(job=job, project=self.project, name='test')
        db.session.add(ls1)
        ls2 = LogSource(job=job, project=self.project, name='test2')
        db.session.add(ls2)
        db.session.commit()

        path = '/api/0/jobs/{0}/'.format(job.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == job.id.hex
        assert len(data['logs']) == 2
        assert data['logs'][0]['id'] == ls1.id.hex
        assert data['logs'][1]['id'] == ls2.id.hex

########NEW FILE########
__FILENAME__ = test_job_log_details
from changes.config import db
from changes.models import LogSource, LogChunk
from changes.testutils import APITestCase


class JobLogDetailsTest(APITestCase):
    def test_simple(self):
        build = self.create_build(self.project)
        job = self.create_job(build)
        source = LogSource(job=job, project=self.project, name='test')
        db.session.add(source)

        lc1 = LogChunk(
            job=job, project=self.project, source=source,
            offset=0, size=100, text='a' * 100,
        )
        db.session.add(lc1)
        lc2 = LogChunk(
            job=job, project=self.project, source=source,
            offset=100, size=100, text='b' * 100,
        )
        db.session.add(lc2)
        db.session.commit()

        path = '/api/0/jobs/{0}/logs/{1}/'.format(
            job.id.hex, source.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['source']['id'] == source.id.hex
        assert data['nextOffset'] == 200
        assert len(data['chunks']) == 2
        assert data['chunks'][0]['text'] == lc1.text
        assert data['chunks'][1]['text'] == lc2.text

########NEW FILE########
__FILENAME__ = test_node_details
from changes.testutils import APITestCase


class NodeDetailsTest(APITestCase):
    def test_simple(self):
        node = self.create_node()
        path = '/api/0/nodes/{0}/'.format(node.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == node.id.hex

########NEW FILE########
__FILENAME__ = test_node_index
from changes.testutils import APITestCase


class NodeIndexTest(APITestCase):
    def test_simple(self):
        node_1 = self.create_node(label='bar')
        node_2 = self.create_node(label='foo')
        path = '/api/0/nodes/'

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == node_1.id.hex
        assert data[1]['id'] == node_2.id.hex

########NEW FILE########
__FILENAME__ = test_node_job_index
from changes.config import db
from changes.models import JobStep, JobPhase
from changes.testutils import APITestCase


class NodeJobIndexTest(APITestCase):
    def test_simple(self):
        node = self.create_node()
        build = self.create_build(self.project)
        job = self.create_job(build)
        phase = JobPhase(
            job=job,
            project=self.project,
            label='test',
        )
        db.session.add(phase)
        jobstep = JobStep(
            job=job,
            project=self.project,
            phase=phase,
            node=node,
            label='test',
        )
        db.session.add(jobstep)
        db.session.commit()

        path = '/api/0/nodes/{0}/jobs/'.format(node.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == job.id.hex

########NEW FILE########
__FILENAME__ = test_patch_details
from changes.testutils import APITestCase


class PatchDetailsTest(APITestCase):
    def test_simple(self):
        patch = self.create_patch(self.project)

        path = '/api/0/patches/{0}/'.format(patch.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == patch.id.hex

    def test_raw(self):
        patch = self.create_patch(self.project)

        path = '/api/0/patches/{0}/?raw=1'.format(patch.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        assert resp.data == patch.diff

########NEW FILE########
__FILENAME__ = test_plan_details
from changes.testutils import APITestCase


class PlanDetailsTest(APITestCase):
    def test_simple(self):
        project1 = self.create_project()
        project2 = self.create_project()

        plan1 = self.create_plan(label='Foo')
        plan1.projects.append(project1)
        plan1.projects.append(project2)

        path = '/api/0/plans/{0}/'.format(plan1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == plan1.id.hex
        assert len(data['projects']) == 2
        assert data['projects'][0]['id'] == project1.id.hex
        assert data['projects'][1]['id'] == project2.id.hex

########NEW FILE########
__FILENAME__ = test_plan_index
from changes.testutils import APITestCase


class PlanIndexTest(APITestCase):
    path = '/api/0/plans/'

    def test_simple(self):
        plan1 = self.plan
        plan2 = self.create_plan(label='Bar')

        resp = self.client.get(self.path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == plan2.id.hex
        assert data[1]['id'] == plan1.id.hex


class CreatePlanTest(APITestCase):
    path = '/api/0/plans/'

    def requires_auth(self):
        resp = self.client.post(self.path, data={
            'name': 'Bar',
        })
        assert resp.status_code == 401

    def test_simple(self):
        self.login_default_admin()

        resp = self.client.post(self.path, data={
            'name': 'Bar',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['name'] == 'Bar'

########NEW FILE########
__FILENAME__ = test_plan_project_index
from changes.testutils import APITestCase


class PlanProjectIndexTest(APITestCase):
    def test_simple(self):
        project1 = self.create_project()
        project2 = self.create_project()

        plan1 = self.create_plan(label='Foo')
        plan1.projects.append(project1)
        plan1.projects.append(project2)

        path = '/api/0/plans/{0}/projects/'.format(plan1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2


class CreatePlanProjectTest(APITestCase):
    def requires_auth(self):
        plan = self.create_plan(label='Foo')

        path = '/api/0/plans/{0}/projects/'.format(plan.id.hex)

        resp = self.client.post(path)
        assert resp.status_code == 401

    def test_simple(self):
        project1 = self.create_project()

        plan1 = self.create_plan(label='Foo')

        self.login_default_admin()

        path = '/api/0/plans/{0}/projects/'.format(plan1.id.hex)

        resp = self.client.post(path, data={
            'id': project1.id,
        })
        assert resp.status_code == 200

########NEW FILE########
__FILENAME__ = test_plan_step_index
from changes.testutils import APITestCase


class PlanStepIndexTest(APITestCase):
    def test_simple(self):
        project1 = self.create_project()
        project2 = self.create_project()

        plan1 = self.create_plan(label='Foo')
        plan1.projects.append(project1)
        plan1.projects.append(project2)
        step1 = self.create_step(plan=plan1)

        path = '/api/0/plans/{0}/steps/'.format(plan1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == step1.id.hex


class CreatePlanStepTest(APITestCase):
    def requires_auth(self):
        plan = self.create_plan(label='Foo')

        path = '/api/0/plans/{0}/steps/'.format(plan.id.hex)

        resp = self.client.post(path)
        assert resp.status_code == 401

    def test_simple(self):
        project1 = self.create_project()
        project2 = self.create_project()

        plan1 = self.create_plan(label='Foo')
        plan1.projects.append(project1)
        plan1.projects.append(project2)

        self.login_default_admin()

        path = '/api/0/plans/{0}/steps/'.format(plan1.id.hex)

        resp = self.client.post(path, data={
            'implementation': 'changes.buildsteps.dummy.DummyBuildStep'
        })
        assert resp.status_code == 201, resp.data
        data = self.unserialize(resp)
        assert data['implementation'] == 'changes.buildsteps.dummy.DummyBuildStep'

########NEW FILE########
__FILENAME__ = test_project_build_index
from uuid import uuid4

from changes.testutils import APITestCase


class ProjectBuildListTest(APITestCase):
    def test_simple(self):
        fake_project_id = uuid4()

        self.create_build(self.project)

        project = self.create_project()
        build = self.create_build(project)

        path = '/api/0/projects/{0}/builds/'.format(fake_project_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/builds/'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex

    def test_include_patches(self):
        project = self.project
        patch = self.create_patch(project)
        source = self.create_source(project, patch=patch)
        build = self.create_build(project)
        self.create_build(project, source=source)

        # ensure include_patches correctly references Source.patch
        path = '/api/0/projects/{0}/builds/?include_patches=0'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex

########NEW FILE########
__FILENAME__ = test_project_build_search
from uuid import uuid4

from changes.constants import Result
from changes.testutils import APITestCase


class ProjectBuildSearchTest(APITestCase):
    def test_simple(self):
        fake_project_id = uuid4()

        self.create_build(self.project)

        project1 = self.create_project()
        build1 = self.create_build(project1, label='test', target='D1234',
                                   result=Result.passed)
        project2 = self.create_project()
        build2 = self.create_build(project2, label='test', target='D1234',
                                   result=Result.failed)

        path = '/api/0/projects/{0}/builds/search/?source=D1234'.format(fake_project_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/builds/search/'.format(project1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build1.id.hex

        path = '/api/0/projects/{0}/builds/search/?source=D1234'.format(project1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build1.id.hex

        path = '/api/0/projects/{0}/builds/search/?query=D1234'.format(project1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build1.id.hex

        path = '/api/0/projects/{0}/builds/search/?query=test'.format(project1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build1.id.hex

        path = '/api/0/projects/{0}/builds/search/?query=something_impossible'.format(project1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

        path = '/api/0/projects/{0}/builds/search/?result=passed'.format(project1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build1.id.hex

        path = '/api/0/projects/{0}/builds/search/?result=failed'.format(project2.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build2.id.hex

        path = '/api/0/projects/{0}/builds/search/?result=aborted'.format(project1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

########NEW FILE########
__FILENAME__ = test_project_commit_details
from uuid import uuid4

from changes.testutils import APITestCase


class ProjectCommitDetailsTest(APITestCase):
    def test_simple(self):
        fake_commit_id = uuid4()

        build = self.create_build(self.project)
        self.create_job(build)

        project = self.create_project()
        revision = self.create_revision(repository=project.repository)
        source = self.create_source(project, revision_sha=revision.sha)
        build = self.create_build(project, source=source)

        path = '/api/0/projects/{0}/commits/{1}/'.format(
            self.project.id.hex, fake_commit_id)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/commits/{1}/'.format(
            project.id.hex, revision.sha)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == revision.sha
        assert len(data['builds']) == 1
        assert data['builds'][0]['id'] == build.id.hex

########NEW FILE########
__FILENAME__ = test_project_commit_index
import mock

from datetime import datetime
from uuid import uuid4

from changes.constants import Status
from changes.testutils import APITestCase
from changes.vcs.base import Vcs, RevisionResult


class ProjectCommitIndexTest(APITestCase):
    def test_simple(self):
        fake_project_id = uuid4()

        project = self.create_project()
        revision1 = self.create_revision(repository=project.repository)
        revision2 = self.create_revision(
            repository=project.repository, parents=[revision1.sha])

        source = self.create_source(project, revision_sha=revision1.sha)
        build = self.create_build(project, source=source, status=Status.finished)

        path = '/api/0/projects/{0}/commits/'.format(fake_project_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/commits/'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == revision2.sha
        assert data[0]['build'] is None
        assert data[1]['id'] == revision1.sha
        assert data[1]['build']['id'] == build.id.hex

    @mock.patch('changes.models.Repository.get_vcs')
    def test_with_vcs(self, get_vcs):
        def log_results():
            yield RevisionResult(
                id='a' * 40,
                message='hello world',
                author='Foo <foo@example.com>',
                author_date=datetime(2013, 9, 19, 22, 15, 22),
            )
            yield RevisionResult(
                id='b' * 40,
                message='biz',
                author='Bar <bar@example.com>',
                author_date=datetime(2013, 9, 19, 22, 15, 21),
            )

        fake_vcs = mock.Mock(spec=Vcs)
        fake_vcs.log.return_value = log_results()

        get_vcs.return_value = fake_vcs

        project = self.create_project()

        source = self.create_source(project, revision_sha='b' * 40)
        build = self.create_build(project, source=source, status=Status.finished)

        path = '/api/0/projects/{0}/commits/'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == 'a' * 40
        assert data[0]['build'] is None
        assert data[1]['id'] == 'b' * 40
        assert data[1]['build']['id'] == build.id.hex

########NEW FILE########
__FILENAME__ = test_project_details
from changes.models import Project
from changes.testutils import APITestCase


class ProjectDetailsTest(APITestCase):
    def test_retrieve(self):
        path = '/api/0/projects/{0}/'.format(
            self.project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == self.project.id.hex

    def test_retrieve_by_slug(self):
        path = '/api/0/projects/{0}/'.format(
            self.project.slug)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == self.project.id.hex

    def test_update(self):
        path = '/api/0/projects/{0}/'.format(
            self.project.id.hex)

        resp = self.client.post(path, data={
            'name': 'details test project',
            'slug': 'details-test-project',
        })
        assert resp.status_code == 200

        project = Project.query.get(self.project.id)
        assert project.name == 'details test project'
        assert project.slug == 'details-test-project'

    def test_update_by_slug(self):
        path = '/api/0/projects/{0}/'.format(
            self.project.slug)

        resp = self.client.post(path, data={
            'name': 'details test project',
            'slug': 'details-test-project',
        })
        assert resp.status_code == 200
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == self.project.id.hex

        project = Project.query.get(self.project.id)
        assert project.name == 'details test project'
        assert project.slug == 'details-test-project'

########NEW FILE########
__FILENAME__ = test_project_index
from changes.constants import Result, Status
from changes.models import Project
from changes.testutils import APITestCase


class ProjectListTest(APITestCase):
    def test_simple(self):
        project_1 = self.project
        project_2 = self.project2
        project_3 = self.create_project(name='zzz')

        build_1 = self.create_build(
            project_1, status=Status.finished, result=Result.passed)
        build_2 = self.create_build(
            project_2, status=Status.finished, result=Result.failed)

        path = '/api/0/projects/'

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 3
        assert data[0]['id'] == project_1.id.hex
        assert data[0]['lastBuild']['id'] == build_1.id.hex
        assert data[0]['lastPassingBuild']['id'] == build_1.id.hex
        assert data[1]['id'] == project_2.id.hex
        assert data[1]['lastBuild']['id'] == build_2.id.hex
        assert data[1]['lastPassingBuild'] is None
        assert data[2]['id'] == project_3.id.hex
        assert data[2]['lastBuild'] is None
        assert data[2]['lastPassingBuild'] is None


class ProjectCreateTest(APITestCase):
    def test_simple(self):
        path = '/api/0/projects/'

        # without auth
        resp = self.client.post(path, data={
            'name': 'Foobar',
            'repository': 'ssh://example.com/foo',
        })
        assert resp.status_code == 401

        self.login_default()

        resp = self.client.post(path, data={
            'name': 'Foobar',
            'repository': 'ssh://example.com/foo',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id']
        assert data['slug'] == 'foobar'

        assert Project.query.filter(
            Project.name == 'Foobar',
        ).first()

########NEW FILE########
__FILENAME__ = test_project_options_index
from changes.config import db
from changes.models import ProjectOption
from changes.testutils import APITestCase


class BuildListTest(APITestCase):
    def test_simple(self):
        path = '/api/0/projects/{0}/options/'.format(self.project.slug)

        resp = self.client.post(path, data={
            'mail.notify-author': '0',
            'build.allow-patches': '1',
            'build.expect-tests': '1',
        })
        assert resp.status_code == 401

        self.login_default()

        resp = self.client.post(path, data={
            'mail.notify-author': '0',
            'build.allow-patches': '1',
            'build.expect-tests': '1',
        })
        assert resp.status_code == 200

        options = dict(db.session.query(
            ProjectOption.name, ProjectOption.value
        ).filter(
            ProjectOption.project == self.project,
        ))

        assert options.get('mail.notify-author') == '0'
        assert options.get('build.allow-patches') == '1'
        assert options.get('build.expect-tests') == '1'

########NEW FILE########
__FILENAME__ = test_project_source_build_index
from changes.testutils import APITestCase


class ProjectSourceBuildIndexTest(APITestCase):
    def test_simple(self):
        source = self.create_source(self.project)
        build1 = self.create_build(self.project, source=source)
        build2 = self.create_build(self.project, source=source)
        path = '/api/0/projects/{0}/sources/{1}/builds/'.format(
            self.project.id.hex, source.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == build2.id.hex
        assert data[1]['id'] == build1.id.hex

########NEW FILE########
__FILENAME__ = test_project_source_details
from changes.testutils import APITestCase
from changes.api.project_source_details import ProjectSourceDetailsAPIView


class ProjectSourceDetailsTest(APITestCase):
    def test_simple(self):
        source = self.create_source(self.project)

        path = '/api/0/projects/{0}/sources/{1}/'.format(
            self.project.id.hex, source.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == source.id.hex

    def test_filter_coverage_for_added_lines(self):
        view = ProjectSourceDetailsAPIView()
        diff = open('sample.diff').read()
        coverage = ['N'] * 150
        coverage[52] = 'C'
        coverage[53] = 'C'
        coverage[54] = 'C'
        coverage_dict = {'ci/run_with_retries.py': coverage}
        result = view._filter_coverage_for_added_lines(diff, coverage_dict)
        assert len(result) == 23  # 23 additions
        assert result == ['N', 'N', 'C', 'C', 'C', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N']

########NEW FILE########
__FILENAME__ = test_project_stats
import itertools

from datetime import datetime, timedelta
from exam import fixture

from changes.config import db
from changes.models import ItemStat
from changes.testutils import APITestCase


def to_timestamp(dt):
    return int(float(dt.strftime('%s.%f')) * 1000)


class ProjectDetailsTest(APITestCase):
    @fixture
    def path(self):
        return '/api/0/projects/{0}/stats/'.format(self.project.id.hex)

    def test_simple(self):
        now = datetime(2014, 4, 21, 22, 15, 22)

        build1 = self.create_build(
            project=self.project,
            date_created=now,
        )
        build2 = self.create_build(
            project=self.project,
            date_created=now - timedelta(hours=1),
        )
        build3 = self.create_build(
            project=self.project,
            date_created=now - timedelta(days=1),
        )
        build4 = self.create_build(
            project=self.project,
            date_created=now.replace(day=1) - timedelta(days=32),
        )
        build5 = self.create_build(
            project=self.project,
            date_created=now.replace(day=1) - timedelta(days=370),
        )

        db.session.add(ItemStat(name='test_count', value=1, item_id=build1.id))
        db.session.add(ItemStat(name='test_count', value=3, item_id=build2.id))
        db.session.add(ItemStat(name='test_count', value=6, item_id=build3.id))
        db.session.add(ItemStat(name='test_count', value=20, item_id=build4.id))
        db.session.add(ItemStat(name='test_count', value=100, item_id=build5.id))
        db.session.commit()

        base_path = self.path + '?from=' + now.strftime('%s') + '&'

        # test hourly
        resp = self.client.get(base_path + 'stat=test_count&resolution=1h')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 24
        assert data[0]['time'] == to_timestamp(datetime(2014, 4, 20, 22, 0))
        assert data[0]['value'] == 6
        for point in data[1:-1]:
            assert point['value'] == 0
        assert data[-1]['time'] == to_timestamp(datetime(2014, 4, 21, 21, 0))
        assert data[-1]['value'] == 3

        # test weekly
        resp = self.client.get(base_path + 'stat=test_count&resolution=1w')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 26
        for point in itertools.chain(data[:-8], data[-7:-1]):
            assert point['value'] == 0
        assert data[-8]['time'] == to_timestamp(datetime(2014, 2, 24, 0, 0))
        assert data[-8]['value'] == 20
        assert data[-1]['time'] == to_timestamp(datetime(2014, 4, 14, 0, 0))
        assert data[-1]['value'] == 6

        # test daily
        resp = self.client.get(base_path + 'stat=test_count&resolution=1d')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 30
        for point in data[:-1]:
            assert point['value'] == 0
        assert data[-1]['time'] == to_timestamp(datetime(2014, 4, 20, 0, 0))
        assert data[-1]['value'] == 6

        # test monthly
        resp = self.client.get(base_path + 'stat=test_count&resolution=1m')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 12
        for point in itertools.chain(data[:-2], data[-1:]):
            assert point['value'] == 0
        assert data[-2]['time'] == to_timestamp(datetime(2014, 2, 1, 0, 0))
        assert data[-2]['value'] == 20

########NEW FILE########
__FILENAME__ = test_project_test_details
from uuid import uuid4

from changes.constants import Result, Status
from changes.testutils import APITestCase


class ProjectTestDetailsTest(APITestCase):
    def test_simple(self):
        fake_id = uuid4()

        project = self.create_project()

        previous_build = self.create_build(
            project=project,
            status=Status.finished,
            result=Result.passed,
        )
        previous_job = self.create_job(previous_build)

        build = self.create_build(
            project=project,
            status=Status.finished,
            result=Result.passed,
        )
        job = self.create_job(build)

        previous_parent_group = self.create_test(
            job=previous_job,
            name='foo',
        )

        parent_group = self.create_test(
            job=job,
            name='foo',
        )

        # invalid project id
        path = '/api/0/projects/{0}/tests/{1}/'.format(
            fake_id.hex, parent_group.name_sha)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/tests/{1}/'.format(
            project.id.hex, fake_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/tests/{1}/'.format(
            project.id.hex, parent_group.name_sha)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        # simple test for the composite primary key
        assert data['hash'] == parent_group.name_sha
        assert data['project']['id'] == parent_group.project.id.hex
        assert len(data['results']) == 2
        assert data['results'][1]['id'] == previous_parent_group.id.hex
        assert data['results'][0]['id'] == parent_group.id.hex

########NEW FILE########
__FILENAME__ = test_project_test_group_index
from uuid import uuid4

from changes.constants import Result, Status
from changes.testutils import APITestCase


class ProjectTestIndexTest(APITestCase):
    def test_simple(self):
        fake_project_id = uuid4()

        build = self.create_build(self.project)
        self.create_job(build)

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(
            build, status=Status.finished, result=Result.passed)

        self.create_test(job=job, name='foo.bar', duration=50)
        self.create_test(job=job, name='foo.baz', duration=70)
        self.create_test(job=job, name='blah.blah', duration=10)

        path = '/api/0/projects/{0}/testgroups/'.format(fake_project_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/testgroups/'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['groups']) == 2
        assert data['groups'][0]['name'] == 'foo'
        assert data['groups'][0]['path'] == 'foo'
        assert data['groups'][0]['numTests'] == 2
        assert data['groups'][0]['totalDuration'] == 120
        assert data['groups'][1]['name'] == 'blah.blah'
        assert data['groups'][1]['path'] == 'blah.blah'
        assert data['groups'][1]['numTests'] == 1
        assert data['groups'][1]['totalDuration'] == 10
        assert len(data['trail']) == 0

        path = '/api/0/projects/{0}/testgroups/?parent=foo'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['groups']) == 2
        assert data['groups'][0]['name'] == 'baz'
        assert data['groups'][0]['path'] == 'foo.baz'
        assert data['groups'][0]['numTests'] == 1
        assert data['groups'][0]['totalDuration'] == 70
        assert data['groups'][1]['name'] == 'bar'
        assert data['groups'][1]['path'] == 'foo.bar'
        assert data['groups'][1]['numTests'] == 1
        assert data['groups'][1]['totalDuration'] == 50
        assert len(data['trail']) == 1
        assert data['trail'][0] == {
            'name': 'foo',
            'path': 'foo',
        }

########NEW FILE########
__FILENAME__ = test_project_test_index
from uuid import uuid4

from changes.constants import Result, Status
from changes.testutils import APITestCase


class ProjectTestIndexTest(APITestCase):
    def test_simple(self):
        fake_project_id = uuid4()

        build = self.create_build(self.project)
        self.create_job(build)

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(
            build, status=Status.finished, result=Result.passed)
        test = self.create_test(job=job, name='foobar', duration=50)

        path = '/api/0/projects/{0}/tests/'.format(fake_project_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/tests/?sort=duration'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['hash'] == test.name_sha
        assert data[0]['project']['id'] == project.id.hex

        path = '/api/0/projects/{0}/tests/?sort=name'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['hash'] == test.name_sha
        assert data[0]['project']['id'] == project.id.hex

        path = '/api/0/projects/{0}/tests/?query=foobar'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['hash'] == test.name_sha
        assert data[0]['project']['id'] == project.id.hex

        path = '/api/0/projects/{0}/tests/?query=hello'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

        # test duration
        path = '/api/0/projects/{0}/tests/?min_duration=50'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['hash'] == test.name_sha
        assert data[0]['project']['id'] == project.id.hex

        path = '/api/0/projects/{0}/tests/?min_duration=51'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

########NEW FILE########
__FILENAME__ = test_step_details
from changes.config import db
from changes.models import Step
from changes.testutils import APITestCase


class StepDetailsTest(APITestCase):
    def test_simple(self):
        plan = self.create_plan(label='Foo')
        step = self.create_step(plan=plan)

        path = '/api/0/steps/{0}/'.format(step.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == step.id.hex


class UpdateStepDetailsTest(APITestCase):
    def requires_auth(self):
        plan = self.create_plan(label='Foo')
        step = self.create_step(plan=plan)

        path = '/api/0/steps/{0}/'.format(step.id.hex)

        resp = self.client.post(path)
        assert resp.status_code == 401

    def test_simple(self):
        self.login_default_admin()

        plan = self.create_plan(label='Foo')
        step = self.create_step(plan=plan)

        self.login_default_admin()

        path = '/api/0/steps/{0}/'.format(step.id.hex)

        resp = self.client.post(path, data={
            'order': 1,
            'implementation': 'changes.buildsteps.dummy.DummyBuildStep',
            'data': '{}',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['data'] == '{}'
        assert data['order'] == 1
        assert data['implementation'] == 'changes.buildsteps.dummy.DummyBuildStep'

        db.session.expire(step)

        step = Step.query.get(step.id)
        assert step.data == {}
        assert step.order == 1
        assert step.implementation == 'changes.buildsteps.dummy.DummyBuildStep'


class DeleteStepDetailsTest(APITestCase):
    def requires_auth(self):
        plan = self.create_plan(label='Foo')
        step = self.create_step(plan=plan)

        path = '/api/0/steps/{0}/'.format(step.id.hex)

        resp = self.client.delete(path)
        assert resp.status_code == 401

    def test_simple(self):
        self.login_default()

        plan = self.create_plan(label='Foo')
        step = self.create_step(plan=plan)

        self.login_default_admin()

        path = '/api/0/steps/{0}/'.format(step.id.hex)

        step_id = step.id

        resp = self.client.delete(path)
        assert resp.status_code == 200

        db.session.expire_all()

        step = Step.query.get(step_id)
        assert step is None

########NEW FILE########
__FILENAME__ = test_task_details
from __future__ import absolute_import

from uuid import uuid4

from changes.testutils import APITestCase


class TaskDetailsTest(APITestCase):
    def test_simple(self):
        task = self.create_task(
            task_name='example',
            task_id=uuid4(),
        )
        child_1 = self.create_task(
            task_name='example',
            task_id=uuid4(),
            parent_id=task.task_id,
        )
        child_1_1 = self.create_task(
            task_name='example',
            task_id=uuid4(),
            parent_id=child_1.task_id,
        )
        child_2 = self.create_task(
            task_name='example',
            task_id=uuid4(),
            parent_id=task.task_id,
        )

        path = '/api/0/tasks/{0}/'.format(task.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == task.id.hex
        assert len(data['children']) == 2

########NEW FILE########
__FILENAME__ = test_task_index
from datetime import datetime

from changes.testutils import APITestCase


class TaskIndexTest(APITestCase):
    def test_simple(self):
        task_1 = self.create_task(
            task_name='example',
            date_created=datetime(2013, 9, 19, 22, 15, 24),
        )
        task_2 = self.create_task(
            task_name='example',
            date_created=datetime(2013, 9, 20, 22, 15, 24),
        )

        path = '/api/0/tasks/'

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == task_2.id.hex
        assert data[1]['id'] == task_1.id.hex

########NEW FILE########
__FILENAME__ = test_testcase_details
from changes.testutils import APITestCase


class TestCaseDetailsTest(APITestCase):
    def test_simple(self):
        build = self.create_build(project=self.project)
        job = self.create_job(build=build)

        testcase = self.create_test(job=job)

        path = '/api/0/tests/{0}/'.format(
            testcase.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == testcase.id.hex

########NEW FILE########
__FILENAME__ = test_collector
from __future__ import absolute_import

import mock
import responses

from changes.backends.jenkins.generic_builder import JenkinsGenericBuilder
from changes.backends.jenkins.buildsteps.collector import JenkinsCollectorBuildStep
from changes.constants import Status
from changes.models import JobPhase, JobStep
from changes.testutils import TestCase


class JenkinsCollectorBuildStepTest(TestCase):
    def get_buildstep(self):
        return JenkinsCollectorBuildStep(
            job_name='foo-bar',
            script='exit 0',
            cluster='default',
        )

    def get_mock_builder(self):
        return mock.Mock(spec=JenkinsGenericBuilder)

    def test_get_builder(self):
        builder = self.get_buildstep().get_builder()
        assert builder.job_name == 'foo-bar'
        assert builder.script == 'exit 0'

    @mock.patch.object(JenkinsCollectorBuildStep, 'get_builder')
    def test_default_artifact_handling(self, get_builder):
        builder = self.get_mock_builder()
        get_builder.return_value = builder

        build = self.create_build(self.project)
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })
        artifact = {'fileName': 'junit.xml'}

        buildstep = self.get_buildstep()
        buildstep.fetch_artifact(step, artifact)

        builder.sync_artifact.assert_called_once_with(step, artifact)

    @responses.activate
    @mock.patch.object(JenkinsCollectorBuildStep, 'get_builder')
    def test_job_expansion(self, get_builder):
        """
        Fairly heavy integration test which mocks out a few things but ensures
        that generic APIs are called correctly and the jobs.json is parsed
        as expected.
        """
        builder = self.get_mock_builder()
        builder.fetch_artifact.return_value.json.return_value = {
            'phase': 'Run',
            'jobs': [
                {'name': 'Optional name',
                 'cmd': 'echo 1'},
                {'cmd': 'py.test --junit=junit.xml'},
            ],
        }
        builder.create_job_from_params.return_value = {
            'job_name': 'foo-bar',
            'build_no': 23,
        }

        get_builder.return_value = builder

        build = self.create_build(self.project)
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })
        artifact = {
            'fileName': 'jobs.json',
        }

        buildstep = self.get_buildstep()
        buildstep.fetch_artifact(step, artifact)

        phase2 = JobPhase.query.filter(
            JobPhase.job_id == job.id,
            JobPhase.id != phase.id,
        ).first()

        assert phase2, 'phase wasnt created'
        assert phase2.label == 'Run'
        assert phase2.status == Status.queued

        new_steps = sorted(JobStep.query.filter(
            JobStep.phase_id == phase2.id
        ), key=lambda x: x.date_created)

        assert len(new_steps) == 2
        assert new_steps[0].label == 'Optional name'
        assert new_steps[0].data == {
            'build_no': 23,
            'job_name': 'foo-bar',
            'cmd': 'echo 1',
        }

        assert new_steps[1].label == 'a357e93d82b8627ba1aa5f5c58884cd8'
        assert new_steps[1].data == {
            'build_no': 23,
            'job_name': 'foo-bar',
            'cmd': 'py.test --junit=junit.xml',
        }

        builder.fetch_artifact.assert_called_once_with(step, artifact)
        builder.create_job_from_params.assert_any_call(
            job_name='foo-bar',
            target_id=new_steps[0].id.hex,
            params=builder.get_job_parameters.return_value,
        )
        builder.create_job_from_params.assert_any_call(
            job_name='foo-bar',
            target_id=new_steps[1].id.hex,
            params=builder.get_job_parameters.return_value,
        )

########NEW FILE########
__FILENAME__ = test_test_collector
from __future__ import absolute_import

import mock
import responses

from changes.backends.jenkins.generic_builder import JenkinsGenericBuilder
from changes.backends.jenkins.buildsteps.test_collector import JenkinsTestCollectorBuildStep
from changes.constants import Result, Status
from changes.models import JobPhase, JobStep
from changes.testutils import TestCase


class JenkinsTestCollectorBuildStepTest(TestCase):
    def get_buildstep(self):
        return JenkinsTestCollectorBuildStep(
            job_name='foo-bar',
            script='exit 0',
            cluster='default',
            max_shards=2,
        )

    def get_mock_builder(self):
        return mock.Mock(spec=JenkinsGenericBuilder)

    def test_get_builder(self):
        builder = self.get_buildstep().get_builder()
        assert builder.job_name == 'foo-bar'
        assert builder.script == 'exit 0'
        assert builder.cluster == 'default'

    @mock.patch.object(JenkinsTestCollectorBuildStep, 'get_builder')
    def test_default_artifact_handling(self, get_builder):
        builder = self.get_mock_builder()
        get_builder.return_value = builder

        build = self.create_build(self.project)
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })
        artifact = {'fileName': 'junit.xml'}

        buildstep = self.get_buildstep()
        buildstep.fetch_artifact(step, artifact)

        builder.sync_artifact.assert_called_once_with(step, artifact)

    def test_get_test_stats(self):
        build = self.create_build(
            project=self.project,
            status=Status.finished,
            result=Result.passed,
        )
        job = self.create_job(build)
        self.create_test(job, name='foo.bar.test_baz', duration=50)
        self.create_test(job, name='foo.bar.test_bar', duration=25)

        buildstep = self.get_buildstep()

        results, avg_time = buildstep.get_test_stats(self.project)

        assert avg_time == 37

        assert results['foo.bar'] == 75
        assert results['foo.bar.test_baz'] == 50
        assert results['foo.bar.test_bar'] == 25

    @responses.activate
    @mock.patch.object(JenkinsTestCollectorBuildStep, 'get_builder')
    @mock.patch.object(JenkinsTestCollectorBuildStep, 'get_test_stats')
    def test_job_expansion(self, get_test_stats, get_builder):
        """
        Fairly heavy integration test which mocks out a few things but ensures
        that generic APIs are called correctly and the tests.json is parsed
        as expected.
        """
        builder = self.get_mock_builder()
        builder.fetch_artifact.return_value.json.return_value = {
            'phase': 'Test',
            'cmd': 'py.test --junit=junit.xml {test_names}',
            'tests': [
                'foo.bar.test_baz',
                'foo.bar.test_bar',
                'foo.bar.test_biz',
                'foo.bar.test_buz',
            ],
        }
        builder.create_job_from_params.return_value = {
            'job_name': 'foo-bar',
            'build_no': 23,
        }

        get_builder.return_value = builder
        get_test_stats.return_value = {
            'foo.bar.test_baz': 50,
            'foo.bar.test_bar': 15,
            'foo.bar.test_biz': 10,
            'foo.bar.test_buz': 200,
            'foo.bar': 275,
        }, 68

        build = self.create_build(self.project)
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })
        artifact = {
            'fileName': 'tests.json',
        }

        buildstep = self.get_buildstep()
        buildstep.fetch_artifact(step, artifact)

        phase2 = JobPhase.query.filter(
            JobPhase.job_id == job.id,
            JobPhase.id != phase.id,
        ).first()

        assert phase2, 'phase wasnt created'
        assert phase2.label == 'Test'
        assert phase2.status == Status.queued

        new_steps = sorted(JobStep.query.filter(
            JobStep.phase_id == phase2.id
        ), key=lambda x: x.date_created)

        assert len(new_steps) == 2
        assert new_steps[0].label == '790ed83d37c20fd5178ddb4f20242ef6'
        assert new_steps[0].data == {
            'build_no': 23,
            'job_name': 'foo-bar',
            'tests': ['foo.bar.test_buz'],
            'path': '',
            'cmd': 'py.test --junit=junit.xml {test_names}',
        }

        assert new_steps[1].label == '4984ae5173fdb4166e5454d2494a106d'
        assert new_steps[1].data == {
            'build_no': 23,
            'job_name': 'foo-bar',
            'tests': ['foo.bar.test_baz', 'foo.bar.test_bar', 'foo.bar.test_biz'],
            'path': '',
            'cmd': 'py.test --junit=junit.xml {test_names}',
        }

        builder.fetch_artifact.assert_called_once_with(step, artifact)
        builder.create_job_from_params.assert_any_call(
            job_name='foo-bar',
            target_id=new_steps[0].id.hex,
            params=builder.get_job_parameters.return_value,
        )
        builder.create_job_from_params.assert_any_call(
            job_name='foo-bar',
            target_id=new_steps[1].id.hex,
            params=builder.get_job_parameters.return_value,
        )

########NEW FILE########
__FILENAME__ = test_builder
from __future__ import absolute_import

import mock
import os.path
import responses
import pytest

from flask import current_app
from uuid import UUID

from changes.config import db
from changes.constants import Status, Result
from changes.models import (
    Artifact, TestCase, Patch, LogSource, LogChunk, Job, FileCoverage
)
from changes.backends.jenkins.builder import JenkinsBuilder, chunked
from changes.testutils import (
    BackendTestCase, eager_tasks, SAMPLE_DIFF, SAMPLE_XUNIT, SAMPLE_COVERAGE
)


class BaseTestCase(BackendTestCase):
    provider = 'jenkins'
    builder_cls = JenkinsBuilder
    builder_options = {
        'base_url': 'http://jenkins.example.com',
        'job_name': 'server',
    }

    def get_builder(self, **options):
        base_options = self.builder_options.copy()
        base_options.update(options)
        return self.builder_cls(app=current_app, **base_options)

    def load_fixture(self, filename):
        filepath = os.path.join(
            os.path.dirname(__file__),
            filename,
        )
        with open(filepath, 'rb') as fp:
            return fp.read()


# TODO(dcramer): these tests need to ensure we're passing the right parameters
# to jenkins
class CreateBuildTest(BaseTestCase):
    @responses.activate
    def test_queued_creation(self):
        responses.add(
            responses.POST, 'http://jenkins.example.com/job/server/build/api/json/',
            body='',
            status=201)

        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/api/xml/?xpath=%2Fqueue%2Fitem%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22+and+action%2Fparameter%2Fvalue%3D%2281d1596fd4d642f4a6bdf86c45e014e8%22%5D%2Fid&wrapper=x',
            body=self.load_fixture('fixtures/GET/queue_item_by_job_id.xml'),
            match_querystring=True)

        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/api/xml/?depth=1&xpath=/queue/item[action/parameter/name=%22CHANGES_BID%22%20and%20action/parameter/value=%2281d1596fd4d642f4a6bdf86c45e014e8%22]/id',
            status=404,
            match_querystring=True)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'))

        builder = self.get_builder()
        builder.create_job(job)

        step = job.phases[0].steps[0]

        assert step.data == {
            'build_no': None,
            'item_id': '13',
            'job_name': 'server',
            'queued': True,
        }

    @responses.activate
    def test_active_creation(self):
        responses.add(
            responses.POST, 'http://jenkins.example.com/job/server/build/api/json/',
            body='',
            status=201)

        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/api/xml/?xpath=%2Fqueue%2Fitem%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22+and+action%2Fparameter%2Fvalue%3D%22f9481a17aac446718d7893b6e1c6288b%22%5D%2Fid&wrapper=x',
            status=404,
            match_querystring=True)

        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/api/xml/?xpath=%2FfreeStyleProject%2Fbuild%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22+and+action%2Fparameter%2Fvalue%3D%22f9481a17aac446718d7893b6e1c6288b%22%5D%2Fnumber&depth=1&wrapper=x',
            body=self.load_fixture('fixtures/GET/build_item_by_job_id.xml'),
            match_querystring=True)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('f9481a17aac446718d7893b6e1c6288b'),
        )

        builder = self.get_builder()
        builder.create_job(job)

        step = job.phases[0].steps[0]

        assert step.data == {
            'build_no': '1',
            'item_id': None,
            'job_name': 'server',
            'queued': False,
        }

    @responses.activate
    @mock.patch.object(JenkinsBuilder, '_find_job')
    def test_patch(self, find_job):
        responses.add(
            responses.POST, 'http://jenkins.example.com/job/server/build/api/json/',
            body='',
            status=201)

        find_job.return_value = {
            'build_no': '1',
            'item_id': None,
            'job_name': 'server',
            'queued': False,
        }

        patch = Patch(
            repository=self.repo,
            project=self.project,
            parent_revision_sha='7ebd1f2d750064652ef5bbff72452cc19e1731e0',
            diff=SAMPLE_DIFF,
        )
        db.session.add(patch)

        source = self.create_source(self.project, patch=patch)
        build = self.create_build(self.project, source=source)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8')
        )

        builder = self.get_builder()
        builder.create_job(job)


class CancelJobTest(BaseTestCase):
    @mock.patch.object(JenkinsBuilder, 'cancel_step')
    def test_simple(self, cancel_step):
        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job)
        step1 = self.create_jobstep(phase, data={
            'item_id': 1,
            'job_name': 'server',
        }, status=Status.queued)

        self.create_jobstep(phase, data={
            'item_id': 2,
            'job_name': 'server',
        }, status=Status.finished)

        builder = self.get_builder()
        builder.cancel_job(job)

        cancel_step.assert_called_once_with(step1)


class CancelStepTest(BaseTestCase):
    @responses.activate
    def test_queued(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/cancelItem?id=13',
            match_querystring=True, status=302)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        }, status=Status.queued)

        builder = self.get_builder()
        builder.cancel_step(step)

        assert step.result == Result.aborted
        assert step.status == Status.finished

    @responses.activate
    def test_active(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/stop/',
            body='', status=302)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'build_no': 2,
            'job_name': 'server',
        }, status=Status.in_progress)

        builder = self.get_builder()
        builder.cancel_step(step)

        assert step.status == Status.finished
        assert step.result == Result.aborted


class SyncBuildTest(BaseTestCase):
    @responses.activate
    def test_waiting_in_queue(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/item/13/api/json/',
            body=self.load_fixture('fixtures/GET/queue_details_pending.json'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'build_no': None,
            'item_id': 13,
            'job_name': 'server',
            'queued': True,
        })

        builder = self.get_builder()
        builder.sync_step(step)

        assert step.status == Status.queued

    @responses.activate
    def test_cancelled_in_queue(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/item/13/api/json/',
            body=self.load_fixture('fixtures/GET/queue_details_cancelled.json'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'build_no': None,
            'item_id': 13,
            'job_name': 'server',
            'queued': True,
        })

        builder = self.get_builder()
        builder.sync_step(step)

        assert step.status == Status.finished
        assert step.result == Result.aborted

    @responses.activate
    def test_queued_to_active(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/item/13/api/json/',
            body=self.load_fixture('fixtures/GET/queue_details_building.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_building.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveHtml/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
            body='')
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'build_no': None,
            'item_id': 13,
            'job_name': 'server',
            'queued': True,
        })
        builder = self.get_builder()
        builder.sync_step(step)

        assert step.data['build_no'] == 2

    @responses.activate
    def test_success_result(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_success.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveHtml/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
            body='')
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()
        builder.sync_step(step)

        assert step.data['build_no'] == 2
        assert step.status == Status.finished
        assert step.result == Result.passed
        assert step.date_finished is not None

    @responses.activate
    def test_failed_result(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_failed.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveHtml/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
            body='')
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()
        builder.sync_step(step)

        assert step.data['build_no'] == 2
        assert step.status == Status.finished
        assert step.result == Result.failed
        assert step.date_finished is not None

    @responses.activate
    def test_does_sync_test_report(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_with_test_report.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/testReport/api/json/',
            body=self.load_fixture('fixtures/GET/job_test_report.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveHtml/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
            body='')
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()
        builder.sync_step(step)

        test_list = sorted(TestCase.query.filter_by(job=job), key=lambda x: x.duration)

        assert len(test_list) == 2
        assert test_list[0].name == 'tests.changes.handlers.test_xunit.Test'
        assert test_list[0].result == Result.skipped
        assert test_list[0].message == 'collection skipped'
        assert test_list[0].duration == 0

        assert test_list[1].name == 'tests.changes.api.test_build_details.BuildDetailsTest.test_simple'
        assert test_list[1].result == Result.passed
        assert test_list[1].message == ''
        assert test_list[1].duration == 155

    @responses.activate
    def test_does_sync_log(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_failed.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/testReport/api/json/',
            body=self.load_fixture('fixtures/GET/job_test_report.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveHtml/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '7'},
            body='Foo bar')
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()
        builder.sync_step(step)

        source = LogSource.query.filter_by(job=job).first()
        assert source.step == step
        assert source.name == step.label
        assert source.project == self.project
        assert source.date_created == step.date_started

        chunks = list(LogChunk.query.filter_by(
            source=source,
        ).order_by(LogChunk.date_created.asc()))
        assert len(chunks) == 1
        assert chunks[0].job_id == job.id
        assert chunks[0].project_id == self.project.id
        assert chunks[0].offset == 0
        assert chunks[0].size == 7
        assert chunks[0].text == 'Foo bar'

        assert step.data.get('log_offset') == 7

    @responses.activate
    @mock.patch('changes.backends.jenkins.builder.sync_artifact')
    def test_does_fire_sync_artifacts(self, sync_artifact):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_with_artifacts.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/testReport/api/json/',
            body=self.load_fixture('fixtures/GET/job_test_report.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveHtml/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
            body='')
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)
        builder = self.get_builder()
        builder.sync_step(step)

        log_artifact = Artifact.query.filter(
            Artifact.name == 'foobar.log',
            Artifact.step == step,
        ).first()

        assert log_artifact.data == {
            "displayPath": "foobar.log",
            "fileName": "foobar.log",
            "relativePath": "artifacts/foobar.log",
        }

        sync_artifact.delay_if_needed.assert_any_call(
            artifact_id=log_artifact.id.hex,
            task_id=log_artifact.id.hex,
            parent_task_id=step.id.hex
        )

        xunit_artifact = Artifact.query.filter(
            Artifact.name == 'tests.xml',
            Artifact.step == step,
        ).first()

        assert xunit_artifact.data == {
            "displayPath": "tests.xml",
            "fileName": "tests.xml",
            "relativePath": "artifacts/tests.xml",
        }

        sync_artifact.delay_if_needed.assert_any_call(
            artifact_id=xunit_artifact.id.hex,
            task_id=xunit_artifact.id.hex,
            parent_task_id=step.id.hex
        )

    @responses.activate
    def test_sync_artifact_as_log(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/artifact/artifacts/foobar.log',
            body='hello world')

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()
        builder.sync_artifact(step, {
            "displayPath": "foobar.log",
            "fileName": "foobar.log",
            "relativePath": "artifacts/foobar.log"
        })

        source = LogSource.query.filter(
            LogSource.job_id == job.id,
            LogSource.name == 'foobar.log',
        ).first()
        assert source is not None
        assert source.step == step
        assert source.project == self.project

        chunks = list(LogChunk.query.filter_by(
            source=source,
        ).order_by(LogChunk.date_created.asc()))
        assert len(chunks) == 1
        assert chunks[0].job_id == job.id
        assert chunks[0].project_id == self.project.id
        assert chunks[0].offset == 0
        assert chunks[0].size == 11
        assert chunks[0].text == 'hello world'

    @responses.activate
    def test_sync_artifact_as_xunit(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/artifact/artifacts/xunit.xml',
            body=SAMPLE_XUNIT,
            stream=True)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()
        builder.sync_artifact(step, {
            "displayPath": "xunit.xml",
            "fileName": "xunit.xml",
            "relativePath": "artifacts/xunit.xml"
        })

        test_list = list(TestCase.query.filter(
            TestCase.job_id == job.id
        ))

        assert len(test_list) == 2

    @responses.activate
    def test_sync_artifact_as_coverage(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/artifact/artifacts/coverage.xml',
            body=SAMPLE_COVERAGE,
            stream=True)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()
        builder.sync_artifact(step, {
            "displayPath": "coverage.xml",
            "fileName": "coverage.xml",
            "relativePath": "artifacts/coverage.xml"
        })

        cover_list = list(FileCoverage.query.filter(
            FileCoverage.job_id == job.id
        ))

        assert len(cover_list) == 2


class ChunkedTest(BaseTestCase):
    def test_simple(self):
        foo = 'aaa\naaa\naaa\n'

        result = list(chunked(foo, 5))
        assert len(result) == 3
        assert result[0] == 'aaa\n'
        assert result[1] == 'aaa\n'
        assert result[2] == 'aaa\n'

        result = list(chunked(foo, 8))

        assert len(result) == 2
        assert result[0] == 'aaa\naaa\n'
        assert result[1] == 'aaa\n'

        result = list(chunked(foo, 4))

        assert len(result) == 3
        assert result[0] == 'aaa\n'
        assert result[1] == 'aaa\n'
        assert result[2] == 'aaa\n'

        foo = 'a' * 10

        result = list(chunked(foo, 2))
        assert len(result) == 5
        assert all(r == 'aa' for r in result)

        foo = 'aaaa\naaaa'

        result = list(chunked(foo, 3))
        assert len(result) == 4


class JenkinsIntegrationTest(BaseTestCase):
    """
    This test should ensure a full cycle of tasks completes successfully within
    the jenkins builder space.
    """
    # it's possible for this test to infinitely hang due to continuous polling,
    # so let's ensure we set a timeout
    @pytest.mark.timeout(1)
    @mock.patch('changes.config.redis.lock', mock.MagicMock())
    @eager_tasks
    @responses.activate
    def test_full(self):
        from changes.jobs.create_job import create_job

        # TODO: move this out of this file and integrate w/ buildstep
        responses.add(
            responses.POST, 'http://jenkins.example.com/job/server/build/api/json/',
            body='',
            status=201)
        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/api/xml/?wrapper=x&xpath=%2Fqueue%2Fitem%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22+and+action%2Fparameter%2Fvalue%3D%2281d1596fd4d642f4a6bdf86c45e014e8%22%5D%2Fid',
            body=self.load_fixture('fixtures/GET/queue_item_by_job_id.xml'),
            match_querystring=True)
        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/item/13/api/json/',
            body=self.load_fixture('fixtures/GET/queue_details_building.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_with_test_report.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/testReport/api/json/',
            body=self.load_fixture('fixtures/GET/job_test_report.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveHtml/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '7'},
            body='Foo bar')
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'))

        plan = self.create_plan()
        plan.projects.append(self.project)
        self.create_step(
            plan, order=0, implementation='changes.backends.jenkins.buildstep.JenkinsBuildStep', data={
                'job_name': 'server',
            },
        )
        self.create_job_plan(job, plan)

        job_id = job.id.hex
        build_id = build.id.hex

        create_job.delay(
            job_id=job_id,
            task_id=job_id,
            parent_task_id=build_id,
        )

        job = Job.query.get(job_id)

        assert job.status == Status.finished
        assert job.result == Result.passed
        assert job.date_created
        assert job.date_started
        assert job.date_finished

        phase_list = job.phases

        assert len(phase_list) == 1

        assert phase_list[0].status == Status.finished
        assert phase_list[0].result == Result.passed
        assert phase_list[0].date_created
        assert phase_list[0].date_started
        assert phase_list[0].date_finished

        step_list = phase_list[0].steps

        assert len(step_list) == 1

        assert step_list[0].status == Status.finished
        assert step_list[0].result == Result.passed
        assert step_list[0].date_created
        assert step_list[0].date_started
        assert step_list[0].date_finished
        assert step_list[0].data == {
            'item_id': '13',
            'queued': False,
            'log_offset': 7,
            'job_name': 'server',
            'build_no': 2,
        }

        node = step_list[0].node
        assert node.label == 'server-ubuntu-10.04 (ami-746cf244) (i-836023b7)'
        assert [n.label for n in node.clusters] == ['server-runner']

        test_list = sorted(TestCase.query.filter_by(job=job), key=lambda x: x.duration)

        assert len(test_list) == 2
        assert test_list[0].name == 'tests.changes.handlers.test_xunit.Test'
        assert test_list[0].result == Result.skipped
        assert test_list[0].message == 'collection skipped'
        assert test_list[0].duration == 0

        assert test_list[1].name == 'tests.changes.api.test_build_details.BuildDetailsTest.test_simple'
        assert test_list[1].result == Result.passed
        assert test_list[1].message == ''
        assert test_list[1].duration == 155

        source = LogSource.query.filter_by(job=job).first()
        assert source.name == step_list[0].label
        assert source.step == step_list[0]
        assert source.project == self.project
        assert source.date_created == job.date_started

        chunks = list(LogChunk.query.filter_by(
            source=source,
        ).order_by(LogChunk.date_created.asc()))
        assert len(chunks) == 1
        assert chunks[0].job_id == job.id
        assert chunks[0].project_id == self.project.id
        assert chunks[0].offset == 0
        assert chunks[0].size == 7
        assert chunks[0].text == 'Foo bar'

########NEW FILE########
__FILENAME__ = test_buildstep
from __future__ import absolute_import

import mock

from changes.backends.jenkins.builder import JenkinsBuilder
from changes.backends.jenkins.buildstep import JenkinsBuildStep
from changes.testutils import TestCase


class JenkinsBuildStepTest(TestCase):
    def get_buildstep(self):
        return JenkinsBuildStep(job_name='foo-bar')

    def test_get_builder(self):
        buildstep = self.get_buildstep()
        builder = buildstep.get_builder()
        assert builder.job_name == 'foo-bar'
        assert type(builder) == JenkinsBuilder

    @mock.patch.object(JenkinsBuildStep, 'get_builder')
    def test_execute(self, get_builder):
        builder = mock.Mock()
        get_builder.return_value = builder

        build = self.create_build(self.project)
        job = self.create_job(build)

        buildstep = self.get_buildstep()
        buildstep.execute(job)

        builder.create_job.assert_called_once_with(job)

    @mock.patch.object(JenkinsBuildStep, 'get_builder')
    def test_update(self, get_builder):
        builder = mock.Mock()
        get_builder.return_value = builder

        build = self.create_build(self.project)
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })

        buildstep = self.get_buildstep()
        buildstep.update(job)

        builder.sync_job.assert_called_once_with(job)

    @mock.patch.object(JenkinsBuildStep, 'get_builder')
    def test_update_step(self, get_builder):
        builder = mock.Mock()
        get_builder.return_value = builder

        build = self.create_build(self.project)
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })

        buildstep = self.get_buildstep()
        buildstep.update_step(step)

        builder.sync_step.assert_called_once_with(step)

    @mock.patch.object(JenkinsBuildStep, 'get_builder')
    def test_fetch_artifact(self, get_builder):
        builder = mock.Mock()
        get_builder.return_value = builder

        build = self.create_build(self.project)
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })
        artifact = {'foo': 'bar'}

        buildstep = self.get_buildstep()
        buildstep.fetch_artifact(step, artifact)

        builder.sync_artifact.assert_called_once_with(step, artifact)

########NEW FILE########
__FILENAME__ = test_factory_builder
from __future__ import absolute_import

import mock
import responses

from uuid import UUID

from changes.backends.jenkins.factory_builder import JenkinsFactoryBuilder
from changes.models import JobPhase
from .test_builder import BaseTestCase


class SyncBuildTest(BaseTestCase):
    builder_cls = JenkinsFactoryBuilder
    builder_options = {
        'base_url': 'http://jenkins.example.com',
        'job_name': 'server',
        'downstream_job_names': ['server-downstream'],
    }

    @responses.activate
    @mock.patch('changes.config.queue.delay')
    def test_does_sync_details(self, delay):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_success.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/testReport/api/json/',
            body='')
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveHtml/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
            body='')
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server-downstream/api/xml/?xpath=%2FfreeStyleProject%2Fbuild%5Baction%2Fcause%2FupstreamProject%3D%22server%22+and+action%2Fcause%2FupstreamBuild%3D%222%22%5D%2Fnumber&depth=1&wrapper=a',
            body=self.load_fixture('fixtures/GET/job_list_by_upstream.xml'),
            match_querystring=True)
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job, label='server')
        step = self.create_jobstep(phase, data={
            'build_no': 2,
            'item_id': 13,
            'job_name': 'server',
            'queued': False,
        })

        builder = self.get_builder()
        builder.sync_step(step)

        phase_list = list(JobPhase.query.filter(
            JobPhase.job_id == job.id,
        ).order_by(JobPhase.label.asc()))
        assert len(phase_list) == 2
        assert phase_list[0].label == 'server'
        assert phase_list[1].label == 'server-downstream'

        step_list = sorted(phase_list[1].steps, key=lambda x: x.label)
        assert len(step_list) == 2
        assert step_list[0].label == 'server-downstream #171'
        assert step_list[1].label == 'server-downstream #172'

########NEW FILE########
__FILENAME__ = test_generic_builder
from __future__ import absolute_import

from changes.backends.jenkins.generic_builder import JenkinsGenericBuilder
from .test_builder import BaseTestCase


class JenkinsGenericBuilderTest(BaseTestCase):
    builder_cls = JenkinsGenericBuilder
    builder_options = {
        'base_url': 'http://jenkins.example.com',
        'job_name': 'server',
        'script': 'py.test',
        'cluster': 'default',
    }

    def test_get_job_parameters(self):
        build = self.create_build(self.project)
        job = self.create_job(build)

        builder = self.get_builder()

        result = builder.get_job_parameters(job, path='foo')
        assert {'name': 'CHANGES_BID', 'value': job.id.hex} in result
        assert {'name': 'CHANGES_PID', 'value': job.project.slug} in result
        assert {'name': 'REPO_URL', 'value': job.project.repository.url} in result
        assert {'name': 'REPO_VCS', 'value': job.project.repository.backend.name} in result
        assert {'name': 'REVISION', 'value': job.source.revision_sha} in result
        assert {'name': 'SCRIPT', 'value': self.builder_options['script']} in result
        assert {'name': 'CLUSTER', 'value': self.builder_options['cluster']} in result
        assert {'name': 'WORK_PATH', 'value': 'foo'} in result
        assert len(result) == 8

        # test optional path value
        result = builder.get_job_parameters(job)
        assert {'name': 'WORK_PATH', 'value': ''} in result

########NEW FILE########
__FILENAME__ = test_coverage
import uuid

from cStringIO import StringIO
from mock import patch

from changes.models import Job, JobStep
from changes.models.filecoverage import FileCoverage
from changes.handlers.coverage import CoverageHandler
from changes.testutils import TestCase
from changes.testutils.fixtures import SAMPLE_COVERAGE


def test_result_generation():
    jobstep = JobStep(
        id=uuid.uuid4(),
        job=Job(id=uuid.uuid4(), project_id=uuid.uuid4())
    )

    fp = StringIO(SAMPLE_COVERAGE)

    handler = CoverageHandler(jobstep)
    results = handler.get_coverage(fp)

    assert len(results) == 2

    r1 = results[0]
    assert type(r1) == FileCoverage
    assert r1.job_id == jobstep.job.id
    assert r1.project_id == jobstep.job.project_id
    assert r1.filename == 'setup.py'
    assert r1.data == 'NUNNNNNNNNNUCCNU'
    r2 = results[1]
    assert type(r2) == FileCoverage
    assert r2.job_id == jobstep.job.id
    assert r2.project_id == jobstep.job.project_id
    assert r2.data == 'CCCNNNU'


class CoverageHandlerTest(TestCase):
    @patch.object(CoverageHandler, 'get_coverage')
    @patch.object(CoverageHandler, 'process_diff')
    def test_simple(self, process_diff, get_coverage):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        handler = CoverageHandler(jobstep)

        process_diff.return_value = {
            'setup.py': set([1, 2, 3, 4, 5]),
        }

        # now try with some duplicate coverage
        get_coverage.return_value = [FileCoverage(
            job_id=job.id,
            step_id=jobstep.id,
            project_id=project.id,
            filename='setup.py',
            data='CUNNNNCCNNNUNNNUUUUUU'
        )]

        fp = StringIO()
        handler.process(fp)
        get_coverage.assert_called_once_with(fp)

        get_coverage.reset_mock()

        get_coverage.return_value = [FileCoverage(
            job_id=job.id,
            step_id=jobstep.id,
            project_id=project.id,
            filename='setup.py',
            data='NUUNNNNNNNNUCCNU'
        )]

        fp = StringIO()
        handler.process(fp)
        get_coverage.assert_called_once_with(fp)

        file_cov = list(FileCoverage.query.filter(
            FileCoverage.job_id == job.id,
        ))
        assert len(file_cov) == 1
        assert file_cov[0].filename == 'setup.py'
        assert file_cov[0].data == 'CUUNNNCCNNNUCCNUUUUUU'
        assert file_cov[0].lines_covered == 5
        assert file_cov[0].lines_uncovered == 9
        assert file_cov[0].diff_lines_covered == 1
        assert file_cov[0].diff_lines_uncovered == 2

########NEW FILE########
__FILENAME__ = test_xunit
import uuid

from cStringIO import StringIO

from changes.constants import Result
from changes.models import JobStep, TestResult
from changes.handlers.xunit import XunitHandler
from changes.testutils import SAMPLE_XUNIT


def test_result_generation():
    jobstep = JobStep(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
    )

    fp = StringIO(SAMPLE_XUNIT)

    handler = XunitHandler(jobstep)
    results = handler.get_tests(fp)

    assert len(results) == 2

    r1 = results[0]
    assert type(r1) == TestResult
    assert r1.step == jobstep
    assert r1.package is None
    assert r1.name == 'tests.test_report'
    assert r1.duration == 0.0
    assert r1.result == Result.failed
    assert r1.message == """tests/test_report.py:1: in <module>
>   import mock
E   ImportError: No module named mock"""
    r2 = results[1]
    assert type(r2) == TestResult
    assert r2.step == jobstep
    assert r2.package is None
    assert r2.name == 'tests.test_report.ParseTestResultsTest.test_simple'
    assert r2.duration == 1.65796279907
    assert r2.result == Result.passed
    assert r2.message == ''
    assert r2.reruns == 1

########NEW FILE########
__FILENAME__ = test_cleanup_tasks
from __future__ import absolute_import

from mock import patch

from datetime import datetime
from uuid import uuid4

from changes.constants import Status
from changes.jobs.cleanup_tasks import cleanup_tasks, CHECK_TIME
from changes.models import Task
from changes.testutils import TestCase


class CleanupTasksTest(TestCase):
    @patch('changes.config.queue.delay')
    def test_queues_jobs(self, mock_delay):
        now = datetime.utcnow()
        old_dt = now - (CHECK_TIME * 2)

        task = self.create_task(
            task_name='cleanup_tasks',
            task_id=uuid4(),
            date_created=old_dt,
            status=Status.queued,
            data={'kwargs': {'foo': 'bar'}},
        )

        self.create_task(
            task_name='cleanup_tasks',
            task_id=uuid4(),
            date_created=now,
            status=Status.finished,
        )

        self.create_task(
            task_name='cleanup_tasks',
            task_id=uuid4(),
            date_created=old_dt,
            status=Status.finished,
        )

        cleanup_tasks()

        mock_delay.assert_called_once_with(
            'cleanup_tasks',
            countdown=5,
            kwargs={
                'task_id': task.task_id.hex,
                'parent_task_id': None,
                'foo': 'bar',
            },
        )

        task = Task.query.get(task.id)

        assert task.date_modified > old_dt

########NEW FILE########
__FILENAME__ = test_create_job
from __future__ import absolute_import

import mock

from changes.jobs.create_job import create_job
from changes.models import Step
from changes.testutils import TestCase


class CreateJobTest(TestCase):
    @mock.patch('changes.jobs.create_job.sync_job')
    @mock.patch.object(Step, 'get_implementation')
    def test_simple(self, get_implementation, sync_job):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        build = self.create_build(self.project)
        job = self.create_job(build)
        plan = self.create_plan()
        self.create_step(plan)
        self.create_job_plan(job, plan)

        create_job(
            job_id=job.id.hex,
            task_id=job.id.hex,
            parent_task_id=build.id.hex,
        )

        get_implementation.assert_called_once_with()

        implementation.execute.assert_called_once_with(
            job=job,
        )

        sync_job.delay.assert_called_once_with(
            job_id=job.id.hex,
            task_id=job.id.hex,
            parent_task_id=build.id.hex,
        )

########NEW FILE########
__FILENAME__ = test_signals
from mock import Mock, patch

from flask import current_app

from changes.jobs.signals import fire_signal, run_event_listener
from changes.testutils import TestCase


class SignalTestBase(TestCase):
    def setUp(self):
        super(SignalTestBase, self).setUp()
        self.original_listeners = current_app.config['EVENT_LISTENERS']
        current_app.config['EVENT_LISTENERS'] = (
            ('mock.Mock', 'test.signal'),
            ('mock.Mock', 'test.signal2'),
        )

    def tearDown(self):
        current_app.config['EVENT_LISTENERS'] = self.original_listeners
        super(SignalTestBase, self).tearDown()


class FireSignalTest(SignalTestBase):
    @patch('changes.jobs.signals.run_event_listener')
    def test_simple(self, mock_run_event_listener):
        fire_signal(signal='test.signal', kwargs={'foo': 'bar'})

        mock_run_event_listener.delay.assert_called_once_with(
            listener='mock.Mock',
            signal='test.signal',
            kwargs={'foo': 'bar'},
        )


class RunEventListenerTest(SignalTestBase):
    @patch('changes.jobs.signals.import_string')
    def test_simple(self, mock_import_string):
        mock_listener = Mock()
        mock_import_string.return_value = mock_listener

        run_event_listener(
            listener='mock.Mock',
            signal='test.signal',
            kwargs={'foo': 'bar'},
        )

        mock_import_string.assert_called_once_with('mock.Mock')

        mock_listener.assert_called_once_with(foo='bar')

########NEW FILE########
__FILENAME__ = test_sync_artifact
from __future__ import absolute_import

import mock

from changes.jobs.sync_artifact import sync_artifact
from changes.models import Step
from changes.testutils import TestCase


class SyncArtifactTest(TestCase):
    def setUp(self):
        super(SyncArtifactTest, self).setUp()
        self.project = self.create_project()
        self.build = self.create_build(project=self.project)
        self.job = self.create_job(build=self.build)
        self.jobphase = self.create_jobphase(self.job)
        self.jobstep = self.create_jobstep(self.jobphase)
        self.artifact = self.create_artifact(self.jobstep, name='foo', data={
            'foo': 'bar',
        })

        self.plan = self.create_plan()
        self.plan.projects.append(self.project)
        self.step = self.create_step(self.plan, implementation='test', order=0)
        self.jobplan = self.create_job_plan(self.job, self.plan)

    @mock.patch.object(Step, 'get_implementation')
    def test_simple(self, get_implementation):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        sync_artifact(artifact_id=self.artifact.id.hex)

        implementation.fetch_artifact.assert_called_once_with(
            step=self.jobstep,
            artifact=self.artifact.data,
        )

########NEW FILE########
__FILENAME__ = test_sync_build
from __future__ import absolute_import

import mock

from datetime import datetime

from changes.constants import Status, Result
from changes.config import db
from changes.models import Build, ItemStat
from changes.jobs.sync_build import sync_build
from changes.testutils import TestCase


class SyncBuildTest(TestCase):
    @mock.patch('changes.config.queue.delay')
    def test_simple(self, queue_delay):
        build = self.create_build(
            project=self.project,
            status=Status.unknown,
            result=Result.unknown,
        )

        job_a = self.create_job(
            build=build,
            status=Status.finished,
            result=Result.failed,
            duration=5000,
            date_started=datetime(2013, 9, 19, 22, 15, 22),
            date_finished=datetime(2013, 9, 19, 22, 15, 25),
        )
        job_b = self.create_job(
            build=build,
            status=Status.in_progress,
            result=Result.passed,
            duration=5000,
            date_started=datetime(2013, 9, 19, 22, 15, 23),
            date_finished=datetime(2013, 9, 19, 22, 15, 26),
        )
        self.create_task(
            task_name='sync_job',
            parent_id=build.id,
            task_id=job_a.id,
            status=Status.finished,
        )
        task_b = self.create_task(
            task_name='sync_job',
            parent_id=build.id,
            task_id=job_b.id,
            status=Status.in_progress,
        )

        db.session.add(ItemStat(item_id=job_a.id, name='tests_missing', value=1))
        db.session.add(ItemStat(item_id=job_b.id, name='tests_missing', value=0))
        db.session.commit()

        sync_build(build_id=build.id.hex, task_id=build.id.hex)

        build = Build.query.get(build.id)

        assert build.status == Status.in_progress
        assert build.result == Result.failed

        task_b.status = Status.finished
        db.session.add(task_b)
        job_b.status = Status.finished
        db.session.add(job_b)

        sync_build(build_id=build.id.hex, task_id=build.id.hex)

        build = Build.query.get(build.id)

        assert build.status == Status.finished
        assert build.result == Result.failed
        assert build.duration == 4000
        assert build.date_started == datetime(2013, 9, 19, 22, 15, 22)
        assert build.date_finished == datetime(2013, 9, 19, 22, 15, 26)

        queue_delay.assert_any_call('update_project_stats', kwargs={
            'project_id': self.project.id.hex,
        }, countdown=1)

        stat = ItemStat.query.filter(
            ItemStat.item_id == build.id,
            ItemStat.name == 'tests_missing',
        ).first()
        assert stat.value == 1

########NEW FILE########
__FILENAME__ = test_sync_job
from __future__ import absolute_import

import mock

from changes.constants import Status
from changes.config import db
from changes.jobs.sync_job import sync_job
from changes.models import ItemStat, Job, Step, Task
from changes.testutils import TestCase


class SyncJobTest(TestCase):
    def setUp(self):
        super(SyncJobTest, self).setUp()
        self.project = self.create_project()
        self.build = self.create_build(project=self.project)
        self.job = self.create_job(build=self.build)
        self.jobphase = self.create_jobphase(self.job)
        self.jobstep = self.create_jobstep(self.jobphase)

        self.task = self.create_task(
            parent_id=self.build.id,
            task_id=self.job.id,
            task_name='sync_job',
        )

        self.plan = self.create_plan()
        self.plan.projects.append(self.project)
        self.step = self.create_step(self.plan, implementation='test', order=0)
        self.jobplan = self.create_job_plan(self.job, self.plan)

    @mock.patch('changes.jobs.sync_job.queue.delay')
    @mock.patch.object(Step, 'get_implementation')
    def test_in_progress(self, get_implementation,
                         queue_delay):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        build, job, task = self.build, self.job, self.task

        self.create_task(
            task_name='sync_job_step',
            task_id=job.phases[0].steps[0].id,
            parent_id=job.id,
            status=Status.in_progress,
        )

        def mark_in_progress(job):
            job.status = Status.in_progress

        implementation.update.side_effect = mark_in_progress

        sync_job(
            job_id=job.id.hex,
            task_id=job.id.hex,
            parent_task_id=build.id.hex
        )

        get_implementation.assert_called_once_with()

        implementation.update.assert_called_once_with(
            job=self.job,
        )

        queue_delay.assert_any_call('sync_job', kwargs={
            'job_id': job.id.hex,
            'task_id': job.id.hex,
            'parent_task_id': build.id.hex,
        }, countdown=5)

        task = Task.query.get(task.id)

        assert task.status == Status.in_progress

    @mock.patch('changes.jobs.sync_job.fire_signal')
    @mock.patch('changes.jobs.sync_job.queue.delay')
    @mock.patch.object(Step, 'get_implementation')
    def test_finished(self, get_implementation, queue_delay,
                      mock_fire_signal):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        assert self.jobplan

        build, job, task = self.build, self.job, self.task

        step = job.phases[0].steps[0]

        self.create_task(
            task_name='sync_job_step',
            task_id=step.id,
            parent_id=job.id,
            status=Status.finished,
        )
        self.create_test(job)
        self.create_test(job)

        db.session.add(ItemStat(item_id=step.id, name='tests_missing', value=1))
        db.session.add(ItemStat(item_id=step.id, name='lines_covered', value=10))
        db.session.add(ItemStat(item_id=step.id, name='lines_uncovered', value=25))
        db.session.commit()

        sync_job(
            job_id=job.id.hex,
            task_id=job.id.hex,
            parent_task_id=build.id.hex,
        )

        job = Job.query.get(job.id)

        assert job.status == Status.finished

        queue_delay.assert_any_call('update_project_plan_stats', kwargs={
            'project_id': self.project.id.hex,
            'plan_id': self.plan.id.hex,
        }, countdown=1)

        mock_fire_signal.delay.assert_any_call(
            signal='job.finished',
            kwargs={'job_id': job.id.hex},
        )

        task = Task.query.get(task.id)

        assert task.status == Status.finished

        stat = ItemStat.query.filter(
            ItemStat.item_id == job.id,
            ItemStat.name == 'tests_missing',
        ).first()
        assert stat.value == 1

        stat = ItemStat.query.filter(
            ItemStat.item_id == job.id,
            ItemStat.name == 'lines_covered',
        ).first()
        assert stat.value == 10

        stat = ItemStat.query.filter(
            ItemStat.item_id == job.id,
            ItemStat.name == 'lines_uncovered',
        ).first()
        assert stat.value == 25

########NEW FILE########
__FILENAME__ = test_sync_job_step
from __future__ import absolute_import

import mock

from changes.config import db
from changes.constants import Result, Status
from changes.jobs.sync_job_step import sync_job_step
from changes.models import (
    ItemStat, JobStep, ProjectOption, Step, Task, FileCoverage
)
from changes.testutils import TestCase


class SyncJobStepTest(TestCase):
    @mock.patch('changes.config.queue.delay')
    @mock.patch.object(Step, 'get_implementation')
    def test_in_progress(self, get_implementation, queue_delay):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        def mark_in_progress(step):
            step.status = Status.in_progress

        build = self.create_build(project=self.project)
        job = self.create_job(build=build)

        plan = self.create_plan()
        self.create_step(plan, implementation='test', order=0)
        self.create_job_plan(job, plan)

        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase)
        task = self.create_task(
            parent_id=job.id,
            task_id=step.id,
            task_name='sync_job_step',
        )

        db.session.add(ItemStat(item_id=job.id, name='tests_missing', value=1))
        db.session.commit()

        implementation.update_step.side_effect = mark_in_progress

        sync_job_step(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=job.id.hex,
        )

        get_implementation.assert_called_once_with()

        implementation.update_step.assert_called_once_with(
            step=step
        )

        db.session.expire(step)
        db.session.expire(task)

        step = JobStep.query.get(step.id)

        assert step.status == Status.in_progress

        task = Task.query.get(task.id)

        assert task.status == Status.in_progress

        queue_delay.assert_any_call('sync_job_step', kwargs={
            'step_id': step.id.hex,
            'task_id': step.id.hex,
            'parent_task_id': job.id.hex,
        }, countdown=5)

    @mock.patch('changes.config.queue.delay')
    @mock.patch.object(Step, 'get_implementation')
    def test_finished(self, get_implementation, queue_delay):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        def mark_finished(step):
            step.status = Status.finished
            step.result = Result.passed

        implementation.update_step.side_effect = mark_finished

        build = self.create_build(project=self.project)
        job = self.create_job(build=build)

        plan = self.create_plan()
        self.create_step(plan, implementation='test', order=0)
        self.create_job_plan(job, plan)

        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase)
        task = self.create_task(
            parent_id=job.id,
            task_id=step.id,
            task_name='sync_job_step',
            status=Status.finished,
        )

        db.session.add(FileCoverage(
            job=job, step=step, project=job.project,
            filename='foo.py', data='CCCUUUCCCUUNNN',
            lines_covered=6,
            lines_uncovered=5,
            diff_lines_covered=3,
            diff_lines_uncovered=2,
        ))
        db.session.commit()

        sync_job_step(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=job.id.hex,
        )

        get_implementation.assert_called_once_with()

        implementation.update_step.assert_called_once_with(
            step=step
        )

        db.session.expire(step)
        db.session.expire(task)

        step = JobStep.query.get(step.id)

        assert step.status == Status.finished

        task = Task.query.get(task.id)

        assert task.status == Status.finished

        assert len(queue_delay.mock_calls) == 0

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'tests_missing',
        ).first()
        assert stat.value == 0

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'lines_covered',
        ).first()
        assert stat.value == 6

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'lines_uncovered',
        ).first()
        assert stat.value == 5

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'diff_lines_covered',
        ).first()
        assert stat.value == 3

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'diff_lines_uncovered',
        ).first()
        assert stat.value == 2

    @mock.patch('changes.config.queue.delay')
    @mock.patch.object(Step, 'get_implementation')
    def test_missing_test_results_and_expected(self, get_implementation, queue_delay):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        def mark_finished(step):
            step.status = Status.finished
            step.result = Result.passed

        implementation.update_step.side_effect = mark_finished

        build = self.create_build(project=self.project)
        job = self.create_job(build=build)

        plan = self.create_plan()
        self.create_step(plan, implementation='test', order=0)
        self.create_job_plan(job, plan)

        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase)

        db.session.add(ProjectOption(
            project_id=self.project.id,
            name='build.expect-tests',
            value='1'
        ))
        db.session.commit()

        sync_job_step(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=job.id.hex,
        )

        db.session.expire(step)

        step = JobStep.query.get(step.id)

        assert step.status == Status.finished
        assert step.result == Result.failed

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'tests_missing',
        ).first()
        assert stat.value == 1

########NEW FILE########
__FILENAME__ = test_sync_repo
from __future__ import absolute_import

import mock

from datetime import datetime

from changes.config import db
from changes.jobs.sync_repo import sync_repo
from changes.models import Repository, RepositoryBackend
from changes.testutils import TestCase
from changes.vcs.base import Vcs, RevisionResult


class SyncRepoTest(TestCase):
    @mock.patch('changes.jobs.sync_repo.fire_signal')
    @mock.patch('changes.models.Repository.get_vcs')
    @mock.patch('changes.config.queue.delay')
    def test_simple(self, queue_delay, get_vcs_backend, mock_fire_signal):
        vcs_backend = mock.MagicMock(spec=Vcs)

        def log(parent):
            if parent is None:
                yield RevisionResult(
                    id='a' * 40,
                    message='hello world!',
                    author='Example <foo@example.com>',
                    author_date=datetime(2013, 9, 19, 22, 15, 22),
                )

        get_vcs_backend.return_value = vcs_backend
        vcs_backend.log.side_effect = log

        repo = self.create_repo(
            backend=RepositoryBackend.git)

        sync_repo(repo_id=repo.id.hex, task_id=repo.id.hex)

        get_vcs_backend.assert_called_once_with()
        vcs_backend.log.assert_any_call(parent=None)
        vcs_backend.log.assert_any_call(parent='a' * 40)

        db.session.expire_all()

        repo = Repository.query.get(repo.id)

        assert repo.last_update_attempt is not None
        assert repo.last_update is not None

        # build sync is abstracted via sync_with_builder
        vcs_backend.update.assert_called_once_with()

        # ensure signal is fired
        queue_delay.assert_any_call('sync_repo', kwargs={
            'repo_id': repo.id.hex,
            'task_id': repo.id.hex,
            'parent_task_id': None,
        }, countdown=5)

        mock_fire_signal.delay.assert_any_call(
            signal='revision.created',
            kwargs={
                'repository_id': repo.id.hex,
                'revision_sha': 'a' * 40,
            },
        )

########NEW FILE########
__FILENAME__ = test_update_project_stats
from __future__ import absolute_import

from changes.constants import Status, Result
from changes.config import db
from changes.models import Project, ProjectPlan
from changes.jobs.update_project_stats import (
    update_project_stats, update_project_plan_stats
)
from changes.testutils import TestCase


class UpdateProjectStatsTest(TestCase):
    def test_simple(self):
        self.create_build(
            project=self.project,
            status=Status.finished,
            result=Result.passed,
            duration=5050,
        )

        update_project_stats(project_id=self.project.id.hex)

        db.session.expire(self.project)

        project = Project.query.get(self.project.id)

        assert project.avg_build_time == 5050


class UpdateProjectPlanStatsTest(TestCase):
    def test_simple(self):
        build = self.create_build(
            project=self.project,
            status=Status.finished,
            result=Result.passed,
            duration=5050,
        )
        job = self.create_job(build)
        plan = self.create_plan()
        plan.projects.append(self.project)
        self.create_job_plan(job, plan)

        update_project_plan_stats(
            project_id=self.project.id.hex,
            plan_id=plan.id.hex,
        )

        db.session.expire(plan)

        project_plan = ProjectPlan.query.filter(
            ProjectPlan.project_id == self.project.id,
            ProjectPlan.plan_id == plan.id,
        ).first()

        assert project_plan.avg_build_time == 5050

########NEW FILE########
__FILENAME__ = test_build_revision
from changes.config import db
from changes.listeners.build_revision import revision_created_handler
from changes.models import Build, ProjectOption
from changes.testutils.cases import TestCase


class RevisionCreatedHandlerTestCase(TestCase):
    def test_simple(self):
        repo = self.create_repo()
        revision = self.create_revision(repository=repo)
        project = self.create_project(repository=repo)
        plan = self.create_plan()
        plan.projects.append(project)

        revision_created_handler(revision_sha=revision.sha, repository_id=repo.id)

        build_list = list(Build.query.filter(
            Build.project == project,
        ))

        assert len(build_list) == 1

    def test_disabled(self):
        repo = self.create_repo()
        revision = self.create_revision(repository=repo)
        project = self.create_project(repository=repo)
        plan = self.create_plan()
        plan.projects.append(project)

        db.session.add(ProjectOption(project=project, name='build.commit-trigger', value='0'))
        db.session.commit()

        revision_created_handler(revision_sha=revision.sha, repository_id=repo.id)

        assert not Build.query.first()

########NEW FILE########
__FILENAME__ = test_green_build
from __future__ import absolute_import

import mock
import responses

from changes.constants import Result
from changes.listeners.green_build import build_finished_handler
from changes.models import Event, EventType, RepositoryBackend
from changes.testutils import TestCase


class GreenBuildTest(TestCase):
    @responses.activate
    @mock.patch('changes.listeners.green_build.get_options')
    @mock.patch('changes.models.Repository.get_vcs')
    def test_simple(self, vcs, get_options):
        responses.add(responses.POST, 'https://foo.example.com')

        repository = self.create_repo(
            backend=RepositoryBackend.hg,
        )

        project = self.create_project(repository=repository)

        source = self.create_source(
            project=project,
            revision_sha='a' * 40,
        )
        build = self.create_build(
            project=project,
            source=source,
        )

        build = self.create_build(
            project=project,
            source=source,
        )

        get_options.return_value = {
            'green-build.notify': '1',
        }
        vcs = build.source.repository.get_vcs.return_value
        vcs.run.return_value = '134:asdadfadf'

        # test with failing build
        build.result = Result.failed

        build_finished_handler(build_id=build.id.hex)

        assert len(responses.calls) == 0

        # test with passing build
        build.result = Result.passed

        build_finished_handler(build_id=build.id.hex)

        vcs.run.assert_called_once_with([
            'log', '-r aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', '--limit=1',
            '--template={rev}:{node|short}'
        ])

        get_options.assert_called_once_with(build.project_id)

        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == 'https://foo.example.com/'
        assert responses.calls[0].request.body == 'project={project_slug}&build_server=changes&build_url=http%3A%2F%2Fexample.com%2Fprojects%2F{project_slug}%2Fbuilds%2F{build_id}%2F&id=134%3Aasdadfadf'.format(
            project_slug=build.project.slug,
            build_id=build.id.hex,
        )

        event = Event.query.filter(
            Event.type == EventType.green_build,
        ).first()
        assert event
        assert event.item_id == build.id

########NEW FILE########
__FILENAME__ = test_hipchat
from __future__ import absolute_import

import mock
import responses

from changes.constants import Result
from changes.listeners.hipchat import build_finished_handler
from changes.testutils import TestCase


class HipChatTest(TestCase):
    @responses.activate
    @mock.patch('changes.listeners.hipchat.get_options')
    def test_simple(self, get_options):
        build = self.create_build(self.project, result=Result.failed)

        responses.add(
            responses.POST, 'https://api.hipchat.com/v1/rooms/message',
            body='{"status": "sent"}')

        get_options.return_value = {
            'hipchat.notify': '1',
            'hipchat.room': 'Awesome',
        }

        build_finished_handler(build_id=build.id.hex)

        get_options.assert_called_once_with(build.project_id)

        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == 'https://api.hipchat.com/v1/rooms/message'
        assert responses.calls[0].request.body == \
            'from=Changes&color=red' \
            '&auth_token=abc' \
            '&room_id=Awesome' \
            '&notify=1' \
            '&message=Build+Failed+-+%3Ca+href%3D%22http%3A%2F%2Fexample.com%2Fprojects%2Ftest%2Fbuilds%2F{build_id}%2F%22%3Etest+%231%3C%2Fa%3E+%28{target}%29'.format(
                build_id=build.id.hex,
                target=build.source.revision_sha,
            )

########NEW FILE########
__FILENAME__ = test_mail
import mock

from changes.config import db
from changes.constants import Result
from changes.models import ProjectOption, ItemOption
from changes.listeners.mail import MailNotificationHandler
from changes.testutils.cases import TestCase


class GetRecipientsTestCase(TestCase):
    def test_default_options(self):
        author = self.create_author('foo@example.com')
        build = self.create_build(self.project, result=Result.passed, author=author)
        job = self.create_job(build)

        handler = MailNotificationHandler()
        recipients = handler.get_recipients(job)

        assert recipients == ['{0} <foo@example.com>'.format(author.name)]

    def test_without_author_option(self):
        db.session.add(ProjectOption(
            project=self.project, name='mail.notify-author', value='0'))
        author = self.create_author('foo@example.com')
        build = self.create_build(self.project, result=Result.failed, author=author)
        job = self.create_job(build)
        db.session.commit()

        handler = MailNotificationHandler()
        recipients = handler.get_recipients(job)

        assert recipients == []

    def test_with_addressees(self):
        db.session.add(ProjectOption(
            project=self.project, name='mail.notify-author', value='1'))
        db.session.add(ProjectOption(
            project=self.project, name='mail.notify-addresses',
            value='test@example.com, bar@example.com'))

        author = self.create_author('foo@example.com')
        build = self.create_build(self.project, result=Result.failed, author=author)
        job = self.create_job(build)
        db.session.commit()

        handler = MailNotificationHandler()
        recipients = handler.get_recipients(job)

        assert recipients == [
            '{0} <foo@example.com>'.format(author.name),
            'test@example.com',
            'bar@example.com',
        ]

    def test_with_revision_addressees(self):
        db.session.add(ProjectOption(
            project=self.project, name='mail.notify-author', value='1'))
        db.session.add(ProjectOption(
            project=self.project, name='mail.notify-addresses-revisions',
            value='test@example.com, bar@example.com'))

        author = self.create_author('foo@example.com')
        patch = self.create_patch(project=self.project)
        source = self.create_source(self.project, patch=patch)
        build = self.create_build(
            project=self.project,
            source=source,
            author=author,
            result=Result.failed,
        )
        job = self.create_job(build=build)
        db.session.commit()

        handler = MailNotificationHandler()
        recipients = handler.get_recipients(job)

        assert recipients == ['{0} <foo@example.com>'.format(author.name)]

        build = self.create_build(
            project=self.project,
            result=Result.failed,
            author=author,
        )
        job = self.create_job(build=build)

        handler = MailNotificationHandler()
        recipients = handler.get_recipients(job)

        assert recipients == [
            '{0} <foo@example.com>'.format(author.name),
            'test@example.com',
            'bar@example.com',
        ]


class SendTestCase(TestCase):
    @mock.patch.object(MailNotificationHandler, 'get_recipients')
    def test_simple(self, get_recipients):
        build = self.create_build(self.project, target='D1234')
        job = self.create_job(build=build, result=Result.failed)
        phase = self.create_jobphase(job=job)
        step = self.create_jobstep(phase=phase)
        logsource = self.create_logsource(
            step=step,
            name='console',
        )
        self.create_logchunk(
            source=logsource,
            text='hello world',
        )

        job_link = 'http://example.com/projects/test/builds/%s/jobs/%s/' % (build.id.hex, job.id.hex,)
        log_link = '%slogs/%s/' % (job_link, logsource.id.hex)

        get_recipients.return_value = ['foo@example.com', 'Bob <bob@example.com>']

        handler = MailNotificationHandler()
        handler.send(job, None)

        assert len(self.outbox) == 1
        msg = self.outbox[0]

        assert msg.subject == '%s Failed - %s #%s.%s' % (
            job.build.target, job.project.name, job.build.number, job.number)
        assert msg.recipients == ['foo@example.com', 'Bob <bob@example.com>']
        assert msg.extra_headers['Reply-To'] == 'foo@example.com, Bob <bob@example.com>'

        assert job_link in msg.html
        assert job_link in msg.body
        assert log_link in msg.html
        assert log_link in msg.body

        assert msg.as_string()

    @mock.patch.object(MailNotificationHandler, 'get_recipients')
    def test_multiple_sources(self, get_recipients):
        build = self.create_build(self.project, target='D1234')
        job = self.create_job(build=build, result=Result.failed)
        phase = self.create_jobphase(job=job)
        step = self.create_jobstep(phase=phase)
        logsource = self.create_logsource(
            step=step,
            name='console',
        )
        self.create_logchunk(
            source=logsource,
            text='hello world',
        )
        phase2 = self.create_jobphase(job=job, label='other')
        step2 = self.create_jobstep(phase=phase2)
        logsource2 = self.create_logsource(
            step=step2,
            name='other',
        )
        self.create_logchunk(
            source=logsource2,
            text='hello world',
        )

        job_link = 'http://example.com/projects/test/builds/%s/jobs/%s/' % (build.id.hex, job.id.hex,)
        log_link1 = '%slogs/%s/' % (job_link, logsource.id.hex)
        log_link2 = '%slogs/%s/' % (job_link, logsource2.id.hex)

        get_recipients.return_value = ['foo@example.com', 'Bob <bob@example.com>']

        handler = MailNotificationHandler()
        handler.send(job, None)

        assert len(self.outbox) == 1
        msg = self.outbox[0]

        assert msg.subject == '%s Failed - %s #%s.%s' % (
            job.build.target, job.project.name, job.build.number, job.number)
        assert msg.recipients == ['foo@example.com', 'Bob <bob@example.com>']
        assert msg.extra_headers['Reply-To'] == 'foo@example.com, Bob <bob@example.com>'

        assert job_link in msg.html
        assert job_link in msg.body
        assert log_link1 in msg.html
        assert log_link1 in msg.body
        assert log_link2 in msg.html
        assert log_link2 in msg.body

        assert msg.as_string()


class GetJobOptionsTestCase(TestCase):
    def test_simple(self):
        project = self.project
        plan = self.create_plan()
        plan.projects.append(project)
        build = self.create_build(project)
        job = self.create_job(build)
        self.create_job_plan(job, plan)

        db.session.add(ItemOption(
            item_id=plan.id,
            name='mail.notify-author',
            value='0',
        ))

        db.session.add(ProjectOption(
            project_id=project.id,
            name='mail.notify-author',
            value='1',
        ))

        db.session.add(ProjectOption(
            project_id=project.id,
            name='mail.notify-addresses',
            value='foo@example.com',
        ))
        db.session.commit()

        handler = MailNotificationHandler()
        assert handler.get_job_options(job) == {
            'mail.notify-addresses': 'foo@example.com',
            'mail.notify-author': '0',
        }

########NEW FILE########
__FILENAME__ = test_notification_base
from changes.config import db
from changes.models import LogSource, LogChunk
from changes.listeners.notification_base import NotificationHandler
from changes.testutils.cases import TestCase


class GetLogClippingTestCase(TestCase):
    def test_simple(self):
        build = self.create_build(self.project)
        job = self.create_job(build)

        logsource = LogSource(
            project=self.project,
            job=job,
            name='console',
        )
        db.session.add(logsource)

        logchunk = LogChunk(
            project=self.project,
            job=job,
            source=logsource,
            offset=0,
            size=11,
            text='hello\nworld\n',
        )
        db.session.add(logchunk)
        logchunk = LogChunk(
            project=self.project,
            job=job,
            source=logsource,
            offset=11,
            size=11,
            text='hello\nworld\n',
        )
        db.session.add(logchunk)
        db.session.commit()

        handler = NotificationHandler()
        result = handler.get_log_clipping(logsource, max_size=200, max_lines=3)
        assert result == "world\r\nhello\r\nworld"

        result = handler.get_log_clipping(logsource, max_size=200, max_lines=1)
        assert result == "world"

        result = handler.get_log_clipping(logsource, max_size=5, max_lines=3)
        assert result == "world"

########NEW FILE########
__FILENAME__ = test_repository
from __future__ import absolute_import

from changes.vcs.git import GitVcs
from changes.vcs.hg import MercurialVcs
from changes.models import Repository, RepositoryBackend
from changes.testutils import TestCase


class GetVcsTest(TestCase):
    def test_git(self):
        repo = Repository(
            url='http://example.com/git-repo',
            backend=RepositoryBackend.git,
        )
        result = repo.get_vcs()
        assert type(result) == GitVcs

    def test_hg(self):
        repo = Repository(
            url='http://example.com/git-repo',
            backend=RepositoryBackend.hg,
        )
        result = repo.get_vcs()
        assert type(result) == MercurialVcs

    def test_unknown(self):
        repo = Repository(
            url='http://example.com/git-repo',
            backend=RepositoryBackend.unknown,
        )
        result = repo.get_vcs()
        assert result is None

########NEW FILE########
__FILENAME__ = test_testresult
from changes.constants import Result
from changes.models import ItemStat
from changes.models.testresult import TestResult, TestResultManager
from changes.testutils.cases import TestCase


class TestResultManagerTestCase(TestCase):
    def test_simple(self):
        from changes.models import TestCase

        build = self.create_build(self.project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        results = [
            TestResult(
                step=jobstep,
                name='test_bar',
                package='tests.changes.handlers.test_xunit',
                result=Result.failed,
                message='collection failed',
                duration=156,
            ),
            TestResult(
                step=jobstep,
                name='test_foo',
                package='tests.changes.handlers.test_coverage',
                result=Result.passed,
                message='foobar failed',
                duration=12,
                reruns=1,
            ),
        ]
        manager = TestResultManager(jobstep)
        manager.save(results)

        testcase_list = sorted(TestCase.query.all(), key=lambda x: x.name)

        assert len(testcase_list) == 2

        for test in testcase_list:
            assert test.job_id == job.id
            assert test.step_id == jobstep.id
            assert test.project_id == self.project.id

        assert testcase_list[0].name == 'tests.changes.handlers.test_coverage.test_foo'
        assert testcase_list[0].result == Result.passed
        assert testcase_list[0].message == 'foobar failed'
        assert testcase_list[0].duration == 12
        assert testcase_list[0].reruns == 1

        assert testcase_list[1].name == 'tests.changes.handlers.test_xunit.test_bar'
        assert testcase_list[1].result == Result.failed
        assert testcase_list[1].message == 'collection failed'
        assert testcase_list[1].duration == 156
        assert testcase_list[1].reruns is 0

        teststat = ItemStat.query.filter(
            ItemStat.name == 'test_count',
            ItemStat.item_id == jobstep.id,
        )[0]
        assert teststat.value == 2

        teststat = ItemStat.query.filter(
            ItemStat.name == 'test_failures',
            ItemStat.item_id == jobstep.id,
        )[0]
        assert teststat.value == 1

        teststat = ItemStat.query.filter(
            ItemStat.name == 'test_duration',
            ItemStat.item_id == jobstep.id,
        )[0]
        assert teststat.value == 168

        teststat = ItemStat.query.filter(
            ItemStat.name == 'test_rerun_count',
            ItemStat.item_id == jobstep.id,
        )[0]
        assert teststat.value == 1

########NEW FILE########
__FILENAME__ = test_task
from __future__ import absolute_import

import mock

from uuid import UUID

from changes.config import db
from changes.constants import Result, Status
from changes.models import Task
from changes.testutils import TestCase
from changes.queue.task import tracked_task


@tracked_task
def success_task(foo='bar'):
    pass


@tracked_task
def unfinished_task(foo='bar'):
    raise unfinished_task.NotFinished


@tracked_task
def error_task(foo='bar'):
    raise Exception


class DelayTest(TestCase):
    @mock.patch('changes.config.queue.delay')
    def test_simple(self, queue_delay):
        task_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')
        success_task.delay(
            foo='bar',
            task_id=task_id.hex,
            parent_task_id=parent_task_id.hex,
        )

        queue_delay.assert_called_once_with('success_task', kwargs={
            'foo': 'bar',
            'task_id': task_id.hex,
            'parent_task_id': parent_task_id.hex,
        }, countdown=5)

        task = Task.query.filter(
            Task.task_id == task_id,
            Task.task_name == 'success_task'
        ).first()

        assert task
        assert task.status == Status.queued
        assert task.parent_id == parent_task_id
        assert task.data == {
            'kwargs': {'foo': 'bar'},
        }


class DelayIfNeededTest(TestCase):
    @mock.patch('changes.config.queue.delay')
    def test_task_doesnt_exist(self, queue_delay):
        task_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')
        success_task.delay_if_needed(
            foo='bar',
            task_id=task_id.hex,
            parent_task_id=parent_task_id.hex,
        )

        queue_delay.assert_called_once_with('success_task', kwargs={
            'foo': 'bar',
            'task_id': task_id.hex,
            'parent_task_id': parent_task_id.hex,
        }, countdown=5)

        task = Task.query.filter(
            Task.task_id == task_id,
            Task.task_name == 'success_task'
        ).first()

        assert task
        assert task.status == Status.queued
        assert task.parent_id == parent_task_id
        assert task.data == {
            'kwargs': {'foo': 'bar'},
        }

    @mock.patch('changes.queue.task.TrackedTask.needs_requeued', mock.Mock(return_value=False))
    @mock.patch('changes.config.queue.delay')
    def test_task_does_exist_but_not_outdated(self, queue_delay):
        task_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        self.create_task(
            task_name='success_task',
            task_id=task_id,
            parent_id=parent_task_id,
            status=Status.in_progress,
        )

        success_task.delay_if_needed(
            foo='bar',
            task_id=task_id.hex,
            parent_task_id=parent_task_id.hex,
        )

        assert queue_delay.called is False

    @mock.patch('changes.queue.task.TrackedTask.needs_requeued', mock.Mock(return_value=True))
    @mock.patch('changes.config.queue.delay')
    def test_task_does_exist_and_needs_run(self, queue_delay):
        task_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        self.create_task(
            task_name='success_task',
            task_id=task_id,
            parent_id=parent_task_id,
            status=Status.in_progress,

        )

        success_task.delay_if_needed(
            foo='bar',
            task_id=task_id.hex,
            parent_task_id=parent_task_id.hex,
        )

        queue_delay.assert_called_once_with('success_task', kwargs={
            'foo': 'bar',
            'task_id': task_id.hex,
            'parent_task_id': parent_task_id.hex,
        }, countdown=5)


class VerifyAllChildrenTest(TestCase):
    def test_children_unfinished(self):
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        self.create_task(
            task_name='success_task',
            task_id=UUID('33846695b2774b29a71795a009e8168a'),
            parent_id=parent_task_id,
            status=Status.in_progress,
        )
        self.create_task(
            task_name='success_task',
            task_id=UUID('70e090f5c41e4175a9fd630464804bb0'),
            parent_id=parent_task_id,
            status=Status.finished,
        )

        success_task.task_id = parent_task_id.hex

        result = success_task.verify_all_children()
        assert result == Status.in_progress

    def test_children_finished(self):
        child_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        self.create_task(
            task_name='success_task',
            task_id=child_id,
            parent_id=parent_task_id,
            status=Status.finished,
        )

        success_task.task_id = parent_task_id.hex

        result = success_task.verify_all_children()
        assert result == Status.finished

    @mock.patch('changes.queue.task.TrackedTask.needs_requeued')
    @mock.patch('changes.config.queue.delay')
    def test_child_needs_run(self, queue_delay, needs_requeued):
        child_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        needs_requeued.return_value = True

        task = self.create_task(
            task_name='success_task',
            task_id=child_id,
            parent_id=parent_task_id,
            status=Status.in_progress,
            data={
                'kwargs': {'foo': 'bar'},
            },
        )

        success_task.task_id = parent_task_id.hex

        result = success_task.verify_all_children()

        assert result == Status.in_progress

        needs_requeued.assert_called_once_with(task)
        queue_delay.assert_called_once_with(
            'success_task', kwargs={
                'task_id': child_id.hex,
                'parent_task_id': parent_task_id.hex,
                'foo': 'bar',
            },
        )

    @mock.patch('changes.queue.task.TrackedTask.needs_expired')
    @mock.patch('changes.config.queue.delay')
    def test_child_is_expired(self, queue_delay, needs_expired):
        child_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        needs_expired.return_value = True

        task = self.create_task(
            task_name='success_task',
            task_id=child_id,
            parent_id=parent_task_id,
            status=Status.in_progress,
            data={
                'kwargs': {'foo': 'bar'},
            },
        )

        success_task.task_id = parent_task_id.hex

        result = success_task.verify_all_children()

        assert result == Status.finished

        db.session.refresh(task)

        needs_expired.assert_called_once_with(task)

        assert task.status == Status.finished
        assert task.result == Result.aborted


class RunTest(TestCase):
    @mock.patch('changes.config.queue.delay')
    @mock.patch('changes.config.queue.retry')
    def test_success(self, queue_retry, queue_delay):
        task_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        self.create_task(
            task_name='success_task',
            task_id=task_id,
            parent_id=parent_task_id,
        )

        success_task(
            foo='bar',
            task_id=task_id.hex,
            parent_task_id=parent_task_id.hex,
        )

        task = Task.query.filter(
            Task.task_id == task_id,
            Task.task_name == 'success_task'
        ).first()

        assert task
        assert task.status == Status.finished
        assert task.parent_id == parent_task_id

    @mock.patch('changes.config.queue.delay')
    @mock.patch('changes.config.queue.retry')
    def test_unfinished(self, queue_retry, queue_delay):
        task_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        self.create_task(
            task_name='unfinished_task',
            task_id=task_id,
            parent_id=parent_task_id,
        )

        unfinished_task(
            foo='bar',
            task_id=task_id.hex,
            parent_task_id=parent_task_id.hex,
        )

        task = Task.query.filter(
            Task.task_id == task_id,
            Task.task_name == 'unfinished_task'
        ).first()

        assert task
        assert task.status == Status.in_progress
        assert task.parent_id == parent_task_id

        queue_delay.assert_called_once_with(
            'unfinished_task',
            kwargs={
                'foo': 'bar',
                'task_id': task_id.hex,
                'parent_task_id': parent_task_id.hex,
            },
            countdown=5,
        )

    @mock.patch('changes.config.queue.delay')
    @mock.patch('changes.config.queue.retry')
    def test_error(self, queue_retry, queue_delay):
        task_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        self.create_task(
            task_name='error_task',
            task_id=task_id,
            parent_id=parent_task_id,
        )

        # force a commit as the error will cause a rollback
        db.session.commit()

        error_task(
            foo='bar',
            task_id=task_id.hex,
            parent_task_id=parent_task_id.hex,
        )

        task = Task.query.filter(
            Task.task_id == task_id,
            Task.task_name == 'error_task'
        ).first()

        assert task
        assert task.status == Status.in_progress
        assert task.num_retries == 1
        assert task.parent_id == parent_task_id

        queue_delay.assert_called_once_with(
            'error_task',
            kwargs={
                'foo': 'bar',
                'task_id': task_id.hex,
                'parent_task_id': parent_task_id.hex,
            },
            countdown=61,
        )

########NEW FILE########
__FILENAME__ = test_originfinder
from datetime import datetime

from changes.constants import Result, Status
from changes.testutils import TestCase
from changes.utils.originfinder import find_failure_origins


class FindFailureOriginsTest(TestCase):
    def test_simple(self):
        source = self.create_source(self.project)
        build_a = self.create_build(
            project=self.project, result=Result.passed, status=Status.finished,
            label='build a', date_created=datetime(2013, 9, 19, 22, 15, 22),
            source=source)
        job_a = self.create_job(build=build_a)
        build_b = self.create_build(
            project=self.project, result=Result.failed, status=Status.finished,
            label='build b', date_created=datetime(2013, 9, 19, 22, 15, 23),
            source=source)
        job_b = self.create_job(build=build_b)
        build_c = self.create_build(
            project=self.project, result=Result.failed, status=Status.finished,
            label='build c', date_created=datetime(2013, 9, 19, 22, 15, 24),
            source=source)
        job_c = self.create_job(build=build_c)
        build_d = self.create_build(
            project=self.project, result=Result.failed, status=Status.finished,
            label='build d', date_created=datetime(2013, 9, 19, 22, 15, 25),
            source=source)
        job_d = self.create_job(build=build_d)

        self.create_test(job_a, name='foo', result=Result.passed)
        self.create_test(job_a, name='bar', result=Result.passed)
        self.create_test(job_b, name='foo', result=Result.failed)
        self.create_test(job_b, name='bar', result=Result.passed)
        self.create_test(job_c, name='foo', result=Result.failed)
        self.create_test(job_c, name='bar', result=Result.failed)
        foo_d = self.create_test(job_d, name='foo', result=Result.failed)
        bar_d = self.create_test(job_d, name='bar', result=Result.failed)

        result = find_failure_origins(build_d, [foo_d, bar_d])
        assert result == {
            foo_d: build_b,
            bar_d: build_c
        }

########NEW FILE########
__FILENAME__ = test_trees
from changes.utils.trees import build_tree


def test_build_tree():
    test_names = [
        'foo.bar.bar',
        'foo.bar.biz',
        'foo.biz',
        'blah.brah',
        'blah.blah.blah',
    ]

    result = build_tree(test_names, min_children=2)

    assert sorted(result) == ['blah', 'foo']

    result = build_tree(test_names, min_children=2, parent='foo')

    assert sorted(result) == ['foo.bar', 'foo.biz']

    result = build_tree(test_names, min_children=2, parent='foo.biz')

    assert result == set()

########NEW FILE########
__FILENAME__ = test_base
from datetime import datetime

from changes.models import Revision
from changes.vcs.base import RevisionResult
from changes.testutils.cases import TestCase


class RevisionResultTestCase(TestCase):
    def test_simple(self):
        repo = self.create_repo()
        result = RevisionResult(
            id='c' * 40,
            author='Foo Bar <foo@example.com>',
            committer='Biz Baz <baz@example.com>',
            author_date=datetime(2013, 9, 19, 22, 15, 22),
            committer_date=datetime(2013, 9, 19, 22, 15, 23),
            message='Hello world!',
            parents=['a' * 40, 'b' * 40],

        )
        revision, created = result.save(repo)

        assert created

        assert type(revision) == Revision
        assert revision.repository == repo
        assert revision.sha == 'c' * 40
        assert revision.message == 'Hello world!'
        assert revision.author.name == 'Foo Bar'
        assert revision.author.email == 'foo@example.com'
        assert revision.committer.name == 'Biz Baz'
        assert revision.committer.email == 'baz@example.com'
        assert revision.parents == ['a' * 40, 'b' * 40]
        assert revision.date_created == datetime(2013, 9, 19, 22, 15, 22)
        assert revision.date_committed == datetime(2013, 9, 19, 22, 15, 23)

########NEW FILE########
__FILENAME__ = test_git
from __future__ import absolute_import

import os

from subprocess import check_call

from changes.testutils import TestCase
from changes.vcs.git import GitVcs


class GitVcsTest(TestCase):
    root = '/tmp/changes-git-test'
    path = '%s/clone' % (root,)
    remote_path = '%s/remote' % (root,)
    url = 'file://%s' % (remote_path,)

    def setUp(self):
        self.reset()
        self.addCleanup(check_call, 'rm -rf %s' % (self.root,), shell=True)

    def reset(self):
        check_call('rm -rf %s' % (self.root,), shell=True)
        check_call('mkdir -p %s %s' % (self.path, self.remote_path), shell=True)
        check_call('git init %s' % (self.remote_path,), shell=True)
        with open(os.path.join(self.remote_path, '.git/config'), 'w') as fp:
            fp.write('[user]\n')
            fp.write('email=foo@example.com\n')
            fp.write('name=Foo Bar\n')
        check_call('cd %s && touch FOO && git add FOO && git commit -m "test\nlol\n"' % (
            self.remote_path,
        ), shell=True)
        check_call('cd %s && touch BAR && git add BAR && git commit -m "biz\nbaz\n"' % (
            self.remote_path,
        ), shell=True)

    def get_vcs(self):
        return GitVcs(
            url=self.url,
            path=self.path
        )

    def test_simple(self):
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()
        revision = vcs.get_revision('HEAD')
        assert len(revision.id) == 40
        assert revision.message == 'biz\nbaz\n'
        assert revision.subject == 'biz'
        assert revision.author == 'Foo Bar <foo@example.com>'
        revisions = list(vcs.log())
        assert len(revisions) == 2
        assert revisions[0].subject == 'biz'
        assert revisions[0].message == 'biz\nbaz\n'
        assert revisions[0].author == 'Foo Bar <foo@example.com>'
        assert revisions[0].committer == 'Foo Bar <foo@example.com>'
        assert revisions[0].parents == [revisions[1].id]
        assert revisions[0].author_date == revisions[0].committer_date is not None
        assert revisions[0].branches == ['master']
        assert revisions[1].subject == 'test'
        assert revisions[1].message == 'test\nlol\n'
        assert revisions[1].author == 'Foo Bar <foo@example.com>'
        assert revisions[1].committer == 'Foo Bar <foo@example.com>'
        assert revisions[1].parents == []
        assert revisions[1].author_date == revisions[1].committer_date is not None
        assert revisions[1].branches == ['master']
        diff = vcs.export(revisions[0].id)
        assert diff == """diff --git a/BAR b/BAR
new file mode 100644
index 0000000..e69de29
"""

########NEW FILE########
__FILENAME__ = test_hg
from __future__ import absolute_import

import os
import pytest

from datetime import datetime
from subprocess import check_call

from changes.testutils import TestCase
from changes.vcs.hg import MercurialVcs


def has_current_hg_version():
    import pkg_resources

    try:
        mercurial = pkg_resources.get_distribution('mercurial')
    except pkg_resources.DistributionNotFound:
        return False

    return mercurial.parsed_version < pkg_resources.parse_version('2.4')


@pytest.mark.skipif(not has_current_hg_version(),
                    reason='missing or invalid mercurial version')
class MercurialVcsTest(TestCase):
    root = '/tmp/changes-hg-test'
    path = '%s/clone' % (root,)
    remote_path = '%s/remote' % (root,)
    url = 'file://%s' % (remote_path,)

    def setUp(self):
        self.reset()
        self.addCleanup(check_call, 'rm -rf %s' % (self.root,), shell=True)

    def reset(self):
        check_call('rm -rf %s' % (self.root,), shell=True)
        check_call('mkdir -p %s %s' % (self.path, self.remote_path), shell=True)
        check_call('hg init %s' % (self.remote_path,), shell=True)
        with open(os.path.join(self.remote_path, '.hg/hgrc'), 'w') as fp:
            fp.write('[ui]\n')
            fp.write('username=Foo Bar <foo@example.com>\n')
        check_call('cd %s && touch FOO && hg add FOO && hg commit -m "test\nlol"' % (
            self.remote_path,
        ), shell=True)
        check_call('cd %s && touch BAR && hg add BAR && hg commit -m "biz\nbaz"' % (
            self.remote_path,
        ), shell=True)

    def get_vcs(self):
        return MercurialVcs(
            url=self.url,
            path=self.path
        )

    def test_simple(self):
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()
        revision = vcs.get_revision('tip')
        assert len(revision.id) == 40
        assert revision.message == 'biz\nbaz'
        assert revision.subject == 'biz'
        assert revision.author == 'Foo Bar <foo@example.com>'
        revisions = list(vcs.log())
        assert len(revisions) == 2
        assert revisions[0].subject == 'biz'
        assert revisions[0].message == 'biz\nbaz'
        assert revisions[0].author == 'Foo Bar <foo@example.com>'
        assert revisions[0].committer == 'Foo Bar <foo@example.com>'
        assert revisions[0].parents == [revisions[1].id]
        assert type(revisions[0].author_date) is datetime
        assert revisions[0].author_date == revisions[0].committer_date is not None
        assert revisions[0].branches == ['default']
        assert revisions[1].subject == 'test'
        assert revisions[1].message == 'test\nlol'
        assert revisions[1].author == 'Foo Bar <foo@example.com>'
        assert revisions[1].committer == 'Foo Bar <foo@example.com>'
        assert revisions[1].parents == []
        assert revisions[1].author_date == revisions[1].committer_date is not None
        assert revisions[1].branches == ['default']
        diff = vcs.export(revisions[0].id)
        assert diff == """diff --git a/BAR b/BAR
new file mode 100644
"""

########NEW FILE########
__FILENAME__ = test_auth
import mock

from datetime import datetime
from flask import current_app
from oauth2client import GOOGLE_REVOKE_URI, GOOGLE_TOKEN_URI
from oauth2client.client import OAuth2Credentials

from changes.models import User
from changes.testutils import TestCase


class LoginViewTest(TestCase):
    def test_simple(self):
        resp = self.client.get('/auth/login/')
        assert resp.status_code == 302
        assert resp.headers['Location'] == \
            'https://accounts.google.com/o/oauth2/auth?scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.email&redirect_uri=http%3A%2F%2Flocalhost%2Fauth%2Fcomplete%2F&response_type=code&client_id=aaaaaaaaaaaa&access_type=offline'


class AuthorizedViewTest(TestCase):
    @mock.patch('changes.web.auth.OAuth2WebServerFlow.step2_exchange')
    def test_simple(self, step2_exchange):
        access_token = 'b' * 40
        refresh_token = 'c' * 40

        step2_exchange.return_value = OAuth2Credentials(
            access_token, current_app.config['GOOGLE_CLIENT_ID'],
            current_app.config['GOOGLE_CLIENT_SECRET'],
            refresh_token,
            datetime(2013, 9, 19, 22, 15, 22),
            GOOGLE_TOKEN_URI,
            'foo/1.0',
            revoke_uri=GOOGLE_REVOKE_URI,
            id_token={
                'hd': 'example.com',
                'email': 'foo@example.com',
            },
        )

        resp = self.client.get('/auth/complete/?code=abc')

        step2_exchange.assert_called_once_with('abc')

        assert resp.status_code == 302
        assert resp.headers['Location'] == 'http://localhost/'

        user = User.query.filter(
            User.email == 'foo@example.com',
        ).first()

        assert user


class LogoutViewTest(TestCase):
    def test_simple(self):
        resp = self.client.get('/auth/logout/')
        assert resp.status_code == 302
        assert resp.headers['Location'] == 'http://localhost/'

########NEW FILE########
