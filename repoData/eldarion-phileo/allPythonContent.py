__FILENAME__ = conf
import sys, os

extensions = []
templates_path = []
source_suffix = '.rst'
master_doc = 'index'
project = u'phileo'
copyright = u'2013, Eldarion'
exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'default'
htmlhelp_basename = '%sdoc' % project
latex_documents = [
  ('index', '%s.tex' % project, u'%s Documentation' % project,
   u'Eldarion', 'manual'),
]
man_pages = [
    ('index', project, u'%s Documentation' % project,
     [u'Eldarion'], 1)
]

sys.path.insert(0, os.pardir)
m = __import__(project)

version = m.__version__
release = version

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from phileo.models import Like


admin.site.register(Like,
    raw_id_fields=["sender"],
    list_filter=["timestamp"],
    list_display=["sender", "receiver", "timestamp"],
    search_fields=["sender__username", "sender__email"]
)

########NEW FILE########
__FILENAME__ = auth_backends
from django.contrib.auth.backends import ModelBackend

from phileo.utils import _allowed


class CanLikeBackend(ModelBackend):
    supports_object_permissions = True
    supports_anonymous_user = True
    
    def is_allowed(self, obj):
        return _allowed(obj)
    
    def has_perm(self, user, perm, obj=None):
        if perm == "phileo.can_like":
            return self.is_allowed(obj)
        return super(CanLikeBackend, self).has_perm(user, perm)

########NEW FILE########
__FILENAME__ = models
from django.conf import settings
from django.db import models
from django.utils import timezone

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic


# Compatibility with custom user models, while keeping backwards-compatibility with <1.5
AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", "auth.User")


class Like(models.Model):

    sender = models.ForeignKey(AUTH_USER_MODEL, related_name="liking")

    receiver_content_type = models.ForeignKey(ContentType)
    receiver_object_id = models.PositiveIntegerField()
    receiver = generic.GenericForeignKey(
        ct_field="receiver_content_type",
        fk_field="receiver_object_id"
    )

    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = (
            ("sender", "receiver_content_type", "receiver_object_id"),
        )

    def __unicode__(self):
        return u"%s likes %s" % (self.sender, self.receiver)

########NEW FILE########
__FILENAME__ = settings
from collections import defaultdict

from django.conf import settings


DEFAULT_LIKE_CONFIG = getattr(settings, "PHILEO_DEFAULT_LIKE_CONFIG", {
    "css_class_on": "icon-heart",
    "css_class_off": "icon-heart-empty",
    "like_text_on": "Unlike",
    "like_text_off": "Like",
    "count_text_singular": "like",
    "count_text_plural": "likes"
})

LIKABLE_MODELS = getattr(settings, "PHILEO_LIKABLE_MODELS", defaultdict(dict))

for model in LIKABLE_MODELS:
    custom_data = LIKABLE_MODELS[model].copy()
    default_data = DEFAULT_LIKE_CONFIG.copy()
    LIKABLE_MODELS[model] = default_data
    LIKABLE_MODELS[model].update(custom_data)

########NEW FILE########
__FILENAME__ = signals
import django.dispatch


object_liked = django.dispatch.Signal(providing_args=["like", "request"])
object_unliked = django.dispatch.Signal(providing_args=["object", "request"])

########NEW FILE########
__FILENAME__ = phileo_tags
from django import template

from django.template.loader import render_to_string
from django.contrib.contenttypes.models import ContentType

from phileo.models import Like
from phileo.utils import _allowed, widget_context
from phileo.settings import LIKABLE_MODELS

register = template.Library()


@register.assignment_tag
def who_likes(athlete):
    return Like.objects.filter(
        receiver_content_type=ContentType.objects.get_for_model(athlete),
        receiver_object_id=athlete.pk
    )


class LikesNode(template.Node):
    
    def __init__(self, user, model_list, varname):
        self.user = template.Variable(user)
        
        # Default to all the registered models
        if len(model_list) == 0:
            # These need to look like strings, otherwise they will be treated as variables
            # when they are `resolve()`d later
            model_list = ['"%s"' % model for model in LIKABLE_MODELS]
        
        self.model_list = [template.Variable(m) for m in model_list]
        self.varname = varname
    
    def render(self, context):
        user = self.user.resolve(context)
        content_types = []
        
        for raw_model_name in self.model_list:
            try:
                model_name = raw_model_name.resolve(context)
            except template.VariableDoesNotExist:
                continue
            
            if not _allowed(model_name):
                continue
            
            app, model = model_name.split(".")
            content_type = ContentType.objects.get(app_label=app, model__iexact=model)
            content_types.append(content_type)
        
        context[self.varname] = Like.objects.filter(
            sender=user,
            receiver_content_type__in=content_types
        )
        return ""


@register.tag
def likes(parser, token):
    """
    {% likes user "app.Model" "app.Model" "app.Model" as like_objs %}
    """
    tokens = token.split_contents()
    user = tokens[1]
    varname = tokens[-1]
    model_list = tokens[2:-2]
    
    return LikesNode(user, model_list, varname)


class LikeRenderer(template.Node):
    
    def __init__(self, varname):
        self.varname = template.Variable(varname)
    
    def render(self, context):
        like = self.varname.resolve(context)
        
        instance = like.receiver
        content_type = like.receiver_content_type
        app_name = content_type.app_label
        model_name = content_type.model.lower()
        
        like_context = {
            'instance': instance,
            'like': like,
        }
        
        return render_to_string([
            'phileo/%s/%s.html' % (app_name, model_name),
            'phileo/%s/like.html' % (app_name),
            'phileo/_like.html',
        ], like_context, context)


