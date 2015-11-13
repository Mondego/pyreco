__FILENAME__ = admin
from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib import admin
from django.contrib.auth.models import Group

from django_messages.utils import get_user_model
User = get_user_model()

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None
    
from django_messages.models import Message

class MessageAdminForm(forms.ModelForm):
    """
    Custom AdminForm to enable messages to groups and all users.
    """
    group = forms.ChoiceField(label=_('group'), required=False,
        help_text=_('Creates the message optionally for all users or a group of users.'))

    def __init__(self, *args, **kwargs):
        super(MessageAdminForm, self).__init__(*args, **kwargs)
        self.fields['group'].choices = self._get_group_choices()
        self.fields['recipient'].required = True

    def _get_group_choices(self):
        return [('', u'---------'), ('all', _('All users'))] + \
            [(group.pk, group.name) for group in Group.objects.all()]

    class Meta:
        model = Message
        fields = ('sender', 'recipient', 'group', 'parent_msg', 'subject',
                'body', 'sent_at', 'read_at', 'replied_at', 'sender_deleted_at',
                'recipient_deleted_at')

class MessageAdmin(admin.ModelAdmin):
    form = MessageAdminForm
    fieldsets = (
        (None, {
            'fields': (
                'sender',
                ('recipient', 'group'),
            ),
        }),
        (_('Message'), {
            'fields': (
                'parent_msg',
                'subject', 'body',
            ),
            'classes': ('monospace' ),
        }),
        (_('Date/time'), {
            'fields': (
                'sent_at', 'read_at', 'replied_at',
                'sender_deleted_at', 'recipient_deleted_at',
            ),
            'classes': ('collapse', 'wide'),
        }),
    )
    list_display = ('subject', 'sender', 'recipient', 'sent_at', 'read_at')
    list_filter = ('sent_at', 'sender', 'recipient')
    search_fields = ('subject', 'body')
    raw_id_fields = ('sender', 'recipient', 'parent_msg')

    def save_model(self, request, obj, form, change):
        """
        Saves the message for the recipient and looks in the form instance
        for other possible recipients. Prevents duplication by excludin the
        original recipient from the list of optional recipients.

        When changing an existing message and choosing optional recipients,
        the message is effectively resent to those users.
        """
        obj.save()
        
        if notification:
            # Getting the appropriate notice labels for the sender and recipients.
            if obj.parent_msg is None:
                sender_label = 'messages_sent'
                recipients_label = 'messages_received'
            else:
                sender_label = 'messages_replied'
                recipients_label = 'messages_reply_received'
                
            # Notification for the sender.
            notification.send([obj.sender], sender_label, {'message': obj,})

        if form.cleaned_data['group'] == 'all':
            # send to all users
            recipients = User.objects.exclude(pk=obj.recipient.pk)
        else:
            # send to a group of users
            recipients = []
            group = form.cleaned_data['group']
            if group:
                group = Group.objects.get(pk=group)
                recipients.extend(
                    list(group.user_set.exclude(pk=obj.recipient.pk)))
        # create messages for all found recipients
        for user in recipients:
            obj.pk = None
            obj.recipient = user
            obj.save()

            if notification:
                # Notification for the recipient.
                notification.send([user], recipients_label, {'message' : obj,})
            
admin.site.register(Message, MessageAdmin)

########NEW FILE########
__FILENAME__ = apps
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

class DjangoMessagesConfig(AppConfig):
    name = 'django_messages'
    verbose_name = _('Messages')

########NEW FILE########
__FILENAME__ = context_processors
from django_messages.models import inbox_count_for

def inbox(request):
    if request.user.is_authenticated():
        return {'messages_inbox_count': inbox_count_for(request.user)}
    else:
        return {}

########NEW FILE########
__FILENAME__ = fields
"""
Based on http://www.djangosnippets.org/snippets/595/
by sopelkin
"""

from django import forms
from django.forms import widgets
from django.utils.translation import ugettext_lazy as _

from django_messages.utils import get_user_model, get_username_field

User = get_user_model()


class CommaSeparatedUserInput(widgets.Input):
    input_type = 'text'
    
    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        elif isinstance(value, (list, tuple)):
            value = (', '.join([getattr(user, get_username_field()) for user in value]))
        return super(CommaSeparatedUserInput, self).render(name, value, attrs)
        


