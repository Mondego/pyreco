__FILENAME__ = models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.db import models

from positions.fields import PositionField


class GenericThing(models.Model):
    name = models.CharField(max_length=80)
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType)
    content_object = generic.GenericForeignKey()
    position = PositionField(collection=('object_id', 'content_type'))

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = tests
import doctest
import unittest

from django.contrib.contenttypes.models import ContentType

from positions.examples.lists.models import List
from positions.examples.generic.models import GenericThing

tests = """
>>> l = List.objects.create(name='To Do')
>>> ct = ContentType.objects.get_for_model(l)
>>> t1 = GenericThing.objects.create(name="First Generic Thing",
...                                  object_id=l.pk,
...                                  content_type=ct)

>>> t2 = GenericThing.objects.create(name="Second Generic Thing",
...                                  object_id=l.pk,
...                                  content_type=ct)
>>> t1.position
0
>>> t2.position
1
>>> t1.position = 1
>>> t1.save()

>>> t1.position
1
>>> t2 = GenericThing.objects.get(pk=2)
>>> t2.position
0
>>> t1.delete()

>>> GenericThing.objects.filter(object_id=l.pk, content_type=ct).values_list('name', 'position').order_by('position')
[(u'Second Generic Thing', 0)]
>>> t3 = GenericThing.objects.create(object_id=l.pk, content_type=ct, name='Mr. None')
>>> t3.save()
>>> t3.position
1
>>> t4 = GenericThing.objects.create(object_id=l.pk, content_type=ct, name='Mrs. None')
>>> t4.position
2
>>> t4.position = -2
>>> t4.save()
>>> t4.position
1
>>> GenericThing.objects.order_by('position').values_list('name', flat=True)
[u'Second Generic Thing', u'Mrs. None', u'Mr. None']
"""


__test__ = {'tests': tests}


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite())
    return tests

########NEW FILE########
__FILENAME__ = models
from django.db import models

from positions.fields import PositionField


class List(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name


class Item(models.Model):
    list = models.ForeignKey('list', related_name='items', db_index=True)
    name = models.CharField(max_length=50)
    position = PositionField(collection='list')
    updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = tests
import doctest
import unittest

from positions.examples.lists.models import List, Item


tests = """
>>> l = List.objects.create(name='To Do')


# create a couple items using the default position

>>> l.items.create(name='Write Tests')
<Item: Write Tests>

>>> l.items.values_list('name', 'position')
[(u'Write Tests', 0)]

>>> l.items.create(name='Excersize')
<Item: Excersize>

>>> l.items.values_list('name', 'position').order_by('position')
[(u'Write Tests', 0), (u'Excersize', 1)]


# create an item with an explicit position

>>> l.items.create(name='Learn to spell Exercise', position=0)
<Item: Learn to spell Exercise>

>>> l.items.values_list('name', 'position').order_by('position')
[(u'Learn to spell Exercise', 0), (u'Write Tests', 1), (u'Excersize', 2)]


# save an item without changing it's position

>>> excersize = l.items.order_by('-position')[0]
>>> excersize.name = 'Exercise'
>>> excersize.save()

>>> l.items.values_list('name', 'position').order_by('position')
[(u'Learn to spell Exercise', 0), (u'Write Tests', 1), (u'Exercise', 2)]


# delete an item

>>> learn_to_spell = l.items.order_by('position')[0]
>>> learn_to_spell.delete()

>>> l.items.values_list('name', 'position').order_by('position')
[(u'Write Tests', 0), (u'Exercise', 1)]


# create a couple more items

>>> l.items.create(name='Drink less Coke')
<Item: Drink less Coke>

>>> l.items.create(name='Go to Bed')
<Item: Go to Bed>

>>> l.items.values_list('name', 'position').order_by('position')
[(u'Write Tests', 0), (u'Exercise', 1), (u'Drink less Coke', 2), (u'Go to Bed', 3)]


# move item to end using None

>>> write_tests = l.items.order_by('position')[0]
>>> write_tests.position = None
>>> write_tests.save()

>>> l.items.values_list('name', 'position').order_by('position')
[(u'Exercise', 0), (u'Drink less Coke', 1), (u'Go to Bed', 2), (u'Write Tests', 3)]


# move item using negative index

>>> write_tests.position = -3
>>> write_tests.save()

>>> l.items.values_list('name', 'position').order_by('position')
[(u'Exercise', 0), (u'Write Tests', 1), (u'Drink less Coke', 2), (u'Go to Bed', 3)]


# move item to position

>>> write_tests.position = 2
>>> write_tests.save()

>>> l.items.values_list('name', 'position').order_by('position')
[(u'Exercise', 0), (u'Drink less Coke', 1), (u'Write Tests', 2), (u'Go to Bed', 3)]


# move item to beginning

>>> sleep = l.items.order_by('-position')[0]
>>> sleep.position = 0
>>> sleep.save()

>>> l.items.values_list('name', 'position').order_by('position')
[(u'Go to Bed', 0), (u'Exercise', 1), (u'Drink less Coke', 2), (u'Write Tests', 3)]


# check auto_now updates

>>> sleep_updated, excersize_updated, eat_better_updated, write_tests_updated = [i.updated for i in l.items.order_by('position')]
>>> eat_better = l.items.order_by('-position')[1]
>>> eat_better.position = 1
>>> eat_better.save()
>>> todo_list = list(l.items.order_by('position'))

>>> sleep_updated == todo_list[0].updated
True

>>> eat_better_updated < todo_list[1].updated
True

>>> excersize_updated < todo_list[2].updated
True

>>> write_tests_updated == excersize_updated
True


# create an item using negative index
# http://github.com/jpwatts/django-positions/issues/#issue/5

>>> l.items.values_list('name', 'position').order_by('position')
[(u'Go to Bed', 0), (u'Drink less Coke', 1), (u'Exercise', 2), (u'Write Tests', 3)]

>>> fix_issue_5 = Item(list=l, name="Fix Issue #5")
>>> fix_issue_5.position
-1

>>> fix_issue_5.position = -2
>>> fix_issue_5.position
-2

>>> fix_issue_5.save()
>>> fix_issue_5.position
3

>>> l.items.values_list('name', 'position').order_by('position')
[(u'Go to Bed', 0), (u'Drink less Coke', 1), (u'Exercise', 2), (u'Fix Issue #5', 3), (u'Write Tests', 4)]

# Try again, now that the model has been saved.
>>> fix_issue_5.position = -2
>>> fix_issue_5.save()
>>> fix_issue_5.position
3

>>> l.items.values_list('name', 'position').order_by('position')
[(u'Go to Bed', 0), (u'Drink less Coke', 1), (u'Exercise', 2), (u'Fix Issue #5', 3), (u'Write Tests', 4)]


# create an item using with a position of zero
http://github.com/jpwatts/django-positions/issues#issue/7

>>> item0 = l.items.create(name="Fix Issue #7", position=0)
>>> item0.position
0

>>> l.items.values_list('name', 'position').order_by('position')
[(u'Fix Issue #7', 0), (u'Go to Bed', 1), (u'Drink less Coke', 2), (u'Exercise', 3), (u'Fix Issue #5', 4), (u'Write Tests', 5)]

"""


__test__ = {'tests': tests}


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite())
    return tests

