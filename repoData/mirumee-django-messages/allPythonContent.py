__FILENAME__ = admin
from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib import admin
from django.contrib.auth.models import User, Group

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None
    
from django_messages.models import Message

class MessageAdminForm(forms.ModelForm):
    """
    Custom AdminForm to enable messages to groups and all users.
    """
    recipient = forms.ModelChoiceField(
        label=_('Recipient'), queryset=User.objects.all(), required=True)

    group = forms.ChoiceField(label=_('group'), required=False,
        help_text=_('Creates the message optionally for all users or a group of users.'))

    def __init__(self, *args, **kwargs):
        super(MessageAdminForm, self).__init__(*args, **kwargs)
        self.fields['group'].choices = self._get_group_choices()

    def _get_group_choices(self):
        return [('', u'---------'), ('all', _('All users'))] + \
            [(group.pk, group.name) for group in Group.objects.all()]

    class Meta:
        model = Message

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
                'deleted_at',
            ),
            'classes': ('collapse', 'wide'),
        }),
    )
    list_display = ('subject', 'sender', 'recipient', 'sent_at', 'read_at')
    list_filter = ('sent_at', 'sender', 'recipient')
    search_fields = ('subject', 'body')

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
                recipients_label = 'messages_received'
            else:
                recipients_label = 'messages_reply_received'

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
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _


class CommaSeparatedUserInput(widgets.Input):
    input_type = 'text'
    
    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        elif isinstance(value, (list, tuple)):
            value = (', '.join([user.username for user in value]))
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
        names_set = set([name.strip() for name in names])
        users = list(User.objects.filter(username__in=names_set))
        unknown_names = names_set ^ set([user.username for user in users])
        
        recipient_filter = self._recipient_filter
        invalid_users = []
        if recipient_filter is not None:
            for r in users:
                if recipient_filter(r) is False:
                    users.remove(r)
                    invalid_users.append(r.username)
        
        if unknown_names or invalid_users:
            raise forms.ValidationError(_(u"The following usernames are incorrect: %(users)s") % {'users': ', '.join(list(unknown_names)+invalid_users)})
        
        return users



########NEW FILE########
__FILENAME__ = forms
import datetime
from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext_noop
from django.contrib.auth.models import User
import uuid

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None

from django_messages.models import Message
from django_messages.fields import CommaSeparatedUserField
from django_messages.utils import format_quote


class MessageForm(forms.ModelForm):
    """
    base message form
    """
    recipients = CommaSeparatedUserField(label=_(u"Recipient"))
    subject = forms.CharField(label=_(u"Subject"))
    body = forms.CharField(label=_(u"Body"),
        widget=forms.Textarea(attrs={'rows': '12', 'cols':'55'}))

    class Meta:
        model = Message
        fields = ('recipients', 'subject', 'body',)

    def __init__(self, sender, *args, **kw):
        recipient_filter = kw.pop('recipient_filter', None)
        self.sender = sender
        super(MessageForm, self).__init__(*args, **kw)
        if recipient_filter is not None:
            self.fields['recipients']._recipient_filter = recipient_filter

    def create_recipient_message(self, recipient, message):
        return Message(
            owner = recipient,
            sender = self.sender,
            to = recipient.username,
            recipient = recipient,
            subject = message.subject,
            body = message.body,
            thread = message.thread,
            sent_at = message.sent_at,
        )

    def get_thread(self, message):
        return message.thread or uuid.uuid4().hex

    def save(self, commit=True):
        recipients = self.cleaned_data['recipients']
        instance = super(MessageForm, self).save(commit=False)
        instance.sender = self.sender
        instance.owner = self.sender
        instance.recipient = recipients[0]
        instance.thread = self.get_thread(instance)
        instance.unread = False
        instance.sent_at = datetime.datetime.now()

        message_list = []

        # clone messages in recipients inboxes
        for r in recipients:
            if r == self.sender: # skip duplicates
                continue
            msg = self.create_recipient_message(r, instance)
            message_list.append(msg)

        instance.to = ','.join([r.username for r in recipients])

        if commit:
            instance.save()
            for msg in message_list:
                msg.save()
                if notification:
                    notification.send([msg.recipient], 
                            "messages_received", {'message': msg,})
         
        return instance, message_list


