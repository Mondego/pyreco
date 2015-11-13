__FILENAME__ = fabfile
"""
Common tools for deploy run shell and the like.
"""

import os
from string import Template
from urllib import urlencode

from fabric.api import lcd, task, local, put, env


@task
def pep8():
    """Run Pep8"""
    local("pep8 july --exclude='*migrations*','*static*'")


@task
def test(coverage='False', skip_js='False'):
    """Run the test suite"""
    if coverage != 'False':
        local("rm -rf htmlcov")
        local("coverage run --include='july*' --omit='*migration*' manage.py test")
        local("coverage html")
    else:
        local("python manage.py test july people game")
    if skip_js == 'False':
        with lcd('assets'):
            local('node_modules/grunt-cli/bin/grunt jasmine')
    pep8()


@task
def load(email=None):
    """Manually send a POST to api endpoints."""
    if not email:
        print "You must provide an email address 'fab load:me@foo.com'"
        return

    github = []
    bitbucket = []
    for json_file in os.listdir('data'):
        if json_file.startswith('github'):
            github.append(os.path.join('data', json_file))
        elif json_file.startswith('bitbucket'):
            bitbucket.append(os.path.join('data', json_file))

    for json_file in github:
        with open(json_file) as post:
            p = Template(post.read()).substitute({'__EMAIL__': email})
            payload = urlencode({'payload': p})
            local('curl http://localhost:8000/api/v1/github -s -d %s' % payload)

    for json_file in bitbucket:
        with open(json_file) as post:
            p = Template(post.read()).substitute({'__EMAIL__': email})
            payload = urlencode({'payload': p})
            local('curl http://localhost:8000/api/v1/bitbucket -s -d %s' % payload)


@task
def install():
    """Install the node_modules dependencies"""
    local('git submodule update --init')
    with lcd('assets'):
        local('npm install')


@task
def watch():
    """Grunt watch development files"""
    with lcd('assets'):
        local('node_modules/grunt-cli/bin/grunt concat less:dev watch')


@task
def compile():
    """Compile assets for production."""
    with lcd('assets'):
        local('node_modules/grunt-cli/bin/grunt less:prod uglify')


@task
def staging(user='rmyers'):
    env.hosts = ['january.julython.org']
    env.user = user


@task
def deploy():
    """Deploy to production"""
    compile()
    local("tar -czvf july.tar.gz"
          " --exclude '\.*'"
          " --exclude '*.pyc'"
          " --exclude 'assets*'"
          " --exclude 'htmlcov*'"
          " --exclude '*.db'"
          " --exclude '*.tar.gz'"
          " *")
    put('july.tar.gz', '/tmp/')

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from july.models import User
from social_auth.models import UserSocialAuth


class AuthInline(admin.TabularInline):
    model = UserSocialAuth


def purge_commits(modeladmin, request, queryset):
    for obj in queryset:
        obj.commit_set.all().delete()
purge_commits.short_description = "Purge Commits"


class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'location', 'team']
    search_fields = ['username', 'email']
    inlines = [AuthInline]
    raw_id_fields = ['projects', 'location', 'team']
    list_filter = ['is_active', 'is_superuser']
    actions = [purge_commits]


admin.site.register(User, UserAdmin)

########NEW FILE########
__FILENAME__ = api

from collections import defaultdict
import json
import logging
import re
import urlparse
import requests
from os.path import splitext

from django.core.urlresolvers import reverse
from django import http
from django.template.defaultfilters import date
from django.views.generic.base import View
from django.views.decorators.csrf import csrf_exempt
from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from iso8601 import parse_date
from tastypie.resources import ModelResource
from tastypie.resources import ALL
from tastypie.resources import ALL_WITH_RELATIONS
from tastypie.utils import trailing_slash
from tastypie import fields

from july.people.models import Commit, Project, Location, Team, Language
from july.game.models import Game, Board
from july.models import User

EMAIL_MATCH = re.compile('<(.+?)>')
HOOKS_MATCH = re.compile('repos/[^/]+/[^/]+/hooks.*')


def sub_resource(request, obj, resource, queryset):
    """Return a serializable list of child resources."""
    child = resource()
    sorted_objects = child.apply_sorting(
        queryset,
        options=request.GET)

    paginator = child._meta.paginator_class(
        request.GET, sorted_objects, resource_uri=request.path,
        limit=child._meta.limit, max_limit=child._meta.max_limit,
        collection_name=child._meta.collection_name)
    to_be_serialized = paginator.page()

    # Dehydrate the bundles in preparation for serialization.
    bundles = []

    for ob in to_be_serialized[child._meta.collection_name]:
        bundle = child.build_bundle(obj=ob, request=request)
        bundle.data['points'] = ob.points
        bundles.append(child.full_dehydrate(bundle))

    to_be_serialized[child._meta.collection_name] = bundles
    to_be_serialized = child.alter_list_data_to_serialize(
        request, to_be_serialized)
    return to_be_serialized


class UserResource(ModelResource):

    class Meta:
        queryset = User.objects.filter(is_active=True)
        excludes = ['password', 'email', 'is_superuser', 'is_staff',
                    'is_active']

    def get_projects(self, request, **kwargs):
        basic_bundle = self.build_bundle(request=request)
        obj = self.cached_obj_get(
            bundle=basic_bundle,
            **self.remove_api_resource_names(kwargs))

        to_be_serialized = sub_resource(
            request, obj, ProjectResource, obj.projects.all())
        return self.create_response(request, to_be_serialized)

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/projects%s$" % (
                self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_projects'), name="api_user_projects"),
        ]


class ProjectResource(ModelResource):

    class Meta:
        queryset = Project.objects.all()
        allowed_methods = ['get']
        filtering = {
            'user': ALL_WITH_RELATIONS,
            'locations': ALL,
            'teams': ALL
        }

    def get_users(self, request, **kwargs):
        basic_bundle = self.build_bundle(request=request)
        obj = self.cached_obj_get(
            bundle=basic_bundle,
            **self.remove_api_resource_names(kwargs))

        to_be_serialized = sub_resource(
            request, obj, UserResource, obj.user_set.all())
        return self.create_response(request, to_be_serialized)

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/users%s$" % (
                self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_users'), name="api_project_users"),
        ]


class LargeBoardResource(ModelResource):
    project = fields.ForeignKey(ProjectResource, 'project',
                                blank=True, null=True, full=True)

    class Meta:
        game = Game.active_or_latest()
        # TODO: make this configurable!
        queryset = Board.objects.filter(
            game=game, project__watchers__gte=100,
            project__active=True).select_related('project')


class MediumBoardResource(ModelResource):
    project = fields.ForeignKey(ProjectResource, 'project',
                                blank=True, null=True, full=True)

    class Meta:
        game = Game.active_or_latest()
        # TODO: make this configurable!
        queryset = Board.objects.filter(
            game=game, project__watchers__gte=10,
            project__watchers__lt=100,
            project__active=True).select_related('project')


class SmallBoardResource(ModelResource):
    project = fields.ForeignKey(ProjectResource, 'project',
                                blank=True, null=True, full=True)

    class Meta:
        game = Game.active_or_latest()
        # TODO: make this configurable!
        queryset = Board.objects.filter(
            game=game, project__watchers__lt=10,
            project__active=True).select_related('project')


class LocationResource(ModelResource):

    class Meta:
        queryset = Location.objects.filter(approved=True)
        allowed_methods = ['get']
        filtering = {
            'name': ['istartswith', 'exact', 'icontains'],
        }


class TeamResource(ModelResource):

    class Meta:
        queryset = Team.objects.filter(approved=True)
        allowed_methods = ['get']
        filtering = {
            'name': ['istartswith', 'exact', 'icontains'],
        }


class LanguageResource(ModelResource):

    class Meta:
        queryset = Language.objects.all()


