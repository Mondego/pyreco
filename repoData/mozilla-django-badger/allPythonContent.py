__FILENAME__ = admin
from urlparse import urljoin

from django.conf import settings
from django.contrib import admin

from django import forms
from django.db import models

try:
    from funfactory.urlresolvers import reverse
except ImportError:
    from django.core.urlresolvers import reverse

from .models import (Badge, Award, Nomination, Progress, DeferredAward)


UPLOADS_URL = getattr(settings, 'BADGER_MEDIA_URL',
    urljoin(getattr(settings, 'MEDIA_URL', '/media/'), 'uploads/'))


def show_unicode(obj):
    return unicode(obj)
show_unicode.short_description = "Display"


def show_image(obj):
    if not obj.image:
        return 'None'
    img_url = "%s%s" % (UPLOADS_URL, obj.image)
    return ('<a href="%s" target="_new"><img src="%s" width="48" height="48" /></a>' % 
        (img_url, img_url))

show_image.allow_tags = True
show_image.short_description = "Image"


def build_related_link(self, model_name, name_single, name_plural, qs):
    link = '%s?%s' % (
        reverse('admin:badger_%s_changelist' % model_name, args=[]),
        'badge__exact=%s' % (self.id)
    )
    new_link = '%s?%s' % (
        reverse('admin:badger_%s_add' % model_name, args=[]),
        'badge=%s' % (self.id)
    )
    count = qs.count()
    what = (count == 1) and name_single or name_plural
    return ('<a href="%s">%s %s</a> (<a href="%s">new</a>)' %
            (link, count, what, new_link))


def related_deferredawards_link(self):
    return build_related_link(self, 'deferredaward', 'deferred', 'deferred',
                              self.deferredaward_set)

related_deferredawards_link.allow_tags = True
related_deferredawards_link.short_description = "Deferred Awards"


def related_awards_link(self):
    return build_related_link(self, 'award', 'award', 'awards',
                              self.award_set)

related_awards_link.allow_tags = True
related_awards_link.short_description = "Awards"


class BadgeAdmin(admin.ModelAdmin):
    list_display = ("id", "title", show_image, "slug", "unique", "creator",
                    related_awards_link, related_deferredawards_link, "created",)
    list_display_links = ('id', 'title',)
    search_fields = ("title", "slug", "image", "description",)
    filter_horizontal = ('prerequisites', )
    prepopulated_fields = {"slug": ("title",)}
    formfield_overrides = {
        models.ManyToManyField: {
            "widget": forms.widgets.SelectMultiple(attrs={"size": 25})
        }
    }
    # This prevents Badge from loading all the users on the site
    # which could be a very large number, take forever and result
    # in a huge page.
    raw_id_fields = ("creator",)


def badge_link(self):
    url = reverse('admin:badger_badge_change', args=[self.badge.id])
    return '<a href="%s">%s</a>' % (url, self.badge)

badge_link.allow_tags = True
badge_link.short_description = 'Badge'


class AwardAdmin(admin.ModelAdmin):
    list_display = (show_unicode, badge_link, show_image, 'claim_code', 'user',
                    'creator', 'created', )
    fields = ('badge', 'description', 'claim_code', 'user', 'creator', )
    search_fields = ("badge__title", "badge__slug", "badge__description",
                     "description")
    raw_id_fields = ('user', 'creator',)


class ProgressAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)


def claim_code_link(self):
    return '<a href="%s">%s</a>' % (self.get_claim_url(), self.claim_code)

claim_code_link.allow_tags = True
claim_code_link.short_description = "Claim Code"


class DeferredAwardAdmin(admin.ModelAdmin):
    list_display = ('id', claim_code_link, 'claim_group', badge_link, 'email',
                    'reusable', 'creator', 'created', 'modified',)
    list_display_links = ('id',)
    list_filter = ('reusable', )    
    fields = ('badge', 'claim_group', 'claim_code', 'email', 'reusable',
              'description',)
    readonly_fields = ('created', 'modified')
    search_fields = ("badge__title", "badge__slug", "badge__description",)
    raw_id_fields = ('creator',)


def award_link(self):
    url = reverse('admin:badger_award_change', args=[self.award.id])
    return '<a href="%s">%s</a>' % (url, self.award)

award_link.allow_tags = True
award_link.short_description = 'award'


class NominationAdmin(admin.ModelAdmin):
    list_display = ('id', show_unicode, award_link, 'accepted', 'nominee',
                    'approver', 'creator', 'created', 'modified',)
    list_filter = ('accepted',)
    search_fields = ('badge__title', 'badge__slug', 'badge__description',)
    raw_id_fields = ('nominee', 'creator', 'approver', 'rejected_by',)


for x in ((Badge, BadgeAdmin),
          (Award, AwardAdmin),
          (Nomination, NominationAdmin),
          (Progress, ProgressAdmin),
          (DeferredAward, DeferredAwardAdmin),):
    admin.site.register(*x)

########NEW FILE########
__FILENAME__ = feeds
"""Feeds for badge"""
import datetime
import hashlib
import urllib

from django.contrib.syndication.views import Feed, FeedDoesNotExist
from django.utils.feedgenerator import (SyndicationFeed, Rss201rev2Feed,
                                        Atom1Feed, get_tag_uri)
import django.utils.simplejson as json
from django.shortcuts import get_object_or_404

from django.contrib.auth.models import User
from django.conf import settings

try:
    from tower import ugettext_lazy as _
except ImportError:
    from django.utils.translation import ugettext_lazy as _

try:
    from commons.urlresolvers import reverse
except ImportError:
    from django.core.urlresolvers import reverse

from . import validate_jsonp
from .models import (Badge, Award, Nomination, Progress,
                     BadgeAwardNotAllowedException,
                     DEFAULT_BADGE_IMAGE)


MAX_FEED_ITEMS = getattr(settings, 'BADGER_MAX_FEED_ITEMS', 15)