########NEW FILE########
__FILENAME__ = models
from django.db import models
from positions.fields import PositionField

class Node(models.Model):
    parent = models.ForeignKey('self', related_name='children', blank=True, null=True)
    name = models.CharField(max_length=50)
    position = PositionField(collection='parent')

    def __unicode__(self):
       return self.name

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from positions.examples.nodes.models import Node
import doctest
import os
import unittest


class NodesTestCase(TestCase):
    def setUp(self):
        """
        Creates a simple tree::

            parent1
                child2
                child1
                child3
            parent2
                child4
                child5
                child6
        """
        self.parent1 = Node.objects.create(name='Parent 1')
        self.parent2 = Node.objects.create(name='Parent 2')
        self.child1 = self.parent1.children.create(name='Child 1')
        self.child2 = self.parent1.children.create(name='Child 2')
        self.child3 = self.parent1.children.create(name='Child 3')
        self.child2.position = 0
        self.child2.save()
        self.child1 = Node.objects.get(pk=self.child1.pk)
        self.child2 = Node.objects.get(pk=self.child2.pk)
        self.child3 = Node.objects.get(pk=self.child3.pk)

        self.child4 = self.parent2.children.create(name='Child 4')
        self.child5 = self.parent2.children.create(name='Child 5')
        self.child6 = self.parent2.children.create(name='Child 6')

    def tearDown(self):
        Node.objects.all().delete()

    def test_structure(self):
        """
        Tests the tree structure
        """
        tree = list(Node.objects.order_by('parent__position', 'position').values_list('name', 'position'))
        self.assertEqual(tree, [(u'Parent 1', 0), (u'Parent 2', 1), (u'Child 2', 0), (u'Child 1', 1), (u'Child 3', 2), (u'Child 4', 0), (u'Child 5', 1), (u'Child 6', 2)])

    def test_collection_field_change_sibling_position(self):
        """
        Set child6 as the first sibling in its branch.
        """
        self.child6.position = 0
        self.child6.save()

        tree = list(Node.objects.order_by('parent__position', 'position').values_list('name', 'position'))
        self.assertEqual(tree, [(u'Parent 1', 0), (u'Parent 2', 1), (u'Child 2', 0), (u'Child 1', 1), (u'Child 3', 2), (u'Child 6', 0), (u'Child 4', 1), (u'Child 5', 2)])

    def test_collection_field_change_first_child(self):
        """
        Move child2 to make it the first child of parent2
        """
        self.child2.position = 0
        self.child2.parent = Node.objects.get(pk=self.parent2.pk)
        self.child2.save()

        tree = list(Node.objects.order_by('parent__position', 'position').values_list('name', 'position'))
        self.assertEqual(tree, [(u'Parent 1', 0), (u'Parent 2', 1), (u'Child 1', 0), (u'Child 3', 1), (u'Child 2', 0), (u'Child 4', 1), (u'Child 5', 2), (u'Child 6', 3)])

    def test_collection_field_change_last_child(self):
        """
        Move child2 to make it the last child of parent2
        """

        self.child2.position = -1
        self.child2.parent = Node.objects.get(pk=self.parent2.pk)
        self.child2.save()

        tree = list(Node.objects.order_by('parent__position', 'position').values_list('name', 'position'))
        self.assertEqual(tree, [(u'Parent 1', 0), (u'Parent 2', 1), (u'Child 1', 0), (u'Child 3', 1), (u'Child 4', 0), (u'Child 5', 1), (u'Child 6', 2), (u'Child 2', 3)])

    def test_collection_field_change_sibling_1(self):
        """
        Move child2 to make it the next sibling of child4
        """

        self.child2.position = 1
        self.child2.parent = Node.objects.get(pk=self.parent2.pk)
        self.child2.save()

        tree = list(Node.objects.order_by('parent__position', 'position').values_list('name', 'position'))
        self.assertEqual(tree, [(u'Parent 1', 0), (u'Parent 2', 1), (u'Child 1', 0), (u'Child 3', 1), (u'Child 4', 0), (u'Child 2', 1), (u'Child 5', 2), (u'Child 6', 3)])

    def test_collection_field_change_sibling_2(self):
        """
        Move child2 to make it the next sibling of child5
        """

        self.child2.position = 2
        self.child2.parent = Node.objects.get(pk=self.parent2.pk)
        self.child2.save()

        tree = list(Node.objects.order_by('parent__position', 'position').values_list('name', 'position'))
        self.assertEqual(tree, [(u'Parent 1', 0), (u'Parent 2', 1), (u'Child 1', 0), (u'Child 3', 1), (u'Child 4', 0), (u'Child 5', 1), (u'Child 2', 2), (u'Child 6', 3)])

    def test_collection_field_change_sibling_3(self):
        """
        Move child2 to make it the next sibling of child6 (last child)
        """

        self.child2.position = 3
        self.child2.parent = Node.objects.get(pk=self.parent2.pk)
        self.child2.save()

        tree = list(Node.objects.order_by('parent__position', 'position').values_list('name', 'position'))
        self.assertEqual(tree, [(u'Parent 1', 0), (u'Parent 2', 1), (u'Child 1', 0), (u'Child 3', 1), (u'Child 4', 0), (u'Child 5', 1), (u'Child 6', 2), (u'Child 2', 3)])

    def test_deletion_1(self):
        """
        Delete child2
        """
        self.child2.delete()
        tree = list(Node.objects.order_by('parent__position', 'position').values_list('name', 'position'))
        self.assertEqual(tree, [(u'Parent 1', 0), (u'Parent 2', 1), (u'Child 1', 0), (u'Child 3', 1), (u'Child 4', 0), (u'Child 5', 1), (u'Child 6', 2)])

    def test_deletion_2(self):
        """
        Delete child3
        """
        self.child3.delete()
        tree = list(Node.objects.order_by('parent__position', 'position').values_list('name', 'position'))
        self.assertEqual(tree, [(u'Parent 1', 0), (u'Parent 2', 1), (u'Child 2', 0), (u'Child 1', 1), (u'Child 4', 0), (u'Child 5', 1), (u'Child 6', 2)])

    def test_deletion_3(self):
        """
        Delete child1
        """
        self.child1.delete()
        tree = list(Node.objects.order_by('parent__position', 'position').values_list('name', 'position'))
        self.assertEqual(tree, [(u'Parent 1', 0), (u'Parent 2', 1), (u'Child 2', 0), (u'Child 3', 1), (u'Child 4', 0), (u'Child 5', 1), (u'Child 6', 2)])

    def test_deletion_4(self):
        """
        Delete parent1
        """
        self.parent1.delete()
        tree = list(Node.objects.order_by('parent__position', 'position').values_list('name', 'position'))
        self.assertEqual(tree, [(u'Parent 2', 0), (u'Child 4', 0), (u'Child 5', 1), (u'Child 6', 2)])


