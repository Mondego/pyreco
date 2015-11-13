__FILENAME__ = admin
from django.contrib import admin
from taxonomy.models import Taxonomy, TaxonomyTerm, TaxonomyMap

class TaxonomyAdmin(admin.ModelAdmin):
   pass

class TaxonomyTermAdmin(admin.ModelAdmin):
   pass

class TaxonomyMapAdmin(admin.ModelAdmin):
   pass


admin.site.register(Taxonomy, TaxonomyAdmin)
admin.site.register(TaxonomyTerm, TaxonomyTermAdmin)
admin.site.register(TaxonomyMap, TaxonomyMapAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

###
### Managers
###
class TaxonomyManager(models.Manager):
   def get_for_object(self, obj):
      """
      Get all taxonomy type-term pairings for an instance of a content object.
      """
      ctype = ContentType.objects.get_for_model(obj)
      return self.filter(content_type__pk=ctype.pk,
                         object_id=obj.pk)


###
### Models 
###

class Taxonomy(models.Model):
   """A facility for creating custom content classification types""" 
   type = models.CharField(max_length=50, unique=True)

   class Meta:
      verbose_name = "taxonomy"  
      verbose_name_plural = "taxonomies"

   def __unicode__(self): 
      return self.type

class TaxonomyTerm(models.Model):
   """Terms are associated with a specific Taxonomy, and should be generically usable with any contenttype"""
   type = models.ForeignKey(Taxonomy)
   term = models.CharField(max_length=50)
   parent = models.ForeignKey('self', null=True,blank=True)

   class Meta:
      unique_together = ('type', 'term')

   def __unicode__(self):
      return self.term

class TaxonomyMap(models.Model):
   """Mappings between content and any taxonomy types/terms used to classify it"""
   term        = models.ForeignKey(TaxonomyTerm, db_index=True)
   type        = models.ForeignKey(Taxonomy, db_index=True)
   content_type = models.ForeignKey(ContentType, verbose_name='content type', db_index=True)
   object_id      = models.PositiveIntegerField(db_index=True)   
   object         = generic.GenericForeignKey('content_type', 'object_id')

   objects = TaxonomyManager()

   class Meta:
      unique_together = ('term', 'type', 'content_type', 'object_id')

   def __unicode__(self):
      return u'%s [%s]' % (self.term, self.type)



########NEW FILE########
__FILENAME__ = taxonomy_tags
from django.db.models import get_model
from django.template import Library, Node, TemplateSyntaxError, Variable, resolve_variable

from taxonomy.models import TaxonomyMap

register = Library()

class TaxonomyForObjectNode(Node):
    def __init__(self, obj, context_var):
        self.obj = Variable(obj)
        self.context_var = context_var

    def render(self, context):
        context[self.context_var] = \
            TaxonomyMap.objects.get_for_object(self.obj.resolve(context))
        return ''

def do_taxonomy_for_object(parser, token):
    """
    Retrieves a list of ``TaxonomyMap`` objects and stores them in a context variable.

    Usage::

       {% taxonomy_for_object [object] as [varname] %}

    Example::

        {% taxonomy_for_object foo_object as taxonomy_list %}
    """
    bits = token.contents.split()
    if len(bits) != 4:
        raise TemplateSyntaxError(('%s taxonomy requires exactly three arguments') % bits[0])
    if bits[2] != 'as':
        raise TemplateSyntaxError(("second argument to %s taxonomy must be 'as'") % bits[0])
    return TaxonomyForObjectNode(bits[1], bits[3])

register.tag('taxonomy_for_object', do_taxonomy_for_object)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
