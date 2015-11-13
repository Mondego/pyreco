__FILENAME__ = decorators
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from functools import wraps

from django.conf import settings
from django.http import HttpResponseRedirect

def anonymous_required(function=None):
    """
    Check if the user is anonymous, else redirect it
    """
    def _dec(view_func):
        @wraps(view_func)
        def _view(request, *args, **kwargs):
            if request.user is not None and request.user.is_authenticated():
                return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
            return view_func( request, *args, **kwargs )

        return _view

    if function is None:
        return _dec
    else:
        return _dec(function)

########NEW FILE########
__FILENAME__ = forms
from django import forms

# place form definition here
########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = urls
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import logout
from accounts.decorators import anonymous_required
from accounts.views import login

urlpatterns = patterns('',
    url(r'^manage/', login_required(direct_to_template), {'template': 'accounts/manage.html'}, name='accounts_manage'),
    url(r'^login/$', login, name='accounts_login'),
    url(r'^logged/$', direct_to_template, {'template': 'accounts/logged.html'}, name='logged'),
    url(r'^logout/', login_required(logout), { 'template_name': 'accounts/logged_out.html'}, name='accounts_logout'),
    url(r'', include('social_auth.urls')),
)

########NEW FILE########
__FILENAME__ = views
from django.views.generic.simple import direct_to_template

def login(request):
    if request.REQUEST.get('iframe', False):
        template = 'accounts/login_iframe.html'
    else:
        template = 'accounts/login.html'
    return direct_to_template(request, template)

########NEW FILE########
__FILENAME__ = context_processors
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.core.urlresolvers import resolve
from django.conf import settings

def caching(request):
    """
    Returns timeout to use in template caching
    """
    min_timeout = 1000000
    if settings.DEBUG:
        min_timeout = getattr(settings, 'DEBUG_MAX_TMPL_CACHE_TIMEOUT', None) or min_timeout
    return dict(cache_timeout=dict(
        repository_main_cell = min(86400, min_timeout),
        account_main_cell = min(86400, min_timeout),
        repository_owner_cell = min(86400, min_timeout),
        home_accounts = min(52, min_timeout),
        home_repositories = min(56, min_timeout),
        private_common_part = min(120, min_timeout),
        private_specific_part = min(300, min_timeout),
    ))

def design(request):
    """
    Some tools for design
    """

    section = None
    subsection = None

    # calculate the current section
    if request.path == '/':
        section = 'home'

    elif request.path.startswith('/search/'):
        section = 'search'
        if request.path.startswith('/search/users/'):
            subsection = 'accounts'
        else:
            subsection = 'repositories'

    elif request.path.startswith('/accounts/'):
        section = 'accounts'
        try:
            url_name = resolve(request.path).url_name
        except:
            pass
        else:
            # remove the "accounts_" part
            subsection = url_name[9:]

    elif request.path.startswith('/user/'):
        section = 'user'
        try:
            url_name = resolve(request.path).url_name
        except:
            pass
        else:
            # remove the "account_" part
            subsection = url_name[8:]

    elif request.path.startswith('/project/'):
        section = 'repository'
        try:
            url_name = resolve(request.path).url_name
        except:
            pass
        else:
            # remove the "repository_" part
            subsection = url_name[11:]

    elif request.path.startswith('/dashboard/'):
        section = 'dashboard'
        try:
            url_name = resolve(request.path).url_name
        except:
            pass
        else:
            # remove the "dashboard_" part
            subsection = url_name[10:]

    # final result
    return dict(
        section  = section,
        subsection = subsection,
        current_request = request.get_full_path(),
    )

def context_settings(request):
    return dict(
        SENTRY_DSN = settings.SENTRY_PUBLIC_DSN
    )

########NEW FILE########
__FILENAME__ = github
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from copy import copy
import base64

from pygithub3 import Github
from pygithub3.resources.repos import Repo
from pygithub3.exceptions import NotFound
from requests.exceptions import HTTPError

from django.conf import settings

from core.backends import BaseBackend, README_NAMES, README_TYPES


class GithubBackend(BaseBackend):

    name = 'github'
    auth_backend = 'github'
    needed_repository_identifiers = ('slug', 'official_owner',)
    support = copy(BaseBackend.support)
    support.update(dict(
        user_followers = True,
        user_following = True,
        user_repositories = True,
        user_created_date = True,
        repository_owner = True,
        repository_parent_fork = True,
        repository_followers = True,
        repository_contributors = True,
        repository_readme = True,
        repository_created_date = True,
        repository_modified_date = True,
    ))

    def __init__(self, *args, **kwargs):
        """
        Create an empty dict to cache Github instances
        """
        super(GithubBackend, self).__init__(*args, **kwargs)
        self._github_instances = {}

    @classmethod
    def enabled(cls):
        """
        Return backend enabled status by checking basic settings
        """
        return all(hasattr(settings, name) for name in ('GITHUB_APP_ID', 'GITHUB_API_SECRET'))

    def _get_exception(self, exception, what, token=None):
        """
        Return an internal exception (BackendError)
        """
        code = None
        if isinstance(exception, HTTPError):
            code = exception.response.status_code
        elif isinstance(exception, NotFound):
            code = 404
        return self.get_exception(code, what)

    def create_github_instance(self, *args, **kwargs):
        """
        Create a Github instance from the given parameters.
        Add, if not provided, the `requests_per_second` and `cache` ones.
        """
        if 'per_page' not in kwargs:
            kwargs['per_page'] = 100
        return Github(*args, **kwargs)

    def github(self, token=None):
        """
        Return (and if not exists create and cache) a Github instance
        authenticated for the given token, or an anonymous one if
        there is no token
        """
        token = token or None
        str_token = str(token)
        if str_token not in self._github_instances:
            params = {}
            if token:
                params['token'] = token.token
            self._github_instances[str_token] = self.create_github_instance(**params)
        return self._github_instances[str_token]

    def user_fetch(self, account, token=None):
        """
        Fetch the account from the provider and update the object
        """
        # get/create the github instance
        github = self.github(token)

        # get user data fromgithub
        try:
            guser = github.users.get(account.slug)
        except Exception, e:
            raise self._get_exception(e, '%s' % account.slug)

        # associate github user and account
        rmap = self.user_map(guser)
        for key, value in rmap.items():
            setattr(account, key, value)

    def user_map(self, user):
        """
        Map the given user, which is an object (or dict)
        got from the backend, to a dict usable for creating/updating
        an Account core object
        # in this backend, we attend User objects only
        """
        simple_mapping = dict(
            slug = 'login',
            name = 'name',
            homepage = 'blog',
            avatar = 'avatar_url',
            official_created = 'created_at',
            official_followers_count = 'followers',
            official_following_count = 'following',
            url = 'html_url',
        )

        result = {}

        for internal_key, backend_key in simple_mapping.items():
            value = getattr(user, backend_key, None)
            if value is not None:
                result[internal_key] = value

        if 'avatar' not in result and getattr(user, 'gravatar_id', None):
                result['avatar'] = 'http://www.gravatar.com/avatar/%s' % user.gravatar_id

        if 'url' not in result:
            result['url'] = 'https://github.com/%s/' % user.login

        return result

    def user_following(self, account, token=None):
        """
        Fetch the accounts followed by the given one
        """
        # get/create the github instance
        github = self.github(token)

        # get users data from github
        result = []
        try:
            for guser in github.users.followers.list_following(account.slug).iterator():
                result.append(self.user_map(guser))
        except Exception, e:
            raise self._get_exception(e, '%s\'s following' % account.slug)

        return result

    def user_followers(self, account, token=None):
        """
        Fetch the accounts following the given one
        """
        # get/create the github instance
        github = self.github(token)

        # get users data from github
        result = []
        try:
            for guser in github.users.followers.list(account.slug).iterator():
                result.append(self.user_map(guser))
        except Exception, e:
            raise self._get_exception(e, '%s\'s followers' % account.slug)

        return result

    def user_repositories(self, account, token=None):
        """
        Fetch the repositories owned/watched by the given accont
        """
        # get/create the github instance
        github = self.github(token)

        # get repositories data from github
        result = []
        found = {}
        try:
            for grepo in github.repos.watchers.list_repos(account.slug).iterator():
                repo = self.repository_map(grepo)
                if repo['project'] not in found:
                    result.append(repo)
                    found[repo['project']] = True
            for grepo in github.repos.list(account.slug).iterator():
                repo = self.repository_map(grepo)
                if repo['project'] not in found:
                    result.append(repo)
                    found[repo['project']] = True

        except Exception, e:
            raise self._get_exception(e, '%s\'s repositories' % account.slug)

        return result

    def repository_project(self, repository):
        """
        Return a project name the provider can use
        """
        if isinstance(repository, dict):
            if 'official_owner' in repository:
                # a mapped dict
                owner = repository['official_owner']
                slug = repository['slug']
        elif isinstance(repository, Repo):
            # a repository from pygithub3
            owner = repository.owner.login
            slug = repository.name
        else:
            # a Repository object (from core.models)
            if repository.owner_id:
                owner = repository.owner.slug
            else:
                owner = repository.official_owner
            slug = repository.slug
        return '/'.join([owner, slug])

    def parse_project(self, project):
        """
        Try to get at least a slug, and if the backend can, a user
        by using the given project name
        """
        owner,  name = project.split('/')
        return dict(slug = name, official_owner = owner)

    def repository_fetch(self, repository, token=None):
        """
        Fetch the repository from the provider and update the object
        """
        # get/create the github instance
        github = self.github(token)

        # get repository data fromgithub
        project = repository.get_project()
        project_parts = self.parse_project(project)
        try:
            grepo = github.repos.get(project_parts['official_owner'], project_parts['slug'])
        except Exception, e:
            raise self._get_exception(e, '%s' % project)

        # associate github repo to core one
        rmap = self.repository_map(grepo)
        for key, value in rmap.items():
            setattr(repository, key, value)

    def repository_map(self, repository):
        """
        Map the given repository, which is an object (or dict)
        got from the backend, to a dict usable for creating/updating
        a Repository core object
        # in this backend, we attend Repository objects only
        """

        simple_mapping = dict(
            slug = 'name',
            name = 'name',
            url = 'html_url',
            description = 'description',
            homepage = 'homepage',
            official_owner = 'owner',  # WARNING : It's an object !
            official_forks_count = 'forks',
            official_fork_of = 'parent',  # WARNING : It's an object !
            official_followers_count = 'watchers',
            is_fork = 'fork',
            private = 'private',
            official_created = 'created_at',
            official_modified = 'pushed_at',
            default_branch = 'master_branch',
        )

        result = {}

        for internal_key, backend_key in simple_mapping.items():
            value = getattr(repository, backend_key, None)
            if value is not None:
                result[internal_key] = value

        if 'official_owner' in result:
            result['official_owner'] = result['official_owner'].login
        if 'official_fork_of' in result:
            result['official_fork_of'] = self.repository_project(result['official_fork_of'])

        result['project'] = self.repository_project(result)

        return result

    def repository_followers(self, repository, token=None):
        """
        Fetch the accounts following the given repository
        """
        # get/create the github instance
        github = self.github(token)

        # get users data from github
        project = repository.get_project()
        project_parts = self.parse_project(project)
        result = []
        try:
            for guser in github.repos.watchers.list(project_parts['official_owner'], project_parts['slug']).iterator():
                result.append(self.user_map(guser))
        except Exception, e:
            raise self._get_exception(e, '%s\'s followers' % project)

        return result

    def repository_contributors(self, repository, token=None):
        """
        Fetch the accounts contributing the given repository
        For each account (dict) returned, the number of contributions is stored
        in ['__extra__']['contributions']
        """
        # get/create the github instance
        github = self.github(token)

        # get users data from github
        project = repository.get_project()
        project_parts = self.parse_project(project)
        result = []
        try:
            for guser in github.repos.list_contributors(project_parts['official_owner'], project_parts['slug']).iterator():
                account_dict = self.user_map(guser)
                # TODO : nb of contributions not used yet but later...
                account_dict.setdefault('__extra__', {})['contributions'] = guser.contributions
                result.append(account_dict)
        except Exception, e:
            raise self._get_exception(e, '%s\'s followers' % project)

        return result

    def repository_readme(self, repository, token=None):
        """
        Try to get a readme in the repository
        """
        # get/create the github instance
        github = self.github(token)

        project = repository.get_project()
        project_parts = self.parse_project(project)

        empty_readme = ('', None)

        # get all files at the root of the project
        try:
            tree = github.git_data.trees.get(
                sha = repository.default_branch or 'master',
                recursive = None,
                user = project_parts['official_owner'],
                repo = project_parts['slug'],
            )
        except NotFound:
            return empty_readme
        except Exception, e:
            raise self._get_exception(e, '%s\'s readme' % project)

        # filter readme files
        files = [f for f in tree.tree if f.get('type', None) == 'blob'
            and 'path' in f and any(f['path'].startswith(n) for n in README_NAMES)]

        # not readme file found, exit
        if not files:
            return empty_readme

        # get contents for all these files
        contents = []
        for fil in files:
            filename = fil['path']
            try:
                blob = github.git_data.blobs.get(
                    sha = fil['sha'],
                    user = project_parts['official_owner'],
                    repo = project_parts['slug'],
                )
            except NotFound:
                continue
            except Exception, e:
                raise self._get_exception(e, '%s\'s readme file' % repository.project)
            else:
                try:
                    content = blob.content
                    if blob.encoding == 'base64':
                        content = base64.decodestring(content)
                    contents.append((filename, content))
                except:
                    return empty_readme

        if not contents:
            return empty_readme

        # keep the biggest
        filename, content = sorted(contents, key=len)[-1]

        # find the type
        filetype = 'txt'
        try:
            extension = filename.split('.')[-1]
            for ftype, extensions in README_TYPES:
                if extension in extensions:
                    filetype = ftype
                    break
        except:
            pass

        return content, filetype


BACKENDS = {'github': GithubBackend, }

########NEW FILE########
__FILENAME__ = context_processors
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from core.backends import BACKENDS_BY_AUTH
from core.core_utils import get_user_accounts

def backends(request):
    return dict(
        backends_map = dict((backend.name, auth_backend) for auth_backend, backend in BACKENDS_BY_AUTH.items())
    )

def objects(request):
    return dict(
        user_accounts = get_user_accounts()
    )

########NEW FILE########
__FILENAME__ = core_utils
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

import re
import unicodedata

from django.utils.encoding import smart_unicode

from django_globals import globals

RE_SLUG = re.compile('[^\w-]')

def slugify(value):
    if not isinstance(value, unicode):
        value = smart_unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').lower()
    return RE_SLUG.sub('-', value).replace('_', '-')


def get_user_accounts():
    if not hasattr(globals, 'request'):
        return []
    if not hasattr(globals.request, '_accounts'):
        if globals.user and globals.user.is_authenticated():
                globals.request._accounts = globals.user.accounts.all().order_by('slug')
        else:
            globals.request._accounts = []
    return globals.request._accounts

########NEW FILE########
__FILENAME__ = exceptions
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from httplib import responses

class CoreException(Exception):
    pass

class InvalidIdentifiersForProject(CoreException):
    def __init__(self, backend, message=None):
        super(InvalidIdentifiersForProject, self).__init__(
            message or 'Invalid identifiers for the project. The %s backend says that you need %s' %
            (
                backend.name,
                backend.needed_repository_identifiers,
            )
        )

class OriginalProviderLoginMissing(CoreException):
    def __init__(self, user, backend_name, message=None):
        super(OriginalProviderLoginMissing, self).__init__(
            message or 'The original_login from the %s backend for the user %s is required' %
            (
                backend_name,
                user
            )
        )

class BackendError(CoreException):
    def __init__(self, message=None, code=None):
        if not message:
            if code and code in responses:
                message = 'An error prevent us to accomplish your request : %s' % responses[code]
            else:
                message = 'An undefined error prevent us to accomplish your request'
        super(BackendError, self).__init__(message)
        self.message = message
        self.code = code

    @staticmethod
    def make_for(backend_name, code=None, what=None):

        if code == 401:
            return BackendUnauthorizedError(backend_name, what)

        if code == 403:
            return BackendForbiddenError(backend_name, what)

        if code == 404:
            return BackendNotFoundError(backend_name, what)

        elif code >= 400 and code < 500:
            return BackendAccessError(code, backend_name, what)

        elif code >= 500:
            return BackendInternalError(code, backend_name, what)

        return BackendError(message=None, code=None)

class MultipleBackendError(BackendError):
    def __init__(self, messages):
        super(MultipleBackendError, self).__init__(
            'Many errors occured : ' + ', '.join(messages))
        self.messages = messages

class BackendNotFoundError(BackendError):
    def __init__(self, backend_name, what):
        super(BackendNotFoundError, self).__init__(
            '%s cannot be found on %s' % (what, backend_name), 404)

class BackendAccessError(BackendError):
    def __init__(self, code, message, backend_name, what):
        super(BackendAccessError, self).__init__(
            '%s cannot be accessed on %s: %s' % (what, backend_name, message), code)

class BackendForbiddenError(BackendAccessError):
    def __init__(self, backend_name, what):
        super(BackendForbiddenError, self).__init__(
                403, 'access forbidden', backend_name, what)


class BackendUnauthorizedError(BackendAccessError):
    def __init__(self, backend_name, what):
        super(BackendUnauthorizedError, self).__init__(
                401, 'unauthorized access', backend_name, what)

class BackendInternalError(BackendError):
    def __init__(self, code, backend_name, what):
        super(BackendError, self).__init__(
            '%s cannot be accessed because %s encountered an internal error' % (what, backend_name), code)


########NEW FILE########
__FILENAME__ = forms
from django import forms

# place form definition here
########NEW FILE########
__FILENAME__ = managers
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from copy import copy

from django.db import models
from django.conf import settings
from django.template import Context

from redisco import connection
from haystack import site

from utils.model_utils import queryset_iterator
from core import REDIS_KEYS
from core.backends import get_backend, get_backend_from_auth
from core.exceptions import OriginalProviderLoginMissing
from core.core_utils import slugify
from core.tokens import AccessToken

class SyncableModelManager(models.Manager):
    """
    Base manager for all syncable models
    """

    def get_redis_key(self, key):
        """
        Return the specific redis key for the current model
        """
        return REDIS_KEYS[key][self.model_name]

    def get_best_in_zset(self, key, size):
        """
        Return the `size` items with the best score in the given zset
        """
        ids = map(int, connection.zrevrange(self.get_redis_key(key), 0, size-1))
        objects = self.in_bulk(ids)
        return [objects[id] for id in ids if id in objects]

    def get_last_fetched(self, size=20):
        """
        Return the last `size` fetched objects
        """
        return self.get_best_in_zset('last_fetched', size)

    def get_best(self, size=20):
        """
        Return the `size` objects with the better score
        """
        return self.get_best_in_zset('best_scored', size)

    def update_external(self, print_delta=0, start=0, select_related=None):
        """
        Update search index and cached_templates for all objects
        """
        qs = self.all()
        if select_related:
            qs = qs.select_related(*select_related)
        if start:
            qs = qs.filter(pk__gte=start)
        qs = queryset_iterator(qs)
        #context = Context(dict(STATIC_URL=settings.STATIC_URL))
        search_index = site.get_index(self.model)
        for obj in qs:
            obj.update_search_index(search_index)
            #obj.update_cached_template(context)
            if print_delta and not obj.id % print_delta:
                print obj.id



class AccountManager(SyncableModelManager):
    """
    Manager for the Account model
    """
    model_name = 'account'

    def associate_to_social_auth_user(self, social_auth_user):
        auth_backend = social_auth_user.provider
        backend = get_backend_from_auth(auth_backend)

        access_token = social_auth_user.extra_data.get('access_token', None)
        original_login = social_auth_user.extra_data.get('original_login', None)

        if not original_login:
            raise OriginalProviderLoginMissing(social_auth_user.user, backend.name)

        account = self.get_or_new(backend.name, original_login)
        account.access_token = access_token
        account.user = social_auth_user.user
        account.deleted = False

        if account.fetch_needed():
            account.fetch()
        else:
            account.save()

        token = None
        if access_token:
            token = account.get_default_token()
            if not token:
                token = AccessToken.objects.create(
                    backend = account.backend,
                    login = account.slug,
                    token = access_token
                )

        is_new = not account.get_last_full_fetched()

        account.fetch_full(
            token = token,
            depth = 2 if is_new else 1,
            async = True,
            async_priority = 3 if is_new else 2,
        )

        return account

    def get_or_new(self, backend, slug, **defaults):
        """
        Try to get a existing accout, else create one (without saving it in
        database)
        If defaults is given, it's content will be used to create the new Account
        """
        account = self.get_for_slug(backend, slug)
        if account:
            if defaults:
                account.update_many_fields(**defaults)
        else:
            defaults = copy(defaults)
            allowed_fields = self.model._meta.get_all_field_names()
            defaults = dict((key, value) for key, value in defaults.items()
                if key in allowed_fields)
            defaults['backend'] = backend
            defaults['slug'] = slug
            account = self.model(**defaults)
        return account

    def get_for_slug(self, backend, slug):
        """
        Try to return an existing account object for this backend/slug
        If not found, return None
        """
        try:
            return self.get(backend=backend, slug_lower=slug.lower())
        except:
            return None



class OptimForListAccountManager(AccountManager):
    """
    Default `only` (fetch only some fields) and `select_related`
    """

    list_needed_fields = ('backend', 'status', 'slug', 'name', 'last_fetch', 'avatar', 'score', 'url', 'homepage', 'modified', 'deleted', 'official_created')
    list_select_related = ()

    def get_query_set(self):
        return super(OptimForListAccountManager, self).get_query_set().only(*self.list_needed_fields).select_related(*self.list_select_related)

class OptimForListWithoutDeletedAccountManager(OptimForListAccountManager):
    """
    Exclude deleted accounts
    """
    def get_query_set(self):
        return super(OptimForListWithoutDeletedAccountManager, self).get_query_set().exclude(deleted=True)


class RepositoryManager(SyncableModelManager):
    """
    Manager for the Repository model
    """
    model_name = 'repository'

    def get_or_new(self, backend, project=None, **defaults):
        """
        Try to get a existing accout, else create one (without saving it in
        database)
        If the project is given, get params from it
        This way we can manage projects with user+slug or without user
        """
        backend = get_backend(backend)

        defaults = copy(defaults)

        # get params from the project name
        if project:
            identifiers = backend.parse_project(project)
            for identifier in backend.needed_repository_identifiers:
                if identifiers.get(identifier, False):
                    defaults[identifier] = identifiers[identifier]

        # test that we have all needed defaults
        backend.assert_valid_repository_identifiers(**defaults)

        try:
            identifiers = dict((key, defaults[key].lower())
                for key in backend.needed_repository_identifiers)
            if 'slug' in identifiers and 'slug_lower' not in identifiers:
                identifiers['slug_lower'] = identifiers['slug']
                del identifiers['slug']
            if 'official_owner' in identifiers and 'official_owner_lower' not in identifiers:
                identifiers['official_owner_lower'] = identifiers['official_owner']
                del identifiers['official_owner']
            repository = self.get(backend=backend.name, **identifiers)
        except self.model.DoesNotExist:
            # remove empty defaults
            allowed_fields = self.model._meta.get_all_field_names()
            defaults = dict((key, value) for key, value in defaults.items()
                if key in allowed_fields)
            defaults['backend'] = backend.name

            repository = self.model(**defaults)
        else:
            if defaults:
                repository.update_many_fields(**defaults)

        return repository

    def slugify_project(self, project):
        """
        Slugify each part of a project, but keep the slashes
        """
        return '/'.join([slugify(part) for part in project.split('/')])

    def update_external(self, print_delta=0, start=0, select_related=None):
        if select_related is None:
            select_related = ('owner',)
        return super(RepositoryManager, self).update_external(print_delta, start, select_related)


class OptimForListRepositoryManager(RepositoryManager):
    """
    Default `only` (fetch only some fields) and `select_related`
    """

    # default fields for wanted repositories
    list_needed_fields = ['backend', 'status', 'project', 'slug', 'name', 'last_fetch', 'logo', 'url', 'homepage', 'score', 'is_fork', 'description', 'official_modified', 'owner', 'parent_fork', 'official_created', 'modified', 'deleted']
    # same for the parent fork
    list_needed_fields += ['parent_fork__%s' % field for field in list_needed_fields if field not in ('is_fork', 'parent_fork', 'description', 'official_created')]
    # and needed ones for owners
    list_needed_fields += ['owner__%s' % field for field in OptimForListAccountManager.list_needed_fields]
    list_needed_fields += ['parent_fork__owner__%s' % field for field in ('name', 'slug', 'status', 'backend', 'last_fetch')]

    list_select_related = ('owner', 'parent_fork', 'parent_fork__owner',)

    def get_query_set(self):
        return super(OptimForListRepositoryManager, self).get_query_set().only(*self.list_needed_fields).select_related(*self.list_select_related)

class OptimForListWithoutDeletedRepositoryManager(OptimForListRepositoryManager):
    """
    Exclude deleted repositories
    """
    def get_query_set(self):
        return super(OptimForListWithoutDeletedRepositoryManager, self).get_query_set().exclude(deleted=True)

########NEW FILE########
__FILENAME__ = messages
from django.contrib.messages import constants as levels
from django.contrib.auth.models import User

from offline_messages import utils as messages_utils

def get_user(user):
    """
    Try to return a User, the parameter can be:
    - a User object
    - a user id
    - a user id as a string
    - a username
    """
    if not user:
        return None
    if isinstance(user, User):
        return user
    try:
        if isinstance(user, basestring):
            if user.isdigit():
                user = int(user)
            else:
                return User.objects.get(username=user)
        if isinstance(user, int):
            return User.objects.get(id=user)
    except:
        return None

def add_message(user, level, message, content_object=None, meta={}):
    user = get_user(user)
    if not user:
        return None
    return messages_utils.create_offline_message(user, message, level, content_object=content_object, meta=meta)

def debug(user, message, **kwargs):
    return add_message(user, levels.DEBUG, message, **kwargs)

def info(user, message, **kwargs):
    return add_message(user, levels.INFO, message, **kwargs)

def success(user, message, **kwargs):
    return add_message(user, levels.SUCCESS, message, **kwargs)

def error(user, message, **kwargs):
    return add_message(user, levels.ERROR, message, **kwargs)


########NEW FILE########
__FILENAME__ = middleware
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from core.core_utils import get_user_accounts

class FetchFullCurrentAccounts(object):
    """
    Middleware that try to make a fetch full for all accounts of the current user
    """

    def process_request(self, request):
        accounts = get_user_accounts()
        if accounts:
            for account in accounts:
                account.fetch_full(
                    token = account.get_default_token(),
                    depth = 1,
                    async = True,
                    async_priority = 1,
                    notify_user = request.user,
                )

########NEW FILE########
__FILENAME__ = models
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from datetime import datetime, timedelta
from copy import copy
import math
import sys
import traceback

from django.db import models, transaction, IntegrityError, DatabaseError
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import simplejson
from django.core.cache import cache
from django.template import loader, Context
from django.utils.hashcompat import md5_constructor
from django.utils.http import urlquote
from django.contrib.contenttypes.generic import GenericRelation

from model_utils import Choices
from model_utils.models import TimeStampedModel
from model_utils.fields import StatusField
from haystack import site
from redisco.containers import List, Set, Hash, SortedSet

from core import REDIS_KEYS
from core.backends import BACKENDS, get_backend
from core.managers import (AccountManager, RepositoryManager,
                           OptimForListAccountManager, OptimForListRepositoryManager,
                           OptimForListWithoutDeletedAccountManager, OptimForListWithoutDeletedRepositoryManager)
from core.core_utils import slugify
from core.exceptions import MultipleBackendError, BackendNotFoundError
from core import messages as offline_messages

from tagging.models import PublicTaggedAccount, PublicTaggedRepository, PrivateTaggedAccount, PrivateTaggedRepository, all_official_tags
from tagging.words import get_tags_for_repository
from tagging.managers import TaggableManager
from notes.models import Note

from utils.model_utils import get_app_and_model, update as model_update
from utils import now_timestamp, dt2timestamp

BACKENDS_CHOICES = Choices(*BACKENDS.keys())

