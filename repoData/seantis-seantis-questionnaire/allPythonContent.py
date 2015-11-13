__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import os, os.path, sys
sys.path.insert(0, os.path.abspath("../"))

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
# Django settings for example project.
import os.path

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'example.sqlite',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Berlin'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'j69g6-&t0l43f06iq=+u!ni)9n)g!ygy4dk-dgdbrbdx7%9l*6'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.abspath('./static_root')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.abspath('./static'),
    os.path.abspath('../questionnaire/static/')    
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)


# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'questionnaire.request_cache.RequestCacheMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'example.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.abspath("../questionnaire/templates/"),
    os.path.abspath("./templates/"),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.markup',
    'django.contrib.staticfiles',
    'transmeta',
    'questionnaire',
    'questionnaire.page',
)

LANGUAGES = (
    ('en', 'English'),
    ('de', 'Deutsch'),
)

# Defines the progressbar behavior in the questionnaire
# the possible options are 'default', 'async' and 'none'
#
#   'default'
#   The progressbar will be rendered in each questionset together with the 
#   questions. This is a good choice for smaller questionnaires as the 
#   progressbar will always be up to date.
#
#   'async'
#   The progressbar value is updated using ajax once the questions have been
#   rendered. This approach is the right choice for bigger questionnaires which
#   result in a long time spent on updating the progressbar with each request.
#   (The progress calculation is by far the most time consuming method in 
#    bigger questionnaires as all questionsets and questions need to be
#    parsed to decide if they play a role in the current run or not)
#
#   'none'
#   Completely omits the progressbar. Good if you don't want one or if the
#   questionnaire is so huge that even the ajax request takes too long.
QUESTIONNAIRE_PROGRESS = 'async'

try: from local_settings import *
except: pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    
    url(r'q/', include('questionnaire.urls')),
    
    url(r'^take/(?P<questionnaire_id>[0-9]+)/$', 'questionnaire.views.generate_run'),
    url(r'^$', 'questionnaire.page.views.page', {'page' : 'index'}),
    url(r'^(?P<page>.*)\.html$', 'questionnaire.page.views.page'),
    url(r'^(?P<lang>..)/(?P<page>.*)\.html$', 'questionnaire.page.views.langpage'),
    url(r'^setlang/$', 'questionnaire.views.set_language'),

    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = admin
#!/usr/bin/python
# vim: set fileencoding=utf-8

from django.contrib import admin
from models import *

adminsite = admin.site

class SubjectAdmin(admin.ModelAdmin):
    search_fields = ['surname', 'givenname', 'email']
    list_display = ['surname', 'givenname', 'email']

class ChoiceAdmin(admin.ModelAdmin):
    list_display = ['sortid', 'text', 'value', 'question']

class ChoiceInline(admin.TabularInline):
    ordering = ['sortid']
    model = Choice
    extra = 5

class QuestionSetAdmin(admin.ModelAdmin):
    ordering = ['questionnaire', 'sortid', ]
    list_filter = ['questionnaire', ]
    list_display = ['questionnaire', 'heading', 'sortid', ]
    list_editable = ['sortid', ]

class QuestionAdmin(admin.ModelAdmin):
    ordering = ['questionset__questionnaire', 'questionset', 'number']
    inlines = [ChoiceInline]

    def changelist_view(self, request, extra_context=None):
        "Hack to have Questionnaire list accessible for custom changelist template"
        if not extra_context:
            extra_context = {}
        extra_context['questionnaires'] = Questionnaire.objects.all().order_by('name')
        return super(QuestionAdmin, self).changelist_view(request, extra_context)

class QuestionnaireAdmin(admin.ModelAdmin):
    pass

class RunInfoAdmin(admin.ModelAdmin):
    list_display = ['random', 'runid', 'subject', 'created', 'emailsent', 'lastemailerror']
    pass

class RunInfoHistoryAdmin(admin.ModelAdmin):
    pass

class AnswerAdmin(admin.ModelAdmin):
    search_fields = ['subject', 'runid', 'question', 'answer']
    list_display = ['runid', 'subject', 'question']
    list_filter = ['subject', 'runid']
    ordering = [ 'subject', 'runid', 'question', ]

adminsite.register(Questionnaire, QuestionnaireAdmin)
adminsite.register(Question, QuestionAdmin)
adminsite.register(QuestionSet, QuestionSetAdmin)
adminsite.register(Subject, SubjectAdmin)
adminsite.register(RunInfo, RunInfoAdmin) 
adminsite.register(RunInfoHistory, RunInfoHistoryAdmin) 
adminsite.register(Answer, AnswerAdmin)
########NEW FILE########
__FILENAME__ = emails
# -*- coding: utf-8
"""
Functions to send email reminders to users.
"""

from django.core.mail import get_connection, EmailMessage
from django.contrib.auth.decorators import login_required
from django.template import Context, loader
from django.utils import translation
from django.conf import settings
from models import Subject, QuestionSet, RunInfo, Questionnaire
from datetime import datetime
from django.shortcuts import render_to_response, get_object_or_404
import random, time, smtplib, rfc822
from email.Header import Header
from email.Utils import formataddr, parseaddr
try: from hashlib import md5
except: from md5 import md5


def encode_emailaddress(address):
    """
    Encode an email address as ASCII using the Encoded-Word standard.
    Needed to work around http://code.djangoproject.com/ticket/11144
    """
    try: return address.encode('ascii')
    except UnicodeEncodeError: pass
    nm, addr = parseaddr(address)
    return formataddr( (str(Header(nm, settings.DEFAULT_CHARSET)), addr) )


def _new_random(subject):
    """
    Create a short unique randomized string.
    Returns: subject_id + 'z' +
        md5 hexdigest of subject's surname, nextrun date, and a random number
    """
    return "%dz%s" % (subject.id, md5(subject.surname + str(subject.nextrun) + hex(random.randint(1,999999))).hexdigest()[:6])


def _new_runinfo(subject, questionset):
    """
    Create a new RunInfo entry with a random code

    If a unique subject+runid entry already exists, return that instead..
    That should only occurs with manual database changes
    """
    nextrun = subject.nextrun
    runid = str(nextrun.year)
    entries = list(RunInfo.objects.filter(runid=runid, subject=subject))
    if len(entries)>0:
        r = entries[0]
    else:
        r = RunInfo()
        r.random = _new_random(subject)
        r.subject = subject
        r.runid = runid
        r.emailcount = 0
        r.created = datetime.now()
    r.questionset = questionset
    r.save()
    if nextrun.month == 2 and nextrun.day == 29: # the only exception?
        subject.nextrun = datetime(nextrun.year + 1, 2, 28)
    else:
        subject.nextrun = datetime(nextrun.year + 1, nextrun.month, nextrun.day)
    subject.save()
    return r

def _send_email(runinfo):
    "Send the email for a specific runinfo entry"
    subject = runinfo.subject
    translation.activate(subject.language)
    tmpl = loader.get_template(settings.QUESTIONNAIRE_EMAIL_TEMPLATE)
    c = Context()
    c['surname'] = subject.surname
    c['givenname'] = subject.givenname
    c['gender'] = subject.gender
    c['email'] = subject.email
    c['random'] = runinfo.random
    c['runid'] = runinfo.runid
    c['created'] = runinfo.created
    c['site'] = getattr(settings, 'QUESTIONNAIRE_URL', '(settings.QUESTIONNAIRE_URL not set)')
    email = tmpl.render(c)
    emailFrom = settings.QUESTIONNAIRE_EMAIL_FROM
    emailSubject, email = email.split("\n",1) # subject must be on first line
    emailSubject = emailSubject.strip()
    emailFrom = emailFrom.replace("$RUNINFO", runinfo.random)
    emailTo = '"%s, %s" <%s>' % (subject.surname, subject.givenname, subject.email)

    emailTo = encode_emailaddress(emailTo)
    emailFrom = encode_emailaddress(emailFrom)

    try:
        conn = get_connection()
        msg = EmailMessage(emailSubject, email, emailFrom, [ emailTo ],
            connection=conn)
        msg.send()
        runinfo.emailcount = 1 + runinfo.emailcount
        runinfo.emailsent = datetime.now()
        runinfo.lastemailerror = "OK, accepted by server"
        runinfo.save()
        return True
    except smtplib.SMTPRecipientsRefused:
        runinfo.lastemailerror = "SMTP Recipient Refused"
    except smtplib.SMTPHeloError:
        runinfo.lastemailerror = "SMTP Helo Error"
    except smtplib.SMTPSenderRefused:
        runinfo.lastemailerror = "SMTP Sender Refused"
    except smtplib.SMTPDataError:
        runinfo.lastemailerror = "SMTP Data Error"
    runinfo.save()
    return False


def send_emails(request=None, qname=None):
    """
    1. Create a runinfo entry for each subject who is due and has state 'active'
    2. Send an email for each runinfo entry whose subject receives email,
       providing that the last sent email was sent more than a week ago.

    This can be called either by "./manage.py questionnaire_emails" (without
    request) or through the web, if settings.EMAILCODE is set and matches.
    """
    if request and request.GET.get('code') != getattr(settings,'EMAILCODE', False):
        raise Http404
    if not qname:
        qname = getattr(settings, 'QUESTIONNAIRE_DEFAULT', None)
    if not qname:
        raise Exception("QUESTIONNAIRE_DEFAULT not in settings")
    questionnaire = Questionnaire.objects.get(name=qname)
    questionset = QuestionSet.objects.filter(questionnaire__name=qname).order_by('sortid')
    if not questionset:
        raise Exception("No questionsets for questionnaire '%s' (in settings.py)" % qname)
        return
    questionset = questionset[0]

    viablesubjects = Subject.objects.filter(nextrun__lte = datetime.now(), state='active')
    for s in viablesubjects:
        r = _new_runinfo(s, questionset)
    runinfos = RunInfo.objects.filter(subject__formtype='email', questionset__questionnaire=questionnaire)
    WEEKAGO = time.time() - (60 * 60 * 24 * 7) # one week ago
    outlog = []
    for r in runinfos:
        if r.runid.startswith('test:'):
            continue
        if r.emailcount == -1:
            continue
        if r.emailcount == 0 or time.mktime(r.emailsent.timetuple()) < WEEKAGO:
            try:
                if _send_email(r):
                    outlog.append(u"[%s] %s, %s: OK" % (r.runid, r.subject.surname, r.subject.givenname))
                else:
                    outlog.append(u"[%s] %s, %s: %s" % (r.runid, r.subject.surname, r.subject.givenname, r.lastemailerror))
            except Exception, e:
                outlog.append("Exception: [%s] %s: %s" % (r.runid, r.subject.surname, str(e)))
    if request:
        return HttpResponse("Sent Questionnaire Emails:\n  "
            +"\n  ".join(outlog), mimetype="text/plain")
    return "\n".join(outlog)

########NEW FILE########
__FILENAME__ = langtemplateloader
"""
Wrapper for loading templates from the filesystem.
"""

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.utils._os import safe_join
from django.utils import translation

