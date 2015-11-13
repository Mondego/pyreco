__FILENAME__ = admin
from django.contrib import admin

from aiteo.models import Question, Response


class ResponseInline(admin.StackedInline):
    model = Response


class QuestionAdmin(admin.ModelAdmin):
    inlines = [
        ResponseInline,
    ]


admin.site.register(Question, QuestionAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms

from aiteo.models import Question, Response


class AskQuestionForm(forms.ModelForm):
    
    class Meta:
        model = Question
        fields = ["question", "content"]


class AddResponseForm(forms.ModelForm):
    
    class Meta:
        model = Response
        fields = ["content"]

########NEW FILE########
__FILENAME__ = models
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone

from django.contrib.auth.models import User

from aiteo.signals import voted, vote_cleared


class TimestampModel(models.Model):
    created = models.DateTimeField(default=timezone.now)
    modified = models.DateTimeField(default=timezone.now)
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        self.modified = timezone.now()
        return super(TimestampModel, self).save(*args, **kwargs)


class ScoringModel(TimestampModel):
    score = models.IntegerField(editable=False, default=0)
    vote_count = models.IntegerField(editable=False, default=0)
    
    class Meta:
        abstract = True
    
    def vote(self, user, upvote):
        vote, created = self.votes.get_or_create(user=user, defaults={"upvote": upvote})
        if hasattr(vote, "response"):
            vote_obj = vote.response
        else:
            vote_obj = vote.question
        changed = not created and (vote.upvote != upvote)
        if changed:
            vote.delete()
        if changed or created:
            self.update_score()
        if changed:
            vote_cleared.send(sender=vote.__class__, vote_obj=vote_obj, was_upvote=upvote)
        if created:
            voted.send(sender=vote.__class__, vote_obj=vote_obj, upvote=upvote)
    
    def update_score(self):
        votes = self.votes.count()
        upvotes = self.votes.filter(upvote=True).count()
        downvotes = votes - upvotes
        self.score = upvotes - downvotes
        self.vote_count = votes
        self.save()


class Question(ScoringModel):
    
    question = models.CharField(max_length=100)
    content = models.TextField()
    user = models.ForeignKey(User, related_name="questions")
    
    @property
    def accepted_response(self):
        try:
            response = self.responses.get(accepted=True)
        except Response.DoesNotExist:
            response = None
        return response
    
    def get_absolute_url(self):
        return reverse("aiteo_question_detail", args=[self.pk])


class Response(ScoringModel):
    
    question = models.ForeignKey(Question, related_name="responses")
    content = models.TextField()
    accepted = models.BooleanField(default=False)
    user = models.ForeignKey(User, related_name="responses")
    
    def accept(self):
        # check for another active one and mark it inactive
        try:
            response = Response.objects.get(question=self.question, accepted=True)
        except Response.DoesNotExist:
            pass
        else:
            if self != response:
                response.accepted = False
                response.save()
        self.accepted = True
        self.save()
    
    def get_absolute_url(self):
        return "%s#response-%d" % (self.question.get_absolute_url(), self.pk)


class QuestionVote(TimestampModel):
    question = models.ForeignKey(Question, related_name="votes")
    upvote = models.BooleanField(default=True)
    user = models.ForeignKey(User, related_name="question_votes")
    
    class Meta:
        unique_together = [("question", "user")]


class ResponseVote(TimestampModel):
    response = models.ForeignKey(Response, related_name="votes")
    upvote = models.BooleanField(default=True)
    user = models.ForeignKey(User, related_name="response_votes")
    
    class Meta:
        unique_together = [("response", "user")]

########NEW FILE########
__FILENAME__ = signals
import django.dispatch


voted = django.dispatch.Signal(providing_args=["vote_obj", "upvote"])
vote_cleared = django.dispatch.Signal(providing_args=["vote_obj", "was_upvote"])

########NEW FILE########
__FILENAME__ = aiteo_tags
from django import template
from django.conf import settings
from django.utils.importlib import import_module


workflow = import_module(getattr(settings, "AITEO_WORKFLOW_MODULE", "aiteo.workflow"))
register = template.Library()


@register.filter
def can_accept(user, response):
    return workflow.can_mark_accepted(user, response.question)


@register.filter
def voted_up(user, obj):
    return obj.votes.filter(user=user, upvote=True).exists()


@register.filter
def voted_down(user, obj):
    return obj.votes.filter(user=user, upvote=False).exists()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url


urlpatterns = patterns("aiteo.views",
    url(r"^$", "question_list", name="aiteo_question_list"),
    url(r"^ask/$", "question_create", name="aiteo_question_create"),
    url(r"^questions/(?P<pk>\d+)/$", "question_detail", name="aiteo_question_detail"),
    url(r"^questions/(?P<pk>\d+)/upvote/$", "question_upvote", name="aiteo_question_upvote"),
    url(r"^questions/(?P<pk>\d+)/downvote/$", "question_downvote", name="aiteo_question_downvote"),
    url(r"^responses/(?P<pk>\d+)/upvote/$", "response_upvote", name="aiteo_response_upvote"),
    url(r"^responses/(?P<pk>\d+)/downvote/$", "response_downvote", name="aiteo_response_downvote"),
    url(r"^responses/(?P<pk>\d+)/accept/$", "mark_accepted", name="aiteo_mark_accepted"),
)

########NEW FILE########
__FILENAME__ = views
import json

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.importlib import import_module
from django.views.decorators.http import require_POST

from account.decorators import login_required
from aiteo.forms import AskQuestionForm, AddResponseForm
from aiteo.models import Question, Response


workflow = import_module(getattr(settings, "AITEO_WORKFLOW_MODULE", "aiteo.workflow"))


def question_list(request):
    questions = Question.objects.all().order_by("-score", "created", "id")
    ctx = {
        "questions": questions,
    }
    return render(request, "aiteo/question_list.html", ctx)


@login_required
def question_create(request):
    if request.method == "POST":
        form = AskQuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.user = request.user
            question.save()
            return HttpResponseRedirect(question.get_absolute_url())
    else:
        form = AskQuestionForm()
    ctx = {
        "form": form,
    }
    return render(request, "aiteo/question_create.html", ctx)


def question_detail(request, pk):
    questions = Question.objects.all()
    question = get_object_or_404(questions, pk=pk)
    responses = question.responses.order_by("-score", "created", "id")
    is_me = question.user == request.user
    if request.method == "POST":
        add_response_form = AddResponseForm(request.POST)
        if add_response_form.is_valid():
            response = add_response_form.save(commit=False)
            response.question = question
            response.user = request.user
            response.save()
            return HttpResponseRedirect(response.get_absolute_url())
    else:
        if not is_me or request.user.is_staff:
            add_response_form = AddResponseForm()
        else:
            add_response_form = None
    ctx = {
        "can_mark_accepted": workflow.can_mark_accepted(request.user, question),
        "question": question,
        "responses": responses,
        "add_response_form": add_response_form,
    }
    return render(request, "aiteo/question_detail.html", ctx)


@login_required
@require_POST
def mark_accepted(request, pk):
    response = get_object_or_404(Response, pk=pk)
    if not workflow.can_mark_accepted(request.user, response.question):
        return HttpResponseForbidden("You are not allowed to mark this question accepted.")
    
    response.accept()
    
    data = {"fragments": {}}
    for resp in response.question.responses.all():
        data["fragments"]["#accepted-{}".format(resp.pk)] = render_to_string(
            "aiteo/_accepted.html",
            {"response": resp},
            context_instance=RequestContext(request)
        )
    return HttpResponse(json.dumps(data), mimetype="application/json")


@login_required
@require_POST
def question_upvote(request, pk):
    question = get_object_or_404(Question, pk=pk)
    question.vote(user=request.user, upvote=True)
    data = {
        "html": render_to_string("aiteo/_question_vote_badge.html", {
            "question": question
        }, context_instance=RequestContext(request))
    }
    return HttpResponse(json.dumps(data), mimetype="application/json")


@login_required
@require_POST
def question_downvote(request, pk):
    question = get_object_or_404(Question, pk=pk)
    question.vote(user=request.user, upvote=False)
    data = {
        "html": render_to_string("aiteo/_question_vote_badge.html", {
            "question": question
        }, context_instance=RequestContext(request))
    }
    return HttpResponse(json.dumps(data), mimetype="application/json")


@login_required
@require_POST
def response_upvote(request, pk):
    response = get_object_or_404(Response, pk=pk)
    response.vote(user=request.user, upvote=True)
    data = {
        "html": render_to_string("aiteo/_response_vote_badge.html", {
            "response": response
        }, context_instance=RequestContext(request))
    }
    return HttpResponse(json.dumps(data), mimetype="application/json")


@login_required
@require_POST
def response_downvote(request, pk):
    response = get_object_or_404(Response, pk=pk)
    response.vote(user=request.user, upvote=False)
    data = {
        "html": render_to_string("aiteo/_response_vote_badge.html", {
            "response": response
        }, context_instance=RequestContext(request))
    }
    return HttpResponse(json.dumps(data), mimetype="application/json")

########NEW FILE########
__FILENAME__ = workflow

def can_mark_accepted(user, question):
    return question.user == user

########NEW FILE########
