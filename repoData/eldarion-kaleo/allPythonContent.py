__FILENAME__ = conf
import os
import sys

extensions = []
templates_path = []
source_suffix = ".rst"
master_doc = "index"
project = u"kaleo"
copyright_holder = "Eldarion"
copyright = u"2013, %s" % copyright_holder
exclude_patterns = ["_build"]
pygments_style = "sphinx"
html_theme = "default"
htmlhelp_basename = "%sdoc" % project
latex_documents = [
  ("index", "%s.tex" % project, u"%s Documentation" % project,
   copyright_holder, "manual"),
]
man_pages = [
    ("index", project, u"%s Documentation" % project,
     [copyright_holder], 1)
]

sys.path.insert(0, os.pardir)
m = __import__("kaleo")

version = m.__version__
release = version

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from kaleo.models import JoinInvitation, InvitationStat


class InvitationStatAdmin(admin.ModelAdmin):
    raw_id_fields = ["user"]
    readonly_fields = ["invites_sent", "invites_accepted"]
    list_display = [
        "user",
        "invites_sent",
        "invites_accepted",
        "invites_allocated",
        "invites_remaining",
        "can_send"
    ]
    list_filter = ["invites_sent", "invites_accepted"]


admin.site.register(
    JoinInvitation,
    list_display=["from_user", "to_user", "sent", "status", "to_user_email"],
    list_filter=["sent", "status"],
    search_fields=["from_user__username"]
)
admin.site.register(InvitationStat, InvitationStatAdmin)

########NEW FILE########
__FILENAME__ = compat
import django

from django.db.models.signals import class_prepared
from django.utils import six

try:
    from django.contrib.auth import get_user_model as auth_get_user_model
except ImportError:
    auth_get_user_model = None
    from django.contrib.auth.models import User

from .conf import settings


AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", "auth.User")


def get_user_model(*args, **kwargs):
    if auth_get_user_model is not None:
        return auth_get_user_model(*args, **kwargs)
    else:
        return User


def get_user_lookup_kwargs(kwargs):
    result = {}
    username_field = getattr(get_user_model(), "USERNAME_FIELD", "username")
    for key, value in kwargs.items():
        result[key.format(username=username_field)] = value
    return result


def receiver(signal, **kwargs):  # noqa
    if django.VERSION < (1, 7, 0):
        unresolved_references = {}

        def _resolve_references(sender, **kwargs):
            opts = sender._meta
            reference = (opts.app_label, opts.object_name)
            try:
                receivers = unresolved_references.pop(reference)
            except KeyError:
                pass
            else:
                for signal, func, kwargs in receivers:
                    kwargs["sender"] = sender
                    signal.connect(func, **kwargs)
        class_prepared.connect(_resolve_references, weak=False)

    def _decorator(func):
        if django.VERSION < (1, 7, 0):
            from django.db.models.loading import cache as app_cache
            sender = kwargs.get("sender")
            if isinstance(sender, six.string_types):
                try:
                    app_label, model_name = sender.split(".")
                except ValueError:
                    raise ValueError(
                        "Specified sender must either be a model or a "
                        "model name of the 'app_label.ModelName' form."
                    )
                sender = app_cache.app_models.get(app_label, {}).get(model_name.lower())
                if sender is None:
                    ref = (app_label, model_name)
                    refs = unresolved_references.setdefault(ref, [])
                    refs.append((signal, func, kwargs))
                    return func
                else:
                    kwargs["sender"] = sender
        signal.connect(func, **kwargs)
        return func
    return _decorator

########NEW FILE########
__FILENAME__ = conf
from __future__ import unicode_literals

from django.conf import settings  # noqa

from appconf import AppConf


class KaleoAppConf(AppConf):

    DEFAULT_EXPIRATION = 168
    DEFAULT_INVITE_ALLOCATION = 0

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext as _

from account.models import EmailAddress

from kaleo.models import JoinInvitation


class InviteForm(forms.Form):
    email_address = forms.EmailField()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super(InviteForm, self).__init__(*args, **kwargs)

    def clean_email_address(self):
        email = self.cleaned_data["email_address"]
        if EmailAddress.objects.filter(email=email, verified=True).exists():
            raise forms.ValidationError(_("Email address already in use"))
        elif JoinInvitation.objects.filter(from_user=self.user, signup_code__email=email).exists():
            raise forms.ValidationError(_("You have already invited this user"))
        return email

########NEW FILE########
__FILENAME__ = add_invites
import sys

from django.core.management.base import BaseCommand

from kaleo.models import InvitationStat