def get_template_sources(template_name, template_dirs=None):
    """
    Returns the absolute paths to "template_name", when appended to each
    directory in "template_dirs". Any paths that don't lie inside one of the
    template dirs are excluded from the result set, for security reasons.
    """
    if not template_dirs:
        template_dirs = settings.TEMPLATE_DIRS
    for template_dir in template_dirs:
        try:
            yield safe_join(template_dir, template_name)
        except UnicodeDecodeError:
            # The template dir name was a bytestring that wasn't valid UTF-8.
            raise
        except ValueError:
            # The joined path was located outside of this particular
            # template_dir (it might be inside another one, so this isn't
            # fatal).
            pass

def _load_template_source(template_name, template_dirs=None):
    tried = []
    for filepath in get_template_sources(template_name, template_dirs):
        try:
            return (open(filepath).read().decode(settings.FILE_CHARSET), filepath)
        except IOError:
            tried.append(filepath)
    if tried:
        error_msg = "Tried %s" % tried
    else:
        error_msg = "Your TEMPLATE_DIRS setting is empty. Change it to point to at least one template directory."
    raise TemplateDoesNotExist, error_msg

def load_template_source(template_name, template_dirs=None):
    """Assuming the current language is German.
       If template_name is index.$LANG.html, try index.de.html then index.html
       Also replaces .. with . when attempting fallback.
    """
    if "$LANG" in template_name:
        lang = translation.get_language()
        try:
            t = template_name.replace("$LANG", lang)
            res = _load_template_source(t, template_dirs)
            return res
        except TemplateDoesNotExist: 
            t = template_name.replace("$LANG", "").replace("..",".")
            return _load_template_source(t, template_dirs)
    return _load_template_source(template_name, template_dirs)
load_template_source.is_usable = True

########NEW FILE########
__FILENAME__ = questionnaire_emails
from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        from questionnaire.emails import send_emails
        res = send_emails()
        if res:
            print res

########NEW FILE########
__FILENAME__ = models
from django.db import models
from transmeta import TransMeta
from django.utils.translation import ugettext_lazy as _
from questionnaire import QuestionChoices
import re
from utils import split_numal
from django.utils import simplejson as json
from parsers import parse_checks, ParseException
from django.conf import settings

_numre = re.compile("(\d+)([a-z]+)", re.I)


class Subject(models.Model):
    STATE_CHOICES = [
        ("active", _("Active")),
        ("inactive", _("Inactive")),
        # Can be changed from elsewhere with
        # Subject.STATE_CHOICES[:] = [ ('blah', 'Blah') ]
    ]
    state = models.CharField(max_length=16, default="inactive",
        choices = STATE_CHOICES, verbose_name=_('State'))
    surname = models.CharField(max_length=64, blank=True, null=True,
        verbose_name=_('Surname'))
    givenname = models.CharField(max_length=64, blank=True, null=True,
        verbose_name=_('Given name'))
    email = models.EmailField(null=True, blank=True, verbose_name=_('Email'))
    gender = models.CharField(max_length=8, default="unset", blank=True,
        verbose_name=_('Gender'),
        choices = ( ("unset", _("Unset")),
                    ("male", _("Male")),
                    ("female", _("Female")),
        )
    )
    nextrun = models.DateField(verbose_name=_('Next Run'), blank=True, null=True)
    formtype = models.CharField(max_length=16, default='email',
        verbose_name = _('Form Type'),
        choices = (
            ("email", _("Subject receives emails")),
            ("paperform", _("Subject is sent paper form"),))
    )
    language = models.CharField(max_length=2, default=settings.LANGUAGE_CODE,
        verbose_name = _('Language'), choices = settings.LANGUAGES)

    def __unicode__(self):
        return u'%s, %s (%s)' % (self.surname, self.givenname, self.email)

    def next_runid(self):
        "Return the string form of the runid for the upcoming run"
        return str(self.nextrun.year)

    def last_run(self):
        "Returns the last completed run or None"
        try:
            query = RunInfoHistory.objects.filter(subject=self)
            return query.order_by('-completed')[0]
        except IndexError:
            return None

    def history(self):
        return RunInfoHistory.objects.filter(subject=self).order_by('runid')

    def pending(self):
        return RunInfo.objects.filter(subject=self).order_by('runid')


class Questionnaire(models.Model):
    name = models.CharField(max_length=128)
    redirect_url = models.CharField(max_length=128, help_text="URL to redirect to when Questionnaire is complete. Macros: $SUBJECTID, $RUNID, $LANG", default="/static/complete.html")

    def __unicode__(self):
        return self.name

    def questionsets(self):
        if not hasattr(self, "__qscache"):
            self.__qscache = \
              QuestionSet.objects.filter(questionnaire=self).order_by('sortid')
        return self.__qscache

    class Meta:
        permissions = (
            ("export", "Can export questionnaire answers"),
            ("management", "Management Tools")
        )

class QuestionSet(models.Model):
    __metaclass__ = TransMeta

    "Which questions to display on a question page"
    questionnaire = models.ForeignKey(Questionnaire)
    sortid = models.IntegerField() # used to decide which order to display in
    heading = models.CharField(max_length=64)
    checks = models.CharField(max_length=128, blank=True,
        help_text = """Current options are 'femaleonly' or 'maleonly' and shownif="QuestionNumber,Answer" which takes the same format as <tt>requiredif</tt> for questions.""")
    text = models.TextField(help_text="This is interpreted as Textile: <a href='http://hobix.com/textile/quick.html'>http://hobix.com/textile/quick.html</a>")

    def questions(self):
        if not hasattr(self, "__qcache"):
            self.__qcache = list(Question.objects.filter(questionset=self.id).order_by('number'))
            self.__qcache.sort()
        return self.__qcache

    def next(self):
        qs = self.questionnaire.questionsets()
        retnext = False
        for q in qs:
            if retnext:
                return q
            if q == self:
                retnext = True
        return None

    def prev(self):
        qs = self.questionnaire.questionsets()
        last = None
        for q in qs:
            if q == self:
                return last
            last = q

    def is_last(self):
        try:
            return self.questionnaire.questionsets()[-1] == self
        except NameError:
            # should only occur if not yet saved
            return True

    def is_first(self):
        try:
            return self.questionnaire.questionsets()[0] == self
        except NameError:
            # should only occur if not yet saved
            return True

    def __unicode__(self):
        return u'%s: %s' % (self.questionnaire.name, self.heading)

    class Meta:
        translate = ('text',)


class RunInfo(models.Model):
    "Store the active/waiting questionnaire runs here"
    subject = models.ForeignKey(Subject)
    random = models.CharField(max_length=32) # probably a randomized md5sum
    runid = models.CharField(max_length=32)
    # questionset should be set to the first QuestionSet initially, and to null on completion
    # ... although the RunInfo entry should be deleted then anyway.
    questionset = models.ForeignKey(QuestionSet, blank=True, null=True) # or straight int?
    emailcount = models.IntegerField(default=0)

    created = models.DateTimeField(auto_now_add=True)
    emailsent = models.DateTimeField(null=True, blank=True)

    lastemailerror = models.CharField(max_length=64, null=True, blank=True)

    state = models.CharField(max_length=16, null=True, blank=True)
    cookies = models.TextField(null=True, blank=True)

    tags = models.TextField(
            blank=True,
            help_text=u"Tags active on this run, separated by commas"
        )

    skipped = models.TextField(
            blank=True,
            help_text=u"A comma sepearted list of questions to skip"
        )

    def save(self, **kwargs):
        self.random = (self.random or '').lower()
        super(RunInfo, self).save(**kwargs)

    def set_cookie(self, key, value):
        "runinfo.set_cookie(key, value). If value is None, delete cookie"
        key = key.lower().strip()
        cookies = self.get_cookiedict()
        if type(value) not in (int, float, str, unicode, type(None)):
            raise Exception("Can only store cookies of type integer or string")
        if value is None:
            if key in cookies:
                del cookies[key]
        else:
            if type(value) in ('int', 'float'):
                value=str(value)
            cookies[key] = value
        cstr = json.dumps(cookies)
        self.cookies=cstr
        self.save()
        self.__cookiecache = cookies

    def get_cookie(self, key, default=None):
        if not self.cookies:
            return default
        d = self.get_cookiedict()
        return d.get(key.lower().strip(), default)

    def get_cookiedict(self):
        if not self.cookies:
            return {}
        if not hasattr(self, '__cookiecache'):
            self.__cookiecache = json.loads(self.cookies)
        return self.__cookiecache

    def __unicode__(self):
        return "%s: %s, %s" % (self.runid, self.subject.surname, self.subject.givenname)

    class Meta:
        verbose_name_plural = 'Run Info'


class RunInfoHistory(models.Model):
    subject = models.ForeignKey(Subject)
    runid = models.CharField(max_length=32)
    completed = models.DateField()
    tags = models.TextField(
            blank=True,
            help_text=u"Tags used on this run, separated by commas"
        )
    skipped = models.TextField(
            blank=True,
            help_text=u"A comma sepearted list of questions skipped by this run"
        )
    questionnaire = models.ForeignKey(Questionnaire)

    def __unicode__(self):
        return "%s: %s on %s" % (self.runid, self.subject, self.completed)

    def answers(self):
        "Returns the query for the answers."
        return Answer.objects.filter(subject=self.subject, runid=self.runid)

    class Meta:
        verbose_name_plural = 'Run Info History'

