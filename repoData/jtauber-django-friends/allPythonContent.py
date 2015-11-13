__FILENAME__ = admin
from django.contrib import admin

from friends.models import Contact
from friends.models import Friendship, FriendshipInvitation, FriendshipInvitationHistory
from friends.models import JoinInvitation


class ContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'user', 'added')


class FriendshipAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_user', 'to_user', 'added',)


class JoinInvitationAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_user', 'contact', 'status')


class FriendshipInvitationAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_user', 'to_user', 'sent', 'status',)


class FriendshipInvitationHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_user', 'to_user', 'sent', 'status',)


admin.site.register(Contact, ContactAdmin)
admin.site.register(Friendship, FriendshipAdmin)
admin.site.register(JoinInvitation, JoinInvitationAdmin)
admin.site.register(FriendshipInvitation, FriendshipInvitationAdmin)
admin.site.register(FriendshipInvitationHistory, FriendshipInvitationHistoryAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.conf import settings

from django.contrib.auth.models import User

from friends.models import *

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None

if "emailconfirmation" in settings.INSTALLED_APPS:
    from emailconfirmation.models import EmailAddress
else:
    EmailAddress = None


class UserForm(forms.Form):
    
    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super(UserForm, self).__init__(*args, **kwargs)


if EmailAddress:
    class JoinRequestForm(forms.Form):
        
        email = forms.EmailField(label="Email", required=True, widget=forms.TextInput(attrs={'size':'30'}))
        message = forms.CharField(label="Message", required=False, widget=forms.Textarea(attrs = {'cols': '30', 'rows': '5'}))
        
        def clean_email(self):
            # @@@ this assumes email-confirmation is being used
            self.existing_users = EmailAddress.objects.get_users_for(self.cleaned_data["email"])
            if self.existing_users:
                raise forms.ValidationError(u"Someone with that email address is already here.")
            return self.cleaned_data["email"]
        
        def save(self, user):
            join_request = JoinInvitation.objects.send_invitation(user, self.cleaned_data["email"], self.cleaned_data["message"])
            user.message_set.create(message="Invitation to join sent to %s" % join_request.contact.email)
            return join_request


class InviteFriendForm(UserForm):
    
    to_user = forms.CharField(widget=forms.HiddenInput)
    message = forms.CharField(label="Message", required=False, widget=forms.Textarea(attrs = {'cols': '20', 'rows': '5'}))
    
    def clean_to_user(self):
        to_username = self.cleaned_data["to_user"]
        try:
            User.objects.get(username=to_username)
        except User.DoesNotExist:
            raise forms.ValidationError(u"Unknown user.")
            
        return self.cleaned_data["to_user"]
    
    def clean(self):
        to_user = User.objects.get(username=self.cleaned_data["to_user"])
        previous_invitations_to = FriendshipInvitation.objects.invitations(to_user=to_user, from_user=self.user)
        if previous_invitations_to.count() > 0:
            raise forms.ValidationError(u"Already requested friendship with %s" % to_user.username)
        # check inverse
        previous_invitations_from = FriendshipInvitation.objects.invitations(to_user=self.user, from_user=to_user)
        if previous_invitations_from.count() > 0:
            raise forms.ValidationError(u"%s has already requested friendship with you" % to_user.username)
        return self.cleaned_data
    
    def save(self):
        to_user = User.objects.get(username=self.cleaned_data["to_user"])
        message = self.cleaned_data["message"]
        invitation = FriendshipInvitation(from_user=self.user, to_user=to_user, message=message, status="2")
        invitation.save()
        if notification:
            notification.send([to_user], "friends_invite", {"invitation": invitation})
            notification.send([self.user], "friends_invite_sent", {"invitation": invitation})
        self.user.message_set.create(message="Friendship requested with %s" % to_user.username) # @@@ make link like notification
        return invitation

########NEW FILE########
__FILENAME__ = importer
from django.conf import settings
from django.utils import simplejson as json

import gdata.contacts.service
import vobject
import ybrowserauth

from friends.models import Contact


def import_vcards(stream, user):
    """
    Imports the given vcard stream into the contacts of the given user.
    
    Returns a tuple of (number imported, total number of cards).
    """
    
    total = 0
    imported = 0
    for card in vobject.readComponents(stream):
        total += 1
        try:
            name = card.fn.value
            email = card.email.value
            try:
                Contact.objects.get(user=user, email=email)
            except Contact.DoesNotExist:
                Contact(user=user, name=name, email=email).save()
                imported += 1
        except AttributeError:
            pass # missing value so don't add anything
    return imported, total


def import_yahoo(bbauth_token, user):
    """
    Uses the given BBAuth token to retrieve a Yahoo Address Book and
    import the entries with an email address into the contacts of the
    given user.
    
    Returns a tuple of (number imported, total number of entries).
    """
    
    ybbauth = ybrowserauth.YBrowserAuth(settings.BBAUTH_APP_ID, settings.BBAUTH_SHARED_SECRET)
    ybbauth.token = bbauth_token
    address_book_json = ybbauth.makeAuthWSgetCall("http://address.yahooapis.com/v1/searchContacts?format=json&email.present=1&fields=name,email")
    address_book = json.loads(address_book_json)
    
    total = 0
    imported = 0
    
    for contact in address_book["contacts"]:
        total += 1
        email = contact['fields'][0]['data']
        try:
            first_name = contact['fields'][1]['first']
        except (KeyError, IndexError):
            first_name = None
        try:
            last_name = contact['fields'][1]['last']
        except (KeyError, IndexError):
            last_name = None
        if first_name and last_name:
            name = first_name + " " + last_name
        elif first_name:
            name = first_name
        elif last_name:
            name = last_name
        else:
            name = None
        try:
            Contact.objects.get(user=user, email=email)
        except Contact.DoesNotExist:
            Contact(user=user, name=name, email=email).save()
            imported += 1
    
    return imported, total


def import_google(authsub_token, user):
    """
    Uses the given AuthSub token to retrieve Google Contacts and
    import the entries with an email address into the contacts of the
    given user.
    
    Returns a tuple of (number imported, total number of entries).
    """
    
    contacts_service = gdata.contacts.service.ContactsService()
    contacts_service.auth_token = authsub_token
    contacts_service.UpgradeToSessionToken()
    entries = []
    feed = contacts_service.GetContactsFeed()
    entries.extend(feed.entry)
    next_link = feed.GetNextLink()
    while next_link:
        feed = contacts_service.GetContactsFeed(uri=next_link.href)
        entries.extend(feed.entry)
        next_link = feed.GetNextLink()
    total = 0
    imported = 0
    for entry in entries:
        name = entry.title.text
        for e in entry.email:
            email = e.address
            total += 1
            try:
                Contact.objects.get(user=user, email=email)
            except Contact.DoesNotExist:
                Contact(user=user, name=name, email=email).save()
                imported += 1
    return imported, total

########NEW FILE########
__FILENAME__ = management
from django.conf import settings
from django.db.models import signals
from django.utils.translation import ugettext_noop as _


if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
    
    def create_notice_types(app, created_models, verbosity, **kwargs):
        notification.create_notice_type("friends_invite", _("Invitation Received"), _("you have received an invitation"), default=2)
        notification.create_notice_type("friends_invite_sent", _("Invitation Sent"), _("you have sent an invitation"), default=1)
        notification.create_notice_type("friends_accept", _("Acceptance Received"), _("an invitation you sent has been accepted"), default=2)
        notification.create_notice_type("friends_accept_sent", _("Acceptance Sent"), _("you have accepted an invitation you received"), default=1)
        notification.create_notice_type("friends_otherconnect", _("Other Connection"), _("one of your friends has a new connection"), default=2)
        notification.create_notice_type("join_accept", _("Join Invitation Accepted"), _("an invitation you sent to join this site has been accepted"), default=2)
    
    signals.post_syncdb.connect(create_notice_types, sender=notification)
else:
    print "Skipping creation of NoticeTypes as notification app not found"

########NEW FILE########
__FILENAME__ = models
import datetime

from random import random

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import signals
from django.template.loader import render_to_string
from django.utils.hashcompat import sha_constructor

from django.contrib.sites.models import Site
from django.contrib.auth.models import User

# favour django-mailer but fall back to django.core.mail
if "mailer" in settings.INSTALLED_APPS:
    from mailer import send_mail
else:
    from django.core.mail import send_mail

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None

if "emailconfirmation" in settings.INSTALLED_APPS:
    from emailconfirmation.models import EmailAddress
else:
    EmailAddress = None


class Contact(models.Model):
    """
    A contact is a person known by a user who may or may not themselves
    be a user.
    """
    
    # the user who created the contact
    user = models.ForeignKey(User, related_name="contacts")
    
    name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField()
    added = models.DateField(default=datetime.date.today)
    
    # the user(s) this contact correspond to
    users = models.ManyToManyField(User)
    
    def __unicode__(self):
        return "%s (%s's contact)" % (self.email, self.user)


class FriendshipManager(models.Manager):
    
    def friends_for_user(self, user):
        friends = []
        for friendship in self.filter(from_user=user).select_related(depth=1):
            friends.append({"friend": friendship.to_user, "friendship": friendship})
        for friendship in self.filter(to_user=user).select_related(depth=1):
            friends.append({"friend": friendship.from_user, "friendship": friendship})
        return friends
    
    def are_friends(self, user1, user2):
        if self.filter(from_user=user1, to_user=user2).count() > 0:
            return True
        if self.filter(from_user=user2, to_user=user1).count() > 0:
            return True
        return False
    
    def remove(self, user1, user2):
        if self.filter(from_user=user1, to_user=user2):
            friendship = self.filter(from_user=user1, to_user=user2)
        elif self.filter(from_user=user2, to_user=user1):
            friendship = self.filter(from_user=user2, to_user=user1)
        friendship.delete()


class Friendship(models.Model):
    """
    A friendship is a bi-directional association between two users who
    have both agreed to the association.
    """
    
    to_user = models.ForeignKey(User, related_name="friends")
    from_user = models.ForeignKey(User, related_name="_unused_")
    # @@@ relationship types
    added = models.DateField(default=datetime.date.today)
    
    objects = FriendshipManager()
    
    class Meta:
        unique_together = (('to_user', 'from_user'),)


def friend_set_for(user):
    return set([obj["friend"] for obj in Friendship.objects.friends_for_user(user)])


INVITE_STATUS = (
    ("1", "Created"),
    ("2", "Sent"),
    ("3", "Failed"),
    ("4", "Expired"),
    ("5", "Accepted"),
    ("6", "Declined"),
    ("7", "Joined Independently"),
    ("8", "Deleted")
)


class JoinInvitationManager(models.Manager):
    
    def send_invitation(self, from_user, to_email, message):
        contact, created = Contact.objects.get_or_create(email=to_email, user=from_user)
        salt = sha_constructor(str(random())).hexdigest()[:5]
        confirmation_key = sha_constructor(salt + to_email).hexdigest()
        
        accept_url = u"http://%s%s" % (
            unicode(Site.objects.get_current()),
            reverse("friends_accept_join", args=(confirmation_key,)),
        )
        
        ctx = {
            "SITE_NAME": settings.SITE_NAME,
            "CONTACT_EMAIL": settings.CONTACT_EMAIL,
            "user": from_user,
            "message": message,
            "accept_url": accept_url,
        }
        
        subject = render_to_string("friends/join_invite_subject.txt", ctx)
        email_message = render_to_string("friends/join_invite_message.txt", ctx)
        
        send_mail(subject, email_message, settings.DEFAULT_FROM_EMAIL, [to_email])        
        return self.create(from_user=from_user, contact=contact, message=message, status="2", confirmation_key=confirmation_key)


class JoinInvitation(models.Model):
    """
    A join invite is an invitation to join the site from a user to a
    contact who is not known to be a user.
    """
    
    from_user = models.ForeignKey(User, related_name="join_from")
    contact = models.ForeignKey(Contact)
    message = models.TextField()
    sent = models.DateField(default=datetime.date.today)
    status = models.CharField(max_length=1, choices=INVITE_STATUS)
    confirmation_key = models.CharField(max_length=40)
    
    objects = JoinInvitationManager()
    
    def accept(self, new_user):
        # mark invitation accepted
        self.status = "5"
        self.save()
        # auto-create friendship
        friendship = Friendship(to_user=new_user, from_user=self.from_user)
        friendship.save()
        # notify
        if notification:
            notification.send([self.from_user], "join_accept", {"invitation": self, "new_user": new_user})
            friends = []
            for user in friend_set_for(new_user) | friend_set_for(self.from_user):
                if user != new_user and user != self.from_user:
                    friends.append(user)
            notification.send(friends, "friends_otherconnect", {"invitation": self, "to_user": new_user})


class FriendshipInvitationManager(models.Manager):
    
    def invitations(self, *args, **kwargs):
        return self.filter(*args, **kwargs).exclude(status__in=["6", "8"])


class FriendshipInvitation(models.Model):
    """
    A frienship invite is an invitation from one user to another to be
    associated as friends.
    """
    
    from_user = models.ForeignKey(User, related_name="invitations_from")
    to_user = models.ForeignKey(User, related_name="invitations_to")
    message = models.TextField()
    sent = models.DateField(default=datetime.date.today)
    status = models.CharField(max_length=1, choices=INVITE_STATUS)
    
    objects = FriendshipInvitationManager()
    
    def accept(self):
        if not Friendship.objects.are_friends(self.to_user, self.from_user):
            friendship = Friendship(to_user=self.to_user, from_user=self.from_user)
            friendship.save()
            self.status = "5"
            self.save()
            if notification:
                notification.send([self.from_user], "friends_accept", {"invitation": self})
                notification.send([self.to_user], "friends_accept_sent", {"invitation": self})
                for user in friend_set_for(self.to_user) | friend_set_for(self.from_user):
                    if user != self.to_user and user != self.from_user:
                        notification.send([user], "friends_otherconnect", {"invitation": self, "to_user": self.to_user})
    
    def decline(self):
        if not Friendship.objects.are_friends(self.to_user, self.from_user):
            self.status = "6"
            self.save()


class FriendshipInvitationHistory(models.Model):
    """
    History for friendship invitations
    """
    
    from_user = models.ForeignKey(User, related_name="invitations_from_history")
    to_user = models.ForeignKey(User, related_name="invitations_to_history")
    message = models.TextField()
    sent = models.DateField(default=datetime.date.today)
    status = models.CharField(max_length=1, choices=INVITE_STATUS)


if EmailAddress:
    def new_user(sender, instance, **kwargs):
        if instance.verified:
            for join_invitation in JoinInvitation.objects.filter(contact__email=instance.email):
                if join_invitation.status not in ["5", "7"]: # if not accepted or already marked as joined independently
                    join_invitation.status = "7"
                    join_invitation.save()
                    # notification will be covered below
            for contact in Contact.objects.filter(email=instance.email):
                contact.users.add(instance.user)
                # @@@ send notification
    
    # only if django-email-notification is installed
    signals.post_save.connect(new_user, sender=EmailAddress)

def delete_friendship(sender, instance, **kwargs):
    friendship_invitations = FriendshipInvitation.objects.filter(to_user=instance.to_user, from_user=instance.from_user)
    for friendship_invitation in friendship_invitations:
        if friendship_invitation.status != "8":
            friendship_invitation.status = "8"
            friendship_invitation.save()


signals.pre_delete.connect(delete_friendship, sender=Friendship)


# moves existing friendship invitation from user to user to FriendshipInvitationHistory before saving new invitation
def friendship_invitation(sender, instance, **kwargs):
    friendship_invitations = FriendshipInvitation.objects.filter(to_user=instance.to_user, from_user=instance.from_user)
    for friendship_invitation in friendship_invitations:
        FriendshipInvitationHistory.objects.create(
                from_user=friendship_invitation.from_user,
                to_user=friendship_invitation.to_user,
                message=friendship_invitation.message,
                sent=friendship_invitation.sent,
                status=friendship_invitation.status
                )
        friendship_invitation.delete()


signals.pre_save.connect(friendship_invitation, sender=FriendshipInvitation)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for friendsdev project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'ado_mssql'.
DATABASE_NAME = 'test.db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
# although not all variations may be possible on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '1ec9__w-1t0hd#a@biwd87_af!fj4f%pzug85l%4@gqw%sh2+('

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
)

ROOT_URLCONF = 'friendsdev.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'friends',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin

urlpatterns = patterns('',
    # Example:
    # (r'^friendsdev/', include('friendsdev.foo.urls')),

    # Uncomment this for admin:
    (r'^admin/(.*)', admin.site.root),
)

########NEW FILE########
