__FILENAME__ = compatsettings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django-modeltests',
    'django-serializers-regress'
)

SERIALIZATION_MODULES = {
    "xml": "serializers.compat.xml",
    "python": "serializers.compat.python",
    "json": "serializers.compat.json",
    #"yaml": "serializers.compat.yaml"
}

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
"""
42. Serialization

``django.core.serializers`` provides interfaces to converting Django
``QuerySet`` objects to and from "flat" data (i.e. strings).
"""

from decimal import Decimal

from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=20)

    class Meta:
       ordering = ('name',)

    def __unicode__(self):
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=20)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name


class Article(models.Model):
    author = models.ForeignKey(Author)
    headline = models.CharField(max_length=50)
    pub_date = models.DateTimeField()
    categories = models.ManyToManyField(Category)

    class Meta:
       ordering = ('pub_date',)

    def __unicode__(self):
        return self.headline


class AuthorProfile(models.Model):
    author = models.OneToOneField(Author, primary_key=True)
    date_of_birth = models.DateField()

    def __unicode__(self):
        return u"Profile of %s" % self.author


class Actor(models.Model):
    name = models.CharField(max_length=20, primary_key=True)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name


class Movie(models.Model):
    actor = models.ForeignKey(Actor)
    title = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    class Meta:
       ordering = ('title',)

    def __unicode__(self):
        return self.title


class Score(models.Model):
    score = models.FloatField()


class Team(object):
    def __init__(self, title):
        self.title = title

    def __unicode__(self):
        raise NotImplementedError("Not so simple")

    def __str__(self):
        raise NotImplementedError("Not so simple")

    def to_string(self):
        return "%s" % self.title


class TeamField(models.CharField):
    __metaclass__ = models.SubfieldBase

    def __init__(self):
        super(TeamField, self).__init__(max_length=100)

    def get_db_prep_save(self, value, connection):
        return unicode(value.title)

    def to_python(self, value):
        if isinstance(value, Team):
            return value
        return Team(value)

    def value_to_string(self, obj):
        return self._get_val_from_obj(obj).to_string()


class Player(models.Model):
    name = models.CharField(max_length=50)
    rank = models.IntegerField()
    team = TeamField()

    def __unicode__(self):
        return u'%s (%d) playing for %s' % (self.name, self.rank, self.team.to_string())

########NEW FILE########
__FILENAME__ = tests
from __future__ import absolute_import

# -*- coding: utf-8 -*-
import json
from datetime import datetime
from xml.dom import minidom
from StringIO import StringIO

from django.conf import settings
from django.core import serializers
from django.db import transaction, connection
from django.test import TestCase, TransactionTestCase, Approximate
from django.utils import unittest

from .models import (Category, Author, Article, AuthorProfile, Actor, Movie,
    Score, Player, Team)


class SerializerRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.old_SERIALIZATION_MODULES = getattr(settings, 'SERIALIZATION_MODULES', None)
        self.old_serializers = serializers._serializers

        serializers._serializers = {}
        settings.SERIALIZATION_MODULES = {
            "json2" : "django.core.serializers.json",
        }

    def tearDown(self):
        serializers._serializers = self.old_serializers
        if self.old_SERIALIZATION_MODULES:
            settings.SERIALIZATION_MODULES = self.old_SERIALIZATION_MODULES
        else:
            delattr(settings, 'SERIALIZATION_MODULES')

    def test_register(self):
        "Registering a new serializer populates the full registry. Refs #14823"
        serializers.register_serializer('json3', 'django.core.serializers.json')

        public_formats = serializers.get_public_serializer_formats()
        self.assertIn('json3', public_formats)
        self.assertIn('json2', public_formats)
        self.assertIn('xml', public_formats)

    def test_unregister(self):
        "Unregistering a serializer doesn't cause the registry to be repopulated. Refs #14823"
        serializers.unregister_serializer('xml')
        serializers.register_serializer('json3', 'django.core.serializers.json')

        public_formats = serializers.get_public_serializer_formats()

        self.assertNotIn('xml', public_formats)
        self.assertIn('json3', public_formats)

    def test_builtin_serializers(self):
        "Requesting a list of serializer formats popuates the registry"
        all_formats = set(serializers.get_serializer_formats())
        public_formats = set(serializers.get_public_serializer_formats())

        self.assertIn('xml', all_formats),
        self.assertIn('xml', public_formats)

        self.assertIn('json2', all_formats)
        self.assertIn('json2', public_formats)

        self.assertIn('python', all_formats)
        self.assertNotIn('python', public_formats)

class SerializersTestBase(object):
    @staticmethod
    def _comparison_value(value):
        return value

    def setUp(self):
        sports = Category.objects.create(name="Sports")
        music = Category.objects.create(name="Music")
        op_ed = Category.objects.create(name="Op-Ed")

        self.joe = Author.objects.create(name="Joe")
        self.jane = Author.objects.create(name="Jane")

        self.a1 = Article(
            author=self.jane,
            headline="Poker has no place on ESPN",
            pub_date=datetime(2006, 6, 16, 11, 00)
        )
        self.a1.save()
        self.a1.categories = [sports, op_ed]

        self.a2 = Article(
            author=self.joe,
            headline="Time to reform copyright",
            pub_date=datetime(2006, 6, 16, 13, 00, 11, 345)
        )
        self.a2.save()
        self.a2.categories = [music, op_ed]

    def test_serialize(self):
        """Tests that basic serialization works."""
        serial_str = serializers.serialize(self.serializer_name,
                                           Article.objects.all())
        self.assertTrue(self._validate_output(serial_str))

    def test_serializer_roundtrip(self):
        """Tests that serialized content can be deserialized."""
        serial_str = serializers.serialize(self.serializer_name,
                                           Article.objects.all())
        models = list(serializers.deserialize(self.serializer_name, serial_str))
        self.assertEqual(len(models), 2)

    def test_altering_serialized_output(self):
        """
        Tests the ability to create new objects by
        modifying serialized content.
        """
        old_headline = "Poker has no place on ESPN"
        new_headline = "Poker has no place on television"
        serial_str = serializers.serialize(self.serializer_name,
                                           Article.objects.all())
        serial_str = serial_str.replace(old_headline, new_headline)
        models = list(serializers.deserialize(self.serializer_name, serial_str))

        # Prior to saving, old headline is in place
        self.assertTrue(Article.objects.filter(headline=old_headline))
        self.assertFalse(Article.objects.filter(headline=new_headline))

        for model in models:
            model.save()

        # After saving, new headline is in place
        self.assertTrue(Article.objects.filter(headline=new_headline))
        self.assertFalse(Article.objects.filter(headline=old_headline))

    def test_one_to_one_as_pk(self):
        """
        Tests that if you use your own primary key field
        (such as a OneToOneField), it doesn't appear in the
        serialized field list - it replaces the pk identifier.
        """
        profile = AuthorProfile(author=self.joe,
                                date_of_birth=datetime(1970,1,1))
        profile.save()
        serial_str = serializers.serialize(self.serializer_name,
                                           AuthorProfile.objects.all())
        self.assertFalse(self._get_field_values(serial_str, 'author'))

        for obj in serializers.deserialize(self.serializer_name, serial_str):
            self.assertEqual(obj.object.pk, self._comparison_value(self.joe.pk))

    def test_serialize_field_subset(self):
        """Tests that output can be restricted to a subset of fields"""
        valid_fields = ('headline','pub_date')
        invalid_fields = ("author", "categories")
        serial_str = serializers.serialize(self.serializer_name,
                                    Article.objects.all(),
                                    fields=valid_fields)
        for field_name in invalid_fields:
            self.assertFalse(self._get_field_values(serial_str, field_name))

        for field_name in valid_fields:
            self.assertTrue(self._get_field_values(serial_str, field_name))

    def test_serialize_unicode(self):
        """Tests that unicode makes the roundtrip intact"""
        actor_name = u"Za\u017c\u00f3\u0142\u0107"
        movie_title = u'G\u0119\u015bl\u0105 ja\u017a\u0144'
        ac = Actor(name=actor_name)
        mv = Movie(title=movie_title, actor=ac)
        ac.save()
        mv.save()

        serial_str = serializers.serialize(self.serializer_name, [mv])
        self.assertEqual(self._get_field_values(serial_str, "title")[0], movie_title)
        self.assertEqual(self._get_field_values(serial_str, "actor")[0], actor_name)

        obj_list = list(serializers.deserialize(self.serializer_name, serial_str))
        mv_obj = obj_list[0].object
        self.assertEqual(mv_obj.title, movie_title)

    def test_serialize_superfluous_queries(self):
        """Ensure no superfluous queries are made when serializing ForeignKeys

        #17602
        """
        ac = Actor(name='Actor name')
        ac.save()
        mv = Movie(title='Movie title', actor_id=ac.pk)
        mv.save()

        with self.assertNumQueries(0):
            serial_str = serializers.serialize(self.serializer_name, [mv])

    def test_serialize_with_null_pk(self):
        """
        Tests that serialized data with no primary key results
        in a model instance with no id
        """
        category = Category(name="Reference")
        serial_str = serializers.serialize(self.serializer_name, [category])
        pk_value = self._get_pk_values(serial_str)[0]
        self.assertFalse(pk_value)

        cat_obj = list(serializers.deserialize(self.serializer_name,
                                               serial_str))[0].object
        self.assertEqual(cat_obj.id, None)

    def test_float_serialization(self):
        """Tests that float values serialize and deserialize intact"""
        sc = Score(score=3.4)
        sc.save()
        serial_str = serializers.serialize(self.serializer_name, [sc])
        deserial_objs = list(serializers.deserialize(self.serializer_name,
                                                serial_str))
        self.assertEqual(deserial_objs[0].object.score, Approximate(3.4, places=1))

    def test_custom_field_serialization(self):
        """Tests that custom fields serialize and deserialize intact"""
        team_str = "Spartak Moskva"
        player = Player()
        player.name = "Soslan Djanaev"
        player.rank = 1
        player.team = Team(team_str)
        player.save()
        serial_str = serializers.serialize(self.serializer_name,
                                           Player.objects.all())
        team = self._get_field_values(serial_str, "team")
        self.assertTrue(team)
        self.assertEqual(team[0], team_str)

        deserial_objs = list(serializers.deserialize(self.serializer_name, serial_str))
        self.assertEqual(deserial_objs[0].object.team.to_string(),
                         player.team.to_string())

    def test_pre_1000ad_date(self):
        """Tests that year values before 1000AD are properly formatted"""
        # Regression for #12524 -- dates before 1000AD get prefixed
        # 0's on the year
        a = Article.objects.create(
        author = self.jane,
        headline = "Nobody remembers the early years",
        pub_date = datetime(1, 2, 3, 4, 5, 6))

        serial_str = serializers.serialize(self.serializer_name, [a])
        date_values = self._get_field_values(serial_str, "pub_date")
        self.assertEqual(date_values[0].replace('T', ' '), "0001-02-03 04:05:06")

    def test_pkless_serialized_strings(self):
        """
        Tests that serialized strings without PKs
        can be turned into models
        """
        deserial_objs = list(serializers.deserialize(self.serializer_name,
                                                     self.pkless_str))
        for obj in deserial_objs:
            self.assertFalse(obj.object.id)
            obj.save()
        self.assertEqual(Category.objects.all().count(), 4)


class SerializersTransactionTestBase(object):
    def test_forward_refs(self):
        """
        Tests that objects ids can be referenced before they are
        defined in the serialization data.
        """
        # The deserialization process needs to be contained
        # within a transaction in order to test forward reference
        # handling.
        transaction.enter_transaction_management()
        transaction.managed(True)
        objs = serializers.deserialize(self.serializer_name, self.fwd_ref_str)
        with connection.constraint_checks_disabled():
            for obj in objs:
                obj.save()
        transaction.commit()
        transaction.leave_transaction_management()

        for model_cls in (Category, Author, Article):
            self.assertEqual(model_cls.objects.all().count(), 1)
        art_obj = Article.objects.all()[0]
        self.assertEqual(art_obj.categories.all().count(), 1)
        self.assertEqual(art_obj.author.name, "Agnes")


class XmlSerializerTestCase(SerializersTestBase, TestCase):
    serializer_name = "xml"
    pkless_str = """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
    <object model="django-modeltests.category">
        <field type="CharField" name="name">Reference</field>
    </object>
</django-objects>"""

    @staticmethod
    def _comparison_value(value):
        # The XML serializer handles everything as strings, so comparisons
        # need to be performed on the stringified value
        return unicode(value)

    @staticmethod
    def _validate_output(serial_str):
        try:
            minidom.parseString(serial_str)
        except Exception:
            return False
        else:
            return True

    @staticmethod
    def _get_pk_values(serial_str):
        ret_list = []
        dom = minidom.parseString(serial_str)
        fields = dom.getElementsByTagName("object")
        for field in fields:
            ret_list.append(field.getAttribute("pk"))
        return ret_list

    @staticmethod
    def _get_field_values(serial_str, field_name):
        ret_list = []
        dom = minidom.parseString(serial_str)
        fields = dom.getElementsByTagName("field")
        for field in fields:
            if field.getAttribute("name") == field_name:
                temp = []
                for child in field.childNodes:
                    temp.append(child.nodeValue)
                ret_list.append("".join(temp))
        return ret_list

class XmlSerializerTransactionTestCase(SerializersTransactionTestBase, TransactionTestCase):
    serializer_name = "xml"
    fwd_ref_str = """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
    <object pk="1" model="django-modeltests.article">
        <field to="django-modeltests.author" name="author" rel="ManyToOneRel">1</field>
        <field type="CharField" name="headline">Forward references pose no problem</field>
        <field type="DateTimeField" name="pub_date">2006-06-16T15:00:00</field>
        <field to="django-modeltests.category" name="categories" rel="ManyToManyRel">
            <object pk="1"></object>
        </field>
    </object>
    <object pk="1" model="django-modeltests.author">
        <field type="CharField" name="name">Agnes</field>
    </object>
    <object pk="1" model="django-modeltests.category">
        <field type="CharField" name="name">Reference</field></object>
</django-objects>"""


class JsonSerializerTestCase(SerializersTestBase, TestCase):
    serializer_name = "json"
    pkless_str = """[{"pk": null, "model": "django-modeltests.category", "fields": {"name": "Reference"}}]"""

    @staticmethod
    def _validate_output(serial_str):
        try:
            json.loads(serial_str)
        except Exception:
            return False
        else:
            return True

    @staticmethod
    def _get_pk_values(serial_str):
        ret_list = []
        serial_list = json.loads(serial_str)
        for obj_dict in serial_list:
            ret_list.append(obj_dict["pk"])
        return ret_list

    @staticmethod
    def _get_field_values(serial_str, field_name):
        ret_list = []
        serial_list = json.loads(serial_str)
        for obj_dict in serial_list:
            if field_name in obj_dict["fields"]:
                ret_list.append(obj_dict["fields"][field_name])
        return ret_list

class JsonSerializerTransactionTestCase(SerializersTransactionTestBase, TransactionTestCase):
    serializer_name = "json"
    fwd_ref_str = """[
    {
        "pk": 1,
        "model": "django-modeltests.article",
        "fields": {
            "headline": "Forward references pose no problem",
            "pub_date": "2006-06-16T15:00:00",
            "categories": [1],
            "author": 1
        }
    },
    {
        "pk": 1,
        "model": "django-modeltests.category",
        "fields": {
            "name": "Reference"
        }
    },
    {
        "pk": 1,
        "model": "django-modeltests.author",
        "fields": {
            "name": "Agnes"
        }
    }]"""

try:
    import yaml
except ImportError:
    pass