class Question(models.Model):
    __metaclass__ = TransMeta

    questionset = models.ForeignKey(QuestionSet)
    number = models.CharField(max_length=8, help_text=
        "eg. <tt>1</tt>, <tt>2a</tt>, <tt>2b</tt>, <tt>3c</tt><br /> "
        "Number is also used for ordering questions.")
    text = models.TextField(blank=True)
    type = models.CharField(u"Type of question", max_length=32,
        choices = QuestionChoices,
        help_text = u"Determines the means of answering the question. " \
        "An open question gives the user a single-line textfield, " \
        "multiple-choice gives the user a number of choices he/she can " \
        "choose from. If a question is multiple-choice, enter the choices " \
        "this user can choose from below'.")
    extra = models.CharField(u"Extra information", max_length=128, blank=True, null=True, help_text=u"Extra information (use  on question type)")
    checks = models.CharField(u"Additional checks", max_length=128, blank=True,
        null=True, help_text="Additional checks to be performed for this "
        "value (space separated)  <br /><br />"
        "For text fields, <tt>required</tt> is a valid check.<br />"
        "For yes/no choice, <tt>required</tt>, <tt>required-yes</tt>, "
        "and <tt>required-no</tt> are valid.<br /><br />"
        "If this question is required only if another question's answer is "
        'something specific, use <tt>requiredif="QuestionNumber,Value"</tt> '
        'or <tt>requiredif="QuestionNumber,!Value"</tt> for anything but '
        "a specific value.  "
        "You may also combine tests appearing in <tt>requiredif</tt> "
        "by joining them with the words <tt>and</tt> or <tt>or</tt>, "
        'eg. <tt>requiredif="Q1,A or Q2,B"</tt>')
    footer = models.TextField(u"Footer", help_text="Footer rendered below the question interpreted as textile", blank=True)


    def questionnaire(self):
        return self.questionset.questionnaire

    def getcheckdict(self):
        """getcheckdict returns a dictionary of the values in self.checks"""
        if(hasattr(self, '__checkdict_cached')):
            return self.__checkdict_cached
        try:
            self.__checkdict_cached = d = parse_checks(self.sameas().checks or '')
        except ParseException:
            raise Exception("Error Parsing Checks for Question %s: %s" % (
                self.number, self.sameas().checks))
        return d

    def __unicode__(self):
        return u'{%s} (%s) %s' % (unicode(self.questionset), self.number, self.text)
        
    def sameas(self):
        if self.type == 'sameas':
            try:
                self.__sameas = res = getattr(self, "__sameas", 
                    Question.objects.get(number=self.checks, 
                        questionset__questionnaire=self.questionset.questionnaire))
                return res
            except Question.DoesNotExist:
                return Question(type='comment') # replace with something benign
        return self

    def display_number(self):
        "Return either the number alone or the non-number part of the question number indented"
        m = _numre.match(self.number)
        if m:
            sub = m.group(2)
            return "&nbsp;&nbsp;&nbsp;" + sub
        return self.number

    def choices(self):
        if self.type == 'sameas':
            return self.sameas().choices()
        res = Choice.objects.filter(question=self).order_by('sortid')
        return res

    def is_custom(self):
        return "custom" == self.sameas().type

    def get_type(self):
        "Get the type name, treating sameas and custom specially"
        t = self.sameas().type
        if t == 'custom':
            cd = self.sameas().getcheckdict()
            if 'type' not in cd:
                raise Exception("When using custom types, you must have type=<name> in the additional checks field")
            return cd.get('type')
        return t

    def questioninclude(self):
        return "questionnaire/" + self.get_type() + ".html"

    def __cmp__(a, b):
        anum, astr = split_numal(a.number)
        bnum, bstr = split_numal(b.number)
        cmpnum = cmp(anum, bnum)
        return cmpnum or cmp(astr, bstr)

    class Meta:
        translate = ('text', 'extra', 'footer')


class Choice(models.Model):
    __metaclass__ = TransMeta

    question = models.ForeignKey(Question)
    sortid = models.IntegerField()
    value = models.CharField(u"Short Value", max_length=64)
    text = models.CharField(u"Choice Text", max_length=200)

    def __unicode__(self):
        return u'(%s) %d. %s' % (self.question.number, self.sortid, self.text)

    class Meta:
        translate = ('text',)


class Answer(models.Model):
    subject = models.ForeignKey(Subject, help_text = u'The user who supplied this answer')
    question = models.ForeignKey(Question, help_text = u"The question that this is an answer to")
    runid = models.CharField(u'RunID', help_text = u"The RunID (ie. year)", max_length=32)
    answer = models.TextField()

    def __unicode__(self):
        return "Answer(%s: %s, %s)" % (self.question.number, self.subject.surname, self.subject.givenname)

    def choice_str(self, secondary = False):
        choice_string = ""
        choices = self.question.get_choices()

        for choice in choices:
            for split_answer in self.split_answer():
                if str(split_answer) == choice.value:
                    choice_string += str(choice.text) + " "

    def split_answer(self):
        """
        Decode stored answer value and return as a list of choices.
        Any freeform value will be returned in a list as the last item.

        Calling code should be tolerant of freeform answers outside
        of additional [] if data has been stored in plain text format
        """
        try:
            return json.loads(self.answer)
        except ValueError:
            # this was likely saved as plain text, try to guess what the 
            # value(s) were
            if 'multiple' in self.question.type:
                return self.answer.split('; ')
            else:
                return [self.answer]

    def check_answer(self):
        "Confirm that the supplied answer matches what we expect"
        return True

########NEW FILE########
__FILENAME__ = admin

from django.contrib import admin
from models import Page

class PageAdmin(admin.ModelAdmin):
    list_display = ('slug', 'title',)

admin.site.register(Page, PageAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.core.urlresolvers import reverse
from transmeta import TransMeta

class Page(models.Model):
    __metaclass__ = TransMeta

    slug = models.SlugField(unique=True, primary_key=True)
    title = models.CharField(max_length=256)
    body = models.TextField()
    public = models.BooleanField(default=True)

    def __unicode__(self):
        return u"Page[%s]" % self.slug

    def get_absolute_url(self):
        return reverse('page.views.page', kwargs={'page':self.slug})
        

    class Meta:
        pass
        translate = ('title','body',)

########NEW FILE########
__FILENAME__ = views
# Create your views here.
from django.shortcuts import render_to_response
from django.conf import settings
from django.template import RequestContext
from django import http
from django.utils import translation
from models import Page

def page(request, page):
    try:
        p = Page.objects.get(slug=page, public=True)
    except Page.DoesNotExist:
        raise http.Http404('%s page requested but not found' % page)
    
    return render_to_response("page.html", 
            { "request" : request, "page" : p, }, 
            context_instance = RequestContext(request) 
        )

def langpage(request, lang, page):
    translation.activate_language(lang)
    return page(request, page)

def set_language(request):
    next = request.REQUEST.get('next', None)
    if not next:
        next = request.META.get('HTTP_REFERER', None)
        if not next:
            next = '/'
    response = http.HttpResponseRedirect(next)
    if request.method == 'GET':
        lang_code = request.GET.get('language', None)
        if lang_code and translation.check_for_language(lang_code):
            if hasattr(request, 'session'):
                request.session['django_language'] = lang_code
            else:
                response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code)
    return response


########NEW FILE########
__FILENAME__ = parsers
#!/usr/bin/python

__all__ = ('parse_checks', 'BooleanParser')

try: from pyparsing import *
except ImportError: from utils.pyparsing import *

def __make_parser():
    key = Word(alphas, alphanums+"_-")
    value = Word(alphanums + "-.,_=<>!@$%^&*[]{}:;|/'") | QuotedString('"')
    return Dict(ZeroOrMore(Group( key + Optional( Suppress("=") + value, default=True ) ) ))
__checkparser = __make_parser()

def parse_checks(string):
    """
from parsers import parse_checks
>>> parse_checks('dependent=5a,no dependent="5a && 4a" dog="Roaming Rover" name=Robert foo bar')
([(['dependent', '5a,no'], {}), (['dependent', '5a && 4a'], {}), (['dog', 'Roaming Rover'], {}), (['name', 'Robert'], {}), (['foo', True], {}), (['bar', True], {})], {'dependent': [('5a,no', 0), ('5a && 4a', 1)], 'foo': [(True, 4)], 'bar': [(True, 5)], 'dog': [('Roaming Rover', 2)], 'name': [('Robert', 3)]})
"""
    return __checkparser.parseString(string, parseAll=True)


# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# - Boolean Expression Parser -
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-

class BoolOperand(object):
    def __init__(self, t):
        self.args = t[0][0::2]
    def __str__(self):
        sep = " %s " % self.reprsymbol
        return "(" + sep.join(map(str, self.args)) + ")"

class BoolAnd(BoolOperand):
    reprsymbol = '&&'
    def __nonzero__(self):
        for a in self.args:
            if not bool(a):
                return False
        return True

class BoolOr(BoolOperand):
    reprsymbol = '||'    
    def __nonzero__(self):
        for a in self.args:
            if bool(a):
                return True
        return False

class BoolNot(BoolOperand):
    def __init__(self,t):
        self.arg = t[0][1]
    def __str__(self):
        return "!" + str(self.arg)
    def __nonzero__(self):
        return not bool(self.arg)

class Checker(object):
    "Simple wrapper to call a specific function, passing in args and kwargs each time"
    def __init__(self, func, expr, *args, **kwargs):
        self.func = func
        self.expr = expr
        self.args = args
        self.kwargs = kwargs

    def __nonzero__(self):
        return self.func(self.expr, *self.args, **self.kwargs)

    def __hash__(self):
        return hash(self.expr)

    def __unicode__(self):
        try: fname=self.func.func_name
        except: fname="TestExpr"
        return "%s('%s')" % (fname, self.expr)
    __str__ = __unicode__


class BooleanParser(object):
    """Simple boolean parser

>>> def foo(x):
...   if x == '1': return True
...   return False
... 
>>> foo('1')
True
>>> foo('0')
False
>>> p = BooleanParser(foo)
>>> p.parse('1 and 0')
False
>>> p.parse('1 and 1')
True
>>> p.parse('1 or 1')
True
>>> p.parse('0 or 1')
True
>>> p.parse('0 or 0')
False
>>> p.parse('(0 or 0) and 1')
False
>>> p.parse('(0 or 0) and (1)')
False
>>> p.parse('(0 or 1) and (1)')
True
>>> p.parse('(0 or 0) or (1)')
True
"""

    def __init__(self, func, *args, **kwargs): # treats kwarg boolOperand specially!
        self.args = args
        self.kwargs = kwargs
        self.func = func
        if "boolOperand" in kwargs:
            boolOperand = kwargs["boolOperand"]
            del kwargs["boolOperand"]
        else:
            boolOperand = Word(alphanums + "-.,_=<>!@$%^&*[]{}:;|/\\")
        boolOperand = boolOperand.setParseAction(self._check)
        self.boolExpr = operatorPrecedence( boolOperand,
        [
            ("not ", 1, opAssoc.RIGHT, BoolNot),
            ("or",  2, opAssoc.LEFT,  BoolOr),
            ("and", 2, opAssoc.LEFT,  BoolAnd),
        ])

    def _check(self, string, location, tokens):
        checker = Checker(self.func, tokens[0], *self.args, **self.kwargs)
        tokens[0] = checker

    def parse(self, code):
        if not code or not code.strip():
            return False
        return bool(self.boolExpr.parseString(code)[0])
    
    def toString(self, code):
        return str(self.boolExpr.parseString(code)[0])

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = profiler
import hotshot
import os
import time

from django.conf import settings

from django.db import connection

try:
    PROFILE_LOG_BASE = settings.PROFILE_LOG_BASE
except:
    PROFILE_LOG_BASE = "/tmp"


def profile(log_file):
    """Profile some callable.

    This decorator uses the hotshot profiler to profile some callable (like
    a view function or method) and dumps the profile data somewhere sensible
    for later processing and examination.

    It takes one argument, the profile log name. If it's a relative path, it
    places it under the PROFILE_LOG_BASE. It also inserts a time stamp into the 
    file name, such that 'my_view.prof' become 'my_view-20100211T170321.prof', 
    where the time stamp is in UTC. This makes it easy to run and compare 
    multiple trials.     
    """

    if not os.path.isabs(log_file):
        log_file = os.path.join(PROFILE_LOG_BASE, log_file)

    def _outer(f):
        def _inner(*args, **kwargs):
            # Add a timestamp to the profile output when the callable
            # is actually called.
            (base, ext) = os.path.splitext(log_file)
            base = base + "-" + time.strftime("%Y%m%dT%H%M%S", time.gmtime())
            final_log_file = base + ext

            prof = hotshot.Profile(final_log_file)
            try:
                ret = prof.runcall(f, *args, **kwargs)
            finally:
                prof.close()
            return ret

        return _inner
    return _outer