class CommaSeparatedUserField(forms.Field):
    widget = CommaSeparatedUserInput
    
    def __init__(self, *args, **kwargs):
        recipient_filter = kwargs.pop('recipient_filter', None)
        self._recipient_filter = recipient_filter
        super(CommaSeparatedUserField, self).__init__(*args, **kwargs)
        
    def clean(self, value):
        super(CommaSeparatedUserField, self).clean(value)
        if not value:
            return ''
        if isinstance(value, (list, tuple)):
            return value
        
        names = set(value.split(','))
        names_set = set([name.strip() for name in names if name.strip()])
        users = list(User.objects.filter(**{'%s__in' % get_username_field(): names_set}))
        unknown_names = names_set ^ set([getattr(user, get_username_field()) for user in users])
        
        recipient_filter = self._recipient_filter
        invalid_users = []
        if recipient_filter is not None:
            for r in users:
                if recipient_filter(r) is False:
                    users.remove(r)
                    invalid_users.append(getattr(r, get_username_field()))
        
        if unknown_names or invalid_users:
            raise forms.ValidationError(_(u"The following usernames are incorrect: %(users)s") % {'users': ', '.join(list(unknown_names)+invalid_users)})
        
        return users



########NEW FILE########
__FILENAME__ = forms
import datetime
from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None

from django_messages.models import Message
from django_messages.fields import CommaSeparatedUserField

class ComposeForm(forms.Form):
    """
    A simple default form for private messages.
    """
    recipient = CommaSeparatedUserField(label=_(u"Recipient"))
    subject = forms.CharField(label=_(u"Subject"), max_length=120)
    body = forms.CharField(label=_(u"Body"),
        widget=forms.Textarea(attrs={'rows': '12', 'cols':'55'}))
    
        
    def __init__(self, *args, **kwargs):
        recipient_filter = kwargs.pop('recipient_filter', None)
        super(ComposeForm, self).__init__(*args, **kwargs)
        if recipient_filter is not None:
            self.fields['recipient']._recipient_filter = recipient_filter
    
                
    def save(self, sender, parent_msg=None):
        recipients = self.cleaned_data['recipient']
        subject = self.cleaned_data['subject']
        body = self.cleaned_data['body']
        message_list = []
        for r in recipients:
            msg = Message(
                sender = sender,
                recipient = r,
                subject = subject,
                body = body,
            )
            if parent_msg is not None:
                msg.parent_msg = parent_msg
                parent_msg.replied_at = datetime.datetime.now()
                parent_msg.save()
            msg.save()
            message_list.append(msg)
            if notification:
                if parent_msg is not None:
                    notification.send([sender], "messages_replied", {'message': msg,})
                    notification.send([r], "messages_reply_received", {'message': msg,})
                else:
                    notification.send([sender], "messages_sent", {'message': msg,})
                    notification.send([r], "messages_received", {'message': msg,})
        return message_list

########NEW FILE########
__FILENAME__ = management
from django.db.models import get_models, signals
from django.conf import settings
from django.utils.translation import ugettext_noop as _

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification

    def create_notice_types(app, created_models, verbosity, **kwargs):
        notification.create_notice_type("messages_received", _("Message Received"), _("you have received a message"), default=2)
        notification.create_notice_type("messages_sent", _("Message Sent"), _("you have sent a message"), default=1)
        notification.create_notice_type("messages_replied", _("Message Replied"), _("you have replied to a message"), default=1)
        notification.create_notice_type("messages_reply_received", _("Reply Received"), _("you have received a reply to a message"), default=2)
        notification.create_notice_type("messages_deleted", _("Message Deleted"), _("you have deleted a message"), default=1)
        notification.create_notice_type("messages_recovered", _("Message Recovered"), _("you have undeleted a message"), default=1)

    signals.post_syncdb.connect(create_notice_types, sender=notification)
else:
    print "Skipping creation of NoticeTypes as notification app not found"

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.conf import settings
from django.db.models import signals
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')

