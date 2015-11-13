__FILENAME__ = admin
from django.contrib import admin
from .models import Message

admin.site.register(Message)

########NEW FILE########
__FILENAME__ = backends
from django.core.mail import get_connection
from django.core.mail.backends.base import BaseEmailBackend
from .settings import FIRSTCLASS_EMAIL_BACKEND, FIRSTCLASS_MIDDLEWARE
from .utils import get_cls_by_name

class ProxyBackend(BaseEmailBackend):
    def __init__(self, **kwargs):
        self._backend = get_connection(FIRSTCLASS_EMAIL_BACKEND, **kwargs)
        super(EmailBackend, self).__init__(**kwargs)

    def send_messages(self, email_messages):
        messages = []

        for message in email_messages:
            for path in FIRSTCLASS_MIDDLEWARE:
                middleware = get_cls_by_name(path)()
                message = middleware.process_message(message)

            if message:
                messages.append(message)

        return self._backend.send_messages(messages)

EmailBackend = ProxyBackend

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

FIRSTCLASS_VIEWONLINE_AUTH = getattr(settings, 'FIRSTCLASS_VIEWONLINE_AUTH', False)

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

def anchor_to_text(attrs):
    text = attrs.get('href').strip()
    title = attrs.get('title', attrs.get('text', '')).strip()

    if text == title or not title:
        return text

    return '(%s) %s' % (title, text)

def image_to_text(attrs):
    text = attrs.get('src').strip()
    title = attrs.get('title', attrs.get('alt', '')).strip()

    if not title:
        return text

    return '%s: %s' % (title, text)

# Deprecated
FIRSTCLASS_TEXT_ANCHOR = getattr(settings, 'FIRSTCLASS_TEXT_ANCHOR', anchor_to_text)
FIRSTCLASS_TEXT_IMAGE = getattr(settings, 'FIRSTCLASS_TEXT_IMAGE', image_to_text)

FIRSTCLASS_PLAINTEXT_RULES = getattr(settings, 'FIRSTCLASS_PLAINTEXT_RULES', {
    'a': FIRSTCLASS_TEXT_ANCHOR,
    'img': FIRSTCLASS_TEXT_IMAGE,
})

########NEW FILE########
__FILENAME__ = models
import random
from django.db import models
from django_extensions.db.fields.json import JSONField

class Message(models.Model):
    key = models.CharField(max_length=40, primary_key=True)
    data = JSONField()

    @models.permalink
    def get_absolute_url(self):
        return ('view_message_online', (), {
            'key': self.key,
        })

    def save(self, *args, **kwargs):
        if not self.key:
            while True:
                try:
                    self.key = '%04x' % random.getrandbits(40 * 4)
                    super(Message, self).save(*args, **kwargs)
                except:
                    continue
                else:
                    return

        super(Message, self).save(*args, **kwargs)

    def __unicode__(self):
        return u"%s to %s" % (self.data['subject'], ', '.join(self.data['to']))

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

FIRSTCLASS_EMAIL_BACKEND = getattr(settings, 'FIRSTCLASS_EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
FIRSTCLASS_MIDDLEWARE = getattr(settings, 'FIRSTCLASS_MIDDLEWARE', (
    'firstclass.middleware.online.ViewOnlineMiddleware',
    'firstclass.middleware.alternative.MultiAlternativesMiddleware',
    'firstclass.middleware.text.PlainTextMiddleware',
))

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

urlpatterns = patterns('firstclass.views',
    url(r'^(?P<key>.{40})/$', 'view_message_online', name='view_message_online'),
)

########NEW FILE########
__FILENAME__ = utils
import sys, importlib

def get_cls_by_name(name, aliases={}, imp=None, package=None, sep='.', **kwargs):
    if not imp:
        imp = importlib.import_module

    if not isinstance(name, basestring):
        return name

    name = aliases.get(name) or name
    sep = ':' if ':' in name else sep

    module_name, _, cls_name = name.rpartition(sep)

    if not module_name and package:
        module_name = package

    try:
        module = imp(module_name, package=package, **kwargs)
    except ValueError, exc:
        raise ValueError("Couldn't import %r: %s" %
            (name, exc), sys.exc_info()[2])

    return getattr(module, cls_name)

def call_or_format(func, attrs):
    if hasattr(func, '__call__'):
        return func(attrs)

    return func % attrs

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import get_object_or_404, render_to_response
from django.contrib.auth.decorators import login_required
from django.http import Http404
from firstclass.middleware.online.settings import FIRSTCLASS_VIEWONLINE_AUTH
from .models import Message

def view_message_online(request, key, template='firstclass/message.html'):
    message = get_object_or_404(Message, key=key)

    if FIRSTCLASS_VIEWONLINE_AUTH:
        if request.user.email not in message.data['to']:
            raise Http404

    return render_to_response(template, {
        'message': message,
    })

if FIRSTCLASS_VIEWONLINE_AUTH:
    view_message_online = login_required(view_message_online)

########NEW FILE########
