__FILENAME__ = admin
from django.contrib import admin
from models import Invitation, InvitationStats


class InvitationAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'expiration_date')
admin.site.register(Invitation, InvitationAdmin)


class InvitationStatsAdmin(admin.ModelAdmin):
    list_display = ('user', 'available', 'sent', 'accepted', 'performance')

    def performance(self, obj):
        return '%0.2f' % obj.performance
admin.site.register(InvitationStats, InvitationStatsAdmin)

########NEW FILE########
__FILENAME__ = app_settings
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.importlib import import_module


def get_performance_func(settings):
    performance_func = getattr(settings, 'INVITATION_PERFORMANCE_FUNC', None)
    if isinstance(performance_func, (str, unicode)):
        module_name, func_name = performance_func.rsplit('.', 1)
        try:
            performance_func = getattr(import_module(module_name), func_name)
        except ImportError:
            raise ImproperlyConfigured('Can\'t import performance function ' \
                                       '`%s` from `%s`' % (func_name,
                                                           module_name))
    if performance_func and not callable(performance_func):
        raise ImproperlyConfigured('INVITATION_PERFORMANCE_FUNC must be a ' \
                                   'callable or an import path string ' \
                                   'pointing to a callable.')


INVITE_ONLY = getattr(settings, 'INVITATION_INVITE_ONLY', False)
EXPIRE_DAYS = getattr(settings, 'INVITATION_EXPIRE_DAYS', 15)
INITIAL_INVITATIONS = getattr(settings, 'INVITATION_INITIAL_INVITATIONS', 10)
REWARD_THRESHOLD = getattr(settings, 'INVITATION_REWARD_THRESHOLD', 0.75)
PERFORMANCE_FUNC = get_performance_func(settings)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.auth.models import User
from registration.forms import RegistrationForm


def save_user(form_instance):
    """
    Create a new **active** user from form data.

    This method is intended to replace the ``save`` of
    ``django-registration``s ``RegistrationForm``. Required form fields
    are ``username``, ``email`` and ``password1``.
    """
    username = form_instance.cleaned_data['username']
    email = form_instance.cleaned_data['email']
    password = form_instance.cleaned_data['password1']
    new_user = User.objects.create_user(username, email, password)
    new_user.save()
    return new_user


class InvitationForm(forms.Form):
    email = forms.EmailField()


class RegistrationFormInvitation(RegistrationForm):
    """
    Subclass of ``registration.RegistrationForm`` that create an **active**
    user.

    Since registration is (supposedly) done via invitation, no further
    activation is required. For this reason ``email`` field always return
    the value of ``email`` argument given the constructor.
    """
    def __init__(self, email, *args, **kwargs):
        super(RegistrationFormInvitation, self).__init__(*args, **kwargs)
        self._make_email_immutable(email)

    def _make_email_immutable(self, email):
        self._email = self.initial['email'] = email
        if 'email' in self.data:
            self.data = self.data.copy()
            self.data['email'] = email
        self.fields['email'].widget.attrs.update({'readonly': True})

    def clean_email(self):
        return self._email

    save = save_user

########NEW FILE########
__FILENAME__ = models
import datetime
import random
from django.db import models
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.utils.hashcompat import sha_constructor
from django.contrib.auth.models import User
from django.contrib.sites.models import Site, RequestSite
import app_settings
import signals


def performance_calculator_invite_only(invitation_stats):
    """Calculate a performance score between ``0.0`` and ``1.0``.
    """
    if app_settings.INVITE_ONLY:
        total = invitation_stats.available + invitation_stats.sent
    try:
        send_ratio = float(invitation_stats.sent) / total
    except ZeroDivisionError:
        send_ratio = 0.0
    accept_ratio = performance_calculator_invite_optional(invitation_stats)
    return min((send_ratio + accept_ratio) * 0.6, 1.0)


def performance_calculator_invite_optional(invitation_stats):
    try:
        accept_ratio = float(invitation_stats.accepted) / invitation_stats.sent
        return min(accept_ratio, 1.0)
    except ZeroDivisionError:
        return 0.0


DEFAULT_PERFORMANCE_CALCULATORS = {
    True: performance_calculator_invite_only,
    False: performance_calculator_invite_optional,
}


class InvitationError(Exception):
    pass


