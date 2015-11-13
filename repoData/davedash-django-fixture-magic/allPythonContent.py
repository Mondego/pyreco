__FILENAME__ = base
# TODO: delete this file when I'm less lazy.
########NEW FILE########
__FILENAME__ = custom_dump
import sys
try:
    import json
except ImportError:
    from django.utils import simplejson as json

from django.core.management.base import BaseCommand
from django.db.models import loading
from django.core.serializers import serialize
from django.conf import settings
from django.template import Variable, VariableDoesNotExist

from fixture_magic.utils import (add_to_serialize_list, reorder_json,
        serialize_me, serialize_fully)

class Command(BaseCommand):
    help = 'Dump multiple pre-defined sets of objects into a JSON fixture.'
    args = "[dump_name pk [pk2 pk3 [..]]"

    def handle(self, dump_name, *pks, **options):
        # Get the primary object
        dump_settings = settings.CUSTOM_DUMPS[dump_name]
        (app_label, model_name) = dump_settings['primary'].split('.')
        dump_me = loading.get_model(app_label, model_name)
        objs = dump_me.objects.filter(pk__in=[int(i) for i in pks])
        for obj in objs:
            # get the dependent objects and add to serialize list
            for dep in dump_settings['dependents']:
                try:
                    thing = Variable("thing.%s" % dep).resolve({'thing': obj})
                    add_to_serialize_list([thing])
                except VariableDoesNotExist:
                    sys.stderr.write('%s not found' % dep)

            if not dump_settings['dependents']:
                add_to_serialize_list([obj])

        serialize_fully()
        data = serialize('json', [o for o in serialize_me if o is not None])

        data = reorder_json(json.loads(data), dump_settings.get('order', []),
                ordering_cond=dump_settings.get('order_cond',{}))

        print json.dumps(data, indent=4)

########NEW FILE########
__FILENAME__ = dump_object
from optparse import make_option

from django.core.exceptions import FieldError, ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers import serialize
from django.db.models import loading

from fixture_magic.utils import (add_to_serialize_list, serialize_me,
        serialize_fully)


class Command(BaseCommand):
    help = ('Dump specific objects from the database into JSON that you can '
            'use in a fixture')
    args = "<[--kitchensink | -k] object_class id1 [id2 [...]]>"

    option_list = BaseCommand.option_list + (
            make_option('--kitchensink', '-k',
                action='store_true', dest='kitchensink',
                default=False,
                help='Attempts to get related objects as well.'),
            )

    def handle(self, *args, **options):
        error_text = ('%s\nTry calling dump_object with --help argument or ' +
                      'use the following arguments:\n %s' %self.args)
        try:
            #verify input is valid
            (app_label, model_name) = args[0].split('.')
            ids = args[1:]
            assert(ids)
        except IndexError:
            raise CommandError(error_text %'No object_class or id arguments supplied.')
        except ValueError:
            raise CommandError(error_text %("object_class must be provided in"+
                    " the following format: app_name.model_name"))
        except AssertionError:
            raise CommandError(error_text %'No id arguments supplied.')

        dump_me = loading.get_model(app_label, model_name)
        try:
            if ids[0] == '*':
                objs = dump_me.objects.all()
            else:
                objs = dump_me.objects.filter(pk__in=[int(i) for i in ids])
        except ValueError:
            # We might have primary keys that are longs...
            try:
                objs = dump_me.objects.filter(pk__in=[long(i) for i in ids]) 
            except ValueError:
                # Finally, we might have primary keys that are strings...
                objs = dump_me.objects.filter(pk__in=ids)

        if options.get('kitchensink'):
            related_fields = [rel.get_accessor_name() for rel in
                          dump_me._meta.get_all_related_objects()]

            for obj in objs:
                for rel in related_fields:
                    try:
                        add_to_serialize_list(obj.__getattribute__(rel).all())
                    except FieldError:
                        pass
                    except ObjectDoesNotExist:
                        pass

        add_to_serialize_list(objs)
        serialize_fully()
        self.stdout.write(serialize('json', [o for o in serialize_me if o is not None],
                indent=4))

