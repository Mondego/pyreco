__FILENAME__ = conf
import sys, os

extensions = []
templates_path = []
source_suffix = '.rst'
master_doc = 'index'
project = u'metron'
copyright = u'2011-2013, Eldarion'
exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'default'
htmlhelp_basename = 'metrondoc'
latex_documents = [
  ('index', 'metron.tex', u'metron Documentation',
   u'Eldarion', 'manual'),
]
man_pages = [
    ('index', 'metron', u'metron Documentation',
     [u'Eldarion'], 1)
]

sys.path.insert(0, os.pardir)
m = __import__(project)

version = m.__version__
release = version
########NEW FILE########
__FILENAME__ = activity
import json

from django.conf import settings


SESSION_KEY_NAME = getattr(settings, "METRON_ACTIVITY_SESSION_KEY_NAME", "_metron_activity")


def _key_name(kind):
    return SESSION_KEY_NAME + "-" + kind


def all(request, kind):
    actions = request.session.pop(_key_name(kind), None)
    if actions:
        for action in actions:
            action["args"] = list(action["args"])
            for i, arg in enumerate(action["args"]):
                if isinstance(action["args"][i], dict):
                    action["args"][i] = json.dumps(action["args"][i])
                else:
                    action["args"][i] = repr(action["args"][i])
    return actions


def add(request, kind, method, *args):
    """
    add(request, "mixpanel", "track", "purchase", {order: "1234", amount: "100"})
    add(request, "google", "push", ["_addTrans", "1234", "Gondor", "100"])
    """
    request.session.setdefault(_key_name(kind), []).append({
        "method": method,
        "args": args
    })

########NEW FILE########
__FILENAME__ = metron_tags
from django import template
from django.conf import settings

from metron import activity


register = template.Library()


@register.simple_tag(takes_context=True)
def analytics(context):
    content = ""
    for kind, codes in getattr(settings, "METRON_SETTINGS", {}).items():
        site_id = getattr(context.get("request"), "metron_site_id", settings.SITE_ID)
        code = codes.get(int(site_id))
        if code is not None and "user" in context and "request" in context:
            t = template.loader.get_template("metron/_%s.html" % kind)
            content += t.render(template.Context({
                "code": code,
                "user": context["user"],
                "actions": activity.all(context["request"], kind)
            }))
    return content


@register.simple_tag(takes_context=True)
def adwords_conversion(context, key):
    content = ""
    page_ids = getattr(settings, "METRON_ADWORDS_SETTINGS", {}).get(key)
    if page_ids:
        t = template.loader.get_template("metron/_adwords_conversion.html")
        content = t.render(template.Context({
            "conversion_id": page_ids["conversion_id"],
            "conversion_format": page_ids["conversion_format"],
            "conversion_label": page_ids["conversion_label"]
        }))
    return content

########NEW FILE########