class ReorderTestCase(TestCase):
    def tearDown(self):
        Node.objects.all().delete()

    def test_assigning_parent(self):
        a = Node.objects.create(name=u"A")
        b = Node.objects.create(name=u"B")
        c = Node.objects.create(name=u"C")
        self.assertEqual(a.position, 0)
        self.assertEqual(b.position, 1)
        self.assertEqual(c.position, 2)
        b.parent = a
        b.save()
        # A hasn't changed.
        self.assertEqual(a.position, 0)
        # B has been positioned relative to A.
        self.assertEqual(b.position, 0)
        # C has moved up to fill the gap left by B.
        self.assertEqual(c.position, 1)

    def test_changing_parent(self):
        a = Node.objects.create(name=u"A")
        b = Node.objects.create(name=u"B")
        c = Node.objects.create(name=u"C", parent=a)
        d = Node.objects.create(name=u"D", parent=a)
        self.assertEqual(a.parent, None)
        self.assertEqual(a.position, 0)
        self.assertEqual(b.parent, None)
        self.assertEqual(b.position, 1)
        self.assertEqual(c.parent, a)
        self.assertEqual(c.position, 0)
        self.assertEqual(d.parent, a)
        self.assertEqual(d.position, 1)
        c.parent = b
        c.save()
        # A's position hasn't changed.
        self.assertEqual(a.parent, None)
        self.assertEqual(a.position, 0)
        # B's position hasn't changed.
        self.assertEqual(b.parent, None)
        self.assertEqual(b.position, 1)
        # C's relative position hasn't changed.
        self.assertEqual(c.parent, b)
        self.assertEqual(c.position, 0)
        # D has moved up to fill the gap left by C.
        self.assertEqual(d.parent, a)
        self.assertEqual(d.position, 0)