########NEW FILE########
__FILENAME__ = merge_fixtures
try:
    import json
except ImportError:
    from django.utils import simplejson as json

from django.core.management.base import BaseCommand

def write_json(output):
    try:
        # check our json import supports sorting keys
        json.dumps([1], sort_keys=True)
    except TypeError:
        print json.dumps(output, indent=4)
    else:
        print json.dumps(output, sort_keys=True, indent=4)

class Command(BaseCommand):
    help = ('Merge a series of fixtures and remove duplicates.')
    args = '[file ...]'

    def handle(self, *files, **options):
        """
        Load a bunch of json files.  Store the pk/model in a seen dictionary.
        Add all the unseen objects into output.
        """
        output = []
        seen = {}

        for f in files:
            f = file(f)
            data = json.loads(f.read())
            for object in data:
                key = '%s|%s' % (object['model'], object['pk'])
                if key not in seen:
                    seen[key] = 1
                    output.append(object)

        write_json(output)

########NEW FILE########
__FILENAME__ = reorder_fixtures
try:
    import json
except ImportError:
    from django.utils import simplejson as json

from django.core.management.base import BaseCommand

from fixture_magic.utils import reorder_json


class Command(BaseCommand):
    help = 'Reorder fixtures so some objects come before others.'
    args = '[fixture model ...]'

    def handle(self, fixture, *models, **options):
        output = reorder_json(json.loads(file(fixture).read()), models)

        print json.dumps(output, indent=4)

########NEW FILE########
__FILENAME__ = utils
from django.db import models

serialize_me = []
seen = {}


def reorder_json(data, models, ordering_cond={}):
    """Reorders JSON (actually a list of model dicts).

    This is useful if you need fixtures for one model to be loaded before
    another.

    :param data: the input JSON to sort
    :param models: the desired order for each model type
    :param ordering_cond: a key to sort within a model
    :return: the ordered JSON
    """
    output = []
    bucket = {}
    others = []

    for model in models:
        bucket[model] = []

    for object in data:
        if object['model'] in bucket.keys():
            bucket[object['model']].append(object)
        else:
            others.append(object)
    for model in models:
        if ordering_cond.has_key(model):
            bucket[model].sort(key=ordering_cond[model])
        output.extend(bucket[model])

    output.extend(others)
    return output


def get_fields(obj):
    try:
        return obj._meta.fields
    except AttributeError:
        return []


def serialize_fully():
    index = 0

    while index < len(serialize_me):
        for field in get_fields(serialize_me[index]):
            if isinstance(field, models.ForeignKey):
                add_to_serialize_list(
                    [serialize_me[index].__getattribute__(field.name)])

        index += 1

    serialize_me.reverse()


def add_to_serialize_list(objs):
    for obj in objs:
        if obj is None:
            continue
        if not hasattr(obj, '_meta'):
            add_to_serialize_list(obj)
            continue

        # Proxy models don't serialize well in Django.
        if obj._meta.proxy:
            obj = obj._meta.proxy_for_model.objects.get(pk=obj.pk)

        key = "%s:%s:%s" % (obj._meta.app_label, obj._meta.module_name,
                            obj.pk)
        if key not in seen:
            serialize_me.append(obj)
            seen[key] = 1

########NEW FILE########
__FILENAME__ = test_settings
SECRET_KEY = 'not empty'

########NEW FILE########
__FILENAME__ = test_utils
import os
import unittest

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'
from fixture_magic.utils import reorder_json, get_fields

__author__ = 'davedash'


class UtilsTestCase(unittest.TestCase):
    def test_reorder_json(self):
        """Test basic ordering of JSON/python object."""
        input_json = [{'model': 'f'}, {'model': 'x'},]
        expected = [{'model': 'x'}, {'model': 'f'}]
        self.assertEqual(expected, reorder_json(input_json, models=['x', 'f'])
        )

    def test_get_fields(self):
        obj = lambda: None
        obj._meta = lambda: None
        obj._meta.fields = ['foo']

        self.assertEqual(['foo'], get_fields(obj))


########NEW FILE########
