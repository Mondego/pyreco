__FILENAME__ = config
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import os

DEBUG = False
TESTING = False
SECRET_KEY = os.environ["SECRET_KEY"]
LOG_FILENAME = os.environ["LOG_FILENAME"]

# GitHub API.
GITHUB_ID = os.environ["GITHUB_ID"]
GITHUB_SECRET = os.environ["GITHUB_SECRET"]

# Redis setup.
REDIS_PORT = int(os.environ.get("OSRC_REDIS_PORT", 6380))

########NEW FILE########
__FILENAME__ = database
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["get_connection", "get_pipeline", "format_key"]

import flask
import redis
redis_pool = None


def get_connection():
    global redis_pool
    if redis_pool is None:
        port = int(flask.current_app.config["REDIS_PORT"])
        redis_pool = redis.ConnectionPool(port=port)
    return redis.Redis(connection_pool=redis_pool)


def get_pipeline():
    r = get_connection()
    return r.pipeline()


def format_key(key):
    return "{0}:{1}".format(flask.current_app.config["REDIS_PREFIX"], key)

########NEW FILE########
__FILENAME__ = default_settings
#!/usr/bin/env python
# -*- coding: utf-8 -*-

DEBUG = False
SECRET_KEY = "development key"

REDIS_PORT = 6379
REDIS_PREFIX = "osrc"

GITHUB_ID = None
GITHUB_SECRET = None

########NEW FILE########
__FILENAME__ = frontend
#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["frontend"]

import json
import flask
import urllib
import string
import random
import requests
from math import sqrt
from functools import wraps

from . import stats
from .database import get_connection, format_key

frontend = flask.Blueprint("frontend", __name__)


