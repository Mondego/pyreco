__FILENAME__ = admin
from django.contrib import admin
from mailchimp.models import Campaign
from mailchimp.settings import VIEWS_OVERVIEW


class MailchimpAdmin(admin.ModelAdmin):
    def get_urls(self):
        from django.conf.urls import patterns, url
        urlpatterns = patterns('',
            url(r'^$',
                VIEWS_OVERVIEW,
                name='mailchimp_campaign_changelist',
                kwargs={'page':'1'}),
        )
        return urlpatterns
    
    def has_add_permission(self, request):
        # disable the 'add' button
        return False
    
    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('mailchimp.can_view')
        
    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Campaign, MailchimpAdmin)

########NEW FILE########
__FILENAME__ = chimp
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from mailchimp.chimpy.chimpy import Connection as BaseConnection, ChimpyException
from mailchimp.utils import wrap, build_dict, Cache, WarningLogger
from mailchimp.exceptions import (MCCampaignDoesNotExist, MCListDoesNotExist,
    MCConnectionFailed, MCTemplateDoesNotExist, MCFolderDoesNotExist)
from mailchimp.constants import *
from mailchimp.settings import WEBHOOK_KEY
import datetime


class SegmentCondition(object):
    OPERATORS = {
        'eq': lambda a,b: a == b,
        'ne': lambda a,b: a != b,
        'gt': lambda a,b: a > b,
        'lt': lambda a,b: a < b,
        'like': lambda a,b: a in b,
        'nlike': lambda a,b: a not in b,
        'starts': lambda a,b: str(a).startswith(str(b)),
        'ends': lambda a,b: str(a).endswith(str(b))
    }
    
    def __init__(self, field, op, value):
        self.field = field
        self.op = op
        self.value = value
        check_function_name = 'check_%s' % self.field
        if not hasattr(self, check_function_name):
            check_function_name = 'merge_check'
        self.checker = getattr(self, check_function_name)
        
    def check(self, member):
        return self.checker(member)
    
    def check_interests(self, member):
        interests = self.value.split(',')
        if self.op == 'all':
            for interest in interests:
                if interest not in member.interests:
                    return False
            return True
        elif self.op == 'one':
            for interest in interests:
                if interest in member.interests:
                    return True
            return False
        else:
            for interest in interests:
                if interest in member.interests:
                    return False
            return True
        
    def merge_check(self, member):
        return self.OPERATORS[self.op](member.merges[self.field.upper()], self.value)


class BaseChimpObject(object):
    _attrs = ()
    _methods = ()
    
    verbose_attr = 'id'
    cache_key = 'id'
    
    def __init__(self, master, info):
        self.master = master
        for attr in self._attrs:
            setattr(self, attr, info[attr])
            
        base = self.__class__.__name__.lower()
        self.cache = master.cache.get_child_cache(getattr(self, self.cache_key))
        self.con = master.con
        
        for method in self._methods:
            setattr(self, method, wrap(base, self.master.con, method, self.id))
            
    def __repr__(self):
        return '<%s object: %s>' % (self.__class__.__name__, getattr(self, self.verbose_attr))

    def __str__(self):
        return unicode(self).encode('utf-8')


class Campaign(BaseChimpObject):
    _attrs = ('archive_url', 'create_time', 'emails_sent', 'folder_id',
              'from_email', 'from_name', 'id', 'inline_css', 'list_id',
              'send_time', 'status', 'subject', 'title', 'to_name', 'type',
              'web_id')
    
    _methods =  ('delete', 'pause', 'replicate', 'resume', 'schedule',
                 'send_now', 'send_test', 'unschedule')
    
    verbose_attr = 'subject'

    def __init__(self, master, info):
        super(Campaign, self).__init__(master, info)
        try:
            self.list = self.master.get_list_by_id(self.list_id)
        except MCListDoesNotExist:
            self.list = None
        self._content = None
        self.frozen_info = info
        
    def __unicode__(self):
        return self.subject

    @property
    def content(self):
        return self.get_content()

    def get_content(self):
        if self._content is None:
            self._content = self.con.campaign_content(self.id)
        return self._content
    
    def send_now_async(self):
        now = datetime.datetime.utcnow()
        soon = now + datetime.timedelta(minutes=1)
        return self.schedule(soon)

    def delete(self):
        return self.con.campaign_delete(self.id)
        
    def pause(self):
        return self.con.campaign_pause(self.id)
        
    def update(self):
        status = []
        for key, value in self._get_diff():
            status.append(self.con.campaign_update(self.id, key, value))
        return all(status)
    
    def _get_diff(self):
        diff = []
        new_frozen = {}
        for key in self._attrs:
            current = getattr(self, key)
            if self.frozen_info[key] != current:
                diff.append((key, current))
            new_frozen[key] = current
        self.frozen_info = new_frozen
        return diff
    
    @property
    def is_sent(self):
        return self.status == 'sent'
        
        
class Member(BaseChimpObject):
    _attrs = ('email', 'timestamp')
    
    _extended_attrs = ('id', 'ip_opt', 'ip_signup', 'merges', 'status')
    
    verbose_attr = 'email'
    cache_key = 'email'
    
    def __init__(self, master, info):
        super(Member, self).__init__(master, info)
        
    def __unicode__(self):
        return self.email

    def __getattr__(self, attr):
        if attr in self._extended_attrs:
            return self.info[attr]
        raise AttributeError, attr
    
    @property
    def interests(self):
        return [i.strip() for i in self.merges['INTERESTS'].split(',')]
    
    @property
    def info(self):
        return self.get_info()
            
    def get_info(self):
        return self.cache.get('list_member_info', self.con.list_member_info, self.master.id, self.email)
    
    def update(self):
        return self.con.list_update_member(self.master.id, self.email, self.merges)
    
    
class LazyMemberDict(dict):
    def __init__(self, master):
        super(LazyMemberDict, self).__init__()
        self._list = master
        
    def __getitem__(self, key):
        if key in self:
            return super(LazyMemberDict, self).__getitem__(key)
        value = self._list.get_member(key)
        self[key] = value
        return value
        
        
class List(BaseChimpObject):
    '''
    This represents a mailing list. Most of the methods (defined in _methods) are wrappers of the flat
    API found in chimpy.chimpy. As such, signatures are the same.
    '''
    _methods = ('batch_subscribe', 
                'batch_unsubscribe', 
                'subscribe', # Sig: (email_address,merge_vars{},email_type='text',double_optin=True)
                'unsubscribe')
    
    _attrs = ('id', 'date_created', 'name', 'web_id', 'stats')
    
    verbose_attr = 'name'
    
    def __init__(self, *args, **kwargs):
        super(List, self).__init__(*args, **kwargs)
        self.members = LazyMemberDict(self)
    
    def segment_test(self, match, conditions):
        return self.master.con.campaign_segment_test(self.id, {'match': match, 'conditions': conditions})

    def list_interest_groupings(self):
        return self.master.con.list_interest_groupings(self.id)

    def list_interest_groups(self, grouping_id=None, full=False):
        grouping_id = int(grouping_id or self._default_grouping())
        groupings = self.list_interest_groupings()
        grouping = None
        for g in groupings:
            if int(g['id']) == grouping_id:
                grouping = g
                break
        if not grouping:
            return []
        if not full:
            return [group['name'] for group in grouping['groups']]
        return grouping
    
    def add_interest_group(self, groupname, grouping_id=None):
        grouping_id = grouping_id or self._default_grouping()
        return self.master.con.list_interest_group_add(self.id, groupname, grouping_id)
        
    def remove_interest_group(self, groupname, grouping_id=None):
        grouping_id = grouping_id or self._default_grouping()
        return self.master.con.list_interest_group_del(self.id, groupname, grouping_id)
        
    def update_interest_group(self, oldname, newname, grouping_id=None):
        grouping_id = grouping_id or self._default_grouping()
        return self.master.con.list_interest_group_update(self.id, oldname, newname, grouping_id)
    
    def add_interests_if_not_exist(self, *interests):
        self.cache.flush('interest_groups')
        interest_groups = self.interest_groups['groups']
        names = set(g['name'] for g in interest_groups)
        for interest in set(interests):
            if interest not in names:
                self.add_interest_group(interest)
                interest_groups.append(interest)

    def _default_grouping(self):
        if not hasattr(self, '_default_grouping_id'):
            groupings = self.list_interest_groupings()
            if len(groupings):
                self._default_grouping_id = groupings[0]['id']
            else:
                self._default_grouping_id = None
        return self._default_grouping_id

    @property
    def webhooks(self):
        return self.get_webhooks()
    
    def get_webhooks(self):
        return self.cache.get('webhooks', self.master.con.list_webhooks, self.id)
    
    def add_webhook(self, url, actions, sources):
        return self.master.con.list_webhook_add(self.id, url, actions, sources)
    
    def remove_webhook(self, url):
        return self.master.con.list_webhook_del(self.id, url)
    
    def add_webhook_if_not_exists(self, url, actions, sources):
        for webhook in self.webhooks:
            if webhook['url'] == url:
                return True
        return self.add_webhook(url, actions, sources)
    
    def install_webhook(self):
        domain = Site.objects.get_current().domain
        if not (domain.startswith('http://') or domain.startswith('https://')):
            domain = 'http://%s' % domain
        if domain.endswith('/'):
            domain = domain[:-1] 
        url = domain + reverse('mailchimp_webhook', kwargs={'key': WEBHOOK_KEY})
        actions = {'subscribe': True,
                   'unsubscribe': True,
                   'profile': True,
                   'cleaned': True,
                   'upemail': True,}
        sources = {'user': True,
                   'admin': True,
                   'api': False}
        return self.add_webhook_if_not_exists(url, actions, sources)
    
    @property
    def interest_groups(self):
        return self.get_interest_groups()
    
    def get_interest_groups(self):
        return self.cache.get('interest_groups', self.list_interest_groups, full=True)
    
    def add_merge(self, key, desc, req=None):
        req = req or {}
        return self.master.con.list_merge_var_add(self.id, key, desc, req if req else False)
        
    def remove_merge(self, key):
        return self.master.con.list_merge_var_del(self.id, key)
    
    def add_merges_if_not_exists(self, *new_merges):
        self.cache.flush('merges')
        merges = [m['tag'].upper() for m in self.merges]
        for merge in set(new_merges):
            if merge.upper() not in merges:
                self.add_merge(merge, merge, False)
                merges.append(merge.upper())
    
    @property
    def merges(self):
        return self.get_merges()
    
    def get_merges(self):
        return self.cache.get('merges', self.master.con.list_merge_vars, self.id)
    
    def __unicode__(self):
        return self.name

    def get_member(self, email):
        try:
            data = self.master.con.list_member_info(self.id, email)
        except ChimpyException:
            return None
        # actually it would make more sense giving the member everything
        memberdata = {}
        memberdata['timestamp'] = data['timestamp']
        memberdata['email'] = data['email']
        return Member(self, memberdata)
    
    def filter_members(self, segment_opts):
        """
        segment_opts = {'match': 'all' if self.segment_options_all else 'any',
        'conditions': simplejson.loads(self.segment_options_conditions)}
        """
        mode = all if segment_opts['match'] == 'all' else any
        conditions = [SegmentCondition(**dict((str(k), v) for k,v in c.items())) for c in segment_opts['conditions']]
        for email, member in self.members.items():
            if mode([condition.check(member) for condition in conditions]):
                yield member
    
    
