__FILENAME__ = admin
from django.contrib import admin
from voting.models import Vote

admin.site.register(Vote)

########NEW FILE########
__FILENAME__ = managers
from django.conf import settings
from django.db import connection, models

try:
    from django.db.models.sql.aggregates import Aggregate
except ImportError:
    supports_aggregates = False
else:
    supports_aggregates = True

from django.contrib.contenttypes.models import ContentType

if supports_aggregates:
    class CoalesceWrapper(Aggregate):
        sql_template = 'COALESCE(%(function)s(%(field)s), %(default)s)'
    
        def __init__(self, lookup, **extra): 
            self.lookup = lookup
            self.extra = extra
    
        def _default_alias(self):
            return '%s__%s' % (self.lookup, self.__class__.__name__.lower())
        default_alias = property(_default_alias)
    
        def add_to_query(self, query, alias, col, source, is_summary):
            super(CoalesceWrapper, self).__init__(col, source, is_summary, **self.extra)
            query.aggregate_select[alias] = self


    class CoalesceSum(CoalesceWrapper):
        sql_function = 'SUM'


    class CoalesceCount(CoalesceWrapper):
        sql_function = 'COUNT'


class VoteManager(models.Manager):
    def get_score(self, obj):
        """
        Get a dictionary containing the total score for ``obj`` and
        the number of votes it's received.
        """
        ctype = ContentType.objects.get_for_model(obj)
        result = self.filter(object_id=obj._get_pk_val(),
                             content_type=ctype).extra(
            select={
                'score': 'COALESCE(SUM(vote), 0)',
                'num_votes': 'COALESCE(COUNT(vote), 0)',
        }).values_list('score', 'num_votes')[0]

        return {
            'score': int(result[0]),
            'num_votes': int(result[1]),
        }

    def get_scores_in_bulk(self, objects):
        """
        Get a dictionary mapping object ids to total score and number
        of votes for each object.
        """
        object_ids = [o._get_pk_val() for o in objects]
        if not object_ids:
            return {}
        
        ctype = ContentType.objects.get_for_model(objects[0])
        
        if supports_aggregates:
            queryset = self.filter(
                object_id__in = object_ids,
                content_type = ctype,
            ).values(
                'object_id',
            ).annotate(
                score = CoalesceSum('vote', default='0'),
                num_votes = CoalesceCount('vote', default='0'),
            )
        else:
            queryset = self.filter(
                object_id__in = object_ids,
                content_type = ctype,
                ).extra(
                    select = {
                        'score': 'COALESCE(SUM(vote), 0)',
                        'num_votes': 'COALESCE(COUNT(vote), 0)',
                    }
                ).values('object_id', 'score', 'num_votes')
            queryset.query.group_by.append('object_id')
        
        vote_dict = {}
        for row in queryset:
            vote_dict[row['object_id']] = {
                'score': int(row['score']),
                'num_votes': int(row['num_votes']),
            }
        
        return vote_dict

    def record_vote(self, obj, user, vote):
        """
        Record a user's vote on a given object. Only allows a given user
        to vote once, though that vote may be changed.

        A zero vote indicates that any existing vote should be removed.
        """
        if vote not in (+1, 0, -1):
            raise ValueError('Invalid vote (must be +1/0/-1)')
        ctype = ContentType.objects.get_for_model(obj)
        try:
            v = self.get(user=user, content_type=ctype,
                         object_id=obj._get_pk_val())
            if vote == 0:
                v.delete()
            else:
                v.vote = vote
                v.save()
        except models.ObjectDoesNotExist:
            if vote != 0:
                self.create(user=user, content_type=ctype,
                            object_id=obj._get_pk_val(), vote=vote)

    def get_top(self, Model, limit=10, reversed=False):
        """
        Get the top N scored objects for a given model.

        Yields (object, score) tuples.
        """
        ctype = ContentType.objects.get_for_model(Model)
        query = """
        SELECT object_id, SUM(vote) as %s
        FROM %s
        WHERE content_type_id = %%s
        GROUP BY object_id""" % (
            connection.ops.quote_name('score'),
            connection.ops.quote_name(self.model._meta.db_table),
        )

        # MySQL has issues with re-using the aggregate function in the
        # HAVING clause, so we alias the score and use this alias for
        # its benefit.
        if settings.DATABASE_ENGINE == 'mysql':
            having_score = connection.ops.quote_name('score')
        else:
            having_score = 'SUM(vote)'
        if reversed:
            having_sql = ' HAVING %(having_score)s < 0 ORDER BY %(having_score)s ASC LIMIT %%s'
        else:
            having_sql = ' HAVING %(having_score)s > 0 ORDER BY %(having_score)s DESC LIMIT %%s'
        query += having_sql % {
            'having_score': having_score,
        }

        cursor = connection.cursor()
        cursor.execute(query, [ctype.id, limit])
        results = cursor.fetchall()

        # Use in_bulk() to avoid O(limit) db hits.
        objects = Model.objects.in_bulk([id for id, score in results])

        # Yield each object, score pair. Because of the lazy nature of generic
        # relations, missing objects are silently ignored.
        for id, score in results:
            if id in objects:
                yield objects[id], int(score)

    def get_bottom(self, Model, limit=10):
        """
        Get the bottom (i.e. most negative) N scored objects for a given
        model.

        Yields (object, score) tuples.
        """
        return self.get_top(Model, limit, True)

    def get_for_user(self, obj, user):
        """
        Get the vote made on the given object by the given user, or
        ``None`` if no matching vote exists.
        """
        if not user.is_authenticated():
            return None
        ctype = ContentType.objects.get_for_model(obj)
        try:
            vote = self.get(content_type=ctype, object_id=obj._get_pk_val(),
                            user=user)
        except models.ObjectDoesNotExist:
            vote = None
        return vote

    def get_for_user_in_bulk(self, objects, user):
        """
        Get a dictionary mapping object ids to votes made by the given
        user on the corresponding objects.
        """
        vote_dict = {}
        if len(objects) > 0:
            ctype = ContentType.objects.get_for_model(objects[0])
            votes = list(self.filter(content_type__pk=ctype.id,
                                     object_id__in=[obj._get_pk_val() \
                                                    for obj in objects],
                                     user__pk=user.id))
            vote_dict = dict([(vote.object_id, vote) for vote in votes])
        return vote_dict

