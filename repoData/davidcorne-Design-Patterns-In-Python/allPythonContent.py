__FILENAME__ = DataCaching
#!/usr/bin/env python
# Written by: DGC

# python imports
import math

#==============================================================================
class DataCache(object):

    def __init__(self):
        """ A class representing cachable data, starts invalid."""
        self.data = None

    def __call__(self):
        """ 
        When an instance is called it returns the stored data or None if no 
        data has been cached.
        e.g
        data = cached_data()
        """
        return self.data

    def __nonzero__(self):
        """ 
        Called on bool(instance) or if(instance) returns if there is data 
        cached.
        e.g
        if (not data):
            # set data
        """
        return self.data is not None
    
    def set(self, data):
        """ Sets the data. """
        self.data = data
        
    def reset(self):
        """ Returns the class to an invalid state. """
        self.data = None

#==============================================================================
class Line(object):
    
    def __init__(self, start, end):
        """ 
        This is a class representing a 2D line.
        Takes a start point and end point represented by two pairs.
        """
        self.start = start
        self.end = end
        self.length_data = DataCache()
        
    def length(self):
        if (not self.length_data):
            x_length = self.start[0] - self.end[0]
            y_length = self.start[1] - self.end[1]
            length = math.sqrt((x_length ** 2) + (y_length ** 2))
            self.length_data.set(length)
        else:
            print("Cached value used")
        return self.length_data()

#==============================================================================
if (__name__ == "__main__"):
    l = Line((0, 0), (1, 0))
    print(l.length())
    print(l.length())
    

########NEW FILE########
__FILENAME__ = Interpreter
#!/usr/bin/env python
# Written by: DGC

import re

#==============================================================================
class CamelCase(object):

    def __init__(self):
        self.SomeProperty = "A property"

    def SomeMethod(self, argument):
        print(argument)

#==============================================================================
class CamelCaseInterpreter(object):
    
    def __init__(self, old_class):
        super(CamelCaseInterpreter, self).__setattr__("__old_class", old_class)

    def __getattribute__(self, name):
        old_class = super(CamelCaseInterpreter, self).__getattribute__("__old_class")
        converter = super(CamelCaseInterpreter, self).__getattribute__("name_converter")
        return old_class.__getattribute__(converter(name))

    def __setattr__(self, name, value):
        old_class = super(CamelCaseInterpreter, self).__getattribute__("__old_class")
        converter = super(CamelCaseInterpreter, self).__getattribute__("name_converter")
        old_class.__setattr__(converter(name), value)

    def name_converter(self, name):
        """ 
        Converts function/property names which are lowercase with underscores 
        to CamelCase. i.e some_property becomes SomeProperty.
        """
        new_name = name[0].upper()
        previous_underscore = new_name == "_"
        for char in name[1:]:
            if (char == "_"):
                previous_underscore = True
            else:
                if (previous_underscore):
                    new_name += char.upper()
                else:
                    new_name += char
                previous_underscore = False
        return new_name

#==============================================================================
if (__name__ == "__main__"):
    old_class = CamelCase()

    interpreted_class = CamelCaseInterpreter(old_class)
    print(interpreted_class.some_property)

    interpreted_class.some_property = "Newly set property"
    print(interpreted_class.some_property)

    interpreted_class.some_method("Argument to some_method")
    

########NEW FILE########
__FILENAME__ = Iterator
#!/usr/bin/env python
# Written by: DGC

#==============================================================================
class ReverseIterator(object):
    """ 
    Iterates the object given to it in reverse so it shows the difference. 
    """

    def __init__(self, iterable_object):
        self.list = iterable_object
        # start at the end of the iterable_object
        self.index = len(iterable_object)

    def __iter__(self):
        # return an iterator
        return self

    def next(self):
        """ Return the list backwards so it's noticeably different."""
        if (self.index == 0):
            # the list is over, raise a stop index exception
            raise StopIteration
        self.index = self.index - 1
        return self.list[self.index]

#==============================================================================
class Days(object):

    def __init__(self):
        self.days = [
        "Monday",
        "Tuesday", 
        "Wednesday", 
        "Thursday",
        "Friday", 
        "Saturday", 
        "Sunday"
        ]

    def reverse_iter(self):
        return ReverseIterator(self.days)