class Template(BaseChimpObject):
    _attrs = ('id', 'layout', 'name', 'preview_image', 'sections', 'default_content', 'source', 'preview')
    
    verbose_attr = 'name'
    
    def build(self, **kwargs):
        class BuiltTemplate(object):
            def __init__(self, template, data):
                self.template = template
                self.data = data
                self.id = self.template.id
            
            def __iter__(self):
                return iter(self.data.items())
        data = {}
        for key, value in kwargs.items():
            if key in self.sections:
                data['html_%s' % key] = value
        return BuiltTemplate(self, data)


class Folder(BaseChimpObject):
    _attrs = ('id', 'name', 'type', 'date_created')

    def __init__(self, master, info):
        info['id'] = info['folder_id']
        del info['folder_id']

        super(Folder, self).__init__(master, info)


class Connection(object):
    REGULAR = REGULAR_CAMPAIGN
    PLAINTEXT = PLAINTEXT_CAMPAIGN
    ABSPLIT = ABSPLIT_CAMPAIGN
    RSS = RSS_CAMPAIGN
    TRANS = TRANS_CAMPAIGN
    AUTO = AUTO_CAMPAIGN
    DOES_NOT_EXIST = {
        'templates': MCTemplateDoesNotExist,
        'campaigns': MCCampaignDoesNotExist,
        'lists': MCListDoesNotExist,
        'folders': MCFolderDoesNotExist,
    }
    
    def __init__(self, api_key=None, secure=False, check=True):
        self._secure = secure
        self._check = check
        self._api_key = None
        self.con = None
        self.is_connected = False
        if api_key is not None:
            self.connect(api_key)
            
    def connect(self, api_key):
        self._api_key = api_key
        self.cache = Cache(api_key)
        self.warnings = WarningLogger()
        self.con = self.warnings.proxy(BaseConnection(self._api_key, self._secure))
        if self._check:
            status = self.ping()
            if status != STATUS_OK:
                raise MCConnectionFailed(status)
        self.is_connected = True
        
    def ping(self):
        return self.con.ping()
        
    @property
    def campaigns(self):
        return self.get_campaigns()
    
    def get_campaigns(self):
        return self.cache.get('campaigns', self._get_categories)
    
    @property
    def lists(self):
        return self.get_lists()
    
    def get_lists(self):
        return self.cache.get('lists', self._get_lists)
    
    @property
    def templates(self):
        return self.get_templates()
    
    def get_templates(self):
        return self.cache.get('templates', self._get_templates)
    
    def _get_categories(self):
        return build_dict(self, Campaign, self.con.campaigns()['data'])
    
    def _get_lists(self):
        return build_dict(self, List, self.con.lists())
    
    def _get_templates(self):
        templates = self.con.campaign_templates()
        for t in templates:
            t.update(self.con.template_info(template_id=t['id']))
        return build_dict(self, Template, templates)

    @property
    def folders(self):
        return self.get_folders()

    def get_folders(self):
        return self.cache.get('folders', self._get_folders)

    def _get_folders(self):
        return build_dict(self, Folder, self.con.folders(), key='folder_id')
    
    def get_list_by_id(self, id):
        return self._get_by_id('lists', id)
    
    def get_campaign_by_id(self, id):
        return self._get_by_id('campaigns', id)
            
    def get_template_by_id(self, id):
        return self._get_by_id('templates', id)
    
    def get_template_by_name(self, name):
        return self._get_by_key('templates', 'name', name)

    def get_folder_by_id(self, id):
        return self._get_by_id('folders', id)

    def get_folder_by_name(self, name):
        return self._get_by_key('folders', 'name', name)

    def _get_by_id(self, thing, id):
        try:
            return getattr(self, thing)[id]
        except KeyError:
            self.cache.flush(thing)
            try:
                return getattr(self, thing)[id]
            except KeyError:
                raise self.DOES_NOT_EXIST[thing](id)
            
    def _get_by_key(self, thing, name, key):
        for id, obj in getattr(self, thing).items():
            if getattr(obj, name) == key:
                return obj
        raise self.DOES_NOT_EXIST[thing]('%s=%s' % (name, key))
        
    def create_campaign(self, campaign_type, campaign_list, template, subject,
            from_email, from_name, to_name, folder_id=None,
            tracking=None, title='',
            authenticate=False, analytics=None, auto_footer=False,
            generate_text=False, auto_tweet=False, segment_opts=None,
            type_opts=None):
        """
        Creates a new campaign and returns it for the arguments given.
        """
        tracking = tracking or {'opens':True, 'html_clicks': True}
        type_opts = type_opts or {}
        segment_opts = segment_opts or {}
        analytics = analytics or {}
        options = {}
        if title:
            options['title'] = title
        else:
            options['title'] = subject
        options['list_id'] = campaign_list.id
        options['template_id'] = template.id
        options['subject'] = subject
        options['from_email'] = from_email
        options['from_name'] = from_name
        options['to_name'] = to_name
        if folder_id:
            options['folder_id'] = folder_id
        options['tracking'] = tracking
        options['authenticate'] = bool(authenticate)
        if analytics:
            options['analytics'] = analytics
        options['auto_footer'] = bool(auto_footer)
        options['generate_text'] = bool(generate_text)
        options['auto_tweet'] = bool(auto_tweet)
        content = dict(template)
        kwargs = {}
        if segment_opts.get('conditions', None):
            kwargs['segment_opts'] = segment_opts
        if type_opts:
            kwargs['type_opts'] = type_opts
        cid = self.con.campaign_create(campaign_type, options, content,
            **kwargs)
        camp = self.get_campaign_by_id(cid)
        camp.template_object = template
        return camp
    
    def queue(self, campaign_type, contents, list_id, template_id, subject,
        from_email, from_name, to_name, folder_id=None, tracking_opens=True,
        tracking_html_clicks=True, tracking_text_clicks=False, title=None,
        authenticate=False, google_analytics=None, auto_footer=False,
        auto_tweet=False, segment_options=False, segment_options_all=True,
        segment_options_conditions=None, type_opts=None, obj=None):
        from mailchimp.models import Queue
        segment_options_conditions = segment_options_conditions or []
        type_opts = type_opts or {}
        kwargs = locals().copy()
        del kwargs['Queue']
        del kwargs['self']
        return Queue.objects.queue(**kwargs)

########NEW FILE########
__FILENAME__ = chimpy
import urllib
import urllib2
import pprint
from utils import transform_datetime
from utils import flatten
from warnings import warn
from django.utils import simplejson
_debug = 1


class ChimpyException(Exception):
    pass

class ChimpyWarning(Warning):
    pass


