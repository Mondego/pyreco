__FILENAME__ = actions
from django.core.exceptions import PermissionDenied
from hitcount.models import BlacklistIP, BlacklistUserAgent

def blacklist_ips(modeladmin, request, queryset):
    for obj in queryset:
       ip, created = BlacklistIP.objects.get_or_create(ip=obj.ip)
       if created:
           ip.save()
    msg = "Successfully blacklisedt %d IPs." % queryset.count() 
    modeladmin.message_user(request, msg)
blacklist_ips.short_description = "BLACKLIST the selected IP ADDRESSES"

def blacklist_user_agents(modeladmin, request, queryset):
    for obj in queryset:
       ua, created = BlacklistUserAgent.objects.get_or_create(
                        user_agent=obj.user_agent)
       if created:
           ua.save()
    msg = "Successfully blacklisted %d User Agents." % queryset.count() 
    modeladmin.message_user(request, msg)
blacklist_user_agents.short_description = "BLACKLIST the selected USER AGENTS"

def delete_queryset(modeladmin, request, queryset):
    # TODO 
    #
    # Right now, when you delete a hit there is no warning or "turing back".
    # Consider adding a "are you sure you want to do this?" as is 
    # implemented in django's contrib.admin.actions file.

    if not modeladmin.has_delete_permission(request):
        raise PermissionDenied
    else:
        if queryset.count() == 1:
            msg = "1 hit was"
        else:
            msg = "%s hits were" % queryset.count()

        for obj in queryset.iterator():
            obj.delete() # calling it this way to get custom delete() method

        modeladmin.message_user(request, "%s successfully deleted." % msg)
delete_queryset.short_description = "DELETE selected hits"

def blacklist_delete_ips(modeladmin, request, queryset):
    blacklist_ips(modeladmin, request, queryset)
    delete_queryset(modeladmin, request, queryset)
blacklist_delete_ips.short_description = "DELETE the selected hits and " + \
                                         "BLACKLIST the IP ADDRESSES"

def blacklist_delete_user_agents(modeladmin, request, queryset):
    blacklist_user_agents(modeladmin, request, queryset)
    delete_queryset(modeladmin, request, queryset)
blacklist_delete_user_agents.short_description = "DELETE the selected hits " + \
                                            "and BLACKLIST the USER AGENTS"


########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from hitcount.models import Hit, HitCount, BlacklistIP, BlacklistUserAgent
from hitcount import actions

def created_format(obj):
    '''
    Format the created time for the admin. PS: I am not happy with this.
    '''
    return "%s" % obj.created.strftime("%m/%d/%y<br />%H:%M:%S")
created_format.short_description = "Date (UTC)"
created_format.allow_tags = True
created_format.admin_order_field = 'created'


