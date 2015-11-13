__FILENAME__ = mixins
import json, csv
from StringIO import StringIO
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse


class FiltersMixin(object):
	"""
	Enable simple filtering of querysets
	"""

	filters = []

	def get_queryset(self):
		"""
		Override get_queryset and apply filters.
		"""
		return super(FiltersMixin, self).get_queryset().filter(**self.get_filters())

	def get_filters(self):
		"""
		Provides a dictionary of filters to apply to the queryset.
		"""

		filters = {}

		for key, value in self.request.GET.items():
			if key not in self.filters:
				continue

			filters[key] = value

		return filters


class URIMixin(object):
	"""
	Enable display of URIs in responses
	"""

	model_resource_name = None
	uri_attribute_name = '_uri'


	def get_model_resource_name(self, relationship=None):
		"""
		Hook for returning the url name for the model.
		This is the parameter that you would pass into "reverse()".

		Defaults to "model_resource_name" of main model or related model.
		"""

		if relationship:
			return self.relationships[relationship].get('model_resource_name')

		return self.model_resource_name


	def get_resource_url_kwargs(self, model, relationship=None):
		"""
		Returns the kwargs for the call to "reverse()".
		Should be related to your pk or slug.
		"""

		return { 'pk': model.pk }


	def get_model_resource_url(self, model, relationship=None):
		"""
		Return a resource url for a given model
		"""

		resource_name = self.get_model_resource_name(relationship)

		if resource_name is None:
			raise ImproperlyConfigured('URIMixin requires either a definition of "model_resource_name" or an implementation of "get_model_resource_name()" or "get_model_resource_url()"')

		return reverse(resource_name, kwargs=self.get_resource_url_kwargs(model, relationship))


	def hydrate(self, *a, **k):
		"""
		Remove the URI parameter from incoming requests.
		"""

		data = super(URIMixin, self).hydrate(*a, **k)

		try:
			del data[self.uri_attribute_name]
		except:
			pass

		return data


	def dehydrate(self, model, fields=None, exclude=None, relationship_prefix=None):
		"""
		Insert the URI parameter into the data.
		"""

		data = super(URIMixin, self).dehydrate(model, fields, exclude, relationship_prefix)

		try:
			data[self.uri_attribute_name] = self.get_model_resource_url(model, relationship=relationship_prefix)
		except ImproperlyConfigured:
			#we only pass this exception up if this is the root model.
			if relationship_prefix is None:
				raise

		return data





class JSONMixin(object):
	""" Mixin for working with JSON encoded data """

	mimetype = 'application/json'

	def parse(self, data):
		return json.loads(data)

	def render(self, context):
		return json.dumps(context, indent=4)


class FlatFileMixin(object):
	def parse(self, data):
		input = StringIO(data)
		reader = csv.DictReader(input, delimiter=self.get_delimiter())

		data = list(reader)

		return data if len(data) > 1 else data[0]


	def render(self, context):
		output = StringIO()
		writer = csv.DictWriter(output, context.keys(), extrasaction='ignore', delimiter=self.get_delimiter())

		writer.writeheader()
		writer.writerows(context)

		return output.getvalue()


	def get_delimiter(self):
		return self.delimiter


class TSVMixin(FlatFileMixin):
	""" Mixin with your resource to IO in TSV """

	delimiter = '\t'
	mimetype = 'text/tab-separated-values'


class CSVMixin(FlatFileMixin):
	""" Mixin with your resource to IO in CSV """

	delimiter = ','
	mimetype = 'text/csv'

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = responses
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed


class SliverResponse(Exception):
	pass

class HttpResponseBadRequest(SliverResponse):
	response = HttpResponseBadRequest


class HttpResponseUnauthorized(SliverResponse):
	response = HttpResponseNotAllowed
########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
from django.views.generic import View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.list import MultipleObjectMixin

from django.db.models import ForeignKey, OneToOneField
from django.db.models.fields.related import RelatedField

import datetime

from types import NoneType
from decimal import Decimal

from django.http import HttpResponse

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

import responses

