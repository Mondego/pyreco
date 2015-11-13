__FILENAME__ = models
"""
Models for the django-analytical Django application.

This application currently does not use models.
"""

########NEW FILE########
__FILENAME__ = analytical
"""
Analytical template tags and filters.
"""

from __future__ import absolute_import

import logging

from django import template
from django.template import Node, TemplateSyntaxError
from django.utils.importlib import import_module
from analytical.utils import AnalyticalException


TAG_LOCATIONS = ['head_top', 'head_bottom', 'body_top', 'body_bottom']
TAG_POSITIONS = ['first', None, 'last']
TAG_MODULES = [
    'analytical.chartbeat',
    'analytical.clickmap',
    'analytical.clicky',
    'analytical.crazy_egg',
    'analytical.gauges',
    'analytical.google_analytics',
    'analytical.gosquared',
    'analytical.hubspot',
    'analytical.intercom',
    'analytical.kiss_insights',
    'analytical.kiss_metrics',
    'analytical.mixpanel',
    'analytical.olark',
    'analytical.optimizely',
    'analytical.performable',
    'analytical.reinvigorate',
    'analytical.snapengage',
    'analytical.spring_metrics',
    'analytical.uservoice',
    'analytical.woopra',
]


logger = logging.getLogger(__name__)
register = template.Library()


def _location_tag(location):
    def analytical_tag(parser, token):
        bits = token.split_contents()
        if len(bits) > 1:
            raise TemplateSyntaxError("'%s' tag takes no arguments" % bits[0])
        return AnalyticalNode(location)
    return analytical_tag

for loc in TAG_LOCATIONS:
    register.tag('analytical_%s' % loc, _location_tag(loc))


class AnalyticalNode(Node):
    def __init__(self, location):
        self.nodes = [node_cls() for node_cls in template_nodes[location]]

    def render(self, context):
        return "".join([node.render(context) for node in self.nodes])


def _load_template_nodes():
    template_nodes = dict((l, dict((p, []) for p in TAG_POSITIONS))
            for l in TAG_LOCATIONS)
    def add_node_cls(location, node, position=None):
        template_nodes[location][position].append(node)
    for path in TAG_MODULES:
        module = _import_tag_module(path)
        try:
            module.contribute_to_analytical(add_node_cls)
        except AnalyticalException, e:
            logger.debug("not loading tags from '%s': %s", path, e)
    for location in TAG_LOCATIONS:
        template_nodes[location] = sum((template_nodes[location][p]
                for p in TAG_POSITIONS), [])
    return template_nodes

def _import_tag_module(path):
    app_name, lib_name = path.rsplit('.', 1)
    return import_module("%s.templatetags.%s" % (app_name, lib_name))

template_nodes = _load_template_nodes()

########NEW FILE########
__FILENAME__ = chartbeat
"""
Chartbeat template tags and filters.
"""

from __future__ import absolute_import

import json
import re

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import is_internal_ip, disable_html, get_required_setting


USER_ID_RE = re.compile(r'^\d+$')
INIT_CODE = """<script type="text/javascript">var _sf_startpt=(new Date()).getTime()</script>"""
SETUP_CODE = """
    <script type="text/javascript">
      var _sf_async_config=%(config)s;
      (function(){
        function loadChartbeat() {
          window._sf_endpt=(new Date()).getTime();
          var e = document.createElement('script');
          e.setAttribute('language', 'javascript');
          e.setAttribute('type', 'text/javascript');
          e.setAttribute('src',
             (("https:" == document.location.protocol) ? "https://a248.e.akamai.net/chartbeat.download.akamai.com/102508/" : "http://static.chartbeat.com/") +
             "js/chartbeat.js");
          document.body.appendChild(e);
        }
        var oldonload = window.onload;
        window.onload = (typeof window.onload != 'function') ?
           loadChartbeat : function() { oldonload(); loadChartbeat(); };
      })();
    </script>
"""
DOMAIN_CONTEXT_KEY = 'chartbeat_domain'


register = Library()


@register.tag
def chartbeat_top(parser, token):
    """
    Top Chartbeat template tag.

    Render the top Javascript code for Chartbeat.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return ChartbeatTopNode()

class ChartbeatTopNode(Node):
    def render(self, context):
        if is_internal_ip(context):
            return disable_html(INIT_CODE, "Chartbeat")
        return INIT_CODE


@register.tag
def chartbeat_bottom(parser, token):
    """
    Bottom Chartbeat template tag.

    Render the bottom Javascript code for Chartbeat.  You must supply
    your Chartbeat User ID (as a string) in the ``CHARTBEAT_USER_ID``
    setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return ChartbeatBottomNode()

class ChartbeatBottomNode(Node):
    def __init__(self):
        self.user_id = get_required_setting('CHARTBEAT_USER_ID', USER_ID_RE,
                "must be (a string containing) a number")

    def render(self, context):
        config = {'uid': self.user_id}
        domain = _get_domain(context)
        if domain is not None:
            config['domain'] = domain
        html = SETUP_CODE % {'config': json.dumps(config, sort_keys=True)}
        if is_internal_ip(context, 'CHARTBEAT'):
            html = disable_html(html, 'Chartbeat')
        return html


def contribute_to_analytical(add_node):
    ChartbeatBottomNode()  # ensure properly configured
    add_node('head_top', ChartbeatTopNode, 'first')
    add_node('body_bottom', ChartbeatBottomNode, 'last')


def _get_domain(context):
    domain = context.get(DOMAIN_CONTEXT_KEY)

    if domain is not None:
        return domain
    else:
        if 'django.contrib.sites' not in settings.INSTALLED_APPS:
            return
        elif getattr(settings, 'CHARTBEAT_AUTO_DOMAIN', True):
            try:
                return Site.objects.get_current().domain
            except (ImproperlyConfigured, Site.DoesNotExist): #pylint: disable=E1101
                return

########NEW FILE########
__FILENAME__ = clickmap
"""
Clickmap template tags and filters.
"""

from __future__ import absolute_import

import re

from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import get_identity, is_internal_ip, disable_html, get_required_setting


CLICKMAP_TRACKER_ID_RE = re.compile(r'^\d+$')
TRACKING_CODE = """
    <script type="text/javascript">
    var clickmapConfig = {tracker: '%(tracker_id)', version:'2'};
    window.clickmapAsyncInit = function(){ __clickmap.init(clickmapConfig); };
    (function() { var _cmf = document.createElement('script'); _cmf.async = true;
    _cmf.src = document.location.protocol + '//www.clickmap.ch/tracker.js?t=';
    _cmf.src += clickmapConfig.tracker; _cmf.id += 'clickmap_tracker';
    _cmf.src += '&v='+clickmapConfig.version+'&now='+(new Date().getTime());
    if (document.getElementById('clickmap_tracker')==null) {
    document.getElementsByTagName('head')[0].appendChild(_cmf); }}());
    </script>
"""

register = Library()


@register.tag
def clickmap(parser, token):
    """
    Clickmap tracker template tag.

    Renders Javascript code to track page visits.  You must supply
    your clickmap tracker ID (as a string) in the ``CLICKMAP_TRACKER_ID``
    setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return ClickmapNode()


class ClickmapNode(Node):
    def __init__(self):
        self.tracker_id = get_required_setting('CLICKMAP_TRACKER_ID',
                CLICKMAP_TRACKER_ID_RE,
                "must be a (string containing) a number")

    def render(self, context):
        html = TRACKING_CODE % {'portal_id': self.portal_id,
                'domain': self.domain}
        if is_internal_ip(context, 'CLICKMAP'):
            html = disable_html(html, 'Clickmap')
        return html


def contribute_to_analytical(add_node):
    ClickmapNode()  # ensure properly configured
    add_node('body_bottom', ClickmapNode)

########NEW FILE########
__FILENAME__ = clicky
"""
Clicky template tags and filters.
"""

from __future__ import absolute_import

import json
import re

from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import get_identity, is_internal_ip, disable_html, \
        get_required_setting


SITE_ID_RE = re.compile(r'^\d+$')
TRACKING_CODE = """
    <script type="text/javascript">
    var clicky = { log: function(){ return; }, goal: function(){ return; }};
    var clicky_site_ids = clicky_site_ids || [];
    clicky_site_ids.push(%(site_id)s);
    var clicky_custom = %(custom)s;
    (function() {
      var s = document.createElement('script');
      s.type = 'text/javascript';
      s.async = true;
      s.src = '//static.getclicky.com/js';
      ( document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0] ).appendChild( s );
    })();
    </script>
    <noscript><p><img alt="Clicky" width="1" height="1" src="//in.getclicky.com/%(site_id)sns.gif" /></p></noscript>
"""


register = Library()


@register.tag
def clicky(parser, token):
    """
    Clicky tracking template tag.

    Renders Javascript code to track page visits.  You must supply
    your Clicky Site ID (as a string) in the ``CLICKY_SITE_ID``
    setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return ClickyNode()

class ClickyNode(Node):
    def __init__(self):
        self.site_id = get_required_setting('CLICKY_SITE_ID', SITE_ID_RE,
                "must be a (string containing) a number")

    def render(self, context):
        custom = {}
        for dict_ in context:
            for var, val in dict_.items():
                if var.startswith('clicky_'):
                    custom[var[7:]] = val
        if 'username' not in custom.get('session', {}):
            identity = get_identity(context, 'clicky')
            if identity is not None:
                custom.setdefault('session', {})['username'] = identity

        html = TRACKING_CODE % {'site_id': self.site_id,
                'custom': json.dumps(custom, sort_keys=True)}
        if is_internal_ip(context, 'CLICKY'):
            html = disable_html(html, 'Clicky')
        return html


def contribute_to_analytical(add_node):
    ClickyNode()  # ensure properly configured
    add_node('body_bottom', ClickyNode)

########NEW FILE########
__FILENAME__ = crazy_egg
"""
Crazy Egg template tags and filters.
"""

from __future__ import absolute_import

import re

from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import is_internal_ip, disable_html, get_required_setting


ACCOUNT_NUMBER_RE = re.compile(r'^\d+$')
SETUP_CODE = """<script type="text/javascript" src="//dnn506yrbagrg.cloudfront.net/pages/scripts/%(account_nr_1)s/%(account_nr_2)s.js"></script>"""
USERVAR_CODE = "CE2.set(%(varnr)d, '%(value)s');"


register = Library()


@register.tag
def crazy_egg(parser, token):
    """
    Crazy Egg tracking template tag.

    Renders Javascript code to track page clicks.  You must supply
    your Crazy Egg account number (as a string) in the
    ``CRAZY_EGG_ACCOUNT_NUMBER`` setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return CrazyEggNode()

class CrazyEggNode(Node):
    def __init__(self):
        self.account_nr = get_required_setting('CRAZY_EGG_ACCOUNT_NUMBER',
                ACCOUNT_NUMBER_RE, "must be (a string containing) a number")

    def render(self, context):
        html = SETUP_CODE % {'account_nr_1': self.account_nr[:4],
            'account_nr_2': self.account_nr[4:]}
        values = (context.get('crazy_egg_var%d' % i) for i in range(1, 6))
        vars = [(i, v) for i, v in enumerate(values, 1) if v is not None]
        if vars:
            js = " ".join(USERVAR_CODE % {'varnr': varnr, 'value': value}
                        for (varnr, value) in vars)
            html = '%s\n<script type="text/javascript">%s</script>' \
                    % (html, js)
        if is_internal_ip(context, 'CRAZY_EGG'):
            html = disable_html(html, 'Crazy Egg')
        return html


def contribute_to_analytical(add_node):
    CrazyEggNode()  # ensure properly configured
    add_node('body_bottom', CrazyEggNode)

########NEW FILE########
__FILENAME__ = gauges
"""
Gaug.es template tags and filters.
"""

from __future__ import absolute_import

import re

from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import is_internal_ip, disable_html, get_required_setting

SITE_ID_RE = re.compile(r'[\da-f]+$')
TRACKING_CODE = """
    <script type="text/javascript">
      var _gauges = _gauges || [];
      (function() {
        var t   = document.createElement('script');
        t.type  = 'text/javascript';
        t.async = true;
        t.id    = 'gauges-tracker';
        t.setAttribute('data-site-id', '%(site_id)s');
        t.src = '//secure.gaug.es/track.js';
        var s = document.getElementsByTagName('script')[0];
        s.parentNode.insertBefore(t, s);
      })();
    </script>
"""

register = Library()


@register.tag
def gauges(parser, token):
    """
    Gaug.es template tag.

    Renders Javascript code to gaug.es testing.  You must supply
    your Site ID account number in the ``GAUGES_SITE_ID``
    setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return GaugesNode()


class GaugesNode(Node):
    def __init__(self):
        self.site_id = get_required_setting(
                'GAUGES_SITE_ID', SITE_ID_RE,
                "must be a string looking like 'XXXXXXX'")

    def render(self, context):
        html = TRACKING_CODE % {'site_id': self.site_id}
        if is_internal_ip(context, 'GAUGES'):
            html = disable_html(html, 'Gauges')
        return html


def contribute_to_analytical(add_node):
    GaugesNode()
    add_node('head_bottom', GaugesNode)

########NEW FILE########
__FILENAME__ = google_analytics
"""
Google Analytics template tags and filters.
"""

from __future__ import absolute_import

import re

from django.conf import settings
from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import is_internal_ip, disable_html, \
        get_required_setting, get_domain, AnalyticalException

def enumerate(sequence, start=0):
    """Copy of the Python 2.6 `enumerate` builtin for compatibility."""
    n = start
    for elem in sequence:
        yield n, elem
        n += 1


TRACK_SINGLE_DOMAIN = 1
TRACK_MULTIPLE_SUBDOMAINS = 2
TRACK_MULTIPLE_DOMAINS = 3

SCOPE_VISITOR = 1
SCOPE_SESSION = 2
SCOPE_PAGE = 3

PROPERTY_ID_RE = re.compile(r'^UA-\d+-\d+$')
SETUP_CODE = """
    <script type="text/javascript">

      var _gaq = _gaq || [];
      _gaq.push(['_setAccount', '%(property_id)s']);
      _gaq.push(['_trackPageview']);
      %(commands)s
      (function() {
        var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
        ga.src = ('https:' == document.location.protocol ? %(source_scheme)s) + %(source_url)s;
        var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
      })();

    </script>
"""
DOMAIN_CODE = "_gaq.push(['_setDomainName', '%s']);"
NO_ALLOW_HASH_CODE = "_gaq.push(['_setAllowHash', false]);"
ALLOW_LINKER_CODE = "_gaq.push(['_setAllowLinker', true]);"
CUSTOM_VAR_CODE = "_gaq.push(['_setCustomVar', %(index)s, '%(name)s', " \
        "'%(value)s', %(scope)s]);"
SITE_SPEED_CODE = "_gaq.push(['_trackPageLoadTime']);"
ANONYMIZE_IP_CODE = "_gaq.push (['_gat._anonymizeIp']);"
DEFAULT_SOURCE = ("'https://ssl' : 'http://www'", "'.google-analytics.com/ga.js'")
DISPLAY_ADVERTISING_SOURCE = ("'https://' : 'http://'", "'stats.g.doubleclick.net/dc.js'")

register = Library()

