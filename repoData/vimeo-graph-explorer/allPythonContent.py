__FILENAME__ = check_update_metric
#!/usr/bin/env python2
"""
this program shows how the proto1 -> proto2 upgrade looks like for
all metrics given as cmdline arguments.
very convenient to verify the working of plugins etc.
"""

import sys
from pprint import pprint
import logging

from graph_explorer import structured_metrics
from graph_explorer import config
from graph_explorer.log import make_logger

if len(sys.argv) < 3:
    print "check_update_metric.py <config file> <metric1> [<metric2> [<metric3...]]"
    sys.exit(1)

config.init(sys.argv[1])
config.valid_or_die()


logger = make_logger('check_update_metric', config)
logger.setLevel(logging.WARN)

s_metrics = structured_metrics.StructuredMetrics(config, logger)
errors = s_metrics.load_plugins()
if len(errors) > 0:
    print 'errors encountered while loading plugins:'
    for e in errors:
        print '\t%s' % e
for v in s_metrics.list_metrics(sys.argv[2:]).values():
    pprint(v)

########NEW FILE########
__FILENAME__ = process_alerting
#!/usr/bin/python2
from graph_explorer.alerting import msg_codes, Db, Result
from graph_explorer.alerting.emailoutput import EmailOutput
from graph_explorer import structured_metrics
from graph_explorer import config, preferences
import os
from argparse import ArgumentParser

app_dir = os.path.dirname(__file__)
if app_dir:
    os.chdir(app_dir)

parser = ArgumentParser(description="Process alerting rules")
parser.add_argument("configfile", metavar="CONFIG_FILENAME", type=str)
args = parser.parse_args()

config.init(args.configfile)
config.valid_or_die()


if not config.alerting:
    print "alerting disabled in config"
    os.exit(0)

s_metrics = structured_metrics.StructuredMetrics(config)
db = Db(config.alerting_db)
rules = db.get_rules()

output = EmailOutput(config)


def submit_maybe(result):
    if result.to_report():
        output.submit(result)
        db.save_notification(result)
        print "sent notification!"
    else:
        print "no notification"


for rule in rules:
    print " >>> ", rule.name()
    if not rule.active:
        print "inactive. skipping..."
        continue
    try:
        results, worst = rule.check_values(config, s_metrics, preferences)
    except Exception, e:
        result = Result(db, config, "Could not process your rule", 3, rule)
        result.body = ["Could not process your rule", str(e)]
        print result.log()
        submit_maybe(result)
        continue
    result = Result(db, config, "%s is %s" % (rule.name(), msg_codes[worst]), worst, rule)
    for (target, value, status) in results:
        line = " * %s value %s --> status %s" % (target, value, msg_codes[status])
        result.body.append(line)
    print result.log()
    submit_maybe(result)

########NEW FILE########
__FILENAME__ = run_graph_explorer
#!/usr/bin/env python2

import os
import sys
from argparse import ArgumentParser
from bottle import run, debug, PasteServer
from graph_explorer import config


def main():
    parser = ArgumentParser(description="Run Graph Explorer")
    parser.add_argument("configfile", metavar="CONFIG_FILENAME", type=str)
    parser.add_argument("--debug", type=bool)
    args = parser.parse_args()

    config.init(args.configfile)
    config.valid_or_die()

    # tmp disabled. breaks config loading
    #app_dir = os.path.dirname(__file__)
    #if app_dir:
    #    os.chdir(app_dir)

    debug(args.debug)
    run('graph_explorer.app',
        reloader=True,
        host=config.listen_host,
        port=config.listen_port,
        server=PasteServer)


if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
__FILENAME__ = update_metrics
#!/usr/bin/env python2
import os
import sys
from argparse import ArgumentParser

from graph_explorer import config
from graph_explorer.backend import Backend
from graph_explorer import structured_metrics
from graph_explorer.log import make_logger


def main():
    parser = ArgumentParser(description="Update Graph Explorer metrics")
    parser.add_argument("configfile", metavar="CONFIG_FILENAME", type=str)
    args = parser.parse_args()

    config.init(args.configfile)

    logger = make_logger('update_metrics', config)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    try:
        backend = Backend(config, logger)
        s_metrics = structured_metrics.StructuredMetrics(config, logger)
        errors = s_metrics.load_plugins()
        if len(errors) > 0:
            logger.warn('errors encountered while loading plugins:')
            for e in errors:
                print '\t%s' % e
        logger.info("fetching/saving metrics from graphite...")
        backend.download_metrics_json()
        logger.info("generating structured metrics data...")
        backend.update_data(s_metrics)
        logger.info("success!")
    except Exception, e:  # pylint: disable=W0703
        logger.error("sorry, something went wrong: %s", e)
        from traceback import print_exc
        print_exc()
        sys.exit(2)


if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
__FILENAME__ = emailoutput
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from graph_explorer.alerting import Output, get_png
from urlparse import urljoin


class EmailOutput(Output):
    def __init__(self, config):
        self.config = config

    def submit(self, result):
        manage_uri = urljoin(self.config.alerting_base_uri, "/rules/view/%d" % result.rule.Id)
        content = [
            """\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"/>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<title>%s</title><style type="text/css" >
            body {
                background-color: rgb(18, 20, 23);
                color: rgb(173, 175, 174);
            }
            a {
                text-decoration: none;
                color: rgb(51, 181, 229);
            }
            </style></head>""" % result.title,
            "<body>",
            "<center><b>%s</b></center>" % result.title,
            "<br/>val_warn: %f" % result.rule.val_warn,
            "<br/>val_crit: %f" % result.rule.val_crit,
            "<br/>Result:",
            "<br/>%s" % "\n<br/>".join(result.body),
            '<br/><img src="cid:graph.png" alt="graph" type="image/png" />',
            '<br/><a href="%s">Manage alert</a>' % manage_uri,
            "</body></html>"
        ]
        msg = MIMEMultipart()
        msg["To"] = result.rule.dest
        msg["From"] = self.config.alerting_from
        msg["Subject"] = result.title

        msgText = MIMEText("\n".join(content), 'html')
        msg.attach(msgText)
        targets = [target for (target, value, status) in result.rule.results]
        img = MIMEImage(get_png(targets, result.rule.val_warn, result.rule.val_crit, self.config, 400))
        img.add_header('Content-ID', '<graph.png>')

        msg.attach(img)

        s = smtplib.SMTP(self.config.alerting_smtp)
        dest = [to_addr.strip() for to_addr in result.rule.dest.split(',')]
        s.sendmail(self.config.alerting_from, dest, msg.as_string())
        s.quit()

########NEW FILE########
__FILENAME__ = app
#!/usr/bin/env python2
import bottle
from bottle import route, template, request, static_file, response, hook, BaseTemplate, post, redirect
import config
import preferences
from urlparse import urljoin
import structured_metrics
from graphs import Graphs
import graphs as g
from backend import Backend, make_config
from simple_match import filter_matching
from log import make_logger
from query import Query
from validation import RuleEditForm, RuleAddForm
import dashboards

import os
import traceback
from alerting import Db, rule_from_form


# contains all errors as key:(title,msg) items.
# will be used throughout the runtime to track all encountered errors
errors = {}

# will contain the latest data
last_update = None

config = make_config(config)

logger = make_logger('app', config)

logger.debug('app starting')
backend = Backend(config, logger)
s_metrics = structured_metrics.StructuredMetrics(config, logger)
graphs_manager = Graphs()
graphs_manager.load_plugins()
graphs_all = graphs_manager.list_graphs()

bottle.TEMPLATE_PATH.insert(0, os.path.dirname(__file__))


@route('<path:re:/assets/.*>')
@route('<path:re:/timeserieswidget/.*(js|css)>')
@route('<path:re:/timeserieswidget/timezone-js/src/.*js>')
@route('<path:re:/timeserieswidget/tz/.*>')
@route('<path:re:/DataTables/media/js/.*js>')
@route('<path:re:/DataTablesPlugins/integration/bootstrap/.*(js|css)>')
def static(path):
    return static_file(path, root=os.path.dirname(__file__))


@route('/', method='GET')
@route('/index', method='GET')
@route('/index/', method='GET')
@route('/index/<query:path>', method='GET')
def index(query=''):
    body = template('templates/body.index', errors=errors, query=query)
    return render_page(body)


@route('/dashboard/<dashboard_name>')
@route('/dashboard/<dashboard_name>/')
@route('/dashboard/<dashboard_name>/<apply_all_from_url>', method='GET')
def slash_dashboard(dashboard_name=None, apply_all_from_url=''):
    bottle.TEMPLATE_PATH.extend(dashboards.get_dirs(config))
    dashboard = template(dashboard_name, errors=errors, apply_all_from_url=apply_all_from_url)
    return render_page(dashboard)


def render_page(body, page='index'):
    dashboard_names = dashboards.list_dashboards(config)
    return unicode(template('templates/page', body=body, page=page, last_update=last_update, dashboards=dashboard_names))


@route('/meta')
def meta():
    body = template('templates/body.meta', todo=template('templates/' + 'todo'.upper()))
    return render_page(body, 'meta')


# accepts comma separated list of metric_id's
@route('/inspect/<metrics>')
def inspect_metric(metrics=''):
    metrics = map(s_metrics.load_metric, metrics.split(','))
    args = {'errors': errors,
            'metrics': metrics,
            }
    body = template('templates/body.inspect', args)
    return render_page(body, 'inspect')


@route('/api/<query:path>', method='GET')
def api(query=''):
    try:
        query = Query(query)
        (query, targets_matching) = s_metrics.matching(query)
    except Exception, e:  # pylint: disable=W0703
        return e

    tags = set()
    for target in targets_matching.values():
        for tag_name in target['tags'].keys():
            tags.add(tag_name)
    graphs_matching = filter_matching(query['ast'], graphs_all)
    graphs_matching = g.build(graphs_matching, query)
    stats = {'len_targets_all': s_metrics.count_metrics(),
             'len_graphs_all': len(graphs_all),
             'len_targets_matching': len(targets_matching),
             'len_graphs_matching': len(graphs_matching),
             }
    graphs = []
    targets_list = {}
    if query['statement'] in ('graph', 'lines', 'stack'):
        graphs_targets_matching = g.build_from_targets(targets_matching, query, preferences)[0]
        stats['len_graphs_targets_matching'] = len(graphs_targets_matching)
        graphs_matching.update(graphs_targets_matching)
        stats['len_graphs_matching_all'] = len(graphs_matching)
        for key in sorted(graphs_matching.iterkeys()):
            graphs.append((key, graphs_matching[key]))
    elif query['statement'] == 'list':
        # for now, only supports targets, not graphs
        targets_list = targets_matching
        stats['len_graphs_targets_matching'] = 0
        stats['len_graphs_matching_all'] = 0

    del query['target_modifiers']  # callback functions that are not serializable
    args = {'errors': errors,
            'query': query,
            'graphs': graphs,
            'targets_list': targets_list,
            'tags': list(tags),
            }
    args.update(stats)
    return args


@route('/graphs/', method='POST')
@route('/graphs/<query:path>', method='GET')  # used for manually testing
def graphs_nodeps(query=''):
    return handle_graphs(query, False)


@route('/graphs_deps/', method='POST')
@route('/graphs_deps/<query:path>', method='GET')  # used for manually testing
def graphs_deps(query=''):
    return handle_graphs(query, True)


def handle_graphs(query, deps):
    '''
    get all relevant graphs matching query,
    graphs from structured_metrics targets, as well as graphs
    defined in structured_metrics plugins
    '''
    if 'metrics_file' in errors:
        return template('templates/graphs', errors=errors)
    if not query:
        query = request.forms.get('query')
    if not query:
        return template('templates/graphs', query=query, errors=errors)

    return render_graphs(query, deps=deps)


@route('/render/<query>')
@route('/render/', method='POST')
@route('/render', method='POST')
def proxy_render(query=''):
    import urllib2
    url = urljoin(config.graphite_url_server, "/render/" + query)
    body = request.body.read()
    f = urllib2.urlopen(url, body)
    # this can be very verbose:
    # logger.debug("proxying graphite request: " + body)
    message = f.info()
    response.headers['Content-Type'] = message.gettype()
    return f.read()


@route('/graphs_minimal/<query:path>', method='GET')
def graphs_minimal(query=''):
    return handle_graphs_minimal(query, False)


@route('/graphs_minimal_deps/<query:path>', method='GET')
def graphs_minimal_deps(query=''):
    return handle_graphs_minimal(query, True)


@route('/rules')
@route('/rules/')
def rules_list():
    db = Db(config.alerting_db)
    if 'rules' in errors:
        del errors['rules']
    try:
        body = template('templates/body.rules', errors=errors, rules=db.get_rules())
    except Exception, e:
        errors['rules'] = ("Couldn't list rules: %s" % e, traceback.format_exc())
    if errors:
        body = template('templates/snippet.errors', errors=errors)
        return render_page(body)
    return render_page(body, 'rules')


@route('/rules/edit/<Id>')
@post('/rules/edit')
def rules_edit(Id=None):
    db = Db(config.alerting_db)
    if Id is not None:
        rule = db.get_rule(int(Id))
    else:
        rule = db.get_rule(int(request.forms['Id']))
    form = RuleEditForm(request.forms, rule)
    if request.method == 'POST' and form.validate():
        try:
            if 'rules_add' in errors:
                del errors['rules_add']
            form.populate_obj(rule)
            db = Db(config.alerting_db)
            db.edit_rule(rule)
        except Exception, e:  # pylint: disable=W0703
            errors["rules_add"] = ("Couldn't add rule: %s" % e, traceback.format_exc())
        return redirect('/rules')
    args = {'errors': errors,
            'form': form
            }
    body = template('templates/body.rules_edit', args)
    return render_page(body, 'rules_edit')


@route('/rules/add')
@route('/rules/add/')
@route('/rules/add/<expr>')
@post('/rules/add')
def rules_add(expr=''):
    form = RuleAddForm(request.forms)
    if request.method == 'GET':
        form.expr.data = expr
    if request.method == 'POST' and form.validate():
        try:
            if 'rules_add' in errors:
                del errors['rules_add']
            rule = rule_from_form(form)
            db = Db(config.alerting_db)
            db.add_rule(rule)
        except Exception, e:  # pylint: disable=W0703
            errors["rules_add"] = ("Couldn't add rule: %s" % e, traceback.format_exc())
        return redirect('/rules')
    args = {'errors': errors,
            'form': form
            }
    body = template('templates/body.rules_add', args)
    return render_page(body, 'rules_add')


@route('/rules/view/<Id>')
def rules_view(Id):
    db = Db(config.alerting_db)
    rule = db.get_rule(int(Id))
    body = template('templates/body.rule', errors=errors, rule=rule)
    return render_page(body)


@route('/rules/delete/<Id>')
def rules_delete(Id):
    db = Db(config.alerting_db)
    try:
        db.delete_rule(int(Id))
    except Exception, e:  # pylint: disable=W0703
        errors["rules_delete"] = ("Couldn't delete rule: %s" % e, traceback.format_exc())
    if errors:
        body = template('templates/snippet.errors', errors=errors)
        return render_page(body)
    return redirect('/rules')


@hook('before_request')
def seedviews():
    # templates need to know the relative path to get resources from
    root = '../' * request.path.count('/')
    BaseTemplate.defaults['root'] = root
    BaseTemplate.defaults['config'] = config
    BaseTemplate.defaults['preferences'] = preferences


def handle_graphs_minimal(query, deps):
    '''
    like handle_graphs(), but without extra decoration, so can be used on
    dashboards
    TODO dashboard should show any errors
    '''
    if not query:
        return template('templates/graphs', query=query, errors=errors)
    return render_graphs(query, minimal=True, deps=deps)


