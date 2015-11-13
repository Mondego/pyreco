__FILENAME__ = conf
# -*- coding: utf-8 -*-
import sys, os
sys.path.append("../")

extensions = []
templates_path = ['_templates']
source_suffix = '.txt'
master_doc = 'index'

project = 'milkman'
copyright = '2011'
version = '4.5'
release = '4.5'

today_fmt = '%B %d, %Y'
exclude_trees = []
pygments_style = 'sphinx'
html_style = 'default.css'
html_static_path = ['_static']
html_last_updated_fmt = '%b %d, %Y'

htmlhelp_basename = 'milkmandoc'
latex_documents = [
  ('index', 'milkman.tex', 'Milkman Documentation',
   '', 'manual'),
]

########NEW FILE########
__FILENAME__ = dairy
from django.db import models
from django.db.models.fields.related import RelatedField

from milkman import generators


class MilkmanRegistry(object):
    default_generators = {}

    def __init__(self):
        try:
            self.add_generator(models.BigIntegerField,
                generators.random_big_integer_maker)
        except AttributeError:
            pass  # Only supported in django 1.2+

        self.add_generator(models.AutoField,
            generators.random_auto_field_maker)
        self.add_generator(models.BooleanField,
            generators.random_boolean_maker)
        self.add_generator(models.CharField,
            generators.random_string_maker)
        self.add_generator(models.CommaSeparatedIntegerField,
            generators.random_comma_seperated_integer_maker)
        self.add_generator(models.DateField,
            generators.random_date_string_maker)
        self.add_generator(models.DateTimeField,
            generators.random_datetime)
        self.add_generator(models.DecimalField,
            generators.random_decimal_maker)
        self.add_generator(models.EmailField,
            generators.email_generator('user', 'example.com'))
        self.add_generator(models.FloatField,
            generators.random_float_maker)
        self.add_generator(models.IntegerField,
            generators.random_integer_maker)
        self.add_generator(models.IPAddressField,
            generators.random_ipaddress_maker)
        self.add_generator(models.NullBooleanField,
            generators.random_null_boolean_maker)
        self.add_generator(models.PositiveIntegerField,
            generators.random_positive_integer_maker)
        self.add_generator(models.PositiveSmallIntegerField,
            generators.random_small_positive_integer_maker)
        self.add_generator(models.SlugField,
            generators.random_string_maker)
        self.add_generator(models.SmallIntegerField,
            generators.random_small_integer_maker)
        self.add_generator(models.TextField,
            generators.random_string_maker)
        self.add_generator(models.TimeField,
            generators.random_time_string_maker)
        # self.add_generator(models.URLField, generators.random_url_maker)
        # self.add_generator(models.FileField, default_generator)
        # self.add_generator(models.FilePathField, default_generator)
        self.add_generator(models.ImageField, generators.random_image_maker)
        # self.add_generator(models.XMLField, default_generator)

    def add_generator(self, cls, func):
        self.default_generators[cls] = func

    def get(self, cls):
        return self.default_generators.get(cls,
            lambda f: generators.loop(lambda: ''))


