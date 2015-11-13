__FILENAME__ = 3-tier
#!/usr/bin/env python
# -*- coding: utf-8 -*-


class Data(object):
    """ Data Store Class """

    products = {
        'milk': {'price': 1.50, 'quantity': 10},
        'eggs': {'price': 0.20, 'quantity': 100},
        'cheese': {'price': 2.00, 'quantity': 10}
    }

    def __get__(self, obj, klas):
        print ("(Fetching from Data Store)")
        return {'products': self.products}


class BusinessLogic(object):

    """ Business logic holding data store instances """

    data = Data()

    def product_list(self):
        return self.data['products'].keys()

    def product_information(self, product):
        return self.data['products'].get(product, None)


class Ui(object):
    """ UI interaction class """

    def __init__(self):
        self.business_logic = BusinessLogic()

    def get_product_list(self):
        print('PRODUCT LIST:')
        for product in self.business_logic.product_list():
            #print(product)
            yield product
        print('')

    def get_product_information(self, product):
        product_info = self.business_logic.product_information(product)
        if product_info:
            print('PRODUCT INFORMATION:')
            print('Name: {0}, Price: {1:.2f}, Quantity: {2:}'.format(
                product.title(), product_info.get('price', 0),
                product_info.get('quantity', 0)))
        else:
            print('That product "{0}" does not exist in the records'.format(
                product))


def main():
    ui = Ui()
    ui.get_product_list()
    ui.get_product_information('cheese')
    ui.get_product_information('eggs')
    ui.get_product_information('milk')
    ui.get_product_information('arepas')

if __name__ == '__main__':
    main()

### OUTPUT ###
# (Fetching from Data Store)
# PRODUCT INFORMATION:
# Name: Cheese, Price: 2.00, Quantity: 10
# (Fetching from Data Store)
# PRODUCT INFORMATION:
# Name: Eggs, Price: 0.20, Quantity: 100
# (Fetching from Data Store)
# PRODUCT INFORMATION:
# Name: Milk, Price: 1.50, Quantity: 10
# (Fetching from Data Store)
# That product "arepas" does not exist in the records

########NEW FILE########
__FILENAME__ = abstract_factory
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# http://ginstrom.com/scribbles/2007/10/08/design-patterns-python-style/

"""Implementation of the abstract factory pattern"""

import random


class PetShop:

    """A pet shop"""

    def __init__(self, animal_factory=None):
        """pet_factory is our abstract factory.
        We can set it at will."""

        self.pet_factory = animal_factory

    def show_pet(self):
        """Creates and shows a pet using the
        abstract factory"""

        pet = self.pet_factory.get_pet()
        print("We have a lovely {}".format(pet))
        print("It says {}".format(pet.speak()))
        print("We also have {}".format(self.pet_factory.get_food()))


# Stuff that our factory makes

class Dog:

    def speak(self):
        return "woof"

    def __str__(self):
        return "Dog"


class Cat:

    def speak(self):
        return "meow"

    def __str__(self):
        return "Cat"


# Factory classes

class DogFactory:

    def get_pet(self):
        return Dog()

    def get_food(self):
        return "dog food"


class CatFactory:

    def get_pet(self):
        return Cat()

    def get_food(self):
        return "cat food"


# Create the proper family
def get_factory():
    """Let's be dynamic!"""
    return random.choice([DogFactory, CatFactory])()


# Show pets with various factories
if __name__ == "__main__":
    shop = PetShop()
    for i in range(3):
        shop.pet_factory = get_factory()
        shop.show_pet()
        print("=" * 20)

### OUTPUT ###
# We have a lovely Dog
# It says woof
# We also have dog food
# ====================
# We have a lovely Dog
# It says woof
# We also have dog food
# ====================
# We have a lovely Dog
# It says woof
# We also have dog food
# ====================

########NEW FILE########
__FILENAME__ = adapter
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""http://ginstrom.com/scribbles/2008/11/06/generic-adapter-class-in-python/"""

import os


class Dog(object):

    def __init__(self):
        self.name = "Dog"

    def bark(self):
        return "woof!"


class Cat(object):

    def __init__(self):
        self.name = "Cat"

    def meow(self):
        return "meow!"


class Human(object):

    def __init__(self):
        self.name = "Human"

    def speak(self):
        return "'hello'"


class Car(object):

    def __init__(self):
        self.name = "Car"

    def make_noise(self, octane_level):
        return "vroom{0}".format("!" * octane_level)


class Adapter(object):

    """
    Adapts an object by replacing methods.
    Usage:
    dog = Dog
    dog = Adapter(dog, dict(make_noise=dog.bark))

    >>> objects = []
    >>> dog = Dog()
    >>> objects.append(Adapter(dog, dict(make_noise=dog.bark)))
    >>> cat = Cat()
    >>> objects.append(Adapter(cat, dict(make_noise=cat.meow)))
    >>> human = Human()
    >>> objects.append(Adapter(human, dict(make_noise=human.speak)))
    >>> car = Car()
    >>> car_noise = lambda: car.make_noise(3)
    >>> objects.append(Adapter(car, dict(make_noise=car_noise)))

    >>> for obj in objects:
    ...     print('A {} goes {}'.format(obj.name, obj.make_noise()))
    A Dog goes woof!
    A Cat goes meow!
    A Human goes 'hello'
    A Car goes vroom!!!
    """

    def __init__(self, obj, adapted_methods):
        """We set the adapted methods in the object's dict"""
        self.obj = obj
        self.__dict__.update(adapted_methods)

    def __getattr__(self, attr):
        """All non-adapted calls are passed to the object"""
        return getattr(self.obj, attr)


def main():
    objects = []
    dog = Dog()
    objects.append(Adapter(dog, dict(make_noise=dog.bark)))
    cat = Cat()
    objects.append(Adapter(cat, dict(make_noise=cat.meow)))
    human = Human()
    objects.append(Adapter(human, dict(make_noise=human.speak)))
    car = Car()
    objects.append(Adapter(car, dict(make_noise=lambda: car.make_noise(3))))

    for obj in objects:
        print("A {0} goes {1}".format(obj.name, obj.make_noise()))


if __name__ == "__main__":
    main()

### OUTPUT ###
# A Dog goes woof!
# A Cat goes meow!
# A Human goes 'hello'
# A Car goes vroom!!!

########NEW FILE########
__FILENAME__ = borg
#!/usr/bin/env python
# -*- coding: utf-8 -*-


