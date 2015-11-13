__FILENAME__ = admin
from activity_stream.models import * 
from django.contrib import admin

admin.site.register(ActivityFollower)
admin.site.register(ActivityTypes)
admin.site.register(ActivityStreamItem)

########NEW FILE########
__FILENAME__ = management
from django.db.models import signals
from django.utils.translation import ugettext_noop as _
import activity_stream.models
from activity_stream.models import ActivityTypes

try:
    from notification import models as notification
except ImportError:
    notification = None

    
def create_activity_types(app, created_models, verbosity, **kwargs):

    if notification:
        notification.create_notice_type("new_follower", _("New Follower"), _("somebody is following you now"), default=2)

    try:
        ActivityTypes.objects.get_or_create(name="started_following", batch_time_minutes=30, is_batchable=True)
        ActivityTypes.objects.get_or_create(name="likes", is_batchable=False)
    except:
        pass
    
signals.post_syncdb.connect(create_activity_types, sender=activity_stream.models)


########NEW FILE########
__FILENAME__ = models
from django.db import models

from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from django.contrib.auth.models import User

try:
    import cPickle as pickle
except:
    import pickle

import base64

# settings used by the app
ACTIVITY_DEFAULT_BATCH_TIME = getattr(settings, "ACTIVITY_DEFAULT_BATCH_TIME",
                                      30)

class SerializedDataField(models.TextField):
    """Because Django for some reason feels its needed to repeatedly call
    to_python even after it's been converted this does not support strings."""
    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        if value is None: return
        if not isinstance(value, basestring): return value
        value = pickle.loads(base64.b64decode(value))
        return value

    def get_db_prep_save(self, value):
        if value is None: return
        return base64.b64encode(pickle.dumps(value))


class ActivityFollower(models.Model):
    to_user  = models.ForeignKey(User, related_name="followed")
    from_user  = models.ForeignKey(User, related_name="following")
    created_at = models.DateTimeField(_('created at'), default=datetime.now)
    def __unicode__(self):
        return str(self.from_user)+" following "+str(self.to_user)
    class Meta:
        unique_together       = [('to_user', 'from_user')]
    
class ActivityTypes(models.Model):
    name  = models.CharField(_('title'), max_length=200, unique=True)
    template = models.TextField(_('template'), null=True, blank=True)
    batch_time_minutes = models.IntegerField(_("batch time in minutes"),
                                             null=True,
                                             blank=True)
    batch_template = models.TextField(_('batch template'), null=True, blank=True)
    is_batchable = models.BooleanField(default=False)
    def __unicode__(self):
        return self.name


class ActivityStreamItem(models.Model):
    SAFETY_LEVELS = (
        (1, _('Public')),
        (2, _('Followers')),
        (3, _('Friends')),
        (3, _('Private')),
    )
    actor = models.ForeignKey(User, related_name="activity_stream")
    type = models.ForeignKey(ActivityTypes, related_name="segments", blank=True,
                             null=True)

    data = SerializedDataField(_('data'), blank=True, null=True)

    safetylevel = models.IntegerField(_('safetylevel'), choices=SAFETY_LEVELS,
                                      default=2, help_text=_('Who can see this?'))
    created_at      = models.DateTimeField(_('created at'), default=datetime.now)

    is_batched = models.BooleanField(default=False)
    

    def first_subject(self):
        return self.subjects.all()[0]

    class Meta:
        get_latest_by       = '-created_at'

    def __unicode__(self):
        return str(self.actor)+" "+str(self.type)+" is_batched: %s"%self.is_batched

    def get_absolute_url(self):
        return ('activity_item', None, {
            'username': self.actor.username,
            'id': self.id
    })

    def render(self, context):
        from django.template.loader import get_template
        from django.template import Template
        from django.template import Context
        t = get_template('activity_stream/%s/full%s.html'%(self.type.name,self.get_batch_suffix()))
        html = t.render(Context({'activity_item': self,
                'request': context.get('request')}))
        return html
    get_absolute_url = models.permalink(get_absolute_url)
    
    def get_batch_suffix(self):
        if self.is_batched:
            return "_batched"
        else:
            return ""


