__FILENAME__ = conf
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

import os
import sys

sys.path.insert(0, os.path.abspath('..'))
sys.path.append(os.path.abspath('_themes'))

sys.path.append(os.path.abspath('../tests'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'testproject.settings'


project = "Save The Change"
copyright = "2013, Karan Lyons"
version = release = "1.0.0"
language = 'English'

extensions = [
	'sphinx.ext.autodoc',
	'sphinx.ext.intersphinx',
	'sphinx.ext.viewcode',
	'sphinx.ext.coverage'
]
intersphinx_mapping = {
	'python': ('http://docs.python.org/2.7', None),
	'django': ('https://docs.djangoproject.com/en/1.5', 'https://docs.djangoproject.com/en/1.5/_objects'),
}
templates_path = ['_templates']
exclude_patterns = ['_build']
html_theme_path = ['_themes']
html_static_path = ['_static']
source_suffix = '.rst'
master_doc = 'index'

add_function_parentheses = True
add_module_names = True
pygments_style = 'sphinx'

htmlhelp_basename = 'save_the_change_docs'
html_title = "Save The Change {version} Documentation".format(version=version)
html_short_title = "Save The Change"
html_last_updated_fmt = ''
html_show_sphinx = False

if os.environ.get('READTHEDOCS', None) == 'True':
	html_theme = 'default'

else:
	html_theme = 'flask'
	html_theme_options = {
		'index_logo': '',
		'index_logo_height': '0px',
	}

########NEW FILE########
__FILENAME__ = mixins
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

from collections import defaultdict
from copy import copy

from django.db import models
from django.utils import six
from django.db.models import ManyToManyField, ForeignKey
from django.db.models.related import RelatedObject


__all__ = ('SaveTheChange', 'TrackChanges')


class DoesNotExist:
	"""
	It's unlikely, but there could potentially be a time when a field is added
	to or removed from an instance. This class represents a field in a state of
	nonexistance, just in case we ever run into it.
	
	"""
	
	pass


class BaseChangeTracker(object):
	"""
	Adds a :py:class:`dict` named :attr:`._changed_fields` to the model, which
	stores fields that have changed. The key is the field name, and the value
	the original value of the field from the database.
	
	If the value of a field is changed back to its original value, its entry is
	removed from :attr:`._changed_fields`. Thus, overhead is kept at a minimum.
	
	A caveat: This can't do anything to help you with
	:class:`~django.db.models.ManyToManyField`\s nor reverse relationships, which
	is par for the course: they aren't handled by
	:meth:`~django.db.models.Model.save`, but are pushed to the database
	immediately when changed.
	
	"""
	
	def __init__(self, *args, **kwargs):
		super(BaseChangeTracker, self).__init__(*args, **kwargs)
		
		self._changed_fields = {} #: A :py:class:`dict` storing changed fields.
	
	def __setattr__(self, name, value):
		"""
		Updates :attr:`._changed_fields` when new values are set for fields.
		
		"""
		
		if hasattr(self, '_changed_fields'):
			try:
				name_map = self._meta._name_map
			
			except AttributeError:
				name_map = self._meta.init_name_map()
			
			if name in name_map and name_map[name][0].__class__ not in (ManyToManyField, RelatedObject):
				field = name_map[name][0]
				
				if isinstance(field, ForeignKey) and field.null is False:
					# Required ForeignKey fields raise a DoesNotExist error if
					# there is an attempt to get the value and it has not been
					# assigned yet. Handle this gracefully.
					try:
						old = getattr(self, name, DoesNotExist)
					
					except field.rel.to.DoesNotExist:
						old = None
				
				else:
					old = getattr(self, name, DoesNotExist)
				
				# A parent's __setattr__ may change value.
				super(BaseChangeTracker, self).__setattr__(name, value)
				new = getattr(self, name, DoesNotExist)
				
				try:
					changed = (old != new)
				
				except: # pragma: no cover (covers naive/aware datetime comparison failure; unreachable in py3)
					changed = True
				
				if changed:
					changed_fields = self._changed_fields
					
					if name in changed_fields:
						if changed_fields[name] == new:
							# We've changed this field back to its original
							# value from the database. No need to push it
							# back up.
							changed_fields.pop(name)
					
					else:
						changed_fields[name] = copy(old)
			
			else:
				super(BaseChangeTracker, self).__setattr__(name, value)
		
		else:
			super(BaseChangeTracker, self).__setattr__(name, value)
	
	def save(self, *args, **kwargs):
		"""
		Clears :attr:`._changed_fields`.
		
		"""
		
		super(BaseChangeTracker, self).save(*args, **kwargs)
		
		self._changed_fields = {}


class SaveTheChange(BaseChangeTracker):
	"""
	A model mixin that keeps track of fields that have changed since model
	instantiation, and when saved updates only those fields.
	
	If :meth:`~django.db.models.Model.save` is called with ``update_fields``,
	the passed ``kwarg`` is given precedence. Similarly, if ``force_insert`` is
	set, ``update_fields`` will not be.
	
	"""
	
	def save(self, *args, **kwargs):
		"""
		Builds and passes the ``update_fields`` kwarg to Django.
		
		"""
		
		if self.pk and hasattr(self, '_changed_fields') and 'update_fields' not in kwargs and not kwargs.get('force_insert', False):
			kwargs['update_fields'] = [key for key, value in six.iteritems(self._changed_fields) if hasattr(self, key)]
		
		super(SaveTheChange, self).save(*args, **kwargs)


class TrackChanges(BaseChangeTracker):
	"""
	A model mixin that tracks model fields' values and provide some properties
	and methods to work with the old/new values.
	
	"""
	
	@property
	def has_changed(self):
		"""
		A :py:obj:`bool` indicating if any fields have changed.
		
		"""
		
		return bool(self._changed_fields)
	
	@property
	def changed_fields(self):
		"""
		A :py:obj:`tuple` of changed fields.
		
		"""
		
		return tuple(self._changed_fields.keys())
	
	@property
	def old_values(self):
		"""
		A :py:class:`dict` of the old field values.
		
		"""
		
		old_values = self.new_values
		old_values.update(self._changed_fields)
		
		return old_values
	
	@property
	def new_values(self):
		"""
		A :py:class:`dict` of the new field values.
		
		"""
		
		try:
			name_map = self._meta._name_map
		
		except AttributeError:
			name_map = self._meta.init_name_map()
		
		return dict([(field, getattr(self, field)) for field in name_map])
	
	def revert_fields(self, fields=None):
		"""
		Reverts supplied fields to their original values.
		
		:param list fields: Fields to revert.
		
		"""
		
		for field in fields:
			if field in self._changed_fields:
				setattr(self, field, self._changed_fields[field])


class UpdateTogetherMeta(models.base.ModelBase):
	"""
	A metaclass that hides our added ``update_together`` attribute from the
	instance's ``Meta``, since otherwise Django's fascistic Meta options
	sanitizer will throw an exception.
	
	(If you have another mixin that adds to your model's ``Meta``, create a
	``metaclass`` that inherits from both this and the other
	mixin's ``metaclass``.)
	
	"""
	
	def __new__(cls, name, bases, attrs):
		if not [b for b in bases if isinstance(b, UpdateTogetherMeta)]:
			return super(UpdateTogetherMeta, cls).__new__(cls, name, bases, attrs)
		
		else:
			meta = None
			update_together = ()
			
			# Deferred fields won't have our model's Meta.
			if 'Meta' in attrs and attrs['Meta'].__module__ != 'django.db.models.query_utils':
				meta = attrs.get('Meta')
			
			else:
				for base in bases:
					meta = getattr(base, '_meta', None)
					
					if meta:
						break
			
			if meta and hasattr(meta, 'update_together'):
				update_together = getattr(meta, 'update_together')
				delattr(meta, 'update_together')
			
			new_class = super(UpdateTogetherMeta, cls).__new__(cls, name, bases, attrs)
			
			mapping = defaultdict(set)
			for codependents in update_together:
				for dependent in codependents:
					mapping[dependent].update(codependents)
			
			update_together = dict(mapping)
			
			if meta:
				setattr(meta, 'update_together', update_together)
			
			setattr(new_class._meta, 'update_together', update_together)
			
			return new_class


class UpdateTogetherModel(BaseChangeTracker, models.Model, six.with_metaclass(UpdateTogetherMeta)):
	"""
	A replacement for :class:`~django.db.models.Model` which allows you to
	specify the ``Meta`` attribute ``update_together``: a
	:py:obj:`list`/:py:obj:`tuple` of :py:obj:`list`\s/:py:obj:`tuple`\s
	defining fields that should always be updated together if any of
	them change.
	
	"""
	
	def save(self, *args, **kwargs):
		if 'update_fields' in kwargs:
			update_fields = set(kwargs['update_fields'])
			
			for field in kwargs['update_fields']:
				update_fields.update(self._meta.update_together.get(field, []))
			
			kwargs['update_fields'] = list(update_fields)
		
		super(UpdateTogetherModel, self).save(*args, **kwargs)
	
	class Meta:
		abstract = True

########NEW FILE########
__FILENAME__ = manage
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

import os
import sys


if __name__ == "__main__":
	os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testproject.settings')
	from django.core.management import execute_from_command_line
	execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = test
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['DJANGO_SETTINGS_MODULE'] = 'testproject.settings'

from django.test.utils import get_runner
from django.conf import settings


def run_tests():
	sys.exit(bool(get_runner(settings)(verbosity=1, interactive=True).run_tests(['testapp'])))


if __name__ == '__main__':
	run_tests()

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

import os
import sys


sys.path.insert(0, '..')

DEBUG = TEMPLATE_DEBUG = True

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': 'test_database'
	},
}