class InvitationManager(models.Manager):
    def invite(self, user, email):
        """
        Get or create an invitation for ``email`` from ``user``.

        This method doesn't an send email. You need to call ``send_email()``
        method on returned ``Invitation`` instance.
        """
        invitation = None
        try:
            # It is possible that there is more than one invitation fitting
            # the criteria. Normally this means some older invitations are
            # expired or an email is invited consequtively.
            invitation = self.filter(user=user, email=email)[0]
            if not invitation.is_valid():
                invitation = None
        except (Invitation.DoesNotExist, IndexError):
            pass
        if invitation is None:
            user.invitation_stats.use()
            key = '%s%0.16f%s%s' % (settings.SECRET_KEY,
                                    random.random(),
                                    user.email,
                                    email)
            key = sha_constructor(key).hexdigest()
            invitation = self.create(user=user, email=email, key=key)
        return invitation
    invite.alters_data = True

    def find(self, invitation_key):
        """
        Find a valid invitation for the given key or raise
        ``Invitation.DoesNotExist``.

        This function always returns a valid invitation. If an invitation is
        found but not valid it will be automatically deleted.
        """
        try:
            invitation = self.filter(key=invitation_key)[0]
        except IndexError:
            raise Invitation.DoesNotExist
        if not invitation.is_valid():
            invitation.delete()
            raise Invitation.DoesNotExist
        return invitation

    def valid(self):
        """Filter valid invitations.
        """
        expiration = datetime.datetime.now() - datetime.timedelta(
                                                     app_settings.EXPIRE_DAYS)
        return self.get_query_set().filter(date_invited__gte=expiration)

    def invalid(self):
        """Filter invalid invitation.
        """
        expiration = datetime.datetime.now() - datetime.timedelta(
                                                     app_settings.EXPIRE_DAYS)
        return self.get_query_set().filter(date_invited__le=expiration)


class Invitation(models.Model):
    user = models.ForeignKey(User, related_name='invitations')
    email = models.EmailField(_(u'e-mail'))
    key = models.CharField(_(u'invitation key'), max_length=40, unique=True)
    date_invited = models.DateTimeField(_(u'date invited'),
                                        default=datetime.datetime.now)

    objects = InvitationManager()

    class Meta:
        verbose_name = _(u'invitation')
        verbose_name_plural = _(u'invitations')
        ordering = ('-date_invited',)

    def __unicode__(self):
        return _('%(username)s invited %(email)s on %(date)s') % {
            'username': self.user.username,
            'email': self.email,
            'date': str(self.date_invited.date()),
        }

    @models.permalink
    def get_absolute_url(self):
        return ('invitation_register', (), {'invitation_key': self.key})

    @property
    def _expires_at(self):
        return self.date_invited + datetime.timedelta(app_settings.EXPIRE_DAYS)

    def is_valid(self):
        """
        Return ``True`` if the invitation is still valid, ``False`` otherwise.
        """
        return datetime.datetime.now() < self._expires_at

    def expiration_date(self):
        """Return a ``datetime.date()`` object representing expiration date.
        """
        return self._expires_at.date()
    expiration_date.short_description = _(u'expiration date')
    expiration_date.admin_order_field = 'date_invited'

    def send_email(self, email=None, site=None, request=None):
        """
        Send invitation email.

        Both ``email`` and ``site`` parameters are optional. If not supplied
        instance's ``email`` field and current site will be used.

        **Templates:**

        :invitation/invitation_email_subject.txt:
            Template used to render the email subject.

            **Context:**

            :invitation: ``Invitation`` instance ``send_email`` is called on.
            :site: ``Site`` instance to be used.

        :invitation/invitation_email.txt:
            Template used to render the email body.

            **Context:**

            :invitation: ``Invitation`` instance ``send_email`` is called on.
            :expiration_days: ``INVITATION_EXPIRE_DAYS`` setting.
            :site: ``Site`` instance to be used.

        **Signals:**

        ``invitation.signals.invitation_sent`` is sent on completion.
        """
        email = email or self.email
        if site is None:
            if Site._meta.installed:
                site = Site.objects.get_current()
            elif request is not None:
                site = RequestSite(request)
        subject = render_to_string('invitation/invitation_email_subject.txt',
                                   {'invitation': self, 'site': site})
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        message = render_to_string('invitation/invitation_email.txt', {
            'invitation': self,
            'expiration_days': app_settings.EXPIRE_DAYS,
            'site': site
        })
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
        signals.invitation_sent.send(sender=self)

    def mark_accepted(self, new_user):
        """
        Update sender's invitation statistics and delete self.

        ``invitation.signals.invitation_accepted`` is sent just before the
        instance is deleted.
        """
        self.user.invitation_stats.mark_accepted()
        signals.invitation_accepted.send(sender=self,
                                         inviting_user=self.user,
                                         new_user=new_user)
        self.delete()
    mark_accepted.alters_data = True