class MessageManager(models.Manager):

    def inbox_for(self, user):
        """
        Returns all messages that were received by the given user and are not
        marked as deleted.
        """
        return self.filter(
            recipient=user,
            recipient_deleted_at__isnull=True,
        )

    def outbox_for(self, user):
        """
        Returns all messages that were sent by the given user and are not
        marked as deleted.
        """
        return self.filter(
            sender=user,
            sender_deleted_at__isnull=True,
        )

    def trash_for(self, user):
        """
        Returns all messages that were either received or sent by the given
        user and are marked as deleted.
        """
        return self.filter(
            recipient=user,
            recipient_deleted_at__isnull=False,
        ) | self.filter(
            sender=user,
            sender_deleted_at__isnull=False,
        )


class Message(models.Model):
    """
    A private message from user to user
    """
    subject = models.CharField(_("Subject"), max_length=120)
    body = models.TextField(_("Body"))
    sender = models.ForeignKey(AUTH_USER_MODEL, related_name='sent_messages', verbose_name=_("Sender"))
    recipient = models.ForeignKey(AUTH_USER_MODEL, related_name='received_messages', null=True, blank=True, verbose_name=_("Recipient"))
    parent_msg = models.ForeignKey('self', related_name='next_messages', null=True, blank=True, verbose_name=_("Parent message"))
    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True)
    read_at = models.DateTimeField(_("read at"), null=True, blank=True)
    replied_at = models.DateTimeField(_("replied at"), null=True, blank=True)
    sender_deleted_at = models.DateTimeField(_("Sender deleted at"), null=True, blank=True)
    recipient_deleted_at = models.DateTimeField(_("Recipient deleted at"), null=True, blank=True)
    
    objects = MessageManager()
    
    def new(self):
        """returns whether the recipient has read the message or not"""
        if self.read_at is not None:
            return False
        return True
        
    def replied(self):
        """returns whether the recipient has written a reply to this message"""
        if self.replied_at is not None:
            return True
        return False
    
    def __unicode__(self):
        return self.subject
    
    def get_absolute_url(self):
        return ('messages_detail', [self.id])
    get_absolute_url = models.permalink(get_absolute_url)
    
    def save(self, **kwargs):
        if not self.id:
            self.sent_at = timezone.now()
        super(Message, self).save(**kwargs) 
    
    class Meta:
        ordering = ['-sent_at']
        verbose_name = _("Message")
        verbose_name_plural = _("Messages")
        
def inbox_count_for(user):
    """
    returns the number of unread messages for the given user but does not
    mark them seen
    """
    return Message.objects.filter(recipient=user, read_at__isnull=True, recipient_deleted_at__isnull=True).count()

# fallback for email notification if django-notification could not be found
if "notification" not in settings.INSTALLED_APPS:
    from django_messages.utils import new_message_email
    signals.post_save.connect(new_message_email, sender=Message)

########NEW FILE########
__FILENAME__ = signals

########NEW FILE########
__FILENAME__ = inbox
from django.template import Library, Node, TemplateSyntaxError

class InboxOutput(Node):
    def __init__(self, varname=None):
        self.varname = varname
        
    def render(self, context):
        try:
            user = context['user']
            count = user.received_messages.filter(read_at__isnull=True, recipient_deleted_at__isnull=True).count()
        except (KeyError, AttributeError):
            count = ''
        if self.varname is not None:
            context[self.varname] = count
            return ""
        else:
            return "%s" % (count)        
        
def do_print_inbox_count(parser, token):
    """
    A templatetag to show the unread-count for a logged in user.
    Returns the number of unread messages in the user's inbox.
    Usage::
    
        {% load inbox %}
        {% inbox_count %}
    
        {# or assign the value to a variable: #}
        
        {% inbox_count as my_var %}
        {{ my_var }}
        
    """
    bits = token.contents.split()
    if len(bits) > 1:
        if len(bits) != 3:
            raise TemplateSyntaxError, "inbox_count tag takes either no arguments or exactly two arguments"
        if bits[1] != 'as':
            raise TemplateSyntaxError, "first argument to inbox_count tag must be 'as'"
        return InboxOutput(bits[2])
    else:
        return InboxOutput()

register = Library()     
register.tag('inbox_count', do_print_inbox_count)

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils import timezone
from django_messages.models import Message
from django_messages.utils import format_subject, format_quote


class SendTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user('user1', 'user1@example.com', '123456')
        self.user2 = User.objects.create_user('user2', 'user2@example.com', '123456')
        self.msg1 = Message(sender=self.user1, recipient=self.user2, subject='Subject Text', body='Body Text')
        self.msg1.save()
        
    def testBasic(self):
        self.assertEquals(self.msg1.sender, self.user1)
        self.assertEquals(self.msg1.recipient, self.user2)
        self.assertEquals(self.msg1.subject, 'Subject Text')
        self.assertEquals(self.msg1.body, 'Body Text')
        self.assertEquals(self.user1.sent_messages.count(), 1)
        self.assertEquals(self.user1.received_messages.count(), 0)
        self.assertEquals(self.user2.received_messages.count(), 1)
        self.assertEquals(self.user2.sent_messages.count(), 0)
        
class DeleteTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user('user3', 'user3@example.com', '123456')
        self.user2 = User.objects.create_user('user4', 'user4@example.com', '123456')
        self.msg1 = Message(sender=self.user1, recipient=self.user2, subject='Subject Text 1', body='Body Text 1')
        self.msg2 = Message(sender=self.user1, recipient=self.user2, subject='Subject Text 2', body='Body Text 2')
        self.msg1.sender_deleted_at = timezone.now()
        self.msg2.recipient_deleted_at = timezone.now()
        self.msg1.save()
        self.msg2.save()
                
    def testBasic(self):
        self.assertEquals(Message.objects.outbox_for(self.user1).count(), 1)
        self.assertEquals(Message.objects.outbox_for(self.user1)[0].subject, 'Subject Text 2')
        self.assertEquals(Message.objects.inbox_for(self.user2).count(),1)
        self.assertEquals(Message.objects.inbox_for(self.user2)[0].subject, 'Subject Text 1')
        #undelete
        self.msg1.sender_deleted_at = None
        self.msg2.recipient_deleted_at = None
        self.msg1.save()
        self.msg2.save()
        self.assertEquals(Message.objects.outbox_for(self.user1).count(), 2)
        self.assertEquals(Message.objects.inbox_for(self.user2).count(),2)


class IntegrationTestCase(TestCase):
    """
    Test the app from a user perpective using Django's Test-Client.
    
    """
    
    T_USER_DATA = [{'username': 'user_1', 'password': '123456', 
                    'email': 'user_1@example.com'},
                   {'username': 'user_2', 'password': '123456', 
                    'email': 'user_2@example.com'},]
    T_MESSAGE_DATA = [{'subject': 'Test Subject 1',
                       'body': 'Lorem ipsum\ndolor sit amet\n\nconsectur.'}]
                                      
    def setUp(self):
        """ create 2 users and a test-client logged in as user_1 """
        self.user_1 = User.objects.create_user(**self.T_USER_DATA[0])
        self.user_2 = User.objects.create_user(**self.T_USER_DATA[1])
        self.c = Client()
        self.c.login(username=self.T_USER_DATA[0]['username'], 
                     password=self.T_USER_DATA[0]['password'])
        
    def testInboxEmpty(self):
        """ request the empty inbox """
        response = self.c.get(reverse('messages_inbox'))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.templates[0].name, 'django_messages/inbox.html')
        self.assertEquals(len(response.context['message_list']), 0)
    
    def testOutboxEmpty(self):
        """ request the empty outbox """
        response = self.c.get(reverse('messages_outbox'))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.templates[0].name, 'django_messages/outbox.html')
        self.assertEquals(len(response.context['message_list']), 0)

    def testTrashEmpty(self):
        """ request the empty trash """
        response = self.c.get(reverse('messages_trash'))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.templates[0].name, 'django_messages/trash.html')
        self.assertEquals(len(response.context['message_list']), 0)

    def testCompose(self):
        """ compose a message step by step """
        response = self.c.get(reverse('messages_compose'))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.templates[0].name, 'django_messages/compose.html')
        response = self.c.post(reverse('messages_compose'),
            {'recipient': self.T_USER_DATA[1]['username'],
             'subject': self.T_MESSAGE_DATA[0]['subject'],
             'body': self.T_MESSAGE_DATA[0]['body']})
        # successfull sending should redirect to inbox
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['Location'], "http://testserver%s"%reverse('messages_inbox'))
        
        # make sure the message exists in the outbox after sending
        response = self.c.get(reverse('messages_outbox'))
        self.assertEquals(len(response.context['message_list']), 1)

    def testReply(self):
        """ test that user_2 can reply """
        # create a message for this test
        Message.objects.create(sender=self.user_1, 
                               recipient=self.user_2, 
                               subject=self.T_MESSAGE_DATA[0]['subject'], 
                               body=self.T_MESSAGE_DATA[0]['body'])
        # log the user_2 in and check the inbox
        self.c.login(username=self.T_USER_DATA[1]['username'], 
                     password=self.T_USER_DATA[1]['password'])
        response = self.c.get(reverse('messages_inbox'))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.templates[0].name, 'django_messages/inbox.html')
        self.assertEquals(len(response.context['message_list']), 1)
        pk = getattr(response.context['message_list'][0], 'pk')
        # reply to the first message
        response = self.c.get(reverse('messages_reply', 
            kwargs={'message_id':pk}))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.templates[0].name, 'django_messages/compose.html')
        self.assertEquals(response.context['form'].initial['body'], 
                format_quote(self.user_1, self.T_MESSAGE_DATA[0]['body']))
        self.assertEqual(response.context['form'].initial['subject'],
                u"Re: %(subject)s"%{'subject': self.T_MESSAGE_DATA[0]['subject']})
                     
