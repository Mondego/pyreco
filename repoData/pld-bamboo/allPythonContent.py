__FILENAME__ = bambooapp
#!/usr/bin/env python

import sys
sys.stdout = sys.stderr
sys.path.append('/var/www/bamboo/current')
sys.path.append('/var/www/bamboo/current/bamboo')

import cherrypy

from bamboo.config.routes import connect_routes


# use routes dispatcher
dispatcher = cherrypy.dispatch.RoutesDispatcher()
routes_conf = {'/': {'request.dispatch': dispatcher}}
prod_conf = 'config/prod.conf'

# connect routes
connect_routes(dispatcher)

# global config
cherrypy.config.update(routes_conf)
cherrypy.config.update(prod_conf)
cherrypy.config.update({'environment': 'embedded'})

# app config
application = cherrypy.tree.mount(root=None, config=routes_conf)
application.merge(prod_conf)

########NEW FILE########
__FILENAME__ = celeryconfig
from bamboo.config import settings

BROKER_BACKEND = 'mongodb'
BROKER_URL = 'mongodb://localhost:27017/%s' % settings.DATABASE_NAME
CELERY_RESULT_BACKEND = 'mongodb'
CELERY_MONGODB_BACKEND_SETTINGS = {
    'host': 'localhost',
    'port': 27017,
    'database': settings.DATABASE_NAME,
    'taskmeta_collection': 'celery_tasks',
}
CELERY_IMPORTS = (
    'bamboo.core.merge',
    'bamboo.lib.readers',
    'bamboo.models.calculation',
    'bamboo.models.dataset',
)
CELERYD_CONCURRENCY = 1

########NEW FILE########
__FILENAME__ = celeryconfig_test
from bamboo.config import settings

BROKER_BACKEND = 'mongodb'
BROKER_URL = 'mongodb://localhost:27017/%s' % settings.TEST_DATABASE_NAME
CELERY_RESULT_BACKEND = 'mongodb'
CELERY_MONGODB_BACKEND_SETTINGS = {
    'host': 'localhost',
    'port': 27017,
    'database': settings.TEST_DATABASE_NAME,
    'taskmeta_collection': 'celery_tasks',
}
CELERY_IMPORTS = (
    'bamboo.core.merge',
    'bamboo.lib.readers',
    'bamboo.models.calculation',
    'bamboo.models.dataset',
)
CELERYD_CONCURRENCY = 1

########NEW FILE########
__FILENAME__ = db
from pymongo import MongoClient

from bamboo.config import settings


class Database(object):
    """Container for the MongoDB client."""

    # MongoDB client default host and port
    __client__ = MongoClient('localhost', 27017, w=1, j=False)
    __db__ = None

    @classmethod
    def create_db(cls, db_name):
        """Create a database `db_name`.

        :param cls: The class to set a client on.
        :param db_name: The name of the collection to create.
        """
        cls.__db__ = cls.__client__[db_name]

    @classmethod
    def client(cls):
        """Return the database client."""
        return cls.__client__

    @classmethod
    def db(cls, name=None):
        """Create the database if it has not been created.

        If name is provided, create a new database.

        :param cls: The class to set the database for.
        :param name: The name of the database to create, default None.
        :returns: The created database.
        """
        if not cls.__db__ or name:
            cls.create_db(name or settings.DATABASE_NAME)
        return cls.__db__

########NEW FILE########
__FILENAME__ = routes
from bamboo.controllers.calculations import Calculations
from bamboo.controllers.datasets import Datasets
from bamboo.controllers.root import Root
from bamboo.controllers.version import Version

# define routes as tuples:
# (name, method, route, controller, action)
ROUTES = [
    # root
    ['root', 'GET',
        '/', 'root', 'index'],
    # datasets
    ['datasets_aggregations', 'GET',
        '/datasets/:dataset_id/aggregations', 'datasets', 'aggregations'],
    ['datasets_create', 'POST', '/datasets', 'datasets', 'create'],
    ['datasets_delete', 'DELETE',
        '/datasets/:dataset_id', 'datasets', 'delete'],
    ['datasets_drop_columns', 'PUT',
        '/datasets/:dataset_id/drop_columns', 'datasets', 'drop_columns'],
    ['datasets_info', 'GET',
        '/datasets/:dataset_id/info', 'datasets', 'info'],
    ['datasets_merge', 'POST', '/datasets/merge', 'datasets', 'merge'],
    ['datasets_join', 'POST',
        '/datasets/:dataset_id/join', 'datasets', 'join'],
    ['datasets_join_alias', 'POST', '/datasets/join', 'datasets', 'join'],
    ['datasets_plot', 'GET',
        '/datasets/:dataset_id/plot', 'datasets', 'plot'],
    ['datasets_resample', 'GET',
        '/datasets/:dataset_id/resample', 'datasets', 'resample'],
    ['datasets_reset', 'PUT',
        '/datasets/:dataset_id/reset', 'datasets', 'reset'],
    ['datasets_rolling', 'GET',
        '/datasets/:dataset_id/rolling', 'datasets', 'rolling'],
    ['datasets_set_olap_type', 'PUT',
        '/datasets/:dataset_id/set_olap_type', 'datasets', 'set_olap_type'],
    ['datasets_show', 'GET',
        '/datasets/:dataset_id.:format', 'datasets', 'show'],
    ['datasets_show', 'GET', '/datasets/:dataset_id', 'datasets', 'show'],
    ['datasets_set_info', 'PUT',
        '/datasets/:dataset_id/info', 'datasets', 'set_info'],
    ['datasets_summary', 'GET',
        '/datasets/:dataset_id/summary', 'datasets', 'summary'],
    ['datasets_update', 'PUT',
        '/datasets/:dataset_id', 'datasets', 'update'],
    ['datasets_row_delete', 'DELETE', '/datasets/:dataset_id/row/:index',
        'datasets', 'row_delete'],
    ['datasets_row_show', 'GET', '/datasets/:dataset_id/row/:index',
        'datasets', 'row_show'],
    ['datasets_row_update', 'PUT', '/datasets/:dataset_id/row/:index',
        'datasets', 'row_update'],
    # calculations
    ['calculations_create', 'POST',
        '/calculations/:dataset_id', 'calculations', 'create'],
    ['calculations_create_alias', 'POST',
        '/datasets/:dataset_id/calculations', 'calculations', 'create'],
    ['calculations_delete', 'DELETE',
        '/datasets/:dataset_id/calculations', 'calculations', 'delete'],
    ['calculations_delete_alias', 'DELETE',
        '/datasets/:dataset_id/calculations/:name', 'calculations', 'delete'],
    ['calculations_show', 'GET',
        '/calculations/:dataset_id', 'calculations', 'show'],
    ['calculations_show_alias', 'GET',
        '/datasets/:dataset_id/calculations', 'calculations', 'show'],
    # version
    ['version', 'GET', '/version', 'version', 'index'],
]


def options():
    """Create option methods for all routes."""
    return [['%s_options' % name, 'OPTIONS', route, controller, 'options']
            for (name, _, route, controller, _) in ROUTES]


def connect_routes(dispatcher):
    """This function takes the dispatcher and attaches the routes.

    :param dispatcher: The CherryPy dispatcher.
    """
    # controller instances map
    controllers = {
        'root': Root(),
        'calculations': Calculations(),
        'datasets': Datasets(),
        'version': Version(),
    }

    # map them into args to dispatcher
    dictify = lambda x: dict(zip(
        ['name', 'conditions', 'route', 'controller', 'action'], x))
    route_case = {
        'conditions': lambda v: dict(method=v),
        'controller': lambda v: controllers[v],
    }
    kwarg_map = lambda d: {
        k: route_case.get(k, lambda v: v)(v) for k, v in d.iteritems()
    }

    routes = [kwarg_map(dictify(route)) for route in ROUTES + options()]

    # attach them
    for route in routes:
        dispatcher.connect(**route)

########NEW FILE########
__FILENAME__ = settings
import sys


# database config
ASYNC_FLAG = 'BAMBOO_ASYNC_OFF'
DATABASE_NAME = 'bamboo_dev'
TEST_DATABASE_NAME = DATABASE_NAME + '_test'


if len(sys.argv) > 1 and 'celeryconfig_test' in sys.argv[1]:
    DATABASE_NAME = TEST_DATABASE_NAME

RUN_PROFILER = False

########NEW FILE########
__FILENAME__ = abstract_controller
import cherrypy

from bamboo.lib.exceptions import ArgumentError
from bamboo.lib.jsontools import JSONError
from bamboo.lib.mongo import dump_mongo_json
from bamboo.models.dataset import Dataset


class AbstractController(object):
    """Abstract controller class for web facing controllers.

    Attributes:

    - ERROR: constant string for error messages.
    - SUCCESS: constant string for success messages.

    """

    exposed = True

    CSV = 'application/csv'
    JSON = 'application/json'

    ERROR = 'error'
    SUCCESS = 'success'

    DEFAULT_ERROR_MESSAGE = 'id not found'
    DEFAULT_SUCCESS_STATUS_CODE = 200
    ERROR_STATUS_CODE = 400
    NO_CONTENT_STATUS_CODE = 204

    def options(self, dataset_id=None, name=None):
        """Set Cross Origin Resource Sharing (CORS) headers.

        Set the CORS headers required for AJAX non-GET requests.

        :param dataset_id: Ignored argument so signature maps requests from
            clients.

        :returns: An empty string with the proper response headers for CORS.
        """
        self.__add_cors_headers()
        cherrypy.response.headers['Content-Length'] = 0
        cherrypy.response.status = self.NO_CONTENT_STATUS_CODE

        return ''

    def set_response_params(self, obj,
                            success_status_code=DEFAULT_SUCCESS_STATUS_CODE,
                            content_type=JSON):
        """Set response parameters.

        :param obj: The object to set the response for.
        :param content_type: The content type.
        :param success_status_code: The HTTP status code to return, default is
            DEFAULT_SUCCESS_STATUS_CODE.
        """
        cherrypy.response.headers['Content-Type'] = content_type
        cherrypy.response.status = success_status_code if obj is not None else\
            self.ERROR_STATUS_CODE

    def _dump_or_error(self, obj, error_message=DEFAULT_ERROR_MESSAGE,
                       callback=False):
        """Dump JSON or return error message, potentially with callback.

        If `obj` is None `error_message` is returned and the HTTP status code
        is set to 400. Otherwise the HTTP status code is set to
        `success_status_code`. If `callback` exists, the returned string is
        wrapped in the callback for JSONP.

        :param obj: Data to dump as JSON using BSON encoder.
        :param error_message: Error message to return is object is None.
        :param callback: Callback string to wrap obj in for JSONP.

        :returns: A JSON string wrapped with callback if callback is not False.
        """
        if obj is None:
            obj = {self.ERROR: error_message}

        result = obj if isinstance(obj, basestring) else dump_mongo_json(obj)
        self.__add_cors_headers()

        return '%s(%s)' % (str(callback), result) if callback else result

    def _safe_get_and_call(self, dataset_id, action, callback=None,
                           exceptions=(),
                           success_status_code=DEFAULT_SUCCESS_STATUS_CODE,
                           error=DEFAULT_ERROR_MESSAGE,
                           content_type=JSON):
        """Find dataset and call action with it and kwargs.

        Finds the dataset by `dataset_id` then calls function `action` and
        catches any passed in exceptions as well as a set of standard
        exceptions. Passes the result, error and callback to dump_or_error and
        returns the resulting string.

        :param dataset_id: The dataset ID to fetch.
        :param action: A function to call within a try block that takes a
            dataset any kwargs.
        :param callback: A JSONP callback that is passed through to
            dump_or_error.
        :param exceptions: A set of exceptions to additionally catch.
        :param success_status_code: The HTTP status code to return, default is
            DEFAULT_SUCCESS_STATUS_CODE.
        :param error: Default error string.
        :param kwargs: A set of keyword arguments that are passed to the
            action.

        :returns: A string that is the result of calling action or an error
            caught when calling action.
        """
        exceptions += (ArgumentError, JSONError, ValueError)

        dataset = Dataset.find_one(dataset_id) if dataset_id else None
        result = None

        try:
            if dataset is None or dataset.record:
                result = action(dataset)
        except exceptions as err:
            error = err.__str__()

        self.set_response_params(result, success_status_code, content_type)

        return self._dump_or_error(result, error, callback)

    def _success(self, msg, dataset_id):
        return {self.SUCCESS: msg, Dataset.ID: dataset_id}

    def __add_cors_headers(self):
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        cherrypy.response.headers['Access-Control-Allow-Methods'] =\
            'GET, POST, PUT, DELETE, OPTIONS'
        cherrypy.response.headers['Access-Control-Allow-Headers'] =\
            'Content-Type, Accept'

########NEW FILE########
__FILENAME__ = calculations
from bamboo.controllers.abstract_controller import AbstractController
from bamboo.core.parser import ParseError
from bamboo.lib.exceptions import ArgumentError
from bamboo.lib.jsontools import safe_json_loads
from bamboo.models.calculation import Calculation, UniqueCalculationError,\
    DependencyError
from bamboo.models.dataset import Dataset


class Calculations(AbstractController):
    """The Calculations Controller provides access to calculations.

    Calculations are formulas and names that (for now) must be linked to a
    specific dataset via that dataset's ID. All actions in the Calculations
    Controller can optionally take a `callback` parameter.  If passed the
    returned result will be wrapped this the parameter value.  E.g., if
    ``callback=parseResults`` the returned value will be
    ``parseResults([some-JSON])``, where ``some-JSON`` is the function return
    value.
    """

    def delete(self, dataset_id, name, group=None):
        """Delete the calculation with `name` from the dataset.

        Delete the calculation with column `name` from the dataset specified by
        the hash `dataset_id` from mongo. If it is an aggregate calculation a
        `group` must also be passed to determine the correct aggregate
        calculation to delete. This will also remove the column `name` from the
        dataframe for the dataset or the aggregate dataset.

        :param dataset_id: The dataset ID for which to delete the calculation.
        :param name: The name of the calculation to delete.
        :param group: The group of the calculation to delete, if an
            aggregation.

        :returns: JSON with success if delete or an error string if the
            calculation could not be found.
        """
        def action(dataset):
            calculation = Calculation.find_one(dataset.dataset_id, name, group)

            if calculation:
                calculation.delete(dataset)

                return self._success('deleted calculation: \'%s\'' % name,
                                     dataset_id)

        return self._safe_get_and_call(
            dataset_id, action, exceptions=(DependencyError,),
            error = 'name and dataset_id combination not found')

    def create(self, dataset_id, formula=None, name=None, json_file=None,
               group=None):
        """Add a calculation to a dataset with the given fomula, etc.

        Create a new calculation for `dataset_id` named `name` that calculates
        the `formula`.  Variables in formula can only refer to columns in the
        dataset.

        :param dataset_id: The dataset ID to add the calculation to.
        :param formula: The formula for the calculation which must match the
            parser language.
        :param name: The name to assign the new column for this formula.
        :param data: A dict or list of dicts mapping calculation names and
            formulas.
        :param group: A column to group by for aggregations, must be a
            dimension.

        :returns: A success string is the calculation is create. An error
            string if the dataset could not be found, the formula could not be
            parsed, or the group was invalid.
        """
        def action(dataset):
            if json_file:
                calculations = safe_json_loads(json_file.file.read())
                Calculation.create_from_list_or_dict(dataset, calculations)
                success_message = 'created calculations from JSON'
            elif formula is None or name is None:
                raise ArgumentError('Must provide both formula and name argume'
                                    'nts, or json_file argument')
            else:
                Calculation.create(dataset, formula, name, group)

            return self._success('created calculation: %s' % name, dataset_id)

        return self._safe_get_and_call(
            dataset_id, action,
            exceptions=(UniqueCalculationError, ParseError,),
            success_status_code=201)

    def show(self, dataset_id, callback=False):
        """Retrieve the calculations for `dataset_id`.

        :param dataset_id: The dataset to show calculations for.
        :param callback: A JSONP callback function string.

        :returns: A list of calculation records.  Each calculation record
            shows the calculations name, formula, group (if it exists), and
            state.
        """
        def action(dataset):
            result = Calculation.find(dataset)

            return [x.clean_record for x in result]

        return self._safe_get_and_call(dataset_id, action, callback=callback)

########NEW FILE########
__FILENAME__ = datasets
import urllib2

from external import bearcart
from pandas import concat
import vincent

from bamboo.controllers.abstract_controller import AbstractController
from bamboo.core.aggregations import AGGREGATIONS
from bamboo.core.frame import df_to_csv_string, NonUniqueJoinError
from bamboo.core.merge import merge_dataset_ids, MergeError
from bamboo.core.summary import ColumnTypeError
from bamboo.lib.exceptions import ArgumentError
from bamboo.lib.jsontools import df_to_jsondict, JSONError, safe_json_loads
from bamboo.lib.utils import parse_int
from bamboo.lib.query_args import QueryArgs
from bamboo.models.dataset import Dataset
from bamboo.models.observation import Observation


def valid_column(dataset, c):
    if c not in dataset.columns:
        raise ArgumentError("'%s' is not a column for this dataset." % c)


class Datasets(AbstractController):
    """
    The Datasets Controller provides access to data.  Datasets can store data
    from uploaded CSVs or URLs pointing to CSVs.  Additional rows can be passed
    as JSON and added to a dataset.

    All actions in the Datasets Controller can optionally take a `callback`
    parameter.  If passed the returned result will be wrapped this the
    parameter value.  E.g., is ``callback=parseResults`` the returned value
    will be ``parseResults([some-JSON])``, where ``some-JSON`` is the function
    return value.

    Attributes:

    - DEFAULT_AGGREGATION: The default aggregation for plotting with an index.
    - SELECT_ALL_FOR_SUMMARY: A string the the client can pass to
    - indicate that all columns should be summarized.

    """
    DEFAULT_AGGREGATION = 'sum'
    SELECT_ALL_FOR_SUMMARY = 'all'

    def delete(self, dataset_id, query=None):
        """Delete the dataset with hash `dataset_id`.

        This also deletes any observations associated with the dataset_id. The
        dataset and observations are not recoverable.

        :param dataset_id: The dataset ID of the dataset to be deleted.

        :returns: A string of success or error if that dataset could not be
            found.
        """
        def action(dataset, query=query):
            message = ' rows matching query: %s' % query if query else ''
            query = safe_json_loads(query)
            dataset.delete(query)

            return self._success('deleted dataset%s' % message, dataset_id)

        return self._safe_get_and_call(dataset_id, action)

    def info(self, dataset_id, callback=False):
        """Fetch and return the meta-data for a dataset.

        :param dataset_id: The dataset ID of the dataset to return meta-data
            for.
        :param callback: A JSONP callback function to wrap the result in.

        :returns: The data for `dataset_id`. Returns an error message if
            `dataset_id` does not exist.
        """
        def action(dataset):
            return dataset.info()

        return self._safe_get_and_call(dataset_id, action, callback=callback)

    def set_info(self, dataset_id, **kwargs):
        """Set the metadata for a dataset.

        :param dataset_id: ID of the dataset to update.
        :param attribution: Text to set the attribution to.
        :param description: Text to set the description to.
        :param label: Text to set the label to.
        :param license: Text to set the license to.

        :returns: Success or error.
        """
        def action(dataset):
            return dataset.info(kwargs)

        return self._safe_get_and_call(dataset_id, action)

    def summary(self, dataset_id, query={}, select=None, group=None, limit=0,
                order_by=None, callback=False, flat=False):
        """Return a summary of the dataset ID given the passed parameters.

        Retrieve the dataset by ID then limit that data using the optional
        `query`, `select` and `limit` parameters. Summarize the resulting data
        potentially grouping by the optional `group` parameter. Order the
        results using `order_by` if passed.

        :param dataset_id: The dataset ID of the dataset to summarize.
        :param select: This is a required argument, it can be 'all' or a
            MongoDB JSON query.
        :param group: If passed, group the summary by this column or list of
            columns.
        :param query: If passed restrict summary to rows matching this query.
        :param limit: If passed limit the rows to summarize to this number.
        :param order_by: If passed order the result using this column.
        :param flat: Return multigroups as a flat list.
        :param callback: A JSONP callback function to wrap the result in.

        :returns: An error message if `dataset_id` does not exist or the JSON
            for query or select is improperly formatted.  Otherwise the summary
            as a JSON string.

        :raises: `ArgumentError` if no select is supplied or dataset is not in
            ready state.
        """
        def action(dataset, query=query, select=select, limit=limit):
            if not dataset.is_ready:
                raise ArgumentError('dataset is not finished importing')

            limit = parse_int(limit, 0)
            query = self.__parse_query(query)
            select = self.__parse_select(select, required=True)

            groups = dataset.split_groups(group)
            [valid_column(dataset, c) for c in groups]

            # if select append groups to select
            if select:
                select.update(dict(zip(groups, [1] * len(groups))))

            query_args = QueryArgs(query=query, select=select, limit=limit,
                                   order_by=order_by)
            dframe = dataset.dframe(query_args)

            return dataset.summarize(dframe, groups=groups,
                                     no_cache=query or select, flat=flat)

        return self._safe_get_and_call(dataset_id, action, callback=callback,
                                       exceptions=(ColumnTypeError,))

    def aggregations(self, dataset_id, callback=False):
        """Return a dict of aggregated data for the given `dataset_id`.

        :param dataset_id: The dataset ID of the dataset to return aggregations
            for.
        :param callback: A JSONP callback function to wrap the result in.

        :returns: An error message if `dataset_id` does not exist. Otherwise,
            returns a dict of the form {[group]: [id]}.
        """
        def action(dataset):
            return dataset.aggregated_datasets_dict

        return self._safe_get_and_call(dataset_id, action, callback=callback)

    def show(self, dataset_id, query=None, select=None, distinct=None, limit=0,
             order_by=None, format=None, callback=False, count=False,
             index=False):
        """ Return rows for `dataset_id`, matching the passed parameters.

        Retrieve the dataset by ID then limit that data using the optional
        `query`, `select` and `limit` parameters. Order the results using
        `order_by` if passed.

        :param dataset_id: The dataset ID of the dataset to return.
        :param select: A MongoDB JSON query for select.
        :param distinct: A field to return distinct results for.
        :param query: If passed restrict results to rows matching this query.
        :param limit: If passed limit the rows to this number.
        :param order_by: If passed order the result using this column.
        :param format: Format of output data, 'json' or 'csv'
        :param callback: A JSONP callback function to wrap the result in.
        :param count: Return the count for this query.
        :param index: Include index with data.

        :returns: An error message if `dataset_id` does not exist or the JSON
            for query or select is improperly formatted. Otherwise a JSON
            string of the rows matching the parameters.
        """
        content_type = self.__content_type_for_format(format)

        def action(dataset, limit=limit, query=query, select=select):
            query_args = self.__parse_query_args(
                limit, order_by, query, select, distinct=distinct,
                dataset=dataset)

            if count:
                return dataset.count(query_args)
            else:
                dframe = dataset.dframe(query_args, index=index)

                if distinct:
                    return sorted(dframe[0].tolist())

            return self.__dataframe_as_content_type(content_type, dframe)

        return self._safe_get_and_call(
            dataset_id, action, callback=callback, content_type=content_type)

    def merge(self, dataset_ids, mapping=None):
        """Merge the datasets with the dataset_ids in `datasets`.

        :param dataset_ids: A JSON encoded array of dataset IDs for existing
            datasets.
        :param mapping: An optional mapping from original column names to
            destination names.

        :returns: An error if the datasets could not be found or less than two
            dataset IDs were passed.  Otherwise, the ID of the new merged
            dataset created by combining the datasets provided as an argument.
        """

        def action(dataset, dataset_ids=dataset_ids, mapping=mapping):
            mapping = safe_json_loads(mapping)

            dataset_ids = safe_json_loads(dataset_ids)
            dataset = merge_dataset_ids(dataset_ids, mapping)

            return {Dataset.ID: dataset.dataset_id}

        return self._safe_get_and_call(
            None, action, exceptions=(MergeError,), error = 'merge failed')

    def create(self, **kwargs):
        """Create a dataset by URL, CSV or schema file.

        If `url` is provided, create a dataset by downloading a CSV from that
        URL. If `url` is not provided and `csv_file` is provided, create a
        dataset with the data in the passed `csv_file`. If both `url` and
        `csv_file` are provided, `csv_file` is ignored. If `schema` is
        supplied, an empty dataset is created with the associated column
        structure.

        .. note::

            The follow words are reserved and will be slugified by adding
            underscores (or multiple underscores to ensure uniqueness) if used
            as column names:

                - all
                - and
                - case
                - date
                - default
                - in
                - not
                - or
                - sum
                - today

        :param url: A URL to load a CSV file from. The URL must point to a CSV
            file.
        :param csv_file: An uploaded CSV file to read from.
        :param json_file: An uploaded JSON file to read from.
        :param schema: A SDF schema file (JSON)
        :param na_values: A JSON list of values to interpret as missing data.
        :param perish: Number of seconds after which to delete the dataset.

        :returns: An error message if `url`, `csv_file`, or `scehma` are not
            provided. An error message if an improperly formatted value raises
            a ValueError, e.g. an improperly formatted CSV file. An error
            message if the URL could not be loaded. Otherwise returns a JSON
            string with the dataset ID of the newly created dataset.  Note that
            the dataset will not be fully loaded until its state is set to
            ready.
        """
        return self.__create_or_update(**kwargs)

    def reset(self, dataset_id, **kwargs):
        """Replace a dataset's data.

        Takes equivalent arguments and returns equivalent values as `create`.
        """
        return self.__create_or_update(dataset_id=dataset_id, **kwargs)

    def update(self, dataset_id, update, clear_pending=False):
        """Update the `dataset_id` with the new rows as JSON.

        :param dataset_id: The ID of the dataset to update.
        :param update: The JSON to update the dataset with.
        :param clear_pending: Remove any pending updates. Default False.

        :returns: A JSON dict with the ID of the dataset updated, or with an
            error message.
        """
        def action(dataset, update=update):
            if clear_pending:
                dataset.clear_pending_updates()
            update = safe_json_loads(update)
            dataset.add_observations(update)

            return {Dataset.ID: dataset_id}

        return self._safe_get_and_call(
            dataset_id, action, exceptions=(NonUniqueJoinError,))

    def drop_columns(self, dataset_id, columns):
        """Drop columns in dataset.

        Removes all the `columns` from the dataset with ID `dataset_id`.

        :param dataset_id: The ID of the dataset to update.
        :param columns: An array of columns within the dataset.

        :returns: An error if any column is not in the dataset. Otherwise a
            success message.
        """
        def action(dataset):
            deleted = dataset.delete_columns(columns)

            return self._success('dropped columns: %s' % deleted, dataset_id)

        return self._safe_get_and_call(dataset_id, action)

    def join(self, dataset_id, other_dataset_id, on=None):
        """Join the columns from two existing datasets.

        The `on` column must exists in both dataset. The values in the `on`
        `on` column of the other dataset must be unique.

        `on` can either be a single string to join on the same column in both
        datasets, or a comman separated list of the name for the left hand side
        and then the name for the right hand side. E.g.:

            * on=food_type,foodtype

        Will join on the left hand `food_type` column and the right hand
        `foodtype` column.


        :param dataset_id: The left hand dataset to be joined onto.
        :param other_dataset_id: The right hand to join.
        :param on: A column to join on, this column must be unique in the other
          dataset.

        :returns: Success and the new merged dataset ID or error message.
        """
        def action(dataset):
            other_dataset = Dataset.find_one(other_dataset_id)

            if other_dataset.record:
                merged_dataset = dataset.join(other_dataset, on)

                return self._success('joined dataset %s to %s on %s' % (
                    other_dataset_id, dataset_id, on),
                    merged_dataset.dataset_id)

        return self._safe_get_and_call(
            dataset_id, action, exceptions=(KeyError, NonUniqueJoinError))

    def resample(self, dataset_id, date_column, interval, how='mean',
                 query={}, format=None):
        """Resample a dataset.

        Resample a dataset based on the given interval and date column.

        :param dataset_id: The ID of the dataset to resample.
        :param date_column: This column determins the dates that are used in
            resampling.
        :param interval: The interval to use in resampling, any interval valid
            for the pandas resample function is accepted.
        :type interval: String
        :param how: The method of interpolation to use, any method valid for
            the pandas resampling function is accepted.
        :param query: A query to restrict the data which is resampled.
        :param format: The format of the returned DataFrame.

        :returns: A resampled DataFrame.
        """
        content_type = self.__content_type_for_format(format)

        def action(dataset, query=query):
            query = self.__parse_query(query)
            dframe = dataset.resample(date_column, interval, how, query=query)

            return self.__dataframe_as_content_type(content_type, dframe)

        return self._safe_get_and_call(dataset_id, action,
                                       exceptions=(TypeError,),
                                       content_type=content_type)

    def set_olap_type(self, dataset_id, column, olap_type):
        """Set the OLAP Type for this `column` of dataset.

        Only columns with an original OLAP Type of 'measure' can be modified.
        This includes columns with Simple Type integer, float, and datetime.

        :param dataset_id: The ID of the dataset to modify.
        :param column: The column to set the OLAP Type for.
        :param olap_type: The OLAP Type to set. Must be 'dimension' or
            'measure'.

        :returns: A success or error message.
        """

        def action(dataset):
            dataset.set_olap_type(column, olap_type)

            return self._success('set OLAP Type for column "%s" to "%s".' % (
                column, olap_type), dataset_id)

        return self._safe_get_and_call(dataset_id, action)

    def rolling(self, dataset_id, window, win_type='boxcar',
                format=None):
        """Calculate the rolling window over a dataset.

        Calculate a rolling aggregation over the dataset.

        :param dataset_id: The dataset to calculate a rolling aggregation for.
        :param window: The number of observations to include in each window of
            aggregation.
        :type window: Numeric
        :param win_type: The method of aggegating data in the window, default
            'boxcar'.  See pandas docs for details.
        :param format: The format of the returned DtaFrame.

        :returns: A DataFrame of aggregated rolling data.
        """
        content_type = self.__content_type_for_format(format)

        def action(dataset):
            dframe = dataset.rolling(str(win_type), int(window))
            return self.__dataframe_as_content_type(content_type, dframe)

        return self._safe_get_and_call(dataset_id, action,
                                       content_type=content_type)

    def row_delete(self, dataset_id, index):
        """Delete a row from dataset by index.

        :param dataset_id: The dataset to modify.
        :param index: The index to delete in the dataset.

        :returns: Success or error message.
        """
        def action(dataset):
            dataset.delete_observation(parse_int(index))

            return self._success('Deleted row with index "%s".' % index,
                                 dataset_id)

        return self._safe_get_and_call(dataset_id, action)

    def row_show(self, dataset_id, index):
        """Show a row by index.

        :param dataset_id: The dataset to fetch a row from.
        :param index: The index of the row to fetch.

        :returns: The requested row.
        """
        def action(dataset):
            row = Observation.find_one(dataset, parse_int(index))

            if row:
                return row.clean_record

        error_message = "No row exists at index %s" % index
        return self._safe_get_and_call(dataset_id, action, error=error_message)

    def row_update(self, dataset_id, index, data):
        """Update a row in dataset by index.

        Update the row in dataset identified by `index` by updating it with the
        JSON dict `data`.  If there is a column in the DataFrame for which
        there is not a corresponding key in `data` that column will not be
        modified.

        :param dataset_id: The dataset to modify.
        :param index: The index to update.
        :param data: A JSON dict to update the row with.

        :returns: Success or error message.
        """
        def action(dataset, data=data):
            data = safe_json_loads(data)
            dataset.update_observation(parse_int(index), data)

            return self._success('Updated row with index "%s".' % index,
                                 dataset_id)

        return self._safe_get_and_call(dataset_id, action,
                                       exceptions=(NonUniqueJoinError,))

    def plot(self, dataset_id, query=None, select=None, limit=0, group=None,
             order_by=None, index=None, plot_type='line', aggregation='sum',
             palette=None, vega=False, width=750, height=400):
        """Plot a dataset given restrictions.

        :param dataset_id: The dataset ID of the dataset to return.
        :param select: A MongoDB JSON query for select.
        :param distinct: A field to return distinct results for.
        :param query: If passed restrict results to rows matching this query.
        :param limit: If passed limit the rows to this number.
        :param group: Group by this column.
        :param order_by: If passed order the result using this column.
        :param index: If passed set this column as the index.
        :param plot_type: Option type of plot, may be: *area*, *bar*, *line*,
            *scatterplot*, or *stack*.  The default is *line*.
        :param aggregation: The type of aggregation to use.  The default is
            *sum*.
        :param palette: Color palette to use for the graph, accepts any of
            https://github.com/shutterstock/rickshaw#color-schemes, default
            spectrum14.
        :param vega: Output vega JSON.

        :returns: HTML with an embedded plot.
        """
        def action(dataset, select=select):
            query_args = self.__parse_query_args(limit, order_by, query,
                                                 select, dataset=dataset)

            numerics_select = dataset.schema.numerics_select
            query_select = query_args.select

            if query_select is None:
                query_select = numerics_select
            else:
                query_select = {k: v for k, v in query_select.items() if k in
                                numerics_select.keys()}

            if not query_select:
                raise ArgumentError(
                    'No numeric columns for dataset, or no select columns are '
                    'numeric. Select: %s.' % select)

            if index:
                query_select[index] = 1
                valid_column(dataset, index)

            if group:
                query_select[group] = 1
                valid_column(dataset, group)

            query_args.select = query_select

            dframe = dataset.dframe(query_args=query_args).dropna()
            axis = None

            if group or index:
                agg = self.__parse_aggregation(aggregation)

            if index:
                if group:
                    groupby = dframe.groupby(group)
                    dframes = []

                    for g in groupby.groups.keys():
                        renamed = {c: '%s %s' % (c, g) for c in dframe.columns}
                        data = groupby.get_group(g).groupby(index).agg(agg)
                        dframes.append(data.rename(columns=renamed))

                    dframe = concat(dframes).fillna(0).reset_index().groupby(
                        index).agg(agg).sort_index()
                else:
                    dframe = dframe.groupby(index).agg(agg)
            elif group:
                dframe = dframe.groupby(group).agg(agg).reset_index()
                axis = dframe[group].tolist()
                dframe = dframe.drop(group, axis=1)

            if vega:
                dframe.index = axis or dframe.index.map(float)
                vis = vincent.Bar()
                vis.tabular_data(dframe, columns=dframe.columns.tolist()[0:1])

                return vis.vega
            else:
                vis = bearcart.Chart(dframe, plt_type=plot_type, width=width,
                                     height=height, palette=palette,
                                     x_axis=axis or True,
                                     x_time=index is not None)

            return vis.build_html()

        return self._safe_get_and_call(
            dataset_id, action, content_type='text/html')

    def __create_or_update(self, url=None, csv_file=None, json_file=None,
                           schema=None, na_values=[], perish=0,
                           dataset_id=None):
        result = None
        error = 'url, csv_file or schema required'

        try:
            if schema or url or csv_file or json_file:
                if dataset_id is None:
                    dataset = Dataset()
                    dataset.save()
                else:
                    dataset = Dataset.find_one(dataset_id)
                    Observation.delete_all(dataset)

                if schema:
                    dataset.import_schema(schema)

                na_values = safe_json_loads(na_values)

                if url:
                    dataset.import_from_url(url, na_values=na_values)
                elif csv_file:
                    dataset.import_from_csv(csv_file, na_values=na_values)
                elif json_file:
                    dataset.import_from_json(json_file)

                result = {Dataset.ID: dataset.dataset_id}

            perish = parse_int(perish)
            perish and dataset.delete(countdown=perish)
        except urllib2.URLError:
            error = 'could not load: %s' % url
        except IOError:
            error = 'could not get a filehandle for: %s' % csv_file
        except JSONError as e:
            error = e.__str__()

        self.set_response_params(result, success_status_code=201)

        return self._dump_or_error(result, error)

    def __content_type_for_format(self, format):
        return self.CSV if format == 'csv' else self.JSON

    def __dataframe_as_content_type(self, content_type, dframe):
        if content_type == self.CSV:
            return df_to_csv_string(dframe)
        else:
            return df_to_jsondict(dframe)

    def __parse_select(self, select, required=False):
        if required and select is None:
            raise ArgumentError('no select')

        if select == self.SELECT_ALL_FOR_SUMMARY:
            select = None
        elif select is not None:
            select = safe_json_loads(select, error_title='select')

            if not isinstance(select, dict):
                msg = 'select argument must be a JSON dictionary, found: %s.'
                raise ArgumentError(msg % select)

        return select

    def __parse_query(self, query):
        return safe_json_loads(query) or {}

    def __parse_aggregation(self, agg):
        return agg if agg in AGGREGATIONS else self.DEFAULT_AGGREGATION

    def __parse_query_args(self, limit, order_by, query, select,
                           distinct=None, dataset=None):
            limit = parse_int(limit, 0)
            query = self.__parse_query(query)
            select = self.__parse_select(select)

            return QueryArgs(query=query, select=select, distinct=distinct,
                             limit=limit, order_by=order_by, dataset=dataset)

########NEW FILE########
__FILENAME__ = root
import cherrypy

from bamboo.lib.mail import send_mail


ERROR_RESPONSE_BODY = """
    <html><body><p>Sorry, an error occured. We are working to resolve it.
    </p><p>For more help please email the <a
    href= 'https://groups.google.com/forum/#!forum/bamboo-dev'>bamboo-dev
    list</a></p></body></html>"""


def handle_error():
    cherrypy.response.status = 500
    cherrypy.response.body = [ERROR_RESPONSE_BODY]
    send_mail('smtp.googlemail.com', 'bamboo.errors', 'test-password',
              'bamboo-errors@googlegroups.com',
              'bamboo.errors@gmail.com',
              '[ERROR] 500 Error in Bamboo',
              cherrypy._cperror.format_exc())


class Root(object):
    _cp_config = {'request.error_response': handle_error}

    def index(self):
        """Redirect to documentation index."""
        raise cherrypy.HTTPRedirect('/docs/index.html')

########NEW FILE########
__FILENAME__ = version
from bamboo.controllers.abstract_controller import AbstractController
from bamboo.lib.version import get_version


class Version(AbstractController):

    def index(self):
        """Return JSON of version and version description"""
        return self._dump_or_error(get_version())

########NEW FILE########
__FILENAME__ = aggregations
from math import isnan

from pandas import concat, DataFrame, Series
from scipy.stats.stats import pearsonr

from bamboo.lib.utils import minint, parse_float


class Aggregation(object):
    """Abstract class for all aggregations.

    :param column: Column to aggregate.
    :param columns: List of columns to aggregate.
    :param formula_name: The string to refer to this aggregation.
    """
    column = None
    columns = None
    formula_name = None

    def __init__(self, name, groups, dframe):
        self.name = name
        self.groups = groups
        self.dframe = dframe

    def eval(self, columns):
        self.columns = columns
        self.column = columns[0] if len(columns) else None
        return self.group() if self.groups else self.agg()

    def group(self):
        """For when aggregation is called with a group parameter."""
        return self._groupby().agg(self.formula_name)

    def agg(self):
        """For when aggregation is called without a group parameter."""
        result = float(self.column.__getattribute__(self.formula_name)())
        return self._value_to_dframe(result)

    def _value_to_dframe(self, value):
        return DataFrame({self.name: Series([value])})

    def _groupby(self):
        return self.dframe[self.groups].join(concat(
            self.columns, axis=1)).groupby(self.groups, as_index=False)


class CountAggregation(Aggregation):
    """Calculate the count of rows fulfilling the criteria in the formula.

    N/A values are ignored unless there are no arguments to the function, in
    which case it returns the number of rows in the dataset.

    Written as ``count(CRITERIA)``. Where `CRITERIA` is an optional boolean
    expression that signifies which rows are to be counted.
    """
    formula_name = 'count'

    def group(self):
        if self.column is not None:
            joined = self.dframe[self.groups].join(
                self.column)
            joined = joined[self.column]
            groupby = joined.groupby(self.groups, as_index=False)
            result = groupby.agg(
                self.formula_name)[self.column.name].reset_index()
        else:
            result = self.dframe[self.groups]
            result = result.groupby(self.groups).apply(lambda x: len(x)).\
                reset_index().rename(columns={0: self.name})

        return result

    def agg(self):
        if self.column is not None:
            self.column = self.column[self.column]
            result = float(self.column.__getattribute__(self.formula_name)())
        else:
            result = len(self.dframe)

        return self._value_to_dframe(result)


class RatioAggregation(Aggregation):
    """Calculate the ratio.

    Columns with N/A for either the numerator or denominator are ignored.  This
    will store associated numerator and denominator columns.  Written as
    ``ratio(NUMERATOR, DENOMINATOR)``. Where `NUMERATOR` and `DENOMINATOR` are
    both valid formulas.
    """
    formula_name = 'ratio'

    def group(self):
        return self._group(self.columns)

    def _group(self, columns):
        dframe = self.dframe[self.groups]
        dframe = self._build_dframe(dframe, columns)
        groupby = dframe.groupby(self.groups, as_index=False)
        return self._add_calculated_column(groupby.sum())

    def agg(self):
        dframe = DataFrame(index=self.column.index)

        dframe = self._build_dframe(dframe, self.columns)
        column_names = [self.__name_for_idx(i) for i in xrange(0, 2)]
        dframe = dframe.dropna(subset=column_names)

        dframe = DataFrame([dframe.sum().to_dict()])

        return self._add_calculated_column(dframe)

    def reduce(self, dframe, columns):
        """Reduce the columns and store in `dframe`.

        :param dframe: The DataFrame to reduce.
        :param columns: Columns in the DataFrame to reduce on.
        """
        self.columns = columns
        self.column = columns[0]
        new_dframe = self.agg()

        for column in new_dframe.columns:
            dframe[column] += new_dframe[column]

        dframe[self.name] = self.__agg_dframe(dframe)

        return dframe

    def __name_for_idx(self, idx):
        return '%s_%s' % (self.name, {
            0: 'numerator',
            1: 'denominator',
        }[idx])

    def _build_dframe(self, dframe, columns):
        for idx, column in enumerate(columns):
            column.name = self.__name_for_idx(idx)

        return concat([dframe] + [DataFrame(col) for col in columns], axis=1)

    def _add_calculated_column(self, dframe):
        column = dframe[self.__name_for_idx(0)].apply(float) /\
            dframe[self.__name_for_idx(1)]
        column.name = self.name

        return dframe.join(column)

    def __agg_dframe(self, dframe):
        return dframe[self.__name_for_idx(0)].apply(float) /\
            dframe[self.__name_for_idx(1)]


class ArgMaxAggregation(Aggregation):
    """Return the index for the maximum of a column.

    Written as ``argmax(FORMULA)``. Where `FORMULA` is a valid formula.
    """
    formula_name = 'argmax'

    def group(self):
        """For when aggregation is called with a group parameter."""
        self.column = self.column.apply(lambda value: parse_float(value))
        group_dframe = self.dframe[self.groups].join(self.column)
        indices = group_dframe.reset_index().set_index(
            self.groups + [self.name])

        def max_index_for_row(row):
            groups = row[self.groups]
            value = row[self.name]

            xsection = indices.xs(groups, level=self.groups)

            if isnan(value):
                return minint()

            max_index = xsection.get_value(value, 'index')

            if isinstance(max_index, Series):
                max_index = max_index.max()

            return max_index

        groupby_max = self._groupby().max().reset_index()
        column = groupby_max.apply(max_index_for_row, axis=1).apply(int)
        column.name = self.name

        return DataFrame(column).join(groupby_max[self.groups])


class MaxAggregation(Aggregation):
    """Calculate the maximum.

    Written as ``max(FORMULA)``. Where `FORMULA` is a valid formula.
    """
    formula_name = 'max'


class MeanAggregation(RatioAggregation, Aggregation):
    """Calculate the arithmetic mean.

    Written as ``mean(FORMULA)``. Where `FORMULA` is a valid formula.

    Because mean is a ratio this inherits from `RatioAggregation` to
    use its generic reduce implementation.
    """
    formula_name = 'mean'

    def group(self):
        return self._group([self.column, Series([1] * len(self.column))])

    def agg(self):
        dframe = DataFrame(index=[0])

        columns = [
            Series([col]) for col in [self.column.sum(), len(self.column)]]

        dframe = self._build_dframe(dframe, columns)
        dframe = DataFrame([dframe.sum().to_dict()])

        return self._add_calculated_column(dframe)


class MedianAggregation(Aggregation):
    """Calculate the median. Written as ``median(FORMULA)``.

    Where `FORMULA` is a valid formula.
    """
    formula_name = 'median'


class MinAggregation(Aggregation):
    """Calculate the minimum.

    Written as ``min(FORMULA)``. Where `FORMULA` is a valid formula.
    """
    formula_name = 'min'


class NewestAggregation(Aggregation):
    """Return the second column's value at the newest row in the first column.

    Find the maximum value for the first column and return the entry at that
    row from the second column.

    Written as ``newest(INDEX_FORMULA, VALUE_FORMULA)`` where ``INDEX_FORMULA``
    and ``VALUE_FORMULA`` are valid formulae.
    """
    formula_name = 'newest'
    value_column = 1

    def agg(self):
        index, values = self.columns
        index.name = 'index'
        values.name = self.name

        idframe = DataFrame(values).join(index).dropna().reset_index()
        idx = idframe['index'].argmax()
        result = idframe[self.name].get_value(idx)

        return self._value_to_dframe(result)

    def group(self):
        argmax_agg = ArgMaxAggregation(self.name, self.groups, self.dframe)
        argmax_df = argmax_agg.eval(self.columns)
        indices = argmax_df.pop(self.name)

        newest_col = self.columns[self.value_column][indices]
        newest_col.index = argmax_df.index
        newest_col.name = self.name

        return argmax_df.join(newest_col)


class PearsonAggregation(Aggregation):
    """Calculate the Pearson correlation and associatd p-value.

    Calculate the Pearson correlation coefficient between two columns and the
    p-value for that correlation coefficient.

    Written as ``pearson(FORMULA1, FORMULA2)``. Where ``FORMULA1`` and
    ``FORMULA2`` are valid formulae.
    """
    formula_name = 'pearson'

    def agg(self):
        coor, pvalue = self.__pearsonr(self.columns)
        pvalue_column = Series([pvalue], name=self.__pvalue_name)
        return self._value_to_dframe(coor).join(pvalue_column)

    def group(self):
        def pearson(dframe):
            columns = [dframe[name] for name in dframe.columns[-2:]]

            return DataFrame([self.__pearsonr(columns)],
                             columns=[self.name, self.__pvalue_name])

        groupby = self._groupby()
        dframe = groupby.apply(pearson).reset_index()

        # remove extra index column
        del dframe[dframe.columns[len(self.groups)]]
        return dframe

    def __pearsonr(self, columns):
        columns = [c.dropna() for c in columns]
        shared_index = reduce(
            lambda x, y: x.index.intersection(y.index), columns)
        columns = [c.ix[shared_index] for c in columns]

        return pearsonr(*columns)

    @property
    def __pvalue_name(self):
        return '%s_pvalue' % self.name


class StandardDeviationAggregation(Aggregation):
    """Calculate the standard deviation. Written as ``std(FORMULA)``.

    Where `FORMULA` is a valid formula.
    """
    formula_name = 'std'


class SumAggregation(Aggregation):
    """Calculate the sum.

    Written as ``sum(FORMULA)``. Where `FORMULA` is a valid formula.
    """
    formula_name = 'sum'

    def reduce(self, dframe, columns):
        self.columns = columns
        self.column = columns[0]
        dframe = dframe.reset_index()
        dframe[self.name] += self.agg()[self.name]

        return dframe


class VarianceAggregation(Aggregation):
    """Calculate the variance. Written as ``var(FORMULA)``.

    Where `FORMULA` is a valid formula.
    """
    formula_name = 'var'


# dict of formula names to aggregation classes
AGGREGATIONS = {
    cls.formula_name: cls for cls in
    Aggregation.__subclasses__()
    if cls.formula_name
}

########NEW FILE########
__FILENAME__ = aggregator
from pandas import concat

from bamboo.core.aggregations import AGGREGATIONS
from bamboo.core.frame import add_parent_column, rows_for_parent_id
from bamboo.lib.parsing import parse_columns


def group_join(groups, left, other):
    if groups:
        other.set_index(groups, inplace=True)

    return left.join(other, on=groups if len(groups) else None)


def aggregated_dataset(dataset, dframe, groups):
    """Create an aggregated dataset for this dataset.

    Creates and saves a dataset from the given `dframe`.  Then stores this
    dataset as an aggregated dataset given `groups` for `self`.

    :param dframe: The DataFrame to store in the new aggregated dataset.
    :param groups: The groups associated with this aggregated dataset.
    :returns: The newly created aggregated dataset.
    """
    a_dataset = dataset.create()
    a_dataset.save_observations(dframe)

    # store a link to the new dataset
    group_str = dataset.join_groups(groups)
    a_datasets_dict = dataset.aggregated_datasets_dict
    a_datasets_dict[group_str] = a_dataset.dataset_id
    dataset.update({dataset.AGGREGATED_DATASETS: a_datasets_dict})

    return a_dataset


class Aggregator(object):
    """Perform a aggregations on datasets.

    Apply the `aggregation` to group columns by `groups` and the `columns`
    of the `dframe`. Store the resulting `dframe` as a linked dataset for
    `dataset`. If a linked dataset with the same groups already exists update
    this dataset.  Otherwise create a new linked dataset.
    """

    def __init__(self, dframe, groups, _type, name, columns):
        """Create an Aggregator.

        :param columns: The columns to aggregate over.
        :param dframe: The DataFrame to aggregate.
        :param groups: A list of columns to group on.
        :param _type: The aggregation to perform.
        :param name: The name of the aggregation.
        """
        self.columns = columns
        self.dframe = dframe
        self.groups = groups
        self.name = name
        aggregation = AGGREGATIONS.get(_type)
        self.aggregation = aggregation(self.name, self.groups, self.dframe)

    def save(self, dataset):
        """Save this aggregation.

        If an aggregated dataset for this aggregations group already exists
        store in this dataset, if not create a new aggregated dataset and store
        the aggregation in this new aggregated dataset.

        """
        new_dframe = self.aggregation.eval(self.columns)
        new_dframe = add_parent_column(new_dframe, dataset.dataset_id)

        a_dataset = dataset.aggregated_dataset(self.groups)

        if a_dataset is None:
            a_dataset = aggregated_dataset(dataset, new_dframe, self.groups)
        else:
            a_dframe = a_dataset.dframe()
            new_dframe = group_join(self.groups, a_dframe, new_dframe)
            a_dataset.replace_observations(new_dframe)

        self.new_dframe = new_dframe

    def update(self, dataset, child_dataset, formula, reducible):
        """Attempt to reduce an update and store."""
        parent_dataset_id = dataset.dataset_id

        # get dframe only including rows from this parent
        dframe = rows_for_parent_id(child_dataset.dframe(
            keep_parent_ids=True, reload_=True), parent_dataset_id)

        # remove rows in child from parent
        child_dataset.remove_parent_observations(parent_dataset_id)

        if reducible and self.__is_reducible():
            dframe = self.aggregation.reduce(dframe, self.columns)
        else:
            dframe = self.updated_dframe(dataset, formula, dframe)

        new_a_dframe = concat([child_dataset.dframe(), dframe])
        new_a_dframe = add_parent_column(new_a_dframe, parent_dataset_id)
        child_dataset.replace_observations(new_a_dframe)

        return child_dataset.dframe()

    def updated_dframe(self, dataset, formula, dframe):
        """Create a new aggregation and update return updated dframe."""
        # build column arguments from original dframe
        columns = parse_columns(dataset, formula, self.name, self.dframe)
        new_dframe = self.aggregation.eval(columns)

        new_columns = [x for x in new_dframe.columns if x not in self.groups]

        dframe = dframe.drop(new_columns, axis=1)
        dframe = group_join(self.groups, new_dframe, dframe)

        return dframe

    def __is_reducible(self):
        """If it is not grouped and a reduce is defined."""
        return not self.groups and 'reduce' in dir(self.aggregation)

########NEW FILE########
__FILENAME__ = calculator
from collections import defaultdict

from celery.task import task
from pandas import concat, DataFrame

from bamboo.core.aggregator import Aggregator
from bamboo.core.frame import add_parent_column, join_dataset
from bamboo.core.parser import Parser
from bamboo.lib.datetools import recognize_dates
from bamboo.lib.jsontools import df_to_jsondict
from bamboo.lib.mongo import MONGO_ID
from bamboo.lib.parsing import parse_columns
from bamboo.lib.query_args import QueryArgs
from bamboo.lib.utils import combine_dicts, flatten, to_list


def calculate_columns(dataset, calculations):
    """Calculate and store new columns for `calculations`.

    The new columns are join t othe Calculation dframe and replace the
    dataset's observations.

    .. note::

        This can result in race-conditions when:

        - deleting ``controllers.Datasets.DELETE``
        - updating ``controllers.Datasets.POST([dataset_id])``

        Therefore, perform these actions asychronously.

    :param dataset: The dataset to calculate for.
    :param calculations: A list of calculations.
    """
    new_cols = None

    for c in calculations:
        if c.aggregation:
            aggregator = __create_aggregator(
                dataset, c.formula, c.name, c.groups_as_list)
            aggregator.save(dataset)
        else:
            columns = parse_columns(dataset, c.formula, c.name)
            if new_cols is None:
                new_cols = DataFrame(columns[0])
            else:
                new_cols = new_cols.join(columns[0])

    if new_cols is not None:
        dataset.update_observations(new_cols)

    # propagate calculation to any merged child datasets
    [__propagate_column(x, dataset) for x in dataset.merged_datasets]


@task(default_retry_delay=5, ignore_result=True)
def calculate_updates(dataset, new_data, new_dframe_raw=None,
                      parent_dataset_id=None, update_id=None):
    """Update dataset with `new_data`.

    This can result in race-conditions when:

    - deleting ``controllers.Datasets.DELETE``
    - updating ``controllers.Datasets.POST([dataset_id])``

    Therefore, perform these actions asychronously.

    :param new_data: Data to update this dataset with.
    :param new_dframe_raw: DataFrame to update this dataset with.
    :param parent_dataset_id: If passed add ID as parent ID to column,
        default is None.
    """
    if not __update_is_valid(dataset, new_dframe_raw):
        dataset.remove_pending_update(update_id)
        return

    __ensure_ready(dataset, update_id)

    if new_dframe_raw is None:
        new_dframe_raw = dframe_from_update(dataset, new_data)

    new_dframe = recognize_dates(new_dframe_raw, dataset.schema)

    new_dframe = __add_calculations(dataset, new_dframe)

    # set parent id if provided
    if parent_dataset_id:
        new_dframe = add_parent_column(new_dframe, parent_dataset_id)

    dataset.append_observations(new_dframe)
    dataset.clear_summary_stats()

    propagate(dataset, new_dframe=new_dframe, update={'add': new_dframe_raw})

    dataset.update_complete(update_id)


def dframe_from_update(dataset, new_data):
    """Make a DataFrame for the `new_data`.

    :param new_data: Data to add to dframe.
    :type new_data: List.
    """
    filtered_data = []
    columns = dataset.columns
    labels_to_slugs = dataset.schema.labels_to_slugs
    num_columns = len(columns)
    num_rows = dataset.num_rows
    dframe_empty = not num_columns

    if dframe_empty:
        columns = dataset.schema.keys()

    for row in new_data:
        filtered_row = dict()
        for col, val in row.iteritems():
            # special case for reserved keys (e.g. _id)
            if col == MONGO_ID:
                if (not num_columns or col in columns) and\
                        col not in filtered_row.keys():
                    filtered_row[col] = val
            else:
                # if col is a label take slug, if it's a slug take col
                slug = labels_to_slugs.get(
                    col, col if col in labels_to_slugs.values() else None)

                # if slug is valid or there is an empty dframe
                if (slug or col in labels_to_slugs.keys()) and (
                        dframe_empty or slug in columns):
                    filtered_row[slug] = dataset.schema.convert_type(
                        slug, val)

        filtered_data.append(filtered_row)

    index = range(num_rows, num_rows + len(filtered_data))
    new_dframe = DataFrame(filtered_data, index=index)

    return new_dframe


@task(default_retry_delay=5, ignore_result=True)
def propagate(dataset, new_dframe=None, update=None):
    """Propagate changes in a modified dataset."""
    __update_aggregate_datasets(dataset, new_dframe, update=update)

    if update:
        __update_merged_datasets(dataset, update)
        __update_joined_datasets(dataset, update)


def __add_calculations(dataset, new_dframe):
    labels_to_slugs = dataset.schema.labels_to_slugs

    for calculation in dataset.calculations(include_aggs=False):
        function = Parser.parse_function(calculation.formula)
        new_column = new_dframe.apply(function, axis=1, args=(dataset, ))
        potential_name = calculation.name

        if potential_name not in dataset.dframe().columns:
            if potential_name in labels_to_slugs:
                new_column.name = labels_to_slugs[potential_name]
        else:
            new_column.name = potential_name

        new_dframe = new_dframe.join(new_column)

    return new_dframe


def __calculation_data(dataset):
    """Create a list of aggregate calculation information.

    Builds a list of calculation information from the current datasets
    aggregated datasets and aggregate calculations.
    """
    calcs_to_data = defaultdict(list)

    calculations = dataset.calculations(only_aggs=True)
    names_to_formulas = {c.name: c.formula for c in calculations}
    names = set(names_to_formulas.keys())

    for group, dataset in dataset.aggregated_datasets:
        labels_to_slugs = dataset.schema.labels_to_slugs
        calculations_for_dataset = list(set(
            labels_to_slugs.keys()).intersection(names))

        for calc in calculations_for_dataset:
            calcs_to_data[calc].append((
                names_to_formulas[calc], labels_to_slugs[calc],  group,
                dataset))

    return flatten(calcs_to_data.values())


def __update_is_valid(dataset, new_dframe):
    """Check if the update is valid.

    Check whether this is a right-hand side of any joins
    and deny the update if the update would produce an invalid
    join as a result.

    :param dataset: The dataset to check if update valid for.
    :param new_dframe: The update dframe to check.
    :returns: True is the update is valid, False otherwise.
    """
    select = {on: 1 for on in dataset.on_columns_for_rhs_of_joins if on in
              new_dframe.columns and on in dataset.columns}
    dframe = dataset.dframe(query_args=QueryArgs(select=select))

    for on in select.keys():
        merged_join_column = concat([new_dframe[on], dframe[on]])

        if len(merged_join_column) != merged_join_column.nunique():
            return False

    return True


def __create_aggregator(dataset, formula, name, groups, dframe=None):
    # TODO this should work with index eventually
    columns = parse_columns(dataset, formula, name, dframe, no_index=True)

    dependent_columns = Parser.dependent_columns(formula, dataset)
    aggregation = Parser.parse_aggregation(formula)

    # get dframe with only the necessary columns
    select = combine_dicts({group: 1 for group in groups},
                           {col: 1 for col in dependent_columns})

    # ensure at least one column (MONGO_ID) for the count aggregation
    query_args = QueryArgs(select=select or {MONGO_ID: 1})
    dframe = dataset.dframe(query_args=query_args, keep_mongo_keys=not select)

    return Aggregator(dframe, groups, aggregation, name, columns)


def __ensure_ready(dataset, update_id):
    # dataset must not be pending
    if not dataset.is_ready or (
            update_id and dataset.has_pending_updates(update_id)):
        dataset.reload()
        raise calculate_updates.retry()


def __find_merge_offset(dataset, merged_dataset):
    offset = 0

    for parent_id in merged_dataset.parent_ids:
        if dataset.dataset_id == parent_id:
            break

        offset += dataset.find_one(parent_id).num_rows

    return offset


def __propagate_column(dataset, parent_dataset):
    """Propagate columns in `parent_dataset` to `dataset`.

    When a new calculation is added to a dataset this will propagate the
    new column to all child (merged) datasets.

    :param dataset: THe child dataet.
    :param parent_dataset: The dataset to propagate.
    """
    # delete the rows in this dataset from the parent
    dataset.remove_parent_observations(parent_dataset.dataset_id)

    # get this dataset without the out-of-date parent rows
    dframe = dataset.dframe(keep_parent_ids=True)

    # create new dframe from the upated parent and add parent id
    parent_dframe = add_parent_column(parent_dataset.dframe(),
                                      parent_dataset.dataset_id)

    # merge this new dframe with the existing dframe
    updated_dframe = concat([dframe, parent_dframe])

    # save new dframe (updates schema)
    dataset.replace_observations(updated_dframe)
    dataset.clear_summary_stats()

    # recur into merged dataset
    [__propagate_column(x, dataset) for x in dataset.merged_datasets]


def __remapped_data(dataset_id, mapping, slugified_data):
    column_map = mapping.get(dataset_id) if mapping else None

    if column_map:
        slugified_data = [{column_map.get(k, k): v for k, v in row.items()}
                          for row in slugified_data]

    return slugified_data


def __slugify_data(new_data, labels_to_slugs):
    slugified_data = []
    new_data = to_list(new_data)

    for row in new_data:
        for key, value in row.iteritems():
            if labels_to_slugs.get(key) and key != MONGO_ID:
                del row[key]
                row[labels_to_slugs[key]] = value

        slugified_data.append(row)

    return slugified_data


def __update_aggregate_datasets(dataset, new_dframe, update=None):
    calcs_to_data = __calculation_data(dataset)

    for formula, slug, groups, a_dataset in calcs_to_data:
        __update_aggregate_dataset(dataset, formula, new_dframe, slug, groups,
                                   a_dataset, update is None)


def __update_aggregate_dataset(dataset, formula, new_dframe, name, groups,
                               a_dataset, reducible):
    """Update the aggregated dataset built for `dataset` with `calculation`.

    Proceed with the following steps:

        - delete the rows in this dataset from the parent
        - recalculate aggregated dataframe from aggregation
        - update aggregated dataset with new dataframe and add parent id
        - recur on all merged datasets descending from the aggregated
          dataset

    :param formula: The formula to execute.
    :param new_dframe: The DataFrame to aggregate on.
    :param name: The name of the aggregation.
    :param groups: A column or columns to group on.
    :type group: String, list of strings, or None.
    :param a_dataset: The DataSet to store the aggregation in.
    """
    # parse aggregation and build column arguments
    aggregator = __create_aggregator(
        dataset, formula, name, groups, dframe=new_dframe)
    new_agg_dframe = aggregator.update(dataset, a_dataset, formula, reducible)

    # jsondict from new dframe
    new_data = df_to_jsondict(new_agg_dframe)

    for merged_dataset in a_dataset.merged_datasets:
        # remove rows in child from this merged dataset
        merged_dataset.remove_parent_observations(a_dataset.dataset_id)

        # calculate updates for the child
        calculate_updates(merged_dataset, new_data,
                          parent_dataset_id=a_dataset.dataset_id)


def __update_joined_datasets(dataset, update):
    """Update any joined datasets."""
    if 'add' in update:
        new_dframe = update['add']

    for direction, other_dataset, on, j_dataset in dataset.joined_datasets:
        if 'add' in update:
            if direction == 'left':
                # only proceed if on in new dframe
                if on in new_dframe.columns:
                    left_dframe = other_dataset.dframe(padded=True)

                    # only proceed if new on value is in on column in lhs
                    if len(set(new_dframe[on]).intersection(
                            set(left_dframe[on]))):
                        merged_dframe = join_dataset(left_dframe, dataset, on)
                        j_dataset.replace_observations(merged_dframe)

                        # TODO is it OK not to propagate the join here?
            else:
                # if on in new data join with existing data
                if on in new_dframe:
                    new_dframe = join_dataset(new_dframe, other_dataset, on)

                calculate_updates(j_dataset, df_to_jsondict(new_dframe),
                                  parent_dataset_id=dataset.dataset_id)
        elif 'delete' in update:
            j_dataset.delete_observation(update['delete'])
        elif 'edit' in update:
            j_dataset.update_observation(*update['edit'])


def __update_merged_datasets(dataset, update):
    if 'add' in update:
        data = df_to_jsondict(update['add'])

        # store slugs as labels for child datasets
        data = __slugify_data(data, dataset.schema.labels_to_slugs)

    # update the merged datasets with new_dframe
    for mapping, merged_dataset in dataset.merged_datasets_with_map:
        if 'add' in update:
            mapped_data = __remapped_data(dataset.dataset_id, mapping, data)
            calculate_updates(merged_dataset, mapped_data,
                              parent_dataset_id=dataset.dataset_id)
        elif 'delete' in update:
            offset = __find_merge_offset(dataset, merged_dataset)
            merged_dataset.delete_observation(update['delete'] + offset)
        elif 'edit' in update:
            offset = __find_merge_offset(dataset, merged_dataset)
            index, data = update['edit']
            merged_dataset.update_observation(index + offset, data)

########NEW FILE########
__FILENAME__ = frame
from cStringIO import StringIO

from pandas import Series

from bamboo.lib.mongo import MONGO_ID_ENCODED


# reserved bamboo keys
BAMBOO_RESERVED_KEY_PREFIX = '^^'
DATASET_ID = BAMBOO_RESERVED_KEY_PREFIX + 'dataset_id'
INDEX = BAMBOO_RESERVED_KEY_PREFIX + 'index'
PARENT_DATASET_ID = BAMBOO_RESERVED_KEY_PREFIX + 'parent_dataset_id'

BAMBOO_RESERVED_KEYS = [
    DATASET_ID,
    INDEX,
    PARENT_DATASET_ID,
]

# all the reserved keys
RESERVED_KEYS = BAMBOO_RESERVED_KEYS + [MONGO_ID_ENCODED]


def add_id_column(df, dataset_id):
    return add_constant_column(df, dataset_id, DATASET_ID) if not\
        DATASET_ID in df.columns else df


def add_constant_column(df, value, name):
    column = Series([value] * len(df), index=df.index, name=name)
    return df.join(column)


def add_parent_column(df, parent_dataset_id):
    """Add parent ID column to this DataFrame."""
    return add_constant_column(df, parent_dataset_id, PARENT_DATASET_ID)


def df_to_csv_string(df):
    buffer = StringIO()
    df.to_csv(buffer, encoding='utf-8', index=False)
    return buffer.getvalue()


def join_dataset(left, other, on):
    """Left join an `other` dataset.

    :param other: Other dataset to join.
    :param on: Column or 2 comma seperated columns to join on.

    :returns: Joined DataFrame.

    :raises: `KeyError` if join columns not in datasets.
    """
    on_lhs, on_rhs = (on.split(',') * 2)[:2]

    right_dframe = other.dframe(padded=True)

    if on_lhs not in left.columns:
        raise KeyError('No item named "%s" in left hand side dataset' % on_lhs)

    if on_rhs not in right_dframe.columns:
        raise KeyError('No item named "%s" in right hand side dataset' %
                       on_rhs)

    right_dframe = right_dframe.set_index(on_rhs)

    if len(right_dframe.index) != len(right_dframe.index.unique()):
        msg = 'Join column "%s" of the right hand side dataset is not unique'
        raise NonUniqueJoinError(msg % on_rhs)

    shared_columns = left.columns.intersection(right_dframe.columns)

    if len(shared_columns):
        rename_map = [{c: '%s.%s' % (c, v) for c in shared_columns} for v
                      in ['x', 'y']]
        left.rename(columns=rename_map[0], inplace=True)
        right_dframe.rename(columns=rename_map[1], inplace=True)

    return left.join(right_dframe, on=on_lhs)


def remove_reserved_keys(df, exclude=[]):
    """Remove reserved internal columns in this DataFrame.

    :param keep_parent_ids: Keep parent column if True, default False.
    """
    reserved_keys = __column_intersect(
        df, BAMBOO_RESERVED_KEYS).difference(set(exclude))

    return df.drop(reserved_keys, axis=1)


def rows_for_parent_id(df, parent_id):
    """DataFrame with only rows for `parent_id`.

    :param parent_id: The ID to restrict rows to.

    :returns: A DataFrame including only rows with a parent ID equal to
        that passed in.
    """
    return df[df[PARENT_DATASET_ID] == parent_id].drop(PARENT_DATASET_ID, 1)


def __column_intersect(df, list_):
    """Return the intersection of `list_` and DataFrame's columns."""
    return set(list_).intersection(set(df.columns.tolist()))


class NonUniqueJoinError(Exception):
    pass

########NEW FILE########
__FILENAME__ = merge
from celery.task import task
from pandas import concat

from bamboo.core.frame import add_parent_column
from bamboo.lib.async import call_async
from bamboo.models.dataset import Dataset


class MergeError(Exception):
    """For errors while merging datasets."""
    pass


def merge_dataset_ids(dataset_ids, mapping):
    """Load a JSON array of dataset IDs and start a background merge task.

    :param dataset_ids: An array of dataset IDs to merge.

    :raises: `MergeError` if less than 2 datasets are provided. If a dataset
        cannot be found for a dataset ID it is ignored. Therefore if 2 dataset
        IDs are provided and one of them is bad an error is raised.  However,
        if three dataset IDs are provided and one of them is bad, an error is
        not raised.
    """
    datasets = [Dataset.find_one(dataset_id) for dataset_id in dataset_ids]
    datasets = [dataset for dataset in datasets if dataset.record]

    if len(datasets) < 2:
        raise MergeError(
            'merge requires 2 datasets (found %s)' % len(datasets))

    new_dataset = Dataset.create()

    call_async(__merge_datasets_task, new_dataset, datasets, mapping)

    return new_dataset


@task(default_retry_delay=2, ignore_result=True)
def __merge_datasets_task(new_dataset, datasets, mapping):
    """Merge datasets specified by dataset_ids.

    :param new_dataset: The dataset store the merged dataset in.
    :param dataset_ids: A list of IDs to merge into `new_dataset`.
    """
    # check that all datasets are in a 'ready' state
    while any([not dataset.record_ready for dataset in datasets]):
        [dataset.reload() for dataset in datasets]
        raise __merge_datasets_task.retry(countdown=1)

    new_dframe = __merge_datasets(datasets, mapping)

    # save the resulting dframe as a new dataset
    new_dataset.save_observations(new_dframe)

    # store the child dataset ID with each parent
    for dataset in datasets:
        dataset.add_merged_dataset(mapping, new_dataset)


def __merge_datasets(datasets, mapping):
    """Merge two or more datasets."""
    dframes = []

    if not mapping:
        mapping = {}

    for dataset in datasets:
        dframe = dataset.dframe()
        column_map = mapping.get(dataset.dataset_id)

        if column_map:
            dframe = dframe.rename(columns=column_map)

        dframe = add_parent_column(dframe, dataset.dataset_id)
        dframes.append(dframe)

    return concat(dframes, ignore_index=True)

########NEW FILE########
__FILENAME__ = operations
# future must be first
from __future__ import division
import operator

import numpy as np
from scipy.stats import percentileofscore

from bamboo.lib.datetools import now, parse_date_to_unix_time,\
    parse_str_to_unix_time, safe_parse_date_to_unix_time
from bamboo.lib.query_args import QueryArgs
from bamboo.lib.utils import parse_float


def extract_binary_children(parent):
    children = [parent.value[0]]

    for oper, val in parent.operator_operands(parent.value[1:]):
        children.append(val)

    return children


class EvalTerm(object):
    """Base class for evaluation."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.value = tokens[0]

    def operator_operands(self, tokenlist):
        """Generator to extract operators and operands in pairs."""
        it = iter(tokenlist)

        while 1:
            try:
                yield (it.next(), it.next())
            except StopIteration:
                break

    def operation(self, oper, result, val):
        return self.operations[oper](result, val)

    def get_children(self):
        return []

    def dependent_columns(self, dataset):
        return []


class EvalConstant(EvalTerm):
    """Class to evaluate a parsed constant or variable."""

    def eval(self, row, dataset):
        value = parse_float(self.value)
        if value is not None:
            return value

        # it may be a variable
        field = self.field(row)

        # test is date and parse as date
        return self.__parse_field(field, dataset)

    def __parse_field(self, field, dataset):
            if dataset and dataset.schema.is_date_simpletype(
                    self.value):
                field = safe_parse_date_to_unix_time(field)

            return field

    def field(self, row):
        return row.get(self.value)

    def dependent_columns(self, dataset):
        value = parse_float(self.value)
        if value is not None:
            return []

        # if value is not number or date, add as a column
        return [self.value]


class EvalString(EvalTerm):
    """Class to evaluate a parsed string."""

    def eval(self, row, dataset):
        return self.value


class EvalSignOp(EvalTerm):
    """Class to evaluate expressions with a leading + or - sign."""

    def __init__(self, tokens):
        self.sign, self.value = tokens[0]

    def eval(self, row, dataset):
        mult = {'+': 1, '-': -1}[self.sign]
        return mult * self.value.eval(row, dataset)

    def get_children(self):
        return [self.value]


class EvalBinaryArithOp(EvalTerm):
    """Class for evaluating binary arithmetic operations."""

    operations = {
        '+': operator.__add__,
        '-': operator.__sub__,
        '*': operator.__mul__,
        '/': operator.__truediv__,
        '^': operator.__pow__,
    }

    def eval(self, row, dataset):
        result = np.float64(self.value[0].eval(row, dataset))

        for oper, val in self.operator_operands(self.value[1:]):
            val = np.float64(val.eval(row, dataset))
            result = self.operation(oper, result, val)
            if np.isinf(result):
                return np.nan

        return result

    def get_children(self):
        return extract_binary_children(self)


class EvalMultOp(EvalBinaryArithOp):
    """Class to distinguish precedence of multiplication/division expressions.
    """
    pass


class EvalPlusOp(EvalBinaryArithOp):
    """Class to distinguish precedence of addition/subtraction expressions.
    """
    pass


class EvalExpOp(EvalBinaryArithOp):
    """Class to distinguish precedence of exponentiation expressions.
    """
    pass


class EvalComparisonOp(EvalTerm):
    """Class to evaluate comparison expressions."""

    op_map = {
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "!=": lambda a, b: a != b,
        "==": lambda a, b: a == b,
    }

    def eval(self, row, dataset):
        val1 = np.float64(self.value[0].eval(row, dataset))

        for oper, val in self.operator_operands(self.value[1:]):
            fn = EvalComparisonOp.op_map[oper]
            val2 = np.float64(val.eval(row, dataset))
            if not fn(val1, val2):
                break
            val1 = val2
        else:
            return True

        return False

    def get_children(self):
        return extract_binary_children(self)


class EvalNotOp(EvalTerm):
    """Class to evaluate not expressions."""

    def __init__(self, tokens):
        self.value = tokens[0][1]

    def eval(self, row, dataset):
        return not self.value.eval(row, dataset)

    def get_children(self):
        return [self.value]


class EvalBinaryBooleanOp(EvalTerm):
    """Class for evaluating binary boolean operations."""

    operations = {
        'and': lambda p, q: p and q,
        'or': lambda p, q: p or q,
    }

    def eval(self, row, dataset):
        result = np.bool_(self.value[0].eval(row, dataset))

        for oper, val in self.operator_operands(self.value[1:]):
            val = np.bool_(val.eval(row, dataset))
            result = self.operation(oper, result, val)

        return result

    def get_children(self):
        return extract_binary_children(self)


class EvalAndOp(EvalBinaryBooleanOp):
    """Class to distinguish precedence of and expressions."""
    pass


class EvalOrOp(EvalBinaryBooleanOp):
    """Class to distinguish precedence of or expressions."""
    pass


class EvalInOp(EvalTerm):
    """Class to eval in expressions."""

    def eval(self, row, dataset):
        val_to_test = str(self.value[0].eval(row, dataset))
        val_list = []

        for val in self.value[1:]:
            val_list.append(val.eval(row, dataset))

        return val_to_test in val_list

    def get_children(self):
        return self.value


class EvalCaseOp(EvalTerm):
    """Class to eval case statements."""

    def eval(self, row, dataset):
        for token in self.value:
            case_result = token.eval(row, dataset)
            if case_result:
                return case_result

        return np.nan

    def get_children(self):
        return self.value


class EvalMapOp(EvalTerm):
    """Class to eval map statements."""

    def eval(self, row, dataset):
        if self.tokens[0] == 'default' or self.tokens[0].eval(row, dataset):
            return self.tokens[1].eval(row, dataset)

        return False

    def get_children(self):
        # special "default" key returns the next token (value)
        if self.tokens[0] == 'default':
            return [self.tokens[1]]

        # otherwise, return the map key and value
        return self.tokens[0:2]


class EvalFunction(object):
    """Class to eval functions."""

    def __init__(self, tokens):
        self.value = tokens[0][1]

    def get_children(self):
        return [self.value]

    def dependent_columns(self, dataset):
        return []


class EvalDate(EvalFunction):
    """Class to evaluate date expressions."""

    def eval(self, row, dataset):
        # parse date from string
        return parse_str_to_unix_time(self.value.eval(row, dataset))


class EvalToday(EvalTerm):
    """Class to produce te current date time."""

    def eval(self, row, dataset):
        return parse_date_to_unix_time(now())


class EvalPercentile(EvalFunction):
    """Class to evaluate percentile expressions."""

    def eval(self, row, dataset):
        # parse date from string
        col = self.value.value
        query_args = QueryArgs(select={col: 1})
        column = dataset.dframe(query_args=query_args)[col]
        field = self.value.field(row)
        return percentileofscore(column, field)

    def get_children(self):
        return []

    def dependent_columns(self, dataset):
        return [self.value.value]

########NEW FILE########
__FILENAME__ = parser
from functools import partial

from pyparsing import alphanums, nums, oneOf, opAssoc, operatorPrecedence,\
    CaselessLiteral, Combine, Keyword, Literal, MatchFirst, Optional,\
    ParseException, Regex, Word, ZeroOrMore

from bamboo.core.aggregations import AGGREGATIONS
from bamboo.core.operations import EvalAndOp, EvalCaseOp, EvalComparisonOp,\
    EvalConstant, EvalExpOp, EvalDate, EvalInOp, EvalMapOp, EvalMultOp,\
    EvalNotOp, EvalOrOp, EvalPercentile, EvalPlusOp, EvalSignOp, EvalString,\
    EvalToday


def build_caseless_or_expression(strings):
    literals = [CaselessLiteral(aggregation) for aggregation in strings]
    return reduce(lambda or_expr, literal: or_expr | literal, literals)


def get_dependent_columns(parsed_expr, dataset):
    return __find_dependent_columns(dataset, parsed_expr, [])


def __find_dependent_columns(dataset, parsed_expr, result):
    """Find dependent columns for a dataset and parsed expression.

    :param dataset: The dataset to find dependent columns for.
    :param parsed_expr: The parsed formula expression.
    """
    dependent_columns = parsed_expr.dependent_columns(dataset)
    result.extend(dependent_columns)

    for child in parsed_expr.get_children():
        __find_dependent_columns(dataset, child, result)

    return result


class ParseError(Exception):
    """For errors while parsing formulas."""
    pass


class Parser(object):
    """Class for parsing and evaluating formula.

    Attributes:

    - aggregation: Aggregation parsed from formula.
    - aggregation_names: Possible aggregations.
    - bnf: Cached Backus-Naur Form of formula.
    - column_functions: Cached additional columns as aggregation parameters.
    - function_names: Names of possible functions in formulas.
    - operator_names: Names of possible operators in formulas.
    - parsed_expr: Cached parsed expression.
    - special_names: Names of possible reserved names in formulas.
    - reserved_words: List of all possible reserved words that may be used in
      formulas.
    """

    aggregation = None
    aggregation_names = AGGREGATIONS.keys()
    bnf = None
    column_functions = None
    function_names = ['date', 'percentile', 'today']
    operator_names = ['and', 'or', 'not', 'in']
    parsed_expr = None
    special_names = ['default']

    reserved_words = aggregation_names + function_names + operator_names +\
        special_names

    def __init__(self):
        self.bnf = self.__build_bnf()

    @classmethod
    def dependent_columns(cls, formula, dataset):
        functions, _ = cls.parse(formula)
        columns = [get_dependent_columns(f, dataset) for f in functions]

        return set.union(set(), *columns)

    @property
    def functions(self):
        return self.column_functions if self.aggregation else self.parsed_expr

    def store_aggregation(self, _, __, tokens):
        """Cached a parsed aggregation."""
        self.aggregation = tokens[0]
        self.column_functions = tokens[1:]

    def __build_bnf(self):
        """Parse formula to function based on language definition.

        Backus-Naur Form of formula language:

        =========   ==========
        Operation   Expression
        =========   ==========
        addop       '+' | '-'
        multop      '*' | '/'
        expop       '^'
        compop      '==' | '<' | '>' | '<=' | '>='
        notop       'not'
        andop       'and'
        orop        'or'
        real        \d+(.\d+)
        integer     \d+
        variable    \w+
        string      ".+"
        atom        real | integer | variable
        func        func ( atom )
        factor      atom [ expop factor]*
        term        factor [ multop factor ]*
        expr        term [ addop term ]*
        equation    expr [compop expr]*
        in          string in '[' "string"[, "string"]* ']'
        neg         [notop]* equation | in
        conj        neg [andop neg]*
        disj        conj [orop conj]*
        case        'case' disj: atom[, disj: atom]*[, 'default': atom]
        trans       trans ( case )
        agg         agg ( trans[, trans]* )
        =========   ==========

        """
        if self.bnf:
            return self.bnf

        # literal operators
        exp_op = Literal('^')
        sign_op = oneOf('+ -')
        mult_op = oneOf('* /')
        plus_op = oneOf('+ -')
        not_op = CaselessLiteral('not')
        and_op = CaselessLiteral('and')
        or_op = CaselessLiteral('or')
        in_op = CaselessLiteral('in').suppress()
        comparison_op = oneOf('< <= > >= != ==')
        case_op = CaselessLiteral('case').suppress()

        # aggregation functions
        aggregations = build_caseless_or_expression(self.aggregation_names)

        # literal syntactic
        open_bracket = Literal('[').suppress()
        close_bracket = Literal(']').suppress()
        open_paren = Literal('(').suppress()
        close_paren = Literal(')').suppress()
        comma = Literal(',').suppress()
        dquote = Literal('"').suppress()
        colon = Literal(':').suppress()

        # functions
        date_func = CaselessLiteral('date')
        percentile_func = CaselessLiteral('percentile')
        today_func = CaselessLiteral('today()').setParseAction(EvalToday)

        # case statment
        default = CaselessLiteral('default')

        reserved_words = MatchFirst(
            [Keyword(word) for word in self.reserved_words])

        # atoms
        integer = Word(nums)
        real = Combine(Word(nums) + '.' + Word(nums))
        variable = ~reserved_words + Word(alphanums + '_')
        atom = real | integer | variable
        atom.setParseAction(EvalConstant)

        # everything between pairs of double quotes is a string
        string = dquote + Regex('[^"]+') + dquote
        string.setParseAction(EvalString)

        # expressions
        in_list = open_bracket + string +\
            ZeroOrMore(comma + string) + close_bracket

        func_expr = operatorPrecedence(string, [
            (date_func, 1, opAssoc.RIGHT, EvalDate),
        ]) | today_func

        arith_expr = operatorPrecedence(atom | func_expr, [
            (sign_op, 1, opAssoc.RIGHT, EvalSignOp),
            (exp_op, 2, opAssoc.RIGHT, EvalExpOp),
            (mult_op, 2, opAssoc.LEFT, EvalMultOp),
            (plus_op, 2, opAssoc.LEFT, EvalPlusOp),
        ])

        comp_expr = operatorPrecedence(arith_expr, [
            (comparison_op, 2, opAssoc.LEFT, EvalComparisonOp),
        ])

        prop_expr = operatorPrecedence(comp_expr | in_list, [
            (in_op, 2, opAssoc.RIGHT, EvalInOp),
            (not_op, 1, opAssoc.RIGHT, EvalNotOp),
            (and_op, 2, opAssoc.LEFT, EvalAndOp),
            (or_op, 2, opAssoc.LEFT, EvalOrOp),
        ])

        default_statement = (default + colon + atom).setParseAction(EvalMapOp)
        map_statement = (prop_expr + colon + atom).setParseAction(EvalMapOp)

        case_list = map_statement + ZeroOrMore(
            comma + map_statement) + Optional(comma + default_statement)

        case_expr = operatorPrecedence(case_list, [
            (case_op, 1, opAssoc.RIGHT, EvalCaseOp),
        ]) | prop_expr

        trans_expr = operatorPrecedence(case_expr, [
            (percentile_func, 1, opAssoc.RIGHT, EvalPercentile),
        ])

        return ((aggregations + open_paren + Optional(
            trans_expr + ZeroOrMore(comma + trans_expr)))
            .setParseAction(self.store_aggregation) + close_paren)\
            | trans_expr

    @classmethod
    def parse(cls, formula):
        """Parse formula and return evaluation function.

        Parse `formula` into an aggregation name and functions.
        There will be multiple functions is the aggregation takes multiple
        arguments, e.g. ratio which takes a numerator and denominator formula.

        Examples:

        - constants
            - ``9 + 5``,
        - aliases
            - ``rating``,
            - ``gps``,
        - arithmetic
            - ``amount + gps_alt``,
            - ``amount - gps_alt``,
            - ``amount + 5``,
            - ``amount - gps_alt + 2.5``,
            - ``amount * gps_alt``,
            - ``amount / gps_alt``,
            - ``amount * gps_alt / 2.5``,
            - ``amount + gps_alt * gps_precision``,
        - precedence
            - ``(amount + gps_alt) * gps_precision``,
        - comparison
            - ``amount == 2``,
            - ``10 < amount``,
            - ``10 < amount + gps_alt``,
        - logical
            - ``not amount == 2``,
            - ``not(amount == 2)``,
            - ``amount == 2 and 10 < amount``,
            - ``amount == 2 or 10 < amount``,
            - ``not not amount == 2 or 10 < amount``,
            - ``not amount == 2 or 10 < amount``,
            - ``not amount == 2) or 10 < amount``,
            - ``not(amount == 2 or 10 < amount)``,
            - ``amount ^ 3``,
            - ``amount + gps_alt) ^ 2 + 100``,
            - ``amount``,
            - ``amount < gps_alt - 100``,
        - membership
            - ``rating in ["delectible"]``,
            - ``risk_factor in ["low_risk"]``,
            - ``amount in ["9.0", "2.0", "20.0"]``,
            - ``risk_factor in ["low_risk"]) and (amount in ["9.0", "20.0"])``,
        - dates
            - ``date("09-04-2012") - submit_date > 21078000``,
        - cases
            - ``case food_type in ["morning_food"]: 1, default: 3``
        - transformations: row-wise column based aggregations
            - ``percentile(amount)``

        :param formula: The string to parse.

        :returns: A tuple with the name of the aggregation in the formula, if
           any and a list of functions built from the input string.
        """
        parser = cls()

        try:
            parser.parsed_expr = parser.bnf.parseString(formula, parseAll=True)
        except ParseException, err:
            raise ParseError('Parse Failure for string "%s": %s' % (
                             formula, err))

        return [parser.functions, parser.aggregation]

    @classmethod
    def parse_aggregation(cls, formula):
        _, a = cls.parse(formula)
        return a

    @classmethod
    def parse_function(cls, formula):
        return cls.parse_functions(formula)[0]

    @classmethod
    def parse_functions(cls, formula):
        return [partial(f.eval) for f in cls.parse(formula)[0]]

    @classmethod
    def validate(cls, dataset, formula, groups):
        """Validate `formula` and `groups` for dataset.

        Validate the formula and group string by attempting to get a row from
        the dframe for the dataset and then running parser validation on this
        row. Additionally, ensure that the groups in the group string are
        columns in the dataset.

        :param dataset: The dataset to validate for.
        :param formula: The formula to validate.
        :param groups: A list of columns to group by.

        :returns: The aggregation (or None) for the formula.
        """
        cls.validate_formula(formula, dataset)

        for group in groups:
            if not group in dataset.schema.keys():
                raise ParseError(
                    'Group %s not in dataset columns.' % group)

    @classmethod
    def validate_formula(cls, formula, dataset):
        """Validate the *formula* on an example *row* of data.

        Rebuild the BNF then parse the `formula` given the sample `row`.

        :param formula: The formula to validate.
        :param dataset: The dataset to validate against.

        :returns: The aggregation for the formula.
        """
        # check valid formula
        cls.parse(formula)
        schema = dataset.schema

        if not schema:
            raise ParseError(
                'No schema for dataset, please add data or wait for it to '
                'finish processing')

        for column in cls.dependent_columns(formula, dataset):
            if column not in schema.keys():
                raise ParseError('Missing column reference: %s' % column)

    def __getstate__(self):
        """Get state for pickle."""
        return [
            self.aggregation,
            self.aggregation_names,
            self.function_names,
            self.operator_names,
            self.special_names,
            self.reserved_words,
            self.special_names,
        ]

    def __setstate__(self, state):
        """Set internal variables from pickled state."""
        self.aggregation, self.aggregation_names, self.function_names,\
            self.operator_names, self.special_names, self.reserved_words,\
            self.special_names = state
        self.__build_bnf()

########NEW FILE########
__FILENAME__ = summary
from bamboo.lib.jsontools import series_to_jsondict
from bamboo.lib.mongo import dict_from_mongo, dict_for_mongo
from bamboo.lib.utils import combine_dicts


MAX_CARDINALITY_FOR_COUNT = 10000
SUMMARY = 'summary'


class ColumnTypeError(Exception):
    """Exception when grouping on a non-dimensional column."""
    pass


def summarize_series(is_factor, data):
    """Call summary function dependent on dtype type.

    :param dtype: The dtype of the column to be summarized.
    :param data: The data to be summarized.

    :returns: The appropriate summarization for the type of `dtype`.
    """
    return data.value_counts() if is_factor else data.describe()


def summarizable(dframe, col, groups, dataset):
    """Check if column should be summarized.

    :param dframe: DataFrame to check unique values in.
    :param col: Column to check for factor and number of uniques.
    :param groups: List of groups if summarizing with group, can be empty.
    :param dataset: Dataset to pull schema from.

    :returns: True if column, with parameters should be summarized, otherwise
        False.
    """
    if dataset.is_dimension(col):
        cardinality = dframe[col].nunique() if len(groups) else\
            dataset.cardinality(col)
        if cardinality > MAX_CARDINALITY_FOR_COUNT:
            return False

    return not col in groups


def summarize_df(dframe, dataset, groups=[]):
    """Calculate summary statistics."""
    return {
        col: {
            SUMMARY: series_to_jsondict(
                summarize_series(dataset.is_dimension(col), data))
        } for col, data in dframe.iteritems() if summarizable(
            dframe, col, groups, dataset)
    }


def summarize_with_groups(dframe, groups, dataset):
    """Calculate summary statistics for group."""
    return series_to_jsondict(
        dframe.groupby(groups).apply(summarize_df, dataset, groups))


def summarize(dataset, dframe, groups, no_cache, update=False):
    """Raises a ColumnTypeError if grouping on a non-dimensional column."""
    # do not allow group by numeric types
    for group in groups:
        if not dataset.is_factor(group):
            raise ColumnTypeError("group: '%s' is not a dimension." % group)

    group_str = dataset.join_groups(groups) or dataset.ALL

    # check cached stats for group and update as necessary
    stats = dataset.stats
    group_stats = stats.get(group_str)

    if no_cache or not group_stats or update:
        group_stats = summarize_with_groups(dframe, groups, dataset) if\
            groups else summarize_df(dframe, dataset)

        if not no_cache:
            if update:
                original_group_stats = stats.get(group_str, {})
                group_stats = combine_dicts(original_group_stats, group_stats)

            stats.update({group_str: group_stats})
            dataset.update({dataset.STATS: dict_for_mongo(stats)})

    stats_dict = dict_from_mongo(group_stats)

    if groups:
        stats_dict = {group_str: stats_dict}

    return stats_dict

########NEW FILE########
__FILENAME__ = async
import os

ASYNC_FLAG = 'BAMBOO_ASYNC_OFF'


def is_async():
    return not os.getenv(ASYNC_FLAG)


def set_async(on):
    if on:
        if not is_async():
            del os.environ[ASYNC_FLAG]
    else:
        os.environ[ASYNC_FLAG] = 'True'


def call_async(function, *args, **kwargs):
    """Potentially asynchronously call `function` with the arguments.

    :param function: The function to call.
    :param args: Arguments for the function.
    :param kwargs: Keyword arguments for the function.
    """
    countdown = kwargs.pop('countdown', 0)

    if is_async():
        function.__getattribute__('apply_async')(
            countdown=countdown, args=args, kwargs=kwargs)
    else:  # pragma: no cover
        function(*args, **kwargs)

########NEW FILE########
__FILENAME__ = datetools
from calendar import timegm
from datetime import datetime

from dateutil.parser import parse as date_parse
import numpy as np

from bamboo.lib.utils import is_float_nan


def __parse_dates(dframe):
    for i, dtype in enumerate(dframe.dtypes):
        if dtype.type == np.object_:
            column = dframe.columns[i]
            new_column = _convert_column_to_date(dframe, column)

            if not new_column is None:
                dframe[column] = new_column

    return dframe


def __parse_dates_schema(dframe, schema):
    """Convert columes to datetime if column in *schema* is of type datetime.

    :param dframe: The DataFrame to convert columns in.

    :returns: A DataFrame with column values convert to datetime types.
    """
    dframe_columns = dframe.columns.tolist()

    for column, column_schema in schema.items():
        if column in dframe_columns and schema.is_date_simpletype(column):
            new_column = _convert_column_to_date(dframe, column)

            if not new_column is None:
                dframe[column] = new_column

    return dframe


def recognize_dates(df, schema=None):
    """Convert data columns to datetimes.

    Check if object columns in a dataframe can be parsed as dates.
    If yes, rewrite column with values parsed as dates.

    If schema is passed, convert columes to datetime if column in *schema* is
    of type datetime.

    :param df: The DataFrame to convert columns in.
    :param schema: Schema to define columns of type datetime.

    :returns: A DataFrame with column values convert to datetime types.
    """
    return __parse_dates_schema(df, schema) if schema else __parse_dates(df)


def _is_potential_date(value):
    return not (is_float_nan(value) or isinstance(value, bool))


def _convert_column_to_date(dframe, column):
    """Inline conversion of column in dframe to date type."""
    try:
        return dframe[column].apply(parse_date)
    except (AttributeError, OverflowError, ValueError):
        # It is already a datetime, a number that is too large to be a date, or
        # not a correctly formatted date.
        pass


def now():
    return datetime.now()


def parse_date(x):
    try:
        return date_parse(x) if _is_potential_date(x) else x
    except ValueError:
        return datetime.strptime(x, '%d%b%Y')


def parse_str_to_unix_time(value):
    return parse_date_to_unix_time(date_parse(value))


def parse_date_to_unix_time(date):
    return timegm(date.utctimetuple())


def parse_timestamp_query(query, schema):
    """Interpret date column queries as JSON."""
    if query:
        for date_column in schema.datetimes(query.keys()):
            query[date_column] = {
                key: datetime.fromtimestamp(int(value)) for (key, value) in
                query[date_column].items()
            }

    return query


def safe_parse_date_to_unix_time(date):
    if isinstance(date, datetime):
        date = parse_date_to_unix_time(date)

    return date

########NEW FILE########
__FILENAME__ = decorators
class classproperty(property):
    """Declare properties for classes."""

    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()

########NEW FILE########
__FILENAME__ = exceptions
class ArgumentError(Exception):
    pass

########NEW FILE########
__FILENAME__ = jsontools
from bson import json_util
import numpy as np
import simplejson as json

from bamboo.lib.mongo import dump_mongo_json
from bamboo.lib.utils import is_float_nan


# JSON encoding string
JSON_NULL = 'null'


class JSONError(Exception):
    """For errors while parsing JSON."""
    pass


def df_to_jsondict(df):
    """Return DataFrame as a list of dicts for each row."""
    return [series_to_jsondict(series) for _, series in df.iterrows()]


def df_to_json(df):
    """Convert DataFrame to a list of dicts, then dump to JSON."""
    jsondict = df_to_jsondict(df)
    return dump_mongo_json(jsondict)


def get_json_value(value):
    """Parse JSON value based on type."""
    if is_float_nan(value):
        value = JSON_NULL
    elif isinstance(value, np.int64):
        value = int(value)
    elif isinstance(value, np.bool_):
        value = bool(value)

    return value


def series_to_jsondict(series):
    """Convert a Series to a dictionary encodable as JSON."""
    return series if series is None else {
        unicode(key): get_json_value(value)
        for key, value in series.iteritems()
    }


def safe_json_loads(string, error_title='string'):
    try:
        return string and json.loads(string, object_hook=json_util.object_hook)
    except ValueError as err:
        raise JSONError('cannot decode %s: %s' % (error_title, err.__str__()))

########NEW FILE########
__FILENAME__ = mail
import smtplib


def __format_message(recipient, sender, subject, body):
    return ('To: %s\r\nFrom: %s\r\nSubject: %s\r\nContent-type:'
            'text/plain\r\n\r\n%s' % (recipient, sender, subject, body))


def send_mail(smtp_server, mailbox_name, mailbox_password, recipient, sender,
              subject, body):
    msg = __format_message(recipient, sender, subject, body)

    server = smtplib.SMTP(smtp_server, 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(mailbox_name, mailbox_password)
    server.sendmail(sender, recipient, msg)
    server.close()

########NEW FILE########
__FILENAME__ = mongo
from base64 import b64encode
from numpy import datetime64
import simplejson as json
import re

from bson import json_util


# _id is reserved by MongoDB
MONGO_RESERVED_KEY_PREFIX = '##'
MONGO_ID = '_id'
MONGO_ID_ENCODED = MONGO_RESERVED_KEY_PREFIX + '_id'

ILLEGAL_VALUES = ['$', '.']
REPLACEMENT_VALUES = [b64encode(value) for value in ILLEGAL_VALUES]

RE_ILLEGAL_MAP = [(re.compile(r'\%s' % value), REPLACEMENT_VALUES[idx]) for
                  idx, value in enumerate(ILLEGAL_VALUES)]
RE_LEGAL_MAP = [(re.compile(r'\%s' % value), ILLEGAL_VALUES[idx]) for
                idx, value in enumerate(REPLACEMENT_VALUES)]


def df_mongo_decode(df, keep_mongo_keys=False):
    """Decode MongoDB reserved keys in this DataFrame."""
    rename_dict = {}

    if MONGO_ID in df.columns:
        if keep_mongo_keys:
            df.rename(columns={MONGO_ID: MONGO_ID_ENCODED,
                               MONGO_ID_ENCODED: MONGO_ID}, inplace=True)
        else:
            del df[MONGO_ID]
            if MONGO_ID_ENCODED in df.columns:
                rename_dict[MONGO_ID_ENCODED] = MONGO_ID

    if rename_dict:
        df.rename(columns={MONGO_ID_ENCODED: MONGO_ID}, inplace=True)

    return df


def dump_mongo_json(obj):
    """Dump JSON using BSON conversion.

    Args:

    :param obj: Datastructure to dump as JSON.

    :returns: JSON string of dumped `obj`.
    """
    return json.dumps(obj, default=json_util.default)


def remove_mongo_reserved_keys(_dict):
    """Remove any keys reserved for MongoDB from `_dict`.

    Check for `MONGO_ID` in stored dictionary.  If found replace
    with unprefixed, if not found remove reserved key from dictionary.

    Args:

    :param _dict: Dictionary to remove reserved keys from.

    :returns: Dictionary with reserved keys removed.
    """
    if _dict.get(MONGO_ID_ENCODED):
        _dict[MONGO_ID] = _dict.pop(MONGO_ID_ENCODED)
    else:
        # remove mongo reserved keys
        del _dict[MONGO_ID]

    return _dict


def reserve_encoded(string):
    """Return encoding prefixed string."""
    return MONGO_ID_ENCODED if string == MONGO_ID else string


def dict_from_mongo(_dict):
    for key, value in _dict.items():
        if isinstance(value, list):
            value = [dict_from_mongo(obj)
                     if isinstance(obj, dict) else obj for obj in value]
        elif isinstance(value, dict):
            value = dict_from_mongo(value)

        if _was_encoded_for_mongo(key):
            del _dict[key]
            _dict[_decode_from_mongo(key)] = value

    return _dict


def dict_for_mongo(_dict):
    """Encode all keys in `_dict` for MongoDB."""
    for key, value in _dict.items():
        if _is_invalid_for_mongo(key):
            del _dict[key]
            key = key_for_mongo(key)

        if isinstance(value, list):
            _dict[key] = [dict_for_mongo(obj) if isinstance(obj, dict) else obj
                          for obj in value]
        elif isinstance(value, dict):
            _dict[key] = dict_for_mongo(value)
        else:
            _dict[key] = value_for_mongo(value)

    return _dict


def key_for_mongo(key):
    """Encode illegal MongoDB characters in string.

    Base64 encode any characters in a string that cannot be MongoDB keys. This
    includes any '$' and any '.'. '$' are supposed to be allowed as the
    non-first character but the current version of MongoDB does not allow any
    occurence of '$'.

    :param key: The string to remove characters from.

    :returns: The string with illegal keys encoded.
    """
    return reduce(lambda s, expr: expr[0].sub(expr[1], s),
                  RE_ILLEGAL_MAP, key)


def value_for_mongo(value):
    """Ensure value is a format acceptable for a MongoDB value.

    :param value: The value to encode.

    :returns: The encoded value.
    """
    if isinstance(value, datetime64):
        value = str(value)

    return value


def _decode_from_mongo(key):
    return reduce(lambda s, expr: expr[0].sub(expr[1], s),
                  RE_LEGAL_MAP, key)


def _is_invalid_for_mongo(key):
    """Return if string is invalid for storage in MongoDB."""
    return any([key.count(value) > 0 for value in ILLEGAL_VALUES])


def _was_encoded_for_mongo(key):
    return any([key.count(value) > 0 for value in REPLACEMENT_VALUES])

########NEW FILE########
__FILENAME__ = parsing
from bamboo.core.parser import Parser
from bamboo.lib.mongo import MONGO_ID, MONGO_ID_ENCODED
from bamboo.lib.query_args import QueryArgs
from bamboo.lib.schema_builder import make_unique


def parse_columns(dataset, formula, name, dframe=None, no_index=False):
    """Parse a formula and return columns resulting from its functions.

    Parse a formula into a list of functions then apply those functions to
    the Data Frame and return the resulting columns.

    :param formula: The formula to parse.
    :param name: Name of the formula.
    :param dframe: A DataFrame to apply functions to.
    :param no_index: Drop the index on result columns.
    """
    functions = Parser.parse_functions(formula)
    dependent_columns = Parser.dependent_columns(formula, dataset)

    # make select from dependent_columns
    if dframe is None:
        select = {col: 1 for col in dependent_columns or [MONGO_ID]}

        dframe = dataset.dframe(
            query_args=QueryArgs(select=select),
            keep_mongo_keys=True).set_index(MONGO_ID_ENCODED)

        if not dependent_columns:
            # constant column, use dummy
            dframe['dummy'] = 0

    return __build_columns(dataset, dframe, functions, name, no_index)


def __build_columns(dataset, dframe, functions, name, no_index):
    columns = []

    for function in functions:
        column = dframe.apply(function, axis=1, args=(dataset,))
        column.name = make_unique(name, [c.name for c in columns])

        if no_index:
            column = column.reset_index(drop=True)

        columns.append(column)

    return columns

########NEW FILE########
__FILENAME__ = query_args
from dateutil import parser
from time import mktime

from bamboo.lib.utils import combine_dicts, replace_keys


def parse_order_by(order_by):
    if order_by:
        if order_by[0] in ('-', '+'):
            sort_dir, field = -1 if order_by[0] == '-' else 1, order_by[1:]
        else:
            sort_dir, field = 1, order_by
        order_by = [(field, sort_dir)]

    return order_by


def parse_dates_from_query(query, dataset):
    if query and dataset:
        for col in dataset.schema.datetimes(query.keys()):
            query[col] = maybe_parse_date(query[col])

    return query or {}


def maybe_parse_date(o):
    if isinstance(o, dict):
        return {k: maybe_parse_date(v) for k, v in o.items()}
    elif isinstance(o, list):
        return [maybe_parse_date(e) for e in o]
    elif isinstance(o, basestring):
        return mktime(parser.parse(o).timetuple())
    else:
        return o


class QueryArgs(object):
    def __init__(self, query=None, select=None, distinct=None, limit=0,
                 order_by=None, dataset=None):
        """A holder for query arguments.

        :param query: An optional query.
        :param select: An optional select to limit the fields in the dframe.
        :param distinct: Return distinct entries for this field.
        :param limit: Limit on the number of rows in the returned dframe.
        :param order_by: Sort resulting rows according to a column value and
            sign indicating ascending or descending.

        Example of `order_by`:

          - ``order_by='mycolumn'``
          - ``order_by='-mycolumn'``
        """
        self.query = parse_dates_from_query(query, dataset)
        self.select = select
        self.distinct = distinct
        self.limit = limit
        self.order_by = parse_order_by(order_by)

    def encode(self, encoding, query):
        """Encode query, order_by, and select given an encoding.

        The query will be combined with the existing query.

        :param encoding: A dict to encode the QueryArgs fields with.
        :param query: An additional dict to combine with the existing query.
        """
        self.query = replace_keys(combine_dicts(self.query, query), encoding)
        self.order_by = self.order_by and replace_keys(dict(self.order_by),
                                                       encoding).items()
        self.select = self.select and replace_keys(self.select, encoding)

    def __nonzero__(self):
        return bool(self.query or self.select or self.distinct or self.limit
                    or self.order_by)

########NEW FILE########
__FILENAME__ = readers
from functools import partial
import simplejson as json
import os
import tempfile

from celery.exceptions import RetryTaskError
from celery.task import task
import pandas as pd

from bamboo.lib.async import call_async
from bamboo.lib.datetools import recognize_dates
from bamboo.lib.schema_builder import filter_schema


@task(ignore_result=True)
def import_dataset(dataset, file_reader, delete=False):
    """For reading a URL and saving the corresponding dataset.

    Import a DataFrame using the provided `file_reader` function. All
    exceptions are caught and on exception the dataset is marked as failed and
    set for deletion after 24 hours.

    :param dataset: The dataset to import into.
    :param file_reader: Function for reading the dataset.
    :param delete: Delete filepath_or_buffer after import, default False.
    """
    try:
        dframe = file_reader()
        dataset.save_observations(dframe)
    except Exception as e:
        if isinstance(e, RetryTaskError):
            raise e
        else:
            dataset.failed(e.__str__())
            dataset.delete(countdown=86400)


def csv_file_reader(name, na_values=[], delete=False):
    try:
        return recognize_dates(
            pd.read_csv(name, encoding='utf-8', na_values=na_values))
    finally:
        if delete:
            os.unlink(name)


def json_file_reader(content):
    return recognize_dates(pd.DataFrame(json.loads(content)))


class ImportableDataset(object):
    def import_from_url(self, url, na_values=[], allow_local_file=False):
        """Load a URL, read from a CSV, add data to dataset.

        :param url: URL to load file from.
        :param allow_local_file: Allow URL to refer to a local file.

        :raises: `IOError` for an unreadable file or a bad URL.

        :returns: The created dataset.
        """
        if not allow_local_file and isinstance(url, basestring)\
                and url[0:4] == 'file':
            raise IOError

        call_async(
            import_dataset, self, partial(
                csv_file_reader, url, na_values=na_values))

        return self

    def import_from_csv(self, csv_file, na_values=[]):
        """Import data from a CSV file.

        .. note::

            Write to a named tempfile in order  to get a handle for pandas'
            `read_csv` function.

        :param csv_file: The CSV File to create a dataset from.

        :returns: The created dataset.
        """
        if 'file' in dir(csv_file):
            csv_file = csv_file.file

        tmpfile = tempfile.NamedTemporaryFile(delete=False)
        tmpfile.write(csv_file.read())

        # pandas needs a closed file for *read_csv*
        tmpfile.close()

        call_async(import_dataset, self, partial(
            csv_file_reader, tmpfile.name, na_values=na_values, delete=True))

        return self

    def import_from_json(self, json_file):
        """Impor data from a JSON file.

        :param json_file: JSON file to import.
        """
        content = json_file.file.read()
        call_async(import_dataset, self, partial(json_file_reader, content))

        return self

    def import_schema(self, schema):
        """Create a dataset from a SDF schema file (JSON).

        :param schema: The SDF (JSON) file to create a dataset from.

        :returns: The created dataset.
        """
        try:
            schema = json.loads(schema.file.read())
        except AttributeError:
            schema = json.loads(schema)

        self.set_schema(filter_schema(schema))
        self.ready()

        return self

########NEW FILE########
__FILENAME__ = schema_builder
from datetime import datetime
import numpy as np
import re

from bamboo.core.frame import RESERVED_KEYS
from bamboo.core.parser import Parser
from bamboo.lib.exceptions import ArgumentError
from bamboo.lib.mongo import reserve_encoded


CARDINALITY = 'cardinality'
OLAP_TYPE = 'olap_type'
SIMPLETYPE = 'simpletype'
LABEL = 'label'

# olap_types
DIMENSION = 'dimension'
MEASURE = 'measure'

# simpletypes
BOOLEAN = 'boolean'
DATETIME = 'datetime'
INTEGER = 'integer'
FLOAT = 'float'
STRING = 'string'

# map from numpy objects to olap_types
DTYPE_TO_OLAP_TYPE = {
    np.object_: DIMENSION,
    np.bool_: DIMENSION,
    np.float64: MEASURE,
    np.int64: MEASURE,
    datetime: MEASURE,
}

# map from numpy objects to simpletypes
DTYPE_TO_SIMPLETYPE = {
    np.bool_:   BOOLEAN,
    np.float64: FLOAT,
    np.int64:   INTEGER,
    np.object_: STRING,
    datetime: DATETIME,
}
SIMPLETYPE_TO_DTYPE = {
    FLOAT: np.float64,
    INTEGER: np.int64,
}
SIMPLETYPE_TO_OLAP_TYPE = {
    v: DTYPE_TO_OLAP_TYPE[k] for (k, v) in DTYPE_TO_SIMPLETYPE.items()}

RE_ENCODED_COLUMN = re.compile(ur'(?u)\W')


class Schema(dict):
    @classmethod
    def safe_init(cls, arg):
        """Make schema with potential arg of None."""
        return cls() if arg is None else cls(arg)

    @property
    def labels_to_slugs(self):
        """Build dict from column labels to slugs."""
        return {
            column_attrs[LABEL]: reserve_encoded(column_name) for
            (column_name, column_attrs) in self.items()
        }

    @property
    def numerics(self):
        return [slug for slug, col_schema in self.items()
                if col_schema[SIMPLETYPE] in [INTEGER, FLOAT]]

    @property
    def numerics_select(self):
        return {col: 1 for col in self.numerics}

    def cardinality(self, column):
        if self.is_dimension(column):
            return self[column].get(CARDINALITY)

    def convert_type(self, slug, value):
        column_schema = self.get(slug)
        if column_schema:
            type_func = SIMPLETYPE_TO_DTYPE.get(column_schema[SIMPLETYPE])
            if type_func:
                value = type_func(value)

        return value

    def datetimes(self, intersect_with):
        return [slug for slug, col in self.items()
                if col[SIMPLETYPE] == DATETIME and slug in intersect_with]

    def is_date_simpletype(self, column):
        return self[column][SIMPLETYPE] == DATETIME

    def is_dimension(self, column):
        col_schema = self.get(column)

        return col_schema and col_schema[OLAP_TYPE] == DIMENSION

    def rebuild(self, dframe, overwrite=False):
        """Rebuild a schema for a dframe.

        :param dframe: The DataFrame whose schema to merge with the current
            schema.
        :param overwrite: If true replace schema, otherwise update.
        """
        current_schema = self
        new_schema = schema_from_dframe(dframe, self)

        if current_schema and not overwrite:
            # merge new schema with existing schema
            current_schema.update(new_schema)
            new_schema = current_schema

        return new_schema

    def rename_map_for_dframe(self, dframe):
        """Return a map from dframe columns to slugs.

        :param dframe: The DataFrame to produce the map for.
        """
        labels_to_slugs = self.labels_to_slugs

        return {
            column: labels_to_slugs[column] for column in
            dframe.columns.tolist() if self._resluggable_column(
                column, labels_to_slugs, dframe)
        }

    def set_olap_type(self, column, olap_type):
        """Set the OLAP Type for this `column` of schema.

        Only columns with an original OLAP Type of 'measure' can be modified.
        This includes columns with Simple Type integer, float, and datetime.

        :param column: The column to set the OLAP Type for.
        :param olap_type: The OLAP Type to set. Must be 'dimension' or
            'measure'.
        :raises: `ArgumentError` if trying to set the OLAP Type of an column
          whose OLAP Type was not originally a 'measure'.
        """
        self[column][OLAP_TYPE] = olap_type

    def _resluggable_column(self, column, labels_to_slugs, dframe):
        """Test if column should be slugged.

        A column should be slugged if:
            1. The `column` is a key in `labels_to_slugs` and
            2. The `column` is not a value in `labels_to_slugs` or
                1. The `column` label is not equal to the `column` slug and
                2. The slug is not in the `dframe`'s columns

        :param column: The column to reslug.
        :param labels_to_slugs: The labels to slugs map (only build once).
        :param dframe: The DataFrame that column is in.
        """
        return (column in labels_to_slugs.keys() and (
                not column in labels_to_slugs.values() or (
                    labels_to_slugs[column] != column and
                    labels_to_slugs[column] not in dframe.columns)))


def schema_from_dframe(dframe, schema=None):
    """Build schema from the DataFrame and a schema.

    :param dframe: The DataFrame to build a schema for.
    :param schema: Existing schema, optional.

    :returns: A dictionary schema.
    """
    dtypes = dframe.dtypes.to_dict()

    column_names = list()
    names_to_labels = dict()

    # use existing labels for existing columns
    for name in dtypes.keys():
        if name not in RESERVED_KEYS:
            column_names.append(name)
            if schema:
                schema_for_name = schema.get(name)
                if schema_for_name:
                    names_to_labels[name] = schema_for_name[
                        LABEL]

    encoded_names = dict(zip(column_names, _slugify_columns(column_names)))
    schema = Schema()

    for (name, dtype) in dtypes.items():
        if name not in RESERVED_KEYS:
            column_schema = {
                LABEL: names_to_labels.get(name, name),
                OLAP_TYPE: _olap_type_for_data_and_dtype(
                    dframe[name], dtype),
                SIMPLETYPE: _simpletype_for_data_and_dtype(
                    dframe[name], dtype),
            }

            try:
                column_schema[CARDINALITY] = dframe[
                    name].nunique()
            except AttributeError:
                pass
            except TypeError:
                # E.g. dates with and without offset can not be compared and
                # raise a type error.
                pass

            schema[encoded_names[name]] = column_schema

    return schema


def _slugify_columns(column_names):
    """Convert list of strings into unique slugs.

    Convert non-alphanumeric characters in column names into underscores and
    ensure that all column names are unique.

    :param column_names: A list of strings.

    :returns: A list of slugified names with a one-to-one mapping to
        `column_names`.
    """

    encoded_names = []

    for column_name in column_names:
        slug = RE_ENCODED_COLUMN.sub('_', column_name).lower()
        slug = make_unique(slug, encoded_names + Parser.reserved_words)
        encoded_names.append(slug)

    return encoded_names


def make_unique(name, reserved_names):
    """Return a slug ensuring name is not in `reserved_names`.

    :param name: The name to make unique.
    :param reserved_names: A list of names the column must not be included in.
    """
    while name in reserved_names:
        name += '_'

    return name


def filter_schema(schema):
    """Remove not settable columns."""
    for column, column_schema in schema.iteritems():
        if column_schema.get(CARDINALITY):
            del column_schema[CARDINALITY]
            schema[column] = column_schema

    return schema


def _olap_type_for_data_and_dtype(column, dtype):
    return _type_for_data_and_dtypes(
        DTYPE_TO_OLAP_TYPE, column, dtype.type)


def _simpletype_for_data_and_dtype(column, dtype):
    return _type_for_data_and_dtypes(
        DTYPE_TO_SIMPLETYPE, column, dtype.type)


def _type_for_data_and_dtypes(type_map, column, dtype_type):
    has_datetime = any([isinstance(field, datetime) for field in column])

    return type_map[datetime if has_datetime else dtype_type]

########NEW FILE########
__FILENAME__ = utils
from itertools import chain
from math import isnan
from sys import maxint

import numpy as np


def flatten(list_):
    return [item for sublist in list_ for item in sublist]


def combine_dicts(*dicts):
    """Combine dicts with keys in later dicts taking precedence."""
    return dict(chain(*[_dict.iteritems() for _dict in dicts]))


def invert_dict(dict_):
    return {v: k for (k, v) in dict_.items()} if dict_ else {}


def is_float_nan(num):
    """Return True is `num` is a float and NaN."""
    return isinstance(num, float) and isnan(num)


def minint():
    return -maxint - 1


def parse_float(value, default=None):
    return _parse_type(np.float64, value, default)


def parse_int(value, default=None):
    return _parse_type(int, value, default)


def _parse_type(_type, value, default):
    try:
        return _type(value)
    except ValueError:
        return default


def replace_keys(original, mapping):
    """Recursively replace any keys in original with their values in mappnig.

    :param original: The dictionary to replace keys in.
    :param mapping: A dict mapping keys to new keys.

    :returns: Original with keys replaced via mapping.
    """
    return original if not type(original) in (dict, list) else {
        mapping.get(k, k): {
            dict: lambda: replace_keys(v, mapping),
            list: lambda: [replace_keys(vi, mapping) for vi in v]
        }.get(type(v), lambda: v)() for k, v in original.iteritems()}


def to_list(maybe_list):
    return maybe_list if isinstance(maybe_list, list) else [maybe_list]

########NEW FILE########
__FILENAME__ = version
from subprocess import check_output

# versioning
VERSION_MAJOR = 0.6
VERSION_MINOR = 3
VERSION_NUMBER = '%.1f.%d' % (VERSION_MAJOR, VERSION_MINOR)
VERSION_DESCRIPTION = 'alpha'


def safe_command_request(args):
    try:
        return check_output(args).strip()
    except:
        # might fail at least if git is not present
        # or if there's no git repository
        return ''


def get_version():
    return {'version': VERSION_NUMBER,
            'version_major': VERSION_MAJOR,
            'version_minor': VERSION_MINOR,
            'description': VERSION_DESCRIPTION,
            'branch': safe_command_request([
                'git', 'rev-parse', '--abbrev-ref', 'HEAD']),
            'commit': safe_command_request(['git', 'rev-parse', 'HEAD'])}

########NEW FILE########
__FILENAME__ = abstract_model
from bamboo.config.db import Database
from bamboo.core.frame import BAMBOO_RESERVED_KEYS
from bamboo.lib.decorators import classproperty
from bamboo.lib.mongo import dict_for_mongo, remove_mongo_reserved_keys


class AbstractModel(object):
    """An abstact class for all MongoDB models.

    Attributes:

    - __collection__: The MongoDB collection to communicate with.
    - STATE: A key with which to store state.
    - STATE_PENDING: A value for the pending state.
    - STATE_READY: A value for the ready state.

    """

    __collection__ = None
    __collectionname__ = None

    DB_READ_BATCH_SIZE = 1000
    DB_SAVE_BATCH_SIZE = 2000
    ERROR_MESSAGE = 'error_message'
    GROUP_DELIMITER = ','  # delimiter when passing multiple groups as a string
    MIN_BATCH_SIZE = 50
    STATE = 'state'
    STATE_FAILED = 'failed'
    STATE_PENDING = 'pending'
    STATE_READY = 'ready'

    @property
    def state(self):
        return self.record[self.STATE]

    @property
    def error_message(self):
        return self.record.get(self.ERROR_MESSAGE)

    @property
    def is_pending(self):
        return self.state == self.STATE_PENDING

    @property
    def is_ready(self):
        return self.state == self.STATE_READY

    @property
    def record_ready(self):
        return self.record is not None and self.state == self.STATE_READY

    @property
    def clean_record(self):
        """Remove reserved keys from records."""
        _dict = {
            key: value for (key, value) in self.record.items() if not key in
            BAMBOO_RESERVED_KEYS
        }
        return remove_mongo_reserved_keys(_dict)

    @classmethod
    def set_collection(cls, collection_name):
        """Return a MongoDB collection for the passed name.

        :param collection_name: The name of collection to return.

        :returns: A MongoDB collection from the current database.
        """
        return Database.db()[collection_name]

    @classproperty
    @classmethod
    def collection(cls):
        """Set the internal collection to the class' collection name."""
        if not cls.__collection__:
            cls.__collection__ = AbstractModel.set_collection(
                cls.__collectionname__)

        return cls.__collection__

    @classmethod
    def create(cls, *args):
        model = cls()
        return model.save(*args)

    @classmethod
    def find(cls, query_args, as_dict=False, as_cursor=False):
        """An interface to MongoDB's find functionality.

        :param query_args: An optional QueryArgs to hold the query arguments.
        :param as_cursor: If True, return the cursor.
        :param as_dict: If True, return dicts and not model instances.

        :returns: A list of dicts or model instances for each row returned.
        """
        cursor = cls.collection.find(query_args.query,
                                     query_args.select,
                                     sort=query_args.order_by,
                                     limit=query_args.limit)

        if as_cursor:
            return cursor
        else:
            return [record for record in cursor] if as_dict else [
                cls(record) for record in cursor
            ]

    @classmethod
    def find_one(cls, query, select=None, as_dict=False):
        """Return the first row matching `query` and `select` from MongoDB.

        :param query: A query to pass to MongoDB.
        :param select: An optional select to pass to MongoDB.
        :param as_dict: If true, return dicts and not model instances.

        :returns: A model instance of the row returned for this query and
            select.
        """
        record = cls.collection.find_one(query, select)

        return record if as_dict else cls(record)

    @classmethod
    def unset(cls, query, unset_query):
        """Call unset with the spec `query` the unset document `unset_query`.

        :param query: The spec restrict updates to.
        :param unset_query: The query to pass to unset.
        """
        cls.collection.update(query, {"$unset": unset_query}, multi=True)

    def __init__(self, record=None):
        """Instantiate with data in `record`."""
        self.record = record

    def __nonzero__(self):
        return self.record is not None

    def failed(self, message=None):
        """Perist the state of the current instance to `STATE_FAILED`.

        :params message: A string store as the error message, default None.
        """
        doc = {self.STATE: self.STATE_FAILED}

        if message:
            doc.update({self.ERROR_MESSAGE: message})

        self.update(doc)

    def pending(self):
        """Perist the state of the current instance to `STATE_PENDING`"""
        self.update({self.STATE: self.STATE_PENDING})

    def ready(self):
        """Perist the state of the current instance to `STATE_READY`"""
        self.update({self.STATE: self.STATE_READY})

    def delete(self, query):
        """Delete rows matching query.

        :param query: The query for rows to delete.
        """
        self.collection.remove(query)

    def save(self, record):
        """Save `record` in this model's collection.

        Save the record in the model instance's collection and set the internal
        record of this instance to the passed in record.

        :param record: The dict to save in the model's collection.

        :returns: The record passed in.
        """
        self.collection.insert(record)
        self.record = record

        return self

    def update(self, record):
        """Update the current instance with `record`.

        Update the current model instance based on its `_id`, set it to the
        passed in `record`.

        :param record: The record to replace the instance's data with.
        """
        record = dict_for_mongo(record)
        id_dict = {'_id': self.record['_id']}
        self.collection.update(id_dict, {'$set': record})

        # Set record to the latest record from the database
        self.record = self.__class__.collection.find_one(id_dict)

    def split_groups(self, groups):
        """Split a string based on the group delimiter"""
        return groups.split(self.GROUP_DELIMITER) if groups else []

    def join_groups(self, groups):
        return self.GROUP_DELIMITER.join(groups)

########NEW FILE########
__FILENAME__ = calculation
import traceback

from celery.task import Task, task

from bamboo.core.calculator import calculate_columns
from bamboo.core.frame import DATASET_ID
from bamboo.core.parser import Parser
from bamboo.lib.async import call_async
from bamboo.lib.exceptions import ArgumentError
from bamboo.lib.query_args import QueryArgs
from bamboo.lib.schema_builder import make_unique
from bamboo.lib.utils import to_list
from bamboo.models.abstract_model import AbstractModel


class CalculateTask(Task):
    def after_return(self, status, retval, task_id, args, kwargs, einfo=None):
        if status == 'FAILURE':
            calculations = args[0]

            for calculation in calculations:
                calculation.failed(traceback.format_exc())


class DependencyError(Exception):
    pass


class UniqueCalculationError(Exception):

    def __init__(self, name, current_names):
        current_names_str = '", "'.join(current_names)
        msg = ('The calculation name "%s" is not unique for this dataset. Plea'
               'se choose a name that does not exists.  The current names are:'
               '"%s"' % (name, current_names_str))

        Exception.__init__(self, msg)


@task(base=CalculateTask, default_retry_delay=5, max_retries=10,
      ignore_result=True)
def calculate_task(calculations, dataset):
    """Background task to run a calculation.

    Set calculation to failed and raise if an exception occurs.

    :param calculation: Calculation to run.
    :param dataset: Dataset to run calculation on.
    """
    # block until other calculations for this dataset are finished
    calculations[0].restart_if_has_pending(dataset, calculations[1:])

    calculate_columns(dataset.reload(), calculations)

    for calculation in calculations:
        calculation.add_dependencies(
            dataset, Parser.dependent_columns(calculation.formula, dataset))

        if calculation.aggregation is not None:
            aggregated_id = dataset.aggregated_datasets_dict[calculation.group]
            calculation.set_aggregation_id(aggregated_id)

        calculation.ready()


def _check_name_and_make_unique(name, dataset):
    """Check that the name is valid and make unique if valid.

    :param name: The name to make unique.
    :param dataset: The dataset to make unique for.
    :raises: `UniqueCalculationError` if not unique.
    :returns: A unique name.
    """
    current_names = dataset.labels

    if name in current_names:
        raise UniqueCalculationError(name, current_names)

    return make_unique(name, dataset.schema.keys())


@task(ignore_result=True)
def delete_task(calculation, dataset):
    """Background task to delete `calculation` and columns in its dataset.

    :param calculation: Calculation to delete.
    :param dataset: Dataset for this calculation.
    """
    slug = dataset.schema.labels_to_slugs.get(calculation.name)

    if slug:
        dataset.delete_columns(slug)
        dataset.clear_summary_stats(column=slug)

    calculation.remove_dependencies()

    super(calculation.__class__, calculation).delete({
        DATASET_ID: calculation.dataset_id,
        calculation.NAME: calculation.name})


class Calculation(AbstractModel):

    __collectionname__ = 'calculations'

    AGGREGATION = 'aggregation'
    AGGREGATION_ID = 'aggregation_id'
    DEPENDENCIES = 'dependencies'
    DEPENDENT_CALCULATIONS = 'dependent_calculations'
    FORMULA = 'formula'
    GROUP = 'group'
    NAME = 'name'

    @property
    def aggregation(self):
        return self.record[self.AGGREGATION]

    @property
    def aggregation_id(self):
        return self.record.get(self.AGGREGATION_ID)

    @property
    def dataset_id(self):
        return self.record[DATASET_ID]

    @property
    def dependencies(self):
        return self.record.get(self.DEPENDENCIES, [])

    @property
    def dependent_calculations(self):
        return self.record.get(self.DEPENDENT_CALCULATIONS, [])

    @property
    def formula(self):
        return self.record[self.FORMULA]

    @property
    def group(self):
        return self.record[self.GROUP]

    @property
    def groups_as_list(self):
        return self.split_groups(self.group)

    @property
    def name(self):
        return self.record[self.NAME]

    @classmethod
    def create(cls, dataset, formula, name, group=None):
        calculation = super(cls, cls).create(dataset, formula, name, group)
        call_async(calculate_task, [calculation], dataset.clear_cache())

        return calculation

    @classmethod
    def create_from_list_or_dict(cls, dataset, calculations):
        calculations = to_list(calculations)

        if not len(calculations) or not isinstance(calculations, list) or\
                any([not isinstance(e, dict) for e in calculations]):
            raise ArgumentError('Improper format for JSON calculations.')

        parsed_calculations = []

        # Pull out args to check JSON format
        try:
            for c in calculations:
                groups = c.get("groups")

                if not isinstance(groups, list):
                    groups = [groups]

                for group in groups:
                    parsed_calculations.append(
                        [c[cls.FORMULA], c[cls.NAME], group])
        except KeyError as e:
            raise ArgumentError('Required key %s not found in JSON' % e)

        # Save instead of create so that we calculate on all at once.
        calculations = [cls().save(dataset, formula, name, group)
                        for formula, name, group in parsed_calculations]
        call_async(calculate_task, calculations, dataset.clear_cache())

    @classmethod
    def find(cls, dataset, include_aggs=True, only_aggs=False):
        """Return the calculations for`dataset`.

        :param dataset: The dataset to retrieve the calculations for.
        :param include_aggs: Include aggregations, default True.
        :param only_aggs: Exclude non-aggregations, default False.
        """
        query = {DATASET_ID: dataset.dataset_id}

        if not include_aggs:
            query[cls.AGGREGATION] = None

        if only_aggs:
            query[cls.AGGREGATION] = {'$ne': None}

        query_args = QueryArgs(query=query, order_by='name')
        return super(cls, cls).find(query_args)

    @classmethod
    def find_one(cls, dataset_id, name, group=None):
        query = {DATASET_ID: dataset_id, cls.NAME: name}

        if group:
            query[cls.GROUP] = group

        return super(cls, cls).find_one(query)

    def add_dependencies(self, dataset, dependent_columns):
        """Store calculation dependencies."""
        calculations = dataset.calculations()
        names_to_calcs = {calc.name: calc for calc in calculations}

        for column_name in dependent_columns:
            calc = names_to_calcs.get(column_name)
            if calc:
                self.add_dependency(calc.name)
                calc.add_dependent_calculation(self.name)

    def add_dependency(self, name):
        self.__add_and_update_set(self.DEPENDENCIES, self.dependencies, name)

    def add_dependent_calculation(self, name):
        self.__add_and_update_set(self.DEPENDENT_CALCULATIONS,
                                  self.dependent_calculations, name)

    def delete(self, dataset):
        """Delete this calculation.

        First ensure that there are no other calculations which depend on this
        one. If not, start a background task to delete the calculation.

        :param dataset: Dataset for this calculation.

        :raises: `DependencyError` if dependent calculations exist.
        :raises: `ArgumentError` if group is not in DataSet or calculation does
            not exist for DataSet.
        """
        if len(self.dependent_calculations):
            msg = 'Cannot delete, calculations %s depend on this calculation.'
            raise DependencyError(msg % self.dependent_calculations)

        if not self.group is None:
            # it is an aggregate calculation
            dataset = dataset.aggregated_dataset(self.group)

            if not dataset:
                msg = 'Aggregation with group "%s" does not exist for dataset.'
                raise ArgumentError(msg % self.group)

        call_async(delete_task, self, dataset)

    def remove_dependent_calculation(self, name):
        new_dependent_calcs = self.dependent_calculations
        new_dependent_calcs.remove(name)
        self.update({self.DEPENDENT_CALCULATIONS: new_dependent_calcs})

    def remove_dependencies(self):
        for name in self.dependencies:
            calculation = self.find_one(self.dataset_id, name)
            calculation.remove_dependent_calculation(self.name)

    def restart_if_has_pending(self, dataset, current_calcs=[]):
        current_names = sorted([self.name] + [c.name for c in current_calcs])
        unfinished = [c for c in dataset.calculations() if c.is_pending]
        unfinished_names = [c.name for c in unfinished[:len(current_names)]]

        if len(unfinished) and current_names != sorted(unfinished_names):
            raise calculate_task.retry()

    def save(self, dataset, formula, name, group_str=None):
        """Parse, save, and calculate a formula.

        Validate `formula` and `group_str` for the given `dataset`. If the
        formula and group are valid for the dataset, then save a new
        calculation for them under `name`. Finally, create a background task
        to compute the calculation.

        Calculations are initially saved in a **pending** state, after the
        calculation has finished processing it will be in a **ready** state.

        :param dataset: The DataSet to save.
        :param formula: The formula to save.
        :param name: The name of the formula.
        :param group_str: Columns to group on.
        :type group_str: String, list or strings, or None.

        :raises: `ParseError` if an invalid formula was supplied.
        """
        # ensure that the formula is parsable
        groups = self.split_groups(group_str) if group_str else []
        Parser.validate(dataset, formula, groups)
        aggregation = Parser.parse_aggregation(formula)

        if aggregation:
            # set group if aggregation and group unset
            group_str = group_str or ''

            # check that name is unique for aggregation
            aggregated_dataset = dataset.aggregated_dataset(groups)

            if aggregated_dataset:
                name = _check_name_and_make_unique(name, aggregated_dataset)

        else:
            # set group if aggregation and group unset
            name = _check_name_and_make_unique(name, dataset)

        record = {
            DATASET_ID: dataset.dataset_id,
            self.AGGREGATION: aggregation,
            self.FORMULA: formula,
            self.GROUP: group_str,
            self.NAME: name,
            self.STATE: self.STATE_PENDING,
        }
        super(self.__class__, self).save(record)

        return self

    def set_aggregation_id(self, _id):
        self.update({self.AGGREGATION_ID: _id})

    def __add_and_update_set(self, link_key, existing, new):
        new_list = list(set(existing + [new]))

        if new_list != existing:
            self.update({link_key: new_list})

########NEW FILE########
__FILENAME__ = dataset
import re
import uuid
from time import gmtime, strftime

from celery.task import task
from pandas import DataFrame, rolling_window

from bamboo.core.calculator import calculate_updates, dframe_from_update,\
    propagate
from bamboo.core.frame import BAMBOO_RESERVED_KEY_PREFIX,\
    DATASET_ID, INDEX, join_dataset, PARENT_DATASET_ID, remove_reserved_keys
from bamboo.core.summary import summarize
from bamboo.lib.async import call_async
from bamboo.lib.exceptions import ArgumentError
from bamboo.lib.mongo import df_mongo_decode
from bamboo.lib.readers import ImportableDataset
from bamboo.lib.query_args import QueryArgs
from bamboo.lib.schema_builder import Schema
from bamboo.lib.utils import combine_dicts, to_list
from bamboo.models.abstract_model import AbstractModel
from bamboo.models.calculation import Calculation
from bamboo.models.observation import Observation

# The format pandas encodes multicolumns in.
strip_pattern = re.compile("\(u'|', u'|'\)")


@task(ignore_result=True)
def delete_task(dataset, query=None):
    """Background task to delete dataset and its associated observations."""
    Observation.delete_all(dataset, query=query)

    if query is None:
        super(dataset.__class__, dataset).delete(
            {DATASET_ID: dataset.dataset_id})
        Observation.delete_encoding(dataset)


class Dataset(AbstractModel, ImportableDataset):

    __collectionname__ = 'datasets'

    # caching keys
    STATS = '_stats'
    ALL = '_all'

    # metadata
    AGGREGATED_DATASETS = BAMBOO_RESERVED_KEY_PREFIX + 'linked_datasets'
    ATTRIBUTION = 'attribution'
    CREATED_AT = 'created_at'
    DESCRIPTION = 'description'
    ID = 'id'
    JOINED_DATASETS = 'joined_datasets'
    LABEL = 'label'
    LICENSE = 'license'
    NUM_COLUMNS = 'num_columns'
    NUM_ROWS = 'num_rows'
    MERGED_DATASETS = 'merged_datasets'
    PARENT_IDS = 'parent_ids'
    PENDING_UPDATES = 'pending_updates'
    SCHEMA = 'schema'
    UPDATED_AT = 'updated_at'

    def __init__(self, record=None):
        super(Dataset, self).__init__(record)
        self.__dframe = None

    @property
    def aggregated_datasets(self):
        return [(self.split_groups(group), self.find_one(_id)) for (
            group, _id) in self.aggregated_datasets_dict.items()]

    @property
    def aggregated_datasets_dict(self):
        return self.record.get(self.AGGREGATED_DATASETS, {})

    @property
    def attribution(self):
        return self.record.get(self.ATTRIBUTION)

    @property
    def columns(self):
        return self.schema.keys() if self.num_rows else []

    @property
    def dataset_id(self):
        return self.record[DATASET_ID]

    @property
    def description(self):
        return self.record.get(self.DESCRIPTION)

    @property
    def joined_datasets(self):
        # TODO: fetch all datasets in single DB call
        # (let Dataset.find take a list of IDs)
        return [
            (direction, self.find_one(other_dataset_id), on,
             self.find_one(joined_dataset_id))
            for direction, other_dataset_id, on, joined_dataset_id in
            self.joined_dataset_ids]

    @property
    def joined_dataset_ids(self):
        return [
            tuple(_list) for _list in self.record.get(self.JOINED_DATASETS, [])
        ]

    @property
    def label(self):
        return self.record.get(self.LABEL)

    @property
    def labels(self):
        return [column[self.LABEL] for column in self.schema.values()]

    @property
    def license(self):
        return self.record.get(self.LICENSE)

    @property
    def merged_datasets(self):
        return self.__linked_datasets(self.merged_dataset_ids)

    @property
    def merged_datasets_with_map(self):
        results = self.merged_dataset_info

        if len(results):
            mappings, ids = zip(*results)
            results = zip(mappings, self.__linked_datasets(ids))

        return results

    @property
    def merged_dataset_ids(self):
        results = self.merged_dataset_info
        return zip(*results)[-1] if results else results

    @property
    def merged_dataset_info(self):
        return self.record.get(self.MERGED_DATASETS, [])

    @property
    def num_columns(self):
        return self.record.get(self.NUM_COLUMNS, 0)

    @property
    def num_rows(self):
        return self.record.get(self.NUM_ROWS, 0)

    @property
    def on_columns_for_rhs_of_joins(self):
        return [on for direction, _, on, __ in
                self.joined_datasets if direction == 'left']

    @property
    def parent_ids(self):
        query_args = QueryArgs(select={PARENT_DATASET_ID: 1},
                               distinct=PARENT_DATASET_ID)
        return self.observations(query_args)

    @property
    def pending_updates(self):
        return self.record[self.PENDING_UPDATES]

    @property
    def schema(self):
        schema_dict = {}

        if self.record:
            schema_dict = self.record.get(self.SCHEMA)

        return Schema.safe_init(schema_dict)

    @property
    def stats(self):
        return self.record.get(self.STATS, {})

    @property
    def updatable_keys(self):
        return [self.LABEL, self.DESCRIPTION, self.LICENSE, self.ATTRIBUTION]

    @property
    def __is_cached(self):
        return self.__dframe is not None

    @classmethod
    def create(cls, dataset_id=None):
        return super(cls, cls).create(dataset_id)

    @classmethod
    def find(cls, dataset_id):
        """Return datasets for `dataset_id`."""
        query_args = QueryArgs(query={DATASET_ID: dataset_id})
        return super(cls, cls).find(query_args)

    @classmethod
    def find_one(cls, dataset_id):
        """Return dataset for `dataset_id`."""
        return super(cls, cls).find_one({DATASET_ID: dataset_id})

    def __linked_datasets(self, ids):
        return [self.find_one(_id) for _id in ids]

    def add_joined_dataset(self, new_data):
        """Add the ID of `new_dataset` to the list of joined datasets."""
        self.__add_linked_data(self.JOINED_DATASETS, self.joined_dataset_ids,
                               new_data)

    def add_merged_dataset(self, mapping, new_dataset):
        """Add the ID of `new_dataset` to the list of merged datasets."""
        self.__add_linked_data(self.MERGED_DATASETS, self.merged_dataset_info,
                               [mapping, new_dataset.dataset_id])

    def add_observations(self, new_data):
        """Update `dataset` with `new_data`."""
        update_id = uuid.uuid4().hex
        self.add_pending_update(update_id)

        new_data = to_list(new_data)

        # fetch data before other updates
        new_dframe_raw = dframe_from_update(self, new_data)

        call_async(calculate_updates, self, new_data,
                   new_dframe_raw=new_dframe_raw, update_id=update_id)

    def add_pending_update(self, update_id):
        self.collection.update(
            {'_id': self.record['_id']},
            {'$push': {self.PENDING_UPDATES: update_id}})

    def aggregated_dataset(self, groups):
        groups = to_list(groups)
        _id = self.aggregated_datasets_dict.get(self.join_groups(groups))

        return self.find_one(_id) if _id else None

    def append_observations(self, dframe):
        Observation.append(dframe, self)
        self.update({self.NUM_ROWS: self.num_rows + len(dframe)})

        # to update cardinalities here we need to refetch the full DataFrame.
        dframe = self.dframe(keep_parent_ids=True)
        self.build_schema(dframe)
        self.update_stats(dframe)

    def build_schema(self, dframe, overwrite=False, set_num_columns=True):
        """Build schema for a dataset.

        If no schema exists, build a schema from the passed `dframe` and store
        that schema for this dataset.  Otherwise, if a schema does exist, build
        a schema for the passed `dframe` and merge this schema with the current
        schema.  Keys in the new schema replace keys in the current schema but
        keys in the current schema not in the new schema are retained.

        If `set_num_columns` is True the number of columns will be set to the
        number of keys (columns) in the new schema.

        :param dframe: The DataFrame whose schema to merge with the current
            schema.
        :param overwrite: If true replace schema, otherwise update.
        :param set_num_columns: If True also set the number of columns.
        """
        new_schema = self.schema.rebuild(dframe, overwrite)
        self.set_schema(new_schema,
                        set_num_columns=(set_num_columns or overwrite))

    def calculations(self, include_aggs=True, only_aggs=False):
        """Return the calculations for this dataset.

        :param include_aggs: Include aggregations, default True.
        :param only_aggs: Exclude non-aggregations, default False.
        """
        return Calculation.find(self, include_aggs, only_aggs)

    def cardinality(self, col):
        return self.schema.cardinality(col)

    def clear_cache(self):
        self.__dframe = None

        return self

    def clear_pending_updates(self):
        self.collection.update(
            {'_id': self.record['_id']},
            {'$set': {self.PENDING_UPDATES: []}})

    def clear_summary_stats(self, group=None, column=None):
        """Remove summary stats for `group` and optional `column`.

        By default will remove all stats.

        :param group: The group to remove stats for, default None.
        :param column: The column to remove stats for, default None.
        """
        stats = self.stats

        if stats:
            if column:
                stats_for_field = stats.get(group or self.ALL)

                if stats_for_field:
                    stats_for_field.pop(column, None)
            elif group:
                stats.pop(group, None)
            else:
                stats = {}

            self.update({self.STATS: stats})

    def count(self, query_args=None):
        """Return the count of rows matching query in dataset.

        :param query_args: An optional QueryArgs to hold the query arguments.
        """
        query_args = query_args or QueryArgs()
        obs = self.observations(query_args, as_cursor=True)

        count = len(obs) if query_args.distinct else obs.count()

        limit = query_args.limit
        if limit > 0 and count > limit:
            count = limit

        return count

    def delete(self, query=None, countdown=0):
        """Delete this dataset.

        :param countdown: Delete dataset after this number of seconds.
        """
        call_async(delete_task, self.clear_cache(), query=query,
                   countdown=countdown)

    def delete_columns(self, columns):
        """Delete column `column` from this dataset.

        :param column: The column to delete.
        """
        columns = set(self.schema.keys()).intersection(set(to_list(columns)))

        if not len(columns):
            raise ArgumentError("Columns: %s not in dataset.")

        Observation.delete_columns(self, columns)
        new_schema = self.schema

        [new_schema.pop(c) for c in columns]

        self.set_schema(new_schema, set_num_columns=True)

        return columns

    def delete_observation(self, index):
        """Delete observation at index.

        :params index: The index of an observation to delete.
        """
        Observation.delete(self, index)

        dframe = self.dframe()
        self.update({self.NUM_ROWS: len(dframe)})
        self.build_schema(dframe, overwrite=True)
        call_async(propagate, self, update={'delete': index})

    def dframe(self, query_args=None, keep_parent_ids=False, padded=False,
               index=False, reload_=False, keep_mongo_keys=False):
        """Fetch the dframe for this dataset.

        :param query_args: An optional QueryArgs to hold the query arguments.
        :param keep_parent_ids: Do not remove parent IDs from the dframe,
            default False.
        :param padded: Used for joining, default False.
        :param index: Return the index with dframe, default False.
        :param reload_: Force refresh of data, default False.
        :param keep_mongo_keys: Used for updating documents, default False.

        :returns: Return DataFrame with contents based on query parameters
            passed to MongoDB. DataFrame will not have parent ids if
            `keep_parent_ids` is False.
        """
        # bypass cache if we need specific version
        cacheable = not (query_args or keep_parent_ids or padded)

        # use cached copy if we have already fetched it
        if cacheable and not reload_ and self.__is_cached:
            return self.__dframe

        query_args = query_args or QueryArgs()
        observations = self.observations(query_args, as_cursor=True)

        if query_args.distinct:
            return DataFrame(observations)

        dframe = Observation.batch_read_dframe_from_cursor(
            self, observations, query_args.distinct, query_args.limit)

        dframe = df_mongo_decode(dframe, keep_mongo_keys=keep_mongo_keys)

        excluded = [keep_parent_ids and PARENT_DATASET_ID, index and INDEX]
        dframe = remove_reserved_keys(dframe, filter(bool, excluded))

        if index:
            dframe.rename(columns={INDEX: 'index'}, inplace=True)

        dframe = self.__maybe_pad(dframe, padded)

        if cacheable:
            self.__dframe = dframe

        return dframe

    def has_pending_updates(self, update_id):
        """Check if this dataset has pending updates.

        Call the update identfied by `update_id` the current update. A dataset
        has pending updates if, not including the current update, there are any
        pending updates and the update at the top of the queue is not the
        current update.

        :param update_id: An update to exclude when checking for pending
            updates.
        :returns: True if there are pending updates, False otherwise.
        """
        self.reload()
        pending_updates = self.pending_updates

        return pending_updates[0] != update_id and len(
            set(pending_updates) - set([update_id]))

    def info(self, update=None):
        """Return or update meta-data for this dataset.

        :param update: Dictionary to update info with, default None.
        :returns: Dictionary of info for this dataset.
        """
        if update:
            update_dict = {key: value for key, value in update.items()
                           if key in self.updatable_keys}
            self.update(update_dict)

        return {
            self.ID: self.dataset_id,
            self.LABEL: self.label,
            self.DESCRIPTION: self.description,
            self.SCHEMA: self.schema,
            self.LICENSE: self.license,
            self.ATTRIBUTION: self.attribution,
            self.CREATED_AT: self.record.get(self.CREATED_AT),
            self.UPDATED_AT: self.record.get(self.UPDATED_AT),
            self.NUM_COLUMNS: self.num_columns,
            self.NUM_ROWS: self.num_rows,
            self.STATE: self.state,
            self.PARENT_IDS: self.parent_ids,
            self.PENDING_UPDATES: self.pending_updates,
        }

    def is_dimension(self, col):
        return self.schema.is_dimension(col)

    def is_factor(self, col):
        return self.is_dimension(col) or self.schema.is_date_simpletype(col)

    def join(self, other, on):
        """Join with dataset `other` on the passed columns.

        :param other: The other dataset to join.
        :param on: The column in this and the `other` dataset to join on.
        """
        merged_dframe = self.dframe()

        if not len(merged_dframe.columns):
            # Empty dataset, simulate columns
            merged_dframe = self.place_holder_dframe()

        merged_dframe = join_dataset(merged_dframe, other, on)
        merged_dataset = self.create()

        if self.num_rows and other.num_rows:
            merged_dataset.save_observations(merged_dframe)
        else:
            merged_dataset.build_schema(merged_dframe, set_num_columns=True)
            merged_dataset.ready()

        self.add_joined_dataset(
            ('right', other.dataset_id, on, merged_dataset.dataset_id))
        other.add_joined_dataset(
            ('left', self.dataset_id, on, merged_dataset.dataset_id))

        return merged_dataset

    def observations(self, query_args=None, as_cursor=False):
        """Return observations for this dataset.

        :param query_args: An optional QueryArgs to hold the query arguments.
        :param as_cursor: Return the observations as a cursor.
        """
        return Observation.find(self, query_args or QueryArgs(),
                                as_cursor=as_cursor)

    def place_holder_dframe(self, dframe=None):
        columns = self.schema.keys()

        if dframe is not None:
            columns = [c for c in columns if c not in dframe.columns[1:]]

        return DataFrame([[''] * len(columns)], columns=columns)

    def reload(self):
        """Reload the dataset from DB and clear any cache."""
        dataset = Dataset.find_one(self.dataset_id)
        self.record = dataset.record
        self.clear_cache()

        return self

    def remove_parent_observations(self, parent_id):
        """Remove obervations for this dataset with the passed `parent_id`.

        :param parent_id: Remove observations with this ID as their parent
            dataset ID.
        """
        Observation.delete_all(self, {PARENT_DATASET_ID: parent_id})
        # clear the cached dframe
        self.__dframe = None

    def remove_pending_update(self, update_id):
        self.collection.update(
            {'_id': self.record['_id']},
            {'$pull': {self.PENDING_UPDATES: update_id}})

    def replace_observations(self, dframe, overwrite=False,
                             set_num_columns=True):
        """Remove all rows for this dataset and save the rows in `dframe`.

        :param dframe: Replace rows in this dataset with this DataFrame's rows.
        :param overwrite: If true replace the schema, otherwise update it.
            Default False.
        :param set_num_columns: If true update the dataset stored number of
            columns.  Default True.

        :returns: DataFrame equivalent to the passed in `dframe`.
        """
        self.build_schema(dframe, overwrite=overwrite,
                          set_num_columns=set_num_columns)
        Observation.delete_all(self)

        return self.save_observations(dframe)

    def resample(self, date_column, interval, how, query=None):
        """Resample a dataset given a new time frame.

        :param date_column: The date column use as the index for resampling.
        :param interval: The interval code for resampling.
        :param how: How to aggregate in the resample.
        :returns: A DataFrame of the resampled DataFrame for this dataset.
        """
        query_args = QueryArgs(query=query)
        dframe = self.dframe(query_args).set_index(date_column)
        resampled = dframe.resample(interval, how=how)
        return resampled.reset_index()

    def rolling(self, win_type, window):
        """Calculate a rolling window over all numeric columns.

        :param win_type: The type of window, see pandas pandas.rolling_window.
        :param window: The number of observations used for calculating the
            window.
        :returns: A DataFrame of the rolling window calculated for this
            dataset.
        """
        dframe = self.dframe(QueryArgs(select=self.schema.numerics_select))
        return rolling_window(dframe, window, win_type)

    def save(self, dataset_id=None):
        """Store dataset with `dataset_id` as the unique internal ID.

        Store a new dataset with an ID given by `dataset_id` is exists,
        otherwise reate a random UUID for this dataset. Additionally, set the
        created at time to the current time and the state to pending.

        :param dataset_id: The ID to store for this dataset, default is None.

        :returns: A dict representing this dataset.
        """
        if dataset_id is None:
            dataset_id = uuid.uuid4().hex

        record = {
            DATASET_ID: dataset_id,
            self.AGGREGATED_DATASETS: {},
            self.CREATED_AT: strftime("%Y-%m-%d %H:%M:%S", gmtime()),
            self.STATE: self.STATE_PENDING,
            self.PENDING_UPDATES: [],
        }

        return super(self.__class__, self).save(record)

    def save_observations(self, dframe):
        """Save rows in `dframe` for this dataset.

        :param dframe: DataFrame to save rows from.
        """
        return Observation.save(dframe, self)

    def set_olap_type(self, column, olap_type):
        """Set the OLAP Type for this `column` of dataset.

        Only columns with an original OLAP Type of 'measure' can be modified.
        This includes columns with Simple Type integer, float, and datetime.

        :param column: The column to set the OLAP Type for.
        :param olap_type: The OLAP Type to set. Must be 'dimension' or
            'measure'.
        """
        schema = self.schema
        schema.set_olap_type(column, olap_type)

        self.set_schema(schema, False)

        # Build summary for new type.
        self.summarize(self.dframe(), update=True)

    def set_schema(self, schema, set_num_columns=True):
        """Set the schema from an existing one."""
        update_dict = {self.SCHEMA: schema}

        if set_num_columns:
            update_dict.update({self.NUM_COLUMNS: len(schema.keys())})

        self.update(update_dict)

    def summarize(self, dframe, groups=[], no_cache=False, update=False,
                  flat=False):
        """Build and return a summary of the data in this dataset.

        Return a summary of dframe grouped by `groups`, or the overall
        summary if no groups are specified.

        :param dframe: dframe to summarize
        :param groups: A list of columns to group on.
        :param no_cache: Do not fetch a cached summary.
        :param flat: Return a flattened list of groups.

        :returns: A summary of the dataset as a dict. Numeric columns will be
            summarized by the arithmetic mean, standard deviation, and
            percentiles. Dimensional columns will be summarized by counts.
        """
        self.reload()

        summary = summarize(self, dframe, groups, no_cache, update=update)

        if flat:
            flat_summary = []

            for cols, v in summary.iteritems():
                cols = self.split_groups(cols)

                for k, data in v.iteritems():
                    col_values = self.split_groups(k)
                    col_values = [strip_pattern.sub(',', i)[1:-1]
                                  for i in col_values]
                    flat_summary.append(
                        combine_dicts(dict(zip(cols, col_values)), data))

            summary = flat_summary

        return summary

    def update(self, record):
        """Update dataset `dataset` with `record`."""
        record[self.UPDATED_AT] = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        super(self.__class__, self).update(record)

    def update_observation(self, index, data):
        # check that update is valid
        dframe_from_update(self, [data])
        Observation.update(self, index, data)
        call_async(propagate, self, update={'edit': [index, data]})

    def update_observations(self, dframe):
        return Observation.update_from_dframe(dframe, self)

    def update_complete(self, update_id):
        """Remove `update_id` from this datasets list of pending updates.

        :param update_id: The ID of the completed update.
        """
        self.collection.update(
            {'_id': self.record['_id']},
            {'$pull': {self.PENDING_UPDATES: update_id}})

    def update_stats(self, dframe, update=False):
        """Update store statistics for this dataset.

         :param dframe: Use this DataFrame for summary statistics.
         :param update: Update or replace summary statistics, default False.
        """
        self.update({
            self.NUM_ROWS: len(dframe),
            self.STATE: self.STATE_READY,
        })
        self.summarize(dframe, update=update)

    def __add_linked_data(self, link_key, existing_data, new_data):
        self.update({link_key: existing_data + [new_data]})

    def __maybe_pad(self, dframe, pad):
        if pad:
            if len(dframe.columns):
                on = dframe.columns[0]
                place_holder = self.place_holder_dframe(dframe).set_index(on)
                dframe = dframe.join(place_holder, on=on)
            else:
                dframe = self.place_holder_dframe()

        return dframe

########NEW FILE########
__FILENAME__ = observation
from math import ceil
from pandas import concat, DataFrame
from pymongo.errors import AutoReconnect

from bamboo.core.frame import add_id_column, DATASET_ID, INDEX
from bamboo.lib.datetools import now, parse_timestamp_query
from bamboo.lib.mongo import MONGO_ID, MONGO_ID_ENCODED
from bamboo.lib.parsing import parse_columns
from bamboo.lib.query_args import QueryArgs
from bamboo.lib.utils import combine_dicts, invert_dict, replace_keys
from bamboo.models.abstract_model import AbstractModel


def add_index(df):
    """Add an encoded index to this DataFrame."""
    if not INDEX in df.columns:
        # No index, create index for this dframe.
        if not 'index' in df.columns:
            # Custom index not supplied, use pandas default index.
            df.reset_index(inplace=True)

        df.rename(columns={'index': INDEX}, inplace=True)

    return df


def encode(dframe, dataset, append_index=True):
    """Encode the columns for `dataset` to slugs and add ID column.

    The ID column is the dataset_id for dataset.  This is
    used to link observations to a specific dataset.

    :param dframe: The DataFrame to encode.
    :param dataset: The Dataset to use a mapping for.
    :param append_index: Add index to the DataFrame, default True.

    :returns: A modified `dframe`.
    """
    if append_index:
        dframe = add_index(dframe)

    dframe = add_id_column(dframe, dataset.dataset_id)
    encoded_columns_map = dataset.schema.rename_map_for_dframe(dframe)

    return dframe.rename(columns=encoded_columns_map)


def update_calculations(record, dataset):
    calculations = dataset.calculations(include_aggs=False)

    if len(calculations):
        dframe = DataFrame(data=record, index=[0])
        labels_to_slugs = dataset.schema.labels_to_slugs

        for c in calculations:
            columns = parse_columns(dataset, c.formula, c.name, dframe=dframe)
            record[labels_to_slugs[c.name]] = columns[0][0]

    return record


class Observation(AbstractModel):

    __collectionname__ = 'observations'

    DELETED_AT = '-1'  # use a short code for key
    ENCODING = 'enc'
    ENCODING_DATASET_ID = '%s_%s' % (DATASET_ID, ENCODING)

    @classmethod
    def delete(cls, dataset, index):
        """Delete observation at index for dataset.

        :param dataset: The dataset to delete the observation from.
        :param index: The index of the observation to delete.
        """
        query = {INDEX: index, DATASET_ID: dataset.dataset_id}
        query = cls.encode(query, dataset=dataset)

        cls.__soft_delete(query)

    @classmethod
    def delete_all(cls, dataset, query=None):
        """Delete the observations for `dataset`.

        :param dataset: The dataset to delete observations for.
        :param query: An optional query to restrict deletion.
        """
        query = query or {}
        query.update({DATASET_ID: dataset.dataset_id})
        query = cls.encode(query, dataset=dataset)

        super(cls, cls()).delete(query)

    @classmethod
    def delete_columns(cls, dataset, columns):
        """Delete a column from the dataset."""
        encoding = cls.encoding(dataset)

        cls.unset({cls.ENCODING_DATASET_ID: dataset.dataset_id},
                  {"%s.%s" % (cls.ENCODING, c): 1 for c in columns})

        cls.unset(
            cls.encode({DATASET_ID: dataset.dataset_id}, encoding=encoding),
            cls.encode({c: 1 for c in columns}, encoding=encoding))

    @classmethod
    def delete_encoding(cls, dataset):
        query = {cls.ENCODING_DATASET_ID: dataset.dataset_id}

        super(cls, cls()).delete(query)

    @classmethod
    def encoding(cls, dataset, encoded_dframe=None):
        record = super(cls, cls).find_one({
            cls.ENCODING_DATASET_ID: dataset.dataset_id}).record

        if record is None and encoded_dframe is not None:
            encoding = cls.__make_encoding(encoded_dframe)
            cls.__store_encoding(dataset, encoding)

            return cls.encoding(dataset)

        return record[cls.ENCODING] if record else None

    @classmethod
    def encode(cls, dict_, dataset=None, encoding=None):
        if dataset:
            encoding = cls.encoding(dataset)

        return replace_keys(dict_, encoding) if encoding else dict_

    @classmethod
    def decoding(cls, dataset):
        return invert_dict(cls.encoding(dataset))

    @classmethod
    def find(cls, dataset, query_args=None, as_cursor=False,
             include_deleted=False):
        """Return observation rows matching parameters.

        :param dataset: Dataset to return rows for.
        :param include_deleted: If True, return delete records, default False.
        :param query_args: An optional QueryArgs to hold the query arguments.

        :raises: `JSONError` if the query could not be parsed.

        :returns: A list of dictionaries matching the passed in `query` and
            other parameters.
        """
        encoding = cls.encoding(dataset) or {}
        query_args = query_args or QueryArgs()

        query_args.query = parse_timestamp_query(query_args.query,
                                                 dataset.schema)
        query_args.encode(encoding, {DATASET_ID: dataset.dataset_id})

        if not include_deleted:
            query = query_args.query
            query[cls.DELETED_AT] = 0
            query_args.query = query

        # exclude deleted at column
        query_args.select = query_args.select or {cls.DELETED_AT: 0}

        distinct = query_args.distinct
        records = super(cls, cls).find(query_args, as_dict=True,
                                       as_cursor=(as_cursor or distinct))

        return records.distinct(encoding.get(distinct, distinct)) if distinct\
            else records

    @classmethod
    def update_from_dframe(cls, df, dataset):
        dataset.build_schema(df)
        encoded_dframe = encode(df.reset_index(), dataset, append_index=False)
        encoding = cls.encoding(dataset)

        cls.__batch_update(encoded_dframe, encoding)
        cls.__store_encoding(dataset, encoding)
        dataset.update_stats(df, update=True)

    @classmethod
    def find_one(cls, dataset, index, decode=True):
        """Return row by index.

        :param dataset: The dataset to find the row for.
        :param index: The index of the row to find.
        """
        query = {INDEX: index, DATASET_ID: dataset.dataset_id,
                 cls.DELETED_AT: 0}
        query = cls.encode(query, dataset=dataset)
        decoding = cls.decoding(dataset)
        record = super(cls, cls).find_one(query, as_dict=True)

        return cls(cls.encode(record, encoding=decoding) if decode else record)

    @classmethod
    def append(cls, dframe, dataset):
        """Append an additional dframe to an existing dataset.

        :params dframe: The DataFrame to append.
        :params dataset: The DataSet to add `dframe` to.
        """
        encoded_dframe = encode(dframe, dataset)
        encoding = cls.encoding(dataset, encoded_dframe)

        cls.__batch_save(encoded_dframe, encoding)
        dataset.clear_summary_stats()

    @classmethod
    def save(cls, dframe, dataset):
        """Save data in `dframe` with the `dataset`.

        Encode `dframe` for MongoDB, and add fields to identify it with the
        passed in `dataset`. All column names in `dframe` are converted to
        slugs using the dataset's schema.  The dataset is update to store the
        size of the stored data.

        :param dframe: The DataFrame to store.
        :param dataset: The dataset to store the dframe in.
        """
        # Build schema for the dataset after having read it from file.
        if not dataset.schema:
            dataset.build_schema(dframe)

        # Update stats, before inplace encoding.
        dataset.update_stats(dframe)

        encoded_dframe = encode(dframe, dataset)
        encoding = cls.encoding(dataset, encoded_dframe)

        cls.__batch_save(encoded_dframe, encoding)

    @classmethod
    def update(cls, dataset, index, record):
        """Update a dataset row by index.

        The record dictionary will update, not replace, the data in the row at
        index.

        :param dataset: The dataset to update a row for.
        :param dex: The index of the row to update.
        :param record: The dictionary to update the row with.
        """
        previous_record = cls.find_one(dataset, index).record
        previous_record.pop(MONGO_ID)
        record = combine_dicts(previous_record, record)
        record = update_calculations(record, dataset)

        record = cls.encode(record, dataset=dataset)

        cls.delete(dataset, index)

        super(cls, cls()).save(record)

    @classmethod
    def batch_read_dframe_from_cursor(cls, dataset, observations, distinct,
                                      limit):
        """Read a DataFrame from a MongoDB Cursor in batches."""
        dframes = []
        batch = 0
        decoding = cls.decoding(dataset)

        while True:
            start = batch * cls.DB_READ_BATCH_SIZE
            end = start + cls.DB_READ_BATCH_SIZE

            if limit > 0 and end > limit:
                end = limit

            # if there is a limit this may occur, and we are done
            if start >= end:
                break

            current_observations = [
                replace_keys(ob, decoding) for ob in observations[start:end]]

            # if the batches exhausted the data
            if not len(current_observations):
                break

            dframes.append(DataFrame(current_observations))

            if not distinct:
                observations.rewind()

            batch += 1

        return concat(dframes) if len(dframes) else DataFrame()

    @classmethod
    def __batch_save(cls, dframe, encoding):
        """Save records in batches to avoid document size maximum setting.

        :param dframe: A DataFrame to save in the current model.
        """
        def command(records, encoding):
            cls.collection.insert(records)

        batch_size = cls.DB_SAVE_BATCH_SIZE

        cls.__batch_command_wrapper(command, dframe, encoding, batch_size)

    @classmethod
    def __batch_update(cls, dframe, encoding):
        """Update records in batches to avoid document size maximum setting.

        DataFrame must have column with record (object) ids.

        :param dfarme: The DataFrame to update.
        """
        def command(records, encoding):
            # Encode the reserved key to access the row ID.
            mongo_id_key = encoding.get(MONGO_ID_ENCODED, MONGO_ID_ENCODED)

            # MongoDB has no batch updates.
            for record in records:
                spec = {MONGO_ID: record[mongo_id_key]}
                del record[mongo_id_key]
                doc = {'$set': record}
                cls.collection.update(spec, doc)

        cls.__batch_command_wrapper(command, dframe, encoding,
                                    cls.DB_SAVE_BATCH_SIZE)

    @classmethod
    def __batch_command_wrapper(cls, command, df, encoding, batch_size):
        try:
            cls.__batch_command(command, df, encoding, batch_size)
        except AutoReconnect:
            batch_size /= 2

            # If batch size drop is less than MIN_BATCH_SIZE, assume the
            # records are too large or there is another error and fail.
            if batch_size >= cls.MIN_BATCH_SIZE:
                cls.__batch_command_wrapper(command, df, encoding, batch_size)

    @classmethod
    def __batch_command(cls, command, dframe, encoding, batch_size):
        batches = int(ceil(float(len(dframe)) / batch_size))

        for batch in xrange(0, batches):
            start = batch * batch_size
            end = start + batch_size
            current_dframe = dframe[start:end]
            records = cls.__encode_records(current_dframe, encoding)
            command(records, encoding)

    @classmethod
    def __encode_records(cls, dframe, encoding):
        return [cls.__encode_record(row.to_dict(), encoding)
                for (_, row) in dframe.iterrows()]

    @classmethod
    def __encode_record(cls, row, encoding):
        encoded = replace_keys(row, encoding)
        encoded[cls.DELETED_AT] = 0

        return encoded

    @classmethod
    def __make_encoding(cls, dframe, start=0):
        # Ensure that DATASET_ID is first so that we can guarantee an index.
        columns = [DATASET_ID] + sorted(dframe.columns - [DATASET_ID])
        return {v: str(start + i) for (i, v) in enumerate(columns)}

    @classmethod
    def __soft_delete(cls, query):
        cls.collection.update(query,
                              {'$set': {cls.DELETED_AT: now().isoformat()}})

    @classmethod
    def __store_encoding(cls, dataset, encoding):
        """Store encoded columns with dataset.

        :param dataset: The dataset to store the encoding with.
        :param encoding: The encoding for dataset.
        """
        record = {cls.ENCODING_DATASET_ID: dataset.dataset_id,
                  cls.ENCODING: encoding}
        super(cls, cls()).delete({cls.ENCODING_DATASET_ID: dataset.dataset_id})
        super(cls, cls()).save(record)

########NEW FILE########
__FILENAME__ = test_abstract_controller
import cherrypy

from bamboo.controllers.abstract_controller import AbstractController
from bamboo.tests.test_base import TestBase


class TestOptions(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.controller = AbstractController()

    def test_options_empty_response(self):
        response = self.controller.options()
        self.assertTrue(response == '')

    def test_options_status_code(self):
        self.controller.options()
        self.assertEqual(
            cherrypy.response.status, self.controller.NO_CONTENT_STATUS_CODE)

    def test_options_content_length(self):
        self.controller.options()
        self.assertEqual(cherrypy.response.headers['Content-Length'], 0)

########NEW FILE########
__FILENAME__ = test_abstract_datasets
import simplejson as json

from bamboo.controllers.calculations import Calculations
from bamboo.controllers.datasets import Datasets
from bamboo.core.summary import SUMMARY
from bamboo.lib.jsontools import df_to_jsondict
from bamboo.lib.mongo import MONGO_ID
from bamboo.models.dataset import Dataset
from bamboo.tests.test_base import TestBase


def comparable(dframe):
    return [reduce_precision(r) for r in df_to_jsondict(dframe)]


def reduce_precision(row):
    return {k: round(v, 10) if isinstance(v, float) else v
            for k, v in row.iteritems()}


class TestAbstractDatasets(TestBase):

    NUM_COLS = 15
    NUM_ROWS = 19

    def setUp(self):
        TestBase.setUp(self)
        self.controller = Datasets()
        self._file_name = 'good_eats.csv'
        self._update_file_name = 'good_eats_update.json'
        self._update_check_file_path = '%sgood_eats_update_values.json' % (
            self.FIXTURE_PATH)
        self.default_formulae = [
            'amount',
            'amount + 1',
            'amount - 5',
        ]

    def _put_row_updates(self, dataset_id=None, file_name=None, validate=True):
        if not dataset_id:
            dataset_id = self.dataset_id

        if not file_name:
            file_name = self._update_file_name

        update = open('%s%s' % (self.FIXTURE_PATH, file_name), 'r').read()
        result = json.loads(self.controller.update(dataset_id=dataset_id,
                                                   update=update))

        if validate:
            self.assertTrue(isinstance(result, dict))
            self.assertTrue(Dataset.ID in result)

        # set up the (default) values to test against
        with open(self._update_check_file_path, 'r') as f:
            self._update_values = json.loads(f.read())

    def _load_schema(self):
        return json.loads(
            self.controller.info(self.dataset_id))[Dataset.SCHEMA]

    def _check_dframes_are_equal(self, dframe1, dframe2):
        rows1 = comparable(dframe1)
        rows2 = comparable(dframe2)

        self.__check_dframe_is_subset(rows1, rows2)
        self.__check_dframe_is_subset(rows2, rows1)

    def __check_dframe_is_subset(self, rows1, rows2):
        for row in rows1:
            self.assertTrue(row in rows2,
                            '\nrow:\n%s\n\nnot in rows2:\n%s' % (row, rows2))

    def _post_calculations(self, formulae=[], group=None):
        schema = self._load_schema()
        controller = Calculations()

        for idx, formula in enumerate(formulae):
            name = 'calc_%d' % idx if not schema or\
                formula in schema.keys() else formula

            controller.create(self.dataset_id, formula=formula, name=name,
                              group=group)

    def _test_summary_built(self, result):
        # check that summary is created
        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)
        self.dataset_id = result[Dataset.ID]

        results = self.controller.summary(
            self.dataset_id,
            select=self.controller.SELECT_ALL_FOR_SUMMARY)

        return self._test_summary_results(results)

    def _test_summary_results(self, results):
        results = json.loads(results)
        self.assertTrue(isinstance(results, dict))
        return results

    def _test_aggregations(self, groups=['']):
        results = json.loads(self.controller.aggregations(self.dataset_id))
        self.assertTrue(isinstance(results, dict))
        self.assertEqual(len(results.keys()), len(groups))
        self.assertEqual(results.keys(), groups)
        linked_dataset_id = results[groups[0]]
        self.assertTrue(isinstance(linked_dataset_id, basestring))

        # inspect linked dataset
        return json.loads(self.controller.show(linked_dataset_id))

    def _test_summary_no_group(self, results, dataset_id=None, group=None):
        if not dataset_id:
            dataset_id = self.dataset_id

        group = [group] if group else []
        result_keys = results.keys()

        # minus the column that we are grouping on
        self.assertEqual(len(result_keys), self.NUM_COLS - len(group))

        columns = [col for col in
                   self.get_data(self._file_name).columns.tolist()
                   if not col in [MONGO_ID] + group]

        dataset = Dataset.find_one(dataset_id)
        labels_to_slugs = dataset.schema.labels_to_slugs

        for col in columns:
            slug = labels_to_slugs[col]
            self.assertTrue(slug in result_keys,
                            'col (slug): %s in: %s' % (slug, result_keys))
            self.assertTrue(SUMMARY in results[slug].keys())

########NEW FILE########
__FILENAME__ = test_abstract_datasets_update
import pickle

from bamboo.controllers.calculations import Calculations
from bamboo.lib.datetools import recognize_dates
from bamboo.models.dataset import Dataset
from bamboo.tests.controllers.test_abstract_datasets import\
    TestAbstractDatasets


class TestAbstractDatasetsUpdate(TestAbstractDatasets):

    def setUp(self):
        """
        These tests use the following dataset configuration:

            d -> dataset
            m -> merged
            a -> aggregated

            d1   d2
             \  /  \
              m1    a1
                \  /
                 m2

        Dependencies flow from top to bottom.
        """
        TestAbstractDatasets.setUp(self)

    def _create_original_datasets(self):
        self.dataset1_id = self._post_file()
        self.dataset2_id = self._post_file()

    def _add_common_calculations(self):
        self.calculations = Calculations()
        self.calculations.create(
            self.dataset2_id, 'amount + gps_alt', 'amount plus gps_alt')

    def _verify_dataset(self, dataset_id, fixture_path):
        dframe = Dataset.find_one(dataset_id).dframe()
        expected_dframe = recognize_dates(
            pickle.load(open('%s%s' % (
                self.FIXTURE_PATH, fixture_path), 'rb')))
        self._check_dframes_are_equal(dframe, expected_dframe)

########NEW FILE########
__FILENAME__ = test_calculations
from time import sleep

import simplejson as json

from bamboo.controllers.abstract_controller import AbstractController
from bamboo.controllers.calculations import Calculations
from bamboo.controllers.datasets import Datasets
from bamboo.core.frame import DATASET_ID
from bamboo.models.calculation import Calculation
from bamboo.models.dataset import Dataset
from bamboo.tests.decorators import requires_async
from bamboo.tests.test_base import TestBase
from bamboo.tests.controllers.test_abstract_datasets import\
    TestAbstractDatasets
from bamboo.lib.utils import is_float_nan


class TestCalculations(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.controller = Calculations()
        self.dataset_controller = Datasets()
        self.dataset_id = None
        self.formula = 'amount + gps_alt'
        self.name = 'test'

    def __post_formula(self, formula=None, name=None):
        if not formula:
            formula = self.formula
        if not name:
            name = self.name

        if not self.dataset_id:
            self.dataset_id = self._post_file()

        return self.controller.create(self.dataset_id, formula, name)

    def __post_update(self, dataset_id, update):
        return json.loads(self.dataset_controller.update(
            dataset_id=dataset_id, update=json.dumps(update)))

    def __wait_for_calculation_ready(self, dataset_id, name):
        while True:
            calculation = Calculation.find_one(dataset_id, name)

            if calculation.is_ready:
                break

            sleep(self.SLEEP_DELAY)

    def __test_error(self, response, error_text=None):
        response = json.loads(response)

        self.assertTrue(isinstance(response, dict))
        self.assertTrue(self.controller.ERROR in response)

        if not error_text:
            error_text = 'Must provide'

        self.assertTrue(error_text in response[self.controller.ERROR])

    def __test_create_from_json(self, json_filename, non_agg_cols=1, ex_len=1,
                                group=None):
        json_filepath = 'tests/fixtures/%s' % json_filename
        mock_uploaded_file = self._file_mock(json_filepath)
        dataset = Dataset.find_one(self.dataset_id)
        prev_columns = len(dataset.dframe().columns)
        response = json.loads(self.controller.create(
            self.dataset_id, json_file=mock_uploaded_file, group=group))

        self.assertTrue(isinstance(response, dict))
        self.assertTrue(self.controller.SUCCESS in response)
        self.assertTrue(self.dataset_id in response[Dataset.ID])

        self.assertEqual(
            ex_len, len(json.loads(self.controller.show(self.dataset_id))))
        self.assertEqual(
            prev_columns + non_agg_cols,
            len(dataset.reload().dframe().columns))

        return dataset

    def __verify_create(self, response):
        self.assertTrue(isinstance(response, dict))
        self.assertTrue(self.controller.SUCCESS in response)
        self.assertEqual(response[Dataset.ID], self.dataset_id)

        self.__wait_for_calculation_ready(self.dataset_id, self.name)

        dataset = Dataset.find_one(self.dataset_id)
        dframe = dataset.dframe()

        self.assertTrue(self.name in dataset.schema.keys())
        self.assertTrue(self.name in dframe.columns)
        self.assertEqual(TestAbstractDatasets.NUM_ROWS, len(dframe))
        self.assertEqual(TestAbstractDatasets.NUM_ROWS,
                         dataset.info()[Dataset.NUM_ROWS])

    def test_show(self):
        self.__post_formula()
        response = self.controller.show(self.dataset_id)

        self.assertTrue(isinstance(json.loads(response), list))

    def test_create(self):
        response = json.loads(self.__post_formula())
        self.__verify_create(response)

    @requires_async
    def test_create_async_not_ready(self):
        self.dataset_id = self._create_dataset_from_url(
            '%s%s' % (self._local_fixture_prefix(), 'good_eats_huge.csv'))
        response = json.loads(self.__post_formula())
        dataset = Dataset.find_one(self.dataset_id)

        self.assertFalse(dataset.is_ready)
        self.assertTrue(isinstance(response, dict))
        self.assertFalse(DATASET_ID in response)

        self._wait_for_dataset_state(self.dataset_id)

        self.assertFalse(self.name in dataset.schema.keys())

    @requires_async
    def test_create_async_sets_calculation_status(self):
        self.dataset_id = self._create_dataset_from_url(
            '%s%s' % (self._local_fixture_prefix(), 'good_eats_huge.csv'))

        self._wait_for_dataset_state(self.dataset_id)

        response = json.loads(self.__post_formula())

        self.assertTrue(isinstance(response, dict))
        self.assertTrue(self.controller.SUCCESS in response)
        self.assertEqual(response[Dataset.ID], self.dataset_id)

        response = json.loads(self.controller.show(self.dataset_id))[0]

        self.assertTrue(isinstance(response, dict))
        self.assertTrue(Calculation.STATE in response)
        self.assertEqual(response[Calculation.STATE],
                         Calculation.STATE_PENDING)

        self.__wait_for_calculation_ready(self.dataset_id, self.name)

        dataset = Dataset.find_one(self.dataset_id)

        self.assertTrue(self.name in dataset.schema.keys())

    @requires_async
    def test_create_async(self):
        self.dataset_id = self._post_file()

        self._wait_for_dataset_state(self.dataset_id)

        response = json.loads(self.__post_formula())
        self.__verify_create(response)

    def test_create_invalid_formula(self):
        dataset_id = self._post_file()
        result = json.loads(
            self.controller.create(dataset_id, '=NON_EXIST', self.name))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Datasets.ERROR in result.keys())

    def test_create_update_summary(self):
        dataset_id = self._post_file()
        Datasets().summary(
            dataset_id,
            select=Datasets.SELECT_ALL_FOR_SUMMARY)
        dataset = Dataset.find_one(dataset_id)

        self.assertTrue(isinstance(dataset.stats, dict))
        self.assertTrue(isinstance(dataset.stats[Dataset.ALL], dict))

        self.__post_formula()

        # stats should have new column for calculation
        dataset = Dataset.find_one(self.dataset_id)
        stats = dataset.stats.get(Dataset.ALL)
        self.assertTrue(self.name in stats.keys())

    def test_delete_nonexistent_calculation(self):
        dataset_id = self._post_file()
        result = json.loads(self.controller.delete(dataset_id, self.name))

        self.assertTrue(Calculations.ERROR in result)

    def test_delete(self):
        self.__post_formula()
        result = json.loads(self.controller.delete(self.dataset_id, self.name))

        self.assertTrue(AbstractController.SUCCESS in result)

        dataset = Dataset.find_one(self.dataset_id)
        self.assertTrue(self.name not in dataset.schema.labels_to_slugs)

    def test_delete_calculation_not_in_dataset(self):
        self.__post_formula()

        # Remove column from dataset
        dataset = Dataset.find_one(self.dataset_id)
        dataset.delete_columns([self.name])

        result = json.loads(self.controller.delete(self.dataset_id, self.name))

        self.assertTrue(AbstractController.SUCCESS in result)

        dataset = Dataset.find_one(self.dataset_id)
        self.assertTrue(self.name not in dataset.schema.labels_to_slugs)

    def test_delete_update_summary(self):
        self.__post_formula()

        dataset = Dataset.find_one(self.dataset_id)
        self.assertTrue(self.name in dataset.stats.get(Dataset.ALL).keys())

        json.loads(self.controller.delete(self.dataset_id, self.name))

        dataset = Dataset.find_one(self.dataset_id)
        self.assertTrue(self.name not in dataset.stats.get(Dataset.ALL).keys())

    def test_show_jsonp(self):
        self.__post_formula()
        results = self.controller.show(self.dataset_id, callback='jsonp')

        self.assertEqual('jsonp(', results[0:6])
        self.assertEqual(')', results[-1])

    def test_create_aggregation(self):
        self.formula = 'sum(amount)'
        self.name = 'test'
        response = json.loads(self.__post_formula())

        self.assertTrue(isinstance(response, dict))
        self.assertTrue(self.controller.SUCCESS in response)
        self.assertEqual(response[Dataset.ID], self.dataset_id)

        dataset = Dataset.find_one(self.dataset_id)

        self.assertTrue('' in dataset.aggregated_datasets_dict.keys())

    def test_delete_aggregation(self):
        self.formula = 'sum(amount)'
        self.name = 'test'
        json.loads(self.__post_formula())

        result = json.loads(
            self.controller.delete(self.dataset_id, self.name, ''))

        self.assertTrue(AbstractController.SUCCESS in result)

        dataset = Dataset.find_one(self.dataset_id)
        agg_dataset = dataset.aggregated_dataset('')

        self.assertTrue(self.name not in agg_dataset.schema.labels_to_slugs)

    def test_error_on_delete_calculation_with_dependency(self):
        self.__post_formula()
        dep_name = self.name
        self.formula = dep_name
        self.name = 'test1'
        response = json.loads(self.__post_formula())

        self.assertTrue(isinstance(response, dict))
        self.assertTrue(self.controller.SUCCESS in response)

        result = json.loads(
            self.controller.delete(self.dataset_id, dep_name, ''))

        self.assertTrue(AbstractController.ERROR in result)
        self.assertTrue('depend' in result[AbstractController.ERROR])

    def test_create_multiple(self):
        self.dataset_id = self._post_file()
        self.__test_create_from_json(
            'good_eats.calculations.json', non_agg_cols=2, ex_len=2)

    def test_create_multiple_ignore_group(self):
        self.dataset_id = self._post_file()
        dataset = self.__test_create_from_json(
            'good_eats.calculations.json', non_agg_cols=2, ex_len=2,
            group='risk_factor')

        self.assertEqual(dataset.aggregated_datasets_dict, {})

    def test_create_json_single(self):
        self.dataset_id = self._post_file()
        self.__test_create_from_json('good_eats_single.calculations.json')

    def test_create_multiple_with_group(self):
        self.dataset_id = self._post_file()
        groups = ['risk_factor', 'risk_factor,food_type', 'food_type']
        dataset = self.__test_create_from_json(
            'good_eats_group.calculations.json', non_agg_cols=2, ex_len=6)

        for group in groups:
            self.assertTrue(group in dataset.aggregated_datasets_dict.keys())
            dframe = dataset.aggregated_dataset(group).dframe()

            for column in Calculation().split_groups(group):
                self.assertTrue(column in dframe.columns)

    def test_create_with_missing_args(self):
        self.dataset_id = self._post_file()
        self.__test_error(self.controller.create(self.dataset_id))
        self.__test_error(
            self.controller.create(self.dataset_id, formula='gps_alt'))
        self.__test_error(
            self.controller.create(self.dataset_id, name='test'))

    def test_create_with_bad_json(self):
        self.dataset_id = self._post_file()
        json_filepath = self._fixture_path_prefix(
            'good_eats_bad.calculations.json')
        mock_uploaded_file = self._file_mock(json_filepath)

        self.__test_error(
            self.controller.create(self.dataset_id,
                                   json_file=mock_uploaded_file),
            error_text='Required')

        # Mock is now an empty file
        self.__test_error(
            self.controller.create(self.dataset_id,
                                   json_file=mock_uploaded_file),
            error_text='Improper format for JSON')

    def test_create_reserved_name(self):
        name = 'sum'
        response = json.loads(self.__post_formula(None, name))

        self.assertTrue(isinstance(response, dict))
        self.assertTrue(self.controller.SUCCESS in response)
        self.assertEqual(response[Dataset.ID], self.dataset_id)

        dataset = Dataset.find_one(self.dataset_id)
        slug = dataset.schema.labels_to_slugs[name]
        response = json.loads(self.__post_formula('%s + amount' % slug))

        self.assertTrue(isinstance(response, dict))
        self.assertTrue(self.controller.SUCCESS in response)
        self.assertTrue(self.dataset_id in response[Dataset.ID])

    def test_create_with_duplicate_names(self):
        formula_names_to_valid = {
            'water_not_functioning_none': True,   # an already slugged column
            'water_not_functioning/none': False,  # a non-slug column
            'region': False,    # an existing column
            'date': False,      # a reserved key and an existing column
            'sum': True,        # a reserved key
        }

        for formula_name, valid in formula_names_to_valid.items():
            dataset_id = self._post_file('water_points.csv')
            dframe_before = Dataset.find_one(dataset_id).dframe()

            # a calculation
            response = json.loads(self.controller.create(
                dataset_id,
                'water_source_type in ["borehole"]',
                formula_name))

            self.assertTrue(isinstance(response, dict))

            if valid:
                self.assertTrue(self.controller.SUCCESS in response)
            else:
                self.assertTrue(self.controller.ERROR in response)
                self.assertTrue(
                    formula_name in response[self.controller.ERROR])

            dataset = Dataset.find_one(dataset_id)

            if valid:
                name = dataset.calculations()[-1].name

            # an aggregation
            response = json.loads(self.controller.create(
                dataset_id,
                'newest(date_, water_functioning)',
                formula_name))

            self.assertTrue(isinstance(response, dict))
            self.assertTrue(self.controller.SUCCESS in response)

            dframe_after = dataset.dframe()

            # Does not change data
            self.assertEqual(len(dframe_before), len(dframe_after))

            if valid:
                slug = dataset.schema.labels_to_slugs[name]
                self.assertTrue(slug not in dframe_before.columns)
                self.assertTrue(slug in dframe_after.columns)

            if valid:
                # Does change columns
                self.assertEqual(
                    len(dframe_before.columns) + 1, len(dframe_after.columns))
            else:
                # Does not change columns
                self.assertEqual(
                    len(dframe_before.columns), len(dframe_after.columns))

            # check OK on update
            update = {
                'date': '2013-01-05',
                'water_source_type': 'borehole',
            }
            result = self.__post_update(dataset_id, update)
            self.assertTrue(Dataset.ID in result)
            dataset = Dataset.find_one(dataset_id)
            dframe_after_update = dataset.dframe()
            self.assertEqual(len(dframe_after) + 1, len(dframe_after_update))

    def test_cannot_create_aggregations_with_duplicate_names(self):
        dataset_id = self._post_file('water_points.csv')

        formula_name = 'name'

        response = json.loads(self.controller.create(
            dataset_id,
            'newest(date_, water_functioning)',
            formula_name))

        self.assertTrue(self.controller.SUCCESS in response)

        # another with the same name
        response = json.loads(self.controller.create(
            dataset_id,
            'newest(date_, water_functioning)',
            formula_name))

        self.assertTrue(formula_name in response[self.controller.ERROR])

    def test_can_create_aggregations_with_duplicate_as_slug_names(self):
        dataset_id = self._post_file('water_points.csv')

        formula_name = 'name*'

        response = json.loads(self.controller.create(
            dataset_id,
            'newest(date_, water_functioning)',
            formula_name))

        self.assertTrue(self.controller.SUCCESS in response)

        # another with the same name
        response = json.loads(self.controller.create(
            dataset_id,
            'newest(date_, water_functioning)',
            'name_'))

        self.assertTrue(self.controller.SUCCESS in response)

    def test_newest(self):
        expected_dataset = {
            u'wp_functional': {0: u'no', 1: u'yes', 2: u'no', 3: u'yes'},
            u'id': {0: 1, 1: 2, 2: 3, 3: 4}}
        dataset_id = self._post_file('newest_test.csv')
        self.controller.create(dataset_id,
                               'newest(submit_date,functional)',
                               'wp_functional', group='id')
        dataset = Dataset.find_one(dataset_id)
        agg_ds = dataset.aggregated_dataset('id')

        self.assertEqual(expected_dataset, agg_ds.dframe().to_dict())

    def test_update_after_agg(self):
        dataset_id = self._post_file('wp_data.csv')
        results = json.loads(self.controller.create(dataset_id,
                             'newest(submit_date,wp_id)', 'wp_newest'))

        dataset = Dataset.find_one(dataset_id)
        previous_num_rows = dataset.num_rows

        self.assertTrue(self.controller.SUCCESS in results)
        self.assertFalse(dataset.aggregated_dataset('') is None)

        update = {
            'submit_date': '2013-01-05',
            'wp_id': 'D',
            'functional': 'no',
        }
        self.__post_update(dataset_id, update)
        update = {
            'wp_id': 'E',
            'functional': 'no',
        }
        self.__post_update(dataset_id, update)

        dataset = Dataset.find_one(dataset_id)
        current_num_rows = dataset.num_rows
        agg_df = dataset.aggregated_dataset('').dframe()

        self.assertEqual(agg_df.get_value(0, 'wp_newest'), 'D')
        self.assertEqual(current_num_rows, previous_num_rows + 2)

    @requires_async
    def test_update_after_agg_group(self):
        dataset_id = self._post_file('wp_data.csv')
        group = 'wp_id'
        self._wait_for_dataset_state(dataset_id)

        test_calculations = {
            'newest(submit_date,functional)': 'wp_functional',
            'max(submit_date)': 'latest_submit_date',
            'ratio(functional in ["yes"], 1)': 'wp_func_ratio'}

        expected_results = {'wp_id': ['A', 'B', 'C', 'n/a'],
                            'wp_functional': ['yes', 'no', 'yes', 'yes'],
                            'wp_func_ratio': [1.0, 0.0, 1.0, 1.0],
                            'wp_func_ratio_denominator': [1, 1, 1, 1],
                            'wp_func_ratio_numerator': [1.0, 0.0, 1.0, 1.0],
                            'latest_submit_date': [1356998400, 1357084800,
                                                   1357171200, 1357257600]}

        expected_results_after = {
            'wp_id': ['A', 'B', 'C', 'D', 'n/a'],
            'wp_functional': ['no', 'no', 'yes', 'yes'],
            'wp_func_ratio': [0.5, 0.0, 1.0, 1.0, 1.0],
            'wp_func_ratio_denominator': [2.0, 1.0, 1.0, 1.0, 1.0],
            'wp_func_ratio_numerator': [1.0, 0.0, 1.0, 1.0, 1.0],
            'latest_submit_date': [1357603200.0, 1357084800.0,
                                   1357171200.0, 1357257600.0]}

        for formula, name in test_calculations.items():
            results = json.loads(self.controller.create(
                dataset_id, formula, name, group=group))

            self.assertTrue(self.controller.SUCCESS in results)

        dataset = Dataset.find_one(dataset_id)
        previous_num_rows = dataset.num_rows

        while True:
            dataset = Dataset.find_one(dataset_id)

            if dataset.aggregated_dataset(group) and all(
                    [not c.is_pending for c in dataset.calculations()]):
                break
            sleep(self.SLEEP_DELAY)

        agg_dframe = dataset.aggregated_dataset(group).dframe()
        self.assertEqual(set(expected_results.keys()),
                         set(agg_dframe.columns.tolist()))

        for column, results in expected_results.items():
            self.assertEqual(results,
                             agg_dframe[column].tolist())

        update = {
            'wp_id': 'D',
            'functional': 'yes',
        }
        self.__post_update(dataset_id, update)
        update = {
            'submit_date': '2013-01-08',
            'wp_id': 'A',
            'functional': 'no',
        }
        self.__post_update(dataset_id, update)

        while True:
            dataset = Dataset.find_one(dataset_id)
            current_num_rows = dataset.num_rows

            if not len(dataset.pending_updates):
                break

            sleep(self.SLEEP_DELAY)

        dataset = Dataset.find_one(dataset_id)
        agg_dframe = dataset.aggregated_dataset(group).dframe()

        self.assertEqual(current_num_rows, previous_num_rows + 2)
        self.assertEqual(set(expected_results_after.keys()),
                         set(agg_dframe.columns.tolist()))
        for column, results in expected_results_after.items():
            column = [x for x in agg_dframe[column].tolist() if not
                      is_float_nan(x)]
            self.assertEqual(results, column)

    @requires_async
    def test_fail_in_background(self):
        dataset_id = self._post_file('wp_data.csv')
        group = 'wp_id'
        self._wait_for_dataset_state(dataset_id)

        self.controller.create(dataset_id,
                               'newest(submit_date,functional)',
                               'wp_functional',
                               group=group)
        self.controller.create(dataset_id,
                               'max(submit_date)',
                               'latest_submit_date',
                               group=group)

        # Update the name to cause has pending to be true and infinite retries.
        # It will fail after 10 retries.
        calc = Calculation.find_one(dataset_id, 'latest_submit_date', group)
        calc.update({calc.NAME: 'another_name'})

        update = {
            'wp_id': 'D',
            'functional': 'yes',
        }
        self.__post_update(dataset_id, update)
        update = {
            'submit_date': '2013-01-08',
            'wp_id': 'A',
            'functional': 'no',
        }
        self.__post_update(dataset_id, update)

        while True:
            dataset = Dataset.find_one(dataset_id)
            calcs_not_pending = [
                c.state != c.STATE_PENDING for c in dataset.calculations()]

            if not len(dataset.pending_updates) and all(calcs_not_pending):
                break

            sleep(self.SLEEP_DELAY)

        for c in dataset.calculations():
            self.assertEqual(c.STATE_FAILED, c.state)
            self.assertTrue('Traceback' in c.error_message)

    def test_fail_then_create(self):
        response = json.loads(self.__post_formula())
        self.__verify_create(response)

        # Overwrite as failed
        calc = Calculation.find_one(self.dataset_id, self.name)
        calc.update({calc.STATE: calc.STATE_FAILED})

        # Test we can still add a calculation
        self.name = 'test2'
        response = json.loads(self.__post_formula())
        self.__verify_create(response)

########NEW FILE########
__FILENAME__ = test_datasets
from datetime import datetime
import pickle
from tempfile import NamedTemporaryFile
from time import mktime, sleep
from urllib2 import URLError

from mock import patch
import simplejson as json

from bamboo.controllers.datasets import Datasets
from bamboo.lib.datetools import now
from bamboo.lib.jsontools import df_to_jsondict
from bamboo.lib.query_args import QueryArgs
from bamboo.lib.schema_builder import CARDINALITY, DATETIME, OLAP_TYPE,\
    SIMPLETYPE
from bamboo.models.dataset import Dataset
from bamboo.tests.controllers.test_abstract_datasets import\
    TestAbstractDatasets
from bamboo.tests.decorators import requires_async


class TestDatasets(TestAbstractDatasets):

    def setUp(self):
        TestAbstractDatasets.setUp(self)
        self._file_path = self._fixture_path_prefix(self._file_name)
        self._file_uri = self._local_fixture_prefix(self._file_name)
        self.url = 'http://formhub.org/mberg/forms/good_eats/data.csv'

    def __test_get_with_query_or_select(
            self, query='{}', select=None, distinct=None, num_results=None,
            result_keys=None):
        dataset_id = self._post_file()
        results = json.loads(self.controller.show(dataset_id, query=query,
                             select=select, distinct=distinct))

        self.assertTrue(isinstance(results, list))

        if num_results:
            self.assertEqual(len(results), num_results)
        if num_results > 3:
            self.assertTrue(isinstance(results[3], dict))
        if select:
            self.assertEqual(sorted(results[0].keys()), result_keys)
        if query != '{}':
            self.assertEqual(len(results), num_results)

    def __upload_mocked_file(self, **kwargs):
        mock_uploaded_file = self._file_mock(self._file_path)

        return json.loads(self.controller.create(
            csv_file=mock_uploaded_file, **kwargs))

    def __wait_for_dataset(self, dataset_id):
        while True:
            results = json.loads(self.controller.show(dataset_id))
            if len(results):
                break
            sleep(self.SLEEP_DELAY)

        sleep(self.SLEEP_DELAY)

        return results

    def test_create_from_csv(self):
        result = self.__upload_mocked_file()
        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)

        # test parse type as date correctly
        dframe = Dataset.find_one(result[Dataset.ID]).dframe()
        self.assertTrue(isinstance(dframe.submit_date[0], datetime))

        results = self._test_summary_built(result)
        self._test_summary_no_group(results)

    def test_create_from_csv_unicode(self):
        dframe_length = 1
        dframe_data = [{u'\u03c7': u'\u03b1', u'\u03c8': u'\u03b2'}]

        _file_name = 'unicode.csv'
        self._file_path = self._file_path.replace(self._file_name, _file_name)
        result = self.__upload_mocked_file()

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)

        dataset = Dataset.find_one(result[Dataset.ID])

        self.assertEqual(Dataset.STATE_READY, dataset.state)

        dframe = dataset.dframe()

        self.assertEqual(dframe_length, len(dframe))
        self.assertEqual(dframe_data, df_to_jsondict(dframe))

        self._test_summary_built(result)

    def test_create_from_csv_custom_na(self):
        dframe_length = 4
        _file_name = 'wp_data.csv'
        self._file_path = self._file_path.replace(self._file_name, _file_name)
        result = self.__upload_mocked_file(na_values=json.dumps(['n/a']))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)

        dataset = Dataset.find_one(result[Dataset.ID])

        self.assertEqual(Dataset.STATE_READY, dataset.state)
        self.assertEqual(dframe_length, len(dataset.dframe()))
        self.assertTrue(isinstance(dataset.dframe().wp_id[1], float))

        self._test_summary_built(result)

    def test_create_from_csv_mixed_col(self):
        dframe_length = 8
        _file_name = 'good_eats_mixed.csv'
        self._file_path = self._file_path.replace(self._file_name, _file_name)
        result = self.__upload_mocked_file()

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)

        dataset = Dataset.find_one(result[Dataset.ID])

        self.assertEqual(Dataset.STATE_READY, dataset.state)
        self.assertEqual(dframe_length, len(dataset.dframe()))

        self._test_summary_built(result)

    def test_create_from_file_for_nan_float_cell(self):
        """First data row has one cell blank, which is usually interpreted
        as nan, a float value."""
        _file_name = 'good_eats_nan_float.csv'
        self._file_path = self._file_path.replace(self._file_name, _file_name)
        result = self.__upload_mocked_file()

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)

        results = self._test_summary_built(result)
        self._test_summary_no_group(results)
        results = json.loads(self.controller.info(self.dataset_id))
        simpletypes = pickle.load(
            open(self._fixture_path_prefix('good_eats_simpletypes.pkl'), 'rb'))

        for column_name, column_schema in results[Dataset.SCHEMA].items():
            self.assertEqual(
                column_schema[SIMPLETYPE], simpletypes[column_name])

    def test_create_from_url_failure(self):
        result = json.loads(self.controller.create(url=self._file_uri))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Datasets.ERROR in result)

    def test_create_from_url(self):
        dframe = self.get_data('good_eats.csv')
        with patch('pandas.read_csv', return_value=dframe):
            result = json.loads(self.controller.create(url=self.url))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)

        results = json.loads(self.controller.show(result[Dataset.ID]))

        self.assertEqual(len(results), self.NUM_ROWS)
        self._test_summary_built(result)

    @requires_async
    @patch('pandas.read_csv', return_value=None)
    def test_create_from_not_csv_url(self, read_csv):
        result = json.loads(self.controller.create(
            url='http://74.125.228.110/'))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)

        results = json.loads(self.controller.show(result[Dataset.ID]))

        self.assertEqual(len(results), 0)

    @requires_async
    @patch('pandas.read_csv', return_value=None, side_effect=URLError(''))
    def test_create_from_bad_url(self, read_csv):
        result = json.loads(self.controller.create(
            url='http://dsfskfjdks.com'))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)

        dataset_id = result[Dataset.ID]
        dataset = self._wait_for_dataset_state(dataset_id)

        self.assertEqual(Dataset.STATE_FAILED, dataset.state)

    @requires_async
    def test_create_from_bad_csv(self):
        tmp_file = NamedTemporaryFile(delete=False)
        mock = self._file_mock(tmp_file.name)
        result = json.loads(self.controller.create(
            csv_file=mock))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)

        dataset_id = result[Dataset.ID]
        dataset = self._wait_for_dataset_state(dataset_id)

        self.assertEqual(Dataset.STATE_FAILED, dataset.state)

    def test_create_from_json(self):
        mock = self._file_mock(self._fixture_path_prefix('good_eats.json'))
        result = json.loads(self.controller.create(
            json_file=mock))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)

        # test parse type as date correctly
        dframe = Dataset.find_one(result[Dataset.ID]).dframe()
        self.assertTrue(isinstance(dframe.submit_date[0], datetime))

        results = self._test_summary_built(result)
        self._test_summary_no_group(results)

    @requires_async
    def test_create_from_json_async(self):
        mock = self._file_mock(self._fixture_path_prefix('good_eats.json'))
        result = json.loads(self.controller.create(
            json_file=mock))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)

        self.__wait_for_dataset(result[Dataset.ID])

        results = self._test_summary_built(result)
        self._test_summary_no_group(results)

    def test_create_no_url_or_csv(self):
        result = json.loads(self.controller.create())

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Datasets.ERROR in result)

    def test_show(self):
        dataset_id = self._post_file()
        results = json.loads(self.controller.show(dataset_id))

        self.assertTrue(isinstance(results, list))
        self.assertTrue(isinstance(results[0], dict))
        self.assertEqual(len(results), self.NUM_ROWS)

    def test_show_csv(self):
        dataset_id = self._post_file()
        results = self.controller.show(dataset_id, format='csv')

        self.assertTrue(isinstance(results, str))
        self.assertEqual(len(results.split('\n')[0].split(',')), self.NUM_COLS)
        # one for header, one for empty final line
        self.assertEqual(len(results.split('\n')), self.NUM_ROWS + 2)

    @requires_async
    def test_show_async(self):
        dataset_id = self._post_file()

        results = self.__wait_for_dataset(dataset_id)

        self.assertTrue(isinstance(results, list))
        self.assertTrue(isinstance(results[0], dict))
        self.assertEqual(len(results), self.NUM_ROWS)

    def test_show_after_calculation(self):
        self.dataset_id = self._post_file()
        self._post_calculations(['amount < 4'])
        results = json.loads(self.controller.show(self.dataset_id,
                             select='{"amount___4": 1}'))

        self.assertTrue(isinstance(results, list))
        self.assertTrue(isinstance(results[0], dict))
        self.assertEqual(len(results), self.NUM_ROWS)

    def test_show_index(self):
        dataset_id = self._post_file()
        results = json.loads(self.controller.show(dataset_id, index=True))

        for row in results:
            self.assertTrue('index' in row.keys())

    def test_info(self):
        dataset_id = self._post_file()
        results = json.loads(self.controller.info(dataset_id))
        expected_keys = [Dataset.ID, Dataset.LABEL, Dataset.DESCRIPTION,
                         Dataset.LICENSE, Dataset.ATTRIBUTION,
                         Dataset.CREATED_AT, Dataset.PARENT_IDS,
                         Dataset.UPDATED_AT,
                         Dataset.SCHEMA, Dataset.NUM_ROWS, Dataset.NUM_COLUMNS,
                         Dataset.STATE]

        self.assertTrue(isinstance(results, dict))

        for key in expected_keys:
            self.assertTrue(key in results.keys())

        self.assertEqual(results[Dataset.NUM_ROWS], self.NUM_ROWS)
        self.assertEqual(results[Dataset.NUM_COLUMNS], self.NUM_COLS)
        self.assertEqual(results[Dataset.STATE], Dataset.STATE_READY)
        self.assertEqual(results[Dataset.PARENT_IDS], [])

    def test_info_parent_ids(self):
        self.dataset_id = self._post_file()
        self._post_calculations(self.default_formulae + ['sum(amount)'])
        agg_id = json.loads(self.controller.aggregations(self.dataset_id))['']
        results = json.loads(self.controller.info(agg_id))
        self.assertEqual([self.dataset_id], results[Dataset.PARENT_IDS])

    def test_info_cardinality(self):
        dataset_id = self._post_file()
        results = json.loads(self.controller.info(dataset_id))

        self.assertTrue(isinstance(results, dict))
        self.assertTrue(Dataset.SCHEMA in results.keys())

        schema = results[Dataset.SCHEMA]
        cardinalities = pickle.load(open(
            self._fixture_path_prefix('good_eats_cardinalities.pkl'), 'rb'))

        for key, column in schema.items():
            self.assertTrue(CARDINALITY in column.keys())
            self.assertEqual(
                column[CARDINALITY], cardinalities[key])

    def test_info_after_adding_calculations(self):
        self.dataset_id = self._post_file()
        self._post_calculations(formulae=self.default_formulae)
        results = json.loads(self.controller.info(self.dataset_id))
        self.assertEqual(results[Dataset.NUM_COLUMNS], self.NUM_COLS +
                         len(self.default_formulae))

    def test_info_schema(self):
        dataset_id = self._post_file()
        results = json.loads(self.controller.info(dataset_id))
        self.assertTrue(isinstance(results, dict))
        result_keys = results.keys()
        for key in [
                Dataset.CREATED_AT, Dataset.ID, Dataset.SCHEMA,
                Dataset.UPDATED_AT]:
            self.assertTrue(key in result_keys)
        self.assertEqual(
            results[Dataset.SCHEMA]['submit_date'][SIMPLETYPE], DATETIME)

    def test_show_bad_id(self):
        results = self.controller.show('honey_badger')
        self.assertTrue(Datasets.ERROR in results)

    def test_show_with_query(self):
        query = '{"rating": "delectible"}'
        self.__test_get_with_query_or_select(query, num_results=11)

    def test_show_with_or_query(self):
        self.__test_get_with_query_or_select(
            '{"$or": [{"food_type": "lunch"}, {"food_type": "deserts"}]}',
            num_results=9)

    @requires_async
    def test_show_with_query_async(self):
        self.__test_get_with_query_or_select('{"rating": "delectible"}',
                                             num_results=0)

    def test_show_with_query_limit_order_by(self):

        def get_results(query='{}', select=None, limit=None, order_by=None):
            dataset_id = self._post_file()
            return json.loads(self.controller.show(dataset_id,
                                                   query=query,
                                                   select=select,
                                                   limit=limit,
                                                   order_by=order_by))

        # test the limit
        limit = 4
        results = get_results(limit=limit)
        self.assertEqual(len(results), limit)

        # test the order_by
        limit = 1
        results = get_results(limit=limit, order_by='rating')
        self.assertEqual(results[0].get('rating'), 'delectible')

        limit = 1
        results = get_results(limit=limit, order_by='-rating')
        self.assertEqual(results[0].get('rating'), 'epic_eat')

    def test_show_with_bad_query(self):
        dataset_id = self._post_file()
        results = json.loads(self.controller.show(dataset_id,
                             query='bad json'))
        self.assertTrue('JSON' in results[Datasets.ERROR])

    def test_show_with_date_query(self):
        query = {
            'submit_date': {'$lt': mktime(now().timetuple())}
        }
        self.__test_get_with_query_or_select(
            query=json.dumps(query),
            num_results=self.NUM_ROWS)
        query = {
            'submit_date': {'$gt': mktime(now().timetuple())}
        }
        self.__test_get_with_query_or_select(
            query=json.dumps(query),
            num_results=0)
        date = mktime(datetime(2012, 2, 1, 0).timetuple())
        query = {
            'submit_date': {'$gt': date}
        }
        self.__test_get_with_query_or_select(
            query=json.dumps(query),
            num_results=4)

    def test_show_with_formatted_date_query(self):
        query = '{"submit_date": {"$lt": "2012-01-06"}}'
        self.__test_get_with_query_or_select(query, num_results=11)

    def test_show_with_select(self):
        self.__test_get_with_query_or_select(select='{"rating": 1}',
                                             num_results=self.NUM_ROWS,
                                             result_keys=['rating'])

    def test_show_with_distinct(self):
        dataset_id = self._post_file()
        results = json.loads(self.controller.show(dataset_id, query='{}',
                             distinct='rating'))
        self.assertTrue(isinstance(results, list))
        self.assertEqual(['delectible', 'epic_eat'], results)

    def test_show_with_select_and_query(self):
        self.__test_get_with_query_or_select('{"rating": "delectible"}',
                                             '{"rating": 1}',
                                             num_results=11,
                                             result_keys=['rating'])

    def test_aggregations_datasets_empty(self):
        self.dataset_id = self._post_file()
        self._post_calculations(formulae=self.default_formulae)
        results = json.loads(self.controller.aggregations(self.dataset_id))

        self.assertTrue(isinstance(results, dict))
        self.assertEqual(len(results.keys()), 0)

    def test_aggregations_datasets(self):
        self.dataset_id = self._post_file()
        self._post_calculations(self.default_formulae + ['sum(amount)'])

        results = self._test_aggregations()

        row_keys = ['sum_amount_']

        for row in results:
            self.assertEqual(row.keys(), row_keys)
            self.assertTrue(isinstance(row.values()[0], float))

    def test_aggregations_datasets_with_group(self):
        self.dataset_id = self._post_file()
        group = 'food_type'
        self._post_calculations(self.default_formulae + ['sum(amount)'], group)
        results = self._test_aggregations([group])
        row_keys = [group, 'sum_amount_']

        for row in results:
            self.assertEqual(row.keys(), row_keys)
            self.assertTrue(isinstance(row.values()[0], basestring))
            self.assertTrue(isinstance(row.values()[1], float))

    def test_aggregations_datasets_with_multigroup(self):
        self.dataset_id = self._post_file()
        group = 'food_type,rating'
        self._post_calculations(self.default_formulae + ['sum(amount)'], group)
        results = self._test_aggregations([group])
        # only so we can split
        dataset = Dataset()
        row_keys = (dataset.split_groups(group) +
                    ['sum_amount_']).sort()

        for row in results:
            sorted_row_keys = row.keys().sort()
            self.assertEqual(sorted_row_keys, row_keys)
            self.assertTrue(isinstance(row.values()[0], basestring))
            self.assertTrue(isinstance(row.values()[1], basestring))
            self.assertTrue(isinstance(row.values()[2], float))

    def test_aggregations_datasets_with_group_two_calculations(self):
        self.dataset_id = self._post_file()
        group = 'food_type'
        self._post_calculations(
            self.default_formulae + ['sum(amount)', 'sum(gps_alt)'], group)
        results = self._test_aggregations([group])
        row_keys = [group, 'sum_amount_', 'sum_gps_alt_']

        for row in results:
            self.assertEqual(row.keys(), row_keys)
            self.assertTrue(isinstance(row.values()[0], basestring))
            for value in row.values()[1:]:
                self.assertTrue(isinstance(value, float) or value == 'null')

    def test_aggregations_datasets_with_two_groups(self):
        self.dataset_id = self._post_file()
        group = 'food_type'
        self._post_calculations(self.default_formulae + ['sum(amount)'])
        self._post_calculations(['sum(gps_alt)'], group)
        groups = ['', group]
        results = self._test_aggregations(groups)

        for row in results:
            self.assertEqual(row.keys(), ['sum_amount_'])
            self.assertTrue(isinstance(row.values()[0], float))

        # get second linked dataset
        results = json.loads(self.controller.aggregations(self.dataset_id))

        self.assertEqual(len(results.keys()), len(groups))
        self.assertEqual(results.keys(), groups)

        linked_dataset_id = results[group]

        self.assertTrue(isinstance(linked_dataset_id, basestring))

        # inspect linked dataset
        results = json.loads(self.controller.show(linked_dataset_id))
        row_keys = [group, 'sum_gps_alt_']

        for row in results:
            self.assertEqual(row.keys(), row_keys)

    def test_delete(self):
        dataset_id = self._post_file()
        result = json.loads(self.controller.delete(dataset_id))

        self.assertEqual(result[Datasets.SUCCESS], 'deleted dataset')
        self.assertEqual(result[Dataset.ID], dataset_id)

    def test_delete_bad_id(self):
        for dataset_name in self.TEST_DATASETS:
            result = json.loads(self.controller.delete(
                                self.test_dataset_ids[dataset_name]))

            self.assertTrue(Datasets.ERROR in result)

    def test_delete_with_query(self):
        dataset_id = self._post_file()
        query = {'food_type': 'caffeination'}
        dataset = Dataset.find_one(dataset_id)
        dframe = dataset.dframe(query_args=QueryArgs(query=query))
        len_after_delete = len(dataset.dframe()) - len(dframe)

        query = json.dumps(query)
        result = json.loads(self.controller.delete(dataset_id, query=query))
        message = result[Datasets.SUCCESS]

        self.assertTrue('deleted dataset' in message)
        self.assertTrue(query in message)
        self.assertEqual(result[Dataset.ID], dataset_id)

        dframe = Dataset.find_one(dataset_id).dframe()

        self.assertEqual(len(dframe), len_after_delete)

    def test_show_jsonp(self):
        dataset_id = self._post_file()
        results = self.controller.show(dataset_id, callback='jsonp')

        self.assertEqual('jsonp(', results[0:6])
        self.assertEqual(')', results[-1])

    def test_drop_columns(self):
        dataset_id = self._post_file()
        results = json.loads(
            self.controller.drop_columns(dataset_id, ['food_type']))

        self.assertTrue(isinstance(results, dict))
        self.assertTrue(Datasets.SUCCESS in results)
        self.assertTrue('dropped' in results[Datasets.SUCCESS])

        results = json.loads(self.controller.show(dataset_id))

        self.assertTrue(isinstance(results, list))
        self.assertTrue(isinstance(results[0], dict))
        self.assertEqual(len(results[0].keys()), self.NUM_COLS - 1)

    def test_drop_columns_non_existent_id(self):
        results = json.loads(
            self.controller.drop_columns('313514', ['food_type']))

        self.assertTrue(isinstance(results, dict))
        self.assertTrue(Datasets.ERROR in results)

    def test_drop_columns_non_existent_column(self):
        dataset_id = self._post_file()
        results = json.loads(
            self.controller.drop_columns(dataset_id, ['foo']))

        self.assertTrue(isinstance(results, dict))
        self.assertTrue(Datasets.ERROR in results)

    def test_bad_date(self):
        dataset_id = self._post_file('bad_date.csv')
        dataset = Dataset.find_one(dataset_id)

        self.assertEqual(dataset.num_rows, 1)
        self.assertEqual(len(dataset.schema.keys()), 3)

        result = json.loads(self.controller.summary(
            dataset_id, select=self.controller.SELECT_ALL_FOR_SUMMARY,
            group='name'))

        self.assertTrue('name' in result.keys())

    def test_multiple_date_formats(self):
        dataset_id = self._post_file('multiple_date_formats.csv')
        dataset = Dataset.find_one(dataset_id)

        self.assertEqual(dataset.num_rows, 2)
        self.assertEqual(len(dataset.schema.keys()), 4)

    def test_boolean_column(self):
        dataset_id = self._post_file('water_points.csv')
        summaries = json.loads(self.controller.summary(dataset_id,
                               select=self.controller.SELECT_ALL_FOR_SUMMARY))

        for summary in summaries.values():
            self.assertFalse(summary is None)

    @requires_async
    def test_perishable_dataset(self):
        perish_after = 2
        result = self.__upload_mocked_file(perish=perish_after)
        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)
        dataset_id = result[Dataset.ID]

        while True:
            results = json.loads(self.controller.show(dataset_id))
            if len(results):
                self.assertTrue(len(results), self.NUM_ROWS)
                break
            sleep(self.SLEEP_DELAY)

        # test that later it is deleted
        sleep(perish_after)
        result = json.loads(self.controller.show(dataset_id))
        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Datasets.ERROR in result)

    def test_set_info(self):
        dataset_id = self._post_file('multiple_date_formats.csv')
        kwargs = {
            'attribution': '1',
            'description': '2',
            'label': '3',
            'license': '4',
        }
        results = json.loads(self.controller.set_info(dataset_id, **kwargs))

        self.assertEqual(results[Dataset.ID], dataset_id)

        dataset = Dataset.find_one(dataset_id)

        for key, value in dataset.info().items():
            if kwargs.get(key):
                self.assertEqual(value, kwargs[key])

    def test_count(self):
        dataset_id = self._post_file()

        results = json.loads(self.controller.show(dataset_id, count=True))

        self.assertEqual(results, self.NUM_ROWS)

    def test_count_with_distinct(self):
        dataset_id = self._post_file()

        results = json.loads(self.controller.show(
            dataset_id, count=True, distinct='amount'))

        self.assertEqual(results, self.NUM_ROWS - 4)

    def test_count_with_limit(self):
        dataset_id = self._post_file()
        limit = 10

        results = json.loads(self.controller.show(
            dataset_id, count=True, limit=limit))

        self.assertEqual(results, limit)

    def test_count_with_query(self):
        dataset_id = self._post_file()

        results = json.loads(self.controller.show(
            dataset_id, query='{"rating": "delectible"}',
            count=True))

        self.assertEqual(results, 11)

    def test_set_olap_type(self):
        new_olap_type = 'dimension'
        column = 'amount'

        dataset_id = self._post_file()

        results = json.loads(self.controller.info(dataset_id))
        expected_schema = results[Dataset.SCHEMA]
        expected_schema[column][OLAP_TYPE] = new_olap_type

        # set OLAP Type
        results = json.loads(self.controller.set_olap_type(
            dataset_id, column, new_olap_type))
        self.assertTrue(Datasets.SUCCESS in results.keys())

        # Check new schema
        results = json.loads(self.controller.info(dataset_id))
        new_schema = results[Dataset.SCHEMA]
        self.assertEqual(expected_schema, new_schema)

        # Check summary
        results = json.loads(self.controller.summary(
            dataset_id, select=self.controller.SELECT_ALL_FOR_SUMMARY))
        summary = results[column]['summary']
        self.assertFalse('count' in summary.keys())

        # set OLAP Type back
        new_olap_type = 'measure'
        expected_schema[column][OLAP_TYPE] = new_olap_type
        results = json.loads(self.controller.set_olap_type(
            dataset_id, column, new_olap_type))
        self.assertTrue(Datasets.SUCCESS in results.keys())

        # Check new schema
        results = json.loads(self.controller.info(dataset_id))
        new_schema = results[Dataset.SCHEMA]
        self.assertEqual(expected_schema, new_schema)

        # Check summary
        results = json.loads(self.controller.summary(
            dataset_id, select=self.controller.SELECT_ALL_FOR_SUMMARY))
        summary = results[column]['summary']
        self.assertTrue('count' in summary.keys())

    def test_reset(self):
        dataset_id = self._post_file()
        mock_uploaded_file = self._file_mock(self._file_path)

        result = json.loads(self.controller.reset(dataset_id,
                                                  csv_file=mock_uploaded_file))

        self.assertEqual(result[Dataset.ID], dataset_id)

        # test parse type as date correctly
        dframe = Dataset.find_one(result[Dataset.ID]).dframe()
        self.assertTrue(isinstance(dframe.submit_date[0], datetime))

        results = self._test_summary_built(result)
        self._test_summary_no_group(results)

########NEW FILE########
__FILENAME__ = test_datasets_edit
from pandas import Series
import simplejson as json

from bamboo.controllers.datasets import Datasets
from bamboo.models.dataset import Dataset
from bamboo.models.observation import Observation
from bamboo.tests.controllers.test_abstract_datasets import\
    TestAbstractDatasets


class TestDatasetsEdit(TestAbstractDatasets):

    def setUp(self):
        TestAbstractDatasets.setUp(self)

    def test_show_row(self):
        dataset_id = self._post_file()
        result = json.loads(self.controller.row_show(dataset_id, 0))

        self.assertTrue(isinstance(result, dict))
        self.assertEqual(9.0, result['amount'])

        result = json.loads(self.controller.row_show(dataset_id, "0"))

        self.assertTrue(isinstance(result, dict))
        self.assertEqual(9.0, result['amount'])

    def test_show_row_nonexistent_index(self):
        dataset_id = self._post_file()
        result = json.loads(self.controller.row_show(dataset_id, "90"))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Datasets.ERROR in result)

    def test_show_row_bad_index(self):
        dataset_id = self._post_file()
        result = json.loads(self.controller.row_show(dataset_id, "A"))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Datasets.ERROR in result)

    def test_delete_row(self):
        dataset_id = self._post_file()
        dataset = Dataset.find_one(dataset_id)
        index = 0
        expected_dframe = Dataset.find_one(
            dataset_id).dframe()[index + 1:].reset_index()
        del expected_dframe['index']

        results = json.loads(self.controller.row_delete(dataset_id, index))
        self.assertTrue(Datasets.SUCCESS in results.keys())

        dataset = Dataset.find_one(dataset_id)
        dframe = dataset.dframe()
        self.assertEqual(self.NUM_ROWS - 1, len(dframe))
        self._check_dframes_are_equal(expected_dframe, dframe)

        # check info updated
        info = dataset.info()
        self.assertEqual(self.NUM_ROWS - 1, info[Dataset.NUM_ROWS])

        # check that row is softly deleted
        all_observations = Observation.find(dataset, include_deleted=True)
        self.assertEqual(self.NUM_ROWS, len(all_observations))

    def test_delete_row_with_agg(self):
        amount_sum = 2007.5
        amount_sum_after = 1998.5
        index = 0

        self.dataset_id = self._post_file()
        self._post_calculations(formulae=['sum(amount)'])
        agg = self._test_aggregations()[0]
        self.assertEqual(agg['sum_amount_'], amount_sum)

        results = json.loads(
            self.controller.row_delete(self.dataset_id, index))
        self.assertTrue(Datasets.SUCCESS in results.keys())

        agg = self._test_aggregations()[0]
        self.assertEqual(agg['sum_amount_'], amount_sum_after)

    def test_delete_row_with_join(self):
        index = 0

        left_dataset_id = self._post_file()
        right_dataset_id = self._post_file('good_eats_aux.csv')
        on = 'food_type'
        results = json.loads(self.controller.join(
            left_dataset_id, right_dataset_id, on=on))
        joined_dataset_id = results[Dataset.ID]

        results = json.loads(self.controller.join(
            joined_dataset_id, right_dataset_id, on=on))
        joined_dataset_id2 = results[Dataset.ID]

        results = json.loads(
            self.controller.row_delete(left_dataset_id, index))
        self.assertTrue(Datasets.SUCCESS in results.keys())

        dframe = Dataset.find_one(joined_dataset_id).dframe(index=True)
        self.assertFalse(index in dframe['index'].tolist())

        dframe = Dataset.find_one(joined_dataset_id2).dframe(index=True)
        self.assertFalse(index in dframe['index'].tolist())

    def test_delete_row_with_merge(self):
        index = 0

        dataset_id1 = self._post_file()
        dataset_id2 = self._post_file()
        result = json.loads(self.controller.merge(
            dataset_ids=json.dumps([dataset_id1, dataset_id2])))
        merged_id = result[Dataset.ID]

        results = json.loads(
            self.controller.row_delete(dataset_id2, index))
        self.assertTrue(Datasets.SUCCESS in results.keys())

        results = json.loads(
            self.controller.row_delete(dataset_id1, index))
        self.assertTrue(Datasets.SUCCESS in results.keys())

        dframe = Dataset.find_one(merged_id).dframe(index=True)
        self.assertFalse(index in dframe['index'].tolist())
        self.assertFalse(index + self.NUM_ROWS in dframe['index'].tolist())

    def test_edit_row(self):
        dataset_id = self._post_file()
        index = 0
        update = {'amount': 10, 'food_type': 'breakfast'}
        expected_dframe = Dataset.find_one(dataset_id).dframe()
        expected_row = expected_dframe.ix[0].to_dict()
        expected_row.update(update)
        expected_dframe.ix[0] = Series(expected_row)

        results = json.loads(self.controller.row_update(dataset_id, index,
                                                        json.dumps(update)))
        self.assertTrue(Datasets.SUCCESS in results.keys())

        dataset = Dataset.find_one(dataset_id)
        dframe = dataset.dframe()
        self.assertEqual(self.NUM_ROWS, len(dframe))
        self._check_dframes_are_equal(expected_dframe, dframe)

        # check that previous row exists
        all_observations = Observation.find(dataset, include_deleted=True)
        self.assertEqual(self.NUM_ROWS + 1, len(all_observations))

    def test_edit_row_with_calculation(self):
        amount_before = 9
        amount_after = 10
        value = 5
        index = 0
        update = {'amount': amount_after, 'food_type': 'breakfast'}

        self.dataset_id = self._post_file()
        self._post_calculations(formulae=['amount + %s' % value])

        result = json.loads(self.controller.row_show(self.dataset_id, index))
        self.assertEqual(amount_before + value, result['amount___%s' % value])

        results = json.loads(self.controller.row_update(self.dataset_id, index,
                                                        json.dumps(update)))
        self.assertTrue(Datasets.SUCCESS in results.keys())

        result = json.loads(self.controller.row_show(self.dataset_id, index))
        self.assertEqual(amount_after + value, result['amount___%s' % value])

    def test_edit_row_with_agg(self):
        amount_sum = 2007.5
        amount_sum_after = 2008.5

        self.dataset_id = self._post_file()
        self._post_calculations(formulae=['sum(amount)'])
        agg = self._test_aggregations()[0]
        self.assertEqual(agg['sum_amount_'], amount_sum)

        index = 0
        update = {'amount': 10, 'food_type': 'breakfast'}
        results = json.loads(self.controller.row_update(self.dataset_id, index,
                                                        json.dumps(update)))
        self.assertTrue(Datasets.SUCCESS in results.keys())

        agg = self._test_aggregations()[0]
        self.assertEqual(agg['sum_amount_'], amount_sum_after)

    def test_edit_row_with_join(self):
        index = 0
        value = 10
        update = {'amount': value, 'food_type': 'breakfast'}

        left_dataset_id = self._post_file()
        right_dataset_id = self._post_file('good_eats_aux.csv')
        on = 'food_type'
        results = json.loads(self.controller.join(
            left_dataset_id, right_dataset_id, on=on))
        joined_dataset_id = results[Dataset.ID]

        results = json.loads(self.controller.join(
            joined_dataset_id, right_dataset_id, on=on))
        joined_dataset_id2 = results[Dataset.ID]

        results = json.loads(self.controller.row_update(left_dataset_id, index,
                                                        json.dumps(update)))
        self.assertTrue(Datasets.SUCCESS in results.keys())

        result = json.loads(self.controller.row_show(joined_dataset_id, 0))
        self.assertEqual(value, result['amount'])

        result = json.loads(self.controller.row_show(joined_dataset_id2, 0))
        self.assertEqual(value, result['amount'])

    def test_edit_row_with_join_invalid(self):
        index = 0
        update = {'food_type': 'deserts'}

        left_dataset_id = self._post_file()
        right_dataset_id = self._post_file('good_eats_aux.csv')
        num_rows_before = Dataset.find_one(right_dataset_id).num_rows
        on = 'food_type'
        json.loads(self.controller.join(
            left_dataset_id, right_dataset_id, on=on))

        results = json.loads(self.controller.row_update(
            right_dataset_id, index, json.dumps(update)))
        self.assertTrue(Datasets.SUCCESS in results.keys())

        dataset = Dataset.find_one(right_dataset_id)
        self.assertEqual(num_rows_before, dataset.num_rows)
        self.assertEqual(dataset.pending_updates, [])

    def test_edit_row_with_merge(self):
        index = 0
        value = 10
        update = {'amount': value, 'food_type': 'breakfast'}

        dataset_id1 = self._post_file()
        dataset_id2 = self._post_file()
        result = json.loads(self.controller.merge(
            dataset_ids=json.dumps([dataset_id1, dataset_id2])))
        merged_id = result[Dataset.ID]

        results = json.loads(self.controller.row_update(dataset_id1, index,
                                                        json.dumps(update)))
        self.assertTrue(Datasets.SUCCESS in results.keys())

        results = json.loads(self.controller.row_update(dataset_id2, index,
                                                        json.dumps(update)))
        self.assertTrue(Datasets.SUCCESS in results.keys())

        result = json.loads(self.controller.row_show(merged_id, index))
        self.assertEqual(value, result['amount'])

        result = json.loads(self.controller.row_show(merged_id, index +
                                                     self.NUM_ROWS))
        self.assertEqual(value, result['amount'])

########NEW FILE########
__FILENAME__ = test_datasets_from_schema
import simplejson as json

from bamboo.lib.schema_builder import SIMPLETYPE
from bamboo.models.dataset import Dataset
from bamboo.tests.controllers.test_abstract_datasets import\
    TestAbstractDatasets
from bamboo.tests.mock import MockUploadedFile


class TestDatasetsFromSchema(TestAbstractDatasets):

    def setUp(self):
        TestAbstractDatasets.setUp(self)

    def _upload_from_schema(self, file_name):
        schema = open('tests/fixtures/%s' % file_name)
        mock_uploaded_file = MockUploadedFile(schema)

        return json.loads(self.controller.create(schema=mock_uploaded_file))

    def _upload_good_eats_schema(self):
        result = self._upload_from_schema('good_eats.schema.json')
        self._test_summary_built(result)

    def test_create_from_schema(self):
        self._upload_good_eats_schema()
        results = json.loads(self.controller.show(self.dataset_id))

        self.assertTrue(isinstance(results, list))
        self.assertEqual(len(results), 0)

        results = json.loads(self.controller.info(self.dataset_id))

        self.assertTrue(isinstance(results, dict))
        self.assertTrue(Dataset.SCHEMA in results.keys())
        self.assertTrue(Dataset.NUM_ROWS in results.keys())
        self.assertEqual(results[Dataset.NUM_ROWS], 0)
        self.assertTrue(Dataset.NUM_COLUMNS in results.keys())
        self.assertEqual(results[Dataset.NUM_COLUMNS], self.NUM_COLS)

    def test_create_from_schema_and_update(self):
        self._upload_good_eats_schema()
        results = json.loads(self.controller.show(self.dataset_id))

        self.assertFalse(len(results))

        dataset = Dataset.find_one(self.dataset_id)

        self.assertEqual(dataset.num_rows, 0)

        old_schema = dataset.schema
        self._put_row_updates()
        results = json.loads(self.controller.show(self.dataset_id))

        self.assertTrue(len(results))

        for result in results:
            self.assertTrue(isinstance(result, dict))
            self.assertTrue(len(result.keys()))

        dataset = Dataset.find_one(self.dataset_id)

        self.assertEqual(dataset.num_rows, 1)

        new_schema = dataset.schema

        self.assertEqual(set(old_schema.keys()), set(new_schema.keys()))

        for column in new_schema.keys():
            if new_schema.cardinality(column):
                self.assertEqual(new_schema.cardinality(column), 1)

    def test_create_one_from_schema_and_join(self):
        self._upload_good_eats_schema()
        left_dataset_id = self.dataset_id
        right_dataset_id = self._post_file('good_eats_aux.csv')

        on = 'food_type'
        dataset_id_tuples = [
            (left_dataset_id, right_dataset_id),
            (right_dataset_id, left_dataset_id),
        ]

        for dataset_ids in dataset_id_tuples:
            result = json.loads(self.controller.join(*dataset_ids, on=on))
            expected_schema_keys = set(sum([
                Dataset.find_one(dataset_id).schema.keys()
                for dataset_id in dataset_ids], []))

            self.assertTrue(isinstance(result, dict))
            self.assertTrue(Dataset.ID in result)
            merge_dataset_id = result[Dataset.ID]
            dataset = Dataset.find_one(merge_dataset_id)
            self.assertEqual(dataset.num_rows, 0)
            self.assertEqual(dataset.num_columns, len(expected_schema_keys))
            schema_keys = set(dataset.schema.keys())
            self.assertEqual(schema_keys, expected_schema_keys)

    def test_create_two_from_schema_and_join(self):
        self._upload_good_eats_schema()
        left_dataset_id = self.dataset_id

        schema = open('tests/fixtures/good_eats_aux.schema.json')
        mock_uploaded_file = MockUploadedFile(schema)
        result = json.loads(
            self.controller.create(schema=mock_uploaded_file))
        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)
        right_dataset_id = result[Dataset.ID]

        on = 'food_type'
        dataset_id_tuples = [
            (left_dataset_id, right_dataset_id),
            (right_dataset_id, left_dataset_id),
        ]

        for dataset_ids in dataset_id_tuples:
            result = json.loads(self.controller.join(*dataset_ids, on=on))
            expected_schema_keys = set(sum([
                Dataset.find_one(dataset_id).schema.keys()
                for dataset_id in dataset_ids], []))

            self.assertTrue(isinstance(result, dict))
            self.assertTrue(Dataset.ID in result)
            merge_dataset_id = result[Dataset.ID]
            dataset = Dataset.find_one(merge_dataset_id)
            self.assertEqual(dataset.num_rows, 0)
            self.assertEqual(dataset.num_columns, len(expected_schema_keys))
            schema_keys = set(dataset.schema.keys())
            self.assertEqual(schema_keys, expected_schema_keys)

    def test_create_two_from_schema_and_join_and_update_vacuous_rhs(self):
        self._upload_good_eats_schema()
        left_dataset_id = self.dataset_id

        schema = open('tests/fixtures/good_eats_aux.schema.json')
        mock_uploaded_file = MockUploadedFile(schema)
        result = json.loads(
            self.controller.create(schema=mock_uploaded_file))
        right_dataset_id = result[Dataset.ID]

        on = 'food_type'
        result = json.loads(self.controller.join(
            left_dataset_id, right_dataset_id, on=on))
        merged_dataset_id = self.dataset_id = result[Dataset.ID]

        num_rows = 0
        results = json.loads(self.controller.show(merged_dataset_id))
        self.assertEqual(num_rows, len(results))

        num_rows += 1
        self._put_row_updates()
        results = json.loads(self.controller.show(merged_dataset_id))
        self.assertEqual(num_rows, len(results))

        num_rows += 1
        self._put_row_updates(left_dataset_id)
        results = json.loads(self.controller.show(merged_dataset_id))
        self.assertEqual(num_rows, len(results))

        self._put_row_updates(right_dataset_id)
        results = json.loads(self.controller.show(merged_dataset_id))
        self.assertEqual(num_rows, len(results))

    def test_create_two_from_schema_and_join_and_update_child_rhs(self):
        self._upload_good_eats_schema()
        left_dataset_id = self.dataset_id

        result = self._upload_from_schema('good_eats_aux.schema.json')
        right_dataset_id = result[Dataset.ID]

        on = 'food_type'
        result = json.loads(self.controller.join(
            left_dataset_id, right_dataset_id, on=on))
        merged_dataset_id = self.dataset_id = result[Dataset.ID]

        num_rows = 0
        results = json.loads(self.controller.show(merged_dataset_id))
        self.assertEqual(num_rows, len(results))

        num_rows += 1
        self._put_row_updates(file_name='good_eats_update_bg.json')
        results = json.loads(self.controller.show(merged_dataset_id))
        self.assertEqual(num_rows, len(results))

        self._put_row_updates(right_dataset_id,
                              file_name='good_eats_aux_update.json')
        results = json.loads(self.controller.show(merged_dataset_id))
        self.assertEqual(num_rows, len(results))

    def test_create_two_from_schema_and_join_and_update_lhs_rhs(self):
        self._upload_good_eats_schema()
        left_dataset_id = self.dataset_id

        result = self._upload_from_schema('good_eats_aux.schema.json')
        right_dataset_id = result[Dataset.ID]

        on = 'food_type'
        result = json.loads(self.controller.join(
            left_dataset_id, right_dataset_id, on=on))
        merged_dataset_id = self.dataset_id = result[Dataset.ID]

        num_rows = 0
        results = json.loads(self.controller.show(merged_dataset_id))
        self.assertEqual(num_rows, len(results))

        num_rows += 1
        self._put_row_updates(left_dataset_id,
                              file_name='good_eats_update_bg.json')
        results = json.loads(self.controller.show(merged_dataset_id))
        self.assertEqual(num_rows, len(results))

        self.dataset_id = right_dataset_id
        self._put_row_updates(right_dataset_id,
                              file_name='good_eats_aux_update.json')
        results = json.loads(self.controller.show(merged_dataset_id))
        self.assertEqual(num_rows, len(results))
        result = results[0]
        self.assertTrue('code' in result.keys())
        self.assertFalse(result['code'] is None)

    def test_schema_with_boolean_column(self):
        mock_csv_file = self._file_mock('wp_data.csv', add_prefix=True)
        mock_schema_file = self._file_mock(
            'wp_data.schema.json', add_prefix=True)
        result = json.loads(self.controller.create(csv_file=mock_csv_file,
                                                   schema=mock_schema_file))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)

        dataset = Dataset.find_one(result[Dataset.ID])
        mock_schema_file.file.seek(0)

        for column, schema in json.loads(mock_schema_file.file.read()).items():
            self.assertEqual(schema[SIMPLETYPE],
                             dataset.schema[column][SIMPLETYPE])

########NEW FILE########
__FILENAME__ = test_datasets_join
import simplejson as json

from bamboo.controllers.datasets import Datasets
from bamboo.models.dataset import Dataset
from bamboo.tests.controllers.test_abstract_datasets import\
    TestAbstractDatasets


class TestDatasets(TestAbstractDatasets):

    def setUp(self):
        TestAbstractDatasets.setUp(self)

    def test_join_datasets(self):
        left_dataset_id = self._post_file()
        right_dataset_id = self._post_file('good_eats_aux.csv')
        on = 'food_type'
        results = json.loads(self.controller.join(
            left_dataset_id, right_dataset_id, on=on))

        self.assertTrue(Datasets.SUCCESS in results.keys())
        self.assertTrue(Dataset.ID in results.keys())

        joined_dataset_id = results[Dataset.ID]
        data = json.loads(self.controller.show(joined_dataset_id))

        self.assertTrue('code' in data[0].keys())

        left_dataset = Dataset.find_one(left_dataset_id)
        right_dataset = Dataset.find_one(right_dataset_id)

        self.assertEqual([('right', right_dataset_id, on, joined_dataset_id)],
                         left_dataset.joined_dataset_ids)
        self.assertEqual([('left', left_dataset_id, on, joined_dataset_id)],
                         right_dataset.joined_dataset_ids)

    def test_join_datasets_different_columns(self):
        left_dataset_id = self._post_file()
        right_dataset_id = self._post_file('good_eats_aux_join.csv')
        on_lhs = 'food_type'
        on_rhs = 'also_food_type'
        on = '%s,%s' % (on_lhs, on_rhs)
        results = json.loads(self.controller.join(
            left_dataset_id, right_dataset_id, on=on))

        self.assertTrue(Datasets.SUCCESS in results.keys())
        self.assertTrue(Dataset.ID in results.keys())

        joined_dataset_id = results[Dataset.ID]
        data = json.loads(self.controller.show(joined_dataset_id))

        self.assertTrue('code' in data[0].keys())

        left_dataset = Dataset.find_one(left_dataset_id)
        right_dataset = Dataset.find_one(right_dataset_id)

        self.assertEqual([('right', right_dataset_id, on, joined_dataset_id)],
                         left_dataset.joined_dataset_ids)
        self.assertEqual([('left', left_dataset_id, on, joined_dataset_id)],
                         right_dataset.joined_dataset_ids)

    def test_join_datasets_non_unique_rhs(self):
        left_dataset_id = self._post_file()
        right_dataset_id = self._post_file()
        results = json.loads(self.controller.join(
            left_dataset_id, right_dataset_id, on='food_type'))

        self.assertTrue(Datasets.ERROR in results.keys())
        self.assertTrue('right' in results[Datasets.ERROR])
        self.assertTrue('not unique' in results[Datasets.ERROR])

    def test_join_datasets_on_col_not_in_lhs(self):
        left_dataset_id = self._post_file()
        right_dataset_id = self._post_file('good_eats_aux.csv')
        on = 'code'
        results = json.loads(self.controller.join(
            left_dataset_id, right_dataset_id, on=on))

        self.assertTrue(Datasets.ERROR in results.keys())
        self.assertTrue('left' in results[Datasets.ERROR])

    def test_join_datasets_on_col_not_in_rhs(self):
        left_dataset_id = self._post_file()
        right_dataset_id = self._post_file('good_eats_aux.csv')
        on = 'rating'
        results = json.loads(self.controller.join(
            left_dataset_id, right_dataset_id, on=on))

        self.assertTrue(Datasets.ERROR in results.keys())
        self.assertTrue('right' in results[Datasets.ERROR])

    def test_join_datasets_overlap(self):
        left_dataset_id = self._post_file('good_eats.csv')
        right_dataset_id = self._post_file('good_eats.csv')
        on = 'food_photo'

        results = json.loads(self.controller.join(
            left_dataset_id, right_dataset_id, on=on))

        self.assertTrue(Datasets.SUCCESS in results.keys())
        self.assertTrue(Dataset.ID in results.keys())

        joined_dataset_id = results[Dataset.ID]
        data = json.loads(self.controller.show(joined_dataset_id))
        keys = data[0].keys()

        for column in Dataset.find_one(left_dataset_id).dframe().columns:
            if column != on:
                self.assertTrue('%s_x' % column in keys)
                self.assertTrue('%s_y' % column in keys)

########NEW FILE########
__FILENAME__ = test_datasets_merge
from time import sleep

from pandas import concat
import simplejson as json

from bamboo.core.frame import PARENT_DATASET_ID, RESERVED_KEYS
from bamboo.models.dataset import Dataset
from bamboo.tests.controllers.test_abstract_datasets import\
    TestAbstractDatasets
from bamboo.tests.decorators import requires_async


class TestDatasetsMerge(TestAbstractDatasets):

    def _post_merge(self, dataset_ids):
        dataset_id1, dataset_id2 = dataset_ids
        return json.loads(self.controller.merge(
            dataset_ids=json.dumps(dataset_ids),
            mapping=json.dumps({
                dataset_id1: {
                    "food_type": "food_type_2",
                },
                dataset_id2: {
                    "code": "comments",
                    "food_type": "food_type_2",
                },
            })))[Dataset.ID]

    @requires_async
    def test_merge_datasets_0_not_enough(self):
        result = json.loads(self.controller.merge(dataset_ids=json.dumps([])))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(self.controller.ERROR in result)

    @requires_async
    def test_merge_datasets_1_not_enough(self):
        dataset_id = self._post_file()
        result = json.loads(self.controller.merge(
            dataset_ids=json.dumps([dataset_id])))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(self.controller.ERROR in result)

    @requires_async
    def test_merge_datasets_must_exist(self):
        dataset_id = self._post_file()
        result = json.loads(self.controller.merge(
            dataset_ids=json.dumps([dataset_id, 0000])))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(self.controller.ERROR in result)

    def test_merge_datasets(self):
        dataset_id1 = self._post_file()
        dataset_id2 = self._post_file()
        result = json.loads(self.controller.merge(
            dataset_ids=json.dumps([dataset_id1, dataset_id2])))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)

        datasets = [Dataset.find_one(dataset_id)
                    for dataset_id in [dataset_id1, dataset_id2]]

        for dataset in datasets:
            self.assertTrue(result[Dataset.ID] in dataset.merged_dataset_ids)

        dframe1 = datasets[0].dframe()
        merged_dataset = Dataset.find_one(result[Dataset.ID])
        merged_dframe = merged_dataset.dframe(keep_parent_ids=True)

        for _, row in merged_dframe.iterrows():
            self.assertTrue(PARENT_DATASET_ID in row.keys())

        merged_dframe = merged_dataset.dframe()

        self.assertEqual(len(merged_dframe), 2 * len(dframe1))

        expected_dframe = concat([dframe1, dframe1],
                                 ignore_index=True)

        self.assertEqual(list(merged_dframe.columns),
                         list(expected_dframe.columns))

        self._check_dframes_are_equal(merged_dframe, expected_dframe)

    @requires_async
    def test_merge_datasets_async(self):
        dataset_id1 = self._post_file()
        dataset_id2 = self._post_file()

        self.assertEqual(
            Dataset.find_one(dataset_id1).state,
            Dataset.STATE_PENDING)
        self.assertEqual(
            Dataset.find_one(dataset_id2).state,
            Dataset.STATE_PENDING)

        result = json.loads(self.controller.merge(
            dataset_ids=json.dumps([dataset_id1, dataset_id2])))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)

        merged_id = result[Dataset.ID]

        while True:
            datasets = [Dataset.find_one(dataset_id)
                        for dataset_id in [merged_id, dataset_id1, dataset_id2]
                        ]

            if all([dataset.record_ready for dataset in datasets]) and all(
                    [d.merged_dataset_ids for d in datasets[1:]]):
                break

            sleep(self.SLEEP_DELAY)

        datasets = [Dataset.find_one(dataset_id)
                    for dataset_id in [dataset_id1, dataset_id2]]

        for dataset in datasets:
            self.assertTrue(merged_id in dataset.merged_dataset_ids)

        dframe1 = datasets[0].dframe()
        merged_dataset = Dataset.find_one(merged_id)
        merged_dframe = merged_dataset.dframe(keep_parent_ids=True)

        for _, row in merged_dframe.iterrows():
            self.assertTrue(PARENT_DATASET_ID in row.keys())

        merged_dframe = merged_dataset.dframe()

        self.assertEqual(len(merged_dframe), 2 * len(dframe1))

        expected_dframe = concat([dframe1, dframe1],
                                 ignore_index=True)

        self.assertEqual(list(merged_dframe.columns),
                         list(expected_dframe.columns))

        self._check_dframes_are_equal(merged_dframe, expected_dframe)

    @requires_async
    def test_merge_datasets_add_calc_async(self):
        dataset_id1 = self._post_file('good_eats_large.csv')
        dataset_id2 = self._post_file('good_eats_large.csv')
        result = json.loads(self.controller.merge(
            dataset_ids=json.dumps([dataset_id1, dataset_id2])))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)

        self.dataset_id = result[Dataset.ID]
        self.schema = json.loads(
            self.controller.info(self.dataset_id))[Dataset.SCHEMA]

        self._post_calculations(['amount < 4'])

    def test_merge_datasets_no_reserved_keys(self):
        dataset_id1 = self._post_file()
        dataset_id2 = self._post_file()
        result = json.loads(self.controller.merge(
            dataset_ids=json.dumps([dataset_id1, dataset_id2])))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)

        response = json.loads(self.controller.show(result[Dataset.ID]))
        row_keys = sum([row.keys() for row in response], [])

        for reserved_key in RESERVED_KEYS:
            self.assertFalse(reserved_key in row_keys)

    def test_merge_with_map(self):
        dataset_id1 = self._post_file()
        dataset_id2 = self._post_file('good_eats_aux.csv')
        merged_dataset_id = self._post_merge([dataset_id1, dataset_id2])

        expected_columns = Dataset.find_one(
            dataset_id1).dframe().columns.tolist()
        expected_columns.remove("food_type")
        expected_columns.append("food_type_2")
        expected_columns = set(expected_columns)

        merged_dataset = Dataset.find_one(merged_dataset_id)
        new_columns = set(merged_dataset.dframe().columns)

        self.assertEquals(expected_columns, new_columns)

    def test_merge_with_map_update(self):
        dataset_id1 = self._post_file()
        dataset_id2 = self._post_file('good_eats_aux.csv')
        merged_dataset_id = self._post_merge([dataset_id1, dataset_id2])

        original_ds2 = json.loads(self.controller.show(dataset_id2))
        original_length = len(original_ds2)
        original_merge = json.loads(self.controller.show(merged_dataset_id))
        original_merge_length = len(original_merge)

        self._put_row_updates(dataset_id2, 'good_eats_aux_update.json')
        response = json.loads(self.controller.show(dataset_id2))
        new_length = len(response)

        for new_row in response:
            if new_row not in original_ds2:
                break

        response = json.loads(self.controller.show(merged_dataset_id))

        for new_merge_row in response:
            if new_merge_row not in original_merge:
                break

        new_merge_length = len(response)

        self.assertEqual(original_length + 1, new_length)
        self.assertEqual(original_merge_length + 1, new_merge_length)
        self.assertEqual(new_row['food_type'], new_merge_row['food_type_2'])
        self.assertEqual(new_row['code'], new_merge_row['comments'])

########NEW FILE########
__FILENAME__ = test_datasets_plot
import simplejson as json

from bamboo.lib.query_args import QueryArgs
from bamboo.models.dataset import Dataset
from bamboo.tests.controllers.test_abstract_datasets import\
    TestAbstractDatasets


class TestDatasets(TestAbstractDatasets):

    def setUp(self):
        TestAbstractDatasets.setUp(self)
        self.dataset_id = self._post_file('water_points.csv')
        self.dataset = Dataset.find_one(self.dataset_id)

    def __test_result(self, result, dframe):
        for column in dframe.columns:
            for i, v in dframe[column].iteritems():
                v = str(v)[0:5]
                self.assertTrue(v in result, v)

    def test_plot(self):
        result = self.controller.plot(self.dataset_id)

        dframe = self.dataset.dframe(
            query_args=QueryArgs(select=self.dataset.schema.numerics_select))
        dframe = dframe.dropna()

        self.__test_result(result, dframe)

    def test_plot_select_none(self):
        column = 'acreage'
        select = json.dumps({column: 1})
        result = self.controller.plot(self.dataset_id, select=select)
        result = json.loads(result)

        self.assertTrue(column in result[self.controller.ERROR])

    def test_plot_select(self):
        column = 'community_pop'
        select = {column: 1}
        result = self.controller.plot(self.dataset_id,
                                      select=json.dumps(select))

        dframe = self.dataset.dframe(QueryArgs(select=select))
        self.__test_result(result, dframe)

    def test_plot_index(self):
        dataset_id = self._post_file()
        dataset = Dataset.find_one(dataset_id)

        column = 'amount'
        select = {column: 1}
        result = self.controller.plot(dataset_id, select=json.dumps(select),
                                      index='submit_date')
        dframe = dataset.dframe()

        dframe = self.dataset.dframe(QueryArgs(select=select))
        self.__test_result(result, dframe)

    def test_plot_type(self):
        column = 'community_pop'
        select = json.dumps({column: 1})
        plot_types = ['area', 'bar', 'line', 'scatterplot', 'stack']

        for plot_type in plot_types:
            result = self.controller.plot(self.dataset_id, select=select,
                                          plot_type=plot_type)
            dframe = self.dataset.dframe()

            for i, amount in dframe[column].iteritems():
                self.assertTrue(str(amount) in result)

    def test_plot_invalid_group(self):
        column = 'bongo'
        result = self.controller.plot(self.dataset_id, group=column)
        result = json.loads(result)

        self.assertTrue(column in result[self.controller.ERROR])

    def test_plot_invalid_index(self):
        column = 'bongo'
        result = self.controller.plot(self.dataset_id, index=column)
        result = json.loads(result)

        self.assertTrue(column in result[self.controller.ERROR])

    def test_plot_output_vega(self):
        result = self.controller.plot(self.dataset_id, vega=True)
        result = json.loads(result)

        self.assertTrue(isinstance(result, dict))

    def test_plot_output_height_width(self):
        result = self.controller.plot(self.dataset_id, height=200, width=300)
        result = result

        self.assertTrue('200' in result)
        self.assertTrue('300' in result)

########NEW FILE########
__FILENAME__ = test_datasets_post_update
from time import sleep

import simplejson as json

from bamboo.controllers.datasets import Datasets
from bamboo.lib.jsontools import df_to_jsondict
from bamboo.models.dataset import Dataset
from bamboo.tests.controllers.test_abstract_datasets import\
    TestAbstractDatasets
from bamboo.tests.decorators import requires_async


class TestDatasetsPostUpdate(TestAbstractDatasets):

    def setUp(self):
        TestAbstractDatasets.setUp(self)
        self._file_name_with_slashes = 'good_eats_with_slashes.csv'

    def _check_schema(self, results):
        schema = self._load_schema()

        for result in results:
            for column in schema.keys():
                self.assertTrue(
                    column in result.keys(),
                    "column %s not in %s" % (column, result.keys()))

    def test_dataset_id_update_bad_dataset_id(self):
        result = json.loads(self.controller.update(dataset_id=111,
                                                   update=None))
        assert(Datasets.ERROR in result)

    @requires_async
    def test_dataset_update_pending(self):
        dataset_id = self._post_file(self._file_name_with_slashes)
        dataset = Dataset.find_one(dataset_id)

        self.assertEqual(dataset.state, Dataset.STATE_PENDING)

        self._put_row_updates(dataset_id)

        while True:
            dataset.reload()

            if not len(dataset.pending_updates):
                break

            sleep(self.SLEEP_DELAY)

        results = json.loads(self.controller.show(dataset_id))
        num_rows_after_update = len(results)

        self.assertEqual(num_rows_after_update, self.NUM_ROWS + 1)

    def test_dataset_update(self):
        self.dataset_id = self._post_file(self._file_name_with_slashes)
        self._post_calculations(self.default_formulae)
        self._put_row_updates()
        results = json.loads(self.controller.show(self.dataset_id))
        num_rows_after_update = len(results)

        self.assertEqual(num_rows_after_update, self.NUM_ROWS + 1)
        self._check_schema(results)

        # ensure new row is in results
        self.assertTrue(self._update_values in results)

    def test_dataset_update_unicode(self):
        num_rows_before_update = 1
        data = [
            {u'\u03c7': u'\u03b1', u'\u03c8': u'\u03b2'},
            {u'\u03c7': u'\u03b3', u'\u03c8': u'\u03b4'},
        ]
        self.dataset_id = self._post_file('unicode.csv')
        self._put_row_updates(file_name='unicode.json')
        results = json.loads(self.controller.show(self.dataset_id))
        num_rows_after_update = len(results)

        self.assertEqual(num_rows_after_update, num_rows_before_update + 1)
        self._check_schema(results)

        dataset = Dataset.find_one(self.dataset_id)
        self.assertEqual(data, df_to_jsondict(dataset.dframe()))

    def test_dataset_update_with_slugs(self):
        self.dataset_id = self._post_file(self._file_name_with_slashes)
        self._post_calculations(self.default_formulae)
        self._put_row_updates(file_name='good_eats_update_slugs.json')
        results = json.loads(self.controller.show(self.dataset_id))
        num_rows_after_update = len(results)

        self.assertEqual(num_rows_after_update, self.NUM_ROWS + 1)
        self._check_schema(results)

        # ensure new row is in results
        self.assertTrue(self._update_values in results)

    def test_update_multiple(self):
        dataset_id = self._post_file(self._file_name_with_slashes)
        num_rows = len(json.loads(self.controller.show(dataset_id)))
        num_update_rows = 2
        self._put_row_updates(dataset_id=dataset_id,
                              file_name='good_eats_update_multiple.json')
        results = json.loads(self.controller.show(dataset_id))
        num_rows_after_update = len(results)

        self.assertEqual(num_rows_after_update, num_rows + num_update_rows)

    def test_update_with_aggregation(self):
        self.dataset_id = self._post_file()
        self._post_calculations(
            formulae=self.default_formulae + ['sum(amount)'])
        num_rows = len(json.loads(self.controller.show(self.dataset_id)))
        self._put_row_updates()
        results = json.loads(self.controller.show(self.dataset_id))
        num_rows_after_update = len(results)

        self.assertEqual(num_rows_after_update, num_rows + 1)

        schema = self._load_schema()

        for result in results:
            for column in schema.keys():
                self.assertTrue(
                    column in result.keys(),
                    "column %s not in %s" % (column, result.keys()))

        self._test_aggregations()

    def test_info_after_row_update(self):
        dataset_id = self._post_file()
        self._put_row_updates(dataset_id)
        results = json.loads(self.controller.info(dataset_id))
        self.assertEqual(results[Dataset.NUM_ROWS], self.NUM_ROWS + 1)

    def test_update_diff_schema(self):
        dataset_id = self._post_file()
        dataset = Dataset.find_one(dataset_id)

        column = 'amount'
        update = json.dumps({column: '2'})

        expected_col_schema = dataset.schema[column]

        self.controller.update(dataset_id=dataset_id, update=update)
        dataset = Dataset.find_one(dataset_id)

        self.assertEqual(dataset.num_rows, self.NUM_ROWS + 1)
        self.assertEqual(expected_col_schema, dataset.schema[column])

    def test_update_diff_schema_unconvertable(self):
        dataset_id = self._post_file()
        dataset = Dataset.find_one(dataset_id)

        column = 'amount'
        update = json.dumps({column: 'a'})

        expected_col_schema = dataset.schema[column]

        result = json.loads(self.controller.update(dataset_id=dataset_id,
                                                   update=update))
        dataset = Dataset.find_one(dataset_id)

        # the update is rejected
        self.assertTrue(Datasets.ERROR in result)
        self.assertEqual(dataset.num_rows, self.NUM_ROWS)
        self.assertEqual(expected_col_schema, dataset.schema[column])

    @requires_async
    def test_update_diff_schema_unconvertable_async(self):
        dataset_id = self._post_file()
        dataset = self._wait_for_dataset_state(dataset_id)

        column = 'amount'
        update = json.dumps({column: 'a'})

        expected_col_schema = dataset.schema[column]

        result = json.loads(self.controller.update(dataset_id=dataset_id,
                                                   update=update))
        dataset = Dataset.find_one(dataset_id)

        # the update is rejected
        self.assertTrue(Datasets.ERROR in result)
        self.assertEqual(dataset.num_rows, self.NUM_ROWS)
        self.assertEqual(expected_col_schema, dataset.schema[column])

    def test_index_on_update(self):
        self.dataset_id = self._post_file(self._file_name_with_slashes)
        self._put_row_updates()
        results = json.loads(self.controller.show(self.dataset_id, index=True))

        for i, row in enumerate(results):
            self.assertEqual(i, row['index'])

########NEW FILE########
__FILENAME__ = test_datasets_summary
from base64 import b64encode

import simplejson as json

from bamboo.lib.mongo import ILLEGAL_VALUES
from bamboo.controllers.datasets import Datasets
from bamboo.core.summary import SUMMARY
from bamboo.models.dataset import Dataset
from bamboo.tests.controllers.test_abstract_datasets import\
    TestAbstractDatasets
from bamboo.tests.decorators import requires_async


class TestDatasetsSummary(TestAbstractDatasets):

    def setUp(self):
        TestAbstractDatasets.setUp(self)

    def test_summary(self):
        dataset_id = self._post_file()
        results = self.controller.summary(
            dataset_id, select=self.controller.SELECT_ALL_FOR_SUMMARY)
        results = self._test_summary_results(results)
        self._test_summary_no_group(results, dataset_id)

    @requires_async
    def test_summary_async(self):
        dataset_id = self._post_file()
        results = self.controller.summary(
            dataset_id, select=self.controller.SELECT_ALL_FOR_SUMMARY)
        dataset = Dataset.find_one(dataset_id)

        self.assertEqual(dataset.state, Dataset.STATE_PENDING)

        results = self._test_summary_results(results)

        self.assertTrue(Datasets.ERROR in results.keys())
        self.assertTrue('not finished' in results[Datasets.ERROR])

    def test_summary_restrict_by_cardinality(self):
        dataset_id = self._post_file('good_eats_huge.csv')
        results = self.controller.summary(
            dataset_id, select=self.controller.SELECT_ALL_FOR_SUMMARY)
        results = self._test_summary_results(results)

        # food_type has unique greater than the limit in this csv
        self.assertEqual(len(results.keys()), self.NUM_COLS - 1)
        self.assertFalse('food_type' in results.keys())

    def test_summary_illegal_keys(self):
        dataset_id = self._post_file(file_name='good_eats_illegal_keys.csv')
        results = self.controller.summary(
            dataset_id, select=self.controller.SELECT_ALL_FOR_SUMMARY)

        results = self._test_summary_results(results)

    def test_summary_decode_illegal_keys(self):
        dataset_id = self._post_file('good_eats_illegal_keys.csv')
        summaries = json.loads(self.controller.summary(
            dataset_id, select=self.controller.SELECT_ALL_FOR_SUMMARY))

        encoded_values = [b64encode(value) for value in ILLEGAL_VALUES]

        for column, summary in summaries.iteritems():
            # check the column names
            for encoded_value in encoded_values:
                self.assertFalse(encoded_value in column, '%s in %s' %
                                 (encoded_value, column))
            # check in "summary" for encoded keys (possibly from data)
            for key in summary.values()[0].keys():
                for encoded_value in encoded_values:
                    self.assertFalse(encoded_value in key, '%s in %s' %
                                     (encoded_value, key))

    def test_summary_unicode(self):
        file_name = 'unicode.csv'
        dataset_id = self._post_file(file_name=file_name)
        results = self.controller.summary(
            dataset_id, select=self.controller.SELECT_ALL_FOR_SUMMARY)
        results = self._test_summary_results(results)
        columns = [col for col in
                   self.get_data(file_name).columns.tolist()]
        summary_keys = results.keys()
        for column in columns:
            self.assertTrue(column in summary_keys)

    def test_summary_no_select(self):
        dataset_id = self._post_file()
        results = json.loads(self.controller.summary(dataset_id))

        self.assertTrue(Datasets.ERROR in results.keys())

    def test_summary_with_query(self):
        dataset_id = self._post_file()
        # (sic)
        query_column = 'rating'
        results = self.controller.summary(
            dataset_id,
            query='{"%s": "delectible"}' % query_column,
            select=self.controller.SELECT_ALL_FOR_SUMMARY)

        results = self._test_summary_results(results)
        # ensure only returned results for this query column
        self.assertEqual(len(results[query_column][SUMMARY].keys()), 1)
        self._test_summary_no_group(results, dataset_id)

    def test_summary_with_group(self):
        dataset_id = self._post_file()
        groups = [
            ('rating', ['delectible', 'epic_eat']),
            ('amount', []),
        ]

        for group, column_values in groups:
            json_results = self.controller.summary(
                dataset_id,
                group=group,
                select=self.controller.SELECT_ALL_FOR_SUMMARY)
            results = self._test_summary_results(json_results)
            result_keys = results.keys()

            if len(column_values):
                self.assertTrue(group in result_keys, 'group: %s in: %s'
                                % (group, result_keys))
                self.assertEqual(column_values, results[group].keys())

                for column_value in column_values:
                    self._test_summary_no_group(
                        results[group][column_value],
                        dataset_id=dataset_id,
                        group=group)
            else:
                self.assertFalse(group in results.keys())
                self.assertTrue(Datasets.ERROR in results.keys())

    def test_summary_with_select_as_list(self):
        dataset_id = self._post_file()

        json_results = self.controller.summary(
            dataset_id,
            select=json.dumps('[]'))

        results = self._test_summary_results(json_results)
        self.assertTrue(Datasets.ERROR in results.keys())
        self.assertTrue('must be a' in results[Datasets.ERROR])

    def test_summary_with_group_select(self):
        dataset_id = self._post_file()
        group = 'food_type'
        json_select = {'rating': 1}

        json_results = self.controller.summary(
            dataset_id,
            group=group,
            select=json.dumps(json_select))

        results = self._test_summary_results(json_results)

        self.assertTrue(group in results.keys())
        for summary in results[group].values():
            self.assertTrue(len(summary.keys()), 1)

    def test_summary_with_multigroup(self):
        dataset_id = self._post_file()
        group_columns = 'rating,food_type'

        results = self.controller.summary(
            dataset_id,
            group=group_columns,
            select=self.controller.SELECT_ALL_FOR_SUMMARY)

        results = self._test_summary_results(results)

        self.assertFalse(Datasets.ERROR in results.keys())
        self.assertTrue(group_columns in results.keys())
        # for split
        dataset = Dataset()
        self.assertEqual(
            len(dataset.split_groups(results[group_columns].keys()[0])),
            len(dataset.split_groups(group_columns)))

    def test_summary_with_multigroup_flat(self):
        dataset_id = self._post_file()
        col1 = 'rating'
        col1_values = ['delectible', 'epic_eat']
        col2 = 'food_type'
        group_columns = '%s,%s' % (col1, col2)

        results = json.loads(self.controller.summary(
            dataset_id,
            group=group_columns,
            select=self.controller.SELECT_ALL_FOR_SUMMARY,
            flat=True))

        self.assertTrue(isinstance(results, list))

        for i in results:
            self.assertTrue(i[col1] in col1_values)
            self.assertTrue(col2 in i.keys())

    def test_summary_multigroup_noncat_group(self):
        dataset_id = self._post_file()
        group_columns = 'rating,amount'

        results = self.controller.summary(
            dataset_id,
            group=group_columns,
            select=self.controller.SELECT_ALL_FOR_SUMMARY)

        results = self._test_summary_results(results)
        self.assertTrue(Datasets.ERROR in results.keys())

    def test_summary_nonexistent_group(self):
        dataset_id = self._post_file()
        group_columns = 'bongo'

        results = self.controller.summary(
            dataset_id,
            group=group_columns,
            select=self.controller.SELECT_ALL_FOR_SUMMARY)

        results = self._test_summary_results(results)
        self.assertTrue('not a column' in results[Datasets.ERROR])

    def test_summary_with_group_and_query(self):
        dataset_id = self._post_file()
        query_column = 'rating'

        results = self.controller.summary(
            dataset_id,
            group='rating',
            query='{"%s": "delectible"}' % query_column,
            select=self.controller.SELECT_ALL_FOR_SUMMARY)

        results = self._test_summary_results(results)
        self.assertEqual(len(results[query_column].keys()), 1)

########NEW FILE########
__FILENAME__ = test_datasets_ts_functions
import simplejson as json

from bamboo.controllers.datasets import Datasets
from bamboo.tests.controllers.test_abstract_datasets import\
    TestAbstractDatasets


class TestDatasetsTsFunctions(TestAbstractDatasets):

    def setUp(self):
        TestAbstractDatasets.setUp(self)

    def __build_resample_result(self, query=None):
        dataset_id = self._post_file('good_eats.csv')
        date_column = 'submit_date'
        interval = 'W'
        results = json.loads(self.controller.resample(
            dataset_id, date_column, interval, query=query))

        self.assertTrue(isinstance(results, list))

        return [date_column, results]

    def __check_interval(self, date_column, results):
        last_date_time = None

        for row in results:
            new_date_time = row[date_column]['$date']

            if last_date_time:
                self.assertEqual(604800000, new_date_time - last_date_time)

            last_date_time = new_date_time

    def test_resample_only_shows_numeric(self):
        date_column, results = self.__build_resample_result()

        permitted_keys = [
            '_id',
            '_percentage_complete',
            'gps_alt',
            'gps_precision',
            'amount',
            'gps_latitude',
            'gps_longitude',
        ] + [date_column]

        for result in results:
            for key in result.keys():
                self.assertTrue(key in permitted_keys)

    def test_resample_interval_correct(self):
        date_column, results = self.__build_resample_result()

        self.__check_interval(date_column, results)

    def test_resample_non_date_column(self):
        dataset_id = self._post_file('good_eats.csv')
        result = json.loads(self.controller.resample(
            dataset_id, 'amount', 'W'))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Datasets.ERROR in result)
        self.assertTrue('DatetimeIndex' in result[Datasets.ERROR])

    def test_resample_bad_interval(self):
        dataset_id = self._post_file('good_eats.csv')
        interval = 'BAD'
        result = json.loads(self.controller.resample(
            dataset_id, 'submit_date', interval))

        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Datasets.ERROR in result)
        self.assertEqual(
            'Could not evaluate %s' % interval, result[Datasets.ERROR])

    def test_resample(self):
        expected_length = 17
        date_column, results = self.__build_resample_result()

        self.assertEqual(expected_length, len(results))

    def test_resample_with_query(self):
        expected_length = 15
        query = '{"food_type": "lunch"}'
        date_column, results = self.__build_resample_result(query)

        self.assertEqual(expected_length, len(results))

        self.__check_interval(date_column, results)

    def test_rolling_mean(self):
        dataset_id = self._post_file('good_eats.csv')
        window = '3'
        results = json.loads(self.controller.rolling(
            dataset_id, window))
        self.assertTrue(isinstance(results, list))

        for i, row in enumerate(results):
            if i < int(window) - 1:
                for value in row.values():
                    self.assertEqual('null', value)
            else:
                self.assertTrue(isinstance(row['amount'], float))

    def test_rolling_bad_window(self):
        dataset_id = self._post_file('good_eats.csv')
        window = '3n'
        results = json.loads(self.controller.rolling(
            dataset_id, window))
        self.assertTrue(Datasets.ERROR in results.keys())

    def test_rolling_bad_type(self):
        dataset_id = self._post_file('good_eats.csv')
        results = json.loads(self.controller.rolling(
            dataset_id, 3, win_type='BAD'))

        self.assertTrue(isinstance(results, dict))
        self.assertTrue(Datasets.ERROR in results)
        self.assertEqual('Unknown window type.', results[Datasets.ERROR])

########NEW FILE########
__FILENAME__ = test_datasets_update
import simplejson as json

from bamboo.controllers.calculations import Calculations
from bamboo.core.frame import PARENT_DATASET_ID
from bamboo.models.dataset import Dataset
from bamboo.tests.controllers.test_abstract_datasets_update import\
    TestAbstractDatasetsUpdate


class TestDatasetsUpdate(TestAbstractDatasetsUpdate):

    def setUp(self):
        TestAbstractDatasetsUpdate.setUp(self)
        self._create_original_datasets()

        # create aggregated datasets
        self.calculations = Calculations()
        self.name1 = 'sum of amount'
        self.formula1 = 'sum(amount)'
        self.calculations.create(self.dataset2_id, self.formula1, self.name1)
        result = json.loads(
            self.controller.aggregations(self.dataset2_id))
        self.aggregated_dataset1_id = result['']

        # create merged datasets
        result = json.loads(self.controller.merge(dataset_ids=json.dumps(
            [self.dataset1_id, self.dataset2_id])))
        self.merged_dataset1_id = result[Dataset.ID]

        result = json.loads(self.controller.merge(dataset_ids=json.dumps(
            [self.merged_dataset1_id, self.aggregated_dataset1_id])))
        self.merged_dataset2_id = result[Dataset.ID]

    def test_setup_datasets(self):
        self._verify_dataset(self.dataset1_id,
                             'updates/originals/dataset1.pkl')
        self._verify_dataset(self.dataset2_id,
                             'updates/originals/dataset2.pkl')
        self._verify_dataset(
            self.aggregated_dataset1_id,
            'updates/originals/linked_dataset1.pkl')
        self._verify_dataset(
            self.merged_dataset1_id,
            'updates/originals/merged_dataset1.pkl')
        self._verify_dataset(
            self.merged_dataset2_id,
            'updates/originals/merged_dataset2.pkl')

    def _test_update1(self):
        for dataset_id in [self.merged_dataset1_id, self.merged_dataset2_id]:
            merged_dataset = Dataset.find_one(dataset_id)
            merged_dframe = merged_dataset.dframe(keep_parent_ids=True)
            for _, row in merged_dframe.iterrows():
                self.assertTrue(PARENT_DATASET_ID in row.keys())

        self._verify_dataset(self.dataset1_id,
                             'updates/update1/dataset1.pkl')
        self._verify_dataset(
            self.merged_dataset1_id,
            'updates/update1/merged_dataset1.pkl')
        self._verify_dataset(
            self.merged_dataset2_id,
            'updates/update1/merged_dataset2.pkl')

    def test_datasets_update1(self):
        self._put_row_updates(self.dataset1_id)
        self._test_update1()

    def test_datasets_update1_and_update2(self):
        self._put_row_updates(self.dataset1_id)
        self._test_update1()
        self._put_row_updates(self.dataset2_id)
        self._verify_dataset(
            self.merged_dataset1_id,
            'updates/update2/merged_dataset1.pkl')
        self._verify_dataset(
            self.aggregated_dataset1_id,
            'updates/update2/linked_dataset1.pkl')
        self._verify_dataset(
            self.merged_dataset2_id,
            'updates/update2/merged_dataset2.pkl')

    def test_datasets_update_merged(self):
        self._put_row_updates(self.merged_dataset1_id)
        self._verify_dataset(
            self.merged_dataset1_id,
            'updates/update_merged/merged_dataset1.pkl')
        self._verify_dataset(
            self.merged_dataset2_id,
            'updates/update_merged/merged_dataset2.pkl')

    def test_datasets_update_aggregated_dataset(self):
        self._put_row_updates(
            dataset_id=self.aggregated_dataset1_id,
            file_name='updates/update_agg/update.json')
        self._verify_dataset(
            self.aggregated_dataset1_id,
            'updates/update_agg/linked_dataset1.pkl')
        self._verify_dataset(
            self.merged_dataset2_id,
            'updates/update_agg/merged_dataset2.pkl')
        self._put_row_updates(self.dataset2_id)
        self._verify_dataset(
            self.dataset2_id,
            'updates/update_agg2/dataset2.pkl')
        self._verify_dataset(
            self.aggregated_dataset1_id,
            'updates/update_agg2/linked_dataset1.pkl')
        self._verify_dataset(
            self.merged_dataset2_id,
            'updates/update_agg2/merged_dataset2.pkl')

########NEW FILE########
__FILENAME__ = test_datasets_update_with_aggs
import simplejson as json

from bamboo.models.dataset import Dataset
from bamboo.tests.controllers.test_abstract_datasets_update import\
    TestAbstractDatasetsUpdate


class TestDatasetsUpdateWithAggs(TestAbstractDatasetsUpdate):

    def setUp(self):
        TestAbstractDatasetsUpdate.setUp(self)
        self._create_original_datasets()
        self._add_common_calculations()

        # create linked datasets
        aggregations = {
            'max(amount)': 'max of amount',
            'mean(amount)': 'mean of amount',
            'median(amount)': 'median of amount',
            'min(amount)': 'min of amount',
            'ratio(amount, gps_latitude)': 'ratio of amount and gps_latitude',
            'sum(amount)': 'sum of amount',
        }

        for aggregation, name in aggregations.items():
            self.calculations.create(
                self.dataset2_id, aggregation, name)

        # and with group
        for aggregation, name in aggregations.items():
            self.calculations.create(
                self.dataset2_id, aggregation, name, group='food_type')

        result = json.loads(
            self.controller.aggregations(self.dataset2_id))

        self.linked_dataset1_id = result['']

        # create merged datasets
        result = json.loads(self.controller.merge(dataset_ids=json.dumps(
            [self.dataset1_id, self.dataset2_id])))
        self.merged_dataset1_id = result[Dataset.ID]

        result = json.loads(self.controller.merge(dataset_ids=json.dumps(
            [self.merged_dataset1_id, self.linked_dataset1_id])))
        self.merged_dataset2_id = result[Dataset.ID]

    def test_setup_datasets(self):
        self._verify_dataset(
            self.dataset1_id,
            'updates_with_aggs/originals/dataset1.pkl')
        self._verify_dataset(
            self.dataset2_id,
            'updates_with_aggs/originals/dataset2.pkl')
        self._verify_dataset(
            self.linked_dataset1_id,
            'updates_with_aggs/originals/linked_dataset1.pkl')
        self._verify_dataset(
            self.merged_dataset1_id,
            'updates_with_aggs/originals/merged_dataset1.pkl')
        self._verify_dataset(
            self.merged_dataset2_id,
            'updates_with_aggs/originals/merged_dataset2.pkl')

    def test_datasets_update(self):
        self._put_row_updates(self.dataset2_id)
        self._verify_dataset(
            self.dataset2_id,
            'updates_with_aggs/update/dataset2.pkl')
        self._verify_dataset(
            self.merged_dataset1_id,
            'updates_with_aggs/update/merged_dataset1.pkl')
        self._verify_dataset(
            self.linked_dataset1_id,
            'updates_with_aggs/update/linked_dataset1.pkl')
        self._verify_dataset(
            self.merged_dataset2_id,
            'updates_with_aggs/update/merged_dataset2.pkl')

########NEW FILE########
__FILENAME__ = test_datasets_update_with_calcs
import simplejson as json

from bamboo.models.dataset import Dataset
from bamboo.tests.controllers.test_abstract_datasets_update import\
    TestAbstractDatasetsUpdate


class TestDatasetsUpdateWithCalcs(TestAbstractDatasetsUpdate):

    def setUp(self):
        TestAbstractDatasetsUpdate.setUp(self)
        self._create_original_datasets()
        self._add_common_calculations()

        # create linked datasets
        self.calculations.create(
            self.dataset2_id, 'sum(amount)', 'sum of amount')
        result = json.loads(
            self.controller.aggregations(self.dataset2_id))
        self.linked_dataset1_id = result['']

        # create merged datasets
        result = json.loads(self.controller.merge(dataset_ids=json.dumps(
            [self.dataset1_id, self.dataset2_id])))
        self.merged_dataset1_id = result[Dataset.ID]

        result = json.loads(self.controller.merge(dataset_ids=json.dumps(
            [self.merged_dataset1_id, self.linked_dataset1_id])))
        self.merged_dataset2_id = result[Dataset.ID]

    def test_setup_datasets(self):
        self._verify_dataset(
            self.dataset1_id,
            'updates_with_calcs/originals/dataset1.pkl')
        self._verify_dataset(
            self.dataset2_id,
            'updates_with_calcs/originals/dataset2.pkl')
        self._verify_dataset(
            self.linked_dataset1_id,
            'updates_with_calcs/originals/linked_dataset1.pkl')
        self._verify_dataset(
            self.merged_dataset1_id,
            'updates_with_calcs/originals/merged_dataset1.pkl')
        self._verify_dataset(
            self.merged_dataset2_id,
            'updates_with_calcs/originals/merged_dataset2.pkl')

    def _add_calculations(self):
        self.calculations.create(self.dataset2_id,
                                 'amount_plus_gps_alt > gps_precision',
                                 'amount plus gps_alt > gps_precision')
        self.calculations.create(self.linked_dataset1_id,
                                 'sum_of_amount * 2',
                                 'amount')
        self.calculations.create(self.merged_dataset1_id,
                                 'gps_alt * 2',
                                 'double gps_alt')
        self.calculations.create(self.merged_dataset2_id,
                                 'amount * 2',
                                 'double amount')
        self._verify_dataset(
            self.dataset2_id,
            'updates_with_calcs/calcs/dataset2.pkl')
        self._verify_dataset(
            self.linked_dataset1_id,
            'updates_with_calcs/calcs/linked_dataset1.pkl')
        self._verify_dataset(
            self.merged_dataset1_id,
            'updates_with_calcs/calcs/merged_dataset1.pkl')
        self._verify_dataset(
            self.merged_dataset2_id,
            'updates_with_calcs/calcs/merged_dataset2.pkl')

    def test_datasets_add_calculations(self):
        self._add_calculations()

########NEW FILE########
__FILENAME__ = test_datasets_update_with_join
from time import sleep

import json

from bamboo.models.dataset import Dataset
from bamboo.tests.controllers.test_abstract_datasets_update import\
    TestAbstractDatasetsUpdate
from bamboo.tests.decorators import requires_async


class TestDatasetsUpdateWithJoin(TestAbstractDatasetsUpdate):

    NUM_ROWS_AUX = 8

    def setUp(self):
        """
        These tests use the following dataset configuration:

            l -> left
            r -> right
            j -> joined

            l1   r2
             \  /
              j1

        Dependencies flow from top to bottom.
        """
        TestAbstractDatasetsUpdate.setUp(self)

        # create original datasets
        self.left_dataset_id = self._post_file()
        self.right_dataset_id = self._post_file('good_eats_aux.csv')

        # create joined dataset
        self.on = 'food_type'
        results = json.loads(self.controller.join(
            self.left_dataset_id, self.right_dataset_id, on=self.on))
        self.joined_dataset_id = results[Dataset.ID]

    def test_setup_datasets(self):
        self._verify_dataset(
            self.left_dataset_id,
            'updates_with_join/originals/left_dataset.pkl')
        self._verify_dataset(
            self.right_dataset_id,
            'updates_with_join/originals/right_dataset.pkl')
        self._verify_dataset(
            self.joined_dataset_id,
            'updates_with_join/originals/joined_dataset.pkl')

    def _verify_update_left(self):
        self._verify_dataset(
            self.left_dataset_id,
            'updates_with_join/update_left/left_dataset.pkl')
        self._verify_dataset(
            self.joined_dataset_id,
            'updates_with_join/update_left/joined_dataset.pkl')

    def test_datasets_update_left(self):
        self._put_row_updates(
            self.left_dataset_id,
            file_name='updates_with_join/update_left/update.json'
        )
        self._verify_update_left()

    @requires_async
    def test_datasets_update_left_async(self):
        self._put_row_updates(
            self.left_dataset_id,
            file_name='updates_with_join/update_left/update.json'
        )

        self._left_side_wait()
        self._verify_update_left()

    def _left_side_wait(self):
        while True:
            results1 = json.loads(self.controller.show(self.left_dataset_id))
            results2 = json.loads(self.controller.show(self.joined_dataset_id))
            if all([len(res) for res in [results1, results2]]) and\
                    len(results2) > self.NUM_ROWS:
                break
            sleep(self.SLEEP_DELAY)

    def _verify_update_left_no_join_col(self):
        self._verify_dataset(
            self.left_dataset_id,
            'updates_with_join/update_left_no_join_col/left_dat'
            'aset.pkl')
        self._verify_dataset(
            self.joined_dataset_id,
            'updates_with_join/update_left_no_join_col/joined_d'
            'ataset.pkl')

    def test_datasets_update_left_no_join_col(self):
        self._put_row_updates(
            self.left_dataset_id,
            file_name='updates_with_join/update_left_no_join_co'
            'l/update.json')

        self._verify_update_left_no_join_col()

    @requires_async
    def test_datasets_update_left_no_join_col_async(self):
        self._put_row_updates(
            self.left_dataset_id,
            file_name='updates_with_join/update_left_no_join_co'
            'l/update.json')

        self._left_side_wait()
        self._verify_update_left_no_join_col()

    def _verify_update_right(self):
        self._verify_dataset(
            self.left_dataset_id,
            'updates_with_join/update_right/left_dataset.pkl')
        self._verify_dataset(
            self.right_dataset_id,
            'updates_with_join/update_right/right_dataset.pkl')
        self._verify_dataset(
            self.joined_dataset_id,
            'updates_with_join/update_right/joined_dataset.pkl')

    def test_datasets_update_right(self):
        self._put_row_updates(
            self.left_dataset_id,
            file_name='updates_with_join/update_left/update_baked_goods.json'
        )
        self._put_row_updates(
            self.right_dataset_id,
            file_name='updates_with_join/update_right/update.json'
        )

        self._verify_update_right()

    @requires_async
    def test_datasets_update_right_async(self):
        self._put_row_updates(
            self.left_dataset_id,
            file_name='updates_with_join/update_left/update_baked_goods.json'
        )
        self._put_row_updates(
            self.right_dataset_id,
            file_name='updates_with_join/update_right/update.json'
        )

        while True:
            results1 = json.loads(self.controller.show(self.left_dataset_id))
            results2 = json.loads(self.controller.show(self.right_dataset_id))
            results3 = json.loads(self.controller.show(self.joined_dataset_id))
            if all([len(res) for res in [results1, results2, results3]]) and\
                    len(results2) > self.NUM_ROWS_AUX:
                break
            sleep(self.SLEEP_DELAY)

        # so check succeeds before test teardown
        sleep(3 * self.SLEEP_DELAY)
        self._verify_update_right()

    def test_datasets_update_right_non_unique_join(self):
        self._put_row_updates(
            self.right_dataset_id,
            file_name='updates_with_join/update_right/update_non_unique.json',
            validate=False
        )
        self._verify_dataset(
            self.right_dataset_id,
            'updates_with_join/originals/right_dataset.pkl')
        self._verify_dataset(
            self.joined_dataset_id,
            'updates_with_join/originals/joined_dataset.pkl')

########NEW FILE########
__FILENAME__ = test_root
from cherrypy import HTTPRedirect

from bamboo.controllers.root import Root
from bamboo.tests.test_base import TestBase


class TestRoot(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.controller = Root()

    def test_index(self):
        try:
            self.controller.index()
        except HTTPRedirect as redirect:
            self.assertEqual(redirect.status, 303)
            self.assertTrue(redirect.urls[0].endswith('/docs/index.html'))

########NEW FILE########
__FILENAME__ = test_version
import json

from bamboo.controllers.version import Version
from bamboo.tests.test_base import TestBase


class TestVersion(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.controller = Version()

    def test_index(self):
        response = json.loads(self.controller.index())
        response_keys = response.keys()
        keys = [
            'version',
            'description',
            'branch',
            'commit',
        ]
        for key in keys:
            self.assertTrue(key in response_keys)

########NEW FILE########
__FILENAME__ = test_aggregations
from collections import defaultdict
import pickle

import numpy as np

from bamboo.tests.core.test_calculator import TestCalculator


AGG_CALCS_TO_DEPS = {
    'pearson(gps_latitude, amount)': ['gps_latitude', 'amount'],
    'var(amount)': ['amount'],
    'std(amount)': ['amount'],
    'max(amount)': ['amount'],
    'mean(amount)': ['amount'],
    'median(amount)': ['amount'],
    'min(amount)': ['amount'],
    'sum(amount)': ['amount'],
    'sum(gps_latitude)': ['gps_latitude'],
    'ratio(amount, gps_latitude)': ['amount', 'gps_latitude'],
    'sum(risk_factor in ["low_risk"])': ['risk_factor'],
    'ratio(risk_factor in ["low_risk"], risk_factor in ["low_risk",'
    ' "medium_risk"])': ['risk_factor'],
    'ratio(risk_factor in ["low_risk"], 1)': ['risk_factor'],
    'count(risk_factor in ["low_risk"])': ['risk_factor'],
    'count()': [],
    'argmax(submit_date)': ['submit_date'],
    'newest(submit_date, amount)': ['amount', 'submit_date'],
}


class TestAggregations(TestCalculator):

    AGGREGATION_RESULTS = {
        'var(amount)': 132918.536184,
        'std(amount)': 364.57994,
        'max(amount)': 1600,
        'mean(amount)': 105.65789473684211,
        'median(amount)': 12,
        'min(amount)': 2.0,
        'sum(amount)': 2007.5,
        'sum(gps_latitude)': 624.089497667,
        'ratio(amount, gps_latitude)': 3.184639,
        'sum(risk_factor in ["low_risk"])': 18,
        'ratio(risk_factor in ["low_risk"], risk_factor in ["low_risk",'
        ' "medium_risk"])': 18.0 / 19,
        'ratio(risk_factor in ["low_risk"], 1)': 18.0 / 19,
        'count()': 19.0,
        'count(risk_factor in ["low_risk"])': 18.0,
        'argmax(submit_date)': 18.0,
        'newest(submit_date, amount)': 28.0,
        'pearson(gps_latitude, amount)': -0.67643,
    }

    GROUP_TO_RESULTS = {
        'food_type':
        pickle.load(
            open('tests/fixtures/good_eats_agg_group_food_type.pkl', 'rb')),
        'food_type,rating':
        pickle.load(
            open('tests/fixtures/good_eats_agg_group_food_type_rating.pkl',
                 'rb')),
    }

    def setUp(self):
        TestCalculator.setUp(self)
        self.calculations = AGG_CALCS_TO_DEPS.keys()
        self.expected_length = defaultdict(int)
        self.groups_list = None

    def _offset_for_formula(self, formula, num_columns):
        if formula[:4] in ['mean', 'rati']:
            num_columns += 2
        elif formula[:7] == 'pearson':
            num_columns += 1

        return num_columns

    def _get_initial_len(self, formula, groups_list):
        initial_len = 0 if self.group == '' else len(groups_list)
        return self._offset_for_formula(formula, initial_len)

    def _columns_per_aggregation(self, formula, initial_num_columns=1):
        return self._offset_for_formula(formula, initial_num_columns)

    def _calculations_to_results(self, formula, row):
        if self.group:
            res = self.GROUP_TO_RESULTS[self.group][formula]
            column = row[self.groups_list[0]] if len(self.groups_list) <= 1\
                else tuple([row[group] for group in self.groups_list])
            res = res[column]
            return res
        else:
            return self.AGGREGATION_RESULTS[formula]

    def _test_calculation_results(self, name, formula):
        self.expected_length[self.group] += self._columns_per_aggregation(
            formula)

        # retrieve linked dataset
        linked_dset = self.dataset.aggregated_dataset(self.group)
        self.assertFalse(linked_dset is None)
        linked_dframe = linked_dset.dframe()

        name = linked_dset.schema.labels_to_slugs[name]

        self.assertTrue(name in linked_dframe.columns)
        self.assertEqual(len(linked_dframe.columns),
                         self.expected_length[self.group])

        # test that the schema is up to date
        self.assertTrue(linked_dset.SCHEMA in linked_dset.record.keys())
        self.assertTrue(isinstance(linked_dset.schema, dict))
        schema = linked_dset.schema

        # test slugified column names
        column_names = [name]
        if self.groups_list:
            column_names.extend(self.groups_list)
        for column_name in column_names:
            self.assertTrue(column_name in schema.keys())

        for idx, row in linked_dframe.iterrows():
            result = np.float64(row[name])
            stored = self._calculations_to_results(formula, row)
            # np.nan != np.nan, continue if we have two nan values
            if np.isnan(result) and np.isnan(stored):
                continue
            msg = self._equal_msg(result, stored, formula)
            self.assertAlmostEqual(result, stored, self.places, msg)

    def _test_aggregation(self):
        if self.group:
            self.groups_list = self.dataset.split_groups(self.group)
            self.expected_length[self.group] += len(self.groups_list)
        else:
            self.group = ''

        self._test_calculator()

    def test_aggregation(self):
        self._test_aggregation()

    def test_aggregation_with_group(self):
        self.group = 'food_type'
        self._test_aggregation()

    def test_aggregation_with_multigroup(self):
        self.group = 'food_type,rating'
        self._test_aggregation()

########NEW FILE########
__FILENAME__ = test_calculations
import numpy as np

from bamboo.lib.datetools import parse_date_to_unix_time
from bamboo.models.dataset import Dataset
from bamboo.tests.core.test_calculator import TestCalculator


CALCS_TO_DEPS = {
    # constants
    '-9 + 5': [],

    # aliases
    'rating': ['rating'],
    'gps': ['gps'],

    # arithmetic
    'amount + gps_alt': ['amount', 'gps_alt'],
    'amount - gps_alt': ['amount', 'gps_alt'],
    'amount + 5': ['amount'],
    'amount - gps_alt + 2.5': ['amount', 'gps_alt'],
    'amount * gps_alt': ['amount', 'gps_alt'],
    'amount / gps_alt': ['amount', 'gps_alt'],
    'amount * gps_alt / 2.5': ['amount', 'gps_alt'],
    'amount + gps_alt * gps_precision': ['amount', 'gps_alt',
                                         'gps_precision'],

    # precedence
    '(amount + gps_alt) * gps_precision': ['amount', 'gps_alt',
                                           'gps_precision'],

    # comparison
    'amount == 2': ['amount'],
    '10 < amount': ['amount'],
    '10 < amount + gps_alt': ['amount', 'gps_alt'],

    # logical
    'not amount == 2': ['amount'],
    'not(amount == 2)': ['amount'],
    'amount == 2 and 10 < amount': ['amount'],
    'amount == 2 or 10 < amount': ['amount'],
    'not not amount == 2 or 10 < amount': ['amount'],
    'not amount == 2 or 10 < amount': ['amount'],
    '(not amount == 2) or 10 < amount': ['amount'],
    'not(amount == 2 or 10 < amount)': ['amount'],
    'amount ^ 3': ['amount'],
    '(amount + gps_alt) ^ 2 + 100': ['amount', 'gps_alt'],
    '-amount': ['amount'],
    '-amount < gps_alt - 100': ['amount', 'gps_alt'],

    # membership
    'rating in ["delectible"]': ['rating'],
    'risk_factor in ["low_risk"]': ['risk_factor'],
    'amount in ["9.0", "2.0", "20.0"]': ['amount'],
    '(risk_factor in ["low_risk"]) and (amount in ["9.0", "20.0"])':
    ['risk_factor', 'amount'],

    # dates
    'date("09-04-2012") - submit_date > 21078000': ['submit_date'],
    'today() - submit_date': ['submit_date'],

    # cases
    'case food_type in ["morning_food"]: 1, food_type in ["lunch"]: 2,'
    ' default: 3': ['food_type'],
    'case food_type in ["morning_food"]: 1, food_type in ["lunch"]: 2':
    ['food_type'],

    # row-wise column-based aggregations
    'percentile(amount)': ['amount']
}

DYNAMIC = ['today() - submit_date']


class TestCalculations(TestCalculator):

    def setUp(self):
        TestCalculator.setUp(self)
        self.calculations = CALCS_TO_DEPS.keys()
        self.dynamic_calculations = DYNAMIC

    def _test_calculation_results(self, name, formula):
            unslug_name = name
            labels = self.column_labels_to_slugs.keys()
            self.assertTrue(name in labels, '%s not in %s' % (name, labels))

            name = self.column_labels_to_slugs[unslug_name]

            # test that updated dataframe persisted
            self.dframe = self.dataset.dframe()
            self.assertTrue(name in self.dframe.columns, '%s not in %s' %
                            (name, self.dframe.columns))

            # test new number of columns
            self.added_num_cols += 1
            self.assertEqual(self.start_num_cols + self.added_num_cols,
                             len(self.dframe.columns.tolist()))

            # test that the schema is up to date
            dataset = Dataset.find_one(self.dataset.dataset_id)
            self.assertTrue(Dataset.SCHEMA in dataset.record.keys())
            self.assertTrue(isinstance(dataset.schema, dict))
            schema = dataset.schema

            # test slugified column names
            self.slugified_key_list.append(name)
            self.assertEqual(sorted(schema.keys()),
                             sorted(self.slugified_key_list))

            # test column labels
            self.label_list.append(unslug_name)
            labels = [schema[col][Dataset.LABEL] for col in schema.keys()]
            self.assertEqual(sorted(labels), sorted(self.label_list))

            # test result of calculation
            self._test_cached_dframe(name, formula,
                                     formula in self.dynamic_calculations)

    def _test_cached_dframe(self, name, original_formula, dynamic):
        formula = not dynamic and self.column_labels_to_slugs[original_formula]

        for idx, row in self.dframe.iterrows():
            try:
                result = np.float64(row[name])
                places = self.places

                if dynamic:
                    # downsample and set low precision for time comparison
                    stored = (parse_date_to_unix_time(self.now) -
                              parse_date_to_unix_time(row['submit_date'])
                              ) / 100
                    result = int(result / 100)
                    places = 0
                else:
                    stored = np.float64(row[formula])

                # one np.nan != np.nan, continue if we have two nan values
                if np.isnan(result) and np.isnan(stored):
                    continue

                msg = self._equal_msg(result, stored, original_formula)
                self.assertAlmostEqual(result, stored, places, msg)
            except ValueError:
                msg = self._equal_msg(row[name], row[formula], formula)
                self.assertEqual(row[name], row[formula], msg)

    def test_calculator(self):
        self._test_calculator()

########NEW FILE########
__FILENAME__ = test_calculator
from bamboo.core.parser import Parser
from bamboo.core.calculator import calculate_columns
from bamboo.lib.datetools import now, recognize_dates
from bamboo.models.calculation import Calculation
from bamboo.models.dataset import Dataset
from bamboo.tests.test_base import TestBase


class TestCalculator(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.dataset = Dataset()
        self.dataset.save(
            self.test_dataset_ids['good_eats_with_calculations.csv'])
        dframe = recognize_dates(
            self.get_data('good_eats_with_calculations.csv'))
        self.dataset.save_observations(dframe)
        self.group = None
        self.places = 5

    def _equal_msg(self, calculated, stored, formula):
        return '(calculated %s) %s != (stored %s) %s ' % (type(calculated),
               calculated, type(stored), stored) +\
            '(within %s places), formula: %s' % (self.places, formula)

    def _test_calculator(self):
        self.dframe = self.dataset.dframe()

        columns = self.dframe.columns.tolist()
        self.start_num_cols = len(columns)
        self.added_num_cols = 0

        column_labels_to_slugs = {
            column_attrs[Dataset.LABEL]: (column_name) for
            (column_name, column_attrs) in self.dataset.schema.items()
        }
        self.label_list, self.slugified_key_list = [
            list(ary) for ary in zip(*column_labels_to_slugs.items())
        ]

        for idx, formula in enumerate(self.calculations):
            name = 'test-%s' % idx

            Parser.validate_formula(formula, self.dataset)

            calculation = Calculation()
            calculation.save(self.dataset, formula, name, self.group)
            self.now = now()
            calculate_columns(self.dataset, [calculation])

            self.column_labels_to_slugs = self.dataset.schema.labels_to_slugs

            self._test_calculation_results(name, formula)

########NEW FILE########
__FILENAME__ = test_frame
from pandas import Series

from bamboo.core.frame import BAMBOO_RESERVED_KEYS, remove_reserved_keys,\
    rows_for_parent_id, PARENT_DATASET_ID
from bamboo.tests.test_base import TestBase


class TestFrame(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.dframe = self.get_data('good_eats.csv')

    def _add_bamboo_reserved_keys(self, value=1):
        for key in BAMBOO_RESERVED_KEYS:
            column = Series([value] * len(self.dframe))
            column.name = key
            self.dframe = self.dframe.join(column)

    def test_add_parent_column(self):
        value = 1
        self._add_bamboo_reserved_keys(value)

        for index, item in self.dframe[PARENT_DATASET_ID].iteritems():
            self.assertEqual(item, value)

    def test_remove_reserved_keys(self):
        self._add_bamboo_reserved_keys()

        for key in BAMBOO_RESERVED_KEYS:
            self.assertTrue(key in self.dframe.columns)

        dframe = remove_reserved_keys(self.dframe)

        for key in BAMBOO_RESERVED_KEYS:
            self.assertFalse(key in dframe.columns)

    def test_remove_reserved_keys_exclusion(self):
        self._add_bamboo_reserved_keys()

        for key in BAMBOO_RESERVED_KEYS:
            self.assertTrue(key in self.dframe.columns)

        dframe = remove_reserved_keys(self.dframe, [PARENT_DATASET_ID])

        for key in BAMBOO_RESERVED_KEYS:
            if key == PARENT_DATASET_ID:
                self.assertTrue(key in dframe.columns)
            else:
                self.assertFalse(key in dframe.columns)

    def test_only_rows_for_parent_id(self):
        parent_id = 1
        len_parent_rows = len(self.dframe) / 2

        column = Series([parent_id] * len_parent_rows)
        column.name = PARENT_DATASET_ID

        self.dframe = self.dframe.join(column)
        dframe_only = rows_for_parent_id(self.dframe, parent_id)

        self.assertFalse(PARENT_DATASET_ID in dframe_only.columns)
        self.assertEqual(len(dframe_only), len_parent_rows)

########NEW FILE########
__FILENAME__ = test_parser
from bamboo.core.parser import ParseError, Parser
from bamboo.lib.utils import combine_dicts
from bamboo.models.dataset import Dataset
from bamboo.tests.test_base import TestBase
from bamboo.tests.core.test_aggregations import AGG_CALCS_TO_DEPS
from bamboo.tests.core.test_calculations import CALCS_TO_DEPS


class TestParser(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.dataset_id = self._post_file()
        self.dataset = Dataset.find_one(self.dataset_id)
        self.parser = Parser()
        self.row = {'amount': 1}

    def _parse_and_check_func(self, formula):
        functions = Parser.parse_functions(formula)
        for func in functions:
            self.assertEqual(func.func.func_name, 'eval')
        return functions[0]

    def test_parse_formula(self):
        func = self._parse_and_check_func('amount')
        self.assertEqual(func(self.row, self.dataset), 1)

    def test_bnf(self):
        bnf = self.parser._Parser__build_bnf()
        self.assertNotEqual(bnf, None)

    def test_parse_formula_with_var(self):
        func = self._parse_and_check_func('amount + 1')
        self.assertEqual(func(self.row, self.dataset), 2)

    def test_parse_formula_dependent_columns(self):
        formulas_to_deps = combine_dicts(AGG_CALCS_TO_DEPS, CALCS_TO_DEPS)

        for formula, column_list in formulas_to_deps.iteritems():
            columns = Parser.dependent_columns(formula, self.dataset)
            self.assertEqual(set(column_list), columns)

    def test_parse_formula_bad_formula(self):
        bad_formulas = [
            '=BAD +++ FOR',
            '2 +>+ 1',
            '1 ** 2',
        ]

        for bad_formula in bad_formulas:
            self.assertRaises(ParseError, Parser.parse, bad_formula)

########NEW FILE########
__FILENAME__ = decorators
from functools import wraps
import time

from bamboo.config.settings import RUN_PROFILER
from bamboo.lib.async import set_async


def requires_async(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        set_async(True)
        result = func(*args, **kwargs)
        set_async(False)
        return result
    return wrapper


def run_profiler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if RUN_PROFILER:
            return func(*args, **kwargs)
    return wrapper


def print_time(func):
    """
    @print_time

    Put this decorator around a function to see how many seconds each
    call of this function takes to run.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        seconds = end - start
        print "SECONDS:", seconds, func.__name__, kwargs
        return result
    return wrapper

########NEW FILE########
__FILENAME__ = test_datetools
from datetime import datetime

from bamboo.lib.datetools import recognize_dates
from bamboo.lib.schema_builder import DATETIME, SIMPLETYPE, Schema
from bamboo.tests.test_base import TestBase


class TestDatetools(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.dframe = self.get_data('good_eats.csv')

    def test_recognize_dates(self):
        dframe = self.get_data('soil_samples.csv')
        with_dates = recognize_dates(dframe)

        for field in with_dates['single_letter']:
            self.assertTrue(isinstance(field, basestring))

    def test_recognize_dates_as_dates(self):
        df_with_dates = recognize_dates(self.dframe)

        for field in df_with_dates['submit_date']:
            self.assertTrue(isinstance(field, datetime))

    def test_recognize_dates_from_schema(self):
        schema = Schema({
            'submit_date': {
                SIMPLETYPE: DATETIME
            }
        })
        df_with_dates = recognize_dates(self.dframe, schema)

        for field in df_with_dates['submit_date']:
            self.assertTrue(isinstance(field, datetime))

########NEW FILE########
__FILENAME__ = test_decorators
from bamboo.tests import decorators as test_decorators
from bamboo.tests.test_base import TestBase


class TestDecorators(TestBase):

    def setUp(self):
        def test_func():
            pass
        self._test_func = test_func

    def _test_decorator(self, func):
        wrapped_test_func = func(self._test_func)
        self.assertTrue(hasattr(wrapped_test_func, '__call__'))
        wrapped_test_func()

    def test_print_time(self):
        self._test_decorator(test_decorators.print_time)

########NEW FILE########
__FILENAME__ = test_jsontools
from bamboo.lib.jsontools import df_to_json, df_to_jsondict
from bamboo.tests.test_base import TestBase


class TestFrame(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.dframe = self.get_data('good_eats.csv')

    def test_to_jsondict(self):
        jsondict = df_to_jsondict(self.dframe)
        self.assertEqual(len(jsondict), len(self.dframe))

        for col in jsondict:
            self.assertEqual(len(col), len(self.dframe.columns))

    def test_to_json(self):
        json = df_to_json(self.dframe)
        self.assertEqual(type(json), str)

########NEW FILE########
__FILENAME__ = test_mail
from mock import patch

from bamboo.lib.mail import send_mail
from bamboo.tests.test_base import TestBase


class TestRoot(TestBase):

    @patch('smtplib.SMTP')
    def test_handle_error(self, send_mail):
        send_mail('server', 'mailbox', 'password', 'rec', 'sender', 'body')

########NEW FILE########
__FILENAME__ = test_mongo
from bamboo.lib.mongo import df_mongo_decode, MONGO_ID
from bamboo.tests.test_base import TestBase


class TestFrame(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.dframe = self.get_data('good_eats.csv')

    def test_decode_reserved_keys(self):
        self.assertTrue(MONGO_ID in self.dframe.columns)
        dframe = df_mongo_decode(self.dframe)
        self.assertFalse(MONGO_ID in dframe.columns)

########NEW FILE########
__FILENAME__ = test_schema
from numpy import isnan

from bamboo.core.frame import RESERVED_KEYS
from bamboo.lib.schema_builder import CARDINALITY, Schema, schema_from_dframe
from bamboo.tests.test_base import TestBase


class TestSchema(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.dframe = self.get_data('good_eats.csv')

    def test_init(self):
        schema = Schema()
        self.assertTrue(isinstance(schema, dict))

    def test_rebuild(self):
        schema = Schema()
        new_schema = schema.rebuild(self.dframe)

        self.assertNotEqual(schema, new_schema)

    def test_rebuild_merge(self):
        col = 'not-in-dframe'
        schema = Schema({col: {}})
        new_schema = schema.rebuild(self.dframe)

        self.assertEqual(new_schema[col], {})

    def test_rebuild_no_merge(self):
        col = 'not-in-dframe'
        schema = Schema({col: {}})
        new_schema = schema.rebuild(self.dframe, overwrite=True)

        self.assertFalse(col in new_schema)

    def test_schema_from_dframe_unique_encoded_columns(self):
        self.dframe.rename(columns={'food_type': 'rating+',
                                    'comments': 'rating-'}, inplace=True)
        schema = schema_from_dframe(self.dframe)

        self.assertTrue('rating_' in schema)
        self.assertTrue('rating__' in schema)

    def test_schema_from_dframe_cardnalities(self):
        schema = schema_from_dframe(self.dframe)

        for column, column_schema in schema.items():
            card = column_schema[CARDINALITY]
            self.assertTrue(card <= len(self.dframe))
            self.assertTrue(card >= 0)

            if card == 0:
                self.assertTrue(all([isnan(x) for x in self.dframe[column]]))

    def test_schema_from_dframe_no_reserved_keys(self):
        for key in RESERVED_KEYS:
            self.dframe[key] = 1

        for key in RESERVED_KEYS:
            self.assertTrue(key in self.dframe.columns)

        schema = schema_from_dframe(self.dframe)

        for key in RESERVED_KEYS:
            self.assertFalse(key in schema)

########NEW FILE########
__FILENAME__ = mock
class MockUploadedFile(object):

    def __init__(self, _file):
        self.file = _file

########NEW FILE########
__FILENAME__ = test_calculation
from nose.tools import assert_raises

from bamboo.core.parser import ParseError
from bamboo.models.calculation import Calculation, DependencyError
from bamboo.models.dataset import Dataset
from bamboo.tests.test_base import TestBase


class TestCalculation(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.dataset = Dataset()
        self.dataset.save(self.test_dataset_ids['good_eats.csv'])
        self.formula = 'rating'
        self.name = 'test'

    def _save_calculation(self, formula):
        if not formula:
            formula = self.formula
        return Calculation.create(self.dataset, formula, self.name)

    def _save_observations(self):
        self.dataset.save_observations(self.get_data('good_eats.csv'))

    def _save_observations_and_calculation(self, formula=None):
        self._save_observations()
        return self._save_calculation(formula)

    def test_save(self):
        calculation = self._save_observations_and_calculation()

        self.assertTrue(isinstance(calculation, Calculation))

        record = calculation.record

        self.assertTrue(isinstance(record, dict))
        self.assertTrue(Calculation.FORMULA in record.keys())
        self.assertTrue(Calculation.STATE in record.keys())

        record = Calculation.find(self.dataset)[0].record

        self.assertEqual(record[Calculation.STATE], Calculation.STATE_READY)
        self.assertTrue(Calculation(record).is_ready)

    def test_save_set_status(self):
        record = self._save_observations_and_calculation().record

        self.assertTrue(isinstance(record, dict))
        self.assertTrue(Calculation.FORMULA in record.keys())

    def test_save_set_aggregation(self):
        calculation = self._save_observations_and_calculation('max(amount)')

        self.assertEqual('max', calculation.aggregation)

    def test_save_set_aggregation_id(self):
        calculation = self._save_observations_and_calculation('max(amount)')
        agg_id = self.dataset.aggregated_datasets_dict['']

        self.assertEqual(agg_id, calculation.aggregation_id)

    def test_save_improper_formula(self):
        assert_raises(ParseError, self._save_observations_and_calculation,
                      'NON_EXISTENT_COLUMN')
        try:
            self._save_observations_and_calculation('NON_EXISTENT_COLUMN')
        except ParseError as e:
            self.assertTrue('Missing column' in e.__str__())

    def test_save_unparsable_formula(self):
        assert_raises(ParseError, self._save_observations_and_calculation,
                      '=NON_EXISTENT_COLUMN')
        try:
            self._save_observations_and_calculation(
                '=NON_EXISTENT_COLUMN')
        except ParseError as e:
            self.assertTrue('Parse Failure' in e.__str__())

    def test_save_improper_formula_no_data(self):
        assert_raises(ParseError, Calculation().save, self.dataset,
                      'NON_EXISTENT_COLUMN', self.name)
        try:
            Calculation().save(self.dataset, 'NON_EXISTENT_COLUMN',
                               self.name)
        except ParseError as e:
            self.assertTrue('No schema' in e.__str__())

    def test_save_unparsable_formula_no_data(self):
        assert_raises(ParseError, Calculation().save, self.dataset,
                      '=NON_EXISTENT_COLUMN', self.name)
        try:
            Calculation().save(self.dataset, '=NON_EXISTENT_COLUMN',
                               self.name)
        except ParseError as e:
            self.assertTrue('Parse Failure' in e.__str__())

    def test_save_non_existent_group(self):
        self._save_observations()
        assert_raises(ParseError, Calculation().save, self.dataset,
                      self.formula, self.name, group_str='NON_EXISTENT_GROUP')
        try:
            Calculation().save(self.dataset, self.formula, self.name,
                               group_str='NON_EXISTENT_GROUP')
        except ParseError as e:
            self.assertTrue('Group' in e.__str__())

    def test_find(self):
        self._save_observations_and_calculation()
        rows = Calculation.find(self.dataset)
        new_record = rows[0].record
        status = new_record.pop(Calculation.STATE)
        self.assertEqual(status, Calculation.STATE_READY)

    def test_sets_dependent_calculations(self):
        self._save_observations_and_calculation()
        self.name = 'test1'
        self._save_calculation('test')
        calculation = Calculation.find_one(self.dataset.dataset_id, 'test')
        self.assertEqual(calculation.dependent_calculations, ['test1'])

    def test_removes_dependent_calculations(self):
        self._save_observations_and_calculation()
        self.name = 'test1'
        self._save_calculation('test')
        calculation = Calculation.find_one(self.dataset.dataset_id, 'test')
        self.assertEqual(calculation.dependent_calculations, ['test1'])
        calculation = Calculation.find_one(self.dataset.dataset_id, 'test1')
        calculation.delete(self.dataset)
        calculation = Calculation.find_one(self.dataset.dataset_id, 'test')
        self.assertEqual(calculation.dependent_calculations, [])

    def test_disallow_delete_dependent_calculation(self):
        self._save_observations_and_calculation()
        self.name = 'test1'
        self._save_calculation('test')
        calculation = Calculation.find_one(self.dataset.dataset_id, 'test')
        self.assertEqual(calculation.dependent_calculations, ['test1'])
        calculation = Calculation.find_one(self.dataset.dataset_id, 'test')
        assert_raises(DependencyError, calculation.delete, self.dataset)

########NEW FILE########
__FILENAME__ = test_dataset
from datetime import datetime

from pandas import DataFrame

from bamboo.tests.test_base import TestBase
from bamboo.models.dataset import Dataset
from bamboo.models.observation import Observation
from bamboo.lib.datetools import recognize_dates
from bamboo.lib.mongo import MONGO_ID_ENCODED
from bamboo.lib.schema_builder import OLAP_TYPE, RE_ENCODED_COLUMN, SIMPLETYPE


class TestDataset(TestBase):

    def test_save(self):
        for dataset_name in self.TEST_DATASETS:
            dataset = Dataset().save(self.test_dataset_ids[dataset_name])
            record = dataset.record

            self.assertTrue(isinstance(record, dict))
            self.assertTrue('_id' in record.keys())

    def test_find(self):
        for dataset_name in self.TEST_DATASETS:
            dataset = Dataset.create(self.test_dataset_ids[dataset_name])
            record = dataset.record
            rows = Dataset.find(self.test_dataset_ids[dataset_name])

            self.assertEqual(record, rows[0].record)

    def test_find_one(self):
        for dataset_name in self.TEST_DATASETS:
            dataset = Dataset.create(self.test_dataset_ids[dataset_name])
            record = dataset.record
            row = Dataset.find_one(self.test_dataset_ids[dataset_name])

            self.assertEqual(record, row.record)

    def test_create(self):
        for dataset_name in self.TEST_DATASETS:
            dataset = Dataset.create(self.test_dataset_ids[dataset_name])

            self.assertTrue(isinstance(dataset, Dataset))

    def test_delete(self):
        for dataset_name in self.TEST_DATASETS:
            dataset = Dataset.create(self.test_dataset_ids[dataset_name])
            records = Dataset.find(self.test_dataset_ids[dataset_name])
            self.assertNotEqual(records, [])
            dataset.delete()
            records = Dataset.find(self.test_dataset_ids[dataset_name])

            self.assertEqual(records, [])
            self.assertEqual(Observation.encoding(dataset), None)

    def test_update(self):
        for dataset_name in self.TEST_DATASETS:
            dataset = Dataset.create(self.test_dataset_ids[dataset_name])
            self.assertFalse('field' in dataset.record)
            dataset.update({'field': {'key': 'value'}})
            dataset = Dataset.find_one(self.test_dataset_ids[dataset_name])

            self.assertTrue('field' in dataset.record)
            self.assertEqual(dataset.record['field'], {'key': 'value'})

    def test_build_schema(self):
        for dataset_name in self.TEST_DATASETS:
            dataset = Dataset.create(self.test_dataset_ids[dataset_name])
            dataset.build_schema(self.get_data(dataset_name))

            # get dataset with new schema
            dataset = Dataset.find_one(self.test_dataset_ids[dataset_name])

            for key in [
                    Dataset.CREATED_AT, Dataset.SCHEMA, Dataset.UPDATED_AT]:
                self.assertTrue(key in dataset.record.keys())

            df_columns = self.get_data(dataset_name).columns.tolist()
            seen_columns = []

            for column_name, column_attributes in dataset.schema.items():
                # check column_name is unique
                self.assertFalse(column_name in seen_columns)
                seen_columns.append(column_name)

                # check column name is only legal chars
                self.assertFalse(RE_ENCODED_COLUMN.search(column_name))

                # check has require attributes
                self.assertTrue(SIMPLETYPE in column_attributes)
                self.assertTrue(OLAP_TYPE in column_attributes)
                self.assertTrue(Dataset.LABEL in column_attributes)

                # check label is an original column
                original_col = column_attributes[Dataset.LABEL]
                error_msg = '%s not in %s' % (original_col, df_columns)
                self.assertTrue(original_col in df_columns, error_msg)
                df_columns.remove(column_attributes[Dataset.LABEL])

                # check not reserved key
                self.assertFalse(column_name == MONGO_ID_ENCODED)

            # ensure all columns in df_columns have store columns
            self.assertTrue(len(df_columns) == 0)

    def test_dframe(self):
        dataset = Dataset.create(self.test_dataset_ids['good_eats.csv'])
        dataset.save_observations(
            recognize_dates(self.get_data('good_eats.csv')))
        dframe = dataset.dframe()

        self.assertTrue(isinstance(dframe, DataFrame))
        self.assertTrue(all(self.get_data('good_eats.csv').reindex(
                        columns=dframe.columns).eq(dframe)))
        columns = dframe.columns

        # ensure no reserved keys
        self.assertFalse(MONGO_ID_ENCODED in columns)

        # ensure date is converted
        self.assertTrue(isinstance(dframe.submit_date[0], datetime))

    def test_count(self):
        dataset = Dataset.create(self.test_dataset_ids['good_eats.csv'])
        dataset.save_observations(
            recognize_dates(self.get_data('good_eats.csv')))

        self.assertEqual(len(dataset.dframe()), dataset.count())

########NEW FILE########
__FILENAME__ = test_observation
from bamboo.core.frame import INDEX
from bamboo.lib.mongo import dump_mongo_json, MONGO_ID, MONGO_ID_ENCODED
from bamboo.lib.query_args import QueryArgs
from bamboo.models.dataset import Dataset
from bamboo.models.observation import Observation
from bamboo.tests.test_base import TestBase


class TestObservation(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.dataset = Dataset()
        self.dataset.save(self.test_dataset_ids['good_eats.csv'])
        self.query_args = QueryArgs({"rating": "delectible"})

    def __save_records(self):
        Observation.save(self.get_data('good_eats.csv'),
                         self.dataset)
        records = Observation.find(self.dataset)
        self.assertTrue(isinstance(records, list))
        self.assertTrue(isinstance(records[0], dict))
        self.assertTrue('_id' in records[0].keys())

        return records

    def __decode(self, row):
        return Observation.encode(row,
                                  encoding=Observation.decoding(self.dataset))

    def test_encoding(self):
        self.__save_records()
        encoding = Observation.encoding(self.dataset)

        for column in self.dataset.dframe().columns:
            if column == MONGO_ID:
                column = MONGO_ID_ENCODED

            self.assertTrue(column in encoding.keys())

        for v in encoding.values():
            self.assertTrue(isinstance(int(v), int))

    def test_encode_no_dataset(self):
        records = self.__save_records()

        for record in records:
            encoded = Observation.encode(record)
            self.assertEqual(dump_mongo_json(encoded), dump_mongo_json(record))

    def test_save(self):
        records = self.__save_records()
        self.assertEqual(len(records), 19)

    def test_save_over_bulk(self):
        Observation.save(self.get_data('good_eats_large.csv'),
                         self.dataset)
        records = Observation.find(self.dataset)

        self.assertEqual(len(records), 1001)

    def test_find(self):
        self.__save_records()
        rows = Observation.find(self.dataset)

        self.assertTrue(isinstance(rows, list))

    def test_find_with_query(self):
        self.__save_records()
        rows = Observation.find(self.dataset, self.query_args)

        self.assertTrue(isinstance(rows, list))

    def test_find_with_select(self):
        self.__save_records()
        query_args = QueryArgs(select={"rating": 1})
        rows = Observation.find(self.dataset, query_args)

        self.assertTrue(isinstance(rows, list))

        row = self.__decode(rows[0])

        self.assertEquals(sorted(row.keys()), ['_id', 'rating'])

    def test_find_with_select_and_query(self):
        self.__save_records()
        self.query_args.select = {"rating": 1}
        rows = Observation.find(self.dataset, self.query_args)
        self.assertTrue(isinstance(rows, list))

        row = self.__decode(rows[0])

        self.assertEquals(sorted(row.keys()), ['_id', 'rating'])

    def test_delete_all(self):
        self.__save_records()
        records = Observation.find(self.dataset)
        self.assertNotEqual(records, [])
        Observation.delete_all(self.dataset)
        records = Observation.find(self.dataset)

        self.assertEqual(records, [])

    def test_delete_one(self):
        self.__save_records()
        records = Observation.find(self.dataset)
        self.assertNotEqual(records, [])

        row = self.__decode(records[0])

        Observation.delete(self.dataset, row[INDEX])
        new_records = Observation.find(self.dataset)

        # Dump to avoid problems with nan != nan.
        self.assertEqual(dump_mongo_json(records[1:]),
                         dump_mongo_json(new_records))

    def test_delete_encoding(self):
        self.__save_records()
        encoding = Observation.encoding(self.dataset)

        self.assertTrue(isinstance(encoding, dict))

        Observation.delete_encoding(self.dataset)
        encoding = Observation.encoding(self.dataset)

        self.assertEqual(encoding, None)

########NEW FILE########
__FILENAME__ = test_bamboo
from subprocess import call

from bamboo.tests.test_base import TestBase
from bamboo import bambooapp  # nopep8


class TestBamboo(TestBase):

    def setUp(self):
        TestBase.setUp(self)

    def test_bambooapp(self):
        # this tests that importing bamboo.bambooapp succeeds
        pass

    def test_pep8(self):
        result = call(['pep8', '.'])
        self.assertEqual(result, 0, "Code is not pep8.")

########NEW FILE########
__FILENAME__ = test_base
import os
from time import sleep
import unittest
import uuid

from pandas import read_csv

from bamboo.config.db import Database
from bamboo.config.settings import TEST_DATABASE_NAME
from bamboo.models.dataset import Dataset
from bamboo.tests.mock import MockUploadedFile


class TestBase(unittest.TestCase):

    FIXTURE_PATH = 'tests/fixtures/'
    SLEEP_DELAY = 0.2
    TEST_DATASETS = [
        'good_eats.csv',
        'good_eats_large.csv',
        'good_eats_with_calculations.csv',
        'kenya_secondary_schools_2007.csv',
        'soil_samples.csv',
        'water_points.csv',
        'unicode.csv',
    ]

    test_dataset_ids = {}

    def setUp(self):
        self.__drop_database()
        self.__create_database()
        self.__load_test_data()

    def tearDown(self):
        self.__drop_database()

    def get_data(self, dataset_name):
        return read_csv('%s%s' % (self._local_fixture_prefix(), dataset_name),
                        encoding='utf-8')

    def _create_dataset_from_url(self, url):
        dataset = Dataset.create()
        return dataset.import_from_url(url, allow_local_file=True).dataset_id

    def _local_fixture_prefix(self, filename=''):
        return 'file://localhost%s/tests/fixtures/%s' % (os.getcwd(), filename)

    def _fixture_path_prefix(self, filename=''):
        return '/%s/tests/fixtures/%s' % (os.getcwd(), filename)

    def _file_mock(self, file_path, add_prefix=False):
        if add_prefix:
            file_path = self._fixture_path_prefix(file_path)

        file_ = open(file_path, 'r')

        return MockUploadedFile(file_)

    def _post_file(self, file_name='good_eats.csv'):
        dataset = Dataset.create()
        return dataset.import_from_csv(
            self._file_mock(self._fixture_path_prefix(file_name))).dataset_id

    def _wait_for_dataset_state(self, dataset_id):
        while True:
            dataset = Dataset.find_one(dataset_id)

            if dataset.state != Dataset.STATE_PENDING:
                break

            sleep(self.SLEEP_DELAY)

        return dataset

    def __create_database(self):
        Database.db(TEST_DATABASE_NAME)

    def __drop_database(self):
        Database.client().drop_database(TEST_DATABASE_NAME)

    def __load_test_data(self):
        for dataset_name in self.TEST_DATASETS:
            self.test_dataset_ids[dataset_name] = uuid.uuid4().hex

########NEW FILE########
__FILENAME__ = test_profile
import json
import os
from tempfile import NamedTemporaryFile

from pandas import concat

from bamboo.controllers.datasets import Datasets
from bamboo.models.dataset import Dataset
from bamboo.tests.decorators import run_profiler
from bamboo.tests.mock import MockUploadedFile
from bamboo.tests.test_base import TestBase


class TestProfile(TestBase):

    TEST_CASE_SIZES = {
        'tiny': (1, 1),
        'small': (2, 2),
        'large': (4, 40),
    }

    def setUp(self):
        TestBase.setUp(self)
        self.datasets = Datasets()
        self.tmp_file = NamedTemporaryFile(delete=False)

    def tearDown(self):
        os.unlink(self.tmp_file.name)

    def _expand_width(self, df, exponent):
        for i in xrange(0, exponent):
            other = df.rename(
                columns={col: '%s-%s' % (col, idx) for (idx, col) in
                         enumerate(df.columns)})
            df = df.join(other)
            df.rename(columns={col: str(idx) for (idx, col) in
                      enumerate(df.columns)}, inplace=True)
        return df

    def _grow_test_data(self, dataset_name, width_exp, length_factor):
        df = self.get_data(dataset_name)
        df = self._expand_width(df, width_exp)
        return concat([df] * length_factor)

    def test_tiny_profile(self):
        self._test_profile('tiny')

    def test_small_profile(self):
        self._test_profile('small')

    def test_large_profile(self):
        self._test_profile('large')

    @run_profiler
    def _test_profile(self, size):
        print 'bamboo/bamboo: %s' % size
        self._test_create_data(*self.TEST_CASE_SIZES[size])
        print 'saving dataset'
        self._test_save_dataset()
        self._test_get_info()
        self._test_get_summary()
        self._test_get_summary_with_group('province')
        self._test_get_summary_with_group('school_zone')

    def _test_create_data(self, width_exp, length_factor):
        self.data = self._grow_test_data(
            'kenya_secondary_schools_2007.csv', width_exp, length_factor)
        print 'bamboo/bamboo rows: %s, columns: %s' % (
            len(self.data), len(self.data.columns))

    def _test_save_dataset(self):
        self.data.to_csv(self.tmp_file)
        self.tmp_file.close()
        mock_uploaded_file = MockUploadedFile(open(self.tmp_file.name, 'r'))
        result = json.loads(self.datasets.create(csv_file=mock_uploaded_file))
        self.assertTrue(isinstance(result, dict))
        self.assertTrue(Dataset.ID in result)
        self.dataset_id = result[Dataset.ID]

    def _test_get_info(self):
        result = json.loads(self.datasets.info(self.dataset_id))
        self.assertTrue(isinstance(result, dict))

    def _test_get_summary(self):
        result = json.loads(self.datasets.summary(
            self.dataset_id,
            select=self.datasets.SELECT_ALL_FOR_SUMMARY))
        self.assertTrue(isinstance(result, dict))

    def _test_get_summary_with_group(self, group):
        result = json.loads(self.datasets.summary(
            self.dataset_id, group=group,
            select=self.datasets.SELECT_ALL_FOR_SUMMARY))
        self.assertTrue(isinstance(result, dict))

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# bamboo documentation build configuration file, created by
# sphinx-quickstart on Fri May 25 12:48:30 2012.
#
# This file is execfile()d with the current directory set to its containing dir
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

from bamboo.lib.version import VERSION_NUMBER, VERSION_DESCRIPTION

# -- General configuration ----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx.ext.coverage',
              'sphinx.ext.pngmath', 'sphinx.ext.mathjax',
              'sphinx.ext.inheritance_diagram', 'sphinx.ext.ifconfig',
              'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'bamboo'
copyright = u'2013, Peter Lubell-Doughtie, Mark Johnston'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = VERSION_NUMBER
# The full version, including alpha/beta/rc tags.
release = '%s %s' % (VERSION_NUMBER, VERSION_DESCRIPTION)

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'nature'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'bamboodoc'


# -- Options for LaTeX output -------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual])
latex_documents = [
    ('index', 'bamboo.tex', u'bamboo Documentation',
     u'Peter Lubell-Doughtie, Mark Johnston', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output -------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'bamboo', u'bamboo Documentation',
     [u'Peter Lubell-Doughtie, Mark Johnston'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'bamboo', u'bamboo Documentation',
     u'Peter Lubell-Doughtie, Mark Johnston', 'bamboo',
     'bamboo is a data analysis web service.',
     'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = bearcart
# -*- coding: utf-8 -*-
'''
Rickshaw
-------

Python Pandas + Rickshaw.js

'''

from __future__ import division
import time
import json
from pkg_resources import resource_string
import numpy as np
import pandas as pd
from jinja2 import Environment, PackageLoader


class Chart(object):
    '''Visualize Pandas Timeseries with Rickshaw.js'''

    def __init__(self, data=None, width=750, height=400, plt_type='line',
                 colors=None, x_time=True, palette=None, **kwargs):
        '''Generate a Rickshaw time series visualization with Pandas
        Series and DataFrames.

         The bearcart Chart generates the Rickshaw visualization of a Pandas
         timeseries Series or DataFrame. The only required parameters are
         data, width, height, and type. Colors is an optional parameter;
         bearcart will default to the Rickshaw spectrum14 color palette if
         none are passed. Keyword arguments can be passed to disable the
         following components:
            - x_axis
            - y_axis
            - hover
            - legend

        Parameters
        ----------
        data: Pandas Series or DataFrame, default None
             The Series or Dataframe must have a Datetime index.
        width: int, default 960
            Width of the chart in pixels
        height: int, default 500
            Height of the chart in pixels
        type: string, default 'line'
            Must be one of 'line', 'area', 'scatterplot' or 'bar'
        colors: dict, default None
            Dict with keys matching DataFrame or Series column names, and hex
            strings for colors
        x_time: boolean, default True
            If passed as False, the x-axis will have non-time values
        kwargs:
            Keyword arguments that, if passed as False, will disable the
            following components: x_axis, y_axis, hover, legend

        Returns
        -------
        Bearcart object

        Examples
        --------
        >>>vis = bearcart.Chart(data=df, width=800, height=300, type='area')
        >>>vis = bearcart.Chart(data=series,type='scatterplot',
                                colors={'Data 1': '#25aeb0',
                                        'Data 2': '#114e4f'})
        #Disable x_axis and legend
        >>>vis = bearcart.Chart(data=df, x_axis=False, legend=False)

        '''

        self.defaults = {'x_axis': True, 'y_axis': True, 'hover': True,
                         'legend': True}

        self.env = Environment(loader=PackageLoader('external.bearcart',
                                                    'templates'))

        self.palette_scheme = palette or 'spectrum14'

        #Colors need to be js strings
        if colors:
            self.colors = {key: "'{0}'".format(value)
                           for key, value in colors.iteritems()}
        else:
            self.colors = None

        self.x_axis_time = x_time
        self.renderer = plt_type
        self.width = width
        self.height = height
        self.template_vars = {}

        #Update defaults for passed kwargs
        for key, value in kwargs.iteritems():
            self.defaults[key] = value

        # Get templates for graph elements
        for att, val in self.defaults.iteritems():
            render_vars = {}
            if val:
                if not self.x_axis_time:
                    if att == 'x_axis' and val is not True:
                        att = 'x_axis_num'
                        render_vars = self.make_ticks(val)
                    elif att == 'hover':
                        render_vars = {'x_hover': 'xFormatter: function(x)'
                                       '{return xTicks[x]}'}
                temp = self.env.get_template(att + '.js')
                self.template_vars.update({att: temp.render(render_vars)})

        #Transform data into Rickshaw-happy JSON format
        if data is not None:
            self.transform_data(data)

    def make_ticks(self, axis):
        self.template_vars['transform'] = (
            "rotateText();$('#legend').bind('click',rotateText);")
        cases = ','.join(["%s:'%s'" % (i, v) for i, v in enumerate(axis)])
        return {'xTicks': 'var xTicks = {%s};' % cases,
                'ticks': 'tickFormat:function(x){return xTicks[x]},'}

    def transform_data(self, data):
        '''Transform Pandas Timeseries into JSON format

        Parameters
        ----------
        data: DataFrame or Series
            Pandas DataFrame or Series must have datetime index

        Returns
        -------
        JSON to object.json_data

        Example
        -------
        >>>vis.transform_data(df)
        >>>vis.json_data

        '''
        def convert(v):
            if isinstance(v, np.float64):
                v = float(v)
            elif isinstance(v, np.int64):
                v = int(v)

            return v

        objectify = lambda dat: [{"x": convert(x), "y": convert(y)}
                                 for x, y in dat.iteritems()]

        self.raw_data = data
        if isinstance(data, pd.Series):
            data.name = data.name or 'data'
            self.json_data = [{'name': data.name, 'data': objectify(data)}]
        elif isinstance(data, pd.DataFrame):
            self.json_data = [{'name': x[0], 'data': objectify(x[1])}
                              for x in data.iteritems()]

        #Transform to Epoch seconds for Rickshaw
        if self.x_axis_time:
            for datacol in self.json_data:
                datacol = datacol['data']
                for objs in datacol:
                    if pd.isnull(objs['x']):
                        objs['x'] = None
                    elif (isinstance(objs['x'], pd.tslib.Timestamp) or
                          isinstance(objs['x'], pd.Period)):
                        objs['x'] = int(time.mktime(objs['x'].timetuple()))

    def _build_graph(self):
        '''Build Rickshaw graph syntax with all data'''

        #Set palette colors if necessary
        if not self.colors:
            self.palette = self.env.get_template('palette.js')
            self.template_vars.update({'palette': self.palette.render(
                {'scheme': self.palette_scheme})})
            self.colors = {x['name']: 'palette.color()'
                           for x in self.json_data}

        template_vars = []
        for dataset in self.json_data:
            template_vars.append({'name': str(dataset['name']),
                                  'color': self.colors[dataset['name']],
                                  'data': json.dumps(dataset['data'])})

        variables = {'dataset': template_vars, 'width': self.width,
                     'height': self.height, 'render': self.renderer}
        graph = self.env.get_template('graph.js')
        self.template_vars.update({'graph': graph.render(variables)})

    def build_html(self):
        self._build_graph()
        html = self.env.get_template('bcart_template.html')
        self.HTML = html.render(self.template_vars)

        return self.HTML

    def create_chart(self, html_path='index.html', data_path='data.json',
                     js_path=None, css_path=None):
        '''Save bearcart output to HTML and JSON.

        Parameters
        ----------
        html_path: string, default 'index.html'
            Path for html output
        data_path: string, default 'data.json'
            Path for data JSON output
        js_path: string, default None
            If passed, the Rickshaw javascript library will be saved to the
            path. The file must be named "rickshaw.min.js"
        css_path: string, default None
            If passed, the Rickshaw css library will be saved to the
            path. The file must be named "rickshaw.min.css"

        Returns
        -------
        HTML, JSON, JS, and CSS

        Example
        --------
        >>>vis.create_chart(html_path='myvis.html', data_path='visdata.json'),
                            js_path='rickshaw.min.js',
                            cs_path='rickshaw.min.css')
        '''
        self.build_html()

        with open(html_path, 'w') as f:
            f.write(self.HTML)

        with open(data_path, 'w') as f:
            json.dump(self.json_data, f, sort_keys=True, indent=4,
                      separators=(',', ': '))

        if js_path:
            js = resource_string('bearcart', 'rickshaw.min.js')
            with open(js_path, 'w') as f:
                f.write(js)
        if css_path:
            css = resource_string('bearcart', 'rickshaw.min.css')
            with open(css_path, 'w') as f:
                    f.write(css)

########NEW FILE########
__FILENAME__ = fabfile
import os
import sys

from fabric.api import env, run, cd


DEPLOYMENTS = {
    'prod': {
        'home':         '/var/www/',
        'host_string':  'bamboo@bamboo.io',
        'virtual_env':  'bamboo',
        'repo_name':    'current',
        'project':      'bamboo',
        'docs':         'docs',
        'branch':       'master',
        'key_filename': os.path.expanduser('~/.ssh/modilabs.pem'),
        'init_script':  'bamboo_uwsgi.sh',
        'celeryd':      'celeryd',
    }
}


def _run_in_virtualenv(command):
    run('source ~/.virtualenvs/%s/bin/activate && %s' % (env.virtual_env,
                                                         command))


def _check_key_filename(deployment_name):
    if 'key_filename' in DEPLOYMENTS[deployment_name] and \
            not os.path.exists(DEPLOYMENTS[deployment_name]['key_filename']):
        print 'Cannot find required permissions file: %s' % \
            DEPLOYMENTS[deployment_name]['key_filename']
        return False
    return True


def _setup_env(deployment_name):
    env.update(DEPLOYMENTS[deployment_name])
    if not _check_key_filename(deployment_name):
        sys.exit(1)
    env.project_directory = os.path.join(env.home, env.project)
    env.code_src = os.path.join(env.project_directory, env.repo_name)
    env.doc_src = os.path.join(env.project_directory, env.repo_name, env.docs)
    env.pip_requirements_file = os.path.join(
        env.code_src, 'deploy/requirements/requirements.pip')


def deploy(deployment_name):
    _setup_env(deployment_name)

    # update code
    with cd(env.code_src):
        run('git fetch origin %(branch)s' % env)
        run('git reset --hard origin/%(branch)s' % env)
        run('git pull origin %(branch)s' % env)
        run('find . -name "*.pyc" -delete')

    # update docs
    with cd(env.doc_src):
        _run_in_virtualenv('make html')

    # install dependencies
    _run_in_virtualenv('pip install -r %s' % env.pip_requirements_file)

    # restart celery
    with cd(env.code_src):
        _run_in_virtualenv('../shared/%s restart' % env.celeryd)

    # restart the server
    with cd(env.code_src):
        _run_in_virtualenv('./scripts/%s restart' % env.init_script)

########NEW FILE########
__FILENAME__ = migrate_to_encoded
import argparse

from pybamboo.dataset import Dataset


BAMBOO_DEV_URL = 'http://dev.bamboo.io/'


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dataset', help='The dataset ID to migrate')
    args = parser.parse_args()
    main()


def main():
    dataset_url = "%sdatasets/%s.csv" % (BAMBOO_DEV_URL, args.dataset)

    dataset = Dataset(url=dataset_url)
    print dataset.id

########NEW FILE########
__FILENAME__ = 001_observations_add_deleted_at
#!/usr/bin/env python

import os
import sys
sys.path.append(os.getcwd())

from bamboo.models.observation import Observation


def migrate():
    observation = Observation
    record = {Observation.DELETED_AT: 0}
    observation.collection.update({}, {'$set': record}, multi=True)


if __name__ == '__main__':
    migrate()

########NEW FILE########
__FILENAME__ = mongo_index
#!/usr/bin/env python

import os
import sys
sys.path.append(os.getcwd())

from pymongo import ASCENDING

from bamboo.config.db import Database
from bamboo.core.frame import DATASET_ID
from bamboo.models.observation import Observation

# The encoded dataset_id will be set to '0'.
ENCODED_DATASET_ID = '0'


def bamboo_index(collection, key):
    ensure_index = collection.__getattribute__('ensure_index')
    ensure_index([(key, ASCENDING)])
    ensure_index([(key, ASCENDING), (Observation.DELETED_AT, ASCENDING)])


def ensure_indexing():
    """Ensure that bamboo models are indexed."""
    db = Database.db()

    # collections
    calculations = db.calculations
    datasets = db.datasets
    observations = db.observations

    # indices
    bamboo_index(datasets, DATASET_ID)
    bamboo_index(observations, ENCODED_DATASET_ID)
    bamboo_index(observations, Observation.ENCODING_DATASET_ID)
    bamboo_index(calculations, DATASET_ID)


if __name__ == '__main__':
    ensure_indexing()

########NEW FILE########
__FILENAME__ = run_server
#!/usr/bin/env python

import os
import sys
sys.path.append(os.getcwd())

import cherrypy

from bamboo.config.routes import connect_routes


# use routes dispatcher
dispatcher = cherrypy.dispatch.RoutesDispatcher()
routes_conf = {'/': {'request.dispatch': dispatcher}}
local_conf = 'bamboo/config/local.conf'

# connect routes
connect_routes(dispatcher)

# global config
cherrypy.config.update(routes_conf)
cherrypy.config.update(local_conf)

# app config
app = cherrypy.tree.mount(root=None, config=routes_conf)
app.merge(local_conf)


# start server
if __name__ == '__main__':  # pragma: no cover
    cherrypy.quickstart(app)

########NEW FILE########