class Command(BaseCommand):
    help = "Adds invites to all users with 0 invites remaining."

    def handle(self, *args, **kwargs):
        if len(args) == 0:
            sys.exit("You must supply the number of invites as an argument.")

        try:
            num_of_invites = int(args[0])
        except ValueError:
            sys.exit("The argument for number of invites must be an integer.")

        InvitationStat.add_invites(num_of_invites)

########NEW FILE########
__FILENAME__ = infinite_invites
from django.core.management.base import BaseCommand

from kaleo.compat import get_user_model
from kaleo.models import InvitationStat


class Command(BaseCommand):
    help = "Sets invites_allocated to -1 to represent infinite invites."

    def handle(self, *args, **kwargs):
        for user in get_user_model().objects.all():
            stat, _ = InvitationStat.objects.get_or_create(user=user)
            stat.invites_allocated = -1
            stat.save()

########NEW FILE########
__FILENAME__ = topoff_invites
import sys

from django.core.management.base import BaseCommand

from kaleo.models import InvitationStat


class Command(BaseCommand):
    help = "Makes sure all users have a certain number of invites."

    def handle(self, *args, **kwargs):
        if len(args) == 0:
            sys.exit("You must supply the number of invites as an argument.")

        try:
            num_of_invites = int(args[0])
        except ValueError:
            sys.exit("The argument for number of invites must be an integer.")

        InvitationStat.topoff(num_of_invites)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils import timezone

from account.models import SignupCode

from kaleo.compat import get_user_model, AUTH_USER_MODEL
from kaleo.conf import settings
from kaleo.signals import invite_sent, joined_independently, invite_accepted


class NotEnoughInvitationsError(Exception):
    pass


class JoinInvitation(models.Model):

    STATUS_SENT = 1
    STATUS_ACCEPTED = 2
    STATUS_JOINED_INDEPENDENTLY = 3

    INVITE_STATUS_CHOICES = [
        (STATUS_SENT, "Sent"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_JOINED_INDEPENDENTLY, "Joined Independently")
    ]

    from_user = models.ForeignKey(AUTH_USER_MODEL, related_name="invites_sent")
    to_user = models.ForeignKey(AUTH_USER_MODEL, null=True, related_name="invites_received")
    message = models.TextField(null=True)
    sent = models.DateTimeField(default=timezone.now)
    status = models.IntegerField(choices=INVITE_STATUS_CHOICES)
    signup_code = models.OneToOneField(SignupCode)

    def to_user_email(self):
        return self.signup_code.email

    def accept(self, user):
        self.to_user = user
        self.status = JoinInvitation.STATUS_ACCEPTED
        self.save()
        self.from_user.invitationstat.increment_accepted()
        invite_accepted.send(sender=JoinInvitation, invitation=self)

    @classmethod
    def process_independent_joins(cls, user, email):
        invites = cls.objects.filter(
            to_user__isnull=True,
            signup_code__email=email
        )
        for invite in invites:
            invite.to_user = user
            invite.status = cls.STATUS_JOINED_INDEPENDENTLY
            invite.save()
            joined_independently.send(sender=cls, invitation=invite)

    @classmethod
    def invite(cls, from_user, to_email, message=None, send=True):
        if not from_user.invitationstat.can_send():
            raise NotEnoughInvitationsError()

        signup_code = SignupCode.create(
            email=to_email,
            inviter=from_user,
            expiry=settings.KALEO_DEFAULT_EXPIRATION,
            check_exists=False  # before we are called caller must check for existence
        )
        signup_code.save()
        join = cls.objects.create(
            from_user=from_user,
            message=message,
            status=JoinInvitation.STATUS_SENT,
            signup_code=signup_code
        )
        def send_invite(*args, **kwargs):
            signup_code.send(*args, **kwargs)
            InvitationStat.objects.filter(user=from_user).update(invites_sent=models.F("invites_sent") + 1)
            invite_sent.send(sender=cls, invitation=join)
        if send:
            send_invite()
        else:
            join.send_invite = send_invite
        return join