def render_graphs(query, minimal=False, deps=False):
    if "query_parse" in errors:
        del errors["query_parse"]
    try:
        query = Query(query)
    except Exception, e:  # pylint: disable=W0703
        errors["query_parse"] = ("Couldn't parse query: %s" % e, traceback.format_exc())
    if errors:
        body = template('templates/snippet.errors', errors=errors)
        return render_page(body)

    # TODO: something goes wrong here.
    # if you do a query that will give an ES error (say 'foo(')
    # and then fix the query and hit enter, this code will see the new query
    # and ES will process the query fine, but for some reason the old error
    # doesn't clear and sticks instead.

    if "match_metrics" in errors:
        del errors["match_metrics"]
    try:
        (query, targets_matching) = s_metrics.matching(query)
        # presentation overrides. useful to make screenshots etc with
        # specific query settings not visible in the UI
        # query['from'] = "-3weeks"
        # query['to'] = "-2weeks"
    except Exception, e:  # pylint: disable=W0703
        errors["match_metrics"] = ("Couldn't find matching metrics: %s" % e, traceback.format_exc())
    if errors:
        body = template('templates/snippet.errors', errors=errors)
        return render_page(body)

    tags = set()
    for target in targets_matching.values():
        for tag_name in target['tags'].keys():
            tags.add(tag_name)
    graphs_matching = filter_matching(query['ast'], graphs_all)
    graphs_matching = g.build(graphs_matching, query)
    stats = {'len_targets_all': s_metrics.count_metrics(),
             'len_graphs_all': len(graphs_all),
             'len_targets_matching': len(targets_matching),
             'len_graphs_matching': len(graphs_matching),
             }
    out = ''
    graphs = []
    targets_list = {}
    # the code to handle different statements, and the view
    # templates could be a bit prettier, but for now it'll do.
    if query['statement'] in ('graph', 'lines', 'stack'):
        graphs_targets_matching = g.build_from_targets(targets_matching, query, preferences)[0]
        stats['len_graphs_targets_matching'] = len(graphs_targets_matching)
        graphs_matching.update(graphs_targets_matching)
        stats['len_graphs_matching_all'] = len(graphs_matching)
        if len(graphs_matching) > 0 and deps:
            out += template('templates/snippet.graph-deps')
        for key in sorted(graphs_matching.iterkeys()):
            graphs.append((key, graphs_matching[key]))
    elif query['statement'] == 'list':
        # for now, only supports targets, not graphs
        targets_list = targets_matching
        stats['len_graphs_targets_matching'] = 0
        stats['len_graphs_matching_all'] = 0

    args = {'errors': errors,
            'query': query,
            'graphs': graphs,
            'targets_list': targets_list,
            'tags': tags,
            }
    args.update(stats)
    if minimal:
        out += template('templates/graphs_minimal', args)
    else:
        out += template('templates/graphs', args)
    return out


# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = backend
#!/usr/bin/env python2
import json
import os
import logging
import urllib2
from urlparse import urljoin


class MetricsError(Exception):
    def __init__(self, msg, underlying_error):
        Exception.__init__(self, msg, underlying_error)
        self.msg = str(msg)
        self.underlying_error = str(underlying_error)

    def __str__(self):
        return "%s (%s)" % (self.msg, self.underlying_error)


class Backend(object):
    def __init__(self, config, logger=logging):
        self.config = config
        self.logger = logger

    def download_metrics_json(self):
        url = urljoin(self.config.graphite_url_server, "metrics/index.json")
        if self.config.graphite_username is not None and self.config.graphite_password is not None:
            username = self.config.graphite_username
            password = self.config.graphite_password
            passmanager = urllib2.HTTPPasswordMgrWithDefaultRealm()
            passmanager.add_password(None, url, username, password)
            authhandler = urllib2.HTTPBasicAuthHandler(passmanager)
            opener = urllib2.build_opener(authhandler)
            urllib2.install_opener(opener)

        response = urllib2.urlopen(url)

        with open('%s.tmp' % self.config.filename_metrics, 'w') as m:
            m.write(response.read())
        try:
            os.unlink(self.config.filename_metrics)
        except OSError:
            pass
        os.rename('%s.tmp' % self.config.filename_metrics, self.config.filename_metrics)

    def load_metrics(self):
        try:
            with open(self.config.filename_metrics, 'r') as f:
                metrics = json.load(f)
            # workaround for graphite bug where metrics can have leading dots
            # has been fixed (https://github.com/graphite-project/graphite-web/pull/293)
            # but older graphite versions still do it
            if len(metrics) and metrics[0][0] == '.':
                metrics = [m.lstrip('.') for m in metrics]
            return metrics
        except IOError, e:
            raise MetricsError("Can't load metrics file", e)
        except ValueError, e:
            raise MetricsError("Can't parse metrics file", e)

    def stat_metrics(self):
        try:
            return os.stat(self.config.filename_metrics)
        except OSError, e:
            raise MetricsError("Can't load metrics file", e)

    def update_data(self, s_metrics):
        self.logger.debug("loading metrics")
        metrics = self.load_metrics()

        self.logger.debug("removing outdated targets")
        s_metrics.remove_metrics_not_in(metrics)

        self.logger.debug("updating targets")
        s_metrics.update_targets(metrics)


def make_config(config):
    # backwards compat.
    if hasattr(config, 'graphite_url'):
        if not hasattr(config, 'graphite_url_server'):
            config.graphite_url_server = config.graphite_url
        if not hasattr(config, 'graphite_url_client'):
            config.graphite_url_client = config.graphite_url
    return config


def get_action_on_rules_match(rules, subject):
    '''
    rules being a a list of tuples, and each tuple having 2 elements, like:
    {'plugin': ['diskspace', 'memory'], 'unit': 'B'},
    action

    the dict is a list of conditions that must match (and). if the value is an iterable, those count as OR
    action can be whatever you want. the actions for all matching rules are yielded.
    '''
    for (match_rules, action) in rules:
        rule_match = True
        for (tag_k, tag_v) in match_rules.items():
            if tag_k not in subject:
                rule_match = False
                break
            if isinstance(tag_v, basestring):
                if subject[tag_k] != tag_v:
                    rule_match = False
                    break
            else:
                # tag_v is a list -> OR of multiple allowed options
                tag_match = False
                for option in tag_v:
                    if subject[tag_k] == option:
                        tag_match = True
                if not tag_match:
                    rule_match = False
                    break
        if rule_match:
            yield action

# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = colors
# some colors (light and dark version)
# better would be to compute colors, gradients and lighter/darker versions as needed
colors = {
    'blue': ('#5C9DFF', '#0000B2'),
    'yellow': ('#FFFFB2', '#FFFF00'),
    'green': ('#80CC80', '#009900'),
    'brown': ('#694C2E', '#A59482'),
    'red': ('#FF5C33', '#B24024'),
    'purple': ('#FF94FF', '#995999'),
    'turq': ('#75ACAC', '#197575'),
    'orange': ('#FFC266', '#FF9900'),
    'white': '#FFFFFF',
    'black': '#000000'
}


# from http://chase-seibert.github.io/blog/2011/07/29/python-calculate-lighterdarker-rgb-colors.html
# + fix from 2nd comment cause it was a little broken otherwise
def color_variant(hex_color, brightness_offset=1):
    """ takes a color like #87c95f and produces a lighter or darker variant """
    if len(hex_color) != 7:
        raise Exception("Passed %s into color_variant(), needs to be in #87c95f format." % hex_color)
    rgb_hex = [hex_color[x:x + 2] for x in [1, 3, 5]]
    new_rgb_int = [int(hex_value, 16) + brightness_offset for hex_value in rgb_hex]
    new_rgb_int = [min([255, max([0, i])]) for i in new_rgb_int]  # make sure new values are between 0 and 255
    # hex() produces "0x88", we want just "88"
    #return "#" + "".join([hex(i)[2:] for i in new_rgb_int])
    return "#%02x%02x%02x" % tuple(new_rgb_int)

########NEW FILE########
__FILENAME__ = config
import sys
from ConfigParser import SafeConfigParser, NoOptionError, NoSectionError
from graph_explorer.validation import ConfigValidator


class DummyConfigParser(object):
    def __getattr__(self, name):
        raise Exception("Configuration not initialised")


parser = DummyConfigParser()
file_name = ""


def init(filename):
    global parser, config, file_name
    file_name = filename
    parser = SafeConfigParser()
    parser.read([filename])

    # This is for backward-compatability. Code should probably be changed to get values
    # from the ConfigParser object directly.
    # no this is because we want to be able to validate the whole thing
    config = sys.modules[__name__]

    # no config parser allows for a value not to exist, will always raise exception
    # but we want to be able to validate later and show all bad and missing values.
    def get(section, option):
        try:
            return parser.get(section, option)
        except (NoOptionError, NoSectionError):
            pass
        return None

    def getlist(section, option):
        try:
            list_str = parser.get(section, option)
            return list_str.splitlines()
        except (NoOptionError, NoSectionError):
            pass
        return None

    def getint(section, option):
        try:
            return parser.getint(section, option)
        except (NoOptionError, NoSectionError):
            pass
        return None

    def getboolean(section, option):
        try:
            return parser.getboolean(section, option)
        except (NoOptionError, NoSectionError):
            pass
        return None

    config.listen_host = get("graph_explorer", "listen_host")
    config.listen_port = getint("graph_explorer", "listen_port")
    config.filename_metrics = get("graph_explorer", "filename_metrics")
    config.log_file = get("graph_explorer", "log_file")

    config.graphite_url_server = get("graphite", "url_server")
    config.graphite_url_client = get("graphite", "url_client")
    config.graphite_username = get("graphite", "username") or None
    config.graphite_password = get("graphite", "password") or None

    config.anthracite_host = get("anthracite", "host") or None
    config.anthracite_port = getint("anthracite", "port") or 9200
    config.anthracite_index = get("anthracite", "index") or None
    config.anthracite_add_url = get("anthracite", "add_url") or None

    config.locations_plugins_structured_metrics = getlist("locations", "plugins_structured_metrics")
    config.locations_dashboards = getlist("locations", "dashboards")

    config.es_host = get("elasticsearch", "host")
    config.es_port = getint("elasticsearch", "port")
    config.es_index = get("elasticsearch", "index")
    config.limit_es_metrics = getint("elasticsearch", "limit_es_metrics")
    config.process_native_proto2 = getboolean("elasticsearch", "process_native_proto2")

    config.alerting = getboolean("alerting", "alerting")
    config.alerting_db = get("alerting", "db")
    config.alerting_smtp = get("alerting", "smtp")
    config.alerting_from = get("alerting", "from")
    config.alert_backoff = getint("alerting", "backoff")
    config.alerting_base_uri = get("alerting", "base_uri")

    config.collectd_StoreRates = getboolean("collectd", "StoreRates")
    config.collectd_prefix = get("collectd", "prefix")


def valid_or_die():
    global config, file_name
    config = sys.modules[__name__]
    c = ConfigValidator(obj=config)
    if c.validate():
        return
    print "Configuration errors (%s):" % file_name
    for (key, err) in c.errors.items():
        print key,
        for e in err:
            print "\n    %s" % e
    sys.exit(1)

########NEW FILE########
__FILENAME__ = convert
prefixes_SI = {
    'y': 1e-24,  # yocto
    'z': 1e-21,  # zepto
    'a': 1e-18,  # atto
    'f': 1e-15,  # femto
    'p': 1e-12,  # pico
    'n': 1e-9,   # nano
    'u': 1e-6,   # micro
    'm': 1e-3,   # mili
    'c': 1e-2,   # centi
    'd': 1e-1,   # deci
    'k': 1e3,    # kilo
    'M': 1e6,    # mega
    'G': 1e9,    # giga
    'T': 1e12,   # tera
    'P': 1e15,   # peta
    'E': 1e18,   # exa
    'Z': 1e21,   # zetta
    'Y': 1e24,   # yotta
}
prefixes_IEC = {
    'Ki': 1024,
    'Mi': 1024**2,
    'Gi': 1024**3,
    'Ti': 1024**4
}

def parse_str(string):
    try:
        return float(string)
    except ValueError:
        prefixes = dict(prefixes_SI.items() + prefixes_IEC.items())
        for prefix, val in prefixes.items():
            if string.endswith(prefix):
                return float(string.replace(prefix, '')) * val
    raise Exception("I didn't understand '%s'" % string)


########NEW FILE########
__FILENAME__ = dashboards
import os
import glob


def get_dirs(config):
    dirs = []
    for entry in config.locations_dashboards:
        if entry == '**builtins**':
            entry = os.path.join(os.path.dirname(__file__), 'templates/dashboards')
        dirs.append(entry)
    return dirs


def list_dashboards(config):
    dashboards = []

    for entry in get_dirs(config):
        tpl_list = glob.glob(os.path.join(entry, '*.tpl'))
        dashboards.extend(map(lambda tpl: os.path.basename(tpl)[:-4], tpl_list))
    return sorted(dashboards)

########NEW FILE########
__FILENAME__ = log
import logging

f = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def make_logger(logger_name, config):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    chandler = logging.StreamHandler()
    chandler.setFormatter(f)
    logger.addHandler(chandler)

    if config.log_file:
        fhandler = logging.FileHandler(config.log_file)
        fhandler.setFormatter(f)
        logger.addHandler(fhandler)
    return logger

########NEW FILE########
__FILENAME__ = preferences
count_interval = 60  # counts are in buckets of <size>s seconds; i.e. statsd flushInterval
timezone = "America/New_York"

from preferences_color import apply_colors
# match on graph properties (after targets are matched and graph is built)
# and apply options accordingly.
# if options is a dict, merge it into the graph. if it's a function, the graph
# gets passed and the return value is used as new graph definition.
# all tags must match, if multiple tags are given in a list, they are OR'ed
# multiple matches can occur, they are performed in order.
graph_options = [
    [
        {'where': 'system_memory', 'unit': 'B'},  # match
        {'state': 'stacked', 'suffixes': 'binary'}  # set option
    ],
    [
        {'plugin': 'diskspace', 'unit': 'B'},
        {'state': 'stacked', 'suffixes': 'binary'}
    ],
    [
        {'what': 'cpu_usage'},
        {'state': 'stacked'}
    ],
    [
        {'unit': ['freq_rel', 'freq_abs']},
        {'state': 'stacked'}
    ],
    [
        {'unit': 'P'},  # probabilities between 0 and 1
        {'yaxis': {'max': 1}}
    ],
    [
        {},
        apply_colors
    ]
]

########NEW FILE########
__FILENAME__ = preferences_color
from colors import colors
from backend import get_action_on_rules_match


# convenience functions


def get_unique_tag_value(graph, target, tag):
    '''
    get a tag corresponding to a target, if it's clear the target "owns" the tag.
    this makes sure, if you're looking at cpu graphs with group by server,
    each cpu type (user, idle, etc) has a representative color
    but if you group by type (and compare servers on one graph for e.g. 'idle') you don't want
    all targets to have the same color... except if due to filtering only 1 server shows up, we
    can apply the color again.
    note that if the graph has 6 targets: 3 different servers, each 2 different types, then this
    will proceed and you'll see 3 targets of each color.
    this could be extended to search for the value in the variables of all other targets, to guarantee
    uniqueness (and avoid a color showing up multiple times)
    TLDR: color a target based on tag value, but avoid all targets having the same color on 1 graph
    '''
    # the graph has other targets that have different values for this tag
    if tag in target['variables']:
        t = target['variables'][tag]
    elif len(graph['targets']) == 1:
        # there's no other targets in the graph, maybe due to a filter.
        # so we can safely get the value from [promoted] constants
        if tag in graph['constants']:
            t = graph['constants'][tag]
        elif tag in graph['promoted_constants']:
            t = graph['promoted_constants'][tag]
        else:
            return None
    else:
        return None

    # t can be a tuple if it's an aggregated tag
    if isinstance(t, basestring):
        return t
    else:
        return t[0]


def get_tag_value(graph, target, tag):
    '''
    get a tag, if it applies to the target.  irrespective of other targets
    i.e. color a target based on tag value, and don't try to avoid multiple targets with same color
    on 1 graph.
    '''
    if tag in target['variables']:
        t = target['variables'][tag]
    elif tag in graph['constants']:
        t = graph['constants'][tag]
    elif tag in graph['promoted_constants']:
        t = graph['promoted_constants'][tag]
    else:
        return None
    if isinstance(t, basestring):
        return t
    else:
        return t[0]


def bin_set_color(graph, target):
    if 'bin_upper' not in target['tags']:
        return
    # later we could do a real green-to-red interpolation by looking at
    # the total range (all bin_uppers in the entire class) and computing
    # a color, maybe using something like color_variant("#FF0000", -150),
    # for now, this will have to do
    bin_upper = target['tags']['bin_upper']
    colormap = {
        '0.01': '#2FFF00',
        '0.05': '#64DD0E',
        '0.1': '#9CDD0E',
        '0.5': '#DDCC0E',
        '1': '#DDB70E',
        '5': '#FF6200',
        '10': '#FF3C00',
        '50': '#FF1E00',
        'inf': '#FF0000'
    }
    if bin_upper in colormap:
        target['color'] = colormap[bin_upper]