def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.TestLoader().loadTestsFromTestCase(NodesTestCase))
    s.addTest(doctest.DocFileSuite(os.path.join('doctests', 'nodes.txt'), optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return s

########NEW FILE########
__FILENAME__ = forms
from django import forms

from positions.examples.photos.models import Photo


class PhotoForm(forms.ModelForm):
    class Meta:
        model = Photo 
        fields = ['name',]

########NEW FILE########
__FILENAME__ = models
from django.db import models

from positions import PositionField


class Album(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name


class Photo(models.Model):
    album = models.ForeignKey(Album, related_name='photos')
    name = models.CharField(max_length=50)
    position = PositionField(collection='album', default=0)

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = tests
import doctest
import unittest

from positions.examples.photos.forms import PhotoForm
from positions.examples.photos.models import Album, Photo


tests = """

>>> album = Album.objects.create(name="Vacation")


# The Photo model doesn't use the default (-1) position. Make sure that works.

>>> bahamas = album.photos.create(name="Bahamas")
>>> bahamas.position
0

>>> jamaica = album.photos.create(name="Jamaica")
>>> jamaica.position
0

>>> grand_cayman = album.photos.create(name="Grand Cayman")
>>> grand_cayman.position
0

>>> cozumel = album.photos.create(name="Cozumel")
>>> cozumel.position
0

>>> album.photos.order_by('position').values_list('name', 'position')
[(u'Cozumel', 0), (u'Grand Cayman', 1), (u'Jamaica', 2), (u'Bahamas', 3)]

>>> cozumel.name = "Cozumel, Mexico"
>>> cozumel.save(update_fields=['name'])
>>> cozumel.position
0

>>> jamaica.name = "Ocho Rios, Jamaica"
>>> jamaica.save(update_fields=['name', 'position'])
>>> jamaica.position
2

>>> grand_cayman_form = PhotoForm(dict(name="Georgetown, Grand Cayman"), instance=grand_cayman)
>>> grand_cayman = grand_cayman_form.save()
>>> grand_cayman.position
1

"""


__test__ = {'tests': tests}


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite())
    return tests

########NEW FILE########
__FILENAME__ = models
from django.db import models

from positions import PositionField


class Menu(models.Model):
    name = models.CharField(max_length=100)


class Item(models.Model):
    menu = models.ForeignKey(Menu)
    position = PositionField(collection='menu')


class Food(Item):
    name = models.CharField(max_length=100)


class Drink(Item):
    name = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = tests
import doctest
import unittest

from django.db import models

from positions.examples.restaurants.models import Menu, Food, Drink


tests = """

>>> romanos = Menu.objects.create(name="Romano's Pizza")

>>> pizza = Food.objects.create(menu=romanos, name="Pepperoni")
>>> pizza.position
0

>>> wine = Drink.objects.create(menu=romanos, name="Merlot")
>>> wine.position
0

>>> spaghetti = Food.objects.create(menu=romanos, name="Spaghetti & Meatballs")
>>> spaghetti.position
1

>>> soda = Drink.objects.create(menu=romanos, name="Coca-Cola")
>>> soda.position
1

"""


__test__ = {'tests': tests}


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite())
    return tests

########NEW FILE########
__FILENAME__ = models
from django.db import models

from positions import PositionField


class SubUnit(models.Model):
    name = models.CharField(max_length=100)


class Task(models.Model):
    """
    Base class for lessons/exercises - ordered items within a sub-unit
    """
    sub_unit = models.ForeignKey(SubUnit)
    title = models.CharField(max_length=100)
    position = PositionField(collection='sub_unit', parent_link='task_ptr')


class Lesson(Task):
    text = models.CharField(max_length=100)


class Exercise(Task):
    description = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = tests
import doctest
import unittest

from django.db import models

from positions.examples.school.models import SubUnit, Lesson, Exercise


tests = """

>>> american_revolution = SubUnit.objects.create(name="American Revolution")

>>> no_taxation = Lesson.objects.create(sub_unit=american_revolution, title="No Taxation without Representation", text="...")
>>> no_taxation.position
0

>>> research_paper = Exercise.objects.create(sub_unit=american_revolution, title="Paper", description="Two pages, double spaced")
>>> research_paper.position
1

>>> tea_party = Lesson.objects.create(sub_unit=american_revolution, title="Boston Tea Party", text="...")
>>> tea_party.position
2

>>> quiz = Exercise.objects.create(sub_unit=american_revolution, title="Pop Quiz", description="...")
>>> quiz.position
3

# create a task with an explicit position
>>> intro_lesson = Lesson.objects.create(sub_unit=american_revolution, title="The Intro", text="...", position=0)
>>> american_revolution.task_set.values_list('title', 'position')
[(u'The Intro', 0), (u'No Taxation without Representation', 1), (u'Paper', 2), (u'Boston Tea Party', 3)]

"""


__test__ = {'tests': tests}


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite())
    return tests