@register.tag
def render_like(parser, token):
    """
    {% likes user as like_list %}
    <ul>
        {% for like in like_list %}
            <li>{% render_like like %}</li>
        {% endfor %}
    </ul>
    """
    
    tokens = token.split_contents()
    var = tokens[1]
    
    return LikeRenderer(var)


@register.filter
def likes_count(obj):
    """
    Something like:
    
        <div class="likes_count">{{ obj|likes_count }}</div>
    
    will render:
    
        <div class="likes_count">34</div>
    """
    return Like.objects.filter(
        receiver_content_type=ContentType.objects.get_for_model(obj),
        receiver_object_id=obj.pk
    ).count()


@register.inclusion_tag("phileo/_widget.html")
def phileo_widget(user, obj):
    return widget_context(user, obj)


@register.inclusion_tag("phileo/_widget_brief.html")
def phileo_widget_brief(user, obj):
    return widget_context(user, obj)


class LikedObjectsNode(template.Node):
    
    def __init__(self, objects, user, varname):
        self.objects = template.Variable(objects)
        self.user = template.Variable(user)
        self.varname = varname
    
    def get_objects(self, user, objects):
        is_stream = None
        get_id = None
        indexed = {}
        
        for obj in objects:
            if hasattr(obj, "cast") and callable(obj.cast):
                obj = obj.cast()
            if is_stream is None and get_id is None:
                is_stream = not hasattr(obj, "_meta")
                get_id = lambda x: is_stream and x.item.id or x.id
            
            ct = ContentType.objects.get_for_model(is_stream and obj.item or obj)
            if ct not in indexed.keys():
                indexed[ct] = []
            obj.liked = False
            indexed[ct].append(obj)
        
        for ct in indexed.keys():
            likes = Like.objects.filter(
                sender=user,
                receiver_content_type=ct,
                receiver_object_id__in=[get_id(o) for o in indexed[ct]]
            )
            
            for obj in indexed[ct]:
                for like in likes:
                    if like.receiver_object_id == get_id(obj):
                        obj.liked = True
                yield obj
    
    def render(self, context):
        user = self.user.resolve(context)
        objects = self.objects.resolve(context)
        context[self.varname] = self.get_objects(user, objects)
        return ""


@register.tag
def liked(parser, token):
    """
    {% liked objects by user as varname %}
    """
    tag, objects, _, user, _, varname = token.split_contents()
    return LikedObjectsNode(objects, user, varname)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import url, patterns


urlpatterns = patterns("phileo.views",
    url(r"^like/(?P<content_type_id>\d+):(?P<object_id>\d+)/$", "like_toggle", name="phileo_like_toggle")
)

########NEW FILE########
__FILENAME__ = utils
from django.core.urlresolvers import reverse
from django.db import models

from django.contrib.contenttypes.models import ContentType

from phileo.models import Like
from phileo.settings import LIKABLE_MODELS


def name(obj):
    return "%s.%s" % (obj._meta.app_label, obj._meta.object_name)


def _allowed(model):
    if isinstance(model, models.Model):
        app_model = name(model)
    elif isinstance(model, str):
        app_model = model
    else:
        app_model = str(model)
    return app_model in LIKABLE_MODELS


def get_config(obj):
    return LIKABLE_MODELS[name(obj)]


def widget_context(user, obj):
    ct = ContentType.objects.get_for_model(obj)
    config = get_config(obj)
    like_count = Like.objects.filter(
       receiver_content_type=ct,
       receiver_object_id=obj.pk
    ).count()
    if like_count == 1:
        counts_text = config["count_text_singular"]
    else:
        counts_text = config["count_text_plural"]
    
    can_like = user.has_perm("phileo.can_like", obj)
    
    ctx = {
        "can_like": can_like,
        "like_count": like_count,
        "counts_text": counts_text,
    }
    
    if can_like:
        liked = Like.objects.filter(
           sender=user,
           receiver_content_type=ct,
           receiver_object_id=obj.pk
        ).exists()
        
        if liked:
            like_text = config["like_text_on"]
            like_class = config["css_class_on"]
        else:
            like_text = config["like_text_off"]
            like_class = config["css_class_off"]
        
        ctx.update({
            "like_url": reverse("phileo_like_toggle", kwargs={
                "content_type_id": ct.id,
                "object_id": obj.pk
            }),
            "liked": liked,
            "like_text": like_text,
            "like_class": like_class
        })
    return ctx

########NEW FILE########
__FILENAME__ = views
import json

from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from phileo.models import Like
from phileo.signals import object_liked, object_unliked
from phileo.utils import widget_context


@login_required
@require_POST
def like_toggle(request, content_type_id, object_id):
    content_type = get_object_or_404(ContentType, pk=content_type_id)
    obj = content_type.get_object_for_this_type(pk=object_id)
    
    if not request.user.has_perm("phileo.can_like", obj):
        return HttpResponseForbidden()
    
    like, created = Like.objects.get_or_create(
        sender=request.user,
        receiver_content_type=content_type,
        receiver_object_id=object_id
    )
    
    if created:
        object_liked.send(sender=Like, like=like, request=request)
    else:
        like.delete()
        object_unliked.send(
            sender=Like,
            object=obj,
            request=request
        )
    
    if request.is_ajax():
        html_ctx = widget_context(request.user, obj)
        template = "phileo/_widget.html"
        if request.GET.get("t") == "b":
            template = "phileo/_widget_brief.html"
        data = {
            "html": render_to_string(
                template,
                html_ctx,
                context_instance=RequestContext(request)
            ),
            "likes_count": html_ctx["like_count"],
            "liked": html_ctx["liked"],
        }
        return HttpResponse(json.dumps(data), mimetype="application/json")
    
    return redirect(request.META["HTTP_REFERER"])

########NEW FILE########