class InvitationStatsManager(models.Manager):
    def give_invitations(self, user=None, count=None):
        rewarded_users = 0
        invitations_given = 0
        if not isinstance(count, int) and not callable(count):
            raise TypeError('Count must be int or callable.')
        if user is None:
            qs = self.get_query_set()
        else:
            qs = self.filter(user=user)
        for instance in qs:
            if callable(count):
                c = count(instance.user)
            else:
                c = count
            if c:
                instance.add_available(c)
                rewarded_users += 1
                invitations_given += c
        return rewarded_users, invitations_given

    def reward(self, user=None, reward_count=app_settings.INITIAL_INVITATIONS):
        def count(user):
            if user.invitation_stats.performance >= \
                                                app_settings.REWARD_THRESHOLD:
                return reward_count
            return 0
        return self.give_invitations(user, count)


class InvitationStats(models.Model):
    """Store invitation statistics for ``user``.
    """
    user = models.OneToOneField(User,
                                related_name='invitation_stats')
    available = models.IntegerField(_(u'available invitations'),
                                    default=app_settings.INITIAL_INVITATIONS)
    sent = models.IntegerField(_(u'invitations sent'), default=0)
    accepted = models.IntegerField(_(u'invitations accepted'), default=0)

    objects = InvitationStatsManager()

    class Meta:
        verbose_name = verbose_name_plural = _(u'invitation stats')
        ordering = ('-user',)

    def __unicode__(self):
        return _(u'invitation stats for %(username)s') % {
                                               'username': self.user.username}

    @property
    def performance(self):
        if app_settings.PERFORMANCE_FUNC:
            return app_settings.PERFORMANCE_FUNC(self)
        return DEFAULT_PERFORMANCE_CALCULATORS[app_settings.INVITE_ONLY](self)

    def add_available(self, count=1):
        """
        Add usable invitations.

        **Optional arguments:**

        :count:
            Number of invitations to add. Default is ``1``.

        ``invitation.signals.invitation_added`` is sent at the end.
        """
        self.available = models.F('available') + count
        self.save()
        signals.invitation_added.send(sender=self, user=self.user, count=count)
    add_available.alters_data = True

    def use(self, count=1):
        """
        Mark invitations used.

        Raises ``InvitationError`` if ``INVITATION_INVITE_ONLY`` is True or
        ``count`` is more than available invitations.

        **Optional arguments:**

        :count:
            Number of invitations to mark used. Default is ``1``.
        """
        if app_settings.INVITE_ONLY:
            if self.available - count >= 0:
                self.available = models.F('available') - count
            else:
                raise InvitationError('No available invitations.')
        self.sent = models.F('sent') + count
        self.save()
    use.alters_data = True

    def mark_accepted(self, count=1):
        """
        Mark invitations accepted.

        Raises ``InvitationError`` if more invitations than possible is
        being accepted.

        **Optional arguments:**

        :count:
            Optional. Number of invitations to mark accepted. Default is ``1``.
        """
        if self.accepted + count > self.sent:
            raise InvitationError('There can\'t be more accepted ' \
                                  'invitations than sent invitations.')
        self.accepted = models.F('accepted') + count
        self.save()
    mark_accepted.alters_data = True


def create_stats(sender, instance, created, raw, **kwargs):
    if created and not raw:
        InvitationStats.objects.create(user=instance)
models.signals.post_save.connect(create_stats,
                                 sender=User,
                                 dispatch_uid='invitation.models.create_stats')

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal


invitation_added = Signal(providing_args=['user', 'count'])

invitation_sent = Signal()

invitation_accepted = Signal(providing_args=['inviting_user', 'new_user'])

########NEW FILE########
__FILENAME__ = invitation_tags
from django import template
from invitation.app_settings import INVITE_ONLY


register = template.Library()


@register.inclusion_tag('admin/invitation/invitationstats/_reward_link.html')
def admin_reward_link():
    """
    Adds a reward action if INVITE_ONLY is ``True``.

    Usage::

        {% admin_reward_link %}
    """
    return {'INVITE_ONLY': INVITE_ONLY}