class BaseJSONFeedGenerator(SyndicationFeed):
    """JSON feed generator"""
    # TODO:liberate - Can this class be a generally-useful lib?

    mime_type = 'application/json'

    def _encode_complex(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()

    def build_item(self, item):
        """Simple base item formatter.
        Omit some named keys and any keys with false-y values"""
        omit_keys = ('obj', 'unique_id', )
        return dict((k, v) for k, v in item.items()
                    if v and k not in omit_keys)

    def build_feed(self):
        """Simple base feed formatter.
        Omit some named keys and any keys with false-y values"""
        omit_keys = ('obj', 'request', 'id', )
        feed_data = dict((k, v) for k, v in self.feed.items()
                         if v and k not in omit_keys)
        feed_data['items'] = [self.build_item(item) for item in self.items]
        return feed_data

    def write(self, outfile, encoding):
        request = self.feed['request']

        # Check for a callback param, validate it before use
        callback = request.GET.get('callback', None)
        if callback is not None:
            if not validate_jsonp.is_valid_jsonp_callback_value(callback):
                callback = None

        # Build the JSON string, wrapping it in a callback param if necessary.
        json_string = json.dumps(self.build_feed(),
                                 default=self._encode_complex)
        if callback:
            outfile.write('%s(%s)' % (callback, json_string))
        else:
            outfile.write(json_string)


class BaseFeed(Feed):
    """Base feed for all of badger, allows switchable generator from URL route
    and other niceties"""
    # TODO:liberate - Can this class be a generally-useful lib?

    json_feed_generator = BaseJSONFeedGenerator
    rss_feed_generator = Rss201rev2Feed
    atom_feed_generator = Atom1Feed

    def __call__(self, request, *args, **kwargs):
        self.request = request
        return super(BaseFeed, self).__call__(request, *args, **kwargs)

    def get_object(self, request, format):
        self.link = request.build_absolute_uri('/')
        if format == 'json':
            self.feed_type = self.json_feed_generator
        elif format == 'rss':
            self.feed_type = self.rss_feed_generator
        else:
            self.feed_type = self.atom_feed_generator
        return super(BaseFeed, self).get_object(request)

    def feed_extra_kwargs(self, obj):
        return {'request': self.request, 'obj': obj, }

    def item_extra_kwargs(self, obj):
        return {'obj': obj, }

    def item_pubdate(self, obj):
        return obj.created

    def item_author_link(self, obj):
        if not obj.creator or not hasattr(obj.creator, 'get_absolute_url'):
            return None
        else:
            return self.request.build_absolute_uri(
                obj.creator.get_absolute_url())

    def item_author_name(self, obj):
        if not obj.creator:
            return None
        else:
            return '%s' % obj.creator

    def item_description(self, obj):
        if obj.image:
            image_url = obj.image.url
        else:
            image_url = '%simg/default-badge.png' % settings.MEDIA_URL
        return """
            <div>
                <a href="%(href)s"><img alt="%(alt)s" src="%(image_url)s" /></a>
            </div>
        """ % dict(
            alt=unicode(obj),
            href=self.request.build_absolute_uri(obj.get_absolute_url()),
            image_url=self.request.build_absolute_uri(image_url)
        )


class AwardActivityStreamJSONFeedGenerator(BaseJSONFeedGenerator):
    pass


class AwardActivityStreamAtomFeedGenerator(Atom1Feed):
    pass


class AwardsFeed(BaseFeed):
    """Base class for all feeds listing awards"""
    title = _(u'Recently awarded badges')
    subtitle = None

    json_feed_generator = AwardActivityStreamJSONFeedGenerator
    atom_feed_generator = AwardActivityStreamAtomFeedGenerator

    def item_title(self, obj):
        return _(u'{badgetitle} awarded to {username}').format(
            badgetitle=obj.badge.title, username=obj.user.username)

    def item_author_link(self, obj):
        if not obj.creator:
            return None
        else:
            return self.request.build_absolute_uri(
                reverse('badger.views.awards_by_user',
                        args=(obj.creator.username,)))

    def item_link(self, obj):
        return self.request.build_absolute_uri(
            reverse('badger.views.award_detail',
                    args=(obj.badge.slug, obj.pk, )))


class AwardsRecentFeed(AwardsFeed):
    """Feed of all recent badge awards"""

    def items(self):
        return (Award.objects
                .order_by('-created')
                .all()[:MAX_FEED_ITEMS])


class AwardsByUserFeed(AwardsFeed):
    """Feed of recent badge awards for a user"""

    def get_object(self, request, format, username):
        super(AwardsByUserFeed, self).get_object(request, format)
        user = get_object_or_404(User, username=username)
        self.title = _(u'Badges recently awarded to {username}').format(
            username=user.username)
        self.link = request.build_absolute_uri(
            reverse('badger.views.awards_by_user', args=(user.username,)))
        return user

    def items(self, user):
        return (Award.objects
                .filter(user=user)
                .order_by('-created')
                .all()[:MAX_FEED_ITEMS])


class AwardsByBadgeFeed(AwardsFeed):
    """Feed of recent badge awards for a badge"""

    def get_object(self, request, format, slug):
        super(AwardsByBadgeFeed, self).get_object(request, format)
        badge = get_object_or_404(Badge, slug=slug)
        self.title = _(u'Recent awards of "{badgetitle}"').format(
            badgetitle=badge.title)
        self.link = request.build_absolute_uri(
            reverse('badger.views.awards_by_badge', args=(badge.slug,)))
        return badge

    def items(self, badge):
        return (Award.objects
                .filter(badge=badge).order_by('-created')
                .all()[:MAX_FEED_ITEMS])


class BadgesJSONFeedGenerator(BaseJSONFeedGenerator):
    pass


class BadgesFeed(BaseFeed):
    """Base class for all feeds listing badges"""
    title = _(u'Recently created badges')

    json_feed_generator = BadgesJSONFeedGenerator

    def item_title(self, obj):
        return obj.title

    def item_link(self, obj):
        return self.request.build_absolute_uri(
            reverse('badger.views.detail',
                    args=(obj.slug, )))


class BadgesRecentFeed(BadgesFeed):

    def items(self):
        return (Badge.objects
                .order_by('-created')
                .all()[:MAX_FEED_ITEMS])


class BadgesByUserFeed(BadgesFeed):
    """Feed of badges recently created by a user"""

    def get_object(self, request, format, username):
        super(BadgesByUserFeed, self).get_object(request, format)
        user = get_object_or_404(User, username=username)
        self.title = _(u'Badges recently created by {username}').format(
            username=user.username)
        self.link = request.build_absolute_uri(
            reverse('badger.views.badges_by_user', args=(user.username,)))
        return user

    def items(self, user):
        return (Badge.objects
                .filter(creator=user)
                .order_by('-created')
                .all()[:MAX_FEED_ITEMS])

########NEW FILE########
__FILENAME__ = forms
import logging
import re

from django.conf import settings

from django import forms
from django.db import models
from django.contrib.auth.models import User, AnonymousUser
from django.forms import FileField, CharField, Textarea, ValidationError
from django.core.validators import validate_email

try:
    from tower import ugettext_lazy as _
except ImportError:
    from django.utils.translation import ugettext_lazy as _

from badger.models import Award, Badge, Nomination

try:
    from taggit.managers import TaggableManager
except ImportError:
    TaggableManager = None


EMAIL_SEPARATOR_RE = re.compile(r'[,;\s]+')


class MyModelForm(forms.ModelForm):

    required_css_class = "required"
    error_css_class = "error"

    def as_ul(self):
        """Returns this form rendered as HTML <li>s -- excluding the <ul></ul>.
        """
        # TODO: l10n: This doesn't work for rtl languages
        return self._html_output(
            normal_row=(u'<li%(html_class_attr)s>%(label)s %(field)s'
                        '%(help_text)s%(errors)s</li>'),
            error_row=u'<li>%s</li>',
            row_ender='</li>',
            help_text_html=u' <p class="help">%s</p>',
            errors_on_separate_row=False)


class MyForm(forms.Form):

    required_css_class = "required"
    error_css_class = "error"

    def as_ul(self):
        """Returns this form rendered as HTML <li>s -- excluding the <ul></ul>.
        """
        # TODO: l10n: This doesn't work for rtl languages
        return self._html_output(
            normal_row=(u'<li%(html_class_attr)s>%(label)s %(field)s'
                        '%(help_text)s%(errors)s</li>'),
            error_row=u'<li>%s</li>',
            row_ender='</li>',
            help_text_html=u' <p class="help">%s</p>',
            errors_on_separate_row=False)


class MultipleItemsField(forms.Field):
    """Form field which accepts multiple text items"""
    # Based on https://docs.djangoproject.com/en/dev/ref/forms/validation/
    #          #form-field-default-cleaning
    widget = Textarea

    def __init__(self, **kwargs):
        self.max_items = kwargs.get('max_items', 10)
        if 'max_items' in kwargs:
            del kwargs['max_items']
        self.separator_re = re.compile(r'[,;\s]+')
        if 'separator_re' in kwargs:
            del kwargs['separator_re']
        super(MultipleItemsField, self).__init__(**kwargs)

    def to_python(self, value):
        """Normalize data to a list of strings."""
        if not value:
            return []
        items = self.separator_re.split(value)
        return [i.strip() for i in items if i.strip()]

    def validate_item(self, item):
        return True

    def validate(self, value):
        """Check if value consists only of valid items."""
        super(MultipleItemsField, self).validate(value)

        # Enforce max number of items
        if len(value) > self.max_items:
            raise ValidationError(
                _(u'{num} items entered, only {maxnum} allowed').format(
                    num=len(value), maxnum=self.max_items))

        # Validate each of the items
        invalid_items = []
        for item in value:
            try:
                self.validate_item(item)
            except ValidationError:
                invalid_items.append(item)

        if len(invalid_items) > 0:
            # TODO: l10n: Not all languages separate with commas
            raise ValidationError(
                _(u'These items were invalid: {itemlist}').format(
                    itemlist=u', '.join(invalid_items)))


class MultiEmailField(MultipleItemsField):
    """Form field which accepts multiple email addresses"""
    def validate_item(self, item):
        validate_email(item)


class BadgeAwardForm(MyForm):
    """Form to create either a real or deferred badge award"""
    # TODO: Needs a captcha?
    emails = MultiEmailField(max_items=10,
            help_text=_(u'Enter up to 10 email addresses for badge award '
                            'recipients'))
    description = CharField(
            label='Explanation',
            widget=Textarea, required=False,
            help_text=_(u'Explain why this badge should be awarded'))


class DeferredAwardGrantForm(MyForm):
    """Form to grant a deferred badge award"""
    # TODO: Needs a captcha?
    email = forms.EmailField()


class MultipleClaimCodesField(MultipleItemsField):
    """Form field which accepts multiple DeferredAward claim codes"""
    def validate_item(self, item):
        from badger.models import DeferredAward
        try:
            DeferredAward.objects.get(claim_code=item)
            return True
        except DeferredAward.DoesNotExist:
            raise ValidationError(_(u'No such claim code, {claimcode}').format(
                claimcode=item))


class DeferredAwardMultipleGrantForm(MyForm):
    email = forms.EmailField(
            help_text=_(u'Email address to which claims should be granted'))
    claim_codes = MultipleClaimCodesField(
            help_text=_(u'Comma- or space-separated list of badge claim codes'))


class BadgeEditForm(MyModelForm):

    class Meta:
        model = Badge
        fields = ('title', 'image', 'description',)
        try:
            # HACK: Add "tags" as a field only if the taggit app is available.
            import taggit
            fields += ('tags',)
        except ImportError:
            pass
        fields += ('unique', 'nominations_accepted',
                   'nominations_autoapproved',)

    required_css_class = "required"
    error_css_class = "error"

    def __init__(self, *args, **kwargs):
        super(BadgeEditForm, self).__init__(*args, **kwargs)

        # TODO: l10n: Pretty sure this doesn't work for rtl languages.
        # HACK: inject new templates into the image field, monkeypatched
        # without creating a subclass
        self.fields['image'].widget.template_with_clear = u'''
            <p class="clear">%(clear)s
                <label for="%(clear_checkbox_id)s">%(clear_checkbox_label)s</label></p>
        '''
        # TODO: l10n: Pretty sure this doesn't work for rtl languages.
        self.fields['image'].widget.template_with_initial = u'''
            <div class="clearablefileinput">
                <p>%(initial_text)s: %(initial)s</p>
                %(clear_template)s
                <p>%(input_text)s: %(input)s</p>
            </div>
        '''


class BadgeNewForm(BadgeEditForm):

    class Meta(BadgeEditForm.Meta):
        pass

    def __init__(self, *args, **kwargs):
        super(BadgeNewForm, self).__init__(*args, **kwargs)


class BadgeSubmitNominationForm(MyForm):
    """Form to submit badge nominations"""
    emails = MultiEmailField(max_items=10,
            help_text=_(
                u'Enter up to 10 email addresses for badge award nominees'))

########NEW FILE########
__FILENAME__ = helpers
import hashlib
import urllib
import urlparse

from django.conf import settings

from django.contrib.auth.models import SiteProfileNotAvailable
from django.core.exceptions import ObjectDoesNotExist
from django.utils.html import conditional_escape

try:
    from commons.urlresolvers import reverse
except ImportError:
    from django.core.urlresolvers import reverse

import jingo
import jinja2
from jinja2 import evalcontextfilter, Markup, escape
from jingo import register, env

from .models import (Badge, Award, Nomination, Progress,
                     BadgeAwardNotAllowedException)


@register.function
def user_avatar(user, secure=False, size=256, rating='pg', default=''):
    try:
        profile = user.get_profile()
        if profile.avatar:
            return profile.avatar.url
    except AttributeError:
        pass
    except SiteProfileNotAvailable:
        pass
    except ObjectDoesNotExist:
        pass

    base_url = (secure and 'https://secure.gravatar.com' or
        'http://www.gravatar.com')
    m = hashlib.md5(user.email)
    return '%(base_url)s/avatar/%(hash)s?%(params)s' % dict(
        base_url=base_url, hash=m.hexdigest(),
        params=urllib.urlencode(dict(
            s=size, d=default, r=rating
        ))
    )


@register.function
def user_awards(user):
    return Award.objects.filter(user=user)


@register.function
def user_badges(user):
    return Badge.objects.filter(creator=user)


@register.function
def badger_allows_add_by(user):
    return Badge.objects.allows_add_by(user)


@register.function
def qr_code_image(value, alt=None, size=150):
    # TODO: Bake our own QR codes, someday soon!
    url = conditional_escape("http://chart.apis.google.com/chart?%s" % \
            urllib.urlencode({'chs': '%sx%s' % (size, size), 'cht': 'qr', 'chl': value, 'choe': 'UTF-8'}))
    alt = conditional_escape(alt or value)

    return Markup(u"""<img class="qrcode" src="%s" width="%s" height="%s" alt="%s" />""" %
                  (url, size, size, alt))


@register.function
def nominations_pending_approval(user):
    return Nomination.objects.filter(badge__creator=user,
                                     approver__isnull=True)


@register.function
def nominations_pending_acceptance(user):
    return Nomination.objects.filter(nominee=user,
                                     approver__isnull=False,
                                     accepted=False)

########NEW FILE########
__FILENAME__ = rebake_awards
from os.path import dirname, basename

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db.models import get_apps, get_models, signals
from django.utils.importlib import import_module

from badger.models import Badge, Award, Progress
from badger.management import update_badges


class Command(BaseCommand):
    args = ''
    help = 'Rebake award images'

    def handle(self, *args, **options):
        for award in Award.objects.all():
            award.save()

########NEW FILE########
__FILENAME__ = update_badges
from os.path import dirname, basename

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db.models import get_apps, get_models, signals
from django.utils.importlib import import_module

from badger.models import Badge, Award, Progress
from badger.management import update_badges


class Command(BaseCommand):
    args = ''
    help = 'Update badges from apps'

    def handle(self, *args, **options):
        # TODO: overwrite needs to be a command option
        update_badges(overwrite=True)

########NEW FILE########
__FILENAME__ = middleware
import logging
import time
from datetime import datetime
from django.conf import settings

from .models import (Badge, Award)


LAST_CHECK_COOKIE_NAME = getattr(settings,
    'BADGER_LAST_CHECK_COOKIE_NAME', 'badgerLastAwardCheck')


class RecentBadgeAwardsList(object):
    """Very lazy accessor for recent awards."""

    def __init__(self, request):
        self.request = request
        self.was_used = False
        self._queryset = None

        # Try to fetch and parse the timestamp of the last award check, fall
        # back to None
        try:
            self.last_check = datetime.fromtimestamp(float(
                self.request.COOKIES[LAST_CHECK_COOKIE_NAME]))
        except (KeyError, ValueError):
            self.last_check = None

    def process_response(self, response):
        if (self.request.user.is_authenticated() and
                (not self.last_check or self.was_used)):
            response.set_cookie(LAST_CHECK_COOKIE_NAME, time.time())
        return response

    def get_queryset(self, last_check=None):
        if not last_check:
            last_check = self.last_check

        if not (last_check and self.request.user.is_authenticated()):
            # No queryset for anonymous users or missing last check timestamp
            return None

        if not self._queryset:
            self.was_used = True
            self._queryset = (Award.objects
                .filter(user=self.request.user,
                        created__gt=last_check)
                .exclude(hidden=True))

        return self._queryset

    def __iter__(self):
        qs = self.get_queryset()
        if qs is None:
            return []
        return qs.iterator()

    def __len__(self):
        qs = self.get_queryset()
        if qs is None:
            return 0
        return len(qs)


class RecentBadgeAwardsMiddleware(object):
    """Middleware that adds ``recent_badge_awards`` to request

    This property is lazy-loading, so if you don't use it, then it
    shouldn't have much effect on runtime.

    To use, add this to your ``MIDDLEWARE_CLASSES`` in ``settings.py``::

        MIDDLEWARE_CLASSES = (
            ...
            'badger.middleware.RecentBadgeAwardsMiddleware',
            ...
        )


    Then in your view code::

        def awesome_view(request):
            for award in request.recent_badge_awards:
                do_something_awesome(award)

    """

    def process_request(self, request):
        request.recent_badge_awards = RecentBadgeAwardsList(request)
        return None

    def process_response(self, request, response):
        if not hasattr(request, 'recent_badge_awards'):
            return response
        return request.recent_badge_awards.process_response(response)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Badge'
        db.create_table('badger_badge', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50, db_index=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('unique', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('badger', ['Badge'])

        # Adding unique constraint on 'Badge', fields ['title', 'slug']
        db.create_unique('badger_badge', ['title', 'slug'])

        # Adding M2M table for field prerequisites on 'Badge'
        db.create_table('badger_badge_prerequisites', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_badge', models.ForeignKey(orm['badger.badge'], null=False)),
            ('to_badge', models.ForeignKey(orm['badger.badge'], null=False))
        ))
        db.create_unique('badger_badge_prerequisites', ['from_badge_id', 'to_badge_id'])

        # Adding model 'Award'
        db.create_table('badger_award', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('badge', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['badger.Badge'])),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='award_user', to=orm['auth.User'])),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='award_creator', null=True, to=orm['auth.User'])),
            ('hidden', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('badger', ['Award'])

        # Adding model 'Progress'
        db.create_table('badger_progress', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('badge', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['badger.Badge'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='progress_user', to=orm['auth.User'])),
            ('percent', self.gf('django.db.models.fields.FloatField')(default=0)),
            ('counter', self.gf('django.db.models.fields.FloatField')(default=0, null=True, blank=True)),
            ('notes', self.gf('badger.models.JSONField')(null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('badger', ['Progress'])

        # Adding unique constraint on 'Progress', fields ['badge', 'user']
        db.create_unique('badger_progress', ['badge_id', 'user_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Progress', fields ['badge', 'user']
        db.delete_unique('badger_progress', ['badge_id', 'user_id'])

        # Removing unique constraint on 'Badge', fields ['title', 'slug']
        db.delete_unique('badger_badge', ['title', 'slug'])

        # Deleting model 'Badge'
        db.delete_table('badger_badge')

        # Removing M2M table for field prerequisites on 'Badge'
        db.delete_table('badger_badge_prerequisites')

        # Deleting model 'Award'
        db.delete_table('badger_award')

        # Deleting model 'Progress'
        db.delete_table('badger_progress')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'badger.award': {
            'Meta': {'object_name': 'Award'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'award_creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'award_user'", 'to': "orm['auth.User']"})
        },
        'badger.badge': {
            'Meta': {'unique_together': "(('title', 'slug'),)", 'object_name': 'Badge'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'prerequisites': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['badger.Badge']", 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'unique': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'badger.progress': {
            'Meta': {'unique_together': "(('badge', 'user'),)", 'object_name': 'Progress'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'counter': ('django.db.models.fields.FloatField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'notes': ('badger.models.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'percent': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'progress_user'", 'to': "orm['auth.User']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['badger']

########NEW FILE########
__FILENAME__ = 0002_auto__add_deferredaward__add_field_badge_nominations_accepted
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'DeferredAward'
        db.create_table('badger_deferredaward', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('badge', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['badger.Badge'])),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('reusable', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('email', self.gf('django.db.models.fields.EmailField')(db_index=True, max_length=75, null=True, blank=True)),
            ('claim_code', self.gf('django.db.models.fields.CharField')(default='8k0y4w', unique=True, max_length=6, db_index=True)),
            ('claim_group', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=32, null=True, blank=True)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('badger', ['DeferredAward'])

        # Adding field 'Badge.nominations_accepted'
        db.add_column('badger_badge', 'nominations_accepted',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting model 'DeferredAward'
        db.delete_table('badger_deferredaward')

        # Deleting field 'Badge.nominations_accepted'
        db.delete_column('badger_badge', 'nominations_accepted')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'badger.award': {
            'Meta': {'ordering': "['-modified', '-created']", 'object_name': 'Award'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'award_creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'award_user'", 'to': "orm['auth.User']"})
        },
        'badger.badge': {
            'Meta': {'ordering': "['-modified', '-created']", 'unique_together': "(('title', 'slug'),)", 'object_name': 'Badge'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'nominations_accepted': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'prerequisites': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['badger.Badge']", 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'unique': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'badger.deferredaward': {
            'Meta': {'ordering': "['-modified', '-created']", 'object_name': 'DeferredAward'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'claim_code': ('django.db.models.fields.CharField', [], {'default': "'byhidc'", 'unique': 'True', 'max_length': '6', 'db_index': 'True'}),
            'claim_group': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'db_index': 'True', 'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'reusable': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'badger.progress': {
            'Meta': {'unique_together': "(('badge', 'user'),)", 'object_name': 'Progress'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'counter': ('django.db.models.fields.FloatField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'notes': ('badger.models.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'percent': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'progress_user'", 'to': "orm['auth.User']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        }
    }

    complete_apps = ['badger']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_award_claim_code__chg_field_deferredaward_claim_code
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Award.claim_code'
        db.add_column('badger_award', 'claim_code',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=32, db_index=True, blank=True),
                      keep_default=False)


        # Changing field 'DeferredAward.claim_code'
        db.alter_column('badger_deferredaward', 'claim_code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32))
    def backwards(self, orm):
        # Deleting field 'Award.claim_code'
        db.delete_column('badger_award', 'claim_code')


        # Changing field 'DeferredAward.claim_code'
        db.alter_column('badger_deferredaward', 'claim_code', self.gf('django.db.models.fields.CharField')(max_length=6, unique=True))
    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'badger.award': {
            'Meta': {'ordering': "['-modified', '-created']", 'object_name': 'Award'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'claim_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '32', 'db_index': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'award_creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'award_user'", 'to': "orm['auth.User']"})
        },
        'badger.badge': {
            'Meta': {'ordering': "['-modified', '-created']", 'unique_together': "(('title', 'slug'),)", 'object_name': 'Badge'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'nominations_accepted': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'prerequisites': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['badger.Badge']", 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'unique': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'badger.deferredaward': {
            'Meta': {'ordering': "['-modified', '-created']", 'object_name': 'DeferredAward'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'claim_code': ('django.db.models.fields.CharField', [], {'default': "'yuv7xu'", 'unique': 'True', 'max_length': '32', 'db_index': 'True'}),
            'claim_group': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'db_index': 'True', 'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'reusable': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'badger.progress': {
            'Meta': {'unique_together': "(('badge', 'user'),)", 'object_name': 'Progress'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'counter': ('django.db.models.fields.FloatField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'notes': ('badger.models.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'percent': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'progress_user'", 'to': "orm['auth.User']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        }
    }

    complete_apps = ['badger']
########NEW FILE########
__FILENAME__ = 0004_auto__add_nomination
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models, DatabaseError


class Migration(SchemaMigration):
    old_table_name = 'badger_multiplayer_nomination'
    new_table_name = 'badger_nomination'

    def forwards(self, orm):
        """If it exists, rename badger_multiplayer_nomination to
        badger_nomination. Otherwise, create a brand new badger_nomination.

        This is weird, but it's because I merged the multiplayer app into
        badger core."""

        if self._table_exists(self.old_table_name):
            return self._forwards_rename(orm)
        else:
            return self._forwards_create(orm)
        db.send_create_signal('badger', ['Nomination'])

    def _table_exists(self, name):
        """Determine whether the table exists."""
        # HACK: Digging into South's db guts, in order to route around the
        # usual error handling. I feel dirty. There must be a better way.
        cursor = db._get_connection().cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM %s" % name)
            return True
        except DatabaseError:
            return False

    def _forwards_rename(self, orm):
        if self._table_exists(self.new_table_name):
            # This shouldn't happen, but weird things abound.
            db.delete_table(self.new_table_name)
        db.rename_table(self.old_table_name, self.new_table_name)

    def _forwards_create(self, orm):
        if self._table_exists(self.new_table_name):
            # This shouldn't happen, but weird things abound.
            return

        # Adding model 'Nomination'
        db.create_table(self.new_table_name, (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('badge', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['badger.Badge'])),
            ('nominee', self.gf('django.db.models.fields.related.ForeignKey')(related_name='nomination_nominee', to=orm['auth.User'])),
            ('accepted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='nomination_creator', null=True, to=orm['auth.User'])),
            ('approver', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='nomination_approver', null=True, to=orm['auth.User'])),
            ('award', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['badger.Award'], null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))

    def backwards(self, orm):
        # Deleting model 'Nomination'
        db.delete_table(self.new_table_name)

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'badger.award': {
            'Meta': {'ordering': "['-modified', '-created']", 'object_name': 'Award'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'claim_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '32', 'db_index': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'award_creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'award_user'", 'to': "orm['auth.User']"})
        },
        'badger.badge': {
            'Meta': {'ordering': "['-modified', '-created']", 'unique_together': "(('title', 'slug'),)", 'object_name': 'Badge'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'nominations_accepted': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'prerequisites': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['badger.Badge']", 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'unique': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'badger.deferredaward': {
            'Meta': {'ordering': "['-modified', '-created']", 'object_name': 'DeferredAward'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'claim_code': ('django.db.models.fields.CharField', [], {'default': "'frvppj'", 'unique': 'True', 'max_length': '32', 'db_index': 'True'}),
            'claim_group': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'db_index': 'True', 'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'reusable': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'badger.nomination': {
            'Meta': {'object_name': 'Nomination'},
            'accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'approver': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'nomination_approver'", 'null': 'True', 'to': "orm['auth.User']"}),
            'award': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Award']", 'null': 'True', 'blank': 'True'}),
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'nomination_creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'nominee': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nomination_nominee'", 'to': "orm['auth.User']"})
        },
        'badger.progress': {
            'Meta': {'unique_together': "(('badge', 'user'),)", 'object_name': 'Progress'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'counter': ('django.db.models.fields.FloatField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'notes': ('badger.models.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'percent': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'progress_user'", 'to': "orm['auth.User']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        }
    }

    complete_apps = ['badger']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_award_description
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Award.description'
        db.add_column('badger_award', 'description',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Award.description'
        db.delete_column('badger_award', 'description')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'badger.award': {
            'Meta': {'ordering': "['-modified', '-created']", 'object_name': 'Award'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'claim_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '32', 'db_index': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'award_creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'award_user'", 'to': "orm['auth.User']"})
        },
        'badger.badge': {
            'Meta': {'ordering': "['-modified', '-created']", 'unique_together': "(('title', 'slug'),)", 'object_name': 'Badge'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'nominations_accepted': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'prerequisites': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['badger.Badge']", 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'unique': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'badger.deferredaward': {
            'Meta': {'ordering': "['-modified', '-created']", 'object_name': 'DeferredAward'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'claim_code': ('django.db.models.fields.CharField', [], {'default': "'4jca7j'", 'unique': 'True', 'max_length': '32', 'db_index': 'True'}),
            'claim_group': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'db_index': 'True', 'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'reusable': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'badger.nomination': {
            'Meta': {'object_name': 'Nomination'},
            'accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'approver': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'nomination_approver'", 'null': 'True', 'to': "orm['auth.User']"}),
            'award': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Award']", 'null': 'True', 'blank': 'True'}),
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'nomination_creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'nominee': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nomination_nominee'", 'to': "orm['auth.User']"})
        },
        'badger.progress': {
            'Meta': {'unique_together': "(('badge', 'user'),)", 'object_name': 'Progress'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'counter': ('django.db.models.fields.FloatField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'notes': ('badger.models.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'percent': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'progress_user'", 'to': "orm['auth.User']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        }
    }

    complete_apps = ['badger']
########NEW FILE########
__FILENAME__ = 0006_auto__add_field_nomination_rejecter__add_field_nomination_rejection_re
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Nomination.rejected_by'
        db.add_column('badger_nomination', 'rejected_by',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='nomination_rejected_by', null=True, to=orm['auth.User']),
                      keep_default=False)

        # Adding field 'Nomination.rejected_reason'
        db.add_column('badger_nomination', 'rejected_reason',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Nomination.rejected_by'
        db.delete_column('badger_nomination', 'rejected_by_id')

        # Deleting field 'Nomination.rejected_reason'
        db.delete_column('badger_nomination', 'rejected_reason')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'badger.award': {
            'Meta': {'ordering': "['-modified', '-created']", 'object_name': 'Award'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'claim_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '32', 'db_index': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'award_creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'award_user'", 'to': "orm['auth.User']"})
        },
        'badger.badge': {
            'Meta': {'ordering': "['-modified', '-created']", 'unique_together': "(('title', 'slug'),)", 'object_name': 'Badge'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'nominations_accepted': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'prerequisites': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['badger.Badge']", 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'unique': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'badger.deferredaward': {
            'Meta': {'ordering': "['-modified', '-created']", 'object_name': 'DeferredAward'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'claim_code': ('django.db.models.fields.CharField', [], {'default': "'xamuuk'", 'unique': 'True', 'max_length': '32', 'db_index': 'True'}),
            'claim_group': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'db_index': 'True', 'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'reusable': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'badger.nomination': {
            'Meta': {'object_name': 'Nomination'},
            'accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'approver': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'nomination_approver'", 'null': 'True', 'to': "orm['auth.User']"}),
            'award': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Award']", 'null': 'True', 'blank': 'True'}),
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'nomination_creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'nominee': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nomination_nominee'", 'to': "orm['auth.User']"}),
            'rejected_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'nomination_rejected_by'", 'null': 'True', 'to': "orm['auth.User']"}),
            'rejected_reason': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'badger.progress': {
            'Meta': {'unique_together': "(('badge', 'user'),)", 'object_name': 'Progress'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'counter': ('django.db.models.fields.FloatField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'notes': ('badger.models.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'percent': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'progress_user'", 'to': "orm['auth.User']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        }
    }

    complete_apps = ['badger']

########NEW FILE########
__FILENAME__ = 0007_auto__add_field_badge_nominations_autoapproved
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Badge.nominations_autoapproved'
        db.add_column('badger_badge', 'nominations_autoapproved',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Badge.nominations_autoapproved'
        db.delete_column('badger_badge', 'nominations_autoapproved')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'badger.award': {
            'Meta': {'ordering': "['-modified', '-created']", 'object_name': 'Award'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'claim_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '32', 'db_index': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'award_creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'award_user'", 'to': "orm['auth.User']"})
        },
        'badger.badge': {
            'Meta': {'ordering': "['-modified', '-created']", 'unique_together': "(('title', 'slug'),)", 'object_name': 'Badge'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'nominations_accepted': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'nominations_autoapproved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'prerequisites': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['badger.Badge']", 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'unique': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'badger.deferredaward': {
            'Meta': {'ordering': "['-modified', '-created']", 'object_name': 'DeferredAward'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'claim_code': ('django.db.models.fields.CharField', [], {'default': "'m34huu'", 'unique': 'True', 'max_length': '32', 'db_index': 'True'}),
            'claim_group': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'db_index': 'True', 'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'reusable': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'badger.nomination': {
            'Meta': {'object_name': 'Nomination'},
            'accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'approver': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'nomination_approver'", 'null': 'True', 'to': "orm['auth.User']"}),
            'award': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Award']", 'null': 'True', 'blank': 'True'}),
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'nomination_creator'", 'null': 'True', 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'nominee': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nomination_nominee'", 'to': "orm['auth.User']"}),
            'rejected_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'nomination_rejected_by'", 'null': 'True', 'to': "orm['auth.User']"}),
            'rejected_reason': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'badger.progress': {
            'Meta': {'unique_together': "(('badge', 'user'),)", 'object_name': 'Progress'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['badger.Badge']"}),
            'counter': ('django.db.models.fields.FloatField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'notes': ('badger.models.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'percent': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'progress_user'", 'to': "orm['auth.User']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['badger']
########NEW FILE########
__FILENAME__ = models
import logging
import re
import random
import hashlib

from datetime import datetime, timedelta, tzinfo
from time import time, gmtime, strftime

import os.path
from os.path import dirname

from urlparse import urljoin

from django.conf import settings

from django.db import models
from django.db.models import signals, Q, Count, Max
from django.db.models.fields.files import FieldFile, ImageFieldFile
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType

from django.template import Context, TemplateDoesNotExist
from django.template.loader import render_to_string

from django.core.serializers.json import DjangoJSONEncoder

try:
    import django.utils.simplejson as json
except ImportError: # Django 1.5 no longer bundles simplejson
    import json

# HACK: Django 1.2 is missing receiver and user_logged_in
try:
    from django.dispatch import receiver
    from django.contrib.auth.signals import user_logged_in
except ImportError:
    receiver = False
    user_logged_in = False

try:
    from tower import ugettext_lazy as _
except ImportError:
    from django.utils.translation import ugettext_lazy as _

try:
    from funfactory.urlresolvers import reverse
except ImportError:
    from django.core.urlresolvers import reverse

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    from PIL import Image
except ImportError:
    import Image

try:
    import taggit
    from taggit.managers import TaggableManager
    from taggit.models import Tag, TaggedItem
except ImportError:
    taggit = None

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None

import badger
from .signals import (badge_will_be_awarded, badge_was_awarded,
                      nomination_will_be_approved, nomination_was_approved,
                      nomination_will_be_accepted, nomination_was_accepted,
                      nomination_will_be_rejected, nomination_was_rejected,
                      user_will_be_nominated, user_was_nominated)


OBI_VERSION = "0.5.0"

IMG_MAX_SIZE = getattr(settings, "BADGER_IMG_MAX_SIZE", (256, 256))

SITE_ISSUER = getattr(settings, 'BADGER_SITE_ISSUER', {
    "origin": "http://mozilla.org",
    "name": "Badger",
    "org": "Mozilla",
    "contact": "lorchard@mozilla.com"
})

# Set up a file system for badge uploads that can be kept separate from the
# rest of /media if necessary. Lots of hackery to ensure sensible defaults.
UPLOADS_ROOT = getattr(settings, 'BADGER_MEDIA_ROOT',
    os.path.join(getattr(settings, 'MEDIA_ROOT', 'media/'), 'uploads'))
UPLOADS_URL = getattr(settings, 'BADGER_MEDIA_URL',
    urljoin(getattr(settings, 'MEDIA_URL', '/media/'), 'uploads/'))
BADGE_UPLOADS_FS = FileSystemStorage(location=UPLOADS_ROOT,
                                     base_url=UPLOADS_URL)

DEFAULT_BADGE_IMAGE = getattr(settings, 'BADGER_DEFAULT_BADGE_IMAGE',
    "%s/fixtures/default-badge.png" % dirname(__file__))
DEFAULT_BADGE_IMAGE_URL = getattr(settings, 'BADGER_DEFAULT_BADGE_IMAGE_URL',
    urljoin(getattr(settings, 'MEDIA_URL', '/media/'), 'img/default-badge.png'))

TIME_ZONE_OFFSET = getattr(settings, "TIME_ZONE_OFFSET", timedelta(0))

MK_UPLOAD_TMPL = '%(base)s/%(h1)s/%(h2)s/%(hash)s_%(field_fn)s_%(now)s_%(rand)04d.%(ext)s'

DEFAULT_HTTP_PROTOCOL = getattr(settings, "DEFAULT_HTTP_PROTOCOL", "http")

CLAIM_CODE_LENGTH = getattr(settings, "CLAIM_CODE_LENGTH", 6)


def _document_django_model(cls):
    """Adds meta fields to the docstring for better autodoccing"""
    fields = cls._meta.fields
    doc = cls.__doc__

    if not doc.endswith('\n\n'):
        doc = doc + '\n\n'

    for f in fields:
        doc = doc + '    :arg {0}:\n'.format(f.name)

    cls.__doc__ = doc
    return cls


def scale_image(img_upload, img_max_size):
    """Crop and scale an image file."""
    try:
        img = Image.open(img_upload)
    except IOError:
        return None

    src_width, src_height = img.size
    src_ratio = float(src_width) / float(src_height)
    dst_width, dst_height = img_max_size
    dst_ratio = float(dst_width) / float(dst_height)

    if dst_ratio < src_ratio:
        crop_height = src_height
        crop_width = crop_height * dst_ratio
        x_offset = int(float(src_width - crop_width) / 2)
        y_offset = 0
    else:
        crop_width = src_width
        crop_height = crop_width / dst_ratio
        x_offset = 0
        y_offset = int(float(src_height - crop_height) / 2)

    img = img.crop((x_offset, y_offset,
        x_offset + int(crop_width), y_offset + int(crop_height)))
    img = img.resize((dst_width, dst_height), Image.ANTIALIAS)

    # If the mode isn't RGB or RGBA we convert it. If it's not one
    # of those modes, then we don't know what the alpha channel should
    # be so we convert it to "RGB".
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    new_img = StringIO()
    img.save(new_img, "PNG")
    img_data = new_img.getvalue()

    return ContentFile(img_data)


# Taken from http://stackoverflow.com/a/4019144
def slugify(txt):
    """A custom version of slugify that retains non-ascii characters. The
    purpose of this function in the application is to make URLs more readable
    in a browser, so there are some added heuristics to retain as much of the
    title meaning as possible while excluding characters that are troublesome
    to read in URLs. For example, question marks will be seen in the browser
    URL as %3F and are thereful unreadable. Although non-ascii characters will
    also be hex-encoded in the raw URL, most browsers will display them as
    human-readable glyphs in the address bar -- those should be kept in the
    slug."""
    # remove trailing whitespace
    txt = txt.strip()
    # remove spaces before and after dashes
    txt = re.sub('\s*-\s*', '-', txt, re.UNICODE)
    # replace remaining spaces with dashes
    txt = re.sub('[\s/]', '-', txt, re.UNICODE)
    # replace colons between numbers with dashes
    txt = re.sub('(\d):(\d)', r'\1-\2', txt, re.UNICODE)
    # replace double quotes with single quotes
    txt = re.sub('"', "'", txt, re.UNICODE)
    # remove some characters altogether
    txt = re.sub(r'[?,:!@#~`+=$%^&\\*()\[\]{}<>]', '', txt, re.UNICODE)
    return txt


def get_permissions_for(self, user):
    """Mixin method to collect permissions for a model instance"""
    pre = 'allows_'
    pre_len = len(pre)
    methods = (m for m in dir(self) if m.startswith(pre))
    perms = dict(
        (m[pre_len:], getattr(self, m)(user))
        for m in methods
    )
    return perms


def mk_upload_to(field_fn, ext, tmpl=MK_UPLOAD_TMPL):
    """upload_to builder for file upload fields"""
    def upload_to(instance, filename):
        base, slug = instance.get_upload_meta()
        slug_hash = (hashlib.md5(slug.encode('utf-8', 'ignore'))
                            .hexdigest())
        return tmpl % dict(now=int(time()), rand=random.randint(0, 1000),
                           slug=slug[:50], base=base, field_fn=field_fn,
                           pk=instance.pk,
                           hash=slug_hash, h1=slug_hash[0], h2=slug_hash[1],
                           ext=ext)
    return upload_to


class JSONField(models.TextField):
    """JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly
    see: http://djangosnippets.org/snippets/1478/
    """

    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        """Convert our string value to JSON after we load it from the DB"""
        if not value:
            return dict()
        try:
            if (isinstance(value, basestring) or
                    type(value) is unicode):
                return json.loads(value)
        except ValueError:
            return dict()
        return value

    def get_db_prep_save(self, value, connection):
        """Convert our JSON object to a string before we save"""
        if not value:
            return '{}'
        if isinstance(value, dict):
            value = json.dumps(value, cls=DjangoJSONEncoder)
        if isinstance(value, basestring) or value is None:
            return value
        return smart_unicode(value)


# Tell South that this field isn't all that special
try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^badger.models.JSONField"])
except ImportError:
    pass


class SearchManagerMixin(object):
    """Quick & dirty manager mixin for search"""

    # See: http://www.julienphalip.com/blog/2008/08/16/adding-search-django-site-snap/
    def _normalize_query(self, query_string,
                        findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                        normspace=re.compile(r'\s{2,}').sub):
        """
        Splits the query string in invidual keywords, getting rid of unecessary spaces
        and grouping quoted words together.
        Example::

            foo._normalize_query('  some random  words "with   quotes  " and   spaces')
            ['some', 'random', 'words', 'with quotes', 'and', 'spaces']

        """
        return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)]

    # See: http://www.julienphalip.com/blog/2008/08/16/adding-search-django-site-snap/
    def _get_query(self, query_string, search_fields):
        """
        Returns a query, that is a combination of Q objects. That
        combination aims to search keywords within a model by testing
        the given search fields.

        """
        query = None  # Query to search for every search term
        terms = self._normalize_query(query_string)
        for term in terms:
            or_query = None  # Query to search for a given term in each field
            for field_name in search_fields:
                q = Q(**{"%s__icontains" % field_name: term})
                if or_query is None:
                    or_query = q
                else:
                    or_query = or_query | q
            if query is None:
                query = or_query
            else:
                query = query & or_query
        return query

    def search(self, query_string, sort='title'):
        """Quick and dirty keyword search on submissions"""
        # TODO: Someday, replace this with something like Sphinx or another real
        # search engine
        strip_qs = query_string.strip()
        if not strip_qs:
            return self.all_sorted(sort).order_by('-modified')
        else:
            query = self._get_query(strip_qs, self.search_fields)
            return self.all_sorted(sort).filter(query).order_by('-modified')

    def all_sorted(self, sort=None):
        """Apply to .all() one of the sort orders supported for views"""
        queryset = self.all()
        if sort == 'title':
            return queryset.order_by('title')
        else:
            return queryset.order_by('-created')


class BadgerException(Exception):
    """General Badger model exception"""


class BadgeException(BadgerException):
    """Badge model exception"""


class BadgeAwardNotAllowedException(BadgeException):
    """Attempt to award a badge not allowed."""


class BadgeAlreadyAwardedException(BadgeException):
    """Attempt to award a unique badge twice."""


class BadgeDeferredAwardManagementNotAllowedException(BadgeException):
    """Attempt to manage deferred awards not allowed."""


class BadgeManager(models.Manager, SearchManagerMixin):
    """Manager for Badge model objects"""
    search_fields = ('title', 'slug', 'description', )

    def allows_add_by(self, user):
        if user.is_anonymous():
            return False
        if getattr(settings, "BADGER_ALLOW_ADD_BY_ANYONE", False):
            return True
        if user.has_perm('badger.add_badge'):
            return True
        return False

    def allows_grant_by(self, user):
        if user.is_anonymous():
            return False
        if user.has_perm('badger.grant_deferredaward'):
            return True
        return False

    def top_tags(self, min_count=2, limit=20):
        """Assemble list of top-used tags"""
        if not taggit:
            return []

        # TODO: There has got to be a better way to do this. I got lost in
        # Django model bits, though.

        # Gather list of tags sorted by use frequency
        ct = ContentType.objects.get_for_model(Badge)
        tag_counts = (TaggedItem.objects
            .values('tag')
            .annotate(count=Count('id'))
            .filter(content_type=ct, count__gte=min_count)
            .order_by('-count'))[:limit]

        # Gather set of tag IDs from list
        tag_ids = set(x['tag'] for x in tag_counts)

        # Gather and map tag objects to IDs
        tags_by_id = dict((x.pk, x)
            for x in Tag.objects.filter(pk__in=tag_ids))

        # Join tag objects up with counts
        tags_with_counts = [
            dict(count=x['count'], tag=tags_by_id[x['tag']])
            for x in tag_counts]

        return tags_with_counts


@_document_django_model
class Badge(models.Model):
    """Representation of a badge"""
    objects = BadgeManager()

    title = models.CharField(max_length=255, blank=False, unique=True,
        help_text='Short, descriptive title')
    slug = models.SlugField(blank=False, unique=True,
        help_text='Very short name, for use in URLs and links')
    description = models.TextField(blank=True,
        help_text='Longer description of the badge and its criteria')
    image = models.ImageField(blank=True, null=True,
            storage=BADGE_UPLOADS_FS, upload_to=mk_upload_to('image', 'png'),
            help_text='Upload an image to represent the badge')
    prerequisites = models.ManyToManyField('self', symmetrical=False,
            blank=True, null=True,
            help_text=('When all of the selected badges have been awarded, this '
                       'badge will be automatically awarded.'))
    # TODO: Rename? Eventually we'll want a globally-unique badge. That is, one
    # unique award for one person for the whole site.
    unique = models.BooleanField(default=True,
            help_text=('Should awards of this badge be limited to '
                       'one-per-person?'))

    nominations_accepted = models.BooleanField(default=True, blank=True,
            help_text=('Should this badge accept nominations from '
                       'other users?'))

    nominations_autoapproved = models.BooleanField(default=False, blank=True,
            help_text='Should all nominations be automatically approved?')

    if taggit:
        tags = TaggableManager(blank=True)

    creator = models.ForeignKey(User, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, blank=False)
    modified = models.DateTimeField(auto_now=True, blank=False)

    class Meta:
        unique_together = ('title', 'slug')
        ordering = ['-modified', '-created']
        permissions = (
            ('manage_deferredawards',
             _(u'Can manage deferred awards for this badge')),
        )

    get_permissions_for = get_permissions_for

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('badger.views.detail', args=(self.slug,))

    def get_upload_meta(self):
        return ("badge", self.slug)

    def clean(self):
        if self.image:
            scaled_file = scale_image(self.image.file, IMG_MAX_SIZE)
            if not scaled_file:
                raise ValidationError(_(u'Cannot process image'))
            self.image.file = scaled_file

    def save(self, **kwargs):
        """Save the submission, updating slug and screenshot thumbnails"""
        if not self.slug:
            self.slug = slugify(self.title)

        super(Badge, self).save(**kwargs)

        if notification:
            if self.creator:
                notification.send([self.creator], 'badge_edited',
                                  dict(badge=self,
                                       protocol=DEFAULT_HTTP_PROTOCOL))

    def delete(self, **kwargs):
        """Make sure deletes cascade to awards"""
        self.award_set.all().delete()
        super(Badge, self).delete(**kwargs)

    def allows_detail_by(self, user):
        # TODO: Need some logic here, someday.
        return True

    def allows_edit_by(self, user):
        if user.is_anonymous():
            return False
        if user.has_perm('badger.change_badge'):
            return True
        if user == self.creator:
            return True
        return False

    def allows_delete_by(self, user):
        if user.is_anonymous():
            return False
        if user.has_perm('badger.change_badge'):
            return True
        if user == self.creator:
            return True
        return False

    def allows_award_to(self, user):
        """Is award_to() allowed for this user?"""
        if None == user:
            return True
        if user.is_anonymous():
            return False
        if user.is_staff or user.is_superuser:
            return True
        if user == self.creator:
            return True

        # TODO: List of delegates for whom awarding is allowed

        return False

    def allows_manage_deferred_awards_by(self, user):
        """Can this user manage deferred awards"""
        if user.is_anonymous():
            return False
        if user.has_perm('badger.manage_deferredawards'):
            return True
        if user == self.creator:
            return True
        return False

    def generate_deferred_awards(self, user, amount=10, reusable=False):
        """Generate a number of deferred awards with a claim group code"""
        if not self.allows_manage_deferred_awards_by(user):
            raise BadgeDeferredAwardManagementNotAllowedException()
        return (DeferredAward.objects.generate(self, user, amount, reusable))

    def get_claim_group(self, claim_group):
        """Get all the deferred awards for a claim group code"""
        return DeferredAward.objects.filter(claim_group=claim_group)

    def delete_claim_group(self, user, claim_group):
        """Delete all the deferred awards for a claim group code"""
        if not self.allows_manage_deferred_awards_by(user):
            raise BadgeDeferredAwardManagementNotAllowedException()
        self.get_claim_group(claim_group).delete()

    @property
    def claim_groups(self):
        """Produce a list of claim group IDs available"""
        return DeferredAward.objects.get_claim_groups(badge=self)

    def award_to(self, awardee=None, email=None, awarder=None,
                 description='', raise_already_awarded=False):
        """Award this badge to the awardee on the awarder's behalf"""
        # If no awarder given, assume this is on the badge creator's behalf.
        if not awarder:
            awarder = self.creator

        if not self.allows_award_to(awarder):
            raise BadgeAwardNotAllowedException()

        # If we have an email, but no awardee, try looking up the user.
        if email and not awardee:
            qs = User.objects.filter(email=email)
            if not qs:
                # If there's no user for this email address, create a
                # DeferredAward for future claiming.

                if self.unique and DeferredAward.objects.filter(
                    badge=self, email=email).exists():
                    raise BadgeAlreadyAwardedException()

                da = DeferredAward(badge=self, email=email)
                da.save()
                return da

            # Otherwise, we'll use the most recently created user
            awardee = qs.latest('date_joined')

        if self.unique and self.is_awarded_to(awardee):
            if raise_already_awarded:
                raise BadgeAlreadyAwardedException()
            else:
                return Award.objects.filter(user=awardee, badge=self)[0]

        return Award.objects.create(user=awardee, badge=self,
                                    creator=awarder,
                                    description=description)

    def check_prerequisites(self, awardee, dep_badge, award):
        """Check the prerequisites for this badge. If they're all met, award
        this badge to the user."""
        if self.is_awarded_to(awardee):
            # Not unique, but badge auto-award from prerequisites should only
            # happen once.
            return None
        for badge in self.prerequisites.all():
            if not badge.is_awarded_to(awardee):
                # Bail on the first unmet prerequisites
                return None
        return self.award_to(awardee)

    def is_awarded_to(self, user):
        """Has this badge been awarded to the user?"""
        return Award.objects.filter(user=user, badge=self).count() > 0

    def progress_for(self, user):
        """Get or create (but not save) a progress record for a user"""
        try:
            # Look for an existing progress record...
            p = Progress.objects.get(user=user, badge=self)
        except Progress.DoesNotExist:
            # If none found, create a new one but don't save it yet.
            p = Progress(user=user, badge=self)
        return p

    def allows_nominate_for(self, user):
        """Is nominate_for() allowed for this user?"""
        if not self.nominations_accepted:
            return False
        if None == user:
            return True
        if user.is_anonymous():
            return False
        if user.is_staff or user.is_superuser:
            return True
        if user == self.creator:
            return True

        # TODO: Flag to enable / disable nominations from anyone
        # TODO: List of delegates from whom nominations are accepted

        return True

    def nominate_for(self, nominee, nominator=None):
        """Nominate a nominee for this badge on the nominator's behalf"""
        nomination = Nomination.objects.create(badge=self, creator=nominator,
                                         nominee=nominee)
        if notification:
            if self.creator:
                notification.send([self.creator], 'nomination_submitted',
                                  dict(nomination=nomination,
                                       protocol=DEFAULT_HTTP_PROTOCOL))

        if self.nominations_autoapproved:
            nomination.approve_by(self.creator)

        return nomination

    def is_nominated_for(self, user):
        return Nomination.objects.filter(nominee=user, badge=self).count() > 0

    def as_obi_serialization(self, request=None):
        """Produce an Open Badge Infrastructure serialization of this badge"""
        if request:
            base_url = request.build_absolute_uri('/')[:-1]
        else:
            base_url = 'http://%s' % (Site.objects.get_current().domain,)

        # see: https://github.com/brianlovesdata/openbadges/wiki/Assertions
        if not self.creator:
            issuer = SITE_ISSUER
        else:
            issuer = {
                # TODO: Get from user profile instead?
                "origin": urljoin(base_url, self.creator.get_absolute_url()),
                "name": self.creator.username,
                "contact": self.creator.email
            }

        data = {
            # The version of the spec/hub this manifest is compatible with. Use
            # "0.5.0" for the beta.
            "version": OBI_VERSION,
            # TODO: truncate more intelligently
            "name": self.title[:128],
            # TODO: truncate more intelligently
            "description": self.description[:128] or self.title[:128],
            "criteria": urljoin(base_url, self.get_absolute_url()),
            "issuer": issuer
        }

        image_url = self.image and self.image.url or DEFAULT_BADGE_IMAGE_URL
        data['image'] = urljoin(base_url, image_url)

        return data


class AwardManager(models.Manager):
    def get_query_set(self):
        return super(AwardManager, self).get_query_set().exclude(hidden=True)


@_document_django_model
class Award(models.Model):
    """Representation of a badge awarded to a user"""

    admin_objects = models.Manager()
    objects = AwardManager()

    description = models.TextField(blank=True,
            help_text='Explanation and evidence for the badge award')
    badge = models.ForeignKey(Badge)
    image = models.ImageField(blank=True, null=True,
                              storage=BADGE_UPLOADS_FS,
                              upload_to=mk_upload_to('image', 'png'))
    claim_code = models.CharField(max_length=32, blank=True,
            default='', unique=False, db_index=True,
            help_text='Code used to claim this award')
    user = models.ForeignKey(User, related_name="award_user")
    creator = models.ForeignKey(User, related_name="award_creator",
                                blank=True, null=True)
    hidden = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True, blank=False)
    modified = models.DateTimeField(auto_now=True, blank=False)

    get_permissions_for = get_permissions_for

    class Meta:
        ordering = ['-modified', '-created']

    def __unicode__(self):
        by = self.creator and (u' by %s' % self.creator) or u''
        return u'Award of %s to %s%s' % (self.badge, self.user, by)

    @models.permalink
    def get_absolute_url(self):
        return ('badger.views.award_detail', (self.badge.slug, self.pk))

    def get_upload_meta(self):
        u = self.user.username
        return ("award/%s/%s/%s" % (u[0], u[1], u), self.badge.slug)

    def allows_detail_by(self, user):
        # TODO: Need some logic here, someday.
        return True

    def allows_delete_by(self, user):
        if user.is_anonymous():
            return False
        if user == self.user:
            return True
        if user == self.creator:
            return True
        if user.has_perm('badger.change_award'):
            return True
        return False

    def save(self, *args, **kwargs):

        # Signals and some bits of logic only happen on a new award.
        is_new = not self.pk

        if is_new:
            # Bail if this is an attempt to double-award a unique badge
            if self.badge.unique and self.badge.is_awarded_to(self.user):
                raise BadgeAlreadyAwardedException()

            # Only fire will-be-awarded signal on a new award.
            badge_will_be_awarded.send(sender=self.__class__, award=self)

        super(Award, self).save(*args, **kwargs)

        # Called after super.save(), so we have some auto-gen fields
        if badger.settings.BAKE_AWARD_IMAGES:
            self.bake_obi_image()

        if is_new:
            # Only fire was-awarded signal on a new award.
            badge_was_awarded.send(sender=self.__class__, award=self)

            if notification:
                if self.creator:
                    notification.send([self.badge.creator], 'badge_awarded',
                                      dict(award=self,
                                           protocol=DEFAULT_HTTP_PROTOCOL))
                notification.send([self.user], 'award_received',
                                  dict(award=self,
                                       protocol=DEFAULT_HTTP_PROTOCOL))

            # Since this badge was just awarded, check the prerequisites on all
            # badges that count this as one.
            for dep_badge in self.badge.badge_set.all():
                dep_badge.check_prerequisites(self.user, self.badge, self)

            # Reset any progress for this user & badge upon award.
            Progress.objects.filter(user=self.user, badge=self.badge).delete()

    def delete(self):
        """Make sure nominations get deleted along with awards"""
        Nomination.objects.filter(award=self).delete()
        super(Award, self).delete()

    def as_obi_assertion(self, request=None):
        badge_data = self.badge.as_obi_serialization(request)

        if request:
            base_url = request.build_absolute_uri('/')[:-1]
        else:
            base_url = 'http://%s' % (Site.objects.get_current().domain,)

        # If this award has a creator (ie. not system-issued), tweak the issuer
        # data to reflect award creator.
        # TODO: Is this actually a good idea? Or should issuer be site-wide
        if self.creator:
            badge_data['issuer'] = {
                # TODO: Get from user profile instead?
                "origin": base_url,
                "name": self.creator.username,
                "contact": self.creator.email
            }

        # see: https://github.com/brianlovesdata/openbadges/wiki/Assertions
        # TODO: This salt is stable, and the badge.pk is generally not
        # disclosed anywhere, but is it obscured enough?
        hash_salt = (hashlib.md5('%s-%s' % (self.badge.pk, self.pk))
                            .hexdigest())
        recipient_text = '%s%s' % (self.user.email, hash_salt)
        recipient_hash = ('sha256$%s' % hashlib.sha256(recipient_text)
                                               .hexdigest())
        assertion = {
            "recipient": recipient_hash,
            "salt": hash_salt,
            "evidence": urljoin(base_url, self.get_absolute_url()),
            # TODO: implement award expiration
            # "expires": self.expires.date().isoformat(),
            "issued_on": self.created.date().isoformat(),
            "badge": badge_data
        }
        return assertion

    def bake_obi_image(self, request=None):
        """Bake the OBI JSON badge award assertion into a copy of the original
        badge's image, if one exists."""

        if request:
            base_url = request.build_absolute_uri('/')
        else:
            base_url = 'http://%s' % (Site.objects.get_current().domain,)

        if self.badge.image:
            # Make a duplicate of the badge image
            self.badge.image.open()
            img_copy_fh = StringIO(self.badge.image.file.read())
        else:
            # Make a copy of the default badge image
            img_copy_fh = StringIO(open(DEFAULT_BADGE_IMAGE, 'rb').read())

        try:
            # Try processing the image copy, bail if the image is bad.
            img = Image.open(img_copy_fh)
        except IOError:
            return False

        # Here's where the baking gets done. JSON representation of the OBI
        # assertion gets written into the "openbadges" metadata field
        # see: http://blog.client9.com/2007/08/python-pil-and-png-metadata-take-2.html
        # see: https://github.com/mozilla/openbadges/blob/development/lib/baker.js
        # see: https://github.com/mozilla/openbadges/blob/development/controllers/baker.js
        try:
            from PIL import PngImagePlugin
        except ImportError:
            import PngImagePlugin
        meta = PngImagePlugin.PngInfo()

        # TODO: Will need this, if we stop doing hosted assertions
        # assertion = self.as_obi_assertion(request)
        # meta.add_text('openbadges', json.dumps(assertion))
        hosted_assertion_url = '%s%s' % (
            base_url, reverse('badger.award_detail_json',
                              args=(self.badge.slug, self.id)))
        meta.add_text('openbadges', hosted_assertion_url)

        # And, finally save out the baked image.
        new_img = StringIO()
        img.save(new_img, "PNG", pnginfo=meta)
        img_data = new_img.getvalue()
        name_before = self.image.name
        self.image.save('', ContentFile(img_data), False)
        if (self.image.storage.exists(name_before)):
            self.image.storage.delete(name_before)

        # Update the image field with the new image name
        # NOTE: Can't do a full save(), because this gets called in save()
        Award.objects.filter(pk=self.pk).update(image=self.image)

        return True

    @property
    def nomination(self):
        """Find the nomination behind this award, if any."""
        # TODO: This should really be a foreign key relation, someday.
        try:
            return Nomination.objects.get(award=self)
        except Nomination.DoesNotExist:
            return None


class ProgressManager(models.Manager):
    pass


class Progress(models.Model):
    """Record tracking progress toward auto-award of a badge"""
    badge = models.ForeignKey(Badge)
    user = models.ForeignKey(User, related_name="progress_user")
    percent = models.FloatField(default=0)
    counter = models.FloatField(default=0, blank=True, null=True)
    notes = JSONField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, blank=False)
    modified = models.DateTimeField(auto_now=True, blank=False)

    class Meta:
        unique_together = ('badge', 'user')
        verbose_name_plural = "Progresses"

    get_permissions_for = get_permissions_for

    def __unicode__(self):
        perc = self.percent and (' (%s%s)' % (self.percent, '%')) or ''
        return u'Progress toward %s by %s%s' % (self.badge, self.user, perc)

    def save(self, *args, **kwargs):
        """Save the progress record, with before and after signals"""
        # Signals and some bits of logic only happen on a new award.
        is_new = not self.pk

        # Bail if this is an attempt to double-award a unique badge
        if (is_new and self.badge.unique and
                self.badge.is_awarded_to(self.user)):
            raise BadgeAlreadyAwardedException()

        super(Progress, self).save(*args, **kwargs)

        # If the percent is over/equal to 1.0, auto-award on save.
        if self.percent >= 100:
            self.badge.award_to(self.user)

    def _quiet_save(self, raise_exception=False):
        try:
            self.save()
        except BadgeAlreadyAwardedException as e:
            if raise_exception:
                raise e

    def update_percent(self, current, total=None, raise_exception=False):
        """Update the percent completion value."""
        if total is None:
            value = current
        else:
            value = (float(current) / float(total)) * 100.0
        self.percent = value
        self._quiet_save(raise_exception)

    def increment_by(self, amount, raise_exception=False):
        # TODO: Do this with an UPDATE counter+amount in DB
        self.counter += amount
        self._quiet_save(raise_exception)
        return self

    def decrement_by(self, amount, raise_exception=False):
        # TODO: Do this with an UPDATE counter-amount in DB
        self.counter -= amount
        self._quiet_save(raise_exception)
        return self


class DeferredAwardManager(models.Manager):

    def get_claim_groups(self, badge):
        """Build a list of all known claim group IDs for a badge"""
        qs = (self.filter(badge=badge)
                    .values('claim_group').distinct().all()
                    .annotate(modified=Max('modified'), count=Count('id')))
        return [x
                for x in qs
                if x['claim_group']]

    def generate(self, badge, user=None, amount=10, reusable=False):
        """Generate a number of deferred awards for a badge"""
        claim_group = '%s-%s' % (time(), random.randint(0, 10000))
        for i in range(0, amount):
            (DeferredAward(badge=badge, creator=user, reusable=reusable,
                           claim_group=claim_group).save())
        return claim_group

    def claim_by_email(self, awardee):
        """Claim all deferred awards that match the awardee's email"""
        return self._claim_qs(awardee, self.filter(email=awardee.email))

    def claim_by_code(self, awardee, code):
        """Claim a deferred award by code for the awardee"""
        return self._claim_qs(awardee, self.filter(claim_code=code))

    def _claim_qs(self, awardee, qs):
        """Claim all the deferred awards that match the queryset"""
        for da in qs:
            da.claim(awardee)


def make_random_code():
    """Generare a random code, using a set of alphanumeric characters that
    attempts to avoid ambiguously similar shapes."""
    s = '3479acefhjkmnprtuvwxy'
    return ''.join([random.choice(s) for x in range(CLAIM_CODE_LENGTH)])


class DeferredAwardGrantNotAllowedException(BadgerException):
    """Attempt to grant a DeferredAward not allowed"""


@_document_django_model
class DeferredAward(models.Model):
    """Deferred award, can be converted into into a real award."""
    objects = DeferredAwardManager()

    badge = models.ForeignKey(Badge)
    description = models.TextField(blank=True)
    reusable = models.BooleanField(default=False)
    email = models.EmailField(blank=True, null=True, db_index=True)
    claim_code = models.CharField(max_length=32,
            default=make_random_code, unique=True, db_index=True)
    claim_group = models.CharField(max_length=32, blank=True, null=True,
            db_index=True)
    creator = models.ForeignKey(User, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, blank=False)
    modified = models.DateTimeField(auto_now=True, blank=False)

    class Meta:
        ordering = ['-modified', '-created']
        permissions = (
            ("grant_deferredaward",
             _(u'Can grant deferred award to an email address')),
        )

    get_permissions_for = get_permissions_for

    def allows_detail_by(self, user):
        # TODO: Need some logic here, someday.
        return True

    def allows_claim_by(self, user):
        if user.is_anonymous():
            return False
        # TODO: Need some logic here, someday.
        # TODO: Could enforce that the user.email == self.email, but I want to
        # allow for people with multiple email addresses. That is, I get an
        # award claim invite sent to lorchard@mozilla.com, but I claim it while
        # signed in as me@lmorchard.com. Warning displayed in the view.
        return True

    def allows_grant_by(self, user):
        if user.is_anonymous():
            return False
        if user.has_perm('badger.grant_deferredaward'):
            return True
        if self.badge.allows_award_to(user):
            return True
        if user == self.creator:
            return True
        return False

    def get_claim_url(self):
        """Get the URL to a page where this DeferredAward can be claimed."""
        return reverse('badger.views.claim_deferred_award',
                       args=(self.claim_code,))

    def save(self, **kwargs):
        """Save the DeferredAward, sending a claim email if it's new"""
        is_new = not self.pk
        has_existing_deferreds = False
        if self.email:
            has_existing_deferreds = DeferredAward.objects.filter(
                email=self.email).exists()

        super(DeferredAward, self).save(**kwargs)

        if is_new and self.email and not has_existing_deferreds:
            try:
                # If this is new and there's an email, send an invite to claim.
                context = Context(dict(
                    deferred_award=self,
                    badge=self.badge,
                    protocol=DEFAULT_HTTP_PROTOCOL,
                    current_site=Site.objects.get_current()
                ))
                tmpl_name = 'badger/deferred_award_%s.txt'
                subject = render_to_string(tmpl_name % 'subject', {}, context)
                # Email subjects can't contain newlines, so we strip it. It makes
                # the template less fragile.
                subject = subject.strip()
                body = render_to_string(tmpl_name % 'body', {}, context)
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL,
                          [self.email], fail_silently=False)
            except TemplateDoesNotExist:
                pass

    def claim(self, awardee):
        """Claim the deferred award for the given user"""
        try:
            award = self.badge.award_to(awardee=awardee, awarder=self.creator)
            award.claim_code = self.claim_code
            award.save()
        except (BadgeAlreadyAwardedException, BadgeAwardNotAllowedException):
            # Just swallow up and ignore any issues in awarding.
            award = None
        if not self.reusable:
            # Self-destruct, if not made reusable.
            self.delete()
        return award

    def grant_to(self, email, granter):
        """Grant this deferred award to the given email"""
        if not self.allows_grant_by(granter):
            raise DeferredAwardGrantNotAllowedException()
        if not self.reusable:
            # If not reusable, reassign email and regenerate claim code.
            self.email = email
            self.claim_code = make_random_code()
            self.save()
            return self
        else:
            # If reusable, create a clone and leave this deferred award alone.
            new_da = DeferredAward(badge=self.badge, email=email,
                                   creator=granter, reusable=False)
            new_da.save()
            return new_da


class NominationException(BadgerException):
    """Nomination model exception"""


class NominationApproveNotAllowedException(NominationException):
    """Attempt to approve a nomination was disallowed"""


class NominationAcceptNotAllowedException(NominationException):
    """Attempt to accept a nomination was disallowed"""


class NominationRejectNotAllowedException(NominationException):
    """Attempt to reject a nomination was disallowed"""


class NominationManager(models.Manager):
    pass


@_document_django_model
class Nomination(models.Model):
    """Representation of a user nominated by another user for a badge"""
    objects = NominationManager()

    badge = models.ForeignKey(Badge)
    nominee = models.ForeignKey(User, related_name="nomination_nominee",
            blank=False, null=False)
    accepted = models.BooleanField(default=False)
    creator = models.ForeignKey(User, related_name="nomination_creator",
            blank=True, null=True)
    approver = models.ForeignKey(User, related_name="nomination_approver",
            blank=True, null=True)
    rejected_by = models.ForeignKey(User, related_name="nomination_rejected_by",
            blank=True, null=True)
    rejected_reason = models.TextField(blank=True)
    award = models.ForeignKey(Award, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, blank=False)
    modified = models.DateTimeField(auto_now=True, blank=False)

    get_permissions_for = get_permissions_for

    def __unicode__(self):
        return u'Nomination for %s to %s by %s' % (self.badge, self.nominee,
                                                   self.creator)

    def get_absolute_url(self):
        return reverse('badger.views.nomination_detail',
                       args=(self.badge.slug, self.id))

    def save(self, *args, **kwargs):

        # Signals and some bits of logic only happen on a new nomination.
        is_new = not self.pk

        # Bail if this is an attempt to double-award a unique badge
        if (is_new and self.badge.unique and
                self.badge.is_awarded_to(self.nominee)):
            raise BadgeAlreadyAwardedException()

        if is_new:
            user_will_be_nominated.send(sender=self.__class__,
                                        nomination=self)

        if self.is_approved and self.is_accepted:
            self.award = self.badge.award_to(self.nominee, self.approver)

        super(Nomination, self).save(*args, **kwargs)

        if is_new:
            user_was_nominated.send(sender=self.__class__,
                                    nomination=self)

    def allows_detail_by(self, user):
        if (user.is_staff or
               user.is_superuser or
               user == self.badge.creator or
               user == self.nominee or
               user == self.creator):
            return True

        # TODO: List of delegates empowered by badge creator to approve nominations

        return False

    @property
    def is_approved(self):
        """Has this nomination been approved?"""
        return self.approver is not None

    def allows_approve_by(self, user):
        if self.is_approved or self.is_rejected:
            return False
        if user.is_staff or user.is_superuser:
            return True
        if user == self.badge.creator:
            return True

        # TODO: List of delegates empowered by badge creator to approve nominations

        return False

    def approve_by(self, approver):
        """Approve this nomination.
        Also awards, if already accepted."""
        if not self.allows_approve_by(approver):
            raise NominationApproveNotAllowedException()
        self.approver = approver
        nomination_will_be_approved.send(sender=self.__class__,
                                         nomination=self)
        self.save()
        nomination_was_approved.send(sender=self.__class__,
                                     nomination=self)
        if notification:
            if self.badge.creator:
                notification.send([self.badge.creator], 'nomination_approved',
                                  dict(nomination=self,
                                       protocol=DEFAULT_HTTP_PROTOCOL))
            if self.creator:
                notification.send([self.creator], 'nomination_approved',
                                  dict(nomination=self,
                                       protocol=DEFAULT_HTTP_PROTOCOL))
            notification.send([self.nominee], 'nomination_received',
                              dict(nomination=self,
                                   protocol=DEFAULT_HTTP_PROTOCOL))

        return self

    @property
    def is_accepted(self):
        """Has this nomination been accepted?"""
        return self.accepted

    def allows_accept(self, user):
        if self.is_accepted or self.is_rejected:
            return False
        if user.is_staff or user.is_superuser:
            return True
        if user == self.nominee:
            return True
        return False

    def accept(self, user):
        """Accept this nomination for the nominee.

        Also awards, if already approved.
        """
        if not self.allows_accept(user):
            raise NominationAcceptNotAllowedException()
        self.accepted = True
        nomination_will_be_accepted.send(sender=self.__class__,
                                         nomination=self)
        self.save()
        nomination_was_accepted.send(sender=self.__class__,
                                     nomination=self)

        if notification:
            if self.badge.creator:
                notification.send([self.badge.creator], 'nomination_accepted',
                                  dict(nomination=self,
                                       protocol=DEFAULT_HTTP_PROTOCOL))
            if self.creator:
                notification.send([self.creator], 'nomination_accepted',
                                  dict(nomination=self,
                                       protocol=DEFAULT_HTTP_PROTOCOL))

        return self

    @property
    def is_rejected(self):
        """Has this nomination been rejected?"""
        return self.rejected_by is not None

    def allows_reject_by(self, user):
        if self.is_approved or self.is_rejected:
            return False
        if user.is_staff or user.is_superuser:
            return True
        if user == self.nominee:
            return True
        if user == self.badge.creator:
            return True
        return False

    def reject_by(self, user, reason=''):
        if not self.allows_reject_by(user):
            raise NominationRejectNotAllowedException()
        self.rejected_by = user
        self.rejected_reason = reason
        nomination_will_be_rejected.send(sender=self.__class__,
                                         nomination=self)
        self.save()
        nomination_was_rejected.send(sender=self.__class__,
                                     nomination=self)

        if notification:
            if self.badge.creator:
                notification.send([self.badge.creator], 'nomination_rejected',
                                  dict(nomination=self,
                                       protocol=DEFAULT_HTTP_PROTOCOL))
            if self.creator:
                notification.send([self.creator], 'nomination_rejected',
                                  dict(nomination=self,
                                       protocol=DEFAULT_HTTP_PROTOCOL))

        return self


# HACK: Django 1.2 is missing receiver and user_logged_in
if receiver and user_logged_in:
    @receiver(user_logged_in)
    def claim_on_login(sender, request, user, **kwargs):
        """When a user logs in, claim any deferred awards by email"""
        DeferredAward.objects.claim_by_email(user)

########NEW FILE########
__FILENAME__ = printing
#!/usr/bin/env python
"""Quick and dirty render-to-PDF for badge award claim codes"""

import logging
import math
import urllib
import urllib2
try:
    from cStringIO import cStringIO as StringIO
except ImportError:
    from StringIO import StringIO

from reportlab.pdfgen import canvas
from reportlab.lib import pagesizes
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, BaseDocTemplate, Paragraph, Preformatted, Spacer,
    PageBreak, Frame, FrameBreak, PageTemplate, Image, Table)
from reportlab.platypus.doctemplate import LayoutError
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.rl_config import defaultPageSize 
from reportlab.lib.units import inch 
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from reportlab.lib import textsplit

from reportlab.lib.utils import ImageReader

from django.conf import settings

from django.http import (HttpResponseRedirect, HttpResponse,
        HttpResponseForbidden, HttpResponseNotFound)

from django.utils.html import conditional_escape


def render_claims_to_pdf(request, slug, claim_group, deferred_awards):
    """Currently hard-coded to print to Avery 22805 labels"""

    metrics = dict(
        page_width=(8.5 * inch),
        page_height=(11.0 * inch),

        top_margin=(0.5 * inch),
        left_margin=((25.0 / 32.0) * inch),

        qr_overlap=((1.0 / 32.0) * inch),
        padding=((1.0 / 16.0) * inch),

        horizontal_spacing=((5.0 / 16.0) * inch),
        vertical_spacing=((13.0 / 64.0) * inch),

        width=(1.5 * inch),
        height=(1.5 * inch),
    )

    debug = (request.GET.get('debug', False) is not False)

    pagesize = (metrics['page_width'], metrics['page_height'])
    cols = int((metrics['page_width'] - metrics['left_margin']) /
               (metrics['width'] + metrics['horizontal_spacing']))
    rows = int((metrics['page_height'] - metrics['top_margin']) /
               (metrics['height'] + metrics['vertical_spacing']))
    per_page = (cols * rows)
    label_ct = len(deferred_awards)
    page_ct = math.ceil(label_ct / per_page)

    pages = [deferred_awards[x:x + (per_page)]
             for x in range(0, label_ct, per_page)]

    response = HttpResponse(content_type='application/pdf; charset=utf-8')
    if not debug:
        # If debugging, don't force download.
        response['Content-Disposition'] = ('attachment; filename="%s-%s.pdf"' %
                (slug.encode('utf-8', 'replace'), claim_group))

    badge_img = None

    fout = StringIO()
    c = canvas.Canvas(fout, pagesize=pagesize)

    for page in pages:
        c.translate(metrics['left_margin'],
                    metrics['page_height'] - metrics['top_margin'])

        for row in range(0, rows, 1):
            c.translate(0.0, 0 - metrics['height'])
            c.saveState()

            for col in range(0, cols, 1):

                try:
                    da = page.pop(0)
                except IndexError:
                    continue

                if not badge_img:
                    image_fin = da.badge.image.file
                    image_fin.open()
                    badge_img = ImageReader(StringIO(image_fin.read()))

                c.saveState()
                render_label(request, c, metrics, da, badge_img, debug)
                c.restoreState()

                dx = (metrics['width'] + metrics['horizontal_spacing'])
                c.translate(dx, 0.0)

            c.restoreState()
            c.translate(0.0, 0 - metrics['vertical_spacing'])

        c.showPage()

    c.save()
    response.write(fout.getvalue())
    return response


def render_label(request, c, metrics, da, badge_img, debug):
    """Render a single label"""
    badge = da.badge

    badge_image_width = (1.0 + (1.0 / 64.0)) * inch
    badge_image_height = (1.0 + (1.0 / 64.0)) * inch

    qr_left = badge_image_width - metrics['qr_overlap']
    qr_bottom = badge_image_height - metrics['qr_overlap']
    qr_width = metrics['width'] - qr_left
    qr_height = metrics['height'] - qr_bottom

    if False and debug:
        # Draw some layout lines on debug.
        c.setLineWidth(0.3)
        c.rect(0, 0, metrics['width'], metrics['height'])
        c.rect(qr_left, qr_bottom, qr_width, qr_height)
        c.rect(0, 0, badge_image_width, badge_image_height)

    fit_text(c, da.badge.title,
             0.0, badge_image_height,
             badge_image_width, qr_height)

    c.saveState()
    c.rotate(-90)

    code_height = qr_height * (0.45)
    claim_height = qr_height - code_height

    c.setFont("Courier", code_height)
    c.drawCentredString(0 - (badge_image_width / 2.0),
                        metrics['height'] - code_height,
                        da.claim_code)

    text = """
        <font name="Helvetica">Claim at</font> <font name="Courier">%s</font>
    """ % (settings.SITE_TITLE)
    fit_text(c, text,
             0 - badge_image_height, badge_image_width,
             badge_image_width, claim_height)

    c.restoreState()

    # Attempt to build a QR code image for the claim URL
    claim_url = request.build_absolute_uri(da.get_claim_url())
    qr_img = None
    try:
        # Try using PyQRNative: http://code.google.com/p/pyqrnative/
        # badg.us should have this in vendor-local
        from PyQRNative import QRCode, QRErrorCorrectLevel
        # TODO: Good-enough settings?
        if len(claim_url) < 20:
            qr = QRCode(3, QRErrorCorrectLevel.L)
        elif len(claim_url) < 50:
            qr = QRCode(4, QRErrorCorrectLevel.L)
        else:
            qr = QRCode(10, QRErrorCorrectLevel.L)
        qr.addData(claim_url)
        qr.make()
        qr_img = ImageReader(qr.makeImage())

    except ImportError:
        try:
            # Hmm, if we don't have PyQRNative, then try abusing this web
            # service. Should be fine for low volumes.
            qr_url = ("http://api.qrserver.com/v1/create-qr-code/?%s" %
                urllib.urlencode({'size': '%sx%s' % (500, 500),
                                  'data': claim_url}))

            qr_img = ImageReader(StringIO(urllib2.urlopen(qr_url).read()))

        except Exception:
            # Ignore issues in drawing the QR code - maybe show an error?
            pass

    if qr_img:
        c.drawImage(qr_img, qr_left, qr_bottom, qr_width, qr_height)

    c.drawImage(badge_img,
                0.0 * inch, 0.0 * inch,
                badge_image_width, badge_image_height)


def fit_text(c, text, x, y, max_w, max_h, font_name='Helvetica',
             padding_w=4.5, padding_h=4.5, font_decrement=0.0625):
    """Draw text, reducing font size until it fits with a given max width and
    height."""

    max_w -= (padding_w * 2.0)
    max_h -= (padding_h * 2.0)

    x += padding_w
    y += padding_h

    font_size = max_h

    while font_size > 1.0:
        ps = ParagraphStyle(name='text', alignment=TA_CENTER,
                            fontName=font_name, fontSize=font_size,
                            leading=font_size)
        p = Paragraph(text, ps)
        actual_w, actual_h = p.wrapOn(c, max_w, max_h)
        if actual_h > max_h or actual_w > max_w:
            font_size -= font_decrement
        else:
            y_pad = (max_h - actual_h) / 2
            p.drawOn(c, x, y + y_pad)
            return

########NEW FILE########
__FILENAME__ = signals
"""Signals relating to badges.

For each of these, you can register to receive them using standard
Django methods.

Let's look at :py:func:`badges.signals.badge_will_be_awarded`. For
example::

    from badger.signals import badge_will_be_awarded

    @receiver(badge_will_be_awarded)
    def my_callback(sender, **kwargs):
        award = kwargs['award']

        print('sender: {0}'.format(sender))
        print('award: {0}'.format(award))


The sender will be :py:class:`badges.models.Award` class. The
``award`` argument will be the ``Award`` instance that is being
awarded.

"""
from django.dispatch import Signal


def _signal_with_docs(args, doc):
    # FIXME - this fixes the docstring, but not the provided arguments
    # so the API docs look weird.
    signal = Signal(providing_args=args)
    signal.__doc__ = doc
    return signal


badge_will_be_awarded = _signal_with_docs(
    ['award'],
    """Fires off before badge is awarded

    Signal receiver parameters:

    :arg award: the Award instance

    """)

badge_was_awarded = _signal_with_docs(
    ['award'],
    """Fires off after badge is awarded

    Signal receiver parameters:

    :arg award: the Award instance

    """)

user_will_be_nominated = _signal_with_docs(
    ['nomination'],
    """Fires off before user is nominated for a badge

    Signal receiver parameters:

    :arg nomination: the Nomination instance

    """)

user_was_nominated = _signal_with_docs(
    ['nomination'],
    """Fires off after user is nominated for a badge

    Signal receiver parameters:

    :arg nomination: the Nomination instance

    """)

nomination_will_be_approved = _signal_with_docs(
    ['nomination'],
    """Fires off before nomination is approved

    Signal receiver parameters:

    :arg nomination: the Nomination instance being approved

    """)

nomination_was_approved = _signal_with_docs(
    ['nomination'],
    """Fires off after nomination is approved

    Signal receiver parameters:

    :arg nomination: the Nomination instance being approved

    """)

nomination_will_be_accepted = _signal_with_docs(
    ['nomination'],
    """Fires off before nomination is accepted

    Signal receiver parameters:

    :arg nomination: the Nomination instance being accepted

    """)

nomination_was_accepted = _signal_with_docs(
    ['nomination'],
    """Fires off after nomination is accepted

    Signal receiver parameters:

    :arg nomination: the Nomination instance being accepted

    """)

nomination_will_be_rejected = _signal_with_docs(
    ['nomination'],
    """Fires off before nomination is rejected

    Signal receiver parameters:

    :arg nomination: the Nomination instance being rejected

    """)

nomination_was_rejected = _signal_with_docs(
    ['nomination'],
    """Fires off after nomination is rejected

    Signal receiver parameters:

    :arg nomination: the Nomination instance being rejected

    """)

########NEW FILE########
__FILENAME__ = badger_tags
# django
from django import template
from django.conf import settings
from django.shortcuts import  get_object_or_404
from badger.models import Award, Badge


from django.contrib.auth.models import SiteProfileNotAvailable
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse

import hashlib
import urllib

from django.utils.translation import ugettext_lazy as _

register = template.Library()


@register.filter
def permissions_for(obj, user):
    try:
        return obj.get_permissions_for(user)
    except:
        return {}


@register.filter
def key(obj, name):
    try:
        return obj[name]
    except:
        return None


@register.simple_tag
def user_avatar(user, secure=False, size=256, rating='pg', default=''):

    try:
        profile = user.get_profile()
        if profile.avatar:
            return profile.avatar.url
    except SiteProfileNotAvailable:
        pass
    except ObjectDoesNotExist:
        pass
    except AttributeError:
        pass

    base_url = (secure and 'https://secure.gravatar.com' or
        'http://www.gravatar.com')
    m = hashlib.md5(user.email)
    return '%(base_url)s/avatar/%(hash)s?%(params)s' % dict(
        base_url=base_url, hash=m.hexdigest(),
        params=urllib.urlencode(dict(
            s=size, d=default, r=rating
        ))
    )


@register.simple_tag
def award_image(award):
    if award.image:
        img_url = award.image.url
    elif award.badge.image:
        img_url = award.badge.image.url
    else:
        img_url = "/media/img/default-badge.png"

    return img_url


@register.simple_tag
def user_award_list(badge, user):
    if badge.allows_award_to(user):
        return '<li><a class="award_badge" href="%s">%s</a></li>' % (reverse('badger.views.award_badge', args=[badge.slug, ]), _(u'Issue award'))
    else:
        return ''

########NEW FILE########
__FILENAME__ = test_badges_py
import logging

from django.conf import settings
from django.core.management import call_command
from django.template.defaultfilters import slugify
from django.contrib.auth.models import User

from nose.tools import assert_equal, with_setup, assert_false, eq_, ok_
from nose.plugins.attrib import attr

from . import BadgerTestCase

import badger
from badger.utils import get_badge, award_badge

from badger.models import (Badge, Award, Progress,
        BadgeAwardNotAllowedException,
        BadgeAlreadyAwardedException)

from badger_example.models import GuestbookEntry


class BadgesPyTest(BadgerTestCase):

    def setUp(self):
        self.user_1 = self._get_user(username="user_1",
                email="user_1@example.com", password="user_1_pass")
        Award.objects.all().delete()

    def tearDown(self):
        Award.objects.all().delete()
        Badge.objects.all().delete()

    def test_badges_from_fixture(self):
        """Badges can be created via fixture"""
        b = get_badge("test-1")
        eq_("Test #1", b.title)
        b = get_badge("button-clicker")
        eq_("Button Clicker", b.title)
        b = get_badge("first-post")
        eq_("First post!", b.title)

    def test_badges_from_code(self):
        """Badges can be created in code"""
        b = get_badge("test-2")
        eq_("Test #2", b.title)
        b = get_badge("awesomeness")
        eq_("Awesomeness (you have it)", b.title)
        b = get_badge("250-words")
        eq_("250 Words", b.title)
        b = get_badge("master-badger")
        eq_("Master Badger", b.title)

    def test_badge_awarded_on_model_create(self):
        """A badge should be awarded on first guestbook post"""
        user = self._get_user()
        post = GuestbookEntry(message="This is my first post", creator=user)
        post.save()
        b = get_badge('first-post')
        ok_(b.is_awarded_to(user))

        # "first-post" badge should be unique
        post = GuestbookEntry(message="This is my first post", creator=user)
        post.save()
        eq_(1, Award.objects.filter(user=user, badge=b).count())

    def test_badge_awarded_on_content(self):
        """A badge should be awarded upon 250 words worth of guestbook posts
        created"""
        user = self._get_user()

        b = get_badge('250-words')

        # Post 5 words in progress...
        GuestbookEntry.objects.create(creator=user,
            message="A few words to start")
        ok_(not b.is_awarded_to(user))
        eq_(5, b.progress_for(user).counter)

        # Post 5 more words in progress...
        GuestbookEntry.objects.create(creator=user,
            message="A few more words posted")
        ok_(not b.is_awarded_to(user))
        eq_(10, b.progress_for(user).counter)

        # Post 90 more...
        msg = ' '.join('lots of words that repeat' for x in range(18))
        GuestbookEntry.objects.create(creator=user, message=msg)
        ok_(not b.is_awarded_to(user))
        eq_(100, b.progress_for(user).counter)

        # And 150 more for the finale...
        msg = ' '.join('lots of words that repeat' for x in range(30))
        GuestbookEntry.objects.create(creator=user, message=msg)

        # Should result in a badge award and reset progress.
        ok_(b.is_awarded_to(user))
        eq_(0, b.progress_for(user).counter)

        # But, just checking the reset counter shouldn't create a new DB row.
        eq_(0, Progress.objects.filter(user=user, badge=b).count())

    def test_badge_awarded_on_content_percent(self):
        """A badge should be awarded upon 250 words worth of guestbook posts
        created, but the tracking is done via percentage"""
        user = self._get_user()

        b = get_badge('250-words-by-percent')

        # Post 5 words in progress...
        GuestbookEntry.objects.create(creator=user,
            message="A few words to start")
        ok_(not b.is_awarded_to(user))
        eq_((5.0 / 250.0) * 100.0, b.progress_for(user).percent)

        # Post 5 more words in progress...
        GuestbookEntry.objects.create(creator=user,
            message="A few more words posted")
        ok_(not b.is_awarded_to(user))
        eq_((10.0 / 250.0) * 100.0, b.progress_for(user).percent)

        # Post 90 more...
        msg = ' '.join('lots of words that repeat' for x in range(18))
        GuestbookEntry.objects.create(creator=user, message=msg)
        ok_(not b.is_awarded_to(user))
        eq_((100.0 / 250.0) * 100.0, b.progress_for(user).percent)

        # And 150 more for the finale...
        msg = ' '.join('lots of words that repeat' for x in range(30))
        GuestbookEntry.objects.create(creator=user, message=msg)

        # Should result in a badge award and reset progress.
        ok_(b.is_awarded_to(user))
        eq_(0, b.progress_for(user).percent)

        # But, just checking the reset percent shouldn't create a new DB row.
        eq_(0, Progress.objects.filter(user=user, badge=b).count())

    def test_metabadge_awarded(self):
        """Upon completing collection of badges, award a meta-badge"""
        user = self._get_user()

        ok_(not get_badge('master-badger').is_awarded_to(user))

        # Cover a few bases on award creation...
        award_badge('test-1', user)
        award_badge('test-2', user)
        a = Award(badge=get_badge('button-clicker'), user=user)
        a.save()

        get_badge('awesomeness').award_to(user)
        eq_(1, Award.objects.filter(badge=get_badge("master-badger"),
                                    user=user).count())
        
        ok_(get_badge('master-badger').is_awarded_to(user))

    def test_progress_quiet_save(self):
        """Progress will not raise a BadgeAlreadyAwardedException unless told"""
        b = self._get_badge('imunique')
        b.unique = True
        b.save()

        user = self._get_user()

        b.progress_for(user).update_percent(50)
        b.progress_for(user).update_percent(75)
        b.progress_for(user).update_percent(100)

        ok_(b.is_awarded_to(user))

        try:
            b.progress_for(user).update_percent(50)
            b.progress_for(user).update_percent(75)
            b.progress_for(user).update_percent(100)
        except BadgeAlreadyAwardedException:
            ok_(False, "Exception should not have been raised")

        try:
            b.progress_for(user).update_percent(50, raise_exception=True)
            b.progress_for(user).update_percent(75, raise_exception=True)
            b.progress_for(user).update_percent(100, raise_exception=True)
            ok_(False, "Exception should have been raised")
        except BadgeAlreadyAwardedException:
            pass

    def _get_user(self, username="tester", email="tester@example.com",
            password="trustno1"):
        (user, created) = User.objects.get_or_create(username=username,
                defaults=dict(email=email))
        if created:
            user.set_password(password)
            user.save()
        return user

    def _get_badge(self, title="Test Badge",
            description="This is a test badge", creator=None):
        creator = creator or self.user_1
        (badge, created) = Badge.objects.get_or_create(title=title,
                defaults=dict(description=description, creator=creator))
        return badge

########NEW FILE########
__FILENAME__ = test_feeds
import logging
import feedparser

from django.conf import settings

from django.http import HttpRequest
from django.test.client import Client

from pyquery import PyQuery as pq

from nose.tools import assert_equal, with_setup, assert_false, eq_, ok_
from nose.plugins.attrib import attr

from django.template.defaultfilters import slugify

from django.contrib.auth.models import User

try:
    from commons.urlresolvers import reverse
except ImportError:
    from django.core.urlresolvers import reverse

from . import BadgerTestCase

from badger.models import (Badge, Award, Progress,
        BadgeAwardNotAllowedException)
from badger.utils import get_badge, award_badge


class BadgerFeedsTest(BadgerTestCase):

    def setUp(self):
        self.testuser = self._get_user()
        self.client = Client()
        Award.objects.all().delete()

    def tearDown(self):
        Award.objects.all().delete()
        Badge.objects.all().delete()

    def test_award_feeds(self):
        """Can view award detail"""
        user = self._get_user()
        user2 = self._get_user(username='tester2')

        b1, created = Badge.objects.get_or_create(creator=user, title="Code Badge #1")
        award = b1.award_to(user2)

        # The award should show up in each of these feeds.
        feed_urls = (
            reverse('badger.feeds.awards_recent', 
                    args=('atom', )),
            reverse('badger.feeds.awards_by_badge', 
                    args=('atom', b1.slug, )),
            reverse('badger.feeds.awards_by_user',
                    args=('atom', user2.username,)),
        )

        # Check each of the feeds
        for feed_url in feed_urls:
            r = self.client.get(feed_url, follow=True)

            # The feed should be parsed without issues by feedparser
            feed = feedparser.parse(r.content)
            eq_(0, feed.bozo)

            # Look through entries for the badge title
            found_it = False
            for entry in feed.entries:
                if b1.title in entry.title and user2.username in entry.title:
                    found_it = True

            ok_(found_it)

    def _get_user(self, username="tester", email="tester@example.com",
            password="trustno1"):
        (user, created) = User.objects.get_or_create(username=username,
                defaults=dict(email=email))
        if created:
            user.set_password(password)
            user.save()
        return user

########NEW FILE########
__FILENAME__ = test_middleware
import logging
import time

from nose.tools import assert_equal, with_setup, assert_false, eq_, ok_
from nose.plugins.attrib import attr

from django.http import HttpRequest, HttpResponse
from django.utils import simplejson as json
from django.test.client import Client

from django.core.urlresolvers import reverse
from django.contrib.auth.models import AnonymousUser

from . import BadgerTestCase

import badger

from badger.models import (Badge, Award, Nomination, Progress, DeferredAward)
from badger.middleware import (RecentBadgeAwardsMiddleware,
                               LAST_CHECK_COOKIE_NAME)


class RecentBadgeAwardsMiddlewareTest(BadgerTestCase):

    def setUp(self):
        self.creator = self._get_user(username='creator')
        self.testuser = self._get_user()
        self.mw = RecentBadgeAwardsMiddleware()

        self.badges = []
        for n in ('test1','test2','test3'):
            badge = Badge(title=n, creator=self.creator)
            badge.save()
            self.badges.append(badge)

        self.awards = []
        for b in self.badges:
            self.awards.append(b.award_to(self.testuser))

    def tearDown(self):
        Award.objects.all().delete()
        Badge.objects.all().delete()

    def test_no_process_request(self):
        """If something skips our process_request, the process_response hook
        should do nothing."""
        request = HttpRequest()
        response = HttpResponse()
        self.mw.process_response(request, response)

    def test_anonymous(self):
        """No recent awards for anonymous user"""
        request = HttpRequest()
        request.user = AnonymousUser()
        self.mw.process_request(request)
        ok_(hasattr(request, 'recent_badge_awards'))
        eq_(0, len(request.recent_badge_awards))

    def test_no_cookie(self):
        """No recent awards without a last-check cookie, but set the cookie"""
        request = HttpRequest()
        request.user = self.testuser
        self.mw.process_request(request)
        ok_(hasattr(request, 'recent_badge_awards'))
        eq_(0, len(request.recent_badge_awards))
        eq_(False, request.recent_badge_awards.was_used)

        response = HttpResponse()
        self.mw.process_response(request, response)
        ok_(LAST_CHECK_COOKIE_NAME in response.cookies)

    def test_unused_recent_badge_awards(self):
        """Recent awards offered with cookie, but cookie not updated if unused"""
        request = HttpRequest()
        request.user = self.testuser
        request.COOKIES[LAST_CHECK_COOKIE_NAME] = '1156891591.492586'
        self.mw.process_request(request)
        ok_(hasattr(request, 'recent_badge_awards'))

        response = HttpResponse()
        self.mw.process_response(request, response)
        ok_(LAST_CHECK_COOKIE_NAME not in response.cookies)

    def test_used_recent_badge_awards(self):
        """Recent awards offered with cookie, cookie updated if set used"""
        old_time = '1156891591.492586'
        request = HttpRequest()
        request.user = self.testuser
        request.COOKIES[LAST_CHECK_COOKIE_NAME] = old_time
        self.mw.process_request(request)
        ok_(hasattr(request, 'recent_badge_awards'))

        # Use the recent awards set by checking length and contents
        eq_(3, len(request.recent_badge_awards))
        for ra in request.recent_badge_awards:
            ok_(ra in self.awards)

        response = HttpResponse()
        self.mw.process_response(request, response)
        ok_(LAST_CHECK_COOKIE_NAME in response.cookies)
        ok_(response.cookies[LAST_CHECK_COOKIE_NAME].value != old_time)

########NEW FILE########
__FILENAME__ = test_models
# -*- coding: utf-8 -*-
from os.path import dirname
import logging
import time

try:
    from PIL import Image
except ImportError:
    import Image

from django.conf import settings

from django.core.management import call_command
from django.db.models import loading
from django.core.files.base import ContentFile
from django.http import HttpRequest
from django.utils import simplejson as json
from django.test.client import Client

from django.core import mail

from nose.tools import assert_equal, with_setup, assert_false, eq_, ok_
from nose.plugins.attrib import attr

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None

try:
    from funfactory.urlresolvers import reverse
except ImportError:
    from django.core.urlresolvers import reverse

from django.contrib.auth.models import User

from . import BadgerTestCase, patch_settings

import badger
from badger.models import (Badge, Award, Nomination, Progress, DeferredAward,
        BadgeAwardNotAllowedException,
        BadgeAlreadyAwardedException,
        DeferredAwardGrantNotAllowedException,
        NominationApproveNotAllowedException,
        NominationAcceptNotAllowedException,
        NominationRejectNotAllowedException,
        SITE_ISSUER, slugify)

from badger_example.models import GuestbookEntry


BASE_URL = 'http://example.com'
BADGE_IMG_FN = "%s/fixtures/default-badge.png" % dirname(dirname(__file__))


class BadgerBadgeTest(BadgerTestCase):

    def test_get_badge(self):
        """Can create a badge"""
        badge = self._get_badge()

        eq_(slugify(badge.title), badge.slug)
        ok_(badge.created is not None)
        ok_(badge.modified is not None)
        eq_(badge.created.year, badge.modified.year)
        eq_(badge.created.month, badge.modified.month)
        eq_(badge.created.day, badge.modified.day)

    def test_unicode_slug(self):
        """Issue #124: django slugify function turns up blank slugs"""
        badge = self._get_badge()
        badge.title = u'弁護士バッジ（レプリカ）'
        badge.slug = ''
        img_data = open(BADGE_IMG_FN, 'r').read()
        badge.image.save('', ContentFile(img_data), True)
        badge.save()

        ok_(badge.slug != '')
        eq_(slugify(badge.title), badge.slug)

    def test_award_badge(self):
        """Can award a badge to a user"""
        badge = self._get_badge()
        user = self._get_user()

        ok_(not badge.is_awarded_to(user))
        badge.award_to(awardee=user, awarder=badge.creator)
        ok_(badge.is_awarded_to(user))

    def test_award_unique_duplication(self):
        """Only one award for a unique badge can be created"""
        user = self._get_user()
        b = Badge.objects.create(slug='one-and-only', title='One and Only',
                unique=True, creator=user)
        a = Award.objects.create(badge=b, user=user)

        # award_to should not trigger the exception by default
        b.award_to(awardee=user)

        try:
            b.award_to(awardee=user, raise_already_awarded=True)
            ok_(False, 'BadgeAlreadyAwardedException should have been raised')
        except BadgeAlreadyAwardedException:
            # The raise_already_awarded flag should raise the exception
            pass

        try:
            a = Award.objects.create(badge=b, user=user)
            ok_(False, 'BadgeAlreadyAwardedException should have been raised')
        except BadgeAlreadyAwardedException:
            # But, directly creating another award should trigger the exception
            pass

        eq_(1, Award.objects.filter(badge=b, user=user).count())


class BadgerOBITest(BadgerTestCase):

    def test_baked_award_image(self):
        """Award gets image baked with OBI assertion"""
        # Get the source for a sample badge image
        img_data = open(BADGE_IMG_FN, 'r').read()

        # Make a badge with a creator
        user_creator = self._get_user(username="creator")
        badge = self._get_badge(title="Badge with Creator",
                                creator=user_creator)
        badge.image.save('', ContentFile(img_data), True)

        # Get some users who can award any badge
        user_1 = self._get_user(username="superuser_1",
                                is_superuser=True)
        user_2 = self._get_user(username="superuser_2",
                                is_superuser=True)

        # Get some users who can receive badges
        user_awardee_1 = self._get_user(username="awardee_1")
        user_awardee_2 = self._get_user(username="awardee_1")

        # Try awarding the badge once with baking enabled and once without
        for enabled in (True, False):
            with patch_settings(BADGER_BAKE_AWARD_IMAGES=enabled):
                award_1 = badge.award_to(awardee=user_awardee_1)
                if not enabled:
                    ok_(not award_1.image)
                else:
                    ok_(award_1.image)
                    img = Image.open(award_1.image.file)
                    hosted_assertion_url = img.info['openbadges']
                    expected_url = '%s%s' % (
                        BASE_URL, reverse('badger.award_detail_json',
                                          args=(award_1.badge.slug,
                                                award_1.id)))
                    eq_(expected_url, hosted_assertion_url)
                award_1.delete()


class BadgerProgressTest(BadgerTestCase):

    def test_progress_badge_already_awarded(self):
        """New progress toward an awarded unique badge cannot be recorded"""
        user = self._get_user()
        b = Badge.objects.create(slug='one-and-only', title='One and Only',
                unique=True, creator=user)

        p = b.progress_for(user)
        p.update_percent(100)

        try:
            p = Progress.objects.create(badge=b, user=user)
            ok_(False, 'BadgeAlreadyAwardedException should have been raised')
        except BadgeAlreadyAwardedException:
            pass

        # None, because award deletes progress.
        eq_(0, Progress.objects.filter(badge=b, user=user).count())


class BadgerDeferredAwardTest(BadgerTestCase):

    def test_claim_by_code(self):
        """Can claim a deferred award by claim code"""
        user = self._get_user()
        awardee = self._get_user(username='winner1',
                                 email='winner@example.com')

        badge1 = self._get_badge(title="Test A", creator=user)

        ok_(not badge1.is_awarded_to(awardee))

        da = DeferredAward(badge=badge1)
        da.save()
        code = da.claim_code

        eq_(1, DeferredAward.objects.filter(claim_code=code).count())
        DeferredAward.objects.claim_by_code(awardee, code)
        eq_(0, DeferredAward.objects.filter(claim_code=code).count())

        ok_(badge1.is_awarded_to(awardee))

        # Ensure the award was marked with the claim code.
        award = Award.objects.get(claim_code=code)
        eq_(award.badge.pk, badge1.pk)

    def test_claim_by_email(self):
        """Can claim all deferred awards by email address"""
        deferred_email = 'winner@example.com'
        user = self._get_user()
        titles = ("Test A", "Test B", "Test C")
        badges = (self._get_badge(title=title, creator=user)
                  for title in titles)
        deferreds = []

        # Issue deferred awards for each of the badges.
        for badge in badges:
            result = badge.award_to(email=deferred_email, awarder=user)
            deferreds.append(result)
            ok_(hasattr(result, 'claim_code'))

        # Scour the mail outbox for claim messages.
        if notification:
            for deferred in deferreds:
                found = False
                for msg in mail.outbox:
                    if (deferred.badge.title in msg.subject and
                            deferred.get_claim_url() in msg.body):
                        found = True
                ok_(found, '%s should have been found in subject' %
                           deferred.badge.title)

        # Register an awardee user with the email address, but the badge should
        # not have been awarded yet.
        awardee = self._get_user(username='winner2', email=deferred_email)
        for badge in badges:
            ok_(not badge.is_awarded_to(awardee))

        # Now, claim the deferred awards, and they should all self-destruct
        eq_(3, DeferredAward.objects.filter(email=awardee.email).count())
        DeferredAward.objects.claim_by_email(awardee)
        eq_(0, DeferredAward.objects.filter(email=awardee.email).count())

        # After claiming, the awards should exist.
        for badge in badges:
            ok_(badge.is_awarded_to(awardee))

    def test_reusable_claim(self):
        """Can repeatedly claim a reusable deferred award"""
        user = self._get_user()
        awardee = self._get_user(username='winner1',
                                 email='winner@example.com')

        badge1 = self._get_badge(title="Test A", creator=user, unique=False)

        ok_(not badge1.is_awarded_to(awardee))

        da = DeferredAward(badge=badge1, reusable=True)
        da.save()
        code = da.claim_code

        for i in range(0, 5):
            eq_(1, DeferredAward.objects.filter(claim_code=code).count())
            DeferredAward.objects.claim_by_code(awardee, code)

        ok_(badge1.is_awarded_to(awardee))
        eq_(5, Award.objects.filter(badge=badge1, user=awardee).count())

    def test_disallowed_claim(self):
        """Deferred award created by someone not allowed to award a badge
        cannot be claimed"""
        user = self._get_user()
        random_guy = self._get_user(username='random_guy',
                                    is_superuser=False)
        awardee = self._get_user(username='winner1',
                                 email='winner@example.com')

        badge1 = self._get_badge(title="Test A", creator=user)

        ok_(not badge1.is_awarded_to(awardee))

        da = DeferredAward(badge=badge1, creator=random_guy)
        da.save()
        code = da.claim_code

        eq_(1, DeferredAward.objects.filter(claim_code=code).count())
        result = DeferredAward.objects.claim_by_code(awardee, code)
        eq_(0, DeferredAward.objects.filter(claim_code=code).count())

        ok_(not badge1.is_awarded_to(awardee))

    def test_granted_claim(self):
        """Reusable deferred award can be granted to someone by email"""

        # Assemble the characters involved...
        creator = self._get_user()
        random_guy = self._get_user(username='random_guy',
                                    email='random_guy@example.com',
                                    is_superuser=False)
        staff_person = self._get_user(username='staff_person',
                                      email='staff@example.com',
                                      is_staff=True)
        grantee_email = 'winner@example.com'
        grantee = self._get_user(username='winner1',
                                 email=grantee_email)

        # Create a consumable award claim
        badge1 = self._get_badge(title="Test A", creator=creator)
        original_email = 'original@example.com'
        da = DeferredAward(badge=badge1, creator=creator, email=original_email)
        claim_code = da.claim_code
        da.save()

        # Grant the deferred award, ensure the existing one is modified.
        new_da = da.grant_to(email=grantee_email, granter=staff_person)
        ok_(claim_code != new_da.claim_code)
        ok_(da.email != original_email)
        eq_(da.pk, new_da.pk)
        eq_(new_da.email, grantee_email)

        # Claim the deferred award, assert that the appropriate deferred award
        # was destroyed
        eq_(1, DeferredAward.objects.filter(pk=da.pk).count())
        eq_(1, DeferredAward.objects.filter(pk=new_da.pk).count())
        DeferredAward.objects.claim_by_email(grantee)
        eq_(0, DeferredAward.objects.filter(pk=da.pk).count())
        eq_(0, DeferredAward.objects.filter(pk=new_da.pk).count())

        # Finally, assert the award condition
        ok_(badge1.is_awarded_to(grantee))

        # Create a reusable award claim
        badge2 = self._get_badge(title="Test B", creator=creator)
        da = DeferredAward(badge=badge2, creator=creator, reusable=True)
        claim_code = da.claim_code
        da.save()

        # Grant the deferred award, ensure a new deferred award is generated.
        new_da = da.grant_to(email=grantee_email, granter=staff_person)
        ok_(claim_code != new_da.claim_code)
        ok_(da.pk != new_da.pk)
        eq_(new_da.email, grantee_email)

        # Claim the deferred award, assert that the appropriate deferred award
        # was destroyed
        eq_(1, DeferredAward.objects.filter(pk=da.pk).count())
        eq_(1, DeferredAward.objects.filter(pk=new_da.pk).count())
        DeferredAward.objects.claim_by_email(grantee)
        eq_(1, DeferredAward.objects.filter(pk=da.pk).count())
        eq_(0, DeferredAward.objects.filter(pk=new_da.pk).count())

        # Finally, assert the award condition
        ok_(badge2.is_awarded_to(grantee))

        # Create one more award claim
        badge3 = self._get_badge(title="Test C", creator=creator)
        da = DeferredAward(badge=badge3, creator=creator)
        claim_code = da.claim_code
        da.save()

        # Grant the deferred award, ensure a new deferred award is generated.
        try:
            new_da = da.grant_to(email=grantee_email, granter=random_guy)
            is_ok = False
        except Exception, e:
            ok_(type(e) is DeferredAwardGrantNotAllowedException)
            is_ok = True

        ok_(is_ok, "Permission should be required for granting")

    def test_mass_generate_claim_codes(self):
        """Claim codes can be generated in mass for a badge"""
        # Assemble the characters involved...
        creator = self._get_user()
        random_guy = self._get_user(username='random_guy',
                                    email='random_guy@example.com',
                                    is_superuser=False)
        staff_person = self._get_user(username='staff_person',
                                      email='staff@example.com',
                                      is_staff=True)

        # Create a consumable award claim
        badge1 = self._get_badge(title="Test A", creator=creator)
        eq_(0, len(badge1.claim_groups))

        # Generate a number of groups of varying size
        num_awards = (10, 20, 40, 80, 100)
        num_groups = len(num_awards)
        groups_generated = dict()
        for x in range(0, num_groups):
            num = num_awards[x]
            cg = badge1.generate_deferred_awards(user=creator, amount=num)
            time.sleep(1.0)
            groups_generated[cg] = num
            eq_(num, DeferredAward.objects.filter(claim_group=cg).count())

        # Ensure the expected claim groups are available
        if False:
            # FIXME: Seems like the claim groups count doesn't work with
            # sqlite3 tests
            eq_(num_groups, len(badge1.claim_groups))
            for item in badge1.claim_groups:
                cg = item['claim_group']
                eq_(groups_generated[cg], item['count'])

            # Delete deferred awards found in the first claim group
            cg_1 = badge1.claim_groups[0]['claim_group']
            badge1.delete_claim_group(user=creator, claim_group=cg_1)

            # Assert that the claim group is gone, and now there's one less.
            eq_(num_groups - 1, len(badge1.claim_groups))

    def test_deferred_award_unique_duplication(self):
        """Only one deferred award for a unique badge can be created"""
        deferred_email = 'winner@example.com'
        user = self._get_user()
        b = Badge.objects.create(slug='one-and-only', title='One and Only',
                                 unique=True, creator=user)
        a = Award.objects.create(badge=b, user=user)

        b.award_to(email=deferred_email, awarder=user)

        # There should be one deferred award for the email.
        eq_(1, DeferredAward.objects.filter(email=deferred_email).count())

        # Award again. Tt should raise an exception and there still should
        # be one deferred award.
        self.assertRaises(
            BadgeAlreadyAwardedException,
            lambda: b.award_to(email=deferred_email, awarder=user))
        eq_(1, DeferredAward.objects.filter(email=deferred_email).count())

    def test_only_first_deferred_sends_email(self):
        """Only the first deferred award will trigger an email."""
        deferred_email = 'winner@example.com'
        user = self._get_user()
        b1 = Badge.objects.create(slug='one-and-only', title='One and Only',
                                  unique=True, creator=user)
        b1.award_to(email=deferred_email, awarder=user)

        # There should be one deferred award and one email in the outbox.
        eq_(1, DeferredAward.objects.filter(email=deferred_email).count())
        eq_(1, len(mail.outbox))

        # Award a second badge and there should be two deferred awards and
        # still only one email in the outbox.
        b2 = Badge.objects.create(slug='another-one', title='Another One',
                                  unique=True, creator=user)
        b2.award_to(email=deferred_email, awarder=user)
        eq_(2, DeferredAward.objects.filter(email=deferred_email).count())
        eq_(1, len(mail.outbox))


class BadgerMultiplayerBadgeTest(BadgerTestCase):

    def setUp(self):
        self.user_1 = self._get_user(username="user_1",
                email="user_1@example.com", password="user_1_pass")

        self.stranger = self._get_user(username="stranger",
                email="stranger@example.com",
                password="stranger_pass")

    def tearDown(self):
        Nomination.objects.all().delete()
        Award.objects.all().delete()
        Badge.objects.all().delete()

    def test_nominate_badge(self):
        """Can nominate a user for a badge"""
        badge = self._get_badge()
        nominator = self._get_user(username="nominator",
                email="nominator@example.com", password="nomnom1")
        nominee = self._get_user(username="nominee",
                email="nominee@example.com", password="nomnom2")

        ok_(not badge.is_nominated_for(nominee))
        nomination = badge.nominate_for(nominator=nominator, nominee=nominee)
        ok_(badge.is_nominated_for(nominee))

    def test_approve_nomination(self):
        """A nomination can be approved"""
        nomination = self._create_nomination()

        eq_(False, nomination.allows_approve_by(self.stranger))
        eq_(True, nomination.allows_approve_by(nomination.badge.creator))

        ok_(not nomination.is_approved)
        nomination.approve_by(nomination.badge.creator)
        ok_(nomination.is_approved)

    def test_autoapprove_nomination(self):
        """All nominations should be auto-approved for a badge flagged for
        auto-approval"""
        badge = self._get_badge()
        badge.nominations_autoapproved = True
        badge.save()

        nomination = self._create_nomination()
        ok_(nomination.is_approved)

    def test_accept_nomination(self):
        """A nomination can be accepted"""
        nomination = self._create_nomination()

        eq_(False, nomination.allows_accept(self.stranger))
        eq_(True, nomination.allows_accept(nomination.nominee))

        ok_(not nomination.is_accepted)
        nomination.accept(nomination.nominee)
        ok_(nomination.is_accepted)

    def test_approve_accept_nomination(self):
        """A nomination that is approved and accepted results in an award"""
        nomination = self._create_nomination()

        ok_(not nomination.badge.is_awarded_to(nomination.nominee))
        nomination.approve_by(nomination.badge.creator)
        nomination.accept(nomination.nominee)
        ok_(nomination.badge.is_awarded_to(nomination.nominee))

        ct = Award.objects.filter(nomination=nomination).count()
        eq_(1, ct, "There should be an award associated with the nomination")

    def test_reject_nomination(self):
        SAMPLE_REASON = "Just a test anyway"
        nomination = self._create_nomination()
        rejected_by = nomination.badge.creator

        eq_(False, nomination.allows_reject_by(self.stranger))
        eq_(True, nomination.allows_reject_by(nomination.badge.creator))
        eq_(True, nomination.allows_reject_by(nomination.nominee))

        nomination.reject_by(rejected_by, reason=SAMPLE_REASON)
        eq_(rejected_by, nomination.rejected_by)
        ok_(nomination.is_rejected)
        eq_(SAMPLE_REASON, nomination.rejected_reason)

        eq_(False, nomination.allows_reject_by(self.stranger))
        eq_(False, nomination.allows_reject_by(nomination.badge.creator))
        eq_(False, nomination.allows_reject_by(nomination.nominee))
        eq_(False, nomination.allows_accept(self.stranger))
        eq_(False, nomination.allows_accept(nomination.nominee))
        eq_(False, nomination.allows_approve_by(self.stranger))
        eq_(False, nomination.allows_approve_by(nomination.badge.creator))

    def test_disallowed_nomination_approval(self):
        """By default, only badge creator should be allowed to approve a
        nomination."""

        nomination = self._create_nomination()
        other_user = self._get_user(username="other")

        try:
            nomination = nomination.approve_by(other_user)
            ok_(False, "Nomination should not have succeeded")
        except NominationApproveNotAllowedException:
            ok_(True)

    def test_disallowed_nomination_accept(self):
        """By default, only nominee should be allowed to accept a
        nomination."""

        nomination = self._create_nomination()
        other_user = self._get_user(username="other")

        try:
            nomination = nomination.accept(other_user)
            ok_(False, "Nomination should not have succeeded")
        except NominationAcceptNotAllowedException:
            ok_(True)

    def _get_user(self, username="tester", email="tester@example.com",
            password="trustno1"):
        (user, created) = User.objects.get_or_create(username=username,
                defaults=dict(email=email))
        if created:
            user.set_password(password)
            user.save()
        return user

    def test_nomination_badge_already_awarded(self):
        """New nomination for an awarded unique badge cannot be created"""
        user = self._get_user()
        b = Badge.objects.create(slug='one-and-only', title='One and Only',
                unique=True, creator=user)

        n = b.nominate_for(user)
        n.accept(user)
        n.approve_by(user)

        try:
            n = Nomination.objects.create(badge=b, nominee=user)
            ok_(False, 'BadgeAlreadyAwardedException should have been raised')
        except BadgeAlreadyAwardedException:
            pass

        # Nominations stick around after award.
        eq_(1, Nomination.objects.filter(badge=b, nominee=user).count())

    def _get_badge(self, title="Test Badge",
            description="This is a test badge", creator=None):
        creator = creator or self.user_1
        (badge, created) = Badge.objects.get_or_create(title=title,
                defaults=dict(description=description, creator=creator))
        return badge

    def _create_nomination(self, badge=None, nominator=None, nominee=None):
        badge = badge or self._get_badge()
        nominator = nominator or self._get_user(username="nominator",
                email="nominator@example.com", password="nomnom1")
        nominee = nominee or self._get_user(username="nominee",
                email="nominee@example.com", password="nomnom2")
        nomination = badge.nominate_for(nominator=nominator, nominee=nominee)
        return nomination

########NEW FILE########
__FILENAME__ = test_views
import logging
import hashlib

from django.conf import settings

from django.http import HttpRequest
from django.test.client import Client

from django.utils import simplejson
from django.utils.translation import get_language

from django.contrib.auth.models import User

from pyquery import PyQuery as pq

from nose.tools import assert_equal, with_setup, assert_false, eq_, ok_
from nose.plugins.attrib import attr

from django.template.defaultfilters import slugify

try:
    from funfactory.urlresolvers import (get_url_prefix, Prefixer, reverse,
                                         set_url_prefix)
    from tower import activate
except ImportError:
    from django.core.urlresolvers import reverse
    get_url_prefix = None

from . import BadgerTestCase

from badger.models import (Badge, Award, Nomination, Progress, DeferredAward,
        NominationApproveNotAllowedException,
        NominationAcceptNotAllowedException,
        BadgeAwardNotAllowedException)
from badger.utils import get_badge, award_badge


class BadgerViewsTest(BadgerTestCase):

    def setUp(self):
        self.testuser = self._get_user()
        self.client = Client()
        Award.objects.all().delete()

    def tearDown(self):
        Award.objects.all().delete()
        Badge.objects.all().delete()

    @attr('json')
    def test_badge_detail(self):
        """Can view badge detail"""
        user = self._get_user()
        badge = Badge(creator=user, title="Test II",
                      description="Another test")
        badge.save()

        r = self.client.get(reverse('badger.views.detail',
            args=(badge.slug,)), follow=True)
        doc = pq(r.content)

        eq_('badge_detail', doc.find('body').attr('id'))
        eq_(1, doc.find('.badge .title:contains("%s")' % badge.title).length)
        eq_(badge.description, doc.find('.badge .description').text())

        # Now, take a look at the JSON format
        url = reverse('badger.detail_json', args=(badge.slug, ))
        r = self.client.get(url, follow=True)

        data = simplejson.loads(r.content)
        eq_(badge.title, data['name'])
        eq_(badge.description, data['description'])
        eq_('http://testserver%s' % badge.get_absolute_url(), 
            data['criteria'])

    @attr('json')
    def test_award_detail(self):
        """Can view award detail"""
        user = self._get_user()
        user2 = self._get_user(username='tester2')

        b1, created = Badge.objects.get_or_create(creator=user,
                title="Code Badge #1", description="Some description")
        award = b1.award_to(user2)

        url = reverse('badger.views.award_detail', args=(b1.slug, award.pk,))
        r = self.client.get(url, follow=True)
        doc = pq(r.content)

        eq_('award_detail', doc.find('body').attr('id'))
        eq_(1, doc.find('.award .awarded_to .username:contains("%s")' % user2.username).length)
        eq_(1, doc.find('.badge .title:contains("%s")' % b1.title).length)

        # Now, take a look at the JSON format
        url = reverse('badger.award_detail_json', args=(b1.slug, award.pk,))
        r = self.client.get(url, follow=True)

        data = simplejson.loads(r.content)

        hash_salt = (hashlib.md5('%s-%s' % (award.badge.pk, award.pk))
                            .hexdigest())
        recipient_text = '%s%s' % (award.user.email, hash_salt)
        recipient_hash = ('sha256$%s' % hashlib.sha256(recipient_text)
                                               .hexdigest())

        eq_(recipient_hash, data['recipient'])
        eq_('http://testserver%s' % award.get_absolute_url(), 
            data['evidence'])
        eq_(award.badge.title, data['badge']['name'])
        eq_(award.badge.description, data['badge']['description'])
        eq_('http://testserver%s' % award.badge.get_absolute_url(), 
            data['badge']['criteria'])

    def test_awards_by_user(self):
        """Can view awards by user"""
        user = self._get_user()
        user2 = self._get_user(username='tester2')

        b1, created = Badge.objects.get_or_create(creator=user, title="Code Badge #1")
        b2, created = Badge.objects.get_or_create(creator=user, title="Code Badge #2")
        b3, created = Badge.objects.get_or_create(creator=user, title="Code Badge #3")

        b1.award_to(user2)
        award_badge(b2.slug, user2)
        Award.objects.create(badge=b3, user=user2)

        url = reverse('badger.views.awards_by_user', args=(user2.username,))
        r = self.client.get(url, follow=True)
        doc = pq(r.content)

        eq_('badge_awards_by_user', doc.find('body').attr('id'))
        eq_(3, doc.find('.badge').length)
        for b in (b1, b2, b3):
            eq_(1, doc.find('.badge .title:contains("%s")' % b.title).length)

    def test_awards_by_badge(self):
        """Can view awards by badge"""
        user = self._get_user()
        b1 = Badge.objects.create(creator=user, title="Code Badge #1")

        u1 = self._get_user(username='tester1')
        u2 = self._get_user(username='tester2')
        u3 = self._get_user(username='tester3')

        for u in (u1, u2, u3):
            b1.award_to(u)

        url = reverse('badger.views.awards_by_badge', args=(b1.slug,))
        r = self.client.get(url, follow=True)
        doc = pq(r.content)

        eq_(3, doc.find('.award').length)
        for u in (u1, u2, u3):
            eq_(1, doc.find('.award .user:contains("%s")' % u.username)
                      .length)

    def test_award_detail_includes_nomination(self):
        """Nomination should be included in award detail"""
        creator = self._get_user(username="creator", email="creator@example.com")
        awardee = self._get_user(username="awardee", email="awardee@example.com")
        nominator = self._get_user(username="nominator", email="nominator@example.com")

        b1 = Badge.objects.create(creator=creator, title="Badge to awarded")

        ok_(not b1.is_awarded_to(awardee))

        nomination = b1.nominate_for(nominator=nominator, nominee=awardee)
        nomination.approve_by(creator)
        nomination.accept(awardee)

        ok_(b1.is_awarded_to(awardee))

        award = Award.objects.get(badge=b1, user=awardee)

        r = self.client.get(award.get_absolute_url(), follow=True)
        eq_(200, r.status_code)

        doc = pq(r.content)

        nomination_el = doc.find('.award .nominated_by .username')
        eq_(nomination_el.length, 1)
        eq_(nomination_el.text(), str(nominator))

        approved_el = doc.find('.award .nomination_approved_by .username')
        eq_(approved_el.length, 1)
        eq_(approved_el.text(), str(creator))

    def test_award_detail_includes_nomination_autoapproved(self):
        """Auto-approved nomination should be indicated in award detail"""
        creator = self._get_user(username="creator", email="creator@example.com")
        awardee = self._get_user(username="awardee", email="awardee@example.com")
        nominator = self._get_user(username="nominator", email="nominator@example.com")

        b2 = Badge.objects.create(creator=creator, title="Badge to awarded 2")
        b2.nominations_autoapproved = True
        b2.save()

        ok_(not b2.is_awarded_to(awardee))

        nomination = b2.nominate_for(nominator=nominator, nominee=awardee)
        nomination.accept(awardee)

        ok_(b2.is_awarded_to(awardee))

        award = Award.objects.get(badge=b2, user=awardee)

        r = self.client.get(award.get_absolute_url(), follow=True)
        eq_(200, r.status_code)

        doc = pq(r.content)

        approved_el = doc.find('.award .nomination_approved_by .autoapproved')
        eq_(approved_el.length, 1)

    def test_issue_award(self):
        """Badge creator can issue award to another user"""
        SAMPLE_DESCRIPTION = u'This is a sample description'
        
        user1 = self._get_user(username="creator", email="creator@example.com")
        user2 = self._get_user(username="awardee", email="awardee@example.com")

        b1 = Badge.objects.create(creator=user1, title="Badge to awarded")

        url = reverse('badger.views.award_badge', args=(b1.slug,))

        # Non-creator should be denied attempt to award badge
        self.client.login(username="awardee", password="trustno1")
        r = self.client.get(url, follow=True)
        eq_(403, r.status_code)

        # But, the creator should be allowed
        self.client.login(username="creator", password="trustno1")
        r = self.client.get(url, follow=True)
        eq_(200, r.status_code)

        doc = pq(r.content)
        form = doc('form#award_badge')
        eq_(1, form.length)
        eq_(1, form.find('*[name=emails]').length)
        eq_(1, form.find('*[name=description]').length)
        eq_(1, form.find('input.submit,button.submit').length)

        r = self.client.post(url, dict(
            emails=user2.email,
            description=SAMPLE_DESCRIPTION
        ), follow=False)

        ok_('award' in r['Location'])

        ok_(b1.is_awarded_to(user2))

        award = Award.objects.filter(user=user2, badge=b1)[0]
        eq_(SAMPLE_DESCRIPTION, award.description)
        
        r = self.client.get(award.get_absolute_url(), follow=True)
        eq_(200, r.status_code)

        doc = pq(r.content)
        eq_(SAMPLE_DESCRIPTION, doc.find('.award .description').text())

    def test_issue_multiple_awards(self):
        """Multiple emails can be submitted at once to issue awards"""
        # Build creator user and badge
        creator = self._get_user(username="creator", email="creator@example.com")
        b1 = Badge.objects.create(creator=creator, title="Badge to defer")

        # Build future awardees
        user1 = self._get_user(username="user1", email="user1@example.com")
        user2 = self._get_user(username="user2", email="user2@example.com")
        user3 = self._get_user(username="user3", email="user3@example.com")
        user4_email = 'user4@example.com'

        # Login as the badge creator, prepare to award...
        self.client.login(username="creator", password="trustno1")
        url = reverse('badger.views.award_badge', args=(b1.slug,))
        r = self.client.get(url, follow=True)
        eq_(200, r.status_code)

        # Make sure the expected parts appear in the form.
        doc = pq(r.content)
        form = doc('form#award_badge')
        eq_(1, form.length)
        eq_(1, form.find('*[name=emails]').length)
        eq_(1, form.find('input.submit,button.submit').length)

        # Post a list of emails with a variety of separators.
        r = self.client.post(url, dict(
            emails=("%s,%s\n%s %s" %
                    (user1.email, user2.email, user3.email, user4_email)),
        ), follow=False)

        # Ensure that the known users received awards and the unknown user got
        # a deferred award.
        ok_(b1.is_awarded_to(user1))
        ok_(b1.is_awarded_to(user2))
        ok_(b1.is_awarded_to(user3))
        eq_(1, DeferredAward.objects.filter(email=user4_email).count())

    def test_deferred_award_claim_on_login(self):
        """Ensure that a deferred award gets claimed on login."""
        deferred_email = "awardee@example.com"
        user1 = self._get_user(username="creator", email="creator@example.com")
        b1 = Badge.objects.create(creator=user1, title="Badge to defer")
        url = reverse('badger.views.award_badge', args=(b1.slug,))

        self.client.login(username="creator", password="trustno1")
        r = self.client.get(url, follow=True)
        eq_(200, r.status_code)

        doc = pq(r.content)
        form = doc('form#award_badge')
        eq_(1, form.length)
        eq_(1, form.find('*[name=emails]').length)
        eq_(1, form.find('input.submit,button.submit').length)

        r = self.client.post(url, dict(
            emails=deferred_email,
        ), follow=False)

        ok_('award' not in r['Location'])

        user2 = self._get_user(username="awardee", email=deferred_email)
        self.client.login(username="awardee", password="trustno1")
        r = self.client.get(reverse('badger.views.detail',
            args=(b1.slug,)), follow=True)
        ok_(b1.is_awarded_to(user2))

    def test_deferred_award_immediate_claim(self):
        """Ensure that a deferred award can be immediately claimed rather than
        viewing detail"""
        deferred_email = "awardee@example.com"
        user1 = self._get_user(username="creator", email="creator@example.com")
        b1 = Badge.objects.create(creator=user1, title="Badge to defer")
        
        da = DeferredAward(badge=b1, creator=user1)
        da.save()
        url = da.get_claim_url()

        # Just viewing the claim URL shouldn't require login.
        r = self.client.get(url, follow=False)
        eq_(200, r.status_code)

        # But, attempting to claim the award should require login
        r = self.client.post(reverse('badger.views.claim_deferred_award'), dict(
            code=da.claim_code,
        ), follow=False)
        eq_(302, r.status_code)
        ok_('login' in r['Location'])

        # So, try logging in and fetch the immediate-claim URL
        user2 = self._get_user(username="awardee", email=deferred_email)
        self.client.login(username="awardee", password="trustno1")
        r = self.client.post(reverse('badger.views.claim_deferred_award'), dict(
            code=da.claim_code,
        ), follow=False)
        eq_(302, r.status_code)
        ok_('awards' in r['Location'])

        ok_(b1.is_awarded_to(user2))

    def test_claim_code_shows_awards_after_claim(self):
        """Claim code URL should lead to award detail or list after claim"""
        user1 = self._get_user(username="creator",
                               email="creator@example.com")
        user2 = self._get_user(username="awardee",
                               email="awardee@example.com")
        b1 = Badge.objects.create(creator=user1, unique=False,
                                  title="Badge for claim viewing")
        da = DeferredAward(badge=b1, creator=user1)
        da.save()

        url = da.get_claim_url()

        # Before claim, code URL leads to claim page. 
        r = self.client.get(url, follow=False)
        eq_(200, r.status_code)
        doc = pq(r.content)
        form = doc('form#claim_award')

        # After claim, code URL leads to a single award detail page.
        award = da.claim(user2)
        r = self.client.get(url, follow=False)
        eq_(302, r.status_code)
        award_url = reverse('badger.views.award_detail',
                            args=(award.badge.slug, award.pk))
        ok_(award_url in r['Location'])

    def test_reusable_deferred_award_visit(self):
        """Issue #140: Viewing a claim page for a deferred award that has been
        claimed, yet is flagged as reusable, should result in the claim page
        and not a redirect to awards"""
        user1 = self._get_user(username="creator", email="creator@example.com")
        user2 = self._get_user(username="awardee1", email="a1@example.com")
        user3 = self._get_user(username="awardee2", email="a2@example.com")

        # Create the badge, a deferred award, and claim it once already.
        b1 = Badge.objects.create(creator=user1, title="Badge to defer")
        da = DeferredAward.objects.create(badge=b1, creator=user1,
                                          reusable=True)
        da.claim(user3)

        # Visiting the claim URL should yield the claim code page.
        url = da.get_claim_url()
        self.client.login(username="awardee1", password="trustno1")
        r = self.client.get(url, follow=True)
        eq_(200, r.status_code)
        doc = pq(r.content)
        form = doc('form#claim_award')
        eq_(1, form.length)

    def test_grant_deferred_award(self):
        """Deferred award for a badge can be granted to an email address."""
        deferred_email = "awardee@example.com"
        user1 = self._get_user(username="creator", email="creator@example.com")
        b1 = Badge.objects.create(creator=user1, title="Badge to defer")
        
        da = DeferredAward(badge=b1, creator=user1, email='foobar@example.com')
        da.save()
        url = da.get_claim_url()

        self.client.login(username="creator", password="trustno1")
        r = self.client.get(url, follow=True)
        eq_(200, r.status_code)

        doc = pq(r.content)
        form = doc('form#grant_award')
        eq_(1, form.length)
        eq_(1, form.find('*[name=email]').length)
        eq_(1, form.find('input.submit,button.submit').length)

        r = self.client.post(url, dict(
            is_grant=1, email=deferred_email,
        ), follow=False)

        user2 = self._get_user(username="awardee", email=deferred_email)
        self.client.login(username="awardee", password="trustno1")
        r = self.client.get(reverse('badger.views.detail',
            args=(b1.slug,)), follow=True)
        ok_(b1.is_awarded_to(user2))

    def test_create(self):
        """Can create badge with form"""
        # Login should be required
        r = self.client.get(reverse('badger.views.create'))
        eq_(302, r.status_code)
        ok_('/accounts/login' in r['Location'])

        # Should be fine after login
        settings.BADGER_ALLOW_ADD_BY_ANYONE = True
        self.client.login(username="tester", password="trustno1")
        r = self.client.get(reverse('badger.views.create'))
        eq_(200, r.status_code)

        # Make a chick check for expected form elements
        doc = pq(r.content)

        form = doc('form#create_badge')
        eq_(1, form.length)

        eq_(1, form.find('input[name=title]').length)
        eq_(1, form.find('textarea[name=description]').length)
        # For styling purposes, we'll allow either an input or button element
        eq_(1, form.find('input.submit,button.submit').length)

        r = self.client.post(reverse('badger.views.create'), dict(
        ), follow=True)
        doc = pq(r.content)
        eq_(1, doc.find('form .error > input[name=title]').length)

        badge_title = "Test badge #1"
        badge_desc = "This is a test badge"

        r = self.client.post(reverse('badger.views.create'), dict(
            title=badge_title,
            description=badge_desc,
        ), follow=True)
        doc = pq(r.content)

        eq_('badge_detail', doc.find('body').attr('id'))
        ok_(badge_title in doc.find('.badge .title').text())
        eq_(badge_desc, doc.find('.badge .description').text())

        slug = doc.find('.badge').attr('data-slug')

        badge = Badge.objects.get(slug=slug)
        eq_(badge_title, badge.title)
        eq_(badge_desc, badge.description)

    def test_edit(self):
        """Can edit badge detail"""
        user = self._get_user()
        badge = Badge(creator=user, title="Test II",
                      description="Another test")
        badge.save()

        self.client.login(username="tester", password="trustno1")

        r = self.client.get(reverse('badger.views.detail',
            args=(badge.slug,)), follow=True)
        doc = pq(r.content)

        eq_('badge_detail', doc.find('body').attr('id'))
        edit_url = doc.find('a.edit_badge').attr('href')
        ok_(edit_url is not None)

        r = self.client.get(edit_url)
        doc = pq(r.content)
        eq_('badge_edit', doc.find('body').attr('id'))

        badge_title = "Edited title"
        badge_desc = "Edited description"

        r = self.client.post(edit_url, dict(
            title=badge_title,
            description=badge_desc,
        ), follow=True)
        doc = pq(r.content)

        eq_('badge_detail', doc.find('body').attr('id'))
        ok_(badge_title in doc.find('.badge .title').text())
        eq_(badge_desc, doc.find('.badge .description').text())

        slug = doc.find('.badge').attr('data-slug')

        badge = Badge.objects.get(slug=slug)
        eq_(badge_title, badge.title)
        eq_(badge_desc, badge.description)

    def test_edit_preserves_creator(self):
        """Edit preserves the original creator of the badge (bugfix)"""
        orig_user = self._get_user(username='orig_user')
        badge = Badge(creator=orig_user, title="Test 3",
                      description="Another test")
        badge.save()

        edit_user = self._get_user(username='edit_user')
        edit_user.is_superuser = True
        edit_user.save()

        self.client.login(username="edit_user", password="trustno1")
        edit_url = reverse('badger.views.edit',
                args=(badge.slug,))
        r = self.client.post(edit_url, dict(
            title='New Title',
        ), follow=True)
        doc = pq(r.content)

        # The badge's creator should not have changed to the editing user.
        badge_after = Badge.objects.get(pk=badge.pk)
        ok_(badge_after.creator.pk != edit_user.pk)

    def test_delete(self):
        """Can delete badge"""
        user = self._get_user()
        badge = Badge(creator=user, title="Test III",
                      description="Another test")
        badge.save()
        slug = badge.slug

        badge.award_to(user)

        self.client.login(username="tester", password="trustno1")

        r = self.client.get(reverse('badger.views.detail',
            args=(badge.slug,)), follow=True)
        doc = pq(r.content)

        eq_('badge_detail', doc.find('body').attr('id'))
        delete_url = doc.find('a.delete_badge').attr('href')
        ok_(delete_url is not None)

        r = self.client.get(delete_url)
        doc = pq(r.content)
        eq_('badge_delete', doc.find('body').attr('id'))
        eq_("1", doc.find('.awards_count').text())

        r = self.client.post(delete_url, {}, follow=True)
        doc = pq(r.content)

        try:
            badge = Badge.objects.get(slug=slug)
            ok_(False)
        except Badge.DoesNotExist:
            ok_(True)

    def test_delete_award(self):
        """Can delete award"""
        user = self._get_user()
        badge = Badge(creator=user, title="Test III",
                      description="Another test")
        badge.save()

        award = badge.award_to(user)

        self.client.login(username="tester", password="trustno1")

        r = self.client.get(reverse('badger.views.award_detail',
            args=(badge.slug, award.id)), follow=True)
        doc = pq(r.content)

        eq_('award_detail', doc.find('body').attr('id'))
        delete_url = doc.find('a.delete_award').attr('href')
        ok_(delete_url is not None)

        r = self.client.post(delete_url, {}, follow=True)

        try:
            award = Award.objects.get(pk=award.pk)
            ok_(False)
        except Award.DoesNotExist:
            ok_(True)

    def _get_user(self, username="tester", email="tester@example.com",
            password="trustno1"):
        (user, created) = User.objects.get_or_create(username=username,
                defaults=dict(email=email))
        if created:
            user.set_password(password)
            user.save()
        return user

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.conf import settings

from .feeds import (AwardsRecentFeed, AwardsByUserFeed, AwardsByBadgeFeed,
                    BadgesRecentFeed, BadgesByUserFeed)
from . import views


urlpatterns = patterns('badger.views',
    url(r'^$', 'badges_list', name='badger.badges_list'),
    url(r'^staff_tools$', 'staff_tools',
        name='badger.staff_tools'),
    url(r'^tag/(?P<tag_name>.+)/?$', 'badges_list',
        name='badger.badges_list'),
    url(r'^awards/?', 'awards_list',
        name='badger.awards_list'),
    url(r'^badge/(?P<slug>[^/]+)/awards/?$', 'awards_list',
        name='badger.awards_list_for_badge'),
    url(r'^badge/(?P<slug>[^/]+)/awards/(?P<id>\d+)\.json$', 'award_detail',
        kwargs=dict(format="json"),
        name='badger.award_detail_json'),
    url(r'^badge/(?P<slug>[^/]+)/awards/(?P<id>\d+)/?$', 'award_detail',
        name='badger.award_detail'),
    url(r'^badge/(?P<slug>[^/]+)/awards/(?P<id>\d+)/delete$', 'award_delete',
        name='badger.award_delete'),
    url(r'^badge/(?P<slug>[^/]+)/claims/(?P<claim_group>.+)\.pdf$', 'claims_list',
        kwargs=dict(format='pdf'),
        name='badger.claims_list_pdf'),
    url(r'^badge/(?P<slug>[^/]+)/claims/(?P<claim_group>[^/]+)/?$', 'claims_list',
        name='badger.claims_list'),
    url(r'^claim/(?P<claim_code>[^/]+)/?$', 'claim_deferred_award',
        name='badger.claim_deferred_award'),
    url(r'^claim/?$', 'claim_deferred_award',
        name='badger.claim_deferred_award_form'),
    url(r'^badge/(?P<slug>[^/]+)/award', 'award_badge',
        name='badger.award_badge'),
    url(r'^badge/(?P<slug>.+)\.json$', 'detail',
        kwargs=dict(format="json"),
        name='badger.detail_json'),
    url(r'^badge/(?P<slug>[^/]+)/?$', 'detail',
        name='badger.detail'),
    url(r'^badge/(?P<slug>[^/]+)/awards/?$', 'awards_by_badge',
        name='badger.awards_by_badge'),
    url(r'^users/(?P<username>[^/]+)/awards/?$', 'awards_by_user',
        name='badger.awards_by_user'),

    url(r'^create$', 'create',
        name='badger.create_badge'),
    url(r'^badge/(?P<slug>[^/]+)/nominate$', 'nominate_for',
        name='badger.nominate_for'),
    url(r'^badge/(?P<slug>[^/]+)/edit$', 'edit',
        name='badger.badge_edit'),
    url(r'^badge/(?P<slug>[^/]+)/delete$', 'delete',
        name='badger.badge_delete'),
    url(r'^badge/(?P<slug>[^/]+)/nominations/(?P<id>\d+)/?$', 'nomination_detail',
        name='badger.nomination_detail'),
    url(r'^users/(?P<username>[^/]+)/badges/?$', 'badges_by_user',
        name='badger.badges_by_user'),

    url(r'^feeds/(?P<format>[^/]+)/badges/?$', BadgesRecentFeed(),
        name="badger.feeds.badges_recent"),
    url(r'^feeds/(?P<format>[^/]+)/users/(?P<username>[^/]+)/badges/?$',
        BadgesByUserFeed(),
        name="badger.feeds.badges_by_user"),

    url(r'^feeds/(?P<format>[^/]+)/awards/?$',
        AwardsRecentFeed(), name="badger.feeds.awards_recent"),
    url(r'^feeds/(?P<format>[^/]+)/badge/(?P<slug>[^/]+)/awards/?$',
        AwardsByBadgeFeed(), name="badger.feeds.awards_by_badge"),
    url(r'^feeds/(?P<format>[^/]+)/users/(?P<username>[^/]+)/awards/?$',
        AwardsByUserFeed(), name="badger.feeds.awards_by_user"),
)

########NEW FILE########
__FILENAME__ = urls_simple
"""
This is a simplified URLs list that omits any of the multiplayer features,
assuming that all badges will be managed from the admin interface, and most
badges will be awarded in badges.py
"""
from django.conf.urls import patterns, include, url

from django.conf import settings

from .feeds import (AwardsRecentFeed, AwardsByUserFeed, AwardsByBadgeFeed,
                    BadgesRecentFeed, BadgesByUserFeed)
from . import views


urlpatterns = patterns('badger.views',
    url(r'^$', 'badges_list', name='badger.badges_list'),
    url(r'^tag/(?P<tag_name>.+)/?$', 'badges_list',
        name='badger.badges_list'),
    url(r'^awards/?', 'awards_list',
        name='badger.awards_list'),
    url(r'^badge/(?P<slug>[^/]+)/awards/?$', 'awards_list',
        name='badger.awards_list_for_badge'),
    url(r'^badge/(?P<slug>[^/]+)/awards/(?P<id>[^\.]+)\.json$', 'award_detail',
        kwargs=dict(format="json"),
        name='badger.award_detail_json'),
    url(r'^badge/(?P<slug>[^/]+)/awards/(?P<id>[^/]+)/?$', 'award_detail',
        name='badger.award_detail'),
    url(r'^badge/(?P<slug>[^/]+)/awards/(?P<id>[^/]+)/delete$', 'award_delete',
        name='badger.award_delete'),
    url(r'^badge/(?P<slug>[^\.]+)\.json$', 'detail',
        kwargs=dict(format="json"),
        name='badger.detail_json'),
    url(r'^badge/(?P<slug>[^/]+)/?$', 'detail',
        name='badger.detail'),
    url(r'^badge/(?P<slug>[^/]+)/awards/?$', 'awards_by_badge',
        name='badger.awards_by_badge'),
    url(r'^users/(?P<username>[^/]+)/awards/?$', 'awards_by_user',
        name='badger.awards_by_user'),
    url(r'^feeds/(?P<format>[^/]+)/badges/?$', BadgesRecentFeed(),
        name="badger.feeds.badges_recent"),
    url(r'^feeds/(?P<format>[^/]+)/awards/?$',
        AwardsRecentFeed(), name="badger.feeds.awards_recent"),
    url(r'^feeds/(?P<format>[^/]+)/badge/(?P<slug>[^/]+)/awards/?$',
        AwardsByBadgeFeed(), name="badger.feeds.awards_by_badge"),
    url(r'^feeds/(?P<format>[^/]+)/users/(?P<username>[^/]+)/awards/?$',
        AwardsByUserFeed(), name="badger.feeds.awards_by_user"),
)

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings
from django.db.models import signals

import badger
from badger.models import Badge, Award, Progress


def update_badges(badge_data, overwrite=False):
    """Creates or updates list of badges

    :arg badge_data: list of dicts. keys in the dict correspond to the
        Badge model class. Also, you can pass in ``prerequisites``.
    :arg overwrite: whether or not to overwrite the existing badge

    :returns: list of Badge instances---one per dict passed in

    """
    badges = []
    for data in badge_data:
        badges.append(update_badge(data, overwrite=overwrite))
    return badges


def update_badge(data_in, overwrite=False):
    # Clone the data, because we might delete fields
    data = dict(**data_in)

    # If there are prerequisites, ensure they're real badges and remove
    # from the set of data fields.
    if 'prerequisites' not in data:
        prerequisites = None
    else:
        prerequisites = [get_badge(n)
            for n in data.get('prerequisites', [])]
        del data['prerequisites']

    badge, created = Badge.objects.get_or_create(title=data['title'],
                                                 defaults=data)

    # If overwriting, and not just created, then save with current fields.
    if overwrite and not created:
        for k, v in data.items():
            setattr(badge, k, v)
        badge.save()

    # Set prerequisites if overwriting, or badge is newly created.
    if (overwrite or created) and prerequisites:
        badge.prerequisites.clear()
        badge.prerequisites.add(*prerequisites)

    return badge


def get_badge(slug_or_badge):
    """Return badge specified by slug or by instance

    :arg slug_or_badge: slug or Badge instance

    :returns: Badge instance

    """
    if isinstance(slug_or_badge, Badge):
        b = slug_or_badge
    else:
        b = Badge.objects.get(slug=slug_or_badge)
    return b


def award_badge(slug_or_badge, awardee, awarder=None):
    """Award a badge to an awardee, with optional awarder

    :arg slug_or_badge: slug or Badge instance to award
    :arg awardee: User this Badge is awarded to
    :arg awarder: User who awarded this Badge

    :returns: Award instance

    :raise BadgeAwardNotAllowedexception: ?

    :raise BadgeAlreadyAwardedException: if the badge is unique and
        has already been awarded to this user

    """
    b = get_badge(slug_or_badge)
    return b.award_to(awardee=awardee, awarder=awarder)


def get_progress(slug_or_badge, user):
    """Get a progress record for a badge and awardee

    :arg slug_or_badge: slug or Badge instance
    :arg user: User to check progress for

    :returns: Progress instance

    """
    b = get_badge(slug_or_badge)
    return b.progress_for(user)

########NEW FILE########
__FILENAME__ = validate_jsonp
# -*- coding: utf-8 -*-
# see also: http://github.com/tav/scripts/raw/master/validate_jsonp.py
# Placed into the Public Domain by tav <tav@espians.com>

"""Validate Javascript Identifiers for use as JSON-P callback parameters."""

import re

from unicodedata import category

# ------------------------------------------------------------------------------
# javascript identifier unicode categories and "exceptional" chars
# ------------------------------------------------------------------------------

valid_jsid_categories_start = frozenset([
    'Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl'
    ])

valid_jsid_categories = frozenset([
    'Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl', 'Mn', 'Mc', 'Nd', 'Pc'
    ])

valid_jsid_chars = ('$', '_')

# ------------------------------------------------------------------------------
# regex to find array[index] patterns
# ------------------------------------------------------------------------------

array_index_regex = re.compile(r'\[[0-9]+\]$')

has_valid_array_index = array_index_regex.search
replace_array_index = array_index_regex.sub

# ------------------------------------------------------------------------------
# javascript reserved words -- including keywords and null/boolean literals
# ------------------------------------------------------------------------------

is_reserved_js_word = frozenset([

    'abstract', 'boolean', 'break', 'byte', 'case', 'catch', 'char', 'class',
    'const', 'continue', 'debugger', 'default', 'delete', 'do', 'double',
    'else', 'enum', 'export', 'extends', 'false', 'final', 'finally', 'float',
    'for', 'function', 'goto', 'if', 'implements', 'import', 'in', 'instanceof',
    'int', 'interface', 'long', 'native', 'new', 'null', 'package', 'private',
    'protected', 'public', 'return', 'short', 'static', 'super', 'switch',
    'synchronized', 'this', 'throw', 'throws', 'transient', 'true', 'try',
    'typeof', 'var', 'void', 'volatile', 'while', 'with',

    # potentially reserved in a future version of the ES5 standard
    # 'let', 'yield'

    ]).__contains__

# ------------------------------------------------------------------------------
# the core validation functions
# ------------------------------------------------------------------------------


def is_valid_javascript_identifier(identifier, escape=r'\u', ucd_cat=category):
    """Return whether the given ``id`` is a valid Javascript identifier."""

    if not identifier:
        return False

    if not isinstance(identifier, unicode):
        try:
            identifier = unicode(identifier, 'utf-8')
        except UnicodeDecodeError:
            return False

    if escape in identifier:

        new = []; add_char = new.append
        split_id = identifier.split(escape)
        add_char(split_id.pop(0))

        for segment in split_id:
            if len(segment) < 4:
                return False
            try:
                add_char(unichr(int('0x' + segment[:4], 16)))
            except Exception:
                return False
            add_char(segment[4:])

        identifier = u''.join(new)

    if is_reserved_js_word(identifier):
        return False

    first_char = identifier[0]

    if not ((first_char in valid_jsid_chars) or
            (ucd_cat(first_char) in valid_jsid_categories_start)):
        return False

    for char in identifier[1:]:
        if not ((char in valid_jsid_chars) or
                (ucd_cat(char) in valid_jsid_categories)):
            return False

    return True


def is_valid_jsonp_callback_value(value):
    """Return whether the given ``value`` can be used as a JSON-P callback."""

    for identifier in value.split(u'.'):
        while '[' in identifier:
            if not has_valid_array_index(identifier):
                return False
            identifier = replace_array_index(u'', identifier)
        if not is_valid_javascript_identifier(identifier):
            return False

    return True

# ------------------------------------------------------------------------------
# test
# ------------------------------------------------------------------------------


def test():
    """
    The function ``is_valid_javascript_identifier`` validates a given identifier
    according to the latest draft of the ECMAScript 5 Specification:

      >>> is_valid_javascript_identifier('hello')
      True

      >>> is_valid_javascript_identifier('alert()')
      False

      >>> is_valid_javascript_identifier('a-b')
      False

      >>> is_valid_javascript_identifier('23foo')
      False

      >>> is_valid_javascript_identifier('foo23')
      True

      >>> is_valid_javascript_identifier('$210')
      True

      >>> is_valid_javascript_identifier(u'Stra\u00dfe')
      True

      >>> is_valid_javascript_identifier(r'\u0062') # u'b'
      True

      >>> is_valid_javascript_identifier(r'\u62')
      False

      >>> is_valid_javascript_identifier(r'\u0020')
      False

      >>> is_valid_javascript_identifier('_bar')
      True

      >>> is_valid_javascript_identifier('some_var')
      True

      >>> is_valid_javascript_identifier('$')
      True

    But ``is_valid_jsonp_callback_value`` is the function you want to use for
    validating JSON-P callback parameter values:

      >>> is_valid_jsonp_callback_value('somevar')
      True

      >>> is_valid_jsonp_callback_value('function')
      False

      >>> is_valid_jsonp_callback_value(' somevar')
      False

    It supports the possibility of '.' being present in the callback name, e.g.

      >>> is_valid_jsonp_callback_value('$.ajaxHandler')
      True

      >>> is_valid_jsonp_callback_value('$.23')
      False

    As well as the pattern of providing an array index lookup, e.g.

      >>> is_valid_jsonp_callback_value('array_of_functions[42]')
      True

      >>> is_valid_jsonp_callback_value('array_of_functions[42][1]')
      True

      >>> is_valid_jsonp_callback_value('$.ajaxHandler[42][1].foo')
      True

      >>> is_valid_jsonp_callback_value('array_of_functions[42]foo[1]')
      False

      >>> is_valid_jsonp_callback_value('array_of_functions[]')
      False

      >>> is_valid_jsonp_callback_value('array_of_functions["key"]')
      False

    Enjoy!

    """

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = views
import logging
import random

from django.conf import settings

from django.http import (HttpResponseRedirect, HttpResponse,
        HttpResponseForbidden, HttpResponseNotFound, Http404)

from django.utils import simplejson

from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.template.defaultfilters import slugify

try:
    from funfactory.urlresolvers import (get_url_prefix, Prefixer, reverse,
                                         set_url_prefix)
    from tower import activate
except ImportError:
    from django.core.urlresolvers import reverse

try:
    from tower import ugettext_lazy as _
except ImportError:
    from django.utils.translation import ugettext_lazy as _

from django.views.generic.list import ListView
from django.views.decorators.http import (require_GET, require_POST,
                                          require_http_methods)

from django.contrib import messages

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

try:
    import taggit
    from taggit.models import Tag, TaggedItem
except ImportError:
    taggit = None

import badger
from badger import settings as bsettings
from .models import (Badge, Award, Nomination, DeferredAward,
                     Progress, BadgeAwardNotAllowedException,
                     BadgeAlreadyAwardedException,
                     NominationApproveNotAllowedException,
                     NominationAcceptNotAllowedException)
from .forms import (BadgeAwardForm, DeferredAwardGrantForm,
                    DeferredAwardMultipleGrantForm, BadgeNewForm,
                    BadgeEditForm, BadgeSubmitNominationForm)


def home(request):
    """Badger home page"""
    badge_list = Badge.objects.order_by('-modified').all()[:bsettings.MAX_RECENT]
    award_list = Award.objects.order_by('-modified').all()[:bsettings.MAX_RECENT]
    badge_tags = Badge.objects.top_tags()

    return render_to_response('%s/home.html' % bsettings.TEMPLATE_BASE, dict(
        badge_list=badge_list, award_list=award_list, badge_tags=badge_tags
    ), context_instance=RequestContext(request))


class BadgesListView(ListView):
    """Badges list page"""
    model = Badge
    template_name = '%s/badges_list.html' % bsettings.TEMPLATE_BASE
    template_object_name = 'badge'
    paginate_by = bsettings.BADGE_PAGE_SIZE

    def get_queryset(self):
        qs = Badge.objects.order_by('-modified')
        query_string = self.request.GET.get('q', None)
        tag_name = self.kwargs.get('tag_name', None)
        if query_string is not None:
            sort_order = self.request.GET.get('sort', 'created')
            qs = Badge.objects.search(query_string, sort_order)
        if taggit and tag_name:
            tag = get_object_or_404(Tag, name=tag_name)
            qs = (Badge.objects.filter(tags__in=[tag]).distinct())
        return qs

    def get_context_data(self, **kwargs):
        context = super(BadgesListView, self).get_context_data(**kwargs)
        context['award_list'] = None
        context['tag_name'] = self.kwargs.get('tag_name', None)
        context['query_string'] = kwargs.get('q', None)
        if context['query_string'] is not None:
            # TODO: Is this the most efficient query?
            context['award_list'] = (Award.objects.filter(badge__in=self.get_queryset()))
        if taggit and context['tag_name']:
            # TODO: Is this the most efficient query?
            context['award_list'] = (Award.objects.filter(badge__in=self.get_queryset()))
        return context

badges_list = BadgesListView.as_view()


@require_http_methods(['HEAD', 'GET', 'POST'])
def detail(request, slug, format="html"):
    """Badge detail view"""
    badge = get_object_or_404(Badge, slug=slug)
    if not badge.allows_detail_by(request.user):
        return HttpResponseForbidden('Detail forbidden')

    awards = (Award.objects.filter(badge=badge)
                           .order_by('-created'))[:bsettings.MAX_RECENT]

    # FIXME: This is awkward. It used to collect sections as responses to a
    # signal sent out to badger_multiplayer and hypothetical future expansions
    # to badger
    sections = dict()
    sections['award'] = dict(form=BadgeAwardForm())
    if badge.allows_nominate_for(request.user):
        sections['nominate'] = dict(form=BadgeSubmitNominationForm())

    if request.method == "POST":

        if request.POST.get('is_generate', None):
            if not badge.allows_manage_deferred_awards_by(request.user):
                return HttpResponseForbidden('Claim generate denied')
            amount = int(request.POST.get('amount', 10))
            reusable = (amount == 1)
            cg = badge.generate_deferred_awards(user=request.user,
                                                amount=amount,
                                                reusable=reusable)

        if request.POST.get('is_delete', None):
            if not badge.allows_manage_deferred_awards_by(request.user):
                return HttpResponseForbidden('Claim delete denied')
            group = request.POST.get('claim_group')
            badge.delete_claim_group(request.user, group)

        url = reverse('badger.views.detail', kwargs=dict(slug=slug))
        return HttpResponseRedirect(url)

    claim_groups = badge.claim_groups

    if format == 'json':
        data = badge.as_obi_serialization(request)
        resp = HttpResponse(simplejson.dumps(data))
        resp['Content-Type'] = 'application/json'
        return resp
    else:
        return render_to_response('%s/badge_detail.html' % bsettings.TEMPLATE_BASE, dict(
            badge=badge, award_list=awards, sections=sections,
            claim_groups=claim_groups
        ), context_instance=RequestContext(request))


@require_http_methods(['GET', 'POST'])
@login_required
def create(request):
    """Create a new badge"""
    if not Badge.objects.allows_add_by(request.user):
        return HttpResponseForbidden()

    if request.method != "POST":
        form = BadgeNewForm()
        form.initial['tags'] = request.GET.get('tags', '')
    else:
        form = BadgeNewForm(request.POST, request.FILES)
        if form.is_valid():
            new_sub = form.save(commit=False)
            new_sub.creator = request.user
            new_sub.save()
            form.save_m2m()
            return HttpResponseRedirect(reverse(
                    'badger.views.detail', args=(new_sub.slug,)))

    return render_to_response('%s/badge_create.html' % bsettings.TEMPLATE_BASE, dict(
        form=form,
    ), context_instance=RequestContext(request))


@require_http_methods(['GET', 'POST'])
@login_required
def edit(request, slug):
    """Edit an existing badge"""
    badge = get_object_or_404(Badge, slug=slug)
    if not badge.allows_edit_by(request.user):
        return HttpResponseForbidden()

    if request.method != "POST":
        form = BadgeEditForm(instance=badge)
    else:
        form = BadgeEditForm(request.POST, request.FILES, instance=badge)
        if form.is_valid():
            new_sub = form.save(commit=False)
            new_sub.save()
            form.save_m2m()
            return HttpResponseRedirect(reverse(
                    'badger.views.detail', args=(new_sub.slug,)))

    return render_to_response('%s/badge_edit.html' % bsettings.TEMPLATE_BASE, dict(
        badge=badge, form=form,
    ), context_instance=RequestContext(request))


@require_http_methods(['GET', 'POST'])
@login_required
def delete(request, slug):
    """Delete a badge"""
    badge = get_object_or_404(Badge, slug=slug)
    if not badge.allows_delete_by(request.user):
        return HttpResponseForbidden()

    awards_count = badge.award_set.count()

    if request.method == "POST":
        messages.info(request, _(u'Badge "{badgetitle}" deleted.').format(
            badgetitle=badge.title))
        badge.delete()
        return HttpResponseRedirect(reverse('badger.views.badges_list'))

    return render_to_response('%s/badge_delete.html' % bsettings.TEMPLATE_BASE, dict(
        badge=badge, awards_count=awards_count,
    ), context_instance=RequestContext(request))


@require_http_methods(['GET', 'POST'])
@login_required
def award_badge(request, slug):
    """Issue an award for a badge"""
    badge = get_object_or_404(Badge, slug=slug)
    if not badge.allows_award_to(request.user):
        return HttpResponseForbidden('Award forbidden')

    if request.method != "POST":
        form = BadgeAwardForm()
    else:
        form = BadgeAwardForm(request.POST, request.FILES)
        if form.is_valid():
            emails = form.cleaned_data['emails']
            description = form.cleaned_data['description']
            for email in emails:
                result = badge.award_to(email=email, awarder=request.user,
                                        description=description)
                if result:
                    if not hasattr(result, 'claim_code'):
                        messages.info(request, _(u'Award issued to {email}').format(
                            email=email))
                    else:
                        messages.info(request, _(
                            u'Invitation to claim award sent to {email}').format(email=email))
            return HttpResponseRedirect(reverse('badger.views.detail',
                                                args=(badge.slug,)))

    return render_to_response('%s/badge_award.html' % bsettings.TEMPLATE_BASE, dict(
        form=form, badge=badge,
    ), context_instance=RequestContext(request))


class AwardsListView(ListView):
    model = Award
    template_name = '%s/awards_list.html' % bsettings.TEMPLATE_BASE
    template_object_name = 'award'
    paginate_by = bsettings.BADGE_PAGE_SIZE

    def get_badge(self):
        if not hasattr(self, 'badge'):
            self._badge = get_object_or_404(Badge, slug=self.kwargs.get('slug', None))
        return self._badge

    def get_queryset(self):
        qs = Award.objects.order_by('-modified')
        if self.kwargs.get('slug', None) is not None:
            qs = qs.filter(badge=self.get_badge())
        return qs

    def get_context_data(self, **kwargs):
        context = super(AwardsListView, self).get_context_data(**kwargs)
        if self.kwargs.get('slug', None) is None:
            context['badge'] = None
        else:
            context['badge'] = self.get_badge()
        return context

awards_list = AwardsListView.as_view()


@require_http_methods(['HEAD', 'GET'])
def award_detail(request, slug, id, format="html"):
    """Award detail view"""
    badge = get_object_or_404(Badge, slug=slug)
    award = get_object_or_404(Award, badge=badge, pk=id)
    if not award.allows_detail_by(request.user):
        return HttpResponseForbidden('Award detail forbidden')

    if format == 'json':
        data = simplejson.dumps(award.as_obi_assertion(request))
        resp = HttpResponse(data)
        resp['Content-Type'] = 'application/json'
        return resp
    else:
        return render_to_response('%s/award_detail.html' % bsettings.TEMPLATE_BASE, dict(
            badge=badge, award=award,
        ), context_instance=RequestContext(request))


@require_http_methods(['GET', 'POST'])
@login_required
def award_delete(request, slug, id):
    """Delete an award"""
    badge = get_object_or_404(Badge, slug=slug)
    award = get_object_or_404(Award, badge=badge, pk=id)
    if not award.allows_delete_by(request.user):
        return HttpResponseForbidden('Award delete forbidden')

    if request.method == "POST":
        messages.info(request, _(u'Award for badge "{badgetitle}" deleted.').format(
            badgetitle=badge.title))
        award.delete()
        url = reverse('badger.views.detail', kwargs=dict(slug=slug))
        return HttpResponseRedirect(url)

    return render_to_response('%s/award_delete.html' % bsettings.TEMPLATE_BASE, dict(
        badge=badge, award=award
    ), context_instance=RequestContext(request))


@login_required
def _do_claim(request, deferred_award):
    """Perform claim of a deferred award"""
    if not deferred_award.allows_claim_by(request.user):
        return HttpResponseForbidden('Claim denied')
    award = deferred_award.claim(request.user)
    if award:
        url = reverse('badger.views.award_detail',
                      args=(award.badge.slug, award.id,))
        return HttpResponseRedirect(url)


def _redirect_to_claimed_awards(awards, awards_ct):
    # Has this claim code already been used for awards?
    # If so, then a GET redirects to an award detail or list
    if awards_ct == 1:
        award = awards[0]
        url = reverse('badger.views.award_detail',
                      args=(award.badge.slug, award.id,))
        return HttpResponseRedirect(url)
    elif awards_ct > 1:
        award = awards[0]
        url = reverse('badger.views.awards_list',
                      args=(award.badge.slug,))
        return HttpResponseRedirect(url)


@require_http_methods(['GET', 'POST'])
def claim_deferred_award(request, claim_code=None):
    """Deferred award detail view"""
    if not claim_code:
        claim_code = request.REQUEST.get('code', '').strip()

    # Look for any awards that match this claim code.
    awards = Award.objects.filter(claim_code=claim_code)
    awards_ct = awards.count()

    # Try fetching a DeferredAward matching the claim code. If none found, then
    # make one last effort to redirect a POST to awards. Otherwise, 404
    try:
        deferred_award = DeferredAward.objects.get(claim_code=claim_code)

        # If this is a GET and there are awards matching the claim code,
        # redirect to the awards.
        if (request.method == "GET" and awards_ct > 0 and
                not deferred_award.reusable):
            return _redirect_to_claimed_awards(awards, awards_ct)

    except DeferredAward.DoesNotExist:
        if awards_ct > 0:
            return _redirect_to_claimed_awards(awards, awards_ct)
        else:
            raise Http404('No such claim code, %s' % claim_code)

    if not deferred_award.allows_detail_by(request.user):
        return HttpResponseForbidden('Claim detail denied')

    if request.method != "POST":
        grant_form = DeferredAwardGrantForm()
    else:
        grant_form = DeferredAwardGrantForm(request.POST, request.FILES)
        if not request.POST.get('is_grant', False) is not False:
            return _do_claim(request, deferred_award)
        else:
            if not deferred_award.allows_grant_by(request.user):
                return HttpResponseForbidden('Grant denied')
            if grant_form.is_valid():
                email = request.POST.get('email', None)
                deferred_award.grant_to(email=email, granter=request.user)
                messages.info(request, _(u'Award claim granted to {email}').format(
                    email=email))
                url = reverse('badger.views.detail',
                              args=(deferred_award.badge.slug,))
                return HttpResponseRedirect(url)

    return render_to_response('%s/claim_deferred_award.html' % bsettings.TEMPLATE_BASE, dict(
        badge=deferred_award.badge, deferred_award=deferred_award,
        grant_form=grant_form
    ), context_instance=RequestContext(request))


@require_http_methods(['GET', 'POST'])
@login_required
def claims_list(request, slug, claim_group, format="html"):
    """Lists claims"""
    badge = get_object_or_404(Badge, slug=slug)
    if not badge.allows_manage_deferred_awards_by(request.user):
        return HttpResponseForbidden()

    deferred_awards = badge.get_claim_group(claim_group)

    if format == "pdf":
        from badger.printing import render_claims_to_pdf
        return render_claims_to_pdf(request, slug, claim_group,
                                    deferred_awards)

    return render_to_response('%s/claims_list.html' % bsettings.TEMPLATE_BASE, dict(
        badge=badge, claim_group=claim_group,
        deferred_awards=deferred_awards
    ), context_instance=RequestContext(request))


@require_GET
def awards_by_user(request, username):
    """Badge awards by user"""
    user = get_object_or_404(User, username=username)
    awards = Award.objects.filter(user=user)
    return render_to_response('%s/awards_by_user.html' % bsettings.TEMPLATE_BASE, dict(
        user=user, award_list=awards,
    ), context_instance=RequestContext(request))


@require_GET
def awards_by_badge(request, slug):
    """Badge awards by badge"""
    badge = get_object_or_404(Badge, slug=slug)
    awards = Award.objects.filter(badge=badge)
    return render_to_response('%s/awards_by_badge.html' % bsettings.TEMPLATE_BASE, dict(
        badge=badge, awards=awards,
    ), context_instance=RequestContext(request))


@require_http_methods(['GET', 'POST'])
@login_required
def staff_tools(request):
    """HACK: This page offers miscellaneous tools useful to event staff.
    Will go away in the future, addressed by:
    https://github.com/mozilla/django-badger/issues/35
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden()

    if request.method != "POST":
        grant_form = DeferredAwardMultipleGrantForm()
    else:
        if request.REQUEST.get('is_grant', False) is not False:
            grant_form = DeferredAwardMultipleGrantForm(request.POST, request.FILES)
            if grant_form.is_valid():
                email = grant_form.cleaned_data['email']
                codes = grant_form.cleaned_data['claim_codes']
                for claim_code in codes:
                    da = DeferredAward.objects.get(claim_code=claim_code)
                    da.grant_to(email, request.user)
                    messages.info(request, _(u'Badge "{badgetitle}" granted to {email}').format(
                        badgetitle=da.badge, email=email))
                url = reverse('badger.views.staff_tools')
                return HttpResponseRedirect(url)

    return render_to_response('%s/staff_tools.html' % bsettings.TEMPLATE_BASE, dict(
        grant_form=grant_form
    ), context_instance=RequestContext(request))


@require_GET
def badges_by_user(request, username):
    """Badges created by user"""
    user = get_object_or_404(User, username=username)
    badges = Badge.objects.filter(creator=user)
    return render_to_response('%s/badges_by_user.html' % bsettings.TEMPLATE_BASE, dict(
        user=user, badge_list=badges,
    ), context_instance=RequestContext(request))


@require_http_methods(['GET', 'POST'])
@login_required
def nomination_detail(request, slug, id, format="html"):
    """Show details on a nomination, provide for approval and acceptance"""
    badge = get_object_or_404(Badge, slug=slug)
    nomination = get_object_or_404(Nomination, badge=badge, pk=id)
    if not nomination.allows_detail_by(request.user):
        return HttpResponseForbidden()

    if request.method == "POST":
        action = request.POST.get('action', '')
        if action == 'approve_by':
            nomination.approve_by(request.user)
        elif action == 'accept':
            nomination.accept(request.user)
        elif action == 'reject_by':
            nomination.reject_by(request.user)
        return HttpResponseRedirect(reverse(
                'badger.views.nomination_detail',
                args=(slug, id)))

    return render_to_response('%s/nomination_detail.html' % bsettings.TEMPLATE_BASE,
                              dict(badge=badge, nomination=nomination,),
                              context_instance=RequestContext(request))


@require_http_methods(['GET', 'POST'])
@login_required
def nominate_for(request, slug):
    """Submit nomination for a badge"""
    badge = get_object_or_404(Badge, slug=slug)
    if not badge.allows_nominate_for(request.user):
        return HttpResponseForbidden()

    if request.method != "POST":
        form = BadgeSubmitNominationForm()
    else:
        form = BadgeSubmitNominationForm(request.POST, request.FILES)
        if form.is_valid():
            emails = form.cleaned_data['emails']
            for email in emails:
                users = User.objects.filter(email=email)
                if not users:
                    # TODO: Need a deferred nomination mechanism for
                    # non-registered users.
                    pass
                else:
                    nominee = users[0]
                    try:
                        award = badge.nominate_for(nominee, request.user)
                        messages.info(request,
                            _(u'Nomination submitted for {email}').format(email=email))
                    except BadgeAlreadyAwardedException:
                        messages.info(request,
                            _(u'Badge already awarded to {email}').format(email=email))
                    except Exception:
                        messages.info(request,
                            _(u'Nomination failed for {email}').format(email=email))

            return HttpResponseRedirect(reverse('badger.views.detail',
                                                args=(badge.slug,)))

    return render_to_response('%s/badge_nominate_for.html' % bsettings.TEMPLATE_BASE,
                              dict(form=form, badge=badge,),
                              context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = badges
from django.conf import settings
from django.db.models import Sum
from django.db.models.signals import post_save

from .models import GuestbookEntry

import badger
import badger.utils
from badger.utils import get_badge, award_badge, get_progress
from badger.models import Badge, Award, Progress
from badger.signals import badge_was_awarded


badges = [

    dict(slug="test-2",
         title="Test #2",
         description="Second badge"),

    dict(slug="awesomeness",
         title="Awesomeness (you have it)",
         description="Badge with a slug not derived from title."),

    dict(slug="250-words",
         title="250 Words",
         description="You've posted 250 words to my guestbook!"),

    dict(slug="250-words-by-percent",
         title="100% of 250 Words",
         description="You've posted 100% of 250 words to my guestbook!"),

]


def update_badges(overwrite=False):
    badges = [
        dict(slug="master-badger",
             title="Master Badger",
             description="You've collected all badges",
             prerequisites=('test-1', 'test-2', 'awesomeness',
                            'button-clicker')),
    ]

    return badger.utils.update_badges(badges, overwrite)


def on_guestbook_post(sender, **kwargs):
    o = kwargs['instance']
    created = kwargs['created']

    if created:
        award_badge('first-post', o.creator)

    # Increment progress counter and track the completion condition ourselves.
    b = get_badge('250-words')
    p = b.progress_for(o.creator).increment_by(o.word_count)
    if p.counter >= 250:
        b.award_to(o.creator)

    # Update percentage from total word count, and Progress will award on 100%
    total_word_count = (GuestbookEntry.objects.filter(creator=o.creator)
                        .aggregate(s=Sum('word_count'))['s'])
    (get_progress("250-words-by-percent", o.creator)
           .update_percent(total_word_count, 250))


def on_badge_award(sender, signal, award, **kwargs):
    pass


def register_signals():
    post_save.connect(on_guestbook_post, sender=GuestbookEntry)
    badge_was_awarded.connect(on_badge_award, sender=Badge)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User

from django.template.defaultfilters import slugify


class GuestbookEntry(models.Model):
    """Representation of a guestbook entry"""
    message = models.TextField(blank=True)
    creator = models.ForeignKey(User, blank=False)
    created = models.DateTimeField(auto_now_add=True, blank=False)
    modified = models.DateTimeField(auto_now=True, blank=False)
    word_count = models.IntegerField(default=0, blank=True)

    def save(self, *args, **kwargs):
        self.word_count = len(self.message.split(' '))
        super(GuestbookEntry, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

import badger
badger.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'badger_example.views.home', name='home'),
    # url(r'^badger_example/', include('badger_example.foo.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^badges/', include('badger.urls')),
)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-badger documentation build configuration file, created by
# sphinx-quickstart on Thu Feb 14 09:51:15 2013.
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
#sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
# sys.path.insert(0, os.path.abspath('.'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'test_settings'

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx.ext.ifconfig',
              'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-badger'
copyright = u'2013, Les Orchard'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.0.1'
# The full version, including alpha/beta/rc tags.
release = '0.0.1'

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
htmlhelp_basename = 'django-badgerdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-badger.tex', u'django-badger Documentation',
   u'Les Orchard', 'manual'),
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

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-badger', u'django-badger Documentation',
     [u'Les Orchard'], 1)
]

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_settings")


def nose_collector():
    import nose
    return nose.collector()


if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = test_settings
# Django settings for badger_example project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

SITE_ID = 1

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'NAME': 'test-badger.db',
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False # True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'e-=ohaa)s7s3+qeye9^l2!qb&amp;^-ak5o4sty69=vhv@fnxjn7_q'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    #'jingo.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'badger.middleware.RecentBadgeAwardsMiddleware',
)

ROOT_URLCONF = 'badger_example.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    'south',
    'django_nose',  # has to come after south for good test-fu
    'badger_example',
    'badger',
]

MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': [],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

BADGER_TEMPLATE_BASE = 'badger'

########NEW FILE########
