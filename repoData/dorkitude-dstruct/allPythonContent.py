__FILENAME__ = dstruct
from utils import classproperty, extract_classes

class DStruct(object):
    """

    You can use this to wrap a dictionary and/or a list of keyword args with an
    object capable of direct attribute access.  This is great for making fake
    objects that conform to a simple attribute interface.
    
    For example, your controller can use DStruct instead of Dictionaries to
    pass complex/multi-level stuff into a template.  If you pass complex stuff
    in with DStruct, you've established a flexible accessor interface, the
    backend implementation of which can be changed later with no harm done!

    Simple Usage
    ============

    Initialize with a dictionary:

        struct = DStruct({"k1":"v1", "k2": "v2"})
        struct.k1 # outputs "v1"

    Initialize with keyword arguments:

        struct = DStruct(k1="v1", k2="v2")
        struct.k1 # outputs "v1"

    Initialize with a dictionary *and* keyword arguments:

        struct = DStruct({"k3":"v3"}, k1="v1", k2="v2")
        struct.k3 # outputs "v3"
        struct.k2 # outputs "v2"


    Subclassing
    ===========

    You can also subclass DStruct to configure certain behavior.

    You can specify certain attributes as "required", and if your call to the
    constructor is missing one of them, initialization will raise an Exception
    of the type `RequiredAttributeMissing`.

    Optionally, you can demand a specific type for each of these attributes.


    Basic Subclass Examples: Required Attribute
    -------------------------------------------

    Declare a subclass with some required attributes:
    
        class CartesianCoordinate(DStruct):
            # Represents a cartesian point.
            
            # You must construct this with 'x' and 'y' attributes:
            x = DStruct.RequiredAttribute()
            y = DStruct.RequiredAttribute()

    Valid use:

        origin = CartesianCoordinate(x=0, y=0)
        point = CartesianCoordinate(x=5, y=12)
        point.x - origin.x # outputs 5
        point.y - origin.y # outputs 12

    Invalid use:
        
        crap = CartesianCoordinate(x=3) # raises RequiredAttributeMissing

    Advanced Subclass Examples: Required Attribute with a type
    ----------------------------------------------------------
    
    Declare a DStruct subclass with some attribute type requirements:

        class Label(object):
            pass

        class MapLocation(DStruct):
            latitude = DStruct.RequiredAttribute(float)
            longitude = DStruct.RequiredAttribute(float)
            label = DStruct.RequiredAttribute(Label)

            @property
            def name(self):
                return self.label.name
        
    Valid use:

        l1 = MapLocation(latitude=1.1,longitude=1.1,label=BaseLabel("hi"))
        l2 = MapLocation(latitude=1.1,longitude=1.1,label=Label("hi"))

    Invalid use:

        # raises an RequiredAttributeInvalid
        thing = MapLocation({
            "latitude": 1.5,
            "longitude": 3,  # this is an int, not a float!  BOOM!
            "label": Label("sup"), 
            })
            
        # raises an RequiredAttributeInvalid
        thing = MapLocation({
            "latitude": 1.5,
            "longitude": 3.4, 
            "label": 991,  # this is an int, not a Label instance!  BOOM!
            })

    """

    @classproperty
    def struct_schema_check_on_init(cls):
        """

        :returns: Boolean.  If True, the `__init__` method will call the
        `check_struct_schema` method at the end. 

        """
        return True


    def __init__(self, input_dict=None, **entries): 
        """

        Load the provided inputs onto this object, then set the instance
        attribute `_struct_has_loaded` to True.  Optionally (if the class
        attribute `struct_schema_check_on_init` is True), end with a call to
        `self.check_struct_schema()`.

        :param input_dict:  Dictionary.  Any number of key-value pairs to be
        loaded onto this instance.

        :param **entries:  Any number of key-value pairs to be loaded onto this
        instance.

        :returns: None

        """

        # 1. Load the stuff:
        self.load_struct_inputs(input_dict, **entries)

        # 2. Mark myself as having been loaded:
        self._struct_has_loaded = True

        # 3. Optionally, end with a schema check:
        if self.__class__.struct_schema_check_on_init:
            self.check_struct_schema()

    def load_struct_inputs(self, input_dict, **entries):

        if not input_dict:
            input_dict = {}

        self.__dict__.update(input_dict)
        self.__dict__.update(entries)

    @classmethod
    def get_extra_allowed_types(cls, _type):
        """

        Get a list of other types that are "squint matches" for the specified
        type.

        Subclasses can override this for more flexible schemas!

        :param _type:  Type.  The type that was specified in the
        `RequiredAttribute` constructor (the schema's expected type).

        :returns:  List of Types.

        """

        extra_types = []

        # This is provided largely as an example, but also because it's likely
        # to be the desired behavior for most people using `str` as a required
        # type:
        if _type is str:
            extra_types.append(unicode)
        elif _type is unicode:
            extra_types.append(str)

        return extra_types



    def check_struct_schema(self, clazz=None):
        """

        Check this instance's properties against the class's requirements.

        If a required attribute is missing, raise a RequiredAttributeMissing.

        If a required attribute is present, but has an unacceptable type,
        raise a RequiredAttributeInvalid.

        :param clazz: Class.  From which class should we pull the schema?
        Defaults to the instance's class (i.e. `self.__class`), which would
        confirm all the required attributes in the inheritance tree.  This
        parameter is exposed so a subclasses can check the relevant schemas
        with more granularity, if desired.

        :returns:  None.

        """

        if not clazz:
            clazz = self.__class__

        # are there any required attributes?
        if len(clazz.required_attributes) > 0:
            # ...if so, confirm them all:
            for key,required_type in clazz.required_attributes.items():

                # confirm I have something stored at this key
                if key not in self.__dict__:
                    raise DStruct.RequiredAttributeMissing(self, key)

                # validate my value's type (if one is specified)
                if required_type:

                    allowed_types = [required_type]
                    allowed_types += clazz.get_extra_allowed_types(
                            required_type)
                
                    if not [1 for allowed_type in allowed_types 
                            if isinstance(self.__dict__[key], allowed_type)]:
                        raise DStruct.RequiredAttributeInvalid(
                                self, key, self.__dict__[key])

    def __getitem__(self, key):
        return self.__dict__[key]

    @classproperty
    def required_attributes(cls):
        """

        Figures out which attributes, if any, were declared as
        RequiredAttribute instances.

        :returns: Dictionary.  The keys in this dictionary are the names of the
        attributes that are required.  For each attribute, the value either
        `None` or a type object.

        """

        required_attributes = {}

        for clazz in extract_classes(cls):
            for key,value in clazz.__dict__.items():
                if isinstance(value, cls.RequiredAttribute):
                    required_attributes[key] = value.required_type

        return required_attributes

    class RequiredAttribute(object):
        """

        This is a declarative marker class.
        
        It can be used by subclasses to declare a specific attribute as
        a required attribute.

        If it does so, initialization will fail with a
        `RequiredAttributeMissing` exception.

        """
        def __init__(self, required_type=None):
            self.required_type = required_type


    class RequiredAttributeMissing(Exception):
        """

        This is raised by `DStruct.__init__` if you didn't construct the
        instance with some attribute that has been designated as a required
        attribute.

        """
        def __init__(self, struct_instance, key):
            msg = "You need an attribute called `{}` when making a {}".format(
                    key, struct_instance.__class__.__name__)
            super(self.__class__, self).__init__(msg)


    class RequiredAttributeInvalid(Exception): 
        """

        This is raised by `DStruct.__init__` if you construct the instance
        with a required attribute that isn't an instance of the specified type. 

        """
        def __init__(self, struct_instance, key, value):
            msg = "The value of the attribute`{}` must be an instance of {}.".format(
                    key, struct_instance.__class__.required_attributes[key])
            msg += "  Instead, I got: {}, which is a {}".format(
                    value, type(value))
            super(self.__class__, self).__init__(msg)