########NEW FILE########
__FILENAME__ = invite_only_urls
from django.utils.importlib import import_module
from invitation import app_settings


app_settings.INVITE_ONLY = True
reload(import_module('invitation.urls'))
reload(import_module('invitation.tests.urls'))
from invitation.tests.urls import urlpatterns

########NEW FILE########
__FILENAME__ = invite_optional_urls
from django.utils.importlib import import_module
from invitation import app_settings


app_settings.INVITE_ONLY = False
reload(import_module('invitation.urls'))
reload(import_module('invitation.tests.urls'))
from invitation.tests.urls import urlpatterns

########NEW FILE########
__FILENAME__ = models
import datetime
from django.core import mail
from django.contrib.auth.models import User
from utils import BaseTestCase
from invitation import app_settings
from invitation.models import InvitationError, Invitation, InvitationStats
from invitation.models import performance_calculator_invite_only
from invitation.models import performance_calculator_invite_optional


EXPIRE_DAYS = app_settings.EXPIRE_DAYS
INITIAL_INVITATIONS = app_settings.INITIAL_INVITATIONS


class InvitationTestCase(BaseTestCase):
    def setUp(self):
        super(InvitationTestCase, self).setUp()
        user = self.user()
        user.invitation_stats.use()
        self.invitation = Invitation.objects.create(user=user,
                                                    email=u'test@example.com',
                                                    key=u'F' * 40)

    def make_invalid(self, invitation=None):
        invitation = invitation or self.invitation
        invitation.date_invited = datetime.datetime.now() - \
                                  datetime.timedelta(EXPIRE_DAYS + 10)
        invitation.save()
        return invitation

    def test_send_email(self):
        self.invitation.send_email()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].recipients()[0], u'test@example.com')
        self.invitation.send_email(u'other@email.org')
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].recipients()[0], u'other@email.org')

    def test_mark_accepted(self):
        new_user = User.objects.create_user('test', 'test@example.com', 'test')
        pk = self.invitation.pk
        self.invitation.mark_accepted(new_user)
        self.assertRaises(Invitation.DoesNotExist,
                          Invitation.objects.get, pk=pk)

    def test_invite(self):
        self.user().invitation_stats.add_available(10)
        Invitation.objects.all().delete()
        invitation = Invitation.objects.invite(self.user(), 'test@example.com')
        self.assertEqual(invitation.user, self.user())
        self.assertEqual(invitation.email, 'test@example.com')
        self.assertEqual(len(invitation.key), 40)
        self.assertEqual(invitation.is_valid(), True)
        self.assertEqual(type(invitation.expiration_date()), datetime.date)
        # Test if existing valid record is returned
        # when we try with the same credentials
        self.assertEqual(Invitation.objects.invite(self.user(),
                                              'test@example.com'), invitation)
        # Try with an invalid invitation
        invitation = self.make_invalid(invitation)
        new_invitation = Invitation.objects.invite(self.user(),
                                                   'test@example.com')
        self.assertEqual(new_invitation.is_valid(), True)
        self.assertNotEqual(new_invitation, invitation)

    def test_find(self):
        self.assertEqual(Invitation.objects.find(self.invitation.key),
                         self.invitation)
        invitation = self.make_invalid()
        self.assertEqual(invitation.is_valid(), False)
        self.assertRaises(Invitation.DoesNotExist,
                          Invitation.objects.find, invitation.key)
        self.assertEqual(Invitation.objects.all().count(), 0)
        self.assertRaises(Invitation.DoesNotExist,
                          Invitation.objects.find, '')


class InvitationStatsBaseTestCase(BaseTestCase):
    def stats(self, user=None):
        user = user or self.user()
        return (user.invitation_stats.available,
                user.invitation_stats.sent,
                user.invitation_stats.accepted)

    class MockInvitationStats(object):
        def __init__(self, available, sent, accepted):
            self.available = available
            self.sent = sent
            self.accepted = accepted


