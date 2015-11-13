__FILENAME__ = admin
from django.contrib import admin

# Register your models here.

########NEW FILE########
__FILENAME__ = award_defs
from .models import Award, AwardDef, Badge

from biostar.apps.posts.models import Post, Vote

from django.utils.timezone import utc
from datetime import datetime, timedelta


def now():
    return datetime.utcnow().replace(tzinfo=utc)


def wrap_list(obj, cond):
    return [obj] if cond else []

# Award definitions
AUTOBIO = AwardDef(
    name="Autobiographer",
    desc="has more than 80 characters in the information field of the user's profile",
    func=lambda user: wrap_list(user, len(user.profile.info) > 80),
    icon="fa fa-bullhorn"
)

GOOD_QUESTION = AwardDef(
    name="Good Question",
    desc="asked a question that was upvoted at least 5 times",
    func=lambda user: Post.objects.filter(vote_count__gt=5, author=user, type=Post.QUESTION),
    icon="fa fa-question"
)

GOOD_ANSWER = AwardDef(
    name="Good Answer",
    desc="created an answer that was upvoted at least 5 times",
    func=lambda user: Post.objects.filter(vote_count__gt=5, author=user, type=Post.ANSWER),
    icon="fa fa-pencil-square-o"
)

STUDENT = AwardDef(
    name="Student",
    desc="asked a question with at least 3 up-votes",
    func=lambda user: Post.objects.filter(vote_count__gt=2, author=user, type=Post.QUESTION),
    icon="fa fa-certificate"
)

TEACHER = AwardDef(
    name="Teacher",
    desc="created an answer with at least 3 up-votes",
    func=lambda user: Post.objects.filter(vote_count__gt=2, author=user, type=Post.ANSWER),
    icon="fa fa-smile-o"
)

COMMENTATOR = AwardDef(
    name="Commentator",
    desc="created a comment with at least 3 up-votes",
    func=lambda user: Post.objects.filter(vote_count__gt=2, author=user, type=Post.COMMENT),
    icon="fa fa-comment"
)

CENTURION = AwardDef(
    name="Centurion",
    desc="created 100 posts",
    func=lambda user: wrap_list(user, Post.objects.filter(author=user).count() > 100),
    icon="fa fa-bolt",
    type=Badge.SILVER,
)

EPIC_QUESTION = AwardDef(
    name="Epic Question",
    desc="created a question with more than 10,000 views",
    func=lambda user: Post.objects.filter(author=user, view_count__gt=10000),
    icon="fa fa-bullseye",
    type=Badge.GOLD,
)

POPULAR = AwardDef(
    name="Popular Question",
    desc="created a question with more than 1,000 views",
    func=lambda user: Post.objects.filter(author=user, view_count__gt=1000),
    icon="fa fa-eye",
    type=Badge.GOLD,
)

ORACLE = AwardDef(
    name="Oracle",
    desc="created more than 1,000 posts (questions + answers + comments)",
    func=lambda user: wrap_list(user, Post.objects.filter(author=user).count() > 1000),
    icon="fa fa-sun-o",
    type=Badge.GOLD,
)

PUNDIT = AwardDef(
    name="Pundit",
    desc="created a comment with more than 10 votes",
    func=lambda user: Post.objects.filter(author=user, type=Post.COMMENT, vote_count__gt=10),
    icon="fa fa-comments-o",
    type=Badge.SILVER,
)

GURU = AwardDef(
    name="Guru",
    desc="received more than 100 upvotes",
    func=lambda user: wrap_list(user, Vote.objects.filter(post__author=user).count() > 100),
    icon="fa fa-beer",
    type=Badge.SILVER,
)

CYLON = AwardDef(
    name="Cylon",
    desc="received 1,000 up votes",
    func=lambda user: wrap_list(user, Vote.objects.filter(post__author=user).count() > 1000),
    icon="fa fa-rocket",
    type=Badge.GOLD,
)

VOTER = AwardDef(
    name="Voter",
    desc="voted more than 100 times",
    func=lambda user: wrap_list(user, Vote.objects.filter(author=user).count() > 100),
    icon="fa fa-thumbs-o-up"
)

SUPPORTER = AwardDef(
    name="Supporter",
    desc="voted at least 25 times",
    func=lambda user: wrap_list(user, Vote.objects.filter(author=user).count() > 25),
    icon="fa fa-thumbs-up",
    type=Badge.SILVER,
)

SCHOLAR = AwardDef(
    name="Scholar",
    desc="created an answer that has been accepted",
    func=lambda user: Post.objects.filter(author=user, type=Post.ANSWER, has_accepted=True),
    icon="fa fa-check-circle-o"
)

PROPHET = AwardDef(
    name="Prophet",
    desc="created a post with more than 20 followers",
    func=lambda user: Post.objects.filter(author=user, type__in=Post.TOP_LEVEL, subs_count__gt=20),
    icon="fa fa-pagelines"
)

LIBRARIAN = AwardDef(
    name="Librarian",
    desc="created a post with more than 10 bookmarks",
    func=lambda user: Post.objects.filter(author=user, type__in=Post.TOP_LEVEL, book_count__gt=10),
    icon="fa fa-bookmark-o"
)

def rising_star(user):
    # The user joined no more than three months ago
    cond = now() < user.profile.date_joined + timedelta(weeks=15)
    cond = cond and Post.objects.filter(author=user).count() > 50
    return wrap_list(user, cond)

RISING_STAR = AwardDef(
    name="Rising Star",
    desc="created 50 posts within first three months of joining",
    func=rising_star,
    icon="fa fa-star",
    type=Badge.GOLD,
)

# These awards can only be earned once
SINGLE_AWARDS = [
    AUTOBIO,
    STUDENT,
    TEACHER,
    COMMENTATOR,
    SUPPORTER,
    SCHOLAR,
    VOTER,
    CENTURION,
    CYLON,
    RISING_STAR,
    GURU,
    POPULAR,
    EPIC_QUESTION,
    ORACLE,
    PUNDIT,
    GOOD_ANSWER,
    GOOD_QUESTION,
    PROPHET,
    LIBRARIAN,
]

GREAT_QUESTION = AwardDef(
    name="Great Question",
    desc="created a question with more than 5,000 views",
    func=lambda user: Post.objects.filter(author=user, view_count__gt=5000),
    icon="fa fa-fire",
    type=Badge.SILVER,
)

GOLD_STANDARD = AwardDef(
    name="Gold Standard",
    desc="created a post with more than 25 bookmarks",
    func=lambda user: Post.objects.filter(author=user, book_count__gt=25),
    icon="fa fa-bookmark",
    type=Badge.GOLD,
)

APPRECIATED = AwardDef(
    name="Appreciated",
    desc="created a post with more than 5 votes",
    func=lambda user: Post.objects.filter(author=user, vote_count__gt=4),
    icon="fa fa-heart",
    type=Badge.SILVER,
)


# These awards can be won multiple times
MULTI_AWARDS = [
    GREAT_QUESTION,
    GOLD_STANDARD,
    APPRECIATED,
]