class FormatTestCase(TestCase):
    """ some tests for helper functions """
    def testSubject(self):
        """ test that reply counting works as expected """
        self.assertEquals(format_subject(u"foo bar"), u"Re: foo bar")
        self.assertEquals(format_subject(u"Re: foo bar"), u"Re[2]: foo bar")
        self.assertEquals(format_subject(u"Re[2]: foo bar"), u"Re[3]: foo bar")
        self.assertEquals(format_subject(u"Re[10]: foo bar"), u"Re[11]: foo bar")
        
        
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from django.views.generic import RedirectView

from django_messages.views import *

urlpatterns = patterns('',
    url(r'^$', RedirectView.as_view(url='inbox/'), name='messages_redirect'),
    url(r'^inbox/$', inbox, name='messages_inbox'),
    url(r'^outbox/$', outbox, name='messages_outbox'),
    url(r'^compose/$', compose, name='messages_compose'),
    url(r'^compose/(?P<recipient>[\w.@+-]+)/$', compose, name='messages_compose_to'),
    url(r'^reply/(?P<message_id>[\d]+)/$', reply, name='messages_reply'),
    url(r'^view/(?P<message_id>[\d]+)/$', view, name='messages_detail'),
    url(r'^delete/(?P<message_id>[\d]+)/$', delete, name='messages_delete'),
    url(r'^undelete/(?P<message_id>[\d]+)/$', undelete, name='messages_undelete'),
    url(r'^trash/$', trash, name='messages_trash'),
)

########NEW FILE########
__FILENAME__ = utils
import re
import django
from django.utils.text import wrap
from django.utils.translation import ugettext, ugettext_lazy as _
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.conf import settings

# favour django-mailer but fall back to django.core.mail

if "mailer" in settings.INSTALLED_APPS:
    from mailer import send_mail
else:
    from django.core.mail import send_mail

def format_quote(sender, body):
    """
    Wraps text at 55 chars and prepends each
    line with `> `.
    Used for quoting messages in replies.
    """
    lines = wrap(body, 55).split('\n')
    for i, line in enumerate(lines):
        lines[i] = "> %s" % line
    quote = '\n'.join(lines)
    return ugettext(u"%(sender)s wrote:\n%(body)s") % {
        'sender': sender,
        'body': quote
    }

def format_subject(subject):
    """
    Prepends 'Re:' to the subject. To avoid multiple 'Re:'s
    a counter is added.
    NOTE: Currently unused. First step to fix Issue #48.
    FIXME: Any hints how to make this i18n aware are very welcome.
    
    """
    subject_prefix_re = r'^Re\[(\d*)\]:\ '
    m = re.match(subject_prefix_re, subject, re.U)
    prefix = u""
    if subject.startswith('Re: '):
        prefix = u"[2]"
        subject = subject[4:]
    elif m is not None:
        try:
            num = int(m.group(1))
            prefix = u"[%d]" % (num+1)
            subject = subject[6+len(str(num)):]
        except:
            # if anything fails here, fall back to the old mechanism
            pass
        
    return ugettext(u"Re%(prefix)s: %(subject)s") % {
        'subject': subject, 
        'prefix': prefix
    }
    