class Resource(View):
	"""
	Root resource object
	"""

	fields = None
	exclude = []
	relationships = {}

	@method_decorator(csrf_exempt)
	def dispatch(self, request, *args, **kwargs):
		"""
		Make sure the request meets any global requirements and is exempt from csrf.
		"""

		#if a response exception is raised, grab it and return it to django
		try:
			return super(Resource, self).dispatch(request, *args, **kwargs)
		except responses.SliverResponse, r:
			return r.response()

	def get_model_class(self):
		return self.model if hasattr(self, 'model') and self.model else self.get_queryset().model

	def hydrate(self):
		"""
		Prepares the incoming data for the database.
		"""

		data = self.parse(self.request.body)
		cleaned_data = {}

		model_class = self.get_model_class()

		for key, val in data.items():
			#make sure it's allowed
			if (self.fields and key not in self.fields) or key in self.exclude:
				continue

			#get the field with that name
			field = model_class._meta.get_field_by_name(key)[0]

			#hydrate it
			cleaned_data[key] = self.hydrate_value(field, val)

		return cleaned_data


	def hydrate_value(self, field, val):
		"""
		Prepares a single model attribute for the database.
		"""
		try:
			val = field.get_prep_value(val)
		except:
			raise responses.HttpResponseBadRequest

		#this is a foreign key, we need to manually hydrate it
		if val and isinstance(field, RelatedField):
			fk = {}
			fk[field.rel.field_name] = val

			val = field.rel.to.objects.get(**fk)

		return val


	def dehydrate_value(self, model, field):
		"""
		Prepares a single model attribute for the tubes.
		"""

		val = field.value_from_object(model)

		#if it's something from the datetime lib, convert to iso
		if isinstance(val, (datetime.datetime, datetime.date, datetime.time)):
			val = val.isoformat()

		#decimal fields
		elif isinstance(val, Decimal):
			val = float(val)

		#if it's something we don't know about, just convert to string
		elif not isinstance(val, (int, str, bool, NoneType)):
			val = unicode(val)		

		return val


	def dehydrate_relationship(self, model, relationship_name, relationship_prefix=None):
		"""
		Prepares a relationship for the tubes.
		"""

		full_relationship_name = '__'.join([relationship_prefix, relationship_name]) if relationship_prefix else relationship_name

		related_object = getattr(model, relationship_name)
		relationship_data = self.relationships[full_relationship_name]

		dehydrate_params = {
			'fields': relationship_data.get('fields'),
			'exclude': relationship_data.get('exclude'),
			'relationship_prefix': full_relationship_name,
		}

		#this is a to-many relationship
		if related_object.__class__.__name__ in ('RelatedManager', 'ManyRelatedManager'):
			return [self.dehydrate(related_model, **dehydrate_params) for related_model in related_object.all()]

		#this is a to-one relationship
		return self.dehydrate(related_object, **dehydrate_params)
		

	def dehydrate(self, model, fields=None, exclude=None, relationship_prefix=None):
		"""
		Prepares the full resource for the tubes.
		"""

		field_values = {}
		exclude = exclude or []

		#if the relationship is optional, this will show up as None sometimes, so we just return it.
		if model is None:
			return None

		#loop through the fields and scoop up the data
		for field in model._meta.fields:
			if fields and not field.name in fields:
				continue

			if field.name in exclude:
				continue

			full_relationship_name = '__'.join([relationship_prefix, field.name]) if relationship_prefix else field.name

			#if this is a relationship they want expanded on
			if isinstance(field, RelatedField) and full_relationship_name in self.relationships:
				field_values[field.name] = self.dehydrate_relationship(model, field.name, relationship_prefix=relationship_prefix)

			#normal field, get the value
			else:
				field_values[field.name] = self.dehydrate_value(model, field)

		#loop through reverse relationships
		for reverse_relationship in model._meta.get_all_related_objects():
			relationship_name = reverse_relationship.get_accessor_name()
			full_relationship_name = '__'.join([relationship_prefix, relationship_name]) if relationship_prefix else relationship_name

			if full_relationship_name in self.relationships:
				field_values[relationship_name] = self.dehydrate_relationship(model, relationship_name, relationship_prefix=relationship_prefix)

		#loop through m2m relationships
		for m2m_relationship in model._meta.many_to_many:
			relationship_name = m2m_relationship.name
			full_relationship_name = '__'.join([relationship_prefix, relationship_name]) if relationship_prefix else relationship_name

			if full_relationship_name in self.relationships:
				field_values[relationship_name] = self.dehydrate_relationship(model, relationship_name, relationship_prefix=relationship_prefix)			

		return field_values


	def render_to_response(self, context, status=200):
		"""
		Out to the tubes...
		"""
		return HttpResponse(self.render(context), mimetype=self.get_mimetype(), status=status)

	def get_mimetype(self):
		"""
		Determine the mimetype for the request
		"""
		if self.mimetype:
			return self.mimetype
		return 'text/html'




class ModelResource(SingleObjectMixin, Resource):
	"""
	Resource for a single model
	"""

	def get(self, request, *args, **kwargs):
		"""
		GET requests - fetch object
		"""

		self.object = self.get_object()
		return self.render_to_response(self.get_context_data())


	def put(self, request, *args, **kwargs):
		"""
		PUT requests - update object
		"""

		self.object = self.get_object()

		for key, val in self.hydrate().items():
			setattr(self.object, key, val)

		self.object.save()

		return self.render_to_response(self.get_context_data())


	def delete(self, request, *args, **kwargs):
		"""
		DELETE requests - delete object
		"""

		self.object = self.get_object()
		self.object.delete()
		return self.render_to_response({}, status=204)


	def get_context_data(self):
		"""
		Prepares data for response
		"""
		return self.dehydrate(self.object, self.fields, self.exclude)




class CollectionResource(MultipleObjectMixin, Resource):
	"""
	Resource for a collection of models
	"""

	def post(self, request, *args, **kwargs):
		"""
		POST requests - add object
		"""

		model_class = self.get_model_class()
		self.object = model_class.objects.create(**self.hydrate())

		return self.render_to_response(self.dehydrate(self.object), status=201)


	def get(self, request, *args, **kwargs):
		"""
		GET requests - fetch objects
		"""

		self.object_list = self.get_queryset()
		return self.render_to_response(self.get_context_data())


	def get_context_data(self):
		"""
		Loop through the models in the queryset and dehydrate them.
		"""
		return [self.dehydrate(model, self.fields, self.exclude) for model in self.object_list]

########NEW FILE########