########NEW FILE########
__FILENAME__ = models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.db import models

from voting.managers import VoteManager

SCORES = (
    (u'+1', +1),
    (u'-1', -1),
)

class Vote(models.Model):
    """
    A vote on an object by a User.
    """
    user         = models.ForeignKey(User)
    content_type = models.ForeignKey(ContentType)
    object_id    = models.PositiveIntegerField()
    object       = generic.GenericForeignKey('content_type', 'object_id')
    vote         = models.SmallIntegerField(choices=SCORES)

    objects = VoteManager()

    class Meta:
        db_table = 'votes'
        # One vote per user per object
        unique_together = (('user', 'content_type', 'object_id'),)

    def __unicode__(self):
        return u'%s: %s on %s' % (self.user, self.vote, self.object)

    def is_upvote(self):
        return self.vote == 1

    def is_downvote(self):
        return self.vote == -1

########NEW FILE########
__FILENAME__ = voting_tags
from django import template
from django.utils.html import escape

from voting.models import Vote

register = template.Library()

# Tags

class ScoreForObjectNode(template.Node):
    def __init__(self, object, context_var):
        self.object = object
        self.context_var = context_var

    def render(self, context):
        try:
            object = template.resolve_variable(self.object, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.context_var] = Vote.objects.get_score(object)
        return ''

class ScoresForObjectsNode(template.Node):
    def __init__(self, objects, context_var):
        self.objects = objects
        self.context_var = context_var

    def render(self, context):
        try:
            objects = template.resolve_variable(self.objects, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.context_var] = Vote.objects.get_scores_in_bulk(objects)
        return ''