def new_message_email(sender, instance, signal, 
        subject_prefix=_(u'New Message: %(subject)s'),
        template_name="django_messages/new_message.html",
        default_protocol=None,
        *args, **kwargs):
    """
    This function sends an email and is called via Django's signal framework.
    Optional arguments:
        ``template_name``: the template to use
        ``subject_prefix``: prefix for the email subject.
        ``default_protocol``: default protocol in site URL passed to template
    """
    if default_protocol is None:
        default_protocol = getattr(settings, 'DEFAULT_HTTP_PROTOCOL', 'http')

    if 'created' in kwargs and kwargs['created']:
        try:
            current_domain = Site.objects.get_current().domain
            subject = subject_prefix % {'subject': instance.subject}
            message = render_to_string(template_name, {
                'site_url': '%s://%s' % (default_protocol, current_domain),
                'message': instance,
            })
            if instance.recipient.email != "":
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                    [instance.recipient.email,])
        except Exception, e:
            #print e
            pass #fail silently


def get_user_model():
    if django.VERSION[:2] >= (1, 5):
        from django.contrib.auth import get_user_model
        return get_user_model()
    else:
        from django.contrib.auth.models import User
        return User


def get_username_field():
    if django.VERSION[:2] >= (1, 5):
        return get_user_model().USERNAME_FIELD
    else:
        return 'username'
########NEW FILE########
__FILENAME__ = views
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.utils import timezone
from django.core.urlresolvers import reverse
from django.conf import settings

from django_messages.models import Message
from django_messages.forms import ComposeForm
from django_messages.utils import format_quote, get_user_model, get_username_field

User = get_user_model()

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None

def inbox(request, template_name='django_messages/inbox.html'):
    """
    Displays a list of received messages for the current user.
    Optional Arguments:
        ``template_name``: name of the template to use.
    """
    message_list = Message.objects.inbox_for(request.user)
    return render_to_response(template_name, {
        'message_list': message_list,
    }, context_instance=RequestContext(request))
inbox = login_required(inbox)

def outbox(request, template_name='django_messages/outbox.html'):
    """
    Displays a list of sent messages by the current user.
    Optional arguments:
        ``template_name``: name of the template to use.
    """
    message_list = Message.objects.outbox_for(request.user)
    return render_to_response(template_name, {
        'message_list': message_list,
    }, context_instance=RequestContext(request))
outbox = login_required(outbox)

def trash(request, template_name='django_messages/trash.html'):
    """
    Displays a list of deleted messages.
    Optional arguments:
        ``template_name``: name of the template to use
    Hint: A Cron-Job could periodicly clean up old messages, which are deleted
    by sender and recipient.
    """
    message_list = Message.objects.trash_for(request.user)
    return render_to_response(template_name, {
        'message_list': message_list,
    }, context_instance=RequestContext(request))
trash = login_required(trash)

def compose(request, recipient=None, form_class=ComposeForm,
        template_name='django_messages/compose.html', success_url=None, recipient_filter=None):
    """
    Displays and handles the ``form_class`` form to compose new messages.
    Required Arguments: None
    Optional Arguments:
        ``recipient``: username of a `django.contrib.auth` User, who should
                       receive the message, optionally multiple usernames
                       could be separated by a '+'
        ``form_class``: the form-class to use
        ``template_name``: the template to use
        ``success_url``: where to redirect after successfull submission
    """
    if request.method == "POST":
        sender = request.user
        form = form_class(request.POST, recipient_filter=recipient_filter)
        if form.is_valid():
            form.save(sender=request.user)
            messages.info(request, _(u"Message successfully sent."))
            if success_url is None:
                success_url = reverse('messages_inbox')
            if 'next' in request.GET:
                success_url = request.GET['next']
            return HttpResponseRedirect(success_url)
    else:
        form = form_class()
        if recipient is not None:
            recipients = [u for u in User.objects.filter(**{'%s__in' % get_username_field(): [r.strip() for r in recipient.split('+')]})]
            form.fields['recipient'].initial = recipients
    return render_to_response(template_name, {
        'form': form,
    }, context_instance=RequestContext(request))
compose = login_required(compose)

