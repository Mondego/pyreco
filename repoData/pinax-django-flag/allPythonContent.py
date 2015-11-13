__FILENAME__ = admin
from django.contrib import admin

from flag.models import FlaggedContent, FlagInstance


class InlineFlagInstance(admin.TabularInline):
    model = FlagInstance
    extra = 0


class FlaggedContentAdmin(admin.ModelAdmin):
    inlines = [InlineFlagInstance]


admin.site.register(FlaggedContent, FlaggedContentAdmin)

########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from django.conf import settings
from django.db import models

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils.translation import ugettext_lazy as _

from flag import signals


STATUS = getattr(settings, "FLAG_STATUSES", [
    ("1", _("flagged")),
    ("2", _("flag rejected by moderator")),
    ("3", _("creator notified")),
    ("4", _("content removed by creator")),
    ("5", _("content removed by moderator")),
])


class FlaggedContent(models.Model):
    
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey("content_type", "object_id")
    
    creator = models.ForeignKey(User, related_name="flagged_content") # user who created flagged content -- this is kept in model so it outlives content
    status = models.CharField(max_length=1, choices=STATUS, default="1")
    moderator = models.ForeignKey(User, null=True, related_name="moderated_content") # moderator responsible for last status change
    count = models.PositiveIntegerField(default=1)
    
    class Meta:
        unique_together = [("content_type", "object_id")]


class FlagInstance(models.Model):
    
    flagged_content = models.ForeignKey(FlaggedContent)
    user = models.ForeignKey(User) # user flagging the content
    when_added = models.DateTimeField(default=datetime.now)
    when_recalled = models.DateTimeField(null=True) # if recalled at all
    comment = models.TextField() # comment by the flagger


def add_flag(flagger, content_type, object_id, content_creator, comment, status=None):
    
    # check if it's already been flagged
    defaults = dict(creator=content_creator)
    if status is not None:
        defaults["status"] = status
    flagged_content, created = FlaggedContent.objects.get_or_create(
        content_type = content_type,
        object_id = object_id,
        defaults = defaults
    )
    if not created:
        flagged_content.count = models.F("count") + 1
        flagged_content.save()
        # pull flagged_content from database to get count attribute filled
        # properly (not the best way, but works)
        flagged_content = FlaggedContent.objects.get(pk=flagged_content.pk)
    
    flag_instance = FlagInstance(
        flagged_content = flagged_content,
        user = flagger,
        comment = comment
    )
    flag_instance.save()
    
    signals.content_flagged.send(
        sender = FlaggedContent,
        flagged_content = flagged_content,
        flagged_instance = flag_instance,
    )
    
    return flag_instance

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal


content_flagged = Signal(providing_args=["flagged_content", "flagged_instance"])
########NEW FILE########
__FILENAME__ = flag_tags
from django import template

from django.contrib.contenttypes.models import ContentType


register = template.Library()


@register.inclusion_tag("flag/flag_form.html", takes_context=True)
def flag(context, content_object, creator_field):
    content_type = ContentType.objects.get(
        app_label = content_object._meta.app_label,
        model = content_object._meta.module_name
    )
    request = context["request"]
    return {
        "content_type": content_type.id,
        "object_id": content_object.id,
        "creator_field": creator_field,
        "request": request,
        "user": request.user,
    }

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.views.generic import TemplateView


urlpatterns = patterns("",
    url(r"^$", "flag.views.flag", name="flag"),
    url(r'^thank_you', TemplateView.as_view(template_name="flag/thank_you.html"), name='flag-reported'),
)
########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _
from django.contrib import messages

from flag.models import add_flag


@login_required
def flag(request):
    
    content_type = request.POST.get("content_type")
    object_id = request.POST.get("object_id")
    creator_field = request.POST.get("creator_field")
    comment = request.POST.get("comment")
    next = request.POST.get("next")
    
    content_type = get_object_or_404(ContentType, id = int(content_type))
    object_id = int(object_id)
    
    content_object = content_type.get_object_for_this_type(id=object_id)
    
    if creator_field and hasattr(content_object, creator_field):
        creator = getattr(content_object, creator_field)
    else:
        creator = None
    
    add_flag(request.user, content_type, object_id, creator, comment)
    messages.success(request, _("You have added a flag. A moderator will review your submission shortly."), fail_silently=True)
    
    if next:
        return HttpResponseRedirect(next)
    else:
        return HttpResponseRedirect(reverse('flag-reported'))

########NEW FILE########