class Connection(object):
    """mailchimp api connection"""

    output = "json"
    version = '1.3'

    def __init__(self, apikey=None, secure=False):
        self._apikey = apikey
        proto = 'http'
        if secure:
            proto = 'https'
        api_host = 'api.mailchimp.com'
        if '-' in apikey:
            key, dc = apikey.split('-')
        else:
            dc = 'us1'
        api_host = dc + '.' + api_host

        self.url = '%s://%s/%s/' % (proto, api_host, self.version)
        self.opener = urllib2.build_opener()
        self.opener.addheaders = [('Content-Type', 'application/x-www-form-urlencoded')]
        
    def _rpc(self, method, **params):
        """make an rpc call to the server"""

        params = urllib.urlencode(params, doseq=True)

        if _debug > 1:
            print __name__, "making request with parameters"
            pprint.pprint(params)
            print __name__, "encoded parameters:", params

        response = self.opener.open("%s?method=%s" %(self.url, method), params)
        data = response.read()
        response.close()

        if _debug > 1:
            print __name__, "rpc call received", data

        result = simplejson.loads(data)

        try:
            if 'error' in result:
                raise ChimpyException("%s:\n%s" % (result['error'], params))
        except TypeError:
            # thrown when results is not iterable (eg bool)
            pass

        return result

    def _api_call(self, method, **params):
        """make an api call"""


        # flatten dict variables
        params = dict([(str(k), v.encode('utf-8') if isinstance(v, unicode) else v) for k,v in flatten(params).items()])
        params['output'] = self.output
        params['apikey'] = self._apikey

        return self._rpc(method=method, **params)

    def ping(self):
        return self._api_call(method='ping')

    def lists(self, limit=25):
        all_lists = []
        start = 0
        has_more = True
        while has_more:
            response = self._api_call(method='lists', start=start, limit=limit)
            all_lists += response['data']
            has_more = int(response['total']) > len(all_lists)
            start += 1
        return all_lists

    def list_batch_subscribe(self,
                             id,
                             batch,
                             double_optin=True,
                             update_existing=False,
                             replace_interests=False):

        return self._api_call(method='listBatchSubscribe',
                              id=id,
                              batch=batch,
                              double_optin=double_optin,
                              update_existing=update_existing,
                              replace_interests=replace_interests)

    def list_batch_unsubscribe(self,
                               id,
                               emails,
                               delete_member=False,
                               send_goodbye=True,
                               send_notify=False):

        return self._api_call(method='listBatchUnsubscribe',
                              id=id,
                              emails=emails,
                              delete_member=delete_member,
                              send_goodbye=send_goodbye,
                              send_notify=send_notify)

    def list_subscribe(self,
                       id,
                       email_address,
                       merge_vars,
                       email_type='text',
                       double_optin=True,
                       update_existing=False,
                       replace_interests=True,
                       send_welcome=False):
        return self._api_call(method='listSubscribe',
                              id=id,
                              email_address=email_address,
                              merge_vars=merge_vars,
                              email_type=email_type,
                              double_optin=double_optin,
                              update_existing=update_existing,
                              replace_interests=replace_interests,
                              send_welcome=send_welcome)

    def list_unsubscribe(self,
                         id,
                         email_address,
                         delete_member=False,
                         send_goodbye=True,
                         send_notify=True):
        return self._api_call(method='listUnsubscribe',
                              id=id,
                              email_address=email_address,
                              delete_member=delete_member,
                              send_goodbye=send_goodbye,
                              send_notify=send_notify)

    def list_update_member(self,
                           id,
                           email_address,
                           merge_vars,
                           email_type='',
                           replace_interests=True):
        return self._api_call(method='listUpdateMember',
                              id=id,
                              email_address=email_address,
                              merge_vars=merge_vars,
                              email_type=email_type,
                              replace_interests=replace_interests)

    def list_member_info(self, id, email_address):
        if isinstance(email_address, basestring):
            first = True
            email_address = [email_address]
        else:
            first = False
        result =  self._api_call(method='listMemberInfo',
                              id=id,
                              email_address=email_address)
        if first:
            return result['data'][0]
        return result

    def list_members(self, id, status='subscribed', since=None, start=0, limit=100):
        return self._api_call(method='listMembers', id=id, status=status, since=since, start=start, limit=limit)

    def list_interest_groupings_add(self, id, name, type, groups):
        """
        Add a new Interest Grouping - if interest groups for the List are not yet
        enabled, adding the first grouping will automatically turn them on.

        http://apidocs.mailchimp.com/api/1.3/listinterestgroupingadd.func.php
        """
        return self._api_call(method='listInterestGroupingAdd', id=id, name=name, type=type, groups=groups)

    def list_interest_groupings_del(self, grouping_id):
        """
        Delete an existing Interest Grouping - this will permanently delete all
        contained interest groups and will remove those selections from all list
        members

        http://apidocs.mailchimp.com/api/1.3/listinterestgroupingdel.func.php
        """
        return self._api_call(method='listInterestGroupingDel', grouping_id=grouping_id)

    def list_interest_groupings(self, id):
        return self._api_call(method='listInterestGroupings', id=id)

    def list_interest_groups(self, id, grouping_id, full=False):
        groupings = self.list_interest_groupings(id)
        grouping = None
        for g in groupings:
            if int(g['id']) == grouping_id:
                grouping = g
                break
        if not grouping:
            return []
        if not full:
            return [group['name'] for group in grouping['groups']]
        return grouping

    def list_interest_group_add(self, id, name, grouping_id):
        return self._api_call(method='listInterestGroupAdd', id=id, group_name=name, grouping_id=grouping_id)

    def list_interest_group_del(self, id, name, grouping_id):
        return self._api_call(method='listInterestGroupDel', id=id, group_name=name, grouping_id=grouping_id)

    def list_interest_group_update(self, id, old_name, new_name, grouping_id):
        return self._api_call(method='listInterestGroupUpdate', id=id, old_name=old_name, new_name=new_name, grouping_id=grouping_id)

    def list_merge_vars(self, id):
        return self._api_call(method='listMergeVars', id=id)

    def list_merge_var_add(self, id, tag, name, req=False):
        tag = tag.upper()
        return self._api_call(method='listMergeVarAdd', id=id, tag=tag, name=name, req=req)

    def list_merge_var_del(self, id, tag):
        return self._api_call(method='listMergeVarDel', id=id, tag=tag)
    
    def list_webhooks(self, id):
        return self._api_call(method='listWebhooks', id=id)
    
    # public static listWebhookAdd(string apikey, string id, string url, array actions, array sources)
    def list_webhook_add(self, id, url, actions, sources):
        return self._api_call(method='listWebhookAdd', id=id, url=url, actions=actions, sources=sources)
    
    def list_webhook_del(self, id, url):
        return self._api_call(method='listWebhookDel', id=id, url=url)

    def campaign_content(self, cid, archive_version=True):
        """Get the content (both html and text) for a campaign, exactly as it would appear in the campaign archive
        http://apidocs.mailchimp.com/api/1.3/campaigncontent.func.php
        """

        return self._api_call(method='campaignContent', cid=cid, for_archive=archive_version)

    def campaign_create(self, campaign_type, options, content, **kwargs):
        """Create a new draft campaign to send.
        http://www.mailchimp.com/api/1.3/campaigncreate.func.php

        Optional parameters: segment_opts, type_opts
        """
        # enforce the 100 char limit (urlencoded!!!)
        title = options.get('title', options['subject'])
        if isinstance(title, unicode):
            title = title.encode('utf-8')
        titlelen = len(urllib.quote_plus(title))
        if titlelen > 99:
            title = title[:-(titlelen - 96)] + '...'
            warn("cropped campaign title to fit the 100 character limit, new title: '%s'" % title, ChimpyWarning)
        subject = options['subject']
        if isinstance(subject, unicode):
            subject = subject.encode('utf-8')
        subjlen = len(urllib.quote_plus(subject))
        if subjlen > 99:
            subject = subject[:-(subjlen - 96)] + '...'
            warn("cropped campaign subject to fit the 100 character limit, new subject: '%s'" % subject, ChimpyWarning)
        options['title'] = title
        options['subject'] = subject
        return self._api_call(method='campaignCreate', type=campaign_type, options=options, content=content, **kwargs)

    def campaign_delete(self, cid):
        """Delete a campaign.
        http://www.mailchimp.com/api/1.3/campaigndelete.func.php
        """

        return self._api_call(method='campaignDelete', cid=cid)

    def campaign_pause(self, cid):
        """Pause a RSS campaign from sending.
        http://apidocs.mailchimp.com/api/1.3/campaignpause.func.php
        """

        return self._api_call(method='campaignPause', cid=cid)

    def campaign_replicate(self, cid):
        """Replicate a campaign.
        http://apidocs.mailchimp.com/api/1.3/campaignreplicate.func.php
        """

        return self._api_call(method='campaignReplicate', cid=cid)

    def campaign_resume(self, cid):
        """Resume sending a RSS campaign.
        http://apidocs.mailchimp.com/api/1.3/campaignresume.func.php
        """

        return self._api_call(method='campaignResume', cid=cid)

    def campaign_schedule(self, cid, schedule_time, schedule_time_b=None):
        """Schedule a campaign to be sent in the future.
        http://apidocs.mailchimp.com/api/1.3/campaignschedule.func.php
        """

        schedule_time = transform_datetime(schedule_time)

        if schedule_time_b:
            schedule_time_b = transform_datetime(schedule_time_b)

        return self._api_call(method='campaignSchedule', cid=cid, schedule_time=schedule_time, schedule_time_b=schedule_time_b)

    def campaign_send_now(self, cid):
        """Send a given campaign immediately.
        http://apidocs.mailchimp.com/api/1.3/campaignsendnow.func.php
        """

        return self._api_call(method='campaignSendNow', cid=cid)

    def campaign_send_test(self, cid, test_emails, **kwargs):
        """Send a test of this campaign to the provided email address.
        Optional parameter: send_type
        http://apidocs.mailchimp.com/api/1.3/campaignsendtest.func.php
        """

        if isinstance(test_emails, basestring):
            test_emails = [test_emails]

        return self._api_call(method='campaignSendTest', cid=cid, test_emails=test_emails, **kwargs)

    def templates(self, user=True, gallery=False, base=False):
        """
        Retrieve various templates available in the system, allowing something
        similar to our template gallery to be created.

        http://apidocs.mailchimp.com/api/1.3/templates.func.php
        """
        return self._api_call(method='templates', user=user, gallery=gallery, base=base)

    def template_info(self, template_id, template_type='user'):
        """
        Pull details for a specific template to help support editing
        http://apidocs.mailchimp.com/api/1.3/templateinfo.func.php
        """
        return self._api_call(method='templateInfo', tid=template_id, type=type)

    def campaign_templates(self):
        return self.templates()['user']

    def campaign_unschedule(self, cid):
        """Unschedule a campaign that is scheduled to be sent in the future  """

        return self._api_call(method='campaignUnschedule', cid=cid)

    def campaign_update(self, cid, name, value):
        """Update just about any setting for a campaign that has not been sent.
        http://apidocs.mailchimp.com/api/1.3/campaignupdate.func.php
        """

        return self._api_call(method='campaignUpdate', cid=cid, name=name, value=value)

    def campaigns(self, filter_id='', filter_folder=None, filter_fromname='', filter_fromemail='',
                  filter_title='', filter_subject='', filter_sendtimestart=None, filter_sendtimeend=None,
                  filter_exact=False, start=0, limit=50):
        """Get the list of campaigns and their details matching the specified filters.
        Timestamps should be passed as datetime objects.

        http://apidocs.mailchimp.com/api/1.3/campaigns.func.php
        """

        filter_sendtimestart = transform_datetime(filter_sendtimestart)
        filter_sendtimeend = transform_datetime(filter_sendtimeend)


        return self._api_call(method='campaigns',
                              filter_id=filter_id, filter_folder=filter_folder, filter_fromname=filter_fromname,
                              filter_fromemail=filter_fromemail, filter_title=filter_title, filter_subject=filter_subject,
                              filter_sendtimestart=filter_sendtimestart, filter_sendtimeend=filter_sendtimeend,
                              filter_exact=filter_exact, start=start, limit=limit)

    def campaign_segment_test(self, list_id, options):
        return self._api_call(method='campaignSegmentTest', list_id=list_id, options=options)

    def folder_add(self, name, folder_type='campaign'):
        """
        Add a new folder to file campaigns or autoresponders in
        http://apidocs.mailchimp.com/api/1.3/folderadd.func.php
        """
        return self._api_call('folderAdd', name=name, type=folder_type)

    def folder_del(self, folder_id, folder_type='campaign'):
        """
        Delete a campaign or autoresponder folder.
        http://apidocs.mailchimp.com/api/1.3/folderdel.func.php
        """
        return self._api_call('folderDel', fid=folder_id, type=folder_type)

    def folder_update(self, folder_id, name, folder_type='campaign'):
        """
        Update the name of a folder for campaigns or autoresponders
        http://apidocs.mailchimp.com/api/1.3/folderupdate.func.php
        """
        return self._api_call('folderUpdate', fid=folder_id, name=name, type=folder_type)

    def folders(self):
        """List all the folders for a user account.
        http://apidocs.mailchimp.com/api/1.3/folders.func.php
        """

        return self._api_call(method='folders')

    # backwars compat for v1.2
    campaign_folders = folders

########NEW FILE########
__FILENAME__ = test_chimpy
"""
Tests for chimpy. Run them with noserunner

You need to activate groups in the Mailchimp web UI before running tests:

 * Browse to http://admin.mailchimp.com
 * List setting -> Groups for segmentation 
 * Check "add groups to my list"

"""

import os
import pprint
import operator
import random
import md5
import datetime

import chimpy

chimp = None


EMAIL_ADDRESS = 'casualbear@googlemail.com'
EMAIL_ADDRESS2 = 'dummy@dummy.com'
LIST_NAME = 'unittests'
LIST_ID = None


def setup_module():
    assert 'MAILCHIMP_APIKEY' in os.environ, \
        "please set the MAILCHIMP_APIKEY environment variable\n" \
        "you can get a new api key by calling:\n" \
        " wget 'http://api.mailchimp.com/1.1/?output=json&method=login" \
        "&password=xxxxxx&username=yyyyyyyy' -O apikey"


    global chimp
    chimp = chimpy.Connection(os.environ['MAILCHIMP_APIKEY'])


def test_ping():
    assert chimp.ping() == "Everything's Chimpy!"


def test_lists():
    lists = chimp.lists()
    pprint.pprint(lists)
    list_names = map(lambda x: x['name'], lists)
    assert LIST_NAME in list_names


def list_id():
    global LIST_ID
    if LIST_ID is None:
        test_list = [x for x in chimp.lists() if x['name'] == LIST_NAME].pop()
        LIST_ID = test_list['id']
    return LIST_ID

# use double_optin=False to prevent manual intervention
def test_list_subscribe_and_unsubscribe():
    result = chimp.list_subscribe(list_id(), EMAIL_ADDRESS,
                                    {'FIRST': 'unit', 'LAST': 'tests'},
                                    double_optin=False)
    pprint.pprint(result)
    assert result == True

    members = chimp.list_members(list_id())['data']
    print members
    emails = map(lambda x: x['email'], members)
    print members
    assert EMAIL_ADDRESS in emails

    result = chimp.list_unsubscribe(list_id(),
                                    EMAIL_ADDRESS,
                                    delete_member=True,
                                    send_goodbye=False,
                                    send_notify=False)
    pprint.pprint(result)
    assert result == True

def test_list_batch_subscribe_and_batch_unsubscribe():
    batch = [{'EMAIL':EMAIL_ADDRESS,'EMAIL_TYPE':'html'},
             {'EMAIL':EMAIL_ADDRESS2,'EMAIL_TYPE':'text'}]

    result = chimp.list_batch_subscribe(list_id(),
                                        batch,
                                        double_optin=False,
                                        update_existing=False,
                                        replace_interests=False)
    assert result['add_count'] == 2

    members = chimp.list_members(list_id())['data']
    emails = map(lambda x: x['email'], members)
    assert EMAIL_ADDRESS in emails
    assert EMAIL_ADDRESS2 in emails

    result = chimp.list_batch_unsubscribe(list_id(),
                                          [EMAIL_ADDRESS,EMAIL_ADDRESS2],
                                          delete_member=True,
                                          send_goodbye=False,
                                          send_notify=False)
    assert result['success_count'] == 2

def test_list_interest_groups_add_and_delete():
    # check no lists exists