class InvitationStat(models.Model):

    user = models.OneToOneField(AUTH_USER_MODEL)
    invites_sent = models.IntegerField(default=0)
    invites_allocated = models.IntegerField(default=settings.KALEO_DEFAULT_INVITE_ALLOCATION)
    invites_accepted = models.IntegerField(default=0)

    def increment_accepted(self):
        self.invites_accepted += 1
        self.save()

    @classmethod
    def add_invites_to_user(cls, user, amount):
        stat, _ = InvitationStat.objects.get_or_create(user=user)
        if stat.invites_allocated != -1:
            stat.invites_allocated += amount
            stat.save()

    @classmethod
    def add_invites(cls, amount):
        for user in get_user_model().objects.all():
            cls.add_invites_to_user(user, amount)

    @classmethod
    def topoff_user(cls, user, amount):
        "Makes sure user has a certain number of invites"
        stat, _ = cls.objects.get_or_create(user=user)
        remaining = stat.invites_remaining()
        if remaining != -1 and remaining < amount:
            stat.invites_allocated += (amount - remaining)
            stat.save()

    @classmethod
    def topoff(cls, amount):
        "Makes sure all users have a certain number of invites"
        for user in get_user_model().objects.all():
            cls.topoff_user(user, amount)

    def invites_remaining(self):
        if self.invites_allocated == -1:
            return -1
        return self.invites_allocated - self.invites_sent

    def can_send(self):
        if self.invites_allocated == -1:
            return True
        return self.invites_allocated > self.invites_sent
    can_send.boolean = True

########NEW FILE########
__FILENAME__ = receivers
from django.db.models.signals import post_save

from account.models import SignupCodeResult, EmailConfirmation
from account.signals import signup_code_used, email_confirmed, user_signed_up

from kaleo.compat import AUTH_USER_MODEL, receiver
from kaleo.models import JoinInvitation, InvitationStat


@receiver(signup_code_used, sender=SignupCodeResult)
def handle_signup_code_used(sender, **kwargs):
    result = kwargs.get("signup_code_result")
    try:
        invite = result.signup_code.joininvitation
        invite.accept(result.user)
    except JoinInvitation.DoesNotExist:
        pass


@receiver(email_confirmed, sender=EmailConfirmation)
def handle_email_confirmed(sender, **kwargs):
    email_address = kwargs.get("email_address")
    JoinInvitation.process_independent_joins(
        user=email_address.user,
        email=email_address.email
    )


@receiver(user_signed_up)
def handle_user_signup(sender, user, form, **kwargs):
    email_qs = user.emailaddress_set.filter(email=user.email, verified=True)
    if user.is_active and email_qs.exists():
        JoinInvitation.process_independent_joins(
            user=user,
            email=user.email
        )


@receiver(post_save, sender=AUTH_USER_MODEL)
def create_stat(sender, instance=None, **kwargs):
    if instance is None:
        return
    InvitationStat.objects.get_or_create(user=instance)

########NEW FILE########
__FILENAME__ = signals
import django.dispatch


invite_sent = django.dispatch.Signal(providing_args=["invitation"])
invite_accepted = django.dispatch.Signal(providing_args=["invitation"])
joined_independently = django.dispatch.Signal(providing_args=["invitation"])

########NEW FILE########
__FILENAME__ = stats
from kaleo.models import JoinInvitation


def stats():
    return {
        "join_invitations_sent": JoinInvitation.objects.count(),
        "join_invitations_accepted": JoinInvitation.objects.filter(
            status=JoinInvitation.STATUS_ACCEPTED
        ).count()
    }

########NEW FILE########
__FILENAME__ = kaleo_tags
from django import template

from kaleo.forms import InviteForm
from kaleo.models import InvitationStat


register = template.Library()


@register.inclusion_tag("kaleo/_invites_remaining.html")
def invites_remaining(user):
    try:
        remaining = user.invitationstat.invites_remaining()
    except InvitationStat.DoesNotExist:
        remaining = 0
    return {"invites_remaining": remaining}


@register.inclusion_tag("kaleo/_invite_form.html")
def invite_form(user):
    return {"form": InviteForm(user=user), "user": user}


@register.inclusion_tag("kaleo/_invited.html")
def invites_sent(user):
    return {"invited_list": user.invites_sent.all()}


@register.filter
def status_class(invite):
    if invite.status == invite.STATUS_SENT:
        return "sent"
    elif invite.status == invite.STATUS_ACCEPTED:
        return "accepted"
    elif invite.status == invite.STATUS_JOINED_INDEPENDENTLY:
        return "joined"
    return ""

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase

from django.contrib.auth.models import User

import kaleo.receivers  # noqa

from account.models import SignupCode
from kaleo.models import JoinInvitation