else:
    class YamlSerializerTestCase(SerializersTestBase, TestCase):
        serializer_name = "yaml"
        fwd_ref_str = """- fields:
    headline: Forward references pose no problem
    pub_date: 2006-06-16 15:00:00
    categories: [1]
    author: 1
  pk: 1
  model: django-modeltests.article
- fields:
    name: Reference
  pk: 1
  model: django-modeltests.category
- fields:
    name: Agnes
  pk: 1
  model: django-modeltests.author"""

        pkless_str = """- fields:
    name: Reference
  pk: null
  model: django-modeltests.category"""

        @staticmethod
        def _validate_output(serial_str):
            try:
                yaml.safe_load(StringIO(serial_str))
            except Exception:
                return False
            else:
                return True

        @staticmethod
        def _get_pk_values(serial_str):
            ret_list = []
            stream = StringIO(serial_str)
            for obj_dict in yaml.safe_load(stream):
                ret_list.append(obj_dict["pk"])
            return ret_list

        @staticmethod
        def _get_field_values(serial_str, field_name):
            ret_list = []
            stream = StringIO(serial_str)
            for obj_dict in yaml.safe_load(stream):
                if "fields" in obj_dict and field_name in obj_dict["fields"]:
                    field_value = obj_dict["fields"][field_name]
                    # yaml.safe_load will return non-string objects for some
                    # of the fields we are interested in, this ensures that
                    # everything comes back as a string
                    if isinstance(field_value, basestring):
                        ret_list.append(field_value)
                    else:
                        ret_list.append(str(field_value))
            return ret_list

    class YamlSerializerTransactionTestCase(SerializersTransactionTestBase, TransactionTestCase):
        serializer_name = "yaml"
        fwd_ref_str = """- fields:
    headline: Forward references pose no problem
    pub_date: 2006-06-16 15:00:00
    categories: [1]
    author: 1
  pk: 1
  model: django-modeltests.article
- fields:
    name: Reference
  pk: 1
  model: django-modeltests.category
- fields:
    name: Agnes
  pk: 1
  model: django-modeltests.author"""

########NEW FILE########
__FILENAME__ = models
"""
A test spanning all the capabilities of all the serializers.

This class sets up a model for each model field type
(except for image types, because of the PIL dependency).
"""

from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.localflavor.us.models import USStateField, PhoneNumberField

# The following classes are for testing basic data
# marshalling, including NULL values, where allowed.

class BooleanData(models.Model):
    data = models.BooleanField()

class CharData(models.Model):
    data = models.CharField(max_length=30, null=True)

class DateData(models.Model):
    data = models.DateField(null=True)

class DateTimeData(models.Model):
    data = models.DateTimeField(null=True)

class DecimalData(models.Model):
    data = models.DecimalField(null=True, decimal_places=3, max_digits=5)

class EmailData(models.Model):
    data = models.EmailField(null=True)

class FileData(models.Model):
    data = models.FileField(null=True, upload_to='/foo/bar')

class FilePathData(models.Model):
    data = models.FilePathField(null=True)

class FloatData(models.Model):
    data = models.FloatField(null=True)

class IntegerData(models.Model):
    data = models.IntegerField(null=True)

class BigIntegerData(models.Model):
    data = models.BigIntegerField(null=True)

# class ImageData(models.Model):
#    data = models.ImageField(null=True)

class IPAddressData(models.Model):
    data = models.IPAddressField(null=True)

class GenericIPAddressData(models.Model):
    data = models.GenericIPAddressField(null=True)

class NullBooleanData(models.Model):
    data = models.NullBooleanField(null=True)

class PhoneData(models.Model):
    data = PhoneNumberField(null=True)

class PositiveIntegerData(models.Model):
    data = models.PositiveIntegerField(null=True)

class PositiveSmallIntegerData(models.Model):
    data = models.PositiveSmallIntegerField(null=True)

class SlugData(models.Model):
    data = models.SlugField(null=True)

class SmallData(models.Model):
    data = models.SmallIntegerField(null=True)

class TextData(models.Model):
    data = models.TextField(null=True)

class TimeData(models.Model):
    data = models.TimeField(null=True)

class USStateData(models.Model):
    data = USStateField(null=True)

class Tag(models.Model):
    """A tag on an item."""
    data = models.SlugField()
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()

    content_object = generic.GenericForeignKey()

    class Meta:
        ordering = ["data"]

class GenericData(models.Model):
    data = models.CharField(max_length=30)

    tags = generic.GenericRelation(Tag)

# The following test classes are all for validation
# of related objects; in particular, forward, backward,
# and self references.

class Anchor(models.Model):
    """This is a model that can be used as
    something for other models to point at"""

    data = models.CharField(max_length=30)

    class Meta:
        ordering = ('id',)

class NaturalKeyAnchorManager(models.Manager):
    def get_by_natural_key(self, data):
        return self.get(data=data)

class NaturalKeyAnchor(models.Model):
    objects = NaturalKeyAnchorManager()

    data = models.CharField(max_length=100, unique=True)

    def natural_key(self):
        return (self.data,)

class UniqueAnchor(models.Model):
    """This is a model that can be used as
    something for other models to point at"""

    data = models.CharField(unique=True, max_length=30)

class FKData(models.Model):
    data = models.ForeignKey(Anchor, null=True)

class FKDataNaturalKey(models.Model):
    data = models.ForeignKey(NaturalKeyAnchor, null=True)

class M2MData(models.Model):
    data = models.ManyToManyField(Anchor, null=True)

class O2OData(models.Model):
    # One to one field can't be null here, since it is a PK.
    data = models.OneToOneField(Anchor, primary_key=True)

class FKSelfData(models.Model):
    data = models.ForeignKey('self', null=True)

class M2MSelfData(models.Model):
    data = models.ManyToManyField('self', null=True, symmetrical=False)

class FKDataToField(models.Model):
    data = models.ForeignKey(UniqueAnchor, null=True, to_field='data')

class FKDataToO2O(models.Model):
    data = models.ForeignKey(O2OData, null=True)

class M2MIntermediateData(models.Model):
    data = models.ManyToManyField(Anchor, null=True, through='Intermediate')

class Intermediate(models.Model):
    left = models.ForeignKey(M2MIntermediateData)
    right = models.ForeignKey(Anchor)
    extra = models.CharField(max_length=30, blank=True, default="doesn't matter")

# The following test classes are for validating the
# deserialization of objects that use a user-defined
# field as the primary key.
# Some of these data types have been commented out
# because they can't be used as a primary key on one
# or all database backends.

class BooleanPKData(models.Model):
    data = models.BooleanField(primary_key=True)

class CharPKData(models.Model):
    data = models.CharField(max_length=30, primary_key=True)

# class DatePKData(models.Model):
#    data = models.DateField(primary_key=True)

# class DateTimePKData(models.Model):
#    data = models.DateTimeField(primary_key=True)

class DecimalPKData(models.Model):
    data = models.DecimalField(primary_key=True, decimal_places=3, max_digits=5)

class EmailPKData(models.Model):
    data = models.EmailField(primary_key=True)

# class FilePKData(models.Model):
#    data = models.FileField(primary_key=True, upload_to='/foo/bar')

class FilePathPKData(models.Model):
    data = models.FilePathField(primary_key=True)

class FloatPKData(models.Model):
    data = models.FloatField(primary_key=True)

class IntegerPKData(models.Model):
    data = models.IntegerField(primary_key=True)

# class ImagePKData(models.Model):
#    data = models.ImageField(primary_key=True)

class IPAddressPKData(models.Model):
    data = models.IPAddressField(primary_key=True)

class GenericIPAddressPKData(models.Model):
    data = models.GenericIPAddressField(primary_key=True)

# This is just a Boolean field with null=True, and we can't test a PK value of NULL.
# class NullBooleanPKData(models.Model):
#     data = models.NullBooleanField(primary_key=True)

class PhonePKData(models.Model):
    data = PhoneNumberField(primary_key=True)

class PositiveIntegerPKData(models.Model):
    data = models.PositiveIntegerField(primary_key=True)

class PositiveSmallIntegerPKData(models.Model):
    data = models.PositiveSmallIntegerField(primary_key=True)

class SlugPKData(models.Model):
    data = models.SlugField(primary_key=True)

class SmallPKData(models.Model):
    data = models.SmallIntegerField(primary_key=True)

# class TextPKData(models.Model):
#     data = models.TextField(primary_key=True)

# class TimePKData(models.Model):
#    data = models.TimeField(primary_key=True)

class USStatePKData(models.Model):
    data = USStateField(primary_key=True)

class ComplexModel(models.Model):
    field1 = models.CharField(max_length=10)
    field2 = models.CharField(max_length=10)
    field3 = models.CharField(max_length=10)

# Tests for handling fields with pre_save functions, or
# models with save functions that modify data
class AutoNowDateTimeData(models.Model):
    data = models.DateTimeField(null=True, auto_now=True)

class ModifyingSaveData(models.Model):
    data = models.IntegerField(null=True)

    def save(self):
        "A save method that modifies the data in the object"
        self.data = 666
        super(ModifyingSaveData, self).save(raw)

# Tests for serialization of models using inheritance.
# Regression for #7202, #7350
class AbstractBaseModel(models.Model):
    parent_data = models.IntegerField()
    class Meta:
        abstract = True

class InheritAbstractModel(AbstractBaseModel):
    child_data = models.IntegerField()

class BaseModel(models.Model):
    parent_data = models.IntegerField()

class InheritBaseModel(BaseModel):
    child_data = models.IntegerField()

class ExplicitInheritBaseModel(BaseModel):
    parent = models.OneToOneField(BaseModel)
    child_data = models.IntegerField()

class ProxyBaseModel(BaseModel):
    class Meta:
        proxy = True

class ProxyProxyBaseModel(ProxyBaseModel):
    class Meta:
        proxy = True

class LengthModel(models.Model):
    data = models.IntegerField()

    def __len__(self):
        return self.data


########NEW FILE########
__FILENAME__ = tests
"""
A test spanning all the capabilities of all the serializers.

This class defines sample data and a dynamically generated
test case that is capable of testing the capabilities of
the serializers. This includes all valid data values, plus
forward, backwards and self references.
"""
from __future__ import absolute_import

import datetime
import decimal
from io import BytesIO

try:
    import yaml
except ImportError:
    yaml = None

from django.core import serializers
from django.core.serializers import SerializerDoesNotExist
from django.core.serializers.base import DeserializationError
from django.db import connection, models
from django.test import TestCase
from django.utils.functional import curry
from django.utils.unittest import skipUnless

from .models import (BooleanData, CharData, DateData, DateTimeData, EmailData,
    FileData, FilePathData, DecimalData, FloatData, IntegerData, IPAddressData,
    GenericIPAddressData, NullBooleanData, PhoneData, PositiveIntegerData,
    PositiveSmallIntegerData, SlugData, SmallData, TextData, TimeData,
    USStateData, GenericData, Anchor, UniqueAnchor, FKData, M2MData, O2OData,
    FKSelfData, M2MSelfData, FKDataToField, FKDataToO2O, M2MIntermediateData,
    Intermediate, BooleanPKData, CharPKData, EmailPKData, FilePathPKData,
    DecimalPKData, FloatPKData, IntegerPKData, IPAddressPKData,
    GenericIPAddressPKData, PhonePKData, PositiveIntegerPKData,
    PositiveSmallIntegerPKData, SlugPKData, SmallPKData, USStatePKData,
    AutoNowDateTimeData, ModifyingSaveData, InheritAbstractModel, BaseModel,
    ExplicitInheritBaseModel, InheritBaseModel, ProxyBaseModel,
    ProxyProxyBaseModel, BigIntegerData, LengthModel, Tag, ComplexModel,
    NaturalKeyAnchor, FKDataNaturalKey)

# A set of functions that can be used to recreate
# test data objects of various kinds.
# The save method is a raw base model save, to make
# sure that the data in the database matches the
# exact test case.
def data_create(pk, klass, data):
    instance = klass(id=pk)
    instance.data = data
    models.Model.save_base(instance, raw=True)
    return [instance]

def generic_create(pk, klass, data):
    instance = klass(id=pk)
    instance.data = data[0]
    models.Model.save_base(instance, raw=True)
    for tag in data[1:]:
        instance.tags.create(data=tag)
    return [instance]

def fk_create(pk, klass, data):
    instance = klass(id=pk)
    setattr(instance, 'data_id', data)
    models.Model.save_base(instance, raw=True)
    return [instance]

def m2m_create(pk, klass, data):
    instance = klass(id=pk)
    models.Model.save_base(instance, raw=True)
    instance.data = data
    return [instance]

def im2m_create(pk, klass, data):
    instance = klass(id=pk)
    models.Model.save_base(instance, raw=True)
    return [instance]

def im_create(pk, klass, data):
    instance = klass(id=pk)
    instance.right_id = data['right']
    instance.left_id = data['left']
    if 'extra' in data:
        instance.extra = data['extra']
    models.Model.save_base(instance, raw=True)
    return [instance]

def o2o_create(pk, klass, data):
    instance = klass()
    instance.data_id = data
    models.Model.save_base(instance, raw=True)
    return [instance]

def pk_create(pk, klass, data):
    instance = klass()
    instance.data = data
    models.Model.save_base(instance, raw=True)
    return [instance]

def inherited_create(pk, klass, data):
    instance = klass(id=pk,**data)
    # This isn't a raw save because:
    #  1) we're testing inheritance, not field behavior, so none
    #     of the field values need to be protected.
    #  2) saving the child class and having the parent created
    #     automatically is easier than manually creating both.
    models.Model.save(instance)
    created = [instance]
    for klass,field in instance._meta.parents.items():
        created.append(klass.objects.get(id=pk))
    return created

# A set of functions that can be used to compare
# test data objects of various kinds
def data_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    testcase.assertEqual(data, instance.data,
         "Objects with PK=%d not equal; expected '%s' (%s), got '%s' (%s)" % (
            pk, data, type(data), instance.data, type(instance.data))
    )

def generic_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    testcase.assertEqual(data[0], instance.data)
    testcase.assertEqual(data[1:], [t.data for t in instance.tags.order_by('id')])

def fk_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    testcase.assertEqual(data, instance.data_id)

def m2m_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    testcase.assertEqual(data, [obj.id for obj in instance.data.order_by('id')])

def im2m_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    #actually nothing else to check, the instance just should exist

def im_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    testcase.assertEqual(data['left'], instance.left_id)
    testcase.assertEqual(data['right'], instance.right_id)
    if 'extra' in data:
        testcase.assertEqual(data['extra'], instance.extra)
    else:
        testcase.assertEqual("doesn't matter", instance.extra)

def o2o_compare(testcase, pk, klass, data):
    instance = klass.objects.get(data=data)
    testcase.assertEqual(data, instance.data_id)

def pk_compare(testcase, pk, klass, data):
    instance = klass.objects.get(data=data)
    testcase.assertEqual(data, instance.data)

def inherited_compare(testcase, pk, klass, data):
    instance = klass.objects.get(id=pk)
    for key,value in data.items():
        testcase.assertEqual(value, getattr(instance,key))

# Define some data types. Each data type is
# actually a pair of functions; one to create
# and one to compare objects of that type
data_obj = (data_create, data_compare)
generic_obj = (generic_create, generic_compare)
fk_obj = (fk_create, fk_compare)
m2m_obj = (m2m_create, m2m_compare)
im2m_obj = (im2m_create, im2m_compare)
im_obj = (im_create, im_compare)
o2o_obj = (o2o_create, o2o_compare)
pk_obj = (pk_create, pk_compare)
inherited_obj = (inherited_create, inherited_compare)