########NEW FILE########
__FILENAME__ = settings
SECRET_KEY = 'sekr3t'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'positions.examples.lists',
    'positions.examples.nodes',
    'positions.examples.generic',
    'positions.examples.todo',
    'positions.examples.store',
    'positions.examples.photos',
    'positions.examples.school',
    'positions.examples.restaurants',
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

from positions.fields import PositionField


class Product(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=50)
    products = models.ManyToManyField(Product, through='ProductCategory', related_name='categories')

    def __unicode__(self):
        return self.name


class ProductCategory(models.Model):
    product = models.ForeignKey(Product)
    category = models.ForeignKey(Category)
    position = PositionField(collection='category')

    class Meta(object):
        unique_together = ('product', 'category')

    def __unicode__(self):
        return u"%s in %s" % (self.product, self.category)

########NEW FILE########
__FILENAME__ = tests
import doctest
import unittest

from django.db import models

from positions import PositionField
from positions.examples.store.models import Product, Category, ProductCategory


tests = """

>>> clothes = Category.objects.create(name="Clothes")
>>> sporting_goods = Category.objects.create(name="Sporting Goods")

>>> bat = Product.objects.create(name="Bat")
>>> bat_in_sporting_goods = ProductCategory.objects.create(product=bat, category=sporting_goods)

>>> cap = Product.objects.create(name="Cap")
>>> cap_in_sporting_goods = ProductCategory.objects.create(product=cap, category=sporting_goods)
>>> cap_in_clothes = ProductCategory.objects.create(product=cap, category=clothes)

>>> glove = Product.objects.create(name="Glove")
>>> glove_in_sporting_goods = ProductCategory.objects.create(product=glove, category=sporting_goods)

>>> tshirt = Product.objects.create(name="T-shirt")
>>> tshirt_in_clothes = ProductCategory.objects.create(product=tshirt, category=clothes)

>>> jeans = Product.objects.create(name="Jeans")
>>> jeans_in_clothes = ProductCategory.objects.create(product=jeans, category=clothes)

>>> jersey = Product.objects.create(name="Jersey")
>>> jersey_in_sporting_goods = ProductCategory.objects.create(product=jersey, category=sporting_goods)
>>> jersey_in_clothes = ProductCategory.objects.create(product=jersey, category=clothes)

>>> ball = Product.objects.create(name="Ball")
>>> ball_in_sporting_goods = ProductCategory.objects.create(product=ball, category=sporting_goods)

>>> ProductCategory.objects.filter(category=clothes).values_list('product__name', 'position').order_by('position')
[(u'Cap', 0), (u'T-shirt', 1), (u'Jeans', 2), (u'Jersey', 3)]

>>> ProductCategory.objects.filter(category=sporting_goods).values_list('product__name', 'position').order_by('position')
[(u'Bat', 0), (u'Cap', 1), (u'Glove', 2), (u'Jersey', 3), (u'Ball', 4)]


Moving cap in sporting goods shouldn't effect its position in clothes.

>>> cap_in_sporting_goods.position = -1
>>> cap_in_sporting_goods.save()

>>> ProductCategory.objects.filter(category=clothes).values_list('product__name', 'position').order_by('position')
[(u'Cap', 0), (u'T-shirt', 1), (u'Jeans', 2), (u'Jersey', 3)]

>>> ProductCategory.objects.filter(category=sporting_goods).values_list('product__name', 'position').order_by('position')
[(u'Bat', 0), (u'Glove', 1), (u'Jersey', 2), (u'Ball', 3), (u'Cap', 4)]


# Deleting an object should reorder both collections.
>>> cap.delete()

>>> ProductCategory.objects.filter(category=clothes).values_list('product__name', 'position').order_by('position')
[(u'T-shirt', 0), (u'Jeans', 1), (u'Jersey', 2)]

>>> ProductCategory.objects.filter(category=sporting_goods).values_list('product__name', 'position').order_by('position')
[(u'Bat', 0), (u'Glove', 1), (u'Jersey', 2), (u'Ball', 3)]

"""