# JSONP support.
# Based on: https://gist.github.com/aisipos/1094140
def jsonp(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = flask.request.args.get("callback", False)
        if callback:
            r = f(*args, **kwargs)
            content = "{0}({1})".format(callback, r.data)
            mime = "application/javascript"
            return flask.current_app.response_class(content, mimetype=mime,
                                                    status=r.status_code)
        else:
            return f(*args, **kwargs)
    return decorated_function


# Custom Jinja2 filters.
def firstname(value):
    return value.split()[0]


def compare(user1, user2):
    return stats.get_comparison(user1, user2)


@frontend.route("/")
def index():
    return flask.render_template("index.html")


def get_user_stats(username):
    # Get the user information.
    user_info, optout = stats.get_user_info(username)
    if user_info is None:
        return None, optout

    # Get the usage stats and bail if there isn't enough information.
    usage = stats.get_usage_stats(username)
    if usage is None:
        return None, optout

    # Get the social stats.
    social_stats = stats.get_social_stats(username)
    return dict(dict(user_info, **social_stats), usage=usage), optout


@frontend.route("/<username>")
@frontend.route("/<username>/")
def user_view(username):
    # Get the stats.
    stats, optout = get_user_stats(username)
    if stats is None:
        return flask.render_template("noinfo.html"), 404

    # Load the list of adjectives.
    with flask.current_app.open_resource("adjectives.json") as f:
        adjectives = json.load(f)

    # Load the list of languages.
    with flask.current_app.open_resource("languages.json") as f:
        language_list = json.load(f)

    # Load the list of event action descriptions.
    with flask.current_app.open_resource("event_actions.json") as f:
        event_actions = json.load(f)

    # Load the list of event verbs.
    with flask.current_app.open_resource("event_verbs.json") as f:
        event_verbs = json.load(f)

    # Figure out the user's best time of day.
    with flask.current_app.open_resource("time_of_day.json") as f:
        times_of_day = json.load(f)
    best_time = (max(enumerate(stats["usage"]["day"]),
                     key=lambda o: o[1])[0], None)
    for tod in times_of_day:
        times = tod["times"]
        if times[0] <= best_time[0] < times[1]:
            best_time = (best_time[0], tod["name"])
            break

    # Compute the name of the best description of the user's weekly schedule.
    with flask.current_app.open_resource("week_types.json") as f:
        week_types = json.load(f)
    best_dist = -1
    week_type = None
    user_vector = stats["usage"]["week"]
    norm = 1.0 / sqrt(sum([v * v for v in user_vector]))
    user_vector = [v*norm for v in user_vector]
    for week in week_types:
        vector = week["vector"]
        norm = 1.0 / sqrt(sum([v * v for v in vector]))
        dot = sum([(v*norm-w) ** 2 for v, w in zip(vector, user_vector)])
        if best_dist < 0 or dot < best_dist:
            best_dist = dot
            week_type = week["name"]

    return flask.render_template("user.html",
                                 adjectives=adjectives,
                                 language_list=language_list,
                                 event_actions=event_actions,
                                 event_verbs=event_verbs,
                                 week_type=week_type,
                                 best_time=best_time,
                                 enumerate=enumerate,
                                 **stats)


@frontend.route("/<username>.json")
@jsonp
def stats_view(username):
    stats, optout = get_user_stats(username)
    if stats is None:
        resp = flask.jsonify(message="Not enough information for {0}."
                             .format(username))
        resp.status_code = 404
        return resp
    return flask.jsonify(stats)


@frontend.route("/<username>/<reponame>")
def repo_view(username, reponame):
    s = stats.get_repo_info(username, reponame)
    if s is None:
        return flask.render_template("noinfo.html"), 404
    return flask.render_template("repo.html", **s)


@frontend.route("/<username>/<reponame>.json")
@jsonp
def repo_stats_view(username, reponame):
    s = stats.get_repo_info(username, reponame)
    if s is None:
        resp = flask.jsonify(message="Not enough information for {0}/{1}."
                             .format(username, reponame))
        resp.status_code = 404
        return resp
    return flask.jsonify(**s)


@frontend.route("/opt-out/<username>")
def opt_out(username):
    return flask.render_template("opt-out.html", username=username)


@frontend.route("/opt-out/<username>/login")
def opt_out_login(username):
    state = "".join([random.choice(string.ascii_uppercase + string.digits)
                     for x in range(24)])
    flask.session["state"] = state
    params = dict(
        client_id=flask.current_app.config["GITHUB_ID"],
        redirect_uri=flask.url_for(".opt_out_callback", username=username,
                                   _external=True),
        state=state,
    )
    return flask.redirect("https://github.com/login/oauth/authorize?{0}"
                          .format(urllib.urlencode(params)))


@frontend.route("/opt-out/<username>/callback")
def opt_out_callback(username):
    state1 = flask.session.get("state")
    state2 = flask.request.args.get("state")
    code = flask.request.args.get("code")
    if state1 is None or state2 is None or code is None or state1 != state2:
        flask.flash("Couldn't authorize access.")
        return flask.redirect(flask.url_for(".opt_out_error",
                                            username=username))

    # Get an access token.
    params = dict(
        client_id=flask.current_app.config["GITHUB_ID"],
        client_secret=flask.current_app.config["GITHUB_SECRET"],
        code=code,
    )
    r = requests.post("https://github.com/login/oauth/access_token",
                      data=params, headers={"Accept": "application/json"})
    if r.status_code != requests.codes.ok:
        flask.flash("Couldn't acquire an access token from GitHub.")
        return flask.redirect(flask.url_for(".opt_out_error",
                                            username=username))
    data = r.json()
    access = data.get("access_token", None)
    if access is None:
        flask.flash("No access token returned.")
        return flask.redirect(flask.url_for(".opt_out_error",
                                            username=username))

    # Check the username.
    r = requests.get("https://api.github.com/user",
                     params={"access_token": access})
    if r.status_code != requests.codes.ok:
        flask.flash("Couldn't get user information.")
        return flask.redirect(flask.url_for(".opt_out_error",
                                            username=username))
    data = r.json()
    login = data.get("login", None)
    if login is None or login.lower() != username.lower():
        flask.flash("You have to log in as '{0}' in order to opt-out."
                    .format(username))
        return flask.redirect(flask.url_for(".opt_out_error",
                                            username=username))

    # Save the opt-out to the database.
    user = username.lower()
    get_connection().set(format_key("user:{0}:optout".format(user)), True)

    return flask.redirect(flask.url_for(".opt_out_success", username=username))


@frontend.route("/opt-out/<username>/error")
def opt_out_error(username):
    return flask.render_template("opt-out-error.html", username=username)


@frontend.route("/opt-out/<username>/success")
def opt_out_success(username):
    return flask.render_template("opt-out-success.html")

########NEW FILE########
__FILENAME__ = index
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["rebuild_index", "get_neighbors"]

import os
import h5py
import flask
import shutil
import pyflann
import numpy as np

from .database import get_pipeline, format_key

_basepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
evttypes = [l.strip() for l in open(os.path.join(_basepath, "evttypes.txt"))]
langs = [l.strip() for l in open(os.path.join(_basepath, "languages.txt"))]

index_filename = "index.h5"
points_filename = "points.h5"

nevts = len(evttypes)
nlangs = len(langs)
nvector = 1 + 7 + nevts + 1 + 1 + 1 + 1 + nlangs + 1


def get_vector(user, pipe=None):
    """
    Given a username, fetch all of the data needed to build a behavior vector
    from the database.

    :param user: The GitHub username.
    :param pipe: (optional) if provided, simply add the requests to the
                 existing redis pipeline and don't execute the request.

    """
    no_pipe = False
    if pipe is None:
        pipe = get_pipeline()
        no_pipe = True

    user = user.lower()
    pipe.zscore(format_key("user"), user)
    pipe.hgetall(format_key("user:{0}:day".format(user)))
    pipe.zrevrange(format_key("user:{0}:event".format(user)), 0, -1,
                   withscores=True)
    pipe.zcard(format_key("user:{0}:contribution".format(user)))
    pipe.zcard(format_key("user:{0}:connection".format(user)))
    pipe.zcard(format_key("user:{0}:repo".format(user)))
    pipe.zcard(format_key("user:{0}:lang".format(user)))
    pipe.zrevrange(format_key("user:{0}:lang".format(user)), 0, -1,
                   withscores=True)

    if no_pipe:
        return pipe.execute()


def parse_vector(results):
    """
    Parse the results of a call to ``get_vector`` into a numpy array.

    :param results: The list of results from the redis request.

    """
    points = np.zeros(nvector)
    total = int(results[0])

    points[0] = 1.0 / (total + 1)

    # Week means.
    for k, v in results[1].iteritems():
        points[1 + int(k)] = float(v) / total

    # Event types.
    n = 8
    for k, v in results[2]:
        points[n + evttypes.index(k)] = float(v) / total

    # Number of contributions, connections and languages.
    n += nevts
    points[n] = 1.0 / (float(results[3]) + 1)
    points[n + 1] = 1.0 / (float(results[4]) + 1)
    points[n + 2] = 1.0 / (float(results[5]) + 1)
    points[n + 3] = 1.0 / (float(results[6]) + 1)

    # Top languages.
    n += 4
    for k, v in results[7]:
        if k in langs:
            points[n + langs.index(k)] = float(v) / total
        else:
            # Unknown language.
            points[-1] = float(v) / total

    return points


def _h5_filename(fn):
    return os.path.join(flask.current_app.config.get("INDEX_DIR", ""), fn)


def get_neighbors(name, num=5):
    """
    Find the K nearest neighbors to a user in "behavior space".

    :param name: The GitHub username.
    :param num: (optioanl; default: 5) The number of neighbors to find.

    """
    # Get the vector for this user.
    vector = get_vector(name)

    # If any of the components are None, bail.
    if any([v is None for v in vector]):
        return []

    # Parse the vector.
    vector = parse_vector(vector)

    # Load the points and user names.
    with h5py.File(_h5_filename(points_filename), "r") as f:
        points = f["points"][...]
        usernames = f["names"][...]

    # Load the index.
    flann = pyflann.FLANN()
    flann.load_index(_h5_filename(index_filename), points)

    # Find the neighbors.
    inds, dists = flann.nn_index(vector, num_neighbors=num+1)
    inds = inds[0]
    if usernames[inds[0]] == name:
        inds = inds[1:]
    else:
        inds = inds[:-1]
    return list(usernames[inds])


def rebuild_index():
    """
    Rebuild the K-nearest neighbors index based on 50000 of the most active
    users (ignoring the top 500 most active).

    """
    pipe = get_pipeline()
    usernames = pipe.zrevrange(format_key("user"), 500, 50500).execute()[0]

    for user in usernames:
        get_vector(user, pipe=pipe)

    results = pipe.execute()
    points = np.zeros([len(usernames), nvector])
    for i in range(len(usernames)):
        points[i, :] = parse_vector(results[8 * i:8 * (i + 1)])

    flann = pyflann.FLANN()
    flann.build_index(points)

    # Save the index.
    fn1 = _h5_filename(index_filename)
    tmp1 = fn1 + ".tmp"
    flann.save_index(tmp1)

    # Save the index coordinates.
    fn2 = _h5_filename(points_filename)
    tmp2 = fn2 + ".tmp"
    with h5py.File(tmp2, "w") as f:
        f["points"] = points
        f["names"] = usernames

    # Atomically move the index files into place.
    shutil.move(tmp1, fn1)
    shutil.move(tmp2, fn2)

########NEW FILE########
__FILENAME__ = stats
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["get_user_info", "get_social_stats", "get_usage_stats"]

import re
import json
import flask
import requests
import numpy as np

from .index import get_neighbors
from .timezone import estimate_timezone
from .database import get_connection, get_pipeline, format_key

ghapi_url = "https://api.github.com/users/{username}"

# The default time-to-live for the temporary keys (2 weeks).
DEFAULT_TTL = 14 * 24 * 60 * 60


def _redis_execute(pipe, cmd, key, *args, **kwargs):
    key = format_key(key)
    r = getattr(pipe, cmd)(key, *args, **kwargs)
    pipe.expire(key, DEFAULT_TTL)
    return r


def _is_robot():
    """
    Adapted from: https://github.com/jpvanhal/flask-split

    """
    robot_regex = r"""
        (?i)\b(
            Baidu|
            Gigabot|
            Googlebot|
            libwww-perl|
            lwp-trivial|
            msnbot|
            bingbot|
            SiteUptime|
            Slurp|
            WordPress|
            ZIBB|
            ZyBorg|
            YandexBot
        )\b
    """
    user_agent = flask.request.headers.get("User-Agent", "")
    return re.search(robot_regex, user_agent, flags=re.VERBOSE)


def get_user_info(username):
    # Normalize the username.
    user = username.lower()

    # Get the cached information.
    pipe = get_pipeline()
    pipe.get(format_key("user:{0}:name".format(user)))
    pipe.get(format_key("user:{0}:etag".format(user)))
    pipe.get(format_key("user:{0}:gravatar".format(user)))
    pipe.get(format_key("user:{0}:tz".format(user)))
    pipe.exists(format_key("user:{0}:optout".format(user)))
    name, etag, gravatar, timezone, optout = pipe.execute()
    if optout:
        return None, True

    if name is not None:
        name = name.decode("utf-8")

    # Return immediately if it's a robot.
    if not _is_robot():
        # Work out the authentication headers.
        auth = {}
        client_id = flask.current_app.config.get("GITHUB_ID", None)
        client_secret = flask.current_app.config.get("GITHUB_SECRET", None)
        if client_id is not None and client_secret is not None:
            auth["client_id"] = client_id
            auth["client_secret"] = client_secret

        # Perform a conditional fetch on the database.
        headers = {}
        if etag is not None:
            headers = {"If-None-Match": etag}

        r = requests.get(ghapi_url.format(username=username), params=auth,
                         headers=headers)
        code = r.status_code
        if code != 304 and code == requests.codes.ok:
            data = r.json()
            name = data.get("name") or data.get("login") or username
            etag = r.headers["ETag"]
            gravatar = data.get("gravatar_id", "none")
            location = data.get("location", None)
            if location is not None:
                tz = estimate_timezone(location)
                if tz is not None:
                    timezone = tz

            # Update the cache.
            _redis_execute(pipe, "set", "user:{0}:name".format(user), name)
            _redis_execute(pipe, "set", "user:{0}:etag".format(user), etag)
            _redis_execute(pipe, "set", "user:{0}:gravatar".format(user),
                           gravatar)
            if timezone is not None:
                _redis_execute(pipe, "set", "user:{0}:tz".format(user),
                               timezone)
            pipe.execute()

    return {
        "username": username,
        "name": name if name is not None else username,
        "gravatar": gravatar if gravatar is not None else "none",
        "timezone": int(timezone) if timezone is not None else None,
    }, False


def get_social_stats(username, max_connected=5, max_users=50):
    if _is_robot():
        return {
            "connected_users": [],
            "similar_users": [],
            "repositories": [],
        }

    r = get_connection()
    pipe = r.pipeline()
    user = username.lower()

    # Find the connected users.
    connection_key = format_key("social:connection:{0}".format(user))
    pipe.exists(connection_key)
    pipe.zrevrange(connection_key, 0, max_connected-1)
    pipe.zrevrange(format_key("social:user:{0}".format(user)), 0, -1,
                   withscores=True)
    flag, connected_users, repos = pipe.execute()
    if not _is_robot() and not flag:
        [pipe.zrevrange(format_key("social:repo:{0}".format(repo)), 0,
                        max_users)
         for repo, count in repos]
        users = pipe.execute()
        [pipe.zincrby(connection_key, u, 1) for l in users for u in l
         if u != user]
        pipe.expire(connection_key, 172800)
        pipe.zrevrange(connection_key, 0, max_connected-1)
        connected_users = pipe.execute()[-1]

    # Get the nearest neighbors in behavior space.
    similar_users = get_neighbors(user)
    [pipe.get(format_key("user:{0}:name".format(u)))
     for u in connected_users + similar_users]
    names = pipe.execute()

    # Parse all the users.
    users = [{"username": u, "name": n.decode("utf-8") if n is not None else u}
             for u, n in zip(connected_users+similar_users, names)]

    nc = len(connected_users)
    return {
        "connected_users": users[:nc],
        "similar_users": users[nc:],
        "repositories": [{"repo": repo, "count": int(count)}
                         for repo, count in repos[:5] if int(count) > 5],
    }


def make_histogram(data, size, offset=0):
    result = [0] * size
    for k, v in data:
        val = float(v)
        i = int(k) + offset
        while (i < 0):
            i += size
        result[i % size] = val
    return result


def get_usage_stats(username):
    user = username.lower()
    pipe = get_pipeline()

    # Get the total number of events performed by this user.
    pipe.zscore(format_key("user"), user)

    # The timezone estimate.
    pipe.get(format_key("user:{0}:tz".format(user)))

    # Get the top <= 5 most common events.
    pipe.zrevrangebyscore(format_key("user:{0}:event".format(user)),
                          "+inf", 0, 0, 5, withscores=True)

    # The average daily and weekly schedules.
    pipe.hgetall(format_key("user:{0}:hour".format(user)))
    pipe.hgetall(format_key("user:{0}:day".format(user)))

    # The language stats.
    pipe.zrevrange(format_key("user:{0}:lang".format(user)), 0, -1,
                   withscores=True)

    # Parse the results.
    results = pipe.execute()
    total_events = int(results[0]) if results[0] is not None else 0
    if not total_events:
        return None
    timezone = results[1]
    offset = int(timezone) + 8 if timezone is not None else 0
    event_counts = results[2]
    daily_histogram = make_histogram(results[3].items(), 24, offset)
    weekly_histogram = make_histogram(results[4].items(), 7)
    languages = results[5]

    # Parse the languages into a nicer form and get quantiles.
    [(pipe.zcount(format_key("lang:{0}:user".format(l)), 100, "+inf"),
      pipe.zrevrank(format_key("lang:{0}:user".format(l)), user))
     for l, c in languages]
    quants = pipe.execute()
    languages = [{"language": l,
                  "quantile": (min([100, int(100 * float(pos) / tot) + 1])
                               if tot > 0 and pos is not None
                               else 100),
                  "count": int(c)}
                 for (l, c), tot, pos in zip(languages, quants[::2],
                                             quants[1::2])]

    # Generate some stats for the event specific event types.
    [(pipe.hgetall(format_key("user:{0}:event:{1}:day".format(user, e))),
      pipe.hgetall(format_key("user:{0}:event:{1}:hour".format(user, e))))
     for e, c in event_counts]
    results = pipe.execute()
    events = [{"type": e[0],
               "total": int(e[1]),
               "week": map(int, make_histogram(w.items(), 7)),
               "day": map(int, make_histogram(d.items(), 24, offset))}
              for e, w, d in zip(event_counts, results[::2], results[1::2])]

    return {
        "total": total_events,
        "events": events,
        "day": map(int, daily_histogram),
        "week": map(int, weekly_histogram),
        "languages": languages,
    }


def get_comparison(user1, user2):
    # Normalize the usernames.
    user1, user2 = user1.lower(), user2.lower()

    # Grab the stats from the database.
    pipe = get_pipeline()
    pipe.zscore(format_key("user"), user1)
    pipe.zscore(format_key("user"), user2)
    pipe.zrevrange(format_key("user:{0}:event".format(user1)), 0, -1,
                   withscores=True)
    pipe.zrevrange(format_key("user:{0}:event".format(user2)), 0, -1,
                   withscores=True)
    pipe.zrevrange(format_key("user:{0}:lang".format(user1)), 0, -1,
                   withscores=True)
    pipe.zrevrange(format_key("user:{0}:lang".format(user2)), 0, -1,
                   withscores=True)
    pipe.hgetall(format_key("user:{0}:day".format(user1)))
    pipe.hgetall(format_key("user:{0}:day".format(user2)))
    raw = pipe.execute()

    # Get the total number of events.
    total1 = float(raw[0]) if raw[0] is not None else 0
    total2 = float(raw[1]) if raw[1] is not None else 0
    if not total1:
        return "is more active on GitHub"
    elif not total2:
        return "is less active on GitHub"

    # Load the event types from disk.
    with flask.current_app.open_resource("event_types.json") as f:
        evttypes = json.load(f)

    # Compare the fractional event types.
    evts1 = dict(raw[2])
    evts2 = dict(raw[3])
    diffs = []
    for e, desc in evttypes.iteritems():
        if e in evts1 and e in evts2:
            d = float(evts2[e]) / total2 / float(evts1[e]) * total1
            if d != 1:
                more = "more" if d > 1 else "less"
                if d > 1:
                    d = 1.0 / d
                diffs.append((desc.format(more=more, user=user2), d * d))

    # Compare language usage.
    langs1 = dict(raw[4])
    langs2 = dict(raw[5])
    for l in set(langs1.keys()) | set(langs2.keys()):
        n = float(langs1.get(l, 0)) / total1
        d = float(langs2.get(l, 0)) / total2
        if n != d and d > 0:
            if n > 0:
                d = d / n
            else:
                d = 1.0 / d
            more = "more" if d > 1 else "less"
            desc = "is {{more}} of a {0} aficionado".format(l)
            if d > 1:
                d = 1.0 / d
            diffs.append((desc.format(more=more), d * d))

    # Number of languages.
    nl1, nl2 = len(raw[4]), len(raw[5])
    if nl1 and nl2:
        desc = "speaks {more} languages"
        if nl1 > nl2:
            diffs.append((desc.format(more="fewer"),
                          nl2 * nl2 / nl1 / nl1))
        else:
            diffs.append((desc.format(user=user2, more="more"),
                          nl1 * nl1 / nl2 / nl2))

    # Compare the average weekly schedules.
    week1 = map(lambda v: int(v[1]), raw[6].iteritems())
    week2 = map(lambda v: int(v[1]), raw[7].iteritems())
    mu1, mu2 = sum(week1) / 7.0, sum(week2) / 7.0
    var1 = np.sqrt(sum(map(lambda v: (v - mu1) ** 2, week1)) / 7.0) / mu1
    var2 = np.sqrt(sum(map(lambda v: (v - mu2) ** 2, week2)) / 7.0) / mu2
    if var1 or var2 and var1 != var2:
        if var1 > var2:
            diffs.append(("has a more consistent weekly schedule", var2/var1))
        else:
            diffs.append(("has a less consistent weekly schedule", var1/var2))

    # Compute the relative probabilities of the comparisons and normalize.
    ps = map(lambda v: v[1], diffs)
    norm = sum(ps)

    # Choose a random description weighted by the probabilities.
    return np.random.choice([d[0] for d in diffs], p=[p / norm for p in ps])


def get_repo_info(username, reponame, maxusers=5, max_recommend=5):
    if _is_robot():
        return None

    # Normalize the repository name.
    repo = "{0}/{1}".format(username, reponame)
    rkey = format_key("social:repo:{0}".format(repo))
    recommend_key = format_key("social:recommend:{0}".format(repo))

    # Get the list of users.
    pipe = get_pipeline()
    pipe.exists(format_key("user:{0}:optout".format(username.lower())))
    pipe.exists(rkey)
    pipe.exists(recommend_key)
    pipe.zrevrange(recommend_key, 0, max_recommend-1)
    pipe.zrevrange(rkey, 0, maxusers-1, withscores=True)
    flag0, flag1, flag2, recommendations, users = pipe.execute()
    if flag0 or not flag1:
        return None

    if not flag2:
        # Compute the repository similarities.
        [pipe.zrevrange(format_key("social:user:{0}".format(u)), 0, -1)
         for u, count in users]
        repos = pipe.execute()
        [pipe.zincrby(recommend_key, r, 1) for l in repos for r in l
         if r != repo]
        pipe.expire(recommend_key, 172800)
        pipe.zrevrange(recommend_key, 0, max_recommend-1)
        recommendations = pipe.execute()[-1]

    # Get the contributor names.
    users = [(u, c) for u, c in users if int(c) > 1]
    [pipe.get(format_key("user:{0}:name".format(u))) for u, count in users]
    names = pipe.execute()

    return {
        "repository": repo,
        "recommendations": recommendations,
        "contributors": [{"username": u, "name": n.decode("utf-8")
                          if n is not None else u,
                          "count": int(count)}
                         for (u, count), n in zip(users, names)]
    }

########NEW FILE########
__FILENAME__ = timezone
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["estimate_timezone"]

import re
import flask
import logging
import requests

from .database import get_pipeline, format_key

tz_re = re.compile(r"<offset>([\-0-9]+)</offset>")
mqapi_url = "http://open.mapquestapi.com/geocoding/v1/address"
tzapi_url = "https://maps.googleapis.com/maps/api/timezone/json"
goapi_url = "https://maps.googleapis.com/maps/api/geocode/json"


def _google_geocode(location):
    # Check for quota limits.
    pipe = get_pipeline()
    usage_key = format_key("google_usage_limit")
    usage = pipe.get(usage_key).execute()[0]
    if usage is not None:
        logging.warn("Skipping Google geocode request for usage limits.")
        return None

    # Submit the request.
    params = dict(
        address=location,
        sensor="false",
        key=flask.current_app.config["GOOGLE_KEY"],
    )
    r = requests.get(goapi_url, params=params)
    if r.status_code != requests.codes.ok:
        logging.error(r.content)
        return None

    data = r.json()

    # Try not to go over usage limits.
    status = data.get("status", None)
    if status == "OVER_QUERY_LIMIT":
        pipe.set(usage_key, 1).expire(usage_key, 60*60)
        pipe.execute()
        return None

    # Parse the results.
    results = data.get("results", [])
    if not len(results):
        return None

    # Find the coordinates.
    loc = results[0].get("geometry", {}).get("location", None)
    return loc


def _mq_geocode(location):
    params = {"location": location, "thumbMaps": False, "maxResults": 1}
    r = requests.get(mqapi_url, params=params)
    if r.status_code != requests.codes.ok:
        return None

    # Parse the results.
    results = r.json().get("results", [])
    if not len(results):
        return None

    # Find the coordinates.
    locs = results[0].get("locations", {})
    if not len(locs):
        return None

    loc = locs[0].get("latLng", None)
    return loc


def geocode(location):
    if not len(location):
        return None

    # Try Google first.
    try:
        loc = _google_geocode(location)
    except Exception as e:
        logging.warn("Google geocoding failed with:\n{0}".format(e))
        loc = None

    # Fall back onto MapQuest.
    if loc is None:
        try:
            loc = _mq_geocode(location)
        except Exception as e:
            logging.warn("MQ geocoding failed with:\n{0}".format(e))
            loc = None

    return loc


def estimate_timezone(location):
    # Start by geocoding the location string.
    loc = geocode(location)
    if loc is None:
        logging.warn("Couldn't resolve location for {0}".format(location))
        return None

    # Resolve the timezone associated with these coordinates.
    params = dict(
        key=flask.current_app.config["GOOGLE_KEY"],
        location="{lat},{lng}".format(**loc),
        timestamp=0,
        sensor="false",
    )
    r = requests.get(tzapi_url, params=params)
    if r.status_code != requests.codes.ok:
        logging.error("Timezone zone request failed:\n{0}".format(r.url))
        return None

    result = r.json().get("rawOffset", None)
    if result is None:
        return None
    return int(result / (60*60))

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from osrc import create_app

if __name__ == "__main__":
    app = create_app("../local.py")
    app.debug = True
    app.run()

########NEW FILE########
__FILENAME__ = set_expire
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import logging
from itertools import imap
from osrc.database import get_pipeline, format_key

# The default time-to-live for every key.
DEFAULT_TTL = 2 * 7 * 24 * 60 * 60
TEMP_TTL = 24 * 60 * 60


def set_expire():
    pipe = get_pipeline()

    # Get the list of all keys.
    keys = pipe.keys().execute()[0]
    n = float(len(keys))
    print("Found {0:.0f} keys".format(n))

    # Loop over the keys and deal with each one.
    for i, key in enumerate(keys):
        # Skip the opt-out keys.
        if key.endswith(":optout"):
            continue

        # Deal with temporary keys.
        if any(imap(key.endswith, [":name", ":etag", ":gravatar", ":tz"])):
            pipe.expire(key, TEMP_TTL)
            continue

        # Everything else should get the default TTL.
        pipe.expire(key, DEFAULT_TTL)

        # Execute the updates in batches.
        if (i+1) % 5000 == 0:
            print("Finished {0} keys [{1:.2f} %]".format(i+1, (i+1)/n*100))
            pipe.execute()

    pipe.execute()


def del_connections():
    pipe = get_pipeline()

    # Get the list of all keys.
    keys = pipe.keys(format_key("social:connection:*")).execute()[0]
    n = float(len(keys))
    print("Found {0:.0f} keys".format(n))

    # Loop over the keys and deal with each one.
    for i, key in enumerate(keys):
        pipe.delete(key)

    pipe.execute()


if __name__ == "__main__":
    import argparse
    from osrc import create_app

    # Parse the command line arguments.
    parser = argparse.ArgumentParser(
        description="Add expiry dates to everything")
    parser.add_argument("--config", default=None,
                        help="The path to the local configuration file.")
    parser.add_argument("--log", default=None,
                        help="The path to the log file.")
    parser.add_argument("--connections", action="store_true",
                        help="Delete the connections?")
    args = parser.parse_args()

    largs = dict(level=logging.INFO,
                 format="[%(asctime)s] %(name)s:%(levelname)s:%(message)s")
    if args.log is not None:
        largs["filename"] = args.log
    logging.basicConfig(**largs)

    # Initialize a flask app.
    app = create_app(args.config)

    # Set up the app in a request context.
    with app.test_request_context():
        if args.connections:
            del_connections()
        else:
            set_expire()

########NEW FILE########