class Borg:
    __shared_state = {}

    def __init__(self):
        self.__dict__ = self.__shared_state
        self.state = 'Init'

    def __str__(self):
        return self.state


class YourBorg(Borg):
    pass

if __name__ == '__main__':
    rm1 = Borg()
    rm2 = Borg()

    rm1.state = 'Idle'
    rm2.state = 'Running'

    print('rm1: {0}'.format(rm1))
    print('rm2: {0}'.format(rm2))

    rm2.state = 'Zombie'

    print('rm1: {0}'.format(rm1))
    print('rm2: {0}'.format(rm2))

    print('rm1 id: {0}'.format(id(rm1)))
    print('rm2 id: {0}'.format(id(rm2)))

    rm3 = YourBorg()

    print('rm1: {0}'.format(rm1))
    print('rm2: {0}'.format(rm2))
    print('rm3: {0}'.format(rm3))

### OUTPUT ###
# rm1: Running
# rm2: Running
# rm1: Zombie
# rm2: Zombie
# rm1 id: 140732837899224
# rm2 id: 140732837899296
# rm1: Init
# rm2: Init
# rm3: Init

########NEW FILE########
__FILENAME__ = bridge
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""http://en.wikibooks.org/wiki/Computer_Science_Design_Patterns/Bridge_Pattern#Python"""


# ConcreteImplementor 1/2
class DrawingAPI1(object):

    def draw_circle(self, x, y, radius):
        print('API1.circle at {}:{} radius {}'.format(x, y, radius))


# ConcreteImplementor 2/2
class DrawingAPI2(object):

    def draw_circle(self, x, y, radius):
        print('API2.circle at {}:{} radius {}'.format(x, y, radius))


# Refined Abstraction
class CircleShape(object):

    def __init__(self, x, y, radius, drawing_api):
        self._x = x
        self._y = y
        self._radius = radius
        self._drawing_api = drawing_api

    # low-level i.e. Implementation specific
    def draw(self):
        self._drawing_api.draw_circle(self._x, self._y, self._radius)

    # high-level i.e. Abstraction specific
    def scale(self, pct):
        self._radius *= pct


def main():
    shapes = (
        CircleShape(1, 2, 3, DrawingAPI1()),
        CircleShape(5, 7, 11, DrawingAPI2())
    )

    for shape in shapes:
        shape.scale(2.5)
        shape.draw()


if __name__ == '__main__':
    main()

### OUTPUT ###
# API1.circle at 1:2 radius 7.5
# API2.circle at 5:7 radius 27.5

########NEW FILE########
__FILENAME__ = builder
#!/usr/bin/python
# -*- coding : utf-8 -*-

"""
@author: Diogenes Augusto Fernandes Herminio <diofeher@gmail.com>
https://gist.github.com/420905#file_builder_python.py
"""


# Director
class Director(object):

    def __init__(self):
        self.builder = None

    def construct_building(self):
        self.builder.new_building()
        self.builder.build_floor()
        self.builder.build_size()

    def get_building(self):
        return self.builder.building


# Abstract Builder
class Builder(object):

    def __init__(self):
        self.building = None

    def new_building(self):
        self.building = Building()


# Concrete Builder
class BuilderHouse(Builder):

    def build_floor(self):
        self.building.floor = 'One'

    def build_size(self):
        self.building.size = 'Big'


class BuilderFlat(Builder):

    def build_floor(self):
        self.building.floor = 'More than One'

    def build_size(self):
        self.building.size = 'Small'


# Product
class Building(object):

    def __init__(self):
        self.floor = None
        self.size = None

    def __repr__(self):
        return 'Floor: {0.floor} | Size: {0.size}'.format(self)


# Client
if __name__ == "__main__":
    director = Director()
    director.builder = BuilderHouse()
    director.construct_building()
    building = director.get_building()
    print(building)
    director.builder = BuilderFlat()
    director.construct_building()
    building = director.get_building()
    print(building)

### OUTPUT ###
# Floor: One | Size: Big
# Floor: More than One | Size: Small

########NEW FILE########
__FILENAME__ = catalog
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A class that uses different static function depending of a parameter passed in
init. Note the use of a single dictionnary instead of multiple conditions
"""
__author__ = "Ibrahim Diop <http://ibrahim.zinaria.com>"
__gist__ = "<https://gist.github.com/diopib/7679559>"


class Catalog():

    """
    catalog of multiple static methods that are executed depending on an init
    parameter
    """

    def __init__(self, param):

        # dictionary that will be used to determine which static method is
        # to be executed but that will be also used to store possible param
        # value
        self.static_method_choices = {'param_value_1': self.static_method_1,
                                      'param_value_2': self.static_method_2}

        # simple test to validate param value
        if param in self.static_method_choices.keys():
            self.param = param
        else:
            raise Exception("Invalid Value for Param: {0}".format(param))

    @staticmethod
    def static_method_1():
        print("executed method 1!")

    @staticmethod
    def static_method_2():
        print("executed method 2!")

    def main_method(self):
        """
        will execute either static_method_1 or static_method_2
        depending on self.param value
        """
        self.static_method_choices[self.param]()


def main():
    """
    >>> c = Catalog('param_value_1').main_method()
    executed method 1!
    >>> Catalog('param_value_2').main_method()
    executed method 2!
    """

    test = Catalog('param_value_2')
    test.main_method()

if __name__ == "__main__":
    main()

### OUTPUT ###
# executed method 2!

########NEW FILE########
__FILENAME__ = chain
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""http://www.testingperspective.com/wiki/doku.php/collaboration/chetan/designpatternsinpython/chain-of-responsibilitypattern"""


class Handler:

    def __init__(self):
        self._successor = None

    def successor(self, successor):
        self._successor = successor

    def handle(self, request):
        raise NotImplementedError('Must provide implementation in subclass.')


class ConcreteHandler1(Handler):

    def handle(self, request):
        if 0 < request <= 10:
            print('request {} handled in handler 1'.format(request))
        elif self._successor:
            self._successor.handle(request)


class ConcreteHandler2(Handler):

    def handle(self, request):
        if 10 < request <= 20:
            print('request {} handled in handler 2'.format(request))
        elif self._successor:
            self._successor.handle(request)


class ConcreteHandler3(Handler):

    def handle(self, request):
        if 20 < request <= 30:
            print('request {} handled in handler 3'.format(request))
        elif self._successor:
            self._successor.handle(request)


class DefaultHandler(Handler):

    def handle(self, request):
            print('end of chain, no handler for {}'.format(request))