#    pprint.pprint(chimp.list_interest_groups(list_id()))
    grouping_id = chimp.list_interest_groupings_add(list_id(), 'test grouping', 'hidden', ['first group'])
    assert len(chimp.list_interest_groups(list_id(), grouping_id)['groups']) == 1

    # add list
    assert chimp.list_interest_group_add(list_id(), 'test', grouping_id)
    assert len(chimp.list_interest_groups(list_id(), grouping_id)['groups']) == 2

    # delete list
    assert chimp.list_interest_group_del(list_id(), 'test', grouping_id)
    assert len(chimp.list_interest_groups(list_id(), grouping_id)['groups']) == 1
    assert (chimp.list_interest_groupings_del(grouping_id))

def test_list_merge_vars_add_and_delete():
    pprint.pprint(chimp.list_merge_vars(list_id()))
    assert len(chimp.list_merge_vars(list_id())) == 3

    # add list
    assert chimp.list_merge_var_add(list_id(), 'test', 'some_text')
    assert len(chimp.list_merge_vars(list_id())) == 4

    # delete list
    assert chimp.list_merge_var_del(list_id(), 'test')
    assert len(chimp.list_merge_vars(list_id())) == 3

def test_list_update_member_and_member_info():
    # set up
    assert chimp.list_subscribe(list_id(), EMAIL_ADDRESS,
                                    {'FIRST': 'unit', 'LAST': 'tests'},
                                    double_optin=False)
    assert chimp.list_merge_var_add(list_id(), 'TEST', 'test_merge_var')
    grouping_id = chimp.list_interest_groupings_add(list_id(), 'tlistg', 'hidden', ['tlist'])


    # update member and get the info back
    assert chimp.list_update_member(list_id(), EMAIL_ADDRESS,
                                    {'TEST': 'abc',
                                    'INTERESTS': 'tlist'}, replace_interests=False)
    info = chimp.list_member_info(list_id(), EMAIL_ADDRESS)
    pprint.pprint(info)

    # tear down
    assert chimp.list_merge_var_del(list_id(), 'TEST')
    assert chimp.list_interest_group_del(list_id(), 'tlist', grouping_id)
    assert chimp.list_interest_groupings_del(grouping_id)
    assert chimp.list_unsubscribe(list_id(), EMAIL_ADDRESS,
                                    delete_member=True,
                                    send_goodbye=False,
                                    send_notify=False)

    # check the info matches the set up
    assert 'TEST' in info['merges']
    assert info['merges']['TEST'] == 'abc'


def test_create_delete_campaign():
    uid = md5.new(str(random.random())).hexdigest()
    subject = 'chimpy campaign test %s' % uid
    options = {'list_id': list_id(),
           'subject': subject,
           'from_email': EMAIL_ADDRESS,
           'from_name': 'chimpy',
           'generate_text': True
           }

    #this just to be sure flatten utility is working
    segment_opts = {'match': 'any', 
            'conditions':[{'field': 'date', 'op': 'gt', 'value': '2000-01-01'},
                          {'field': 'email', 'op': 'like', 'value': '@'}]}

    html = """ <html><body><h1>My test newsletter</h1><p>Just testing</p>
               <a href="*|UNSUB|*">Unsubscribe</a>*|REWARDS|*</body>"""


    content = {'html': html}
    cid = chimp.campaign_create('regular', options, content, segment_opts=segment_opts)
    assert isinstance(cid, basestring)

    # check if the new campaign really is there
    campaigns = chimp.campaigns(filter_subject=subject)
    assert len(campaigns['data'])==1
    assert campaigns['data'][0]['id'] == cid

    # our content properly addd?
    final_content = chimp.campaign_content(cid)
    assert '<h1>My test newsletter</h1>' in final_content['html']
    assert 'My test newsletter' in final_content['text']

    # clean up
    chimp.campaign_delete(cid)

def test_replicate_update_campaign():
    """ replicates and updates a campaign """

    uid = md5.new(str(random.random())).hexdigest()
    subject = 'chimpy campaign test %s' % uid
    options = {'list_id': list_id(),
           'subject': subject,
           'from_email': EMAIL_ADDRESS,
           'from_name': 'chimpy',
           'generate_text': True
           }

    html = """ <html><body><h1>My test newsletter</h1><p>Just testing</p>
               <a href="*|UNSUB|*">Unsubscribe</a>*|REWARDS|*</body>"""


    content = {'html': html}
    cid = chimp.campaign_create('regular', options, content)

    newcid = chimp.campaign_replicate(cid=cid)
    assert isinstance(newcid, basestring)

    newsubject = 'Fresh subject ' + uid
    newtitle = 'Custom title ' + uid

    res = chimp.campaign_update(newcid, 'subject', newsubject)
    assert res is True
    res = chimp.campaign_update(newcid, 'title', newtitle)
    assert res is True

#    campaigns = chimp.campaigns(filter_subject=newsubject)
#    pprint.pprint(campaigns['data'])
#    assert len(campaigns['data'])==1
#    campaigns = chimp.campaigns(filter_title=newtitle)
#    assert len(campaigns['data'])==1

    #clean up
    chimp.campaign_delete(newcid)
    chimp.campaign_delete(cid)

def test_schedule_campaign():
    """ schedules and unschedules a campaign """

    uid = md5.new(str(random.random())).hexdigest()
    subject = 'chimpy campaign schedule test %s' % uid
    options = {'list_id': list_id(),
           'subject': subject,
           'from_email': EMAIL_ADDRESS,
           'from_name': 'chimpy',
           'generate_text': True
           }

    html = """ <html><body><h1>My test newsletter</h1><p>Just testing</p>
               <a href="*|UNSUB|*">Unsubscribe</a>*|REWARDS|*</body>"""


    content = {'html': html}
    cid = chimp.campaign_create('regular', options, content)

    schedule_time = datetime.datetime(2012, 12, 20, 19, 0, 0)
    chimp.campaign_schedule(cid, schedule_time)

    campaign = chimp.campaigns(filter_subject=subject)['data'][0]
    assert campaign['status'] == 'schedule'
    assert campaign['send_time'] in ('Dec 20, 2012 07:00 pm', '2012-12-20 19:00:00')

    chimp.campaign_unschedule(cid)
    campaign = chimp.campaigns(filter_subject=subject)['data'][0]
    assert campaign['status'] == 'save'

    #clean up
    chimp.campaign_delete(cid)

def test_rss_campaign():
    """ add, pause, resume rss campaign """

    uid = md5.new(str(random.random())).hexdigest()
    subject = 'chimpy campaign rss test %s' % uid
    options = {'list_id': list_id(),
           'subject': subject,
           'from_email': EMAIL_ADDRESS,
           'from_name': 'chimpy',
           'generate_text': True
           }

    html = """ <html><body><h1>My test RSS newsletter</h1><p>Just testing</p>
               <a href="*|UNSUB|*">Unsubscribe</a>*|REWARDS|*</body>"""


    content = {'html': html}
    type_opts = {'url': 'http://mailchimp.com/blog/rss'}

    cid = chimp.campaign_create('rss', options, content, type_opts=type_opts)
    campaign = chimp.campaigns(filter_subject=subject)['data'][0]
    assert campaign['type'] == 'rss'

    # Todo: Could not find a way to activate the RSS from the API. You need to
    # activate before being able to test pause and resume. send_now and schedule
    # didn't do the trick.

    #chimp.campaign_pause(cid)
    #chimp.campaign_resume(cid)

    #clean up
    chimp.campaign_delete(cid)

if __name__ == '__main__':
    setup_module()
    for f in globals().keys():
        if f.startswith('test_') and callable(globals()[f]):
            print f
            globals()[f]()

########NEW FILE########
__FILENAME__ = utils
from datetime import datetime

def transform_datetime(dt):
    """ converts datetime parameter"""                               

    if dt is None:
        dt = ''
    else:
        assert isinstance(dt, datetime)
        dt = dt.strftime('%Y-%m-%d %H:%M:%S')
 
    return dt


def flatten(params, key=None):
    """ flatten nested dictionaries and lists """
    flat = {}
    for name, val in params.items():
        if key is not None and not isinstance(key, int):
            name = "%s[%s]" % (key, name)
        if isinstance(val, dict):
            flat.update(flatten(val, name))
        elif isinstance(val, list):
            flat.update(flatten(dict(enumerate(val)), name))
        elif val is not None:
            flat[name] = val
    return flat


########NEW FILE########
__FILENAME__ = constants
STATUS_OK = "Everything's Chimpy!"
REGULAR_CAMPAIGN = 'regular'
PLAINTEXT_CAMPAIGN = 'plaintext'
ABSPLIT_CAMPAIGN = 'absplit'
RSS_CAMPAIGN = 'rss'
TRANS_CAMPAIGN = 'trans'
AUTO_CAMPAIGN = 'auto'

########NEW FILE########
__FILENAME__ = cron
"""
Example cronjob:

from cronjobs.base import Cron
from cronjobs.constants import MINUTES
from mailchimp.utils import dequeue

class DequeueCron(Cron):
    run_every = 1
    interval_unit = MINUTES
 
    def job(self):
        try:
            dequeue()
            return True
        except:
            return False
"""
########NEW FILE########
__FILENAME__ = exceptions
class ChimpException(Exception): pass

class MCCampaignDoesNotExist(ChimpException): pass
class MCListDoesNotExist(ChimpException): pass
class MCConnectionFailed(ChimpException): pass
class MCTemplateDoesNotExist(ChimpException): pass
class MCFolderDoesNotExist(ChimpException): pass

class MailchimpWarning(Warning): pass
########NEW FILE########
__FILENAME__ = mcdequeue
from django.core.management import BaseCommand
from mailchimp.utils import dequeue
from optparse import make_option


class Command(BaseCommand):
    
    def handle(self, *args, **options):
        if len(args) and args[0].isdigit():
            limit = int(args[0])
        else:
            limit = None
        print 'Dequeueing Campaigns'
        done = False
        for camp in dequeue(limit):
            done = True
            if camp:
                print '- Dequeued campaign %s (%s)' % (camp.name, camp.campaign_id)
            else:
                print 'ERROR'
        if not done:
            print 'Nothing to dequeue'
        print 'Done'
########NEW FILE########
__FILENAME__ = mcmakemerge
from django.core.management import BaseCommand
from django.contrib.sites.models import Site
from mailchimp.utils import get_connection


class Command(BaseCommand):
    def handle(self, *args, **options):
        if len(args) != 1:
            print 'You have to specify exactly one argument to this command'
            return
        merge = args[0]
        print 'Adding the merge var `%s` to all lists' % merge
        c = get_connection()
        for list in c.lists.values():
            print 'Checking list %s' % list.name
            list.add_merges_if_not_exists(merge)
            print '  ok'
        print 'Done'
########NEW FILE########
__FILENAME__ = mcsitegroups
from django.core.management import BaseCommand
from django.contrib.sites.models import Site
from mailchimp.utils import get_connection


class Command(BaseCommand):
    def handle(self, *args, **options):
        print 'Installing site segment groups for all lists and all sites'
        c = get_connection()
        interests = []
        for site in Site.objects.all():
            interests.append(site.domain)
        for list in c.lists.values():
            print 'Checking list %s' % list.name
            list.add_interests_if_not_exist(*interests)
            print '  ok'
        print 'Done'
########NEW FILE########
__FILENAME__ = mcwebhooks
from django.core.management import BaseCommand
from mailchimp.utils import get_connection


class Command(BaseCommand):
    def handle(self, *args, **options):
        print 'Installing webhooks for all lists'
        c = get_connection()
        for list in c.lists.values():
            print 'Checking list %s' % list.name
            # def add_webhook_if_not_exists(self, url, actions, sources):
            if list.install_webhook():
                print '  ok'
            else:
                print '  ERROR!'
        print 'Done'