class SyncableModel(TimeStampedModel):
    """
    A base model usable for al objects syncable within a provider.
    TimeStampedModel add `created` and `modified` fields, auto updated
    when needed.
    """

    STATUS = Choices(
        ('creating', 'Creating'),                  # just created
        ('fetch_needed', 'Need to fetch object'),  # need to be updated
        ('need_related', 'Need to fetch related'), # related need to be updated
        ('updating', 'Updating'),                  # update running from the backend (not used)
        ('ok', 'Ok'),                              # everything ok ok
    )

    # it's forbidden to fetch if the last fetch is less than...
    MIN_FETCH_DELTA = getattr(settings, 'MIN_FETCH_DELTA', timedelta(minutes=30))
    MIN_FETCH_RELATED_DELTA = getattr(settings, 'MIN_FETCH_RELATED_DELTA', timedelta(minutes=30))
    # we need to fetch is the last fetch is more than
    MIN_FETCH_DELTA_NEEDED = getattr(settings, 'MIN_FETCH_DELTA_NEEDED', timedelta(hours=6))
    MIN_FETCH_RELATED_DELTA_NEEDED = getattr(settings, 'MIN_FETCH_RELATED_DELTA_NEEDED', timedelta(hours=6))
    # limit for auto fetch full
    MIN_FETCH_FULL_DELTA = getattr(settings, 'MIN_FETCH_FULL_DELTA', timedelta(days=2))

    # The backend from where this object come from
    backend = models.CharField(max_length=30, choices=BACKENDS_CHOICES, db_index=True)

    # A status field, using STATUS
    status = StatusField(max_length=15, db_index=True)
    deleted = models.BooleanField(default=False, db_index=True)

    # Date of last own full fetch
    last_fetch = models.DateTimeField(blank=True, null=True, db_index=True)

    # Store a score for this object
    score = models.PositiveIntegerField(default=0, db_index=True)

    # object's fields

    # The slug for this object (text identifier for the provider)
    slug = models.SlugField(max_length=255, db_index=True)
    # for speed search in get_or_new
    slug_lower = models.SlugField(max_length=255, db_index=True)
    # The same, adapted for sorting
    slug_sort = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    # The fullname
    name = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    # The web url
    url = models.URLField(max_length=255, blank=True, null=True)

    # backend errors
    backend_last_status = models.PositiveIntegerField(default=200)
    backend_same_status = models.PositiveIntegerField(default=0)
    backend_last_message = models.TextField(blank=True, null=True)

    note = GenericRelation(Note)

    # Fetch operations
    backend_prefix = ''
    related_operations = (
        # name, with count, with modified
    )

    class Meta:
        abstract = True

    @transaction.commit_manually
    def update(self, **kwargs):
        """
        Make an atomic update on the database, and fail gracefully
        """
        raise_if_error = kwargs.pop('raise_if_error', True)
        try:
            model_update(self, **kwargs)
        except (DatabaseError, IntegrityError), e:
            sys.stderr.write('\nError when updating %s with : %s\n' % (self, kwargs))
            sys.stderr.write(' => %s\n' % e)
            sys.stderr.write("====================================================================\n")
            sys.stderr.write('\n'.join(traceback.format_exception(*sys.exc_info())) + '\n')
            sys.stderr.write("====================================================================\n")
            transaction.rollback()
            if raise_if_error:
                raise e
        except:
            transaction.commit()
        else:
            transaction.commit()

    def __unicode__(self):
        return u'%s' % self.slug

    def is_new(self):
        """
        Return True if this object is a new one not saved in db
        """
        return self.status == 'creating' or not self.pk

    def __init__(self, *args, **kwargs):
        """
        Init some internal values
        """
        super(SyncableModel, self).__init__(*args, **kwargs)
        if not self.status:
            self.status = self.STATUS.creating

    def get_backend(self):
        """
        Return (and create and cache if needed) the backend object
        """
        if not hasattr(self, '_backend'):
            self._backend = get_backend(self.backend)
        return self._backend

    def get_new_status(self, for_save=False):
        """
        Return the status to be saved
        """
        # no id, object is in creating mode
        if not self.id and not for_save:
            return self.STATUS.creating

        # Never fetched of fetched "long" time ago => fetch needed
        if not self.last_fetch or self.last_fetch < datetime.utcnow() - self.MIN_FETCH_DELTA_NEEDED:
            return self.STATUS.fetch_needed

        # Work on each related field
        for name, with_count, with_modified in self.related_operations:
            if with_count:
                # count never updated => fetch of related needed
                count = getattr(self, '%s_count' % name)
                if count is None:
                    return self.STATUS.need_related
            if with_modified:
                # modified date never updated or too old => fetch of related needed
                date = getattr(self, '%s_modified' % name)
                if not date or date < datetime.utcnow() - self.MIN_FETCH_RELATED_DELTA_NEEDED:
                    return self.STATUS.need_related

        # else, default ok
        return self.STATUS.ok

    def save(self, *args, **kwargs):
        """
        Update the status before saving, and update some stuff (score, search index, tags)
        """
        self.status = self.get_new_status(for_save=True)
        super(SyncableModel, self).save(*args, **kwargs)
        self.update_related_data(async=True)

    def update_related_data(self, async=False):
        """
        Update data related to this object, as score,
        search index, public tags
        """
        if async:
            self_str = self.simple_str()
            to_update_set = Set(settings.WORKER_UPDATE_RELATED_DATA_SET_KEY)
            if self_str not in to_update_set:
                to_update_set.add(self_str)
                List(settings.WORKER_UPDATE_RELATED_DATA_KEY).append(self_str)
            return

        self.update_score()
        self.update_search_index()
        self.find_public_tags()

    def fetch_needed(self):
        """
        Check if a fetch is needed for this object.
        It's True if it's a new object, if the status is "fetch_needed" or
        if it's ok and fetched long time ago
        """
        self.status = self.get_new_status()
        if self.status  in (self.STATUS.creating, self.STATUS.fetch_needed,):
            return True
        return False

    def fetch_allowed(self):
        """
        Return True if a new fetch is allowed (not too recent)
        """
        if self.deleted:
            return False
        return bool(not self.last_fetch or self.last_fetch < datetime.utcnow() - self.MIN_FETCH_DELTA)

    def fetch(self, token=None, log_stderr=False):
        """
        Fetch data from the provider (need to be implemented in subclass)
        """
        return self.fetch_allowed()

    def fetch_related_needed(self):
        """
        Check if we need to update some related objects
        """
        self.status = self.get_new_status()
        if self.status in (self.STATUS.creating,):
            return False
        return self.status in (self.STATUS.fetch_needed, self.STATUS.need_related)

    def fetch_related_allowed(self):
        """
        Return True if a new fetch of related is allowed (if at least one is
        not too recent)
        """
        if self.deleted:
            return False
        for name, with_count, with_modified in self.related_operations:
            if not with_modified:
                continue
            if self.fetch_related_allowed_for(name):
                return True

        return False

    def last_fetch_related(self):
        """
        Get the last related modified date
        """
        last = None
        backend = self.get_backend()
        for name, with_count, with_modified in self.related_operations:
            if not with_modified:
                continue
            if not backend.supports(self.backend_prefix + name):
                continue
            date = getattr(self, '%s_modified' % name)
            if last is None or date > last:
                last = date

        return last

    def fetch_related_allowed_for(self, operation):
        """
        Return True if a new fetch of a related is allowed(if not too recent)
        """
        try:
            name, with_count, with_modified = [op for op in self.related_operations if op[0] == operation][0]
        except:
            return False

        if not with_modified:
            return True

        if not self.get_backend().supports(self.backend_prefix + operation):
            return False
        date = getattr(self, '%s_modified' % operation)
        if not date or date < datetime.utcnow() - self.MIN_FETCH_RELATED_DELTA:
            return True

        return False

    def fetch_related(self, limit=None, token=None, ignore=None, log_stderr=False):
        """
        If the object has some related content that need to be fetched, do
        it, but limit the fetch to the given limit (default 1)
        Returns the number of operations done
        """
        done = 0
        exceptions = []
        if ignore is None:
            ignore = []
        for name, with_count, with_modified in self.related_operations:
            if name in ignore:
                continue
            if not self.fetch_related_allowed_for(name):
                continue

            action = getattr(self, 'fetch_%s' % name)

            if log_stderr:
                sys.stderr.write("      - %s\n" % name)

            try:
                if action(token=token):
                    done += 1
            except Exception, e:
                if log_stderr:
                    sys.stderr.write("          => ERROR : %s\n" % e)
                exceptions.append(e)

            if limit and done >= limit:
                break
        if done:
            self.save()

        # handle one or many exceptions
        if exceptions:
            if len(exceptions) == 1:
                raise exceptions[0]
            else:
                raise MultipleBackendError([str(e) for e in exceptions])

        return done

    def update_many_fields(self, **params):
        """
        Update many fields on the object using ones
        found in `params`
        """
        if not params:
            return
        updated = 0
        for param, value in params.items():
            if not hasattr(self, param):
                continue
            field = getattr(self, param)
            if not callable(field) and field != value:
                setattr(self, param, value)
                updated += 1
        if updated:
            self.save()
        return updated

    def haystack_context(self):
        """
        Return a dict haystack can use to render a template for this object,
        as it does not, obviously, handle request and no context processors
        """
        return dict(
            STATIC_URL = settings.STATIC_URL,
        )

    def get_user_note(self, user=None):
        """
        Return the note for the current (or given) user
        """
        from private.views import get_user_note_for_object
        return get_user_note_for_object(self, user)

    def get_user_tags(self, user=None):
        """
        Return the tags for the current (or given) user
        """
        from private.views import get_user_tags_for_object
        return get_user_tags_for_object(self, user)

    def _compute_score_part(self, value):
        """
        Apply a mathematical operation to a value and return the result to
        be used as a part of a score
        """
        return math.sqrt(value)

    def _compute_final_score(self, parts, divider):
        """
        Take many parts of the score, a divider, and return a final score
        """
        score = sum(parts.values())/divider * 10
        if score > 0:
            return score * math.log1p(score) / 10
        else:
            return 0

    def prepare_score(self):
        """
        Prepare the computation of current score for this object
        """
        parts = dict(infos=0.0)
        divider = 0.0

        if self.name != self.slug:
            parts['infos'] += 0.3
        if self.homepage:
            parts['infos'] += 0.3
        if self.last_fetch:
            parts['infos'] += 0.3

        return parts, divider

    def compute_score(self):
        """
        Compute the final score of this object
        """
        parts, divider = self.prepare_score()
        return self._compute_final_score(parts, divider)

    def update_score(self, save=True):
        """
        Update the score and save it
        """
        if self.deleted:
            return

        self.score = int(round(self.compute_score()))
        if save:
            self.update(score=self.score)
        if self.score > 100:
            SortedSet(self.get_redis_key('best_scored')).add(self.id, self.score)

    def score_to_boost(self, force_compute=False):
        """
        Transform the score in a "boost" value usable by haystack
        """
        score = self.score
        if force_compute or not score:
            score = self.compute_score()
        return score/100.0

    def simple_str(self):
        """
        Return a unique string for this object, usable as a key (in redis or...)
        """
        return '%s:%d' % ('.'.join(get_app_and_model(self)), self.pk)

    def get_last_full_fetched(self):
        """
        Return the timestamp of the last fetch
        """
        return SortedSet(self.get_redis_key('last_fetched')).score(self.id)

    def fetch_full_allowed(self, delta=None):
        """
        Return True if a fetch_full can be done, respecting a delay
        """
        if delta is None:
            delta = self.MIN_FETCH_FULL_DELTA
        score = self.get_last_full_fetched()
        return not score or score < dt2timestamp(datetime.utcnow() - delta)

    def fetch_full(self, token=None, depth=0, async=False, async_priority=None,
                   notify_user=None, allowed_interval=None):
        """
        Make a full fetch of the current object : fetch object and related
        """

        # check if not done too recently
        if not self.fetch_full_allowed(allowed_interval):
            return token, None

        # init
        self_str = self.simple_str()
        redis_hash = Hash(settings.WORKER_FETCH_FULL_HASH_KEY)

        # manage async mode
        if async:
            if async_priority is None:
                async_priority = depth


            # check if already in a better priority list
            try:
                existing_priority = int(redis_hash[self_str])
            except:
                existing_priority = None
            if existing_priority is not None and existing_priority >= async_priority:
                return token, None

            sys.stderr.write("SET ASYNC (%d) FOR FETCH FULL %s #%d (token=%s)\n" % (depth, self, self.pk, token))

            # async : we serialize the params and put them into redis for future use
            data = dict(
                object = self_str,
                token = token.uid if token else None,
                depth = depth,
            )
            if notify_user:
                data['notify_user'] = notify_user.id if isinstance(notify_user, User) else notify_user

            # add the serialized data to redis
            data_s = simplejson.dumps(data)
            redis_hash[self_str] = async_priority
            List(settings.WORKER_FETCH_FULL_KEY % async_priority).append(data_s)

            # return dummy data when asyc
            return token, None

        else:
            del redis_hash[self_str]

        # ok, GO
        dmain = datetime.utcnow()
        fetch_error = None
        try:

            backend = self.get_backend()
            token_manager = backend.token_manager()

            token = token_manager.get_one(token)

            sys.stderr.write("FETCH FULL %s #%d (depth=%d, token=%s)\n" % (self, self.pk, depth, token))

            # start try to update the object
            try:
                df = datetime.utcnow()
                sys.stderr.write("  - fetch object (%s)\n" % self)
                fetched = self.fetch(token=token, log_stderr=True)
            except Exception, e:
                if isinstance(e, BackendError):
                    if e.code:
                        if e.code in (401, 403):
                            token.set_status(e.code, str(e))
                        elif e.code == 404:
                            self.set_backend_status(e.code, str(e))
                fetch_error = e
                ddf = datetime.utcnow() - df
                sys.stderr.write("      => ERROR (in %s) : %s\n" % (ddf, e))
                if notify_user:
                    offline_messages.error(notify_user, '%s couldn\'t be fetched' % self.str_for_user(notify_user).capitalize(), content_object=self, meta=dict(error = fetch_error))
            else:
                self.set_backend_status(200, 'ok')
                ddf = datetime.utcnow() - df
                sys.stderr.write("      => OK (%s) in %s [%s]\n" % (fetched, ddf, self.fetch_full_self_message()))

                # then fetch related
                try:
                    dr = datetime.utcnow()
                    sys.stderr.write("  - fetch related (%s)\n" % self)
                    nb_fetched = self.fetch_related(token=token, log_stderr=True)
                except Exception, e:
                    if isinstance(e, BackendError):
                        if e.code and e.code in (401, 403):
                            token.set_status(e.code, str(e))
                    ddr = datetime.utcnow() - dr
                    sys.stderr.write("      => ERROR (in %s): %s\n" % (ddr, e))
                    fetch_error = e
                    if notify_user:
                        offline_messages.error(notify_user, 'The related of %s couldn\'t be fetched' % self.str_for_user(notify_user), content_object=self, meta=dict(error = fetch_error))
                else:
                    ddr = datetime.utcnow() - dr
                    sys.stderr.write("      => OK (%s) in %s [%s]\n" % (nb_fetched, ddr, self.fetch_full_related_message()))

            if notify_user and not fetch_error:
                offline_messages.success(notify_user, '%s was correctly fetched' % self.str_for_user(notify_user).capitalize(), content_object=self)

            # finally, perform a fetch full of related
            if not fetch_error and depth > 0:
                self.fetch_full_specific(token=token, depth=depth, async=True)

            # save the date of last fetch
            SortedSet(self.get_redis_key('last_fetched')).add(self.id, now_timestamp())

        except Exception, e:
                fetch_error = e
                sys.stderr.write("      => MAIN ERROR FOR FETCH FULL OF %s: %s (see below)\n" % (self, e))
                sys.stderr.write("====================================================================\n")
                sys.stderr.write('\n'.join(traceback.format_exception(*sys.exc_info())))
                sys.stderr.write("====================================================================\n")

        finally:
            ddmain = datetime.utcnow() - dmain
            sys.stderr.write("END OF FETCH FULL %s in %s (depth=%d)\n" % (self, ddmain, depth))

            if token:
                token.release()

            return token, fetch_error

    def str_for_user(self, user):
        """
        Given a user, try to give a personified str for this object
        """
        return 'the %s "%s"' % (self.model_name, self)


    def set_backend_status(self, code, message, save=True):
        """
        Save informations about last status
        If the status is the same than the last one, keep the count
        by incrementing the value.
        """
        if code == self.backend_last_status:
            self.backend_same_status += 1
        else:
            self.backend_same_status = 1
        self.backend_last_status = code
        self.backend_last_message = message
        if save:
            self.save()

    def update_search_index(self, search_index=None):
        """
        Update the search index for the current object
        """
        if self.deleted:
            return

        try:
            if not search_index:
                search_index = self.get_search_index()
            search_index.update_object(self)
        except:
            pass

    def remove_from_search_index(self):
        """
        Remove the current object from the search index
        """
        try:
            self.get_search_index().remove_object(self)
        except:
            pass

    def update_count(self, name, save=True, async=False):

        """
        Update a saved count
        """
        if async:
            # async : we serialize the params and put them into redis for future use
            data = dict(
                object = self.simple_str(),
                count_type = name,
            )
            # add the serialized data to redis
            data_s = simplejson.dumps(data)
            List(settings.WORKER_UPDATE_COUNT_KEY).append(data_s)
            return

        field = '%s_count' % name
        count = getattr(self, name).count()
        if save:
            self.update(**{field: count})
        else:
            setattr(self, field, count)

    def fetch_related_entries(self, functionality, entry_name, entries_name, key, token=None):
        """
        Fech entries of type `entries_name` from the backend by calling the `functionality` method after
        testing its support.
        The `entry_name` is used for the needed add_%s and remove_%s methods
        """
        if not self.get_backend().supports(functionality):
            return False

        official_count_field = 'official_%s_count' % entries_name
        if hasattr(self, official_count_field) and not getattr(self, official_count_field) and (
            not self.last_fetch or self.last_fetch > datetime.utcnow()-timedelta(hours=1)):
                return False

        method_add_entry = getattr(self, 'add_%s' % entry_name)
        method_rem_entry = getattr(self, 'remove_%s' % entry_name)

        # get all previous entries
        check_diff = bool(getattr(self, '%s_count' % entries_name))
        if check_diff:
            old_entries = dict((getattr(obj, key), obj) for obj in getattr(self, entries_name).all())
            new_entries = set()

        # get and save new entries
        entries_list = getattr(self.get_backend(), functionality)(self, token=token)
        for gobj in entries_list:
            if check_diff and gobj[key] in old_entries:
                if check_diff:
                    new_entries.add(gobj[key])
            else:
                obj = method_add_entry(gobj, False)
                if obj:
                    if check_diff:
                        new_entries.add(getattr(obj, key))

        # remove old entries
        if check_diff:
            removed = set(old_entries.keys()).difference(new_entries)
            for key_ in removed:
                method_rem_entry(old_entries[key_], False)

        setattr(self, '%s_modified' % entries_name, datetime.utcnow())
        self.update_count(entries_name, async=True)

        return True

    def add_related_account_entry(self, account, self_entries_name, reverse_entries_name, update_self_count=True):
        """
        Make a call to `add_related_entry` with `repository` as `obj`.
        `account` can be an Account object, or a dict. In this case, it
        must contain a `slug` field.
        All other fields in `account` will only be used to fill
        the new Account fields if we must create it.
        """
        # we have a dict : get the account
        if isinstance(account, dict):
            if not account.get('slug', False):
                return None
            account = Account.objects.get_or_new(
                self.backend, account.pop('slug'), **account)

        # we have something else but an account : exit
        elif not isinstance(account, Account):
            return None

        return self.add_related_entry(account, self_entries_name, reverse_entries_name, update_self_count)

    def add_related_repository_entry(self, repository, self_entries_name, reverse_entries_name, update_self_count=True):
        """
        Make a call to `add_related_entry` with `repository` as `obj`.
        `repository` can be an Repository object, or a dict. In this case, it
        must contain enouhg identifiers (see `needed_repository_identifiers`)
        All other fields in `repository` will only be used to fill
        the new Repository fields if we must create it.
        """
        # we have a dict : get the repository
        if isinstance(repository, dict):
            try:
                self.get_backend().assert_valid_repository_identifiers(**repository)
            except:
                return None
            else:
                repository = Repository.objects.get_or_new(
                    self.backend, repository.pop('project', None), **repository)

        # we have something else but a repository : exit
        elif not isinstance(repository, Repository):
            return None

        return self.add_related_entry(repository, self_entries_name, reverse_entries_name, update_self_count)

    def add_related_entry(self, obj, self_entries_name, reverse_entries_name, update_self_count=True):
        """
        Try to add the `obj` in the `self_entries_name` list of the current object.
        `reverse_entries_name` is the name of the obj's list to put the current
        object in (reverse list)
        `obj` must be an object of the good type (Account or Repository). It's
        recommended to call add_related_account_entry and add_related_repository_entry
        instead of this method.
        """
        # save the object if it's a new one

        to_save = is_new = obj.is_new()
        if not is_new and obj.deleted:
            obj.deleted = False
            to_save = True

        if to_save:
            setattr(obj, '%s_count' % reverse_entries_name, 1)
            obj.save()

        # add the entry
        getattr(self, self_entries_name).add(obj)

        # update the count if we can
        if update_self_count:
            self.update_count(self_entries_name, async=True)

        # update the reverse count for the other object
        if not is_new:
            obj.update_count(reverse_entries_name, async=True)

        return obj

    def remove_related_account_entry(self, account, self_entries_name, reverse_entries_name, update_self_count=True):
        """
        Make a call to `remove_related_entry` with `account` as `obj`.
        `account` must be an Account instance
        """
        # we have something else but an account : exit
        if not isinstance(account, Account):
            return

        return self.remove_related_entry(account, self_entries_name, reverse_entries_name, update_self_count)

    def remove_related_repository_entry(self, repository, self_entries_name, reverse_entries_name, update_self_count=True):
        """
        Make a call to `remove_related_entry` with `repository` as `obj`.
        `repository` must be an Repository instance
        """
        # we have something else but a repository : exit
        if not isinstance(repository, Repository):
            return None

        return self.remove_related_entry(repository, self_entries_name, reverse_entries_name, update_self_count)

    def remove_related_entry(self, obj, self_entries_name, reverse_entries_name, update_self_count=True):
        """
        Remove the given object from the ones in the `self_entries_name` of the
        current object.
        `reverse_entries_name` is the name of the obj's list to remove the current
        object from (reverse list)
        `obj` must be an object of the good type (Account or Repository). It's
        recommended to call remove_related_account_entry and
        remove_related_repository_entry instead of this method.
        """
        # remove from the list
        getattr(self, self_entries_name).remove(obj)

        # update the count if we can
        if update_self_count:
            self.update_count(self_entries_name, async=True)

        # update the reverse count for the other object
        obj.update_count(reverse_entries_name, async=True)

        return obj

    def fake_delete(self, to_update):
        """
        Set the object as deleted and update all given field (*_count and
        *_modified, set to 0 and now() by subclasses)
        """
        to_update.update(dict(
            deleted = True,
            last_fetch = datetime.utcnow(),
            score = 0,
        ))
        self.update(**to_update)
        self.remove_from_search_index()
        SortedSet(self.get_redis_key('last_fetched')).remove(self.id)
        SortedSet(self.get_redis_key('best_scored')).remove(self.id)

    def get_redis_key(self, key):
        """
        Return the specific redis key for the current model
        """
        return REDIS_KEYS[key][self.model_name]

    def get_content_template(self):
        """
        Return the name of the template used to display the object
        """
        return 'front/%s_content.html' % self.model_name

    def get_anonymous_template_content(self, context=None, regenerate=False, partial=True):
        """
        Return the anonymous content template for this object, updating it
        in cache if needed, with partial caching (parts for authenticated users
        are not cached)
        """
        if not context:
            context = Context(dict(
                STATIC_URL = settings.STATIC_URL,
            ))
        context.update({
            'obj': self,
            '__regenerate__': regenerate,
            '__partial__': partial,
        })

        return loader.get_template(self.get_content_template()).render(context)

    def update_cached_template(self, context=None):
        """
        Update the cached template
        """
        args = md5_constructor(urlquote(self.id))
        cache_key = 'template.cache.%s_content.%s' % (self.model_name, args.hexdigest())
        cache.delete(cache_key)
        self.get_anonymous_template_content(context, regenerate=True, partial=True)

    def _get_url(self, url_type, **kwargs):
        """
        Construct the url for a permalink
        """
        if not url_type.startswith(self.model_name):
            url_type = '%s_%s' % (self.model_name, url_type)
        params = copy(kwargs)
        if 'backend' not in params:
            params['backend'] = self.backend
        return (url_type, (), params)

    def get_absolute_url(self):
        """
        Home page url for this object
        """
        return self._get_url('home')

    def get_about_url(self):
        """
        About page url for this object
        """
        return self._get_url('about')

    def get_edit_tags_url(self):
        """
        Url to edit tags for this object
        """
        return self._get_url('edit_tags')

    def get_edit_note_url(self):
        """
        Url to edit the note for this object
        """
        return self._get_url('edit_note')

    def count_taggers(self):
        """
        Return the number of users with at least one tag on this object
        """
        # TODO : must be a better way (group by ?)
        return len(set(self.private_tags_class.objects.filter(content_object=self).values_list('owner', flat=True)))

    def count_tags(self, tags_type=None):
        """
        """
        queryset = self.private_tags
        if tags_type == 'places':
            queryset = queryset.filter(name__startswith='@')
        elif tags_type == 'projects':
            queryset = queryset.filter(name__startswith='#')
        elif tags_type == 'starred':
            queryset = queryset.filter(slug='starred')
        elif tags_type == 'check-later':
            queryset = queryset.filter(slug='check-later')
        elif tags_type == 'tags':
            queryset = queryset.exclude(name__startswith='#').exclude(name__startswith='@').exclude(slug='check-later').exclude(slug='starred')

        return queryset.count()


class Account(SyncableModel):
    """
    Represent an account from a backend
    How load an account, the good way :
        Account.objects.get_or_new(backend, slug)
    """
    model_name = 'account'
    model_name_plural = 'accounts'
    search_type = 'people'
    content_type = settings.CONTENT_TYPES['account']
    public_tags_class = PublicTaggedAccount
    private_tags_class = PrivateTaggedAccount

    # it's forbidden to fetch if the last fetch is less than...
    MIN_FETCH_DELTA = getattr(settings, 'ACCOUNT_MIN_FETCH_DELTA', SyncableModel.MIN_FETCH_DELTA)
    MIN_FETCH_RELATED_DELTA = getattr(settings, 'ACCOUNT_MIN_FETCH_RELATED_DELTA', SyncableModel.MIN_FETCH_RELATED_DELTA)
    # we need to fetch is the last fetch is more than
    MIN_FETCH_DELTA_NEEDED = getattr(settings, 'ACCOUNT_MIN_FETCH_DELTA_NEEDED', SyncableModel.MIN_FETCH_DELTA_NEEDED)
    MIN_FETCH_RELATED_DELTA_NEEDED = getattr(settings, 'ACCOUNT_MIN_FETCH_RELATED_DELTA_NEEDED', SyncableModel.MIN_FETCH_RELATED_DELTA_NEEDED)
    # limit for auto fetch full
    MIN_FETCH_FULL_DELTA = getattr(settings, 'MIN_FETCH_FULL_DELTA', SyncableModel.MIN_FETCH_FULL_DELTA)

    # Basic informations

    # The avatar url
    avatar = models.URLField(max_length=255, blank=True, null=True)
    # The account's homeage
    homepage = models.URLField(max_length=255, blank=True, null=True)
    # Is this account private ?
    private = models.NullBooleanField(blank=True, null=True, db_index=True)
    # Account dates
    official_created = models.DateTimeField(blank=True, null=True)

    # If there is a user linked to this account
    user = models.ForeignKey(User, related_name='accounts', blank=True, null=True, on_delete=models.SET_NULL)

    # The last access_token for authenticated requests
    access_token = models.TextField(blank=True, null=True)

    # Followers informations

    # From the backed
    official_followers_count = models.PositiveIntegerField(blank=True, null=True)
    official_following_count = models.PositiveIntegerField(blank=True, null=True)
    # Saved counts
    followers_count = models.PositiveIntegerField(blank=True, null=True)
    following_count = models.PositiveIntegerField(blank=True, null=True)
    followers_modified = models.DateTimeField(blank=True, null=True)
    following_modified = models.DateTimeField(blank=True, null=True)
    # List of followed Account object
    following = models.ManyToManyField('self', related_name='followers', symmetrical=False)

    # List of owned/watched repositories
    repositories = models.ManyToManyField('Repository', related_name='followers')
    # Saved count
    repositories_count = models.PositiveIntegerField(blank=True, null=True)
    repositories_modified = models.DateTimeField(blank=True, null=True)

    # Count of contributed projects
    contributing_count = models.PositiveIntegerField(blank=True, null=True)

    # The managers
    objects = AccountManager()
    for_list = OptimForListWithoutDeletedAccountManager()
    for_user_list = OptimForListAccountManager()

    # tags
    public_tags = TaggableManager(through=public_tags_class, related_name='public_on_accounts')
    private_tags = TaggableManager(through=private_tags_class, related_name='private_on_accounts')

    # Fetch operations
    backend_prefix = 'user_'
    related_operations = (
        # name, with count, with modified
        ('following', True, True),
        ('followers', True, True),
        ('repositories', True, True),
    )

    class Meta:
        unique_together = (
            ('backend', 'slug'),
            ('backend', 'slug_lower')
        )

    def fetch(self, token=None, log_stderr=False):
        """
        Fetch data from the provider
        """
        if not super(Account, self).fetch(token, log_stderr):
            return False

        try:
            self.get_backend().user_fetch(self, token=token)
        except BackendNotFoundError, e:
            if self.id:
                self.fake_delete()
            raise e
        else:
            self.deleted = False

        self.last_fetch = datetime.utcnow()

        if not self.official_following_count:
            self.following_modified = self.last_fetch
            self.following_count = 0
            if self.following_count:
                for following in self.following.all():
                    self.remove_following(following, False)

        if not self.official_followers_count:
            self.followers_modified = self.last_fetch
            self.followers_count = 0
            if self.followers_count:
                for follower in self.followers.all():
                    self.remove_follower(follower, False)

        self.save()

        return True

    def save(self, *args, **kwargs):
        """
        Update the project and sortable fields
        """
        if self.slug:
            self.slug_sort = slugify(self.slug)
            self.slug_lower = self.slug.lower()
        super(Account, self).save(*args, **kwargs)

    def fetch_following(self, token=None):
        """
        Fetch the accounts followed by this account
        """
        return self.fetch_related_entries('user_following', 'following', 'following', 'slug', token=token)

    def add_following(self, account, update_self_count=True):
        """
        Try to add the account described by `account` as followed by
        the current account.
        """
        return self.add_related_account_entry(account, 'following', 'followers', update_self_count)

    def remove_following(self, account, update_self_count=True):
        """
        Remove the given account from the ones followed by
        the current account
        """
        return self.remove_related_account_entry(account, 'following', 'followers', update_self_count)

    def fetch_followers(self, token=None):
        """
        Fetch the accounts following this account
        """
        return self.fetch_related_entries('user_followers', 'follower', 'followers', 'slug', token=token)

    def add_follower(self, account, update_self_count=True):
        """
        Try to add the account described by `account` as follower of
        the current account.
        """
        return self.add_related_account_entry(account, 'followers', 'following', update_self_count)

    def remove_follower(self, account, update_self_count=True):
        """
        Remove the given account from the ones following
        the current account
        """
        return self.remove_related_account_entry(account, 'followers', 'following', update_self_count)

    def fetch_repositories(self, token=None):
        """
        Fetch the repositories owned/watched by this account
        """
        return self.fetch_related_entries('user_repositories', 'repository', 'repositories', 'project', token=token)

    def add_repository(self, repository, update_self_count=True):
        """
        Try to add the repository described by `repository` as one
        owner/watched by the current account.
        """
        return self.add_related_repository_entry(repository, 'repositories', 'followers', update_self_count)

    def remove_repository(self, repository, update_self_count):
        """
        Remove the given account from the ones the user own/watch
        """
        # mark the repository as deleted if it is removed from it's owner account
        if repository.owner_id and repository.owner_id == self.id:
            repository.fake_delete()

        return self.remove_related_repository_entry(repository, 'repositories', 'followers', update_self_count)

    @models.permalink
    def _get_url(self, url_type, **kwargs):
        """
        Construct the url for a permalink
        """
        (url_type, args, kwargs) = super(Account, self)._get_url(url_type, **kwargs)
        if 'slug' not in kwargs:
            kwargs['slug'] = self.slug
        return (url_type, args, kwargs)

    def get_followers_url(self):
        """
        Followers page url for this Account
        """
        return self._get_url('followers')

    def get_following_url(self):
        """
        Following page url for this Account
        """
        return self._get_url('following')

    def get_repositories_url(self):
        """
        Repositories page url for this Account
        """
        return self._get_url('repositories')

    def get_contributing_url(self):
        """
        Contributing page url for this Account
        """
        return self._get_url('contributing')

    def following_ids(self):
        """
        Return the following as a list of ids
        """
        if not hasattr(self, '_following_ids'):
            self._following_ids = self.following.values_list('id', flat=True)
        return self._following_ids

    def followers_ids(self):
        """
        Return the followers as a list of ids
        """
        if not hasattr(self, '_followers_ids'):
            self._followers_ids = self.followers.values_list('id', flat=True)
        return self._followers_ids

    def prepare_score(self):
        """
        Compute the current score for this account
        """
        parts, divider = super(Account, self).prepare_score()
        backend = self.get_backend()

        # boost if registered user
        if self.user_id:
            parts['user'] = 2

        if backend.supports('user_created_date'):
            now = datetime.utcnow()
            divider += 0.5
            if not self.official_created:
                parts['life_time'] = 0
            else:
                parts['life_time'] = self._compute_score_part((now - self.official_created).days / 90.0)

        if backend.supports('user_followers'):
            divider += 1
            parts['followers'] = self._compute_score_part(self.official_followers_count or 0)

        if backend.supports('repository_owner'):
            divider += 1
            repositories_score = []
            for repository in self.own_repositories.all():
                repo_parts, repo_divider = repository.prepare_main_score()
                repositories_score.append(self._compute_final_score(repo_parts, repo_divider))
            if repositories_score:
                min_score = sum(repositories_score) / float(len(repositories_score)) - 0.1
                repos = [score for score in repositories_score if score >= min_score]
                avg = sum(repos) / float(len(repos))
                parts['repositories'] = avg

        if backend.supports('repository_contributors'):
            divider += 1
            if self.contributing_count:
                parts['contributing'] = self._compute_score_part(self.contributing_count)


        #print parts
        return parts, divider

    def score_to_boost(self, force_compute=False):
        """
        Transform the score in a "boost" value usable by haystack
        """
        score = super(Account, self).score_to_boost(force_compute=force_compute)
        return math.log10(max(score*100, 5) / 2.0) - 0.3

    def find_public_tags(self):
        """
        Update the public tags for this accounts.
        """
        tags = {}
        # we use values for a big memory optimization on accounts with a lot of repositories
        rep_tagged_items = PublicTaggedRepository.objects.filter(content_object__followers=self).values('content_object__is_fork', 'content_object__owner__id', 'tag__slug', 'weight')
        for tagged_item in rep_tagged_items:
            divider = 1.0
            slug = tagged_item['tag__slug']
            if tagged_item['content_object__is_fork']:
                divider = 2
            if tagged_item['content_object__owner__id'] != self.id:
                divider = divider * 3
            if slug not in tags:
                tags[slug] = 0
            tags[slug] += (tagged_item['weight'] or 1) / divider

        tags = sorted(tags.iteritems(), key=lambda t: t[1], reverse=True)

        self.public_tags.set(tags[:5])

        # force cache update
        self.all_public_tags(force_cache=True)

    def all_public_tags(self, with_weight=False, force_cache=False):
        """
        Return all public tags for this account.
        Use this instead of self.public_tags.all() because
        we set the default order
        If `with_weight` is True, return the through model of the tagging
        system, with tags and weight.
        Else simply returns tags.
        in both cases, sort is by weight (desc) and slug (asc)
        """
        if not hasattr(self, '_all_public_tags'):
            self._all_user_tags = {}
        if with_weight not in self._all_user_tags:
            if with_weight:
                result = self.publictaggedaccount_set.select_related('tag').all()
            else:
                cache_key = self.get_redis_key('public_tags') % self.id
                tags = None
                if not force_cache:
                    tags = cache.get(cache_key)
                if tags is None:
                    tags = self.public_tags.order_by('-public_account_tags__weight', 'slug')
                    cache.set(cache_key, tags, 2678400)
                result = tags
            self._all_user_tags[with_weight] = result
        return self._all_user_tags[with_weight]

    def all_private_tags(self, user):
        """
        Return all private tags for this account set by the given user.
        Use this instead of self.private_tags.filter(owner=user) because
        we set the default order
        """
        return self.private_tags.filter(private_account_tags__owner=user).order_by('-private_account_tags__weight', 'slug').distinct()

    def links_with_user(self, user):
        """
        Return informations about some links between this account and the given user
        """
        backend = self.get_backend()
        links = {}

        if self.user_id == user.id:
            links['self'] = self.user

        if backend.supports('user_following'):
            followed = self.following.filter(user=user)
            if followed:
                links['followed'] = followed

        if backend.supports('user_followers'):
            following = self.followers.filter(user=user)
            if following:
                links['following'] = following

        if backend.supports('repository_followers'):
            project_following = Repository.objects.filter(owner=self, followers__user=user)
            if project_following:
                links['project_following'] = project_following
            project_followed = Repository.objects.filter(owner__user=user, followers=self)
            if project_followed:
                links['project_followed'] = project_followed

        return links

    def get_default_token(self):
        """
        Return the token object for this account
        """
        return self.get_backend().token_manager().get_for_account(self)

    def fetch_full_self_message(self):
        """
        Return the message part to display after a fetch of the object during a fetch_full
        """
        return 'fwr=%s, fwg=%s' % (self.official_followers_count, self.official_following_count)

    def fetch_full_related_message(self):
        """
        Return the message part to display after a fetch of the related during a fetch_full
        """
        return 'fwr=%s, fwg=%s, rep=%s' % (self.followers_count, self.following_count, self.repositories_count)

    def fetch_full_specific(self, depth=0, token=None, async=False):
        """
        After the full fetch of the account, try to make a full fetch of all
        related objects: repositories, followers, following
        """
        if depth > 0:
            depth -= 1

            # do fetch full for all repositories
            sys.stderr.write(" - full fetch of repositories (for %s)\n" % self)
            for repository in self.repositories.all():
                token, rep_fetch_error = repository.fetch_full(depth=depth, token=token, async=async)

                # access token invalidated, get a new one
                if rep_fetch_error and rep_fetch_error.code in (401, 403):
                    token = None

            # do fetch for all followers
            sys.stderr.write(" - full fetch of followers (for %s)\n" % self)
            for account in self.followers.all():
                token, rep_fetch_error = account.fetch_full(depth=depth, token=token, async=async)

                # access token invalidated, get a new one
                if rep_fetch_error and rep_fetch_error.code in (401, 403):
                    token = None

            # do fetch for all following
            sys.stderr.write(" - full fetch of following (for %s)\n" % self)
            for account in self.following.all():
                token, rep_fetch_error = account.fetch_full(depth=depth, token=token, async=async)

                # access token invalidated, get a new one
                if rep_fetch_error and rep_fetch_error.code in (401, 403):
                    token = None

    def get_search_index(self):
        """
        Return the search index for this model
        """
        return site.get_index(Account)

    def fake_delete(self):
        """
        Set the account as deleted and remove if from every automatic
        lists (not from ones created by users : tags, notes...)
        """
        to_update = {}
        now = datetime.utcnow()

        # manage following
        for account in self.following.all():
            account.update(
                followers_count = models.F('followers_count') - 1,
                raise_if_error = False
            )
        self.following.clear()
        to_update['following_count'] = 0
        to_update['following_modified'] = now

        # manage followers
        for account in self.followers.all():
            account.update(
                following_count = models.F('following_count') - 1,
                raise_if_error = False
            )
        self.followers.clear()
        to_update['followers_count'] = 0
        to_update['followers_modified'] = now

        # manage repositories
        for repository in self.repositories.all():
            if repository.owner_id == self.id:
                repository.fake_delete()
            else:
                repository.update(
                    followers_count = models.F('followers_count') - 1,
                raise_if_error = False
                )
        self.repositories.clear()
        to_update['repositories_count'] = 0
        to_update['repositories_modified'] = now

        # manage contributing
        for repository in self.contributing.all():
            repository.update(
                contributors_count = models.F('contributors_count') - 1,
                raise_if_error = False
            )
        self.contributing.clear()
        to_update['contributing_count'] = 0

        # final update
        to_update['user'] = None
        super(Account, self).fake_delete(to_update)

    def str_for_user(self, user):
        """
        Given a user, try to give a personified str for this account
        """
        user = offline_messages.get_user(user)
        default = super(Account, self).str_for_user(user)
        if not user or not self.user or self.user != user:
            return default
        return 'your account "%s"' % self