########NEW FILE########
__FILENAME__ = base_test_case
# Python standard library imports:
import unittest

# Our imports:
from ..utils import snake_to_mixed


class BaseTestCase(unittest.TestCase):
    """

    Extend this with your test cases to get some sweet shit!

    - Notes:
        - Never override the mixed case setup/teardown methods!  Those are how
         

    - Provides:

        - Instance methods:

            - `self.set_up()`: subclasses should use this for their
              test-by-test set up

            - `self.tear_down()`: subclasses should use this for their
              test-by-test tear down

        - Classmethods:

            - `cls.set_up_class():`:  subclasses should use this for their
              class-level set up

            - `cls.tear_down_class()`: subclasses should use this for their
              class-level tear down

        - Method aliases:

            - If you call any snake_case method call (instance method or
              classmethod) and that method does not exist, BaseTestCase will 
              attempt to call the mixedCase version, e.g.:
                - `self.assert_equal()`:  aliases self.assertEqual
                - `self.assert_true()`:  aliases self.assertTrue
    """

    # --------------------
    # Magic for snake_case
    # --------------------
    class __metaclass__(type):
        def __getattr__(cls, name):
            """
            
            This provides snake_case aliases for mixedCase classmethods.

            For instance, if you were to ask for `cls.tear_down_class`, and it
            didn't exist, you would transparently get a reference to
            `cls.tearDownClass` instead.

            """

            name = snake_to_mixed(name)
            return type.__getattribute__(cls, name)
        
    def __getattr__(self, name):
        """
        
        This provides snake_case aliases for mixedCase instance methods.

        For instance, if you were to ask for `self.assert_equal`, and it
        didn't exist, you would transparently get a reference to
        `self.assertEqual` instead.

        """

        mixed_name = snake_to_mixed(name)
        mixed_attr = None

        try:
            mixed_attr = object.__getattribute__(self, mixed_name)
        except:
            pass

        if mixed_attr:
            return mixed_attr

        return self.__getattribute__(name)


    # --------------------------- 
    # Set Up and Tear Down stuff
    # --------------------------- 

    @classmethod
    def setUpClass(cls):
        cls.set_up_class()

    @classmethod
    def tearDownClass(cls):
        cls.tear_down_class()

    def setUp(self):
        self.set_up()

    def tearDown(self):
        self.tear_down()

    @classmethod
    def set_up_class(cls):
        pass

    @classmethod
    def tear_down_class(cls):
        pass


    def set_up(self):
        pass

    def tear_down(self):
        pass