#==============================================================================
if (__name__ == "__main__"):
    days = Days()
    for day in days.reverse_iter():
        print(day)

########NEW FILE########
__FILENAME__ = Memento
#!/usr/bin/env python
# Written by: DGC

import copy

#==============================================================================
class Memento(object):

    def __init__(self, data):
        # make a deep copy of every variable in the given class
        for attribute in vars(data):
            # mechanism for using properties without knowing their names
            setattr(self, attribute, copy.deepcopy(getattr(data, attribute)))

#==============================================================================
class Undo(object):

    def __init__(self):
        # each instance keeps the latest saved copy so that there is only one 
        # copy of each in memory
        self.__last = None

    def save(self):
        self.__last = Memento(self)

    def undo(self):
        for attribute in vars(self):
            # mechanism for using properties without knowing their names
            setattr(self, attribute, getattr(self.__last, attribute))

#==============================================================================
class Data(Undo):

    def __init__(self):
        super(Data, self).__init__()
        self.numbers = []

#==============================================================================
if (__name__ == "__main__"):
    d = Data()
    repeats = 10
    # add a number to the list in data repeat times
    print("Adding.")
    for i in range(repeats):
        print("0" + str(i) + " times: " + str(d.numbers))
        d.save()
        d.numbers.append(i)
    print("10 times: " + str(d.numbers))
    d.save()
    print("")
    
    # now undo repeat times
    print("Using Undo.")
    for i in range(repeats):
        print("0" + str(i) + " times: " + str(d.numbers))
        d.undo()
    print("10 times: " + str(d.numbers))

########NEW FILE########
__FILENAME__ = MonoState
#!/usr/bin/env python
# Written by: DGC

# python imports

#==============================================================================
class MonoState(object):
    __data = 5
    
    @property
    def data(self):
        return self.__class__.__data

    @data.setter
    def data(self, value):
        self.__class__.__data = value

#==============================================================================
class MonoState2(object):
    pass

def add_monostate_property(cls, name, initial_value):
    """
    Adds a property "name" to the class "cls" (should pass in a class object 
    not a class instance) with the value "initial_value".
    
    This property is a monostate property so all instances of the class will 
    have the same value property. You can think of it being a singleton 
    property, the class instances will be different but the property will 
    always be the same.

    This will add a variable __"name" to the class which is the internal 
    storage for the property.

    Example usage:
    class MonoState(object):
        pass
        
    add_monostate_property(MonoState, "data", 5)
    m = MonoState()
    # returns 5
    m.data
    """
    internal_name = "__" + name

    def getter(self):
        return getattr(self.__class__, internal_name)
    def setter(self, value):
        setattr(self.__class__, internal_name, value)
    def deleter(self):
        delattr(self.__class__, internal_name)
    prop = property(getter, setter, deleter, "monostate variable: " + name)
    # set the internal attribute
    setattr(cls, internal_name, initial_value)
    # set the accesser property
    setattr(cls, name, prop)

#==============================================================================
if (__name__ == "__main__"):
    print("Using a class:")
    class_1 = MonoState()
    print("First data:  " + str(class_1.data))
    class_1.data = 4
    class_2 = MonoState()
    print("Second data: " + str(class_2.data))
    print("First instance:  " + str(class_1))
    print("Second instance: " + str(class_2))
    print("These are not singletons, so these are different instances")

    print("")
    print("")

    print("Dynamically adding the property:")
    add_monostate_property(MonoState2, "data", 5)
    dynamic_1 = MonoState2()
    print("First data:  " + str(dynamic_1.data))
    dynamic_1.data = 4
    dynamic_2 = MonoState2()
    print("Second data: " + str(dynamic_2.data))
    print("First instance:  " + str(dynamic_1))
    print("Second instance: " + str(dynamic_2))
    print("These are not singletons, so these are different instances")

########NEW FILE########
__FILENAME__ = Observer
#!/usr/bin/env python
# Written by: DGC

import abc