class VoteByUserNode(template.Node):
    def __init__(self, user, object, context_var):
        self.user = user
        self.object = object
        self.context_var = context_var

    def render(self, context):
        try:
            user = template.resolve_variable(self.user, context)
            object = template.resolve_variable(self.object, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.context_var] = Vote.objects.get_for_user(object, user)
        return ''

class VotesByUserNode(template.Node):
    def __init__(self, user, objects, context_var):
        self.user = user
        self.objects = objects
        self.context_var = context_var

    def render(self, context):
        try:
            user = template.resolve_variable(self.user, context)
            objects = template.resolve_variable(self.objects, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.context_var] = Vote.objects.get_for_user_in_bulk(objects, user)
        return ''

class DictEntryForItemNode(template.Node):
    def __init__(self, item, dictionary, context_var):
        self.item = item
        self.dictionary = dictionary
        self.context_var = context_var

    def render(self, context):
        try:
            dictionary = template.resolve_variable(self.dictionary, context)
            item = template.resolve_variable(self.item, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.context_var] = dictionary.get(item.id, None)
        return ''

def do_score_for_object(parser, token):
    """
    Retrieves the total score for an object and the number of votes
    it's received and stores them in a context variable which has
    ``score`` and ``num_votes`` properties.

    Example usage::

        {% score_for_object widget as score %}

        {{ score.score }}point{{ score.score|pluralize }}
        after {{ score.num_votes }} vote{{ score.num_votes|pluralize }}
    """
    bits = token.contents.split()
    if len(bits) != 4:
        raise template.TemplateSyntaxError("'%s' tag takes exactly three arguments" % bits[0])
    if bits[2] != 'as':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'as'" % bits[0])
    return ScoreForObjectNode(bits[1], bits[3])

def do_scores_for_objects(parser, token):
    """
    Retrieves the total scores for a list of objects and the number of
    votes they have received and stores them in a context variable.

    Example usage::

        {% scores_for_objects widget_list as score_dict %}
    """
    bits = token.contents.split()
    if len(bits) != 4:
        raise template.TemplateSyntaxError("'%s' tag takes exactly three arguments" % bits[0])
    if bits[2] != 'as':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'as'" % bits[0])
    return ScoresForObjectsNode(bits[1], bits[3])

def do_vote_by_user(parser, token):
    """
    Retrieves the ``Vote`` cast by a user on a particular object and
    stores it in a context variable. If the user has not voted, the
    context variable will be ``None``.

    Example usage::

        {% vote_by_user user on widget as vote %}
    """
    bits = token.contents.split()
    if len(bits) != 6:
        raise template.TemplateSyntaxError("'%s' tag takes exactly five arguments" % bits[0])
    if bits[2] != 'on':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'on'" % bits[0])
    if bits[4] != 'as':
        raise template.TemplateSyntaxError("fourth argument to '%s' tag must be 'as'" % bits[0])
    return VoteByUserNode(bits[1], bits[3], bits[5])

def do_votes_by_user(parser, token):
    """
    Retrieves the votes cast by a user on a list of objects as a
    dictionary keyed with object ids and stores it in a context
    variable.

    Example usage::

        {% votes_by_user user on widget_list as vote_dict %}
    """
    bits = token.contents.split()
    if len(bits) != 6:
        raise template.TemplateSyntaxError("'%s' tag takes exactly four arguments" % bits[0])
    if bits[2] != 'on':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'on'" % bits[0])
    if bits[4] != 'as':
        raise template.TemplateSyntaxError("fourth argument to '%s' tag must be 'as'" % bits[0])
    return VotesByUserNode(bits[1], bits[3], bits[5])

def do_dict_entry_for_item(parser, token):
    """
    Given an object and a dictionary keyed with object ids - as
    returned by the ``votes_by_user`` and ``scores_for_objects``
    template tags - retrieves the value for the given object and
    stores it in a context variable, storing ``None`` if no value
    exists for the given object.

    Example usage::

        {% dict_entry_for_item widget from vote_dict as vote %}
    """
    bits = token.contents.split()
    if len(bits) != 6:
        raise template.TemplateSyntaxError("'%s' tag takes exactly five arguments" % bits[0])
    if bits[2] != 'from':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'from'" % bits[0])
    if bits[4] != 'as':
        raise template.TemplateSyntaxError("fourth argument to '%s' tag must be 'as'" % bits[0])
    return DictEntryForItemNode(bits[1], bits[3], bits[5])