def apply_colors(graph):
    '''
    update target colors in a clever, dynamic way. basically it's about defining
    colors for certain metrics (such as cpu idle metric = green), but since you
    can group by arbitrary things, you might have a graph comparing the idle
    values for different servers, in which case they should not be all green.

    # the graph will look something like:
        {
            'promoted_constants': {'type': 'update_time', 'plugin': 'carbon'},
            'from': '-24hours',
            'until': 'now',
            'constants': {'unit': 'ms', 'target_type': 'gauge'},
            'targets': [
                {
                    'id': u'carbon.agents.dfvimeographite2-a.avgUpdateTime',
                    'variables': {'agent': u'dfvimeographite2-a'},
                    'target': u'carbon.agents.dfvimeographite2-a.avgUpdateTime'
                },
                (...)
            ]
        }
    '''

    # color targets based on tags, even when due to grouping metrics with the same tags (colors)
    # show up on the same graph
    rules_tags = [
        [
            {'stat': ['upper', 'upper_90']},
            {
                'http_method': {
                    'GET': colors['blue'][1],
                    'HEAD': colors['yellow'][1],
                    'PUT': colors['green'][1],
                    'REPLICATE': colors['brown'][1],
                    'DELETE': colors['red'][1]
                }
            }
        ],
    ]

    # color targets based on tags, except when due to grouping metrics
    # with the same tags show up on the same graph
    rules_unique_tags = [
        # http stuff, for swift and others
        [
            {},
            {
                'http_method': {
                    'GET': colors['blue'][0],
                    'HEAD': colors['yellow'][0],
                    'PUT': colors['green'][0],
                    'REPLICATE': colors['brown'][0],
                    'DELETE': colors['red'][0]
                }
            }
        ],
        [
            {'what': 'cpu_usage'},
            {
                'type': {
                    'idle': colors['green'][0],
                    'user': colors['blue'][0],
                    'system': colors['blue'][1],
                    'nice': colors['purple'][0],
                    'softirq': colors['red'][0],
                    'irq': colors['red'][1],
                    'iowait': colors['orange'][0],
                    'guest': colors['white'],
                    'guest_nice': colors['white'],
                    'steal': '#FFA791'  # brighter red
                }
            }
        ],
        [
            {},
            {
                'mountpoint': {
                    '_var': colors['red'][0],
                    '_lib': colors['orange'][1],
                    '_boot': colors['blue'][0],
                    '_tmp': colors['purple'][0],
                    'root': colors['green'][0]
                }
            }
        ],
        [
            {'plugin': 'load'},
            {
                'type': {
                    '01': colors['red'][1],
                    '05': colors['red'][0],
                    '15': '#FFA791'  # brighter red
                }
            }
        ],
        [
            {'unit': 'ms'},
            {
                'type': {
                    'update_time': colors['turq'][0]
                }
            }
        ],
        [
            {'unit': 'freq_abs'},
            bin_set_color
        ]
    ]

    for target in graph['targets']:
        tags = dict(graph['constants'].items() + graph['promoted_constants'].items() + target['variables'].items())

        for action in get_action_on_rules_match(rules_unique_tags, tags):
            if callable(action):  # hasattr(action, '__call__'):
                action(graph, target)
            else:
                for (tag_key, matches) in action.items():
                    t = get_unique_tag_value(graph, target, tag_key)
                    if t is not None and t in matches:
                        target['color'] = matches[t]

        for action in get_action_on_rules_match(rules_tags, target):
            for (tag_key, matches) in action.items():
                t = get_tag_value(graph, target, tag_key)
                if t is not None and t in matches:
                    target['color'] = matches[t]

    return graph

########NEW FILE########
__FILENAME__ = query
import re
import convert
import copy
import unitconv
import warnings

# note, consider "query" in the broad sense.  it is used for user input, as
# well as the blueprint config for graphs, i.e. "spec"


class Query(dict):
    default = {
        'statement': 'graph',
        'patterns': [],
        'group_by': {'target_type=': [''], 'unit=': [''], 'server': ['']},
        'sum_by': {},
        'avg_by': {},
        'avg_over': None,
        'min': None,
        'max': None,
        'from': '-24hours',
        'to': 'now',
        'limit_targets': 500,
        'events_query': '*',
        'target_modifiers': []
    }

    def __init__(self, query_str):
        dict.__init__(self)
        tmp = copy.deepcopy(Query.default)
        self.update(tmp)
        self.parse(query_str)
        self.prepare()
        self['ast'] = self.build_ast(self['patterns'])
        self.allow_compatible_units()

    def parse(self, query_str):
        avg_over_match = '^([0-9]*)(s|M|h|d|w|mo)$'

        # for a call like ('foo bar baz quux', 'bar ', 'baz', 'def')
        # returns ('foo quux', 'baz') or the original query and the default val if no match
        def parse_val(query_str, predicate_match, value_match, value_default=None):
            match = re.search('\\b(%s%s)' % (predicate_match, value_match), query_str)
            value = value_default
            if match and match.groups() > 0:
                value = match.groups(1)[0].replace(predicate_match, '')
                query_str = query_str[:match.start(1)] + query_str[match.end(1):]
            return (query_str, value)

        if '||' in query_str:
            (query_str, _, self['events_query']) = query_str.partition('||')

        (query_str, self['statement']) = parse_val(query_str, '^', '(graph|list|stack|lines)\\b',
                                                   self['statement'])
        self['statement'] = self['statement'].rstrip()

        (query_str, self['to']) = parse_val(query_str, 'to ', '[^ ]+', self['to'])
        (query_str, self['from']) = parse_val(query_str, 'from ', '[^ ]+', self['from'])

        (query_str, group_by_str) = parse_val(query_str, 'GROUP BY ', '[^ ]+')
        (query_str, extra_group_by_str) = parse_val(query_str, 'group by ', '[^ ]+')
        (query_str, sum_by_str) = parse_val(query_str, 'sum by ', '[^ ]+')
        (query_str, avg_by_str) = parse_val(query_str, 'avg by ', '[^ ]+')
        (query_str, avg_over_str) = parse_val(query_str, 'avg over ', '[^ ]+')
        (query_str, min_str) = parse_val(query_str, 'min ', '[^ ]+')
        (query_str, max_str) = parse_val(query_str, 'max ', '[^ ]+')
        explicit_group_by = {}
        if group_by_str is not None:
            explicit_group_by = Query.build_buckets(group_by_str)
            self['group_by'] = explicit_group_by
        elif extra_group_by_str is not None:
            for k in self['group_by'].keys():
                if not k.endswith('='):
                    del self['group_by'][k]
            explicit_group_by = Query.build_buckets(extra_group_by_str)
            self['group_by'].update(explicit_group_by)
        if sum_by_str is not None:
            self['sum_by'] = Query.build_buckets(sum_by_str)
        if avg_by_str is not None:
            self['avg_by'] = Query.build_buckets(avg_by_str)
        if min_str is not None:
            # check if we can parse the values, but don't actually replace yet
            # because we want to keep the 'pretty' value for now so we can display
            # it in the query details section
            convert.parse_str(min_str)
            self['min'] = min_str
        if max_str is not None:
            convert.parse_str(max_str)
            self['max'] = max_str

        # if you specified a tag in avg_by or sum_by that is included in the
        # default group_by (and you didn't explicitly ask to group by that tag), we
        # remove it from group by, so that the avg/sum can work properly.
        for tag in self['sum_by'].keys() + self['avg_by'].keys():
            for tag_check in (tag, "%s=" % tag):
                if tag_check in self['group_by'] and tag_check not in explicit_group_by.keys():
                    del self['group_by'][tag_check]

        # doing this sanity check would now be tricky: basically you can have the same keys in more than 1 of sum/avg/group by,
        # it now depends on the bucket configuration.  since i can't wrap my head around it anymore, let's just leave it be for now.
        # it's up to people to construct sane queries, and if they do a stupid query, then at least GE shouldn't crash or anything.
        # sum_individual_keys = len(self['group_by']) + len(self['sum_by']) + len(self['avg_by'])
        # sum_unique_keys = len(set(self['group_by'].keys() + self['sum_by'].keys() + self['avg_by'].keys()))
        # if sum_individual_keys != sum_unique_keys:
        #     raise Exception("'group by' (%s), 'sum by (%s)' and 'avg by (%s)' "
        #                     "cannot list the same tag keys" %
        #                     (', '.join(self['group_by'].keys()),
        #                      ', '.join(self['sum_by'].keys()),
        #                      ', '.join(self['avg_by'].keys())))

        if avg_over_str is not None:
            # avg_over_str should be something like 'h', '10M', etc
            avg_over = re.match(avg_over_match, avg_over_str)
            if avg_over is not None:  # if None, that's an invalid request. ignore it. TODO error to user
                avg_over = avg_over.groups()
                self['avg_over'] = (int(avg_over[0]), avg_over[1])

        (query_str, self['limit_targets']) = parse_val(query_str, 'limit ', '[^ ]+', self['limit_targets'])
        self['limit_targets'] = int(self['limit_targets'])

        # split query_str into multiple patterns which are all matched independently
        # this allows you write patterns in any order, and also makes it easy to use negations
        self['patterns'] += query_str.split()

    # process the syntactic sugar
    def prepare(self):
        # we want to put these ones in front of the patterns list
        new_patterns = []
        for (tag, cfg) in self['group_by'].items():
            if tag.endswith('='):
                # add the pattern for the strong tag
                new_patterns.append(tag)
                # remove it from the struct so that from here on we have a consistent format
                # a spec coming from group by can be like 'foo=', 'foo=,bar', or 'foo=:bucket1,bar'
                self['group_by'][tag[:-1]] = cfg
                del self['group_by'][tag]
        new_patterns.extend(self['patterns'])
        self['patterns'] = new_patterns

    @staticmethod
    def apply_graphite_function_to_target(target, funcname, *args):
        def format_arg(arg):
            if isinstance(arg, basestring):
                return '"%s"' % arg
            return str(arg)
        target['target'] = "%s(%s)" % (funcname, ','.join([target['target']] + map(format_arg, args)))

    @classmethod
    def graphite_function_applier(cls, funcname, *args):
        def apply_graphite_function(target, _graph_config):
            cls.apply_graphite_function_to_target(target, funcname, *args)
        return apply_graphite_function

    @staticmethod
    def variable_applier(**tags):
        def apply_variables(target, graph_config):
            for new_k, new_v in tags.items():
                if new_k in graph_config['constants']:
                    graph_config['constants'][new_k] = new_v
                else:
                    target['variables'][new_k] = new_v
        return apply_variables

    @staticmethod
    def graph_config_applier(**configs):
        def apply_graph_config(_target, graph_config):
            graph_config.update(configs)
        return apply_graph_config

    @classmethod
    def convert_to_requested_unit_applier(cls, compatibles):
        def apply_requested_unit(target, _graph_config):
            tags = target['tags']
            try:
                scale, extra_op = compatibles[tags['unit']]
            except (KeyError, ValueError):
                # this probably means ES didn't respect the query we made,
                # or we didn't make it properly, or something? issue a warning
                # but let things go on
                warnings.warn("Found a target with unit %r which wasn't in our "
                              "list of compatible units (%r) for this query."
                              % (tags.get('unit'), compatibles.keys()),
                              RuntimeWarning)
                return
            if extra_op == 'derive':
                cls.apply_derivative_to_target(target, scale)
            else:
                if scale != 1.0:
                    cls.apply_graphite_function_to_target(target, 'scale', scale)
                if extra_op == 'integrate':
                    # graphite assumes that anything you integrate is per minute.
                    # hitcount assumes that incoming data is per second.
                    cls.apply_graphite_function_to_target(target, 'hitcount', '1min')
                    cls.apply_graphite_function_to_target(target, 'integral')
        return apply_requested_unit

    @classmethod
    def derive_counters(cls, target, _graph_config):
        if target['tags'].get('target_type') == 'counter':
            cls.apply_derivative_to_target(target, known_non_negative=True)

    @classmethod
    def apply_derivative_to_target(cls, target, scale=1, known_non_negative=False):
        wraparound = target['tags'].get('wraparound')
        if wraparound is not None:
            cls.apply_graphite_function_to_target(target, 'nonNegativeDerivative', int(wraparound))
        elif known_non_negative:
            cls.apply_graphite_function_to_target(target, 'nonNegativeDerivative')
        else:
            cls.apply_graphite_function_to_target(target, 'derivative')
        cls.apply_graphite_function_to_target(target, 'scaleToSeconds', scale)

    def allow_compatible_units(self):
        newpat, mods = self.transform_ast_for_compatible_units(self['ast'])
        if not mods:
            # no explicit unit requested; default is to apply derivative to
            # targets with target_type=counter, and leave others alone
            mods = [self.derive_counters]
        self['ast'] = newpat
        self['target_modifiers'].extend(mods)

    @classmethod
    def transform_ast_for_compatible_units(cls, ast):
        if ast[0] == 'match_tag_equality' and ast[1] == 'unit':
            requested_unit = ast[2]
            unitinfo = unitconv.parse_unitname(requested_unit, fold_scale_prefix=False)
            prefixclass = unitconv.prefix_class_for(unitinfo['scale_multiplier'])
            use_unit = unitinfo['base_unit']
            compatibles = unitconv.determine_compatible_units(**unitinfo)

            # rewrite the search term to include all the alternates
            ast = ('match_or',) + tuple(
                [('match_tag_equality', 'unit', u) for u in compatibles.keys()])

            modifiers = [
                cls.convert_to_requested_unit_applier(compatibles),
                cls.variable_applier(unit=use_unit)
            ]
            if prefixclass == 'binary':
                modifiers.append(cls.graph_config_applier(suffixes=prefixclass))
            return ast, modifiers
        elif ast[0] in ('match_and', 'match_or'):
            # recurse into subexpressions, in case they have unit=* terms
            # underneath. this won't be totally correct in case there's a way
            # to have multiple "unit=*" terms inside varying structures of
            # 'and' and 'or', but that's not exposed to the user yet anyway,
            # and auto-unit-conversion in that case probably isn't worth
            # supporting.
            new_target_modifiers = []
            newargs = []
            for sub_ast in ast[1:]:
                if isinstance(sub_ast, tuple):
                    sub_ast, mods = cls.transform_ast_for_compatible_units(sub_ast)
                    new_target_modifiers.extend(mods)
                newargs.append(sub_ast)
            ast = (ast[0],) + tuple(newargs)
            return ast, new_target_modifiers
        return ast, []

    query_pattern_re = re.compile(r'''
        # this should accept any string
        ^
        (?P<negate> ! )?
        (?P<key> [^=:]* )
        (?:
            (?P<operation> [=:] )
            (?P<term> .* )
        )?
        $
    ''', re.X)

    @classmethod
    def filtered_on(cls, query, tag):
        """
        does the given query filter on given tag? if so return first filter
        """
        # ! this assumes the ast is in the simple format without nests etc.
        for cond in query['ast']:
            if cond[0].startswith('match_tag') and cond[1] == tag:
                return cond
        return False

    @classmethod
    def build_ast(cls, patterns):
        # prepare higher performing query structure, to later match objects
        """
        if patterns looks like so:
        ['target_type=', 'unit=', '!tag_k=not_equals_thistag', 'tag_k:match_this_val', 'arbitrary', 'words']

        then the AST will look like so:
        ('match_and',
         ('!tag_k=not_equals_thistag', ('match_negate',
                                         ('match_tag_equality', 'tag_k', 'not_equals_thistag'))),
         ('target_type=',              ('match_tag_exists', 'target_type')),
         ('unit=',                     ('match_tag_exists', 'unit')),
         ('tag_k:match_this_val',      ('match_tag_regex', 'tag_k', 'match_this_val')),
         ('words',                     ('match_id_regex', 'words')),
         ('arbitrary',                 ('match_id_regex', 'arbitrary'))
        )
        """

        asts = []
        for pattern in patterns:
            matchobj = cls.query_pattern_re.match(pattern)
            oper, key, term, negate = matchobj.group('operation', 'key', 'term', 'negate')
            if oper == '=':
                if key and term:
                    ast = ('match_tag_equality', key, term)
                elif key and not term:
                    ast = ('match_tag_exists', key)
                elif term and not key:
                    ast = ('match_any_tag_value', term)
                else:
                    # pointless pattern
                    continue
            elif oper == ':':
                if key and term:
                    ast = ('match_tag_regex', key, term)
                elif key and not term:
                    ast = ('match_tag_name_regex', key)
                elif term and not key:
                    ast = ('match_tag_value_regex', key)
                else:
                    # pointless pattern
                    continue
            else:
                ast = ('match_id_regex', key)
            if negate:
                ast = ('match_negate', ast)
            asts.append(ast)
        if len(asts) == 1:
            return asts[0]
        return ('match_and',) + tuple(asts)

    # avg by foo
    # avg by foo,bar
    # avg by n3:bucketmatch1|bucketmatch2|..,othertag
    # group by target_type=,region:us-east|us-west|..
    @classmethod
    def build_buckets(cls, spec):
        # http://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-in-python-whilst-preserving-order
        def uniq_list(seq):
            seen = set()
            seen_add = seen.add
            return [x for x in seq if x not in seen and not seen_add(x)]
        tag_specs = spec.split(',')
        struct = {}
        for tag_spec in tag_specs:
            if ':' in tag_spec:
                tag_spec = tag_spec.split(':', 2)
                tag = tag_spec[0]
                buckets = tag_spec[1].split('|')
            else:
                tag = tag_spec
                buckets = []
            # there should always be a fallback ('' bucket), which matches all values
            # while we're add it, remove dupes
            buckets.append('')
            struct[tag] = uniq_list(buckets)
        return struct

########NEW FILE########
__FILENAME__ = simple_match
import re


def match_tag_equality(_oid, data, key, term):
    return data['tags'].get(key) == term


def match_tag_exists(_oid, data, key):
    return key in data['tags']


def match_any_tag_value(_oid, data, term):
    return term in data['tags'].itervalues()