test_data = [
    # Format: (data type, PK value, Model Class, data)
    (data_obj, 1, BooleanData, True),
    (data_obj, 2, BooleanData, False),
    (data_obj, 10, CharData, "Test Char Data"),
    (data_obj, 11, CharData, ""),
    (data_obj, 12, CharData, "None"),
    (data_obj, 13, CharData, "null"),
    (data_obj, 14, CharData, "NULL"),
    (data_obj, 15, CharData, None),
    # (We use something that will fit into a latin1 database encoding here,
    # because that is still the default used on many system setups.)
    (data_obj, 16, CharData, u'\xa5'),
    (data_obj, 20, DateData, datetime.date(2006,6,16)),
    (data_obj, 21, DateData, None),
    (data_obj, 30, DateTimeData, datetime.datetime(2006,6,16,10,42,37)),
    (data_obj, 31, DateTimeData, None),
    (data_obj, 40, EmailData, "hovercraft@example.com"),
    (data_obj, 41, EmailData, None),
    (data_obj, 42, EmailData, ""),
    (data_obj, 50, FileData, 'file:///foo/bar/whiz.txt'),
#     (data_obj, 51, FileData, None),
    (data_obj, 52, FileData, ""),
    (data_obj, 60, FilePathData, "/foo/bar/whiz.txt"),
    (data_obj, 61, FilePathData, None),
    (data_obj, 62, FilePathData, ""),
    (data_obj, 70, DecimalData, decimal.Decimal('12.345')),
    (data_obj, 71, DecimalData, decimal.Decimal('-12.345')),
    (data_obj, 72, DecimalData, decimal.Decimal('0.0')),
    (data_obj, 73, DecimalData, None),
    (data_obj, 74, FloatData, 12.345),
    (data_obj, 75, FloatData, -12.345),
    (data_obj, 76, FloatData, 0.0),
    (data_obj, 77, FloatData, None),
    (data_obj, 80, IntegerData, 123456789),
    (data_obj, 81, IntegerData, -123456789),
    (data_obj, 82, IntegerData, 0),
    (data_obj, 83, IntegerData, None),
    #(XX, ImageData
    (data_obj, 90, IPAddressData, "127.0.0.1"),
    (data_obj, 91, IPAddressData, None),
    (data_obj, 95, GenericIPAddressData, "fe80:1424:2223:6cff:fe8a:2e8a:2151:abcd"),
    (data_obj, 96, GenericIPAddressData, None),
    (data_obj, 100, NullBooleanData, True),
    (data_obj, 101, NullBooleanData, False),
    (data_obj, 102, NullBooleanData, None),
    (data_obj, 110, PhoneData, "212-634-5789"),
    (data_obj, 111, PhoneData, None),
    (data_obj, 120, PositiveIntegerData, 123456789),
    (data_obj, 121, PositiveIntegerData, None),
    (data_obj, 130, PositiveSmallIntegerData, 12),
    (data_obj, 131, PositiveSmallIntegerData, None),
    (data_obj, 140, SlugData, "this-is-a-slug"),
    (data_obj, 141, SlugData, None),
    (data_obj, 142, SlugData, ""),
    (data_obj, 150, SmallData, 12),
    (data_obj, 151, SmallData, -12),
    (data_obj, 152, SmallData, 0),
    (data_obj, 153, SmallData, None),
    (data_obj, 160, TextData, """This is a long piece of text.
It contains line breaks.
Several of them.
The end."""),
    (data_obj, 161, TextData, ""),
    (data_obj, 162, TextData, None),
    (data_obj, 170, TimeData, datetime.time(10,42,37)),
    (data_obj, 171, TimeData, None),
    (data_obj, 180, USStateData, "MA"),
    (data_obj, 181, USStateData, None),
    (data_obj, 182, USStateData, ""),

    (generic_obj, 200, GenericData, ['Generic Object 1', 'tag1', 'tag2']),
    (generic_obj, 201, GenericData, ['Generic Object 2', 'tag2', 'tag3']),

    (data_obj, 300, Anchor, "Anchor 1"),
    (data_obj, 301, Anchor, "Anchor 2"),
    (data_obj, 302, UniqueAnchor, "UAnchor 1"),

    (fk_obj, 400, FKData, 300), # Post reference
    (fk_obj, 401, FKData, 500), # Pre reference
    (fk_obj, 402, FKData, None), # Empty reference

    (m2m_obj, 410, M2MData, []), # Empty set
    (m2m_obj, 411, M2MData, [300,301]), # Post reference
    (m2m_obj, 412, M2MData, [500,501]), # Pre reference
    (m2m_obj, 413, M2MData, [300,301,500,501]), # Pre and Post reference

    (o2o_obj, None, O2OData, 300), # Post reference
    (o2o_obj, None, O2OData, 500), # Pre reference

    (fk_obj, 430, FKSelfData, 431), # Pre reference
    (fk_obj, 431, FKSelfData, 430), # Post reference
    (fk_obj, 432, FKSelfData, None), # Empty reference

    (m2m_obj, 440, M2MSelfData, []),
    (m2m_obj, 441, M2MSelfData, []),
    (m2m_obj, 442, M2MSelfData, [440, 441]),
    (m2m_obj, 443, M2MSelfData, [445, 446]),
    (m2m_obj, 444, M2MSelfData, [440, 441, 445, 446]),
    (m2m_obj, 445, M2MSelfData, []),
    (m2m_obj, 446, M2MSelfData, []),

    (fk_obj, 450, FKDataToField, "UAnchor 1"),
    (fk_obj, 451, FKDataToField, "UAnchor 2"),
    (fk_obj, 452, FKDataToField, None),

    (fk_obj, 460, FKDataToO2O, 300),

    (im2m_obj, 470, M2MIntermediateData, None),

    #testing post- and prereferences and extra fields
    (im_obj, 480, Intermediate, {'right': 300, 'left': 470}),
    (im_obj, 481, Intermediate, {'right': 300, 'left': 490}),
    (im_obj, 482, Intermediate, {'right': 500, 'left': 470}),
    (im_obj, 483, Intermediate, {'right': 500, 'left': 490}),
    (im_obj, 484, Intermediate, {'right': 300, 'left': 470, 'extra': "extra"}),
    (im_obj, 485, Intermediate, {'right': 300, 'left': 490, 'extra': "extra"}),
    (im_obj, 486, Intermediate, {'right': 500, 'left': 470, 'extra': "extra"}),
    (im_obj, 487, Intermediate, {'right': 500, 'left': 490, 'extra': "extra"}),

    (im2m_obj, 490, M2MIntermediateData, []),

    (data_obj, 500, Anchor, "Anchor 3"),
    (data_obj, 501, Anchor, "Anchor 4"),
    (data_obj, 502, UniqueAnchor, "UAnchor 2"),

    (pk_obj, 601, BooleanPKData, True),
    (pk_obj, 602, BooleanPKData, False),
    (pk_obj, 610, CharPKData, "Test Char PKData"),
#     (pk_obj, 620, DatePKData, datetime.date(2006,6,16)),
#     (pk_obj, 630, DateTimePKData, datetime.datetime(2006,6,16,10,42,37)),
    (pk_obj, 640, EmailPKData, "hovercraft@example.com"),
#     (pk_obj, 650, FilePKData, 'file:///foo/bar/whiz.txt'),
    (pk_obj, 660, FilePathPKData, "/foo/bar/whiz.txt"),
    (pk_obj, 670, DecimalPKData, decimal.Decimal('12.345')),
    (pk_obj, 671, DecimalPKData, decimal.Decimal('-12.345')),
    (pk_obj, 672, DecimalPKData, decimal.Decimal('0.0')),
    (pk_obj, 673, FloatPKData, 12.345),
    (pk_obj, 674, FloatPKData, -12.345),
    (pk_obj, 675, FloatPKData, 0.0),
    (pk_obj, 680, IntegerPKData, 123456789),
    (pk_obj, 681, IntegerPKData, -123456789),
    (pk_obj, 682, IntegerPKData, 0),
#     (XX, ImagePKData
    (pk_obj, 690, IPAddressPKData, "127.0.0.1"),
    (pk_obj, 695, GenericIPAddressPKData, "fe80:1424:2223:6cff:fe8a:2e8a:2151:abcd"),
    # (pk_obj, 700, NullBooleanPKData, True),
    # (pk_obj, 701, NullBooleanPKData, False),
    (pk_obj, 710, PhonePKData, "212-634-5789"),
    (pk_obj, 720, PositiveIntegerPKData, 123456789),
    (pk_obj, 730, PositiveSmallIntegerPKData, 12),
    (pk_obj, 740, SlugPKData, "this-is-a-slug"),
    (pk_obj, 750, SmallPKData, 12),
    (pk_obj, 751, SmallPKData, -12),
    (pk_obj, 752, SmallPKData, 0),
#     (pk_obj, 760, TextPKData, """This is a long piece of text.
# It contains line breaks.
# Several of them.
# The end."""),
#    (pk_obj, 770, TimePKData, datetime.time(10,42,37)),
    (pk_obj, 780, USStatePKData, "MA"),
#     (pk_obj, 790, XMLPKData, "<foo></foo>"),

    (data_obj, 800, AutoNowDateTimeData, datetime.datetime(2006,6,16,10,42,37)),
    (data_obj, 810, ModifyingSaveData, 42),

    (inherited_obj, 900, InheritAbstractModel, {'child_data':37,'parent_data':42}),
    (inherited_obj, 910, ExplicitInheritBaseModel, {'child_data':37,'parent_data':42}),
    (inherited_obj, 920, InheritBaseModel, {'child_data':37,'parent_data':42}),

    (data_obj, 1000, BigIntegerData, 9223372036854775807),
    (data_obj, 1001, BigIntegerData, -9223372036854775808),
    (data_obj, 1002, BigIntegerData, 0),
    (data_obj, 1003, BigIntegerData, None),
    (data_obj, 1004, LengthModel, 0),
    (data_obj, 1005, LengthModel, 1),
]

natural_key_test_data = [
    (data_obj, 1100, NaturalKeyAnchor, "Natural Key Anghor"),
    (fk_obj, 1101, FKDataNaturalKey, 1100),
    (fk_obj, 1102, FKDataNaturalKey, None),
]

# Because Oracle treats the empty string as NULL, Oracle is expected to fail
# when field.empty_strings_allowed is True and the value is None; skip these
# tests.
if connection.features.interprets_empty_strings_as_nulls:
    test_data = [data for data in test_data
                 if not (data[0] == data_obj and
                         data[2]._meta.get_field('data').empty_strings_allowed and
                         data[3] is None)]

# Regression test for #8651 -- a FK to an object iwth PK of 0
# This won't work on MySQL since it won't let you create an object
# with a primary key of 0,
if connection.features.allows_primary_key_0:
    test_data.extend([
        (data_obj, 0, Anchor, "Anchor 0"),
        (fk_obj, 465, FKData, 0),
    ])

# Dynamically create serializer tests to ensure that all
# registered serializers are automatically tested.
class SerializerTests(TestCase):
    def test_get_unknown_serializer(self):
        """
        #15889: get_serializer('nonsense') raises a SerializerDoesNotExist
        """
        with self.assertRaises(SerializerDoesNotExist):
            serializers.get_serializer("nonsense")

        with self.assertRaises(KeyError):
            serializers.get_serializer("nonsense")

        # SerializerDoesNotExist is instantiated with the nonexistent format
        with self.assertRaises(SerializerDoesNotExist) as cm:
            serializers.get_serializer("nonsense")
        self.assertEqual(cm.exception.args, ("nonsense",))

    def test_unregister_unkown_serializer(self):
        with self.assertRaises(SerializerDoesNotExist):
            serializers.unregister_serializer("nonsense")

    def test_get_unkown_deserializer(self):
        with self.assertRaises(SerializerDoesNotExist):
            serializers.get_deserializer("nonsense")

    def test_json_deserializer_exception(self):
        with self.assertRaises(DeserializationError):
            for obj in serializers.deserialize("json", """[{"pk":1}"""):
                pass

    @skipUnless(yaml, "PyYAML not installed")
    def test_yaml_deserializer_exception(self):
        with self.assertRaises(DeserializationError):
            for obj in serializers.deserialize("yaml", "{"):
                pass

    def test_serialize_proxy_model(self):
        BaseModel.objects.create(parent_data=1)
        base_objects = BaseModel.objects.all()
        proxy_objects = ProxyBaseModel.objects.all()
        proxy_proxy_objects = ProxyProxyBaseModel.objects.all()
        base_data = serializers.serialize("json", base_objects)
        proxy_data = serializers.serialize("json", proxy_objects)
        proxy_proxy_data = serializers.serialize("json", proxy_proxy_objects)
        self.assertEqual(base_data, proxy_data.replace('proxy', ''))
        self.assertEqual(base_data, proxy_proxy_data.replace('proxy', ''))


def serializerTest(format, self):

    # Create all the objects defined in the test data
    objects = []
    instance_count = {}
    for (func, pk, klass, datum) in test_data:
        with connection.constraint_checks_disabled():
            objects.extend(func[0](pk, klass, datum))

    # Get a count of the number of objects created for each class
    for klass in instance_count:
        instance_count[klass] = klass.objects.count()

    # Add the generic tagged objects to the object list
    objects.extend(Tag.objects.all())

    # Serialize the test database
    serialized_data = serializers.serialize(format, objects, indent=2)

    for obj in serializers.deserialize(format, serialized_data):
        obj.save()

    # Assert that the deserialized data is the same
    # as the original source
    for (func, pk, klass, datum) in test_data:
        func[1](self, pk, klass, datum)

    # Assert that the number of objects deserialized is the
    # same as the number that was serialized.
    for klass, count in instance_count.items():
        self.assertEqual(count, klass.objects.count())


def naturalKeySerializerTest(format, self):
    # Create all the objects defined in the test data
    objects = []
    instance_count = {}
    for (func, pk, klass, datum) in natural_key_test_data:
        with connection.constraint_checks_disabled():
            objects.extend(func[0](pk, klass, datum))

    # Get a count of the number of objects created for each class
    for klass in instance_count:
        instance_count[klass] = klass.objects.count()

    # Serialize the test database
    serialized_data = serializers.serialize(format, objects, indent=2,
        use_natural_keys=True)

    for obj in serializers.deserialize(format, serialized_data):
        obj.save()

    # Assert that the deserialized data is the same
    # as the original source
    for (func, pk, klass, datum) in natural_key_test_data:
        func[1](self, pk, klass, datum)

    # Assert that the number of objects deserialized is the
    # same as the number that was serialized.
    for klass, count in instance_count.items():
        self.assertEqual(count, klass.objects.count())

def fieldsTest(format, self):
    obj = ComplexModel(field1='first', field2='second', field3='third')
    obj.save_base(raw=True)

    # Serialize then deserialize the test database
    serialized_data = serializers.serialize(format, [obj], indent=2, fields=('field1','field3'))
    result = next(serializers.deserialize(format, serialized_data))

    # Check that the deserialized object contains data in only the serialized fields.
    self.assertEqual(result.object.field1, 'first')
    self.assertEqual(result.object.field2, '')
    self.assertEqual(result.object.field3, 'third')

def streamTest(format, self):
    obj = ComplexModel(field1='first',field2='second',field3='third')
    obj.save_base(raw=True)

    # Serialize the test database to a stream
    stream = BytesIO()
    serializers.serialize(format, [obj], indent=2, stream=stream)

    # Serialize normally for a comparison
    string_data = serializers.serialize(format, [obj], indent=2)

    # Check that the two are the same
    self.assertEqual(string_data, stream.getvalue())
    stream.close()

for format in serializers.get_serializer_formats():
    setattr(SerializerTests, 'test_' + format + '_serializer', curry(serializerTest, format))
    setattr(SerializerTests, 'test_' + format + '_natural_key_serializer', curry(naturalKeySerializerTest, format))
    setattr(SerializerTests, 'test_' + format + '_serializer_fields', curry(fieldsTest, format))
    if format != 'python':
        setattr(SerializerTests, 'test_' + format + '_serializer_stream', curry(streamTest, format))


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys


if __name__ == "__main__":
    if sys.argv[1] == 'testcompat':
        sys.argv[1] = 'test'
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "compatsettings")
    else:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testsettings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = json
from serializers import FixtureSerializer

format = 'json'


class Serializer(FixtureSerializer):
    internal_use_only = False  # Backwards compatability

    def getvalue(self):
        return self.value  # Backwards compatability with serialization API.

    def serialize(self, *args, **kwargs):
        return super(Serializer, self).serialize(format, *args, **kwargs)


def Deserializer(*args, **kwargs):
    return Serializer().deserialize(format, *args, **kwargs)

########NEW FILE########
__FILENAME__ = python
from serializers import FixtureSerializer

format = 'python'