class ActivityStreamItemSubject(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()
    activity_stream_item = models.ForeignKey(ActivityStreamItem,
                                             related_name="subjects")

    def __unicode__(self):
        return "%s %s"%(self.content_type, self.object_id)


from django.db.models.signals import post_save, post_delete
def delete_activity_on_subject_delete(sender, instance, **kwargs):
    if instance.activity_stream_item.subjects.count()<1:
        instance.activity_stream_item.delete()
post_delete.connect(delete_activity_on_subject_delete,
                    sender=ActivityStreamItemSubject)


def get_people_i_follow(user, count=20, offset=0):
    if hasattr(settings, "ACTIVITY_GET_PEOPLE_I_FOLLOW"):
        return settings.ACTIVITY_GET_PEOPLE_I_FOLLOW(user)
    else:
        followers =  ActivityFollower.objects.filter(from_user=user).all()[offset:count]
        return [follower.to_user for follower in followers]


def get_my_followers(user, count=20, offset=0):
    if hasattr(settings, "ACTIVITY_GET_MY_FOLLOWERS"):
        return settings.ACTIVITY_GET_MY_FOLLOWERS(user)
    else:
        followers = ActivityFollower.objects.filter(to_user=user).all()[offset:count]
        return [follower.from_user for follower in followers]


def create_activity_item(type, user, subject, data=None, safetylevel=1, custom_date=None):
    type = ActivityTypes.objects.get(name=type)
    if type.is_batchable:
        # see if one exists in timeframe
        batch_minutes = type.batch_time_minutes
        if not batch_minutes:
            batch_minutes = ACTIVITY_DEFAULT_BATCH_TIME

        cutoff_time = datetime.now()-timedelta(minutes=batch_minutes)
        batchable_items = ActivityStreamItem.objects.filter(actor=user, type=type,
                  created_at__gt=cutoff_time).order_by('-created_at').all()[0:1]
        if batchable_items: # if no batchable items then just create a ActivityStreamItem below
            batchable_items[0].subjects.create(content_object=subject)
            batchable_items[0].is_batched = True
            batchable_items[0].save()
            return batchable_items[0]

    new_item = ActivityStreamItem.objects.create(actor=user, type=type, data=data,
                                                 safetylevel=safetylevel)
    new_item.subjects.create(content_object=subject)
    
    if custom_date:
        new_item.created_at = custom_date
        new_item.save() 
    return new_item

    
from django.contrib.contenttypes import generic
class TestSubject(models.Model):
    test = models.BooleanField(default=False)
    activity = generic.GenericRelation(ActivityStreamItemSubject)

########NEW FILE########
__FILENAME__ = activity_stream_tags
from django.template import Library, Node, TemplateSyntaxError, TemplateDoesNotExist
from activity_stream.models import ActivityFollower, ActivityStreamItem, get_people_i_follow, get_my_followers
from django.template import Variable, resolve_variable
from django.template import loader
from django.db.models import get_model
from django import template

import datetime

register = Library()


@register.inclusion_tag("activity_stream/follower_list.html", takes_context=True)
def followed_by_him(context, user, count):
    followed = get_people_i_follow(user, count)
    return {"followed": followed, "request":context.get("request")}


@register.inclusion_tag("activity_stream/following_list.html", takes_context=True)
def following_him(context, user, count):
    fans = get_my_followers(user, count)
    return {"following": fans, "request":context.get("request")}


@register.inclusion_tag("activity_stream/user_activity_stream.html", takes_context=True)
def users_activity_stream(context, user, count, offset=0):
	if not count:
		count = 20
		
	if not offset:
		offset=0
	activity_items = ActivityStreamItem.objects.filter(actor=user, 
						       subjects__isnull=False, 
						       created_at__lte=datetime.datetime.now())\
						.order_by('-created_at').distinct()[offset:count]
	
	return {"activity_items": activity_items,
			"user": context.get("user"),
			"request":context.get("request")
			}


@register.inclusion_tag("activity_stream/friends_activity_stream.html", takes_context=True)
def following_activity_stream(context, user, count, offset=0):
	
	if not count:
		count = 20
		
	if not offset:
		offset=0
	
	following =  get_people_i_follow(user, 1000)
	following = list(following)
	following.append(user)   
	activity_items = ActivityStreamItem.objects.filter(actor__in=following, \
													   subjects__isnull=False, \
													   created_at__lte=datetime.datetime.now())\
												.order_by('-created_at').distinct()[offset:count]
	return {"activity_items": activity_items, "user": context.get("user"),
		"request":context.get("request")}


@register.inclusion_tag("activity_stream/global_activity_stream.html", takes_context=True)
def global_activity_stream(context, count, offset=0, privacylevel=0):
	
	if not count:
		count = 20
		
	if not offset:
		offset=0
		
	activity_items = ActivityStreamItem.objects.filter(subjects__isnull=False,
										created_at__lte=datetime.datetime.now())\
								.order_by('-created_at').distinct()[offset:count]
	
	return {"activity_items": activity_items, "user": context.get("user"),
		"request":context.get("request")}


class RenderActivityNode(Node):
    def __init__(self, activity):
        self.activity = activity
        print self.activity
    
    def render(self, context):
        activity = context[self.activity]
        return activity.render(context)

def render_activity(parser, token):
    try:
        tag_name, format_string = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires a single argument" % token.contents.split()[0]
    return RenderActivityNode(format_string)

register.tag('render_activity', render_activity)


class IsFollowingNode(Node):
    def __init__(self, from_user, to_user, node_true, node_false):
        self.from_user = template.Variable(from_user)
        self.to_user = template.Variable(to_user)
        self.node_true = node_true
        self.node_false = node_false
        
    def render(self, context):
        to_user = self.to_user.resolve(context)
        from_user = self.from_user.resolve(context)
        if to_user and from_user:
            if to_user.is_authenticated() and from_user.is_authenticated():
                is_following = ActivityFollower.objects.filter(to_user=to_user,from_user=from_user).count()
                if is_following:
                    return self.node_true.render(context)
                else:
                    return self.node_false.render(context)
            else:
                return self.node_false.render(context)

def is_following(parser, token):
    bits = token.split_contents()[1:]
    nodelist_true = parser.parse(('else', 'endif_is_following'))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse(('endif_is_following',))
        parser.delete_first_token()
    else:
        nodelist_false = None
    return IsFollowingNode(bits[0], bits[1], nodelist_true, nodelist_false)

register.tag('if_is_following', is_following)

########NEW FILE########
__FILENAME__ = tests
import os, re
from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.core.files.base import ContentFile

from activity_stream.models import *
from activity_stream.templatetags.activity_stream_tags import users_activity_stream

import datetime

class StoryTest(TestCase):
    def setUp(self):
        self.file_path = os.path.join(os.path.realpath(os.path.dirname(__file__)), "../../test_data")
        User.objects.get_or_create(username="admin", email="sfd@sdf.com")
        ActivityTypes.objects.create(name="placed", is_batchable=True)
        ActivityTypes.objects.create(name="placed2")

    def test_cascaded_delete(self):
        c = Client()
        c.login(username='admin', password='localhost')
        photo = TestSubject.objects.create(test=True)
        photo2 = TestSubject.objects.create(test=True)
        activityItem = create_activity_item("placed", User.objects.get(username="admin"), photo)
        activityItem.delete()
        self.assertTrue(TestSubject.objects.get(pk=photo.id))

        activityItem2 = create_activity_item("placed", User.objects.get(username="admin"), photo2)
        items = users_activity_stream({}, User.objects.get(username="admin"),1000)
        self.assertEquals(len(items['activity_items']), 1)

        photo2.delete()

        items = users_activity_stream({}, User.objects.get(username="admin"),1000)
        self.assertEquals(len(items['activity_items']), 0)

    def test_batching(self):
        c = Client()
        c.login(username='admin', password='localhost')
        photo = TestSubject.objects.create(test=True)
        photo2 = TestSubject.objects.create(test=True)
        photo.save()
        activityItem1 = create_activity_item("placed", \
                                             User.objects.get(username="admin"),\
                                             photo)
        self.assertTrue(activityItem1)
        self.assertEquals(activityItem1.is_batched, False)
        self.assertEquals(activityItem1.subjects.count(), 1)

        activityItem2 = create_activity_item("placed", \
                                             User.objects.get(username="admin"), \
                                            photo2)
        self.assertTrue(activityItem2)
        self.assertEquals(activityItem2.is_batched, True)
        self.assertEquals(activityItem2.subjects.count(), 2)

        #activityItem2.delete()
        #activityItem2.delete()


    def test_future_activities(self):
        c = Client()
        c.login(username='admin', password='localhost')
        photo = TestSubject.objects.create(test=False)
        photo.save()
        custom_date = datetime.date.today() + datetime.timedelta(3)
        activityItem = create_activity_item("placed2",\
                                            User.objects.get(username="admin"),\
                                            photo, custom_date=custom_date)
        self.assertTrue(activityItem)
        self.assertEquals(activityItem.is_batched, False)
        self.assertEquals(activityItem.subjects.count(), 1)
        items = users_activity_stream({}, User.objects.get(username="admin"),1000)
        self.assertEquals(len(items['activity_items']), 0)
        activityItem.delete()



########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^global-activity-stream/$', 'activity_stream.views.global_stream',
        name='global_activity_stream'),
    
    url(r'^ajax-global-activity-stream/$', 'activity_stream.views.global_stream',
            {"template_name":"activity_stream/ajax_global_stream.html"},
            name='ajax_global_activity_stream'),
    
    url(r'^(?P<username>[-\w]+)/(?P<id>[\d]+)/$',
         'activity_stream.views.activity_stream_item', name='activity_item'),
    
    url(r'^(?P<username>[-\w]+)/$', 'activity_stream.views.activity_stream',
        name='activity_stream'),
    
    url(r'^(?P<username>[-\w]+)/ajax$', 'activity_stream.views.following_stream',
        {"template_name":"activity_stream/ajax_following_stream.html"},
        name='ajax_following_stream'),
    
    url(r'^(?P<username>[-\w]+)/start-follow/$',
        'activity_stream.views.start_follow', name='start_activity_follow'),
    
    url(r'^(?P<username>[-\w]+)/end-follow/$',
         'activity_stream.views.end_follow', name='end_activity_follow'),
    
    url(r'^(?P<id>[\d]+)/like/$', 'activity_stream.views.like', name='activity_like'),
    
    
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.template import RequestContext
from django.db import IntegrityError
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.generic import date_based
from django.conf import settings
from activity_stream.models import ActivityFollower, create_activity_item, ActivityStreamItem