register.tag('score_for_object', do_score_for_object)
register.tag('scores_for_objects', do_scores_for_objects)
register.tag('vote_by_user', do_vote_by_user)
register.tag('votes_by_user', do_votes_by_user)
register.tag('dict_entry_for_item', do_dict_entry_for_item)

# Simple Tags

def confirm_vote_message(object_description, vote_direction):
    """
    Creates an appropriate message asking the user to confirm the given vote
    for the given object description.

    Example usage::

        {% confirm_vote_message widget.title direction %}
    """
    if vote_direction == 'clear':
        message = 'Confirm clearing your vote for <strong>%s</strong>.'
    else:
        message = 'Confirm <strong>%s</strong> vote for <strong>%%s</strong>.' % vote_direction
    return message % (escape(object_description),)

register.simple_tag(confirm_vote_message)

# Filters

def vote_display(vote, arg=None):
    """
    Given a string mapping values for up and down votes, returns one
    of the strings according to the given ``Vote``:

    =========  =====================  =============
    Vote type   Argument               Outputs
    =========  =====================  =============
    ``+1``     ``"Bodacious,Bogus"``  ``Bodacious``
    ``-1``     ``"Bodacious,Bogus"``  ``Bogus``
    =========  =====================  =============

    If no string mapping is given, "Up" and "Down" will be used.

    Example usage::

        {{ vote|vote_display:"Bodacious,Bogus" }}
    """
    if arg is None:
        arg = 'Up,Down'
    bits = arg.split(',')
    if len(bits) != 2:
        return vote.vote # Invalid arg
    up, down = bits
    if vote.vote == 1:
        return up
    return down

register.filter(vote_display)
########NEW FILE########
__FILENAME__ = models
from django.db import models

class Item(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

########NEW FILE########
__FILENAME__ = runtests
import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'voting.tests.settings'

from django.test.simple import run_tests

failures = run_tests(None, verbosity=9)
if failures:
    sys.exit(failures)

########NEW FILE########
__FILENAME__ = settings
import os

DIRNAME = os.path.dirname(__file__)

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = os.path.join(DIRNAME, 'database.db')

#DATABASE_ENGINE = 'mysql'
#DATABASE_NAME = 'tagging_test'
#DATABASE_USER = 'root'
#DATABASE_PASSWORD = ''
#DATABASE_HOST = 'localhost'
#DATABASE_PORT = '3306'

#DATABASE_ENGINE = 'postgresql_psycopg2'
#DATABASE_NAME = 'tagging_test'
#DATABASE_USER = 'postgres'
#DATABASE_PASSWORD = ''
#DATABASE_HOST = 'localhost'
#DATABASE_PORT = '5432'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'voting',
    'voting.tests',
)