class ComposeForm(MessageForm):
    """
    A simple default form for private messages.
    """

    class Meta:
        model = Message
        fields = ('recipients', 'subject', 'body',)
    

class ReplyForm(MessageForm):
    """
    reply to form
    """
    class Meta:
        model = Message
        fields = ('recipients', 'subject', 'body',)

    def __init__(self, sender, message, *args, **kw):
        self.parent_message = message
        initial = kw.pop('initial', {})
        initial['recipients'] = message.sender.username
        initial['body'] = self.quote_message(message)
        initial['subject'] = self.quote_subject(message.subject)
        kw['initial'] = initial
        super(ReplyForm, self).__init__(sender, *args, **kw)
    
    def quote_message(self, original_message):
        return format_quote(original_message.sender, original_message.body)

    def quote_subject(self, subject):
        return u'Re: %s' % subject

    def create_recipient_message(self, recipient, message):
        msg = super(ReplyForm, self).create_recipient_message(recipient, message)
        msg.replied_at = datetime.datetime.now()

        # find parent in recipient messages
        try:
            msg.parent_msg = Message.objects.get(
                owner=recipient,
                sender=message.recipient,
                recipient=message.sender,
                thread=message.thread)
        except (Message.DoesNotExist, Message.MultipleObjectsReturned):
            # message may be deleted 
            pass

        return msg


    def get_thread(self, message):
        return self.parent_message.thread

    def save(self, commit=True):
        instance, message_list = super(ReplyForm, self).save(commit=False)
        instance.replied_at = datetime.datetime.now()
        instance.parent_msg = self.parent_message
        if commit:
            instance.save()
            for msg in message_list:
                msg.save()
                if notification:
                    notification.send([msg.recipient],
                            "messages_reply_received", {
                                'message': msg,
                                'parent_msg': self.parent_message,
                                })
        return instance, message_list



########NEW FILE########
__FILENAME__ = management
from django.db.models import get_models, signals
from django.conf import settings
from django.utils.translation import ugettext_noop as _

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification

    def create_notice_types(app, created_models, verbosity, **kwargs):
        notification.create_notice_type("messages_received", _("Message Received"), _("you have received a message"), default=2)
        notification.create_notice_type("messages_reply_received", _("Reply Received"), _("you have received a reply to a message"), default=2)

    signals.post_syncdb.connect(create_notice_types, sender=notification)
else:
    print "Skipping creation of NoticeTypes as notification app not found"

########NEW FILE########
__FILENAME__ = models
import datetime
from django.db import models
from django.conf import settings
from django.db.models import signals
from django.db.models.query import QuerySet
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _


class MessageQueryset(QuerySet):
    def unread(self):
        return self.filter(unread=True)


class BaseMessageManager(models.Manager):
    def get_query_set(self):
        return MessageQueryset(self.model)
    
    def trash(self, messages):
        """
        move messages to trash
        """
        messages.update(deleted=True, deleted_at=datetime.datetime.now())

    def send(self, messages):
        """
        send messages
        """
        pass


class Inbox(BaseMessageManager):
    def get_query_set(self):
        return super(Inbox, self).get_query_set().filter(deleted=False)

    def for_user(self, user):
        """
        Returns all messages that were received by the given user and are not
        marked as deleted.
        """
        return self.get_query_set().filter(owner=user, recipient=user)


class Outbox(BaseMessageManager):
    def get_query_set(self):
        return super(Outbox, self).get_query_set().filter(deleted=False)

    def for_user(self, user):
        """
        Returns all messages that were sent by the given user and are not
        marked as deleted.
        """
        return self.get_query_set().filter(owner=user, sender=user)


class Trash(BaseMessageManager):
    """
    Trash manager
    """

    def get_query_set(self):
        return super(Trash, self).get_query_set().filter(deleted=True)

    def for_user(self, user):
        """
        Returns all messages that were either received or sent by the given
        user and are marked as deleted.
        """
        return self.get_query_set().filter(owner=user)


