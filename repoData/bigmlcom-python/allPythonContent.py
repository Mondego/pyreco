__FILENAME__ = api
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2012-2014 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""BigML.io Python bindings.

This is a simple binding to BigML.io, the BigML API.

Example usage (assuming that you have previously set up the BIGML_USERNAME and
BIGML_API_KEY environment variables):

from bigml.api import BigML

api = BigML()
source = api.create_source('./data/iris.csv')
dataset = api.create_dataset(source)
model = api.create_model(dataset)
prediction = api.create_prediction(model, {'sepal width': 1})
api.pprint(prediction)

"""
import sys
import logging
LOG_FORMAT = '%(asctime)-15s: %(message)s'
LOGGER = logging.getLogger('BigML')

import time
import os
import re
import locale
import pprint

from threading import Thread

import requests
import urllib2
from poster.encode import multipart_encode, MultipartParam
from poster.streaminghttp import register_openers


try:
    import simplejson as json
except ImportError:
    import json

from bigml.util import (invert_dictionary, localize, is_url, check_dir,
                        clear_console_line, reset_console_line, console_log,
                        maybe_save, get_exponential_wait)
from bigml.util import DEFAULT_LOCALE
from bigml.domain import Domain
from bigml.domain import DEFAULT_DOMAIN, DEFAULT_PROTOCOL

register_openers()

# Base URL
BIGML_URL = '%s://%s/andromeda/'
# Development Mode URL
BIGML_DEV_URL = '%s://%s/dev/andromeda/'

# Basic resources
SOURCE_PATH = 'source'
DATASET_PATH = 'dataset'
MODEL_PATH = 'model'
PREDICTION_PATH = 'prediction'
EVALUATION_PATH = 'evaluation'
ENSEMBLE_PATH = 'ensemble'
BATCH_PREDICTION_PATH = 'batchprediction'
CLUSTER_PATH = 'cluster'
CENTROID_PATH = 'centroid'
BATCH_CENTROID_PATH = 'batchcentroid'


# Resource Ids patterns
ID_PATTERN = '[a-f0-9]{24}'
SHARED_PATTERN = '[a-zA-Z0-9]{27}'
SOURCE_RE = re.compile(r'^%s/%s$' % (SOURCE_PATH, ID_PATTERN))
DATASET_RE = re.compile(r'^(public/)?%s/%s$|^shared/%s/%s$' % (
    DATASET_PATH, ID_PATTERN, DATASET_PATH, SHARED_PATTERN))
MODEL_RE = re.compile(r'^(public/)?%s/%s$|^shared/%s/%s$' % (
    MODEL_PATH, ID_PATTERN, MODEL_PATH, SHARED_PATTERN))
PREDICTION_RE = re.compile(r'^%s/%s$' % (PREDICTION_PATH, ID_PATTERN))
EVALUATION_RE = re.compile(r'^%s/%s$' % (EVALUATION_PATH, ID_PATTERN))
ENSEMBLE_RE = re.compile(r'^%s/%s$' % (ENSEMBLE_PATH, ID_PATTERN))
BATCH_PREDICTION_RE = re.compile(r'^%s/%s$' % (BATCH_PREDICTION_PATH,
                                               ID_PATTERN))
CLUSTER_RE = re.compile(r'^(public/)?%s/%s$|^shared/%s/%s$' % (
    CLUSTER_PATH, ID_PATTERN, CLUSTER_PATH, SHARED_PATTERN))
CENTROID_RE = re.compile(r'^%s/%s$' % (CENTROID_PATH, ID_PATTERN))
BATCH_CENTROID_RE = re.compile(r'^%s/%s$' % (BATCH_CENTROID_PATH,
                                             ID_PATTERN))


RESOURCE_RE = {
    'source': SOURCE_RE,
    'dataset': DATASET_RE,
    'model': MODEL_RE,
    'prediction': PREDICTION_RE,
    'evaluation': EVALUATION_RE,
    'ensemble': ENSEMBLE_RE,
    'batchprediction': BATCH_PREDICTION_RE,
    'cluster': CLUSTER_RE,
    'centroid': CENTROID_RE,
    'batchcentroid': BATCH_CENTROID_RE}
DOWNLOAD_DIR = '/download'

# Headers
SEND_JSON = {'Content-Type': 'application/json;charset=utf-8'}
ACCEPT_JSON = {'Accept': 'application/json;charset=utf-8'}

# HTTP Status Codes from https://bigml.com/developers/status_codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_ACCEPTED = 202
HTTP_NO_CONTENT = 204
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_PAYMENT_REQUIRED = 402
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_METHOD_NOT_ALLOWED = 405
HTTP_TOO_MANY_REQUESTS = 429
HTTP_LENGTH_REQUIRED = 411
HTTP_INTERNAL_SERVER_ERROR = 500

# Resource status codes
WAITING = 0
QUEUED = 1
STARTED = 2
IN_PROGRESS = 3
SUMMARIZED = 4
FINISHED = 5
UPLOADING = 6
FAULTY = -1
UNKNOWN = -2
RUNNABLE = -3

# Map status codes to labels
STATUSES = {
    WAITING: "WAITING",
    QUEUED: "QUEUED",
    STARTED: "STARTED",
    IN_PROGRESS: "IN_PROGRESS",
    SUMMARIZED: "SUMMARIZED",
    FINISHED: "FINISHED",
    UPLOADING: "UPLOADING",
    FAULTY: "FAULTY",
    UNKNOWN: "UNKNOWN",
    RUNNABLE: "RUNNABLE"
}

# Minimum query string to get model fields
TINY_MODEL = "full=false"


def get_resource(regex, resource):
    """Returns a resource/id.

    """
    if isinstance(resource, dict) and 'resource' in resource:
        resource = resource['resource']
    if isinstance(resource, basestring) and regex.match(resource):
        return resource
    raise ValueError("Cannot find resource id for %s" % resource)


def get_resource_type(resource):
    """Returns the associated resource type for a resource

    """
    if isinstance(resource, dict) and 'resource' in resource:
        resource = resource['resource']
    if not isinstance(resource, basestring):
        raise ValueError("Failed to parse a resource string or structure.")
    for resource_type, resource_re in RESOURCE_RE.items():
        if resource_re.match(resource):
            return resource_type
    return None


def check_resource_type(resource, expected_resource, message=None):
    """Checks the resource type.

    """
    resource_type = get_resource_type(resource)
    if not expected_resource == resource_type:
        raise Exception("%s\nFound %s." % (message, resource_type))


def get_source_id(source):
    """Returns a source/id.
    """
    return get_resource(SOURCE_RE, source)


def get_dataset_id(dataset):
    """Returns a dataset/id.

    """
    return get_resource(DATASET_RE, dataset)


def get_model_id(model):
    """Returns a model/id.

    """
    return get_resource(MODEL_RE, model)


def get_prediction_id(prediction):
    """Returns a prediction/id.

    """
    return get_resource(PREDICTION_RE, prediction)


def get_evaluation_id(evaluation):
    """Returns an evaluation/id.

    """
    return get_resource(EVALUATION_RE, evaluation)


def get_ensemble_id(ensemble):
    """Returns an ensemble/id.

    """
    return get_resource(ENSEMBLE_RE, ensemble)


def get_batch_prediction_id(batch_prediction):
    """Returns a batchprediction/id.

    """
    return get_resource(BATCH_PREDICTION_RE, batch_prediction)


def get_cluster_id(cluster):
    """Returns a cluster/id.

    """
    return get_resource(CLUSTER_RE, cluster)


def get_centroid_id(centroid):
    """Returns a centroid/id.

    """
    return get_resource(CENTROID_RE, centroid)


def get_batch_centroid_id(batch_centroid):
    """Returns a batchcentroid/id.

    """
    return get_resource(BATCH_CENTROID_RE, batch_centroid)


def get_resource_id(resource):
    """Returns the resource id if it falls in one of the registered types

    """
    if isinstance(resource, dict) and 'resource' in resource:
        return resource['resource']
    elif isinstance(resource, basestring) and (
            SOURCE_RE.match(resource)
            or DATASET_RE.match(resource)
            or MODEL_RE.match(resource)
            or PREDICTION_RE.match(resource)
            or EVALUATION_RE.match(resource)
            or ENSEMBLE_RE.match(resource)
            or BATCH_PREDICTION_RE.match(resource)
            or CLUSTER_RE.match(resource)
            or CENTROID_RE.match(resource)
            or BATCH_CENTROID_RE.match(resource)):
        return resource
    else:
        return


def resource_is_ready(resource):
    """Checks a fully fledged resource structure and returns True if finished.

    """
    if not isinstance(resource, dict) or not 'error' in resource:
        raise Exception("No valid resource structure found")
    if resource['error'] is not None:
        raise Exception(resource['error']['status']['message'])
    return (resource['code'] in [HTTP_OK, HTTP_ACCEPTED] and
            get_status(resource)['code'] == FINISHED)


def get_status(resource):
    """Extracts status info if present or sets the default if public

    """
    if not isinstance(resource, dict):
        raise ValueError("We need a complete resource to extract its status")
    if 'object' in resource:
        if resource['object'] is None:
            raise ValueError("The resource has no status info\n%s" % resource)
        resource = resource['object']
    if not resource.get('private', True):
        status = {'code': FINISHED}
    else:
        status = resource['status']
    return status


def check_resource(resource, get_method, query_string='', wait_time=1,
                   retries=None, raise_on_error=False):
    """Waits until a resource is finished.

       Given a resource and its corresponding get_method
           source, api.get_source
           dataset, api.get_dataset
           model, api.get_model
           prediction, api.get_prediction
           evaluation, api.get_evaluation
           ensemble, api.get_ensemble
           batch_prediction, api.get_batch_prediction
       it calls the get_method on the resource with the given query_string
       and waits with sleeping intervals of wait_time
       until the resource is in a final state (either FINISHED
       or FAULTY). The number of retries can be limited using the retries
       parameter.

    """
    def get_kwargs(resource_id):
        if not (EVALUATION_RE.match(resource_id) or
                PREDICTION_RE.match(resource_id) or
                BATCH_PREDICTION_RE.match(resource_id) or
                CENTROID_RE.match(resource_id) or
                BATCH_CENTROID_RE.match(resource_id)):
            return {'query_string': query_string}
        return {}

    kwargs = {}
    if isinstance(resource, basestring):
        resource_id = resource
        kwargs = get_kwargs(resource_id)
        resource = get_method(resource, **kwargs)
    else:
        resource_id = get_resource_id(resource)
        if resource_id is None:
            raise ValueError("Failed to extract a valid resource id to check.")
        kwargs = get_kwargs(resource_id)

    counter = 0
    while retries is None or counter < retries:
        counter += 1
        status = get_status(resource)
        code = status['code']
        if code == FINISHED:
            if raise_on_error:
                exception_on_error(resource)
            return resource
        elif code == FAULTY:
            raise ValueError(status)
        time.sleep(get_exponential_wait(wait_time, counter))
        resource = get_method(resource, **kwargs)
    if raise_on_error:
        exception_on_error(resource)
    return resource


def exception_on_error(resource):
    """Raises exception if resource has error

    """
    if resource['error'] is not None:
        raise Exception(resource['error']['status']['message'])


def assign_dir(path):
    """Silently checks the path for existence or creates it.

       Returns either the path or None.
    """
    if not isinstance(path, basestring):
        return None
    try:
        return check_dir(path)
    except ValueError:
        return None


def stream_copy(response, filename):
    """Copies the contents of a response stream to a local file.

    """
    file_size = 0
    path = os.path.dirname(filename)
    check_dir(path)
    try:
        with open(filename, 'wb') as file_handle:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file_handle.write(chunk)
                    file_handle.flush()
                    file_size += len(chunk)
    except IOError:
        file_size = 0
    return file_size


def http_ok(resource):
    """Checking the validity of the http return code

    """
    if 'code' in resource:
        return resource['code'] in [HTTP_OK, HTTP_CREATED, HTTP_ACCEPTED]


def count(listing):
    """Count of existing resources

    """
    if 'meta' in listing and 'query_total' in listing['meta']:
        return listing['meta']['query_total']


##############################################################################
#
# Patch for requests
#
##############################################################################
def patch_requests():
    """ Monkey patches requests to get debug output.

    """
    def debug_request(method, url, **kwargs):
        """Logs the request and response content for api's remote requests

        """
        response = original_request(method, url, **kwargs)
        logging.debug("Data: {}".format(response.request.body))
        logging.debug("Response: {}".format(response.content))
        return response
    original_request = requests.api.request
    requests.api.request = debug_request


##############################################################################
#
# BigML class
#
##############################################################################


class BigML(object):
    """Entry point to create, retrieve, list, update, and delete
    sources, datasets, models and predictions.

    Full API documentation on the API can be found from BigML at:
        https://bigml.com/developers

    Resources are wrapped in a dictionary that includes:
        code: HTTP status code
        resource: The resource/id
        location: Remote location of the resource
        object: The resource itself
        error: An error code and message

    """
    def __init__(self, username=None, api_key=None, dev_mode=False,
                 debug=False, set_locale=False, storage=None, domain=None):
        """Initializes the BigML API.

        If left unspecified, `username` and `api_key` will default to the
        values of the `BIGML_USERNAME` and `BIGML_API_KEY` environment
        variables respectively.

        If `dev_mode` is set to `True`, the API will be used in development
        mode where the size of your datasets are limited but you are not
        charged any credits.

        If storage is set to a directory name, the resources obtained in
        CRU operations will be stored in the given directory.

        If domain is set, the api will point to the specified domain. Default
        will be the one in the environment variable `BIGML_DOMAIN` or
        `bigml.io` if missing. The expected domain argument is a string or a
        Domain object. See Domain class for details.

        """

        logging_level = logging.ERROR
        if debug:
            logging_level = logging.DEBUG
            patch_requests()

        logging.basicConfig(format=LOG_FORMAT,
                            level=logging_level,
                            stream=sys.stdout)

        if username is None:
            try:
                username = os.environ['BIGML_USERNAME']
            except KeyError:
                sys.exit("Cannot find BIGML_USERNAME in your environment")

        if api_key is None:
            try:
                api_key = os.environ['BIGML_API_KEY']
            except KeyError:
                sys.exit("Cannot find BIGML_API_KEY in your environment")

        self.auth = "?username=%s;api_key=%s;" % (username, api_key)
        self.dev_mode = dev_mode

        self._set_api_urls(dev_mode=dev_mode, domain=domain)

        if set_locale:
            locale.setlocale(locale.LC_ALL, DEFAULT_LOCALE)
        self.storage = assign_dir(storage)
        self.getters = {
            'source': self.get_source,
            'dataset': self.get_dataset,
            'model': self.get_model,
            'ensemble': self.get_ensemble,
            'prediction': self.get_prediction,
            'evaluation': self.get_evaluation,
            'batchprediction': self.get_batch_prediction,
            'cluster': self.get_cluster,
            'centroid': self.get_centroid,
            'batchcentroid': self.get_batch_centroid}

    def _set_api_urls(self, dev_mode=False, domain=None):
        """Sets the urls that point to the REST api methods for each resource

        """
        if domain is None:
            domain = Domain()
        elif isinstance(domain, basestring):
            domain = Domain(domain=domain)
        elif not isinstance(domain, Domain):
            raise ValueError("The domain must be set using a Domain object.")
        # Setting the general and prediction domain options
        self.general_domain = domain.general_domain
        self.prediction_domain = domain.prediction_domain
        self.prediction_protocol = domain.prediction_protocol
        self.verify = domain.verify
        self.verify_prediction = domain.verify_prediction
        if dev_mode:
            self.url = BIGML_DEV_URL % (DEFAULT_PROTOCOL, self.general_domain)
            self.prediction_url = BIGML_DEV_URL % (DEFAULT_PROTOCOL,
                                                   self.general_domain)
        else:
            self.url = BIGML_URL % (DEFAULT_PROTOCOL, self.general_domain)
            self.prediction_url = BIGML_URL % (
                self.prediction_protocol, self.prediction_domain)

        # Base Resource URLs
        self.source_url = self.url + SOURCE_PATH
        self.dataset_url = self.url + DATASET_PATH
        self.model_url = self.url + MODEL_PATH
        self.prediction_url = self.prediction_url + PREDICTION_PATH
        self.evaluation_url = self.url + EVALUATION_PATH
        self.ensemble_url = self.url + ENSEMBLE_PATH
        self.batch_prediction_url = self.url + BATCH_PREDICTION_PATH
        self.cluster_url = self.url + CLUSTER_PATH
        self.centroid_url = self.url + CENTROID_PATH
        self.batch_centroid_url = self.url + BATCH_CENTROID_PATH


    def _create(self, url, body, verify=None):
        """Creates a new remote resource.

        Posts `body` in JSON to `url` to create a new remote resource.

        Returns a BigML resource wrapped in a dictionary that includes:
            code: HTTP status code
            resource: The resource/id
            location: Remote location of the resource
            object: The resource itself
            error: An error code and message

        """
        code = HTTP_INTERNAL_SERVER_ERROR
        resource_id = None
        location = None
        resource = None
        error = {
            "status": {
                "code": code,
                "message": "The resource couldn't be created"}}

        # If a prediction server is in use, the first prediction request might
        # return a HTTP_ACCEPTED (202) while the model or ensemble is being
        # downloaded.
        code = HTTP_ACCEPTED
        if verify is None:
            verify = self.verify
        while code == HTTP_ACCEPTED:
            try:
                response = requests.post(url + self.auth,
                                         headers=SEND_JSON,
                                         data=body, verify=verify)
                code = response.status_code
                if code in [HTTP_CREATED, HTTP_OK]:
                    if 'location' in response.headers:
                        location = response.headers['location']
                    resource = json.loads(response.content, 'utf-8')
                    resource_id = resource['resource']
                    error = None
                elif code in [HTTP_BAD_REQUEST,
                              HTTP_UNAUTHORIZED,
                              HTTP_PAYMENT_REQUIRED,
                              HTTP_FORBIDDEN,
                              HTTP_NOT_FOUND,
                              HTTP_TOO_MANY_REQUESTS]:
                    error = json.loads(response.content, 'utf-8')
                    LOGGER.error(self.error_message(error, method='create'))
                elif code != HTTP_ACCEPTED:
                    LOGGER.error("Unexpected error (%s)" % code)
                    code = HTTP_INTERNAL_SERVER_ERROR

            except ValueError:
                LOGGER.error("Malformed response")
                code = HTTP_INTERNAL_SERVER_ERROR
            except requests.ConnectionError, exc:
                LOGGER.error("Connection error: %s" % str(exc))
                code = HTTP_INTERNAL_SERVER_ERROR
            except requests.Timeout:
                LOGGER.error("Request timed out")
                code = HTTP_INTERNAL_SERVER_ERROR
            except requests.RequestException:
                LOGGER.error("Ambiguous exception occurred")
                code = HTTP_INTERNAL_SERVER_ERROR

        return maybe_save(resource_id, self.storage, code,
                          location, resource, error)

    def _get(self, url, query_string='',
             shared_username=None, shared_api_key=None):
        """Retrieves a remote resource.

        Uses HTTP GET to retrieve a BigML `url`.

        Returns a BigML resource wrapped in a dictionary that includes:
            code: HTTP status code
            resource: The resource/id
            location: Remote location of the resource
            object: The resource itself
            error: An error code and message

        """
        code = HTTP_INTERNAL_SERVER_ERROR
        resource_id = None
        location = url
        resource = None
        error = {
            "status": {
                "code": HTTP_INTERNAL_SERVER_ERROR,
                "message": "The resource couldn't be retrieved"}}
        auth = (self.auth if shared_username is None
                else "?username=%s;api_key=%s" % (
                    shared_username, shared_api_key))
        try:
            response = requests.get(url + auth + query_string,
                                    headers=ACCEPT_JSON,
                                    verify=self.verify)

            code = response.status_code

            if code == HTTP_OK:
                resource = json.loads(response.content, 'utf-8')
                resource_id = resource['resource']
                error = None
            elif code in [HTTP_BAD_REQUEST,
                          HTTP_UNAUTHORIZED,
                          HTTP_NOT_FOUND,
                          HTTP_TOO_MANY_REQUESTS]:
                error = json.loads(response.content, 'utf-8')
                LOGGER.error(self.error_message(error, method='get'))
            else:
                LOGGER.error("Unexpected error (%s)" % code)
                code = HTTP_INTERNAL_SERVER_ERROR

        except ValueError:
            LOGGER.error("Malformed response")
        except requests.ConnectionError, exc:
            LOGGER.error("Connection error: %s" % str(exc))
        except requests.Timeout:
            LOGGER.error("Request timed out")
        except requests.RequestException:
            LOGGER.error("Ambiguous exception occurred")

        return maybe_save(resource_id, self.storage, code,
                          location, resource, error)

    def _list(self, url, query_string=''):
        """Lists all existing remote resources.

        Resources in listings can be filterd using `query_string` formatted
        according to the syntax and fields labeled as filterable in the BigML
        documentation for each resource.

        Sufixes:
            __lt: less than
            __lte: less than or equal to
            __gt: greater than
            __gte: greater than or equal to

        For example:

            'size__gt=1024'

        Resources can also be sortened including a sort_by statement within
        the `query_sting`. For example:

            'order_by=size'

        """
        code = HTTP_INTERNAL_SERVER_ERROR
        meta = None
        resources = None
        error = {
            "status": {
                "code": code,
                "message": "The resource couldn't be listed"}}
        try:

            response = requests.get(url + self.auth + query_string,
                                    headers=ACCEPT_JSON, verify=self.verify)
            code = response.status_code

            if code == HTTP_OK:
                resource = json.loads(response.content, 'utf-8')
                meta = resource['meta']
                resources = resource['objects']
                error = None
            elif code in [HTTP_BAD_REQUEST,
                          HTTP_UNAUTHORIZED,
                          HTTP_NOT_FOUND,
                          HTTP_TOO_MANY_REQUESTS]:
                error = json.loads(response.content, 'utf-8')
            else:
                LOGGER.error("Unexpected error (%s)" % code)
                code = HTTP_INTERNAL_SERVER_ERROR

        except ValueError:
            LOGGER.error("Malformed response")
        except requests.ConnectionError, exc:
            LOGGER.error("Connection error: %s" % str(exc))
        except requests.Timeout:
            LOGGER.error("Request timed out")
        except requests.RequestException:
            LOGGER.error("Ambiguous exception occurred")

        return {
            'code': code,
            'meta': meta,
            'objects': resources,
            'error': error}

    def _update(self, url, body):
        """Updates a remote resource.

        Uses PUT to update a BigML resource. Only the new fields that
        are going to be updated need to be included in the `body`.

        Returns a resource wrapped in a dictionary:
            code: HTTP_ACCEPTED if the update has been OK or an error
                  code otherwise.
            resource: Resource/id
            location: Remote location of the resource.
            object: The new updated resource
            error: Error code if any. None otherwise

        """
        code = HTTP_INTERNAL_SERVER_ERROR
        resource_id = None
        location = url
        resource = None
        error = {
            "status": {
                "code": code,
                "message": "The resource couldn't be updated"}}

        try:
            response = requests.put(url + self.auth,
                                    headers=SEND_JSON,
                                    data=body, verify=self.verify)

            code = response.status_code

            if code == HTTP_ACCEPTED:
                resource = json.loads(response.content, 'utf-8')
                resource_id = resource['resource']
                error = None
            elif code in [HTTP_UNAUTHORIZED,
                          HTTP_PAYMENT_REQUIRED,
                          HTTP_METHOD_NOT_ALLOWED,
                          HTTP_TOO_MANY_REQUESTS]:
                error = json.loads(response.content, 'utf-8')
                LOGGER.error(self.error_message(error, method='update'))
            else:
                LOGGER.error("Unexpected error (%s)" % code)
                code = HTTP_INTERNAL_SERVER_ERROR

        except ValueError:
            LOGGER.error("Malformed response")
        except requests.ConnectionError, exc:
            LOGGER.error("Connection error: %s" % str(exc))
        except requests.Timeout:
            LOGGER.error("Request timed out")
        except requests.RequestException:
            LOGGER.error("Ambiguous exception occurred")

        return maybe_save(resource_id, self.storage, code,
                          location, resource, error)

    def _delete(self, url):
        """Permanently deletes a remote resource.

        If the request is successful the status `code` will be HTTP_NO_CONTENT
        and `error` will be None. Otherwise, the `code` will be an error code
        and `error` will be provide a specific code and explanation.

        """
        code = HTTP_INTERNAL_SERVER_ERROR
        error = {
            "status": {
                "code": code,
                "message": "The resource couldn't be deleted"}}

        try:
            response = requests.delete(url + self.auth, verify=self.verify)
            code = response.status_code

            if code == HTTP_NO_CONTENT:
                error = None
            elif code in [HTTP_BAD_REQUEST,
                          HTTP_UNAUTHORIZED,
                          HTTP_NOT_FOUND,
                          HTTP_TOO_MANY_REQUESTS]:
                error = json.loads(response.content, 'utf-8')
                LOGGER.error(self.error_message(error, method='delete'))
            else:
                LOGGER.error("Unexpected error (%s)" % code)
                code = HTTP_INTERNAL_SERVER_ERROR

        except ValueError:
            LOGGER.error("Malformed response")
        except requests.ConnectionError, exc:
            LOGGER.error("Connection error: %s" % str(exc))
        except requests.Timeout:
            LOGGER.error("Request timed out")
        except requests.RequestException:
            LOGGER.error("Ambiguous exception occurred")

        return {
            'code': code,
            'error': error}

    def _download(self, url, filename=None):
        """Retrieves a remote file.

        Uses HTTP GET to download a file object with a BigML `url`.
        """
        code = HTTP_INTERNAL_SERVER_ERROR
        file_object = None

        response = requests.get(url + self.auth,
                                verify=self.verify, stream=True)
        code = response.status_code

        if code == HTTP_OK:
            if filename is None:
                file_object = response.raw
            else:
                file_size = stream_copy(response, filename)
                if file_size == 0:
                    LOGGER.error("Error copying file to %s" % filename)
                else:
                    file_object = filename
        elif code in [HTTP_BAD_REQUEST,
                      HTTP_UNAUTHORIZED,
                      HTTP_NOT_FOUND,
                      HTTP_TOO_MANY_REQUESTS]:
            error = response.content
            LOGGER.error("Error downloading: %s" % error)
        else:
            LOGGER.error("Unexpected error (%s)" % code)
            code = HTTP_INTERNAL_SERVER_ERROR

        return file_object

    def _set_create_from_datasets_args(self, datasets, args=None,
                                       wait_time=3, retries=10, key=None):
        """Builds args dictionary for the create call from a `dataset` or a
           list of `datasets`.

        """
        dataset_ids = []
        if not isinstance(datasets, list):
            origin_datasets = [datasets]
        else:
            origin_datasets = datasets

        for dataset in origin_datasets:
            check_resource_type(dataset, DATASET_PATH,
                                message="A dataset id is needed to create a"
                                        " model.")
            dataset = check_resource(dataset, self.get_dataset,
                                     wait_time=wait_time, retries=retries,
                                     raise_on_error=True)
            dataset_ids.append(get_dataset_id(dataset))

        create_args = {}
        if args is not None:
            create_args.update(args)

        if len(dataset_ids) == 1:
            if key is None:
                key = "dataset"
            create_args.update({
                key: dataset_ids[0]})
        else:
            if key is None:
                key = "datasets"
            create_args.update({
                key: dataset_ids})

        return create_args

    def ok(self, resource):
        """Waits until the resource is finished or faulty, updates it and
           returns True on success

        """
        if http_ok(resource):
            resource_type = get_resource_type(resource)
            resource.update(check_resource(resource,
                                           self.getters[resource_type]))
            return True
        else:
            LOGGER.error("The resource couldn't be created: %s" %
                         resource['error'])

    def error_message(self, resource, resource_type='resource', method=None):
        """Error message for each type of resource

        """
        error = None
        error_info = None
        if isinstance(resource, dict):
            if 'error' in resource:
                error_info = resource['error']
            elif ('code' in resource
                  and 'status' in resource):
                error_info = resource
        if error_info is not None and 'code' in error_info:
            code = error_info['code']
            if ('status' in error_info and
                    'message' in error_info['status']):
                error = error_info['status']['message']
                extra = error_info['status'].get('extra', None)
                if extra is not None:
                    error += ": %s" % extra
            if code == HTTP_NOT_FOUND and method == 'get':
                alternate_message = ''
                if self.general_domain != DEFAULT_DOMAIN:
                    alternate_message = (
                        u'- The %s was not created in %s.\n' % (
                            resource_type, self.general_domain))
                error += (
                    u'\nCouldn\'t find a %s matching the given'
                    u' id. The most probable causes are:\n\n%s'
                    u'- A typo in the %s\'s id.\n'
                    u'- The %s id cannot be accessed with your credentials.\n'
                    u'\nDouble-check your %s and'
                    u' credentials info and retry.' % (
                        resource_type, alternate_message, resource_type,
                        resource_type, resource_type))
                return error
            if code == HTTP_UNAUTHORIZED:
                error += u'\nDouble-check your credentials, please.'
                return error
            if code == HTTP_BAD_REQUEST:
                error += u'\nDouble-check the arguments for the call, please.'
                return error
            if code == HTTP_TOO_MANY_REQUESTS:
                error += (u'\nToo many requests. Please stop '
                          u' requests for a while before resuming.')
                return error
            elif code == HTTP_PAYMENT_REQUIRED:
                error += (u'\nYou\'ll need to buy some more credits to perform'
                          u' the chosen action')
                return error

        return "Invalid %s structure:\n\n%s" % (resource_type, resource)

    ##########################################################################
    #
    # Utils
    #
    ##########################################################################

    def get_fields(self, resource):
        """Retrieve fields used by a resource.

        Returns a dictionary with the fields that uses
        the resource keyed by Id.

        """

        def _get_fields_key(resource):
            """Returns the fields key from a resource dict

            """
            if resource['code'] in [HTTP_OK, HTTP_ACCEPTED]:
                if MODEL_RE.match(resource_id):
                    return resource['object']['model']['model_fields']
                else:
                    return resource['object']['fields']
            return None

        if isinstance(resource, dict) and 'resource' in resource:
            resource_id = resource['resource']
        elif (isinstance(resource, basestring) and (
              SOURCE_RE.match(resource) or DATASET_RE.match(resource) or
              MODEL_RE.match(resource) or PREDICTION_RE.match(resource))):
            resource_id = resource
            resource = self._get("%s%s" % (self.url, resource_id))
        else:
            LOGGER.error("Wrong resource id")
            return
        # Tries to extract fields information from resource dict. If it fails,
        # a get remote call is used to retrieve the resource by id.
        fields = None
        try:
            fields = _get_fields_key(resource)
        except KeyError:
            resource = self._get("%s%s" % (self.url, resource_id))
            fields = _get_fields_key(resource)

        return fields

    def pprint(self, resource, out=sys.stdout):
        """Pretty prints a resource or part of it.

        """

        if (isinstance(resource, dict)
                and 'object' in resource
                and 'resource' in resource):

            resource_id = resource['resource']
            if (SOURCE_RE.match(resource_id) or DATASET_RE.match(resource_id)
                    or MODEL_RE.match(resource_id)
                    or EVALUATION_RE.match(resource_id)
                    or ENSEMBLE_RE.match(resource_id)
                    or CLUSTER_RE.match(resource_id)):
                out.write("%s (%s bytes)\n" % (resource['object']['name'],
                                               resource['object']['size']))
            elif PREDICTION_RE.match(resource['resource']):
                objective_field_name = (resource['object']['fields']
                                                [resource['object']
                                                 ['objective_fields'][0]]
                                                ['name'])
                input_data = {}
                for key, value in resource['object']['input_data'].items():
                    try:
                        name = resource['object']['fields'][key]['name']
                    except KeyError:
                        name = key
                    input_data[name] = value

                prediction = (
                    resource['object']['prediction']
                            [resource['object']['objective_fields'][0]])
                out.write("%s for %s is %s\n" % (objective_field_name,
                                                 input_data,
                                                 prediction))
            out.flush()
        else:
            pprint.pprint(resource, out, indent=4)

    def status(self, resource):
        """Maps status code to string.

        """
        resource_id = get_resource_id(resource)
        if resource_id:
            resource = self._get("%s%s" % (self.url, resource_id))
            status = get_status(resource)
            code = status['code']
            return STATUSES.get(code, "UNKNOWN")
        else:
            status = get_status(resource)
            if status['code'] != UPLOADING:
                LOGGER.error("Wrong resource id")
                return
            return STATUSES[UPLOADING]

    def check_resource(self, resource, get_method,
                       query_string='', wait_time=1):
        """Deprecated method. Use check_resource function instead.

        """
        return check_resource(resource, get_method,
                              query_string=query_string, wait_time=wait_time)

    def check_origins(self, dataset, model, args, model_types=None,
                      wait_time=3, retries=10):
        """Returns True if the dataset and model needed to build
           the batch prediction or evaluation are finished. The args given
           by the user are modified to include the related ids in the
           create call.

           If model_types is a list, then we check any of the model types in
           the list.

        """

        def args_update(get_method):
            """Updates args when the resource is ready

            """
            if resource_id:
                check_resource(resource_id, get_method,
                               wait_time=wait_time, retries=retries,
                               raise_on_error=True)
                args.update({
                    resource_type: resource_id,
                    "dataset": dataset_id})

        if model_types is None:
            model_types = []

        resource_type = get_resource_type(dataset)
        if not DATASET_PATH == resource_type:
            raise Exception("A dataset id is needed as second argument"
                            " to create the resource. %s found." %
                            resource_type)
        dataset_id = get_dataset_id(dataset)
        if dataset_id:
            dataset = check_resource(dataset_id, self.get_dataset,
                                     wait_time=wait_time, retries=retries,
                                     raise_on_error=True)
            resource_type = get_resource_type(model)
            if resource_type in model_types:
                resource_id = get_resource_id(model)
                args_update(self.getters[resource_type])
            elif resource_type == MODEL_PATH:
                resource_id = get_model_id(model)
                args_update(self.get_model)
            else:
                raise Exception("A model or ensemble id is needed as first"
                                " argument to create the resource."
                                " %s found." % resource_type)

        return dataset_id and resource_id

    ##########################################################################
    #
    # Sources
    # https://bigml.com/developers/sources
    #
    ##########################################################################
    def _create_remote_source(self, url, args=None):
        """Creates a new source using a URL

        """
        create_args = {}
        if args is not None:
            create_args.update(args)
        create_args.update({"remote": url})
        body = json.dumps(create_args)
        return self._create(self.source_url, body)

    def _create_local_source(self, file_name, args=None):
        """Creates a new source using a local file.

        This function is now DEPRECATED as "requests" do not stream the file
        content what limited the size of local files to a small number of GBs.

        """
        create_args = {}
        if args is not None:
            create_args.update(args)

        if 'source_parser' in create_args:
            create_args['source_parser'] = json.dumps(
                create_args['source_parser'])

        code = HTTP_INTERNAL_SERVER_ERROR
        resource_id = None
        location = None
        resource = None
        error = {
            "status": {
                "code": code,
                "message": "The resource couldn't be created"}}

        try:
            files = {os.path.basename(file_name): open(file_name, "rb")}
        except IOError:
            sys.exit("ERROR: cannot read training set")

        try:
            response = requests.post(self.source_url + self.auth,
                                     files=files,
                                     data=create_args, verify=self.verify)

            code = response.status_code
            if code == HTTP_CREATED:
                location = response.headers['location']
                resource = json.loads(response.content, 'utf-8')
                resource_id = resource['resource']
                error = None
            elif code in [HTTP_BAD_REQUEST,
                          HTTP_UNAUTHORIZED,
                          HTTP_PAYMENT_REQUIRED,
                          HTTP_NOT_FOUND,
                          HTTP_TOO_MANY_REQUESTS]:
                error = json.loads(response.content, 'utf-8')
            else:
                LOGGER.error("Unexpected error (%s)" % code)
                code = HTTP_INTERNAL_SERVER_ERROR

        except ValueError:
            LOGGER.error("Malformed response")
        except requests.ConnectionError, exc:
            LOGGER.error("Connection error: %s" % str(exc))
        except requests.Timeout:
            LOGGER.error("Request timed out")
        except requests.RequestException:
            LOGGER.error("Ambiguous exception occurred")

        return {
            'code': code,
            'resource': resource_id,
            'location': location,
            'object': resource,
            'error': error}

    def _upload_source(self, args, source, out=sys.stdout):
        """Uploads a source asynchronously.

        """

        def update_progress(param, current, total):
            """Updates source's progress.

            """
            progress = round(current * 1.0 / total, 2)
            if progress < 1.0:
                source['object']['status']['progress'] = progress

        resource = self._process_source(source['resource'], source['location'],
                                        source['object'],
                                        args=args, progress_bar=True,
                                        callback=update_progress, out=out)
        source['code'] = resource['code']
        source['resource'] = resource['resource']
        source['location'] = resource['location']
        source['object'] = resource['object']
        source['error'] = resource['error']

    def _stream_source(self, file_name, args=None, async=False,
                       progress_bar=False, out=sys.stdout):
        """Creates a new source.

        """

        def draw_progress_bar(param, current, total):
            """Draws a text based progress report.

            """
            pct = 100 - ((total - current) * 100) / (total)
            console_log("Uploaded %s out of %s bytes [%s%%]" % (
                localize(current), localize(total), pct))
        create_args = {}
        if args is not None:
            create_args.update(args)
        if 'source_parser' in create_args:
            create_args['source_parser'] = json.dumps(
                create_args['source_parser'])

        resource_id = None
        location = None
        resource = None
        error = None

        try:
            if isinstance(file_name, basestring):
                create_args.update({os.path.basename(file_name):
                                    open(file_name, "rb")})
            else:
                create_args = create_args.items()
                name = '<none>'
                create_args.append(MultipartParam(name, filename=name,
                                                  fileobj=file_name))

        except IOError, exception:
            sys.exit("Error: cannot read training set. %s" % str(exception))

        if async:
            source = {
                'code': HTTP_ACCEPTED,
                'resource': resource_id,
                'location': location,
                'object': {'status': {'message': 'The upload is in progress',
                                      'code': UPLOADING,
                                      'progress': 0.0}},
                'error': error}
            upload_args = (create_args, source)
            thread = Thread(target=self._upload_source,
                            args=upload_args,
                            kwargs={'out': out})
            thread.start()
            return source
        return self._process_source(resource_id, location, resource,
                                    args=create_args,
                                    progress_bar=progress_bar,
                                    callback=draw_progress_bar, out=out)

    def _process_source(self, resource_id, location, resource,
                        args=None, progress_bar=False, callback=None,
                        out=sys.stdout):
        """Creates a new source.

        """
        code = HTTP_INTERNAL_SERVER_ERROR
        error = {
            "status": {
                "code": code,
                "message": "The resource couldn't be created"}}

        if progress_bar and callback is not None:
            body, headers = multipart_encode(args, cb=callback)
        else:
            body, headers = multipart_encode(args)

        request = urllib2.Request(self.source_url + self.auth, body, headers)

        try:
            response = urllib2.urlopen(request)
            clear_console_line(out=out)
            reset_console_line(out=out)
            code = response.getcode()
            if code == HTTP_CREATED:
                location = response.headers['location']
                content = response.read()
                resource = json.loads(content, 'utf-8')
                resource_id = resource['resource']
                error = {}
        except ValueError:
            LOGGER.error("Malformed response")
        except urllib2.HTTPError, exception:
            code = exception.code
            if code in [HTTP_BAD_REQUEST,
                        HTTP_UNAUTHORIZED,
                        HTTP_PAYMENT_REQUIRED,
                        HTTP_NOT_FOUND,
                        HTTP_TOO_MANY_REQUESTS]:
                content = exception.read()
                error = json.loads(content, 'utf-8')
                LOGGER.error(self.error_message(error, method='create'))
            else:
                LOGGER.error("Unexpected error (%s)" % code)
                code = HTTP_INTERNAL_SERVER_ERROR

        except urllib2.URLError, exception:
            LOGGER.error("Error establishing connection: %s" % str(exception))
            error = exception.args
        return {
            'code': code,
            'resource': resource_id,
            'location': location,
            'object': resource,
            'error': error}

    def create_source(self, path=None, args=None, async=False,
                      progress_bar=False, out=sys.stdout):
        """Creates a new source.

           The source can be a local file path or a URL.

        """

        if path is None:
            raise Exception('A local path or a valid URL must be provided.')

        if is_url(path):
            return self._create_remote_source(url=path, args=args)
        else:
            return self._stream_source(file_name=path, args=args, async=async,
                                       progress_bar=progress_bar, out=out)

    def get_source(self, source, query_string=''):
        """Retrieves a remote source.

           The source parameter should be a string containing the
           source id or the dict returned by create_source.
           As source is an evolving object that is processed
           until it reaches the FINISHED or FAULTY state, thet function will
           return a dict that encloses the source values and state info
           available at the time it is called.

        """
        check_resource_type(source, SOURCE_PATH,
                            message="A source id is needed.")
        source_id = get_source_id(source)
        if source_id:
            return self._get("%s%s" % (self.url, source_id),
                             query_string=query_string)

    def source_is_ready(self, source):
        """Checks whether a source' status is FINISHED.

        """
        check_resource_type(source, SOURCE_PATH,
                            message="A source id is needed.")
        source = self.get_source(source)
        return resource_is_ready(source)

    def list_sources(self, query_string=''):
        """Lists all your remote sources.

        """
        return self._list(self.source_url, query_string)

    def update_source(self, source, changes):
        """Updates a source.

        Updates remote `source` with `changes'.

        """
        check_resource_type(source, SOURCE_PATH,
                            message="A source id is needed.")
        source_id = get_source_id(source)
        if source_id:
            body = json.dumps(changes)
            return self._update("%s%s" % (self.url, source_id), body)

    def delete_source(self, source):
        """Deletes a remote source permanently.

        """
        check_resource_type(source, SOURCE_PATH,
                            message="A source id is needed.")
        source_id = get_source_id(source)
        if source_id:
            return self._delete("%s%s" % (self.url, source_id))

    ##########################################################################
    #
    # Datasets
    # https://bigml.com/developers/datasets
    #
    ##########################################################################
    def create_dataset(self, origin_resource, args=None,
                       wait_time=3, retries=10):
        """Creates a remote dataset.

        Uses a remote resource to create a new dataset using the
        arguments in `args`.
        The allowed remote resources can be:
            - source
            - dataset
            - list of datasets
            - cluster
        In the case of using cluster id as origin_resources, a centroid must
        also be provided in the args argument. The first centroid is used
        otherwise.
        If `wait_time` is higher than 0 then the dataset creation
        request is not sent until the `source` has been created successfuly.

        """
        create_args = {}
        if args is not None:
            create_args.update(args)

        if isinstance(origin_resource, list):
            # mutidatasets
            create_args = self._set_create_from_datasets_args(
                origin_resource, args=create_args, wait_time=wait_time,
                retries=retries, key="origin_datasets")
        else:
            # dataset from source
            resource_type = get_resource_type(origin_resource)
            if resource_type == SOURCE_PATH:
                source_id = get_source_id(origin_resource)
                if source_id:
                    check_resource(source_id, self.get_source,
                                   wait_time=wait_time,
                                   retries=retries,
                                   raise_on_error=True)
                    create_args.update({
                        "source": source_id})
            # dataset from dataset
            elif resource_type == DATASET_PATH:
                create_args = self._set_create_from_datasets_args(
                    origin_resource, args=create_args, wait_time=wait_time,
                    retries=retries, key="origin_dataset")
            # dataset from cluster and centroid
            elif resource_type == CLUSTER_PATH:
                cluster_id = get_cluster_id(origin_resource)
                cluster = check_resource(cluster_id, self.get_cluster,
                                         wait_time=wait_time,
                                         retries=retries,
                                         raise_on_error=True)
                if not 'centroid' in create_args:
                    try:
                        centroid = cluster['object'][
                            'cluster_datasets_ids'].keys()[0]
                        create_args.update({'centroid': centroid})
                    except KeyError:
                        raise KeyError("Failed to generate the dataset. A "
                                       "centroid id is needed in the args "
                                       "argument to generate a dataset from "
                                       "a cluster.")
                create_args.update({'cluster': cluster_id})
            else:
                raise Exception("A source, dataset, list of dataset ids"
                                " or cluster id plus centroid id are needed"
                                " to create a"
                                " dataset. %s found." % resource_type)

        body = json.dumps(create_args)
        return self._create(self.dataset_url, body)

    def get_dataset(self, dataset, query_string=''):
        """Retrieves a dataset.

           The dataset parameter should be a string containing the
           dataset id or the dict returned by create_dataset.
           As dataset is an evolving object that is processed
           until it reaches the FINISHED or FAULTY state, the function will
           return a dict that encloses the dataset values and state info
           available at the time it is called.
        """
        check_resource_type(dataset, DATASET_PATH,
                            message="A dataset id is needed.")
        dataset_id = get_dataset_id(dataset)
        if dataset_id:
            return self._get("%s%s" % (self.url, dataset_id),
                             query_string=query_string)

    def dataset_is_ready(self, dataset):
        """Check whether a dataset' status is FINISHED.

        """
        check_resource_type(dataset, DATASET_PATH,
                            message="A dataset id is needed.")
        resource = self.get_dataset(dataset)
        return resource_is_ready(resource)

    def list_datasets(self, query_string=''):
        """Lists all your datasets.

        """
        return self._list(self.dataset_url, query_string)

    def update_dataset(self, dataset, changes):
        """Updates a dataset.

        """
        check_resource_type(dataset, DATASET_PATH,
                            message="A dataset id is needed.")
        dataset_id = get_dataset_id(dataset)
        if dataset_id:
            body = json.dumps(changes)
            return self._update("%s%s" % (self.url, dataset_id), body)

    def delete_dataset(self, dataset):
        """Deletes a dataset.

        """
        check_resource_type(dataset, DATASET_PATH,
                            message="A dataset id is needed.")
        dataset_id = get_dataset_id(dataset)
        if dataset_id:
            return self._delete("%s%s" % (self.url, dataset_id))

    def error_counts(self, dataset, raise_on_error=True):
        """Returns the ids of the fields that contain errors and their number.

           The dataset argument can be either a dataset resource structure
           or a dataset id (that will be used to retrieve the associated
           remote resource).

        """
        errors_dict = {}
        if not isinstance(dataset, dict) or not 'object' in dataset:
            check_resource_type(dataset, DATASET_PATH,
                                message="A dataset id is needed.")
            dataset_id = get_dataset_id(dataset)
            dataset = check_resource(dataset_id, self.get_dataset,
                                     raise_on_error=raise_on_error)
            if not raise_on_error and dataset['error'] is not None:
                dataset_id = None
        else:
            dataset_id = get_dataset_id(dataset)
        if dataset_id:
            errors = dataset.get('object', {}).get(
                'status', {}).get('field_errors', {})
            for field_id in errors:
                errors_dict[field_id] = errors[field_id]['total']
        return errors_dict

    ##########################################################################
    #
    # Models
    # https://bigml.com/developers/models
    #
    ##########################################################################
    def create_model(self, datasets, args=None, wait_time=3, retries=10):
        """Creates a model from a `dataset` or a list o `datasets`.

        """
        create_args = self._set_create_from_datasets_args(
            datasets, args=args, wait_time=wait_time, retries=retries)

        body = json.dumps(create_args)
        return self._create(self.model_url, body)

    def get_model(self, model, query_string='',
                  shared_username=None, shared_api_key=None):
        """Retrieves a model.

           The model parameter should be a string containing the
           model id or the dict returned by create_model.
           As model is an evolving object that is processed
           until it reaches the FINISHED or FAULTY state, the function will
           return a dict that encloses the model values and state info
           available at the time it is called.

           If this is a shared model, the username and sharing api key must
           also be provided.
        """
        check_resource_type(model, MODEL_PATH,
                            message="A model id is needed.")
        model_id = get_model_id(model)
        if model_id:
            return self._get("%s%s" % (self.url, model_id),
                             query_string=query_string,
                             shared_username=shared_username,
                             shared_api_key=shared_api_key)

    def model_is_ready(self, model, **kwargs):
        """Checks whether a model's status is FINISHED.

        """
        check_resource_type(model, MODEL_PATH,
                            message="A model id is needed.")
        resource = self.get_model(model, **kwargs)
        return resource_is_ready(resource)

    def list_models(self, query_string=''):
        """Lists all your models.

        """
        return self._list(self.model_url, query_string)

    def update_model(self, model, changes):
        """Updates a model.

        """
        check_resource_type(model, MODEL_PATH,
                            message="A model id is needed.")
        model_id = get_model_id(model)
        if model_id:
            body = json.dumps(changes)
            return self._update("%s%s" % (self.url, model_id), body)

    def delete_model(self, model):
        """Deletes a model.

        """
        check_resource_type(model, MODEL_PATH,
                            message="A model id is needed.")
        model_id = get_model_id(model)
        if model_id:
            return self._delete("%s%s" % (self.url, model_id))

    ##########################################################################
    #
    # Predictions
    # https://bigml.com/developers/predictions
    #
    ##########################################################################
    def create_prediction(self, model, input_data=None,
                          args=None, wait_time=3, retries=10, by_name=True):
        """Creates a new prediction.
           The model parameter can be:
            - a simple model
            - an ensemble
           The by_name argument is now deprecated. It will be removed.

        """
        ensemble_id = None
        model_id = None

        resource_type = get_resource_type(model)
        if resource_type == ENSEMBLE_PATH:
            ensemble_id = get_ensemble_id(model)
            if ensemble_id is not None:
                check_resource(ensemble_id, self.get_ensemble,
                               wait_time=wait_time, retries=retries,
                               raise_on_error=True)
        elif resource_type == MODEL_PATH:
            model_id = get_model_id(model)
            check_resource(model_id, self.get_model,
                           query_string=TINY_MODEL,
                           wait_time=wait_time, retries=retries,
                           raise_on_error=True)
        else:
            raise Exception("A model or ensemble id is needed to create a"
                            " prediction. %s found." % resource_type)

        if input_data is None:
            input_data = {}
        create_args = {}
        if args is not None:
            create_args.update(args)
        create_args.update({
            "input_data": input_data})
        if ensemble_id is None:
            create_args.update({
                "model": model_id})
        else:
            create_args.update({
                "ensemble": ensemble_id})

        body = json.dumps(create_args)
        return self._create(self.prediction_url, body,
                            verify=self.verify_prediction)

    def get_prediction(self, prediction):
        """Retrieves a prediction.

        """
        check_resource_type(prediction, PREDICTION_PATH,
                            message="A prediction id is needed.")
        prediction_id = get_prediction_id(prediction)
        if prediction_id:
            return self._get("%s%s" % (self.url, prediction_id))

    def list_predictions(self, query_string=''):
        """Lists all your predictions.

        """
        return self._list(self.prediction_url, query_string)

    def update_prediction(self, prediction, changes):
        """Updates a prediction.

        """
        check_resource_type(prediction, PREDICTION_PATH,
                            message="A prediction id is needed.")
        prediction_id = get_prediction_id(prediction)
        if prediction_id:
            body = json.dumps(changes)
            return self._update("%s%s" % (self.url, prediction_id), body)

    def delete_prediction(self, prediction):
        """Deletes a prediction.

        """
        check_resource_type(prediction, PREDICTION_PATH,
                            message="A prediction id is needed.")
        prediction_id = get_prediction_id(prediction)
        if prediction_id:
            return self._delete("%s%s" % (self.url, prediction_id))

    ##########################################################################
    #
    # Evaluations
    # https://bigml.com/developers/evaluations
    #
    ##########################################################################
    def create_evaluation(self, model, dataset,
                          args=None, wait_time=3, retries=10):
        """Creates a new evaluation.

        """
        create_args = {}
        if args is not None:
            create_args.update(args)

        model_types = [ENSEMBLE_PATH, MODEL_PATH]
        origin_resources_checked = self.check_origins(
            dataset, model, create_args, model_types=model_types,
            wait_time=wait_time, retries=retries)

        if origin_resources_checked:
            body = json.dumps(create_args)
            return self._create(self.evaluation_url, body)

    def get_evaluation(self, evaluation):
        """Retrieves an evaluation.

           The evaluation parameter should be a string containing the
           evaluation id or the dict returned by create_evaluation.
           As evaluation is an evolving object that is processed
           until it reaches the FINISHED or FAULTY state, the function will
           return a dict that encloses the evaluation values and state info
           available at the time it is called.
        """
        check_resource_type(evaluation, EVALUATION_PATH,
                            message="An evaluation id is needed.")
        evaluation_id = get_evaluation_id(evaluation)
        if evaluation_id:
            return self._get("%s%s" % (self.url, evaluation_id))

    def list_evaluations(self, query_string=''):
        """Lists all your evaluations.

        """
        return self._list(self.evaluation_url, query_string)

    def update_evaluation(self, evaluation, changes):
        """Updates an evaluation.

        """
        check_resource_type(evaluation, EVALUATION_PATH,
                            message="An evaluation id is needed.")
        evaluation_id = get_evaluation_id(evaluation)
        if evaluation_id:
            body = json.dumps(changes)
            return self._update("%s%s" % (self.url, evaluation_id), body)

    def delete_evaluation(self, evaluation):
        """Deletes an evaluation.

        """
        check_resource_type(evaluation, EVALUATION_PATH,
                            message="An evaluation id is needed.")
        evaluation_id = get_evaluation_id(evaluation)
        if evaluation_id:
            return self._delete("%s%s" % (self.url, evaluation_id))

    ##########################################################################
    #
    # Ensembles
    # https://bigml.com/developers/ensembles
    #
    ##########################################################################
    def create_ensemble(self, datasets, args=None, wait_time=3, retries=10):
        """Creates an ensemble from a dataset or a list of datasets.

        """

        create_args = self._set_create_from_datasets_args(
            datasets, args=args, wait_time=wait_time, retries=retries)

        body = json.dumps(create_args)
        return self._create(self.ensemble_url, body)

    def get_ensemble(self, ensemble, query_string=''):
        """Retrieves an ensemble.

           The ensemble parameter should be a string containing the
           ensemble id or the dict returned by create_ensemble.
           As an ensemble is an evolving object that is processed
           until it reaches the FINISHED or FAULTY state, the function will
           return a dict that encloses the ensemble values and state info
           available at the time it is called.
        """
        check_resource_type(ensemble, ENSEMBLE_PATH,
                            message="An ensemble id is needed.")
        ensemble_id = get_ensemble_id(ensemble)
        if ensemble_id:
            return self._get("%s%s" % (self.url, ensemble_id),
                             query_string=query_string)

    def ensemble_is_ready(self, ensemble):
        """Checks whether a ensemble's status is FINISHED.

        """
        check_resource_type(ensemble, ENSEMBLE_PATH,
                            message="An ensemble id is needed.")
        resource = self.get_ensemble(ensemble)
        return resource_is_ready(resource)

    def list_ensembles(self, query_string=''):
        """Lists all your ensembles.

        """
        return self._list(self.ensemble_url, query_string)

    def update_ensemble(self, ensemble, changes):
        """Updates a ensemble.

        """
        check_resource_type(ensemble, ENSEMBLE_PATH,
                            message="An ensemble id is needed.")
        ensemble_id = get_ensemble_id(ensemble)
        if ensemble_id:
            body = json.dumps(changes)
            return self._update("%s%s" % (self.url, ensemble_id), body)

    def delete_ensemble(self, ensemble):
        """Deletes a ensemble.

        """
        check_resource_type(ensemble, ENSEMBLE_PATH,
                            message="An ensemble id is needed.")
        ensemble_id = get_ensemble_id(ensemble)
        if ensemble_id:
            return self._delete("%s%s" % (self.url, ensemble_id))

    ##########################################################################
    #
    # Batch Predictions
    # https://bigml.com/developers/batch_predictions
    #
    ##########################################################################
    def create_batch_prediction(self, model, dataset,
                                args=None, wait_time=3, retries=10):
        """Creates a new batch prediction.

           The model parameter can be:
            - a simple model
            - an ensemble

        """
        create_args = {}
        if args is not None:
            create_args.update(args)

        model_types = [ENSEMBLE_PATH, MODEL_PATH]
        origin_resources_checked = self.check_origins(
            dataset, model, create_args, model_types=model_types,
            wait_time=wait_time, retries=retries)
        if origin_resources_checked:
            body = json.dumps(create_args)
            return self._create(self.batch_prediction_url, body)

    def get_batch_prediction(self, batch_prediction):
        """Retrieves a batch prediction.

           The batch_prediction parameter should be a string containing the
           batch_prediction id or the dict returned by create_batch_prediction.
           As batch_prediction is an evolving object that is processed
           until it reaches the FINISHED or FAULTY state, the function will
           return a dict that encloses the batch_prediction values and state
           info available at the time it is called.
        """
        check_resource_type(batch_prediction, BATCH_PREDICTION_PATH,
                            message="A batch prediction id is needed.")
        batch_prediction_id = get_batch_prediction_id(batch_prediction)
        if batch_prediction_id:
            return self._get("%s%s" % (self.url, batch_prediction_id))

    def download_batch_prediction(self, batch_prediction, filename=None):
        """Retrieves the batch predictions file.

           Downloads predictions, that are stored in a remote CSV file. If
           a path is given in filename, the contents of the file are downloaded
           and saved locally. A file-like object is returned otherwise.
        """
        check_resource_type(batch_prediction, BATCH_PREDICTION_PATH,
                            message="A batch prediction id is needed.")
        batch_prediction_id = get_batch_prediction_id(batch_prediction)
        if batch_prediction_id:
            return self._download("%s%s%s" % (self.url, batch_prediction_id,
                                              DOWNLOAD_DIR), filename=filename)

    def list_batch_predictions(self, query_string=''):
        """Lists all your batch predictions.

        """
        return self._list(self.batch_prediction_url, query_string)

    def update_batch_prediction(self, batch_prediction, changes):
        """Updates a batch prediction.

        """
        check_resource_type(batch_prediction, BATCH_PREDICTION_PATH,
                            message="A batch prediction id is needed.")
        batch_prediction_id = get_batch_prediction_id(batch_prediction)
        if batch_prediction_id:
            body = json.dumps(changes)
            return self._update("%s%s" % (self.url, batch_prediction_id), body)

    def delete_batch_prediction(self, batch_prediction):
        """Deletes a batch prediction.

        """
        check_resource_type(batch_prediction, BATCH_PREDICTION_PATH,
                            message="A batch prediction id is needed.")
        batch_prediction_id = get_batch_prediction_id(batch_prediction)
        if batch_prediction_id:
            return self._delete("%s%s" % (self.url, batch_prediction_id))

    ##########################################################################
    #
    # Clusters
    # https://bigml.com/developers/clusters
    #
    ##########################################################################
    def create_cluster(self, datasets, args=None, wait_time=3, retries=10):
        """Creates a cluster from a `dataset` or a list o `datasets`.

        """
        create_args = self._set_create_from_datasets_args(
            datasets, args=args, wait_time=wait_time, retries=retries)

        body = json.dumps(create_args)
        return self._create(self.cluster_url, body)

    def get_cluster(self, cluster, query_string='',
                    shared_username=None, shared_api_key=None):
        """Retrieves a cluster.

           The model parameter should be a string containing the
           cluster id or the dict returned by create_cluster.
           As cluster is an evolving object that is processed
           until it reaches the FINISHED or FAULTY state, the function will
           return a dict that encloses the cluster values and state info
           available at the time it is called.

           If this is a shared cluster, the username and sharing api key must
           also be provided.
        """
        check_resource_type(cluster, CLUSTER_PATH,
                            message="A cluster id is needed.")
        cluster_id = get_cluster_id(cluster)
        if cluster_id:
            return self._get("%s%s" % (self.url, cluster_id),
                             query_string=query_string,
                             shared_username=shared_username,
                             shared_api_key=shared_api_key)

    def cluster_is_ready(self, cluster, **kwargs):
        """Checks whether a cluster's status is FINISHED.

        """
        check_resource_type(cluster, CLUSTER_PATH,
                            message="A cluster id is needed.")
        resource = self.get_cluster(cluster, **kwargs)
        return resource_is_ready(resource)

    def list_clusters(self, query_string=''):
        """Lists all your clusters.

        """
        return self._list(self.cluster_url, query_string)

    def update_cluster(self, cluster, changes):
        """Updates a cluster.

        """
        check_resource_type(cluster, CLUSTER_PATH,
                            message="A cluster id is needed.")
        cluster_id = get_cluster_id(cluster)
        if cluster_id:
            body = json.dumps(changes)
            return self._update("%s%s" % (self.url, cluster_id), body)

    def delete_cluster(self, cluster):
        """Deletes a cluster.

        """
        check_resource_type(cluster, CLUSTER_PATH,
                            message="A cluster id is needed.")
        cluster_id = get_cluster_id(cluster)
        if cluster_id:
            return self._delete("%s%s" % (self.url, cluster_id))

    ##########################################################################
    #
    # Centroids
    # https://bigml.com/developers/centroids
    #
    ##########################################################################
    def create_centroid(self, cluster, input_data=None,
                        args=None, wait_time=3, retries=10):
        """Creates a new centroid.

        """
        cluster_id = None
        resource_type = get_resource_type(cluster)
        if resource_type == CLUSTER_PATH:
            cluster_id = get_cluster_id(cluster)
            check_resource(cluster_id, self.get_cluster,
                           query_string=TINY_MODEL,
                           wait_time=wait_time, retries=retries,
                           raise_on_error=True)
        else:
            raise Exception("A cluster id is needed to create a"
                            " centroid. %s found." % resource_type)

        if input_data is None:
            input_data = {}
        create_args = {}
        if args is not None:
            create_args.update(args)
        create_args.update({
            "input_data": input_data})
        create_args.update({
            "cluster": cluster_id})

        body = json.dumps(create_args)
        return self._create(self.centroid_url, body,
                            verify=self.verify)

    def get_centroid(self, centroid):
        """Retrieves a centroid.

        """
        check_resource_type(centroid, CENTROID_PATH,
                            message="A centroid id is needed.")
        centroid_id = get_centroid_id(centroid)
        if centroid_id:
            return self._get("%s%s" % (self.url, centroid_id))

    def list_centroids(self, query_string=''):
        """Lists all your centroids.

        """
        return self._list(self.centroid_url, query_string)

    def update_centroid(self, centroid, changes):
        """Updates a centroid.

        """
        check_resource_type(centroid, CENTROID_PATH,
                            message="A centroid id is needed.")
        centroid_id = get_centroid_id(centroid)
        if centroid_id:
            body = json.dumps(changes)
            return self._update("%s%s" % (self.url, centroid_id), body)

    def delete_centroid(self, centroid):
        """Deletes a centroid.

        """
        check_resource_type(centroid, CENTROID_PATH,
                            message="A centroid id is needed.")
        centroid_id = get_centroid_id(centroid)
        if centroid_id:
            return self._delete("%s%s" % (self.url, centroid_id))

    ##########################################################################
    #
    # Batch Centroids
    # https://bigml.com/developers/batch_centroids
    #
    ##########################################################################
    def create_batch_centroid(self, cluster, dataset,
                              args=None, wait_time=3, retries=10):
        """Creates a new batch centroid.


        """
        create_args = {}
        if args is not None:
            create_args.update(args)

        model_types = [CLUSTER_PATH]
        origin_resources_checked = self.check_origins(
            dataset, cluster, create_args, model_types=model_types,
            wait_time=wait_time, retries=retries)

        if origin_resources_checked:
            body = json.dumps(create_args)
            return self._create(self.batch_centroid_url, body)

    def get_batch_centroid(self, batch_centroid):
        """Retrieves a batch centroid.

           The batch_centroid parameter should be a string containing the
           batch_centroid id or the dict returned by create_batch_centroid.
           As batch_centroid is an evolving object that is processed
           until it reaches the FINISHED or FAULTY state, the function will
           return a dict that encloses the batch_centroid values and state
           info available at the time it is called.
        """
        check_resource_type(batch_centroid, BATCH_CENTROID_PATH,
                            message="A batch centroid id is needed.")
        batch_centroid_id = get_batch_centroid_id(batch_centroid)
        if batch_centroid_id:
            return self._get("%s%s" % (self.url, batch_centroid_id))

    def download_batch_centroid(self, batch_centroid, filename=None):
        """Retrieves the batch centroid file.

           Downloads centroids, that are stored in a remote CSV file. If
           a path is given in filename, the contents of the file are downloaded
           and saved locally. A file-like object is returned otherwise.
        """
        check_resource_type(batch_centroid, BATCH_CENTROID_PATH,
                            message="A batch centroid id is needed.")
        batch_centroid_id = get_batch_centroid_id(batch_centroid)
        if batch_centroid_id:
            return self._download("%s%s%s" % (self.url, batch_centroid_id,
                                              DOWNLOAD_DIR), filename=filename)

    def list_batch_centroids(self, query_string=''):
        """Lists all your batch centroids.

        """
        return self._list(self.batch_centroid_url, query_string)

    def update_batch_centroid(self, batch_centroid, changes):
        """Updates a batch centroid.

        """
        check_resource_type(batch_centroid, BATCH_CENTROID_PATH,
                            message="A batch centroid id is needed.")
        batch_centroid_id = get_batch_centroid_id(batch_centroid)
        if batch_centroid_id:
            body = json.dumps(changes)
            return self._update("%s%s" % (self.url, batch_centroid_id), body)

    def delete_batch_centroid(self, batch_centroid):
        """Deletes a batch centroid.

        """
        check_resource_type(batch_centroid, BATCH_CENTROID_PATH,
                            message="A batch centroid id is needed.")
        batch_centroid_id = get_batch_centroid_id(batch_centroid)
        if batch_centroid_id:
            return self._delete("%s%s" % (self.url, batch_centroid_id))

########NEW FILE########
__FILENAME__ = basemodel
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2013-2014 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A BasicModel resource.

This module defines a BasicModel to hold the main information of the model
resource in BigML. It becomes the starting point for the Model class, that
is used for local predictions.

"""
import logging
LOGGER = logging.getLogger('BigML')

import sys
import locale
import os
import json

from bigml.api import FINISHED
from bigml.api import (get_status, BigML, get_model_id,
                       check_resource)
from bigml.util import invert_dictionary, utf8
from bigml.util import DEFAULT_LOCALE

# Query string to ask for fields: only the ones in the model, with summary
# (needed for the list of terms in text fields) and
# no pagination (all the model fields)
ONLY_MODEL = 'only_model=true;limit=-1;'


def retrieve_model(api, model_id, query_string=''):
    """ Retrieves model info either from a local repo or from the remote server

    """
    if api.storage is not None:
        try:
            with open("%s%s%s" % (api.storage, os.sep,
                                  model_id.replace("/", "_"))) as model_file:
                model = json.loads(model_file.read())
            return model
        except ValueError:
            raise ValueError("The file %s contains no JSON")
        except IOError:
            pass
    model = check_resource(model_id, api.get_model, query_string)
    return model


def extract_objective(objective_field):
    """Extract the objective field id from the model structure

    """
    if isinstance(objective_field, list):
        return objective_field[0]
    return objective_field


def print_importance(instance, out=sys.stdout):
    """Print a field importance structure

    """
    count = 1
    field_importance, fields = instance.field_importance_data()
    for [field, importance] in field_importance:
        out.write(utf8(u"    %s. %s: %.2f%%\n" % (count,
                       fields[field]['name'],
                       round(importance, 4) * 100)))
        count += 1


def check_model_structure(model):
    """Checks the model structure to see if it contains all the needed keys

    """
    return (isinstance(model, dict) and 'resource' in model and
            model['resource'] is not None and
            ('object' in model and 'model' in model['object'] or
             'model' in model))


class BaseModel(object):
    """ A lightweight wrapper of the basic model information

    Uses a BigML remote model to build a local version that contains the
    main features of a model, except its tree structure.

    """

    def __init__(self, model, api=None):

        if check_model_structure(model):
            self.resource_id = model['resource']
        else:
            # If only the model id is provided, the short version of the model
            # resource is used to build a basic summary of the model
            if api is None:
                api = BigML()
            self.resource_id = get_model_id(model)
            if self.resource_id is None:
                raise Exception(api.error_message(model,
                                                  resource_type='model',
                                                  method='get'))
            query_string = ONLY_MODEL
            model = retrieve_model(api, self.resource_id,
                                   query_string=query_string)
            # Stored copies of the model structure might lack some necessary
            # keys
            if not check_model_structure(model):
                model = api.get_model(self.resource_id,
                                      query_string=query_string)

        if ('object' in model and isinstance(model['object'], dict)):
            model = model['object']

        if ('model' in model and isinstance(model['model'], dict)):
            status = get_status(model)
            if ('code' in status and status['code'] == FINISHED):
                if 'model_fields' in model['model']:
                    fields = model['model']['model_fields']
                    # pagination or exclusion might cause a field not to
                    # be in available fields dict
                    if not all(key in model['model']['fields']
                               for key in fields.keys()):
                        raise Exception("Some fields are missing"
                                        " to generate a local model."
                                        " Please, provide a model with"
                                        " the complete list of fields.")
                    for field in fields:
                        field_info = model['model']['fields'][field]
                        if 'summary' in field_info:
                            fields[field]['summary'] = field_info['summary']
                        fields[field]['name'] = field_info['name']
                objective_field = model['objective_fields']
                self.objective_field = extract_objective(objective_field)
                self.uniquify_varnames(fields)
                self.inverted_fields = invert_dictionary(fields)
                self.fields = fields
                self.description = model['description']
                self.field_importance = model['model'].get('importance',
                                                           None)
                if self.field_importance:
                    self.field_importance = [element for element
                                             in self.field_importance
                                             if element[0] in fields]
                self.locale = model.get('locale', DEFAULT_LOCALE)

            else:
                raise Exception("The model isn't finished yet")
        else:
            raise Exception("Cannot create the BaseModel instance. Could not"
                            " find the 'model' key in the resource:\n\n%s" %
                            model)

    def uniquify_varnames(self, fields):
        """Tests if the fields names are unique. If they aren't, a
           transformation is applied to ensure unicity.

        """
        unique_names = set([fields[key]['name'] for key in fields])
        if len(unique_names) < len(fields):
            self.transform_repeated_names(fields)

    def transform_repeated_names(self, fields):
        """If a field name is repeated, it will be transformed adding its
           column number. If that combination is also a field name, the
           field id will be added.

        """
        # The objective field treated first to avoid changing it.
        unique_names = [fields[self.objective_field]['name']]

        field_ids = [field_id for field_id in fields
                     if field_id != self.objective_field]
        for field_id in field_ids:
            new_name = fields[field_id]['name']
            if new_name in unique_names:
                new_name = "{0}{1}".format(fields[field_id]['name'],
                                           fields[field_id]['column_number'])
                if new_name in unique_names:
                    new_name = "{0}_{1}".format(new_name, field_id)
                fields[field_id]['name'] = new_name
            unique_names.append(new_name)

    def resource(self):
        """Returns the model resource ID

        """
        return self.resource_id

    def field_importance_data(self):
        """Returns field importance related info

        """
        return self.field_importance, self.fields

    def print_importance(self, out=sys.stdout):
        """Prints the importance data

        """
        print_importance(self, out=out)

########NEW FILE########
__FILENAME__ = domain
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2014 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Domain class to handle domain assignation for VPCs

"""
import os
import requests

# Default domain and protocol
DEFAULT_DOMAIN = 'bigml.io'
DEFAULT_PROTOCOL = 'https'

# Base Domain
BIGML_DOMAIN = os.environ.get('BIGML_DOMAIN', DEFAULT_DOMAIN)

# Domain for prediction server
BIGML_PREDICTION_DOMAIN = os.environ.get('BIGML_PREDICTION_DOMAIN',
                                         BIGML_DOMAIN)

# Protocol for prediction server
BIGML_PREDICTION_PROTOCOL = os.environ.get('BIGML_PREDICTION_PROTOCOL',
                                           DEFAULT_PROTOCOL)


class Domain(object):
    """A Domain object to store the remote domain information for the API

       The domain that serves the remote resources can be set globally for
       all the resources either by setting the BIGML_DOMAIN environment
       variable

       export BIGML_DOMAIN=my_VPC.bigml.io

       or can be given in the constructor using the `domain` argument.

       my_domain = Domain("my_VPC.bigml.io")

       You can also specify a separate domain to handle predictions. This can
       be set by using the BIGML_PREDICTION_DOMAIN and
       BIGML_PREDICTION_PROTOCOL
       environment variables

       export BIGML_PREDICTION_DOMAIN=my_prediction_server.bigml.com
       export BIGML_PREDICITION_PROTOCOL=https

       or the `prediction_server` and `prediction_protocol` arguments.

       The constructor values will override the environment settings.
    """

    def __init__(self, domain=None, prediction_domain=None,
                 prediction_protocol=None):
        # Base domain for remote resources
        self.general_domain = BIGML_DOMAIN if domain is None else domain
        
        # Usually, predictions are served from the same domain
        if prediction_domain is None:
            if domain is not None:
                self.prediction_domain = domain
                self.prediction_protocol = DEFAULT_PROTOCOL
            else:
                self.prediction_domain = BIGML_PREDICTION_DOMAIN
                self.prediction_protocol = BIGML_PREDICTION_PROTOCOL
        # If the domain for predictions is different from the general domain,
        # for instance in high-availability prediction servers
        else:
            self.prediction_domain = prediction_domain
            if prediction_protocol is None:
                self.prediction_protocol = BIGML_PREDICTION_PROTOCOL
            else:
                self.prediction_protocol = prediction_protocol

        # Check SSL when comming from `bigml.io` subdomains
        self.verify = self.general_domain.lower().endswith(DEFAULT_DOMAIN)
        self.verify_prediction = (
            (self.prediction_domain.lower().endswith(DEFAULT_DOMAIN) and
             self.prediction_protocol == DEFAULT_PROTOCOL))

########NEW FILE########
__FILENAME__ = ensemble
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2012-2014 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""An local Ensemble object.

This module defines an Ensemble to make predictions locally using its
associated models.

This module can not only save you a few credits, but also enormously
reduce the latency for each prediction and let you use your models
offline.

from bigml.api import BigML
from bigml.ensemble import Ensemble

# api connection
api = BigML(storage='./storage')

# creating ensemble
ensemble = api.create_ensemble('dataset/5143a51a37203f2cf7000972')

# Ensemble object to predict
ensemble = Ensemble(ensemble, api)
ensemble.predict({"petal length": 3, "petal width": 1})

"""
import sys
import logging
LOGGER = logging.getLogger('BigML')

from bigml.api import BigML, get_ensemble_id, get_model_id, check_resource
from bigml.model import Model, retrieve_model, print_distribution
from bigml.model import STORAGE, ONLY_MODEL
from bigml.multivote import MultiVote
from bigml.multivote import PLURALITY_CODE
from bigml.multimodel import MultiModel
from bigml.basemodel import BaseModel, print_importance


class Ensemble(object):
    """A local predictive Ensemble.

       Uses a number of BigML remote models to build an ensemble local version
       that can be used to generate predictions locally.

    """

    def __init__(self, ensemble, api=None, max_models=None):

        if api is None:
            self.api = BigML(storage=STORAGE)
        else:
            self.api = api
        self.ensemble_id = None
        if isinstance(ensemble, list):
            try:
                models = [get_model_id(model) for model in ensemble]
            except ValueError:
                raise ValueError('Failed to verify the list of models. Check '
                                 'your model id values.')
            self.distributions = None
        else:
            self.ensemble_id = get_ensemble_id(ensemble)
            ensemble = check_resource(ensemble, self.api.get_ensemble)
            models = ensemble['object']['models']
            self.distributions = ensemble['object'].get('distributions', None)
        self.model_ids = models
        self.fields = self.all_model_fields()

        number_of_models = len(models)
        if max_models is None:
            self.models_splits = [models]
        else:
            self.models_splits = [models[index:(index + max_models)] for index
                                  in range(0, number_of_models, max_models)]
        if len(self.models_splits) == 1:
            models = [retrieve_model(self.api, model_id,
                                     query_string=ONLY_MODEL)
                      for model_id in self.models_splits[0]]
            self.multi_model = MultiModel(models, self.api)

    def list_models(self):
        """Lists all the model/ids that compound the ensemble.

        """
        return self.model_ids

    def predict(self, input_data, by_name=True, method=PLURALITY_CODE,
                with_confidence=False, options=None):
        """Makes a prediction based on the prediction made by every model.

           The method parameter is a numeric key to the following combination
           methods in classifications/regressions:
              0 - majority vote (plurality)/ average: PLURALITY_CODE
              1 - confidence weighted majority vote / error weighted:
                  CONFIDENCE_CODE
              2 - probability weighted majority vote / average:
                  PROBABILITY_CODE
              3 - threshold filtered vote / doesn't apply:
                  THRESHOLD_CODE
        """

        if len(self.models_splits) > 1:
            # If there's more than one chunck of models, they must be
            # sequentially used to generate the votes for the prediction
            votes = MultiVote([])
            for models_split in self.models_splits:
                models = [retrieve_model(self.api, model_id,
                                         query_string=ONLY_MODEL)
                          for model_id in models_split]
                multi_model = MultiModel(models, api=self.api)
                votes_split = multi_model.generate_votes(input_data,
                                                         by_name=by_name)
                votes.extend(votes_split.predictions)
        else:
            # When only one group of models is found you use the
            # corresponding multimodel to predict
            votes_split = self.multi_model.generate_votes(input_data,
                                                          by_name=by_name)
            votes = MultiVote(votes_split.predictions)
        return votes.combine(method=method, with_confidence=with_confidence,
                             options=options)

    def field_importance_data(self):
        """Computes field importance based on the field importance information
           of the individual models in the ensemble.

        """
        field_importance = {}
        field_names = {}
        if (self.distributions is not None and
                isinstance(self.distributions, list) and
                all('importance' in item for item in self.distributions)):
            # Extracts importance from ensemble information
            importances = [model_info['importance'] for model_info in
                           self.distributions]
            for index in range(0, len(importances)):
                model_info = importances[index]
                for field_info in model_info:
                    field_id = field_info[0]
                    if not field_id in field_importance:
                        field_importance[field_id] = 0.0
                        name = self.fields[field_id]['name']
                        field_names[field_id] = {'name': name}
                    field_importance[field_id] += field_info[1]
        else:
            # Old ensembles, extracts importance from model information
            for model_id in self.model_ids:
                local_model = BaseModel(model_id, api=self.api)
                for field_info in local_model.field_importance:
                    field_id = field_info[0]
                    if not field_info[0] in field_importance:
                        field_importance[field_id] = 0.0
                        name = self.fields[field_id]['name']
                        field_names[field_id] = {'name': name}
                    field_importance[field_id] += field_info[1]

        number_of_models = len(self.model_ids)
        for field_id in field_importance.keys():
            field_importance[field_id] /= number_of_models
        return map(list, sorted(field_importance.items(), key=lambda x: x[1],
                                reverse=True)), field_names

    def print_importance(self, out=sys.stdout):
        """Prints ensemble field importance

        """
        print_importance(self, out=out)

    def get_data_distribution(self, distribution_type="training"):
        """Returns the required data distribution by adding the distributions
           in the models

        """
        ensemble_distribution = []
        categories = []
        for model_distribution in self.distributions:
            summary = model_distribution[distribution_type]
            if 'bins' in summary:
                distribution = summary['bins']
            elif 'counts' in summary:
                distribution = summary['counts']
            elif 'categories' in summary:
                distribution = summary['categories']
            for point, instances in distribution:
                if point in categories:
                    ensemble_distribution[
                        categories.index(point)][1] += instances
                else:
                    categories.append(point)
                    ensemble_distribution.append([point, instances])

        return sorted(ensemble_distribution,  key=lambda x: x[0])

    def summarize(self, out=sys.stdout):
        """Prints ensemble summary. Only field importance at present.

        """
        distribution = self.get_data_distribution("training")

        out.write(u"Data distribution:\n")
        print_distribution(distribution, out=out)
        out.write(u"\n\n")

        predictions = self.get_data_distribution("predictions")

        out.write(u"Predicted distribution:\n")
        print_distribution(predictions, out=out)
        out.write(u"\n\n")

        out.write(u"Field importance:\n")
        self.print_importance(out=out)
        out.flush()

    def all_model_fields(self):
        """Retrieves the fields used as predictors in all the ensemble
           models

        """
        fields = {}
        for model_id in self.model_ids:
            local_model = Model(model_id, self.api)
            fields.update(local_model.fields)
        return fields

########NEW FILE########
__FILENAME__ = fields
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2012-2014 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A class to deal with the fields of a resource.

This module helps to map between ids, names, and column_numbers in the
fields of source, dataset, or model. Also to validate your input data
for predictions or to list all the fields from a resource.

from bigml.api import BigML
from bigml.fields import Fields

api = BigML()

source = api.get_source("source/50a6bb94eabcb404d3000174")
fields = Fields(source['object']['fields'])

dataset = api.get_dataset("dataset/50a6bb96eabcb404cd000342")
fields = Fields(dataset['object']['fields'])

# Note that the fields in a model come one level deeper
model = api.get_model("model/50a6bbac035d0706db0008f8")
fields = Fields(model['object']['model']['fields'])

prediction = api.get_prediction("prediction/50a69688035d0706dd00044d")
fields =  Fields(prediction['object']['fields'])


"""
import sys
import locale

from bigml.util import invert_dictionary, python_map_type, find_locale
from bigml.util import DEFAULT_LOCALE
from bigml.api import get_resource_type

SOURCE_TYPE = 'source'
DATASET_TYPE = 'dataset'
MODEL_TYPE = 'model'

RESOURCES_WITH_FIELDS = [SOURCE_TYPE, DATASET_TYPE, MODEL_TYPE]
DEFAULT_MISSING_TOKENS = ["", "N/A", "n/a", "NULL", "null", "-", "#DIV/0",
                          "#REF!", "#NAME?", "NIL", "nil", "NA", "na",
                          "#VALUE!", "#NULL!", "NaN", "#N/A", "#NUM!", "?"]


def get_fields_structure(resource):
    """Returns the field structure for a resource, its locale and
       missing_tokens

    """
    try:
        resource_type = get_resource_type(resource)
    except ValueError:
        raise ValueError("Unknown resource structure")

    if resource_type in RESOURCES_WITH_FIELDS:
        if resource_type == SOURCE_TYPE:
            resource_locale = resource['object']['source_parser']['locale']
            missing_tokens = resource['object'][
                'source_parser']['missing_tokens']
        else:
            resource_locale = resource['object']['locale']
            missing_tokens = resource['object']['missing_tokens']
        if resource_type == MODEL_TYPE:
            fields = resource['object']['model']['fields']
        else:
            fields = resource['object']['fields']
        return fields, resource_locale, missing_tokens
    else:
        return None, None, None


class Fields(object):
    """A class to deal with BigML auto-generated ids.

    """
    def __init__(self, resource_or_fields, missing_tokens=None,
                 data_locale=None, verbose=False,
                 objective_field=None, objective_field_present=False,
                 include=None):

        # The constructor can be instantiated with resources or a fields
        # structure. The structure is checked and fields structure is returned
        # if a resource type is matched.
        try:
            resource_info = get_fields_structure(resource_or_fields)
            (self.fields,
             resource_locale,
             resource_missing_tokens) = resource_info
            if data_locale is None:
                data_locale = resource_locale
            if missing_tokens is None:
                if resource_missing_tokens:
                    missing_tokens = resource_missing_tokens
        except ValueError:
            # If the resource structure is not in the expected set, fields
            # structure is assumed
            self.fields = resource_or_fields
            if data_locale is None:
                data_locale = DEFAULT_LOCALE
            if missing_tokens is None:
                missing_tokens = DEFAULT_MISSING_TOKENS
        if self.fields is None:
            raise ValueError("No fields structure was found.")
        self.fields_by_name = invert_dictionary(self.fields, 'name')
        self.fields_by_column_number = invert_dictionary(self.fields,
                                                         'column_number')
        find_locale(data_locale, verbose)
        self.missing_tokens = missing_tokens
        self.fields_columns = sorted(self.fields_by_column_number.keys())
        # Ids of the fields to be included
        self.filtered_fields = (self.fields.keys() if include is None
                                else include)
        # To be updated in update_objective_field
        self.row_ids = None
        self.headers = None
        self.objective_field = None
        self.objective_field_present = None
        self.filtered_indexes = None
        self.update_objective_field(objective_field, objective_field_present)

    def update_objective_field(self, objective_field, objective_field_present,
                               headers=None):
        """Updates objective_field and headers info

            Permits to update the objective_field, objective_field_present and
            headers info from the constructor and also in a per row basis.
        """
        # If no objective field, select the last column, else store its column
        if objective_field is None:
            self.objective_field = self.fields_columns[-1]
        elif isinstance(objective_field, basestring):
            self.objective_field = self.field_column_number(objective_field)
        else:
            self.objective_field = objective_field

        # If present, remove the objective field from the included fields
        objective_id = self.field_id(self.objective_field)
        if objective_id in self.filtered_fields:
            del(self.filtered_fields[self.filtered_fields.index(objective_id)])

        self.objective_field_present = objective_field_present
        if headers is None:
            # The row is supposed to contain the fields sorted by column number
            self.row_ids = [item[0] for item in
                            sorted(self.fields.items(),
                                   key=lambda x: x[1]['column_number'])
                            if objective_field_present or
                            item[1]['column_number'] != self.objective_field]
            self.headers = self.row_ids
        else:
            # The row is supposed to contain the fields as sorted in headers
            self.row_ids = map(self.field_id, headers)
            self.headers = headers
        # Mapping each included field to its correspondent index in the row.
        # The result is stored in filtered_indexes.
        self.filtered_indexes = []
        for field in self.filtered_fields:
            try:
                index = self.row_ids.index(field)
                self.filtered_indexes.append(index)
            except ValueError:
                continue

    def field_id(self, key):
        """Returns a field id.

        """

        if isinstance(key, basestring):
            try:
                id = self.fields_by_name[key]
            except KeyError:
                sys.exit("Error: field name '%s' does not exist" % key)
            return id
        elif isinstance(key, int):
            try:
                id = self.fields_by_column_number[key]
            except KeyError:
                sys.exit("Error: field column number '%s' does not exist" %
                         key)
            return id

    def field_name(self, key):
        """Returns a field name.

        """
        if isinstance(key, basestring):
            try:
                name = self.fields[key]['name']
            except KeyError:
                sys.exit("Error: field id '%s' does not exist" % key)
            return name
        elif isinstance(key, int):
            try:
                name = self.fields[self.fields_by_column_number[key]]['name']
            except KeyError:
                sys.exit("Error: field column number '%s' does not exist" %
                         key)
            return name

    def field_column_number(self, key):
        """Returns a field column number.

        """
        try:
            return self.fields[key]['column_number']
        except KeyError:
            return self.fields[self.fields_by_name[key]]['column_number']

    def len(self):
        """Returns the number of fields.

        """
        return len(self.fields)

    def pair(self, row, headers=None,
             objective_field=None, objective_field_present=None):
        """Pairs a list of values with their respective field ids.

            objective_field is the column_number of the objective field.

           `objective_field_present` must be True is the objective_field column
           is present in the row.

        """
        # Try to get objective field form Fields or use the last column
        if objective_field is None:
            if self.objective_field is None:
                objective_field = self.fields_columns[-1]
            else:
                objective_field = self.objective_field
        # If objective fields is a name or an id, retrive column number
        if isinstance(objective_field, basestring):
            objective_field = self.field_column_number(objective_field)

        # Try to guess if objective field is in the data by using headers or
        # comparing the row length to the number of fields
        if objective_field_present is None:
            if headers:
                objective_field_present = (self.field_name(objective_field) in
                                           headers)
            else:
                objective_field_present = len(row) == self.len()

        # If objective field, its presence or headers have changed, update
        if (objective_field != self.objective_field or
                objective_field_present != self.objective_field_present or
                (headers is not None and headers != self.headers)):
            self.update_objective_field(objective_field,
                                        objective_field_present, headers)

        row = map(self.normalize, row)
        return self.to_input_data(row)

    def list_fields(self, out=sys.stdout):
        """Lists a description of the fields.

        """
        for field in [(val['name'], val['optype'], val['column_number'])
                      for _, val in sorted(self.fields.items(),
                                           key=lambda k:
                                           k[1]['column_number'])]:
            out.write('[%-32s: %-16s: %-8s]\n' % (field[0],
                                                  field[1], field[2]))
            out.flush()

    def preferred_fields(self):
        """Returns fields where attribute preferred is set to True or where
           it isn't set at all.

        """
        return {key: field for key, field in self.fields.iteritems()
                if ((not 'preferred' in field) or field['preferred'])}

    def validate_input_data(self, input_data, out=sys.stdout):
        """Validates whether types for input data match types in the
        fields definition.

        """
        if isinstance(input_data, dict):
            for name in input_data:
                if name in self.fields_by_name:
                    out.write('[%-32s: %-16s: %-16s: ' %
                              (name, type(input_data[name]),
                               self.fields[self.fields_by_name[name]]
                               ['optype']))
                    if (type(input_data[name]) in
                        python_map_type(self.fields[self.fields_by_name[name]]
                                        ['optype'])):
                        out.write('OK\n')
                    else:
                        out.write('WRONG\n')
                else:
                    out.write("Field '%s' does not exist\n" % name)
        else:
            out.write("Input data must be a dictionary")

    def normalize(self, value):
        """Transforms to unicode and cleans missing tokens

        """
        if not isinstance(value, unicode):
            value = unicode(value, "utf-8")
        return None if value in self.missing_tokens else value

    def to_input_data(self, row):
        """Builds dict with field, value info only for the included headers

        """
        pair = []
        for index in self.filtered_indexes:
            pair.append((self.headers[index], row[index]))
        return dict(pair)

    def missing_counts(self):
        """Returns the ids for the fields that contain missing values

        """
        summaries = [(field_id, field.get('summary', {}))
                     for field_id, field in self.fields.items()]
        if len(summaries) == 0:
            raise ValueError("The structure has not enough information "
                             "to extract the fields containing missing values."
                             "Only datasets and models have such information. "
                             "You could retry the get remote call "
                             "'limit=-1' in the get remote call.")

        return dict([(field_id, summary.get('missing_count', 0))
                     for field_id, summary in summaries
                     if summary.get('missing_count', 0) > 0])

########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2013-2014 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A local Predictive Model.

This module defines a Model to make predictions locally or
embedded into your application without needing to send requests to
BigML.io.

This module cannot only save you a few credits, but also enormously
reduce the latency for each prediction and let you use your models
offline.

You can also visualize your predictive model in IF-THEN rule format
and even generate a python function that implements the model.

Example usage (assuming that you have previously set up the BIGML_USERNAME
and BIGML_API_KEY environment variables and that you own the model/id below):

from bigml.api import BigML
from bigml.model import Model

api = BigML()

model = Model(api.get_model('model/5026965515526876630001b2'))
model.predict({"petal length": 3, "petal width": 1})

You can also see model in a IF-THEN rule format with:

model.rules()

Or auto-generate a python function code for the model with:

model.python()

"""
import logging
LOGGER = logging.getLogger('BigML')

import sys
import locale

from bigml.api import FINISHED
from bigml.api import (BigML, get_model_id, get_status)
from bigml.util import (slugify, markdown_cleanup,
                        prefix_as_comment, utf8,
                        find_locale, cast)
from bigml.util import DEFAULT_LOCALE
from bigml.tree import Tree, LAST_PREDICTION, PROPORTIONAL
from bigml.predicate import Predicate
from bigml.basemodel import BaseModel, retrieve_model, print_importance
from bigml.basemodel import ONLY_MODEL


PYTHON_CONV = {
    "double": "locale.atof",
    "float": "locale.atof",
    "integer": "lambda x: int(locale.atof(x))",
    "int8": "lambda x: int(locale.atof(x))",
    "int16": "lambda x: int(locale.atof(x))",
    "int32": "lambda x: int(locale.atof(x))",
    "int64": "lambda x: long(locale.atof(x))",
    "day": "lambda x: int(locale.atof(x))",
    "month": "lambda x: int(locale.atof(x))",
    "year": "lambda x: int(locale.atof(x))",
    "hour": "lambda x: int(locale.atof(x))",
    "minute": "lambda x: int(locale.atof(x))",
    "second": "lambda x: int(locale.atof(x))",
    "millisecond": "lambda x: int(locale.atof(x))",
    "day-of-week": "lambda x: int(locale.atof(x))",
    "day-of-month": "lambda x: int(locale.atof(x))"
}

PYTHON_FUNC = dict([(numtype, eval(function))
                    for numtype, function in PYTHON_CONV.iteritems()])

INDENT = u'    '

STORAGE = './storage'


def extract_objective(objective_field):
    """Extract the objective field id from the model structure

    """
    if isinstance(objective_field, list):
        return objective_field[0]
    return objective_field


def print_distribution(distribution, out=sys.stdout):
    """Prints distribution data

    """
    total = reduce(lambda x, y: x + y,
                   [group[1] for group in distribution])
    for group in distribution:
        out.write(utf8(u"    %s: %.2f%% (%d instance%s)\n" % (group[0],
                       round(group[1] * 1.0 / total, 4) * 100,
                       group[1],
                       "" if group[1] == 1 else "s")))


class Model(BaseModel):
    """ A lightweight wrapper around a Tree model.

    Uses a BigML remote model to build a local version that can be used
    to generate predictions locally.

    """

    def __init__(self, model, api=None):

        if not (isinstance(model, dict) and 'resource' in model and
                model['resource'] is not None):
            if api is None:
                api = BigML(storage=STORAGE)
            self.resource_id = get_model_id(model)
            if self.resource_id is None:
                raise Exception(api.error_message(model,
                                                  resource_type='model',
                                                  method='get'))
            query_string = ONLY_MODEL
            model = retrieve_model(api, self.resource_id,
                                   query_string=query_string)
        BaseModel.__init__(self, model, api=api)
        if ('object' in model and isinstance(model['object'], dict)):
            model = model['object']

        if ('model' in model and isinstance(model['model'], dict)):
            status = get_status(model)
            if ('code' in status and status['code'] == FINISHED):
                distribution = model['model']['distribution']['training']
                self.ids_map = {}
                self.tree = Tree(
                    model['model']['root'],
                    self.fields,
                    objective_field=self.objective_field,
                    root_distribution=distribution,
                    parent_id=None,
                    ids_map=self.ids_map)
                self.terms = {}
            else:
                raise Exception("The model isn't finished yet")
        else:
            raise Exception("Cannot create the Model instance. Could not"
                            " find the 'model' key in the resource:\n\n%s" %
                            model)
        if self.tree.regression:
            try:
                import numpy
                import scipy
                self.regression_ready = True
            except ImportError:
                self.regression_ready = False

    def list_fields(self, out=sys.stdout):
        """Prints descriptions of the fields for this model.

        """
        self.tree.list_fields(out)

    def get_leaves(self):
        """Returns a list that includes all the leaves of the model.

        """
        return self.tree.get_leaves()

    def filter_input_data(self, input_data, by_name=True):
        """Filters the keys given in input_data checking against model fields

        """

        if isinstance(input_data, dict):
            empty_fields = [(key, value) for (key, value) in input_data.items()
                            if value is None]
            for (key, value) in empty_fields:
                del input_data[key]

            if by_name:
                # We no longer check that the input data keys match some of
                # the dataset fields. We only remove the keys that are not
                # used as predictors in the model
                input_data = dict(
                    [[self.inverted_fields[key], value]
                        for key, value in input_data.items()
                        if key in self.inverted_fields])
            else:
                input_data = dict(
                    [[key, value]
                        for key, value in input_data.items()
                        if key in self.fields])
            return input_data
        else:
            LOGGER.error("Failed to read input data in the expected"
                         " {field:value} format.")
            return {}

    def predict(self, input_data, by_name=True,
                print_path=False, out=sys.stdout, with_confidence=False,
                missing_strategy=LAST_PREDICTION):
        """Makes a prediction based on a number of field values.

        By default the input fields must be keyed by field name but you can use
        `by_name` to input them directly keyed by id.

        """
        # Checks if this is a regression model, using PROPORTIONAL
        # missing_strategy
        if (self.tree.regression and missing_strategy == PROPORTIONAL and
                not self.regression_ready):
            raise ImportError("Failed to find the numpy and scipy libraries,"
                              " needed to use proportional missing strategy"
                              " for regressions. Please install them before"
                              " using local predictions for the model.")
        # Checks and cleans input_data leaving the fields used in the model
        input_data = self.filter_input_data(input_data, by_name=by_name)

        # Strips affixes for numeric values and casts to the final field type
        cast(input_data, self.fields)

        prediction_info = self.tree.predict(input_data,
                                            missing_strategy=missing_strategy)
        prediction, path, confidence, distribution, instances = prediction_info

        # Prediction path
        if print_path:
            out.write(utf8(u' AND '.join(path) + u' => %s \n' % prediction))
            out.flush()
        if with_confidence:
            return [prediction, confidence, distribution, instances]
        return prediction

    def docstring(self):
        """Returns the docstring describing the model.

        """
        docstring = (u"Predictor for %s from %s\n" % (
            self.fields[self.tree.objective_field]['name'],
            self.resource_id))
        self.description = (unicode(markdown_cleanup(
            self.description).strip())
            or u'Predictive model by BigML - Machine Learning Made Easy')
        docstring += u"\n" + INDENT * 2 + (u"%s" %
                     prefix_as_comment(INDENT * 2, self.description))
        return docstring

    def get_ids_path(self, filter_id):
        """Builds the list of ids that go from a given id to the tree root

        """
        ids_path = None
        if filter_id is not None and self.tree.id is not None:
            if not filter_id in self.ids_map:
                raise ValueError("The given id does not exist.")
            else:
                ids_path = [filter_id]
                last_id = filter_id
                while self.ids_map[last_id].parent_id is not None:
                    ids_path.append(self.ids_map[last_id].parent_id)
                    last_id = self.ids_map[last_id].parent_id
        return ids_path

    def rules(self, out=sys.stdout, filter_id=None, subtree=True):
        """Returns a IF-THEN rule set that implements the model.

        `out` is file descriptor to write the rules.

        """
        ids_path = self.get_ids_path(filter_id)
        return self.tree.rules(out, ids_path=ids_path, subtree=subtree)

    def python(self, out=sys.stdout, hadoop=False,
               filter_id=None, subtree=True):
        """Returns a basic python function that implements the model.

        `out` is file descriptor to write the python code.

        """
        ids_path = self.get_ids_path(filter_id)
        if hadoop:
            return (self.hadoop_python_mapper(out=out,
                                              ids_path=ids_path,
                                              subtree=subtree) or
                    self.hadoop_python_reducer(out=out))
        else:
            return self.tree.python(out, self.docstring(), ids_path=ids_path,
                                    subtree=subtree)

    def tableau(self, out=sys.stdout, hadoop=False,
                filter_id=None, subtree=True):
        """Returns a basic tableau function that implements the model.

        `out` is file descriptor to write the tableau code.

        """
        ids_path = self.get_ids_path(filter_id)
        if hadoop:
            return "Hadoop output not available."
        else:
            response = self.tree.tableau(out, ids_path=ids_path,
                                         subtree=subtree)
            if response:
                out.write(u"END\n")
            else:
                out.write(u"\nThis function cannot be represented "
                          u"in Tableau syntax.\n")
            out.flush()
            return None

    def group_prediction(self):
        """Groups in categories or bins the predicted data

        dict - contains a dict grouping counts in 'total' and 'details' lists.
                'total' key contains a 3-element list.
                       - common segment of the tree for all instances
                       - data count
                       - predictions count
                'details' key contains a list of elements. Each element is a
                          3-element list:
                       - complete path of the tree from the root to the leaf
                       - leaf predictions count
                       - confidence
        """
        groups = {}
        tree = self.tree
        distribution = tree.distribution

        for group in distribution:
            groups[group[0]] = {'total': [[], group[1], 0],
                                'details': []}
        path = []

        def add_to_groups(groups, output, path, count, confidence):
            """Adds instances to groups array

            """
            group = output
            if not output in groups:
                groups[group] = {'total': [[], 0, 0],
                                 'details': []}
            groups[group]['details'].append([path, count, confidence])
            groups[group]['total'][2] += count

        def depth_first_search(tree, path):
            """Search for leafs' values and instances

            """
            if isinstance(tree.predicate, Predicate):
                path.append(tree.predicate)
                if tree.predicate.term:
                    term = tree.predicate.term
                    if not tree.predicate.field in self.terms:
                        self.terms[tree.predicate.field] = []
                    if not term in self.terms[tree.predicate.field]:
                        self.terms[tree.predicate.field].append(term)

            if len(tree.children) == 0:
                add_to_groups(groups, tree.output,
                              path, tree.count, tree.confidence)
                return tree.count
            else:
                children = tree.children[:]
                children.reverse()

                children_sum = 0
                for child in children:
                    children_sum += depth_first_search(child, path[:])
                if children_sum < tree.count:
                    add_to_groups(groups, tree.output, path,
                                  tree.count - children_sum, tree.confidence)
                return tree.count

        depth_first_search(tree, path)

        return groups

    def get_data_distribution(self):
        """Returns training data distribution

        """
        tree = self.tree
        distribution = tree.distribution

        return sorted(distribution,  key=lambda x: x[0])

    def get_prediction_distribution(self, groups=None):
        """Returns model predicted distribution

        """
        if groups is None:
            groups = self.group_prediction()

        predictions = [[group, groups[group]['total'][2]] for group in groups]
        # remove groups that are not predicted
        predictions = filter(lambda x: x[1] > 0, predictions)

        return sorted(predictions,  key=lambda x: x[0])

    def summarize(self, out=sys.stdout):
        """Prints summary grouping distribution as class header and details

        """
        tree = self.tree

        def extract_common_path(groups):
            """Extracts the common segment of the prediction path for a group

            """
            for group in groups:
                details = groups[group]['details']
                common_path = []
                if len(details) > 0:
                    mcd_len = min([len(x[0]) for x in details])
                    for i in range(0, mcd_len):
                        test_common_path = details[0][0][i]
                        for subgroup in details:
                            if subgroup[0][i] != test_common_path:
                                i = mcd_len
                                break
                        if i < mcd_len:
                            common_path.append(test_common_path)
                groups[group]['total'][0] = common_path
                if len(details) > 0:
                    groups[group]['details'] = sorted(details,
                                                      key=lambda x: x[1],
                                                      reverse=True)

        def confidence_error(value):
            """Returns confidence for categoric objective fields
               and error for numeric objective fields
            """
            if value is None:
                return ""
            objective_type = self.fields[tree.objective_field]['optype']
            if objective_type == 'numeric':
                return u" [Error: %s]" % value
            else:
                return u" [Confidence: %.2f%%]" % (round(value, 4) * 100)

        distribution = self.get_data_distribution()

        out.write(u"Data distribution:\n")
        print_distribution(distribution, out=out)
        out.write(u"\n\n")

        groups = self.group_prediction()
        predictions = self.get_prediction_distribution(groups)

        out.write(u"Predicted distribution:\n")
        print_distribution(predictions, out=out)
        out.write(u"\n\n")

        if self.field_importance:
            out.write(u"Field importance:\n")
            print_importance(self, out=out)

        extract_common_path(groups)

        for group in [x[0] for x in predictions]:
            details = groups[group]['details']
            path = [prediction.to_rule(self.fields) for
                    prediction in groups[group]['total'][0]]
            data_per_group = groups[group]['total'][1] * 1.0 / tree.count
            pred_per_group = groups[group]['total'][2] * 1.0 / tree.count
            out.write(utf8(u"\n\n%s : (data %.2f%% / prediction %.2f%%) %s\n" %
                           (group,
                            round(data_per_group, 4) * 100,
                            round(pred_per_group, 4) * 100,
                            " and ".join(path))))

            if len(details) == 0:
                out.write(u"    The model will never predict this class\n")
            for j in range(0, len(details)):
                subgroup = details[j]
                pred_per_sgroup = subgroup[1] * 1.0 / groups[group]['total'][2]
                path = [prediction.to_rule(self.fields) for
                        prediction in subgroup[0]]
                path_chain = " and ".join(path) if len(path) else "(root node)"
                out.write(utf8(u"    · %.2f%%: %s%s\n" %
                               (round(pred_per_sgroup, 4) * 100,
                                path_chain,
                                confidence_error(subgroup[2]))))
        out.flush()

    def hadoop_python_mapper(self, out=sys.stdout, ids_path=None,
                             subtree=True):
        """Returns a hadoop mapper header to make predictions in python

        """
        input_fields = [(value, key) for (key, value) in
                        sorted(self.inverted_fields.items(),
                               key=lambda x: x[1])]
        parameters = [value for (key, value) in
                      input_fields if key != self.tree.objective_field]
        args = []
        for field in input_fields:
            slug = slugify(self.fields[field[0]]['name'])
            self.fields[field[0]].update(slug=slug)
            if field[0] != self.tree.objective_field:
                args.append("\"" + self.fields[field[0]]['slug'] + "\"")
        output = \
u"""#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import csv
import locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')


class CSVInput(object):
    \"\"\"Reads and parses csv input from stdin

       Expects a data section (without headers) with the following fields:
       %s

       Data is processed to fall into the corresponding input type by applying
       INPUT_TYPES, and per field PREFIXES and SUFFIXES are removed. You can
       also provide strings to be considered as no content markers in
       MISSING_TOKENS.
    \"\"\"
    def __init__(self, input=sys.stdin):
        \"\"\" Opens stdin and defines parsing constants

        \"\"\"
        try:
            self.reader = csv.reader(input, delimiter=',', quotechar='\"')
""" % ",".join(parameters)

        output += (u"\n%sself.INPUT_FIELDS = [%s]\n" %
                  ((INDENT * 3), (",\n " + INDENT * 8).join(args)))

        input_types = []
        prefixes = []
        suffixes = []
        count = 0
        fields = self.fields
        for key in [key[0] for key in input_fields
                    if key != self.tree.objective_field]:
            input_type = ('None' if not fields[key]['datatype'] in
                          PYTHON_CONV
                          else PYTHON_CONV[fields[key]['datatype']])
            input_types.append(input_type)
            if 'prefix' in fields[key]:
                prefixes.append("%s: %s" % (count,
                                            repr(fields[key]['prefix'])))
            if 'suffix' in fields[key]:
                suffixes.append("%s: %s" % (count,
                                            repr(fields[key]['suffix'])))
            count += 1
        static_content = "%sself.INPUT_TYPES = [" % (INDENT * 3)
        formatter = ",\n%s" % (" " * len(static_content))
        output += u"\n%s%s%s" % (static_content,
                                 formatter.join(input_types),
                                 "]\n")
        static_content = "%sself.PREFIXES = {" % (INDENT * 3)
        formatter = ",\n%s" % (" " * len(static_content))
        output += u"\n%s%s%s" % (static_content,
                                 formatter.join(prefixes),
                                 "}\n")
        static_content = "%sself.SUFFIXES = {" % (INDENT * 3)
        formatter = ",\n%s" % (" " * len(static_content))
        output += u"\n%s%s%s" % (static_content,
                                 formatter.join(suffixes),
                                 "}\n")
        output += \
u"""            self.MISSING_TOKENS = ['?']
        except Exception, exc:
            sys.stderr.write(\"Cannot read csv\"
                             \" input. %s\\n\" % str(exc))

    def __iter__(self):
        \"\"\" Iterator method

        \"\"\"
        return self

    def next(self):
        \"\"\" Returns processed data in a list structure

        \"\"\"
        def normalize(value):
            \"\"\"Transforms to unicode and cleans missing tokens
            \"\"\"
            value = unicode(value.decode('utf-8'))
            return \"\" if value in self.MISSING_TOKENS else value

        def cast(function_value):
            \"\"\"Type related transformations
            \"\"\"
            function, value = function_value
            if not len(value):
                return None
            if function is None:
                return value
            else:
                return function(value)

        try:
            values = self.reader.next()
        except StopIteration:
            raise StopIteration()
        if len(values) < len(self.INPUT_FIELDS):
            sys.stderr.write(\"Found %s fields when %s were expected.\\n\" %
                             (len(values), len(self.INPUT_FIELDS)))
            raise StopIteration()
        else:
            values = values[0:len(self.INPUT_FIELDS)]
        try:
            values = map(normalize, values)
            for key in self.PREFIXES:
                prefix_len = len(self.PREFIXES[key])
                if values[key][0:prefix_len] == self.PREFIXES[key]:
                    values[key] = values[key][prefix_len:]
            for key in self.SUFFIXES:
                suffix_len = len(self.SUFFIXES[key])
                if values[key][-suffix_len:] == self.SUFFIXES[key]:
                    values[key] = values[key][0:-suffix_len]
            function_tuples = zip(self.INPUT_TYPES, values)
            values = map(cast, function_tuples)
            data = {}
            for i in range(len(values)):
                data.update({self.INPUT_FIELDS[i]: values[i]})
            return data
        except Exception, exc:
            sys.stderr.write(\"Error in data transformations. %s\\n\" %
                             str(exc))
            return False
\n\n
"""
        out.write(utf8(output))
        out.flush()

        self.tree.python(out, self.docstring(),
                         input_map=True,
                         ids_path=ids_path,
                         subtree=subtree)
        output = \
u"""
csv = CSVInput()
for values in csv:
    if not isinstance(values, bool):
        print u'%%s\\t%%s' %% (repr(values), repr(predict_%s(values)))
\n\n
""" % fields[self.tree.objective_field]['slug']
        out.write(utf8(output))
        out.flush()

    def hadoop_python_reducer(self, out=sys.stdout):
        """Returns a hadoop reducer to make predictions in python

        """

        output = \
u"""#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

count = 0
previous = None

def print_result(values, prediction, count):
    \"\"\"Prints input data and predicted value as an ordered list.

    \"\"\"
    result = \"[%s, %s]\" % (values, prediction)
    print u\"%s\\t%s\" % (result, count)

for line in sys.stdin:
    values, prediction = line.strip().split('\\t')
    if previous is None:
        previous = (values, prediction)
    if values != previous[0]:
        print_result(previous[0], previous[1], count)
        previous = (values, prediction)
        count = 0
    count += 1
if count > 0:
    print_result(previous[0], previous[1], count)
"""
        out.write(utf8(output))
        out.flush()

    def to_prediction(self, value_as_string, data_locale=DEFAULT_LOCALE):
        """Given a prediction string, returns its value in the required type

        """
        if not isinstance(value_as_string, unicode):
            value_as_string = unicode(value_as_string, "utf-8")

        objective_field = self.tree.objective_field
        if self.fields[objective_field]['optype'] == 'numeric':
            if data_locale is None:
                data_locale = self.locale
            find_locale(data_locale)
            datatype = self.fields[objective_field]['datatype']
            cast_function = PYTHON_FUNC.get(datatype, None)
            if cast_function is not None:
                return cast_function(value_as_string)
        return value_as_string

    def average_confidence(self):
        """Average for the confidence of the predictions resulting from
           running the training data through the model

        """
        total = 0.0
        cumulative_confidence = 0
        groups = self.group_prediction()
        for _, predictions in groups.items():
            for _, count, confidence in predictions['details']:
                cumulative_confidence += count * confidence
                total += count
        return float('nan') if total == 0.0 else cumulative_confidence

########NEW FILE########
__FILENAME__ = multimodel
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2012-2014 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A Multiple Local Predictive Model.

This module defines a Multiple Model to make predictions locally using multiple
local models.

This module cannot only save you a few credits, but also enormously
reduce the latency for each prediction and let you use your models
offline.

from bigml.api import BigML
from bigml.multimodel import MultiModel

api = BigML()

model = MultiModel([api.get_model(model['resource']) for model in
                    api.list_models(query_string="tags__in=my_tag")
                    ['objects']])

model.predict({"petal length": 3, "petal width": 1})

"""
import logging
LOGGER = logging.getLogger('BigML')


import csv
import ast
from bigml.model import Model
from bigml.model import LAST_PREDICTION
from bigml.util import get_predictions_file_name
from bigml.multivote import MultiVote
from bigml.multivote import PLURALITY_CODE


def read_votes(votes_files, to_prediction, data_locale=None):
    """Reads the votes found in the votes' files.

       Returns a list of MultiVote objects containing the list of predictions.
       votes_files parameter should contain the path to the files where votes
       are stored
       In to_prediction parameter we expect the method of a local model object
       that casts the string prediction values read from the file to their
       real type. For instance
           >>> local_model = Model(model)
           >>> prediction = local_model.to_prediction("1")
           >>> isinstance(prediction, int)
           True
           >>> read_votes(["my_predictions_file"], local_model.to_prediction)
       data_locale should contain the string identification for the locale
       used in numeric formatting.
    """
    votes = []
    for order in range(0, len(votes_files)):
        votes_file = votes_files[order]
        index = 0
        for row in csv.reader(open(votes_file, "U"), lineterminator="\n"):
            prediction = to_prediction(row[0], data_locale=data_locale)
            if index > (len(votes) - 1):
                votes.append(MultiVote([]))
            distribution = None
            instances = None
            if len(row) > 2:
                distribution = ast.literal_eval(row[2])
                instances = int(row[3])
                try:
                    confidence = float(row[1])
                except ValueError:
                    confidence = 0
            prediction_row = [prediction, confidence, order,
                              distribution, instances]
            votes[index].append_row(prediction_row)
            index += 1
    return votes


class MultiModel(object):
    """A multiple local model.

    Uses a number of BigML remote models to build a local version that can be
    used to generate predictions locally.

    """

    def __init__(self, models, api=None):
        self.models = []
        if isinstance(models, list):
            for model in models:
                self.models.append(Model(model, api=api))
        else:
            self.models.append(Model(models, api=api))

    def list_models(self):
        """Lists all the model/ids that compound the multi model.

        """
        return [model.resource() for model in self.models]

    def predict(self, input_data, by_name=True, method=PLURALITY_CODE,
                with_confidence=False, options=None,
                missing_strategy=LAST_PREDICTION):
        """Makes a prediction based on the prediction made by every model.

           The method parameter is a numeric key to the following combination
           methods in classifications/regressions:
              0 - majority vote (plurality)/ average: PLURALITY_CODE
              1 - confidence weighted majority vote / error weighted:
                  CONFIDENCE_CODE
              2 - probability weighted majority vote / average:
                  PROBABILITY_CODE
              3 - threshold filtered vote / doesn't apply:
                  THRESHOLD_COD
        """

        votes = self.generate_votes(input_data, by_name=by_name,
                                    missing_strategy=missing_strategy)
        return votes.combine(method=method, with_confidence=with_confidence,
                             options=options)

    def generate_votes(self, input_data, by_name=True,
                       missing_strategy=LAST_PREDICTION):
        """ Generates a MultiVote object that contains the predictions
            made by each of the models.
        """
        votes = MultiVote([])
        for order in range(0, len(self.models)):
            model = self.models[order]
            prediction_info = model.predict(input_data, by_name=by_name,
                                            with_confidence=True,
                                            missing_strategy=missing_strategy)
            prediction, confidence, distribution, instances = prediction_info
            prediction_row = [prediction, confidence, order,
                              distribution, instances]
            votes.append_row(prediction_row)
        return votes

    def batch_predict(self, input_data_list, output_file_path,
                      by_name=True, reuse=False,
                      missing_strategy=LAST_PREDICTION):
        """Makes predictions for a list of input data.

           The predictions generated for each model are stored in an output
           file. The name of the file will use the following syntax:
                model_[id of the model]__predictions.csv
           For instance, when using model/50c0de043b563519830001c2 to predict,
           the output file name will be
                model_50c0de043b563519830001c2__predictions.csv
        """
        for model in self.models:
            output_file = get_predictions_file_name(model.resource_id,
                                                    output_file_path)
            if reuse:
                try:
                    predictions_file = open(output_file)
                    predictions_file.close()
                    continue
                except IOError:
                    pass
            try:
                predictions_file = csv.writer(open(output_file, 'w', 0),
                                              lineterminator="\n")
            except IOError:
                raise Exception("Cannot find %s directory." % output_file_path)
            for input_data in input_data_list:
                prediction = model.predict(input_data,
                                           by_name=by_name,
                                           with_confidence=True,
                                           missing_strategy=missing_strategy)
                if isinstance(prediction[0], basestring):
                    prediction[0] = prediction[0].encode("utf-8")
                predictions_file.writerow(prediction)

    def batch_votes(self, predictions_file_path, data_locale=None):
        """Adds the votes for predictions generated by the models.

           Returns a list of MultiVote objects each of which contains a list
           of predictions.
        """

        votes_files = []
        for model in self.models:
            votes_files.append(get_predictions_file_name(model.resource_id,
                               predictions_file_path))
        return read_votes(votes_files, self.models[0].to_prediction,
                          data_locale=data_locale)

########NEW FILE########
__FILENAME__ = multivote
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2012-2014 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Auxiliar class for predictions combination.

"""
import logging
LOGGER = logging.getLogger('BigML')

import numbers
import math

PLURALITY = 'plurality'
CONFIDENCE = 'confidence weighted'
PROBABILITY = 'probability weighted'
THRESHOLD = 'threshold'
PLURALITY_CODE = 0
CONFIDENCE_CODE = 1
PROBABILITY_CODE = 2
THRESHOLD_CODE = 3

PREDICTION_HEADERS = ['prediction', 'confidence', 'order', 'distribution',
                      'count']
COMBINATION_WEIGHTS = {
    PLURALITY: None,
    CONFIDENCE: 'confidence',
    PROBABILITY: 'probability',
    THRESHOLD: None}
COMBINER_MAP = {
    PLURALITY_CODE: PLURALITY,
    CONFIDENCE_CODE: CONFIDENCE,
    PROBABILITY_CODE: PROBABILITY,
    THRESHOLD_CODE: THRESHOLD}
WEIGHT_KEYS = {
    PLURALITY: None,
    CONFIDENCE: ['confidence'],
    PROBABILITY: ['distribution', 'count'],
    THRESHOLD: None}

DEFAULT_METHOD = 0


def ws_confidence(prediction, distribution, ws_z=1.96, ws_n=None):
    """Wilson score interval computation of the distribution for the prediction

       expected arguments:
            prediction: the value of the prediction for which confidence is
                        computed
            distribution: a distribution-like structure of predictions and
                          the associated weights. (e.g.
                          [['Iris-setosa', 10], ['Iris-versicolor', 5]])
            ws_z: percentile of the standard normal distribution
            ws_n: total number of instances in the distribution. If absent,
                  the number is computed as the sum of weights in the
                  provided distribution

    """
    if isinstance(distribution, list):
        distribution = dict(distribution)
    ws_p = distribution[prediction]
    if ws_p < 0:
        raise ValueError("The distribution weight must be a positive value")
    ws_norm = float(sum(distribution.values()))
    if not ws_norm == 1.0:
        ws_p = ws_p / ws_norm
    if ws_n is None:
        ws_n = ws_norm
    else:
        ws_n = float(ws_n)
    if ws_n < 1:
        raise ValueError("The total of instances in the distribution must be"
                         " a positive integer")
    ws_z = float(ws_z)
    ws_z2 = ws_z * ws_z
    ws_factor = ws_z2 / ws_n
    ws_sqrt = math.sqrt((ws_p * (1 - ws_p) + ws_factor / 4) / ws_n)
    return (ws_p + ws_factor / 2 - ws_z * ws_sqrt) / (1 + ws_factor)


class MultiVote(object):
    """A multiple vote prediction

    Uses a number of predictions to generate a combined prediction.

    """

    @classmethod
    def avg(cls, instance, with_confidence=False):
        """Returns the average of a list of numeric values.

           If with_confidence is True, the combined confidence (as the
           average of confidences of the multivote predictions) is also
           returned
        """
        if (instance.predictions and with_confidence and
                not all(['confidence' in prediction
                         for prediction in instance.predictions])):
            raise Exception("Not enough data to use the selected "
                            "prediction method. Try creating your"
                            " model anew.")
        total = len(instance.predictions)
        result = 0.0
        confidence = 0.0
        for prediction in instance.predictions:
            result += prediction['prediction']
            if with_confidence:
                confidence += prediction['confidence']
        if with_confidence:
            return ((result / total, confidence / total) if total > 0 else
                    (float('nan'), 0))
        return result / total if total > 0 else float('nan')

    @classmethod
    def error_weighted(cls, instance, with_confidence=False):
        """Returns the prediction combining votes using error to compute weight

           If with_confidences is true, the combined confidence (as the
           error weighted average of the confidences of the multivote
           predictions) is also returned
        """
        if (instance.predictions and with_confidence and
                not all(['confidence' in prediction
                         for prediction in instance.predictions])):
            raise Exception("Not enough data to use the selected "
                            "prediction method. Try creating your"
                            " model anew.")
        top_range = 10
        result = 0.0
        normalization_factor = cls.normalize_error(instance, top_range)
        if normalization_factor == 0:
            if with_confidence:
                return float('nan'), 0
            else:
                return float('nan')
        if with_confidence:
            combined_error = 0.0
        for prediction in instance.predictions:
            result += prediction['prediction'] * prediction['_error_weight']
            if with_confidence:
                combined_error += (prediction['confidence'] *
                                   prediction['_error_weight'])
            del prediction['_error_weight']
        if with_confidence:
            return (result / normalization_factor,
                    combined_error / normalization_factor)
        else:
            return result / normalization_factor

    @classmethod
    def normalize_error(cls, instance, top_range):
        """Normalizes error to a [0, top_range] and builds probabilities

        """
        if instance.predictions and not all(['confidence' in prediction
                                             for prediction
                                             in instance.predictions]):
            raise Exception("Not enough data to use the selected "
                            "prediction method. Try creating your"
                            " model anew.")

        error_values = [prediction['confidence']
                        for prediction in instance.predictions]
        max_error = max(error_values)
        min_error = min(error_values)
        error_range = 1.0 * (max_error - min_error)
        normalize_factor = 0
        if error_range > 0:
            # Shifts and scales predictions errors to [0, top_range].
            # Then builds e^-[scaled error] and returns the normalization
            # factor to fit them between [0, 1]
            for prediction in instance.predictions:
                delta = (min_error - prediction['confidence'])
                prediction['_error_weight'] = math.exp(delta / error_range *
                                                       top_range)
                normalize_factor += prediction['_error_weight']
        else:
            for prediction in instance.predictions:
                prediction['_error_weight'] = 1
            normalize_factor = len(instance.predictions)
        return normalize_factor

    def __init__(self, predictions):
        """Init method, builds a MultiVote with a list of predictions

           The constuctor expects a list of well formed predictions like:
                {'prediction': 'Iris-setosa', 'confidence': 0.7}
            Each prediction can also contain an 'order' key that is used
            to break even in votations. The list order is used by default.
        """
        self.predictions = []
        if isinstance(predictions, list):
            self.predictions.extend(predictions)
        else:
            self.predictions.append(predictions)
        if not all(['order' in prediction for prediction in predictions]):
            for i in range(len(self.predictions)):
                self.predictions[i]['order'] = i

    def is_regression(self):
        """Returns True if all the predictions are numbers

        """
        return all([isinstance(prediction['prediction'], numbers.Number)
                   for prediction in self.predictions])

    def next_order(self):
        """Return the next order to be assigned to a prediction

           Predictions in MultiVote are ordered in arrival sequence when
           added using the constructor or the append and extend methods.
           This order is used to break even cases in combination
           methods for classifications.
        """
        if self.predictions:
            return self.predictions[-1]['order'] + 1
        return 0

    def combine(self, method=DEFAULT_METHOD, with_confidence=False,
                options=None):
        """Reduces a number of predictions voting for classification and
           averaging predictions for regression.

           method will determine the voting method (plurality, confidence
           weighted, probability weighted or threshold).
           If with_confidence is true, the combined confidence (as a weighted
           average of the confidences of votes for the combined prediction)
           will also be given.
        """
        # there must be at least one prediction to be combined
        if not self.predictions:
            raise Exception("No predictions to be combined.")

        method = COMBINER_MAP.get(method, COMBINER_MAP[DEFAULT_METHOD])
        keys = WEIGHT_KEYS.get(method, None)
        # and all predictions should have the weight-related keys
        if not keys is None:
            for key in keys:
                if not all([key in prediction for prediction
                           in self.predictions]):
                    raise Exception("Not enough data to use the selected "
                                    "prediction method. Try creating your"
                                    " model anew.")
        if self.is_regression():
            for prediction in self.predictions:
                if prediction['confidence'] is None:
                    prediction['confidence'] = 0
            function = NUMERICAL_COMBINATION_METHODS.get(method,
                                                         self.__class__.avg)
            return function(self, with_confidence=with_confidence)
        else:
            if (method == THRESHOLD):
                if options is None:
                    options = {}
                predictions = self.single_out_category(options)
            elif method == PROBABILITY:
                predictions = MultiVote([])
                predictions.predictions = self.probability_weight()
            else:
                predictions = self
            return predictions.combine_categorical(
                COMBINATION_WEIGHTS.get(method, None),
                with_confidence=with_confidence)

    def probability_weight(self):
        """Reorganizes predictions depending on training data probability

        """
        predictions = []
        for prediction in self.predictions:
            if not 'distribution' in prediction or not 'count' in prediction:
                raise Exception("Probability weighting is not available "
                                "because distribution information is missing.")
            total = prediction['count']
            if total < 1 or not isinstance(total, int):
                raise Exception("Probability weighting is not available "
                                "because distribution seems to have %s "
                                "as number of instances in a node" % total)
            order = prediction['order']
            for prediction, instances in prediction['distribution']:
                predictions.append({'prediction': prediction,
                                    'probability': float(instances) / total,
                                    'count': instances,
                                    'order': order})
        return predictions

    def combine_distribution(self, weight_label='probability'):
        """Builds a distribution based on the predictions of the MultiVote

           Given the array of predictions, we build a set of predictions with
           them and associate the sum of weights (the weight being the
           contents of the weight_label field of each prediction)
        """
        if not all([weight_label in prediction
                    for prediction in self.predictions]):
            raise Exception("Not enough data to use the selected "
                            "prediction method. Try creating your"
                            " model anew.")
        distribution = {}
        total = 0
        for prediction in self.predictions:
            if not prediction['prediction'] in distribution:
                distribution[prediction['prediction']] = 0.0
            distribution[prediction['prediction']] += prediction[weight_label]
            total += prediction['count']
        if total > 0:
            distribution = [[key, value] for key, value in
                            distribution.items()]
        else:
            distribution = []
        return distribution, total

    def combine_categorical(self, weight_label=None, with_confidence=False):
        """Returns the prediction combining votes by using the given weight:

            weight_label can be set as:
            None:          plurality (1 vote per prediction)
            'confidence':  confidence weighted (confidence as a vote value)
            'probability': probability weighted (probability as a vote value)

            If with_confidence is true, the combined confidence (as a weighted
            average of the confidences of the votes for the combined
            prediction) will also be given.
        """
        mode = {}
        if weight_label is None:
            weight = 1
        for prediction in self.predictions:
            if not weight_label is None:
                if not weight_label in COMBINATION_WEIGHTS.values():
                    raise Exception("Wrong weight_label value.")
                if not weight_label in prediction:
                    raise Exception("Not enough data to use the selected "
                                    "prediction method. Try creating your"
                                    " model anew.")
                else:
                    weight = prediction[weight_label]
            category = prediction['prediction']
            if category in mode:
                mode[category] = {"count": mode[category]["count"] +
                                  weight,
                                  "order": mode[category]["order"]}
            else:
                mode[category] = {"count": weight,
                                  "order": prediction['order']}

        prediction = sorted(mode.items(), key=lambda x: (x[1]['count'],
                                                         -x[1]['order']),
                            reverse=True)[0][0]

        if with_confidence:
            if 'confidence' in self.predictions[0]:
                return self.weighted_confidence(prediction,
                                                weight_label)
            # if prediction had no confidence, compute it from distribution
            else:
                combined_distribution = self.combine_distribution()
                distribution, count = combined_distribution
                combined_confidence = ws_confidence(prediction, distribution,
                                                    ws_n=count)
                return prediction, combined_confidence
        return prediction

    def weighted_confidence(self, combined_prediction, weight_label):
        """Compute the combined weighted confidence from a list of predictions

        """
        predictions = filter(lambda x: x['prediction'] == combined_prediction,
                             self.predictions)
        if (weight_label is not None and
                (not isinstance(weight_label, basestring) or
                 any([not 'confidence' or not weight_label in prediction
                 for prediction in predictions]))):
            raise ValueError("Not enough data to use the selected "
                             "prediction method. Lacks %s information." %
                             weight_label)
        final_confidence = 0.0
        total_weight = 0.0
        weight = 1
        for prediction in predictions:
            if weight_label is not None:
                weight = prediction[weight_label]
            final_confidence += weight * prediction['confidence']
            total_weight += weight
        final_confidence = (final_confidence / total_weight
                            if total_weight > 0 else float('nan'))
        return combined_prediction, final_confidence

    def append(self, prediction_info):
        """Adds a new prediction into a list of predictions

           prediction_info should contain at least:
           - prediction: whose value is the predicted category or value

           for instance:
               {'prediction': 'Iris-virginica'}

           it may also contain the keys:
           - confidence: whose value is the confidence/error of the prediction
           - distribution: a list of [category/value, instances] pairs
                           describing the distribution at the prediction node
           - count: the total number of instances of the training set in the
                    node
        """
        if (isinstance(prediction_info, dict) and
                'prediction' in prediction_info):
            order = self.next_order()
            prediction_info['order'] = order
            self.predictions.append(prediction_info)
        else:
            LOGGER.warning("Failed to add the prediction.\n"
                           "The minimal key for the prediction is 'prediction'"
                           ":\n{'prediction': 'Iris-virginica'")

    def single_out_category(self, options):
        """Singles out the votes for a chosen category and returns a prediction
           for this category iff the number of votes reaches at least the given
           threshold.

        """
        if options is None or any(not option in options for option in
                                  ["threshold", "category"]):
            raise Exception("No category and threshold information was"
                            " found. Add threshold and category info."
                            " E.g. {\"threshold\": 6, \"category\":"
                            " \"Iris-virginica\"}.")
        length = len(self.predictions)
        if (options["threshold"] > length):
            raise Exception("You cannot set a threshold value larger than "
                            "%s. The ensemble has not enough models to use"
                            " this threshold value." % length)
        if (options["threshold"] < 1):
            raise Exception("The threshold must be a positive value")
        category_predictions = []
        rest_of_predictions = []
        for prediction in self.predictions:
            if (prediction['prediction'] == options["category"]):
                category_predictions.append(prediction)
            else:
                rest_of_predictions.append(prediction)
        if (len(category_predictions) >= options["threshold"]):
            return MultiVote(category_predictions)
        return MultiVote(rest_of_predictions)

    def append_row(self, prediction_row,
                   prediction_headers=PREDICTION_HEADERS):
        """Adds a new prediction into a list of predictions

           prediction_headers should contain the labels for the prediction_row
           values in the same order.

           prediction_headers should contain at least the following string
           - 'prediction': whose associated value in prediction_row
                           is the predicted category or value

           for instance:
               prediction_row = ['Iris-virginica']
               prediction_headers = ['prediction']

           it may also contain the following headers and values:
           - 'confidence': whose associated value in prediction_row
                           is the confidence/error of the prediction
           - 'distribution': a list of [category/value, instances] pairs
                             describing the distribution at the prediction node
           - 'count': the total number of instances of the training set in the
                      node
        """

        if (isinstance(prediction_row, list) and
                isinstance(prediction_headers, list) and
                len(prediction_row) == len(prediction_headers) and
                'prediction' in prediction_headers):
            order = self.next_order()
            try:
                index = prediction_headers.index('order')
                prediction_row[index] = order
            except ValueError:
                prediction_headers.append('order')
                prediction_row.append(order)
            prediction_info = {}
            for i in range(0, len(prediction_row)):
                prediction_info.update({prediction_headers[i]:
                                        prediction_row[i]})
            self.predictions.append(prediction_info)
        else:
            LOGGER.error("WARNING: failed to add the prediction.\n"
                         "The row must have label 'prediction' at least.")

    def extend(self, predictions_info):
        """Given a list of predictions, extends the list with another list of
           predictions and adds the order information. For instance,
           predictions_info could be:

                [{'prediction': 'Iris-virginica', 'confidence': 0.3},
                 {'prediction': 'Iris-versicolor', 'confidence': 0.8}]
           where the expected prediction keys are: prediction (compulsory),
           confidence, distribution and count.
        """
        if isinstance(predictions_info, list):
            order = self.next_order()
            for i in range(0, len(predictions_info)):
                prediction = predictions_info[i]
                if isinstance(prediction, dict):
                    prediction['order'] = order + i
                    self.append(prediction)
                else:
                    LOGGER.error("WARNING: failed to add the prediction.\n"
                                 "Only dict like predictions are expected.")
        else:
            LOGGER.error("WARNING: failed to add the predictions.\n"
                         "Only a list of dict-like predictions are expected.")

    def extend_rows(self, predictions_rows,
                    prediction_headers=PREDICTION_HEADERS):
        """Given a list of predictions, extends the list with a list of
           predictions and adds the order information. For instance,
           predictions_info could be:

                [['Iris-virginica', 0.3],
                 ['Iris-versicolor', 0.8]]
           and their respective labels are extracted from predition_headers,
           that for this example would be:
                ['prediction', 'confidence']

           The expected prediction elements are: prediction (compulsory),
           confidence, distribution and count.
        """
        order = self.next_order()
        try:
            index = prediction_headers.index('order')
        except ValueError:
            index = len(prediction_headers)
            prediction_headers.append('order')
        if isinstance(predictions_rows, list):
            for i in range(0, len(predictions_rows)):
                prediction = predictions_rows[i]
                if isinstance(prediction, list):
                    if index == len(prediction):
                        prediction.append(order + i)
                    else:
                        prediction[index] = order + i
                    self.append_row(prediction, prediction_headers)
                else:
                    LOGGER.error("WARNING: failed to add the prediction.\n"
                                 "Only row-like predictions are expected.")
        else:
            LOGGER.error("WARNING: failed to add the predictions.\n"
                         "Only a list of row-like predictions are expected.")

NUMERICAL_COMBINATION_METHODS = {
    PLURALITY: MultiVote.avg,
    CONFIDENCE: MultiVote.error_weighted,
    PROBABILITY: MultiVote.avg}

########NEW FILE########
__FILENAME__ = predicate
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2013-2014 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Predicate structure for the BigML local Model

This module defines an auxiliary Predicate structure that is used in the Tree
to save the node's predicate info.

"""

import operator
import re

from bigml.util import plural

# Map operator str to its corresponding function
OPERATOR = {
    "<": operator.lt,
    "<=": operator.le,
    "=": operator.eq,
    "!=": operator.ne,
    "/=": operator.ne,
    ">=": operator.ge,
    ">": operator.gt
}
TM_TOKENS = 'tokens_only'
TM_FULL_TERM = 'full_terms_only'
TM_ALL = 'all'
FULL_TERM_PATTERN = re.compile(r'^.+\b.+$', re.U)
RELATIONS = {
    '<=': 'no more than %s %s',
    '>=': '%s %s at most',
    '>': 'more than %s %s',
    '<': 'less than %s %s'
}


def term_matches(text, forms_list, options):
    """ Counts the number of occurences of the words in forms_list in the text

        The terms in forms_list can either be tokens or full terms. The
        matching for tokens is contains and for full terms is equals.
    """
    token_mode = options.get('token_mode', TM_TOKENS)
    case_sensitive = options.get('case_sensitive', False)
    first_term = forms_list[0]
    if token_mode == TM_FULL_TERM:
        return full_term_match(text, first_term, case_sensitive)
    # In token_mode='all' we will match full terms using equals and
    # tokens using contains
    if token_mode == TM_ALL and len(forms_list) == 1:
        if re.match(FULL_TERM_PATTERN, first_term):
            return full_term_match(text, first_term, case_sensitive)
    return term_matches_tokens(text, forms_list, case_sensitive)


def full_term_match(text, full_term, case_sensitive):
    """Counts the match for full terms according to the case_sensitive option

    """
    if not case_sensitive:
        text = text.lower()
        full_term = full_term.lower()
    return 1 if text == full_term else 0


def get_tokens_flags(case_sensitive):
    """Returns flags for regular expression matching depending on text analysis
       options

    """
    flags = re.U
    if not case_sensitive:
        flags = (re.I | flags)
    return flags


def term_matches_tokens(text, forms_list, case_sensitive):
    """ Counts the number of occurences of the words in forms_list in the text

    """
    flags = get_tokens_flags(case_sensitive)
    expression = ur'(\b|_)%s(\b|_)' % '(\\b|_)|(\\b|_)'.join(forms_list)
    pattern = re.compile(expression, flags=flags)
    matches = re.findall(pattern, text)
    return len(matches)


class Predicate(object):
    """A predicate to be evaluated in a tree's node.

    """
    def __init__(self, operation, field, value, term=None):
        self.operator = operation
        self.field = field
        self.value = value
        self.term = term

    def is_full_term(self, fields):
        """Returns a boolean showing if a term is considered as a full_term

        """
        if self.term is not None:
            options = fields[self.field]['term_analysis']
            token_mode = options.get('token_mode', TM_TOKENS)
            if token_mode == TM_FULL_TERM:
                return True
            if token_mode == TM_ALL:
                return re.match(FULL_TERM_PATTERN, self.term)
        return False

    def to_rule(self, fields, label='name'):
        """ Builds rule string from a predicate

        """
        name = fields[self.field][label]
        full_term = self.is_full_term(fields)
        if self.term is not None:
            relation_suffix = ''
            if ((self.operator == '<' and self.value <= 1) or
                    (self.operator == '<=' and self.value == 0)):
                relation_literal = ('is not equal to' if full_term
                                    else 'does not contain')
            else:
                relation_literal = 'is equal to' if full_term else 'contains'
                if not full_term:
                    if self.operator != '>' or self.value != 0:
                        relation_suffix = (RELATIONS[self.operator] %
                                           (self.value,
                                            plural('time', self.value)))
            return u"%s %s %s %s" % (name, relation_literal,
                                     self.term, relation_suffix)
        return u"%s %s %s" % (name,
                              self.operator,
                              self.value)

    def apply(self, input_data, fields):
        """ Applies the operators defined in the predicate as strings to
            the provided input data
        """
        if self.term is not None:
            all_forms = fields[self.field]['summary'].get('term_forms', {})
            term_forms = all_forms.get(self.term, [])
            terms = [self.term]
            terms.extend(term_forms)
            options = fields[self.field]['term_analysis']
            return apply(OPERATOR[self.operator],
                         [term_matches(input_data[self.field], terms, options),
                          self.value])
        return apply(OPERATOR[self.operator],
                     [input_data[self.field],
                      self.value])

########NEW FILE########
__FILENAME__ = tree
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2013-2014 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Tree structure for the BigML local Model

This module defines an auxiliary Tree structure that is used in the local Model
to make predictions locally or embedded into your application without needing
to send requests to BigML.io.

"""
import keyword
import numbers
import math

try:
    import numpy
    from scipy import stats
except ImportError:
    pass

from bigml.predicate import Predicate
from bigml.predicate import TM_TOKENS, TM_FULL_TERM, TM_ALL
from bigml.util import sort_fields, slugify, split, utf8
from bigml.multivote import ws_confidence


# Map operator str to its corresponding python operator
PYTHON_OPERATOR = {
    "<": "<",
    "<=": "<=",
    "=": "==",
    "!=": "!=",
    "/=": "!=",
    ">=": ">=",
    ">": ">"
}


MAX_ARGS_LENGTH = 10

INDENT = u'    '

TERM_OPTIONS = ["case_sensitive", "token_mode"]

LAST_PREDICTION = 0
PROPORTIONAL = 1
BINS_LIMIT = 32


def get_instances(distribution):
    """Returns the total number of instances in a distribution

    """
    return sum(x[1] for x in distribution) if distribution else 0


def merge_distributions(distribution, new_distribution):
    """Adds up a new distribution structure to a map formatted distribution

    """
    for value, instances in new_distribution.items():
        if not value in distribution:
            distribution[value] = 0
        distribution[value] += instances
    return distribution


def merge_bins(distribution, limit):
    """Merges the bins of a regression distribution to the given limit number

    """
    length = len(distribution)
    if limit < 1 or length <= limit or length < 2:
        return distribution
    index_to_merge = 2
    shortest = float('inf')
    for index in range(1, length):
        distance = distribution[index][0] - distribution[index - 1][0]
        if distance < shortest:
            shortest = distance
            index_to_merge = index
    new_distribution = distribution[: index_to_merge - 1]
    left = distribution[index_to_merge - 1]
    right = distribution[index_to_merge]
    new_bin = [(left[0] * left[1] + right[0] * right[1]) /
               (left[1] + right[1]), left[1] + right[1]]
    new_distribution.append(new_bin)
    if index_to_merge < (length - 1):
        new_distribution.extend(distribution[(index_to_merge + 1):])
    return merge_bins(new_distribution, limit)


def mean(distribution):
    """Computes the mean of a distribution in the [[point, instances]] syntax

    """
    addition = 0.0
    count = 0.0
    for point, instances in distribution:
        addition += point * instances
        count += instances
    if count > 0:
        return addition / count
    return float('nan')


def unbiased_sample_variance(distribution, distribution_mean=None):
    """Computes the standard deviation of a distribution in the
       [[point, instances]] syntax

    """
    addition = 0.0
    count = 0.0
    if mean is None or not isinstance(distribution_mean, numbers.Number):
        distribution_mean = mean(distribution)
    for point, instances in distribution:
        addition += ((point - distribution_mean) ** 2) * instances
        count += instances
    if count > 1:
        return addition / (count - 1)
    return float('nan')


def regression_error(distribution_variance, population, r_z=1.96):
    """Computes the variance error

    """
    if population > 0:
        chi_distribution = stats.chi2(population)
        ppf = chi_distribution.ppf(1 - math.erf(r_z / math.sqrt(2)))
        if ppf != 0:
            error = distribution_variance * (population - 1) / ppf
            error = error * ((math.sqrt(population) + r_z) ** 2)
            return math.sqrt(error / population)
    return float('nan')


def tableau_string(text):
    """Transforms to a string representation in Tableau

    """
    value = repr(text)
    if isinstance(text, unicode):
        return value[1:]
    return value


def filter_nodes(nodes_list, ids=None, subtree=True):
    """Filters the contents of a nodes_list. If any of the nodes is in the
       ids list, the rest of nodes are removed. If none is in the ids list
       we include or exclude the nodes depending on the subtree flag.

    """
    if not nodes_list:
        return None
    nodes = nodes_list[:]
    if ids is not None:
        for node in nodes:
            if node.id in ids:
                nodes = [node]
                return nodes
    if not subtree:
        nodes = []
    return nodes


class Tree(object):
    """A tree-like predictive model.

    """
    def __init__(self, tree, fields, objective_field=None,
                 root_distribution=None, parent_id=None, ids_map=None,
                 subtree=True):

        self.fields = fields
        self.objective_field = objective_field
        self.output = tree['output']

        if tree['predicate'] is True:
            self.predicate = True
        else:
            self.predicate = Predicate(
                tree['predicate']['operator'],
                tree['predicate']['field'],
                tree['predicate']['value'],
                tree['predicate'].get('term', None))
        if 'id' in tree:
            self.id = tree['id']
            self.parent_id = parent_id
            if isinstance(ids_map, dict):
                ids_map[self.id] = self
        else:
            self.id = None

        children = []
        if 'children' in tree:
            for child in tree['children']:
                children.append(Tree(child,
                                     self.fields,
                                     objective_field=objective_field,
                                     parent_id=self.id,
                                     ids_map=ids_map,
                                     subtree=subtree))

        self.children = children
        self.regression = self.is_regression()
        self.count = tree['count']
        self.confidence = tree.get('confidence', None)
        if 'distribution' in tree:
            self.distribution = tree['distribution']
        elif ('objective_summary' in tree):
            summary = tree['objective_summary']
            if 'bins' in summary:
                self.distribution = summary['bins']
            elif 'counts' in summary:
                self.distribution = summary['counts']
            elif 'categories' in summary:
                self.distribution = summary['categories']
        else:
            summary = root_distribution
            if 'bins' in summary:
                self.distribution = summary['bins']
            elif 'counts' in summary:
                self.distribution = summary['counts']
            elif 'categories' in summary:
                self.distribution = summary['categories']

    def list_fields(self, out):
        """Lists a description of the model's fields.

        """
        out.write(utf8(u'<%-32s : %s>\n' % (
            self.fields[self.objective_field]['name'],
            self.fields[self.objective_field]['optype'])))
        out.flush()

        for field in [(val['name'], val['optype']) for key, val in
                      sort_fields(self.fields)
                      if key != self.objective_field]:
            out.write(utf8(u'[%-32s : %s]\n' % (field[0], field[1])))
            out.flush()
        return self.fields

    def is_regression(self):
        """Checks if the subtree structure can be a regression

        """
        def is_classification(node):
            """Checks if the node's value is a category

            """
            return isinstance(node.output, basestring)

        classification = is_classification(self)
        if classification:
            return False
        if not self.children:
            return True
        else:
            return not any([is_classification(child)
                           for child in self.children])

    def get_leaves(self):
        """Returns a list that includes all the leaves of the tree.

        """
        leaves = []

        if self.children:
            for child in self.children:
                leaves += child.get_leaves()
        else:
            leaves += [{
                'confidence': self.confidence,
                'count': self.count,
                'distribution': self.distribution,
                'output': self.output
            }]
        return leaves

    def predict(self, input_data, path=None, missing_strategy=LAST_PREDICTION):
        """Makes a prediction based on a number of field values.

        The input fields must be keyed by Id. There are two possible
        strategies to predict when the value for the splitting field
        is missing:
            0 - LAST_PREDICTION: the last issued prediction is returned.
            1 - PROPORTIONAL: as we cannot choose between the two branches
                in the tree that stem from this split, we consider both. The
                algorithm goes on until the final leaves are reached and
                all their predictions are used to decide the final prediction.
        """

        if path is None:
            path = []
        if missing_strategy == PROPORTIONAL:
            final_distribution = self.predict_proportional(input_data,
                                                           path=path)

            if self.regression:
                # sort elements by their mean
                distribution = [list(element) for element in
                                sorted(final_distribution.items(),
                                       key=lambda x: x[0])]
                distribution = merge_bins(distribution, BINS_LIMIT)
                prediction = mean(distribution)
                total_instances = sum([instances
                                       for _, instances in distribution])
                confidence = regression_error(
                    unbiased_sample_variance(distribution, prediction),
                    total_instances)
                return (prediction, path, confidence,
                        distribution, total_instances)
            else:
                distribution = [list(element) for element in
                                sorted(final_distribution.items(),
                                       key=lambda x: (-x[1], x[0]))]
                return (distribution[0][0], path,
                        ws_confidence(distribution[0][0], final_distribution),
                        distribution, get_instances(distribution))

        else:
            if self.children and split(self.children) in input_data:
                for child in self.children:
                    if child.predicate.apply(input_data, self.fields):
                        path.append(child.predicate.to_rule(self.fields))
                        return child.predict(input_data, path)
            return (self.output, path, self.confidence,
                    self.distribution, get_instances(self.distribution))

    def predict_proportional(self, input_data, path=None):
        """Makes a prediction based on a number of field values averaging
           the predictions of the leaves that fall in a subtree.

           Each time a splitting field has no value assigned, we consider
           both branches of the split to be true, merging their
           predictions.

        """

        if path is None:
            path = []

        final_distribution = {}
        if not self.children:
            return merge_distributions({}, dict((x[0], x[1])
                                                for x in self.distribution))
        if split(self.children) in input_data:
            for child in self.children:
                if child.predicate.apply(input_data, self.fields):
                    new_rule = child.predicate.to_rule(self.fields)
                    if not new_rule in path:
                        path.append(new_rule)
                    return child.predict_proportional(input_data, path)
        else:
            for child in self.children:
                final_distribution = merge_distributions(
                    final_distribution,
                    child.predict_proportional(input_data, path))
            return final_distribution

    def generate_rules(self, depth=0, ids_path=None, subtree=True):
        """Translates a tree model into a set of IF-THEN rules.

        """
        rules = u""
        children = filter_nodes(self.children, ids=ids_path,
                                subtree=subtree)
        if children:
            for child in children:
                rules += (u"%s IF %s %s\n" %
                         (INDENT * depth,
                          child.predicate.to_rule(self.fields, 'slug'),
                          "AND" if child.children else "THEN"))
                rules += child.generate_rules(depth + 1, ids_path=ids_path,
                                              subtree=subtree)
        else:
            rules += (u"%s %s = %s\n" %
                     (INDENT * depth,
                      (self.fields[self.objective_field]['slug']
                       if self.objective_field else "Prediction"),
                      self.output))
        return rules

    def rules(self, out, ids_path=None, subtree=True):
        """Prints out an IF-THEN rule version of the tree.

        """
        for field in [(key, val) for key, val in sort_fields(self.fields)]:

            slug = slugify(self.fields[field[0]]['name'])
            self.fields[field[0]].update(slug=slug)
        out.write(utf8(self.generate_rules(ids_path=ids_path,
                                           subtree=subtree)))
        out.flush()

    def python_body(self, depth=1, cmv=None, input_map=False,
                    ids_path=None, subtree=True):
        """Translate the model into a set of "if" python statements.

        `depth` controls the size of indentation. As soon as a value is missing
        that node is returned without further evaluation.

        """

        def map_data(field, missing=False):
            """Returns the subject of the condition in map format when
               more than MAX_ARGS_LENGTH arguments are used.
            """
            if input_map:
                if missing:
                    return "not '%s' in data or data['%s']" % (field, field)
                else:
                    return "data['%s']" % field
            return field
        if cmv is None:
            cmv = []
        body = u""
        term_analysis_fields = []
        children = filter_nodes(self.children, ids=ids_path,
                                subtree=subtree)
        if children:
            field = split(children)
            if not self.fields[field]['slug'] in cmv:
                body += (u"%sif (%s is None):\n" %
                        (INDENT * depth,
                         map_data(self.fields[field]['slug'], True)))
                if self.fields[self.objective_field]['optype'] == 'numeric':
                    value = self.output
                else:
                    value = repr(self.output)
                body += (u"%sreturn %s\n" %
                        (INDENT * (depth + 1),
                         value))
                cmv.append(self.fields[field]['slug'])

            for child in children:
                optype = self.fields[child.predicate.field]['optype']
                if (optype == 'numeric' or optype == 'text'):
                    value = child.predicate.value
                else:
                    value = repr(child.predicate.value)
                if optype == 'text':
                    body += (
                        u"%sif (term_matches(%s, \"%s\", %s\"%s\") %s %s):\n" %
                        (INDENT * depth,
                         map_data(self.fields[child.predicate.field]['slug'],
                         False),
                         self.fields[child.predicate.field]['slug'],
                         ('u' if isinstance(child.predicate.term, unicode)
                          else ''),
                         child.predicate.term.replace("\"", "\\\""),
                         PYTHON_OPERATOR[child.predicate.operator],
                         value))
                    term_analysis_fields.append((child.predicate.field,
                                                 child.predicate.term))
                else:
                    body += (
                        u"%sif (%s %s %s):\n" %
                        (INDENT * depth,
                         map_data(self.fields[child.predicate.field]['slug'],
                         False),
                         PYTHON_OPERATOR[child.predicate.operator],
                         value))
                next_level = child.python_body(depth + 1, cmv=cmv[:],
                                               input_map=input_map,
                                               ids_path=ids_path,
                                               subtree=subtree)
                body += next_level[0]
                term_analysis_fields.extend(next_level[1])
        else:
            if self.fields[self.objective_field]['optype'] == 'numeric':
                value = self.output
            else:
                value = repr(self.output)
            body = u"%sreturn %s\n" % (INDENT * depth, value)

        return body, term_analysis_fields

    def python(self, out, docstring, input_map=False,
               ids_path=None, subtree=True):
        """Writes a python function that implements the model.

        """
        args = []
        parameters = sort_fields(self.fields)
        if not input_map:
            input_map = len(parameters) > MAX_ARGS_LENGTH
        reserved_keywords = keyword.kwlist if not input_map else None
        prefix = "_" if not input_map else ""
        for field in [(key, val) for key, val in parameters]:
            slug = slugify(self.fields[field[0]]['name'],
                           reserved_keywords=reserved_keywords, prefix=prefix)
            self.fields[field[0]].update(slug=slug)
            if not input_map:
                if field[0] != self.objective_field:
                    args.append("%s=None" % (slug))
        if input_map:
            args.append("data={}")
        predictor_definition = (u"def predict_%s" %
                                self.fields[self.objective_field]['slug'])
        depth = len(predictor_definition) + 1
        predictor = u"%s(%s):\n" % (predictor_definition,
                                   (",\n" + " " * depth).join(args))
        predictor_doc = (INDENT + u"\"\"\" " + docstring +
                         u"\n" + INDENT + u"\"\"\"\n")
        body, term_analysis_predicates = self.python_body(input_map=input_map,
                                                          ids_path=ids_path,
                                                          subtree=subtree)
        terms_body = ""
        if term_analysis_predicates:
            terms_body = self.term_analysis_body(term_analysis_predicates)
        predictor += predictor_doc + terms_body + body
        out.write(utf8(predictor))
        out.flush()

    def term_analysis_body(self, term_analysis_predicates):
        """ Writes auxiliary functions to handle the term analysis fields

        """
        body = u""
        # static content
        body += """
    import re

    tm_tokens = '%s'
    tm_full_term = '%s'
    tm_all = '%s'


    def term_matches(text, field_name, term):
        \"\"\" Counts the number of occurences of term and its variants in text

        \"\"\"
        forms_list = term_forms[field_name].get(term, [term])
        options = term_analysis[field_name]
        token_mode = options.get('token_mode', tm_tokens)
        case_sensitive = options.get('case_sensitive', False)
        first_term = forms_list[0]
        if token_mode == tm_full_term:
            return full_term_match(text, first_term, case_sensitive)
        else:
            # In token_mode='all' we will match full terms using equals and
            # tokens using contains
            if token_mode == tm_all and len(forms_list) == 1:
                pattern = re.compile(r'^.+\\b.+$', re.U)
                if re.match(pattern, first_term):
                    return full_term_match(text, first_term, case_sensitive)
            return term_matches_tokens(text, forms_list, case_sensitive)


    def full_term_match(text, full_term, case_sensitive):
        \"\"\"Counts the match for full terms according to the case_sensitive
              option

        \"\"\"
        if not case_sensitive:
            text = text.lower()
            full_term = full_term.lower()
        return 1 if text == full_term else 0

    def get_tokens_flags(case_sensitive):
        \"\"\"Returns flags for regular expression matching depending on text
              analysis options

        \"\"\"
        flags = re.U
        if not case_sensitive:
            flags = (re.I | flags)
        return flags


    def term_matches_tokens(text, forms_list, case_sensitive):
        \"\"\" Counts the number of occurences of the words in forms_list in
               the text

        \"\"\"
        flags = get_tokens_flags(case_sensitive)
        expression = ur'(\\b|_)%%s(\\b|_)' %% '(\\\\b|_)|(\\\\b|_)'.join(forms_list)
        pattern = re.compile(expression, flags=flags)
        matches = re.findall(pattern, text)
        return len(matches)
""" % (TM_TOKENS, TM_FULL_TERM, TM_ALL)

        term_analysis_options = set(map(lambda x: x[0],
                                        term_analysis_predicates))
        term_analysis_predicates = set(term_analysis_predicates)
        body += """
    term_analysis = {"""
        for field_id in term_analysis_options:
            field = self.fields[field_id]
            body += """
        \"%s\": {""" % field['slug']
            for option in field['term_analysis']:
                if option in TERM_OPTIONS:
                    body += """
                \"%s\": %s,""" % (option, repr(field['term_analysis'][option]))
            body += """
        },"""
        body += """
    }"""
        if term_analysis_predicates:
            term_forms = {}
            fields = self.fields
            for field_id, term in term_analysis_predicates:
                alternatives = []
                field = fields[field_id]
                if field['slug'] not in term_forms:
                    term_forms[field['slug']] = {}
                all_forms = field['summary'].get('term_forms', {})
                if all_forms:
                    alternatives = all_forms.get(term, [])
                    if alternatives:
                        terms = [term]
                        terms.extend(all_forms.get(term, []))
                        term_forms[field['slug']][term] = terms
            body += """
    term_forms = {"""
            for field in term_forms:
                body += """
        \"%s\": {""" % field
                for term in term_forms[field]:
                    body += """
            u\"%s\": %s,""" % (term, term_forms[field][term])
                body += """
        },
                """
            body += """
    }
"""

        return body

    def tableau_body(self, body=u"", conditions=None, cmv=None,
                     ids_path=None, subtree=True):
        """Translate the model into a set of "if" statements in Tableau syntax

        `depth` controls the size of indentation. As soon as a value is missing
        that node is returned without further evaluation.

        """

        if cmv is None:
            cmv = []
        if conditions is None:
            conditions = []
            alternate = u"IF"
        else:
            alternate = u"ELSEIF"

        children = filter_nodes(self.children, ids=ids_path,
                                subtree=subtree)
        if children:
            field = split(children)
            if not self.fields[field]['name'] in cmv:
                conditions.append("ISNULL([%s])" % self.fields[field]['name'])
                body += (u"%s %s THEN " %
                         (alternate, " AND ".join(conditions)))
                if self.fields[self.objective_field]['optype'] == 'numeric':
                    value = self.output
                else:
                    value = tableau_string(self.output)
                body += (u"%s\n" % value)
                cmv.append(self.fields[field]['name'])
                alternate = u"ELSEIF"
                del conditions[-1]

            for child in children:
                optype = self.fields[child.predicate.field]['optype']
                if optype == 'text':
                    return u""
                if (optype == 'numeric'):
                    value = child.predicate.value
                else:
                    value = repr(child.predicate.value)
                conditions.append("[%s]%s%s" % (
                    self.fields[child.predicate.field]['name'],
                    PYTHON_OPERATOR[child.predicate.operator],
                    value))
                body = child.tableau_body(body, conditions[:], cmv=cmv[:],
                                          ids_path=ids_path, subtree=subtree)
                del conditions[-1]
        else:
            if self.fields[self.objective_field]['optype'] == 'numeric':
                value = self.output
            else:
                value = tableau_string(self.output)
            body += (
                u"%s %s THEN" % (alternate, " AND ".join(conditions)))
            body += u" %s\n" % value

        return body

    def tableau(self, out, ids_path=None, subtree=True):
        """Writes a Tableau function that implements the model.

        """
        body = self.tableau_body(ids_path=ids_path, subtree=subtree)
        if not body:
            return False
        out.write(utf8(body))
        out.flush()
        return True

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2012-2014 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Miscellaneous utility functions.

"""
import re
import unidecode
from urlparse import urlparse
import locale
import sys
import os
import json
import math
import random


DEFAULT_LOCALE = 'en_US.UTF-8'
WINDOWS_DEFAULT_LOCALE = 'English'
LOCALE_SYNONYMS = {'en': [['en_US', 'en-US', 'en_US.UTF8', 'en_US.UTF-8',
                          'English_United States.1252', 'en-us', 'en_us',
                          'en_US.utf8'],
                          ['en_GB', 'en-GB', 'en_GB.UTF8', 'en_GB.UTF-8',
                          'English_United Kingdom.1252', 'en-gb', 'en_gb',
                          'en_GB.utf8']],
                   'es': ['es_ES', 'es-ES', 'es_ES.UTF8', 'es_ES.UTF-8',
                          'Spanish_Spain.1252', 'es-es', 'es_es',
                          'es_ES.utf8'],
                   'sp': ['es_ES', 'es-ES', 'es_ES.UTF8', 'es_ES.UTF-8',
                          'Spanish_Spain.1252', 'es-es', 'es_es',
                          'es_ES.utf8'],
                   'fr': [['fr_FR', 'fr-FR', 'fr_BE', 'fr_CH', 'fr-BE',
                           'fr-CH', 'fr_FR.UTF8', 'fr_CH.UTF8',
                           'fr_BE.UTF8', 'fr_FR.UTF-8', 'fr_CH.UTF-8',
                           'fr_BE.UTF-8', 'French_France.1252', 'fr-fr',
                           'fr_fr', 'fr-be', 'fr_be', 'fr-ch', 'fr_ch',
                           'fr_FR.utf8', 'fr_BE.utf8', 'fr_CH.utf8'],
                          ['fr_CA', 'fr-CA', 'fr_CA.UTF8', 'fr_CA.UTF-8',
                           'French_Canada.1252', 'fr-ca', 'fr_ca',
                           'fr_CA.utf8']],
                   'de': ['de_DE', 'de-DE', 'de_DE.UTF8', 'de_DE.UTF-8',
                          'German_Germany.1252', 'de-de', 'de_de',
                          'de_DE.utf8'],
                   'ge': ['de_DE', 'de-DE', 'de_DE.UTF8', 'de_DE.UTF-8',
                          'German_Germany.1252', 'de-de', 'de_de',
                          'de_DE.utf8'],
                   'it': ['it_IT', 'it-IT', 'it_IT.UTF8', 'it_IT.UTF-8',
                          'Italian_Italy.1252', 'it-it', 'it_it',
                          'it_IT.utf8'],
                   'ca': ['ca_ES', 'ca-ES', 'ca_ES.UTF8', 'ca_ES.UTF-8',
                          'Catalan_Spain.1252', 'ca-es', 'ca_es',
                          'ca_ES.utf8']}

BOLD_REGEX = re.compile(r'''(\*\*)(?=\S)([^\r]*?\S[*_]*)\1''')
ITALIC_REGEX = re.compile(r'''(_)(?=\S)([^\r]*?\S)\1''')
LINKS_REGEX = re.compile((r'''(\[((?:\[[^\]]*\]|[^\[\]])*)\]\([ \t]*()'''
                          r'''<?(.*?)>?[ \t]*((['"])(.*?)\6[ \t]*)?\))'''),
                         re.MULTILINE)
TYPE_MAP = {
    "categorical": str,
    "numeric": locale.atof,
    "text": str
}

PYTHON_TYPE_MAP = {
    "categorical": [unicode, str],
    "numeric": [int, float],
    "text": [unicode, str]
}

PREDICTIONS_FILE_SUFFIX = '_predictions.csv'

PROGRESS_BAR_WIDTH = 50


def python_map_type(value):
    """Maps a BigML type to equivalent Python types.

    """
    if value in PYTHON_TYPE_MAP:
        return PYTHON_TYPE_MAP[value]
    else:
        return [unicode, str]


def invert_dictionary(dictionary, field='name'):
    """Inverts a dictionary.

    Useful to make predictions using fields' names instead of Ids.
    It does not check whether new keys are duplicated though.

    """
    return dict([[value[field], key]
                for key, value in dictionary.items()])


def slugify(name, reserved_keywords=None, prefix=''):
    """Translates a field name into a variable name.

    """
    name = unidecode.unidecode(name).lower()
    name = re.sub(r'\W+', '_', name)
    if name[0].isdigit():
        name = "field_" + name
    if reserved_keywords:
        if name in reserved_keywords:
            name = prefix + name
    return name


def localize(number):
    """Localizes `number` to show commas appropriately.

    """
    return locale.format("%d", number, grouping=True)


def is_url(value):
    """Returns True if value is a valid URL.

    """
    url = isinstance(value, basestring) and urlparse(value)
    return url and url.scheme and url.netloc and url.path


def split(children):
    """Returns the field that is used by the node to make a decision.

    """
    field = set([child.predicate.field for child in children])

    if len(field) == 1:
        return field.pop()


def markdown_cleanup(text):
    """Returns the text without markdown codes

    """
    def cleanup_bold_and_italic(text):
        """Removes from text bold and italic markdowns

        """
        text = BOLD_REGEX.sub(r'''\2''', text)
        text = ITALIC_REGEX.sub(r'''\2''', text)
        return text

    def links_to_footer(text):
        """Removes from text links and adds them as footer

        """
        links_found = re.findall(LINKS_REGEX, text)
        text = LINKS_REGEX.sub(r'''\2[*]''', text)
        text = '%s\n%s' % (text, '\n'.join(['[*]%s: %s' % (link[1], link[3])
                           for link in links_found]))
        return text

    new_line_regex = re.compile('(\n{2,})', re.DOTALL)
    text = new_line_regex.sub('\n', text)
    text = cleanup_bold_and_italic(text)
    text = links_to_footer(text)
    return text


def prefix_as_comment(comment_prefix, text):
    """Adds comment prefixes to new lines in comments

    """
    return text.replace('\n', '\n' + comment_prefix)


def sort_fields(fields):
    """Sort fields by their column_number but put children after parents.

    """
    fathers = [(key, val) for key, val in
               sorted(fields.items(), key=lambda k:k[1]['column_number'])
               if not 'auto_generated' in val]
    children = [(key, val) for key, val in
                sorted(fields.items(), key=lambda k:k[1]['column_number'])
                if 'auto_generated' in val]
    children.reverse()
    fathers_keys = [father[0] for father in fathers]
    for child in children:
        try:
            index = fathers_keys.index(child[1]['parent_ids'][0])
        except ValueError:
            index = -1

        if index >= 0:
            fathers.insert(index + 1, child)
        else:
            fathers.append(child)
    return fathers


def utf8(text):
    """Returns text in utf-8 encoding

    """
    return text.encode("utf-8")


def map_type(value):
    """Maps a BigML type to a Python type.

    """
    if value in TYPE_MAP:
        return TYPE_MAP[value]
    else:
        return str


def locale_synonyms(main_locale, locale_alias):
    """Returns True if both strings correspond to equivalent locale conventions

    """
    language_code = main_locale[0:2]
    if not language_code in LOCALE_SYNONYMS:
        return False
    alternatives = LOCALE_SYNONYMS[language_code]
    if isinstance(alternatives[0], basestring):
        return (main_locale in alternatives and locale_alias in alternatives)
    else:
        result = False
        for subgroup in alternatives:
            if main_locale in subgroup:
                result = locale_alias in subgroup
                break
        return result


def bigml_locale(locale_alias):
    """Returns the locale used in bigml.com for the given locale_alias

       The result is the locale code used in bigml.com provided that
       the locale user code has been correctly mapped. None otherwise.
    """
    language_code = locale_alias.lower()[0:2]
    if not language_code in LOCALE_SYNONYMS:
        return None
    alternatives = LOCALE_SYNONYMS[language_code]
    if isinstance(alternatives[0], basestring):
        return (alternatives[0] if locale_alias in alternatives
                else None)
    else:
        result = None
        for subgroup in alternatives:
            if locale_alias in subgroup:
                result = subgroup[0]
                break
        return result


def find_locale(data_locale=DEFAULT_LOCALE, verbose=False):
    """Looks for the given locale or the closest alternatives

    """
    new_locale = None
    try:
        data_locale = str(data_locale)
    except UnicodeEncodeError:
        data_locale = data_locale.encode("utf8")
    try:
        new_locale = locale.setlocale(locale.LC_ALL, data_locale)
    except locale.Error:
        pass
    if new_locale is None:
        for locale_alias in LOCALE_SYNONYMS.get(data_locale[0:2], []):
            if isinstance(locale_alias, list):
                for subalias in locale_alias:
                    try:
                        new_locale = locale.setlocale(locale.LC_ALL, subalias)
                        break
                    except locale.Error:
                        pass
                if not new_locale is None:
                    break
            else:
                try:
                    new_locale = locale.setlocale(locale.LC_ALL, locale_alias)
                    break
                except locale.Error:
                    pass
    if new_locale is None:
        try:
            new_locale = locale.setlocale(locale.LC_ALL, DEFAULT_LOCALE)
        except locale.Error:
            pass
    if new_locale is None:
        try:
            new_locale = locale.setlocale(locale.LC_ALL,
                                          WINDOWS_DEFAULT_LOCALE)
        except locale.Error:
            pass
    if new_locale is None:
        new_locale = locale.setlocale(locale.LC_ALL, '')

    if verbose and not locale_synonyms(data_locale, new_locale):
        print ("WARNING: Unable to find %s locale, using %s instead. This "
               "might alter numeric fields values.\n") % (data_locale,
                                                          new_locale)


def get_predictions_file_name(model, path):
    """Returns the file name for a multimodel predictions file

    """
    if isinstance(model, dict) and 'resource' in model:
        model = model['resource']
    return "%s%s%s_%s" % (path,
                          os.sep,
                          model.replace("/", "_"),
                          PREDICTIONS_FILE_SUFFIX)


def clear_console_line(out=sys.stdout, length=PROGRESS_BAR_WIDTH):
    """Fills console line with blanks.

    """
    out.write("%s" % (" " * length))
    out.flush()


def reset_console_line(out=sys.stdout, length=PROGRESS_BAR_WIDTH):
    """Returns cursor to first column.

    """
    out.write("\b" * (length + 1))
    out.flush()


def console_log(message, out=sys.stdout, length=PROGRESS_BAR_WIDTH):
    """Prints the message to the given output

    """
    clear_console_line(out=out, length=length)
    reset_console_line(out=out, length=length)
    out.write(message)
    reset_console_line(out=out, length=length)


def get_csv_delimiter():
    """Returns the csv delimiter character

    """
    point_char = locale.localeconv()['decimal_point']
    return ',' if point_char != ',' else ';'


def strip_affixes(value, field):
    """Strips prefixes and suffixes if present

    """
    if not isinstance(value, unicode):
        value = unicode(value, "utf-8")
    if 'prefix' in field and value.startswith(field['prefix']):
        value = value[len(field['prefix']):]
    if 'suffix' in field and value.endswith(field['suffix']):
        value = value[0:-len(field['suffix'])]
    return value


def cast(input_data, fields):
    """Checks expected type in input data values, strips affixes and casts

    """
    for (key, value) in input_data.items():
        if ((fields[key]['optype'] == 'numeric' and
             isinstance(value, basestring)) or
            (fields[key]['optype'] != 'numeric' and
             not isinstance(value, basestring))):
            try:
                if fields[key]['optype'] == 'numeric':
                    value = strip_affixes(value, fields[key])
                input_data.update({key:
                                   map_type(fields[key]
                                            ['optype'])(value)})
            except ValueError:
                raise ValueError(u"Mismatch input data type in field "
                                 u"\"%s\" for value %s." %
                                 (fields[key]['name'],
                                  value))


def check_dir(path):
    """Creates a directory if it doesn't exist

    """
    if os.path.exists(path):
        if not os.path.isdir(path):
            raise ValueError(u"The given path is not a directory")
    elif len(path) > 0:
        os.makedirs(path)
    return path


def maybe_save(resource_id, path,
               code=None, location=None,
               resource=None, error=None):
    """ Builds the resource dict response and saves it if a path is provided.

        The resource is saved in a local repo json file in the given path.

    """
    resource = {
        'code': code,
        'resource': resource_id,
        'location': location,
        'object': resource,
        'error': error}
    if path is not None and resource_id is not None:
        try:
            resource_json = json.dumps(resource)
        except ValueError:
            print("The resource has an invalid JSON format")
        try:
            resource_file_name = "%s%s%s" % (path, os.sep,
                                             resource_id.replace('/', '_'))
            with open(resource_file_name, "w", 0) as resource_file:
                resource_file.write(resource_json)
        except IOError:
            print("Failed writing resource to %s" % resource_file_name)
    return resource


def plural(text, num):
    """Pluralizer: adds "s" at the end of a string if a given number is > 1

    """
    return "%s%s" % (text, "s"[num == 1:])


def get_exponential_wait(wait_time, retry_count):
    """Computes the exponential wait time used in next request using the
       base values provided by the user:
        - wait_time: starting wait time
        - retries: total number of retries
        - retries_left: retries left

    """
    delta = (retry_count ** 2) * wait_time / 2
    exp_factor = delta if retry_count > 1 else 0
    return wait_time + math.floor(random.random() * exp_factor)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# BigML documentation build configuration file, created by
# sphinx-quickstart on Tue Jul  3 20:57:42 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import os
import re
import sys

# Path to this project
project_path = os.path.join(os.path.dirname(__file__), '..')

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, project_path)

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'BigML'
copyright = u'2011 - 2014, The BigML Team'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
# Read the version from bigml.__version__ without importing the package
# (and thus attempting to import packages it depends on that may not be
# installed yet).
init_py_path = os.path.join(project_path, 'bigml', '__init__.py')
version = re.search("__version__ = '([^']+)'",
                    open(init_py_path).read()).group(1)
# The full version, including alpha/beta/rc tags.
release = version

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

# The reST default role (used for this markup: `text`) to use for all documents.
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


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

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
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'BigMLdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'BigML.tex', u'BigML Documentation',
   u'The BigML Team', 'manual'),
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


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'bigml', u'BigML Documentation',
     [u'The BigML Team'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'BigML', u'BigML Documentation',
   u'The BigML Team', 'BigML', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = common_steps
from lettuce import *

from bigml.api import HTTP_OK
from bigml.api import HTTP_CREATED
from bigml.api import HTTP_ACCEPTED
from bigml.api import HTTP_BAD_REQUEST
from bigml.api import HTTP_UNAUTHORIZED
from bigml.api import HTTP_NOT_FOUND

@step(r'I get an OK response')
def i_get_an_OK_response(step):
    assert world.status == HTTP_OK

@step(r'I get a created response')
def i_get_a_created_response(step):
    assert world.status == HTTP_CREATED

@step(r'I get an accepted response')
def i_get_an_accepted_response(step):
    assert world.status == HTTP_ACCEPTED

@step(r'I get a bad request response')
def i_get_a_bad_request_response(step):
    assert world.status == HTTP_BAD_REQUEST

@step(r'I get a unauthorized response')
def i_get_a_unauthorized_response(step):
    assert world.status == HTTP_UNAUTHORIZED

@step(r'I get a not found response')
def i_get_a_not_found_response(step):
    assert world.status == HTTP_NOT_FOUND

@step(r'I want to use api in DEV mode')
def i_want_api_dev_mode(step):
    world.api = world.api_dev_mode
    # Update counters of resources for DEV mode
    sources = world.api.list_sources()
    assert sources['code'] == HTTP_OK
    world.init_sources_count = sources['meta']['total_count']

    datasets = world.api.list_datasets()
    assert datasets['code'] == HTTP_OK
    world.init_datasets_count = datasets['meta']['total_count']

    models = world.api.list_models()
    assert models['code'] == HTTP_OK
    world.init_models_count = models['meta']['total_count']

    predictions = world.api.list_predictions()
    assert predictions['code'] == HTTP_OK
    world.init_predictions_count = predictions['meta']['total_count']

    evaluations = world.api.list_evaluations()
    assert evaluations['code'] == HTTP_OK
    world.init_evaluations_count = evaluations['meta']['total_count']

    ensembles = world.api.list_ensembles()
    assert ensembles['code'] == HTTP_OK
    world.init_ensembles_count = ensembles['meta']['total_count']

    batch_predictions = world.api.list_batch_predictions()
    assert batch_predictions['code'] == HTTP_OK
    world.init_batch_predictions_count = batch_predictions['meta']['total_count']

    clusters = world.api.list_clusters()
    assert clusters['code'] == HTTP_OK
    world.init_clusters_count = clusters['meta']['total_count']

    centroids = world.api.list_centroids()
    assert centroids['code'] == HTTP_OK
    world.init_centroids_count = centroids['meta']['total_count']

    batch_centroids = world.api.list_batch_centroids()
    assert batch_centroids['code'] == HTTP_OK
    world.init_batch_centroids_count = batch_centroids['meta']['total_count']

########NEW FILE########
__FILENAME__ = compare_predictions-steps
import json
import os
from lettuce import step, world
from bigml.model import Model
from bigml.multimodel import MultiModel
from bigml.multivote import MultiVote

@step(r'I retrieve a list of remote models tagged with "(.*)"')
def i_retrieve_a_list_of_remote_models(step, tag):
    world.list_of_models = [world.api.get_model(model['resource']) for model in
                            world.api.list_models(query_string="tags__in=%s" % tag)['objects']]


@step(r'I create a local model')
def i_create_a_local_model(step):
    world.local_model = Model(world.model)


@step(r'I create a local prediction for "(.*)"')
def i_create_a_local_prediction(step, data=None):
    if data is None:
        data = "{}"
    data = json.loads(data)
    world.local_prediction = world.local_model.predict(data)


@step(r'I create a proportional missing strategy local prediction for "(.*)"')
def i_create_a_proportional_local_prediction(step, data=None):
    if data is None:
        data = "{}"
    data = json.loads(data)
    world.local_prediction = world.local_model.predict(
        data, with_confidence=True, missing_strategy=1)


@step(r'I create a prediction from a multi model for "(.*)"')
def i_create_a_prediction_from_a_multi_model(step, data=None):
    if data is None:
        data = "{}"
    data = json.loads(data)
    world.local_prediction = world.local_model.predict(data)


@step(r'the local prediction is "(.*)"')
def the_local_prediction_is(step, prediction):
    if isinstance(world.local_prediction, list):
        local_prediction = world.local_prediction[0]
    else:
        local_prediction = world.local_prediction
    try:
        local_model = world.local_model
        if local_model.tree.regression:
            local_prediction = round(float(local_prediction), 4)
            prediction = round(float(prediction), 4)
    except:
        local_model = world.local_ensemble.multi_model.models[0]
        if local_model.tree.regression:
            local_prediction = round(float(local_prediction), 4)
            prediction = round(float(prediction), 4)

    assert local_prediction == prediction


@step(r'the confidence for the local prediction is "(.*)"')
def the_local_prediction_confidence_is(step, confidence):
    local_confidence = world.local_prediction[1]
    local_confidence = round(float(local_confidence), 4)
    confidence = round(float(confidence), 4)
    assert local_confidence == confidence


@step(r'I create a local multi model')
def i_create_a_local_multi_model(step):
    world.local_model = MultiModel(world.list_of_models)

@step(r'I create a batch prediction for "(.*)" and save it in "(.*)"')
def i_create_a_batch_prediction(step, input_data_list, directory):
    if len(directory) > 0 and not os.path.exists(directory):
        os.makedirs(directory)
    input_data_list = eval(input_data_list)
    assert isinstance(input_data_list, list)
    world.local_model.batch_predict(input_data_list, directory)

@step(r'I combine the votes in "(.*)"')
def i_combine_the_votes(step, directory):
    world.votes = world.local_model.batch_votes(directory)

@step(r'the plurality combined predictions are "(.*)"')
def the_plurality_combined_prediction(step, predictions):
    predictions = eval(predictions)
    for i in range(len(world.votes)):
        combined_prediction = world.votes[i].combine()
        assert combined_prediction == predictions[i]

@step(r'the confidence weighted predictions are "(.*)"')
def the_confidence_weighted_prediction(step, predictions):
    predictions = eval(predictions)
    for i in range(len(world.votes)):
        combined_prediction = world.votes[i].combine(1)
        assert combined_prediction == predictions[i]

########NEW FILE########
__FILENAME__ = compute_multivote_prediction-steps
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2012 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import time
import json
import os
from datetime import datetime, timedelta
from lettuce import step, world

from bigml.api import HTTP_CREATED
from bigml.api import HTTP_ACCEPTED
from bigml.api import FINISHED
from bigml.api import FAULTY
from bigml.api import get_status
from bigml.multivote import MultiVote

@step(r'I create a MultiVote for the set of predictions in file (.*)$')
def i_create_a_multivote(step, predictions_file):
    try:
        with open(predictions_file, 'r') as predictions_file:
            world.multivote = MultiVote(json.load(predictions_file))
    except IOError:
        assert False, "Failed to read %s" % predictions_file

@step(r'I compute the prediction with confidence using method "(.*)"$')
def compute_prediction(step, method):
    try:
        world.combined_prediction, world.combined_confidence = (
            world.multivote.combine(int(method), with_confidence=True))
    except ValueError:
        assert False, "Incorrect method"

@step(r'I compute the prediction without confidence using method "(.*)"$')
def compute_prediction_no_confidence(step, method):
    try:
        world.combined_prediction_nc = world.multivote.combine(int(method))
    except ValueError:
        assert False, "Incorrect method"

@step(r'the combined prediction is "(.*)"$')
def check_combined_prediction(step, prediction):

    if world.multivote.is_regression():
        try:
            assert round(world.combined_prediction, 6) == round(float(prediction), 6)
        except ValueError, exc:
            assert False, str(exc)
    else:
        assert world.combined_prediction == prediction

@step(r'the combined prediction without confidence is "(.*)"$')
def check_combined_prediction_no_confidence(step, prediction):

    if world.multivote.is_regression():
        try:
            assert round(world.combined_prediction_nc, 6) == round(
                float(prediction), 6)
        except ValueError, exc:
            assert False, str(exc)
    else:
        assert world.combined_prediction == prediction

@step(r'the confidence for the combined prediction is (.*)$')
def check_combined_confidence(step, confidence):
    try:
        assert round(world.combined_confidence, 6) == round(float(confidence), 6)
    except ValueError, exc:
        assert False, str(exc)

########NEW FILE########
__FILENAME__ = create_batch_prediction-steps
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2012 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import time
import json
import requests
import csv
from datetime import datetime, timedelta
from lettuce import step, world

from bigml.api import HTTP_CREATED
from bigml.api import FINISHED
from bigml.api import FAULTY
from bigml.api import get_status


@step(r'I create a batch prediction for the dataset with the model$')
def i_create_a_batch_prediction(step):
    dataset = world.dataset.get('resource')
    model = world.model.get('resource')
    resource = world.api.create_batch_prediction(model, dataset)
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.batch_prediction = resource['object']
    world.batch_predictions.append(resource['resource'])


@step(r'I create a batch prediction for the dataset with the ensemble$')
def i_create_a_batch_prediction_ensemble(step):
    dataset = world.dataset.get('resource')
    ensemble = world.ensemble.get('resource')
    resource = world.api.create_batch_prediction(ensemble, dataset)
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.batch_prediction = resource['object']
    world.batch_predictions.append(resource['resource'])


@step(r'I wait until the batch prediction status code is either (\d) or (-\d) less than (\d+)')
def wait_until_batch_prediction_status_code_is(step, code1, code2, secs):
    start = datetime.utcnow()
    step.given('I get the batch prediction "{id}"'.format(id=world.batch_prediction['resource']))
    status = get_status(world.batch_prediction)
    while (status['code'] != int(code1) and
           status['code'] != int(code2)):
        time.sleep(3)
        assert datetime.utcnow() - start < timedelta(seconds=int(secs))
        step.given('I get the batch prediction "{id}"'.format(id=world.batch_prediction['resource']))
        status = get_status(world.batch_prediction)
    assert status['code'] == int(code1)


@step(r'I wait until the batch centroid status code is either (\d) or (-\d) less than (\d+)')
def wait_until_batch_centroid_status_code_is(step, code1, code2, secs):
    start = datetime.utcnow()
    step.given('I get the batch centroid "{id}"'.format(id=world.batch_centroid['resource']))
    status = get_status(world.batch_centroid)
    while (status['code'] != int(code1) and
           status['code'] != int(code2)):
        time.sleep(3)
        assert datetime.utcnow() - start < timedelta(seconds=int(secs))
        step.given('I get the batch centroid "{id}"'.format(id=world.batch_centroid['resource']))
        status = get_status(world.batch_centroid)
    assert status['code'] == int(code1)


@step(r'I wait until the batch prediction is ready less than (\d+)')
def the_batch_prediction_is_finished_in_less_than(step, secs):
    wait_until_batch_prediction_status_code_is(step, FINISHED, FAULTY, secs)

@step(r'I wait until the batch centroid is ready less than (\d+)')
def the_batch_centroid_is_finished_in_less_than(step, secs):
    wait_until_batch_centroid_status_code_is(step, FINISHED, FAULTY, secs)


@step(r'I download the created predictions file to "(.*)"')
def i_download_predictions_file(step, filename):
    file_object = world.api.download_batch_prediction(
        world.batch_prediction, filename=filename)
    assert file_object is not None
    world.output = file_object
    
@step(r'I download the created centroid file to "(.*)"')
def i_download_centroid_file(step, filename):
    file_object = world.api.download_batch_centroid(
        world.batch_centroid, filename=filename)
    assert file_object is not None
    world.output = file_object

@step(r'the batch prediction file is like "(.*)"')
def i_check_predictions(step, check_file):
    predictions_file = world.output
    try:
        predictions_file = csv.reader(open(predictions_file, "U"), lineterminator="\n")
        check_file = csv.reader(open(check_file, "U"), lineterminator="\n")
        for row in predictions_file:
            check_row = check_file.next()
            if len(check_row) != len(row):
                assert False
            for index in range(len(row)):
                dot = row[index].find(".")
                if dot > 0:
                    try:
                        decimal_places = min(len(row[index]), len(check_row[index])) - dot - 1
                        row[index] = round(float(row[index]), decimal_places)
                        check_row[index] = round(float(check_row[index]), decimal_places)    
                    except ValueError:
                        pass
                if check_row[index] != row[index]:
                    print row, check_row
                    assert False
        assert True
    except Exception, exc:
        assert False, str(exc)

@step(r'the batch centroid file is like "(.*)"')
def i_check_batch_centroid(step, check_file):
    i_check_predictions(step, check_file)


@step(r'I check the batch centroid is ok')
def i_check_batch_centroid_is_ok(step):
    assert world.api.ok(world.batch_centroid)

@step(r'I create a batch centroid for the dataset$')
def i_create_a_batch_prediction_with_cluster(step):
    dataset = world.dataset.get('resource')
    cluster = world.cluster.get('resource')
    resource = world.api.create_batch_centroid(cluster, dataset)
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.batch_centroid = resource['object']
    world.batch_centroids.append(resource['resource'])

########NEW FILE########
__FILENAME__ = create_cluster-steps
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2012 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import time
import json
import os
from datetime import datetime, timedelta
from lettuce import step, world

from bigml.api import HTTP_CREATED
from bigml.api import HTTP_ACCEPTED
from bigml.api import FINISHED
from bigml.api import FAULTY
from bigml.api import get_status

@step(r'I create a cluster$')
def i_create_a_cluster(step):
    dataset = world.dataset.get('resource')
    resource = world.api.create_cluster(dataset)
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.cluster = resource['object']
    world.clusters.append(resource['resource'])

@step(r'I create a cluster from a dataset list$')
def i_create_a_cluster_from_dataset_list(step):
    resource = world.api.create_cluster(world.dataset_ids)
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.cluster = resource['object']
    world.clusters.append(resource['resource'])

@step(r'I wait until the cluster status code is either (\d) or (-\d) less than (\d+)')
def wait_until_cluster_status_code_is(step, code1, code2, secs):
    start = datetime.utcnow()
    step.given('I get the cluster "{id}"'.format(id=world.cluster['resource']))
    status = get_status(world.cluster)
    while (status['code'] != int(code1) and
           status['code'] != int(code2)):
           time.sleep(3)
           assert datetime.utcnow() - start < timedelta(seconds=int(secs))
           step.given('I get the cluster "{id}"'.format(id=world.cluster['resource']))
           status = get_status(world.cluster)
    assert status['code'] == int(code1)

@step(r'I wait until the cluster is ready less than (\d+)')
def the_cluster_is_finished_in_less_than(step, secs):
    wait_until_cluster_status_code_is(step, FINISHED, FAULTY, secs)

@step(r'I make the cluster shared')
def make_the_cluster_shared(step):
    resource = world.api.update_cluster(world.cluster['resource'],
                                      {'shared': True})
    world.status = resource['code']
    assert world.status == HTTP_ACCEPTED
    world.location = resource['location']
    world.cluster = resource['object']

@step(r'I get the cluster sharing info')
def get_sharing_info(step):
    world.shared_hash = world.cluster['shared_hash']
    world.sharing_key = world.cluster['sharing_key']

@step(r'I check the cluster status using the model\'s shared url')
def cluster_from_shared_url(step):
    world.cluster = world.api.get_cluster("shared/cluster/%s" % world.shared_hash)
    assert get_status(world.cluster)['code'] == FINISHED

@step(r'I check the cluster status using the model\'s shared key')
def cluster_from_shared_key(step):
   
    username = os.environ.get("BIGML_USERNAME")
    world.cluster = world.api.get_cluster(world.cluster['resource'],
        shared_username=username, shared_api_key=world.sharing_key)
    assert get_status(world.cluster)['code'] == FINISHED

########NEW FILE########
__FILENAME__ = create_dataset-steps
import os
import time
import json
from datetime import datetime, timedelta
from lettuce import *
from bigml.api import HTTP_CREATED
from bigml.api import HTTP_OK
from bigml.api import HTTP_ACCEPTED
from bigml.api import FINISHED
from bigml.api import FAULTY
from bigml.api import get_status

@step(r'I create a dataset$')
def i_create_a_dataset(step):
    resource = world.api.create_dataset(world.source['resource'])
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.dataset = resource['object']
    world.datasets.append(resource['resource'])


@step(r'I create a dataset with "(.*)"')
def i_create_a_dataset_with(step, data="{}"):
    resource = world.api.create_dataset(world.source['resource'], json.loads(data))
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.dataset = resource['object']
    world.datasets.append(resource['resource'])


@step(r'I wait until the dataset status code is either (\d) or (\d) less than (\d+)')
def wait_until_dataset_status_code_is(step, code1, code2, secs):
    start = datetime.utcnow()
    step.given('I get the dataset "{id}"'.format(id=world.dataset['resource']))
    status = get_status(world.dataset)
    while (status['code'] != int(code1) and
           status['code'] != int(code2)):
        time.sleep(3)
        assert datetime.utcnow() - start < timedelta(seconds=int(secs))
        step.given('I get the dataset "{id}"'.format(id=world.dataset['resource']))
        status = get_status(world.dataset)
    assert status['code'] == int(code1)

@step(r'I wait until the dataset is ready less than (\d+)')
def the_dataset_is_finished_in_less_than(step, secs):
    wait_until_dataset_status_code_is(step, FINISHED, FAULTY, secs)

@step(r'I make the dataset public')
def make_the_dataset_public(step):
    resource = world.api.update_dataset(world.dataset['resource'],
                                        {'private': False})
    world.status = resource['code']
    assert world.status == HTTP_ACCEPTED
    world.location = resource['location']
    world.dataset = resource['object']

@step(r'I get the dataset status using the dataset\'s public url')
def build_local_dataset_from_public_url(step):
    world.dataset = world.api.get_dataset("public/%s" % world.dataset['resource'])

@step(r'the dataset\'s status is FINISHED')
def dataset_status_finished(step):
    assert get_status(world.dataset)['code'] == FINISHED

@step(r'I create a dataset extracting a (.*) sample$')
def i_create_a_split_dataset(step, rate):
    world.origin_dataset = world.dataset
    resource = world.api.create_dataset(world.dataset['resource'], {'sample_rate': float(rate)})
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.dataset = resource['object']
    world.datasets.append(resource['resource'])

@step(r'I compare the datasets\' instances$')
def i_compare_datasets_instances(step):
    world.datasets_instances = (world.dataset['rows'], world.origin_dataset['rows'])

@step(r'the proportion of instances between datasets is (.*)$')
def proportion_datasets_instances(step, rate):
    assert int(world.datasets_instances[1] * float(rate)) == world.datasets_instances[0]

@step(r'I create a dataset from the cluster and the centroid$')
def i_create_a_dataset_from_cluster_centroid(step):
    resource = world.api.create_dataset(
        world.cluster['resource'],
        args={'centroid': world.centroid['centroid_id']})
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.dataset = resource['object']
    world.datasets.append(resource['resource'])

@step(r'I check that the dataset is created for the cluster and the centroid$')
def i_check_dataset_from_cluster_centroid(step):
    cluster = world.api.get_cluster(world.cluster['resource'])
    world.status = cluster['code']
    assert world.status == HTTP_OK
    assert "dataset/%s" % (
        cluster['object']['cluster_datasets'][
            world.centroid['centroid_id']]) == world.dataset['resource']

########NEW FILE########
__FILENAME__ = create_ensemble-steps
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2012 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import time
import json
import os
from datetime import datetime, timedelta
from lettuce import step, world

from bigml.api import HTTP_CREATED
from bigml.api import HTTP_ACCEPTED
from bigml.api import FINISHED
from bigml.api import FAULTY
from bigml.api import get_status
from bigml.ensemble import Ensemble

@step(r'I create an ensemble of (\d+) models and (\d+) tlp$')
def i_create_an_ensemble(step, number_of_models, tlp):
    dataset = world.dataset.get('resource')
    try:
        number_of_models = int(number_of_models)
        tlp = int(tlp)
        args = {'number_of_models': number_of_models,
                'tlp': tlp, 'sample_rate': 0.99, 'seed': 'BigML'}
    except:
        args = {}

    resource = world.api.create_ensemble(dataset, args=args)
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.ensemble = resource['object']
    world.ensemble_id = resource['resource']
    world.ensembles.append(resource['resource'])

@step(r'I wait until the ensemble status code is either (\d) or (-\d) less than (\d+)')
def wait_until_ensemble_status_code_is(step, code1, code2, secs):
    start = datetime.utcnow()
    step.given('I get the ensemble "{id}"'.format(id=world.ensemble['resource']))
    status = get_status(world.ensemble)
    while (status['code'] != int(code1) and
           status['code'] != int(code2)):
        time.sleep(3)
        assert datetime.utcnow() - start < timedelta(seconds=int(secs))
        step.given('I get the ensemble "{id}"'.format(id=world.ensemble['resource']))
        status = get_status(world.ensemble)
    assert status['code'] == int(code1)

@step(r'I wait until the ensemble is ready less than (\d+)')
def the_ensemble_is_finished_in_less_than(step, secs):
    wait_until_ensemble_status_code_is(step, FINISHED, FAULTY, secs)


@step(r'I create a local Ensemble$')
def create_local_ensemble(step):
    world.local_ensemble = Ensemble(world.ensemble_id, world.api)

@step(r'I create a local Ensemble with the last (\d+) models$')
def create_local_ensemble_with_list(step, number_of_models):
    world.local_ensemble = Ensemble(world.models[-int(number_of_models):], world.api)

@step(r'the field importance text is (.*?)$')
def field_importance_print(step, field_importance):
    field_importance_data = world.local_ensemble.field_importance_data()[0]
    if field_importance_data == json.loads(field_importance):
        assert True
    else:
        assert False, "Found %s, expected %s" % (field_importance_data, field_importance)

########NEW FILE########
__FILENAME__ = create_evaluation-steps
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2012 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import time
import json
from datetime import datetime, timedelta
from lettuce import step, world

from bigml.api import HTTP_CREATED
from bigml.api import FINISHED
from bigml.api import FAULTY
from bigml.api import get_status

@step(r'I create an evaluation for the model with the dataset$')
def i_create_an_evaluation(step):
    dataset = world.dataset.get('resource')
    model = world.model.get('resource')
    resource = world.api.create_evaluation(model, dataset)
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.evaluation = resource['object']
    world.evaluations.append(resource['resource'])


@step(r'I create an evaluation for the ensemble with the dataset$')
def i_create_an_evaluation_ensemble(step):
    dataset = world.dataset.get('resource')
    ensemble = world.ensemble.get('resource')
    resource = world.api.create_evaluation(ensemble, dataset)
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.evaluation = resource['object']
    world.evaluations.append(resource['resource'])

@step(r'I wait until the evaluation status code is either (\d) or (-\d) less than (\d+)')
def wait_until_evaluation_status_code_is(step, code1, code2, secs):
    start = datetime.utcnow()
    step.given('I get the evaluation "{id}"'.format(id=world.evaluation['resource']))
    status = get_status(world.evaluation)
    while (status['code'] != int(code1) and
           status['code'] != int(code2)):
        time.sleep(3)
        assert datetime.utcnow() - start < timedelta(seconds=int(secs))
        step.given('I get the evaluation "{id}"'.format(id=world.evaluation['resource']))
        status = get_status(world.evaluation)
    assert status['code'] == int(code1)

@step(r'I wait until the evaluation is ready less than (\d+)')
def the_evaluation_is_finished_in_less_than(step, secs):
    wait_until_evaluation_status_code_is(step, FINISHED, FAULTY, secs)

@step(r'the measured "(.*)" is (\d+\.*\d*)')
def the_measured_measure_is_value(step, measure, value):
    assert world.evaluation['result']['model'][measure] + 0.0 == float(value)

@step(r'the measured "(.*)" is greater than (\d+\.*\d*)')
def the_measured_measure_is_greater_value(step, measure, value):
    assert world.evaluation['result']['model'][measure] + 0.0 > float(value)

########NEW FILE########
__FILENAME__ = create_model-steps
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2012 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import time
import json
import os
from datetime import datetime, timedelta
from lettuce import step, world

from bigml.api import HTTP_CREATED
from bigml.api import HTTP_ACCEPTED
from bigml.api import FINISHED
from bigml.api import FAULTY
from bigml.api import get_status

@step(r'I create a model$')
def i_create_a_model(step):
    dataset = world.dataset.get('resource')
    resource = world.api.create_model(dataset)
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.model = resource['object']
    world.models.append(resource['resource'])

@step(r'I create a model from a dataset list$')
def i_create_a_model_from_dataset_list(step):
    resource = world.api.create_model(world.dataset_ids)
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.model = resource['object']
    world.models.append(resource['resource'])

@step(r'I wait until the model status code is either (\d) or (-\d) less than (\d+)')
def wait_until_model_status_code_is(step, code1, code2, secs):
    start = datetime.utcnow()
    step.given('I get the model "{id}"'.format(id=world.model['resource']))
    status = get_status(world.model)
    while (status['code'] != int(code1) and
           status['code'] != int(code2)):
           time.sleep(3)
           assert datetime.utcnow() - start < timedelta(seconds=int(secs))
           step.given('I get the model "{id}"'.format(id=world.model['resource']))
           status = get_status(world.model)
    assert status['code'] == int(code1)

@step(r'I wait until the model is ready less than (\d+)')
def the_model_is_finished_in_less_than(step, secs):
    wait_until_model_status_code_is(step, FINISHED, FAULTY, secs)

@step(r'I create a model with "(.*)"')
def i_create_a_model_with(step, data="{}"):
    resource = world.api.create_model(world.dataset.get('resource'), json.loads(data))
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.model = resource['object']
    world.models.append(resource['resource'])

@step(r'I make the model public')
def make_the_model_public(step):
    resource = world.api.update_model(world.model['resource'],
                                      {'private': False, 'white_box': True})
    world.status = resource['code']
    assert world.status == HTTP_ACCEPTED
    world.location = resource['location']
    world.model = resource['object']

@step(r'I check the model status using the model\'s public url')
def model_from_public_url(step):
    world.model = world.api.get_model("public/%s" % world.model['resource'])
    assert get_status(world.model)['code'] == FINISHED

@step(r'I make the model shared')
def make_the_model_shared(step):
    resource = world.api.update_model(world.model['resource'],
                                      {'shared': True})
    world.status = resource['code']
    assert world.status == HTTP_ACCEPTED
    world.location = resource['location']
    world.model = resource['object']

@step(r'I get the model sharing info')
def get_sharing_info(step):
    world.shared_hash = world.model['shared_hash']
    world.sharing_key = world.model['sharing_key']

@step(r'I check the model status using the model\'s shared url')
def model_from_shared_url(step):
    world.model = world.api.get_model("shared/model/%s" % world.shared_hash)
    assert get_status(world.model)['code'] == FINISHED

@step(r'I check the model status using the model\'s shared key')
def model_from_shared_key(step):
   
    username = os.environ.get("BIGML_USERNAME")
    world.model = world.api.get_model(world.model['resource'],
        shared_username=username, shared_api_key=world.sharing_key)
    assert get_status(world.model)['code'] == FINISHED

@step(r'"(.*)" field\'s name is changed to "(.*)"')
def field_name_to_new_name(step, field_id, new_name):
    if world.local_model.tree.fields[field_id]['name'] != new_name:
        print world.local_model.tree.fields[field_id]['name'], new_name
    assert world.local_model.tree.fields[field_id]['name'] == new_name

########NEW FILE########
__FILENAME__ = create_multimodel-steps
from lettuce import step, world

@step(r'I store the dataset id in a list')
def i_store_dataset_id(step):
    world.dataset_ids.append(world.dataset['resource'])

@step(r'I check the model stems from the original dataset list')
def i_check_model_datasets_and_datasets_ids(step):
    model = world.model
    if 'datasets' in model and model['datasets'] == world.dataset_ids:
        assert True
    else:
        assert False, ("The model contains only %s "
                       "and the dataset ids are %s" %
                       (",".join(model['datasets']),
                        ",".join(world.dataset_ids)))                  

########NEW FILE########
__FILENAME__ = create_prediction-steps
import json
import time
from datetime import datetime, timedelta
from lettuce import step, world
from bigml.api import HTTP_CREATED
from bigml.api import FINISHED, FAULTY
from bigml.api import get_status


@step(r'I create a prediction for "(.*)"')
def i_create_a_prediction(step, data=None):
    if data is None:
        data = "{}"
    model = world.model['resource']
    data = json.loads(data)
    resource = world.api.create_prediction(model, data)
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.prediction = resource['object']
    world.predictions.append(resource['resource'])


@step(r'I create a centroid for "(.*)"')
def i_create_a_centroid(step, data=None):
    if data is None:
        data = "{}"
    cluster = world.cluster['resource']
    data = json.loads(data)
    resource = world.api.create_centroid(cluster, data)
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.centroid = resource['object']
    world.centroids.append(resource['resource'])


@step(r'I create a proportional missing strategy prediction for "(.*)"')
def i_create_a_proportional_prediction(step, data=None):
    if data is None:
        data = "{}"
    model = world.model['resource']
    data = json.loads(data)
    resource = world.api.create_prediction(model, data,
                                           args={'missing_strategy': 1})
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.prediction = resource['object']
    world.predictions.append(resource['resource'])


@step(r'the prediction for "(.*)" is "(.*)"')
def the_prediction_is(step, objective, prediction):
    assert str(world.prediction['prediction'][objective]) == prediction


@step(r'the centroid is "(.*)"')
def the_centroid_is(step, centroid):
    assert str(world.centroid['centroid_name']) == centroid

@step(r'I check the centroid is ok')
def the_centroid_is_ok(step):
    assert world.api.ok(world.centroid)

@step(r'the confidence for the prediction is "(.*)"')
def the_confidence_is(step, confidence):
    local_confidence = round(float(world.prediction['confidence']), 4)
    confidence = round(float(confidence), 4)
    assert local_confidence == confidence


@step(r'I create an ensemble prediction for "(.*)"')
def i_create_an_ensemble_prediction(step, data=None):
    if data is None:
        data = "{}"
    ensemble = world.ensemble['resource']
    data = json.loads(data)
    resource = world.api.create_prediction(ensemble, data)
    world.status = resource['code']
    assert world.status == HTTP_CREATED
    world.location = resource['location']
    world.prediction = resource['object']
    world.predictions.append(resource['resource'])

@step(r'I wait until the prediction status code is either (\d) or (\d) less than (\d+)')
def wait_until_prediction_status_code_is(step, code1, code2, secs):
    start = datetime.utcnow()
    step.given('I get the prediction "{id}"'.format(id=world.prediction['resource']))
    status = get_status(world.prediction)
    while (status['code'] != int(code1) and
           status['code'] != int(code2)):
        time.sleep(3)
        assert datetime.utcnow() - start < timedelta(seconds=int(secs))
        step.given('I get the prediction "{id}"'.format(id=world.prediction['resource']))
        status = get_status(world.prediction)
    assert status['code'] == int(code1)

@step(r'I wait until the prediction is ready less than (\d+)')
def the_prediction_is_finished_in_less_than(step, secs):
    wait_until_prediction_status_code_is(step, FINISHED, FAULTY, secs)

@step(r'I create a local ensemble prediction for "(.*)"$')
def create_local_ensemble_prediction(step, input_data):
    world.local_prediction = world.local_ensemble.predict(json.loads(input_data))

########NEW FILE########
__FILENAME__ = create_source-steps
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2012 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import time
import json
from datetime import datetime, timedelta
from urllib import urlencode
from lettuce import step, world

from bigml.api import HTTP_CREATED, HTTP_ACCEPTED
from bigml.api import FINISHED
from bigml.api import FAULTY
from bigml.api import UPLOADING
from bigml.api import get_status

@step(r'I create a data source uploading a "(.*)" file$')
def i_upload_a_file(step, file):
    resource = world.api.create_source(file)
    # update status
    world.status = resource['code']
    world.location = resource['location']
    world.source = resource['object']
    # save reference
    world.sources.append(resource['resource'])

@step(r'I create a data source using the url "(.*)"')
def i_create_using_url(step, url):
    resource = world.api.create_source(url)
    # update status
    world.status = resource['code']
    world.location = resource['location']
    world.source = resource['object']
    # save reference
    world.sources.append(resource['resource'])

@step(r'I create a data source uploading a "(.*)" file in asynchronous mode$')
def i_upload_a_file_async(step, file):
    resource = world.api.create_source(file, async=True)
    world.resource = resource

@step(r'I wait until the source has been created less than (\d+) secs')
def the_source_has_been_created_async(step, secs):
    start = datetime.utcnow()
    status = get_status(world.resource)
    while status['code'] == UPLOADING:
        time.sleep(3)
        assert datetime.utcnow() - start < timedelta(seconds=int(secs))
        status = get_status(world.resource)
    assert world.resource['code'] == HTTP_CREATED
    # update status
    world.status = world.resource['code']
    world.location = world.resource['location']
    world.source = world.resource['object']
    # save reference
    world.sources.append(world.resource['resource'])

@step(r'I wait until the source status code is either (\d) or (\d) less than (\d+)')
def wait_until_source_status_code_is(step, code1, code2, secs):
    start = datetime.utcnow()
    step.given('I get the source "{id}"'.format(id=world.source['resource']))
    status = get_status(world.source)
    while (status['code'] != int(code1) and
           status['code'] != int(code2)):
        time.sleep(3)
        assert datetime.utcnow() - start < timedelta(seconds=int(secs))
        step.given('I get the source "{id}"'.format(id=world.source['resource']))
        status = get_status(world.source)
    assert status['code'] == int(code1)

@step(r'I wait until the source is ready less than (\d+)')
def the_source_is_finished(step, secs):
    wait_until_source_status_code_is(step, FINISHED, FAULTY, secs)

@step(r'I update the source with params "(.*)"')
def i_update_source_with(step, data="{}"):
    resource = world.api.update_source(world.source.get('resource'), json.loads(data))
    world.status = resource['code']
    assert world.status == HTTP_ACCEPTED

########NEW FILE########
__FILENAME__ = read_batch_prediction-steps
import os
from lettuce import step, world

from bigml.api import HTTP_OK

@step(r'I get the batch prediction "(.*)"')
def i_get_the_batch_prediction(step, batch_prediction):
    resource = world.api.get_batch_prediction(batch_prediction)
    world.status = resource['code']
    assert world.status == HTTP_OK
    world.batch_prediction = resource['object']


########NEW FILE########
__FILENAME__ = read_cluster-steps
import os
from lettuce import step, world

from bigml.api import HTTP_OK

@step(r'I get the cluster "(.*)"')
def i_get_the_cluster(step, cluster):
    resource = world.api.get_cluster(cluster)
    world.status = resource['code']
    assert world.status == HTTP_OK
    world.cluster = resource['object']

@step(r'I get the batch centroid "(.*)"')
def i_get_the_batch_centroid(step, batch_centroid):
    resource = world.api.get_batch_centroid(batch_centroid)
    world.status = resource['code']
    assert world.status == HTTP_OK
    world.batch_centroid = resource['object']

@step(r'I get the centroid "(.*)"')
def i_get_the_centroid(step, centroid):
    resource = world.api.get_centroid(centroid)
    world.status = resource['code']
    assert world.status == HTTP_OK
    world.centroid = resource['object']

########NEW FILE########
__FILENAME__ = read_dataset-steps
import json

from lettuce import step, world
from bigml.api import HTTP_OK
from bigml.fields import Fields

@step(r'I get the dataset "(.*)"')
def i_get_the_dataset(step, dataset):
    resource = world.api.get_dataset(dataset)
    world.status = resource['code']
    assert world.status == HTTP_OK
    world.dataset = resource['object']


@step(r'I ask for the missing values counts in the fields')
def i_get_the_missing_values(step):
    resource = world.dataset
    fields = Fields(resource['fields'])
    world.step_result = fields.missing_counts()


@step(r'I ask for the error counts in the fields')
def i_get_the_errors_values(step):
    resource = world.dataset
    world.step_result = world.api.error_counts(resource)


@step(r'the (missing values counts|error counts) dict is "(.*)"')
def i_get_the_errors_values(step, text, properties_dict):
    if properties_dict is None:
        assert False
    assert world.step_result == json.loads(properties_dict)

########NEW FILE########
__FILENAME__ = read_ensemble-steps
import os
from lettuce import step, world

from bigml.api import HTTP_OK

@step(r'I get the ensemble "(.*)"')
def i_get_the_ensemble(step, ensemble):
    resource = world.api.get_ensemble(ensemble)
    world.status = resource['code']
    assert world.status == HTTP_OK
    world.ensemble = resource['object']


########NEW FILE########
__FILENAME__ = read_evaluation-steps
import os
from lettuce import step, world

from bigml.api import HTTP_OK

@step(r'I get the evaluation "(.*)"')
def i_get_the_evaluation(step, evaluation):
    resource = world.api.get_evaluation(evaluation)
    world.status = resource['code']
    assert world.status == HTTP_OK
    world.evaluation = resource['object']


########NEW FILE########
__FILENAME__ = read_model-steps
import os
from lettuce import step, world

from bigml.api import HTTP_OK

@step(r'I get the model "(.*)"')
def i_get_the_model(step, model):
    resource = world.api.get_model(model)
    world.status = resource['code']
    assert world.status == HTTP_OK
    world.model = resource['object']


########NEW FILE########
__FILENAME__ = read_prediction-steps
import os
from lettuce import step, world
from bigml.api import HTTP_OK

@step(r'I get the prediction "(.*)"')
def i_get_the_prediction(step, prediction):
    resource = world.api.get_prediction(prediction)
    world.status = resource['code']
    assert world.status == HTTP_OK
    world.prediction = resource['object']

########NEW FILE########
__FILENAME__ = read_source-steps
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2012 BigML
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from lettuce import step, world
from bigml.api import HTTP_OK

@step(r'I get the source "(.*)"')
def i_get_the_source(step, resource):
    resource = world.api.get_source(resource)
    world.status = resource['code']
    assert world.status == HTTP_OK
    world.source = resource['object']

@step(r'the source has DEV (True|False)')
def source_has_dev(step, boolean):
    if boolean == 'False':
        boolean = ''
    boolean = bool(boolean)
    dev = world.source['dev']
    assert dev == boolean

########NEW FILE########
__FILENAME__ = terrain
# terrain.py
import os
import shutil

from lettuce import before, after, world

from bigml.api import BigML
from bigml.api import HTTP_OK

@before.each_feature
def setup_resources(feature):
    world.USERNAME = os.environ['BIGML_USERNAME']
    world.API_KEY = os.environ['BIGML_API_KEY']
    assert world.USERNAME is not None
    assert world.API_KEY is not None
    world.api = BigML(world.USERNAME, world.API_KEY)
    world.api_dev_mode = BigML(world.USERNAME, world.API_KEY, dev_mode=True)

    sources = world.api.list_sources()
    assert sources['code'] == HTTP_OK
    world.init_sources_count = sources['meta']['total_count']

    datasets = world.api.list_datasets()
    assert datasets['code'] == HTTP_OK
    world.init_datasets_count = datasets['meta']['total_count']

    models = world.api.list_models()
    assert models['code'] == HTTP_OK
    world.init_models_count = models['meta']['total_count']

    predictions = world.api.list_predictions()
    assert predictions['code'] == HTTP_OK
    world.init_predictions_count = predictions['meta']['total_count']

    evaluations = world.api.list_evaluations()
    assert evaluations['code'] == HTTP_OK
    world.init_evaluations_count = evaluations['meta']['total_count']

    ensembles = world.api.list_ensembles()
    assert ensembles['code'] == HTTP_OK
    world.init_ensembles_count = ensembles['meta']['total_count']

    batch_predictions = world.api.list_batch_predictions()
    assert batch_predictions['code'] == HTTP_OK
    world.init_batch_predictions_count = batch_predictions['meta']['total_count']

    clusters = world.api.list_clusters()
    assert clusters['code'] == HTTP_OK
    world.init_clusters_count = clusters['meta']['total_count']

    centroids = world.api.list_centroids()
    assert centroids['code'] == HTTP_OK
    world.init_centroids_count = centroids['meta']['total_count']

    batch_centroids = world.api.list_batch_centroids()
    assert batch_centroids['code'] == HTTP_OK
    world.init_batch_centroids_count = batch_centroids['meta']['total_count']

    world.sources = []
    world.datasets = []
    world.models = []
    world.predictions = []
    world.evaluations = []
    world.ensembles = []
    world.batch_predictions = []
    world.clusters = []
    world.centroids = []
    world.batch_centroids = []

    world.dataset_ids = []
    world.fields_properties_dict = {}
@after.each_feature
def cleanup_resources(feature):

    if os.path.exists('./tmp'):
        shutil.rmtree('./tmp')

    # first delete clusters to be able to delete datasets generated from them
    for id in world.clusters:
        world.api.delete_cluster(id)
    world.clusters = []

    for id in world.sources:
        world.api.delete_source(id)
    world.sources = []

    for id in world.datasets:
        world.api.delete_dataset(id)
    world.datasets = []

    for id in world.models:
        world.api.delete_model(id)
    world.models = []

    for id in world.predictions:
        world.api.delete_prediction(id)
    world.predictions = []

    for id in world.evaluations:
        world.api.delete_evaluation(id)
    world.evaluations = []

    for id in world.ensembles:
        world.api.delete_ensemble(id)
    world.ensembles = []

    for id in world.batch_predictions:
        world.api.delete_batch_prediction(id)
    world.batch_predictions = []

    for id in world.centroids:
        world.api.delete_centroid(id)
    world.centroids = []

    for id in world.batch_centroids:
        world.api.delete_batch_centroid(id)
    world.batch_centroids = []

    sources = world.api.list_sources()
    assert sources['code'] == HTTP_OK
    world.final_sources_count = sources['meta']['total_count']

    datasets = world.api.list_datasets()
    assert datasets['code'] == HTTP_OK
    world.final_datasets_count = datasets['meta']['total_count']

    models = world.api.list_models()
    assert models['code'] == HTTP_OK
    world.final_models_count = models['meta']['total_count']

    predictions = world.api.list_predictions()
    assert predictions['code'] == HTTP_OK
    world.final_predictions_count = predictions['meta']['total_count']

    evaluations = world.api.list_evaluations()
    assert evaluations['code'] == HTTP_OK
    world.final_evaluations_count = evaluations['meta']['total_count']

    ensembles = world.api.list_ensembles()
    assert ensembles['code'] == HTTP_OK
    world.final_ensembles_count = ensembles['meta']['total_count']

    clusters = world.api.list_clusters()
    assert clusters['code'] == HTTP_OK
    world.final_clusters_count = clusters['meta']['total_count']

    batch_predictions = world.api.list_batch_predictions()
    assert batch_predictions['code'] == HTTP_OK
    world.final_batch_predictions_count = batch_predictions['meta']['total_count']

    centroids = world.api.list_centroids()
    assert centroids['code'] == HTTP_OK
    world.final_centroids_count = centroids['meta']['total_count']

    batch_centroids = world.api.list_batch_centroids()
    assert batch_centroids['code'] == HTTP_OK
    world.final_batch_centroids_count = batch_centroids['meta']['total_count']


    assert world.final_sources_count == world.init_sources_count
    assert world.final_datasets_count == world.init_datasets_count
    assert world.final_models_count == world.init_models_count
    assert world.final_predictions_count == world.init_predictions_count
    assert world.final_evaluations_count == world.init_evaluations_count
    assert world.final_ensembles_count == world.init_ensembles_count
    assert world.final_batch_predictions_count == world.init_batch_predictions_count
    assert world.final_clusters_count == world.init_clusters_count
    assert world.final_centroids_count == world.init_centroids_count
    assert world.final_batch_centroids_count == world.init_batch_centroids_count

@after.each_scenario
def cleanup_resources(scenario):
    world.dataset_ids = []

########NEW FILE########