@register.tag
def google_analytics(parser, token):
    """
    Google Analytics tracking template tag.

    Renders Javascript code to track page visits.  You must supply
    your website property ID (as a string) in the
    ``GOOGLE_ANALYTICS_PROPERTY_ID`` setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return GoogleAnalyticsNode()

class GoogleAnalyticsNode(Node):
    def __init__(self):
        self.property_id = get_required_setting(
                'GOOGLE_ANALYTICS_PROPERTY_ID', PROPERTY_ID_RE,
                "must be a string looking like 'UA-XXXXXX-Y'")

    def render(self, context):
        commands = self._get_domain_commands(context)
        commands.extend(self._get_custom_var_commands(context))
        commands.extend(self._get_other_commands(context))
        if getattr(settings, 'GOOGLE_ANALYTICS_DISPLAY_ADVERTISING', False):
            source = DISPLAY_ADVERTISING_SOURCE
        else:
            source = DEFAULT_SOURCE
        html = SETUP_CODE % {'property_id': self.property_id,
                             'commands': " ".join(commands),
                             'source_scheme': source[0],
                             'source_url': source[1]}
        if is_internal_ip(context, 'GOOGLE_ANALYTICS'):
            html = disable_html(html, 'Google Analytics')
        return html

    def _get_domain_commands(self, context):
        commands = []
        tracking_type = getattr(settings, 'GOOGLE_ANALYTICS_TRACKING_STYLE',
                TRACK_SINGLE_DOMAIN)
        if tracking_type == TRACK_SINGLE_DOMAIN:
            pass
        else:
            domain = get_domain(context, 'google_analytics')
            if domain is None:
                raise AnalyticalException("tracking multiple domains with"
                        " Google Analytics requires a domain name")
            commands.append(DOMAIN_CODE % domain)
            commands.append(NO_ALLOW_HASH_CODE)
            if tracking_type == TRACK_MULTIPLE_DOMAINS:
                commands.append(ALLOW_LINKER_CODE)
        return commands

    def _get_custom_var_commands(self, context):
        values = (context.get('google_analytics_var%s' % i)
                for i in range(1, 6))
        vars = [(i, v) for i, v in enumerate(values, 1) if v is not None]
        commands = []
        for index, var in vars:
            name = var[0]
            value = var[1]
            try:
                scope = var[2]
            except IndexError:
                scope = SCOPE_PAGE
            commands.append(CUSTOM_VAR_CODE % locals())
        return commands

    def _get_other_commands(self, context):
        commands = []
        if getattr(settings, 'GOOGLE_ANALYTICS_SITE_SPEED', False):
            commands.append(SITE_SPEED_CODE)
        if getattr(settings, 'GOOGLE_ANALYTICS_ANONYMIZE_IP', False):
            commands.append(ANONYMIZE_IP_CODE)
        return commands

def contribute_to_analytical(add_node):
    GoogleAnalyticsNode()  # ensure properly configured
    add_node('head_bottom', GoogleAnalyticsNode)

########NEW FILE########
__FILENAME__ = gosquared
"""
GoSquared template tags and filters.
"""

from __future__ import absolute_import

import re

from django.conf import settings
from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import get_identity, get_user_from_context, \
        is_internal_ip, disable_html, get_required_setting


TOKEN_RE = re.compile(r'^\S+-\S+-\S+$')
TRACKING_CODE = """
    <script type="text/javascript">
      var GoSquared={};
      %(config)s
      (function(w){
        function gs(){
          w._gstc_lt=+(new Date); var d=document;
          var g = d.createElement("script"); g.type = "text/javascript"; g.async = true; g.src = "//d1l6p2sc9645hc.cloudfront.net/tracker.js";
          var s = d.getElementsByTagName("script")[0]; s.parentNode.insertBefore(g, s);
        }
        w.addEventListener?w.addEventListener("load",gs,false):w.attachEvent("onload",gs);
      })(window);
    </script>
"""
TOKEN_CODE = 'GoSquared.acct = "%s";'
IDENTIFY_CODE = 'GoSquared.UserName = "%s";'


register = Library()


@register.tag
def gosquared(parser, token):
    """
    GoSquared tracking template tag.

    Renders Javascript code to track page visits.  You must supply
    your GoSquared site token in the ``GOSQUARED_SITE_TOKEN`` setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return GoSquaredNode()

class GoSquaredNode(Node):
    def __init__(self):
        self.site_token = get_required_setting('GOSQUARED_SITE_TOKEN', TOKEN_RE,
                "must be a string looking like XXX-XXXXXX-X")

    def render(self, context):
        configs = [TOKEN_CODE % self.site_token]
        identity = get_identity(context, 'gosquared', self._identify)
        if identity:
            configs.append(IDENTIFY_CODE % identity)
        html = TRACKING_CODE % {
            'token': self.site_token,
            'config': ' '.join(configs),
        }
        if is_internal_ip(context, 'GOSQUARED'):
            html = disable_html(html, 'GoSquared')
        return html

    def _identify(self, user):
        name = user.get_full_name()
        if not name:
            name = user.username
        return name


def contribute_to_analytical(add_node):
    GoSquaredNode()  # ensure properly configured
    add_node('body_bottom', GoSquaredNode)

########NEW FILE########
__FILENAME__ = hubspot
"""
HubSpot template tags and filters.
"""

from __future__ import absolute_import

import re

from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import is_internal_ip, disable_html, get_required_setting


PORTAL_ID_RE = re.compile(r'^\d+$')
DOMAIN_RE = re.compile(r'^[\w.-]+$')
TRACKING_CODE = """
    <script type="text/javascript" language="javascript">
      var hs_portalid = %(portal_id)s;
      var hs_salog_version = "2.00";
      var hs_ppa = "%(domain)s";
      document.write(unescape("%%3Cscript src='" + document.location.protocol + "//" + hs_ppa + "/salog.js.aspx' type='text/javascript'%%3E%%3C/script%%3E"));
    </script>
"""


register = Library()


@register.tag
def hubspot(parser, token):
    """
    HubSpot tracking template tag.

    Renders Javascript code to track page visits.  You must supply
    your portal ID (as a string) in the ``HUBSPOT_PORTAL_ID`` setting,
    and the website domain in ``HUBSPOT_DOMAIN``.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return HubSpotNode()

class HubSpotNode(Node):
    def __init__(self):
        self.portal_id = get_required_setting('HUBSPOT_PORTAL_ID',
                PORTAL_ID_RE, "must be a (string containing a) number")
        self.domain = get_required_setting('HUBSPOT_DOMAIN',
                DOMAIN_RE, "must be an internet domain name")

    def render(self, context):
        html = TRACKING_CODE % {'portal_id': self.portal_id,
                'domain': self.domain}
        if is_internal_ip(context, 'HUBSPOT'):
            html = disable_html(html, 'HubSpot')
        return html


def contribute_to_analytical(add_node):
    HubSpotNode()  # ensure properly configured
    add_node('body_bottom', HubSpotNode)

########NEW FILE########
__FILENAME__ = intercom
"""
intercom.io template tags and filters.
"""

from __future__ import absolute_import
import json
import time
import re

from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import disable_html, get_required_setting, is_internal_ip,\
                            get_user_from_context, get_identity

APP_ID_RE = re.compile(r'[\da-f]+$')
TRACKING_CODE = """
<script id="IntercomSettingsScriptTag">
  window.intercomSettings = %(settings_json)s;
</script>
<script>(function(){var w=window;var ic=w.Intercom;if(typeof ic==="function"){ic('reattach_activator');ic('update',intercomSettings);}else{var d=document;var i=function(){i.c(arguments)};i.q=[];i.c=function(args){i.q.push(args)};w.Intercom=i;function l(){var s=d.createElement('script');s.type='text/javascript';s.async=true;s.src='https://static.intercomcdn.com/intercom.v1.js';var x=d.getElementsByTagName('script')[0];x.parentNode.insertBefore(s,x);}if(w.attachEvent){w.attachEvent('onload',l);}else{w.addEventListener('load',l,false);}}})()</script>
"""

register = Library()


@register.tag
def intercom(parser, token):
    """
    Intercom.io template tag.

    Renders Javascript code to intercom.io testing.  You must supply
    your APP ID account number in the ``INTERCOM_APP_ID``
    setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return IntercomNode()


class IntercomNode(Node):
    def __init__(self):
        self.app_id = get_required_setting(
                'INTERCOM_APP_ID', APP_ID_RE,
                "must be a string looking like 'XXXXXXX'")

    def _identify(self, user):
        name = user.get_full_name()
        if not name:
            name = user.username
        return name

    def _get_custom_attrs(self, context):
        vars = {}
        for dict_ in context:
            for var, val in dict_.items():
                if var.startswith('intercom_'):
                    vars[var[9:]] = val

        user = get_user_from_context(context)
        if user is not None and user.is_authenticated():
            if 'name' not in vars:
                vars['name'] = get_identity(context, 'intercom', self._identify, user)
            if 'email' not in vars and user.email:
                vars['email'] = user.email

            vars['created_at'] = int(time.mktime(user.date_joined.timetuple()))
        else:
            vars['created_at'] = None

        return vars

    def render(self, context):
        html = ""
        user = get_user_from_context(context)
        vars = self._get_custom_attrs(context)
        vars["app_id"] = self.app_id
        html = TRACKING_CODE % {"settings_json": json.dumps(vars, sort_keys=True)}
        
        if is_internal_ip(context, 'INTERCOM') or not user or not user.is_authenticated():
            # Intercom is disabled for non-logged in users.
            html = disable_html(html, 'Intercom')
        return html


def contribute_to_analytical(add_node):
    IntercomNode()
    add_node('body_bottom', IntercomNode)

########NEW FILE########
__FILENAME__ = kiss_insights
"""
KISSinsights template tags.
"""

from __future__ import absolute_import

import re

from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import get_identity, get_required_setting


ACCOUNT_NUMBER_RE = re.compile(r'^\d+$')
SITE_CODE_RE = re.compile(r'^[\w]+$')
SETUP_CODE = """
    <script type="text/javascript">var _kiq = _kiq || []; %(commands)s</script>
    <script type="text/javascript" src="//s3.amazonaws.com/ki.js/%(account_number)s/%(site_code)s.js" async="true"></script>
"""
IDENTIFY_CODE = "_kiq.push(['identify', '%s']);"
SHOW_SURVEY_CODE = "_kiq.push(['showSurvey', %s]);"
SHOW_SURVEY_CONTEXT_KEY = 'kiss_insights_show_survey'


register = Library()


@register.tag
def kiss_insights(parser, token):
    """
    KISSinsights set-up template tag.

    Renders Javascript code to set-up surveys.  You must supply
    your account number and site code in the
    ``KISS_INSIGHTS_ACCOUNT_NUMBER`` and ``KISS_INSIGHTS_SITE_CODE``
    settings.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return KissInsightsNode()

class KissInsightsNode(Node):
    def __init__(self):
        self.account_number = get_required_setting(
                'KISS_INSIGHTS_ACCOUNT_NUMBER', ACCOUNT_NUMBER_RE,
                "must be (a string containing) a number")
        self.site_code = get_required_setting('KISS_INSIGHTS_SITE_CODE',
                SITE_CODE_RE, "must be a string containing three characters")

    def render(self, context):
        commands = []
        identity = get_identity(context, 'kiss_insights')
        if identity is not None:
            commands.append(IDENTIFY_CODE % identity)
        try:
            commands.append(SHOW_SURVEY_CODE
                    % context[SHOW_SURVEY_CONTEXT_KEY])
        except KeyError:
            pass
        html = SETUP_CODE % {'account_number': self.account_number,
                'site_code': self.site_code, 'commands': " ".join(commands)}
        return html


def contribute_to_analytical(add_node):
    KissInsightsNode()  # ensure properly configured
    add_node('body_top', KissInsightsNode)

########NEW FILE########
__FILENAME__ = kiss_metrics
"""
KISSmetrics template tags.
"""

from __future__ import absolute_import

import json
import re

from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import is_internal_ip, disable_html, get_identity, \
        get_required_setting


API_KEY_RE = re.compile(r'^[0-9a-f]{40}$')
TRACKING_CODE = """
    <script type="text/javascript">
      var _kmq = _kmq || [];
      %(commands)s
      function _kms(u){
        setTimeout(function(){
          var s = document.createElement('script');
          s.type = 'text/javascript';
          s.async = true;
          s.src = u;
          var f = document.getElementsByTagName('script')[0];
          f.parentNode.insertBefore(s, f);
        }, 1);
      }
      _kms('//i.kissmetrics.com/i.js');
      _kms('//doug1izaerwt3.cloudfront.net/%(api_key)s.1.js');
    </script>
"""
IDENTIFY_CODE = "_kmq.push(['identify', '%s']);"
EVENT_CODE = "_kmq.push(['record', '%(name)s', %(properties)s]);"
PROPERTY_CODE = "_kmq.push(['set', %(properties)s]);"
ALIAS_CODE = "_kmq.push(['alias', '%s', '%s']);"

EVENT_CONTEXT_KEY = 'kiss_metrics_event'
PROPERTY_CONTEXT_KEY = 'kiss_metrics_properties'
ALIAS_CONTEXT_KEY = 'kiss_metrics_alias'

register = Library()


@register.tag
def kiss_metrics(parser, token):
    """
    KISSinsights tracking template tag.

    Renders Javascript code to track page visits.  You must supply
    your KISSmetrics API key in the ``KISS_METRICS_API_KEY``
    setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return KissMetricsNode()

class KissMetricsNode(Node):
    def __init__(self):
        self.api_key = get_required_setting('KISS_METRICS_API_KEY',
                API_KEY_RE,
                "must be a string containing a 40-digit hexadecimal number")

    def render(self, context):
        commands = []
        identity = get_identity(context, 'kiss_metrics')
        if identity is not None:
            commands.append(IDENTIFY_CODE % identity)
        try:
            properties = context[ALIAS_CONTEXT_KEY]
            key, value = properties.popitem()
            commands.append(ALIAS_CODE % (key,value))
        except KeyError:
            pass                         
        try:
            name, properties = context[EVENT_CONTEXT_KEY]
            commands.append(EVENT_CODE % {'name': name,
                    'properties': json.dumps(properties, sort_keys=True)})
        except KeyError:
            pass
        try:
            properties = context[PROPERTY_CONTEXT_KEY]
            commands.append(PROPERTY_CODE % {
                    'properties': json.dumps(properties, sort_keys=True)})
        except KeyError:
            pass
        html = TRACKING_CODE % {'api_key': self.api_key,
                'commands': " ".join(commands)}
        if is_internal_ip(context, 'KISS_METRICS'):
            html = disable_html(html, 'KISSmetrics')
        return html


def contribute_to_analytical(add_node):
    KissMetricsNode()  # ensure properly configured
    add_node('head_top', KissMetricsNode)

########NEW FILE########
__FILENAME__ = mixpanel
"""
Mixpanel template tags and filters.
"""

from __future__ import absolute_import

import json
import re

from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import is_internal_ip, disable_html, get_identity, \
        get_required_setting


MIXPANEL_API_TOKEN_RE = re.compile(r'^[0-9a-f]{32}$')
TRACKING_CODE = """
    <script type="text/javascript">(function(e,b){if(!b.__SV){var a,f,i,g;window.mixpanel=b;a=e.createElement("script");a.type="text/javascript";a.async=!0;a.src=("https:"===e.location.protocol?"https:":"http:")+'//cdn.mxpnl.com/libs/mixpanel-2.2.min.js';f=e.getElementsByTagName("script")[0];f.parentNode.insertBefore(a,f);b._i=[];b.init=function(a,e,d){function f(b,h){var a=h.split(".");2==a.length&&(b=b[a[0]],h=a[1]);b[h]=function(){b.push([h].concat(Array.prototype.slice.call(arguments,0)))}}var c=b;"undefined"!==
typeof d?c=b[d]=[]:d="mixpanel";c.people=c.people||[];c.toString=function(b){var a="mixpanel";"mixpanel"!==d&&(a+="."+d);b||(a+=" (stub)");return a};c.people.toString=function(){return c.toString(1)+".people (stub)"};i="disable track track_pageview track_links track_forms register register_once alias unregister identify name_tag set_config people.set people.increment people.append people.track_charge people.clear_charges people.delete_user".split(" ");for(g=0;g<i.length;g++)f(c,i[g]);b._i.push([a,
e,d])};b.__SV=1.2}})(document,window.mixpanel||[]);
    mixpanel.init('%(token)s');
    %(commands)s
    </script>
"""
IDENTIFY_CODE = "mixpanel.register_once({distinct_id: '%s'});"
EVENT_CODE = "mixpanel.track('%(name)s', %(properties)s);"
EVENT_CONTEXT_KEY = 'mixpanel_event'

register = Library()


@register.tag
def mixpanel(parser, token):
    """
    Mixpanel tracking template tag.

    Renders Javascript code to track page visits.  You must supply
    your Mixpanel token in the ``MIXPANEL_API_TOKEN`` setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return MixpanelNode()

class MixpanelNode(Node):
    def __init__(self):
        self.token = get_required_setting(
                'MIXPANEL_API_TOKEN', MIXPANEL_API_TOKEN_RE,
                "must be a string containing a 32-digit hexadecimal number")

    def render(self, context):
        commands = []
        identity = get_identity(context, 'mixpanel')
        if identity is not None:
            commands.append(IDENTIFY_CODE % identity)
        try:
            name, properties = context[EVENT_CONTEXT_KEY]
            commands.append(EVENT_CODE % {'name': name,
                    'properties': json.dumps(properties, sort_keys=True)})
        except KeyError:
            pass
        html = TRACKING_CODE % {'token': self.token,
                'commands': " ".join(commands)}
        if is_internal_ip(context, 'MIXPANEL'):
            html = disable_html(html, 'Mixpanel')
        return html


def contribute_to_analytical(add_node):
    MixpanelNode()  # ensure properly configured
    add_node('head_bottom', MixpanelNode)

########NEW FILE########
__FILENAME__ = olark
"""
Olark template tags.
"""

from __future__ import absolute_import

import json
import re

from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import get_identity, get_required_setting


SITE_ID_RE = re.compile(r'^\d+-\d+-\d+-\d+$')
SETUP_CODE = """
    <script type='text/javascript'>
      /*{literal}<![CDATA[*/ window.olark||(function(k){var g=window,j=document,a=g.location.protocol=="https:"?"https:":"http:",i=k.name,b="load",h="addEventListener";(function(){g[i]=function(){(c.s=c.s||[]).push(arguments)};var c=g[i]._={},f=k.methods.length;while(f--){(function(l){g[i][l]=function(){g[i]("call",l,arguments)}})(k.methods[f])}c.l=k.loader;c.i=arguments.callee;c.p={0:+new Date};c.P=function(l){c.p[l]=new Date-c.p[0]};function e(){c.P(b);g[i](b)}g[h]?g[h](b,e,false):g.attachEvent("on"+b,e);c.P(1);var d=j.createElement("script"),m=document.getElementsByTagName("script")[0];d.type="text/javascript";d.async=true;d.src=a+"//"+c.l;m.parentNode.insertBefore(d,m);c.P(2)})()})({loader:(function(a){return "static.olark.com/jsclient/loader1.js?ts="+(a?a[1]:(+new Date))})(document.cookie.match(/olarkld=([0-9]+)/)),name:"olark",methods:["configure","extend","declare","identify"]}); olark.identify('%(site_id)s');/*]]>{/literal}*/
      %(extra_code)s
    </script>