class InvitationStatsInviteOnlyTestCase(InvitationStatsBaseTestCase):
    def setUp(self):
        super(InvitationStatsInviteOnlyTestCase, self).setUp()
        app_settings.INVITE_ONLY = True

    def test_default_performance_func(self):
        self.assertAlmostEqual(performance_calculator_invite_only(
                                     self.MockInvitationStats(5, 5, 1)), 0.42)
        self.assertAlmostEqual(performance_calculator_invite_only(
                                     self.MockInvitationStats(0, 10, 10)), 1.0)
        self.assertAlmostEqual(performance_calculator_invite_only(
                                     self.MockInvitationStats(10, 0, 0)), 0.0)

    def test_add_available(self):
        self.assertEqual(self.stats(), (INITIAL_INVITATIONS, 0, 0))
        self.user().invitation_stats.add_available()
        self.assertEqual(self.stats(), (INITIAL_INVITATIONS + 1, 0, 0))
        self.user().invitation_stats.add_available(10)
        self.assertEqual(self.stats(), (INITIAL_INVITATIONS + 11, 0, 0))

    def test_use(self):
        self.user().invitation_stats.add_available(10)
        self.assertEqual(self.stats(), (INITIAL_INVITATIONS + 10, 0, 0))
        self.user().invitation_stats.use()
        self.assertEqual(self.stats(), (INITIAL_INVITATIONS + 9, 1, 0))
        self.user().invitation_stats.use(5)
        self.assertEqual(self.stats(), (INITIAL_INVITATIONS + 4, 6, 0))
        self.assertRaises(InvitationError,
                          self.user().invitation_stats.use,
                          INITIAL_INVITATIONS + 5)

    def test_mark_accepted(self):
        if INITIAL_INVITATIONS < 10:
            i = 10
            self.user().invitation_stats.add_available(10-INITIAL_INVITATIONS)
        else:
            i = INITIAL_INVITATIONS
        self.user().invitation_stats.use(i)
        self.user().invitation_stats.mark_accepted()
        self.assertEqual(self.stats(), (0, i, 1))
        self.user().invitation_stats.mark_accepted(5)
        self.assertEqual(self.stats(), (0, i, 6))
        self.assertRaises(InvitationError,
                          self.user().invitation_stats.mark_accepted, i)

    def test_give_invitations(self):
        self.assertEqual(self.stats(), (INITIAL_INVITATIONS, 0, 0))
        InvitationStats.objects.give_invitations(count=3)
        self.assertEqual(self.stats(), (INITIAL_INVITATIONS + 3, 0, 0))
        InvitationStats.objects.give_invitations(self.user(), count=3)
        self.assertEqual(self.stats(), (INITIAL_INVITATIONS + 6, 0, 0))
        InvitationStats.objects.give_invitations(self.user(),
                                                 count=lambda u: 4)
        self.assertEqual(self.stats(), (INITIAL_INVITATIONS + 10, 0, 0))

    def test_reward(self):
        self.assertAlmostEqual(self.user().invitation_stats.performance, 0.0)
        InvitationStats.objects.reward()
        self.assertEqual(self.user().invitation_stats.available,
                         INITIAL_INVITATIONS)
        self.user().invitation_stats.use(INITIAL_INVITATIONS)
        self.user().invitation_stats.mark_accepted(INITIAL_INVITATIONS)
        InvitationStats.objects.reward()
        invitation_stats = self.user().invitation_stats
        self.assertEqual(invitation_stats.performance > 0.5, True)
        self.assertEqual(invitation_stats.available, INITIAL_INVITATIONS)