class Serializer(FixtureSerializer):
    internal_use_only = True  # Backwards compatability

    def getvalue(self):
        return self.value  # Backwards compatability with serialization API.

    def serialize(self, *args, **kwargs):
        return super(Serializer, self).serialize(format, *args, **kwargs)


def Deserializer(*args, **kwargs):
    return Serializer().deserialize(format, *args, **kwargs)

########NEW FILE########
__FILENAME__ = xml
from serializers import FixtureSerializer

format = 'xml'


class Serializer(FixtureSerializer):
    internal_use_only = False  # Backwards compatability

    def getvalue(self):
        return self.value  # Backwards compatability with serialization API.

    def serialize(self, *args, **kwargs):
        return super(Serializer, self).serialize(format, *args, **kwargs)


def Deserializer(*args, **kwargs):
    return Serializer().deserialize(format, *args, **kwargs)

########NEW FILE########
__FILENAME__ = yaml
from serializers import FixtureSerializer

format = 'yaml'


class Serializer(FixtureSerializer):
    internal_use_only = False  # Backwards compatability

    def getvalue(self):
        return self.value  # Backwards compatability with serialization API.

    def serialize(self, *args, **kwargs):
        return super(Serializer, self).serialize(format, *args, **kwargs)


def Deserializer(*args, **kwargs):
    return Serializer().deserialize(format, *args, **kwargs)

########NEW FILE########
__FILENAME__ = fields
import datetime
from django.utils.encoding import is_protected_type, smart_unicode
from django.core import validators
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.db.models.related import RelatedObject
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.translation import ugettext_lazy as _
from serializers.utils import is_simple_callable
import warnings


class Field(object):
    creation_counter = 0

    def __init__(self, source=None, readonly=False):
        self.source = source
        self.readonly = readonly
        self.parent = None
        self.creation_counter = Field.creation_counter
        Field.creation_counter += 1

    def initialize(self, parent, model_field=None):
        """
        Called to set up a field prior to field_to_native or field_from_native.

        parent - The parent serializer.
        model_field - The model field this field corrosponds to, if one exists.
        """
        self.parent = parent
        self.root = parent.root or parent
        self.context = self.root.context
        if model_field:
            self.model_field = model_field

    def field_from_native(self, data, field_name, into):
        """
        Given a dictionary and a field name, updates the dictionary `into`,
        with the field and it's deserialized value.
        """
        if self.readonly:
            return

        try:
            native = data[field_name]
        except KeyError:
            return  # TODO Consider validation behaviour, 'required' opt etc...

        if self.source == '*':
            into.update(self.from_native(native))
        else:
            into[self.source or field_name] = self.from_native(native)

    def from_native(self, value):
        """
        Reverts a simple representation back to the field's value.
        """
        if hasattr(self, 'model_field'):
            try:
                return self.model_field.rel.to._meta.get_field(self.model_field.rel.field_name).to_python(value)
            except:
                return self.model_field.to_python(value)
        return value

    def field_to_native(self, obj, field_name):
        """
        Given and object and a field name, returns the value that should be
        serialized for that field.
        """
        if self.source == '*':
            return self.to_native(obj)

        self.obj = obj  # Need to hang onto this in the case of model fields
        if hasattr(self, 'model_field'):
            return self.to_native(self.model_field._get_val_from_obj(obj))

        return self.to_native(getattr(obj, self.source or field_name))

    def to_native(self, value):
        """
        Converts the field's value into it's simple representation.
        """
        if is_simple_callable(value):
            value = value()

        if is_protected_type(value):
            return value
        elif hasattr(self, 'model_field'):
            return self.model_field.value_to_string(self.obj)
        return smart_unicode(value)

    def attributes(self):
        """
        Returns a dictionary of attributes to be used when serializing to xml.
        """
        try:
            return {
                "type": self.model_field.get_internal_type()
            }
        except AttributeError:
            return {}


class RelatedField(Field):
    """
    A base class for model related fields or related managers.

    Subclass this and override `convert` to define custom behaviour when
    serializing related objects.
    """

    def field_to_native(self, obj, field_name):
        obj = getattr(obj, field_name)
        if obj.__class__.__name__ in ('RelatedManager', 'ManyRelatedManager'):
            return [self.to_native(item) for item in obj.all()]
        return self.to_native(obj)

    def attributes(self):
        try:
            return {
                "rel": self.model_field.rel.__class__.__name__,
                "to": smart_unicode(self.model_field.rel.to._meta)
            }
        except AttributeError:
            return {}


class PrimaryKeyRelatedField(RelatedField):
    """
    Serializes a model related field or related manager to a pk value.
    """

    # Note the we use ModelRelatedField's implementation, as we want to get the
    # raw database value directly, since that won't involve another
    # database lookup.
    #
    # An alternative implementation would simply be this...
    #
    # class PrimaryKeyRelatedField(RelatedField):
    #     def to_native(self, obj):
    #         return obj.pk

    error_messages = {
        'invalid': _(u"'%s' value must be an integer."),
    }

    def to_native(self, pk):
        """
        Simply returns the object's pk.  You can subclass this method to
        provide different serialization behavior of the pk.
        (For example returning a URL based on the model's pk.)
        """
        return pk

    def field_to_native(self, obj, field_name):
        try:
            obj = obj.serializable_value(field_name)
        except AttributeError:
            field = obj._meta.get_field_by_name(field_name)[0]
            obj = getattr(obj, field_name)
            if obj.__class__.__name__ == 'RelatedManager':
                return [self.to_native(item.pk) for item in obj.all()]
            elif isinstance(field, RelatedObject):
                return self.to_native(obj.pk)
            raise
        if obj.__class__.__name__ == 'ManyRelatedManager':
            return [self.to_native(item.pk) for item in obj.all()]
        return self.to_native(obj)

    def field_from_native(self, data, field_name, into):
        value = data.get(field_name)
        if hasattr(value, '__iter__'):
            into[field_name] = [self.from_native(item) for item in value]
        else:
            into[field_name + '_id'] = self.from_native(value)


class NaturalKeyRelatedField(RelatedField):
    """
    Serializes a model related field or related manager to a natural key value.
    """
    is_natural_key = True  # XML renderer handles these differently

    def to_native(self, obj):
        if hasattr(obj, 'natural_key'):
            return obj.natural_key()
        return obj

    def field_from_native(self, data, field_name, into):
        value = data.get(field_name)
        into[self.model_field.attname] = self.from_native(value)

    def from_native(self, value):
        # TODO: Support 'using' : db = options.pop('using', DEFAULT_DB_ALIAS)
        manager = self.model_field.rel.to._default_manager
        manager = manager.db_manager(DEFAULT_DB_ALIAS)
        return manager.get_by_natural_key(*value).pk


class BooleanField(Field):
    error_messages = {
        'invalid': _(u"'%s' value must be either True or False."),
    }

    def from_native(self, value):
        if value in (True, False):
            # if value is 1 or 0 than it's equal to True or False, but we want
            # to return a true bool for semantic reasons.
            return bool(value)
        if value in ('t', 'True', '1'):
            return True
        if value in ('f', 'False', '0'):
            return False
        raise ValidationError(self.error_messages['invalid'] % value)


class CharField(Field):
    def from_native(self, value):
        if isinstance(value, basestring) or value is None:
            return value
        return smart_unicode(value)


class DateField(Field):
    error_messages = {
        'invalid': _(u"'%s' value has an invalid date format. It must be "
                     u"in YYYY-MM-DD format."),
        'invalid_date': _(u"'%s' value has the correct format (YYYY-MM-DD) "
                          u"but it is an invalid date."),
    }

    def from_native(self, value):
        if value is None:
            return value
        if isinstance(value, datetime.datetime):
            if settings.USE_TZ and timezone.is_aware(value):
                # Convert aware datetimes to the default time zone
                # before casting them to dates (#17742).
                default_timezone = timezone.get_default_timezone()
                value = timezone.make_naive(value, default_timezone)
            return value.date()
        if isinstance(value, datetime.date):
            return value

        try:
            parsed = parse_date(value)
            if parsed is not None:
                return parsed
        except ValueError:
            msg = self.error_messages['invalid_date'] % value
            raise ValidationError(msg)

        msg = self.error_messages['invalid'] % value
        raise ValidationError(msg)


class DateTimeField(Field):
    error_messages = {
        'invalid': _(u"'%s' value has an invalid format. It must be in "
                     u"YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ] format."),
        'invalid_date': _(u"'%s' value has the correct format "
                          u"(YYYY-MM-DD) but it is an invalid date."),
        'invalid_datetime': _(u"'%s' value has the correct format "
                              u"(YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ]) "
                              u"but it is an invalid date/time."),
    }

    def from_native(self, value):
        if value is None:
            return value
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            value = datetime.datetime(value.year, value.month, value.day)
            if settings.USE_TZ:
                # For backwards compatibility, interpret naive datetimes in
                # local time. This won't work during DST change, but we can't
                # do much about it, so we let the exceptions percolate up the
                # call stack.
                warnings.warn(u"DateTimeField received a naive datetime (%s)"
                              u" while time zone support is active." % value,
                              RuntimeWarning)
                default_timezone = timezone.get_default_timezone()
                value = timezone.make_aware(value, default_timezone)
            return value

        try:
            parsed = parse_datetime(value)
            if parsed is not None:
                return parsed
        except ValueError:
            msg = self.error_messages['invalid_datetime'] % value
            raise ValidationError(msg)

        try:
            parsed = parse_date(value)
            if parsed is not None:
                return datetime.datetime(parsed.year, parsed.month, parsed.day)
        except ValueError:
            msg = self.error_messages['invalid_date'] % value
            raise ValidationError(msg)

        msg = self.error_messages['invalid'] % value
        raise ValidationError(msg)


class IntegerField(Field):
    error_messages = {
        'invalid': _(u"'%s' value must be an integer."),
    }

    def from_native(self, value):
        if value in validators.EMPTY_VALUES:
            return None
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(self.error_messages['invalid'])
        return value


class FloatField(Field):
    error_messages = {
        'invalid': _("'%s' value must be a float."),
    }

    def from_native(self, value):
        if value is None:
            return value
        try:
            return float(value)
        except (TypeError, ValueError):
            msg = self.error_messages['invalid'] % value
            raise ValidationError(msg)

# field_mapping = {
#     models.AutoField: IntegerField,
#     models.BooleanField: BooleanField,
#     models.CharField: CharField,
#     models.DateTimeField: DateTimeField,
#     models.DateField: DateField,
#     models.BigIntegerField: IntegerField,
#     models.IntegerField: IntegerField,
#     models.PositiveIntegerField: IntegerField,
#     models.FloatField: FloatField
# }


# def modelfield_to_serializerfield(field):
#     return field_mapping.get(type(field), Field)

########NEW FILE########
__FILENAME__ = fixture_serializer
from django.core.serializers.base import DeserializedObject
from django.db import models
from django.utils.datastructures import SortedDict
from django.utils.encoding import smart_unicode
from serializers import Field, PrimaryKeyRelatedField, NaturalKeyRelatedField
from serializers import Serializer
from serializers.renderers import (
    JSONRenderer,
    YAMLRenderer,
    DumpDataXMLRenderer
)
from serializers.parsers import (
    JSONParser,
    DumpDataXMLParser
)
from serializers.utils import DictWithMetadata


class ModelNameField(Field):
    """
    Serializes the model instance's model name.  Eg. 'auth.User'.
    """
    def field_to_native(self, obj, field_name):
        return smart_unicode(obj._meta)

    def field_from_native(self, data, field_name, into):
        # We don't actually want to restore the model name metadata to a field.
        pass


class FixtureFields(Serializer):
    """
    A serializer which uses serializes all the local fields on a model.
    """

    # Use an unsorted dict to ensure byte-for-byte backwards compatability
    _dict_class = DictWithMetadata

    def default_fields(self, serialize, obj=None, data=None, nested=False):
        """
        Return the set of all fields defined on the model.
        For fixtures this consists of only the local fields on the model.
        """
        if serialize:
            cls = obj.__class__
        else:
            cls = self.parent.model

        # all local fields + all m2m fields without through relationship
        opts = cls._meta.concrete_model._meta
        fields = [field for field in opts.local_fields if field.serialize]
        fields += [field for field in opts.many_to_many
                   if field.serialize and field.rel.through._meta.auto_created]

        ret = SortedDict()
        for model_field in fields:
            if model_field.rel and nested:
                field = FixtureSerializer()
            elif model_field.rel:
                field = self._nk_or_pk_field(serialize, data, model_field)
            else:
                field = Field()
            field.initialize(parent=self, model_field=model_field)
            ret[model_field.name] = field
        return ret

    def _nk_or_pk_field(self, serialize, data, model_field):
        """
        Determine if natural key field or primary key field should be used.
        """
        if ((serialize and self.root.use_natural_keys) or
            not serialize
            and hasattr(model_field.rel.to._default_manager, 'get_by_natural_key')
            and hasattr(data[model_field.name], '__iter__')):
            return NaturalKeyRelatedField()
        return PrimaryKeyRelatedField()


class FixtureSerializer(Serializer):
    """
    A serializer that is used for serializing/deserializing fixtures.
    This is used by the 'dumpdata' and 'loaddata' managment commands.
    """

    # NB: Unsorted dict to ensure byte-for-byte backwards compatability
    _dict_class = DictWithMetadata

    pk = Field()
    model = ModelNameField()
    fields = FixtureFields(source='*')

    class Meta:
        renderer_classes = {
            'xml': DumpDataXMLRenderer,
            'json': JSONRenderer,
            'yaml': YAMLRenderer,
        }
        parser_classes = {
            'xml': DumpDataXMLParser,
            'json': JSONParser
        }

    def serialize(self, *args, **kwargs):
        """
        Override default behavior slightly:

        1. Add 'use_natural_keys' option to switch between PK and NK relations.
        2. The 'fields' and 'exclude' options should apply to the
           'FixtureFields' child serializer, not to the root serializer.
        """
        self.use_natural_keys = kwargs.pop('use_natural_keys', False)

        # TODO: Actually, this is buggy - fields/exclude will be retained as
        # state between subsequant calls to serialize()
        fields = kwargs.pop('fields', None)
        exclude = kwargs.pop('exclude', None)
        if fields is not None:
            self.fields['fields'].opts.fields = fields
        if exclude is not None:
            self.fields['fields'].opts.exclude = exclude

        return super(FixtureSerializer, self).serialize(*args, **kwargs)

    def restore_fields(self, data):
        """
        Prior to deserializing the fields, we want to determine the model
        class, and store it so it can be used to:

        1. Determine the correct fields for restoring attributes on the model.
        2. Determine the class to use when restoring the model.
        """
        self.model = models.get_model(*data['model'].split("."))
        return super(FixtureSerializer, self).restore_fields(data)

    def restore_object(self, attrs, instance=None):
        """
        Restore the model instance.
        """
        m2m_data = {}
        for field in self.model._meta.many_to_many:
            if field.name in attrs:
                m2m_data[field.name] = attrs.pop(field.name)
        return DeserializedObject(self.model(**attrs), m2m_data)

########NEW FILE########
__FILENAME__ = parsers
import json
from xml.dom import pulldom
from django.core.serializers.base import DeserializationError


class JSONParser(object):
    def parse(self, stream):
        try:
            return json.load(stream)
        except Exception as e:
            # Map to deserializer error
            raise DeserializationError(e)


class DumpDataXMLParser(object):
    def parse(self, stream):
        event_stream = pulldom.parse(stream)
        for event, node in event_stream:
            if event == "START_ELEMENT" and node.nodeName == "object":
                event_stream.expandNode(node)
                yield self._handle_object(node)

    def _handle_object(self, node):
        ret = {}

        if node.hasAttribute("pk"):
            ret['pk'] = node.getAttribute('pk')
        else:
            ret['pk'] = None
        ret['model'] = node.getAttribute('model')

        fields = {}
        for field_node in node.getElementsByTagName("field"):
            # If the field is missing the name attribute, bail
            name = field_node.getAttribute("name")
            rel = field_node.getAttribute("rel")
            if not name:
                raise DeserializationError("<field> node is missing the 'name' attribute")

            if field_node.getElementsByTagName('None'):
                value = None
            elif rel == 'ManyToManyRel':
                value = [n.getAttribute('pk') for n in field_node.getElementsByTagName('object')]
            elif field_node.getElementsByTagName('natural'):
                value = [getInnerText(n).strip() for n in field_node.getElementsByTagName('natural')]
            else:
                value = getInnerText(field_node).strip()

            fields[name] = value

        ret['fields'] = fields

        return ret