########NEW FILE########
__FILENAME__ = tests
# Python standard library imports:
import random

# Our imports:
from base_test_case import BaseTestCase
from .. import DStruct


class DStructTestCase(BaseTestCase):

    def test_struct(self):

        # test constructing with a dict
        s = DStruct({"k1":"v1", "k2": "v2"})
        self.assert_equal(s.k1, "v1")
        self.assert_equal(s.k2, "v2")

        # test constructing with a list of keyword args
        s = DStruct(k1="v1", k2="v2")
        self.assert_equal(s.k1, "v1")
        self.assert_equal(s.k2, "v2")
        
        # test constructing with both 
        s = DStruct({"k3":"v3"}, k1="v1", k2="v2")
        self.assert_equal(s.k1, "v1")
        self.assert_equal(s.k2, "v2")
        self.assert_equal(s.k3, "v3")

        # confirm readability as dict
        self.assert_equal(s["k1"], "v1")
        self.assert_equal(s["k2"], "v2")
        self.assert_equal(s["k3"], "v3")

    def test_struct_required_attribute_missing(self):

        # make a custom struct class:
        class CartesianCoordinate(DStruct):
            '''

            Represents a cartesian point.  You must construct with 'x' and 'y'
            attibutes!

            '''

            x = DStruct.RequiredAttribute()
            y = DStruct.RequiredAttribute()

            # FYI, it would be equivalent to write:
            # required_attributes = {"x":None, "y":None}


        # create a couple of coordinates:
        origin = CartesianCoordinate({"x":0, "y":0})
        point = CartesianCoordinate(x=5, y=12)
        
        # confirm their values were stored appropriately:
        self.assert_equal(point.x - origin.x, 5) # outputs 5
        self.assert_equal(point.y - origin.y, 12) # outputs 5
        
        # test a few varieties of improper use:
        with self.assert_raises(DStruct.RequiredAttributeMissing):
            crap = CartesianCoordinate(x=3)

        with self.assert_raises(DStruct.RequiredAttributeMissing):
            crap = CartesianCoordinate({"y":3})

        with self.assert_raises(DStruct.RequiredAttributeMissing):
            crap = CartesianCoordinate()

    def test_struct_required_attribute_invalid(self):

        class BaseLabel(object):
            def __init__(self, name):
                self.name = name
        

        class Label(BaseLabel):
            pass


        # make a custom struct class:
        class MapLocation(DStruct):
            '''

            Represents a map location, specified by floating point values.
            
            You must construct this with float values for "latitude" and
            "longitude", plus a BaseLabel value for "label".

            '''

            latitude = DStruct.RequiredAttribute(float)
            longitude = DStruct.RequiredAttribute(float)
            label = DStruct.RequiredAttribute(BaseLabel)

            @property
            def name(self):
                return self.label.name

            # FYI, it would be equivalent to write this:
                #required_attributes = {
                #        "latitude":float, 
                #        "longitude":float,
                #        "name":BaseLabel,
                #        }


        # make one with a BaseLabel instance for the "label" attribute:
        MapLocation(latitude=1.1,longitude=1.1,label=BaseLabel("hi"))
        # ...and one with a Label instance:
        MapLocation(latitude=1.1,longitude=1.1,label=Label("hi"))

        # make one with a single dictionary argument:
        coffeeshop = MapLocation({
                "latitude": 37.744861,
                "longitude": -122.477732,
                "label": Label("Brown Owl Coffee"),
                })
        # ...and confirm the values are held:
        self.assert_equal(coffeeshop.name, "Brown Owl Coffee")
        self.assert_equal(coffeeshop.longitude, -122.477732)
        self.assert_equal(coffeeshop.latitude, 37.744861)

        # make one with a number of keyword arguments:
        office = MapLocation(
                latitude=37.781586,
                longitude=-122.391343,
                label=BaseLabel("Hatchery SF"), 
                )
        # ...and confirm the values are held:
        self.assert_equal(office.name, "Hatchery SF")
        self.assert_equal(office.longitude, -122.391343)
        self.assert_equal(office.latitude, 37.781586)

        # make one with a dictionary argument AND and some keyword arguments:
        space = MapLocation(
                {"latitude":37.773564},
                longitude=-122.415869,
                label=Label("pariSoma"),
                )
        # ...and confirm the values are held:
        self.assert_equal(space.name, "pariSoma")
        self.assert_equal(space.longitude, -122.415869)
        self.assert_equal(space.latitude, 37.773564)


        # supply an invalid attribute type
        with self.assert_raises(DStruct.RequiredAttributeInvalid):
            thing = MapLocation({
                "latitude": 1.5,
                "longitude": 3,  # this is an int, not a float!  BOOM
                "label": Label("sup"), 
                })

        with self.assert_raises(DStruct.RequiredAttributeInvalid):
            thing = MapLocation({
                "latitude": 1.5,
                "longitude": 3.4, 
                "label": 991,# this is an int, not a Label instance!  BOOM
                })

        
        # confirm
        with self.assert_raises(DStruct.RequiredAttributeMissing):
            thing = MapLocation({
                "latitude": 1.5,
                "longitude": 3.4,
                # we didn't send "name", BOOM!
                })

    def test_struct_required_attribute_dictionary(self):
        """

        Make sure we can use a class-level dictionary called
        `required_attributes` rather than relying on the classproperty
        `DStruct.required_attributes()`.

        """

        class SlowInt(DStruct):
            """
            A wrapper for a primitive: the worst integer implementation either.
            """
            required_attributes = {"value": int}

        # this should work:
        i = SlowInt(value=9)

        # this should work:
        i = SlowInt({"value":9})

        # try not sending a field called "value":
        with self.assert_raises(DStruct.RequiredAttributeMissing):
            i = SlowInt({"x":9})

        # try sending an invalid type for "value":
        with self.assert_raises(DStruct.RequiredAttributeInvalid):
            i = SlowInt({"value":9.4}) # a float, not an int. BOOM!

    def test_flexible_schema(self):

        class HippieStruct(DStruct):

            x = DStruct.RequiredAttribute(int)
            y = DStruct.RequiredAttribute(float)

            @classmethod
            def get_extra_allowed_types(cls, _type):
                x = super(HippieStruct, cls).get_extra_allowed_types(
                        _type)

                if _type is int:
                    x.append(float)
                elif _type is float:
                    x.append(int)

                return x


        # None of these should fail, since float and int are interchangeable
        # now:
        HippieStruct(x=1, y=1)
        HippieStruct(x=1.5, y=1.5)
        HippieStruct(x=1, y=1.5)
        HippieStruct(x=1.5, y=1)

        # But this should still fail:
        with self.assert_raises(DStruct.RequiredAttributeInvalid):
            HippieStruct(x="DUDE THAT IS A STRING!", y=1)

    def test_delayed_verification(self):

        class Product(DStruct):

            # tell DStruct.__init__ not to verify schema:
            struct_schema_check_on_init = False

            # schema:
            name = DStruct.RequiredAttribute(str)
            category = DStruct.RequiredAttribute(str)
            price_in_cents = DStruct.RequiredAttribute(int)
            price_displayed = DStruct.RequiredAttribute(str)

            def __init__(self, *args, **kwargs):
                # load my attributes:
                super(Product, self).__init__(*args, **kwargs)

                # set price_displayed:
                self.price_displayed = "${}".format(
                        float(self.price_in_cents)/100)

                # now, check the schema:
                self.check_struct_schema()


        # make a valid Product:
        product = Product(
                name="The Ten Faces of Innovation",
                category="Books",
                price_in_cents=1977)

        self.assert_equal(product.price_displayed, "$19.77")


        # make a Product that's missing a required attribute:
        with self.assert_raises(DStruct.RequiredAttributeMissing):
            product = Product(
                    name="The Ten Faces of Innovation",
                    price_in_cents=1977)

        # make an invalid Product:
        with self.assert_raises(DStruct.RequiredAttributeInvalid):
            product = Product(
                    name="The Ten Faces of Innovation",
                    category=None,
                    price_in_cents=1977)


    def test_extra_allowed_types(self):

        class NonUser(DStruct):
            """

            Represents someone who has landed on site, but hasn't yet done
            Facebook auth or Twitter auth.

            """

            # schema:
            name = DStruct.RequiredAttribute(str)
            age = DStruct.RequiredAttribute(int)


            @classmethod
            def get_extra_allowed_types(cls, _type):
                """

                Overriding this because sometimes we won't have a person's age,
                but if we do, we need it to be an integer.

                """

                extra_types = []

                if _type is int:
                    extra_types.append(type(None))

                return extra_types


        # make a valid NonUser with name and age:
        anon = NonUser(
                name="user_from_linked_in_ad_31351513_A13CB941FF22",
                age=27)

        # make a valid NonUser with name but an age of `None`:
        anon = NonUser(
                name="user_from_linked_in_ad_31351513_A13CB941FF22",
                age=None)

        # make a NonUser and don't send the age:
        with self.assert_raises(DStruct.RequiredAttributeMissing):
            anon = NonUser(
                    name="user_from_linked_in_ad_31351513_A13CB941FF22")

        # make a NonUser and send an age that is not an `int` OR `None`:
        with self.assert_raises(DStruct.RequiredAttributeInvalid):
            anon = NonUser(
                    name="user_from_linked_in_ad_31351513_A13CB941FF22",
                    age="eighteen")

