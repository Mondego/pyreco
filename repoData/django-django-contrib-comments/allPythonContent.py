__FILENAME__ = admin
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _, ungettext

from django_comments.models import Comment
from django_comments import get_model
from django_comments.views.moderation import perform_flag, perform_approve, perform_delete


class UsernameSearch(object):
    """The User object may not be auth.User, so we need to provide
    a mechanism for issuing the equivalent of a .filter(user__username=...)
    search in CommentAdmin.
    """
    def __str__(self):
        return 'user__%s' % get_user_model().USERNAME_FIELD


class CommentsAdmin(admin.ModelAdmin):
    fieldsets = (
        (None,
           {'fields': ('content_type', 'object_pk', 'site')}
        ),
        (_('Content'),
           {'fields': ('user', 'user_name', 'user_email', 'user_url', 'comment')}
        ),
        (_('Metadata'),
           {'fields': ('submit_date', 'ip_address', 'is_public', 'is_removed')}
        ),
     )

    list_display = ('name', 'content_type', 'object_pk', 'ip_address', 'submit_date', 'is_public', 'is_removed')
    list_filter = ('submit_date', 'site', 'is_public', 'is_removed')
    date_hierarchy = 'submit_date'
    ordering = ('-submit_date',)
    raw_id_fields = ('user',)
    search_fields = ('comment', UsernameSearch(), 'user_name', 'user_email', 'user_url', 'ip_address')
    actions = ["flag_comments", "approve_comments", "remove_comments"]

    def get_actions(self, request):
        actions = super(CommentsAdmin, self).get_actions(request)
        # Only superusers should be able to delete the comments from the DB.
        if not request.user.is_superuser and 'delete_selected' in actions:
            actions.pop('delete_selected')
        if not request.user.has_perm('django_comments.can_moderate'):
            if 'approve_comments' in actions:
                actions.pop('approve_comments')
            if 'remove_comments' in actions:
                actions.pop('remove_comments')
        return actions

    def flag_comments(self, request, queryset):
        self._bulk_flag(request, queryset, perform_flag,
                        lambda n: ungettext('flagged', 'flagged', n))
    flag_comments.short_description = _("Flag selected comments")

    def approve_comments(self, request, queryset):
        self._bulk_flag(request, queryset, perform_approve,
                        lambda n: ungettext('approved', 'approved', n))
    approve_comments.short_description = _("Approve selected comments")

    def remove_comments(self, request, queryset):
        self._bulk_flag(request, queryset, perform_delete,
                        lambda n: ungettext('removed', 'removed', n))
    remove_comments.short_description = _("Remove selected comments")

    def _bulk_flag(self, request, queryset, action, done_message):
        """
        Flag, approve, or remove some comments from an admin action. Actually
        calls the `action` argument to perform the heavy lifting.
        """
        n_comments = 0
        for comment in queryset:
            action(request, comment)
            n_comments += 1

        msg = ungettext('1 comment was successfully %(action)s.',
                        '%(count)s comments were successfully %(action)s.',
                        n_comments)
        self.message_user(request, msg % {'count': n_comments, 'action': done_message(n_comments)})

# Only register the default admin if the model is the built-in comment model
# (this won't be true if there's a custom comment app).
if get_model() is Comment:
    admin.site.register(Comment, CommentsAdmin)

########NEW FILE########
__FILENAME__ = feeds
from django.contrib.syndication.views import Feed
from django.contrib.sites.models import get_current_site
from django.utils.translation import ugettext as _

import django_comments

class LatestCommentFeed(Feed):
    """Feed of latest comments on the current site."""

    def __call__(self, request, *args, **kwargs):
        self.site = get_current_site(request)
        return super(LatestCommentFeed, self).__call__(request, *args, **kwargs)

    def title(self):
        return _("%(site_name)s comments") % dict(site_name=self.site.name)

    def link(self):
        return "http://%s/" % (self.site.domain)

    def description(self):
        return _("Latest comments on %(site_name)s") % dict(site_name=self.site.name)

    def items(self):
        qs = django_comments.get_model().objects.filter(
            site__pk = self.site.pk,
            is_public = True,
            is_removed = False,
        )
        return qs.order_by('-submit_date')[:40]

    def item_pubdate(self, item):
        return item.submit_date

########NEW FILE########
__FILENAME__ = forms
import time
from django import forms
from django.forms.util import ErrorDict
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.crypto import salted_hmac, constant_time_compare
from django.utils.encoding import force_text
from django.utils.text import get_text_list
from django.utils import timezone
from django.utils.translation import ungettext, ugettext, ugettext_lazy as _

from django_comments.models import Comment

COMMENT_MAX_LENGTH = getattr(settings,'COMMENT_MAX_LENGTH', 3000)

class CommentSecurityForm(forms.Form):
    """
    Handles the security aspects (anti-spoofing) for comment forms.
    """
    content_type  = forms.CharField(widget=forms.HiddenInput)
    object_pk     = forms.CharField(widget=forms.HiddenInput)
    timestamp     = forms.IntegerField(widget=forms.HiddenInput)
    security_hash = forms.CharField(min_length=40, max_length=40, widget=forms.HiddenInput)

    def __init__(self, target_object, data=None, initial=None):
        self.target_object = target_object
        if initial is None:
            initial = {}
        initial.update(self.generate_security_data())
        super(CommentSecurityForm, self).__init__(data=data, initial=initial)

    def security_errors(self):
        """Return just those errors associated with security"""
        errors = ErrorDict()
        for f in ["honeypot", "timestamp", "security_hash"]:
            if f in self.errors:
                errors[f] = self.errors[f]
        return errors

    def clean_security_hash(self):
        """Check the security hash."""
        security_hash_dict = {
            'content_type' : self.data.get("content_type", ""),
            'object_pk' : self.data.get("object_pk", ""),
            'timestamp' : self.data.get("timestamp", ""),
        }
        expected_hash = self.generate_security_hash(**security_hash_dict)
        actual_hash = self.cleaned_data["security_hash"]
        if not constant_time_compare(expected_hash, actual_hash):
            raise forms.ValidationError("Security hash check failed.")
        return actual_hash

    def clean_timestamp(self):
        """Make sure the timestamp isn't too far (> 2 hours) in the past."""
        ts = self.cleaned_data["timestamp"]
        if time.time() - ts > (2 * 60 * 60):
            raise forms.ValidationError("Timestamp check failed")
        return ts

    def generate_security_data(self):
        """Generate a dict of security data for "initial" data."""
        timestamp = int(time.time())
        security_dict =   {
            'content_type'  : str(self.target_object._meta),
            'object_pk'     : str(self.target_object._get_pk_val()),
            'timestamp'     : str(timestamp),
            'security_hash' : self.initial_security_hash(timestamp),
        }
        return security_dict

    def initial_security_hash(self, timestamp):
        """
        Generate the initial security hash from self.content_object
        and a (unix) timestamp.
        """

        initial_security_dict = {
            'content_type' : str(self.target_object._meta),
            'object_pk' : str(self.target_object._get_pk_val()),
            'timestamp' : str(timestamp),
          }
        return self.generate_security_hash(**initial_security_dict)

    def generate_security_hash(self, content_type, object_pk, timestamp):
        """
        Generate a HMAC security hash from the provided info.
        """
        info = (content_type, object_pk, timestamp)
        key_salt = "django.contrib.forms.CommentSecurityForm"
        value = "-".join(info)
        return salted_hmac(key_salt, value).hexdigest()

class CommentDetailsForm(CommentSecurityForm):
    """
    Handles the specific details of the comment (name, comment, etc.).
    """
    name          = forms.CharField(label=_("Name"), max_length=50)
    email         = forms.EmailField(label=_("Email address"))
    url           = forms.URLField(label=_("URL"), required=False)
    comment       = forms.CharField(label=_('Comment'), widget=forms.Textarea,
                                    max_length=COMMENT_MAX_LENGTH)

    def get_comment_object(self):
        """
        Return a new (unsaved) comment object based on the information in this
        form. Assumes that the form is already validated and will throw a
        ValueError if not.

        Does not set any of the fields that would come from a Request object
        (i.e. ``user`` or ``ip_address``).
        """
        if not self.is_valid():
            raise ValueError("get_comment_object may only be called on valid forms")

        CommentModel = self.get_comment_model()
        new = CommentModel(**self.get_comment_create_data())
        new = self.check_for_duplicate_comment(new)

        return new

    def get_comment_model(self):
        """
        Get the comment model to create with this form. Subclasses in custom
        comment apps should override this, get_comment_create_data, and perhaps
        check_for_duplicate_comment to provide custom comment models.
        """
        return Comment

    def get_comment_create_data(self):
        """
        Returns the dict of data to be used to create a comment. Subclasses in
        custom comment apps that override get_comment_model can override this
        method to add extra fields onto a custom comment model.
        """
        return dict(
            content_type = ContentType.objects.get_for_model(self.target_object),
            object_pk    = force_text(self.target_object._get_pk_val()),
            user_name    = self.cleaned_data["name"],
            user_email   = self.cleaned_data["email"],
            user_url     = self.cleaned_data["url"],
            comment      = self.cleaned_data["comment"],
            submit_date  = timezone.now(),
            site_id      = settings.SITE_ID,
            is_public    = True,
            is_removed   = False,
        )

    def check_for_duplicate_comment(self, new):
        """
        Check that a submitted comment isn't a duplicate. This might be caused
        by someone posting a comment twice. If it is a dup, silently return the *previous* comment.
        """
        possible_duplicates = self.get_comment_model()._default_manager.using(
            self.target_object._state.db
        ).filter(
            content_type = new.content_type,
            object_pk = new.object_pk,
            user_name = new.user_name,
            user_email = new.user_email,
            user_url = new.user_url,
        )
        for old in possible_duplicates:
            if old.submit_date.date() == new.submit_date.date() and old.comment == new.comment:
                return old

        return new

    def clean_comment(self):
        """
        If COMMENTS_ALLOW_PROFANITIES is False, check that the comment doesn't
        contain anything in PROFANITIES_LIST.
        """
        comment = self.cleaned_data["comment"]
        if settings.COMMENTS_ALLOW_PROFANITIES == False:
            bad_words = [w for w in settings.PROFANITIES_LIST if w in comment.lower()]
            if bad_words:
                raise forms.ValidationError(ungettext(
                    "Watch your mouth! The word %s is not allowed here.",
                    "Watch your mouth! The words %s are not allowed here.",
                    len(bad_words)) % get_text_list(
                        ['"%s%s%s"' % (i[0], '-'*(len(i)-2), i[-1])
                         for i in bad_words], ugettext('and')))
        return comment

class CommentForm(CommentDetailsForm):
    honeypot      = forms.CharField(required=False,
                                    label=_('If you enter anything in this field '\
                                            'your comment will be treated as spam'))

    def clean_honeypot(self):
        """Check that nothing's been entered into the honeypot."""
        value = self.cleaned_data["honeypot"]
        if value:
            raise forms.ValidationError(self.fields["honeypot"].label)
        return value

########NEW FILE########
__FILENAME__ = managers
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_text

class CommentManager(models.Manager):

    def in_moderation(self):
        """
        QuerySet for all comments currently in the moderation queue.
        """
        return self.get_query_set().filter(is_public=False, is_removed=False)

    def for_model(self, model):
        """
        QuerySet for all comments for a particular model (either an instance or
        a class).
        """
        ct = ContentType.objects.get_for_model(model)
        qs = self.get_query_set().filter(content_type=ct)
        if isinstance(model, models.Model):
            qs = qs.filter(object_pk=force_text(model._get_pk_val()))
        return qs

########NEW FILE########
__FILENAME__ = models
from django.conf import settings
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core import urlresolvers
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible

from django_comments.managers import CommentManager

COMMENT_MAX_LENGTH = getattr(settings, 'COMMENT_MAX_LENGTH', 3000)


