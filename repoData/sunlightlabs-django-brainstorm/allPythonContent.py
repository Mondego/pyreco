__FILENAME__ = admin
from django.contrib import admin
from brainstorm.models import Subsite, Idea

class SubsiteAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name')

class IdeaAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'subsite')
    list_filter = ('subsite',)

admin.site.register(Subsite, SubsiteAdmin)
admin.site.register(Idea, IdeaAdmin)

########NEW FILE########
__FILENAME__ = feeds
from django.contrib.syndication.feeds import Feed, FeedDoesNotExist
from brainstorm.models import Subsite

class SubsiteFeed(Feed):

    title_template = 'brainstorm/feed_title.html'
    description_template = 'brainstorm/feed_description.html'

    def get_object(self, bits):
        return Subsite.objects.get(slug__exact=bits[0])

    def title(self, obj):
        return 'Latest ideas submitted for %s' % obj.name

    def description(self, obj):
        return 'Latest ideas submitted for %s' % obj.name

    def link(self, obj):
        if not obj:
            raise FeedDoesNotExist
        return obj.get_absolute_url()

    def items(self, obj):
        return obj.ideas.order_by('-submit_date')[:30]

    def item_link(self, item):
        return item.get_absolute_url()

    def item_author_name(self, item):
        return item.user

    def item_pubdate(self, item):
        return item.submit_date


########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.contrib.contenttypes import generic
from django.contrib.comments.models import Comment
from django.db.models.signals import post_save

ALLOW_ALL, REQUIRE_LOGIN, DISALLOW_ALL = range(3)
SUBSITE_POST_STATUS = (
    (ALLOW_ALL, 'Allow All Posts'),
    (REQUIRE_LOGIN, 'Require Login'),
    (DISALLOW_ALL, 'Allow No Posts'),
)

class Subsite(models.Model):
    slug = models.SlugField(max_length=50, primary_key=True)
    name = models.CharField(max_length=50)
    description = models.TextField()

    theme = models.CharField(help_text='name of base theme template', max_length=100)

    ideas_per_page = models.IntegerField(default=10)
    post_status = models.IntegerField(default=ALLOW_ALL, choices=SUBSITE_POST_STATUS)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('ideas_popular', args=[self.slug])

    def user_can_post(self, user):
        if self.post_status == DISALLOW_ALL:
            return False
        elif self.post_status == ALLOW_ALL:
            return True
        elif self.post_status == REQUIRE_LOGIN:
            return not user.is_anonymous()

class IdeaManager(models.Manager):

    def with_user_vote(self, user):
        return self.extra(select={'user_vote':'SELECT value FROM brainstorm_vote WHERE idea_id=brainstorm_idea.id AND user_id=%s'}, select_params=[user.id])

class Idea(models.Model):

    title = models.CharField(max_length=100)
    description = models.TextField()
    score = models.IntegerField(default=0)

    submit_date = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(User, null=True, related_name='ideas')
    subsite = models.ForeignKey(Subsite, related_name='ideas')

    comments = generic.GenericRelation(Comment, object_id_field='object_pk')

    objects = IdeaManager()

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('idea_detail', args=[self.subsite_id, self.id])

class Vote(models.Model):
    user = models.ForeignKey(User, related_name='idea_votes')
    idea = models.ForeignKey(Idea, related_name='votes')
    value = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return '%s %s on %s' % (self.user, self.value, self.idea)

    class Meta:
        unique_together = (('user', 'idea'),)

def update_idea_votes(sender, instance, created, **kwargs):
    score = instance.idea.votes.aggregate(score=models.Sum('value'))['score']
    instance.idea.score = score
    instance.idea.save()
post_save.connect(update_idea_votes, sender=Vote)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from brainstorm.models import Idea
from brainstorm.feeds import SubsiteFeed

BRAINSTORM_USE_SECRETBALLOT = getattr(settings, 'BRAINSTORM_USE_SECRETBALLOT', False)

feeds = {
    'latest': SubsiteFeed,
}

# feeds live at rss/latest/site-name/
urlpatterns = patterns('',
    url(r'^rss/(?P<url>.*)/$', 'django.contrib.syndication.views.feed',
        {'feed_dict': feeds}),
)

urlpatterns += patterns('brainstorm.views',
    url(r'^(?P<slug>[\w-]+)/$', 'idea_list', {'ordering': 'most_popular'}, name='ideas_popular'),
    url(r'^(?P<slug>[\w-]+)/latest/$', 'idea_list', {'ordering': 'latest'}, name='ideas_latest'),
    url(r'^(?P<slug>[\w-]+)/(?P<id>\d+)/$', 'idea_detail', name='idea_detail'),
    url(r'^(?P<slug>[\w-]+)/new_idea/$', 'new_idea', name='new_idea'),
    url(r'^vote/$', 'vote', name='idea_vote'),
)

if BRAINSTORM_USE_SECRETBALLOT:
    urlpatterns = patterns('secretballot.views',
        url(r'^vote_up/(?P<object_id>\d+)/$', 'vote',
            {'content_type': ContentType.objects.get_for_model(Idea), 'vote': 1},
              name='vote_up'),
        url(r'^vote_down/(?P<object_id>\d+)/$', 'vote',
            {'content_type': ContentType.objects.get_for_model(Idea), 'vote': -1},
              name='vote_down'),
        url(r'^unvote/(?P<object_id>\d+)/$', 'vote',
            {'content_type': ContentType.objects.get_for_model(Idea), 'vote': 0},
              name='unvote'),
    ) + urlpatterns


########NEW FILE########
__FILENAME__ = views
import datetime
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.http import HttpResponse
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.views.generic import list_detail
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings
from brainstorm.models import Subsite, Idea, Vote

def idea_list(request, slug, ordering='-total_upvotes'):
    ordering_db = {'most_popular': '-score',
                   'latest': '-submit_date'}[ordering]
    qs = Idea.objects.with_user_vote(request.user).filter(subsite__slug=slug).select_related().order_by(ordering_db)
    if hasattr(qs, '_gatekeeper'):
        qs = qs.approved()
    return list_detail.object_list(request, queryset=qs,
        extra_context={'ordering': ordering, 'subsite':slug}, paginate_by=10,
        template_object_name='idea')

def idea_detail(request, slug, id):
    idea = get_object_or_404(Idea.objects.with_user_vote(request.user), pk=id, subsite__slug=slug)
    return render_to_response('brainstorm/idea_detail.html',
                              {'idea': idea},
                              context_instance=RequestContext(request))

@require_POST
def new_idea(request, slug):
    subsite = get_object_or_404(Subsite, pk=slug)
    if not subsite.user_can_post(request.user):
        return redirect(subsite.get_absolute_url())
    title = request.POST['title']
    description = request.POST['description']
    if not title.strip() or not description.strip():
        return redirect(subsite.get_absolute_url())
    user = request.user
    idea = Idea.objects.create(title=title, description=description, user=user,
                               subsite=subsite)
    return redirect(idea)

@require_POST
@login_required
def vote(request):
    idea_id = int(request.POST.get('idea'))
    score = int(request.POST.get('score'))
    if score not in (0,1):
        score = 0
    idea = get_object_or_404(Idea, pk=idea_id)
    score_diff = score
    vote, created = Vote.objects.get_or_create(user=request.user, idea=idea,
                                               defaults={'value':score})
    if not created:
        new_score = idea.score + (score-vote.value)
        vote.value = score
        vote.save()
    else:
        new_score = idea.score

    if request.is_ajax():
        return HttpResponse("{'score':%d}" % new_score)

    return redirect(idea)

########NEW FILE########