class Observer(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def update(self):
        raise

class ConcreteObserver(Observer):
    pass

if (__name__ == "__main__"):
    print("thing")
    conc = ConcreteObserver()
    
    
        



########NEW FILE########
__FILENAME__ = State
#!/usr/bin/env python
# Written by: DGC

#==============================================================================
class Language(object):
    
    def greet(self):
        return self.greeting

#==============================================================================
class English(Language):
    
    def __init__(self):
        self.greeting = "Hello"

#==============================================================================
class French(Language):
    
    def __init__(self):
        self.greeting = "Bonjour"

#==============================================================================
class Spanish(Language):
    
    def __init__(self):
        self.greeting = "Hola"

#==============================================================================
class Multilinguist(object):

    def __init__(self, language):
        self.greetings = {
            "English": "Hello",
            "French": "Bonjour",
            "Spanish": "Hola"
            }
        self.language = language

    def greet(self):
        print(self.greetings[self.language])

#==============================================================================
if (__name__ == "__main__"):

    # talking in English
    translator = Multilinguist("English")
    translator.greet()

    # meets a Frenchman
    translator.language = "French"
    translator.greet()

    # greets a Spaniard
    translator.language = "Spanish"    
    translator.greet()

########NEW FILE########
__FILENAME__ = Strategy
#!/usr/bin/env python
# Written by: DGC

#==============================================================================
class PrimeFinder(object):
    
    def __init__(self, algorithm):
        """ 
        Constructor, takes a callable object called algorithm. 
        algorithm should take a limit argument and return an iterable of prime 
        numbers below that limit.
        """ 
        self.algorithm = algorithm
        self.primes = []

    def calculate(self, limit):
        """ Will calculate all the primes below limit. """
        self.primes = self.algorithm(limit)

    def out(self):
        """ Prints the list of primes prefixed with which algorithm made it """
        print(self.algorithm.__name__)
        for prime in self.primes:
            print(prime)
        print("")

#==============================================================================
def hard_coded_algorithm(limit):
    """ 
    Has hardcoded values for all the primes under 50, returns a list of those
    which are less than the given limit.
    """
    hardcoded_primes = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47]
    primes = []
    for prime in hardcoded_primes:
        if (prime < limit):
            primes.append(prime)
    return primes

#==============================================================================
def standard_algorithm(limit):
    """ 
    Not a great algorithm either, but it's the normal one to use.
    It puts 2 in a list, then for all the odd numbers less than the limit if 
    none of the primes are a factor then add it to the list.
    """
    primes = [2]
    # check only odd numbers.
    for number in range(3, limit, 2):
        is_prime = True
        # divide it by all our known primes, could limit by sqrt(number)
        for prime in primes:
            if (number % prime == 0):
                is_prime = False
                break
        if (is_prime):
            primes.append(number)
    return primes

#==============================================================================
class HardCodedClass(object):
    
    def __init__(self, limit):
        hardcoded_primes = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47]
        self.primes = []
        for prime in hardcoded_primes:
            if (prime < limit):
                self.primes.append(prime)
        
    def __iter__(self):
        return iter(self.primes)

#==============================================================================
if (__name__ == "__main__"):
    hardcoded_primes = PrimeFinder(hard_coded_algorithm)
    hardcoded_primes.calculate(50)
    hardcoded_primes.out()

    standard_primes = PrimeFinder(standard_algorithm)
    standard_primes.calculate(50)
    standard_primes.out()

    class_primes = PrimeFinder(HardCodedClass)
    class_primes.calculate(50)
    class_primes.out()

    print(
        "Do the two algorithms get the same result on 50 primes? %s" 
        %(str(hardcoded_primes.primes == standard_primes.primes))
        )

    # the hardcoded algorithm only works on numbers under 50
    hardcoded_primes.calculate(100)
    standard_primes.calculate(100)

    print(
        "Do the two algorithms get the same result on 100 primes? %s" 
        %(str(hardcoded_primes.primes == standard_primes.primes))
        )

########NEW FILE########
__FILENAME__ = Strategy_old
#!/usr/bin/env python
# Written by: DGC

import abc

#==============================================================================
class PrimeFinder(object):
    
    def __init__(self, algorithm):
        """ 
        Constructor, takes a lass called algorithm. 
        algorithm should have a function called calculate which will take a 
        limit argument and return an iterable of prime numbers below that 
        limit.
        """ 
        self.algorithm = algorithm
        self.primes = []

    def calculate(self, limit):
        """ Will calculate all the primes below limit. """
        self.primes = self.algorithm.calculate(limit)

    def out(self):
        """ Prints the list of primes prefixed with which algorithm made it """
        print(self.algorithm.name)
        for prime in self.primes:
            print(prime)
        print("")

