__FILENAME__ = admin
#encoding=utf8

from django.contrib import admin
from models import Room, Message


class RoomAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


class MessageAdmin(admin.ModelAdmin):
    pass


admin.site.register(Room, RoomAdmin)
admin.site.register(Message, MessageAdmin)

########NEW FILE########
__FILENAME__ = chat
# encoding: utf-8

import json
import itertools
from datetime import datetime, timedelta
from collections import deque

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import (HttpResponse,
                        HttpResponseBadRequest)
from django.utils.decorators import method_decorator

from gevent.event import Event

from ..models import Room
from ..signals import chat_message_received
from ..utils.auth import check_user_passes_test
from ..utils.decorators import ajax_user_passes_test_or_403
from ..utils.decorators import ajax_room_login_required
from ..utils.handlers import MessageHandlerFactory


TIME_FORMAT = '%Y-%m-%dT%H:%M:%S:%f'

TIMEOUT = 30
if settings.DEBUG:
    TIMEOUT = 3


class ChatView(object):
    """Returns a singleton of ChatView
    Methods dispatch all the ajax requests from chat

    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            self = super(ChatView, cls).__new__(cls, *args, **kwargs)
            ChatView.__init__(self, *args, **kwargs)
            cls._instance = self
        return cls._instance

    def __init__(self):
        """
        Defines dictionary attibutes sorted by room_id
        For each room:
        - new_message_events contains gevent.Event objects used by message
          handlers to pause/restart execution and implement long polling
        - messages stores the queue of the latest 50 messages
        - counters contains iterators to pick up message identifiers
        - connected_users is a dictionary holding the usernames of connected
          users sorted by the time of their latest request
        - new_connected_user_event contains gevent.Event objects used
          by self.notify_users_list and self.get_users_list methods to
          implement long polling

        """
        self.handler = MessageHandlerFactory()
        self.new_message_events = {}
        self.messages = {}
        self.counters = {}
        self.connected_users = {}
        self.new_connected_user_event = {}
        rooms = Room.objects.all()
        for room in rooms:
            self.new_message_events[room.id] = Event()
            self.messages[room.id] = deque(maxlen=50)
            self.counters[room.id] = itertools.count(1)
            self.connected_users[room.id] = {}
            self.new_connected_user_event[room.id] = Event()

    def get_username(self, request):
        """Returns username if user is authenticated, guest name otherwise """
        if request.user.is_authenticated():
            username = request.user.username
        else:
            guestname = request.session.get('guest_name')
            username = '(guest) %s' % guestname
        return username

    def signal_new_message_event(self, room_id):
        """Signals new_message_event given a room_id """
        self.new_message_events[room_id].set()
        self.new_message_events[room_id].clear()

    def wait_for_new_message(self, room_id, timeout=TIMEOUT):
        """Waits for new_message_event given a room_id """
        self.new_message_events[room_id].wait(timeout)

    def get_messages_queue(self, room_id):
        """Returns the message queue given a room_id """
        return self.messages[room_id]

    def get_next_message_id(self, room_id):
        """Returns the next message identifier given a room_id """
        return self.counters[room_id].next()

    def get_connected_users(self, room_id):
        """Returns the connected users given a room_id"""
        return self.connected_users[room_id]

    @method_decorator(ajax_room_login_required)
    @method_decorator(ajax_user_passes_test_or_403(check_user_passes_test))
    def get_messages(self, request):
        """Handles ajax requests for messages
        Requests must contain room_id and latest_id
        Delegates MessageHandler.retrieve_message method to return the list
        of messages

        """
        try:
            room_id = int(request.GET['room_id'])
            latest_msg_id = int(request.GET['latest_message_id'])
        except:
            return HttpResponseBadRequest(
            "Parameters missing or bad parameters. "
            "Expected a GET request with 'room_id' and 'latest_message_id' "
            "parameters")

        messages = self.handler.retrieve_messages(
                        self, room_id, latest_msg_id)

        to_jsonify = [
            {"message_id": msg_id,
             "username": message.username,
             "date": message.date.strftime(TIME_FORMAT),
             "content": message.content}
            for msg_id, message in messages
            if msg_id > latest_msg_id
        ]
        return HttpResponse(json.dumps(to_jsonify),
                            mimetype="application/json")

    @method_decorator(ajax_room_login_required)
    @method_decorator(ajax_user_passes_test_or_403(check_user_passes_test))
    def send_message(self, request):
        """Gets room_id and message from request and sends a
        chat_message_received signal

        """
        try:
            room_id = int(request.POST['room_id'])
            message = request.POST['message']
            date = datetime.now()
        except:
            return HttpResponseBadRequest(
            "Parameters missing or bad parameters"
            "Expected a POST request with 'room_id' and 'message' parameters")
        user = request.user
        username = self.get_username(request)
        chat_message_received.send(
            sender=self,
            room_id=room_id,
            username=username,
            message=message,
            date=date,
            user=user if user.is_authenticated() else None)

        return HttpResponse(json.dumps({
                 'timestamp': date.strftime(TIME_FORMAT), }
        ))

    @method_decorator(ajax_room_login_required)
    @method_decorator(ajax_user_passes_test_or_403(check_user_passes_test))
    def notify_users_list(self, request):
        """Updates user time into connected users dictionary """
        try:
            room_id = int(request.POST['room_id'])
        except:
            return HttpResponseBadRequest(
            "Parameters missing or bad parameters"
            "Expected a POST request with 'room_id'")
        username = self.get_username(request)
        date = datetime.today()
        self.connected_users[room_id].update({username: date})
        self.new_connected_user_event[room_id].set()
        self.new_connected_user_event[room_id].clear()
        return HttpResponse('Connected')

    @method_decorator(ajax_room_login_required)
    @method_decorator(ajax_user_passes_test_or_403(check_user_passes_test))
    def get_users_list(self, request):
        """Dumps the list of connected users """
        REFRESH_TIME = 8
        try:
            room_id = int(request.GET['room_id'])
        except:
            return HttpResponseBadRequest(
            "Parameters missing or bad parameters"
            "Expected a POST request with 'room_id'")
        username = self.get_username(request)
        self.connected_users[room_id].update({
                                username: datetime.today()
                            })
        self.new_connected_user_event[room_id].wait(REFRESH_TIME)

        # clean connected_users dictionary of disconnected users
        self._clean_connected_users(room_id)
        json_users = [
            {"username": _user,
             "date": _date.strftime(TIME_FORMAT)}
            for _user, _date in self.connected_users[room_id].iteritems()
        ]
        json_response = {
            "now": datetime.today().strftime(TIME_FORMAT),
            "users": json_users,
            "refresh": str(REFRESH_TIME),
        }
        return HttpResponse(json.dumps(json_response),
                            mimetype='application/json')

    @method_decorator(ajax_room_login_required)
    @method_decorator(ajax_user_passes_test_or_403(check_user_passes_test))
    def get_latest_message_id(self, request):
        """Dumps the id of the latest message sent """
        try:
            room_id = int(request.GET['room_id'])
        except:
            return HttpResponseBadRequest()
        latest_msg_id = self.handler.get_latest_message_id(self, room_id)
        response = {"id": latest_msg_id}
        return HttpResponse(json.dumps(response), mimetype="application/json")

    def _clean_connected_users(self, room_id, seconds=60):
        """Remove from connected users dictionary users not seen
        for seconds

        """
        now = datetime.today()
        for usr, date in self.connected_users[room_id].items():
            if (now - timedelta(seconds=seconds)) > date:
                self.connected_users[room_id].pop(usr)


@receiver(post_save, sender=Room)
def create_events_for_new_room(sender, **kwargs):
    """Creates an entry in Chat dictionary attributes
    when a new room is created

    """
    if kwargs.get('created'):
        instance = kwargs.get('instance')
        room_id = instance.id
        chatview = ChatView()
        chatview.new_message_events[room_id] = Event()
        chatview.messages[room_id] = deque(maxlen=50)
        chatview.counters[room_id] = itertools.count(1)
        chatview.connected_users[room_id] = {}
        chatview.new_connected_user_event[room_id] = Event()

########NEW FILE########
__FILENAME__ = guest
from django import forms


class GuestNameForm(forms.Form):
    guest_name = forms.CharField(max_length=20)
    room_slug = forms.SlugField(widget=forms.HiddenInput())

########NEW FILE########
__FILENAME__ = run_gevent
from gevent import monkey
monkey.patch_all()

from django.core.management.commands import runserver


class Command(runserver.BaseRunserverCommand):
    def handle(self, *args, **options):
        """Apply gevent monkey patch and calls default runserver handler
        """
        super(Command, self).handle(*args, **options)

########NEW FILE########
__FILENAME__ = test_gevent
from gevent import monkey
from gevent import __version__ as gevent_version
monkey.patch_all()

from django.core.management.commands import test


class Command(test.Command):
    def handle(self, *args, **kw):
        print "using GEvent %s" % gevent_version
        super(Command, self).handle(*args, **kw)

########NEW FILE########
__FILENAME__ = models
#encoding=utf8

from django.db import models
from django.contrib.auth.models import User

from polymorphic import PolymorphicModel


class Room(PolymorphicModel):
    name = models.CharField(max_length=64, unique=True)
    slug = models.SlugField()
    description = models.TextField()
    subscribers = models.ManyToManyField(User, blank=True)
    allow_anonymous_access = models.NullBooleanField()
    private = models.NullBooleanField()
    password = models.CharField(max_length=32, blank=True)

    def __unicode__(self):
        return u"%s" % self.name

    @models.permalink
    def get_absolute_url(self):
        return ('room_view', [self.slug])


class Message(PolymorphicModel):
    user = models.ForeignKey(User, null=True)
    # username field is useful to store guest name of unauthenticated users
    username = models.CharField(max_length=20)
    date = models.DateTimeField()
    room = models.ForeignKey(Room)
    content = models.CharField(max_length=5000)

########NEW FILE########
__FILENAME__ = signals
from utils.handlers import MessageHandlerFactory
from django.dispatch import Signal


chat_message_received = Signal(
    providing_args=[
        "room_id",
        "username",
        "message",
        "date",
])

handler = MessageHandlerFactory()

chat_message_received.connect(handler.handle_received_message)

########NEW FILE########
__FILENAME__ = tests
import json
import urlparse

from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import Client

from chatrooms.ajax.chat import ChatView
from chatrooms.models import Room
from chatrooms.utils.auth import get_login_url


class ChatroomsTest(TestCase):
    def setUp(self):
        # creates a user
        self.username = 'john'
        self.userpwd = 'johnpasswd'
        self.useremail = 'john@beatles.com'
        self.user = User.objects.create_user(
                            username=self.username,
                            password=self.userpwd,
                            email=self.useremail)
        self.user.save()

    def test_chatview_attributes(self):
        """Asserts new items are added to ChatView instance
        when a new room is created, and these items are removed
        when a room is deleted

        """
        new_room = Room(name="New room",
                        slug="new-room")
        new_room.save()
        chatview = ChatView()
        self.assertIn(new_room.id, chatview.new_message_events)
        self.assertIn(new_room.id, chatview.messages)
        self.assertIn(new_room.id, chatview.connected_users)
        self.assertIn(new_room.id, chatview.counters)
        self.assertIn(new_room.id, chatview.new_connected_user_event)

        # works without a post_delete handler: somewhere the Django models
        #  collector gets rid of these items (awkward, not documented feat)
        new_room.delete()
        self.assertNotIn(new_room.id, chatview.new_message_events)
        self.assertNotIn(new_room.id, chatview.messages)
        self.assertNotIn(new_room.id, chatview.connected_users)
        self.assertNotIn(new_room.id, chatview.counters)
        self.assertNotIn(new_room.id, chatview.new_connected_user_event)

    def test_anonymous_access(self):
        anon_room = Room(
                        allow_anonymous_access=True,
                        name="Anonymous Room",
                        slug="anonymous-room")
        login_req_room = Room(
                        allow_anonymous_access=False,
                        name="Login required room",
                        slug="login-required-room")
        anon_room.save()
        login_req_room.save()

        client = Client()

        response = client.get(login_req_room.get_absolute_url())
        # a login view may not have been implemented, so assertRedirects fails
        self.assertEquals(response.status_code, 302)
        url = response['Location']
        expected_url = get_login_url(login_req_room.get_absolute_url())
        e_scheme, e_netloc, e_path, e_query, e_fragment = urlparse.urlsplit(
                                                                expected_url)
        if not (e_scheme or e_netloc):
            expected_url = urlparse.urlunsplit(('http', 'testserver', e_path,
                e_query, e_fragment))
        self.assertEquals(url, expected_url)

        response = client.get(
            anon_room.get_absolute_url(),
            follow=True)

        # assert redirect
        self.assertRedirects(
            response,
            'http://testserver/chat/setguestname/?room_slug=anonymous-room')

        # post guestname
        guestname_posted = client.post(
            response.redirect_chain[0][0],
            {'guest_name': 'guest',
             'room_slug': 'anonymous-room'},
            follow=True)
        self.assertRedirects(
            guestname_posted,
            anon_room.get_absolute_url()
        )

    def test_get_messages(self, *args, **kwargs):
        username, password = self.username, self.userpwd

        # login user
        client = Client()
        client.login(username=username, password=password)

        # creates a room
        room = Room()
        room.save()

        # message queue empty: check last_message_id
        response = client.get('/chat/get_latest_msg_id/?room_id=%d' % room.id)
        json_response = json.loads(response.content)
        last_msg_id = json_response['id']
        self.assertEquals(last_msg_id, -1)

        # posts a message
        post_response = client.post('/chat/send_message/',
                                {'room_id': room.pk,
                                 'message': 'ABCD'},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEquals(post_response.status_code, 200)
        json_response = json.loads(post_response.content)
        timestamp = json_response['timestamp']

        # gets list of messages
        response = client.get(
            '/chat/get_messages/?room_id=%d&latest_message_id=%d' % (
                                                room.id, last_msg_id),
                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEquals(response.status_code, 200)
        json_response = json.loads(response.content)

        expected_json = [{u'message_id': 1,
                          u'username': u'john',
                          u'date': timestamp,
                          u'content': u'ABCD', }]
        self.assertEquals(expected_json, json_response)

        # check last_message_id
        response = client.get('/chat/get_latest_msg_id/?room_id=%d' % room.id)
        json_response = json.loads(response.content)
        last_msg_id = json_response['id']
        self.assertEquals(last_msg_id, 1)

########NEW FILE########
__FILENAME__ = urls
#encoding=utf8

from django.conf.urls.defaults import url, patterns

from . import views
from .utils.decorators import room_check_access
from .ajax import chat

urlpatterns = patterns('chatrooms',
    # room views
    url(r'^rooms/$',
        views.RoomsListView.as_view(),
        name="rooms_list"),
    url(r'^room/(?P<slug>[-\w\d]+)/$',
        room_check_access(views.RoomView.as_view()),
        name="room_view"),
    url(r'^setguestname/$',
        views.GuestNameView.as_view(),
        name="set_guestname"),

    # ajax requests
    url(r'^get_messages/', chat.ChatView().get_messages),
    url(r'^send_message/', chat.ChatView().send_message),
    url(r'^get_latest_msg_id/', chat.ChatView().get_latest_message_id),
    url(r'^get_users_list/$', chat.ChatView().get_users_list),
    url(r'^notify_users_list/$', chat.ChatView().notify_users_list),
)

########NEW FILE########
__FILENAME__ = auth
#encoding=utf8
import urlparse

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import ImproperlyConfigured
from django.http import QueryDict

from django_load.core import load_object


def get_login_url(next, login_url=None,
                      redirect_field_name=REDIRECT_FIELD_NAME):
    """Returns the full login_url with next parameter set """
    if not login_url:
        login_url = settings.LOGIN_URL

    login_url_parts = list(urlparse.urlparse(login_url))
    if redirect_field_name:
        querystring = QueryDict(login_url_parts[4], mutable=True)
        querystring[redirect_field_name] = next
        login_url_parts[4] = querystring.urlencode(safe='/')

    return urlparse.urlunparse(login_url_parts)


def get_test_user_function():
    """
    Returns the function set on settings.CHATROOMS_TEST_USER_FUNCTION
    if any, else returns False

    """
    if hasattr(settings, 'CHATROOMS_TEST_USER_FUNCTION'):
        try:
            return load_object(settings.CHATROOMS_TEST_USER_FUNCTION)
        except (ImportError, TypeError):
            raise ImproperlyConfigured(
                "The variable set as settings.CHATROOMS_TEST_USER_FUNCTION "
                "is not a module or the path is not correct"
            )
    return False

test_user_function = get_test_user_function()


def check_user_passes_test(request, user):
    """
    Returns the test_user_function if any,
    else returns True

    """
    if test_user_function:
        return test_user_function(request, user)
    return True

########NEW FILE########
__FILENAME__ = celery_handlers
#encoding=utf8

from celery.app import app_or_default
from celery.events import Event

from django.db.models import Max

from .handlers import MessageHandler
from ..models import Room, Message


class CeleryMessageHandler(MessageHandler):
    """Custom MessageHandler class using celery
    for synchronization
    """
    def __init__(self):
        """Initializes celery events and dispatchers
        """
        self.app = app_or_default()
        self.event = Event(type='chatrooms')
        self.dispatcher = self.app.events.Dispatcher(
                            connection=self.app.broker_connection(),
                            enabled=True)

    def handle_received_message(self,
        sender, room_id, username, message, date, **kwargs):
        """
        1. saves the message
        2. sends the event

        """

        room = Room.objects.get(id=room_id)
        fields = {
            'room': room,
            'date': date,
            'content': message,
            'username': username,
        }
        user = kwargs.get('user')
        if user:
            fields['user'] = user
        # 1
        new_message = Message(**fields)
        new_message.save()

        # 2
        self.dispatcher.send(type='chatrooms')

    def retrieve_messages(self, chatobj, room_id, latest_msg_id, **kwargs):
        """
        1. waits for "chatrooms" event
        2. returns the messages with id greater than latest_msg_id

        """
        def handler(*args, **kwargs):
            pass

        receiver = self.app.events.Receiver(
                    connection=self.app.broker_connection(),
                    handlers={"chatrooms": handler, })
        try:
            # 1
            receiver.capture(limit=1, timeout=20, wakeup=True)
        except:  # Timeout
            pass
        # 2
        messages = Message.objects.filter(room=room_id, id__gt=latest_msg_id)
        return [(msg.pk, msg) for msg in messages]

    def get_latest_message_id(self, chatobj, room_id):
        """Returns id of the latest message received """
        latest_msg_id = Message.objects.filter(
                        room=room_id).aggregate(
                        max_id=Max('id')).get('max_id')
        if not latest_msg_id:
            latest_msg_id = -1
        return latest_msg_id

########NEW FILE########
__FILENAME__ = decorators
#encoding=utf8

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import (HttpResponse,
                         HttpResponseForbidden,
                         HttpResponseRedirect)
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.decorators import available_attrs
from django.utils.functional import wraps

from ..models import Room


def ajax_user_passes_test_or_403(test_func, message="Access denied"):
    """
    Decorator for views that checks if the user passes the given test_func,
    raising 403 if it doesn't.
    If the request is ajax returns a 403 response with a message,
    else renders a 403.html template.
    The test should be a callable that takes a user object and
    returns True if the user passes.

    """
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request, request.user):
                return view_func(request, *args, **kwargs)
            # returns an HttpResponseForbidden if request is ajax
            if request.is_ajax:
                return HttpResponseForbidden(message)
            # else returns the 403 page
            ctx = RequestContext(request)
            resp = render_to_response('403.html', context_instance=ctx)
            resp.status_code = 403
            return resp
        return _wrapped_view
    return decorator


def ajax_room_login_required(view_func):
    """Handle non-authenticated users differently if it is an AJAX request
    If the ``allow_anonymous_access`` is set, allows access to anonymous

    """
    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
        room_id = request.REQUEST.get('room_id')
        if room_id:
            room = get_object_or_404(Room, pk=room_id)
            if room.allow_anonymous_access:
                return view_func(request, *args, **kwargs)
        if request.is_ajax():
            if request.user.is_authenticated():
                return view_func(request, *args, **kwargs)
            else:
                response = HttpResponse()
                response['X-Django-Requires-Auth'] = True
                response['X-Django-Login-Url'] = settings.LOGIN_URL
                return response
        else:
            return login_required(view_func)(request, *args, **kwargs)
    return _wrapped_view


def room_check_access(view_func):
    """Decorator for RoomView detailed view.
    Deny access to unauthenticated users if room doesn't allow anon access
    Shows a form to set a guest user name if the room allows access
    to not authenticated users and the guest_name has not yet been set
    for the current session

    """
    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
        room_slug = kwargs.get('slug')
        room = get_object_or_404(Room, slug=room_slug)
        if request.user.is_authenticated():
            return view_func(request, *args, **kwargs)
        elif room.allow_anonymous_access:
            if not request.session.get('guest_name'):
                return HttpResponseRedirect(
                    # TODO: use django.http.QueryDict
                    reverse('set_guestname') + '?room_slug=%s' % room_slug)
            return view_func(request, *args, **kwargs)
        return login_required(view_func)(request, *args, **kwargs)
    return _wrapped_view


def signals_new_message_at_end(func):
    """Decorator for MessageHandler.handle_received_message method
    """
    @wraps(func, assigned=available_attrs(func))
    def _wrapper(self, sender, room_id, username, message, date, **kwargs):
        f = func(self, sender, room_id, username, message, date, **kwargs)
        sender.signal_new_message_event(room_id)
        return f
    return _wrapper


def waits_for_new_message_at_start(func):
    """Decorator for MessageHandler.retrieve_messages method
    """
    @wraps(func, assigned=available_attrs(func))
    def _wrapper(self, chatobj, room_id, *args, **kwargs):
        chatobj.wait_for_new_message(room_id)
        return func(self, chatobj, room_id, *args, **kwargs)
    return _wrapper

########NEW FILE########
__FILENAME__ = examples
from django.core.exceptions import ObjectDoesNotExist


def check_user_is_subscribed(request, user):
    """
    Example of function settable as settings.CHATROOMS_TEST_USER_FUNCTION
    Takes request and user as arguments
    Returns True if the request user is subscribed to the request chat room,
    False otherwise

    """
    room_id = request.GET['room_id']
    try:
        user.room_set.get(pk=room_id)
        return True
    except ObjectDoesNotExist:
        return False

########NEW FILE########
__FILENAME__ = handlers
#encoding=utf8

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django_load.core import load_object

from .decorators import (signals_new_message_at_end,
                        waits_for_new_message_at_start)
from ..models import Room, Message


class MessageHandler(object):
    """
    Class which implements two methods:
    - handle_received_message
    is designated to handle the "chat_message_received" signal
    - retrieve_messages
    is designated to return the list of messages sent to chat room so far

    ``handle_received_message`` method is designed to perform operations
    with the received message such that ``retrieve_messages`` is able to
    retrieve it afterwards.

    These methods are responsible for long polling implementation:
    ``retrieve_messages`` waits for new_message_event at its start,
    ``handle_received_message`` signals new_message_event at its end.

    The handlers can be customized and replaced extending this class
    and setting the full path name of the extending class
    into settings.CHATROOMS_HANDLERS_CLASS
    """

    @signals_new_message_at_end
    def handle_received_message(self,
        sender, room_id, username, message, date, **kwargs):
        """
        Default handler for the message_received signal.
        1 - Saves an instance of message to db
        2 - Appends a tuple (message_id, message_obj)
            to the sender.messages queue
        3 - Signals the "New message" event on the sender (decorator)
        4 - Returns the created message

        """
        room = Room.objects.get(id=room_id)
        fields = {
            'room': room,
            'date': date,
            'content': message,
            'username': username,
        }
        user = kwargs.get('user')
        if user:
            fields['user'] = user
        # 1
        new_message = Message(**fields)
        new_message.save()

        # 2
        msg_number = sender.get_next_message_id(room_id)
        messages_queue = sender.get_messages_queue(room_id)
        messages_queue.append((msg_number, new_message))

        # 3 - decorator does
        # sender.signal_new_message_event(room_id)

        # 4
        return new_message

    @waits_for_new_message_at_start
    def retrieve_messages(self, chatobj, room_id, latest_msg_id, **kwargs):
        """
        Returns a list of tuples like:
        [(message_id, message_obj), ...]
        Where message_obj is an instance of Message or an object with
        the attributes 'username', 'date' and 'content' at least

        1 - Waits for new_message_event (decorator)
        2 - returns the queue of messages stored in
        the ChatView.message dictionary by self.handle_received_message

        """
        # 1 - decorator does
        # chatobj.wait_for_new_message(room_id)

        # 2
        return chatobj.get_messages_queue(room_id)

    def get_latest_message_id(self, chatobj, room_id):
        """Returns id of the latest message received """
        latest_msg_id = -1
        msgs_queue = chatobj.messages[room_id]
        if msgs_queue:
            latest_msg_id = msgs_queue[-1][0]
        return latest_msg_id


class MessageHandlerFactory(object):
    """
    Returns a (singleton) instance of the class set as
    settings.CHATROOMS_HANDLERS_CLASS
    if any, else returns an instance of MessageHandler

    """
    _instance = None

    def __new__(cls):
        klass = MessageHandler
        if hasattr(settings, 'CHATROOMS_HANDLERS_CLASS'):
            try:
                klass = load_object(settings.CHATROOMS_HANDLERS_CLASS)
            except (ImportError, TypeError) as exc:
                raise ImproperlyConfigured(
                    "An error occurred while loading the "
                    "CHATROOMS_HANDLERS_CLASS: %s" % exc
                )

        if not cls._instance:
            cls._instance = klass()
        return cls._instance

########NEW FILE########
__FILENAME__ = redis_handlers
#encoding=utf8
import redis

from django.db.models import Max

from .handlers import MessageHandler
from ..models import Room, Message


class RedisMessageHandler(MessageHandler):
    """Custom MessageHandler class using redis
    for synchronization
    """
    def __init__(self):
        """Initializes redis connection
        """
        self.client = redis.Redis()
        self.pubsub = self.client.pubsub()

    def handle_received_message(self,
        sender, room_id, username, message, date, **kwargs):
        """
        1. saves the message
        2. publish a message to the redis client

        """

        room = Room.objects.get(id=room_id)
        fields = {
            'room': room,
            'date': date,
            'content': message,
            'username': username,
        }
        user = kwargs.get('user')
        if user:
            fields['user'] = user
        # 1
        new_message = Message(**fields)
        new_message.save()

        # 2
        self.client.publish('chatrooms', 'new message')

    def retrieve_messages(self, chatobj, room_id, latest_msg_id, **kwargs):
        """
        1. waits for "new message" on redis
        2. returns the list of latest messages

        """
        client = redis.Redis(socket_timeout=20)
        pubsub = client.pubsub()
        pubsub.subscribe('chatrooms')
        # 1
        msg = pubsub.listen().next()  # TODO: timeout?
        pubsub.unsubscribe('chatrooms')
        # 2
        messages = Message.objects.filter(room=room_id, id__gt=latest_msg_id)
        return [(msg.pk, msg) for msg in messages]

    def get_latest_message_id(self, chatobj, room_id):
        """Returns id of the latest message received """
        latest_msg_id = Message.objects.filter(
                        room=room_id).aggregate(
                        max_id=Max('id')).get('max_id')
        if not latest_msg_id:
            latest_msg_id = -1
        return latest_msg_id

########NEW FILE########
__FILENAME__ = views
#encoding=utf8

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.generic import ListView, DetailView, FormView

from .utils.auth import get_login_url
from .forms.guest import GuestNameForm
from .models import Room


class RoomsListView(ListView):
    """View to show the list of rooms available """
    context_object_name = "rooms"
    template_name = "chatrooms/rooms_list.html"
    paginate_by = 20

    def get_queryset(self):
        filters = {}
        if self.request.user.is_anonymous():
            filters['allow_anonymous_access'] = True
        return Room.objects.filter(**filters)


class RoomView(DetailView):
    """View for the single room """
    model = Room
    context_object_name = 'room'
    template_name = "chatrooms/room.html"


class GuestNameView(FormView):
    """Shows the form to choose a guest name to anonymous users """
    form_class = GuestNameForm
    template_name = 'chatrooms/guestname_form.html'

    def get_context_data(self, **kwargs):
        kwargs.update(super(GuestNameView, self).get_context_data(**kwargs))
        room_slug = self.request.GET.get('room_slug')
        next = ''
        if room_slug:
            next = reverse('room_view', kwargs={'slug': room_slug})
        kwargs['login_url'] = get_login_url(next)
        return kwargs

    def get_initial(self):
        init = super(GuestNameView, self).get_initial()
        room_slug = self.request.GET.get('room_slug')
        if room_slug:
            init.update(room_slug=room_slug)
        return init

    def form_valid(self, form):
        guest_name = form.cleaned_data.get('guest_name')
        room_slug = form.cleaned_data.get('room_slug')
        self.request.session['guest_name'] = guest_name
        if room_slug:
            redirect_url = reverse('room_view', kwargs={'slug': room_slug})
        else:
            redirect_url = reverse('rooms_list')
        return HttpResponseRedirect(redirect_url)

########NEW FILE########