########NEW FILE########
__FILENAME__ = tests
r"""
>>> from django.contrib.auth.models import User
>>> from voting.models import Vote
>>> from voting.tests.models import Item

##########
# Voting #
##########

# Basic voting ###############################################################

>>> i1 = Item.objects.create(name='test1')
>>> users = []
>>> for username in ['u1', 'u2', 'u3', 'u4']:
...     users.append(User.objects.create_user(username, '%s@test.com' % username, 'test'))
>>> Vote.objects.get_score(i1)
{'score': 0, 'num_votes': 0}
>>> Vote.objects.record_vote(i1, users[0], +1)
>>> Vote.objects.get_score(i1)
{'score': 1, 'num_votes': 1}
>>> Vote.objects.record_vote(i1, users[0], -1)
>>> Vote.objects.get_score(i1)
{'score': -1, 'num_votes': 1}
>>> Vote.objects.record_vote(i1, users[0], 0)
>>> Vote.objects.get_score(i1)
{'score': 0, 'num_votes': 0}
>>> for user in users:
...     Vote.objects.record_vote(i1, user, +1)
>>> Vote.objects.get_score(i1)
{'score': 4, 'num_votes': 4}
>>> for user in users[:2]:
...     Vote.objects.record_vote(i1, user, 0)
>>> Vote.objects.get_score(i1)
{'score': 2, 'num_votes': 2}
>>> for user in users[:2]:
...     Vote.objects.record_vote(i1, user, -1)
>>> Vote.objects.get_score(i1)
{'score': 0, 'num_votes': 4}

>>> Vote.objects.record_vote(i1, user, -2)
Traceback (most recent call last):
    ...
ValueError: Invalid vote (must be +1/0/-1)

# Retrieval of votes #########################################################

>>> i2 = Item.objects.create(name='test2')
>>> i3 = Item.objects.create(name='test3')
>>> i4 = Item.objects.create(name='test4')
>>> Vote.objects.record_vote(i2, users[0], +1)
>>> Vote.objects.record_vote(i3, users[0], -1)
>>> Vote.objects.record_vote(i4, users[0], 0)
>>> vote = Vote.objects.get_for_user(i2, users[0])
>>> (vote.vote, vote.is_upvote(), vote.is_downvote())
(1, True, False)
>>> vote = Vote.objects.get_for_user(i3, users[0])
>>> (vote.vote, vote.is_upvote(), vote.is_downvote())
(-1, False, True)
>>> Vote.objects.get_for_user(i4, users[0]) is None
True

# In bulk
>>> votes = Vote.objects.get_for_user_in_bulk([i1, i2, i3, i4], users[0])
>>> [(id, vote.vote) for id, vote in votes.items()]
[(1, -1), (2, 1), (3, -1)]
>>> Vote.objects.get_for_user_in_bulk([], users[0])
{}

>>> for user in users[1:]:
...     Vote.objects.record_vote(i2, user, +1)
...     Vote.objects.record_vote(i3, user, +1)
...     Vote.objects.record_vote(i4, user, +1)
>>> list(Vote.objects.get_top(Item))
[(<Item: test2>, 4), (<Item: test4>, 3), (<Item: test3>, 2)]
>>> for user in users[1:]:
...     Vote.objects.record_vote(i2, user, -1)
...     Vote.objects.record_vote(i3, user, -1)
...     Vote.objects.record_vote(i4, user, -1)
>>> list(Vote.objects.get_bottom(Item))
[(<Item: test3>, -4), (<Item: test4>, -3), (<Item: test2>, -2)]

>>> Vote.objects.get_scores_in_bulk([i1, i2, i3, i4])
{1: {'score': 0, 'num_votes': 4}, 2: {'score': -2, 'num_votes': 4}, 3: {'score': -4, 'num_votes': 4}, 4: {'score': -3, 'num_votes': 3}}
>>> Vote.objects.get_scores_in_bulk([])
{}
"""

########NEW FILE########
__FILENAME__ = views
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.contrib.auth.views import redirect_to_login
from django.template import loader, RequestContext
from django.utils import simplejson

from voting.models import Vote

VOTE_DIRECTIONS = (('up', 1), ('down', -1), ('clear', 0))

