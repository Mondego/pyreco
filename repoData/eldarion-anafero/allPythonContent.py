__FILENAME__ = admin
from django.contrib import admin

from anafero.models import Referral, ReferralResponse


admin.site.register(
    Referral,
    list_display=[
        "user",
        "code",
        "label",
        "redirect_to",
        "target_content_type",
        "target_object_id"
    ],
    readonly_fields=["code", "created_at"],
    list_filter=["target_content_type", "created_at"],
    search_fields=["user", "code"]
)

admin.site.register(
    ReferralResponse,
    list_display=[
        "referral",
        "session_key",
        "user",
        "ip_address",
        "action"
    ],
    readonly_fields=["referral", "session_key", "user", "ip_address", "action"],
    list_filter=["action", "created_at"],
    search_fields=["referral__code", "referral__user__username", "ip_address"]
)

########NEW FILE########
__FILENAME__ = callbacks
import random


def generate_code(referral_class):
    def _generate_code():
        t = "abcdefghijkmnopqrstuvwwxyzABCDEFGHIJKLOMNOPQRSTUVWXYZ1234567890"
        return "".join([random.choice(t) for i in range(40)])
    code = _generate_code()
    while referral_class.objects.filter(code=code).exists():
        code = _generate_code()
    return code


def filter_responses(user=None, referral=None):
    from anafero.models import ReferralResponse
    responses = ReferralResponse.objects.all()
    if user:
        responses = responses.filter(referral__user=user)
    if referral:
        responses = responses.filter(referral=referral)
    return responses.order_by("-created_at")

########NEW FILE########
__FILENAME__ = conf
from django.conf import settings  # noqa

from appconf import AppConf

from anafero.utils import load_path_attr


class AnaferoAppConf(AppConf):

    IP_ADDRESS_META_FIELD = "HTTP_X_FORWARDED_FOR"
    SECURE_URLS = False
    ACTION_DISPLAY = {"RESPONDED": "Clicked on referral link"}
    CODE_GENERATOR_CALLBACK = "anafero.callbacks.generate_code"
    RESPONSES_FILTER_CALLBACK = "anafero.callbacks.filter_responses"

    def configure_code_generator_callback(self, value):
        return load_path_attr(value)

    def configure_responses_filter_callback(self, value):
        return load_path_attr(value)

########NEW FILE########
__FILENAME__ = middleware
from django.core.exceptions import ImproperlyConfigured

from anafero.models import Referral


class SessionJumpingMiddleware(object):

    def process_request(self, request):
        if not hasattr(request, "user"):
            raise ImproperlyConfigured(
                "django.contrib.auth.middleware.AuthenticationMiddleware middleware must come "
                "before anafero.middleware.SessionJumpingMiddleware"
            )
        cookie = request.COOKIES.get("anafero-referral")
        if request.user.is_authenticated() and cookie:
            code, session_key = cookie.split(":")

            try:
                referral = Referral.objects.get(code=code)
                referral.link_responses_to_user(request.user, session_key)
            except Referral.DoesNotExist:
                pass

            request.user._can_delete_anafero_cookie = True

    def process_response(self, request, response):
        if hasattr(request, "user") and getattr(request.user, "_can_delete_anafero_cookie", False):
            response.delete_cookie("anafero-referral")
        return response

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from django.db import models
from django.core.urlresolvers import reverse
from django.utils import timezone

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.sites.models import Site

from anafero.conf import settings
from anafero.signals import user_linked_to_response


AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", "auth.User")