def timethis(fn):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = fn(*args, **kwargs)
        print fn.__name__, 'took', time.time() - start
        return result

    return wrapper

from pprint import pprint

def sqlprint(fn):
    def wrapper(*args, **kwargs):
        connection.queries = list()
        result = fn(*args, **kwargs)
        print fn.__name__, 'issued'
        pprint(connection.queries)
        return result
    return wrapper
########NEW FILE########
__FILENAME__ = choice
from questionnaire import *
from django.utils.translation import ugettext as _, ungettext
from django.utils.simplejson import dumps

@question_proc('choice', 'choice-freeform')
def question_choice(request, question):
    choices = []
    jstriggers = []

    cd = question.getcheckdict()
    key = "question_%s" % question.number
    key2 = "question_%s_comment" % question.number
    val = None
    if key in request.POST:
        val = request.POST[key]
    else:
        if 'default' in cd:
            val = cd['default']
    for choice in question.choices():
        choices.append( ( choice.value == val, choice, ) )

    if question.type == 'choice-freeform':
        jstriggers.append('%s_comment' % question.number)

    return {
        'choices'   : choices,
        'sel_entry' : val == '_entry_',
        'qvalue'    : val or '',
        'required'  : True,
        'comment'   : request.POST.get(key2, ""),
        'jstriggers': jstriggers,
    }

@answer_proc('choice', 'choice-freeform')
def process_choice(question, answer):
    opt = answer['ANSWER'] or ''
    if not opt:
        raise AnswerException(_(u'You must select an option'))
    if opt == '_entry_' and question.type == 'choice-freeform':
        opt = answer.get('comment','')
        if not opt:
            raise AnswerException(_(u'Field cannot be blank'))
        return dumps([[opt]])
    else:
        valid = [c.value for c in question.choices()]
        if opt not in valid:
            raise AnswerException(_(u'Invalid option!'))
    return dumps([opt])
add_type('choice', 'Choice [radio]')
add_type('choice-freeform', 'Choice with a freeform option [radio]')


@question_proc('choice-multiple', 'choice-multiple-freeform')
def question_multiple(request, question):
    key = "question_%s" % question.number
    choices = []
    counter = 0
    cd = question.getcheckdict()
    defaults = cd.get('default','').split(',')
    for choice in question.choices():
        counter += 1
        key = "question_%s_multiple_%d" % (question.number, choice.sortid)
        if key in request.POST or \
          (request.method == 'GET' and choice.value in defaults):
            choices.append( (choice, key, ' checked',) )
        else:
            choices.append( (choice, key, '',) )
    extracount = int(cd.get('extracount', 0))
    if not extracount and question.type == 'choice-multiple-freeform':
        extracount = 1
    extras = []
    for x in range(1, extracount+1):
        key = "question_%s_more%d" % (question.number, x)
        if key in request.POST:
            extras.append( (key, request.POST[key],) )
        else:
            extras.append( (key, '',) )
    return {
        "choices": choices,
        "extras": extras,
        "template"  : "questionnaire/choice-multiple-freeform.html",
        "required" : cd.get("required", False) and cd.get("required") != "0",

    }

@answer_proc('choice-multiple', 'choice-multiple-freeform')
def process_multiple(question, answer):
    multiple = []
    multiple_freeform = []

    requiredcount = 0
    required = question.getcheckdict().get('required', 0)
    if required:
        try:
            requiredcount = int(required)
        except ValueError:
            requiredcount = 1
    if requiredcount and requiredcount > question.choices().count():
        requiredcount = question.choices().count()

    for k, v in answer.items():
        if k.startswith('multiple'):
            multiple.append(v)
        if k.startswith('more') and len(v.strip()) > 0:
            multiple_freeform.append(v)

    if len(multiple) + len(multiple_freeform) < requiredcount:
        raise AnswerException(ungettext(u"You must select at least %d option",
                                        u"You must select at least %d options",
                                        requiredcount) % requiredcount)
    multiple.sort()
    if multiple_freeform:
        multiple.append(multiple_freeform)
    return dumps(multiple)
add_type('choice-multiple', 'Multiple-Choice, Multiple-Answers [checkbox]')
add_type('choice-multiple-freeform', 'Multiple-Choice, Multiple-Answers, plus freeform [checkbox, input]')



########NEW FILE########
__FILENAME__ = custom
#
# Custom type exists for backwards compatibility. All custom types should now
# exist in the drop down list of the management interface.
#

from questionnaire import *
from questionnaire import Processors, QuestionProcessors
from django.utils.translation import ugettext as _

@question_proc('custom')
def question_custom(request, question):
    cd = question.getcheckdict()
    _type = cd['type']
    d = {}
    if _type in QuestionProcessors:
        d = QuestionProcessors[_type](request, question)
    if 'template' not in d:
        d['template'] = 'questionnaire/%s.html' % _type
    return d

@answer_proc('custom')
def process_custom(question, answer):
    cd = question.getcheckdict()
    _type = cd['type']
    if _type in Processors:
        return Processors[_type](question, answer)
    raise AnswerException(_(u"Processor not defined for this question"))


########NEW FILE########
__FILENAME__ = range
from questionnaire import *
from django.conf import settings
from django.utils.translation import ugettext as _
from django.utils.simplejson import dumps

@question_proc('range')
def question_range(request, question):
    cd = question.getcheckdict()
    
    rmin, rmax = parse_range(cd)
    rstep = parse_step(cd)
    runit = cd.get('unit', '')
    
    current = request.POST.get('question_%s' % question.number, rmin)

    return {
        'required' : True,
        'rmin' : rmin,
        'rmax' : rmax,
        'rstep' : rstep,
        'runit' : runit,
        'current' : current,
        'jsinclude' : [settings.STATIC_URL+'range.js']
    }

@answer_proc('range')
def process_range(question, answer):
    cd = question.getcheckdict()

    rmin, rmax = parse_range(cd)
    rstep = parse_step(cd)

    convert = range_type(rmin, rmax, rstep)

    try:
    	ans = convert(answer['ANSWER'])
    except:
	   raise AnswerException("Could not convert `%r`")
    
    if ans > convert(rmax) or ans < convert(rmin):
        raise AnswerException(_(u"Out of range"))

    return dumps([ans])

add_type('range', 'Range of numbers [select]')

def parse_range(checkdict):
    "Given a checkdict for a range widget return the min and max string values."

    Range = checkdict.get('range', '1-5')

    try:
        rmin, rmax = Range.split('-', 1)
    except ValueError:
        rmin, rmax = '1', '5'

    return rmin, rmax

def parse_step(checkdict):
    "Given a checkdict for a range widget return the step as string value."

    return checkdict.get('step', '1')

def range_type(rmin, rmax, step):
    """Given the min, max and step value return float or int depending on
    the number of digits after 0.

    """

    if any((digits(rmin), digits(rmax), digits(step))):
        return float
    else:
        return int

def digits(number):
    "Given a number as string return the number of digits after 0."
    if '.' in number or ',' in number:
        if '.' in number:
            return len(number.split('.')[1])
        else:
            return len(number.split(',')[1])
    else:
        return 0

########NEW FILE########
__FILENAME__ = simple
from questionnaire import *
from django.utils.translation import ugettext as _
from django.utils.simplejson import dumps

@question_proc('choice-yesno','choice-yesnocomment','choice-yesnodontknow')
def question_yesno(request, question):
    key = "question_%s" % question.number
    key2 = "question_%s_comment" % question.number
    val = request.POST.get(key, None)
    cmt = request.POST.get(key2, '')
    qtype = question.get_type()
    cd = question.getcheckdict()
    jstriggers = []

    if qtype == 'choice-yesnocomment':
        hascomment = True
    else:
        hascomment = False
    if qtype == 'choice-yesnodontknow' or 'dontknow' in cd:
        hasdontknow = True
    else:
        hasdontknow = False

    if not val:
        if cd.get('default', None):
            val = cd['default']

    checks = ''
    if hascomment:
        if cd.get('required-yes'):
            jstriggers = ['%s_comment' % question.number]
            checks = ' checks="dep_check(\'%s,yes\')"' % question.number
        elif cd.get('required-no'):
            checks = ' checks="dep_check(\'%s,no\')"' % question.number
        elif cd.get('required-dontknow'):
            checks = ' checks="dep_check(\'%s,dontknow\')"' % question.number

    return {
        'required' : True,
        'checks' : checks,
        'value' : val,
        'qvalue' : '',
        'hascomment' : hascomment,
        'hasdontknow' : hasdontknow,
        'comment' : cmt,
        'jstriggers' : jstriggers,
        'template' : 'questionnaire/choice-yesnocomment.html',
    }

@question_proc('open', 'open-textfield')
def question_open(request, question):
    key = "question_%s" % question.number
    value = question.getcheckdict().get('default','')
    if key in request.POST:
        value = request.POST[key]
    return {
        'required' : question.getcheckdict().get('required', False),
        'value' : value,
    }

@answer_proc('open', 'open-textfield', 'choice-yesno', 'choice-yesnocomment', 'choice-yesnodontknow')
def process_simple(question, ansdict):
    checkdict = question.getcheckdict()
    ans = ansdict['ANSWER'] or ''
    qtype = question.get_type()
    if qtype.startswith('choice-yesno'):
        if ans not in ('yes','no','dontknow'):
            raise AnswerException(_(u'You must select an option'))
        if qtype == 'choice-yesnocomment' \
        and len(ansdict.get('comment','').strip()) == 0:
            if checkdict.get('required', False):
                raise AnswerException(_(u'Field cannot be blank'))
            if checkdict.get('required-yes', False) and ans == 'yes':
                raise AnswerException(_(u'Field cannot be blank'))
            if checkdict.get('required-no', False) and ans == 'no':
                raise AnswerException(_(u'Field cannot be blank'))
    else:
        if not ans.strip() and checkdict.get('required', False):
           raise AnswerException(_(u'Field cannot be blank'))
    if ansdict.has_key('comment') and len(ansdict['comment']) > 0:
        return dumps([ans, [ansdict['comment']]])
    if ans:
        return dumps([ans])
    return dumps([])
add_type('open', 'Open Answer, single line [input]')
add_type('open-textfield', 'Open Answer, multi-line [textarea]')
add_type('choice-yesno', 'Yes/No Choice [radio]')
add_type('choice-yesnocomment', 'Yes/No Choice with optional comment [radio, input]')
add_type('choice-yesnodontknow', 'Yes/No/Don\'t know Choice [radio]')


@answer_proc('comment')
def process_comment(question, answer):
    pass
add_type('comment', 'Comment Only')




########NEW FILE########
__FILENAME__ = timeperiod
from questionnaire import *
from django.utils.translation import ugettext as _, ugettext_lazy

