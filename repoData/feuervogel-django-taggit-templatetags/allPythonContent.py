__FILENAME__ = runtests
#!/usr/bin/env python

import sys
from os.path import dirname, abspath
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASE_ENGINE='sqlite3',
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'taggit',
            'taggit_templatetags',
            'taggit_templatetags.tests'            
        ]
    )

from django.test.simple import run_tests

def runtests(*test_args):
    if not test_args:
        test_args = ['tests']
    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)
    failures = run_tests(test_args, verbosity=1, interactive=True)
    sys.exit(failures)

if __name__ == '__main__':
    runtests(*sys.argv[1:])
########NEW FILE########
__FILENAME__ = models
# no models in here
from django.db import models

class AModel(models.Model):
    name = models.CharField(max_length=50)
########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

# define the minimal weight of a tag in the tagcloud
TAGCLOUD_MIN = getattr(settings, 'TAGGIT_TAGCLOUD_MIN', 1.0)

# define the maximum weight of a tag in the tagcloud 
TAGCLOUD_MAX = getattr(settings, 'TAGGIT_TAGCLOUD_MAX', 6.0) 
########NEW FILE########
__FILENAME__ = taggit_extras
from django import template
from django.db import models
from django.db.models import Count
from django.core.exceptions import FieldError

from templatetag_sugar.register import tag
from templatetag_sugar.parser import Name, Variable, Constant, Optional, Model

from taggit import VERSION as TAGGIT_VERSION
from taggit.managers import TaggableManager
from taggit.models import TaggedItem, Tag
from taggit_templatetags import settings

T_MAX = getattr(settings, 'TAGCLOUD_MAX', 6.0)
T_MIN = getattr(settings, 'TAGCLOUD_MIN', 1.0)

register = template.Library()

def get_queryset(forvar=None):
    if None == forvar:
        # get all tags
        queryset = Tag.objects.all()
    else:
        # extract app label and model name
        beginning, applabel, model = None, None, None
        try:
            beginning, applabel, model = forvar.rsplit('.', 2)
        except ValueError:
            try:
                applabel, model = forvar.rsplit('.', 1)
            except ValueError:
                applabel = forvar
        
        # filter tagged items        
        if applabel:
            queryset = TaggedItem.objects.filter(content_type__app_label=applabel.lower())
        if model:
            queryset = queryset.filter(content_type__model=model.lower())
            
        # get tags
        tag_ids = queryset.values_list('tag_id', flat=True)
        queryset = Tag.objects.filter(id__in=tag_ids)

    # Retain compatibility with older versions of Django taggit
    # a version check (for example taggit.VERSION <= (0,8,0)) does NOT
    # work because of the version (0,8,0) of the current dev version of django-taggit
    try:
        return queryset.annotate(num_times=Count('taggeditem_items'))
    except FieldError:
        return queryset.annotate(num_times=Count('taggit_taggeditem_items'))

def get_weight_fun(t_min, t_max, f_min, f_max):
    def weight_fun(f_i, t_min=t_min, t_max=t_max, f_min=f_min, f_max=f_max):
        # Prevent a division by zero here, found to occur under some
        # pathological but nevertheless actually occurring circumstances.
        if f_max == f_min:
            mult_fac = 1.0
        else:
            mult_fac = float(t_max-t_min)/float(f_max-f_min)
            
        return t_max - (f_max-f_i)*mult_fac
    return weight_fun

@tag(register, [Constant('as'), Name(), Optional([Constant('for'), Variable()])])
def get_taglist(context, asvar, forvar=None):
    queryset = get_queryset(forvar)         
    queryset = queryset.order_by('-num_times')        
    context[asvar] = queryset
    return ''

@tag(register, [Constant('as'), Name(), Optional([Constant('for'), Variable()])])
def get_tagcloud(context, asvar, forvar=None):
    queryset = get_queryset(forvar)
    num_times = queryset.values_list('num_times', flat=True)
    if(len(num_times) == 0):
        context[asvar] = queryset
        return ''
    weight_fun = get_weight_fun(T_MIN, T_MAX, min(num_times), max(num_times))
    queryset = queryset.order_by('name')
    for tag in queryset:
        tag.weight = weight_fun(tag.num_times)
    context[asvar] = queryset
    return ''
    
def include_tagcloud(forvar=None):
    return {'forvar': forvar}

def include_taglist(forvar=None):
    return {'forvar': forvar}
  
register.inclusion_tag('taggit_templatetags/taglist_include.html')(include_taglist)
register.inclusion_tag('taggit_templatetags/tagcloud_include.html')(include_tagcloud)

