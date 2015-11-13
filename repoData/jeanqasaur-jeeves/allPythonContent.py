__FILENAME__ = forms
from django.forms import Form, ModelForm, CharField, FileField, Textarea, ModelForm, HiddenInput, MultipleChoiceField, CheckboxSelectMultiple, BooleanField, ChoiceField

from models import Paper, PaperVersion, UserProfile, Review, ReviewAssignment, Comment, UserPCConflict
from django.contrib.auth.models import User
import random
from django.forms.formsets import formset_factory

class SubmitForm(Form):
    coauthor1 = CharField(required=False)
    coauthor2 = CharField(required=False)
    coauthor3 = CharField(required=False)

    title = CharField(1024, required=True)
    contents = FileField(required=True)
    abstract = CharField(widget=Textarea, required=True)

    def __init__(self, possible_reviewers, default_conflict_reviewers, *args, **kwargs):
        super(SubmitForm, self).__init__(*args, **kwargs)

        choices = []
        for r in possible_reviewers:
            choices.append((r.username, r))

        self.fields['conflicts'] = MultipleChoiceField(widget=CheckboxSelectMultiple(), required=False, choices=choices, initial=list(default_conflict_reviewers))

    def is_valid(self):
        if not super(SubmitForm, self).is_valid():
            return False

        try:
            coauthors = []
            for coauthor_id in ['coauthor1', 'coauthor2', 'coauthor3']:
                if coauthor_id in self.cleaned_data and self.cleaned_data[coauthor_id]:
                    coauthor = User.objects.filter(username=self.cleaned_data[coauthor_id]).get()
                    coauthors.append(coauthor)
        except User.DoesNotExist:
            return False

        self.cleaned_data['coauthors'] = coauthors
        return True

    def save(self, user):
        d = self.cleaned_data
        
        authors = [user]
        if 'coauthor1' in d:
            authors.append(d['coauthor1'])
        if 'coauthor2' in d:
            authors.append(d['coauthor2'])
        if 'coauthor3' in d:
            authors.append(d['coauthor3'])

        paper = Paper()
        paper.save()

        paper.authors.add(user)
        for coauthor in d['coauthors']:
            paper.authors.add(coauthor)
        paper.save()

        d['contents'].name = '%030x' % random.randrange(16**30) + ".pdf"

        paper_version = PaperVersion(
            paper = paper,
            title = d['title'],
            abstract = d['abstract'],
            contents = d['contents'],
        )
        paper_version.save()

        # need to save paper twice since paper and paper_version point to each other...
        paper.latest_version = paper_version
        paper.save()

        for conflict_username in d['conflicts']:
            ra = ReviewAssignment()
            ra.user = User.objects.get(username=conflict_username)
            ra.paper = paper
            ra.type = 'conflict'
            ra.save()

        return paper

class SubmitReviewForm(ModelForm):
    class Meta:
        model = Review
        fields = ['contents', 'score_novelty', 'score_presentation', 'score_technical', 'score_confidence']

class SubmitCommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['contents']

class ReviewAssignmentForm(ModelForm):
    class Meta:
        model = ReviewAssignment
        fields = ['assign_type', 'user', 'paper']
        widgets = {
            'user' : HiddenInput(),
            'paper' : HiddenInput(),
        }

ReviewAssignmentFormset = formset_factory(ReviewAssignmentForm, extra=0)

class SearchForm(Form):
    # should only show accepted papers
    filter_accepted = BooleanField(required=False)

    # should only show papers accepted by a reviewer
    # filter_reviewer (defined in __init__ below)

    # should only show papers by the given author
    # filter_author (defined in __init__ below)

    filter_title_contains = CharField(required=False)

    sort_by = ChoiceField(required=True,
                            choices=(('---', None),
                                     ('title', 'title'),
                                     ('score_technical', 'score_technical'),
                                    ))

    def __init__(self, *args, **kwargs):
        reviewers = kwargs['reviewers']
        authors = kwargs['authors']
        del kwargs['reviewers']
        del kwargs['authors']

        super(SearchForm, self).__init__(*args, **kwargs)
        
        self.fields['filter_reviewer'] = ChoiceField(required=False,
            choices=[('', '---')] + [(r.username, r) for r in reviewers])
        self.fields['filter_author'] = ChoiceField(required=False,
            choices=[('', '---')] + [(r.username, r) for r in authors])

    def get_results(self):
        d = self.cleaned_data

        query = Paper.objects

        # TODO enable support for accepting papers and then enable this
        #if d['filter_accepted']:
        #    query = query.filter(

        if d.get('filter_reviewer', ''):
            query = query.filter(authors__username=d['filter_reviewer'])

        if d.get('filter_author', ''):
            query = query.filter(reviewers__username=d['filter_author'])

        if d.get('filter_title_contains', ''):
            query = query.filter(latest_version__title__contains=d['filter_title_contains'])

        if d.get('sort_by','') == 'title':
            query = query.order_by('latest_version__title')
        elif d.get('sort_by','') == 'score_technical':
            query = query.order_by('latest_version__score_technical')

        print query.query.__str__()
        results = list(query.all())

        return list(results)

########NEW FILE########
__FILENAME__ = models
from django.db.models import Model, ManyToManyField, ForeignKey, CharField, TextField, DateTimeField, IntegerField, FileField, BooleanField

from jeevesdb.JeevesModel import JeevesModel as Model
from jeevesdb.JeevesModel import JeevesForeignKey as ForeignKey
from jeevesdb.JeevesModel import label_for

from sourcetrans.macro_module import macros, jeeves
import JeevesLib

from settings import CONF_PHASE as phase

class UserProfile(Model):
    username = CharField(max_length=1024)
    email = CharField(max_length=1024)

    name = CharField(max_length=1024)
    affiliation = CharField(max_length=1024)
    acm_number = CharField(max_length=1024)

    level = CharField(max_length=12,
                    choices=(('normal', 'normal'),
                        ('pc', 'pc'),
                        ('chair', 'chair')))

    @staticmethod
    def jeeves_get_private_email(user):
        return ""

    @staticmethod
    @label_for('email')
    @jeeves
    def jeeves_restrict_userprofilelabel(user, ctxt):
        return user == ctxt or (ctxt != None and ctxt.level == 'chair')

    class Meta:
        db_table = 'user_profiles'

class UserPCConflict(Model):
    user = ForeignKey(UserProfile, null=True, related_name='userpcconflict_user')
    pc = ForeignKey(UserProfile, null=True, related_name='userpcconflict_pc')

    @staticmethod
    def jeeves_get_private_user(uppc):
        return None
    @staticmethod
    def jeeves_get_private_pc(uppc):
        return None

    @staticmethod
    @label_for('user', 'pc')
    @jeeves
    def jeeves_restrict_userpcconflictlabel(uppc, ctxt):
        return True
        #return ctxt.level == 'chair' or uppc.user == ctxt

class Paper(Model):
    #latest_version = ForeignKey('PaperVersion', related_name='latest_version_of', null=True)
    # add this below because of cyclic dependency; awkward hack
    # (limitation of JeevesModel not ordinary Model)
    author = ForeignKey(UserProfile, null=True)
    accepted = BooleanField()

    @staticmethod
    def jeeves_get_private_author(paper):
        return None

    @staticmethod
    @label_for('author')
    @jeeves
    def jeeves_restrict_paperlabel(paper, ctxt):
        if phase == 'final':
            return True
        else:
            if paper == None:
                return False
            if PaperPCConflict.objects.get(paper=paper, pc=ctxt) != None:
                return False

            return (paper != None and paper.author == ctxt) or (ctxt != None and (ctxt.level == 'chair' or ctxt.level == 'pc'))

    class Meta:
        db_table = 'papers'

class PaperPCConflict(Model):
    paper = ForeignKey(Paper, null=True)
    pc = ForeignKey(UserProfile, null=True)

    @staticmethod
    def jeeves_get_private_paper(ppcc): return None
    @staticmethod
    def jeeves_get_private_pc(ppcc): return None

    @staticmethod
    @label_for('paper', 'pc')
    @jeeves
    def jeeves_restrict_paperpcconflictlabel(ppcc, ctxt):
        return True
        #return ctxt.level == 'admin' or (ppcc.paper != None and ppcc.paper.author == ctxt)

class PaperCoauthor(Model):
    paper = ForeignKey(Paper, null=True)
    author = CharField(max_length=1024)

    @staticmethod
    def jeeves_get_private_paper(pco): return None
    @staticmethod
    def jeeves_get_private_author(pco): return ""

    @staticmethod
    @label_for('paper', 'author')
    @jeeves
    def jeeves_restrict_papercoauthorlabel(pco, ctxt):
        if pco.paper == None:
            return False
        if PaperPCConflict.objects.get(paper=pco.paper, pc=ctxt) != None:
            return False
        ans = ctxt.level == 'pc' or ctxt.level == 'chair' or (pco.paper != None and pco.paper.author == ctxt)
        return ans

#class PaperReviewer(Model):
#    paper = ForeignKey(Paper, null=True)
#    reviewer = ForeignKey(UserProfile, null=True)

#    @staticmethod
#    def jeeves_get_private_paper(pco): return None
#    @staticmethod
#    def jeeves_get_private_reviewer(pco): return None

#    @staticmethod
#    @label_for('paper', 'reviewer')
#    @jeeves
#    def jeeves_restrict_paperreviewerlabel(prv, ctxt):
#        return ctxt.level == 'pc' or ctxt.level == 'chair'

class ReviewAssignment(Model):
    paper = ForeignKey(Paper, null=True)
    user = ForeignKey(UserProfile, null=True)
    assign_type = CharField(max_length=8, null=True,
        choices=(('none','none'),
                ('assigned','assigned'),
                ('conflict','conflict')))

    class Meta:
        db_table = 'review_assignments'

    @staticmethod
    def jeeves_get_private_paper(rva): return None
    @staticmethod
    def jeeves_get_private_user(rva): return None
    @staticmethod
    def jeeves_get_private_assign_type(rva): return 'none'

    @staticmethod
    @label_for('paper', 'user', 'assign_type')
    @jeeves
    def jeeves_restrict_paperreviewerlabel(prv, ctxt):
        if prv != None and PaperPCConflict.objects.get(paper=prv.paper, pc=ctxt) != None:
            return False
        return ctxt.level == 'pc' or ctxt.level == 'chair'

class PaperVersion(Model):
    paper = ForeignKey(Paper, null=True)

    title = CharField(max_length=1024)
    contents = FileField(upload_to='papers')
    abstract = TextField()
    time = DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'paper_versions'

    @staticmethod
    @label_for('paper', 'title', 'contents', 'abstract')
    @jeeves
    def jeeves_restrict_paperversionlabel(pv, ctxt):
        if pv == None or pv.paper == None:
            return False
        if PaperPCConflict.objects.get(paper=pv.paper, pc=ctxt) != None:
            return False
        return (pv.paper != None and pv.paper.author == ctxt) or ctxt.level == 'pc' or ctxt.level == 'chair'
    
    @staticmethod
    def jeeves_get_private_paper(pv): return None
    @staticmethod
    def jeeves_get_private_title(pv): return ""
    @staticmethod
    def jeeves_get_private_contents(pv): return ""
    @staticmethod
    def jeeves_get_private_abstract(pv): return ""

# see comment above
Paper.latest_version = ForeignKey(PaperVersion, related_name='latest_version_of', null=True)

class Tag(Model):
    name = CharField(max_length=32)
    paper = ForeignKey(Paper, null=True)

    class Meta:
        db_table = 'tags'

class Review(Model):
    time = DateTimeField(auto_now_add=True)
    paper = ForeignKey(Paper, null=True)
    reviewer = ForeignKey(UserProfile, null=True)
    contents = TextField()

    score_novelty = IntegerField()
    score_presentation = IntegerField()
    score_technical = IntegerField()
    score_confidence = IntegerField()

    @staticmethod
    def jeeves_get_private_paper(review): return None
    @staticmethod
    def jeeves_get_private_reviewer(review): return None
    @staticmethod
    def jeeves_get_private_contents(review): return ""
    @staticmethod
    def jeeves_get_private_score_novelty(review): return -1
    @staticmethod
    def jeeves_get_private_score_presentation(review): return -1
    @staticmethod
    def jeeves_get_private_score_technical(review): return -1
    @staticmethod
    def jeeves_get_private_score_confidence(review): return -1

    @staticmethod
    @label_for('paper', 'reviewer', 'contents', 'score_novelty', 'score_presentation', 'score_technical', 'score_confidence')
    @jeeves
    def jeeves_restrict_reviewlabel(review, ctxt):
        if review != None and PaperPCConflict.objects.get(paper=review.paper, pc=ctxt) != None:
            return False
        return ctxt.level == 'chair' or ctxt.level == 'pc' or \
                (phase == 'final' and review.paper.author == ctxt)

    class Meta:
        db_table = 'reviews'

class Comment(Model):
    time = DateTimeField(auto_now_add=True)
    paper = ForeignKey(Paper, null=True)
    user = ForeignKey(UserProfile, null=True)
    contents = TextField()

    class Meta:
        db_table = 'comments'

    @staticmethod
    def jeeves_get_private_paper(review): return None
    @staticmethod
    def jeeves_get_private_user(review): return None
    @staticmethod
    def jeeves_get_private_contents(review): return ""

    @staticmethod
    @label_for('paper', 'user', 'contents')
    @jeeves
    def jeeves_restrict_reviewlabel(comment, ctxt):
        if comment != None and PaperPCConflict.objects.get(paper=comment.paper, pc=ctxt) != None:
            return False
        return ctxt.level == 'chair' or ctxt.level == 'pc'

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created and instance.is_superuser: 
        UserProfile.objects.create(
            username=instance.username,
            email=instance.email,
            level='chair',
        )

########NEW FILE########
__FILENAME__ = settings
"""
Django settings for conf project.  
For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(__file__)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '!$e(y9&5ol=#s7wex!xhv=f&5f2@ufjez3ee9kdifw=41p_+%*'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, '..', 'templates/'),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

ALLOWED_HOSTS = ['*']

TEMPLATE_LOADERS = (
    'django_jinja.loaders.AppLoader',
    'django_jinja.loaders.FileSystemLoader',
)
DEFAULT_JINJA2_TEMPLATE_EXTENSION = '.html'

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_jinja',
    'timelog',
    'conf',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'timelog.middleware.TimeLogMiddleware',
    'logging_middleware.ConfLoggingMiddleware',
)

ROOT_URLCONF = 'urls'

WSGI_APPLICATION = 'wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'jconf.db'),
    }
}

MEDIA_ROOT = os.path.join(BASE_DIR, '..', "media")
MEDIA_URL = "/media/"

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, '..', "static"),
)

# possible phases are submit, review, final
CONF_PHASE = 'submit'

LOG_PATH = os.path.join(BASE_DIR, '..', 'logs/')
TIMELOG_LOG = os.path.join(LOG_PATH, 'timelog.log')
SQL_LOG = os.path.join(LOG_PATH, 'sqllog.log')

LOGGING = {
  'version': 1,
  'formatters': {
    'plain': {
      'format': '%(asctime)s %(message)s'},
    },
  'handlers': {
    'timelog': {
      'level': 'DEBUG',
      'class': 'logging.handlers.RotatingFileHandler',
      'filename': TIMELOG_LOG,
      'maxBytes': 1024 * 1024 * 5,  # 5 MB
      'backupCount': 5,
      'formatter': 'plain',
    },
    'sqllog': {
      'level': 'DEBUG',
      'class': 'logging.handlers.RotatingFileHandler',
      'filename': SQL_LOG,
      'maxBytes': 1024 * 1024 * 5,  # 5 MB
      'backupCount': 5,
      'formatter': 'plain',
    },
  },
  'loggers': {
    'timelog.middleware': {
      'handlers': ['timelog'],
      'level': 'DEBUG',
      'propogate': False,
     },
    'timing_logging': {
      'handlers': ['timelog'],
      'level': 'DEBUG',
      'propogate': False,
     },
    'logging_middleware': {
      'handlers': ['sqllog'],
      'level': 'DEBUG',
      'propogate': False
    },
  },
}

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.models import User
import urllib
import random

import forms

from models import Paper, PaperVersion, UserProfile, Review, ReviewAssignment, Comment, UserPCConflict, PaperCoauthor, PaperPCConflict

from sourcetrans.macro_module import macros, jeeves
import JeevesLib
import logging

def register_account(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect("index")

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.save()

            UserProfile.objects.create(
                username=user.username,
                name=request.POST.get('name',''),
                affiliation=request.POST.get('affiliation',''),
                level='normal',
                email=request.POST.get('email', ''),
            )

            user = authenticate(username=request.POST['username'],
                         password=request.POST['password1'])
            login(request, user)
            return HttpResponseRedirect("index")
    else:
        form = UserCreationForm()

    return render_to_response("registration/account.html", RequestContext(request,
        {
            'form' : form,
            'which_page' : "register"
        }))

@jeeves
def add_to_context(context_dict, request, template_name, profile, concretize):
    template_name = concretize(template_name)
    context_dict['concretize'] = concretize

    context_dict['is_admin'] = profile != None and profile.level == "chair"
    context_dict['profile'] = profile

    context_dict['is_logged_in'] = (request.user and
                                    request.user.is_authenticated() and
                                    (not request.user.is_anonymous()))

def request_wrapper(view_fn):
    logger = logging.getLogger('timing_logging')
    import time

    def real_view_fn(request):
        try:
            t1 = time.time()
            ans = view_fn(request)
            t2 = time.time()
            template_name = ans[0]
            context_dict = ans[1]

            profile = UserProfile.objects.get(username=request.user.username)

            if template_name == "redirect":
                path = context_dict
                return HttpResponseRedirect(JeevesLib.concretize(profile, path))

            concretizeState = JeevesLib.jeevesState.policyenv.getNewSolverState(profile)
            def concretize(val):
                return concretizeState.concretizeExp(val, JeevesLib.jeevesState.pathenv.getEnv())
            #concretize = lambda val : JeevesLib.concretize(profile, val)
            add_to_context(context_dict, request, template_name, profile, concretize)

            #print 'concretized is', concretize(context_dict['latest_title'])

            r = render_to_response(template_name, RequestContext(request, context_dict))

            t3 = time.time()

            logger.info("Jeeves time: %f" % (t2 - t1))
            logger.info("Concre time: %f" % (t3 - t2))

            return r

        except Exception:
            import traceback
            traceback.print_exc()
            raise

    real_view_fn.__name__ = view_fn.__name__
    return real_view_fn

@login_required
@request_wrapper
@jeeves
def index(request):
    user = UserProfile.objects.get(username=request.user.username)

    return (   "index.html"
           , { 'name' : user.name 
             , 'which_page': "home" })

@request_wrapper
@jeeves
def about_view(request):
  return ( "about.html"
         , { 'which_page' : "about" } )

@login_required
@request_wrapper
@jeeves
def papers_view(request):
    user = UserProfile.objects.get(username=request.user.username)

    papers = Paper.objects.all()
    paper_data = JeevesLib.JList2()
    for paper in papers:
        paper_versions = PaperVersion.objects.filter(paper=paper).order_by('-time').all()
        latest_version_title = paper_versions[0].title if paper_versions.__len__() > 0 else None

        paper_data.append({
            'paper' : paper,
            'latest' : latest_version_title
        })

    return ("papers.html", {
        'papers' : papers
      , 'which_page' : "home"
      , 'paper_data' : paper_data
      , 'name' : user.name
    })

@login_required
@request_wrapper
@jeeves
def paper_view(request):
    user = UserProfile.objects.get(username=request.user.username)

    paper = Paper.objects.get(jeeves_id=request.GET.get('id', ''))
    if paper != None:
        if request.method == 'POST':
            if request.POST.get('add_comment', 'false') == 'true':
                Comment.objects.create(paper=paper, user=user,
                            contents=request.POST.get('comment', ''))

            elif request.POST.get('add_review', 'false') == 'true':
                Review.objects.create(paper=paper, reviewer=user,
                            contents=request.POST.get('review', ''),
                            score_novelty=int(request.POST.get('score_novelty', '1')),
                            score_presentation=int(request.POST.get('score_presentation', '1')),
                            score_technical=int(request.POST.get('score_technical', '1')),
                            score_confidence=int(request.POST.get('score_confidence', '1')),
                          )
            elif request.POST.get('new_version', 'false') == 'true' and user == paper.author:
                contents = request.FILES.get('contents', None)
                if contents != None and paper.author != None:
                    set_random_name(contents)
                    PaperVersion.objects.create(paper=paper,
                        title=request.POST.get('title', ''),
                        contents=contents,
                        abstract=request.POST.get('abstract', ''),
                    )

        paper_versions = PaperVersion.objects.filter(paper=paper).order_by('-time').all()
        coauthors = PaperCoauthor.objects.filter(paper=paper).all()
        latest_abstract = paper_versions[0].abstract if paper_versions.__len__() > 0 else None
        latest_title = paper_versions[0].title if paper_versions.__len__() > 0 else None
        reviews = Review.objects.filter(paper=paper).order_by('-time').all()
        comments = Comment.objects.filter(paper=paper).order_by('-time').all()
        author = paper.author
    else:
        paper = None
        paper_versions = []
        coauthors = []
        latest_abstract = None
        latest_title = None
        reviews = []
        comments = []
        author = None

    return ("paper.html", {
        'paper' : paper,
        'paper_versions' : paper_versions,
        'author' : author,
        'coauthors' : coauthors,
        'latest_abstract' : latest_abstract,
        'latest_title' : latest_title,
        'reviews' : reviews,
        'comments' : comments,
        'which_page' : "paper",
        'review_score_fields': [ ("Novelty", "score_novelty", 10)
                               , ("Presentation", "score_presentation", 10)
                               , ("Technical", "score_technical", 10)
                               , ("Confidence", "score_confidence", 10) ]  
  })

def set_random_name(contents):
    contents.name = '%030x' % random.randrange(16**30) + ".pdf"

@login_required
@request_wrapper
@jeeves
def submit_view(request):
    user = UserProfile.objects.get(username=request.user.username)

    if request.method == 'POST':
        coauthors = request.POST.getlist('coauthors[]')
        title = request.POST.get('title', None)
        abstract = request.POST.get('abstract', None)
        contents = request.FILES.get('contents', None)

        if title == None or abstract == None or contents == None:
            return ("submit.html", {
                'coauthors' : coauthors,
                'title' : title,
                'abstract' : abstract,
                'contents' : contents.name,
                'error' : 'Please fill out all fields',
                'which_page' : "submit",
            })

        paper = Paper.objects.create(author=user, accepted=False)
        for coauthor in coauthors:
            if coauthor != "":
                PaperCoauthor.objects.create(paper=paper, author=coauthor)
        set_random_name(contents)
        PaperVersion.objects.create(
            paper=paper,
            title=title,
            abstract=abstract,
            contents=contents
        )

        for conf in request.POST.getlist('pc_conflicts[]'):
            new_pc_conflict = UserProfile.objects.get(username=conf)
            PaperPCConflict.objects.create(paper=paper, pc=new_pc_conflict)

        return ("redirect", "paper?id=" + paper.jeeves_id)

    pcs = UserProfile.objects.filter(level='pc').all()
    pc_conflicts = [uppc.pc for uppc in UserPCConflict.objects.filter(user=user).all()]
    
    return ("submit.html", {
        'coauthors' : [],
        'title' : '',
        'abstract' : '',
        'contents' : '',
        'error' : '',
        "pcs": [{'pc':pc, 'conflict':pc in pc_conflicts} for pc in pcs],
        'pc_conflicts' : pc_conflicts,
        'which_page': "submit",
    })

@login_required
@request_wrapper
@jeeves
def profile_view(request):
    profile = UserProfile.objects.get(username=request.user.username)
    if profile == None:
        profile = UserProfile(username=request.user.username)
        profile.level = 'normal'
    pcs = UserProfile.objects.filter(level='pc').all()
    
    if request.method == 'POST':
        profile.name = request.POST.get('name', '')
        profile.affiliation = request.POST.get('affiliation', '')
        profile.acm_number = request.POST.get('acm_number', '')
        profile.email = request.POST.get('email', '')
        profile.save()

        UserPCConflict.objects.filter(user=profile).delete()
        pc_conflicts = []
        for conf in request.POST.getlist('pc_conflicts[]'):
            new_pc_conflict = UserProfile.objects.get(username=conf)
            UserPCConflict.objects.create(user=profile, pc=new_pc_conflict)
            pc_conflicts.append(new_pc_conflict)
    else:
        pc_conflicts = [uppc.pc for uppc in UserPCConflict.objects.filter(user=profile).all()]

    return ("profile.html", {
        "name": profile.name,
        "affiliation": profile.affiliation,
        "acm_number": profile.acm_number,
        "pc_conflicts": pc_conflicts,
        "email": profile.email,
        "pcs": pcs,
        "which_page": "profile",
        "pcs": [{'pc':pc, 'conflict':pc in pc_conflicts} for pc in pcs],
    })

@login_required
def submit_review_view(request):
    user = UserProfile.objects.get(username=request.user.username)

    try:
        if request.method == 'GET':
            paper_id = int(request.GET['id'])
        elif request.method == 'POST':
            paper_id = int(request.POST['id'])
        paper = Paper.objects.filter(id=paper_id).get()
        review = Review()
        review.paper = paper
        review.reviewer = user
        if request.method == 'POST':
            form = forms.SubmitReviewForm(request.POST, instance=review)
            if form.is_valid():
                form.save(paper)
                return HttpResponseRedirect("paper?id=%s" % paper_id)
        else:
            form = forms.SubmitReviewForm()
    except (ValueError, KeyError, Paper.DoesNotExist):
        paper = None
        form = None

    return render_to_response("submit_review.html", RequestContext(request, {
        'form' : form,
        'paper' : paper,
        'which_page' : "submit_review",
    }))

@login_required
@request_wrapper
@jeeves
def users_view(request):
    user = UserProfile.objects.get(username=request.user.username)
    if user.level != 'chair':
        return (   "redirect", "/index")

    user_profiles = UserProfile.objects.all()

    if request.method == 'POST':
        for profile in user_profiles:
            query_param_name = 'level-' + profile.username
            level = request.POST.get(query_param_name, '')
            if level in ['normal', 'pc', 'chair']:
                profile.level = level
                profile.save()

    return ("users_view.html", {
        'user_profiles': user_profiles,
        'which_pages' : "users"
    })

@login_required
def submit_comment_view(request):
    user = UserProfile.objects.get(username=request.user.username)

    try:
        if request.method == 'GET':
            paper_id = int(request.GET['id'])
        elif request.method == 'POST':
            paper_id = int(request.POST['id'])
        paper = Paper.objects.filter(id=paper_id).get()
        comment = Comment()
        comment.paper = paper
        comment.user = user
        if request.method == 'POST':
            form = forms.SubmitCommentForm(request.POST, instance=comment)
            if form.is_valid():
                form.save(paper)
                return HttpResponseRedirect("paper?id=%s" % paper_id)
        else:
            form = forms.SubmitCommentForm()
    except (ValueError, KeyError, Paper.DoesNotExist):
        paper = None
        form = None

    return render_to_response("submit_comment.html", RequestContext(request, {
        'form' : form,
        'paper' : paper,
        'which_page' : "submit_comment"
    }))

#@jeeves
#def get_rev_assign(paper, reviewer):
#    revassigs = ReviewAssignment.objects.filter(paper=paper, user=reviewer).all()
#    assignment = revassigs[0] if revassigs.__len__() > 0 else None
#    return assignment

@login_required
@request_wrapper
@jeeves
def assign_reviews_view(request):
    possible_reviewers = UserProfile.objects.filter(level='pc').all()

    reviewer = UserProfile.objects.get(username=request.GET.get('reviewer_username', '')) # might be None

    if reviewer != None:
        papers = Paper.objects.all()

        if request.method == 'POST':
            ReviewAssignment.objects.filter(user=reviewer).delete()
            for paper in papers:
                ReviewAssignment.objects.create(paper=paper, user=reviewer,
                            assign_type='assigned'
                                if request.POST.get('assignment-' + paper.jeeves_id, '')=='yes'
                                else 'none')
        papers_data = [{
            'paper' : paper,
            'latest_version' : PaperVersion.objects.filter(paper=paper).order_by('-time').all()[-1],
            'assignment' : ReviewAssignment.objects.get(paper=paper, user=reviewer),
            'has_conflict' : PaperPCConflict.objects.get(pc=reviewer, paper=paper) != None,
        } for paper in papers]
    else:
        papers_data = []

    return ("assign_reviews.html", {
        'reviewer' : reviewer,
        'possible_reviewers' : possible_reviewers,
        'papers_data' : papers_data,
        'which_page' : "assign_reviews"
    })

@login_required
def search_view(request):
    # TODO choose the actual set of possible reviewers
    possible_reviewers = list(User.objects.all())
    possible_authors = list(User.objects.all())

    form = forms.SearchForm(request.GET, reviewers=possible_reviewers, authors=possible_authors)
    if form.is_valid():
        results = form.get_results()
    else:
        results = []

    return render_to_response("search.html", RequestContext(request, {
        'form' : form,
        'results' : results,
        'which_page' : "search"
    }))


########NEW FILE########
__FILENAME__ = logging_middleware
import logging
from django.db import connection
from django.utils.encoding import smart_str

logger = logging.getLogger(__name__)

# Based off of https://djangosnippets.org/snippets/290/

class ConfLoggingMiddleware(object):
    def process_request(self, request):
        pass

    def process_response(self, request, response):
        logger.info("%s \"%s\" (%s)" % (request.method, smart_str(request.path_info), response.status_code))

        indentation = 2
        if len(connection.queries) > 0:
            total_time = 0.0
            for query in connection.queries:
                nice_sql = query['sql'].replace('"', '').replace(',',', ')
                sql = "[%s] %s" % (query['time'], nice_sql)
                total_time = total_time + float(query['time'])
                logger.info("%s%s\n" % (" "*indentation, sql))
            replace_tuple = (" "*indentation, str(total_time))
            logger.info("%s[TOTAL QUERIES: %d]" % (" "*indentation, len(connection.queries)))
            logger.info("%s[TOTAL TIME: %s seconds]" % replace_tuple)
        return response

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

import macropy.activate
from macropy.core.exporters import SaveExporter
macropy.exporter = SaveExporter("exported", ".")

import JeevesLib
JeevesLib.init()

if __name__ == "__main__":
    os.environ["DJANGO_SETTINGS_MODULE"] = "conf.settings"

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from django.conf.urls.static import static
from django.conf import settings

from conf import views

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'conf.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),

    url(r'^accounts/login/$', 'django.contrib.auth.views.login'),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout_then_login'),
    url(r'^accounts/profile/$', views.profile_view),

    url(r'^register$', views.register_account),

    url(r'^index$', views.papers_view),
    url(r'^$', views.papers_view),
    url(r'^submit$', views.submit_view),
    url(r'^papers$', views.papers_view),
    url(r'^paper$', views.paper_view),
    url(r'^submit_review$', views.submit_review_view),
    url(r'^submit_comment$', views.submit_comment_view),
    url(r'^assign_reviews$', views.assign_reviews_view),
    url(r'^search$', views.search_view),
    url(r'^about$', views.about_view),
    url(r'^users$', views.users_view),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for conf project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
import logging, sys
logging.basicConfig(stream=sys.stderr)
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'conf/'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
os.environ["DJANGO_SETTINGS_MODULE"] = "conf.settings"

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = assignment
import sys
sys.path.append("../../..")
import JeevesLib
import math
from datetime import *

class Assignment():
  def __init__(self, assignmentId, name, dueDate, maxPoints, prompt, authorId):
    self.assignmentId = assignmentId
    self.name = name
    self.dueDate = dueDate
    self.maxPoints = maxPoints
    self.prompt = prompt
    self.authorId = authorId
    
  # Labels
  # Policies

  def __repr__(self):
    return "Assignment(%d, %s, %s)" % (self.assignmentId, self.name, self.prompt)

  # Math Functions
  def average(self, l):
    return float(sum(l))/len(l)

  def std(self, l):
    mean = self.average(l)
    variance = map(lambda x: (float(x) - mean)**2, l)
    stdev = math.sqrt(self.average(variance))
    return stdev #check precision

  def median(self, l):
    sortedL = sorted(l)
    length = len(sortedL)
    if length % 2:          
      return sortedL[length / 2]
    else:
      return self.average( sortedL[length / 2], sortedL[length/2 - 1] )
     
  # Get

  # Set

  # Show























########NEW FILE########
__FILENAME__ = main
import sys
sys.path.append("../../..")
import JeevesLib
import macropy.activate
from smt.Z3 import *

from users import *
from assignment import *
from submission import *
from datetime import *

#TODO Make all variables "private" -> add _variableName
class CourseManager:
  def __init__(self):
    JeevesLib.init()
    self.assignmentList = []
    self.userList = []
    self.submissionList = []
    self.session = None

  def log_in(self, username, password):
    user = self.userList[self.userNameToIndex(username)]
    if user.validate(password):
      self.session = user
      return True
    else:
      return False

  def log_out(self):
    self.session = none
    return True

  def addStudent(self, uName, fName, lName, email, password):
    sId = len(self.userList)+1
    stud = Student(sId, uName, fName, lName, email)
    stud.setPassword(password)
    self.userList.append(stud)
    if len(self.userList) == sId:
      return True
    else:
      return False

  def addInstructor(self, uName, fName, lName, email, password):
    insId = len(self.userList)+1
    ins = Instructor(insId, uName, fName, lName, email)
    ins.setPassword(password)
    self.userList.append(ins)
    if len(self.userList) == insId:
      return True
    else:
      return False

  def userNameToIndex(self,name):
    for x in xrange(len(self.userList)):
      user = self.userList[x]
      if user.userName == name:
        return x
      else:
        -1

  def addAssignment(self, aName, due, maxPoints, prompt):
    if isinstance(session, Instructor):
      aId = len(self.assignmentList) + 1
      assg = Assignment(aId, aName, due, maxPoints, prompt, session.userId)
      self.assignmentList.append(assg)
    return isinstance(session, Instructor)

  def viewAssignment(self, name):
    for x in xrange(len(self.assignmentList)):
      assignment = self.assignmentList[x]
      if assignment.name == name:
        return assignment
    return None

  def addSubmission(self, assignmentId, title, text):
    if isinstance(self.session, Student):
      sId = len(self.submissionList) + 1
      submission = Submission(sId, title, assignmentId, self.session.userId, text)
      self.submissionList.append(submission)
    return isinstance(self.session, Student)

  def viewSubmissionDetails(self, sId):
    submission = self.submissionList[sId-1]
    title = submission.showTitle(self.session)
    details = submission.showSubmissionDetails(self.session)
    grade = submission.showGrade(self.session)
    return "Submission(%s, %s, %d)" % (title, details, grade)

  #Incomplete
  def viewSubmissionFromUser(self, assignment, userName):
    for x in xrange(len(submissionList)):
      assignment = self.assignmentList[x]
      if assignment.name == name:
        return assignment

if __name__ == '__main__':
  cm = CourseManager()
  cm.addInstructor("jyang", "Jean", "Yang", "jy@mit.edu", "password")
  cm.addStudent("thance","Travis","Hance","th@mit.edu","password")
  cm.addStudent("bshaibu","Ben","Shaibu","bs@mit.edu", "password")
  while cm.session is None:
    print("Log In")
    uname = raw_input("Username: ")
    pword = raw_input("Password: ")
    if cm.log_in(uname, pword):
      print("Log In Successful!")
      print(cm.session)
    else:
      print ("Log In Failed.") 


########NEW FILE########
__FILENAME__ = submission
from datetime import *

import sys
sys.path.append("../../..")
import JeevesLib
from smt.Z3 import *
import macropy.activate

from users import *
from assignment import *

class Submission():
  def __init__(self, submissionId, title, assignmentId, submitterId, fileRef):
    self.submissionId = submissionId
    self.title = title
    self.assignmentId = assignmentId
    self.submitterId = submitterId
    self.fileRef = fileRef
    self.submittedOn = ""
    self.grade = None
    self.submittedOn = datetime.now()
    JeevesLib.init()

    ## Policies ##
    def _isUser(context):
      return isinstance(context, User)

    def _isSubmitter(context):
      return context.userId == self.submitterId

    def _isInstructor(context):
      return isinstance(context, Instructor)
    
    ## Labels ##
    self._viewerL = JeevesLib.mkLabel()
    self._editorL = JeevesLib.mkLabel()
    self._adminL = JeevesLib.mkLabel()
  
    ## Restrict Labels ##
    JeevesLib.restrict(self._viewerL, lambda oc: JeevesLib.jor(lambda :_isSubmitter(oc),  lambda : _isInstructor(oc) ) )
    JeevesLib.restrict(self._editorL, lambda oc: _isSubmitter(oc) )
    JeevesLib.restrict(self._adminL, lambda oc: _isInstructor(oc) )

  ## Getter, Setters, and Show-ers ##   

  #Grade 
  def getGrade(self):
    score = JeevesLib.mkSensitive(_viewerL, self.grade, -1)
    return score

  def setGrade(self,score):
    # Would it be better to store score as a concretized value? 
    # It wouldn't work as well for a database, but possibly in simple examples
    self.grade = score

  def showGrade(self, context):
    faceted_value = self.getGrade()
    return JeevesLib.concretize(context, faceted_value)

  #Submission Details (fileRef)
  def getSubmissionDetails(self):
    details = JeevesLib.mkSensitive(self._viewerL, self.fileRef, "N/A")
    return details

  def setSubmissionDetails(self, text):
    self.fileRef = text

  def showSubmissionDetails(self, context):
    return JeevesLib.concretize(context, self.getSubmissionDetails())
  
  #Submission Title
  def getTitle(self):
    details = JeevesLib.mkSensitive(self._viewerL, self.title, "N/A")
    return details

  def setTitle(self, title):
    self.title = title

  def showTitle(self, context):
    return JeevesLib.concretize(context, self.getTitle())
  
  ## Magic Methods ##
  def __repr__(self):
    #Is there a way to integrate contexts with representation?
    #Would there be a point?    
    return "Submisison(%d, %s, %s)" % (self.submissionId, self.title, self.fileRef)

  def __eq__(self, other):
    if isinstance(other, self.__class__):
      return self.submissionId == other.submissionId and self.title == other.title
    else:
      return False

  def __ne__(self, other):
    return not self.__eq__(other)

########NEW FILE########
__FILENAME__ = testAssignment
import unittest
import math
from datetime import *
import sys
sys.path.append("../../../..")
import JeevesLib
sys.path.append("..")
from assignment import *

class TestAssignment(unittest.TestCase):

  def setUp(self):
    self.due = datetime(2013, 11, 15, 12, 13, 14)
    self.a = Assignment(1, "Documentation", self.due, 100, "Create Documentation", 1)
    self.tlist = [1,2,4,5,6]

  def testAverage(self):
    self.assertEqual(self.a.average(self.tlist), 3.6)

  def testMedian(self):
    self.assertEqual(self.a.median(self.tlist), 4)

  def testStandardDeviation(self):
    #2.0736
    self.assertEqual(round(self.a.std(self.tlist)), 2)

if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = testCourseManager
import unittest
from datetime import *
import sys
sys.path.append("../../../..")
import JeevesLib
import macropy.activate
from smt.Z3 import *
sys.path.append("..")
from main import *
from users import *
from assignment import *
from submission import *

class TestCourseManager(unittest.TestCase):

  def setUp(self):
    JeevesLib.init()
    self.cm = CourseManager()
    user1 = Instructor(1,"jyang","Jean","Yang","jy@mit.edu")
    user1.setPassword("password")
    user2 = Student(2,"thance","Travis","Hance","th@mit.edu")
    user2.setPassword("password")
    user3 = Student(3,"bshaibu","Ben","Shaibu","bs@mit.edu")
    user3.setPassword("password")

    dueDate = datetime(2013, 11, 27, 12, 13, 14)
    dueDate = datetime(2013, 12, 10, 5, 5, 5)
    assignment1 = Assignment(1, "Documentation", dueDate, 100, "Create Documentation", 1)
    assignment2 = Assignment(2, "Create Application", dueDate, 100, "Create Application", 1)

    submission1 = Submission(1, "PyJeeves Docs", 1, 3, "This is Jeeves in Python!")
    submission2 = Submission(1, "CourseManager Docs", 1, 3, "This is a CourseManager in Python!")

    self.cm.userList = [user1, user2, user3]
    self.cm.assignmentList = [assignment1, assignment2]
    self.cm.submissionList = [submission1, submission2]

  def testInitialSystem(self):
    self.assertEqual(len(self.cm.userList), 3)
    self.assertEqual(len(self.cm.assignmentList), 2)
    self.assertEqual(len(self.cm.submissionList), 2)

  def testAccessUsers(self):
    user1 = Instructor(1,"jyang","Jean","Yang","jy@mit.edu")
    user1.setPassword("password")
    user2 = Student(2,"thance","Travis","Hance","th@mit.edu")
    user2.setPassword("password")
    user3 = Student(3,"bshaibu","Ben","Shaibu","bs@mit.edu")
    user3.setPassword("password")
    
    self.assertEqual(self.cm.userList[0], user1)
    self.assertEqual(self.cm.userList[1], user2)
    self.assertEqual(self.cm.userList[2], user3)

  def testAddUsers(self):
    user4 = Student(4,"sneaky","Sneaky","McSneak","sneak@mit.edu")
    user4.setPassword("password")
    user5 = Instructor(5,"asl", "Armando", "Solar-Lezama", "asl@mit.edu")
    user5.setPassword("password")

    self.assertTrue( self.cm.addStudent("sneaky","Sneaky","McSneak","sneak@mit.edu", "password") )
    self.assertTrue( self.cm.addInstructor("asl", "Armando", "Solar-Lezama", "asl@mit.edu", "password") )
    self.assertEqual( self.cm.userList[3], user4 )
    self.assertEqual( self.cm.userList[4], user5 )

  def testLogIn(self):
    user3 = Student(3,"bshaibu","Ben","Shaibu","bs@mit.edu")
    user3.setPassword("password")
    self.assertTrue(self.cm.log_in("bshaibu", "password"))
    self.assertEqual(self.cm.session, user3)

  def testViewStudentSubmission(self):
    self.cm.log_in("jyang", "password")
    print(self.cm.viewSubmissionDetails(1))

  def testViewYourSubmision(self):
    pass
  
  def testViewAnotherSubmission(self):
    pass

if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = testSubmission
import unittest
import sys
sys.path.append("../../../..")
import JeevesLib
import macropy.activate
from smt.Z3 import *
sys.path.append("..")
from users import *
from assignment import *
from submission import *

class TestSubmission(unittest.TestCase):

  def setUp(self):
    JeevesLib.init()

  def testEquality(self):
    submission = Submission(1, "PyJeeves Docs", 1, 2, "This is Jeeves in Python!")
    submission1 = Submission(1, "PyJeeves Docs", 1, 2, "This is Jeeves in Python!")
    submission2 = Submission(1, "CourseManager Docs", 1, 2, "This is a CourseManager in Python!")
    self.assertEqual(submission,submission1)
    self.assertNotEqual(submission,submission2)

if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = testUser
import unittest
import hashlib
import sys
sys.path.append("..")
from users import *
sys.path.append("../../../..")
import JeevesLib

class TestUser(unittest.TestCase):

  def setUp(self):
    pass

  def testPasswordValidation(self):
    self.user = User(1,"bob","Bob","Barker","bbarker@mit.edu")
    self.user.setPassword("password")
    self.assertTrue( self.user.validate("password") )

  def testEquality(self):
    a = User(1,"bob","Bob","Barker","bbarker@mit.edu")
    b = User(1,"bob","Bob","Barker","bbarker@mit.edu")
    c = User(2,"stew","Stu","Pickle","spickle@mit.edu")
    self.assertEqual(a,b)
    self.assertNotEqual(a,c)
    bobTeacher = Instructor(1,"bob","Bob","Barker","bbarker@mit.edu")
    bobStudent = Student(1,"bob","Bob","Barker","bbarker@mit.edu")
    self.assertNotEqual(bobTeacher, bobStudent)

if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = users
import sys
sys.path.append("../../..")
import JeevesLib
import hashlib

class User:
  def __init__(self, userId, userName, firstName, lastName, email):
    self.userId = userId
    self.userName = userName
    self.firstName = firstName
    self.lastName = lastName
    self.email = email
    self._passwordDigest = ""

  def __repr__(self):
    return "User(%d, %s)" % (self.userId, self.userName)

  # Labels

  # Policies

  ## Password Functions ##
  def md5(self, string):
    return hashlib.md5(string).hexdigest()

  def setPassword(self, password):
    self._passwordDigest = self.md5(password)

  def validate(self, password):
    return self._passwordDigest == self.md5(password)

  ## Actions ##
  def submitAssignment(self, assignment, name):
    pass
  
  def createAssignment(self, assignmentname, dueDate, maxPoints, prompt):
    pass
  
  ## Magic Methods ##
  def __eq__(self, other):
    if isinstance(other, self.__class__):
      return self.userId == other.userId and self.userName == other.userName
    else:
      return False

  def __ne__(self, other):
    return not self.__eq__(other)
    
class Student(User):
  def __init__(self, userId, userName, firstName, lastName, email):
    User.__init__(self, userId, userName, firstName, lastName, email)

class Instructor(User):
  def __init__(self, userId, userName, firstName, lastName, email):
    User.__init__(self, userId, userName, firstName, lastName, email)

########NEW FILE########
__FILENAME__ = forms
from django.forms import Form, ModelForm, CharField, FileField, Textarea, ModelForm, HiddenInput, MultipleChoiceField, CheckboxSelectMultiple, BooleanField, ChoiceField

from models import Paper, PaperVersion, UserProfile, Review, ReviewAssignment, Comment, UserPCConflict
from django.contrib.auth.models import User
import random
from django.forms.formsets import formset_factory

class SubmitForm(Form):
    coauthor1 = CharField(required=False)
    coauthor2 = CharField(required=False)
    coauthor3 = CharField(required=False)

    title = CharField(1024, required=True)
    contents = FileField(required=True)
    abstract = CharField(widget=Textarea, required=True)

    def __init__(self, possible_reviewers, default_conflict_reviewers, *args, **kwargs):
        super(SubmitForm, self).__init__(*args, **kwargs)

        choices = []
        for r in possible_reviewers:
            choices.append((r.username, r))

        self.fields['conflicts'] = MultipleChoiceField(widget=CheckboxSelectMultiple(), required=False, choices=choices, initial=list(default_conflict_reviewers))

    def is_valid(self):
        if not super(SubmitForm, self).is_valid():
            return False

        try:
            coauthors = []
            for coauthor_id in ['coauthor1', 'coauthor2', 'coauthor3']:
                if coauthor_id in self.cleaned_data and self.cleaned_data[coauthor_id]:
                    coauthor = User.objects.filter(username=self.cleaned_data[coauthor_id]).get()
                    coauthors.append(coauthor)
        except User.DoesNotExist:
            return False

        self.cleaned_data['coauthors'] = coauthors
        return True

    def save(self, user):
        d = self.cleaned_data
        
        authors = [user]
        if 'coauthor1' in d:
            authors.append(d['coauthor1'])
        if 'coauthor2' in d:
            authors.append(d['coauthor2'])
        if 'coauthor3' in d:
            authors.append(d['coauthor3'])

        paper = Paper()
        paper.save()

        paper.authors.add(user)
        for coauthor in d['coauthors']:
            paper.authors.add(coauthor)
        paper.save()

        d['contents'].name = '%030x' % random.randrange(16**30) + ".pdf"

        paper_version = PaperVersion(
            paper = paper,
            title = d['title'],
            abstract = d['abstract'],
            contents = d['contents'],
        )
        paper_version.save()

        # need to save paper twice since paper and paper_version point to each other...
        paper.latest_version = paper_version
        paper.save()

        for conflict_username in d['conflicts']:
            ra = ReviewAssignment()
            ra.user = User.objects.get(username=conflict_username)
            ra.paper = paper
            ra.type = 'conflict'
            ra.save()

        return paper

class SubmitReviewForm(ModelForm):
    class Meta:
        model = Review
        fields = ['contents', 'score_novelty', 'score_presentation', 'score_technical', 'score_confidence']

class SubmitCommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['contents']

class ReviewAssignmentForm(ModelForm):
    class Meta:
        model = ReviewAssignment
        fields = ['assign_type', 'user', 'paper']
        widgets = {
            'user' : HiddenInput(),
            'paper' : HiddenInput(),
        }

ReviewAssignmentFormset = formset_factory(ReviewAssignmentForm, extra=0)

class SearchForm(Form):
    # should only show accepted papers
    filter_accepted = BooleanField(required=False)

    # should only show papers accepted by a reviewer
    # filter_reviewer (defined in __init__ below)

    # should only show papers by the given author
    # filter_author (defined in __init__ below)

    filter_title_contains = CharField(required=False)

    sort_by = ChoiceField(required=True,
                            choices=(('---', None),
                                     ('title', 'title'),
                                     ('score_technical', 'score_technical'),
                                    ))

    def __init__(self, *args, **kwargs):
        reviewers = kwargs['reviewers']
        authors = kwargs['authors']
        del kwargs['reviewers']
        del kwargs['authors']

        super(SearchForm, self).__init__(*args, **kwargs)
        
        self.fields['filter_reviewer'] = ChoiceField(required=False,
            choices=[('', '---')] + [(r.username, r) for r in reviewers])
        self.fields['filter_author'] = ChoiceField(required=False,
            choices=[('', '---')] + [(r.username, r) for r in authors])

    def get_results(self):
        d = self.cleaned_data

        query = Paper.objects

        # TODO enable support for accepting papers and then enable this
        #if d['filter_accepted']:
        #    query = query.filter(

        if d.get('filter_reviewer', ''):
            query = query.filter(authors__username=d['filter_reviewer'])

        if d.get('filter_author', ''):
            query = query.filter(reviewers__username=d['filter_author'])

        if d.get('filter_title_contains', ''):
            query = query.filter(latest_version__title__contains=d['filter_title_contains'])

        if d.get('sort_by','') == 'title':
            query = query.order_by('latest_version__title')
        elif d.get('sort_by','') == 'score_technical':
            query = query.order_by('latest_version__score_technical')

        print query.query.__str__()
        results = list(query.all())

        return list(results)

########NEW FILE########
__FILENAME__ = hipaaModels
from django.db.models import Model, ManyToManyField, ForeignKey, CharField, TextField, DateTimeField, IntegerField, FileField, BooleanField

from jeevesdb.JeevesModel import JeevesModel as Model
from jeevesdb.JeevesModel import JeevesForeignKey as ForeignKey
from jeevesdb.JeevesModel import label_for

from sourcetrans.macro_module import macros, jeeves
import JeevesLib

from settings import CONF_PHASE as phase

class Address(Model):
    Street=CharField(max_length=100)
    City=CharField(max_length=30)
    State=CharField(max_length=20)
    ZipCode=CharField(max_length=5)
    class Meta:
        db_table = 'Address'
        
class Individual(Model):
    FirstName = CharField(max_length=1024)
    Email = CharField(max_length=1024)
    Address = ForeignKey(Address)
    BirthDate = DateField()
    Sex = CharField(max_length=6)
    Parent = ForeignKey("self",blank=True,null=True)
    LastName = CharField(max_length=1024)
    UID=IntegerField(primary_key=True)
    SSN = CharField(max_length=9)
    TelephoneNumber = CharField(max_length=10)
    FaxNumber = CharField(max_length=10)
    PersonalRepresentative = ForeignKey("self",blank=True,null=True)
    ReligiousAffiliation = CharField(max_length=100)
    class Meta:
        db_table = 'Individual'

class CoveredEntity(Model):
    
    '''
    Health plan, health clearinghouse,
    or health care provider making sensitive transactions. This includes hospitals.
    '''
    
    Name = CharField(max_length=1024)
    Directory = ManyToManyField(Individual,through="HospitalVisit")
    Associates = ManyToManyField(BusinessAssociate,through="BusinessAssociateAgreement")
    class Meta:
        db_table = 'CoveredEntity'

class BusinessAssociate(Model):
    
    '''
    Persons or corporations that perform services for covered entities. They may
    or may not be covered entities themselves.
    '''
    
    Name = CharField(max_length=1024)
    CoveredIdentity = ForeignKey(CoveredEntity, null=True, blank=True)
    class Meta:
        db_table = 'BusinessAssociate'

class BusinessAssociateAgreement(Model):
    BusinessAssociate = ForeignKey(BusinessAssociate)
    CoveredEntity = ForeignKey(CoveredEntity)
    SharedInformation = OneToOneField(InformationTransferSet)
    class Meta:
        db_table = 'BusinessAssociateAgreement'

class Treatment(Model):
    '''
    Provided medical treatment, medication, or service.
    '''
    Service = CharField(max_length=100)
    DatePerformed = DateField()
    PrescribingEntity = ForeignKey(CoveredEntity)
    PerformingEntity = ForeignKey(CoveredEntity)
    Patient = ForeignKey(Individual)
    class Meta:
        db_table = 'Treatment'

class Diagnosis(Model): 
    '''
    Recognition of health condition or situation by a medical professional.
    '''
    Manifestation = CharField(max_length=100)
    DateRecognized = DateField()
    RecognizedEntity = ForeignKey(CoveredEntity)
    Patient = ForeignKey(Individual)
    class Meta:
        db_table = 'Diagnosis'

class HospitalVisit(Model):
    Patient = ForeignKey(Individual)
    Hospital = ForeignKey(CoveredEntity)
    DateAdmitted = DateField()
    Location = TextField()
    Condition = TextField()
    Active = BooleanField(default=True) #If the patient is still at the hospital.
    class Meta:
        db_table = 'HospitalVisit'
        
class Transaction(Model):
    
    '''
    A defined standard transaction between covered entitities.

    Attributes:
    Standard - Transaction Code: ICS-10-PCS, HCPCS, e.g.
    FirstParty, SecondParty - Covered entities performing the transaction
    SharedInformation - Information transferred between the parties to fulfill the transaction.
    '''

    Standard = CharField(max_length=100)
    FirstParty = ForeignKey(CoveredEntity)
    SecondParty = ForeignKey(CoveredEntity)
    SharedInformation = OneToOneField(InformationTransferSet)
    DateRequested = DateField()
    DateResponded = DateField()
    Purpose = TextField()
    class Meta:
        db_table = 'Transaction'
        
class InformationTransferSet(Model):
    
    '''
    Collection of private information that can be shared
    '''
    Treatments = ManyToManyField(Treatment)
    Diagnoses = ManyToManyField(Diagnosis)
    HospitalVisits = ManyToManyField(HospitalVisit)
    class Meta:
        db_table = 'InformationTransferSet'

########NEW FILE########
__FILENAME__ = models
from django.db.models import Model, ManyToManyField, ForeignKey, CharField, TextField, DateTimeField, IntegerField, FileField, BooleanField

from jeevesdb.JeevesModel import JeevesModel as Model
from jeevesdb.JeevesModel import JeevesForeignKey as ForeignKey
from jeevesdb.JeevesModel import label_for

from sourcetrans.macro_module import macros, jeeves
import JeevesLib

from settings import CONF_PHASE as phase

class UserProfile(Model):
    username = CharField(max_length=1024)
    email = CharField(max_length=1024)

    name = CharField(max_length=1024)
    affiliation = CharField(max_length=1024)
    acm_number = CharField(max_length=1024)

    level = CharField(max_length=12,
                    choices=(('normal', 'normal'),
                        ('pc', 'pc'),
                        ('chair', 'chair')))

    @staticmethod
    def jeeves_get_private_email(user):
        return ""

    @staticmethod
    @label_for('email')
    @jeeves
    def jeeves_restrict_userprofilelabel(user, ctxt):
        return user == ctxt or (ctxt != None and ctxt.level == 'chair')

    class Meta:
        db_table = 'user_profiles'

class UserPCConflict(Model):
    user = ForeignKey(UserProfile, null=True, related_name='userpcconflict_user')
    pc = ForeignKey(UserProfile, null=True, related_name='userpcconflict_pc')

    @staticmethod
    def jeeves_get_private_user(uppc):
        return None
    @staticmethod
    def jeeves_get_private_pc(uppc):
        return None

    @staticmethod
    @label_for('user', 'pc')
    @jeeves
    def jeeves_restrict_userpcconflictlabel(uppc, ctxt):
        return True
        #return ctxt.level == 'chair' or uppc.user == ctxt

class Paper(Model):
    #latest_version = ForeignKey('PaperVersion', related_name='latest_version_of', null=True)
    # add this below because of cyclic dependency; awkward hack
    # (limitation of JeevesModel not ordinary Model)
    author = ForeignKey(UserProfile, null=True)
    accepted = BooleanField()

    @staticmethod
    def jeeves_get_private_author(paper):
        return None

    @staticmethod
    @label_for('author')
    @jeeves
    def jeeves_restrict_paperlabel(paper, ctxt):
        if phase == 'final':
            return True
        else:
            return (paper != None and paper.author == ctxt) or (ctxt != None and ctxt.level == 'chair')

    class Meta:
        db_table = 'papers'

class PaperPCConflict(Model):
    paper = ForeignKey(Paper, null=True)
    pc = ForeignKey(UserProfile, null=True)

    @staticmethod
    def jeeves_get_private_paper(ppcc): return None
    @staticmethod
    def jeeves_get_private_pc(ppcc): return None

    @staticmethod
    @label_for('paper', 'pc')
    @jeeves
    def jeeves_restrict_paperpcconflictlabel(ppcc, ctxt):
        return True
        #return ctxt.level == 'admin' or (ppcc.paper != None and ppcc.paper.author == ctxt)

class PaperCoauthor(Model):
    paper = ForeignKey(Paper, null=True)
    author = CharField(max_length=1024)

    @staticmethod
    def jeeves_get_private_paper(pco): return None
    @staticmethod
    def jeeves_get_private_author(pco): return ""

    @staticmethod
    @label_for('paper', 'author')
    @jeeves
    def jeeves_restrict_papercoauthorlabel(pco, ctxt):
        if pco.paper == None:
            return False
        if PaperPCConflict.objects.get(paper=pco.paper, pc=ctxt) != None:
            return False
        ans = ctxt.level == 'chair' or (pco.paper != None and pco.paper.author == ctxt)
        return ans

#class PaperReviewer(Model):
#    paper = ForeignKey(Paper, null=True)
#    reviewer = ForeignKey(UserProfile, null=True)

#    @staticmethod
#    def jeeves_get_private_paper(pco): return None
#    @staticmethod
#    def jeeves_get_private_reviewer(pco): return None

#    @staticmethod
#    @label_for('paper', 'reviewer')
#    @jeeves
#    def jeeves_restrict_paperreviewerlabel(prv, ctxt):
#        return ctxt.level == 'pc' or ctxt.level == 'chair'

class ReviewAssignment(Model):
    paper = ForeignKey(Paper, null=True)
    user = ForeignKey(UserProfile, null=True)
    assign_type = CharField(max_length=8, null=True,
        choices=(('none','none'),
                ('assigned','assigned'),
                ('conflict','conflict')))

    class Meta:
        db_table = 'review_assignments'

    @staticmethod
    def jeeves_get_private_paper(rva): return None
    @staticmethod
    def jeeves_get_private_user(rva): return None
    @staticmethod
    def jeeves_get_private_assign_type(rva): return 'none'

    @staticmethod
    @label_for('paper', 'user', 'assign_type')
    @jeeves
    def jeeves_restrict_paperreviewerlabel(prv, ctxt):
        if prv != None and PaperPCConflict.objects.get(paper=prv.paper, pc=ctxt) != None:
            return False
        return ctxt.level == 'pc' or ctxt.level == 'chair'

class PaperVersion(Model):
    paper = ForeignKey(Paper, null=True)

    title = CharField(max_length=1024)
    contents = FileField(upload_to='papers')
    abstract = TextField()
    time = DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'paper_versions'

    @staticmethod
    @label_for('paper', 'title', 'contents', 'abstract')
    @jeeves
    def jeeves_restrict_paperversionlabel(pv, ctxt):
        if pv == None or pv.paper == None or PaperPCConflict.objects.get(paper=pv.paper, pc=ctxt) != None:
            return False
        return (pv.paper != None and pv.paper.author == ctxt) or ctxt.level == 'pc' or ctxt.level == 'chair'
    
    @staticmethod
    def jeeves_get_private_paper(pv): return None
    @staticmethod
    def jeeves_get_private_title(pv): return ""
    @staticmethod
    def jeeves_get_private_contents(pv): return ""
    @staticmethod
    def jeeves_get_private_abstract(pv): return ""

# see comment above
Paper.latest_version = ForeignKey(PaperVersion, related_name='latest_version_of', null=True)

class Tag(Model):
    name = CharField(max_length=32)
    paper = ForeignKey(Paper, null=True)

    class Meta:
        db_table = 'tags'

class Review(Model):
    time = DateTimeField(auto_now_add=True)
    paper = ForeignKey(Paper, null=True)
    reviewer = ForeignKey(UserProfile, null=True)
    contents = TextField()

    score_novelty = IntegerField()
    score_presentation = IntegerField()
    score_technical = IntegerField()
    score_confidence = IntegerField()

    @staticmethod
    def jeeves_get_private_paper(review): return None
    @staticmethod
    def jeeves_get_private_reviewer(review): return None
    @staticmethod
    def jeeves_get_private_contents(review): return ""
    @staticmethod
    def jeeves_get_private_score_novelty(review): return -1
    @staticmethod
    def jeeves_get_private_score_presentation(review): return -1
    @staticmethod
    def jeeves_get_private_score_technical(review): return -1
    @staticmethod
    def jeeves_get_private_score_confidence(review): return -1

    @staticmethod
    @label_for('paper', 'reviewer', 'contents', 'score_novelty', 'score_presentation', 'score_technical', 'score_confidence')
    @jeeves
    def jeeves_restrict_reviewlabel(review, ctxt):
        if review != None and PaperPCConflict.objects.get(paper=review.paper, pc=ctxt) != None:
            return False
        return ctxt.level == 'chair' or ctxt.level == 'pc' or \
                (phase == 'final' and review.paper.author == ctxt)

    class Meta:
        db_table = 'reviews'

class Comment(Model):
    time = DateTimeField(auto_now_add=True)
    paper = ForeignKey(Paper, null=True)
    user = ForeignKey(UserProfile, null=True)
    contents = TextField()

    class Meta:
        db_table = 'comments'

    @staticmethod
    def jeeves_get_private_paper(review): return None
    @staticmethod
    def jeeves_get_private_user(review): return None
    @staticmethod
    def jeeves_get_private_contents(review): return ""

    @staticmethod
    @label_for('paper', 'user', 'contents')
    @jeeves
    def jeeves_restrict_reviewlabel(comment, ctxt):
        if comment != None and PaperPCConflict.objects.get(paper=comment.paper, pc=ctxt) != None:
            return False
        return ctxt.level == 'chair' or ctxt.level == 'pc'

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created and instance.is_superuser: 
        UserProfile.objects.create(
            username=instance.username,
            email=instance.email,
            level='chair',
        )

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.models import User
from django.views import generic
from datetime import date
import urllib
import random

import forms

from models import Paper, PaperVersion, UserProfile, Review, ReviewAssignment, Comment, UserPCConflict, PaperCoauthor, PaperPCConflict

from sourcetrans.macro_module import macros, jeeves
import JeevesLib

def register_account(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect("index")

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.save()

            UserProfile.objects.create(
                username=user.username,
                name=request.POST.get('name',''),
                affiliation=request.POST.get('affiliation',''),
                level='normal',
                email=request.POST.get('email', ''),
            )

            user = authenticate(username=request.POST['username'],
                         password=request.POST['password1'])
            login(request, user)
            return HttpResponseRedirect("index")
    else:
        form = UserCreationForm()

    return render_to_response("registration/account.html", RequestContext(request,
        {
            'form' : form,
            'which_page' : "register"
        }))

@jeeves
def add_to_context(context_dict, request, template_name, profile, concretize):
    template_name = concretize(template_name)
    context_dict['concretize'] = concretize

    context_dict['is_admin'] = profile != None and profile.level == "chair"
    context_dict['profile'] = profile

    context_dict['is_logged_in'] = (request.user and
                                    request.user.is_authenticated() and
                                    (not request.user.is_anonymous()))

def request_wrapper(view_fn):
    def real_view_fn(request):
        try:
            ans = view_fn(request)
            template_name = ans[0]
            context_dict = ans[1]

            profile = UserProfile.objects.get(username=request.user.username)

            if template_name == "redirect":
                path = context_dict
                return HttpResponseRedirect(JeevesLib.concretize(profile, path))

            concretizeState = JeevesLib.jeevesState.policyenv.getNewSolverState(profile)
            def concretize(val):
                return concretizeState.concretizeExp(val, JeevesLib.jeevesState.pathenv.getEnv())
            #concretize = lambda val : JeevesLib.concretize(profile, val)
            add_to_context(context_dict, request, template_name, profile, concretize)

            #print 'concretized is', concretize(context_dict['latest_title'])

            return render_to_response(template_name, RequestContext(request, context_dict))

        except Exception:
            import traceback
            traceback.print_exc()
            raise

    real_view_fn.__name__ = view_fn.__name__
    return real_view_fn

@login_required
@request_wrapper
@jeeves
def index(request):
    user = UserProfile.objects.get(username=request.user.username)

    return (   "index.html"
           , { 'name' : user.name 
             , 'which_page': "home" })

@request_wrapper
@jeeves
def about_view(request):
  return ( "about.html"
         , { 'which_page' : "about" } )

@login_required
@request_wrapper
@jeeves
def papers_view(request):
    user = UserProfile.objects.get(username=request.user.username)

    papers = Paper.objects.all()
    paper_data = JeevesLib.JList2()
    for paper in papers:
        paper_versions = PaperVersion.objects.filter(paper=paper).order_by('-time').all()
        latest_version_title = paper_versions[0].title if paper_versions.__len__() > 0 else None

        paper_data.append({
            'paper' : paper,
            'latest' : latest_version_title
        })

    return ("papers.html", {
        'papers' : papers
      , 'which_page' : "home"
      , 'paper_data' : paper_data
      , 'name' : user.name
    })

@login_required
@request_wrapper
@jeeves
def paper_view(request):
    user = UserProfile.objects.get(username=request.user.username)

    paper = Paper.objects.get(jeeves_id=request.GET.get('id', ''))
    if paper != None:
        if request.method == 'POST':
            if request.POST.get('add_comment', 'false') == 'true':
                Comment.objects.create(paper=paper, user=user,
                            contents=request.POST.get('comment', ''))

            elif request.POST.get('add_review', 'false') == 'true':
                Review.objects.create(paper=paper, reviewer=user,
                            contents=request.POST.get('review', ''),
                            score_novelty=int(request.POST.get('score_novelty', '1')),
                            score_presentation=int(request.POST.get('score_presentation', '1')),
                            score_technical=int(request.POST.get('score_technical', '1')),
                            score_confidence=int(request.POST.get('score_confidence', '1')),
                          )
            elif request.POST.get('new_version', 'false') == 'true' and user == paper.author:
                contents = request.FILES.get('contents', None)
                if contents != None and paper.author != None:
                    set_random_name(contents)
                    PaperVersion.objects.create(paper=paper,
                        title=request.POST.get('title', ''),
                        contents=contents,
                        abstract=request.POST.get('abstract', ''),
                    )

        paper_versions = PaperVersion.objects.filter(paper=paper).order_by('-time').all()
        coauthors = PaperCoauthor.objects.filter(paper=paper).all()
        latest_abstract = paper_versions[0].abstract if paper_versions.__len__() > 0 else None
        latest_title = paper_versions[0].title if paper_versions.__len__() > 0 else None
        reviews = Review.objects.filter(paper=paper).order_by('-time').all()
        comments = Comment.objects.filter(paper=paper).order_by('-time').all()
        author = paper.author
    else:
        paper = None
        paper_versions = []
        coauthors = []
        latest_abstract = None
        latest_title = None
        reviews = []
        comments = []
        author = None

    return ("paper.html", {
        'paper' : paper,
        'paper_versions' : paper_versions,
        'author' : author,
        'coauthors' : coauthors,
        'latest_abstract' : latest_abstract,
        'latest_title' : latest_title,
        'reviews' : reviews,
        'comments' : comments,
        'which_page' : "paper",
        'review_score_fields': [ ("Novelty", "score_novelty", 10)
                               , ("Presentation", "score_presentation", 10)
                               , ("Technical", "score_technical", 10)
                               , ("Confidence", "score_confidence", 10) ]  
  })

def set_random_name(contents):
    contents.name = '%030x' % random.randrange(16**30) + ".pdf"

@login_required
@request_wrapper
@jeeves
def submit_view(request):
    user = UserProfile.objects.get(username=request.user.username)

    if request.method == 'POST':
        coauthors = request.POST.getlist('coauthors[]')
        title = request.POST.get('title', None)
        abstract = request.POST.get('abstract', None)
        contents = request.FILES.get('contents', None)

        if title == None or abstract == None or contents == None:
            return ("submit.html", {
                'coauthors' : coauthors,
                'title' : title,
                'abstract' : abstract,
                'contents' : contents.name,
                'error' : 'Please fill out all fields',
                'which_page' : "submit",
            })

        paper = Paper.objects.create(author=user, accepted=False)
        for coauthor in coauthors:
            if coauthor != "":
                PaperCoauthor.objects.create(paper=paper, author=coauthor)
        set_random_name(contents)
        PaperVersion.objects.create(
            paper=paper,
            title=title,
            abstract=abstract,
            contents=contents
        )

        for conf in request.POST.getlist('pc_conflicts[]'):
            new_pc_conflict = UserProfile.objects.get(username=conf)
            PaperPCConflict.objects.create(paper=paper, pc=new_pc_conflict)

        return ("redirect", "paper?id=" + paper.jeeves_id)

    pcs = UserProfile.objects.filter(level='pc').all()
    pc_conflicts = [uppc.pc for uppc in UserPCConflict.objects.filter(user=user).all()]
    
    return ("submit.html", {
        'coauthors' : [],
        'title' : '',
        'abstract' : '',
        'contents' : '',
        'error' : '',
        "pcs": [{'pc':pc, 'conflict':pc in pc_conflicts} for pc in pcs],
        'pc_conflicts' : pc_conflicts,
        'which_page': "submit",
    })

@login_required
@request_wrapper
@jeeves
def profile_view(request):
    profile = UserProfile.objects.get(username=request.user.username)
    if profile == None:
        profile = UserProfile(username=request.user.username)
        profile.level = 'normal'
    pcs = UserProfile.objects.filter(level='pc').all()
    
    if request.method == 'POST':
        profile.name = request.POST.get('name', '')
        profile.affiliation = request.POST.get('affiliation', '')
        profile.acm_number = request.POST.get('acm_number', '')
        profile.email = request.POST.get('email', '')
        profile.save()

        UserPCConflict.objects.filter(user=profile).delete()
        pc_conflicts = []
        for conf in request.POST.getlist('pc_conflicts[]'):
            new_pc_conflict = UserProfile.objects.get(username=conf)
            UserPCConflict.objects.create(user=profile, pc=new_pc_conflict)
            pc_conflicts.append(new_pc_conflict)
    else:
        pc_conflicts = [uppc.pc for uppc in UserPCConflict.objects.filter(user=profile).all()]

    return ("profile.html", {
        "name": profile.name,
        "affiliation": profile.affiliation,
        "acm_number": profile.acm_number,
        "pc_conflicts": pc_conflicts,
        "email": profile.email,
        "pcs": pcs,
        "which_page": "profile",
        "pcs": [{'pc':pc, 'conflict':pc in pc_conflicts} for pc in pcs],
    })

@login_required
def submit_review_view(request):
    user = UserProfile.objects.get(username=request.user.username)

    try:
        if request.method == 'GET':
            paper_id = int(request.GET['id'])
        elif request.method == 'POST':
            paper_id = int(request.POST['id'])
        paper = Paper.objects.filter(id=paper_id).get()
        review = Review()
        review.paper = paper
        review.reviewer = user
        if request.method == 'POST':
            form = forms.SubmitReviewForm(request.POST, instance=review)
            if form.is_valid():
                form.save(paper)
                return HttpResponseRedirect("paper?id=%s" % paper_id)
        else:
            form = forms.SubmitReviewForm()
    except (ValueError, KeyError, Paper.DoesNotExist):
        paper = None
        form = None

    return render_to_response("submit_review.html", RequestContext(request, {
        'form' : form,
        'paper' : paper,
        'which_page' : "submit_review",
    }))

@login_required
@request_wrapper
@jeeves
def users_view(request):
    user = UserProfile.objects.get(username=request.user.username)
    if user.level != 'chair':
        return (   "redirect", "/index")

    user_profiles = UserProfile.objects.all()

    if request.method == 'POST':
        for profile in user_profiles:
            query_param_name = 'level-' + profile.username
            level = request.POST.get(query_param_name, '')
            if level in ['normal', 'pc', 'chair']:
                profile.level = level
                profile.save()

    return ("users_view.html", {
        'user_profiles': user_profiles,
        'which_pages' : "users"
    })

@login_required
def submit_comment_view(request):
    user = UserProfile.objects.get(username=request.user.username)

    try:
        if request.method == 'GET':
            paper_id = int(request.GET['id'])
        elif request.method == 'POST':
            paper_id = int(request.POST['id'])
        paper = Paper.objects.filter(id=paper_id).get()
        comment = Comment()
        comment.paper = paper
        comment.user = user
        if request.method == 'POST':
            form = forms.SubmitCommentForm(request.POST, instance=comment)
            if form.is_valid():
                form.save(paper)
                return HttpResponseRedirect("paper?id=%s" % paper_id)
        else:
            form = forms.SubmitCommentForm()
    except (ValueError, KeyError, Paper.DoesNotExist):
        paper = None
        form = None

    return render_to_response("submit_comment.html", RequestContext(request, {
        'form' : form,
        'paper' : paper,
        'which_page' : "submit_comment"
    }))

#@jeeves
#def get_rev_assign(paper, reviewer):
#    revassigs = ReviewAssignment.objects.filter(paper=paper, user=reviewer).all()
#    assignment = revassigs[0] if revassigs.__len__() > 0 else None
#    return assignment

@login_required
@request_wrapper
@jeeves
def assign_reviews_view(request):
    possible_reviewers = UserProfile.objects.filter(level='pc').all()

    reviewer = UserProfile.objects.get(username=request.GET.get('reviewer_username', '')) # might be None

    if reviewer != None:
        papers = Paper.objects.all()

        if request.method == 'POST':
            ReviewAssignment.objects.filter(user=reviewer).delete()
            for paper in papers:
                ReviewAssignment.objects.create(paper=paper, user=reviewer,
                            assign_type='assigned'
                                if request.POST.get('assignment-' + paper.jeeves_id, '')=='yes'
                                else 'none')
        papers_data = [{
            'paper' : paper,
            'latest_version' : PaperVersion.objects.filter(paper=paper).order_by('-time').all()[-1],
            'assignment' : ReviewAssignment.objects.get(paper=paper, user=reviewer),
            'has_conflict' : PaperPCConflict.objects.get(pc=reviewer, paper=paper) != None,
        } for paper in papers]
    else:
        papers_data = []

    return ("assign_reviews.html", {
        'reviewer' : reviewer,
        'possible_reviewers' : possible_reviewers,
        'papers_data' : papers_data,
        'which_page' : "assign_reviews"
    })

@login_required
def search_view(request):
    # TODO choose the actual set of possible reviewers
    possible_reviewers = list(User.objects.all())
    possible_authors = list(User.objects.all())

    form = forms.SearchForm(request.GET, reviewers=possible_reviewers, authors=possible_authors)
    if form.is_valid():
        results = form.get_results()
    else:
        results = []

    return render_to_response("search.html", RequestContext(request, {
        'form' : form,
        'results' : results,
        'which_page' : "search"
    }))
def treatments_view(request, patient):
	treatments=[
		{
			"Service" : "021009W",
			"DatePerformed" : date(2012,4,12),
			"PrescribingEntity" : "West Health",
			"PerformingEntity" : "Enlit Surgical"
		},
		{
			"Service" : "ADA:D4211",
			"DatePerformed" : date(2012,6,26),
			"PrescribingEntity" : "Cooper Base Dental",
			"PerformingEntity" : "Cooper Base Dental"
		},
		{
			"Service" : "D7287",
			"DatePerformed" : date(2013,1,3),
			"PrescribingEntity" : "Beautiful Smile",
			"PerformingEntity" : "Mary Orman, DDS"
		},
		{
			"Service" : "D2970",
			"DatePerformed" : date(2013,3,2),
			"PrescribingEntity" : "Samuel Borndi, DMD",
			"PerformingEntity" : "Enlit Surgical"
		}
	]
	return render_to_response("treatments.html", RequestContext(request, {"treatments":treatments}))

def diagnoses_view(request, patient):
	diagnoses=[
		{
			"Manifestation" : "A38.8",
			"DateRecognized" : date(2012,10,17),
			"RecognizingEntity" : "Solomon Health",
			"Diagnosis" : "Negative"
		},
		{
			"Manifestation" : "E54",
			"DateRecognized" : date(2012,11,24),
			"RecognizingEntity" : "Cragley Medical National",
			"Diagnosis" : "Negative"
		},
		{
			"Manifestation" : "B01.0",
			"DateRecognized" : date(2013,2,1),
			"RecognizingEntity" : "Southwest Hospital",
			"Diagnosis" : "Negative"
		},
		{
			"Manifestation" : "T84.012",
			"DateRecognized" : date(2013,10,17),
			"RecognizingEntity" : "Dr. Wragley Medical Center",
			"Diagnosis" : "Positive"
		}
    ]
	return render_to_response("diagnoses.html", RequestContext(request, {"diagnoses":diagnoses}))

def info_view(request, patient):
	dataset = [
		("Name","John H. Doe"),
		("Gender","Male"),
		("Birth Date", date(1986,4,3)),
		("Address","42 Granite Way, Vineville, MI, 42459"),
		("Telephone Number","729-555-4708"),
		("Fax Number","939-555-1439"),
		("Social Security Number","219-09-9999"),
		("Driver's License Number","2549305480"),
		("Email","jdoe8643@example.org"),
		("Employer","Macro Creations Inc."),
	]
	return render_to_response("info.html", RequestContext(request, {"dataset":dataset}))

########NEW FILE########
__FILENAME__ = logging_middleware
import logging
from django.db import connection
from django.utils.encoding import smart_str

logger = logging.getLogger(__name__)

# Based off of https://djangosnippets.org/snippets/290/

class ConfLoggingMiddleware(object):
    def process_request(self, request):
        pass

    def process_response(self, request, response):
        logger.info("%s \"%s\" (%s)" % (request.method, smart_str(request.path_info), response.status_code))

        indentation = 2
        if len(connection.queries) > 0:
            total_time = 0.0
            for query in connection.queries:
                nice_sql = query['sql'].replace('"', '').replace(',',', ')
                sql = "[%s] %s" % (query['time'], nice_sql)
                total_time = total_time + float(query['time'])
                logger.info("%s%s\n" % (" "*indentation, sql))
            replace_tuple = (" "*indentation, str(total_time))
            logger.info("%s[TOTAL TIME: %s seconds]" % replace_tuple)
        return response

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

import macropy.activate
from macropy.core.exporters import SaveExporter
macropy.exporter = SaveExporter("exported", ".")

import JeevesLib
JeevesLib.init()

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
"""
Django settings for hipaa project.  
For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(__file__)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '!$e(y9&5ol=#s7wex!xhv=f&5f2@ufjez3ee9kdifw=41p_+%*'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates/'),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

ALLOWED_HOSTS = []

TEMPLATE_LOADERS = (
    'django_jinja.loaders.AppLoader',
    'django_jinja.loaders.FileSystemLoader',
)
DEFAULT_JINJA2_TEMPLATE_EXTENSION = '.html'

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_jinja',
    'timelog',
    'hipaa',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'timelog.middleware.TimeLogMiddleware',
    'logging_middleware.ConfLoggingMiddleware',
)

ROOT_URLCONF = 'urls'

WSGI_APPLICATION = 'wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)

# possible phases are submit, review, final
CONF_PHASE = 'submit'

LOG_PATH = os.path.join(BASE_DIR, 'logs')
TIMELOG_LOG = os.path.join(LOG_PATH, 'timelog.log')
SQL_LOG = os.path.join(LOG_PATH, 'sqllog.log')

LOGGING = {
  'version': 1,
  'formatters': {
    'plain': {
      'format': '%(asctime)s %(message)s'},
    },
  'handlers': {
    'timelog': {
      'level': 'DEBUG',
      'class': 'logging.handlers.RotatingFileHandler',
      'filename': TIMELOG_LOG,
      'maxBytes': 1024 * 1024 * 5,  # 5 MB
      'backupCount': 5,
      'formatter': 'plain',
    },
    'sqllog': {
      'level': 'DEBUG',
      'class': 'logging.handlers.RotatingFileHandler',
      'filename': SQL_LOG,
      'maxBytes': 1024 * 1024 * 5,  # 5 MB
      'backupCount': 5,
      'formatter': 'plain',
    },
  },
  'loggers': {
    'timelog.middleware': {
      'handlers': ['timelog'],
      'level': 'DEBUG',
      'propogate': False,
     },
    'logging_middleware': {
      'handlers': ['sqllog'],
      'level': 'DEBUG',
      'propogate': False
    },
  },
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from django.conf.urls.static import static
from django.conf import settings

from hipaa import views

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'conf.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),

    url(r'^accounts/login/$', 'django.contrib.auth.views.login'),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout_then_login'),
    url(r'^accounts/profile/$', views.profile_view),

    url(r'^register$', views.register_account),

    url(r'^index$', views.papers_view),
    url(r'^$', views.papers_view),
    url(r'^submit$', views.submit_view),
    url(r'^papers$', views.papers_view),
    url(r'^paper$', views.paper_view),
    url(r'^submit_review$', views.submit_review_view),
    url(r'^submit_comment$', views.submit_comment_view),
    url(r'^assign_reviews$', views.assign_reviews_view),
    url(r'^search$', views.search_view),
    url(r'^about$', views.about_view),
    url(r'^users$', views.users_view),
    url(r'^patients/(?P<patient>[0-9]+)/treatments$', views.treatments_view),
    url(r'^patients/(?P<patient>[0-9]+)/diagnoses$', views.diagnoses_view),
    url(r'^patients/(?P<patient>[0-9]+)/info$', views.info_view),
    url(r'^patients/(?P<patient>[0-9]+)/$', views.info_view),
    url(r'^entity/(?P<entity>[0-9]+)/transactions', views.treatments_view),
    url(r'^entity/(?P<entity>[0-9]+)/associates', views.diagnoses_view),
    url(r'^entity/(?P<entity>[0-9]+)/directory', views.info_view),
    url(r'^entity/(?P<entity>[0-9]+)/$', views.info_view),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for conf project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hipaa.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = BaseClasses
from OpenmrsClasses import *

class BaseOpenmrsObject(OpenmrsObject):
    def __init__(self):
        self.uuid = str(uuid4()) #generates a random uuid

    def getUuid(self):
        return self.uuid

    def setUuid(self, uuid):
        self.uuid = uuid

    def hashCode(self):
        if self.getUuid() == None:
            return hash(object) #im not sure if this serves the same purpose as "return super.hashCode();" in the JAVA code
        return hash(self.getUuid())

    def equals(self, obj):
        if self is obj:
            return True
        if not(isinstance(obj, BaseOpenmrsObject)):
            return False
        other = obj
        if self.getUuid() == None:
            return False
        return self.getUuid() == (other.getUuid())

    def __str__(self):
        return "ClassName{hashCode= " + str(self.hashCode()) + "," + "uuid=" + str(self.uuid) + "}"
    
class BaseOpenmrsData(BaseOpenmrsObject, OpenmrsData):
    def __init(self,creator=None,dateCreated=None, changedBy=None, dateChanged=None, \
               voided=False,dateVoided=None, voidedBy=None, voidReason=None):
        self.creator = creator
        self.dateCreated = dateCreated
        self.changedBy = changedBy
        self.dateChanged = dateChanged
        self.voided = voided
        self.dateVoided = dateVoided
        self.voidedBy = voidedBy
        self.voidReason = voidReason

    def getCreator(self):
        return self.creator
    def setCreator(self, creator):
        self.creator = creator
    def getDateCreated(self):
        return self.dateCreated
    def setDateCreated(self, dateCreated):
        self.dateCreated = dateCreated
    def getChangedBy(self):
        return self.changedBy
    def setChangedBy(self, changedBy):
        self.changedBy = changedBy
    def getDateChanged(self):
        return self.dateChanged
    def setDateChanged(self, dateChanged):
        self.dateChanged = dateChanged
    def isVoided(self):
        return self.voided
    def getVoided(self):
        return self.isVoided()
    def setVoided(self, voided):
        self.voided = voided
    def getDateVoided(self):
        return self.dateVoided
    def setDateVoided(self, dateVoided):
        self.dateVoided = dateVoided
    def getVoidedBy(self):
        return self.voidedBy
    def setVoidedBy(self, voidedBy):
        self.voidedBy = voidedBy
    def getVoidReason(self):
        return self.voidReason
    def setVoidReason(self, voidReason):
        self.voidReason = voidReason

class BaseOpenmrsMetadata(BaseOpenmrsObject, OpenmrsMetadata):
    def __init__(self,name=None, description=None, creator=None, dateCreated=None, \
                 changedBy=None, retired=False, retiredBy = None):
        self.name = name
        self.description = description
        self.creator = creator
        self.dateCreated = dateCreated
        self.changedBy = changedBy
        self.dateChanged = dateChanged
        self.retired = retired
        self.dateRetired = dateRetired
        self.retiredBy = retiredBy
        self.retireReason = retireReason

########NEW FILE########
__FILENAME__ = Interfaces
from OpenmrsClasses import *

class Auditable(OpenmrsObject):
    __metaclass__= ABCMeta
    
    def getCreator(self):
        pass
    def setCreator(self, creator):
        pass
    def getDateCreated(self):
        pass
    def setDateCreated(self, dateCreated):
        pass
    def getChangedBy(self):
        pass
    def setChangedBy(self, changedBy):
        pass
    def getDateChanged(self):
        pass
    def setDateChanged(self, dateChanged):
        pass
    
class Attributable:
    __metaclass__= ABCMeta

    def hydrate(self, s):
        pass
    def serialize(self):
        pass
    def getPossibleValues(self):
        pass
    def findPossibleValues(self, searchText):
        pass
    def getDisplayString(self):
        pass
class Retireable(OpenmrsObject):
    __metaclass__ = ABCMeta
    
    def isRetired(self):
        pass
    def setRetired(self, retired):
        pass
    def getRetiredBy(self):
        pass
    def setRetiredBy(self, retiredBy):
        pass
    def getDateRetired(self):
        pass
    def setDateRetired(self, dateRetired):
        pass
    def getRetireReason(self):
        pass
    def setRetireReason(self, retireReason):
        pass

class Voidable(OpenmrsObject):
    __metaclass__ = ABCMeta

    def isVoided(self):
        pass
    def setVoided(self, voided):
        pass
    def getVoidedBy(self):
        pass
    def setVoidedBy(self, voidedBy):
        pass
    def getDateVoided(self):
        pass
    def setDateVoided(self, dateVoided):
        pass
    def getVoidReason(self):
        pass
    def setVoidReason(self, voidReason):
        pass
    
class Orderable(Order):
    __metaclass__ = ABCMeta

    def getUniqueIdentifier(self):
        pass
    def getConcept(self):
        pass
    def getName(self):
        pass
    def getDescription(self):
        pass

########NEW FILE########
__FILENAME__ = Obs
from BaseClasses import *
import sets
import logging

class Node:
    def __init__(self, cargo, nextNode, previousNode):
        self.cargo = cargo
        self.next = nextNode
        self.previous = previousNode
    def __str__(self):
        print str(self.cargo)
    
class ordered_set(set):
    def __init__(self, *args, **kwargs):
        set.__init__(self, *args, **kwargs)
        self.elements = []
        for i in self:
            self.elements.append(i)
        self._order = self.elements #NOT SURE IF ORDERED IN ORDER ELTS WERE ADDED

    def add(self, elt):
        set.add(self, elt)
        if elt in self._order:
            self._order.remove(elt)
        self._order.append(elt)

    def remove(self, elt):
        set.remove(self, elt)
        self._order.remove(elt)

    def order(self):
        return self._order[:]

    def ordered_items(self):
        return [(elt) for elt in self._order]
    
o = ordered_set(set([3, 2, 5, 4, 10]))
print o

            
class Obs(BaseOpenmrsData): #needs to implement Serializable
    serialVersionUID = 112342333L
    #log = LogFactory.getLog(Obs) #haven't defined a LogFactory yet

    def __init__(self, obsId=None,question=None, obsDatetime=None, accessionNumber=None,\
                 obsGroup = None, groupMembers=set(), valueCoded=None, valueCodedName=None,\
                 valueDrug=None, valueGroupId=None,valueDatetime=None, valueNumeric=None,\
                 valueModifier=None, valueText=None, valueComplex=None,complexData = None,\
                 comment=None, personId=None,person=None, order=None, location=None,encounter=None,\
                 previousVersion=None, voided=None, creator = None, dateCreated=None, voidedBy= None,\
                 dateVoided=None, voidReason = None):
        self.obsId = obsId
        self.concept = question
        self.obsDatetime = obsDatetime
        self.accessionNumber = accessionNumber
        self.obsGroup = obsGroup
        self.groupMembers = groupMembers #set
        self.valueCoded = valueCoded #Concept obj
        self.valueCodedName = valueCodedName #ConceptName obj
        self.valueDrug = valueDrug #Drug obj
        self.valueGroupId = valueGroupId
        self.valueDatetime = valueDatetime
        self.valueNumeric = valueNumeric
        self.valueModifier = valueModifier
        self.valueText = valueText
        self.valueComplex = valueComplex
        self.complexData = complexData #transient: can't be serialized
        self.comment = comment
        self.person = person
        if person != None:
            self.personId = person.getPersonId() #transient
        self.order = order
        self.location = location
        self.encounter = encounter
        self.previousVersion = previousVersion
        self.voided = voided
        self.creator = creator
        self.dateCreated = dateCreated
        self.voidedBy = voidedBy
        self.dateVoided = dateVoided
        self.voidReason = voidReason
    def newInstance(self, obsToCopy):
        newObs = Obs(obsToCopy.getPerson(), obsToCopy.getConcept(), obsToCopy.getObsDatetime(),\
                     obsToCopy.getLocation())
        newObs.setObsGroup(obsToCopy.getObsGroup())
        newObs.setAccessionNumber(obsToCopy.getAccessionNumber())
        newObs.setValueCoded(obsToCopy.getValueCoded())
        newObs.setValueDrug(obsToCopy.getValueDrug())
        newObs.setValueGroupId(obsToCopy.getValueGroupId())
        newObs.setValueDatetime(obsToCopy.getValueDatetime())
        newObs.setValueNumeric(obsToCopy.getValueNumeric())
        newObs.setValueModifier(obsToCopy.getValueModifier())
        newObs.setValueText(obsToCopy.getValueText())
        newObs.setComment(obsToCopy.getComment())
        newObs.setOrder(obsToCopy.getOrder())
        newObs.setEncounter(obsToCopy.getEncounter())
        newObs.setCreator(obsToCopy.getCreator())
        newObs.setDateCreated(obsToCopy.getDateCreated())
        newObs.setVoided(obsToCopy.getVoided())
        newObs.setVoidedBy(obsToCopy.getVoidedBy())
        newObs.setDateVoided(obsToCopy.getDateVoided())
        newObs.setVoidReason(obsToCopy.getVoidReason())
        
        newObs.setValueComplex(obsToCopy.getValueComplex())
        newObs.setComplexData(obsToCopy.getComplexData())

        if obsToCopy.hasGroupMembers(True):
            for member in obsToCopy.getGroupMembers(True):
                if member.getObsId() == None:
                    newObs.addGroupMember(member)
                else:
                    newObs.addGroupMember(Obs.newInstance(member))
        return newObs
    def getComment(self):
        return self.comment
    def setComment(self, comment):
        self.comment = comment
    def getConcept(self):
        return self.concept
    def setConcept(self, concept):
        self.concept = concept
    def getConceptDescription(self):
        if self.getConcept() == None:
            return None
        return self.concept.getDescription()
    def getEncounter(self):
        return self.encounter
    def setEncounter(self, encounter):
        self.encounter = encounter
    def getLocation(self):
        return self.location
    def setLocation(self, location):
        self.location = location
    def getObsDatetime(self):
        return self.obsDatetime
    def setObsDatetime(self, obsDatetime):
        self.obsDatetime = obsDatetime
    def getObsGroup(self):
        return self.obsGroup
    def setObsGroup(self,obsGroup):
        self.obsGroup = obsGroup

    
    def hasGroupMembers(self, includeVoided=False):
        #uses springFramework library
        pass
        
    def isObsGrouping(self):
        return self.hasGroupMembers(True)
    
    def getGroupMembers(self, includeVoided=False):
        if includeVoided:
            return self.groupMembers
        if self.groupMembers == None:
            return None
        nonVoided = ordered_set(self.groupMembers)
        
        for obs in nonVoided:
            if obs.isVoided():
                nonVoided.remove(obs) #not sure if this is what's required
        return nonVoided
    def setGroupMembers(self, groupMembers):
        self.groupMembers = groupMembers
    def addGroupMember(self, member):
        if member == None:
            return None
        if self.getGroupMembers() == None:
            self.groupMembers = sets.ImmutableSet() #Same as HashSet?
##        if member == self:
##            raise APIException("An obsGroup cannot have itself as a mentor. obsGroup: " + self \
##			        + " obsMember attempting to add: " + member)
            #I think APIException is defined in another JAVA class file; not sure if Python has this
        member.setObsGroup(self)
        self.groupMembers.add(member)
    def removeGroupMember(self, member):
        if (member == None) or self.getGroupMembers() == None:
            return None
        if self.groupMembers.remove(member):
            member.setObsGroup(None)
    def getRelatedObservations(self):
        ret = sets.Set() #Supposed to be ImmutableSet but we can't add elts to that; Set isnt hashed
        if self.isObsGrouping():
            for i in self.getGroupMembers():
                ret.add(i)
            parentObs = self
            while parentObs.getObsGroup() != None :
                for obsSibling in parentObs.getObsGroup().getGroupMembers():
                    if not(obsSibling.isObsGrouping()):
                        ret.add(obsSibling)
                parentObs = parentObs.getObsGroup()
        elif self.getObsGroup() != None:
            for obsSibling in self.getObsGroup().getGroupMembers():
                if not(obsSibling.isObsGrouping()):
                    ret.add(obsSibling)
        return ret
    def getObsId(self):
        return self.obsId
    def setObsId(self,obsId):
        self.obsId = obsId
    def getOrder(self):
        return self.order
    def setOrder(self, order):
        self.order = order
    def getPersonId(self):
        return self.personId
    def setPersonId(self, personId):
        self.personId = personId
    def getPerson(self):
        return self.person
    def setPerson(self, person):
        self.person = person
        if person != None:
            self.personId = person.getPersonId()
    def setValueBoolean(self, valueBoolean):
        if (valueBoolean != None) and (self.getConcept() != None) and self.getConcept().getDatatype().isBoolean():
            if valueBoolean.booleanValue():
                self.setValueCoded(Context().getConceptService().getTrueConcept())
            else:
                self.setValueCoded(Context().getConceptService().getFalseConcept())
        #Context is from api directory
        elif valueBoolean == None:
            self.setValueCoded(None)
    def getValueAsBoolean(self):
        if self.getValueCoded() != None:
            if self.getValueCoded() == Context().getConceptService().getTrueConcept():
                return True
            elif self.getValueCoded() == Context().getConceptService().getFalseConcept():
                return False
        elif self.getValueNumeric() != None:
            if self.getValueNumeric() == 1:
                return True
            elif self.getValueNumeric() == 0:
                return False
        return None
    def getValueBoolean(self):
        if (self.getConcept() != None) and (self.valueCoded != None) and (self.getConcept().getDatatype().isBoolean()):
            trueConcept = Context.getConceptService().getTrueConcept()
            return (trueConcept != None) and (self.valueCoded.getId() == trueConcept.getId())
        return None
    def getValueCoded(self):
        return self.valueCoded
    def setValueCoded(self, valueCoded):
        self.valueCoded = valueCoded
    def getValueCodedName(self):
        return self.valueCodedName
    def setValueCodedName(self, valueCodedName):
        self.valueCodedName = valueCodedName
    def getValueDrug(self):
        return self.valueDrug
    def setValueDrug(self, valueDrug):
        self.valueDrug = valueDrug
    def getValueDatetime(self):
        return self.valueDatetime
    def setValueDatetime(self, valueDatetime):
        self.valueDatetime = valueDatetime
    def getValueDate(self):
        return self.valueDatetime
    def setValueDate(self, valueDate):
        self.valueDatetime = valueDate
    def getValueTime(self):
        return self.valueDatetime
    def setValueTime(self, valueTime):
        self.valueDatetime = valueTime
    def getValueGroupId(self):
        return self.valueGroupId
    def setValueGroupId(self, valueGroupId):
        self.valueGroupId = valueGroupId
    def getValueModifier(self):
        return self.valueModifier
    def setValueModifier(self, valueModifier):
        self.valueModifier = valueModifier
    def getValueNumeric(self):
        return self.valueNumeric
    def setValueNumeric(self, valueNumeric):
        self.valueNumeric = valueNumeric
    def getValueText(self):
        return self.valueText
    def setValueText(self, valueText):
        self.valueText = valueText
    def isComplex(self):
        if self.getConcept() != None:
            return self.getConcept().isComplex()
        return False
    def getValueComplex(self):
        return self.valueComplex
    def setValueComplex(self, valueComplex):
        self.valueComplex = valueComplex
    def setComplexData(self, complexData):
        self.complexData = complexData
    def getComplexData(self):
        return self.complexData
    def getAccessionNumber(self):
        return self.accessionNumber
    def setAccessionNumber(self, accessionNumber):
        self.accessionNumber = accessionNumber
    def getValueAsString(self, locale):
        #Needs NumberFormat and other built in functions
        pass
    def setValueAsString(self, s):
        #logging.Logger.debug("self.getConcept() == " + str(self.getConcept()))
        if (self.getConcept() != None): #and (isBlank(s)): #isBlank(s) checks if s is whitespace, null, or empty. Need to find Python equivalent. 
            abbrev = self.getConcept().getDatatype().getHl7Abbreviation()
            if abbrev == "BIT":
                self.setValueBoolean(s) #s might be lowercase true, not True. Solve this.
            elif abbrev == "CWE":
                raise RuntimeException("Not Yet Implemented")
            elif (abbrev == "NM") or (abbrev == "SN"):
                self.setValueNumeric(s)
            elif abbrev == "DT":
                self.setValueDatetime(s) #dateFormat.parse(s) in JAVA. must be in da specific date format
            elif abbrev == "TM":
                self.setValueDatetime(s) #timeFormat.parse(s) in JAVA too
            elif abbrev == "TS":
                self.setValueDatetime(s) #datetimeFormat.parse(s)
            elif abbrev == "ST":
                self.setValueText(s)
##            else:
##                raise RuntimeException("Don't know how to handle " + str(abbrev))
##        else:
##            raise RuntimeException("concept is None for " + str(self))
    def __str__(self):
        if self.obsId == None:
            return "obs id is None"
        return "Obs #" + str(self.obsId)
    def getId(self):
        return self.getObsId
    def setId(self,Id):
        self.setObsId(Id)
    def getPreviousVersion(self):
        return self.previousVersion
    def setPreviousVersion(self, previousVersion):
        self.previousVersion = previousVersion
    def hasPreviousVersion(self):
        return self.getPreviousVersion() != None

########NEW FILE########
__FILENAME__ = OpenmrsClasses
from abc import ABCMeta, abstractmethod
import uuid
#import org.python.google.common.base.objects as objects #not sure if this is the same as com.google.common.base.Objects in JAVA code
from datetime import datetime, date 
import pickle


#Interfaces
class OpenmrsObject:
    """This is the base interface for all OpenMRS-defined classes"""
    
    __metaclass__ = ABCMeta

    @abstractmethod
    def getId(self):
    #return id - The unique Identifier for the object
        pass
    
    def setId(self, Id):
    #param id - The unique Identifier for the object
        pass
    
    def getUuid(self):
    #return the universally unique id for this object
        pass
    
    def setUuid(self, uuid):
    #param uuid a universally unique id for this object
        pass


    
class OpenmrsData(Auditable, Voidable):

    __metaclass__ = ABCMeta
    
class OpenmrsMetadata(Auditable, Retireable):

    __metaclass__ = ABCMeta

    def getName(self):
        pass
    def setName(self, name):
        pass
    def getDescription(self):
        pass
    def setDescription(self, description):
        pass       
        

    




 

        


########NEW FILE########
__FILENAME__ = Order
from BaseClasses import *

class Enum(set):
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError
    
class Order(BaseOpenmrsData): #serializable has to be implemented
    serialVersionUID = 1L
    OrderAction = Enum(['ORDER', 'DISCONTINUE']) #is this equivalent of enum type in JAVA?
    Urgency = Enum(['ROUTINE', 'STAT'])
    #is it right that these are class attributes?
    
    def __init__(self, creator = None, dateCreated = None, orderId=None, patient=None, concept=None, discontinued = False, \
                 autoExpireDate=None, discontinuedBy=None, discontinuedDate=None, discontinuedReason=None, \
                 encounter=None, instructions=None,accessionNumber=None, orderer=None, startDate=None,\
                 orderNumber=None, previousOrderNumber=None, voided = False, voidedBy = None, dateVoided=None, voidReason=None):
        self.creator = creator
        self.dateCreated = dateCreated
        self.orderId = orderId
        self.patient = patient
        self.concept = concept
        self.discontinued = discontinued
        self.autoExpireDate = autoExpireDate
        self.discontinuedBy = discontinuedBy
        self.discontinuedDate = discontinuedDate
        self.discontinuedReason = discontinuedReason
        self.encounter = encounter
        self.instructions = instructions
        self.accessionNumber = accessionNumber
        self.orderer = orderer
        self.startDate = startDate
        self.orderNumber = orderNumber
        self.previousOrderNumber = previousOrderNumber
        self.orderAction = Order.OrderAction.ORDER
        self.urgency = Order.Urgency.ROUTINE
        self.voided = voided
        self.voidedBy = voidedBy
        self.dateVoided = dateVoided
        self.voidReason = voidReason
        #is it right that these are instance attributes
    def copy(self):
        return self.copyHelper(Order())
    
    def copyHelper(self, target):
        target.setPatient(self.getPatient())
        target.setConcept(self.getConcept())
        target.setInstructions(self.getInstructions())
        target.setStartDate(self.getStartDate())
        target.setAutoExpireDate(self.getAutoExpireDate())
        target.setEncounter(self.getEncounter())
        target.setOrderer(self.getOrderer())
        target.setCreator(self.getCreator())
        target.setDateCreated(self.getDateCreated())
        target.setDiscontinued(self.getDiscontinued())
        target.setDiscontinuedDate(self.getDiscontinuedDate())
        target.setDiscontinuedReason(self.getDiscontinuedReason())
        target.setDiscontinuedBy(self.getDiscontinuedBy())
        target.setAccessionNumber(self.getAccessionNumber())
        target.setVoided(self.isVoided())
        target.setVoidedBy(self.getVoidedBy())
        target.setDateVoided(self.getDateVoided())
        target.setVoidReason(self.getVoidReason())
        target.setOrderNumber(self.getOrderNumber())
        target.setPreviousOrderNumber(self.getPreviousOrderNumber())
        target.setOrderAction(self.getOrderAction())
        target.setUrgency(self.getUrgency())
        return target

    def equals(self, obj):
        if isinstance(obj, Order):
            o = obj
            if (self.getOrderId() != None) and (o.getOrderId != None):
                return self.getOrderId() == o.getOrderId()
        return False
    
    def hashCode(self):
        if self.getOrderId() == None:
            return hash(object) #same as super.hashCode()? super.hashCode() returns diff codes everytime its run
        return hash(self.getOrderId())

    def isDrugOrder(self):
        return False
    def getAutoExpireDate(self):
        return self.autoExpireDate
    def setAutoExpireDate(self, autoExpireDate):
        self.autoExpireDate = autoExpireDate #datetime object
    def getConcept(self):
        return self.concept
    def setConcept(self, concept):
        self.concept = concept
    def getDiscontinued(self):
        return self.discontinued
    def setDiscontinued(self, discontinued):
        self.discontinued = discontinued #should it be discontinued or self.discontinued?
    def getDiscontinuedBy(self):
        return self.discontinuedBy
    def setDiscontinuedBy(self, discontinuedBy):
        self.discontinuedBy=discontinuedBy
    def getDiscontinuedDate(self):
        return self.discontinuedDate
    def setDiscontinuedDate(self, discontinuedDate):
        self.discontinuedDate=discontinuedDate
    def getDiscontinuedReason(self):
        return self.discontinuedReason
    def setDiscontinuedReason(self, discontinuedReason):
        self.discontinuedReason = discontinuedReason
    def getEncounter(self):
        return self.encounter
    def setEncounter(self, encounter):
        self.encounter = encounter
    def getInstructions(self):
        return self.instructions
    def setInstructions(self, instructions):
        self.instructions = instructions
    def getAccessionNumber(self):
        return self.accessionNumber
    def setAccessionNumber(self, accessionNumber):
        self.accessionNumber = accessionNumber
    def getOrderer(self):
        return self.orderer
    def setOrderer(self, orderer):
        self.orderer = orderer
    def getOrderId(self):
        return self.orderId
    def setOrderId(self, orderId):
        self.orderId = orderId
    def getStartDate(self):
        return self.startDate #datetime object
    def setStartDate(self, startDate):
        self.startDate = startDate
    def isCurrent(self, checkDate=None):
        #checkDate is an optional argument so it's equivalent of the two methods
        #isCurrent() and isCurrent(Date checkDate) in JAVA code. If checkDate is None,
        #a datetime object representing today is initialized, which is same as isCurrent(new Date()) 
        if self.isVoided():
            return False
        if checkDate == None:
            checkDate = datetime.now() #this returns the datetime object with microsecond, the JAVA code returns a Date object of when the obj was created
        if (self.startDate != None) and (checkDate < self.startDate):
            return False
        if (self.discontinued != None) and self.discontinued:
            if self.discontinuedDate == None:
                return checkDate == self.startDate
            else:
                return checkDate < self.discontinuedDate
        else:
            if self.autoExpireDate == None:
                return True
            else:
                return checkDate < self.autoExpireDate
            
    def isFuture(self, checkDate=None):
        if self.isVoided():
            return False
        if checkDate == None:
            checkDate = datetime.now()
        return (self.startDate != None) and checkDate < self.startDate
    
    def isDiscontinued(self, checkDate):
        if self.isVoided():
            return False
        if (checkDate == None):
            checkDate = datetime.now()
        if (self.discontinued == None) or not(self.discontinued):
            return False
        if (self.startDate == None) or (checkDate < self.startDate):
            return False
        if (self.discontinuedDate != None) and (self.discontinuedDate > checkDate):
            return False
        return True
    
    def isDiscontinuedRightNow(self):
        return self.isDiscontinued(datetime.now())
    
    def getPatient(self):
        return self.patient
    def setPatient(self, patient):
        self.patient = patient
    def getOrderNumber(self):
        return self.orderNumber
    def setOrderNumber(self, orderNumber):
        self.orderNumber = orderNumber
    def getPreviousOrderNumber(self):
        return self.previousOrderNumber
    def setPreviousOrderNumber(self, previousOrderNumber):
        self.previousOrderNumber = previousOrderNumber
    def getOrderAction(self):
        return self.orderAction
    def setOrderAction(self, orderAction):
        self.orderAction=orderAction
    def getId(self):
        return self.getOrderId()
    def __str__(self):
        #type(self) same as getClass()? 
        return "Order. orderId: " + str(self.orderId) + " patient: " + str(self.patient) + " concept: " + str(self.concept)
    def setId(self, Id):
        self.setOrderId(Id)
    def getUrgency(self):
        return self.urgency
    def setUrgency(self, urgency):
        self.urgency = urgency
        
    def copyForModification(self):
        #I'm not sure if this makes a copy
        copy = self.copyHelper(self)
        copy.orderNumber = None
        copy.previousOrderNumber = self.orderNumber
        #would self.orderNumber be None since copy.orderNumber = None and copy = self?
        return copy

########NEW FILE########
__FILENAME__ = tests
import unittest
from Order import *
from Obs import *
from Interfaces import *
from HeadersForClasses import *

class TestOrderFunctions(unittest.TestCase):

    def setUp(self):
        self.order = Order()
        self.order.setOrderId(9112)
        self.order.setOrderNumber('911')
        
    def test_copy_methods(self):
        copy1 = self.order.copy()
        copy2 = self.order.copyForModification()
        self.assertEqual(self.order.OrderAction.ORDER, 'ORDER')
        self.assertEqual(self.order.Urgency.ROUTINE, 'ROUTINE')
        self.assertIs(copy2, self.order)
        self.assertIsNot(copy1, self.order)
        self.assertIsNot(copy1, copy2)
        self.assertEqual(self.order.hashCode(), self.order.getOrderId())

    def test_date_methods(self):
        self.assertTrue(self.order.isCurrent())
        checkDate = datetime(2013, 12, 25)

        autoExpireDate = datetime(2017, 12, 25)
        self.order.setAutoExpireDate(autoExpireDate)
        self.assertTrue(self.order.isCurrent(checkDate))
        
        discontinuedDate = datetime(2015, 12, 25)
        self.order.setDiscontinuedDate(discontinuedDate)
        self.assertTrue(self.order.isCurrent(checkDate))
        self.assertFalse(self.order.isDiscontinued(checkDate))
        
        startDate = datetime(2014, 12, 25)
        self.order.setStartDate(startDate)
        self.assertFalse(self.order.isCurrent(checkDate))
        self.order.setDiscontinued(True)
        self.assertFalse(self.order.isDiscontinued(checkDate))
        
        checkDate2 = datetime(2016, 12, 25)
        self.assertTrue(self.order.isDiscontinued(checkDate2))

        self.assertTrue(self.order.isFuture(checkDate))
        self.assertFalse(self.order.isDrugOrder())

        obj = Order(orderId = 9112)
        self.assertTrue(self.order.equals(obj))

        
        
class TestObsFunctions(unittest.TestCase):

    def setUp(self):
        self.obs = Obs(913)
        
    def test_newInstance_method(self):
        concept = Concept()
        concept.setDatatype(True)
        
        self.obsToCopy = Obs(Person(), concept, datetime.now(), Location())
        self.newObs = self.obs.newInstance(self.obsToCopy)
        self.assertFalse(self.newObs == self.obsToCopy)#both have None obsId
        self.assertIsNot(self.newObs, self.obsToCopy) 
        
        self.obsToCopy = Obs(9118)
        self.newObs = self.obs.newInstance(self.obsToCopy)
        self.assertFalse(self.newObs == self.obsToCopy)#newObs has None obsId but obsToCopy has an obsId

    def test_obs_group_methods(self):
        self.obs.setObsGroup(None)
        self.assertFalse(self.obs.hasGroupMembers())

        self.obs1 = Obs(127)
        self.obs2 = Obs(9827)
        concept = Concept()
        concept.setSet(True)
        self.obs.setConcept(concept)
        self.obs.setGroupMembers(set([self.obs1, self.obs2]))
        self.assertTrue(self.obs.getGroupMembers(True) != None)
        self.assertTrue(self.obs.getGroupMembers(False) != None)

        self.obs.addGroupMember(Obs(7543))
        self.obs.addGroupMember(self.obs)
        #self.assertRaises(APIException) #the line before should raise this exception

        self.obs.removeGroupMember(self.obs1)
        self.assertIsNone(self.obs1.getObsGroup())

        #self.obsToCopy should be parent group of obs members.  
        ret = self.obs.getRelatedObservations()
        for i in ret:
            self.assertFalse(i.isObsGrouping())
            
    def test_value_methods(self):
        self.obs.setValueBoolean(True)
        #self.assertIsNotNone(self.obs.getValueCoded())

        self.obs.setValueNumeric(1)
        self.assertTrue(self.obs.getValueAsBoolean())

        self.obs.setValueNumeric(0)
        self.assertFalse(self.obs.getValueAsBoolean())

        self.assertFalse(self.obs.isComplex())
        
        self.obs.setValueAsString("True")
        #self.assertTrue(self.obs.getValueAsString())

        concept1 = Concept()
        concept1.setDatatype(ConceptDatatype(13))
        self.obs.setConcept(concept1)
        self.obs.getConcept().getDatatype().setHl7Abbreviation("NM")
        self.obs.setValueAsString("13")
        #self.assertTrue(self.obs.getValueAsString(locale) == "13")

        
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = User
from BaseClasses import *
from Interfaces import *
from sets import *
import logging

class User(BaseOpenmrsMetadata, Attributable):

    serialVersionID = 2L
    #log = LogFactory.getLog(getClass()); needs LogFactory
    
    def __init__(self, userId=None, person=None, systemId=None, username=None, secretQuestion=None, \
                 roles=None, userProperties=None, ):
        self.userId = userId
        self.person = person
        self.systemId = systemId
        self.username = username
        self.secretQuestion = secretQuestion
        self.roles = roles
        self.userProperties = userProperties
        self.proficientLocales = None
        self.parsedProficientLocalesProperty = ""

    def isSuperUser(self):
        return self.containsRole(RoleConstants.SUPERUSER) #imported library in java code; find equivalent in pyhton
    def hasPrivilege(self, privilege):
        if (privilege == None) or (privilege == ""):
            return True
        if self.isSuperUser():
            return True
        tmproles = self.getAllRoles()
        for i in tmproles:
            if i.hasPrivilege(privilege):
                return True
        return False
    def hasRole(self, r, ignoreSuperUser=False):
        if ignoreSuperUser == False:
            if self.isSuperUser():
                return True
        if self.roles == None:
            return False
        tmproles = self.getAllRoles()

        logging.logger.debug("User #" + str(self.userId) + " has roles: " + str(tmproles))
        
        return self.containsRole(r)
    
    def containsRole(self, roleName):
        for role in self.getAllRoles():
            if role.getRole() == roleName:
                return True
        return False
    def getPrivileges(self):
        privileges = sets.Set() #not hashed; in JAVA it is
        tmproles = self.getAllRoles()
        for role in tmproles: #should it being frmo role.next or the first one?(JAVA code)
            privs = role.getPrivileges()
            if privs != None:
                for priv in privs:
                    privileges.add(priv)
        return privileges
    def getAllRoles(self):
        baseRoles = sets.Set()
        totalRoles = sets.Set()
        if self.getRoles() != None:
            for role in self.getRoles:
                baseRoles.add(role)
                totalRoles.add(role)
        logging.logger.debug("User's base roles: " + str(baseRoles))

        try:
            for r in baseRoles:
                for p in r.getAllParentoles():
                    totalRoles.add(p)
        except ClassCastException: #in JAVA, is there an exception like this in python.
                logging.logger.error("Error converting roles for user: " + str(self))
                logging.logger.error("baseRoles.class: " + str(baseRoles.getClass().getName()))
                logging.logger.error("baseRoles: " + str(baseRoles))
                i = iter(baseRoles)
                while next(i) != None:
                    logging.logger.error("baseRoles: '" + str(next(i)) + "'")
        return totalRoles
        
        #incomplete; there are more methods

########NEW FILE########
__FILENAME__ = settings
"""
Django settings for conf project.  
For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(__file__)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '!$e(y9&5ol=#s7wex!xhv=f&5f2@ufjez3ee9kdifw=41p_+%*'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates/'),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'conf',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'urls'

WSGI_APPLICATION = 'wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from django.conf.urls.static import static
from django.conf import settings

from conf import views

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'conf.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),

    url(r'^accounts/login/$', 'django.contrib.auth.views.login'),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout_then_login'),
    url(r'^accounts/profile/$', views.profile_view),

    url(r'^register$', views.register_account),

    url(r'^index$', views.index),
    url(r'^$', views.index),
    url(r'^submit$', views.submit_view),
    url(r'^paper$', views.paper_view),
    url(r'^submit_review$', views.submit_review_view),
    url(r'^submit_comment$', views.submit_comment_view),
    url(r'^assign_reviews$', views.assign_reviews_view),
    url(r'^search$', views.search_view),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for conf project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = PathVars
import JeevesLib
import fast.AST

class VarSetting:
  def __init__(self, var, val):
    self.var = var
    self.val = val
  def __eq__(self, other):
    return self.var is other.var and self.val == other.val
  def __str__(self):
    return "(%s, %s)" % (self.var.name, self.val)

# TODO: Define your path variable environment, as well as manipulations, here.
class PathVars:
  def __init__(self):
    self.conditions = []

  def push(self, var, value):
    assert type(var) == fast.AST.Var
    assert type(value) == bool
    if VarSetting(var, not value) in self.conditions:
      raise Exception("Path condition for '%s' already set to '%s'" % (var, not value))
    self.conditions.append(VarSetting(var, value))

  def pop(self):
    self.conditions.pop()

  def hasPosVar(self, var):
    return VarSetting(var, True) in self.conditions

  def hasNegVar(self, var):
    return VarSetting(var, False) in self.conditions

  def getPathFormula(self):
    c2 = [(vs.var if vs.val else fast.AST.Not(vs.var)) for vs in self.conditions]
    return reduce(fast.AST.And, c2, fast.AST.Constant(True))

  def getEnv(self):
    return {vs.var.name : vs.val for vs in self.conditions}

########NEW FILE########
__FILENAME__ = PolicyEnv
import JeevesLib

import fast.AST
from collections import defaultdict
from eval.Eval import partialEval
from fast.AST import FExpr

from smt.Z3 import Z3

class SolverState:
    def __init__(self, policies, ctxt):
        self.solver = Z3()
        self.result = {}
        self.ctxt = ctxt

        self.policies = policies # NOT a copy
        self.policies_index = 0

    def concretizeExp(self, f, pathenv):
        f = fast.AST.fexpr_cast(f)

        while self.policies_index < len(self.policies):
            label, policy = self.policies[self.policies_index]
            self.policies_index += 1

            predicate = policy(self.ctxt) #predicate should be True if label can be HIGH
            predicate_vars = predicate.vars()
            constraint = partialEval(fast.AST.Implies(label, predicate), pathenv)

            if constraint.type != bool:
                raise ValueError("constraints must be bools")
            self.solver.boolExprAssert(constraint)

        if not self.solver.check():
            raise UnsatisfiableException("Constraints not satisfiable")

        vars_needed = f.vars()
        for var in vars_needed:
            if var not in self.result:
                self.solver.push()
                self.solver.boolExprAssert(var)
                if self.solver.isSatisfiable():
                    self.result[var] = True
                else:
                    self.solver.pop()
                    self.solver.boolExprAssert(fast.AST.Not(var))
                    self.result[var] = False
        
        assert self.solver.check()

        return f.eval(self.result)

class PolicyEnv:
  def __init__(self):
    self.labels = []
    self.policies = []

  def mkLabel(self, name="", uniquify=True):
    label = fast.AST.Var(name, uniquify)
    self.labels.append(label)
    return label

  # policy is a function from context to bool which returns true
  # if the label is allowed to be HIGH
  def restrict(self, label, policy, use_empty_env=False):
    pcFormula = fast.AST.Constant(True) if use_empty_env else JeevesLib.jeevesState.pathenv.getPathFormula()
    self.policies.append((label, lambda ctxt :
      fast.AST.Implies(
        pcFormula,
        fast.AST.fexpr_cast(policy(ctxt)),
      )
    ))

  def getNewSolverState(self, ctxt):
    return SolverState(self.policies, ctxt)

  def concretizeExp(self, ctxt, f, pathenv):
    solver_state = self.getNewSolverState(ctxt)
    return solver_state.concretizeExp(f, pathenv)

  """
  # Takes a context and an expression
  def concretizeExp(self, ctxt, f, pathenv):
    f = fast.AST.fexpr_cast(f)
    dependencies = defaultdict(set)
    constraints = []
    # First, find all all the dependencies between labels
    # and add Not(predicate) ==> label == LOW conditions
    for label, policy in self.policies:
      predicate = policy(ctxt) #predicate should be True if label can be HIGH
      predicate_vars = predicate.vars()
      dependencies[label] |= predicate_vars
      constraints.append(partialEval(fast.AST.Implies(label, predicate), pathenv))

    # NOTE(TJH): wtf? commenting this out to make stuff work
    # If a depends on b, then we want (b == Low ==> a == Low)
    #for (label, label_deps) in dependencies.iteritems():
    #  for label_dep in label_deps:
    #    constraints.append(fast.AST.Implies(label, label_dep))

    thevars = f.vars()
    env = smt.SMT.solve(constraints, self.labels[::-1], thevars)
    ev = f.eval(env)

    #print 'env is', {v.name:val for v, val in env.iteritems()}, 'ev is', ev
    return ev
  """

########NEW FILE########
__FILENAME__ = VarEnv
class VarEnv:
  def __init__(self):
    pass

########NEW FILE########
__FILENAME__ = WritePolicyEnv
import JeevesLib

# import fast.AST
# from collections import defaultdict

class WritePolicyEnv:
  def __init__(self):
    self.writers = {}

  def mapPrimaryContext(self, ivar, ctxt):
    self.writers[ivar] = ctxt

  # This function associates a new set of write policies with a label.
  def addWritePolicy(self, label, policy, newWriter):
    # If the label is associated with a writer, then associate it with the
    # new write policies.
    if self.writers.has_key(label):
      ictxt = self.writers[label]

      # Make a new label mapped to the same writer.
      newLabel = JeevesLib.mkLabel(label.name)
      self.mapPrimaryContext(newLabel, ictxt)

      # Associate the new policies with this new label.
      JeevesLib.restrict(newLabel
        , lambda oc:
            JeevesLib.jand(lambda: label
              , lambda: JeevesLib.jand(
                  lambda: policy(ictxt)(oc)
                , lambda: policy(newWriter)(oc))))
      return newLabel
    # Otherwise return the label as is.
    else:
      return label

########NEW FILE########
__FILENAME__ = Eval
'''
NOTE(JY): In Transformer.scala, we essentially do a bunch of weird stuff to
get the equivalent of type classes for overloading. I don't think we have to do
that in Python.
'''

from fast.AST import *

def partialEval(f, env={}, unassignedOkay=False):
  if isinstance(f, BinaryExpr):
    left = partialEval(f.left, env, unassignedOkay)
    right = partialEval(f.right, env, unassignedOkay)
    return facetJoin(left, right, f.opr)
  elif isinstance(f, UnaryExpr):
    sub = partialEval(f.sub, env, unassignedOkay)
    return facetApply(sub, f.opr)
  elif isinstance(f, Constant):
    return f
  elif isinstance(f, Facet):
    if f.cond.name in env:
      return partialEval(f.thn, env, unassignedOkay) if env[f.cond.name] else partialEval(f.els, env, unassignedOkay)
    else:
      true_env = dict(env)
      true_env[f.cond.name] = True
      false_env = dict(env)
      false_env[f.cond.name] = False
      return create_facet(f.cond, partialEval(f.thn, true_env, unassignedOkay),
                           partialEval(f.els, false_env, unassignedOkay))
  elif isinstance(f, Var):
    if f.name in env:
      return Constant(env[f.name])
    else:
      return Facet(f, Constant(True), Constant(False))
  elif isinstance(f, FObject):
    return f
  elif isinstance(f, Unassigned):
   if unassignedOkay:
     return f
   else:
     raise f.getException()
  else:
    raise TypeError("partialEval does not support type %s" % f.__class__.__name__)

def create_facet(cond, left, right):
  if isinstance(left, Constant) and isinstance(right, Constant) and left.v == right.v:
    return left
  if isinstance(left, FObject) and isinstance(right, FObject) and left.v is right.v:
    return left
  return Facet(cond, left, right)

def facetApply(f, opr):
  if isinstance(f, Facet):
    return create_facet(f.cond, facetApply(f.thn, opr), facetApply(f.els, opr))
  elif isinstance(f, Constant):
    return Constant(opr(f.v))
  elif isinstance(f, FObject):
    return FObject(opr(f.v))

'''
This function should combine two 

NOTE(JY): We should just be able to use the universal Facet constructor
instead of the weird stuff we were doing before... You may need to change
things to get it to work though!
'''
def facetJoin(f0, f1, opr):
  if isinstance(f0, Facet):
    thn = facetJoin(f0.thn, f1, opr)
    els = facetJoin(f0.els, f1, opr)
    return create_facet(f0.cond, thn, els)
  elif isinstance(f1, Facet):
    thn = facetJoin(f0, f1.thn, opr)
    els = facetJoin(f0, f1.els, opr)
    return create_facet(f1.cond, thn, els)
  else:
    return Constant(opr(f0.v, f1.v))

########NEW FILE########
__FILENAME__ = AST
'''
This defines the abstract syntax tree for sensitive expressions.

Note(JY): An interesting thing is that we no longer need to define polymorphism
in types explicitly. We might be able to have a much cleaner implementation than
the Scala one!
'''
from abc import ABCMeta, abstractmethod
import operator
import z3
import JeevesLib
import traceback

import env.VarEnv
import env.PolicyEnv
import env.PathVars
import env.WritePolicyEnv
import threading
from collections import defaultdict

class JeevesState:
  def __init__(self):
    pass

  def init(self):
    self._varenv = defaultdict(env.VarEnv.VarEnv)
    self._pathenv = defaultdict(env.PathVars.PathVars)
    self._policyenv = defaultdict(env.PolicyEnv.PolicyEnv)
    self._writeenv = defaultdict(env.WritePolicyEnv.WritePolicyEnv)
    self._all_labels = defaultdict(dict)

  @property
  def varenv(self):
    return self._varenv[threading.current_thread()]
  @property
  def pathenv(self):
    return self._pathenv[threading.current_thread()]
  @property
  def policyenv(self):
    return self._policyenv[threading.current_thread()]
  @property
  def writeenv(self):
    return self._writeenv[threading.current_thread()]
  @property
  def all_labels(self):
    return self._all_labels[threading.current_thread()]

jeevesState = JeevesState()

'''
Abstract class for sensitive expressions.
'''
class FExpr:
  __metaclass__ = ABCMeta
  
  @abstractmethod
  def vars(self):
    return NotImplemented

  # TODO: Need to figure out a way to thread the environment through eval so
  # we don't have to pass the argument explicitly. We also want to make sure
  # that we're using the correct environment though... Do we have to use some
  # sort of global? :(
  # TJH: going to just assume it's a global for now, so we don't have to
  # pass it through
  @abstractmethod
  def eval(self, env):
    return NotImplemented

  @abstractmethod
  def z3Node(self):
    return NotImplemented

  @abstractmethod
  def getChildren(self):
    return NotImplemented

  # Return a version of yourself with the write-associated labels remapped to
  # point to the new policy in addition to the previous policies.
  @abstractmethod
  def remapLabels(self, policy, writer):
    return NotImplemented

  def prettyPrint(self, indent=""):
    return "%s%s\n%s" % (indent, type(self).__name__,
      "\n".join(child.prettyPrint(indent + "  ")
                for child in self.getChildren()))

  '''
  Sensitive Boolean expressions.
  NOTE(JY): I'm making the change Formula-> BoolExpr so that everything matches
  better.
  '''

  def __eq__(l, r):
    return Eq(l, fexpr_cast(r))

  def __ne__(l, r):
    return Not(Eq(l, fexpr_cast(r)))
    
  # The & operator
  def __and__(l, r):
    return And(l, fexpr_cast(r))
  def __rand__(r, l):
    return And(fexpr_cast(l), r)

  # The | operator
  def __or__(l, r):
    return Or(l, fexpr_cast(r))
  def __ror__(r, l):
    return Or(fexpr_cast(l), r)

  #def constant(v): BoolVal(v)
  #def default(): return NotImplemented
  ## TODO: Make this infix?
  #def implies(self, other): Not(self) or other
  #def iff(self, other): self == other
  #def facet(self, thn, els): Facet(self, thn, els)

  '''
  Integer expressions.
  '''
  def __add__(l, r):
    return Add(l, fexpr_cast(r))
  def __radd__(r, l):
    return Add(fexpr_cast(l), r)

  def __sub__(l, r):
    return Sub(l, fexpr_cast(r))
  def __rsub__(r, l):
    return Sub(fexpr_cast(l), r)

  def __mul__(l, r):
    return Mult(l, fexpr_cast(r))
  def __rmul__(r, l):
    return Mult(fexpr_cast(l), r)

  def __div__(l, r):
    return Div(l, fexpr_cast(r))
  def __rdiv__(r, l):
    return Div(fexpr_cast(l), r)

  def __mod__(l, r):
    return Mod(l, fexpr_cast(r))
  def __rmod__(r, l):
    return Mod(fexpr_cast(l), r)

  def __abs__(v):
    if isinstance(v, FExpr):
      return JeevesLib.jif(v > 0, lambda:v, lambda:0 - v)
    return abs(v)

  # TODO bitwise operations? do we care?

  def __lt__(l, r):
    return Lt(l, fexpr_cast(r))

  def __gt__(l, r):
    return Gt(l, fexpr_cast(r))

  def __le__(l, r):
    return LtE(l, fexpr_cast(r))

  def __ge__(l, r):
    return GtE(l, fexpr_cast(r))

class CannotEvalException(Exception):
  pass

def get_var_by_name(var_name):
  v = Var()
  v.name = var_name
  return v

class Var(FExpr):
  counter = 0

  def __init__(self, name=None, uniquify=True):
    if name:
      if uniquify:
        self.name = "v%d_%s" % (Var.counter, name)
      else:
        self.name = name
    else:
      self.name = "v%d" % Var.counter
    self.type = bool
    Var.counter += 1

  def eval(self, env):
    try:
      return env[self]
    except IndexError:
      raise CannotEvalException("Variable %s is not in path environment" % self)

  def remapLabels(self, policy, writer):
    return self

  def __str__(self):
    return self.name

  def vars(self):
    return {self}

  def z3Node(self):
    return z3.Bool(self.name)

  def getChildren(self):
    return []

  def prettyPrint(self, indent=""):
    return indent + self.name

# helper methods for faceted __setattr__
def get_objs_in_faceted_obj(f, d, env):
  if isinstance(f, Facet):
    if f.cond.name in env:
      if env[f.cond.name]:
        get_objs_in_faceted_obj(f.thn, d, env)
      else:
        get_objs_in_faceted_obj(f.els, d, env)
    else:
      get_objs_in_faceted_obj(f.thn, d, env)
      get_objs_in_faceted_obj(f.els, d, env)
  elif isinstance(f, FObject):
    d[id(f.v)] = f.v
  else:
    raise TypeError("wow such error: attribute access for non-object type; %s"
            % f.__class__.__name__)

def replace_obj_attributes(f, obj, oldvalue, newvalue, env):
  if isinstance(f, Facet):
    if f.cond.name in env:
      if env[f.cond.name]:
        return replace_obj_attributes(f.thn, obj, oldvalue, newvalue, env)
      else:
        return replace_obj_attributes(f.els, obj, oldvalue, newvalue, env)
    else:
      return Facet(f.cond,
        replace_obj_attributes(f.thn, obj, oldvalue, newvalue, env),
        replace_obj_attributes(f.els, obj, oldvalue, newvalue, env))
  elif f.v is obj:
    return newvalue
  else:
    return oldvalue

'''
Facets.
NOTE(JY): I think we don't have to have specialized facets anymore because we
don't have to deal with such a strict type system. One reason we might not be
able to do this is if we have to specialize execution of facets by checking
the type of the facet...
'''
class Facet(FExpr):
  def __init__(self, cond, thn, els):
    assert isinstance(cond, Var)

    self.__dict__['cond'] = cond
    self.__dict__['thn'] = fexpr_cast(thn)
    self.__dict__['els'] = fexpr_cast(els)

    # Note (TJH): idiomatic python does lots of automatic casts to bools,
    # especially to check if an integer is nonzero, for instance. We might
    # want to consider casting
    if self.cond.type != bool:
        raise TypeError("Condition on Facet should be a bool but is type %s."
                            % self.cond.type.__name__)

    # Note (TJH): Ordinary Python would of course allow these types to be
    # distinct, but that sounds pretty annoying to support on our end.
    # TODO: Unassigned makes things super-awkward, we need to figure that out.
    # For now, just ignore them.
    #if (self.thn.type != None and self.els.type != None and
    #        self.thn.type != self.els.type):
    #    raise TypeError("Condition on both sides of a Facet must have the "
    #                    "same type, they are %s and %s."
    #                    % (self.thn.type.__name__, self.els.type.__name__))

    self.__dict__['type'] = self.thn.type or self.els.type

  def eval(self, env):
    return self.thn.eval(env) if self.cond.eval(env) else self.els.eval(env)

  def vars(self):
    return self.cond.vars().union(self.thn.vars()).union(self.els.vars())

  def z3Node(self):
    return z3.If(self.cond.z3Node(), self.thn.z3Node(), self.els.z3Node())

  def getChildren(self):
    return [self.cond, self.thn, self.els]

  def remapLabels(self, policy, writer):
    if isinstance(self.cond, Var):
      newCond = jeevesState.writeenv.addWritePolicy(
                  self.cond, policy, writer)
    else:
      newCond = self.cond.remapLabels(policy, writer)
    return Facet(newCond
      , self.thn.remapLabels(policy, writer)
      , self.els.remapLabels(policy, writer))

  def prettyPrint(self, indent=""):
    return "< " + self.cond.prettyPrint() + " ? " + self.thn.prettyPrint() + " : " + self.els.prettyPrint() + " >"
  def __str__(self):
    return self.prettyPrint()


  def __call__(self, *args, **kw):
    return JeevesLib.jif(self.cond,
        lambda:self.thn(*args, **kw), lambda:self.els(*args, **kw))

  # called whenever an attribute that does not exist is accessed
  def __getattr__(self, attribute):
    if JeevesLib.jeevesState.pathenv.hasPosVar(self.cond):
      return getattr(self.thn, attribute)
    elif JeevesLib.jeevesState.pathenv.hasNegVar(self.cond):
      return getattr(self.els, attribute)
    return Facet(self.cond,
      getattr(self.thn, attribute),
      getattr(self.els, attribute))

  def __setattr__(self, attribute, value):
    if attribute in self.__dict__:
      self.__dict__[attribute] = value
    else:
      env = jeevesState.pathenv.getEnv()
      value = fexpr_cast(value)
      objs = {}
      get_objs_in_faceted_obj(self, objs, env)
      for _, obj in objs.iteritems():
        if hasattr(obj, attribute):
          old_val = getattr(obj, attribute)
        else:
          old_val = Unassigned("attribute '%s'" % attribute)
        t = replace_obj_attributes(self, obj, old_val, value, env)
        setattr(obj, attribute, t)

  def __getitem__(self, attribute):
    if JeevesLib.jeevesState.pathenv.hasPosVar(self.cond):
      return self.thn[attribute]
    elif JeevesLib.jeevesState.pathenv.hasNegVar(self.cond):
      return self.els[attribute]
    return Facet(self.cond, self.thn[attribute], self.els[attribute])

  def __setitem__(self, attribute, value):
    env = jeevesState.pathenv.getEnv()
    value = fexpr_cast(value)
    objs = {}
    get_objs_in_faceted_obj(self, objs, env)
    for _, obj in objs.iteritems():
      t = replace_obj_attributes(self, obj, obj[attribute], value, env)
      obj[attribute] = t

  def __eq__(self, other):
    other = fexpr_cast(other)
    if self.type == object or other.type == object:
      return JeevesLib.jif(self.cond, lambda : self.thn == other,
                                                   lambda : self.els == other)
    else:
      return Eq(self, other)
  def __ne__(self, other):
    other = fexpr_cast(other)
    if self.type == object or other.type == object:
      return JeevesLib.jif(self.cond, lambda : self.thn != other,
                                                   lambda : self.els != other)
    else:
      return Not(Eq(self, other))
  def __lt__(self, other):
    other = fexpr_cast(other)
    if self.type == object or other.type == object:
      return JeevesLib.jif(self.cond, lambda : self.thn < other,
                                                   lambda : self.els < other)
    else:
      return Lt(self, other)
  def __gt__(self, other):
    other = fexpr_cast(other)
    if self.type == object or other.type == object:
      return JeevesLib.jif(self.cond, lambda : self.thn > other,
                                                   lambda : self.els > other)
    else:
      return Gt(self, other)
  def __le__(self, other):
    other = fexpr_cast(other)
    if self.type == object or other.type == object:
      return JeevesLib.jif(self.cond, lambda : self.thn <= other,
                                                   lambda : self.els <= other)
    else:
      return LtE(self, other)
  def __ge__(self, other):
    other = fexpr_cast(other)
    if self.type == object or other.type == object:
      return JeevesLib.jif(self.cond, lambda : self.thn >= other,
                                                   lambda : self.els >= other)
    else:
      return GtE(self, other)

  def __len__(self):
    if self.type == object:
      return JeevesLib.jif(self.cond,
                lambda : self.thn.__len__(),
                lambda : self.els.__len__())
    else:
      raise TypeError("cannot take len of non-object; type %s" % self.type.__name__)

class Constant(FExpr):
  def __init__(self, v):
    assert not isinstance(v, FExpr)
    self.v = v
    self.type = type(v)

  def eval(self, env):
    return self.v

  def vars(self):
    return set()

  def z3Node(self):
    return self.v

  def getChildren(self):
    return []

  def remapLabels(self, policy, writer):
    return self

  def prettyPrint(self, indent=""):
    return indent + "const:" + repr(self.v)

  def __call__(self, *args, **kw):
    return self.v(*args, **kw)

'''
Binary expressions.
'''
class BinaryExpr(FExpr):
  def __init__(self, left, right):
    self.left = left
    self.right = right
    self.type = self.ret_type

  def vars(self):
    return self.left.vars().union(self.right.vars())

  def getChildren(self):
    return [self.left, self.right]

class UnaryExpr(FExpr):
  def __init__(self, sub):
    self.sub = sub
    self.type = self.ret_type

  def vars(self):
    return self.sub.vars()

  def getChildren(self):
    return [self.sub]

'''
Operators.
'''
class Add(BinaryExpr):
  opr = staticmethod(operator.add)
  ret_type = int
  def eval(self, env):
    return self.left.eval(env) + self.right.eval(env)
  def z3Node(self):
    return self.left.z3Node() + self.right.z3Node()
  def remapLabels(self, policy, writer):
    return Add(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

class Sub(BinaryExpr):
  opr = staticmethod(operator.sub)
  ret_type = int
  def eval(self, env):
    return self.left.eval(env) - self.right.eval(env)
  def z3Node(self):
    return self.left.z3Node() - self.right.z3Node()
  def remapLabels(self, policy, writer):
    return Sub(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

class Mult(BinaryExpr):
  opr = staticmethod(operator.mul)
  ret_type = int
  def eval(self, env):
    return self.left.eval(env) * self.right.eval(env)
  def z3Node(self):
    return self.left.z3Node() * self.right.z3Node()
  def remapLabels(self, policy, writer):
    return Mult(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

class Div(BinaryExpr):
  opr = staticmethod(operator.div)
  ret_type = int
  def eval(self, env):
    return self.left.eval(env) / self.right.eval(env)
  def z3Node(self):
    return NotImplemented
  def remapLabels(self, policy, writer):
    return Div(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

class Mod(BinaryExpr):
  opr = staticmethod(operator.mod)
  ret_type = int
  def eval(self, env):
    return self.left.eval(env) % self.right.eval(env)
  def z3Node(self):
    return NotImplemented
  def remapLabels(self, policy, writer):
    return Mod(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

# Not sure if bitwise operations are supported by Z3?
class BitAnd(BinaryExpr):
  opr = staticmethod(operator.and_)
  ret_type = int
  def eval(self, env):
    return self.left.eval(env) & self.right.eval(env)
  def z3Node(self):
    return NotImplemented
  def remapLabels(self, policy, writer):
    return BitAnd(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

class BitOr(BinaryExpr):
  opr = staticmethod(operator.or_)
  ret_type = int
  def eval(self, env):
    return self.left.eval(env) | self.right.eval(env)
  def z3Node(self):
    return NotImplemented
  def remapLabels(self, policy, writer):
    return BitOr(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

class LShift(BinaryExpr):
  opr = staticmethod(operator.ilshift)
  ret_type = int
  def eval(self, env):
    return self.left.eval(env) << self.right.eval(env)
  def z3Node(self):
    return NotImplemented
  def remapLabels(self, policy, writer):
    return LShift(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

class RShift(BinaryExpr):
  opr = staticmethod(operator.irshift)
  ret_type = int
  def eval(self, env):
    return self.left.eval(env) >> self.right.eval(env)
  def z3Node(self):
    return NotImplemented
  def remapLabels(self, policy, writer):
    return RShift(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

# Boolean operations

class And(BinaryExpr):
  opr = staticmethod(operator.and_)
  ret_type = bool
  def eval(self, env):
    return self.left.eval(env) and self.right.eval(env)
  def z3Node(self):
    return z3.And(self.left.z3Node(), self.right.z3Node())
  def remapLabels(self, policy, writer):
    return And(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

class Or(BinaryExpr):
  opr = staticmethod(operator.or_)
  ret_type = bool
  def eval(self, env):
    return self.left.eval(env) or self.right.eval(env)
  def z3Node(self):
    return z3.Or(self.left.z3Node(), self.right.z3Node())
  def remapLabels(self, policy, writer):
    return Or(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

class Not(UnaryExpr):
  opr = staticmethod(operator.not_)
  ret_type = bool
  def eval(self, env):
    return not self.sub.eval(env)
  def z3Node(self):
    return z3.Not(self.sub.z3Node())
  def remapLabels(self, policy, writer):
    return Not(self.sub.remapLabels(policy, writer))

# Doesn't correspond to a Python operator but is useful
class Implies(BinaryExpr):
  opr = staticmethod(lambda x, y : (not x) or y)
  ret_type = bool
  def eval(self, env):
    return (not self.left.eval(env)) or self.right.eval(env)
  def z3Node(self):
    return z3.Implies(self.left.z3Node(), self.right.z3Node())
  def remapLabels(self, policy, writer):
    return Implies(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

# Comparison operations

class Eq(BinaryExpr):
  opr = staticmethod(operator.eq)
  ret_type = bool
  def eval(self, env):
    return self.left.eval(env) == self.right.eval(env)
  def z3Node(self):
    return self.left.z3Node() == self.right.z3Node()
  def remapLabels(self, policy, writer):
    return Eq(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

class Lt(BinaryExpr):
  opr = staticmethod(operator.lt)
  ret_type = bool
  def eval(self, env):
    return self.left.eval(env) < self.right.eval(env)
  def z3Node(self):
    return self.left.z3Node() < self.right.z3Node()
  def remapLabels(self, policy, writer):
    return Lt(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

class LtE(BinaryExpr):
  opr = staticmethod(operator.le)
  ret_type = bool
  def eval(self, env):
    return self.left.eval(env) <= self.right.eval(env)
  def z3Node(self):
    return self.left.z3Node() <= self.right.z3Node()
  def remapLabels(self, policy, writer):
    return LtE(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

class Gt(BinaryExpr):
  opr = staticmethod(operator.gt)
  ret_type = bool
  def eval(self, env):
    return self.left.eval(env) > self.right.eval(env)
  def z3Node(self):
    return self.left.z3Node() > self.right.z3Node()
  def remapLabels(self, policy, writer):
    return Gt(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

class GtE(BinaryExpr):
  opr = staticmethod(operator.ge)
  ret_type = bool
  def eval(self, env):
    return self.left.eval(env) >= self.right.eval(env)
  def z3Node(self):
    return self.left.z3Node() >= self.right.z3Node()
  def remapLabels(self, policy, writer):
    return GtE(
        self.left.remapLabels(policy, writer)
      , self.right.remapLabels(policy, writer))

class Unassigned(FExpr):
  def __init__(self, thing_not_found):
    self.type = None
    self.thing_not_found = thing_not_found
  def eval(self, env):
    raise self.getException()
  def z3Node(self):
    pass #TODO ?? what goes here
  def getChildren(self):
    return []
  def remapLabels(self, policy):
    return self
  def vars(self):
    return set()
  def remapLabels(self, policy, writer):
    return self
  def getException(self):
    return Exception("wow such error: %s does not exist." % (self.thing_not_found,))
  def __call__(self, *args, **kwargs):
    raise self.getException()
  def __getattr__(self, attr):
    #raise self.getException()
    return Unassigned(self.thing_not_found)

# TODO(TJH): figure out the correct implementation of this
def is_obj(o):
  return isinstance(o, list) or isinstance(o, tuple) or hasattr(o, '__dict__') or o is None

# helper method
def fexpr_cast(a):
  if isinstance(a, FExpr):
    return a
  elif isinstance(a, list):
    return FObject(JeevesLib.JList(a))
  elif is_obj(a):
    return FObject(a)
  else:
    return Constant(a)

class FObject(FExpr):
  def __init__(self, v):
    assert not isinstance(v, JeevesLib.Namespace)
    assert not isinstance(v, FObject)
    self.__dict__['v'] = v
    self.__dict__['type'] = object

  def eval(self, env):
    if isinstance(self.v, JeevesLib.JList):
      return self.v.l.eval(env)
    elif isinstance(self.v, JeevesLib.JList2):
      return self.v.eval(env)
    else:
      return self.v

  def vars(self):
    if isinstance(self.v, JeevesLib.JList):
      return self.v.l.vars()
    elif isinstance(self.v, JeevesLib.JList2):
      return self.v.vars()
    else:
      return set()

  def z3Node(self):
    return id(self)

  def getChildren(self):
    return []

  # TODO: Make sure this is right...
  def remapLabels(self, policy, writer):
    if isinstance(self.v, FExpr):
      return FObject(self.v.remapLabels(policy, writer))
    else:
      return self

  def __call__(self, *args, **kw):
    return self.v.__call__(*args, **kw)

  # called whenever an attribute that does not exist is accessed
  def __getattr__(self, attribute):
    if hasattr(self.v, attribute):
      return getattr(self.v, attribute)
    else:
      return Unassigned("attribute '%s'" % attribute)

  def __setattr__(self, attribute, val):
    if attribute in self.__dict__:
      self.__dict__[attribute] = val
    else:
      setattr(self.v, attribute, val)

  def __getitem__(self, item):
    try:
      return self.v[item]
    except (KeyError, IndexError, TypeError):
      return Unassigned("item '%s'" % item)

  def __setitem__(self, item, val):
    self.v[item] = val

  def __len__(self):
    return self.v.__len__()

  def __eq__(self, other): 
    try:
      f = getattr(self.v, '__eq__')
    except AttributeError:
      return Eq(self, fexpr_cast(other))
    return f(other)

  def __ne__(self, other):
    try:
      f = getattr(self.v, '__ne__')
    except AttributeError:
      return Not(Eq(self, fexpr_cast(other)))
    return f(other)

  def __lt__(self, other):
    try:
      f = getattr(self.v, '__lt__')
    except AttributeError:
      return Lt(self, fexpr_cast(other))
    return f(other)

  def __gt__(self, other):
    try:
      f = getattr(self.v, '__gt__')
    except AttributeError:
      return Gt(self, fexpr_cast(other))
    return f(other)

  def __le__(self, other):
    try:
      f = getattr(self.v, '__le__')
    except AttributeError:
      return LtE(self, fexpr_cast(other))
    return f(other)

  def __ge__(self, other):
    try:
      f = getattr(self.v, '__ge__')
    except AttributeError:
      return GtE(self, fexpr_cast(other))
    return f(other)

  def prettyPrint(self, indent=""):
    return 'FObject:%s' % str(self.v)

"""
  def __and__(l, r):
  def __rand__(r, l):
  def __or__(l, r):
  def __ror__(r, l):
  def __add__(l, r):
  def __radd__(r, l):
  def __sub__(l, r):
  def __rsub__(r, l):
  def __mul__(l, r):
  def __rmul__(r, l):
  def __div__(l, r):
  def __rdiv__(r, l):
  def __mod__(l, r):
  def __rmod__(r, l):
"""

########NEW FILE########
__FILENAME__ = ProtectedRef
# NOTE(JY): Importing JeevesLib for the write policy environment instance.
# Is there a better way to do this?
from macropy.case_classes import macros, enum
import JeevesLib
from AST import And, Facet, FExpr, FObject
from eval.Eval import partialEval

@enum
class UpdateResult:
  Success, Unknown, Failure

class Undefined(Exception):
  pass
class PolicyError(Exception):
  pass

@JeevesLib.supports_jeeves
class ProtectedRef:
  # TODO: Find nice ways of supplying defaults for inputWritePolicy and
  # outputWritePolicy?
  @JeevesLib.supports_jeeves
  def __init__(self, v, inputWP, outputWP, trackImplicit=True):
    self.v = v

    if isinstance(inputWP, FExpr):
      if isinstance(inputWP, FObject):
        self.inputWP = inputWP.v
      else:
        raise PolicyError("Input write policy cannot be faceted.")
    else:
      self.inputWP = inputWP
    
    if isinstance(outputWP, FExpr):
      if isinstance(outputWP, FObject):
        self.outputWP = outputWP.v
      else:
        raise PolicyError("Output write policy cannot be faceted.")
    else:
      self.outputWP = outputWP

    self.trackImplicit = trackImplicit

  @JeevesLib.supports_jeeves
  def applyInputWP(self, writer, writeCtxt):
    if self.inputWP:
      r = self.inputWP(self.v)(writer)
      if isinstance(r, FExpr):
        r = JeevesLib.concretize(writeCtxt, partialEval(r, JeevesLib.jeevesState.pathenv.getEnv()))
      if r:
        return UpdateResult.Success
      else:
        return UpdateResult.Failure
    else:
      return UpdateResult.Success

  # TODO: Crap. We can only do this if we don't mutate anything. We don't have
  # the static analyses right now to figure that out!
  '''
  @JeevesLib.supports_jeeves
  def applyOutputWP(self, writer):
    if self.outputWP:
      try:
        r = self.outputWP(self.v)(writer)(Undefined)
        if isinstance(r, FExpr):
          try:
            r = JeevesLib.evalToConcrete(r)
          except Exception:
            r = PartialEval(r)
        if r == True:
          return UpdateResult.Success
        elif r == False:
          return UpdateResult.Failure
        else:
          return UpdateResult.Unknown
      except Exception:
        return UpdateResult.Unknown
    else:
      return UpdateResult.Success
  '''

  @JeevesLib.supports_jeeves
  def addWritePolicy(self, label, writer):
    if self.outputWP:
      return JeevesLib.jeevesState.writeenv.addWritePolicy(label
        , self.outputWP(self.v), writer)
    else:
      return label

  # TODO: store the current writer with the Jeeves environment?
  @JeevesLib.supports_jeeves
  def update(self, writer, writeCtxt, vNew):
    # For each variable, make a copy of it and add policies.
    def mkFacetTree(pathvars, high, low):
      if pathvars:
        #(bv, isPos) = pathvars.pop()
        vs = pathvars.pop()
        bv = vs.var
        isPos = vs.val
        bvNew = self.addWritePolicy(bv, writer)
        
        lv = JeevesLib.mkLabel(bv.name)
        JeevesLib.jeevesState.writeenv.mapPrimaryContext(lv, writer)
        newFacet = mkFacetTree(pathvars, high, low)
        if isPos:
          JeevesLib.restrict(lv, lambda ic: lv)
          return Facet(bvNew, newFacet, low)
        else:
          JeevesLib.restrict(lv, lambda ic: not lv)
          return Facet(bvNew, low, newFacet)
      # If there are not path variables, then return the high facet.
      else:
        return high

    # First we try to apply the input write policy. If it for sure didn't work,
    # then we return the old value.
    if self.applyInputWP(writer, writeCtxt) == UpdateResult.Failure:
      return UpdateResult.Failure
    else:
      if not self.outputWP:
        self.v = vNew
        return UpdateResult.Success
      if self.outputWP:
        vOld = self.v
        if isinstance(vNew, FExpr):
          vNewRemapped = vNew.remapLabels(self.outputWP(vOld), writer)
        else:
          vNewRemapped = vNew
 
        # Create a new label and map it to the resulting confidentiality
        # policy in the confidentiality policy environment.
        wvar = JeevesLib.mkLabel() # TODO: Label this?
        JeevesLib.restrict(wvar, self.outputWP(vOld)(writer))

        # Create a faceted value < wvar ? vNew' : vOld >, where vNew' has
        # the write-associated labels remapped to take into account the new
        # writer. Add the path conditions.
        JeevesLib.jeevesState.pathenv.push(wvar, True)
        rPC = mkFacetTree(list(JeevesLib.jeevesState.pathenv.conditions)
                , vNewRemapped, vOld)
        JeevesLib.jeevesState.pathenv.pop()

        if self.trackImplicit:
          JeevesLib.jeevesState.writeenv.mapPrimaryContext(wvar, writer)

        self.v = rPC
        return UpdateResult.Unknown

########NEW FILE########
__FILENAME__ = JeevesModel
from django.db import models
from django.db.models.fields import IntegerField
from django.db.models.query import QuerySet
from django.db.models import Manager
from django.db.models import Field, CharField, ForeignKey
from django.db.models.loading import get_model
import django.db.models.fields.related

import JeevesLib
from JeevesLib import fexpr_cast
from eval.Eval import partialEval
from fast.AST import Facet, FObject, Unassigned, get_var_by_name, FExpr

import string
import random
import itertools

class JeevesQuerySet(QuerySet):
  @JeevesLib.supports_jeeves
  def get_jiter(self):
    self._fetch_all()

    def get_env(obj, fields, env):
      if hasattr(obj, "jeeves_vars"):
        vs = unserialize_vars(obj.jeeves_vars)
      else:
        vs = {}
      for var_name, value in vs.iteritems():
        if var_name in env and env[var_name] != value:
          return None
        env[var_name] = value
        acquire_label_by_name(self.model._meta.app_label, var_name)
      for field, subs in (fields.iteritems() if fields else []):
        if field and get_env(getattr(obj, field), subs, env) is None:
          return None
      return env

    results = []
    for obj in self._result_cache:
      env = get_env(obj, self.query.select_related, {})
      if env is not None:
        results.append((obj, env))
    return results

  def get(self, use_base_env=False, **kwargs):
    l = self.filter(**kwargs).get_jiter()
    if len(l) == 0:
      return None
    
    for (o, _) in l:
      if o.jeeves_id != l[0][0].jeeves_id:
        raise Exception("wow such error: get() found rows for more than one jeeves_id")

    cur = None
    for (o, conditions) in l:
      old = cur
      cur = FObject(o)
      for var_name, val in conditions.iteritems():
        if val:
          cur = Facet(acquire_label_by_name(self.model._meta.app_label, var_name), cur, old)
        else:
          cur = Facet(acquire_label_by_name(self.model._meta.app_label, var_name), old, cur)
    try:
      return partialEval(cur, {} if use_base_env else JeevesLib.jeevesState.pathenv.getEnv())
    except TypeError:
      raise Exception("wow such error: could not find a row for every condition")

  def filter(self, **kwargs):
    l = []
    for argname, _ in kwargs.iteritems():
      t = argname.split('__')
      if len(t) > 1:
        l.append("__".join(t[:-1]))
    if len(l) > 0:
      return super(JeevesQuerySet, self).filter(**kwargs).select_related(*l)
    else:
      return super(JeevesQuerySet, self).filter(**kwargs)

  @JeevesLib.supports_jeeves
  def all(self):
    t = JeevesLib.JList2([])
    env = JeevesLib.jeevesState.pathenv.getEnv()
    for val, cond in self.get_jiter():
      popcount = 0
      for vname, vval in cond.iteritems():
        if vname not in env:
          v = acquire_label_by_name(self.model._meta.app_label, vname)
          JeevesLib.jeevesState.pathenv.push(v, vval)
          popcount += 1
        elif env[vname] != vval:
          break
      else:
        t.append(val)
      for _ in xrange(popcount):
        JeevesLib.jeevesState.pathenv.pop()
    return t

  @JeevesLib.supports_jeeves
  def delete(self):
    # can obviously be optimized
    # TODO write tests for this
    for val, cond in self.get_jiter():
      popcount = 0
      for vname, vval in cond.iteritems():
        if vname not in JeevesLib.jeevesState.pathenv.getEnv():
          v = acquire_label_by_name(self.model._meta.app_label, vname)
          JeevesLib.jeevesState.pathenv.push(v, vval)
          popcount += 1
      val.delete()
      for _ in xrange(popcount):
        JeevesLib.jeevesState.pathenv.pop()


  @JeevesLib.supports_jeeves
  def exclude(self, **kwargs):
    raise NotImplementedError

  # methods that return a queryset subclass of the ordinary QuerySet
  # need to be overridden

  def values(self, *fields):
    raise NotImplementedError

  def values_list(self, *fields, **kwargs):
    raise NotImplementedError

  def dates(self, field_name, kind, order='ASC'):
    raise NotImplementedError

  def datetimes(self, field_name, kind, order='ASC', tzinfo=None):
    raise NotImplementedError

  def none(self):
    raise NotImplementedError

class JeevesManager(Manager):
  @JeevesLib.supports_jeeves
  def get_queryset(self):
    return (super(JeevesManager, self).get_queryset()
              ._clone(klass=JeevesQuerySet)
              .order_by('jeeves_id')
           )
  
  def all(self):
    return super(JeevesManager, self).all().all()

  @JeevesLib.supports_jeeves
  def create(self, **kw):
    m = self.model(**kw)
    m.save()
    return m

alphanum = string.digits + string.letters
sysrand = random.SystemRandom()
JEEVES_ID_LEN = 32
def get_random_jeeves_id():
  return "".join(alphanum[sysrand.randint(0, len(alphanum)-1)]
                    for i in xrange(JEEVES_ID_LEN))

# From python docs
def powerset(iterable):
  "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
  s = list(iterable)
  return itertools.chain.from_iterable(
        itertools.combinations(s, r) for r in range(len(s)+1))

def clone(old):
  new_kwargs = dict([(fld.name, getattr(old, fld.name)) for fld in old._meta.fields
            if not isinstance(fld, JeevesForeignKey)]);
  ans = old.__class__(**new_kwargs)
  for fld in old._meta.fields:
    if isinstance(fld, JeevesForeignKey):
      setattr(ans, fld.attname, getattr(old, fld.attname))
  return ans

def serialize_vars(e):
  return ';' + ''.join('%s=%d;' % (var_name, var_value)
                        for var_name, var_value in e.iteritems())

def unserialize_vars(s):
  t = s[1:].split(';')
  e = {}
  for u in t:
    if u != "":
      v = u.split('=')
      e[v[0]] = bool(int(v[1]))
  return e

def fullEval(val, env):
  p = partialEval(val, env)
  return p.v

def acquire_label_by_name(app_label, label_name):
  if JeevesLib.doesLabelExist(label_name):
    return JeevesLib.getLabel(label_name)
  else:
    label = JeevesLib.mkLabel(label_name, uniquify=False)
    model_name, field_name, jeeves_id = label_name.split('__')
    model = get_model(app_label, model_name)
    # TODO: optimization: most of the time this obj will be the one we are
    # already fetching
    obj = model.objects.get(use_base_env=True, jeeves_id=jeeves_id)
    restrictor = getattr(model, 'jeeves_restrict_' + field_name)
    JeevesLib.restrict(label, lambda ctxt : restrictor(obj, ctxt), True)
    return label
 
def get_one_differing_var(e1, e2):
  if len(e1) != len(e2):
    return None
  ans = None
  for v in e1:
    if v in e2:
      if e1[v] != e2[v]:
        if ans is None:
          ans = v
        else:
          return None
    else:
      return None
  return ans

def label_for(*field_names):
    def decorator(f):
        f._jeeves_label_for = field_names
        return f
    return decorator

#from django.db.models.base import ModelBase
#class JeevesModelBase(ModelBase):
#  def __new__(cls, name, bases, attrs):
#    obj = super(ModelBase, cls).__new__(cls, name, bases, attrs)

#    return obj

# Make a Jeeves Model that enhances the vanilla Django model with information
# about how labels work and that kind of thing. We'll also need to override
# some methods so that we can create records and make queries appropriately.

class JeevesModel(models.Model):
  def __init__(self, *args, **kw):
    self.jeeves_base_env = JeevesLib.jeevesState.pathenv.getEnv()
    super(JeevesModel, self).__init__(*args, **kw)

    self._jeeves_labels = {}
    field_names = [f.name for f in self._meta.concrete_fields]
    for attr in dir(self.__class__):
      if attr.startswith('jeeves_restrict_'):
        value = getattr(self.__class__, attr)
        label_name = attr[len('jeeves_restrict_'):]
        assert label_name not in self._jeeves_labels
        if hasattr(value, '_jeeves_label_for'):
          self._jeeves_labels[label_name] = value._jeeves_label_for
        else:
          assert label_name in field_names
          self._jeeves_labels[label_name] = (label_name,)

  def __setattr__(self, name, value):
    field_names = [field.name for field in self._meta.concrete_fields] if hasattr(self, '_meta') else []
    if name in field_names and name not in ('jeeves_vars', 'jeeves_id', 'id'):
      old_val = getattr(self, name) if hasattr(self, name) else \
                  Unassigned("attribute '%s' in %s" % (name, self.__class__.__name__))
      models.Model.__setattr__(self, name, JeevesLib.jassign(old_val, value, self.jeeves_base_env))
    else:
      models.Model.__setattr__(self, name, value)

  objects = JeevesManager()
  jeeves_id = CharField(max_length=JEEVES_ID_LEN, null=False)
  jeeves_vars = CharField(max_length=1024, null=False)

  @JeevesLib.supports_jeeves
  def do_delete(self, e):
    if len(e) == 0:
      delete_query = self.__class__._objects_ordinary.filter(jeeves_id=self.jeeves_id)
      delete_query.delete()
    else:
      filter_query = self.__class__._objects_ordinary.filter(jeeves_id=self.jeeves_id)
      objs = list(filter_query)
      for obj in objs:
        eobj = unserialize_vars(obj.jeeves_vars)
        if any(var_name in eobj and eobj[var_name] != var_value
               for var_name, var_value in e.iteritems()):
          continue
        if all(var_name in eobj and eobj[var_name] == var_value
               for var_name, var_value in e.iteritems()):
          super(JeevesModel, obj).delete()
          continue
        addon = ""
        for var_name, var_value in e.iteritems():
          if var_name not in eobj:
            new_obj = clone(obj)
            if addon != "":
              new_obj.id = None # so when we save a new row will be made
            new_obj.jeeves_vars += addon + '%s=%d;' % (var_name, not var_value)
            addon += '%s=%d;' % (var_name, var_value)
            super(JeevesModel, new_obj).save()

  @JeevesLib.supports_jeeves
  def acquire_label(self, field_name):
    label_name = '%s__%s__%s' % (self.__class__.__name__, field_name, self.jeeves_id)
    if JeevesLib.doesLabelExist(label_name):
      return JeevesLib.getLabel(label_name)
    else:
      label = JeevesLib.mkLabel(label_name, uniquify=False)
      restrictor = getattr(self, 'jeeves_restrict_' + field_name)
      JeevesLib.restrict(label, lambda ctxt : restrictor(self, ctxt), True)
      return label

  @JeevesLib.supports_jeeves
  def save(self, *args, **kw):
    if not self.jeeves_id:
      self.jeeves_id = get_random_jeeves_id()

    if kw.get("update_field", None) is not None:
      raise NotImplementedError("Partial saves not supported.")

    field_names = set()
    for field in self._meta.concrete_fields:
      if not field.primary_key and not hasattr(field, 'through'):
        field_names.add(field.attname)

    for label_name, field_name_list in self._jeeves_labels.iteritems():
      label = self.acquire_label(label_name)
      for field_name in field_name_list:
        public_field_value = getattr(self, field_name)
        private_field_value = getattr(self, 'jeeves_get_private_' + field_name)(self)
        faceted_field_value = partialEval(
          JeevesLib.mkSensitive(label, public_field_value, private_field_value),
          JeevesLib.jeevesState.pathenv.getEnv()
        )
        setattr(self, field_name, faceted_field_value)

    all_vars = []
    d = {}
    env = JeevesLib.jeevesState.pathenv.getEnv()
    for field_name in field_names:
      value = getattr(self, field_name)
      f = partialEval(fexpr_cast(value), env)
      all_vars.extend(v.name for v in f.vars())
      d[field_name] = f
    all_vars = list(set(all_vars))

    for p in powerset(all_vars):
      true_vars = list(p)
      false_vars = list(set(all_vars).difference(p))
      e = dict(env)
      e.update({tv : True for tv in true_vars})
      e.update({fv : False for fv in false_vars})

      self.do_delete(e)

      klass = self.__class__
      obj_to_save = klass(**{
        field_name : fullEval(field_value, e)
        for field_name, field_value in d.iteritems()
      })

      all_jid_objs = list(klass._objects_ordinary.filter(jeeves_id=obj_to_save.jeeves_id).all())
      all_relevant_objs = [obj for obj in all_jid_objs if
            all(field_name == 'jeeves_vars' or 
                getattr(obj_to_save, field_name) == getattr(obj, field_name)
                for field_name in d)]
      while True:
        # check if we can collapse
        # if we can, repeat; otherwise, exit
        for i in xrange(len(all_relevant_objs)):
          other_obj = all_relevant_objs[i]
          diff_var = get_one_differing_var(e, unserialize_vars(other_obj.jeeves_vars))
          if diff_var is not None:
            super(JeevesModel, other_obj).delete()
            del e[diff_var]
            break
        else:
          break

      obj_to_save.jeeves_vars = serialize_vars(e)
      super(JeevesModel, obj_to_save).save(*args, **kw)

  @JeevesLib.supports_jeeves
  def delete(self, *args, **kw):
    if self.jeeves_id is None:
      return

    field_names = set()
    for field in self._meta.concrete_fields:
      if not field.primary_key and not hasattr(field, 'through'):
        field_names.add(field.attname)

    all_vars = []
    d = {}
    env = JeevesLib.jeevesState.pathenv.getEnv()
    for field_name in field_names:
      value = getattr(self, field_name)
      f = partialEval(fexpr_cast(value), env)
      all_vars.extend(v.name for v in f.vars())
      d[field_name] = f

    for p in powerset(all_vars):
      true_vars = list(p)
      false_vars = list(set(all_vars).difference(p))
      e = dict(env)
      e.update({tv : True for tv in true_vars})
      e.update({fv : False for fv in false_vars})

      self.do_delete(e)

  class Meta:
    abstract = True

  _objects_ordinary = Manager()

  @JeevesLib.supports_jeeves
  def __eq__(self, other):
    if isinstance(other, FExpr):
      return other == self
    return isinstance(other, self.__class__) and self.jeeves_id == other.jeeves_id

  @JeevesLib.supports_jeeves
  def __ne__(self, other):
    if isinstance(other, FExpr):
      return other != self
    return not (isinstance(other, self.__class__) and self.jeeves_id == other.jeeves_id)

from django.contrib.auth.models import User
@JeevesLib.supports_jeeves
def evil_hack(self, other):
  if isinstance(other, FExpr):
    return other == self
  return isinstance(other, self.__class__) and self.id == other.id
User.__eq__ = evil_hack 

class JeevesRelatedObjectDescriptor(property):
  @JeevesLib.supports_jeeves
  def __init__(self, field):
    self.field = field
    self.cache_name = field.get_cache_name()

  @JeevesLib.supports_jeeves
  def get_cache(self, instance):
    cache_attr_name = self.cache_name
    if hasattr(instance, cache_attr_name):
      cache = getattr(instance, cache_attr_name)
      if not isinstance(cache, dict):
        jid = getattr(instance, self.field.get_attname())
        assert not isinstance(jid, FExpr)
        cache = {jid : cache}
        setattr(instance, cache_attr_name, cache)
    else:
      cache = {}
      setattr(instance, cache_attr_name, cache)
    return cache

  @JeevesLib.supports_jeeves
  def __get__(self, instance, instance_type):
    if instance is None:
      return self

    cache = self.get_cache(instance)
    def getObj(jeeves_id):
      if jeeves_id is None:
        return None
      if jeeves_id not in cache:
        cache[jeeves_id] = self.field.to.objects.get(**{self.field.join_field.name:jeeves_id})
      return cache[jeeves_id]
    if instance is None:
      return self
    return JeevesLib.facetMapper(fexpr_cast(getattr(instance, self.field.get_attname())), getObj)

  @JeevesLib.supports_jeeves
  def __set__(self, instance, value):
    cache = self.get_cache(instance)
    def getID(obj):
      if obj is None:
        return None
      obj_jid = getattr(obj, self.field.join_field.name)
      if obj_jid is None:
        raise Exception("Object must be saved before it can be attached via JeevesForeignKey.")
      cache[obj_jid] = obj
      return obj_jid
    ids = JeevesLib.facetMapper(fexpr_cast(value), getID)
    setattr(instance, self.field.get_attname(), ids)

from django.db.models.fields.related import ForeignObject
class JeevesForeignKey(ForeignObject):
  requires_unique_target = False
  @JeevesLib.supports_jeeves
  def __init__(self, to, *args, **kwargs):
    self.to = to

    for f in self.to._meta.fields:
      if f.name == 'jeeves_id':
        self.join_field = f
        break
    else:
      # support non-Jeeves tables
      self.join_field = to._meta.pk
      #raise Exception("Need jeeves_id field")

    kwargs['on_delete'] = models.DO_NOTHING
    super(JeevesForeignKey, self).__init__(to, [self], [self.join_field], *args, **kwargs)
    self.db_constraint = False

  @JeevesLib.supports_jeeves
  def contribute_to_class(self, cls, name, virtual_only=False):
    super(JeevesForeignKey, self).contribute_to_class(cls, name, virtual_only=virtual_only)
    setattr(cls, self.name, JeevesRelatedObjectDescriptor(self))

  @JeevesLib.supports_jeeves
  def get_attname(self):
    return '%s_id' % self.name
  
  @JeevesLib.supports_jeeves
  def get_attname_column(self):
    attname = self.get_attname()
    column = self.db_column or attname
    return attname, column

  @JeevesLib.supports_jeeves
  def db_type(self, connection):
    return IntegerField().db_type(connection=connection)

  @JeevesLib.supports_jeeves
  def get_path_info(self):
    opts = self.to._meta
    from_opts = self.model._meta
    return [django.db.models.fields.related.PathInfo(from_opts, opts, (self.join_field,), self, False, True)]

  @JeevesLib.supports_jeeves
  def get_joining_columns(self):
    return ((self.column, self.join_field.column),)

  @property
  def foreign_related_fields(self):
    return (self.join_field,)

  @property
  def local_related_fields(self):
    return (self,)

  @property
  def related_fields(self):
    return ((self, self.join_field),)

  @property
  def reverse_related_fields(self):
    return ((self.join_field, self),)

  @JeevesLib.supports_jeeves
  def get_extra_restriction(self, where_class, alias, related_alias):
    return None

  @JeevesLib.supports_jeeves
  def get_cache_name(self):
    return '_jfkey_cache_' + self.name

  def db_type(self, connection):
    return "VARCHAR(%d)" % JEEVES_ID_LEN

########NEW FILE########
__FILENAME__ = JeevesLib
"""API for Python Jeeves libary.

  :synopsis: Functions for creating sensitive values, labels, and policies.

.. moduleauthor:: Travis Hance <tjhance7@gmail.com>
.. moduleauthor:: Jean Yang <jeanyang@csail.mit.edu>

"""

from env.VarEnv import VarEnv
from env.PolicyEnv import PolicyEnv
from env.PathVars import PathVars
from env.WritePolicyEnv import WritePolicyEnv
from smt.Z3 import Z3
from fast.AST import Facet, fexpr_cast, Constant, Var, Not, FExpr, Unassigned, FObject, jeevesState
from eval.Eval import partialEval
import copy

def init():
  """Initialization function for Jeeves library.

  You should always call this before you do anything Jeeves-y.

  """
  jeevesState.init()

  # TODO this needs to be GC'ed somehow

def supports_jeeves(f):
  f.__jeeves = 0
  return f

@supports_jeeves
def mkLabel(varName = "", uniquify=True):
  """Makes a label to associate with policies and sensitive values.

  :param varName: Optional variable name (to help with debugging).
  :type varName: string
  :returns: Var - fresh label.
  """
  label = jeevesState.policyenv.mkLabel(varName, uniquify)
  jeevesState.all_labels[label.name] = label
  return label

@supports_jeeves
def doesLabelExist(varName):
  return varName in jeevesState.all_labels

@supports_jeeves
def getLabel(varName):
  return jeevesState.all_labels[varName]

@supports_jeeves
def restrict(varLabel, pred, use_empty_env=False):
  """Associates a policy with a label.

  :param varLabel: Label to associate with policy.
  :type varLabel: string
  :param pred: Policy: function taking output channel and returning Boolean result.
  :type pred: T -> bool, where T is the type of the output channel
  """
  jeevesState.policyenv.restrict(varLabel, pred, use_empty_env)

@supports_jeeves
def mkSensitive(varLabel, vHigh, vLow):
  """Creates a sensitive value with two facets.

  :param varLabel: Label to associate with sensitive value.
  :type varLabel: Var
  :param vHigh: High-confidentiality facet for viewers with restricted access.
  :type vHigh: T
  :param vLow: Low-confidentiality facet for other viewers.
  :type vLow: T
  """

  if isinstance(varLabel, Var):
    return Facet(varLabel, fexpr_cast(vHigh), fexpr_cast(vLow))
  else:
    return JeevesLib.jif(varLabel, lambda:vHigh, lambda:vLow)

@supports_jeeves
def concretize(ctxt, v):
  """Projects out a single value to the viewer.

  :param ctxt: Output channel (viewer).
  :type ctxt: T, where policies have type T -> bool
  :param v: Value to concretize.
  :type v: FExpr
  :returns: The concrete (non-faceted) version of T under the policies in the environment.
  """
  return jeevesState.policyenv.concretizeExp(ctxt, v, jeevesState.pathenv.getEnv())

@supports_jeeves
def jif(cond, thn_fn, els_fn):
  condTrans = partialEval(fexpr_cast(cond), jeevesState.pathenv.getEnv())
  if condTrans.type != bool:
    raise TypeError("jif must take a boolean as a condition")
  return jif2(condTrans, thn_fn, els_fn)

def jif2(cond, thn_fn, els_fn):
  if isinstance(cond, Constant):
    return thn_fn() if cond.v else els_fn()

  elif isinstance(cond, Facet):
    if not isinstance(cond.cond, Var):
      raise TypeError("facet conditional is of type %s"
                      % cond.cond.__class__.__name__)

    with PositiveVariable(cond.cond):
      thn = jif2(cond.thn, thn_fn, els_fn)
    with NegativeVariable(cond.cond):
      els = jif2(cond.els, thn_fn, els_fn)

    return Facet(cond.cond, thn, els)

  else:
    raise TypeError("jif condition must be a constant or a var")

# supports short-circuiting
# without short-circuiting jif is unnecessary
# are there performance issues?
@supports_jeeves
def jand(l, r): # inputs are functions
  left = l()
  if not isinstance(left, FExpr):
    return left and r()
  return jif(left, r, lambda:left)

@supports_jeeves
def jor(l, r): # inputs are functions
  left = l()
  if not isinstance(left, FExpr):
    return left or r()
  return jif(left, lambda:left, r)

# this one is more straightforward
# just takes an expression
@supports_jeeves
def jnot(f):
  if isinstance(f, FExpr):
    return Not(f)
  else:
    return not f

@supports_jeeves
def jassign(old, new, base_env={}):
  res = new
  for vs in jeevesState.pathenv.conditions:
    (var, val) = (vs.var, vs.val)
    if var.name not in base_env:
      if val:
        res = Facet(var, res, old)
      else:
        res = Facet(var, old, res)
  if isinstance(res, FExpr):
    return partialEval(res, {}, True)
  else:
    return res

'''
@supports_jeeves
def jhasElt(lst, f):
  acc = False
  # Short circuits.
  for elt in lst:
    isElt = f(elt) # TODO: This should eventually be japply of f to elt.
    if isinstance(isElt, FExpr):
      acc = jor(lambda: isElt, lambda: acc)
    else:
      if isElt:
        return True
  return acc 

@supports_jeeves
def jhas(lst, v):
  return jhasElt(lst, lambda x: x == v)
'''

class PositiveVariable:
  def __init__(self, var):
    self.var = var
  def __enter__(self):
    jeevesState.pathenv.push(self.var, True)
  def __exit__(self, type, value, traceback):
    jeevesState.pathenv.pop()

class NegativeVariable:
  def __init__(self, var):
    self.var = var
  def __enter__(self):
    jeevesState.pathenv.push(self.var, False)
  def __exit__(self, type, value, traceback):
    jeevesState.pathenv.pop()

def liftTuple(t):
  t = fexpr_cast(t)
  if isinstance(t, FObject):
    return t.v
  elif isinstance(t, Facet):
    a = liftTuple(t.thn)
    b = liftTuple(t.els)
    return tuple([Facet(t.cond, a1, b1) for (a1, b1) in zip(a, b)])
  else:
    raise TypeError("bad use of liftTuple")

class Namespace:
  def __init__(self, kw, funcname):
    self.__dict__.update(kw)
    self.__dict__['_jeeves_funcname'] = funcname
    self.__dict__['_jeeves_base_env'] = jeevesState.pathenv.getEnv()

  def __setattr__(self, attr, value):
    self.__dict__[attr] = jassign(self.__dict__.get(attr, Unassigned("variable '%s' in %s" % (attr, self._jeeves_funcname))), value, self.__dict__['_jeeves_base_env'])

@supports_jeeves
def jgetattr(obj, attr):
  if isinstance(obj, FExpr):
    return getattr(obj, attr)
  else:
    return getattr(obj, attr) if hasattr(obj, attr) else Unassigned("attribute '%s'" % attr)

@supports_jeeves
def jgetitem(obj, item):
  try:
    return obj[item]
  except (KeyError, KeyError, TypeError) as e:
    return Unassigned("item '%s'" % attr)

@supports_jeeves
def jmap(iterable, mapper):
  if isinstance(iterable, JList2):
    return jmap_jlist2(iterable, mapper)
  if isinstance(iterable, FObject) and isinstance(iterable.v, JList2):
    return jmap_jlist2(iterable.v, mapper)

  iterable = partialEval(fexpr_cast(iterable), jeevesState.pathenv.getEnv())
  return FObject(JList(jmap2(iterable, mapper)))
def jmap2(iterator, mapper):
  if isinstance(iterator, Facet):
    if jeevesState.pathenv.hasPosVar(iterator.cond):
      return jmap2(iterator.thn, mapper)
    if jeevesState.pathenv.hasNegVar(iterator.cond):
      return jmap2(iterator.els, mapper)
    with PositiveVariable(iterator.cond):
      thn = jmap2(iterator.thn, mapper)
    with NegativeVariable(iterator.cond):
      els = jmap2(iterator.els, mapper)
    return Facet(iterator.cond, thn, els)
  elif isinstance(iterator, FObject):
    return jmap2(iterator.v, mapper)
  elif isinstance(iterator, JList):
    return jmap2(iterator.l, mapper)
  elif isinstance(iterator, JList2):
    return jmap2(iterator.convert_to_jlist1().l, mapper)
  elif isinstance(iterator, list) or isinstance(iterator, tuple):
    return FObject([mapper(item) for item in iterator])
  else:
    return jmap2(iterator.__iter__(), mapper)

def jmap_jlist2(jlist2, mapper):
  ans = JList2([])
  env = jeevesState.pathenv.getEnv()
  for i, e in jlist2.l:
    popcount = 0
    for vname, vval in e.iteritems():
      if vname not in env:
        v = getLabel(vname)
        jeevesState.pathenv.push(v, vval)
        popcount += 1
      elif env[vname] != vval:
        break
    else:
      ans.l.append((mapper(i), e))
    for _ in xrange(popcount):
      jeevesState.pathenv.pop()
  return FObject(ans)

def facetMapper(facet, fn, wrapper=fexpr_cast):
  if isinstance(facet, Facet):
    return Facet(facet.cond, facetMapper(facet.thn, fn, wrapper), facetMapper(facet.els, fn, wrapper))
  elif isinstance(facet, Constant) or isinstance(facet, FObject):
    return wrapper(fn(facet.v))

class JList:
  def validate(self):
    def foo(x):
      assert isinstance(x, list), 'thingy is ' + str(x.l.v)
      return x
    facetMapper(self.l, foo, lambda x : x)

  def __init__(self, l):
    self.l = l if isinstance(l, FExpr) else FObject(l)
    self.validate()
  def __getitem__(self, i):
    return self.l[i]
  def __setitem__(self, i, val):
    self.l[i] = jassign(self.l[i], val)

  def __len__(self):
    return self.l.__len__()
  def __iter__(self):
    return self.l.__iter__()

  def append(self, val):
    l2 = facetMapper(self.l, list, FObject) #deep copy
    l2.append(val)
    self.l = jassign(self.l, l2)
    self.validate()

  def prettyPrint(self):
    def tryPrint(x):
      return x.__class__.__name__
      '''
      try:
        return x.__class__.__name__ #x.prettyPrint()
      except AttributeError:
        return str(x)
      '''
    return str(len(self.l)) #''.join(map(tryPrint, self.l))

class JList2:
  def __init__(self, l=[]):
    if isinstance(l, list):
      self.l = [(i, {}) for i in l]
    else:
      raise NotImplementedError
  
  def append(self, val):
    self.l.append((val, jeevesState.pathenv.getEnv()))

  def eval(self, env):
    return [i for i,e in self.l if all(env[getLabel(v)] == e[v] for v in e)]

  def vars(self):
    all_vars = set()
    for _, e in self.l:
      all_vars.update(set(e.keys()))
    return {getLabel(v) for v in all_vars}

  def convert_to_jlist1(self):
    all_vars = [v.name for v in self.vars()]
    def rec(cur_e, i):
      if i == len(all_vars):
        return FObject([i for i,e in self.l if all(cur_e[v] == e[v] for v in e)])
      else:
        cur_e1 = dict(cur_e)
        cur_e2 = dict(cur_e)
        cur_e1[all_vars[i]] = True
        cur_e2[all_vars[i]] = False
        return Facet(getLabel(all_vars[i]),
            rec(cur_e1, i+1), rec(cur_e2, i+1))
    return JList(rec({}, 0))

  def __getitem__(self, i):
    return self.convert_to_jlist1().__getitem__(i)

  def __setitem__(self, i, val):
    raise NotImplementedError

  def __len__(self):
    return self.convert_to_jlist1().__len__()

class JIterator:
  def __init__(self, l):
    self.l = l

@supports_jeeves
def jfun(f, *args, **kw):
  if hasattr(f, '__jeeves'):
    return f(*args, **kw)
  else:
    env = jeevesState.pathenv.getEnv()
    if len(args) > 0:
      return jfun2(f, args, kw, 0, partialEval(fexpr_cast(args[0]), env), [])
    else:
      it = kw.__iter__()
      try:
        fst = next(it)
      except StopIteration:
        return fexpr_cast(f())
      return jfun3(f, kw, it, fst, partialEval(fexpr_cast(kw[fst]), env), (), {})

def jfun2(f, args, kw, i, arg, args_concrete):
  if isinstance(arg, Constant) or isinstance(arg, FObject):
    env = jeevesState.pathenv.getEnv()
    if i < len(args) - 1:
      return jfun2(f, args, kw, i+1, partialEval(fexpr_cast(args[i+1]), env), tuple(list(args_concrete) + [arg.v]))
    else:
      it = kw.__iter__()
      try:
        fst = next(it)
      except StopIteration:
        return fexpr_cast(f(*tuple(list(args_concrete) + [arg.v])))
      return jfun3(f, kw, it, fst, partialEval(fexpr_cast(kw[fst]), env), tuple(list(args_concrete) + [arg.v]), {})
  else:
    with PositiveVariable(arg.cond):
      thn = jfun2(f, args, kw, i, arg.thn, args_concrete)
    with NegativeVariable(arg.cond):
      els = jfun2(f, args, kw, i, arg.els, args_concrete)
    return Facet(arg.cond, thn, els)

from itertools import tee
def jfun3(f, kw, it, key, val, args_concrete, kw_concrete):
  if isinstance(val, Constant) or isinstance(val, FObject):
    kw_c = dict(kw_concrete)
    kw_c[key] = val.v
    try:
      next_key = next(it)
    except StopIteration:
      return fexpr_cast(f(*args_concrete, **kw_c))
    env = jeevesState.pathenv.getEnv()
    return jfun3(f, kw, it, next_key, partialEval(fexpr_cast(kw[next_key]), env), args_concrete, kw_c)
  else:
    it1, it2 = tee(it)
    with PositiveVariable(val.cond):
      thn = jfun3(f, kw, it1, key, val.thn, args_concrete, kw_concrete)
    with NegativeVariable(val.cond):
      els = jfun3(f, kw, it2, key, val.els, args_concrete, kw_concrete)
    return Facet(val.cond, thn, els)

def evalToConcrete(f):
    g = partialEval(fexpr_cast(f), jeevesState.pathenv.getEnv())
    if isinstance(g, Constant):
      return g.v
    elif isinstance(g, FObject):
      return g.v
    else:
      raise Exception("wow such error: evalToConcrete on non-concrete thingy-ma-bob")

from jlib.JContainer import *

########NEW FILE########
__FILENAME__ = JContainer
'''
List-type functions for Jeeves containers.
'''
import JeevesLib
from fast.AST import FExpr, Constant, Facet

@JeevesLib.supports_jeeves
def jhasElt(lst, f):
  if isinstance(lst, Facet):
    return JeevesLib.jif(lst.cond, lambda:jhasElt(lst.thn, f), lambda:jhasElt(lst.els, f))
  elif isinstance(lst, JeevesLib.JList):
    return jhasElt(lst.l, f)
  elif isinstance(lst, JeevesLib.FObject):
    return jhasElt(lst.v, f)

  acc = False
  # Short circuits.
  for elt in lst:
    isElt = f(elt) # TODO: This should eventually be japply of f to elt.
    if isinstance(isElt, FExpr):
      acc = JeevesLib.jor(lambda: isElt, lambda: acc)
    else:
      if isElt:
        return True
  return acc

@JeevesLib.supports_jeeves
def jhas(lst, v):
  return jhasElt(lst, lambda x: x == v)

@JeevesLib.supports_jeeves
def jall(lst):
  def myall(lst):
    acc = True
    for elt in lst:
      acc = JeevesLib.jand(lambda: elt, lambda: acc)
    return acc

  if isinstance(lst, list):
    return myall(lst)
  else: # lst is a JList
    return JeevesLib.facetMapper(lst.l, myall)

########NEW FILE########
__FILENAME__ = runtests
import unittest
import macropy.activate
from macropy.core.exporters import SaveExporter
macropy.exporter = SaveExporter("exported", ".")

import test.testAST
import test.testJeevesConfidentiality
import test.testSourceTransform
import test.testZ3
import test.gallery.battleship.testBattleship

unittest.TextTestRunner().run(unittest.TestSuite([
    unittest.defaultTestLoader.loadTestsFromModule(test.testAST),
    unittest.defaultTestLoader.loadTestsFromModule(test.testJeevesConfidentiality),
    unittest.defaultTestLoader.loadTestsFromModule(test.testZ3),
    unittest.defaultTestLoader.loadTestsFromModule(test.testSourceTransform),
    unittest.defaultTestLoader.loadTestsFromModule(test.gallery.battleship.testBattleship),
]))

########NEW FILE########
__FILENAME__ = SMT
'''
Translate expressions to SMT import format.
'''
from Z3 import Z3

class UnsatisfiableException(Exception):
    pass

# NOTE(JY): Think about if the solver needs to know about everything for
# negative constraints. I don't think so because enough things should be
# concrete that this doesn't matter.
def solve(constraints, defaults, desiredVars):
  # NOTE(JY): This is just a sketch of what should go on...
  # Implement defaults by adding values to the model and 

  #for v in jeeveslib.env.envVars:
  #  jeeveslib.solver.push()
  #  solver.assertConstraint(v = z3.BoolVal(True))
  #  if (solver.check() == solver.Unsat):
  #    jeeveslib.solver.pop()

  # Now get the variables back from the solver by evaluating all
  # variables in question...

  # Now return the new environment...
  #return NotImplemented

  solver = Z3()
  result = {}

  for constraint in constraints:
    if constraint.type != bool:
      raise ValueError("constraints must be bools")
    solver.boolExprAssert(constraint)

  if not solver.check():
    raise UnsatisfiableException("Constraints not satisfiable")

  for default in defaults:
    solver.push()
    if default.type != bool:
      raise ValueError("defaults must be bools")
    solver.boolExprAssert(default)
    if not solver.isSatisfiable():
      solver.pop()

  assert solver.check()

  result = {}
  for var in desiredVars:
    result[var] = solver.evaluate(var)
    assert (result[var] is True) or (result[var] is False)

  return result

########NEW FILE########
__FILENAME__ = Z3
'''
Defines the interface to the Z3 solver.
'''
# TODO: Define UnsatException and SolverException
import z3

class Z3:
  def __init__(self):
    self.solver = z3.Solver()

  # TODO: Is this the place to do this?
  #def __del__(self):
  #  z3.delete()

  # Defining variables.
  def getIntVar(self, name):
    return z3.Int(name)

  def getBoolVar(self, name):
    return z3.Bool(name)

  def check(self):
    return self.solver.check()

  def isSatisfiable(self):
    r = self.solver.check()
    if r == z3.sat:
      return True
    elif r == z3.unsat:
      return False
    else:
      raise ValueError("got neither sat nor unsat from solver")

  def evaluate(self, t):
    s = self.solver.model().eval(t.z3Node())
    assert z3.is_true(s) or z3.is_false(s)
    return z3.is_true(s)

  def solverAssert(self, constraint):
    return self.solver.add(constraint)

  def boolExprAssert(self, constraint):
    return self.solver.add(constraint.z3Node())

  def push(self):
    self.solver.push()

  def pop(self):
    self.solver.pop()

  def reset(self):
    self.solver.reset_memory()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Python Jeeves documentation build configuration file, created by
# sphinx-quickstart on Wed Feb 26 16:14:12 2014.
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
sys.path.insert(0, os.path.abspath('/home/jeanyang/code/pythonjeeves/'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Python Jeeves'
copyright = u'2014, Travis Hance, Jean Yang'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0'

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
exclude_patterns = []

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
htmlhelp_basename = 'PythonJeevesdoc'


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
  ('index', 'PythonJeeves.tex', u'Python Jeeves Documentation',
   u'Travis Hance, Jean Yang', 'manual'),
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
    ('index', 'pythonjeeves', u'Python Jeeves Documentation',
     [u'Travis Hance, Jean Yang'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'PythonJeeves', u'Python Jeeves Documentation',
   u'Travis Hance, Jean Yang', 'PythonJeeves', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = add_supports_jeeves
from macropy.core.macros import *
from macropy.core.quotes import macros, q, ast, u
from ast import *

import common

"""
Adds the @JeevesLib.supports_jeeves decorator to indicate that the function
supports Jeeves
"""

def add_supports_jeeves(node):
  @Walker
  def transform(tree, stop, **kw):
    if isinstance(tree, FunctionDef) or isinstance(tree, ClassDef):
      tree.decorator_list.insert(0, q[JeevesLib.supports_jeeves])

    if isinstance(tree, Lambda):
      args = tree.args
      body = transform.recurse(tree.body)
      stop()
      return q[JeevesLib.supports_jeeves(ast[Lambda(args, body)])]

  return transform.recurse(node)

########NEW FILE########
__FILENAME__ = basic_expr
from macropy.core.macros import *
from macropy.core.quotes import macros, q, ast, u
from ast import *

import common

"""
Transforms all expressions in a tree if they are not overidable normally
For example, and -> jand
not -> jnot
A if CONDITION else B -> jif
"""

def basic_expr_transform(node):
  @Walker
  def transform(tree, stop, **kw):
    if isinstance(tree, FunctionDef) or isinstance(tree, ClassDef):
      for decorator in tree.decorator_list:
        if isinstance(decorator, Name) and decorator.id == "jeeves":
          raise Exception("Do not use nested @jeeves")

    # not expr
    # JeevesLib.jnot(expr)
    if isinstance(tree, UnaryOp) and isinstance(tree.op, Not):
      return q[ JeevesLib.jnot(ast[tree.operand]) ]

    # a1 and a2 and ... and an
    # JeevesLib.jand(lambda : left, lambda : right)
    if isinstance(tree, BoolOp):
      if isinstance(tree.op, And):
        fn = q[ JeevesLib.jand ]
      else:
        fn = q[ JeevesLib.jor ]
      result = tree.values[-1]
      for operand in tree.values[-2::-1]:
        result = q[ ast[fn](lambda : ast[operand], lambda : ast[result]) ]
      return result

    if isinstance(tree, List):
      elts = [transform.recurse(elt) for elt in tree.elts]
      newlist = List(elts=elts, ctx=tree.ctx)
      stop()
      return q[ JeevesLib.JList(ast[newlist]) ]

    # thn if cond else els
    # JeevesLib.jif(cond, lambda : thn, lambda : els)
    if isinstance(tree, IfExp):
      return q[ JeevesLib.jif(ast[tree.test], lambda : ast[tree.body], lambda : ast[tree.orelse]) ]

    # [expr for args in iterator]
    # JeevesLib.jmap(iterator
    if isinstance(tree, ListComp):
      elt = tree.elt
      generators = tree.generators
      assert len(generators) == 1
      assert len(generators[0].ifs) == 0
      target = common.storeToParam(generators[0].target)
      iter = generators[0].iter
      lmbda = Lambda(
        args=arguments(
          args=[target],
          vararg=None,
          kwarg=None,
          defaults=[]
        ),
        body=elt
      )
      return q[ JeevesLib.jmap(ast[iter], ast[lmbda]) ]

    if isinstance(tree, Compare):
      assert len(tree.ops) == 1
      # TODO other comparisons besides 'in'
      if isinstance(tree.ops[0], In):
        return q[ JeevesLib.jhas(ast[tree.comparators[0]], ast[tree.left]) ]

    # replace f(...) with jfun(f, ...)
    if isinstance(tree, Call):
      func = transform.recurse(tree.func)
      args = [transform.recurse(arg) for arg in tree.args]
      keywords = [transform.recurse(kw) for kw in tree.keywords]
      starargs = transform.recurse(tree.starargs)
      kwargs = transform.recurse(tree.kwargs)
      stop()

      return Call(
        func=q[JeevesLib.jfun],
        args=[func] + args,
        keywords=keywords,
        starargs=starargs,
        kwargs=kwargs
      )

  return transform.recurse(node)

########NEW FILE########
__FILENAME__ = body_stmts
from macropy.core.macros import *
from macropy.core.quotes import macros, q, ast, u
from ast import *

import common

import copy

"""
Replace if-statments and for-blocks with jif and jmap
"""
def body_stmts_transform(tree, gen_sym):
  @Walker
  def transform(tree, stop, **kw):
    # If a1,a2,..,an are all the local variables, change
    #
    # if condition:
    #     thn_body
    # else:
    #     els_body
    # 
    # to
    #
    # def thn_fn_name():
    #     thn_body
    # def els_fn_name():
    #     els_body
    # jif(condition, thn_fn_name, els_fn_name)
    if isinstance(tree, If):
      # TODO search over the bodies, and only do this for the variables that
      # get assigned to.
      thn_fn_name = gen_sym()
      els_fn_name = gen_sym()

      test = transform.recurse(tree.test)
      thn_body = transform.recurse(tree.body)
      els_body = transform.recurse(tree.orelse)
      stop()

      def get_func(funcname, funcbody):
        return FunctionDef(
          name=funcname, 
          args=arguments(
            args=[],
            vararg=None,
            kwarg=None,
            defaults=[],
          ),
          body=funcbody or [Pass()],
          decorator_list=[],
        )

      return [
        get_func(thn_fn_name, thn_body),
        get_func(els_fn_name, els_body),
        Expr(value=q[
          JeevesLib.jif(ast[test],
            ast[Name(id=thn_fn_name,ctx=Load())],
            ast[Name(id=els_fn_name,ctx=Load())],
          )
        ])
      ]

    if isinstance(tree, For):
      body_fn_name = gen_sym()

      iter = transform.recurse(tree.iter)
      body = transform.recurse(tree.body)
      targetParams = common.storeToParam(copy.deepcopy(tree.target))
      assert len(tree.orelse) == 0 or isinstance(tree.orelse[0], Pass)
      stop()

      func = copy_location(FunctionDef(
        name=body_fn_name,
        args=arguments(
          args=[targetParams],
          vararg=None,
          kwarg=None,
          defaults=[],
        ),
        body=body,
        decorator_list=[]
      ), tree)

      return [
        func,
        Expr(value=q[ JeevesLib.jmap(ast[iter], ast[Name(body_fn_name,Load())]) ])
      ]

  return transform.recurse(tree)

########NEW FILE########
__FILENAME__ = classes
from macropy.core.macros import *
from macropy.core.quotes import macros, q, ast, u
from ast import *

def classes_transform(node, gen_sym):
  @Walker
  def transform(tree, **k2):
    if isinstance(tree, ClassDef):
      # ClassDef(identifier name, expr* bases, stmt* body, expr* decorator_list)

      # Add the function
      # def __setattr__(self, attr, value):
      #   self.__dict__[attr] = jassign(self.__dict__.get(attr, Unassigned("attribute '%s'" % attr)), value)
      self_name = gen_sym()
      attr_name = gen_sym()
      value_name = gen_sym()
      newfunc = FunctionDef(
        name="__setattr__",
        args=arguments(
          args=[Name(id=self_name,ctx=Param()),
                Name(id=attr_name,ctx=Param()),
                Name(id=value_name,ctx=Param()),
               ],
          vararg=None,
          kwarg=None,
          defaults=[]
        ),
        decorator_list=[],
        body=[
          Assign([Subscript(
            value=Attribute(
              value=Name(id=self_name, ctx=Load()),
              attr="__dict__",
              ctx=Load(),
            ),
            slice=Index(Name(id=attr_name, ctx=Load())),
            ctx=Store(),
          )],
          q[ JeevesLib.jassign(name[self_name].__dict__.get(name[attr_name],
                JeevesLib.Unassigned("attribute '%s'" % name[attr_name])), name[value_name]) ]
          )
        ]
      )

      return copy_location(ClassDef(
        name=tree.name,
        bases=tree.bases,
        body=[newfunc] + tree.body,
        decorator_list=tree.decorator_list,
      ), tree)

  return transform.recurse(node)

########NEW FILE########
__FILENAME__ = common
from macropy.core.macros import *
from macropy.core.quotes import macros, q, ast, u
from ast import *

@Walker
def toParam(tree, **kw):
  if isinstance(tree, Store):
    return Param()

@Walker
def toLoad(tree, **kw):
  if isinstance(tree, Store):
    return Load()

def storeToParam(node):
  return toParam.recurse(node)

def storeToLoad(node):
  return toLoad.recurse(node)

########NEW FILE########
__FILENAME__ = macro_module
# macro_module.py
from macropy.core.macros import *
from macropy.core.quotes import macros, q, ast, u
from ast import *

from basic_expr import basic_expr_transform
from body_stmts import body_stmts_transform
from namespace import replace_local_scopes_with_namespace
from classes import classes_transform
from return_transform import return_transform
from add_supports_jeeves import add_supports_jeeves

macros = Macros()

@macros.decorator
def jeeves(tree, gen_sym, **kw):
    tree = basic_expr_transform(tree)
    tree = add_supports_jeeves(tree)
    tree = return_transform(tree, gen_sym)
    tree = replace_local_scopes_with_namespace(tree, gen_sym)
    tree = body_stmts_transform(tree, gen_sym)

    tree = classes_transform(tree, gen_sym)

    return tree

########NEW FILE########
__FILENAME__ = namespace
from macropy.core.macros import *
from macropy.core.quotes import macros, q, ast, u
from ast import *

import common
import copy

# Returns a list of the vars assigned to in an arguments node
def get_params_in_arguments(node):
  @Walker
  def get_params(tree, collect, **kw):
    if isinstance(tree, Name):
      collect(tree.id)
  _, p1 = get_params.recurse_collect(node.args)
  _, p2 = get_params.recurse_collect(node.vararg)
  _, p3 = get_params.recurse_collect(node.kwarg)
  return p1 + p2 + p3

# Takes a FunctionDef node and returns a pair
# (list of local variables, list of parameter variables)
def get_vars_in_scope(node):
  @Walker
  def get_vars(tree, collect, stop, **kw):
    if isinstance(tree, Name) and isinstance(tree.ctx, Store):
      collect(tree.id)
    if isinstance(tree, ClassDef):
      stop()
    if tree != node and isinstance(tree, FunctionDef):
      collect(tree.name)
      stop()
    if isinstance(tree, arguments):
      pass

  @Walker
  def get_globals(tree, collect, stop, **kw):
    if isinstance(tree, Global):
      for name in tree.names:
        collect(name)
    if tree != node and (isinstance(tree, ClassDef) or isinstance(tree, FunctionDef)):
      stop()

  _, v = get_vars.recurse_collect(node)
  _, g = get_globals.recurse_collect(node)
  p = get_params_in_arguments(node.args)
  return (list(set(v) - set(g)), p)

def replace_local_scopes_with_namespace(node, gen_sym):
  @Walker
  def transform(tree, stop, ctx, set_ctx, **kw):
    if isinstance(tree, FunctionDef):
      varNames, paramNames = get_vars_in_scope(tree)
      namespaceName = gen_sym()

      # namespaceName = Namespace({param1:value1,...},funcname)
      namespaceStmt = Assign(
        targets=[Name(id=namespaceName,ctx=Store())],
        value=Call(
          func=q[JeevesLib.Namespace],
          args=[Dict(
            keys=[Str(p) for p in paramNames],
            values=[Name(id=p, ctx=Load()) for p in paramNames],
          ),
            Str(s=tree.name)
          ],
          keywords=[],
          starargs=None,
          kwargs=None,
        )
      )

      # make a copy of the scope mapping nad update it
      scopeMapping = dict(ctx)
      for name in varNames + paramNames:
        scopeMapping[name] = namespaceName

      name = tree.name
      args = transform.recurse(tree.args, ctx=ctx) 
      body = transform.recurse(tree.body, ctx=scopeMapping)
      decorator_list = transform.recurse(tree.decorator_list, ctx=ctx)
      newtree = copy_location(
        FunctionDef(name=name, args=args,
                body=[namespaceStmt]+body,
                decorator_list=decorator_list),
        tree
      )

      stop()
      
      if tree.name in ctx and ctx[tree.name] != None:
        outerAssignStmt = copy_location(Assign(
          targets=[Attribute(
            value=Name(id=ctx[tree.name], ctx=Load()),
            attr=tree.name,
            ctx=Store()
          )],
          value=Name(id=tree.name, ctx=Load()),
        ), tree)
        return [newtree, outerAssignStmt]
      else:
        return newtree

    if isinstance(tree, Lambda):
      paramNames = get_params_in_arguments(tree.args)

      # make a copy of the scope mapping and update it
      scopeMapping = dict(ctx)
      for name in paramNames:
        scopeMapping[name] = None

      args = transform.recurse(tree.args, ctx=ctx)
      body = transform.recurse(tree.body, ctx=scopeMapping)
      newlambda = copy_location(Lambda(args=args, body=body), tree)
      stop()
      return newlambda

    if isinstance(tree, Name) and (isinstance(tree.ctx, Load) or isinstance(tree.ctx, Store) or isinstance(tree.ctx, Del)):
      if tree.id in ctx and ctx[tree.id] != None:
        return Attribute(
          value=Name(id=ctx[tree.id], ctx=Load()),
          attr=tree.id,
          ctx=tree.ctx
        )

    if isinstance(tree, For):
      # For(expr target, expr iter, stmt* body, stmt* orelse)
      target = tree.target
      iter = tree.iter
      body = tree.body
      orelse = tree.orelse
      
      stop()

      assignTarget = transform.recurse(copy.deepcopy(target), ctx=ctx)
      assignValue = common.storeToLoad(copy.deepcopy(target))
      assignStmt = Assign([assignTarget], assignValue)

      iter = transform.recurse(iter, ctx=ctx)
      body = transform.recurse(body, ctx=ctx)
      orelse = transform.recurse(orelse, ctx=ctx)

      return copy_location(
        For(target=target, iter=iter, body=[assignStmt]+body, orelse=orelse),
        tree
      )

    if isinstance(tree, arguments):
      stop()
      return arguments(
        args=tree.args,
        vararg=tree.vararg,
        kwarg=tree.kwarg,
        defaults=transform.recurse(tree.defaults, ctx=ctx)
      )

  return transform.recurse(node, ctx={})

########NEW FILE########
__FILENAME__ = return_transform
from macropy.core.macros import *
from macropy.core.quotes import macros, q, ast, u
from ast import *

import common

"""
move all return statements to the end of a function
"""

def return_transform(node, gen_sym):
  @Walker
  def transform(tree, **kw):
    if isinstance(tree, FunctionDef):
      hasnt_returned_var = gen_sym()
      return_value_var = gen_sym()

      def return_recurse(body):
        tail = []
        for stmt in body[::-1]:
          if isinstance(stmt, Return):
            tail = [Assign(targets=[Name(id=hasnt_returned_var,ctx=Store())],value=Name("False",Load()))]
            if stmt.value:
              tail.append(copy_location(
                Assign(targets=[Name(id=return_value_var,ctx=Store())],value=stmt.value),
                stmt
              ))
          elif isinstance(stmt, If):
            tail = [
              If(test=Name(id=hasnt_returned_var,ctx=Load()),
                body=tail[::-1],
                orelse=[Pass()],
              ),
              copy_location(
                If(test=stmt.test,
                  body=return_recurse(stmt.body),
                  orelse=return_recurse(stmt.orelse)
                ), stmt),
            ]
          elif isinstance(stmt, For):
            tail = [
              If(test=Name(id=hasnt_returned_var,ctx=Load()),
                body=tail[::-1],
                orelse=[Pass()],
              ),
              copy_location(
                For(target=stmt.target,
                  iter=stmt.iter,
                  body=[If(
                    test=Name(hasnt_returned_var,Load()),
                    body=return_recurse(stmt.body),
                    orelse=[Pass()],
                  )],
                  orelse=[Pass()]
                ), stmt),
            ]
          else:
            tail.append(stmt)

        return tail[::-1]

      tree.body = (
       [
          Assign(targets=[Name(hasnt_returned_var,Store())], value=Name("True",Load())),
          Assign(targets=[Name(return_value_var,Store())], value=Name("None",Load())),
       ] +
       return_recurse(tree.body) +
       [
          Return(value=Name(return_value_var,Load())),
       ]
      )

  return transform.recurse(node)

########NEW FILE########
__FILENAME__ = Auction
'''
Authentication demo example for Jeeves with confidentiality policies.
'''
#from macropy.case_classes import macros, case
import JeevesLib

class User:
  def __init__(self, userId):
    self.userId = userId

class AuctionContext():
  def __init__(self, user, time, bids):
    self.user = user
    self.time = time
    self.bids = bids

class Bid:
  def __init__(self, value, owner, policy):
    lab = JeevesLib.mkLabel ()
    # TODO: Add policy that the output channel has to be either the owner or
    # satisfy the policy on it (policy(oc)).
    JeevesLib.restrict(lab
        , lambda oc: JeevesLib.jor(
            lambda: oc.user == owner, lambda: policy(oc)))
    self.value = JeevesLib.mkSensitive(lab, value, -1)
    self.owner = owner

########NEW FILE########
__FILENAME__ = testAuction
import macropy.activate
import JeevesLib
from smt.Z3 import *
import unittest
from Auction import AuctionContext, Bid, User
import JeevesLib

class TestAuction(unittest.TestCase):
  def setUp(self):
    JeevesLib.init()
    self.aliceUser = User(0)
    self.bobUser = User(1)
    self.claireUser = User(2)

  def testOwnerCanSee(self):
    policy = lambda oc: False
    aliceBid = Bid(3, self.aliceUser, policy)
    
    ctxt0 = AuctionContext(self.aliceUser, 0, [])
    self.assertEqual(3
        , JeevesLib.concretize(ctxt0, aliceBid.value))

    ctxt1 = AuctionContext(self.bobUser, 0, [])
    self.assertEqual(-1
        , JeevesLib.concretize(ctxt1, aliceBid.value))

  def testTimeSensitiveRelease(self):
    auctionEndTime = 10
    policy = lambda oc: oc.time > auctionEndTime
    aliceBid = Bid(3, self.aliceUser, policy)

    self.assertEqual(3
        , JeevesLib.concretize(
          AuctionContext(self.bobUser, 11, []), aliceBid.value))
    self.assertEqual(-1
        , JeevesLib.concretize(
          AuctionContext(self.bobUser, 10, []), aliceBid.value))

  def testSealedAuction(self):
    # Function that returns true if the context contains a bid from the given
    # user.
    def hasBidFromUser(ctxt, u):
      return JeevesLib.jhasElt(ctxt.bids, lambda b: b.owner == u)
    allUsers = [self.aliceUser, self.bobUser, self.claireUser]
    policy = lambda oc: reduce(lambda acc, c: JeevesLib.jand(
                    lambda: hasBidFromUser(oc, c), lambda: acc)
                  , allUsers)

    aliceBid = Bid(3, self.aliceUser, policy)
    bobBid = Bid(4, self.bobUser, policy)
    claireBid = Bid(5, self.claireUser, policy)

    self.assertEqual(-1,
      JeevesLib.concretize(
        AuctionContext(self.bobUser, 11, [aliceBid]), aliceBid.value))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = AuthConfidentiality
'''
Authentication demo example for Jeeves with confidentiality policies.
'''
import JeevesLib
from sourcetrans.macro_module import macros, jeeves

@jeeves
class Principal:
  class User:
    def __init__(self, userId, name, pwd):
      self.userId = userId
      self.name = name

      # Sensitive password.
      self.pwdLabel = JeevesLib.mkLabel()
      JeevesLib.restrict(self.pwdLabel, lambda oc:
        oc.pwd == self.pwd if isinstance(oc, Principal.User) else False)
      self.pwd = JeevesLib.mkSensitive(self.pwdLabel, pwd, "")

    def __eq__(self, other):
      return self.userId == other.userId
  class NullUser:
    def __eq__(self, other):
      return isinstance(other, Principal.NullUser)

class Authentication:
  @staticmethod
  @jeeves
  def login(prin, pwd):
    if isinstance(prin, Principal.User):
      return prin if (prin.pwd == pwd) else Principal.NullUser()

########NEW FILE########
__FILENAME__ = testAuthConfidentiality
from smt.Z3 import *
import unittest
from AuthConfidentiality import Authentication, Principal
import JeevesLib

class TestAuthConfidentiality(unittest.TestCase):
  def setUp(self):
    JeevesLib.init()
    self.alicePwd = "alicePwd"
    self.bobPwd = "bobPwd"
    self.aliceUser = Principal.User(1, "Alice", self.alicePwd)
    self.bobUser = Principal.User(2, "Bob", self.bobPwd)

  def testUserCanSeeOwnPassword(self):  
    alicePwdToAlice = JeevesLib.concretize(
        self.aliceUser, self.aliceUser.pwd)
    self.assertEqual(alicePwdToAlice, self.alicePwd)

  def testUserCannotSeeOtherPassword(self):
    bobPwdToAlice = JeevesLib.concretize(
        self.aliceUser, self.bobUser.pwd)
    self.assertEqual(bobPwdToAlice, "")

  def testLogin(self):
    self.assertEqual( JeevesLib.concretize(self.aliceUser
                        , Authentication.login(self.aliceUser, self.alicePwd))
                    , self.aliceUser)
    self.assertEqual( JeevesLib.concretize(self.aliceUser
                        , Authentication.login(self.aliceUser, "otherPwd"))
                      , Principal.NullUser())

  def testSensitiveUserPassword(self):
    # Make a sensitive user that is either Alice or Bob. Make sure it shows the
    # the right password based on the access level of the user.
    pass

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = Battleship
'''
Battleship game demo example.
'''
import JeevesLib
import Board
from Bomb import Bomb
from sourcetrans.macro_module import macros, jeeves

class Game:
  class NoSuchUserException(Exception):
    def __init__(self, u):
      self.u = u

  def __init__(self, boards):
    self.boards = boards
    self._moves = []

  def getBoard(self, user):
    try:
      return self.boards[user]
    except Exception:
      raise NoSuchUserException(user)

  @jeeves
  def allShipsPlaced(self):
    return JeevesLib.jall(map(lambda b: b.allPlaced(), self.boards.values()))

  @jeeves
  def gameOver(self):
    return not JeevesLib.jall(map(lambda b: not b.hasLost(), self.boards.values()))

  @jeeves
  def hasTurn(self, user):
    return (not self._moves) or (not self._moves[-1] == user)
  
  def bomb(self, ctxt, user, x, y):
    piece = self.getBoard(user).placeBomb(ctxt, x, y)
    self._moves.append(ctxt.user)
    return piece

'''
object BattleshipGame extends JeevesLib[GameContext] {
  val alice = User(0)
  val aliceBoard = Board(alice)
  val aliceBomb = Bomb(alice)

  val bob = User(1)
  val bobBoard = Board(bob)
  val bobBomb = Bomb(bob)

  val game = Game(Map(alice -> aliceBoard, bob -> bobBoard))
  val aliceCtxt = GameContext(alice, game)
  val bobCtxt =  GameContext(bob, game)

  // TODO: Make server socket so we can have two players playing at once.
  def main(args: Array[String]): Unit = {
    println("Welcome to this Battleship game.")

    // Alice's pieces.
    aliceBoard.placeShip(aliceCtxt, Carrier(alice), Point(0, 0), Point(0, 5))
    aliceBoard.placeShip(
      aliceCtxt, Battleship(alice), Point(1, 0), Point(1, 4))
    aliceBoard.placeShip(aliceCtxt, Cruiser(alice), Point(2, 0), Point(2, 3))
    aliceBoard.placeShip(
      aliceCtxt, Destroyer(alice), Point(3, 0), Point(3, 2))
    aliceBoard.placeShip(
      aliceCtxt, Destroyer(alice), Point(4, 0), Point(4, 2))
    aliceBoard.placeShip(
      aliceCtxt, Submarine(alice), Point(5, 0), Point(5, 1))
    aliceBoard.placeShip(
      aliceCtxt, Submarine(alice), Point(5, 1), Point(5, 2))
 
    // Bob's pieces.
    bobBoard.placeShip(
        bobCtxt, Carrier(bob), Point(0, 0), Point(0, 5))
    bobBoard.placeShip(
      bobCtxt, Battleship(bob), Point(1, 0), Point(1, 4))
    bobBoard.placeShip(bobCtxt, Cruiser(bob), Point(2, 0), Point(2, 3))
    bobBoard.placeShip(
      bobCtxt, Destroyer(bob), Point(3, 0), Point(3, 2))
    bobBoard.placeShip(
      bobCtxt, Destroyer(bob), Point(4, 0), Point(4, 2))
    bobBoard.placeShip(
      bobCtxt, Submarine(bob), Point(5, 0), Point(5, 1))
    bobBoard.placeShip(
      bobCtxt, Submarine(bob), Point(5, 1), Point(5, 2))

    game.bomb(bobCtxt, alice, 0, 0)
    game.bomb(aliceCtxt, bob, 0, 0)
    game.bomb(bobCtxt, alice, 1, 0)
    game.bomb(aliceCtxt, bob, 1, 0)
    game.bomb(bobCtxt, alice, 2, 0)
    game.bomb(aliceCtxt, bob, 2, 0)
    game.bomb(bobCtxt, alice, 3, 0)
    game.bomb(aliceCtxt, bob, 3, 0)
    game.bomb(bobCtxt, alice, 4, 0)
    game.bomb(aliceCtxt, bob, 4, 0)
    game.bomb(bobCtxt, alice, 5, 0)
    game.bomb(aliceCtxt, bob, 5, 0)
    game.bomb(bobCtxt, alice, 5, 1)
    //game.gameOver()

    /*
    // TODO: Listen until we get two players.
    while (!board0.hasLost() || !board1.hasLost()) {
      println("Player 0 board:")
      board0.printBoard()

      println("Player 1 board:")
      board1.printBoard()

      val input = readLine("prompt> ")
    }
    */
  }
'''

########NEW FILE########
__FILENAME__ = Board
'''
Defines a battleship game board.
'''
import JeevesLib
from Bomb import Bomb
from GamePiece import Carrier, Battleship, Cruiser, Destroyer, Submarine, NoShip
from sourcetrans.macro_module import macros, jeeves
from Square import Square

class Board:
  class OutOfBoundsException(Exception):
    pass

  def __init__(self, owner):
    self.owner = owner  
    self.boardSize = 10
    
    # Initialize the board.
    self.board = []
    for i in range(0, self.boardSize):
      curCol = []
      for j in range(0, self.boardSize):      
        curCol.append(Square(self.owner))
      self.board.append(curCol)    

    self.pieces = [ Carrier(owner), Battleship(owner), Cruiser(owner)
                  , Destroyer(owner), Destroyer(owner)
                  , Submarine(owner), Submarine(owner) ]

  def getSquare(self, x, y):
    return self.board[x][y]

  # Places a ship on the board. Looks in the list of current pieces to mark
  # it as placed. Updates the ship and the board.
  @jeeves
  def placeShip(self, ctxt, ship, start, end):
    for cur in self.pieces:
      if cur == ship and not cur.isPlaced():
        # Update the relevant board pieces.
        pts = cur.getPiecePoints(start, end)
        if not (pts == None):
          for pt in pts:
            shipUpdated = self.board[pt.x][pt.y].updateShip(ctxt, cur)
            squareUpdated = cur.addSquare(self.board[pt.x][pt.y])
            if not (shipUpdated and squareUpdated):
              return False
          return cur.placePiece(ctxt)
        # If the points didn't fit, then we can't place the ship.
        else:        
            print "Piece didn't fit: "
            print ship
            print "\n"
            return False
    print "Don't have piece to play: "
    print ship
    print "\n"
    return False

  # Places a bomb. Updates the specific square on the board. If there is a
  # ship at this point, this function also updates the ship with the fact that
  # it has been bombed.
  # NOTE: This seems to be a problematic function causing some tests to fail...
  @jeeves
  def placeBomb(self, ctxt, x, y):
    if x < self.boardSize and y < self.boardSize:
      boardShip = self.board[x][y].getShip()
      bomb = Bomb(ctxt.user)
      bombedPoint = self.board[x][y].bomb(ctxt, bomb)
      succeeded = (bombedPoint if boardShip == NoShip()
                    else boardShip.bombPiece(ctxt) and JeevesLib.jall(map(lambda s: s.bomb(ctxt, bomb), boardShip.getSquares())))
      print "succeeded: ", succeeded
      return boardShip if succeeded else NoShip()
    else:
      print "Bomb location outside of board: (" + x + ", " + y + ")" + "\n"
      raise OutOfBoundsException

  # Determines if all of a player's pieces have been placed. This variable
  # should always be concrete.
  @jeeves
  def allPlaced(self):
    return JeevesLib.jall(map(lambda p: p.isPlaced(), self.pieces))
  
  # Determines if all pieces on the board have been bombed. This variable
  # should always be concrete.
  @jeeves
  def hasLost(self):
    return JeevesLib.jall(map(lambda p: p.isBombed(), self.pieces))

  def printBoard(self, ctxt):
    for j in range(0, 10):
      for i in range(0, 10):
        curSquare = self.board[i][j]
        if JeevesLib.concretize(ctxt, curSquare.hasBomb()):
          print("X")
        elif concretize(ctxt, curSquare.hasShip()):
          print("S")
        else:
          print("W")
      print("\n")

  def printUnplacedPieces(self):
    print "Remaining unplaced pieces:\n"
    for p in self.pieces:
      if not p.isPlaced():
        print p
        print "\n"

  def printRemainingPieces(self):
    print "Remaining pieces:\n"
    for p in self.pieces:
      if not p.isBombed():
        print p
        print "\n"

########NEW FILE########
__FILENAME__ = Bomb
import JeevesLib
from sourcetrans.macro_module import macros, jeeves

@jeeves
class Bomb:
  def __init__(self, owner):
    self.owner = owner

########NEW FILE########
__FILENAME__ = GameContext
import JeevesLib
from sourcetrans.macro_module import macros, jeeves

@jeeves
class GameContext:
  def __init__(self, user, game):
    self.user = user
    self.game = game

########NEW FILE########
__FILENAME__ = GamePiece
from abc import ABCMeta, abstractmethod
from sourcetrans.macro_module import macros, jeeves
import JeevesLib
from fast.ProtectedRef import ProtectedRef, UpdateResult
from util.Singleton import Singleton
from Point import Point

@jeeves
class GamePiece:
  __metaclass__ = ABCMeta

  def __init__(self, owner):
    self.owner = owner  
    self._placedRef = ProtectedRef(False
      , lambda hasShip: lambda ic: (not hasShip) and self.isOwner(ic)
      , None)
    # TODO: See if we can do away with this...
    self._placed = False
    self._bombed = False

    self._squares = []

  def __eq__(self, other):
    return (self.name == other.name and self.owner == other.owner)

  def isOwner(self, ctxt):
    return ctxt.user == self.owner

  # If the current user is allowed to place the pice, then we mark the current
  # piece as placed and return True. Otherwise we return False.
  def placePiece(self, ctxt):
    if (self._placedRef.update(ctxt, ctxt, True) == UpdateResult.Success):
      self._placed = True
      return True
    else:
      return False
  # This is always a concrete value.
  def isPlaced(self):
    return self._placed
  # If the current user is allowed to bomb the piece, then we mark the piece
  # and return True. Otherwise we return False.
  def bombPiece(self, ctxt):
    self._bombed = True;
    return True
  
  # This is always a concrete value.
  def isBombed(self):
    return self._bombed

  # Gets the board coordinates associated with a given piece.
  def getPiecePoints(self, start, end):
    if start.inLine(end) and start.distance(end) == self.size:
      # If we are on the same horizontal line...
      if start.x == end.x:
        yPts = range(start.y
                      , end.y) if start.y < end.y else range(end.y, start.y)
        return map(lambda yPt: Point(start.x, yPt), yPts)
      else:
        xPts = range(start.x
                      , end.x) if start.x < end.x else range(end.x, start.x)
        return map(lambda xPt: Point(xPt, start.y), xPts)
    else:
      return None
  
  # Adds a piece to the list of squares associated with a given piece.
  def addSquare(self, s):
    self._squares.append(s)
    return True
  def getSquares(self):
    return self._squares

class Carrier(GamePiece):
  name = 'carrier'
  def __init__(self, owner):
    self.size = 5
    GamePiece.__init__(self, owner)
class Battleship(GamePiece):
  name = 'battleship'
  def __init__(self, owner):
    self.size = 4
    GamePiece.__init__(self, owner)
class Cruiser(GamePiece):
  name = 'cruiser'
  def __init__(self, owner):
    self.size = 3
    GamePiece.__init__(self, owner)
class Destroyer(GamePiece):
  name = 'destroyer'
  def __init__(self, owner):
    self.size = 2
    GamePiece.__init__(self, owner)
class Submarine(GamePiece):
  name = 'submarine'
  def __init__(self, owner):
    self.size = 1
    GamePiece.__init__(self, owner)
class NoShip(GamePiece, Singleton):
  name = 'noship'
  def __init__(self):
    self.size = 0
    self.owner = None
    self._squares = []

########NEW FILE########
__FILENAME__ = Point
class Point:
  def __init__(self, x, y):
    self.x = x
    self.y = y

  def distance(self, other):
    return abs(self.x - other.x) + abs(self.y - other.y)

  # Whether to points are in the same line. We use this function to determine
  # whether endpoints are legitimate for placing a ship.
  def inLine(self, other):
    return self.x == other.x or self.y == other.y

########NEW FILE########
__FILENAME__ = Square
import JeevesLib
from fast.ProtectedRef import ProtectedRef, UpdateResult
from GamePiece import NoShip
from sourcetrans.macro_module import macros, jeeves

@jeeves
class Square:
  def __init__(self, owner):
    self.owner = owner
    self.shipRef = ProtectedRef(NoShip()
      # Policy for updating: must be owner and there can't be a ship there
      # already.
      , lambda ship: lambda ic: ship == NoShip() and self.isOwner(ic)
      , None)
    self.hasBombRef = ProtectedRef(None
      , lambda _bomb: lambda ic:
          self.hasTurn(ic) and self.allShipsPlaced(ic) and
            not self.gameOver(ic)
      , None)

  def isOwner(self, ctxt):
    return ctxt.user == self.owner
  def hasTurn(self, ctxt):
    return ctxt.game.hasTurn(ctxt.user)
  def allShipsPlaced(self, ctxt):
    return ctxt.game.allShipsPlaced()
  def gameOver(self, ctxt):
    return ctxt.game.gameOver()
  def mkShipSecret(self, ship):
    a = JeevesLib.mkLabel("ship")
    JeevesLib.restrict(a
      , lambda ctxt:
          self.hasBomb() or self.isOwner(ctxt) or self.gameOver(ctxt));
    return JeevesLib.mkSensitive(a, ship, NoShip())

  # Returns whether updating a square's ship reference succeeded.
  def updateShip(self, ctxt, ship):
    return self.shipRef.update(ctxt, ctxt, self.mkShipSecret(ship)) == UpdateResult.Success
  def hasShip(self):
    return not self.shipRef.v == NoShip()
  def getShip(self):
    return self.shipRef.v

  def bomb(self, ctxt, bomb):
    r = self.hasBombRef.update(ctxt, ctxt, bomb)
    print 'moooooooooo', r
    return r == UpdateResult.Success
  
  def hasBomb(self):
    return not (self.hasBombRef.v == None)

########NEW FILE########
__FILENAME__ = testBattleship
import macropy.activate
import JeevesLib
from smt.Z3 import *
import unittest
from Battleship import Game
from Board import Board
from Bomb import Bomb
from GameContext import GameContext
from GamePiece import Carrier, Battleship, Cruiser, Destroyer, Submarine, NoShip
from Point import Point
from User import User

class TestBattleship(unittest.TestCase):
  def setUp(self):
    JeevesLib.init()

    self.alice = User(0, "Alice")
    self.aliceBoard = Board(self.alice)
    self.aliceBomb = Bomb(self.alice)

    self.bob = User(1, "Bob")
    self.bobBoard = Board(self.bob)
    self.bobBomb = Bomb(self.bob)

    self.game = Game({self.alice: self.aliceBoard, self.bob: self.bobBoard})
    self.aliceCtxt = GameContext(self.alice, self.game)
    self.bobCtxt =  GameContext(self.bob, self.game)

  def can_only_place_piece_on_own_board(self):
    # Bob cannot put pieces on Alice's board.
    self.assertFalse(
      self.aliceBoard.placeShip(
        self.bobCtxt, Battleship(self.bob), Point(1, 0), Point(1, 4)))

  def test_placing_pieces(self):
    self.assertTrue(
      self.aliceBoard.placeShip(
        self.aliceCtxt, Carrier(self.alice), Point(0, 0), Point(0, 5)))
    
    # Cannot place the same piece again.
    self.assertFalse(
      self.aliceBoard.placeShip(
        self.aliceCtxt, Carrier(self.alice), Point(0,0), Point(0, 5)))

    # Cannot place another piece at the same location.
    self.assertFalse(
      self.aliceBoard.placeShip(
        self.aliceCtxt, Battleship(self.alice), Point(0, 0), Point(0, 4)))
    
    self.assertFalse(
      JeevesLib.concretize(self.aliceCtxt, self.aliceBoard.allPlaced()))
    self.assertFalse(
      JeevesLib.concretize(self.bobCtxt, self.aliceBoard.allPlaced()))

    # Cannot bomb until all pieces placed.
    self.assertFalse(
      self.aliceBoard.getSquare(0, 0).bomb(self.bobCtxt, self.bobBomb))

    # Putting the rest of Alice's pieces...
    self.assertTrue(    
      self.aliceBoard.placeShip(
        self.aliceCtxt, Battleship(self.alice), Point(1, 0), Point(1, 4)))
    
    self.assertTrue(
      self.aliceBoard.placeShip(
        self.aliceCtxt, Cruiser(self.alice), Point(2, 0), Point(2, 3)))
    
    self.assertTrue(
      self.aliceBoard.placeShip(
        self.aliceCtxt, Destroyer(self.alice), Point(3, 0), Point(3, 2)))
    
    self.assertTrue(
      self.aliceBoard.placeShip(
        self.aliceCtxt, Destroyer(self.alice), Point(4, 0), Point(4, 2)))
    
    self.assertTrue(
      self.aliceBoard.placeShip(
        self.aliceCtxt, Submarine(self.alice), Point(5, 0), Point(5, 1)))
    
    self.assertTrue(
      self.aliceBoard.placeShip(
        self.aliceCtxt, Submarine(self.alice), Point(5, 1), Point(5, 2)))

    # Cannot put more pieces than are available.
    self.assertFalse(
      self.aliceBoard.placeShip(
        self.aliceCtxt, Submarine(self.alice), Point(6,0), Point(6, 1)))

    #  Putting Bob's pieces... 
    self.assertTrue(
      self.bobBoard.placeShip(
        self.bobCtxt, Carrier(self.bob), Point(0, 0), Point(0, 5)))
    self.assertTrue(
      self.bobBoard.placeShip(
        self.bobCtxt, Battleship(self.bob), Point(1, 0), Point(1, 4)))
    self.assertTrue(
      self.bobBoard.placeShip(
        self.bobCtxt, Cruiser(self.bob), Point(2, 0), Point(2, 3)))
    self.assertTrue(
      self.bobBoard.placeShip(
        self.bobCtxt, Destroyer(self.bob), Point(3, 0), Point(3, 2)))
    self.assertTrue(
      self.bobBoard.placeShip(
        self.bobCtxt, Destroyer(self.bob), Point(4, 0), Point(4, 2)))
    self.assertTrue(
      self.bobBoard.placeShip(
        self.bobCtxt, Submarine(self.bob), Point(5, 0), Point(5, 1)))
    self.assertTrue(
      self.bobBoard.placeShip(
        self.bobCtxt, Submarine(self.bob), Point(5, 1), Point(5, 2)))

    # Can bomb a piece with no ship.
    self.assertEqual(NoShip()
      , JeevesLib.concretize(
          self.aliceCtxt, self.game.bomb(self.aliceCtxt, self.bob, 9, 9)))

    # Can bomb a piece with some ship.
    self.assertEqual(Carrier(self.alice)
      , JeevesLib.concretize(
          self.aliceCtxt, self.game.bomb(self.bobCtxt, self.alice, 0, 0)))

    self.assertEqual(NoShip()
      , JeevesLib.concretize(
          self.bobCtxt, self.game.bomb(self.bobCtxt, self.alice, 0, 0)))

    self.assertEqual(Carrier(self.alice)
      , JeevesLib.concretize(
          self.bobCtxt, self.aliceBoard.getSquare(0, 0).getShip()))
    self.assertEqual(Carrier(self.alice)
      , JeevesLib.concretize(
          self.bobCtxt, self.aliceBoard.getSquare(0, 3).getShip()))

    self.assertEqual(NoShip()
      , JeevesLib.concretize(
          self.aliceCtxt, self.bobBoard.getSquare(0, 0).getShip()))
    
    self.assertEqual(Carrier(self.bob)
      , JeevesLib.concretize(
          self.aliceCtxt, self.game.bomb(self.aliceCtxt, self.bob, 0, 0)))
    self.assertEqual(Battleship(self.alice)
      , JeevesLib.concretize(
          self.bobCtxt, self.game.bomb(self.bobCtxt, self.alice, 1, 0)))
    self.assertEqual(Battleship(self.bob)
      , JeevesLib.concretize(
          self.aliceCtxt, self.game.bomb(self.aliceCtxt, self.bob, 1, 0)))
    self.assertEqual(Cruiser(self.alice)
      , JeevesLib.concretize(
          self.bobCtxt, self.game.bomb(self.bobCtxt, self.alice, 2, 0)))
    self.assertEqual(Cruiser(self.bob)
      , JeevesLib.concretize(
          self.aliceCtxt, self.game.bomb(self.aliceCtxt, self.bob, 2, 0)))
    self.assertEqual(Destroyer(self.alice)
      , JeevesLib.concretize(
          self.bobCtxt, self.game.bomb(self.bobCtxt, self.alice, 3, 0)))
    self.assertEqual(Destroyer(self.bob)
      , JeevesLib.concretize(
          self.aliceCtxt, self.game.bomb(self.aliceCtxt, self.bob, 3, 0)))
    self.assertEqual(Destroyer(self.alice)
      , JeevesLib.concretize(
        self.bobCtxt, self.game.bomb(self.bobCtxt, self.alice, 4, 0)))
    self.assertEqual(Destroyer(self.bob)
      , JeevesLib.concretize(
        self.aliceCtxt, self.game.bomb(self.aliceCtxt, self.bob, 4, 0)))
    self.assertEqual(Submarine(self.alice)
      , JeevesLib.concretize(
        self.bobCtxt, self.game.bomb(self.bobCtxt, self.alice, 5, 0)))
    self.assertEqual(Submarine(self.bob)
      , JeevesLib.concretize(
        self.aliceCtxt, self.game.bomb(self.aliceCtxt, self.bob, 5, 0)))
    self.assertTrue(self.game.gameOver())

    self.assertEqual(NoShip()
      , JeevesLib.concretize(
        self.aliceCtxt, self.game.bomb(self.aliceCtxt, self.bob, 5, 1)))
    
    self.assertEqual(Submarine(self.bob)
      , JeevesLib.concretize(
        self.aliceCtxt, self.bobBoard.getSquare(5, 1).getShip()))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = User
import JeevesLib
from sourcetrans.macro_module import macros, jeeves

@jeeves
class User:
  def __init__(self, userId, name=""):
    self.userId = userId
    self.name = name
  def __eq__(self, other):
    return self.userId == other.userId
  def __hash__(self):
    return self.userId

########NEW FILE########
__FILENAME__ = testContextual
import JeevesLib
from smt.Z3 import *
import unittest
from macropy.case_classes import macros, enum

import JeevesLib
from sourcetrans.macro_module import macros, jeeves

@enum
class Location:
  Home, Work, Other

class User:
  def __init__(self, userId):
    self.userId = userId

class Context:
  def __init__(self, user, location):
    self.user = user
    self.location = location

class TestContextual(unittest.TestCase):
  def setUp(self):
    # Need to initialize the JeevesLib environment.
    JeevesLib.init()

    self.alice = User(0)
    self.bob = User(1)

  @jeeves
  def testContextual(self):
    a = JeevesLib.mkLabel()
    JeevesLib.restrict(a
      , lambda oc: oc.user == self.alice or oc.location == Location.Work)
    xS = JeevesLib.mkSensitive(a, 42, 0)
    self.assertEqual(
        JeevesLib.concretize(Context(self.alice, Location.Work), xS)
      , 42)
    self.assertEqual(
        JeevesLib.concretize(Context(self.alice, Location.Home), xS)
      , 42)
    self.assertEqual(
        JeevesLib.concretize(Context(self.bob, Location.Work), xS)
      , 42)
    self.assertEqual(
        JeevesLib.concretize(Context(self.bob, Location.Home), xS)
      , 0)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = testFunctions
import JeevesLib
import unittest

from fast.ProtectedRef import ProtectedRef, UpdateResult
from sourcetrans.macro_module import macros, jeeves

class User:
  def __init__(self, userId):
    self.userId = userId

# Test that once values are sanitized, they may flow to the output, but not
# before.
class TestFunctions(unittest.TestCase):
  def setUp(self):
    # Need to initialize the JeevesLib environment.
    JeevesLib.init()

    self.alice = User(0)
    self.bob = User(1)

  # If the input does not do anything bad to our data structure, then we
  # allow it to pass.
  @jeeves
  def testBehavioralGood(self):
    touchedBadData = False
    def f(x):
      return x+1
    x = ProtectedRef(lambda x: x, None
      , lambda _this: lambda ic: lambda touchedBad: not touchedBad)
    self.assertEqual(JeevesLib.concretize(None, (x.v)(1)), 1)
    assert x.update(None, None, f) == UpdateResult.Unknown
    self.assertEqual(JeevesLib.concretize(None, (x.v)(1)), 2)

  @jeeves
  def testBehavioralBad(self):
    touchedBadData = False
    def f(x):
      global touchedBadData
      touchedBadData = True
      return x+1
    x = ProtectedRef(lambda x: x, None
      , lambda _this: lambda ic: lambda oc: not touchedBadData)
    self.assertEqual(JeevesLib.concretize(None, (x.v)(1)), 1)
    assert x.update(None, None, f) == UpdateResult.Unknown
    self.assertEqual(JeevesLib.concretize(None, (x.v)(1)), 1)

  # TODO: Users can endorse functions.

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = testSanitization
import JeevesLib
import unittest

from fast.ProtectedRef import ProtectedRef, UpdateResult
import JeevesLib
from sourcetrans.macro_module import macros, jeeves

class User:
  def __init__(self, userId):
    self.userId = userId

# Test that once values are sanitized, they may flow to the output, but not
# before.
class TestSanitization(unittest.TestCase):
  def setUp(self):
    # Need to initialize the JeevesLib environment.
    JeevesLib.init()

    self.alice = User(0)
    self.bob = User(1)

  # If the input does not do anything bad to our data structure, then we
  # allow it to pass.
  @jeeves
  def testBehavioralSanitizationGood(self):
    touchedBadData = False
    def f(s):
      global touchedBadData
      if s == "bad":
        touchedBadData = True
      return s
    x = ProtectedRef("dunno", None
      , lambda _this: lambda ic: lambda oc: not touchedBadData)
    self.assertEqual(JeevesLib.concretize(None, x.v), "dunno")
    assert x.update(None, None, f("good")) == UpdateResult.Unknown
    self.assertEqual(JeevesLib.concretize(None, x.v), "good")

  @jeeves
  def testBehavioralSanitizationBad(self):
    touchedBadData = False
    def f(s):
      global touchedBadData
      if s == "bad":
        touchedBadData = True
      return s
    x = ProtectedRef("dunno", None
      , lambda _this: lambda ic: lambda oc: not touchedBadData)
    assert x.update(None, None, f("bad")) == UpdateResult.Unknown
    print touchedBadData
    self.assertEqual(JeevesLib.concretize(None, x.v), "dunno")


  def testEndorseSanitizeFunction(self):
    pass
    # TODO: Need a way of associating sanitization function with some sort of
    # endorsement, probably with facet rewriting.

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = Fitness
'''
Fitness example for Jeeves with confidentiality policies.
'''
import datetime
import operator

import JeevesLib
from sourcetrans.macro_module import macros, jeeves

class InternalError(Exception):
  def __init__(self, message):
    self.message = message

# Definitions of locations.
@jeeves
class User:
  def __init__(self, userId):
    self.userId = userId
    self.activity = {}

  def addActivity(self, activity):
    # Confidentiality policy: 
    self.activity[datetime.date] = activity

  # POLICY: If there are more than k people who have similar profile like Jean,
  # then uses avgActivityLevelJean as the real value to compute the group
  # average; else use the existing group average avgActivityLevelinstead. This
  # means that adding Jean's value avgActivityLevelJean will not change the
  # group's average and will not be picked out as outliner. 
  def getAverageActivityLevel(self):
    a = JeevesLib.mkLabel('activity_label')
 
    # Compute average activity level.
    activityValues = self.activity.values()
    # TODO: We really want this to be the average activity level of the
    # *output channel* and not the current activity level...
    genericAverage = 3
    averageActivity = reduce(operator.add, activityValues, 0) / len(activityValues) if len(activityValues) > 0 else genericAverage
    # Can see the average activity level if there are at least 3 with averages
    # within 0.2.
    JeevesLib.restrict(a
      , lambda oc: oc.atLeastKSimilar(averageActivity, 2, 0.2))
    activityLevel = JeevesLib.mkSensitive(a, averageActivity, genericAverage)
    return activityLevel

# TODO: Is this just the view context?
@jeeves
class UserNetwork:
  def __init__(self, users=[]):
    self.users = users

  def getAverageActivityLevel(self):
    userSum = reduce(lambda acc, u: acc + u.averageActivityLevel(), self.users)
    return userSum / len(self.users)

  def atLeastKSimilar(self, avg, k, delta):
    count = 0
    for user in self.users:
      userAvg = user.getAverageActivityLevel()
      if (avg - delta) < userAvg and userAvg < (avg + delta):
        count += 1
    return count >= k

########NEW FILE########
__FILENAME__ = testFitness
from smt.Z3 import *
import unittest

from Fitness import User, UserNetwork
import JeevesLib

class TestFitness(unittest.TestCase):
  def setUp(self):
    # Need to initialize the JeevesLib environment.
    JeevesLib.init()

    self.alice = User(0)
    self.bob = User(1)
    self.carol = User(2)

    self.genericAverage = 3
    self.users = UserNetwork([self.alice, self.bob, self.carol])

  '''
  def testUserAverage(self):
    self.alice.addActivity(1)
    self.alice.addActivity(1)
    self.assertEqual(JeevesLib.concretize(self.users, self.alice.getAverageActivityLevel()))
  '''

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = Auth
import JeevesLib
from sourcetrans.macro_module import macros, jeeves

'''
TODO:
- Think about what Jeeves policies are good for here.
- Think about whether there is even any point of having credentials if we can
  just use Jeeves.
- Add @jeeves to things.
'''

class InternalAuthError(Exception):
  pass

class Cred:
  pass

class MkCred(Cred):
  def __init__(self, prin):
    self.prin = prin
  def __eq__(self, other):
    return self.prin == other.prin
  def __str__(self):
    return "Cred(" + self.prin.__str__() + ")"

class Prin:
  passwords = { 'Alice': 'AlicePW' }

  def login(self, pw):
    if isinstance(self, U):
      actualPwd = Prin.passwords[self.name]
      if actualPwd == pw:
        return MkCred(self)
      else:
        return None
    elif isinstance(self, Admin):
      if pw == "AdminPW":
        return MkCred(self)
      else:
        return None
    else:
      raise InternalAuthError

class U(Prin):
  def __init__(self, name):
    self.name = name
  def __eq__(self, other):
    return self.name == other.name
  def __str__(self):
    return self.name
class Admin(Prin):
  def __str__(self):
    return "Admin"
  def __eq__(self, other):
    return isinstance(other, Admin)

########NEW FILE########
__FILENAME__ = ExternDB
def findRecordsByKeyword(kw):
  # Return a list of dbrecs.
  pass

# Returns a integer (ID?).
def persistRecord(r):
  pass

# Returns a string serialization of the auth state.
def readAuthState():
  pass

########NEW FILE########
__FILENAME__ = ExternNetwork
'''
This is supposed to interface with the external network stuff.
'''
class Request:
  class GetPatientRecords:
    def __init__(self, kw):
      self.kw = kw
  class GetRecordContents:
    def __init__(self, record):
      self.record = record
  class ActivateRole:
    def __init__(self, role):
      self.role = role
  class ConsentToTreatment:
    def __init__(self, prin):
      self.prin = prin

def nextRequest():
  # Return a principle, a credential, and a request.
  pass

class Response:
  class RecordList:
    def __init__(self, records):
      self.records = records
    def __eq__(self, other):
      return self.records == other.records
  class RecordContents:
    def __init__(date, v, annots):
      self.date = date
      self.v = v
      self.annots = annots
    def __eq__(self, other):
      return (self.date == other.date and self.v == other.v and
        self.annots == self.annots)
  class Denied:
    def __init__(self, s):
      self.s = s
    def __eq__(self, other):
      return self.s == other.s
  class Ok:
    def __eq__(self, other):
      return isinstance(other, Ok)

def respond(response):
  pass

########NEW FILE########
__FILENAME__ = HealthDB
import ExternDB
from PolicyTypes import Sign

'''
Data model.
'''
class Subject:
  pass
class General(Subject):
  pass
class Psychiatric(Subject):
  pass
class HIV(Subject):
  pass
class Other(Subject):
  def __init__(self, ty):
    self.ty = ty

class Annotation:
  def __init__(self, author, date, contents):
    self.author = author
    self.date = date
    self.contents = contents

class Contents:
  def __init__(self, d, v, a):
    self.d = d
    self.v = v
    self.a = a

class Record:
  def __init__(self, recid, patient, author, subject, privateContents):
    self.recid = recid
    self.patient = patient # Prin
    self.author = author
    self.subject = subject
    self.privateContents = privateContents		 
              
''' 
Signatures of external utility functions
'''
class Extern:
  # Returns a record.
  def parseDbRecord(dbrecord):
    pass
  def unparseRecord(record):
    pass
  def parseAuthstate(stateStr):
    pass

'''
Public API to database.
'''
class DatabaseAPI:
  # Returns a record and state. 
  # s is a permit; tok is an authstate
  def searchByKW(prin, cred, kw, s, tok):
    dbrecs = ExternDB.findRecordByKeyword(kw)
    recs = map(ExternDB.parseDBRecord, dbrecs)
    return recs, tok

  '''
  val read_contents: p:prin -> cred p -> r:record -> 
                     s:permit p (Read r.recid) -> StateIs s -> 
                     (date * string * annots * StateIs s)
  '''
  def readContents(prin, cred, r, s, tok):
    pc = r.privateContents
    return (pc.d, pc.c, pc.a, tok)

'''
Public API for authorization-related functions.
'''
class AuthAPI:
  def activateRole(p, c, r, s, tok):
    # TODO: Define ActiveRole.
    s.append(ActiveRole(p, r))
    return (s, Sign(s))

  def consentToTreatment(patient, cred, doc, s, tok):
    s.addElt
    return s, Sign(s)
  
  '''
  val annotate_record: p:prin -> cred p -> r:record -> a:annotation ->
                       s:permit p (Annotate r.recid) -> StateIs s -> StateIs s
  '''
  def annotateRecord(p, c, r, a, s, tok):                    
    r.privateContents.a.append(a)
    ExternDP.persistRecord(unparseRec(r))
    return tok

########NEW FILE########
__FILENAME__ = HealthMgr
import ExternNetwork
import HealthDB
from ExternNetwork import Request, Response
from HealthDB import AuthAPI
from PolicyTypes import Attribute, RoleType

'''
Event loop. Runs everything by processing requests from the network. Each
iteration of the loop gets the next request from the network and returns a
response.
'''
# TODO: Jeeves-ify this.
# @jeeves
def evtLoop(s, tok):
  # Each request comes with a principal, some credentials, and the body of the
  # request. (We'll just be mocking the request for now...)
  (p, cred, request) = ExternNetwork.nextRequest()
  # If this is a request for patient records
  if isinstance(request, Request.GetPatientRecords):
    test = (PolicyTypes.checkIn(PolicyTypes.ActiveRole(p, RoleType.Doctor), s)
            or PolicyTypes.checkIn(Attribute.ActiveRole(p, RoleType.Nurse), s)
            or PolicyTypes.checkIn(Attribute.ActiveRole(
                p, RoleType.InsuranceProvider), s))
    if test:
      records, tokNew = searchByKw(p, cred, kw, s, tok)
      ExternNetwork.respond(Response.RecordList(records))
      evtLoop(s, tokNew)
    else:
      ExternNetwork.respond(Response.Denied("Sorry, insufficient privilege"))
      evtLoop(s, tok)
  elif isinstance(request, Request.GetRecordContents):
    r = request.record   
    test = (p == r.author or
            ((p == r.patient) and
              PolicyTypes.checkIn(
                Attribute.ActiveRole(p, RoleType.Patient), s)) or
            (PolicyTypes.checkIn(Attribute.IsTreating(p, r.patient), s) and
              ((isinstance(r.subject, HealthDB.Psychiatric) and
                  PolicyTypes.checkIn(
                    Attribute.ActiveRole(p, RoleType.Psychiatrist), s)) or
               ((not isinstance(r.subject, HealthDB.Psychiatric) and 
                  PolicyTypes.checkIn(
                    Attribute.ActiveRole(p, RoleType.Doctor), s))))))
    if test:
      d, con, al, tokNew = HealthDB.readContents(p, cred, r, s, tok)
      ExternNetwork.respond(Response.RecordContents(d, con, al))
      evtloop(s, tokNew)
    else:
      ExternNetwork.respond(Response.Denied("Sorry, insufficient privilege"))
      evtLoop(s, tok)
  if isinstance(request, Request.ActivateRole):
    r = request.role   
    test = PolicyTypes.checkIn(Attribute.CanBeInRole(p, r), s)
    if test:
      sNew, tokNew = HealthDB.activateRole(p, cred, r, s, tok)
      ExternNetwork.respond(ExternNework.Ok)
      evtLoop(sNew, tokNew)
    else:
      ExternNetwork.respond(
        ExternNetwork.Denied("Sorry, insufficient privilege"))
      evtloop(s, tok)
  if isinstance(request, Request.ConsentToTreatment):
    doc = request.prin
    test = (PolicyTypes.checkIn(Attribute.ActiveRole(p, RoleType.Patient), s)
              and policyTypes.checkIn(Attribute.CanBeInRole(doc, Doctor), s))
    if test:
      sNew, tokNew = AuthAPI.consentToTreatment(p, cred, doc, s, tok)
      ExternNetwork.respond(Response.Ok)
      evtLoop(sNew, tokNew)
    else:
      ExternNetwork.respond(Response.Denied("Sorry, insufficient privilege"))
      evtLoop(s, tok)

########NEW FILE########
__FILENAME__ = Policy
'''
assume docCanRead: forall (p:prin) (r:record) (s:authstate).
  (In (ActiveRole p Doctor) s) &&
  (In (IsTreating p r.patient) s) &&
  (not (r.subject = Psychiatric)) =>
  GrantedIn (Permit p (Read r.recid)) s

assume psychCanRead: forall (p:prin) (r:record) (s:authstate).
  (In (ActiveRole p Psychiatrist) s) &&
  (In (IsTreating p r.patient) s) &&
  (r.subject = Psychiatric) =>
  GrantedIn (Permit p (Read r.recid)) s

assume patCanConsent: forall (pat:prin) (doc:prin) (s:authstate).
  In (ActiveRole pat Patient) s && In (CanBeInRole doc Doctor) s =>
  GrantedIn (Permit pat (ConsentTo doc)) s

assume pCanActivate: forall (p:prin) (r:role) (s:authstate).
  In (CanBeInRole p r) s => GrantedIn (Permit p (Activate r)) s

assume pCanSearchByKW: forall (p:prin) (s:authstate).
  (In (ActiveRole p Doctor) s ||
   In (ActiveRole p Nurse) s ||
   In (ActiveRole p InsuranceProvider) s) =>
  GrantedIn (Permit p Search) s

assume authorCanRead: forall (p:prin) (r:record) (s:authstate).
  (p=r.author) => GrantedIn (Permit p (Read r.recid)) s

assume patCanRead: forall (p:prin) (r:record) (s:authstate).
  (p=r.patient) && In (ActiveRole p Patient) s =>
  GrantedIn (Permit p (Read r.recid)) s
'''

########NEW FILE########
__FILENAME__ = PolicyTypes
from macropy.case_classes import macros, enum

@enum
class RoleType:
  Patient, Doctor, Psychiatrist, Nurse, Pharmacist, Nurse, Pharmacist
  InsuranceProvider

class Action:
  class Read:
    def __init__(self, v):
      self.v = v
  class Write:
    def __init__(self, v):
      self.v = v
  class Annotate:
    def __init__(self, v):
      self.v = v
  class Delete:
    def __init__(self, v):
      self.v = v
  class Search:
    pass
  class ConsentTo:
    def __init__(self, p):
      self.p = p
  class Activate:
    def __init__(self, r):
      self.r = r

# This is a kind of permission.
class Permit:
  def __init__(self, prin, action):
    self.prin = prin
    self.action = action

class Attribute:
  class CanBeInRole:
    def __init__(self, prin, role):
      self.prin = prin
      self.role = role
    def __eq__(self, other):
      return self.prin == other.prin and self.role == other.role
  class ActiveRole:
    def __init__(self, prin, role):
      self.prin = prin
      self.role = role
    def __eq__(self, other):
      return self.prin == other.prin and self.role == other.role
  class IsTreating:
    def __init__(self, p1, p2):
      self.p1 = p1
      self.p2 = p2
      return self.p1 == other.p1 and self.p2 == other.p2

class AuthState:
  def __init__(self):
    self.attribs = []
  # Add attribute etc.
  def __contains__(self, item):
    item in self.attribs
  def addElt(self, elt):
    self.attribs.append(elt)

'''
n :: attribute => authstate => P
assume forall (a:attribute) (tl:authstate). In a (ACons a tl)
assume forall (a:attribute) (b:attribute) (tl:authstate). In a tl => In a (ACons b tl)
assume forall (a:attribute). (not (In a ANil))
assume forall (a:attribute) (b:attribute) (tl:authstate). ((not (In a tl)) && (not (a=b)))
  => (not (In a (ACons b tl)))
'''
class Sign:
  def __init__(self, authstate):
    self.authstate = authstate
  def __eq__(self, other):
    return self.authstate == other.authstate

'''
type GrantedIn :: permission => authstate => P
(* Some commonly used type abbreviations *)
type permit (p:prin) (a:action) = s:authstate { GrantedIn (Permit p a) s}
type authcontains (a:attribute) = x:authstate { In a x}

(* prenex and implies rewritten *)
type extendedstate (s:authstate) (a:attribute) =
    x:authstate { (forall (b:attribute). (In a x) && ((not (In b s)) || (In b x)))}

assume Skolemize_extendedstate:
  forall (s:authstate) (a:attribute) (x:authstate).
    ((not (forall (b:attribute).     ((In a x) && ((not (In b s)) || (In b x)))))
       => (exists (b:attribute). not ((In a x) && ((not (In b s)) || (In b x)))))
'''

'''
Checks if 
'''
def checkIn(a, authState):
  return a in authState

########NEW FILE########
__FILENAME__ = testHealthWeb
import JeevesLib
import unittest
import mock
# from mock import MagicMock
from mock import patch

import Auth
import ExternNetwork
from ExternNetwork import Request, Response
import HealthMgr

class TestHealthWeb(unittest.TestCase):
  def setUp(self):
    JeevesLib.init()
    # x = Auth.Test()
    # self.auth = Authentication()
    self.alicePrin = Auth.U("Alice")
    self.adminPrin = Auth.Admin()

  '''
  Test Auth.
  '''
  def testEqualities(self):
    self.assertEqual(Auth.U("Alice"), Auth.U("Alice"))
    self.assertEqual(Auth.MkCred(self.alicePrin), Auth.MkCred(self.alicePrin))
    self.assertEqual(Auth.Admin(), Auth.Admin())
    self.assertNotEqual(Auth.U("Alice"), Auth.Admin())

  def testLogin(self):
    self.assertEqual(
      self.alicePrin.login("AlicePW"), Auth.MkCred(self.alicePrin))
    self.assertEqual(self.alicePrin.login("xyz"), None)
    self.assertEqual(self.adminPrin.login("AdminPW"), Auth.MkCred(self.adminPrin))

  '''
  Test that we're mocking things up correctly...
  '''
  '''
  def testMockNetwork(self):
    ExternNetwork.request = mock.Mock(return_value=[])
    self.assertEqual(ExternNetwork.request(), [])

    ExternNetwork.respond = mock.Mock()
    ExternNetwork.respond(Response.Ok)
    ExternNetwork.respond.assert_called_with(Response.Ok)
  '''

  def testEvlLoop(self):
    pass #HealthMgr.evt

########NEW FILE########
__FILENAME__ = Location
'''
Location example for Jeeves with confidentiality policies.
'''
from abc import ABCMeta, abstractmethod
from macropy.case_classes import macros, enum

import JeevesLib
from sourcetrans.macro_module import macros, jeeves


class InternalError(Exception):
  def __init__(self, message):
    self.message = message

# Definitions of locations.
@jeeves
class Location:
  __metaclass__ = ABCMeta
  @abstractmethod
  def isIn(self, loc):
    return False
  @abstractmethod 
  def isNear(self, loc, radius=50.0):
    return False
class GPS(Location):
  def __init__(self, latitude, longitude, city=None):
    self.latitude = latitude
    self.longitude = longitude
    self.city = city
  def __eq__(self, other):
    return (isinstance(other, GPS) and (self.latitude == other.latitude)
      and (self.longitude == other.longitude))
  def isIn(self, loc):
    if isinstance(loc, GPS):
      return self == loc
    elif isinstance(loc, City):
      return self.city == loc
    elif isinstance(loc, Country):
      return self.city.country == loc
    else:
      raise InternalError("A location must be a GPS, City, or Country.")
class City(Location):
  def __init__(self, city, country):
    self.city = city
    self.country = country
  def __eq__(self, other):
    return (isinstance(other, City) and (self.city == other.city)
      and (self.country == other.country))
  def isIn(self, loc):
    if isinstance(loc, GPS):
      return False
    elif isinstance(loc, City):
      return self == loc
    elif isinstance(loc, Country):
      return self.country == loc
    else:
      raise InternalError("A location must be a GPS, City, or Country.")
class Country(Location):
  def __init__(self, name):
    self.name = name
  def __eq__(self, other):
    return isinstance(other, Country) and self.name == other.name
  def isIn(self, loc):
    if isinstance(loc, GPS):
      return False
    elif isinstance(loc, City):
      return False
    elif isinstance(loc, Country):
      return self == loc
    else:
      raise InternalError("A location must be a GPS, City, or Country.")

# Users have a user ID and a location.
@jeeves
class User:
  def __init__(self, userId, location, friends=[]):
    self.userId = userId
    self.location = location
    self.friends = list(friends)
  def addFriend(self, friend):
    self.friends.append(friend)
  def isFriends(self, other):
    return JeevesLib.jhas(self.friends, other)
  def prettyPrint(self):
    return str(self.userId)

class LocationNetwork:
  def __init__(self, users=[]):
    self.users = users

  @jeeves
  def countUsersInLocation(self, loc):
    sum = 0
    for user in self.users:
      if user.location.isIn(loc):
        sum += 1
    return sum

########NEW FILE########
__FILENAME__ = testLocation
import JeevesLib
from smt.Z3 import *
import unittest
from Location import Location, GPS, City, Country, User, LocationNetwork
import JeevesLib

class TestLocation(unittest.TestCase):
  def setUp(self):
    # Need to initialize the JeevesLib environment.
    JeevesLib.init()

    # Define some locations.
    self.countryUSA = Country("USA")
    self.cityCambridge = City("Cambridge", self.countryUSA)
    self.gpsMIT = GPS(40.589063, -74.159178, self.cityCambridge) 

    # Define some users with their locations.
    # Alice's location is restricted to Alice and her friends.
    aliceLabel = JeevesLib.mkLabel()
    JeevesLib.restrict(aliceLabel
      , lambda oc: owner == oc or owner.isFriends(oc))
    self.alice = User(0
      , JeevesLib.mkSensitive(aliceLabel, self.gpsMIT, self.cityCambridge))
    
    # Bob's location has no policies.
    self.bob = User(1, self.cityCambridge)

    
    self.carol = User(2, self.countryUSA)

    self.alice.addFriend(self.bob)
    self.bob.addFriend(self.alice)

  # This makes sure the isIn function works properly.
  def testIsin(self):
    self.assertTrue(self.cityCambridge.isIn(self.cityCambridge))
    self.assertTrue(self.cityCambridge.isIn(self.countryUSA))
    self.assertTrue(self.gpsMIT.isIn(self.gpsMIT))
    self.assertTrue(self.gpsMIT.isIn(self.countryUSA))
    self.assertFalse(self.cityCambridge.isIn(self.gpsMIT))
    self.assertFalse(self.countryUSA.isIn(self.gpsMIT))
    self.assertFalse(self.countryUSA.isIn(self.cityCambridge))

  # This makes sure the isFriends function works properly.
  def testIsFriends(self):
    self.assertTrue(
      JeevesLib.concretize(self.alice, self.alice.isFriends(self.bob)))
    self.assertTrue(
      JeevesLib.concretize(self.alice, self.bob.isFriends(self.alice)))
    self.assertFalse(
      JeevesLib.concretize(self.alice, self.alice.isFriends(self.carol)))
    self.assertFalse(
      JeevesLib.concretize(self.alice, self.carol.isFriends(self.alice)))

  # This makes sure locations can only be viewed if they are supposed to be
  # viewed.
  def testViewLocation(self):
    # Alice and Bob can see the high-confidentiality version of Alice's
    # location, but Carol cannot.
    self.assertEqual(JeevesLib.concretize(self.alice, self.alice.location)
      , self.gpsMIT)
    self.assertEqual(JeevesLib.concretize(self.bob, self.alice.location)
      , self.gpsMIT)
    self.assertEqual(JeevesLib.concretize(self.carol, self.alice.location)
      , self.cityCambridge)

  def testCountUsersInLocation(self):
    # Only Alice and Bob can see Alice's "high" location of S
    locNetwork = LocationNetwork([self.alice, self.bob, self.carol])
    usersInStata = locNetwork.countUsersInLocation(self.gpsMIT)
    self.assertEqual(JeevesLib.concretize(self.alice, usersInStata), 1)
    self.assertEqual(JeevesLib.concretize(self.bob, usersInStata), 1)
    self.assertEqual(JeevesLib.concretize(self.carol, usersInStata), 0)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = Location
'''
Location example for Jeeves with confidentiality policies.
'''
from abc import ABCMeta, abstractmethod

from fast.ProtectedRef import ProtectedRef, UpdateResult
import JeevesLib
from sourcetrans.macro_module import macros, jeeves

class InternalError(Exception):
  def __init__(self, message):
    self.message = message

# Definitions of locations.
@jeeves
class Location:
  __metaclass__ = ABCMeta
  @abstractmethod
  def isIn(self, loc):
    return False
class GPS(Location):
  def __init__(self, latitude, longitude, city=None):
    self.latitude = latitude
    self.longitude = longitude
    self.city = city
  def __eq__(self, other):
    return (isinstance(other, GPS) and (self.latitude == other.latitude)
      and (self.longitude == other.longitude))
  def isIn(self, loc):
    if isinstance(loc, GPS):
      return self == loc
    elif isinstance(loc, City):
      return self.city == loc
    elif isinstance(loc, Country):
      return self.city.country == loc
    else:
      return False
class City(Location):
  def __init__(self, city, country):
    self.city = city
    self.country = country
  def __eq__(self, other):
    return (isinstance(other, City) and (self.city == other.city)
      and (self.country == other.country))
  def isIn(self, loc):
    if isinstance(loc, GPS):
      return False
    elif isinstance(loc, City):
      return self == loc
    elif isinstance(loc, Country):
      return self.country == loc
    else:
      return False
class Country(Location):
  def __init__(self, name):
    self.name = name
  def __eq__(self, other):
    return isinstance(other, Country) and self.name == other.name
  def isIn(self, loc):
    if isinstance(loc, GPS):
      return False
    elif isinstance(loc, City):
      return False
    elif isinstance(loc, Country):
      return self == loc
    else:
      return False
class Unknown(Location):
  def __init__(self):
    self.tag = "Unknown"
  def __eq__(self, other):
    return self.tag == other.tag
  def isIn(self, loc):
    return False

# Users have a user ID and a location.
@jeeves
class User:
  def __init__(self, userId, friends=[]):
    # TODO: Implement more interesting policies for this.
    def allowUserWrite(user):
      return lambda _this: lambda ictxt: lambda octxt: ictxt == user
    self.userId = userId
    self.location = ProtectedRef(Unknown(), None
      , lambda _this: lambda ic: lambda oc:
          ic == self)
    self.friends = list(friends)
  def addFriend(self, friend):
    self.friends.append(friend)
  def isFriends(self, other):
    return JeevesLib.jhas(self.friends, other)
  def prettyPrint(self):
    return "user" # str(self.userId)
  def __eq__(self, other):
    return self.userId == other.userId

class LocationNetwork:
  def __init__(self, users=[]):
    self.users = users

  @jeeves
  def countUsersInLocation(self, loc):
    sum = 0
    for user in self.users:
      print user.location.v
      if user.location.v.isIn(loc):
        sum += 1
    return sum

########NEW FILE########
__FILENAME__ = testLocationFlow
from smt.Z3 import *
import unittest

from fast.ProtectedRef import ProtectedRef, UpdateResult
from Location import Location, GPS, City, Country, User, LocationNetwork
import JeevesLib
from sourcetrans.macro_module import macros, jeeves

class TestLocationFlow(unittest.TestCase):
  def setUp(self):
    def canSee(owner, ctxt):
      return owner == ctxt or owner.isFriends(ctxt)

    # Need to initialize the JeevesLib environment.
    JeevesLib.init()

    # Define some locations.
    self.countryUSA = Country("USA")
    self.cityCambridge = City("Cambridge", self.countryUSA)
    self.gpsMIT = GPS(40.589063, -74.159178, self.cityCambridge) 

    # Define some users.
    self.alice = User(0)
#      , JeevesLib.mkSensitive(aliceLabel, self.gpsMIT, self.cityCambridge))
    self.bob = User(1) #, self.cityCambridge)
    self.carol = User(2) #, self.countryUSA)

    self.alice.addFriend(self.bob)
    self.bob.addFriend(self.alice)

    aliceLabel = JeevesLib.mkLabel()
    JeevesLib.restrict(aliceLabel, lambda oc: oc == self.alice or self.alice.isFriends(oc))
    self.aliceLoc = JeevesLib.mkSensitive(aliceLabel, self.gpsMIT
                      , self.cityCambridge)

  @jeeves
  def testUpdates(self):
    # Bob cannot update Alice's location.
    self.assertEqual(
      self.alice.location.update(self.bob, self.bob, self.aliceLoc)
      , UpdateResult.Unknown)

    # Alice updates her location.
    self.assertEqual(self.alice.location.update(self.alice, self.alice
      , self.aliceLoc), UpdateResult.Unknown)
    # Only Alice and her friends can see the high-confidentiality version of
    # her location.
    self.assertEqual(JeevesLib.concretize(self.alice, self.alice.location.v)
      , self.gpsMIT)
    self.assertEqual(JeevesLib.concretize(self.bob, self.alice.location.v)
      , self.gpsMIT)
    # TODO: This doesn't work yet because we don't have a rank-ordering of
    # labels associated with write policies so that we can prioritize assigning
    # certain labels to high over others.
    self.assertEqual(JeevesLib.concretize(self.carol, self.alice.location.v)
      , self.cityCambridge)

  def testCountUsersInLocation(self):
    self.assertEqual(self.alice.location.update(self.alice, self.alice
      , self.aliceLoc), UpdateResult.Unknown)
    self.assertEqual(self.bob.location.update(self.bob, self.bob, self.cityCambridge), UpdateResult.Unknown)
    self.assertEqual(self.carol.location.update(self.carol, self.carol, self.countryUSA), UpdateResult.Unknown)

    # Only Alice and Bob can see Alice's "high" location of S
    locNetwork = LocationNetwork([self.alice, self.bob, self.carol])
    usersInStata = locNetwork.countUsersInLocation(self.gpsMIT)
    self.assertEqual(JeevesLib.concretize(self.alice, usersInStata), 1)
    self.assertEqual(JeevesLib.concretize(self.bob, usersInStata), 1)
    self.assertEqual(JeevesLib.concretize(self.carol, usersInStata), 0)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = Chemotaxis
'''
We try to model chemotaxis as an information flow system, where receptor
sensitivities correspond to flow permissions.
'''
from macropy.case_classes import macros, enum
import JeevesLib
from fast.ProtectedRef import ProtectedRef
from sourcetrans.macro_module import macros, jeeves

class Impossible(Exception):
  def __init__(self, msg):
    self.msg = msg

# TODO: Add an adjacency edge?
@enum
class EdgeType:
  ReceptorActivation, PhosphoTransfer, Methylation, FlagellumControl

class Edge:
  def __init__(self, v, edgeType):
    self.v = v
    self.edgeType = edgeType

@jeeves
class Protein:
  # TODO: Figure out what kinds of policies should go here...
  def __init__(self, name, initValue=0):
    self.name = name
    self._vRef = ProtectedRef(initValue
      # We also support policies where the write checks get concretized right
      # away in the context of the user.
      , None
      # Flow is only permitted if there is an edge.
      # The policy takes the current value (v), the input channel (ic), and
      # the output channel.
      , lambda v: lambda ic: lambda oc:
          JeevesLib.jhasElt(self.edges, lambda edge: edge.v == oc))
    self._edges = []
  def addEdge(self, node, edgeType):
    self._edges.append(Edge(node, edgeType))
  def updateValue(self, ictxt, f):
    self._vRef.update(ictxt, ictxt, f(self._vRef.v))

# TODO: Do these different color proteins have different properties?
class BlueProtein(Protein):
  pass
class GreenProtein(Protein):
  pass
class PProtein(Protein):
  pass
class RedProtein(Protein):
  pass
class YellowProtein(Protein):
  pass

'''
This class defines chemotaxis actions for a set of proteins (in a bacteria
cell?
'''
class Chemotaxis:
  def __init__(self):
    self.proteins = []
    self._ligandEdges = []
    self._flagellumOut = Protein("FOut")

  # TODO: Change the update functions to update to what they should actually do.
  def runStep(self):
    for protein in self.proteins:
      # TODO: Add a case for adjacency?
      for edge in self.edges:
        if edge.edgeType == EdgeType.ReceptorActivation:
          edge.v.updateValue(lambda v: v)
        elif edge.edgeType == Edgetype.PhosphoTransfer:
          edge.v.updateValue(lambda v: v)
        elif edge.edgeType == EdgeType.Methylation:
          edge.v.updateValue(lambda v: v)
        elif edge.edgeType ==FlagellumControl:
          edge.v.updateValue(lambda v: v)
        else:
          raise Impossible("Edge should be one of the above types.")

########NEW FILE########
__FILENAME__ = RSphaeroides
from Chemotaxis import Protein, BlueProtein, Chemotaxis, GreenProtein, PProtein, RedProtein, YellowProtein, EdgeType

class RSphaeroides(Chemotaxis):
  # Define the structure of the cell in terms of connections.
  # TODO: How do we specify initial values for proteins where there are more
  # than one of the same?
  def __init__(self, values={}):
    Chemotaxis.__init__(self)

    self.proteinMCP = GreenProtein("MCP")
    self._ligandEdges.append(self.proteinMCP)
    self.proteinW2 = GreenProtein("W2")
    self.proteinW3 = GreenProtein("W3")
    self.proteinA2_0 = GreenProtein("A2")
    self.proteinA2_1 = GreenProtein("A2")
    self.proteinR2 = RedProtein("R2")
    self.proteinR2.addEdge(self.proteinMCP, EdgeType.Methylation)
    self.proteinP_0 = Protein("P")
    self.proteinA2_1.addEdge(self.proteinP_0, EdgeType.PhosphoTransfer)

    self.proteinTlp = GreenProtein("Tlp")
    self._ligandEdges.append(self.proteinMCP)
    self.proteinW4 = GreenProtein("R4")
    self.proteinA4 = GreenProtein("A4")
    self.proteinA3 = GreenProtein("A3")
    self.proteinR3 = RedProtein("R3")
    self.proteinR3.addEdge(self.proteinTlp, EdgeType.Methylation)
    self.proteinP_1 = Protein("P")
    self.proteinA4.addEdge(self.proteinP_1, EdgeType.PhosphoTransfer)
  
    self.proteinB1_0 = YellowProtein("B1")
    self.proteinB1_1 = YellowProtein("B1")
    self.proteinB1_0.addEdge(self.proteinB1_1, EdgeType.FlagellumControl)
    self.proteinB1_1.addEdge(self.proteinB1_0, EdgeType.FlagellumControl)
    self.proteinP_2 = Protein("P") 
    # TODO: How to add a phosphotransfer with an edge?

    self.proteinY6_1 = BlueProtein("Y6")
    self.proteinY6_1.addEdge(self._flagellumOut, EdgeType.FlagellumControl)
    
    self.proteins = [ self.proteinMCP, self.proteinW2, self.proteinW3
                    , self.proteinA2_0, self.proteinA2_1, self.proteinR2
                    , self.proteinP_0, self.proteinTlp, self.proteinA4
                    , self.proteinA3, self.proteinR3, self.proteinP_1
                    , self.proteinB1_0, self.proteinB1_1, self.proteinP_2 ]

########NEW FILE########
__FILENAME__ = testChemotaxis
import JeevesLib
from smt.Z3 import *
import unittest
from RSphaeroides import RSphaeroides
import JeevesLib

class TestAuction(unittest.TestCase):
  def setUp(self):
    JeevesLib.init()

  def test_something(self):
    r = RSphaeroides()
    pass

########NEW FILE########
__FILENAME__ = testJeevesBasic
'''
This tests code after the macro transformation.
'''
import JeevesLib
from smt.Z3 import *
import sys
import unittest

class User:
  def __init__(self, userId):
    self.userId = userId

class GPS:
  def __init__(self, lt, lg):
    self.lt = lt
    self.lg = lg
  def distance(self, other):
    return abs(self.lt - other.lt) + abs(self.lg - other.lg)
  def __eq__(self, other):
    return (self.lt == other.lt) and (self.lg == other.lg)

class LocationContext:
  def __init__(self, user, location):
    self.user = user
    self.location = location 

class TestJeevesBasic(unittest.TestCase):
  def setUp(self):
    self.s = Z3()
    # reset the Jeeves state
    JeevesLib.init()

  '''
  Basic example of showing different values to different viewers.
  '''
  def testBasic(self):
    alice = User(0)
    bob = User(1)

    a = JeevesLib.mkLabel()
    JeevesLib.restrict(a, lambda oc: oc == alice)
    xS = JeevesLib.mkSensitive(a, 42, 0)
    self.assertEqual(42, JeevesLib.concretize(alice, xS))
    self.assertEqual(0, JeevesLib.concretize(bob, xS))

  '''
  Using 'and' and 'or'. Without the source transformation, we have to use 'jand'
  and 'jor' explicitly because of the lack of overloading.
  '''
  def testAndOr(self):
    alice = User(0)
    bob = User(1)
    charlie = User(2)

    a = JeevesLib.mkLabel()
    JeevesLib.restrict(a
        , lambda oc: JeevesLib.jor(lambda: oc == alice, lambda: oc == bob))
    xS = JeevesLib.mkSensitive(a, 42, 0)
    self.assertEqual(42, JeevesLib.concretize(alice, xS))
    self.assertEqual(42, JeevesLib.concretize(bob, xS))
    self.assertEqual(0, JeevesLib.concretize(charlie, xS))

  '''
  Example of using dynamic state in a policy.
  '''
  def testStatefulPolicy(self):
    alice = User(0)
    bob = User(1)
    charlie = User(2)

    friends = { alice: [bob], bob: [alice], charlie: [] }
    a = JeevesLib.mkLabel()
    # Policy: can see if viewer is in the friends list.
    JeevesLib.restrict(a
        , lambda oc: JeevesLib.jhas(friends[alice], oc))
    xS = JeevesLib.mkSensitive(a, 42, 0)
    # Bob can see but Alice and Charlie can not.
    self.assertEqual(0, JeevesLib.concretize(alice, xS))
    self.assertEqual(42, JeevesLib.concretize(bob, xS))
    self.assertEqual(0, JeevesLib.concretize(charlie, xS))

    # Update friends list and now Charlie can see.
    friends[alice].append(charlie)
    
    self.assertEqual(0, JeevesLib.concretize(alice, xS))
    self.assertEqual(42, JeevesLib.concretize(bob, xS))
    self.assertEqual(42, JeevesLib.concretize(charlie, xS))

  '''
  Example of a policy that depends on a sensitive value.
  '''
  def testDependentPolicy(self):
    defaultLoc = GPS(sys.maxint, sys.maxint)
    
    alice = User(0)
    a = JeevesLib.mkLabel()
    aliceLoc = JeevesLib.mkSensitive(a, GPS(0, 0), defaultLoc)
    JeevesLib.restrict(a, lambda oc: oc.location.distance(aliceLoc) < 25)
    aliceCtxt = LocationContext(alice, aliceLoc)

    bob = User(1)
    self.assertEqual(GPS(0, 0)
        , JeevesLib.concretize(LocationContext(bob, GPS(5, 5)), aliceLoc))
    self.assertEqual(defaultLoc
        , JeevesLib.concretize(LocationContext(bob, GPS(12, 13)), aliceLoc))

  '''
  Example with a circular dependency.
  '''
  def testCircularDependency(self):
    a = JeevesLib.mkLabel()
    alice = User(0)
    bob = User(1)
    charlie = User(2)
    guestList = JeevesLib.JList([alice, bob])
    guestListS = JeevesLib.mkSensitive(a, guestList, JeevesLib.JList([]))
    JeevesLib.restrict(a, lambda oc: JeevesLib.jhas(guestListS, oc))

    self.assertEqual([alice, bob], JeevesLib.concretize(alice, guestListS))
    self.assertEqual([alice, bob], JeevesLib.concretize(bob, guestListS))
    self.assertEqual([], JeevesLib.concretize(charlie, guestListS))

  '''
  Conditionals.
  '''
  def testConditional(self):
    a = JeevesLib.mkLabel()
    alice = User(0) 
    bob = User(1)
    JeevesLib.restrict(a, lambda oc: oc == alice)
    xS = JeevesLib.mkSensitive(a, 42, 0)
    r = JeevesLib.jif(xS == 42, lambda: 1, lambda: 2)
    self.assertEqual(1, JeevesLib.concretize(alice, r))
    self.assertEqual(2, JeevesLib.concretize(bob, r))

  '''
  Functions.
  '''
  def testFunction(self):
    pass

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
"""
Django settings for conf project.  
For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

import sys

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(__file__)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '!$e(y9&5ol=#s7wex!xhv=f&5f2@ufjez3ee9kdifw=41p_+%*'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates/'),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'testdb',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'urls'

WSGI_APPLICATION = 'wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

if 'test' in sys.argv:
  DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'test.db'),
        'TEST_NAME': os.path.join(os.path.dirname(__file__), 'test.db'),
    }
  }
else:
  DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
  }


MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from jeevesdb import JeevesModel

class Animal(JeevesModel.JeevesModel):
  name = models.CharField(max_length=30)
  sound = models.CharField(max_length=30)

  def speak(self):
    return "The %s says \"%s\"" % (self.name, self.sound)

class Zoo(JeevesModel.JeevesModel):
  name = models.CharField(max_length=30)
  inhabitant = JeevesModel.JeevesForeignKey(Animal)

class AnimalWithPolicy(JeevesModel.JeevesModel):
  name = models.CharField(max_length=30)
  sound = models.CharField(max_length=30)

  @staticmethod
  def jeeves_get_private_sound(animal):
    return ""

  @staticmethod
  def jeeves_restrict_sound(animal, ctxt):
    return ctxt == animal

class AnimalWithPolicy2(JeevesModel.JeevesModel):
  name = models.CharField(max_length=30)
  sound = models.CharField(max_length=30)

  @staticmethod
  def jeeves_get_private_sound(animal):
    return ""

  @staticmethod
  @JeevesModel.label_for('sound')
  def jeeves_restrict_awplabel(animal, ctxt):
    return ctxt == animal

########NEW FILE########
__FILENAME__ = tests
from django.db import models
from django.utils import unittest
from django.test import TestCase

import JeevesLib

from jeevesdb import JeevesModel
from testdb.models import Animal, Zoo, AnimalWithPolicy, AnimalWithPolicy2

def parse_vars_row(vs):
  d = {}
  for entry in vs.split(';')[1:-1]:
    name, val = entry.split('=')
    d[name] = bool(int(val))
  return d

# expected is a list
# [({name:'lion',...}, {var_name:True,...})]
def areRowsEqual(rows, expected):
  rows = list(rows)
  if len(rows) != len(expected):
    print 'got len %d, expected %d' % (len(rows), len(expected))
    return False
  for attrs_dict, vars_dict in expected:
    for r in rows:
      vars_dict1 = parse_vars_row(r.jeeves_vars)
      if (vars_dict == vars_dict1 and
          all(getattr(r, name) == val for name, val in attrs_dict.iteritems())):
          break
    else:
      print 'could not find', attrs_dict, vars_dict
      return False
  return True

class TestJeevesModel(TestCase):
  def setUp(self):
    JeevesLib.init()

    Animal.objects.create(name='lion', sound='roar')
    Animal.objects.create(name='cat', sound='meow')

    self.x = JeevesLib.mkLabel()
    self.y = JeevesLib.mkLabel()
    JeevesLib.restrict(self.x, lambda (a,_) : a)
    JeevesLib.restrict(self.y, lambda (_,a) : a)

    Animal.objects.create(name='fox',
        sound=JeevesLib.mkSensitive(self.x, 'Hatee-hatee-hatee-ho!',
            'Joff-tchoff-tchoff-tchoffo-tchoffo-tchoff!'))

    Animal.objects.create(name='a',
        sound=JeevesLib.mkSensitive(self.x,
            JeevesLib.mkSensitive(self.y, 'b', 'c'),
            JeevesLib.mkSensitive(self.y, 'd', 'e')))

  def testWrite(self):
    lion = Animal._objects_ordinary.get(name='lion')
    self.assertEquals(lion.name, 'lion')
    self.assertEquals(lion.sound, 'roar')
    self.assertEquals(lion.jeeves_vars, ';')

    fox = Animal._objects_ordinary.filter(name='fox').filter(jeeves_vars=';%s=1;'%self.x.name).all()[0]
    self.assertEquals(fox.sound, 'Hatee-hatee-hatee-ho!')
    fox = Animal._objects_ordinary.filter(name='fox').filter(jeeves_vars=';%s=0;'%self.x.name).all()[0]
    self.assertEquals(fox.sound, 'Joff-tchoff-tchoff-tchoffo-tchoffo-tchoff!')

    a = list(Animal._objects_ordinary.filter(name='a').all())
    self.assertTrue(areRowsEqual(a, [
      ({'name':'a', 'sound':'b'}, {self.x.name:True, self.y.name:True}),
      ({'name':'a', 'sound':'c'}, {self.x.name:True, self.y.name:False}),
      ({'name':'a', 'sound':'d'}, {self.x.name:False, self.y.name:True}),
      ({'name':'a', 'sound':'e'}, {self.x.name:False, self.y.name:False}),
     ]))

  def testQueryDelete(self):
    Animal.objects.create(name='delete_test1',
        sound=JeevesLib.mkSensitive(self.x,
            JeevesLib.mkSensitive(self.y, 'b', 'c'),
            JeevesLib.mkSensitive(self.y, 'd', 'e')))
    Animal.objects.filter(name='delete_test1').filter(sound='b').delete()
    a = list(Animal._objects_ordinary.filter(name='delete_test1').all())
    self.assertTrue(areRowsEqual(a, [
      ({'name':'delete_test1', 'sound':'c'}, {self.x.name:True, self.y.name:False}),
      ({'name':'delete_test1', 'sound':'d'}, {self.x.name:False, self.y.name:True}),
      ({'name':'delete_test1', 'sound':'e'}, {self.x.name:False, self.y.name:False}),
     ]))

    an = Animal.objects.create(name='delete_test2',
        sound=JeevesLib.mkSensitive(self.x,
            JeevesLib.mkSensitive(self.y, 'b', 'c'),
            JeevesLib.mkSensitive(self.y, 'd', 'e')))
    with JeevesLib.PositiveVariable(self.x):
      an.delete()
    a = list(Animal._objects_ordinary.filter(name='delete_test2').all())
    self.assertTrue(areRowsEqual(a, [
      ({'name':'delete_test2', 'sound':'d'}, {self.x.name:False, self.y.name:True}),
      ({'name':'delete_test2', 'sound':'e'}, {self.x.name:False, self.y.name:False}),
     ]))

    an = Animal.objects.create(name='delete_test3', sound='b')
    with JeevesLib.PositiveVariable(self.x):
      an.delete()
    a = list(Animal._objects_ordinary.filter(name='delete_test3').all())
    self.assertTrue(areRowsEqual(a, [
      ({'name':'delete_test3', 'sound':'b'}, {self.x.name:False})
    ]))

    an = Animal.objects.create(name='delete_test4', sound='b')
    with JeevesLib.PositiveVariable(self.x):
      with JeevesLib.NegativeVariable(self.y):
        an.delete()
    a = list(Animal._objects_ordinary.filter(name='delete_test4').all())
    self.assertTrue(areRowsEqual(a, [
      ({'name':'delete_test4', 'sound':'b'}, {self.x.name:False}),
      ({'name':'delete_test4', 'sound':'b'}, {self.x.name:True, self.y.name:True}),
    ]) or areRowsEqual(a, [
      ({'name':'delete_test4', 'sound':'b'}, {self.y.name:True}),
      ({'name':'delete_test4', 'sound':'b'}, {self.y.name:False, self.x.name:False}),
    ]))

    an = Animal.objects.create(name='delete_test5',
            sound=JeevesLib.mkSensitive(self.x, 'b', 'c'))
    with JeevesLib.PositiveVariable(self.x):
      an.delete()
    a = list(Animal._objects_ordinary.filter(name='delete_test5').all())
    self.assertTrue(areRowsEqual(a, [
      ({'name':'delete_test5', 'sound':'c'}, {self.x.name:False})
    ]))

    an = Animal.objects.create(name='delete_test6',
            sound=JeevesLib.mkSensitive(self.x, 'b', 'c'))
    with JeevesLib.PositiveVariable(self.y):
      an.delete()
    a = list(Animal._objects_ordinary.filter(name='delete_test6').all())
    self.assertTrue(areRowsEqual(a, [
      ({'name':'delete_test6', 'sound':'b'}, {self.x.name:True,self.y.name:False}),
      ({'name':'delete_test6', 'sound':'c'}, {self.x.name:False,self.y.name:False}),
    ]))

  def testSave(self):
    an = Animal.objects.create(name='save_test1', sound='b')
    an.sound = 'c'
    with JeevesLib.PositiveVariable(self.x):
      an.save()
    a = list(Animal._objects_ordinary.filter(name='save_test1').all())
    self.assertTrue(areRowsEqual(a, [
      ({'name':'save_test1', 'sound':'b'}, {self.x.name:False}),
      ({'name':'save_test1', 'sound':'c'}, {self.x.name:True}),
    ]))

    an = Animal.objects.create(name='save_test2', sound='b')
    an.sound = 'c'
    with JeevesLib.PositiveVariable(self.x):
      with JeevesLib.NegativeVariable(self.y):
        an.save()
    a = list(Animal._objects_ordinary.filter(name='save_test2').all())
    self.assertTrue(areRowsEqual(a, [
      ({'name':'save_test2', 'sound':'c'}, {self.x.name:True, self.y.name:False}),
      ({'name':'save_test2', 'sound':'b'}, {self.x.name:True, self.y.name:True}),
      ({'name':'save_test2', 'sound':'b'}, {self.x.name:False}),
    ]) or areRowsEqual(a, [
      ({'name':'save_test2', 'sound':'c'}, {self.x.name:True, self.y.name:False}),
      ({'name':'save_test2', 'sound':'b'}, {self.x.name:False, self.y.name:False}),
      ({'name':'save_test2', 'sound':'b'}, {self.y.name:True}),
    ]))

    an = Animal.objects.create(name='save_test3',
        sound=JeevesLib.mkSensitive(self.x, 'b', 'c'))
    an.sound = JeevesLib.mkSensitive(self.x, 'd', 'e')
    an.save()
    a = list(Animal._objects_ordinary.filter(name='save_test3').all())
    self.assertTrue(areRowsEqual(a, [
      ({'name':'save_test3', 'sound':'d'}, {self.x.name:True}),
      ({'name':'save_test3', 'sound':'e'}, {self.x.name:False}),
    ]))

    an = Animal.objects.create(name='save_test4',
        sound=JeevesLib.mkSensitive(self.x, 'b', 'c'))
    an.sound = JeevesLib.mkSensitive(self.y, 'd', 'e')
    an.save()
    a = list(Animal._objects_ordinary.filter(name='save_test4').all())
    self.assertTrue(areRowsEqual(a, [
        ({'name':'save_test4', 'sound':'d'}, {self.y.name:True}),
        ({'name':'save_test4', 'sound':'e'}, {self.y.name:False}),
    ]) or areRowsEqual(a, [
        ({'name':'save_test4', 'sound':'d'}, {self.y.name:True, self.x.name:True}),
        ({'name':'save_test4', 'sound':'d'}, {self.y.name:True, self.x.name:False}),
        ({'name':'save_test4', 'sound':'e'}, {self.y.name:False, self.x.name:True}),
        ({'name':'save_test4', 'sound':'e'}, {self.y.name:False, self.x.name:False}),
    ]))

    an = Animal.objects.create(name='save_test5',
        sound=JeevesLib.mkSensitive(self.x, 'b', 'c'))
    an.sound = JeevesLib.mkSensitive(self.y, 'd', 'e')
    with JeevesLib.PositiveVariable(self.x):
      an.save()
    a = list(Animal._objects_ordinary.filter(name='save_test5').all())
    self.assertTrue(areRowsEqual(a, [
        ({'name':'save_test5', 'sound':'c'}, {self.x.name:False}),
        ({'name':'save_test5', 'sound':'d'}, {self.x.name:True, self.y.name:True}),
        ({'name':'save_test5', 'sound':'e'}, {self.x.name:True, self.y.name:False}),
    ]))

    an = Animal.objects.create(name='save_test6',
        sound=JeevesLib.mkSensitive(self.x, 'b', 'c'))
    an.sound = JeevesLib.mkSensitive(self.y, 'd', 'e')
    with JeevesLib.PositiveVariable(self.y):
      an.save()
    a = list(Animal._objects_ordinary.filter(name='save_test6').all())
    self.assertTrue(areRowsEqual(a, [
        ({'name':'save_test6', 'sound':'b'}, {self.x.name:True, self.y.name:False}),
        ({'name':'save_test6', 'sound':'d'}, {self.x.name:True, self.y.name:True}),
        ({'name':'save_test6', 'sound':'c'}, {self.x.name:False, self.y.name:False}),
        ({'name':'save_test6', 'sound':'d'}, {self.x.name:False, self.y.name:True}),
    ]) or areRowsEqual(a, [
        ({'name':'save_test6', 'sound':'b'}, {self.x.name:True, self.y.name:False}),
        ({'name':'save_test6', 'sound':'d'}, {self.y.name:True}),
        ({'name':'save_test6', 'sound':'c'}, {self.x.name:False, self.y.name:False}),
    ]))

    an = Animal.objects.create(name='save_test7',
        sound=JeevesLib.mkSensitive(self.x, 'b', 'c'))
    an.sound = JeevesLib.mkSensitive(self.y, 'd', 'e')
    with JeevesLib.PositiveVariable(self.x):
      with JeevesLib.PositiveVariable(self.y):
        an.save()
    a = list(Animal._objects_ordinary.filter(name='save_test7').all())
    self.assertTrue(areRowsEqual(a, [
        ({'name':'save_test7', 'sound':'d'}, {self.x.name:True, self.y.name:True}),
        ({'name':'save_test7', 'sound':'b'}, {self.x.name:True, self.y.name:False}),
        ({'name':'save_test7', 'sound':'c'}, {self.x.name:False}),
    ]))

  def testSaveCollapse(self):
    an = Animal.objects.create(name='savec_test', sound='b')
    an.sound = 'c'
    with JeevesLib.PositiveVariable(self.x):
      an.save()
    with JeevesLib.NegativeVariable(self.x):
      an.save()

    a = list(Animal._objects_ordinary.filter(name='savec_test').all())
    self.assertTrue(areRowsEqual(a, [
        ({'name':'savec_test', 'sound':'c'}, {}),
    ]))

  def testEnvWrite(self):
    an = Animal.objects.create(name='save_ew_test', sound='b')
    with JeevesLib.PositiveVariable(self.x):
      an.sound = 'c'
    an.save()

    a = list(Animal._objects_ordinary.filter(name='save_ew_test').all())
    self.assertTrue(areRowsEqual(a, [
        ({'name':'save_ew_test', 'sound':'b'}, {self.x.name:False}),
        ({'name':'save_ew_test', 'sound':'c'}, {self.x.name:True}),
    ]))

  def testGet1(self):
    an = Animal.objects.create(name='get_test1', sound='get_test1_sound_xyz')

    bn = Animal.objects.get(name='get_test1')
    self.assertEqual(an.name, 'get_test1')
    self.assertEqual(an.sound, 'get_test1_sound_xyz')

    cn = Animal.objects.get(sound='get_test1_sound_xyz')
    self.assertEqual(cn.name, 'get_test1')
    self.assertEqual(cn.sound, 'get_test1_sound_xyz')

    self.assertTrue(JeevesLib.concretize((True, True), an == bn))
    self.assertTrue(JeevesLib.concretize((True, True), an == cn))
    self.assertTrue(JeevesLib.concretize((True, True), bn == cn))

    self.assertTrue(JeevesLib.concretize((False, True), an == bn))
    self.assertTrue(JeevesLib.concretize((False, True), an == cn))
    self.assertTrue(JeevesLib.concretize((False, True), bn == cn))

  def testGet2(self):
    an = Animal.objects.create(name='get_test2', sound=JeevesLib.mkSensitive(self.x, 'b', 'c'))

    bn = Animal.objects.get(name='get_test2')

    self.assertEqual(JeevesLib.concretize((True, True), an == bn), True)
    self.assertEqual(JeevesLib.concretize((False, True), an == bn), True)
    self.assertEqual(an.name, 'get_test2')
    self.assertEqual(an.sound.cond.name, self.x.name)
    self.assertEqual(an.sound.thn.v, 'b')
    self.assertEqual(an.sound.els.v, 'c')

  def testGet3(self):
    an = Animal.objects.create(name='get_test3', sound=JeevesLib.mkSensitive(self.x, JeevesLib.mkSensitive(self.y, 'b', 'c'), JeevesLib.mkSensitive(self.y, 'd', 'e')))

    bn = Animal.objects.get(name='get_test3')

    self.assertEqual(JeevesLib.concretize((True, True), an == bn), True)
    self.assertEqual(JeevesLib.concretize((False, True), an == bn), True)
    self.assertEqual(JeevesLib.concretize((True,True), bn.sound), 'b')
    self.assertEqual(JeevesLib.concretize((True,False), bn.sound), 'c')
    self.assertEqual(JeevesLib.concretize((False,True), bn.sound), 'd')
    self.assertEqual(JeevesLib.concretize((False,False), bn.sound), 'e')

  def testGet4(self):
    with JeevesLib.PositiveVariable(self.x):
      an = Animal.objects.create(name='get_test4', sound='a')
    with JeevesLib.NegativeVariable(self.y):
      bn = Animal.objects.create(name='get_test4', sound='b')
    
    got_exc = False
    try:
      cn = Animal.objects.get(name='get_test4')
    except Exception:
      got_exc = True

    self.assertTrue(got_exc)
    #self.assertEqual(cn.cond.name, self.x.name)
    #self.assertEqual(cn.thn.v.name, 'get_test4')
    #self.assertEqual(cn.thn.v.sound, 'a')
    #self.assertEqual(cn.els.v.name, 'get_test4')
    #self.assertEqual(cn.els.v.sound, 'b')

    #an1 = cn.thn
    #bn1 = cn.els
    #self.assertTrue(an == an1)
    #self.assertTrue(bn == bn1)
    #self.assertTrue(an != bn)
    #self.assertTrue(an != bn1)
    #self.assertTrue(bn != an)
    #self.assertTrue(bn != an1)

  def testFilter1(self):
    an = Animal.objects.create(name='filter_test1', sound='a')

    bl = Animal.objects.filter(name='filter_test1').get_jiter()
    self.assertEquals(bl, [(an, {})])

  def testFilter2(self):
    with JeevesLib.PositiveVariable(self.x):
      an = Animal.objects.create(name='filter_test2', sound='a')

    bl = Animal.objects.filter(name='filter_test2').get_jiter()
    self.assertEquals(bl, [(an, {self.x.name:True})])

  def testFilter3(self):
    with JeevesLib.PositiveVariable(self.x):
      an = Animal.objects.create(name='filter_test3', sound='a')
    with JeevesLib.NegativeVariable(self.y):
      bn = Animal.objects.create(name='filter_test3', sound='b')

    bl = Animal.objects.filter(name='filter_test3').order_by('sound').get_jiter()
    self.assertEquals(bl, [(an, {self.x.name:True}), (bn, {self.y.name:False})])

  def testFilter4(self):
    an = Animal.objects.create(name='filter_test4', sound='b')
    bn = Animal.objects.create(name='filter_test4', sound=JeevesLib.mkSensitive(self.x, 'a', 'c'))

    bl = Animal.objects.filter(name='filter_test4').order_by('sound').get_jiter()
    self.assertEquals(bl, [(bn, {self.x.name:True}), (an, {}), (bn, {self.x.name:False})])

  def testJeevesForeignKey(self):
    an = Animal.objects.create(name='fkey_test1_an', sound='a')
    bn = Animal.objects.create(name='fkey_test1_bn', sound='b')
    zoo = Zoo.objects.create(name='fkey_test1_zoo',
        inhabitant=JeevesLib.mkSensitive(self.x, an, bn))
    a = list(Animal._objects_ordinary.filter(name='fkey_test1_an').all())
    b = list(Animal._objects_ordinary.filter(name='fkey_test1_bn').all())
    z = list(Zoo._objects_ordinary.filter(name='fkey_test1_zoo').all())
    self.assertTrue(areRowsEqual(a, [
      ({'name':'fkey_test1_an', 'sound':'a'}, {})
     ]))
    self.assertTrue(areRowsEqual(b, [
      ({'name':'fkey_test1_bn', 'sound':'b'}, {})
     ]))
    self.assertTrue(areRowsEqual(z, [
      ({'name':'fkey_test1_zoo', 'inhabitant_id':an.jeeves_id}, {self.x.name:True}),
      ({'name':'fkey_test1_zoo', 'inhabitant_id':bn.jeeves_id}, {self.x.name:False}),
     ]))
    z = Zoo.objects.get(name='fkey_test1_zoo')
    self.assertEqual(JeevesLib.concretize((True, True), z.inhabitant), an)
    self.assertEqual(JeevesLib.concretize((False, True), z.inhabitant), bn)

    z.inhabitant.sound = 'd'
    z.inhabitant.save()

    a = list(Animal._objects_ordinary.filter(name='fkey_test1_an').all())
    b = list(Animal._objects_ordinary.filter(name='fkey_test1_bn').all())
    z = list(Zoo._objects_ordinary.filter(name='fkey_test1_zoo').all())
    self.assertTrue(areRowsEqual(a, [
      ({'name':'fkey_test1_an', 'sound':'a'}, {self.x.name:False}),
      ({'name':'fkey_test1_an', 'sound':'d'}, {self.x.name:True}),
     ]))
    self.assertTrue(areRowsEqual(b, [
      ({'name':'fkey_test1_bn', 'sound':'b'}, {self.x.name:True}),
      ({'name':'fkey_test1_bn', 'sound':'d'}, {self.x.name:False}),
     ]))
    self.assertTrue(areRowsEqual(z, [
      ({'name':'fkey_test1_zoo', 'inhabitant_id':an.jeeves_id}, {self.x.name:True}),
      ({'name':'fkey_test1_zoo', 'inhabitant_id':bn.jeeves_id}, {self.x.name:False}),
     ]))

  def testFKeyUpdate(self):
    an = Animal.objects.create(name='fkeyup_test_an', sound='a')
    zoo = Zoo.objects.create(name='fkeyup_test_zoo', inhabitant=an)

    an.sound = 'b'
    an.save()

    z = Zoo.objects.get(name='fkeyup_test_zoo')
    self.assertTrue(z != None)
    self.assertEqual(z.inhabitant, an)

  def testFilterForeignKeys1(self):
    an = Animal.objects.create(name='filterfkey_test1_an', sound='a')
    bn = Animal.objects.create(name='filterfkey_test1_bn', sound='b')
    zoo = Zoo.objects.create(name='filterfkey_test1_zoo',
        inhabitant=JeevesLib.mkSensitive(self.x, an, bn))

    zool = Zoo.objects.filter(inhabitant__name='filterfkey_test1_an').get_jiter()
    self.assertEquals(zool, [(zoo, {self.x.name:True})])

  def testFilterForeignKeys2(self):
    an = Animal.objects.create(name='filterfkey_test2_an',
                sound=JeevesLib.mkSensitive(self.x, 'a', 'b'))
    zoo = Zoo.objects.create(name='filterfkey_zoo', inhabitant=an)

    zool = Zoo.objects.filter(inhabitant__name='filterfkey_test2_an').filter(inhabitant__sound='a').get_jiter()
    self.assertEquals(zool, [(zoo, {self.x.name:True})])

  def testNullFields(self):
    # TODO
    pass

  def testPolicy(self):
    awp = AnimalWithPolicy.objects.create(name='testpolicy1', sound='meow')

    a = list(AnimalWithPolicy._objects_ordinary.filter(name='testpolicy1').all())
    name = 'AnimalWithPolicy__sound__' + awp.jeeves_id
    self.assertTrue(areRowsEqual(a, [
      ({'name':'testpolicy1', 'sound':'meow'}, {name:True}),
      ({'name':'testpolicy1', 'sound':''}, {name:False}),
     ]))

  def testPolicy2(self):
    awp = AnimalWithPolicy2.objects.create(name='testpolicy2', sound='meow')

    a = list(AnimalWithPolicy2._objects_ordinary.filter(name='testpolicy2').all())
    name = 'AnimalWithPolicy2__awplabel__' + awp.jeeves_id
    self.assertTrue(areRowsEqual(a, [
      ({'name':'testpolicy2', 'sound':'meow'}, {name:True}),
      ({'name':'testpolicy2', 'sound':''}, {name:False}),
     ]))

########NEW FILE########
__FILENAME__ = testAST
import unittest
import macropy.activate

import JeevesLib
from fast.AST import *
from eval.Eval import partialEval
from JeevesLib import PositiveVariable, NegativeVariable

def isPureFacetTree(f):
    if isinstance(f, Constant):
        return True
    elif isinstance(f, Facet):
        return isPureFacetTree(f.thn) and isPureFacetTree(f.els)
    else:
        return False


class TestAST(unittest.TestCase):

    def setUp(self):
        pass

    # TODO test eval

    def testArithmeticL(self):
        t = Constant(20)
        r = ((((t + 1) - 2) * 3) / 3) % 5
        self.assertEqual(r.right.v, 5)
        self.assertEqual(r.left.right.v, 3)
        self.assertEqual(r.left.left.right.v, 3)
        self.assertEqual(r.left.left.left.right.v, 2)
        self.assertEqual(r.left.left.left.left.right.v, 1)
        self.assertEqual(r.left.left.left.left.left.v, 20)

        self.assertEqual(r.eval({}), ((((20 + 1) - 2) * 3) / 3) % 5)

    def testArithmeticR(self):
        t = Constant(20)
        r = 40000 % (1000 / (3 * (2 - (1 + t))))
        self.assertEqual(r.left.v, 40000)
        self.assertEqual(r.right.left.v, 1000)
        self.assertEqual(r.right.right.left.v, 3)
        self.assertEqual(r.right.right.right.left.v, 2)
        self.assertEqual(r.right.right.right.right.left.v, 1)
        self.assertEqual(r.right.right.right.right.right.v, 20)

        self.assertEqual(r.eval({}), 40000 % (1000 / (3 * (2 - (1 + 20)))))

    def testBooleans(self):
        for a in (True, False):
            r = Not(Constant(a))
            self.assertEqual(r.sub.v, a)
            self.assertEqual(r.eval({}), not a)

            for b in (True, False):
                r = Or(Constant(a), Constant(b))
                self.assertEqual(r.left.v, a)
                self.assertEqual(r.right.v, b)
                self.assertEquals(r.eval({}), a or b)

                r = And(Constant(a), Constant(b))
                self.assertEqual(r.left.v, a)
                self.assertEqual(r.right.v, b)
                self.assertEquals(r.eval({}), a and b)

                r = Implies(Constant(a), Constant(b))
                self.assertEqual(r.left.v, a)
                self.assertEqual(r.right.v, b)
                self.assertEquals(r.eval({}), (not a) or b)

    def testComparisons(self):
        a = Constant(20)
        
        b = a == 40
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 40)
        self.assertEqual(b.eval({}), False)

        b = a != 40
        self.assertEqual(b.sub.left.v, 20)
        self.assertEqual(b.sub.right.v, 40)
        self.assertEqual(b.eval({}), True)

        b = a > 40
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 40)
        self.assertEqual(b.eval({}), False)

        b = a >= 40
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 40)
        self.assertEqual(b.eval({}), False)

        b = a < 40
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 40)
        self.assertEqual(b.eval({}), True)

        b = a <= 40
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 40)
        self.assertEqual(b.eval({}), True)
 
        b = 40 == a
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 40)
        self.assertEqual(b.eval({}), False)

        b = 40 != a
        self.assertEqual(b.sub.left.v, 20)
        self.assertEqual(b.sub.right.v, 40)
        self.assertEqual(b.eval({}), True)

        b = 40 > a
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 40)
        self.assertEqual(b.eval({}), True)

        b = 40 >= a
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 40)
        self.assertEqual(b.eval({}), True)

        b = 40 < a
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 40)
        self.assertEqual(b.eval({}), False)

        b = 40 <= a
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 40)
        self.assertEqual(b.eval({}), False)

        b = a == 20
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 20)
        self.assertEqual(b.eval({}), True)

        b = a != 20
        self.assertEqual(b.sub.left.v, 20)
        self.assertEqual(b.sub.right.v, 20)
        self.assertEqual(b.eval({}), False)

        b = a > 20
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 20)
        self.assertEqual(b.eval({}), False)

        b = a >= 20
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 20)
        self.assertEqual(b.eval({}), True)

        b = a < 20
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 20)
        self.assertEqual(b.eval({}), False)

        b = a <= 20
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 20)
        self.assertEqual(b.eval({}), True)
 
        b = 20 == a
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 20)
        self.assertEqual(b.eval({}), True)

        b = 20 != a
        self.assertEqual(b.sub.left.v, 20)
        self.assertEqual(b.sub.right.v, 20)
        self.assertEqual(b.eval({}), False)

        b = 20 > a
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 20)
        self.assertEqual(b.eval({}), False)

        b = 20 >= a
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 20)
        self.assertEqual(b.eval({}), True)

        b = 20 < a
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 20)
        self.assertEqual(b.eval({}), False)

        b = 20 <= a
        self.assertEqual(b.left.v, 20)
        self.assertEqual(b.right.v, 20)
        self.assertEqual(b.eval({}), True)

    def testPartialEval(self):
        JeevesLib.init()

        l = Var("l")

        a = Facet(l, Constant(1), Constant(2))
        ap = partialEval(a)
        self.assertTrue(isPureFacetTree(ap))
        self.assertEqual(ap.eval({l:True}), 1)
        self.assertEqual(ap.eval({l:False}), 2)

        a = Facet(l, Add(Constant(1), Constant(-1)), Constant(2))
        ap = partialEval(a)
        self.assertTrue(isPureFacetTree(ap))
        self.assertEqual(ap.eval({l:True}), 0)
        self.assertEqual(ap.eval({l:False}), 2)

        a = Add(
            Facet(l, Constant(1), Constant(10)),
            Facet(l, Constant(100), Constant(1000))
        )
        ap = partialEval(a)
        self.assertTrue(isPureFacetTree(ap))
        self.assertEqual(ap.eval({l:True}), 101)
        self.assertEqual(ap.eval({l:False}), 1010)

        l1 = Var("l1")
        l2 = Var("l2")
        a = Add(
            Facet(l1, Constant(1), Constant(10)),
            Facet(l2, Constant(100), Constant(1000))
        )
        ap = partialEval(a)
        self.assertTrue(isPureFacetTree(ap))
        self.assertEqual(ap.eval({l1:True, l2:True}), 101)
        self.assertEqual(ap.eval({l1:True, l2:False}), 1001)
        self.assertEqual(ap.eval({l1:False, l2:True}), 110)
        self.assertEqual(ap.eval({l1:False, l2:False}), 1010)



########NEW FILE########
__FILENAME__ = testJeevesConfidentiality
'''
This tests code after the macro transformation.

Before the transformation, there would be calls to mkLabel and restrict but
the jifs should be gone. It would also 
'''
#import macropy.activate
import JeevesLib
from smt.Z3 import *
import unittest
from JeevesLib import PositiveVariable, NegativeVariable

class TestJeevesConfidentiality(unittest.TestCase):
  def setUp(self):
    self.s = Z3()
    # reset the Jeeves state
    JeevesLib.init()

  def test_restrict_all_permissive(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda _: True)
    xConcrete = JeevesLib.concretize(None, x)
    # make sure that concretizing x allows everyone to see
    self.assertTrue(xConcrete)

  def test_restrict_all_restrictive(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda _: False)
    xConcrete = JeevesLib.concretize(None, x)
    self.assertFalse(xConcrete)

  def test_restrict_with_context(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda y: y == 2)

    xConcrete = JeevesLib.concretize(2, x)
    self.assertTrue(xConcrete)

    xConcrete = JeevesLib.concretize(3, x)
    self.assertFalse(xConcrete)

  def test_restrict_with_sensitivevalue(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda y: y == 2)
    value = JeevesLib.mkSensitive(x, 42, 41)

    valueConcrete = JeevesLib.concretize(2, value)
    self.assertEquals(valueConcrete, 42)

    valueConcrete = JeevesLib.concretize(1, value)
    self.assertEquals(valueConcrete, 41)

  def test_restrict_with_cyclic(self):
    jl = JeevesLib

    # use the value itself as the context
    x = jl.mkLabel('x')
    jl.restrict(x, lambda ctxt : ctxt == 42)

    value = jl.mkSensitive(x, 42, 20)
    self.assertEquals(jl.concretize(value, value), 42)

    value = jl.mkSensitive(x, 41, 20)
    self.assertEquals(jl.concretize(value, value), 20)

  def test_jif_with_ints(self):
    jl = JeevesLib

    x = jl.mkLabel('x')
    jl.restrict(x, lambda ctxt : ctxt == 42)

    a = jl.jif(x, lambda:13, lambda:17 )
    self.assertEquals(jl.concretize(42, a), 13)
    self.assertEquals(jl.concretize(-2, a), 17)

    b = jl.jif(True, lambda:13, lambda:17)
    self.assertEquals(jl.concretize(42, b), 13)
    self.assertEquals(jl.concretize(-2, b), 13)

    c = jl.jif(False, lambda:13, lambda:17)
    self.assertEquals(jl.concretize(42, c), 17)
    self.assertEquals(jl.concretize(-2, c), 17)

    conditional = jl.mkSensitive(x, True, False)
    d = jl.jif(conditional, lambda:13, lambda:17)
    self.assertEquals(jl.concretize(42, d), 13)
    self.assertEquals(jl.concretize(-2, d), 17)

    conditional = jl.mkSensitive(x, False, True)
    d = jl.jif(conditional, lambda:13, lambda:17)
    self.assertEquals(jl.concretize(42, d), 17)
    self.assertEquals(jl.concretize(-2, d), 13)

    y = jl.mkLabel('y')
    z = jl.mkLabel('z')
    jl.restrict(y, lambda (a,_) : a)
    jl.restrict(z, lambda (_,a) : a)
    faceted_int = jl.mkSensitive(y, 10, 0)
    conditional = faceted_int > 5
    i1 = jl.mkSensitive(z, 101, 102)
    i2 = jl.mkSensitive(z, 103, 104)
    f = jl.jif(conditional, lambda:i1, lambda:i2)
    self.assertEquals(jl.concretize((True, True), f),101)
    self.assertEquals(jl.concretize((True, False), f), 102)
    self.assertEquals(jl.concretize((False, True), f), 103)
    self.assertEquals(jl.concretize((False, False), f), 104)

  def test_jif_with_objects(self):
    return NotImplemented

  def test_restrict_under_conditional(self):
    jl = JeevesLib

    x = jl.mkLabel('x')
    def yes_restrict():
        jl.restrict(x, lambda ctxt : ctxt == 1)
    def no_restrict():
        pass

    value = jl.mkSensitive(x, 42, 0)
    jl.jif(value == 42, yes_restrict, no_restrict)
    self.assertEquals(jl.concretize(0, value), 0)
    self.assertEquals(jl.concretize(1, value), 42)

    y = jl.mkLabel('y')
    def yes_restrict():
        jl.restrict(y, lambda ctxt : ctxt == 1)
    def no_restrict():
        pass

    value = jl.mkSensitive(y, 43, 0)
    jl.jif(value == 42, yes_restrict, no_restrict)
    self.assertEquals(jl.concretize(0, value), 43)
    self.assertEquals(jl.concretize(1, value), 43)

  def test_jbool_functions_constants(self):
    jl = JeevesLib

    self.assertEquals(jl.jand(lambda:True, lambda:True), True)
    self.assertEquals(jl.jand(lambda:True, lambda:False), False)
    self.assertEquals(jl.jand(lambda:False, lambda:True), False)
    self.assertEquals(jl.jand(lambda:False, lambda:False), False)

    self.assertEquals(jl.jor(lambda:True, lambda:True), True)
    self.assertEquals(jl.jor(lambda:True, lambda:False), True)
    self.assertEquals(jl.jor(lambda:False, lambda:True), True)
    self.assertEquals(jl.jor(lambda:False, lambda:False), False)

    self.assertEquals(jl.jnot(True), False)
    self.assertEquals(jl.jnot(False), True)

  def test_jbool_functions_fexprs(self):
    jl = JeevesLib

    x = jl.mkLabel('x')
    jl.restrict(x, lambda (a,_) : a == 42)

    for lh in (True, False):
      for ll in (True, False):
        for rh in (True, False):
          for rl in (True, False):
            l = jl.mkSensitive(x, lh, ll)
            r = jl.mkSensitive(x, rh, rl)
            self.assertEquals(jl.concretize((42,0), jl.jand(lambda:l, lambda:r)), lh and rh)
            self.assertEquals(jl.concretize((10,0), jl.jand(lambda:l, lambda:r)), ll and rl)
            self.assertEquals(jl.concretize((42,0), jl.jor(lambda:l, lambda:r)), lh or rh)
            self.assertEquals(jl.concretize((10,0), jl.jor(lambda:l, lambda:r)), ll or rl)
            self.assertEquals(jl.concretize((42,0), jl.jnot(l)), not lh)
            self.assertEquals(jl.concretize((10,0), jl.jnot(l)), not ll)

    y = jl.mkLabel('y')
    jl.restrict(y, lambda (_,b) : b == 42)

    for lh in (True, False):
      for ll in (True, False):
        for rh in (True, False):
          for rl in (True, False):
            l = jl.mkSensitive(x, lh, ll)
            r = jl.mkSensitive(y, rh, rl)
            self.assertEquals(jl.concretize((42,0), jl.jand(lambda:l, lambda:r)), lh and rl)
            self.assertEquals(jl.concretize((10,0), jl.jand(lambda:l, lambda:r)), ll and rl)
            self.assertEquals(jl.concretize((42,42), jl.jand(lambda:l, lambda:r)), lh and rh)
            self.assertEquals(jl.concretize((10,42), jl.jand(lambda:l, lambda:r)), ll and rh)

            self.assertEquals(jl.concretize((42,0), jl.jor(lambda:l, lambda:r)), lh or rl)
            self.assertEquals(jl.concretize((10,0), jl.jor(lambda:l, lambda:r)), ll or rl)
            self.assertEquals(jl.concretize((42,42), jl.jor(lambda:l, lambda:r)), lh or rh)
            self.assertEquals(jl.concretize((10,42), jl.jor(lambda:l, lambda:r)), ll or rh)

  def test_nested_conditionals_no_shared_path(self):
    return NotImplemented

  def test_nested_conditionals_shared_path(self):
    return NotImplemented

  def test_jif_with_assign(self):
    jl = JeevesLib

    y = jl.mkLabel('y')
    jl.restrict(y, lambda ctxt : ctxt == 42)

    value0 = jl.mkSensitive(y, 0, 1)
    value2 = jl.mkSensitive(y, 2, 3)

    value = value0
    value = jl.jassign(value, value2)
    self.assertEquals(jl.concretize(42, value), 2)
    self.assertEquals(jl.concretize(10, value), 3)

    value = 100
    value = jl.jassign(value, value2)
    self.assertEquals(jl.concretize(42, value), 2)
    self.assertEquals(jl.concretize(10, value), 3)

    value = value0
    value = jl.jassign(value, 200)
    self.assertEquals(jl.concretize(42, value), 200)
    self.assertEquals(jl.concretize(10, value), 200)

    value = 100
    value = jl.jassign(value, 200)
    self.assertEquals(jl.concretize(42, value), 200)
    self.assertEquals(jl.concretize(10, value), 200)

  def test_jif_with_assign_with_pathvars(self):
    jl = JeevesLib

    x = jl.mkLabel('x')
    y = jl.mkLabel('y')
    jl.restrict(x, lambda (a,_) : a)
    jl.restrict(y, lambda (_,b) : b)

    value0 = jl.mkSensitive(y, 0, 1)
    value2 = jl.mkSensitive(y, 2, 3)

    value = value0
    with PositiveVariable(x):
      value = jl.jassign(value, value2)
    self.assertEquals(jl.concretize((True, True), value), 2)
    self.assertEquals(jl.concretize((True, False), value), 3)
    self.assertEquals(jl.concretize((False, True), value), 0)
    self.assertEquals(jl.concretize((False, False), value), 1)

    value = value0
    with NegativeVariable(x):
      value = jl.jassign(value, value2)
    self.assertEquals(jl.concretize((False, True), value), 2)
    self.assertEquals(jl.concretize((False, False), value), 3)
    self.assertEquals(jl.concretize((True, True), value), 0)
    self.assertEquals(jl.concretize((True, False), value), 1)

  def test_function_facets(self):
    def add1(a):
        return a+1
    def add2(a):
        return a+2

    jl = JeevesLib

    x = jl.mkLabel('x')
    jl.restrict(x, lambda ctxt : ctxt == 42)

    fun = jl.mkSensitive(x, add1, add2)
    value = fun(15)
    self.assertEquals(jl.concretize(42, value), 16)
    self.assertEquals(jl.concretize(41, value), 17)

  def test_objects_faceted(self):
    class TestClass:
      def __init__(self, a, b):
        self.a = a
        self.b = b

    jl = JeevesLib

    x = jl.mkLabel('x')
    jl.restrict(x, lambda ctxt : ctxt)

    y = jl.mkSensitive(x,
      TestClass(1, 2),
      TestClass(3, 4))

    self.assertEquals(jl.concretize(True, y.a), 1)
    self.assertEquals(jl.concretize(True, y.b), 2)
    self.assertEquals(jl.concretize(False, y.a), 3)
    self.assertEquals(jl.concretize(False, y.b), 4)

  def test_objects_mutate(self):
    class TestClass:
      def __init__(self, a, b):
        self.__dict__['a'] = a
        self.__dict__['b'] = b
      def __setattr__(self, attr, val):
        self.__dict__[attr] = JeevesLib.jassign(
            self.__dict__[attr], val)

    jl = JeevesLib

    x = jl.mkLabel('x')
    jl.restrict(x, lambda ctxt : ctxt)

    s = TestClass(1, None)
    t = TestClass(3, None)
    y = jl.mkSensitive(x, s, t)

    def mut():
      y.a = y.a + 100
    def nonmut():
      pass

    jl.jif(y.a == 1, mut, nonmut)

    self.assertEquals(jl.concretize(True, y.a), 101)
    self.assertEquals(jl.concretize(True, s.a), 101)
    self.assertEquals(jl.concretize(True, t.a), 3)
    self.assertEquals(jl.concretize(False, y.a), 3)
    self.assertEquals(jl.concretize(False, s.a), 1)
    self.assertEquals(jl.concretize(False, t.a), 3)

  def test_objects_methodcall(self):
    class TestClassMethod:
      def __init__(self, a, b):
        self.a = a
        self.b = b
      def add_a_to_b(self):
        self.b = JeevesLib.jassign(self.b, self.a + self.b)
      def return_sum(self):
        return self.a + self.b

    jl = JeevesLib

    x = jl.mkLabel('x')
    jl.restrict(x, lambda ctxt : ctxt)

    s = TestClassMethod(1, 10)
    t = TestClassMethod(100, 1000)
    y = jl.mkSensitive(x, s, t)

    self.assertEquals(jl.concretize(True, y.return_sum()), 11)
    self.assertEquals(jl.concretize(False, y.return_sum()), 1100)

    y.add_a_to_b()
    self.assertEquals(jl.concretize(True, s.a), 1)
    self.assertEquals(jl.concretize(True, s.b), 11)
    self.assertEquals(jl.concretize(True, t.a), 100)
    self.assertEquals(jl.concretize(True, t.b), 1000)
    self.assertEquals(jl.concretize(True, y.a), 1)
    self.assertEquals(jl.concretize(True, y.b), 11)
    self.assertEquals(jl.concretize(False, s.a), 1)
    self.assertEquals(jl.concretize(False, s.b), 10)
    self.assertEquals(jl.concretize(False, t.a), 100)
    self.assertEquals(jl.concretize(False, t.b), 1100)
    self.assertEquals(jl.concretize(False, y.a), 100)
    self.assertEquals(jl.concretize(False, y.b), 1100)

  def test_objects_eq_is(self):
    class TestClass:
      def __init__(self, a):
        self.a = a
    class TestClassEq:
      def __init__(self, a):
        self.a = a
      def __eq__(self, other):
        return self.a == other.a
      def __ne__(self, other):
        return self.a != other.a
      def __lt__(self, other):
        return self.a < other.a
      def __gt__(self, other):
        return self.a > other.a
      def __le__(self, other):
        return self.a <= other.a
      def __ge__(self, other):
        return self.a >= other.a

    jl = JeevesLib
    x = jl.mkLabel('x')
    jl.restrict(x, lambda ctxt : ctxt)

    a = TestClass(3)
    b = TestClass(3)
    c = TestClass(2)

    # Ensure that a < b and b < c (will probably be true anyway,
    # just making sure)
    a, b, c = sorted((a, b, c))
    a.a, b.a, c.a = 3, 3, 2

    v1 = jl.mkSensitive(x, a, c)
    v2 = jl.mkSensitive(x, b, c)
    v3 = jl.mkSensitive(x, c, a)
    self.assertEquals(jl.concretize(True, v1 == v1), True)
    self.assertEquals(jl.concretize(True, v2 == v2), True)
    self.assertEquals(jl.concretize(True, v3 == v3), True)
    self.assertEquals(jl.concretize(True, v1 == v2), False)
    self.assertEquals(jl.concretize(True, v2 == v3), False)
    self.assertEquals(jl.concretize(True, v3 == v1), False)

    self.assertEquals(jl.concretize(True, v1 != v1), False)
    self.assertEquals(jl.concretize(True, v2 != v2), False)
    self.assertEquals(jl.concretize(True, v3 != v3), False)
    self.assertEquals(jl.concretize(True, v1 != v2), True)
    self.assertEquals(jl.concretize(True, v2 != v3), True)
    self.assertEquals(jl.concretize(True, v3 != v1), True)

    self.assertEquals(jl.concretize(True, v1 < v1), False)
    self.assertEquals(jl.concretize(True, v2 < v2), False)
    self.assertEquals(jl.concretize(True, v3 < v3), False)
    self.assertEquals(jl.concretize(True, v1 < v2), True)
    self.assertEquals(jl.concretize(True, v2 < v3), True)
    self.assertEquals(jl.concretize(True, v3 < v1), False)

    self.assertEquals(jl.concretize(True, v1 > v1), False)
    self.assertEquals(jl.concretize(True, v2 > v2), False)
    self.assertEquals(jl.concretize(True, v3 > v3), False)
    self.assertEquals(jl.concretize(True, v1 > v2), False)
    self.assertEquals(jl.concretize(True, v2 > v3), False)
    self.assertEquals(jl.concretize(True, v3 > v1), True)

    self.assertEquals(jl.concretize(True, v1 <= v1), True)
    self.assertEquals(jl.concretize(True, v2 <= v2), True)
    self.assertEquals(jl.concretize(True, v3 <= v3), True)
    self.assertEquals(jl.concretize(True, v1 <= v2), True)
    self.assertEquals(jl.concretize(True, v2 <= v3), True)
    self.assertEquals(jl.concretize(True, v3 <= v1), False)

    self.assertEquals(jl.concretize(True, v1 >= v1), True)
    self.assertEquals(jl.concretize(True, v2 >= v2), True)
    self.assertEquals(jl.concretize(True, v3 >= v3), True)
    self.assertEquals(jl.concretize(True, v1 >= v2), False)
    self.assertEquals(jl.concretize(True, v2 >= v3), False)
    self.assertEquals(jl.concretize(True, v3 >= v1), True)

    self.assertEquals(jl.concretize(False, v2 == v3), False)
    self.assertEquals(jl.concretize(False, v2 != v3), True)
    self.assertEquals(jl.concretize(False, v2 < v3), False)
    self.assertEquals(jl.concretize(False, v2 > v3), True)
    self.assertEquals(jl.concretize(False, v2 <= v3), False)
    self.assertEquals(jl.concretize(False, v2 >= v3), True)

    a = TestClassEq(3)
    b = TestClassEq(3)
    c = TestClassEq(2)

    v1 = jl.mkSensitive(x, a, c)
    v2 = jl.mkSensitive(x, b, c)
    v3 = jl.mkSensitive(x, c, a)
    self.assertEquals(jl.concretize(True, v1 == v1), True)
    self.assertEquals(jl.concretize(True, v2 == v2), True)
    self.assertEquals(jl.concretize(True, v3 == v3), True)
    self.assertEquals(jl.concretize(True, v1 == v2), True)
    self.assertEquals(jl.concretize(True, v2 == v3), False)
    self.assertEquals(jl.concretize(True, v3 == v1), False)

    self.assertEquals(jl.concretize(True, v1 != v1), False)
    self.assertEquals(jl.concretize(True, v2 != v2), False)
    self.assertEquals(jl.concretize(True, v3 != v3), False)
    self.assertEquals(jl.concretize(True, v1 != v2), False)
    self.assertEquals(jl.concretize(True, v2 != v3), True)
    self.assertEquals(jl.concretize(True, v3 != v1), True)

    self.assertEquals(jl.concretize(True, v1 < v1), False)
    self.assertEquals(jl.concretize(True, v2 < v2), False)
    self.assertEquals(jl.concretize(True, v3 < v3), False)
    self.assertEquals(jl.concretize(True, v1 < v2), False)
    self.assertEquals(jl.concretize(True, v2 < v3), False)
    self.assertEquals(jl.concretize(True, v3 < v1), True)

    self.assertEquals(jl.concretize(True, v1 > v1), False)
    self.assertEquals(jl.concretize(True, v2 > v2), False)
    self.assertEquals(jl.concretize(True, v3 > v3), False)
    self.assertEquals(jl.concretize(True, v1 > v2), False)
    self.assertEquals(jl.concretize(True, v2 > v3), True)
    self.assertEquals(jl.concretize(True, v3 > v1), False)

    self.assertEquals(jl.concretize(True, v1 <= v1), True)
    self.assertEquals(jl.concretize(True, v2 <= v2), True)
    self.assertEquals(jl.concretize(True, v3 <= v3), True)
    self.assertEquals(jl.concretize(True, v1 <= v2), True)
    self.assertEquals(jl.concretize(True, v2 <= v3), False)
    self.assertEquals(jl.concretize(True, v3 <= v1), True)

    self.assertEquals(jl.concretize(True, v1 >= v1), True)
    self.assertEquals(jl.concretize(True, v2 >= v2), True)
    self.assertEquals(jl.concretize(True, v3 >= v3), True)
    self.assertEquals(jl.concretize(True, v1 >= v2), True)
    self.assertEquals(jl.concretize(True, v2 >= v3), True)
    self.assertEquals(jl.concretize(True, v3 >= v1), False)

    self.assertEquals(jl.concretize(False, v2 == v3), False)
    self.assertEquals(jl.concretize(False, v2 != v3), True)
    self.assertEquals(jl.concretize(False, v2 < v3), True)
    self.assertEquals(jl.concretize(False, v2 > v3), False)
    self.assertEquals(jl.concretize(False, v2 <= v3), True)
    self.assertEquals(jl.concretize(False, v2 >= v3), False)

  def test_objects_operators(self):
    return NotImplemented

  def test_objects_delattr(self):
    return NotImplemented

  def test_objects_hasattr(self):
    return NotImplemented

  def test_objects_callable(self):
    return NotImplemented

  def test_functions_operators(self):
    return NotImplemented

  def test_accessing_special_attributes(self):
    return NotImplemented

  def test_attribute_names(self):
    return NotImplemented

  def test_jhasElt(self):
    jl = JeevesLib

    a = jl.mkLabel ()
    jl.restrict(a, lambda x: x)
    xS = jl.mkSensitive(a, 42, 1)

    b = jl.mkLabel ()
    jl.restrict(b, lambda x: x)
    yS = jl.mkSensitive(b, 43, 3)

    lst = [xS, 2, yS]
    self.assertTrue(jl.concretize(True, jl.jhasElt(lst, lambda x: x == 42)))
    self.assertFalse(jl.concretize(False, jl.jhasElt(lst, lambda x: x == 42)))
    self.assertFalse(jl.concretize(True, jl.jhasElt(lst, lambda x: x == 1)))
    self.assertTrue(jl.concretize(False, jl.jhasElt(lst, lambda x: x == 1)))
    self.assertTrue(jl.concretize(True, jl.jhasElt(lst, lambda x: x == 43)))
    self.assertFalse(jl.concretize(False, jl.jhasElt(lst, lambda x: x == 43)))
    self.assertFalse(jl.concretize(True, jl.jhasElt(lst, lambda x: x == 3)))
    self.assertTrue(jl.concretize(False, jl.jhasElt(lst, lambda x: x == 3)))

  def test_jhas_empty(self):
    jl = JeevesLib
    lst = []
    self.assertFalse(jl.concretize(True, jl.jhas(lst, 2)))

  def test_jhas_in_policy(self):
    jl = JeevesLib
    a = jl.mkLabel ()
    jl.restrict(a, lambda oc: jl.jhas(oc, 3))
    self.assertTrue(jl.concretize([1, 2, 3], a))
    self.assertTrue(jl.concretize([3], a))
    self.assertFalse(jl.concretize([], a))
    self.assertFalse(jl.concretize([1, 2], a))

  def test_jall(self):
    jl = JeevesLib
    a = jl.mkLabel ()
    jl.restrict(a, lambda x: x)
    xS = jl.mkSensitive(a, True, False)

    b = jl.mkLabel ()
    jl.restrict(b, lambda x: jl.jnot(x) )
    yS = jl.mkSensitive(b, False, True)

    lst = [xS, True, yS]

    self.assertTrue(jl.concretize(True, jl.jall(lst)))
    self.assertFalse(jl.concretize(False, jl.jall(lst)))

  def test_list(self):
    jl = JeevesLib
    x = jl.mkLabel('x')
    jl.restrict(x, lambda ctxt : ctxt)

    l = jl.mkSensitive(x, [40,41,42], [0,1,2,3])

    self.assertEqual(jl.concretize(True, l[0]), 40)
    self.assertEqual(jl.concretize(True, l[1]), 41)
    self.assertEqual(jl.concretize(True, l[2]), 42)
    self.assertEqual(jl.concretize(False, l[0]), 0)
    self.assertEqual(jl.concretize(False, l[1]), 1)
    self.assertEqual(jl.concretize(False, l[2]), 2)
    self.assertEqual(jl.concretize(False, l[3]), 3)

    self.assertEqual(jl.concretize(True, l.__len__()), 3)
    self.assertEqual(jl.concretize(False, l.__len__()), 4)

    l[1] = 19

    self.assertEqual(jl.concretize(True, l[0]), 40)
    self.assertEqual(jl.concretize(True, l[1]), 19)
    self.assertEqual(jl.concretize(True, l[2]), 42)
    self.assertEqual(jl.concretize(False, l[0]), 0)
    self.assertEqual(jl.concretize(False, l[1]), 19)
    self.assertEqual(jl.concretize(False, l[2]), 2)
    self.assertEqual(jl.concretize(False, l[3]), 3)

  def test_jmap_listcomp(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda ctxt : ctxt)

    l = JeevesLib.mkSensitive(x, [0,1,2], [3,4,5,6])
    m = JeevesLib.jmap(l, lambda x : x*x)

    self.assertEqual(JeevesLib.concretize(True, m[0]), 0)
    self.assertEqual(JeevesLib.concretize(True, m[1]), 1)
    self.assertEqual(JeevesLib.concretize(True, m[2]), 4)
    self.assertEqual(JeevesLib.concretize(False, m[0]), 9)
    self.assertEqual(JeevesLib.concretize(False, m[1]), 16)
    self.assertEqual(JeevesLib.concretize(False, m[2]), 25)
    self.assertEqual(JeevesLib.concretize(False, m[3]), 36)

  def test_jlist(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda ctxt : ctxt)

    l = JeevesLib.mkSensitive(x, JeevesLib.JList([0,1,2]), JeevesLib.JList([3,4,5,6]))
    def add10():
      l.append(10)
    def add11():
      l.append(11)
    JeevesLib.jif(x, add10, add11)

    self.assertEqual(JeevesLib.concretize(True, l[0]), 0)
    self.assertEqual(JeevesLib.concretize(True, l[1]), 1)
    self.assertEqual(JeevesLib.concretize(True, l[2]), 2)
    self.assertEqual(JeevesLib.concretize(True, l[3]), 10)
    self.assertEqual(JeevesLib.concretize(False, l[0]), 3)
    self.assertEqual(JeevesLib.concretize(False, l[1]), 4)
    self.assertEqual(JeevesLib.concretize(False, l[2]), 5)
    self.assertEqual(JeevesLib.concretize(False, l[3]), 6)
    self.assertEqual(JeevesLib.concretize(False, l[4]), 11)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = testJeevesWrite
'''
This tests write policies.
'''
import unittest
from sourcetrans.macro_module import macros, jeeves
from fast.ProtectedRef import ProtectedRef, UpdateResult
import JeevesLib

class DummyUser:
  def __init__(self, userId):
    self.userId = userId
  def __eq__(self, other):
    return self.userId == other.userId

class TestJeevesWrite(unittest.TestCase):
  def setUp(self):
    # reset the Jeeves state
    JeevesLib.init()
    self.nobodyUser = DummyUser(-1)
    self.aliceUser = DummyUser(0)
    self.bobUser = DummyUser(1)
    self.carolUser = DummyUser(2)

  def allowUserWrite(self, user):
    return lambda _this: lambda ictxt: lambda octxt: ictxt == user

  def test_write_allowed_for_all_viewers(self):
    x = ProtectedRef(0, None, self.allowUserWrite(self.aliceUser))
    assert x.update(self.aliceUser, self.aliceUser, 42) == UpdateResult.Unknown
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v), 42)
    self.assertEqual(JeevesLib.concretize(self.bobUser, x.v), 42)
    self.assertEqual(JeevesLib.concretize(self.carolUser, x.v), 42)

  def test_write_disallowed_for_all_viewers(self):
    x = ProtectedRef(0, None, self.allowUserWrite(self.aliceUser))
    assert x.update(self.bobUser, self.bobUser, 42) == UpdateResult.Unknown
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v), 0)
    self.assertEqual(JeevesLib.concretize(self.bobUser, x.v), 0)
    self.assertEqual(JeevesLib.concretize(self.carolUser, x.v), 0)

  @jeeves
  def test_write_selectively_allowed(self):
    x = ProtectedRef(0, None
          , lambda _this: lambda ictxt: lambda octxt:
              ictxt == self.aliceUser and octxt == self.bobUser)
    assert x.update(self.aliceUser, self.aliceUser, 42) == UpdateResult.Unknown
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v), 0)
    self.assertEqual(JeevesLib.concretize(self.bobUser, x.v), 42)
    self.assertEqual(JeevesLib.concretize(self.carolUser, x.v), 0)

  def test_permitted_writer_overwrite(self):  
    x = ProtectedRef(0, None, self.allowUserWrite(self.bobUser))
    assert x.update(self.aliceUser, self.aliceUser, 42) == UpdateResult.Unknown
    assert x.update(self.bobUser, self.bobUser, 43) == UpdateResult.Unknown
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v), 43)
    self.assertEqual(JeevesLib.concretize(self.bobUser, x.v), 43)
    self.assertEqual(JeevesLib.concretize(self.carolUser, x.v), 43)

  @jeeves
  def test_output_varies_depending_on_viewer(self):
    x = ProtectedRef(0, None
          , lambda _this: lambda ictxt: lambda octxt:
              ictxt == self.aliceUser and octxt == self.bobUser)
    x.update(self.aliceUser, self.aliceUser, 42)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v), 0)
    self.assertEqual(JeevesLib.concretize(self.bobUser, x.v), 42)
    self.assertEqual(JeevesLib.concretize(self.carolUser, x.v), 0)

  @jeeves
  def test_combining_write_policies_in_operation(self):
    x = ProtectedRef(0, None, self.allowUserWrite(self.bobUser))
    x.update(self.bobUser, self.bobUser, 42)
    y = ProtectedRef(2, None
      , lambda _this: lambda ictxt: lambda octxt:
          ictxt == self.aliceUser and octxt == self.bobUser)
    y.update(self.aliceUser, self.aliceUser, 43)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v + y.v), 44)
    self.assertEqual(JeevesLib.concretize(self.bobUser, x.v + y.v), 85)
    self.assertEqual(JeevesLib.concretize(self.carolUser, x.v + y.v), 44)

  # Alice is allowed to write to x and only Bob is allowed to write to y.
  # Our write policies disallow Bob from accidentally writing a value from
  # Alice into y. (That is, without an explicit endorsement...)
  def test_prevent_flow_of_untrusted_writes(self):
    x = ProtectedRef(0, None, self.allowUserWrite(self.aliceUser))
    assert x.update(self.aliceUser, self.aliceUser, 42) == UpdateResult.Unknown
    y = ProtectedRef(1, None, self.allowUserWrite(self.bobUser))
    assert y.update(self.bobUser, self.bobUser, x.v) == UpdateResult.Unknown
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v), 42)
    self.assertEqual(JeevesLib.concretize(self.bobUser, x.v), 42)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, y.v), 0)
    self.assertEqual(JeevesLib.concretize(self.bobUser, y.v), 0)   

  def test_prevent_flow_of_operations_on_untrusted_writes(self):
    x = ProtectedRef(0, None, self.allowUserWrite(self.aliceUser))
    x.update(self.aliceUser, self.aliceUser, 42)
    y = ProtectedRef(1, None, self.allowUserWrite(self.bobUser))
    y.update(self.bobUser, self.bobUser, 43)
    z = ProtectedRef(0, None, self.allowUserWrite(self.carolUser))
    z.update(self.carolUser, self.carolUser, x.v + y.v)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, z.v), 1)
    self.assertEqual(JeevesLib.concretize(self.bobUser, z.v), 1)
    self.assertEqual(JeevesLib.concretize(self.carolUser, z.v), 1)

  # Alice is allowed to write to x and only Bob is allowed to write to y.
  # Our policy enforcement prevents Alice from influencing values that Bob
  # writes.
  @jeeves
  def test_prevent_untrusted_writes_through_implicit_flows(self):
    x = ProtectedRef(0, None, self.allowUserWrite(self.aliceUser))
    x.update(self.aliceUser, self.aliceUser, 42)
    y = ProtectedRef(1, None, self.allowUserWrite(self.bobUser))
    y.update(self.bobUser, self.bobUser, 2 if x.v == 42 else 3)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, y.v), 3)
    self.assertEqual(JeevesLib.concretize(self.bobUser, y.v), 3)

  @jeeves
  def test_prevent_implicit_flows_of_confidential_values(self):
    x = ProtectedRef(0, None
          , lambda _this: lambda ictxt: lambda octxt:
              ictxt == self.aliceUser and octxt == self.aliceUser)
    x.update(self.aliceUser, self.aliceUser, 42)
    y = ProtectedRef(1, None
          , lambda _this: lambda ictxt: lambda octxt:
              ictxt == self.bobUser or ictxt == self.aliceUser)
    y.update(self.bobUser, self.bobUser, 2 if x.v == 42 else 3)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, y.v), 2)
    self.assertEqual(JeevesLib.concretize(self.bobUser, y.v), 3)

  # If Alice and Bob are allowed to write to x and y respectively, then
  # x + y should be allowed to be written to a value where they are both
  # allowed to write.
  def test_combining_values_into_permissive_write(self):
    x = ProtectedRef(0, None, self.allowUserWrite(self.bobUser))
    x.update(self.bobUser, self.bobUser, 42)
    y = ProtectedRef(1, None, self.allowUserWrite(self.aliceUser))
    y.update(self.aliceUser, self.aliceUser, 43)
    z = ProtectedRef(0, None
          , lambda _this: lambda ictxt: lambda otxt:
              ictxt == self.aliceUser or ictxt == self.bobUser
                or ictxt == self.carolUser)
    z.update(self.carolUser, self.carolUser, x.v + y.v)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, z.v), 85)
    self.assertEqual(JeevesLib.concretize(self.bobUser, z.v), 85)
    self.assertEqual(JeevesLib.concretize(self.carolUser, z.v), 85)

  # Only bob can see the special value alice wrote to him...
  @jeeves
  def test_combining_confidentiality_with_operations(self):  
    x = ProtectedRef(0, None, self.allowUserWrite(self.bobUser))
    x.update(self.bobUser, self.bobUser, 42)
    y = ProtectedRef(2, None
          , lambda _this: lambda ictxt: lambda octxt:
              ictxt == self.aliceUser and octxt == self.bobUser)
    y.update(self.aliceUser, self.aliceUser, 43)
    z = ProtectedRef(0, None
          , lambda _this: lambda ictxt: lambda octxt:
              ictxt == self.aliceUser or ictxt == self.bobUser
                or ictxt == self.carolUser)
    z.update(self.carolUser, self.carolUser,  x.v + y.v)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, z.v), 44)
    self.assertEqual(JeevesLib.concretize(self.bobUser, z.v), 85)
    self.assertEqual(JeevesLib.concretize(self.carolUser, z.v), 44)

  def test_write_policies_with_confidentiality(self):  
    # Make a sensitive value that is either Bob or the nobody user. Only Bob
    # can see this.
    a = JeevesLib.mkLabel ()
    JeevesLib.restrict(a, lambda ctxt: ctxt == self.bobUser)
    secretWriter = JeevesLib.mkSensitive(a, self.bobUser, self.nobodyUser)
    # We now make a protected reference where the input channel has to be the
    # secret writer.
    x = ProtectedRef(0, None
          , lambda _this: lambda ictxt: lambda octxt: ictxt == secretWriter)
    x.update(self.bobUser, self.bobUser, 42)
    self.assertEqual(JeevesLib.concretize(self.bobUser, secretWriter)
      , self.bobUser)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, secretWriter)
      , self.nobodyUser)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, secretWriter)
      , self.nobodyUser)
    # Only Bob should be able to see the value he wrote.
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v), 0)   
    self.assertEqual(JeevesLib.concretize(self.bobUser, x.v), 42)
    self.assertEqual(JeevesLib.concretize(self.carolUser, x.v), 0)
 
  def test_input_write_policies_with_confidentiality(self):
    # Make a sensitive value that is either Bob or the nobody user. Only Bob
    # can see this.
    a = JeevesLib.mkLabel ()
    JeevesLib.restrict(a, lambda ctxt: ctxt == self.bobUser)
    secretWriter = JeevesLib.mkSensitive(a, self.bobUser, self.nobodyUser)
    # We now make a protected reference where the input channel has to be the
    # secret writer.
    x = ProtectedRef(0
          , lambda _this: lambda ictxt: ictxt == secretWriter
          , None)
    x.update(self.bobUser, self.bobUser, 42)
    self.assertEqual(JeevesLib.concretize(self.bobUser, secretWriter)
      , self.bobUser)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, secretWriter)
      , self.nobodyUser)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, secretWriter)
      , self.nobodyUser)
    # Only Bob should be able to see the value he wrote.
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v), 42)
    self.assertEqual(JeevesLib.concretize(self.bobUser, x.v), 42)
    self.assertEqual(JeevesLib.concretize(self.carolUser, x.v), 42)
 
  # If Alice does something bad, then we will reject all of her influences.
  def test_determine_writer_trust_later(self):
    x = ProtectedRef(0, None
          , lambda _this: lambda ictxt: lambda octxt:
              JeevesLib.jhas(octxt, ictxt))
    x.update(self.aliceUser, self.aliceUser, 42)
    self.assertEqual(JeevesLib.concretize([self.aliceUser], x.v), 42)
    self.assertEqual(JeevesLib.concretize([], x.v), 0)

  def test_function_facets_allowed_to_write(self):
    def id(x):
      return x
    def inc(x):
      return x+1
    x = ProtectedRef(id, None, self.allowUserWrite(self.bobUser))
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v)(1), 1)
    x.update(self.bobUser, self.bobUser, inc)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v)(1), 2)
  
  def test_function_facets_cannot_write(self):
    def id(x):
      return x
    def inc(x):
      return x+1
    x = ProtectedRef(id, None, self.allowUserWrite(self.bobUser))
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v)(1), 1)
    x.update(self.aliceUser, self.aliceUser, inc)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v)(1), 1)

  @jeeves
  def test_output_write_policy_with_this_cannot_update(self):  
    x = ProtectedRef(0, None
          , lambda v: lambda ictxt: lambda _octxt:
              (not (v == 3)) and ictxt == self.aliceUser)    
    x.update(self.aliceUser, self.aliceUser, 1)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v), 1)
    x.update(self.aliceUser, self.aliceUser, 3)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v), 3)  
    x.update(self.aliceUser, self.aliceUser, 5)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v), 3)    

  @jeeves
  def test_output_write_policies_involving_this_can_update(self):
    x = ProtectedRef(0, None
          , lambda v: lambda ictxt: lambda _:
              v == 0 and ictxt == self.aliceUser)
    x.update(self.aliceUser, self.aliceUser, 1)
    print x.v.prettyPrint()
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v), 1)
    x.update(self.aliceUser, self.aliceUser, 3)
    print x.v.prettyPrint()
    self.assertEqual(JeevesLib.concretize(self.aliceUser, x.v), 1)

  def test_not_tracking_implicit_flows(self):
    x = ProtectedRef(0, None, self.allowUserWrite(self.aliceUser), False)
    x.update(self.aliceUser, self.aliceUser, 42)
    y = ProtectedRef(1, None, self.allowUserWrite(self.bobUser), False)
    y.update(self.bobUser, self.bobUser, 2 if x.v == 42 else 3)
    self.assertEqual(JeevesLib.concretize(self.aliceUser, y.v), 2)
    self.assertEqual(JeevesLib.concretize(self.bobUser, y.v), 2)

  '''
  def test_with_objects(self):
    x = ProtectedRef(None
      , lambda _bomb: lambda ic: True
      , lambda _bomb: lambda ic: lambda _oc:
          self.hasTurn(ic) and self.allShipsPlaced(ic) and
            (not self.gameOver(ic))
  '''

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = testSourceTransform
import unittest
import macropy.activate
from sourcetrans.macro_module import macros, jeeves
import JeevesLib
import operator

@jeeves
class TestClass:
  def __init__(self, a, b):
    self.a = a
    self.b = b

@jeeves
class TestClassMethod:
  def __init__(self, a, b):
    self.a = a
    self.b = b

  def add_a_to_b(self):
    self.b += self.a

  def return_sum(self):
    return self.a + self.b

@jeeves
class TestClass1:
  def __init__(self, a):
    self.a = a

@jeeves
class TestClass1Eq:
  def __init__(self, a):
    self.a = a
  def __eq__(self, other):
    return self.a == other.a
  def __ne__(self, other):
    return self.a != other.a
  def __lt__(self, other):
    return self.a < other.a
  def __gt__(self, other):
    return self.a > other.a
  def __le__(self, other):
    return self.a <= other.a
  def __ge__(self, other):
    return self.a >= other.a

class TestSourceTransform(unittest.TestCase):
  def setUp(self):
    # reset the Jeeves state
    JeevesLib.init()

  @jeeves
  def test_restrict_all_permissive(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda _: True)
    xConcrete = JeevesLib.concretize(None, x)
    self.assertTrue(xConcrete)

  @jeeves
  def test_restrict_all_restrictive(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda _: False)
    xConcrete = JeevesLib.concretize(None, x)
    self.assertFalse(xConcrete)

  @jeeves
  def test_restrict_with_context(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda y: y == 2)

    xConcrete = JeevesLib.concretize(2, x)
    self.assertTrue(xConcrete)

    xConcrete = JeevesLib.concretize(3, x)
    self.assertFalse(xConcrete)

  @jeeves
  def test_restrict_with_sensitive_value(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda y: y == 2)
    value = JeevesLib.mkSensitive(x, 42, 41)

    valueConcrete = JeevesLib.concretize(2, value)
    self.assertEquals(valueConcrete, 42)

    valueConcrete = JeevesLib.concretize(1, value)
    self.assertEquals(valueConcrete, 41)

  @jeeves
  def test_restrict_with_cyclic(self):
    jl = JeevesLib

    # use the value itself as the context
    x = jl.mkLabel('x')
    jl.restrict(x, lambda ctxt : ctxt == 42)

    value = jl.mkSensitive(x, 42, 20)
    self.assertEquals(jl.concretize(value, value), 42)

    value = jl.mkSensitive(x, 41, 20)
    self.assertEquals(jl.concretize(value, value), 20)

  @jeeves
  def test_jif_with_ints(self):
    jl = JeevesLib

    x = jl.mkLabel('x')
    jl.restrict(x, lambda ctxt : ctxt == 42)

    a = 13 if x else 17
    self.assertEquals(jl.concretize(42, a), 13)
    self.assertEquals(jl.concretize(-2, a), 17)

    b = 13 if True else 17
    self.assertEquals(jl.concretize(42, b), 13)
    self.assertEquals(jl.concretize(-2, b), 13)

    c = 13 if False else 17
    self.assertEquals(jl.concretize(42, c), 17)
    self.assertEquals(jl.concretize(-2, c), 17)

    conditional = jl.mkSensitive(x, True, False)
    d = 13 if conditional else 17
    self.assertEquals(jl.concretize(42, d), 13)
    self.assertEquals(jl.concretize(-2, d), 17)

    conditional = jl.mkSensitive(x, False, True)
    d = 13 if conditional else 17
    self.assertEquals(jl.concretize(42, d), 17)
    self.assertEquals(jl.concretize(-2, d), 13)

    y = jl.mkLabel('y')
    z = jl.mkLabel('z')
    jl.restrict(y, lambda (a,_) : a)
    jl.restrict(z, lambda (_,a) : a)
    faceted_int = jl.mkSensitive(y, 10, 0)
    conditional = faceted_int > 5
    i1 = jl.mkSensitive(z, 101, 102)
    i2 = jl.mkSensitive(z, 103, 104)
    f = i1 if conditional else i2
    self.assertEquals(jl.concretize((True, True), f),101)
    self.assertEquals(jl.concretize((True, False), f), 102)
    self.assertEquals(jl.concretize((False, True), f), 103)
    self.assertEquals(jl.concretize((False, False), f), 104)

  @jeeves
  def test_restrict_under_conditional(self):
    x = JeevesLib.mkLabel('x')

    value = JeevesLib.mkSensitive(x, 42, 0)
    if value == 42:
      JeevesLib.restrict(x, lambda ctxt : ctxt == 1)
    self.assertEquals(JeevesLib.concretize(0, value), 0)
    self.assertEquals(JeevesLib.concretize(1, value), 42)

    y = JeevesLib.mkLabel('y')

    value = JeevesLib.mkSensitive(y, 43, 0)
    if value == 42:
        JeevesLib.restrict(y, lambda ctxt : ctxt == 1)
    self.assertEquals(JeevesLib.concretize(0, value), 43)
    self.assertEquals(JeevesLib.concretize(1, value), 43)

  @jeeves
  def test_jbool_functions_fexprs(self):
    jl = JeevesLib

    x = jl.mkLabel('x')
    jl.restrict(x, lambda (a,_) : a == 42)

    for lh in (True, False):
      for ll in (True, False):
        for rh in (True, False):
          for rl in (True, False):
            l = jl.mkSensitive(x, lh, ll)
            r = jl.mkSensitive(x, rh, rl)
            self.assertEquals(jl.concretize((42,0), l and r), operator.and_(lh, rh))
            self.assertEquals(jl.concretize((10,0), l and r), operator.and_(ll, rl))
            self.assertEquals(jl.concretize((42,0), l or r), operator.or_(lh, rh))
            self.assertEquals(jl.concretize((10,0), l or r), operator.or_(ll, rl))
            self.assertEquals(jl.concretize((42,0), not l), operator.not_(lh))
            self.assertEquals(jl.concretize((10,0), not l), operator.not_(ll))

    y = jl.mkLabel('y')
    jl.restrict(y, lambda (_,b) : b == 42)

    for lh in (True, False):
      for ll in (True, False):
        for rh in (True, False):
          for rl in (True, False):
            l = jl.mkSensitive(x, lh, ll)
            r = jl.mkSensitive(y, rh, rl)
            self.assertEquals(jl.concretize((42,0), l and r), operator.and_(lh, rl))
            self.assertEquals(jl.concretize((10,0), l and r), operator.and_(ll, rl))
            self.assertEquals(jl.concretize((42,42), l and r), operator.and_(lh, rh))
            self.assertEquals(jl.concretize((10,42), l and r), operator.and_(ll, rh))

            self.assertEquals(jl.concretize((42,0), l or r), operator.or_(lh, rl))
            self.assertEquals(jl.concretize((10,0), l or r), operator.or_(ll, rl))
            self.assertEquals(jl.concretize((42,42), l or r), operator.or_(lh, rh))
            self.assertEquals(jl.concretize((10,42), l or r), operator.or_(ll, rh))
  
  @jeeves
  def test_jif_with_assign(self):
    jl = JeevesLib

    y = jl.mkLabel('y')
    jl.restrict(y, lambda ctxt : ctxt == 42)

    value0 = jl.mkSensitive(y, 0, 1)
    value2 = jl.mkSensitive(y, 2, 3)

    value = value0
    value = value2
    self.assertEquals(jl.concretize(42, value), 2)
    self.assertEquals(jl.concretize(10, value), 3)

    value = 100
    value = value2
    self.assertEquals(jl.concretize(42, value), 2)
    self.assertEquals(jl.concretize(10, value), 3)

    value = value0
    value = 200
    self.assertEquals(jl.concretize(42, value), 200)
    self.assertEquals(jl.concretize(10, value), 200)

    value = 100
    value = 200
    self.assertEquals(jl.concretize(42, value), 200)
    self.assertEquals(jl.concretize(10, value), 200)

  @jeeves
  def test_jif_with_assign_with_pathvars(self):
    jl = JeevesLib

    x = jl.mkLabel('x')
    y = jl.mkLabel('y')
    jl.restrict(x, lambda (a,_) : a)
    jl.restrict(y, lambda (_,b) : b)

    value0 = jl.mkSensitive(y, 0, 1)
    value2 = jl.mkSensitive(y, 2, 3)

    value = value0
    if x:
      value = value2
    self.assertEquals(jl.concretize((True, True), value), 2)
    self.assertEquals(jl.concretize((True, False), value), 3)
    self.assertEquals(jl.concretize((False, True), value), 0)
    self.assertEquals(jl.concretize((False, False), value), 1)

    value = value0
    if not x:
      value = value2
    self.assertEquals(jl.concretize((False, True), value), 2)
    self.assertEquals(jl.concretize((False, False), value), 3)
    self.assertEquals(jl.concretize((True, True), value), 0)
    self.assertEquals(jl.concretize((True, False), value), 1)

  @jeeves
  def test_function_facets(self):
    def add1(a):
        return a+1
    def add2(a):
        return a+2

    jl = JeevesLib

    x = jl.mkLabel('x')
    jl.restrict(x, lambda ctxt : ctxt == 42)

    fun = jl.mkSensitive(x, add1, add2)
    value = fun(15)
    self.assertEquals(jl.concretize(42, value), 16)
    self.assertEquals(jl.concretize(41, value), 17)

  @jeeves
  def test_objects_faceted(self):
    jl = JeevesLib

    x = jl.mkLabel('x')
    jl.restrict(x, lambda ctxt : ctxt)

    y = jl.mkSensitive(x,
      TestClass(1, 2),
      TestClass(3, 4))

    self.assertEquals(jl.concretize(True, y.a), 1)
    self.assertEquals(jl.concretize(True, y.b), 2)
    self.assertEquals(jl.concretize(False, y.a), 3)
    self.assertEquals(jl.concretize(False, y.b), 4)

  @jeeves
  def test_objects_mutate(self):
    jl = JeevesLib

    x = jl.mkLabel('x')
    jl.restrict(x, lambda ctxt : ctxt)

    s = TestClass(1, None)
    t = TestClass(3, None)
    y = jl.mkSensitive(x, s, t)

    if y.a == 1:
      y.a = y.a + 100

    self.assertEquals(jl.concretize(True, y.a), 101)
    self.assertEquals(jl.concretize(True, s.a), 101)
    self.assertEquals(jl.concretize(True, t.a), 3)
    self.assertEquals(jl.concretize(False, y.a), 3)
    self.assertEquals(jl.concretize(False, s.a), 1)
    self.assertEquals(jl.concretize(False, t.a), 3)

  def test_objects_methodcall(self):
    jl = JeevesLib

    x = jl.mkLabel('x')
    jl.restrict(x, lambda ctxt : ctxt)

    s = TestClassMethod(1, 10)
    t = TestClassMethod(100, 1000)
    y = jl.mkSensitive(x, s, t)

    self.assertEquals(jl.concretize(True, y.return_sum()), 11)
    self.assertEquals(jl.concretize(False, y.return_sum()), 1100)

    y.add_a_to_b()
    self.assertEquals(jl.concretize(True, s.a), 1)
    self.assertEquals(jl.concretize(True, s.b), 11)
    self.assertEquals(jl.concretize(True, t.a), 100)
    self.assertEquals(jl.concretize(True, t.b), 1000)
    self.assertEquals(jl.concretize(True, y.a), 1)
    self.assertEquals(jl.concretize(True, y.b), 11)
    self.assertEquals(jl.concretize(False, s.a), 1)
    self.assertEquals(jl.concretize(False, s.b), 10)
    self.assertEquals(jl.concretize(False, t.a), 100)
    self.assertEquals(jl.concretize(False, t.b), 1100)
    self.assertEquals(jl.concretize(False, y.a), 100)
    self.assertEquals(jl.concretize(False, y.b), 1100)

  @jeeves
  def test_objects_eq_is(self):
    jl = JeevesLib
    x = jl.mkLabel('x')
    jl.restrict(x, lambda ctxt : ctxt)

    a = TestClass1(3)
    b = TestClass1(3)
    c = TestClass1(2)

    # Ensure that a < b and b < c (will probably be true anyway,
    # just making sure)
    s = sorted((a, b, c))
    a = s[0]
    b = s[1]
    c = s[2]
    a.a = 3
    b.a = 3
    c.a = 2

    v1 = jl.mkSensitive(x, a, c)
    v2 = jl.mkSensitive(x, b, c)
    v3 = jl.mkSensitive(x, c, a)
    self.assertEquals(jl.concretize(True, v1 == v1), True)
    self.assertEquals(jl.concretize(True, v2 == v2), True)
    self.assertEquals(jl.concretize(True, v3 == v3), True)
    self.assertEquals(jl.concretize(True, v1 == v2), False)
    self.assertEquals(jl.concretize(True, v2 == v3), False)
    self.assertEquals(jl.concretize(True, v3 == v1), False)

    self.assertEquals(jl.concretize(True, v1 != v1), False)
    self.assertEquals(jl.concretize(True, v2 != v2), False)
    self.assertEquals(jl.concretize(True, v3 != v3), False)
    self.assertEquals(jl.concretize(True, v1 != v2), True)
    self.assertEquals(jl.concretize(True, v2 != v3), True)
    self.assertEquals(jl.concretize(True, v3 != v1), True)

    self.assertEquals(jl.concretize(True, v1 < v1), False)
    self.assertEquals(jl.concretize(True, v2 < v2), False)
    self.assertEquals(jl.concretize(True, v3 < v3), False)
    self.assertEquals(jl.concretize(True, v1 < v2), True)
    self.assertEquals(jl.concretize(True, v2 < v3), True)
    self.assertEquals(jl.concretize(True, v3 < v1), False)

    self.assertEquals(jl.concretize(True, v1 > v1), False)
    self.assertEquals(jl.concretize(True, v2 > v2), False)
    self.assertEquals(jl.concretize(True, v3 > v3), False)
    self.assertEquals(jl.concretize(True, v1 > v2), False)
    self.assertEquals(jl.concretize(True, v2 > v3), False)
    self.assertEquals(jl.concretize(True, v3 > v1), True)

    self.assertEquals(jl.concretize(True, v1 <= v1), True)
    self.assertEquals(jl.concretize(True, v2 <= v2), True)
    self.assertEquals(jl.concretize(True, v3 <= v3), True)
    self.assertEquals(jl.concretize(True, v1 <= v2), True)
    self.assertEquals(jl.concretize(True, v2 <= v3), True)
    self.assertEquals(jl.concretize(True, v3 <= v1), False)

    self.assertEquals(jl.concretize(True, v1 >= v1), True)
    self.assertEquals(jl.concretize(True, v2 >= v2), True)
    self.assertEquals(jl.concretize(True, v3 >= v3), True)
    self.assertEquals(jl.concretize(True, v1 >= v2), False)
    self.assertEquals(jl.concretize(True, v2 >= v3), False)
    self.assertEquals(jl.concretize(True, v3 >= v1), True)

    self.assertEquals(jl.concretize(False, v2 == v3), False)
    self.assertEquals(jl.concretize(False, v2 != v3), True)
    self.assertEquals(jl.concretize(False, v2 < v3), False)
    self.assertEquals(jl.concretize(False, v2 > v3), True)
    self.assertEquals(jl.concretize(False, v2 <= v3), False)
    self.assertEquals(jl.concretize(False, v2 >= v3), True)

    a = TestClass1Eq(3)
    b = TestClass1Eq(3)
    c = TestClass1Eq(2)

    v1 = jl.mkSensitive(x, a, c)
    v2 = jl.mkSensitive(x, b, c)
    v3 = jl.mkSensitive(x, c, a)
    self.assertEquals(jl.concretize(True, v1 == v1), True)
    self.assertEquals(jl.concretize(True, v2 == v2), True)
    self.assertEquals(jl.concretize(True, v3 == v3), True)
    self.assertEquals(jl.concretize(True, v1 == v2), True)
    self.assertEquals(jl.concretize(True, v2 == v3), False)
    self.assertEquals(jl.concretize(True, v3 == v1), False)

    self.assertEquals(jl.concretize(True, v1 != v1), False)
    self.assertEquals(jl.concretize(True, v2 != v2), False)
    self.assertEquals(jl.concretize(True, v3 != v3), False)
    self.assertEquals(jl.concretize(True, v1 != v2), False)
    self.assertEquals(jl.concretize(True, v2 != v3), True)
    self.assertEquals(jl.concretize(True, v3 != v1), True)

    self.assertEquals(jl.concretize(True, v1 < v1), False)
    self.assertEquals(jl.concretize(True, v2 < v2), False)
    self.assertEquals(jl.concretize(True, v3 < v3), False)
    self.assertEquals(jl.concretize(True, v1 < v2), False)
    self.assertEquals(jl.concretize(True, v2 < v3), False)
    self.assertEquals(jl.concretize(True, v3 < v1), True)

    self.assertEquals(jl.concretize(True, v1 > v1), False)
    self.assertEquals(jl.concretize(True, v2 > v2), False)
    self.assertEquals(jl.concretize(True, v3 > v3), False)
    self.assertEquals(jl.concretize(True, v1 > v2), False)
    self.assertEquals(jl.concretize(True, v2 > v3), True)
    self.assertEquals(jl.concretize(True, v3 > v1), False)

    self.assertEquals(jl.concretize(True, v1 <= v1), True)
    self.assertEquals(jl.concretize(True, v2 <= v2), True)
    self.assertEquals(jl.concretize(True, v3 <= v3), True)
    self.assertEquals(jl.concretize(True, v1 <= v2), True)
    self.assertEquals(jl.concretize(True, v2 <= v3), False)
    self.assertEquals(jl.concretize(True, v3 <= v1), True)

    self.assertEquals(jl.concretize(True, v1 >= v1), True)
    self.assertEquals(jl.concretize(True, v2 >= v2), True)
    self.assertEquals(jl.concretize(True, v3 >= v3), True)
    self.assertEquals(jl.concretize(True, v1 >= v2), True)
    self.assertEquals(jl.concretize(True, v2 >= v3), True)
    self.assertEquals(jl.concretize(True, v3 >= v1), False)

    self.assertEquals(jl.concretize(False, v2 == v3), False)
    self.assertEquals(jl.concretize(False, v2 != v3), True)
    self.assertEquals(jl.concretize(False, v2 < v3), True)
    self.assertEquals(jl.concretize(False, v2 > v3), False)
    self.assertEquals(jl.concretize(False, v2 <= v3), True)
    self.assertEquals(jl.concretize(False, v2 >= v3), False)

  @jeeves
  def test_jhasElt(self):
    jl = JeevesLib

    a = jl.mkLabel ()
    jl.restrict(a, lambda x: x)
    xS = jl.mkSensitive(a, 42, 1)

    b = jl.mkLabel ()
    jl.restrict(b, lambda x: x)
    yS = jl.mkSensitive(b, 43, 3)

    lst = [xS, 2, yS]
    self.assertEquals(jl.concretize(True, 42 in lst) , True)
    self.assertEquals(jl.concretize(False, 42 in lst) , False)
    self.assertEquals(jl.concretize(True, 1 in lst) , False)
    self.assertEquals(jl.concretize(False, 1 in lst) , True)
    self.assertEquals(jl.concretize(True, 43 in lst) , True)
    self.assertEquals(jl.concretize(False, 43 in lst) , False)
    self.assertEquals(jl.concretize(True, 3 in lst) , False)
    self.assertEquals(jl.concretize(False, 3 in lst) , True)

  @jeeves
  def test_list(self):
    jl = JeevesLib
    x = jl.mkLabel('x')
    jl.restrict(x, lambda ctxt : ctxt)

    l = jl.mkSensitive(x, [40,41,42], [0,1,2,3])

    self.assertEqual(jl.concretize(True, l[0]), 40)
    self.assertEqual(jl.concretize(True, l[1]), 41)
    self.assertEqual(jl.concretize(True, l[2]), 42)
    self.assertEqual(jl.concretize(False, l[0]), 0)
    self.assertEqual(jl.concretize(False, l[1]), 1)
    self.assertEqual(jl.concretize(False, l[2]), 2)
    self.assertEqual(jl.concretize(False, l[3]), 3)

    self.assertEqual(jl.concretize(True, l.__len__()), 3)
    self.assertEqual(jl.concretize(False, l.__len__()), 4)

    l[1] = 19

    self.assertEqual(jl.concretize(True, l[0]), 40)
    self.assertEqual(jl.concretize(True, l[1]), 19)
    self.assertEqual(jl.concretize(True, l[2]), 42)
    self.assertEqual(jl.concretize(False, l[0]), 0)
    self.assertEqual(jl.concretize(False, l[1]), 19)
    self.assertEqual(jl.concretize(False, l[2]), 2)
    self.assertEqual(jl.concretize(False, l[3]), 3)

  @jeeves
  def test_jmap(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda ctxt : ctxt)

    l = JeevesLib.mkSensitive(x, [0,1,2], [3,4,5,6])
    m = [x*x for x in l]

    self.assertEqual(JeevesLib.concretize(True, m[0]), 0)
    self.assertEqual(JeevesLib.concretize(True, m[1]), 1)
    self.assertEqual(JeevesLib.concretize(True, m[2]), 4)
    self.assertEqual(JeevesLib.concretize(False, m[0]), 9)
    self.assertEqual(JeevesLib.concretize(False, m[1]), 16)
    self.assertEqual(JeevesLib.concretize(False, m[2]), 25)
    self.assertEqual(JeevesLib.concretize(False, m[3]), 36)

  @jeeves
  def test_jmap_for(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda ctxt : ctxt)

    l = JeevesLib.mkSensitive(x, [0,1,2], [3,4,5,6])
    m = 0
    for t in l:
      m = m + t*t

    self.assertEqual(JeevesLib.concretize(True, m), 5)
    self.assertEqual(JeevesLib.concretize(False, m), 86)

  @jeeves
  def test_jlist(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda ctxt : ctxt)

    l = JeevesLib.mkSensitive(x, [0,1,2], [3,4,5,6])
    if x:
      l.append(10)
    else:
      l.append(11)

    self.assertEqual(JeevesLib.concretize(True, l[0]), 0)
    self.assertEqual(JeevesLib.concretize(True, l[1]), 1)
    self.assertEqual(JeevesLib.concretize(True, l[2]), 2)
    self.assertEqual(JeevesLib.concretize(True, l[3]), 10)
    self.assertEqual(JeevesLib.concretize(False, l[0]), 3)
    self.assertEqual(JeevesLib.concretize(False, l[1]), 4)
    self.assertEqual(JeevesLib.concretize(False, l[2]), 5)
    self.assertEqual(JeevesLib.concretize(False, l[3]), 6)
    self.assertEqual(JeevesLib.concretize(False, l[4]), 11)

    if x:
        l[0] = 20
    self.assertEqual(JeevesLib.concretize(True, l[0]), 20)
    self.assertEqual(JeevesLib.concretize(False, l[0]), 3)

  @jeeves
  def test_or_in_lambda(self):
    x = JeevesLib.mkLabel()
    JeevesLib.restrict(x, lambda oc: oc == 1 or oc == 2)
    self.assertTrue(JeevesLib.concretize(1, x))
    self.assertTrue(JeevesLib.concretize(2, x))
    self.assertFalse(JeevesLib.concretize(3, x))

  @jeeves
  def test_return(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda ctxt : ctxt)

    y = [5]

    def awesome_function():
      y[0] = 7
      if x:
        return 30
      y[0] = 19
      return 17

    z = awesome_function()

    self.assertEqual(JeevesLib.concretize(True, y[0]), 7)
    self.assertEqual(JeevesLib.concretize(False, y[0]), 19)
    self.assertEqual(JeevesLib.concretize(True, z), 30)
    self.assertEqual(JeevesLib.concretize(False, z), 17)

  @jeeves
  def test_scope(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda ctxt : ctxt)

    y = 5

    def awesome_function():
      y = 7
      if x:
        return 30
      y = 19
      return 17

    z = awesome_function()

    self.assertEqual(JeevesLib.concretize(True, y), 5)
    self.assertEqual(JeevesLib.concretize(False, y), 5)
    self.assertEqual(JeevesLib.concretize(True, z), 30)
    self.assertEqual(JeevesLib.concretize(False, z), 17)

  @jeeves
  def test_return_in_for(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda ctxt : ctxt)

    y = JeevesLib.mkSensitive(x, [5,60,7], [11,2,4,81,3,12])

    def bulbasaur():
      for j in y:
        if j >= 40:
          return j

    z = bulbasaur()

    self.assertEqual(JeevesLib.concretize(True, z), 60)
    self.assertEqual(JeevesLib.concretize(False, z), 81)

  @jeeves
  def test_jfun(self):
    x = JeevesLib.mkLabel('x')
    JeevesLib.restrict(x, lambda ctxt : ctxt)
    
    y = JeevesLib.mkSensitive(x, [1,2,3], [4,5,6,7])

    z = map(lambda x : x*x, y)

    self.assertEqual(JeevesLib.concretize(True, z[0]), 1)
    self.assertEqual(JeevesLib.concretize(True, z[1]), 4)
    self.assertEqual(JeevesLib.concretize(True, z[2]), 9)
    self.assertEqual(JeevesLib.concretize(False, z[0]), 16)
    self.assertEqual(JeevesLib.concretize(False, z[1]), 25)
    self.assertEqual(JeevesLib.concretize(False, z[2]), 36)
    self.assertEqual(JeevesLib.concretize(False, z[3]), 49)

########NEW FILE########
__FILENAME__ = testZ3
import macropy.activate
from smt.Z3 import *
from fast import AST
import unittest

class TestZ3(unittest.TestCase):
  def setUp(self):
    self.s = Z3()

  def test_sat_ints(self):
    x = self.s.getIntVar('x')
    self.s.solverAssert(x > 0)
    self.s.solverAssert(x < 2)
    self.assertTrue(self.s.isSatisfiable())

  def test_unsat_ints(self):
    x = self.s.getIntVar('x')
    self.s.solverAssert(x > 2)
    self.s.solverAssert(x < 2)
    self.assertFalse(self.s.isSatisfiable())

  def test_multiple_vars(self):
    x0 = self.s.getIntVar('x')
    x1 = self.s.getIntVar('x')
    self.s.solverAssert(x0 > 2)
    self.s.solverAssert(x1 < 2)
    self.assertFalse(self.s.isSatisfiable())

  def test_multiple_vars2(self):
    x0 = self.s.getIntVar('x')
    x1 = self.s.getIntVar('y')
    self.s.solverAssert(x0 > 2)
    self.s.solverAssert(x1 < 2)
    self.assertTrue(self.s.isSatisfiable())

  def test_ast(self):
    b1 = AST.Var('x')
    b2 = AST.Var('y')

    t = AST.Facet(b1, 1, 10) + AST.Facet(b2, 100, 1000)

    self.assertTrue(self.s.isSatisfiable())

    self.s.push()
    self.s.boolExprAssert(t == 101)
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(t == 1001)
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(t == 110)
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(t == 1010)
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(t == 11)
    self.assertFalse(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(t == 1001)
    self.s.boolExprAssert(t == 1010)
    self.assertFalse(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(t == 1001)
    self.s.boolExprAssert(AST.Not(b1))
    self.assertFalse(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(t - 1 == 1009)
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(t - 1 == 1008)
    self.assertFalse(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(t * 2 == 2002)
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(t * 2 == 2004)
    self.assertFalse(self.s.isSatisfiable())
    self.s.pop()

  def test_ast_bools(self):
    b1 = AST.Var()
    b2 = AST.Var()
    b3 = AST.Var()
    b4 = AST.Var()

    self.s.push()
    self.s.boolExprAssert(AST.And(b1, b2))
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.And(b1, b2))
    self.s.boolExprAssert(AST.Not(b1))
    self.assertFalse(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Or(b1, b2))
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Or(b1, b2))
    self.s.boolExprAssert(AST.Not(b1))
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Or(b1, b2))
    self.s.boolExprAssert(AST.Not(b1))
    self.s.boolExprAssert(AST.Not(b2))
    self.assertFalse(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Or(b1, b2))
    self.s.boolExprAssert(AST.And(AST.Not(b1),AST.Not(b2)))
    self.assertFalse(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.And(AST.Or(b1, b2),AST.And(AST.Not(b1),AST.Not(b2))))
    self.assertFalse(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Implies(b1, b2))
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Implies(b1, b2))
    self.s.boolExprAssert(b1)
    self.s.boolExprAssert(b2)
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Implies(b1, b2))
    self.s.boolExprAssert(b1)
    self.s.boolExprAssert(AST.Not(b2))
    self.assertFalse(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Implies(b1, b2))
    self.s.boolExprAssert(AST.Not(b1))
    self.s.boolExprAssert(b2)
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Implies(b1, b2))
    self.s.boolExprAssert(AST.Not(b1))
    self.s.boolExprAssert(AST.Not(b2))
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

  def test_ast_comparisons(self):
    b1 = AST.Var()
    b2 = AST.Var()

    self.s.push()
    self.s.boolExprAssert(AST.Facet(b1, 0, 1) != AST.Facet(b1, 1, 2) - 1)
    self.assertFalse(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Facet(b1, 0, 1) < AST.Facet(b2, 3, 4))
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Facet(b1, 0, 1) <= AST.Facet(b2, 3, 4))
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Facet(b1, 0, 1) < AST.Facet(b2, -1, 0))
    self.assertFalse(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Facet(b1, 0, 1) <= AST.Facet(b2, -1,0))
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Facet(b1, 3, 4) > AST.Facet(b2, 0, 1))
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Facet(b1, 3, 4) >= AST.Facet(b2, 0, 1))
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Facet(b1, -1, 0) > AST.Facet(b2, 0, 1))
    self.assertFalse(self.s.isSatisfiable())
    self.s.pop()

    self.s.push()
    self.s.boolExprAssert(AST.Facet(b1, -1, 0) >= AST.Facet(b2, 0, 1))
    self.assertTrue(self.s.isSatisfiable())
    self.s.pop()

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = Singleton
class Singleton(object):
  _instance = None
  def __new__(cls, *args, **kwargs):
    if not cls._instance:
      cls._instance = super(Singleton, cls).__new__(cls, *args, **kwargs)
    return cls._instance

########NEW FILE########
