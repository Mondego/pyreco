__FILENAME__ = app
# Copyright 2012 litl, LLC.  Licensed under the MIT license.

import logging
import logging.config
import os

from flask import Flask

from .base import base
from .github import register_github_hooks


app = Flask("leeroy")

app.config.from_object("leeroy.settings")

if "LEEROY_CONFIG" in os.environ:
    app.config.from_envvar("LEEROY_CONFIG")

logging_conf = app.config.get("LOGGING_CONF")
if logging_conf and os.path.exists(logging_conf):
    logging.config.fileConfig(logging_conf)

logger_name = app.config.get("LOGGER_NAME")
if logger_name:
    logging.root.name = logger_name

app.register_blueprint(base)

register_github_hooks(app)

########NEW FILE########
__FILENAME__ = base
# Copyright 2012 litl, LLC.  Licensed under the MIT license.

import logging

from flask import Blueprint, current_app, json, request, Response, abort
from werkzeug.exceptions import BadRequest, NotFound

from . import github, jenkins

base = Blueprint("base", __name__)


@base.route("/ping")
def ping():
    return "pong"


def _parse_jenkins_json(request):
    # The Jenkins notification plugin (at least as of 1.4) incorrectly sets
    # its Content-type as application/x-www-form-urlencoded instead of
    # application/json.  As a result, all of the data gets stored as a key
    # in request.form.  Try to detect that and deal with it.
    if len(request.form) == 1:
        try:
            return json.loads(request.form.keys()[0])
        except ValueError:
            # Seems bad that there's only 1 key, but press on
            return request.form
    else:
        return request.json


@base.route("/notification/jenkins", methods=["POST"])
def jenkins_notification():
    data = _parse_jenkins_json(request)

    jenkins_name = data["name"]
    jenkins_number = data["build"]["number"]
    jenkins_url = data["build"]["full_url"]
    phase = data["build"]["phase"]

    logging.debug("Received Jenkins notification for %s %s (%s): %s",
                  jenkins_name, jenkins_number, jenkins_url, phase)

    if phase not in ("STARTED", "COMPLETED"):
        return Response(status=204)

    git_base_repo = data["build"]["parameters"]["GIT_BASE_REPO"]
    git_sha1 = data["build"]["parameters"]["GIT_SHA1"]

    repo_config = github.get_repo_config(current_app, git_base_repo)

    if repo_config is None:
        err_msg = "No repo config for {0}".format(git_base_repo)
        logging.warn(err_msg)
        raise NotFound(err_msg)

    desc_prefix = "Jenkins build '{0}' #{1}".format(jenkins_name,
                                                    jenkins_number)

    if phase == "STARTED":
        github_state = "pending"
        github_desc = desc_prefix + " is running"
    else:
        status = data["build"]["status"]

        if status == "SUCCESS":
            github_state = "success"
            github_desc = desc_prefix + " has succeeded"
        elif status == "FAILURE" or status == "UNSTABLE":
            github_state = "failure"
            github_desc = desc_prefix + " has failed"
        elif status == "ABORTED":
            github_state = "error"
            github_desc = desc_prefix + " has encountered an error"
        else:
            logging.debug("Did not understand '%s' build status. Aborting.",
                          status)
            abort()

    logging.debug(github_desc)

    github.update_status(current_app,
                         repo_config,
                         git_base_repo,
                         git_sha1,
                         github_state,
                         github_desc,
                         jenkins_url)

    return Response(status=204)