#==============================================================================
class Algorithm(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def calculate(self, limit):
        raise

#==============================================================================
class HardCoded(Algorithm):
    """ 
    Has hardcoded values for all the primes under 50, returns a list of those
    which are less than the given limit.
    """
    
    def __init__(self):
        self.name = "hard_coded_algorithm"

    def calculate(self, limit):
        hardcoded_primes = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47]
        primes = []
        for prime in hardcoded_primes:
            if (prime < limit):
                primes.append(prime)
        return primes

#==============================================================================
class Standard(Algorithm):
    """ 
    Not a great algorithm either, but it's the normal one to use.
    It puts 2 in a list, then for all the odd numbers less than the limit if 
    none of the primes are a factor then add it to the list.
    """

    def __init__(self):
        self.name = "standard_algorithm"

    def calculate(self, limit):
        primes = [2]
        # check only odd numbers.
        for number in range(3, limit, 2):
            is_prime = True
            # divide it by all our known primes, could limit by sqrt(number)
            for prime in primes:
                if (number % prime == 0):
                    is_prime = False
                    break
            if (is_prime):
                primes.append(number)
        return primes

#==============================================================================
if (__name__ == "__main__"):
    hard_coded_algorithm = HardCoded()
    hardcoded_primes = PrimeFinder(hard_coded_algorithm)
    hardcoded_primes.calculate(50)
    hardcoded_primes.out()

    standard_algorithm = Standard()
    standard_primes = PrimeFinder(standard_algorithm)
    standard_primes.calculate(50)
    standard_primes.out()

    print(
        "Do the two algorithms get the same result on 50 primes? %s" 
        %(str(hardcoded_primes.primes == standard_primes.primes))
        )

    # the hardcoded algorithm only works on numbers under 50
    hardcoded_primes.calculate(100)
    standard_primes.calculate(100)

    print(
        "Do the two algorithms get the same result on 100 primes? %s" 
        %(str(hardcoded_primes.primes == standard_primes.primes))
        )

########NEW FILE########
__FILENAME__ = Builder
#!/usr/bin/env python
# Written by: DGC

import abc

#==============================================================================
class Vehicle(object):

    def __init__(self, type_name):
        self.type = type_name
        self.wheels = None
        self.doors = None
        self.seats = None

    def view(self):
        print(
            "This vehicle is a " +
            self.type +
            " with; " +
            str(self.wheels) +
            " wheels, " +
            str(self.doors) +
            " doors, and " +
            str(self.seats) +
            " seats."
            )

#==============================================================================
class VehicleBuilder(object):
    """
    An abstract builder class, for concrete builders to be derived from.
    """
    __metadata__ = abc.ABCMeta
    
    @abc.abstractmethod
    def make_wheels(self):
        raise

    @abc.abstractmethod
    def make_doors(self):
        raise

    @abc.abstractmethod
    def make_seats(self):
        raise

#==============================================================================
class CarBuilder(VehicleBuilder):

    def __init__(self):
        self.vehicle = Vehicle("Car ")

    def make_wheels(self):
        self.vehicle.wheels = 4

    def make_doors(self):
        self.vehicle.doors = 3

    def make_seats(self):
        self.vehicle.seats = 5

#==============================================================================
class BikeBuilder(VehicleBuilder):

    def __init__(self):
        self.vehicle = Vehicle("Bike")

    def make_wheels(self):
        self.vehicle.wheels = 2

    def make_doors(self):
        self.vehicle.doors = 0

    def make_seats(self):
        self.vehicle.seats = 2

#==============================================================================
class VehicleManufacturer(object):
    """
    The director class, this will keep a concrete builder.
    """
    
    def __init__(self):
        self.builder = None

    def create(self):
        """ 
        Creates and returns a Vehicle using self.builder
        Precondition: not self.builder is None
        """
        assert not self.builder is None, "No defined builder"
        self.builder.make_wheels()
        self.builder.make_doors()
        self.builder.make_seats()
        return self.builder.vehicle
    
#==============================================================================
if (__name__ == "__main__"):
    manufacturer = VehicleManufacturer()
    
    manufacturer.builder = CarBuilder()
    car = manufacturer.create()
    car.view()

    manufacturer.builder = BikeBuilder()
    bike = manufacturer.create()
    bike.view()