class Client:

    def __init__(self):
        h1 = ConcreteHandler1()
        h2 = ConcreteHandler2()
        h3 = ConcreteHandler3()
        h4 = DefaultHandler()

        h1.successor(h2)
        h2.successor(h3)
        h3.successor(h4)

        self.handlers = (h1, h2, h3, h4,)

    def delegate(self, requests):
        for request in requests:
            self.handlers[0].handle(request)


if __name__ == "__main__":
    client = Client()
    requests = [2, 5, 14, 22, 18, 3, 35, 27, 20]
    client.delegate(requests)

### OUTPUT ###
# request 2 handled in handler 1
# request 5 handled in handler 1
# request 14 handled in handler 2
# request 22 handled in handler 3
# request 18 handled in handler 2
# request 3 handled in handler 1
# end of chain, no handler for 35
# request 27 handled in handler 3
# request 20 handled in handler 2

########NEW FILE########
__FILENAME__ = command
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os


class MoveFileCommand(object):

    def __init__(self, src, dest):
        self.src = src
        self.dest = dest

    def execute(self):
        self()

    def __call__(self):
        print('renaming {} to {}'.format(self.src, self.dest))
        os.rename(self.src, self.dest)

    def undo(self):
        print('renaming {} to {}'.format(self.dest, self.src))
        os.rename(self.dest, self.src)


def main():
    command_stack = []

    # commands are just pushed into the command stack
    command_stack.append(MoveFileCommand('foo.txt', 'bar.txt'))
    command_stack.append(MoveFileCommand('bar.txt', 'baz.txt'))

    # they can be executed later on
    for cmd in command_stack:
        cmd.execute()

    # and can also be undone at will
    for cmd in reversed(command_stack):
        cmd.undo()

if __name__ == "__main__":
    main()

### OUTPUT ###
# renaming foo.txt to bar.txt
# renaming bar.txt to baz.txt
# renaming baz.txt to bar.txt
# renaming bar.txt to foo.txt

########NEW FILE########
__FILENAME__ = composite
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A class which defines a composite object which can store
hieararchical dictionaries with names.

This class is same as a hiearchical dictionary, but it
provides methods to add/access/modify children by name,
like a Composite.

Created Anand B Pillai     <abpillai@gmail.com>

"""
__author__ = "Anand B Pillai"
__maintainer__ = "Anand B Pillai"
__version__ = "0.2"


def normalize(val):
    """ Normalize a string so that it can be used as an attribute
    to a Python object """

    if val.find('-') != -1:
        val = val.replace('-', '_')

    return val


def denormalize(val):
    """ De-normalize a string """

    if val.find('_') != -1:
        val = val.replace('_', '-')

    return val


class SpecialDict(dict):

    """ A dictionary type which allows direct attribute
    access to its keys """

    def __getattr__(self, name):

        if name in self.__dict__:
            return self.__dict__[name]
        elif name in self:
            return self.get(name)
        else:
            # Check for denormalized name
            name = denormalize(name)
            if name in self:
                return self.get(name)
            else:
                raise AttributeError('no attribute named %s' % name)

    def __setattr__(self, name, value):

        if name in self.__dict__:
            self.__dict__[name] = value
        elif name in self:
            self[name] = value
        else:
            # Check for denormalized name
            name2 = denormalize(name)
            if name2 in self:
                self[name2] = value
            else:
                # New attribute
                self[name] = value


class CompositeDict(SpecialDict):

    """ A class which works like a hierarchical dictionary.
    This class is based on the Composite design-pattern """

    ID = 0

    def __init__(self, name=''):

        if name:
            self._name = name
        else:
            self._name = ''.join(('id#', str(self.__class__.ID)))
            self.__class__.ID += 1

        self._children = []
        # Link  back to father
        self._father = None
        self[self._name] = SpecialDict()

    def __getattr__(self, name):

        if name in self.__dict__:
            return self.__dict__[name]
        elif name in self:
            return self.get(name)
        else:
            # Check for denormalized name
            name = denormalize(name)
            if name in self:
                return self.get(name)
            else:
                # Look in children list
                child = self.findChild(name)
                if child:
                    return child
                else:
                    attr = getattr(self[self._name], name)
                    if attr:
                        return attr

                    raise AttributeError('no attribute named %s' % name)

    def isRoot(self):
        """ Return whether I am a root component or not """

        # If I don't have a parent, I am root
        return not self._father

    def isLeaf(self):
        """ Return whether I am a leaf component or not """

        # I am a leaf if I have no children
        return not self._children

    def getName(self):
        """ Return the name of this ConfigInfo object """

        return self._name

    def getIndex(self, child):
        """ Return the index of the child ConfigInfo object 'child' """

        if child in self._children:
            return self._children.index(child)
        else:
            return -1

    def getDict(self):
        """ Return the contained dictionary """

        return self[self._name]

    def getProperty(self, child, key):
        """ Return the value for the property for child
        'child' with key 'key' """

        # First get the child's dictionary
        childDict = self.getInfoDict(child)
        if childDict:
            return childDict.get(key, None)

    def setProperty(self, child, key, value):
        """ Set the value for the property 'key' for
        the child 'child' to 'value' """

        # First get the child's dictionary
        childDict = self.getInfoDict(child)
        if childDict:
            childDict[key] = value

    def getChildren(self):
        """ Return the list of immediate children of this object """

        return self._children

    def getAllChildren(self):
        """ Return the list of all children of this object """

        l = []
        for child in self._children:
            l.append(child)
            l.extend(child.getAllChildren())

        return l

    def getChild(self, name):
        """ Return the immediate child object with the given name """

        for child in self._children:
            if child.getName() == name:
                return child

    def findChild(self, name):
        """ Return the child with the given name from the tree """

        # Note - this returns the first child of the given name
        # any other children with similar names down the tree
        # is not considered.

        for child in self.getAllChildren():
            if child.getName() == name:
                return child

    def findChildren(self, name):
        """ Return a list of children with the given name from the tree """

        # Note: this returns a list of all the children of a given
        # name, irrespective of the depth of look-up.

        children = []

        for child in self.getAllChildren():
            if child.getName() == name:
                children.append(child)

        return children

    def getPropertyDict(self):
        """ Return the property dictionary """

        d = self.getChild('__properties')
        if d:
            return d.getDict()
        else:
            return {}

    def getParent(self):
        """ Return the person who created me """

        return self._father

    def __setChildDict(self, child):
        """ Private method to set the dictionary of the child
        object 'child' in the internal dictionary """

        d = self[self._name]
        d[child.getName()] = child.getDict()

    def setParent(self, father):
        """ Set the parent object of myself """

        # This should be ideally called only once
        # by the father when creating the child :-)
        # though it is possible to change parenthood
        # when a new child is adopted in the place
        # of an existing one - in that case the existing
        # child is orphaned - see addChild and addChild2
        # methods !
        self._father = father

    def setName(self, name):
        """ Set the name of this ConfigInfo object to 'name' """

        self._name = name

    def setDict(self, d):
        """ Set the contained dictionary """

        self[self._name] = d.copy()

    def setAttribute(self, name, value):
        """ Set a name value pair in the contained dictionary """

        self[self._name][name] = value

    def getAttribute(self, name):
        """ Return value of an attribute from the contained dictionary """

        return self[self._name][name]

    def addChild(self, name, force=False):
        """ Add a new child 'child' with the name 'name'.
        If the optional flag 'force' is set to True, the
        child object is overwritten if it is already there.

        This function returns the child object, whether
        new or existing """

        if type(name) != str:
            raise ValueError('Argument should be a string!')

        child = self.getChild(name)
        if child:
            # print('Child %s present!' % name)
            # Replace it if force==True
            if force:
                index = self.getIndex(child)
                if index != -1:
                    child = self.__class__(name)
                    self._children[index] = child
                    child.setParent(self)

                    self.__setChildDict(child)
            return child
        else:
            child = self.__class__(name)
            child.setParent(self)

            self._children.append(child)
            self.__setChildDict(child)

            return child

    def addChild2(self, child):
        """ Add the child object 'child'. If it is already present,
        it is overwritten by default """

        currChild = self.getChild(child.getName())
        if currChild:
            index = self.getIndex(currChild)
            if index != -1:
                self._children[index] = child
                child.setParent(self)
                # Unset the existing child's parent
                currChild.setParent(None)
                del currChild

                self.__setChildDict(child)
        else:
            child.setParent(self)
            self._children.append(child)
            self.__setChildDict(child)


if __name__ == "__main__":
    window = CompositeDict('Window')
    frame = window.addChild('Frame')
    tfield = frame.addChild('Text Field')
    tfield.setAttribute('size', '20')

    btn = frame.addChild('Button1')
    btn.setAttribute('label', 'Submit')

    btn = frame.addChild('Button2')
    btn.setAttribute('label', 'Browse')

    # print(window)
    # print(window.Frame)
    # print(window.Frame.Button1)
    # print(window.Frame.Button2)
    print(window.Frame.Button1.label)
    print(window.Frame.Button2.label)

### OUTPUT ###
# Submit
# Browse

########NEW FILE########
__FILENAME__ = decorator
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""http://stackoverflow.com/questions/3118929/implementing-the-decorator-pattern-in-python"""