class Repository(SyncableModel):
    """
    Represent a repository from a backend
    How load a repository, the good way :
        Repository.objects.get_or_new(backend, project_name)
    """
    model_name = 'repository'
    model_name_plural = 'repositories'
    search_type = 'repositories'
    content_type = settings.CONTENT_TYPES['repository']
    public_tags_class = PublicTaggedRepository
    private_tags_class = PrivateTaggedRepository

    # it's forbidden to fetch if the last fetch is less than...
    MIN_FETCH_DELTA = getattr(settings, 'REPOSITORY_MIN_FETCH_DELTA', SyncableModel.MIN_FETCH_DELTA)
    MIN_FETCH_RELATED_DELTA = getattr(settings, 'REPOSITORY_MIN_FETCH_RELATED_DELTA', SyncableModel.MIN_FETCH_RELATED_DELTA)
    # we need to fetch is the last fetch is more than
    MIN_FETCH_DELTA_NEEDED = getattr(settings, 'REPOSITORY_MIN_FETCH_DELTA_NEEDED', SyncableModel.MIN_FETCH_DELTA_NEEDED)
    MIN_FETCH_RELATED_DELTA_NEEDED = getattr(settings, 'REPOSITORY_MIN_FETCH_RELATED_DELTA_NEEDED', SyncableModel.MIN_FETCH_RELATED_DELTA_NEEDED)
    # limit for auto fetch full
    MIN_FETCH_FULL_DELTA = getattr(settings, 'MIN_FETCH_FULL_DELTA', SyncableModel.MIN_FETCH_FULL_DELTA)

    # Basic informations

    # The description of this repository
    description = models.TextField(blank=True, null=True)
    # The project's logo url
    logo = models.URLField(max_length=255, blank=True, null=True)
    # The project's homeage
    homepage = models.URLField(max_length=255, blank=True, null=True)
    # The canonical project name (example twidi/myproject)
    project = models.TextField(db_index=True)
    # The same, adapted for sorting
    project_sort = models.TextField(db_index=True)
    # Is this repository private ?
    private = models.NullBooleanField(blank=True, null=True, db_index=True)
    # Repository dates
    official_created = models.DateTimeField(blank=True, null=True)
    official_modified = models.DateTimeField(blank=True, null=True)

    # Owner

    # The owner's "slug" of this project, from the backend
    official_owner = models.CharField(max_length=255, blank=True, null=True)
    # for speed search in get_or_new
    official_owner_lower = models.CharField(max_length=255, blank=True, null=True)
    # The Account object whom own this Repository
    owner = models.ForeignKey(Account, related_name='own_repositories', blank=True, null=True, on_delete=models.SET_NULL)

    # Forks & followers informations

    # Forks count (from the backend)
    official_forks_count = models.PositiveIntegerField(blank=True, null=True)
    # Project name of the repository from which this repo is the fork (from the backend)
    official_fork_of = models.TextField(blank=True, null=True)
    # Saved count
    forks_count = models.PositiveIntegerField(blank=True, null=True)

    # Followers count (from the backend)
    official_followers_count = models.PositiveIntegerField(blank=True, null=True)
    # Saved count
    followers_count = models.PositiveIntegerField(blank=True, null=True)
    followers_modified = models.DateTimeField(blank=True, null=True)

    # Set to True if this Repository is a fork of another
    is_fork = models.NullBooleanField(blank=True, null=True)
    # The Repository object from which this repo is the fork
    parent_fork = models.ForeignKey('self', related_name='forks', blank=True, null=True, on_delete=models.SET_NULL)

    # List of owned/watched contributors
    contributors = models.ManyToManyField('Account', related_name='contributing')
    # Saved count
    contributors_count = models.PositiveIntegerField(blank=True, null=True)
    contributors_modified = models.DateTimeField(blank=True, null=True)

    # more about the content of the reopsitory
    default_branch = models.CharField(max_length=255, blank=True, null=True)
    readme = models.TextField(blank=True, null=True)
    readme_type = models.CharField(max_length=10, blank=True, null=True)
    readme_modified = models.DateTimeField(blank=True, null=True)

    # The managers
    objects = RepositoryManager()
    for_list = OptimForListWithoutDeletedRepositoryManager()
    for_user_list = OptimForListRepositoryManager()

    # tags
    public_tags = TaggableManager(through=public_tags_class, related_name='public_on_repositories')
    private_tags = TaggableManager(through=private_tags_class, related_name='private_on_repositories')

    # Fetch operations
    backend_prefix = 'repository_'
    related_operations = (
        # name, with count, with modified
        ('owner', False, False),
        ('parent_fork', False, False),
        ('followers', True, True),
        ('contributors', True, True),
        ('readme', False, True),
    )


    def __unicode__(self):
        return u'%s' % self.get_project()

    def get_new_status(self, for_save=False):
        """
        Return the status to be saved
        """
        default = super(Repository, self).get_new_status(for_save=for_save)
        if default != self.STATUS.ok:
            return default

        # need the parents fork's name ?
        if self.is_fork and not self.official_fork_of:
            return self.STATUS.fetch_needed

        # need the owner (or to remove it) ?
        if self.official_owner and not self.owner_id:
            return self.STATUS.need_related
        if not self.official_owner and self.owner_id:
            return self.STAUTS.need_related

        # need the parent fork ?
        if self.is_fork and not self.parent_fork_id:
            return self.STATUS.need_related

        return self.STATUS.ok

    def get_project(self):
        """
        Return the project name (sort of identifier)
        """
        return self.project or self.get_backend().repository_project(self)

    def fetch(self, token=None, log_stderr=False):
        """
        Fetch data from the provider
        """
        if not super(Repository, self).fetch(token, log_stderr):
            return False

        old_official_modified = self.official_modified

        try:
            self.get_backend().repository_fetch(self, token=token)
        except BackendNotFoundError, e:
            if self.id:
                self.fake_delete()
            raise e
        else:
            self.deleted = False

        self.last_fetch = datetime.utcnow()

        if not self.official_followers_count:
            self.followers_modified = self.last_fetch
            self.followers_count = 0
            if self.followers_count:
                for follower in self.followers.all():
                    self.remove_follower(follower, False)

        self.save()

        self._modified = old_official_modified < self.official_modified

        return True

    def save(self, *args, **kwargs):
        """
        Update the project and sortable fields
        """
        if not self.project:
            self.project = self.get_project()
        self.project_sort = Repository.objects.slugify_project(self.project)

        if self.slug:
            self.slug_sort = slugify(self.slug)
            self.slug_lower = self.slug.lower()

        if self.official_owner:
            self.official_owner_lower = self.official_owner.lower()
            # auto-create a Account object for owner if one is needed but not exists
            if not self.owner_id:
                owner = Account.objects.get_or_new(
                    self.backend,
                    self.official_owner
                )
                if owner.is_new():
                    owner.save()
                self.owner = owner

        super(Repository, self).save(*args, **kwargs)

    def fetch_owner(self, token=None):
        """
        Create or update the repository's owner
        """
        if not self.get_backend().supports('repository_owner'):
            return False

        if not self.official_owner:
            if self.owner_id:
                self.owner = None
                self.save()
            return False

        save_needed = False
        fetched = False

        if not self.owner_id and not self.owner:
            save_needed = True
            owner = Account.objects.get_or_new(self.backend, self.official_owner)
        else:
            owner = self.owner

        if owner.fetch_needed():
            #owner.fetch(token=token)
            owner.fetch_full(token=token, async=True, async_priority=3, depth=0, allowed_interval=owner.MIN_FETCH_DELTA)
            fetched = True

        if save_needed:
            if not self.owner_id:
                self.owner = owner
            self.add_follower(owner, True)

        return fetched

    def fetch_parent_fork(self, token=None):
        """
        Create of update the parent fork, only if needed and if we have the
        parent fork's name
        """
        if not self.get_backend().supports('repository_parent_fork'):
            return False

        if not (self.is_fork and self.official_fork_of):
            if self.parent_fork_id:
                self.parent_fork = None
                self.save()
            return False

        save_needed = False
        fetched = False

        parent_is_new = False
        if not self.parent_fork_id:
            save_needed = True
            parent_fork = Repository.objects.get_or_new(self.backend,
                project=self.official_fork_of)
        else:
            parent_fork = self.parent_fork

        if parent_fork.fetch_needed():
            if parent_fork.is_new():
                parent_fork.forks_count = 1
            #parent_fork.fetch(token=token)
            parent_fork.fetch_full(token=token, async=True, async_priority=3, depth=0, allowed_interval=parent_fork.MIN_FETCH_DELTA)
            fetched = True

        if save_needed:
            if not self.parent_fork_id:
                self.parent_fork = parent_fork
            self.save()
            if not parent_is_new:
                self.parent_fork.update_count('forks', async=True)

        return fetched

    def fetch_followers(self, token=None):
        """
        Fetch the accounts following this repository
        """
        return self.fetch_related_entries('repository_followers', 'follower', 'followers', 'slug', token=token)

    def add_follower(self, account, update_self_count=True):
        """
        Try to add the account described by `account` as follower of
        the current repository.
        """
        return self.add_related_account_entry(account, 'followers', 'repositories', update_self_count)

    def remove_follower(self, account, update_self_count=True):
        """
        Remove the given account from the ones following
        the Repository
        """
        return self.remove_related_account_entry(account, 'followers', 'repositories', update_self_count)

    def fetch_contributors(self, token=None):
        """
        Fetch the accounts following this repository
        """
        return self.fetch_related_entries('repository_contributors', 'contributor', 'contributors', 'slug', token=token)

    def add_contributor(self, account, update_self_count=True):
        """
        Try to add the account described by `account` as contributor of
        the current repository.
        """
        return self.add_related_account_entry(account, 'contributors', 'contributing', update_self_count)

    def remove_contributor(self, account, update_self_count=True):
        """
        Remove the given account from the ones contributing to
        the Repository
        """
        return self.remove_related_account_entry(account, 'contributors', 'contributing', update_self_count)

    @models.permalink
    def _get_url(self, url_type, **kwargs):
        """
        Construct the url for a permalink
        """
        (url_type, args, kwargs) = super(Repository, self)._get_url(url_type, **kwargs)
        if 'project' not in kwargs:
            kwargs['project'] = self.project
        return (url_type, args, kwargs)

    def get_owner_url(self):
        """
        Url to the owner of this Repository
        """
        return self._get_url('owner')

    def get_followers_url(self):
        """
        Followers page url for this Repository
        """
        return self._get_url('followers')

    def get_contributors_url(self):
        """
        Contributors page url for this Repository
        """
        return self._get_url('contributors')

    def get_forks_url(self):
        """
        Forks page url for this Repository
        """
        return self._get_url('forks')

    def get_parent_fork_url(self):
        """
        Url to the parent fork of this Repository
        """
        return self._get_url('parent_fork')

    def get_readme_url(self):
        """
        Readme page url for this Repository
        """
        return self._get_url('readme')

    def followers_ids(self):
        """
        Return the followers as a list of ids
        """
        if not hasattr(self, '_followers_ids'):
            self._followers_ids = self.followers.values_list('id', flat=True)
        return self._followers_ids

    def contributors_ids(self):
        """
        Return the contributors as a list of ids
        """
        if not hasattr(self, '_contributors_ids'):
            self._contributors_ids = self.contributors.values_list('id', flat=True)
        return self._contributors_ids

    def fetch_readme(self, token=None):
        """
        Try to get a readme in the repository
        """
        if not self.get_backend().supports('repository_readme'):
            return False

        if not getattr(self, '_modified', True):
            return False

        readme = self.get_backend().repository_readme(self, token=token)

        if readme is not None:
            if isinstance(readme, (list, tuple)):
                readme_type = readme[1]
                readme = readme[0]
            else:
                readme_type = 'txt'

            self.readme = readme
            self.readme_type = readme_type

        self.readme_modified = datetime.utcnow()
        self.save()
        return True

    def prepare_main_score(self):
        """
        Compute the popularity of the repository, used to compute it's total
        score, and also to compute it's owner's score
        """
        backend = self.get_backend()

        divider = 0.0
        parts = dict(infos=0)

        # basic scores
        if self.name != self.slug:
            parts['infos'] += 0.3
        if self.description:
            parts['infos'] += 0.3
        if self.readme:
            parts['infos'] += 0.3

        if backend.supports('repository_created_date'):
            now = datetime.utcnow()
            divider += 0.5
            if not self.official_created:
                parts['life_time'] = 0
            else:
                parts['life_time'] = self._compute_score_part((now - self.official_created).days / 90.0)
                if backend.supports('repository_modified_date'):
                    if not self.official_modified or self.official_modified <= self.official_created:
                        # never updated, or updated before created ? seems to be a forked never touched
                        del parts['life_time']
                    else:
                        parts['zombie'] = - self._compute_score_part((now - self.official_modified).days / 90.0)
                else:
                    parts['life_time'] = parts['life_time'] / 2.0

        if backend.supports('repository_followers'):
            divider += 1
            parts['followers'] = self._compute_score_part(self.official_followers_count or 0)

        if backend.supports('repository_parent_fork'):
            divider += 1.0/3
            parts['forks'] = self._compute_score_part(self.official_forks_count or 0)

        if self.is_fork:
            divider = divider * 2

        return parts, divider

    def prepare_score(self):
        """
        Compute the current score for this repository
        """
        parts, divider = self.prepare_main_score()

        backend = self.get_backend()
        if backend.supports('repository_owner'):
            divider += 1
            if self.owner_id:
                owner_score = self.owner.score or self.owner.compute_score()
                parts['owner'] = self._compute_score_part(owner_score)

        #print parts
        return parts, divider

    def score_to_boost(self, force_compute=False):
        """
        Transform the score in a "boost" value usable by haystack
        """
        score = super(Repository, self).score_to_boost(force_compute=force_compute)
        return math.log1p(max(score*100, 5) / 5.0) - 0.6

    def find_public_tags(self, known_tags=None):
        """
        Update the public tags for this repository.
        """
        if not known_tags:
            known_tags = all_official_tags()
        rep_tags = get_tags_for_repository(self, known_tags)
        tags = sorted(rep_tags.iteritems(), key=lambda t: t[1], reverse=True)
        self.public_tags.set(tags[:5])

        # force cache update
        self.all_public_tags(force_cache=True)

    def all_public_tags(self, with_weight=False, force_cache=False):
        """
        Return all public tags for this repository.
        Use this instead of self.public_tags.all() because
        we set the default order
        If `with_weight` is True, return the through model of the tagging
        system, with tags and weight.
        Else simply returns tags.
        in both cases, sort is by weight (desc) and slug (asc)
        """
        if with_weight:
            return self.publictaggedrepository_set.select_related('tag').all()
        else:
            cache_key = self.get_redis_key('public_tags') % self.id
            tags = None
            if not force_cache:
                tags = cache.get(cache_key)
            if tags is None:
                tags = self.public_tags.order_by('-public_repository_tags__weight', 'slug')
                cache.set(cache_key, tags, 2678400)
            return tags

    def all_private_tags(self, user):
        """
        Return all private tags for this repository set by the given user.
        Use this instead of self.private_tags.filter(owner=user) because
        we set the default order
        """
        return self.private_tags.filter(private_repository_tags__owner=user).order_by('-private_repository_tags__weight', 'slug').distinct()

    def links_with_user(self, user):
        """
        Return informations about some links between this repository and the given user
        """
        backend = self.get_backend()
        links = {}

        if backend.supports('repository_owner'):
            if self.owner.user_id == user.id:
                links['owning'] = self.owner

            if backend.supports('repository_parent_fork'):
                forks = self.forks.filter(owner__user=user)
                if forks:
                    links['forks'] = forks

                project_forks = Repository.objects.filter(
                        slug_lower=self.slug_lower, owner__user=user).select_related('owner').exclude(
                                id=self.id)
                if forks:
                    project_forks = project_forks.exclude(id__in=list(fork.id for fork in forks))
                if project_forks:
                    links['project_forks'] = project_forks

        if backend.supports('repository_followers'):
            following = self.followers.filter(user=user)
            if following:
                links['following'] = following

            project_following = Repository.objects.filter(
                    slug_lower=self.slug_lower, followers__user=user).exclude(
                            owner__user=user).exclude(id=self.id).select_related('owner')
            if project_following:
                links['project_following'] = project_following

        if backend.supports('repository_contributors'):
            contributing = self.contributors.filter(user=user)
            if contributing:
                links['contributing'] = contributing

        return links

    def fetch_full_self_message(self):
        """
        Return the message part to display after a fetch of the object during a fetch_full
        """
        return 'fwr=%s, frk=%s, is_frk=%s' % (self.official_followers_count, self.official_forks_count, self.is_fork)

    def fetch_full_related_message(self):
        """
        Return the message part to display after a fetch of the related during a fetch_full
        """
        return 'fwr=%s, ctb=%s' % (self.followers_count, self.contributors_count)

    def get_default_token(self):
        """
        Return the token object for this repository's owner
        """
        if self.owner_id:
            return self.get_backend().token_manager().get_for_account(self.owner)
        return None

    def fetch_full_specific(self, depth=0, token=None, async=False):
        """
        After the full fetch of the repository, try to make a full fetch of all
        related objects: owner, parent_fork, forks, contributors, followers
        """
        if depth > 0:
            depth -= 1

            # do fetch for all followers
            sys.stderr.write(" - full fetch of followers (for %s)\n" % self)
            for account in self.followers.all():
                token, rep_fetch_error = account.fetch_full(depth=depth, token=token, async=async)

                # access token invalidated, get a new one
                if rep_fetch_error and rep_fetch_error.code in (401, 403):
                    token = None

            # do fetch for owner
            if self.owner_id:
                sys.stderr.write(" - full fetch of owner (for %s)\n" % self)
                token, rep_fetch_error = self.owner.fetch_full(depth=depth, token=token, async=async)

                # access token invalidated, get a new one
                if rep_fetch_error and rep_fetch_error.code in (401, 403):
                    token = None

            # do fetch for parent fork
            if self.is_fork and self.parent_fork_id:
                sys.stderr.write(" - full fetch of parent fork (for %s)\n" % self)
                token, rep_fetch_error = self.parent_fork.fetch_full(depth=depth, token=token, async=async)

                # access token invalidated, get a new one
                if rep_fetch_error and rep_fetch_error.code in (401, 403):
                    token = None

            # do fetch full for all forks
            sys.stderr.write(" - full fetch of forks (for %s)\n" % self)
            for repository in self.forks.all():
                token, rep_fetch_error = repository.fetch_full(depth=depth, token=token, async=async)

                # access token invalidated, get a new one
                if rep_fetch_error and rep_fetch_error.code in (401, 403):
                    token = None

            # do fetch for all contributors
            sys.stderr.write(" - full fetch of contributors (for %s)\n" % self)
            for account in self.contributors.all():
                token, rep_fetch_error = account.fetch_full(depth=depth, token=token, async=async)

                # access token invalidated, get a new one
                if rep_fetch_error and rep_fetch_error.code in (401, 403):
                    token = None

    def get_search_index(self):
        """
        Return the search index for this model
        """
        return site.get_index(Repository)

    def fake_delete(self):
        """
        Set the repository as deleted and remove if from every automatic
        lists (not from ones created by users : tags, notes...)
        """
        to_update = {}
        now = datetime.utcnow()

        # manage contributors
        for account in self.contributors.all():
            account.update(
                contributing_count = models.F('contributing_count') - 1,
                raise_if_error = False
            )
        self.contributors.clear()
        to_update['contributors_count'] = 0
        to_update['contributors_modified'] = now

        # manage child forks
        for fork in self.forks.all():
            fork.update(
                is_fork = False,
                official_fork_of = None,
            )
        self.forks.clear()
        to_update['forks_count'] = 0

        # manage parent fork
        if self.parent_fork_id:
            self.parent_fork.update(
                forks_count = models.F('forks_count') - 1,
                raise_if_error = False
            )
            to_update['parent_fork'] = None
            to_update['official_fork_of'] = None

        # manage followers
        for follower in self.followers.all():
            follower.update(
                repositories_count = models.F('repositories_count') - 1,
                raise_if_error = False
            )
        self.followers.clear()
        to_update['followers_count'] = 0
        to_update['followers_modified'] = now

        # final update
        to_update['owner'] = None
        super(Repository, self).fake_delete(to_update)


    def str_for_user(self, user):
        """
        Given a user, try to give a personified str for this repository
        """
        user = offline_messages.get_user(user)
        default = super(Repository, self).str_for_user(user)
        if not user or not self.owner.user or self.owner.user != user:
            return default
        return 'your repository "%s"' % self.slug


def get_object_from_str(object_str):
    """
    Try to get an object from its str representation, "core.account:123"
    (same represetation as returned by simple_str)
    """
    model_name, id = object_str.split(':')
    if '.' in model_name:
        model_name = model_name.split('.')[-1]

    if model_name == 'account':
        model = Account
    elif model_name == 'repository':
        model = Repository
    else:
        raise Exception('Invalid object')

    return model.objects.get(id=id)


from core.signals import *

########NEW FILE########
__FILENAME__ = search_indexes
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

import re

from haystack.indexes import *
from haystack import site

from core.models import Account, Repository

SLUG_SORT_RE = re.compile(r'[^a-z]')

class CoreIndex(SearchIndex):
    """
    Base search index, used for core models
    """
    text = CharField(document=True, use_template=True)
    slug = CharField(model_attr='slug', boost=2)
    slug_normalized = CharField(model_attr='slug_sort')
    slug_sort = CharField()
    name = CharField(model_attr='name', null=True, boost=1.5)
    modified = DateTimeField(model_attr='modified')
    internal_score = IntegerField()
    get_absolute_url = CharField(model_attr='get_absolute_url', indexed=False)

    def get_updated_field(self):
        """
        Use the `modified` field to only updates new objects
        """
        return 'modified'

    def _prepare_slug_sort(self, slug):
        """
        Remove everything but letters, to have one entire worl instead of many
        in search engines, better for correct sorting
        """
        return SLUG_SORT_RE.sub('a', slug.replace('-', ''))

    def prepare_slug_sort(self, obj):
        return self._prepare_slug_sort(obj.slug_sort)

    def prepare_internal_score(self, obj):
        return obj.score or 0

    def prepare(self, obj):
        """
        Use the object's score to calculate the boost
        """
        data = super(CoreIndex, self).prepare(obj)
        data['boost'] = obj.score_to_boost()
        return data

class AccountIndex(CoreIndex):
    """
    Search index for Account objects
    """
    all_public_tags = CharField(null=True)

    def prepare_all_public_tags(self, obj):
        return ' '.join([tag.slug for tag in obj.all_public_tags()])

site.register(Account, AccountIndex)

class RepositoryIndex(CoreIndex):
    """
    Search index for Repository objects
    """
    project = CharField(model_attr='project', boost=2.5)
    description = CharField(model_attr='description', null=True)
    readme = CharField(model_attr='readme', null=True, boost=0.5)
    owner_slug_sort = CharField(null=True)
    official_modified_sort = DateTimeField(model_attr='official_modified', null=True)
    owner_id = IntegerField(model_attr='owner_id', null=True)
    is_fork = BooleanField(model_attr='is_fork', null=True)
    owner_internal_score = IntegerField()

    def prepare_owner_slug_sort(self, obj):
        if obj.owner_id:
            return self._prepare_slug_sort(obj.owner.slug_sort)
        return None

    def prepare_owner_internal_score(self, obj):
        if obj.owner_id and obj.owner.score:
            return obj.owner.score
        return 0

site.register(Repository, RepositoryIndex)

########NEW FILE########
__FILENAME__ = signals
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.dispatch import receiver
from django.contrib import messages

from social_auth.signals import pre_update
from django_globals import globals

from core.backends import BACKENDS_BY_AUTH
from core.models import Account
from core.exceptions import BackendError

@receiver(pre_update, sender=None, dispatch_uid='core.signals.CreateAccountOnSocialAccount')
def CreateAccountOnSocialAccount(sender, user, response, details, **kwargs):
    """
    Associate (and then fetch if needed) an Account object for the user just logged
    """
    if not getattr(sender, 'name', None) in BACKENDS_BY_AUTH:
        return False

    social_user = None
    try:
        social_users = user.social_auth.all()
        for soc_user in social_users:
            if details['username'] == soc_user.extra_data.get('original_login'):
                social_user = soc_user
                break
    except:
        pass

    try:
        if not social_user:
            raise Exception('Social user not found')
        Account.objects.associate_to_social_auth_user(social_user)
    except BackendError, e:
        messages.error(globals.request, e.message)
    except Exception:
        messages.error(globals.request, 'We were not able to associate your account !')

    return False


########NEW FILE########
__FILENAME__ = reposio_core
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from lxml.html.clean import clean_html

from django import template
from django.contrib.markup.templatetags import markup
from django.utils.safestring import mark_safe
from django.template.defaultfilters import urlize
from django.db.models.sql.query import get_proxied_model

from haystack.models import SearchResult

from core.models import SyncableModel
from core.backends import BaseBackend, get_backend
from tagging.flags import split_tags_and_flags
from utils.model_utils import get_app_and_model
from adv_cache_tag.tag import CacheTag

register = template.Library()

@register.filter
def supports(backend, functionnality):
    """
    Return True if the given backend supports the given functionnality.
    `backend` can be a backend name, or a backend object
    """

    if isinstance(backend, basestring):
        backend = get_backend(backend)
        if not backend:
            return False

    if isinstance(backend, BaseBackend):
        return backend.supports(functionnality)

    return False