class Referral(models.Model):

    user = models.ForeignKey(
        AUTH_USER_MODEL,
        related_name="referral_codes",
        null=True
    )
    label = models.CharField(max_length=100, blank=True)
    code = models.CharField(max_length=40, unique=True)
    expired_at = models.DateTimeField(null=True)
    redirect_to = models.CharField(max_length=512)
    target_content_type = models.ForeignKey(ContentType, null=True, blank=True)
    target_object_id = models.PositiveIntegerField(null=True, blank=True)
    target = generic.GenericForeignKey(
        ct_field="target_content_type",
        fk_field="target_object_id"
    )

    created_at = models.DateTimeField(default=timezone.now)

    def __unicode__(self):
        if self.user:
            return "%s (%s)" % (self.user, self.code)
        else:
            return self.code

    @classmethod
    def for_request(cls, request):
        cookie = request.COOKIES.get("anafero-referral")
        if cookie:
            code, session_key = cookie.split(":")
            try:
                return Referral.objects.get(code=code)
            except Referral.DoesNotExist:
                pass

    @property
    def url(self):
        path = reverse("anafero_process_referral", kwargs={"code": self.code})
        domain = Site.objects.get_current().domain
        protocol = "https" if settings.ANAFERO_SECURE_URLS else "http"
        return "%s://%s%s" % (protocol, domain, path)

    @property
    def response_count(self):
        return self.responses.filter(action="RESPONDED").count()

    @classmethod
    def create(cls, redirect_to, user=None, label="", target=None):
        code = settings.ANAFERO_CODE_GENERATOR_CALLBACK(cls)

        if target:
            obj, _ = cls.objects.get_or_create(
                user=user,
                code=code,
                redirect_to=redirect_to,
                label=label,
                target_content_type=ContentType.objects.get_for_model(target),
                target_object_id=target.pk
            )
        else:
            obj, _ = cls.objects.get_or_create(
                user=user,
                code=code,
                label=label,
                redirect_to=redirect_to,
            )

        return obj

    @classmethod
    def record_response(cls, request, action_string, target=None):
        referral = cls.referral_for_request(request)
        if referral:
            return referral.respond(request, action_string, target=target)

    @classmethod
    def referral_for_request(cls, request):
        if request.user.is_authenticated():
            qs = ReferralResponse.objects.filter(user=request.user)
        else:
            qs = ReferralResponse.objects.filter(session_key=request.session.session_key)

        try:
            return qs.order_by("-created_at")[0].referral
        except IndexError:
            pass

    def link_responses_to_user(self, user, session_key):
        for response in self.responses.filter(session_key=session_key, user__isnull=True):
            response.user = user
            response.save()
            user_linked_to_response.send(sender=self, response=response)

    def respond(self, request, action_string, user=None, target=None):
        if user is None:
            if request.user.is_authenticated():
                user = request.user
            else:
                user = None

        ip_address = request.META.get(
            settings.ANAFERO_IP_ADDRESS_META_FIELD,
            ""
        )

        kwargs = dict(
            referral=self,
            session_key=request.session.session_key,
            ip_address=ip_address,
            action=action_string,
            user=user
        )
        if target:
            kwargs.update({"target": target})

        return ReferralResponse.objects.create(**kwargs)

    def filtered_responses(self):
        return settings.ANAFERO_RESPONSES_FILTER_CALLBACK(
            referral=self
        )


class ReferralResponse(models.Model):

    referral = models.ForeignKey(Referral, related_name="responses")
    session_key = models.CharField(max_length=40)
    user = models.ForeignKey(AUTH_USER_MODEL, null=True)
    ip_address = models.CharField(max_length=45)
    action = models.CharField(max_length=128)

    target_content_type = models.ForeignKey(ContentType, null=True)
    target_object_id = models.PositiveIntegerField(null=True)
    target = generic.GenericForeignKey(
        ct_field="target_content_type",
        fk_field="target_object_id"
    )

    created_at = models.DateTimeField(default=timezone.now)

########NEW FILE########
__FILENAME__ = signals
import django.dispatch


user_linked_to_response = django.dispatch.Signal(providing_args=["response"])

########NEW FILE########
__FILENAME__ = anafero_tags
from django import template

from django.contrib.contenttypes.models import ContentType

from anafero.conf import settings


register = template.Library()


@register.inclusion_tag("anafero/_create_referral_form.html", takes_context=True)
def create_referral(context, url, obj=None):
    if obj:
        context.update(
            {"url": url, "obj": obj, "obj_ct": ContentType.objects.get_for_model(obj)}
        )
    else:
        context.update(
            {"url": url, "obj": "", "obj_ct": ""}
        )
    return context


class ReferralResponsesNode(template.Node):

    def __init__(self, user_var, target_var):
        self.user_var = user_var
        self.target_var = target_var

    def render(self, context):
        user = self.user_var.resolve(context)
        qs = settings.ANAFERO_RESPONSES_FILTER_CALLBACK(
            user=user
        )
        context[self.target_var] = qs
        return ""


@register.tag
def referral_responses(parser, token):
    bits = token.split_contents()
    tag_name = bits[0]
    bits = bits[1:]
    if len(bits) < 2 or bits[-2] != "as":
        raise template.TemplateSyntaxError(
            "'%s' tag takes at least 2 arguments and the second to last "
            "argument must be 'as'" % tag_name
        )
    return ReferralResponsesNode(parser.compile_filter(bits[0]), bits[2])