import datetime
try:
    from notification import models as notification
except ImportError:
    notification = None

def activity_stream_item(request, username, id,
                         template_name="activity_stream/activity_item.html"):
    user = get_object_or_404(User, username=username)
    activity_item = get_object_or_404(ActivityStreamItem, pk=id)
    return render_to_response(template_name, {
        "activity_item": activity_item,
        "viewed_user": user,
    }, context_instance=RequestContext(request))

@login_required
def start_follow(request, username, success_url=None):
    user = get_object_or_404(User, username=username)
    follower = ActivityFollower(to_user=user, from_user=request.user)
    follower.save()

    create_activity_item("started_following", request.user, user)

    if not success_url:
        success_url = request.META.get('HTTP_REFERER','/')
       
    if notification:
        notification.send([user], "new_follower", {"follower": request.user})
        
    return HttpResponseRedirect(success_url)

@login_required
def end_follow(request, username, success_url=None):
    user = get_object_or_404(User, username=username)
    follower = ActivityFollower.objects.get(to_user=user, from_user=request.user)
    follower.delete()
    if not success_url:
        success_url = reverse("activity_stream", args=(user.username,))
    return HttpResponseRedirect(success_url)
    
    
@login_required
def like(request, id):
    subject = get_object_or_404(ActivityStreamItem, pk=id)
    create_activity_item("likes", request.user, subject)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER','/'))