class InvitationStatsInviteOptionalTestCase(InvitationStatsBaseTestCase):
    def setUp(self):
        super(InvitationStatsInviteOptionalTestCase, self).setUp()
        app_settings.INVITE_ONLY = False

    def test_default_performance_func(self):
        self.assertAlmostEqual(performance_calculator_invite_optional(
                                     self.MockInvitationStats(5, 5, 1)), 0.2)
        self.assertAlmostEqual(performance_calculator_invite_optional(
                                     self.MockInvitationStats(20, 5, 1)), 0.2)
        self.assertAlmostEqual(performance_calculator_invite_optional(
                                     self.MockInvitationStats(0, 5, 1)), 0.2)
        self.assertAlmostEqual(performance_calculator_invite_optional(
                                     self.MockInvitationStats(0, 10, 10)), 1.0)
        self.assertAlmostEqual(performance_calculator_invite_optional(
                                     self.MockInvitationStats(10, 0, 0)), 0.0)

    def test_use(self):
        self.assertEqual(self.stats(), (INITIAL_INVITATIONS, 0, 0))
        self.user().invitation_stats.use()
        self.assertEqual(self.stats(), (INITIAL_INVITATIONS, 1, 0))
        self.user().invitation_stats.use(5)
        self.assertEqual(self.stats(), (INITIAL_INVITATIONS, 6, 0))
        self.user().invitation_stats.use(INITIAL_INVITATIONS + 5)
        self.assertEqual(self.stats(), (INITIAL_INVITATIONS,
                                        INITIAL_INVITATIONS + 11,
                                        0))

    def test_mark_accepted(self):
        if INITIAL_INVITATIONS < 10:
            i = 10
            self.user().invitation_stats.add_available(10-INITIAL_INVITATIONS)
        else:
            i = INITIAL_INVITATIONS
        self.user().invitation_stats.use(i)
        self.user().invitation_stats.mark_accepted()
        self.assertEqual(self.stats(), (i, i, 1))
        self.user().invitation_stats.mark_accepted(5)
        self.assertEqual(self.stats(), (i, i, 6))
        self.assertRaises(InvitationError,
                          self.user().invitation_stats.mark_accepted, i)
        self.user().invitation_stats.mark_accepted(4)
        self.assertEqual(self.stats(), (i, i, 10))

    def test_reward(self):
        self.assertAlmostEqual(self.user().invitation_stats.performance, 0.0)
        InvitationStats.objects.reward()
        self.assertEqual(self.user().invitation_stats.available,
                         INITIAL_INVITATIONS)
        self.user().invitation_stats.use(INITIAL_INVITATIONS)
        self.user().invitation_stats.mark_accepted(INITIAL_INVITATIONS)
        InvitationStats.objects.reward()
        invitation_stats = self.user().invitation_stats
        self.assertEqual(
            invitation_stats.performance > app_settings.REWARD_THRESHOLD, True)
        self.assertEqual(invitation_stats.available, INITIAL_INVITATIONS * 2)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
import invitation.urls as invitation_urls


urlpatterns = invitation_urls.urlpatterns + patterns('',
    url(r'^register/$',
        'django.views.generic.simple.direct_to_template',
        {'template': 'registration/registration_register.html'},
        name='registration_register'),
    url(r'^register/complete/$',
        'django.views.generic.simple.direct_to_template',
        {'template': 'registration/registration_complete.html'},
        name='registration_complete'),
)

########NEW FILE########
__FILENAME__ = utils
import os
from django.conf import settings
from django.test import TestCase
from django.contrib.auth.models import User


class BaseTestCase(TestCase):
    def setUp(self):
        super(BaseTestCase, self).setUp()
        settings.TEMPLATE_DIRS = (
            os.path.join(os.path.dirname(__file__), 'templates'),
        )
        User.objects.create_user('testuser',
                                 'testuser@example.com',
                                 'testuser')

    def user(self):
        return User.objects.get(username='testuser')

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.core import mail
from django.contrib.auth.models import User
from utils import BaseTestCase
from invitation.models import Invitation


class InviteOnlyModeTestCase(BaseTestCase):
    urls = 'invitation.tests.invite_only_urls'

    def test_invation_mode(self):
        # Normal registration view should redirect
        response = self.client.get(reverse('registration_register'))
        self.assertRedirects(response, reverse('invitation_invite_only'))
        # But registration after invitation view should work
        response = self.client.get(reverse('invitation_register',
                                           args=('A' * 40,)))
        self.assertEqual(response.status_code, 200)

    def test_invitation(self):
        available = self.user().invitation_stats.available
        self.client.login(username='testuser', password='testuser')
        response = self.client.post(reverse('invitation_invite'),
                                    {'email': 'friend@example.com'})
        self.assertRedirects(response, reverse('invitation_complete'))
        self.assertEqual(self.user().invitation_stats.available, available-1)
        # Delete previously created invitation and
        # set available invitations count to 0.
        Invitation.objects.all().delete()
        invitation_stats = self.user().invitation_stats
        invitation_stats.available = 0
        invitation_stats.save()
        del(invitation_stats)
        response = self.client.post(reverse('invitation_invite'),
                                    {'email': 'friend@example.com'})
        self.assertRedirects(response, reverse('invitation_unavailable'))

    def test_registration(self):
        # Make sure error message is shown in
        # case of an invalid invitation key
        response = self.client.get(reverse('invitation_register',
                                           args=('A' * 40,)))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                'invitation/wrong_invitation_key.html')
        # Registration with an invitation
        invitation = Invitation.objects.invite(self.user(),
                                               'friend@example.com')
        register_url = reverse('invitation_register', args=(invitation.key,))
        response = self.client.get(register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                'registration/registration_form.html')
        self.assertContains(response, invitation.email)
        # We are posting a different email than the
        # invitation.email but the form should just
        # ignore it and register with invitation.email
        response = self.client.post(register_url,
                                    {'username': u'friend',
                                     'email': u'noone@example.com',
                                     'password1': u'friend',
                                     'password2': u'friend'})
        self.assertRedirects(response, reverse('invitation_registered'))
        self.assertEqual(len(mail.outbox), 0)       # No confirmation email
        self.assertEqual(self.user().invitation_stats.accepted, 1)
        new_user = User.objects.get(username='friend')
        self.assertEqual(new_user.is_active, True)
        self.assertRaises(Invitation.DoesNotExist,
                          Invitation.objects.get,
                          user=self.user(),
                          email='friend@example.com')