@register.filter
def action_display(value):
    return settings.ANAFERO_ACTION_DISPLAY.get(value, value)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase


class Tests(TestCase):

    def setUp(self):
        pass

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, include
except ImportError:
    from django.conf.urls.defaults import patterns, include


urlpatterns = patterns(
    "",
    (r"^", include("anafero.urls")),
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import url, patterns

from anafero.views import create_referral, process_referral


urlpatterns = patterns(
    "",
    url(r"^$", create_referral, name="anafero_create_referral"),
    url(r"^(?P<code>\w+)/$", process_referral, name="anafero_process_referral")
)

########NEW FILE########
__FILENAME__ = utils
from django.core.exceptions import ImproperlyConfigured
from django.utils import importlib


def ensure_session_key(request):
    """
    Given a request return a session key that will be used. There may already
    be a session key associated, but if there is not, we force the session to
    create itself and persist between requests for the client behind the given
    request.
    """
    key = request.session.session_key
    if key is None:
        # @@@ Django forces us to handle session key collision amongst
        # multiple processes (not handled)
        request.session.save()
        # force session to persist for client
        request.session.modified = True
        key = request.session.session_key
    return key


def load_path_attr(path):
    i = path.rfind(".")
    module, attr = path[:i], path[i + 1:]
    try:
        mod = importlib.import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured("Error importing %s: '%s'" % (module, e))
    try:
        attr = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured("Module '%s' does not define a '%s'" % (module, attr))
    return attr

########NEW FILE########
__FILENAME__ = views
import json

from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from anafero.models import Referral
from anafero.utils import ensure_session_key


@login_required
@require_POST
def create_referral(request):
    target = None
    ctx = {"url": request.POST.get("redirect_to")}

    if request.POST.get("obj_ct_pk") and request.POST.get("obj_pk"):
        ct = ContentType.objects.get(pk=request.POST.get("obj_ct_pk"))
        target = ct.get_object_for_this_type(pk=request.POST.get("obj_pk"))
        ctx["obj"] = target
        ctx["obj_ct"] = ct

    referral = Referral.create(
        user=request.user,
        redirect_to=request.POST.get("redirect_to"),
        label=request.POST.get("label", ""),
        target=target
    )

    return HttpResponse(
        json.dumps({
            "url": referral.url,
            "code": referral.code,
            "html": render_to_string(
                "anafero/_create_referral_form.html",
                ctx,
                context_instance=RequestContext(request)
            )
        }),
        mimetype="application/json"
    )


def process_referral(request, code):
    referral = get_object_or_404(Referral, code=code)
    session_key = ensure_session_key(request)
    referral.respond(request, "RESPONDED")
    response = redirect(referral.redirect_to)
    if request.user.is_anonymous():
        response.set_cookie(
            "anafero-referral",
            "%s:%s" % (code, session_key)
        )
    else:
        response.delete_cookie("anafero-referral")

    return response

########NEW FILE########
__FILENAME__ = conf
import sys, os

extensions = []
templates_path = []
source_suffix = ".rst"
master_doc = "index"
project = u"anafero"
package = "anafero"
copyright = u"2013, Eldarion"
exclude_patterns = ["_build"]
pygments_style = "sphinx"
html_theme = "default"
html_static_path = []
htmlhelp_basename = "anaferodoc"
latex_documents = [
  ("index", "anafero.tex", u"anafero Documentation",
   u"Eldarion", "manual"),
]
man_pages = [
    ("index", "anafero", u"anafero Documentation",
     [u"Eldarion"], 1)
]

sys.path.insert(0, os.pardir)
m = __import__(package)

version = m.__version__
release = version

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import sys

import django

from django.conf import settings


DEFAULT_SETTINGS = dict(
    INSTALLED_APPS=[
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sites",
        "anafero",
        "anafero.tests"
    ],
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
    SITE_ID=1,
    ROOT_URLCONF="anafero.tests.urls",
    SECRET_KEY="notasecret",
)


def runtests(*test_args):
    if not settings.configured:
        settings.configure(**DEFAULT_SETTINGS)

    # Compatibility with Django 1.7's stricter initialization
    if hasattr(django, "setup"):
        django.setup()

    if not test_args:
        test_args = ["tests"]

    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, parent)

    from django.test.simple import DjangoTestSuiteRunner
    failures = DjangoTestSuiteRunner(
        verbosity=1, interactive=True, failfast=False).run_tests(test_args)
    sys.exit(failures)


if __name__ == "__main__":
    runtests(*sys.argv[1:])

########NEW FILE########