class Message(models.Model):
    """
    A private message from user to user
    """
    owner = models.ForeignKey(User, related_name='messages')
    to = models.CharField(max_length=255) # recipient usernames comma separated
    subject = models.CharField(_("Subject"), max_length=120)
    body = models.TextField(_("Body"))
    sender = models.ForeignKey(User, related_name='+', verbose_name=_("Sender"))
    recipient = models.ForeignKey(User, related_name='+', null=True, blank=True, verbose_name=_("Recipient"))
    thread = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    parent_msg = models.ForeignKey('self', related_name='next_messages', null=True, blank=True, verbose_name=_("Parent message"))
    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True)
    unread = models.BooleanField(default=True, db_index=True)
    read_at = models.DateTimeField(_("read at"), null=True, blank=True)
    replied_at = models.DateTimeField(_("replied at"), null=True, blank=True)
    deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(_("Sender deleted at"), null=True, blank=True)

    objects = BaseMessageManager()
    inbox = Inbox()
    outbox = Outbox()
    trash = Trash()
    
    def is_unread(self):
        """returns whether the recipient has read the message or not"""
        return bool(self.read_at is None)

    def undelete(self):
        self.deleted = False
        self.deleted_at = None

    def mark_read(self):
        self.unread = False
        self.read_at = datetime.datetime.now()

    def mark_unread(self):
        self.unread = True
        self.read_at = None

    def move_to_trash(self):
        self.deleted = True
        self.deleted_at = datetime.datetime.now()
        
    def replied(self):
        """returns whether the recipient has written a reply to this message"""
        return bool(self.replied_at is not None)
    
    def __unicode__(self):
        return self.subject

    def all_recipients(self):
        return User.objects.filter(username__in=self.to.split(','))
    
    @models.permalink
    def get_absolute_url(self):
        return ('messages_detail', None, {'message_id': self.pk})
    
    class Meta:
        ordering = ['-sent_at']
        verbose_name = _("Message")
        verbose_name_plural = _("Messages")
        db_table = 'messages_message'
        

def inbox_count_for(user):
    """
    returns the number of unread messages for the given user but does not
    mark them seen
    """
    return Message.inbox.for_user(user).unread().count()


# fallback for email notification if django-notification could not be found
if "notification" not in settings.INSTALLED_APPS:
    from django_messages.utils import new_message_email
    signals.post_save.connect(new_message_email, sender=Message)

########NEW FILE########
__FILENAME__ = signals

########NEW FILE########
__FILENAME__ = inbox
from django.template import Library, Node, TemplateSyntaxError
from django_messages.models import inbox_count_for

class InboxOutput(Node):
    def __init__(self, varname=None):
        self.varname = varname
        
    def render(self, context):
        try:
            user = context['user']
            count = inbox_count_for(user)
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
import datetime
from django.test import TestCase
from django.contrib.auth.models import User
from django_messages.models import Message

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
        self.msg1.sender_deleted_at = datetime.datetime.now()
        self.msg2.recipient_deleted_at = datetime.datetime.now()
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
        
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.views.generic.simple import redirect_to

from django_messages.views import *

urlpatterns = patterns('',
    url(r'^$', redirect_to, {'url': 'inbox/'}),
    url(r'^inbox/$', inbox, name='messages_inbox'),
    url(r'^outbox/$', outbox, name='messages_outbox'),
    url(r'^compose/$', compose, name='messages_compose'),
    url(r'^compose/(?P<recipient>[\+\w]+)/$', compose, name='messages_compose_to'),
    url(r'^reply/(?P<message_id>[\d]+)/$', reply, name='messages_reply'),
    url(r'^view/(?P<message_id>[\d]+)/$', view, name='messages_detail'),
    url(r'^delete/(?P<message_id>[\d]+)/$', delete, name='messages_delete'),
    url(r'^undelete/(?P<message_id>[\d]+)/$', undelete, name='messages_undelete'),
    url(r'^trash/$', trash, name='messages_trash'),
)

########NEW FILE########
__FILENAME__ = utils
# -*- coding:utf-8 -*-
import re