########NEW FILE########
__FILENAME__ = models
from django.db import models

from taggit.managers import TaggableManager

class BaseModel(models.Model):
    name = models.CharField(max_length=50, unique=True)
    tags = TaggableManager()
    
    def __unicode__(self):
        return self.name
    
    class Meta(object):
        abstract = True 

class AlphaModel(BaseModel):
    pass

class BetaModel(BaseModel):
    pass

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.template import Context, Template
from django.template.loader import get_template

from taggit_templatetags.tests.models import AlphaModel, BetaModel
from taggit.tests.tests import BaseTaggingTest

from taggit_templatetags.templatetags.taggit_extras import get_weight_fun

class SetUpTestCase():
    a_model = AlphaModel
    b_model = BetaModel
    
    def setUp(self):
        a1 = self.a_model.objects.create(name="apple")
        a2 = self.a_model.objects.create(name="pear")
        b1 = self.b_model.objects.create(name="dog")
        b2 = self.b_model.objects.create(name="kitty")
        
        a1.tags.add("green")
        a1.tags.add("sweet")
        a1.tags.add("fresh")
        
        a2.tags.add("yellow")
        a2.tags.add("sour")
        
        b1.tags.add("sweet")
        b1.tags.add("yellow")
        
        b2.tags.add("sweet")
        b2.tags.add("green")
        

class TestWeightFun(TestCase):
    def test_one(self):
        t_min = 1
        t_max = 6
        f_min = 10
        f_max = 20
        weight_fun = get_weight_fun(t_min, t_max, f_min, f_max)
        self.assertEqual(weight_fun(20), 6)
        self.assertEqual(weight_fun(10), 1)
        self.assertEqual(weight_fun(15), 3.5)
    
    def test_two(self):
        t_min = 10
        t_max = 100
        f_min = 5
        f_max = 7
        weight_fun = get_weight_fun(t_min, t_max, f_min, f_max)
        self.assertEqual(weight_fun(5), 10)
        self.assertEqual(weight_fun(7), 100)
        self.assertEqual(weight_fun(6), 55)


class TemplateTagListTestCase(SetUpTestCase, BaseTaggingTest, TestCase):    
    def get_template(self, argument):
        return """      {%% load taggit_extras %%}
                        {%% get_taglist %s %%}
                """ % argument
                
    def test_project(self):
        t = Template(self.get_template("as taglist"))
        c = Context({})
        t.render(c)
        self.assert_tags_equal(c.get("taglist"), ["sweet", "green", "yellow", "fresh", "sour"], False)
        
    def test_app(self):
        t = Template(self.get_template("as taglist for 'tests'"))
        c = Context({})
        t.render(c)
        self.assert_tags_equal(c.get("taglist"), ["sweet", "green", "yellow", "fresh", "sour"], False)
        
    def test_model(self):
        t = Template(self.get_template("as taglist for 'tests.BetaModel'"))
        c = Context({})
        t.render(c)
        self.assert_tags_equal(c.get("taglist"), ["sweet", "green", "yellow"], False)

class TemplateTagCloudTestCase(SetUpTestCase, BaseTaggingTest, TestCase):
    def get_template(self, argument):
        return """      {%% load taggit_extras %%}
                        {%% get_tagcloud %s %%}
                """ % argument
                
    def test_project(self):
        t = Template(self.get_template("as taglist"))
        c = Context({})
        t.render(c)
        self.assert_tags_equal(c.get("taglist"), ["fresh", "green", "sour", "sweet", "yellow"], False)
        self.assertEqual(c.get("taglist")[3].name, "sweet")
        self.assertEqual(c.get("taglist")[3].weight, 6.0)
        self.assertEqual(c.get("taglist")[1].name, "green")
        self.assertEqual(c.get("taglist")[1].weight, 3.5)
        self.assertEqual(c.get("taglist")[2].name, "sour")
        self.assertEqual(c.get("taglist")[2].weight, 1.0)
                
    def test_app(self):
        t = Template(self.get_template("as taglist for 'tests'"))
        c = Context({})
        t.render(c)
        self.assert_tags_equal(c.get("taglist"), ["fresh", "green", "sour", "sweet", "yellow"], False)
        self.assertEqual(c.get("taglist")[3].name, "sweet")
        self.assertEqual(c.get("taglist")[3].weight, 6.0)
        self.assertEqual(c.get("taglist")[1].name, "green")
        self.assertEqual(c.get("taglist")[1].weight, 3.5)
        self.assertEqual(c.get("taglist")[2].name, "sour")
        self.assertEqual(c.get("taglist")[2].weight, 1.0)  
        
    def test_model(self):
        t = Template(self.get_template("as taglist for 'tests.BetaModel'"))
        c = Context({})
        t.render(c)
        self.assert_tags_equal(c.get("taglist"), ["green", "sweet", "yellow"], False)
        self.assertEqual(c.get("taglist")[0].name, "green")
        self.assertEqual(c.get("taglist")[0].weight, 1.0)
        self.assertEqual(c.get("taglist")[1].name, "sweet")
        self.assertEqual(c.get("taglist")[1].weight, 6.0)
        self.assertEqual(c.get("taglist")[2].name, "yellow")
        self.assertEqual(c.get("taglist")[2].weight, 1.0)
        