class MilkTruck(object):
    def __init__(self, model_class):
        self.generators = {}
        
        if isinstance(model_class, basestring):
            model_class = self.get_model_class_from_string(model_class)
        self.model_class = model_class

    def get_model_class_from_string(self, model_name):
        assert '.' in model_name, ("'model_class' must be either a model"
                                   " or a model name in the format"
                                   " app_label.model_name")
        app_label, model_name = model_name.split(".")
        return models.get_model(app_label, model_name)

    def deliver(self, the_milkman, **explicit_values):

        model_explicit_values = {}
        related_explicit_values = {}
        for key, value in explicit_values.iteritems():
            if '__' in key:
                prefix, sep, postfix = key.partition('__')
                related_explicit_values.setdefault(prefix, {})
                related_explicit_values[prefix][postfix] = value
            else:
                model_explicit_values[key] = value

        exclude = []
        if model_explicit_values:
            exclude = model_explicit_values.keys()

        target = self.model_class()

        self.set_explicit_values(target, model_explicit_values)
        self.set_local_fields(
            target,
            the_milkman,
            exclude,
            related_explicit_values
        )
        target.save()

        self.set_m2m_explicit_values(target, model_explicit_values)
        self.set_m2m_fields(
            target,
            the_milkman,
            exclude,
            related_explicit_values
        )

        return target

    def is_m2m(self, field):
        return field in [f.name for f in
            self.model_class._meta.local_many_to_many]

    def has_explicit_through_table(self, field):
        if isinstance(field.rel.through, models.base.ModelBase):  # Django 1.2
            return not field.rel.through._meta.auto_created
        if isinstance(field.rel.through, (str, unicode)):  # Django 1.1
            return True
        return False

    def set_explicit_values(self, target, explicit_values):
        for k, v in explicit_values.iteritems():
            if not self.is_m2m(k):
                setattr(target, k, v)

    def set_m2m_explicit_values(self, target, explicit_values):
        for k, vs in explicit_values.iteritems():
            if self.is_m2m(k):
                setattr(target, k, vs)

    def set_local_fields(self,
                         target,
                         the_milkman,
                         exclude,
                         related_explicit_values):
        for field in self.fields_to_generate(self.model_class._meta.fields,
                                             exclude):
            if isinstance(field, RelatedField):
                explicit_values = related_explicit_values.get(field.name, {})
                v = the_milkman.deliver(field.rel.to, **explicit_values)
            else:
                v = self.generator_for(the_milkman.registry, field).next()
            setattr(target, field.name, v)

    def set_m2m_fields(self,
                       target,
                       the_milkman,
                       exclude,
                       related_explicit_values):
        for field in self.fields_to_generate(
                self.model_class._meta.local_many_to_many, exclude):
            if not self.has_explicit_through_table(field):
                exclude = {}
                # if the target field is the same class, we don't want to keep
                # generating
                if type(target) == field.related.model:
                    exclude = {field.name: ''}
                explicit_values = related_explicit_values.get(field.name, {})
                explicit_values.update(exclude)
                setattr(target, field.name, [the_milkman.deliver(
                    field.rel.to, **explicit_values)])

    def generator_for(self, registry, field):
        field_cls = type(field)
        if not field.name in self.generators:
            gen_maker = registry.get(field_cls)
            generator = gen_maker(field)
            self.generators[field.name] = generator()
        return self.generators[field.name]

    def fields_to_generate(self, l, exclude):
        return [f for f in l if f.name not in exclude and
                self.needs_generated_value(f)]

    def needs_generated_value(self, field):
        return hasattr(field, 'has_default') and \
               not field.has_default() and \
               not field.blank and \
               not field.null


class Milkman(object):
    def __init__(self, registry):
        self.trucks = {}
        self.registry = registry

    def deliver(self, model_class, **explicit_values):
        truck = self.trucks.setdefault(model_class, MilkTruck(model_class))
        return truck.deliver(self, **explicit_values)

milkman = Milkman(MilkmanRegistry())

########NEW FILE########
__FILENAME__ = generators
import datetime
import errno
import os
import random
import string
import sys
import uuid

from django.core.files.storage import DefaultStorage
from django.utils import timezone

from PIL import Image, ImageDraw


DEFAULT_STRING_LENGTH = 8
DECIMAL_TEMPLATE = "%%d.%%0%dd"
EMAIL_TEMPLATE = "%s%%d@%s"
DATETIME_TEMPLATE = "%s %d:%d"


def loop(func):
    def loop_generator(*args, **kwargs):
        while 1:
            yield func(*args, **kwargs)
    return loop_generator


def sequence(func):
    def sequence_generator(*args, **kwargs):
        i = 0
        while 1:
            i += 1
            yield func(i, *args, **kwargs)
    return sequence_generator


def default_gen_maker(field):
    return loop(lambda: '')


def random_choice_iterator(choices=[''], size=1):
    for i in range(0, size):
        yield random.choice(choices)