def getInnerText(node):
    """
    Get all the inner text of a DOM node (recursively).
    """
    # inspired by http://mail.python.org/pipermail/xml-sig/2005-March/011022.html
    inner_text = []
    for child in node.childNodes:
        if child.nodeType == child.TEXT_NODE or child.nodeType == child.CDATA_SECTION_NODE:
            inner_text.append(child.data)
        elif child.nodeType == child.ELEMENT_NODE:
            inner_text.extend(getInnerText(child))
        else:
            pass
    return u"".join(inner_text)

########NEW FILE########
__FILENAME__ = renderers
import datetime
from django.utils import simplejson as json
from django.utils.encoding import smart_unicode
from django.utils.html import urlize
from django.utils.xmlutils import SimplerXMLGenerator
from serializers.utils import SafeDumper, DictWriter, DjangoJSONEncoder
try:
    import yaml
except ImportError:
    yaml = None


class BaseRenderer(object):
    """
    Defines the base interface that renderers should implement.
    """

    def render(obj, stream, **opts):
        return str(obj)


class JSONRenderer(BaseRenderer):
    """
    Render a native python object into JSON.
    """
    def render(self, obj, stream, **opts):
        indent = opts.pop('indent', None)
        sort_keys = opts.pop('sort_keys', False)
        return json.dump(obj, stream, cls=DjangoJSONEncoder,
                         indent=indent, sort_keys=sort_keys)


class YAMLRenderer(BaseRenderer):
    """
    Render a native python object into YAML.
    """
    def render(self, obj, stream, **opts):
        indent = opts.pop('indent', None)
        default_flow_style = opts.pop('default_flow_style', None)
        return yaml.dump(obj, stream, Dumper=SafeDumper,
                         indent=indent, default_flow_style=default_flow_style)


class HTMLRenderer(BaseRenderer):
    """
    A basic html renderer, that renders data into tabular format.
    """
    def render(self, obj, stream, **opts):
        self._to_html(stream, obj)

    def _to_html(self, stream, data):
        if isinstance(data, dict):
            stream.write('<table>\n')
            for key, value in data.items():
                stream.write('<tr><td>%s</td><td>' % key)
                self._to_html(stream, value)
                stream.write('</td></tr>\n')
            stream.write('</table>\n')

        elif hasattr(data, '__iter__'):
            stream.write('<ul>\n')
            for item in data:
                stream.write('<li>')
                self._to_html(stream, item)
                stream.write('</li>')
            stream.write('</ul>\n')

        else:
            stream.write(urlize(smart_unicode(data)))


class XMLRenderer(BaseRenderer):
    """
    Render a native python object into a generic XML format.
    """
    def render(self, obj, stream, **opts):
        xml = SimplerXMLGenerator(stream, 'utf-8')
        xml.startDocument()
        self._to_xml(xml, obj)
        xml.endDocument()

    def _to_xml(self, xml, data):
        if isinstance(data, dict):
            xml.startElement('object', {})
            for key, value in data.items():
                xml.startElement(key, {})
                self._to_xml(xml, value)
                xml.endElement(key)
            xml.endElement('object')

        elif hasattr(data, '__iter__'):
            xml.startElement('list', {})
            for item in data:
                xml.startElement('item', {})
                self._to_xml(xml, item)
                xml.endElement('item')
            xml.endElement('list')

        else:
            xml.characters(smart_unicode(data))


class DumpDataXMLRenderer(BaseRenderer):
    """
    Render a native python object into XML dumpdata format.
    """
    def render(self, obj, stream, **opts):
        xml = SimplerXMLGenerator(stream, 'utf-8')
        xml.startDocument()
        xml.startElement('django-objects', {'version': '1.0'})
        if hasattr(obj, '__iter__'):
            [self.model_to_xml(xml, item) for item in obj]
        else:
            self.model_to_xml(xml, obj)
        xml.endElement('django-objects')
        xml.endDocument()

    def model_to_xml(self, xml, data):
        pk = data['pk']
        model = data['model']
        fields_data = data['fields']

        attrs = {}
        if pk is not None:
            attrs['pk'] = unicode(pk)
        attrs['model'] = model

        xml.startElement('object', attrs)

        # For each item in fields get it's key, value and serializer field
        key_val_field = [
            (key, val, fields_data.fields[key])
            for key, val in fields_data.items()
        ]

        # Due to implmentation details, the existing xml dumpdata format
        # renders ordered fields, whilst json and yaml render unordered
        # fields (ordering determined by python's `dict` implementation)
        # To maintain byte-for-byte backwards compatability,
        # we'll deal with that now.
        key_val_field = sorted(key_val_field,
                               key=lambda x: x[2].creation_counter)

        for key, value, serializer_field in key_val_field:
            attrs = {'name': key}
            attrs.update(serializer_field.attributes())
            xml.startElement('field', attrs)

            if value is not None and getattr(serializer_field, 'is_natural_key', False):
                self.handle_natural_key(xml, value)
            elif attrs.get('rel', None) == 'ManyToManyRel':
                self.handle_many_to_many(xml, value)
            elif isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
                self.handle_datetimes(xml, value)
            elif value is None:
                self.handle_none(xml)
            else:
                self.handle_value(xml, value)

            xml.endElement('field')
        xml.endElement('object')

    def handle_natural_key(self, xml, value):
        for item in value:
            xml.addQuickElement('natural', contents=item)

    def handle_many_to_many(self, xml, value):
        for item in value:
            xml.addQuickElement('object', attrs={'pk': str(item)})

    def handle_datetimes(self, xml, value):
        xml.characters(value.isoformat())

    def handle_value(self, xml, value):
        xml.characters(smart_unicode(value))

    def handle_none(self, xml):
        xml.addQuickElement('None')


class CSVRenderer(BaseRenderer):
    def render(self, obj, stream, **opts):
        if isinstance(obj, dict) or not hasattr(obj, '__iter__'):
            obj = [obj]
        writer = None
        for item in obj:
            if not writer:
                writer = DictWriter(stream, item.keys())
                writer.writeheader()
            writer.writerow(item)

if not yaml:
    YAMLRenderer = None

########NEW FILE########
__FILENAME__ = serializer
from decimal import Decimal
from django.core.serializers.base import DeserializedObject
from django.utils.datastructures import SortedDict
import copy
import datetime
import types
from serializers.renderers import (
    JSONRenderer,
    YAMLRenderer,
    XMLRenderer,
    HTMLRenderer,
    CSVRenderer,
)
from serializers.parsers import (
    JSONParser,
)
from serializers.fields import *
from serializers.utils import SortedDictWithMetadata, is_simple_callable
from StringIO import StringIO
from io import BytesIO


class RecursionOccured(BaseException):
    pass


def _is_protected_type(obj):
    """
    True if the object is a native datatype that does not need to
    be serialized further.
    """
    return isinstance(obj, (
        types.NoneType,
       int, long,
       datetime.datetime, datetime.date, datetime.time,
       float, Decimal,
       basestring)
    )


def _get_declared_fields(bases, attrs):
    """
    Create a list of serializer field instances from the passed in 'attrs',
    plus any fields on the base classes (in 'bases').

    Note that all fields from the base classes are used.
    """
    fields = [(field_name, attrs.pop(field_name))
              for field_name, obj in attrs.items()
              if isinstance(obj, Field)]
    fields.sort(key=lambda x: x[1].creation_counter)

    # If this class is subclassing another Serializer, add that Serializer's
    # fields.  Note that we loop over the bases in *reverse*. This is necessary
    # in order to the correct order of fields.
    for base in bases[::-1]:
        if hasattr(base, 'base_fields'):
            fields = base.base_fields.items() + fields

    return SortedDict(fields)


class SerializerMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs['base_fields'] = _get_declared_fields(bases, attrs)
        return super(SerializerMetaclass, cls).__new__(cls, name, bases, attrs)


class SerializerOptions(object):
    """
    Meta class options for ModelSerializer
    """
    def __init__(self, meta):
        self.nested = getattr(meta, 'nested', False)
        self.fields = getattr(meta, 'fields', ())
        self.exclude = getattr(meta, 'exclude', ())
        self.renderer_classes = getattr(meta, 'renderer_classes', {
            'xml': XMLRenderer,
            'json': JSONRenderer,
            'yaml': YAMLRenderer,
            'csv': CSVRenderer,
            'html': HTMLRenderer,
        })
        self.parser_classes = getattr(meta, 'parser_classes', {
            'json': JSONParser
        })


class BaseSerializer(Field):
    class Meta(object):
        pass

    _options_class = SerializerOptions
    _dict_class = SortedDictWithMetadata  # Set to unsorted dict for backwards compatability with unsorted implementations.

    def __init__(self, source=None, readonly=False):
        super(BaseSerializer, self).__init__(source, readonly)
        self.fields = copy.deepcopy(self.base_fields)
        self.opts = self._options_class(self.Meta)
        self.parent = None
        self.root = None

    #####
    # Methods to determine which fields to use when (de)serializing objects.

    def default_fields(self, serialize, obj=None, data=None, nested=False):
        """
        Return the complete set of default fields for the object, as a dict.
        """
        return {}

    def get_fields(self, serialize, obj=None, data=None, nested=False):
        """
        Returns the complete set of fields for the object as a dict.

        This will be the set of any explicitly declared fields,
        plus the set of fields returned by get_default_fields().
        """
        ret = SortedDict()

        # Get the explicitly declared fields
        for key, field in self.fields.items():
            ret[key] = field
            # Determine if the declared field corrosponds to a model field.
            try:
                if key == 'pk':
                    model_field = obj._meta.pk
                else:
                    model_field = obj._meta.get_field_by_name(key)[0]
            except:
                model_field = None
            # Set up the field
            field.initialize(parent=self, model_field=model_field)

        # Add in the default fields
        fields = self.default_fields(serialize, obj, data, nested)
        for key, val in fields.items():
            if key not in ret:
                ret[key] = val

        # If 'fields' is specified, use those fields, in that order.
        if self.opts.fields:
            new = SortedDict()
            for key in self.opts.fields:
                new[key] = ret[key]
            ret = new

        # Remove anything in 'exclude'
        if self.opts.exclude:
            for key in self.opts.exclude:
                ret.pop(key, None)

        return ret

    #####
    # Field methods - used when the serializer class is itself used as a field.

    def initialize(self, parent, model_field=None):
        """
        Same behaviour as usual Field, except that we need to keep track
        of state so that we can deal with handling maximum depth and recursion.
        """
        super(BaseSerializer, self).initialize(parent, model_field)
        self.stack = parent.stack[:]
        if parent.opts.nested and not isinstance(parent.opts.nested, bool):
            self.opts.nested = parent.opts.nested - 1
        else:
            self.opts.nested = parent.opts.nested

    #####
    # Methods to convert or revert from objects <--> primative representations.

    def get_field_key(self, field_name):
        """
        Return the key that should be used for a given field.
        """
        return field_name

    def convert_object(self, obj):
        """
        Core of serialization.
        Convert an object into a dictionary of serialized field values.
        """
        if obj in self.stack and not self.source == '*':
            raise RecursionOccured()
        self.stack.append(obj)

        ret = self._dict_class()
        ret.fields = {}

        fields = self.get_fields(serialize=True, obj=obj, nested=self.opts.nested)
        for field_name, field in fields.items():
            key = self.get_field_key(field_name)
            try:
                value = field.field_to_native(obj, field_name)
            except RecursionOccured:
                field = self.get_fields(serialize=True, obj=obj, nested=False)[field_name]
                value = field.field_to_native(obj, field_name)
            ret[key] = value
            ret.fields[key] = field
        return ret

    def restore_fields(self, data):
        """
        Core of deserialization, together with `restore_object`.
        Converts a dictionary of data into a dictionary of deserialized fields.
        """
        fields = self.get_fields(serialize=False, data=data, nested=self.opts.nested)
        reverted_data = {}
        for field_name, field in fields.items():
            field.field_from_native(data, field_name, reverted_data)
        return reverted_data

    def restore_object(self, attrs, instance=None):
        """
        Deserialize a dictionary of attributes into an object instance.
        You should override this method to control how deserialized objects
        are instantiated.
        """
        if instance is not None:
            instance.update(attrs)
            return instance
        return attrs

    def to_native(self, obj):
        """
        Serialize objects -> primatives.
        """
        if _is_protected_type(obj):
            return obj
        elif is_simple_callable(obj):
            return self.to_native(obj())
        elif isinstance(obj, dict):
            return dict([(key, self.to_native(val))
                         for (key, val) in obj.items()])
        elif hasattr(obj, '__iter__'):
            return (self.to_native(item) for item in obj)
        return self.convert_object(obj)

    def from_native(self, data):
        """
        Deserialize primatives -> objects.
        """
        if _is_protected_type(data):
            return data
        elif hasattr(data, '__iter__') and not isinstance(data, dict):
            return (self.from_native(item) for item in data)
        else:
            attrs = self.restore_fields(data)
            return self.restore_object(attrs, instance=getattr(self, 'instance', None))

    def render(self, data, stream, format, **options):
        """
        Render primatives -> bytestream for serialization.
        """
        renderer = self.opts.renderer_classes[format]()
        return renderer.render(data, stream, **options)

    def parse(self, stream, format, **options):
        """
        Parse bytestream -> primatives for deserialization.
        """
        parser = self.opts.parser_classes[format]()
        return parser.parse(stream, **options)

    def serialize(self, format, obj, context=None, **options):
        """
        Perform serialization of objects into bytestream.
        First converts the objects into primatives,
        then renders primative types to bytestream.
        """
        self.stack = []
        self.context = context or {}

        data = self.to_native(obj)
        if format != 'python':
            stream = options.pop('stream', StringIO())
            self.render(data, stream, format, **options)
            if hasattr(stream, 'getvalue'):
                self.value = stream.getvalue()
            else:
                self.value = None
        else:
            self.value = data
        return self.value

    def deserialize(self, format, stream_or_string, instance=None, context=None, **options):
        """
        Perform deserialization of bytestream into objects.
        First parses the bytestream into primative types,
        then converts primative types into objects.
        """
        self.stack = []
        self.context = context or {}
        self.instance = instance

        if format != 'python':
            if isinstance(stream_or_string, basestring):
                stream = BytesIO(stream_or_string)
            else:
                stream = stream_or_string
            data = self.parse(stream, format, **options)
        else:
            data = stream_or_string
        return self.from_native(data)


class Serializer(BaseSerializer):
    __metaclass__ = SerializerMetaclass


class ModelSerializerOptions(SerializerOptions):
    """
    Meta class options for ModelSerializer
    """
    def __init__(self, meta):
        super(ModelSerializerOptions, self).__init__(meta)
        self.model = getattr(meta, 'model', None)


class ModelSerializer(RelatedField, Serializer):
    """
    A serializer that deals with model instances and querysets.
    """
    _options_class = ModelSerializerOptions

    def default_fields(self, serialize, obj=None, data=None, nested=False):
        """
        Return all the fields that should be serialized for the model.
        """
        if serialize:
            cls = obj.__class__
        else:
            cls = self.opts.model

        opts = cls._meta.concrete_model._meta
        pk_field = opts.pk
        while pk_field.rel:
            pk_field = pk_field.rel.to._meta.pk
        fields = [pk_field]
        fields += [field for field in opts.fields if field.serialize]
        fields += [field for field in opts.many_to_many if field.serialize]

        ret = SortedDict()
        for model_field in fields:
            if model_field.rel and nested:
                field = self.get_nested_field(model_field)
            elif model_field.rel:
                field = self.get_related_field(model_field)
            else:
                field = self.get_field(model_field)
            field.initialize(parent=self, model_field=model_field)
            ret[model_field.name] = field
        return ret

    def get_nested_field(self, model_field):
        """
        Creates a default instance of a nested relational field.
        """
        return ModelSerializer()

    def get_related_field(self, model_field):
        """
        Creates a default instance of a flat relational field.
        """
        return PrimaryKeyRelatedField()

    def get_field(self, model_field):
        """
        Creates a default instance of a basic field.
        """
        return Field()

    def restore_object(self, attrs, instance=None):
        """
        Restore the model instance.
        """
        m2m_data = {}
        for field in self.opts.model._meta.many_to_many:
            if field.name in attrs:
                m2m_data[field.name] = attrs.pop(field.name)
        return DeserializedObject(self.opts.model(**attrs), m2m_data)