########NEW FILE########
__FILENAME__ = utils
import string


def dedupe_list(input_list, preserve_order=True):
    """

    Remove duplicates from the list, preserving order.

    :param input_list: list, the thing we need to dedupe
    :returns: list, a new copy of the input_list without duplicates

    """
    seen = set()
    return [ x for x in input_list if x not in seen and not seen.add(x)]


def snake_to_mixed(underscore_input):
    """
    mixedCaseLooksLikeThis
    """

    word_list = underscore_input.split('_')
    word_count = len( word_list )
    if word_count > 1:
        for i in range(1, word_count):
            word_list[i] = string.capwords( word_list[i] )
    ret = ''.join(word_list)
    return ret



def extract_classes(clazz):
    """

    Find all parent classes, anywhere in the inheritance tree.

    :param clazz: class, the thing to crawl through 
    
    Returns a list of all base classes in the inheritance tree

    """

    extracted = [clazz]

    for base in clazz.__bases__:
        extracted += extract_classes(base)

    # no need to include 'object'
    if object in extracted:
        extracted.remove(object)

    return dedupe_list(extracted, preserve_order=True)
 

# Decorate a method with @classproperty to make it behave like @property, but 
# at the class level. 
# Stolen by dorkitude from StackOverflow: http://goo.gl/06cij

class ClassPropertyError(Exception):
    pass


class ClassPropertyDescriptor(object):

    def __init__(self, fget, fset=None):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        return self.fget.__get__(obj, klass)()

def classproperty(func):
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)

    return ClassPropertyDescriptor(func)


########NEW FILE########