TIME_ZONE = 'UTC'
USE_TZ = True

MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'uploads')

SECRET_KEY = 'q+xn9-%#q-u2zu*)utsl)wde%&k6ci88hqpjo1w9=2*@l*3ydl'

INSTALLED_APPS = (
	'testproject.testapp',
)

TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

import os

from django.db import models
from django.utils import six

from save_the_change.mixins import SaveTheChange, TrackChanges, UpdateTogetherModel


class Enlightenment(models.Model):
	"""
	A model to test ForeignKeys.
	
	"""
	
	aspect = models.CharField(max_length=32)


class EnlightenedModel(SaveTheChange, TrackChanges, UpdateTogetherModel):
	"""
	A model to test (almost) everything else.
	
	TODO: Figure out a way to properly test {File,Image}Fields.
	
	"""
	
	big_integer = models.BigIntegerField()
	boolean = models.BooleanField()
	char = models.CharField(max_length=32)
	comma_seperated_integer = models.CommaSeparatedIntegerField(max_length=32)
	date = models.DateField()
	date_time = models.DateTimeField()
	decimal = models.DecimalField(max_digits=16, decimal_places=8)
	email = models.EmailField()
	enlightenment = models.ForeignKey(Enlightenment)
#	file = models.FileField(upload_to='./')
	file_path = models.FilePathField(path=os.path.join(__file__, '..', 'uploads'))
	float = models.FloatField()
