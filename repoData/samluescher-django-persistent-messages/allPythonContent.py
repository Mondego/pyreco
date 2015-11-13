__FILENAME__ = admin
from persistent_messages.models import Message
from django.contrib import admin

class MessageAdmin(admin.ModelAdmin):
    list_display = ['level', 'user', 'from_user', 'subject', 'message', 'created', 'read', 'is_persistent']

admin.site.register(Message, MessageAdmin)

########NEW FILE########
__FILENAME__ = api
from persistent_messages import notify
from persistent_messages import constants 

def add_message(request, level, message, extra_tags='', fail_silently=False, subject='', user=None, email=False, from_user=None, expires=None, close_timeout=None):
    """
    """
    if email:
        notify.email(level, message, extra_tags, subject, user, from_user)
    return request._messages.add(level, message, extra_tags, subject, user, from_user, expires, close_timeout)

def info(request, message, extra_tags='', fail_silently=False, subject='', user=None, email=False, from_user=None, expires=None, close_timeout=None):
    """
    """
    level = constants.INFO
    return add_message(request, level, message, extra_tags, fail_silently, subject, user, email, from_user, expires, close_timeout)

def warning(request, message, extra_tags='', fail_silently=False, subject='', user=None, email=False, from_user=None, expires=None, close_timeout=None):
    """
    """
    level = constants.WARNING
    return add_message(request, level, message, extra_tags, fail_silently, subject, user, email, from_user, expires, close_timeout)

def debug(request, message, extra_tags='', fail_silently=False, subject='', user=None, email=False, from_user=None, expires=None, close_timeout=None):
    """
    """
    level = constants.DEBUG
    return add_message(request, level, message, extra_tags, fail_silently, subject, user, email, from_user, expires, close_timeout)

########NEW FILE########
__FILENAME__ = constants
DEBUG = 110
INFO = 120
SUCCESS = 125
WARNING = 130
ERROR = 140

DEFAULT_TAGS = {
    INFO: 'info',
    SUCCESS: 'success',
    WARNING: 'warning',
    ERROR: 'error',
}

PERSISTENT_MESSAGE_LEVELS = (INFO, SUCCESS, WARNING, ERROR)

########NEW FILE########
__FILENAME__ = models
import persistent_messages
from persistent_messages.constants import PERSISTENT_MESSAGE_LEVELS
from django.db import models
from django.contrib.auth.models import User 
from django.utils.encoding import force_unicode
from django.contrib import messages
from django.contrib.messages import utils
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_unicode

LEVEL_TAGS = utils.get_level_tags()

class Message(models.Model):
    user = models.ForeignKey(User, blank=True, null=True)
    from_user = models.ForeignKey(User, blank=True, null=True, related_name="from_user")
    subject = models.CharField(max_length=255, blank=True, default='')
    message = models.TextField()
    LEVEL_CHOICES = (
        (messages.DEBUG, 'DEBUG'),
        (messages.INFO, 'INFO'),
        (messages.SUCCESS, 'SUCCESS'),
        (messages.WARNING, 'WARNING'),
        (messages.ERROR, 'ERROR'),
        (persistent_messages.DEBUG, 'PERSISTENT DEBUG'),
        (persistent_messages.INFO, 'PERSISTENT INFO'),
        (persistent_messages.SUCCESS, 'PERSISTENT SUCCESS'),
        (persistent_messages.WARNING, 'PERSISTENT WARNING'),
        (persistent_messages.ERROR, 'PERSISTENT ERROR'),
    )
    level = models.IntegerField(choices=LEVEL_CHOICES)
    extra_tags = models.CharField(max_length=128)
    created = models.DateTimeField(auto_now_add=True)    
    modified = models.DateTimeField(auto_now=True)
    read = models.BooleanField(default=False)
    expires = models.DateTimeField(null=True, blank=True)
    close_timeout = models.IntegerField(null=True, blank=True)

    def is_persistent(self):
        return self.level in PERSISTENT_MESSAGE_LEVELS
    is_persistent.boolean = True
    
    def __eq__(self, other):
        return isinstance(other, Message) and self.level == other.level and \
                                              self.message == other.message
    def __unicode__(self):
        if self.subject:
            message = _('%(subject)s: %(message)s') % {'subject': self.subject, 'message': self.message}
        else:
            message = self.message
        return force_unicode(message)

    def _prepare_message(self):
        """
        Prepares the message for saving by forcing the ``message``
        and ``extra_tags`` and ``subject`` to unicode in case they are lazy translations.

        Known "safe" types (None, int, etc.) are not converted (see Django's
        ``force_unicode`` implementation for details).
        """
        self.subject = force_unicode(self.subject, strings_only=True)
        self.message = force_unicode(self.message, strings_only=True)
        self.extra_tags = force_unicode(self.extra_tags, strings_only=True)

    def save(self, *args, **kwargs):
        self._prepare_message()
        super(Message, self).save(*args, **kwargs)

    def _get_tags(self):
        label_tag = force_unicode(LEVEL_TAGS.get(self.level, ''),
                                  strings_only=True)
        extra_tags = force_unicode(self.extra_tags, strings_only=True)
   
        if (self.read):
            read_tag = "read"
        else:
            read_tag = "unread"
   
        if extra_tags and label_tag:
            return u' '.join([extra_tags, label_tag, read_tag])
        elif extra_tags:
            return u' '.join([extra_tags, read_tag])
        elif label_tag:
            return u' '.join([label_tag, read_tag])
        return read_tag
    tags = property(_get_tags)
    
