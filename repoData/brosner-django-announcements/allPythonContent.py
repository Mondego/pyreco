__FILENAME__ = admin
from django.contrib import admin

from announcements.models import Announcement
from announcements.forms import AnnouncementAdminForm


class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "creator", "creation_date", "members_only")
    list_filter = ("members_only",)
    form = AnnouncementAdminForm
    fieldsets = [
        (None, {
            "fields": ["title", "content", "site_wide", "members_only"],
        }),
        
        ("Manage announcement", {
            "fields": ["send_now"],
        }),
    ]

    def save_model(self, request, obj, form, change):
        if not change:
            # When creating a new announcement, set the creator field.
            obj.creator = request.user
        obj.save()


admin.site.register(Announcement, AnnouncementAdmin)

########NEW FILE########
__FILENAME__ = context_processors
from announcements.models import current_announcements_for_request


def site_wide_announcements(request):
    """
    Adds the site-wide announcements to the global context of templates.
    """
    ctx = {"site_wide_announcements": current_announcements_for_request(request, site_wide=True)}
    return ctx

########NEW FILE########
__FILENAME__ = feeds
from atomformat import Feed

from announcements.models import Announcement


class AnnouncementsBase(Feed):
    
    # subclass and set:
    #   feed_id = "..."
    #   feed_title = "..."
    #   feed_links = [
    #     {"rel": "self", "href": "..."},
    #     {"rel": "alternate", "href": "..."},
    #   ]
    #   def item_id
    #   def item_links
    
    def items(self):
        return Announcement.objects.order_by("-creation_date")[:10]
    
    def item_title(self, item):
        return item.title
    
    def item_content(self, item):
        return item.content
    
    def item_authors(self, item):
        return [{"name": str(item.creator)}]
    
    def item_updated(self, item):
        return item.creation_date



########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

try:
    from notification import models as notification
except ImportError:
    notification = None

from announcements.models import Announcement


class AnnouncementAdminForm(forms.ModelForm):
    """
    A custom form for the admin of the Announcement model. Has an extra field
    called send_now that when checked will send out the announcement allowing
    the user to decide when that happens.
    """

    send_now = forms.BooleanField(required=False,
        help_text=_("Tick this box to send out this announcement now."))
    
    class Meta:
        model = Announcement
        exclude = ("creator", "creation_date")
    
    def save(self, commit=True):
        """
        Checks the send_now field in the form and when True sends out the
        announcement through notification if present.
        """

        announcement = super(AnnouncementAdminForm, self).save(commit)
        if self.cleaned_data["send_now"]:
            if notification:
                users = User.objects.all()
                notification.send(users, "announcement", {
                    "announcement": announcement,
                }, on_site=False, queue=True)
        return announcement

########NEW FILE########
__FILENAME__ = management
from django.db.models import get_models, signals


try:
    from notification import models as notification
    
    def create_notice_types(app, created_models, verbosity, **kwargs):
        """
        Create the announcement notice type for sending notifications when
        announcements occur.
        """
        notification.create_notice_type("announcement", "Announcement", "you have received an announcement")
    
    signals.post_syncdb.connect(create_notice_types, sender=notification)
except ImportError:
    print "Skipping creation of NoticeTypes as notification app not found"

########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

try:
    set
except NameError:
    from sets import Set as set   # Python 2.3 fallback


class AnnouncementManager(models.Manager):
    """
    A basic manager for dealing with announcements.
    """
    def current(self, exclude=[], site_wide=False, for_members=False):
        """
        Fetches and returns a queryset with the current announcements. This
        method takes the following parameters:
        
        ``exclude``
            A list of IDs that should be excluded from the queryset.
        
        ``site_wide``
            A boolean flag to filter to just site wide announcements.
        
        ``for_members``
            A boolean flag to allow member only announcements to be returned
            in addition to any others.
        """
        queryset = self.all()
        if site_wide:
            queryset = queryset.filter(site_wide=True)
        if exclude:
            queryset = queryset.exclude(pk__in=exclude)
        if not for_members:
            queryset = queryset.filter(members_only=False)
        queryset = queryset.order_by("-creation_date")
        return queryset


class Announcement(models.Model):
    """
    A single announcement.
    """
    title = models.CharField(_("title"), max_length=50)
    content = models.TextField(_("content"))
    creator = models.ForeignKey(User, verbose_name=_("creator"))
    creation_date = models.DateTimeField(_("creation_date"), default=datetime.now)
    site_wide = models.BooleanField(_("site wide"), default=False)
    members_only = models.BooleanField(_("members only"), default=False)
    
    objects = AnnouncementManager()
    
    def get_absolute_url(self):
        return ("announcement_detail", [str(self.pk)])
    get_absolute_url = models.permalink(get_absolute_url)
    
    def __unicode__(self):
        return self.title
    
    class Meta:
        verbose_name = _("announcement")
        verbose_name_plural = _("announcements")