"""
NICKNAME_CODE = "olark('api.chat.updateVisitorNickname', {snippet: '%s'});"
NICKNAME_CONTEXT_KEY = 'olark_nickname'
STATUS_CODE = "olark('api.chat.updateVisitorStatus', {snippet: %s});"
STATUS_CONTEXT_KEY = 'olark_status'
MESSAGE_CODE = "olark.configure('locale.%(key)s', \"%(msg)s\");"
MESSAGE_KEYS = set(["welcome_title", "chatting_title", "unavailable_title",
        "busy_title", "away_message", "loading_title", "welcome_message",
        "busy_message", "chat_input_text", "name_input_text",
        "email_input_text", "offline_note_message", "send_button_text",
        "offline_note_thankyou_text", "offline_note_error_text",
        "offline_note_sending_text", "operator_is_typing_text",
        "operator_has_stopped_typing_text", "introduction_error_text",
        "introduction_messages", "introduction_submit_button_text"])

register = Library()


@register.tag
def olark(parser, token):
    """
    Olark set-up template tag.

    Renders Javascript code to set-up Olark chat.  You must supply
    your site ID in the ``OLARK_SITE_ID`` setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return OlarkNode()

class OlarkNode(Node):
    def __init__(self):
        self.site_id = get_required_setting('OLARK_SITE_ID', SITE_ID_RE,
                "must be a string looking like 'XXXX-XXX-XX-XXXX'")

    def render(self, context):
        extra_code = []
        try:
            extra_code.append(NICKNAME_CODE % context[NICKNAME_CONTEXT_KEY])
        except KeyError:
            identity = get_identity(context, 'olark', self._get_nickname)
            if identity is not None:
                extra_code.append(NICKNAME_CODE % identity)
        try:
            extra_code.append(STATUS_CODE %
                    json.dumps(context[STATUS_CONTEXT_KEY], sort_keys=True))
        except KeyError:
            pass
        extra_code.extend(self._get_configuration(context))
        html = SETUP_CODE % {'site_id': self.site_id,
                'extra_code': " ".join(extra_code)}
        return html

    def _get_nickname(self, user):
        name = user.get_full_name()
        if name:
            return "%s (%s)" % (name, user.username)
        else:
            return user.username

    def _get_configuration(self, context):
        code = []
        for dict_ in context:
            for var, val in dict_.items():
                if var.startswith('olark_'):
                    key = var[6:]
                    if key in MESSAGE_KEYS:
                        code.append(MESSAGE_CODE % {'key': key, 'msg': val})
        return code


def contribute_to_analytical(add_node):
    OlarkNode()  # ensure properly configured
    add_node('body_bottom', OlarkNode)

########NEW FILE########
__FILENAME__ = optimizely
"""
Optimizely template tags and filters.
"""

from __future__ import absolute_import

import re

from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import is_internal_ip, disable_html, get_required_setting


ACCOUNT_NUMBER_RE = re.compile(r'^\d+$')
SETUP_CODE = """<script src="//cdn.optimizely.com/js/%(account_number)s.js"></script>"""


register = Library()


@register.tag
def optimizely(parser, token):
    """
    Optimizely template tag.

    Renders Javascript code to set-up A/B testing.  You must supply
    your Optimizely account number in the ``OPTIMIZELY_ACCOUNT_NUMBER``
    setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return OptimizelyNode()


class OptimizelyNode(Node):
    def __init__(self):
        self.account_number = get_required_setting(
                'OPTIMIZELY_ACCOUNT_NUMBER', ACCOUNT_NUMBER_RE,
                "must be a string looking like 'XXXXXXX'")

    def render(self, context):
        html = SETUP_CODE % {'account_number': self.account_number}
        if is_internal_ip(context, 'OPTIMIZELY'):
            html = disable_html(html, 'Optimizely')
        return html


def contribute_to_analytical(add_node):
    OptimizelyNode()  # ensure properly configured
    add_node('head_top', OptimizelyNode)

########NEW FILE########
__FILENAME__ = performable
"""
Performable template tags and filters.
"""

from __future__ import absolute_import

import re

from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import is_internal_ip, disable_html, get_identity, \
        get_required_setting


API_KEY_RE = re.compile(r'^\w+$')
SETUP_CODE = """
    <script src="//d1nu2rn22elx8m.cloudfront.net/performable/pax/%(api_key)s.js" type="text/javascript"></script>
"""
IDENTIFY_CODE = """
    <script type="text/javascript">
      var _paq = _paq || [];
      _paq.push(["identify", {identity: "%s"}]);
    </script>
"""
EMBED_CODE = """
    <script type="text/javascript" src="//d1nu2rn22elx8m.cloudfront.net/performable/embed/page.js"></script>
    <script type="text/javascript">
      (function() {
      var $f = new PerformableEmbed();
      $f.initialize({'host': '%(hostname)s', 'page': '%(page_id)s'});
      $f.write();
    })()
    </script>
"""

register = Library()


@register.tag
def performable(parser, token):
    """
    Performable template tag.

    Renders Javascript code to set-up Performable tracking.  You must
    supply your Performable API key in the ``PERFORMABLE_API_KEY``
    setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return PerformableNode()

class PerformableNode(Node):
    def __init__(self):
        self.api_key = get_required_setting('PERFORMABLE_API_KEY', API_KEY_RE,
                "must be a string looking like 'XXXXX'")

    def render(self, context):
        html = SETUP_CODE % {'api_key': self.api_key}
        identity = get_identity(context, 'performable')
        if identity is not None:
            html = "%s%s" % (IDENTIFY_CODE % identity, html)
        if is_internal_ip(context, 'PERFORMABLE'):
            html = disable_html(html, 'Performable')
        return html


@register.simple_tag
def performable_embed(hostname, page_id):
    """
    Include a Performable landing page.
    """
    return EMBED_CODE % {'hostname': hostname, 'page_id': page_id}


def contribute_to_analytical(add_node):
    PerformableNode()  # ensure properly configured
    add_node('body_bottom', PerformableNode)

########NEW FILE########
__FILENAME__ = reinvigorate
"""
Reinvigorate template tags and filters.
"""

from __future__ import absolute_import

import json
import re

from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import get_identity, is_internal_ip, disable_html, \
        get_required_setting


TRACKING_ID_RE = re.compile(r'^[\w\d]+-[\w\d]+$')
TRACKING_CODE = """
    <script type="text/javascript">
      document.write(unescape("%%3Cscript src='" + (("https:" == document.location.protocol) ? "https://ssl-" : "http://") + "include.reinvigorate.net/re_.js' type='text/javascript'%%3E%%3C/script%%3E"));
    </script>
    <script type="text/javascript">
      try {
        %(tags)s
        reinvigorate.track("%(tracking_id)s");
      } catch(err) {}
    </script>
"""


register = Library()


@register.tag
def reinvigorate(parser, token):
    """
    Reinvigorate tracking template tag.

    Renders Javascript code to track page visits.  You must supply
    your Reinvigorate tracking ID (as a string) in the
    ``REINVIGORATE_TRACKING_ID`` setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return ReinvigorateNode()

class ReinvigorateNode(Node):
    def __init__(self):
        self.tracking_id = get_required_setting('REINVIGORATE_TRACKING_ID',
                TRACKING_ID_RE,
                "must be a string looking like XXXXX-XXXXXXXXXX")

    def render(self, context):
        re_vars = {}
        for dict_ in context:
            for var, val in dict_.items():
                if var.startswith('reinvigorate_'):
                    re_vars[var[13:]] = val
        if 'name' not in re_vars:
            identity = get_identity(context, 'reinvigorate',
                    lambda u: u.get_full_name())
            if identity is not None:
                re_vars['name'] = identity
        if 'context' not in re_vars:
            email = get_identity(context, 'reinvigorate', lambda u: u.email)
            if email is not None:
                re_vars['context'] = email
        tags = " ".join("var re_%s_tag = %s;" % (tag, json.dumps(value, sort_keys=True))
                for tag, value in re_vars.items())

        html = TRACKING_CODE % {'tracking_id': self.tracking_id,
                'tags': tags}
        if is_internal_ip(context, 'REINVIGORATE'):
            html = disable_html(html, 'Reinvigorate')
        return html


def contribute_to_analytical(add_node):
    ReinvigorateNode()  # ensure properly configured
    add_node('body_bottom', ReinvigorateNode)

########NEW FILE########
__FILENAME__ = snapengage
"""
SnapEngage template tags.
"""

from __future__ import absolute_import

import re

from django.conf import settings
from django.template import Library, Node, TemplateSyntaxError
from django.utils import translation

from analytical.utils import get_identity, get_required_setting


BUTTON_LOCATION_LEFT = 0
BUTTON_LOCATION_RIGHT = 1
BUTTON_LOCATION_TOP = 2
BUTTON_LOCATION_BOTTOM = 3

BUTTON_STYLE_NONE = 0
BUTTON_STYLE_DEFAULT = 1
BUTTON_STYLE_LIVE = 2

FORM_POSITION_TOP_LEFT = 'tl'
FORM_POSITION_TOP_RIGHT = 'tr'
FORM_POSITION_BOTTOM_LEFT = 'bl'
FORM_POSITION_BOTTOM_RIGHT = 'br'

WIDGET_ID_RE = re.compile(r'^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$')
SETUP_CODE = """
    <script type="text/javascript">
      document.write(unescape("%%3Cscript src='" + ((document.location.protocol=="https:")?"https://snapabug.appspot.com":"http://www.snapengage.com") + "/snapabug.js' type='text/javascript'%%3E%%3C/script%%3E"));</script><script type="text/javascript">
      %(settings_code)s
    </script>
"""
DOMAIN_CODE = 'SnapABug.setDomain("%s");'
SECURE_CONNECTION_CODE = 'SnapABug.setSecureConnexion();'
INIT_CODE = 'SnapABug.init("%s");'
ADDBUTTON_CODE = 'SnapABug.addButton("%(id)s","%(location)s","%(offset)s"%(dynamic_tail)s);'
SETBUTTON_CODE = 'SnapABug.setButton("%s");'
SETEMAIL_CODE = 'SnapABug.setUserEmail("%s"%s);'
SETLOCALE_CODE = 'SnapABug.setLocale("%s");'
FORM_POSITION_CODE = 'SnapABug.setChatFormPosition("%s");'
FORM_TOP_POSITION_CODE = 'SnapABug.setFormTopPosition(%d);'
BUTTONEFFECT_CODE = 'SnapABug.setButtonEffect("%s");'
DISABLE_OFFLINE_CODE = 'SnapABug.allowOffline(false);'
DISABLE_SCREENSHOT_CODE = 'SnapABug.allowScreenshot(false);'
DISABLE_OFFLINE_SCREENSHOT_CODE = 'SnapABug.showScreenshotOption(false);'
DISABLE_PROACTIVE_CHAT_CODE = 'SnapABug.allowProactiveChat(false);'
DISABLE_SOUNDS_CODE = 'SnapABug.allowChatSound(false);'

register = Library()


@register.tag
def snapengage(parser, token):
    """
    SnapEngage set-up template tag.

    Renders Javascript code to set-up SnapEngage chat.  You must supply
    your widget ID in the ``SNAPENGAGE_WIDGET_ID`` setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return SnapEngageNode()

class SnapEngageNode(Node):
    def __init__(self):
        self.widget_id = get_required_setting('SNAPENGAGE_WIDGET_ID',
                WIDGET_ID_RE, "must be a string looking like this: "
                    "'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX'")

    def render(self, context):
        settings_code = []

        domain = self._get_setting(context, 'snapengage_domain',
                'SNAPENGAGE_DOMAIN')
        if domain is not None:
            settings_code.append(DOMAIN_CODE % domain)

        secure_connection = self._get_setting(context,
                'snapengage_secure_connection', 'SNAPENGAGE_SECURE_CONNECTION',
                False)
        if secure_connection:
            settings_code.append(SECURE_CONNECTION_CODE)

        email = context.get('snapengage_email')
        if email is None:
            email = get_identity(context, 'snapengage', lambda u: u.email)
        if email is not None:
            if self._get_setting(context, 'snapengage_readonly_email',
                    'SNAPENGAGE_READONLY_EMAIL', False):
                readonly_tail = ',true'
            else:
                readonly_tail = ''
            settings_code.append(SETEMAIL_CODE % (email, readonly_tail))

        locale = self._get_setting(context, 'snapengage_locale',
                'SNAPENGAGE_LOCALE')
        if locale is None:
            locale = translation.to_locale(translation.get_language())
        settings_code.append(SETLOCALE_CODE % locale)

        form_position = self._get_setting(context,
                'snapengage_form_position', 'SNAPENGAGE_FORM_POSITION')
        if form_position is not None:
            settings_code.append(FORM_POSITION_CODE % form_position)

        form_top_position = self._get_setting(context,
                'snapengage_form_top_position', 'SNAPENGAGE_FORM_TOP_POSITION')
        if form_top_position is not None:
            settings_code.append(FORM_TOP_POSITION_CODE % form_top_position)

        show_offline = self._get_setting(context, 'snapengage_show_offline',
                'SNAPENGAGE_SHOW_OFFLINE', True)
        if not show_offline:
            settings_code.append(DISABLE_OFFLINE_CODE)

        screenshots = self._get_setting(context, 'snapengage_screenshots',
                'SNAPENGAGE_SCREENSHOTS', True)
        if not screenshots:
            settings_code.append(DISABLE_SCREENSHOT_CODE)

        offline_screenshots = self._get_setting(context,
            'snapengage_offline_screenshots',
            'SNAPENGAGE_OFFLINE_SCREENSHOTS', True)
        if not offline_screenshots:
            settings_code.append(DISABLE_OFFLINE_SCREENSHOT_CODE)

        if not context.get('snapengage_proactive_chat', True):
            settings_code.append(DISABLE_PROACTIVE_CHAT_CODE)

        sounds = self._get_setting(context, 'snapengage_sounds',
            'SNAPENGAGE_SOUNDS', True)
        if not sounds:
            settings_code.append(DISABLE_SOUNDS_CODE)

        button_effect = self._get_setting(context, 'snapengage_button_effect',
                'SNAPENGAGE_BUTTON_EFFECT')
        if button_effect is not None:
            settings_code.append(BUTTONEFFECT_CODE % button_effect)

        button = self._get_setting(context, 'snapengage_button',
                'SNAPENGAGE_BUTTON', BUTTON_STYLE_DEFAULT)
        if button == BUTTON_STYLE_NONE:
            settings_code.append(INIT_CODE % self.widget_id)
        else:
            if not isinstance(button, int):
                # Assume button as a URL to a custom image
                settings_code.append(SETBUTTON_CODE % button)
            button_location = self._get_setting(context,
                    'snapengage_button_location', 'SNAPENGAGE_BUTTON_LOCATION',
                    BUTTON_LOCATION_LEFT)
            button_offset = self._get_setting(context,
                    'snapengage_button_location_offset',
                    'SNAPENGAGE_BUTTON_LOCATION_OFFSET', '55%')
            settings_code.append(ADDBUTTON_CODE % {
                'id': self.widget_id,
                'location': button_location,
                'offset': button_offset,
                'dynamic_tail': ',true' if (button == BUTTON_STYLE_LIVE) else '',
                })
        html = SETUP_CODE % {'widget_id': self.widget_id,
                'settings_code': " ".join(settings_code)}
        return html

    def _get_setting(self, context, context_key, setting=None, default=None):
        try:
            return context[context_key]
        except KeyError:
            if setting is not None:
                return getattr(settings, setting, default)
            else:
                return default


def contribute_to_analytical(add_node):
    SnapEngageNode()  # ensure properly configured
    add_node('body_bottom', SnapEngageNode)

########NEW FILE########
__FILENAME__ = spring_metrics
"""
Spring Metrics template tags and filters.
"""

from __future__ import absolute_import

import re

from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import get_identity, is_internal_ip, disable_html, \
        get_required_setting


TRACKING_ID_RE = re.compile(r'^[0-9a-f]+$')
TRACKING_CODE = """
    <script type='text/javascript'>
     var _springMetq = _springMetq || [];
     _springMetq.push(['id', '%(tracking_id)s']);
     (
      function(){
       var s = document.createElement('script');
       s.type = 'text/javascript';
       s.async = true;
       s.src = ('https:' == document.location.protocol ? 'https://d3rmnwi2tssrfx.cloudfront.net/a.js' : 'http://static.springmetrics.com/a.js');
       var x = document.getElementsByTagName('script')[0];
       x.parentNode.insertBefore(s, x);
      }
     )();
     %(custom_commands)s
    </script>
"""


