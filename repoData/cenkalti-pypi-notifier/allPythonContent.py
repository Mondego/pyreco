__FILENAME__ = manage
#!/usr/bin/env python
import os
import errno
import logging
from functools import wraps

import flask.ext.script
from flask import current_app

from pypi_notifier import create_app, db, models, cache, sentry


logging.basicConfig(level=logging.DEBUG)


try:
    # Must be a class name from config.py
    config = os.environ['PYPI_NOTIFIER_CONFIG']
except KeyError:
    print "PYPI_NOTIFIER_CONFIG is not found in env, using DevelopmentConfig."
    print 'If you want to use another config please set it as ' \
          '"export PYPI_NOTIFIER_CONFIG=ProductionConfig".'
    config = 'DevelopmentConfig'


class Manager(flask.ext.script.Manager):
    """Subclassed to send exception information to Senry on command errors."""
    def command(self, func):
        func = catch_exception(func)
        return super(Manager, self).command(func)


def catch_exception(f):
    """Sends exception information to Sentry and reraises it."""
    @wraps(f)
    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception:
            if getattr(sentry, 'app', None):
                sentry.captureException()
            raise
    return inner


manager = Manager(create_app)
manager.add_option('-c', '--config', dest='config', required=False,
                   default=config)


@manager.shell
def make_shell_context():
    return dict(app=current_app, db=db, models=models)


@manager.command
def init_db():
    db.create_all()


@manager.command
def drop_db():
    try:
        os.unlink('/tmp/pypi_notifier.db')
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


@manager.command
def fetch_package_list():
    models.Package.get_all_names()


@manager.command
def clear_cache():
    cache.clear()


@manager.command
def find_latest(name):
    print models.Package(name).find_latest_version()


@manager.command
def update_repos():
    models.Repo.update_all_repos()


@manager.command
def update_packages():
    models.Package.update_all_packages()


@manager.command
def send_emails():
    models.User.send_emails()


if __name__ == '__main__':
    manager.run()

########NEW FILE########
__FILENAME__ = config.example
class BaseConfig(object):
    SECRET_KEY = 'insecure'
    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/pypi_notifier.db'
    CACHE_TYPE = 'filesystem'
    CACHE_DIR = '/tmp'


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/pypi_notifier.db'
    GITHUB_CLIENT_ID = ''
    GITHUB_CLIENT_SECRET = ''
    GITHUB_CALLBACK_URL = 'http://localhost:5000/github-callback'


class TestingConfig(BaseConfig):
    TESTING = True
    CSRF_ENABLED = False
    DEBUG_TB_ENABLED = False
    GITHUB_CLIENT_ID = 'a'
    GITHUB_CLIENT_SECRET = 'b'
    GITHUB_CALLBACK_URL = 'http://localhost:5000/github-callback'


class ProductionConfig(BaseConfig):
    SECRET_KEY = ''
    GITHUB_CLIENT_ID = ''
    GITHUB_CLIENT_SECRET = ''
    GITHUB_CALLBACK_URL = 'http://www.pypi-notifier.org/github-callback'
    SENTRY_DSN = None
    POSTMARK_APIKEY = ''

########NEW FILE########
__FILENAME__ = mixin
from pypi_notifier import db


class ModelMixin(object):

    @classmethod
    def get_or_create(cls, **kwargs):
        instance = db.session.query(cls).filter_by(**kwargs).first()
        if not instance:
            instance = cls(**kwargs)
        return instance

########NEW FILE########
__FILENAME__ = package
import logging
import xmlrpclib
from datetime import datetime, timedelta
from sqlalchemy import or_
from sqlalchemy.ext.associationproxy import association_proxy
from pypi_notifier import db, cache
from pypi_notifier.models.mixin import ModelMixin
from pypi_notifier.models.util import ignored


logger = logging.getLogger(__name__)