def reply(request, message_id, form_class=ComposeForm,
        template_name='django_messages/compose.html', success_url=None,
        recipient_filter=None, quote_helper=format_quote):
    """
    Prepares the ``form_class`` form for writing a reply to a given message
    (specified via ``message_id``). Uses the ``format_quote`` helper from
    ``messages.utils`` to pre-format the quote. To change the quote format
    assign a different ``quote_helper`` kwarg in your url-conf.

    """
    parent = get_object_or_404(Message, id=message_id)

    if parent.sender != request.user and parent.recipient != request.user:
        raise Http404

    if request.method == "POST":
        sender = request.user
        form = form_class(request.POST, recipient_filter=recipient_filter)
        if form.is_valid():
            form.save(sender=request.user, parent_msg=parent)
            messages.info(request, _(u"Message successfully sent."))
            if success_url is None:
                success_url = reverse('messages_inbox')
            return HttpResponseRedirect(success_url)
    else:
        form = form_class(initial={
            'body': quote_helper(parent.sender, parent.body),
            'subject': _(u"Re: %(subject)s") % {'subject': parent.subject},
            'recipient': [parent.sender,]
            })
    return render_to_response(template_name, {
        'form': form,
    }, context_instance=RequestContext(request))
reply = login_required(reply)

def delete(request, message_id, success_url=None):
    """
    Marks a message as deleted by sender or recipient. The message is not
    really removed from the database, because two users must delete a message
    before it's save to remove it completely.
    A cron-job should prune the database and remove old messages which are
    deleted by both users.
    As a side effect, this makes it easy to implement a trash with undelete.

    You can pass ?next=/foo/bar/ via the url to redirect the user to a different
    page (e.g. `/foo/bar/`) than ``success_url`` after deletion of the message.
    """
    user = request.user
    now = timezone.now()
    message = get_object_or_404(Message, id=message_id)
    deleted = False
    if success_url is None:
        success_url = reverse('messages_inbox')
    if 'next' in request.GET:
        success_url = request.GET['next']
    if message.sender == user:
        message.sender_deleted_at = now
        deleted = True
    if message.recipient == user:
        message.recipient_deleted_at = now
        deleted = True
    if deleted:
        message.save()
        messages.info(request, _(u"Message successfully deleted."))
        if notification:
            notification.send([user], "messages_deleted", {'message': message,})
        return HttpResponseRedirect(success_url)
    raise Http404
delete = login_required(delete)

def undelete(request, message_id, success_url=None):
    """
    Recovers a message from trash. This is achieved by removing the
    ``(sender|recipient)_deleted_at`` from the model.
    """
    user = request.user
    message = get_object_or_404(Message, id=message_id)
    undeleted = False
    if success_url is None:
        success_url = reverse('messages_inbox')
    if 'next' in request.GET:
        success_url = request.GET['next']
    if message.sender == user:
        message.sender_deleted_at = None
        undeleted = True
    if message.recipient == user:
        message.recipient_deleted_at = None
        undeleted = True
    if undeleted:
        message.save()
        messages.info(request, _(u"Message successfully recovered."))
        if notification:
            notification.send([user], "messages_recovered", {'message': message,})
        return HttpResponseRedirect(success_url)
    raise Http404
undelete = login_required(undelete)

def view(request, message_id, template_name='django_messages/view.html'):
    """
    Shows a single message.``message_id`` argument is required.
    The user is only allowed to see the message, if he is either
    the sender or the recipient. If the user is not allowed a 404
    is raised.
    If the user is the recipient and the message is unread
    ``read_at`` is set to the current datetime.
    """
    user = request.user
    now = timezone.now()
    message = get_object_or_404(Message, id=message_id)
    if (message.sender != user) and (message.recipient != user):
        raise Http404
    if message.read_at is None and message.recipient == user:
        message.read_at = now
        message.save()
    return render_to_response(template_name, {
        'message': message,
    }, context_instance=RequestContext(request))
view = login_required(view)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-messages documentation build configuration file, created by
# sphinx-quickstart on Mon Jan 26 10:27:49 2009.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.txt'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-messages'
copyright = u'2009-2014, Arne Brodowski'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.5'
# The full version, including alpha/beta/rc tags.
release = '0.5.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
unused_docs = ['README',]

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# Options for HTML output
# -----------------------

html_theme_path = ['.',]

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
# html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = './django-messages.png'

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['.static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
html_use_modindex = False

# If false, no index is generated.
html_use_index = False

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
html_copy_source = False

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-messagesdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'django-messages.tex', ur'django-messages Documentation',
   ur'Arne Brodowski', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