def random_string_maker(field, chars=None):
    max_length = getattr(field, 'max_length', DEFAULT_STRING_LENGTH)
    return loop(lambda: random_string(max_length, chars))


def random_string(max_length=None, chars=None):
    if max_length is None:
        max_length = DEFAULT_STRING_LENGTH
    if chars is None:
        chars = (string.ascii_letters + string.digits)
    i = random_choice_iterator(chars, max_length)
    return ''.join(x for x in i)


def random_boolean_maker(field=None):
    return loop(lambda: random.choice((True, False)))


def random_null_boolean_maker(field=None):
    return loop(lambda: random.choice((None, True, False)))


def random_datetime(field):
    return loop(lambda: timezone.now() - datetime.timedelta(days=random.randint(0, 300)))


def random_date(field):
    return loop(lambda: (timezone.now() - datetime.timedelta(days=random.randint(0, 300)).date))


def random_date_string():
    y = random.randint(1900, 2020)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return str(datetime.date(y, m, d))


def random_time_string():
    h = random.randint(0, 23)
    m = random.randint(0, 59)
    s = random.randint(0, 59)
    return str(datetime.time(h, m, s))


def random_date_string_maker(field):
    return loop(random_date_string)


def random_datetime_string():
    h = random.randint(1, 12)
    m = random.randint(0, 59)
    result = DATETIME_TEMPLATE % (random_date_string(), h, m)
    return result


def random_datetime_string_maker(field):
    return loop(random_datetime_string)


def random_decimal_maker(field):
    x = pow(10, field.max_digits - field.decimal_places) - 1
    y = pow(10, field.decimal_places) - 1
    fmt_string = DECIMAL_TEMPLATE % field.decimal_places

    def gen():
        return fmt_string % (random.randint(1, x), random.randint(1, y))

    return loop(gen)


def email_generator(addr, domain):
    template = EMAIL_TEMPLATE % (addr, domain)

    def email_gen_maker(field):
        return sequence(lambda i: template % i)

    return email_gen_maker


def random_integer_maker(field, low=-2147483647, high=2147483647):
    return loop(lambda: random.randint(low, high))


def random_big_integer_maker(field):
    return random_integer_maker(
        field,
        low=-9223372036854775808,
        high=9223372036854775807
    )


def random_small_integer_maker(field):
    return random_integer_maker(field, low=-1, high=1)


def random_small_positive_integer_maker(field):
    return random_integer_maker(field, low=0, high=1)


def random_positive_integer_maker(field):
    return random_integer_maker(field, low=0)


def random_float_maker(field):
    return loop(lambda: random_float())


def random_auto_field_maker(field):
    return loop(lambda: random.randint(1, 2147483647))


def random_float():
    return random.uniform(sys.float_info.min, sys.float_info.max)


def random_ipaddress_maker(field):
    return loop(lambda: "%s.%s.%s.%s" % (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255))
    )


def random_comma_seperated_integer(max_length):
    if max_length is None:
        max_length = DEFAULT_STRING_LENGTH

    max_length = (int)(max_length / 2)
    chars = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    return reduce(
        lambda x, y: "%s,%s" % (x, y),
        random_string(max_length, chars)
    ).lstrip(',')


def random_comma_seperated_integer_maker(field):
    max_length = getattr(field, 'max_length', DEFAULT_STRING_LENGTH)
    return loop(lambda: random_comma_seperated_integer(max_length))


def random_time_string_maker(field):
    return loop(lambda: random_time_string())


def random_rgb():
    return (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
    )