__test__ = {'tests': tests}


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite())
    return tests

########NEW FILE########
__FILENAME__ = models
from django.db import models

import positions


class Item(models.Model):
    description = models.CharField(max_length=50)

    # I'm calling the PositionField "index" to make sure any internal code that
    # relies on a PositionField being called "position" will break.
    # https://github.com/jpwatts/django-positions/pull/12
    index = positions.PositionField()

    objects = positions.PositionManager('index')

    def __unicode__(self):
        return self.description


__test__ = {'API_TESTS':"""

>>> Item.objects.position_field_name
'index'

>>> Item.objects.all().position_field_name
'index'

>>> Item.objects.create(description="Add a `reposition` method")
<Item: Add a `reposition` method>

>>> Item.objects.create(description="Write some tests")
<Item: Write some tests>

>>> Item.objects.create(description="Push to GitHub")
<Item: Push to GitHub>

>>> Item.objects.order_by('index')
[<Item: Add a `reposition` method>, <Item: Write some tests>, <Item: Push to GitHub>]

>>> alphabetized = Item.objects.order_by('description')
>>> alphabetized
[<Item: Add a `reposition` method>, <Item: Push to GitHub>, <Item: Write some tests>]

>>> alphabetized.position_field_name
'index'

>>> repositioned = alphabetized.reposition(save=False)
>>> repositioned
[<Item: Add a `reposition` method>, <Item: Push to GitHub>, <Item: Write some tests>]

# Make sure the position wasn't saved
>>> Item.objects.order_by('index')
[<Item: Add a `reposition` method>, <Item: Write some tests>, <Item: Push to GitHub>]

>>> repositioned = alphabetized.reposition()
>>> repositioned
[<Item: Add a `reposition` method>, <Item: Push to GitHub>, <Item: Write some tests>]

>>> Item.objects.order_by('index')
[<Item: Add a `reposition` method>, <Item: Push to GitHub>, <Item: Write some tests>]

>>> item = Item.objects.order_by('index')[0]
>>> item
<Item: Add a `reposition` method>

>>> item.index
0

>>> item.index = -1
>>> item.save()

# Make sure the signals are still connected
>>> Item.objects.order_by('index')
[<Item: Push to GitHub>, <Item: Write some tests>, <Item: Add a `reposition` method>]

>>> [i.index for i in Item.objects.order_by('index')]
[0, 1, 2]


# Add an item at position zero
# http://github.com/jpwatts/django-positions/issues/#issue/7

>>> item0 = Item(description="Fix Issue #7")
>>> item0.index = 0
>>> item0.save()

>>> Item.objects.values_list('description', 'index').order_by('index')
[(u'Fix Issue #7', 0), (u'Push to GitHub', 1), (u'Write some tests', 2), (u'Add a `reposition` method', 3)]

"""}

########NEW FILE########
__FILENAME__ = tests
import doctest
import unittest

from positions.examples.todo import models


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(models))
    return tests

########NEW FILE########
__FILENAME__ = fields
import datetime
import warnings

from django.db import models
from django.db.models.signals import post_delete, post_save, pre_delete

try:
    from django.utils.timezone import now
except ImportError:
    now = datetime.datetime.now

# define basestring for python 3
try:
    basestring
except NameError:
    basestring = (str, bytes)