########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding model 'Campaign'
        db.create_table('mailchimp_campaign', (
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('sent_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('campaign_id', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('mailchimp', ['Campaign'])

        # Adding model 'Reciever'
        db.create_table('mailchimp_reciever', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('campaign', self.gf('django.db.models.fields.related.ForeignKey')(related_name='recievers', to=orm['mailchimp.Campaign'])),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
        ))
        db.send_create_signal('mailchimp', ['Reciever'])
    
    
    def backwards(self, orm):
        
        # Deleting model 'Campaign'
        db.delete_table('mailchimp_campaign')

        # Deleting model 'Reciever'
        db.delete_table('mailchimp_reciever')
    
    
    models = {
        'mailchimp.campaign': {
            'Meta': {'object_name': 'Campaign'},
            'campaign_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'sent_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'mailchimp.reciever': {
            'Meta': {'object_name': 'Reciever'},
            'campaign': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'recievers'", 'to': "orm['mailchimp.Campaign']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }
    
    complete_apps = ['mailchimp']

########NEW FILE########
__FILENAME__ = 0002_added_queue
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding model 'Queue'
        db.create_table('mailchimp_queue', (
            ('type_opts', self.gf('django.db.models.fields.TextField')()),
            ('segment_options_all', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contents', self.gf('django.db.models.fields.TextField')()),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('campaign_type', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('authenticate', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('from_email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('segment_options', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('list_id', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('auto_tweet', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('from_name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('folder_id', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('generate_text', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('to_email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('tracking_text_clicks', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('auto_footer', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('tracking_html_clicks', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('google_analytics', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('segment_options_conditions', self.gf('django.db.models.fields.TextField')()),
            ('template_id', self.gf('django.db.models.fields.IntegerField')()),
            ('tracking_opens', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
        ))
        db.send_create_signal('mailchimp', ['Queue'])
    
    
    def backwards(self, orm):
        
        # Deleting model 'Queue'
        db.delete_table('mailchimp_queue')
    
    
    models = {
        'mailchimp.campaign': {
            'Meta': {'object_name': 'Campaign'},
            'campaign_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'sent_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'mailchimp.queue': {
            'Meta': {'object_name': 'Queue'},
            'authenticate': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'auto_footer': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'auto_tweet': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'campaign_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'contents': ('django.db.models.fields.TextField', [], {}),
            'folder_id': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'from_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'generate_text': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'google_analytics': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'list_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'segment_options': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'segment_options_all': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'segment_options_conditions': ('django.db.models.fields.TextField', [], {}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'template_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'tracking_html_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'tracking_opens': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'tracking_text_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'type_opts': ('django.db.models.fields.TextField', [], {})
        },
        'mailchimp.reciever': {
            'Meta': {'object_name': 'Reciever'},
            'campaign': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'recievers'", 'to': "orm['mailchimp.Campaign']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }
    
    complete_apps = ['mailchimp']

########NEW FILE########
__FILENAME__ = 0003_fixed_template_id
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Changing field 'Queue.template_id'
        db.alter_column('mailchimp_queue', 'template_id', self.gf('django.db.models.fields.PositiveIntegerField')())
    
    
    def backwards(self, orm):
        
        # Changing field 'Queue.template_id'
        db.alter_column('mailchimp_queue', 'template_id', self.gf('django.db.models.fields.IntegerField')())
    
    
    models = {
        'mailchimp.campaign': {
            'Meta': {'object_name': 'Campaign'},
            'campaign_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'sent_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'mailchimp.queue': {
            'Meta': {'object_name': 'Queue'},
            'authenticate': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'auto_footer': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'auto_tweet': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'campaign_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'contents': ('django.db.models.fields.TextField', [], {}),
            'folder_id': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'from_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'generate_text': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'google_analytics': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'list_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'segment_options': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'segment_options_all': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'segment_options_conditions': ('django.db.models.fields.TextField', [], {}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'template_id': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'tracking_html_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'tracking_opens': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'tracking_text_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'type_opts': ('django.db.models.fields.TextField', [], {})
        },
        'mailchimp.reciever': {
            'Meta': {'object_name': 'Reciever'},
            'campaign': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'recievers'", 'to': "orm['mailchimp.Campaign']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }
    
    complete_apps = ['mailchimp']

########NEW FILE########
__FILENAME__ = 0004_fixed_template_id_max
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        pass

    def backwards(self, orm):
        pass

    models = {
        'mailchimp.campaign': {
            'Meta': {'object_name': 'Campaign'},
            'campaign_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'sent_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'mailchimp.queue': {
            'Meta': {'object_name': 'Queue'},
            'authenticate': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'auto_footer': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'auto_tweet': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'campaign_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'contents': ('django.db.models.fields.TextField', [], {}),
            'folder_id': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'from_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'generate_text': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'google_analytics': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'list_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'segment_options': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'segment_options_all': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'segment_options_conditions': ('django.db.models.fields.TextField', [], {}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'template_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'tracking_html_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'tracking_opens': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'tracking_text_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'type_opts': ('django.db.models.fields.TextField', [], {})
        },
        'mailchimp.reciever': {
            'Meta': {'object_name': 'Reciever'},
            'campaign': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'recievers'", 'to': "orm['mailchimp.Campaign']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }
    
    complete_apps = ['mailchimp']

########NEW FILE########
__FILENAME__ = 0005_added_link_to_object
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding field 'Campaign.object_id'
        db.add_column('mailchimp_campaign', 'object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True))

        # Adding field 'Campaign.content_type'
        db.add_column('mailchimp_campaign', 'content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True, blank=True))

        # Adding field 'Queue.object_id'
        db.add_column('mailchimp_queue', 'object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True))

        # Adding field 'Queue.content_type'
        db.add_column('mailchimp_queue', 'content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True, blank=True))
    
    
    def backwards(self, orm):
        
        # Deleting field 'Campaign.object_id'
        db.delete_column('mailchimp_campaign', 'object_id')

        # Deleting field 'Campaign.content_type'
        db.delete_column('mailchimp_campaign', 'content_type_id')

        # Deleting field 'Queue.object_id'
        db.delete_column('mailchimp_queue', 'object_id')

        # Deleting field 'Queue.content_type'
        db.delete_column('mailchimp_queue', 'content_type_id')
    
    
    models = {
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'mailchimp.campaign': {
            'Meta': {'object_name': 'Campaign'},
            'campaign_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sent_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'mailchimp.queue': {
            'Meta': {'object_name': 'Queue'},
            'authenticate': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'auto_footer': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'auto_tweet': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'campaign_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'contents': ('django.db.models.fields.TextField', [], {}),
            'folder_id': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'from_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'generate_text': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'google_analytics': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'list_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'segment_options': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'segment_options_all': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'segment_options_conditions': ('django.db.models.fields.TextField', [], {}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'template_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'tracking_html_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'tracking_opens': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'tracking_text_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'type_opts': ('django.db.models.fields.TextField', [], {})
        },
        'mailchimp.reciever': {
            'Meta': {'object_name': 'Reciever'},
            'campaign': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'recievers'", 'to': "orm['mailchimp.Campaign']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }
    
    complete_apps = ['mailchimp']

########NEW FILE########
__FILENAME__ = 0006_added_locks
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding field 'Queue.locked'
        db.add_column('mailchimp_queue', 'locked', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True))
    
    
    def backwards(self, orm):
        
        # Deleting field 'Queue.locked'
        db.delete_column('mailchimp_queue', 'locked')
    
    
    models = {
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'mailchimp.campaign': {
            'Meta': {'object_name': 'Campaign'},
            'campaign_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sent_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'mailchimp.queue': {
            'Meta': {'object_name': 'Queue'},
            'authenticate': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'auto_footer': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'auto_tweet': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'campaign_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'contents': ('django.db.models.fields.TextField', [], {}),
            'folder_id': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'from_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'generate_text': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'google_analytics': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'list_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'locked': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'segment_options': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'segment_options_all': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'segment_options_conditions': ('django.db.models.fields.TextField', [], {}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'template_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'tracking_html_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'tracking_opens': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'tracking_text_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'type_opts': ('django.db.models.fields.TextField', [], {})
        },
        'mailchimp.reciever': {
            'Meta': {'object_name': 'Reciever'},
            'campaign': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'recievers'", 'to': "orm['mailchimp.Campaign']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }
    
    complete_apps = ['mailchimp']

########NEW FILE########
__FILENAME__ = 0007_extra_info
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding field 'Campaign.extra_info'
        db.add_column('mailchimp_campaign', 'extra_info', self.gf('django.db.models.fields.TextField')(null=True))

        # Adding field 'Queue.extra_info'
        db.add_column('mailchimp_queue', 'extra_info', self.gf('django.db.models.fields.TextField')(null=True))
    
    
    def backwards(self, orm):
        
        # Deleting field 'Campaign.extra_info'
        db.delete_column('mailchimp_campaign', 'extra_info')

        # Deleting field 'Queue.extra_info'
        db.delete_column('mailchimp_queue', 'extra_info')
    
    
    models = {
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'mailchimp.campaign': {
            'Meta': {'object_name': 'Campaign'},
            'campaign_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'extra_info': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sent_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'mailchimp.queue': {
            'Meta': {'object_name': 'Queue'},
            'authenticate': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'auto_footer': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'auto_tweet': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'campaign_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'contents': ('django.db.models.fields.TextField', [], {}),
            'extra_info': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'folder_id': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'from_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'generate_text': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'google_analytics': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'list_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'locked': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'segment_options': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'segment_options_all': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'segment_options_conditions': ('django.db.models.fields.TextField', [], {}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'template_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'tracking_html_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'tracking_opens': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'tracking_text_clicks': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'type_opts': ('django.db.models.fields.TextField', [], {})
        },
        'mailchimp.reciever': {
            'Meta': {'object_name': 'Reciever'},
            'campaign': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'recievers'", 'to': "orm['mailchimp.Campaign']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }
    
    complete_apps = ['mailchimp']

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils import simplejson
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from mailchimp.utils import get_connection


class QueueManager(models.Manager):
    def queue(self, campaign_type, contents, list_id, template_id, subject,
        from_email, from_name, to_email, folder_id=None, tracking_opens=True,
        tracking_html_clicks=True, tracking_text_clicks=False, title=None,
        authenticate=False, google_analytics=None, auto_footer=False,
        auto_tweet=False, segment_options=False, segment_options_all=True,
        segment_options_conditions=[], type_opts={}, obj=None, extra_info=[]):
        """
        Queue a campaign
        """
        kwargs = locals().copy()
        kwargs['segment_options_conditions'] = simplejson.dumps(segment_options_conditions)
        kwargs['type_opts'] = simplejson.dumps(type_opts)
        kwargs['contents'] = simplejson.dumps(contents)
        kwargs['extra_info'] = simplejson.dumps(extra_info)
        for thing in ('template_id', 'list_id'):
            thingy = kwargs[thing]
            if hasattr(thingy, 'id'):
                kwargs[thing] = thingy.id
        del kwargs['self']
        del kwargs['obj']
        if obj:
            kwargs['object_id'] = obj.pk
            kwargs['content_type'] = ContentType.objects.get_for_model(obj)
        return self.create(**kwargs)
    
    def dequeue(self, limit=None):
        if limit:
            qs = self.filter(locked=False)[:limit]
        else:
            qs = self.filter(locked=False)
        for obj in qs:
             yield obj.send()
    
    def get_or_404(self, *args, **kwargs):
        return get_object_or_404(self.model, *args, **kwargs)



class Queue(models.Model):
    """
    A FIFO queue for async sending of campaigns
    """
    campaign_type = models.CharField(max_length=50)
    contents = models.TextField()
    list_id = models.CharField(max_length=50)
    template_id = models.PositiveIntegerField()
    subject = models.CharField(max_length=255)
    from_email = models.EmailField()
    from_name = models.CharField(max_length=255)
    to_email = models.EmailField()
    folder_id = models.CharField(max_length=50, null=True, blank=True)
    tracking_opens = models.BooleanField(default=True)
    tracking_html_clicks = models.BooleanField(default=True)
    tracking_text_clicks = models.BooleanField(default=False)
    title = models.CharField(max_length=255, null=True, blank=True)
    authenticate = models.BooleanField(default=False)
    google_analytics = models.CharField(max_length=100, blank=True, null=True)
    auto_footer = models.BooleanField(default=False)
    generate_text = models.BooleanField(default=False)
    auto_tweet = models.BooleanField(default=False)
    segment_options = models.BooleanField(default=False)
    segment_options_all = models.BooleanField()
    segment_options_conditions = models.TextField()
    type_opts = models.TextField()
    content_type = models.ForeignKey(ContentType, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    extra_info = models.TextField(null=True)
    locked = models.BooleanField(default=False)
    
    objects = QueueManager()
    
    def send(self):
        """
        send (schedule) this queued object
        """
        # check lock
        if self.locked:
            return False
        # aquire lock
        self.locked = True
        self.save()
        # get connection and send the mails 
        c = get_connection()
        tpl = c.get_template_by_id(self.template_id)
        content_data = dict([(str(k), v) for k,v in simplejson.loads(self.contents).items()])
        built_template = tpl.build(**content_data)
        tracking = {'opens': self.tracking_opens, 
                    'html_clicks': self.tracking_html_clicks,
                    'text_clicks': self.tracking_text_clicks}
        if self.google_analytics:
            analytics = {'google': self.google_analytics}
        else:
            analytics = {}
        segment_opts = {'match': 'all' if self.segment_options_all else 'any',
            'conditions': simplejson.loads(self.segment_options_conditions)}
        type_opts = simplejson.loads(self.type_opts)
        title = self.title or self.subject
        camp = c.create_campaign(self.campaign_type, c.get_list_by_id(self.list_id),
            built_template, self.subject, self.from_email, self.from_name,
            self.to_email, self.folder_id, tracking, title, self.authenticate,
            analytics, self.auto_footer, self.generate_text, self.auto_tweet,
            segment_opts, type_opts)
        if camp.send_now_async():
            self.delete()
            kwargs = {}
            if self.content_type and self.object_id:
                kwargs['content_type'] = self.content_type
                kwargs['object_id'] = self.object_id
            if self.extra_info:
                kwargs['extra_info'] = simplejson.loads(self.extra_info)
            return Campaign.objects.create(camp.id, segment_opts, **kwargs)
        # release lock if failed
        self.locked = False
        self.save()
        return False
    
    def get_dequeue_url(self):
        return reverse('mailchimp_dequeue', kwargs={'id': self.id})
    
    def get_cancel_url(self):
        return reverse('mailchimp_cancel', kwargs={'id': self.id})
    
    def get_list(self):
        return get_connection().lists[self.list_id]
    
    @property
    def object(self):
        """
        The object might have vanished until now, so triple check that it's there!
        """
        if self.object_id:
            model = self.content_type.model_class()
            try:
                return model.objects.get(id=self.object_id)
            except model.DoesNotExist:
                return None
        return None
    
    def get_object_admin_url(self):
        if not self.object:
            return ''
        name = 'admin:%s_%s_change' % (self.object._meta.app_label,
            self.object._meta.module_name)
        return reverse(name, args=(self.object.pk,))
    
    def can_dequeue(self, user):
        if user.is_superuser:
            return True
        if not user.is_staff:
            return False
        if callable(getattr(self.object, 'mailchimp_can_dequeue', None)):
            return self.object.mailchimp_can_dequeue(user)
        return user.has_perm('mailchimp.can_send') and user.has_perm('mailchimp.can_dequeue') 
    

class CampaignManager(models.Manager):
    def create(self, campaign_id, segment_opts, content_type=None, object_id=None,
            extra_info=[]):
        con = get_connection()
        camp = con.get_campaign_by_id(campaign_id)
        extra_info = simplejson.dumps(extra_info)
        obj = self.model(content=camp.content, campaign_id=campaign_id,
             name=camp.title, content_type=content_type, object_id=object_id,
             extra_info=extra_info)
        obj.save()
        segment_opts = dict([(str(k), v) for k,v in segment_opts.items()])
        for email in camp.list.filter_members(segment_opts):
            Reciever.objects.create(campaign=obj, email=email)
        return obj
    
    def get_or_404(self, *args, **kwargs):
        return get_object_or_404(self.model, *args, **kwargs)
    
    
class DeletedCampaign(object):
    subject = u'<deleted from mailchimp>'


class Campaign(models.Model):
    sent_date = models.DateTimeField(auto_now_add=True)
    campaign_id = models.CharField(max_length=50)
    content = models.TextField()
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey(ContentType, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    extra_info = models.TextField(null=True)
    
    objects = CampaignManager()
    
    class Meta:
        ordering = ['-sent_date']
        permissions = [('can_view', 'Can view Mailchimp information'),
                       ('can_send', 'Can send Mailchimp newsletters')]
        verbose_name = _('Mailchimp Log')
        verbose_name_plural = _('Mailchimp Logs')
        
    def get_absolute_url(self):
        return reverse('mailchimp_campaign_info', kwargs={'campaign_id': self.campaign_id})
    
    def get_object_admin_url(self):
        if not self.object:
            return ''
        name = 'admin:%s_%s_change' % (self.object._meta.app_label,
            self.object._meta.module_name)
        return reverse(name, args=(self.object.pk,))
    
    def get_extra_info(self):
        if self.extra_info:
            return simplejson.loads(self.extra_info)
        return []
    
    @property
    def object(self):
        """
        The object might have vanished until now, so triple check that it's there!
        """
        if self.object_id:
            model = self.content_type.model_class()
            try:
                return model.objects.get(id=self.object_id)
            except model.DoesNotExist:
                return None
        return None
    
    @property
    def mc(self):
        try:
            if not hasattr(self, '_mc'):
                self._mc = get_connection().get_campaign_by_id(self.campaign_id)
            return self._mc
        except:
            return DeletedCampaign()


class Reciever(models.Model):
    campaign = models.ForeignKey(Campaign, related_name='recievers')
    email = models.EmailField()
########NEW FILE########
__FILENAME__ = settings
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from mailchimp.exceptions import MailchimpWarning
import warnings

API_KEY = getattr(settings, 'MAILCHIMP_API_KEY', None)
if API_KEY is None:
    raise ImproperlyConfigured('django-mailchimp requires the MAILCHIMP_API_KEY setting')

SECURE = getattr(settings, 'MAILCHIMP_SECURE', True)

# THIS DOES NOT WORK:
#REAL_CACHE = bool(getattr(settings, 'MAILCHIMP_USE_REAL_CACHE', False))
"""
In [1]: from mailchimp.utils import get_connection

In [2]: c = get_connection ()

In [3]: c.campaigns
key lists <type 'str'>
value {'f48ceea763': <List object: Affichage List>, 'a41f00cba2': <List object: API Test List>} <type 'dict'>
key lists <type 'str'>
value {'f48ceea763': <List object: Affichage List>, 'a41f00cba2': <List object: API Test List>} <type 'dict'>
---------------------------------------------------------------------------
TypeError                                 Traceback (most recent call last)

/home/jonas/workspace/affichage/<ipython console> in <module>()

/home/jonas/workspace/django-mailchimp/mailchimp/chimp.pyc in campaigns(self)
    354     @property
    355     def campaigns(self):
--> 356         return self.get_campaigns()
    357 
    358     def get_campaigns(self):

/home/jonas/workspace/django-mailchimp/mailchimp/chimp.pyc in get_campaigns(self)
    357 
    358     def get_campaigns(self):
--> 359         return self.cache.get('campaigns', self._get_categories)
    360 
    361     @property

/home/jonas/workspace/django-mailchimp/mailchimp/utils.py in get(self, key, obj, *args, **kwargs)
     37         value = self._get(key)
     38         if value is None:
---> 39             value = obj(*args, **kwargs) if callable(obj) else obj
     40             self._set(key, value)
     41         return value

/home/jonas/workspace/django-mailchimp/mailchimp/chimp.pyc in _get_categories(self)
    374 
    375     def _get_categories(self):
--> 376         return build_dict(self, Campaign, self.con.campaigns())
    377 
    378     def _get_lists(self):

/home/jonas/workspace/django-mailchimp/mailchimp/utils.py in build_dict(master, klass, data, key)
     87 
     88 def build_dict(master, klass, data, key='id'):
---> 89     return  dict([(info[key], klass(master, info)) for info in data])
     90 
     91 def _convert(name):

/home/jonas/workspace/django-mailchimp/mailchimp/chimp.pyc in __init__(self, master, info)
     92     def __init__(self, master, info):
     93         super(Campaign, self).__init__(master, info)
---> 94         self.list = self.master.get_list_by_id(self.list_id)
     95         self._content = None
     96         self.frozen_info = info

/home/jonas/workspace/django-mailchimp/mailchimp/chimp.pyc in get_list_by_id(self, id)
    383 
    384     def get_list_by_id(self, id):
--> 385         return self._get_by_id('lists', id)
    386 
    387     def get_campaign_by_id(self, id):

/home/jonas/workspace/django-mailchimp/mailchimp/chimp.pyc in _get_by_id(self, thing, id)
    396     def _get_by_id(self, thing, id):
    397         try:
--> 398             return getattr(self, thing)[id]
    399         except KeyError:
    400             self.cache.flush(thing)

/home/jonas/workspace/django-mailchimp/mailchimp/chimp.pyc in lists(self)
    361     @property
    362     def lists(self):
--> 363         return self.get_lists()
    364 
    365     def get_lists(self):

/home/jonas/workspace/django-mailchimp/mailchimp/chimp.pyc in get_lists(self)
    364 
    365     def get_lists(self):
--> 366         return self.cache.get('lists', self._get_lists)
    367 
    368     @property

/home/jonas/workspace/django-mailchimp/mailchimp/utils.py in get(self, key, obj, *args, **kwargs)
     38         if value is None:
     39             value = obj(*args, **kwargs) if callable(obj) else obj
---> 40             self._set(key, value)
     41         return value
     42 

/home/jonas/workspace/django-mailchimp/mailchimp/utils.py in _real_set(self, key, value)
     44         print 'key', key, type(key)
     45         print 'value', value, type(value)
---> 46         cache.set(key, value, CACHE_TIMEOUT)
     47 
     48     def _real_get(self, key):

/home/jonas/workspace/affichage/parts/django/django/core/cache/backends/locmem.pyc in set(self, key, value, timeout)
     81         try:
     82             try:
---> 83                 self._set(key, pickle.dumps(value), timeout)
     84             except pickle.PickleError:
     85                 pass

/usr/lib/python2.6/copy_reg.pyc in _reduce_ex(self, proto)
     68     else:
     69         if base is self.__class__:
---> 70             raise TypeError, "can't pickle %s objects" % base.__name__
     71         state = base(self)
     72     args = (self.__class__, base, state)

TypeError: can't pickle instancemethod objects

"""
REAL_CACHE = False
CACHE_TIMEOUT = getattr(settings, 'MAILCHIMP_CACHE_TIMEOUT', 300)

WEBHOOK_KEY = getattr(settings, 'MAILCHIMP_WEBHOOK_KEY', '')
if not WEBHOOK_KEY:
    warnings.warn("you did not define a MAILCHIMP_WEBHOOK_KEY setting. "
        "django-mailchimp will create a random one by itself", MailchimpWarning)
    import string
    import random
    alphanum = string.ascii_letters + string.digits
    for x in range(50):
        WEBHOOK_KEY += random.choice(alphanum)

VIEWS_OVERVIEW = getattr(settings, 'MAILCHIMP_VIEWS_OVERVIEW', 'mailchimp.views.overview')
VIEWS_INFO = getattr(settings, 'MAILCHIMP_VIEWS_INFO', 'mailchimp.views.campaign_information')
VIEWS_SCHEDULE_OBJECT = getattr(settings, 'MAILCHIMP_VIEWS_SEND_OBJECT', 'mailchimp.views.schedule_campaign_for_object')
VIEWS_TEST_OBJECT = getattr(settings, 'MAILCHIMP_VIEWS_TEST_OBJECT', 'mailchimp.views.test_campaign_for_object')
########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

args = ["list", "fired_at", "email", "interests", "fname", "lname", "merges"]

mc_subscribe = Signal(providing_args=args)
mc_unsubscribe = Signal(providing_args=args)
mc_profile = Signal(providing_args=args)
mc_upemail = Signal(providing_args=["list", "old_email", "new_email", "fired_at"])
mc_cleaned = Signal(providing_args=["fired_at", "list", "reason", "email"])
mc_campaign = Signal(providing_args=["fired_at", "list", "campaign_id", "reason", "status", "subject"])


def get_signal(name):
    return globals()['mc_%s' % name]
########NEW FILE########
__FILENAME__ = mailchimp_admin_tags
from django import template

register = template.Library()

@register.filter
def can_dequeue(user, obj):
    return obj.can_dequeue(user)
########NEW FILE########
__FILENAME__ = mailchimp_tags
from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from mailchimp.utils import is_queued_or_sent

register = template.Library()


def mailchimp_send_for_object(context, object):
    is_sent = is_queued_or_sent(object)
    sent_date = None
    campaign_id = None
    if is_sent and hasattr(is_sent, 'sent_date'):
        sent_date = is_sent.sent_date
        campaign_id = is_sent.campaign_id
    if hasattr(object, 'mailchimp_allow_send'):
        objchck = object.mailchimp_allow_send
    else:
        objchck = lambda r: True
    request = context['request']
    return {
        'content_type': ContentType.objects.get_for_model(object).pk,
        'primary_key': object.pk,
        'allow': request.user.has_perm('mailchimp.can_send') and objchck(request),
        'is_sent': is_sent,
        'sent_date': sent_date,
        'campaign_id': campaign_id,
        'can_view': sent_date and request.user.has_perm('mailchimp.can_view'),
        'admin_prefix': settings.ADMIN_MEDIA_PREFIX,
        'can_test': bool(request.user.email),
    }
register.inclusion_tag('mailchimp/send_button.html', takes_context=True)(mailchimp_send_for_object)
########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import *
except ImportError:  # django < 1.4
    from django.conf.urls.defaults import *

from mailchimp.settings import VIEWS_INFO, VIEWS_OVERVIEW, VIEWS_SCHEDULE_OBJECT, VIEWS_TEST_OBJECT
from mailchimp.views import webhook, dequeue, cancel, test_real

urlpatterns = patterns('',
    url(r'^$', VIEWS_OVERVIEW, name='mailchimp_overview', kwargs={'page':'1'}),
    url(r'^(?P<page>\d+)/$', VIEWS_OVERVIEW, name='mailchimp_overview'),
    url(r'^send/(?P<content_type>\d+)/(?P<pk>\d+)/$', VIEWS_SCHEDULE_OBJECT, name='mailchimp_schedule_for_object'),
    url(r'^test/(?P<content_type>\d+)/(?P<pk>\d+)/$', VIEWS_TEST_OBJECT, name='mailchimp_test_for_object'),
    url(r'^test/(?P<content_type>\d+)/(?P<pk>\d+)/real/$', test_real, name='mailchimp_real_test_for_object'),
    url(r'^info/(?P<campaign_id>\w+)/$', VIEWS_INFO, name='mailchimp_campaign_info'),
    url(r'^dequeue/(?P<id>\d+)/', dequeue, name='mailchimp_dequeue'),
    url(r'^cancel/(?P<id>\d+)/', cancel, name='mailchimp_cancel'),
    url(r'^webhook/(?P<key>\w+)/', webhook, name='mailchimp_webhook'),
)

########NEW FILE########
__FILENAME__ = utils
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib import messages 
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.contrib.contenttypes.models import ContentType
from django.utils import simplejson
from django.contrib.auth import logout
from django.contrib.messages import debug, info, success, warning, error, add_message
from django.http import (
    HttpResponse, HttpResponseForbidden, Http404, HttpResponseNotAllowed,
    HttpResponseRedirect, HttpResponsePermanentRedirect, HttpResponseNotModified,
    HttpResponseBadRequest, HttpResponseNotFound, HttpResponseGone,
    HttpResponseServerError
)
from mailchimp.settings import API_KEY, SECURE, REAL_CACHE, CACHE_TIMEOUT
import re
import warnings

class KeywordArguments(dict):
    def __getattr__(self, attr):
        return self[attr]


class Cache(object):
    def __init__(self, prefix=''):
        self._data = {}
        self._clear_lock = False
        self._prefix = prefix
        if REAL_CACHE:
            self._set = getattr(self, '_real_set')
            self._get = getattr(self, '_real_get')
            self._del = getattr(self, '_real_del')
        else:
            self._set = getattr(self, '_fake_set')
            self._get = getattr(self, '_fake_get')
            self._del = getattr(self, '_fake_del')
            

    def get(self, key, obj, *args, **kwargs):
        if self._clear_lock:
            self.flush(key)
            self._clear_lock = False
        value = self._get(key)
        if value is None:
            value = obj(*args, **kwargs) if callable(obj) else obj          
            self._set(key, value)
        return value
    
    def _real_set(self, key, value):
        cache.set(key, value, CACHE_TIMEOUT)
    
    def _real_get(self, key):
        return cache.get(key, None)
    
    def _real_del(self, key):
        cache.delete(key)
    
    def _fake_set(self, key, value):
        self._data[key] = value
    
    def _fake_get(self, key):
        return self._data.get(key, None)
    
    def _fake_del(self, key):
        if key in self._data:
            del self._data[key]
    
    def get_child_cache(self, key):
        return Cache('%s_%s_' % (self._prefix, key))
    
    def flush(self, *keys):
        for key in keys:
            if key in self._data:
                self._del(key)
            
    def lock(self):
        self._clear_lock = True

    def clear(self, call):
        self.lock()
        return call()


def wrap(base, parent, name, *baseargs, **basekwargs):
    def _wrapped(*args, **kwargs):
        fullargs = baseargs + args
        kwargs.update(basekwargs)
        return getattr(parent, '%s_%s' % (base, name))(*fullargs, **kwargs)
    return _wrapped


def build_dict(master, klass, data, key='id'):
    return  dict([(info[key], klass(master, info)) for info in data])

def _convert(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class Bullet(object):
    def __init__(self, number, link, active):
        self.number = number
        self.link = link
        self.active = active


class Paginator(object):
    def __init__(self, objects, page, get_link, per_page=20, bullets=5):
        page = int(page)
        self.page = page
        self.get_link = get_link
        self.all_objects = objects
        self.objects_count = objects.count()
        per_page = per_page() if callable(per_page) else per_page
        self.pages_count = int(float(self.objects_count) / float(per_page)) + 1
        self.bullets_count = 5
        self.per_page = per_page
        self.start = (page - 1) * per_page
        self.end = page * per_page
        self.is_first = page == 1
        self.first_bullet = Bullet(1, self.get_link(1), False)
        self.is_last = page == self.pages_count
        self.last_bullet = Bullet(self.pages_count, self.get_link(self.pages_count), False)
        self.has_pages = self.pages_count != 1
        self._objects = None
        self._bullets = None
        
    @property
    def bullets(self):
        if self._bullets is None:
            pre = int(float(self.bullets_count) / 2)
            bullets = [Bullet(self.page, self.get_link(self.page), True)]
            diff = 0
            for i in range(1, pre + 1):
                this = self.page - i
                if this:
                    bullets.insert(0, Bullet(this, self.get_link(this), False))
                else:
                    diff = pre - this
                    break
            for i in range(1, pre + 1 + diff):
                this = self.page +  i
                if this <= self.pages_count:
                    bullets.append(Bullet(this, self.get_link(this), False))
                else:
                    break
            self._bullets = bullets
        return self._bullets
        
    @property
    def objects(self):
        if self._objects is None:
            self._objects = self.all_objects[self.start:self.end]
        return self._objects

    
class InternalRequest(object):
    def __init__(self, request, args, kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs
        
    def contribute_to_class(self, cls):
        cls.request = self.request
        cls.args = self.args
        cls.kwargs = self.kwargs
    

class BaseView(object):
    """
    A base class to create class based views.
    
    It will automatically check allowed methods if a list of allowed methods are
    given. It also automatically tries to route to 'handle_`method`' methods if
    they're available. So if for example you define a 'handle_post' method and
    the request method is 'POST', this one will be called instead of 'handle'.
    
    For each request a new instance of this class will be created and it will get
    three attributes set: request, args and kwargs.
    """
    # A list of allowed methods (if empty any method will be allowed)
    allowed_methods = []
    # The template to use in the render_to_response helper
    template = 'base.html'
    # Only allow access to logged in users
    login_required = False
    # Only allow access to users with certain permissions
    required_permissions = []
    # Only allow access to superusers
    superuser_required = False
    # Response to send when request is automatically declined
    auto_decline_response = 'not_found'
    
    #===========================================================================
    # Dummy Attributes (DO NOT OVERWRITE)
    #=========================================================================== 
    request = None
    args = tuple()
    kwargs = {}
    
    #===========================================================================
    # Internal Methods
    #===========================================================================
    
    def __init__(self, *args, **kwargs):
        # Preserve args and kwargs
        self._initial_args = args
        self._initial_kwargs = kwargs

    @property
    def __name__(self):
        """
        INTERNAL: required by django
        """
        return self.get_view_name()
        
    def __call__(self, request, *args, **kwargs):
        """
        INTERNAL: Called by django when a request should be handled by this view.
        Creates a new instance of this class to sandbox 
        """
        if self.allowed_methods and request.method not in self.allowed_methods:
            return getattr(self, self.auto_decline_response)()
        if self.login_required and not request.user.is_authenticated():
            return getattr(self, self.auto_decline_response)()
        if self.superuser_required and not request.user.is_superuser:
            return getattr(self, self.auto_decline_response)()
        if self.required_permissions and not request.user.has_perms(self.required_permissions):
            return getattr(self, self.auto_decline_response)()
        handle_func_name = 'handle_%s' % request.method.lower()
        if not hasattr(self, handle_func_name):
            handle_func_name = 'handle'
        # Create a sandbox instance of this class to safely set the request, args and kwargs attributes
        sandbox = self.__class__(*self._initial_args, **self._initial_kwargs)
        sandbox.args = args
        sandbox.kwargs = kwargs
        sandbox.request = request
        return getattr(sandbox, handle_func_name)()
    
    #===========================================================================
    # Misc Helpers
    #===========================================================================
    
    def get_view_name(self):
        """
        Returns the name of this view
        """
        return self.__class__.__name__
    
    def get_template(self):
        return self.template
    
    def logout(self):
        logout(self.request)
        

    def get_page_link(self, page):
        return '%s?page=%s' % (self.request.path, page)
        
    def paginate(self, objects, page):
        return Paginator(objects, page, self.get_page_link, 20, 5)
    
    def reverse(self, view_name, *args, **kwargs):
        return reverse(view_name, args=args or (), kwargs=kwargs or {})
    
    #===========================================================================
    # Handlers
    #===========================================================================
    
    def handle(self):
        """
        Write your view logic here
        """
        pass
    
    #===========================================================================
    # Response Helpers
    #===========================================================================
    
    def not_allowed(self, data=''):
        return HttpResponseNotAllowed(data)
    
    def forbidden(self, data=''):
        return HttpResponseForbidden(data)
    
    def redirect(self, url):
        return HttpResponseRedirect(url)
    
    def named_redirect(self, viewname, urlconf=None, args=None, kwargs=None,
            prefix=None, current_app=None):
        return self.redirect(reverse(view, urlconf, args, kwargs, prefix, current_app))
    
    def permanent_redirect(self, url):
        return HttpResponsePermanentRedirect(url)
    
    def named_permanent_redirect(self, viewname, urlconf=None, args=None,
            kwargs=None, prefix=None, current_app=None):
        return self.permanent_redirect(reverse(view, urlconf, args, kwargs, prefix, current_app))
    
    def not_modified(self, data=''):
        return HttpResponseNotModified(data)
    
    def bad_request(self, data=''):
        return HttpResponseBadRequest(data)
    
    def not_found(self, data=''):
        return HttpResponseNotFound(data)
    
    def gone(self, data=''):
        return HttpResponseGone(data)
    
    def server_error(self, data=''):
        return HttpResponseServerError(data)
    
    def simplejson(self, data):
        return HttpResponse(simplejson.dumps(data), content_type='application/json')
    
    def response(self, data):
        return HttpResponse(data)
    
    def render_to_response(self, data, request_context=True):
        if request_context:
            return render_to_response(self.get_template(), data, RequestContext(self.request))
        return render_to_response(self.get_template(), data)
    
    #===========================================================================
    # Message Helpers
    #===========================================================================
    
    def message_debug(self, message):
        debug(self.request, message)
        
    def message_info(self, message):
        info(self.request, message)
        
    def message_success(self, message):
        success(self.request, message)
        
    def message_warning(self, message):
        warning(self.request, message)
        
    def message_error(self, message):
        error(self.request, message)
        
    def add_message(self, msgtype, message):
        add_message(self.request, msgtype, message)
    
    
class WarningProxy(object):
    __stuff = {}
    def __init__(self, logger, obj):
        WarningProxy.__stuff[self] = {}
        WarningProxy.__stuff[self]['logger'] = logger
        WarningProxy.__stuff[self]['obj'] = obj

    def __getattr__(self, attr):
        WarningProxy.__stuff[self]['logger'].lock()
        val = getattr(WarningProxy.__stuff[self]['obj'], attr)
        WarningProxy.__stuff[self]['logger'].release()
        return WarningProxy(WarningProxy.__stuff[self]['logger'], val)
    
    def __setattr__(self, attr, value):
        WarningProxy.__stuff[self]['logger'].lock()
        setattr(WarningProxy.__stuff[self]['obj'], attr)
        WarningProxy.__stuff[self]['logger'].release()
        
    def __call__(self, *args, **kwargs):
        WarningProxy.__stuff[self]['logger'].lock()
        val = WarningProxy.__stuff[self]['obj'](*args, **kwargs)
        WarningProxy.__stuff[self]['logger'].release()
        return val
    
    
class WarningLogger(object):
    def __init__(self):
        self.proxies = []
        self.queue = []
        self._old = warnings.showwarning
        
    def proxy(self, obj):
        return WarningProxy(self, obj)
    
    def lock(self):
        warnings.showwarning = self._showwarning
        
    def _showwarning(self, message, category, filename, lineno, fileobj=None):
        self.queue.append((message, category, filename, lineno))
        self._old(message, category, filename, lineno, fileobj)
    
    def release(self):
        warnings.showwarning = self._old
        
    def get(self):
        queue = list(self.queue)
        self.queue = []
        return queue
    
    def reset(self):
        self.queue = []
    
    
class Lazy(object):
    def __init__(self, real):
        self.__real = real
        self.__cache = {}
        
    def __getattr__(self, attr):
        if attr not in self.__cache:
            self.__cache[attr] = getattr(self.__real, attr)
        return self.__cache[attr]
    

def dequeue(limit=None):
    from mailchimp.models import Queue
    for camp in Queue.objects.dequeue(limit):
        yield camp
        
def is_queued_or_sent(object):
    from mailchimp.models import Queue, Campaign
    object_id = object.pk
    content_type = ContentType.objects.get_for_model(object)
    q = Queue.objects.filter(content_type=content_type, object_id=object_id)
    if q.count():
        return q[0]
    c = Campaign.objects.filter(content_type=content_type, object_id=object_id)
    if c.count():
        return c[0]
    return False

# this has to be down here to prevent circular imports
from mailchimp.chimp import Connection
# open a non-connected connection (lazily connect on first get_connection call)
CONNECTION = Connection(secure=SECURE)

def get_connection():
    if not CONNECTION.is_connected:
        CONNECTION.connect(API_KEY)
    return CONNECTION
########NEW FILE########
__FILENAME__ = views
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from django.http import Http404
from mailchimp.models import Campaign, Queue
from mailchimp.settings import WEBHOOK_KEY
from mailchimp.signals import get_signal
from mailchimp.utils import BaseView, Lazy, get_connection
import datetime
import re

class MailchimpBaseView(BaseView):
    @property
    def connection(self):
        return get_connection()
    
    
class MailchimpView(MailchimpBaseView):
    required_permissions = ['mailchimp.can_view']


class Overview(MailchimpView):
    template = 'mailchimp/overview.html'
    def handle_post(self):
        return self.not_allowed()
    
    def handle_get(self):
        data = {
            'paginator': self.paginate(Campaign.objects.all(), int(self.kwargs.get('page', 1))),
            'queue': Queue.objects.all()
        }
        return self.render_to_response(data)
        
    def get_page_link(self, page):
        return self.reverse('mailchimp_overview', page=page)


class ScheduleCampaignForObject(MailchimpView):
    def auth_check(self):
        basic = super(ScheduleCampaignForObject, self).auth_check()
        if not basic:
            return basic
        return self.request.user.has_perm('mailchimp.can_send')
    
    def handle_post(self):
        return self.not_allowed()
    
    def back(self):
        return self.redirect(self.request.META['HTTP_REFERER'])
    
    def handle_get(self):
        ct = ContentType.objects.get(pk=self.kwargs['content_type'])
        obj = ct.model_class().objects.get(pk=self.kwargs['pk'])
        if obj.mailchimp_schedule(self.connection):
            self.message_success("The Campaign has been scheduled for sending.")
        else:
            self.message_error("An error has occured while trying to send, please try again later.")
        return self.back()
        
        
class TestCampaignForObjectReal(ScheduleCampaignForObject):
    def handle_get(self):
        ct = ContentType.objects.get(pk=self.kwargs['content_type'])
        obj = ct.model_class().objects.get(pk=self.kwargs['pk'])
        self.connection.warnings.reset()
        if obj.mailchimp_test(self.connection, self.request):
            self.message_success("A Test Campaign has been sent to your email address (%s)." % self.request.user.email)
            for message, category, filename, lineno in self.connection.warnings.get():
                self.message_warning("%s: %s" % (category.__name__, message))
        else:
            self.message_error("And error has occured while trying to send the test mail to you, please try again later")
        return self.simplejson(True)
    
    
class TestCampaignForObject(ScheduleCampaignForObject):
    template = 'mailchimp/send_test.html'
    
    def handle_get(self):
        data = {
            'ajaxurl': reverse('mailchimp_real_test_for_object', kwargs=self.kwargs),
            'redirecturl': self.request.META['HTTP_REFERER']
        }
        return self.render_to_response(data)


class CampaignInformation(MailchimpView):
    template = 'mailchimp/campaign_information.html'
    def handle_post(self):
        return self.not_allowed()
    
    def handle_get(self):
        camp = Campaign.objects.get_or_404(campaign_id=self.kwargs['campaign_id'])
        data = {'campaign': camp}
        extra_info = camp.get_extra_info()
        if camp.object and hasattr(camp.object, 'mailchimp_get_extra_info'):
            extra_info = camp.object.mailchimp_get_extra_info()
        data['extra_info'] = extra_info
        return self.render_to_response(data)
        

class WebHook(MailchimpBaseView):
    def handle_get(self):
        return self.response("hello chimp")
    
    def handle_post(self):
        if self.kwargs.get('key', '') != WEBHOOK_KEY:
            return self.not_found()
        data = self.request.POST
        signal = get_signal(data['type'])
        ts = data["fired_at"]
        fired_at = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        kwargs = {
            'list': self.connection.get_list_by_id(data["data[list_id]"]),
            'fired_at': fired_at,
            'type': data['type'],
        }
        if data['type'] == 'cleaned':
            kwargs.update({
                'reason': data['data[reason]'],
                'email': data['data[email]'],
            })
        elif data['type'] == 'upemail':
            kwargs.update({
                 'old_email': data['data[old_email]'],
                 'new_email': data['data[new_email]'],
            })
        elif data['type'] == 'campaign':
            kwargs.update({
                'campaign_id': data['data[id]'],
                'subject': data['data[subject]'],
                'status': data['data[status]'],
                'reason': data['data[reason]'],
            })
        else:
            merge_re = re.compile('data\[merges\]\[(?P<name>\w+)\]')
            merges = {}
            for key, value in data.items():
                match = merge_re.match(key)
                if match:
                    name = match.group('name').lower()
                    if name in ('interests', 'fname', 'lname'):
                        continue
                    merges[name] = value
            kwargs.update({
                'email': data['data[email]'],
                'fname': data['data[merges][FNAME]'] if 'data[merges][FNAME]' in data else '',
                'lname': data['data[merges][LNAME]'] if 'data[merges][LNAME]' in data else '',
                'merges': merges,
            })
            if 'data[merges][INTERESTS]' in data:
                kwargs['interests'] = [i.strip() for i in data['data[merges][INTERESTS]'].split(',')]
        signal.send(sender=self.connection, **kwargs)
        return self.response("ok")

        
class Dequeue(ScheduleCampaignForObject):
    def handle_get(self):
        q = Queue.objects.get_or_404(pk=self.kwargs['id'])
        if q.send():
            self.message_success("The Campaign has successfully been dequeued.")
        else:
            self.message_error("An error has occured while trying to dequeue this campaign, please try again later.")
        return self.back()
        

class Cancel(ScheduleCampaignForObject):
    def handle_get(self):
        q = Queue.objects.get_or_404(pk=self.kwargs['id'])
        q.delete()
        self.message_success("The Campaign has been canceled.")
        return self.back()


webhook = csrf_exempt(WebHook())
dequeue = Dequeue()
cancel = Cancel()
campaign_information = CampaignInformation()
overview = Overview()
schedule_campaign_for_object = ScheduleCampaignForObject()
test_campaign_for_object = TestCampaignForObject()
test_real = TestCampaignForObjectReal()

########NEW FILE########