@base.route("/notification/github", methods=["POST"])
def github_notification():
    event_type = request.headers.get("X-GitHub-Event")
    if event_type is None:
        msg = "Got GitHub notification without a type"
        logging.warn(msg)
        return BadRequest(msg)
    elif event_type == "ping":
        return Response(status=200)
    elif event_type != "pull_request":
        msg = "Got unknown GitHub notification event type: %s" % (event_type,)
        logging.warn(msg)
        return BadRequest(msg)

    action = request.json["action"]
    pull_request = request.json["pull_request"]
    number = pull_request["number"]
    html_url = pull_request["html_url"]
    base_repo_name = github.get_repo_name(pull_request, "base")

    logging.debug("Received GitHub pull request notification for "
                  "%s %s (%s): %s",
                  base_repo_name, number, html_url, action)

    if action not in ("opened", "reopened", "synchronize"):
        logging.debug("Ignored '%s' action." % action)
        return Response(status=204)

    repo_config = github.get_repo_config(current_app, base_repo_name)

    if repo_config is None:
        err_msg = "No repo config for {0}".format(base_repo_name)
        logging.warn(err_msg)
        raise NotFound(err_msg)

    head_repo_name, shas = github.get_commits(current_app,
                                              repo_config,
                                              pull_request)

    logging.debug("Trigging builds for %d commits", len(shas))

    html_url = pull_request["html_url"]

    for sha in shas:
        github.update_status(current_app,
                             repo_config,
                             base_repo_name,
                             sha,
                             "pending",
                             "Jenkins build is being scheduled")

        logging.debug("Scheduling build for %s %s", head_repo_name, sha)
        jenkins.schedule_build(current_app,
                               repo_config,
                               head_repo_name,
                               sha,
                               html_url)

    return Response(status=204)

########NEW FILE########
__FILENAME__ = cron
import logging
import time
import datetime
from leeroy import github
from leeroy.app import app
from leeroy.github import get_pull_requests, get_status
from leeroy.jenkins import schedule_build

__author__ = 'davedash'

# How old does a commit status need to be (in seconds) before we retry the
# request.
# If a URL isn't present, this indicates a job was never made. If a URL is
# present, this indicates a job may not have reported back to Leeroy.
MAX_AGE_PENDING_WITH_URL = 10 * 60
MAX_AGE_PENDING_WITHOUT_URL = 2 * 60

log = logging.getLogger(__name__)


def convert_to_age_in_seconds(last_status):
    updated_at = last_status.get('updated_at')
    fmt = '%Y-%m-%dT%H:%M:%SZ'
    update_at_in_seconds = time.mktime(
        datetime.datetime.strptime(updated_at, fmt).timetuple())
    age = time.time() - update_at_in_seconds
    return age


def retry_jenkins(repo_config, pull_request):
    pr_number = pull_request['number']
    html_url = pull_request["html_url"]
    sha = pull_request['head']['sha']
    log.debug("Creating a new Jenkins job for {0}".format(pr_number))
    head_repo_name, shas = github.get_commits(app, repo_config, pull_request)
    schedule_build(app, repo_config, head_repo_name, sha, html_url)


def main():
    for repo_config in app.config["REPOSITORIES"]:
        for pull_request in get_pull_requests(app, repo_config):
            sha = pull_request['head']['sha']
            repo_name = repo_config['github_repo']
            status_data = get_status(app, repo_config, repo_name, sha).json
            if status_data:
                last_status = status_data[0]
                status = last_status.get('state')
                if status == 'pending':
                    max_age = MAX_AGE_PENDING_WITHOUT_URL
                    if last_status.get('target_url'):
                        max_age = MAX_AGE_PENDING_WITH_URL

                    age = convert_to_age_in_seconds(last_status)
                    if age > max_age:
                        # Somewhat heavy, but it'll do
                        retry_jenkins(repo_config, pull_request)
            else:
                # Somewhat heavy, but it'll do
                retry_jenkins(repo_config, pull_request)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = github
# Copyright 2012 litl, LLC.  Licensed under the MIT license.

from flask import json, url_for

import logging
import requests
import warnings

github_status_url = "/repos/{repo_name}/statuses/{sha}"
github_hooks_url = "/repos/{repo_name}/hooks"
github_commits_url = "/repos/{repo_name}/pulls/{number}/commits"

# Use requests.Session() objects keyed by github_repo to handle GitHub API
# authentication details (token vs user/pass) and SSL trust options.
request_sessions = {}

BUILD_COMMITS_ALL = "ALL"
BUILD_COMMITS_LAST = "LAST"
BUILD_COMMITS_NEW = "NEW"


def get_api_url(app, repo_config, url):
    base_url = repo_config.get("github_api_base",
                               app.config["GITHUB_API_BASE"])

    return base_url + url


def get_api_response(app, repo_config, url):
    url = get_api_url(app, repo_config, url).format(
        repo_name=repo_config.get('github_repo'))
    s = get_session_for_repo(app, repo_config)
    return s.get(url)