########NEW FILE########
__FILENAME__ = Factory_Method
#!/usr/bin/env python
# Written by: DGC

#==============================================================================
class Line(object):
    """ A non-directed line. """

    def __init__(self, point_1, point_2):
        self.point_1 = point_1
        self.point_2 = point_2

    def __eq__(self, line):
        """ Magic method to overide == operator. """
        # if the lines are equal then the two points must be the same, but not 
        # necessarily named the same i.e self.point_1 == line.point_2 and 
        # self.point_2 == line.point_1 means that the lines are equal.
        if (type(line) != Line):
            return False
        if (self.point_1 == line.point_1):
            # line numbering matches
            return self.point_2 == line.point_2
        elif (self.point_1 == line.point_2):
            # line numbering does not match
            return self.point_2 == line.point_1
        else:
            # self.point_1 is not the start or end of the other line, not equal
            return False

#==============================================================================
class Vector(object):
    """ A directional vector. """
    
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, vector):
        """ Magic method to overide == operator. """
        if (type(vector) != Vector):
            return False
        return (self.x == vector.x) and (self.y == vector.y)

#------------------------------------------------------------------------------
# Factory functions
#------------------------------------------------------------------------------

class Factory(object):

    @classmethod
    def line_from_point_vector(self, point, vector):
        """ Returns the line from travelling vector from point. """
        new_point = (point[0] + vector.x, point[1] + vector.y)
        return Line(point, new_point)

    @classmethod
    def vector_from_line(self, line):
        """ 
        Returns the directional vector of the line. This is a vector v, such 
        that line.point_1 + v == line.point_2 
        """
        return Vector(
            line.point_2.x - line.point_1.x, 
            line.point_2.y - line.point_1.y
            )

#==============================================================================
if (__name__ == "__main__"):
    # make a line from (1, 1) to (1, 0), check that the line made from the 
    # point (1, 1) and the vector (0, -1) is the same line.
    constructor_line = Line((1, 1), (1, 0))
    vector = Vector(0, -1);
    factory_line = Factory.line_from_point_vector(
        (1, 1),
        vector
        )
    print(constructor_line == factory_line)
    

########NEW FILE########
__FILENAME__ = ResourceAcquisitionIsInitialization
#!/usr/bin/env python
# Written by: DGC

# python imports

# local imports

#==============================================================================
class Box(object):
    
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        print("Box " + self.name + " Opened")
        return self

    def __exit__(self, exception_type, exception, traceback):
        all_none = all(
            arg is None for arg in [exception_type, exception, traceback]
            )
        if (not all_none):
            print("Exception: \"%s\" raised." %(str(exception)))
        print("Box Closed")
        print("")
        return all_none

#==============================================================================
if (__name__ == "__main__"):
    with Box("tupperware") as simple_box:
        print("Nothing in " + simple_box.name)
    with Box("Pandora's") as pandoras_box:
        raise Exception("All the evils in the world")
    print("end")

########NEW FILE########
__FILENAME__ = Singleton
#!/usr/bin/env python
# Written by: DGC

import abc

#==============================================================================
class Singleton(object):
    """ A generic base class to derive any singleton class from. """
    __metaclass__ = abc.ABCMeta
    __instance = None

    def __new__(new_singleton, *arguments, **keyword_arguments):
        """Override the __new__ method so that it is a singleton."""
        if new_singleton.__instance is None:
            new_singleton.__instance = object.__new__(new_singleton)
            new_singleton.__instance.init(*arguments, **keyword_arguments)
        return new_singleton.__instance

    @abc.abstractmethod
    def init(self, *arguments, **keyword_arguments):
        """ 
        as __init__ will be called on every new instance of a base class of 
        Singleton we need a function for initialisation. This will only be 
        called once regardless of how many instances of Singleton are made.
        """
        raise

#==============================================================================
class GlobalState(Singleton):

    def init(self):
        self.value = 0
        print("init() called once")
        print("")

    def __init__(self):
        print("__init__() always called")
        print("")

class DerivedGlobalState(GlobalState):
    
    def __init__(self):
        print("derived made")
        super(DerivedGlobalState, self).__init__()

    def thing(self):
        print(self.value)