########NEW FILE########
__FILENAME__ = notify
from django.core.mail import send_mail

def email(level, message, extra_tags, subject, user, from_user):
    if not user or not user.email:
        raise Exception('Function needs to be passed a `User` object with valid email address.')
    send_mail(subject, message, from_user.email if from_user else None, [user.email], fail_silently=False)

########NEW FILE########
__FILENAME__ = storage
from persistent_messages.models import Message
from persistent_messages.constants import PERSISTENT_MESSAGE_LEVELS
from django.contrib import messages 
from django.contrib.messages.storage.base import BaseStorage
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db.models import Q
import datetime

def get_user(request):
    if hasattr(request, 'user') and request.user.__class__ != AnonymousUser:
        return request.user
    else:
        return AnonymousUser()

"""
Messages need a primary key when being displayed so that they can be closed/marked as read by the user.
Hence, they need to be stored when being added. You can disable this, but then you'll only be able to 
close a message when it is displayed for the second time. 
"""
STORE_WHEN_ADDING = True

#@TODO USE FALLBACK 
class PersistentMessageStorage(FallbackStorage):

    def __init__(self, *args, **kwargs):
        super(PersistentMessageStorage, self).__init__(*args, **kwargs)
        self.non_persistent_messages = []
        self.is_anonymous = not get_user(self.request).is_authenticated()

    def _message_queryset(self, exclude_unread=True):
        qs = Message.objects.filter(user=get_user(self.request)).filter(Q(expires=None) | Q(expires__gt=datetime.datetime.now()))
        if exclude_unread:
            qs = qs.exclude(read=True)
        return qs

    def _get(self, *args, **kwargs):
        """
        Retrieves a list of stored messages. Returns a tuple of the messages
        and a flag indicating whether or not all the messages originally
        intended to be stored in this storage were, in fact, stored and
        retrieved; e.g., ``(messages, all_retrieved)``.
        """
        if not get_user(self.request).is_authenticated():
            return super(PersistentMessageStorage, self)._get(*args, **kwargs)
        messages = []
        for message in self._message_queryset():
            if not message.is_persistent():
                self.non_persistent_messages.append(message)
            messages.append(message)
        return (messages, True)

    def get_persistent(self):
        return self._message_queryset(exclude_unread=False).filter(level__in=PERSISTENT_MESSAGE_LEVELS)

    def get_persistent_unread(self):
        return self._message_queryset(exclude_unread=True).filter(level__in=PERSISTENT_MESSAGE_LEVELS)

    def count_unread(self):
        return self._message_queryset(exclude_unread=True).count()

    def count_persistent_unread(self):
        return self.get_persistent_unread().count()
        
    def _delete_non_persistent(self):
        for message in self.non_persistent_messages:
            message.delete()
        self.non_persistent_messages = []

    def __iter__(self):
        if not get_user(self.request).is_authenticated():
            return super(PersistentMessageStorage, self).__iter__()
        self.used = True
        messages = []
        messages.extend(self._loaded_messages)
        if self._queued_messages:
            messages.extend(self._queued_messages)
        return iter(messages)

    def _prepare_messages(self, messages):
        if not get_user(self.request).is_authenticated():
            return super(PersistentMessageStorage, self)._prepare_messages(messages)
        """
        Obsolete method since model takes care of this.
        """
        pass
        
    def _store(self, messages, response, *args, **kwargs):
        """
        Stores a list of messages, returning a list of any messages which could
        not be stored.

        If STORE_WHEN_ADDING is True, messages are already stored at this time and won't be
        saved again.
        """
        if not get_user(self.request).is_authenticated():
            return super(PersistentMessageStorage, self)._store(messages, response, *args, **kwargs)
        for message in messages:
            if not self.used or message.is_persistent():
                if not message.pk:
                    message.save()
        return []

    def update(self, response):
        if not get_user(self.request).is_authenticated():
            return super(PersistentMessageStorage, self).update(response)
        """
        Deletes all non-persistent, read messages. Saves all unstored messages.
        """
        if self.used:
            self._delete_non_persistent()
        return super(PersistentMessageStorage, self).update(response)

    def add(self, level, message, extra_tags='', subject='', user=None, from_user=None, expires=None, close_timeout=None):
        """
        Queues a message to be stored.

        The message is only queued if it contained something and its level is
        not less than the recording level (``self.level``).
        """
        to_user = user or get_user(self.request)
        if not to_user.is_authenticated():
            if Message(level=level).is_persistent():
                raise NotImplementedError('Persistent message levels cannot be used for anonymous users.')
            else:
                return super(PersistentMessageStorage, self).add(level, message, extra_tags)
        if not message:
            return
        # Check that the message level is not less than the recording level.
        level = int(level)
        if level < self.level:
            return
        # Add the message.
        message = Message(user=to_user, level=level, message=message, extra_tags=extra_tags, subject=subject, from_user=from_user, expires=expires, close_timeout=close_timeout)
        # Messages need a primary key when being displayed so that they can be closed/marked as read by the user.
        # Hence, save it now instead of adding it to queue:
        if STORE_WHEN_ADDING:
            message.save()
        else:
            self.added_new = True
            self._queued_messages.append(message)