class BaseCommentAbstractModel(models.Model):
    """
    An abstract base class that any custom comment models probably should
    subclass.
    """

    # Content-object field
    content_type = models.ForeignKey(ContentType,
            verbose_name=_('content type'),
            related_name="content_type_set_for_%(class)s")
    object_pk = models.TextField(_('object ID'))
    content_object = generic.GenericForeignKey(ct_field="content_type", fk_field="object_pk")

    # Metadata about the comment
    site = models.ForeignKey(Site)

    class Meta:
        abstract = True

    def get_content_object_url(self):
        """
        Get a URL suitable for redirecting to the content object.
        """
        return urlresolvers.reverse(
            "comments-url-redirect",
            args=(self.content_type_id, self.object_pk)
        )


@python_2_unicode_compatible
class Comment(BaseCommentAbstractModel):
    """
    A user comment about some object.
    """

    # Who posted this comment? If ``user`` is set then it was an authenticated
    # user; otherwise at least user_name should have been set and the comment
    # was posted by a non-authenticated user.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'),
                    blank=True, null=True, related_name="%(class)s_comments")
    user_name = models.CharField(_("user's name"), max_length=50, blank=True)
    user_email = models.EmailField(_("user's email address"), blank=True)
    user_url = models.URLField(_("user's URL"), blank=True)

    comment = models.TextField(_('comment'), max_length=COMMENT_MAX_LENGTH)

    # Metadata about the comment
    submit_date = models.DateTimeField(_('date/time submitted'), default=None)
    ip_address = models.GenericIPAddressField(_('IP address'), unpack_ipv4=True, blank=True, null=True)
    is_public = models.BooleanField(_('is public'), default=True,
                    help_text=_('Uncheck this box to make the comment effectively ' \
                                'disappear from the site.'))
    is_removed = models.BooleanField(_('is removed'), default=False,
                    help_text=_('Check this box if the comment is inappropriate. ' \
                                'A "This comment has been removed" message will ' \
                                'be displayed instead.'))

    # Manager
    objects = CommentManager()

    class Meta:
        db_table = "django_comments"
        ordering = ('submit_date',)
        permissions = [("can_moderate", "Can moderate comments")]
        verbose_name = _('comment')
        verbose_name_plural = _('comments')

    def __str__(self):
        return "%s: %s..." % (self.name, self.comment[:50])

    def save(self, *args, **kwargs):
        if self.submit_date is None:
            self.submit_date = timezone.now()
        super(Comment, self).save(*args, **kwargs)

    def _get_userinfo(self):
        """
        Get a dictionary that pulls together information about the poster
        safely for both authenticated and non-authenticated comments.

        This dict will have ``name``, ``email``, and ``url`` fields.
        """
        if not hasattr(self, "_userinfo"):
            userinfo = {
                "name": self.user_name,
                "email": self.user_email,
                "url": self.user_url
            }
            if self.user_id:
                u = self.user
                if u.email:
                    userinfo["email"] = u.email

                # If the user has a full name, use that for the user name.
                # However, a given user_name overrides the raw user.username,
                # so only use that if this comment has no associated name.
                if u.get_full_name():
                    userinfo["name"] = self.user.get_full_name()
                elif not self.user_name:
                    userinfo["name"] = u.get_username()
            self._userinfo = userinfo
        return self._userinfo
    userinfo = property(_get_userinfo, doc=_get_userinfo.__doc__)

    def _get_name(self):
        return self.userinfo["name"]

    def _set_name(self, val):
        if self.user_id:
            raise AttributeError(_("This comment was posted by an authenticated "\
                                   "user and thus the name is read-only."))
        self.user_name = val
    name = property(_get_name, _set_name, doc="The name of the user who posted this comment")

    def _get_email(self):
        return self.userinfo["email"]

    def _set_email(self, val):
        if self.user_id:
            raise AttributeError(_("This comment was posted by an authenticated "\
                                   "user and thus the email is read-only."))
        self.user_email = val
    email = property(_get_email, _set_email, doc="The email of the user who posted this comment")

    def _get_url(self):
        return self.userinfo["url"]

    def _set_url(self, val):
        self.user_url = val
    url = property(_get_url, _set_url, doc="The URL given by the user who posted this comment")

    def get_absolute_url(self, anchor_pattern="#c%(id)s"):
        return self.get_content_object_url() + (anchor_pattern % self.__dict__)

    def get_as_text(self):
        """
        Return this comment as plain text.  Useful for emails.
        """
        d = {
            'user': self.user or self.name,
            'date': self.submit_date,
            'comment': self.comment,
            'domain': self.site.domain,
            'url': self.get_absolute_url()
        }
        return _('Posted by %(user)s at %(date)s\n\n%(comment)s\n\nhttp://%(domain)s%(url)s') % d


@python_2_unicode_compatible
class CommentFlag(models.Model):
    """
    Records a flag on a comment. This is intentionally flexible; right now, a
    flag could be:

        * A "removal suggestion" -- where a user suggests a comment for (potential) removal.

        * A "moderator deletion" -- used when a moderator deletes a comment.

    You can (ab)use this model to add other flags, if needed. However, by
    design users are only allowed to flag a comment with a given flag once;
    if you want rating look elsewhere.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'), related_name="comment_flags")
    comment = models.ForeignKey(Comment, verbose_name=_('comment'), related_name="flags")
    flag = models.CharField(_('flag'), max_length=30, db_index=True)
    flag_date = models.DateTimeField(_('date'), default=None)

    # Constants for flag types
    SUGGEST_REMOVAL = "removal suggestion"
    MODERATOR_DELETION = "moderator deletion"
    MODERATOR_APPROVAL = "moderator approval"

    class Meta:
        db_table = 'django_comment_flags'
        unique_together = [('user', 'comment', 'flag')]
        verbose_name = _('comment flag')
        verbose_name_plural = _('comment flags')

    def __str__(self):
        return "%s flag of comment ID %s by %s" % \
            (self.flag, self.comment_id, self.user.get_username())

    def save(self, *args, **kwargs):
        if self.flag_date is None:
            self.flag_date = timezone.now()
        super(CommentFlag, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = moderation
"""
A generic comment-moderation system which allows configuration of
moderation options on a per-model basis.

To use, do two things:

1. Create or import a subclass of ``CommentModerator`` defining the
   options you want.

2. Import ``moderator`` from this module and register one or more
   models, passing the models and the ``CommentModerator`` options
   class you want to use.


Example
-------

First, we define a simple model class which might represent entries in
a Weblog::

    from django.db import models

    class Entry(models.Model):
        title = models.CharField(maxlength=250)
        body = models.TextField()
        pub_date = models.DateField()
        enable_comments = models.BooleanField()

Then we create a ``CommentModerator`` subclass specifying some
moderation options::

    from django_comments.moderation import CommentModerator, moderator

    class EntryModerator(CommentModerator):
        email_notification = True
        enable_field = 'enable_comments'

And finally register it for moderation::

    moderator.register(Entry, EntryModerator)

This sample class would apply two moderation steps to each new
comment submitted on an Entry:

* If the entry's ``enable_comments`` field is set to ``False``, the
  comment will be rejected (immediately deleted).

* If the comment is successfully posted, an email notification of the
  comment will be sent to site staff.

For a full list of built-in moderation options and other
configurability, see the documentation for the ``CommentModerator``
class.