register = Library()


@register.tag
def spring_metrics(parser, token):
    """
    Spring Metrics tracking template tag.

    Renders Javascript code to track page visits.  You must supply
    your Spring Metrics Tracking ID in the
    ``SPRING_METRICS_TRACKING_ID`` setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return SpringMetricsNode()

class SpringMetricsNode(Node):
    def __init__(self):
        self.tracking_id = get_required_setting('SPRING_METRICS_TRACKING_ID',
            TRACKING_ID_RE, "must be a hexadecimal string")

    def render(self, context):
        custom = {}
        for dict_ in context:
            for var, val in dict_.items():
                if var.startswith('spring_metrics_'):
                    custom[var[15:]] = val
        if 'email' not in custom:
            identity = get_identity(context, 'spring_metrics',
                    lambda u: u.email)
            if identity is not None:
                custom['email'] = identity

        html = TRACKING_CODE % {'tracking_id': self.tracking_id,
                'custom_commands': self._generate_custom_javascript(custom)}
        if is_internal_ip(context, 'SPRING_METRICS'):
            html = disable_html(html, 'Spring Metrics')
        return html

    def _generate_custom_javascript(self, vars):
        commands = []
        convert = vars.pop('convert', None)
        if convert is not None:
            commands.append("_springMetq.push(['convert', '%s'])" % convert)
        commands.extend("_springMetq.push(['setdata', {'%s': '%s'}]);"
                % (var, val) for var, val in vars.items())
        return " ".join(commands)


def contribute_to_analytical(add_node):
    SpringMetricsNode()  # ensure properly configured
    add_node('head_bottom', SpringMetricsNode)

########NEW FILE########
__FILENAME__ = uservoice
"""
UserVoice template tags.
"""

from __future__ import absolute_import

import json
import re

from django.conf import settings
from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import get_required_setting


WIDGET_KEY_RE = re.compile(r'^[a-zA-Z0-9]*$')
TRACKING_CODE = """
    <script type="text/javascript">

    UserVoice=window.UserVoice||[];(function(){
            var uv=document.createElement('script');uv.type='text/javascript';
            uv.async=true;uv.src='//widget.uservoice.com/%(widget_key)s.js';
            var s=document.getElementsByTagName('script')[0];
            s.parentNode.insertBefore(uv,s)})();

    UserVoice.push(['set', %(options)s]);
    %(trigger)s
    </script>
"""
TRIGGER = "UserVoice.push(['addTrigger', {}]);"
register = Library()


@register.tag
def uservoice(parser, token):
    """
    UserVoice tracking template tag.

    Renders Javascript code to track page visits.  You must supply
    your UserVoice Widget Key in the ``USERVOICE_WIDGET_KEY``
    setting or the ``uservoice_widget_key`` template context variable.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return UserVoiceNode()


class UserVoiceNode(Node):
    def __init__(self):
        self.default_widget_key = get_required_setting('USERVOICE_WIDGET_KEY',
                WIDGET_KEY_RE, "must be an alphanumeric string")

    def render(self, context):
        widget_key = context.get('uservoice_widget_key')
        if not widget_key:
            widget_key = self.default_widget_key
        if not widget_key:
            return ''
        # default
        options = {}
        options.update(getattr(settings, 'USERVOICE_WIDGET_OPTIONS', {}))
        options.update(context.get('uservoice_widget_options', {}))

        trigger = context.get('uservoice_add_trigger',
                              getattr(settings, 'USERVOICE_ADD_TRIGGER', True))

        html = TRACKING_CODE % {'widget_key': widget_key,
                                'options':  json.dumps(options, sort_keys=True),
                                'trigger': TRIGGER if trigger else ''}
        return html


def contribute_to_analytical(add_node):
    UserVoiceNode()  # ensure properly configured
    add_node('body_bottom', UserVoiceNode)

########NEW FILE########
__FILENAME__ = woopra
"""
Woopra template tags and filters.
"""

from __future__ import absolute_import

import json
import re

from django.conf import settings
from django.template import Library, Node, TemplateSyntaxError

from analytical.utils import get_identity, get_user_from_context, \
        is_internal_ip, disable_html, get_required_setting


DOMAIN_RE = re.compile(r'^\S+$')
TRACKING_CODE = """
     <script type="text/javascript">
      var woo_settings = %(settings)s;
      var woo_visitor = %(visitor)s;
      (function(){
        var wsc=document.createElement('script');
        wsc.type='text/javascript';
        wsc.src=document.location.protocol+'//static.woopra.com/js/woopra.js';
        wsc.async=true;
        var ssc = document.getElementsByTagName('script')[0];
        ssc.parentNode.insertBefore(wsc, ssc);
      })();
    </script>
"""


register = Library()


@register.tag
def woopra(parser, token):
    """
    Woopra tracking template tag.

    Renders Javascript code to track page visits.  You must supply
    your Woopra domain in the ``WOOPRA_DOMAIN`` setting.
    """
    bits = token.split_contents()
    if len(bits) > 1:
        raise TemplateSyntaxError("'%s' takes no arguments" % bits[0])
    return WoopraNode()

class WoopraNode(Node):
    def __init__(self):
        self.domain = get_required_setting('WOOPRA_DOMAIN', DOMAIN_RE,
                "must be a domain name")

    def render(self, context):
        settings = self._get_settings(context)
        visitor = self._get_visitor(context)

        html = TRACKING_CODE % {
            'settings': json.dumps(settings, sort_keys=True),
            'visitor': json.dumps(visitor, sort_keys=True),
        }
        if is_internal_ip(context, 'WOOPRA'):
            html = disable_html(html, 'Woopra')
        return html

    def _get_settings(self, context):
        vars = {'domain': self.domain}
        try:
            vars['idle_timeout'] = str(settings.WOOPRA_IDLE_TIMEOUT)
        except AttributeError:
            pass
        return vars

    def _get_visitor(self, context):
        vars = {}
        for dict_ in context:
            for var, val in dict_.items():
                if var.startswith('woopra_'):
                    vars[var[7:]] = val
        if 'name' not in vars and 'email' not in vars:
            user = get_user_from_context(context)
            if user is not None and user.is_authenticated():
                vars['name'] = get_identity(context, 'woopra',
                        self._identify, user)
                if user.email:
                    vars['email'] = user.email
        return vars

    def _identify(self, user):
        name = user.get_full_name()
        if not name:
            name = user.username
        return name


def contribute_to_analytical(add_node):
    WoopraNode()  # ensure properly configured
    add_node('head_bottom', WoopraNode)

########NEW FILE########
__FILENAME__ = settings
"""
django-analytical testing settings.
"""

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

INSTALLED_APPS = [
    'analytical',
]

SECRET_KEY = 'testing'

########NEW FILE########
__FILENAME__ = dummy
"""
Dummy testing template tags and filters.
"""

from __future__ import absolute_import

from django.template import Library, Node, TemplateSyntaxError

from analytical.templatetags.analytical import TAG_LOCATIONS


register = Library()


def _location_node(location):
    class DummyNode(Node):
        def render(self, context):
            return "<!-- dummy_%s -->" % location
    return DummyNode

_location_nodes = dict((l, _location_node(l)) for l in TAG_LOCATIONS)


def _location_tag(location):
    def dummy_tag(parser, token):
        bits = token.split_contents()
        if len(bits) > 1:
            raise TemplateSyntaxError("'%s' tag takes no arguments" % bits[0])
        return _location_nodes[location]
    return dummy_tag

for loc in TAG_LOCATIONS:
    register.tag('dummy_%s' % loc, _location_tag(loc))


def contribute_to_analytical(add_node_cls):
    for location in TAG_LOCATIONS:
        add_node_cls(location, _location_nodes[location])

########NEW FILE########
__FILENAME__ = test_tag_analytical
"""
Tests for the generic template tags and filters.
"""

from django.template import Context, Template

from analytical.templatetags import analytical
from analytical.tests.utils import TagTestCase


class AnalyticsTagTestCase(TagTestCase):
    """
    Tests for the ``analytical`` template tags.
    """

    def setUp(self):
        super(AnalyticsTagTestCase, self).setUp()
        self._tag_modules = analytical.TAG_MODULES
        analytical.TAG_MODULES = ['analytical.tests.dummy']
        analytical.template_nodes = analytical._load_template_nodes()

    def tearDown(self):
        analytical.TAG_MODULES = self._tag_modules
        analytical.template_nodes = analytical._load_template_nodes()
        super(AnalyticsTagTestCase, self).tearDown()

    def render_location_tag(self, location, vars=None):
        if vars is None:
            vars = {}
        t = Template("{%% load analytical %%}{%% analytical_%s %%}"
                % location)
        return t.render(Context(vars))

    def test_location_tags(self):
        for l in ['head_top', 'head_bottom', 'body_top', 'body_bottom']:
            r = self.render_location_tag(l)
            self.assertTrue('dummy_%s' % l in r, r)

########NEW FILE########
__FILENAME__ = test_tag_chartbeat
"""
Tests for the Chartbeat template tags and filters.
"""

import re

from django.conf import settings
from django.contrib.sites.models import Site
from django.http import HttpRequest
from django.template import Context
from django.test import TestCase

from analytical.templatetags.chartbeat import ChartbeatTopNode, \
        ChartbeatBottomNode
from analytical.tests.utils import TagTestCase, with_apps, without_apps, \
        override_settings, SETTING_DELETED
from analytical.utils import AnalyticalException


@without_apps('django.contrib.sites')
@override_settings(CHARTBEAT_USER_ID='12345')
class ChartbeatTagTestCaseNoSites(TestCase):
    def test_rendering_setup_no_site(self):
        r = ChartbeatBottomNode().render(Context())
        self.assertTrue('var _sf_async_config={"uid": "12345"};' in r, r)


@with_apps('django.contrib.sites')
@override_settings(CHARTBEAT_USER_ID='12345')
class ChartbeatTagTestCaseWithSites(TestCase):
    def setUp(self):
        from django.core.management import call_command
        from django.db.models import loading
        loading.cache.loaded = False
        call_command("syncdb", verbosity=0)

    def test_rendering_setup_site(self):
        site = Site.objects.create(domain="test.com", name="test")
        with override_settings(SITE_ID=site.id):
            r = ChartbeatBottomNode().render(Context())
            self.assertTrue(re.search(
                    'var _sf_async_config={.*"uid": "12345".*};', r), r)
            self.assertTrue(re.search(
                    'var _sf_async_config={.*"domain": "test.com".*};', r), r)

    @override_settings(CHARTBEAT_AUTO_DOMAIN=False)
    def test_auto_domain_false(self):
        """
        Even if 'django.contrib.sites' is in INSTALLED_APPS, if
        CHARTBEAT_AUTO_DOMAIN is False, ensure there is no 'domain'
        in _sf_async_config.
        """
        r = ChartbeatBottomNode().render(Context())
        self.assertTrue('var _sf_async_config={"uid": "12345"};' in r, r)


@override_settings(CHARTBEAT_USER_ID='12345')
class ChartbeatTagTestCase(TagTestCase):
    """
    Tests for the ``chartbeat`` template tag.
    """

    def test_top_tag(self):
        r = self.render_tag('chartbeat', 'chartbeat_top',
                {'chartbeat_domain': "test.com"})
        self.assertTrue('var _sf_startpt=(new Date()).getTime()' in r, r)

    def test_bottom_tag(self):
        r = self.render_tag('chartbeat', 'chartbeat_bottom',
                {'chartbeat_domain': "test.com"})
        self.assertTrue(re.search(
                'var _sf_async_config={.*"uid": "12345".*};', r), r)
        self.assertTrue(re.search(
                'var _sf_async_config={.*"domain": "test.com".*};', r), r)

    def test_top_node(self):
        r = ChartbeatTopNode().render(
                Context({'chartbeat_domain': "test.com"}))
        self.assertTrue('var _sf_startpt=(new Date()).getTime()' in r, r)

    def test_bottom_node(self):
        r = ChartbeatBottomNode().render(
                Context({'chartbeat_domain': "test.com"}))
        self.assertTrue(re.search(
                'var _sf_async_config={.*"uid": "12345".*};', r), r)
        self.assertTrue(re.search(
                'var _sf_async_config={.*"domain": "test.com".*};', r), r)

    @override_settings(CHARTBEAT_USER_ID=SETTING_DELETED)
    def test_no_user_id(self):
        self.assertRaises(AnalyticalException, ChartbeatBottomNode)

    @override_settings(CHARTBEAT_USER_ID='123abc')
    def test_wrong_user_id(self):
        self.assertRaises(AnalyticalException, ChartbeatBottomNode)

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        r = ChartbeatBottomNode().render(context)
        self.assertTrue(r.startswith(
                '<!-- Chartbeat disabled on internal IP address'), r)
        self.assertTrue(r.endswith('-->'), r)

########NEW FILE########
__FILENAME__ = test_tag_clickmap
"""
Tests for the Clickmap template tags and filters.
"""

import re

from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpRequest
from django.template import Context

from analytical.templatetags.clickmap import ClickmapNode
from analytical.tests.utils import TagTestCase, override_settings, SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(CLICKMAP_TRACKER_ID='12345')
class ClickyTagTestCase(TagTestCase):
    """
    Tests for the ``clickmap`` template tag.
    """

    def test_tag(self):
        r = self.render_tag('clicjmap', 'clickmap')
        self.assertTrue("tracker: '12345', version:'2'};" in r, r)

    def test_node(self):
        r = ClickmapNode().render(Context({}))
        self.assertTrue("tracker: '12345', version:'2'};" in r, r)

    @override_settings(CLICKMAP_TRACKER_ID=SETTING_DELETED)
    def test_no_site_id(self):
        self.assertRaises(AnalyticalException, ClickmapNode)

    @override_settings(CLICKMAP_TRACKER_ID='abc')
    def test_wrong_site_id(self):
        self.assertRaises(AnalyticalException, ClickyNode)

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        r = ClickmapNode().render(context)
        self.assertTrue(r.startswith(
                '<!-- Clickmap disabled on internal IP address'), r)
        self.assertTrue(r.endswith('-->'), r)

########NEW FILE########
__FILENAME__ = test_tag_clicky
"""
Tests for the Clicky template tags and filters.
"""

import re

from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpRequest
from django.template import Context