def get_repo_name(pull_request, key):
    return pull_request[key]["repo"]["full_name"]


def get_repo_config(app, repo_name):
    for repo_config in app.config["REPOSITORIES"]:
        if repo_name == repo_config["github_repo"]:
            return repo_config


def get_session_for_repo(app, repo_config):
    session = request_sessions.get(repo_config["github_repo"])
    if session is None:
        session = requests.Session()
        session.verify = repo_config.get("github_verify",
                                         app.config["GITHUB_VERIFY"])

        token = repo_config.get("github_token",
                                app.config.get("GITHUB_TOKEN"))

        if token:
            session.headers = {"Authorization": "token " + token}
        else:
            user = repo_config.get("github_user",
                                   app.config.get("GITHUB_USER"))
            password = repo_config.get("github_password",
                                       app.config.get("GITHUB_PASSWORD"))
            session.auth = (user, password)
    return session


def get_build_commits(app, repo_config):
    """
    Determine the value for BUILD_COMMITS from the app and repository
    config. Resolves the previous BUILD_ALL_COMMITS = True/False option
    to BUILD_COMMITS = 'ALL'/'LAST' respectively.
    """
    build_commits = repo_config.get("build_commits")
    build_all_commits = repo_config.get("build_all_commits",
                                        app.config.get("BUILD_ALL_COMMITS"))

    if not build_commits and build_all_commits is not None:
        # Determine BUILD_COMMITS from legacy BUILD_ALL_COMMITS
        if build_all_commits:
            build_commits = BUILD_COMMITS_ALL
        else:
            build_commits = BUILD_COMMITS_LAST
        warnings.warn("BUILD_ALL_COMMITS is deprecated. Use the BUILD_COMMITS "
                      "setting instead.", DeprecationWarning)
    elif not build_commits:
        # Determine BUILD_COMMITS from global app config.
        build_commits = app.config["BUILD_COMMITS"]
    return build_commits


def get_commits(app, repo_config, pull_request):
    head_repo_name = get_repo_name(pull_request, "head")
    base_repo_name = get_repo_name(pull_request, "base")
    build_commits = get_build_commits(app, repo_config)

    if build_commits in (BUILD_COMMITS_ALL, BUILD_COMMITS_NEW):
        number = pull_request["number"]

        url = get_api_url(app, repo_config, github_commits_url).format(
            repo_name=base_repo_name,
            number=number)

        s = get_session_for_repo(app, repo_config)
        response = s.get(url)

        commits = [c["sha"] for c in response.json]

        if build_commits == BUILD_COMMITS_NEW:
            commits = [sha for sha in commits if not
                       has_status(app, repo_config, base_repo_name, sha)]

        return head_repo_name, commits
    elif build_commits == BUILD_COMMITS_LAST:
        return head_repo_name, [pull_request["head"]["sha"]]
    else:
        logging.error("Invalid value '%s' for BUILD_COMMITS for repo: %s",
                      build_commits, base_repo_name)


def update_status(app, repo_config, repo_name, sha, state, desc,
                  target_url=None):
    url = get_api_url(app, repo_config, github_status_url).format(
        repo_name=repo_name,
        sha=sha)

    params = dict(state=state,
                  description=desc)

    if target_url:
        params["target_url"] = target_url

    headers = {"Content-Type": "application/json"}

    logging.debug("Setting status on %s %s to %s", repo_name, sha, state)

    s = get_session_for_repo(app, repo_config)
    s.post(url, data=json.dumps(params), headers=headers)


def get_status(app, repo_config, repo_name, sha):
    """Gets the status of a commit.

    .. note::
        ``repo_name`` might not ever be anything other than
        ``repo_config['github_repo']``.

    :param app: Flask app for leeroy
    :param repo_config: configuration for the repo
    :param repo_name: The name of the owner/repo
    :param sha: SHA for the status we are looking for
    :return: returns json response of status
    """
    url = get_api_url(app, repo_config, github_status_url).format(
        repo_name=repo_name, sha=sha)
    logging.debug("Getting status for %s %s", repo_name, sha)
    s = get_session_for_repo(app, repo_config)
    response = s.get(url)
    return response