@register.filter
def links_with_user(obj, user):
    """
    Return informations about some links between the given object (account or repository) and the given user
    """
    try:
        return obj.links_with_user(user)
    except:
        return {}

@register.filter
def note_and_tags(obj, user):
    """
    Return the note and tags for the given object (account or repository) by the given user
    """
    try:
        note = obj.get_user_note(user)
        private_tags = obj.get_user_tags(user)
        if private_tags:
            app_label, model_name = get_app_and_model(obj)
            flags_and_tags = split_tags_and_flags(private_tags, model_name)
        else:
            flags_and_tags = None

        return dict(
            note = note,
            flags_and_tags = flags_and_tags
        )
    except:
        return {}

@register.filter
def readme(repository):
    """
    Return a rendered version of the readme for the given repository
    """
    if not repository.readme or not repository.readme.strip():
        return 'No readme :('

    readme = None

    try:
        if repository.readme_type == 'markdown':
            readme = markup.markdown(repository.readme)
        elif repository.readme_type == 'textile':
            readme = markup.textile(repository.readme)
        elif repository.readme_type == 'rest':
            readme = markup.restructuredtext(repository.readme)
    except:
        pass

    if not readme:
        readme = '<pre>%s</pre>' % urlize(repository.readme)

    try:
        result = mark_safe(clean_html(readme))
    except:
        result = 'Unreadble readme :('

    return result
readme.is_safe = True


@register.filter
def url(obj, url_type):
    """
    Return a specific url for the given object
    """
    try:
        return obj._get_url(url_type)
    except:
        return ''

@register.filter
def count_tags(obj, tags_type):
    """
    Return the number of tags of the given type for the given object
    """
    try:
        return obj.count_tags(tags_type)
    except:
        return ''

class CoreCacheTag(CacheTag):
    class Meta(CacheTag.Meta):
        include_pk = True
        compress = True
        compress_spaces = True
        versioning = True
        internal_version = '0.5'

    def create_content(self):
        obj = self.context['obj']

        current_user_data_keys = [key for key in vars(obj) if key.startswith('current_user_')]

        if not isinstance(obj, SyncableModel) or obj._deferred:

            if isinstance(obj, SearchResult):
                model = obj.model
            else:
                model = get_proxied_model(obj._meta)

            print "RENDER %s.%s" % (model, obj.pk)

            full_obj = model.for_user_list.get(id=obj.pk)
            for key in current_user_data_keys:
                setattr(full_obj, key, getattr(obj, key))
            self.context['obj'] = self.context[obj.model_name] = full_obj

        super(CoreCacheTag, self).create_content()

CoreCacheTag.register(register, 'corecache');

########NEW FILE########
__FILENAME__ = tokens
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

import time

from redisco import models, connection

AVAILABLE_LIST_KEY = 'available_tokens'


class AccessToken(models.Model):
    """
    Model to store, in redis (via redisco) all tokens and their status
    """
    uid = models.Attribute(required=True, indexed=True, unique=True)
    login = models.Attribute(required=True, indexed=True)
    token = models.Attribute(required=True, indexed=True)
    backend = models.Attribute(required=True, indexed=True)
    status = models.IntegerField(required=True, indexed=True, default=200)
    last_use = models.DateTimeField(auto_now_add=True, auto_now=True)
    last_message = models.Attribute()

    def __unicode__(self):
        return str(self)

    def __str__(self):
        return self.uid

    def save(self):
        is_new = self.is_new()
        result = super(AccessToken, self).save()
        if result == True and is_new:
            self.release()
        return result

    def is_valid(self):
        """
        Overrive the default method to save the uid, which is unique (by
        concatenating backend and token)
        """
        self.uid = '%s:%s:%s' % (self.backend, self.login, self.token)
        return super(AccessToken, self).is_valid()

    def lock(self):
        """
        Set the token as currently used
        """
        return connection.srem(AVAILABLE_LIST_KEY, self.uid)

    def release(self):
        """
        Set the token as not currently used
        """
        return connection.sadd(AVAILABLE_LIST_KEY, self.uid)

    def set_status(self, code, message):
        """
        Set a new status and message for this token
        """
        self.status = code
        self.last_message = message
        self.save()


class AccessTokenManager(object):

    by_backend = {}

    @classmethod
    def get_for_backend(cls, backend_name):
        """
        Return a manager for the given backend name.
        Only one manager exists for each backend
        """
        if backend_name not in cls.by_backend:
            cls.by_backend[backend_name] = cls(backend_name)
        return cls.by_backend[backend_name]

    def __init__(self, backend_name):
        """
        A manager is for a specific backend
        """
        self.backend_name = backend_name

    def get_one(self, default_token=None, wait=True):
        """
        Return an available token for the current backend and lock it
        If `default_token` is given, check it's a good one
        """
        if default_token:
            default_token = self.get_by_uid(default_token.uid)
            if default_token and default_token.status == 200:
                if default_token.lock():
                    return default_token

        while True:
            uid = connection.spop(AVAILABLE_LIST_KEY)
            token = self.get_by_uid(uid)
            if token and token.status == 200:
                return token

            if not wait:
                return None

            time.sleep(0.5)

    def get_for_account(self, account):
        """
        Return the token for the given account
        """
        if not account.access_token:
            return None
        return AccessToken.objects.filter(
            backend = self.backend_name,
            login = account.slug,
            token = account.access_token,
        ).first()

    def get_by_uid(self, uid):
        """
        Return the token for a given uid
        """
        if not uid:
            return None
        return AccessToken.objects.filter(backend=self.backend_name, uid=uid).first()

########NEW FILE########
__FILENAME__ = accounts
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *

from core.views.accounts import *

urlpatterns = patterns('',
    url(r'^$', home, name='account_home'),
    url(r'^edit-tags/$', edit_tags, name='account_edit_tags'),
    url(r'^edit-note/$', edit_note, name='account_edit_note'),
    url(r'^about/$', about, name='account_about'),

    url(r'^followers/$', followers, name='account_followers'),
    url(r'^following/$', following, name='account_following'),
    url(r'^repositories/$', repositories, name='account_repositories'),
    url(r'^contributing/$', contributing, name='account_contributing'),
)


########NEW FILE########
__FILENAME__ = repositories
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *

from core.views.repositories import *

urlpatterns = patterns('',
    url(r'^$', home, name='repository_home'),
    url(r'^edit-tags/$', edit_tags, name='repository_edit_tags'),
    url(r'^edit-note/$', edit_note, name='repository_edit_note'),
    url(r'^about/$', about, name='repository_about'),

    url(r'^followers/$', followers, name='repository_followers'),
    url(r'^contributors/$', contributors, name='repository_contributors'),
    url(r'^forks/$', forks, name='repository_forks'),
    url(r'^readme/$', readme, name='repository_readme'),
    url(r'^owner/$', owner, name='repository_owner'),
    url(r'^parent-fork/$', parent_fork, name='repository_parent_fork'),
)


########NEW FILE########
__FILENAME__ = accounts
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.shortcuts import render, redirect

from endless_pagination.decorators import page_template

from core.views.decorators import check_account, check_support
from core.views import base_object_search
from front.decorators import ajaxable
from private.forms import NoteForm
from utils.views import ajax_login_required

@check_account
@ajaxable('front/account_details.html')
def home(request, backend, slug, account=None, template='front/account_main.html'):
    """
    Home page of an account
    """
    context = dict(obj = account)
    return render(request, template, context)

@check_account
@ajaxable('front/account_details.html')
def edit_tags(request, backend, slug, account=None, template='front/account_main.html'):
    """
    Home page of an account, in tags-editing mode
    """
    context = dict(obj = account)
    if not request.is_ajax():
        context['edit_tags'] = True
    return render(request, template, context)

@check_account
@ajax_login_required
#@ajaxable('front/account_details.html')
@ajaxable('front/note_form.html')
def edit_note(request, backend, slug, account=None, template='front/account_main.html'):
    """
    Home page of an account, in tags-editing mode
    """
    note = account.get_user_note()

    context = dict(
        overlay = True,
        obj = account,
        edit_note = True,
        note = note,
        note_form = NoteForm(instance=note) if note else NoteForm(noted_object=account),
    )
    return render(request, template, context)

@check_support('user_followers')
@check_account
@page_template("front/include_results.html")
def followers(request, backend, slug, account=None, template="front/account_main.html", extra_context=None):
    """
    Page listing accounts following an account
    """
    return base_object_search(
            request,
            account,
            'people',
            'followers',
            template = template,
            search_extra_params = None,
            extra_context = extra_context,
        )

@check_support('user_following')
@check_account
@page_template("front/include_results.html")
def following(request, backend, slug, account=None, template="front/account_main.html", extra_context=None):
    """
    Page listing accounts followed by an account
    """
    return base_object_search(
            request,
            account,
            'people',
            'following',
            template = template,
            search_extra_params = None,
            extra_context = extra_context,
        )

@check_support('user_repositories')
@check_account
@page_template("front/include_results.html")
def repositories(request, backend, slug, account=None, template="front/account_main.html", extra_context=None):
    """
    Page listing repositories owned/watched by an account
    """
    return base_object_search(
            request,
            account,
            'repositories',
            'repositories',
            template = template,
            search_extra_params = None,
            extra_context = extra_context,
        )

@check_support('repository_contributors')
@check_account
@page_template("front/include_results.html")
def contributing(request, backend, slug, account=None, template="front/account_main.html", extra_context=None):
    """
    Page listing repositories with contributions by an account
    """
    return base_object_search(
            request,
            account,
            'repositories',
            'contributing',
            template = template,
            search_extra_params = None,
            extra_context = extra_context,
        )

@check_account
def about(request, backend, slug, account=None):

    if not request.is_ajax():
        return redirect(account)

    context = dict(obj = account)
    return render(request, 'front/include_subsection_about.html', context)

#def _filter_repositories(request, account, queryset):
#    """
#    Helper doing all sort/query stuff about repositories, for listing
#    repositories owned/followed or contributed by an account,
#    """
#    sort_key = request.GET.get('sort_by', 'name')
#    repository_supports_owner = account.get_backend().supports('repository_owner')
#    repository_supports_parent_fork = account.get_backend().supports('repository_parent_fork')
#    sort = get_repository_sort(sort_key, repository_supports_owner)
#
#    sorted_repositories = queryset.order_by(sort['db_sort'])
#
#    if repository_supports_owner:
#        owner_only = request.GET.get('owner-only', False) == 'y'
#    else:
#        owner_only = False
#
#    if owner_only:
#        sorted_repositories = sorted_repositories.filter(owner=account)
#
#    if repository_supports_parent_fork:
#        hide_forks = request.GET.get('hide-forks', False) == 'y'
#    else:
#        hide_forks = False
#
#    if hide_forks:
#        sorted_repositories = sorted_repositories.exclude(is_fork=True)
#
#    query = request.GET.get('q')
#    if query:
#        keywords = parse_keywords(query)
#        search_queryset = make_query(RepositorySearchView.search_fields, keywords)
#        search_queryset = search_queryset.models(RepositorySearchView.model)
#        if owner_only:
#            search_queryset = search_queryset.filter(owner_id=account.id)
#        if hide_forks:
#            search_queryset = search_queryset.exclude(is_fork=True)
#        # It's certainly not the best way to do it but.... :(
#        sorted_ids = [r.id for r in sorted_repositories]
#        if sorted_ids:
#            search_queryset = search_queryset.filter(django_id__in=sorted_ids)
#            found_ids = [int(r.pk) for r in search_queryset]
#            sorted_repositories = [r for r in sorted_repositories if r.id in found_ids]
#
#    distinct = request.GET.get('distinct', False) == 'y'
#    if distinct and not owner_only:
#        # try to keep one entry for each slug
#        uniq = []
#        slugs = {}
#        for repository in sorted_repositories:
#            if repository.slug in slugs:
#                slugs[repository.slug].append(repository)
#                continue
#            slugs[repository.slug] = []
#            uniq.append(repository)
#        for repository in uniq:
#            repository.distinct_others = slugs[repository.slug]
#        # try to keep the first non-fork for each one
#        sorted_repositories = []
#        sort_lambda = lambda r:r.official_created
#        for repository in uniq:
#            if not repository.distinct_others or repository.owner_id == account.id:
#                good_repository = repository
#            else:
#                important_ones = [r for r in repository.distinct_others if not r.is_fork]
#                owned = [r for r in important_ones if r.owner_id == account.id]
#                if owned:
#                    good_repository = owned[0]  # only one possible
#                else:
#                    if important_ones:
#                        if not repository.is_fork:
#                            important_ones + [repository,]
#                    else:
#                        important_ones = repository.distinct_others + [repository,]
#
#                    good_repository = sorted(important_ones, key=sort_lambda)[0]
#
#                if good_repository != repository:
#                    good_repository.distinct_others = [r for r in repository.distinct_others + [repository,] if r != good_repository]
#                    delattr(repository, 'distinct_others')
#
#                if hasattr(good_repository, 'distinct_others'):
#                    good_repository.distinct_others = sorted(good_repository.distinct_others, key=sort_lambda)
#
#            sorted_repositories.append(good_repository)
#
#    page = paginate(request, sorted_repositories, settings.REPOSITORIES_PER_PAGE)
#
#    return dict(
#        account = account,
#        page = page,
#        sort = dict(
#            key = sort['key'],
#            reverse = sort['reverse'],
#        ),
#        owner_only = 'y' if owner_only else False,
#        hide_forks = 'y' if hide_forks else False,
#        distinct = 'y' if distinct else False,
#        query = query or "",
#    )


########NEW FILE########
__FILENAME__ = decorators
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from functools import wraps

from django.http import Http404
from django.contrib import messages

from core.models import Account, Repository
from core.backends import get_backend


def check_account(function=None):
    """
    Check if an account identified by a backend and a slug exists
    """
    def _dec(view_func):
        @wraps(view_func)
        def _view(request, backend, slug, *args, **kwargs):
            try:
                account = Account.objects.get(backend=backend, slug=slug)
            except:
                raise Http404
            else:
                if account.deleted and view_func.__name__ != 'home':
                    messages.error(request, 'This page is useless since the account has been deleted')

                save_counts = set()
                if account.followers_count is None and account.get_backend().supports('user_followers'):
                    account.update_count('followers', save=False)
                    save_counts.add('followers')
                if account.following_count is None and account.get_backend().supports('user_following'):
                    account.update_count('following', save=False)
                    save_counts.add('following')
                if account.repositories_count is None and account.get_backend().supports('user_repositories'):
                    account.update_count('repositories', save=False)
                    save_counts.add('repositories')
                if account.contributing_count is None and account.get_backend().supports('user_repositories'):
                    account.update_count('contributing', save=False)
                    save_counts.add('contributing')
                if save_counts:
                    # update the object in DB, via an update, not a save
                    # if counts is "followers", add `followers_count=account.followers_count`
                    account.update(
                        **dict(('%s_count' % name, getattr(account, '%s_count' % name)) for name in save_counts)
                    )

                account.include_details = True
                kwargs['account'] = account
                return view_func(request, backend, slug, *args, **kwargs)

        return _view

    if function is None:
        return _dec
    else:
        return _dec(function)

def check_repository(function=None):
    """
    Check if a repository identified by a backend and a project exists
    """
    def _dec(view_func):
        @wraps(view_func)
        def _view(request, backend, project, *args, **kwargs):
            try:
                repository = Repository.objects.select_related('owner').select_related('owner', 'parent_fork', 'parent_fork_owner').get(backend=backend, project=project)
            except:
                raise Http404
            else:
                if repository.deleted and view_func.__name__ != 'home':
                    messages.error(request, 'This page is useless since the project has been deleted')

                save_counts = set()
                if repository.followers_count is None and repository.get_backend().supports('repository_followers'):
                    repository.update_count('followers', save=False)
                    save_counts.add('followers')
                if repository.contributors_count is None and repository.get_backend().supports('repository_contributors'):
                    repository.update_count('contributors', save=False)
                    save_counts.add('contributors')
                if repository.forks_count is None and repository.get_backend().supports('repository_parent_fork'):
                    repository.update_count('forks', save=False)
                    save_counts.add('forks')
                if save_counts:
                    # update the object in DB, via an update, not a save
                    # if counts is "followers", add `followers_count=repository.followers_count`
                    repository.update(
                        **dict(('%s_count' % name, getattr(repository, '%s_count' % name)) for name in save_counts)
                    )

                repository.include_details = True
                kwargs['repository'] = repository
                return view_func(request, backend, project, *args, **kwargs)

        return _view

    if function is None:
        return _dec
    else:
        return _dec(function)

def check_support(functionnality=None):
    """
    Check if the backend supports the given functionnality
    """
    def _dec(view_func):
        @wraps(view_func)
        def _view(request, backend, *args, **kwargs):
            try:
                if not get_backend(backend).supports(functionnality):
                    raise Http404
            except:
                raise Http404
            else:
                return view_func(request, backend, *args, **kwargs)

        return _view

    return _dec

########NEW FILE########
__FILENAME__ = repositories
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.shortcuts import render, redirect
from django.http import Http404

from endless_pagination.decorators import page_template

from core.views.decorators import check_repository, check_support
from core.views import base_object_search
from front.decorators import ajaxable
from private.forms import NoteForm
from utils.views import ajax_login_required

@check_repository
@ajaxable('front/repository_details.html')
def home(request, backend, project, repository=None, template='front/repository_main.html'):
    """
    Home page of a repository
    """
    context = dict(obj = repository)
    return render(request, template, context)

@check_repository
@ajaxable('front/repository_details.html')
def edit_tags(request, backend, project, repository=None, template='front/repository_main.html'):
    """
    Home page of a repository, in tags-editing mode
    """
    context = dict(obj = repository)
    if not request.is_ajax():
        context['edit_tags'] = True
    return render(request, template, context)

@check_repository
@ajax_login_required
#@ajaxable('front/repository_details.html')
@ajaxable('front/note_form.html')
def edit_note(request, backend, project, repository=None, template='front/repository_main.html'):
    """
    Home page of a repository, in tags-editing mode
    """
    note = repository.get_user_note()

    context = dict(
        overlay = True,
        obj = repository,
        edit_note = True,
        note = note,
        note_form = NoteForm(instance=note) if note else NoteForm(noted_object=repository),
    )
    return render(request, template, context)

@check_repository
def owner(request, backend, project, repository=None):
    """
    Link to the repository's owner page
    """
    if not repository.owner:
        raise Http404
    if not request.is_ajax():
        return redirect(repository.owner)

    repository.owner.include_details = 'about'

    context = dict(obj = repository.owner)

    return render(request, 'front/include_subsection_object.html', context)

@check_repository
def parent_fork(request, backend, project, repository=None):
    """
    Link to the repository's parent-fork page
    """
    if not repository.parent_fork:
        raise Http404
    if not request.is_ajax():
        return redirect(repository.parent_fork)

    repository.parent_fork.include_details = 'about'

    context = dict(obj = repository.parent_fork)

    return render(request, 'front/include_subsection_object.html', context)

@check_support('repository_followers')
@check_repository
@page_template("front/include_results.html")
def followers(request, backend, project, repository=None, template="front/repository_main.html", extra_context=None):
    """
    Page listing users following a repository
    """
    return base_object_search(
            request,
            repository,
            'people',
            'followers',
            template = template,
            search_extra_params = None,
            extra_context = extra_context,
        )

@check_support('repository_contributors')
@check_repository
@page_template("front/include_results.html")
def contributors(request, backend, project, repository=None, template="front/repository_main.html", extra_context=None):
    """
    Page listing users contributing to a repository
    """
    return base_object_search(
            request,
            repository,
            'people',
            'contributors',
            template = template,
            search_extra_params = None,
            extra_context = extra_context,
        )

@check_support('repository_readme')
@check_repository
@ajaxable('front/include_subsection_readme.html')
def readme(request, backend, project, repository=None, template="front/repository_main.html"):
    context = dict(obj = repository)
    return render(request, template, context)

@check_repository
def about(request, backend, project, repository=None):

    if not request.is_ajax():
        return redirect(repository)

    context = dict(obj = repository)
    return render(request, 'front/include_subsection_about.html', context)

@check_support('repository_parent_fork')
@check_repository
@page_template("front/include_results.html")
def forks(request, backend, project, repository=None, template="front/repository_main.html", extra_context=None):
    """
    Page listing forks of a repository
    """
    return base_object_search(
            request,
            repository,
            'repositories',
            'forks',
            template = template,
            search_extra_params = { 'show_forks': 'y' },
            extra_context = extra_context,
        )

    #if mode == 'real_forks':
    #    sorted_forks = Repository.for_list.filter(parent_fork=repository)
    #else:
    #    sorted_forks = Repository.for_list.filter(name=repository.name).exclude(is_fork=True)
    ## check sub forks, one query / level
    #if mode == 'real_forks':
    #    current_forks = page.object_list
    #    while True:
    #        by_id = dict((obj.id, obj) for obj in current_forks)
    #        current_forks = Repository.for_list.filter(parent_fork__in=by_id.keys()).order_by('-official_modified')
    #        if not current_forks:
    #            break
    #        for fork in current_forks:
    #            parent_fork = by_id[fork.parent_fork_id]
    #            if not hasattr(parent_fork, 'direct_forks'):
    #                parent_fork.direct_forks = []
    #            parent_fork.direct_forks.append(fork)
    #    # make one list for each first level fork, to avoid recursion in templates
    #    all_forks = []
    #    def get_all_forks_for(fork, level):
    #        fork.fork_level = level
    #        all_subforks = [fork,]
    #        if hasattr(fork, 'direct_forks'):
    #            for subfork in fork.direct_forks:
    #                all_subforks += get_all_forks_for(subfork, level+1)
    #            delattr(fork, 'direct_forks')
    #        return all_subforks
    #    for fork in page.object_list:
    #        all_forks += get_all_forks_for(fork, 0)
    #    page.object_list = all_forks




########NEW FILE########
__FILENAME__ = sort
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from copy import copy
from utils.sort import prepare_sort

repository_sort_map = dict(
    name = 'slug_sort',
    owner = 'owner__slug_sort',
    updated = 'official_modified',
)
account_sort_map = dict(
    name = 'slug_sort',
)

def get_repository_sort(key, allow_owner=True, default='name', default_reverse=False, disabled=None):
    """
    Return needed informations about sorting repositories
    """
    _repository_sort_map = copy(repository_sort_map)

    if not allow_owner:
        del _repository_sort_map['owner']

    if disabled:
        for entry in disabled:
            _repository_sort_map.pop(entry, None)

    return prepare_sort(key, _repository_sort_map, default, default_reverse)

def get_account_sort(key, default='name', default_reverse=False, disabled=None):
    """
    Return needed informations about sorting accounts
    """
    _account_sort_map = account_sort_map

    if disabled:
        _account_sort_map = copy(account_sort_map)
        for entry in disabled:
            _account_sort_map.pop(entry, None)

    return prepare_sort(key, _account_sort_map, default, default_reverse)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = dashboard_tags
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django import template
register = template.Library()

@register.filter
def distinctify(objects, fields=None):
    """
    Return a distinct list (by id) of objects, but keep specific fields
    For example, with the followers of a user, we have a list of Accounts,
    each with an extra field "current_user_account_id" to save which account
    of the current user is followed.
    If an account follow more than one of the user's accouts, it will be
    present more than one time in the list.
    This function keeps only one entry of each, but regroups some fields into
    lists, so all the "current_user_account_id" of the many occurences of one
    account are stored in a "current_user_account_id_list" of the only
    occurence which this function kept.
    `fields` is a string with name of fields to regroup, separated by a coma
    (no spaces !)
    Usage : {{ mylist|distinctify:"field1,field2" }}
    """
    if not objects:
        return []

    special_fields = []
    if fields:
        special_fields = fields.split(',')

    # first test length: it's same, no need to distintify
    ids = set([obj.id for obj in objects])
    if len(ids) == len(objects):
        # check if all fields are present
        ok = True
        for field in special_fields:
            if not hasattr(objects[0], '%s_list' % field):
                ok = False
                break
        # not fields present, quickly create them
        if not ok:
            for obj in objects:
                for field in special_fields:
                    setattr(obj, '%s_list' % field, set((getattr(obj, field),)))
        return objects

    # we really have to distinct !
    result = []
    found = {}

    for obj in objects:

        if obj.id not in found:
            found[obj.id] = obj
            result.append(obj)

            for field in special_fields:
                if not hasattr(obj, '%s_list' % field):
                    setattr(obj, '%s_list' % field, set())

        for field in special_fields:
            if hasattr(obj, field):
                getattr(found[obj.id], '%s_list' % field).add(getattr(obj, field))

    return result



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
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *
from django.shortcuts import HttpResponseRedirect

def redirect_dashboard(request, search_type, search_filter, options=None):
    if not options:
        options = {}
    q = request.REQUEST.get('q', '')
    order = request.REQUEST.get('sort_by', '')
    url = '/?type=%s&q=%s&filter=%s%s&order=%s' % (
        search_type,
        q,
        search_filter,
        '&%s' % (''.join(['%s=%s' % (opt_key, opt_value) for opt_key, opt_value in options.items()]),),
        order
    )
    return HttpResponseRedirect(url)

def redirect_followers(request):
    return redirect_dashboard(request, 'people', 'followers')

def redirect_following(request):
    return redirect_dashboard(request, 'people', 'following')

def redirect_repositories(request):
    search_filter = 'following'
    if request.REQUEST.get('owner-only', 'n') == 'y':
        search_filter = 'owned'
    options = {}
    if request.REQUEST.get('hide-forks', 'n') == 'n':
        options['show_forks'] = 'y'
    return redirect_dashboard(request, 'repositories', search_filter, options)

def redirect_contributing(request):
    search_filter = 'contributed'
    if request.REQUEST.get('owner-only', 'n') == 'y':
        search_filter = 'owned'
    options = {}
    if request.REQUEST.get('hide-forks', 'n') == 'n':
        options['show_forks'] = 'y'
    return redirect_dashboard(request, 'repositories', search_filter, options)

def redirect_notes(request, obj_type):
    search_type = 'repositories'
    if obj_type == 'accounts':
        search_type = 'people'
    return redirect_dashboard(request, search_type, 'noted')

def redirect_tags(request, obj_type):
    options = {}
    search_type = 'repositories'
    if obj_type == 'accounts':
        search_type = 'people'
    else:
        options['show_forks'] = 'y'
    search_filter = 'tagged'
    tag = request.REQUEST.get('tag', '')
    if tag:
        search_filter = 'tag:%s' % tag
    return redirect_dashboard(request, search_type, search_filter, options)


urlpatterns = patterns('',
    url(r'^$', redirect_repositories, name='dashboard_home'),
    url(r'^tags(?:/(?P<obj_type>repositories|accounts))?/$', redirect_tags, name='dashboard_tags'),
    url(r'^notes(?:/(?P<obj_type>repositories|accounts))?/$', redirect_notes, name='dashboard_notes'),
    url(r'^following/$', redirect_following, name='dashboard_following'),
    url(r'^followers/$', redirect_following, name='dashboard_followers'),
    url(r'^repositories/$', redirect_repositories, name='dashboard_repositories'),
    url(r'^contributing/$', redirect_contributing, name='dashboard_contributing'),
)

########NEW FILE########
__FILENAME__ = views
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.conf import settings

from notes.models import Note

from core.models import Account, Repository
from core.views.sort import get_repository_sort,get_account_sort
from core.core_utils import get_user_accounts
from utils.sort import prepare_sort
from utils.views import paginate
from search.views import parse_keywords, make_query, RepositorySearchView
from tagging.flags import split_tags_and_flags

def _get_sorted_user_tags(user, only=None):
    """
    Return all tags for the user, sorted by usage (desc) and name (asc)
    The result is a dict with two entries : `repository` and `account`,
    grouping tags for each category. Each list is a list of tuple, with
    the tag's slug in first, then the tag's name and finally the list of
    tagged objects (only names)
    """
    result = {}
    types = dict(account='slug', repository='project')

    for obj_type in types:
        if only and obj_type != only:
            continue

        tagged_items = getattr(user, 'tagging_privatetagged%s_items' % obj_type).values_list('tag__slug', 'tag__name', 'content_object__%s' % types[obj_type])

        tags = {}
        if not tagged_items:
            result[obj_type] = []
            continue

        for tag_slug, tag_name, obj in tagged_items:
            if tag_slug not in tags:
                tags[tag_slug] = dict(slug=tag_slug, name=tag_name, objects=[])
            tags[tag_slug]['objects'].append(obj)

        tags = sorted(tags.values(), key=lambda tag: (-len(tag['objects']), tag['slug']), reverse=False)
        result[obj_type] = split_tags_and_flags(tags, obj_type, True) if tags else []

    return result

def _get_last_user_notes(user, limit=None, only=None, sort_by='-modified'):
    """
    Return `limit` last noted objects (or all if no limit), sorted by date (desc).
    The result is a dict with two entries: `repotiroy` and `account`,
    grouping notes for each category. Each list is a list of objects
    (repository or account) with a "current_user_rendered_note" added attribute
    """
    result = {}
    types = dict(account=Account, repository=Repository)

    for obj_type in types:
        if only and obj_type != only:
            continue

        notes = Note.objects.filter(author=user, content_type__app_label='core', content_type__model=obj_type).values_list('object_id', 'rendered_content', 'modified')

        sort_objs = True
        if sort_by in ('-modified', 'modified'):
            sort_objs = False
            notes = notes.order_by(sort_by)

        if limit:
            notes = notes[:limit]

        if not notes:
            result[obj_type] = []
            continue

        notes_by_obj_id = dict((note[0], note[1:]) for note in notes)

        if sort_objs:
            objs = types[obj_type].for_user_list.filter(id__in=notes_by_obj_id.keys()).order_by(sort_by)
            result[obj_type] = [obj for obj in objs if obj.id in notes_by_obj_id]
        else:
            objs = types[obj_type].for_user_list.in_bulk(notes_by_obj_id.keys())
            result[obj_type] = [objs[note[0]] for note in notes if note[0] in objs]

        for obj in result[obj_type]:
            obj.current_user_has_extra = True
            obj.current_user_has_note = True
            obj.current_user_rendered_note = notes_by_obj_id[obj.id][0]
            obj.current_user_note_modified = notes_by_obj_id[obj.id][1]

    return result


@login_required
def home(request):
    """
    Home of the user dashboard.
    For tags and notes we use callbacks, so they are only executed if
    called in templates
    For "best", it's simple querysets
    """

    def get_tags():
        return _get_sorted_user_tags(request.user)
    def get_notes():
        return _get_last_user_notes(request.user, 5)

    best = dict(
        accounts = dict(
            followers = Account.for_user_list.filter(following__user=request.user).order_by('-score').distinct()[:5],
            following = Account.for_user_list.filter(followers__user=request.user).order_by('-score').distinct()[:5],
        ),
        repositories = dict(
            followed = Repository.for_user_list.filter(followers__user=request.user).exclude(owner__user=request.user).order_by('-score').distinct()[:5],
            owned = Repository.for_user_list.filter(owner__user=request.user).order_by('-score').distinct()[:5],
        ),
    )

    context = dict(
        tags = get_tags,
        notes = get_notes,
        best = best,
    )
    return render(request, 'dashboard/home.html', context)

def obj_type_from_url(obj_type):
    """
    In url, we can have "accounts" and "repositories", but we need
    "account" and "repository".
    """
    if obj_type == 'accounts':
        return 'account'
    elif obj_type == 'repositories':
        return 'repository'
    else:
        return obj_type

