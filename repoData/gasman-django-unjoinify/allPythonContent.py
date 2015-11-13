__FILENAME__ = models
from django.db import models

class Festival(models.Model):
	name = models.CharField(max_length = 200)

class Award(models.Model):
	name = models.CharField(max_length = 200)
	festival = models.ForeignKey('Festival', related_name = 'awards')
	presenter = models.OneToOneField('Presenter', related_name = 'award', null = True)

# Okay, this is a slightly spurious use of OneToOneField, but how else are you going to work one in? :-)
class Presenter(models.Model):
	name = models.CharField(max_length = 200)

class Movie(models.Model):
	title = models.CharField(max_length = 200)
	producers = models.ManyToManyField('Person', related_name = 'movies_produced')

class Nomination(models.Model):
	movie = models.ForeignKey('Movie', related_name = 'nominations')
	award = models.ForeignKey('Award', related_name = 'nominations')
	ranking = models.IntegerField()

class Person(models.Model):
	first_name = models.CharField(max_length = 30)
	surname = models.CharField(max_length = 30)
	movies_acted_in = models.ManyToManyField('Movie', related_name = 'actors')

########NEW FILE########
__FILENAME__ = settings
import os
DIRNAME = os.path.dirname(__file__)

DEFAULT_CHARSET = 'utf-8'

test_engine = os.environ.get("UNJOINIFY_TEST_ENGINE", "sqlite3")

DATABASE_ENGINE = test_engine
DATABASE_NAME = os.environ.get("UNJOINIFY_DATABASE_NAME", "unjoinify_test")
DATABASE_USER = os.environ.get("UNJOINIFY_DATABASE_USER", "")
DATABASE_PASSWORD = os.environ.get("UNJOINIFY_DATABASE_PASSWORD", "")
DATABASE_HOST = os.environ.get("UNJOINIFY_DATABASE_HOST", "localhost")

if test_engine == "sqlite":
	DATABASE_NAME = os.path.join(DIRNAME, 'unjoinify_test.db')
	DATABASE_HOST = ""
elif test_engine == "mysql":
	DATABASE_PORT = os.environ.get("UNJOINIFY_DATABASE_PORT", 3306)
elif test_engine == "postgresql_psycopg2":
	DATABASE_PORT = os.environ.get("UNJOINIFY_DATABASE_PORT", 5432)


INSTALLED_APPS = (
	'unjoinify',
	'unjoinify.tests',
)

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase

from unjoinify.tests.models import Festival, Award, Presenter
from unjoinify import unjoinify

class TestUnjoinify(TestCase):
	fixtures = ['unjoinify_testdata.json']
	
	def test_unjoinify(self):
		awards = unjoinify(Award, """
			SELECT
				tests_award.id,
				tests_award.name,
				tests_nomination.id AS nominations__id,
				tests_nomination.ranking AS nominations__ranking,
				tests_movie.id AS nominations__movie__id,
				tests_movie.title AS nominations__movie__title,
				producer.id AS nominations__movie__producers__id,
				producer.first_name AS nominations__movie__producers__first_name,
				producer.surname AS nominations__movie__producers__surname,
				actor.id AS nominations__movie__actors__id,
				actor.first_name AS nominations__movie__actors__first_name,
				actor.surname AS nominations__movie__actors__surname,
				tests_presenter.id AS presenter__id,
				tests_presenter.name AS presenter__name
			FROM
				tests_award
				LEFT JOIN tests_nomination ON (tests_award.id = tests_nomination.award_id)
				LEFT JOIN tests_movie ON (tests_nomination.movie_id = tests_movie.id)
				LEFT JOIN tests_movie_producers ON (tests_movie.id = tests_movie_producers.movie_id)
				LEFT JOIN tests_person AS producer ON (tests_movie_producers.person_id = producer.id)
				LEFT JOIN tests_person_movies_acted_in ON (tests_person_movies_acted_in.movie_id = tests_movie.id)
				LEFT JOIN tests_person AS actor ON (tests_person_movies_acted_in.person_id = actor.id)
				LEFT JOIN tests_presenter ON (tests_award.presenter_id = tests_presenter.id)
			WHERE
				tests_award.festival_id = %s
			ORDER BY
				tests_award.name,
				tests_nomination.ranking,
				producer.surname,
				actor.surname
		""", (1,))
		
		(award, nominations, presenter) = awards[0]
		self.assertEquals("Best Director", award.name)
		self.assertEquals(3, len(nominations))
		self.assertEquals(None, presenter)
		
		(nomination, movie, producers, actors) = nominations[0]
		self.assertEquals(1, nomination.ranking)
		self.assertEquals("The King's Speech", movie.title)
		self.assertEquals(3, len(producers))
		self.assertEquals("Canning", producers[0].surname)
		self.assertEquals(2, len(actors))
		self.assertEquals("Firth", actors[0].surname)
		
		(award, nominations, presenter) = awards[1]
		self.assertEquals("Best Picture", award.name)
		self.assertEquals("Steven Spielberg", presenter.name)
	
	def test_reverse_one_to_one_relation(self):
		presenters = unjoinify(Presenter, """
			SELECT
				tests_presenter.id,
				tests_presenter.name,
				tests_award.id AS award__id,
				tests_award.name AS award__name
			FROM
				tests_presenter
				LEFT JOIN tests_award ON (tests_presenter.id = tests_award.presenter_id)
		""")
		
		(presenter, award) = presenters[0]
		self.assertEquals("Steven Spielberg", presenter.name)
		self.assertEquals("Best Picture", award.name)
	
	def test_overriding_column_names(self):
		festivals = unjoinify(Festival, """
			SELECT
				tests_festival.id AS arbitrary_name_1,
				tests_festival.name AS arbitrary_name_2,
				tests_award.id AS arbitrary_name_3,
				tests_award.name AS arbitrary_name_4
			FROM
				tests_festival
				LEFT JOIN tests_award ON (tests_festival.id = tests_award.festival_id)
			ORDER BY
				tests_festival.name,
				tests_award.name
		""", columns = ["id", "name", "awards__id", "awards__name"])
		
		(festival, awards) = festivals[0]
		self.assertEquals("83rd Academy Awards", festival.name)
		self.assertEquals("Best Director", awards[0].name)