"""

import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.base import ModelBase
from django.template import Context, loader
from django.contrib.sites.models import get_current_site
from django.utils import timezone

import django_comments
from django_comments import signals

class AlreadyModerated(Exception):
    """
    Raised when a model which is already registered for moderation is
    attempting to be registered again.

    """
    pass

class NotModerated(Exception):
    """
    Raised when a model which is not registered for moderation is
    attempting to be unregistered.

    """
    pass

class CommentModerator(object):
    """
    Encapsulates comment-moderation options for a given model.

    This class is not designed to be used directly, since it doesn't
    enable any of the available moderation options. Instead, subclass
    it and override attributes to enable different options::

    ``auto_close_field``
        If this is set to the name of a ``DateField`` or
        ``DateTimeField`` on the model for which comments are
        being moderated, new comments for objects of that model
        will be disallowed (immediately deleted) when a certain
        number of days have passed after the date specified in
        that field. Must be used in conjunction with
        ``close_after``, which specifies the number of days past
        which comments should be disallowed. Default value is
        ``None``.

    ``auto_moderate_field``
        Like ``auto_close_field``, but instead of outright
        deleting new comments when the requisite number of days
        have elapsed, it will simply set the ``is_public`` field
        of new comments to ``False`` before saving them. Must be
        used in conjunction with ``moderate_after``, which
        specifies the number of days past which comments should be
        moderated. Default value is ``None``.

    ``close_after``
        If ``auto_close_field`` is used, this must specify the
        number of days past the value of the field specified by
        ``auto_close_field`` after which new comments for an
        object should be disallowed. Default value is ``None``.

    ``email_notification``
        If ``True``, any new comment on an object of this model
        which survives moderation will generate an email to site
        staff. Default value is ``False``.

    ``enable_field``
        If this is set to the name of a ``BooleanField`` on the
        model for which comments are being moderated, new comments
        on objects of that model will be disallowed (immediately
        deleted) whenever the value of that field is ``False`` on
        the object the comment would be attached to. Default value
        is ``None``.

    ``moderate_after``
        If ``auto_moderate_field`` is used, this must specify the number
        of days past the value of the field specified by
        ``auto_moderate_field`` after which new comments for an
        object should be marked non-public. Default value is
        ``None``.

    Most common moderation needs can be covered by changing these
    attributes, but further customization can be obtained by
    subclassing and overriding the following methods. Each method will
    be called with three arguments: ``comment``, which is the comment
    being submitted, ``content_object``, which is the object the
    comment will be attached to, and ``request``, which is the
    ``HttpRequest`` in which the comment is being submitted::

    ``allow``
        Should return ``True`` if the comment should be allowed to
        post on the content object, and ``False`` otherwise (in
        which case the comment will be immediately deleted).

    ``email``
        If email notification of the new comment should be sent to
        site staff or moderators, this method is responsible for
        sending the email.

    ``moderate``
        Should return ``True`` if the comment should be moderated
        (in which case its ``is_public`` field will be set to
        ``False`` before saving), and ``False`` otherwise (in
        which case the ``is_public`` field will not be changed).

    Subclasses which want to introspect the model for which comments
    are being moderated can do so through the attribute ``_model``,
    which will be the model class.

    """
    auto_close_field = None
    auto_moderate_field = None
    close_after = None
    email_notification = False
    enable_field = None
    moderate_after = None

    def __init__(self, model):
        self._model = model

    def _get_delta(self, now, then):
        """
        Internal helper which will return a ``datetime.timedelta``
        representing the time between ``now`` and ``then``. Assumes
        ``now`` is a ``datetime.date`` or ``datetime.datetime`` later
        than ``then``.

        If ``now`` and ``then`` are not of the same type due to one of
        them being a ``datetime.date`` and the other being a
        ``datetime.datetime``, both will be coerced to
        ``datetime.date`` before calculating the delta.

        """
        if now.__class__ is not then.__class__:
            now = datetime.date(now.year, now.month, now.day)
            then = datetime.date(then.year, then.month, then.day)
        if now < then:
            raise ValueError("Cannot determine moderation rules because date field is set to a value in the future")
        return now - then

    def allow(self, comment, content_object, request):
        """
        Determine whether a given comment is allowed to be posted on
        a given object.

        Return ``True`` if the comment should be allowed, ``False
        otherwise.

        """
        if self.enable_field:
            if not getattr(content_object, self.enable_field):
                return False
        if self.auto_close_field and self.close_after is not None:
            close_after_date = getattr(content_object, self.auto_close_field)
            if close_after_date is not None and self._get_delta(timezone.now(), close_after_date).days >= self.close_after:
                return False
        return True

    def moderate(self, comment, content_object, request):
        """
        Determine whether a given comment on a given object should be
        allowed to show up immediately, or should be marked non-public
        and await approval.

        Return ``True`` if the comment should be moderated (marked
        non-public), ``False`` otherwise.

        """
        if self.auto_moderate_field and self.moderate_after is not None:
            moderate_after_date = getattr(content_object, self.auto_moderate_field)
            if moderate_after_date is not None and self._get_delta(timezone.now(), moderate_after_date).days >= self.moderate_after:
                return True
        return False

    def email(self, comment, content_object, request):
        """
        Send email notification of a new comment to site staff when email
        notifications have been requested.

        """
        if not self.email_notification:
            return
        recipient_list = [manager_tuple[1] for manager_tuple in settings.MANAGERS]
        t = loader.get_template('comments/comment_notification_email.txt')
        c = Context({ 'comment': comment,
                      'content_object': content_object })
        subject = '[%s] New comment posted on "%s"' % (get_current_site(request).name,
                                                          content_object)
        message = t.render(c)
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list, fail_silently=True)

class Moderator(object):
    """
    Handles moderation of a set of models.

    An instance of this class will maintain a list of one or more
    models registered for comment moderation, and their associated
    moderation classes, and apply moderation to all incoming comments.

    To register a model, obtain an instance of ``Moderator`` (this
    module exports one as ``moderator``), and call its ``register``
    method, passing the model class and a moderation class (which
    should be a subclass of ``CommentModerator``). Note that both of
    these should be the actual classes, not instances of the classes.

    To cease moderation for a model, call the ``unregister`` method,
    passing the model class.

    For convenience, both ``register`` and ``unregister`` can also
    accept a list of model classes in place of a single model; this
    allows easier registration of multiple models with the same
    ``CommentModerator`` class.

    The actual moderation is applied in two phases: one prior to
    saving a new comment, and the other immediately after saving. The
    pre-save moderation may mark a comment as non-public or mark it to
    be removed; the post-save moderation may delete a comment which
    was disallowed (there is currently no way to prevent the comment
    being saved once before removal) and, if the comment is still
    around, will send any notification emails the comment generated.

    """
    def __init__(self):
        self._registry = {}
        self.connect()

    def connect(self):
        """
        Hook up the moderation methods to pre- and post-save signals
        from the comment models.

        """
        signals.comment_will_be_posted.connect(self.pre_save_moderation, sender=django_comments.get_model())
        signals.comment_was_posted.connect(self.post_save_moderation, sender=django_comments.get_model())

    def register(self, model_or_iterable, moderation_class):
        """
        Register a model or a list of models for comment moderation,
        using a particular moderation class.

        Raise ``AlreadyModerated`` if any of the models are already
        registered.

        """
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model in self._registry:
                raise AlreadyModerated("The model '%s' is already being moderated" % model._meta.module_name)
            self._registry[model] = moderation_class(model)

    def unregister(self, model_or_iterable):
        """
        Remove a model or a list of models from the list of models
        whose comments will be moderated.

        Raise ``NotModerated`` if any of the models are not currently
        registered for moderation.

        """
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model not in self._registry:
                raise NotModerated("The model '%s' is not currently being moderated" % model._meta.module_name)
            del self._registry[model]

    def pre_save_moderation(self, sender, comment, request, **kwargs):
        """
        Apply any necessary pre-save moderation steps to new
        comments.

        """
        model = comment.content_type.model_class()
        if model not in self._registry:
            return
        content_object = comment.content_object
        moderation_class = self._registry[model]

        # Comment will be disallowed outright (HTTP 403 response)
        if not moderation_class.allow(comment, content_object, request):
            return False

        if moderation_class.moderate(comment, content_object, request):
            comment.is_public = False

    def post_save_moderation(self, sender, comment, request, **kwargs):
        """
        Apply any necessary post-save moderation steps to new
        comments.

        """
        model = comment.content_type.model_class()
        if model not in self._registry:
            return
        self._registry[model].email(comment, comment.content_object, request)

# Import this instance in your own code to use in registering
# your models for moderation.
moderator = Moderator()

########NEW FILE########
__FILENAME__ = signals
"""
Signals relating to comments.
"""
from django.dispatch import Signal

# Sent just before a comment will be posted (after it's been approved and
# moderated; this can be used to modify the comment (in place) with posting
# details or other such actions. If any receiver returns False the comment will be
# discarded and a 400 response. This signal is sent at more or less
# the same time (just before, actually) as the Comment object's pre-save signal,
# except that the HTTP request is sent along with this signal.
comment_will_be_posted = Signal(providing_args=["comment", "request"])

# Sent just after a comment was posted. See above for how this differs
# from the Comment object's post-save signal.
comment_was_posted = Signal(providing_args=["comment", "request"])

# Sent after a comment was "flagged" in some way. Check the flag to see if this
# was a user requesting removal of a comment, a moderator approving/removing a
# comment, or some other custom user flag.
comment_was_flagged = Signal(providing_args=["comment", "flag", "created", "request"])

########NEW FILE########
__FILENAME__ = comments
from django import template
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import smart_text

import django_comments

register = template.Library()


class BaseCommentNode(template.Node):
    """
    Base helper class (abstract) for handling the get_comment_* template tags.
    Looks a bit strange, but the subclasses below should make this a bit more
    obvious.
    """

    @classmethod
    def handle_token(cls, parser, token):
        """Class method to parse get_comment_list/count/form and return a Node."""
        tokens = token.split_contents()
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag must be 'for'" % tokens[0])

        # {% get_whatever for obj as varname %}
        if len(tokens) == 5:
            if tokens[3] != 'as':
                raise template.TemplateSyntaxError("Third argument in %r must be 'as'" % tokens[0])
            return cls(
                object_expr = parser.compile_filter(tokens[2]),
                as_varname = tokens[4],
            )

        # {% get_whatever for app.model pk as varname %}
        elif len(tokens) == 6:
            if tokens[4] != 'as':
                raise template.TemplateSyntaxError("Fourth argument in %r must be 'as'" % tokens[0])
            return cls(
                ctype = BaseCommentNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr = parser.compile_filter(tokens[3]),
                as_varname = tokens[5]
            )

        else:
            raise template.TemplateSyntaxError("%r tag requires 4 or 5 arguments" % tokens[0])

    @staticmethod
    def lookup_content_type(token, tagname):
        try:
            app, model = token.split('.')
            return ContentType.objects.get_by_natural_key(app, model)
        except ValueError:
            raise template.TemplateSyntaxError("Third argument in %r must be in the format 'app.model'" % tagname)
        except ContentType.DoesNotExist:
            raise template.TemplateSyntaxError("%r tag has non-existant content-type: '%s.%s'" % (tagname, app, model))

    def __init__(self, ctype=None, object_pk_expr=None, object_expr=None, as_varname=None, comment=None):
        if ctype is None and object_expr is None:
            raise template.TemplateSyntaxError("Comment nodes must be given either a literal object or a ctype and object pk.")
        self.comment_model = django_comments.get_model()
        self.as_varname = as_varname
        self.ctype = ctype
        self.object_pk_expr = object_pk_expr
        self.object_expr = object_expr
        self.comment = comment

    def render(self, context):
        qs = self.get_query_set(context)
        context[self.as_varname] = self.get_context_value_from_queryset(context, qs)
        return ''

    def get_query_set(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if not object_pk:
            return self.comment_model.objects.none()

        qs = self.comment_model.objects.filter(
            content_type = ctype,
            object_pk    = smart_text(object_pk),
            site__pk     = settings.SITE_ID,
        )

        # The is_public and is_removed fields are implementation details of the
        # built-in comment model's spam filtering system, so they might not
        # be present on a custom comment model subclass. If they exist, we
        # should filter on them.
        field_names = [f.name for f in self.comment_model._meta.fields]
        if 'is_public' in field_names:
            qs = qs.filter(is_public=True)
        if getattr(settings, 'COMMENTS_HIDE_REMOVED', True) and 'is_removed' in field_names:
            qs = qs.filter(is_removed=False)

        return qs

    def get_target_ctype_pk(self, context):
        if self.object_expr:
            try:
                obj = self.object_expr.resolve(context)
            except template.VariableDoesNotExist:
                return None, None
            return ContentType.objects.get_for_model(obj), obj.pk
        else:
            return self.ctype, self.object_pk_expr.resolve(context, ignore_failures=True)

    def get_context_value_from_queryset(self, context, qs):
        """Subclasses should override this."""
        raise NotImplementedError

class CommentListNode(BaseCommentNode):
    """Insert a list of comments into the context."""
    def get_context_value_from_queryset(self, context, qs):
        return list(qs)

class CommentCountNode(BaseCommentNode):
    """Insert a count of comments into the context."""
    def get_context_value_from_queryset(self, context, qs):
        return qs.count()

class CommentFormNode(BaseCommentNode):
    """Insert a form for the comment model into the context."""

    def get_form(self, context):
        obj = self.get_object(context)
        if obj:
            return django_comments.get_form()(obj)
        else:
            return None

    def get_object(self, context):
        if self.object_expr:
            try:
                return self.object_expr.resolve(context)
            except template.VariableDoesNotExist:
                return None
        else:
            object_pk = self.object_pk_expr.resolve(context,
                    ignore_failures=True)
            return self.ctype.get_object_for_this_type(pk=object_pk)

    def render(self, context):
        context[self.as_varname] = self.get_form(context)
        return ''

class RenderCommentFormNode(CommentFormNode):
    """Render the comment form directly"""

    @classmethod
    def handle_token(cls, parser, token):
        """Class method to parse render_comment_form and return a Node."""
        tokens = token.split_contents()
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag must be 'for'" % tokens[0])

        # {% render_comment_form for obj %}
        if len(tokens) == 3:
            return cls(object_expr=parser.compile_filter(tokens[2]))

        # {% render_comment_form for app.models pk %}
        elif len(tokens) == 4:
            return cls(
                ctype = BaseCommentNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr = parser.compile_filter(tokens[3])
            )

    def render(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if object_pk:
            template_search_list = [
                "comments/%s/%s/form.html" % (ctype.app_label, ctype.model),
                "comments/%s/form.html" % ctype.app_label,
                "comments/form.html"
            ]
            context.push()
            formstr = render_to_string(template_search_list, {"form" : self.get_form(context)}, context)
            context.pop()
            return formstr
        else:
            return ''

class RenderCommentListNode(CommentListNode):
    """Render the comment list directly"""

    @classmethod
    def handle_token(cls, parser, token):
        """Class method to parse render_comment_list and return a Node."""
        tokens = token.split_contents()
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag must be 'for'" % tokens[0])

        # {% render_comment_list for obj %}
        if len(tokens) == 3:
            return cls(object_expr=parser.compile_filter(tokens[2]))

        # {% render_comment_list for app.models pk %}
        elif len(tokens) == 4:
            return cls(
                ctype = BaseCommentNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr = parser.compile_filter(tokens[3])
            )

    def render(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if object_pk:
            template_search_list = [
                "comments/%s/%s/list.html" % (ctype.app_label, ctype.model),
                "comments/%s/list.html" % ctype.app_label,
                "comments/list.html"
            ]
            qs = self.get_query_set(context)
            context.push()
            liststr = render_to_string(template_search_list, {
                "comment_list" : self.get_context_value_from_queryset(context, qs)
            }, context)
            context.pop()
            return liststr
        else:
            return ''

# We could just register each classmethod directly, but then we'd lose out on
# the automagic docstrings-into-admin-docs tricks. So each node gets a cute
# wrapper function that just exists to hold the docstring.

@register.tag
def get_comment_count(parser, token):
    """
    Gets the comment count for the given params and populates the template
    context with a variable containing that value, whose name is defined by the
    'as' clause.

    Syntax::

        {% get_comment_count for [object] as [varname]  %}
        {% get_comment_count for [app].[model] [object_id] as [varname]  %}

    Example usage::

        {% get_comment_count for event as comment_count %}
        {% get_comment_count for calendar.event event.id as comment_count %}
        {% get_comment_count for calendar.event 17 as comment_count %}

    """
    return CommentCountNode.handle_token(parser, token)

@register.tag
def get_comment_list(parser, token):
    """
    Gets the list of comments for the given params and populates the template
    context with a variable containing that value, whose name is defined by the
    'as' clause.

    Syntax::

        {% get_comment_list for [object] as [varname]  %}
        {% get_comment_list for [app].[model] [object_id] as [varname]  %}

    Example usage::

        {% get_comment_list for event as comment_list %}
        {% for comment in comment_list %}
            ...
        {% endfor %}

    """
    return CommentListNode.handle_token(parser, token)

@register.tag
def render_comment_list(parser, token):
    """
    Render the comment list (as returned by ``{% get_comment_list %}``)
    through the ``comments/list.html`` template

    Syntax::

        {% render_comment_list for [object] %}
        {% render_comment_list for [app].[model] [object_id] %}

    Example usage::

        {% render_comment_list for event %}

    """
    return RenderCommentListNode.handle_token(parser, token)

@register.tag
def get_comment_form(parser, token):
    """
    Get a (new) form object to post a new comment.

    Syntax::

        {% get_comment_form for [object] as [varname] %}
        {% get_comment_form for [app].[model] [object_id] as [varname] %}
    """
    return CommentFormNode.handle_token(parser, token)

@register.tag
def render_comment_form(parser, token):
    """
    Render the comment form (as returned by ``{% render_comment_form %}``) through
    the ``comments/form.html`` template.

    Syntax::

        {% render_comment_form for [object] %}
        {% render_comment_form for [app].[model] [object_id] %}
    """
    return RenderCommentFormNode.handle_token(parser, token)

@register.simple_tag
def comment_form_target():
    """
    Get the target URL for the comment form.

    Example::

        <form action="{% comment_form_target %}" method="post">
    """
    return django_comments.get_form_target()

@register.simple_tag
def get_comment_permalink(comment, anchor_pattern=None):
    """
    Get the permalink for a comment, optionally specifying the format of the
    named anchor to be appended to the end of the URL.

    Example::
        {% get_comment_permalink comment "#c%(id)s-by-%(user_name)s" %}
    """

    if anchor_pattern:
        return comment.get_absolute_url(anchor_pattern)
    return comment.get_absolute_url()


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

urlpatterns = patterns('django_comments.views',
    url(r'^post/$',          'comments.post_comment',       name='comments-post-comment'),
    url(r'^posted/$',        'comments.comment_done',       name='comments-comment-done'),
    url(r'^flag/(\d+)/$',    'moderation.flag',             name='comments-flag'),
    url(r'^flagged/$',       'moderation.flag_done',        name='comments-flag-done'),
    url(r'^delete/(\d+)/$',  'moderation.delete',           name='comments-delete'),
    url(r'^deleted/$',       'moderation.delete_done',      name='comments-delete-done'),
    url(r'^approve/(\d+)/$', 'moderation.approve',          name='comments-approve'),
    url(r'^approved/$',      'moderation.approve_done',     name='comments-approve-done'),
)

urlpatterns += patterns('',
    url(r'^cr/(\d+)/(.+)/$', 'django.contrib.contenttypes.views.shortcut', name='comments-url-redirect'),
)

########NEW FILE########
__FILENAME__ = comments
from __future__ import absolute_import

from django import http
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.html import escape
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

import django_comments
from django_comments import signals
from django_comments.views.utils import next_redirect, confirmation_view

class CommentPostBadRequest(http.HttpResponseBadRequest):
    """
    Response returned when a comment post is invalid. If ``DEBUG`` is on a
    nice-ish error message will be displayed (for debugging purposes), but in
    production mode a simple opaque 400 page will be displayed.
    """
    def __init__(self, why):
        super(CommentPostBadRequest, self).__init__()
        if settings.DEBUG:
            self.content = render_to_string("comments/400-debug.html", {"why": why})


@csrf_protect
@require_POST
def post_comment(request, next=None, using=None):
    """
    Post a comment.

    HTTP POST is required. If ``POST['submit'] == "preview"`` or if there are
    errors a preview template, ``comments/preview.html``, will be rendered.
    """
    # Fill out some initial data fields from an authenticated user, if present
    data = request.POST.copy()
    if request.user.is_authenticated():
        if not data.get('name', ''):
            data["name"] = request.user.get_full_name() or request.user.get_username()
        if not data.get('email', ''):
            data["email"] = request.user.email

    # Look up the object we're trying to comment about
    ctype = data.get("content_type")
    object_pk = data.get("object_pk")
    if ctype is None or object_pk is None:
        return CommentPostBadRequest("Missing content_type or object_pk field.")
    try:
        model = models.get_model(*ctype.split(".", 1))
        target = model._default_manager.using(using).get(pk=object_pk)
    except TypeError:
        return CommentPostBadRequest(
            "Invalid content_type value: %r" % escape(ctype))
    except AttributeError:
        return CommentPostBadRequest(
            "The given content-type %r does not resolve to a valid model." % \
                escape(ctype))
    except ObjectDoesNotExist:
        return CommentPostBadRequest(
            "No object matching content-type %r and object PK %r exists." % \
                (escape(ctype), escape(object_pk)))
    except (ValueError, ValidationError) as e:
        return CommentPostBadRequest(
            "Attempting go get content-type %r and object PK %r exists raised %s" % \
                (escape(ctype), escape(object_pk), e.__class__.__name__))

    # Do we want to preview the comment?
    preview = "preview" in data

    # Construct the comment form
    form = django_comments.get_form()(target, data=data)

    # Check security information
    if form.security_errors():
        return CommentPostBadRequest(
            "The comment form failed security verification: %s" % \
                escape(str(form.security_errors())))

    # If there are errors or if we requested a preview show the comment
    if form.errors or preview:
        template_list = [
            # These first two exist for purely historical reasons.
            # Django v1.0 and v1.1 allowed the underscore format for
            # preview templates, so we have to preserve that format.
            "comments/%s_%s_preview.html" % (model._meta.app_label, model._meta.module_name),
            "comments/%s_preview.html" % model._meta.app_label,
            # Now the usual directory based template hierarchy.
            "comments/%s/%s/preview.html" % (model._meta.app_label, model._meta.module_name),
            "comments/%s/preview.html" % model._meta.app_label,
            "comments/preview.html",
        ]
        return render_to_response(
            template_list, {
                "comment": form.data.get("comment", ""),
                "form": form,
                "next": data.get("next", next),
            },
            RequestContext(request, {})
        )

    # Otherwise create the comment
    comment = form.get_comment_object()
    comment.ip_address = request.META.get("REMOTE_ADDR", None)
    if request.user.is_authenticated():
        comment.user = request.user

    # Signal that the comment is about to be saved
    responses = signals.comment_will_be_posted.send(
        sender=comment.__class__,
        comment=comment,
        request=request
    )

    for (receiver, response) in responses:
        if response == False:
            return CommentPostBadRequest(
                "comment_will_be_posted receiver %r killed the comment" % receiver.__name__)

    # Save the comment and signal that it was saved
    comment.save()
    signals.comment_was_posted.send(
        sender=comment.__class__,
        comment=comment,
        request=request
    )

    return next_redirect(request, fallback=next or 'comments-comment-done',
        c=comment._get_pk_val())

comment_done = confirmation_view(
    template="comments/posted.html",
    doc="""Display a "comment was posted" success page."""
)

########NEW FILE########
__FILENAME__ = moderation
from __future__ import absolute_import

from django import template
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render_to_response
from django.views.decorators.csrf import csrf_protect

import django_comments
from django_comments import signals
from django_comments.views.utils import next_redirect, confirmation_view

@csrf_protect
@login_required
def flag(request, comment_id, next=None):
    """
    Flags a comment. Confirmation on GET, action on POST.

    Templates: :template:`comments/flag.html`,
    Context:
        comment
            the flagged `comments.comment` object
    """
    comment = get_object_or_404(django_comments.get_model(), pk=comment_id, site__pk=settings.SITE_ID)

    # Flag on POST
    if request.method == 'POST':
        perform_flag(request, comment)
        return next_redirect(request, fallback=next or 'comments-flag-done',
            c=comment.pk)

    # Render a form on GET
    else:
        return render_to_response('comments/flag.html',
            {'comment': comment, "next": next},
            template.RequestContext(request)
        )

@csrf_protect
@permission_required("django_comments.can_moderate")
def delete(request, comment_id, next=None):
    """
    Deletes a comment. Confirmation on GET, action on POST. Requires the "can
    moderate comments" permission.

    Templates: :template:`comments/delete.html`,
    Context:
        comment
            the flagged `comments.comment` object
    """
    comment = get_object_or_404(django_comments.get_model(), pk=comment_id, site__pk=settings.SITE_ID)

    # Delete on POST
    if request.method == 'POST':
        # Flag the comment as deleted instead of actually deleting it.
        perform_delete(request, comment)
        return next_redirect(request, fallback=next or 'comments-delete-done',
            c=comment.pk)

    # Render a form on GET
    else:
        return render_to_response('comments/delete.html',
            {'comment': comment, "next": next},
            template.RequestContext(request)
        )

@csrf_protect
@permission_required("django_comments.can_moderate")
def approve(request, comment_id, next=None):
    """
    Approve a comment (that is, mark it as public and non-removed). Confirmation
    on GET, action on POST. Requires the "can moderate comments" permission.

    Templates: :template:`comments/approve.html`,
    Context:
        comment
            the `comments.comment` object for approval
    """
    comment = get_object_or_404(django_comments.get_model(), pk=comment_id, site__pk=settings.SITE_ID)

    # Delete on POST
    if request.method == 'POST':
        # Flag the comment as approved.
        perform_approve(request, comment)
        return next_redirect(request, fallback=next or 'comments-approve-done',
            c=comment.pk)

    # Render a form on GET
    else:
        return render_to_response('comments/approve.html',
            {'comment': comment, "next": next},
            template.RequestContext(request)
        )

# The following functions actually perform the various flag/aprove/delete
# actions. They've been broken out into separate functions to that they
# may be called from admin actions.

def perform_flag(request, comment):
    """
    Actually perform the flagging of a comment from a request.
    """
    flag, created = django_comments.models.CommentFlag.objects.get_or_create(
        comment = comment,
        user    = request.user,
        flag    = django_comments.models.CommentFlag.SUGGEST_REMOVAL
    )
    signals.comment_was_flagged.send(
        sender  = comment.__class__,
        comment = comment,
        flag    = flag,
        created = created,
        request = request,
    )

def perform_delete(request, comment):
    flag, created = django_comments.models.CommentFlag.objects.get_or_create(
        comment = comment,
        user    = request.user,
        flag    = django_comments.models.CommentFlag.MODERATOR_DELETION
    )
    comment.is_removed = True
    comment.save()
    signals.comment_was_flagged.send(
        sender  = comment.__class__,
        comment = comment,
        flag    = flag,
        created = created,
        request = request,
    )


def perform_approve(request, comment):
    flag, created = django_comments.models.CommentFlag.objects.get_or_create(
        comment = comment,
        user    = request.user,
        flag    = django_comments.models.CommentFlag.MODERATOR_APPROVAL,
    )

    comment.is_removed = False
    comment.is_public = True
    comment.save()

    signals.comment_was_flagged.send(
        sender  = comment.__class__,
        comment = comment,
        flag    = flag,
        created = created,
        request = request,
    )

# Confirmation views.

flag_done = confirmation_view(
    template = "comments/flagged.html",
    doc = 'Displays a "comment was flagged" success page.'
)
delete_done = confirmation_view(
    template = "comments/deleted.html",
    doc = 'Displays a "comment was deleted" success page.'
)
approve_done = confirmation_view(
    template = "comments/approved.html",
    doc = 'Displays a "comment was approved" success page.'
)

########NEW FILE########
__FILENAME__ = utils
"""
A few bits of helper functions for comment views.
"""

import textwrap
try:
    from urllib.parse import urlencode
except ImportError:     # Python 2
    from urllib import urlencode

from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, resolve_url
from django.template import RequestContext
from django.core.exceptions import ObjectDoesNotExist
from django.utils.http import is_safe_url

import django_comments

def next_redirect(request, fallback, **get_kwargs):
    """
    Handle the "where should I go next?" part of comment views.

    The next value could be a
    ``?next=...`` GET arg or the URL of a given view (``fallback``). See
    the view modules for examples.

    Returns an ``HttpResponseRedirect``.
    """
    next = request.POST.get('next')
    if not is_safe_url(url=next, host=request.get_host()):
        next = resolve_url(fallback)

    if get_kwargs:
        if '#' in next:
            tmp = next.rsplit('#', 1)
            next = tmp[0]
            anchor = '#' + tmp[1]
        else:
            anchor = ''

        joiner = ('?' in next) and '&' or '?'
        next += joiner + urlencode(get_kwargs) + anchor
    return HttpResponseRedirect(next)

def confirmation_view(template, doc="Display a confirmation view."):
    """
    Confirmation view generator for the "comment was
    posted/flagged/deleted/approved" views.
    """
    def confirmed(request):
        comment = None
        if 'c' in request.GET:
            try:
                comment = django_comments.get_model().objects.get(pk=request.GET['c'])
            except (ObjectDoesNotExist, ValueError):
                pass
        return render_to_response(template,
            {'comment': comment},
            context_instance=RequestContext(request)
        )

    confirmed.__doc__ = textwrap.dedent("""\
        %s

        Templates: :template:`%s``
        Context:
            comment
                The posted comment
        """ % (doc, template)
    )
    return confirmed

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Django Comments documentation build configuration file, created by
# sphinx-quickstart on Mon Mar 11 10:23:49 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.intersphinx', 'extensions']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.txt'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Django Comments'
copyright = u'2013, Django Software Foundation and contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.5'
# The full version, including alpha/beta/rc tags.
release = '1.5'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

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
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'DjangoCommentsdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('newindex', 'DjangoComments.tex', u'Django Comments Documentation',
   u'Django Software Foundation and contributors', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('newindex', 'djangocomments', u'Django Comments Documentation',
     [u'Django Software Foundation and contributors'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('newindex', 'DjangoComments', u'Django Comments Documentation',
   u'Django Software Foundation and contributors', 'DjangoComments', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'Django Comments'
epub_author = u'Django Software Foundation and contributors'
epub_publisher = u'Django Software Foundation and contributors'
epub_copyright = u'2013, Django Software Foundation and contributors'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
#epub_cover = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'python': ('http://docs.python.org/', None),
    'django': ('http://docs.djangoproject.com/en/stable', 'http://docs.djangoproject.com/en/stable/_objects'),
}

########NEW FILE########
__FILENAME__ = extensions
def setup(app):
    app.add_crossref_type(
        directivename = "setting",
        rolename      = "setting",
        indextemplate = "pair: %s; setting",
    )
    app.add_crossref_type(
        directivename = "templatetag",
        rolename      = "ttag",
        indextemplate = "pair: %s; template tag"
    )
    app.add_crossref_type(
        directivename = "templatefilter",
        rolename      = "tfilter",
        indextemplate = "pair: %s; template filter"
    )

########NEW FILE########
__FILENAME__ = forms
from django import forms


class CustomCommentForm(forms.Form):
    pass

########NEW FILE########
__FILENAME__ = models
from django.db import models


class CustomComment(models.Model):
    pass

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse


def custom_submit_comment(request):
    return HttpResponse("Hello from the custom submit comment view.")

def custom_flag_comment(request, comment_id):
    return HttpResponse("Hello from the custom flag view.")

def custom_delete_comment(request, comment_id):
    return HttpResponse("Hello from the custom delete view.")

def custom_approve_comment(request, comment_id):
    return HttpResponse("Hello from the custom approve view.")

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

"""
Adapted from django-constance, which itself was adapted from django-adminfiles.
"""

import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
parent = os.path.dirname(here)
sys.path[0:0] = [here, parent]

from django.conf import settings
settings.configure(
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3'}},
    INSTALLED_APPS = [
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.sites",
        "django.contrib.admin",
        "django_comments",
        "testapp",
        "custom_comments",
    ],
    ROOT_URLCONF = 'testapp.urls',
    SECRET_KEY = "it's a secret to everyone",
    SITE_ID = 1,
)

from django.test.simple import DjangoTestSuiteRunner

def main():
    runner = DjangoTestSuiteRunner(failfast=True, verbosity=1)
    failures = runner.run_tests(['testapp'], interactive=True)
    sys.exit(failures)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = models
"""
Comments may be attached to any object. See the comment documentation for
more information.
"""

from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Author(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)

@python_2_unicode_compatible
class Article(models.Model):
    author = models.ForeignKey(Author)
    headline = models.CharField(max_length=100)

    def __str__(self):
        return self.headline

@python_2_unicode_compatible
class Entry(models.Model):
    title = models.CharField(max_length=250)
    body = models.TextField()
    pub_date = models.DateField()
    enable_comments = models.BooleanField()

    def __str__(self):
        return self.title

class Book(models.Model):
    dewey_decimal = models.DecimalField(primary_key=True, decimal_places=2, max_digits=5)

########NEW FILE########
__FILENAME__ = app_api_tests
from __future__ import absolute_import

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test.utils import override_settings
from django.utils import six

import django_comments
from django_comments.models import Comment
from django_comments.forms import CommentForm

from . import CommentTestCase


class CommentAppAPITests(CommentTestCase):
    """Tests for the "comment app" API"""

    def testGetCommentApp(self):
        self.assertEqual(django_comments.get_comment_app(), django_comments)

    @override_settings(
        COMMENTS_APP='missing_app',
        INSTALLED_APPS=list(settings.INSTALLED_APPS) + ['missing_app'],
    )
    def testGetMissingCommentApp(self):
        with six.assertRaisesRegex(self, ImproperlyConfigured, 'missing_app'):
            _ = django_comments.get_comment_app()

    def testGetForm(self):
        self.assertEqual(django_comments.get_form(), CommentForm)

    def testGetFormTarget(self):
        self.assertEqual(django_comments.get_form_target(), "/post/")

    def testGetFlagURL(self):
        c = Comment(id=12345)
        self.assertEqual(django_comments.get_flag_url(c), "/flag/12345/")

    def getGetDeleteURL(self):
        c = Comment(id=12345)
        self.assertEqual(django_comments.get_delete_url(c), "/delete/12345/")

    def getGetApproveURL(self):
        c = Comment(id=12345)
        self.assertEqual(django_comments.get_approve_url(c), "/approve/12345/")


@override_settings(
    COMMENTS_APP='custom_comments',
    INSTALLED_APPS=list(settings.INSTALLED_APPS) + [
        'custom_comments'],
)
class CustomCommentTest(CommentTestCase):
    urls = 'testapp.urls'

    def testGetCommentApp(self):
        import custom_comments
        self.assertEqual(django_comments.get_comment_app(), custom_comments)

    def testGetModel(self):
        from custom_comments.models import CustomComment
        self.assertEqual(django_comments.get_model(), CustomComment)

    def testGetForm(self):
        from custom_comments.forms import CustomCommentForm
        self.assertEqual(django_comments.get_form(), CustomCommentForm)

    def testGetFormTarget(self):
        self.assertEqual(django_comments.get_form_target(), "/post/")

    def testGetFlagURL(self):
        c = Comment(id=12345)
        self.assertEqual(django_comments.get_flag_url(c), "/flag/12345/")

    def getGetDeleteURL(self):
        c = Comment(id=12345)
        self.assertEqual(django_comments.get_delete_url(c), "/delete/12345/")

    def getGetApproveURL(self):
        c = Comment(id=12345)
        self.assertEqual(django_comments.get_approve_url(c), "/approve/12345/")

########NEW FILE########
__FILENAME__ = comment_form_tests
from __future__ import absolute_import

import time

from django.conf import settings

from django_comments.forms import CommentForm
from django_comments.models import Comment

from . import CommentTestCase
from ..models import Article


class CommentFormTests(CommentTestCase):
    def testInit(self):
        f = CommentForm(Article.objects.get(pk=1))
        self.assertEqual(f.initial['content_type'], str(Article._meta))
        self.assertEqual(f.initial['object_pk'], "1")
        self.assertNotEqual(f.initial['security_hash'], None)
        self.assertNotEqual(f.initial['timestamp'], None)

    def testValidPost(self):
        a = Article.objects.get(pk=1)
        f = CommentForm(a, data=self.getValidData(a))
        self.assertTrue(f.is_valid(), f.errors)
        return f

    def tamperWithForm(self, **kwargs):
        a = Article.objects.get(pk=1)
        d = self.getValidData(a)
        d.update(kwargs)
        f = CommentForm(Article.objects.get(pk=1), data=d)
        self.assertFalse(f.is_valid())
        return f

    def testHoneypotTampering(self):
        self.tamperWithForm(honeypot="I am a robot")

    def testTimestampTampering(self):
        self.tamperWithForm(timestamp=str(time.time() - 28800))

    def testSecurityHashTampering(self):
        self.tamperWithForm(security_hash="Nobody expects the Spanish Inquisition!")

    def testContentTypeTampering(self):
        self.tamperWithForm(content_type="auth.user")

    def testObjectPKTampering(self):
        self.tamperWithForm(object_pk="3")

    def testSecurityErrors(self):
        f = self.tamperWithForm(honeypot="I am a robot")
        self.assertTrue("honeypot" in f.security_errors())

    def testGetCommentObject(self):
        f = self.testValidPost()
        c = f.get_comment_object()
        self.assertTrue(isinstance(c, Comment))
        self.assertEqual(c.content_object, Article.objects.get(pk=1))
        self.assertEqual(c.comment, "This is my comment")
        c.save()
        self.assertEqual(Comment.objects.count(), 1)

    def testProfanities(self):
        """Test COMMENTS_ALLOW_PROFANITIES and PROFANITIES_LIST settings"""
        a = Article.objects.get(pk=1)
        d = self.getValidData(a)

        # Save settings in case other tests need 'em
        saved = settings.PROFANITIES_LIST, settings.COMMENTS_ALLOW_PROFANITIES

        # Don't wanna swear in the unit tests if we don't have to...
        settings.PROFANITIES_LIST = ["rooster"]

        # Try with COMMENTS_ALLOW_PROFANITIES off
        settings.COMMENTS_ALLOW_PROFANITIES = False
        f = CommentForm(a, data=dict(d, comment="What a rooster!"))
        self.assertFalse(f.is_valid())

        # Now with COMMENTS_ALLOW_PROFANITIES on
        settings.COMMENTS_ALLOW_PROFANITIES = True
        f = CommentForm(a, data=dict(d, comment="What a rooster!"))
        self.assertTrue(f.is_valid())

        # Restore settings
        settings.PROFANITIES_LIST, settings.COMMENTS_ALLOW_PROFANITIES = saved

########NEW FILE########
__FILENAME__ = comment_utils_moderators_tests
from __future__ import absolute_import

from django.core import mail
from django.test.utils import override_settings

from django_comments.models import Comment
from django_comments.moderation import (moderator, CommentModerator,
    AlreadyModerated)

from . import CommentTestCase
from ..models import Entry


class EntryModerator1(CommentModerator):
    email_notification = True

class EntryModerator2(CommentModerator):
    enable_field = 'enable_comments'

class EntryModerator3(CommentModerator):
    auto_close_field = 'pub_date'
    close_after = 7

class EntryModerator4(CommentModerator):
    auto_moderate_field = 'pub_date'
    moderate_after = 7

class EntryModerator5(CommentModerator):
    auto_moderate_field = 'pub_date'
    moderate_after = 0

class EntryModerator6(CommentModerator):
    auto_close_field = 'pub_date'
    close_after = 0

class CommentUtilsModeratorTests(CommentTestCase):
    fixtures = ["comment_utils.xml"]

    def createSomeComments(self):
        # Tests for the moderation signals must actually post data
        # through the comment views, because only the comment views
        # emit the custom signals moderation listens for.
        e = Entry.objects.get(pk=1)
        data = self.getValidData(e)

        self.client.post("/post/", data, REMOTE_ADDR="1.2.3.4")

        # We explicitly do a try/except to get the comment we've just
        # posted because moderation may have disallowed it, in which
        # case we can just return it as None.
        try:
            c1 = Comment.objects.all()[0]
        except IndexError:
            c1 = None

        self.client.post("/post/", data, REMOTE_ADDR="1.2.3.4")

        try:
            c2 = Comment.objects.all()[0]
        except IndexError:
            c2 = None
        return c1, c2

    def tearDown(self):
        moderator.unregister(Entry)

    def testRegisterExistingModel(self):
        moderator.register(Entry, EntryModerator1)
        self.assertRaises(AlreadyModerated, moderator.register, Entry, EntryModerator1)

    def testEmailNotification(self):
        with override_settings(MANAGERS=("test@example.com",)):
            moderator.register(Entry, EntryModerator1)
            self.createSomeComments()
            self.assertEqual(len(mail.outbox), 2)

    def testCommentsEnabled(self):
        moderator.register(Entry, EntryModerator2)
        self.createSomeComments()
        self.assertEqual(Comment.objects.all().count(), 1)

    def testAutoCloseField(self):
        moderator.register(Entry, EntryModerator3)
        self.createSomeComments()
        self.assertEqual(Comment.objects.all().count(), 0)

    def testAutoModerateField(self):
        moderator.register(Entry, EntryModerator4)
        c1, c2 = self.createSomeComments()
        self.assertEqual(c2.is_public, False)

    def testAutoModerateFieldImmediate(self):
        moderator.register(Entry, EntryModerator5)
        c1, c2 = self.createSomeComments()
        self.assertEqual(c2.is_public, False)

    def testAutoCloseFieldImmediate(self):
        moderator.register(Entry, EntryModerator6)
        c1, c2 = self.createSomeComments()
        self.assertEqual(Comment.objects.all().count(), 0)

########NEW FILE########
__FILENAME__ = comment_view_tests
from __future__ import absolute_import, unicode_literals

import re

from django.conf import settings
from django.contrib.auth.models import User

from django_comments import signals
from django_comments.models import Comment

from . import CommentTestCase
from ..models import Article, Book


post_redirect_re = re.compile(r'^http://testserver/posted/\?c=(?P<pk>\d+$)')

class CommentViewTests(CommentTestCase):

    def testPostCommentHTTPMethods(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        response = self.client.get("/post/", data)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response["Allow"], "POST")

    def testPostCommentMissingCtype(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        del data["content_type"]
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)

    def testPostCommentBadCtype(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["content_type"] = "Nobody expects the Spanish Inquisition!"
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)

    def testPostCommentMissingObjectPK(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        del data["object_pk"]
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)

    def testPostCommentBadObjectPK(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["object_pk"] = "14"
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)

    def testPostInvalidIntegerPK(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["comment"] = "This is another comment"
        data["object_pk"] = '\ufffd'
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)

    def testPostInvalidDecimalPK(self):
        b = Book.objects.get(pk='12.34')
        data = self.getValidData(b)
        data["comment"] = "This is another comment"
        data["object_pk"] = 'cookies'
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)

    def testCommentPreview(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["preview"] = "Preview"
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "comments/preview.html")

    def testHashTampering(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["security_hash"] = "Nobody expects the Spanish Inquisition!"
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)

    def testDebugCommentErrors(self):
        """The debug error template should be shown only if DEBUG is True"""
        olddebug = settings.DEBUG

        settings.DEBUG = True
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["security_hash"] = "Nobody expects the Spanish Inquisition!"
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, "comments/400-debug.html")

        settings.DEBUG = False
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)
        self.assertTemplateNotUsed(response, "comments/400-debug.html")

        settings.DEBUG = olddebug

    def testCreateValidComment(self):
        address = "1.2.3.4"
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        self.response = self.client.post("/post/", data, REMOTE_ADDR=address)
        self.assertEqual(self.response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 1)
        c = Comment.objects.all()[0]
        self.assertEqual(c.ip_address, address)
        self.assertEqual(c.comment, "This is my comment")

    def testCreateValidCommentIPv6(self):
        """
        Test creating a valid comment with a long IPv6 address.
        Note that this test should fail when Comment.ip_address is an IPAddress instead of a GenericIPAddress,
        but does not do so on SQLite or PostgreSQL, because they use the TEXT and INET types, which already
        allow storing an IPv6 address internally.
        """
        address = "2a02::223:6cff:fe8a:2e8a"
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        self.response = self.client.post("/post/", data, REMOTE_ADDR=address)
        self.assertEqual(self.response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 1)
        c = Comment.objects.all()[0]
        self.assertEqual(c.ip_address, address)
        self.assertEqual(c.comment, "This is my comment")

    def testCreateValidCommentIPv6Unpack(self):
        address = "::ffff:18.52.18.52"
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        self.response = self.client.post("/post/", data, REMOTE_ADDR=address)
        self.assertEqual(self.response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 1)
        c = Comment.objects.all()[0]
        # We trim the '::ffff:' bit off because it is an IPv4 addr
        self.assertEqual(c.ip_address, address[7:])
        self.assertEqual(c.comment, "This is my comment")

    def testPostAsAuthenticatedUser(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data['name'] = data['email'] = ''
        self.client.login(username="normaluser", password="normaluser")
        self.response = self.client.post("/post/", data, REMOTE_ADDR="1.2.3.4")
        self.assertEqual(self.response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 1)
        c = Comment.objects.all()[0]
        self.assertEqual(c.ip_address, "1.2.3.4")
        u = User.objects.get(username='normaluser')
        self.assertEqual(c.user, u)
        self.assertEqual(c.user_name, u.get_full_name())
        self.assertEqual(c.user_email, u.email)

    def testPostAsAuthenticatedUserWithoutFullname(self):
        """
        Check that the user's name in the comment is populated for
        authenticated users without first_name and last_name.
        """
        user = User.objects.create_user(username='jane_other',
                email='jane@example.com', password='jane_other')
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data['name'] = data['email'] = ''
        self.client.login(username="jane_other", password="jane_other")
        self.response = self.client.post("/post/", data, REMOTE_ADDR="1.2.3.4")
        c = Comment.objects.get(user=user)
        self.assertEqual(c.ip_address, "1.2.3.4")
        self.assertEqual(c.user_name, 'jane_other')
        user.delete()

    def testPreventDuplicateComments(self):
        """Prevent posting the exact same comment twice"""
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        self.client.post("/post/", data)
        self.client.post("/post/", data)
        self.assertEqual(Comment.objects.count(), 1)

        # This should not trigger the duplicate prevention
        self.client.post("/post/", dict(data, comment="My second comment."))
        self.assertEqual(Comment.objects.count(), 2)

    def testCommentSignals(self):
        """Test signals emitted by the comment posting view"""

        # callback
        def receive(sender, **kwargs):
            self.assertEqual(kwargs['comment'].comment, "This is my comment")
            self.assertTrue('request' in kwargs)
            received_signals.append(kwargs.get('signal'))

        # Connect signals and keep track of handled ones
        received_signals = []
        expected_signals = [
            signals.comment_will_be_posted, signals.comment_was_posted
        ]
        for signal in expected_signals:
            signal.connect(receive)

        # Post a comment and check the signals
        self.testCreateValidComment()
        self.assertEqual(received_signals, expected_signals)

        for signal in expected_signals:
            signal.disconnect(receive)

    def testWillBePostedSignal(self):
        """
        Test that the comment_will_be_posted signal can prevent the comment from
        actually getting saved
        """
        def receive(sender, **kwargs): return False
        signals.comment_will_be_posted.connect(receive, dispatch_uid="comment-test")
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Comment.objects.count(), 0)
        signals.comment_will_be_posted.disconnect(dispatch_uid="comment-test")

    def testWillBePostedSignalModifyComment(self):
        """
        Test that the comment_will_be_posted signal can modify a comment before
        it gets posted
        """
        def receive(sender, **kwargs):
             # a bad but effective spam filter :)...
            kwargs['comment'].is_public = False

        signals.comment_will_be_posted.connect(receive)
        self.testCreateValidComment()
        c = Comment.objects.all()[0]
        self.assertFalse(c.is_public)

    def testCommentNext(self):
        """Test the different "next" actions the comment view can take"""
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        response = self.client.post("/post/", data)
        location = response["Location"]
        match = post_redirect_re.match(location)
        self.assertTrue(match != None, "Unexpected redirect location: %s" % location)

        data["next"] = "/somewhere/else/"
        data["comment"] = "This is another comment"
        response = self.client.post("/post/", data)
        location = response["Location"]
        match = re.search(r"^http://testserver/somewhere/else/\?c=\d+$", location)
        self.assertTrue(match != None, "Unexpected redirect location: %s" % location)

        data["next"] = "http://badserver/somewhere/else/"
        data["comment"] = "This is another comment with an unsafe next url"
        response = self.client.post("/post/", data)
        location = response["Location"]
        match = post_redirect_re.match(location)
        self.assertTrue(match != None, "Unsafe redirection to: %s" % location)

    def testCommentDoneView(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        response = self.client.post("/post/", data)
        location = response["Location"]
        match = post_redirect_re.match(location)
        self.assertTrue(match != None, "Unexpected redirect location: %s" % location)
        pk = int(match.group('pk'))
        response = self.client.get(location)
        self.assertTemplateUsed(response, "comments/posted.html")
        self.assertEqual(response.context[0]["comment"], Comment.objects.get(pk=pk))

    def testCommentNextWithQueryString(self):
        """
        The `next` key needs to handle already having a query string (#10585)
        """
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["next"] = "/somewhere/else/?foo=bar"
        data["comment"] = "This is another comment"
        response = self.client.post("/post/", data)
        location = response["Location"]
        match = re.search(r"^http://testserver/somewhere/else/\?foo=bar&c=\d+$", location)
        self.assertTrue(match != None, "Unexpected redirect location: %s" % location)

    def testCommentPostRedirectWithInvalidIntegerPK(self):
        """
        Tests that attempting to retrieve the location specified in the
        post redirect, after adding some invalid data to the expected
        querystring it ends with, doesn't cause a server error.
        """
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["comment"] = "This is another comment"
        response = self.client.post("/post/", data)
        location = response["Location"]
        broken_location = location + "\ufffd"
        response = self.client.get(broken_location)
        self.assertEqual(response.status_code, 200)

    def testCommentNextWithQueryStringAndAnchor(self):
        """
        The `next` key needs to handle already having an anchor. Refs #13411.
        """
        # With a query string also.
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["next"] = "/somewhere/else/?foo=bar#baz"
        data["comment"] = "This is another comment"
        response = self.client.post("/post/", data)
        location = response["Location"]
        match = re.search(r"^http://testserver/somewhere/else/\?foo=bar&c=\d+#baz$", location)
        self.assertTrue(match != None, "Unexpected redirect location: %s" % location)

        # Without a query string
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["next"] = "/somewhere/else/#baz"
        data["comment"] = "This is another comment"
        response = self.client.post("/post/", data)
        location = response["Location"]
        match = re.search(r"^http://testserver/somewhere/else/\?c=\d+#baz$", location)
        self.assertTrue(match != None, "Unexpected redirect location: %s" % location)

########NEW FILE########
__FILENAME__ = feed_tests
from __future__ import absolute_import

from xml.etree import ElementTree as ET

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site

from django_comments.models import Comment

from . import CommentTestCase
from ..models import Article


class CommentFeedTests(CommentTestCase):
    urls = 'testapp.urls'
    feed_url = '/rss/comments/'

    def setUp(self):
        site_2 = Site.objects.create(id=settings.SITE_ID+1,
            domain="example2.com", name="example2.com")
        # A comment for another site
        c5 = Comment.objects.create(
            content_type = ContentType.objects.get_for_model(Article),
            object_pk = "1",
            user_name = "Joe Somebody",
            user_email = "jsomebody@example.com",
            user_url = "http://example.com/~joe/",
            comment = "A comment for the second site.",
            site = site_2,
        )

    def test_feed(self):
        response = self.client.get(self.feed_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/rss+xml; charset=utf-8')

        rss_elem = ET.fromstring(response.content)

        self.assertEqual(rss_elem.tag, "rss")
        self.assertEqual(rss_elem.attrib, {"version": "2.0"})

        channel_elem = rss_elem.find("channel")

        title_elem = channel_elem.find("title")
        self.assertEqual(title_elem.text, "example.com comments")

        link_elem = channel_elem.find("link")
        self.assertEqual(link_elem.text, "http://example.com/")

        atomlink_elem = channel_elem.find("{http://www.w3.org/2005/Atom}link")
        self.assertEqual(atomlink_elem.attrib, {"href": "http://example.com/rss/comments/", "rel": "self"})

        self.assertNotContains(response, "A comment for the second site.")

########NEW FILE########
__FILENAME__ = model_tests
from __future__ import absolute_import

from django_comments.models import Comment

from . import CommentTestCase
from ..models import Author, Article


class CommentModelTests(CommentTestCase):
    def testSave(self):
        for c in self.createSomeComments():
            self.assertNotEqual(c.submit_date, None)

    def testUserProperties(self):
        c1, c2, c3, c4 = self.createSomeComments()
        self.assertEqual(c1.name, "Joe Somebody")
        self.assertEqual(c2.email, "jsomebody@example.com")
        self.assertEqual(c3.name, "Frank Nobody")
        self.assertEqual(c3.url, "http://example.com/~frank/")
        self.assertEqual(c1.user, None)
        self.assertEqual(c3.user, c4.user)

class CommentManagerTests(CommentTestCase):

    def testInModeration(self):
        """Comments that aren't public are considered in moderation"""
        c1, c2, c3, c4 = self.createSomeComments()
        c1.is_public = False
        c2.is_public = False
        c1.save()
        c2.save()
        moderated_comments = list(Comment.objects.in_moderation().order_by("id"))
        self.assertEqual(moderated_comments, [c1, c2])

    def testRemovedCommentsNotInModeration(self):
        """Removed comments are not considered in moderation"""
        c1, c2, c3, c4 = self.createSomeComments()
        c1.is_public = False
        c2.is_public = False
        c2.is_removed = True
        c1.save()
        c2.save()
        moderated_comments = list(Comment.objects.in_moderation())
        self.assertEqual(moderated_comments, [c1])

    def testForModel(self):
        c1, c2, c3, c4 = self.createSomeComments()
        article_comments = list(Comment.objects.for_model(Article).order_by("id"))
        author_comments = list(Comment.objects.for_model(Author.objects.get(pk=1)))
        self.assertEqual(article_comments, [c1, c3])
        self.assertEqual(author_comments, [c2])

    def testPrefetchRelated(self):
        c1, c2, c3, c4 = self.createSomeComments()
        # one for comments, one for Articles, one for Author
        with self.assertNumQueries(3):
            qs = Comment.objects.prefetch_related('content_object')
            [c.content_object for c in qs]

########NEW FILE########
__FILENAME__ = moderation_view_tests
from __future__ import absolute_import, unicode_literals

from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import translation

from django_comments import signals
from django_comments.models import Comment, CommentFlag

from . import CommentTestCase


class FlagViewTests(CommentTestCase):

    def testFlagGet(self):
        """GET the flag view: render a confirmation page."""
        comments = self.createSomeComments()
        pk = comments[0].pk
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.get("/flag/%d/" % pk)
        self.assertTemplateUsed(response, "comments/flag.html")

    def testFlagPost(self):
        """POST the flag view: actually flag the view (nice for XHR)"""
        comments = self.createSomeComments()
        pk = comments[0].pk
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/flag/%d/" % pk)
        self.assertEqual(response["Location"], "http://testserver/flagged/?c=%d" % pk)
        c = Comment.objects.get(pk=pk)
        self.assertEqual(c.flags.filter(flag=CommentFlag.SUGGEST_REMOVAL).count(), 1)
        return c

    def testFlagPostNext(self):
        """
        POST the flag view, explicitly providing a next url.
        """
        comments = self.createSomeComments()
        pk = comments[0].pk
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/flag/%d/" % pk, {'next': "/go/here/"})
        self.assertEqual(response["Location"],
            "http://testserver/go/here/?c=%d" % pk)

    def testFlagPostUnsafeNext(self):
        """
        POSTing to the flag view with an unsafe next url will ignore the
        provided url when redirecting.
        """
        comments = self.createSomeComments()
        pk = comments[0].pk
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/flag/%d/" % pk,
            {'next': "http://elsewhere/bad"})
        self.assertEqual(response["Location"],
            "http://testserver/flagged/?c=%d" % pk)

    def testFlagPostTwice(self):
        """Users don't get to flag comments more than once."""
        c = self.testFlagPost()
        self.client.post("/flag/%d/" % c.pk)
        self.client.post("/flag/%d/" % c.pk)
        self.assertEqual(c.flags.filter(flag=CommentFlag.SUGGEST_REMOVAL).count(), 1)

    def testFlagAnon(self):
        """GET/POST the flag view while not logged in: redirect to log in."""
        comments = self.createSomeComments()
        pk = comments[0].pk
        response = self.client.get("/flag/%d/" % pk)
        self.assertEqual(response["Location"], "http://testserver/accounts/login/?next=/flag/%d/" % pk)
        response = self.client.post("/flag/%d/" % pk)
        self.assertEqual(response["Location"], "http://testserver/accounts/login/?next=/flag/%d/" % pk)

    def testFlaggedView(self):
        comments = self.createSomeComments()
        pk = comments[0].pk
        response = self.client.get("/flagged/", data={"c": pk})
        self.assertTemplateUsed(response, "comments/flagged.html")

    def testFlagSignals(self):
        """Test signals emitted by the comment flag view"""

        # callback
        def receive(sender, **kwargs):
            self.assertEqual(kwargs['flag'].flag, CommentFlag.SUGGEST_REMOVAL)
            self.assertEqual(kwargs['request'].user.username, "normaluser")
            received_signals.append(kwargs.get('signal'))

        # Connect signals and keep track of handled ones
        received_signals = []
        signals.comment_was_flagged.connect(receive)

        # Post a comment and check the signals
        self.testFlagPost()
        self.assertEqual(received_signals, [signals.comment_was_flagged])

        signals.comment_was_flagged.disconnect(receive)

def makeModerator(username):
    u = User.objects.get(username=username)
    ct = ContentType.objects.get_for_model(Comment)
    p = Permission.objects.get(content_type=ct, codename="can_moderate")
    u.user_permissions.add(p)

class DeleteViewTests(CommentTestCase):

    def testDeletePermissions(self):
        """The delete view should only be accessible to 'moderators'"""
        comments = self.createSomeComments()
        pk = comments[0].pk
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.get("/delete/%d/" % pk)
        self.assertEqual(response["Location"], "http://testserver/accounts/login/?next=/delete/%d/" % pk)

        makeModerator("normaluser")
        response = self.client.get("/delete/%d/" % pk)
        self.assertEqual(response.status_code, 200)

    def testDeletePost(self):
        """POSTing the delete view should mark the comment as removed"""
        comments = self.createSomeComments()
        pk = comments[0].pk
        makeModerator("normaluser")
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/delete/%d/" % pk)
        self.assertEqual(response["Location"], "http://testserver/deleted/?c=%d" % pk)
        c = Comment.objects.get(pk=pk)
        self.assertTrue(c.is_removed)
        self.assertEqual(c.flags.filter(flag=CommentFlag.MODERATOR_DELETION, user__username="normaluser").count(), 1)

    def testDeletePostNext(self):
        """
        POSTing the delete view will redirect to an explicitly provided a next
        url.
        """
        comments = self.createSomeComments()
        pk = comments[0].pk
        makeModerator("normaluser")
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/delete/%d/" % pk, {'next': "/go/here/"})
        self.assertEqual(response["Location"],
            "http://testserver/go/here/?c=%d" % pk)

    def testDeletePostUnsafeNext(self):
        """
        POSTing to the delete view with an unsafe next url will ignore the
        provided url when redirecting.
        """
        comments = self.createSomeComments()
        pk = comments[0].pk
        makeModerator("normaluser")
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/delete/%d/" % pk,
            {'next': "http://elsewhere/bad"})
        self.assertEqual(response["Location"],
            "http://testserver/deleted/?c=%d" % pk)

    def testDeleteSignals(self):
        def receive(sender, **kwargs):
            received_signals.append(kwargs.get('signal'))

        # Connect signals and keep track of handled ones
        received_signals = []
        signals.comment_was_flagged.connect(receive)

        # Post a comment and check the signals
        self.testDeletePost()
        self.assertEqual(received_signals, [signals.comment_was_flagged])

        signals.comment_was_flagged.disconnect(receive)

    def testDeletedView(self):
        comments = self.createSomeComments()
        pk = comments[0].pk
        response = self.client.get("/deleted/", data={"c": pk})
        self.assertTemplateUsed(response, "comments/deleted.html")

class ApproveViewTests(CommentTestCase):

    def testApprovePermissions(self):
        """The approve view should only be accessible to 'moderators'"""
        comments = self.createSomeComments()
        pk = comments[0].pk
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.get("/approve/%d/" % pk)
        self.assertEqual(response["Location"], "http://testserver/accounts/login/?next=/approve/%d/" % pk)

        makeModerator("normaluser")
        response = self.client.get("/approve/%d/" % pk)
        self.assertEqual(response.status_code, 200)

    def testApprovePost(self):
        """POSTing the approve view should mark the comment as removed"""
        c1, c2, c3, c4 = self.createSomeComments()
        c1.is_public = False; c1.save()

        makeModerator("normaluser")
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/approve/%d/" % c1.pk)
        self.assertEqual(response["Location"], "http://testserver/approved/?c=%d" % c1.pk)
        c = Comment.objects.get(pk=c1.pk)
        self.assertTrue(c.is_public)
        self.assertEqual(c.flags.filter(flag=CommentFlag.MODERATOR_APPROVAL, user__username="normaluser").count(), 1)

    def testApprovePostNext(self):
        """
        POSTing the approve view will redirect to an explicitly provided a next
        url.
        """
        c1, c2, c3, c4 = self.createSomeComments()
        c1.is_public = False; c1.save()

        makeModerator("normaluser")
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/approve/%d/" % c1.pk,
            {'next': "/go/here/"})
        self.assertEqual(response["Location"],
            "http://testserver/go/here/?c=%d" % c1.pk)

    def testApprovePostUnsafeNext(self):
        """
        POSTing to the approve view with an unsafe next url will ignore the
        provided url when redirecting.
        """
        c1, c2, c3, c4 = self.createSomeComments()
        c1.is_public = False; c1.save()

        makeModerator("normaluser")
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/approve/%d/" % c1.pk,
            {'next': "http://elsewhere/bad"})
        self.assertEqual(response["Location"],
            "http://testserver/approved/?c=%d" % c1.pk)

    def testApproveSignals(self):
        def receive(sender, **kwargs):
            received_signals.append(kwargs.get('signal'))

        # Connect signals and keep track of handled ones
        received_signals = []
        signals.comment_was_flagged.connect(receive)

        # Post a comment and check the signals
        self.testApprovePost()
        self.assertEqual(received_signals, [signals.comment_was_flagged])

        signals.comment_was_flagged.disconnect(receive)

    def testApprovedView(self):
        comments = self.createSomeComments()
        pk = comments[0].pk
        response = self.client.get("/approved/", data={"c":pk})
        self.assertTemplateUsed(response, "comments/approved.html")

class AdminActionsTests(CommentTestCase):
    urls = "testapp.urls_admin"

    def setUp(self):
        super(AdminActionsTests, self).setUp()

        # Make "normaluser" a moderator
        u = User.objects.get(username="normaluser")
        u.is_staff = True
        perms = Permission.objects.filter(
            content_type__app_label = 'django_comments',
            codename__endswith = 'comment'
        )
        for perm in perms:
            u.user_permissions.add(perm)
        u.save()

    def testActionsNonModerator(self):
        comments = self.createSomeComments()
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.get("/admin/django_comments/comment/")
        self.assertNotContains(response, "approve_comments")

    def testActionsModerator(self):
        comments = self.createSomeComments()
        makeModerator("normaluser")
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.get("/admin/django_comments/comment/")
        self.assertContains(response, "approve_comments")

    def testActionsDisabledDelete(self):
        "Tests a CommentAdmin where 'delete_selected' has been disabled."
        comments = self.createSomeComments()
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.get('/admin2/django_comments/comment/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<option value="delete_selected">')

    def performActionAndCheckMessage(self, action, action_params, expected_message):
        response = self.client.post('/admin/django_comments/comment/',
                                    data={'_selected_action': action_params,
                                          'action': action,
                                          'index': 0},
                                    follow=True)
        messages = list(m.message for m in response.context['messages'])
        self.assertTrue(expected_message in messages,
                     ("Expected message '%s' wasn't set (messages were: %s)" %
                        (expected_message, messages)))

    def testActionsMessageTranslations(self):
        c1, c2, c3, c4 = self.createSomeComments()
        one_comment = c1.pk
        many_comments = [c2.pk, c3.pk, c4.pk]
        makeModerator("normaluser")
        self.client.login(username="normaluser", password="normaluser")
        with translation.override('en'):
            #Test approving
            self.performActionAndCheckMessage('approve_comments', one_comment, '1 comment was successfully approved.')
            self.performActionAndCheckMessage('approve_comments', many_comments, '3 comments were successfully approved.')
            #Test flagging
            self.performActionAndCheckMessage('flag_comments', one_comment, '1 comment was successfully flagged.')
            self.performActionAndCheckMessage('flag_comments', many_comments, '3 comments were successfully flagged.')
            #Test removing
            self.performActionAndCheckMessage('remove_comments', one_comment, '1 comment was successfully removed.')
            self.performActionAndCheckMessage('remove_comments', many_comments, '3 comments were successfully removed.')

########NEW FILE########
__FILENAME__ = templatetag_tests
from __future__ import absolute_import

from django.contrib.contenttypes.models import ContentType
from django.template import Template, Context, Library, libraries

from django_comments.forms import CommentForm
from django_comments.models import Comment

from ..models import Article, Author
from . import CommentTestCase

register = Library()

@register.filter
def noop(variable, param=None):
    return variable

libraries['comment_testtags'] = register


class CommentTemplateTagTests(CommentTestCase):

    def render(self, t, **c):
        ctx = Context(c)
        out = Template(t).render(ctx)
        return ctx, out

    def testCommentFormTarget(self):
        ctx, out = self.render("{% load comments %}{% comment_form_target %}")
        self.assertEqual(out, "/post/")

    def testGetCommentForm(self, tag=None):
        t = "{% load comments %}" + (tag or "{% get_comment_form for testapp.article a.id as form %}")
        ctx, out = self.render(t, a=Article.objects.get(pk=1))
        self.assertEqual(out, "")
        self.assertTrue(isinstance(ctx["form"], CommentForm))

    def testGetCommentFormFromLiteral(self):
        self.testGetCommentForm("{% get_comment_form for testapp.article 1 as form %}")

    def testGetCommentFormFromObject(self):
        self.testGetCommentForm("{% get_comment_form for a as form %}")

    def testWhitespaceInGetCommentFormTag(self):
        self.testGetCommentForm("{% load comment_testtags %}{% get_comment_form for a|noop:'x y' as form %}")

    def testRenderCommentForm(self, tag=None):
        t = "{% load comments %}" + (tag or "{% render_comment_form for testapp.article a.id %}")
        ctx, out = self.render(t, a=Article.objects.get(pk=1))
        self.assertTrue(out.strip().startswith("<form action="))
        self.assertTrue(out.strip().endswith("</form>"))

    def testRenderCommentFormFromLiteral(self):
        self.testRenderCommentForm("{% render_comment_form for testapp.article 1 %}")

    def testRenderCommentFormFromObject(self):
        self.testRenderCommentForm("{% render_comment_form for a %}")

    def testWhitespaceInRenderCommentFormTag(self):
        self.testRenderCommentForm("{% load comment_testtags %}{% render_comment_form for a|noop:'x y' %}")

    def testRenderCommentFormFromObjectWithQueryCount(self):
        with self.assertNumQueries(1):
            self.testRenderCommentFormFromObject()

    def verifyGetCommentCount(self, tag=None):
        t = "{% load comments %}" + (tag or "{% get_comment_count for testapp.article a.id as cc %}") + "{{ cc }}"
        ctx, out = self.render(t, a=Article.objects.get(pk=1))
        self.assertEqual(out, "2")

    def testGetCommentCount(self):
        self.createSomeComments()
        self.verifyGetCommentCount("{% get_comment_count for testapp.article a.id as cc %}")

    def testGetCommentCountFromLiteral(self):
        self.createSomeComments()
        self.verifyGetCommentCount("{% get_comment_count for testapp.article 1 as cc %}")

    def testGetCommentCountFromObject(self):
        self.createSomeComments()
        self.verifyGetCommentCount("{% get_comment_count for a as cc %}")

    def testWhitespaceInGetCommentCountTag(self):
        self.createSomeComments()
        self.verifyGetCommentCount("{% load comment_testtags %}{% get_comment_count for a|noop:'x y' as cc %}")

    def verifyGetCommentList(self, tag=None):
        c1, c2, c3, c4 = Comment.objects.all()[:4]
        t = "{% load comments %}" +  (tag or "{% get_comment_list for testapp.author a.id as cl %}")
        ctx, out = self.render(t, a=Author.objects.get(pk=1))
        self.assertEqual(out, "")
        self.assertEqual(list(ctx["cl"]), [c2])

    def testGetCommentList(self):
        self.createSomeComments()
        self.verifyGetCommentList("{% get_comment_list for testapp.author a.id as cl %}")

    def testGetCommentListFromLiteral(self):
        self.createSomeComments()
        self.verifyGetCommentList("{% get_comment_list for testapp.author 1 as cl %}")

    def testGetCommentListFromObject(self):
        self.createSomeComments()
        self.verifyGetCommentList("{% get_comment_list for a as cl %}")

    def testWhitespaceInGetCommentListTag(self):
        self.createSomeComments()
        self.verifyGetCommentList("{% load comment_testtags %}{% get_comment_list for a|noop:'x y' as cl %}")

    def testGetCommentPermalink(self):
        c1, c2, c3, c4 = self.createSomeComments()
        t = "{% load comments %}{% get_comment_list for testapp.author author.id as cl %}"
        t += "{% get_comment_permalink cl.0 %}"
        ct = ContentType.objects.get_for_model(Author)
        author = Author.objects.get(pk=1)
        ctx, out = self.render(t, author=author)
        self.assertEqual(out, "/cr/%s/%s/#c%s" % (ct.id, author.id, c2.id))

    def testGetCommentPermalinkFormatted(self):
        c1, c2, c3, c4 = self.createSomeComments()
        t = "{% load comments %}{% get_comment_list for testapp.author author.id as cl %}"
        t += "{% get_comment_permalink cl.0 '#c%(id)s-by-%(user_name)s' %}"
        ct = ContentType.objects.get_for_model(Author)
        author = Author.objects.get(pk=1)
        ctx, out = self.render(t, author=author)
        self.assertEqual(out, "/cr/%s/%s/#c%s-by-Joe Somebody" % (ct.id, author.id, c2.id))

    def testWhitespaceInGetCommentPermalinkTag(self):
        c1, c2, c3, c4 = self.createSomeComments()
        t = "{% load comments comment_testtags %}{% get_comment_list for testapp.author author.id as cl %}"
        t += "{% get_comment_permalink cl.0|noop:'x y' %}"
        ct = ContentType.objects.get_for_model(Author)
        author = Author.objects.get(pk=1)
        ctx, out = self.render(t, author=author)
        self.assertEqual(out, "/cr/%s/%s/#c%s" % (ct.id, author.id, c2.id))

    def testRenderCommentList(self, tag=None):
        t = "{% load comments %}" + (tag or "{% render_comment_list for testapp.article a.id %}")
        ctx, out = self.render(t, a=Article.objects.get(pk=1))
        self.assertTrue(out.strip().startswith("<dl id=\"comments\">"))
        self.assertTrue(out.strip().endswith("</dl>"))

    def testRenderCommentListFromLiteral(self):
        self.testRenderCommentList("{% render_comment_list for testapp.article 1 %}")

    def testRenderCommentListFromObject(self):
        self.testRenderCommentList("{% render_comment_list for a %}")

    def testWhitespaceInRenderCommentListTag(self):
        self.testRenderCommentList("{% load comment_testtags %}{% render_comment_list for a|noop:'x y' %}")

    def testNumberQueries(self):
        """
        Ensure that the template tags use cached content types to reduce the
        number of DB queries.
        Refs #16042.
        """

        self.createSomeComments()

        # {% render_comment_list %} -----------------

        # Clear CT cache
        ContentType.objects.clear_cache()
        with self.assertNumQueries(4):
            self.testRenderCommentListFromObject()

        # CT's should be cached
        with self.assertNumQueries(3):
            self.testRenderCommentListFromObject()

        # {% get_comment_list %} --------------------

        ContentType.objects.clear_cache()
        with self.assertNumQueries(4):
            self.verifyGetCommentList()

        with self.assertNumQueries(3):
            self.verifyGetCommentList()

        # {% render_comment_form %} -----------------

        ContentType.objects.clear_cache()
        with self.assertNumQueries(3):
            self.testRenderCommentForm()

        with self.assertNumQueries(2):
            self.testRenderCommentForm()

        # {% get_comment_form %} --------------------

        ContentType.objects.clear_cache()
        with self.assertNumQueries(3):
            self.testGetCommentForm()

        with self.assertNumQueries(2):
            self.testGetCommentForm()

        # {% get_comment_count %} -------------------

        ContentType.objects.clear_cache()
        with self.assertNumQueries(3):
            self.verifyGetCommentCount()

        with self.assertNumQueries(2):
            self.verifyGetCommentCount()

########NEW FILE########
__FILENAME__ = urls
from __future__ import absolute_import

from django.conf.urls import patterns, url

from django_comments.feeds import LatestCommentFeed

from custom_comments import views


feeds = {
     'comments': LatestCommentFeed,
}

urlpatterns = patterns('',
    url(r'^post/$', views.custom_submit_comment),
    url(r'^flag/(\d+)/$', views.custom_flag_comment),
    url(r'^delete/(\d+)/$', views.custom_delete_comment),
    url(r'^approve/(\d+)/$', views.custom_approve_comment),
    url(r'^cr/(\d+)/(.+)/$', 'django.contrib.contenttypes.views.shortcut', name='comments-url-redirect'),
)

urlpatterns += patterns('',
    (r'^rss/comments/$', LatestCommentFeed()),
)

########NEW FILE########
__FILENAME__ = urls_admin
from django.conf.urls import patterns, include
from django.contrib import admin
from django_comments.admin import CommentsAdmin
from django_comments.models import Comment

# Make a new AdminSite to avoid picking up the deliberately broken admin
# modules in other tests.
admin_site = admin.AdminSite()
admin_site.register(Comment, CommentsAdmin)

# To demonstrate proper functionality even when ``delete_selected`` is removed.
admin_site2 = admin.AdminSite()
admin_site2.disable_action('delete_selected')
admin_site2.register(Comment, CommentsAdmin)

urlpatterns = patterns('',
    (r'^admin/', include(admin_site.urls)),
    (r'^admin2/', include(admin_site2.urls)),
)

########NEW FILE########
__FILENAME__ = urls_default
from django.conf.urls import patterns, include

urlpatterns = patterns('',
    (r'^', include('django_comments.urls')),

    # Provide the auth system login and logout views
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout'),
)

########NEW FILE########