@login_required
def tags(request, obj_type=None):
    """
    Display all tags for the given object type, and a list of tagged objects.
    A get parameter "tag" allow to filter the list.
    """
    if obj_type is None:
        return redirect(tags, obj_type='repositories')

    model = obj_type_from_url(obj_type)

    def get_tags():
        return _get_sorted_user_tags(request.user, only=model)[model]

    tag_slug = request.GET.get('tag', None)

    params = { 'privatetagged%s__owner' % model: request.user }
    if tag_slug:
        params['privatetagged%s__tag__slug' % model] = tag_slug

    sort_key = request.GET.get('sort_by', 'name')

    if model == 'account':
        objects = Account.objects.filter(**params)
        sort = get_account_sort(sort_key)
        per_page = settings.ACCOUNTS_PER_PAGE
    else:
        objects = Repository.objects.filter(**params).select_related('owner')
        sort = get_repository_sort(sort_key)
        per_page = settings.REPOSITORIES_PER_PAGE

    objects = objects.order_by(sort['db_sort']).distinct()

    page = paginate(request, objects, per_page)

    context = dict(
        tags = get_tags,
        obj_type = obj_type,
        tag_filter = tag_slug,
        page = page,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
    )
    return render(request, 'dashboard/tags.html', context)


@login_required
def notes(request, obj_type=None):
    """
    Display all repositories or accounts with a note
    """
    if obj_type is None:
        return redirect(notes, obj_type='repositories')

    model = obj_type_from_url(obj_type)

    sort_key = request.GET.get('sort_by', '-note')
    if model == 'account':
        sort = get_account_sort(sort_key, default=None)
        per_page = settings.ACCOUNTS_PER_PAGE
    else:
        sort = get_repository_sort(sort_key, default=None)
        per_page = settings.REPOSITORIES_PER_PAGE
    if not sort.get('db_sort'):
        sort = prepare_sort(sort_key, dict(note='modified'), default='note', default_reverse=True)

    all_notes = _get_last_user_notes(request.user, only=model, sort_by=sort['db_sort'])[model]

    page = paginate(request, all_notes, per_page)

    context = dict(
        page = page,
        obj_type = obj_type,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
    )
    return render(request, 'dashboard/notes.html', context)


def accounts_dict(request):
    """
    Return a dict with all accounts of the current user
    """
    return dict((a.id, a) for a in get_user_accounts())


@login_required
def following(request):
    """
    Display following for all accounts of the user
    """

    all_following = Account.for_user_list.filter(followers__user=request.user).extra(select=dict(current_user_account_id='core_account_following.from_account_id'))

    sort = get_account_sort(request.GET.get('sort_by', None), default=None)

    if sort['key']:
        all_following = all_following.order_by(sort['db_sort'])

    followers_ids = Account.objects.filter(following__user=request.user).values_list('id', flat=True)

    def get_accounts_dict():
        return accounts_dict(request)

    page = paginate(request, all_following, settings.ACCOUNTS_PER_PAGE)

    context = dict(
        page = page,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
        followers_ids = followers_ids,
        accounts = get_accounts_dict,
    )
    return render(request, 'dashboard/following.html', context)


@login_required
def followers(request):
    """
    Display followers for all accounts of the user
    """

    all_followers = Account.for_user_list.filter(following__user=request.user).extra(select=dict(current_user_account_id='core_account_following.to_account_id'))

    sort = get_account_sort(request.GET.get('sort_by', None), default=None)

    if sort['key']:
        all_followers = all_followers.order_by(sort['db_sort'])

    following_ids = Account.objects.filter(followers__user=request.user).values_list('id', flat=True)

    def get_accounts_dict():
        return accounts_dict(request)

    page = paginate(request, all_followers, settings.ACCOUNTS_PER_PAGE)

    context = dict(
        page = page,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
        following_ids = following_ids,
        accounts = get_accounts_dict,
    )
    return render(request, 'dashboard/followers.html', context)


def _filter_repositories(request, param, extra):
    """
    Helper doing all sort/query stuff about repositories, for listing
    repositories owned/followed or contributed by the user
    """

    params = {param: request.user}

    owner_only = request.GET.get('owner-only', False) == 'y'
    if owner_only:
        params['owner__user'] = request.user

    all_repositories = Repository.for_user_list.filter(**params).extra(select=dict(current_user_account_id=extra))

    hide_forks = request.GET.get('hide-forks', False) == 'y'
    if hide_forks:
        all_repositories = all_repositories.exclude(is_fork=True)

    sort = get_repository_sort(request.GET.get('sort_by', None))
    if sort['key']:
        all_repositories = all_repositories.order_by(sort['db_sort'])

    accounts = accounts_dict(request)

    query = request.GET.get('q')
    if query:
        keywords = parse_keywords(query)
        search_queryset = make_query(RepositorySearchView.search_fields, keywords)
        search_queryset = search_queryset.models(RepositorySearchView.model)
        if owner_only:
            search_queryset = search_queryset.filter(owner_id__in=accounts.keys())
        if hide_forks:
            search_queryset = search_queryset.exclude(is_fork=True)
        # It's certainly not the best way to do it but.... :(
        sorted_ids = [r.id for r in all_repositories]
        if sorted_ids:
            search_queryset = search_queryset.filter(django_id__in=sorted_ids)
            found_ids = [int(r.pk) for r in search_queryset]
            all_repositories = [r for r in all_repositories if r.id in found_ids]

    distinct = request.GET.get('distinct', False) == 'y'
    if distinct:
        # try to keep one entry for each backend/slug
        uniq = []
        slugs = {}
        for repository in all_repositories:
            slug = '%s:%s' % (repository.backend, repository.slug)
            if slug in slugs:
                slugs[slug].append(repository)
                continue
            slugs[slug] = []
            uniq.append(repository)
        for repository in uniq:
            slug = '%s:%s' % (repository.backend, repository.slug)
            repository.distinct_others = slugs[slug]
        # try to keep the first non-fork for each one
        all_repositories = []
        sort_lambda = lambda r:r.official_created
        for repository in uniq:
            if not repository.distinct_others or repository.owner_id in accounts:
                good_repository = repository
            else:
                important_ones = [r for r in repository.distinct_others if not r.is_fork]
                owned = [r for r in important_ones if r.owner_id in accounts]
                if owned:
                    good_repository = owned[0]  # all are from the owner, take one
                else:
                    if important_ones:
                        if not repository.is_fork:
                            important_ones + [repository,]
                    else:
                        important_ones = repository.distinct_others + [repository,]

                    good_repository = sorted(important_ones, key=sort_lambda)[0]

                if good_repository != repository:
                    good_repository.distinct_others = [r for r in repository.distinct_others + [repository,] if r != good_repository]
                    delattr(repository, 'distinct_others')

                if hasattr(good_repository, 'distinct_others'):
                    good_repository.distinct_others = sorted(good_repository.distinct_others, key=sort_lambda)

            good_repository.current_user_account_id_list = set((good_repository.current_user_account_id,))
            if hasattr(good_repository, 'distinct_others'):
                for other_rep in good_repository.distinct_others:
                    good_repository.current_user_account_id_list.add(other_rep.current_user_account_id)

            all_repositories.append(good_repository)

    page = paginate(request, all_repositories, settings.REPOSITORIES_PER_PAGE)

    context = dict(
        all_repositories = all_repositories,
        page = page,
        sort = dict(
            key = sort['key'],
            reverse = sort['reverse'],
        ),
        accounts = accounts,
        owner_only = 'y' if owner_only else False,
        hide_forks = 'y' if hide_forks else False,
        distinct = 'y' if distinct else False,
        query = query or "",
    )
    return context


@login_required
def repositories(request):
    """
    Display repositories followed/owned by the user
    """
    context = _filter_repositories(request, param='followers__user', extra='core_account_repositories.account_id')
    return render(request, 'dashboard/repositories.html', context)


@login_required
def contributing(request):
    """
    Display repositories contributed by the user
    """
    context = _filter_repositories(request, param='contributors__user', extra='core_repository_contributors.account_id')
    return render(request, 'dashboard/contributing.html', context)

########NEW FILE########
__FILENAME__ = decorators
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from functools import wraps

def ajaxable(template, ignore_if=None):
    """
    If the request is an ajax one, then call the view with the template given
    as parameter to this decorator instead of the original one.
    The view MUST have the template in its parameters
    """
    def decorator(view):
        #decorator with arguments wrap
        @wraps(view)
        def decorated(request, *args, **kwargs):
            if request.is_ajax():
                ignore = False
                if ignore_if:
                    for field in ignore_if:
                        if field in request.REQUEST:
                            ignore = True
                            break
                if not ignore:
                    kwargs['template'] = template
            return view(request, *args, **kwargs)
        return decorated
    return decorator


########NEW FILE########
__FILENAME__ = forms
from django import forms

# place form definition here
########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = search
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.db.models import Q
from django.conf import settings

from haystack.query import SQ, SearchQuerySet, EmptySearchQuerySet
from haystack.models import SearchResult

from core.models import Repository, Account
from utils.sort import prepare_sort

class CannotHandleException(Exception):
    pass

class CoreSearchResult(SearchResult):
    pass

class RepositoryResult(CoreSearchResult):
    model_name_plural = Repository.model_name_plural
    content_type = Repository.content_type
    search_type = Repository.search_type

class AccountResult(CoreSearchResult):
    model_name_plural = Account.model_name_plural
    content_type = Account.content_type
    search_type = Account.search_type

class _Filter(object):
    """
    An abstract default filter for all
    """
    only = dict(
        account = ('id', 'backend', 'status', 'slug', 'modified'),
        repository = ('id', 'backend', 'status', 'slug', 'project', 'modified'),
    )
    default_sort = None

    def __init__(self, query_filter, search):
        """
        Create the filter and save the query_filter
        """
        super(_Filter, self).__init__()
        self.query_filter = query_filter
        self.search = search
        # if the search has a query, the default sort is the solr one
        if search.query:
            self.default_sort = None

    def original_filter(self):
        """
        Compute the original filter
        """
        return self.query_filter

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Strip the filter and return it
        """
        if not query_filter:
            return ''
        try:
            return query_filter.strip()
        except:
            return ''

    @classmethod
    def handle(cls, search):
        """
        Return a new filter or raise CannotHandleException, after
        tried to get a tag from the filter
        """
        query_filter = cls.parse_filter(search.query_filter, search)
        return cls(query_filter, search)

    def apply(self, queryset):
        """
        Apply the current filter on the givent queryset for the current search
        and return an updated queryset
        If the search is emtpy, we return directly all the objects,
        else we apply the filter on ids for the current search
        """
        if isinstance(queryset, EmptySearchQuerySet):
            return self.get_objects()
        else:
            ids = list(self.get_ids()[:settings.SOLR_MAX_IN])
            return queryset.filter(django_id__in=ids)

    def get_queryset_filter(self):
        """
        To be implemented in sublcasses
        """
        return Q()

    def get_manager(self):
        """
        Return the manager to use for the filter
        If the user is authenticated, use the manager including deleted objects
        """
        if self.search.check_user():
            return self.search.model.objects
        else:
            return self.search.model.objects.exclude(deleted=True)

    def get_queryset(self):
        """
        Return the queryset on the search's model, filtered
        """
        return self.get_manager().filter(
                self.get_queryset_filter()
            )

    def get_ids(self):
        """
        Get the filtered queryset and return the ids (a queryset, in fact)
        """
        return self.get_queryset().values_list('id', flat=True)

    def get_objects(self):
        """
        Get the filtered queryset and return the objects (a queryset, in fact)
        We only need the id (status is required by core/models) because we
        directly load a cached template
        """
        return self.get_queryset().only(*self.only[self.search.model_name])


class NoFilter(_Filter):
    """
    A filter... without filter
    """

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if we don't have a filter
        """
        query_filter = super(NoFilter, cls).parse_filter(query_filter, search)
        if query_filter:
            raise CannotHandleException
        return None

    def original_filter(self):
        """
        Return an empty filter
        """
        return ''

    def apply(self, queryset):
        """
        No filter, return all
        """
        return queryset


class _TagFilter(_Filter):
    """
    An abstract filter for all tags
    """
    default_sort = 'name'

    def original_filter(self):
        return 'tag:' + self.query_filter

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if the filter is a tag and return it
        """
        if not search.check_user():
            raise CannotHandleException
        if not query_filter.startswith('tag:'):
            raise CannotHandleException
        return query_filter[4:]

    def get_queryset_filter(self):
        return Q(**{
            'privatetagged%s__owner' % self.search.model_name: self.search.user,
            'privatetagged%s__tag__slug' % self.search.model_name: self.query_filter,
        })


class SimpleTagFilter(_TagFilter):
    """
    A filter for simple tags (not flags, places, projects...)
    """
    pass


class _PrefixedTagFilter(_TagFilter):
    """
    A abstract filter for managing filter starting with a prefix
    """

    def original_filter(self):
        return 'tag:' + self.prefix + self.query_filter

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if the filter is a tag and starts with a prefix, and return the
        tag
        """
        tag = super(_PrefixedTagFilter, cls).parse_filter(query_filter, search)
        if not tag.startswith(cls.prefix):
            raise CannotHandleException
        return tag


class PlaceFilter(_PrefixedTagFilter):
    """
    A filter for projects (tags starting with @)
    """
    prefix = '@'


class ProjectFilter(_PrefixedTagFilter):
    """
    A filter for projects (tags starting with #)
    """
    prefix = '#'


class FlagFilter(_TagFilter):
    """
    A filter for specific flags, defined in allowed
    """
    allowed = ('starred', 'check-later')

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if the filter is an allowed flag and return it
        """
        tag = super(FlagFilter, cls).parse_filter(query_filter, search)
        if tag not in cls.allowed:
            raise CannotHandleException
        return tag


class NotedFilter(_Filter):
    """
    A filter for noted objects
    """
    default_sort = 'name'

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if the filter is exactly "noted"
        """
        if not search.check_user():
            raise CannotHandleException
        query_filter = super(NotedFilter, cls).parse_filter(query_filter, search)
        if query_filter != 'noted':
            raise CannotHandleException
        return query_filter

    def get_queryset_filter(self):
        """
        Return only objects with a note
        """
        return Q(note__author=self.search.user)


class TaggedFilter(_Filter):
    """
    An abstract filter for tagged objects
    """
    default_sort = 'name'

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if the filter is exactly "tagged"
        """
        if not search.check_user():
            raise CannotHandleException
        query_filter = super(TaggedFilter, cls).parse_filter(query_filter, search)
        if query_filter != 'tagged':
            raise CannotHandleException
        return query_filter

    def get_queryset_filter(self):
        return Q(**{
            'privatetagged%s__owner' % self.search.model_name: self.search.user,
        })

    def get_queryset(self):
        qs = super(TaggedFilter, self).get_queryset()
        qs = qs.exclude(**{
                'privatetagged%s__tag__slug__in' % self.search.model_name: ('check-later', 'starred'),
            })
        return qs.distinct()


class UserObjectListFilter(_Filter):
    """
    A filter for list of a loggued user
    """
    default_sort = 'name'

    # all allowed filters for each model, with the matching queryset main part
    allowed = dict(
        account = dict(
            following = 'followers__user',
            followers = 'following__user',
            accounts = 'user',
        ),
        repository = dict(
            following = 'followers__user',
            owned = 'owner__user',
            contributed = 'contributors__user',
        )
    )

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if the filter is an allowed one
        """
        if not search.check_user():
            raise CannotHandleException
        query_filter = super(UserObjectListFilter, cls).parse_filter(query_filter, search)
        if query_filter not in cls.allowed[search.model_name]:
            raise CannotHandleException
        return query_filter

    def get_queryset_filter(self):
        """
        Return a filter on a list for the current user
        """
        part = self.allowed[self.search.model_name][self.query_filter]
        return Q(**{part: self.search.user})


class ObjectRelativesFilter(_Filter):
    """
    A filter for a list of objects relatives to an object
    """
    default_sort = 'score'

    allowed = dict(
        account = ('following', 'followers', 'repositories', 'contributing'),
        repository = ('followers', 'contributors', 'forks')
    )

    @classmethod
    def parse_filter(cls, query_filter, search):
        """
        Test if the filter is an allowed one
        """
        if not search.base:
            raise CannotHandleException
        query_filter = super(ObjectRelativesFilter, cls).parse_filter(query_filter, search)
        if query_filter not in cls.allowed[search.base.model_name]:
            raise CannotHandleException
        return query_filter

    def get_queryset(self):
        """
        Return a filter of on a list for the current base object
        """
        queryset = getattr(self.search.base, self.query_filter).all()
        #if self.search.base.model_name == 'account' and self.search.model_name == 'repository'
        return queryset


# all valid filter, ordered
FILTERS = (ObjectRelativesFilter, UserObjectListFilter, NotedFilter, TaggedFilter, FlagFilter, ProjectFilter, PlaceFilter, SimpleTagFilter, NoFilter)
DEFAULT_FILTER = NoFilter


class Search(object):
    model = None
    model_name = None
    search_key = None
    search_fields = None
    search_params = ('q', 'filter', 'order')
    allowed_options = ()

    order_map = dict(db={}, solr={})

    def __init__(self, params, user=None):
        """
        Create the search object
        """
        super(Search, self).__init__()

        # init fields
        self.params = params
        self.user = user

        self.query = self.get_param('q')
        self.query_filter = self.get_param('filter')
        self.query_order = self.get_param('order')

        self.model_name = self.model.model_name

        self.results = None

        # get search parameters
        self.base = self.get_base()
        self.filter = self.get_filter()
        self.options = self.get_options()
        self.order = self.get_order()

    @staticmethod
    def get_class(search_type):
        """
        Return the correct search class for the given type
        """
        if search_type == 'people':
            return AccountSearch
        elif search_type == 'repositories':
            return RepositorySearch

    @staticmethod
    def get_for_params(params, user=None):
        """
        Return either a RepositorySearch or AccountSearch
        """
        cls = Search.get_class(params.get('type', 'repositories'))
        return cls(params, user)

    @staticmethod
    def get_params_from_request(request, search_type, ignore=None):
        """
        Get some params from the request, if they are not already defined (in ignore)
        """
        cls = Search.get_class(search_type)

        all_params = list(cls.search_params + cls.allowed_options)
        all_params += ['direct-%s' % param for param in all_params]

        params = {}
        for param in all_params:
            if ignore and param in ignore:
                continue
            if param not in request.REQUEST:
                continue
            params[param] = request.REQUEST[param]
        return params

    def get_param(self, name, default=''):
        """
        Return the value of the `name` field in the parameters of the current
        search, stripped. If we have a value for the same parameter but with a
        name prefixed with 'direct-', use it
        """
        return self.params.get(
            'direct-%s' % name,
            self.params.get(
                name,
                default
            )
        ).strip()

    def get_filter(self):
        """
        Find a good filter object for query string
        Raise CannotHandleException if no filter found
        """
        filter_obj = None
        for filter_cls in FILTERS:
            try:
                filter_obj = filter_cls.handle(self)
            except:
                continue
            else:
                break
        if not filter_obj:
            return DEFAULT_FILTER(self.query_filter, self)
        return filter_obj

    def get_options(self):
        """
        Return a dict with all options
        """
        options = {}
        for option in self.allowed_options:
            options[option] = 'y' if self.get_param(option, 'n') == 'y' else False
        return options

    def get_base(self):
        """
        Verify and save the base object if we have one
        """
        base = self.params.get('base', None)
        if base and isinstance(base, (Account, Repository)):
            return base
        return None

    def get_order(self):
        """
        Get the correct order for the current search
        """
        order_map_type = 'solr' if self.query else 'db'
        result = prepare_sort(
            self.query_order,
            self.order_map[order_map_type],
            self.filter.default_sort,
            False
        )
        if not result['key']:
            result['key'] = ''
        return result

    def parse_keywords(self, query_string):
        """
        Take a query string (from userr) and parse it to have a list of keywords.
        If many words are between two double-quotes, they are considered as one
        keyword.
        """
        qs = SearchQuerySet()
        keywords = []
        # Pull out anything wrapped in quotes and do an exact match on it.
        open_quote_position = None
        non_exact_query = query_string
        for offset, char in enumerate(query_string):
            if char == '"':
                if open_quote_position != None:
                    current_match = non_exact_query[open_quote_position + 1:offset]
                    if current_match:
                        keywords.append(qs.query.clean(current_match))
                    non_exact_query = non_exact_query.replace('"%s"' % current_match, '', 1)
                    open_quote_position = None
                else:
                    open_quote_position = offset
        # Pseudo-tokenize the rest of the query.
        keywords += non_exact_query.split()

        return keywords

        result = []
        for keyword in keywords:
            result.append(qs.query.clean(keyword))

        return result

    def make_query(self, fields, keywords, queryset=None):
        """
        Create the query for haystack for searching in `fields ` for documents
        with `keywords`. All keywords are ANDed, and if a keyword starts with a "-"
        all document with it will be excluded.
        """
        if not keywords or not fields:
            return EmptySearchQuerySet()

        if not queryset:
            queryset = SearchQuerySet()

        q = None
        only_exclude = True

        for keyword in keywords:
            exclude = False
            if keyword.startswith('-') and len(keyword) > 1:
                exclude = True
                keyword = keyword[1:]
            else:
                only_exclude = False

            keyword = queryset.query.clean(keyword)

            q_keyword = None

            for field in fields:

                q_field = SQ(**{ field: keyword })

                if q_keyword:
                    q_keyword = q_keyword | q_field
                else:
                    q_keyword = q_field

            if exclude:
                q_keyword = ~ q_keyword

            if q:
                q = q & q_keyword
            else:
                q = q_keyword

        if q:
            if only_exclude and len(keywords) > 1:
                # it seems that solr cannot manage only exclude when we have many of them
                # so we AND a query that we not match : the same as for ".models(self.model)"
                q = SQ(django_ct = 'core.%s' % self.model_name) & q
            return queryset.filter(q)
        else:
            return queryset

    def get_search_queryset(self):
        """
        Return the results for this search
        We only need the id because we
        directly load a cached template
        """
        if self.query:
            keywords = self.parse_keywords(self.query)
            queryset = self.make_query(self.search_fields, keywords)

            queryset = queryset.models(self.model).only('id', 'get_absolute_url', 'modified')

            return queryset.result_class(self.result_class)
        else:
            return EmptySearchQuerySet()

    def apply_filter(self, queryset):
        """
        Apply the current filter to the queryset
        """
        if self.filter:
            return self.filter.apply(queryset)
        return queryset

    def apply_options(self, queryset):
        """
        Apply some options to the queryset
        Do nothing by default
        """
        return queryset

    def apply_order(self, queryset):
        """
        Apply the current order to the query set
        """
        if self.order['db_sort']:
            return queryset.order_by(self.order['db_sort'])
        return queryset

    def update_results(self):
        """
        Calculate te results
        """
        self.results = self.apply_order(
            self.apply_options(
                self.apply_filter(
                    self.get_search_queryset()
                )
            )
        )

    def get_results(self, force_update=False):
        """
        Return the final page of results
        """
        if force_update or self.results is None:
            self.update_results()
        return self.results

    def check_user(self):
        """
        Return True if the user is authenticated and active, or return False
        """
        if not hasattr(self, '_check_user_cache'):
            try:
                self._check_user_cache = self.user and self.user.is_authenticated() and self.user.is_active
            except:
                self._check_user_cache = False
        return self._check_user_cache

    def content_template(self):
        """
        Return the template to use for this search's results
        """
        return 'front/%s_content.html' % self.model_name

    def is_default(self):
        """
        Return True if the Search is in a default status (no filter, options, order, query)
        """

        if self.query:
            return False
        if not self.base and self.filter.original_filter():
            return False
        sort_key = self.order.get('key', None)
        if sort_key and sort_key != self.filter.default_sort:
            return False
        if any(self.options.values()):
            return False
        return True


class RepositorySearch(Search):
    """
    A search in repositories
    """
    model = Repository
    model_name = 'repository'
    search_key = 'repositories'
    search_fields = ('project', 'slug', 'slug_sort', 'name', 'description', 'readme',)
    allowed_options = ('show_forks', 'is_owner',)
    result_class = RepositoryResult

    order_map = dict(
        db = dict(
            name = 'slug_sort',
            score = '-score',
            owner = 'owner__slug_sort',
            updated = '-official_modified',
            owner_score = '-owner__score',
        ),
        solr = dict(
            name = 'slug_sort',
            score = '-internal_score',
            owner = 'owner_slug_sort',
            updated = '-official_modified_sort',
            owner_score = '-owner_internal_score',
        ),
    )

    def apply_options(self, queryset):
        """
        Apply the "show forks" option
        """
        queryset = super(RepositorySearch, self).apply_options(queryset)

        if isinstance(queryset, EmptySearchQuerySet):
            return queryset

        if not self.options.get('show_forks', False):
            queryset = queryset.exclude(is_fork=True)

        if self.base and self.base.model_name == 'account' and self.options.get('is_owner', False):
            queryset = queryset.filter(owner=self.base.pk)

        return queryset


class AccountSearch(Search):
    """
    A search in accounts
    """
    model = Account
    model_name = 'account'
    search_key = 'accounts'
    search_fields = ('slug', 'slug_sort', 'name', 'all_public_tags')
    result_class = AccountResult

    order_map = dict(
        db = dict(
            name = 'slug_sort',
            score = '-score',
        ),
        solr = dict(
            name = 'slug_sort',
            score = '-internal_score',
        ),
    )

########NEW FILE########
__FILENAME__ = urls
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *
from front.views import main, fetch

urlpatterns = patterns('',
    url(r'^fetch/$', fetch, name='fetch'),
    url(r'^$', main, name='front_main'),
)

########NEW FILE########
__FILENAME__ = views
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponseBadRequest

from endless_pagination.decorators import page_template

from core.backends import get_backend
from core.models import Account, Repository
from core import messages as offline_messages
from private.views import get_user_tags
from front.search import Search
from utils.djson.response import JSONResponse
from utils.views import ajax_login_required

@page_template("front/include_results.html")
def main(request, template='front/main.html', extra_context=None):

    search = Search.get_for_params(request.REQUEST, request.user)

    tags = get_user_tags(request)

    context = dict(
        search = search,
        tags = tags
    )

    if extra_context is not None:
        context.update(extra_context)

    return render(request, template, context)


@require_POST
@ajax_login_required
@login_required
def fetch(request):
    """
    Trigger an asyncrhronous fetch_full of an object
    """

    try:
        otype = request.POST['type']
        if otype not in ('account', 'repository'):
            raise

        id = int(request.POST['id'])

        backend = get_backend(request.POST['backend'] or None)
        if not backend:
            raise

        if otype == 'account':
            slug = request.POST['slug']
            obj = Account.objects.get(id=id, backend=backend.name, slug=slug)
        else:
            project = request.POST['project']
            obj = Repository.objects.get(id=id, backend=backend.name, project=project)

    except:
        return HttpResponseBadRequest('Vilain :)')

    else:
        obj.fetch_full(async=True, async_priority=4, notify_user=request.user, allowed_interval=obj.MIN_FETCH_DELTA)

        message = 'Fetch of %s is in the queue and will be done soon' % obj.str_for_user(request.user)

        if request.is_ajax():
            result = dict(
                message = message
            )

            return JSONResponse(result)

        offline_messages.success(request.user, message, content_object=obj)

        return redirect(obj)

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
__FILENAME__ = forms
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django import forms
from django.contrib.contenttypes.models import ContentType

from django_globals import globals
from notes.models import Note, Topic

from private.models import ALLOWED_MODELS
from tagging.words import edit_string_for_tags
from tagging.forms import TagField
from tagging.models import Tag

class NoteBaseForm(forms.ModelForm):
    """
    Base forms with common stuff for NoteForm and NoteDeleteForm
    """
    class Meta:
        model = Note
        fields = ('object_id', 'content_type')

    def __init__(self, *args, **kwargs):
        """
        Simply hide the two fields
        """
        super(NoteBaseForm, self).__init__(*args, **kwargs)
        self.fields['object_id'].widget = forms.HiddenInput()
        self.fields['content_type'].widget = forms.HiddenInput()

    def get_related_object(self):
        """
        Return the noted object if valid, else None
        """
        if self.instance:
            return self.instance.content_object
        else:
            try:
                content_type = self.cleaned_data['content_type']
            except:
                content_type = None
            if not content_type:
                return None
            return content_type.get_object_for_this_type(pk=self.cleaned_data['object_id'])

    def get_note_from_content_type(self):
        """
        Try to get an existing note from the content_type parameters
        """
        try:
            return Note.objects.get(
                content_type = self.cleaned_data['content_type'],
                object_id = self.cleaned_data['object_id'],
                author = globals.user
            )
        except:
            return None

    def clean_content_type(self):
        """
        Check if the content_type is in allowed models
        """
        content_type = self.cleaned_data['content_type']
        if '%s.%s' % (content_type.app_label, content_type.model) not in ALLOWED_MODELS:
            raise forms.ValidationError('It\'s not possible to manage notes for this kind of object')
        return content_type


class NoteForm(NoteBaseForm):
    """
    Form to add or edit *the* note to an object, by the currently logged user
    """
    class Meta(NoteBaseForm.Meta):
        #fields = ('content', 'markup',) + NoteBaseForm.Meta.fields
        fields = ('content',) + NoteBaseForm.Meta.fields

    def __init__(self, *args, **kwargs):
        """
        If it's a form for a new note, a `noted_object` argument must be in kwargs
        """
        # get or create a note, to have content_type filled in the form
        if 'instance' not in 'kwargs' and 'noted_object' in kwargs:
            kwargs['instance'] = Note(content_object=kwargs.pop('noted_object'))

        super(NoteForm, self).__init__(*args, **kwargs)

        ## change the help text for markup
        #self.fields['markup'].help_text = self.fields['markup'].help_text\
        #    .replace('are using with this model', 'want to use')

        self.fields['content'].label = 'Your private note'

    def save(self, commit=True):
        """
        Try to load an existing not for the current content_type and update it
        or create a new one
        """
        instance = super(NoteForm, self).save(commit=False)
        try:
            # try to load an existing note
            existing_instance = self.get_note_from_content_type()
            if not existing_instance:
                raise Note.DoesNotExist
            # use the loaded one and copy data from the temporary one
            current_instance = instance
            instance = existing_instance
            instance.content = current_instance.content
            instance.markup = current_instance.markup
        except Note.DoesNotExist:
            # continue creating the new note
            instance.author = globals.user
            # we don't use topics for now so we always use the same one
            topic, topic_created = Topic.objects.get_or_create(title='Private notes')
            instance.topic = topic

        # force notes to be private
        instance.public = False

        instance.save()
        self.instance = instance

        return instance


class NoteDeleteForm(NoteBaseForm):
    """
    Form used to delete a note of the currently logged user
    """
    class Meta(NoteBaseForm.Meta):
        fields = NoteBaseForm.Meta.fields

    def save(self, commit=True):
        """
        Override the save to delete the object
        """
        note = self.get_note_from_content_type()
        if note:
            note.delete()
        return None