def match_tag_regex(_oid, data, key, term):
    return key in data['tags'] and re.search(term, data['tags'][key])


def match_tag_name_regex(_oid, data, key):
    regex = re.compile(key)
    return any(regex.search(k) for k in data['tags'].iterkeys())


def match_tag_value_regex(_oid, data, term):
    regex = re.compile(term)
    return any(regex.search(v) for v in data['tags'].itervalues())


def match_id_regex(oid, _data, key):
    return re.search(key, oid)


def match_negate(oid, data, ast):
    return not match_ast(oid, data, ast)


def match_or(oid, data, *asts):
    return any(match_ast(oid, data, ast) for ast in asts)


def match_and(oid, data, *asts):
    return all(match_ast(oid, data, ast) for ast in asts)


# (oid, data) -> a key:object from the dict of objects
# ast: an AST structure from Query.compile_asts()
def match_ast(oid, data, ast):
    return globals()[ast[0]](oid, data, *ast[1:])


# objects is expected to be a dict with elements like id: data
# id's are matched, and the return value is a dict in the same format
# if you use tags, make sure data['tags'] is a dict of tags or this'll blow up
def filter_matching(ast, objects):
    return dict((oid, data) for (oid, data) in objects.items() if match_ast(oid, data, ast))

########NEW FILE########
__FILENAME__ = carbon
from . import Plugin


class CarbonPlugin(Plugin):
    '''
    these definitions are probably not correct and need to be adjusted.
    a lot of these might actually be rates and/or in different units. somebody fixme kthx!
    '''
    targets = [
        {
            'match': 'carbon\.agents\.(?P<agent>[^\.]+)\.(?P<wtt>[^\.]+)$',
            'target_type': 'gauge'
        },
        {
            'match': 'carbon\.agents\.(?P<agent>[^\.]+)\.cache\.(?P<wtt>[^\.]+)$',
            'target_type': 'gauge'
        },
    ]

    def sanitize(self, target):
        if target['tags']['wtt'] == 'avgUpdateTime':
            target['tags']['unit'] = 'ms'
            target['tags']['type'] = 'update_time'
        if target['tags']['wtt'] == 'committedPoints':
            target['tags']['unit'] = 'datapoints'
            target['tags']['type'] = 'committed'
        if target['tags']['wtt'] == 'cpuUsage':
            target['tags']['unit'] = 'jiffies'
            target['tags']['type'] = 'carbon_cpu_user'
        if target['tags']['wtt'] == 'creates':
            target['tags']['unit'] = 'whisper_files'
            target['tags']['type'] = 'created'
        if target['tags']['wtt'] == 'errors':
            target['tags']['unit'] = 'Err'
            target['tags']['type'] = 'carbon'
        if target['tags']['wtt'] == 'memUsage':
            target['tags']['unit'] = 'B'
            target['tags']['type'] = 'carbon_mem'
        if target['tags']['wtt'] == 'metricsReceived':
            target['tags']['unit'] = 'metrics'
            target['tags']['type'] = 'received'
        if target['tags']['wtt'] == 'pointsPerUpdate':
            target['tags']['unit'] = 'datapoints_per_update'
        if target['tags']['wtt'] == 'updateOperations':
            target['tags']['unit'] = 'updates'
        if target['tags']['wtt'] == 'queries':
            target['tags']['unit'] = 'queries'
        if target['tags']['wtt'] == 'queues':
            target['tags']['unit'] = 'queues'
        if target['tags']['wtt'] == 'size':
            target['tags']['unit'] = 'B'
            target['tags']['type'] = 'cache_size'
        if target['tags']['wtt'] == 'overflow':
            target['tags']['unit'] = 'events'
            target['tags']['type'] = 'overflow'
        del target['tags']['wtt']
# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = catchall
from . import Plugin


class CatchallPlugin(Plugin):
    """
    Turns metrics that aren't matched by any other plugin in something a bit more useful (than not having them at all)
    Another way to look at it is.. plugin:catchall is the list of targets you can better organize ;)
    Note that the assigned tags (i.e. source tags) are best guesses.  We can't know for sure!
    (this description goes for all catchall plugins)
    """
    priority = -5

    targets = [
        {
            'match': '^(?P<tosplit>[^=]*)$',
            'target_type': 'unknown',
            'tags': {
                 'unit': 'unknown',
                 'source': 'unknown'
            }
        },
    ]


# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = catchall_diamond
from . import Plugin


class CatchallDiamondPlugin(Plugin):
    """
    Like catchall, but for targets from diamond (presumably)
    """
    priority = -4

    targets = [
        {
            'match': '^servers\.(?P<server>[^\.]+)\.(?P<tosplit>.*)',
            'target_type': 'unknown',
            'tags': {
                'unit': 'unknown',
                'source': 'diamond'
            }
        },
    ]


# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = catchall_statsd
from . import Plugin


class CatchallStatsdPlugin(Plugin):
    """
    Like catchall, but for targets from statsd (presumably)
    """
    priority = -4

    targets = [
        {
            'match': '^stats\.gauges\.(?P<tosplit>.*)',
            'target_type': 'gauge',
            'tags': {
                'unit': 'unknown',
                'source': 'statsd'
            }
        },
        {
            'match': '^stats\.timers\.(?P<tosplit>.*)',
            'tags': {
                'source': 'statsd'
            },
            'configure': lambda self, target: self.parse_statsd_timer(target)
        },
        {
            'match': '^stats\.(?P<tosplit>.*)',
            'target_type': 'rate',
            'tags': {
                'unit': 'unknown/s',
                'source': 'statsd'
            }
        },
        {
            'match': '^stats_counts\.(?P<tosplit>.*)',
            'target_type': 'count',
            'tags': {
                'unit': 'unknown',
                'source': 'statsd'
            }
        },
    ]

# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = collectd
from . import Plugin


class CollectdPlugin(Plugin):
    def __init__(self, config):
        if hasattr(config, 'collectd_prefix'):
            prefix = config.collectd_prefix
        else:
            prefix = '^collectd\.'

        self.targets = [
            {
                'match': prefix + '(?P<server>[^\.]+)\.(?P<collectd_plugin>cpu)\.(?P<core>[^\.]+)\.cpu\.(?P<type>[^\.]+)$',
                'target_type': 'gauge_pct',
                'tags': {
                    'unit': 'Jiff',
                    'what': 'cpu_usage'
                }
            },
            {
                'match': prefix + '(?P<server>.+?)\.(?P<collectd_plugin>load)\.load\.(?P<wt>.*)$',
                'target_type': 'gauge',
                'configure': lambda self, target: self.fix_load(target)
            },
            {
                'match': prefix + '(?P<server>[^\.]+)\.interface\.(?P<device>[^\.]+)\.if_(?P<wt>[^\.]+)\.(?P<dir>[^\.]+)$',
                'target_type': 'counter',
                'tags': {'collectd_plugin': 'network'},
                'configure': lambda self, target: self.fix_network(target)
            },
            {
                'match': prefix + '(?P<server>[^\.]+)\.memory\.memory\.(?P<type>[^\.]+)$',
                'target_type': 'gauge',
                'tags': {
                    'unit': 'B',
                    'where': 'system_memory'
                }
            },
            {
                'match': prefix + '(?P<server>[^\.]+)\.df\.(?P<mountpoint>[^\.]+)\.df_complex\.(?P<type>[^\.]+)$',
                'target_type': 'gauge',
                'tags': {'unit': 'B'}
            },
            {
                'match': prefix + '(?P<server>[^\.]+)\.(?P<collectd_plugin>disk)\.(?P<device>[^\.]+)\.disk_(?P<wt>[^\.]+)\.(?P<operation>[^\.]+)$',
                'configure': lambda self, target: self.fix_disk(target)
            }
        ]
        super(CollectdPlugin, self).__init__(config)

    def fix_disk(self, target):
        wt = {
            'merged': {
                'unit': 'Req',
                'type': 'merged'
            },
            'octets': {
                'unit': 'B'
            },
            'ops': {
                'unit': 'Req',
                'type': 'executed'
            },
            'time': {
                'unit': 'ms'
            }
        }
        target['tags'].update(wt[target['tags']['wt']])

        if self.config.collectd_StoreRates:
            target['tags']['target_type'] = 'rate'
            target['tags']['unit'] = target['tags']['unit'] + "/s"
        else:
            target['tags']['target_type'] = 'counter'

        del target['tags']['wt']

    def fix_load(self, target):
        human_to_computer = {
            'shortterm': '01',
            'midterm': '05',
            'longterm': '15'
        }
        target['tags']['unit'] = 'load'
        target['tags']['type'] = human_to_computer.get(target['tags']['wt'], 'unknown')
        del target['tags']['wt']

    def fix_network(self, target):
        dirs = {'rx': 'in', 'tx': 'out'}
        units = {'packets': 'Pckt', 'errors': 'Err', 'octets': 'B'}

        if self.config.collectd_StoreRates:
            target['tags']['target_type'] = 'rate'
            target['tags']['unit'] = units[target['tags']['wt']] + "/s"
        else:
            target['tags']['target_type'] = 'counter'
            target['tags']['unit'] = units[target['tags']['wt']]

        target['tags']['direction'] = dirs[target['tags']['dir']]
        del target['tags']['wt']
        del target['tags']['dir']

# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = cpu
from . import Plugin


class CpuPlugin(Plugin):
    '''
    core can be individual cores as well as total.
    http://www.linuxhowtos.org/System/procstat.htm documents all states, except guest and steal(?)
    everything is in percent, but note that e.g. a 16 core machine goes up to 1600% for total.
    '''
    targets = [
        {
            'match': '^servers\.(?P<server>[^\.]+)\.cpu\.(?P<core>[^\.]+)\.(?P<type>.*)$',
            'target_type': 'gauge_pct',
            'tags': {
                'unit': 'Jiff',
                'what': 'cpu_usage'
            }
        }
    ]

    def default_configure_target(self, target):
        if target['tags']['core'] == 'total':
            target['tags']['core'] = '_sum_'

# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = diamondcollectortime
from . import Plugin


class DiamondCollectortimePlugin(Plugin):
    """
    capture collectortime of all diamond plugins
    """
    targets = [
        {
            'match': '^servers\.(?P<server>[^\.]+)\.(?P<diamond_plugin>[^\.]+)\.(?P<type>collector_time)_(?P<unit>ms)$',
            'target_type': 'gauge',
        }
    ]

# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = diamond_openstack_swift
from . import Plugin


class DiamondOpenstackSwiftPlugin(Plugin):

    targets = [
        {
            'match': '^servers\.(?P<server>[^\.]+)\.openstackswift\.(?P<category>container_metrics)\.(?P<account>[^\.]+)\.(?P<container>[^\.]+)\.(?P<wt>[^\.]+)$',
            'target_type': 'gauge',
        },
        {
            'match': '^servers\.(?P<server>[^\.]+)\.openstackswift\.(?P<category>dispersion)\.(?P<what>container|object|errors)\.?(?P<wt>[^\.]*)$',
            'target_type': 'gauge',
        }
    ]

    def sanitize(self, target):
        if target['tags'].get('what', '') == 'container':
            target['tags']['what'] = 'containers'
        if target['tags'].get('what', '') == 'object':
            target['tags']['what'] = 'objects'

        if 'wt' in target['tags']:
            if target['tags']['wt'] == 'bytes':
                target['tags']['unit'] = 'B'
                target['tags']['type'] = 'used'
            if target['tags']['wt'] == 'objects':
                target['tags']['what'] = 'objects'
                target['tags']['type'] = 'present'
            if target['tags']['wt'] == 'x_timestamp':
                target['tags']['what'] = 'timestamp'
                target['tags']['type'] = 'x'
            if target['tags']['wt'] == 'copies_found':
                target['tags']['type'] = 'found'
            if target['tags']['wt'] == 'copies_expected':
                target['tags']['type'] = 'expected'
            if target['tags']['wt'] == 'pct_found':
                target['tags']['type'] = 'found'
                target['tags']['target_type'] = target['tags']['target_type'] + '_pct'
            if target['tags']['wt'] == 'retries':
                target['tags']['type'] = 'retries_query_' + target['tags']['what']
                target['tags']['what'] = 'events'
            if target['tags']['wt'].startswith('missing_') or target['tags']['wt'] == 'overlapping':  # this should be the rest:
                target['tags']['type'] = target['tags']['wt']
            del target['tags']['wt']


# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = diskspace
from . import Plugin


class DiskspacePlugin(Plugin):
    targets = [
        {
            'match': '^servers\.(?P<server>[^\.]+)\.diskspace\.(?P<mountpoint>[^\.]+)\.(?P<wwt>.*)$',
            'target_type': 'gauge',
        }
    ]

    def sanitize(self, target):
        (u, mtype) = target['tags']['wwt'].split('_')
        units = {
            'byte': 'B',
            'inodes': 'Ino'
        }
        target['tags']['unit'] = units[u]
        target['tags']['type'] = mtype
        del target['tags']['wwt']

# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = filestat
from . import Plugin


class FilestatPlugin(Plugin):

    targets = [
        {
            'match': '^servers\.(?P<server>[^\.]+)\.files\.(?P<type>assigned|max|unused)$',
            'target_type': 'gauge',
            'tags': {'unit': 'File'}
        },
    ]

# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = iostat
from . import Plugin


class IostatPlugin(Plugin):
    '''
    corresponds to diamond diskusage plugin
    '''
    targets = [
        {
            'match': '^servers\.(?P<server>[^\.]+)\.iostat\.(?P<device>[^\.]+)\.(?P<wt>.*_per_second)$',
            'target_type': 'rate',
        },
        {
            'match': '^servers\.(?P<server>[^\.]+)\.iostat\.(?P<device>[^\.]+)\.(?P<wt>.*)$',
            'target_type': 'gauge',
        }
    ]

    def sanitize(self, target):
        # NOTE: a bunch of these are probably not accurate. TODO: someone has
        # to go over these, preferrably someone familiar with the diamond
        # plugin or /proc/diskstats.
        sanitizer = {
            'average_queue_length': ('iops', 'in queue'),
            'average_request_size_byte': ('B', 'iop avg size'),
            'await': ('ms', 'iop service time'),
            'concurrent_io': ('iops', 'concurrent'),
            'io': ('io', None),
            'io_in_progress': ('iops', 'in_progress'),
            'io_milliseconds': ('ms', 'io'),
            'io_milliseconds_weighted': ('ms_weighted', 'io'),
            'iops': ('iops', None),
            'read_await': ('ms', 'read service time'),
            'read_byte': ('B', 'read'),
            'read_byte_per_second': ('B', 'read'),
            'read_requests_merged': ('read_requests', 'merged'),
            'read_requests_merged_per_second': ('read_requests', 'merged'),
            'reads': ('reads', None),
            'reads_byte': ('B', 'read'),
            'reads_merged': ('reads', 'merged'),
            'reads_milliseconds': ('ms', 'spent reading'),
            'reads_per_second': ('reads', None),
            'service_time': ('ms', 'service time'),
            'util_percentage': ('utilisation', None, 'pct'),
            'write_await': ('ms', 'write service time'),
            'write_byte': ('B', 'written'),
            'write_byte_per_second': ('B', 'written'),
            'write_requests_merged': ('write_requests', 'merged'),
            'write_requests_merged_per_second': ('write_requests', 'merged'),
            'writes': ('writes', None),
            'writes_byte': ('B', 'written'),
            'writes_merged': ('writes', 'merged'),
            'writes_milliseconds': ('ms', 'spent writing'),
            'writes_per_second': ('writes', None)
        }
        wt = target['tags']['wt']
        target['tags']['unit'] = sanitizer[wt][0]
        if sanitizer[wt][1] is not None:
            target['tags']['type'] = sanitizer[wt][1]
        if len(sanitizer[wt]) > 2:
            target['tags']['target_type'] = target['tags']['target_type'] + '_' + sanitizer[wt][2]
        del target['tags']['wt']
        return None
# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = load
from . import Plugin


class LoadPlugin(Plugin):
    targets = [
        {
            'match': '^servers\.(?P<server>[^\.]+)\.loadavg\.(?P<wt>.*)$',
            'target_type': 'gauge'
        }
    ]

    def sanitize(self, target):
        if target['tags']['wt'] in ('01', '05', '15'):
            target['tags']['unit'] = 'Load'
            target['tags']['type'] = target['tags']['wt']
        if target['tags']['wt'] in ('processes_running', 'processes_total'):  # this should be ev. else
            (target['tags']['unit'], target['tags']['type']) = target['tags']['wt'].split('_')
        del target['tags']['wt']
# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = memory
from . import Plugin


class MemoryPlugin(Plugin):
    targets = [
        {
            'match': '^servers\.(?P<server>[^\.]+)\.memory\.(?P<type>.*)$',
            'target_type': 'gauge',
            'tags': {
                'unit': 'B',
                'where': 'system_memory'
            },
            'configure': lambda self, target: self.fix_underscores(target, 'type'),
        }
    ]

    def sanitize(self, target):
        target['tags']['type'] = target['tags']['type'].replace('mem_', 'ram_')

# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = mysql
from . import Plugin


class MysqlPlugin(Plugin):
    targets = [
        {
            'match': '^servers\.(?P<server>[^\.]+)\.mysql\.(?P<unit>Thread)s_(?P<type>[^\.]+)$',
            'target_type': 'gauge',
        },
        {
            'match': '^servers\.(?P<server>[^\.]+)\.mysql\.(?P<unit>Conn)ections$',
            'target_type': 'gauge',
        }
    ]

# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = native_proto2
from . import Plugin


class NativeProto2Plugin(Plugin):
    priority = 5
    targets = []

    def upgrade_metric(self, metric):
        if '=' in metric:
            if getattr(self.config, 'process_native_proto2', True):
                nodes = metric.split('.')
                tags = {}
                for (i, node) in enumerate(nodes):
                    if '=' in node:
                        (key, val) = node.split('=', 1)
                        # graphite fix -> Mbps -> Mb/s
                        if key == 'unit' and val.endswith('ps'):
                            val = val[:-2] + "/s"
                        tags[key] = val
                    else:
                        tags["n%d" % (i + 1)] = node
                target = {
                    'id': metric,
                    'tags': tags
                }
                return (self.get_target_id(target), target)
            else:
                return False
        return None
# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = network
from . import Plugin


class NetworkPlugin(Plugin):
    targets = [
        {
            'match': '^servers\.(?P<server>[^\.]+)\.network\.(?P<device>[^\.]+)\.(?P<wt>.*)$',
            'target_type': 'rate',
        }
    ]

    def sanitize(self, target):
        if target['tags']['wt'].endswith('_bit'):
            target['tags']['unit'] = 'B/s'
            target['tags']['type'] = target['tags']['wt'].split('_')[0]
        elif target['tags']['wt'].endswith('_errors'):
            target['tags']['unit'] = 'Err/s'
            target['tags']['type'] = target['tags']['wt'].split('_')[0]
        else:
            target['tags']['unit'] = 'Pckt/s'
            target['tags']['type'] = target['tags']['wt']
        del target['tags']['wt']

# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = openstack_swift
from . import Plugin


class OpenstackSwift(Plugin):
    http_methods = ['GET', 'HEAD', 'PUT', 'REPLICATE']
    targets = [
        # proxy-server
        {
            'match': '^stats.timers\.(?P<server>[^\.]+)\.(?P<service>proxy-server)\.(?P<swift_type>account|container|object)\.(?P<http_method>[^\.]+)\.(?P<http_code>[^\.]+)\.timing\.(?P<tosplit>[^\.]+)$',
            'configure': lambda self, target: self.parse_statsd_timer(target)
        },
        {
            'match': '^stats_counts\.(?P<server>[^\.]+)\.(?P<service>proxy-server)\.?(?P<swift_type>account|container|object)?\.?(?P<http_method>[^\.]*)\.?(?P<http_code>[^\.]*)\.(?P<wt>[^\.]+)$',
            'target_type': 'count'
        },
        {
            'match': '^stats\.(?P<server>[^\.]+)\.(?P<service>proxy-server)\.?(?P<swift_type>account|container|object)?\.?(?P<http_method>[^\.]*)\.?(?P<http_code>[^\.]*)\.(?P<wt>[^\.]+)$',
            'target_type': 'rate'
        },
        # tempauth
        {
            'match': '^stats\.(?P<server>[^\.]+)\.(?P<service>tempauth)\.AUTH_\.(?P<type>[^\.]+)$',
            'target_type': 'rate',
            'tags': {'unit': 'Req/s'}
        },
        {
            'match': '^stats_counts\.(?P<server>[^\.]+)\.(?P<service>tempauth)\.AUTH_\.(?P<type>[^\.]+)$',
            'target_type': 'count',
            'tags': {'unit': 'Req'}
        },
        # object-server
        {
            'match': '^stats\.timers\.(?P<server>[^\.]+)\.(?P<service>object-server)\.(?P<http_method>[^\.]+)\.timing\.(?P<tosplit>[^\.]+)$',
            'tags': {'swift_type': 'object'},
            'configure': lambda self, target: self.parse_statsd_timer(target),
        },
        {
            'match': '^stats_counts\.(?P<server>[^\.]+)\.(?P<service>object-server)\.?(?P<http_method>[^\.]*)\.(?P<unit>async_pendings|errors|timeouts)$',
            'target_type': 'count',
            'tags': {'swift_type': 'object'}
        },
        {
            'match': '^stats\.(?P<server>[^\.]+)\.(?P<service>object-server)\.?(?P<http_method>[^\.]*)\.(?P<unit>async_pendings|errors|timeouts)$',
            'target_type': 'rate',
            'tags': {'swift_type': 'object'}
        },
        # object-auditor
        {
            'match': '^stats\.timers\.(?P<server>[^\.]+)\.(?P<service>object-auditor)\.(?P<http_method>[^\.]+)\.timing\.(?P<tosplit>[^\.]+)$',
            'configure': lambda self, target: self.parse_statsd_timer(target)
        },
        # misc
        {
            'match': '^stats\.(?P<server>[^\.]+)\.(?P<service>[^\.]+)\.failures$',
            'target_type': 'rate',
            'tags': {'unit': 'Err/s'}
        }
    ]

    def sanitize(self, target):
        if 'wt' not in target['tags']:
            return
        sanitizer = {
            'xfer': ('B', 'transferred'),
            'errors': ('Err', None),
            'handoff_count': ('handoffs', 'node'),
            'handoff_all_count': ('handoffs', 'only hand-off locations'),
            'client_disconnects': ('disconnects', 'client'),
            'client_timeouts': ('timeouts', 'client')
        }
        wt = target['tags']['wt']
        target['tags']['unit'] = sanitizer[wt][0]
        if sanitizer[wt][1] is not None:
            target['tags']['type'] = sanitizer[wt][1]
        del target['tags']['wt']

# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = sockstat
from . import Plugin


class SockstatPlugin(Plugin):
    targets = [
        {
            'match': '^servers\.(?P<server>[^\.]+)\.sockets\.(?P<protocol>tcp|udp)?_?(?P<type>[^\.]+)$',
            'target_type': 'gauge',
            'tags': {'unit': 'Sock'}
        }
    ]

# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = sqs
from . import Plugin


class SqsPlugin(Plugin):
    targets = [
        {
            'match': '^servers\.(?P<server>[^\.]+)\.sqs\.(?P<region>[^\.]+)\.(?P<queue>[^\.]+)\.(?P<type>ApproximateNumberOfMessages.*)$',
            'target_type': 'gauge',
            'tags': {'unit': 'Msg'}
        }
    ]

# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = statsd
from . import Plugin


class StatsdPlugin(Plugin):
    '''
    'use this in combination with: derivative(statsd.*.udp_packet_receive_errors)',
    assumes that if you use prefixStats, it's of the format statsd.<statsd_server> , adjust as needed.
    '''
    targets = [
        Plugin.gauge('^statsd\.?(?P<server>[^\.]*)\.(?P<wtt>numStats)', {'service': 'statsd'}),
        Plugin.gauge('^stats\.statsd\.?(?P<server>[^\.]*)\.(?P<wtt>processing_time)$', {'service': 'statsd'}),
        Plugin.count('^stats\.statsd\.?(?P<server>[^\.]*)\.(?P<wtt>[^\.]+)$', {'service': 'statsd'}),  # packets_received, bad_lines_seen
        Plugin.gauge('^stats\.statsd\.?(?P<server>[^\.]*)\.(?P<wtt>graphiteStats\.calculationtime)$', {'service': 'statsd'}),
        Plugin.gauge('^stats\.statsd\.?(?P<server>[^\.]*)\.(?P<wtt>graphiteStats\.flush_[^\.]+)$', {'service': 'statsd'}),  # flush_length, flush_time
        {
            'match': 'stats\.statsd\.?(?P<server>[^\.]*)\.(?P<wtt>graphiteStats\.last_[^\.]+)$',  # last_flush, last_exception. unix timestamp
            'target_type': 'counter',
            'tags': { 'service': 'statsd' }
        },
        # TODO: a new way to have a metric that denotes "all timer packets
        # received".  so i guess a way to define "meta" metrics based on a
        # query (because you may also want to type queries such as "sum(timers
        # unit=Pckt received)" yourself in the query interface
        #{
        #    'match': '^stats\.timers',
        #    'limit': 1,
        #    'target_type': 'count',
        #    'tags': { 'unit': 'Pckt', 'type': 'received_timer'},
        #    'configure': lambda self, target: {'target': 'sumSeries(%s)' % ','.join(['stats.timers.%s.count' % infix for infix in ['*', '*.*', '*.*.*', '*.*.*.*', '*.*.*.*.*']])},
        #}
    ]

    def sanitize(self, target):
        if 'wtt' not in target['tags']:
            return
        if target['tags']['wtt'] == 'packets_received':
            target['tags']['unit'] = 'Pckt/M'
            target['tags']['direction'] = 'in'
        if target['tags']['wtt'] == 'bad_lines_seen':
            target['tags']['unit'] = 'Err/M'
            target['tags']['direction'] = 'in'
            target['tags']['type'] = 'invalid_line'
        if target['tags']['wtt'] == 'numStats':
            target['tags']['unit'] = 'Metric'
            target['tags']['direction'] = 'out'
        if target['tags']['wtt'] == 'graphiteStats.calculationtime':
            target['tags']['unit'] = 'ms'
            target['tags']['type'] = 'calculationtime'
        if target['tags']['wtt'] == 'graphiteStats.last_exception':
            if target['tags']['target_type'] == 'counter':
                target['tags']['unit'] = 'timestamp'
                target['tags']['type'] = 'last_exception'
            else:  # gauge
                target['tags']['unit'] = 's'
                target['tags']['type'] = 'last_exception age'
        if target['tags']['wtt'] == 'graphiteStats.last_flush':
            if target['tags']['target_type'] == 'counter':
                target['tags']['unit'] = 'timestamp'
                target['tags']['type'] = 'last_flush'
            else:  # gauge
                target['tags']['unit'] = 's'
                target['tags']['type'] = 'last_flush age'
        if target['tags']['wtt'] == 'graphiteStats.flush_length':
            target['tags']['unit'] = 'B'
            target['tags']['direction'] = 'out'
            target['tags']['to'] = 'graphite'
        if target['tags']['wtt'] == 'graphiteStats.flush_time':
            target['tags']['unit'] = 'ms'
            target['tags']['direction'] = 'out'
            target['tags']['to'] = 'graphite'
        if target['tags']['wtt'] == 'processing_time':
            target['tags']['unit'] = 'ms'
            target['tags']['type'] = 'processing'
        del target['tags']['wtt']
# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = tcp
from . import Plugin


class TcpPlugin(Plugin):
    targets = [
        {
            'match': '^servers\.(?P<server>[^\.]+)\.(?P<protocol>tcp)\.(?P<type>.*)$',
            'target_type': 'rate',
            'tags': {'unit': 'Event'},
            'configure': lambda self, target: self.fix_underscores(target, 'type'),
        }
    ]

    def sanitize(self, target):
        target['tags']['type'] = target['tags']['type'].replace('TCP', '')

# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = udp
from . import Plugin


class UdpPlugin(Plugin):
    targets = [
        {
            'targets': [
                {
                    'match': '^servers\.(?P<server>[^\.]+)\.(?P<protocol>udp)\.(?P<type>In|Out)(?P<unit>Datagrams)$',
                    'configure': lambda self, target: self.fix_underscores(target, ['type', 'unit'])
                },
                {
                    'match': '^servers\.(?P<server>[^\.]+)\.(?P<protocol>udp)\.(?P<type>[^\.]+)Errors$',
                    'tags': {'unit': 'Err/s'},
                    'configure': lambda self, target: self.fix_underscores(target, 'type'),
                },
                {
                    'match': '^servers\.(?P<server>[^\.]+)\.(?P<protocol>udp)\.(?P<type>NoPorts)$',
                    'tags': {'unit': 'Event/s'},
                    'configure': lambda self, target: self.fix_underscores(target, 'type')
                }
            ],
            'target_type': 'rate'
        }
    ]

# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = vmstat
from . import Plugin


class VmstatPlugin(Plugin):
    targets = [
        {
            'match': '^servers\.(?P<server>[^\.]+)\.vmstat\.(?P<type>.*)$',
            'target_type': 'rate',
            'tags': {'unit': 'Page'}
        }
    ]

    def sanitize(self, target):
        target['tags']['type'] = target['tags']['type'].replace('pgpg', 'paging_')
        target['tags']['type'] = target['tags']['type'].replace('pswp', 'swap_')
# vim: ts=4 et sw=4:

########NEW FILE########
__FILENAME__ = suggested_queries
# Note:
# * these demonstrate some id matching, tag matching, etc. there's usually
#    multiple ways to achieve the same result.
# * tags here do not necessarily correspond to tags in targets. they are for
#   informative purposes only.  although we could (automatically) display the
#   tags from the query (and make keys implicit in the color of the label or
#   something, to save space), I don't do that because:
#   * id matching allows shorter, easier hackable queries.  this hides
#   information which would otherwise be available as tags.
#   * some tags don't need to be mentioned explicitly (i.e. type=byte_used can
#   be assumed for disk usage)
#   * some tags can be paraphrased per env-specific rules (usually the case for
#   hostnames)
queries = [
    {
        'query': 'diskspace unit=B used _var',
        'desc': '/var usage'
    },
    {
        'query': 'diskspace unit=B used _var avg by server',
        'desc': '/var usage, average of all servers'
    },
    {
        'query': 'diskspace unit=B/s used _var',
        'desc': 'change in /var usage'
    },
    {
        'query': 'iostat rate (read|write) byte',
        'desc': 'read/write B/s'  # TODO: a better way to paraphrase these. some kind of aggregation?
    },
    {
        'query': 'stack plugin=load group by type !05 !15 avg over 30M',
        'desc': 'compare load across machines'  # no 5,15 minutely avg, we already have 1 minutely
    },
    {
        'query': 'device=eth0 (rx|tx) bit avg by type sum by server avg over 1h',
        'desc': 'network traffic'
    }
]
suggested_queries = {
    'notes': 'these will only work if you have the corresponding metrics',
    'queries': queries
}

########NEW FILE########
__FILENAME__ = target
import re


class Target(dict):
    def __init__(self, src_dict):
        dict.__init__(self)
        self['match_buckets'] = {}
        self.update(src_dict)

    # targets that can get aggregated together with other tags, must
    # have at least 1 of the aggregation tags ('sum by' / 'avg by')
    # tags in the variables list.
    # targets that can get aggregated together must:
    # * have the same aggregation tag keys (not values, because we
    # aggregate across different values for these tags)
    # * fall into the same aggregation bucket
    # * have the same variables (key and val), except those vals that
    # are being aggregated by.
    # so for every group of aggregation tags and variables we build a
    # list of targets that can be aggregated together

    # of course it only makes sense to agg by tags that the target
    # actually has, and that are not already constants (meaning
    # every target in the graph has the same value)

    def get_agg_key(self, agg_by_struct):
        if not agg_by_struct:
            return False

        # key with all tag_v:bucket_id for tags in agg_by_struct
        agg_id = []
        for agg_tag in sorted(set(agg_by_struct.keys()).intersection(set(self['variables'].keys()))):
            # find first bucket pattern that maches.
            # note that there should always be a catchall (''), so bucket_id should always be set
            bucket_id = next((patt for patt in agg_by_struct[agg_tag] if patt in self['variables'][agg_tag]))
            agg_id.append("%s:%s" % (agg_tag, bucket_id))
            self['match_buckets'][agg_tag] = bucket_id
        agg_id_str = ','.join(sorted(agg_id))

        # key with all variable tag_k=tag_v if tag_k not in agg_by_struct
        variables = []
        for tag_key in sorted(set(self['variables'].keys()).difference(set(agg_by_struct.keys()))):
            val = self['variables'][tag_key]
            # t can be a tuple if it's an aggregated tag
            if not isinstance(val, basestring):
                val = val[0]
            variables.append('%s=%s' % (tag_key, val))
        variables_str = ','.join(variables)
        # some values can be like "'bucket' sum (23 vals, 2 uniqs)" due to an
        # earlier aggregation. if now targets have a different amount
        # values matched, that doesn't matter and they should still
        # be aggregated together if the rest of the conditions are met
        variables_str = re.sub('\([0-9]+ vals, [0-9]+ uniqs\)', '(deets)', variables_str)

        # does this target miss one or more of the agg_by_struct keys?
        # i.e. 'sum by n1,n6' and this target only has the n1 tag.
        # put the ones that have the same missing tags together
        # and later aggregate them without that tag
        missing = []
        for tag_key in sorted(set(agg_by_struct.keys()).difference(set(self['variables'].keys()))):
            missing.append(tag_key)
        missing_str = ','.join(sorted(missing))

        agg_key = 'agg_id_found:%s__agg_id_missing:%s__variables:%s' % (agg_id_str, missing_str, variables_str)
        #from pprint import pformat
        #print "get_agg_key"
        #print "    self:", pformat(self, 8, 100)
        #print "    struct:", agg_by_struct
        #print "    resulting key:", agg_key
        return agg_key

    def get_graph_info(self, group_by):
        constants = {}
        graph_key = []
        self['variables'] = {}
        for (tag_name, tag_value) in self['tags'].items():
            if tag_name in group_by:
                if len(group_by[tag_name]) == 1:
                    assert group_by[tag_name][0] == ''
                    # only the fallback bucket, we know this will be a constant
                    constants[tag_name] = tag_value
                    graph_key.append("%s=%s" % (tag_name, tag_value))
                else:
                    bucket_id = next((patt for patt in group_by[tag_name] if patt in tag_value))
                    graph_key.append("%s:%s" % (tag_name, bucket_id))
                    self['variables'][tag_name] = tag_value
            else:
                self['variables'][tag_name] = tag_value
        graph_key = '__'.join(sorted(graph_key))
        return (graph_key, constants)