class TemplateInclusionTagTest(SetUpTestCase, TestCase, BaseTaggingTest):    
    def test_taglist_project(self):
        t = get_template('taggit_templatetags/taglist_include.html')
        c = Context({'forvar': None})
        t.render(c)
        self.assert_tags_equal(c.get("tags"), ["sweet", "green", "yellow", "fresh", "sour"], False)
                
    def test_taglist_app(self):
        t = get_template('taggit_templatetags/taglist_include.html')
        c = Context({'forvar': 'tests'})
        t.render(c)
        self.assert_tags_equal(c.get("tags"), ["sweet", "green", "yellow", "fresh", "sour"], False)
            
    def test_taglist_model(self):
        t = get_template('taggit_templatetags/taglist_include.html')
        c = Context({'forvar': 'tests.BetaModel'})
        t.render(c)
        self.assert_tags_equal(c.get("tags"), ["sweet", "green", "yellow"], False)
        
    def test_tagcloud_project(self):
        t = get_template('taggit_templatetags/tagcloud_include.html')
        c = Context({'forvar': None})
        t.render(c)
        self.assert_tags_equal(c.get("tags"), ["fresh", "green", "sour", "sweet", "yellow"], False)
    
    def test_tagcloud_app(self):
        t = get_template('taggit_templatetags/tagcloud_include.html')
        c = Context({'forvar': 'tests'})
        t.render(c)
        self.assert_tags_equal(c.get("tags"), ["fresh", "green", "sour", "sweet", "yellow"], False)
    
    def test_tagcloud_model(self):
        t = get_template('taggit_templatetags/tagcloud_include.html')
        c = Context({'forvar': 'tests.BetaModel'})
        t.render(c)
        self.assert_tags_equal(c.get("tags"), ["green", "sweet", "yellow"], False)
        
        
class AlphaPathologicalCaseTestCase(TestCase, BaseTaggingTest):
    """
    This is a testcase for one tag once.
    """
    a_model = AlphaModel
    def setUp(self):
        a1 = self.a_model.objects.create(name="apple")
        a1.tags.add("green")
        
    def test_tagcloud(self):
        t = get_template('taggit_templatetags/tagcloud_include.html')
        c = Context({'forvar': None})
        t.render(c)
        self.assert_tags_equal(c.get("tags"), ["green"], False)
        self.assertEqual(c.get("tags")[0].name, "green")
        self.assertEqual(c.get("tags")[0].weight, 6.0)  
        
class BetaPathologicalCaseTestCase(TestCase, BaseTaggingTest):
    """
    This is a testcase for one tag thrice.
    """
    a_model = AlphaModel
    b_model = BetaModel
    
    def setUp(self):
        a1 = self.a_model.objects.create(name="apple")
        a2 = self.a_model.objects.create(name="pear")
        b1 = self.b_model.objects.create(name="dog")
        a1.tags.add("green")
        a2.tags.add("green")
        b1.tags.add("green")
        
    def test_tagcloud(self):
        t = get_template('taggit_templatetags/tagcloud_include.html')
        c = Context({'forvar': None})
        t.render(c)
        self.assert_tags_equal(c.get("tags"), ["green"], False)
        self.assertEqual(c.get("tags")[0].name, "green")
        self.assertEqual(c.get("tags")[0].weight, 6.0)  
        
class GammaPathologicalCaseTestCase(TestCase, BaseTaggingTest):
    """
    This is a pathological testcase for no tag at all.
    """
    a_model = AlphaModel
    b_model = BetaModel
    
    def setUp(self):
        a1 = self.a_model.objects.create(name="apple")
        b1 = self.b_model.objects.create(name="dog")
        
    def test_tagcloud(self):
        t = get_template('taggit_templatetags/tagcloud_include.html')
        c = Context({'forvar': None})
        t.render(c)
        self.assert_tags_equal(c.get("tags"), [], False)
        
########NEW FILE########