########NEW FILE########
__FILENAME__ = tests
import datetime
from decimal import Decimal
from django.core import serializers
from django.db import models
from django.test import TestCase
from django.utils.datastructures import SortedDict
from serializers import Serializer, ModelSerializer, FixtureSerializer
from serializers.fields import Field, NaturalKeyRelatedField, PrimaryKeyRelatedField

# ObjectSerializer has been removed from serializers
# leaving it in the tests for the moment for more coverage.


class ObjectSerializer(Serializer):
    def default_fields(self, serialize, obj=None, data=None, nested=False):
        """
        Given an object, return the default set of fields to serialize.

        For ObjectSerializer this should be the set of all the non-private
        object attributes.
        """
        if not serialize:
            raise Exception('ObjectSerializer does not support deserialization')

        ret = SortedDict()
        attrs = [key for key in obj.__dict__.keys() if not(key.startswith('_'))]
        for attr in sorted(attrs):
            if nested:
                field = self.__class__()
            else:
                field = Field()
            field.initialize(parent=self)
            ret[attr] = field
        return ret


class NestedObjectSerializer(ObjectSerializer):
    class Meta:
        nested = True


class DepthOneObjectSerializer(ObjectSerializer):
    class Meta:
        nested = 1


def expand(obj):
    """
    Unroll any generators in returned object.
    """
    if isinstance(obj, dict):
        ret = SortedDict()  # Retain original ordering
        for key, val in obj.items():
            ret[key] = expand(val)
        return ret
    elif hasattr(obj, '__iter__'):
        return [expand(item) for item in obj]
    return obj


def get_deserialized(queryset, serializer=None, format=None, **kwargs):
    format = format or 'json'
    if serializer:
        # django-serializers
        serialized = serializer.serialize(format, queryset, **kwargs)
        return serializer.deserialize(format, serialized)
    # Existing Django serializers
    serialized = serializers.serialize(format, queryset, **kwargs)
    return serializers.deserialize(format, serialized)


def deserialized_eq(objects1, objects2):
    objects1 = list(objects1)
    objects2 = list(objects2)
    if len(objects1) != len(objects2):
        return False
    for index in range(len(objects1)):
        if objects1[index].object != objects2[index].object:
            return False
        if objects1[index].m2m_data.keys() != objects2[index].m2m_data.keys():
            return False
        m2m_data1 = objects1[index].m2m_data
        m2m_data2 = objects2[index].m2m_data
        for field_name in m2m_data1.keys():
            if set([int(m2m) for m2m in m2m_data1[field_name]]) != \
                set([int(m2m) for m2m in m2m_data2[field_name]]):
                return False
        object1 = objects1[index].object
        object2 = objects2[index].object
        for field in object1._meta.fields:
            if getattr(object1, field.attname) != getattr(object2, field.attname):
                return False

    return True


class SerializationTestCase(TestCase):
    def assertEquals(self, lhs, rhs):
        """
        Regular assert, but unroll any generators before comparison.
        """
        lhs = expand(lhs)
        rhs = expand(rhs)
        return super(SerializationTestCase, self).assertEquals(lhs, rhs)


class TestBasicObjects(SerializationTestCase):
    def test_list(self):
        obj = []
        expected = '[]'
        output = ObjectSerializer().serialize('json', obj)
        self.assertEquals(output, expected)

    def test_dict(self):
        obj = {}
        expected = '{}'
        output = ObjectSerializer().serialize('json', obj)
        self.assertEquals(output, expected)


class ExampleObject(object):
    """
    An example class for testing basic serialization.
    """
    def __init__(self):
        self.a = 1
        self.b = 'foo'
        self.c = True
        self._hidden = 'other'


class Person(object):
    """
    An example class for testing serilization of properties and methods.
    """
    CHILD_AGE = 16

    def __init__(self, first_name=None, last_name=None, age=None, **kwargs):
        self.first_name = first_name
        self.last_name = last_name
        self.age = age
        for key, val in kwargs.items():
            setattr(self, key, val)

    @property
    def full_name(self):
        return self.first_name + ' ' + self.last_name

    def is_child(self):
        return self.age < self.CHILD_AGE

    def __unicode__(self):
        return self.full_name


class EncoderTests(SerializationTestCase):
    def setUp(self):
        self.obj = ExampleObject()

    def test_json(self):
        expected = '{"a": 1, "b": "foo", "c": true}'
        output = ObjectSerializer().serialize('json', self.obj)
        self.assertEquals(output, expected)

    def test_yaml(self):
        expected = '{a: 1, b: foo, c: true}\n'
        output = ObjectSerializer().serialize('yaml', self.obj)
        self.assertEquals(output, expected)

    def test_xml(self):
        expected = '<?xml version="1.0" encoding="utf-8"?>\n<object><a>1</a><b>foo</b><c>True</c></object>'
        output = ObjectSerializer().serialize('xml', self.obj)
        self.assertEquals(output, expected)


class BasicSerializerTests(SerializationTestCase):
    def setUp(self):
        self.obj = ExampleObject()

    def test_serialize_basic_object(self):
        """
        Objects are serialized by converting into dictionaries.
        """
        expected = {
            'a': 1,
            'b': 'foo',
            'c': True
        }

        self.assertEquals(ObjectSerializer().serialize('python', self.obj), expected)

    def test_serialize_fields(self):
        """
        Setting 'Meta.fields' specifies exactly which fields to serialize.
        """
        class CustomSerializer(ObjectSerializer):
            class Meta:
                fields = ('a', 'c')

        expected = {
            'a': 1,
            'c': True
        }

        self.assertEquals(CustomSerializer().serialize('python', self.obj), expected)

    def test_serialize_exclude(self):
        """
        Setting 'Meta.exclude' causes a field to be excluded.
        """
        class CustomSerializer(ObjectSerializer):
            class Meta:
                exclude = ('b',)

        expected = {
            'a': 1,
            'c': True
        }

        self.assertEquals(CustomSerializer().serialize('python', self.obj), expected)


class SerializeAttributeTests(SerializationTestCase):
    """
    Test covering serialization of different types of attributes on objects.
    """
    def setUp(self):
        self.obj = Person('john', 'doe', 42)

    def test_serialization_only_includes_instance_properties(self):
        """
        By default only serialize instance properties, not class properties.
        """
        expected = {
            'first_name': 'john',
            'last_name': 'doe',
            'age': 42
        }

        self.assertEquals(ObjectSerializer().serialize('python', self.obj), expected)

    def test_serialization_can_include_properties(self):
        """
        Object properties can be included as fields.
        """
        class CustomSerializer(ObjectSerializer):
            full_name = Field()

            class Meta:
                fields = ('full_name', 'age')

        expected = {
            'full_name': 'john doe',
            'age': 42
        }

        self.assertEquals(CustomSerializer().serialize('python', self.obj), expected)

    def test_serialization_can_include_no_arg_methods(self):
        """
        Object methods may be included as fields.
        """
        class CustomSerializer(ObjectSerializer):
            full_name = Field()
            is_child = Field()

            class Meta:
                fields = ('full_name', 'is_child')

        expected = {
            'full_name': 'john doe',
            'is_child': False
        }

        self.assertEquals(CustomSerializer().serialize('python', self.obj), expected)


class SerializerFieldTests(SerializationTestCase):
    """
    Tests declaring explicit fields on the serializer.
    """

    def setUp(self):
        self.obj = Person('john', 'doe', 42)

    def test_explicit_fields_replace_defaults(self):
        """
        Setting include_default_fields to `False` fields on a serializer
        ensures that only explicitly declared fields are used.
        """
        class CustomSerializer(Serializer):
            full_name = ObjectSerializer()

        expected = {
            'full_name': 'john doe',
        }

        self.assertEquals(CustomSerializer().serialize('python', self.obj), expected)

    def test_include_default_fields(self):
        """
        By default, both fields which have been explicitly included via a
        Serializer field declaration, and regular default object fields will
        be included.
        """
        class CustomSerializer(ObjectSerializer):
            full_name = ObjectSerializer()

        expected = {
            'full_name': 'john doe',
            'first_name': 'john',
            'last_name': 'doe',
            'age': 42
        }

        self.assertEquals(CustomSerializer().serialize('python', self.obj), expected)

    # def test_field_label(self):
    #     """
    #     A serializer field can take a 'label' argument, which is used as the
    #     field key instead of the field's property name.
    #     """
    #     class CustomSerializer(ObjectSerializer):
    #         full_name = ObjectSerializer(label='Full name')
    #         age = ObjectSerializer(label='Age')

    #         class Meta:
    #             fields = ('full_name', 'age')

    #     expected = {
    #         'Full name': 'john doe',
    #         'Age': 42
    #     }

    #     self.assertEquals(CustomSerializer().serialize('python', self.obj), expected)

    def test_source(self):
        """
        Setting source='*', means the complete object will be used when
        serializing that field.
        """
        class CustomSerializer(ObjectSerializer):
            full_name = ObjectSerializer()
            details = ObjectSerializer(source='*')

            class Meta:
                fields = ('full_name', 'details')

        expected = {
            'full_name': 'john doe',
            'details': {
                'first_name': 'john',
                'last_name': 'doe',
                'age': 42
            }
        }

        self.assertEquals(CustomSerializer().serialize('python', self.obj), expected)

    def test_source_all_with_custom_serializer(self):
        """
        A custom serializer can be used with source='*' as serialize the
        complete object within a field.
        """
        class DetailsSerializer(ObjectSerializer):
            first_name = ObjectSerializer()
            last_name = ObjectSerializer()

            class Meta:
                fields = ('first_name', 'last_name')

        class CustomSerializer(ObjectSerializer):
            full_name = ObjectSerializer()
            details = DetailsSerializer(source='*')

            class Meta:
                fields = ('full_name', 'details')

        expected = {
            'full_name': 'john doe',
            'details': {
                'first_name': 'john',
                'last_name': 'doe'
            }
        }

        self.assertEquals(CustomSerializer().serialize('python', self.obj), expected)

    # def test_serializer_fields_do_not_share_state(self):
    #     """
    #     Make sure that different serializer instances do not share the same
    #     SerializerField instances.
    #     """
    #     class CustomSerializer(Serializer):
    #         example = Serializer()

    #     serializer_one = CustomSerializer()
    #     serializer_two = CustomSerializer()
    #     self.assertFalse(serializer_one.fields['example'] is serializer_two.fields['example'])

    def test_serializer_field_order_preserved(self):
        """
        Make sure ordering of serializer fields is preserved.
        """
        class CustomSerializer(ObjectSerializer):
            first_name = Field()
            full_name = Field()
            age = Field()
            last_name = Field()

            class Meta:
                preserve_field_order = True

        keys = ['first_name', 'full_name', 'age', 'last_name']

        self.assertEquals(CustomSerializer().serialize('python', self.obj).keys(), keys)


class NestedSerializationTests(SerializationTestCase):
    """
    Tests serialization of nested objects.
    """

    def setUp(self):
        fred = Person('fred', 'bloggs', 41)
        emily = Person('emily', 'doe', 37)
        jane = Person('jane', 'doe', 44, partner=fred)
        self.obj = Person('john', 'doe', 42, siblings=[jane, emily])

    def test_nested_serialization(self):
        """
        Default with nested serializers is to include full serialization of
        child elements.
        """
        expected = {
            'first_name': 'john',
            'last_name': 'doe',
            'age': 42,
            'siblings': [
                {
                    'first_name': 'jane',
                    'last_name': 'doe',
                    'age': 44,
                    'partner': {
                        'first_name': 'fred',
                        'last_name': 'bloggs',
                        'age': 41,
                    }
                },
                {
                    'first_name': 'emily',
                    'last_name': 'doe',
                    'age': 37,
                }
            ]
        }
        self.assertEquals(NestedObjectSerializer().serialize('python', self.obj), expected)

    def test_nested_serialization_with_args(self):
        """
        We can pass serializer options through to nested fields as usual.
        """
        class SiblingsSerializer(ObjectSerializer):
            full_name = Field()

            class Meta:
                fields = ('full_name',)

        class PersonSerializer(Serializer):
            full_name = Field()
            siblings = SiblingsSerializer()

        expected = {
            'full_name': 'john doe',
            'siblings': [
                {
                    'full_name': 'jane doe'
                },
                {
                    'full_name': 'emily doe',
                }
            ]
        }

        self.assertEquals(PersonSerializer().serialize('python', self.obj), expected)

    # TODO: Changed slightly
    # def test_flat_serialization(self):
    #     """
    #     If 'nested' is False then nested objects should be serialized as
    #     flat values.
    #     """
    #     expected = {
    #         'first_name': 'john',
    #         'last_name': 'doe',
    #         'age': 42,
    #         'siblings': [
    #             'jane doe',
    #             'emily doe'
    #         ]
    #     }

    #     self.assertEquals(ObjectSerializer().serialize('python', self.obj), expected)

    def test_depth_one_serialization(self):
        """
        If 'nested' is greater than 0 then nested objects should be serialized
        as flat values once the specified depth has been reached.
        """
        expected = {
            'first_name': 'john',
            'last_name': 'doe',
            'age': 42,
            'siblings': [
                {
                    'first_name': 'jane',
                    'last_name': 'doe',
                    'age': 44,
                    'partner': 'fred bloggs'
                },
                {
                    'first_name': 'emily',
                    'last_name': 'doe',
                    'age': 37,
                }
            ]
        }

        self.assertEquals(DepthOneObjectSerializer().serialize('python', self.obj), expected)


class RecursiveSerializationTests(SerializationTestCase):
    def setUp(self):
        emily = Person('emily', 'doe', 37)
        john = Person('john', 'doe', 42, daughter=emily)
        emily.father = john
        self.obj = john

    def test_recursive_serialization(self):
        """
        If recursion occurs, serializer will fall back to flat values.
        """
        expected = {
            'first_name': 'john',
            'last_name': 'doe',
            'age': 42,
            'daughter': {
                    'first_name': 'emily',
                    'last_name': 'doe',
                    'age': 37,
                    'father': 'john doe'
            }
        }
        self.assertEquals(NestedObjectSerializer().serialize('python', self.obj), expected)


##### Simple models without relationships. #####

class RaceEntry(models.Model):
    name = models.CharField(max_length=100)
    runner_number = models.PositiveIntegerField()
    start_time = models.DateTimeField()
    finish_time = models.DateTimeField()


class RaceEntrySerializer(ModelSerializer):
    class Meta:
        model = RaceEntry