def graphite_func_aggregate(targets, agg_by_tags, aggfunc):

    aggfunc_abbrev = {
        "averageSeries": "avg",
        "sumSeries": "sum"
    }

    agg = Target({
        'target': '%s(%s)' % (aggfunc, ','.join([t['target'] for t in targets])),
        'id': [t['id'] for t in targets],
        'variables': targets[0]['variables'],
        'tags': targets[0]['tags']
    })

    # set the tags that we're aggregating by to their special values

    # differentiators is a list of tag values that set the contributing targets apart
    # this will be used later in the UI
    differentiators = {}

    # in principle every target that came in will have the same match_bucket for the given tag
    # (that's the whole point of bucketing)
    # however, some targets may end up in the aggregation without actually having the tag
    # so only set it when we find it
    bucket_id = '<none>'

    for agg_by_tag in agg_by_tags.keys():

        for t in targets:
            if agg_by_tag in t['match_buckets']:
                bucket_id = t['match_buckets'][agg_by_tag]
            differentiators[agg_by_tag] = differentiators.get(agg_by_tag, [])
            differentiators[agg_by_tag].append(t['variables'].get(agg_by_tag, '<missing>'))
        differentiators[agg_by_tag].sort()

        bucket_id_str = ''
        # note, bucket_id can be an empty string (catchall bucket),
        # in which case don't mention it explicitly
        if bucket_id:
            bucket_id_str = "'%s' " % bucket_id

        tag_val = (
            '%s%s (%d vals, %d uniqs)' % (
                bucket_id_str,
                aggfunc_abbrev.get(aggfunc, aggfunc),
                len(differentiators[agg_by_tag]),
                len(set(differentiators[agg_by_tag]))
            ),
            differentiators[agg_by_tag]
        )
        agg['variables'][agg_by_tag] = tag_val
        agg['tags'][agg_by_tag] = tag_val

    return agg

########NEW FILE########
__FILENAME__ = dummyprefs
# for test cases
class DummyPrefs:
    graph_options = []

########NEW FILE########
__FILENAME__ = testhelpers
import copy


def get_proto2(key, tags_base, target_type, unit, updates={}):
    metric = {
        'id': key,
        'tags': copy.deepcopy(tags_base),
    }
    metric['tags'].update(updates)
    metric['tags']['target_type'] = target_type
    metric['tags']['unit'] = unit
    return metric

########NEW FILE########
__FILENAME__ = test_81
from graph_explorer.query import Query
import graph_explorer.graphs as g
from graph_explorer.target import Target
from dummyprefs import DummyPrefs


def test_nontrivial_implicit_aggregation():
    preferences = DummyPrefs()
    # we ultimately want 1 graph with 1 line for each server,
    # irrespective of the values of the other tags (n1 and n2)
    # and even whether or not the metrics have those tags at all.
    query = Query("")
    query['group_by'] = {}
    query['sum_by'] = {'n1': [''], 'n2': ['']}

    targets = {
        # web1 : one with and without n2
        'web1.a.a': {
            'id': 'web1.a.a',
            'tags': {
                'server': 'web1',
                'n1': 'a',
                'n2': 'a'
            }
        },
        'web1.a': {
            'id': 'web1.a',
            'tags': {
                'server': 'web1',
                'n1': 'a',
            }
        },
        # web 2: 2 different values of n2
        'web2.a.a': {
            'id': 'web2.a.a',
            'tags': {
                'server': 'web2',
                'n1': 'a',
                'n2': 'a'
            }
        },
        'web2.a.b': {
            'id': 'web2.a.b',
            'tags': {
                'server': 'web2',
                'n1': 'a',
                'n2': 'b'
            }
        },
        # web3: with and without n2, diff value for n1
        'web3.a.a': {
            'id': 'web3.a.a',
            'tags': {
                'server': 'web3',
                'n1': 'a',
                'n2': 'a'
            }
        },
        'web3.b': {
            'id': 'web3.b',
            'tags': {
                'server': 'web3',
                'n1': 'b'
            }
        }
    }
    from pprint import pprint
    for (k, v) in targets.items():
        v = Target(v)
        v.get_graph_info(group_by={})
        targets[k] = v
    graphs, _query = g.build_from_targets(targets, query, preferences)
    # TODO: there should be only 1 graph, containing 3 lines, with each 2 targets per server
    # i.e. something like this:
    expected = {
        'targets': {
            'web1.a.a__web1.a': {
                'id': ['web1.a.a', 'web1.a']
            },
            'web2.a.a__web2.a.b': {
                'id': ['web2.a.a', 'web2.a.b']
            },
            'web3.a.a__web3.b': {
                'id': ['web3.a.a', 'web3.b']
            }
        }
    }

    print "Graphs:"
    for (k, v) in graphs.items():
        print "graph key"
        pprint(k)
        print "val:"
        pprint(v)
    assert expected == graphs

########NEW FILE########
__FILENAME__ = test_config
def test_config_valid():
    # TODO update this for new text files
    from graph_explorer import config
    from graph_explorer.validation import ConfigValidator

    c = ConfigValidator(obj=config)
    valid = c.validate()
    if not valid:
        from pprint import pprint
        pprint(c.errors)
    # assert valid

########NEW FILE########
__FILENAME__ = test_equivalence
from graph_explorer.query import Query
import graph_explorer.graphs as g
from dummyprefs import DummyPrefs


def test_equivalence():
    preferences = DummyPrefs()
    query = Query("")
    query['sum_by'] = {'core': ['']}
    targets = {
        'servers.host.cpu.cpu0.irq': {
            'id': 'servers.host.cpu.cpu0.irq',
            'tags': {
                'core': 'cpu0',
                'plugin': 'cpu',
                'server': 'host',
                'target_type': 'gauge_pct',
                'type': 'irq',
                'unit': 'cpu_state'
            }
        },
        'servers.host.cpu.cpu0.softirq': {
            'id': 'servers.host.cpu.cpu0.softirq',
            'tags': {
                'core': 'cpu0',
                'plugin': 'cpu',
                'server': 'host',
                'target_type': 'gauge_pct',
                'type': 'softirq',
                'unit': 'cpu_state'
            }
        },
        'servers.host.cpu.cpu2.irq': {
            'id': 'servers.host.cpu.cpu2.irq',
            'tags': {
                'core': 'cpu2',
                'plugin': 'cpu',
                'server': 'host',
                'target_type': 'gauge_pct',
                'type': 'irq',
                'unit': 'cpu_state'
            }
        },
        'servers.host.cpu.cpu2.softirq': {
            'id': 'servers.host.cpu.cpu2.softirq',
            'tags': {
                'core': 'cpu2',
                'plugin': 'cpu',
                'server': 'host',
                'target_type': 'gauge_pct',
                'type': 'softirq',
                'unit': 'cpu_state'
            }
        },
        'servers.host.cpu.total.irq': {
            'id': 'servers.host.cpu.total.irq',
            'tags': {
                'core': '_sum_',
                'plugin': 'cpu',
                'server': 'host',
                'target_type': 'gauge_pct',
                'type': 'irq',
                'unit': 'cpu_state'
            }
        },
        'servers.host.cpu.total.softirq': {
            'id': 'servers.host.cpu.total.softirq',
            'tags': {
                'core': '_sum_',
                'plugin': 'cpu',
                'server': 'host',
                'target_type': 'gauge_pct',
                'type': 'softirq',
                'unit': 'cpu_state'
            }
        }
    }

    graphs, _query = g.build_from_targets(targets, query, preferences)
    assert len(graphs) == 1
    _, graph = graphs.popitem()
    assert len(graph['targets']) == 2
    ids = [t['id'] for t in graph['targets']]
    assert ids == ['servers.host.cpu.total.irq', 'servers.host.cpu.total.softirq']

    # if there's a filter, equivalence doesn't hold and we should get 2 targets,
    # each the sum of two non-sums
    # and the _sum_ metrics should be removed
    query = Query("core:(_sum_|cpu0|cpu2) sum by core")
    #query['sum_by'] = {'core': ['']}
    #query['patterns'].append('core:(_sum_|cpu0|cpu2)')
    graphs, _query = g.build_from_targets(targets, query, preferences)
    assert len(graphs) == 1
    _, graph = graphs.popitem()
    assert len(graph['targets']) == 2
    ids = [t['id'] for t in graph['targets']]
    assert ids == [
        ['servers.host.cpu.cpu0.softirq', 'servers.host.cpu.cpu2.softirq'],
        ['servers.host.cpu.cpu0.irq', 'servers.host.cpu.cpu2.irq']
    ]

########NEW FILE########
__FILENAME__ = test_graphs
from graph_explorer.query import Query
import graph_explorer.graphs as g
from graph_explorer.target import Target
from dummyprefs import DummyPrefs


def test_aggregation():
    preferences = DummyPrefs()
    # note: uneven aggregation: we only want 1 resulting metric,
    query = Query("")
    query['avg_by'] = {'server': ['']}
    query['sum_by'] = {'type': ['']}

    targets = {
        'web1.db': {
            'id': 'web1.db',
            'tags': {
                'server': 'web1',
                'type': 'db',
                'n3': 'foo'
            }
        },
        'web1.php': {
            'id': 'web1.php',
            'tags': {
                'server': 'web1',
                'type': 'php',
                'n3': 'foo'
            }
        },
        'web2.db': {
            'id': 'web2.db',
            'tags': {
                'server': 'web2',
                'type': 'db',
                'n3': 'foo'
            }
        },
        'web2.php': {
            'id': 'web2.php',
            'tags': {
                'server': 'web2',
                'type': 'php',
                'n3': 'foo'
            }
        },
        'web2.memcache': {
            'id': 'web2.memcache',
            'tags': {
                'server': 'web2',
                'type': 'memcache',
                'n3': 'foo'
            }
        }
    }
    from pprint import pprint
    for (k, v) in targets.items():
        v = Target(v)
        v.get_graph_info(group_by={})
        targets[k] = v
    graphs, _query = g.build_from_targets(targets, query, preferences)
    # TODO: there should be only 1 graph, containing all 5 items
    print "Graphs:"
    for (k, v) in graphs.items():
        print "graph key"
        pprint(k)
        print "val:"
        pprint(v)
    assert {} == graphs

########NEW FILE########
__FILENAME__ = test_query
from graph_explorer.query import Query
import copy
import unittest


def test_build_buckets_one_no_buckets():
    assert Query.build_buckets("foo") == {'foo': ['']}


def test_build_buckets_two_no_buckets():
    assert Query.build_buckets("foo,bar") == {'foo': [''], 'bar': ['']}


def test_build_buckets_two_with_buckets():
    assert Query.build_buckets("n3:bucketmatch1|bucketmatch2,othertag") == {
        'n3': ['bucketmatch1', 'bucketmatch2', ''],
        'othertag': ['']
    }


def test_build_buckets_two_with_buckets_group_by_style():
    # for 'group by', there can be '=' in there.
    assert Query.build_buckets('target_type=,region:us-east|us-west|') == {
        'target_type=': [''],
        'region': ['us-east', 'us-west', '']
    }


class _QueryTestBase(unittest.TestCase):
    maxDiff = None

    @staticmethod
    def dummyQuery(**dummydict):
        dummy = copy.deepcopy(Query.default)
        # minimal form of prepare() (syntactic sugar processing)
        # we do it this way so we know how the data structure looks like
        dummy.update({
            'patterns': ['target_type=', 'unit='],
            'group_by': {'target_type': [''], 'unit': [''], 'server': ['']}
        })
        dummy.update(dummydict)
        return dummy

    def assertQueryMatches(self, query1, query2):
        self.assertDictEqual(query1, query2)


class TestQueryBasic(_QueryTestBase):
    def test_empty(self):
        query = Query("")
        self.assertQueryMatches(query, self.dummyQuery(
            ast=(
                'match_and',
                ('match_tag_exists', 'target_type'),
                ('match_tag_exists', 'unit')
            ),
            target_modifiers=[Query.derive_counters],
            patterns=['target_type=', 'unit=']
        ))

    def test_two_simple_terms(self):
        query = Query("foo bar")
        self.assertQueryMatches(query, self.dummyQuery(
            ast=(
                'match_and',
                ('match_tag_exists', 'target_type'),
                ('match_tag_exists', 'unit'),
                ('match_id_regex', 'foo'),
                ('match_id_regex', 'bar')
            ),
            target_modifiers=[Query.derive_counters],
            patterns=['target_type=', 'unit=', 'foo', 'bar']
        ))

    def test_query_only_statement(self):
        dummy = self.dummyQuery(
            statement='list',
            ast=(
                'match_and',
                ('match_tag_exists', 'target_type'),
                ('match_tag_exists', 'unit')
            ),
            patterns=['target_type=', 'unit='],
            target_modifiers=[Query.derive_counters],
        )
        query = Query("list")
        self.assertQueryMatches(query, dummy)
        query = Query("list ")
        self.assertQueryMatches(query, dummy)


class TestQueryAdvanced(_QueryTestBase):
    def test_typo_before_sum(self):
        query = Query("octo -20hours unit=b/s memory group by foo avg by barsum by baz")
        dummy = self.dummyQuery(
            avg_by={'barsum': ['']},
            group_by={'target_type': [''], 'unit': [''], 'foo': ['']},
            patterns=['target_type=', 'unit=', 'octo', '-20hours', 'unit=b/s',
                      'memory', 'by', 'baz']
        )
        del dummy['target_modifiers']
        self.assertDictContainsSubset(dummy, query)
        ast_first_part = (
            'match_and',
            ('match_tag_exists', 'target_type'),
            ('match_tag_exists', 'unit'),
            ('match_id_regex', 'octo'),
            ('match_id_regex', '-20hours'),
        )
        ast_last_part = (
            ('match_id_regex', 'memory'),
            ('match_id_regex', 'by'),
            ('match_id_regex', 'baz')
        )
        ast = query['ast']

        self.assertTupleEqual(ast[:len(ast_first_part)],
                              ast_first_part)
        self.assertTupleEqual(ast[len(ast_first_part) + 1:],
                              ast_last_part)
        fat_hairy_or_filter = ast[len(ast_first_part)]
        self.assertEqual(fat_hairy_or_filter[0], 'match_or')
        unit_clauses = fat_hairy_or_filter[1:]
        for clause in unit_clauses:
            self.assertEqual(clause[:2], ('match_tag_equality', 'unit'))
        all_the_units = [clause[2] for clause in unit_clauses]
        for unit in ('b/s', 'MiB/s', 'PiB', 'kB/w', 'b'):
            self.assertIn(unit, all_the_units)
        self.assertTrue(any('apply_requested_unit' in str(f) for f in query['target_modifiers']),
                        msg='apply_requested_unit callback not in %r' % query['target_modifiers'])

    def test_sum_by_buckets(self):
        query = Query("stack from -20hours to -10hours avg over 10M sum by foo:bucket1|bucket2,bar min 100 max 200")
        self.assertQueryMatches(query, self.dummyQuery(**{
            'ast': (
                'match_and',
                ('match_tag_exists', 'target_type'),
                ('match_tag_exists', 'unit')
            ),
            'patterns': ['target_type=', 'unit='],
            'statement': 'stack',
            'avg_over': (10, 'M'),
            'from': '-20hours',
            'to': '-10hours',
            'min': '100',
            'max': '200',
            'sum_by': {'foo': ['bucket1', 'bucket2', ''], 'bar': ['']},
            'target_modifiers': [Query.derive_counters],
        }))

    def test_group_by_advanced(self):
        query = Query("dfvimeodfs disk srv node used group by mountpoint=:dfs1,server")
        # note: ideally, the order would be <default group by strong> + user defined group by's
        # but that was a little hard to implement
        self.assertQueryMatches(query, self.dummyQuery(**{
            'ast': (
                'match_and',
                ('match_tag_exists', 'mountpoint'),
                ('match_tag_exists', 'target_type'),
                ('match_tag_exists', 'unit'),
                ('match_id_regex', 'dfvimeodfs'),
                ('match_id_regex', 'disk'),
                ('match_id_regex', 'srv'),
                ('match_id_regex', 'node'),
                ('match_id_regex', 'used')
            ),
            'patterns': ['mountpoint=', 'target_type=', 'unit=', 'dfvimeodfs', 'disk', 'srv', 'node', 'used'],
            'group_by': {'target_type': [''], 'unit': [''], 'mountpoint': ['dfs1', ''], 'server': ['']},
            'target_modifiers': [Query.derive_counters],
        }))