def random_image(field):

    color1 = random_rgb()
    color2 = random_rgb()
    color3 = random_rgb()
    color4 = random_rgb()
    size = (random.randint(300, 900), random.randint(300, 900))

    im = Image.new("RGB", size)  # create the image
    draw = ImageDraw.Draw(im)    # create a drawing object that is
    draw.rectangle(
        [(0, 0), ((size[0] / 2), (size[1] / 2))],
        fill=color1
    )
    draw.rectangle(
        [((size[0] / 2), 0), ((size[1] / 2), size[0])],
        fill=color2
    )
    draw.rectangle(
        [(0, (size[1] / 2)), ((size[0] / 2), size[1])],
        fill=color3
    )
    draw.rectangle(
        [((size[0] / 2), (size[1] / 2)), (size[0], size[1])],
        fill=color4
    )

    filename = "%s.png" % uuid.uuid4().hex[:10]
    filename = field.generate_filename(None, filename)
    storage = DefaultStorage()
    full_path = storage.path(filename)
    directory = os.path.dirname(full_path)

    try:
        os.makedirs(directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    filehandle = storage.open(filename, mode="w")
    im.save(filehandle, "PNG")

    filehandle.close()

    return filename  # and we"re done!


def random_image_maker(field):
    return loop(lambda: random_image(field))

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import sys
from django.core.management import execute_manager

sys.path.append('../')
try:
    from testapp import settings 
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Root(models.Model):
    my_auto = models.AutoField(blank=False, null=False, primary_key=True)
    try:
        my_biginteger = models.BigIntegerField(blank=False, null=False)
    except AttributeError:
        pass
    my_boolean = models.BooleanField(blank=False, null=False)
    my_char = models.CharField(blank=False, null=False, max_length=16)
    my_commaseperatedinteger = models.CommaSeparatedIntegerField(blank=False, null=False, max_length=12)
    my_date = models.DateField(blank=False, null=False)
    my_datetime = models.DateTimeField(blank=False, null=False)
    my_decimal = models.DecimalField(blank=False, null=False, decimal_places=2, max_digits=4)
    my_email = models.EmailField(blank=False, null=False)
    # = models.FileField(blank=False, null=False)
    # = models.FilePathField(blank=False, null=False)
    my_float = models.FloatField(blank=False, null=False)
    # = models.ImageField(blank=False, null=False)
    my_integer = models.IntegerField(blank=False, null=False)
    my_ip = models.IPAddressField(blank=False, null=False)
    my_nullboolean = models.NullBooleanField(blank=False, null=False)
    my_positiveinteger = models.PositiveIntegerField(blank=False, null=False)
    my_positivesmallinteger = models.PositiveSmallIntegerField(blank=False, null=False)
    my_slug = models.SlugField(blank=False, null=False)
    my_smallinteger = models.SmallIntegerField(blank=False, null=False)
    my_text = models.TextField(blank=False, null=False)
    my_time = models.TimeField(blank=False, null=False)
    # = models.URLField(blank=False, null=False)
    # = models.XMLField(blank=False, null=False)

class Child(models.Model):
    name = models.CharField(blank=False, null=False, max_length=16)
    root = models.ForeignKey(Root, blank=False, null=False)

class Sibling(models.Model):
    name = models.CharField(blank=False, null=False, max_length=16)
    root = models.ForeignKey(Root, blank=True, null=True)

class GrandChild(models.Model):
    name = models.CharField(blank=False, null=False, max_length=16)
    parent = models.ForeignKey(Child)

class Uncle(models.Model):
    name = models.CharField(blank=False, null=False, max_length=16)

class Aunt(models.Model):
    name = models.CharField(blank=False, null=False, max_length=16)
    uncles = models.ManyToManyField(Uncle, blank=False, null=False)

class CounselingUncle(models.Model):
    uncle = models.ForeignKey(Uncle)
    cousin = models.ForeignKey("EstrangedChild")
    date_started = models.DateField()

class EstrangedChild(models.Model):
    name = models.CharField(max_length=16)
    uncles = models.ManyToManyField(Uncle, through=CounselingUncle)

class PsychoChild(models.Model):
    name = models.CharField(max_length=16)
    alter_egos = models.ManyToManyField("self")

class AdoptedChild(Child):
    birth_origin = models.CharField(max_length=100)

class ImageChild(Child):
    photo = models.ImageField(upload_to="uploads/")

class LongName(models.Model):
    name = models.CharField(max_length=200)

class ShortName(models.Model):
    name = models.CharField(max_length=100)


########NEW FILE########
__FILENAME__ = settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'mydatabase'
    }
}