class HitAdmin(admin.ModelAdmin):
    list_display = (created_format,'user','ip','user_agent','hitcount')
    search_fields = ('ip','user_agent')
    date_hierarchy = 'created'
    actions = [ actions.blacklist_ips,
                actions.blacklist_user_agents,
                actions.blacklist_delete_ips,
                actions.blacklist_delete_user_agents,
                actions.delete_queryset,
                ]

    def __init__(self, *args, **kwargs):
        super(HitAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None,)

    def get_actions(self, request):
        # Override the default `get_actions` to ensure that our model's
        # `delete()` method is called.
        actions = super(HitAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

# TODO: Add inlines to the HitCount object so we can see a list of the recent
# hits for the object.  For this inline to work, we need to:
#   a) be able to see the hit data but *not* edit it
#   b) have the `delete` command actually alter the HitCount
#   c) remove the ability to 'add new hit'
#
#class HitInline(admin.TabularInline):
#    model = Hit
#    fk_name = 'hitcount'
#    extra = 0

class HitCountAdmin(admin.ModelAdmin):
    list_display = ('content_object','hits','modified')
    fields = ('hits',)

    # TODO - when above is ready
    #inlines = [ HitInline, ]

class BlacklistIPAdmin(admin.ModelAdmin):
    pass


class BlacklistUserAgentAdmin(admin.ModelAdmin):
    pass
 
admin.site.register(Hit, HitAdmin)
admin.site.register(HitCount, HitCountAdmin) 
admin.site.register(BlacklistIP, BlacklistIPAdmin)
admin.site.register(BlacklistUserAgent, BlacklistUserAgentAdmin)

########NEW FILE########
__FILENAME__ = hitcount_cleanup
import datetime
from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    help = "Can be run as a cronjob or directly to clean out old Hits objects from the database."

    def handle_noargs(self, **options):
        from django.db import transaction
        from hitcount.models import Hit
        from django.conf import settings
        grace = getattr(settings, 'HITCOUNT_KEEP_HIT_IN_DATABASE', {'days':30})
        period = datetime.datetime.now() - datetime.timedelta(**grace)
        Hit.objects.filter(created__lt=period).delete()
        transaction.commit_unless_managed()

########NEW FILE########
__FILENAME__ = models
import datetime

from django.db import models
from django.conf import settings
from django.db.models import F

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from django.dispatch import Signal

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')

# SIGNALS #

delete_hit_count = Signal(providing_args=['save_hitcount',])

def delete_hit_count_callback(sender, instance, 
        save_hitcount=False, **kwargs):
    '''
    Custom callback for the Hit.delete() method.

    Hit.delete(): removes the hit from the associated HitCount object.
    Hit.delete(save_hitcount=True): preserves the hit for the associated
        HitCount object.
    '''
    if not save_hitcount:
        instance.hitcount.hits = F('hits') - 1
        instance.hitcount.save()

delete_hit_count.connect(delete_hit_count_callback)


# EXCEPTIONS #

class DuplicateContentObject(Exception):
    'If content_object already exists for this model'
    pass

# MANAGERS #

class HitManager(models.Manager):

    def filter_active(self, *args, **kwargs):
        '''
        Return only the 'active' hits.
        
        How you count a hit/view will depend on personal choice: Should the
        same user/visitor *ever* be counted twice?  After a week, or a month,
        or a year, should their view be counted again?

        The defaulf is to consider a visitor's hit still 'active' if they 
        return within a the last seven days..  After that the hit
        will be counted again.  So if one person visits once a week for a year,
        they will add 52 hits to a given object.

        Change how long the expiration is by adding to settings.py:

        HITCOUNT_KEEP_HIT_ACTIVE  = {'days' : 30, 'minutes' : 30}

        Accepts days, seconds, microseconds, milliseconds, minutes, 
        hours, and weeks.  It's creating a datetime.timedelta object.
        '''
        grace = getattr(settings, 'HITCOUNT_KEEP_HIT_ACTIVE', {'days':7})
        period = datetime.datetime.utcnow() - datetime.timedelta(**grace)
        queryset = self.get_query_set()
        queryset = queryset.filter(created__gte=period)
        return queryset.filter(*args, **kwargs)


# MODELS #

class HitCount(models.Model):
    '''
    Model that stores the hit totals for any content object.

    '''
    hits            = models.PositiveIntegerField(default=0)
    modified        = models.DateTimeField(default=datetime.datetime.utcnow)
    content_type    = models.ForeignKey(ContentType,
                        verbose_name="content type",
                        related_name="content_type_set_for_%(class)s",)
    object_pk       = models.TextField('object ID')
    content_object  = generic.GenericForeignKey('content_type', 'object_pk')

    class Meta:
        ordering = ( '-hits', )
        #unique_together = (("content_type", "object_pk"),)
        get_latest_by = "modified"
        db_table = "hitcount_hit_count"
        verbose_name = "Hit Count"
        verbose_name_plural = "Hit Counts"

    def __unicode__(self):
        return u'%s' % self.content_object

    def save(self, *args, **kwargs):
        self.modified = datetime.datetime.utcnow()

        if not self.pk and self.object_pk and self.content_type:
            # Because we are using a models.TextField() for `object_pk` to
            # allow *any* primary key type (integer or text), we
            # can't use `unique_together` or `unique=True` to gaurantee
            # that only one HitCount object exists for a given object.
            #
            # This is just a simple hack - if there is no `self.pk`
            # set, it checks the database once to see if the `content_type`
            # and `object_pk` exist together (uniqueness).  Obviously, this
            # is not fool proof - if someone sets their own `id` or `pk` 
            # when initializing the HitCount object, we could get a duplicate.
            if HitCount.objects.filter(
                    object_pk=self.object_pk).filter(
                            content_type=self.content_type):
                raise DuplicateContentObject, "A HitCount object already " + \
                        "exists for this content_object."

        super(HitCount, self).save(*args, **kwargs)

    def hits_in_last(self, **kwargs):
        '''
        Returns hit count for an object during a given time period.

        This will only work for as long as hits are saved in the Hit database.
        If you are purging your database after 45 days, for example, that means
        that asking for hits in the last 60 days will return an incorrect
        number as that the longest period it can search will be 45 days.
        
        For example: hits_in_last(days=7).

        Accepts days, seconds, microseconds, milliseconds, minutes, 
        hours, and weeks.  It's creating a datetime.timedelta object.
        '''
        assert kwargs, "Must provide at least one timedelta arg (eg, days=1)"
        period = datetime.datetime.utcnow() - datetime.timedelta(**kwargs)
        return self.hit_set.filter(created__gte=period).count()

    def get_content_object_url(self):
        '''
        Django has this in its contrib.comments.model file -- seems worth
        implementing though it may take a couple steps.
        '''
        pass


class Hit(models.Model):
    '''
    Model captures a single Hit by a visitor.

    None of the fields are editable because they are all dynamically created.
    Browsing the Hit list in the Admin will allow one to blacklist both
    IP addresses and User Agents. Blacklisting simply causes those hits 
    to not be counted or recorded any more.

    Depending on how long you set the HITCOUNT_KEEP_HIT_ACTIVE , and how long
    you want to be able to use `HitCount.hits_in_last(days=30)` you should
    probably also occasionally clean out this database using a cron job.

    It could get rather large.
    '''
    created         = models.DateTimeField(editable=False)
    ip              = models.CharField(max_length=40, editable=False)
    session         = models.CharField(max_length=40, editable=False)
    user_agent      = models.CharField(max_length=255, editable=False)
    user            = models.ForeignKey(AUTH_USER_MODEL, null=True, editable=False)
    hitcount        = models.ForeignKey(HitCount, editable=False)

    class Meta:
        ordering = ( '-created', )    
        get_latest_by = 'created'

    def __unicode__(self):
        return u'Hit: %s' % self.pk 

    def save(self, *args, **kwargs):
        '''
        The first time the object is created and saved, we increment 
        the associated HitCount object by one.  The opposite applies
        if the Hit is deleted.
        '''
        if not self.created:
            self.hitcount.hits = F('hits') + 1
            self.hitcount.save()
            self.created = datetime.datetime.utcnow()

        super(Hit, self).save(*args, **kwargs)

    objects = HitManager()

    def delete(self, save_hitcount=False):
        '''
        If a Hit is deleted and save_hitcount=True, it will preserve the 
        HitCount object's total.  However, under normal circumstances, a 
        delete() will trigger a subtraction from the HitCount object's total.

        NOTE: This doesn't work at all during a queryset.delete().
        '''
        delete_hit_count.send(sender=self, instance=self, 
                save_hitcount=save_hitcount)
        super(Hit, self).delete()



class BlacklistIP(models.Model):
    ip = models.CharField(max_length=40, unique=True)

    class Meta: 
        db_table = "hitcount_blacklist_ip"
        verbose_name = "Blacklisted IP"
        verbose_name_plural = "Blacklisted IPs"

    def __unicode__(self):
        return u'%s' % self.ip


class BlacklistUserAgent(models.Model):
    user_agent = models.CharField(max_length=255, unique=True)

    class Meta: 
        db_table = "hitcount_blacklist_user_agent"
        verbose_name = "Blacklisted User Agent"
        verbose_name_plural = "Blacklisted User Agents"

    def __unicode__(self):
        return u'%s' % self.user_agent


########NEW FILE########
__FILENAME__ = hitcount_tags
from django import template
from django.template import TemplateSyntaxError
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.core.exceptions import MultipleObjectsReturned

from hitcount.models import HitCount

register = template.Library()


def get_target_ctype_pk(context, object_expr):
    # I don't really understand how this is working, but I took it from the
    # comment app in django.contrib and the removed it from the Node.
    try:
        obj = object_expr.resolve(context)
    except template.VariableDoesNotExist:
        return None, None

    return ContentType.objects.get_for_model(obj), obj.pk


def return_period_from_string(arg):
    '''
    Takes a string such as "days=1,seconds=30" and strips the quotes
    and returns a dictionary with the key/value pairs
    '''
    period = {}

    if arg[0] == '"' and arg[-1] == '"':
        opt = arg[1:-1] #remove quotes
    else:
        opt = arg

    for o in opt.split(","):
        key, value = o.split("=")
        period[str(key)] = int(value)

    return period
    

class GetHitCount(template.Node):

    def handle_token(cls, parser, token):
        args = token.contents.split()

        # {% get_hit_count for [obj] %}        
        if len(args) == 3 and args[1] == 'for':
            return cls(object_expr = parser.compile_filter(args[2]))
        
        # {% get_hit_count for [obj] as [var] %}
        elif len(args) == 5 and args[1] == 'for' and args[3] == 'as':
            return cls(object_expr = parser.compile_filter(args[2]),
                        as_varname  = args[4],)

        # {% get_hit_count for [obj] within ["days=1,minutes=30"] %}
        elif len(args) == 5 and args[1] == 'for' and args[3] == 'within':
            return cls(object_expr = parser.compile_filter(args[2]),
                        period = return_period_from_string(args[4]))

        # {% get_hit_count for [obj] within ["days=1,minutes=30"] as [var] %}
        elif len(args) == 7 and args [1] == 'for' and \
                args[3] == 'within' and args[5] == 'as':
            return cls(object_expr = parser.compile_filter(args[2]),
                        as_varname  = args[6],
                        period      = return_period_from_string(args[4]))

        else: # TODO - should there be more troubleshooting prior to bailing?
            raise TemplateSyntaxError, \
                    "'get_hit_count' requires " + \
                    "'for [object] in [timeframe] as [variable]' " + \
                    "(got %r)" % args
        
    handle_token = classmethod(handle_token)


    def __init__(self, object_expr, as_varname=None, period=None):
        self.object_expr = object_expr
        self.as_varname = as_varname
        self.period = period


    def render(self, context):
        ctype, object_pk = get_target_ctype_pk(context, self.object_expr)
        
        try:
            obj, created = HitCount.objects.get_or_create(content_type=ctype, 
                        object_pk=object_pk)
        except MultipleObjectsReturned:
            # from hitcount.models
            # Because we are using a models.TextField() for `object_pk` to
            # allow *any* primary key type (integer or text), we
            # can't use `unique_together` or `unique=True` to gaurantee
            # that only one HitCount object exists for a given object.

            # remove duplicate
            items = HitCount.objects.all().filter(content_type=ctype, object_pk=object_pk)
            obj = items[0]
            for extra_items in items[1:]:
                extra_items.delete()
                
        if self.period: # if user sets a time period, use it
            try:
                hits = obj.hits_in_last(**self.period)
            except:
                hits = '[hitcount error w/time period]'
        else:
            hits = obj.hits
        
        if self.as_varname: # if user gives us a variable to return
            context[self.as_varname] = str(hits) 
            return ''
        else:
            return str(hits)


def get_hit_count(parser, token):
    '''
    Returns hit counts for an object.

    - Return total hits for an object: 
      {% get_hit_count for [object] %}
    
    - Get total hits for an object as a specified variable:
      {% get_hit_count for [object] as [var] %}
    
    - Get total hits for an object over a certain time period:
      {% get_hit_count for [object] within ["days=1,minutes=30"] %}

    - Get total hits for an object over a certain time period as a variable:
      {% get_hit_count for [object] within ["days=1,minutes=30"] as [var] %}

    The time arguments need to follow datetime.timedelta's limitations:         
    Accepts days, seconds, microseconds, milliseconds, minutes, 
    hours, and weeks. 
    '''
    return GetHitCount.handle_token(parser, token)

register.tag('get_hit_count', get_hit_count)


class GetHitCountJavascript(template.Node):


    def handle_token(cls, parser, token):
        args = token.contents.split()
        
        if len(args) == 3 and args[1] == 'for':
            return cls(object_expr = parser.compile_filter(args[2]))

        else:
            raise TemplateSyntaxError, \
                    "'get_hit_count' requires " + \
                    "'for [object] in [timeframe] as [variable]' " + \
                    "(got %r)" % args

    handle_token = classmethod(handle_token)


    def __init__(self, object_expr):
        self.object_expr = object_expr


    def render(self, context):
        ctype, object_pk = get_target_ctype_pk(context, self.object_expr)
        
        obj, created = HitCount.objects.get_or_create(content_type=ctype, 
                        object_pk=object_pk)

        js =    "$.post( '" + reverse('hitcount_update_ajax') + "',"   + \
                "\n\t{ hitcount_pk : '" + str(obj.pk) + "' },\n"         + \
                "\tfunction(data, status) {\n"                         + \
                "\t\tif (data.status == 'error') {\n"                  + \
                "\t\t\t// do something for error?\n"                   + \
                "\t\t}\n\t},\n\t'json');"

        return js

def get_hit_count_javascript(parser, token):
    '''
    Return javascript for an object (goes in the document's onload function)
    and requires jQuery.  NOTE: only works on a single object, not an object
    list.

    For example:

    <script src="/media/js/jquery-latest.js" type="text/javascript"></script>
    <script type="text/javascript"><!--
    $(document).ready(function() {
        {% get_hit_count_javascript for [object] %}
    });
    --></script> 
    '''
    return GetHitCountJavascript.handle_token(parser, token)

register.tag('get_hit_count_javascript', get_hit_count_javascript)


########NEW FILE########
__FILENAME__ = utils
from django.conf import settings
import re

# this is not intended to be an all-knowing IP address regex
IP_RE = re.compile('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')

def get_ip(request):
    """
    Retrieves the remote IP address from the request data.  If the user is
    behind a proxy, they may have a comma-separated list of IP addresses, so
    we need to account for that.  In such a case, only the first IP in the
    list will be retrieved.  Also, some hosts that use a proxy will put the
    REMOTE_ADDR into HTTP_X_FORWARDED_FOR.  This will handle pulling back the
    IP from the proper place.

    **NOTE** This function was taken from django-tracking (MIT LICENSE)
             http://code.google.com/p/django-tracking/
    """

    # if neither header contain a value, just use local loopback
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR',
                                  request.META.get('REMOTE_ADDR', '127.0.0.1'))
    if ip_address:
        # make sure we have one and only one IP
        try:
            ip_address = IP_RE.match(ip_address)
            if ip_address:
                ip_address = ip_address.group(0)
            else:
                # no IP, probably from some dirty proxy or other device
                # throw in some bogus IP
                ip_address = '10.0.0.1'
        except IndexError:
            pass

    return ip_address