class foo_decorator(object):

    def __init__(self, decoratee):
        self._decoratee = decoratee

    def f1(self):
        print("decorated f1")
        self._decoratee.f1()

    def __getattr__(self, name):
        return getattr(self._decoratee, name)


class undecorated_foo(object):

    def f1(self):
        print("original f1")

    def f2(self):
        print("original f2")


@foo_decorator
class decorated_foo(object):

    def f1(self):
        print("original f1")

    def f2(self):
        print("original f2")


def main():
    u = undecorated_foo()
    v = foo_decorator(u)
    # The @foo_decorator syntax is just shorthand for calling
    # foo_decorator on the decorated object right after its
    # declaration.

    v.f1()
    v.f2()

if __name__ == '__main__':
    main()

### OUTPUT ###
# decorated f1
# original f1
# original f2

########NEW FILE########
__FILENAME__ = facade
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

SLEEP = 0.5


# Complex Parts
class TC1:

    def run(self):
        print("###### In Test 1 ######")
        time.sleep(SLEEP)
        print("Setting up")
        time.sleep(SLEEP)
        print("Running test")
        time.sleep(SLEEP)
        print("Tearing down")
        time.sleep(SLEEP)
        print("Test Finished\n")


class TC2:

    def run(self):
        print("###### In Test 2 ######")
        time.sleep(SLEEP)
        print("Setting up")
        time.sleep(SLEEP)
        print("Running test")
        time.sleep(SLEEP)
        print("Tearing down")
        time.sleep(SLEEP)
        print("Test Finished\n")


class TC3:

    def run(self):
        print("###### In Test 3 ######")
        time.sleep(SLEEP)
        print("Setting up")
        time.sleep(SLEEP)
        print("Running test")
        time.sleep(SLEEP)
        print("Tearing down")
        time.sleep(SLEEP)
        print("Test Finished\n")


# Facade
class TestRunner:

    def __init__(self):
        self.tc1 = TC1()
        self.tc2 = TC2()
        self.tc3 = TC3()
        self.tests = [i for i in (self.tc1, self.tc2, self.tc3)]

    def runAll(self):
        [i.run() for i in self.tests]


# Client
if __name__ == '__main__':
    testrunner = TestRunner()
    testrunner.runAll()

### OUTPUT ###
# ###### In Test 1 ######
# Setting up
# Running test
# Tearing down
# Test Finished
#
# ###### In Test 2 ######
# Setting up
# Running test
# Tearing down
# Test Finished
#
# ###### In Test 3 ######
# Setting up
# Running test
# Tearing down
# Test Finished
#

########NEW FILE########
__FILENAME__ = factory_method
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""http://ginstrom.com/scribbles/2007/10/08/design-patterns-python-style/"""


class GreekGetter:

    """A simple localizer a la gettext"""

    def __init__(self):
        self.trans = dict(dog="σκύλος", cat="γάτα")

    def get(self, msgid):
        """We'll punt if we don't have a translation"""
        try:
            return self.trans[msgid]
        except KeyError:
            return str(msgid)


class EnglishGetter:

    """Simply echoes the msg ids"""

    def get(self, msgid):
        return str(msgid)


def get_localizer(language="English"):
    """The factory method"""
    languages = dict(English=EnglishGetter, Greek=GreekGetter)
    return languages[language]()

# Create our localizers
e, g = get_localizer("English"), get_localizer("Greek")
# Localize some text
for msgid in "dog parrot cat bear".split():
    print(e.get(msgid), g.get(msgid))

### OUTPUT ###
# dog σκύλος
# parrot parrot
# cat γάτα
# bear bear

########NEW FILE########
__FILENAME__ = flyweight
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""http://codesnipers.com/?q=python-flyweights"""

import weakref