def has_status(app, repo_config, repo_name, sha):
    response = get_status(app, repo_config, repo_name, sha)

    # The GitHub commit status API returns a JSON list, so `len()` checks
    # whether any statuses are set for the commit.
    return bool(len(response.json))


def register_github_hooks(app):
    with app.app_context():
        github_endpoint = "http://%s%s" % (
            app.config.get("GITHUB_NOTIFICATION_SERVER_NAME",
                           app.config["SERVER_NAME"]),
            url_for("base.github_notification", _external=False))

    for repo_config in app.config["REPOSITORIES"]:
        repo_name = repo_config["github_repo"]
        url = get_api_url(app, repo_config, github_hooks_url).format(
            repo_name=repo_name)

        s = get_session_for_repo(app, repo_config)
        response = s.get(url)

        if not response.ok:
            logging.warn("Unable to look up GitHub hooks for repo %s "
                         "with url %s: %s %s",
                         repo_name, url, response.status_code,
                         response.reason)
            continue

        found_hook = False
        for hook in response.json:
            if hook["name"] != "web":
                continue

            if hook['config']['url'] == github_endpoint:
                found_hook = True
                break

        if not found_hook:
            params = {"name": "web",
                      "config": {"url": github_endpoint,
                                 "content_type": "json"},
                      "events": ["pull_request"]}
            headers = {"Content-Type": "application/json"}

            response = s.post(url, data=json.dumps(params), headers=headers)

            if response.ok:
                logging.info("Registered github hook for %s: %s",
                             repo_name, github_endpoint)
            else:
                logging.error("Unable to register github hook for %s: %s",
                              repo_name, response.status_code)


def get_pull_request(app, repo_config, pull_request):
    """Data for a given pull request.

    :param app: Flask app
    :param repo_config: dict with ``github_repo`` key
    :param pull_request: the pull request number
    """
    response = get_api_response(
        app, repo_config,
        "/repos/{{repo_name}}/pulls/{0}".format(pull_request))
    return response.json


def get_pull_requests(app, repo_config):
    """Last 30 pull requests from a repository.

    :param app: Flask app
    :param repo_config: dict with ``github_repo`` key

    :returns: id for a pull request
    """
    response = get_api_response(app, repo_config, "/repos/{repo_name}/pulls")
    return (item for item in response.json)

########NEW FILE########
__FILENAME__ = jenkins
# Copyright 2012 litl, LLC.  Licensed under the MIT license.

import logging
import requests

build_path = "/job/{job_name}/buildWithParameters"\
    "?GIT_BASE_REPO={git_base_repo}" \
    "&GIT_HEAD_REPO={git_head_repo}" \
    "&GIT_SHA1={git_sha1}" \
    "&GITHUB_URL={github_url}"


def get_jenkins_auth(app, repo_config):
    user = repo_config.get("jenkins_user",
                           app.config["JENKINS_USER"])
    password = repo_config.get("jenkins_password",
                               app.config["JENKINS_PASSWORD"])

    return user, password


def get_jenkins_url(app, repo_config):
    return repo_config.get("jenkins_url", app.config["JENKINS_URL"])


def schedule_build(app, repo_config, head_repo_name, sha, html_url):
    base_repo_name = repo_config["github_repo"]
    job_name = repo_config["jenkins_job_name"]

    url = get_jenkins_url(app, repo_config) + \
        build_path.format(job_name=job_name,
                          git_base_repo=base_repo_name,
                          git_head_repo=head_repo_name,
                          git_sha1=sha,
                          github_url=html_url)

    logging.debug("Requesting build from Jenkins: %s", url)
    response = requests.post(url, auth=get_jenkins_auth(app, repo_config))
    logging.debug("Jenkins responded with status code %s",
                  response.status_code)

########NEW FILE########
__FILENAME__ = retry
import argparse
import logging

from leeroy import github
from leeroy.app import app
from leeroy.jenkins import schedule_build

__author__ = 'davedash'