########NEW FILE########
__FILENAME__ = test_structured_metrics
from graph_explorer import structured_metrics


def test_load():
    s_metrics = structured_metrics.StructuredMetrics()
    errors = s_metrics.load_plugins()
    assert len(errors) == 0

########NEW FILE########
__FILENAME__ = test_structured_metrics_native_proto2
from graph_explorer import structured_metrics


def test_native_proto2_disabled():
    # by default, the plugin ignores them
    s_metrics = structured_metrics.StructuredMetrics()
    s_metrics.load_plugins()

    key = "foo.bar=blah.baz"
    real = s_metrics.list_metrics([key])
    assert len(real) == 0


def test_native_proto2_enabled():
    DummyCfg = type('DummyCfg', (object,), {})
    DummyCfg.process_native_proto2 = True
    s_metrics = structured_metrics.StructuredMetrics(DummyCfg)
    s_metrics.load_plugins()

    key = "foo.bar=blah.baz.target_type=rate.unit=MiB/d"
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert real.values()[0] == {
        'id': key,
        'tags': {
            'n1': 'foo',
            'bar': 'blah',
            'n3': 'baz',
            'target_type': 'rate',
            'unit': 'MiB/d'
        }
    }

########NEW FILE########
__FILENAME__ = test_structured_metrics_plugin_catchall
import testhelpers
from graph_explorer import structured_metrics