class TagsBaseForm(forms.Form):
    """
    Base forms with common stuff for TagsForm and TagsDeleteForm
    """
    content_type = forms.IntegerField(widget = forms.HiddenInput())
    object_id = forms.IntegerField(widget = forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        """
        Save tagged_object
        """
        self.tagged_object = kwargs.pop('tagged_object', None)
        if self.tagged_object:
            if not kwargs.get('initial'):
                kwargs['initial'] = {}
            kwargs['initial'].update(dict(
                content_type = ContentType.objects.get_for_model(self.tagged_object).id,
                object_id = self.tagged_object.id,
            ))
        super(TagsBaseForm, self).__init__(*args, **kwargs)
        self.content_type = None
        self.object_id = None

    def get_related_object(self):
        """
        Return the tagged object if valid, else None
        """
        if self.tagged_object:
            return self.tagged_object
        else:
            try:
                return self.content_type.get_object_for_this_type(pk=self.object_id)
            except:
                return None

    def clean_content_type(self):
        """
        Check if the content_type is in allowed models, and save the content_type
        """
        content_type = ContentType.objects.get_for_id(self.cleaned_data['content_type'])
        if '%s.%s' % (content_type.app_label, content_type.model) not in ALLOWED_MODELS:
            raise forms.ValidationError('It\'s not possible to manage tags for this kind of object')
        self.content_type = content_type
        return self.content_type

    def clean_object_id(self):
        """
        Save the object id
        """
        self.object_id = self.cleaned_data['object_id']
        return self.object_id

class TagsForm(TagsBaseForm):
    """
    Form to add or edit tags for an object, by the currently logged user
    """
    tags = TagField()

    def __init__(self, *args, **kwargs):
        """
        Set the defaults tags
        """
        tagged_object = kwargs.get('tagged_object')

        if tagged_object:
            if not kwargs.get('initial'):
                kwargs['initial'] = {}
            kwargs['initial']['tags'] = edit_string_for_tags(tagged_object.get_user_tags())

        super(TagsForm, self).__init__(*args, **kwargs)

        self.fields['tags'].set_available_tags(self.get_available_tags())

    def get_available_tags(self):
        """
        Return all available tags for use with the autocomplete
        If None, all tags from db will be used (via ajax call, else via insert into html)
        """
        return None

    def save(self):
        """
        Get the tags from the form parsed by taggit, and save them to the tagged_object
        """
        tags = self.cleaned_data['tags']
        dict_tags = {}
        weight = len(tags)
        for tag in tags:
            dict_tags[tag] = weight
            weight -= 1

        owner = globals.user

        tagged_object = self.get_related_object()
        tagged_object.private_tags.set(dict_tags, owner=owner)

class TagsAddOneForm(TagsBaseForm):
    """
    For adding an existing tag
    """
    tag = TagField()

    def save(self):
        owner = globals.user
        tagged_object = self.get_related_object()
        tagged_object.private_tags.add(self.cleaned_data['tag'], owner=owner)

class TagsToggleForm(TagsBaseForm):
    """
    For toggling a tag
    """
    tag = TagField()

    def save(self):
        owner = globals.user
        tagged_object = self.get_related_object()
        tag = self.cleaned_data['tag'][0]
        is_set = bool(tagged_object.all_private_tags(owner).filter(name=tag).count())
        if is_set:
            tagged_object.private_tags.remove(self.cleaned_data['tag'], owner=owner)
        else:
            tagged_object.private_tags.add(self.cleaned_data['tag'], owner=owner)
        return not is_set


class TagsRemoveOneForm(TagsBaseForm):
    """
    For removing an existing tag
    """
    tag = TagField()

    def save(self):
        owner = globals.user
        tagged_object = self.get_related_object()
        tagged_object.private_tags.remove(self.cleaned_data['tag'], owner=owner)


class TagsCreateOneForm(TagsBaseForm):
    """
    For adding a non existing tag
    """
    tag = TagField()

    def save(self):
        owner = globals.user
        tagged_object = self.get_related_object()
        tagged_object.private_tags.add(self.cleaned_data['tag'], owner=owner)


class AccountTagsForm(TagsForm):

    def get_available_tags(self):
        """
        Return the list of all private tags used by the user for accounts
        """
        user = globals.user
        tags = Tag.objects.filter(private_account_tags__owner=user).order_by('name')
        return [tag.name for tag in tags]

class RepositoryTagsForm(TagsForm):

    def get_available_tags(self):
        """
        Return the list of all private tags used by the user for repositories
        """
        user = globals.user
        tags = Tag.objects.filter(private_repository_tags__owner=user).order_by('name')
        return [tag.name for tag in tags]


class TagsDeleteForm(TagsBaseForm):
    """
    Form used to delete a note of the currently logged user
    """

    def save(self):
        """
        Delete all tags for an object set by the currently logged user
        """
        owner = globals.user

        tagged_object = self.get_related_object()
        tagged_object.private_tags.clear(owner=owner)


########NEW FILE########
__FILENAME__ = models
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf import settings

ALLOWED_MODELS = settings.NOTES_ALLOWED_MODELS

########NEW FILE########
__FILENAME__ = private_tags
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django import template
from django.core.urlresolvers import reverse
from django.utils.http import urlquote
from django.utils import simplejson

from django_globals import globals
from notes.models import Note

from private.models import ALLOWED_MODELS
from private.forms import NoteForm, NoteDeleteForm, TagsDeleteForm, TagsBaseForm
from core.models import Account, Repository, get_object_from_str
from utils.model_utils import get_app_and_model
from utils.views import get_request_param
from tagging.models import Tag
from tagging.flags import split_tags_and_flags
from front.views import get_user_tags

register = template.Library()

@register.simple_tag
def prepare_private(objects, ignore=None):
    """
    Update each object included in the `objects` with private informations (note and tags)
    All objects must be from the same content_type
    `ignore` is a string where we will search for "-tags", "-notes" and "related" to avoid compute them
    if found
    """
    try:
        if not (globals.user and globals.user.is_authenticated()):
            return ''

        if hasattr(objects,'__len__'):
            objects = list(objects)
        else:
            objects = [objects]

        # find objects' type
        obj = objects[0]

        app_label, model_name = get_app_and_model(obj)

        if '%s.%s' % (app_label, model_name) not in ALLOWED_MODELS:
            return ''

        user = globals.user

        dict_objects = dict((int(obj.pk), obj) for obj in objects)
        ids = sorted(dict_objects.keys())
        if not ids:
            return ''

        # read and save notes
        if not (ignore and '-notes' in ignore):
            notes = Note.objects.filter(
                    content_type__app_label = app_label,
                    content_type__model = model_name,
                    author = user,
                    object_id__in=ids
                    ).values_list('object_id', 'rendered_content', 'modified')

            for obj_id, note, modified in notes:
                dict_objects[obj_id].current_user_has_extra = True
                dict_objects[obj_id].current_user_has_note = True
                dict_objects[obj_id].current_user_rendered_note = note
                dict_objects[obj_id].current_user_note_modified = modified

        # read and save tags
        if not (ignore and '-tags' in ignore):
            if model_name == 'account':
                qs_tags = user.tagging_privatetaggedaccount_items
            else:
                qs_tags = user.tagging_privatetaggedrepository_items

            private_tagged_items = qs_tags.filter(
                    content_object__in=ids
                ).values_list('content_object', 'tag__name', 'tag__slug')

            for obj_id, tag, slug in private_tagged_items:
                if not getattr(dict_objects[obj_id], 'current_user_has_tags', None):
                    dict_objects[obj_id].current_user_has_extra = True
                    dict_objects[obj_id].current_user_has_tags = True
                    dict_objects[obj_id].current_user_tags = []
                dict_objects[obj_id].current_user_tags.append(dict(name=tag, slug=slug))

            for obj in dict_objects.values():
                if not getattr(obj, 'current_user_tags', None):
                    continue
                obj.current_user_tags = split_tags_and_flags(obj.current_user_tags, model_name, tags_are_dict=True)
                obj.current_user_has_tags = (obj.current_user_tags['places'] or obj.current_user_tags['projects'] or obj.current_user_tags['tags'])


        if not (ignore and '-related' in ignore):
            if model_name == 'account':
                # self
                self_accounts = Account.objects.filter(id__in=ids, user=user).values_list('id', flat=True)
                for obj_id in self_accounts:
                    dict_objects[obj_id].current_user_has_extra = True
                    dict_objects[obj_id].current_user_is_self = True

                # follows
                following = Account.objects.filter(id__in=ids, followers__user=user).values_list('id', flat=True)
                for obj_id in following:
                    dict_objects[obj_id].current_user_has_extra = True
                    dict_objects[obj_id].current_user_follows = True

                # is followed
                followed = Account.objects.filter(id__in=ids, following__user=user).values_list('id', flat=True)
                for obj_id in followed:
                    dict_objects[obj_id].current_user_has_extra = True
                    dict_objects[obj_id].current_user_followed = True

            else:
                # owns or follows
                following = Repository.objects.filter(id__in=ids, followers__user=user).values_list('id', 'owner__user_id')
                for obj_id, owner_id in following:
                    dict_objects[obj_id].current_user_has_extra = True
                    if owner_id == user.id:
                        dict_objects[obj_id].current_user_owns = True
                    else:
                        dict_objects[obj_id].current_user_follows = True

                # fork
                forked = Repository.objects.filter(id__in=ids, forks__owner__user=user).values_list('id', flat=True)
                for obj_id in forked:
                    dict_objects[obj_id].current_user_has_extra = True
                    dict_objects[obj_id].current_user_has_fork = True

        return ''
    except:
        return ''


class PrepareAllUserTagsNode(template.Node):
    def render(self, context):
        result = {}

        if globals.user and globals.user.is_authenticated():
            result = get_user_tags(globals.request)

        context['all_user_tags'] = result

        return ''

@register.tag
def prepare_all_user_tags(parser, token):
    return PrepareAllUserTagsNode()

@register.simple_tag
def all_user_tags_json():
    result = {}

    if globals.user and globals.user.is_authenticated():
        result = get_user_tags(globals.request)

    return simplejson.dumps(result)


@register.inclusion_tag('private/edit_private.html')
def edit_private(object_str):
    """
    Display the the private editor for the given object. `object_str` is the object
    representaiton as defined by the `simple_str` method in the core module.
    """
    if not (object_str and globals.user and globals.user.is_authenticated()):
        return {}

    try:
        # find the object
        edit_object = get_object_from_str(object_str)
        app_label, model_name = get_app_and_model(edit_object)

        # get private data
        note = edit_object.get_user_note()
        private_tags = edit_object.get_user_tags()

        # special tags
        flags_and_tags = split_tags_and_flags(private_tags, model_name)

        # get other private tags
        other_tags = Tag.objects.filter(
                **{'private_%s_tags__owner' % model_name:globals.user})
        if private_tags:
            other_tags = other_tags.exclude(
                    id__in=[t.id for t in private_tags])
        if flags_and_tags['special']:
            other_tags = other_tags.exclude(
                    slug__in=[t['slug'] for t in flags_and_tags['special']])
        other_tags = other_tags.distinct()

        # for tags url
        if model_name == 'account':
            model_name_plural = 'accounts'
        else:
            model_name_plural = 'repositories'

        # urls for edit link and when_finished link
        if globals.request.is_ajax():
            when_finished = globals.request.META.get('HTTP_REFERER')
            if when_finished:
                host = 'http%s://%s' % (
                    's' if globals.request.is_secure() else '',
                    globals.request.get_host()
                )
                if when_finished.startswith(host):
                    when_finished = when_finished[len(host):]
                else:
                    when_finished = None
            if not when_finished:
                when_finished = edit_object.get_absolute_url()
            edit_url = when_finished + '%sedit_extra=%s&when_finished=%s' % (
                '&' if '?' in when_finished else '?',
                edit_object.simple_str(),
                urlquote(when_finished),
            )
        else:
            when_finished = get_request_param(globals.request, 'when_finished')
            edit_url = get_request_param(globals.request, 'edit_url', globals.request.get_full_path())

        return dict(
            edit_object = edit_object,
            note_save_form = NoteForm(instance=note) if note else NoteForm(noted_object=edit_object),
            note_delete_form = NoteDeleteForm(instance=note) if note else None,
            tag_save_form = TagsBaseForm(tagged_object=edit_object),
            tags_delete_form = TagsDeleteForm(tagged_object=edit_object) if private_tags else None,
            private_tags = flags_and_tags['normal'],
            other_tags = other_tags,
            special_tags = flags_and_tags['special'],
            used_special_tags = flags_and_tags['special_used'],
            url_tags = reverse('dashboard_tags', kwargs=dict(obj_type=model_name_plural)),
            edit_url = edit_url,
            when_finished = when_finished,
        )

    except:
        return {}

########NEW FILE########
__FILENAME__ = urls
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *

from private.views import note_save, note_delete, tags_save, tags_delete, ajax_edit, ajax_close, toggle, tag_save

urlpatterns = patterns('',
    url(r'^notes/save/$', note_save, name='note_save'),
    url(r'^notes/delete/$', note_delete, name='note_delete'),
    url(r'^tags/save/$', tags_save, name='tags_save'),
    url(r'^tags/delete/$', tags_delete, name='tags_delete'),
    url(r'^edit-ajax/(?P<object_key>(?:core\.)?(?:account|repository):\d+)/$', ajax_edit, name='private_ajax_edit'),
    url(r'^close-ajax/(?P<object_key>(?:core\.)?(?:account|repository):\d+)/$', ajax_close, name='private_ajax_close'),
    url(r'^toggle/(?P<key>star|check-later)/$', toggle, name='private_toggle'),
    url(r'^tag/save/$', tag_save, name='tag_save'),
)

########NEW FILE########
__FILENAME__ = views
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from operator import itemgetter

from django_globals import globals
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.shortcuts import redirect, render
from django.http import HttpResponseBadRequest

from notes.models import Note

from private.forms import (NoteForm, NoteDeleteForm,
        TagsForm, TagsDeleteForm, TagsAddOneForm, TagsRemoveOneForm, TagsCreateOneForm, TagsToggleForm)
from utils.model_utils import get_app_and_model
from core.models import get_object_from_str
from utils.djson.response import JSONResponse
from utils.views import ajax_login_required
from tagging.models import Tag
from tagging.flags import split_tags_and_flags

def get_user_note_for_object(obj, user=None):
    """
    Return a note by the current logged user for the given object
    A user can only have one note by object
    """
    user = user or globals.user
    if not (user and user.is_authenticated()):
        return None

    app_label, model_name = get_app_and_model(obj)

    try:
        return Note.objects.filter(
            author=user,
            content_type__app_label = app_label,
            content_type__model = model_name,
            object_id=obj.id
        )[0]
    except:
        return None

def return_from_editor(request, obj):
    """
    Manage redirect when we came from the editor.
    If the user clicked a button named "submit-close", he wants to
    quit the editor after action done, so redirect to the `when_finished`
    url, else use the `edit_url`.
    If not from the editor, redirect to the object default page.
    """
    if request.is_ajax():
        context = dict(
            obj_type = get_app_and_model(obj)[1],
            object = obj,
            edit_extra = obj.simple_str(),
            want_close = bool(request.POST.get('submit-close')),
        )
        return render(request, 'private/edit_private_ajax.html', context)

    param_name = 'edit_url'
    if request.POST.get('submit-close'):
        param_name = 'when_finished'
    return redirect(request.POST.get(param_name) or obj)

def ajax_edit(request, object_key):
    """
    Render the edit form, without other html, for use in ajax
    """
    return render(request, 'private/edit_private_ajax.html', dict(edit_extra = object_key))

def ajax_close(request, object_key):
    """
    Render the html to replace existing when closing via ajax the private editor
    """
    obj = get_object_from_str(object_key)
    return render(request, 'private/edit_private_ajax_onclose.html', dict(
        obj_type = get_app_and_model(obj)[1],
        object = obj,
    ))


@require_POST
@ajax_login_required
@login_required
def note_save(request):
    """
    Save a note for the current user
    """
    if ('delete' in request.POST
            or not request.POST.get('content', '').strip()):
        return note_delete(request)

    result = {}
    message_func = messages.success
    message_type = 'message'

    form = NoteForm(request.POST)
    if form.is_valid():
        note = form.save()
        noted_object = note.content_object
        message = 'Your private note was saved for `%s`'
        if request.is_ajax():
            #result['note'] = note.content
            result['note_rendered'] = note.rendered_content
    else:
        noted_object = form.get_related_object()
        if not noted_object:
            return HttpResponseBadRequest('Vilain :)')
        message = 'We were unable to save your note for `%s` !'
        message_func = messages.error
        message_type = 'error'

    message = message % noted_object

    if request.is_ajax():
        result[message_type] = message
        return JSONResponse(result)
    else:
        message_func(request, message)
        return redirect(noted_object or '/')


@require_POST
@ajax_login_required
@login_required
def note_delete(request):
    """
    Delete a note for the current user
    """

    result = {}
    message_func = messages.success
    message_type = 'message'

    form = NoteDeleteForm(request.POST)
    if form.is_valid():
        noted_object = form.get_related_object()
        form.save()
        message = 'Your private note for `%s` was deleted'
    else:
        noted_object = form.get_related_object()
        if not noted_object:
            return HttpResponseBadRequest('Vilain :)')
        message = 'We were unable to delete your note for `%s`!'
        message_func = messages.error
        message_type = 'error'

    message = message % noted_object

    if request.is_ajax():
        result[message_type] = message
        return JSONResponse(result)
    else:
        message_func(request, message)
        return redirect(noted_object or '/')


def get_user_tags_for_object(obj, user=None):
    """
    Return all tags associated to an object by the current logged user
    """
    user = user or globals.user
    if not (user and user.is_authenticated()):
        return None

    return obj.all_private_tags(user)


@require_POST
@ajax_login_required
@login_required
def tags_save(request):
    """
    Save some tags for the current user
    """
    view_data = dict(
        save = dict(
            form = TagsForm,
            success = 'Your private tags were saved',
            error = 'We were unable to save your tags !',
        ),
        add = dict(
            form = TagsAddOneForm,
            success = 'Your private tags was added',
            error = 'We were unable to add your tag !',
        ),
        remove = dict(
            form = TagsRemoveOneForm,
            success = 'Your private tags was removed',
            error = 'We were unable to remove your tag !',
        ),
        create = dict(
            form = TagsCreateOneForm,
            success = 'Your private tags was added',
            error = 'We were unable to add your tag ! (you must provide one...)',
        ),
    )

    action = request.POST.get('act', 'save')

    form = view_data[action]['form'](request.POST)
    if form.is_valid():
        tagged_object = form.get_related_object()
        form.save()
        messages.success(request, view_data[action]['success'])
    else:
        tagged_object = form.get_related_object()
        if not tagged_object:
            return HttpResponseBadRequest('Vilain :)')
        messages.error(request, view_data[action]['error'])

    return return_from_editor(request, tagged_object)


@require_POST
@ajax_login_required
@login_required
def tags_delete(request):
    """
    Delete some tags for the current user
    """
    form = TagsDeleteForm(request.POST)
    if form.is_valid():
        tagged_object = form.get_related_object()
        form.save()
        messages.success(request, 'Your private tags were deleted')
    else:
        tagged_object = form.get_related_object()
        if not tagged_object:
            return HttpResponseBadRequest('Vilain :)')
        messages.error(request, 'We were unable to delete your tags !')

    return return_from_editor(request, tagged_object)

## BELOW : new front ##

def _get_all_tags(request, model):
    return split_tags_and_flags(Tag.objects.filter(
                **{'private_%s_tags__owner' % model: request.user}).distinct(), model)

def get_user_tags(request):
    """
    Return the tags to be used in the search form filter.
    Work is done to note if tags are only for repositories, only for people
    or both.
    """
    # TODO => cache !

    if hasattr(request, '_all_user_tags'):
        return request._all_user_tags

    result = {'has': {}, 'for_only': {}}
    if request.user.is_authenticated():
        tags = {}
        types = ('places', 'projects', 'tags')
        for model in ('account', 'repository'):
            tags[model] = _get_all_tags(request, model)
            for tag_type in types:
                tags[model][tag_type] = set(tags[model][tag_type])

        ta, tr = tags['account'], tags['repository']
        for tag_type in types:
            set_a, set_r = ta[tag_type], tr[tag_type]
            result['has'][tag_type] = True
            if not set_a and not set_r:
                result['has'][tag_type] = False
            elif not set_a:
                result['for_only'][tag_type] = 'repositories'
            elif not set_r:
                result['for_only'][tag_type] = 'people'
            else:
                for tag in set_r - set_a:
                    tag.for_only = 'repositories'
                for tag in set_a - set_r:
                    tag.for_only = 'people'
            tags[tag_type] = set_a.union(set_r)

        for tag_type in types:
            result[tag_type] = []
            for tag in tags[tag_type]:
                tag_dict = dict(
                    slug=tag.slug,
                    name=tag.name,
                )
                for_only = getattr(tag, 'for_only', None)
                if for_only is not None:
                    tag_dict['for_only'] = for_only
                result[tag_type].append(tag_dict)


            result[tag_type] = sorted(result[tag_type], key=itemgetter('name'))

    request._all_user_tags = result
    return result

TOGGLABLE = {
    'star': {
        'tag': 'starred',
        'title_on': 'Starred',
        'title_off': 'Star it',
    },
    'check-later': {
        'tag': 'check later',
        'title_on': 'You want to check it later',
        'title_off': 'Click to check it later',
    },
}

@require_POST
@ajax_login_required
@login_required
def toggle(request, key, template=None):

    post = dict(tag = TOGGLABLE[key]['tag'])

    for var in ('content_type', 'object_id'):
        if var in request.POST:
            post[var] = request.POST[var]

    form = TagsToggleForm(post)

    if form.is_valid():
        tagged_object = form.get_related_object()
        is_set = form.save()
        flag = post['tag']
        message = 'Your `%s` flag was %s' % (flag, 'set' if is_set else 'removed')
        if request.is_ajax():
            return JSONResponse(dict(
                flag = flag,
                is_set = is_set,
                title = TOGGLABLE[key]['title_on' if is_set else 'title_off'],
                message = message,
            ))
        else:
            messages.success(request, message)
    else:
        tagged_object = form.get_related_object()
        if not tagged_object:
            return HttpResponseBadRequest('Vilain :)')
        message = 'We were unable to toggle your flag'
        if request.is_ajax():
            return JSONResponse(dict(error=message))
        else:
            messages.error(request, message)

    return redirect(tagged_object)

def _get_tag_type(tag):
    try:
        tag_type = tag[0]
        return 'place' if tag_type == '@' else 'project' if tag_type == '#' else 'tag'
    except:
        return tag

@require_POST
@ajax_login_required
@login_required
def tag_save(request):

    view_data = dict(
        #save = dict(
        #    form = TagsForm,
        #    success = 'Your private tags were saved',
        #    error = 'We were unable to save your tags !',
        #),
        add = dict(
            form = TagsAddOneForm,
            success = 'Your private %s for `%s` was just added',
            error = 'We were unable to add your private %s for `%s` !',
            data = dict(is_set=True),
        ),
        remove = dict(
            form = TagsRemoveOneForm,
            success = 'Your private %s for `%s` was just removed',
            error = 'We were unable to remove your private %s for `%s` !',
            data = dict(is_set=False),
        ),
        create = dict(
            form = TagsCreateOneForm,
            success = 'Your private %s for `%s` was just added',
            error = 'We were unable to add your private %s for `%s` ! (you must provide one...)',
            data = dict(is_set=True),
        ),
    )

    action = request.POST.get('act', 'create')

    form = view_data[action]['form'](request.POST)
    if form.is_valid():
        tagged_object = form.get_related_object()
        form.save()
        tag_name = form.cleaned_data['tag'][0]
        message = view_data[action]['success'] % (
            _get_tag_type(tag_name),
            tagged_object,
        )
        if request.is_ajax():
            result = dict(
                view_data[action]['data'],
                message = message,
            )
            if action == 'create':
                result['slug'] = Tag.objects.filter(**{
                    'private_%s_tags__owner' % tagged_object.model_name: globals.user,
                    'name': tag_name.lower()
                }).values_list('slug', flat=True)[0]
            return JSONResponse(result)
        messages.success(request, message)
    else:
        tagged_object = form.get_related_object()
        if not tagged_object:
            return HttpResponseBadRequest('Vilain :)')
        message = view_data[action]['error'] % (
            _get_tag_type(request.POST.get('tag', '')),
            tagged_object,
        )
        if request.is_ajax():
            return JSONResponse(dict(error=message))
        else:
            messages.error(request, message)

    return redirect(tagged_object.get_edit_tags_url() or '/')

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = urls
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *
from django.shortcuts import HttpResponsePermanentRedirect

def redirect_search(request, search_type, options=None):
    if not options:
        options = ()
    q = request.REQUEST.get('q', '')
    order = request.REQUEST.get('sort_by', '')
    url = '/?type=%s&q=%s&filter=%s&order=%s' % (
        search_type,
        q,
        ''.join(['&%s=%s' % (opt_key.replace('-', '_'), request.REQUEST.get(opt_key)) for opt_key in options]),
        order
    )

    return HttpResponsePermanentRedirect(url)

def redirect_search_repositories(request):
    return redirect_search(request, 'repositories', ('show-forks',))

def redirect_search_accounts(request):
    return redirect_search(request, 'people')

urlpatterns = patterns('',
    url(r'^$', redirect_search_repositories, name='search'),
    url(r'^users/$', redirect_search_accounts, name='search_accounts'),
)

########NEW FILE########
__FILENAME__ = views
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from datetime import datetime, timedelta

from django.http import Http404

from haystack.forms import SearchForm
from haystack.query import SQ, SearchQuerySet, EmptySearchQuerySet
from pure_pagination import Paginator, InvalidPage
from saved_searches.views import SavedSearchView as BaseSearchView
from saved_searches.models import SavedSearch
from browsecap.browser import is_crawler

from core.models import Account, Repository
from utils.sort import prepare_sort

# monkey patch to add simple_str to haystack
from haystack.models import SearchResult
def haystack_simple_str(self):
    return '%s.%s:%s' % (self.app_label, self.model_name, self.pk)
SearchResult.simple_str = haystack_simple_str

def parse_keywords(query_string):
    """
    Take a query string (think browser) and parse it to have a list of keywords.
    If many words are between two double-quotes, they are considered as one
    keyword.
    """
    qs = SearchQuerySet()
    keywords = []
    # Pull out anything wrapped in quotes and do an exact match on it.
    open_quote_position = None
    non_exact_query = query_string
    for offset, char in enumerate(query_string):
        if char == '"':
            if open_quote_position != None:
                current_match = non_exact_query[open_quote_position + 1:offset]
                if current_match:
                    keywords.append(qs.query.clean(current_match))
                non_exact_query = non_exact_query.replace('"%s"' % current_match, '', 1)
                open_quote_position = None
            else:
                open_quote_position = offset
    # Pseudo-tokenize the rest of the query.
    keywords += non_exact_query.split()

    return keywords

    result = []
    for keyword in keywords:
        result.append(qs.query.clean(keyword))

    return result

def make_query(fields, keywords, queryset=None):
    """
    Create the query for haystack for searching in `fields ` for documents
    with `keywords`. All keywords are ANDed, and if a keyword starts with a "-"
    all document with it will be excluded.
    """
    if not keywords or not fields:
        return EmptySearchQuerySet()

    if not queryset:
        queryset = SearchQuerySet()

    q = None
    for field in fields:
        q_field = None
        for keyword in keywords:
            exclude = False
            if keyword.startswith('-') and len(keyword) > 1:
                exclude = True
                keyword = keyword[1:]

            q_tmp = SQ(**{field: queryset.query.clean(keyword)})

            if exclude:
                q_tmp = ~ q_tmp

            if q_field:
                q_field = q_field & q_tmp
            else:
                q_field = q_tmp

        if q:
            q = q | q_field
        else:
            q = q_field

    if q:
        return queryset.filter(q)
    else:
        return queryset

class PurePaginationSearchView(BaseSearchView):

    def build_page(self):
        """
        Use django-pure-pagination
        """
        paginator = Paginator(self.results, self.results_per_page, request=self.request)
        try:
            page = paginator.page(self.request.GET.get('page', 1))
        except InvalidPage:
            raise Http404

        return (paginator, page)

class CoreSearchView(PurePaginationSearchView):
    """
    Class based view to handle search on core's objects
    """
    search_key = None
    model = None
    sort_map = {}

    def __init__(self, *args, **kwargs):
        """
        Set a "search key" for theses searches to be used for more recents/popular
        """
        kwargs['search_key'] = self.search_key
        kwargs['form_class'] = SearchForm
        super(CoreSearchView, self).__init__(*args, **kwargs)

    def get_sort(self):
        """
        Prepare (with validiti check) sorting key
        """
        if not hasattr(self.request, '_haystack_sort'):
            self.request._haystack_sort = None
            if self.sort_map:
                sort_key = self.request.GET.get('sort_by', None)
                self._haystack_sort = prepare_sort(
                    key = sort_key,
                    sort_map = self.sort_map,
                    default = None,
                    default_reverse = False
                )
        return self._haystack_sort

    def get_results(self):
        """
        Limit to a model, and sort if needed
        """
        query = self.get_query()
        if query:
            keywords = parse_keywords(self.get_query())
            queryset = make_query(self.search_fields, keywords)

            queryset = queryset.models(self.model)

            sort = self.get_sort()
            if sort and sort['db_sort']:
                queryset = queryset.order_by(sort['db_sort'])

            return queryset
        else:
            return EmptySearchQuerySet()

    def extra_context(self):
        """
        Add sorting infos in context
        """
        context = {}
        context.update(super(CoreSearchView, self).extra_context())
        context['sort'] = self.get_sort()

        return context


class RepositorySearchView(CoreSearchView):
    """
    Class based view to handle search of repositories
    """
    __name__ = 'RepositorySearchView'
    template = 'search/repositories.html'
    search_key = 'repositories'
    model = Repository
    sort_map = dict(
        name = 'slug_sort',
        owner = 'owner_slug_sort',
        updated = 'official_modified_sort',
    )
    search_fields = ('project', 'slug', 'slug_sort', 'name', 'description', 'readme',)

    def extra_context(self):
        """
        Add more recents and populars
        """
        context = {}
        context.update(super(RepositorySearchView, self).extra_context())
        context.update(dict(
            most_popular = SavedSearch.objects.most_popular(search_key='repositories')[:20],
            most_recent = SavedSearch.objects.most_recent(search_key='repositories')[:20],
        ))
        if self.request.user and self.request.user.is_authenticated():
            context['user_most_recent'] = SavedSearch.objects.most_recent(
                search_key='repositories', user=self.request.user)[:20]

        if self.request.GET.get('show-forks', False) == 'y':
            context['show_forks'] = 'y'

        return context

    def get_results(self):
        """
        Filter with is_fork
        """
        result = super(RepositorySearchView, self).get_results()

        if not isinstance(result, EmptySearchQuerySet):
            show_forks = self.request.GET.get('show-forks', False) == 'y'
            if not show_forks:
                result = result.exclude(is_fork=True)

        return result

    def save_search(self, page):
        """
        Do not save if the user made this search recently, if the sort order
        is not the default one, if a filter is applied, or if it's a crawler
        """

        # do not save if a filter is applied
        if self.request.GET.get('show-forks', False) == 'y':
            return

        # do not save if the sort order is not the default one
        sort = self.get_sort()
        if sort and sort['db_sort']:
            return

        # do not save if the request is from a user agent
        if is_crawler(self.request.META.get('HTTP_USER_AGENT', '')):
            return

        # do not save if we have a "/" in the request
        if "/" in self.query:
            return

        # check if this user did this search recently
        filter_user = None
        if self.request.user and self.request.user.is_authenticated():
            filter_user = self.request.user
        count_recent = SavedSearch.objects.most_recent(
                user = filter_user,
                search_key = self.search_key,
                collapsed = False,
            ).filter(
                    user_query = self.query,
                    created__gt = datetime.utcnow()-timedelta(minutes=15)
                ).count()
        if count_recent:
            return

        # nothing blocking, save the search
        return super(RepositorySearchView, self).save_search(page)


class AccountSearchView(CoreSearchView):
    """
    Class based view to handle search of accounts
    """
    __name__ = 'AccountSearchView'
    template = 'search/accounts.html'
    search_key = 'accounts'
    model = Account
    sort_map = dict(
        name = 'slug_sort',
    )
    search_fields = ('slug', 'slug_sort', 'name', )

########NEW FILE########
__FILENAME__ = search_sites
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

import haystack
haystack.autodiscover()


########NEW FILE########
__FILENAME__ = dev
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

#Settings used for development

DEBUG = True
SENTRY_DEBUG = True
HAYSTACK_SOLR_URL = 'http://localhost:8080/solr'

if False:
    # django debug toolbar
    INSTALLED_APPS = list(INSTALLED_APPS) + [
        'debug_toolbar',
    ]
    MIDDLEWARE_CLASSES = [
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    ] + list(MIDDLEWARE_CLASSES)
    INTERNAL_IPS = ('127.0.0.1',)

    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
    }