class CommitResource(ModelResource):
    user = fields.ForeignKey(UserResource, 'user', blank=True, null=True)
    project = fields.ForeignKey(ProjectResource, 'project',
                                blank=True, null=True)

    class Meta:
        queryset = Commit.objects.all().select_related(
            'user', 'project')
        allowed_methods = ['get']
        filtering = {
            'user': ALL_WITH_RELATIONS,
            'project': ALL_WITH_RELATIONS,
            'timestamp': ['exact', 'range', 'gt', 'lt'],
        }

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/calendar%s$" % (
                self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_calendar'),
                name="api_get_calendar"),
        ]

    def get_calendar(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.throttle_check(request)
        filters = {}

        game = Game.active_or_latest()
        username = request.GET.get('username')
        if username:
            filters['user__username'] = username

        # user = kwargs.get('user', None)
        calendar = Commit.calendar(game=game, **filters)
        return self.create_response(request, calendar)

    def gravatar(self, email):
        """Return a link to gravatar image."""
        url = 'http://www.gravatar.com/avatar/%s?s=48'
        from hashlib import md5
        email = email.strip().lower()
        try:
            hashed = md5(email).hexdigest()
        except:
            hashed = 'unicode_error'
        return url % hashed

    def dehydrate(self, bundle):
        email = bundle.data.pop('email')
        gravatar = self.gravatar(email)
        bundle.data['project_name'] = bundle.obj.project.name
        bundle.data['project_url'] = reverse('project-details',
                                             args=[bundle.obj.project.slug])
        bundle.data['username'] = getattr(bundle.obj.user, 'username', None)
        # Format the date properly using django template filter
        bundle.data['timestamp'] = date(bundle.obj.timestamp, 'c')
        bundle.data['picture_url'] = getattr(bundle.obj.user,
                                             'picture_url',
                                             gravatar)
        bundle.data['files'] = bundle.obj.files
        return bundle


class LoginRequiredMixin(object):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class JSONMixin(object):

    def respond_json(self, data, **kwargs):
        content = json.dumps(data)
        resp = http.HttpResponse(content,
                                 content_type='application/json',
                                 **kwargs)
        resp['Access-Control-Allow-Origin'] = '*'
        return resp


class GithubAPIHandler(LoginRequiredMixin, View):

    def get(self, request, path):
        github = request.user.github
        if github is None:
            return http.HttpResponseForbidden()
        token = github.extra_data.get('access_token', '')
        headers = {'Authorization': 'token %s' % token}
        url = 'https://api.github.com/%s' % path
        resp = requests.get(url, params=request.GET, headers=headers)
        if resp.status_code == 404:
            return http.HttpResponseNotFound()
        resp.raise_for_status()
        return http.HttpResponse(resp.text, content_type='application/json')

    def post(self, request, path):
        github = request.user.github
        if github is None:
            logging.error("User does not have a github account")
            return http.HttpResponseForbidden()
        # only allow actions on hooks
        if not HOOKS_MATCH.match(path):
            logging.error("Bad path: %s", path)
            return http.HttpResponseForbidden()
        action = self.request.POST.get('action')
        if action == "add":
            data = {
                "name": "web",
                "active": True,
                "events": ["push"],
                "config": {
                    "url": "http://www.julython.org/api/v1/github",
                    "content_type": "form",
                    "insecure_ssl": "1"
                }
            }
        elif action == "test":
            data = ""
        token = github.extra_data.get('access_token', '')
        headers = {'Authorization': 'token %s' % token}
        url = 'https://api.github.com/%s' % path
        resp = requests.post(
            url, data=json.dumps(data),
            params=request.GET, headers=headers)
        if resp.status_code == 404:
            return http.HttpResponseNotFound()
        resp.raise_for_status()
        return http.HttpResponse(resp.text, content_type='application/json')


def add_language(file_dict):
    """Parse a filename for the language.

    >>> d = {"file": "somefile.py", "type": "added"}
    >>> add_language(d)
    {"file": "somefile.py", "type": "added", "language": "Python"}
    """
    name = file_dict.get('file', '')
    language = None
    path, ext = splitext(name.lower())
    type_map = {
        #
        # C/C++
        #
        '.c': 'C/C++',
        '.cc': 'C/C++',
        '.cpp': 'C/C++',
        '.h': 'C/C++',
        '.hpp': 'C/C++',
        '.so': 'C/C++',
        #
        # C#
        #
        '.cs': 'C#',
        #
        # Clojure
        #
        '.clj': 'Clojure',
        #
        # Documentation
        #
        '.txt': 'Documentation',
        '.md': 'Documentation',
        '.rst': 'Documentation',
        '.hlp': 'Documentation',
        '.pdf': 'Documentation',
        '.man': 'Documentation',
        #
        # Erlang
        #
        '.erl': 'Erlang',
        #
        # Fortran
        #
        '.f': 'Fortran',
        '.f77': 'Fortran',
        #
        # Go
        #
        '.go': 'Golang',
        #
        # Groovy
        #
        '.groovy': 'Groovy',
        #
        # html/css/images
        #
        '.xml': 'html/css',
        '.html': 'html/css',
        '.htm': 'html/css',
        '.css': 'html/css',
        '.sass': 'html/css',
        '.less': 'html/css',
        '.scss': 'html/css',
        '.jpg': 'html/css',
        '.gif': 'html/css',
        '.png': 'html/css',
        '.jpeg': 'html/css',
        #
        # Java
        #
        '.class': 'Java',
        '.ear': 'Java',
        '.jar': 'Java',
        '.java': 'Java',
        '.war': 'Java',
        #
        # JavaScript
        #
        '.js': 'JavaScript',
        '.json': 'JavaScript',
        '.coffee': 'CoffeeScript',
        '.litcoffee': 'CoffeeScript',
        '.dart': 'Dart',
        #
        # Lisp
        #
        '.lisp': 'Common Lisp',
        #
        # Lua
        #
        '.lua': 'Lua',
        #
        # Objective-C
        #
        '.m': 'Objective-C',
        #
        # Perl
        #
        '.pl': 'Perl',
        #
        # PHP
        #
        '.php': 'PHP',
        #
        # Python
        #
        '.py': 'Python',
        '.pyc': 'Python',
        '.pyd': 'Python',
        '.pyo': 'Python',
        '.pyx': 'Python',
        '.pxd': 'Python',
        #
        # R
        #
        '.r': 'R',
        #
        # Ruby
        #
        '.rb': 'Ruby',
        #
        # Scala
        #
        '.scala': 'Scala',
        #
        # Scheme
        #
        '.scm': 'Scheme',
        '.scheme': 'Scheme',
        #
        # No Extension
        #
        '': '',
    }
    # Common extentionless files
    doc_map = {
        'license': 'Legalese',
        'copyright': 'Legalese',
        'changelog': 'Documentation',
        'contributing': 'Documentation',
        'readme': 'Documentation',
        'makefile': 'Build Tools',
    }
    if ext == '':
        language = doc_map.get(path)
    else:
        language = type_map.get(ext)
    file_dict['language'] = language
    return file_dict


class PostCallbackHandler(View, JSONMixin):

    def parse_commits(self, commits, project):
        """
        Takes a list of raw commit data and returns a dict of::

            {'email': [list of parsed commits]}

        """
        commit_dict = defaultdict(list)
        for k, v in [self._parse_commit(data, project) for data in commits]:
            # Did we not actual parse a commit?
            if v is None:
                continue
            commit_dict[k].append(v)

        return commit_dict

    def _parse_repo(self, repository):
        """Parse a repository."""
        raise NotImplementedError("Subclasses must define this")

    def _parse_commit(self, commit, project):
        """Parse a single commit."""
        raise NotImplementedError("Subclasses must define this")

    def parse_payload(self, request):
        """
        Hook for turning post data into payload.
        """
        payload = request.POST.get('payload')
        return payload

    def _publish_commits(self, commits):
        """Publish the commits to the real time channel."""
        host = self.request.META.get('HTTP_HOST', 'localhost:8000')
        url = 'http://%s/events/pub/' % host
        for commit in commits[:3]:
            try:
                resource = CommitResource()
                bundle = resource.build_bundle(obj=commit)
                # Make the timestamp a date object (again?)
                bundle.obj.timestamp = parse_date(bundle.obj.timestamp)
                dehydrated = resource.full_dehydrate(bundle)
                serialized = resource.serialize(
                    None, dehydrated, format='application/json')
                if commit.user:
                    requests.post(url + 'user-%s' % commit.user.id, serialized)
                requests.post(url + 'project-%s' % commit.project.id,
                              serialized)
                requests.post(url + 'global', serialized)
            except:
                logging.exception("Error publishing message")

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(PostCallbackHandler, self).dispatch(*args, **kwargs)

    def post(self, request):
        payload = self.parse_payload(request)
        if not payload:
            return http.HttpResponseBadRequest()
        try:
            data = json.loads(payload)
        except:
            logging.exception("Unable to serialize POST")
            return http.HttpResponseBadRequest()

        commit_data = data.get('commits', [])

        repo = self._parse_repo(data)
        logging.info(repo)
        project = Project.create(**repo)

        if project is None:
            logging.error("Project Disabled")
            # TODO: discover what response codes are helpful to github
            # and bitbucket
            return self.respond_json({'error': 'abuse'}, status=202)

        commit_dict = self.parse_commits(commit_data, project)
        total_commits = []
        for email, commits in commit_dict.iteritems():
            # TODO: run this in a task queue?
            cmts = Commit.create_by_email(email, commits, project=project)
            total_commits += cmts

        status = 201 if len(total_commits) else 200

        self._publish_commits(total_commits)

        return self.respond_json(
            {'commits': [c.hash for c in total_commits]},
            status=status)


class BitbucketHandler(PostCallbackHandler):
    """
    Take a POST from bitbucket in the format::

        payload=>"{
            "canon_url": "https://bitbucket.org",
            "commits": [
                {
                    "author": "marcus",
                    "branch": "featureA",
                    "files": [
                        {
                            "file": "somefile.py",
                            "type": "modified"
                        }
                    ],
                    "message": "Added some featureA things",
                    "node": "d14d26a93fd2",
                    "parents": [
                        "1b458191f31a"
                    ],
                    "raw_author": "Marcus Bertrand <marcus@somedomain.com>",
                    "raw_node": "d14d26a93fd28d3166fa81c0cd3b6f339bb95bfe",
                    "revision": 3,
                    "size": -1,
                    "timestamp": "2012-05-30 06:07:03",
                    "utctimestamp": "2012-05-30 04:07:03+00:00"
                }
            ],
            "repository": {
                "absolute_url": "/marcus/project-x/",
                "fork": false,
                "is_private": true,
                "name": "Project X",
                "owner": "marcus",
                "scm": "hg",
                "slug": "project-x",
                "website": ""
            },
            "user": "marcus"
        }"
    """

    def _parse_repo(self, data):
        """Returns a dict suitable for creating a project.

        "repository": {
                "absolute_url": "/marcus/project-x/",
                "fork": false,
                "is_private": true,
                "name": "Project X",
                "owner": "marcus",
                "scm": "hg",
                "slug": "project-x",
                "website": ""
            }
        """
        if not isinstance(data, dict):
            raise AttributeError("Expected a dict object")

        repo = data.get('repository')
        canon_url = data.get('canon_url', '')

        abs_url = repo.get('absolute_url', '')
        if not abs_url.startswith('http'):
            abs_url = urlparse.urljoin(canon_url, abs_url)

        result = {
            'url': abs_url,
            'description': repo.get('website') or '',
            'name': repo.get('name'),
            'service': 'bitbucket'
        }

        fork = repo.get('fork', False)
        if fork:
            result['forked'] = True
        else:
            result['forked'] = False

        return result

    def _parse_email(self, raw_email):
        """
        Takes a raw email like: 'John Doe <joe@example.com>'

        and returns 'joe@example.com'
        """
        m = EMAIL_MATCH.search(raw_email)
        if m:
            return m.group(1)
        return ''

    @staticmethod
    def parse_extensions(data):
        """Returns a list of file extensions in the commit data"""
        file_dicts = data.get('files')
        extensions = [
            ext[1:] for root, ext in
            [splitext(file_dict['file']) for file_dict in file_dicts]]
        return extensions

    def _parse_commit(self, data, project):
        """Parse a single commit.

        Example::

            {
                "author": "marcus",
                "branch": "featureA",
                "files": [
                    {
                        "file": "somefile.py",
                        "type": "modified"
                    }
                ],
                "message": "Added some featureA things",
                "node": "d14d26a93fd2",
                "parents": [
                    "1b458191f31a"
                ],
                "raw_author": "Marcus Bertrand <marcus@somedomain.com>",
                "raw_node": "d14d26a93fd28d3166fa81c0cd3b6f339bb95bfe",
                "revision": 3,
                "size": -1,
                "timestamp": "2012-05-30 06:07:03",
                "utctimestamp": "2012-05-30 04:07:03+00:00"
            }
        """
        if not isinstance(data, dict):
            raise AttributeError("Expected a dict object")

        email = self._parse_email(data.get('raw_author'))
        files = map(add_language, data.get('files', []))

        url = urlparse.urljoin(project.url, 'commits/%s' % data['raw_node'])

        commit_data = {
            'hash': data['raw_node'],
            'email': email,
            'author': data.get('author'),
            'name': data.get('author'),
            'message': data.get('message'),
            'timestamp': data.get('utctimestamp'),
            'url': data.get('url', url),
            'files': files,
        }
        return email, commit_data


class GithubHandler(PostCallbackHandler):
    """
    Takes a POST response from github in the following format::

        payload=>"{
            "before": "5aef35982fb2d34e9d9d4502f6ede1072793222d",
            "repository": {
                "url": "http://github.com/defunkt/github",
                "name": "github",
                "description": "You're lookin' at it.",
                "watchers": 5,
                "forks": 2,
                "private": 1,
                "owner": {
                    "email": "chris@ozmm.org",
                    "name": "defunkt"
                }
            },
            "commits": [
            {
              "id": "41a212ee83ca127e3c8cf465891ab7216a705f59",
              "url": "http://github.com/defunkt/github/commit/41a212ef59",
              "author": {
                "email": "chris@ozmm.org",
                "name": "Chris Wanstrath"
              },
              "message": "okay i give in",
              "timestamp": "2008-02-15T14:57:17-08:00",
              "added": ["filepath.rb"]
            },
            {
              "id": "de8251ff97ee194a289832576287d6f8ad74e3d0",
              "url": "http://github.com/defunkt/github/commit/de8f8ae3d0",
              "author": {
                "email": "chris@ozmm.org",
                "name": "Chris Wanstrath"
              },
              "message": "update pricing a tad",
              "timestamp": "2008-02-15T14:36:34-08:00"
            }
            ],
            "after": "de8251ff97ee194a289832576287d6f8ad74e3d0",
            "ref": "refs/heads/master"
        }"
    """

    def _parse_repo(self, data):
        """Returns a dict suitable for creating a project."""
        if not isinstance(data, dict):
            raise AttributeError("Expected a dict object")

        data = data.get('repository')

        return {
            'url': data['url'],
            'description': data.get('description', ''),
            'name': data.get('name'),
            'forks': data.get('forks', 0),
            'watchers': data.get('watchers', 0),
            'service': 'github',
            'repo_id': data.get('id')
        }

    def _parse_files(self, data):
        """Make files look like bitbuckets json list."""
        def wrapper(key, data):
            return [{"file": f, "type": key} for f in data.get(key, [])]

        added = wrapper('added', data)
        modified = wrapper('modified', data)
        removed = wrapper('removed', data)
        return added + modified + removed

    def _parse_commit(self, data, project):
        """Return a tuple of (email, dict) to simplify commit creation.

        Raw commit data::

            {
              "id": "41a212ee83ca127e3c8cf465891ab7216a705f59",
              "url": "http://github.com/defunkt/github/commit/41a212ee83ca",
              "author": {
                "email": "chris@ozmm.org",
                "name": "Chris Wanstrath"
              },
              "message": "okay i give in",
              "timestamp": "2008-02-15T14:57:17-08:00",
              "added": ["filepath.rb"]
            },
        """
        if not isinstance(data, dict):
            raise AttributeError("Expected a dict object")

        author = data.get('author', {})
        email = author.get('email', '')
        name = author.get('name', '')
        files = map(add_language, self._parse_files(data))

        commit_data = {
            'hash': data['id'],
            'url': data['url'],
            'email': email,
            'name': name,
            'message': data['message'],
            'timestamp': data['timestamp'],
            'files': files,
        }
        return email, commit_data

########NEW FILE########
__FILENAME__ = github
import logging

from social_auth.backends.contrib import github


class GithubBackend(github.GithubBackend):
    ID_KEY = 'login'

    def get_user_details(self, response):
        """Return user details from Github account"""
        data = {
            'username': response.get('login'),
            'email': response.get('email') or '',
            'fullname': response.get('name', 'Secret Agent'),
            'last_name': '',
            'url': response.get('blog', ''),
            'description': response.get('bio', ''),
            'picture_url': response.get('avatar_url', '')
        }

        try:
            names = data['fullname'].split(' ')
            data['first_name'], data['last_name'] = names[0], names[-1]
        except:
            data['first_name'] = data['fullname']

        logging.debug("Github Auth: %s", data)
        return data


# Backend definition
BACKENDS = {
    'github': github.GithubAuth,
}

########NEW FILE########
__FILENAME__ = social
import logging

from social_auth.models import UserSocialAuth

from july.people.models import Commit
from july.game.models import Player


def social_auth_user(backend, uid, user=None, *args, **kwargs):
    """Return UserSocialAuth account for backend/uid pair or None if it
    doesn't exists.

    Raise AuthAlreadyAssociated if UserSocialAuth entry belongs to another
    user.
    """
    social_user = UserSocialAuth.get_social_auth(backend.name, uid)
    if social_user:
        if user and social_user.user != user:
            merge_users(user, social_user.user, commit=True)
        elif not user:
            user = social_user.user
    return {'social_user': social_user,
            'user': user,
            'new_association': False}


def merge_users(new_user, old_user, commit=False):
    """
    Merge the users together.

    Args:
      * new_user: User to move items to.
      * old_user: User to move items from.
      * commit: (bool) Actually preform the operations.
    """
    logging.info("Merging %s (%s) into: %s (%s)", old_user, old_user.id,
                 new_user, new_user.id)
    if not commit:
        for o in UserSocialAuth.objects.filter(user=old_user):
            logging.info("Found Auth: %s", o)
        logging.info("Found %s commits",
                     Commit.objects.filter(user=old_user).count())
        logging.info("Found %s projects", old_user.projects.count())
        for p in Player.objects.filter(user=old_user):
            logging.info("Player: %s, %s points: %s", p, p.game, p.points)
        logging.info("Merge player by adding --commit")
    else:
        UserSocialAuth.objects.filter(user=old_user).update(user=new_user)
        for commit in Commit.objects.filter(user=old_user):
            commit.user = new_user
            # Run save individually to trigger the post save hooks.
            commit.save()
        for project in old_user.projects.all():
            new_user.projects.add(project)
        old_user.is_active = False
        old_user.save()
        new_user.save()
        logging.info("Merged")

########NEW FILE########
__FILENAME__ = twitter
__author__ = 'Kevin'

import logging

from social_auth.backends import twitter


class TwitterBackend(twitter.TwitterBackend):
    """Twitter OAuth authentication backend"""

    def get_user_details(self, response):
        """Return user details from Twitter account"""
        data = {
            'username': response['screen_name'],
            'email': '',  # not supplied
            'fullname': response['name'],
            'last_name': '',
            'url': response.get('url', ''),
            'description': response.get('description', ''),
            'picture_url': response.get('profile_image_url', ''),
        }
        try:
            name = response['name']
            data['first_name'], data['last_name'] = name.split(' ', 1)
        except:
            data['first_name'] = response['name']

        logging.debug("Twitter auth: %s", data)
        return data


# Backend definition
BACKENDS = {
    'twitter': twitter.TwitterAuth,
}

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import UserCreationForm
from django.contrib.sites.models import get_current_site
from django.core.mail import send_mail
from django.template import loader
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from july.models import User


class RegistrationForm(UserCreationForm):

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username',)

    def clean_username(self):
        # Since User.username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        username = self.cleaned_data["username"]
        try:
            User._default_manager.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages['duplicate_username'])


class AbuseForm(forms.Form):
    desc = forms.CharField(widget=forms.Textarea, required=True)
    url = forms.URLField(required=True)


class PasswordResetForm(forms.Form):
    email = forms.EmailField(max_length=254)

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None, html_email_template_name=None):
        """
        Generates a one-use only link for resetting password and sends to the
        user.
        """
        email = self.cleaned_data["email"]
        user = User.get_by_auth_id("email:%s" % email)
        if not user:
            return
        current_site = get_current_site(request)
        site_name = current_site.name
        domain = current_site.domain
        c = {
            'email': email,
            'domain': domain,
            'site_name': site_name,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'user': user,
            'token': token_generator.make_token(user),
            'protocol': 'https' if use_https else 'http',
        }
        subject = loader.render_to_string(subject_template_name, c)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        mail = loader.render_to_string(email_template_name, c)

        if html_email_template_name:
            html_email = loader.render_to_string(html_email_template_name, c)
        else:
            html_email = None
        send_mail(subject, mail, from_email, [email])

########NEW FILE########
__FILENAME__ = admin

from django.contrib import admin

from july.game.models import Game, Player, Board, LanguageBoard


class GameAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'start', 'end']


class PlayerAdmin(admin.ModelAdmin):
    list_display = ['user', 'game', 'points']
    list_filter = ['game']
    raw_id_fields = ['user', 'boards']


class BoardAdmin(admin.ModelAdmin):
    list_display = ['project', 'game', 'points']
    list_filter = ['game']
    raw_id_fields = ['project']


class LanguageBoardAdmin(admin.ModelAdmin):
    list_display = ['language', 'game', 'points']
    list_filter = ['game']