perioddict = {
    "second" : ugettext_lazy("second(s)"),
    "minute" : ugettext_lazy("minute(s)"),
    "hour" : ugettext_lazy("hour(s)"),
    "day" : ugettext_lazy("day(s)"),
    "week" : ugettext_lazy("week(s)"),
    "month" : ugettext_lazy("month(s)"),
    "year" : ugettext_lazy("year(s)"),
}

@question_proc('timeperiod')
def question_timeperiod(request, question):
    cd = question.getcheckdict()
    if "units" in cd:
        units = cd["units"].split(',')
    else:
        units = ["day","week","month","year"]
    timeperiods = []
    if not units:
        units = ["day","week","month","year"]

    key1 = "question_%s" % question.number
    key2 = "question_%s_unit" % question.number
    value = request.POST.get(key1, '')
    unitselected = request.POST.get(key2, units[0])

    for x in units:
        if x in perioddict:
            timeperiods.append( (x, unicode(perioddict[x]), unitselected==x) )
    return {
        "required" : "required" in cd,
        "timeperiods" : timeperiods,
        "value" : value,
    }

@answer_proc('timeperiod')
def process_timeperiod(question, answer):
    if not answer['ANSWER'] or not answer.has_key('unit'):
        raise AnswerException(_(u"Invalid time period"))
    period = answer['ANSWER'].strip()
    if period:
        try:
            period = str(int(period))
        except ValueError:
            raise AnswerException(_(u"Time period must be a whole number"))
    unit = answer['unit']
    checkdict = question.getcheckdict()
    if checkdict and 'units' in checkdict:
        units = checkdict['units'].split(',')
    else:
        units = ('day', 'hour', 'week', 'month', 'year')
    if not period and "required" in checkdict:
        raise AnswerException(_(u'Field cannot be blank'))
    if unit not in units:
        raise AnswerException(_(u"Invalid time period"))
    return "%s; %s" % (period, unit)

add_type('timeperiod', 'Time Period [input, select]')


########NEW FILE########
__FILENAME__ = request_cache
# Per request cache middleware

# Provides a simple cache dictionary only existing for the request's lifetime

# The middleware provides a threadsafe LocMemCache which can be used just
# like any other django cache facility

from functools import wraps
from threading import currentThread
from django.core.cache.backends.locmem import LocMemCache

_request_cache = {}
_installed_middleware = False

def get_request_cache():
    assert _installed_middleware, 'RequestCacheMiddleware not loaded'
    return _request_cache[currentThread()]

def clear_request_cache():
    _request_cache[currentThread()].clear()

class RequestCache(LocMemCache):
    def __init__(self):
        name = 'locmemcache@%i' % hash(currentThread())
        params = dict()
        super(RequestCache, self).__init__(name, params)

class RequestCacheMiddleware(object):
    def __init__(self):
        global _installed_middleware
        _installed_middleware = True

    def process_request(self, request):
        cache = _request_cache.get(currentThread()) or RequestCache()
        _request_cache[currentThread()] = cache

        cache.clear()