########NEW FILE########
__FILENAME__ = prod
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

DEBUG = False
TEMPLATE_DEBUG = False

TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', (
#        ('template_preprocessor.template.loaders.PreprocessedLoader', (
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
#        )),
    )),
)


########NEW FILE########
__FILENAME__ = settings
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

import os.path, sys
PROJECT_PATH = os.path.dirname(__file__)
sys.path[0:0] = [PROJECT_PATH,]

DEBUG = True
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
LANGUAGE_CODE = 'en'
LANGUAGES = (
    ('en', 'EN'),
)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.normpath(os.path.join(PROJECT_PATH, 'media/'))

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.normpath(os.path.join(PROJECT_PATH, 'static'))

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.normpath(os.path.join(PROJECT_PATH, 'project_static')),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '(w8x(uxj%opf^2ytd3wx_ztqu4c=7nn9yj0*6$et8z18b^(@&e'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

# django-template-preprocessor
#TEMPLATE_LOADERS = (
#    ('template_preprocessor.template.loaders.PreprocessedLoader',
#        TEMPLATE_LOADERS
#    ),
#)
#MEDIA_CACHE_DIR = os.path.normpath(os.path.join(MEDIA_ROOT, 'cache/'))
#MEDIA_CACHE_URL = os.path.normpath(os.path.join(MEDIA_URL, 'cache/'))
#TEMPLATE_CACHE_DIR = os.path.normpath(os.path.join(PROJECT_PATH, '..', 'templates-cache/'))
## Enabled modules of the template preprocessor
#TEMPLATE_PREPROCESSOR_OPTIONS = {
#        # Default settings
#        '*': ('html', 'whitespace-compression', ),
#
#        # Override for specific applications
#        ('django.contrib.admin', 'django.contrib.admindocs', 'debug_toolbar'): ('no-html',),
#}



MIDDLEWARE_CLASSES = (
    #'johnny.middleware.LocalStoreClearMiddleware',
    #'johnny.middleware.QueryCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django_globals.middleware.Global',
    'project.core.middleware.FetchFullCurrentAccounts',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.request',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.contrib.messages.context_processors.messages',
    'project.context_processors.context_settings',
    'project.context_processors.design',
    'project.context_processors.caching',
    'project.core.context_processors.backends',
    'project.core.context_processors.objects',
)

ROOT_URLCONF = 'project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.normpath(os.path.join(PROJECT_PATH, 'templates')),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.markup',

    # apps
    'raven.contrib.django',
    'django_extensions',
    'social_auth',
    'django_globals',
    'haystack',
    'saved_searches',
    'pure_pagination',
    'notes',
    'taggit',
    #'template_preprocessor',
    'redisession',
    'endless_pagination',
    'adv_cache_tag',
    'include_strip_tag',
    'offline_messages',

    # ours
    'utils',
    'front',
    'core',
    'accounts',
    'search',
    'private',
    'tagging',
    'dashboard',
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

DATE_FORMAT = "Y-m-d H:i"

# core
CONTENT_TYPES = dict(
    account = 17,
    repository = 18
)

# social_auth
AUTHENTICATION_BACKENDS = (
    'social_auth.backends.contrib.github.GithubBackend',
    'django.contrib.auth.backends.ModelBackend',
)
SOCIAL_AUTH_ENABLED_BACKENDS = ('github',)
SOCIAL_AUTH_EXTRA_DATA = True
GITHUB_EXTRA_DATA = [
    ('html_url', 'home'),
    ('login', 'original_login'),
    ('avatar_url', 'avatar_url'),
]
#GITHUB_AUTH_EXTRA_ARGUMENTS = {'scope': 'user,public_repo'}
SOCIAL_AUTH_ASSOCIATE_BY_MAIL = True
SOCIAL_AUTH_ERROR_KEY = 'social_errors'
SOCIAL_AUTH_UUID_LENGTH = 2

LOGIN_REDIRECT_URL = '/accounts/logged/'
LOGIN_URL = '/accounts/login/'
LOGIN_ERROR_URL = '/accounts/login/?error'

# enabled site backends
CORE_ENABLED_BACKENDS = ('github', )

# haystack
HAYSTACK_SITECONF = 'project.search_sites'
HAYSTACK_SEARCH_ENGINE = 'solr'
HAYSTACK_SEARCH_RESULTS_PER_PAGE = 20
HAYSTACK_INCLUDE_SPELLING = True
# solr
HAYSTACK_SOLR_URL = 'http://url/to/solr'
SOLR_MAX_IN = 1900

# pagination
ACCOUNTS_PER_PAGE = 50
REPOSITORIES_PER_PAGE = 50
ENDLESS_PAGINATION_ORPHANS = 5

# notes
NOTES_ALLOWED_MODELS = ('core.account', 'core.repository',)

# johnny-cache
CACHES = {
    'default' : dict(
        BACKEND = 'redis_cache.RedisCache',
        LOCATION = 'localhost:6379',
        OPTIONS = dict(
            DB = 1,
            PICKLE_VERSION = 2,
        ),
#        JOHNNY_CACHE = True,
    ),
    'templates': dict(
        BACKEND = 'redis_cache.RedisCache',
        LOCATION = 'localhost:6379',
        OPTIONS = dict(
            DB = 3,
            PICKLE_VERSION = 2,
        ),
    )
}
#JOHNNY_MIDDLEWARE_SECONDS = 3600 * 24 * 30
#JOHNNY_MIDDLEWARE_KEY_PREFIX='jc_reposio'

# redis
REDIS_PARAMS = dict(
    host = 'localhost',
    port = 6379,
    db = 0,
)

# sessions
SESSION_ENGINE = 'redisession.backend'
SESSION_SAVE_EVERY_REQUEST = True
MESSAGE_STORAGE = 'offline_messages.storage.OfflineStorageEngine'
# update the redisession default params
REDIS_SESSION_CONFIG = {
    'SERVER': dict(
        host = 'localhost',
        port = 6379,
        db = 2,
    ),
    'COMPRESS_LIB': None,
}

# adv cache
ADV_CACHE_INCLUDE_PK = True
ADV_CACHE_VERSIONING = True
ADV_CACHE_COMPRESS = True
ADV_CACHE_COMPRESS_SPACES = True
ADV_CACHE_BACKEND = 'templates'

# asynchronous
WORKER_FETCH_FULL_KEY = 'fetch_full:%d'
WORKER_FETCH_FULL_HASH_KEY = 'fetch_full_hash'
WORKER_FETCH_FULL_MAX_PRIORITY = 5
WORKER_FETCH_FULL_ERROR_KEY = 'fetch_full_error'

WORKER_UPDATE_RELATED_DATA_KEY = 'update_related_data'
WORKER_UPDATE_RELATED_DATA_SET_KEY = 'update_related_data_set'

WORKER_UPDATE_COUNT_KEY = 'update_count'

# sentry
SENTRY_DSN = None
SENTRY_PUBLIC_DSN = None

# metasettings
try:
    import metasettings
    METASETTINGS_DIR    = os.path.normpath(os.path.join(PROJECT_PATH, 'settings'))
    try:
        from settings_rules import method, rules
    except ImportError, e:
        raise e
    else:
        METASETTINGS_PATTERNS = rules
        METASETTINGS_METHOD = getattr(metasettings, method)
        metasettings.init(globals())
except Exception, e:
    sys.stderr.write("Error while loading metasettings : %s\n" % e )
    try:
        from local_settings import *
    except ImportError, e:
        sys.stderr.write("Error: You should define your own settings, see settings_rules.py.sample (or just add a local_settings.py)\nError was : %s\n" % e)
        sys.exit(1)

import redisco
redisco.connection_setup(**REDIS_PARAMS)

########NEW FILE########
__FILENAME__ = flags
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from core.core_utils import slugify

FLAGS = dict(
    account = ('starred', 'known', 'check later'),
    repository = ('starred', 'used', 'check later')
)
#FLAGS['all'] = tuple(set(FLAGS['account']+FLAGS['repository']))

def split_tags_and_flags(tags, obj_type, tags_are_dict=False):
    """
    Based on the given list of flags, we return a dict with 3 list of flags :
    - one with flags used
    - one with flags not used
    - one with the other tags
    """
    all_tags = [] # for compatibility
    real_tags = []
    special_tags = list(FLAGS[obj_type])
    used_special_tags = {}
    places = []
    projects = []
    for tag in tags:
        if tags_are_dict:
            lower_tag = tag['name'].lower()
        else:
            lower_tag = tag.name.lower()
        if lower_tag in FLAGS[obj_type]:
            used_special_tags[lower_tag] = tag
            special_tags.remove(lower_tag)
        else:
            start = lower_tag[0]
            if start == '@':
                places.append(tag)
            elif start == '#':
                projects.append(tag)
            else:
                real_tags.append(tag)
            all_tags.append(tag)

    special_tags = [dict(slug=slugify(tag), name=tag) for tag in special_tags]

    sorted_used_special_tags = [used_special_tags[tag] for tag in FLAGS[obj_type] if tag in used_special_tags]

    result = dict(
        special = special_tags,
        special_used = sorted_used_special_tags,
        normal = all_tags,
        tags = real_tags,
        places = places,
        projects = projects,
    )

    # had booleans for flags
    for tag in sorted_used_special_tags:
        if isinstance(tag, dict):
            result[tag['slug']] = True
        else:
            result[tag.slug] = True


    return result


########NEW FILE########
__FILENAME__ = forms
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django import forms
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.simplejson import dumps

from tagging.words import parse_tags

class TagAutocomplete(forms.widgets.Input):
    input_type = 'text'

    class Media:
        css = {
            'all': ('css/jquery.autocomplete.css',),
        }
        js = ('js/jquery.autocomplete.min.js',)

    def __init__(self, *args, **kwargs):
        self.available_tags = None
        super(TagAutocomplete, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        json_view = reverse('tagging_autocomplete')
        html = super(TagAutocomplete, self).render(name, value, attrs)

        params = dict(
            multiple = True,
            minChars = 0,
            delay = 100,
        )

        if self.available_tags is not None:
            params.update(dict(
                url = None,
                data = self.available_tags,
            ))

        js = u'<script type="text/javascript">jQuery().ready(function() { jQuery("#%s").autocomplete("%s", %s); });</script>' % (attrs['id'], json_view, dumps(params))
        return mark_safe("\n".join([html, js]))

    def set_available_tags(self, tags):
        """
        Set tags to look for in autocomplete mode
        """
        self.available_tags = tags


class TagField(forms.CharField):
    """
    Better TagField from taggit, that allows multi-line edit
    """
    widget = TagAutocomplete
    _help_text =  'Enter tags separated by comas. A tag can be composed of many words if they are between double quotes.<br />Exemple : <blockquote>django, "python framework", "my project: foobar", web</blockquote>This will result in 4 tags : "<em>django</em>", "<em>python framework</em>", "<em>my project: foobar</em>" and "<em>web</em>"'

    def __init__(self, *args, **kwargs):
        if not kwargs.get('help_text'):
            kwargs['help_text'] = self._help_text

        super(TagField, self).__init__(*args, **kwargs)

    def set_available_tags(self, tags):
        """
        Set tags to use in the autocomplete widget
        """
        if isinstance(self.widget, TagAutocomplete):
            self.widget.set_available_tags(tags)

    def clean(self, value):
        value = super(TagField, self).clean(value)
        try:
            return parse_tags(value.replace("\n", ", "))
        except ValueError:
            raise forms.ValidationError(_("Please see help text to know attended format"))


########NEW FILE########
__FILENAME__ = managers
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from taggit.managers import TaggableManager as BaseTaggableManager, _TaggableManager as _BaseTaggableManager
from taggit.utils import require_instance_manager

class TaggableManager(BaseTaggableManager):
    """
    We must subclass it to use our own manager
    """
    def __init__(self, *args, **kwargs):
        """
        A related name can now be set
        """
        related_name = kwargs.pop('related_name', None)
        super(TaggableManager, self).__init__(*args, **kwargs)
        if related_name:
            self.rel.related_name = related_name

    def __get__(self, instance, model):
        if instance is not None and instance.pk is None:
            raise ValueError("%s objects need to have a primary key value "
                "before you can access their tags." % model.__name__)
        manager = _TaggableManager(
            through=self.through, model=model, instance=instance
        )
        return manager


def prepare_tag(tag):
    return tag.strip().lower()


class _TaggableManager(_BaseTaggableManager):
    """
    Manager to use add, set... with a weight for each tag
    """

    def _lookup_kwargs(self, **filters):
        """
        It's possible to filter by other fields
        """
        result = self.through.lookup_kwargs(self.instance)
        result.update(filters)
        return result

    @require_instance_manager
    def add(self, tags, **filters):
        """
        Add a LIST of tags.
        Each tag can be :
        - a Tag object, eventually with a weight added field
        - a tuple with a tag and a weight, the tag can be:
            - a Tag object (weight will be the default one)
            - a string
        - a string (weight will be the default one)
        """
        if isinstance(tags, dict):
            tags = tags.items()

        obj_tags = {}
        str_tags = {}

        for tag in tags:
            if isinstance(tag, self.through.tag_model()):
                obj_tags[prepare_tag(tag.name)] = (tag, getattr(tag, 'weight', None))
            elif isinstance(tag, (tuple, list)):
                if isinstance(tag[0], self.through.tag_model()):
                    obj_tags[prepare_tag(tag[0].name)] = tag
                elif isinstance(tag[0], basestring):
                    str_tags[prepare_tag(tag[0])] = tag[1]
            elif isinstance(tag, basestring):
                str_tags[prepare_tag(tag)] = None

        # If str_tags has 0 elements Django actually optimizes that to not do a
        # query.  Malcolm is very smart.
        existing = self.through.tag_model().objects.filter(
            name__in=str_tags.keys()
        )

        dict_existing = dict((t.name, t) for t in existing)
        for tag in str_tags.keys():
            if tag in dict_existing:
                obj_tags[tag] = (dict_existing[tag], str_tags[tag])
                del str_tags[tag]

        # add new str_tags
        for new_tag, weight in str_tags.items():
            obj_tags[new_tag] = (
                self.through.tag_model().objects.create(name=new_tag),
                weight
            )

        for slug, tag in obj_tags.items():
            defaults = {}
            if tag[1]:
                defaults['weight'] = tag[1]

            params = dict(tag=tag[0], defaults=defaults)
            params.update(self._lookup_kwargs(**filters))

            tagged_item, created = self.through.objects.get_or_create(**params)
            if not created and tagged_item.weight != tag[1]:
                tagged_item.weight = tag[1]
                tagged_item.save()

    @require_instance_manager
    def set(self, tags, **filters):
        self.clear(**filters)
        self.add(tags, **filters)

    @require_instance_manager
    def remove(self, tags, **filters):
        str_tags = set()
        for tag in tags:
            if isinstance(tag, (tuple, list)):
                tag = tag[0]
            if isinstance(tag, self.through.tag_model()):
                tag = tag.name
            str_tags.add(tag)

        self.through.objects.filter(**self._lookup_kwargs(**filters)).filter(
            tag__name__in=str_tags).delete()

    @require_instance_manager
    def clear(self, **filters):
        self.through.objects.filter(**self._lookup_kwargs(**filters)).delete()

########NEW FILE########
__FILENAME__ = models
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.db import models
from django.contrib.auth.models import User

from taggit.models import ItemBase, TagBase

from core.core_utils import slugify as core_slugify
from tagging.managers import prepare_tag

class Tag(TagBase):

    official = models.BooleanField(default=False)

    class Meta:
        ordering = ['slug',]

    def slugify(self, tag, i=None):
        slug = core_slugify(tag)
        if i is not None:
            slug += "_%d" % i
        return slug

    def save(self, *args, **kwargs):
        self.name = prepare_tag(self.name)
        super(Tag, self).save(*args, **kwargs)

class BaseTaggedItem(ItemBase):
    weight = models.FloatField(blank=True, null=True, default=1)

    class Meta:
        abstract = True
        ordering = ('-weight', 'tag__slug',)

    @classmethod
    def tags_for(cls, model, instance=None):
        if instance is not None:
            return cls.tag_model().objects.filter(**{
                '%s__content_object' % cls.tag_relname(): instance
            })
        return cls.tag_model().objects.filter(**{
            '%s__content_object__isnull' % cls.tag_relname(): False
        }).distinct()

class PublicTaggedItem(BaseTaggedItem):
    class Meta(BaseTaggedItem.Meta):
        abstract = True

class PublicTaggedAccount(PublicTaggedItem):
    tag = models.ForeignKey(Tag, related_name="public_account_tags")
    content_object = models.ForeignKey('core.Account')

class PublicTaggedRepository(PublicTaggedItem):
    tag = models.ForeignKey(Tag, related_name="public_repository_tags")
    content_object = models.ForeignKey('core.Repository')

class PrivateTaggedItem(BaseTaggedItem):
    owner = models.ForeignKey(User, related_name="%(app_label)s_%(class)s_items")

    class Meta(BaseTaggedItem.Meta):
        abstract = True

class PrivateTaggedAccount(PrivateTaggedItem):
    tag = models.ForeignKey(Tag, related_name="private_account_tags")
    content_object = models.ForeignKey('core.Account')

class PrivateTaggedRepository(PrivateTaggedItem):
    tag = models.ForeignKey(Tag, related_name="private_repository_tags")
    content_object = models.ForeignKey('core.Repository')

def all_official_tags():
    """
    Return (and cache) the list of all official tags (as a set of slugs)
    """
    if not all_official_tags._cache:
        all_official_tags._cache = set(Tag.objects.filter(official=True).values_list('slug', flat=True))
    return all_official_tags._cache
all_official_tags._cache = None

########NEW FILE########
__FILENAME__ = tagging_tags
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from operator import itemgetter
from copy import copy

from django import template

register = template.Library()

@register.filter
def tag_is_in(tag, tags):
    """
    Return True if `tag` is in the given list
    """
    if not tag or not tags:
        return False

    if isinstance(tag, dict):
        slug = tag['slug']
    else:
        slug = tag.slug

    if isinstance(tags[0], dict):
        return slug in [t['slug'] for t in tags]
    else:
        return slug in [t.slug for t in tags]

#def tags_as_dicts(tags):
#    if not tags:
#        return []
#    if isinstance(tags[0], dict):
#        return copy(tags)
#    else:
#        result = []
#        for tag in tags:
#            tag_dict = dict(slug=tag.slug, name=tag.name)
#            if hasattr(tag, 'for_only'):
#                tag_dict['for_only'] = tag.for_only
#            result.append(tag_dict)
#        return result

@register.filter
def add_tags(tags1, tags2):

    if not tags2:
        return tags1 or []

    if not tags1:
        return tags2

    tags1 = copy(tags1)
    tags2 = sorted([dict(slug=t.slug, name=t.name) for t in tags2], key=itemgetter('slug'))

    # try to do it fast...
    result = []
    while tags1:
        while tags2 and tags2[0]['slug'] <= tags1[0]['slug']:
            tag = tags2.pop(0)
            if tag['slug'] != tags1[0]['slug']:
                result.append(tag)
        if not tags2:
            break
        result.append(tags1.pop(0))
    result += tags1

    return result

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
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import *
from tagging.views import autocomplete

urlpatterns = patterns('',
    url(r'^autocomplete$', autocomplete, name='tagging_autocomplete'),
)


########NEW FILE########
__FILENAME__ = views
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from tagging.models import Tag
from django.http import HttpResponse
from django.utils.datastructures import MultiValueDictKeyError

def autocomplete(request):
    try:
        tags = Tag.objects.filter(name__istartswith=request.GET['q']).values_list('name', flat=True)
    except MultiValueDictKeyError:
        tags = []
    return HttpResponse('\n'.join(tags), mimetype='text/plain')

########NEW FILE########
__FILENAME__ = words
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

"""
This module is here to create the firsts tags, based on thousands of
repositories : get all words, keep the most importants and save them as tags
Usage:
    all_words = {}
    repositories_to_words(Repository.objects.all(), words=all_words, return_words=False)
    all_tags = sort_words(all_words, limit=2500, return_format='set')
    add_tags(all_tags, official=True, check_duplicates=False)
"""

import string
import re


def get_ignore_words():
    """
    When needed, compute/cache and return a list of words to ignore
    """
    if get_ignore_words._ignore_cache is None:

        # stop words from postgresql files

        #import codecs
        #from core.core_utils import slugify
        #get_ignore_words._ignore_cache = set()
        #for filename in ('english', 'french', 'german', 'spanish',):
        #    f=codecs.open('/usr/share/postgresql/8.4/tsearch_data/%s.stop' % filename, 'r', 'utf-8')
        #    get_ignore_words._ignore_cache.update(slugify(li) for li in [l.strip() for l in f] if len(li) > 1)
        #    f.close()
        get_ignore_words._ignore_cache = set(('aber', 'about', 'above', 'after', 'again', 'against', 'ai', 'aie', 'aient', 'aies', 'ait', 'al', 'algo', 'algunas', 'algunos', 'all', 'alle', 'allem', 'allen', 'aller', 'alles', 'als', 'also', 'am', 'an', 'and', 'ander', 'andere', 'anderem', 'anderen', 'anderer', 'anderes', 'anderm', 'andern', 'anderr', 'anders', 'ante', 'antes', 'any', 'are', 'as', 'at', 'au', 'auch', 'auf', 'aura', 'aurai', 'auraient', 'aurais', 'aurait', 'auras', 'aurez', 'auriez', 'aurions', 'aurons', 'auront', 'aus', 'aux', 'avaient', 'avais', 'avait', 'avec', 'avez', 'aviez', 'avions', 'avons', 'ayant', 'ayante', 'ayantes', 'ayants', 'ayez', 'ayons', 'be', 'because', 'been', 'before', 'bei', 'being', 'below', 'between', 'bin', 'bis', 'bist', 'both', 'but', 'by', 'can', 'ce', 'ces', 'como', 'con', 'contra', 'cual', 'cuando', 'da', 'damit', 'dann', 'dans', 'das', 'dasselbe', 'dazu', 'de', 'dein', 'deine', 'deinem', 'deinen', 'deiner', 'deines', 'del', 'dem', 'demselben', 'den', 'denn', 'denselben', 'der', 'derer', 'derselbe', 'derselben', 'des', 'desde', 'desselben', 'dessen', 'dich', 'did', 'die', 'dies', 'diese', 'dieselbe', 'dieselben', 'diesem', 'diesen', 'dieser', 'dieses', 'dir', 'do', 'doch', 'does', 'doing', 'don', 'donde', 'dort', 'down', 'du', 'durante', 'durch', 'during', 'each', 'ein', 'eine', 'einem', 'einen', 'einer', 'eines', 'einig', 'einige', 'einigem', 'einigen', 'einiger', 'einiges', 'einmal', 'el', 'ella', 'ellas', 'elle', 'ellos', 'en', 'entre', 'er', 'era', 'erais', 'eramos', 'eran', 'eras', 'eres', 'es', 'esa', 'esas', 'ese', 'eso', 'esos', 'est', 'esta', 'estaba', 'estabais', 'estabamos', 'estaban', 'estabas', 'estad', 'estada', 'estadas', 'estado', 'estados', 'estais', 'estamos', 'estan', 'estando', 'estar', 'estara', 'estaran', 'estaras', 'estare', 'estareis', 'estaremos', 'estaria', 'estariais', 'estariamos', 'estarian', 'estarias', 'estas', 'este', 'esteis', 'estemos', 'esten', 'estes', 'esto', 'estos', 'estoy', 'estuve', 'estuviera', 'estuvierais', 'estuvieramos', 'estuvieran', 'estuvieras', 'estuvieron', 'estuviese', 'estuvieseis', 'estuviesemos', 'estuviesen', 'estuvieses', 'estuvimos', 'estuviste', 'estuvisteis', 'estuvo', 'et', 'etaient', 'etais', 'etait', 'etant', 'etante', 'etantes', 'etants', 'ete', 'etee', 'etees', 'etes', 'etiez', 'etions', 'etwas', 'eu', 'euch', 'eue', 'euer', 'eues', 'eumes', 'eure', 'eurem', 'euren', 'eurent', 'eurer', 'eures', 'eus', 'eusse', 'eussent', 'eusses', 'eussiez', 'eussions', 'eut', 'eutes', 'eux', 'few', 'for', 'from', 'fue', 'fuera', 'fuerais', 'fueramos', 'fueran', 'fueras', 'fueron', 'fuese', 'fueseis', 'fuesemos', 'fuesen', 'fueses', 'fui', 'fuimos', 'fuiste', 'fuisteis', 'fumes', 'fur', 'furent', 'further', 'fus', 'fusse', 'fussent', 'fusses', 'fussiez', 'fussions', 'fut', 'futes', 'gegen', 'gewesen', 'ha', 'hab', 'habe', 'habeis', 'haben', 'habia', 'habiais', 'habiamos', 'habian', 'habias', 'habida', 'habidas', 'habido', 'habidos', 'habiendo', 'habra', 'habran', 'habras', 'habre', 'habreis', 'habremos', 'habria', 'habriais', 'habriamos', 'habrian', 'habrias', 'had', 'han', 'has', 'hasta', 'hat', 'hatte', 'hatten', 'have', 'having', 'hay', 'haya', 'hayais', 'hayamos', 'hayan', 'hayas', 'he', 'hemos', 'her', 'here', 'hers', 'herself', 'hier', 'him', 'himself', 'hin', 'hinter', 'his', 'how', 'hube', 'hubiera', 'hubierais', 'hubieramos', 'hubieran', 'hubieras', 'hubieron', 'hubiese', 'hubieseis', 'hubiesemos', 'hubiesen', 'hubieses', 'hubimos', 'hubiste', 'hubisteis', 'hubo', 'ich', 'if', 'ihm', 'ihn', 'ihnen', 'ihr', 'ihre', 'ihrem', 'ihren', 'ihrer', 'ihres', 'il', 'im', 'in', 'indem', 'ins', 'into', 'is', 'ist', 'it', 'its', 'itself', 'je', 'jede', 'jedem', 'jeden', 'jeder', 'jedes', 'jene', 'jenem', 'jenen', 'jener', 'jenes', 'jetzt', 'just', 'kann', 'kein', 'keine', 'keinem', 'keinen', 'keiner', 'keines', 'konnen', 'konnte', 'la', 'las', 'le', 'les', 'leur', 'lo', 'los', 'lui', 'ma', 'machen', 'mais', 'man', 'manche', 'manchem', 'manchen', 'mancher', 'manches', 'mas', 'me', 'mein', 'meine', 'meinem', 'meinen', 'meiner', 'meines', 'meme', 'mes', 'mi', 'mia', 'mias', 'mich', 'mio', 'mios', 'mir', 'mis', 'mit', 'moi', 'mon', 'more', 'most', 'mucho', 'muchos', 'muss', 'musste', 'muy', 'my', 'myself', 'nach', 'nada', 'ne', 'ni', 'nicht', 'nichts', 'no', 'noch', 'nor', 'nos', 'nosotras', 'nosotros', 'not', 'notre', 'nous', 'now', 'nuestra', 'nuestras', 'nuestro', 'nuestros', 'nun', 'nur', 'ob', 'oder', 'of', 'off', 'ohne', 'on', 'once', 'only', 'ont', 'or', 'os', 'other', 'otra', 'otras', 'otro', 'otros', 'ou', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 'par', 'para', 'pas', 'pero', 'poco', 'por', 'porque', 'pour', 'qu', 'que', 'qui', 'quien', 'quienes', 'sa', 'same', 'se', 'sea', 'seais', 'seamos', 'sean', 'seas', 'sehr', 'sein', 'seine', 'seinem', 'seinen', 'seiner', 'seines', 'selbst', 'sentid', 'sentida', 'sentidas', 'sentido', 'sentidos', 'sera', 'serai', 'seraient', 'serais', 'serait', 'seran', 'seras', 'sere', 'sereis', 'seremos', 'serez', 'seria', 'seriais', 'seriamos', 'serian', 'serias', 'seriez', 'serions', 'serons', 'seront', 'ses', 'she', 'should', 'si', 'sich', 'sie', 'siente', 'sin', 'sind', 'sintiendo', 'so', 'sobre', 'soient', 'sois', 'soit', 'solche', 'solchem', 'solchen', 'solcher', 'solches', 'soll', 'sollte', 'some', 'sommes', 'somos', 'son', 'sondern', 'sonst', 'sont', 'soy', 'soyez', 'soyons', 'su', 'such', 'suis', 'sur', 'sus', 'suya', 'suyas', 'suyo', 'suyos', 'ta', 'tambien', 'tanto', 'te', 'tendra', 'tendran', 'tendras', 'tendre', 'tendreis', 'tendremos', 'tendria', 'tendriais', 'tendriamos', 'tendrian', 'tendrias', 'tened', 'teneis', 'tenemos', 'tenga', 'tengais', 'tengamos', 'tengan', 'tengas', 'tengo', 'tenia', 'teniais', 'teniamos', 'tenian', 'tenias', 'tenida', 'tenidas', 'tenido', 'tenidos', 'teniendo', 'tes', 'than', 'that', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they', 'this', 'those', 'through', 'ti', 'tiene', 'tienen', 'tienes', 'to', 'todo', 'todos', 'toi', 'ton', 'too', 'tu', 'tus', 'tuve', 'tuviera', 'tuvierais', 'tuvieramos', 'tuvieran', 'tuvieras', 'tuvieron', 'tuviese', 'tuvieseis', 'tuviesemos', 'tuviesen', 'tuvieses', 'tuvimos', 'tuviste', 'tuvisteis', 'tuvo', 'tuya', 'tuyas', 'tuyo', 'tuyos', 'uber', 'um', 'un', 'una', 'und', 'under', 'une', 'uno', 'unos', 'uns', 'unse', 'unsem', 'unsen', 'unser', 'unses', 'unter', 'until', 'up', 'very', 'viel', 'vom', 'von', 'vor', 'vos', 'vosostras', 'vosostros', 'votre', 'vous', 'vuestra', 'vuestras', 'vuestro', 'vuestros', 'wahrend', 'war', 'waren', 'warst', 'was', 'we', 'weg', 'weil', 'weiter', 'welche', 'welchem', 'welchen', 'welcher', 'welches', 'wenn', 'werde', 'werden', 'were', 'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'wie', 'wieder', 'will', 'wir', 'wird', 'wirst', 'with', 'wo', 'wollen', 'wollte', 'wurde', 'wurden', 'ya', 'yo', 'you', 'your', 'yours', 'yourself', 'yourselves', 'zu', 'zum', 'zur', 'zwar', 'zwischen'))

        # specific words to ignore
        get_ignore_words._ignore_cache.update(('http', 'https', 'www', 'com', 'net', 'org', 'de', 'versions', 'version', 'get', 'got', 'read', 'load', 'clone', 'repository', 'repositories', 'clones', 'fork', 'forks' 'forked', 'cloned', 'without', 'handle', 'manage', 'manages', 'managing', 'handles', 'make', 'makes', 'like', 'mimic', 'mimmics', 'modified', 'full', 'play', 'using', 'use', 'used', 'uses', 'work', 'works', 'worked', 'please', 'alpha', 'beta', 'info', 'infos', 'information', 'informations', 'etc', 'simple', 'yet', 'plus', 'think', 'type', 'anything', 'anyone', 'like', 'high', 'low', 'fast', 'slow', 'medium', 'half', 'based', 'cute', 'place', 'super', 'per', 'create', 'created', 'creates', 'top', 'see', 'useful', 'classic', 'set', 'party', 'second', 'first', 'third', 'pay', 'via', 'fuzzy', 'missing', 'improved', 'working', 'item', 'branch', 'items', 'branches', 'anywhere', 'little', 'big', 'one', 'two', 'three', 'many', 'more', 'long', 'short', 'pure', 'friendly', 'easy', 'hard', 'keep', 'non', 'meetup', 'send', 'sends', 'sending', 'custom', 'global', 'local', 'set', 'sets', 'list', 'lists', 'stuff', 'linked', 'link', 'links', 'line', 'lines', 'hot', 'thing', 'things', 'stage', 'staging', 'prod', 'production', 'world', 'word', 'auto', 'news', 'click', 'development', 'dev', 'devel', 'good', 'bad', 'soft', 'feature', 'features', 'object', 'objects', 'plus', 'help', 'slick', 'thin', 'thick', 'way', 'prog', 'program', 'programming', 'programs', 'love', 'real', 'util', 'utils', 'utility', 'utilities', 'web', 'hub', 'add', 'old', 'best', 'sub'))

    return get_ignore_words._ignore_cache
get_ignore_words._ignore_cache = None

# some synonyms
synonyms = {
    'achievements': 'achievement',
    'actions': 'action',
    'actor': 'actors',
    'add-on': 'addon',
    'add-ons': 'addon',
    'addons': 'addon',
    'algorithms': 'algorithm',
    'analytic': 'analytics',
    'application': 'app',
    'applications': 'app',
    'apps': 'app',
    'assets': 'asset',
    'asynchronous': 'async',
    'attributes': 'attribute',
    'authentication': 'auth',
    'authorization': 'auth',
    'backends': 'backend',
    'basics': 'basic',
    'blocks': 'block',
    'blueprints': 'blueprint',
    'boxes': 'box',
    'bundler': 'bundle',
    'bundles': 'bundle',
    'buttons': 'button',
    'cached': 'cache',
    'caching': 'cache',
    'calculator': 'calc',
    'cells': 'cell',
    'charts': 'chart',
    'classes': 'class',
    'collections': 'collection',
    'colors': 'color',
    'commands': 'command',
    'comments': 'comment',
    'commons': 'common',
    'components': 'component',
    'config': 'conf',
    'configs': 'conf',
    'configuration': 'conf',
    'contacts': 'contact',
    'contents': 'content',
    'cookbooks': 'cookbook',
    'cookies': 'cookie',
    'couch': 'couchdb',
    'databases': 'database',
    'db': 'database',
    'dbs': 'database',
    'defaults': 'default',
    'demos': 'demo',
    'dependencies': 'dependency',
    'deploy': 'deployment',
    'deployement': 'deployment',
    'docrails': 'rails',
    'docs': 'doc',
    'documentation': 'doc',
    'documented': 'doc',
    'documents': 'document',
    'dotemacs': 'emacs',
    'dotfiles': 'dotfile',
    'dotvim': 'vim',
    'email': 'mail',
    'emails': 'mail',
    'embedded': 'embed',
    'env': 'environment',
    'erl': 'erlang',
    'errors': 'error',
    'events': 'event',
    'examples': 'example',
    'exercice': 'exercise',
    'exercices': 'exercise',
    'exercises': 'exercise',
    'experiment': 'experiments',
    'extended': 'extend',
    'extending': 'extend',
    'extends': 'extend',
    'extensions': 'extension',
    'extras': 'extra',
    'facebooker': 'facebook',
    'fav': 'favotire',
    'favorites': 'favorite',
    'fb': 'facebook',
    'fields': 'field',
    'files': 'file',
    'files': 'file',
    'follower': 'follow',
    'followers': 'follow',
    'following': 'follow',
    'followings': 'follow',
    'formats': 'format',
    'forms': 'form',
    'frameworks': 'framework',
    'friends': 'friend',
    'functions': 'function',
    'games': 'game',
    'gems': 'gem',
    'generating': 'generate',
    'generators': 'generator',
    'guides': 'guide',
    'hacks': 'hack',
    'helpers': 'helper',
    'hg': 'mercurial',
    'highlighter': 'highlight',
    'hooks': 'hook',
    'hosts': 'host',
    'images': 'image',
    'img': 'image',
    'issues': 'issue',
    'jq': 'jquery',
    'js': 'javascript',
    'katas': 'kata',
    'keys': 'key',
    'labs': 'lab',
    'lang': 'language',
    'langs': 'lang',
    'languages': 'i18n',
    'learning': 'learn',
    'libraries': 'lib',
    'library': 'lib',
    'libs': 'lib',
    'log': 'logging',
    'logger': 'log',
    'logs': 'logging',
    'mailer': 'mail',
    'mails': 'mail',
    'maps': 'map',
    'members': 'member',
    'memcached': 'memcache',
    'messages': 'message',
    'metas': 'meta',
    'methods': 'method',
    'metric': 'metrics',
    'migrations': 'migration',
    'miscellaneous': 'misc',
    'mixins': 'mixin',
    'models': 'model',
    'modules': 'module',
    'mongo': 'mongodb',
    'monitor': 'monitoring',
    'monitored': 'monitoring',
    'moosex': 'moose',
    'multilingual': 'i18n',
    'nav': 'navigation',
    'notes': 'note',
    'notif': 'notification',
    'notification': 'notify',
    'notifications': 'notification',
    'notifier': 'notify',
    'objc': 'objective-c',
    'objective': 'objective-c',
    'objectivec': 'objective-c',
    'option': 'options',
    'packages': 'package',
    'pages': 'page',
    'paginate': 'pagination',
    'pal': 'paypal',
    'patches': 'patch',
    'patching': 'patch',
    'patterns': 'pattern',
    'permissions': 'permission',
    'pg': 'postgresql',
    'pgsql': 'postresql',
    'plugins': 'plugin',
    'postgre': 'postgresql',
    'postgres': 'postgresql',
    'pres': 'presentation',
    'presentations': 'presentation',
    'profiles': 'profile',
    'profiling': 'profile',
    'programs': 'program',
    'proj': 'project',
    'projects': 'project',
    'proto': 'prototype',
    'providers': 'provider',
    'puppetlabs': 'puppet',
    'py': 'python',
    'pygments': 'pygment',
    'questions': 'question',
    'queues': 'queue',
    'rating': 'rate',
    'ratings': 'rate',
    'rb': 'ruby',
    'recipes': 'recipe',
    'requests': 'request',
    'resources': 'resource',
    'robots': 'robot',
    'ror': 'rails',
    'router': 'route',
    'routes': 'route',
    'routing': 'route',
    'rubygem': 'gem',
    'rubygems': 'gem',
    'rule': 'rules',
    'samples': 'sample',
    'scripts': 'script',
    'secure': 'security',
    'services': 'service',
    'sessions': 'session',
    'setting': 'settings',
    'sgbd': 'database',
    'signals': 'signal',
    'sites': 'site',
    'slides': 'slide',
    'snip': 'snippet',
    'snippets': 'snippet',
    'sortable': 'sort',
    'sorted': 'sort',
    'sorter': 'sort',
    'sorting': 'sort',
    'spec': 'specifications',
    'specification': 'specifications',
    'specs': 'specifications',
    'statistic': 'stat',
    'statistics': 'stat',
    'stats': 'stat',
    'streams': 'stream',
    'subversion': 'svn',
    'tables': 'table',
    'tabs': 'tab',
    'tagger': 'tag',
    'tagging': 'tag',
    'tags': 'tag',
    'tasks': 'task',
    'templates': 'template',
    'tested': 'test',
    'testing': 'test',
    'tests': 'test',
    'themes': 'theme',
    'thumbnails': 'thumbnail',
    'tip': 'tips and tricks',
    'tips': 'tips and tricks',
    'tools': 'tool',
    'translatable': 'i18n',
    'translate': 'i18n',
    'translation': 'i18n',
    'translations': 'i18n',
    'translator': 'i18n',
    'trick': 'tips and tricks',
    'tricks': 'tips and tricks',
    'tutorials': 'tutorial',
    'tweet': 'twitter',
    'tweets': 'twitter',
    'twit': 'twitter',
    'types': 'type',
    'uploader': 'upload',
    'users': 'user',
    'validate': 'validation',
    'validates': 'validation',
    'validations': 'validation',
    'validator': 'validation',
    'values': 'value',
    'views': 'view',
    'vimfiles': 'vim',
    'vimrc': 'vim',
    'voting': 'vote',
    'widgets': 'widget',
    'wrapper': 'wrap',
    'wrapping': 'wrap',
}

def split_into_words(text):
    """
    Split a text into words. Split words with spaces and capital letters.
    Ignore some predefined words.
    Ex: "some ExtJs addons" => some, ext, js, addons
    """
    # TODO : if many upper letter, consider as a whole word
    words, word = [], []
    def add_word(letters):
        if len(letters) <= 1:
            return
        word = ''.join(letters).lower()
        if word in get_ignore_words():
            return
        words.append(word)
    previous_upper = False
    for ch in text:
        start_new = False
        append = True
        if ch.isupper():
            start_new = not previous_upper
        else:
            if not ch in string.letters:
                start_new = True
                append = False
        if start_new and word:
            add_word(word)
            word = []
        if append:
            word.append(ch)
    if word:
        add_word(word)
    return words

text_types = dict(slug=20, description=0.1)

def repository_to_words(repository, words=None, return_words=True, repository_is_dict=False):
    """
    Get some text in a repository and get all words (a dict with each word
    with its weight)
    """
    if words is None:
        words = {}
    for text_type, text_weight in text_types.items():
        if repository_is_dict:
            text = repository.get(text_type, None)
        else:
            text = getattr(repository, text_type, None)
        if not text:
            continue
        text_words = set(split_into_words(text))
        for word in text_words:
            if word not in words:
                words[word] = 0
            words[word] += text_weight
    if return_words:
        return words

def manage_synonyms(words=None, return_words=True):
    """
    Take a list of words and return it after removing synonyms
    """
    if words is None:
        words = {}
    syns = {}
    for word, count in words.iteritems():
        if word in synonyms:
            syns[word] = count
    for syn, count in syns.iteritems():
        good = synonyms[syn]
        if good not in words:
            words[good] = 0
        words[good] += count
        del words[syn]
    if return_words:
        return words

def repositories_to_words(queryset, words=None, return_words=True):
    """
    Taking a list of repositories and get all words as a dict with each word
    and its weight
    """
    if words is None:
        words = {}
    qs = queryset.values('slug', 'description', 'readme')
    for repository in qs:
        repository_to_words(repository, words, False, True)
    manage_synonyms(words, False)
    if return_words:
        return words

def sort_words(words, limit=1000, return_format=None):
    """
    Keep only some words
    """
    if return_format not in ('dict', 'tuple', 'set'):
        return_format = 'set'
    sorted_words = sorted(((word, count) for word, count in words.iteritems() if count > limit), key=lambda w: w[1], reverse=True)
    if return_format == 'set':
        return set(word for word, count in sorted_words)
    if return_format == 'tuple':
        return sorted_words
    return dict(sorted_words)

def get_tags_for_repository(repository, all_tags, repository_is_dict=False):
    """
    Given a list of tags, check for them in a repository and return the found
    ones.
    If you call this for a big list of repositories, you can pass "slug" and
    "description" in a dict (using values in your queryset instead of a whole
    one)
    """
    tags_dict = manage_synonyms(repository_to_words(repository, repository_is_dict=repository_is_dict))
    tags_ok = all_tags.intersection(set(tags_dict.keys()))
    for tag in tags_dict.keys():
        if tag not in tags_ok:
            del tags_dict[tag]
    return tags_dict

def add_tags(tags, official=False, check_duplicates=True):
    """
    Add all tags in database. Set check_duplicates to False if you are SURE no
    tags already in db
    """
    from tagging.models import Tag as TaggingTag
    if check_duplicates:
        add = lambda t: TaggingTag.objects.get_or_create(slug=t, defaults=dict(name=t, official=official))
    else:
        add = lambda t: TaggingTag.objects.create(slug=t, name=t, official=official)
    for tag in tags:
        result = add(tag)
        # if already exists and we say it's official : update it
        if check_duplicates and official:
            tag_obj, created = result
            if not created and not tag_obj.official:
                tag_obj.official = True
                tag_obj.save()

RE_PARSE_TAGS = re.compile('"(.+?)"|,')
def parse_tags(tagstring):
    """
    Parse tags using a simple regular expression (same result as
    replace taggit.utils.parse_tags but with kept order)
    """
    return [word.strip() for word in RE_PARSE_TAGS.split(tagstring) if word and word.strip()]

def edit_string_for_tags(tags):
    """
    Replace taggit.utils.edit_string_for_tags by keeping order
    """
    names = []
    for tag in tags:
        name = tag.name
        if u',' in name or u' ' in name:
            names.append('"%s"' % name)
        else:
            names.append(name)
    return u', '.join(names)

########NEW FILE########
__FILENAME__ = urls
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.conf.urls.defaults import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^', include('front.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^search/', include('search.urls')),
    url(r'^private/', include('private.urls')),
    url(r'^tags/', include('tagging.urls')),
    url(r'^dashboard/', include('dashboard.urls')),
    url(r'^', include('core.urls')),
)