from analytical.templatetags.clicky import ClickyNode
from analytical.tests.utils import TagTestCase, override_settings, SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(CLICKY_SITE_ID='12345678')
class ClickyTagTestCase(TagTestCase):
    """
    Tests for the ``clicky`` template tag.
    """

    def test_tag(self):
        r = self.render_tag('clicky', 'clicky')
        self.assertTrue('clicky_site_ids.push(12345678);' in r, r)
        self.assertTrue('src="//in.getclicky.com/12345678ns.gif"' in r,
                r)

    def test_node(self):
        r = ClickyNode().render(Context({}))
        self.assertTrue('clicky_site_ids.push(12345678);' in r, r)
        self.assertTrue('src="//in.getclicky.com/12345678ns.gif"' in r,
                r)

    @override_settings(CLICKY_SITE_ID=SETTING_DELETED)
    def test_no_site_id(self):
        self.assertRaises(AnalyticalException, ClickyNode)

    @override_settings(CLICKY_SITE_ID='123abc')
    def test_wrong_site_id(self):
        self.assertRaises(AnalyticalException, ClickyNode)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify(self):
        r = ClickyNode().render(Context({'user': User(username='test')}))
        self.assertTrue(
                'var clicky_custom = {"session": {"username": "test"}};' in r,
                r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify_anonymous_user(self):
        r = ClickyNode().render(Context({'user': AnonymousUser()}))
        self.assertFalse('var clicky_custom = {"session": {"username":' in r, r)

    def test_custom(self):
        r = ClickyNode().render(Context({'clicky_var1': 'val1',
                'clicky_var2': 'val2'}))
        self.assertTrue(re.search('var clicky_custom = {.*'
                '"var1": "val1", "var2": "val2".*};', r), r)

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        r = ClickyNode().render(context)
        self.assertTrue(r.startswith(
                '<!-- Clicky disabled on internal IP address'), r)
        self.assertTrue(r.endswith('-->'), r)

########NEW FILE########
__FILENAME__ = test_tag_crazy_egg
"""
Tests for the Crazy Egg template tags and filters.
"""

from django.http import HttpRequest
from django.template import Context

from analytical.templatetags.crazy_egg import CrazyEggNode
from analytical.tests.utils import TagTestCase, override_settings, SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(CRAZY_EGG_ACCOUNT_NUMBER='12345678')
class CrazyEggTagTestCase(TagTestCase):
    """
    Tests for the ``crazy_egg`` template tag.
    """

    def test_tag(self):
        r = self.render_tag('crazy_egg', 'crazy_egg')
        self.assertTrue('/1234/5678.js' in r, r)

    def test_node(self):
        r = CrazyEggNode().render(Context())
        self.assertTrue('/1234/5678.js' in r, r)

    @override_settings(CRAZY_EGG_ACCOUNT_NUMBER=SETTING_DELETED)
    def test_no_account_number(self):
        self.assertRaises(AnalyticalException, CrazyEggNode)

    @override_settings(CRAZY_EGG_ACCOUNT_NUMBER='123abc')
    def test_wrong_account_number(self):
        self.assertRaises(AnalyticalException, CrazyEggNode)

    def test_uservars(self):
        context = Context({'crazy_egg_var1': 'foo', 'crazy_egg_var2': 'bar'})
        r = CrazyEggNode().render(context)
        self.assertTrue("CE2.set(1, 'foo');" in r, r)
        self.assertTrue("CE2.set(2, 'bar');" in r, r)

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        r = CrazyEggNode().render(context)
        self.assertTrue(r.startswith(
                '<!-- Crazy Egg disabled on internal IP address'), r)
        self.assertTrue(r.endswith('-->'), r)

########NEW FILE########
__FILENAME__ = test_tag_gauges
"""
Tests for the Gauges template tags and filters.
"""

from django.http import HttpRequest
from django.template import Context

from analytical.templatetags.gauges import GaugesNode
from analytical.tests.utils import TagTestCase, override_settings, SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(GAUGES_SITE_ID='1234567890abcdef0123456789')
class GaugesTagTestCase(TagTestCase):
    """
    Tests for the ``gauges`` template tag.
    """

    def test_tag(self):
        self.assertEqual("""
    <script type="text/javascript">
      var _gauges = _gauges || [];
      (function() {
        var t   = document.createElement('script');
        t.type  = 'text/javascript';
        t.async = true;
        t.id    = 'gauges-tracker';
        t.setAttribute('data-site-id', '1234567890abcdef0123456789');
        t.src = '//secure.gaug.es/track.js';
        var s = document.getElementsByTagName('script')[0];
        s.parentNode.insertBefore(t, s);
      })();
    </script>
""",
                self.render_tag('gauges', 'gauges'))

    def test_node(self):
        self.assertEqual(
                """
    <script type="text/javascript">
      var _gauges = _gauges || [];
      (function() {
        var t   = document.createElement('script');
        t.type  = 'text/javascript';
        t.async = true;
        t.id    = 'gauges-tracker';
        t.setAttribute('data-site-id', '1234567890abcdef0123456789');
        t.src = '//secure.gaug.es/track.js';
        var s = document.getElementsByTagName('script')[0];
        s.parentNode.insertBefore(t, s);
      })();
    </script>
""",
                GaugesNode().render(Context()))

    @override_settings(GAUGES_SITE_ID=SETTING_DELETED)
    def test_no_account_number(self):
        self.assertRaises(AnalyticalException, GaugesNode)

    @override_settings(GAUGES_SITE_ID='123abQ')
    def test_wrong_account_number(self):
        self.assertRaises(AnalyticalException, GaugesNode)

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        r = GaugesNode().render(context)
        self.assertTrue(r.startswith(
                '<!-- Gauges disabled on internal IP address'), r)
        self.assertTrue(r.endswith('-->'), r)

########NEW FILE########
__FILENAME__ = test_tag_google_analytics
"""
Tests for the Google Analytics template tags and filters.
"""

from django.http import HttpRequest
from django.template import Context

from analytical.templatetags.google_analytics import GoogleAnalyticsNode, \
        TRACK_SINGLE_DOMAIN, TRACK_MULTIPLE_DOMAINS, TRACK_MULTIPLE_SUBDOMAINS,\
        SCOPE_VISITOR, SCOPE_SESSION, SCOPE_PAGE
from analytical.tests.utils import TestCase, TagTestCase, override_settings, \
        without_apps, SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(GOOGLE_ANALYTICS_PROPERTY_ID='UA-123456-7',
        GOOGLE_ANALYTICS_TRACKING_STYLE=TRACK_SINGLE_DOMAIN)
class GoogleAnalyticsTagTestCase(TagTestCase):
    """
    Tests for the ``google_analytics`` template tag.
    """

    def test_tag(self):
        r = self.render_tag('google_analytics', 'google_analytics')
        self.assertTrue("_gaq.push(['_setAccount', 'UA-123456-7']);" in r, r)
        self.assertTrue("_gaq.push(['_trackPageview']);" in r, r)

    def test_node(self):
        r = GoogleAnalyticsNode().render(Context())
        self.assertTrue("_gaq.push(['_setAccount', 'UA-123456-7']);" in r, r)
        self.assertTrue("_gaq.push(['_trackPageview']);" in r, r)

    @override_settings(GOOGLE_ANALYTICS_PROPERTY_ID=SETTING_DELETED)
    def test_no_property_id(self):
        self.assertRaises(AnalyticalException, GoogleAnalyticsNode)

    @override_settings(GOOGLE_ANALYTICS_PROPERTY_ID='wrong')
    def test_wrong_property_id(self):
        self.assertRaises(AnalyticalException, GoogleAnalyticsNode)

    @override_settings(
            GOOGLE_ANALYTICS_TRACKING_STYLE=TRACK_MULTIPLE_SUBDOMAINS,
            GOOGLE_ANALYTICS_DOMAIN='example.com')
    def test_track_multiple_subdomains(self):
        r = GoogleAnalyticsNode().render(Context())
        self.assertTrue("_gaq.push(['_setDomainName', 'example.com']);" in r, r)
        self.assertTrue("_gaq.push(['_setAllowHash', false]);" in r, r)

    @override_settings(GOOGLE_ANALYTICS_TRACKING_STYLE=TRACK_MULTIPLE_DOMAINS,
            GOOGLE_ANALYTICS_DOMAIN='example.com')
    def test_track_multiple_domains(self):
        r = GoogleAnalyticsNode().render(Context())
        self.assertTrue("_gaq.push(['_setDomainName', 'example.com']);" in r, r)
        self.assertTrue("_gaq.push(['_setAllowHash', false]);" in r, r)
        self.assertTrue("_gaq.push(['_setAllowLinker', true]);" in r, r)

    def test_custom_vars(self):
        context = Context({
            'google_analytics_var1': ('test1', 'foo'),
            'google_analytics_var2': ('test2', 'bar', SCOPE_VISITOR),
            'google_analytics_var4': ('test4', 'baz', SCOPE_SESSION),
            'google_analytics_var5': ('test5', 'qux', SCOPE_PAGE),
        })
        r = GoogleAnalyticsNode().render(context)
        self.assertTrue("_gaq.push(['_setCustomVar', 1, 'test1', 'foo', 3]);"
                in r, r)
        self.assertTrue("_gaq.push(['_setCustomVar', 2, 'test2', 'bar', 1]);"
                in r, r)
        self.assertTrue("_gaq.push(['_setCustomVar', 4, 'test4', 'baz', 2]);"
                in r, r)
        self.assertTrue("_gaq.push(['_setCustomVar', 5, 'test5', 'qux', 3]);"
                in r, r)

    @override_settings(GOOGLE_ANALYTICS_SITE_SPEED=True)
    def test_track_page_load_time(self):
        r = GoogleAnalyticsNode().render(Context())
        self.assertTrue("_gaq.push(['_trackPageLoadTime']);" in r, r)

    def test_display_advertising(self):
        with override_settings(GOOGLE_ANALYTICS_DISPLAY_ADVERTISING=False):
            r = GoogleAnalyticsNode().render(Context())
            self.assertTrue("google-analytics.com/ga.js" in r, r)
        with override_settings(GOOGLE_ANALYTICS_DISPLAY_ADVERTISING=True):
            r = GoogleAnalyticsNode().render(Context())
            self.assertTrue("stats.g.doubleclick.net/dc.js" in r, r)

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        r = GoogleAnalyticsNode().render(context)
        self.assertTrue(r.startswith(
                '<!-- Google Analytics disabled on internal IP address'), r)
        self.assertTrue(r.endswith('-->'), r)

    @override_settings(GOOGLE_ANALYTICS_ANONYMIZE_IP=True)
    def test_anonymize_ip(self):
        r = GoogleAnalyticsNode().render(Context())
        self.assertTrue("_gaq.push (['_gat._anonymizeIp']);" in r, r)

    @override_settings(GOOGLE_ANALYTICS_ANONYMIZE_IP=False)
    def test_anonymize_ip_not_present(self):
        r = GoogleAnalyticsNode().render(Context())
        self.assertFalse("_gaq.push (['_gat._anonymizeIp']);" in r, r)

@without_apps('django.contrib.sites')
@override_settings(GOOGLE_ANALYTICS_PROPERTY_ID='UA-123456-7',
        GOOGLE_ANALYTICS_TRACKING_STYLE=TRACK_MULTIPLE_DOMAINS,
        GOOGLE_ANALYTICS_DOMAIN=SETTING_DELETED,
        ANALYTICAL_DOMAIN=SETTING_DELETED)
class NoDomainTestCase(TestCase):
    def test_exception_without_domain(self):
        context = Context()
        self.assertRaises(AnalyticalException, GoogleAnalyticsNode().render,
                context)

########NEW FILE########
__FILENAME__ = test_tag_gosquared
"""
Tests for the GoSquared template tags and filters.
"""

from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpRequest
from django.template import Context

from analytical.templatetags.gosquared import GoSquaredNode
from analytical.tests import override_settings
from analytical.tests.utils import TagTestCase, override_settings, SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(GOSQUARED_SITE_TOKEN='ABC-123456-D')
class GoSquaredTagTestCase(TagTestCase):
    """
    Tests for the ``gosquared`` template tag.
    """

    def test_tag(self):
        r = self.render_tag('gosquared', 'gosquared')
        self.assertTrue('GoSquared.acct = "ABC-123456-D";' in r, r)

    def test_node(self):
        r = GoSquaredNode().render(Context({}))
        self.assertTrue('GoSquared.acct = "ABC-123456-D";' in r, r)

    @override_settings(GOSQUARED_SITE_TOKEN=SETTING_DELETED)
    def test_no_token(self):
        self.assertRaises(AnalyticalException, GoSquaredNode)

    @override_settings(GOSQUARED_SITE_TOKEN='this is not a token')
    def test_wrong_token(self):
        self.assertRaises(AnalyticalException, GoSquaredNode)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_auto_identify(self):
        r = GoSquaredNode().render(Context({'user': User(username='test',
                first_name='Test', last_name='User')}))
        self.assertTrue('GoSquared.UserName = "Test User";' in r, r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_manual_identify(self):
        r = GoSquaredNode().render(Context({
            'user': User(username='test', first_name='Test', last_name='User'),
            'gosquared_identity': 'test_identity',
        }))
        self.assertTrue('GoSquared.UserName = "test_identity";' in r, r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify_anonymous_user(self):
        r = GoSquaredNode().render(Context({'user': AnonymousUser()}))
        self.assertFalse('GoSquared.UserName = ' in r, r)

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        r = GoSquaredNode().render(context)
        self.assertTrue(r.startswith(
                '<!-- GoSquared disabled on internal IP address'), r)
        self.assertTrue(r.endswith('-->'), r)

########NEW FILE########
__FILENAME__ = test_tag_hubspot
"""
Tests for the HubSpot template tags and filters.
"""

from django.http import HttpRequest
from django.template import Context

from analytical.templatetags.hubspot import HubSpotNode
from analytical.tests.utils import TagTestCase, override_settings, SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(HUBSPOT_PORTAL_ID='1234', HUBSPOT_DOMAIN='example.com')
class HubSpotTagTestCase(TagTestCase):
    """
    Tests for the ``hubspot`` template tag.
    """

    def test_tag(self):
        r = self.render_tag('hubspot', 'hubspot')
        self.assertTrue('var hs_portalid = 1234;' in r, r)
        self.assertTrue('var hs_ppa = "example.com";' in r, r)

    def test_node(self):
        r = HubSpotNode().render(Context())
        self.assertTrue('var hs_portalid = 1234;' in r, r)
        self.assertTrue('var hs_ppa = "example.com";' in r, r)

    @override_settings(HUBSPOT_PORTAL_ID=SETTING_DELETED)
    def test_no_portal_id(self):
        self.assertRaises(AnalyticalException, HubSpotNode)

    @override_settings(HUBSPOT_PORTAL_ID='wrong')
    def test_wrong_portal_id(self):
        self.assertRaises(AnalyticalException, HubSpotNode)

    @override_settings(HUBSPOT_DOMAIN=SETTING_DELETED)
    def test_no_domain(self):
        self.assertRaises(AnalyticalException, HubSpotNode)

    @override_settings(HUBSPOT_DOMAIN='wrong domain')
    def test_wrong_domain(self):
        self.assertRaises(AnalyticalException, HubSpotNode)

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        r = HubSpotNode().render(context)
        self.assertTrue(r.startswith(
                '<!-- HubSpot disabled on internal IP address'), r)
        self.assertTrue(r.endswith('-->'), r)

########NEW FILE########
__FILENAME__ = test_tag_intercom
"""
Tests for the intercom template tags and filters.
"""

import datetime

from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpRequest
from django.template import Context

from analytical.templatetags.intercom import IntercomNode
from analytical.tests.utils import TagTestCase, override_settings, SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(INTERCOM_APP_ID='1234567890abcdef0123456789')
class IntercomTagTestCase(TagTestCase):
    """
    Tests for the ``intercom`` template tag.
    """

    def test_tag(self):
        rendered_tag = self.render_tag('intercom', 'intercom')
        self.assertTrue(rendered_tag.startswith('<!-- Intercom disabled on internal IP address'))

    def test_node(self):
        now = datetime.datetime(2014, 4, 9, 15, 15, 0)
        rendered_tag = IntercomNode().render(Context({
            'user': User(
                username='test',
                first_name='Firstname',
                last_name='Lastname',
                email="test@example.com",
                date_joined=now)
        }))
        # Because the json isn't predictably ordered, we can't just test the whole thing verbatim.
        self.assertEquals("""
<script id="IntercomSettingsScriptTag">
  window.intercomSettings = {"app_id": "1234567890abcdef0123456789", "created_at": 1397074500, "email": "test@example.com", "name": "Firstname Lastname"};
</script>
<script>(function(){var w=window;var ic=w.Intercom;if(typeof ic==="function"){ic('reattach_activator');ic('update',intercomSettings);}else{var d=document;var i=function(){i.c(arguments)};i.q=[];i.c=function(args){i.q.push(args)};w.Intercom=i;function l(){var s=d.createElement('script');s.type='text/javascript';s.async=true;s.src='https://static.intercomcdn.com/intercom.v1.js';var x=d.getElementsByTagName('script')[0];x.parentNode.insertBefore(s,x);}if(w.attachEvent){w.attachEvent('onload',l);}else{w.addEventListener('load',l,false);}}})()</script>
""", rendered_tag)

    @override_settings(INTERCOM_APP_ID=SETTING_DELETED)
    def test_no_account_number(self):
        self.assertRaises(AnalyticalException, IntercomNode)

    @override_settings(INTERCOM_APP_ID='123abQ')
    def test_wrong_account_number(self):
        self.assertRaises(AnalyticalException, IntercomNode)

    def test_identify_name_email_and_created_at(self):
        now = datetime.datetime(2014, 4, 9, 15, 15, 0)
        r = IntercomNode().render(Context({'user': User(username='test',
                first_name='Firstname', last_name='Lastname',
                email="test@example.com", date_joined=now)}))
        self.assertTrue(
            """window.intercomSettings = {"app_id": "1234567890abcdef0123456789", "created_at": 1397074500, "email": "test@example.com", "name": "Firstname Lastname"};"""\
            in r
        )

    def test_custom(self):
        r = IntercomNode().render(Context({
                'intercom_var1': 'val1',
                'intercom_var2': 'val2'
        }))
        self.assertTrue('var1": "val1", "var2": "val2"' in r)

    def test_identify_name_and_email(self):
        r = IntercomNode().render(Context({
                'user': User(username='test',
                first_name='Firstname',
                last_name='Lastname',
                email="test@example.com")
        }))
        self.assertTrue('"email": "test@example.com", "name": "Firstname Lastname"' in r)

    def test_identify_username_no_email(self):
        r = IntercomNode().render(Context({'user': User(username='test')}))
        self.assertTrue('"name": "test"' in r, r)

    def test_no_identify_when_explicit_name(self):
        r = IntercomNode().render(Context({'intercom_name': 'explicit',
                'user': User(username='implicit')}))
        self.assertTrue('"name": "explicit"' in r, r)

    def test_no_identify_when_explicit_email(self):
        r = IntercomNode().render(Context({'intercom_email': 'explicit',
                'user': User(username='implicit')}))
        self.assertTrue('"email": "explicit"' in r, r)

    def test_disable_for_anonymous_users(self):
        r = IntercomNode().render(Context({'user': AnonymousUser()}))
        self.assertTrue(r.startswith('<!-- Intercom disabled on internal IP address'), r)

########NEW FILE########
__FILENAME__ = test_tag_kiss_insights
"""
Tests for the KISSinsights template tags and filters.
"""

from django.contrib.auth.models import User, AnonymousUser
from django.template import Context

from analytical.templatetags.kiss_insights import KissInsightsNode
from analytical.tests.utils import TagTestCase, override_settings, SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(KISS_INSIGHTS_ACCOUNT_NUMBER='12345',
        KISS_INSIGHTS_SITE_CODE='abc')
class KissInsightsTagTestCase(TagTestCase):
    """
    Tests for the ``kiss_insights`` template tag.
    """

    def test_tag(self):
        r = self.render_tag('kiss_insights', 'kiss_insights')
        self.assertTrue("//s3.amazonaws.com/ki.js/12345/abc.js" in r, r)

    def test_node(self):
        r = KissInsightsNode().render(Context())
        self.assertTrue("//s3.amazonaws.com/ki.js/12345/abc.js" in r, r)

    @override_settings(KISS_INSIGHTS_ACCOUNT_NUMBER=SETTING_DELETED)
    def test_no_account_number(self):
        self.assertRaises(AnalyticalException, KissInsightsNode)

    @override_settings(KISS_INSIGHTS_SITE_CODE=SETTING_DELETED)
    def test_no_site_code(self):
        self.assertRaises(AnalyticalException, KissInsightsNode)

    @override_settings(KISS_INSIGHTS_ACCOUNT_NUMBER='abcde')
    def test_wrong_account_number(self):
        self.assertRaises(AnalyticalException, KissInsightsNode)

    @override_settings(KISS_INSIGHTS_SITE_CODE='abc def')
    def test_wrong_site_id(self):
        self.assertRaises(AnalyticalException, KissInsightsNode)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify(self):
        r = KissInsightsNode().render(Context({'user': User(username='test')}))
        self.assertTrue("_kiq.push(['identify', 'test']);" in r, r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify_anonymous_user(self):
        r = KissInsightsNode().render(Context({'user': AnonymousUser()}))
        self.assertFalse("_kiq.push(['identify', " in r, r)

    def test_show_survey(self):
        r = KissInsightsNode().render(
                Context({'kiss_insights_show_survey': 1234}))
        self.assertTrue("_kiq.push(['showSurvey', 1234]);" in r, r)

########NEW FILE########
__FILENAME__ = test_tag_kiss_metrics
"""
Tests for the KISSmetrics tags and filters.
"""

from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpRequest
from django.template import Context

from analytical.templatetags.kiss_metrics import KissMetricsNode
from analytical.tests.utils import TagTestCase, override_settings, SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(KISS_METRICS_API_KEY='0123456789abcdef0123456789abcdef'
        '01234567')
class KissMetricsTagTestCase(TagTestCase):
    """
    Tests for the ``kiss_metrics`` template tag.
    """

    def test_tag(self):
        r = self.render_tag('kiss_metrics', 'kiss_metrics')
        self.assertTrue("//doug1izaerwt3.cloudfront.net/0123456789abcdef012345"
                "6789abcdef01234567.1.js" in r, r)

    def test_node(self):
        r = KissMetricsNode().render(Context())
        self.assertTrue("//doug1izaerwt3.cloudfront.net/0123456789abcdef012345"
                "6789abcdef01234567.1.js" in r, r)

    @override_settings(KISS_METRICS_API_KEY=SETTING_DELETED)
    def test_no_api_key(self):
        self.assertRaises(AnalyticalException, KissMetricsNode)

    @override_settings(KISS_METRICS_API_KEY='0123456789abcdef0123456789abcdef'
            '0123456')
    def test_api_key_too_short(self):
        self.assertRaises(AnalyticalException, KissMetricsNode)

    @override_settings(KISS_METRICS_API_KEY='0123456789abcdef0123456789abcdef'
            '012345678')
    def test_api_key_too_long(self):
        self.assertRaises(AnalyticalException, KissMetricsNode)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify(self):
        r = KissMetricsNode().render(Context({'user': User(username='test')}))
        self.assertTrue("_kmq.push(['identify', 'test']);" in r, r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify_anonymous_user(self):
        r = KissMetricsNode().render(Context({'user': AnonymousUser()}))
        self.assertFalse("_kmq.push(['identify', " in r, r)

    def test_event(self):
        r = KissMetricsNode().render(Context({'kiss_metrics_event':
                ('test_event', {'prop1': 'val1', 'prop2': 'val2'})}))
        self.assertTrue("_kmq.push(['record', 'test_event', "
                '{"prop1": "val1", "prop2": "val2"}]);' in r, r)

    def test_property(self):
        r = KissMetricsNode().render(Context({'kiss_metrics_properties':
                {'prop1': 'val1', 'prop2': 'val2'}}))
        self.assertTrue("_kmq.push([\'set\', "
                '{"prop1": "val1", "prop2": "val2"}]);' in r, r)

    def test_alias(self):
        r = KissMetricsNode().render(Context({'kiss_metrics_alias':
                {'test': 'test_alias'}}))
        self.assertTrue("_kmq.push(['alias', 'test', 'test_alias']);" in r,r)
                

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        r = KissMetricsNode().render(context)
        self.assertTrue(r.startswith(
                '<!-- KISSmetrics disabled on internal IP address'), r)
        self.assertTrue(r.endswith('-->'), r)

########NEW FILE########
__FILENAME__ = test_tag_mixpanel
"""
Tests for the Mixpanel tags and filters.
"""

from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpRequest
from django.template import Context

from analytical.templatetags.mixpanel import MixpanelNode
from analytical.tests.utils import TagTestCase, override_settings, SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(MIXPANEL_API_TOKEN='0123456789abcdef0123456789abcdef')
class MixpanelTagTestCase(TagTestCase):
    """
    Tests for the ``mixpanel`` template tag.
    """

    def test_tag(self):
        r = self.render_tag('mixpanel', 'mixpanel')
        self.assertTrue(
                "mixpanel.init('0123456789abcdef0123456789abcdef');" in r,
                r)

    def test_node(self):
        r = MixpanelNode().render(Context())
        self.assertTrue(
                "mixpanel.init('0123456789abcdef0123456789abcdef');" in r,
                r)

    @override_settings(MIXPANEL_API_TOKEN=SETTING_DELETED)
    def test_no_token(self):
        self.assertRaises(AnalyticalException, MixpanelNode)

    @override_settings(MIXPANEL_API_TOKEN='0123456789abcdef0123456789abcdef0')
    def test_token_too_long(self):
        self.assertRaises(AnalyticalException, MixpanelNode)

    @override_settings(MIXPANEL_API_TOKEN='0123456789abcdef0123456789abcde')
    def test_token_too_short(self):
        self.assertRaises(AnalyticalException, MixpanelNode)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify(self):
        r = MixpanelNode().render(Context({'user': User(username='test')}))
        self.assertTrue("mixpanel.register_once({distinct_id: 'test'});" in r, r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify_anonymous_user(self):
        r = MixpanelNode().render(Context({'user': AnonymousUser()}))
        self.assertFalse("mixpanel.register_once({distinct_id:" in r, r)

    def test_event(self):
        r = MixpanelNode().render(Context({'mixpanel_event':
            ('test_event', {'prop1': 'val1', 'prop2': 'val2'})}))
        self.assertTrue("mixpanel.track('test_event', "
                        '{"prop1": "val1", "prop2": "val2"});' in r, r)

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        r = MixpanelNode().render(context)
        self.assertTrue(r.startswith(
                '<!-- Mixpanel disabled on internal IP address'), r)
        self.assertTrue(r.endswith('-->'), r)

########NEW FILE########
__FILENAME__ = test_tag_olark
"""
Tests for the Olark template tags and filters.
"""

from django.contrib.auth.models import User, AnonymousUser
from django.template import Context

from analytical.templatetags.olark import OlarkNode
from analytical.tests.utils import TagTestCase, override_settings, SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(OLARK_SITE_ID='1234-567-89-0123')
class OlarkTestCase(TagTestCase):
    """
    Tests for the ``olark`` template tag.
    """

    def test_tag(self):
        r = self.render_tag('olark', 'olark')
        self.assertTrue("olark.identify('1234-567-89-0123');" in r, r)

    def test_node(self):
        r = OlarkNode().render(Context())
        self.assertTrue("olark.identify('1234-567-89-0123');" in r, r)

    @override_settings(OLARK_SITE_ID=SETTING_DELETED)
    def test_no_site_id(self):
        self.assertRaises(AnalyticalException, OlarkNode)

    @override_settings(OLARK_SITE_ID='1234-567-8901234')
    def test_wrong_site_id(self):
        self.assertRaises(AnalyticalException, OlarkNode)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify(self):
        r = OlarkNode().render(Context({'user':
                User(username='test', first_name='Test', last_name='User')}))
        self.assertTrue("olark('api.chat.updateVisitorNickname', "
                "{snippet: 'Test User (test)'});" in r, r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify_anonymous_user(self):
        r = OlarkNode().render(Context({'user': AnonymousUser()}))
        self.assertFalse("olark('api.chat.updateVisitorNickname', " in r, r)

    def test_nickname(self):
        r = OlarkNode().render(Context({'olark_nickname': 'testnick'}))
        self.assertTrue("olark('api.chat.updateVisitorNickname', "
                "{snippet: 'testnick'});" in r, r)

    def test_status_string(self):
        r = OlarkNode().render(Context({'olark_status': 'teststatus'}))
        self.assertTrue("olark('api.chat.updateVisitorStatus', "
                '{snippet: "teststatus"});' in r, r)

    def test_status_string_list(self):
        r = OlarkNode().render(Context({'olark_status':
                ['teststatus1', 'teststatus2']}))
        self.assertTrue("olark('api.chat.updateVisitorStatus', "
                '{snippet: ["teststatus1", "teststatus2"]});' in r, r)

    def test_messages(self):
        messages = [
            "welcome_title",
            "chatting_title",
            "unavailable_title",
            "busy_title",
            "away_message",
            "loading_title",
            "welcome_message",
            "busy_message",
            "chat_input_text",
            "name_input_text",
            "email_input_text",
            "offline_note_message",
            "send_button_text",
            "offline_note_thankyou_text",
            "offline_note_error_text",
            "offline_note_sending_text",
            "operator_is_typing_text",
            "operator_has_stopped_typing_text",
            "introduction_error_text",
            "introduction_messages",
            "introduction_submit_button_text",
        ]
        vars = dict(('olark_%s' % m, m) for m in messages)
        r = OlarkNode().render(Context(vars))
        for m in messages:
            self.assertTrue("olark.configure('locale.%s', \"%s\");" % (m, m)
                    in r, r)

########NEW FILE########
__FILENAME__ = test_tag_optimizely
"""
Tests for the Optimizely template tags and filters.
"""

from django.http import HttpRequest
from django.template import Context

from analytical.templatetags.optimizely import OptimizelyNode
from analytical.tests.utils import TagTestCase, override_settings, SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(OPTIMIZELY_ACCOUNT_NUMBER='1234567')
class OptimizelyTagTestCase(TagTestCase):
    """
    Tests for the ``optimizely`` template tag.
    """

    def test_tag(self):
        self.assertEqual(
                '<script src="//cdn.optimizely.com/js/1234567.js"></script>',
                self.render_tag('optimizely', 'optimizely'))

    def test_node(self):
        self.assertEqual(
                '<script src="//cdn.optimizely.com/js/1234567.js"></script>',
                OptimizelyNode().render(Context()))

    @override_settings(OPTIMIZELY_ACCOUNT_NUMBER=SETTING_DELETED)
    def test_no_account_number(self):
        self.assertRaises(AnalyticalException, OptimizelyNode)

    @override_settings(OPTIMIZELY_ACCOUNT_NUMBER='123abc')
    def test_wrong_account_number(self):
        self.assertRaises(AnalyticalException, OptimizelyNode)

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        r = OptimizelyNode().render(context)
        self.assertTrue(r.startswith(
                '<!-- Optimizely disabled on internal IP address'), r)
        self.assertTrue(r.endswith('-->'), r)

########NEW FILE########
__FILENAME__ = test_tag_performable
"""
Tests for the Performable template tags and filters.
"""

from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpRequest
from django.template import Context

from analytical.templatetags.performable import PerformableNode
from analytical.tests.utils import TagTestCase, override_settings, SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(PERFORMABLE_API_KEY='123ABC')
class PerformableTagTestCase(TagTestCase):
    """
    Tests for the ``performable`` template tag.
    """

    def test_tag(self):
        r = self.render_tag('performable', 'performable')
        self.assertTrue('/performable/pax/123ABC.js' in r, r)

    def test_node(self):
        r = PerformableNode().render(Context())
        self.assertTrue('/performable/pax/123ABC.js' in r, r)

    @override_settings(PERFORMABLE_API_KEY=SETTING_DELETED)
    def test_no_api_key(self):
        self.assertRaises(AnalyticalException, PerformableNode)

    @override_settings(PERFORMABLE_API_KEY='123 ABC')
    def test_wrong_account_number(self):
        self.assertRaises(AnalyticalException, PerformableNode)

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        r = PerformableNode().render(context)
        self.assertTrue(r.startswith(
                '<!-- Performable disabled on internal IP address'), r)
        self.assertTrue(r.endswith('-->'), r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify(self):
        r = PerformableNode().render(Context({'user': User(username='test')}))
        self.assertTrue('_paq.push(["identify", {identity: "test"}]);' in r, r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify_anonymous_user(self):
        r = PerformableNode().render(Context({'user': AnonymousUser()}))
        self.assertFalse('_paq.push(["identify", ' in r, r)


class PerformableEmbedTagTestCase(TagTestCase):
    """
    Tests for the ``performable_embed`` template tag.
    """

    def test_tag(self):
        domain = 'example.com'
        page = 'test'
        r = self.render_tag('performable', 'performable_embed "%s" "%s"'
                % (domain, page))
        self.assertTrue(
                "$f.initialize({'host': 'example.com', 'page': 'test'});" in r,
                r)

########NEW FILE########
__FILENAME__ = test_tag_reinvigorate
"""
Tests for the Reinvigorate template tags and filters.
"""

import re

from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpRequest
from django.template import Context

from analytical.templatetags.reinvigorate import ReinvigorateNode
from analytical.tests.utils import TagTestCase, override_settings, \
        SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(REINVIGORATE_TRACKING_ID='12345-abcdefghij')
class ReinvigorateTagTestCase(TagTestCase):
    """
    Tests for the ``reinvigorate`` template tag.
    """

    def test_tag(self):
        r = self.render_tag('reinvigorate', 'reinvigorate')
        self.assertTrue('reinvigorate.track("12345-abcdefghij");' in r, r)

    def test_node(self):
        r = ReinvigorateNode().render(Context({}))
        self.assertTrue('reinvigorate.track("12345-abcdefghij");' in r, r)

    @override_settings(REINVIGORATE_TRACKING_ID=SETTING_DELETED)
    def test_no_tracking_id(self):
        self.assertRaises(AnalyticalException, ReinvigorateNode)

    @override_settings(REINVIGORATE_TRACKING_ID='123abc')
    def test_wrong_tracking_id(self):
        self.assertRaises(AnalyticalException, ReinvigorateNode)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify(self):
        r = ReinvigorateNode().render(Context({'user':
                User(username='test', first_name='Test', last_name='User',
                    email='test@example.com')}))
        self.assertTrue('var re_name_tag = "Test User";' in r, r)
        self.assertTrue('var re_context_tag = "test@example.com";' in r, r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify_anonymous_user(self):
        r = ReinvigorateNode().render(Context({'user': AnonymousUser()}))
        self.assertFalse('var re_name_tag = ' in r, r)
        self.assertFalse('var re_context_tag = ' in r, r)

    def test_tags(self):
        r = ReinvigorateNode().render(Context({'reinvigorate_var1': 'val1',
                'reinvigorate_var2': 2}))
        self.assertTrue(re.search('var re_var1_tag = "val1";', r), r)
        self.assertTrue(re.search('var re_var2_tag = 2;', r), r)

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        r = ReinvigorateNode().render(context)
        self.assertTrue(r.startswith(
                '<!-- Reinvigorate disabled on internal IP address'), r)
        self.assertTrue(r.endswith('-->'), r)

########NEW FILE########
__FILENAME__ = test_tag_snapengage
"""
Tests for the SnapEngage template tags and filters.
"""

from django.contrib.auth.models import User, AnonymousUser
from django.template import Context
from django.utils import translation

from analytical.templatetags.snapengage import SnapEngageNode, \
        BUTTON_STYLE_LIVE, BUTTON_STYLE_DEFAULT, BUTTON_STYLE_NONE, \
        BUTTON_LOCATION_LEFT, BUTTON_LOCATION_RIGHT, BUTTON_LOCATION_TOP, \
        BUTTON_LOCATION_BOTTOM, FORM_POSITION_TOP_LEFT
from analytical.tests.utils import TagTestCase, override_settings, \
        SETTING_DELETED
from analytical.utils import AnalyticalException


WIDGET_ID = 'ec329c69-0bf0-4db8-9b77-3f8150fb977e'


@override_settings(
    SNAPENGAGE_WIDGET_ID=WIDGET_ID,
    SNAPENGAGE_BUTTON=BUTTON_STYLE_DEFAULT,
    SNAPENGAGE_BUTTON_LOCATION=BUTTON_LOCATION_LEFT,
    SNAPENGAGE_BUTTON_OFFSET="55%",
)
class SnapEngageTestCase(TagTestCase):
    """
    Tests for the ``snapengage`` template tag.
    """

    def test_tag(self):
        r = self.render_tag('snapengage', 'snapengage')
        self.assertTrue(
            'SnapABug.addButton("ec329c69-0bf0-4db8-9b77-3f8150fb977e","0",'
            '"55%");' in r, r)

    def test_node(self):
        r = SnapEngageNode().render(Context())
        self.assertTrue(
            'SnapABug.addButton("ec329c69-0bf0-4db8-9b77-3f8150fb977e","0",'
            '"55%");' in r, r)

    @override_settings(SNAPENGAGE_WIDGET_ID=SETTING_DELETED)
    def test_no_site_id(self):
        self.assertRaises(AnalyticalException, SnapEngageNode)

    @override_settings(SNAPENGAGE_WIDGET_ID='abc')
    def test_wrong_site_id(self):
        self.assertRaises(AnalyticalException, SnapEngageNode)

    def test_no_button(self):
        r = SnapEngageNode().render(Context({'snapengage_button': BUTTON_STYLE_NONE}))
        self.assertTrue('SnapABug.init("ec329c69-0bf0-4db8-9b77-3f8150fb977e")'
                in r, r)
        with override_settings(SNAPENGAGE_BUTTON=BUTTON_STYLE_NONE):
            r = SnapEngageNode().render(Context())
            self.assertTrue(
                'SnapABug.init("ec329c69-0bf0-4db8-9b77-3f8150fb977e")' in r, r)

    def test_live_button(self):
        r = SnapEngageNode().render(Context({'snapengage_button': BUTTON_STYLE_LIVE}))
        self.assertTrue(
            'SnapABug.addButton("ec329c69-0bf0-4db8-9b77-3f8150fb977e","0",'
            '"55%",true);' in r, r)
        with override_settings(SNAPENGAGE_BUTTON=BUTTON_STYLE_LIVE):
            r = SnapEngageNode().render(Context())
            self.assertTrue(
                'SnapABug.addButton("ec329c69-0bf0-4db8-9b77-3f8150fb977e","0",'
                '"55%",true);' in r, r)

    def test_custom_button(self):
        r = SnapEngageNode().render(Context({
            'snapengage_button': "http://www.example.com/button.png"}))
        self.assertTrue(
            'SnapABug.addButton("ec329c69-0bf0-4db8-9b77-3f8150fb977e","0",'
            '"55%");' in r, r)
        self.assertTrue(
            'SnapABug.setButton("http://www.example.com/button.png");' in r, r)
        with override_settings(
                SNAPENGAGE_BUTTON="http://www.example.com/button.png"):
            r = SnapEngageNode().render(Context())
            self.assertTrue(
                'SnapABug.addButton("ec329c69-0bf0-4db8-9b77-3f8150fb977e","0",'
                '"55%");' in r, r)
            self.assertTrue(
                'SnapABug.setButton("http://www.example.com/button.png");' in r,
                r)

    def test_button_location_right(self):
        r = SnapEngageNode().render(Context({
            'snapengage_button_location': BUTTON_LOCATION_RIGHT}))
        self.assertTrue(
            'SnapABug.addButton("ec329c69-0bf0-4db8-9b77-3f8150fb977e","1",'
            '"55%");' in r, r)
        with override_settings(
            SNAPENGAGE_BUTTON_LOCATION=BUTTON_LOCATION_RIGHT):
            r = SnapEngageNode().render(Context())
            self.assertTrue(
                'SnapABug.addButton("ec329c69-0bf0-4db8-9b77-3f8150fb977e","1",'
                '"55%");' in r, r)

    def test_button_location_top(self):
        r = SnapEngageNode().render(Context({
            'snapengage_button_location': BUTTON_LOCATION_TOP}))
        self.assertTrue(
            'SnapABug.addButton("ec329c69-0bf0-4db8-9b77-3f8150fb977e","2",'
            '"55%");' in r, r)
        with override_settings(SNAPENGAGE_BUTTON_LOCATION=BUTTON_LOCATION_TOP):
            r = SnapEngageNode().render(Context())
            self.assertTrue(
                'SnapABug.addButton("ec329c69-0bf0-4db8-9b77-3f8150fb977e","2",'
                '"55%");' in r, r)

    def test_button_location_bottom(self):
        r = SnapEngageNode().render(Context({
            'snapengage_button_location': BUTTON_LOCATION_BOTTOM}))
        self.assertTrue(
            'SnapABug.addButton("ec329c69-0bf0-4db8-9b77-3f8150fb977e","3",'
            '"55%");' in r, r)
        with override_settings(
                SNAPENGAGE_BUTTON_LOCATION=BUTTON_LOCATION_BOTTOM):
            r = SnapEngageNode().render(Context())
            self.assertTrue(
                'SnapABug.addButton("ec329c69-0bf0-4db8-9b77-3f8150fb977e","3",'
                '"55%");' in r, r)

    def test_button_offset(self):
        r = SnapEngageNode().render(Context({
            'snapengage_button_location_offset': "30%"}))
        self.assertTrue(
            'SnapABug.addButton("ec329c69-0bf0-4db8-9b77-3f8150fb977e","0",'
            '"30%");' in r, r)
        with override_settings(SNAPENGAGE_BUTTON_LOCATION_OFFSET="30%"):
            r = SnapEngageNode().render(Context())
            self.assertTrue(
                'SnapABug.addButton("ec329c69-0bf0-4db8-9b77-3f8150fb977e","0",'
                '"30%");' in r, r)

    def test_button_effect(self):
        r = SnapEngageNode().render(Context({
            'snapengage_button_effect': "-4px"}))
        self.assertTrue('SnapABug.setButtonEffect("-4px");' in r, r)
        with override_settings(SNAPENGAGE_BUTTON_EFFECT="-4px"):
            r = SnapEngageNode().render(Context())
            self.assertTrue('SnapABug.setButtonEffect("-4px");' in r, r)

    def test_form_position(self):
        r = SnapEngageNode().render(Context({
            'snapengage_form_position': FORM_POSITION_TOP_LEFT}))
        self.assertTrue('SnapABug.setChatFormPosition("tl");' in r, r)
        with override_settings(SNAPENGAGE_FORM_POSITION=FORM_POSITION_TOP_LEFT):
            r = SnapEngageNode().render(Context())
            self.assertTrue('SnapABug.setChatFormPosition("tl");' in r, r)

    def test_form_top_position(self):
        r = SnapEngageNode().render(Context({
            'snapengage_form_top_position': 40}))
        self.assertTrue('SnapABug.setFormTopPosition(40);' in r, r)
        with override_settings(SNAPENGAGE_FORM_TOP_POSITION=40):
            r = SnapEngageNode().render(Context())
            self.assertTrue('SnapABug.setFormTopPosition(40);' in r, r)

    def test_domain(self):
        r = SnapEngageNode().render(Context({
            'snapengage_domain': "example.com"}))
        self.assertTrue('SnapABug.setDomain("example.com");' in r, r)
        with override_settings(SNAPENGAGE_DOMAIN="example.com"):
            r = SnapEngageNode().render(Context())
            self.assertTrue('SnapABug.setDomain("example.com");' in r, r)

    def test_secure_connection(self):
        r = SnapEngageNode().render(Context({
            'snapengage_secure_connection': True}))
        self.assertTrue('SnapABug.setSecureConnexion();' in r, r)
        with override_settings(SNAPENGAGE_SECURE_CONNECTION=True):
            r = SnapEngageNode().render(Context())
            self.assertTrue('SnapABug.setSecureConnexion();' in r, r)

    def test_show_offline(self):
        r = SnapEngageNode().render(Context({'snapengage_show_offline': False}))
        self.assertTrue('SnapABug.allowOffline(false);' in r, r)
        with override_settings(SNAPENGAGE_SHOW_OFFLINE=False):
            r = SnapEngageNode().render(Context())
            self.assertTrue('SnapABug.allowOffline(false);' in r, r)

    def test_proactive_chat(self):
        r = SnapEngageNode().render(Context({
            'snapengage_proactive_chat': False}))
        self.assertTrue('SnapABug.allowProactiveChat(false);' in r, r)

    def test_screenshot(self):
        r = SnapEngageNode().render(Context({'snapengage_screenshots': False}))
        self.assertTrue('SnapABug.allowScreenshot(false);' in r, r)
        with override_settings(SNAPENGAGE_SCREENSHOTS=False):
            r = SnapEngageNode().render(Context())
            self.assertTrue('SnapABug.allowScreenshot(false);' in r, r)

    def test_offline_screenshots(self):
        r = SnapEngageNode().render(Context(
                {'snapengage_offline_screenshots': False}))
        self.assertTrue('SnapABug.showScreenshotOption(false);' in r, r)
        with override_settings(SNAPENGAGE_OFFLINE_SCREENSHOTS=False):
            r = SnapEngageNode().render(Context())
            self.assertTrue('SnapABug.showScreenshotOption(false);' in r, r)

    def test_sounds(self):
        r = SnapEngageNode().render(Context({'snapengage_sounds': False}))
        self.assertTrue('SnapABug.allowChatSound(false);' in r, r)
        with override_settings(SNAPENGAGE_SOUNDS=False):
            r = SnapEngageNode().render(Context())
            self.assertTrue('SnapABug.allowChatSound(false);' in r, r)

    @override_settings(SNAPENGAGE_READONLY_EMAIL=False)
    def test_email(self):
        r = SnapEngageNode().render(Context({'snapengage_email':
                'test@example.com'}))
        self.assertTrue('SnapABug.setUserEmail("test@example.com");' in r, r)

    def test_email_readonly(self):
        r = SnapEngageNode().render(Context({'snapengage_email':
                'test@example.com', 'snapengage_readonly_email': True}))
        self.assertTrue('SnapABug.setUserEmail("test@example.com",true);' in r,
                r)
        with override_settings(SNAPENGAGE_READONLY_EMAIL=True):
            r = SnapEngageNode().render(Context({'snapengage_email':
                    'test@example.com'}))
            self.assertTrue('SnapABug.setUserEmail("test@example.com",true);'
                    in r, r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify(self):
        r = SnapEngageNode().render(Context({'user':
                User(username='test', email='test@example.com')}))
        self.assertTrue('SnapABug.setUserEmail("test@example.com");' in r, r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify_anonymous_user(self):
        r = SnapEngageNode().render(Context({'user': AnonymousUser()}))
        self.assertFalse('SnapABug.setUserEmail(' in r, r)

    def test_language(self):
        r = SnapEngageNode().render(Context({'snapengage_locale': 'fr'}))
        self.assertTrue('SnapABug.setLocale("fr");' in r, r)
        with override_settings(SNAPENGAGE_LOCALE='fr'):
            r = SnapEngageNode().render(Context())
            self.assertTrue('SnapABug.setLocale("fr");' in r, r)

    def test_automatic_language(self):
        real_get_language = translation.get_language
        try:
            translation.get_language = lambda: 'fr-ca'
            r = SnapEngageNode().render(Context())
            self.assertTrue('SnapABug.setLocale("fr_CA");' in r, r)
        finally:
            translation.get_language = real_get_language

########NEW FILE########
__FILENAME__ = test_tag_spring_metrics
"""
Tests for the Spring Metrics template tags and filters.
"""

import re

from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpRequest
from django.template import Context

from analytical.templatetags.spring_metrics import SpringMetricsNode
from analytical.tests.utils import TagTestCase, override_settings, \
        SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(SPRING_METRICS_TRACKING_ID='12345678')
class SpringMetricsTagTestCase(TagTestCase):
    """
    Tests for the ``spring_metrics`` template tag.
    """

    def test_tag(self):
        r = self.render_tag('spring_metrics', 'spring_metrics')
        self.assertTrue("_springMetq.push(['id', '12345678']);" in r, r)

    def test_node(self):
        r = SpringMetricsNode().render(Context({}))
        self.assertTrue("_springMetq.push(['id', '12345678']);" in r, r)

    @override_settings(SPRING_METRICS_TRACKING_ID=SETTING_DELETED)
    def test_no_site_id(self):
        self.assertRaises(AnalyticalException, SpringMetricsNode)

    @override_settings(SPRING_METRICS_TRACKING_ID='123xyz')
    def test_wrong_site_id(self):
        self.assertRaises(AnalyticalException, SpringMetricsNode)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify(self):
        r = SpringMetricsNode().render(Context({'user':
                User(email='test@test.com')}))
        self.assertTrue("_springMetq.push(['setdata', "
                "{'email': 'test@test.com'}]);" in r, r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify_anonymous_user(self):
        r = SpringMetricsNode().render(Context({'user': AnonymousUser()}))
        self.assertFalse("_springMetq.push(['setdata', {'email':" in r, r)

    def test_custom(self):
        r = SpringMetricsNode().render(Context({'spring_metrics_var1': 'val1',
                'spring_metrics_var2': 'val2'}))
        self.assertTrue("_springMetq.push(['setdata', {'var1': 'val1'}]);" in r,
                r)
        self.assertTrue("_springMetq.push(['setdata', {'var2': 'val2'}]);" in r,
                r)

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        r = SpringMetricsNode().render(context)
        self.assertTrue(r.startswith(
                '<!-- Spring Metrics disabled on internal IP address'), r)
        self.assertTrue(r.endswith('-->'), r)

########NEW FILE########
__FILENAME__ = test_tag_uservoice
"""
Tests for the UserVoice tags and filters.
"""

from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpRequest
from django.template import Context

from analytical.templatetags.uservoice import UserVoiceNode
from analytical.tests.utils import TagTestCase, override_settings, \
        SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(USERVOICE_WIDGET_KEY='abcdefghijklmnopqrst')
class UserVoiceTagTestCase(TagTestCase):
    """
    Tests for the ``uservoice`` template tag.
    """

    def assertIn(self, element, container):
        try:
            super(TagTestCase, self).assertIn(element, container)
        except AttributeError:
            self.assertTrue(element in container)

    def test_node(self):
        r = UserVoiceNode().render(Context())
        self.assertIn("widget.uservoice.com/abcdefghijklmnopqrst.js", r)

    def test_tag(self):
        r = self.render_tag('uservoice', 'uservoice')
        self.assertIn("widget.uservoice.com/abcdefghijklmnopqrst.js", r)

    @override_settings(USERVOICE_WIDGET_KEY=SETTING_DELETED)
    def test_no_key(self):
        self.assertRaises(AnalyticalException, UserVoiceNode)

    @override_settings(USERVOICE_WIDGET_KEY='abcdefgh ijklmnopqrst')
    def test_invalid_key(self):
        self.assertRaises(AnalyticalException, UserVoiceNode)

    @override_settings(USERVOICE_WIDGET_KEY='')
    def test_empty_key(self):
        r = UserVoiceNode().render(Context())
        self.assertEqual(r, "")

    @override_settings(USERVOICE_WIDGET_KEY='')
    def test_overridden_empty_key(self):
        vars = {'uservoice_widget_key': 'bcdefghijklmnopqrstu'}
        r = UserVoiceNode().render(Context(vars))
        self.assertIn("widget.uservoice.com/bcdefghijklmnopqrstu.js", r)

    def test_overridden_key(self):
        vars = {'uservoice_widget_key': 'defghijklmnopqrstuvw'}
        r = UserVoiceNode().render(Context(vars))
        self.assertIn("widget.uservoice.com/defghijklmnopqrstuvw.js", r)

    @override_settings(USERVOICE_WIDGET_OPTIONS={'key1': 'val1'})
    def test_options(self):
        r = UserVoiceNode().render(Context())
        self.assertIn("""UserVoice.push(['set', {"key1": "val1"}]);""", r)

    @override_settings(USERVOICE_WIDGET_OPTIONS={'key1': 'val1'})
    def test_override_options(self):
        data = {'uservoice_widget_options': {'key1': 'val2'}}
        r = UserVoiceNode().render(Context(data))
        self.assertIn("""UserVoice.push(['set', {"key1": "val2"}]);""", r)

    def test_auto_trigger(self):
        r = UserVoiceNode().render(Context())
        self.assertTrue("UserVoice.push(['addTrigger', {}]);" in r, r)

    @override_settings(USERVOICE_ADD_TRIGGER=False)
    def test_auto_trigger(self):
        r = UserVoiceNode().render(Context())
        self.assertFalse("UserVoice.push(['addTrigger', {}]);" in r, r)

    @override_settings(USERVOICE_ADD_TRIGGER=False)
    def test_auto_trigger_custom_win(self):
        r = UserVoiceNode().render(Context({'uservoice_add_trigger': True}))
        self.assertTrue("UserVoice.push(['addTrigger', {}]);" in r, r)
########NEW FILE########
__FILENAME__ = test_tag_woopra
"""
Tests for the Woopra template tags and filters.
"""

from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpRequest
from django.template import Context

from analytical.templatetags.woopra import WoopraNode
from analytical.tests.utils import TagTestCase, override_settings, \
        SETTING_DELETED
from analytical.utils import AnalyticalException


@override_settings(WOOPRA_DOMAIN='example.com')
class WoopraTagTestCase(TagTestCase):
    """
    Tests for the ``woopra`` template tag.
    """

    def test_tag(self):
        r = self.render_tag('woopra', 'woopra')
        self.assertTrue('var woo_settings = {"domain": "example.com"};' in r, r)

    def test_node(self):
        r = WoopraNode().render(Context({}))
        self.assertTrue('var woo_settings = {"domain": "example.com"};' in r, r)

    @override_settings(WOOPRA_DOMAIN=SETTING_DELETED)
    def test_no_domain(self):
        self.assertRaises(AnalyticalException, WoopraNode)

    @override_settings(WOOPRA_DOMAIN='this is not a domain')
    def test_wrong_domain(self):
        self.assertRaises(AnalyticalException, WoopraNode)

    @override_settings(WOOPRA_IDLE_TIMEOUT=1234)
    def test_idle_timeout(self):
        r = WoopraNode().render(Context({}))
        self.assertTrue('var woo_settings = {"domain": "example.com", '
                '"idle_timeout": "1234"};' in r, r)

    def test_custom(self):
        r = WoopraNode().render(Context({'woopra_var1': 'val1',
                'woopra_var2': 'val2'}))
        self.assertTrue('var woo_visitor = {"var1": "val1", "var2": "val2"};'
            in r, r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify_name_and_email(self):
        r = WoopraNode().render(Context({'user': User(username='test',
                first_name='Firstname', last_name='Lastname',
                email="test@example.com")}))
        self.assertTrue('var woo_visitor = {"email": "test@example.com", '
                '"name": "Firstname Lastname"};' in r, r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify_username_no_email(self):
        r = WoopraNode().render(Context({'user': User(username='test')}))
        self.assertTrue('var woo_visitor = {"name": "test"};' in r, r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_no_identify_when_explicit_name(self):
        r = WoopraNode().render(Context({'woopra_name': 'explicit',
                'user': User(username='implicit')}))
        self.assertTrue('var woo_visitor = {"name": "explicit"};' in r, r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_no_identify_when_explicit_email(self):
        r = WoopraNode().render(Context({'woopra_email': 'explicit',
                'user': User(username='implicit')}))
        self.assertTrue('var woo_visitor = {"email": "explicit"};' in r, r)

    @override_settings(ANALYTICAL_AUTO_IDENTIFY=True)
    def test_identify_anonymous_user(self):
        r = WoopraNode().render(Context({'user': AnonymousUser()}))
        self.assertTrue('var woo_visitor = {};' in r, r)

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        r = WoopraNode().render(context)
        self.assertTrue(r.startswith(
                '<!-- Woopra disabled on internal IP address'), r)
        self.assertTrue(r.endswith('-->'), r)

########NEW FILE########
__FILENAME__ = test_utils
"""
Tests for the analytical.utils module.
"""

from django.conf import settings
from django.contrib.sites.models import Site
from django.http import HttpRequest
from django.template import Context

from analytical.utils import (
    get_domain, is_internal_ip, get_required_setting, AnalyticalException)
from analytical.tests.utils import (
    TestCase, override_settings, with_apps, SETTING_DELETED)


class SettingDeletedTestCase(TestCase):
    @override_settings(USER_ID=SETTING_DELETED)
    def test_deleted_setting_raises_exception(self):
        self.assertRaises(AttributeError, getattr, settings, "USER_ID")

    @override_settings(USER_ID=1)
    def test_only_disable_within_context_manager(self):
        """
        Make sure deleted settings returns once the block exits.
        """
        self.assertEqual(settings.USER_ID, 1)

        with override_settings(USER_ID=SETTING_DELETED):
            self.assertRaises(AttributeError, getattr, settings, "USER_ID")

        self.assertEqual(settings.USER_ID, 1)

    @override_settings(USER_ID=SETTING_DELETED)
    def test_get_required_setting(self):
        """
        Make sure using get_required_setting fails in the right place.
        """
        # only available in python >= 2.7
        if hasattr(self, 'assertRaisesRegexp'):
            with self.assertRaisesRegexp(AnalyticalException, "^USER_ID setting: not found$"):
                user_id = get_required_setting("USER_ID", "\d+", "invalid USER_ID")
        else:
            self.assertRaises(AnalyticalException,
                              get_required_setting, "USER_ID", "\d+", "invalid USER_ID")

@override_settings(ANALYTICAL_DOMAIN="example.org")
class GetDomainTestCase(TestCase):
    def test_get_service_domain_from_context(self):
        context = Context({'test_domain': 'example.com'})
        self.assertEqual(get_domain(context, 'test'), 'example.com')

    def test_get_analytical_domain_from_context(self):
        context = Context({'analytical_domain': 'example.com'})
        self.assertEqual(get_domain(context, 'test'), 'example.com')

    @override_settings(TEST_DOMAIN="example.net")
    def test_get_service_domain_from_settings(self):
        context = Context()
        self.assertEqual(get_domain(context, 'test'), 'example.net')

    def test_get_analytical_domain_from_settings(self):
        context = Context()
        self.assertEqual(get_domain(context, 'test'), 'example.org')


# FIXME: enable Django apps dynamically and enable test again
#@with_apps('django.contrib.sites')
#@override_settings(TEST_DOMAIN=SETTING_DELETED,
#        ANALYTICAL_DOMAIN=SETTING_DELETED)
#class GetDomainTestCaseWithSites(TestCase):
#    def test_get_domain_from_site(self):
#        site = Site.objects.create(domain="example.com", name="test")
#        with override_settings(SITE_ID=site.id):
#            context = Context()
#            self.assertEqual(get_domain(context, 'test'), 'example.com')


class InternalIpTestCase(TestCase):

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_no_internal_ip(self):
        context = Context()
        self.assertFalse(is_internal_ip(context))

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        self.assertTrue(is_internal_ip(context))

    @override_settings(TEST_INTERNAL_IPS=['1.1.1.1'])
    def test_render_prefix_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        self.assertTrue(is_internal_ip(context, 'TEST'))

    @override_settings(INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip_fallback(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '1.1.1.1'
        context = Context({'request': req})
        self.assertTrue(is_internal_ip(context))

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_internal_ip_forwarded_for(self):
        req = HttpRequest()
        req.META['HTTP_X_FORWARDED_FOR'] = '1.1.1.1'
        context = Context({'request': req})
        self.assertTrue(is_internal_ip(context))

    @override_settings(ANALYTICAL_INTERNAL_IPS=['1.1.1.1'])
    def test_render_different_internal_ip(self):
        req = HttpRequest()
        req.META['REMOTE_ADDR'] = '2.2.2.2'
        context = Context({'request': req})
        self.assertFalse(is_internal_ip(context))

########NEW FILE########
__FILENAME__ = utils
"""
Testing utilities.
"""

from __future__ import with_statement

import copy

from django.conf import settings, UserSettingsHolder
from django.core.management import call_command
from django.db.models import loading
from django.template import Template, Context, RequestContext
from django.test.testcases import TestCase
from django.utils.functional import wraps


SETTING_DELETED = object()


# Backported adapted from Django trunk (r16377)
class override_settings(object):
    """
    Temporarily override Django settings.

    Can be used as either a decorator on test classes/functions or as
    a context manager inside test functions.

    In either case it temporarily overrides django.conf.settings so
    that you can test how code acts when certain settings are set to
    certain values or deleted altogether with SETTING_DELETED.

    >>> @override_settings(FOOBAR=42)
    >>> class TestBaz(TestCase):
    >>>     # settings.FOOBAR == 42 for all tests
    >>>
    >>>     @override_settings(FOOBAR=43)
    >>>     def test_widget(self):
    >>>         # settings.FOOBAR == 43 for just this test
    >>>
    >>>         with override_settings(FOOBAR=44):
    >>>             # settings.FOOBAR == 44 just inside this block
    >>>             pass
    >>>
    >>>         # settings.FOOBAR == 43 inside the test
    """
    def __init__(self, **kwargs):
        self.options = kwargs
        self.wrapped = settings._wrapped

    def __enter__(self):
        self.enable()

    def __exit__(self, exc_type, exc_value, traceback):
        self.disable()

    def __call__(self, test_func):
        from django.test import TransactionTestCase
        if isinstance(test_func, type) and issubclass(test_func, TransactionTestCase):
            # When decorating a class, we need to construct a new class
            # with the same name so that the test discovery tools can
            # get a useful name.
            def _pre_setup(innerself):
                self.enable()
                test_func._pre_setup(innerself)
            def _post_teardown(innerself):
                test_func._post_teardown(innerself)
                self.disable()
            inner = type(
                test_func.__name__,
                (test_func,),
                {
                    '_pre_setup': _pre_setup,
                    '_post_teardown': _post_teardown,
                    '__module__': test_func.__module__,
                })
        else:
            @wraps(test_func)
            def inner(*args, **kwargs):
                with self:
                    return test_func(*args, **kwargs)
        return inner

    def enable(self):
        class OverrideSettingsHolder(UserSettingsHolder):
            def __getattr__(self, name):
                if name == "default_settings":
                    return self.__dict__["default_settings"]
                return getattr(self.default_settings, name)

        override = OverrideSettingsHolder(copy.copy(settings._wrapped))
        for key, new_value in self.options.items():
            if new_value is SETTING_DELETED:
                try:
                    delattr(override.default_settings, key)
                except AttributeError:
                    pass
            else:
                setattr(override, key, new_value)
        settings._wrapped = override

    def disable(self):
        settings._wrapped = self.wrapped


def run_tests():
    """
    Use the Django test runner to run the tests.

    Sets the return code to the number of failed tests.
    """
    import sys
    from django.test.simple import DjangoTestSuiteRunner
    runner = DjangoTestSuiteRunner()
    sys.exit(runner.run_tests(["analytical"]))


def with_apps(*apps):
    """
    Class decorator that makes sure the passed apps are present in
    INSTALLED_APPS.
    """
    apps_set = set(settings.INSTALLED_APPS)
    apps_set.update(apps)
    return override_settings(INSTALLED_APPS=list(apps_set))


def without_apps(*apps):
    """
    Class decorator that makes sure the passed apps are not present in
    INSTALLED_APPS.
    """
    apps_list = [a for a in settings.INSTALLED_APPS if a not in apps]
    return override_settings(INSTALLED_APPS=apps_list)


class TagTestCase(TestCase):
    """
    Tests for a template tag.

    Adds support methods for testing template tags.
    """

    def render_tag(self, library, tag, vars=None, request=None):
        if vars is None:
            vars = {}
        t = Template("{%% load %s %%}{%% %s %%}" % (library, tag))
        if request is not None:
            context = RequestContext(request, vars)
        else:
            context = Context(vars)
        return t.render(context)

    def render_template(self, template, vars=None, request=None):
        if vars is None:
            vars = {}
        t = Template(template)
        if request is not None:
            context = RequestContext(request, vars)
        else:
            context = Context(vars)
        return t.render(context)

########NEW FILE########
__FILENAME__ = utils
"""
Utility function for django-analytical.
"""

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured


HTML_COMMENT = "<!-- %(service)s disabled on internal IP " \
        "address\n%(html)s\n-->"


def get_required_setting(setting, value_re, invalid_msg):
    """
    Return a constant from ``django.conf.settings``.  The `setting`
    argument is the constant name, the `value_re` argument is a regular
    expression used to validate the setting value and the `invalid_msg`
    argument is used as exception message if the value is not valid.
    """
    try:
        value = getattr(settings, setting)
    except AttributeError:
        raise AnalyticalException("%s setting: not found" % setting)
    value = str(value)
    if not value_re.search(value):
        raise AnalyticalException("%s setting: %s: '%s'"
                % (setting, invalid_msg, value))
    return value


def get_user_from_context(context):
    """
    Get the user instance from the template context, if possible.

    If the context does not contain a `request` or `user` attribute,
    `None` is returned.
    """
    try:
        return context['user']
    except KeyError:
        pass
    try:
        request = context['request']
        return request.user
    except (KeyError, AttributeError):
        pass
    return None


def get_identity(context, prefix=None, identity_func=None, user=None):
    """
    Get the identity of a logged in user from a template context.

    The `prefix` argument is used to provide different identities to
    different analytics services.  The `identity_func` argument is a
    function that returns the identity of the user; by default the
    identity is the username.
    """
    if prefix is not None:
        try:
            return context['%s_identity' % prefix]
        except KeyError:
            pass
    try:
        return context['analytical_identity']
    except KeyError:
        pass
    if getattr(settings, 'ANALYTICAL_AUTO_IDENTIFY', True):
        try:
            if user is None:
                user = get_user_from_context(context)
            if user.is_authenticated():
                if identity_func is not None:
                    return identity_func(user)
                else:
                    return user.username
        except (KeyError, AttributeError):
            pass
    return None


def get_domain(context, prefix):
    """
    Return the domain used for the tracking code.  Each service may be
    configured with its own domain (called `<name>_domain`), or a
    django-analytical-wide domain may be set (using `analytical_domain`.

    If no explicit domain is found in either the context or the
    settings, try to get the domain from the contrib sites framework.
    """
    domain = context.get('%s_domain' % prefix)
    if domain is None:
        domain = context.get('analytical_domain')
    if domain is None:
        domain = getattr(settings, '%s_DOMAIN' % prefix.upper(), None)
    if domain is None:
        domain = getattr(settings, 'ANALYTICAL_DOMAIN', None)
    if domain is None:
        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            try:
                domain = Site.objects.get_current().domain
            except (ImproperlyConfigured, Site.DoesNotExist):
                pass
    return domain


def is_internal_ip(context, prefix=None):
    """
    Return whether the visitor is coming from an internal IP address,
    based on information from the template context.

    The prefix is used to allow different analytics services to have
    different notions of internal addresses.
    """
    try:
        request = context['request']
        remote_ip = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if not remote_ip:
            remote_ip = request.META.get('REMOTE_ADDR', '')
        if not remote_ip:
            return False

        internal_ips = ''
        if prefix is not None:
            internal_ips = getattr(settings, '%s_INTERNAL_IPS' % prefix, '')
        if not internal_ips:
            internal_ips = getattr(settings, 'ANALYTICAL_INTERNAL_IPS', '')
        if not internal_ips:
            internal_ips = getattr(settings, 'INTERNAL_IPS', '')

        return remote_ip in internal_ips
    except (KeyError, AttributeError):
        return False


def disable_html(html, service):
    """
    Disable HTML code by commenting it out.

    The `service` argument is used to display a friendly message.
    """
    return HTML_COMMENT % {'html': html, 'service': service}


class AnalyticalException(Exception):
    """
    Raised when an exception occurs in any django-analytical code that should
    be silenced in templates.
    """
    silent_variable_failure = True

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# This file is execfile()d with the current directory set to its containing
# directory.

import sys, os
sys.path.append(os.path.join(os.path.abspath('.'), '_ext'))
sys.path.append(os.path.dirname(os.path.abspath('.')))

import analytical


# -- General configuration -----------------------------------------------------

project = u'django-analytical'
copyright = u'2011, Joost Cassee <joost@cassee.net>'

release = analytical.__version__
# The short X.Y version.
version = release.rsplit('.', 1)[0]

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'local']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

add_function_parentheses = True
pygments_style = 'sphinx'

intersphinx_mapping = {
    'http://docs.python.org/2.7': None,
    'http://docs.djangoproject.com/en/1.6': 'http://docs.djangoproject.com/en/1.6/_objects/',
}


# -- Options for HTML output ---------------------------------------------------

html_theme = 'default'
htmlhelp_basename = 'analyticaldoc'


# -- Options for LaTeX output --------------------------------------------------

latex_documents = [
  ('index', 'django-analytical.tex', u'Documentation for django-analytical',
   u'Joost Cassee', 'manual'),
]

########NEW FILE########
__FILENAME__ = local
def setup(app):
    app.add_crossref_type(
        directivename = "setting",
        rolename      = "setting",
        indextemplate = "pair: %s; setting",
    )
    app.add_crossref_type(
        directivename = "templatetag",
        rolename      = "ttag",
        indextemplate = "pair: %s; template tag"
    )
    app.add_crossref_type(
        directivename = "templatefilter",
        rolename      = "tfilter",
        indextemplate = "pair: %s; template filter"
    )
    app.add_crossref_type(
        directivename = "fieldlookup",
        rolename      = "lookup",
        indextemplate = "pair: %s; field lookup type",
    )
    app.add_description_unit(
        directivename = "decorator",
        rolename      = "dec",
        indextemplate = "pair: %s; function decorator",
    )

########NEW FILE########