#	image = models.ImageField(upload_to='./')
	integer = models.IntegerField()
	IP_address = models.IPAddressField()
	generic_IP = models.GenericIPAddressField()
	null_boolean = models.NullBooleanField()
	positive_integer = models.PositiveIntegerField()
	positive_small_integer = models.PositiveSmallIntegerField()
	slug = models.SlugField()
	small_integer = models.SmallIntegerField()
	text = models.TextField()
	time = models.TimeField()
	URL = models.URLField()
	
	class Meta:
		update_together = (
			('big_integer', 'small_integer'),
		)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

import os
import datetime
import pytz
from decimal import Decimal

from django.core.files import File
from django.core.files.images import ImageFile
from django.db import models
from django.db.models.fields.files import FieldFile, ImageFieldFile
from django.test import TestCase

from testproject.testapp.models import Enlightenment, EnlightenedModel


class EnlightenedModelTestCase(TestCase):
	def setUp(self):
		super(EnlightenedModelTestCase, self).setUp()
		
		self.maxDiff = None
		
		self.penny_front = os.path.abspath(os.path.join(__file__, '..', '..', '..', 'penny_front.png'))
		self.penny_back = os.path.abspath(os.path.join(__file__, '..', '..', '..', 'penny_back.png'))
		
		self.uploads = os.path.abspath(os.path.join(self.penny_front, '..', 'testproject', 'uploads'))
		
		self.knowledge = Enlightenment.objects.create(aspect='knowledge')
		self.wisdom = Enlightenment.objects.create(aspect='wisdom')
		
		self.old_values = {
			'big_integer': 3735928559,
			'boolean': True,
			'char': '2 cents',
			'comma_seperated_integer': '4,8,15',
			'date': datetime.date(1999, 12, 31),
			'date_time': datetime.datetime(1999, 12, 31, 23, 59, 59),
			'decimal': Decimal('0.02'),
			'email': 'gautama@kapilavastu.org',
			'enlightenment': self.knowledge,
#			'file': File(open(self.penny_front), 'penny_front_file.png'),
			'file_path': 'uploads/penny_front_file.png',
			'float': 1.61803,
#			'image': ImageFile(open(self.penny_front), 'penny_front_image.png'),
			'integer': 42,
			'IP_address': '127.0.0.1',
			'generic_IP': '::1',
			'null_boolean': None,
			'positive_integer': 1,
			'positive_small_integer': 2,
			'slug': 'onchidiacea',
			'small_integer': 4,
			'text': 'old',
			'time': datetime.time(23, 59, 59),
			'URL': 'http://djangosnippets.org/snippets/2985/',
		}
		
		self.new_values = {
			'big_integer': 3735928495,
			'boolean': False,
			'char': 'Three fiddy',
			'comma_seperated_integer': '16,23,42',
			'date': datetime.date(2000, 1, 1),
			'date_time': pytz.utc.localize(datetime.datetime(2000, 1, 1, 0, 0, 0)),
			'decimal': Decimal('3.50'),
			'email': 'maitreya@unknown.org',
			'enlightenment': self.wisdom,
#			'file': File(open(self.penny_back), 'penny_back_file.png'),
			'file_path': 'uploads/penny_back_file.png',
			'float': 3.14159,
#			'image': ImageFile(open(self.penny_back), 'penny_back_image.png'),
			'integer': 108,
			'IP_address': '255.255.255.255',
			'generic_IP': 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff',
			'null_boolean': True,
			'positive_integer': 5,
			'positive_small_integer': 6,
			'slug': 'soleolifera',
			'small_integer': 9,
			'text': 'new',
			'time': datetime.time(0, 0, 0),
			'URL': 'https://github.com/karanlyons/django-save-the-change',
		}
	
	def create_initial(self):
		self.tearDown()
		
		m = EnlightenedModel(**self.old_values)
		m.save()
		
		self.old_values['id'] = m.id
		self.new_values['id'] = m.id
		
		return m
	
	def create_changed(self):
		m = self.create_initial()
		
		for field_name, value in self.new_values.items():
			setattr(m, field_name, value)
		
		return m
	
	def create_reverted(self):
		m = self.create_changed()
		
		for field_name, value in self.old_values.items():
			setattr(m, field_name, value)
		
		return m
	
	def create_saved(self):
		m = self.create_changed()
		
		m.save()
		
		self.old_values['id'] = m.id
		self.new_values['id'] = m.id
		
		return m
	
	def test_initial__changed_fields(self):
		m = self.create_initial()
		
		self.assertEquals(m._changed_fields, {})
	
	def test_initial_changed_fields(self):
		m = self.create_initial()
		
		self.assertEquals(m.changed_fields, ())
	
	def test_initial_has_changed(self):
		m = self.create_initial()
		
		self.assertEquals(m.has_changed, False)
	
	def test_initial_new_values(self):
		m = self.create_initial()
		
		self.assertEquals(m.new_values, self.old_values)
	
	def test_initial_old_values(self):
		m = self.create_initial()
		
		self.assertEquals(m.old_values, self.old_values)
	
	def test_changed__changed_fields(self):
		m = self.create_changed()
		old_values = self.old_values
		old_values.pop('id')
		
		self.assertEquals(m._changed_fields, old_values)
	
	def test_changed_changed_fields(self):
		m = self.create_changed()
		new_values = self.new_values
		new_values.pop('id')
		
		self.assertEquals(sorted(m.changed_fields), sorted(new_values.keys()))
	
	def test_changed_has_changed(self):
		m = self.create_changed()
		
		self.assertEquals(m.has_changed, True)
	
	def test_changed_new_values(self):
		m = self.create_changed()
		
		self.assertEquals(m.new_values, self.new_values)
	
	def test_changed_old_values(self):
		m = self.create_changed()
		
		self.assertEquals(m.old_values, self.old_values)
	
	def test_changed_reverts(self):
		m = self.create_changed()
		
		m.revert_fields(self.new_values.keys())
		
		self.assertEquals(m.new_values, self.old_values)
	
	def test_reverted__changed_fields(self):
		m = self.create_reverted()
		
		self.assertEquals(m._changed_fields, {})
	
	def test_reverted_changed_fields(self):
		m = self.create_reverted()
		
		self.assertEquals(m.changed_fields, ())
	
	def test_reverted_has_changed(self):
		m = self.create_reverted()
		
		self.assertEquals(m.has_changed, False)
	
	def test_reverted_new_values(self):
		m = self.create_reverted()
		
		self.assertEquals(m.new_values, self.old_values)
	
	def test_reverted_old_values(self):
		m = self.create_reverted()
		
		self.assertEquals(m.old_values, self.old_values)
	
	def test_saved__changed_fields(self):
		m = self.create_saved()
		
		self.assertEquals(m._changed_fields, {})
	
	def test_saved_changed_fields(self):
		m = self.create_saved()
		
		self.assertEquals(m.changed_fields, ())
	
	def test_saved_has_changed(self):
		m = self.create_saved()
		
		self.assertEquals(m.has_changed, False)
	
	def test_saved_new_values(self):
		m = self.create_saved()
		
		self.assertEquals(m.new_values, self.new_values)
	
	def test_saved_old_values(self):
		m = self.create_saved()
		
		self.assertEquals(m.old_values, self.new_values)
	
	def test_changed_twice_new_values(self):
		m = self.create_changed()
		new_values = self.new_values
		m.text = 'newer'
		new_values['text'] = 'newer'
		
		self.assertEquals(m.new_values, new_values)
	
	def test_updated_together_values(self):
		m = self.create_saved()
		EnlightenedModel.objects.all().update(big_integer=0)
		
		new_values = self.new_values
		new_values['small_integer'] = 0
		
		m.small_integer = new_values['small_integer']
		m.save()
		m = EnlightenedModel.objects.all()[0]
		
		self.assertEquals(m.new_values, new_values)
	
	def test_updated_together_with_deferred_fields(self):
		m = self.create_saved()
		
		m = EnlightenedModel.objects.only('big_integer').get(pk=m.pk)
		
		self.assertEquals(m.new_values, self.new_values)
	
	"""
	Regression Tests
	
	"""
	
	def test_assign_fkey_after_init_before_save(self):
		"""
		If a required ForeignKey is assigned after the model is initialized
		but before it is saved, a field.rel.to.DoesNotExist exception should
		not be raised.
		
		"""
		
		del(self.old_values['enlightenment'])
		m = EnlightenedModel(**self.old_values)
		
		try:
			m.enlightenment = self.knowledge
		
		except Enlightenment.DoesNotExist:
			self.fail('Assigning a foreign key resulted in a DoesNotExist.')
	
	def tearDown(self):
		for file_name in os.listdir(self.uploads):
			if file_name.endswith('.png'):
				os.remove(os.path.join(os.path.join(self.uploads, file_name)))
		
		self.old_values.pop('id', None)
		self.new_values.pop('id', None)

########NEW FILE########
__FILENAME__ = wsgi
# -*- coding: utf-8 -*-

from __future__ import division, absolute_import, print_function, unicode_literals

import os


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testapp.settings')
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