class Card(object):

    """The object pool. Has builtin reference counting"""
    _CardPool = weakref.WeakValueDictionary()

    """Flyweight implementation. If the object exists in the
    pool just return it (instead of creating a new one)"""
    def __new__(cls, value, suit):
        obj = Card._CardPool.get(value + suit, None)
        if not obj:
            obj = object.__new__(cls)
            Card._CardPool[value + suit] = obj
            obj.value, obj.suit = value, suit
        return obj

    # def __init__(self, value, suit):
    #     self.value, self.suit = value, suit

    def __repr__(self):
        return "<Card: %s%s>" % (self.value, self.suit)


if __name__ == '__main__':
    # comment __new__ and uncomment __init__ to see the difference
    c1 = Card('9', 'h')
    c2 = Card('9', 'h')
    print(c1, c2)
    print(c1 == c2)
    print(id(c1), id(c2))

### OUTPUT ###
# <Card: 9h> <Card: 9h>
# True
# 140368617673296 140368617673296

########NEW FILE########
__FILENAME__ = graph_search
#!/usr/bin/env python
# -*- coding: utf-8 -*-


class GraphSearch:

    """Graph search emulation in python, from source
    http://www.python.org/doc/essays/graphs/"""

    def __init__(self, graph):
        self.graph = graph

    def find_path(self, start, end, path=[]):
        self.start = start
        self.end = end
        self.path = path

        self.path += [self.start]
        if self.start == self.end:
            return self.path
        if self.start not in self.graph:
            return None
        for node in self.graph[self.start]:
            if node not in self.path:
                newpath = self.find_path(node, self.end, self.path)
                if newpath:
                    return newpath
        return None

    def find_all_path(self, start, end, path=[]):
        self.start = start
        self.end = end
        self.path = path
        self.path += [self.start]
        if self.start == self.end:
            return [self.path]
        if self.start not in self.graph:
            return []
        paths = []
        for node in self.graph[self.start]:
            if node not in self.path:
                newpaths = self.find_all_path(node, self.end, self.path)
                for newpath in newpaths:
                    paths.append(newpath)
        return paths

    def find_shortest_path(self, start, end, path=[]):
        self.start = start
        self.end = end
        self.path = path

        self.path += [self.start]
        if self.start == self.end:
            return self.path
        if self.start not in self.graph:
            return None
        shortest = None
        for node in self.graph[self.start]:
            if node not in self.path:
                newpath = self.find_shortest_path(node, self.end, self.path)
                if newpath:
                    if not shortest or len(newpath) < len(shortest):
                        shortest = newpath
        return shortest

# example of graph usage
graph = {'A': ['B', 'C'],
         'B': ['C', 'D'],
         'C': ['D'],
         'D': ['C'],
         'E': ['F'],
         'F': ['C']
         }

# initialization of new graph search object
graph1 = GraphSearch(graph)


print(graph1.find_path('A', 'D'))
print(graph1.find_all_path('A', 'D'))
print(graph1.find_shortest_path('A', 'D'))

### OUTPUT ###
# ['A', 'B', 'C', 'D']
# [['A', 'B', 'C', 'D']]
# ['A', 'B', 'C', 'D']

########NEW FILE########
__FILENAME__ = iterator
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""http://ginstrom.com/scribbles/2007/10/08/design-patterns-python-style/

Implementation of the iterator pattern with a generator"""


def count_to(count):
    """Counts by word numbers, up to a maximum of five"""
    numbers = ["one", "two", "three", "four", "five"]
    # enumerate() returns a tuple containing a count (from start which
    # defaults to 0) and the values obtained from iterating over sequence
    for pos, number in zip(range(count), numbers):
        yield number

# Test the generator
count_to_two = lambda: count_to(2)
count_to_five = lambda: count_to(5)

print('Counting to two...')
for number in count_to_two():
    print(number, end=' ')

print()

print('Counting to five...')
for number in count_to_five():
    print(number, end=' ')

print()

### OUTPUT ###
# Counting to two...
# one two
# Counting to five...
# one two three four five

########NEW FILE########
__FILENAME__ = mediator
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""http://dpip.testingperspective.com/?p=28"""

import random
import time


class TC:

    def __init__(self):
        self._tm = None
        self._bProblem = 0

    def setup(self):
        print("Setting up the Test")
        time.sleep(0.1)
        self._tm.prepareReporting()

    def execute(self):
        if not self._bProblem:
            print("Executing the test")
            time.sleep(0.1)
        else:
            print("Problem in setup. Test not executed.")

    def tearDown(self):
        if not self._bProblem:
            print("Tearing down")
            time.sleep(0.1)
            self._tm.publishReport()
        else:
            print("Test not executed. No tear down required.")

    def setTM(self, tm):
        self._tm = tm

    def setProblem(self, value):
        self._bProblem = value


class Reporter:

    def __init__(self):
        self._tm = None

    def prepare(self):
        print("Reporter Class is preparing to report the results")
        time.sleep(0.1)

    def report(self):
        print("Reporting the results of Test")
        time.sleep(0.1)

    def setTM(self, tm):
        self._tm = tm


class DB:

    def __init__(self):
        self._tm = None

    def insert(self):
        print("Inserting the execution begin status in the Database")
        time.sleep(0.1)
        # Following code is to simulate a communication from DB to TC
        if random.randrange(1, 4) == 3:
            return -1

    def update(self):
        print("Updating the test results in Database")
        time.sleep(0.1)

    def setTM(self, tm):
        self._tm = tm


class TestManager:

    def __init__(self):
        self._reporter = None
        self._db = None
        self._tc = None

    def prepareReporting(self):
        rvalue = self._db.insert()
        if rvalue == -1:
            self._tc.setProblem(1)
            self._reporter.prepare()

    def setReporter(self, reporter):
        self._reporter = reporter

    def setDB(self, db):
        self._db = db

    def publishReport(self):
        self._db.update()
        self._reporter.report()

    def setTC(self, tc):
        self._tc = tc


if __name__ == '__main__':
    reporter = Reporter()
    db = DB()
    tm = TestManager()
    tm.setReporter(reporter)
    tm.setDB(db)
    reporter.setTM(tm)
    db.setTM(tm)
    # For simplification we are looping on the same test.
    # Practically, it could be about various unique test classes and their
    # objects
    for i in range(3):
        tc = TC()
        tc.setTM(tm)
        tm.setTC(tc)
        tc.setup()
        tc.execute()
        tc.tearDown()

