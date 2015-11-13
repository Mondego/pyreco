__FILENAME__ = abs
from django.template import TemplateDoesNotExist
from ab.models import Experiment, Test


# @@@ The interface to this is shazbot. Rethink is in order.
class AB(object):
    """
    Uses request session to track Experiment state.
        - Whether an Experiment/Test is active
        - Whether an Experiment/Test has been converted   
    """

    def __init__(self, request):
        self.request = request

    def is_active(self):
        """True if at least one Experiment is running on this request."""
        return "ab_active" in self.request.session
        
    def is_converted(self, exp):
        """
        True if request location is the Goal of Experiment and this request
        hasn't already been converted.
        """
        return self.is_experiment_active(exp) and not self.is_experiment_converted(exp) \
            and exp.goal in self.request.path
        
    def is_experiment_active(self, exp):
        """True if this Experiment is active."""
        return self.get_experiment_key(exp) in self.request.session
        
    def is_experiment_converted(self, exp):
        """True if this Experiment has been converted."""
        return "converted" in self.request.session[self.get_experiment_key(exp)]
    
    def get_test(self, exp):
        """Returns a random Test for this Experiment"""
        tests = exp.test_set.all()
        return tests[self.request.session.session_key.__hash__() % len(tests)]

    def get_experiment_key(self, exp):
        return "ab_exp_%s" % exp.name

    def get_experiment(self, template_name):
        try:
            return Experiment.objects.get(template_name=template_name)
        except Experiment.DoesNotExist:
            raise TemplateDoesNotExist, template_name
        
    def run(self, template_name):
        """
        Searches for an Experiment running on template_name. If none are found
        raises a TemplateDoesNotExist otherwise activates a Test for that
        Experiment unless one is already running and returns the Test 
        template_name.
        """
        exp = self.get_experiment(template_name)

        # If this Experiment is active, return the template to show.
        key = self.get_experiment_key(exp)
        if self.is_experiment_active(exp):
            return self.request.session[key]["template"]

        # Otherwise Experiment isn't active so start one of its Tests.
        test = self.get_test(exp)
        self.activate(test, key)

        return test.template_name

    def activate(self, test, key):
        # Record this hit.
        test.hits = test.hits + 1
        test.save()

        # Activate this experiment/test on the request.
        self.request.session[key] = {"id": test.id, "template": test.template_name}
        
        # Mark that there is at least one A/B test running.
        self.request.session["ab_active"] = True
        
    def convert(self, exp):
        """Update the test active on the request for this experiment."""
        key = self.get_experiment_key(exp)
        test_id = self.request.session[key]["id"]
        test = Test.objects.get(pk=test_id)
        test.conversions = test.conversions + 1
        test.save()
        
        self.request.session[key]["converted"] = 1
        self.request.session.modified = True
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from ab.models import Experiment, Test


class TestInline(admin.TabularInline):
    model = Test

class ExperimentAdmin(admin.ModelAdmin):
    inlines = (TestInline,)
    
admin.site.register(Experiment, ExperimentAdmin)

########NEW FILE########
__FILENAME__ = loaders
from django.template.loaders.filesystem import load_template_source as default_template_loader
from ab.middleware import get_current_request


def load_template_source(template_name, template_dirs=None, 
    template_loader=default_template_loader):
    """If an Experiment exists for this template use template_loader to load it."""    
    request = get_current_request()
    test_template_name = request.ab.run(template_name)

    return template_loader(test_template_name, template_dirs=template_dirs)
load_template_source.is_usable = True
        
        
########NEW FILE########
__FILENAME__ = middleware
try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

from ab.abs import AB
from ab.models import Experiment


_thread_locals = local()
def get_current_request():
    return getattr(_thread_locals, 'request', None)


# @@@ This won't work with caching. Need to create an AB aware cache middleware.
class ABMiddleware:
    def process_request(self, request):
        """
        Puts the request object in local thread storage so we can access it in
        the template loader. If an Experiment is active then check whether we've
        reached it's goal.
        """
        _thread_locals.request = request
        
        request.ab = AB(request)
        # request.ab.run()
        # If at least one Experiment is running then check if we're at a Goal
        # @@@ All this logic seems like it could be moved into the AB class. (but does it belong there?)
        if request.ab.is_active():
            exps = Experiment.objects.all()
            for exp in exps:
                if request.ab.is_converted(exp):
                    request.ab.convert(exp)
########NEW FILE########
__FILENAME__ = models
from django.db import models


class Experiment(models.Model):
    """
    
    """
    # @@@ unique=True ??? Does that make sense???
    name = models.CharField(max_length=255, unique=True)
    template_name = models.CharField(max_length=255, unique=True,
        help_text="Example: 'registration/signup.html'. The template to replaced.")
    goal = models.CharField(max_length=255, unique=True,
        help_text="Example: '/signup/complete/'. The path where the goal is converted.")
    
    def __unicode__(self):
        return self.name
    

class Test(models.Model):
    """
    
    """
    experiment = models.ForeignKey(Experiment)
    template_name = models.CharField(max_length=255,
        help_text="Example: 'registration/signup_1.html'. The template to be tested.")
    hits = models.IntegerField(blank=True, default=0, 
        help_text="# uniques that have seen this test.")
    conversions = models.IntegerField(blank=True, default=0,
        help_text="# uniques that have reached the goal from this test.")
    
    def __unicode__(self):
        return self.template_name
########NEW FILE########
__FILENAME__ = tests
import os
 
from django.conf import settings
from django.test import TestCase

from ab.models import Test, Experiment


class ABTests(TestCase):
    urls = "ab.tests.test_urls"
    fixtures = ["test_data"]
    template_dirs = [
        os.path.join(os.path.dirname(__file__), 'templates'),
    ]
    
    def setUp(self):
        self.old_template_dir = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = self.template_dirs    
        
    def tearDown(self):
        settings.TEMPLATE_DIRS = self.old_template_dir
        
    def test_ab(self):
        # Careful here, response.template doesn't know where we are.
    
        # It always looks like we loaded the original.
        response = self.client.get("/test/")        
        self.assertTrue(response.template.name, "original.html")

        # But we really just loaded one of the tests (template_name is the response content)
        test = Test.objects.get(template_name=response.content)
        test_id = test.id
        self.assertEquals(test.hits, 1)
        self.assertEquals(test.conversions, 0)

        # Tests are sticky.
        for _ in range(9):
            responsex = self.client.get("/test/")        
        self.assertEquals(response.content, responsex.content)

        # @@@ Do we need to keep querying to make sure this is up to date?

        # Only one hit per unique view.
        test = Test.objects.get(pk=test_id)
        self.assertEquals(test.hits, 1)

        # Going to another page doesn't effect anything.
        response = self.client.get("/other/")
        test = Test.objects.get(pk=test_id)
        self.assertEquals(response.template.name, response.content)      
        self.assertEquals(test.hits, 1)
        self.assertEquals(test.conversions, 0)
        
        # Going to the goal results in a conversion.
        response = self.client.get("/goal/")
        test = Test.objects.get(pk=test_id)        
        self.assertEquals(response.template.name, response.content)      
        self.assertEquals(test.hits, 1)
        self.assertEquals(test.conversions, 1)
        
        
        

########NEW FILE########
__FILENAME__ = test_urls
from django.conf.urls.defaults import *


urlpatterns = patterns('django.views.generic.simple',
    (r'^test/$', 'direct_to_template', {'template': 'original.html'}),
    (r'^other/$', 'direct_to_template', {'template': 'other.html'}),
    (r'^goal/$', 'direct_to_template', {'template': 'goal.html'}),
)
########NEW FILE########