ALL_AWARDS = SINGLE_AWARDS + MULTI_AWARDS
########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Badge'
        db.create_table(u'badges_badge', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('type', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('unique', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('secret', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('count', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'badges', ['Badge'])

        # Adding model 'Award'
        db.create_table(u'badges_award', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('badge', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['badges.Badge'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['users.User'])),
            ('date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'badges', ['Award'])


    def backwards(self, orm):
        # Deleting model 'Badge'
        db.delete_table(u'badges_badge')

        # Deleting model 'Award'
        db.delete_table(u'badges_award')


    models = {
        u'badges.award': {
            'Meta': {'object_name': 'Award'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['badges.Badge']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.User']"})
        },
        u'badges.badge': {
            'Meta': {'object_name': 'Badge'},
            'count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'secret': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'unique': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'sites.site': {
            'Meta': {'ordering': "(u'domain',)", 'object_name': 'Site', 'db_table': "u'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'users.user': {
            'Meta': {'object_name': 'User'},
            'badges': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'flair': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '15'}),
            'full_score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255'}),
            'new_messages': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sites.Site']", 'null': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['badges']
########NEW FILE########
__FILENAME__ = 0002_auto__del_field_badge_secret__del_field_badge_description__add_field_b
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Badge.secret'
        db.delete_column(u'badges_badge', 'secret')

        # Deleting field 'Badge.description'
        db.delete_column(u'badges_badge', 'description')

        # Adding field 'Badge.desc'
        db.add_column(u'badges_badge', 'desc',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=200),
                      keep_default=False)

        # Adding field 'Badge.icon'
        db.add_column(u'badges_badge', 'icon',
                      self.gf('django.db.models.fields.CharField')(default='fa fa-asterisk', max_length=250),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'Badge.secret'
        db.add_column(u'badges_badge', 'secret',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Badge.description'
        db.add_column(u'badges_badge', 'description',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=200),
                      keep_default=False)

        # Deleting field 'Badge.desc'
        db.delete_column(u'badges_badge', 'desc')

        # Deleting field 'Badge.icon'
        db.delete_column(u'badges_badge', 'icon')


    models = {
        u'badges.award': {
            'Meta': {'object_name': 'Award'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['badges.Badge']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.User']"})
        },
        u'badges.badge': {
            'Meta': {'object_name': 'Badge'},
            'count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'desc': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '200'}),
            'icon': ('django.db.models.fields.CharField', [], {'default': "'fa fa-asterisk'", 'max_length': '250'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'unique': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'sites.site': {
            'Meta': {'ordering': "(u'domain',)", 'object_name': 'Site', 'db_table': "u'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'users.user': {
            'Meta': {'object_name': 'User'},
            'badges': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'flair': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '15'}),
            'full_score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255'}),
            'new_messages': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sites.Site']", 'null': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['badges']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_award_context
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Award.context'
        db.add_column(u'badges_award', 'context',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=1000),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Award.context'
        db.delete_column(u'badges_award', 'context')


    models = {
        u'badges.award': {
            'Meta': {'object_name': 'Award'},
            'badge': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['badges.Badge']"}),
            'context': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1000'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.User']"})
        },
        u'badges.badge': {
            'Meta': {'object_name': 'Badge'},
            'count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'desc': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '200'}),
            'icon': ('django.db.models.fields.CharField', [], {'default': "'fa fa-asterisk'", 'max_length': '250'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'unique': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'sites.site': {
            'Meta': {'ordering': "(u'domain',)", 'object_name': 'Site', 'db_table': "u'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'users.user': {
            'Meta': {'object_name': 'User'},
            'activity': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'badges': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'flair': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '15'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255'}),
            'new_messages': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sites.Site']", 'null': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['badges']
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core import mail
import logging

logger = logging.getLogger(__name__)

# Create your models here.

class Badge(models.Model):
    BRONZE, SILVER, GOLD = range(3)
    CHOICES = ((BRONZE, 'Bronze'), (SILVER, 'Silver'), (GOLD, 'Gold'))

    # The name of the badge.
    name = models.CharField(max_length=50)

    # The description of the badge.
    desc = models.CharField(max_length=200, default='')

    # The rarity of the badge.
    type = models.IntegerField(choices=CHOICES, default=BRONZE)

    # Unique badges may be earned only once
    unique = models.BooleanField(default=False)

    # Total number of times awarded
    count = models.IntegerField(default=0)

    # The icon to display for the badge.
    icon = models.CharField(default='fa fa-asterisk', max_length=250)

    def get_absolute_url(self):
        url = reverse("badge-details", kwargs=dict(pk=self.id))
        return url

    def __unicode__(self):
        return self.name


class Award(models.Model):
    '''
    A badge being awarded to a user.Cannot be ManyToManyField
    because some may be earned multiple times
    '''
    badge = models.ForeignKey(Badge)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    date = models.DateTimeField()
    context = models.CharField(max_length=1000, default='')

class AwardDef(object):
    def __init__(self, name, desc, func, icon, type=Badge.BRONZE):
        self.name = name
        self.desc = desc
        self.fun = func
        self.icon = icon
        self.template = "badge/default.html"
        self.type = type

    def validate(self, *args, **kwargs):
        try:
            value = self.fun(*args, **kwargs)
            return value
        except Exception, exc:
            logger.error("validator error %s" % exc)
        return 0

    def __hash__(self):
        return hash(self.name)

    def __cmp__(self, other):
        return cmp(self.name, other.name)



########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from .models import Award, Badge
from biostar.apps.users.models import User

# Create your tests here.

class AwardTest(TestCase):
    email = "janedoe@site.com"

    def setUp(self):
        from biostar import awards
        awards.init_awards()
        User.objects.create(email=self.email)

    def test_user_badge(self):
        from biostar import awards
        eq = self.assertEqual

        award_count = lambda: Award.objects.all().count()

        for a in Award.objects.all():
            print a

        eq(0, award_count())

        jane = User.objects.get(email=self.email)
        awards.create_user_award(jane)

        # No award for new user.
        eq(0, award_count())

        jane.profile.info = "A" * 1000
        jane.save()

        # Check for the autobiographer award.
        awards.create_user_award(jane)

        eq(1, award_count())

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render

# Create your views here.

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

# Register your models here.

########NEW FILE########
__FILENAME__ = models
'''
Inspired by django-messages at https://github.com/arneb/django-messages
'''

from __future__ import print_function, unicode_literals, absolute_import, division
import logging, datetime
from django.db import models
from django.conf import settings
from django.contrib import admin
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _
from django.core import mail

logger = logging.getLogger(__name__)

def now():
    return datetime.datetime.utcnow().replace(tzinfo=utc)

class MessageManager(models.Manager):

    def inbox_for(self, user):
        "Returns all messages that were received by the given user"
        return self.filter(recipient=user)

    def outbox_for(self, user):
        "Returns all messages that were sent by the given user."
        return self.filter(sender=user)

# A message body is information sent to users.
class MessageBody(models.Model):
    """
    A private message from user to user
    """
    MAX_SIZE = 120

    text = models.TextField(_("Text"))
    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', verbose_name=_("Sender"))
    subject = models.CharField(_("Subject"), max_length=MAX_SIZE)
    parent_msg = models.ForeignKey('self', related_name='next_messages', null=True, blank=True, verbose_name=_("Parent message"))
    sent_at = models.DateTimeField(_("sent at"), null=False)

    objects = MessageManager()

    def __unicode__(self):
        return self.subject

    def save(self, **kwargs):
        self.subject = self.subject[:self.MAX_SIZE]
        self.sent_at= self.sent_at or now()
        super(MessageBody, self).save(**kwargs)


# This contains the notification types.
from biostar.const import LOCAL_MESSAGE, MESSAGING_TYPE_CHOICES

# Connects user to message bodies
class Message(models.Model):
    "Connects recipents to sent messages"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='recipients', verbose_name=_("Recipient"))
    body = models.ForeignKey(MessageBody, related_name='messages', verbose_name=_("Message"))
    type = models.IntegerField(choices=MESSAGING_TYPE_CHOICES, default=LOCAL_MESSAGE, db_index=True)
    unread = models.BooleanField(default=True)
    sent_at = models.DateTimeField(db_index=True, null=True)

    def save(self, *args, **kwargs):
        self.sent_at = self.body.sent_at
        super(Message, self).save(**kwargs)

    def __unicode__(self):
        return u"Message %s, %s" % (self.user, self.body_id)

    @staticmethod
    def inbox_count_for(user):
        "Returns the number of unread messages for the given user but does not mark them seen"
        return MessageBody.objects.filter(recipient=user, unread=True).count()

    def email_tuple(self, recipient_list, from_email=None):
        "Returns an email tuple suitable to be mass emailed"
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        data = (self.body.subject, self.body.text, settings.DEFAULT_FROM_EMAIL, recipient_list)
        return data

# Admin interface to Message and MessageBody.
class MessageBodyAdmin(admin.ModelAdmin):
    search_fields = ('sender__name', 'sender__email', 'recipient__name', 'recipient__email', 'subject')
    list_select_related = ["sender", "post"]

# Admin interface to MessageBody
class MessageAdmin(admin.ModelAdmin):
    search_fields = ('recipient__name', 'recipient__email', 'recipient__name', 'recipient__email', 'subject')
    list_select_related = ["user", "post"]

#admin.site.register(Message, MessageAdmin)
admin.site.register(MessageBody, MessageBodyAdmin)



########NEW FILE########
__FILENAME__ = tests
"""
Notification related tests.

These will execute when you run "manage.py test".
"""

import logging
from django.conf import settings
from biostar.apps.users.models import User, Profile
from biostar.apps.posts.models import Post, Subscription
from biostar.apps.messages.models import Message
from django.core import mail

from django.test import TestCase

logging.disable(logging.CRITICAL)

note_count = lambda: Message.objects.all().count()

class NoteTest(TestCase):

    def test_send_email(self):
        "Testing email sending"
        mail.send_mail('Subject here', 'Here is the message.',
            'from@example.com', ['to@example.com'],
            fail_silently=False)
        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].subject, 'Subject here')

    def test_note_creation(self):
        "Testing notifications"

        eq = self.assertEqual

        # Create some users
        title = "Test"
        emails = ["john@this.edu", "jane@this.edu", "bob@this.edu", "alice@this.edu",
                  "bill@this.edu", "jeff@this.edu" ]

        email_count = len(emails)

        users, posts, user = [], [], None
        parent = None
        for email in emails:
            # Create users.
            user = User.objects.create(email=email)
            users.append(user)

        # A welcome message for each user.
        eq(note_count(), email_count)

        # Create a question.
        first = users[0]
        post = Post(title=title, author=first, type=Post.QUESTION)
        post.save()

        answers = []
        for user in users:
            # Every user adds an answer.
            answ = Post(author=user, type=Post.ANSWER, parent=post)
            answ.save()
            answers.append(answ)


        # Total number of posts
        eq(note_count(), 21)

        # Every user has one subscription to the main post
        eq(email_count, Subscription.objects.all().count())

        # Each user has a messages for content posted after
        # they started following the thread.
        for index, user in enumerate(users):
            mesg_c = Message.objects.filter(user=user).count()
            eq (mesg_c, email_count - index )




########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render

# Create your views here.

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Blog'
        db.create_table(u'planet_blog', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(default='', max_length=255)),
            ('desc', self.gf('django.db.models.fields.TextField')(default='')),
            ('feed', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('link', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'planet', ['Blog'])

        # Adding model 'BlogPost'
        db.create_table(u'planet_blogpost', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('blog', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['planet.Blog'])),
            ('uid', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('content', self.gf('django.db.models.fields.TextField')(default='', max_length=20000)),
            ('html', self.gf('django.db.models.fields.TextField')(default='')),
            ('creation_date', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('insert_date', self.gf('django.db.models.fields.DateTimeField')(null=True, db_index=True)),
            ('published', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('link', self.gf('django.db.models.fields.URLField')(max_length=200)),
        ))
        db.send_create_signal(u'planet', ['BlogPost'])


    def backwards(self, orm):
        # Deleting model 'Blog'
        db.delete_table(u'planet_blog')

        # Deleting model 'BlogPost'
        db.delete_table(u'planet_blogpost')


    models = {
        u'planet.blog': {
            'Meta': {'object_name': 'Blog'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'desc': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'feed': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'})
        },
        u'planet.blogpost': {
            'Meta': {'object_name': 'BlogPost'},
            'blog': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['planet.Blog']"}),
            'content': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '20000'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'html': ('django.db.models.fields.TextField', [], {'default': "''"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'insert_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'db_index': 'True'}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['planet']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_blog_list_order
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Blog.list_order'
        db.add_column(u'planet_blog', 'list_order',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Blog.list_order'
        db.delete_column(u'planet_blog', 'list_order')


    models = {
        u'planet.blog': {
            'Meta': {'object_name': 'Blog'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'desc': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'feed': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'list_order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'})
        },
        u'planet.blogpost': {
            'Meta': {'object_name': 'BlogPost'},
            'blog': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['planet.Blog']"}),
            'content': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '20000'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'html': ('django.db.models.fields.TextField', [], {'default': "''"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'insert_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'db_index': 'True'}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['planet']
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.conf import settings
import os, urllib, logging, feedparser, datetime
from django.core.urlresolvers import reverse
from django.utils.timezone import utc
from django.contrib import admin

logger = logging.getLogger(__name__)

def now():
    return datetime.datetime.utcnow().replace(tzinfo=utc)

def abspath(*args):
    """Generates absolute paths"""
    return os.path.abspath(os.path.join(*args))

# Create your models here.

class Blog(models.Model):
    "Represents a blog"
    title = models.CharField(verbose_name='Blog Name', max_length=255, default="", blank=False)
    desc = models.TextField(default='', blank=True)
    feed = models.URLField()
    link = models.URLField()
    active = models.BooleanField(default=True)
    list_order = models.IntegerField(default=0)

    @property
    def fname(self):
        fname = abspath(settings.PLANET_DIR, '%s.xml' % self.id)
        return fname

    def parse(self):
        try:
            doc = feedparser.parse(self.fname)
        except Exception, exc:
            logger.error("error %s parsing blog %s", (exc, self.id))
            doc = None
        return doc

    def download(self):
        try:
            text = urllib.urlopen(self.feed).read()
            stream = file(self.fname, 'wt')
            stream.write(text)
            stream.close()
        except Exception, exc:
            logger.error("error %s downloading %s", (exc, self.feed))

    def __unicode__(self):
        return self.title

class BlogPost(models.Model):
    "Represents an entry of a Blog"

    # The blog that generated the entry
    blog = models.ForeignKey(Blog)

    # A unique id for this entry
    uid = models.CharField(max_length=200, null=False)

    # The title of the entry
    title = models.CharField(max_length=200, null=False)

    # The content of the feed
    content = models.TextField(default='', max_length=20000)

    # Santizied HTML
    html = models.TextField(default='')

    # Date related fields.
    creation_date = models.DateTimeField(db_index=True)

    # Date at which the post has been inserted into the database
    insert_date = models.DateTimeField(db_index=True, null=True)

    # Has the entry been published
    published = models.BooleanField(default=False)

    # The link to the entry
    link = models.URLField()

    @property
    def get_title(self):
        return u"BLOG: %s" % self.title

    def get_absolute_url(self):
        return self.link

    def save(self, *args, **kwargs):

        if not self.id:
            # Set the date to current time if missing.
            self.insert_date = self.insert_date or now()

        super(BlogPost, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.title

admin.site.register(Blog)
########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(object):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)




########NEW FILE########
__FILENAME__ = views
# Create your views here.
from django.views.generic import DetailView, ListView, TemplateView, UpdateView, View
from .models import Blog, BlogPost
from django.conf import settings
from django.db.models import Max, Count


def reset_counts(request, label):
    "Resets counts in the session"
    label = label.lower()
    counts = request.session.get(settings.SESSION_KEY, {})
    if label in counts:
        counts[label] = ''
        request.session[settings.SESSION_KEY] = counts


class BlogPostList(ListView):
    template_name = "planet/planet_entries.html"
    paginate_by = 25
    model = BlogPost
    context_object_name = 'blogposts'

    def get_queryset(self):
        query = super(BlogPostList, self).get_queryset()
        return query.select_related("blog").order_by("-creation_date")

    def get_context_data(self, **kwargs):
        get = self.request.GET.get
        self.topic = 'planet'
        context = super(BlogPostList, self).get_context_data(**kwargs)
        context['page_title'] = "Planet"
        context['topic'] = self.topic
        context['limit'] = get('limit', '')
        context['q'] = get('q', '')
        context['sort'] = get('sort', '')

        # Sort blog posts by latest insert time
        blogs = Blog.objects.all().annotate(updated_date=Max("blogpost__creation_date"),
                                            count=Count("blogpost__id")).order_by("-updated_date", "-list_order")
        context['blogs'] = blogs

        reset_counts(self.request, self.topic)
        return context

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

# Register your models here.

########NEW FILE########
__FILENAME__ = auth
__author__ = 'ialbert'

def post_permissions(request, post):
    """
    Sets permission attributes on a post.

    """
    user = request.user
    is_editable = has_ownership = False

    if user.is_authenticated():

        if user == post.author :
            has_ownership = is_editable = True
        elif user.is_moderator or user.is_staff:
            is_editable = True

    post.is_editable = is_editable
    post.has_ownership = has_ownership

    return post
########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Tag'
        db.create_table(u'posts_tag', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.TextField')(max_length=50, db_index=True)),
            ('count', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'posts', ['Tag'])

        # Adding model 'Post'
        db.create_table(u'posts_post', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=140)),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['users.User'])),
            ('lastedit_user', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'editor', to=orm['users.User'])),
            ('rank', self.gf('django.db.models.fields.FloatField')(default=0, blank=True)),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('type', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('vote_count', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True, blank=True)),
            ('view_count', self.gf('django.db.models.fields.IntegerField')(default=0, blank=True)),
            ('reply_count', self.gf('django.db.models.fields.IntegerField')(default=0, blank=True)),
            ('comment_count', self.gf('django.db.models.fields.IntegerField')(default=0, blank=True)),
            ('book_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('changed', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('subs_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('thread_score', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True, blank=True)),
            ('creation_date', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('lastedit_date', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('sticky', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('has_accepted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('root', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name=u'descendants', null=True, to=orm['posts.Post'])),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name=u'children', null=True, to=orm['posts.Post'])),
            ('content', self.gf('django.db.models.fields.TextField')(default=u'')),
            ('tag_val', self.gf('django.db.models.fields.CharField')(default=u'', max_length=100, blank=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'], null=True)),
        ))
        db.send_create_signal(u'posts', ['Post'])

        # Adding M2M table for field tag_set on 'Post'
        m2m_table_name = db.shorten_name(u'posts_post_tag_set')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('post', models.ForeignKey(orm[u'posts.post'], null=False)),
            ('tag', models.ForeignKey(orm[u'posts.tag'], null=False))
        ))
        db.create_unique(m2m_table_name, ['post_id', 'tag_id'])

        # Adding model 'PostView'
        db.create_table(u'posts_postview', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ip', self.gf('django.db.models.fields.GenericIPAddressField')(default=u'', max_length=39, null=True, blank=True)),
            ('post', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'post_views', to=orm['posts.Post'])),
            ('date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal(u'posts', ['PostView'])

        # Adding model 'Vote'
        db.create_table(u'posts_vote', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['users.User'])),
            ('post', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'votes', to=orm['posts.Post'])),
            ('type', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, db_index=True, blank=True)),
        ))
        db.send_create_signal(u'posts', ['Vote'])

        # Adding model 'Subscription'
        db.create_table(u'posts_subscription', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['users.User'])),
            ('post', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'subs', to=orm['posts.Post'])),
            ('type', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
        ))
        db.send_create_signal(u'posts', ['Subscription'])

        # Adding unique constraint on 'Subscription', fields ['user', 'post']
        db.create_unique(u'posts_subscription', ['user_id', 'post_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'Subscription', fields ['user', 'post']
        db.delete_unique(u'posts_subscription', ['user_id', 'post_id'])

        # Deleting model 'Tag'
        db.delete_table(u'posts_tag')

        # Deleting model 'Post'
        db.delete_table(u'posts_post')

        # Removing M2M table for field tag_set on 'Post'
        db.delete_table(db.shorten_name(u'posts_post_tag_set'))

        # Deleting model 'PostView'
        db.delete_table(u'posts_postview')

        # Deleting model 'Vote'
        db.delete_table(u'posts_vote')

        # Deleting model 'Subscription'
        db.delete_table(u'posts_subscription')


    models = {
        u'posts.post': {
            'Meta': {'object_name': 'Post'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.User']"}),
            'book_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'changed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'comment_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'default': "u''"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'has_accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastedit_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'lastedit_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'editor'", 'to': u"orm['users.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'children'", 'null': 'True', 'to': u"orm['posts.Post']"}),
            'rank': ('django.db.models.fields.FloatField', [], {'default': '0', 'blank': 'True'}),
            'reply_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'root': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'descendants'", 'null': 'True', 'to': u"orm['posts.Post']"}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sites.Site']", 'null': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subs_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tag_set': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['posts.Tag']", 'symmetrical': 'False', 'blank': 'True'}),
            'tag_val': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '100', 'blank': 'True'}),
            'thread_score': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'type': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'view_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'vote_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True', 'blank': 'True'})
        },
        u'posts.postview': {
            'Meta': {'object_name': 'PostView'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.GenericIPAddressField', [], {'default': "u''", 'max_length': '39', 'null': 'True', 'blank': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'post_views'", 'to': u"orm['posts.Post']"})
        },
        u'posts.subscription': {
            'Meta': {'unique_together': "((u'user', u'post'),)", 'object_name': 'Subscription'},
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'subs'", 'to': u"orm['posts.Post']"}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.User']"})
        },
        u'posts.tag': {
            'Meta': {'object_name': 'Tag'},
            'count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'max_length': '50', 'db_index': 'True'})
        },
        u'posts.vote': {
            'Meta': {'object_name': 'Vote'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.User']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'votes'", 'to': u"orm['posts.Post']"}),
            'type': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'sites.site': {
            'Meta': {'ordering': "(u'domain',)", 'object_name': 'Site', 'db_table': "u'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'users.user': {
            'Meta': {'object_name': 'User'},
            'badges': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'flair': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '15'}),
            'full_score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255'}),
            'new_messages': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sites.Site']", 'null': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['posts']
########NEW FILE########
__FILENAME__ = 0002_auto__add_data
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Data'
        db.create_table(u'posts_data', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('post', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['posts.Post'])),
            ('file', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('size', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'posts', ['Data'])

        # Adding field 'Post.html'
        db.add_column(u'posts_post', 'html',
                      self.gf('django.db.models.fields.TextField')(default=u''),
                      keep_default=False)


        # Changing field 'Post.title'
        db.alter_column(u'posts_post', 'title', self.gf('django.db.models.fields.CharField')(max_length=200))

    def backwards(self, orm):
        # Deleting model 'Data'
        db.delete_table(u'posts_data')

        # Deleting model 'ReplyToken'
        db.delete_table(u'posts_replytoken')

        # Deleting field 'Post.html'
        db.delete_column(u'posts_post', 'html')


        # Changing field 'Post.title'
        db.alter_column(u'posts_post', 'title', self.gf('django.db.models.fields.CharField')(max_length=140))

    models = {
        u'posts.data': {
            'Meta': {'object_name': 'Data'},
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['posts.Post']"}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        u'posts.post': {
            'Meta': {'object_name': 'Post'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.User']"}),
            'book_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'changed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'comment_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'default': "u''"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'has_accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'html': ('django.db.models.fields.TextField', [], {'default': "u''"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastedit_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'lastedit_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'editor'", 'to': u"orm['users.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'children'", 'null': 'True', 'to': u"orm['posts.Post']"}),
            'rank': ('django.db.models.fields.FloatField', [], {'default': '0', 'blank': 'True'}),
            'reply_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'root': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'descendants'", 'null': 'True', 'to': u"orm['posts.Post']"}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sites.Site']", 'null': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subs_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tag_set': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['posts.Tag']", 'symmetrical': 'False', 'blank': 'True'}),
            'tag_val': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '100', 'blank': 'True'}),
            'thread_score': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'type': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'view_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'vote_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True', 'blank': 'True'})
        },
        u'posts.postview': {
            'Meta': {'object_name': 'PostView'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.GenericIPAddressField', [], {'default': "u''", 'max_length': '39', 'null': 'True', 'blank': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'post_views'", 'to': u"orm['posts.Post']"})
        },
        u'posts.replytoken': {
            'Meta': {'object_name': 'ReplyToken'},
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['posts.Post']"}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.User']"})
        },
        u'posts.subscription': {
            'Meta': {'unique_together': "((u'user', u'post'),)", 'object_name': 'Subscription'},
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'subs'", 'to': u"orm['posts.Post']"}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.User']"})
        },
        u'posts.tag': {
            'Meta': {'object_name': 'Tag'},
            'count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'max_length': '50', 'db_index': 'True'})
        },
        u'posts.vote': {
            'Meta': {'object_name': 'Vote'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.User']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'votes'", 'to': u"orm['posts.Post']"}),
            'type': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'sites.site': {
            'Meta': {'ordering': "(u'domain',)", 'object_name': 'Site', 'db_table': "u'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'users.user': {
            'Meta': {'object_name': 'User'},
            'activity': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'badges': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'flair': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '15'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255'}),
            'new_messages': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sites.Site']", 'null': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['posts']
########NEW FILE########
__FILENAME__ = 0003_auto__add_foo
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Foo'
        db.create_table(u'posts_foo', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['users.User'])),
        ))
        db.send_create_signal(u'posts', ['Foo'])

        # Adding model 'ReplyToken'
        db.create_table(u'posts_replytoken', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')()),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['users.User'])),
            ('post', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['posts.Post'])),
            ('token', self.gf('django.db.models.fields.CharField')(max_length=256)),
        ))
        db.send_create_signal(u'posts', ['ReplyToken'])

    def backwards(self, orm):
        # Deleting model 'Foo'
        db.delete_table(u'posts_foo')


    models = {
        u'posts.data': {
            'Meta': {'object_name': 'Data'},
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['posts.Post']"}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        u'posts.foo': {
            'Meta': {'object_name': 'Foo'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.User']"})
        },
        u'posts.post': {
            'Meta': {'object_name': 'Post'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.User']"}),
            'book_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'changed': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'comment_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'default': "u''"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'has_accepted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'html': ('django.db.models.fields.TextField', [], {'default': "u''"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastedit_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'lastedit_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'editor'", 'to': u"orm['users.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'children'", 'null': 'True', 'to': u"orm['posts.Post']"}),
            'rank': ('django.db.models.fields.FloatField', [], {'default': '0', 'blank': 'True'}),
            'reply_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'root': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'descendants'", 'null': 'True', 'to': u"orm['posts.Post']"}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sites.Site']", 'null': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'sticky': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subs_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'tag_set': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['posts.Tag']", 'symmetrical': 'False', 'blank': 'True'}),
            'tag_val': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '100', 'blank': 'True'}),
            'thread_score': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'type': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'view_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'vote_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True', 'blank': 'True'})
        },
        u'posts.postview': {
            'Meta': {'object_name': 'PostView'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.GenericIPAddressField', [], {'default': "u''", 'max_length': '39', 'null': 'True', 'blank': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'post_views'", 'to': u"orm['posts.Post']"})
        },
        u'posts.replytoken': {
            'Meta': {'object_name': 'ReplyToken'},
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['posts.Post']"}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.User']"})
        },
        u'posts.subscription': {
            'Meta': {'unique_together': "((u'user', u'post'),)", 'object_name': 'Subscription'},
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'subs'", 'to': u"orm['posts.Post']"}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.User']"})
        },
        u'posts.tag': {
            'Meta': {'object_name': 'Tag'},
            'count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'max_length': '50', 'db_index': 'True'})
        },
        u'posts.vote': {
            'Meta': {'object_name': 'Vote'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.User']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'votes'", 'to': u"orm['posts.Post']"}),
            'type': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'sites.site': {
            'Meta': {'ordering': "(u'domain',)", 'object_name': 'Site', 'db_table': "u'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'users.user': {
            'Meta': {'object_name': 'User'},
            'activity': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'badges': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'flair': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '15'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255'}),
            'new_messages': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sites.Site']", 'null': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['posts']
########NEW FILE########
__FILENAME__ = models
from __future__ import print_function, unicode_literals, absolute_import, division
import logging, datetime, string
from django.db import models
from django.conf import settings
from django.contrib import admin
from django.contrib.sites.models import Site

from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
import bleach
from django.db.models import Q, F
from django.core.exceptions import ObjectDoesNotExist
from biostar import const
from biostar.apps.util import html
from biostar.apps import util
# HTML sanitization parameters.

logger = logging.getLogger(__name__)

def now():
    return datetime.datetime.utcnow().replace(tzinfo=utc)

class Tag(models.Model):
    name = models.TextField(max_length=50, db_index=True)
    count = models.IntegerField(default=0)

    @staticmethod
    def fixcase(name):
        return name.upper() if len(name) == 1 else name.lower()

    @staticmethod
    def update_counts(sender, instance, action, pk_set, *args, **kwargs):
        "Applies tag count updates upon post changes"

        if action == 'post_add':
            Tag.objects.filter(pk__in=pk_set).update(count=F('count') + 1)

        if action == 'post_remove':
            Tag.objects.filter(pk__in=pk_set).update(count=F('count') - 1)

        if action == 'pre_clear':
            instance.tag_set.all().update(count=F('count') - 1)

    def __unicode__(self):
        return self.name

class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'count')
    search_fields = ['name']


admin.site.register(Tag, TagAdmin)

class PostManager(models.Manager):

    def my_bookmarks(self, user):
        query = self.filter(votes__author=user, votes__type=Vote.BOOKMARK)
        query = query.select_related("root", "author", "lastedit_user")
        query = query.prefetch_related("tag_set")
        return query

    def my_posts(self, target, user):

        # Show all posts for moderators or targets
        if user.is_moderator or user == target:
            query = self.filter(author=target)
        else:
            query = self.filter(author=target).exclude(status=Post.DELETED)

        query = query.select_related("root", "author", "lastedit_user")
        query = query.prefetch_related("tag_set")
        query = query.order_by("-creation_date")
        return query

    def fixcase(self, text):
        return text.upper() if len(text) == 1 else text.lower()

    def tag_search(self, text):
        "Performs a query by one or more + separated tags"
        include, exclude = [], []
        for term in text.split(','):
            term = term.strip()
            if term.endswith("!"):
                exclude.append(self.fixcase(term[:-1]))
            else:
                include.append(self.fixcase(term))

        if include:
            query = self.filter(type__in=Post.TOP_LEVEL, tag_set__name__in=include).exclude(
                tag_set__name__in=exclude)
        else:
            query = self.filter(type__in=Post.TOP_LEVEL).exclude(tag_set__name__in=exclude)

        # Remove fields that are not used.
        query = query.defer('content', 'html')

        # Get the tags.
        query = query.select_related("root", "author", "lastedit_user").prefetch_related("tag_set").distinct()

        return query

    def get_thread(self, root, user):
        # Populate the object to build a tree that contains all posts in the thread.
        is_moderator = user.is_authenticated() and user.is_moderator
        if is_moderator:
            query = self.filter(root=root).select_related("root", "author", "lastedit_user").order_by("type", "-has_accepted", "-vote_count", "creation_date")
        else:
            query = self.filter(root=root).exclude(status=Post.DELETED).select_related("root", "author", "lastedit_user").order_by("type", "-has_accepted", "-vote_count", "creation_date")

        return query

    def top_level(self, user):
        "Returns posts based on a user type"
        is_moderator = user.is_authenticated() and user.is_moderator
        if is_moderator:
            query = self.filter(type__in=Post.TOP_LEVEL)
        else:
            query = self.filter(type__in=Post.TOP_LEVEL).exclude(status=Post.DELETED)

        return query.select_related("root", "author", "lastedit_user").prefetch_related("tag_set").defer("content", "html")


class Post(models.Model):
    "Represents a post in Biostar"

    objects = PostManager()

    # Post statuses.
    PENDING, OPEN, CLOSED, DELETED = range(4)
    STATUS_CHOICES = [(PENDING, "Pending"), (OPEN, "Open"), (CLOSED, "Closed"), (DELETED, "Deleted")]

    # Question types. Answers should be listed before comments.
    QUESTION, ANSWER, JOB, FORUM, PAGE, BLOG, COMMENT, DATA, TUTORIAL, BOARD, TOOL, NEWS = range(12)

    TYPE_CHOICES = [
        (QUESTION, "Question"), (ANSWER, "Answer"), (COMMENT, "Comment"),
        (JOB, "Job"), (FORUM, "Forum"), (TUTORIAL, "Tutorial"),
        (DATA, "Data"), (PAGE, "Page"), (TOOL, "Tool"), (NEWS, "News"),
        (BLOG, "Blog"), (BOARD, "Bulletin Board")
    ]

    TOP_LEVEL = set((QUESTION, JOB, FORUM, PAGE, BLOG, DATA, TUTORIAL, TOOL, NEWS, BOARD))

    title = models.CharField(max_length=200, null=False)

    # The user that originally created the post.
    author = models.ForeignKey(settings.AUTH_USER_MODEL)

    # The user that edited the post most recently.
    lastedit_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='editor')

    # Indicates the information value of the post.
    rank = models.FloatField(default=0, blank=True)

    # Post status: open, closed, deleted.
    status = models.IntegerField(choices=STATUS_CHOICES, default=OPEN)

    # The type of the post: question, answer, comment.
    type = models.IntegerField(choices=TYPE_CHOICES, db_index=True)

    # Number of upvotes for the post
    vote_count = models.IntegerField(default=0, blank=True, db_index=True)

    # The number of views for the post.
    view_count = models.IntegerField(default=0, blank=True)

    # The number of replies that a post has.
    reply_count = models.IntegerField(default=0, blank=True)

    # The number of comments that a post has.
    comment_count = models.IntegerField(default=0, blank=True)

    # Bookmark count.
    book_count = models.IntegerField(default=0)

    # Indicates indexing is needed.
    changed = models.BooleanField(default=True)

    # How many people follow that thread.
    subs_count = models.IntegerField(default=0)

    # The total score of the thread (used for top level only)
    thread_score = models.IntegerField(default=0, blank=True, db_index=True)

    # Date related fields.
    creation_date = models.DateTimeField(db_index=True)
    lastedit_date = models.DateTimeField(db_index=True)

    # Stickiness of the post.
    sticky = models.BooleanField(default=False, db_index=True)

    # Indicates whether the post has accepted answer.
    has_accepted = models.BooleanField(default=False, blank=True)

    # This will maintain the ancestor/descendant relationship bewteen posts.
    root = models.ForeignKey('self', related_name="descendants", null=True, blank=True)

    # This will maintain parent/child replationships between posts.
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')

    # This is the HTML that the user enters.
    content = models.TextField(default='')

    # This is the  HTML that gets displayed.
    html = models.TextField(default='')

    # The tag value is the canonical form of the post's tags
    tag_val = models.CharField(max_length=100, default="", blank=True)

    # The tag set is built from the tag string and used only for fast filtering
    tag_set = models.ManyToManyField(Tag, blank=True, )

    # What site does the post belong to.
    site = models.ForeignKey(Site, null=True)

    def parse_tags(self):
        return util.split_tags(self.tag_val)

    def add_data(self, text):
        ids = util.split_tags(text)
        data = Data.objects.filter(id__in=ids)


    def add_tags(self, text):
        text = text.strip()
        if not text:
            return
        # Sanitize the tag value
        self.tag_val = bleach.clean(text, tags=[], attributes=[], styles={}, strip=True)
        # Clear old tags
        self.tag_set.clear()
        tags = [Tag.objects.get_or_create(name=name)[0] for name in self.parse_tags()]
        self.tag_set.add(*tags)
        #self.save()

    @property
    def as_text(self):
        "Returns the body of the post after stripping the HTML tags"
        text = bleach.clean(self.content, tags=[], attributes=[], styles={}, strip=True)
        return text

    def peek(self, length=300):
        "A short peek at the post"
        return self.as_text[:length]

    def get_title(self):
        if self.status == Post.OPEN:
            return self.title
        else:
            return "(%s) %s" % ( self.get_status_display(), self.title)

    @property
    def is_open(self):
        return self.status == Post.OPEN

    @property
    def age_in_days(self):
        delta = const.now() - self.creation_date
        return delta.days

    def update_reply_count(self):
        "This can be used to set the answer count."
        if self.type == Post.ANSWER:
            reply_count = Post.objects.filter(parent=self.parent, type=Post.ANSWER, status=Post.OPEN).count()
            Post.objects.filter(pk=self.parent_id).update(reply_count=reply_count)

    def delete(self, using=None):
        # Collect tag names.
        tag_names = [t.name for t in self.tag_set.all()]

        # While there is a signal to do this it is much faster this way.
        Tag.objects.filter(name__in=tag_names).update(count=F('count') - 1)

        # Remove tags with zero counts.
        Tag.objects.filter(count=0).delete()
        super(Post, self).delete(using=using)

    def save(self, *args, **kwargs):

        # Sanitize the post body.
        self.html = html.parse_html(self.content)

        # Must add tags with instance method. This is just for safety.
        self.tag_val = html.strip_tags(self.tag_val)

        # Posts other than a question also carry the same tag
        if self.is_toplevel and self.type != Post.QUESTION:
            required_tag = self.get_type_display()
            if required_tag not in self.tag_val:
                self.tag_val += "," + required_tag

        if not self.id:

            # Set the titles
            if self.parent and not self.title:
                self.title = self.parent.title

            if self.parent and self.parent.type in (Post.ANSWER, Post.COMMENT):
                # Only comments may be added to a parent that is answer or comment.
                self.type = Post.COMMENT

            if self.type is None:
                # Set post type if it was left empty.
                self.type = self.COMMENT if self.parent else self.FORUM

            # This runs only once upon object creation.
            self.title = self.parent.title if self.parent else self.title
            self.lastedit_user = self.author
            self.status = self.status or Post.PENDING
            self.creation_date = self.creation_date or now()
            self.lastedit_date = self.creation_date

            # Set the timestamps on the parent
            if self.type == Post.ANSWER:
                self.parent.lastedit_date = self.lastedit_date
                self.parent.lastedit_user = self.lastedit_user
                self.parent.save()

        # Recompute post reply count
        self.update_reply_count()

        super(Post, self).save(*args, **kwargs)

    def __unicode__(self):
        return "%s: %s (id=%s)" % (self.get_type_display(), self.title, self.id)

    @property
    def is_toplevel(self):
        return self.type in Post.TOP_LEVEL

    def get_absolute_url(self):
        "A blog will redirect to the original post"
        #if self.url:
        #    return self.url
        url = reverse("post-details", kwargs=dict(pk=self.root_id))
        return url if self.is_toplevel else "%s#%s" % (url, self.id)

    @staticmethod
    def update_post_views(post, request, minutes=settings.POST_VIEW_MINUTES):
        "Views are updated per user session"

        # Extract the IP number from the request.
        ip1 = request.META.get('REMOTE_ADDR', '')
        ip2 = request.META.get('HTTP_X_FORWARDED_FOR', '').split(",")[0].strip()
        ip = ip1 or ip2 or '0.0.0.0'

        now = const.now()
        since = now - datetime.timedelta(minutes=minutes)

        # One view per time interval from each IP address.
        if not PostView.objects.filter(ip=ip, post=post, date__gt=since):
            PostView.objects.create(ip=ip, post=post, date=now)
            Post.objects.filter(id=post.id).update(view_count=F('view_count') + 1)
        return post

    @staticmethod
    def check_root(sender, instance, created, *args, **kwargs):
        "We need to ensure that the parent and root are set on object creation."
        if created:

            if not (instance.root or instance.parent):
                # Neither root or parent are set.
                instance.root = instance.parent = instance

            elif instance.parent:
                # When only the parent is set the root must follow the parent root.
                instance.root = instance.parent.root

            elif instance.root:
                # The root should never be set on creation.
                raise Exception('Root may not be set on creation')

            if instance.parent.type in (Post.ANSWER, Post.COMMENT):
                # Answers and comments may only have comments associated with them.
                instance.type = Post.COMMENT

            assert instance.root and instance.parent

            if not instance.is_toplevel:
                # Title is inherited from top level.
                instance.title = "%s: %s" % (instance.get_type_display()[0], instance.root.title[:80])

                if instance.type == Post.ANSWER:
                    Post.objects.filter(id=instance.root.id).update(reply_count=F("reply_count") + 1)

            instance.save()

class Foo(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)

class ReplyToken(models.Model):
    """
    Connects a user and a post to a unique token. Sending back the token identifies
    both the user and the post that they are replying to.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    post = models.ForeignKey(Post)
    token = models.CharField(max_length=256)
    date = models.DateTimeField(auto_created=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.token = util.make_uuid()
        super(ReplyToken, self).save(*args, **kwargs)

class ReplyTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'token', 'date')
    ordering = ['-date']
    search_fields = ('post__title', 'user__name')

admin.site.register(ReplyToken, ReplyTokenAdmin)

class Data(models.Model):
    "Represents a dataset attached to a post"
    name = models.CharField(max_length=80)
    post = models.ForeignKey(Post, null=True)
    file = models.FileField(upload_to=settings.MEDIA_ROOT)
    size = models.IntegerField()

class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'author')
    fieldsets = (
        (None, {'fields': ('title',)}),
        ('Attributes', {'fields': ('type', 'status', 'sticky',)}),
        ('Content', {'fields': ('content', )}),
    )
    search_fields = ('title', 'author__name')


admin.site.register(Post, PostAdmin)


class PostView(models.Model):
    """
    Keeps track of post views based on IP address.
    """
    ip = models.GenericIPAddressField(default='', null=True, blank=True)
    post = models.ForeignKey(Post, related_name="post_views")
    date = models.DateTimeField(auto_now=True)


class Vote(models.Model):
    # Post statuses.
    UP, DOWN, BOOKMARK, ACCEPT = range(4)
    TYPE_CHOICES = [(UP, "Upvote"), (DOWN, "DownVote"), (BOOKMARK, "Bookmark"), (ACCEPT, "Accept")]

    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    post = models.ForeignKey(Post, related_name='votes')
    type = models.IntegerField(choices=TYPE_CHOICES, db_index=True)
    date = models.DateTimeField(db_index=True, auto_now=True)

    def __unicode__(self):
        return u"Vote: %s, %s, %s" % (self.post_id, self.author_id, self.get_type_display())

class VoteAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'type', 'date')
    ordering = ['-date']
    search_fields = ('post__title', 'author__name')


admin.site.register(Vote, VoteAdmin)

class SubscriptionManager(models.Manager):
    def get_subs(self, post):
        "Returns all suscriptions for a post"
        return self.filter(post=post.root).select_related("user")

# This contains the notification types.
from biostar.const import LOCAL_MESSAGE, MESSAGING_TYPE_CHOICES


class Subscription(models.Model):
    "Connects a post to a user"

    class Meta:
        unique_together = (("user", "post"),)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("User"), db_index=True)
    post = models.ForeignKey(Post, verbose_name=_("Post"), related_name="subs", db_index=True)
    type = models.IntegerField(choices=MESSAGING_TYPE_CHOICES, default=LOCAL_MESSAGE, db_index=True)
    date = models.DateTimeField(_("Date"), db_index=True)

    objects = SubscriptionManager()

    def __unicode__(self):
        return "%s to %s" % (self.user.name, self.post.title)

    def save(self, *args, **kwargs):

        if not self.id:
            # Set the date to current time if missing.
            self.date = self.date or const.now()

        super(Subscription, self).save(*args, **kwargs)


    @staticmethod
    def get_sub(post, user):

        if user.is_authenticated():
            try:
                return Subscription.objects.get(post=post, user=user)
            except ObjectDoesNotExist, exc:
                return None

        return None

    @staticmethod
    def create(sender, instance, created, *args, **kwargs):
        "Creates a subscription of a user to a post"
        user = instance.author
        root = instance.root
        if Subscription.objects.filter(post=root, user=user).count() == 0:
            sub_type = user.profile.message_prefs
            if sub_type == const.DEFAULT_MESSAGES:
                sub_type = const.EMAIL_MESSAGE if instance.is_toplevel else const.LOCAL_MESSAGE
            sub = Subscription(post=root, user=user, type=sub_type)
            sub.date = datetime.datetime.utcnow().replace(tzinfo=utc)
            sub.save()
            # Increase the subscription count of the root.
            Post.objects.filter(pk=root.id).update(subs_count=F('subs_count') + 1)

    @staticmethod
    def finalize_delete(sender, instance, *args, **kwargs):
        # Decrease the subscription count of the post.
        Post.objects.filter(pk=instance.post.root_id).update(subs_count=F('subs_count') - 1)


# Admin interface for subscriptions
class SubscriptionAdmin(admin.ModelAdmin):
    search_fields = ('user__name', 'user__email')
    list_select_related = ["user", "post"]


admin.site.register(Subscription, SubscriptionAdmin)

# Data signals
from django.db.models.signals import post_save, post_delete, m2m_changed

post_save.connect(Post.check_root, sender=Post)
post_save.connect(Subscription.create, sender=Post, dispatch_uid="create_subs")
post_delete.connect(Subscription.finalize_delete, sender=Subscription, dispatch_uid="delete_subs")
m2m_changed.connect(Tag.update_counts, sender=Post.tag_set.through)


########NEW FILE########
__FILENAME__ = tests
"""
Post related tests.

These will execute when you run "manage.py test".
"""
from __future__ import print_function, unicode_literals, absolute_import, division

import logging
from django.conf import settings
from biostar.apps.users.models import User, Profile
from biostar.apps.posts.models import Post, Subscription, Tag
from biostar.apps.messages.models import Message

from django.test import TestCase

logging.disable(logging.INFO)


class PostTest(TestCase):

    def test_tagging(self):
        "Testing tagging."
        eq = self.assertEqual

        eq(0, Tag.objects.all().count() )

        # Create an admin user and a post.
        title = "Hello Posts!"
        email = "john@this.edu"
        jane = User.objects.create(email=email)
        html = "<b>Hello World!</b>"
        post = Post(title=title, author=jane, type=Post.FORUM, content=html)
        post.save()
        post.add_tags("t1,t2, t3")

        eq(3, Tag.objects.all().count())

        post = Post(title=title, author=jane, type=Post.FORUM, content=html)
        post.save()
        post.add_tags("t1, t2, t3, t2, t1, t1")

        t1 = Tag.objects.get(name="t1")
        t3 = Tag.objects.get(name="t3")

        eq(2, t1.count)
        eq(2, t3.count)

        post.add_tags("t2 t4")

        t1 = Tag.objects.get(name="t1")
        t3 = Tag.objects.get(name="t3")

        eq(1, t1.count)
        eq(1, t3.count)

    def test_post_creation(self):
        "Testing post creation."
        eq = self.assertEqual

        # Create an admin user and a post.
        title = "Hello Posts!"
        email = "john@this.edu"
        jane = User.objects.create(email=email)
        html = "<b>Hello World!</b>"
        post = Post(title=title, author=jane, type=Post.FORUM, content=html)
        post.save()

        # Get the object fresh.
        post = Post.objects.get(pk=post.id)

        eq(post.type, Post.FORUM)
        eq(post.root, post)
        eq(post.parent, post)

        # Subscriptions are automatically created
        sub = Subscription.objects.get(user=jane)
        eq(sub.user, jane)
        eq(sub.post, post)

        # A new post triggers a message to the author.
        email = "jane@this.edu"
        john = User.objects.create(email=email)
        answer = Post(author=john, parent=post, type=Post.ANSWER)
        answer.save()

        eq(answer.root, post)
        eq(answer.parent, post)
        eq(answer.type, Post.ANSWER)

        # Add comment. The parent will override the post type.
        email = "bob@this.edu"
        bob = User.objects.create(email=email)
        comment = Post(author=bob, type=Post.FORUM, parent=answer)
        comment.save()

        eq(comment.root, post)
        eq(comment.parent, answer)
        eq(comment.type, Post.COMMENT)

        # Everyone posting in a thread gets a subscription to the root post of the
        subs = Subscription.objects.filter(post=post)
        eq(len(subs), 3)

TEST_CONTENT_EMBEDDING ="""
<p>Gist links may be formatted</p>

<pre>
https://gist.github.com/ialbert/ae46c5f51d63cdf2d0d2</pre>

<p>or embedded:</p>

<p>https://gist.github.com/ialbert/ae46c5f51d63cdf2d0d2</p>

<p>Video links may be formatted</p>

<pre>
http://www.youtube.com/watch?v=_cDaX0xJPvI</pre>

<p>or embedded:</p>

<p>http://www.youtube.com/watch?v=_cDaX0xJPvI</p>

<p>Internal links are recognized:</p>

<pre>
http://test.biostars.org/u/2/</pre>


<p>vs&nbsp;http://test.biostars.org/u/2/</p>
<p>Similarly&nbsp;</p>

<pre>
http://test.biostars.org/p/2/</pre>

<p>versus&nbsp;http://test.biostars.org/p/2/</p>

<p>&nbsp;</p>
"""
########NEW FILE########
__FILENAME__ = views
# Create your views here.
from django.shortcuts import render_to_response
from django.views.generic import TemplateView, DetailView, ListView, FormView, UpdateView
from .models import Post
from django import forms
from django.core.urlresolvers import reverse
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, Div, Submit, ButtonHolder
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib import messages
from . import auth
from braces.views import LoginRequiredMixin
from datetime import datetime
from django.utils.timezone import utc
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from biostar.const import OrderedDict
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import logging

logger = logging.getLogger(__name__)


def valid_title(text):
    "Validates form input for tags"
    text = text.strip()
    if not text:
        raise ValidationError('Please enter a title')

    if len(text) < 10:
        raise ValidationError('The title is too short')

    words = text.split(" ")
    if len(words) < 3:
        raise ValidationError('More than two words please.')


def valid_tag(text):
    "Validates form input for tags"
    text = text.strip()
    if not text:
        raise ValidationError('Please enter at least one tag')
    if len(text) > 50:
        raise ValidationError('Tag line is too long (50 characters max)')
    words = text.split(",")
    if len(words) > 5:
        raise ValidationError('You have too many tags (5 allowed)')


class LongForm(forms.Form):
    FIELDS = "title content post_type tag_val".split()

    POST_CHOICES = [(Post.QUESTION, "Question"),
                    (Post.JOB, "Job Ad"),
                    (Post.TUTORIAL, "Tutorial"), (Post.TOOL, "Tool"),
                    (Post.FORUM, "Forum"), (Post.NEWS, "News"),
                    (Post.BLOG, "Blog"), (Post.PAGE, "Page")]

    title = forms.CharField(
        label="Post Title",
        max_length=200, min_length=10, validators=[valid_title],
        help_text="Descriptive titles promote better answers.")

    post_type = forms.ChoiceField(
        label="Post Type",
        choices=POST_CHOICES, help_text="Select a post type: Question, Forum, Job, Blog")

    tag_val = forms.CharField(
        label="Post Tags",
        required=True, validators=[valid_tag],
        help_text="Choose one or more tags to match the topic. To create a new tag just type it in and press ENTER.",
    )

    content = forms.CharField(widget=forms.Textarea,
                              min_length=80, max_length=15000,
                              label="Enter your post below")

    def __init__(self, *args, **kwargs):
        super(LongForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "post-form"
        self.helper.layout = Layout(
            Fieldset(
                'Post Form',
                Field('title'),
                Field('post_type'),
                Field('tag_val'),
                Field('content'),
            ),
            ButtonHolder(
                Submit('submit', 'Submit')
            )
        )


class ShortForm(forms.Form):
    FIELDS = ["content"]

    content = forms.CharField(widget=forms.Textarea, min_length=20)

    def __init__(self, *args, **kwargs):
        super(ShortForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Post',
                'content',
            ),
            ButtonHolder(
                Submit('submit', 'Submit')
            )
        )


def parse_tags(category, tag_val):
    pass


@login_required
@csrf_exempt
def external_post_handler(request):
    "This is used to pre-populate a new form submission"
    import hmac

    user = request.user
    home = reverse("home")
    name = request.REQUEST.get("name")

    if not name:
        messages.error(request, "Incorrect request. The name parameter is missing")
        return HttpResponseRedirect(home)

    try:
        secret = dict(settings.EXTERNAL_AUTH).get(name)
    except Exception, exc:
        logger.error(exc)
        messages.error(request, "Incorrect EXTERNAL_AUTH settings, internal exception")
        return HttpResponseRedirect(home)

    if not secret:
        messages.error(request, "Incorrect EXTERNAL_AUTH, no KEY found for this name")
        return HttpResponseRedirect(home)

    content = request.REQUEST.get("content")
    submit = request.REQUEST.get("action")
    digest1 = request.REQUEST.get("digest")
    digest2 = hmac.new(secret, content).hexdigest()

    if digest1 != digest2:
        messages.error(request, "digests does not match")
        return HttpResponseRedirect(home)

    # auto submit the post
    if submit:
        post = Post(author=user, type=Post.QUESTION)
        for field in settings.EXTERNAL_SESSION_FIELDS:
            setattr(post, field, request.REQUEST.get(field, ''))
        post.save()
        post.add_tags(post.tag_val)
        return HttpResponseRedirect(reverse("post-details", kwargs=dict(pk=post.id)))

    # pre populate the form
    sess = request.session
    sess[settings.EXTERNAL_SESSION_KEY] = dict()
    for field in settings.EXTERNAL_SESSION_FIELDS:
        sess[settings.EXTERNAL_SESSION_KEY][field] = request.REQUEST.get(field, '')

    return HttpResponseRedirect(reverse("new-post"))


class NewPost(LoginRequiredMixin, FormView):
    form_class = LongForm
    template_name = "post_edit.html"

    def get(self, request, *args, **kwargs):
        initial = dict()

        # Attempt to prefill from GET parameters
        for key in "title tag_val content".split():
            value = request.GET.get(key)
            if value:
                initial[key] = value

        # Attempt to prefill from external session
        sess = request.session
        if settings.EXTERNAL_SESSION_KEY in sess:
            for field in settings.EXTERNAL_SESSION_FIELDS:
                initial[field] = sess[settings.EXTERNAL_SESSION_KEY].get(field)
            del sess[settings.EXTERNAL_SESSION_KEY]

        form = self.form_class(initial=initial)
        return render(request, self.template_name, {'form': form})


    def post(self, request, *args, **kwargs):
        # Validating the form.
        form = self.form_class(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        # Valid forms start here.
        data = form.cleaned_data.get

        title = data('title')
        content = data('content')
        post_type = int(data('post_type'))
        tag_val = data('tag_val')

        post = Post(
            title=title, content=content, tag_val=tag_val,
            author=request.user, type=post_type,
        )
        post.save()

        # Triggers a new post save.
        post.add_tags(post.tag_val)

        messages.success(request, "%s created" % post.get_type_display())
        return HttpResponseRedirect(post.get_absolute_url())


class NewAnswer(LoginRequiredMixin, FormView):
    """
    Creates a new post.
    """
    form_class = ShortForm
    template_name = "post_edit.html"
    type_map = dict(answer=Post.ANSWER, comment=Post.COMMENT)
    post_type = None

    def get(self, request, *args, **kwargs):
        initial = {}

        # The parent id.
        pid = int(self.kwargs['pid'])
        #form_class = ShortForm if pid else LongForm
        form = self.form_class(initial=initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):

        pid = int(self.kwargs['pid'])

        # Find the parent.
        try:
            parent = Post.objects.get(pk=pid)
        except ObjectDoesNotExist, exc:
            messages.error(request, "The post does not exist. Perhaps it was deleted")
            HttpResponseRedirect("/")

        # Validating the form.
        form = self.form_class(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        # Valid forms start here.
        data = form.cleaned_data.get

        # Figure out the right type for this new post
        post_type = self.type_map.get(self.post_type)
        # Create a new post.
        post = Post(
            title=parent.title, content=data('content'), author=request.user, type=post_type,
            parent=parent,
        )

        messages.success(request, "%s created" % post.get_type_display())
        post.save()

        return HttpResponseRedirect(post.get_absolute_url())


class EditPost(LoginRequiredMixin, FormView):
    """
    Edits an existing post.
    """

    # The template_name attribute must be specified in the calling apps.
    template_name = "post_edit.html"
    form_class = LongForm

    def get(self, request, *args, **kwargs):
        initial = {}

        pk = int(self.kwargs['pk'])
        post = Post.objects.get(pk=pk)
        post = auth.post_permissions(request=request, post=post)

        # Check and exit if not a valid edit.
        if not post.is_editable:
            messages.error(request, "This user may not modify the post")
            return HttpResponseRedirect(reverse("home"))

        initial = dict(title=post.title, content=post.content, post_type=post.type, tag_val=post.tag_val)

        form_class = LongForm if post.is_toplevel else ShortForm
        form = form_class(initial=initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):

        pk = int(self.kwargs['pk'])
        post = Post.objects.get(pk=pk)
        post = auth.post_permissions(request=request, post=post)

        # For historical reasons we had posts with iframes
        # these cannot be edited because the content would be lost in the front end
        if "<iframe" in post.content:
            messages.error(request, "This post is not editable because of an iframe! Contact if you must edit it")
            return HttpResponseRedirect(post.get_absolute_url())

        # Check and exit if not a valid edit.
        if not post.is_editable:
            messages.error(request, "This user may not modify the post")
            return HttpResponseRedirect(post.get_absolute_url())

        # Posts with a parent are not toplevel
        form_class = LongForm if post.is_toplevel else ShortForm

        form = form_class(request.POST)
        if not form.is_valid():
            # Invalid form submission.
            return render(request, self.template_name, {'form': form})

        # Valid forms start here.
        data = form.cleaned_data

        # Set the form attributes.
        for field in form_class.FIELDS:
            setattr(post, field, data[field])

        # TODO: fix this oversight!
        post.type = int(data.get('post_type', post.type))

        # This is needed to validate some fields.
        post.save()

        if post.is_toplevel:
            post.add_tags(post.tag_val)

        # Update the last editing user.
        post.lastedit_user = request.user
        post.lastedit_date = datetime.utcnow().replace(tzinfo=utc)
        post.save()
        messages.success(request, "Post updated")

        return HttpResponseRedirect(post.get_absolute_url())

    def get_success_url(self):
        return reverse("user_details", kwargs=dict(pk=self.kwargs['pk']))


########NEW FILE########
__FILENAME__ = admin
from __future__ import print_function, unicode_literals, absolute_import, division

########NEW FILE########
__FILENAME__ = auth
__author__ = 'ialbert'
from django.conf import settings
from datetime import datetime, timedelta

def user_permissions(request, target):
    """
    Sets permission attributes on a user.

    The is_staff attribute is internal to Django. It allows a user
    to log into the Django admin. The role should be reserved to only
    those that manage the servers.
    """
    user = request.user

    # The user is the target.
    has_ownership = is_editable = False

    if user.is_authenticated():

        if user == target:
            # A user can do anything on their own account.
            has_ownership = is_editable = (user == target)

        elif target.is_administrator:
            # Admins cannot be moderated.
            is_editable = False

        elif user.is_administrator:
            # Admins can edit other users
            is_editable = True

        elif user.is_moderator and not target.is_moderator:
            # A moderator can edit other non-moderators.
            is_editable = True

    # Apply the attributes
    target.has_ownership = has_ownership
    target.is_editable = is_editable

    return target
########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'User'
        db.create_table(u'users_user', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('last_login', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('email', self.gf('django.db.models.fields.EmailField')(unique=True, max_length=255, db_index=True)),
            ('name', self.gf('django.db.models.fields.CharField')(default=u'', max_length=255)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('is_admin', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_staff', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('type', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('new_messages', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('badges', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('score', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('full_score', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('flair', self.gf('django.db.models.fields.CharField')(default=u'', max_length=15)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'], null=True)),
        ))
        db.send_create_signal(u'users', ['User'])

        # Adding model 'Profile'
        db.create_table(u'users_profile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['users.User'], unique=True)),
            ('uuid', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255, db_index=True)),
            ('last_login', self.gf('django.db.models.fields.DateTimeField')()),
            ('date_joined', self.gf('django.db.models.fields.DateTimeField')()),
            ('location', self.gf('django.db.models.fields.CharField')(default=u' ', max_length=255, blank=True)),
            ('website', self.gf('django.db.models.fields.URLField')(default=u'', max_length=255, blank=True)),
            ('scholar', self.gf('django.db.models.fields.CharField')(default=u'', max_length=255, blank=True)),
            ('my_tags', self.gf('django.db.models.fields.TextField')(default=u'', max_length=255, blank=True)),
            ('info', self.gf('django.db.models.fields.TextField')(default=u'', null=True, blank=True)),
            ('message_prefs', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'users', ['Profile'])


    def backwards(self, orm):
        # Deleting model 'User'
        db.delete_table(u'users_user')

        # Deleting model 'Profile'
        db.delete_table(u'users_profile')


    models = {
        u'sites.site': {
            'Meta': {'ordering': "(u'domain',)", 'object_name': 'Site', 'db_table': "u'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'users.profile': {
            'Meta': {'object_name': 'Profile'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('django.db.models.fields.TextField', [], {'default': "u''", 'null': 'True', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {}),
            'location': ('django.db.models.fields.CharField', [], {'default': "u' '", 'max_length': '255', 'blank': 'True'}),
            'message_prefs': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'my_tags': ('django.db.models.fields.TextField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'}),
            'scholar': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['users.User']", 'unique': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'website': ('django.db.models.fields.URLField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'})
        },
        u'users.user': {
            'Meta': {'object_name': 'User'},
            'badges': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'flair': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '15'}),
            'full_score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255'}),
            'new_messages': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sites.Site']", 'null': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['users']
########NEW FILE########
__FILENAME__ = 0002_auto__del_field_user_full_score__add_field_user_activity
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Profile.flag'
        db.add_column(u'users_profile', 'flag',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)

        # Deleting field 'User.full_score'
        db.delete_column(u'users_user', 'full_score')

        # Adding field 'User.activity'
        db.add_column(u'users_user', 'activity',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Profile.flag'
        db.delete_column(u'users_profile', 'flag')

        # Adding field 'User.full_score'
        db.add_column(u'users_user', 'full_score',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)

        # Deleting field 'User.activity'
        db.delete_column(u'users_user', 'activity')


    models = {
        u'sites.site': {
            'Meta': {'ordering': "(u'domain',)", 'object_name': 'Site', 'db_table': "u'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'users.profile': {
            'Meta': {'object_name': 'Profile'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {}),
            'flag': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('django.db.models.fields.TextField', [], {'default': "u''", 'null': 'True', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {}),
            'location': ('django.db.models.fields.CharField', [], {'default': "u' '", 'max_length': '255', 'blank': 'True'}),
            'message_prefs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'my_tags': ('django.db.models.fields.TextField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'}),
            'scholar': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['users.User']", 'unique': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'website': ('django.db.models.fields.URLField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'})
        },
        u'users.user': {
            'Meta': {'object_name': 'User'},
            'activity': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'badges': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'flair': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '15'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255'}),
            'new_messages': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sites.Site']", 'null': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['users']
########NEW FILE########
__FILENAME__ = 0003_auto__add_tag__add_field_profile_twitter_id__add_field_profile_watch_t
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'EmailList'
        db.create_table(u'users_emaillist', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')()),
            ('email', self.gf('django.db.models.fields.EmailField')(unique=True, max_length=255, db_index=True)),
            ('type', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'users', ['EmailList'])

        # Adding model 'Tag'
        db.create_table(u'users_tag', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.TextField')(max_length=50, db_index=True)),
        ))
        db.send_create_signal(u'users', ['Tag'])

        # Adding field 'Profile.twitter_id'
        db.add_column(u'users_profile', 'twitter_id',
                      self.gf('django.db.models.fields.CharField')(default=u'', max_length=255, blank=True),
                      keep_default=False)

        # Adding field 'Profile.watched_tags'
        db.add_column(u'users_profile', 'watched_tags',
                      self.gf('django.db.models.fields.CharField')(default=u'', max_length=100, blank=True),
                      keep_default=False)

        # Adding M2M table for field tags on 'Profile'
        m2m_table_name = db.shorten_name(u'users_profile_tags')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('profile', models.ForeignKey(orm[u'users.profile'], null=False)),
            ('tag', models.ForeignKey(orm[u'users.tag'], null=False))
        ))
        db.create_unique(m2m_table_name, ['profile_id', 'tag_id'])


    def backwards(self, orm):
        # Deleting model 'EmailList'
        db.delete_table(u'users_emaillist')

        # Deleting model 'Tag'
        db.delete_table(u'users_tag')

        # Deleting field 'Profile.twitter_id'
        db.delete_column(u'users_profile', 'twitter_id')

        # Deleting field 'Profile.watched_tags'
        db.delete_column(u'users_profile', 'watched_tags')

        # Removing M2M table for field tags on 'Profile'
        db.delete_table(db.shorten_name(u'users_profile_tags'))


    models = {
        u'sites.site': {
            'Meta': {'ordering': "(u'domain',)", 'object_name': 'Site', 'db_table': "u'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'users.emaillist': {
            'Meta': {'object_name': 'EmailList'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'users.profile': {
            'Meta': {'object_name': 'Profile'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {}),
            'flag': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'info': ('django.db.models.fields.TextField', [], {'default': "u''", 'null': 'True', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {}),
            'location': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'}),
            'message_prefs': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'my_tags': ('django.db.models.fields.TextField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'}),
            'scholar': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['users.Tag']", 'symmetrical': 'False', 'blank': 'True'}),
            'twitter_id': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['users.User']", 'unique': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'watched_tags': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '100', 'blank': 'True'}),
            'website': ('django.db.models.fields.URLField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'})
        },
        u'users.tag': {
            'Meta': {'object_name': 'Tag'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'max_length': '50', 'db_index': 'True'})
        },
        u'users.user': {
            'Meta': {'object_name': 'User'},
            'activity': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'badges': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'flair': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '15'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255'}),
            'new_messages': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sites.Site']", 'null': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'type': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['users']
########NEW FILE########
__FILENAME__ = models
from __future__ import print_function, unicode_literals, absolute_import, division
import logging
from django import forms
from django.db import models
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, UserManager
from django.utils.timezone import utc
from biostar.apps import util
import bleach
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from datetime import datetime, timedelta

# HTML sanitization parameters.
ALLOWED_TAGS = bleach.ALLOWED_TAGS + settings.ALLOWED_TAGS
ALLOWED_STYLES = bleach.ALLOWED_STYLES + settings.ALLOWED_STYLES
ALLOWED_ATTRIBUTES = dict(bleach.ALLOWED_ATTRIBUTES)
ALLOWED_ATTRIBUTES.update(settings.ALLOWED_ATTRIBUTES)

logger = logging.getLogger(__name__)

def now():
    return datetime.utcnow().replace(tzinfo=utc)

class LocalManager(UserManager):

    def get_users(self, sort, limit, q, user):
        sort = const.USER_SORT_MAP.get(sort, None)
        days = const.POST_LIMIT_MAP.get(limit, 0)

        if q:
            query = self.filter(name__icontains=q)
        else:
            query = self

        if days:
            delta = const.now() - timedelta(days=days)
            query = self.filter(profile__last_login__gt=delta)

        if user.is_authenticated() and user.is_moderator:
            query = query.select_related("profile").order_by(sort)
        else:
            query = query.exclude(status=User.BANNED).select_related("profile").order_by(sort)

        return query

class User(AbstractBaseUser):
    # Class level constants.
    USER, MODERATOR, ADMIN, BLOG = range(4)
    TYPE_CHOICES = [(USER, "User"), (MODERATOR, "Moderator"), (ADMIN, "Admin"), (BLOG, "Blog")]

    NEW_USER, TRUSTED, SUSPENDED, BANNED = range(4)
    STATUS_CHOICES = ((NEW_USER, 'New User'), (TRUSTED, 'Trusted'), (SUSPENDED, 'Suspended'), (BANNED, 'Banned'))

    # Required by Django.
    USERNAME_FIELD = 'email'

    objects = LocalManager()

    # Default information on every user.
    email = models.EmailField(verbose_name='Email', db_index=True, max_length=255, unique=True)
    name = models.CharField(verbose_name='Name', max_length=255, default="", blank=False)

    # Fields used by the Django admin.
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    # This designates a user types and with that permissions.
    type = models.IntegerField(choices=TYPE_CHOICES, default=USER)

    # This designates a user statuses on whether they are allowed to log in.
    status = models.IntegerField(choices=STATUS_CHOICES, default=NEW_USER)

    # The number of new messages for the user.
    new_messages = models.IntegerField(default=0)

    # The number of badges for the user.
    badges = models.IntegerField(default=0)

    # Activity score computed over a shorter period.
    score = models.IntegerField(default=0)

    # User's recent activity level.
    activity = models.IntegerField(default=0)

    # Display next to a user name.
    flair = models.CharField(verbose_name='Flair', max_length=15, default="")

    # The site this users belongs to.
    site = models.ForeignKey(Site, null=True)

    @property
    def is_moderator(self):
        if self.is_authenticated():
            return self.type == User.MODERATOR or self.type == User.ADMIN
        else:
            return False

    @property
    def is_administrator(self):
        # The site administrator is different from the Django admin.
        if self.is_authenticated():
            return self.type == User.ADMIN
        else:
            return False

    @property
    def is_trusted(self):
        return self.status == User.TRUSTED

    @property
    def is_suspended(self):
        return self.status == User.SUSPENDED or self.status == User.BANNED

    def get_full_name(self):
        # The user is identified by their email address
        return self.name or self.email

    def get_short_name(self):
        # The user is identified by their email address
        return self.name or self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    def save(self, *args, **kwargs):
        "Actions that need to be performed on every user save."

        if not self.name:
            # Name should be set.
            self.name = self.email.split("@")[0]

        super(User, self).save(*args, **kwargs)

    @property
    def scaled_score(self):
        "People like to see big scores."
        return self.score * 10

    def __unicode__(self):
        return "%s: %s (%s)" % (self.name, self.email, self.id)

    def get_absolute_url(self):
        url = reverse("user-details", kwargs=dict(pk=self.id))
        return url

# This contains the notification types.
from biostar import const

class EmailList(models.Model):
    "The list of emails that opted in receiving emails"
    email = models.EmailField(verbose_name='Email', db_index=True, max_length=255, unique=True)
    type = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    date = models.DateTimeField(auto_created=True)

class Tag(models.Model):
    name = models.TextField(max_length=50, db_index=True)


# Default message preferences.
MESSAGE_PREF_MAP = dict(
    local=const.LOCAL_MESSAGE, default=const.DEFAULT_MESSAGES, email=const.EMAIL_MESSAGE
)
MESSAGE_PREFS = MESSAGE_PREF_MAP.get(settings.DEFAULT_MESSAGE_PREF, const.LOCAL_MESSAGE)

class Profile(models.Model):
    """
    Maintains information that does not always need to be retreived whe a user is accessed.
    """
    LOCAL_MESSAGE, EMAIL_MESSAGE = const.LOCAL_MESSAGE, const.EMAIL_MESSAGE

    TYPE_CHOICES = const.MESSAGING_TYPE_CHOICES

    user = models.OneToOneField(User)

    # Globally unique id used to identify the user in a private feeds
    uuid = models.CharField(null=False, db_index=True, unique=True, max_length=255)

    # The last visit by the user.
    last_login = models.DateTimeField()

    # The last visit by the user.
    date_joined = models.DateTimeField()

    # User provided location.
    location = models.CharField(default="", max_length=255, blank=True)

    # User provided website.
    website = models.URLField(default="", max_length=255, blank=True)

    # Google scholar ID
    scholar = models.CharField(default="", max_length=255, blank=True)

    # Twitter ID
    twitter_id = models.CharField(default="", max_length=255, blank=True)

    # This field is used to select content for the user.
    my_tags = models.TextField(default="", max_length=255, blank=True)

    # Description provided by the user html.
    info = models.TextField(default="", null=True, blank=True)

    # The default notification preferences.
    message_prefs = models.IntegerField(choices=TYPE_CHOICES, default=MESSAGE_PREFS)

    # This stores binary flags on users. Their usage is to
    # allow easy subselection of various subsets of users.
    flag = models.IntegerField(default=0)

    # The tag value is the canonical form of the post's tags
    watched_tags = models.CharField(max_length=100, default="", blank=True)

    # The tag set is built from the watch_tag string and is used to trigger actions
    # when a post that matches this tag is set
    tags = models.ManyToManyField(Tag, blank=True, )

    def parse_tags(self):
        return util.split_tags(self.tag_val)

    def clear_data(self):
        "Actions to take when suspending or banning users"
        self.website = self.twitter_id = self.info = self.location = ''
        self.save()

    def add_tags(self, text):
        text = text.strip()
        # Sanitize the tag value
        self.tag_val = bleach.clean(text, tags=[], attributes=[], styles={}, strip=True)
        # Clear old tags
        self.tags.clear()
        tags = [Tag.objects.get_or_create(name=name)[0] for name in self.parse_tags()]
        self.tags.add(*tags)

    def save(self, *args, **kwargs):

        # Clean the info fields.
        self.info = bleach.clean(self.info, tags=ALLOWED_TAGS,
                                 attributes=ALLOWED_ATTRIBUTES, styles=ALLOWED_STYLES)


        # Strip whitespace from location string
        self.location = self.location.strip()

        if not self.id:
            # This runs only once upon object creation.
            self.uuid = util.make_uuid()
            self.date_joined = self.date_joined or now()
            self.last_login = self.date_joined

        super(Profile, self).save(*args, **kwargs)

    def __unicode__(self):
        return "%s" % self.user.name

    @property
    def filled(self):
        has_location = bool(self.location.strip())
        has_info = bool(self.info.strip())
        return has_location and has_info

    @staticmethod
    def auto_create(sender, instance, created, *args, **kwargs):
        "Should run on every user creation."
        if created:
            prof = Profile(user=instance)
            prof.save()



class UserCreationForm(forms.ModelForm):
    """A form for creating new users."""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('email', 'name')

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """A form for updating users."""
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ['email', 'password', 'name', 'type', 'is_active', 'is_admin', 'is_staff']

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]


class ProfileInline(admin.StackedInline):
    model = Profile
    fields = ["location", "website", "scholar", "twitter_id", "message_prefs", "my_tags", "watched_tags", "info"]


class BiostarUserAdmin(UserAdmin):
    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = ('name', 'id', 'email', 'type', 'is_admin', 'is_staff')
    list_filter = ('is_admin',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('name', 'type')}),
        ('Permissions', {'fields': ('is_admin', 'is_staff')}),
    )
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'type', 'password1', 'password2')}
        ),
    )
    search_fields = ('email', 'name',)
    ordering = ('id', 'name', 'email',)
    filter_horizontal = ()
    inlines = [ProfileInline]

# Register in the admin interface.
admin.site.register(User, BiostarUserAdmin)

# Data signals
from django.db.models.signals import post_save

post_save.connect(Profile.auto_create, sender=User)

NEW_USER_WELCOME_TEMPLATE = "messages/new_user_welcome.html"

def user_create_messages(sender, instance, created, *args, **kwargs):
    "The actions to undertake when creating a new post"
    from biostar.apps.messages.models import Message, MessageBody
    from biostar.apps.util import html
    from biostar.const import now

    user = instance
    if created:
        # Create a welcome message to a user
        # We do this so that tests pass, there is no admin user there
        authors = User.objects.filter(is_admin=True) or [ user ]
        author = authors[0]

        title = "Welcome!"
        content = html.render(name=NEW_USER_WELCOME_TEMPLATE, user=user)
        body = MessageBody.objects.create(author=author, subject=title,
                                          text=content, sent_at=now())
        message = Message(user=user, body=body, sent_at=body.sent_at)
        message.save()

# Creates a message to everyone involved
post_save.connect(user_create_messages, sender=User, dispatch_uid="user-create_messages")

########NEW FILE########
__FILENAME__ = tests
"""
User related tests.

These will execute when you run "manage.py test".
"""
from __future__ import print_function, unicode_literals, absolute_import, division
import logging
from django.conf import settings
from biostar.apps.users.models import User, Profile
from django.test import TestCase

logging.disable(logging.INFO)

class UserTest(TestCase):
    def test_user_creation(self):
        """
        Testing users and their profile creation
        """
        eq = self.assertEqual

        # Create a new usr
        user = User.objects.create(email="foo@bar.com")

        # A user will automatically get a profile
        eq (user.profile.user_id, user.id)

########NEW FILE########
__FILENAME__ = views
# Create your views here.
from django.shortcuts import render_to_response
from django.views.generic import TemplateView, DetailView, ListView, FormView, UpdateView
from .models import User
from . import auth
from django import forms
from django.core.urlresolvers import reverse
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, Submit, ButtonHolder, Div
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.validators import validate_email
from biostar import const
from braces.views import LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from biostar.apps import util
import logging, hmac

logger = logging.getLogger(__name__)


class UserEditForm(forms.Form):
    name = forms.CharField(help_text="The name displayed on the site (required)")

    email = forms.EmailField(help_text="Your email, it will not be visible to other users (required)")

    location = forms.CharField(required=False,
                               help_text="Country/City/Institution (recommended)")

    website = forms.URLField(required=False, max_length=200,
                             help_text="The URL to your website (optional)")

    twitter_id = forms.CharField(required=False, max_length=15,
                                 help_text="Your twitter id (optional)")

    scholar = forms.CharField(required=False, max_length=15,
                              help_text="Your Google Scholar ID (optional)")

    my_tags = forms.CharField(max_length=200, required=False,
                              help_text="Post with tags listed here will show up in the My Tags tab. Use a comma to separate tags. Add a <code>!</code> to remove a tag. Example: <code>galaxy, bed, solid!</code> (optional)")

    watched_tags = forms.CharField(max_length=200, required=False,
                                   help_text="Get email when a post matching the tag is posted. Example: <code>minia, bedops, breakdancer, music</code>.")

    message_prefs = forms.ChoiceField(required=True, choices=const.MESSAGING_TYPE_CHOICES, label="Notifications",
                                      help_text="Where to send notifications. Default mode sends email on followups to questions you've created.")

    info = forms.CharField(widget=forms.Textarea, required=False, label="Add some information about yourself",
                           help_text="A brief description about yourself (recommended)")

    def __init__(self, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.error_text_inline = False
        self.helper.help_text_inline = True
        self.helper.layout = Layout(
            Fieldset(
                'Update your profile',
                Div(
                    Div('name', ),
                    Div('email', ),
                    Div('location'),
                    Div('website'),
                    Div('twitter_id'),
                    Div('scholar'),
                    Div('message_prefs'),
                    Div('my_tags'),
                    Div('watched_tags'),
                    css_class="col-md-offset-1 col-md-10",
                ),
                Div('info', css_class="col-md-12"),
            ),
            ButtonHolder(
                Submit('submit', 'Submit')
            )
        )


class EditUser(LoginRequiredMixin, FormView):
    """
    Edits a user.
    """

    # The template_name attribute must be specified in the calling apps.
    template_name = ""
    form_class = UserEditForm
    user_fields = "name email".split()
    prof_fields = "location website info scholar my_tags watched_tags twitter_id message_prefs".split()

    def get(self, request, *args, **kwargs):
        target = User.objects.get(pk=self.kwargs['pk'])
        target = auth.user_permissions(request=request, target=target)
        if not target.has_ownership:
            messages.error(request, "Only owners may edit their profiles")
            return HttpResponseRedirect(reverse("home"))

        initial = {}

        for field in self.user_fields:
            initial[field] = getattr(target, field)

        for field in self.prof_fields:
            initial[field] = getattr(target.profile, field)

        form = self.form_class(initial=initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        target = User.objects.get(pk=self.kwargs['pk'])
        target = auth.user_permissions(request=request, target=target)
        profile = target.profile

        # The essential authentication step.
        if not target.has_ownership:
            messages.error(request, "Only owners may edit their profiles")
            return HttpResponseRedirect(reverse("home"))

        form = self.form_class(request.POST)
        if form.is_valid():
            f = form.cleaned_data

            if User.objects.filter(email=f['email']).exclude(pk=request.user.id):
                # Changing email to one that already belongs to someone else.
                messages.error(request, "The email that you've entered is already registered to another user!")
                return render(request, self.template_name, {'form': form})

            # Valid data. Save model attributes and redirect.
            for field in self.user_fields:
                setattr(target, field, f[field])

            for field in self.prof_fields:
                setattr(profile, field, f[field])

            target.save()
            profile.add_tags(profile.watched_tags)
            profile.save()
            messages.success(request, "Profile updated")
            return HttpResponseRedirect(self.get_success_url())

        # There is an error in the form.
        return render(request, self.template_name, {'form': form})

    def get_success_url(self):
        return reverse("user-details", kwargs=dict(pk=self.kwargs['pk']))


def test_login(request):
    # Used during debugging external authentication
    response = redirect("/")
    for name, key in settings.EXTERNAL_AUTH:
        email = "foo@bar.com"
        digest = hmac.new(key, email).hexdigest()
        value = "%s:%s" % (email, digest)
        response.set_cookie(name, value)
        messages.info(request, "set cookie %s, %s, %s" % (name, key, value))
    return response


def external_logout(request):
    "This is required to invalidate the external logout cookies"
    logout(request)
    url = settings.EXTERNAL_LOGOUT_URL or 'account_logout'
    response = redirect(url)
    for name, key in settings.EXTERNAL_AUTH:
        response.delete_cookie(name)
    return response


def external_login(request):
    "This is required to allow external login to proceed"
    url = settings.EXTERNAL_LOGIN_URL or 'account_login'
    response = redirect(url)
    return response

class EmailListForm(forms.Form):
    email = forms.EmailField(help_text="Your email")
    subs  = forms.BooleanField(help_text="Subscribe")

class EmailListView(FormView):
    form_class = EmailListForm
    template_name = "email_list_form.html"

    def get(self, request,  *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})


# Adding a captcha enabled form
from allauth.account.views import SignupForm, SignupView
from biostar.apps.util.captcha.fields import MathCaptchaField


class CaptchaForm(SignupForm):
    captcha = MathCaptchaField()


class CaptchaView(SignupView):
    form_class = CaptchaForm

    def get_form_class(self):
        # This is to allow tests to override the form class during testing.
        if settings.CAPTCHA:
            return CaptchaForm
        else:
            return SignupForm


class EmailListSignup(FormView):
    """
    Edits a user.
    """
########NEW FILE########
__FILENAME__ = fields
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

from .widgets import MathCaptchaWidget
from .utils import hash_answer


class MathCaptchaField(forms.MultiValueField):
    default_error_messages = {
        'invalid': _('Please check your math and try again.'),
        'invalid_number': _('Enter a whole number.'),
    }

    def __init__(self, *args, **kwargs):
        self._ensure_widget(kwargs)
        kwargs['required'] = True
        # we skip MultiValueField handling of fields and setup ourselves
        super(MathCaptchaField, self).__init__((), *args, **kwargs)
        self._setup_fields()

    def compress(self, data_list):
        """Compress takes the place of clean with MultiValueFields"""
        if data_list:
            answer = data_list[0]
            real_hashed_answer = data_list[1]
            hashed_answer = hash_answer(answer)
            if hashed_answer != real_hashed_answer:
                raise ValidationError(self.error_messages['invalid'])
        return None

    def _ensure_widget(self, kwargs):
        widget_params = self._extract_widget_params(kwargs)

        if 'widget' not in kwargs or not kwargs['widget']:
            kwargs['widget'] = MathCaptchaWidget(**widget_params)
        elif widget_params:
            msg = '%s must be omitted when widget is provided for %s.'
            msg = msg % (' and '.join(list(widget_params)),
                         self.__class__.__name__)
            raise TypeError(msg)

    def _extract_widget_params(self, kwargs):
        params = {}
        for key in ('start_int', 'end_int'):
            if key in kwargs:
                params[key] = kwargs.pop(key)
        return params

    def _setup_fields(self):
        error_messages = {'invalid': self.error_messages['invalid_number']}
        # set fields
        fields = (
            forms.IntegerField(error_messages=error_messages,
                               localize=self.localize),
            forms.CharField()
        )
        for field in fields:
            field.required = False
        self.fields = fields

########NEW FILE########
__FILENAME__ = utils
from __future__ import absolute_import
from __future__ import unicode_literals

from random import randint, choice
from hashlib import sha1

from django.conf import settings
from django.utils import six

MULTIPLY = '*'
ADD = '+'
SUBTRACT = '-'
CALCULATIONS = {
    MULTIPLY: lambda a, b: a * b,
    ADD: lambda a, b: a + b,
    SUBTRACT: lambda a, b: a - b,
}
OPERATORS = tuple(CALCULATIONS)


def hash_answer(value):
    answer = six.text_type(value)
    to_encode = (settings.SECRET_KEY + answer).encode('utf-8')
    return sha1(to_encode).hexdigest()


def get_operator():
    return choice(OPERATORS)


def get_numbers(start_int, end_int, operator):
    x = randint(start_int, end_int)
    y = randint(start_int, end_int)

    #avoid negative results for subtraction
    if y > x and operator == SUBTRACT:
        x, y = y, x

    return x, y


def calculate(x, y, operator):
    func = CALCULATIONS[operator]
    total = func(x, y)
    return total


########NEW FILE########
__FILENAME__ = widgets
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from django.template.defaultfilters import mark_safe
from django.utils.translation import ugettext_lazy as _

from .utils import hash_answer, get_operator, get_numbers, calculate


class MathCaptchaWidget(forms.MultiWidget):
    def __init__(self, start_int=1, end_int=10, question_tmpl=None,
                 question_class=None, attrs=None):
        self.start_int, self.end_int = self.verify_numbers(start_int, end_int)
        self.question_class = question_class or 'captcha-question'
        self.question_tmpl = (
            question_tmpl or _('What is %(num1)i %(operator)s %(num2)i?'))
        self.question_html = None
        widget_attrs = {'size': '5'}
        widget_attrs.update(attrs or {})
        widgets = (
            # this is the answer input field
            forms.TextInput(attrs=widget_attrs),

            # this is the hashed answer field to compare to
            forms.HiddenInput()
        )
        super(MathCaptchaWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        return [None, None]

    def format_output(self, rendered_widgets):
        output = super(MathCaptchaWidget, self).format_output(rendered_widgets)
        output = '%s%s' % (self.question_html, output)
        return output
    
    def render(self, name, value, attrs=None):
        # hash answer and set as the hidden value of form
        hashed_answer = self.generate_captcha()
        value = ['', hashed_answer]
        
        return super(MathCaptchaWidget, self).render(name, value, attrs=attrs)
    
    def generate_captcha(self):
        # get operator for calculation
        operator = get_operator()

        # get integers for calculation
        x, y = get_numbers(self.start_int, self.end_int, operator)
        
        # set question to display in output
        self.set_question(x, y, operator)

        # preform the calculation
        total = calculate(x, y, operator)

        return hash_answer(total)

    def set_question(self, x, y, operator):
        # make multiplication operator more human-readable
        operator_for_label = '&times;' if operator == '*' else operator
        question = self.question_tmpl % {
            'num1': x,
            'operator': operator_for_label,
            'num2': y
        }

        html = '<span class="%s">%s</span>' % (self.question_class, question)
        self.question_html = mark_safe(html)

    def verify_numbers(self, start_int, end_int):
        start_int, end_int = int(start_int), int(end_int)
        if start_int < 0 or end_int < 0:
            raise Warning('MathCaptchaWidget requires positive integers '
                          'for start_int and end_int.')
        elif end_int < start_int:
            raise Warning('MathCaptchaWidget requires end_int be greater '
                          'than start_int.')
        return start_int, end_int


########NEW FILE########
__FILENAME__ = email_reply_parser
import re

"""
email_reply_parser is a python library port of GitHub's Email Reply Parser.

For more information, visit https://github.com/zapier/email-reply-parser

Copyright (c) 2012 Zapier

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify, merge,
publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons
to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies
or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

class EmailReplyParser(object):
    """ Represents a email message that is parsed.
    """

    @staticmethod
    def read(text):
        """ Factory method that splits email into list of fragments

            text - A string email body

            Returns an EmailMessage instance
        """
        return EmailMessage(text).read()

    @staticmethod
    def parse_reply(text):
        """ Provides the reply portion of email.

            text - A string email body

            Returns reply body message
        """
        return EmailReplyParser.read(text).reply


class EmailMessage(object):
    """ An email message represents a parsed email body.
    """

    SIG_REGEX = r'(--|__|-\w)|(^Sent from my (\w+\s*){1,3})'
    QUOTE_HDR_REGEX = r'^:etorw.*nO'
    MULTI_QUOTE_HDR_REGEX = r'(On\s.*?wrote:)'
    QUOTED_REGEX = r'(>+)'

    def __init__(self, text):
        self.fragments = []
        self.fragment = None
        self.text = text.replace('\r\n', '\n')
        self.found_visible = False

    def read(self):
        """ Creates new fragment for each line
            and labels as a signature, quote, or hidden.

            Returns EmailMessage instance
        """

        self.found_visible = False

        is_multi_quote_header = re.search(self.MULTI_QUOTE_HDR_REGEX, self.text, re.MULTILINE | re.DOTALL)
        if is_multi_quote_header:
            expr = re.compile(self.MULTI_QUOTE_HDR_REGEX, flags=re.DOTALL)
            self.text = expr.sub(
                is_multi_quote_header.groups()[0].replace('\n', ''),
                self.text)

        self.lines = self.text.split('\n')
        self.lines.reverse()

        for line in self.lines:
            self._scan_line(line)

        self._finish_fragment()

        self.fragments.reverse()

        return self

    @property
    def reply(self):
        """ Captures reply message within email
        """
        reply = []
        for f in self.fragments:
            if not (f.hidden or f.quoted):
                reply.append(f.content)
        return '\n'.join(reply)

    def _scan_line(self, line):
        """ Reviews each line in email message and determines fragment type

            line - a row of text from an email message
        """

        line.strip('\n')

        if re.match(self.SIG_REGEX, line):
            line.lstrip()

        is_quoted = re.match(self.QUOTED_REGEX, line) != None

        if self.fragment and len(line.strip()) == 0:
            if re.match(self.SIG_REGEX, self.fragment.lines[-1]):
                self.fragment.signature = True
                self._finish_fragment()

        if self.fragment and ((self.fragment.quoted == is_quoted)
                              or (self.fragment.quoted and (self.quote_header(line) or len(line.strip()) == 0))):

            self.fragment.lines.append(line)
        else:
            self._finish_fragment()
            self.fragment = Fragment(is_quoted, line)

    def quote_header(self, line):
        """ Determines whether line is part of a quoted area

            line - a row of the email message

            Returns True or False
        """
        return re.match(self.QUOTE_HDR_REGEX, line[::-1]) != None

    def _finish_fragment(self):
        """ Creates fragment
        """

        if self.fragment:
            self.fragment.finish()
            if not self.found_visible:
                if self.fragment.quoted \
                        or self.fragment.signature \
                        or (len(self.fragment.content.strip()) == 0):

                    self.fragment.hidden = True
                else:
                    self.found_visible = True
            self.fragments.append(self.fragment)
        self.fragment = None


class Fragment(object):
    """ A Fragment is a part of
        an Email Message, labeling each part.
    """

    def __init__(self, quoted, first_line):
        self.signature = False
        self.hidden = False
        self.quoted = quoted
        self._content = None
        self.lines = [first_line]

    def finish(self):
        """ Creates block of content with lines
            belonging to fragment.
        """
        self.lines.reverse()
        self._content = '\n'.join(self.lines)
        self.lines = None

    @property
    def content(self):
        return self._content

########NEW FILE########
__FILENAME__ = html
import bleach

from django.conf import settings
from django.template import loader, Context, Template, RequestContext
import re
import bleach
import logging

logger = logging.getLogger(__name__)

ALLOWED_TAGS = bleach.ALLOWED_TAGS + settings.ALLOWED_TAGS
ALLOWED_STYLES = bleach.ALLOWED_STYLES + settings.ALLOWED_STYLES
ALLOWED_ATTRIBUTES = dict(bleach.ALLOWED_ATTRIBUTES)
ALLOWED_ATTRIBUTES.update(settings.ALLOWED_ATTRIBUTES)

# Matching patterns will be filled in with post title or user name
USER_PATTERN = r"http(s)?://%s/u/(?P<uid>(\d+))" % settings.SITE_DOMAIN
POST_PATTERN1 = r"http(s)?://%s/p/(?P<uid>(\d+))" % settings.SITE_DOMAIN
POST_PATTERN2 = r"http(s)?://%s/p/\d+/\#(?P<uid>(\d+))" % settings.SITE_DOMAIN

# Matches gists that may be embeded
GIST_PATTERN = r"https://gist.github.com/(?P<uid>([\w/]+))"

# Matches Youtube video links.
YOUTUBE_PATTERN = r"http(s)?://www.youtube.com/watch\?v=(?P<uid>(\w+))"

USER_RE = re.compile(USER_PATTERN)
POST_RE1 = re.compile(POST_PATTERN1)
POST_RE2 = re.compile(POST_PATTERN2)
GIST_RE = re.compile(GIST_PATTERN)
YOUTUBE_RE = re.compile(YOUTUBE_PATTERN)

def clean(text):
    "Sanitize text with no other substitutions"
    html = bleach.clean(text, tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES, styles=ALLOWED_STYLES)
    return html

def parse_html(text):
    "Sanitize text and expand links to match content"
    from biostar.apps.users.models import User
    from biostar.apps.posts.models import Post

    # This will collect the objects that could be embedded
    embed = []

    def internal_links(attrs, new=False):
        "Matches a user"
        try:
            href = attrs['href']

            # Try the patterns
            patt1 = POST_RE1.search(href)
            patt2 = POST_RE2.search(href)
            patt = patt1 or patt2
            if patt:
                uid = patt.group("uid")
                attrs['_text'] = Post.objects.get(id=uid).title

            # Try the user patterns
            patt3 = USER_RE.search(href)
            if patt3:
                uid = patt3.group("uid")
                attrs['_text'] = User.objects.get(id=uid).name

        except Exception, exc:
            logger.error(exc)
        return attrs

    def embedder(attrs, new):
        # This is an existing <a> tag, leave it be.
        if not new:
            return attrs

        href = attrs['_text']

        # Don't linkify non http links
        if href[:4] not in ('http', 'ftp:'):
            return None

        # Try the gist embedding patterns
        targets = [
            (GIST_RE, '<script src="https://gist.github.com/%s.js"></script>'),
            (YOUTUBE_RE, '<iframe width="420" height="315" src="//www.youtube.com/embed/%s" frameborder="0" allowfullscreen></iframe>')
        ]

        for regex, text in targets:
            patt = regex.search(href)
            if patt:
                uid = patt.group("uid")
                obj = text % uid
                embed.append( (uid, obj) )
                attrs['_text'] = uid
                attrs['href'] = uid
                if 'rel' in attrs:
                    del attrs['rel']

        return attrs

    CALLBACKS = bleach.DEFAULT_CALLBACKS + [embedder, internal_links]

    html = bleach.clean(text, tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES, styles=ALLOWED_STYLES)

    try:
        html = bleach.linkify(html, callbacks=CALLBACKS, skip_pre=True)
        # embed the objects
        for uid, obj in embed:
            emb_patt = '<a href="%s">%s</a>' % (uid, uid)
            html = html.replace(emb_patt, obj)
    except Exception, exc:
        logger.error("*** %s" % exc)

    return html

def strip_tags(text):
    "Strip html tags from text"
    text = bleach.clean(text, tags=[], attributes=[], styles={}, strip=True)
    return text

def render(name, **kwds):
    "Helper function to render a template"
    tmpl = loader.get_template(name)
    cont = Context(kwds)
    page = tmpl.render(cont)
    return page

def test():
    pass

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = tests
"""
Utility related tests.

These will execute when you run "manage.py test".
"""
from __future__ import print_function, unicode_literals, absolute_import, division

import bleach, logging
from django.conf import settings
from biostar.apps.util import html

from django.test import TestCase

logging.disable(logging.INFO)
# The pattern that matches the user link.

class UtilTest(TestCase):

    def test_bleach(self):
        "Testing html cleaning"
        eq = self.assertEqual

        inp = '''http://www.psu.edu'''
        exp = '''<a href="http://www.psu.edu" rel="nofollow">http://www.psu.edu</a>'''
        got = bleach.linkify(inp)
        #eq(got, exp)

        inp = '''http://%s/u/123''' % settings.SITE_DOMAIN
        exp = '''<a href="http://www.psu.edu" rel="nofollow">http://www.psu.edu</a>'''
        got = bleach.linkify(inp)
        #eq(got, exp)

        #print (bleach.DEFAULT_CALLBACKS)





########NEW FILE########
__FILENAME__ = views
# Create your views here.
import os
from django import forms
from django.views.generic import  UpdateView, DetailView
from django.contrib.flatpages.models import FlatPage
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.conf import settings

import logging

logger = logging.getLogger(__name__)

def abspath(*args):
    """Generates absolute paths"""
    return os.path.abspath(os.path.join(*args))


########NEW FILE########
__FILENAME__ = awards
from __future__ import absolute_import
from django.conf import settings

from .celery import app

import logging

logger = logging.getLogger(__name__)


def init_awards():
    "Initializes the badges"
    from biostar.apps.badges.models import Badge
    from biostar.apps.badges.award_defs import ALL_AWARDS

    for obj in ALL_AWARDS:
        badge, created = Badge.objects.get_or_create(name=obj.name)

        # Badge descriptions may change.
        if badge.desc != obj.desc:
            badge.desc = obj.desc
            badge.icon = obj.icon
            badge.type = obj.type
            badge.save()

        if created:
            logger.info("initializing badge %s" % badge)


@app.task
# Tries to award a badge to the user
def check_user_profile(ip, user):
    import urllib2, json
    if not user.profile.location:
        try:
            url = "http://api.hostip.info/get_json.php?ip=%s" % ip
            logger.info(url)
            f = urllib2.urlopen(url, timeout=3)
            data = json.loads(f.read())
            f.close()
            location = data.get('country_name', '').title()
            if "unknown" not in location.lower():
                user.profile.location = location
                user.profile.save()
        except Exception, exc:
            logger.error(exc)


@app.task
# Tries to award a badge to the user
def create_user_award(user):
    from biostar.apps.users.models import User
    from biostar.apps.posts.models import Post
    from biostar.apps.badges.models import Badge, Award
    from biostar.apps.badges.award_defs import ALL_AWARDS

    # Update user status.
    if (user.status == User.NEW_USER) and (user.score > 10):
        user.status = User.TRUSTED
        user.save()

    # Debug only
    #Award.objects.all().delete()

    # The awards the user has won at this point
    awards = dict()
    for award in Award.objects.filter(user=user).select_related('badge'):
        awards.setdefault(award.badge.name, []).append(award)

    # Shorcut function to get the award count
    get_award_count = lambda name: len(awards[name]) if name in awards else 0

    for obj in ALL_AWARDS:

        # How many times has been awarded
        seen_count = get_award_count(obj.name)

        # How many times should it been awarded
        valid_targets = obj.validate(user)

        # Keep that targets that have not been awarded
        valid_targets = valid_targets[seen_count:]

        # Some limit on awards
        valid_targets = valid_targets[:100]

        # Award the targets
        for target in valid_targets:
            # Update the badge counts.
            badge = Badge.objects.get(name=obj.name)
            badge.count += 1
            badge.save()

            if isinstance(target, Post):
                context = '<a href="%s">%s</a>' % (target.get_absolute_url(), target.title)
            else:
                context = ""

            date = user.profile.last_login
            award = Award.objects.create(user=user, badge=badge, date=date, context=context)
            logger.info("award %s created for %s" % (award.badge.name, user.email))



########NEW FILE########
__FILENAME__ = celery
from __future__ import absolute_import
from django.conf import settings
from celery.utils.log import get_task_logger
import os

from biostar import const
from datetime import timedelta

logger = get_task_logger(__name__)

from celery import Celery

app = Celery('biostar')

# Read the configuration from the config file.
app.config_from_object(settings.CELERY_CONFIG)

# Discover tasks in applications.
app.autodiscover_tasks(
    lambda: ["biostar.mailer", "biostar.awards"]
)


@app.task
def post_created(user):
    "Executed on a post creation"
    logger.info("post created")

@app.task
def call_command(name, *args, **kwargs):
    "Calls a django command in a delayed fashion"
    logger.info("calling django command %s with %s and %s" % (name, args, kwargs))
    from django.core.management import call_command
    call_command(name, *args, **kwargs)

@app.task
def test(*args, **kwds):
    logger.info("*** executing task %s %s, %s" % (__name__, args, kwds))
########NEW FILE########
__FILENAME__ = celeryconfig
from __future__ import absolute_import
from datetime import timedelta
from celery.schedules import crontab

CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'

BROKER_URL = 'django://'

CELERY_TASK_SERIALIZER = 'pickle'

CELERY_ACCEPT_CONTENT = ['pickle']

CELERYBEAT_SCHEDULE = {

    'prune_data': {
        'task': 'biostar.celery.call_command',
        'schedule': timedelta(days=1),
        'kwargs': dict(name="prune_data")
    },

    'sitemap': {
        'task': 'biostar.celery.call_command',
        'schedule': timedelta(hours=6),
        'kwargs': dict(name="sitemap")
    },

    'update_index': {
        'task': 'biostar.celery.call_command',
        'schedule': timedelta(minutes=15),
        'args': ["update_index"],
        'kwargs': {"age": 1}
    },

    'awards': {
        'task': 'biostar.celery.call_command',
        'schedule': timedelta(hours=3),
        'args': ["user_crawl"],
        'kwargs': {"award": True}
    },

    'hourly_dump': {
        'task': 'biostar.celery.call_command',
        'schedule': crontab(minute=10),
        'args': ["biostar_pg_dump"],
        'kwargs': {"hourly": True}
    },

    'daily_dump': {
        'task': 'biostar.celery.call_command',
        'schedule': crontab(hour=22),
        'args': ["biostar_pg_dump"],
    },

    'hourly_feed': {
        'task': 'biostar.celery.call_command',
        'schedule': crontab(minute=10),
        'args': ["planet"],
        'kwargs': {"update": 1}
    },

    'daily_feed': {
        'task': 'biostar.celery.call_command',
        'schedule': crontab(hour='*/2', minute=15),
        'args': ["planet"],
        'kwargs': {"download": True}
    },

    'bump': {
        'task': 'biostar.celery.call_command',
        'schedule': timedelta(hours=6),
        'args': ["patch"],
        'kwargs': {"bump": True}
    },

}

CELERY_TIMEZONE = 'UTC'
########NEW FILE########
__FILENAME__ = const
"""
Constants that may be used in multiple packages
"""
try:
    from collections import OrderedDict
except ImportError, exc:
    # Python 2.6.
    from ordereddict import OrderedDict

from django.utils.timezone import utc
from datetime import datetime

# Message type selector.
LOCAL_MESSAGE, EMAIL_MESSAGE, NO_MESSAGES, DEFAULT_MESSAGES, ALL_MESSAGES = range(5)

MESSAGING_MAP = OrderedDict([
    (DEFAULT_MESSAGES, "default",),
    (LOCAL_MESSAGE, "local messages",),
    (EMAIL_MESSAGE, "email",),
    (ALL_MESSAGES, "email for every new thread (mailing list mode)",),
])

MESSAGING_TYPE_CHOICES = MESSAGING_MAP.items()

# Connects a user sort dropdown word to a data model field.
USER_SORT_MAP = OrderedDict([
    ("recent visit", "-profile__last_login"),
    ("reputation", "-score"),
    ("date joined", "profile__date_joined"),
    #("number of posts", "-score"),
    ("activity level", "-activity"),
])

# These are the fields rendered in the user sort order drop down.
USER_SORT_FIELDS = USER_SORT_MAP.keys()
USER_SORT_DEFAULT = USER_SORT_FIELDS[0]

USER_SORT_INVALID_MSG = "Invalid sort parameter received"

# Connects a post sort dropdown word to a data model field.
POST_SORT_MAP = OrderedDict([
    ("update", "-lastedit_date"),
    ("views", "-view_count"),
    ("followers", "-subs_count"),
    ("answers", "-reply_count"),
    ("bookmarks", "-book_count"),
    ("votes", "-vote_count"),
    ("rank", "-rank"),
    ("creation", "-creation_date"),
])

# These are the fields rendered in the post sort order drop down.
POST_SORT_FIELDS = POST_SORT_MAP.keys()
POST_SORT_DEFAULT = POST_SORT_FIELDS[0]

POST_SORT_INVALID_MSG = "Invalid sort parameter received"

# Connects a word to a number of days
POST_LIMIT_MAP = OrderedDict([
    ("all time", 0),
    ("today", 1),
    ("this week", 7),
    ("this month", 30),
    ("this year", 365),

])

# These are the fields rendered in the time limit drop down.
POST_LIMIT_FIELDS = POST_LIMIT_MAP.keys()
POST_LIMIT_DEFAULT = POST_LIMIT_FIELDS[0]

POST_LIMIT_INVALID_MSG = "Invalid limit parameter received"


def now():
    return datetime.utcnow().replace(tzinfo=utc)



########NEW FILE########
__FILENAME__ = mailer
from __future__ import absolute_import
import smtplib
import logging
from django.conf import settings
from django.core.mail.utils import DNS_NAME
from django.core.mail.backends import smtp
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail import get_connection

from .celery import app

logger = logging.getLogger(__name__)

# Based on django-celery-email
# https://github.com/pmclanahan/django-celery-email
CONFIG = getattr(settings, 'CELERY_EMAIL_TASK_CONFIG', {})

# Get the email sending backend.
BACKEND = getattr(settings, 'CELERY_EMAIL_BACKEND',
                  'django.core.mail.backends.smtp.EmailBackend')

TASK_CONFIG = {
    'name': 'celery.send_email',
    'ignore_result': True,
}
TASK_CONFIG.update(CONFIG)

@app.task
def send_email(message, **kwargs):

    conn = get_connection(backend=BACKEND,
                          **kwargs.pop('_backend_init_kwargs', {}))
    try:
        result = conn.send_messages([message])
        logger.debug("Successfully sent email message to %r.", message.to)
        return result
    except Exception as e:
        logger.error("Error sending email from %s to %r: %s retrying.",
                     message.from_email, message.to, e)
        send_email.retry(exc=e)

class SSLEmailBackend(smtp.EmailBackend):
    "Required for Amazon SES"
    def __init__(self, *args, **kwargs):
      kwargs.setdefault('timeout', 5)
      super(SSLEmailBackend, self).__init__(*args, **kwargs)

    def open(self):
        if self.connection:
            return False
        try:
            logger.info("sending email via %s" % self.host)
            self.connection = smtplib.SMTP_SSL(self.host, self.port,
                                               local_hostname=DNS_NAME.get_fqdn())
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except:
            if not self.fail_silently:
                raise

class CeleryEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super(CeleryEmailBackend, self).__init__(fail_silently)
        self.init_kwargs = kwargs

    def send_messages(self, email_messages, **kwargs):
        results = []
        kwargs['_backend_init_kwargs'] = self.init_kwargs
        for msg in email_messages:
            results.append(send_email.delay(msg, **kwargs))
        return results
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

# Register your models here.

########NEW FILE########
__FILENAME__ = ajax
__author__ = 'ialbert'
import json, traceback, logging
from braces.views import JSONResponseMixin
from biostar.apps.posts.models import Post, Vote
from biostar.apps.users.models import User
from django.views.generic import View
from django.shortcuts import render_to_response, render
from django.http import HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect, Http404
from functools import partial
from django.db import transaction
from django.db.models import Q, F


def json_response(adict, **kwd):
    """Returns a http response in JSON format from a dictionary"""
    return HttpResponse(json.dumps(adict), **kwd)


logger = logging.getLogger(__name__)


def ajax_msg(msg, status, **kwargs):
    payload = dict(status=status, msg=msg)
    payload.update(kwargs)
    return json_response(payload)


ajax_success = partial(ajax_msg, status='success')
ajax_error = partial(ajax_msg, status='error')


class ajax_error_wrapper(object):
    """
    Used as decorator to trap/display  errors in the ajax calls
    """

    def __init__(self, f):
        self.f = f

    def __call__(self, request):
        try:
            if request.method != 'POST':
                return ajax_error('POST method must be used.')

            if not request.user.is_authenticated():
                return ajax_error('You must be logged in to do that')

            value = self.f(request)
            return value
        except Exception, exc:
            traceback.print_exc()
            return ajax_error('Error: %s' % exc)


POST_TYPE_MAP = dict(vote=Vote.UP, bookmark=Vote.BOOKMARK, accept=Vote.ACCEPT)

@transaction.atomic
def perform_vote(post, user, vote_type):

    # Only maintain one vote for each user/post pair.
    votes = Vote.objects.filter(author=user, post=post, type=vote_type)
    if votes:
        vote = votes[0]
        msg = "%s removed" % vote.get_type_display()
        change = -1
    else:
        change = +1
        vote = Vote.objects.create(author=user, post=post, type=vote_type)
        msg = "%s added" % vote.get_type_display()

    if post.author != user:
        # Update the user reputation only if the author is different.
        User.objects.filter(pk=post.author.id).update(score=F('score') + change)

    # The thread score represents all votes in a thread
    Post.objects.filter(pk=post.root_id).update(thread_score=F('thread_score') + change)

    if vote.type == Vote.BOOKMARK:
        # Apply the vote
        Post.objects.filter(pk=post.id).update(book_count=F('book_count') + change, vote_count=F('vote_count') + change)
        Post.objects.filter(pk=post.id).update(subs_count=F('subs_count') + change)
        Post.objects.filter(pk=post.root_id).update(subs_count=F('subs_count') + change)

    elif vote_type == Vote.ACCEPT:
        if change > 0:
            # There does not seem to be a negation operator for F objects.
            Post.objects.filter(pk=post.id).update(vote_count=F('vote_count') + change, has_accepted=True)
            Post.objects.filter(pk=post.root_id).update(has_accepted=True)
        else:
            Post.objects.filter(pk=post.id).update(vote_count=F('vote_count') + change, has_accepted=False)
            Post.objects.filter(pk=post.root_id).update(has_accepted=False)
    else:
        Post.objects.filter(pk=post.id).update(vote_count=F('vote_count') + change)

    # Clear old votes.
    if votes:
        votes.delete()

    return msg




@ajax_error_wrapper
def vote_handler(request):
    "Handles all voting on posts"


    user = request.user
    vote_type = request.POST['vote_type']
    vote_type = POST_TYPE_MAP[vote_type]
    post_id = request.POST['post_id']

    # Check the post that is voted on.
    post = Post.objects.get(pk=post_id)

    if post.author == user and vote_type == Vote.UP:
        return ajax_error("You can't upvote your own post.")

    #if post.author == user and vote_type == Vote.ACCEPT:
    #    return ajax_error("You can't accept your own post.")

    if post.root.author != user and vote_type == Vote.ACCEPT:
        return ajax_error("Only the person asking the question may accept this answer.")

    with transaction.atomic():
        msg = perform_vote(post=post, user=user, vote_type=vote_type)

    return ajax_success(msg)
########NEW FILE########
__FILENAME__ = context
__author__ = 'ialbert'
from django.conf import settings
from biostar import const, VERSION
from django.core.cache import cache
from biostar.apps.users.models import User
from biostar.apps.posts.models import Post, Vote, PostView
from biostar.apps.badges.models import Award

from datetime import timedelta

CACHE_TIMEOUT = settings.CACHE_TIMEOUT


def get_recent_votes():
    votes = Vote.objects.filter(post__status=Post.OPEN).select_related("post").order_by("-date")[
            :settings.RECENT_VOTE_COUNT]
    return votes


def get_recent_users():
    users = User.objects.all().select_related("profile").order_by("-profile__last_login")[:settings.RECENT_USER_COUNT]
    return users


def get_recent_awards():
    awards = Award.objects.all().select_related("user", "badge")
    awards = awards.order_by("-date")[:6]
    return awards


def get_recent_replies():
    posts = Post.objects.filter(type__in=(Post.ANSWER, Post.COMMENT), root__status=Post.OPEN).select_related(("author"))
    posts = posts.order_by("-creation_date")
    posts = posts[:settings.RECENT_POST_COUNT]
    return posts


TRAFFIC_KEY = "traffic"


def get_traffic(minutes=60):
    "Obtains the number of distinct IP numbers "
    global TRAFFIC_KEY
    traffic = cache.get(TRAFFIC_KEY)
    if not traffic:
        recent = const.now() - timedelta(minutes=minutes)
        try:
            traffic = PostView.objects.filter(date__gt=recent).distinct('ip').count()
        except NotImplementedError, exc:
            traffic = PostView.objects.filter(date__gt=recent).values_list('ip')
            traffic = [t[0] for t in traffic]
            traffic = len(set(traffic))
        cache.set(TRAFFIC_KEY, traffic, CACHE_TIMEOUT)
    return traffic


def shortcuts(request):
    # These values will be added to each context

    context = {
        "GOOGLE_TRACKER": settings.GOOGLE_TRACKER,
        "GOOGLE_DOMAIN": settings.GOOGLE_DOMAIN,
        "SITE_STYLE_CSS": settings.SITE_STYLE_CSS,
        "SITE_LOGO": settings.SITE_LOGO,
        "SITE_NAME": settings.SITE_NAME,
        "CATEGORIES": settings.CATEGORIES,
        "BIOSTAR_VERSION": VERSION,
        "TRAFFIC": get_traffic(),
        'RECENT_REPLIES': get_recent_replies(),
        'RECENT_VOTES': get_recent_votes(),
        "RECENT_USERS": get_recent_users(),
        "RECENT_AWARDS": get_recent_awards(),
        'USE_COMPRESSOR': settings.USE_COMPRESSOR,
        'COUNTS': request.session.get(settings.SESSION_KEY, {}),
        'SITE_ADMINS': settings.ADMINS,
        'TOP_BANNER': settings.TOP_BANNER,
    }

    return context
########NEW FILE########
__FILENAME__ = feeds
from __future__ import unicode_literals, absolute_import, print_function

from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404
from biostar.apps.posts.models import Post
from biostar.apps.users.models import User
from biostar.apps.messages.models import Message
from biostar.apps.planet.models import BlogPost

from django.conf import settings
from django.contrib.sites.models import Site
from datetime import datetime, timedelta
import bleach

SITE = Site.objects.get(id=settings.SITE_ID)
SITE_NAME = settings.SITE_NAME

FEED_COUNT = 25


def reduce_html(text):
    if len(text) > 1500:
        text = bleach.clean(text, strip=True)
        text = text[:1500] + u' ... '
    return text


def split(text):
    text = ''.join(text.split())
    rows = text.split('+')
    return rows

class PlanetFeed(Feed):
    "Latest posts"
    link = "/"
    FEED_COUNT = 50
    title = "%s Planet!" % SITE_NAME
    description = "Latest 50 posts of the %s" % title

    def item_title(self, item):
        try:
            title = u"%s (%s)" % (item.title, item.blog.title)
        except Exception, exc:
            title = item.title
        return title

    def item_description(self, item):
        return item.content[:250]

    def item_guid(self, obj):
        return "%s" % obj.id

    def items(self):
        posts = BlogPost.objects.select_related("blog").order_by('-creation_date')
        return posts[:FEED_COUNT]


class PostBase(Feed):
    "Forms the base class to any feed producing posts"
    link = "/"
    title = "title"
    description = "description"

    def item_title(self, item):
        if item.type != Post.QUESTION:
            return "%s: %s" % (item.get_type_display(), item.title)
        else:
            return item.title

    def item_description(self, item):
        return reduce_html(item.content)

    def item_guid(self, obj):
        return "%s" % obj.id

class LatestFeed(PostBase):
    "Latest posts"
    title = "%s latest!" % SITE_NAME
    description = "Latest 25 posts from the %s" % title

    def items(self):
        posts = Post.objects.filter(type__in=Post.TOP_LEVEL).exclude(type=Post.BLOG).order_by('-creation_date')
        return posts[:FEED_COUNT]

class PostTypeFeed(PostBase):
    TYPE_MAP = {
        'job': Post.JOB, 'blog': Post.BLOG, 'question': Post.QUESTION,
        'forum': Post.FORUM, 'page': Post.PAGE
    }

    def get_object(self, request, text):
        words = split(text)
        codes = [self.TYPE_MAP[word] for word in words if word in self.TYPE_MAP]
        return codes, text

    def description(self, obj):
        code, text = obj
        return "Activity on posts  %s" % text

    def title(self, obj):
        return "Post Activity"

    def items(self, obj):
        codes, text = obj
        posts = Post.objects.filter(type__in=codes).order_by('-creation_date')
        return posts[:FEED_COUNT]


class PostFeed(PostBase):
    def get_object(self, request, text):
        return text

    def description(self, obj):
        return "Activity on posts  %s" % obj

    def title(self, obj):
        return "Post Activity"

    def items(self, text):
        ids = split(text)
        posts = Post.objects.filter(root_id__in=ids).order_by('-creation_date')
        return posts[:FEED_COUNT]


class TagFeed(PostBase):
    "Posts matching one or more tags"

    def get_object(self, request, text):
        return text

    def description(self, obj):
        return "Posts that match  %s" % obj

    def title(self, obj):
        return "Post Feed"

    def items(self, obj):
        posts = Post.objects.tag_search(obj)
        return posts[:FEED_COUNT]


class UserFeed(PostBase):

    def get_object(self, request, text):
        return text

    def description(self, obj):
        return "Posts for users that match  %s" % obj

    def title(self, obj):
        return "User Feed"

    def items(self, text):
        ids = split(text)
        posts = Post.objects.filter(author__id__in=ids).order_by('-creation_date')
        return posts[:FEED_COUNT]





########NEW FILE########
__FILENAME__ = biostar_pg_dump
"""
Dumps a postgresql database into a file
"""

import os
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from datetime import datetime
from optparse import make_option
import biostar

import logging

logger = logging.getLogger("command")


def abspath(*args):
    """Generates absolute paths"""
    return os.path.abspath(os.path.join(*args))


class Command(BaseCommand):
    help = 'Dumps the postgresql database into a file.'

    option_list = BaseCommand.option_list + (
        make_option('--hourly', dest='hourly', action='store_true', default=False, help='hourly datadump'),
        make_option('-u', dest='pg_user', default="www", help='postgres user default=%default'),
        make_option('-p', dest='prog', default="/usr/bin/pg_dump", help='the postgres program default=%default'),
        make_option('-o', dest='outdir', default="~/data/", help='output directory default=%default'),
    )

    def handle(self, *args, **options):
        pg_user = options['pg_user']
        prog = options['prog']
        hourly = options['hourly']
        outdir = options['outdir']
        main(pg_user=pg_user, hourly=hourly, prog=prog, outdir=outdir)


def main(pg_user, hourly, prog, outdir):
    # Get the full path to the directory.
    outdir = os.path.expanduser(outdir)
    if not os.path.isdir(outdir):
        os.mkdir(outdir)

    pg_name = settings.DATABASE_NAME

    # Hourly database dumps have a simpler name so
    # that they overwrite each other.
    if hourly:
        # These names only include the hours.
        tstamp = datetime.now().strftime("hourly-%H")
    else:
        # These names include the date.
        tstamp = datetime.now().strftime("%Y-%m-%d")

    db_file = "%s-%s-%s.sql.gz" % (pg_name, biostar.VERSION, tstamp)
    db_file = abspath(outdir, db_file)

    params = dict(
        pg_user=pg_user,
        pg_name=pg_name,
        version=biostar.VERSION,
        db_file=db_file,
        prog=prog,
    )

    #logger.info("saving %(pg_name)s to %(db_file)s" % params)

    cmd = "%(prog)s -Fp -x -O -b -U %(pg_user)s %(pg_name)s | gzip > %(db_file)s" % params

    # Running the command
    logger.info("%s" % cmd)
    os.system(cmd)


if __name__ == '__main__':
    #generate_sitemap()
    pass
########NEW FILE########
__FILENAME__ = delete_database
from __future__ import print_function, unicode_literals, absolute_import, division
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'deletes an sqlite database'

    def handle(self, *args, **options):
        target = settings.DATABASE_NAME
        if os.path.isfile(target):
            os.remove(target)
        else:
            print("*** file not found: %s" % target)
########NEW FILE########
__FILENAME__ = import_biostar1
from __future__ import print_function, unicode_literals, absolute_import, division
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from django.utils.timezone import utc, get_current_timezone
from django.conf import settings
from django.contrib.auth import get_user_model
import os, csv, datetime
from datetime import timedelta

from django.utils.dateparse import parse_datetime
from django.utils import timezone, encoding

from django.db import transaction
from itertools import *
from django.db.models import signals
from biostar.const import now

def path_join(*args):
    return os.path.abspath(os.path.join(*args))

# Obtain the user model
User = get_user_model()

BATCH_SIZE = 100

USER_TYPE_MAP = {
    "New": User.NEW_USER, "Member": User.USER, "Blog": User.BLOG,
    "Moderator": User.MODERATOR, "Administrator": User.ADMIN
}

USER_STATUS_MAP = {
    "Active": User.TRUSTED, "Suspended": User.SUSPENDED, "Banned": User.BANNED,
}

tz = get_current_timezone()

shift = timedelta(hours=6)

def get(data, attr, func=encoding.smart_unicode):
    value = data.get(attr, '').strip()
    try:
        value = func(value)
    except Exception, exc:
        raise Exception(value)
    return value

def localize_time(text):
    global shift
    naive = parse_datetime(text) + shift
    local = timezone.make_aware(naive, timezone=utc)
    return local

def get_post(row, users, klass):

    POST_TYPE_MAP = {
        "Question": klass.QUESTION, "Answer": klass.ANSWER,
        "Comment": klass.COMMENT, "Job": klass.JOB, "Blog": klass.BLOG,
        "Tool": klass.TOOL, "News": klass.NEWS,
        "Tutorial": klass.TUTORIAL,
    }

    POST_STATUS_MAP = {
        "Open": klass.OPEN,
        "Closed": klass.CLOSED,
        "Deleted": klass.DELETED,
    }

    uid = get(row, 'id', func=int)
    root_id = get(row, 'root_id', func=int)
    parent_id = get(row, 'parent_id', func=int)

    title = get(row, 'title').title()
    title = title[:200]
    tag_val = get(row, 'tag_val').strip()

    author_id = get(row, 'author_id', func=int)
    author = users.get(author_id)

    lastedit_user_id = get(row, 'lastedit_user', func=int)
    lastedit_user = users.get(lastedit_user_id)

    lastedit_user = lastedit_user or author

    if not author:
        print("*** author found for post %s" % (author_id, uid))
        return None

    post_type = get(row, 'post_type')

    post_type = POST_TYPE_MAP.get(post_type, klass.FORUM)

    if post_type == klass.TUTORIAL:
        tag_val += " tutorial"

    post_status = get(row, 'post_status')

    post_status = POST_STATUS_MAP[post_status]

    post = klass(id=uid, title=title, author=author, lastedit_user=author,
                parent_id=parent_id, root_id=root_id)

    post.status = post_status
    post.type = post_type
    post.tag_val = ",".join(tag_val.split())
    post.creation_date = localize_time(get(row, 'creation_date'))
    post.lastedit_date = localize_time(get(row, 'lastedit_date'))
    post.view_count = get(row, "views", func=int)
    post.reply_count = get(row, "answer_count", func=int)
    post.book_count = get(row, "book_count", func=int)
    post.thread_score = get(row, "full_score", func=int)
    post.vote_count = get(row, "score", func=int)
    post.lastedit_user = lastedit_user

    return post

def to_unicode(obj, encoding='utf-8'):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj


class Command(BaseCommand):
    help = 'migrate data from Biostar 1.*'

    option_list = BaseCommand.option_list + (
        make_option("-u", '--users', action="store_true", dest='users', default=False, help='import users'),
        make_option("-p", '--posts', action="store_true", dest='posts', default=False, help='import posts'),
        make_option("-x", '--votes', action="store_true", dest='votes', default=False, help='import votes'),
        make_option("-t", '--tags', action="store_true", dest='tags', default=False, help='auto tag'),
        make_option("-d", '--dir', dest='dir', default="~/tmp/biostar-migrate", help='import directory'),
    )

    def auto_tag(self, source, fname):
        pass


    def migrate_posts(self, source, fname):
        from biostar.server.models import disconnect_all
        from biostar.apps.posts.models import Post, Subscription
        from biostar.apps.messages.models import Message
        from biostar.apps.util import html

        log = self.stdout.write

        # Disconnect signals they will generate way too many messages
        disconnect_all()

        posts = [ p[0] for p in Post.objects.all().values_list("id") ]

        posts = set(posts)

        users = dict((u.id, u) for u in User.objects.all())

        log("migrating posts from %s" % fname)
        stream = csv.DictReader(file(fname), delimiter=b'\t')

        for i, row in enumerate(stream):
            title = to_unicode(row['title'])
            uid = int(row['id'])
            url = row['url'].strip()

            # Skip existing posts
            if uid in posts:
                continue

            posts.add(uid)

            log("migrating post %s: %s" % (uid, title))
            post = get_post(row, users, klass=Post)

            if not post:
                log("skipped %s: %s" % (uid, title))
                continue

            # Read and add the post body.
            post_file = path_join(source, 'posts', str(post.id))
            post.content = file(post_file, 'rt').read()

            if url and post.type == Post.BLOG:
                # Will break out an not deal with Blogs in Biostar.
                continue
                # Link to external blog bosts.
                url_link = '<p><b><i class="fa fa-external-link-square"></i> Read full blogpost at <a href="%s">%s</a></b><p>' % (url, url[:45])
                url_link = to_unicode(url_link)
                content = to_unicode(post.content)
                post.content = url_link + content

            try:
                post.save()
            except Exception, exc:
                log('*** error inserting post %s' % post.id)
                log("*** %s" % exc)
                continue

            # TODO migrate only tags with high count
            post.add_tags(post.tag_val)


        log("migrated %s posts" % Post.objects.all().count())
        log("created %s subscriptions" % Subscription.objects.all().count())
        log("created %s messages" % Message.objects.all().count())

    def migrate_users(self, source, fname):

        #User.objects.all().delete()
        log = self.stdout.write

        log("migrating users from %s" % fname)
        stream = csv.DictReader(file(fname), delimiter=b'\t')

        email_set, uid_seen = set(), set()

        users = dict((u.id, u) for u in User.objects.all())

        for row in stream:
            uid = int(get(row, 'id'))

            # The file may contain the same user multiple times
            # Caused by incremental dumping
            if uid in users or uid in uid_seen:
                continue

            uid_seen.add(uid)

            # Skip the first user. It is the default admin.
            if uid == 1:
                continue

            email = get(row, 'email')
            name = get(row, 'display_name')
            score = get(row, 'score')
            scholar = get(row, 'scholar')
            location = get(row, 'location')
            website = get(row, 'website')
            is_active = get(row, 'status') == "Active"
            user_type = USER_TYPE_MAP[get(row, 'type')]
            date_joined = get(row, 'date_joined')
            last_visited = get(row, 'last_visited')

            # Start populating the user.
            user = User(id=uid, email=email)
            user.email = email or "%s@xyz.xyz" % uid
            user.name = name
            user.score = score
            user.type = user_type

            # Original email were not required to be unique.
            if user.email in email_set:
                user.email = "%s@biostars.org" % uid

            # Adds the email to the seen bucket.
            email_set.add(user.email)

            user.is_active = is_active
            user.save()

            # Populate the profile
            prof = user.profile
            prof.website = website
            prof.scholar = scholar
            prof.location = location
            prof.date_joined = localize_time(date_joined)
            prof.last_login = localize_time(last_visited)
            about_me_file = path_join(source, 'about_me', str(uid))
            prof.info = file(about_me_file, 'rt').read()
            prof.save()

            log("migrated user %s:%s" % (user.id, user.email))

        if settings.DEBUG:
            for id in (2, 10,):
                try:
                    # We use this during debugging to make it easy to log in as someone else
                    bot = User.objects.get(id=id)
                    log(
                        "updated user %s with email=%s, name=%s, password=SECRET_KEY," % (bot.id, bot.email, bot.name))
                    bot.set_password(settings.SECRET_KEY)
                    bot.save()
                except Exception, exc:
                    pass

        log("migrated %s users" % User.objects.all().count())


    def migrate_votes(self, source, fname):
        log = self.stdout.write

        from biostar.apps.posts.models import Post, Vote

        VOTE_TYPE_MAP = {
            "Upvote": Vote.UP, "Downvote": Vote.DOWN,
            "Accept": Vote.ACCEPT, "Bookmark": Vote.BOOKMARK,
        }

        Vote.objects.all().delete()

        posts = Post.objects.all().values_list('id')

        seen = set(p[0] for p in posts)

        log("loaded %s post ids" % len(seen) )

        log("migrating votes from %s" % fname)


        user_map = dict((u.id, u) for u in User.objects.all())

        stream = csv.DictReader(file(fname), delimiter=b'\t')

        def vote_generator():
            for i, row in enumerate(stream):
                post_id = int(get(row, 'post_id'))
                author_id = int(get(row, 'author_id'))
                author = user_map.get(author_id)

                if not author:
                    log("*** author %s not found" % author_id)
                    continue

                vote_type = get(row, 'vote_type')
                vote_type = VOTE_TYPE_MAP[vote_type]
                vote_date = get(row, 'vote_date')
                vote_date = localize_time(vote_date)

                if post_id not in seen:
                    continue

                # Create the vote.
                vote = Vote(author=author, post_id=post_id, type=vote_type, date=vote_date)

                yield vote

        # Insert votes in batch. Bypasses the signals!
        Vote.objects.bulk_create(vote_generator(), batch_size=1000)

        log("migrated %s votes" % Vote.objects.all().count())

    def handle(self, *args, **options):

        source = os.path.expanduser(options['dir'])

        if options['users']:
            fname = path_join(source, "users.txt")
            self.migrate_users(source, fname)

        if options['posts']:
            fname = path_join(source, "posts.txt")
            self.migrate_posts(source, fname)

        if options['votes']:
            fname = path_join(source, "votes.txt")
            self.migrate_votes(source, fname)

        if options['tags']:
            fname = path_join(source, "posts.txt")
            self.auto_tag(source, fname)

        print("*** migrated from %s" % source)

########NEW FILE########
__FILENAME__ = import_mbox
import sys, time, os, logging
import mailbox, markdown, pyzmail
from django.conf import settings
from django.utils.timezone import utc
from django.utils import timezone, encoding
from email.utils import parsedate
from datetime import datetime
import itertools
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from itertools import *
import re, textwrap, urllib
from chardet import detect

from django.db.models import signals
import difflib

logger = logging.getLogger('simple-logger')

# This needs to be shorter so that the content looks good
# on smaller screens as well.
LINE_WIDTH = 70

TEMPDIR = "import/bioc"
DRY_RUN = False

if not os.path.isdir(TEMPDIR):
    os.mkdir(TEMPDIR)


def path_join(*args):
    return os.path.abspath(os.path.join(*args))


class Command(BaseCommand):
    help = 'migrate data from Biostar 1.*'

    option_list = BaseCommand.option_list + (
        make_option("-f", '--file', dest='file', default=False, help='import file'),
        make_option("-l", '--limit', dest='limit', default=None, help='limit posts'),
        make_option("-t", '--tags', dest='tags', default=None, help='tags'),
        make_option("-d", '--dry', dest='dry', action='store_true', default=False,
                    help='dry run, parses the emails only'),
    )

    def handle(self, *args, **options):
        global DRY_RUN
        fname = options['file']
        tags = options['tags']
        limit = options['limit']
        DRY_RUN = options['dry']
        if fname:
            parse_mboxx(fname, limit=limit, tag_val=tags)


class Bunch(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def guess_tags(text, tag_val):
    return tag_val


REPLACE_PATT = [
    "[Galaxy-user]",
    "[Galaxy-User]",
    "[galaxy-user]",
    "[BioC]",
]

SKIPPED_SIZE = 0
SIZE_LIMIT = 10000
SKIPPED_REPLY = 0


def create_post(b, author, root=None, parent=None, tag_val=''):
    from biostar.apps.posts.models import Post

    title = b.subj
    body = b.body
    if not parent:
        title = title.strip()
        title = ' '.join(title.splitlines())
        title = ' '.join(title.split())
        title = title.title()
        post = Post(title=title, type=Post.QUESTION, content=body, tag_val=tag_val, author=author)
    else:
        post_type = Post.ANSWER if parent.is_toplevel else Post.COMMENT
        post = Post(type=post_type, content=body, tag_val="galaxy", author=author, parent=parent)

    post.creation_date = post.lastedit_date = b.date

    if not DRY_RUN:
        post.save()

    tag_val = guess_tags(post.content, tag_val)

    if tag_val and not DRY_RUN:
        post.add_tags(tag_val)

    logger.info("--- creating %s: %s" % (post.get_type_display(), title))

    return post


def fix_file(fname):
    "Fixes the obfuscated emails in mbox files"
    new_name = "tmp-output.txt"
    logger.info("*** fixing obfuscated emails: %s" % new_name)
    fp = open(new_name, 'wt')
    for line in file(fname):
        if line.startswith("From: "):
            line = line.replace(" at ", "@")
        fp.write(line)
    fp.close()
    return new_name


def no_junk(line):
    "Gets rid of lines that contain junk"
    # invalid starts
    for word in "> --- From:".split():
        if line.strip().startswith(word):
            return False
    # junk words
    for word in "scrubbed attachment.html wrote: Sent:".split():
        if word in line:
            return False
    return True


def format_text(text):
    global LINE_WIDTH
    lines = text.splitlines()
    lines = filter(no_junk, lines)
    lines = [textwrap.fill(line, width=LINE_WIDTH) for line in lines]
    text = "\n".join(lines)
    text = "<div class='preformatted'>" + text + "</div>"
    return text


def to_unicode_or_bust(obj, encoding='utf-8'):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj


def bioc_remote_body(body):
    "Attempts to fetch remote body posts"

    # This is a fix for importing the bioconductor email list
    # Fetch the page if it is missing
    if "URL: <https://stat.ethz.ch/pipermail" in body:
        lines = body.splitlines()
        lines = filter(lambda x: x.startswith("URL:"), lines)
        if lines:
            line = lines[0]
            url = line.split()[1]
            url = url[1:-1]
            elems = url.split("/")
            fid = elems[-3] + elems[-2]
            fname = "%s/%s" % (TEMPDIR, fid)
            if not os.path.isfile(fname):
                logger.info(">>> fetching %s" % url)
                web = urllib.urlopen(url)
                text = web.read()
                try:
                    text = to_unicode_or_bust(text)
                except Exception, exc:
                    logger.error(exc)
                    text = "Error: unable to decode %s" % url
                fp = open(fname, 'wt')
                fp.write(text.encode("utf-8"))
                fp.close()
            body = open(fname).read().decode('utf8')
    return body


def unpack_message(data):
    msg = pyzmail.PyzMessage(data)

    # Get the name and email the message is coming from
    name, email = msg.get_address('from')
    email = email.lower()

    # Parse the date
    date = msg.get_decoded_header("Date")
    subj = msg.get_subject()
    if not date or not subj:
        return None

    date = parsedate(date)
    date = datetime(*date[:6])
    date = timezone.make_aware(date, timezone=utc)

    b = Bunch(name=name, email=email, date=date)
    b.id = msg.get_decoded_header("Message-ID")
    b.reply_to = msg.get_decoded_header('In-Reply-To')
    b.subj = subj
    for patt in REPLACE_PATT:
        b.subj = b.subj.replace(patt, "")

    # Get the body of the message
    if not msg.text_part:
        return None

    body = msg.text_part.get_payload()
    charset = detect(body)['encoding']
    body = body.decode(charset).encode('utf-8')

    # Checks for remote body for bioconductor import
    body = bioc_remote_body(body)

    # Reformat the body
    body = format_text(body)

    try:
        b.body = to_unicode_or_bust(body)
    except UnicodeDecodeError, exc:
        # Ignore this post
        return None

    return b


def parse_mboxx(filename, limit=None, tag_val=''):
    from biostar.server.models import disconnect_all
    from biostar.apps.users.models import User
    from biostar.apps.posts.models import Post

    global SKIPPED_REPLY

    #users = User.objects.all().delete()
    users = User.objects.all()
    users = dict([(u.email, u) for u in users])

    #Post.objects.all().delete()

    logger.info("*** found %s users" % len(users))

    if limit is not None:
        limit = int(limit)

    # Disconnect signals
    disconnect_all()

    logger.info("*** parsing mbox %s" % filename)

    new_name = fix_file(filename)

    # Parse the modified mbox.
    mbox = mailbox.mbox(new_name)
    rows = imap(unpack_message, mbox)

    # Remove empty elements
    rows = ifilter(None, rows)
    # Keep only email with sender and subject.
    rows = ifilter(lambda b: b.email, rows)
    rows = ifilter(lambda b: b.subj, rows)

    # Apply limits if necessary.
    rows = islice(rows, limit)

    tree, posts, fallback = {}, {}, {}

    for b in rows:
        datefmt = b.date.strftime('%Y-%m-%d')
        logger.info("*** %s parsing %s " % (datefmt, b.subj))

        if b.email not in users:

            logger.info("--- creating user name:%s, email:%s" % (b.name, b.email))
            u = User(email=b.email, name=b.name)
            if not DRY_RUN:
                u.save()
                u.profile.date_joined = b.date
                u.profile.last_login = b.date
                u.profile.save()

            users[u.email] = u

        author = users[b.email]

        parent = posts.get(b.reply_to) or fallback.get(b.subj)

        # Looks like a reply but still no parent
        # Fuzzy matching to commence
        if not parent and b.subj.startswith("Re:"):
            curr_key = b.subj
            logger.info("searching for best match %s" % curr_key)
            cands = difflib.get_close_matches(curr_key, fallback.keys())
            if cands:
                logger.info("found %s" % cands)
                parent = fallback[cands[0]]

        if parent:
            root = parent.root
            post = create_post(b=b, author=author, parent=parent)
        else:
            post = create_post(b=b, author=author, tag_val=tag_val)

        posts[b.id] = post

        # Fall back to guessing post inheritance from the title
        fall_key = "Re: %s" % post.title
        fallback[fall_key] = post

    logger.info("*** users %s" % len(users))
    logger.info("*** posts %s" % len(posts))
    logger.info("*** post limit: %s" % limit)
    logger.info("*** skipped posts due to size: %s" % SKIPPED_SIZE)
    logger.info("*** skipped posts due to missing parent: %s" % SKIPPED_REPLY)

    if DRY_RUN:
        logger.info("*** dry run, no data saved")
        sys.exit()

    logger.info("*** updating user scores")
    for user in User.objects.all():
        score = Post.objects.filter(author=user).count()
        user.score = user.full_score = score
        user.save()
        latest = Post.objects.filter(author=user).order_by("-creation_date")[:1]
        if latest:
            user.profile.last_login = latest[0].creation_date
            user.profile.save()


if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = initialize_site
from __future__ import print_function, unicode_literals, absolute_import, division
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import os, logging
from django.contrib.sites.models import Site
from django.contrib.flatpages.models import FlatPage
from allauth.socialaccount.models import SocialApp, providers

from django.core.exceptions import ImproperlyConfigured
from optparse import make_option

logger = logging.getLogger(__name__)

def abspath(*args):
    """Generates absolute paths"""
    return os.path.abspath(os.path.join(*args))

class Command(BaseCommand):
    help = 'Initializes content in Biostar'

    def handle(self, *args, **options):
        from biostar import awards
        init_admin()
        init_domain()
        init_social_providers()
        init_flatpages()
        awards.init_awards()

def init_flatpages():
    # list for the flatpages
    names = "faq about help policy sharing".split()
    site = Site.objects.get_current()
    for name in names:
        url = "/info/%s/" % name
        page = FlatPage.objects.filter(url=url, sites=site)
        if not page:
            path = abspath(settings.FLATPAGE_IMPORT_DIR, name)
            path = "%s.html" % path
            if not os.path.isfile(path):
                logger.error("cannot find flatpage %s" % path)
                continue
            content = file(path).read()
            page = FlatPage.objects.create(url=url, content=content, title=name.capitalize())
            page.sites.add(site)
            page.save()
            logger.info("added flatpage for url: %s" % url)

def init_admin():
    # Add the admin user if it is not present.
    from biostar.apps.users.models import User

    email = settings.ADMIN_EMAIL
    admin = User.objects.filter(id=1)
    if not admin:
        admin = User(
            email=email,
            is_staff=True,
            is_admin=True,
            name=settings.ADMIN_NAME,
            type=User.ADMIN
        )
        admin.set_password(settings.SECRET_KEY)
        admin.save()

        admin.profile.location = settings.ADMIN_LOCATION
        admin.profile.save()

        logger.info(
            "added admin user with email=%s, password=SECRET_KEY, name=%s" % (admin.email, admin.get_full_name()))

def init_domain():
    # Initialize to the current site if it is not present.
    from django.contrib.sites.models import Site

    site = Site.objects.get_current()
    if site.domain != settings.SITE_DOMAIN:
        site.name = settings.SITE_NAME
        site.domain = settings.SITE_DOMAIN
        site.save()
        logger.info("adding site=%s, name=%s, domain=%s" % (site.id, site.name, site.domain))

    # Initialize media folder
    for path in (settings.EXPORT_DIR, settings.MEDIA_ROOT):
        if not os.path.isdir(path):
            os.mkdir(path)


def init_social_providers():
    # Initialize social login providers.

    for name, data in settings.SOCIALACCOUNT_PROVIDERS.items():

        try:
            client_id = data.get('PROVIDER_KEY','')
            secret = data.get('PROVIDER_SECRET_KEY','')
            site = Site.objects.get(id=settings.SITE_ID)

            # Check that the provider is registered
            provider = providers.registry.by_id(name)

            # Code duplication since many2many fields cannot be initialized in one step
            exists = SocialApp.objects.filter(name=name)
            if not exists:
                app = SocialApp(
                    name=name,
                    client_id=client_id,
                    provider=name,
                    secret=secret, key='',
                )
                app.save()
                app.sites.add(site)
                app.save()
                logger.info("initializing social provider %s" % name)

        except Exception, exc:
            raise ImproperlyConfigured("error setting provider %s, %s" % (name, exc))



########NEW FILE########
__FILENAME__ = patch
__author__ = 'ialbert'

from django.core.management import call_command
from django.conf import settings
from django.db import connection, transaction
from django.db.models.loading import get_app
from StringIO import StringIO
from django.core.management.base import BaseCommand, CommandError
import os, re
from optparse import make_option
import random
import logging
from datetime import timedelta
from django.db.models import signals, Q

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Runs quick patches over the data. Use it only if you know what you're doing."

    option_list = BaseCommand.option_list + (
        make_option('--users', dest='users', action='store_true', default=False, help='patches_users'),
        make_option('--bump', dest='bump', action='store_true', default=False, help='bumps a random post'),
        make_option('--bump_id', dest='bump_id', type=int, help='bumps a specific post'),
        make_option('--stuff', dest='stuff', action='store_true', default=False, help='runs stuff ...'),
        make_option('--tag', dest='tag', default="", help='tags post by matching a regex.Format regex:name'),
        make_option('--dry', dest='dry', action='store_true', default=False, help='dry run, sometimes applies ;-)'),
    )

    def handle(self, *args, **options):

        tag = options['tag']
        dry = options['dry']

        if tag:
            tagger(tag, dry)

        if options['stuff']:
            stuff()

        if options['users']:
            patch_users()

        if options['bump']:
            bump()

        pk = options['bump_id']
        if pk:
            bump(pk)


def post_patch():
    "One off tasks go here that just need a quick access to the data"
    from biostar.apps.posts.models import Post
    from biostar.apps.users.models import User, Profile

    for post in Post.objects.all():
        post.html = post.content
        post.save()
    for prof in Profile.objects.all():
        prof.location = prof.location.strip()
        prof.save()


def stuff():
    "One off tasks go here that just need a quick access to the data"
    from biostar.apps.posts.models import Post
    from biostar.apps.users.models import User, Profile
    from biostar.const import ALL_MESSAGES

    cond = Q(profile__message_prefs=ALL_MESSAGES)
    cond = Q(profile__tags__name__in=["galaxy"])
    users = User.objects.filter(cond)

    for user in users:
        print user.id, user.email


def tagger(pattern, dry):

    "One off tasks go here that just need a quick access to the data"
    from biostar.apps.posts.models import Post
    from biostar.apps.users.models import User

    posts = Post.objects.filter(type__in=Post.TOP_LEVEL)
    patt, name = pattern.split(":")

    logger.info('%s -> %s' % (patt, name))

    patt = re.compile(patt, re.MULTILINE | re.IGNORECASE| re.DOTALL)
    for post in posts:
        hits = patt.search(post.content)
        if hits:
            logger.info(post.title)
            if not dry:
                tag_val = "%s, %s" % (post.tag_val, name)
                post.tag_val = tag_val
                post.save()
                post.add_tags(tag_val)

def patch_users():
    from biostar.apps.users.models import User, Profile
    from biostar.const import DEFAULT_MESSAGES

    users = Profile.objects.all()
    users.update(message_prefs=DEFAULT_MESSAGES)

def bump(pk=None):
    from biostar.apps.posts.models import Post
    from biostar.apps.users.models import User
    from biostar.const import now

    if not pk:
        query = Post.objects.filter(type=Post.QUESTION, status=Post.OPEN)

        value = random.random()

        if value > 0.5:
            since = now() - timedelta(weeks=10)
            query = query.filter(reply_count=0, creation_date__gt=since)

        query = query.values_list("id")

        ids = [ p[0] for p in query ]

        pk = random.choice(ids)

    community = User.objects.get(pk=1)
    post = Post.objects.get(pk=pk)
    logger.info(post.title)

    if not post.is_toplevel:
        logger.warning("post is not at toplevel")

    post.lastedit_date = now()
    post.lastedit_user = community
    post.save()



########NEW FILE########
__FILENAME__ = planet
__author__ = 'ialbert'

from django.core.management import call_command
from django.conf import settings
from django.db import connection, transaction
from django.db.models.loading import get_app
from StringIO import StringIO
from django.core.management.base import BaseCommand, CommandError
import os, logging
from optparse import make_option
from string import strip
import feedparser, urllib
from django.utils.encoding import smart_text
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger('simple-logger')

def abspath(*args):
    """Generates absolute paths"""
    return os.path.abspath(os.path.join(*args))


class Command(BaseCommand):
    help = 'Performs planet based data collection'

    option_list = BaseCommand.option_list + (
        make_option('--add', dest='add',
                    help='adds blogs to the database'),
        make_option('--download', dest='download', action="store_true", default=False,
                    help='downloads latest feeds'),
        make_option('--update', dest='update', default=0, type=int,
                    help='updates with latest feeds'),
    )

    def handle(self, *args, **options):
        # Create the planet directory if it is missing
        if not os.path.isdir(settings.PLANET_DIR):
            logger.info("creating planet directory %s" % settings.PLANET_DIR)
            os.mkdir(settings.PLANET_DIR)

        add_fname = options['add']
        if add_fname:
            add_blogs(add_fname)

        if options['download']:
            download_blogs()

        count = options['update']
        if count:
            update_entries(count)

def add_blog(feed):
    from biostar.apps.planet.models import Blog
    # makes it easier to troubleshoot when thing fail
    fname = abspath(settings.PLANET_DIR, 'add-blog.xml')
    try:
        text = urllib.urlopen(feed).read()
        stream = file(fname, 'wt')
        stream.write(text)
        stream.close()
        doc = feedparser.parse(fname)
        title = doc.feed.title
        if hasattr(doc.feed, "description"):
            desc = doc.feed.description
        else:
            desc = ""
        link = doc.feed.link
        blog = Blog.objects.create(title=smart_text(title), feed=feed, link=link, desc=smart_text(desc))
        logger.info("adding %s" % blog.title)
        logger.info("link: %s" % blog.link)
        logger.info(blog.desc)
    except Exception, exc:
        logger.error("error %s parsing %s" % (exc, feed))
        blog = None

    logger.info('-' * 10)
    return blog

def download_blogs():
    from biostar.apps.planet.models import Blog

    blogs = Blog.objects.filter(active=True)
    for blog in blogs:
        logger.info("downloading: %s" % blog.title)
        blog.download()

def update_entries(count=3):
    from biostar.apps.planet.models import Blog, BlogPost
    from biostar.apps.util import html

    #BlogPost.objects.all().delete()

    blogs = Blog.objects.filter(active=True)

    for blog in blogs:
        logger.info("parsing: %s: %s" % (blog.id, blog.title))
        try:
            seen = [e.uid for e in BlogPost.objects.filter(blog=blog)]
            seen = set(seen)

            # Parse the blog
            doc = blog.parse()

            # get the new posts
            entries = [ e for e in doc.entries if e.id not in seen ]

            # Only list a few entries
            entries = entries[:count]

            for r in entries:
                r.title = smart_text(r.title)
                r.title = r.title.strip()[:200]
                r.title = html.strip_tags(r.title)
                r.description = smart_text(r.description)
                r.description = html.strip_tags(r.description)

                date = r.get('date_parsed') or r.get('published_parsed')
                date = datetime(date[0], date[1], date[2])
                date = timezone.make_aware(date, timezone=timezone.utc)
                if not r.title:
                    continue
                body = html.clean(r.description)[:5000]
                content = html.strip_tags(body)
                post = BlogPost.objects.create(title=r.title, blog=blog, uid=r.id, content=content, html=body, creation_date=date, link=r.link)
                logger.info("added: %s" % post.title)

        except KeyError, exc:
            logger.error("%s" % exc)


def add_blogs(add_fname):
    from biostar.apps.planet.models import Blog

    #Blog.objects.all().delete()

    # Strip newlines
    urls = map(strip, open(add_fname))

    # Keep feeds with urls that do not yet exists
    urls = filter(lambda url: not Blog.objects.filter(feed=url), urls)

    #urls = urls[:1]

    # Attempt to populate the database with the feeds
    for feed in urls:
        logger.info("parsing %s" % feed)
        add_blog(feed)


########NEW FILE########
__FILENAME__ = prune_data
"""
Prunes the views. Reduces
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import utc
from datetime import datetime, timedelta

import logging


def now():
    return datetime.utcnow().replace(tzinfo=utc)


logger = logging.getLogger("command")


class Command(BaseCommand):
    help = 'Creates a sitemap in the export folder of the site'

    def handle(self, *args, **options):
        main()


def main(days=1, weeks=10):
    from biostar.apps.posts.models import PostView, ReplyToken
    from biostar.apps.messages.models import Message
    from biostar.apps.users.models import User
    from django.db.models import Count

    # Reduce post views.
    past = now() - timedelta(days=days)
    query = PostView.objects.filter(date__lt=past)
    msg = "deleting %s views" % query.count()
    logger.info(msg)
    query.delete()

    # Reduce messages.
    since = now() - timedelta(weeks=weeks)
    query = Message.objects.filter(sent_at__lt=since)
    msg = "deleting %s messages" % query.count()
    logger.info(msg)
    query.delete()

    # Remove old reply tokens
    query = ReplyToken.objects.filter(date__lt=since)
    msg = "deleting %s tokens" % query.count()
    logger.info(msg)
    query.delete()

    # Get rid of too many messages
    MAX_MSG = 100
    users = User.objects.annotate(total=Count("recipients")).filter(total__gt=MAX_MSG)[:100]
    for user in users:
        since = now() - timedelta(days=1)
        Message.objects.filter(user=user, sent_at__lt=since).delete()


if __name__ == '__main__':
    #generate_sitemap()
    pass
########NEW FILE########
__FILENAME__ = sitemap
"""
Creates a sitemap in the EXPORT directory
"""
import os
from django.conf import settings
from django.contrib.sitemaps import GenericSitemap
from django.contrib.sites.models import Site
from biostar.apps.posts.models import Post
from django.utils.encoding import smart_str
from django.template import loader
from django.core.management.base import BaseCommand, CommandError
import logging
from django.contrib import sitemaps

logger = logging.getLogger("command")

class Command(BaseCommand):
    help = 'Creates a sitemap in the export folder of the site'

    def handle(self, *args, **options):
        generate_sitemap()
        #ping_google()

def path(*args):
    "Generates absolute paths"
    return os.path.abspath(os.path.join(*args))

def ping_google():
    try:
        sitemaps.ping_google('/sitemap.xml')
    except Exception, exc:
        # Bare 'except' because we could get a variety
        # of HTTP-related exceptions.
        logger.error(exc)
        pass

def generate_sitemap():
    sitemap = GenericSitemap({
        'queryset': Post.objects.filter(type__in=Post.TOP_LEVEL).exclude(type=Post.BLOG),
    })
    urlset = sitemap.get_urls()
    text = loader.render_to_string('sitemap.xml', {'urlset': urlset})
    text = smart_str(text)
    site = Site.objects.get_current()
    fname = path(settings.STATIC_ROOT, 'sitemap.xml')
    logger.info('*** writing sitemap for %s to %s' % (site, fname))
    fp = open(fname, 'wt')
    fp.write(text)
    fp.close()
    logger.info('*** done')

if __name__ == '__main__':
    #generate_sitemap()
    pass
########NEW FILE########
__FILENAME__ = sqlfix
__author__ = 'ialbert'

from django.core.management import call_command
from django.conf import settings
from django.db import connection, transaction
from django.db.models.loading import get_app
from StringIO import StringIO
from django.core.management.base import BaseCommand, CommandError
import os
from optparse import make_option

os.environ['DJANGO_COLORS'] = 'nocolor'

class Command(BaseCommand):
    help = 'Resets the SQL sequence ids'

    option_list = BaseCommand.option_list + (
        make_option('--drop_index', dest='drop_index', action='store_true', default=False, help='drops the index'),
        make_option('--add_index', dest='add_index', action='store_true', default=False, help='adds the index'),
        make_option('--reset', dest='reset', action='store_true', default=False, help='reset sequences'),
    )

    def handle(self, *args, **options):

        if options['drop_index']:
            sql_command("sqldropindexes", "posts")

        if options['add_index']:
            sql_command("sqlindexes", "posts")

        if options['reset']:
            sql_command("sqlsequencereset", "users posts")

def sql_command(command, apps):
    commands = StringIO()
    cursor = connection.cursor()

    targets = apps.split()

    for app in targets:
        label = app.split('.')[-1]
        if get_app(label, emptyOK=True):
            call_command(command, label, stdout=commands)

    sql = commands.getvalue()
    print sql
    cursor.execute(sql)


########NEW FILE########
__FILENAME__ = test_email
from __future__ import print_function, unicode_literals, absolute_import, division
import logging

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'tests email settings'

    def handle(self, *args, **options):
        from_email = settings.DEFAULT_FROM_EMAIL
        subject = "[biostar] test email "

        recipient_list = [settings.ADMIN_EMAIL]

        params = dict(subject=subject, from_email=from_email, recipient_list=recipient_list)

        message = """
        Hello,

        this is an email sent via the

        test_email

        Biostar management command. Parameters:

        from_email = %(from_email)s
        recipient_list = %(recipient_list)s
        subject = %(subject)s

        """ % params

        logger.info("sending to %s" % recipient_list)
        send_mail(subject=subject, message=message, from_email=from_email, recipient_list=recipient_list)


########NEW FILE########
__FILENAME__ = test_task
from __future__ import print_function, unicode_literals, absolute_import, division
import logging

from django.core.management.base import BaseCommand

from biostar.celery import test

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'tests celery tasks'

    def handle(self, *args, **options):
        logger.info("submitting test task to celery")
        test.delay(100, name="Hello!")



########NEW FILE########
__FILENAME__ = usermod
__author__ = 'ialbert'

from django.core.management import call_command
from django.conf import settings
from django.db import connection, transaction
from django.db.models.loading import get_app
from StringIO import StringIO
from django.core.management.base import BaseCommand, CommandError
import os, logging
from optparse import make_option

logger = logging.getLogger("simple-logger")

class Command(BaseCommand):
    help = 'Modifies users'

    option_list = BaseCommand.option_list + (
        make_option('-u', dest='uid',
                    help='Select user by id'),

        make_option('-e', dest='email',
                    help='Select user by email'),

        make_option('-p', dest='passwd',
                    help='sets a new password for the user'),
    )

    def handle(self, *args, **options):
        from biostar.apps.users.models import User
        user = None

        uid = options['uid']
        email = options['email']

        if uid:
             user = User.objects.get(pk=uid)
        elif email:
             user = User.objects.get(email=email)

        passwd = options['passwd']
        if user and passwd:
            set_passwd(user, passwd)

def set_passwd(user, passwd):
    logger.info("settings the password for user %s" % user)
    user.set_password(passwd)
    user.save()


########NEW FILE########
__FILENAME__ = user_crawl
__author__ = 'ialbert'

from django.core.management import call_command
from django.conf import settings
from django.db import connection, transaction
from django.db.models.loading import get_app
from StringIO import StringIO
from django.core.management.base import BaseCommand, CommandError
import os, logging
from optparse import make_option

logger = logging.getLogger(__name__)

os.environ['DJANGO_COLORS'] = 'nocolor'

class Command(BaseCommand):
    help = 'Performs actions on users'

    option_list = BaseCommand.option_list + (
        make_option('--award', dest='award', action='store_true', default=False,
                    help='goes over the users and attempts to create awards'),
    )

    def handle(self, *args, **options):

        if options['award']:
            crawl_awards()

def crawl_awards():
    from biostar.apps.users.models import User
    from biostar.awards import create_user_award
    import random

    ids = [ u[0] for u in User.objects.all().values_list("id") ]

    random.shuffle(ids)

    ids = ids[:100]

    for pk  in ids:
        user = User.objects.get(pk=pk)
        #logger.info("%s: %s" % (user.id, user.name))
        create_user_award.delay(user=user)



########NEW FILE########
__FILENAME__ = middleware
__author__ = 'ialbert'
from django.contrib import messages
from django.conf import settings
import hmac, logging, re
from datetime import timedelta
from django.contrib.auth import authenticate, login, logout
from biostar.apps.users.models import User, Profile
from biostar import const
from django.core.cache import cache
from biostar.apps.posts.models import Post, Vote
from biostar.apps.messages.models import Message
from biostar.apps.planet.models import BlogPost

from collections import defaultdict
from biostar.awards import create_user_award, check_user_profile

logger = logging.getLogger(__name__)

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


def get_ip(request):
    ip1 = request.META.get('REMOTE_ADDR', '')
    ip2 = request.META.get('HTTP_X_FORWARDED_FOR', '').split(",")[0].strip()
    ip = ip1 or ip2 or '0.0.0.0'
    return ip


class AutoSignupAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):

        # This social login already exists.
        if sociallogin.is_existing:
            return

        # Check if we could/should connect it.
        try:
            email = sociallogin.account.extra_data.get('email')
            #verified = sociallogin.account.extra_data.get('verified_email')
            if email:
                user = User.objects.get(email=email)
                sociallogin.connect(request, user)
        except User.DoesNotExist:
            pass


class ExternalAuth(object):
    '''
    This is an "autentication" that relies on the user being valid.
    We're just following the Django interfaces here.
    '''

    def authenticate(self, email, valid=False):
        # Check the username/password and return a User.
        if valid:
            user = User.objects.get(email=email)
            user.backend = "%s.%s" % (__name__, self.__class__.__name__)
            print user.backend
            return user
        else:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

def valid_external_login(request):
    "Attempts to perform an external login"

    for name, key in settings.EXTERNAL_AUTH:
        value = request.COOKIES.get(name)
        if value:
            try:
                email, digest1 = value.split(":")
                digest2 = hmac.new(key, email).hexdigest()
                valid = (digest1 == digest2)
                if not valid:
                    raise Exception("digests do not match")
            except Exception, exc:
                logger.error(exc)
                return False

            # If we made it this far the data is valid.
            user, flag = User.objects.get_or_create(email=email)
            if flag:
                logger.info("created user %s" % user.email)

            # Authenticate with local info.
            user = ExternalAuth().authenticate(email=user.email, valid=valid)
            login(request=request, user=user)
            return True

    return False


SESSION_KEY, ANON_USER = settings.SESSION_KEY, "anon-user"


def get_counts(request, weeks=settings.COUNT_INTERVAL_WEEKS):
    "Returns the number of counts for each post type in the interval that has passed"
    user = request.user
    now = const.now()

    # Authenticated users get counts since their last login.
    if user.is_authenticated():
        since = user.profile.last_login
    else:
        since = now - timedelta(weeks=weeks)

    # This fetches the posts since last login.
    posts = Post.objects.filter(type__in=Post.TOP_LEVEL, status=Post.OPEN, creation_date__gt=since).order_by(
        '-id').only("id").prefetch_related("tag_set")
    posts = posts[:200]
    counts = defaultdict(int)

    # How many news posts.
    counts['latest'] = len(posts)

    # Produce counts per tag.
    for post in posts:
        for tag in post.tag_set.all():
            counts[tag.name] += 1

    # Fill in the unanswered counts.
    counts['open'] = Post.objects.filter(type=Post.QUESTION, reply_count=0, status=Post.OPEN,
                                         creation_date__gt=since).count()

    # How many new planet posts
    counts['planet'] = BlogPost.objects.filter(insert_date__gt=since).count()

    # Compute a few more counts for the user.
    if user.is_authenticated():
        # These are the new messages since the last login.
        counts['messages'] = Message.objects.filter(user=user, unread=True, sent_at__gt=since).count()

        # These are the new votes since the last login.
        counts['votes'] = Vote.objects.filter(post__author=user, date__gt=since).count()

    return counts


class Visit(object):
    """
    Sets visit specific parameters on objects.
    """

    def process_request(self, request, weeks=settings.COUNT_INTERVAL_WEEKS):
        global SESSION_KEY, ANON_USER

        user, session = request.user, request.session

        # Suspended users are logged out immediately.
        if user.is_authenticated() and user.is_suspended:
            logout(request)
            messages.error(request, 'Sorry, this account has been suspended. Please contact the administrators.')

        # Add attributes to anonymous users.
        if not user.is_authenticated():

            # This attribute is required inside templates.
            user.is_moderator = user.is_admin = False

            # Check external logins.
            if settings.EXTERNAL_AUTH and valid_external_login(request):
                messages.success(request, "Login completed")

            # We do this to detect when an anonymous session turns into a logged in one.
            if ANON_USER not in session:
                session[ANON_USER] = True

        # User attributes that refresh at given intervals.
        if user.is_authenticated():

            # The time between two count refreshes.
            elapsed = (const.now() - user.profile.last_login).seconds

            # The user has an anonymous session already.
            # Update the user login data now.
            if ANON_USER in session:
                del session[ANON_USER]
                elapsed = settings.SESSION_UPDATE_SECONDS + 1

            # The user session will be updated.
            if elapsed > settings.SESSION_UPDATE_SECONDS:
                # Set the last login time.
                Profile.objects.filter(user_id=user.id).update(last_login=const.now())

                # Compute the counts.
                counts = get_counts(request)

                # Store the counts in the session for later use.
                session[SESSION_KEY] = counts

                # Create user awards if possible.
                create_user_award.delay(user=user)

                # check user and fill in details
                check_user_profile.delay(ip=get_ip(request), user=user)


        # Get the counts from the session or the cache.
        counts = session.get(SESSION_KEY) or cache.get(SESSION_KEY)

        # No sessions found, set the them into the session.
        if not counts:
            # Compute the counts
            counts = get_counts(request)

            # Put them into the session.
            session[SESSION_KEY] = counts

            # Store them in the cache for the next anonymous user.
            cache.set(SESSION_KEY, counts, settings.SESSION_UPDATE_SECONDS)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        pass

    def backwards(self, orm):
        pass

    models = {
        
    }

    complete_apps = ['server']
########NEW FILE########
__FILENAME__ = models
"""

There are no database models declarations in this file. Data models are specified in the apps.

Only signals and connections between models are specfied here.
"""
from __future__ import print_function, unicode_literals, absolute_import, division
import logging, datetime
from django.db.models import signals, Q

from biostar.apps.posts.models import Post, Subscription, ReplyToken
from biostar.apps.messages.models import Message, MessageBody
from biostar.apps.badges.models import Award

from biostar.apps.util import html, make_uuid

from django.core import mail
from django.conf import settings
from biostar.const import *
from django.contrib.sites.models import Site

logger = logging.getLogger(__name__)

# This will be the message body on the site.
POST_CREATED_TEXT = "messages/post_created.txt"
POST_CREATED_HTML = "messages/post_created.html"
POST_CREATED_SHORT = "messages/post_created_short.html"

AWARD_CREATED_HTML_TEMPLATE = "messages/award_created.html"

# This will be the message body in an email.

def post_create_messages(sender, instance, created, *args, **kwargs):
    "The actions to undertake when creating a new post"
    from biostar.apps.users.models import User

    post = instance
    if created:
        # The user sending the notifications.
        author = instance.author

        # Insert email subscriptions to users that watch these posts
        if post.is_toplevel:
            cond1 = Q(profile__message_prefs=ALL_MESSAGES)
            cond2 = Q(profile__tags__name__in=post.parse_tags())
            cond = cond1 | cond2
            for watcher in User.objects.filter(cond).exclude(id=author.id):
                sub, flag = Subscription.objects.get_or_create(post=post, user=watcher, type=EMAIL_MESSAGE)

        # Get all subscriptions for the post.
        subs = Subscription.objects.get_subs(post).exclude(user=author)

        # Generate the message from the template.
        content = html.render(name=POST_CREATED_SHORT, post=post, user=author)

        # Generate the email message body.
        site = Site.objects.get_current()
        email_text = html.render(name=POST_CREATED_TEXT, post=post, user=author, site=site)

        # Generate the html message
        email_html = html.render(name=POST_CREATED_HTML, post=post, user=author, site=site)

        # Create the message body.
        body = MessageBody.objects.create(author=author, subject=post.title,
                                          text=content, sent_at=post.creation_date)

        # Collects the emails for bulk sending.
        emails, tokens = [], []

        # This generator will produce the messages.
        def messages():
            for sub in subs:
                message = Message(user=sub.user, body=body, sent_at=body.sent_at)

                # collect to a bulk email if the subscription is by email:
                if sub.type == EMAIL_MESSAGE:
                    try:
                        token = ReplyToken(user=sub.user, post=post, token=make_uuid(8), date=now())
                        from_email = settings.EMAIL_FROM_PATTERN % (author.name, settings.DEFAULT_FROM_EMAIL)
                        from_email = from_email.encode("utf-8")
                        reply_to = settings.EMAIL_REPLY_PATTERN % token.token
                        subject = settings.EMAIL_REPLY_SUBJECT % body.subject
                        # create the email message
                        email = mail.EmailMultiAlternatives(
                            subject=subject,
                            body=email_text,
                            from_email=from_email,
                            to=[sub.user.email],
                            headers={'Reply-To': reply_to},
                        )
                        email.attach_alternative(email_html, "text/html")
                        emails.append(email)
                        tokens.append(token)
                    except Exception, exc:
                        # This here can crash the post submission hence the catchall
                        logger.error(exc)

                yield message

        # Bulk insert of all messages. Bypasses the Django ORM!
        Message.objects.bulk_create(messages(), batch_size=100)
        ReplyToken.objects.bulk_create(tokens, batch_size=100)

        try:
            # Bulk sending email messages.
            conn = mail.get_connection()
            conn.send_messages(emails)
        except Exception, exc:
            logger.error("email error %s" % exc)


def award_create_messages(sender, instance, created, *args, **kwargs):
    "The actions to undertake when creating a new post"
    award = instance

    if created:
        # The user sending the notifications.
        user = award.user
        # Generate the message from the template.
        content = html.render(name=AWARD_CREATED_HTML_TEMPLATE, award=award, user=user)

        subject = "Congratulations: you won %s" % award.badge.name

        # Create the message body.
        body = MessageBody.objects.create(author=user, subject=subject, text=content)
        message = Message.objects.create(user=user, body=body, sent_at=body.sent_at)

# Creates a message to everyone involved
signals.post_save.connect(post_create_messages, sender=Post, dispatch_uid="post-create-messages")

# Creates a message when an award has been made
signals.post_save.connect(award_create_messages, sender=Award, dispatch_uid="award-create-messages")


def disconnect_all():
    signals.post_save.disconnect(post_create_messages, sender=Post, dispatch_uid="post-create-messages")
    signals.post_save.disconnect(award_create_messages, sender=Award, dispatch_uid="award-create-messages")

########NEW FILE########
__FILENAME__ = moderate
"""
Moderator views
"""
from biostar.apps.posts.models import Post
from biostar.apps.badges.models import Award
from biostar.apps.posts.auth import post_permissions
from biostar.apps.users.models import User
from biostar.apps.users.auth import user_permissions
from biostar.apps.util import html
from django.conf import settings
from django.views.generic import FormView
from django.shortcuts import render
from django.contrib import messages
from biostar import const
from braces.views import LoginRequiredMixin
from django import forms
from django.core.urlresolvers import reverse
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, Submit, ButtonHolder
from django.http import HttpResponseRedirect
from django.db.models import Q, F
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

OPEN, CLOSE_OFFTOPIC, CLOSE_SPAM, DELETE, DUPLICATE, MOVE_TO_COMMENT, MOVE_TO_ANSWER, CROSSPOST = map(str, range(8))

from biostar.apps.util import now

POST_LIMIT_ERROR_MSG = '''
<p><b>Sorry!</b> Your posting limit of (%s) post per day has been reached.</p>
<p>This limit is very low for new users and is raised as you gain reputation.</p>
<p>This limit is necessary to protect the site from automated postings by spammers.</p>
'''

TOP_POST_LIMIT_ERROR_MSG = '''
<p><b>Sorry!</b> Your posting limit of (%s) questions per day has been reached.
Note that you can still contribute with comments and answers though.</p>
<p>This limit is very low for new users and is raised as you gain reputation.</p>
<p>This limit is necessary to protect the site from automated postings by spammers.</p>
'''

def update_user_status(user):
    "A user needs to have votes supporting them"
    if user.score >= settings.TRUST_VOTE_COUNT and not user.is_trusted:
        user.status = User.TRUSTED
        user.save()
    return user

def user_exceeds_limits(request, top_level=False):
    """
    Puts on limits on how many posts a user can post.
    """
    user = request.user
    since = now() - timedelta(days=1)

    # Check the user's credentials.
    user = update_user_status(user)

    # How many posts were generated by this user today.
    all_post_count = Post.objects.filter(author=user, creation_date__gt=since).count()

    # How many top level posts were generated by this user today.
    top_post_count = Post.objects.filter(author=user, creation_date__gt=since, type__in=Post.TOP_LEVEL).count()

    # The number of posts a user can create.
    max_post_limit = settings.MAX_POSTS_TRUSTED_USER if user.is_trusted else settings.MAX_POSTS_NEW_USER

    # The number of top level posts a user may create
    max_top_post_limit = settings.MAX_TOP_POSTS_TRUSTED_USER if user.is_trusted else settings.MAX_TOP_POSTS_NEW_USER

    # Apply the limit checks.
    if (all_post_count + 1) > max_post_limit:
        messages.info(request, POST_LIMIT_ERROR_MSG % max_post_limit)
        logger.error("post limit reached for %s" % user)
        return True

    # This only needs to be checked when creating top level post
    if top_level and ((top_post_count + 1) > max_top_post_limit):
        messages.info(request, TOP_POST_LIMIT_ERROR_MSG % max_top_post_limit)
        logger.error("top post limit reached for %s" % user)
        return True

    return False

class PostModForm(forms.Form):
    CHOICES = [
        (OPEN, "Open a closed or deleted post"),
        (MOVE_TO_ANSWER, "Move post to an answer"),
        (MOVE_TO_COMMENT, "Move post to a comment on the top level post"),
        (DUPLICATE, "Duplicated post (top level)"),
        (CROSSPOST, "Cross posted at other site"),
        (CLOSE_OFFTOPIC, "Close post (top level)"),
        (DELETE, "Delete post"),
    ]

    action = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect(), label="Select Action")

    comment = forms.CharField(required=False, max_length=200,
                              help_text="Enter a reason (required when closing, crosspost). This will be inserted into a template comment.")

    dupe = forms.CharField(required=False, max_length=200,
                           help_text="One or more duplicated post numbers, space or comma separated (required for duplicate closing).",
                           label="Duplicate number(s)")

    def __init__(self, *args, **kwargs):
        pk = kwargs['pk']
        kwargs.pop('pk')
        super(PostModForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.error_text_inline = False
        self.helper.help_text_inline = True
        self.helper.form_action = reverse("post-moderation", kwargs=dict(pk=pk))

        self.helper.layout = Layout(
            Fieldset(
                'Select moderation option',
                'action',
                'comment',
                'dupe',
            ),
            ButtonHolder(
                Submit('submit', 'Submit')
            )
        )

    def clean(self):
        cleaned_data = super(PostModForm, self).clean()
        action = cleaned_data.get("action")
        comment = cleaned_data.get("comment")
        dupe = cleaned_data.get("dupe")

        if action == CLOSE_OFFTOPIC and not comment:
            raise forms.ValidationError("Unable to close. Please add a comment!")

        if action == CROSSPOST and not comment:
            raise forms.ValidationError("Please add URL into the comment!")

        if action == DUPLICATE and not dupe:
            raise forms.ValidationError("Unable to close duplicate. Please fill in the post numbers")

        if dupe:
            dupe = dupe.replace(",", " ")
            dupes = dupe.split()[:5]
            cleaned_data['dupe'] = dupes

        return cleaned_data

class PostModeration(LoginRequiredMixin, FormView):
    model = Post
    template_name = "post_moderation_form.html"
    context_object_name = "post"
    form_class = PostModForm

    def get_obj(self):
        pk = self.kwargs['pk']
        obj = Post.objects.get(pk=pk)
        return obj

    def get(self, request, *args, **kwargs):
        post = self.get_obj()
        post = post_permissions(request, post)
        if not post.is_editable:
            messages.warning(request, "You may not moderate this post")
            return HttpResponseRedirect(post.root.get_absolute_url())
        form = self.form_class(pk=post.id)
        context = dict(form=form, post=post)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        user = request.user

        post = self.get_obj()
        post = post_permissions(request, post)

        # The default return url
        response = HttpResponseRedirect(post.root.get_absolute_url())

        if not post.is_editable:
            messages.warning(request, "You may not moderate this post")
            return response

        # Initialize the form class.
        form = self.form_class(request.POST, pk=post.id)

        # Bail out on errors.
        if not form.is_valid():
            messages.error(request, "%s" % form.errors)
            return response

        # A shortcut to the clean form data.
        get = form.cleaned_data.get

        # These will be used in updates, will bypasses signals.
        query = Post.objects.filter(pk=post.id)
        root  = Post.objects.filter(pk=post.root_id)

        action = get('action')
        if action == OPEN and not user.is_moderator:
            messages.error(request, "Only a moderator may open a post")
            return response

        if action == MOVE_TO_ANSWER and post.type == Post.COMMENT:
            # This is a valid action only for comments.
            messages.success(request, "Moved post to answer")
            query.update(type=Post.ANSWER, parent=post.root)
            root.update(reply_count=F("reply_count") + 1)
            return response

        if action == MOVE_TO_COMMENT and post.type == Post.ANSWER:
            # This is a valid action only for answers.
            messages.success(request, "Moved post to answer")
            query.update(type=Post.COMMENT, parent=post.root)
            root.update(reply_count=F("reply_count") - 1)
            return response

        # Some actions are valid on top level posts only.
        if action in (CLOSE_OFFTOPIC, DUPLICATE) and not post.is_toplevel:
            messages.warning(request, "You can only close or open a top level post")
            return response

        if action == OPEN:
            query.update(status=Post.OPEN)
            messages.success(request, "Opened post: %s" % post.title)
            return response

        if action in CLOSE_OFFTOPIC:
            query.update(status=Post.CLOSED)
            messages.success(request, "Closed post: %s" % post.title)
            content = html.render(name="messages/offtopic_posts.html", user=post.author, comment=get("comment"), post=post)
            comment = Post(content=content, type=Post.COMMENT, parent=post, author=user)
            comment.save()
            return response

        if action == CROSSPOST:
            content = html.render(name="messages/crossposted.html", user=post.author, comment=get("comment"), post=post)
            comment = Post(content=content, type=Post.COMMENT, parent=post, author=user)
            comment.save()
            return response

        if action == DUPLICATE:
            query.update(status=Post.CLOSED)
            posts = Post.objects.filter(id__in=get("dupe"))
            content = html.render(name="messages/duplicate_posts.html", user=post.author, comment=get("comment"), posts=posts)
            comment = Post(content=content, type=Post.COMMENT, parent=post, author=user)
            comment.save()
            return response

        if action == DELETE:

            # Delete marks a post deleted but does not remove it.
            # Remove means to delete the post from the database with no trace.

            # Posts with children or older than some value can only be deleted not removed

            # The children of a post.
            children = Post.objects.filter(parent_id=post.id).exclude(pk=post.id)

            # The condition where post can only be deleted.
            delete_only = children or post.age_in_days > 7 or post.vote_count > 1 or (post.author != user)

            if delete_only:
                # Deleted posts can be undeleted by re-opening them.
                query.update(status=Post.DELETED)
                messages.success(request, "Deleted post: %s" % post.title)
                response = HttpResponseRedirect(post.root.get_absolute_url())
            else:
                # This will remove the post. Redirect depends on the level of the post.
                url = "/" if post.is_toplevel else post.parent.get_absolute_url()
                post.delete()
                messages.success(request, "Removed post: %s" % post.title)
                response = HttpResponseRedirect(url)

            # Recompute post reply count
            post.update_reply_count()

            return response

        # By this time all actions should have been performed
        messages.warning(request, "That seems to be an invalid action for that post. \
                It is probably ok! Actions may be shown even when not valid.")
        return response

class UserModForm(forms.Form):
    CHOICES = [
        (User.NEW_USER, "Reinstate as new user"),
        (User.TRUSTED, "Reinstate as trusted user"),
        (User.SUSPENDED, "Suspend user"),
        (User.BANNED, "Ban user"),
    ]

    action = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect(), label="Select Action")

    def __init__(self, *args, **kwargs):
        pk = kwargs['pk']
        kwargs.pop('pk')
        super(UserModForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.error_text_inline = False
        self.helper.help_text_inline = True
        self.helper.form_action = reverse("user-moderation", kwargs=dict(pk=pk))

        self.helper.layout = Layout(
            Fieldset(
                'Select action',
                'action',
            ),
            ButtonHolder(
                Submit('submit', 'Submit')
            )
        )


class UserModeration(LoginRequiredMixin, FormView):
    model = Post
    template_name = "user_moderation_form.html"
    context_object_name = "user"
    form_class = UserModForm

    def get_obj(self):
        pk = self.kwargs['pk']
        obj = User.objects.get(pk=pk)
        return obj

    def get(self, request, *args, **kwargs):
        user = request.user
        target = self.get_obj()
        target = user_permissions(request, target)

        form = self.form_class(pk=target.id)
        context = dict(form=form, target=target)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        user = request.user

        target = self.get_obj()
        target = user_permissions(request, target)
        profile = target.profile

        # The response after the action
        response = HttpResponseRedirect(target.get_absolute_url())

        if target.is_administrator:
            messages.warning(request, "Cannot moderate an administrator")
            return response

        if user == target:
            messages.warning(request, "Cannot moderate yourself")
            return response

        if not user.is_moderator:
            messages.warning(request, "Only moderators have this permission")
            return response

        if not target.is_editable:
            messages.warning(request, "Target not editable by this user")
            return response

        form = self.form_class(request.POST, pk=target.id)
        if not form.is_valid():
            messages.error(request, "Invalid user modification action")
            return response

        action = int(form.cleaned_data['action'])

        if action == User.BANNED and not user.is_administrator:
            messages.error(request, "Only administrators may ban users")
            return response

        if action == User.BANNED and user.is_administrator:
            # Remove data by user
            profile.clear_data()

            # Remove badges that may have been earned by this user
            Award.objects.filter(user=target).delete()

            # Mass delete posts by this user
            query = Post.objects.filter(author=target, type__in=Post.TOP_LEVEL).update(status=Post.DELETED)

            # Delete posts with no votes.
            query = Post.objects.filter(author=target, type__in=Post.TOP_LEVEL, vote_count=0, reply_count=0)
            count = query.count()
            query.delete()

            messages.success(request, "User banned, %s posts removed" % count)


        # Apply the new status
        User.objects.filter(pk=target.id).update(status=action)

        messages.success(request, 'Moderation completed')
        return response


########NEW FILE########
__FILENAME__ = search
__author__ = 'ialbert'
from django.views.generic import DetailView, ListView, TemplateView, RedirectView, View
from haystack.views import SearchView
from haystack.forms import SearchForm
from haystack.query import SearchQuerySet, AutoQuery
from haystack.utils import Highlighter

from django.conf import settings
from biostar.server.views import BaseListMixin
from ajax import ajax_error, ajax_success, ajax_error_wrapper, json_response
from django.conf.urls import patterns
from django.contrib.sitemaps import FlatPageSitemap, GenericSitemap
from biostar.apps.posts.models import Post, Tag
from biostar.apps.planet.models import BlogPost
import logging

logger = logging.getLogger(__name__)

info_dict = {
    'queryset': Post.objects.all(),
}

sitemaps = {
    'flatpages': FlatPageSitemap,
    'posts': GenericSitemap(info_dict, priority=0.6),
}


class SiteSearch(SearchView):
    extra_context = lambda x: dict(topic="search", page_title="Search")


def slow_highlight(query, text):
    "Invoked only if the search backend does not support highlighting"
    highlight = Highlighter(query)
    value = highlight.highlight(text)
    return value


def join_highlights(row):
    "Joins the highlighted text"
    if type(row.highlighted) is dict:
        return ''
    return '<br>'.join(x for x in row.highlighted)


class Search(BaseListMixin):
    template_name = "search/search.html"
    paginate_by = settings.PAGINATE_BY
    context_object_name = "results"
    page_title = "Search"

    def get_queryset(self):
        self.q = self.request.GET.get('q', '')

        if not self.q:
            return []

        content = AutoQuery(self.q)
        query = SearchQuerySet().filter(content=content).highlight()[:50]
        for row in query:
            context = join_highlights(row)
            context = context or slow_highlight(query=self.q, text=row.content)
            row.context = context
        return query

    def get_context_data(self, **kwargs):
        context = super(Search, self).get_context_data(**kwargs)
        context['q'] = self.q
        return context


def suggest_tags(request):
    "Returns suggested tags"

    tags = Tag.objects.all().order_by('-count')[:10]

    data = settings.POST_TAG_LIST + [t.name for t in tags]
    data = filter(None, data)

    return json_response(data)


#@ajax_error_wrapper
def search_title(request):
    "Handles title searches"
    q = request.GET.get('q', '')

    content = AutoQuery(q)
    results = SearchQuerySet().filter(content=content).highlight()[:50]

    items = []
    for row in results:
        try:
            ob = row.object

            # Why can this happen?
            if not ob:
                continue
            context = join_highlights(row)
            context = context or slow_highlight(query=q, text=row.content)
            text = "%s" % row.title
            items.append(
                dict(id=ob.get_absolute_url(), text=text, context=context, author=row.author,
                     url=ob.get_absolute_url()),
            )
        except Exception, exc:
            logger.error(content)
            logger.error(exc)
            pass

    payload = dict(items=items)
    return json_response(payload)

########NEW FILE########
__FILENAME__ = search_indexes
__author__ = 'ialbert'
from biostar.apps.posts.models import Post
from biostar.apps.planet.models import BlogPost
from django.db.models import Q
from haystack import indexes

# Create the search indices.
class PostIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr='title')
    type = indexes.CharField(model_attr='type')
    content = indexes.CharField(model_attr='content')
    author = indexes.CharField(model_attr='author__name')

    def get_model(self):
        return Post

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        cond = Q(type=Post.COMMENT) | Q(status=Post.DELETED)
        return self.get_model().objects.all().exclude(cond)

    def get_updated_field(self):
        return "lastedit_date"

# Create the search indices.
class BlogPostIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr='get_title')
    content = indexes.CharField(model_attr='html')
    author = indexes.CharField(model_attr='blog__title')

    def get_model(self):
        return BlogPost

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        query = self.get_model().objects.all()
        return query

    def get_updated_field(self):
        return "insert_date"

########NEW FILE########
__FILENAME__ = server_tags
from django import template
from django.conf import settings
from django.template import Context, Template
from django.template.defaultfilters import stringfilter
from django.core.context_processors import csrf
from biostar.apps.posts.models import Post
from biostar.apps.messages.models import Message
import random, hashlib, urllib
from datetime import datetime, timedelta
from django.utils.timezone import utc
from django import template
from django.core.urlresolvers import reverse
from biostar import const

register = template.Library()

@register.simple_tag
def get_count(counts, word):
    num = counts.get(word.lower()) or ''
    return num

@register.simple_tag
def current(request, *urls):
    if request.path in (reverse(url) for url in urls):
        return "active"
    return ''

# The purpose of this is to return a random number
# that makes resources look different and therefore reload
if settings.DEBUG:
    @register.simple_tag
    def rand_num():
        return " %f " % random.random()
else:
    # Turns it off when not in debug mode.
    @register.simple_tag
    def rand_num():
        return "1"

@register.filter
def show_nonzero(value):
    "The purpose of this is to return value or empty"
    return value if value else ''

@register.filter
def bignum(number):
    "Reformats numbers with qualifiers as K"
    try:
        value = float(number)/1000.0
        if value > 10:
            return "%0.fk" % value
        elif value > 1:
            return "%0.1fk" % value
    except ValueError, exc:
        pass
    return str(number)

@register.filter
def on(value):
    "The purpose of this is to return value or empty"
    return "on" if value else 'off'

@register.filter
def latest(value):
    "Attempts to hide parts of the email"
    print "-" * 10, value
    return value if value else "Latest"

@register.filter
def hide_email(value):
    "Attempts to hide parts of the email"
    try:
        addr, host = value.split('@')
        hide = '*' * (len(addr) - 1)
        email = addr[0] + hide + '@' + host
        return email
    except Exception, exc:
        return value

@register.simple_tag
def messages_read(user):
    Message.objects.filter(user=user, unread=True).update(unread=False)
    return ''

@register.simple_tag
def gravatar(user, size=80):
    name = user.name
    email = user.email.encode('utf8')
    hash = hashlib.md5(email).hexdigest(),

    gravatar_url = "https://secure.gravatar.com/avatar/%s?" % hash
    gravatar_url += urllib.urlencode({
        's': str(size),
        'd': 'identicon',
    }
    )
    return """<img src="%s" alt="gravatar for %s"/>""" % (gravatar_url, name)


def pluralize(value, word):
    if value > 1:
        return "%d %ss" % (value, word)
    else:
        return "%d %s" % (value, word)


@register.filter
def time_ago(date):
    delta = const.now() - date
    if delta < timedelta(minutes=1):
        return 'just now'
    elif delta < timedelta(hours=1):
        unit = pluralize(delta.seconds // 60, "minute")
    elif delta < timedelta(days=1):
        unit = pluralize(delta.seconds // 3600, "hour")
    elif delta < timedelta(days=30):
        unit = pluralize(delta.days, "day")
    elif delta < timedelta(days=90):
        unit = pluralize(int(delta.days / 7), "week")
    elif delta < timedelta(days=730):
        unit = pluralize(int(delta.days / 30), "month")
    else:
        diff = delta.days / 365.0
        unit = '%0.1f years' % diff
    return "%s ago" % unit


@register.simple_tag
def last_action(post):
    action = "written"
    return "%s" % action

@register.simple_tag
def active(x, y):
    # Create the active class css
    x, y = x or '', y or ''
    return 'active' if x.lower() == y.lower() else ''

@register.simple_tag
def boxclass(post):
    # Create the css class for each row
    if post.has_accepted:
        style = "accepted"
    elif post.reply_count > 0:
        style = "answered"
    elif post.comment_count > 0:
        style = "commented"
    else:
        style = "unanswered"
    return style

@register.inclusion_tag('server_tags/sidebar_posts.html')
def sidebar_posts(posts):
    return dict(posts=posts)

@register.inclusion_tag('server_tags/sidebar_votes.html')
def sidebar_votes(votes):
    return dict(votes=votes)

@register.inclusion_tag('server_tags/sidebar_users.html')
def sidebar_users(users):
    return dict(users=users)

@register.inclusion_tag('server_tags/sidebar_locations.html')
def sidebar_locations(users):
    return dict(users=users)

@register.inclusion_tag('server_tags/sidebar_awards.html')
def sidebar_awards(awards):
    return dict(awards=awards)

@register.inclusion_tag('server_tags/nav_bar.html', takes_context=True)
def nav_bar(context, user):
    "Renders top navigation bar"
    return context

@register.inclusion_tag('server_tags/page_bar.html', takes_context=True)
def page_bar(context):
    "Renders a paging bar"
    return context

@register.inclusion_tag('server_tags/post_user_box.html')
def post_user_box(user, date):
    "Renders a user box"
    return dict(user=user, date=date)

@register.inclusion_tag('server_tags/user_box.html')
def user_box(user, lastlogin):
    "Renders a user box"
    return dict(user=user, lastlogin=lastlogin)

@register.inclusion_tag('server_tags/page_bar_sort_posts.html', takes_context=True)
def page_bar_sort_posts(context):
    context['sort_fields'] = const.POST_SORT_FIELDS
    context['date_fields'] = const.POST_LIMIT_FIELDS
    "Renders a paging bar"
    return context

@register.inclusion_tag('server_tags/page_bar_sort_users.html', takes_context=True)
def page_bar_sort_users(context):
    context['sort_fields'] = const.USER_SORT_FIELDS
    context['date_fields'] = const.POST_LIMIT_FIELDS
    "Renders a paging bar"
    return context


@register.inclusion_tag('server_tags/post_body.html', takes_context=True)
def post_body(context, post, user, tree):
    "Renders the post body"
    return dict(post=post, user=user, tree=tree, request=context['request'])


@register.inclusion_tag('server_tags/search_bar.html', takes_context=True)
def search_bar(context):
    "Displays search bar"
    return context

@register.inclusion_tag('server_tags/post_count_box.html')
def post_count_box(post, context=''):
    "Displays the count box for a post row"
    return dict(post=post, context=context)

@register.inclusion_tag('server_tags/post_actions.html')
def post_actions(post, user, label="COMMENT"):
    "Renders post actions"
    return dict(post=post, user=user, label=label)


@register.inclusion_tag('server_tags/user_link.html')
def userlink(user):
    "Renders the flair"
    marker = "&bull;"
    if user.is_admin:
        marker = '&diams;&diams;'
    elif user.is_moderator:
        marker = '&diams;'
    return {'user': user, 'marker': marker}

# this contains the body of each comment
COMMENT_TEMPLATE = 'server_tags/comment_body.html'
COMMENT_BODY = template.loader.get_template(COMMENT_TEMPLATE)


@register.simple_tag
def render_comments(request, post, tree):
    global COMMENT_BODY, COMMENT_TEMPLATE
    if settings.DEBUG:
        # reload the template to get changes
        COMMENT_BODY = template.loader.get_template(COMMENT_TEMPLATE)
    if post.id in tree:
        text = traverse_comments(request=request, post=post, tree=tree)
    else:
        text = ''
    return text


def traverse_comments(request, post, tree):
    "Traverses the tree and generates the page"
    global COMMENT_BODY

    def traverse(node):
        data = ['<div class="indent">']
        cont = Context({"post": node, 'user': request.user, 'request': request})
        cont.update(csrf(request))
        html = COMMENT_BODY.render(cont)
        data.append(html)
        for child in tree.get(node.id, []):
            data.append(traverse(child))
        data.append("</div>")
        return '\n'.join(data)

    # this collects the comments for the post
    coll = []
    for node in tree[post.id]:
        coll.append(traverse(node))
    return '\n'.join(coll)
########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase, SimpleTestCase
from django.test import Client
from django.core.urlresolvers import reverse
from django.conf import settings
from biostar.apps.users.models import User
from biostar.apps.posts.models import Post, Tag, PostView, Subscription
from biostar.apps.messages.models import Message, MessageBody

import logging, random

logging.disable(logging.WARNING)

user_count = lambda: User.objects.all().count()
post_count = lambda: Post.objects.all().count()
subs_count = lambda: Subscription.objects.all().count()
msg_count = lambda: Message.objects.all().count()
get_user = lambda x: User.objects.get(email=x)

haystack_logger = logging.getLogger('haystack')

# Set up some test data.
NAME_1, EMAIL_1, PASSWD_1 = "John Doe", "user1@example.org", "0123567"
NAME_2, EMAIL_2, PASSWD_2 = "Jane Doe", "user2@example.org", "3456789"

USER_DATA = [
    (EMAIL_1, PASSWD_1),
    (EMAIL_2, PASSWD_2),
]

# The name of test posts
TITLE_1 = "Post 1, title needs to be sufficiently long"
CAT_1, TAG_VAL_1 = Post.QUESTION, "tagA tagB galaXY"

TITLE_2 = "Post 2, title needs to be sufficiently long"
CAT_2, TAG_VAL_2 = Post.JOB, "jobA jobB galaxy"

CONTENT = """
    Lorem ipsum dolor sit amet, consectetur adipisicing elit,
    sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
    """

POST_DATA = [
    (TITLE_1, CAT_1, TAG_VAL_1),
    (TITLE_2, CAT_2, TAG_VAL_2),
]

class UserTest(TestCase):
    # The name of test users

    def code(self, response, code=200):
        self.assertEqual(response.status_code, code)

    def tearDown(self):
        haystack_logger.setLevel(logging.INFO)

    def setUp(self):

        # Disable haystack logger, testing will raise errors
        # on the more_like_this field in templates.
        haystack_logger.setLevel(logging.CRITICAL)

        # Sign up then log out each user.
        for email, passwd in USER_DATA:
            self.sign_up(email, passwd)

            # Turn off the CAPTCHA settings


    def sign_up(self, email, passwd):
        count = user_count()

        with self.settings(CAPTCHA=False, TRUST_VOTE_COUNT=0):
            r = self.client.post(reverse("account_signup"), dict(email=email, password1=passwd, password2=passwd),
                                 follow=True)
            self.assertContains(r, "My Tags")
            self.code(r)
            self.assertEqual(user_count(), count + 1)
            self.logout()

    def login(self, email, passwd):
        "Logs in a user"
        r = self.client.post(reverse("account_login"), dict(login=email, password=passwd), follow=True)
        self.assertContains(r, "My Tags")


    def logout(self):
        "Logs out the current user."
        r = self.client.get(reverse("logout"), follow=True)
        self.assertNotContains(r, "My Tags")


    def test_user_login(self):
        "Test that each user can log in."
        eq = self.assertEqual
        for email, passwd in USER_DATA:
            self.login(email, passwd)
            self.logout()


    def create_new_post(self, title, post_type, tag_val):
        p_count = post_count()
        s_count = subs_count()
        r = self.client.post(
            reverse("new-post"),
            dict(title=title, tag_val=tag_val, post_type=post_type, content=CONTENT),
        )

        # Needs to redirect to post
        self.code(r, 302)

        # After creating a new post the post count and subscription counts increase.
        self.assertEqual(post_count(), p_count + 1)
        self.assertEqual(subs_count(), s_count + 1)

    def create_new_answer(self, post):
        p_count = post_count()
        r = self.client.post(
            reverse("new-answer", kwargs=dict(pid=post.id)),
            dict(content=CONTENT),
        )
        self.code(r, 302)
        self.assertEqual(post_count(), p_count + 1)

    def get_post(self, pk):
        "Gets a post and returns it"
        post = Post.objects.get(pk=pk)
        r = self.client.get(reverse("post-details", kwargs=dict(pk=pk)))
        if post.is_toplevel:
            self.assertContains(r, post.title)
            self.code(r)
        else:
            self.code(r, 302)

        # Verify that a subscription exists for this post and author.

        self.assertTrue(Subscription.objects.get_subs(post).filter(user=post.author).count() == 1)
        return post


    def test_user_new_post(self):
        "Test that each user can create a new post."
        eq = self.assertEqual

        for email, passwd in USER_DATA:
            self.login(email, passwd)
            for title, post_type, tag_val in POST_DATA[:settings.MAX_TOP_POSTS_NEW_USER]:
                # Create unique titles
                title = title + email
                self.create_new_post(title=title, post_type=post_type, tag_val=tag_val)
                post = Post.objects.get(title=title)
                self.get_post(post.id)
            self.logout()


    def test_user_answer(self):
        "Test posting an answer."
        self.login(EMAIL_1, PASSWD_1)
        title = TITLE_1
        self.create_new_post(title=title, post_type=CAT_1, tag_val=TAG_VAL_1)
        post1 = Post.objects.get(title=title)
        post2 = self.get_post(post1.id)
        self.assertEqual(post1, post2)

        # Same user adds a new answer.
        p_count = post_count()
        m_count = msg_count()
        self.create_new_answer(post1)

        # No message has been added because it is the same user.
        self.assertEqual(msg_count(), m_count)
        self.logout()

        # A different user adds an answer
        self.login(EMAIL_2, PASSWD_2)
        self.create_new_answer(post1)

        # A message is added for the author of the parent.
        self.assertEqual(msg_count(), m_count + 1)

        # The user also has a welcome message.
        self.assertEqual(Message.objects.filter(user__email=EMAIL_1).count(), 2)

        # Test voting and that it applies to user and posts
        user1 = get_user(EMAIL_1)
        post = Post.objects.get(title=TITLE_1, type=Post.QUESTION)

        # First access adds a vote.
        r = self.client.post(reverse("vote-submit"), data=dict(post_id=post.id, vote_type="vote"))
        user2 = get_user(EMAIL_1)
        self.assertEqual(user1.score + 1, user2.score)

        # Seconds access removes a vote.
        r = self.client.post(reverse("vote-submit"), data=dict(post_id=post.id, vote_type="vote"))
        user3 = get_user(EMAIL_1)
        self.assertEqual(user1.score, user3.score)

        # Bookmarks also add reputation.
        r = self.client.post(reverse("vote-submit"), data=dict(post_id=post.id, vote_type="bookmark"))
        user4 = get_user(EMAIL_1)
        self.assertEqual(user1.score + 1, user4.score)


    def test_stress(self):
        "Stress test. Render multiple nested posts"
        emails = ["%s@test.org" % x for x in range(10)]
        passwd = "1234567"
        for email in emails:
            self.sign_up(email, passwd)


        with self.settings(TRUST_VOTE_COUNT=0, MAX_TOP_POSTS_TRUSTED_USER=100, MAX_POSTS_TRUSTED_USER=100):
            top_types = [Post.QUESTION, Post.JOB, Post.FORUM, Post.PAGE]
            for count in range(5):
                email = random.choice(emails)
                post_type = random.choice(top_types)
                self.login(email, passwd)

                self.create_new_post(title=TITLE_1, post_type=post_type, tag_val=TAG_VAL_1)
                self.logout()

            for count in range(10):
                valid_ids = [p.id for p in Post.objects.all()]
                email = random.choice(emails)
                self.login(email, passwd)
                id = random.choice(valid_ids)
                self.get_post(pk=id)
                post = Post.objects.get(pk=id)
                self.create_new_answer(post)
                self.logout()


class SiteTest(SimpleTestCase):

    def code(self, response, code=200):
        self.assertEqual(response.status_code, code)

    def test_site_navigation(self):
        "Testing site navigation."

        # Main site navigation.
        names = "home user-list tag-list rss latest-feed signup".split()
        for name in names:
            r = self.client.get(reverse(name))
            self.code(r)

        # Check that default categories work.
        for topic in settings.CATEGORIES:
            r = self.client.get(reverse("topic-list", kwargs=dict(topic=topic)))
            self.code(r)

    def test_redirects(self):
        "Testing page redirects."

        # Pages with redirects.
        names = "login logout new-post user-messages user-votes".split()
        for name in names:
            r = self.client.get(reverse(name))
            self.code(r, 302)

    def test_edit_pages(self):
        "Testing page redirects."
        # Pages that take parameters and redirect.
        names = "user-edit post-edit user-moderation post-moderation ".split()
        for name in names:
            r = self.client.get(reverse(name, kwargs=dict(pk=1)))
            self.code(r, 302)




########NEW FILE########
__FILENAME__ = views
from django.views.generic import DetailView, ListView, TemplateView, UpdateView, View
from django.conf import settings
from biostar.apps.users import auth
from biostar.apps.users.views import EditUser
import os, random
from django.core.cache import cache
from biostar.apps.messages.models import Message
from biostar.apps.users.models import User
from biostar.apps.posts.models import Post, Vote, Tag, Subscription, ReplyToken
from biostar.apps.posts.views import NewPost, NewAnswer
from biostar.apps.badges.models import Badge, Award
from biostar.apps.posts.auth import post_permissions
from biostar.apps.util import html

from django.contrib import messages
from datetime import datetime, timedelta
from biostar.const import OrderedDict
from biostar import const
from braces.views import LoginRequiredMixin, JSONResponseMixin
from django import shortcuts
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator
import logging
from django.contrib.flatpages.models import FlatPage
from haystack.query import SearchQuerySet
from . import moderate
from django.http import Http404
import markdown, pyzmail
from biostar.apps.util.email_reply_parser import EmailReplyParser

logger = logging.getLogger(__name__)


def abspath(*args):
    """Generates absolute paths"""
    return os.path.abspath(os.path.join(*args))


class BaseListMixin(ListView):
    "Base class for each mixin"
    page_title = "Title"
    paginate_by = settings.PAGINATE_BY

    def get_title(self):
        return self.page_title

    def get_context_data(self, **kwargs):
        context = super(BaseListMixin, self).get_context_data(**kwargs)
        context['page_title'] = self.get_title()

        sort = self.request.GET.get('sort', const.POST_SORT_DEFAULT)
        limit = self.request.GET.get('limit', const.POST_LIMIT_DEFAULT)

        if sort not in const.POST_SORT_MAP:
            messages.warning(self.request, const.POST_SORT_INVALID_MSG)
            sort = const.POST_SORT_DEFAULT

        if limit not in const.POST_LIMIT_MAP:
            messages.warning(self.request, const.POST_LIMIT_INVALID_MSG)
            limit = const.POST_LIMIT_DEFAULT

        context['sort'] = sort
        context['limit'] = limit
        context['q'] = self.request.GET.get('q', '')

        return context


def apply_sort(request, query):
    # Note: the naming here needs to match that in the server_tag.py template tags.
    # Apply sort order
    sort = request.GET.get('sort', const.POST_SORT_DEFAULT)
    field = const.POST_SORT_MAP.get(sort, "-lastedit_date")
    query = query.order_by(field)

    # Apply time limit.
    limit = request.GET.get('limit', const.POST_LIMIT_DEFAULT)
    days = const.POST_LIMIT_MAP.get(limit, 0)
    if days:
        delta = const.now() - timedelta(days=days)
        query = query.filter(lastedit_date__gt=delta)
    return query


LATEST = "latest"
MYPOSTS, MYTAGS, UNANSWERED, FOLLOWING, BOOKMARKS = "myposts mytags open following bookmarks".split()
POST_TYPES = dict(jobs=Post.JOB, tools=Post.TOOL, tutorials=Post.TUTORIAL,
                  forum=Post.FORUM, planet=Post.BLOG, pages=Post.PAGE)

# Topics that requires authorization
AUTH_TOPIC = set((MYPOSTS, MYTAGS, BOOKMARKS, FOLLOWING))


def posts_by_topic(request, topic):
    "Returns a post query that matches a topic"
    user = request.user

    # One letter tags are always uppercase
    topic = Tag.fixcase(topic)

    if topic == MYPOSTS:
        # Get the posts that the user wrote.
        return Post.objects.my_posts(target=user, user=user)

    if topic == MYTAGS:
        # Get the posts that the user wrote.
        messages.success(request,
                         'Posts matching the <b><i class="fa fa-tag"></i> My Tags</b> setting in your user profile')
        return Post.objects.tag_search(user.profile.my_tags)

    if topic == UNANSWERED:
        # Get unanswered posts.
        return Post.objects.top_level(user).filter(type=Post.QUESTION, reply_count=0)

    if topic == FOLLOWING:
        # Get that posts that a user follows.
        messages.success(request, 'Threads that will produce notifications.')
        return Post.objects.top_level(user).filter(subs__user=user)

    if topic == BOOKMARKS:
        # Get that posts that a user bookmarked.
        return Post.objects.my_bookmarks(user)

    if topic in POST_TYPES:
        # A post type.
        return Post.objects.top_level(user).filter(type=POST_TYPES[topic])

    if topic and topic != LATEST:
        # Any type of topic.
        return Post.objects.tag_search(topic)

    # Return latest by default.
    return Post.objects.top_level(user)


def reset_counts(request, label):
    "Resets counts in the session"
    label = label.lower()
    counts = request.session.get(settings.SESSION_KEY, {})
    if label in counts:
        counts[label] = ''
        request.session[settings.SESSION_KEY] = counts


class PostList(BaseListMixin):
    """
    This is the base class for any view that produces a list of posts.
    """
    model = Post
    template_name = "post_list.html"
    context_object_name = "posts"
    paginate_by = settings.PAGINATE_BY
    LATEST = "Latest"

    def __init__(self, *args, **kwds):
        super(PostList, self).__init__(*args, **kwds)
        self.limit = 250
        self.topic = None

    def get_title(self):
        if self.topic:
            return "%s Posts" % self.topic
        else:
            return "Latest Posts"

    def get_queryset(self):
        self.topic = self.kwargs.get("topic", "")

        # Catch expired sessions accessing user related information
        if self.topic in AUTH_TOPIC and self.request.user.is_anonymous():
            messages.warning(self.request, "Session expired")
            self.topic = LATEST

        query = posts_by_topic(self.request, self.topic)
        query = apply_sort(self.request, query)

        # Limit latest topics to a few pages.
        if not self.topic:
            query = query[:settings.SITE_LATEST_POST_LIMIT]
        return query

    def get_context_data(self, **kwargs):
        session = self.request.session

        context = super(PostList, self).get_context_data(**kwargs)
        context['topic'] = self.topic or self.LATEST

        reset_counts(self.request, self.topic)

        return context


class MessageList(LoginRequiredMixin, ListView):
    """
    This is the base class for any view that produces a list of posts.
    """
    model = Message
    template_name = "message_list.html"
    context_object_name = "objects"
    paginate_by = settings.PAGINATE_BY
    topic = "messages"

    def get_queryset(self):
        objs = Message.objects.filter(user=self.request.user).select_related("body", "body__author").order_by(
            '-sent_at')
        return objs

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super(MessageList, self).get_context_data(**kwargs)
        people = [m.body.author for m in context[self.context_object_name]]
        people = filter(lambda u: u.id != user.id, people)
        context['topic'] = self.topic
        context['page_title'] = "Messages"
        context['people'] = people
        reset_counts(self.request, self.topic)
        return context


class TagList(BaseListMixin):
    """
    Produces the list of tags
    """
    model = Tag
    page_title = "Tags"
    context_object_name = "tags"
    template_name = "tag_list.html"
    paginate_by = 100

    def get_queryset(self):
        objs = Tag.objects.all().order_by("-count")
        return objs


class VoteList(LoginRequiredMixin, ListView):
    """
    Produces the list of votes
    """
    model = Message
    template_name = "vote_list.html"
    context_object_name = "votes"
    paginate_by = settings.PAGINATE_BY
    topic = "votes"

    def get_queryset(self):
        objs = Vote.objects.filter(post__author=self.request.user).select_related("author", "post").order_by('-date')
        return objs

    def get_context_data(self, **kwargs):
        context = super(VoteList, self).get_context_data(**kwargs)
        people = [v.author for v in context[self.context_object_name]]
        random.shuffle(people)
        context['topic'] = self.topic
        context['page_title'] = "Votes"
        context['people'] = people
        reset_counts(self.request, self.topic)
        return context


class UserList(ListView):
    """
    Base class for the showing user listing.
    """
    model = User
    template_name = "user_list.html"
    context_object_name = "users"
    paginate_by = 60

    def get_queryset(self):
        self.q = self.request.GET.get('q', '')
        self.sort = self.request.GET.get('sort', const.USER_SORT_DEFAULT)
        self.limit = self.request.GET.get('limit', const.POST_LIMIT_DEFAULT)

        if self.sort not in const.USER_SORT_MAP:
            messages.warning(self.request, "Warning! Invalid sort order!")
            self.sort = const.USER_SORT_DEFAULT

        if self.limit not in const.POST_LIMIT_MAP:
            messages.warning(self.request, "Warning! Invalid limit applied!")
            self.limit = const.POST_LIMIT_DEFAULT

        # Apply the sort on users
        obj = User.objects.get_users(sort=self.sort, limit=self.limit, q=self.q, user=self.request.user)
        return obj

    def get_context_data(self, **kwargs):
        context = super(UserList, self).get_context_data(**kwargs)
        context['topic'] = "Users"

        context['sort'] = self.sort
        context['limit'] = self.limit
        context['q'] = self.q
        context['show_lastlogin'] = (self.sort == const.USER_SORT_DEFAULT)
        return context


class BaseDetailMixin(DetailView):
    def get_context_data(self, **kwargs):
        context = super(BaseDetailMixin, self).get_context_data(**kwargs)
        sort = self.request.GET.get('sort', const.POST_SORT_DEFAULT)
        limit = self.request.GET.get('limit', const.POST_LIMIT_DEFAULT)

        context['sort'] = sort
        context['limit'] = limit
        context['q'] = self.request.GET.get('q', '')
        return context


class UserDetails(BaseDetailMixin):
    """
    Renders a user profile.
    """
    model = User
    template_name = "user_details.html"
    context_object_name = "target"

    def get_object(self):
        obj = super(UserDetails, self).get_object()
        obj = auth.user_permissions(request=self.request, target=obj)
        return obj

    def get_context_data(self, **kwargs):
        context = super(UserDetails, self).get_context_data(**kwargs)
        target = context[self.context_object_name]
        #posts = Post.objects.filter(author=target).defer("content").order_by("-creation_date")
        posts = Post.objects.my_posts(target=target, user=self.request.user)
        paginator = Paginator(posts, 10)
        try:
            page = int(self.request.GET.get("page", 1))
            page_obj = paginator.page(page)
        except Exception, exc:
            messages.error(self.request, "Invalid page number")
            page_obj = paginator.page(1)
        context['page_obj'] = page_obj
        context['posts'] = page_obj.object_list
        awards = Award.objects.filter(user=target).select_related("badge", "user").order_by("-date")
        context['awards'] = awards[:25]
        return context


class EditUser(EditUser):
    template_name = "user_edit.html"


class PostDetails(DetailView):
    """
    Shows a thread, top level post and all related content.
    """
    model = Post
    context_object_name = "post"
    template_name = "post_details.html"

    def get(self, *args, **kwargs):
        # This will scroll the page to the right anchor.
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)

        if not self.object.is_toplevel:
            return HttpResponseRedirect(self.object.get_absolute_url())

        return self.render_to_response(context)

    def get_object(self):
        user = self.request.user

        obj = super(PostDetails, self).get_object()

        # Update the post views.
        Post.update_post_views(obj, request=self.request)

        # Adds the permissions
        obj = post_permissions(request=self.request, post=obj)

        # This will be piggybacked on the main object.
        obj.sub = Subscription.get_sub(post=obj, user=user)

        # Bail out if not at top level.
        if not obj.is_toplevel:
            return obj

        # Populate the object to build a tree that contains all posts in the thread.
        # Answers sorted before comments.
        thread = [post_permissions(request=self.request, post=post) for post in Post.objects.get_thread(obj, user)]

        # Do a little preprocessing.
        answers = [p for p in thread if p.type == Post.ANSWER]

        tree = OrderedDict()
        for post in thread:

            if post.type == Post.COMMENT:
                tree.setdefault(post.parent_id, []).append(post)

        store = {Vote.UP: set(), Vote.BOOKMARK: set()}

        if user.is_authenticated():
            pids = [p.id for p in thread]
            votes = Vote.objects.filter(post_id__in=pids, author=user).values_list("post_id", "type")

            for post_id, vote_type in votes:
                store.setdefault(vote_type, set()).add(post_id)

        # Shortcuts to each storage.
        bookmarks = store[Vote.BOOKMARK]
        upvotes = store[Vote.UP]

        # Can the current user accept answers
        can_accept = obj.author == user

        def decorate(post):
            post.has_bookmark = post.id in bookmarks
            post.has_upvote = post.id in upvotes
            post.can_accept = can_accept or post.has_accepted

        # Add attributes by mutating the objects
        map(decorate, thread + [obj])

        # Additional attributes used during rendering
        obj.tree = tree
        obj.answers = answers

        # Add the more like this field
        post = super(PostDetails, self).get_object()

        return obj

    def get_context_data(self, **kwargs):
        context = super(PostDetails, self).get_context_data(**kwargs)
        context['request'] = self.request
        return context


class ChangeSub(LoginRequiredMixin, View):
    pk, type = 0, 0
    TYPE_MAP = {"local": const.LOCAL_MESSAGE, "email": const.EMAIL_MESSAGE}

    def get(self, *args, **kwargs):
        # TODO needs to be done via POST.
        pk = self.kwargs["pk"]
        new_type = self.kwargs["type"]

        new_type = self.TYPE_MAP.get(new_type, None)

        user = self.request.user
        post = Post.objects.get(pk=pk)

        subs = Subscription.objects.filter(post=post, user=user)
        if new_type is None:
            subs.delete()
        else:
            if subs:
                subs.update(type=new_type)
            else:
                Subscription.objects.create(post=post, user=user, type=new_type)

        return shortcuts.redirect(post.get_absolute_url())


class RSS(TemplateView):
    template_name = "rss_info.html"


class RateLimitedNewPost(NewPost):
    "Applies limits to the number of top level posts that can be made"

    def get(self, request, *args, **kwargs):
        if moderate.user_exceeds_limits(request, top_level=True):
            return HttpResponseRedirect("/")
        return super(RateLimitedNewPost, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if moderate.user_exceeds_limits(request, top_level=True):
            return HttpResponseRedirect("/")
        return super(RateLimitedNewPost, self).post(request, *args, **kwargs)


class RateLimitedNewAnswer(NewAnswer):
    "Applies limits to the number of answers that can be made"

    def get(self, request, *args, **kwargs):
        if moderate.user_exceeds_limits(request):
            return HttpResponseRedirect("/")
        return super(RateLimitedNewAnswer, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if moderate.user_exceeds_limits(request):
            return HttpResponseRedirect("/")
        return super(RateLimitedNewAnswer, self).post(request, *args, **kwargs)


class FlatPageView(DetailView):
    template_name = "flatpages/default.html"
    context_object_name = 'flatpage'

    def get_object(self):
        #site_id = get_current_site(self.request).id
        slug = self.kwargs['slug']
        # This is so that we can switch this off and
        # Fall back to the real flatpages app.
        url = "/info/%s/" % slug
        query = FlatPage.objects.get(url=url)
        return query

    def get_context_data(self, **kwargs):
        context = super(FlatPageView, self).get_context_data(**kwargs)

        admins = User.objects.filter(type=User.ADMIN)

        mods = User.objects.filter(type=User.MODERATOR)

        fields = stat_key, u_count, p_count, q_count, a_count, c_count = "user_stats user_count post_count\
            question_count answer_count comment_count".split()

        params = cache.get(stat_key)

        if not params:
            params = dict()
            params[u_count] = User.objects.all().select_related('profile').count()
            params[p_count] = Post.objects.all().count()
            params[q_count] = Post.objects.filter(type=Post.QUESTION).count()
            params[a_count] = Post.objects.filter(type=Post.ANSWER).count()
            params[c_count] = Post.objects.filter(type=Post.COMMENT).count()
            cache.set(stat_key, params, 600)

        # Add each value to the context
        for field in fields:
            context[field] = params.get(field, 0)

        context['admins'] = admins
        context['mods'] = mods

        return context


class FlatPageUpdate(UpdateView):
    model = FlatPage
    fields = ['content']
    template_name = "flatpages/flatpage_edit.html"

    def get_success_url(self):

        # The purpose here is to allow site admins to
        # edit they flatpages and have them being saved
        # on the filesystem. That way they can reimport
        # the modified pages if they need to.

        pk = self.kwargs['pk']
        page = FlatPage.objects.get(pk=pk)

        # The page will be saved under this name.
        fname = "%s.html" % page.title.lower()

        # The output directory for the flatpage.
        fdir = abspath(settings.LIVE_DIR, "flatpages")

        # Temporary activated only in development.
        #fdir = settings.FLATPAGE_IMPORT_DIR

        # Make the directory under the live path.
        if not os.path.isdir(fdir):
            os.mkdir(fdir)

        # This here is user inputted!
        fpath = abspath(fdir, fname)

        # Ensure file goes under the export directory
        if fpath.startswith(fdir):
            with file(fpath, 'wt') as fp:
                fp.write(page.content)

        return super(FlatPageUpdate, self).get_success_url()

    def post(self, *args, **kwargs):
        req = self.request
        user = req.user

        logger.info("user %s edited %s" % (user, kwargs))
        if not self.request.user.is_admin:
            logger.error("user %s access denied on %s" % (user, kwargs))
            messages.error(req, "Only administrators may edit that page")
            return HttpResponseRedirect("/")

        return super(FlatPageUpdate, self).post(*args, **kwargs)


class BadgeView(BaseDetailMixin):
    model = Badge
    template_name = "badge_details.html"

    def get_context_data(self, **kwargs):
        context = super(BadgeView, self).get_context_data(**kwargs)

        # Get the current badge
        badge = context['badge']

        # Get recent awards related to this badge
        awards = Award.objects.filter(badge_id=badge.id).select_related('user').order_by("-date")[:60]

        context['awards'] = awards

        return context


class BadgeList(BaseListMixin):
    model = Badge
    template_name = "badge_list.html"
    context_object_name = "badges"

    def get_queryset(self):
        qs = super(BadgeList, self).get_queryset()
        qs = qs.order_by('-count')
        return qs

    def get_context_data(self, **kwargs):
        context = super(BadgeList, self).get_context_data(**kwargs)
        return context


from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.encoding import smart_text
import json


@csrf_exempt
def email_handler(request):
    key = request.POST.get("key")
    if key != settings.EMAIL_REPLY_SECRET_KEY:
        data = dict(status="error", msg="key does not match")
    else:
        body = request.POST.get("body")
        body = smart_text(body)

        # This is for debug only
        #fname = "%s/email-debug.txt" % settings.LIVE_DIR
        #fp = file(fname, "wt")
        #fp.write(body.encode("utf-8"))
        #fp.close()

        try:
            # Parse the incoming email.
            msg = pyzmail.PyzMessage.factory(body)

            # Extract the address from the address tuples.
            address = msg.get_addresses('to')[0][1]

            # Parse the token from the address.
            start, token, rest = address.split('+')

            # Verify that the token exists.
            token = ReplyToken.objects.get(token=token)

            # Find the post that the reply targets
            post, author = token.post, token.user

            # Extract the body of the email.
            part = msg.text_part or msg.html_part
            text = part.get_payload()

            # Remove the reply related content
            text = EmailReplyParser.parse_reply(text)

            # Apply server specific formatting
            text = html.parse_html(text)

            # Apply the markdown on the text
            text = markdown.markdown(text)

            # Rate-limit sanity check, potentially a runaway process
            since = const.now() - timedelta(days=1)
            if Post.objects.filter(author=author, creation_date__gt=since).count() > settings.MAX_POSTS_TRUSTED_USER:
                raise Exception("too many posts created %s" % author.id)

            # Create the new post.
            post_type = Post.ANSWER if post.is_toplevel else Post.COMMENT
            obj = Post.objects.create(type=post_type, parent=post, content=text, author=author)

            # Delete the token. Disabled for now.
            # Old token should be deleted in the data pruning
            #token.delete()

            # Form the return message.
            data = dict(status="ok", id=obj.id)

        except Exception, exc:
            data = dict(status="error", msg=str(exc))

    data = json.dumps(data)
    return HttpResponse(data, content_type="application/json")

#
# These views below are here to catch old URLs from the 2009 version of the SE1 site
#
POST_REMAP_FILE = '%s/post-remap.txt' % settings.LIVE_DIR
if os.path.isfile(POST_REMAP_FILE):
    logger.info("loading post remap file %s" % POST_REMAP_FILE)
    REMAP = dict([line.split() for line in file(POST_REMAP_FILE)])
else:
    REMAP = {}


def post_redirect(request, pid):
    "Redirect to a post"
    try:
        post = Post.objects.get(id=pid)
    except Post.DoesNotExist:
        raise Http404
    return shortcuts.redirect(post.get_absolute_url(), permanent=True)


def post_remap_redirect(request, pid):
    "Remap post id and redirect, SE1 ids"
    try:
        nid = REMAP[pid]
        post = Post.objects.get(id=nid)
        return shortcuts.redirect(post.get_absolute_url(), permanent=True)
    except Exception, exc:
        messages.error(request, "Unable to redirect: %s" % exc)
        return shortcuts.redirect("/")


def tag_redirect(request, tag):
    try:
        return shortcuts.redirect("/t/%s/" % tag, permanent=True)
    except Exception, exc:
        messages.error(request, "Unable to redirect: %s" % exc)
        return shortcuts.redirect("/")
########NEW FILE########
__FILENAME__ = base
# -*- coding: utf8 -*-
#
# Django settings for biostar project.
#
from __future__ import absolute_import
import os
from django.core.exceptions import ImproperlyConfigured
from .logger import LOGGING

# Turn off debug mode on deployed servers.
DEBUG = True

# Template debug mode.
TEMPLATE_DEBUG = DEBUG

# Should the django compressor be used.
USE_COMPRESSOR = False

# The start categories. These tags have special meaning internally.
START_CATEGORIES = [
    "Latest",  "Open",
]

# These should be the most frequent (or special) tags on the site.
NAVBAR_TAGS = [
    "RNA-Seq", "ChIP-Seq", "SNP", "Assembly",
]

# The last categories. These tags have special meaning internally.
END_CATEGORIES = [
    "Tutorials", "Tools",  "Jobs", "Forum",
]

# These are the tags that always show up in the tag recommendation dropdown.
POST_TAG_LIST = NAVBAR_TAGS + ["software error"]

# This will form the navbar
CATEGORIES = START_CATEGORIES + NAVBAR_TAGS + END_CATEGORIES

# This will appear as a top banner.
# It should point to a template that will be included.
TOP_BANNER = ""

#TOP_BANNER = "test-banner.html"

def get_env(name, func=None):
    """Get the environment variable or return exception"""
    try:
        if func:
            return func(os.environ[name])
        else:
            return unicode(os.environ[name], encoding="utf-8")
    except KeyError:
        msg = "*** Required environment variable %s not set." % name
        raise ImproperlyConfigured(msg)

def abspath(*args):
    """Generates absolute paths"""
    return os.path.abspath(os.path.join(*args))

# Displays debug comments when the server is run from this IP.
INTERNAL_IPS = ('127.0.0.1', )

# Set location relative to the current file directory.
HOME_DIR = get_env("BIOSTAR_HOME")
LIVE_DIR = abspath(HOME_DIR, 'live')

DATABASE_NAME = abspath(LIVE_DIR, get_env("DATABASE_NAME"))
STATIC_DIR = abspath(HOME_DIR, 'biostar', 'static')
TEMPLATE_DIR = abspath(HOME_DIR, 'biostar', 'server', 'templates')

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
EXPORT_DIR = abspath(LIVE_DIR, "export")
STATIC_ROOT = abspath(EXPORT_DIR, "static")

# This is where the planet files are collected
PLANET_DIR = abspath(LIVE_DIR, "planet")

# Absolute filesystem path to the directory that will hold user-uploaded files.
MEDIA_ROOT = abspath(EXPORT_DIR, "media")

# Needs to point to the directory that contains the
# html files that are stored in the flatpages about, faq, help, policy etc.
FLATPAGE_IMPORT_DIR = abspath(HOME_DIR, "import", "pages")

# Default search index location.
WHOOSH_INDEX = abspath(LIVE_DIR, "whoosh_index")

# These settings create an admin user.
# The default password is the SECRET_KEY.
ADMIN_NAME = get_env("BIOSTAR_ADMIN_NAME")
ADMIN_EMAIL = get_env("BIOSTAR_ADMIN_EMAIL")
ADMIN_LOCATION = "State College, USA"
ADMINS = (
    (ADMIN_NAME, ADMIN_EMAIL),
)

# Get the secret key from the environment.
SECRET_KEY = get_env("SECRET_KEY")

MANAGERS = ADMINS

DATABASES = {
    'default': {
        # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATABASE_NAME,
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

# admin site may fail if this setting is active
TEMPLATE_STRING_IF_INVALID = "*** MISSING ***"

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["localhost", get_env("BIOSTAR_HOSTNAME")]

ATOMIC_REQUESTS = True
CONN_MAX_AGE = 10;

# Allowed html content.
ALLOWED_TAGS = "p div br code pre h1 h2 h3 h4 hr span s sub sup b i img strong strike em underline super table thead tr th td tbody".split()
ALLOWED_STYLES = 'color font-weight background-color width height'.split()
ALLOWED_ATTRIBUTES = {
    '*': ['class', 'style'],
    'a': ['href', 'rel'],
    'img': ['src', 'alt', 'width', 'height'],
    'table': ['border', 'cellpadding', 'cellspacing'],
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# These parameters will be inserted into the database automatically.
SITE_ID = 1
SITE_NAME = "Site Name"
SITE_DOMAIN = get_env("BIOSTAR_HOSTNAME")

SERVER_EMAIL = DEFAULT_FROM_EMAIL = get_env("DEFAULT_FROM_EMAIL")

# What domain will handle the replies.
EMAIL_REPLY_PATTERN = "reply+%s+code@biostars.io"

# The format of the email that is sent
EMAIL_FROM_PATTERN = u"%s on Biostar <%s>"

# The secret key that is required to parse the email
EMAIL_REPLY_SECRET_KEY = "abc"

# The subject of the reply goes here
EMAIL_REPLY_SUBJECT = u"[biostar] %s"

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True


# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/static/upload/'

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Use absolute paths, not relative paths.
    STATIC_DIR,
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'biostar.server.middleware.Visit',
)

ROOT_URLCONF = 'biostar.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'biostar.wsgi.application'

TEMPLATE_DIRS = (
    TEMPLATE_DIR,
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

LOGIN_REDIRECT_URL = "/"

MESSAGE_TAGS = {
    10: 'alert-info', 20: 'alert-info',
    25: 'alert-success', 30: 'alert-warning', 40: 'alert-danger',
}

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',


    # 'django.contrib.sessions',

    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',

    # The javascript and CSS asset manager.
    'compressor',

    # Enabling the admin and its documentation.
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.messages',
    'django.contrib.humanize',
    'django.contrib.flatpages',
    'django.contrib.sessions',

    # Biostar specific apps.
    'biostar.apps.users',
    'biostar.apps.util',
    'biostar.apps.posts',
    'biostar.apps.messages',
    'biostar.apps.badges',
    'biostar.apps.planet',

    # The main Biostar server.
    'biostar.server',

    # Social login handlers.
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.persona',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.github',
    #'allauth.socialaccount.providers.linkedin',
    #'allauth.socialaccount.providers.weibo',

    # External apps.
    'haystack',
    'crispy_forms',
    'djcelery',
    'kombu.transport.django',
    'south',
]

CRISPY_TEMPLATE_PACK = 'bootstrap3'

AUTH_USER_MODEL = 'users.User'

DEBUG_TOOLBAR_PATCH_SETTINGS = False

# Default search is provided via Whoosh

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': WHOOSH_INDEX,
    },
}

TEMPLATE_CONTEXT_PROCESSORS = (
    # Django specific context processors.
    "django.core.context_processors.debug",
    "django.core.context_processors.static",
    "django.core.context_processors.request",
    "django.contrib.auth.context_processors.auth",
    "django.contrib.messages.context_processors.messages",

    # Social authorization specific context.
    "allauth.account.context_processors.account",
    "allauth.socialaccount.context_processors.socialaccount",

    # Biostar specific context.
    'biostar.server.context.shortcuts',
)

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "biostar.server.middleware.ExternalAuth",
)

ACCOUNT_CONFIRM_EMAIL_ON_GET = True

# Should the captcha be shown on the signup page.
CAPTCHA = True

# For how long does a user need to be a member to become trusted.
TRUST_RANGE_DAYS = 7

# Votes needed to start trusting the user
TRUST_VOTE_COUNT = 5

# How many non top level posts per day for users.
MAX_POSTS_NEW_USER = 5
MAX_POSTS_TRUSTED_USER = 30

# How many top level posts per day for a new user.
MAX_TOP_POSTS_NEW_USER = 2
MAX_TOP_POSTS_TRUSTED_USER = 5

SOCIALACCOUNT_ADAPTER = 'biostar.server.middleware.AutoSignupAdapter'

# Customize this to match the providers listed in the APPs
SOCIALACCOUNT_PROVIDERS = {

    'facebook': {
        'SCOPE': ['email'],
        'AUTH_PARAMS': {'auth_type': 'reauthenticate'},
        'METHOD': 'oauth2',
        'LOCALE_FUNC': lambda x: 'en_US',
        'PROVIDER_KEY': get_env("FACEBOOK_PROVIDER_KEY"),
        'PROVIDER_SECRET_KEY': get_env("FACEBOOK_PROVIDER_SECRET_KEY"),
    },

    'persona': {
        'REQUEST_PARAMETERS': {'siteName': 'Biostar'}
    },

    'github': {
        'SCOPE': ['email'],
        'PROVIDER_KEY': get_env("GITHUB_PROVIDER_KEY"),
        'PROVIDER_SECRET_KEY': get_env("GITHUB_PROVIDER_SECRET_KEY"),
    },

    'google': {
        'SCOPE': ['email', 'https://www.googleapis.com/auth/userinfo.profile'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'PROVIDER_KEY': get_env("GOOGLE_PROVIDER_KEY"),
        'PROVIDER_SECRET_KEY': get_env("GOOGLE_PROVIDER_SECRET_KEY"),
    },
}

# The google id will injected as a template variable.
GOOGLE_TRACKER = ""
GOOGLE_DOMAIN = ""

# The site logo.
SITE_LOGO = "biostar2.logo.png"

# The default CSS file to load.
SITE_STYLE_CSS = "biostar.style.less"

# Set it to None if all posts should be accesible via the Latest tab.
SITE_LATEST_POST_LIMIT = None

# How many recent objects to show in the sidebar.
RECENT_VOTE_COUNT = 7
RECENT_USER_COUNT = 7
RECENT_POST_COUNT = 12

# Time between two accesses from the same IP to qualify as a different view.
POST_VIEW_MINUTES = 5

# Default  expiration in seconds.
CACHE_TIMEOUT = 60

# Should the messages go to email by default
# Valid values are local, default, email
DEFAULT_MESSAGE_PREF = "local"

# Django precompressor settings.
COMPRESS_PRECOMPILERS = (
    ('text/coffeescript', 'coffee --compile --stdio'),
    ('text/less', 'lessc {infile} {outfile}'),
)

COMPRESS_OFFLINE_CONTEXT = {
    'STATIC_URL': STATIC_URL,
    'SITE_STYLE_CSS': SITE_STYLE_CSS,
}

# The cache mechanism is deployment dependent. Override it externally.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache' if DEBUG else 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake'
    }
}

# The celery configuration file
CELERY_CONFIG = 'biostar.celeryconfig'

# Setting a cookie with email:signed_hash(email)
# will automatically create accounts
EXTERNAL_AUTH = [
    ("foo.bar.com", "ABC"),
]

# Set these to redirect login to an external site.
EXTERNAL_LOGIN_URL = None
EXTERNAL_SIGNUP_URL = None
EXTERNAL_LOGOUT_URL = None
EXTERNAL_SESSION_KEY = "EXTERNAL"
EXTERNAL_SESSION_FIELDS = "title tag_val content".split()

# How far to look for posts for anonymous users.
COUNT_INTERVAL_WEEKS = 10000

# How frequently do we update the counts for authenticated users.
SESSION_UPDATE_SECONDS = 10 * 60
SESSION_COOKIE_NAME = "biostar2"

# The number of posts to show per page.
PAGINATE_BY = 25

# Used by crispyforms.
#CRISPY_FAIL_SILENTLY = not DEBUG

ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[biostar] "
ACCOUNT_PASSWORD_MIN_LENGHT = 6
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USER_MODEL_EMAIL_FIELD = "email"
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"
#ACCOUNT_LOGOUT_ON_GET = True

# Session specific settings.
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'
SESSION_KEY = "session"

# Use a mock email backend for development.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# On deployed servers the following must be set.
EMAIL_HOST = get_env("EMAIL_HOST")
EMAIL_PORT = get_env("EMAIL_PORT", func=int)
EMAIL_HOST_USER = get_env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = get_env("EMAIL_HOST_PASSWORD")

########NEW FILE########
__FILENAME__ = debug
# -*- coding: utf8 -*-
#
# Development settings
#
from .base import *

# add debugging middleware
MIDDLEWARE_CLASSES = list(MIDDLEWARE_CLASSES)
MIDDLEWARE_CLASSES.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

# We load the debug toolbar as well
INSTALLED_APPS = list(INSTALLED_APPS)

# This needs to be added before the user models.
INSTALLED_APPS.append( "debug_toolbar")

def show_toolbar(request):
    return True

DEBUG_TOOLBAR_CONFIG ={
    'SHOW_TOOLBAR_CALLBACK': "biostar.apps.util.always_true",
}

########NEW FILE########
__FILENAME__ = logger
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.


class RateLimitFilter(object):

    def filter(self, record):
        from django.core.cache import cache
        TIMEOUT = 600
        CACHE_KEY = "error-limiter"

        exists = cache.get(CACHE_KEY)
        if not exists:
            cache.set(CACHE_KEY, 1, TIMEOUT)

        return not exists

LOGGING = {
    'version': 1,

    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s.%(funcName)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },

    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },

        'ratelimit': {
            '()': 'biostar.settings.logger.RateLimitFilter',
        }
    },

    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false', 'ratelimit'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console':{
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },

        'simple':{
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },

    'loggers': {

        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },

        'biostar':{
            'level': 'INFO',
            'handlers': ['console'],
        },

        'command':{
            'level': 'INFO',
            'handlers': ['console'],
        },

       'simple-logger':{
            'level': 'INFO',
            'handlers': ['simple'],
        },
    }

}


########NEW FILE########
__FILENAME__ = selenium
# -*- coding: utf8 -*-
#
# Django settings for selenium testing
#
from biostar.settings.base import *

# Turn off captcha
CAPTCHA = False

# How many non top level posts per day for users.
MAX_POSTS_NEW_USER = 100
MAX_POSTS_TRUSTED_USER = 100

# How many top level posts per day for a new user.
MAX_TOP_POSTS_NEW_USER = 100
MAX_TOP_POSTS_TRUSTED_USER = 100

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake'
    }
}
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from django.views.generic import TemplateView
from biostar.server import views, ajax, search, moderate
from biostar.apps.posts.views import NewAnswer, NewPost, EditPost, external_post_handler
from biostar.apps.users.views import external_logout, external_login, CaptchaView, EmailListView
from biostar.apps.planet.views import BlogPostList

urlpatterns = patterns('',

    # Post listing.
    url(r'^$', views.PostList.as_view(), name="home"),

    # Listing of all tags.
    url(r'^t/$', views.TagList.as_view(), name="tag-list"),

    # Badge view details.
    url(r'^b/(?P<pk>\d+)/$', views.BadgeView.as_view(), name="badge-view"),

    # Badge list details.
    url(r'^b/list/$', views.BadgeList.as_view(), name="badge-list"),

    # Topic listing.
    url(r'^t/(?P<topic>.+)/$', views.PostList.as_view(), name="topic-list"),

    # The list of users.
    url(r'^user/list/$', views.UserList.as_view(), name="user-list"),

    # User details.
    url(r'^u/(?P<pk>\d+)/$', views.UserDetails.as_view(), name="user-details"),

    # User details.
    url(r'^u/edit/(?P<pk>\d+)/$', views.EditUser.as_view(), name="user-edit"),

    # Post details.
    url(r'^p/(?P<pk>\d+)/$', views.PostDetails.as_view(), name="post-details"),

    # Change subscription view.
    url(r'^local/sub/(?P<pk>\d+)/(?P<type>\w+)/$', views.ChangeSub.as_view(), name="change-sub"),

    # A separate url for each post type.
    url(r'^p/new/post/$', views.RateLimitedNewPost.as_view(), name="new-post"),

    # A new external post
    url(r'^p/new/external/post/$', external_post_handler, name="new-external-post"),

    url(r'^p/new/answer/(?P<pid>\d+)/$', views.RateLimitedNewAnswer.as_view(post_type="answer"), name="new-answer"),
    url(r'^p/new/comment/(?P<pid>\d+)/$', views.RateLimitedNewAnswer.as_view(post_type="comment"), name="new-comment"),

    # Edit an existing post.
    url(r'^p/edit/(?P<pk>\d+)/$', EditPost.as_view(), name="post-edit"),

    # Message display.
    url(r'^local/list/$', EmailListView.as_view(), name="email-list"),

    # Message display.
    url(r'^local/messages/$', views.MessageList.as_view(), name="user-messages"),

    # Vote display.
    url(r'^local/votes/$', views.VoteList.as_view(), name="user-votes"),

    # Produces the moderator panel.
    url(r'^local/moderate/post/(?P<pk>\d+)/$', moderate.PostModeration.as_view(), name="post-moderation"),

    # Produces the moderator panel.
    url(r'^local/moderate/user/(?P<pk>\d+)/$', moderate.UserModeration.as_view(), name="user-moderation"),

    # Full login and logout
    url(r'^site/login/$', external_login, name="login"),
    url(r'^site/logout/$', external_logout, name="logout"),
    url(r'^accounts/signup/$', CaptchaView.as_view(), name="signup"),

    # Email handlers
    url(r'^local/email/', views.email_handler, name="email-handler"),

    # Search the body.
    url(r'^local/search/page/', search.Search.as_view(), name="search-page"),

    # Search the titles.
    url(r'^local/search/title/', search.search_title, name="search-title"),

    # Returns suggested tags
    url(r'^local/search/tags/', search.suggest_tags, name="suggest-tags"),


    # Returns the planet view
    url(r'^planet/$', BlogPostList.as_view(), name="planet"),

    # Vote submission.
    url(r'^x/vote/$', ajax.vote_handler, name="vote-submit"),

    # Social login pages.
    (r'^accounts/', include('allauth.urls')),

    # Redirecting old posts urls from previous versions of Biostar
    url(r'^post/redirect/(?P<pid>\d+)/$', views.post_redirect),
    url(r'^post/show/(?P<pid>\d+)/$', views.post_redirect),
    url(r'^post/show/(?P<pid>\d+)/([-\w]+)/$', views.post_redirect),
    url(r'^questions/(?P<pid>\d+)/$', views.post_remap_redirect),
    url(r'^questions/(?P<pid>\d+)/([-\w]+)/$', views.post_remap_redirect),
    url(r'^questions/tagged/(?P<tag>.+)/$',views.tag_redirect),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

     # Local robots.txt.
    url(r'^robots\.txt$', TemplateView.as_view(template_name="robots.txt", content_type='text/plain'), name='robots'),

)

# Adding the sitemap.
urlpatterns += patterns('',
    (r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': search.sitemaps})
)

from biostar.server.feeds import LatestFeed, TagFeed, UserFeed, PostFeed, PostTypeFeed, PlanetFeed

# Adding the RSS related urls.
urlpatterns += patterns('',

    # RSS info page.
    url(r'^info/rss/$', views.RSS.as_view(), name='rss'),

    # RSS feeds
    url(r'^feeds/latest/$', LatestFeed(), name='latest-feed'),

    url(r'^feeds/tag/(?P<text>[\w\-_\+]+)/$', TagFeed(), name='tag-feed'),
    url(r'^feeds/user/(?P<text>[\w\-_\+]+)/$', UserFeed(), name='user-feed'),
    url(r'^feeds/post/(?P<text>[\w\-_\+]+)/$', PostFeed(), name='post-feed' ),
    url(r'^feeds/type/(?P<text>[\w\-_\+]+)/$', PostTypeFeed(), name='post-type'),
    url(r'^feeds/planet/$', PlanetFeed(), name='planet-feed'),
)

urlpatterns += patterns('',
    url(r'^info/(?P<slug>\w+)/$', views.FlatPageView.as_view(), name='flatpage'),
    url(r'^info/update/(?P<pk>\d+)/$', views.FlatPageUpdate.as_view(), name='flatpage-update'),
)

# This is used only for the debug toolbar
if settings.DEBUG:
    import debug_toolbar
    from biostar.apps.users.views import test_login
    urlpatterns += patterns('',
        url(r'^__debug__/', include(debug_toolbar.urls)),
        url(r'^test/login/', test_login),
    )
########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for biostar project.
"""

from django.core.wsgi import get_wsgi_application

# This is the default application
application = get_wsgi_application()

def white():
    # This is an alternative WSGI app that wraps static content
    from whitenoise.django import DjangoWhiteNoise
    white = get_wsgi_application()
    white = DjangoWhiteNoise(white)
    return white

########NEW FILE########
__FILENAME__ = fabfile
from fabric.context_managers import prefix
from fabric.api import *
from fabric.contrib.files import exists
from getpass import getpass
from sites import *

def copy_config():
    # Create a default environment.
    if not exists(env.biostar_env):
        put("conf/defaults.env", env.biostar_env)

        # Logging into this directory.
    if not exists("%(biostar_live)s/logs" % env):
        run("mkdir -p %(biostar_live)s/logs" % env)

    # Customize the deployment environment.
    with prefix(env.workon):

        # Copy over all scripts
        scripts = [
            "celery.beat.sh",
            "celery.worker.sh",
            "gunicorn.start.sh",
        ]
        for name in scripts:
            if not exists("live/%s" % name):
                put("conf/server/%s" % name, env.biostar_live)
                run("chmod +x %(biostar_live)s/*.sh" % env)

        if not exists("live/deploy.py"):
            put("biostar/settings/deploy.py", env.biostar_live)

        if not exists("live/biostar.nginx.conf"):
            put("conf/server/biostar.nginx.conf", env.biostar_live)
            sudo("ln -fs %(biostar_live)s/biostar.nginx.conf /etc/nginx/sites-enabled/" % env)

        if not exists("live/biostar.supervisor.conf"):
            put("conf/server/biostar.supervisor.conf", env.biostar_live)
            sudo("ln -fs %(biostar_live)s/biostar.supervisor.conf /etc/supervisor/conf.d/" % env)


def create_biostar():
    "Create the biostar directories"

    # Create directories.
    run('mkdir -p %(biostar_home)s' % env)

    # Clone from repository.
    run("git clone %(biostar_clone)s %(biostar_home)s" % env)

    with cd(env.biostar_home):
        run("git checkout %(biostar_branch)s" % env)

        with prefix(env.wrapper):
            run("mkvirtualenv biostar")
            run("workon biostar && pip install -r %(biostar_home)s/conf/requirements/all.txt" % env)

def restart():
    sudo("service nginx restart")
    sudo("supervisorctl restart biostar")
    sudo("supervisorctl restart worker beat")

def init_biostar():
    with prefix(env.workon):
        run("./biostar.sh init")
        run("./biostar.sh index")

def test():
    with prefix(env.workon):
        run("./biostar.sh test")

def migrate():
    # Clone from repository.
    with prefix(env.workon):
        run("git pull")
        run("python manage.py migrate")

def pull():
    # Perform a pull.
    with prefix(env.workon):
        run("git pull")
        #run("./biostar.sh test")
        run("python manage.py collectstatic --noinput")



########NEW FILE########
__FILENAME__ = sites
from fabric.api import *

BIOSTAR_HOME = "/home/www/sites/biostar-central"
VIRTUALENV_WRAPPER = "source /usr/local/bin/virtualenvwrapper.sh"
CLONE_URL = "https://github.com/ialbert/biostar-central.git"
BRANCH = "master"

def setenv():
    # The python environment that the system needs.
    env.biostar_home = BIOSTAR_HOME
    env.wrapper = VIRTUALENV_WRAPPER
    env.biostar_clone = CLONE_URL
    env.biostar_branch = BRANCH

    # The is the main environment that will be applied to each command.
    # This is the prefix invoked when opertating on the deployed site.
    env.biostar_live = "%(biostar_home)s/live" % env
    env.biostar_env = "%(biostar_live)s/deploy.env" % env
    env.workon = "source /usr/local/bin/virtualenvwrapper.sh && workon biostar && cd %(biostar_home)s && source %(biostar_env)s" % env

def usegalaxy(user="www"):
    "Sets the environment for the biostar galaxy"
    setenv()
    env.hosts.append('biostar.usegalaxy.org')
    env.user = user

def metastars(user="www"):
    "Sets the environment for the biostar galaxy"
    setenv()
    env.hosts.append('metastars.org')
    env.user = user

def main_biostars(user="www"):
    "Sets the environment for the biostar galaxy"
    setenv()
    env.hosts.append('biostars.org')
    env.user = user

def test_site(user='www'):
    setenv()
    env.hosts.append('test.biostars.org')
    env.user = user

def hostname():
    run("hostname")

########NEW FILE########
__FILENAME__ = ubuntu
"""
Command run when intializing an Ubuntu based linux distro from scratch
"""

from fabric.api import run, cd
from fabric.context_managers import prefix
from fabric.api import *
from getpass import getpass
from sites import *


def postgres_setup():
    # sudo su - postgres
    # createuser www
    pass


def add_ssh_key():
    "Appends the current SSH pub key to the remote authorized keys"
    put("~/.ssh/id_rsa.pub", "~/")
    run("mkdir -p .ssh")
    run("cat ~/id_rsa.pub >> ~/.ssh/authorized_keys")
    run("chmod 600 ~/.ssh/authorized_keys")
    run("rm -f ~/id_rsa.pub")


def user_add(user, group=''):
    "Create new users on the remote server"
    password = getpass('*** enter a password for user %s:' % user)

    if group:
        sudo("useradd -m -s /bin/bash %s -g %s" % (user, group))
    else:
        sudo("useradd -m -s /bin/bash %s" % user)

    sudo('echo %s:%s | chpasswd' % (user, password))


def test():
    user_add(user="mary")


def update_distro():
    # Set the hostname
    host = prompt('enter the hostname')
    ip = prompt('enter the ip number')

    sudo('echo  %s > /etc/hostname' % host)
    sudo('hostname -F /etc/hostname')
    sudo('echo "127.0.0.1     localhost.localdomain    localhost" > /etc/hosts')
    sudo('echo "%s    %s    %s" >> /etc/hosts' % ip, host, host)

    # Update the linux distribution.
    sudo("apt-get update")
    sudo("apt-get upgrade -y --show-upgraded")

    # Create group and users that will run the sertver.
    sudo("groupadd admin")

    # Install requirements.
    sudo("apt-get install -y postgresql postgresql-contrib postgresql-server-dev-all software-properties-common")
    sudo("apt-get install -y nginx fail2ban redis-server ufw python-software-properties g++ make openjdk-7-jdk")
    sudo("apt-get install -y build-essential ncurses-dev byacc zlib1g-dev python-dev git supervisor")
    sudo("apt-get install -y python-setuptools")

    # Install pip.
    sudo("easy_install pip")

    # Install the virtual environments.
    sudo("pip install virtualenv virtualenvwrapper")

    # Start webserver
    sudo("service nginx start")

    # Enable firewall.
    sudo("ufw allow ssh")
    sudo("ufw allow http")

    # Installing elastic search
    # wget https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.0.0.deb
    # sudo dpkg -i elasticsearch-1.0.1.deb
    # sudo update-rc.d elasticsearch defaults 95 10
    # sudo /etc/init.d/elasticsearch start




def install_nodejs():

    # reconfigure timezone
    # dpkg-reconfigure tzdata

    # Add two default users
    user_add(user="www", group="admin")

    # Install the lessc compiler.
    sudo("ufw enable")
    sudo("sudo add-apt-repository ppa:chris-lea/node.js")
    sudo("apt-get install -y nodejs")
    sudo("npm install -g less")



########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Biostar Central documentation build configuration file, created by
# sphinx-quickstart on Sun Mar  2 08:46:45 2014.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Biostar Central'
copyright = u'2014, Istvan Albert'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2.0'
# The full version, including alpha/beta/rc tags.
release = '2.0'

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

# The reST default role (used for this markup: `text`) to use for all
# documents.
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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

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

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

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
htmlhelp_basename = 'BiostarCentraldoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'BiostarCentral.tex', u'Biostar Central Documentation',
   u'Istvan Albert', 'manual'),
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


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'biostarcentral', u'Biostar Central Documentation',
     [u'Istvan Albert'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'BiostarCentral', u'Biostar Central Documentation',
   u'Istvan Albert', 'BiostarCentral', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