ROOT_URLCONF = ''

INSTALLED_APPS = (
    'testapp',
)

########NEW FILE########
__FILENAME__ = tests
import unittest
import types
import sys
import string
from django.db import models
from milkman.dairy import milkman
from milkman.dairy import MilkTruck
from milkman.generators import email_generator, random_choice_iterator, random_string, random_float, random_ipaddress_maker, random_float_maker,random_comma_seperated_integer_maker, random_time_string_maker
from testapp.models import *

MODELS = [Root, Child, Uncle]
class ModelTest(unittest.TestCase):
    def tearDown(self):
        for m in MODELS:
            m._default_manager.all().delete()
    
    def test_create(self):
        r = milkman.deliver(Root)
        self.assertEqual(Root, r.__class__)
        self.assertTrue(bool(r.my_auto))
        assert r.my_char is not None

    def test_create_with_string(self):
        r = milkman.deliver('testapp.Root')
        self.assertEqual(Root, r.__class__)
        self.assertTrue(bool(r.my_auto))
        assert r.my_char is not None

    def test_create_explicit(self):
        r = milkman.deliver(Root, my_char='foo')
        self.assertEqual('foo', r.my_char)

    def test_create_child(self):
        child = milkman.deliver(Child)
        assert child.root
    
    def test_optional_relation(self):
        sibling = milkman.deliver(Sibling)
        self.assertEqual(None, sibling.root)
    
    def test_recurs_on_grandchildren(self):
        gc = milkman.deliver(GrandChild)
        self.assertNotEqual(None, gc.parent.root)

    def test_m2m(self):
        aunt = milkman.deliver(Aunt)
        self.assertEquals(1, len(aunt.uncles.all()))
        self.assertEquals(1, len(Uncle.objects.all()))
        self.assertEquals(Uncle.objects.all()[0], aunt.uncles.all()[0])
    
    def test_m2m_explicit(self):
        uncle = milkman.deliver(Uncle)
        aunt = milkman.deliver(Aunt, uncles=[uncle])
        self.assertEquals(uncle, aunt.uncles.all()[0])
    
    def test_m2m_through_model(self):
        couseling_uncle = milkman.deliver(CounselingUncle)
        self.assertTrue(isinstance(couseling_uncle, CounselingUncle))
        self.assertEquals(couseling_uncle.cousin.uncles.all().count(), 1)
        self.assertTrue(len(couseling_uncle.cousin.name) > 0)
        self.assertTrue(len(couseling_uncle.uncle.name) > 0)
    
    def test_m2m_model(self):
        child = milkman.deliver(EstrangedChild)
        self.assertTrue(isinstance(child, EstrangedChild))
        self.assertEquals(child.uncles.all().count(), 0)
        self.assertTrue(len(child.name) > 0)
    
    def test_m2m_model_explicit_add(self):
        child = milkman.deliver(EstrangedChild)
        couseling_uncle = milkman.deliver(CounselingUncle, cousin=child)
        self.assertTrue(isinstance(child, EstrangedChild))
        self.assertEquals(child.uncles.all().count(), 1)
        self.assertTrue(len(child.name) > 0)
        
    def test_m2m_model_self(self):
        child = milkman.deliver(PsychoChild)
        self.assertEquals(child.alter_egos.all().count(), 1)
        self.assertEquals(PsychoChild.objects.all().count(), 2)

    def test_related_explicit_values(self):
        child = milkman.deliver(Child, root__my_char='foo')
        self.assertEqual(child.root.my_char, 'foo')

        grandchild = milkman.deliver(GrandChild, parent__name='foo', parent__root__my_char='bar')
        self.assertEqual(grandchild.parent.name, 'foo')
        self.assertEqual(grandchild.parent.root.my_char, 'bar')

        root = milkman.deliver(Root)
        grandchild = milkman.deliver(GrandChild, parent__root=root)
        self.assertEqual(root.pk, grandchild.parent.root.pk)

    def test_m2m_related_explicit_values(self):
        aunt = milkman.deliver(Aunt, uncles__name='foo')
        self.assertEqual(1, len(aunt.uncles.all()))
        self.assertEqual(aunt.uncles.all()[0].name, 'foo')

    def test_image_model(self):
        image = milkman.deliver(ImageChild)
        self.assertTrue(len(image.photo.url) > 0)
        self.assertTrue(image.photo.size > 0)