log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('repo', choices=[repo['github_repo'] for repo in
                                         app.config['REPOSITORIES']])
    parser.add_argument('pull_request', type=int)
    args = parser.parse_args()

    log.info("Scheduling a build for PR {0}".format(args.pull_request))
    repo_config = github.get_repo_config(app, args.repo)
    pull_request = github.get_pull_request(app, repo_config, args.pull_request)
    head_repo_name, shas = github.get_commits(app, repo_config, pull_request)
    sha = pull_request['head']['sha']
    html_url = pull_request["html_url"]
    schedule_build(app, repo_config, head_repo_name, sha, html_url)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = scripts
#!/usr/bin/env python
# Copyright 2012 litl, LLC.  Licensed under the MIT license.

import sys
from optparse import OptionParser

from leeroy.app import app


def main():
    parser = OptionParser()
    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="activate the flask debugger")
    parser.add_option("-u", "--urls",
                      action="store_true", dest="urls", default=False,
                      help="list the url patterns used")
    parser.add_option("-b", "--bind-address",
                      action="store", type="string", dest="host",
                      default="0.0.0.0",
                      help="specify the address on which to listen")
    parser.add_option("-p", "--port",
                      action="store", type="int", dest="port",
                      default=5000,
                      help="specify the port number on which to run")

    (options, args) = parser.parse_args()

    if options.urls:
        from operator import attrgetter
        rules = sorted(app.url_map.iter_rules(), key=attrgetter("rule"))

        # don't show the less important HTTP methods
        skip_methods = set(["HEAD", "OPTIONS"])

        print "URL rules in use:"
        for rule in rules:
            methods = set(rule.methods).difference(skip_methods)

            print "  %s (%s)" % (rule.rule, " ".join(methods))

        sys.exit(0)

    app.debug = options.debug
    app.run(host=options.host, port=options.port)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = settings
DEBUG = True
LOGGING_CONF = "logging.conf"
LOGGER_NAME = "leeroy"

# The hostname (and :port, if necessary) of this server
SERVER_NAME = "leeroy.example.com"

# The hostname (and :port, if necessary) of the server GitHub should send
# notification to. It can be different from SERVER_NAME when another server is
# proxying requests to leeroy.  Falls back to SERVER_NAME if not provided.
# GITHUB_NOTIFICATION_SERVER_NAME = "leeroy.example.com"

# GitHub configuration
# The base URL for GitHub's API. If using GitHub Enterprise, change this to
# https://servername/api/v3
# GITHUB_API_BASE = "https://github.example.com/api/v3"
GITHUB_API_BASE = "https://api.github.com"

# Verify SSL certificate. Always set this to True unless using GitHub
# Enterprise with a self signed certificate.
GITHUB_VERIFY = True

# Create and use a GitHub API token or supply a user and password.
GITHUB_TOKEN = ""
# GITHUB_USER = "octocat"
# GITHUB_PASSWORD = ""

# Jenkins configuration
# JENKINS_USER and JENKINS_PASSWORD assume you're using basic HTTP
# authentication, not Jenkins's built in auth system.
JENKINS_URL = "https://jenkins.example.com"
JENKINS_USER = "hudson"
JENKINS_PASSWORD = ""

# Whether a Jenkins job is created for each commit in a pull request,
# or only one for the last one.
# What commits to build in a pull request. There are three options:
# 'ALL': build all commits in the pull request.
# 'LAST': build only the last commit in the pull request.
# 'NEW': build only commits that don't already have a commit status set.
#        (default)
BUILD_COMMITS = 'NEW'

# A list of dicts containing configuration for each GitHub repository &
# Jenkins job pair you want to join together.
#
# An example entry:
#
# {"github_repo": "litl/leeroy",
#  "jenkins_job_name": "leeroy-github",
#  "github_api_base": "https://github.example.com/api/v3",
#  "github_token": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
#  "github_user": "litl",
#  "github_password": "password",
#  "jenkins_url": ""https://jenkins2.example.com"",
#  "jenkins_user": "litl",
#  "jenkins_password": "password",
#  "build_commits": "LAST"}
#
# github_api_base, github_token, github_user, github_password, jenkins_url,
# jenkins_user, jenkins_password, and build_commits are optional.  If not
# present, they'll pull from the toplevel configuration options (GITHUB_USER,
# etc.)
REPOSITORIES = [
    {"github_repo": "litl/leeroy",
     "jenkins_job_name": "leeroy-github"}
]

########NEW FILE########