########NEW FILE########
__FILENAME__ = unjoinify
from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.related import ForeignKey, ManyToManyField, OneToOneField
from django.db import connection
import itertools

# given a model class and a field name, determine whether the field is a regular field on the model,
# a relation with a single object on the other end, or a relation with multiple objects on the other end
def recognise_relation_type(model, field_name):
	try:
		field = model._meta.get_field(field_name)
		if isinstance(field, ForeignKey) or isinstance(field, OneToOneField): # OneToOneField is a subclass of ForeignKey anyway, but best not to rely on that
			return ('single', field.rel.to)
		elif isinstance(field, ManyToManyField):
			return ('multiple', field.rel.to)
		else:
			return ('field', None)
	except FieldDoesNotExist:
		# check reverse relations
		for rel in model._meta.get_all_related_objects():
			if rel.get_accessor_name() == field_name:
				if isinstance(rel.field, OneToOneField):
					return ('single', rel.model)
				else:
					return ('multiple', rel.model)
		for rel in model._meta.get_all_related_many_to_many_objects():
			if rel.get_accessor_name() == field_name:
				return ('multiple', rel.model)
		raise FieldDoesNotExist('%s has no field named %r' % (model._meta.object_name, field_name))

def make_unpack_plan(model, columns, prefix = '', plan = None):
	if plan == None:
		plan = []
	field_map = {
		'model': model,
		'fields': {}
	}
	plan.append(field_map)
	
	seen_field_names = set()
	for (column_index, column) in enumerate(columns):
		if column.startswith(prefix):
			suffix = column[len(prefix):]
			field_name = suffix.split('__')[0]
			if field_name in seen_field_names:
				continue
			seen_field_names.add(field_name)
			rel_type, related_model = recognise_relation_type(model, field_name)
			if rel_type == 'field':
				field_map['fields'][field_name] = column_index
			elif rel_type == 'single':
				make_unpack_plan(related_model, columns, prefix = prefix + field_name + '__', plan = plan)
			else: # rel_type == 'multiple'
				plan.append(
					make_unpack_plan(related_model, columns, prefix = prefix + field_name + '__', plan = [])
				)
	return plan

def unjoinify(model, query, query_params = (), columns = None):
	cursor = connection.cursor()
	cursor.execute(query, query_params)
	if not columns:
		columns = [column_description[0] for column_description in cursor.description] # don't trust this - 64 char limit :-(
	plan = make_unpack_plan(model, columns)
	return unpack_with_plan(plan, ResultIter(cursor))

# Wrapper for cursor objects to make compatible with the iterator interface
def ResultIter(cursor, arraysize=1000):
	while True:
		results = cursor.fetchmany(arraysize)
		if not results:
			break
		for result in results:
			yield result

# replace all elements of arr whose indexes are not in mask with None
def mask_columns(arr, mask):
	return [(val if i in mask else None) for i,val in enumerate(arr)]

def unpack_with_plan(plan, results):
	columns_for_grouper = set()
	child_count = 0
	for obj in plan:
		if isinstance(obj, dict):
			for col in obj['fields'].values():
				columns_for_grouper.add(col)
		else:
			child_count += 1
	
	output = []
	seen_primary_ids = set()
	for grouper, rows in itertools.groupby(results, lambda row: mask_columns(row, columns_for_grouper)):
		# check primary key of the first model in the plan;
		# if it's null, skip this row (it's an outer join with no match)
		# Also skip if it's one we've seen before (it's a repeat caused by a cartesian join)
		pk_name = plan[0]['model']._meta.pk.name
		pk_index = plan[0]['fields'][pk_name]
		pk_value = grouper[pk_index]
		if pk_value == None or pk_value in seen_primary_ids:
			continue
		
		seen_primary_ids.add(pk_value)
		
		output_row = []
		if child_count > 1:
			# will need to iterate over grouped_results multiple times, so convert rows into a list
			rows = list(rows)
		
		for obj in plan:
			if isinstance(obj, dict):
				fields = {}
				for field_name, index in obj['fields'].iteritems():
					fields[field_name] = grouper[index]
				# if primary key in fields is none, don't instantiate model
				if fields[obj['model']._meta.pk.name] == None:
					output_row.append(None)
				else:
					model = obj['model'](**fields)
					output_row.append(model)
			else:
				output_row.append(unpack_with_plan(obj, rows))
		
		if any(output_row): # skip if all nulls
			if len(plan) == 1:
				output.append(output_row[0])
			else:
				output.append(tuple(output_row))
	
	return output

########NEW FILE########