class InviteOptionalModeTestCase(BaseTestCase):
    urls = 'invitation.tests.invite_optional_urls'

    def test_invation_mode(self):
        # Normal registration view should work
        response = self.client.get(reverse('registration_register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                'registration/registration_register.html')
        # So as registration after invitation view
        response = self.client.get(reverse('invitation_register',
                                           args=('A' * 40,)))
        self.assertEqual(response.status_code, 200)

    def test_invitation(self):
        self.client.login(username='testuser', password='testuser')
        response = self.client.get(reverse('invitation_invite'))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse('invitation_invite'),
                                    {'email': 'friend@example.com'})
        self.assertRedirects(response, reverse('invitation_complete'))
        invitation_query = Invitation.objects.filter(user=self.user(),
                                                   email='friend@example.com')
        self.assertEqual(invitation_query.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(self.user().invitation_stats.sent, 1)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from django.contrib.auth.decorators import login_required
from app_settings import INVITE_ONLY


login_required_direct_to_template = login_required(direct_to_template)


urlpatterns = patterns('',
    url(r'^invitation/$',
        login_required_direct_to_template,
        {'template': 'invitation/invitation_home.html'},
        name='invitation_home'),
    url(r'^invitation/invite/$',
        'invitation.views.invite',
        name='invitation_invite'),
    url(r'^invitation/invite/complete/$',
        login_required_direct_to_template,
        {'template': 'invitation/invitation_complete.html'},
        name='invitation_complete'),
    url(r'^invitation/invite/unavailable/$',
        login_required_direct_to_template,
        {'template': 'invitation/invitation_unavailable.html'},
        name='invitation_unavailable'),
    url(r'^invitation/accept/complete/$',
        direct_to_template,
        {'template': 'invitation/invitation_registered.html'},
        name='invitation_registered'),
    url(r'^invitation/accept/(?P<invitation_key>\w+)/$',
        'invitation.views.register',
        name='invitation_register'),
)


if INVITE_ONLY:
    urlpatterns += patterns('',
        url(r'^register/$',
            'django.views.generic.simple.redirect_to',
            {'url': '../invitation/invite_only/', 'permanent': False},
            name='registration_register'),
        url(r'^invitation/invite_only/$',
            direct_to_template,
            {'template': 'invitation/invite_only.html'},
            name='invitation_invite_only'),
        url(r'^invitation/reward/$',
            'invitation.views.reward',
            name='invitation_reward'),
    )

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.utils.translation import ugettext
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from models import InvitationError, Invitation, InvitationStats
from forms import InvitationForm, RegistrationFormInvitation
from registration.signals import user_registered


def apply_extra_context(context, extra_context=None):
    if extra_context is None:
        extra_context = {}
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value
    return context


@login_required
def invite(request, success_url=None,
           form_class=InvitationForm,
           template_name='invitation/invitation_form.html',
           extra_context=None):
    """
    Create an invitation and send invitation email.

    Send invitation email and then redirect to success URL if the
    invitation form is valid. Redirect named URL ``invitation_unavailable``
    on InvitationError. Render invitation form template otherwise.

    **Required arguments:**

    None.

    **Optional arguments:**

    :success_url:
        The URL to redirect to on successful registration. Default value is
        ``None``, ``invitation_complete`` will be resolved in this case.

    :form_class:
        A form class to use for invitation. Takes ``request.user`` as first
        argument to its constructor. Must have an ``email`` field. Custom
        validation can be implemented here.

    :template_name:
        A custom template to use. Default value is
        ``invitation/invitation_form.html``.

    :extra_context:
        A dictionary of variables to add to the template context. Any
        callable object in this dictionary will be called to produce
        the end result which appears in the context.

    **Template:**

    ``invitation/invitation_form.html`` or ``template_name`` keyword
    argument.

    **Context:**

    A ``RequestContext`` instance is used rendering the template. Context,
    in addition to ``extra_context``, contains:

    :form:
        The invitation form.
    """
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            try:
                invitation = Invitation.objects.invite(
                                     request.user, form.cleaned_data["email"])
            except InvitationError:
                return HttpResponseRedirect(reverse('invitation_unavailable'))
            invitation.send_email(request=request)
            return HttpResponseRedirect(success_url or \
                                               reverse('invitation_complete'))
    else:
        form = form_class()
    context = apply_extra_context(RequestContext(request), extra_context)
    return render_to_response(template_name,
                              {'form': form},
                              context_instance=context)


def register(request,
             invitation_key,
             wrong_key_template='invitation/wrong_invitation_key.html',
             redirect_to_if_authenticated='/',
             success_url=None,
             form_class=RegistrationFormInvitation,
             template_name='registration/registration_form.html',
             extra_context=None):
    """
    Allow a new user to register via invitation.

    Send invitation email and then redirect to success URL if the
    invitation form is valid. Redirect named URL ``invitation_unavailable``
    on InvitationError. Render invitation form template otherwise. Sends
    registration.signals.user_registered after creating the user.

    **Required arguments:**

    :invitation_key:
        An invitation key in the form of ``[\da-e]{40}``

    **Optional arguments:**

    :wrong_key_template:
        Template to be used when an invalid invitation key is supplied.
        Default value is ``invitation/wrong_invitation_key.html``.

    :redirect_to_if_authenticated:
        URL to be redirected when an authenticated user calls this view.
        Defaults value is ``/``

    :success_url:
        The URL to redirect to on successful registration. Default value is
        ``None``, ``invitation_registered`` will be resolved in this case.

    :form_class:
        A form class to use for registration. Takes the invited email as first
        argument to its constructor.

    :template_name:
        A custom template to use. Default value is
        ``registration/registration_form.html``.

    :extra_context:
        A dictionary of variables to add to the template context. Any
        callable object in this dictionary will be called to produce
        the end result which appears in the context.

    **Templates:**

    ``invitation/invitation_form.html`` or ``template_name`` keyword
    argument as the *main template*.

    ``invitation/wrong_invitation_key.html`` or ``wrong_key_template`` keyword
    argument as the *wrong key template*.

    **Context:**

    ``RequestContext`` instances are used rendering both templates. Context,
    in addition to ``extra_context``, contains:

    For wrong key template
        :invitation_key: supplied invitation key

    For main template
        :form:
            The registration form.
    """
    if request.user.is_authenticated():
        return HttpResponseRedirect(redirect_to_if_authenticated)
    try:
        invitation = Invitation.objects.find(invitation_key)
    except Invitation.DoesNotExist:
        context = apply_extra_context(RequestContext(request), extra_context)
        return render_to_response(wrong_key_template,
                                  {'invitation_key': invitation_key},
                                  context_instance=context)
    if request.method == 'POST':
        form = form_class(invitation.email, request.POST, request.FILES)
        if form.is_valid():
            new_user = form.save()
            invitation.mark_accepted(new_user)
            user_registered.send(sender="invitation",
                                 user=new_user,
                                 request=request)
            return HttpResponseRedirect(success_url or \
                                             reverse('invitation_registered'))
    else:
        form = form_class(invitation.email)
    context = apply_extra_context(RequestContext(request), extra_context)
    return render_to_response(template_name,
                              {'form': form},
                              context_instance=context)


@staff_member_required
def reward(request):
    """
    Add invitations to users with high invitation performance and redirect
    refferring page.
    """
    rewarded_users, invitations_given = InvitationStats.objects.reward()
    if rewarded_users:
        message = ugettext(u'%(users)s users are given a total of ' \
                           u'%(invitations)s invitations.') % {
                                            'users': rewarded_users,
                                            'invitations': invitations_given}
    else:
        message = ugettext(u'No user has performance above ' \
                           u'threshold, no invitations awarded.')
    request.user.message_set.create(message=message)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

########NEW FILE########