#==============================================================================
if (__name__ == "__main__"):
    d = DerivedGlobalState()
    print(type(d))
    d.thing()
    d.value = -20
    e = DerivedGlobalState()
    e.thing()
    f = DerivedGlobalState()
    f.thing()
    
    a = GlobalState()
    # value is default, 0
    print("Expecting 0, value = %i" %(a.value))
    print("")

    # set the value to 5
    a.value = 5

    # make a new object, the value will still be 5
    b = GlobalState()
    print("Expecting 5, value = %i" %(b.value))
    print("")
    print("Is a == b? " + str(a == b))

########NEW FILE########
__FILENAME__ = Adapter
#!/usr/bin/env python
# Written by: DGC

#==============================================================================
class RCCar(object):

    def __init__(self):
        self.speed = 0

    def change_speed(self, speed):
        self.speed = speed
        print("RC car is moving at " + str(self.speed))

#==============================================================================
class RCAdapter(object):

    def __init__(self):
        self.car = RCCar()

    def move_forwards(self):
        self.car.change_speed(10)

    def move_backwards(self):
        self.car.change_speed(-10)

    def stop(self):
        self.car.change_speed(0)

#==============================================================================
class RemoteControl(object):

    def __init__(self):
        self.adapter = RCAdapter()

    def stick_up(self):
        self.adapter.move_forwards()

    def stick_down(self):
        self.adapter.move_backwards()

    def stick_middle(self):
        self.adapter.stop()

#==============================================================================
if (__name__ == "__main__"):
    controller = RemoteControl()
    controller.stick_up()
    controller.stick_middle()
    controller.stick_down()
    controller.stick_middle()
    

########NEW FILE########
__FILENAME__ = Bridge
#!/usr/bin/env python
# Written by: DGC

import abc

#==============================================================================
class Shape(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self):
        pass

    def area(self):
        """ 
        Returns the area of the shape calculated using the shape specific 
        implementation. 
        """
        assert self.calculator != None, "self.calculator not defined."
        return self.calculator(self)

#==============================================================================
class Rectangle(Shape):
    
    def __init__(self, x, y):
        self.calculator = rectangular_area_calculator
        self.x = x
        self.y = y

#==============================================================================
def rectangular_area_calculator(rectangle):
    return rectangle.x * rectangle.y
 
#==============================================================================
class Triangle(Shape):

    def __init__(self, base, height):
        self.calculator = triangular_area_calculator
        self.base = base
        self.height = height

#==============================================================================
def triangular_area_calculator(triangle):
    return 0.5 * triangle.base * triangle.height
       
#==============================================================================
if (__name__ == "__main__"):
    x = 4
    y = 5
    rect = Rectangle(x, y)
    print(str(x) + " x " + str(y) + " Rectangle area: " + str(rect.area()))
  
    base = 4
    height = 5
    tri = Triangle(base, height);
    print(
        "Base " +
        str(base) +
        ", Height " +
        str(height) + 
        " Triangle area: " +
        str(tri.area())
        )

########NEW FILE########
__FILENAME__ = Facade
#!/usr/bin/env python
# Written by: DGC
# An example of how the client interacts with a complex series of objects 
# (car engine, battery and starter motor) through a facade (the car)

#==============================================================================
class Engine(object):
    
    def __init__(self):
        # how much the motor is spinning in revs per minute
        self.spin = 0

    def start(self, spin):
        if (spin > 2000):
            self.spin = spin // 15

#==============================================================================
class StarterMotor(object):
    
    def __init__(self):
        # how much the starter motor is spinning in revs per minute
        self.spin = 0

    def start(self, charge):
        # if there is enough power then spin fast
        if (charge > 50):
            self.spin = 2500

#==============================================================================
class Battery(object):

    def __init__(self):
        # % charged, starts flat
        self.charge = 0

#==============================================================================
class Car(object):
    # the facade object that deals with the battery, engine and starter motor.
    
    def __init__(self):
        self.battery = Battery()
        self.starter = StarterMotor()
        self.engine = Engine()
        
    def turn_key(self):
        # use the battery to turn the starter motor
        self.starter.start(self.battery.charge)

        # use the starter motor to spin the engine
        self.engine.start(self.starter.spin)
        
        # if the engine is spinning the car is started
        if (self.engine.spin > 0):
            print("Engine Started.")
        else:
            print("Engine Not Started.")

    def jump(self):
        self.battery.charge = 100
        print("Jumped")