class TestSimpleModel(SerializationTestCase):
    def setUp(self):
        self.dumpdata = FixtureSerializer()
        self.serializer = RaceEntrySerializer()
        RaceEntry.objects.create(
            name='John doe',
            runner_number=6014,
            start_time=datetime.datetime(year=2012, month=4, day=30, hour=9),
            finish_time=datetime.datetime(year=2012, month=4, day=30, hour=12, minute=25)
        )

    def test_simple_dumpdata_json(self):
        self.assertEquals(
            self.dumpdata.serialize('json', RaceEntry.objects.all()),
            serializers.serialize('json', RaceEntry.objects.all())
        )

    def test_simple_dumpdata_yaml(self):
        self.assertEquals(
            self.dumpdata.serialize('yaml', RaceEntry.objects.all()),
            serializers.serialize('yaml', RaceEntry.objects.all())
        )

    def test_simple_dumpdata_xml(self):
        self.assertEquals(
            self.dumpdata.serialize('xml', RaceEntry.objects.all()),
            serializers.serialize('xml', RaceEntry.objects.all())
        )

    def test_csv(self):
        expected = (
            "id,name,runner_number,start_time,finish_time\r\n"
            "1,John doe,6014,2012-04-30 09:00:00,2012-04-30 12:25:00\r\n"
        )
        self.assertEquals(
            self.serializer.serialize('csv', RaceEntry.objects.all()),
            expected
        )

    def test_simple_dumpdata_fields(self):
        self.assertEquals(
            self.dumpdata.serialize('json', RaceEntry.objects.all(), fields=('name', 'runner_number')),
            serializers.serialize('json', RaceEntry.objects.all(), fields=('name', 'runner_number'))
        )

    def test_deserialize_fields(self):
        lhs = get_deserialized(RaceEntry.objects.all(), serializer=self.dumpdata, fields=('runner_number',))
        rhs = get_deserialized(RaceEntry.objects.all(), fields=('runner_number',))
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_modelserializer_deserialize(self):
        lhs = get_deserialized(RaceEntry.objects.all(), serializer=self.serializer)
        rhs = get_deserialized(RaceEntry.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_dumpdata_deserialize(self):
        lhs = get_deserialized(RaceEntry.objects.all(), serializer=self.dumpdata)
        rhs = get_deserialized(RaceEntry.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_dumpdata_deserialize_xml(self):
        lhs = get_deserialized(RaceEntry.objects.all(), format='xml', serializer=self.dumpdata)
        rhs = get_deserialized(RaceEntry.objects.all(), format='xml')
        self.assertTrue(deserialized_eq(lhs, rhs))

    # def test_xml_parsing(self):
    #     data = self.dumpdata.serialize('xml', RaceEntry.objects.all())
    #     object = list(self.dumpdata.deserialize('xml', data))[0].object
    #     print repr((object.name, object.runner_number, object.start_time, object.finish_time))


class TestNullPKModel(SerializationTestCase):
    def setUp(self):
        self.dumpdata = FixtureSerializer()
        self.serializer = RaceEntrySerializer()
        self.objs = [RaceEntry(
            name='John doe',
            runner_number=6014,
            start_time=datetime.datetime(year=2012, month=4, day=30, hour=9),
            finish_time=datetime.datetime(year=2012, month=4, day=30, hour=12, minute=25)
        )]

    def test_null_pk_dumpdata_json(self):
        self.assertEquals(
            self.dumpdata.serialize('json', self.objs),
            serializers.serialize('json', self.objs)
        )

    def test_null_pk_dumpdata_yaml(self):
        self.assertEquals(
            self.dumpdata.serialize('yaml', self.objs),
            serializers.serialize('yaml', self.objs)
        )

    def test_null_pk_dumpdata_xml(self):
        self.assertEquals(
            self.dumpdata.serialize('xml', self.objs),
            serializers.serialize('xml', self.objs)
        )

    def test_modelserializer_deserialize(self):
        lhs = get_deserialized(self.objs, serializer=self.serializer)
        rhs = get_deserialized(self.objs)
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_dumpdata_deserialize(self):
        lhs = get_deserialized(self.objs, serializer=self.dumpdata)
        rhs = get_deserialized(self.objs)
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_dumpdata_deserialize_xml(self):
        lhs = get_deserialized(self.objs, format='xml', serializer=self.dumpdata)
        rhs = get_deserialized(self.objs, format='xml')
        self.assertTrue(deserialized_eq(lhs, rhs))


##### Model Inheritance #####

class Account(models.Model):
    points = models.PositiveIntegerField()
    company = models.CharField(max_length=100)


class PremiumAccount(Account):
    date_upgraded = models.DateTimeField()


class PremiumAccountSerializer(ModelSerializer):
    class Meta:
        model = PremiumAccount


class TestModelInheritance(SerializationTestCase):
    def setUp(self):
        self.dumpdata = FixtureSerializer()
        self.serializer = PremiumAccountSerializer()
        PremiumAccount.objects.create(
            points=42,
            company='Foozle Inc.',
            date_upgraded=datetime.datetime(year=2012, month=4, day=30, hour=9)
        )

    def test_dumpdata_child_model(self):
        self.assertEquals(
            self.dumpdata.serialize('json', PremiumAccount.objects.all()),
            serializers.serialize('json', PremiumAccount.objects.all())
        )

    def test_serialize_child_model(self):
        expected = [{
            'id': 1,
            'points': 42,
            'company': 'Foozle Inc.',
            'date_upgraded': datetime.datetime(2012, 4, 30, 9, 0)
        }]
        self.assertEquals(
            self.serializer.serialize('python', PremiumAccount.objects.all()),
            expected
        )

    def test_modelserializer_deserialize(self):
        lhs = get_deserialized(PremiumAccount.objects.all(), serializer=self.serializer)
        rhs = get_deserialized(PremiumAccount.objects.all())
        self.assertFalse(deserialized_eq(lhs, rhs))
        # We expect these *not* to match - the dumpdata implementation only
        # includes the base fields.

    def test_dumpdata_deserialize(self):
        lhs = get_deserialized(PremiumAccount.objects.all(), serializer=self.dumpdata)
        rhs = get_deserialized(PremiumAccount.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))

    # TODO:
    # def test_dumpdata_deserialize_xml(self):
    #     lhs = get_deserialized(PremiumAccount.objects.all(), format='xml', serializer=self.dumpdata)
    #     rhs = get_deserialized(PremiumAccount.objects.all(), format='xml')
    #     self.assertTrue(deserialized_eq(lhs, rhs))


# ##### Natural Keys #####

class PetOwnerManager(models.Manager):
    def get_by_natural_key(self, first_name, last_name):
        return self.get(first_name=first_name, last_name=last_name)


class PetManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class PetOwner(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birthdate = models.DateField()

    def natural_key(self):
        return (self.first_name, self.last_name)

    class Meta:
        unique_together = (('first_name', 'last_name'),)

    objects = PetOwnerManager()


class Pet(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(PetOwner, related_name='pets')

    def natural_key(self):
        return self.name

    objects = PetManager()


class TestNaturalKey(SerializationTestCase):
    """
    Test one-to-one field relationship on a model.
    """
    def setUp(self):
        joe = PetOwner.objects.create(
            first_name='joe',
            last_name='adams',
            birthdate=datetime.date(year=1965, month=8, day=27)
        )
        Pet.objects.create(
            owner=joe,
            name='splash gordon'
        )
        Pet.objects.create(
            owner=joe,
            name='frogger'
        )

    def test_naturalkey_dumpdata_json(self):
        """
        Ensure that we can replicate the existing dumpdata
        'use_natural_keys' behaviour.
        """
        self.assertEquals(
            FixtureSerializer().serialize('json', Pet.objects.all(), use_natural_keys=True),
            serializers.serialize('json', Pet.objects.all(), use_natural_keys=True)
        )

    def test_naturalkey_dumpdata_yaml(self):
        """
        Ensure that we can replicate the existing dumpdata
        'use_natural_keys' behaviour.
        """
        self.assertEquals(
            FixtureSerializer().serialize('yaml', Pet.objects.all(), use_natural_keys=True),
            serializers.serialize('yaml', Pet.objects.all(), use_natural_keys=True)
        )

    def test_naturalkey_dumpdata_xml(self):
        """
        Ensure that we can replicate the existing dumpdata
        'use_natural_keys' behaviour.
        """
        self.assertEquals(
            FixtureSerializer().serialize('xml', Pet.objects.all(), use_natural_keys=True),
            serializers.serialize('xml', Pet.objects.all(), use_natural_keys=True)
        )

    def test_naturalkey(self):
        """
        Ensure that we can use NaturalKeyRelatedField to represent foreign
        key relationships.
        """
        class NaturalKeyModelSerializer(ModelSerializer):
            def get_related_field(self, model_field):
                return NaturalKeyRelatedField()

        expected = [{
            "owner": (u"joe", u"adams"),  # NK, not PK
            "id": 1,
            "name": u"splash gordon"
        }, {
            "owner": (u"joe", u"adams"),  # NK, not PK
            "id": 2,
            "name": u"frogger"
        }]
        self.assertEquals(
            NaturalKeyModelSerializer().serialize('python', Pet.objects.all()),
            expected
        )

    def test_naturalkey_reverse_relation(self):
        """
        Ensure that we can use NaturalKeyRelatedField to represent
        reverse foreign key relationships.
        """
        class PetOwnerSerializer(ModelSerializer):
            pets = NaturalKeyRelatedField()

        expected = [{
            "first_name": u"joe",
            "last_name": u"adams",
            "id": 1,
            "birthdate": datetime.date(1965, 8, 27),
            "pets": [u"splash gordon", u"frogger"]  # NK, not PK
        }]
        self.assertEquals(
            PetOwnerSerializer().serialize('python', PetOwner.objects.all()),
            expected
        )

    # def test_modelserializer_deserialize(self):
    #     lhs = get_deserialized(PetOwner.objects.all(), serializer=self.serializer)
    #     rhs = get_deserialized(PetOwner.objects.all())
    #     self.assertTrue(deserialized_eq(lhs, rhs))

    def test_dumpdata_deserialize(self):
        lhs = get_deserialized(Pet.objects.all(), serializer=FixtureSerializer(), use_natural_keys=True)
        rhs = get_deserialized(Pet.objects.all(), use_natural_keys=True)
        self.assertTrue(deserialized_eq(lhs, rhs))


##### One to one relationships #####

class User(models.Model):
    email = models.EmailField()


class Profile(models.Model):
    user = models.OneToOneField(User, related_name='profile')
    country_of_birth = models.CharField(max_length=100)
    date_of_birth = models.DateTimeField()


class ProfileSerializer(ModelSerializer):
    class Meta:
        model = Profile


class NestedProfileSerializer(ModelSerializer):
    class Meta:
        model = Profile
        nested = True


class TestOneToOneModel(SerializationTestCase):
    """
    Test one-to-one field relationship on a model.
    """
    def setUp(self):
        self.dumpdata = FixtureSerializer()
        self.profile_serializer = ProfileSerializer()
        user = User.objects.create(email='joe@example.com')
        Profile.objects.create(
            user=user,
            country_of_birth='UK',
            date_of_birth=datetime.datetime(day=5, month=4, year=1979)
        )

    def test_onetoone_dumpdata_json(self):
        self.assertEquals(
            self.dumpdata.serialize('json', Profile.objects.all()),
            serializers.serialize('json', Profile.objects.all())
        )

    def test_onetoone_dumpdata_yaml(self):
        self.assertEquals(
            self.dumpdata.serialize('yaml', Profile.objects.all()),
            serializers.serialize('yaml', Profile.objects.all())
        )

    def test_onetoone_dumpdata_xml(self):
        self.assertEquals(
            self.dumpdata.serialize('xml', Profile.objects.all()),
            serializers.serialize('xml', Profile.objects.all())
        )

    def test_onetoone_nested(self):
        expected = {
            'id': 1,
            'user': {
                'id': 1,
                'email': 'joe@example.com'
            },
            'country_of_birth': 'UK',
            'date_of_birth': datetime.datetime(day=5, month=4, year=1979)
        }
        self.assertEquals(
            NestedProfileSerializer().serialize('python', Profile.objects.get(id=1)),
            expected
        )

    def test_onetoone_flat(self):
        expected = {
            'id': 1,
            'user': 1,
            'country_of_birth': 'UK',
            'date_of_birth': datetime.datetime(day=5, month=4, year=1979)
        }
        self.assertEquals(
            self.profile_serializer.serialize('python', Profile.objects.get(id=1)),
            expected
        )

    def test_modelserializer_deserialize(self):
        lhs = get_deserialized(Profile.objects.all(), serializer=self.profile_serializer)
        rhs = get_deserialized(Profile.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_dumpdata_deserialize(self):
        lhs = get_deserialized(Profile.objects.all(), serializer=self.dumpdata)
        rhs = get_deserialized(Profile.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))


class TestReverseOneToOneModel(SerializationTestCase):
    """
    Test reverse relationship of one-to-one fields.

    Note the Django's dumpdata serializer doesn't support reverse relations,
    which wouldn't make sense in that context, so we don't include them in
    the tests.
    """

    def setUp(self):
        class NestedUserSerializer(ModelSerializer):
            profile = ModelSerializer()

        class FlatUserSerializer(ModelSerializer):
            profile = PrimaryKeyRelatedField()

        self.nested_model = NestedUserSerializer()
        self.flat_model = FlatUserSerializer()
        user = User.objects.create(email='joe@example.com')
        Profile.objects.create(
            user=user,
            country_of_birth='UK',
            date_of_birth=datetime.datetime(day=5, month=4, year=1979)
        )

    def test_reverse_onetoone_nested(self):
        expected = {
            'id': 1,
            'email': u'joe@example.com',
            'profile': {
                'id': 1,
                'country_of_birth': u'UK',
                'date_of_birth': datetime.datetime(day=5, month=4, year=1979),
                'user': 1
            },
        }
        self.assertEquals(
            self.nested_model.serialize('python', User.objects.get(id=1)),
            expected
        )

    def test_reverse_onetoone_flat(self):
        expected = {
            'id': 1,
            'email': 'joe@example.com',
            'profile': 1,
        }
        self.assertEquals(
            self.flat_model.serialize('python', User.objects.get(id=1)),
            expected
        )


class Owner(models.Model):
    email = models.EmailField()


class Vehicle(models.Model):
    owner = models.ForeignKey(Owner, related_name='vehicles')
    licence = models.CharField(max_length=20)
    date_of_manufacture = models.DateField()


class VehicleSerializer(ModelSerializer):
    class Meta:
        model = Vehicle


class NestedVehicleSerializer(ModelSerializer):
    class Meta:
        model = Vehicle
        nested = True


class TestFKModel(SerializationTestCase):
    """
    Test one-to-one field relationship on a model.
    """
    def setUp(self):
        self.dumpdata = FixtureSerializer()
        self.nested_model = NestedVehicleSerializer()
        self.flat_model = VehicleSerializer()
        self.owner = Owner.objects.create(
            email='tom@example.com'
        )
        self.car = Vehicle.objects.create(
            owner=self.owner,
            licence='DJANGO42',
            date_of_manufacture=datetime.date(day=6, month=6, year=2005)
        )
        self.bike = Vehicle.objects.create(
            owner=self.owner,
            licence='',
            date_of_manufacture=datetime.date(day=8, month=8, year=1990)
        )

    def test_fk_dumpdata_json(self):
        self.assertEquals(
            self.dumpdata.serialize('json', Vehicle.objects.all()),
            serializers.serialize('json', Vehicle.objects.all())
        )

    def test_fk_dumpdata_yaml(self):
        self.assertEquals(
            self.dumpdata.serialize('yaml', Vehicle.objects.all()),
            serializers.serialize('yaml', Vehicle.objects.all())
        )

    def test_fk_dumpdata_xml(self):
        self.assertEquals(
            self.dumpdata.serialize('xml', Vehicle.objects.all()),
            serializers.serialize('xml', Vehicle.objects.all())
        )

    def test_fk_nested(self):
        expected = {
            'id': 1,
            'owner': {
                'id': 1,
                'email': u'tom@example.com'
            },
            'licence': u'DJANGO42',
            'date_of_manufacture': datetime.date(day=6, month=6, year=2005)
        }
        self.assertEquals(
            self.nested_model.serialize('python', Vehicle.objects.get(id=1)),
            expected
        )

    def test_fk_flat(self):
        expected = {
            'id': 1,
            'owner':  1,
            'licence': u'DJANGO42',
            'date_of_manufacture': datetime.date(day=6, month=6, year=2005)
        }
        self.assertEquals(
            self.flat_model.serialize('python', Vehicle.objects.get(id=1)),
            expected
        )

    def test_modelserializer_deserialize(self):
        lhs = get_deserialized(Vehicle.objects.all(), serializer=self.flat_model)
        rhs = get_deserialized(Vehicle.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_dumpdata_deserialize(self):
        lhs = get_deserialized(Vehicle.objects.all(), serializer=self.dumpdata)
        rhs = get_deserialized(Vehicle.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_reverse_fk_flat(self):
        class OwnerSerializer(ModelSerializer):
            vehicles = PrimaryKeyRelatedField()

        expected = {
            'id': 1,
            'email': u'tom@example.com',
            'vehicles':  [1, 2]
        }

        self.assertEquals(
            OwnerSerializer().serialize('python', Owner.objects.get(id=1)),
            expected
        )

    def test_reverse_fk_nested(self):
        class OwnerSerializer(ModelSerializer):
            vehicles = ModelSerializer()

        expected = {
            'id': 1,
            'email': u'tom@example.com',
            'vehicles': [
                {
                    'id': 1,
                    'licence': u'DJANGO42',
                    'owner': 1,
                    'date_of_manufacture': datetime.date(day=6, month=6, year=2005)
                }, {
                    'id': 2,
                    'licence': u'',
                    'owner': 1,
                    'date_of_manufacture': datetime.date(day=8, month=8, year=1990)
                }
            ]
        }
        self.assertEquals(
            OwnerSerializer().serialize('python', Owner.objects.get(id=1)),
            expected
        )


class Author(models.Model):
    name = models.CharField(max_length=100)


class Book(models.Model):
    authors = models.ManyToManyField(Author, related_name='books')
    title = models.CharField(max_length=100)
    in_stock = models.BooleanField()


class BookSerializer(ModelSerializer):
    class Meta:
        model = Book


class NestedBookSerializer(ModelSerializer):
    class Meta:
        model = Book
        nested = True


class TestManyToManyModel(SerializationTestCase):
    """
    Test one-to-one field relationship on a model.
    """
    def setUp(self):
        self.dumpdata = FixtureSerializer()
        self.nested_model = NestedBookSerializer()
        self.flat_model = BookSerializer()
        self.lucy = Author.objects.create(
            name='Lucy Black'
        )
        self.mark = Author.objects.create(
            name='Mark Green'
        )
        self.cookbook = Book.objects.create(
            title='Cooking with gas',
            in_stock=True
        )
        self.cookbook.authors = [self.lucy, self.mark]
        self.cookbook.save()

        self.otherbook = Book.objects.create(
            title='Chimera obscura',
            in_stock=False
        )
        self.otherbook.authors = [self.mark]
        self.otherbook.save()

    def test_m2m_dumpdata_json(self):
        self.assertEquals(
            self.dumpdata.serialize('json', Book.objects.all()),
            serializers.serialize('json', Book.objects.all())
        )
        self.assertEquals(
            self.dumpdata.serialize('json', Author.objects.all()),
            serializers.serialize('json', Author.objects.all())
        )

    def test_m2m_dumpdata_yaml(self):
        self.assertEquals(
            self.dumpdata.serialize('yaml', Book.objects.all()),
            serializers.serialize('yaml', Book.objects.all())
        )
        self.assertEquals(
            self.dumpdata.serialize('yaml', Author.objects.all()),
            serializers.serialize('yaml', Author.objects.all())
        )

    def test_m2m_dumpdata_xml(self):
        # # Hack to ensure field ordering is correct for xml
        # dumpdata = FixtureSerializer()
        # dumpdata.fields['fields'].opts.preserve_field_order = True
        self.assertEquals(
            self.dumpdata.serialize('xml', Book.objects.all()),
            serializers.serialize('xml', Book.objects.all())
        )
        self.assertEquals(
            self.dumpdata.serialize('xml', Author.objects.all()),
            serializers.serialize('xml', Author.objects.all())
        )

    def test_m2m_nested(self):
        expected = {
            'id': 1,
            'title': u'Cooking with gas',
            'in_stock': True,
            'authors': [
                {'id': 1, 'name': 'Lucy Black'},
                {'id': 2, 'name': 'Mark Green'}
            ]
        }
        self.assertEquals(
            self.nested_model.serialize('python', Book.objects.get(id=1)),
            expected
        )

    def test_m2m_flat(self):
        expected = {
            'id': 1,
            'title': u'Cooking with gas',
            'in_stock': True,
            'authors': [1, 2]
        }
        self.assertEquals(
            self.flat_model.serialize('python', Book.objects.get(id=1)),
            expected
        )

    def test_modelserializer_deserialize(self):
        lhs = get_deserialized(Book.objects.all(), serializer=self.flat_model)
        rhs = get_deserialized(Book.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_dumpdata_deserialize(self):
        lhs = get_deserialized(Book.objects.all(), serializer=self.dumpdata)
        rhs = get_deserialized(Book.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))


class Anchor(models.Model):
    data = models.CharField(max_length=30)

    class Meta:
        ordering = ('id',)


class M2MIntermediateData(models.Model):
    data = models.ManyToManyField(Anchor, null=True, through='Intermediate')


class Intermediate(models.Model):
    left = models.ForeignKey(M2MIntermediateData)
    right = models.ForeignKey(Anchor)
    extra = models.CharField(max_length=30, blank=True, default="doesn't matter")


class TestManyToManyThroughModel(SerializationTestCase):
    """
    Test one-to-one field relationship on a model with a 'through' relationship.
    """
    def setUp(self):
        self.dumpdata = FixtureSerializer()
        right = Anchor.objects.create(data='foobar')
        left = M2MIntermediateData.objects.create()
        Intermediate.objects.create(extra='wibble', left=left, right=right)
        self.obj = left

    def test_m2m_through_dumpdata_json(self):
        self.assertEquals(
            self.dumpdata.serialize('json', M2MIntermediateData.objects.all()),
            serializers.serialize('json', M2MIntermediateData.objects.all())
        )
        self.assertEquals(
            self.dumpdata.serialize('json', Anchor.objects.all()),
            serializers.serialize('json', Anchor.objects.all())
        )


class ComplexModel(models.Model):
    field1 = models.CharField(max_length=10)
    field2 = models.CharField(max_length=10)
    field3 = models.CharField(max_length=10)


class FieldsTest(SerializationTestCase):
    def test_fields(self):
        obj = ComplexModel(field1='first', field2='second', field3='third')

        # Serialize then deserialize the test database
        serialized_data = FixtureSerializer().serialize('json', [obj], indent=2, fields=('field1', 'field3'))
        result = next(FixtureSerializer().deserialize('json', serialized_data))

        # Check that the deserialized object contains data in only the serialized fields.
        self.assertEqual(result.object.field1, 'first')
        self.assertEqual(result.object.field2, '')
        self.assertEqual(result.object.field3, 'third')


class Actor(models.Model):
    name = models.CharField(max_length=20, primary_key=True)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name


class Movie(models.Model):
    actor = models.ForeignKey(Actor)
    title = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ('title',)

    def __unicode__(self):
        return self.title


class NonIntegerPKTests(SerializationTestCase):
    def test_unicode_fk(self):
        actor_name = u"Za\u017c\u00f3\u0142\u0107"
        movie_title = u'G\u0119\u015bl\u0105 ja\u017a\u0144'
        ac = Actor(name=actor_name)
        mv = Movie(title=movie_title, actor=ac)
        ac.save()
        mv.save()

        serial_str = FixtureSerializer().serialize('json', [mv])
        self.assertEqual(serializers.serialize('json', [mv]), serial_str)

        obj_list = list(FixtureSerializer().deserialize('json', serial_str))
        mv_obj = obj_list[0].object
        self.assertEqual(mv_obj.title, movie_title)

    def test_unicode_pk(self):
        actor_name = u"Za\u017c\u00f3\u0142\u0107"
        movie_title = u'G\u0119\u015bl\u0105 ja\u017a\u0144'
        ac = Actor(name=actor_name)
        mv = Movie(title=movie_title, actor=ac)
        ac.save()
        mv.save()

        serial_str = FixtureSerializer().serialize('json', [ac])
        self.assertEqual(serializers.serialize('json', [ac]), serial_str)

        obj_list = list(FixtureSerializer().deserialize('json', serial_str))
        ac_obj = obj_list[0].object
        self.assertEqual(ac_obj.name, actor_name)


class FileData(models.Model):
    data = models.FileField(null=True, upload_to='/foo/bar')


class FileFieldTests(SerializationTestCase):
    def test_serialize_file_field(self):
        FileData().save()
        self.assertEquals(
            FixtureSerializer().serialize('json', FileData.objects.all()),
            serializers.serialize('json', FileData.objects.all())
        )


class Category(models.Model):
    name = models.CharField(max_length=20)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name


class ArticleAuthor(models.Model):
    name = models.CharField(max_length=20)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name


class Article(models.Model):
    author = models.ForeignKey(ArticleAuthor)
    headline = models.CharField(max_length=50)
    pub_date = models.DateTimeField()
    categories = models.ManyToManyField(Category)

    class Meta:
        ordering = ('pub_date', )

    def __unicode__(self):
        return self.headline


class TestRoundtrips(SerializationTestCase):
    def setUp(self):
        sports = Category.objects.create(name="Sports")
        music = Category.objects.create(name="Music")
        op_ed = Category.objects.create(name="Op-Ed")

        self.joe = ArticleAuthor.objects.create(name="Joe")
        self.jane = ArticleAuthor.objects.create(name="Jane")

        self.a1 = Article(
            author=self.jane,
            headline="Poker has no place on ESPN",
            pub_date=datetime.datetime(2006, 6, 16, 11, 00)
        )
        self.a1.save()
        self.a1.categories = [sports, op_ed]

        self.a2 = Article(
            author=self.joe,
            headline="Time to reform copyright",
            pub_date=datetime.datetime(2006, 6, 16, 13, 00, 11, 345)
        )
        self.a2.save()
        self.a2.categories = [music, op_ed]

    def test_serializer_roundtrip(self):
        """Tests that serialized content can be deserialized."""
        serial_str = FixtureSerializer().serialize('xml', Article.objects.all())
        models = list(FixtureSerializer().deserialize('xml', serial_str))
        self.assertEqual(len(models), 2)

    def test_altering_serialized_output(self):
        """
        Tests the ability to create new objects by
        modifying serialized content.
        """
        old_headline = "Poker has no place on ESPN"
        new_headline = "Poker has no place on television"
        serial_str = FixtureSerializer().serialize('xml', Article.objects.all())

        serial_str = serial_str.replace(old_headline, new_headline)
        models = list(FixtureSerializer().deserialize('xml', serial_str))

        # Prior to saving, old headline is in place
        self.assertTrue(Article.objects.filter(headline=old_headline))
        self.assertFalse(Article.objects.filter(headline=new_headline))

        for model in models:
            model.save()

        # After saving, new headline is in place
        self.assertTrue(Article.objects.filter(headline=new_headline))
        self.assertFalse(Article.objects.filter(headline=old_headline))

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from django.utils.datastructures import SortedDict
from django.utils.timezone import is_aware

import csv
import datetime
import decimal
import inspect
import types
from django.utils import simplejson as json


def is_simple_callable(obj):
    """
    True if the object is a callable that takes no arguments.
    """
    return (
        (inspect.isfunction(obj) and not inspect.getargspec(obj)[0]) or
        (inspect.ismethod(obj) and len(inspect.getargspec(obj)[0]) <= 1)
    )


class DictWithMetadata(dict):
    """
    A dict-like object, that can have additional metadata attached.
    """
    def __init__(self, *args, **kwargs):
        super(DictWithMetadata, self).__init__(*args, **kwargs)
        self.metadata = {}


class SortedDictWithMetadata(SortedDict, DictWithMetadata):
    pass


try:
    import yaml
except ImportError:
    SafeDumper = None
else:
    # Adapted from http://pyyaml.org/attachment/ticket/161/use_ordered_dict.py
    class SafeDumper(yaml.SafeDumper):
        """
        Handles decimals as strings.
        Handles SortedDicts as usual dicts, but preserves field order, rather
        than the usual behaviour of sorting the keys.
        """
        def represent_decimal(self, data):
            return self.represent_scalar('tag:yaml.org,2002:str', str(data))

        def represent_mapping(self, tag, mapping, flow_style=None):
            value = []
            node = yaml.MappingNode(tag, value, flow_style=flow_style)
            if self.alias_key is not None:
                self.represented_objects[self.alias_key] = node
            best_style = True
            if hasattr(mapping, 'items'):
                mapping = list(mapping.items())
                if not isinstance(mapping, SortedDict):
                    mapping.sort()
            for item_key, item_value in mapping:
                node_key = self.represent_data(item_key)
                node_value = self.represent_data(item_value)
                if not (isinstance(node_key, yaml.ScalarNode) and not node_key.style):
                    best_style = False
                if not (isinstance(node_value, yaml.ScalarNode) and not node_value.style):
                    best_style = False
                value.append((node_key, node_value))
            if flow_style is None:
                if self.default_flow_style is not None:
                    node.flow_style = self.default_flow_style
                else:
                    node.flow_style = best_style
            return node

    SafeDumper.add_representer(DictWithMetadata,
            yaml.representer.SafeRepresenter.represent_dict)
    SafeDumper.add_representer(SortedDictWithMetadata,
            yaml.representer.SafeRepresenter.represent_dict)
    SafeDumper.add_representer(types.GeneratorType,
            yaml.representer.SafeRepresenter.represent_list)


class DjangoJSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time and decimal types.
    """
    def default(self, o):
        # See "Date Time String Format" in the ECMA-262 specification.
        if isinstance(o, datetime.datetime):
            r = o.isoformat()
            if o.microsecond:
                r = r[:23] + r[26:]
            if r.endswith('+00:00'):
                r = r[:-6] + 'Z'
            return r
        elif isinstance(o, datetime.date):
            return o.isoformat()
        elif isinstance(o, datetime.time):
            if is_aware(o):
                raise ValueError("JSON can't represent timezone-aware times.")
            r = o.isoformat()
            if o.microsecond:
                r = r[:12]
            return r
        elif isinstance(o, decimal.Decimal):
            return str(o)
        elif hasattr(o, '__iter__'):
            return [i for i in o]
        return super(DjangoJSONEncoder, self).default(o)


class DictWriter(csv.DictWriter):
    """
    >>> from cStringIO import StringIO
    >>> f = StringIO()
    >>> w = DictWriter(f, ['a', 'b'], restval=u'î')
    >>> w.writerow({'a':'1'})
    >>> w.writerow({'a':'1', 'b':u'ø'})
    >>> w.writerow({'a':u'é'})
    >>> f.seek(0)
    >>> r = DictReader(f, fieldnames=['a'], restkey='r')
    >>> r.next() == {'a':u'1', 'r':[u"î"]}
    True
    >>> r.next() == {'a':u'1', 'r':[u"ø"]}
    True
    >>> r.next() == {'a':u'é', 'r':[u"î"]}
    """
    def __init__(self, csvfile, fieldnames, restval='', extrasaction='raise', dialect='excel', encoding='utf-8', *args, **kwds):
        self.fieldnames = fieldnames
        self.encoding = encoding
        self.restval = restval
        self.writer = csv.DictWriter(csvfile, fieldnames, restval, extrasaction, dialect, *args, **kwds)

    def _stringify(self, s, encoding):
        if type(s) == unicode:
            return s.encode(encoding)
        elif isinstance(s, (int, float)):
            pass  # let csv.QUOTE_NONNUMERIC do its thing.
        elif type(s) != str:
            s = str(s)
        return s

    def writeheader(self):
        header = dict([(item, item) for item in self.fieldnames])
        self.writerow(header)

    def writerow(self, d):
        for fieldname in self.fieldnames:
            if fieldname in d:
                d[fieldname] = self._stringify(d[fieldname], self.encoding)
            else:
                d[fieldname] = self._stringify(self.restval, self.encoding)
        self.writer.writerow(d)

########NEW FILE########
__FILENAME__ = settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'tmp.db',
    },
}

INSTALLED_APPS = (
    'serializers',
)

########NEW FILE########
__FILENAME__ = testsettings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

INSTALLED_APPS = (
    'serializers',
)

########NEW FILE########