class TestsJoinInvitation(TestCase):

    def setUp(self):
        self.to_user = User.objects.create(username='foo1')
        self.from_user = User.objects.create(username='foo2')
        self.signup_code = SignupCode.create(email="me@you.com")
        self.signup_code.save()
        self.status = JoinInvitation.STATUS_ACCEPTED
        self.invitation = JoinInvitation.objects.create(
            from_user=self.from_user,
            status=self.status,
            signup_code=self.signup_code,
        )

    def test_to_user_email(self):
        self.assertEqual(self.signup_code.email, "me@you.com")

    def test_accept(self):
        self.invitation.accept(self.to_user)
        self.assertEqual(self.from_user.invitationstat.invites_accepted, 1)

    def test_process_independent_joins(self):
        JoinInvitation.process_independent_joins(self.to_user, "me@you.com")
        invite = JoinInvitation.objects.get(pk=self.invitation.pk)
        self.assertEqual(invite.status, JoinInvitation.STATUS_JOINED_INDEPENDENTLY)

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, include
except ImportError:
    from django.conf.urls.defaults import patterns, include


urlpatterns = patterns(
    "",
    (r"^", include("kaleo.urls")),
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import url, patterns

from kaleo.views import (
    addto_all,
    addto_user,
    invite,
    topoff_all,
    invite_stat,
    topoff_user
)


urlpatterns = patterns(
    "",
    url(r"^invite/$", invite, name="kaleo_invite"),
    url(r"^invite-stat/(?P<pk>\d+)/$", invite_stat, name="kaleo_invite_stat"),
    url(r"^topoff/$", topoff_all, name="kaleo_topoff_all"),
    url(r"^topoff/(?P<pk>\d+)/$", topoff_user, name="kaleo_topoff_user"),
    url(r"^addto/$", addto_all, name="kaleo_addto_all"),
    url(r"^addto/(?P<pk>\d+)/$", addto_user, name="kaleo_addto_user"),
)

########NEW FILE########
__FILENAME__ = views
import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required

from kaleo.compat import get_user_model
from kaleo.forms import InviteForm
from kaleo.models import JoinInvitation, InvitationStat


@login_required
@require_POST
def invite(request):
    form = InviteForm(request.POST, user=request.user)
    if form.is_valid():
        email = form.cleaned_data["email_address"]
        JoinInvitation.invite(request.user, email)
        form = InviteForm(user=request.user)
    data = {
        "html": render_to_string(
            "kaleo/_invite_form.html", {
                "form": form,
                "user": request.user
            }, context_instance=RequestContext(request)
        ),
        "fragments": {
            ".kaleo-invites-remaining": render_to_string(
                "kaleo/_invites_remaining.html", {
                    "invites_remaining": request.user.invitationstat.invites_remaining()
                }, context_instance=RequestContext(request)
            ),
            ".kaleo-invites-sent": render_to_string(
                "kaleo/_invited.html", {
                    "invited_list": request.user.invites_sent.all()
                }, context_instance=RequestContext(request)
            )
        }
    }
    return HttpResponse(json.dumps(data), content_type="application/json")


@login_required
@permission_required("kaleo.manage_invites", raise_exception=True)
def invite_stat(request, pk):
    user = get_object_or_404(get_user_model(), pk=pk)
    return HttpResponse(json.dumps({
        "html": render_to_string(
            "kaleo/_invite_stat.html", {
                "stat": user.invitationstat
            }, context_instance=RequestContext(request)
        )
    }), content_type="application/json")


@login_required
@permission_required("kaleo.manage_invites", raise_exception=True)
@require_POST
def topoff_all(request):
    amount = int(request.POST.get("amount"))
    InvitationStat.topoff(amount)
    return HttpResponse(json.dumps({
        "inner-fragments": {".invite-total": amount}
    }), content_type="application/json")


@login_required
@permission_required("kaleo.manage_invites", raise_exception=True)
@require_POST
def topoff_user(request, pk):
    user = get_object_or_404(get_user_model(), pk=pk)
    amount = int(request.POST.get("amount"))
    InvitationStat.topoff_user(user=user, amount=amount)
    return HttpResponse(json.dumps({
        "html": amount
    }), content_type="application/json")


@login_required
@permission_required("kaleo.manage_invites", raise_exception=True)
@require_POST
def addto_all(request):
    amount = int(request.POST.get("amount"))
    InvitationStat.add_invites(amount)
    return HttpResponse(json.dumps({
        "inner-fragments": {".amount-added": amount}
    }), content_type="application/json")


@login_required
@permission_required("kaleo.manage_invites", raise_exception=True)
@require_POST
def addto_user(request, pk):
    user = get_object_or_404(get_user_model(), pk=pk)
    amount = int(request.POST.get("amount"))
    InvitationStat.add_invites_to_user(user=user, amount=amount)
    return HttpResponse(json.dumps({
        "html": amount
    }), content_type="application/json")

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
        "account",
        "kaleo",
        "kaleo.tests"
    ],
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
    SITE_ID=1,
    ROOT_URLCONF="kaleo.tests.urls",
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