### OUTPUT ###
# Setting up the Test
# Inserting the execution begin status in the Database
# Executing the test
# Tearing down
# Updating the test results in Database
# Reporting the results of Test
# Setting up the Test
# Inserting the execution begin status in the Database
# Reporter Class is preparing to report the results
# Problem in setup. Test not executed.
# Test not executed. No tear down required.
# Setting up the Test
# Inserting the execution begin status in the Database
# Executing the test
# Tearing down
# Updating the test results in Database
# Reporting the results of Test

########NEW FILE########
__FILENAME__ = memento
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""http://code.activestate.com/recipes/413838-memento-closure/"""

import copy


def Memento(obj, deep=False):
    state = (copy.copy, copy.deepcopy)[bool(deep)](obj.__dict__)

    def Restore():
        obj.__dict__.clear()
        obj.__dict__.update(state)
    return Restore


class Transaction:

    """A transaction guard. This is really just
      syntactic suggar arount a memento closure.
      """
    deep = False

    def __init__(self, *targets):
        self.targets = targets
        self.Commit()

    def Commit(self):
        self.states = [Memento(target, self.deep) for target in self.targets]

    def Rollback(self):
        for st in self.states:
            st()


class transactional(object):

    """Adds transactional semantics to methods. Methods decorated  with
    @transactional will rollback to entry state upon exceptions.
    """

    def __init__(self, method):
        self.method = method

    def __get__(self, obj, T):
        def transaction(*args, **kwargs):
            state = Memento(obj)
            try:
                return self.method(obj, *args, **kwargs)
            except:
                state()
                raise
        return transaction


class NumObj(object):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return '<%s: %r>' % (self.__class__.__name__, self.value)

    def Increment(self):
        self.value += 1

    @transactional
    def DoStuff(self):
        self.value = '1111'  # <- invalid value
        self.Increment()     # <- will fail and rollback


if __name__ == '__main__':
    n = NumObj(-1)
    print(n)
    t = Transaction(n)
    try:
        for i in range(3):
            n.Increment()
            print(n)
        t.Commit()
        print('-- commited')
        for i in range(3):
            n.Increment()
            print(n)
        n.value += 'x'  # will fail
        print(n)
    except:
        t.Rollback()
        print('-- rolled back')
    print(n)
    print('-- now doing stuff ...')
    try:
        n.DoStuff()
    except:
        print('-> doing stuff failed!')
        import sys
        import traceback
        traceback.print_exc(file=sys.stdout)
        pass
    print(n)

### OUTPUT ###
# <NumObj: -1>
# <NumObj: 0>
# <NumObj: 1>
# <NumObj: 2>
# -- commited
# <NumObj: 3>
# <NumObj: 4>
# <NumObj: 5>
# -- rolled back
# <NumObj: 2>
# -- now doing stuff ...
# -> doing stuff failed!
# Traceback (most recent call last):
#   File "memento.py", line 91, in <module>
#     n.DoStuff()
#   File "memento.py", line 47, in transaction
#     return self.method(obj, *args, **kwargs)
#   File "memento.py", line 67, in DoStuff
# self.Increment()     # <- will fail and rollback
#   File "memento.py", line 62, in Increment
#     self.value += 1
# TypeError: Can't convert 'int' object to str implicitly
# <NumObj: 2>

########NEW FILE########
__FILENAME__ = mvc
#!/usr/bin/env python
# -*- coding: utf-8 -*-


class Model(object):

    products = {
        'milk': {'price': 1.50, 'quantity': 10},
        'eggs': {'price': 0.20, 'quantity': 100},
        'cheese': {'price': 2.00, 'quantity': 10}
    }


class View(object):

    def product_list(self, product_list):
        print('PRODUCT LIST:')
        for product in product_list:
            print(product)
        print('')

    def product_information(self, product, product_info):
        print('PRODUCT INFORMATION:')
        print('Name: %s, Price: %.2f, Quantity: %d\n' %
              (product.title(), product_info.get('price', 0),
               product_info.get('quantity', 0)))

    def product_not_found(self, product):
        print('That product "%s" does not exist in the records' % product)


class Controller(object):

    def __init__(self):
        self.model = Model()
        self.view = View()

    def get_product_list(self):
        product_list = self.model.products.keys()
        self.view.product_list(product_list)

    def get_product_information(self, product):
        product_info = self.model.products.get(product, None)
        if product_info is not None:
            self.view.product_information(product, product_info)
        else:
            self.view.product_not_found(product)


if __name__ == '__main__':

    controller = Controller()
    controller.get_product_list()
    controller.get_product_information('cheese')
    controller.get_product_information('eggs')
    controller.get_product_information('milk')
    controller.get_product_information('arepas')

### OUTPUT ###
# PRODUCT LIST:
# cheese
# eggs
# milk
#
# PRODUCT INFORMATION:
# Name: Cheese, Price: 2.00, Quantity: 10
#
# PRODUCT INFORMATION:
# Name: Eggs, Price: 0.20, Quantity: 100
#
# PRODUCT INFORMATION:
# Name: Milk, Price: 1.50, Quantity: 10
#
# That product "arepas" does not exist in the records

########NEW FILE########
__FILENAME__ = observer
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""http://code.activestate.com/recipes/131499-observer-pattern/"""


class Subject(object):

    def __init__(self):
        self._observers = []

    def attach(self, observer):
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer):
        try:
            self._observers.remove(observer)
        except ValueError:
            pass

    def notify(self, modifier=None):
        for observer in self._observers:
            if modifier != observer:
                observer.update(self)


# Example usage
class Data(Subject):

    def __init__(self, name=''):
        Subject.__init__(self)
        self.name = name
        self._data = 0

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
        self.notify()


class HexViewer:

    def update(self, subject):
        print('HexViewer: Subject %s has data 0x%x' %
              (subject.name, subject.data))


class DecimalViewer:

    def update(self, subject):
        print('DecimalViewer: Subject %s has data %d' %
              (subject.name, subject.data))


# Example usage...
def main():
    data1 = Data('Data 1')
    data2 = Data('Data 2')
    view1 = DecimalViewer()
    view2 = HexViewer()
    data1.attach(view1)
    data1.attach(view2)
    data2.attach(view2)
    data2.attach(view1)

    print("Setting Data 1 = 10")
    data1.data = 10
    print("Setting Data 2 = 15")
    data2.data = 15
    print("Setting Data 1 = 3")
    data1.data = 3
    print("Setting Data 2 = 5")
    data2.data = 5
    print("Detach HexViewer from data1 and data2.")
    data1.detach(view2)
    data2.detach(view2)
    print("Setting Data 1 = 10")
    data1.data = 10
    print("Setting Data 2 = 15")
    data2.data = 15