########NEW FILE########
__FILENAME__ = response
# -*- coding: utf-8 -*-
 
from utils.djson import serialize_to_json
from django.http import HttpResponseForbidden, HttpResponse

MIMETYPE = "application/json"
 
class JSONResponse(HttpResponse):
    """ JSON response class """
    def __init__(self,content='', json_opts={}, mimetype=MIMETYPE, *args, **kwargs):
        """
        This returns a object that we send as json content using 
        utils.serialize_to_json, that is a wrapper to simplejson.dumps
        method using a custom class to handle models and querysets. Put your
        options to serialize_to_json in json_opts, other options are used by
        response.
        """
        if content:
            content = serialize_to_json(content, **json_opts)
        else:
            content = serialize_to_json([], **json_opts)
        super(JSONResponse,self).__init__(content, mimetype, *args, **kwargs)

########NEW FILE########
__FILENAME__ = model_utils
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.db.models.sql.query import get_proxied_model
from django.db.models.query_utils import DeferredAttribute

from haystack.models import SearchResult

def get_app_and_model(instance):
    """
    Return the app_label and model_name for the given instance.
    Work for normal model instance but also a proxied one (think `only` and
    `defer`), and even for instance of SearchResult (haystack)
    """
    if isinstance(instance, SearchResult):
        app_label, model_name = instance.app_label, instance.model_name
    else:
        meta = instance._meta
        if getattr(instance, '_deferred', False):
            meta = get_proxied_model(meta)._meta
        app_label, model_name = meta.app_label, meta.module_name

    return app_label, model_name

def get_deferred_fields(instance):
    """
    Return a list of all deferred field for the given instance.
    Deferred fields are ones in "deferred" or not in "only" or parts
    of a queryset
    """
    return [field.attname for field in instance._meta.fields if isinstance(instance.__class__.__dict__.get(field.attname), DeferredAttribute)]


# BELOW : https://github.com/andymccurdy/django-tips-and-tricks/blob/master/model_update.py

import operator

from django.db.models.expressions import F, ExpressionNode

EXPRESSION_NODE_CALLBACKS = {
    ExpressionNode.ADD: operator.add,
    ExpressionNode.SUB: operator.sub,
    ExpressionNode.MUL: operator.mul,
    ExpressionNode.DIV: operator.div,
    ExpressionNode.MOD: operator.mod,
    ExpressionNode.AND: operator.and_,
    ExpressionNode.OR: operator.or_,
    }

class CannotResolve(Exception):
    pass

def _resolve(instance, node):
    if isinstance(node, F):
        return getattr(instance, node.name)
    elif isinstance(node, ExpressionNode):
        return _resolve(instance, node)
    return node

def resolve_expression_node(instance, node):
    op = EXPRESSION_NODE_CALLBACKS.get(node.connector, None)
    if not op:
        raise CannotResolve
    runner = _resolve(instance, node.children[0])
    for n in node.children[1:]:
        runner = op(runner, _resolve(instance, n))
    return runner

def update(instance, **kwargs):
    "Atomically update instance, setting field/value pairs from kwargs"
    # fields that use auto_now=True should be updated corrected, too!
    for field in instance._meta.fields:
        if hasattr(field, 'auto_now') and field.auto_now and field.name not in kwargs:
            kwargs[field.name] = field.pre_save(instance, False)

    rows_affected = instance.__class__._default_manager.filter(pk=instance.pk).update(**kwargs)

    # apply the updated args to the instance to mimic the change
    # note that these might slightly differ from the true database values
    # as the DB could have been updated by another thread. callers should
    # retrieve a new copy of the object if up-to-date values are required
    for k,v in kwargs.iteritems():
        if isinstance(v, ExpressionNode):
            v = resolve_expression_node(instance, v)
        setattr(instance, k, v)

    # If you use an ORM cache, make sure to invalidate the instance!
    #cache.set(djangocache.get_cache_key(instance=instance), None, 5)
    return rows_affected


# BELOW : http://djangosnippets.org/snippets/1949/

import gc

def queryset_iterator(queryset, chunksize=1000):
    '''''
    Iterate over a Django Queryset ordered by the primary key

    This method loads a maximum of chunksize (default: 1000) rows in it's
    memory at the same time while django normally would load all rows in it's
    memory. Using the iterator() method only causes it to not preload all the
    classes.

    Note that the implementation of the iterator does not support ordered query sets.
    '''
    pk = 0
    last_pk = queryset.order_by('-pk')[0].pk
    queryset = queryset.order_by('pk')
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:chunksize]:
            pk = row.pk
            yield row
        gc.collect()

########NEW FILE########
__FILENAME__ = sort
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

# example of sort map :
#repository_sort_map = dict(
#    request_key = 'db_field'
#    name = 'slug_sort',
#    owner = 'owner__slug_sort',
#    updated = 'official_modified',
#)


def prepare_sort(key, sort_map, default, default_reverse):
    """
    Return needed informations about sorting (field to sort on in db, the key
    for the url, and if it's descending or ascending).
    The `key` must be in `sort_map`
    """
    reverse = False

    if key:
        if key[0] == '-':
            key = key[1:]
            reverse = True

    if key not in sort_map:
        key = default
        reverse = default_reverse

    if key:
        db_sort = sort_map[key]
        if reverse:
            db_sort = '-' + db_sort
    else:
        db_sort = None
        key = None

    return dict(
        db_sort = db_sort,
        key = key,
        reverse = reverse,
    )


########NEW FILE########
__FILENAME__ = utils_tags
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from uuid import uuid4

from django.utils.safestring import mark_safe
from django import template
register = template.Library()

@register.filter
def dict_get(dikt, key):
    """
    Custom template tag used like so:
    {{ dictionary|dict_get:var }}
    where dictionary is a dictionary and key is a variable representing
    one of it's keys
    """
    try:
        return dikt.__getitem__(key)
    except:
        return ''

@register.filter
def attr_get(obj, attr):
    """
    Custom template tag used like so:
    {{ object|attr_get:var }}
    where object is an object with attributes and attr is a variable representing
    one of it's attributes
    """
    try:
        result = getattr(obj, attr)
        if callable(result):
            return result()
        return result
    except:
        return ''

def insert_if(value, test, html):
    """
    Return the html if the value is equal to the tests
    """
    try:
        if value == test:
            return mark_safe(html)
    except:
        pass
    return ''

@register.filter
def check_if(value, test):
    return insert_if(value, test, ' checked="checked"')

@register.filter
def select_if(value, test):
    return insert_if(value, test, ' selected="selected"')

@register.filter
def current_if(value, test):
    return insert_if(value, test, ' current')

@register.filter
def current_class_if(value, test):
    return insert_if(value, test, ' class="current"')

class NoneIfOnlySpaces(template.Node):
    """
    If we have only spaces in the block, return an empty string
    """
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        content = self.nodelist.render(context)
        if content.strip() == '':
            return ''
        return content

def do_none_if_only_spaces(parser, token):
    nodelist = parser.parse(('end_%s' % token.contents,))
    parser.delete_first_token()
    return NoneIfOnlySpaces(nodelist)

register.tag('none_if_only_spaces', do_none_if_only_spaces)


# http://www.nomadjourney.com/2009/03/uuid-template-tag-for-django/
class UUIDNode(template.Node):
    """
    Implements the logic of this tag.
    """
    def __init__(self, var_name):
        self.var_name = var_name

    def render(self, context):
        context[self.var_name] = str(uuid4())
        return ''

def do_uuid(parser, token):
    """
    The purpose of this template tag is to generate a random
    UUID and store it in a named context variable.

    Sample usage:
        {% uuid var_name %}
        var_name will contain the generated UUID
    """
    try:
        tag_name, var_name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires exactly one argument" % token.contents.split()[0]
    return UUIDNode(var_name)

do_uuid = register.tag('uuid', do_uuid)


########NEW FILE########
__FILENAME__ = views
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.http import Http404
from pure_pagination import Paginator, InvalidPage
from utils.djson.response import JSONResponse

def paginate(request, objects, per_page):
    """
    Paginate the given `objects` list, with `per_page` entries per page,
    using the `page` GET parameter from the request
    """
    paginator = Paginator(objects, per_page, request=request)
    try:
        page = paginator.page(request.GET.get('page', 1))
    except InvalidPage:
        raise Http404
    else:
        return page

def get_request_param(request, key='next', default=None):
    """
    Try to retrieve and return the `key` parameter.
    """
    return request.POST.get(key, request.GET.get(key, None)) or default

def _ajax_login_required(msg):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if request.is_ajax() and not request.user.is_authenticated():
                return JSONResponse({'login_required': True, 'error': msg})
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def ajax_login_required(function=None, msg='You need to be logged for this'):
    actual_decorator = _ajax_login_required(msg)
    if function:
        return actual_decorator(function)
    return actual_decorator

########NEW FILE########
__FILENAME__ = views
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django.shortcuts import render

from core.models import Account, Repository

def home(request):
    mode = request.GET.get('show')
    if not mode or mode not in ('last', 'popular'):
        mode = 'last'

    context = dict(
        mode = mode
    )

    if mode == 'last':
        context['accounts'] = Account.for_list.get_last_fetched()
        context['repositories'] = Repository.for_list.get_last_fetched()
    else:
        context['accounts'] = Account.for_list.get_best(20)
        context['repositories'] = Repository.for_list.get_best(20)

    return render(request, 'home.html', context)

########NEW FILE########
__FILENAME__ = fetch_full
#!/usr/bin/env python

# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

"""
Full fetch of objects (core.models.SyncableModel.fetch_full)
"""

from workers_tools import init_django, stop_signal
init_django()

import sys

import traceback
from datetime import datetime
import re

from haystack import site
import redis
from redisco.containers import List, Hash

from django.conf import settings
from django.utils import simplejson
from django.db import IntegrityError, DatabaseError

from core.models import Account, Repository
from core.tokens import AccessTokenManager

RE_IGNORE_IMPORT = re.compile(r'(?:, )?"to_ignore": \[[^\]]*\]')

run_ok = True

def parse_json(json, priority):
    """
    Parse the data got from redis lists
    """
    result = {}

    # unserialize
    data = simplejson.loads(json)

    # parse object string
    model_name, id = data['object'].split(':')
    if model_name == 'core.account':
        model = Account
    elif model_name == 'core.repository':
        model = Repository
    else:
        raise Exception('Invalid object string')

    # check if object not already done or to be done in another list
    try:
        wanted_priority = int(Hash(settings.WORKER_FETCH_FULL_HASH_KEY)[data['object']])
    except:
        wanted_priority = None
    if wanted_priority is None or wanted_priority != priority:
        return { 'ignore': True }

    # load object
    result['object'] = model.objects.get(pk=id)

    # find a good token
    token_manager = AccessTokenManager.get_for_backend(result['object'].backend)
    result['token'] = token_manager.get_by_uid(data.get('token', None))

    # which depth...
    result['depth'] = data.get('depth', 0) or 0

    # maybe a user to notity
    result['notify_user'] = data.get('notify_user', None)

    return result

def main():
    """
    Main function to run forever...
    """
    global run_ok

    lists = [settings.WORKER_FETCH_FULL_KEY % priority for priority in range(settings.WORKER_FETCH_FULL_MAX_PRIORITY, -1, -1)]
    redis_instance = redis.Redis(**settings.REDIS_PARAMS)

    nb = 0
    max_nb = 500
    while run_ok:

        # wait for new data
        list_name, json = redis_instance.blpop(lists)

        priority = int(list_name[-1])

        nb += 1
        len_list = redis_instance.llen(list_name)

        sys.stderr.write("\n[%s  #%d | left(%s) : %d] %s\n" % (datetime.utcnow(), nb, list_name, len_list, RE_IGNORE_IMPORT.sub('', json)))

        try:
            # unserialize
            data = parse_json(json, priority)
            if not data:
                raise Exception('Invalid data : %s' % data)
        except:
            sys.stderr.write("\n".join(traceback.format_exception(*sys.exc_info())))

            List(settings.WORKER_FETCH_FULL_ERROR_KEY).append(json)

        else:
            if data.get('ignore', False):
                sys.stderr.write("  => ignore\n")

            else:
                # we're good

                params = dict(
                    token = data['token'],
                    depth = data['depth'],
                    async = False
                )
                if data.get('notify_user', None):
                    params['notify_user'] = data['notify_user']

                _, error = data['object'].fetch_full(**params)

                if error and isinstance(error, (DatabaseError, IntegrityError)):
                    # stop the process if integrityerror to start a new transaction
                    run_ok = False

        if nb >= max_nb:
            run_ok = False


def signal_handler(signum, frame):
    global run_ok
    run_ok = False


if __name__ == "__main__":
    stop_signal(signal_handler)
    main()

########NEW FILE########
__FILENAME__ = update_count
#!/usr/bin/env python

# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

"""
Update count for objects (core.models.SyncableModel.update_count)
"""

from workers_tools import init_django, stop_signal
init_django()

import sys

from django.conf import settings
from django.utils import simplejson
from django.db import transaction, IntegrityError, DatabaseError

import traceback
from datetime import datetime

from haystack import site
import redis

from core.models import Account, Repository

run_ok = True

def parse_json(json):
    """
    Parse the data got from redis list
    """
    # unserialize
    data = simplejson.loads(json)

    # parse object string
    model_name, id = data['object'].split(':')
    if model_name == 'core.account':
        model = Account
    elif model_name == 'core.repository':
        model = Repository
    else:
        raise Exception('Invalid object string')

    # load object
    data['object_str'] = data['object']
    data['object'] = model.objects.get(pk=id)

    return data

@transaction.commit_manually
def run_one(obj, count_type):
    """
    Update counts for `obj`, in its own transaction
    """
    try:
        obj.update_count(
            name = count_type,
            save = True,
            async = False
        )
    except (IntegrityError, DatabaseError), e:
        transaction.rollback()
        raise e
    else:
        transaction.commit()

def main():
    """
    Main function to run forever...
    """
    global run_ok

    redis_instance = redis.Redis(**settings.REDIS_PARAMS)

    nb = 0
    max_nb = 2500
    while run_ok:
        list_name, json = redis_instance.blpop(settings.WORKER_UPDATE_COUNT_KEY)

        nb += 1
        len_to_update = redis_instance.llen(settings.WORKER_UPDATE_COUNT_KEY)

        d = datetime.utcnow()

        try:
            data = parse_json(json)
            sys.stderr.write("[%s  #%d | left : %d] %s.%s (%s)" % (d, nb, len_to_update, data['object_str'], data['count_type'], data['object']))

            run_one(data['object'], data['count_type'])

        except Exception, e:
            sys.stderr.write(" => ERROR : %s (see below)\n" % e)
            sys.stderr.write("====================================================================\n")
            sys.stderr.write('\n'.join(traceback.format_exception(*sys.exc_info())))
            sys.stderr.write("====================================================================\n")

        else:
            try:
                count = getattr(data['object'], '%s_count' % data['count_type'])
            except:
                count = 'ERROR'
            sys.stderr.write(" in %s (%s)\n" % (datetime.utcnow()-d, count))

        if nb >= max_nb:
            run_ok = False

def signal_handler(signum, frame):
    global run_ok
    run_ok = False

if __name__ == "__main__":
    stop_signal(signal_handler)
    main()

########NEW FILE########
__FILENAME__ = update_related_data
#!/usr/bin/env python

# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

"""
Update related data (score, haystack, tags) for objects (core.models.SyncableModel.update_related_data)
"""

from workers_tools import init_django, stop_signal
init_django()

import sys
import traceback
from datetime import datetime

from django.conf import settings
from django.db import transaction, IntegrityError, DatabaseError

from haystack import site
import redis

from core.models import Account, Repository

run_ok = True

@transaction.commit_manually
def run_one(obj):
    """
    Update related for `obj`, in its own transaction
    """
    try:
        obj.update_related_data(async=False)
    except (IntegrityError, DatabaseError), e:
        transaction.rollback()
        raise e
    else:
        transaction.commit()

def main():
    """
    Main function to run forever...
    """
    global run_ok

    redis_instance = redis.Redis(**settings.REDIS_PARAMS)

    models = {
        'core.account': (Account, ()),
        'core.repository': (Repository, ('owner',)),
    }

    nb = 0
    max_nb = 2500
    while run_ok:
        list_name, obj_str = redis_instance.blpop(settings.WORKER_UPDATE_RELATED_DATA_KEY)
        redis_instance.srem(settings.WORKER_UPDATE_RELATED_DATA_SET_KEY, obj_str)

        nb += 1
        len_to_update = redis_instance.scard(settings.WORKER_UPDATE_RELATED_DATA_SET_KEY)

        d = datetime.utcnow()
        sys.stderr.write("[%s  #%d | left : %d] %s" % (d, nb, len_to_update, obj_str))

        try:
            # find the object

            model_name, id = obj_str.split(':')
            model, select_related = models[model_name]

            obj = model.objects
            if select_related:
                obj = obj.select_related(*select_related)
            obj = obj.get(pk=id)

            sys.stderr.write(' (%s)' % obj)

            # if still here, update the object
            run_one(obj)

        except Exception, e:
            sys.stderr.write(" => ERROR : %s (see below)\n" % e)
            sys.stderr.write("====================================================================\n")
            sys.stderr.write('\n'.join(traceback.format_exception(*sys.exc_info())))
            sys.stderr.write("====================================================================\n")

        else:
            sys.stderr.write(" in %s =>  score=%d, tags=(%s)\n" % (datetime.utcnow()-d, obj.score, ', '.join(obj.all_public_tags().values_list('slug', flat=True))))

        if nb >= max_nb:
            run_ok = False

def signal_handler(signum, frame):
    global run_ok
    run_ok = False

if __name__ == "__main__":
    stop_signal(signal_handler)
    main()

########NEW FILE########
__FILENAME__ = workers_tools
# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

import signal, sys, os

def init_django():
    PROJECT_PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    sys.path[0:0] = [PROJECT_PATH,]
    from django.core.management import setup_environ
    import settings
    setup_environ(settings)

def stop_signal(handler):
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)

########NEW FILE########