from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.encoding import force_unicode
from django.utils.text import wrap
from django.utils.translation import ugettext_lazy as _
from django.template import Context, loader
from django.template.loader import render_to_string

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
    return _(u"%(sender)s wrote:\n%(body)s") % {
        'sender': sender,
        'body': quote,
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

########NEW FILE########
__FILENAME__ = views
# -*- coding:utf-8 -*-
import datetime

from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_noop
from django.core.urlresolvers import reverse
from django.conf import settings

from django.db import transaction

from django.views.generic.list_detail import object_list, object_detail

from django_messages.models import Message
from django_messages.forms import ComposeForm, ReplyForm
from django_messages.utils import format_quote


@login_required
def message_list(request, queryset, paginate_by=25,
    extra_context=None, template_name=None):
    return object_list(request, queryset=queryset, paginate_by=paginate_by,
            extra_context=extra_context, template_name=template_name,
            template_object_name='message')
        

@login_required
def inbox(request, template_name='django_messages/inbox.html', **kw):
    """
    Displays a list of received messages for the current user.
    """
    kw['template_name'] = template_name
    queryset = Message.inbox.for_user(request.user)
    return message_list(request, queryset, **kw)


@login_required
def outbox(request, template_name='django_messages/outbox.html', **kw):
    """
    Displays a list of sent messages for the current user.
    """
    kw['template_name'] = template_name
    queryset = Message.outbox.for_user(request.user)
    return message_list(request, queryset, **kw)


@login_required
def trash(request, template_name='django_messages/trash.html', **kw):
    """
    Displays a list of deleted messages.
    """
    kw['template_name'] = template_name
    queryset = Message.trash.for_user(request.user)
    return message_list(request, queryset, **kw)


@login_required
@transaction.commit_on_success
def compose(request, recipient=None, form_class=ComposeForm,
        template_name='django_messages/compose.html', success_url=None,
        recipient_filter=None, extra_context=None):
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
        ``extra_context``: extra context dict
    """
    if request.method == "POST":
        form = form_class(request.user, data=request.POST,
                recipient_filter=recipient_filter)
        if form.is_valid():
            instance, message_list = form.save()
            Message.objects.send(message_list)
            messages.add_message(request, messages.SUCCESS, _(u"Message successfully sent."))
            return redirect(success_url or request.GET.get('next') or inbox)
    else:
        form = form_class(request.user, initial={'recipients': recipient})

    ctx = extra_context or {}
    ctx.update({
        'form': form,
        })

    return render_to_response(template_name, RequestContext(request, ctx))


@login_required
@transaction.commit_on_success
def reply(request, message_id, form_class=ReplyForm,
        template_name='django_messages/reply.html', success_url=None,
        recipient_filter=None, extra_context=None):
    """
    Prepares the ``form_class`` form for writing a reply to a given message
    (specified via ``message_id``). 
    """
    parent = get_object_or_404(Message, pk=message_id, owner=request.user)

    if request.method == "POST":
        form = form_class(request.user, parent, data=request.POST, 
                recipient_filter=recipient_filter)
        if form.is_valid():
            instance, message_list = form.save()
            Message.objects.send(message_list)
            messages.add_message(request, messages.SUCCESS, _(u"Message successfully sent."))
            return redirect(success_url or inbox)
    else:
        form = form_class(request.user, parent)

    ctx = extra_context or {}
    ctx.update({
        'form': form,
        })

    return render_to_response(template_name, 
            RequestContext(request, ctx))


@login_required
@transaction.commit_on_success
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
    
    message = get_object_or_404(Message, pk=message_id, owner=request.user)
    message.move_to_trash()
    message.save()
    messages.add_message(request, messages.SUCCESS, _(u"Message successfully deleted."))
    return redirect(request.GET.get('next') or success_url or inbox)


@login_required
@transaction.commit_on_success
def undelete(request, message_id, success_url=None):
    """
    Recovers a message from trash.
    """
    message = get_object_or_404(Message, pk=message_id, owner=request.user)
    message.undelete()
    message.save()

    message_view = inbox # should be dependent on message box (inbox,outbox)

    messages.add_message(request, messages.SUCCESS,
            _(u"Message successfully recovered."))
    return redirect(request.GET.get('next') or success_url or message_view)


@login_required
def view(request, message_id, template_name='django_messages/view.html',
        extra_context=None):
    """
    Shows a single message.``message_id`` argument is required.
    The user is only allowed to see the message, if he is either
    the sender or the recipient. If the user is not allowed a 404
    is raised.
    If the user is the recipient and the message is unread
    ``read_at`` is set to the current datetime.
    """
    message = get_object_or_404(Message, pk=message_id, owner=request.user)
    if message.is_unread():
        message.mark_read()
        message.save()
    ctx = extra_context or {}
    ctx.update({
        'message': message,
        })
    return render_to_response(template_name, RequestContext(request, ctx))


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
copyright = u'2009, Arne Brodowski'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.4'
# The full version, including alpha/beta/rc tags.
release = '0.4.3pre'

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