#==============================================================================
if (__name__ == "__main__"):
    corsa = Car()
    corsa.turn_key()
    corsa.jump()
    corsa.turn_key()


########NEW FILE########
__FILENAME__ = Proxy
#!/usr/bin/env python
# Written by: DGC

# http://sourcemaking.com/design_patterns/proxy
# give 4 good reasons for a proxy to be made.

# A virtual proxy is a placeholder for "expensive to create" objects. The real
# object is only created when a client first requests/accesses the object.
#
# A remote proxy provides a local representative for an object that resides in
# a different address space. This is what the "stub" code in RPC and CORBA 
# provides.

# A protective proxy controls access to a sensitive master object. The 
# "surrogate" object checks that the caller has the access permissions required
# prior to forwarding the request.

# A smart proxy interposes additional actions when an object is accessed. 
# Typical uses include: 
#   o Counting the number of references to the real object so that it can be 
#     freed automatically when there are no more references (aka smart pointer)
#   o Loading a persistent object into memory when it's first referenced,
#   o Checking that the real object is locked before it is accessed to ensure
#     that no other object can change it.


#==============================================================================
class SharedData(object):

    def __init__(self):
        self.resource = "A resource"

#==============================================================================
class AsyncProxy(object):

    def __init__(self, data):
        """ 
        Takes some data which should now only be accessed through this class, 
        otherwise you could get 
        """
        self.data = data


########NEW FILE########
__FILENAME__ = MVC
#!/usr/bin/env python
# Written by: DGC

from Tkinter import *
import random

#==============================================================================
class Model(object):
    
    def __init__(self):
        # q_and_a is a dictionary where the key is a question and the entry is
        # a list of pairs, these pairs are an answer and whether it is correct
        self.q_and_a = {
            "How many wives did Henry VIII have?": [
                ("Five", False),
                ("Six", True),
                ("Seven", False),
                ("Eight", False)
                ],
            "In which Italian city is Romeo and Juliet primarily set?": [
                ("Verona", True),
                ("Naples", False),
                ("Milano", False),
                ("Pisa", False)
                ],
            "A light year is a measure of what?": [
                ("Energy", False),
                ("Speed", False),
                ("Distance", True),
                ("Intensity", False)
                ]
            }

    def question_and_answers(self):
        """ 
        Returns a randomly chosen question (string) and answers (list of 
        strings)  as a pair.
        """
        key = random.choice(self.q_and_a.keys())
        return (key, [x[0] for x in self.q_and_a[key]])

    def is_correct(self, question, answer):
        answers = self.q_and_a[question]
        for ans in answers:
            if (ans[0] == answer):
                return ans[1]
        assert False, "Could not find answer."

#==============================================================================
class View(object):

    def __init__(self):
        self.parent = Tk()
        self.parent.title("Trivia")

        self.initialise_ui()

        self.controller = None

    def clear_screen(self):
        """ Clears the screen deleting all widgets. """
        self.frame.destroy()
        self.initialise_ui()
        
    def initialise_ui(self):
        self.answer_button = None
        self.continue_button = None

        self.frame = Frame(self.parent)
        self.frame.pack()

    def new_question(self, question, answers):
        """ 
        question is a string, answers is a list of strings
        e.g
        view.new_question(
          "Is the earth a sphere?", 
          ["Yes", "No"]
        )
        """
        self.clear_screen()
        # put the question on as a label
        question_label = Label(self.frame, text=question)
        question_label.pack()

        # put the answers on as a radio buttons
        selected_answer = StringVar()
        selected_answer.set(answers[0])

        for answer in answers:
            option = Radiobutton(
                self.frame,
                text=answer,
                variable=selected_answer,
                value=answer,
                )
            option.pack()

        # button to confirm
        answer_function = lambda : self.controller.answer(
            question,
            selected_answer.get()
            )
        self.answer_button = Button(
            self.frame,
            text="Answer",
            command=answer_function
            )
        self.answer_button.pack()
        
    def main_loop(self):
        mainloop()

    def register(self, controller):
        """ Register a controller to give callbacks to. """
        self.controller = controller

    def feedback(self, feedback):
        self.clear_screen()
        label = Label(self.frame, text=feedback)
        label.pack()
        
        self.continue_button = Button(
            self.frame,
            text="Continue",
            command=self.controller.next_question
            )
        self.continue_button.pack()