class Package(db.Model, ModelMixin):
    __tablename__ = 'packages'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True)
    latest_version = db.Column(db.String(20))
    updated_at = db.Column(db.DateTime)
    last_check = db.Column(db.DateTime)

    repos = association_proxy('requirements', 'repo')

    pypi = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')

    def __init__(self, name):
        self.name = name.lower()

    def __repr__(self):
        return "<Package %s>" % self.name

    @property
    def url(self):
        return "https://pypi.python.org/pypi/%s" % self.original_name

    @classmethod
    def update_all_packages(cls):
        packages = cls.query.filter(
            or_(
                cls.last_check <= datetime.utcnow() - timedelta(days=1),
                cls.last_check == None
            )
        ).all()
        for package in packages:
            with ignored(Exception):
                package.update_from_pypi()
                db.session.commit()

    @classmethod
    @cache.cached(timeout=3600, key_prefix='all_packages')
    def get_all_names(cls):
        packages = cls.pypi.list_packages()
        packages = filter(None, packages)
        return {name.lower(): name for name in packages}

    @property
    def original_name(self):
        return self.get_all_names()[self.name.lower()]

    def find_latest_version(self):
        version = self.pypi.package_releases(self.original_name)[0]
        logger.info("Latest version of %s is %s", self.original_name, version)
        return version

    def update_from_pypi(self):
        """
        Updates the latest version of the package by asking PyPI.

        """
        latest = self.find_latest_version()
        self.last_check = datetime.utcnow()
        if self.latest_version != latest:
            self.latest_version = latest
            self.updated_at = datetime.utcnow()

########NEW FILE########
__FILENAME__ = repo
import base64
import logging
from datetime import datetime
from pkg_resources import parse_requirements
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.associationproxy import association_proxy
from pypi_notifier import db, github
from pypi_notifier.models.user import User
from pypi_notifier.models.package import Package
from pypi_notifier.models.mixin import ModelMixin
from pypi_notifier.models.util import ignored


logger = logging.getLogger(__name__)