class PositionField(models.IntegerField):
    def __init__(self, verbose_name=None, name=None, default=-1, collection=None, parent_link=None, unique_for_field=None, unique_for_fields=None, *args, **kwargs):
        if 'unique' in kwargs:
            raise TypeError("%s can't have a unique constraint." % self.__class__.__name__)
        super(PositionField, self).__init__(verbose_name, name, default=default, *args, **kwargs)

        # Backwards-compatibility mess begins here.
        if collection is not None and unique_for_field is not None:
            raise TypeError("'collection' and 'unique_for_field' are incompatible arguments.")

        if collection is not None and unique_for_fields is not None:
            raise TypeError("'collection' and 'unique_for_fields' are incompatible arguments.")

        if unique_for_field is not None:
            warnings.warn("The 'unique_for_field' argument is deprecated.  Please use 'collection' instead.", DeprecationWarning)
            if unique_for_fields is not None:
                raise TypeError("'unique_for_field' and 'unique_for_fields' are incompatible arguments.")
            collection = unique_for_field

        if unique_for_fields is not None:
            warnings.warn("The 'unique_for_fields' argument is deprecated.  Please use 'collection' instead.", DeprecationWarning)
            collection = unique_for_fields
        # Backwards-compatibility mess ends here.

        if isinstance(collection, basestring):
            collection = (collection,)
        self.collection = collection
        self.parent_link = parent_link
        self._collection_changed =  None

    def contribute_to_class(self, cls, name):
        super(PositionField, self).contribute_to_class(cls, name)
        for constraint in cls._meta.unique_together:
            if self.name in constraint:
                raise TypeError("%s can't be part of a unique constraint." % self.__class__.__name__)
        self.auto_now_fields = []
        for field in cls._meta.fields:
            if getattr(field, 'auto_now', False):
                self.auto_now_fields.append(field)
        setattr(cls, self.name, self)
        pre_delete.connect(self.prepare_delete, sender=cls)
        post_delete.connect(self.update_on_delete, sender=cls)
        post_save.connect(self.update_on_save, sender=cls)

    def get_internal_type(self):
        # pre_save always returns a value >= 0
        return 'PositiveIntegerField'

    def pre_save(self, model_instance, add):
        #NOTE: check if the node has been moved to another collection; if it has, delete it from the old collection.
        previous_instance = None
        collection_changed = False
        if not add and self.collection is not None:
            previous_instance = type(model_instance)._default_manager.get(pk=model_instance.pk)
            for field_name in self.collection:
                field = model_instance._meta.get_field(field_name)
                current_field_value = getattr(model_instance, field.attname)
                previous_field_value = getattr(previous_instance, field.attname)
                if previous_field_value != current_field_value:
                    collection_changed = True
                    break
        if not collection_changed:
            previous_instance = None

        self._collection_changed = collection_changed
        if collection_changed:
            self.remove_from_collection(previous_instance)

        cache_name = self.get_cache_name()
        current, updated = getattr(model_instance, cache_name)

        if collection_changed:
            current = None

        if add:
            if updated is None:
                updated = current
            current = None
        elif updated is None:
            updated = -1

        # existing instance, position not modified; no cleanup required
        if current is not None and updated is None:
            return current

        collection_count = self.get_collection(model_instance).count()
        if current is None:
            max_position = collection_count
        else:
            max_position = collection_count - 1
        min_position = 0

        # new instance; appended; no cleanup required on post_save
        if add and (updated == -1 or updated >= max_position):
            setattr(model_instance, cache_name, (max_position, None))
            return max_position

        if max_position >= updated >= min_position:
            # positive position; valid index
            position = updated
        elif updated > max_position:
            # positive position; invalid index
            position = max_position
        elif abs(updated) <= (max_position + 1):
            # negative position; valid index

            # Add 1 to max_position to make this behave like a negative list index.
            # -1 means the last position, not the last position minus 1

            position = max_position + 1 + updated
        else:
            # negative position; invalid index
            position = min_position

        # instance inserted; cleanup required on post_save
        setattr(model_instance, cache_name, (current, position))
        return position

    def __get__(self, instance, owner):
        if instance is None:
            raise AttributeError("%s must be accessed via instance." % self.name)
        current, updated = getattr(instance, self.get_cache_name())
        return current if updated is None else updated

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("%s must be accessed via instance." % self.name)
        if value is None:
            value = self.default
        cache_name = self.get_cache_name()
        try:
            current, updated = getattr(instance, cache_name)
        except AttributeError:
            current, updated = value, None
        else:
            updated = value
        setattr(instance, cache_name, (current, updated))

    def get_collection(self, instance):
        filters = {}
        if self.collection is not None:
            for field_name in self.collection:
                field = instance._meta.get_field(field_name)
                field_value = getattr(instance, field.attname)
                if field.null and field_value is None:
                    filters['%s__isnull' % field.name] = True
                else:
                    filters[field.name] = field_value
        model = type(instance)
        parent_link = self.parent_link
        if parent_link is not None:
            model = model._meta.get_field(parent_link).rel.to
        return model._default_manager.filter(**filters)

    def get_next_sibling(self, instance):
        """
        Returns the next sibling of this instance.
        """
        try:
            return self.get_collection(instance).filter(**{'%s__gt' % self.name: getattr(instance, self.get_cache_name())[0]})[0]
        except:
            return None

    def remove_from_collection(self, instance):
        """
        Removes a positioned item from the collection.
        """
        queryset = self.get_collection(instance)
        current = getattr(instance, self.get_cache_name())[0]
        updates = {self.name: models.F(self.name) - 1}
        if self.auto_now_fields:
            right_now = now()
            for field in self.auto_now_fields:
                updates[field.name] = right_now
        queryset.filter(**{'%s__gt' % self.name: current}).update(**updates)

    def prepare_delete(self, sender, instance, **kwargs):
        next_sibling = self.get_next_sibling(instance)
        if next_sibling:
            setattr(instance, '_next_sibling_pk', next_sibling.pk)
        else:
            setattr(instance, '_next_sibling_pk', None)
        pass

    def update_on_delete(self, sender, instance, **kwargs):
        next_sibling_pk = getattr(instance, '_next_sibling_pk', None)
        if next_sibling_pk:
            try:
                next_sibling = type(instance)._default_manager.get(pk=next_sibling_pk)
            except:
                next_sibling = None
            if next_sibling:
                queryset = self.get_collection(next_sibling)
                current = getattr(instance, self.get_cache_name())[0]
                updates = {self.name: models.F(self.name) - 1}
                if self.auto_now_fields:
                    right_now = now()
                    for field in self.auto_now_fields:
                        updates[field.name] = right_now
                queryset.filter(**{'%s__gt' % self.name: current}).update(**updates)
        setattr(instance, '_next_sibling_pk', None)

    def update_on_save(self, sender, instance, created, **kwargs):
        collection_changed = self._collection_changed
        self._collection_changed = None

        current, updated = getattr(instance, self.get_cache_name())

        if updated is None and collection_changed == False:
            return None

        queryset = self.get_collection(instance).exclude(pk=instance.pk)

        updates = {}
        if self.auto_now_fields:
            right_now = now()
            for field in self.auto_now_fields:
                updates[field.name] = right_now

        if updated is None and created:
            updated = -1

        if created or collection_changed:
            # increment positions gte updated or node moved from another collection
            queryset = queryset.filter(**{'%s__gte' % self.name: updated})
            updates[self.name] = models.F(self.name) + 1
        elif updated > current:
            # decrement positions gt current and lte updated
            queryset = queryset.filter(**{'%s__gt' % self.name: current, '%s__lte' % self.name: updated})
            updates[self.name] = models.F(self.name) - 1
        else:
            # increment positions lt current and gte updated
            queryset = queryset.filter(**{'%s__lt' % self.name: current, '%s__gte' % self.name: updated})
            updates[self.name] = models.F(self.name) + 1

        queryset.update(**updates)
        setattr(instance, self.get_cache_name(), (updated, None))

    def south_field_triple(self):
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.IntegerField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)