class request_cache(object):
    """ A decorator for use around functions that should be cached for the current
    request. Use like this:

    @request_cache()
    def cached(name):
        print "My name is %s and I'm cached" % name

    @request_cache(keyfn=lambda p: p['id'])
    def cached(param):
        print "My id is %s" % p['id']

    If no keyfn is provided the decorator expects the args to be hashable.

    """

    def __init__(self, keyfn=None):
        self.keyfn = keyfn or (lambda *args: hash(args))

    def __call__(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_request_cache()

            cachekey = self.keyfn(*args)
            cacheval = cache.get(cachekey, 'expired')
            
            if not cacheval == 'expired':
                return cacheval

            result = func(*args, **kwargs)
            cache.set(cachekey, result)

            return result

        return wrapper
########NEW FILE########
__FILENAME__ = questionnaire
#!/usr/bin/python

from django import template
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

register = template.Library()


@register.filter(name="dictget")
def dictget(thedict, key):
    "{{ dictionary|dictget:variableholdingkey }}"
    return thedict.get(key, None)


@register.filter(name="spanclass")
def spanclass(string):
    l = 2 + len(string.strip()) // 6
    if l <= 4:
        return "span-4"
    if l <= 7:
        return "span-7"
    if l < 10:
        return "span-10"
    return "span-%d" % l

@register.filter(name="qtesturl")
def qtesturl(question):
    qset = question.questionset
    return reverse("questionset",
        args=("test:%s" % qset.questionnaire.id,
         qset.sortid))


########NEW FILE########
__FILENAME__ = tests
"""
Basic Test Suite for Questionnaire Application

Unfortunately Django 1.0 only has TestCase and not TransactionTestCase
so we can't test that a submitted page with an error does not have any
answers submitted to the DB.
"""
from django.test import TestCase
from django.test.client import Client
from questionnaire.models import *
from datetime import datetime
import os

class TypeTest(TestCase):
    fixtures = ( 'testQuestions.yaml', )
    urls = 'questionnaire.test_urls'

    def setUp(self):
        self.ansdict1 = {
            'questionset_id' : '1',
            'question_1' : 'Open Answer 1',
            'question_2' : 'Open Answer 2\r\nMultiline',
            'question_3' : 'yes',
            'question_4' : 'dontknow',
            'question_5' : 'yes',
            'question_5_comment' : 'this comment is required because of required-yes check',
            'question_6' : 'no',
            'question_6_comment' : 'this comment is required because of required-no check',
            'question_7' : '5',
            'question_8_unit' : 'week',
            'question_8' : '2',
        }
        self.ansdict2 = {
            'questionset_id' : '2',
            'question_9' : 'q9_choice1',  # choice
            'question_10' : '_entry_', # choice-freeform
            'question_10_comment' : 'my freeform',
            'question_11_multiple_2' : 'q11_choice2', # choice-multiple
            'question_11_multiple_4' : 'q11_choice4', # choice-multiple
            'question_12_multiple_1' : 'q12_choice1',# choice-multiple-freeform
            'question_12_more_1' : 'blah', # choice-multiple-freeform
        }
        runinfo = self.runinfo = RunInfo.objects.get(runid='test:test')
        self.runid = runinfo.runid
        self.subject_id = runinfo.subject_id


    def test010_redirect(self):
        "Check redirection from generic questionnaire to questionset"
        response = self.client.get('/q/test:test/')
        self.assertEqual(response['Location'], 'http://testserver/q/test:test/1/')


    def test020_get_questionset_1(self):
        "Get first page of Questions"
        response = self.client.get('/q/test:test/1/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template[0].name, 'questionnaire/questionset.html')


    def test030_language_setting(self):
        "Set the language and confirm it is set in DB"
        response = self.client.get('/q/test:test/1/', {"lang" : "en"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://testserver/q/test:test/1/')
        response = self.client.get('/q/test:test/1/')
        assert "Don't Know" in response.content
        self.assertEqual(response.status_code, 200)
        runinfo = RunInfo.objects.get(runid='test:test')
        self.assertEqual(runinfo.subject.language, 'en')
        response = self.client.get('/q/test:test/1/', {"lang" : "de"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://testserver/q/test:test/1/')
        response = self.client.get('/q/test:test/1/')
        assert "Weiss nicht" in response.content
        self.assertEqual(response.status_code, 200)
        runinfo = RunInfo.objects.get(runid='test:test')
        self.assertEqual(runinfo.subject.language, 'de')


    def test040_missing_question(self):
        "Post questions with a mandatory field missing"
        c = self.client
        ansdict = self.ansdict1.copy()
        del ansdict['question_3']
        response = c.post('/q/test:test/1/', ansdict)
        self.assertEqual(response.status_code, 200)
        errors = response.context[-1]['errors']
        self.assertEqual(len(errors), 1) and errors.has_key('3')


    def test050_missing_question(self):
        "Post questions with a mandatory field missing"
        c = self.client
        ansdict = self.ansdict1.copy()
        del ansdict['question_5_comment']
        # first set language to english
        response = self.client.get('/q/test:test/1/', {"lang" : "en"})
        response = c.post('/q/test:test/1/', ansdict)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context[-1]['errors']), 1)


    def test060_successful_questionnaire(self):
        "POST complete answers for QuestionSet 1"
        c = self.client
        ansdict1 = self.ansdict1
        runinfo = RunInfo.objects.get(runid='test:test')
        runid = runinfo.random = runinfo.runid = '1real'
        runinfo.save()

        response = c.get('/q/1real/1/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template[0].name, 'questionnaire/questionset.html')
        response = c.post('/q/1real/', ansdict1)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://testserver/q/1real/2/')
        "POST complete answers for QuestionSet 2"
        c = self.client

        ansdict2 = self.ansdict2
        response = c.get('/q/1real/2/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template[0].name, 'questionnaire/questionset.html')
        response = c.post('/q/1real/', ansdict2)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://testserver/')

        self.assertEqual(RunInfo.objects.filter(runid='1real').count(), 0)

        # TODO: The format of these answers seems very strange to me. It was 
        # simpler before I changed it to get the test to work. 
        # I'll have to revisit this once I figure out how this is meant to work
        # for now it is more important to me that all tests pass

        dbvalues = {
            '1' : u'["%s"]' % ansdict1['question_1'],
            '2' : u'["%s"]' % ansdict1['question_2'],
            '3' : u'["%s"]' % ansdict1['question_3'],
            '4' : u'["%s"]' % ansdict1['question_4'],
            '5' : u'["%s", ["%s"]]' % (ansdict1['question_5'], ansdict1['question_5_comment']),
            '6' : u'["%s", ["%s"]]' % (ansdict1['question_6'], ansdict1['question_6_comment']),
            '7' : u'[%s]' % ansdict1['question_7'],
            '8' : u'%s; %s' % (ansdict1['question_8'], ansdict1['question_8_unit']),
            '9' : u'["q9_choice1"]',
            '10' : u'[["my freeform"]]',
            '11' : u'["q11_choice2", "q11_choice4"]',
            '12' : u'["q12_choice1", ["blah"]]',
        }
        for k, v in dbvalues.items():
            ans = Answer.objects.get(runid=runid, subject__id=self.subject_id,
                question__number=k)
            
            v = v.replace('\r', '\\r').replace('\n', '\\n')
            self.assertEqual(ans.answer, v)

    def test070_tags(self):
        c = self.client

        # the first questionset in questionnaire 2 is always shown, 
        # but one of its 2 questions is tagged with testtag
        with_tags = c.get('/q/test:withtags/1/')

        # so we'll get two questions shown if the run is tagged
        self.assertEqual(with_tags.status_code, 200)
        self.assertEqual(len(with_tags.context['qlist']), 2)

        # one question, if the run is not tagged
        without_tags = c.get('/q/test:withouttags/1/')

        self.assertEqual(without_tags.status_code, 200)
        self.assertEqual(len(without_tags.context['qlist']), 1)

        # the second questionset is only shown if the run is tagged
        with_tags = c.get('/q/test:withtags/2/')

        self.assertEqual(with_tags.status_code, 200)
        self.assertEqual(len(with_tags.context['qlist']), 1)

        # meaning it'll be skipped on the untagged run
        without_tags = c.get('/q/test.withouttags/2/')

        self.assertEqual(without_tags.status_code, 302) # redirect

        # the progress values of the first questionset should reflect
        # the fact that in one run there's only one questionset
        with_tags = c.get('/q/test:withtags/1/')
        without_tags = c.get('/q/test:withouttags/1/')

        self.assertEqual(with_tags.context['progress'], 50)
        self.assertEqual(without_tags.context['progress'], 100)
########NEW FILE########
__FILENAME__ = test_urls
# vim: set fileencoding=utf-8

import questionnaire
from django.conf.urls.defaults import *
from views import *

urlpatterns = patterns('',
    url(r'^q/(?P<runcode>[^/]+)/(?P<qs>\d+)/$',
        'questionnaire.views.questionnaire', name='questionset'),
    url(r'^q/([^/]+)/',
        'questionnaire.views.questionnaire', name='questionset'),
    url(r'^q/manage/csv/(\d+)/',
        'questionnaire.views.export_csv'),
    url(r'^q/manage/sendemail/(\d+)/$',
        'questionnaire.views.send_email'),
    url(r'^q/manage/manage/sendemails/$',
        'questionnaire.views.send_emails'),
)

########NEW FILE########
__FILENAME__ = urls
# vim: set fileencoding=utf-8

from django.conf.urls.defaults import *
from views import *

urlpatterns = patterns('',
    url(r'^$',
            questionnaire, name='questionnaire_noargs'),
    url(r'^csv/(?P<qid>\d+)/$',
            export_csv, name='export_csv'),
    url(r'^(?P<runcode>[^/]+)/progress/$', 
            get_async_progress, name='progress'),
    url(r'^(?P<runcode>[^/]+)/(?P<qs>[-]{0,1}\d+)/$',
            questionnaire, name='questionset'),
    url(r'^(?P<runcode>[^/]+)/$',
            questionnaire, name='questionnaire'),
)

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/python

def split_numal(val):
    """Split, for example, '1a' into (1, 'a')
>>> split_numal("11a")
(11, 'a')
>>> split_numal("99")
(99, '')
>>> split_numal("a")
(0, 'a')
>>> split_numal("")
(0, '')
    """
    if not val:
        return 0, ''
    for i in range(len(val)):
        if not val[i].isdigit():
            return int(val[0:i] or '0'), val[i:]
    return int(val), ''
        

def numal_sort(a, b):
    """Sort a list numeric-alphabetically

>>> vals = "1a 1 10 10a 10b 11 2 2a z".split(" "); \\
... vals.sort(numal_sort); \\
... " ".join(vals)
'z 1 1a 2 2a 10 10a 10b 11'
    """
    anum, astr = split_numal(a)
    bnum, bstr = split_numal(b)
    cmpnum = cmp(anum, bnum)
    if(cmpnum == 0):
        return cmp(astr, bstr)
    return cmpnum

def numal0_sort(a, b):
    """
    numal_sort on the first items in the list
    """
    return numal_sort(a[0], b[0])

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = views
#!/usr/bin/python
# vim: set fileencoding=utf-8
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.contrib.auth.decorators import permission_required
from django.shortcuts import render_to_response, get_object_or_404
from django.db import transaction
from django.conf import settings
from datetime import datetime
from django.utils import translation
from django.utils.translation import ugettext_lazy as _
from questionnaire import QuestionProcessors
from questionnaire import questionnaire_done
from questionnaire import questionset_done
from questionnaire import AnswerException
from questionnaire import Processors
from questionnaire.models import *
from questionnaire.parsers import *
from questionnaire.emails import _send_email, send_emails
from questionnaire.utils import numal_sort, split_numal
from questionnaire.request_cache import request_cache
from questionnaire import profiler
import logging
import random
import md5
import re

def r2r(tpl, request, **contextdict):
    "Shortcut to use RequestContext instead of Context in templates"
    contextdict['request'] = request
    return render_to_response(tpl, contextdict, context_instance = RequestContext(request))

def get_runinfo(random):
    "Return the RunInfo entry with the provided random key"
    res = RunInfo.objects.filter(random=random.lower())
    return res and res[0] or None

def get_question(number, questionnaire):
    "Return the specified Question (by number) from the specified Questionnaire"
    res = Question.objects.filter(number=number, questionset__questionnaire=questionnaire)
    return res and res[0] or None


def delete_answer(question, subject, runid):
    "Delete the specified question/subject/runid combination from the Answer table"
    Answer.objects.filter(subject=subject, runid=runid, question=question).delete()


def add_answer(runinfo, question, answer_dict):
    """
    Add an Answer to a Question for RunInfo, given the relevant form input
    
    answer_dict contains the POST'd elements for this question, minus the
    question_{number} prefix.  The question_{number} form value is accessible
    with the ANSWER key.
    """
    answer = Answer()
    answer.question = question
    answer.subject = runinfo.subject
    answer.runid = runinfo.runid

    type = question.get_type()

    if "ANSWER" not in answer_dict:
        answer_dict['ANSWER'] = None

    if type in Processors:
        answer.answer = Processors[type](question, answer_dict) or ''
    else:
        raise AnswerException("No Processor defined for question type %s" % type)

    # first, delete all existing answers to this question for this particular user+run
    delete_answer(question, runinfo.subject, runinfo.runid)
    
    # then save the new answer to the database
    answer.save()
    
    return True

def check_parser(runinfo, exclude=[]):
    depparser = BooleanParser(dep_check, runinfo, {})
    tagparser = BooleanParser(has_tag, runinfo)

    fnmap = {
        "maleonly": lambda v: runinfo.subject.gender == 'male',
        "femaleonly": lambda v: runinfo.subject.gender == 'female',
        "shownif": lambda v: v and depparser.parse(v),
        "iftag": lambda v: v and tagparser.parse(v)
    }

    for ex in exclude:
        del fnmap[ex]

    @request_cache()
    def satisfies_checks(checks):
        if not checks:
            return True

        checks = parse_checks(checks)

        for check, value in checks.items():
            if check in fnmap:                
                value = value and value.strip()
                if not fnmap[check](value):
                    return False

        return True

    return satisfies_checks

@request_cache()
def skipped_questions(runinfo):
    if not runinfo.skipped:
        return []

    return [s.strip() for s in runinfo.skipped.split(',')]

@request_cache()
def question_satisfies_checks(question, runinfo, checkfn=None):
    if question.number in skipped_questions(runinfo):
        return False

    checkfn = checkfn or check_parser(runinfo)
    return checkfn(question.checks)

@request_cache(keyfn=lambda *args: args[0].id)
def questionset_satisfies_checks(questionset, runinfo, checks=None):
    """Return True if the runinfo passes the checks specified in the QuestionSet

    Checks is an optional dictionary with the keys being questionset.pk and the
    values being the checks of the contained questions. 
    
    This, in conjunction with fetch_checks allows for fewer 
    db roundtrips and greater performance.

    Sadly, checks cannot be hashed and therefore the request cache is useless
    here. Thankfully the benefits outweigh the costs in my tests.
    """

    passes = check_parser(runinfo)

    if not passes(questionset.checks):
        return False

    if not checks:
        checks = dict()
        checks[questionset.id] = []

        for q in questionset.questions():
            checks[questionset.id].append((q.checks, q.number))

    # questionsets that pass the checks but have no questions are shown
    # (comments, last page, etc.)
    if not checks[questionset.id]:
        return True

    # if there are questions at least one needs to be visible
    for check, number in checks[questionset.id]:
        if number in skipped_questions(runinfo):
            continue

        if passes(check):
            return True

    return False

def get_progress(runinfo):

    position, total = 0, 0
    
    current = runinfo.questionset
    sets = current.questionnaire.questionsets()

    checks = fetch_checks(sets)

    # fetch the all question checks at once. This greatly improves the
    # performance of the questionset_satisfies_checks function as it
    # can avoid a roundtrip to the database for each question

    for qs in sets:
        if questionset_satisfies_checks(qs, runinfo, checks):
            total += 1

        if qs.id == current.id:
            position = total

    if not all((position, total)):
        progress = 1
    else:
        progress = float(position) / float(total) * 100.00
        
        # progress is always at least one percent
        progress = progress >= 1.0 and progress or 1

    return int(progress)

def get_async_progress(request, runcode, *args, **kwargs):
    """ Returns the progress as json for use with ajax """

    runinfo = get_runinfo(runcode)
    response = dict(progress=get_progress(runinfo))

    cache.set('progress' + runinfo.random, response['progress'])
    response = HttpResponse(json.dumps(response), 
               mimetype='application/javascript');
    response["Cache-Control"] = "no-cache"
    return response

def fetch_checks(questionsets):
    ids = [qs.pk for qs in questionsets]
    
    query = Question.objects.filter(questionset__pk__in=ids)
    query = query.values('questionset_id', 'checks', 'number')

    checks = dict()
    for qsid in ids:
        checks[qsid] = list()

    for result in (r for r in query):
        checks[result['questionset_id']].append(
            (result['checks'], result['number'])
        )

    return checks

def redirect_to_qs(runinfo):
    "Redirect to the correct and current questionset URL for this RunInfo"

    # cache current questionset
    qs = runinfo.questionset

    # skip questionsets that don't pass
    if not questionset_satisfies_checks(runinfo.questionset, runinfo):
        
        next = runinfo.questionset.next()
        
        while next and not questionset_satisfies_checks(next, runinfo):
            next = next.next()
        
        runinfo.questionset = next
        runinfo.save()

        hasquestionset = bool(next)
    else:
        hasquestionset = True

    # empty ?
    if not hasquestionset:
        logging.warn('no questionset in questionnaire which passes the check')
        return finish_questionnaire(runinfo, qs.questionnaire)

    url = reverse("questionset",
                args=[ runinfo.random, runinfo.questionset.sortid ])
    return HttpResponseRedirect(url)

@transaction.commit_on_success
def questionnaire(request, runcode=None, qs=None):
    """
    Process submitted answers (if present) and redirect to next page

    If this is a POST request, parse the submitted data in order to store
    all the submitted answers.  Then return to the next questionset or
    return a completed response.

    If this isn't a POST request, redirect to the main page.

    We only commit on success, to maintain consistency.  We also specifically
    rollback if there were errors processing the answers for this questionset.
    """

    # if runcode provided as query string, redirect to the proper page
    if not runcode:
        runcode = request.GET.get('runcode')
        if not runcode:
            return HttpResponseRedirect("/")
        else:
            return HttpResponseRedirect(reverse("questionnaire",args=[runcode]))

    runinfo = get_runinfo(runcode)

    if not runinfo:
        transaction.commit()
        return HttpResponseRedirect('/')

    # let the runinfo have a piggy back ride on the request
    # so we can easily use the runinfo in places like the question processor
    # without passing it around
    request.runinfo = runinfo

    if not qs:
        # Only change the language to the subjects choice for the initial
        # questionnaire page (may be a direct link from an email)
        if hasattr(request, 'session'):
            request.session['django_language'] = runinfo.subject.language
            translation.activate(runinfo.subject.language)

    if 'lang' in request.GET:
        return set_language(request, runinfo, request.path)

    # --------------------------------
    # --- Handle non-POST requests --- 
    # --------------------------------

    if request.method != "POST":
        if qs is not None:
            qs = get_object_or_404(QuestionSet, sortid=qs, questionnaire=runinfo.questionset.questionnaire)
            if runinfo.random.startswith('test:'):
                pass # ok for testing
            elif qs.sortid > runinfo.questionset.sortid:
                # you may jump back, but not forwards
                return redirect_to_qs(runinfo)
            runinfo.questionset = qs
            runinfo.save()
            transaction.commit()
        # no questionset id in URL, so redirect to the correct URL
        if qs is None:
            return redirect_to_qs(runinfo)
        return show_questionnaire(request, runinfo)

    # -------------------------------------
    # --- Process POST with QuestionSet ---
    # -------------------------------------

    # if the submitted page is different to what runinfo says, update runinfo
    # XXX - do we really want this?
    qs = request.POST.get('questionset_id', None)
    try:
        qsobj = QuestionSet.objects.filter(pk=qs)[0]
        if qsobj.questionnaire == runinfo.questionset.questionnaire:
            if runinfo.questionset != qsobj:
                runinfo.questionset = qsobj
                runinfo.save()
    except:
        pass

    questionnaire = runinfo.questionset.questionnaire
    questionset = runinfo.questionset

    # to confirm that we have the correct answers
    expected = questionset.questions()

    items = request.POST.items()
    extra = {} # question_object => { "ANSWER" : "123", ... }

    # this will ensure that each question will be processed, even if we did not receive
    # any fields for it. Also works to ensure the user doesn't add extra fields in
    for x in expected:
        items.append( (u'question_%s_Trigger953' % x.number, None) )

    # generate the answer_dict for each question, and place in extra
    for item in items:
        key, value = item[0], item[1]
        if key.startswith('question_'):
            answer = key.split("_", 2)
            question = get_question(answer[1], questionnaire)
            if not question:
                logging.warn("Unknown question when processing: %s" % answer[1])
                continue
            extra[question] = ans = extra.get(question, {})
            if(len(answer) == 2):
                ans['ANSWER'] = value
            elif(len(answer) == 3):
                ans[answer[2]] = value
            else:
                logging.warn("Poorly formed form element name: %r" % answer)
                continue
            extra[question] = ans

    errors = {}
    for question, ans in extra.items():
        if not question_satisfies_checks(question, runinfo):
            continue
        if u"Trigger953" not in ans:
            logging.warn("User attempted to insert extra question (or it's a bug)")
            continue
        try:
            cd = question.getcheckdict()
            # requiredif is the new way
            depon = cd.get('requiredif',None) or cd.get('dependent',None)
            if depon:
                depparser = BooleanParser(dep_check, runinfo, extra)
                if not depparser.parse(depon):
                    # if check is not the same as answer, then we don't care
                    # about this question plus we should delete it from the DB
                    delete_answer(question, runinfo.subject, runinfo.runid)
                    if cd.get('store', False):
                        runinfo.set_cookie(question.number, None)
                    continue
            add_answer(runinfo, question, ans)
            if cd.get('store', False):
                runinfo.set_cookie(question.number, ans['ANSWER'])
        except AnswerException, e:
            errors[question.number] = e
        except Exception:
            logging.exception("Unexpected Exception")
            transaction.rollback()
            raise

    if len(errors) > 0:
        res = show_questionnaire(request, runinfo, errors=errors)
        transaction.rollback()
        return res

    questionset_done.send(sender=None,runinfo=runinfo,questionset=questionset)

    next = questionset.next()
    while next and not questionset_satisfies_checks(next, runinfo):
        next = next.next()
    runinfo.questionset = next
    runinfo.save()

    if next is None: # we are finished
        return finish_questionnaire(runinfo, questionnaire)

    transaction.commit()
    return redirect_to_qs(runinfo)

def finish_questionnaire(runinfo, questionnaire):
    hist = RunInfoHistory()
    hist.subject = runinfo.subject
    hist.runid = runinfo.runid
    hist.completed = datetime.now()
    hist.questionnaire = questionnaire
    hist.tags = runinfo.tags
    hist.skipped = runinfo.skipped
    hist.save()

    questionnaire_done.send(sender=None, runinfo=runinfo,
                            questionnaire=questionnaire)

    redirect_url = questionnaire.redirect_url
    for x,y in (('$LANG', translation.get_language()),
                ('$SUBJECTID', runinfo.subject.id),
                ('$RUNID', runinfo.runid),):
        redirect_url = redirect_url.replace(x, str(y))

    if runinfo.runid in ('12345', '54321') \
    or runinfo.runid.startswith('test:'):
        runinfo.questionset = QuestionSet.objects.filter(questionnaire=questionnaire).order_by('sortid')[0]
        runinfo.save()
    else:
        runinfo.delete()
    transaction.commit()
    if redirect_url:
        return HttpResponseRedirect(redirect_url)
    return r2r("questionnaire/complete.$LANG.html", request)

def show_questionnaire(request, runinfo, errors={}):
    """
    Return the QuestionSet template

    Also add the javascript dependency code.
    """
    questions = runinfo.questionset.questions()

    qlist = []
    jsinclude = []      # js files to include
    cssinclude = []     # css files to include
    jstriggers = []
    qvalues = {}

    # initialize qvalues        
    cookiedict = runinfo.get_cookiedict()                                                                                                                       
    for k,v in cookiedict.items():
        qvalues[k] = v

    substitute_answer(qvalues, runinfo.questionset)

    for question in questions:

        # if we got here the questionset will at least contain one question
        # which passes, so this is all we need to check for
        if not question_satisfies_checks(question, runinfo):
            continue

        Type = question.get_type()
        _qnum, _qalpha = split_numal(question.number)

        qdict = {
            'template' : 'questionnaire/%s.html' % (Type),
            'qnum' : _qnum,
            'qalpha' : _qalpha,
            'qtype' : Type,
            'qnum_class' : (_qnum % 2 == 0) and " qeven" or " qodd",
            'qalpha_class' : _qalpha and (ord(_qalpha[-1]) % 2 \
                                          and ' alodd' or ' aleven') or '',
        }
        
        # substitute answer texts
        substitute_answer(qvalues, question)

        # add javascript dependency checks
        cd = question.getcheckdict()
        depon = cd.get('requiredif',None) or cd.get('dependent',None)
        if depon:
            # extra args to BooleanParser are not required for toString
            parser = BooleanParser(dep_check)
            qdict['checkstring'] = ' checks="%s"' % parser.toString(depon)
            jstriggers.append('qc_%s' % question.number)
        if 'default' in cd and not question.number in cookiedict:
            qvalues[question.number] = cd['default']
        if Type in QuestionProcessors:
            qdict.update(QuestionProcessors[Type](request, question))
            if 'jsinclude' in qdict:
                if qdict['jsinclude'] not in jsinclude:
                    jsinclude.extend(qdict['jsinclude'])
            if 'cssinclude' in qdict:
                if qdict['cssinclude'] not in cssinclude:
                    cssinclude.extend(qdict['jsinclude'])
            if 'jstriggers' in qdict:
                jstriggers.extend(qdict['jstriggers'])
            if 'qvalue' in qdict and not question.number in cookiedict:
                qvalues[question.number] = qdict['qvalue']
                
        qlist.append( (question, qdict) )
    
    try:
        has_progress = settings.QUESTIONNAIRE_PROGRESS in ('async', 'default')
        async_progress = settings.QUESTIONNAIRE_PROGRESS == 'async'
    except AttributeError:
        has_progress = True
        async_progress = False

    if has_progress:
        if async_progress:
            progress = cache.get('progress' + runinfo.random, 1)
        else:
            progress = get_progress(runinfo)
    else:
        progress = 0

    if request.POST:
        for k,v in request.POST.items():
            if k.startswith("question_"):
                s = k.split("_")
                if len(s) == 4:
                    qvalues[s[1]+'_'+v] = '1' # evaluates true in JS
                elif len(s) == 3 and s[2] == 'comment':
                    qvalues[s[1]+'_'+s[2]] = v
                else:
                    qvalues[s[1]] = v

    r = r2r("questionnaire/questionset.html", request,
        questionset=runinfo.questionset,
        runinfo=runinfo,
        errors=errors,
        qlist=qlist,
        progress=progress,
        triggers=jstriggers,
        qvalues=qvalues,
        jsinclude=jsinclude,
        cssinclude=cssinclude,
        async_progress=async_progress,
        async_url=reverse('progress', args=[runinfo.random])
    )
    r['Cache-Control'] = 'no-cache'
    r['Expires'] = "Thu, 24 Jan 1980 00:00:00 GMT"
    return r

def substitute_answer(qvalues, obj):
    """Objects with a 'text/text_xx' attribute can contain magic strings
    referring to the answers of other questions. This function takes
    any such object, goes through the stored answers (qvalues) and replaces
    the magic string with the actual value. If this isn't possible the
    magic string is removed from the text.

    Only answers with 'store' in their check will work with this.

    """
        
    if qvalues:
        magic = 'subst_with_ans_'
        regex =r'subst_with_ans_(\S+)'

        replacements = re.findall(regex, obj.text)
        text_attributes = [a for a in dir(obj) if a.startswith('text_')]

        for answerid in replacements:
            
            target = magic + answerid
            replacement = qvalues.get(answerid.lower(), '')

            for attr in text_attributes:
                oldtext = getattr(obj, attr)
                newtext = oldtext.replace(target, replacement)
                
                setattr(obj, attr, newtext)


def set_language(request, runinfo=None, next=None):
    """
    Change the language, save it to runinfo if provided, and
    redirect to the provided URL (or the last URL).
    Can also be used by a url handler, w/o runinfo & next.
    """
    if not next:
        next = request.REQUEST.get('next', None)
    if not next:
        next = request.META.get('HTTP_REFERER', None)
        if not next:
            next = '/'
    response = HttpResponseRedirect(next)
    response['Expires'] = "Thu, 24 Jan 1980 00:00:00 GMT"
    if request.method == 'GET':
        lang_code = request.GET.get('lang', None)
        if lang_code and translation.check_for_language(lang_code):
            if hasattr(request, 'session'):
                request.session['django_language'] = lang_code
            else:
                response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code)
            if runinfo:
                runinfo.subject.language = lang_code
                runinfo.subject.save()
    return response


def _table_headers(questions):
    """
    Return the header labels for a set of questions as a list of strings.

    This will create separate columns for each multiple-choice possiblity
    and freeform options, to avoid mixing data types and make charting easier.
    """
    ql = list(questions.distinct('number'))
    ql.sort(lambda x, y: numal_sort(x.number, y.number))
    columns = []
    for q in ql:
        if q.type == 'choice-yesnocomment':
            columns.extend([q.number, q.number + "-freeform"])
        elif q.type == 'choice-freeform':
            columns.extend([q.number, q.number + "-freeform"])
        elif q.type.startswith('choice-multiple'):
            cl = [c.value for c in q.choice_set.all()]
            cl.sort(numal_sort)
            columns.extend([q.number + '-' + value for value in cl])
            if q.type == 'choice-multiple-freeform':
                columns.append(q.number + '-freeform')
        else:
            columns.append(q.number)
    return columns



@permission_required("questionnaire.export")
def export_csv(request, qid): # questionnaire_id
    """
    For a given questionnaire id, generaete a CSV containing all the
    answers for all subjects.
    """
    import tempfile, csv, cStringIO, codecs
    from django.core.servers.basehttp import FileWrapper

    class UnicodeWriter:
        """
        COPIED from http://docs.python.org/library/csv.html example:

        A CSV writer which will write rows to CSV file "f",
        which is encoded in the given encoding.
        """

        def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
            # Redirect output to a queue
            self.queue = cStringIO.StringIO()
            self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
            self.stream = f
            self.encoder = codecs.getincrementalencoder(encoding)()

        def writerow(self, row):
            self.writer.writerow([s.encode("utf-8") for s in row])
            # Fetch UTF-8 output from the queue ...
            data = self.queue.getvalue()
            data = data.decode("utf-8")
            # ... and reencode it into the target encoding
            data = self.encoder.encode(data)
            # write to the target stream
            self.stream.write(data)
            # empty queue
            self.queue.truncate(0)

        def writerows(self, rows):
            for row in rows:
                self.writerow(row)

    fd = tempfile.TemporaryFile()

    questionnaire = get_object_or_404(Questionnaire, pk=int(qid))
    headings, answers = answer_export(questionnaire)

    writer = UnicodeWriter(fd)
    writer.writerow([u'subject', u'runid'] + headings)
    for subject, runid, answer_row in answers:
        row = ["%s/%s" % (subject.id, subject.state), runid] + [
            a if a else '--' for a in answer_row]
        writer.writerow(row)

    response = HttpResponse(FileWrapper(fd), mimetype="text/csv")
    response['Content-Length'] = fd.tell()
    response['Content-Disposition'] = 'attachment; filename="export-%s.csv"' % qid
    fd.seek(0)
    return response

def answer_export(questionnaire, answers=None):
    """
    questionnaire -- questionnaire model for export
    answers -- query set of answers to include in export, defaults to all

    Return a flat dump of column headings and all the answers for a 
    questionnaire (in query set answers) in the form (headings, answers) 
    where headings is:
        ['question1 number', ...]
    and answers is:
        [(subject1, 'runid1', ['answer1.1', ...]), ... ]

    The headings list might include items with labels like 
    'questionnumber-freeform'.  Those columns will contain all the freeform
    answers for that question (separated from the other answer data).

    Multiple choice questions will have one column for each choice with
    labels like 'questionnumber-choice'.

    The items in the answers list are unicode strings or empty strings
    if no answer was given.  The number of elements in each answer list will
    always match the number of headings.    
    """
    if answers is None:
        answers = Answer.objects.all()
    answers = answers.filter(
        question__questionset__questionnaire=questionnaire).order_by(
        'subject', 'runid', 'question__questionset__sortid', 'question__number')
    answers = answers.select_related()
    questions = Question.objects.filter(
        questionset__questionnaire=questionnaire)
    headings = _table_headers(questions)

    coldict = {}
    for num, col in enumerate(headings): # use coldict to find column indexes
        coldict[col] = num
    # collect choices for each question
    qchoicedict = {}
    for q in questions:
        qchoicedict[q.id] = [x[0] for x in q.choice_set.values_list('value')]

    runid = subject = None
    out = []
    row = []
    for answer in answers:
        if answer.runid != runid or answer.subject != subject:
            if row: 
                out.append((subject, runid, row))
            runid = answer.runid
            subject = answer.subject
            row = [""] * len(headings)
        ans = answer.split_answer()
        if type(ans) == int:
            ans = str(ans) 
        for choice in ans:
            col = None
            if type(choice) == list:
                # freeform choice
                choice = choice[0]
                col = coldict.get(answer.question.number + '-freeform', None)
            if col is None: # look for enumerated choice column (multiple-choice)
                col = coldict.get(answer.question.number + '-' + choice, None)
            if col is None: # single-choice items
                if ((not qchoicedict[answer.question.id]) or
                    choice in qchoicedict[answer.question.id]):
                    col = coldict.get(answer.question.number, None)
            if col is None: # last ditch, if not found throw it in a freeform column
                col = coldict.get(answer.question.number + '-freeform', None)
            if col is not None:
                row[col] = choice
    # and don't forget about the last one
    if row: 
        out.append((subject, runid, row))
    return headings, out

def answer_summary(questionnaire, answers=None):
    """
    questionnaire -- questionnaire model for summary
    answers -- query set of answers to include in summary, defaults to all

    Return a summary of the answer totals in answer_qs in the form:
    [('q1', 'question1 text', 
        [('choice1', 'choice1 text', num), ...], 
        ['freeform1', ...]), ...]

    questions are returned in questionnaire order
    choices are returned in question order
    freeform options are case-insensitive sorted 
    """

    if answers is None:
        answers = Answer.objects.all()
    answers = answers.filter(question__questionset__questionnaire=questionnaire)
    questions = Question.objects.filter(
        questionset__questionnaire=questionnaire).order_by(
        'questionset__sortid', 'number')

    summary = []
    for question in questions:
        q_type = question.get_type()
        if q_type.startswith('choice-yesno'):
            choices = [('yes', _('Yes')), ('no', _('No'))]
            if 'dontknow' in q_type:
                choices.append(('dontknow', _("Don't Know")))
        elif q_type.startswith('choice'):
            choices = [(c.value, c.text) for c in question.choices()]
        else:
            choices = []
        choice_totals = dict([(k, 0) for k, v in choices])
        freeforms = []
        for a in answers.filter(question=question):
            ans = a.split_answer()
            for choice in ans:
                if type(choice) == list:
                    freeforms.extend(choice)
                elif choice in choice_totals:
                    choice_totals[choice] += 1
                else:
                    # be tolerant of improperly marked data
                    freeforms.append(choice)
        freeforms.sort(numal_sort)
        summary.append((question.number, question.text, [
            (n, t, choice_totals[n]) for (n, t) in choices], freeforms))
    return summary
    
def has_tag(tag, runinfo):
    """ Returns true if the given runinfo contains the given tag. """
    return tag in (t.strip() for t in runinfo.tags.split(','))

def dep_check(expr, runinfo, answerdict):
    """
    Given a comma separated question number and expression, determine if the
    provided answer to the question number satisfies the expression.

    If the expression starts with >, >=, <, or <=, compare the rest of
    the expression numerically and return False if it's not able to be
    converted to an integer.

    If the expression starts with !, return true if the rest of the expression
    does not match the answer.

    Otherwise return true if the expression matches the answer.

    If there is no comma and only a question number, it checks if the answer
    is "yes"

    When looking up the answer, it first checks if it's in the answerdict,
    then it checks runinfo's cookies, then it does a database lookup to find
    the answer.
    
    The use of the comma separator is purely historical.
    """

    if hasattr(runinfo, 'questionset'):
        questionnaire = runinfo.questionset.questionnaire
    elif hasattr(runinfo, 'questionnaire'):
        questionnaire = runinfo.questionnaire
    else:
        assert False

    if "," not in expr:
        expr = expr + ",yes"

    check_questionnum, check_answer = expr.split(",",1)
    try:
        check_question = Question.objects.get(number=check_questionnum,
          questionset__questionnaire = questionnaire)
    except Question.DoesNotExist:
        return False

    if check_question in answerdict:
        # test for membership in multiple choice questions
        # FIXME: only checking answerdict
        for k, v in answerdict[check_question].items():
            if not k.startswith('multiple_'):
                continue
            if check_answer.startswith("!"):
                if check_answer[1:].strip() == v.strip():
                    return False
            elif check_answer.strip() == v.strip():
                return True
        actual_answer = answerdict[check_question].get('ANSWER', '')
    elif hasattr(runinfo, 'get_cookie') and runinfo.get_cookie(check_questionnum, False):
        actual_answer = runinfo.get_cookie(check_questionnum)
    else:
        # retrieve from database
        ansobj = Answer.objects.filter(question=check_question,
            runid=runinfo.runid, subject=runinfo.subject)
        if ansobj:
            actual_answer = ansobj[0].split_answer()[0]
            logging.warn("Put `store` in checks field for question %s" \
            % check_questionnum)
        else:
            actual_answer = None

    if not actual_answer:
        if check_question.getcheckdict():
            actual_answer = check_question.getcheckdict().get('default')
    
    if actual_answer is None:
        actual_answer = u''
    if check_answer[0:1] in "<>":
        try:
            actual_answer = float(actual_answer)
            if check_answer[1:2] == "=":
                check_value = float(check_answer[2:])
            else:
                check_value = float(check_answer[1:])
        except:
            logging.error("ERROR: must use numeric values with < <= => > checks (%r)" % check_question)
            return False
        if check_answer.startswith("<="):
            return actual_answer <= check_value
        if check_answer.startswith(">="):
            return actual_answer >= check_value
        if check_answer.startswith("<"):
            return actual_answer < check_value
        if check_answer.startswith(">"):
            return actual_answer > check_value
    if check_answer.startswith("!"):
        return check_answer[1:].strip() != actual_answer.strip()
    return check_answer.strip() == actual_answer.strip()

@permission_required("questionnaire.management")
def send_email(request, runinfo_id):
    if request.method != "POST":
        return HttpResponse("This page MUST be called as a POST request.")
    runinfo = get_object_or_404(RunInfo, pk=int(runinfo_id))
    successful = _send_email(runinfo)
    return r2r("emailsent.html", request, runinfo=runinfo, successful=successful)


def generate_run(request, questionnaire_id):
    """
    A view that can generate a RunID instance anonymously,
    and then redirect to the questionnaire itself.

    It uses a Subject with the givenname of 'Anonymous' and the
    surname of 'User'.  If this Subject does not exist, it will
    be created.

    This can be used with a URL pattern like:
    (r'^take/(?P<questionnaire_id>[0-9]+)/$', 'questionnaire.views.generate_run'),
    """
    qu = get_object_or_404(Questionnaire, id=questionnaire_id)
    qs = qu.questionsets()[0]
    su = Subject.objects.filter(givenname='Anonymous', surname='User')[0:1]
    if su:
        su = su[0]
    else:
        su = Subject(givenname='Anonymous', surname='User')
        su.save()
    hash = md5.new()
    hash.update("".join(map(lambda i: chr(random.randint(0, 255)), range(16))))
    hash.update(settings.SECRET_KEY)
    key = hash.hexdigest()
    run = RunInfo(subject=su, random=key, runid=key, questionset=qs)
    run.save()
    return HttpResponseRedirect(reverse('questionnaire', kwargs={'runcode': key}))


########NEW FILE########