#==============================================================================
class Controller(object):

    def __init__(self, model, view):
        self.model = model
        self.view = view

        self.view.register(self)
        self.new_question()

    def new_question(self):
        q_and_a = self.model.question_and_answers()
        self.view.new_question(q_and_a[0], q_and_a[1])
        
    def next_question(self):
        self.new_question()
        
    def answer(self, question, answer):
        correct = self.model.is_correct(question, answer)
        feedback = ""
        if (correct):
            feedback = "That is correct."
        else:     
            feedback = "Sorry that's wrong."

        self.view.feedback(feedback)

#==============================================================================
if (__name__ == "__main__"):
    # Note: The view should not send to the model but it is often useful
    # for the view to receive update event information from the model. 
    # However you should not update the model from the view.

    view = View()
    model = Model()
    controller = Controller(model, view)

    view.main_loop()
    

########NEW FILE########
__FILENAME__ = utest_MVC
#!/usr/bin/env python
# Written by: DGC

# python imports
import unittest

# local imports
import MVC

#==============================================================================
class utest_MVC(unittest.TestCase):
    
    def test_model(self):
        model = MVC.Model()
        question, possible_answers = model.question_and_answers()

        # can't test what they are because they're random
        self.assertTrue(
            isinstance(question, str),
            "Question should be a string"
            )
        self.assertTrue(
            isinstance(possible_answers, list),
            "Answers should be a list"
            )

        for item in possible_answers:
            self.assertTrue(
                isinstance(item[0], str),
                "Elements of possible answer list should be strings"
                )

    def test_controller(self):
        model = ModelMock()
        view = ViewMock()
        controller = MVC.Controller(model, view)
        controller.new_question()
        self.assertEqual(
            view.question,
            "Question", 
            "Controller should pass the question to the view."
            )
        controller.answer("Question", "correct")
        self.assertEqual(
            controller.view.mock_feedback,
            "That is correct.", 
            "The feedback for a correct answer is wrong."
            )
        controller.answer("Question", "incorrect")
        self.assertEqual(
            controller.view.mock_feedback,
            "Sorry that's wrong.", 
            "The feedback for an incorrect answer is wrong."
            )
        
    def test_view(self):
        view = MVC.View()
        controller = ControllerMock(view)
        view.register(controller)

        self.assertIs(
            view.answer_button, 
            None,
            "The answer button should not be set."
            )
        self.assertIs(
            view.continue_button,
            None,
            "The continue button should not be set."
            )
        view.new_question("Test", ["correct", "incorrect"])
        
        self.assertIsNot(
            view.answer_button, 
            None,
            "The answer button should be set."
            )
        self.assertIs(
            view.continue_button,
            None,
            "The continue button should not be set."
            )
        # simulate a button press
        view.answer_button.invoke()
        self.assertIs(
            view.answer_button, 
            None,
            "The answer button should not be set."
            )
        self.assertIsNot(
            view.continue_button,
            None,
            "The continue button should be set."
            )

        self.assertEqual(
            controller.question,
            "Test",
            "The question asked should be \"Test\"."
            )
        self.assertEqual(
            controller.answer,
            "correct",
            "The answer given should be \"correct\"."
            )
        
        # continue
        view.continue_button.invoke()
        self.assertIsNot(
            view.answer_button, 
            None,
            "The answer button should be set."
            )
        self.assertIs(
            view.continue_button,
            None,
            "The continue button should not be set."
            )

#==============================================================================
class ViewMock(object):
    
    def new_question(self, question, answers):
        self.question = question
        self.answers = answers

    def register(self, controller):
        pass

    def feedback(self, feedback):
        self.mock_feedback = feedback

#==============================================================================
class ModelMock(object):
    
    def question_and_answers(self):
        return ("Question", ["correct", "incorrect"])

    def is_correct(self, question, answer):
        correct = False
        if (answer == "correct"):
            correct = True
        return correct

#==============================================================================
class ControllerMock(object):
    
    def __init__(self, view):
        self.view = view

    def answer(self, question, answer):
        self.question = question
        self.answer = answer
        self.view.feedback("test")

    def next_question(self):
        self.view.new_question("Test", ["correct", "incorrect"])
    

#==============================================================================
if (__name__ == "__main__"):
    unittest.main(verbosity=2)

########NEW FILE########