def test_simple():
    s_metrics = structured_metrics.StructuredMetrics()
    s_metrics.load_plugins()
    tags_base = {
        'plugin': 'catchall',
        'source': 'unknown',
    }

    def get_proto2(key, target_type, unit, updates={}):
        return testhelpers.get_proto2(key, tags_base, target_type, unit, updates)

    key = "foo.bar"
    expected = get_proto2(key, 'unknown', 'unknown', {'n1': 'foo', 'n2': 'bar'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

########NEW FILE########
__FILENAME__ = test_structured_metrics_plugin_catchall_diamond
import testhelpers
from graph_explorer import structured_metrics


def test_basic():
    s_metrics = structured_metrics.StructuredMetrics()
    s_metrics.load_plugins()
    tags_base = {
        'plugin': 'catchall_diamond',
        'source': 'diamond',
    }

    def get_proto2(key, target_type, unit, updates={}):
        return testhelpers.get_proto2(key, tags_base, target_type, unit, updates)

    key = "servers.web123.foo.bar"
    expected = get_proto2(key, 'unknown', 'unknown', {'server': 'web123', 'n1': 'foo', 'n2': 'bar'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

########NEW FILE########
__FILENAME__ = test_structured_metrics_plugin_catchall_statsd
from graph_explorer import structured_metrics
import testhelpers


def test_parse_count_and_rate():
    s_metrics = structured_metrics.StructuredMetrics()
    s_metrics.load_plugins()
    tags_base = {
        'n1': 'foo',
        'n2': 'req',
        'plugin': 'catchall_statsd',
        'source': 'statsd',
    }

    def get_proto2(key, target_type, unit, updates={}):
        return testhelpers.get_proto2(key, tags_base, target_type, unit, updates)

    key = "stats.foo.req"
    expected = get_proto2(key, 'rate', 'unknown/s')
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats_counts.foo.req"
    expected = get_proto2(key, 'count', 'unknown')
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]


def test_parse_timers():
    s_metrics = structured_metrics.StructuredMetrics()
    s_metrics.load_plugins()
    tags_base = {
        'n1': 'memcached_default_get',
        'plugin': 'catchall_statsd',
        'source': 'statsd',
    }

    def get_proto2(key, target_type, unit, updates={}):
        return testhelpers.get_proto2(key, tags_base, target_type, unit, updates)

    key = "stats.timers.memcached_default_get.count"
    expected = get_proto2(key, 'count', 'Pckt')
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.memcached_default_get.count_ps"
    expected = get_proto2(key, 'rate', 'Pckt/s')
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.memcached_default_get.lower"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'lower'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.memcached_default_get.mean"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'mean'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.memcached_default_get.mean_90"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'mean_90'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.memcached_default_get.median"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'median'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.memcached_default_get.std"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'std'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.memcached_default_get.sum"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'sum'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.memcached_default_get.sum_90"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'sum_90'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.memcached_default_get.upper"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'upper'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.memcached_default_get.upper_90"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'upper_90'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.memcached_default_get.histogram.bin_0_01"
    expected = get_proto2(key, 'gauge', 'freq_abs', {'bin_upper': '0.01', 'orig_unit': 'ms'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.memcached_default_get.histogram.bin_5"
    expected = get_proto2(key, 'gauge', 'freq_abs', {'bin_upper': '5', 'orig_unit': 'ms'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.memcached_default_get.histogram.bin_inf"
    expected = get_proto2(key, 'gauge', 'freq_abs', {'bin_upper': 'inf', 'orig_unit': 'ms'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

########NEW FILE########
__FILENAME__ = test_structured_metrics_plugin_openstack_swift
from graph_explorer import structured_metrics
import testhelpers


# test openstack_swift timers, but also reusability of statsd timer logic
def test_parse_timers():
    s_metrics = structured_metrics.StructuredMetrics()
    s_metrics.load_plugins()
    tags_base = {
        'server': 'lvimdfsproxy2',
        'plugin': 'openstack_swift',
        'swift_type': 'object',
        'service': 'proxy-server',
        'http_method': 'GET',
        'http_code': '200'
    }

    def get_proto2(key, target_type, unit, updates={}):
        return testhelpers.get_proto2(key, tags_base, target_type, unit, updates)

    key = "stats.timers.lvimdfsproxy2.proxy-server.object.GET.200.timing.count"
    expected = get_proto2(key, 'count', 'Pckt')
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.lvimdfsproxy2.proxy-server.object.GET.200.timing.count_ps"
    expected = get_proto2(key, 'rate', 'Pckt/s')
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.lvimdfsproxy2.proxy-server.object.GET.200.timing.lower"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'lower'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.lvimdfsproxy2.proxy-server.object.GET.200.timing.mean"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'mean'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.lvimdfsproxy2.proxy-server.object.GET.200.timing.mean_90"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'mean_90'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.lvimdfsproxy2.proxy-server.object.GET.200.timing.median"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'median'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.lvimdfsproxy2.proxy-server.object.GET.200.timing.std"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'std'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.lvimdfsproxy2.proxy-server.object.GET.200.timing.sum"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'sum'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.lvimdfsproxy2.proxy-server.object.GET.200.timing.sum_90"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'sum_90'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.lvimdfsproxy2.proxy-server.object.GET.200.timing.upper"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'upper'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

    key = "stats.timers.lvimdfsproxy2.proxy-server.object.GET.200.timing.upper_90"
    expected = get_proto2(key, 'gauge', 'ms', {'stat': 'upper_90'})
    real = s_metrics.list_metrics([key])
    assert len(real) == 1
    assert expected == real.values()[0]

########NEW FILE########
__FILENAME__ = test_target
from graph_explorer.target import Target


def test_agg_key():
    t = Target({
        'variables': {
            'foo': 'bar',
            'target_type': 'rate',
            'region': 'us-east-1'
        }})

    # catchall bucket
    assert t.get_agg_key({'foo': ['']}) == 'agg_id_found:foo:__agg_id_missing:__variables:region=us-east-1,target_type=rate'

    # non catchall bucket
    assert t.get_agg_key({'foo': ['ba', ''], 'bar': ['']}) == 'agg_id_found:foo:ba__agg_id_missing:bar__variables:region=us-east-1,target_type=rate'

    struct = {
        'n3': ['bucketmatch1', 'bucketmatch2'],
        'othertag': ['']
    }
    # none of the structs applies
    assert t.get_agg_key(struct) == 'agg_id_found:__agg_id_missing:n3,othertag__variables:foo=bar,region=us-east-1,target_type=rate'

    struct = {
        'target_type': [''],
        'region': ['us-east', 'us-west', '']
    }
    # one catchall, the other matches
    assert t.get_agg_key(struct) == 'agg_id_found:region:us-east,target_type:__agg_id_missing:__variables:foo=bar'

########NEW FILE########
__FILENAME__ = test_unitconv
from __future__ import division

import doctest
import unittest
from graph_explorer import unitconv


def test_unitconv():
    # this would be lots better if we could just use py.test --doctest-modules,
    # but a bunch of other code has things that look like doctests and fail,
    # and more code which isn't protected by __name__ == "__main__" checks, and
    # py.test won't let us pick and choose modules for doctesting.
    #
    # or if we could use doctest.DocTestSuite(), that'd be nice, but that
    # would require py.test 2.3 to work, and i worry about adding dependencies
    # on things as new as that.
    doctest.testmod(unitconv)


class TestParseUnitname(unittest.TestCase):
    def test_non_fractional(self):
        self.assertDictEqual(
            unitconv.parse_unitname('Kimo'),
            {'multiplier': 1024 * 60 * 60 * 24 * 30, 'unit_class': 'time',
             'primary_unit': 's', 'base_unit': 'mo',
             'numer_multiplier': 1024 * 60 * 60 * 24 * 30, 'numer_unit_class': 'time',
             'numer_primary_unit': 's', 'numer_base_unit': 'mo'})

    def test_fractional(self):
        self.assertDictEqual(
            unitconv.parse_unitname('GB/h'),
            {'numer_multiplier': 1e9 * 8, 'denom_multiplier': 3600,
             'multiplier': 1e9 * 8 / 3600,
             'numer_unit_class': 'datasize', 'denom_unit_class': 'time',
             'unit_class': 'datasize/time',
             'numer_primary_unit': 'b', 'denom_primary_unit': 's',
             'primary_unit': 'b/s',
             'numer_base_unit': 'B', 'denom_base_unit': 'h',
             'base_unit': 'B/h'})

        self.assertDictEqual(
            unitconv.parse_unitname('kb/k', fold_scale_prefix=False),
            {'numer_multiplier': 1, 'denom_multiplier': 1,
             'multiplier': 1,
             'numer_scale_multiplier': 1000, 'denom_scale_multiplier': 1,
             'scale_multiplier': 1000,
             'numer_unit_class': 'datasize', 'denom_unit_class': None,
             'unit_class': None,
             'numer_primary_unit': 'b', 'denom_primary_unit': 'k',
             'primary_unit': 'b/k',
             'numer_base_unit': 'b', 'denom_base_unit': 'k',
             'base_unit': 'b/k'})

        self.assertDictEqual(
            unitconv.parse_unitname('Foobity/w', fold_scale_prefix=False),
            {'numer_multiplier': 1, 'denom_multiplier': 86400 * 7,
             'multiplier': 1 / (86400 * 7),
             'numer_scale_multiplier': 1, 'denom_scale_multiplier': 1,
             'scale_multiplier': 1,
             'numer_unit_class': None, 'denom_unit_class': 'time',
             'unit_class': None,
             'numer_primary_unit': 'Foobity', 'denom_primary_unit': 's',
             'primary_unit': 'Foobity/s',
             'numer_base_unit': 'Foobity', 'denom_base_unit': 'w',
             'base_unit': 'Foobity/w'})

    def test_unparseable(self):
        self.assertDictEqual(
            unitconv.parse_unitname('/w'),
            {'multiplier': 1, 'unit_class': None, 'primary_unit': '/w',
             'base_unit': '/w'})

        self.assertDictEqual(
            unitconv.parse_unitname('/'),
            {'multiplier': 1, 'unit_class': None, 'primary_unit': '/',
             'base_unit': '/'})

        self.assertDictEqual(
            unitconv.parse_unitname('a/b/c'),
            {'multiplier': 1, 'unit_class': None, 'primary_unit': 'a/b/c',
             'base_unit': 'a/b/c'})

        self.assertDictEqual(
            unitconv.parse_unitname(''),
            {'multiplier': 1, 'unit_class': None, 'primary_unit': '',
             'base_unit': ''})


def run_scenario(user_asked_for, data_exists_as, allow_derivation=True,
                 allow_integration=False, allow_prefixes_in_denominator=False,
                 round_result=6):
    userunit = unitconv.parse_unitname(user_asked_for, fold_scale_prefix=False)
    prefixclass = unitconv.prefix_class_for(userunit['scale_multiplier'])
    use_unit = userunit['base_unit']
    compatibles = unitconv.determine_compatible_units(
            allow_derivation=allow_derivation,
            allow_integration=allow_integration,
            allow_prefixes_in_denominator=allow_prefixes_in_denominator,
            **userunit)
    try:
        scale, extra_op = compatibles[data_exists_as]
    except KeyError:
        return
    if round_result is not None:
        scale = round(scale, round_result)
    return (data_exists_as, use_unit, scale, extra_op, prefixclass)


class TestDetermineCompatible(unittest.TestCase):
    def test_compatible_to_simple_primary_type(self):
        all_time_units = [pair[0] for pair in unitconv.unit_classes_by_name['time']]
        u = unitconv.determine_compatible_units('s', 'time', allow_integration=False)
        compatunits = u.keys()

        for timeunit in all_time_units:
            self.assertIn(timeunit, compatunits)

        self.assertEqual(u['MM'], (60000000.0, None))
        self.assertEqual(u['h'], (3600.0, None))

        self.assertEqual([extra_op for (_multiplier, extra_op) in u.values()],
                         [None] * len(u))

    def test_allow_derivation(self):
        u = unitconv.determine_compatible_units('b', 'datasize', 1, 's', 'time', allow_integration=False)
        self.assertEqual(u['b'], (1.0, 'derive'))
        self.assertEqual(u['B'], (8.0, 'derive'))
        self.assertEqual(u['b/s'], (1.0, None))
        self.assertAlmostEqual(u['B/d'][0], 9.26e-05)
        self.assertIsNone(u['B/d'][1])
        self.assertNotIn('h', u)

    def test_allow_integration(self):
        u = unitconv.determine_compatible_units('Eggnog', None, 0.125, allow_integration=True)
        self.assertEqual(u['Eggnog'], (8.0, None))
        self.assertAlmostEqual(u['Eggnog/h'][0], 0.0022222)
        self.assertEqual(u['Eggnog/h'][1], 'integrate')
        self.assertNotIn('derive', [extra_op for (_multiplier, extra_op) in u.values()])


class TestUnitconv(unittest.TestCase):
    # in the comments explaining results, X(t) represents a data series in
    # graphite with the "data_exists_as" unit, and Y(t) represents the data
    # series we want to graph, in the "user_asked_for" unit. the results of
    # run_scenario should give the necessary steps to convert X(t) to Y(t).

    def test_straightforward_conversion(self):
        self.assertEqual(run_scenario(user_asked_for='B', data_exists_as='b'),
                         ('b', 'B', 0.125, None, 'si'))
        # 0.125 * X(t) b = Y(t) B

    def test_esoteric_conversion_with_derive(self):
        self.assertEqual(run_scenario(user_asked_for='MiB/d', data_exists_as='kb'),
                         ('kb', 'B/d', 10800000, 'derive', 'binary'))
        # d(X(t) kb)/dt kb/s * 86400 s/d * 1B/8b * 1000 B/kB = Y(t) B/d
        # 86400 * 1000 / 8 = 10800000

    def test_unrecognized_unit_derive(self):
        self.assertEqual(run_scenario(user_asked_for='Cheese/w', data_exists_as='Cheese'),
                         ('Cheese', 'Cheese/w', 604800.0, 'derive', 'si'))
        # d(604800.0 * X(t) Cheese)/dt = Y(t) Cheese/w

    def test_integration(self):
        self.assertEqual(run_scenario(user_asked_for='b', data_exists_as='MB/s',
                                      allow_integration=True),
                         ('MB/s', 'b', 8000000.0, 'integrate', 'si'))
        # Integral(8000000.0 * X(t) MB/s, dt) = Y(t) b

    def test_conversion_between_unrecognized_units(self):
        self.assertIsNone(run_scenario(user_asked_for='pony', data_exists_as='coal'))
        # can't convert

    def test_conversion_between_units_of_different_class(self):
        self.assertIsNone(run_scenario(user_asked_for='d', data_exists_as='Mb'))
        # we know what they are but we can't convert days to megabits

    def test_straightforward_conversion_with_compound_units(self):
        self.assertEqual(run_scenario(user_asked_for='kb/s', data_exists_as='TiB/w'),
                         ('TiB/w', 'b/s', 14543804.600212, None, 'si'))
        # X(t) TiB/w * (1024**4 B/TiB) * (8 b/B) * (1 w/604800 s) = Y(t) kb/s
        # 1024**4 * 8 / 604800 =~ 14543804.600212

    def test_straightforward_conversion_between_iec_data_rates(self):
        self.assertEqual(run_scenario(user_asked_for='KiB', data_exists_as='TiB/w',
                                      allow_integration=True),
                         ('TiB/w', 'B', 1817975.575026, 'integrate', 'binary'))
        # X(t) TiB/w * (1024**4 B/TiB) * (1 w/604800 s) = Z(t) B/s
        # Integral(Z(t) KiB/s, dt) = Y(t) KiB

########NEW FILE########
__FILENAME__ = unitconv
"""
Conversions between simple units and simple combinations of units, with
an eye to monitoring metrics

See https://github.com/vimeo/graph-explorer/wiki/Units-%26-Prefixes

2013 paul cannon <paul@spacemonkey.com>
"""

from __future__ import division


si_multiplier_prefixes = (
    ('k', 1000 ** 1),
    ('M', 1000 ** 2),
    ('G', 1000 ** 3),
    ('T', 1000 ** 4),
    ('P', 1000 ** 5),

    # would be easy to support these, but probably better to keep these
    # letters available for other unit names (like "Ebb"? I don't know)
    #('E', 1000 ** 6),
    #('Z', 1000 ** 7),
    #('Y', 1000 ** 8),
)

iec_multiplier_prefixes = (
    ('Ki', 1024 ** 1),
    ('Mi', 1024 ** 2),
    ('Gi', 1024 ** 3),
    ('Ti', 1024 ** 4),
    ('Pi', 1024 ** 5),

    #('Ei', 1024 ** 6),
    #('Zi', 1024 ** 7),
    #('Yi', 1024 ** 8),
)

# make sure longer prefixes are first, since some of the shorter ones
# are prefixes of the longer ones, and we iterate over them with
# .startswith() tests. So if we checked for .startswith('M') first,
# we'd never see 'Mi'. etc
multiplier_prefixes = iec_multiplier_prefixes + si_multiplier_prefixes
multiplier_prefixes_with_empty = multiplier_prefixes + (('', 1),)


second = 1
minute = second * 60
hour = minute * 60
day = hour * 24
week = day * 7
month = day * 30

times = (
    ('s', second),
    ('M', minute),
    ('h', hour),
    ('d', day),
    ('w', week),
    ('mo', month)
)

bit = 1
byte = bit * 8

datasizes = (('b', bit), ('B', byte))

unit_classes = (('time', times), ('datasize', datasizes))
unit_classes_by_name = dict(unit_classes)


def is_power_of_2(n):
    return n & (n - 1) == 0


def prefix_class_for(multiplier):
    if multiplier > 1 \
            and (isinstance(multiplier, int) or multiplier.is_integer()) \
            and is_power_of_2(int(multiplier)):
        return 'binary'
    return 'si'


def identify_base_unit(unitname):
    for unitclassname, units in unit_classes:
        for unit_abbrev, multiplier in units:
            if unitname == unit_abbrev:
                return {'multiplier': multiplier, 'unit_class': unitclassname,
                        'primary_unit': units[0][0], 'base_unit': unitname}
    return {'multiplier': 1, 'unit_class': None, 'primary_unit': unitname,
            'base_unit': unitname}


def parse_simple_unitname(unitname, fold_scale_prefix=True):
    """
    Parse a single unit term with zero or more multiplier prefixes and one unit
    abbreviation, which may or may not be in a known unit class.

    Returns a dictionary with the following keys and values:

    'base_unit': the requested unit with any scaling prefix(es) stripped.

    'primary_unit': either the same as base_unit, or, if the unit is in one
    of the known unit classes, the primary unit for that unit class. E.g., if
    'h' (hour) were requested, the primary_unit would be 's' (second).

    'multiplier': a numeric value giving the multiplier from the primary_unit
    to the requested unit. For example, if 'kh' (kilo-hour) were requested,
    the multiplier would be 1000 * 3600 == 3600000, since a kilo-hour is
    3600000 seconds.

    'unit_class': if the requested unit was in one of the known unit classes,
    the name of that unit class. Otherwise None.

    If fold_scale_prefix is passed and false, any multiplicative factor
    imparted by a scaling prefix will be present in the key 'scale_multiplier'
    instead of being included with the 'multiplier' key.

    >>> parse_simple_unitname('Mb') == {
    ...     'multiplier': 1e6, 'unit_class': 'datasize',
    ...     'primary_unit': 'b', 'base_unit': 'b'}
    True
    >>> parse_simple_unitname('Mb', fold_scale_prefix=False) == {
    ...     'multiplier': 1, 'unit_class': 'datasize', 'primary_unit': 'b',
    ...     'scale_multiplier': 1e6, 'base_unit': 'b'}
    True
    >>> parse_simple_unitname('Err') == {
    ...     'multiplier': 1, 'unit_class': None, 'primary_unit': 'Err',
    ...     'base_unit': 'Err'}
    True
    >>> parse_simple_unitname('Kimo') == {   # "kibimonth"
    ...     'multiplier': 1024 * 86400 * 30, 'unit_class': 'time',
    ...     'primary_unit': 's', 'base_unit': 'mo'}
    True
    >>> parse_simple_unitname('MiG') == {
    ...     'multiplier': 1024 * 1024, 'unit_class': None,
    ...     'primary_unit': 'G', 'base_unit': 'G'}
    True
    >>> parse_simple_unitname('kk') == {  # "kilo-k", don't know what k unit is
    ...     'multiplier': 1000, 'unit_class': None, 'primary_unit': 'k',
    ...     'base_unit': 'k'}
    True
    >>> parse_simple_unitname('MM') == {  # "megaminute"
    ...     'multiplier': 60000000, 'unit_class': 'time',
    ...     'primary_unit': 's', 'base_unit': 'M'}
    True
    >>> parse_simple_unitname('Ki', fold_scale_prefix=False) == {
    ...     'multiplier': 1, 'unit_class': None, 'primary_unit': 'Ki',
    ...     'scale_multiplier': 1, 'base_unit': 'Ki'}
    True
    >>> parse_simple_unitname('') == {
    ...     'multiplier': 1, 'unit_class': None, 'primary_unit': '',
    ...     'base_unit': ''}
    True
    """

    # if the unitname is e.g. 'Pckt' we don't want to parse it as peta ckt's.
    # see https://github.com/vimeo/graph-explorer/wiki/Units-%26-Prefixes
    # for commonly used/standardized units
    special_units = ['Pckt', 'Msg', 'Metric', 'Ticket']

    for prefix, multiplier in multiplier_prefixes:
        if unitname.startswith(prefix) and unitname not in special_units and unitname != prefix:
            base = parse_simple_unitname(unitname[len(prefix):],
                                         fold_scale_prefix=fold_scale_prefix)
            if fold_scale_prefix:
                base['multiplier'] *= multiplier
            else:
                base['scale_multiplier'] *= multiplier
            return base
    base = identify_base_unit(unitname)
    if not fold_scale_prefix:
        base['scale_multiplier'] = 1
    return base


def parse_unitname(unitname, fold_scale_prefix=True):
    """
    Parse a unit term with at most two parts separated by / (a numerator and
    denominator, or just a plain term). Returns a structure identical to that
    returned by parse_simple_unitname(), but with extra fields for the
    numerator and for the denominator, if one exists.

    If there is a denominator, the 'base_unit', 'unit_class', 'primary_unit',
    'multiplier', and 'scale_multiplier' fields will be returned as
    combinations of the corresponding fields for the numerator and the
    denominator.

    >>> parse_unitname('GB/h') == {
    ...     'numer_multiplier': 1e9 * 9, 'denom_multiplier': 3600,
    ...     'multiplier': 1e9 * 8 / 3600,
    ...     'numer_unit_class': 'datasize', 'denom_unit_class': 'time',
    ...     'unit_class': 'datasize/time',
    ...     'numer_primary_unit': 'b', 'denom_primary_unit': 's',
    ...     'primary_unit': 'b/s',
    ...     'numer_base_unit': 'B', 'denom_base_unit': 'h',
    ...     'base_unit': 'B/h'}
    True
    """

    def copyfields(srcdict, nameprefix):
        fields = ('multiplier', 'unit_class', 'primary_unit', 'base_unit', 'scale_multiplier')
        for f in fields:
            try:
                unitstruct[nameprefix + f] = srcdict[f]
            except KeyError:
                pass

    parts = unitname.split('/', 2)
    if len(parts) > 2 or '' in parts:
        # surrender pathetically and just return the original unit
        return {'multiplier': 1, 'unit_class': None, 'primary_unit': unitname,
                'base_unit': unitname}
    unitstruct = parse_simple_unitname(parts[0], fold_scale_prefix=fold_scale_prefix)
    copyfields(unitstruct, 'numer_')
    if len(parts) == 2:
        denominator = parse_simple_unitname(parts[1], fold_scale_prefix=fold_scale_prefix)
        copyfields(denominator, 'denom_')
        unitstruct['multiplier'] /= denominator['multiplier']
        if unitstruct['unit_class'] is None or denominator['unit_class'] is None:
            unitstruct['unit_class'] = None
        else:
            unitstruct['unit_class'] += '/' + denominator['unit_class']
        unitstruct['primary_unit'] += '/' + denominator['primary_unit']
        unitstruct['base_unit'] += '/' + denominator['base_unit']
        if not fold_scale_prefix:
            unitstruct['scale_multiplier'] /= denominator['scale_multiplier']
    return unitstruct


def compat_simple_units_noprefix(unitclass, base_unit=None):
    try:
        return unit_classes_by_name[unitclass]
    except KeyError:
        return [(base_unit, 1)] if base_unit else []


def compat_simple_units(unitclass, base_unit=None):
    """
    >>> compat_simple_units('datasize', 'b')  # doctest: +NORMALIZE_WHITESPACE
    [('Kib', 1024), ('Mib', 1048576), ('Gib', 1073741824),
     ('Tib', 1099511627776), ('Pib', 1125899906842624),
     ('kb', 1000), ('Mb', 1000000), ('Gb', 1000000000),
     ('Tb', 1000000000000), ('Pb', 1000000000000000), ('b', 1),
     ('KiB', 8192), ('MiB', 8388608), ('GiB', 8589934592),
     ('TiB', 8796093022208), ('PiB', 9007199254740992),
     ('kB', 8000), ('MB', 8000000), ('GB', 8000000000),
     ('TB', 8000000000000), ('PB', 8000000000000000), ('B', 8)]
    """

    return [(prefix + base, pmult * bmult)
            for (base, bmult) in compat_simple_units_noprefix(unitclass, base_unit)
            for (prefix, pmult) in multiplier_prefixes_with_empty]


def determine_compatible_units(numer_base_unit, numer_unit_class, multiplier=1,
                               denom_base_unit=None, denom_unit_class=None,
                               allow_derivation=True, allow_integration=True,
                               allow_prefixes_in_denominator=False, **_other):
    """
    Return a dict mapping unit strings to 2-tuples. The keys are all the unit
    strings that we consider compatible with the requested unit. I.e., unit
    types that we think we can convert to or from the unit the user asked for.
    The 2-tuple values in the dict are the (multiplier, extra_op) information
    explaining how to convert data of the key-unit type to unit originally
    requested by the user.

    extra_op may be None, "derive", or "integrate".
    """

    # this multiplier was for converting the other direction, so we'll use
    # the reciprocal here
    scale = 1 / multiplier

    if allow_prefixes_in_denominator:
        denom_compat_units = compat_simple_units
    else:
        denom_compat_units = compat_simple_units_noprefix

    compat_numer = compat_simple_units(numer_unit_class, numer_base_unit)
    compat_denom = denom_compat_units(denom_unit_class, denom_base_unit)

    if denom_base_unit is None:
        # no denominator
        converteries = dict((unit, (scale * mult, None))
                            for (unit, mult) in compat_numer)
        if allow_integration:
            converteries.update(
                    (nunit + '/' + dunit, (scale * nmult / dmult, 'integrate'))
                    for (nunit, nmult) in compat_numer
                    for (dunit, dmult) in denom_compat_units('time'))
    elif allow_derivation and denom_unit_class == 'time':
        converteries = dict((unit, (scale * mult, 'derive'))
                            for (unit, mult) in compat_numer)
    else:
        converteries = {}

    converteries.update(
            (nunit + '/' + dunit, (scale * nmult / dmult, None))
            for (nunit, nmult) in compat_numer
            for (dunit, dmult) in compat_denom)

    return converteries


if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = validation
import sys
import os

sys.path = ["%s/%s" % (os.path.dirname(os.path.realpath(__file__)), 'wtforms')] + sys.path

from wtforms import Form, Field, BooleanField, StringField, validators, DecimalField, TextAreaField, HiddenField, IntegerField

from wtforms.validators import ValidationError


class is_None_or(object):
    def __init__(self, other, message=None):
        self.other = other
        if not message:
            message = u'Field must be None or %s' % other.message
        self.message = message
        self.other.message = message

    def __call__(self, form, field):
        if field.data is None:
            return True
        self.other(form, field)


class is_iterable(object):
    def __init__(self, message=None):
        if not message:
            message = u'Field must be an iterable'
        self.message = message

    def __call__(self, form, field):
        if not hasattr(field.data, '__iter__'):
            raise ValidationError(self.message)


class String_and(object):
    def __init__(self, other, message=None):
        self.other = other
        if not message:
            message = u'Field must be a string'
        self.message = message

    def __call__(self, form, field):
        if not isinstance(field.data, basestring):
            raise ValidationError(self.message)
        self.other(form, field)


# note don't use BooleanField, or wtforms will assume no data -> false
# use regular Field to catch when field not set (field.data will be None)
def isBool(form, field):
    if not isinstance(field.data, bool):
        raise ValidationError('Field must be a boolean')


class ConfigValidator(Form):
    listen_host = StringField('listen_host', [String_and(validators.Length(min=2))])
    listen_port = IntegerField('listen_port', [validators.NumberRange(0, 65535)])
    filename_metrics = StringField('filename_metrics', [String_and(validators.Length(min=2))])
    log_file = StringField('log_file', [String_and(validators.Length(min=2))])
    graphite_url_server = StringField('graphite_url_server', [String_and(validators.Length(min=2))])
    graphite_url_client = StringField('graphite_url_client', [String_and(validators.Length(min=2))])
    # the following 4 can be None.  validators.InputRequired gives weird errors
    graphite_username = StringField('graphite_username', [is_None_or(String_and(validators.Length(min=1)))])
    graphite_password = StringField('graphite_password', [is_None_or(String_and(validators.Length(min=1)))])
    # anthracite_url = StringField('anthracite_url', [is_None_or(String_and(validators.Length(min=1)))])
    anthracite_host = StringField('anthracite_host', [is_None_or(String_and(validators.Length(min=2)))])
    anthracite_port = IntegerField('anthracite_port', [is_None_or(validators.NumberRange(0, 65535))])
    anthracite_index = StringField('anthracite_index', [is_None_or(String_and(validators.Length(min=2)))])
    anthracite_add_url = StringField('anthracite_add_url', [is_None_or(String_and(validators.Length(min=1)))])
    locations_plugins_structured_metrics = Field('locations_plugins_structured_metrics', [is_iterable()])
    locations_dashboards = Field('locations_dashboards', [is_iterable()])
    es_host = StringField('es_host', [String_and(validators.Length(min=2))])
    es_port = IntegerField('es_port', [validators.NumberRange(0, 65535)])
    es_index = StringField('es_index', [String_and(validators.Length(min=2))])
    limit_es_metrics = IntegerField('limit_es_metrics', [validators.NumberRange(0, 1000000000000)])
    process_native_proto2 = Field('process_native_proto2', [isBool])
    alerting = Field('alerting', [isBool])
    alerting_db = StringField('alerting_db', [String_and(validators.Length(min=2))])
    alerting_smtp = StringField('alerting_smtp', [String_and(validators.Length(min=2))])
    # note: validation.Email() doesn't recognize strings like 'Graph Explorer <graph-explorer@example.com>'
    alerting_from = StringField('alerting_from', [String_and(validators.Length(min=2))])
    alert_backoff = IntegerField('alerting_backoff', [validators.NumberRange(1, 99999)])
    alerting_base_uri = StringField('alerting_base_uri', [String_and(validators.Length(min=2))])
    collectd_StoreRates = Field('collectd_StoreRates', [isBool])
    collectd_prefix = StringField('collectd_prefix', [String_and(validators.Length(min=2))])


class RuleAddForm(Form):
    alias = StringField('Alias')
    expr = TextAreaField('Expression', [validators.Length(min=5)])
    val_warn = DecimalField('Value warning')
    val_crit = DecimalField('Value critical')  # TODO at some point validate that val_warn != val_crit
    dest = StringField('Destination (1 or more comma-separated email addresses)', [validators.Length(min=2)])
    active = BooleanField('Active')
    warn_on_null = BooleanField('Warn on null')


class RuleEditForm(RuleAddForm):
    Id = HiddenField()

########NEW FILE########