def vote_on_object(request, model, direction, post_vote_redirect=None,
        object_id=None, slug=None, slug_field=None, template_name=None,
        template_loader=loader, extra_context=None, context_processors=None,
        template_object_name='object', allow_xmlhttprequest=False):
    """
    Generic object vote function.

    The given template will be used to confirm the vote if this view is
    fetched using GET; vote registration will only be performed if this
    view is POSTed.

    If ``allow_xmlhttprequest`` is ``True`` and an XMLHttpRequest is
    detected by examining the ``HTTP_X_REQUESTED_WITH`` header, the
    ``xmlhttp_vote_on_object`` view will be used to process the
    request - this makes it trivial to implement voting via
    XMLHttpRequest with a fallback for users who don't have JavaScript
    enabled.

    Templates:``<app_label>/<model_name>_confirm_vote.html``
    Context:
        object
            The object being voted on.
        direction
            The type of vote which will be registered for the object.
    """
    if allow_xmlhttprequest and request.is_ajax():
        return xmlhttprequest_vote_on_object(request, model, direction,
                                             object_id=object_id, slug=slug,
                                             slug_field=slug_field)

    if extra_context is None: extra_context = {}
    if not request.user.is_authenticated():
        return redirect_to_login(request.path)

    try:
        vote = dict(VOTE_DIRECTIONS)[direction]
    except KeyError:
        raise AttributeError("'%s' is not a valid vote type." % vote_type)

    # Look up the object to be voted on
    lookup_kwargs = {}
    if object_id:
        lookup_kwargs['%s__exact' % model._meta.pk.name] = object_id
    elif slug and slug_field:
        lookup_kwargs['%s__exact' % slug_field] = slug
    else:
        raise AttributeError('Generic vote view must be called with either '
                             'object_id or slug and slug_field.')
    try:
        obj = model._default_manager.get(**lookup_kwargs)
    except ObjectDoesNotExist:
        raise Http404, 'No %s found for %s.' % (model._meta.app_label, lookup_kwargs)

    if request.method == 'POST':
        if post_vote_redirect is not None:
            next = post_vote_redirect
        elif request.REQUEST.has_key('next'):
            next = request.REQUEST['next']
        elif hasattr(obj, 'get_absolute_url'):
            if callable(getattr(obj, 'get_absolute_url')):
                next = obj.get_absolute_url()
            else:
                next = obj.get_absolute_url
        else:
            raise AttributeError('Generic vote view must be called with either '
                                 'post_vote_redirect, a "next" parameter in '
                                 'the request, or the object being voted on '
                                 'must define a get_absolute_url method or '
                                 'property.')
        Vote.objects.record_vote(obj, request.user, vote)
        return HttpResponseRedirect(next)
    else:
        if not template_name:
            template_name = '%s/%s_confirm_vote.html' % (
                model._meta.app_label, model._meta.object_name.lower())
        t = template_loader.get_template(template_name)
        c = RequestContext(request, {
            template_object_name: obj,
            'direction': direction,
        }, context_processors)
        for key, value in extra_context.items():
            if callable(value):
                c[key] = value()
            else:
                c[key] = value
        response = HttpResponse(t.render(c))
        return response

def json_error_response(error_message):
    return HttpResponse(simplejson.dumps(dict(success=False,
                                              error_message=error_message)))

def xmlhttprequest_vote_on_object(request, model, direction,
    object_id=None, slug=None, slug_field=None):
    """
    Generic object vote function for use via XMLHttpRequest.

    Properties of the resulting JSON object:
        success
            ``true`` if the vote was successfully processed, ``false``
            otherwise.
        score
            The object's updated score and number of votes if the vote
            was successfully processed.
        error_message
            Contains an error message if the vote was not successfully
            processed.
    """
    if request.method == 'GET':
        return json_error_response(
            'XMLHttpRequest votes can only be made using POST.')
    if not request.user.is_authenticated():
        return json_error_response('Not authenticated.')

    try:
        vote = dict(VOTE_DIRECTIONS)[direction]
    except KeyError:
        return json_error_response(
            '\'%s\' is not a valid vote type.' % direction)

    # Look up the object to be voted on
    lookup_kwargs = {}
    if object_id:
        lookup_kwargs['%s__exact' % model._meta.pk.name] = object_id
    elif slug and slug_field:
        lookup_kwargs['%s__exact' % slug_field] = slug
    else:
        return json_error_response('Generic XMLHttpRequest vote view must be '
                                   'called with either object_id or slug and '
                                   'slug_field.')
    try:
        obj = model._default_manager.get(**lookup_kwargs)
    except ObjectDoesNotExist:
        return json_error_response(
            'No %s found for %s.' % (model._meta.verbose_name, lookup_kwargs))

    # Vote and respond
    Vote.objects.record_vote(obj, request.user, vote)
    return HttpResponse(simplejson.dumps({
        'success': True,
        'score': Vote.objects.get_score(obj),
    }))

########NEW FILE########