########NEW FILE########
__FILENAME__ = message_filters
# coding=utf-8
from django import template  
 
def latest(queryset, count):
    return queryset.order_by('-created')[:count]

def latest_or_unread(queryset, count):
    count_unread = queryset.filter(read=False).count()
    if count_unread > count:
        count = count_unread
    return queryset.order_by('read', '-created')[:count]
    
register = template.Library()  
register.filter(latest)  
register.filter(latest_or_unread)
########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^detail/(?P<message_id>\d+)/$', 'persistent_messages.views.message_detail', name='message_detail'),
    url(r'^mark_read/(?P<message_id>\d+)/$', 'persistent_messages.views.message_mark_read', name='message_mark_read'),
    url(r'^mark_read/all/$', 'persistent_messages.views.message_mark_all_read', name='message_mark_all_read'),
)

########NEW FILE########
__FILENAME__ = views
from persistent_messages.models import Message
from persistent_messages.storage import get_user
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.core.exceptions import PermissionDenied

def message_detail(request, message_id):
    user = get_user(request)
    if not user.is_authenticated():
        raise PermissionDenied
    message = get_object_or_404(Message, user=user, pk=message_id)
    message.read = True
    message.save()
    return render_to_response('persistent_messages/message/detail.html', {'message': message}, 
        context_instance=RequestContext(request))

def message_mark_read(request, message_id):
    user = get_user(request)
    if not user.is_authenticated():
        raise PermissionDenied
    message = get_object_or_404(Message, user=user, pk=message_id)
    message.read = True
    message.save()
    if not request.is_ajax():
        return HttpResponseRedirect(request.META.get('HTTP_REFERER') or '/')
    else:
        return HttpResponse('')

def message_mark_all_read(request):
    user = get_user(request)
    if not user.is_authenticated():
        raise PermissionDenied
    Message.objects.filter(user=user).update(read=True)
    if not request.is_ajax():
        return HttpResponseRedirect(request.META.get('HTTP_REFERER') or '/')
    else:
        return HttpResponse('')

########NEW FILE########