########NEW FILE########
__FILENAME__ = managers
from django.db.models import Manager
from django.db.models.query import QuerySet
from django.db.models.signals import post_save

from positions.fields import PositionField


class PositionQuerySet(QuerySet):
    def __init__(self, model=None, query=None, using=None, position_field_name='position'):
        super(PositionQuerySet, self).__init__(model, query, using)
        self.position_field_name = position_field_name

    def _clone(self, *args, **kwargs):
        queryset = super(PositionQuerySet, self)._clone(*args, **kwargs)
        queryset.position_field_name = self.position_field_name
        return queryset

    def reposition(self, save=True):
        position_field = self.model._meta.get_field_by_name(self.position_field_name)[0]
        post_save.disconnect(position_field.update_on_save, sender=self.model)
        position = 0
        for obj in self.iterator():
            setattr(obj, self.position_field_name, position)
            if save:
                obj.save()
            position += 1
        post_save.connect(position_field.update_on_save, sender=self.model)
        return self


class PositionManager(Manager):
    def __init__(self, position_field_name='position'):
        super(PositionManager, self).__init__()
        self.position_field_name = position_field_name

    def get_query_set(self):
        return PositionQuerySet(self.model, position_field_name=self.position_field_name)

    def reposition(self):
        return self.get_query_set().reposition()

########NEW FILE########