INHERITED_MODELS = [AdoptedChild]
class ModelInheritanceTest(unittest.TestCase):
    def tearDown(self):
        for m in INHERITED_MODELS:
            m._default_manager.all().delete()
    
    def test_create_adopted_child(self):
        a = milkman.deliver(AdoptedChild)
        assert a.root is not None

class RandomFieldTest(unittest.TestCase):
    def test_required_field(self):
        root = milkman.deliver(Root)
        assert isinstance(root.my_auto, int)
        try:
            assert isinstance(root.my_biginteger, type(models.BigIntegerField.MAX_BIGINT))
        except AttributeError:
            pass
        assert isinstance(root.my_boolean, bool)
        assert isinstance(root.my_char, str)
        assert isinstance(root.my_commaseperatedinteger, str)
        assert isinstance(root.my_date, str)
        assert isinstance(root.my_datetime, str)
        assert isinstance(root.my_decimal, str)
        assert isinstance(root.my_email, str)
        assert isinstance(root.my_float, float)
        assert isinstance(root.my_integer, int)
        assert isinstance(root.my_ip, str)
        assert (isinstance(root.my_nullboolean, bool) or isinstance(root.my_nullboolean, types.NoneType))
        assert isinstance(root.my_positiveinteger, int)
        assert isinstance(root.my_positivesmallinteger, int)
        assert isinstance(root.my_slug, str)
        assert isinstance(root.my_smallinteger, int)
        assert isinstance(root.my_text, str)
        assert isinstance(root.my_time, str)
    
class FieldTest(unittest.TestCase):
    def test_needs_generated_value(self):
        f = Root._meta.get_field('my_char')
        assert MilkTruck(None).needs_generated_value(f)
        assert not f.has_default()
        self.assertEqual('', f.get_default())

class FieldValueGeneratorTest(unittest.TestCase):
    def test_email_generator(self):
        f = models.EmailField()
        g = email_generator('test', 'fake.com')(f)()
        self.assertEquals('test1@fake.com', g.next())
        self.assertEquals('test2@fake.com', g.next())

    def test_random_str(self):
        self.assertEqual(8, len(random_string()))
        self.assertEqual('a' * 8, random_string(chars=['a']))
        self.assertEqual('a' * 10, random_string(10, ['a']))
        
    def test_random_choice_iterator(self):
        self.assertEqual([''],[x for x in random_choice_iterator()])
        self.assertEqual([1],[x for x in random_choice_iterator([1])])
        self.assertEqual(['', ''], [s for s in random_choice_iterator(size=2)])
        self.assertEqual([1, 1], [s for s in random_choice_iterator([1], 2)])
        
    def test_random_float(self):
        assert random_float() >= sys.float_info.min
        assert random_float() <= sys.float_info.max
        assert isinstance(random_float(), float)
        
    def test_random_ipaddress(self):
        f = models.IPAddressField()
        ip = random_ipaddress_maker(f)().next()
        ip = ip.split('.')
        self.assertEquals(len(ip), 4)
        
    def test_random_comma_seperated_integer_maker(self):
        f = models.CommaSeparatedIntegerField()
        v = random_comma_seperated_integer_maker(f)().next()
        self.assertEquals(len(v.split(',')), 4)
        
    def test_timefield_maker(self):
        f = models.TimeField()
        v = random_time_string_maker(f)().next()
        times = v.split(':')
        self.assertEquals(len(times), 3)

    def test_field_name_clash(self):
        milkman.deliver(LongName)
        short_name = milkman.deliver(ShortName)

        self.assertEqual(len(short_name.name), 100)


########NEW FILE########