########NEW FILE########
__FILENAME__ = views
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.utils import simplejson
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from hitcount.utils import get_ip
from hitcount.models import Hit, HitCount, BlacklistIP, BlacklistUserAgent

def _update_hit_count(request, hitcount):
    '''
    Evaluates a request's Hit and corresponding HitCount object and,
    after a bit of clever logic, either ignores the request or registers
    a new Hit.

    This is NOT a view!  But should be used within a view ...

    Returns True if the request was considered a Hit; returns False if not.
    '''
    user = request.user

    if not request.session.session_key:
        request.session.save()

    session_key = request.session.session_key
    ip = get_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
    hits_per_ip_limit = getattr(settings, 'HITCOUNT_HITS_PER_IP_LIMIT', 0)
    exclude_user_group = getattr(settings,
                            'HITCOUNT_EXCLUDE_USER_GROUP', None)

    # first, check our request against the blacklists before continuing
    if BlacklistIP.objects.filter(ip__exact=ip) or \
            BlacklistUserAgent.objects.filter(user_agent__exact=user_agent):
        return False

    # second, see if we are excluding a specific user group or not
    if exclude_user_group and user.is_authenticated():
        if user.groups.filter(name__in=exclude_user_group):
            return False

    #start with a fresh active query set (HITCOUNT_KEEP_HIT_ACTIVE )
    qs = Hit.objects.filter_active()

    # check limit on hits from a unique ip address (HITCOUNT_HITS_PER_IP_LIMIT)
    if hits_per_ip_limit:
        if qs.filter(ip__exact=ip).count() > hits_per_ip_limit:
            return False

    # create a generic Hit object with request data
    hit = Hit(  session=session_key,
                hitcount=hitcount,
                ip=get_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],)

    # first, use a user's authentication to see if they made an earlier hit
    if user.is_authenticated():
        if not qs.filter(user=user,hitcount=hitcount):
            hit.user = user #associate this hit with a user
            hit.save()
            return True

    # if not authenticated, see if we have a repeat session
    else:
        if not qs.filter(session=session_key,hitcount=hitcount):
            hit.save()

            # forces a save on this anonymous users session
            request.session.modified = True

            return True

    return False

def json_error_response(error_message):
    return HttpResponse(simplejson.dumps(dict(success=False,
                                              error_message=error_message)))

# TODO better status responses - consider model after django-voting,
# right now the django handling isn't great.  should return the current
# hit count so we could update it via javascript (since each view will
# be one behind).
def update_hit_count_ajax(request):
    '''
    Ajax call that can be used to update a hit count.

    Ajax is not the only way to do this, but probably will cut down on
    bots and spiders.

    See template tags for how to implement.
    '''

    # make sure this is an ajax request
    if not request.is_ajax():
        raise Http404()

    if request.method == "GET":
        return json_error_response("Hits counted via POST only.")

    hitcount_pk = request.POST.get('hitcount_pk')

    try:
        hitcount = HitCount.objects.get(pk=hitcount_pk)
    except:
        return HttpResponseBadRequest("HitCount object_pk not working")

    result = _update_hit_count(request, hitcount)

    if result:
        status = "success"
    else:
        status = "no hit recorded"

    json = simplejson.dumps({'status': status})
    return HttpResponse(json,mimetype="application/json")

########NEW FILE########