def activity_stream(request, username, template_name="activity_stream/activity_stream.html"):
    user = get_object_or_404(User, username=username)
    return render_to_response(template_name, {
        "viewed_user": user,
        "count": request.GET.get("count", None),
        "offset": request.GET.get("offset", None),
    }, context_instance=RequestContext(request))


def global_stream(request, template_name="activity_stream/global_activity_stream.html"):
    return render_to_response(template_name, {
        "count": request.GET.get("count", None),
        "offset": request.GET.get("offset", None),
    }, context_instance=RequestContext(request))
    
    
def following_stream(request, username, template_name="activity_stream/following_stream.html"):
    user = get_object_or_404(User, username=username)
    return render_to_response(template_name, {
        "viewed_user": user,
        "count": request.GET.get("count", None),
        "offset": request.GET.get("offset", None),
    }, context_instance=RequestContext(request))



########NEW FILE########
__FILENAME__ = app_test_runner
#!/usr/bin/env python

import os
import sys

from optparse import OptionParser

from django.conf import settings
from django.core.management import call_command

def main():
    """
    The entry point for the script. This script is fairly basic. Here is a
    quick example of how to use it::
    
        app_test_runner.py [path-to-app]
    
    You must have Django on the PYTHONPATH prior to running this script. This
    script basically will bootstrap a Django environment for you.
    
    By default this script with use SQLite and an in-memory database. If you
    are using Python 2.5 it will just work out of the box for you.
    
    TODO: show more options here.
    """
    parser = OptionParser()
    parser.add_option("--DATABASE_ENGINE", dest="DATABASE_ENGINE", default="sqlite3")
    parser.add_option("--DATABASE_NAME", dest="DATABASE_NAME", default="")
    parser.add_option("--DATABASE_USER", dest="DATABASE_USER", default="")
    parser.add_option("--DATABASE_PASSWORD", dest="DATABASE_PASSWORD", default="")
    parser.add_option("--SITE_ID", dest="SITE_ID", type="int", default=1)
    
    options, args = parser.parse_args()
    
    # check for app in args
    try:
        app_path = args[0]
    except IndexError:
        print "You did not provide an app path."
        raise SystemExit
    else:
        if app_path.endswith("/"):
            app_path = app_path[:-1]
        parent_dir, app_name = os.path.split(app_path)
        sys.path.insert(0, parent_dir)
    
    settings.configure(**{
        "DATABASE_ENGINE": options.DATABASE_ENGINE,
        "DATABASE_NAME": options.DATABASE_NAME,
        "DATABASE_USER": options.DATABASE_USER,
        "DATABASE_PASSWORD": options.DATABASE_PASSWORD,
        "SITE_ID": options.SITE_ID,
        "ROOT_URLCONF": "",
        "TEMPLATE_LOADERS": (
            "django.template.loaders.filesystem.load_template_source",
            "django.template.loaders.app_directories.load_template_source",
        ),
        "TEMPLATE_DIRS": (
            os.path.join(os.path.dirname(__file__), "templates"),
        ),
        "INSTALLED_APPS": (
            # HACK: the admin app should *not* be required. Need to spend some
            # time looking into this. Django #8523 has a patch for this issue,
            # but was wrongly attached to that ticket. It should have its own
            # ticket.
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.sites",
            app_name,
        ),
    })
    call_command("test")

if __name__ == "__main__":
    main()
########NEW FILE########