class Repo(db.Model, ModelMixin):
    __tablename__ = 'repos'
    __table_args__ = (
        UniqueConstraint('user_id', 'github_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    github_id = db.Column(db.Integer)
    name = db.Column(db.String(200))
    last_check = db.Column(db.DateTime)
    last_modified = db.Column(db.String(40))

    packages = association_proxy('requirements', 'package')

    def __init__(self, github_id, user):
        self.github_id = github_id
        self.user = user

    def __repr__(self):
        return "<Repo %s>" % self.name

    @property
    def url(self):
        return "https://github.com/%s" % self.name

    @classmethod
    def update_all_repos(cls):
        repos = cls.query.all()
        for repo in repos:
            with ignored(Exception):
                repo.update_requirements()
                db.session.commit()

    def update_requirements(self):
        """
        Fetches the content of the requirements.txt files from GitHub,
        parses the file and adds each requirement to the repo.

        """
        for project_name, specs in self.parse_requirements_file():
            # specs may be empty list if no version is specified in file
            # No need to add to table since we can't check updates.
            if specs:
                # There must be '==' operator in specs.
                operators = [s[0] for s in specs]
                if '==' in operators:
                    # If the project is not registered on PyPI,
                    # we are not adding it.
                    if project_name.lower() in Package.get_all_names():
                        self.add_new_requirement(project_name, specs)

        self.last_check = datetime.utcnow()

    def add_new_requirement(self, name, specs):
        from pypi_notifier.models.requirement import Requirement
        package = Package.get_or_create(name=name)
        requirement = Requirement.get_or_create(repo=self, package=package)
        requirement.specs = specs
        self.requirements.append = requirement

    def parse_requirements_file(self):
        contents = self.fetch_requirements()
        if contents:
            contents = strip_requirements(contents)
            if contents:
                for req in parse_requirements(contents):
                    yield req.project_name.lower(), req.specs

    def fetch_requirements(self):
        logger.info("Fetching requirements of repo: %s", self)
        path = 'repos/%s/contents/requirements.txt' % self.name
        headers = None
        if self.last_modified:
            headers = {'If-Modified-Since': self.last_modified}

        params = {'access_token': self.user.github_token}
        response = github.raw_request('GET', path,
                                      headers=headers, params=params)
        logger.debug("Response: %s", response)
        if response.status_code == 200:
            self.last_modified = response.headers['Last-Modified']
            response = response.json()
            if response['encoding'] == 'base64':
                return base64.b64decode(response['content'])
            else:
                raise Exception("Unknown encoding: %s" % response['encoding'])
        elif response.status_code == 304:  # Not modified
            return None
        elif response.status_code == 401:
            # User's token is not valid. Let's delete the user.
            db.session.delete(self.user)
        elif response.status_code == 404:
            # requirements.txt file is not found.
            # Remove the repo so we won't check it again.
            db.session.delete(self)
        else:
            raise Exception("Unknown status code: %s" % response.status_code)


def strip_requirements(s):
    """
    Cleans up requirements.txt contents and returns as new str.

    pkg_resources.parse_requirements() cannot parse the file if it contains
    an option for index URL.
        Example: "-i http://simple.crate.io/"

    Also it cannot parse the repository URLs.
        Example: git+https://github.com/pythonforfacebook/facebook-sdk.git

    """
    ignore_lines = (
        '-e',  # editable
        '-i', '--index-url',  # other source
        'git+', 'svn+', 'hg+', 'bzr+',  # vcs
        '-r',  # include other files (not supported yet) TODO
    )
    return '\n'.join(l for l in s.splitlines()
                     if not l.strip().startswith(ignore_lines))

########NEW FILE########
__FILENAME__ = requirement
import logging
from verlib import NormalizedVersion as Version, IrrationalVersionError
from pypi_notifier import db
from pypi_notifier.models.repo import Repo
from pypi_notifier.models.package import Package
from pypi_notifier.models.mixin import ModelMixin
from pypi_notifier.models.util import JSONType


logger = logging.getLogger(__name__)


class Requirement(db.Model, ModelMixin):
    __tablename__ = 'requirements'

    repo_id = db.Column(db.Integer,
                        db.ForeignKey(Repo.id),
                        primary_key=True)
    package_id = db.Column(db.Integer,
                           db.ForeignKey(Package.id),
                           primary_key=True)
    specs = db.Column(JSONType())

    package = db.relationship(
        Package,
        backref=db.backref('requirements', cascade='all, delete-orphan'))
    repo = db.relationship(
        Repo,
        backref=db.backref('requirements', cascade="all, delete-orphan"))

    def __init__(self, repo, package, specs=None):
        self.repo = repo
        self.package = package
        self.specs = specs

    def __repr__(self):
        return "<Requirement: %s requires %s with %s>" % (
            self.repo.name, self.package.name, self.specs)

    @property
    def required_version(self):
        logger.debug("Finding version of %s", self)
        for specifier, version in self.specs:
            logger.debug("specifier: %s, version: %s", specifier, version)
            if specifier == '==':
                return version

    @property
    def up_to_date(self):
        latest_version = self.package.latest_version
        if not latest_version:
            raise Exception("Latest version of the package is unknown.")

        try:
            return Version(self.required_version) == Version(latest_version)
        except IrrationalVersionError:
            return poor_mans_version_compare(self.required_version,
                                             latest_version)


def poor_mans_version_compare(v1, v2):
    """Check for equality of two version strings that cannot be compared by
    verlib. Example: "0.3.2.RC1"""
    def to_list(v):
        parts = v.split('.')
        # Try to convert each part to int
        for i in range(len(parts)):
            try:
                parts[i] = int(parts[i])
            except Exception:
                pass
        return parts
    return to_list(v1) == to_list(v2)

########NEW FILE########
__FILENAME__ = user
import logging
from datetime import datetime, timedelta
import pystmark
from flask import render_template, current_app
from sqlalchemy import or_
from pypi_notifier import db, github
from pypi_notifier.models.mixin import ModelMixin
from pypi_notifier.models.util import ignored


logger = logging.getLogger(__name__)


class User(db.Model, ModelMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    email = db.Column(db.String(200), nullable=False)
    github_id = db.Column(db.Integer, unique=True)
    github_token = db.Column(db.Integer, unique=True)
    email_sent_at = db.Column(db.DateTime)

    repos = db.relationship('Repo', backref='user',
                            cascade="all, delete-orphan")

    def __init__(self, github_token):
        self.github_token = github_token

    def __repr__(self):
        return "<User %s>" % self.name

    def get_outdated_requirements(self):
        outdateds = []
        for repo in self.repos:
            for req in repo.requirements:
                if not req.up_to_date:
                    logger.debug("%s is outdated", req)
                    outdateds.append(req)

        return outdateds

    @classmethod
    def send_emails(cls):
        users = cls.query.filter(
            or_(
                cls.email_sent_at <= datetime.utcnow() - timedelta(days=7),
                cls.email_sent_at == None
            )
        ).all()
        for user in users:
            with ignored(Exception):
                logger.info(user)
                user.send_email()
                user.email_sent_at = datetime.utcnow()
                db.session.commit()

    def send_email(self):
        outdateds = self.get_outdated_requirements()
        if outdateds:
            html = render_template('email.html', reqs=outdateds)
            message = pystmark.Message(
                sender='no-reply@pypi-notifier.org',
                to=self.email,
                subject="There are updated packages in PyPI",
                html=html)
            response = pystmark.send(message,
                                     current_app.config['POSTMARK_APIKEY'])
            response.raise_for_status()
        else:
            logger.info("No outdated requirement.")

    def get_emails_from_github(self):
        params = {'access_token': self.github_token}
        headers = {'Accept': 'application/vnd.github.v3'}
        emails = github.get('user/emails', params=params, headers=headers)
        return [e for e in emails if e['verified']]

########NEW FILE########
__FILENAME__ = util
import json
import logging
import traceback
from contextlib import contextmanager

from sqlalchemy.types import TypeDecorator, Text

from pypi_notifier import db


logger = logging.getLogger(__name__)


class JSONType(TypeDecorator):
    """Represents an immutable structure as a json-encoded string."""

    impl = Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


@contextmanager
def ignored(*exceptions):
    """Context manager to ignore specifed exceptions

         with ignored(OSError):
             os.remove(somefile)

    """
    try:
        yield
    except exceptions:
        db.session.rollback()
        logger.error(''.join(traceback.format_exc()))

########NEW FILE########
__FILENAME__ = views
import operator

from flask import render_template, request, redirect, url_for, g

from pypi_notifier import db, github
from pypi_notifier.models import Repo


def register_views(app):

    @app.route('/user')
    def user():
        return str(github.get('user'))

    @app.route('/repos')
    def repos():
        repos = github.get('user/repos')
        repos = with_organization_repos(repos)
        selected_ids = [r.github_id for r in g.user.repos]
        for repo in repos:
            repo['checked'] = (repo['id'] in selected_ids)
        return render_template('repos.html', repos=repos)

    def with_organization_repos(repos):
        all_repos = {r['id']: r for r in repos}  # index by id
        orgs = github.get('user/orgs')
        orgs_names = [o['login'] for o in orgs]
        for org_name in orgs_names:
            org_repos = github.get('orgs/%s/repos' % org_name)
            for repo in org_repos:
                all_repos[repo['id']] = repo  # add each repo for each org.

        all_repos = all_repos.values()
        all_repos.sort(key=operator.itemgetter('full_name'))
        return all_repos

    @app.route('/repos', methods=['POST'])
    def post_repos():
        # Add selected repos
        for name, github_id in request.form.iteritems():
            github_id = int(github_id)
            repo = Repo.query.filter(
                Repo.github_id == github_id,
                Repo.user_id == g.user.id).first()
            if repo is None:
                repo = Repo(github_id, g.user)
            repo.name = name
            db.session.add(repo)

        # Remove unselected repos
        ids = map(int, request.form.itervalues())
        for repo in g.user.repos:
            if repo.github_id not in ids:
                db.session.delete(repo)

        db.session.commit()
        return redirect(url_for('done'))

    @app.route('/done')
    def done():
        reqs = g.user.get_outdated_requirements()
        return render_template('done.html', reqs=reqs)

    @app.route('/unsubscribe', methods=['GET', 'POST'])
    def unsubscribe():
        if request.method == 'POST':
            if request.form['confirm'] == 'yes':
                if g.user:
                    db.session.delete(g.user)
                    db.session.commit()
                return render_template('unsubscribed.html')
            else:
                return redirect(url_for('index'))
        return render_template('unsubscribe-confirm.html')

########NEW FILE########
__FILENAME__ = run_gevent
#!/usr/bin/env python
from gevent.monkey import patch_all; patch_all()
from gevent.wsgi import WSGIServer
from pypi_notifier import create_app
app = create_app('ProductionConfig')
http_server = WSGIServer(('0.0.0.0', 5001), app)
http_server.serve_forever()

########NEW FILE########
__FILENAME__ = test
import unittest

from mock import patch
from flask.ext.github import GitHub

from pypi_notifier import create_app, db
from pypi_notifier.models import User, Repo, Requirement, Package
from pypi_notifier.config import TestingConfig


class PyPINotifierTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self._ctx = self.app.test_request_context()
        self._ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self._ctx.pop()

    def test_index(self):
        rv = self.client.get('/')
        assert 'Login' in rv.data

    def test_login(self):
        rv = self.client.get('/login')
        assert rv.status_code == 302
        assert 'github.com' in rv.headers['Location']

    @patch.object(User, 'get_emails_from_github')
    @patch.object(GitHub, 'get')
    @patch.object(GitHub, '_handle_response')
    def test_github_callback(self, handle_response, get, get_emails_from_github):
        handle_response.return_value = 'asdf'
        get.return_value = {'id': 1, 'login': 'cenkalti', 'email': 'cenk@x.com'}
        get_emails_from_github.return_value = [{'email': 'cenk@x.com',
                                                'primary': True,
                                                'verified': True}]

        self.client.get('/github-callback?code=xxxx')

        user = User.query.get(1)
        assert user
        assert user.github_token == 'asdf'

    def fixture(self):
        u1 = User('u1')
        u1.email = 'test@test'
        u2 = User('u2')
        u2.email = 'test@test'
        r1 = Repo('r1', u1)
        r2 = Repo('r2', u2)
        p1 = Package('p1')
        p2 = Package('p2')
        req1 = Requirement(r1, p1)
        req2 = Requirement(r2, p1)
        req3 = Requirement(r2, p2)
        db.session.add(u1)
        db.session.add(u2)
        db.session.add(req1)
        db.session.add(req2)
        db.session.add(req3)
        db.session.commit()
        return locals()

    def test_remove_user(self):
        """Tests SQLAlchemy relationships.

        When a User deletes his account all of the records should be deleted
        except Packages.

        """
        f = self.fixture()

        db.session.delete(f['u2'])
        db.session.commit()

        assert User.query.all() == [f['u1']]
        assert Repo.query.all() == [f['r1']]
        assert Requirement.query.all() == [f['req1']]
        assert Package.query.all() == [f['p1'], f['p2']]

    @patch.object(Package, 'get_all_names')
    def test_update_requirements(self, get_all_names):
        get_all_names.return_value = {'a': 'a', 'b': 'b'}

        u = User('t')
        u.email = 'test@test'
        r = Repo(2, u)
        db.session.add(r)
        db.session.commit()

        with patch.object(Repo, 'fetch_requirements') as fetch_requirements:
            fetch_requirements.return_value = "a==1.0\nb==2.1"
            r.update_requirements()
            db.session.commit()

        reqs = Requirement.query.all()
        assert len(reqs) == 2, reqs
        assert (reqs[0].package.name, reqs[0].required_version) == ('a', '1.0')
        assert (reqs[1].package.name, reqs[1].required_version) == ('b', '2.1')

    def test_strip_index_url(self):
        s = "-i http://simple.crate.io/\ndjango\ncelery"
        from pypi_notifier.models.repo import strip_requirements
        s = strip_requirements(s)
        assert s == 'django\ncelery'


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