if __name__ == '__main__':
    main()

### OUTPUT ###
# Setting Data 1 = 10
# DecimalViewer: Subject Data 1 has data 10
# HexViewer: Subject Data 1 has data 0xa
# Setting Data 2 = 15
# HexViewer: Subject Data 2 has data 0xf
# DecimalViewer: Subject Data 2 has data 15
# Setting Data 1 = 3
# DecimalViewer: Subject Data 1 has data 3
# HexViewer: Subject Data 1 has data 0x3
# Setting Data 2 = 5
# HexViewer: Subject Data 2 has data 0x5
# DecimalViewer: Subject Data 2 has data 5
# Detach HexViewer from data1 and data2.
# Setting Data 1 = 10
# DecimalViewer: Subject Data 1 has data 10
# Setting Data 2 = 15
# DecimalViewer: Subject Data 2 has data 15

########NEW FILE########
__FILENAME__ = pool
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""http://stackoverflow.com/questions/1514120/python-implementation-of-the-object-pool-design-pattern"""


class QueueObject():

    def __init__(self, queue, auto_get=False):
        self._queue = queue
        self.object = self._queue.get() if auto_get else None

    def __enter__(self):
        if self.object is None:
            self.object = self._queue.get()
        return self.object

    def __exit__(self, Type, value, traceback):
        if self.object is not None:
            self._queue.put(self.object)
            self.object = None

    def __del__(self):
        if self.object is not None:
            self._queue.put(self.object)
            self.object = None


def main():
    try:
        import queue
    except ImportError:  # python 2.x compatibility
        import Queue as queue

    def test_object(queue):
        queue_object = QueueObject(queue, True)
        print('Inside func: {}'.format(queue_object.object))

    sample_queue = queue.Queue()

    sample_queue.put('yam')
    with QueueObject(sample_queue) as obj:
        print('Inside with: {}'.format(obj))
    print('Outside with: {}'.format(sample_queue.get()))

    sample_queue.put('sam')
    test_object(sample_queue)
    print('Outside func: {}'.format(sample_queue.get()))

    if not sample_queue.empty():
        print(sample_queue.get())


if __name__ == '__main__':
    main()

### OUTPUT ###
# Inside with: yam
# Outside with: yam
# Inside func: sam
# Outside func: sam

########NEW FILE########
__FILENAME__ = prototype
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy


class Prototype:

    def __init__(self):
        self._objects = {}

    def register_object(self, name, obj):
        """Register an object"""
        self._objects[name] = obj

    def unregister_object(self, name):
        """Unregister an object"""
        del self._objects[name]

    def clone(self, name, **attr):
        """Clone a registered object and update inner attributes dictionary"""
        obj = copy.deepcopy(self._objects.get(name))
        obj.__dict__.update(attr)
        return obj

class A:
    def __init__(self):
        self.x = 3
        self.y = 8
        self.z = 15
        self.garbage = [38, 11, 19]

    def __str__(self):
        return '{} {} {} {}'.format(self.x, self.y, self.z, self.garbage)


def main():
    a = A()
    prototype = Prototype()
    prototype.register_object('objecta', a)
    b = prototype.clone('objecta')
    c = prototype.clone('objecta', x=1, y=2, garbage=[88, 1])
    print([str(i) for i in (a, b, c)])

if __name__ == '__main__':
    main()

### OUTPUT ###
# ['3 8 15 [38, 11, 19]', '3 8 15 [38, 11, 19]', '1 2 15 [88, 1]']

########NEW FILE########
__FILENAME__ = proxy
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time


class SalesManager:

    def work(self):
        print("Sales Manager working...")

    def talk(self):
        print("Sales Manager ready to talk")


class Proxy:

    def __init__(self):
        self.busy = 'No'
        self.sales = None

    def work(self):
        print("Proxy checking for Sales Manager availability")
        if self.busy == 'No':
            self.sales = SalesManager()
            time.sleep(2)
            self.sales.talk()
        else:
            time.sleep(2)
            print("Sales Manager is busy")


if __name__ == '__main__':
    p = Proxy()
    p.work()
    p.busy = 'Yes'
    p.work()

### OUTPUT ###
# Proxy checking for Sales Manager availability
# Sales Manager ready to talk
# Proxy checking for Sales Manager availability
# Sales Manager is busy