admin.site.register(Game, GameAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(Board, BoardAdmin)
admin.site.register(LanguageBoard, LanguageBoardAdmin)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Game'
        db.create_table(u'game_game', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('start', self.gf('django.db.models.fields.DateTimeField')()),
            ('end', self.gf('django.db.models.fields.DateTimeField')()),
            ('commit_points', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('project_points', self.gf('django.db.models.fields.IntegerField')(default=10)),
            ('problem_points', self.gf('django.db.models.fields.IntegerField')(default=5)),
        ))
        db.send_create_signal(u'game', ['Game'])

        # Adding model 'Player'
        db.create_table(u'game_player', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['game.Game'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['july.User'])),
            ('points', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'game', ['Player'])

        # Adding M2M table for field boards on 'Player'
        db.create_table(u'game_player_boards', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('player', models.ForeignKey(orm[u'game.player'], null=False)),
            ('board', models.ForeignKey(orm[u'game.board'], null=False))
        ))
        db.create_unique(u'game_player_boards', ['player_id', 'board_id'])

        # Adding model 'Board'
        db.create_table(u'game_board', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['game.Game'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['people.Project'])),
            ('points', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'game', ['Board'])


    def backwards(self, orm):
        # Deleting model 'Game'
        db.delete_table(u'game_game')

        # Deleting model 'Player'
        db.delete_table(u'game_player')

        # Removing M2M table for field boards on 'Player'
        db.delete_table('game_player_boards')

        # Deleting model 'Board'
        db.delete_table(u'game_board')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'game.board': {
            'Meta': {'ordering': "['-points']", 'object_name': 'Board'},
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['game.Game']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'points': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Project']"})
        },
        u'game.game': {
            'Meta': {'ordering': "['-end']", 'object_name': 'Game'},
            'boards': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['people.Project']", 'through': u"orm['game.Board']", 'symmetrical': 'False'}),
            'commit_points': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'players': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['july.User']", 'through': u"orm['game.Player']", 'symmetrical': 'False'}),
            'problem_points': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'project_points': ('django.db.models.fields.IntegerField', [], {'default': '10'}),
            'start': ('django.db.models.fields.DateTimeField', [], {})
        },
        u'game.player': {
            'Meta': {'ordering': "['-points']", 'object_name': 'Player'},
            'boards': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['game.Board']", 'symmetrical': 'False'}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['game.Game']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'points': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['july.User']"})
        },
        u'july.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'location_members'", 'null': 'True', 'to': u"orm['people.Location']"}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'picture_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'projects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'team_members'", 'null': 'True', 'to': u"orm['people.Team']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'people.location': {
            'Meta': {'object_name': 'Location'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.project': {
            'Meta': {'object_name': 'Project'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'forked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'parent_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.team': {
            'Meta': {'object_name': 'Team'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['game']
########NEW FILE########
__FILENAME__ = 0002_auto__add_languageboard
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'LanguageBoard'
        db.create_table(u'game_languageboard', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['game.Game'])),
            ('points', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('language', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['people.Language'])),
        ))
        db.send_create_signal(u'game', ['LanguageBoard'])


    def backwards(self, orm):
        # Deleting model 'LanguageBoard'
        db.delete_table(u'game_languageboard')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'game.board': {
            'Meta': {'ordering': "['-points']", 'object_name': 'Board'},
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['game.Game']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'points': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Project']"})
        },
        u'game.game': {
            'Meta': {'ordering': "['-end']", 'object_name': 'Game'},
            'boards': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['people.Project']", 'through': u"orm['game.Board']", 'symmetrical': 'False'}),
            'commit_points': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language_boards': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['people.Language']", 'through': u"orm['game.LanguageBoard']", 'symmetrical': 'False'}),
            'players': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['july.User']", 'through': u"orm['game.Player']", 'symmetrical': 'False'}),
            'problem_points': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'project_points': ('django.db.models.fields.IntegerField', [], {'default': '10'}),
            'start': ('django.db.models.fields.DateTimeField', [], {})
        },
        u'game.languageboard': {
            'Meta': {'ordering': "['-points']", 'object_name': 'LanguageBoard'},
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['game.Game']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Language']"}),
            'points': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'game.player': {
            'Meta': {'ordering': "['-points']", 'object_name': 'Player'},
            'boards': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['game.Board']", 'symmetrical': 'False'}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['game.Game']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'points': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['july.User']"})
        },
        u'july.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'location_members'", 'null': 'True', 'to': u"orm['people.Location']"}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'picture_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'projects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'team_members'", 'null': 'True', 'to': u"orm['people.Team']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'people.language': {
            'Meta': {'object_name': 'Language'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        u'people.location': {
            'Meta': {'object_name': 'Location'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.project': {
            'Meta': {'object_name': 'Project'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'forked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'parent_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'repo_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'service': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '30', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.team': {
            'Meta': {'object_name': 'Team'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['game']
########NEW FILE########
__FILENAME__ = models
from collections import namedtuple
import datetime
import logging

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.utils import timezone

from july.people.models import Project, Location, Team, Commit, Language


LOCATION_SQL = """\
SELECT july_user.location_id AS slug,
    people_location.name AS name,
    SUM(game_player.points) AS total
    FROM game_player, july_user, people_location
    WHERE game_player.user_id = july_user.id
    AND july_user.location_id = people_location.slug
    AND people_location.approved = 1
    AND game_player.game_id = %s
    GROUP BY july_user.location_id
    ORDER BY total DESC
    LIMIT 50;
"""


TEAM_SQL = """\
SELECT july_user.team_id AS slug,
    people_team.name AS name,
    SUM(game_player.points) AS total
    FROM game_player, july_user, people_team
    WHERE game_player.user_id = july_user.id
    AND july_user.team_id = people_team.slug
    AND people_team.approved = 1
    AND game_player.game_id = %s
    GROUP BY july_user.team_id
    ORDER BY total DESC
    LIMIT 50;
"""


# Number of commits on each day during the game
HISTOGRAM = """\
SELECT count(*), DATE(people_commit.timestamp),
    game_game.start AS start, game_game.end AS end
    FROM people_commit, game_game
    WHERE game_game.id = %s
    AND people_commit.timestamp > start
    AND people_commit.timestamp < end
    GROUP BY DATE(people_commit.timestamp)
    LIMIT 33;
"""


class Game(models.Model):

    start = models.DateTimeField()
    end = models.DateTimeField()
    commit_points = models.IntegerField(default=1)
    project_points = models.IntegerField(default=10)
    problem_points = models.IntegerField(default=5)
    players = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through='Player')
    boards = models.ManyToManyField(Project, through='Board')
    language_boards = models.ManyToManyField(
        Language, through='LanguageBoard')

    class Meta:
        ordering = ['-end']
        get_latest_by = 'end'

    def __unicode__(self):
        if self.end.month == 8:
            return 'Julython %s' % self.end.year
        elif self.end.month == 2:
            return 'J(an)ulython %s' % self.end.year
        else:
            return 'Testathon %s' % self.end.year

    @property
    def locations(self):
        """Preform a raw query to mimic a real model."""
        return Location.objects.raw(LOCATION_SQL, [self.pk])

    @property
    def teams(self):
        """Preform a raw query to mimic a real model."""
        return Team.objects.raw(TEAM_SQL, [self.pk])

    @property
    def histogram(self):
        """Return a histogram of commits during the month"""
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute(HISTOGRAM, [self.pk])
        Day = namedtuple('Day', 'count date start end')

        def mdate(d):
            # SQLITE returns a string while mysql returns date object
            # so make it look the same.
            if isinstance(d, datetime.date):
                return d
            day = datetime.datetime.strptime(d, '%Y-%m-%d')
            return day.date()

        days = {mdate(i.date): i for i in map(Day._make, cursor.fetchall())}
        num_days = self.end - self.start
        records = []
        for day_n in xrange(num_days.days + 1):
            day = self.start + datetime.timedelta(days=day_n)
            records.append(days.get(day.date(), Day(0, day.date(), '', '')))

        logging.debug(records)
        # TODO (rmyers): This should return a json array with labels
        results = [int(day.count) for day in records]
        return results

    @classmethod
    def active(cls, now=None):
        """Returns the active game or None."""
        if now is None:
            now = timezone.now()
        try:
            return cls.objects.get(start__lte=now, end__gte=now)
        except cls.DoesNotExist:
            return None

    @classmethod
    def active_or_latest(cls, now=None):
        """Return the an active game or the latest one."""
        if now is None:
            now = timezone.now()
        game = cls.active(now)
        if game is None:
            query = cls.objects.filter(end__lte=now)
            if len(query):
                game = query[0]
        return game

    def add_points_to_board(self, commit, from_orphan=False):
        board, created = Board.objects.select_for_update().get_or_create(
            game=self, project=commit.project,
            defaults={'points': self.project_points + self.commit_points})
        if not created and not from_orphan:
            board.points += self.commit_points
            board.save()
        return board

    def add_points_to_language_boards(self, commit):
        for language in commit.languages:
            lang, _ = Language.objects.get_or_create(name=language)
            language_board, created = LanguageBoard.objects. \
                select_for_update().get_or_create(
                    game=self, language=lang,
                    defaults={'points': self.commit_points})
            if not created:
                language_board.points += self.commit_points
                language_board.save()

    def add_points_to_player(self, board, commit):
        player, created = Player.objects.select_for_update().get_or_create(
            game=self, user=commit.user,
            defaults={'points': self.project_points + self.commit_points})
        player.boards.add(board)
        if not created:
            # we need to get the total points for the user
            project_points = player.boards.all().count() * self.project_points
            commit_points = Commit.objects.filter(
                user=commit.user,
                timestamp__gte=self.start,
                timestamp__lte=self.end).count() * self.commit_points
            # TODO (rmyers): Add in problem points
            player.points = project_points + commit_points
            player.save()

    def add_commit(self, commit, from_orphan=False):
        """
        Add a commit to the game, update the scores for the player/boards.
        If the commit was previously an orphan commit don't update the board
        total, since it was already updated.

        TODO (rmyers): This may need to be run by celery in the future instead
        of a post create signal.
        """
        board = self.add_points_to_board(commit, from_orphan)
        self.add_points_to_language_boards(commit)

        if commit.user:
            self.add_points_to_player(board, commit)


class Player(models.Model):
    """A player in the game."""

    game = models.ForeignKey(Game)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    points = models.IntegerField(default=0)
    boards = models.ManyToManyField('Board')

    class Meta:
        ordering = ['-points']
        get_latest_by = 'game__end'

    def __unicode__(self):
        return unicode(self.user)


class AbstractBoard(models.Model):
    """Keeps points per metric per game"""
    game = models.ForeignKey(Game)
    points = models.IntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ['-points']
        get_latest_by = 'game__end'


class Board(AbstractBoard):
    """A project with commits in the game."""

    project = models.ForeignKey(Project)

    def __unicode__(self):
        return 'Board for %s' % unicode(self.project)


class LanguageBoard(AbstractBoard):
    """A language with commits in the game."""

    language = models.ForeignKey(Language)

    def __unicode__(self):
        return 'Board for %s' % unicode(self.language)


@receiver(post_save, sender=Commit)
def add_commit(sender, **kwargs):
    """Listens for new commits and adds them to the game."""
    commit = kwargs.get('instance')
    active_game = Game.active(now=commit.timestamp)
    if active_game is not None:
        from_orphan = not kwargs.get('created', False)
        active_game.add_commit(commit, from_orphan=from_orphan)

########NEW FILE########
__FILENAME__ = tests

import datetime

import uuid
from pytz import UTC

from django.test import TestCase
from django.template.defaultfilters import slugify
from django.utils import timezone

from july.models import User
from july.people.models import Location, Commit, Team, Project
from july.game.models import Game
from july.game.views import GameMixin


class ModelMixin(object):

    def make_game(self, start=None, end=None):
        now = timezone.now()
        if start is None:
            start = now - datetime.timedelta(days=1)
        if end is None:
            end = now + datetime.timedelta(days=1)
        return Game.objects.create(start=start, end=end)

    def make_user(self, username, **kwargs):
        return User.objects.create_user(username=username, **kwargs)

    def make_location(self, location, approved=True):
        slug = slugify(location)
        return Location.objects.create(name=location, slug=slug,
                                       approved=approved)

    def make_team(self, team, approved=True):
        slug = slugify(team)
        return Team.objects.create(name=team, slug=slug, approved=approved)

    def make_project(self, url='http://github.com/project', name='test'):
        return Project.create(url=url, name=name)

    def make_commit(self, auth_id='x:no', hash=None, timestamp=None,
                    project=None, **kwargs):
        if hash is None:
            hash = str(uuid.uuid4())
        if timestamp is None:
            timestamp = timezone.now()
        commit = kwargs.copy()
        commit.update({'hash': hash, 'timestamp': timestamp})
        return Commit.create_by_auth_id(auth_id, [commit], project=project)


class GameModelTests(TestCase, ModelMixin):

    def setUp(self):
        self.now = timezone.now()
        self.yesterday = self.now - datetime.timedelta(days=1)
        self.tomorrow = self.now + datetime.timedelta(days=1)
        self.early = self.now - datetime.timedelta(days=2)
        self.late = self.now + datetime.timedelta(days=2)

    def test_julython(self):
        game = self.make_game(
            end=datetime.datetime(year=2012, month=8, day=2, tzinfo=UTC))
        self.assertEqual(unicode(game), 'Julython 2012')

    def test_janulython(self):
        game = self.make_game(
            end=datetime.datetime(year=2012, month=2, day=2, tzinfo=UTC))
        self.assertEqual(unicode(game), 'J(an)ulython 2012')

    def test_testathon(self):
        game = self.make_game(
            end=datetime.datetime(year=2012, month=5, day=2, tzinfo=UTC))
        self.assertEqual(unicode(game), 'Testathon 2012')

    def test_active(self):
        game = self.make_game()
        active = Game.active()
        self.assertEqual(active, game)

    def test_active_or_latest(self):
        game = self.make_game()
        active = Game.active_or_latest()
        self.assertEqual(active, game)

    def test_active_or_latest_future(self):
        self.make_game(start=self.tomorrow, end=self.late)
        active = Game.active_or_latest()
        self.assertEqual(active, None)

    def test_active_or_latest_past(self):
        game = self.make_game(start=self.early, end=self.yesterday)
        active = Game.active_or_latest()
        self.assertEqual(active, game)

    def test_not_active(self):
        self.make_game(start=self.tomorrow, end=self.late)
        active = Game.active()
        self.assertEqual(active, None)

    def test_add_board(self):
        # Test the post add hook
        game = self.make_game()
        project = self.make_project()
        self.make_commit(project=project)
        self.assertEqual(len(game.boards.all()), 1)
        self.assertEqual(unicode(game.boards.get()), 'test')

    def test_add_player(self):
        game = self.make_game()
        project = self.make_project()
        user = self.make_user('ted')
        user.add_auth_id('test:ted')
        self.make_commit(auth_id='test:ted', project=project)
        self.assertEqual(len(game.players.all()), 1)
        self.assertEqual(unicode(game.players.get()), 'ted')

    def test_histogram(self):
        game = self.make_game()
        project = self.make_project()
        self.make_commit(project=project)
        self.make_commit(project=project)
        self.make_commit(project=project)
        self.make_commit(project=project)
        self.assertEqual(game.histogram, [0, 4, 0])

    def test_histogram_end(self):
        # TODO: Fix histogram
        delta = datetime.timedelta(days=31)
        game = self.make_game(start=self.now - delta, end=self.now)
        project = self.make_project()
        self.make_commit(project=project, timestamp=self.tomorrow - delta)
        self.make_commit(project=project, timestamp=self.yesterday)
        self.make_commit(project=project, timestamp=self.yesterday)
        self.make_commit(project=project, timestamp=self.yesterday)
        self.assertEqual(game.histogram, [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                          0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                          0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0])


class Mixer(GameMixin):
    """Helper class to test mixin"""
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class GameViewTests(TestCase, ModelMixin):

    def setUp(self):
        self.now = timezone.now()
        self.yesterday = self.now - datetime.timedelta(days=1)
        self.tomorrow = self.now + datetime.timedelta(days=1)
        self.early = self.now - datetime.timedelta(days=2)
        self.late = self.now + datetime.timedelta(days=2)

    def test_game_mixin_active(self):
        active = self.make_game()
        mixed = Mixer()
        game = mixed.get_game()
        self.assertEqual(game, active)

    def test_game_mixin_latest(self):
        past = self.make_game(start=self.early, end=self.yesterday)
        mixed = Mixer()
        game = mixed.get_game()
        self.assertEqual(game, past)

    def test_game_mixin_future(self):
        past = self.make_game(start=self.early, end=self.yesterday)
        future = self.make_game(start=self.tomorrow, end=self.late)
        mixed = Mixer()
        game = mixed.get_game()
        self.assertNotEqual(game, future)
        self.assertEqual(game, past)

    def test_game_mixin_old(self):
        recent = self.make_game(start=self.early, end=self.yesterday)
        start = self.early - datetime.timedelta(days=4)
        middle = self.early - datetime.timedelta(days=3)
        end = self.early - datetime.timedelta(days=2)
        past = self.make_game(start=start, end=end)
        mixed = Mixer(year=middle.year, month=middle.month, day=middle.day)
        game = mixed.get_game()
        self.assertNotEqual(game, recent)
        self.assertEqual(game, past)

    def test_player_view(self):
        self.make_game()
        project = self.make_project()
        user = self.make_user('ted')
        user.add_auth_id('test:ted')
        self.make_commit(auth_id='test:ted', project=project)
        resp = self.client.get('/people/')
        self.assertContains(resp, 'ted')

    def test_project_view(self):
        self.make_game()
        project = self.make_project(name="fred")
        user = self.make_user('ted')
        user.add_auth_id('test:ted')
        self.make_commit(auth_id='test:ted', project=project)
        resp = self.client.get('/projects/')
        self.assertEqual(resp.status_code, 200)

    def test_loction_view(self):
        self.make_game()
        project = self.make_project()
        location = self.make_location("Austin, TX")
        user = self.make_user('ted', location=location)
        user.add_auth_id('test:ted')
        self.make_commit(auth_id='test:ted', project=project)
        resp = self.client.get('/location/')
        self.assertContains(resp, "Austin, TX")

    def test_loction_view_new(self):
        self.make_game()
        project = self.make_project()
        location = self.make_location("Austin, TX", approved=False)
        user = self.make_user('ted', location=location)
        user.add_auth_id('test:ted')
        self.make_commit(auth_id='test:ted', project=project)
        resp = self.client.get('/location/austin-tx/')
        self.assertEqual(resp.status_code, 404)

    def test_team_view(self):
        self.make_game()
        project = self.make_project()
        team = self.make_team("Commit Rangers")
        user = self.make_user('ted', team=team)
        user.add_auth_id('test:ted')
        self.make_commit(auth_id='test:ted', project=project)
        resp = self.client.get('/teams/')
        self.assertContains(resp, "Commit Rangers")

    def test_team_view_new(self):
        self.make_game()
        project = self.make_project()
        team = self.make_team("Commit Rangers", approved=False)
        user = self.make_user('ted', team=team)
        user.add_auth_id('test:ted')
        self.make_commit(auth_id='test:ted', project=project)
        resp = self.client.get('/teams/commit-rangers/')
        self.assertEqual(resp.status_code, 404)

    def test_event_handler(self):
        resp = self.client.post('/events/pub/test/', {"foo": "bar"})
        self.assertEqual(resp.status_code, 200)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from july.game import views


urlpatterns = patterns(
    'july.game.views',
    url(r'^people/$',
        views.PlayerList.as_view(),
        name='leaderboard'),
    url(r'^people/(?P<year>\d{4})/(?P<month>\d{1,2})/((?P<day>\d{1,2})/)?$',
        views.PlayerList.as_view(),
        name='leaderboard'),
    url(r'^teams/$',
        views.TeamCollection.as_view(),
        name='teams'),
    url(r'^teams/(?P<year>\d{4})/(?P<month>\d{1,2})/((?P<day>\d{1,2})/)?$',
        views.TeamCollection.as_view(),
        name='teams'),
    url(r'^teams/(?P<slug>[a-zA-Z0-9\-]+)/$',
        views.TeamView.as_view(),
        name='team-details'),
    url(r'^location/$',
        views.LocationCollection.as_view(),
        name='locations'),
    url(r'^location/(?P<year>\d{4})/(?P<month>\d{1,2})/((?P<day>\d{1,2})/)?$',
        views.LocationCollection.as_view(),
        name='locations'),
    url(r'^location/(?P<slug>[a-zA-Z0-9\-]+)/$',
        views.LocationView.as_view(),
        name='location-detail'),
    url(r'^projects/$',
        views.BoardList.as_view(),
        name='projects'),
    url(r'^projects/(?P<year>\d{4})/(?P<month>\d{1,2})/((?P<day>\d{1,2})/)?$',
        views.BoardList.as_view(),
        name='projects'),
    url(r'^projects/(?P<slug>.+)/$',
        views.ProjectView.as_view(),
        name='project-details'),
    url(r'^languages/$',
        views.LanguageBoardList.as_view(),
        name='languages'),
    url(r'^languages/(?P<year>\d{4})/(?P<month>\d{1,2})/((?P<day>\d{1,2})/)?$',
        views.LanguageBoardList.as_view(),
        name='languages'),
    # for local only debug purposes
    url(r'^events/(?P<action>pub|sub|ws)/(?P<channel>.*)$',
        'events', name='events'),
)

########NEW FILE########
__FILENAME__ = views
import datetime
import logging
from pytz import UTC

from django.views.generic import list, detail
from django.http.response import HttpResponse
from django.http import Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.list import ListView

from july.game.models import Player, Game, Board, LanguageBoard
from july.people.models import Project, Location, Team, Language


class GameMixin(object):

    def get_game(self):
        year = int(self.kwargs.get('year', 0))
        mon = int(self.kwargs.get('month', 0))
        day = self.kwargs.get('day')
        if day is None:
            day = 15
        day = int(day)
        if not all([year, mon]):
            now = None
        else:
            now = datetime.datetime(year=year, month=mon, day=day, tzinfo=UTC)
            logging.debug("Getting game for date: %s", now)
        return Game.active_or_latest(now=now)


class PlayerList(ListView, GameMixin):
    model = Player
    paginate_by = 100

    def get_queryset(self):
        game = self.get_game()
        return Player.objects.filter(
            game=game, user__is_active=True).select_related()


class BoardList(ListView, GameMixin):
    model = Board
    paginate_by = 100

    def get_queryset(self):
        game = self.get_game()
        return Board.objects.filter(
            game=game, project__active=True).select_related()


class LanguageBoardList(list.ListView, GameMixin):
    model = LanguageBoard
    paginate_by = 100


class ProjectView(detail.DetailView):
    model = Project

    def get_queryset(self):
        return self.model.objects.filter(active=True)


class LanguageView(detail.DetailView):
    model = Language


class LocationCollection(ListView, GameMixin):
    model = Location

    def get_queryset(self):
        game = self.get_game()
        return game.locations


class LocationView(detail.DetailView):
    model = Location

    def get_object(self):
        obj = super(LocationView, self).get_object()
        if not obj.approved:
            raise Http404("Location not found")
        return obj


class TeamCollection(ListView, GameMixin):
    model = Team

    def get_queryset(self):
        game = self.get_game()
        return game.teams


class TeamView(detail.DetailView):
    model = Team

    def get_object(self):
        obj = super(TeamView, self).get_object()
        if not obj.approved:
            raise Http404("Team not found")
        return obj


@csrf_exempt
def events(request, action, channel):
    logging.info('%s on %s', action, channel)
    if request.method == 'POST':
        logging.info(request.body)
    return HttpResponse('ok')

########NEW FILE########
__FILENAME__ = fix_commits
import logging

from django.core.management.base import BaseCommand

from july.people.models import Commit
from july.models import User
from optparse import make_option


class Command(BaseCommand):
    args = ''
    help = 'Associate orphan commits'
    option_list = BaseCommand.option_list + (
        make_option(
            '--commit',
            action='store_true',
            dest='commit',
            default=False,
            help='Actually change the commits.'),
    )

    def handle(self, *args, **options):
        commit = options['commit']

        bad_emails = []
        fixed = 0
        if not commit:
            count = Commit.objects.filter(user=None)
            logging.info("Found %s commits, add --commit to fix", count)
            return

        for commit in Commit.objects.filter(user=None):
            if commit.email in bad_emails or not commit.email:
                continue
            user = User.get_by_auth_id('email:%s' % commit.email)
            if not user:
                logging.info("Found bad email: %s", commit.email)
                bad_emails.append(commit.email)
                continue
            commit.user = user
            commit.save()
            user.projects.add(commit.project)
            fixed += 1
            if (fixed % 100) == 0:
                logging.info("Fixed %s commits", fixed)

        logging.info("Fixed %s commits", fixed)

########NEW FILE########
__FILENAME__ = fix_locations

import logging

from django.core.management.base import BaseCommand
from django.template.defaultfilters import slugify

from july.models import User
from july.people.models import Location
from july.utils import check_location
from optparse import make_option


class Command(BaseCommand):
    help = 'fix locations'
    option_list = BaseCommand.option_list + (
        make_option(
            '--commit',
            action='store_true',
            dest='commit',
            default=False,
            help='Actually move the items.'),
    )

    def handle(self, *args, **options):
        commit = options['commit']
        empty = 0
        fine = 0
        fixable = 0
        bad = []
        for location in Location.objects.all():
            user_count = User.objects.filter(location=location).count()
            if not user_count:
                logging.info("Empty location: %s", location)
                if commit:
                    location.delete()
                    logging.info('Deleted')
                empty += 1
                continue
            l = check_location(location.name)
            if l == location.name:
                logging.info('Location fine: %s', location)
                fine += 1
                continue

            if not commit:
                if l:
                    fixable += 1
                else:
                    bad.append((location, user_count))
                continue
            elif l is not None:
                new_loc = Location.create(l)
                User.objects.filter(location=location).update(location=new_loc)
                user_count = User.objects.filter(location=location).count()
                if not user_count:
                    logging.error("missed users!")
                else:
                    location.delete()
            elif l is None:
                logging.info('Bad location: %s', location)
                location.approved = False
                location.save()

        if not commit:
            [logging.error('Bad Loc: %s, count: %s', l, c) for l, c in bad]
            logging.info('Empty: %s, Fine: %s, fixable: %s',
                         empty, fine, fixable)
            logging.info('Add --commit to fix locations')

########NEW FILE########
__FILENAME__ = load_commits
import json
import logging
from datetime import datetime

import pytz

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.utils.timezone import make_aware

from july.people.models import Commit, Project
import os


def to_datetime(ts):
    d = datetime.fromtimestamp(ts)
    t = make_aware(d, pytz.UTC)
    return t


def to_commit(commit):
    new = {}
    attrs = ['hash', 'author', 'name', 'message', 'url', 'email']
    new['timestamp'] = to_datetime(commit['timestamp'])
    new['created_on'] = to_datetime(commit['created_on'])
    for key in attrs:
        new[key] = commit.get(key) or ''

    return new


class Command(BaseCommand):
    args = '<commits.json>'
    help = 'Load commits from json file'

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('Must supply a JSON file of commits.')

        commit_path = args[0]

        if os.path.isdir(commit_path):
            files = [os.path.join(commit_path, f) for f in
                     os.listdir(commit_path) if f.startswith('commits')]
        else:
            files = [commit_path]

        for commits_json in files:
            logging.info("Parsing File: %s", commits_json)
            with open(commits_json, 'r') as commit_file:
                commits = json.loads(commit_file.read())
                for commit in commits['models']:
                    try:
                        project, _ = Project.create(url=commit['project'])
                        c = to_commit(commit)
                        Commit.create_by_email(c['email'], c, project)
                    except Exception:
                        logging.exception("Error: %s" % commit)

########NEW FILE########
__FILENAME__ = load_projects
import json
import logging

from django.core.management.base import BaseCommand, CommandError

from july.people.models import Project


class Command(BaseCommand):
    args = '<project.json>'
    help = 'Load projects from json file'

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('Must supply a JSON file of projects.')

        with open(args[0], 'r') as project_file:
            projects = json.loads(project_file.read())
            for project in projects['models']:
                try:
                    Project.objects.get_or_create(
                        url=project['url'],
                        description=project['description'],
                        name=project['name'])
                except Exception, e:
                    logging.exception("Error: %s" % e)

########NEW FILE########
__FILENAME__ = load_users
import json
import logging
import requests
from time import sleep

from django.core.management.base import BaseCommand, CommandError
from django.template.defaultfilters import slugify

from july.models import User
from july.people.models import Location, Team
from optparse import make_option


def get_twitter_id(name):
    # don't overload twitter api
    sleep(60)
    resp = requests.get(
        'https://api.twitter.com/1/users/lookup.json?screen_name=%s' % name)
    data = json.loads(resp.content)
    return data[0]


def get_location(location):
    if location is None:
        return
    slug = slugify(location)
    loc, _ = Location.objects.get_or_create(
        slug=slug, defaults={'name': location})
    return loc


def get_team(team):
    if team is None:
        return
    slug = slugify(team)
    t, _ = Team.objects.get_or_create(slug=slug, defaults={'name': team})
    return t


class FakeUser(object):

    def __init__(self, user, commit=False):
        self.username = None
        self.first_name = user.get('first_name', '')
        self.last_name = user.get('last_name', '')
        self.password = '!'
        self._auth_ids = user.get('auth_ids', [])
        self.url = user.get('url', '') or ''
        self.location = get_location(user.get('location'))
        self.team = get_team(user.get('team'))
        self.description = user.get('description', '') or ''
        self.picture_url = user.get('picture_url', '')
        self.auth_ids = []
        for auth in self._auth_ids:
            provider, uid = auth.split(':')
            if provider == 'own':
                self.username = uid
            elif provider == 'twitter':
                if commit:
                    data = get_twitter_id(uid)
                    tid = data['id']
                    self.picture_url = data.get('profile_image_url', '')
                else:
                    tid = uid
                self.auth_ids.append('twitter:%s' % tid)
            else:
                self.auth_ids.append(auth)

    def create(self):
        if self.username is None:
            print self.__dict__
            return
        defaults = {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'url': self.url,
            'picture_url': self.picture_url,
            'description': self.description,
            'team': self.team,
            'location': self.location
        }
        user, created = User.objects.get_or_create(
            username=self.username, defaults=defaults)
        if not created:
            for k, v in defaults.iteritems():
                setattr(user, k, v)
            user.save()
        user_auth_ids = user.auth_ids
        for auth in self.auth_ids:
            if auth not in user_auth_ids:
                user.add_auth_id(auth)


class Command(BaseCommand):
    args = '<user.json>'
    help = 'Load users from json file'
    option_list = BaseCommand.option_list + (
        make_option(
            '--commit',
            action='store_true',
            dest='commit',
            default=False,
            help='Actually poll twitter/github for account info.'),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('Must supply a JSON file of users.')

        with open(args[0], 'r') as user_file:
            users = json.loads(user_file.read())
            total = len(users['models'])
            count = 0
            for user in users['models']:
                count += 1
                try:
                    f = FakeUser(user, options['commit'])
                    f.create()
                except Exception, e:
                    logging.exception("Error: %s" % e)
                logging.info("Loaded %s of %s: %s", count, total, f.username)

########NEW FILE########
__FILENAME__ = merge_user

from django.core.management.base import BaseCommand, CommandError

from july.models import User
from july.auth.social import merge_users
from optparse import make_option


class Command(BaseCommand):
    args = '<old_user.id> <new_user.id>'
    help = 'move all records from old user to new user'
    option_list = BaseCommand.option_list + (
        make_option(
            '--commit',
            action='store_true',
            dest='commit',
            default=False,
            help='Actually move the items.'),
    )

    def handle(self, *args, **options):
        commit = options['commit']
        if len(args) != 2:
            raise CommandError('You must enter two user ids.')
        try:
            old_user = User.objects.get(pk=int(args[0]))
            new_user = User.objects.get(pk=int(args[1]))
        except:
            raise CommandError("unable to find those users.")

        merge_users(new_user, old_user, commit)

########NEW FILE########
__FILENAME__ = middleware
import datetime
from datetime import date
from django.conf import settings

oneday = datetime.timedelta(days=1)
ABUSE_DELTA = datetime.timedelta(days=settings.ABUSE_LIMIT)


class AbuseMiddleware(object):
    def _can_report_abuse(self, request):
        def can_report_abuse():
            abuse_date = request.session.get('abuse_date')
            return not abuse_date or abuse_date < date.today()
        return can_report_abuse

    def _abuse_reported(self, request):
        def abuse_reported():
            abuse_date = request.session.get('abuse_date')
            if not abuse_date or abuse_date + ABUSE_DELTA < date.today():
                request.session['abuse_date'] = date.today() - ABUSE_DELTA

            request.session['abuse_date'] += oneday
        return abuse_reported

    def process_request(self, request):
        request.can_report_abuse = self._can_report_abuse(request)
        request.abuse_reported = self._abuse_reported(request)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'User'
        db.create_table(u'july_user', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('last_login', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('username', self.gf('django.db.models.fields.CharField')(unique=True, max_length=30)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
            ('is_staff', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('is_superuser', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_joined', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('location', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='location_members', null=True, to=orm['people.Location'])),
            ('team', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='team_members', null=True, to=orm['people.Team'])),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('picture_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
        ))
        db.send_create_signal(u'july', ['User'])

        # Adding M2M table for field groups on 'User'
        db.create_table(u'july_user_groups', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('user', models.ForeignKey(orm[u'july.user'], null=False)),
            ('group', models.ForeignKey(orm[u'auth.group'], null=False))
        ))
        db.create_unique(u'july_user_groups', ['user_id', 'group_id'])

        # Adding M2M table for field user_permissions on 'User'
        db.create_table(u'july_user_user_permissions', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('user', models.ForeignKey(orm[u'july.user'], null=False)),
            ('permission', models.ForeignKey(orm[u'auth.permission'], null=False))
        ))
        db.create_unique(u'july_user_user_permissions', ['user_id', 'permission_id'])

        # Adding M2M table for field projects on 'User'
        db.create_table(u'july_user_projects', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('user', models.ForeignKey(orm[u'july.user'], null=False)),
            ('project', models.ForeignKey(orm[u'people.project'], null=False))
        ))
        db.create_unique(u'july_user_projects', ['user_id', 'project_id'])


    def backwards(self, orm):
        # Deleting model 'User'
        db.delete_table(u'july_user')

        # Removing M2M table for field groups on 'User'
        db.delete_table('july_user_groups')

        # Removing M2M table for field user_permissions on 'User'
        db.delete_table('july_user_user_permissions')

        # Removing M2M table for field projects on 'User'
        db.delete_table('july_user_projects')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'july.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'location_members'", 'null': 'True', 'to': u"orm['people.Location']"}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'picture_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'projects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'team_members'", 'null': 'True', 'to': u"orm['people.Team']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'people.location': {
            'Meta': {'object_name': 'Location'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.project': {
            'Meta': {'object_name': 'Project'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'forked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'parent_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.team': {
            'Meta': {'object_name': 'Team'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['july']
########NEW FILE########
__FILENAME__ = models
"""
Custom User Model for Julython
==============================

This is experimental, but so much worth it!
"""

from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.utils.crypto import salted_hmac
from social_auth.models import UserSocialAuth

from july.people.models import Location, Team, Project, AchievedBadge


class User(AbstractUser):
    location = models.ForeignKey(Location, blank=True, null=True,
                                 related_name='location_members')
    team = models.ForeignKey(Team, blank=True, null=True,
                             related_name='team_members')
    projects = models.ManyToManyField(Project, blank=True, null=True)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True, null=True)
    picture_url = models.URLField(blank=True, null=True)

    def __unicode__(self):
        return self.get_full_name() or self.username

    def add_auth_id(self, auth_str):
        """
        Add a social auth identifier for this user.

        The `auth_str` should be in the format '{provider}:{uid}'
        this is useful for adding multiple unique email addresses.

        Example::

            user = User.objects.get(username='foo')
            user.add_auth_id('email:foo@example.com')
        """
        provider, uid = auth_str.split(':')
        return UserSocialAuth.create_social_auth(self, uid, provider)

    def add_auth_email(self, email, request=None):
        """
        Adds a new, non verified email address, and sends a verification email.
        """
        auth_email = self.add_auth_id('email:%s' % email)
        auth_email.extra_data = {'verified': False}
        auth_email.save()
        return auth_email

    def get_provider(self, provider):
        """Return the uid of the provider or None if not set."""
        try:
            return self.social_auth.filter(provider=provider).get()
        except UserSocialAuth.DoesNotExist:
            return None

    def find_valid_email(self, token):
        result = None
        for email_auth in self.social_auth.filter(provider="email"):
            email = email_auth.uid
            expected = salted_hmac(settings.SECRET_KEY, email).hexdigest()
            if expected == token:
                result = email_auth
        return result

    @property
    def gittip(self):
        return self.get_provider('gittip')

    @property
    def twitter(self):
        return self.get_provider('twitter')

    @property
    def github(self):
        return self.get_provider('github')

    @classmethod
    def get_by_auth_id(cls, auth_str):
        """
        Return the user identified by the auth id.

        Example::

            user = User.get_by_auth_id('twitter:julython')
        """
        provider, uid = auth_str.split(':')
        sa = UserSocialAuth.get_social_auth(provider, uid)
        if sa is None:
            return None
        return sa.user

    @property
    def auth_ids(self):
        auths = self.social_auth.all()
        return [':'.join([a.provider, a.uid]) for a in auths]

    @property
    def badges(self):
        try:
            return AchievedBadge.objects.filter(user=self)
        except:
            return []

    @property
    def points(self):
        try:
            player = self.player_set.latest()
        except:
            return 0
        return player.points

    @property
    def total(self):
        return self.points

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from models import Team, Commit, Location, AchievedBadge, Project
from models import Badge, Language


def purge_commits(modeladmin, request, queryset):
    for obj in queryset:
        obj.commit_set.all().delete()
purge_commits.short_description = "Purge Commits"


admin.site.register(
    Commit,
    list_display=['hash', 'email', 'timestamp', 'project', 'user'],
    search_fields=['hash', 'email', 'project__name', 'user__username'],
    ordering=['-timestamp'],
    raw_id_fields=['user', 'project'])

admin.site.register(
    Language,
    list_display=["__unicode__"])

admin.site.register(
    Badge,
    list_display=["__unicode__"])

admin.site.register(AchievedBadge)


class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'forked', 'active']
    list_filter = ['active']
    search_fields = ['name', 'url']
    actions = [purge_commits]


class GroupAdmin(admin.ModelAdmin):
    list_display = ["__unicode__", "slug", 'total', 'approved']
    ordering = ['-total']
    list_filter = ['approved']
    search_fields = ['name', 'slug']


admin.site.register(Team, GroupAdmin)
admin.site.register(Location, GroupAdmin)
admin.site.register(Project, ProjectAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy
from models import Location, Team

from july.utils import check_location


class EditAddressForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(EditAddressForm, self).__init__(*args, **kwargs)

        if self.user:
            self.fields['address_line1'].initial = getattr(
                self.user, 'address_line1', None)
            self.fields['address_line2'].initial = getattr(
                self.user, 'address_line2', None)
            self.fields['city'].initial = getattr(
                self.user, 'city', None)
            self.fields['state'].initial = getattr(
                self.user, 'state', None)
            self.fields['country'].initial = getattr(
                self.user, 'country', None)
            self.fields['postal_code'].initial = getattr(
                self.user, 'postal_code', None)

    address_line1 = forms.CharField(
        label=ugettext_lazy('Address'),
        max_length=255, required=True
    )
    address_line2 = forms.CharField(
        label=ugettext_lazy('Address Line 2'),
        max_length=255, required=False
    )
    city = forms.CharField(
        label=ugettext_lazy('City'),
        max_length=20, required=True
    )
    state = forms.CharField(
        label=ugettext_lazy('State / Region'),
        max_length=12, required=True
    )
    country = forms.CharField(
        label=ugettext_lazy('Country'),
        max_length=25, required=True
    )
    postal_code = forms.CharField(
        label=ugettext_lazy('Postal Code'),
        max_length=12, required=True
    )


class EditUserForm(forms.Form):
    # Match Twitter
    first_name = forms.CharField(
        label=ugettext_lazy('First name'),
        max_length=255, required=True
    )
    last_name = forms.CharField(
        label=ugettext_lazy('Last name'),
        max_length=255, required=False
    )
    description = forms.CharField(
        label=ugettext_lazy("About me"), max_length=160, required=False,
        widget=forms.TextInput(attrs={'class': 'span6'})
    )
    url = forms.CharField(
        label=ugettext_lazy('URL'),
        max_length=255, required=False,
        widget=forms.TextInput(attrs={'class': 'span4'})
    )

    location = forms.CharField(
        label=ugettext_lazy('Location'),
        help_text=ugettext_lazy(
            'Note new locations need to be approved first before'
            ' they will show up.'),
        max_length=160, required=False,
        widget=forms.TextInput(
            attrs={
                'data-bind': 'typeahead: $data.filterLocation'
            }
        )
    )

    team = forms.CharField(
        label=ugettext_lazy('Team'),
        help_text=ugettext_lazy(
            'Note new teams need to be approved first before'
            ' they will show up'),
        max_length=160, required=False,
        widget=forms.TextInput(
            attrs={
                'data-bind': 'typeahead: $data.filterTeam'
            }
        )
    )

    gittip = forms.CharField(
        label=ugettext_lazy("Gittip Username"), required=False)

    email = forms.EmailField(
        label=ugettext_lazy("Add Email Address"), required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self._gittip = None
        self.twitter = None
        self.github = None
        super(EditUserForm, self).__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['description'].initial = self.user.description
            self.fields['url'].initial = self.user.url
            if self.user.location:
                self.fields['location'].initial = self.user.location.name
            if self.user.team:
                self.fields['team'].initial = self.user.team.name
            # initialize the emails
            self.emails = set(self.user.social_auth.filter(provider="email"))
            self._gittip = self.user.get_provider("gittip")
            self.twitter = self.user.get_provider("twitter")
            self.github = self.user.get_provider("github")
            if self._gittip:
                self.fields['gittip'].initial = self._gittip.uid

    def clean_location(self):
        location = self.data.get('location', '')
        if not location:
            return
        location = check_location(location)
        if not location:
            error_msg = ugettext_lazy(
                "Specified location is invalid"
            )
            raise forms.ValidationError(error_msg)
        return Location.create(location)

    def clean_team(self):
        team = self.data.get('team', '')
        return Team.create(team)

    def clean_gittip(self):
        uid = self.cleaned_data['gittip']
        if not uid:
            if self._gittip is not None:
                self._gittip.delete()
            return None
        if self._gittip is not None:
            self._gittip.uid = uid
            self._gittip.save()
            return uid
        else:
            try:
                self.user.add_auth_id('gittip:%s' % uid)
            except:
                error_msg = ugettext_lazy(
                    "This gittip username is already in use, if this is not"
                    " right please email help@julython.org"
                )
                raise forms.ValidationError(error_msg)
        return uid

    def clean_email(self):
        email = self.cleaned_data['email']
        if not email:
            return None
        if email in [auth.uid for auth in self.emails]:
            error_msg = ugettext_lazy("You already have that email address!")
            raise forms.ValidationError(error_msg)

        # add the email address to the user, this will cause a ndb.put()
        try:
            self.user.add_auth_email(email)
        except Exception:
            error_msg = ugettext_lazy(
                "This email is already taken, if this is not right please "
                "email help@julython.org "
            )
            raise forms.ValidationError(error_msg)

        # Defer a task to fix orphan commits
        # TODO - make this a celery task?
        # deferred.defer(fix_orphans, email=email)
        return email


class CommitForm(forms.Form):

    message = forms.CharField(required=True)
    timestamp = forms.CharField(required=False)
    url = forms.URLField(required=False)
    email = forms.EmailField(required=False)
    author = forms.CharField(required=False)
    name = forms.CharField(required=False)
    hash = forms.CharField(required=False)

    def clean_timestamp(self):
        data = self.cleaned_data.get('timestamp')
        if data:
            import datetime
            data = datetime.datetime.fromtimestamp(float(data))
        return data


class ProjectForm(forms.Form):

    url = forms.URLField(required=True)
    forked = forms.BooleanField(required=False, initial=False)
    parent_url = forms.URLField(required=False)

    def clean_parent_url(self):
        data = self.cleaned_data
        if data['parent_url'] == '':
            return None
        return data['parent_url']

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Commit'
        db.create_table(u'people_commit', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['july.User'], null=True, blank=True)),
            ('hash', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('author', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('email', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('message', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=512, blank=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['people.Project'], null=True, blank=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')()),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'people', ['Commit'])

        # Adding model 'Project'
        db.create_table(u'people_project', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('forked', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('forks', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('watchers', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('parent_url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
        ))
        db.send_create_signal(u'people', ['Project'])

        # Adding model 'Location'
        db.create_table(u'people_location', (
            ('total', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, primary_key=True)),
        ))
        db.send_create_signal(u'people', ['Location'])

        # Adding model 'Team'
        db.create_table(u'people_team', (
            ('total', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, primary_key=True)),
        ))
        db.send_create_signal(u'people', ['Team'])


    def backwards(self, orm):
        # Deleting model 'Commit'
        db.delete_table(u'people_commit')

        # Deleting model 'Project'
        db.delete_table(u'people_project')

        # Deleting model 'Location'
        db.delete_table(u'people_location')

        # Deleting model 'Team'
        db.delete_table(u'people_team')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'july.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'location_members'", 'null': 'True', 'to': u"orm['people.Location']"}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'picture_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'projects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'team_members'", 'null': 'True', 'to': u"orm['people.Team']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'people.commit': {
            'Meta': {'object_name': 'Commit'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['july.User']", 'null': 'True', 'blank': 'True'})
        },
        u'people.location': {
            'Meta': {'object_name': 'Location'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.project': {
            'Meta': {'object_name': 'Project'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'forked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'parent_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.team': {
            'Meta': {'object_name': 'Team'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['people']
########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_commit_message
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Commit.message'
        db.alter_column(u'people_commit', 'message', self.gf('django.db.models.fields.CharField')(max_length=2024))

    def backwards(self, orm):

        # Changing field 'Commit.message'
        db.alter_column(u'people_commit', 'message', self.gf('django.db.models.fields.CharField')(max_length=255))

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'july.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'location_members'", 'null': 'True', 'to': u"orm['people.Location']"}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'picture_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'projects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'team_members'", 'null': 'True', 'to': u"orm['people.Team']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'people.commit': {
            'Meta': {'object_name': 'Commit'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '2024', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['july.User']", 'null': 'True', 'blank': 'True'})
        },
        u'people.location': {
            'Meta': {'object_name': 'Location'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.project': {
            'Meta': {'object_name': 'Project'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'forked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'parent_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.team': {
            'Meta': {'object_name': 'Team'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['people']
########NEW FILE########
__FILENAME__ = 0003_auto__add_badge__add_achievedbadge
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Badge'
        db.create_table(u'people_badge', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('text', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=2024, blank=True)),
        ))
        db.send_create_signal(u'people', ['Badge'])

        # Adding model 'AchievedBadge'
        db.create_table(u'people_achievedbadge', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['july.User'], null=True, blank=True)),
            ('badge', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['people.Badge'], null=True, blank=True)),
            ('achieved_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'people', ['AchievedBadge'])


    def backwards(self, orm):
        # Deleting model 'Badge'
        db.delete_table(u'people_badge')

        # Deleting model 'AchievedBadge'
        db.delete_table(u'people_achievedbadge')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'july.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'location_members'", 'null': 'True', 'to': u"orm['people.Location']"}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'picture_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'projects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'team_members'", 'null': 'True', 'to': u"orm['people.Team']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'people.achievedbadge': {
            'Meta': {'object_name': 'AchievedBadge'},
            'achieved_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Badge']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['july.User']", 'null': 'True', 'blank': 'True'})
        },
        u'people.badge': {
            'Meta': {'object_name': 'Badge'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '2024', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'people.commit': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Commit'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '2024', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['july.User']", 'null': 'True', 'blank': 'True'})
        },
        u'people.location': {
            'Meta': {'object_name': 'Location'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.project': {
            'Meta': {'object_name': 'Project'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'forked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'parent_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.team': {
            'Meta': {'object_name': 'Team'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['people']
########NEW FILE########
__FILENAME__ = 0004_auto__add_field_project_service__add_field_project_repo_id
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Project.service'
        db.add_column(u'people_project', 'service',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=30, blank=True),
                      keep_default=False)

        # Adding field 'Project.repo_id'
        db.add_column(u'people_project', 'repo_id',
                      self.gf('django.db.models.fields.IntegerField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Project.service'
        db.delete_column(u'people_project', 'service')

        # Deleting field 'Project.repo_id'
        db.delete_column(u'people_project', 'repo_id')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'july.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'location_members'", 'null': 'True', 'to': u"orm['people.Location']"}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'picture_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'projects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'team_members'", 'null': 'True', 'to': u"orm['people.Team']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'people.achievedbadge': {
            'Meta': {'object_name': 'AchievedBadge'},
            'achieved_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Badge']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['july.User']", 'null': 'True', 'blank': 'True'})
        },
        u'people.badge': {
            'Meta': {'object_name': 'Badge'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '2024', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'people.commit': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Commit'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '2024', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['july.User']", 'null': 'True', 'blank': 'True'})
        },
        u'people.location': {
            'Meta': {'object_name': 'Location'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.project': {
            'Meta': {'object_name': 'Project'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'forked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'parent_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'repo_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'service': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '30', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.team': {
            'Meta': {'object_name': 'Team'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['people']
########NEW FILE########
__FILENAME__ = 0005_auto__add_language__add_field_commit_files
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Language'
        db.create_table(u'people_language', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
        ))
        db.send_create_signal(u'people', ['Language'])

        # Adding field 'Commit.files'
        db.add_column(u'people_commit', 'files',
                      self.gf('jsonfield.fields.JSONField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting model 'Language'
        db.delete_table(u'people_language')

        # Deleting field 'Commit.files'
        db.delete_column(u'people_commit', 'files')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'july.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'location_members'", 'null': 'True', 'to': u"orm['people.Location']"}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'picture_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'projects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'team_members'", 'null': 'True', 'to': u"orm['people.Team']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'people.achievedbadge': {
            'Meta': {'object_name': 'AchievedBadge'},
            'achieved_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Badge']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['july.User']", 'null': 'True', 'blank': 'True'})
        },
        u'people.badge': {
            'Meta': {'object_name': 'Badge'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '2024', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'people.commit': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Commit'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'files': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '2024', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['july.User']", 'null': 'True', 'blank': 'True'})
        },
        u'people.language': {
            'Meta': {'object_name': 'Language'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        u'people.location': {
            'Meta': {'object_name': 'Location'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.project': {
            'Meta': {'object_name': 'Project'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'forked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'parent_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'repo_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'service': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '30', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.team': {
            'Meta': {'object_name': 'Team'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['people']
########NEW FILE########
__FILENAME__ = 0006_auto__add_field_location_approved__add_field_team_approved
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Location.approved'
        db.add_column(u'people_location', 'approved',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Team.approved'
        db.add_column(u'people_team', 'approved',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Location.approved'
        db.delete_column(u'people_location', 'approved')

        # Deleting field 'Team.approved'
        db.delete_column(u'people_team', 'approved')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'july.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'location_members'", 'null': 'True', 'to': u"orm['people.Location']"}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'picture_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'projects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'team_members'", 'null': 'True', 'to': u"orm['people.Team']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'people.achievedbadge': {
            'Meta': {'object_name': 'AchievedBadge'},
            'achieved_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Badge']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['july.User']", 'null': 'True', 'blank': 'True'})
        },
        u'people.badge': {
            'Meta': {'object_name': 'Badge'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '2024', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'people.commit': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Commit'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'files': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '2024', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['july.User']", 'null': 'True', 'blank': 'True'})
        },
        u'people.language': {
            'Meta': {'object_name': 'Language'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        u'people.location': {
            'Meta': {'object_name': 'Location'},
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.project': {
            'Meta': {'object_name': 'Project'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'forked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'parent_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'repo_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'service': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '30', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.team': {
            'Meta': {'object_name': 'Team'},
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['people']
########NEW FILE########
__FILENAME__ = 0007_auto__add_field_project_active
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Project.active'
        db.add_column(u'people_project', 'active',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Project.active'
        db.delete_column(u'people_project', 'active')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'july.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'location_members'", 'null': 'True', 'to': u"orm['people.Location']"}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'picture_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'projects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'team_members'", 'null': 'True', 'to': u"orm['people.Team']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'people.achievedbadge': {
            'Meta': {'object_name': 'AchievedBadge'},
            'achieved_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Badge']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['july.User']", 'null': 'True', 'blank': 'True'})
        },
        u'people.badge': {
            'Meta': {'object_name': 'Badge'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '2024', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'people.commit': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Commit'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'files': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '2024', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['july.User']", 'null': 'True', 'blank': 'True'})
        },
        u'people.language': {
            'Meta': {'object_name': 'Language'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        u'people.location': {
            'Meta': {'object_name': 'Location'},
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.project': {
            'Meta': {'object_name': 'Project'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'forked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'parent_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'repo_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'service': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '30', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.team': {
            'Meta': {'object_name': 'Team'},
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['people']
########NEW FILE########
__FILENAME__ = 0008_auto__add_field_project_updated_on
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from pytz import UTC


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Project.updated_on'
        db.add_column(u'people_project', 'updated_on',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now=True, default=datetime.datetime(2013, 7, 1, 0, 0, tzinfo=UTC), blank=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Project.updated_on'
        db.delete_column(u'people_project', 'updated_on')

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'july.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'location_members'", 'null': 'True', 'to': u"orm['people.Location']"}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'picture_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'projects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'team_members'", 'null': 'True', 'to': u"orm['people.Team']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'people.achievedbadge': {
            'Meta': {'object_name': 'AchievedBadge'},
            'achieved_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Badge']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['july.User']", 'null': 'True', 'blank': 'True'})
        },
        u'people.badge': {
            'Meta': {'object_name': 'Badge'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '2024', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'people.commit': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Commit'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'files': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '2024', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['people.Project']", 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['july.User']", 'null': 'True', 'blank': 'True'})
        },
        u'people.language': {
            'Meta': {'object_name': 'Language'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        u'people.location': {
            'Meta': {'object_name': 'Location'},
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.project': {
            'Meta': {'object_name': 'Project'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'forked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'forks': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'parent_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'repo_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'service': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '30', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'updated_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'watchers': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'people.team': {
            'Meta': {'object_name': 'Team'},
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'}),
            'total': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['people']

########NEW FILE########
__FILENAME__ = models
import logging
from urlparse import urlparse
from datetime import datetime, timedelta

from django.db import models, transaction
from django.conf import settings
from django.template.defaultfilters import slugify
from django.core.urlresolvers import reverse
from jsonfield import JSONField
from django.db.models.aggregates import Sum, Count
from django.utils.timezone import utc, now
from django.utils.html import strip_tags
from django.core.mail import mail_admins
from django.template import loader
import requests


class Commit(models.Model):
    """
    Commit record for the profile, the parent is the profile
    that way we can update the commit count and last commit timestamp
    in the same transaction.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True)
    hash = models.CharField(max_length=255, unique=True)
    author = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=255, blank=True)
    email = models.CharField(max_length=255, blank=True)
    message = models.CharField(max_length=2024, blank=True)
    url = models.CharField(max_length=512, blank=True)
    project = models.ForeignKey("Project", blank=True, null=True)
    timestamp = models.DateTimeField()
    created_on = models.DateTimeField(auto_now_add=True)
    files = JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u'Commit: %s' % self.hash

    @property
    def languages(self):
        langs = []
        if self.files:
            for f in self.files:
                langs.append(f.get('language'))
        langs = filter(None, langs)
        return set(langs)

    @classmethod
    def create_by_email(cls, email, commits, project=None):
        """Create a commit by email address"""
        return cls.create_by_auth_id(
            'email:%s' % email, commits, project=project)

    @classmethod
    def user_model(cls):
        return cls._meta.get_field('user').rel.to

    @classmethod
    def create_by_auth_id(cls, auth_id, commits, project=None):
        if not isinstance(commits, (list, tuple)):
            commits = [commits]

        user = cls.user_model().get_by_auth_id(auth_id)

        if user:
            return cls.create_by_user(user, commits, project=project)
        return cls.create_orphan(commits, project=project)

    @classmethod
    @transaction.commit_on_success
    def create_by_user(cls, user, commits, project=None):
        """Create a commit with parent user, updating users points."""
        created_commits = []

        if not user.is_active:
            return created_commits

        for c in commits:
            c['user'] = user
            c['project'] = project
            commit_hash = c.pop('hash', None)

            if commit_hash is None:
                logging.info("Commit hash missing in create.")
                continue
            commit, created = cls.objects.get_or_create(
                hash=commit_hash,
                defaults=c)
            if created:
                # increment the counts
                created_commits.append(commit)
            else:
                commit.user = user
                commit.save()

        # Check if there are no new commits and return
        if not created_commits:
            return []

        if project is not None:
            user.projects.add(project)
            user.save()

        # TODO: (Robert Myers) add a call to the defer a task to calculate
        # game stats in a queue?
        return created_commits

    @classmethod
    def create_orphan(cls, commits, project=None):
        """Create a commit with no parent."""
        created_commits = []
        for c in commits:
            c['project'] = project
            commit_hash = c.get('hash')

            if commit_hash is None:
                logging.info("Commit hash missing in create.")
                continue

            commit, created = cls.objects.get_or_create(
                hash=commit_hash,
                defaults=c)
            if created:
                created_commits.append(commit)

        return created_commits

    @classmethod
    def calendar(cls, game, **kwargs):
        """
        Returns number of commits per day for a date range.
        """
        count = cls.objects.filter(
            timestamp__range=(game.start, game.end), **kwargs) \
            .extra(select={'timestamp': 'date(timestamp)'}) \
            .values('timestamp').annotate(commit_count=Count('id'))
        resp = {
            'start': game.start.date(),
            'end': game.end.date(),
            'objects': list(count)
        }
        return resp


class Project(models.Model):
    """
    Project Model:

    This is either a brand new project or an already existing project
    such as #django, #fabric, #tornado, #pip, etc.

    When a user Tweets a url we can automatically create anew project
    for any of the repo host we know already. (github, bitbucket)
    """

    url = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    name = models.CharField(max_length=255, blank=True)
    forked = models.BooleanField(default=False)
    forks = models.IntegerField(default=0)
    watchers = models.IntegerField(default=0)
    parent_url = models.CharField(max_length=255, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    slug = models.SlugField()
    service = models.CharField(max_length=30, blank=True, default='')
    repo_id = models.IntegerField(blank=True, null=True)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        if self.name:
            return self.name
        else:
            return self.slug

    def save(self, *args, **kwargs):
        self.slug = self.project_name
        super(Project, self).save(*args, **kwargs)

    @property
    def points(self):
        try:
            board = self.board_set.latest()
        except:
            return 0
        return board.points

    @property
    def total(self):
        return self.points

    @property
    def project_name(self):
        return self.parse_project_name(self.url)

    def get_absolute_url(self):
        return reverse('project-details', args=[self.slug])

    @classmethod
    def create(cls, **kwargs):
        """Get or create shortcut."""
        repo_id = kwargs.get('repo_id')
        url = kwargs.get('url')
        slug = cls.parse_project_name(url)
        service = kwargs.get('service')

        # If the repo is on a service with no repo id, we can't handle renames.
        if not repo_id:
            project, created = cls.objects.get_or_create(
                slug=slug, defaults=kwargs)

        # Catch renaming of the repo.
        else:
            defaults = kwargs.copy()
            defaults['slug'] = slug
            project, created = cls.objects.get_or_create(
                service=service, repo_id=repo_id,
                defaults=defaults)
            if created and cls.objects.filter(slug=slug).count() > 1:
                # This is an old project that was created without a repo_id.
                project.delete()  # Delete the duplicate project
                project = cls.objects.get(slug=slug)

        if not project.active:
            # Don't bother updating this project and don't add commits.
            return None

        # Update stale project information.
        project.update(slug, created, **kwargs)
        return project

    @classmethod
    def _get_bitbucket_data(cls, **kwargs):
        """Update info from bitbucket if needed."""
        url = kwargs.get('url', '')
        parsed = urlparse(url)
        if parsed.netloc == 'bitbucket.org':
            # grab data from the bitbucket api
            # TODO: (rmyers) authenticate with oauth?
            api = 'https://bitbucket.org/api/1.0/repositories%s'
            try:
                r = requests.get(api % parsed.path)
                data = r.json()
                kwargs['description'] = data.get('description') or ''
                kwargs['forks'] = data.get('forks_count') or 0
                kwargs['watchers'] = data.get('followers_count') or 0
            except:
                logging.exception("Unable to parse: %s", url)
        return kwargs.iteritems()

    def update(self, slug, created, **kwargs):
        old = (now() - self.updated_on).seconds >= 21600
        if created or old or slug != self.slug:
            for key, value in self._get_bitbucket_data(**kwargs):
                setattr(self, key, value)
            self.slug = slug
            self.save()

    @classmethod
    def parse_project_name(cls, url):
        """
        Parse a project url and return a name for it.

        Example::

            Given:
              http://github.com/julython/julython.org
            Return:
              gh-julython-julython.org

        This is used as the Key name in order to speed lookups during
        api requests.
        """
        if not url:
            return
        hosts_lookup = {
            'github.com': 'gh',
            'bitbucket.org': 'bb',
        }
        parsed = urlparse(url)
        path = parsed.path
        if path.startswith('/'):
            path = path[1:]
        tokens = path.split('/')
        netloc_slug = parsed.netloc.replace('.', '-')
        host_abbr = hosts_lookup.get(parsed.netloc, netloc_slug)
        name = '-'.join(tokens)
        if name.endswith('-'):
            name = name[:-1]
        name = name.replace('.', '_')
        return '%s-%s' % (host_abbr, name)


class AchievedBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True)
    badge = models.ForeignKey("Badge", blank=True, null=True)
    achieved_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u'%s: %s' % (self.user, self.badge)


class Badge(models.Model):
    name = models.CharField(max_length=255, blank=True)
    text = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=2024, blank=True)

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name


class Group(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=64, blank=False)
    total = models.IntegerField(default=0)
    approved = models.BooleanField(default=False)
    rel_lookup = None
    lookup = None

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    def members_by_points(self):
        from july.game.models import Game
        latest = Game.active_or_latest()
        kwargs = {
            self.lookup: self
        }
        return latest.players.filter(**kwargs).order_by('-player__points')

    def total_points(self):
        from july.game.models import Game, Player
        latest = Game.active_or_latest()
        kwargs = {
            self.rel_lookup: self,
            'game': latest
        }
        query = Player.objects.filter(**kwargs)
        total = query.aggregate(Sum('points'))
        points = total.get('points__sum')
        return points or 0

    @classmethod
    def create(cls, name):
        slug = slugify(name)
        if not slug:
            return None

        defaults = {
            'name': name,
            'approved': cls.auto_verify,
        }
        obj, created = cls.objects.get_or_create(slug=slug, defaults=defaults)

        if created and not cls.auto_verify:
            html = loader.render_to_string(cls.template, {'slug': slug})
            text = strip_tags(html)
            subject = "[group] %s awaiting approval." % slug
            mail_admins(subject, text, html_message=html)
        return obj


class Location(Group):
    """Simple model for holding point totals and projects for a location"""
    template = 'registration/location.html'
    rel_lookup = 'user__location'
    lookup = 'location'
    auto_verify = True

    def get_absolute_url(self):
        from django.core.urlresolvers import reverse
        return reverse('location-detail', kwargs={'slug': self.slug})


class Team(Group):
    """Simple model for holding point totals and projects for a Team"""
    template = 'registration/team.html'
    rel_lookup = 'user__team'
    lookup = 'team'
    auto_verify = False

    def get_absolute_url(self):
        from django.core.urlresolvers import reverse
        return reverse('team-detail', kwargs={'slug': self.slug})


class Language(models.Model):
    """Model for holding points and projects per programming language."""

    name = models.CharField(max_length=64)

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = tests
# coding: utf-8
import datetime
import json
from pytz import UTC
from mock import MagicMock, patch

from django.test import TestCase
from django.template.defaultfilters import slugify

from july.models import User
from july.people.models import Location, Commit, Team, Project
from july.game.models import Game, Board, Player, LanguageBoard
from july.utils import check_location

import requests


class SCMTestMixin(object):
    """
    All scm endpoints should behave the same, and thus this set of test cases
    shall prove that statment.
    """

    AUTH_ID = "email:ted@example.com"
    API_URL = ""
    PROJECT_URL = ""
    USER = "bobby"
    payload = ""
    START = datetime.datetime(year=2012, month=12, day=1, tzinfo=UTC)
    # End of time itself
    END = datetime.datetime(year=2012, month=12, day=21, tzinfo=UTC)

    def setUp(self):
        self.requests = requests
        self.requests.post = MagicMock()
        self.user = self.make_user(self.USER)
        self.user.add_auth_id(self.AUTH_ID)
        self.game = Game.objects.create(start=self.START, end=self.END)

    @property
    def post(self):
        return self.make_post(self.payload)

    def make_post(self, post={}):
        return {'payload': json.dumps(post)}

    def make_user(self, username, **kwargs):
        return User.objects.create_user(username=username, **kwargs)

    def make_location(self, location, approved=True):
        slug = slugify(location)
        return Location.objects.create(name=location, slug=slug,
                                       approved=approved)

    def make_team(self, team, approved=True):
        slug = slugify(team)
        return Team.objects.create(name=team, slug=slug, approved=approved)

    def test_post_creates_commits(self):
        resp = self.client.post(self.API_URL, self.post)
        resp_body = json.loads(resp.content)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(resp_body['commits']), 2)
        self.assertEqual(self.requests.post.call_count, 6)

    def test_post_adds_points_to_user(self):
        self.client.post(self.API_URL, self.post)
        u = Player.objects.get(game=self.game, user=self.user)
        self.assertEqual(u.points, 12)
        self.assertEqual(self.requests.post.call_count, 6)

    def test_post_adds_points_to_project(self):
        self.client.post(self.API_URL, self.post)
        p = Board.objects.get(game=self.game, project__slug=self.PROJECT_SLUG)
        self.assertEqual(p.points, 12)
        self.assertEqual(self.requests.post.call_count, 6)

    def test_post_adds_project_to_commit(self):
        resp = self.client.post(self.API_URL, self.post)
        resp_body = json.loads(resp.content)
        c_hash = resp_body['commits'][0]
        commit = Commit.objects.get(hash=c_hash)
        self.assertEqual(commit.project.url, self.PROJECT_URL)
        self.assertEqual(commit.project.slug, self.PROJECT_SLUG)
        self.assertEqual(self.requests.post.call_count, 6)

    def test_post_adds_points_to_location(self):
        location = self.make_location('Austin, TX')
        self.user.location = location
        self.user.save()
        self.client.post(self.API_URL, self.post)
        self.assertEqual(self.game.locations[0].total, 12)
        self.assertEqual(self.requests.post.call_count, 6)

    def test_post_new_location(self):
        location = self.make_location('Austin, TX', approved=False)
        self.user.location = location
        self.user.save()
        self.client.post(self.API_URL, self.post)
        locations = [l for l in self.game.locations]
        self.assertEqual(len(locations), 0)
        self.assertEqual(self.requests.post.call_count, 6)

    def test_post_adds_points_to_project_model(self):
        resp = self.client.post(self.API_URL, self.post)
        resp_body = json.loads(resp.content)
        c_hash = resp_body['commits'][0]
        commit = Commit.objects.get(hash=c_hash)
        self.assertEqual(commit.project.total, 12)

    def test_post_adds_points_to_team(self):
        team = self.make_team('Rackers')
        self.user.team = team
        self.user.save()
        self.client.post(self.API_URL, self.post)
        self.assertEqual(self.game.teams[0].total, 12)
        self.assertEqual(self.requests.post.call_count, 6)

    def test_post_adds_points_to_language_boards(self):
        self.client.post(self.API_URL, self.post)
        number_of_languages = LanguageBoard.objects.all().count()
        self.assertEqual(number_of_languages, 4)

        python_board = LanguageBoard.objects.get(language__name='Python')
        self.assertEqual(python_board.points, 2)

        ruby_board = LanguageBoard.objects.get(language__name='Ruby')
        self.assertEqual(ruby_board.points, 1)

    def test_files(self):
        resp = self.client.post(self.API_URL, self.post)
        resp_body = json.loads(resp.content)
        c_hash = resp_body['commits'][0]
        commit = Commit.objects.get(hash=c_hash)
        # Assert commit files
        expected = [
            {"file": "filepath.rb", "type": "added", "language": "Ruby"},
            {"file": "test.py", "type": "modified", "language": "Python"},
            {"file": "README", "type": "modified",
             "language": "Documentation"},
            {"file": "frank.scheme", "type": "removed", "language": "Scheme"},
        ]
        self.assertEqual(commit.files, expected)

    def test_orphan(self):
        with patch.object(User, 'get_by_auth_id') as mock:
            mock.return_value = None
            self.client.post(self.API_URL, self.post)
            self.assertEqual([l for l in self.game.locations], [])
            self.assertEqual(self.requests.post.call_count, 4)

    def test_missing_payload(self):
        resp = self.client.post(self.API_URL, {})
        self.assertEqual(resp.status_code, 400)

    def test_malformed_payload(self):
        resp = self.client.post(self.API_URL, {"payload": "Bad Data"})
        self.assertEqual(resp.status_code, 400)

    def test_location_check(self):
        location = check_location(u'wrocław')
        self.assertEqual(location, 'Wroclaw, Poland')


class ReposTest(SCMTestMixin, TestCase):
    USER = 'bart'
    AUTH_ID = 'email:foo@example.com'
    API_URL = '/api/v1/github'
    PROJECT_URL = 'http://repo.or.cz/w/guppy.git'
    PROJECT_SLUG = 'repo-or-cz-w-guppy_git'
    payload = {
        "repository": {
            "owner": {
                "email": "foo@example.com",
                "name": ""
            },
            "pull_url": "git://repo.or.cz/guppy.git",
            "url": "http://repo.or.cz/w/guppy.git",
            "name": "guppy",
            "full_name": "guppy.git"
        },
        "after": "724618323963990f612a281f89738ad23bde862e",
        "commits": [
            {
                "author": {
                    "email": "foo@example.com",
                    "name": "bart"
                },
                "message": "Make karma more aggressive",
                "timestamp": "2012-12-15 23:01:18+0930",
                "url": "http://repo.or.cz/w/guppy.git/commit/72423bde862e",
                "id": "72461832396399",
                "added": ["filepath.rb"],
                "modified": ["test.py", "README"],
                "removed": ["frank.scheme"]
            },
            {
                "author": {
                    "email": "foo@example.com",
                    "name": "bart"
                },
                "message": "More Change",
                "timestamp": "2012-12-15 23:01:18+0930",
                "url": "http://repo.or.cz/w/guppy.git/commit/ad23bde862e",
                "id": "abde18323963990f612a2",
                "added": [],
                "modified": ["somefile.py"],
                "removed": []
            }
        ],
        "pusher": {
            "email": "foo@example.com",
            "name": "bart"
        },
        "ref": "refs/heads/master",
        "before":
        "f2e71a405da4cf86ff3e709547156be7be073082"}


class GithubTest(SCMTestMixin, TestCase):

    USER = 'defunkt'
    AUTH_ID = 'email:chris@ozmm.org'
    API_URL = '/api/v1/github'
    PROJECT_URL = 'http://github.com/defunkt/github'
    PROJECT_SLUG = 'gh-defunkt-github'
    payload = {
        "before": "5aef35982fb2d34e9d9d4502f6ede1072793222d",
        "repository": {
            "url": "http://github.com/defunkt/github",
            "name": "github",
            "description": "You're lookin' at it.",
            "watchers": 5,
            "forks": 2,
            "private": 1,
            "id": 1,
            "owner": {
                "email": "chris@ozmm.org",
                "name": "defunkt"
            }
        },
        "commits": [
            {
                "id": "41a212ee83ca127e3c8cf465891ab7216a705f59",
                "url": "http://github.com/defunkt/github/commit/41a212ee05f59",
                "author": {
                    "email": "chris@ozmm.org",
                    "name": "Chris Wanstrath"
                },
                "message": "okay i give in",
                "timestamp": "2012-12-15T14:57:17-08:00",
                "added": ["filepath.rb"],
                "modified": ["test.py", "README"],
                "removed": ["frank.scheme"]
            },
            {
                "id": "de8251ff97ee194a289832576287d6f8ad74e3d0",
                "url": "http://github.com/defunkt/github/commit/de8251ff9e3d0",
                "author": {
                    "email": "chris@ozmm.org",
                    "name": "Chris Wanstrath"
                },
                "modified": ["somefile.py"],
                "message": "update pricing a tad",
                "timestamp": "2012-12-15T14:36:34-08:00"
            }
        ],
        "after": "de8251ff97ee194a289832576287d6f8ad74e3d0",
        "ref": "refs/heads/master"
    }

    def test_repo_id(self):
        repo_id = 1
        payload = self.payload

        # Creating a Project with no repo_id
        del(payload['repository']['id'])
        self.client.post(self.API_URL, self.post)
        project = Project.objects.get(slug=self.PROJECT_SLUG)
        first_id = project.pk
        self.assertFalse(project.repo_id)

        # Catching more commits for the repo, this time with repo_id
        payload['repository']['id'] = repo_id
        self.client.post(self.API_URL, self.post)
        project = Project.objects.get(slug=self.PROJECT_SLUG)
        second_id = project.pk
        # Making sure repo_id was attached
        self.assertEquals(project.repo_id, repo_id)
        # Making sure we didn't create new projects.
        number_of_projects = Project.objects.all().count()
        self.assertEquals(number_of_projects, 1)
        self.assertEquals(first_id, second_id)

    def test_repo_renamed(self):
        repo = self.payload['repository']
        self.client.post(self.API_URL, self.post)
        project = Project.objects.get(repo_id=repo['id'])
        self.assertEquals(project.slug, self.PROJECT_SLUG)
        repo['url'] = 'http://github.com/defunkt/notgithub'
        repo['name'] = 'notgithub'
        self.client.post(self.API_URL, self.post)
        project = Project.objects.get(repo_id=repo['id'])
        self.assertNotEquals(project.slug, self.PROJECT_SLUG)
        self.assertEquals(project.url, repo['url'])
        self.assertEquals(project.name, repo['name'])


class BitbucketHandlerTests(SCMTestMixin, TestCase):

    USER = 'marcus'
    AUTH_ID = 'email:marcus@somedomain.com'
    API_URL = '/api/v1/bitbucket'
    PROJECT_URL = 'https://bitbucket.org/rmyers/cannula/'
    PROJECT_SLUG = 'bb-rmyers-cannula'
    payload = {
        "canon_url": "https://bitbucket.org",
        "commits": [
            {
                "author": "marcus",
                "branch": "featureA",
                "files": [
                    {
                        "file": "filepath.rb",
                        "type": "added"
                    },
                    {
                        "file": "test.py",
                        "type": "modified"
                    },
                    {
                        "file": "README",
                        "type": "modified"
                    },
                    {
                        "file": "frank.scheme",
                        "type": "removed"
                    }
                ],
                "message": "Added some featureA things",
                "node": "d14d26a93fd2",
                "parents": [
                    "1b458191f31a"
                ],
                "raw_author": "Marcus Bertrand <marcus@somedomain.com>",
                "raw_node": "1c0cd3b6f339bb95bfed14d26a93fd28d3166fa8",
                "revision": 3,
                "size": -1,
                "timestamp": "2012-12-05 06:07:03",
                "utctimestamp": "2012-12-05 04:07:03+00:00"
            },
            {
                "author": "marcus",
                "branch": "featureB",
                "files": [
                    {
                        "file": "somefile.py",
                        "type": "modified"
                    }
                ],
                "message": "Added some featureB things",
                "node": "d14d26a93fd2",
                "parents": [
                    "1b458191f31a"
                ],
                "raw_author": "Marcus Bertrand <marcus@somedomain.com>",
                "raw_node": "d14d26a93fd28d3166fa81c0cd3b6f339bb95bfe",
                "revision": 3,
                "size": -1,
                "timestamp": "2012-12-06 06:07:03",
                "utctimestamp": "2012-12-06 04:07:03+00:00"
            }
        ],
        "repository": {
            "absolute_url": "/rmyers/cannula/",
            "fork": False,
            "is_private": True,
            "name": "Project X",
            "owner": "marcus",
            "scm": "hg",
            "slug": "project-x",
            "website": ""
        },
        "user": "marcus"
    }

    def test_website_null(self):
        post = self.payload.copy()
        post['repository']['website'] = None
        payload = self.make_post(post)
        resp = self.client.post(self.API_URL, payload)
        resp_body = json.loads(resp.content)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(resp_body['commits']), 2)
        self.assertEqual(self.requests.post.call_count, 6)


class ProjectModelTests(TestCase):

    def test_parse_project_url(self):
        url = 'http://example.com/user/repo.git'
        self.assertEqual(
            Project.parse_project_name(url),
            'example-com-user-repo_git')

    def test_parse_none(self):
        self.assertEqual(None, Project.parse_project_name(None))

    def test_disabled_project(self):
        kwargs = {
            'name': 'foo',
            'url': 'http://example.com/user/repo',
            'repo_id': 1,
            'service': 'github',
        }
        Project.objects.create(active=False, **kwargs)
        project = Project.create(**kwargs)
        self.assertEqual(project, None)

    def test_total_points(self):
        p = Project.objects.create(url='http://example.com/user/repo')
        self.assertEqual(p.total, 0)
        self.assertEqual(p.points, 0)
        self.assertEqual(unicode(p), 'example-com-user-repo')

    def test_absolute_url(self):
        p = Project.objects.create(url='http://github.com/user/repo')
        self.assertEqual(p.get_absolute_url(), '/projects/gh-user-repo/')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from july.people import views


urlpatterns = patterns(
    'july.people.views',
    url(r'^(?P<username>[\w.@+-]+)/$',
        views.UserProfile.as_view(),
        name='member-profile'),
    url(r'^(?P<username>[\w.@+-]+)/edit/$',
        'edit_profile', name='edit-profile'),
    url(r'^(?P<username>[\w.@+-]+)/address/$',
        'edit_address', name='edit-address'),
    url(r'^(?P<username>[\w.@+-]+)/email/(?P<email>.*)$',
        'delete_email', name='delete-email'),
    url(r'^(?P<username>[\w.@+-]+)/project/(?P<slug>.*)$',
        'delete_project', name='delete-project'),
    url(r'^(?P<username>[\w.@+-]+)/projects/$',
        'people_projects', name='user-projects'),
    url(r'^(?P<username>[\w.@+-]+)/badges/$',
        'people_badges', name='user-badges'),
)

########NEW FILE########
__FILENAME__ = views
import logging
import json

from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template.context import RequestContext
from django.template.defaultfilters import slugify
from django.views.generic import detail
from django.utils.crypto import salted_hmac
from django.utils.translation import ugettext_lazy as _
from django.utils.http import int_to_base36
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives, mail_admins
from django.template import loader
from django.contrib.sites.models import get_current_site
from social_auth.models import UserSocialAuth

from july.settings import SECRET_KEY as SECRET
from july.models import User


class UserProfile(detail.DetailView):
    model = User
    slug_field = 'username'
    context_object_name = 'profile'
    slug_url_kwarg = 'username'

    def get_object(self):
        obj = super(UserProfile, self).get_object()
        if not obj.is_active:
            raise Http404("User not found")
        return obj


# TODO (rmyers): move the rest of these views to knockback/backbone routes


def people_projects(request, username):
    return HttpResponseRedirect(reverse('member-profile', args=[username]))


def people_badges(request, username):
    user = get_object_or_404(User, username=username)

    return render_to_response(
        'people/people_badges.html', {
            'badges': user.badges,
            'profile': user,
            'active': 'badges',
        },
        context_instance=RequestContext(request))


def send_verify_email(email, user_id, domain):
    token = salted_hmac(SECRET, email).hexdigest()
    c = {
        'email': email,
        'domain': domain,
        'uid': int_to_base36(user_id),
        'token': token
    }
    subject = _('Julython - verify your email')
    html = loader.render_to_string(
        'registration/verify_email.html', c)
    text = strip_tags(html)
    msg = EmailMultiAlternatives(subject, text, None, [email])
    msg.attach_alternative(html, 'text/html')
    try:
        msg.send()
    except:
        logging.exception("Unable to send email!")


@login_required
def edit_profile(request, username, template_name='people/edit.html'):
    from forms import EditUserForm
    user = request.user

    if user.username != request.user.username:
        http403 = HttpResponse("This ain't you!")
        http403.status = 403
        return http403

    form = EditUserForm(request.POST or None, user=request.user)

    if form.is_valid():
        for key, value in form.cleaned_data.iteritems():
            if key in ['gittip']:
                continue
            if key in ['email']:
                # send verification email
                domain = get_current_site(request).domain
                if value is not None:
                    send_verify_email(value, user.pk, domain)
                # Don't actually add email to user model.
                continue
            if key == 'team':
                # slugify the team to allow easy lookups
                setattr(user, 'team_slug', slugify(value))
            setattr(user, key, value)
        user.save()

        return HttpResponseRedirect(
            reverse('member-profile', kwargs={'username': user.username}))

    ctx = {
        'form': form,
        'profile': user,
        'active': 'edit',
    }
    return render(request, template_name,
                  ctx, context_instance=RequestContext(request))


@login_required
def edit_address(request, username, template_name='people/edit_address.html'):
    from forms import EditAddressForm

    user = request.user

    if user.key != request.user.key:
        http403 = HttpResponse("This ain't you!")
        http403.status = 403
        return http403

    form = EditAddressForm(request.POST or None, user=user)

    if form.is_valid():
        for key, value in form.cleaned_data.iteritems():
            setattr(user, key, value)
            user.put()
        return HttpResponseRedirect(
            reverse('member-profile', kwargs={'username': user.username})
        )

    ctx = {
        'form': form,
        'profile': user,
        'active': 'edit',
    }
    return render(request, template_name, ctx,
                  context_instance=RequestContext(request))


@login_required
def delete_email(request, username, email):

    # the ID we are to delete
    user = User.objects.get(username=username)
    auth = UserSocialAuth.objects.get(provider="email", uid=email)
    e_user = auth.user

    if user is None or e_user is None:
        raise Http404("User not found")

    if user != request.user or user != e_user:
        http403 = HttpResponse("This ain't you!")
        http403.status = 403
        return http403

    if request.method == "POST":
        # delete the email from the user
        auth.delete()
        return HttpResponseRedirect(
            reverse('member-profile',
                    kwargs={'username': request.user.username})
        )

    return render_to_response(
        'people/delete_email.html',
        {'email': email},
        context_instance=RequestContext(request)
    )


@login_required
def delete_project(request, username, slug):

    try:
        project = request.user.projects.get(slug=slug)
    except:
        raise Http404("Project Not Found")

    if request.method == "POST":
        # delete the project from the user
        request.user.projects.remove(project)
        request.user.save()
        return HttpResponseRedirect(
            reverse('member-profile',
                    kwargs={'username': request.user.username})
        )

    return render_to_response(
        'people/delete_project.html',
        {'project': project},
        context_instance=RequestContext(request)
    )

########NEW FILE########
__FILENAME__ = settings
import os
from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS as TCP
from django.core.exceptions import SuspiciousOperation

# Default settings that can be overwritten in secrets
DEBUG = True
SECRET_KEY = 'foobar'
DATABASE_ENGINE = 'django.db.backends.sqlite3'
DATABASE_NAME = 'julython.db'
DATABASE_PASSWORD = ''
DATABASE_SERVER = ''
DATABASE_USER = ''
LOGFILE_PATH = os.path.expanduser('~/julython.log')
TWITTER_CONSUMER_KEY = ''
TWITTER_CONSUMER_SECRET = ''
GITHUB_CONSUMER_KEY = ''
GITHUB_CONSUMER_SECRET = ''
GITHUB_APP_ID = GITHUB_CONSUMER_KEY
GITHUB_API_SECRET = GITHUB_CONSUMER_SECRET
EMAIL_HOST = '127.0.0.1'
EMAIL_PORT = '1025'

try:
    DEBUG = False
    from secrets import *
except ImportError:
    DEBUG = True

if DEBUG:
    import warnings
    warnings.filterwarnings(
        'error', r"DateTimeField received a naive datetime",
        RuntimeWarning, r'django\.db\.models\.fields')

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))

TEMPLATE_DEBUG = DEBUG

DEFAULT_FROM_EMAIL = 'Julython <mail@julython.org>'
SERVER_EMAIL = 'Julython <mail@julython.org>'
ADMINS = (
    ('Robert Myers', 'robert@julython.org'),
)

INTERNAL_IPS = ['127.0.0.1', 'localhost']

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': DATABASE_ENGINE,
        'NAME': DATABASE_NAME,
        'USER': DATABASE_USER,
        'PASSWORD': DATABASE_PASSWORD,
        'HOST': DATABASE_SERVER,
        'PORT': '',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# Timezone Support
USE_TZ = True

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = False

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(CURRENT_DIR, 'static_root')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(CURRENT_DIR, 'static'),
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'july.middleware.AbuseMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = TCP + (
    'django.core.context_processors.request',
)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': True,
    'HIDE_DJANGO_SQL': True,
    'ENABLE_STACKTRACES': True,
}

ROOT_URLCONF = 'july.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates"
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'july',
    'july.game',
    'july.people',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.contenttypes',
    'debug_toolbar',
    'social_auth',
    'south',
)

AUTHENTICATION_BACKENDS = [
    'july.auth.twitter.TwitterBackend',
    'july.auth.github.GithubBackend',
    'django.contrib.auth.backends.ModelBackend',
]

SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
SESSION_SAVE_EVERY_REQUEST = True

HCACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'TIMEOUT': 600,
    }
}

# Django 1.5 Custom User Model !! ftw
AUTH_USER_MODEL = 'july.User'
SOCIAL_AUTH_USER_MODEL = AUTH_USER_MODEL

SOCIAL_AUTH_DEFAULT_USERNAME = 'new_social_auth_user'
SOCIAL_AUTH_UUID_LENGTH = 3
SOCIAL_AUTH_PROTECTED_USER_FIELDS = ['email', 'location', 'url', 'description']
SOCIAL_AUTH_COMPLETE_URL_NAME = 'socialauth_complete'
SOCIAL_AUTH_ASSOCIATE_URL_NAME = 'socialauth_associate_complete'
SOCIAL_AUTH_PIPELINE = [
    'july.auth.social.social_auth_user',
    'social_auth.backends.pipeline.user.get_username',
    'social_auth.backends.pipeline.user.create_user',
    'social_auth.backends.pipeline.social.associate_user',
    'social_auth.backends.pipeline.social.load_extra_data',
    'social_auth.backends.pipeline.user.update_user_details',
]

# Just so we can use the same names for variables - why different social_auth??
GITHUB_APP_ID = GITHUB_CONSUMER_KEY
GITHUB_API_SECRET = GITHUB_CONSUMER_SECRET
GITHUB_EXTENDED_PERMISSIONS = ['user', 'public_repo']
TWITTER_EXTRA_DATA = [('screen_name', 'screen_name')]

ABUSE_LIMIT = 3


def skip_suspicious_ops(record):
    """Skip any errors with spoofed headers.

    ticket: https://code.djangoproject.com/ticket/19866
    """
    if record.exc_info:
        exc_type, exc_value = record.exc_info[:2]
        if isinstance(exc_value, SuspiciousOperation):
            return False
    return True


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
        'skip_suspicious_ops': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': skip_suspicious_ops,
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'simple',
            'maxBytes': 100000000,
            'backupCount': 3,
            'filename': LOGFILE_PATH,
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['skip_suspicious_ops', 'require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'propagate': True,
            'level': 'INFO',
        },
    }
}

# TODO(rmyers): fix tests to work with Django 1.6.1
TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

########NEW FILE########
__FILENAME__ = compress
#!/usr/bin/env python
import os
import optparse
import subprocess
import sys

here = os.path.dirname(__file__)

def main():
    usage = "usage: %prog [file1..fileN]"
    description = """With no file paths given this script will automatically
compress all jQuery-based files of the admin app. Requires the Google Closure
Compiler library and Java version 6 or later."""
    parser = optparse.OptionParser(usage, description=description)
    parser.add_option("-c", dest="compiler", default="~/bin/compiler.jar",
                      help="path to Closure Compiler jar file")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose")
    (options, args) = parser.parse_args()

    compiler = os.path.expanduser(options.compiler)
    if not os.path.exists(compiler):
        sys.exit("Google Closure compiler jar file %s not found. Please use the -c option to specify the path." % compiler)

    if not args:
        if options.verbose:
            sys.stdout.write("No filenames given; defaulting to admin scripts\n")
        args = [os.path.join(here, f) for f in [
            "actions.js", "collapse.js", "inlines.js", "prepopulate.js"]]

    for arg in args:
        if not arg.endswith(".js"):
            arg = arg + ".js"
        to_compress = os.path.expanduser(arg)
        if os.path.exists(to_compress):
            to_compress_min = "%s.min.js" % "".join(arg.rsplit(".js"))
            cmd = "java -jar %s --js %s --js_output_file %s" % (compiler, to_compress, to_compress_min)
            if options.verbose:
                sys.stdout.write("Running: %s\n" % cmd)
            subprocess.call(cmd.split())
        else:
            sys.stdout.write("File %s not found. Sure it exists?\n" % to_compress)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = tests
import datetime
import mock

from django.test import TestCase


class JulyViews(TestCase):

    def test_index(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)

    def test_help(self):
        resp = self.client.get('/help/')
        self.assertEqual(resp.status_code, 200)

    def test_live(self):
        resp = self.client.get('/live/')
        self.assertEqual(resp.status_code, 200)

    def test_register_get(self):
        resp = self.client.get('/register/')
        self.assertEqual(resp.status_code, 200)

    def test_register_bad(self):
        resp = self.client.post('/register/', {'Bad': 'field'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "This field is required.")

    def test_register_good(self):
        post = {
            'username': 'fred',
            'password1': 'secret',
            'password2': 'secret'
        }
        resp = self.client.post('/register/', post)
        self.assertRedirects(resp, '/')


class AbuseTests(TestCase):

    def test_set_abuse(self):
        from django.conf import settings
        settings.ABUSE_LIMIT = 3  # 3 times !

        from middleware import AbuseMiddleware
        today = datetime.date.today()
        request = mock.MagicMock()
        request.session = {}
        mid = AbuseMiddleware()

        abuse_reported = mid._abuse_reported(request)
        can_report_abuse = mid._can_report_abuse(request)

        abuse_reported()  # one
        self.assertEqual(
            request.session['abuse_date'],
            today - datetime.timedelta(days=2),
        )
        self.assertTrue(can_report_abuse())

        abuse_reported()  # two
        self.assertEqual(
            request.session['abuse_date'],
            today - datetime.timedelta(days=1),
        )
        self.assertTrue(can_report_abuse())

        abuse_reported()  # tree
        self.assertEqual(
            request.session['abuse_date'],
            today,
        )
        self.assertFalse(can_report_abuse())  # game is over !

    def test_reset_abuse(self):
        from django.conf import settings
        settings.ABUSE_LIMIT = 3

        from middleware import AbuseMiddleware
        today = datetime.date.today()
        request = mock.MagicMock()
        request.session = {'abuse_date': today-datetime.timedelta(days=10)}
        mid = AbuseMiddleware()

        abuse_reported = mid._abuse_reported(request)
        can_report_abuse = mid._can_report_abuse(request)

        abuse_reported()  # if abuse_date is old enugh it should be reseted
        self.assertEqual(
            request.session['abuse_date'],
            today - datetime.timedelta(days=2),
        )
        self.assertTrue(can_report_abuse())

        request.session = {'abuse_date': today-datetime.timedelta(days=3)}

        abuse_reported()
        self.assertEqual(
            request.session['abuse_date'],
            today - datetime.timedelta(days=2),
        )
        self.assertTrue(can_report_abuse())

        request.session = {'abuse_date': today-datetime.timedelta(days=2)}

        abuse_reported()
        self.assertEqual(
            request.session['abuse_date'],
            today - datetime.timedelta(days=1),
        )
        self.assertTrue(can_report_abuse())

        abuse_reported()
        self.assertEqual(
            request.session['abuse_date'],
            today,
        )
        self.assertFalse(can_report_abuse())

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib.auth import views as auth_views
from django.contrib import admin

from tastypie.api import Api

from july import api
from july.forms import PasswordResetForm

v1_api = Api(api_name='v1')
v1_api.register(api.CommitResource())
v1_api.register(api.ProjectResource())
v1_api.register(api.UserResource())
v1_api.register(api.LocationResource())
v1_api.register(api.TeamResource())
v1_api.register(api.LargeBoardResource())
v1_api.register(api.MediumBoardResource())
v1_api.register(api.SmallBoardResource())


admin.autodiscover()


urlpatterns = patterns(
    '',
    # This line should only be active during maintenance!
    #url(r'^.*', 'july.views.maintenance'),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^_admin/', admin.site.urls),
    # bitbucket and github are special apis
    url(r'^api/v1/bitbucket$', api.BitbucketHandler.as_view()),
    url(r'^api/v1/github$', api.GithubHandler.as_view()),
    url(r'^api/v1/github/(?P<path>.*)$', api.GithubAPIHandler.as_view()),
    # Tasty Pie apis
    url(r'^api/', include(v1_api.urls)),
    url(r'^$', 'july.views.index', name='index'),
    url(r'^live/', 'july.views.live', name='julython-live'),
    url(r'^help/', 'july.views.help_view', name='help'),
    url(r'^signin/$', auth_views.login, name="signin"),
    url(r'^register/$', 'july.views.register', name="register"),
    url(r'^email_verify/(?P<uidb36>[\d\w]+)-(?P<token>[\d\w-]+)$',
        'july.views.email_verify', name='email_verify'),
    url(r'^signout/$', auth_views.logout, {'next_page': '/'}, name="signout"),
    # Password reset urls
    url(r'^password_reset/$', auth_views.password_reset,
        {'password_reset_form': PasswordResetForm},
        name="password_reset"),
    url(r'^password_reset_sent/$', auth_views.password_reset_done,
        name="password_reset_done"),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/'
        r'(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.password_reset_confirm,
        {'post_reset_redirect': '/password_reset_complete/'},
        name='password_reset_confirm'),
    url(r'^password_reset_complete/$', auth_views.password_reset_complete,
        name='password_reset_complete'),
    url(r'^abuse$', 'july.views.send_abuse', name='abuse'),

    url(r'^accounts/profile', 'july.views.login_redirect'),
    url(r'^accounts/', include('social_auth.urls')),
    url(r'^', include('july.game.urls')),
    url(r'^', include('july.people.urls')),


)

########NEW FILE########
__FILENAME__ = utils
# coding: utf-8
import requests


def check_location(location):
    resp = requests.get(
        'http://maps.googleapis.com/maps/api/geocode/json',
        params={'address': location, 'sensor': 'false'})
    resp.raise_for_status()

    data = resp.json()
    if data['status'] == 'ZERO_RESULTS':
        return None
    try:
        return data['results'][0]['formatted_address']
    except (KeyError, IndexError):
        return None

########NEW FILE########
__FILENAME__ = views
import json

from django.utils.http import base36_to_int
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login
from django.contrib.auth import get_user_model
from django.shortcuts import render_to_response, render, redirect
from django.template import Context
from django.conf import settings
from django.core.mail import mail_admins
from django.http import HttpResponseRedirect
from django.http import HttpResponseNotFound
from django.http import HttpResponse

from july.game.models import Game
from july.forms import RegistrationForm

User = get_user_model()


def index(request):
    """Render the home page"""
    game = Game.active_or_latest()
    stats = game.histogram if game else []

    ctx = Context({
        'stats': json.dumps(stats),
        'game': game,
        'total': sum(stats),
        'user': request.user,
        'MEDIA_URL': settings.MEDIA_URL,
        'STATIC_URL': settings.STATIC_URL})

    return render_to_response('index.html', context_instance=ctx)


def help_view(request):
    """Render the help page"""
    ctx = Context({
        'user': request.user,
        'MEDIA_URL': settings.MEDIA_URL,
        'STATIC_URL': settings.STATIC_URL})

    return render_to_response('help.html', context_instance=ctx)


def register(request):
    """Register a new user"""
    if request.POST:
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            # To login immediately after registering
            user.backend = "django.contrib.auth.backends.ModelBackend"
            auth_login(request, user)
            return redirect('july.views.index')
    else:
        form = RegistrationForm()

    return render(
        request,
        'registration/register.html', {'form': form})


@login_required
def login_redirect(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/%s' % request.user.username)
    return HttpResponseRedirect('/')


def maintenance(request):
    """Site is down for maintenance, display this view for all."""
    ctx = Context({})

    return render_to_response('maintenance.html', context_instance=ctx)


def live(request):
    """Render the live view."""
    game = Game.active_or_latest()

    ctx = Context({
        'game': game,
        'user': request.user,
        'MEDIA_URL': settings.MEDIA_URL,
        'STATIC_URL': settings.STATIC_URL})

    return render_to_response('live/index.html', context_instance=ctx)


def email_verify(request, uidb36, token):
    """Verification for the user's email address."""

    try:
        uid_int = base36_to_int(uidb36)
        user = User.objects.get(pk=uid_int)
    except (ValueError, OverflowError, User.DoesNotExist):
        return HttpResponseNotFound()
    valid = user.find_valid_email(token)
    if valid:
        valid.extra_data['verified'] = True
        valid.save()
    return render(
        request, 'registration/email_verified.html', {'valid': valid})


def send_abuse(request):
    from forms import AbuseForm
    response = HttpResponse(
        json.dumps({}),
        content_type="application/json"
    )

    form = AbuseForm(request.POST)
    if form.is_valid():
        desc = form.data['desc']
        url = form.data['url']

        subject = 'Abuse report for %s' % url
        text = """\nUser %s has reported abuse for %s:\n\n%s""" % (
            request.user.username, url, desc)

        request.abuse_reported()
        mail_admins(subject, text)

    return response

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "july.settings")

    from django.core.management import execute_from_command_line
    
    execute_from_command_line(sys.argv)

########NEW FILE########