def current_announcements_for_request(request, **kwargs):
    """
    A helper function to get the current announcements based on some data from
    the HttpRequest.
    
    If request.user is authenticated then allow the member only announcements
    to be returned.
    
    Exclude announcements that have already been viewed by the user based on
    the ``excluded_announcements`` session variable.
    """
    defaults = {}
    if request.user.is_authenticated():
        defaults["for_members"] = True
    defaults["exclude"] = request.session.get("excluded_announcements", set())
    defaults.update(kwargs)
    return Announcement.objects.current(**defaults)

########NEW FILE########
__FILENAME__ = announcement_tags
from django.template import Library, Node

from announcements.models import current_announcements_for_request


register = Library()


class FetchAnnouncementsNode(Node):
    def __init__(self, context_var, limit=None):
        self.context_var = context_var
        self.limit = limit
    
    def render(self, context):
        try:
            request = context["request"]
        except KeyError:
            raise Exception("{% fetch_announcements %} requires the HttpRequest in context.")
        kwargs = {}
        announcements = current_announcements_for_request(request, **kwargs)
        if self.limit:
            announcements = announcements[:self.limit]
        context[self.context_var] = announcements
        return ""

@register.tag
def fetch_announcements(parser, token):
    bits = token.split_contents()
    # @@@ very naive parsing
    if len(bits) == 5:
        limit = bits[2]
        context_var = bits[4]
    elif len(bits) == 3:
        limit = None
        context_var = bits[2]
    return FetchAnnouncementsNode(context_var, limit)

########NEW FILE########
__FILENAME__ = tests
__test__ = {"ANNOUNCEMENT_TESTS": r"""
>>> from django.contrib.auth.models import User
>>> from announcements.models import Announcement

# create ourselves a user to associate to the announcements
>>> superuser = User.objects.create_user("brosner", "brosner@gmail.com")

>>> a1 = Announcement.objects.create(title="Down for Maintenance", creator=superuser)
>>> a2 = Announcement.objects.create(title="Down for Maintenance Again", creator=superuser)
>>> a3 = Announcement.objects.create(title="Down for Maintenance Again And Again", creator=superuser, site_wide=True)
>>> a4 = Announcement.objects.create(title="Members Need to Fill Out New Profile Info", creator=superuser, members_only=True)
>>> a5 = Announcement.objects.create(title="Expected Down Time", creator=superuser, members_only=True, site_wide=True)

# get the announcements that are publically viewable. this is the same as
# calling as using site_wide=False, for_members=False
>>> Announcement.objects.current()
[<Announcement: Down for Maintenance Again And Again>, <Announcement: Down for Maintenance Again>, <Announcement: Down for Maintenance>]

# get just the publically viewable site wide announcements
>>> Announcement.objects.current(site_wide=True)
[<Announcement: Down for Maintenance Again And Again>]

# get the announcements that authenticated users can see.
>>> Announcement.objects.current(for_members=True)
[<Announcement: Expected Down Time>, <Announcement: Members Need to Fill Out New Profile Info>, <Announcement: Down for Maintenance Again And Again>, <Announcement: Down for Maintenance Again>, <Announcement: Down for Maintenance>]

# get just site wide announcements that authenticated users can see.
>>> Announcement.objects.current(site_wide=True, for_members=True)
[<Announcement: Expected Down Time>, <Announcement: Down for Maintenance Again And Again>]

# exclude a couple of announcements from the publically viewabled messages.
>>> Announcement.objects.current(exclude=[a1.pk, a5.pk])
[<Announcement: Down for Maintenance Again And Again>, <Announcement: Down for Maintenance Again>]

"""}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.views.generic import list_detail

from announcements.models import Announcement
from announcements.views import *


announcement_detail_info = {
    "queryset": Announcement.objects.all(),
}

urlpatterns = patterns("",
    url(r"^(?P<object_id>\d+)/$", list_detail.object_detail,
        announcement_detail_info, name="announcement_detail"),
    url(r"^(?P<object_id>\d+)/hide/$", announcement_hide,
        name="announcement_hide"),
    url(r"^$", announcement_list, name="announcement_home"),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponseRedirect
from django.views.generic import list_detail
from django.shortcuts import get_object_or_404

from announcements.models import Announcement, current_announcements_for_request

try:
    set
except NameError:
    from sets import Set as set   # Python 2.3 fallback


def announcement_list(request):
    """
    A basic view that wraps ``django.views.list_detail.object_list`` and
    uses ``current_announcements_for_request`` to get the current
    announcements.
    """
    queryset = current_announcements_for_request(request)
    return list_detail.object_list(request, **{
        "queryset": queryset,
        "allow_empty": True,
    })


def announcement_hide(request, object_id):
    """
    Mark this announcement hidden in the session for the user.
    """
    announcement = get_object_or_404(Announcement, pk=object_id)
    # TODO: perform some basic security checks here to ensure next is not bad
    redirect_to = request.GET.get("next")
    excluded_announcements = request.session.get("excluded_announcements", set())
    excluded_announcements.add(announcement.pk)
    request.session["excluded_announcements"] = excluded_announcements
    return HttpResponseRedirect(redirect_to)

########NEW FILE########