########NEW FILE########
__FILENAME__ = publish_subscribe
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Reference: http://www.slideshare.net/ishraqabd/publish-subscribe-model-overview-13368808
Author: https://github.com/HanWenfang
"""


class Provider:

    def __init__(self):
        self.msg_queue = []
        self.subscribers = {}

    def notify(self, msg):
        self.msg_queue.append(msg)

    def subscribe(self, msg, subscriber):
        if msg not in self.subscribers:
            self.subscribers[msg] = []
            self.subscribers[msg].append(subscriber)  # unfair
        else:
            self.subscribers[msg].append(subscriber)

    def unsubscribe(self, msg, subscriber):
        self.subscribers[msg].remove(subscriber)

    def update(self):
        for msg in self.msg_queue:
            if msg in self.subscribers:
                for sub in self.subscribers[msg]:
                    sub.run(msg)
        self.msg_queue = []


class Publisher:

    def __init__(self, msg_center):
        self.provider = msg_center

    def publish(self, msg):
        self.provider.notify(msg)


class Subscriber:

    def __init__(self, name, msg_center):
        self.name = name
        self.provider = msg_center

    def subscribe(self, msg):
        self.provider.subscribe(msg, self)

    def run(self, msg):
        print("{} got {}".format(self.name, msg))


def main():
    message_center = Provider()

    fftv = Publisher(message_center)

    jim = Subscriber("jim", message_center)
    jim.subscribe("cartoon")
    jack = Subscriber("jack", message_center)
    jack.subscribe("music")
    gee = Subscriber("gee", message_center)
    gee.subscribe("movie")

    fftv.publish("cartoon")
    fftv.publish("music")
    fftv.publish("ads")
    fftv.publish("movie")
    fftv.publish("cartoon")
    fftv.publish("cartoon")
    fftv.publish("movie")
    fftv.publish("blank")

    message_center.update()


if __name__ == "__main__":
    main()

### OUTPUT ###
# jim got cartoon
# jack got music
# gee got movie
# jim got cartoon
# jim got cartoon
# gee got movie

########NEW FILE########
__FILENAME__ = state
"""Implementation of the state pattern"""

# http://ginstrom.com/scribbles/2007/10/08/design-patterns-python-style/


class State(object):

    """Base state. This is to share functionality"""

    def scan(self):
        """Scan the dial to the next station"""
        self.pos += 1
        if self.pos == len(self.stations):
            self.pos = 0
        print("Scanning... Station is", self.stations[self.pos], self.name)


class AmState(State):

    def __init__(self, radio):
        self.radio = radio
        self.stations = ["1250", "1380", "1510"]
        self.pos = 0
        self.name = "AM"

    def toggle_amfm(self):
        print("Switching to FM")
        self.radio.state = self.radio.fmstate


class FmState(State):

    def __init__(self, radio):
        self.radio = radio
        self.stations = ["81.3", "89.1", "103.9"]
        self.pos = 0
        self.name = "FM"

    def toggle_amfm(self):
        print("Switching to AM")
        self.radio.state = self.radio.amstate


class Radio(object):

    """A radio.     It has a scan button, and an AM/FM toggle switch."""

    def __init__(self):
        """We have an AM state and an FM state"""
        self.amstate = AmState(self)
        self.fmstate = FmState(self)
        self.state = self.amstate

    def toggle_amfm(self):
        self.state.toggle_amfm()

    def scan(self):
        self.state.scan()


# Test our radio out
if __name__ == '__main__':
    radio = Radio()
    actions = [radio.scan] * 2 + [radio.toggle_amfm] + [radio.scan] * 2
    actions *= 2

    for action in actions:
        action()

### OUTPUT ###
# Scanning... Station is 1380 AM
# Scanning... Station is 1510 AM
# Switching to FM
# Scanning... Station is 89.1 FM
# Scanning... Station is 103.9 FM
# Scanning... Station is 81.3 FM
# Scanning... Station is 89.1 FM
# Switching to AM
# Scanning... Station is 1250 AM
# Scanning... Station is 1380 AM

########NEW FILE########
__FILENAME__ = strategy
# http://stackoverflow.com/questions/963965/how-is-this-strategy-pattern
# -written-in-python-the-sample-in-wikipedia
"""
In most of other languages Strategy pattern is implemented via creating some
base strategy interface/abstract class and subclassing it with a number of
concrete strategies (as we can see at
http://en.wikipedia.org/wiki/Strategy_pattern), however Python supports
higher-order functions and allows us to have only one class and inject
functions into it's instances, as shown in this example.
"""
import types


class StrategyExample:

    def __init__(self, func=None):
        self.name = 'Strategy Example 0'
        if func is not None:
            self.execute = types.MethodType(func, self)

    def execute(self):
        print(self.name)


def execute_replacement1(self):
    print(self.name + ' from execute 1')


def execute_replacement2(self):
    print(self.name + ' from execute 2')


if __name__ == '__main__':
    strat0 = StrategyExample()

    strat1 = StrategyExample(execute_replacement1)
    strat1.name = 'Strategy Example 1'

    strat2 = StrategyExample(execute_replacement2)
    strat2.name = 'Strategy Example 2'

    strat0.execute()
    strat1.execute()
    strat2.execute()

### OUTPUT ###
# Strategy Example 0
# Strategy Example 1 from execute 1
# Strategy Example 2 from execute 2

########NEW FILE########
__FILENAME__ = template
"""http://ginstrom.com/scribbles/2007/10/08/design-patterns-python-style/

An example of the Template pattern in Python"""

ingredients = "spam eggs apple"
line = '-' * 10


# Skeletons
def iter_elements(getter, action):
    """Template skeleton that iterates items"""
    for element in getter():
        action(element)
        print(line)


def rev_elements(getter, action):
    """Template skeleton that iterates items in reverse order"""
    for element in getter()[::-1]:
        action(element)
        print(line)


# Getters
def get_list():
    return ingredients.split()


def get_lists():
    return [list(x) for x in ingredients.split()]


# Actions
def print_item(item):
    print(item)


def reverse_item(item):
    print(item[::-1])


# Makes templates
def make_template(skeleton, getter, action):
    """Instantiate a template method with getter and action"""
    def template():
        skeleton(getter, action)
    return template

# Create our template functions
templates = [make_template(s, g, a)
             for g in (get_list, get_lists)
             for a in (print_item, reverse_item)
             for s in (iter_elements, rev_elements)]

# Execute them
for template in templates:
    template()

### OUTPUT ###
# spam
# ----------
# eggs
# ----------
# apple
# ----------
# apple
# ----------
# eggs
# ----------
# spam
# ----------
# maps
# ----------
# sgge
# ----------
# elppa
# ----------
# elppa
# ----------
# sgge
# ----------
# maps
# ----------
# ['s', 'p', 'a', 'm']
# ----------
# ['e', 'g', 'g', 's']
# ----------
# ['a', 'p', 'p', 'l', 'e']
# ----------
# ['a', 'p', 'p', 'l', 'e']
# ----------
# ['e', 'g', 'g', 's']
# ----------
# ['s', 'p', 'a', 'm']
# ----------
# ['m', 'a', 'p', 's']
# ----------
# ['s', 'g', 'g', 'e']
# ----------
# ['e', 'l', 'p', 'p', 'a']
# ----------
# ['e', 'l', 'p', 'p', 'a']
# ----------
# ['s', 'g', 'g', 'e']
# ----------
# ['m', 'a', 'p', 's']
# ----------

########NEW FILE########
__FILENAME__ = visitor
"""http://peter-hoffmann.com/2010/extrinsic-visitor-pattern-python-inheritance.html"""


class Node(object):
    pass


class A(Node):
    pass


class B(Node):
    pass


class C(A, B):
    pass


class Visitor(object):

    def visit(self, node, *args, **kwargs):
        meth = None
        for cls in node.__class__.__mro__:
            meth_name = 'visit_' + cls.__name__
            meth = getattr(self, meth_name, None)
            if meth:
                break

        if not meth:
            meth = self.generic_visit
        return meth(node, *args, **kwargs)

    def generic_visit(self, node, *args, **kwargs):
        print('generic_visit ' + node.__class__.__name__)

    def visit_B(self, node, *args, **kwargs):
        print('visit_B ' + node.__class__.__name__)


a = A()
b = B()
c = C()
visitor = Visitor()
visitor.visit(a)
visitor.visit(b)
visitor.visit(c)

### OUTPUT ###
# generic_visit A
# visit_B B
# visit_B C

########NEW FILE########
