__FILENAME__ = ci_run
import logging
import os
import sys


def integrate():
    standard_sdist_run(submodule_order=(
        'daf_fruit_dist',
        'daf_fruit_seed',
        'daf_fruit_orchard'))


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s')

    sys.path.insert(0, os.path.abspath('daf_fruit_dist'))
    from daf_fruit_dist.ci_utils import standard_sdist_run

    integrate()

########NEW FILE########
__FILENAME__ = continuous_integration
import os


def integrate():
    # Test this package, then install the development version of it.
    from daf_fruit_dist.ci_single_module_utils import standard_develop_run

    standard_develop_run()

    # Also build an sdist to be uploaded later.
    from daf_fruit_dist.exec_utils import build_sdist

    build_sdist()


if __name__ == '__main__':
    # Change active directories to the one containing this file.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    integrate()

########NEW FILE########
__FILENAME__ = artifactory_rest
from functools import partial
import glob
import json
import logging
import os
import hashlib
import mimetypes
import pprint
import requests
from daf_fruit_dist.checksums import Checksums
from daf_fruit_dist.file_management import get_file_digests


_HEADER_USER_AGENT = 'User-Agent'
_HEADER_MD5_CHECKSUM = 'X-Checksum-Md5'
_HEADER_SHA1_CHECKSUM = 'X-Checksum-Sha1'
_HEADER_CONTENT_TYPE = 'Content-Type'
_HEADER_CONTENT_ENCODING = 'Content-Encoding'

_CONTENT_TYPE_PROMOTION_REQUEST = (
    'application/vnd.org.jfrog.artifactory.build.PromotionRequest+json')

_CONTENT_TYPE_PUBLISH_BUILD_INFO = (
    'application/vnd.org.jfrog.artifactory+json')


def deploy_file(
        repo_base_url,
        repo_push_id,
        path,
        filename,
        attributes=None,
        username=None,
        password=None,
        verify_cert=True):
    """
    Deploy the file to the /path/ directory at the given URL. A
    dictionary (or pre-formatted string) of attributes may also be
    supplied.
    """

    def store_hashes_in_headers(headers):
        md5, sha1 = get_file_digests(
            filename,
            digests=(hashlib.md5(), hashlib.sha1()))

        headers[_HEADER_MD5_CHECKSUM] = md5.hexdigest()
        headers[_HEADER_SHA1_CHECKSUM] = sha1.hexdigest()

    def store_mimetypes_in_headers(headers):
        content_type, content_enc = mimetypes.guess_type(filename)

        if content_type:
            headers[_HEADER_CONTENT_TYPE] = content_type
        if content_enc:
            headers[_HEADER_CONTENT_ENCODING] = content_enc

    def generate_uri():
        basename = os.path.basename(filename)
        norm_path = _normalize_path(path)
        uri = '{url}/{repo_push_id}/{path}/{basename}'.format(
            url=repo_base_url,
            repo_push_id=repo_push_id,
            path=norm_path,
            basename=basename)

        if attributes:
            if isinstance(attributes, dict):
                uri += ';' + ';'.join(
                    '{}={}'.format(k, v) for k, v in attributes.iteritems())
            elif isinstance(attributes, basestring):
                uri += ';' + attributes
            else:
                raise TypeError(
                    '"attributes" must be either a dictionary or a pre-'
                    'formatted string of "key1=value1;key2=value2" pairs')
        return uri

    def upload_file(deploy_uri):
        logging.info('Deploying: ' + deploy_uri)

        auth = (username, password) if (username or password) else None

        with open(filename, 'rb') as f:
            response = requests.put(
                deploy_uri,
                data=f,
                auth=auth,
                headers=headers,
                verify=verify_cert)

            _log_response(response)

    headers = _make_headers()

    store_hashes_in_headers(headers)
    store_mimetypes_in_headers(headers)

    upload_file(generate_uri())


def deploy_globbed_files(
        repo_base_url,
        repo_push_id,
        path,
        glob_patterns,
        attributes=None,
        username=None,
        password=None,
        verify_cert=True):
    """
    Like deploy_file, except this function takes a list of globbing
    patterns. All files (NOT directories) matched by these patterns are
    deployed to the server.
    """
    logging.debug("Entering deploy_globbed_files with:")
    logging.debug("   repo_base_url: {}".format(repo_base_url))
    logging.debug("   repo_push_id: {}".format(repo_push_id))
    logging.debug("   path: {}".format(path))
    logging.debug("   glob_patterns: {}".format(glob_patterns))

    # Create a version of deploy_file() with every field filled out
    # except for filename.
    deploy = partial(
        deploy_file,
        repo_base_url=repo_base_url,
        repo_push_id=repo_push_id,
        path=path,
        attributes=attributes,
        username=username,
        password=password,
        verify_cert=verify_cert)

    # Set of all files being uploaded. Note that a set is being used
    # here instead of a list so that files matched by more than one
    # globbing pattern are only uploaded once.
    filenames = set()

    for pattern in glob_patterns:
        filenames.update(filter(os.path.isfile, glob.glob(pattern)))

    logging.debug("Found filenames: {}".format(", ".join(filenames)))

    for f in filenames:
        deploy(filename=f)

    return filenames


def build_promote(
        username,
        password,
        repo_base_url,
        build_name,
        build_number,
        promotion_request,
        verify_cert=True):

    uri = '{url}/api/build/promote/{build_name}/{build_number}'.format(
        url=repo_base_url,
        build_name=build_name,
        build_number=build_number)

    json_data = promotion_request.as_json_data
    json_to_put_on_wire = json.dumps(json_data, sort_keys=True)

    auth = _make_auth(username, password)

    headers = _make_headers()
    headers[_HEADER_CONTENT_TYPE] = _CONTENT_TYPE_PROMOTION_REQUEST

    put_req = requests.post(
        uri,
        data=json_to_put_on_wire,
        headers=headers,
        auth=auth,
        verify=verify_cert)

    _log_response(put_req)
    put_req.raise_for_status()

    response_json = put_req.json()

    return response_json


def publish_build_info(
        username,
        password,
        repo_base_url,
        build_info,
        verify_cert=True):

    json_data = build_info.as_json_data
    json_to_put_on_wire = json.dumps(json_data, sort_keys=True)

    uri = '{url}/api/build'.format(url=repo_base_url)
    auth = _make_auth(username, password)

    headers = _make_headers()
    headers[_HEADER_CONTENT_TYPE] = _CONTENT_TYPE_PUBLISH_BUILD_INFO

    put_req = requests.put(
        uri,
        data=json_to_put_on_wire,
        headers=headers,
        auth=auth,
        verify=verify_cert)

    _log_response(response=put_req)

    put_req.raise_for_status()


def determine_checksums(
        username,
        password,
        repo_base_url,
        repo_pull_id,
        file_path,
        verify_cert=True):

    uri = '{url}/api/storage/{repo_pull_id}/{file_path}'.format(
        url=repo_base_url,
        repo_pull_id=repo_pull_id,
        file_path=file_path)

    auth = _make_auth(username, password)

    get_response = requests.get(
        uri,
        headers=_make_headers(),
        auth=auth,
        verify=verify_cert)

    get_response.raise_for_status()
    response_json = get_response.json()

    if 'checksums' in response_json:
        checksum_data = response_json['checksums']
        md5 = checksum_data.get('md5', None)
        sha1 = checksum_data.get('sha1', None)
    else:
        raise RuntimeError(
            "Artifact found in Artifactory but no checksums were available.")

    return Checksums(sha1=sha1, md5=md5)


def _normalize_path(path):
    return path.strip('/')


def _make_auth(username=None, password=None):
    return (username, password) if (username or password) else None


def _make_headers():
    return {_HEADER_USER_AGENT: 'FruitDist/1.0'}


def _log_response(response):
    _log_data_structure('response_headers', response.headers)

    try:
        _log_data_structure('response_json', response.json())
    except StandardError:
        response_text = getattr(response, 'text', None)
        if response_text:
            logging.debug('response_text: {}'.format(response_text))


def _log_data_structure(title, data_structure):
    unindented = pprint.pformat(data_structure)
    shifted = '\n   '.join(unindented.splitlines())
    log_msg = '{}:\n   {}'.format(title, shifted)
    logging.debug(log_msg)

########NEW FILE########
__FILENAME__ = repo_detail
from collections import namedtuple
from distutils.errors import DistutilsOptionError
from distutils.dist import Distribution

RepoDetail = namedtuple(
    'RepoDetail', [
        'repo_base_url',
        'repo_push_id',
        'repo_pull_id',
        'username',
        'password'])


def read_options(
        repo_base_url=None,
        repo_push_id=None,
        repo_pull_id=None,
        username=None,
        password=None):

    if repo_base_url and repo_push_id and username and password:
        return RepoDetail(
            repo_base_url=repo_base_url,
            repo_push_id=repo_push_id,
            repo_pull_id=repo_pull_id,
            username=username,
            password=password)

    artifactory_opts = _read_artifactory_config_section()

    return RepoDetail(
        repo_base_url=_read_value_from_opts(artifactory_opts, 'repo_base_url'),
        repo_push_id=_read_value_from_opts(artifactory_opts, 'repo_push_id'),
        repo_pull_id=_read_value_from_opts(artifactory_opts, 'repo_pull_id'),
        username=_read_value_from_opts(artifactory_opts, 'username'),
        password=_read_value_from_opts(artifactory_opts, 'password'))


def _read_value_from_opts(artifactory_opts, key):
    try:
        config_file_name, config_value = artifactory_opts.get(key)
        return config_value
    except KeyError:
        return None


def _read_artifactory_config_section():
    dist = Distribution()
    file_names = dist.find_config_files()
    dist.parse_config_files(filenames=file_names)
    artifactory_config_key = "artifactory"
    artifactory_opts = dist.get_option_dict(artifactory_config_key)

    if not artifactory_opts:
        raise DistutilsOptionError(
            'Could not find a {} section in {}'.format(
                artifactory_config_key,
                file_names))

    return artifactory_opts

########NEW FILE########
__FILENAME__ = agent
class Agent(object):
    def __init__(self, name, version):
        super(Agent, self).__init__()
        self._name = name
        self._version = version

    def __repr__(self):
        return '''Agent(name=%r, version=%r)'''\
               % (self._name, self._version)

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    @classmethod
    def from_json_data(cls, json_data):
        return Agent(
            name=json_data['name'],
            version=json_data['version'])

    @property
    def as_json_data(self):
        return {'name': self.name,
                'version': self.version}

    def __attrs(self):
        return self._name, self._version

    def __hash__(self):
        return hash(self.__attrs())

    def __eq__(self, other):
        return isinstance(other, Agent) and self.__attrs() == other.__attrs()

    def __ne__(self, other):
        return not self == other

########NEW FILE########
__FILENAME__ = artifact
class Artifact(object):
    def __init__(self, type, name, sha1=None, md5=None):
        super(Artifact, self).__init__()
        self._type = type
        self._name = name
        self._sha1 = sha1
        self._md5 = md5

    def __repr__(self):
        return '''Artifact(type=%r, name=%r, sha1=%r, md5=%r)''' \
               % (self._type, self._name, self._sha1, self._md5)

    @property
    def type(self):
        return self._type

    @property
    def name(self):
        return self._name

    @property
    def sha1(self):
        return self._sha1

    @property
    def md5(self):
        return self._md5

    @classmethod
    def from_json_data(cls, json_data):
        return Artifact(
            type=json_data['type'],
            sha1=json_data['sha1'],
            md5=json_data['md5'],
            name=json_data['name'])

    @property
    def as_json_data(self):
        return {"type": self.type,
                "sha1": self.sha1,
                "md5": self.md5,
                "name": self.name}

    def __attrs(self):
        return self._type, self._name, self._sha1, self._md5

    def __hash__(self):
        return hash(self.__attrs())

    def __eq__(self, other):
        return (
            isinstance(other, Artifact) and
            self.__attrs() == other.__attrs())

    def __ne__(self, other):
        return not self == other

########NEW FILE########
__FILENAME__ = build_info
from daf_fruit_dist.build.build_util import nested_object_from_json_data
from daf_fruit_dist.build.agent import Agent
from daf_fruit_dist.build.build_retention import BuildRetention
from daf_fruit_dist.build.module import Module


class BuildInfo(object):
    def __init__(self, builder):
        super(BuildInfo, self).__init__()
        self._version = builder._version
        self._name = builder._name
        self._number = builder._number
        self._type = builder._type
        self._started = builder._started
        self._duration_millis = builder._duration_millis
        self._artifactory_principal = builder._artifactory_principal
        self._agent = builder._agent
        self._build_agent = builder._build_agent
        self._build_retention = builder._build_retention
        self._modules = tuple(builder._modules)

    @property
    def version(self):
        return self._version

    @property
    def name(self):
        return self._name

    @property
    def number(self):
        return self._number

    @property
    def type(self):
        return self._type

    @property
    def started(self):
        return self._started

    @property
    def duration_millis(self):
        return self._duration_millis

    @property
    def artifactory_principal(self):
        return self._artifactory_principal

    @property
    def agent(self):
        return self._agent

    @property
    def build_agent(self):
        return self._build_agent

    @property
    def build_retention(self):
        return self._build_retention

    @property
    def modules(self):
        return tuple(self._modules)

    @classmethod
    def from_json_data(cls, json_data):
        agent = nested_object_from_json_data(
            json_data,
            'agent',
            Agent.from_json_data)

        build_agent = nested_object_from_json_data(
            json_data,
            'buildAgent',
            Agent.from_json_data)

        build_retention = nested_object_from_json_data(
            json_data,
            'buildRetention',
            BuildRetention.from_json_data)

        builder = BuildInfo.Builder(
            version=json_data['version'],
            name=json_data['name'],
            number=json_data['number'],
            type=json_data['type'],
            started=json_data['started'],
            duration_millis=json_data['durationMillis'],
            artifactory_principal=json_data['artifactoryPrincipal'],
            agent=agent,
            build_agent=build_agent,
            build_retention=build_retention
        )

        modules = [Module.from_json_data(x) for x in json_data['modules']]

        for module in modules:
            builder.add_module(module)

        return builder.build()

    @property
    def as_json_data(self):
        modules_as_json_data = [x.as_json_data for x in self.modules]

        return {"version": self.version,
                "name": self.name,
                "number": self.number,
                "type": self.type,
                "buildAgent": getattr(self.build_agent, 'as_json_data', None),
                "agent": getattr(self.agent, 'as_json_data', None),
                "started": self.started,
                "durationMillis": self.duration_millis,
                "artifactoryPrincipal": self.artifactory_principal,
                "buildRetention": getattr(
                    self.build_retention, 'as_json_data', None),
                "modules": modules_as_json_data}

    def __attrs(self):
        return (self._version,
                self._name,
                self._number,
                self._type,
                self._started,
                self._duration_millis,
                self._artifactory_principal,
                self._agent,
                self._build_agent,
                self._build_retention,
                self._modules)

    def __hash__(self):
        return hash(self.__attrs())

    def __eq__(self, other):
        return (
            isinstance(other, BuildInfo) and
            self.__attrs() == other.__attrs())

    def __ne__(self, other):
        return not self == other

    class Builder(object):
        def __init__(self,
                     version=None,
                     name=None,
                     number=None,
                     type=None,
                     started=None,
                     duration_millis=None,
                     artifactory_principal=None,
                     agent=None,
                     build_agent=None,
                     build_retention=None):
            super(BuildInfo.Builder, self).__init__()
            self._version = version
            self._name = name
            self._number = number
            self._type = type
            self._started = started
            self._duration_millis = duration_millis
            self._artifactory_principal = artifactory_principal
            self._agent = agent
            self._build_agent = build_agent
            self._build_retention = build_retention
            self._modules = []

        def add_module(self, module):
            self._modules.append(module)

        def build(self):
            return BuildInfo(builder=self)

########NEW FILE########
__FILENAME__ = build_retention
class BuildRetention(object):
    def __init__(self,
                 count=None,
                 delete_build_artifacts=None,
                 build_numbers_not_to_be_discarded=None):

        super(BuildRetention, self).__init__()

        self._count = count
        self._delete_build_artifacts = delete_build_artifacts
        self._build_numbers_not_to_be_discarded = \
            build_numbers_not_to_be_discarded

    def __repr__(self):
        return (
            'BuildRetention('
            'count=%r, '
            'delete_build_artifacts=%r, '
            'build_numbers_not_to_be_discarded=%r)' % (
                self._count,
                self._delete_build_artifacts,
                self._build_numbers_not_to_be_discarded))

    @property
    def count(self):
        return self._count

    @property
    def delete_build_artifacts(self):
        return self._delete_build_artifacts

    @property
    def build_numbers_not_to_be_discarded(self):
        return self._build_numbers_not_to_be_discarded

    @classmethod
    def from_json_data(cls, json_data):
        return BuildRetention(
            count=json_data['count'],
            delete_build_artifacts=json_data['deleteBuildArtifacts'],
            build_numbers_not_to_be_discarded=json_data[
                'buildNumbersNotToBeDiscarded'])

    @property
    def as_json_data(self):
        return {
            'count':
            self.count,

            'deleteBuildArtifacts':
            self.delete_build_artifacts,

            'buildNumbersNotToBeDiscarded':
            self.build_numbers_not_to_be_discarded,
        }

    def __attrs(self):
        return (
            self._count,
            self._delete_build_artifacts,
            frozenset(self._build_numbers_not_to_be_discarded))

    def __hash__(self):
        return hash(self.__attrs())

    def __eq__(self, other):
        return (
            isinstance(other, BuildRetention) and
            self.__attrs() == other.__attrs())

    def __ne__(self, other):
        return not self == other

########NEW FILE########
__FILENAME__ = build_util
def nested_object_from_json_data(json_data, key, decode_func):
    rv = None
    if key in json_data:
        data = json_data[key]
        if data:
            rv = decode_func(json_data[key])
    return rv


def get_attr_as_tuple_unless_none(object, name):
    value_as_tuple = None
    value = getattr(object, name, None)
    if value is not None:
        value_as_tuple = tuple(value)
    return value_as_tuple


def get_attr_as_list_unless_none(object, name):
    value_as_list = None
    value = getattr(object, name, None)
    if value is not None:
        value_as_list = list(value)
    return value_as_list

########NEW FILE########
__FILENAME__ = constants
PYTHON_SDIST = "python.sdist"
PYTHON_BDIST = "python.bdist"
PYTHON_EGG = "python.egg"
PYTHON_WHEEL = "python.wheel"
PYTHON_SPHINX = "python.sphinx"
PYTHON_RPM = "python.rpm"
PYTHON_FREEZE = "python.freeze"

PYTHON_GROUP_ID = "python"

########NEW FILE########
__FILENAME__ = dependency
from daf_fruit_dist.build.id import Id
from daf_fruit_dist.build.build_util import nested_object_from_json_data


class Dependency(object):
    def __init__(self, type, id, sha1=None, md5=None):
        super(Dependency, self).__init__()
        self._type = type
        self._id = id
        self._sha1 = sha1
        self._md5 = md5

    def __repr__(self):
        return '''Dependency(type=%r, id=%r, sha1=%r, md5=%r)'''\
               % (self._type, self._id, self._sha1, self._md5)

    @property
    def type(self):
        return self._type

    @property
    def id(self):
        return self._id

    @property
    def sha1(self):
        return self._sha1

    @property
    def md5(self):
        return self._md5

    @classmethod
    def from_json_data(cls, json_data):
        id = nested_object_from_json_data(json_data, 'id', Id.from_json_data)

        return Dependency(
            type=json_data['type'],
            sha1=json_data['sha1'],
            md5=json_data['md5'],
            id=id)

    @property
    def as_json_data(self):
        return {"type": self.type,
                "sha1": self.sha1,
                "md5": self.md5,
                "id": getattr(self.id, 'as_json_data', None)}

    def __attrs(self):
        return self._type, self._id, self._sha1, self._md5

    def __hash__(self):
        return hash(self.__attrs())

    def __eq__(self, other):
        return (
            isinstance(other, Dependency) and
            self.__attrs() == other.__attrs())

    def __ne__(self, other):
        return not self == other

########NEW FILE########
__FILENAME__ = id
class Id(object):
    def __init__(self, group_id, artifact_id, version):
        super(Id, self).__init__()
        self._group_id = group_id
        self._artifact_id = artifact_id
        self._version = version

    def __repr__(self):
        return '''Id(group_id=%r, artifact_id=%r, version=%r)'''\
               % (self._group_id, self._artifact_id, self._version)

    @property
    def group_id(self):
        return self._group_id

    @property
    def artifact_id(self):
        return self._artifact_id

    @property
    def version(self):
        return self._version

    @classmethod
    def from_json_data(cls, json_data):
        group_id, artifact_id, version = json_data.split(":")
        return Id(
            group_id=group_id,
            artifact_id=artifact_id,
            version=version)

    @property
    def as_json_data(self):
        id_as_string = ":".join((
            self.group_id,
            self.artifact_id,
            self.version))
        return id_as_string

    def __attrs(self):
        return self._group_id, self._artifact_id, self._version

    def __hash__(self):
        return hash(self.__attrs())

    def __eq__(self, other):
        return isinstance(other, Id) and self.__attrs() == other.__attrs()

    def __ne__(self, other):
        return not self == other

########NEW FILE########
__FILENAME__ = module
import hashlib
import os
from daf_fruit_dist.build.artifact import Artifact
from daf_fruit_dist.build.dependency import Dependency
from daf_fruit_dist.build.id import Id
from daf_fruit_dist.build.build_util import nested_object_from_json_data, \
    get_attr_as_tuple_unless_none, get_attr_as_list_unless_none
from daf_fruit_dist.file_management import get_file_digests


class Module(object):
    def __repr__(self):
        return (
            'Module(id=%r, properties=%r, artifacts=%r, dependencies=%r)' % (
                self._id,
                self._properties,
                self._artifacts,
                self._dependencies))

    def __init__(self, id, properties, artifacts, dependencies):
        super(Module, self).__init__()
        self._id = id
        self._properties = properties
        self._artifacts = artifacts
        self._dependencies = dependencies

    @property
    def id(self):
        return self._id

    @property
    def properties(self):
        return self._properties

    @property
    def artifacts(self):
        return self._artifacts

    @property
    def dependencies(self):
        return self._dependencies

    @classmethod
    def from_json_data(cls, json_data):
        artifacts_tuple = None

        if 'artifacts' in json_data:
            artifacts_tuple = tuple([
                Artifact.from_json_data(x)
                for x in json_data['artifacts']])

        dependencies_tuple = None

        if 'dependencies' in json_data:
            dependencies_tuple = tuple([
                Dependency.from_json_data(x)
                for x in json_data['dependencies']])

        id = nested_object_from_json_data(json_data, 'id', Id.from_json_data)

        return Module(
            id=id,
            properties=json_data['properties'],
            artifacts=artifacts_tuple,
            dependencies=dependencies_tuple)

    @property
    def as_json_data(self):
        json_data = {
            "properties": self.properties,
            "id": getattr(self.id, 'as_json_data', None)
        }

        if self.artifacts is not None:
            json_data["artifacts"] = [x.as_json_data for x in self.artifacts]

        if self.dependencies is not None:
            json_data["dependencies"] = [
                x.as_json_data for x in self.dependencies]

        return json_data

    def __attrs(self):
        frozen_artifacts = None
        if self._artifacts is not None:
            frozen_artifacts = frozenset(self._artifacts)

        frozen_dependencies = None
        if self._dependencies is not None:
            frozen_dependencies = frozenset(self._dependencies)

        return (
            self._id,
            frozenset(self._properties),
            frozen_artifacts,
            frozen_dependencies)

    def __hash__(self):
        return hash(self.__attrs())

    def __eq__(self, other):
        return (
            isinstance(other, Module) and
            self.__attrs() == other.__attrs())

    def __ne__(self, other):
        return not self == other

    class Builder(object):
        def __init__(
                self,
                id=None,
                properties=None,
                artifacts=None,
                dependencies=None,
                treat_none_as_empty=True
        ):
            super(Module.Builder, self).__init__()
            self._id = id
            self._properties = properties
            self._treat_none_as_empty = treat_none_as_empty

            # Artifacts and Dependency objects are effectively
            # immutable. Consequently there isn't really an
            # encapsulation violation if we just assign the collection
            # directly.
            if artifacts is not None:
                self._artifacts = artifacts
            elif treat_none_as_empty:
                self._artifacts = []
            else:
                self._artifacts = None

            if dependencies is not None:
                self._dependencies = dependencies
            elif treat_none_as_empty:
                self._dependencies = []
            else:
                self._dependencies = None

        @property
        def id(self):
            return self._id

        @property
        def dependencies(self):
            return self._dependencies

        @property
        def artifacts(self):
            return self._artifacts

        @id.setter
        def id(self, value):
            self._id = value

        def add_artifact(self, type, name, sha1=None, md5=None):
            artifact = Artifact(type=type, name=name, sha1=sha1, md5=md5)
            self.ensure_artifacts_defined()
            self._artifacts.append(artifact)

        def add_file_as_artifact(self, type, file):
            full_path = os.path.abspath(file)
            name = os.path.basename(full_path)

            md5, sha1 = get_file_digests(
                full_path,
                digests=(hashlib.md5(), hashlib.sha1()))

            artifact = Artifact(
                type=type,
                name=name,
                sha1=sha1.hexdigest(),
                md5=md5.hexdigest())

            self.ensure_artifacts_defined()
            self._artifacts.append(artifact)

        def add_dependency(self, type, id, sha1=None, md5=None):
            dependency = Dependency(type, id, sha1, md5)
            self.ensure_dependencies_defined()
            self._dependencies.append(dependency)

        def ensure_dependencies_defined(self):
            """
            Ensure dependencies are defined even if only an empty collection.
            """

            if self._dependencies is None:
                self._dependencies = []

        def ensure_artifacts_defined(self):
            """
            Ensure artifacts are defined even if only an empty collection.
            """

            if self._artifacts is None:
                self._artifacts = []

        def build(self):
            return Module(
                id=self._id,
                properties=self._properties,
                artifacts=get_attr_as_tuple_unless_none(
                    self, '_artifacts'),
                dependencies=get_attr_as_tuple_unless_none(
                    self, '_dependencies'))

        @classmethod
        def from_another_module(
                cls,
                module,
                treat_none_as_empty=True,
                copy_dependencies=True):

            dependencies = None

            if copy_dependencies:
                dependencies = get_attr_as_list_unless_none(
                    module,
                    'dependencies')

            return Module.Builder(
                id=module.id,
                properties=module.properties,
                artifacts=get_attr_as_list_unless_none(module, 'artifacts'),
                dependencies=dependencies,
                treat_none_as_empty=treat_none_as_empty,
            )

########NEW FILE########
__FILENAME__ = promotion_request
class PromotionRequest(object):
    def __init__(self,
                 status,
                 ci_user,
                 timestamp,
                 target_repo,
                 comment=None,
                 dry_run=False,
                 copy=False,
                 artifacts=True,
                 dependencies=False,
                 scopes=None,
                 properties=None,
                 fail_fast=True):

        """Construct a PromotionRequest data container.

        :param status: new build status (any string, e.g. "staged")
        :param comment: An optional comment describing the reason for
            promotion.
        :param ci_user: The user that invoked promotion from the CI
            server.
        :param timestamp: ISO8601 formated time the promotion command
            was sent to Artifactory.
        :param dry_run: Run without executing any operation in
            Artifactory but get the results to check if the operation
            can succeed.
        :param target_repo: Optional repository to move or copy the
            build's artifacts and/or dependencies
            (e.g.:"libs-release-local")
        :param copy: Whether to copy instead of move, when a target
            repository is specified.
        :param artifacts: Whether to move/copy the build's artifacts.
        :param dependencies: Whether to move/copy the build's
            dependencies.
        :param scopes: An array of dependency scopes to include when
            "dependencies" is true. (e.g.["compile", "runtime"])
        :param properties: A list of properties to attach to the build's
            artifacts (regardless if "target_repo" is used).
        :param fail_fast: Fail and abort the operation upon receiving an
            error.
        """

        super(PromotionRequest, self).__init__()
        self._status = status
        self._comment = comment
        self._ci_user = ci_user
        self._timestamp = timestamp
        self._target_repo = target_repo
        self._dry_run = dry_run
        self._copy = copy
        self._artifacts = artifacts
        self._dependencies = dependencies
        self._scopes = scopes
        self._properties = properties
        self._fail_fast = fail_fast

    @property
    def status(self):
        return self._status

    @property
    def comment(self):
        return self._comment

    @property
    def ci_user(self):
        return self._ci_user

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def target_repo(self):
        return self._target_repo

    @property
    def dry_run(self):
        return self._dry_run

    @property
    def copy(self):
        return self._copy

    @property
    def artifacts(self):
        return self._artifacts

    @property
    def dependencies(self):
        return self._dependencies

    @property
    def scopes(self):
        return self._scopes

    @property
    def properties(self):
        return self._properties

    @property
    def fail_fast(self):
        return self._fail_fast

    @classmethod
    def from_json_data(cls, json_data):
        return PromotionRequest(
            status=json_data['status'],
            comment=json_data['comment'],
            ci_user=json_data['ciUser'],
            timestamp=json_data['timestamp'],
            target_repo=json_data['targetRepo'],
            dry_run=json_data['dryRun'],
            copy=json_data['copy'],
            artifacts=json_data['artifacts'],
            dependencies=json_data['dependencies'],
            scopes=json_data['scopes'],
            properties=json_data['properties']
        )

    @property
    def as_json_data(self):
        json_data = {
            "status": self.status,
            "comment": self.comment,
            "ciUser": self.ci_user,
            "timestamp": self.timestamp,
            "dryRun": self.dry_run,
            "targetRepo": self.target_repo,
            "copy": self.copy,
            "artifacts": self.artifacts,
            "dependencies": self.dependencies,
            "scopes": self.scopes,
            "properties": self.properties,
            "failFast": self.fail_fast,
        }

        return json_data

    def __attrs(self):
        hashable_attributes = (
            self._status,
            self._comment,
            self._ci_user,
            self._timestamp,
            self._target_repo,
            self._dry_run,
            self._copy,
            self._artifacts,
            self._dependencies,
            tuple(self._scopes),
            frozenset(self._properties),
            self._fail_fast)

        return hashable_attributes

    def __hash__(self):
        return hash(self.__attrs())

    def __eq__(self, other):
        return (
            isinstance(other, PromotionRequest) and
            self.__attrs() == other.__attrs())

    def __ne__(self, other):
        return not self == other

########NEW FILE########
__FILENAME__ = build_info_module_generator
import json
import os
import pkg_resources
from build.constants import PYTHON_SDIST, PYTHON_BDIST, PYTHON_EGG
from build.constants import PYTHON_WHEEL, PYTHON_SPHINX, PYTHON_RPM
from build.constants import PYTHON_FREEZE, PYTHON_GROUP_ID
from build.id import Id
from build.module import Module
from file_management import write_to_file


class BuildInfoModuleGenerator(object):
    """
    Incrementally build up a module level meta-data file for later
    inclusion in an Artifactory build-info message.

    Setuptools/distribute commands are provided with an array of tuples
    accessed at self.distribution.dist_files.

    This along with other information in self.distribution provides the
    information necessary to create the artifacts portion of the build-
    info meta-data Artifactory needs. The caveat is only files built by
    commands within the same execution will be available.

    For example:
    prompt>python setup.py sdist bdist_egg my_custom_command
    prompt>python setup.py bdist_rpm my_custom_command

    In the second execution, my_custom_command will have access to a
    tuple like ("bdist_rpm", "2.7", "somepath/dist/pointy-stick-1.2.3.rpm")
    but will have no information about the sdist and bdist_egg files.

    To ensure the collection of a full set of Module information the
    current design simply writes a meta-data file into the dist
    directory. Each execution of the custom command enhances the meta-
    data file to incorporate new information.

    There are surely better ways to achieve a similar goal, but most of
    them involve customizing existing distribute commands or
    introspecting existing binaries in the dist directory.

    Customizing the existing distribute commands would effectively be a
    fork of the distribute code base, and therefore difficult to
    maintain. Even a monkey patch of the distribute commands would
    likely be a bit fragile.

    Similarly introspection turns out to not be sufficiently
    deterministic. The pkg-info in each distribution doesn't make it
    easy to tell the difference between a bdist and an sdist. It is
    possible to make a good guess, but that isn't really ideal.

    Continuous integration/deployment builds are already outside the
    scope of the distribute package. Furthermore, only a build within a
    continuous integration server should typically be able to upload
    artifacts to a build artifact repository such as Artifactory.
    Therefore, ensuring the continuous integration tooling always calls
    a specialized meta-data collecting command, along with any setup
    command producing a published build artifact, isn't all that bad.
    """

    def __init__(self, determine_dependency_checksums_fn):
        """Construct generator instance.

        :param determine_dependency_checksums_fn: Arguments must match
            (artifact_id, version) and must return an MD5, SHA1 tuple
        """
        super(BuildInfoModuleGenerator, self).__init__()

        self.determine_dependency_checksums_fn = (
            determine_dependency_checksums_fn)

        self._command_to_type_dict = {
            'sdist': PYTHON_SDIST,
            'bdist': PYTHON_BDIST,
            'bdist_dumb': PYTHON_BDIST,
            'bdist_egg': PYTHON_EGG,
            'bdist_wheel': PYTHON_WHEEL,
            'bdist_rpm': PYTHON_RPM,
            'build_sphinx': PYTHON_SPHINX,
            'build_sphinx_zip': PYTHON_SPHINX,
            'freeze': PYTHON_FREEZE
        }

    def update(self,
               module_id,
               module_properties,
               freeze_file,
               dist_files,
               module_file,
               force_dependency_rebuild=False,
               force_clean=False):

        module_builder = self._create_module_builder(
            module_id=module_id,
            module_properties=module_properties,
            module_file=module_file,
            ignore_previous_dependencies=force_dependency_rebuild,
            force_clean=force_clean)

        self._append_artifacts(dist_files, module_builder)

        if module_builder.dependencies is None:
            self._reset_dependencies(freeze_file, module_builder)

        module = module_builder.build()
        self._write_module_file(module, module_file)

    def _create_module_builder(
            self,
            module_id,
            module_properties,
            module_file,
            ignore_previous_dependencies,
            force_clean):

        if force_clean or (not os.path.exists(module_file)):
            module_builder = Module.Builder(
                id=module_id,
                properties=module_properties,
                treat_none_as_empty=False
            )
        else:
            with open(module_file, 'r') as f:
                json_string = f.read()

            json_data = json.loads(json_string)
            existing_module = Module.from_json_data(json_data)

            if module_id != existing_module.id:
                msg = (
                    "module id {} read from {} doesn't match specified value "
                    "of {}".format(
                        existing_module.id,
                        module_file,
                        module_id))
                raise ValueError(msg)

            module_builder = Module.Builder.from_another_module(
                module=existing_module,
                treat_none_as_empty=False,
                copy_dependencies=not ignore_previous_dependencies
            )

        return module_builder

    def _write_module_file(self, module, module_file):
        json_data = module.as_json_data
        json_string = json.dumps(json_data, sort_keys=True, indent=4)
        write_to_file(file_path=module_file, to_write=json_string)

    def _determine_type_from_command_name(self, command_name):
        lc_command_name = command_name.lower()
        if lc_command_name in self._command_to_type_dict:
            artifact_type = self._command_to_type_dict[lc_command_name]
        else:
            raise ValueError(
                "unrecognized artifact command: {}".format(command_name))

        return artifact_type

    def _append_artifacts(self, dist_files, module_builder):
        for cmd, py_version, artifact in dist_files:
            artifact_type = self._determine_type_from_command_name(cmd)
            module_builder.add_file_as_artifact(
                type=artifact_type, file=artifact)

    def _reset_dependencies(self, freeze_file, module_builder):
        requirements = self._parse_req_file(requirement_file=freeze_file)

        module_builder.ensure_dependencies_defined()
        for req in requirements:
            # There are two options for the artifact ID: req.key and
            # req.project_name. The req.key option is all lowercase,
            # while the req.project_name option respects the case of the
            # project. Since Artifactory has trouble locating build
            # dependencies when all lowercase names are specified,
            # req.project_name appears to be a better option here.
            artifact_id = req.project_name

            assignment, version = req.specs[0]

            dependency_id = Id(
                group_id=PYTHON_GROUP_ID,
                artifact_id=artifact_id,
                version=version)

            dependency_md5, dependency_sha1 = (
                self.determine_dependency_checksums_fn(artifact_id, version))

            module_builder.add_dependency(
                type=None,
                id=dependency_id,
                sha1=dependency_sha1,
                md5=dependency_md5)

    def _parse_req_file(self, requirement_file):
        requirements = []

        with open(requirement_file, 'r') as req_f:
            for line in req_f:
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    requirements.append(
                        pkg_resources.Requirement.parse(stripped))

        return requirements

########NEW FILE########
__FILENAME__ = build_info_utils
from collections import namedtuple
from functools import partial
from daf_fruit_dist.artifactory import artifactory_rest, repo_detail
from daf_fruit_dist.build.agent import Agent
from daf_fruit_dist.build.build_info import BuildInfo
from daf_fruit_dist.build.build_retention import BuildRetention
from daf_fruit_dist.build.module import Module
from daf_fruit_dist.iso_time import ISOTime
import json
import os


EnvInfo = namedtuple(
    'EnvInfo', [
        'build_name',
        'build_number',
        'build_agent_name',
        'build_agent_version',
        'build_version'])


def collect_env_info():
    env_errors = []
    check_environ = partial(_get_environ, error_fn=env_errors.append)

    major_version = check_environ('MAJOR_VERSION')
    minor_version = check_environ('MINOR_VERSION')
    build_number = check_environ('BUILD_NUMBER')
    build_name = check_environ(('BUILD_NAME', 'TEAMCITY_BUILDCONF_NAME'))

    if env_errors:
        msg = os.linesep.join(
            ['The following environment variables should be set but are not:']
            + map(lambda vars_tried: (
                '    => ' + ' or '.join(map(repr, vars_tried))), env_errors))
        raise RuntimeError(msg)

    build_number = int(build_number)
    build_agent_name = _get_environ(
        'BUILD_AGENT_NAME', default='TeamCity')
    build_agent_version = _get_environ(
        ('BUILD_AGENT_VERSION', 'TEAMCITY_VERSION'))
    build_version = '{}.{}.{}'.format(
        major_version, minor_version, build_number)

    return EnvInfo(
        build_name=build_name,
        build_number=build_number,
        build_agent_name=build_agent_name,
        build_agent_version=build_agent_version,
        build_version=build_version)


def merge_module_info_files(build_info_files, env_info):
    if env_info.build_agent_name and env_info.build_agent_version:
        build_agent = Agent(
            name=env_info.build_agent_name,
            version=env_info.build_agent_version)
    else:
        build_agent = None

    bi_builder = BuildInfo.Builder(
        version=env_info.build_version,
        name=env_info.build_name,
        number=env_info.build_number,
        type='GENERIC',
        started=ISOTime.now().as_str,
        build_agent=build_agent,
        artifactory_principal="admin",
        agent=Agent(name="defend_against_fruit", version="5.2"),
        build_retention=BuildRetention(
            count=-1,
            delete_build_artifacts=False))

    if build_info_files:
        for build_info_file in build_info_files:
            with open(build_info_file, 'r') as f:
                bi_builder.add_module(Module.from_json_data(
                    json.loads(f.read())))

    return bi_builder.build()


def get_deploy_artifact_function(
        repo_details,
        env_info=None,
        verify_cert=True):

    # Create a short-hand version of the deploy function with the just
    # the repo details filled out.
    if env_info is None:
        attributes = None
    else:
        attributes = {
            'build.name': env_info.build_name,
            'build.number': env_info.build_number}

    return partial(
        artifactory_rest.deploy_globbed_files,
        repo_base_url=repo_details.repo_base_url,
        repo_push_id=repo_details.repo_push_id,
        username=repo_details.username,
        password=repo_details.password,
        attributes=attributes,
        verify_cert=verify_cert)


def get_deploy_build_info_function(repo_details, verify_cert=True):
    return partial(
        artifactory_rest.publish_build_info,
        repo_base_url=repo_details.repo_base_url,
        username=repo_details.username,
        password=repo_details.password,
        verify_cert=verify_cert)


def get_deploy_functions(env_info=None, verify_cert=True):
    repo_details = repo_detail.read_options()

    return (
        get_deploy_artifact_function(
            repo_details, env_info=env_info, verify_cert=verify_cert),

        get_deploy_build_info_function(
            repo_details, verify_cert=verify_cert))


def build_info_to_text(build_info):
    return json.dumps(build_info.as_json_data, sort_keys=True, indent=4)


def _get_environ(order, default=None, error_fn=None):
    if isinstance(order, basestring):
        order = (order,)
    for o in order:
        try:
            return os.environ[o]
        except KeyError:
            pass
    if error_fn:
        error_fn(order)
    return default

########NEW FILE########
__FILENAME__ = checksums
from collections import namedtuple

Checksums = namedtuple("Checksums", ["sha1", "md5"])

########NEW FILE########
__FILENAME__ = checksum_dependency_helper
from pip.exceptions import DistributionNotFound


class ChecksumDependencyHelper(object):
    def __init__(
            self,
            determine_file_path_fn,
            determine_checksums_from_file_path_fn):

        """Construct checksum dependency helper instance.

        :param determine_file_path_fn: arguments must match
            (pkg_name=artifact_id, pkg_version=version) and must return
            the file path portion used in downloading the matching
            module.

        :param determine_checksums_from_file_path_fn: function taking a
            file_path and returning the Checksum named-tuple
        """
        self.determine_file_path_fn = determine_file_path_fn
        self.determine_checksums_from_file_path_fn = (
            determine_checksums_from_file_path_fn)

    def __call__(self, artifact_id, version):
        try:
            #determine_file_path_fn may throw a DistributionNotFound exception
            dependency_path = self.determine_file_path_fn(
                pkg_name=artifact_id,
                pkg_version=version)

            # determine_checksums_from_file_path_fn may throw an
            # RequestException but if so just let it bubble up.
            dependency_checksums = self.determine_checksums_from_file_path_fn(
                dependency_path)
            dependency_sha1 = dependency_checksums.sha1
            dependency_md5 = dependency_checksums.md5

        except DistributionNotFound:
            dependency_sha1 = None
            dependency_md5 = None

        return dependency_md5, dependency_sha1

########NEW FILE########
__FILENAME__ = ci_multi_module_utils
import logging
import os
from file_management import DirectoryContextManager
from file_management import compute_repo_path_from_module_name
from file_management import get_submodule_info
from exec_utils import run_ci_script
from daf_fruit_dist.build_info_utils import merge_module_info_files
from daf_fruit_dist.build_info_utils import build_info_to_text
from daf_fruit_dist.build_info_utils import get_deploy_functions


def execute_submodule_run(submodule_order):
    # Run the CI scripts in all sub-modules.
    for module in submodule_order:
        with DirectoryContextManager(module):
            logging.info('cwd: ' + os.getcwd())
            run_ci_script()


def _collect_build_info(submodule_order, env_info):
    module_info_files = filter(None, map(get_submodule_info, submodule_order))
    merged = merge_module_info_files(module_info_files, env_info)
    return merged


def deploy_all_modules(module_order, env_info, verify_cert=True):
    build_info = _collect_build_info(module_order, env_info)

    logging.debug(os.linesep.join((
        'Build info:',
        build_info_to_text(build_info))))

    deploy_artifact, deploy_build_info = get_deploy_functions(
        env_info=env_info,
        verify_cert=verify_cert)

    def deploy_dist(module):
        path = compute_repo_path_from_module_name(module)
        return deploy_artifact(
            path=path,
            glob_patterns=[os.path.join(module, 'dist', '*')])

    deployed_files = []

    for module in module_order:
        deployed_files.extend(deploy_dist(module))

    deploy_build_info(build_info=build_info)

    return deployed_files

########NEW FILE########
__FILENAME__ = ci_single_module_utils
import logging
import os
import shutil
from file_management import ensure_path_exists, split_ext, rm
from file_management import get_submodule_info
from file_management import compute_repo_path_from_module_name
from file_management import MODULE_INFO_DIR
from exec_utils import run_nosetests, install_dev, build_sdist
from build_info_utils import merge_module_info_files, build_info_to_text
from build_info_utils import get_deploy_functions
from version_utils import VersionUtils


def standard_py_run(script):
    _execute_py_run(script)


def standard_develop_run():
    _execute_develop_run()


def execute_sdist_run():
    # Clean!
    _standard_clean()

    # Create the version.txt file.
    VersionUtils().write_version()

    # Run unit tests.
    run_nosetests()

    # Create sdist .tar.gz archive.
    build_sdist()


def _extract_single_module_from_build_info(build_info):
    if len(build_info.modules) != 1:
        raise RuntimeError(
            "One and only one module is expected in the build info of a "
            "single module build.")

    return build_info.modules[0]


def deploy_module(env_info, verify_cert=True):
    module_info_file = get_submodule_info(module_dir=".")

    build_info = merge_module_info_files(
        build_info_files=(module_info_file,),
        env_info=env_info)

    logging.debug(os.linesep.join(
        ('Build info:', build_info_to_text(build_info))))

    deploy_artifact, deploy_build_info = get_deploy_functions(
        env_info=env_info,
        verify_cert=verify_cert)

    module_info = _extract_single_module_from_build_info(build_info)
    path = compute_repo_path_from_module_name(module_info.id.artifact_id)

    deployed_files = [
        deploy_artifact(path=path, glob_patterns=[os.path.join('dist', '*')])]

    deploy_build_info(build_info=build_info)

    return deployed_files


def _execute_py_run(script):
    # Clean!
    _standard_clean()

    # Create the version.txt file.
    version = VersionUtils().write_version()

    # To "build" the script, simply copy it into the 'dist' directory
    # and tag it with the version.
    destination = _built_script_destination(script, version)
    ensure_path_exists(os.path.dirname(destination))
    shutil.copy2(script, destination)


def _execute_develop_run():
    # Clean!
    _standard_clean()

    # Create the version.txt file.
    VersionUtils().write_version()

    # Run unit tests.
    run_nosetests()

    # Install a link from site-packages back to this package.
    install_dev()


def _standard_clean():
    rm(MODULE_INFO_DIR, 'dist', '*.egg-info', '*.egg', 'version.txt')


def _built_script_destination(script, version):
    base, ext = split_ext(script)
    build_filename = '{base}-{version}.{ext}'.format(
        base=base,
        version=version,
        ext=ext)
    return os.path.join('dist', build_filename)

########NEW FILE########
__FILENAME__ = ci_utils
import argparse
import sys
from ci_multi_module_utils import execute_submodule_run, deploy_all_modules
from daf_fruit_dist.build_info_utils import collect_env_info
from daf_fruit_dist.ci_single_module_utils import execute_sdist_run
from daf_fruit_dist.ci_single_module_utils import deploy_module


def standard_sdist_run(submodule_order=None, integration_tests_fn=None):
    args = _parse_args(sys.argv[1:])

    env_info = collect_env_info() if args.publish else None
    verify_cert = not args.no_cert_verify

    if submodule_order:
        execute_submodule_run(submodule_order)

        if not args.skip_int_tests and integration_tests_fn:
            integration_tests_fn()

        if args.publish:
            deploy_all_modules(
                module_order=submodule_order,
                env_info=env_info,
                verify_cert=verify_cert)
    else:
        execute_sdist_run()

        if not args.skip_int_tests and integration_tests_fn:
            integration_tests_fn()

        if args.publish:
            deploy_module(env_info=env_info, verify_cert=verify_cert)


def _parse_args(args=None):
    parser = argparse.ArgumentParser(
        description='Continuous integration utility responsible for invoking '
                    'the build system within a virtual environment')

    parser.add_argument(
        '--publish',
        action='store_true',
        help='Publish to build artifact repository.')

    parser.add_argument(
        '--no-cert-verify',
        action='store_false',
        help='Do not verify authenticity of host cert when using SSL.')

    parser.add_argument(
        '--skip-int-tests',
        action='store_true',
        help='Skip all integration tests.')

    return parser.parse_args(args)

########NEW FILE########
__FILENAME__ = artifactory_upload
from distutils.errors import DistutilsOptionError
from distutils import log
from functools import partial
from setuptools import Command
from daf_fruit_dist.artifactory import artifactory_rest
from daf_fruit_dist.artifactory import repo_detail
from daf_fruit_dist.file_management import compute_repo_path_from_module_name


class artifactory_upload(Command):
    description = (
        'upload package to an Artifactory server in the simple PyPI layout')

    user_options = [
        ('repo-base-url=', None,
         'base URL of repository'),
        ('repo-push-id=', None,
         'repository to which build artifacts should be deployed (e.g. '
         'pypi-teamfruit-l-local)'),
        ('repo-user=', None,
         'username for the repository (HTTP basic auth)'),
        ('repo-pass=', None,
         'password for the repository (HTTP basic auth)'),
        ('no-cert-verify', None,
         'do not verify authenticity of host cert when using SSL')]

    boolean_options = [
        'no-cert-verify',
    ]

    def initialize_options(self):
        self.repo_base_url = ''
        self.repo_push_id = ''
        self.repo_user = ''
        self.repo_pass = ''
        self.no_cert_verify = 0
        self.resource = None

    def _check_repo_details(self, repo_details):
        if not repo_details.repo_base_url:
            raise DistutilsOptionError('No repository specified!')
        if not repo_details.repo_push_id:
            raise DistutilsOptionError('No repo_push_id specified!')
        if not repo_details.username:
            raise DistutilsOptionError('No repo username specified!')
        if not repo_details.password:
            raise DistutilsOptionError('No repo password specified!')

    def finalize_options(self):
        repo_details = repo_detail.read_options(
            repo_base_url=self.repo_base_url,
            repo_push_id=self.repo_push_id,
            username=self.repo_user,
            password=self.repo_pass)

        self.announce(
            'Repository details: '
            'repo_base_url="{}", '
            'repo_push_id="{}" '
            'username="{}"'.format(
                repo_details.repo_base_url,
                repo_details.repo_push_id,
                repo_details.username),
            level=log.INFO
        )

        self._check_repo_details(repo_details)

        verify_cert = not self.no_cert_verify

        path = compute_repo_path_from_module_name(
            self.distribution.metadata.name)

        self.upload = partial(
            self.__upload,
            repo_base_url=repo_details.repo_base_url,
            repo_push_id=repo_details.repo_push_id,
            path=path,
            username=repo_details.username,
            password=repo_details.password,
            verify_cert=verify_cert)

    def run(self):
        if not self.distribution.dist_files:
            raise DistutilsOptionError(
                'No dist file created in earlier command')

        for dist, python_version, filename in self.distribution.dist_files:
            self.upload(filename=filename)

    def __upload(
            self,
            filename,
            repo_base_url,
            repo_push_id,
            path,
            username=None,
            password=None,
            verify_cert=True):

        self.announce('Uploading: {}/{}/{}/{}'.format(
            repo_base_url, repo_push_id, path, filename),
            level=log.INFO)

        return artifactory_rest.deploy_file(
            filename=filename,
            repo_base_url=repo_base_url,
            repo_push_id=repo_push_id,
            path=path,
            username=username,
            password=password,
            verify_cert=verify_cert)

########NEW FILE########
__FILENAME__ = freeze
import glob
import os
import subprocess
from setuptools import Command
from daf_fruit_dist.file_management import \
    compute_requirements_filename_full_path


class freeze(Command):
    description = (
        'list all packages in the current environment in requirements.txt '
        'format')

    # This must be specified even though there are no user options.
    user_options = []

    # This must exist even though it does nothing.
    def initialize_options(self):
        pass

    # This must exist even though it does nothing.
    def finalize_options(self):
        pass

    def __pip_freeze(self, output_file):
        """
        Perform a 'pip freeze' and write the output (along with a
        comment) to the specified file.
        """
        with open(output_file, 'w') as f:
            f.write('# From: pip freeze' + os.linesep)
            # Absent this flush, the "pip freeze" contents appears
            # *before* the above comment.
            f.flush()
            subprocess.call(['pip', 'freeze'], stdout=f)

    def __freeze_eggs(self, output_file):
        """
        For every egg directory in the current working directory, append
        the egg's name and version to the specified output file.
        """
        for path in glob.glob('*.egg'):
            # Read the metadata from the egg into a string.
            with open(os.path.join(path, 'EGG-INFO', 'PKG-INFO')) as f:
                pkg_info = f.read()

            # Grab just the name and version from the metadata and store
            # them into a dictionary.
            metadata = dict(
                n.split(': ', 1) for
                n in pkg_info.splitlines() if
                n.startswith(('Name', 'Version')))

            # Append the egg's name and version (along with a comment)
            # to the output_file.
            with open(output_file, 'a') as f:
                f.write(
                    '{br}'
                    '# From: ./{egg_dir}{br}'
                    '{name}=={version}{br}'.format(
                        egg_dir=path,
                        name=metadata['Name'],
                        version=metadata['Version'],
                        br=os.linesep))

    def run(self):
        output_file = compute_requirements_filename_full_path(
            artifact_id=self.distribution.metadata.name,
            version=self.distribution.metadata.version)

        # 1. Perform a 'pip freeze' and write to output file. The
        #    captured packages are in site-packages.
        self.__pip_freeze(output_file)

        # 2. Append all eggs in the current directory to the output
        #    file. These packages do not appear in site-packages and are
        #    not caught by 'pip freeze' in the previous step. However,
        #    they are still part of the environment and should be listed.
        self.__freeze_eggs(output_file)

        # TODO: Capture packages in os.environ['PYTHONPATH']?

        # 3. Add output file to self.distribution.dist_files list.
        self.distribution.dist_files.append((
            'freeze',  # Distribution is the same as the command name
            None,  # No specific Python version
            output_file))   # Output filename

########NEW FILE########
__FILENAME__ = module_generator_command
from distutils import log
from setuptools import Command

from daf_fruit_dist.artifactory import artifactory_rest
from daf_fruit_dist.artifactory.repo_detail import read_options
from daf_fruit_dist.checksum_dependency_helper import ChecksumDependencyHelper
from daf_fruit_dist.pip_package_path_finder import PipPackagePathFinder
from daf_fruit_dist.build.constants import PYTHON_GROUP_ID
from daf_fruit_dist.build.id import Id
from daf_fruit_dist.build_info_module_generator import BuildInfoModuleGenerator
from daf_fruit_dist.file_management import \
    compute_requirements_filename_full_path, \
    compute_module_info_filename_full_path


class ModuleGeneratorCommand(Command):
    """
    Command for generating Artifactory module meta-data files for use in
    ``setup.py`` scripts.
    """

    # Description shown in setup.py --help-commands
    description = (
        'Build model portion of Artifactory build-info and save as json file '
        'in dist directory')

    # Options available for this command, tuples of ('longoption',
    # 'shortoption', 'help'). If the longoption name ends in a `=` it
    # takes an argument.
    user_options = [
        ('force-dependency-rebuild', None,
         'rebuild dependency meta-data information'),
        ('force-clean', None,
         'rebuild all meta-data information'),
        ('no-cert-verify', None,
         'do not verify authenticity of host cert when using SSL')]

    # Options that don't take arguments, simple true or false options.
    # These *must* be included in user_options too, but without an
    # equals sign.
    boolean_options = [
        'force-dependency-rebuild',
        'force-clean',
        'no-cert-verify']

    def initialize_options(self):
        # Set a default for each of your user_options (long option name)
        self.force_dependency_rebuild = 0
        self.force_clean = 0
        self.no_cert_verify = 0

    def finalize_options(self):
        # verify the arguments and raise DistutilOptionError if needed
        pass

    def _determine_module_id(self):
        return Id(
            group_id=PYTHON_GROUP_ID,
            artifact_id=self.distribution.metadata.name,
            version=self.distribution.metadata.version)

    def run(self):
        module_id = self._determine_module_id()
        self.announce(
            'Creating module_info file for module: {}'.format(module_id),
            level=log.INFO
        )

        # This command is never used interactively, so it doesn't make
        # sense to add support for passing in repo details like the
        # artifactory_upload command does. If that changes in the future
        # this command can always be enhanced at that time. The work
        # involved to add the options isn't so much in the code changes
        # to this command as in the test coverage that would need to be
        # written. It would also probably require refactoring the
        # commands to share a common base class. All this currently
        # falls under YAGNI (You're Not Going To Need It).

        verify_cert = not self.no_cert_verify
        repo_details = read_options()

        pip_package_path_finder = PipPackagePathFinder()

        def determine_checksums(file_path):
            return artifactory_rest.determine_checksums(
                username=repo_details.username,
                password=repo_details.password,
                repo_pull_id=repo_details.repo_pull_id,
                repo_base_url=repo_details.repo_base_url,
                file_path=file_path,
                verify_cert=verify_cert)

        checksum_dependency_helper = ChecksumDependencyHelper(
            determine_file_path_fn=pip_package_path_finder.determine_file_path,
            determine_checksums_from_file_path_fn=determine_checksums)

        build_info_module_generator = BuildInfoModuleGenerator(
            determine_dependency_checksums_fn=checksum_dependency_helper)

        requirements_file = compute_requirements_filename_full_path(
            artifact_id=module_id.artifact_id,
            version=module_id.version)

        module_info_file = compute_module_info_filename_full_path(
            artifact_id=module_id.artifact_id,
            version=module_id.version)

        build_info_module_generator.update(
            module_id=module_id,
            module_properties={},
            freeze_file=requirements_file,
            dist_files=self.distribution.dist_files,
            module_file=module_info_file,
            force_dependency_rebuild=bool(self.force_dependency_rebuild),
            force_clean=bool(self.force_clean))

        self.announce(
            'Module info file created at: {}'.format(module_info_file),
            level=log.INFO)

########NEW FILE########
__FILENAME__ = exec_utils
import glob
import os
import subprocess
import sys


def build_sdist():
    subprocess.check_call([
        sys.executable,
        'setup.py',
        'sdist',
        '--formats=gztar',
        'freeze',
        'module_generator'])


def build_and_deploy_sdist():
    subprocess.check_call([
        sys.executable,
        'setup.py',
        'sdist',
        '--formats=gztar',
        'freeze',
        'module_generator',
        'artifactory_upload'])


def install_dev():
    subprocess.check_call([
        sys.executable, 'setup.py', 'sdist', '--formats=gztar'])
    sdist = glob.glob(os.path.join('dist', '*.tar.gz'))[0]
    subprocess.check_call(['pip', 'install', sdist])


def run_nosetests():
    subprocess.check_call([sys.executable, 'setup.py', 'nosetests'])


def run_ci_script():
    subprocess.check_call([sys.executable, 'continuous_integration.py'])

########NEW FILE########
__FILENAME__ = file_management
import glob
import os
import shutil
from build.constants import PYTHON_GROUP_ID


MODULE_INFO_DIR = 'module-info'


class DirectoryContextManager(object):
    def __init__(self, new_cwd):
        self.__new_cwd = new_cwd

    def __enter__(self):
        self.__old_cwd = os.getcwd()
        os.chdir(self.__new_cwd)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.__old_cwd)


def ensure_path_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)


def split_ext(filename):
    """
    Example usage:
    > _split_ext('script.py')
    ('script', 'py')
    """
    split = filename.split('.')
    return '.'.join(split[:-1]), split[-1]


def rm(*glob_patterns):
    for pattern in glob_patterns:
        for path in glob.glob(pattern):
            if os.path.exists(path):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)


def compute_module_info_filename(artifact_id, module_version):
    output_filename = '{}-{}-module-info.json'.format(
        artifact_id,
        module_version)
    return output_filename


def compute_module_info_filename_full_path(
        artifact_id,
        version,
        module_info_dir=MODULE_INFO_DIR):
    filename = compute_module_info_filename(artifact_id, version)
    relative_path = os.path.join(module_info_dir, filename)
    return os.path.abspath(relative_path)


def compute_requirements_filename(artifact_id, module_version):
    output_filename = '{}-{}-requirements.txt'.format(
        artifact_id,
        module_version)
    return output_filename


def compute_requirements_filename_full_path(
        artifact_id,
        version,
        dist_dir='dist'):
    filename = compute_requirements_filename(artifact_id, version)
    relative_path = os.path.join(dist_dir, filename)
    return os.path.abspath(relative_path)


def compute_repo_path_from_module_name(module):
    return '{}/{}'.format(PYTHON_GROUP_ID, module)


def get_submodule_info(module_dir, module_info_dir=MODULE_INFO_DIR):
    """Find json module info file for the specified module directory.

    :param module_dir: directory of module or submodule being searched
    :param module_info_dir: sub-directory within module directory in
        which to search
    """

    def _one_json_file(files):
        """
        There should not be more than one JSON file per module. If there
        is, this method raises an error.
        """
        assert len(files) <= 1, \
            'Submodules should have a maximum of one module-info JSON ' \
            'file each.'

        return files[0] if files else None

    def _glob_submodule_info(module_dir, module_info_dir):
        json_pattern = os.path.join(
            module_dir,
            module_info_dir,
            '*-module-info.json')
        return glob.glob(json_pattern)

    return _one_json_file(_glob_submodule_info(
        module_dir=module_dir,
        module_info_dir=module_info_dir))


def get_file_digests(filename, digests, block_size=2 ** 20):
    """
    Calculate hashes of the given file. 'digests' should be an iterable
    container of hashlib-compatible objects.

    Example usage:
    > md5, sha1 = get_file_digests(
        'archive.tar.gz',
        digests=(hashlib.md5(), hashlib.sha1()))
    > md5.hexdigest()
    'b488a911018964989d158a34c47709d4'
    > sha1.hexdigest()
    'e4ba5c0279368c131799e01c774b49ded12fc331'
    """
    with open(filename, 'rb') as f:
        while True:
            data = f.read(block_size)
            if not data:
                break
            for d in digests:
                d.update(data)
    return digests


def write_to_file(file_path, to_write, write_mode='w'):
    """
    Write the given data into the file at the given path. If the path
    does not exist, it is created.
    """
    dirname = os.path.dirname(os.path.abspath(file_path))

    if dirname:
        ensure_path_exists(dirname)

    with open(file_path, write_mode) as f:
        f.write(to_write)

########NEW FILE########
__FILENAME__ = integration_test_tool
import argparse
from collections import namedtuple
import json
import logging
import os
import sys
import textwrap
from daf_fruit_dist.artifactory.artifactory_rest import publish_build_info
from daf_fruit_dist.artifactory.artifactory_rest import build_promote
from daf_fruit_dist.build.agent import Agent
from daf_fruit_dist.build.build_info import BuildInfo
from daf_fruit_dist.build.build_retention import BuildRetention
from daf_fruit_dist.build.constants import PYTHON_SDIST, PYTHON_FREEZE
from daf_fruit_dist.build.id import Id
from daf_fruit_dist.build.module import Module
from daf_fruit_dist.build.promotion_request import PromotionRequest
from daf_fruit_dist.build_info_utils import build_info_to_text


_OPTION_NAMES = {
    'base_url': 'PYPI_SERVER_BASE',
    'username': 'PYPI_PUSH_USERNAME',
    'password': 'PYPI_PUSH_PASSWORD'}


def execute():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s')

    args = _parse_args()
    sub_command_function = args.func
    sub_command_function(args)


EnvTemplateValues = namedtuple('EnvTemplateValues', _OPTION_NAMES.keys())


def _read_environment_for_defaults():
    env_values = {}

    for opt, env in _OPTION_NAMES.iteritems():
        env_values[opt] = os.environ.get(env, None)

    return EnvTemplateValues(**env_values)


def _parse_and_validate(parser, command_line_args):
    env_template_values = _read_environment_for_defaults()

    parsed_args = parser.parse_args(command_line_args)

    def handle_arg(key_name):
        opt_value = getattr(parsed_args, key_name, None)
        if not opt_value:
            opt_value = getattr(env_template_values, key_name, None)

        if not opt_value:
            msg = (
                "Error: {key_name} value must be provided.\n\n"
                "This can be done using the relevant command line argument\n"
                "or the corresponding environment variable: "
                "{env_name}\n\n{usage}".format(
                    key_name=key_name,
                    env_name=_OPTION_NAMES[key_name],
                    usage=parser.format_usage()))
            print msg
            sys.exit(1)

        setattr(parsed_args, key_name, opt_value)

    for key_name in _OPTION_NAMES:
        handle_arg(key_name=key_name)

    return parsed_args


def _parse_args(args=None):
    parser = argparse.ArgumentParser(
        description=(
            'Integration test utility for testing Artifactory Rest API '
            'calls.'),
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.epilog = textwrap.dedent('''
            To see options for a subcommand:
                > python {} <subcommand> --help'''.format(parser.prog))

    parser.add_argument(
        '--username',
        help='Artifactory username')

    parser.add_argument(
        '--password',
        help='Artifactory password')

    parser.add_argument(
        '--base-url',
        help='Artifactory base URL')

    parser.add_argument(
        '--ignore-cert-errors',
        action='store_true',
        default=False,
        help='Verify certificate')

    subparsers = parser.add_subparsers(
        title="subcommands",
        description="Various subcommands for testing")

    parser_build_info = subparsers.add_parser('build-info')

    parser_build_info.add_argument(
        '--name',
        action='store',
        required=True,
        help="name to use in build-info")

    parser_build_info.add_argument(
        '--number',
        action='store',
        required=True,
        help="build number to use in build-info")

    parser_build_info.set_defaults(func=_build_info)

    #build_name, build_number
    parser_build_info = subparsers.add_parser('build-promote')

    parser_build_info.add_argument(
        '--name',
        action='store',
        required=True,
        help="build name to promote")

    parser_build_info.add_argument(
        '--number',
        action='store',
        required=True,
        help="build number to promote")

    parser_build_info.set_defaults(func=_build_promote)

    return _parse_and_validate(parser=parser, command_line_args=args)


def _build_promote(args):
    my_build_number = args.number
    my_build_name = args.name

    promotion_request = PromotionRequest(
        status="monkey",
        comment="promoted using integration test tool",
        ci_user="builder",
        timestamp="2013-03-21T11:30:06.143-0500",
        dry_run=False,
        target_repo="pypi-teamfruit-2-local",
        properties={
            "components": ["c1", "c3", "c14"],
            "release-name": ["fb3-ga"]}
    )
    promotion_request_as_text = json.dumps(
        promotion_request.as_json_data,
        sort_keys=True,
        indent=4)

    logging.debug(promotion_request_as_text)

    promotion_response_json = build_promote(
        username=args.username,
        password=args.password,
        repo_base_url=args.base_url,
        build_name=my_build_name,
        build_number=my_build_number,
        promotion_request=promotion_request,
        verify_cert=not args.ignore_cert_errors
    )

    print "Promotion Response {}".format(promotion_response_json)


def _build_info(args):
    my_build_number = args.number
    my_build_name = args.name

    bi_builder = BuildInfo.Builder(
        version="2.2.2",
        name=my_build_name,
        number=my_build_number,
        # Looks like valid values are "GENERIC", "MAVEN", "ANT", "IVY" and
        # "GRADLE".
        type='GENERIC',
        # Looks like time format is very specific
        started="2013-03-21T10:49:01.143-0500",
        duration_millis=10000,
        artifactory_principal="dude",
        agent=Agent(name="defend_against_fruit", version="5.2"),
        build_agent=Agent(name="TeamCity", version="1.3"),
        build_retention=BuildRetention(
            count=-1,
            delete_build_artifacts=False,
            # Is this for TeamCity "pinned" builds?
            build_numbers_not_to_be_discarded=[111, 999])
    )
    module_builder = Module.Builder(id=Id(
        group_id="python",
        artifact_id="daf_fruit_dist",
        version="1.2.15"))
    module_builder.add_artifact(
        type=PYTHON_SDIST,
        name="daf_fruit_dist-1.2.15.tar.gz",
        sha1="0a66f5619bcce7a441740e154cd97bad04189d86",
        md5="2a17acbb714e7b696c58b4ca6e07c611")
    module_builder.add_artifact(
        type=PYTHON_FREEZE,
        name="daf_fruit_dist-1.2.15-requirements.txt",
        sha1="06e5f0080b6b15704be9d78e801813d802a90625",
        md5="254c0e43bbf5979f8b34ff0428ed6931"
    )
    module_builder.add_dependency(
        type=PYTHON_SDIST,
        id=Id(group_id="python", artifact_id="nose", version="1.2.1"),
        sha1="02cc3ffdd7a1ce92cbee388c4a9e939a79f66ba5",
        md5="735e3f1ce8b07e70ee1b742a8a53585a")

    bi_builder.add_module(module_builder.build())
    build_info = bi_builder.build()
    logging.debug(build_info_to_text(build_info))

    publish_build_info(
        username=args.username,
        password=args.password,
        repo_base_url=args.base_url,
        build_info=build_info,
        verify_cert=not args.ignore_cert_errors
    )


if __name__ == "__main__":
    execute()

########NEW FILE########
__FILENAME__ = iso_time
from datetime import datetime
import time


class ISOTime(object):
    def __init__(self, date, gmt_offset):
        self.__date = date
        self.__gmt_offset = gmt_offset

    @classmethod
    def now(cls, now_fn=datetime.now, time=time):
        gmt_offset = time.altzone if time.daylight else time.timezone
        return cls(date=now_fn(), gmt_offset=gmt_offset)

    @property
    def as_str(self):
        return (
            self.__date.isoformat()[:-3] +
            '{:+05}'.format(self.__gmt_offset / -36))

########NEW FILE########
__FILENAME__ = pip_package_path_finder
from functools import partial
from pip.baseparser import ConfigOptionParser
from pip.exceptions import DistributionNotFound
from pip.index import PackageFinder
from pip.req import InstallRequirement
from daf_fruit_dist.build.constants import PYTHON_GROUP_ID
from daf_fruit_dist.url_utils import subtract_index_url


class PipPackagePathFinder(object):
    """
    Performs the PIP related aspects of determining a module path within
    Artifactory.
    """

    def __init__(self):
        self.pip_index_url = PipPackagePathFinder._get_pip_index_url()

        package_finder = PackageFinder(
            find_links=[],
            index_urls=[self.pip_index_url],
            use_mirrors=False,
            mirrors=[])

        self.finder = partial(_requirement_finder, finder=package_finder)

    @staticmethod
    def _get_pip_index_url():
        pip_config_parser = ConfigOptionParser(name='daf_fruit_dist')
        try:
            return dict(
                pip_config_parser.get_config_section('global'))['index-url']

        except KeyError:
            raise KeyError(
                'The "index-url" option was not specified under the [global] '
                'section within any of the following files: {}'.format(
                    pip_config_parser.get_config_files()))

    def _determine_pip_tail(self, pkg_name, pkg_version):
        """This stuff is only coming from pip.ini."""
        req_str = '{}=={}'.format(pkg_name, pkg_version)
        link = self.finder(req_str=req_str)

        pip_tail = subtract_index_url(
            index_url=self.pip_index_url,
            pkg_url=link.url_without_fragment)

        return pip_tail

    def determine_file_path(self, pkg_name, pkg_version):
        """
        Determines path portion of python module URL used by PIP to
        download module earlier.

        This method uses the PIP tooling to determine the download URL
        which corresponds to a given python package name and version.
        """
        pip_tail = self._determine_pip_tail(pkg_name, pkg_version)

        file_path = '{python_group_id}/{artifact_path}'.format(
            python_group_id=PYTHON_GROUP_ID,
            artifact_path=pip_tail)

        return file_path


def _get_package_name_alternatives(req_str):
    yield req_str
    yield req_str.replace('-', '_')
    yield req_str.replace('_', '-')


def _requirement_finder(finder, req_str):
    """
    First try to find the given requirement. If that fails, try several
    alternatives. If they all fail, raise the first exception caught.
    """
    err = None

    for req_name in _get_package_name_alternatives(req_str):
        req = InstallRequirement(req=req_name, comes_from=None)
        try:
            return finder.find_requirement(req=req, upgrade=True)
        except DistributionNotFound as e:
            if err is None:
                err = e
    raise err

########NEW FILE########
__FILENAME__ = artifactory_rest_tests
from nose.tools import eq_, raises
from nose.plugins.attrib import attr
from requests import HTTPError

from daf_fruit_dist.artifactory.artifactory_rest import determine_checksums
from daf_fruit_dist.artifactory.repo_detail import read_options
from daf_fruit_dist.build.constants import PYTHON_GROUP_ID


nose_file_path = "{}/nose/nose-1.2.1.tar.gz".format(PYTHON_GROUP_ID)


@attr("integration")
def test_typical_usage():
    repo_details = read_options()

    found_checksums = determine_checksums(
        username=repo_details.username,
        password=repo_details.password,
        repo_base_url=repo_details.repo_base_url,
        repo_pull_id=repo_details.repo_pull_id,
        file_path=nose_file_path,
        verify_cert=False)

    eq_(found_checksums.sha1, "02cc3ffdd7a1ce92cbee388c4a9e939a79f66ba5")
    eq_(found_checksums.md5, "735e3f1ce8b07e70ee1b742a8a53585a")


@attr("integration")
@raises(HTTPError)
def test_invalid_username():
    repo_details = read_options()
    determine_checksums(username="badusername123",
                        password=repo_details.password,
                        repo_base_url=repo_details.repo_base_url,
                        repo_pull_id=repo_details.repo_pull_id,
                        file_path=nose_file_path,
                        verify_cert=False)


@attr("integration")
@raises(HTTPError)
def test_invalid_password():
    repo_details = read_options()
    determine_checksums(username=repo_details.username,
                        password="ThisBadPasswordCantBeRight",
                        repo_base_url=repo_details.repo_base_url,
                        repo_pull_id=repo_details.repo_pull_id,
                        file_path=nose_file_path,
                        verify_cert=False)


@attr("integration")
@raises(HTTPError)
def test_bad_file_path():
    repo_details = read_options()
    determine_checksums(username=repo_details.username,
                        password=repo_details.password,
                        repo_base_url=repo_details.repo_base_url,
                        repo_pull_id=repo_details.repo_pull_id,
                        file_path="badorg/badmodule/bebad-1.2.3.tar.gz",
                        verify_cert=False)


@attr("integration")
@raises(HTTPError)
def test_invalid_repo_pull_id():
    repo_details = read_options()
    determine_checksums(username=repo_details.username,
                        password=repo_details.password,
                        repo_base_url=repo_details.repo_base_url,
                        repo_pull_id="bad-repo-pull-id",
                        file_path=nose_file_path,
                        verify_cert=False)

########NEW FILE########
__FILENAME__ = build_info_module_generator_test
from functools import wraps
import json
import os
import pprint
import tempfile

from nose.tools import eq_
from pip.exceptions import DistributionNotFound
from requests import HTTPError
from daf_fruit_dist.checksum_dependency_helper import ChecksumDependencyHelper
from daf_fruit_dist.checksums import Checksums
from daf_fruit_dist.build.artifact import Artifact
from daf_fruit_dist.build.constants import \
    PYTHON_SDIST, \
    PYTHON_BDIST, \
    PYTHON_EGG, \
    PYTHON_GROUP_ID
from daf_fruit_dist.build.dependency import Dependency
from daf_fruit_dist.build.id import Id
from daf_fruit_dist.build.module import Module
from daf_fruit_dist.build_info_module_generator import BuildInfoModuleGenerator


def set_fn_name(name):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        wrapper.__name__ = name
        return wrapper
    return decorator


class BuildInfoModuleGeneratorTestHelper(object):
    def __init__(self):
        super(BuildInfoModuleGeneratorTestHelper, self).__init__()

        self.module_id = Id(
            group_id=PYTHON_GROUP_ID,
            artifact_id="pointy-stick",
            version="1.2.3")

        self.alternate_module_id = Id(
            group_id=PYTHON_GROUP_ID,
            artifact_id="very-pointy-stick",
            version="7.8.9")

        self.module_properties = {"gorilla": "loves oranges",
                                  "orangutan": "loves bananas"}

        dir_name = os.path.dirname(__file__)

        self.full_requirements_file = os.path.abspath(
            os.path.join(
                dir_name,
                "pointy-stick-1.2.3-requirements.txt"))

        self.empty_requirements_file = os.path.abspath(
            os.path.join(
                dir_name,
                "pointy-stick-1.2.3-empty-requirements.txt"))

        self.unfindable_requirements_file = os.path.abspath(
            os.path.join(
                dir_name,
                "pointy-stick-1.2.3-unfindable-requirements.txt"))

        bdist_name = 'pointy-stick-1.2.3-bdist.txt'
        self.bdist_file = os.path.abspath(os.path.join(dir_name, bdist_name))
        bdist_md5 = "4e5b207722b76b240bdab0f8170abe2e"
        bdist_sha1 = "1436227b16793cc398f2919077d700dfbba46c41"
        self.bdist_artifact = Artifact(
            type=PYTHON_BDIST,
            name=bdist_name,
            sha1=bdist_sha1,
            md5=bdist_md5)

        sdist_name = 'pointy-stick-1.2.3-sdist.txt'
        self.sdist_file = os.path.abspath(os.path.join(dir_name, sdist_name))
        sdist_md5 = "a0fd44030bb445f1b6cddb1aec5d0f5d"
        sdist_sha1 = "0a9185359e621f0916f0902b70dbe5cd3980c7bd"
        self.sdist_artifact = Artifact(
            type=PYTHON_SDIST,
            name=sdist_name,
            sha1=sdist_sha1,
            md5=sdist_md5)

        egg_name = 'pointy-stick-1.2.3-egg.txt'
        self.egg_file = os.path.abspath(os.path.join(dir_name, egg_name))
        egg_md5 = "11e074bc70ac6d067fd850a4e0fec467"
        egg_sha1 = "5308474d2eede397dde38769bb8b0c5f38376370"
        self.egg_artifact = Artifact(
            type=PYTHON_EGG,
            name=egg_name,
            sha1=egg_sha1,
            md5=egg_md5)

        # Dependency types are unknown so therefore have been
        # intentionally set to None.
        colorama_id = Id(
            group_id=PYTHON_GROUP_ID,
            artifact_id="colorama",
            version="0.2.4")

        self.colorama_dependency = Dependency(
            id=colorama_id,
            type=None,
            sha1="ColoramaSHA1SHA1SHA1",
            md5="ColoramaMD5MD5MD5")

        mock_id = Id(
            group_id=PYTHON_GROUP_ID,
            artifact_id="mock",
            version="1.0.1")

        self.mock_dependency = Dependency(
            id=mock_id,
            type=None,
            sha1="MockSHA1SHA1SHA1",
            md5="MockMD5MD5MD5")

        nose_id = Id(
            group_id=PYTHON_GROUP_ID,
            artifact_id="nose",
            version="1.2.1")

        self.nose_dependency = Dependency(
            id=nose_id,
            type=None,
            sha1="NoseSHA1SHA1SHA1",
            md5="NoseMD5MD5MD5")

        unfindable_module_id = Id(
            group_id=PYTHON_GROUP_ID,
            artifact_id="unfindablemodule",
            version="999.999.999")

        self.unfindable_dependency = Dependency(
            id=unfindable_module_id,
            type=None,
            sha1=None,
            md5=None)

        def _add_file_path_and_checksum_to_dictionary(dictionary, dependency):
            dep_file_path = BuildInfoModuleGeneratorTestHelper.\
                _compute_synthetic_path(
                    pkg_name=dependency.id.artifact_id,
                    pkg_version=dependency.id.version)

            dep_checksums = Checksums(
                sha1=dependency.sha1,
                md5=dependency.md5)
            dictionary[dep_file_path] = dep_checksums

        self.file_path_to_checksums = {}

        _add_file_path_and_checksum_to_dictionary(
            self.file_path_to_checksums, self.colorama_dependency)

        _add_file_path_and_checksum_to_dictionary(
            self.file_path_to_checksums, self.mock_dependency)

        _add_file_path_and_checksum_to_dictionary(
            self.file_path_to_checksums, self.nose_dependency)

    @staticmethod
    def _compute_synthetic_path(pkg_name, pkg_version):
        path = (
            "{python_group_id}/"
            "{pkg_name}/"
            "{pkg_name}-{pkg_version}.tar.gz".format(
                python_group_id=PYTHON_GROUP_ID,
                pkg_name=pkg_name,
                pkg_version=pkg_version))

        return path

    def determine_file_path(self, pkg_name, pkg_version):
        findable_pairs = (
            (self.colorama_dependency.id.artifact_id,
             self.colorama_dependency.id.version),

            (self.mock_dependency.id.artifact_id,
             self.mock_dependency.id.version),

            (self.nose_dependency.id.artifact_id,
             self.nose_dependency.id.version),
        )
        if (pkg_name, pkg_version) in findable_pairs:
            return self._compute_synthetic_path(pkg_name, pkg_version)
        else:
            raise DistributionNotFound()

    def determine_checksums_from_file_path(self, file_path):
        if file_path in self.file_path_to_checksums:
            return self.file_path_to_checksums[file_path]
        else:
            raise AssertionError(
                "Unexpected file_path {} within test fixture.".format(
                    file_path))

    def determine_checksums_from_file_path_throw_exception(self, file_path):
        # noinspection PyExceptionInherit
        raise HTTPError()


def _create_temp_file_name():
    temp_file = tempfile.NamedTemporaryFile(
        prefix="module_info_test_",
        suffix=".json",
        delete=True)
    temp_file_name = temp_file.name
    temp_file.close()
    return temp_file_name


def _write_module_file(module, module_file):
    json_data = module.as_json_data
    json_string = json.dumps(json_data, sort_keys=True, indent=4)

    with open(module_file, 'w') as f:
        f.write(json_string)


def _read_module_file(module_file):
    with open(module_file, 'r') as f:
        module_as_json = f.read()
        json_data = json.loads(module_as_json)
        module = Module.from_json_data(json_data)
    return module


helper = BuildInfoModuleGeneratorTestHelper()


def _execute(
        module_id,
        dist_files_tuple_array,
        freeze_file,
        module_file,
        force_dependency_rebuild,
        force_clean,
        expected_module_properties,
        expected_artifacts,
        expected_dependencies):
    #tuple pattern is: (command, python_version, dist_file)

    checksum_dependency_helper = ChecksumDependencyHelper(
        determine_file_path_fn=helper.determine_file_path,
        determine_checksums_from_file_path_fn=
        helper.determine_checksums_from_file_path)

    build_info_module_generator = BuildInfoModuleGenerator(
        determine_dependency_checksums_fn=checksum_dependency_helper)

    ########################################
    #Invoke functionality being tested
    build_info_module_generator.update(
        module_id=module_id,
        module_properties=helper.module_properties,
        freeze_file=freeze_file,
        dist_files=dist_files_tuple_array,
        module_file=module_file,
        force_dependency_rebuild=force_dependency_rebuild,
        force_clean=force_clean)

    ########################################
    #validate behavior
    module = _read_module_file(module_file)
    eq_(module.id, module_id)
    eq_(module.artifacts, expected_artifacts)
    eq_(module.dependencies, expected_dependencies)
    eq_(module.properties, expected_module_properties)


@set_fn_name(
    'test_'
    'no_module_file__'
    'no_requirements_file__'
    'no_force_dependencies_rebuild__'
    'no_force_clean')
def temp_fn_01():
    module_output_file_name = _create_temp_file_name()

    _execute(
        module_id=helper.module_id,
        dist_files_tuple_array=[
            ('sdist', None, helper.sdist_file),
            #        ('bdist', None, bdist_file),
            ('bdist_egg', None, helper.egg_file)],
        freeze_file=helper.unfindable_requirements_file,
        module_file=module_output_file_name,
        force_dependency_rebuild=False,
        force_clean=False,
        expected_module_properties=helper.module_properties,
        expected_artifacts=(helper.sdist_artifact, helper.egg_artifact),
        expected_dependencies=(
            helper.colorama_dependency,
            helper.mock_dependency,
            helper.unfindable_dependency,
            helper.nose_dependency
        )
    )
    os.unlink(module_output_file_name)


@set_fn_name(
    'test_'
    'rest_exception__'
    'no_module_file__'
    'full_req_file__'
    'no_force_dep_rebuild__'
    'no_force_clean')
def temp_fn_02():
    module_output_file_name = _create_temp_file_name()
    exception_caught = False
    try:
        checksum_dependency_helper = ChecksumDependencyHelper(
            determine_file_path_fn=helper.determine_file_path,
            determine_checksums_from_file_path_fn=
            helper.determine_checksums_from_file_path_throw_exception)

        build_info_module_generator = BuildInfoModuleGenerator(
            determine_dependency_checksums_fn=checksum_dependency_helper)

        ########################################
        #Invoke functionality being tested
        build_info_module_generator.update(
            module_id=helper.module_id,
            module_properties=helper.module_properties,
            freeze_file=helper.full_requirements_file,
            dist_files=[
                ('sdist', None, helper.sdist_file),
                #        ('bdist', None, bdist_file),
                ('bdist_egg', None, helper.egg_file)],
            module_file=module_output_file_name,
            force_dependency_rebuild=False,
            force_clean=False)
    except HTTPError:
        exception_caught = True
        #Make sure no trash module file is left behind
        assert not os.path.exists(module_output_file_name)

    assert exception_caught, "Expect HTTPError to be encountered"


@set_fn_name(
    'test_'
    'no_module_file__'
    'full_requirements_file__'
    'no_force_dependency_rebuild__'
    'no_force_clean')
def temp_fn_03():
    """No pre-existing module file and a full requirements file"""

    module_output_file_name = _create_temp_file_name()
    _execute(
        module_id=helper.module_id,
        dist_files_tuple_array=[
            ('sdist', None, helper.sdist_file),
            #        ('bdist', None, bdist_file),
            ('bdist_egg', None, helper.egg_file)],
        freeze_file=helper.full_requirements_file,
        module_file=module_output_file_name,
        force_dependency_rebuild=False,
        force_clean=False,
        expected_module_properties=helper.module_properties,
        expected_artifacts=(helper.sdist_artifact, helper.egg_artifact),
        expected_dependencies=(
            helper.colorama_dependency,
            helper.mock_dependency,
            helper.nose_dependency)
    )
    os.unlink(module_output_file_name)


@set_fn_name(
    'test_'
    'no_module_file__'
    'unrecognized_command_in_dist_files_tuple')
def temp_fn_04():
    """Unrecognized command in the dist files tuple"""

    module_output_file_name = _create_temp_file_name()
    exception_caught = False
    try:
        _execute(
            module_id=helper.module_id,
            dist_files_tuple_array=[
                ('sdist', None, helper.sdist_file),
                #        ('bdist', None, bdist_file),
                ('bdist_funky_egg', None, helper.egg_file)],
            freeze_file=helper.full_requirements_file,
            module_file=module_output_file_name,
            force_dependency_rebuild=False,
            force_clean=False,
            expected_module_properties=helper.module_properties,
            expected_artifacts=(helper.sdist_artifact, helper.egg_artifact),
            expected_dependencies=(
                helper.colorama_dependency,
                helper.mock_dependency,
                helper.nose_dependency),
        )
    except ValueError:
        exception_caught = True
        #Make sure no trash module file is left behind
        assert not os.path.exists(module_output_file_name)

    assert exception_caught, "Expect ValueError to be encountered"


@set_fn_name(
    'test_'
    'no_module_file__'
    'empty_requirements_file__'
    'no_force_dependency_rebuild__'
    'no_force_clean')
def temp_fn_05():
    """
    An empty requirements file should result in a defined but empty
    collection of dependencies.

    Do not confuse an empty collection with a collection of None. A
    collection of None would imply no requirements file was processed.
    """

    module_output_file_name = _create_temp_file_name()
    _execute(
        module_id=helper.module_id,
        dist_files_tuple_array=[
            ('sdist', None, helper.sdist_file),
            #        ('bdist', None, bdist_file),
            ('bdist_egg', None, helper.egg_file)],
        freeze_file=helper.empty_requirements_file,
        module_file=module_output_file_name,
        force_dependency_rebuild=False,
        force_clean=False,
        expected_module_properties=helper.module_properties,
        expected_artifacts=(helper.sdist_artifact, helper.egg_artifact),
        expected_dependencies=()
    )
    os.unlink(module_output_file_name)


@set_fn_name(
    'test_'
    'existing_module_file__'
    'full_requirements_file__'
    'no_force_dependency_rebuild__'
    'no_force_clean')
def temp_fn_06():
    """pre-existing module file and full requirements file"""

    module_output_file_name = _create_temp_file_name()

    early_properties = {'skunk': 'stinks', 'raccoon': 'cleans food'}
    early_module = Module(
        id=helper.module_id,
        properties=early_properties,
        artifacts=(helper.bdist_artifact,),
        dependencies=(helper.colorama_dependency,))
    _write_module_file(early_module, module_output_file_name)

    #conditions prepared, now perform action under test and assert results
    _execute(
        module_id=helper.module_id,
        dist_files_tuple_array=[
            ('sdist', None, helper.sdist_file),
            #        ('bdist', None, bdist_file),
            ('bdist_egg', None, helper.egg_file)],
        freeze_file=helper.full_requirements_file,
        module_file=module_output_file_name,
        force_dependency_rebuild=False,
        force_clean=False,
        expected_module_properties=early_properties,
        expected_artifacts=(
            helper.bdist_artifact,
            helper.sdist_artifact,
            helper.egg_artifact),
        expected_dependencies=(helper.colorama_dependency,)
    )
    os.unlink(module_output_file_name)


@set_fn_name(
    'test_'
    'existing_module_file__'
    'non_matching_module_id')
def temp_fn_07():
    """pre-existing module file with non-matching module id"""

    module_output_file_name = _create_temp_file_name()

    early_properties = {'skunk': 'stinks', 'raccoon': 'cleans food'}
    early_module = Module(
        id=helper.alternate_module_id,
        properties=early_properties,
        artifacts=(helper.bdist_artifact,),
        dependencies=(helper.colorama_dependency,))
    _write_module_file(early_module, module_output_file_name)

    exception_caught = False

    #conditions prepared, now perform action under test and assert results
    try:
        _execute(
            module_id=helper.module_id,
            dist_files_tuple_array=[
                ('sdist', None, helper.sdist_file),
                #        ('bdist', None, bdist_file),
                ('bdist_egg', None, helper.egg_file)],
            freeze_file=helper.full_requirements_file,
            module_file=module_output_file_name,
            force_dependency_rebuild=False,
            force_clean=False,
            expected_module_properties=early_properties,
            expected_artifacts=(
                helper.bdist_artifact,
                helper.sdist_artifact,
                helper.egg_artifact),
            expected_dependencies=(helper.colorama_dependency,)
        )
    except ValueError:
        exception_caught = True

    assert exception_caught, "Expect ValueError to be encountered"
    os.unlink(module_output_file_name)


@set_fn_name(
    'test_'
    'existing_module_file__'
    'full_requirements_file__'
    'no_force_dependency_rebuild__'
    'force_clean')
def temp_fn_08():
    """pre-existing module file with force clean"""

    module_output_file_name = _create_temp_file_name()

    early_properties = {'skunk': 'stinks', 'raccoon': 'cleans food'}
    early_module = Module(
        id=helper.module_id,
        properties=early_properties,
        artifacts=(helper.bdist_artifact,),
        dependencies=(helper.colorama_dependency,))
    _write_module_file(early_module, module_output_file_name)

    #conditions prepared, now perform action under test and assert results
    _execute(
        module_id=helper.module_id,
        dist_files_tuple_array=[
            ('sdist', None, helper.sdist_file),
            #        ('bdist', None, bdist_file),
            ('bdist_egg', None, helper.egg_file)],
        freeze_file=helper.full_requirements_file,
        module_file=module_output_file_name,
        force_dependency_rebuild=False,
        force_clean=True,
        expected_module_properties=helper.module_properties,
        expected_artifacts=(helper.sdist_artifact, helper.egg_artifact),
        expected_dependencies=(
            helper.colorama_dependency,
            helper.mock_dependency,
            helper.nose_dependency)
    )
    os.unlink(module_output_file_name)


@set_fn_name(
    'test_'
    'existing_module_file__'
    'full_requirements_file__'
    'force_dependency_rebuild__'
    'no_force_clean')
def temp_fn_09():
    """
    pre-existing module file with incomplete dependencies but a forced
    dependency rebuild
    """

    module_output_file_name = _create_temp_file_name()

    early_properties = {'skunk': 'stinks', 'raccoon': 'cleans food'}
    early_module = Module(
        id=helper.module_id,
        properties=early_properties,
        artifacts=(helper.bdist_artifact,),
        dependencies=(helper.colorama_dependency,))
    _write_module_file(early_module, module_output_file_name)

    #conditions prepared, now perform action under test and assert results
    _execute(
        module_id=helper.module_id,
        dist_files_tuple_array=[
            ('sdist', None, helper.sdist_file),
            #        ('bdist', None, bdist_file),
            ('bdist_egg', None, helper.egg_file)],
        freeze_file=helper.full_requirements_file,
        module_file=module_output_file_name,
        force_dependency_rebuild=True,
        force_clean=False,
        expected_module_properties=early_properties,
        expected_artifacts=(
            helper.bdist_artifact,
            helper.sdist_artifact,
            helper.egg_artifact),
        expected_dependencies=(
            helper.colorama_dependency,
            helper.mock_dependency,
            helper.nose_dependency)
    )
    os.unlink(module_output_file_name)


@set_fn_name(
    'test_'
    'existing_module_file_with_no_artifacts__'
    'full_requirements_file__'
    'no_force_dependency_rebuild__'
    'no_force_clean')
def temp_fn_10():
    """
    pre-existing module file with no artifacts, matching id and
    different properties
    """

    module_output_file_name = _create_temp_file_name()

    early_properties = {'skunk': 'stinks', 'raccoon': 'cleans food'}
    early_module = Module(
        id=helper.module_id,
        properties=early_properties,
        artifacts=None,
        dependencies=(helper.colorama_dependency,))
    _write_module_file(early_module, module_output_file_name)

    #conditions prepared, now perform action under test and assert results
    _execute(
        module_id=helper.module_id,
        dist_files_tuple_array=[
            ('sdist', None, helper.sdist_file),
            #        ('bdist', None, bdist_file),
            ('bdist_egg', None, helper.egg_file)],
        freeze_file=helper.full_requirements_file,
        module_file=module_output_file_name,
        force_dependency_rebuild=False,
        force_clean=False,
        expected_module_properties=early_properties,
        expected_artifacts=(helper.sdist_artifact, helper.egg_artifact),
        expected_dependencies=(helper.colorama_dependency,)
    )
    os.unlink(module_output_file_name)


@set_fn_name(
    'test_'
    'existing_module_file_with_no_deps__'
    'full_requirements_file__'
    'no_force_dependency_rebuild__'
    'no_force_clean')
def temp_fn_11():
    """
    pre-existing module file with no dependencies, matching id and
    different properties
    """

    module_output_file_name = _create_temp_file_name()

    early_properties = {'skunk': 'stinks', 'raccoon': 'cleans food'}
    early_module = Module(
        id=helper.module_id,
        properties=early_properties,
        artifacts=(helper.bdist_artifact,),
        dependencies=None)
    _write_module_file(early_module, module_output_file_name)

    #conditions prepared, now perform action under test and assert results
    _execute(
        module_id=helper.module_id,
        dist_files_tuple_array=[
            ('sdist', None, helper.sdist_file),
            #        ('bdist', None, bdist_file),
            ('bdist_egg', None, helper.egg_file)],
        freeze_file=helper.full_requirements_file,
        module_file=module_output_file_name,
        force_dependency_rebuild=False,
        force_clean=False,
        expected_module_properties=early_properties,
        expected_artifacts=(
            helper.bdist_artifact,
            helper.sdist_artifact,
            helper.egg_artifact),
        expected_dependencies=(
            helper.colorama_dependency,
            helper.mock_dependency,
            helper.nose_dependency)
    )
    os.unlink(module_output_file_name)


@set_fn_name(
    'test_'
    'no_module_file__'
    'missing_requirements_file__'
    'no_force_dependency_rebuild__'
    'no_force_clean')
def temp_fn_12():
    """
    An empty requirements file should result in a defined but empty
    collection of dependencies.

    Do not confuse an empty collection with a collection of None. A
    collection of None would imply no requirements file was processed.
    """

    module_output_file_name = _create_temp_file_name()
    non_existent_requirements_file = _create_temp_file_name()
    exception_caught = False
    try:
        _execute(
            module_id=helper.module_id,
            dist_files_tuple_array=[
                ('sdist', None, helper.sdist_file),
                #        ('bdist', None, bdist_file),
                ('bdist_egg', None, helper.egg_file)],
            freeze_file=non_existent_requirements_file,
            module_file=module_output_file_name,
            force_dependency_rebuild=False,
            force_clean=False,
            expected_module_properties=helper.module_properties,
            expected_artifacts=(helper.sdist_artifact, helper.egg_artifact),
            expected_dependencies=()
        )
    except IOError as e:
        exception_caught = True

        #Make sure no trash module file is left behind
        assert not os.path.exists(module_output_file_name)
        eq_(e.filename, non_existent_requirements_file)

    assert exception_caught, "Expect IOError to be encountered"


def test_case_sensitive_dependencies():
    """
    Verify that artifact IDs of dependencies match the real project
    name, not the case-insensitive key.
    """

    class MockModuleBuilder(object):
        def __init__(self):
            self.__module_names = []

        def ensure_dependencies_defined(self):
            pass

        # noinspection PyShadowingBuiltins
        def add_dependency(self, type, id, sha1, md5):
            self.__module_names.append(id.artifact_id)

        def compare_modules(self, freeze_file):
            with open(freeze_file) as f:
                modules = f.read().splitlines()

            expected_set = frozenset([m.split('==')[0] for m in modules])
            actual_set = frozenset(self.__module_names)

            assert actual_set == expected_set, (
                '\nActual module names:\n    {}'
                '\nExpected module names:\n    {}'.format(
                    '\n    '.join(pprint.pformat(actual_set).splitlines()),
                    '\n    '.join(pprint.pformat(expected_set).splitlines())))

            eq_(actual_set, expected_set)

    generator = BuildInfoModuleGenerator(
        determine_dependency_checksums_fn=
        lambda artifact_id, version: (None, None))

    freeze_file = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "case-sensitive-requirements.txt")

    mock_module_builder = MockModuleBuilder()
    generator._reset_dependencies(freeze_file, mock_module_builder)
    mock_module_builder.compare_modules(freeze_file)

########NEW FILE########
__FILENAME__ = build_info_builder_test
from nose.tools import eq_

from daf_fruit_dist.build.agent import Agent
from daf_fruit_dist.build.build_info import BuildInfo
from daf_fruit_dist.build.build_retention import BuildRetention
from daf_fruit_dist.build.constants import PYTHON_SDIST
from daf_fruit_dist.build.id import Id
from daf_fruit_dist.build.module import Module
from daf_fruit_dist.tests.build_tests import module_test_helper


def _create_build_info_builder():
    bi_builder = BuildInfo.Builder(
        version="2.2.2",
        name="lets-build",
        number="123456789",
        type=PYTHON_SDIST,
        started="100",
        duration_millis=10000,
        artifactory_principal="dude",
        agent=Agent(name="defend_against_fruit", version="5.2"),
        build_agent=Agent(name="TeamCity", version="1.3"),
        build_retention=BuildRetention(
            count=5,
            delete_build_artifacts=False,
            build_numbers_not_to_be_discarded=[111, 999])
    )
    return bi_builder


def _create_build_info():
    bi_builder = _create_build_info_builder()

    moduleA = _create_module()
    bi_builder.add_module(moduleA)

    moduleB = _create_module()
    bi_builder.add_module(moduleB)

    moduleC = _create_module()
    bi_builder.add_module(moduleC)

    build_info = bi_builder.build()

    return build_info


def _assert_basic_attributes(build_info):
    eq_(build_info.name, "lets-build")
    eq_(build_info.version, "2.2.2")
    eq_(build_info.name, "lets-build")
    eq_(build_info.number, "123456789")
    eq_(build_info.type, PYTHON_SDIST)
    eq_(build_info.started, "100")
    eq_(build_info.duration_millis, 10000)
    eq_(build_info.artifactory_principal, "dude")
    eq_(build_info.agent.name, "defend_against_fruit")
    eq_(build_info.agent.version, "5.2")
    eq_(build_info.build_agent.name, "TeamCity")
    eq_(build_info.build_agent.version, "1.3")
    eq_(build_info.build_retention.count, 5)
    eq_(build_info.build_retention.delete_build_artifacts, False)
    eq_(build_info.build_retention.build_numbers_not_to_be_discarded,
        [111, 999])


def _create_module():
    module_builder = module_test_helper.create_module_builder()

    module_test_helper.add_some_artifacts(module_builder)

    module_test_helper.add_some_dependencies(module_builder)

    module = module_builder.build()

    return module


def typical_usage_test():
    build_info = _create_build_info()

    _assert_basic_attributes(build_info)


def equals_and_hash_expected_equality_test():
    """
    Test equals and hashcode behavior of BuildInfo and the containing
    classes.

    If I have messed up I'm pretty sure it will show up as a false
    negative not a false positive. The most likely problem is that I
    have tried to hash some structure that will throw an unhashable
    type error.
    """
    build_info_A = _create_build_info()
    build_info_B = _create_build_info()
    eq_(build_info_A, build_info_B)

    eq_(build_info_A.__hash__(), build_info_B.__hash__())


def equals_and_hash_expected_difference_test():
    """
    quick check to make sure I am not causing problems by feeding a dict
    to frozenset.
    """
    bi_builder_C = _create_build_info_builder()
    module_builder_C = Module.Builder(
        id=Id(
            group_id="defend.against.fruit",
            artifact_id="pointy-stick",
            version="5.2"),
        properties={'ape', 'lets swing'})
    bi_builder_C.add_module(module_builder_C.build())
    build_info_C = bi_builder_C.build()

    bi_builder_D = _create_build_info_builder()
    module_builder_D = Module.Builder(
        id=Id(
            group_id="defend.against.fruit",
            artifact_id="pointy-stick",
            version="5.2"),
        properties={'ape', 'lets make funny faces'})
    bi_builder_D.add_module(module_builder_D.build())
    build_info_D = bi_builder_D.build()

    assert build_info_C != build_info_D, \
        "different property values should result in unequal BuildInfo " \
        "instances"

    assert build_info_C.__hash__() != build_info_D.__hash__(), \
        "different property values should result in unequal hash values"


def json_encoding_decoding_test():
    build_info = _create_build_info()

    module_test_helper.round_trip_to_and_from_wire_format(
        build_info,
        BuildInfo.from_json_data,
        _assert_basic_attributes)


def no_modules_test():
    bi_builder = _create_build_info_builder()
    build_info = bi_builder.build()

    module_test_helper.round_trip_to_and_from_wire_format(
        build_info,
        BuildInfo.from_json_data,
        _assert_basic_attributes)


def single_module_without_artifacts_test():
    bi_builder = _create_build_info_builder()
    module_builderA = module_test_helper.create_module_builder()
    module_test_helper.add_some_dependencies(module_builderA)
    moduleA = module_builderA.build()

    bi_builder.add_module(moduleA)
    build_info = bi_builder.build()

    module_test_helper.round_trip_to_and_from_wire_format(
        build_info,
        BuildInfo.from_json_data,
        _assert_basic_attributes)


def single_module_without_dependencies_test():
    bi_builder = _create_build_info_builder()
    module_builderA = module_test_helper.create_module_builder()
    module_test_helper.add_some_artifacts(module_builderA)
    moduleA = module_builderA.build()

    bi_builder.add_module(moduleA)
    build_info = bi_builder.build()

    module_test_helper.round_trip_to_and_from_wire_format(
        build_info,
        BuildInfo.from_json_data,
        _assert_basic_attributes)


def single_module_with_missing_module_attributes_test():
    module_builder = Module.Builder(
        id=None,
        #id=Id(
        #   group_id="defend.against.fruit",
        #   artifact_id="pointy-stick",
        #   version="5.2"),
        properties={'banana': 'monkey love',
                    'orange': 'gorilla color'})

    module_test_helper.add_some_artifacts(module_builder)

    module_test_helper.add_some_dependencies(module_builder)

    module = module_builder.build()

    bi_builder = _create_build_info_builder()
    bi_builder.add_module(module)

    build_info = bi_builder.build()

    module_test_helper.round_trip_to_and_from_wire_format(
        build_info,
        BuildInfo.from_json_data,
        _assert_basic_attributes)


def missing_basic_attributes_test():
    bi_builder = BuildInfo.Builder(
        version="2.2.2",
        name="lets-build",
        #number="123456789",
        type=PYTHON_SDIST,
        #started="100",
        duration_millis=10000,
        artifactory_principal="dude",
        #agent=Agent(name="defend_against_fruit", version="5.2"),
        #build_agent=Agent(name="TeamCity", version="1.3"),
        build_retention=BuildRetention(
            count=5,
            delete_build_artifacts=False)
    )

    bi_builder.add_module(_create_module())
    build_info = bi_builder.build()

    module_test_helper.round_trip_to_and_from_wire_format(
        build_info,
        from_json_data_func=BuildInfo.from_json_data)

########NEW FILE########
__FILENAME__ = module_builder_test
import json
from nose.tools import eq_
from daf_fruit_dist.build.constants import PYTHON_SDIST
from daf_fruit_dist.build.module import Module
from daf_fruit_dist.tests.build_tests import module_test_helper


def typical_artifacts_no_dependencies_test():
    module_builder = module_test_helper.create_module_builder()
    module_test_helper.add_some_artifacts(module_builder)
    module = module_builder.build()

    module_test_helper.assert_module_basics(module)
    module_test_helper.assert_artifacts(module)


def typical_artifacts_and_dependencies_test():
    module_builder = module_test_helper.create_module_builder()
    module_test_helper.add_some_artifacts(module_builder)
    module_test_helper.add_some_dependencies(module_builder)
    module = module_builder.build()

    module_test_helper.assert_module_basics(module)
    module_test_helper.assert_artifacts(module)
    module_test_helper.assert_dependencies(module)

    json_data = module.as_json_data
    json_string = json.dumps(json_data, sort_keys=True, indent=4)

    assert json_string, "json string is non-null"


def _create_complete_module():
    module_builder = module_test_helper.create_module_builder()
    module_test_helper.add_some_artifacts(module_builder)
    module_test_helper.add_some_dependencies(module_builder)
    module = module_builder.build()
    return module


def json_encoding_decoding_test():
    module = _create_complete_module()

    module_test_helper.round_trip_to_and_from_wire_format(
        module,
        Module.from_json_data,
        module_test_helper.assert_module_basics)


def null_vs_empty_dependencies_test():
    """
    Missing artifacts or dependencies should be None not an empty
    collection.
    """
    module_builder = module_test_helper.create_module_builder(
        treat_none_as_empty=False)

    module = module_builder.build()

    eq_(module.artifacts, None, "artifacts start as None")
    eq_(module.dependencies, None, "dependencies start as None")

    #Take the domain object down to wire-level format
    json_string = json.dumps(module.as_json_data, sort_keys=True, indent=4)

    #Read the wire-level data back into a domain object
    json_data_2 = json.loads(json_string)
    re_hydrated_module = Module.from_json_data(json_data_2)

    eq_(re_hydrated_module.artifacts, None,
        "artifacts of None survives round-trip on the wire")

    eq_(re_hydrated_module.dependencies, None,
        "artifacts of None survives round-trip on the wire")


def ensure_artifacts_defined_test():
    module_builder = module_test_helper.create_module_builder(
        treat_none_as_empty=False)

    module_builder.ensure_artifacts_defined()
    module = module_builder.build()

    eq_(module.artifacts, (), "artifacts defined but empty")
    eq_(module.dependencies, None, "dependencies not defined")


def ensure_dependencies_defined_test():
    module_builder = module_test_helper.create_module_builder(
        treat_none_as_empty=False)

    module_builder.ensure_dependencies_defined()
    module = module_builder.build()

    eq_(module.artifacts, None, "artifacts not defined")
    eq_(module.dependencies, (), "dependencies defined but empty")


def treat_none_as_empty_false__empty_artifacts__undefined_dependencies_test():
    module_builder = module_test_helper.create_module_builder(
        artifacts=[],
        dependencies=None,
        treat_none_as_empty=False)
    module = module_builder.build()

    eq_(module.artifacts, (), "artifacts defined but empty")
    eq_(module.dependencies, None, "dependencies not defined")


def treat_none_as_empty_false__undefined_artifacts__empty_dependencies_test():
    module_builder = module_test_helper.create_module_builder(
        artifacts=None,
        dependencies=[],
        treat_none_as_empty=False)
    module = module_builder.build()

    eq_(module.artifacts, None, "artifacts not defined")
    eq_(module.dependencies, (), "dependencies defined but empty")


def ensure_artifacts_defined_non_empty_collection_test():
    module_builder = module_test_helper.create_module_builder(
        treat_none_as_empty=False)

    module_test_helper.add_some_artifacts(module_builder)
    module_builder.ensure_artifacts_defined()
    module = module_builder.build()

    module_test_helper.assert_artifacts(module)
    eq_(module.dependencies, None, "dependencies not defined")


def ensure_dependencies_defined__non_empty_collection_test():
    module_builder = module_test_helper.create_module_builder(
        treat_none_as_empty=False)

    module_test_helper.add_some_dependencies(module_builder)

    module_builder.ensure_dependencies_defined()
    module = module_builder.build()

    eq_(module.artifacts, None, "artifacts not defined")
    module_test_helper.assert_dependencies(module)


def module_builder_from_module_test():
    moduleA = _create_complete_module()

    module_builderB = Module.Builder.from_another_module(moduleA)
    moduleB = module_builderB.build()

    eq_(moduleB, moduleA)

    # Add some more artifacts. Will blow up if the internal collection
    # isn't mutable as it should be.
    module_test_helper.add_some_artifacts(module_builderB)
    module_test_helper.add_some_dependencies(module_builderB)


def module_builder_from_module_with_dependencies_of_none_test():
    #Intentionally exclude dependencies while ensuring None is treated as None.
    module_builder = module_test_helper.create_module_builder(
        treat_none_as_empty=False)

    module_test_helper.add_some_artifacts(module_builder)
    moduleA = module_builder.build()

    module_builderB = Module.Builder.from_another_module(
        moduleA, treat_none_as_empty=False)

    moduleB = module_builderB.build()

    eq_(moduleB, moduleA)


def module_builder_from_module_copy_dependencies_false_test():
    module_builder = module_test_helper.create_module_builder(
        treat_none_as_empty=False)

    module_test_helper.add_some_artifacts(module_builder)
    module_test_helper.add_some_dependencies(module_builder)
    moduleA = module_builder.build()

    module_builderB = Module.Builder.from_another_module(
        moduleA, treat_none_as_empty=False, copy_dependencies=False)

    moduleB = module_builderB.build()

    eq_(moduleB.id, moduleA.id)
    eq_(moduleB.properties, moduleA.properties)
    eq_(moduleB.artifacts, moduleA.artifacts)
    eq_(moduleB.dependencies, None)

    module_builderC = Module.Builder.from_another_module(
        moduleA, treat_none_as_empty=True, copy_dependencies=False)

    moduleC = module_builderC.build()

    eq_(moduleC.id, moduleA.id)
    eq_(moduleC.artifacts, moduleA.artifacts)
    eq_(moduleC.properties, moduleA.properties)
    eq_(moduleC.dependencies, ())


def dependency_missing_id_test():
    module_builder = module_test_helper.create_module_builder()

    module_test_helper.add_some_artifacts(module_builder)

    #No id specified
    module_builder.add_dependency(
        type=PYTHON_SDIST,
        id=None,
        sha1="GunSHA1SHA1SHA1",
        md5="GunMD5MD5MD5"
    )

    module = module_builder.build()

    module_test_helper.round_trip_to_and_from_wire_format(
        module,
        Module.from_json_data,
        module_test_helper.assert_module_basics)

########NEW FILE########
__FILENAME__ = module_test_helper
import json
import os
from nose.tools import eq_
from daf_fruit_dist.build.constants import \
    PYTHON_SDIST, \
    PYTHON_EGG, \
    PYTHON_FREEZE
from daf_fruit_dist.build.id import Id
from daf_fruit_dist.build.module import Module


def assert_artifacts(module):
    artifacts = module.artifacts

    eq_(len(artifacts), 3)
    eq_(artifacts[0].type, PYTHON_EGG)
    eq_(artifacts[0].sha1, "EggSHA1SHA1SHA1")
    eq_(artifacts[0].md5, "EggMD5MD5MD5")
    eq_(artifacts[0].name, "pointy-stick-5.2.egg")
    eq_(artifacts[1].type, PYTHON_FREEZE)
    eq_(artifacts[1].sha1, "FreezeSHA1SHA1SHA1")
    eq_(artifacts[1].md5, "FreezeMD5MD5MD5")
    eq_(artifacts[1].name, "pointy-stick-5.2.txt")
    eq_(artifacts[2].type, PYTHON_SDIST)
    eq_(artifacts[2].sha1, "c846dc274ccbefd9736b9e48011d2e3a1d149e72")
    eq_(artifacts[2].md5, "e85249246810d56aad3f198deea74bbb")
    eq_(artifacts[2].name, "pointy-stick-5.2.txt")


def create_module_builder(
        artifacts=None,
        dependencies=None,
        treat_none_as_empty=True):

    module_builder = Module.Builder(
        id=Id(
            group_id="defend.against.fruit",
            artifact_id="pointy-stick",
            version="5.2"),
        properties={'banana': 'monkey love', 'orange': 'gorilla color'},
        artifacts=artifacts,
        dependencies=dependencies,
        treat_none_as_empty=treat_none_as_empty
    )
    return module_builder


def add_some_dependencies(module_builder):
    module_builder.add_dependency(
        type=PYTHON_SDIST,
        sha1="GunSHA1SHA1SHA1",
        md5="GunMD5MD5MD5",
        id=Id(
            group_id="defend.against.fruit",
            artifact_id="gun",
            version="2.3"))

    module_builder.add_dependency(
        type=PYTHON_SDIST,
        md5="WeightMD5MD5MD5",
        id=Id(
            group_id="defend.against.fruit",
            artifact_id="weight",
            version="5.6.7"))


def assert_dependencies(module):
    dependencies = module.dependencies

    eq_(dependencies[0].type, PYTHON_SDIST)
    eq_(dependencies[0].sha1, "GunSHA1SHA1SHA1")
    eq_(dependencies[0].md5, "GunMD5MD5MD5")
    eq_(dependencies[0].id.group_id, "defend.against.fruit")
    eq_(dependencies[0].id.artifact_id, "gun")
    eq_(dependencies[0].id.version, "2.3")

    eq_(dependencies[1].type, PYTHON_SDIST)
    eq_(dependencies[1].sha1, None)
    eq_(dependencies[1].md5, "WeightMD5MD5MD5")
    eq_(dependencies[1].id.group_id, "defend.against.fruit")
    eq_(dependencies[1].id.artifact_id, "weight")
    eq_(dependencies[1].id.version, "5.6.7")


def add_some_artifacts(module_builder):
    module_builder.add_artifact(
        type=PYTHON_EGG,
        sha1="EggSHA1SHA1SHA1",
        md5="EggMD5MD5MD5",
        name="pointy-stick-5.2.egg")
    module_builder.add_artifact(
        type=PYTHON_FREEZE,
        sha1="FreezeSHA1SHA1SHA1",
        md5="FreezeMD5MD5MD5",
        name="pointy-stick-5.2.txt")
    dir_name = os.path.dirname(__file__)
    fake_artifact_file = os.path.join(dir_name, 'pointy-stick-5.2.txt')
    module_builder.add_file_as_artifact(
        type=PYTHON_SDIST,
        file=fake_artifact_file)


def assert_module_basics(module):
    eq_(module.id.group_id, "defend.against.fruit")
    eq_(module.id.artifact_id, "pointy-stick")
    eq_(module.id.version, "5.2")
    eq_(module.properties['banana'], 'monkey love')
    eq_(module.properties['orange'], 'gorilla color')


def round_trip_to_and_from_wire_format(
        domain_object,
        from_json_data_func,
        domain_object_assertion_func=None):

    # Perform assertions if any on the domain object before starting
    if domain_object_assertion_func:
        domain_object_assertion_func(domain_object)

    # Take the domain object down to wire-level format
    json_data_1 = domain_object.as_json_data
    domain_object_as_json_1 = json.dumps(json_data_1, sort_keys=True, indent=4)
    assert domain_object_as_json_1, "json string is non-null"

    # Read the wire-level data back into a domain object
    json_data_2 = json.loads(domain_object_as_json_1)
    domain_object_2 = from_json_data_func(json_data_2)

    # See if the re-hydrated domain object still passes the assertions
    # (if any)
    if domain_object_assertion_func:
        domain_object_assertion_func(domain_object_2)

    # Take the re-hydrated domain object back down to the wire-level
    # format again
    json_data_3 = domain_object_2.as_json_data
    domain_object_as_json_3 = json.dumps(json_data_3, sort_keys=True, indent=4)
    assert domain_object_as_json_3, "json string is non-null"

    # Assert the wire-level format looked identical both times
    eq_(domain_object_as_json_1, domain_object_as_json_3)

########NEW FILE########
__FILENAME__ = promotion_request_test
from nose.tools import eq_
from daf_fruit_dist.build.promotion_request import PromotionRequest
from daf_fruit_dist.tests.build_tests import module_test_helper


def _create_promotion_request(comment="Tested on all target platforms."):
    promotion_request = PromotionRequest(
        status="staged",
        comment=comment,
        ci_user="builder",
        timestamp="ISO8601",
        dry_run=True,
        target_repo="libs-release-local",
        copy=False,
        artifacts=True,
        dependencies=False,
        scopes=['compile', 'runtime'],
        properties={
            "components": ["c1", "c3", "c14"],
            "release-name": ["fb3-ga"]},
        fail_fast=True)
    return promotion_request


def equals_test():
    promotion_request = _create_promotion_request()
    promotion_requestB = _create_promotion_request()
    promotion_requestC = _create_promotion_request(comment="lets be different")

    eq_(promotion_request, promotion_requestB)

    assert promotion_requestC != promotion_request, \
        "%r == %r" % (promotion_requestC, promotion_request)


def json_encoding_decoding_test():
    promotion_request = _create_promotion_request()

    def assert_expected_promotion_request(other):
        eq_(other, promotion_request)

    module_test_helper.round_trip_to_and_from_wire_format(
        promotion_request,
        PromotionRequest.from_json_data,
        assert_expected_promotion_request)


def typical_usage_test():
    expected_json_data = {
        "status": "staged",
        "comment": "Tested on all target platforms.",
        "ciUser": "builder",
        "timestamp": "ISO8601",
        "dryRun": True,
        "targetRepo": "libs-release-local",
        "copy": False,
        "artifacts": True,
        "dependencies": False,
        "scopes": ["compile", "runtime"],
        "properties": {
            "components": ["c1", "c3", "c14"],
            "release-name": ["fb3-ga"]},
        "failFast": True,
    }

    promotion_request = _create_promotion_request()

    actual_json_data = promotion_request.as_json_data

    eq_(actual_json_data, expected_json_data)


def no_scopes_specified_test():
    expected_json_data = {
        "status": "staged",
        "comment": "Tested on all target platforms.",
        "ciUser": "builder",
        "timestamp": "ISO8601",
        "dryRun": True,
        "targetRepo": "libs-release-local",
        "copy": False,
        "artifacts": True,
        "dependencies": False,
        "scopes": None,
        "properties": None,
        "failFast": True,
    }

    promotion_request = PromotionRequest(
        status="staged",
        comment="Tested on all target platforms.",
        ci_user="builder",
        timestamp="ISO8601",
        dry_run=True,
        target_repo="libs-release-local",
        copy=False,
        artifacts=True,
        dependencies=False,
        properties=None,
        fail_fast=True)

    actual_json_data = promotion_request.as_json_data

    eq_(actual_json_data, expected_json_data)

########NEW FILE########
__FILENAME__ = checksum_dependency_helper_tests
from collections import namedtuple
from nose.tools import eq_, raises
from pip.exceptions import DistributionNotFound
from requests import RequestException
from daf_fruit_dist.checksum_dependency_helper import ChecksumDependencyHelper


def found_files_and_checksums_test():
    """
    Verify that finding a package and its associated checksums results
    in those checksums being returned.
    """
    TestContext(
        determine_file_path_succeeds=True,
        determine_checksums_succeeds=True,
        expected_checksums=checksums_found).run()


def failed_to_find_file_test():
    """
    Verify that failing to find a package results in None being returned
    for each checksum.
    """
    TestContext(
        determine_file_path_succeeds=False,
        determine_checksums_succeeds=False,
        expected_checksums=checksums_not_found).run()


@raises(RequestException)
def found_file_but_not_checksums_test():
    """
    Verify that successfully finding a package but not its associated
    checksums results in an exception.
    """
    TestContext(
        determine_file_path_succeeds=True,
        determine_checksums_succeeds=False,
        checksum_lookup_exception=RequestException).run()


###############################################################################
######################################################### Test Data and Helpers

Checksums = namedtuple('Hashes', ('md5', 'sha1'))

checksums_found = Checksums(md5='MD5', sha1='SHA1')
checksums_not_found = Checksums(md5=None, sha1=None)


class TestContext(object):
    def __init__(
            self,
            determine_file_path_succeeds,
            determine_checksums_succeeds,
            expected_checksums=None,
            checksum_lookup_exception=Exception):

        self.__checksums = expected_checksums
        self.__checksum_lookup_exception = checksum_lookup_exception

        if determine_file_path_succeeds:
            self.__determine_file_path_fn = lambda pkg_name, pkg_version: None
        else:
            def fn(pkg_name, pkg_version):
                raise DistributionNotFound()
            self.__determine_file_path_fn = fn

        if determine_checksums_succeeds:
            self.__determine_checksums_fn = (
                lambda dependency_path: self.__checksums)
        else:
            def fn(dependency_path):
                raise self.__checksum_lookup_exception()
            self.__determine_checksums_fn = fn

    def __verify_checksums(self, actual_md5, actual_sha1):
        eq_(actual_md5, self.__checksums.md5)
        eq_(actual_sha1, self.__checksums.sha1)

    def run(self):
        checksum_dependency_helper = ChecksumDependencyHelper(
            determine_file_path_fn=self.__determine_file_path_fn,
            determine_checksums_from_file_path_fn=
            self.__determine_checksums_fn)

        actual_md5, actual_sha1 = checksum_dependency_helper(
            artifact_id=None,
            version=None)

        self.__verify_checksums(actual_md5, actual_sha1)

########NEW FILE########
__FILENAME__ = collect_env_info_tests
import os
from nose.tools import raises, eq_
from daf_fruit_dist.build_info_utils import collect_env_info, EnvInfo


###############################################################################
######################################################################### Tests

def test_all_required_set():
    """
    Test that all required environment variables being set results in no
    error.
    """
    with only_these_environment_variables_set(ALL_REQ_ENV_VARS):
        env_info = collect_env_info()

    validate_env_info_against_ideal(
        actual=env_info,
        expected=expected_using_build_name)


@raises(RuntimeError)
def test_no_required_set():
    """
    Test that no required environment variables being set results in an
    error.
    """
    with no_environment_variables_set():
        collect_env_info()


@raises(RuntimeError)
def test_all_required_set_except_major_version():
    """
    Test that all required environment variables being set except
    MAJOR_VERSION generates an error.
    """
    all_except_major_version = dict_subtract(ALL_REQ_ENV_VARS, 'MAJOR_VERSION')

    with only_these_environment_variables_set(all_except_major_version):
        collect_env_info()


@raises(RuntimeError)
def test_all_required_set_except_minor_version():
    """
    Test that all required environment variables being set except
    MINOR_VERSION generates an error.
    """
    all_except_minor_version = dict_subtract(ALL_REQ_ENV_VARS, 'MINOR_VERSION')

    with only_these_environment_variables_set(all_except_minor_version):
        collect_env_info()


@raises(RuntimeError)
def test_all_required_set_except_build_number():
    """
    Test that all required environment variables being set except
    BUILD_NUMBER generates an error.
    """
    all_except_build_number = dict_subtract(ALL_REQ_ENV_VARS, 'BUILD_NUMBER')

    with only_these_environment_variables_set(all_except_build_number):
        collect_env_info()


@raises(RuntimeError)
def test_all_required_set_except_build_name_and_teamcity_buildconf_name():
    """
    Test that all required environment variables being set except
    BUILD_NAME *and* TEAMCITY_BUILDCONF_NAME generates an error.
    """
    all_except_any_build_name = dict_subtract(
        ALL_REQ_ENV_VARS, ('BUILD_NAME', 'TEAMCITY_BUILDCONF_NAME'))

    with only_these_environment_variables_set(all_except_any_build_name):
        collect_env_info()


def test_all_required_set_except_build_name():
    """
    Test that all required environment variables being set except
    BUILD_NAME is happy.
    """
    all_except_build_name = dict_subtract(ALL_REQ_ENV_VARS, 'BUILD_NAME')

    with only_these_environment_variables_set(all_except_build_name):
        env_info = collect_env_info()

    validate_env_info_against_ideal(
        actual=env_info,
        expected=expected_using_teamcity_buildconf_name)


def test_all_required_set_except_teamcity_buildconf_name():
    """
    Test that all required environment variables being set except
    TEAMCITY_BUILDCONF_NAME is happy.
    """
    all_but_teamcity_buildconf_name = dict_subtract(
        ALL_REQ_ENV_VARS, 'TEAMCITY_BUILDCONF_NAME')

    with only_these_environment_variables_set(all_but_teamcity_buildconf_name):
        env_info = collect_env_info()

    validate_env_info_against_ideal(
        actual=env_info,
        expected=expected_using_build_name)


@raises(ValueError)
def test_non_integer_build_number():
    """
    Test that all required environment variables being set except
    BUILD_NUMBER generates an error.
    """
    all_set_with_non_int_build_num = dict(ALL_REQ_ENV_VARS)
    all_set_with_non_int_build_num['BUILD_NUMBER'] = 'foo'

    with only_these_environment_variables_set(all_set_with_non_int_build_num):
        collect_env_info()


def test_custom_build_agent_name():
    """
    Test that setting a custom BUILD_AGENT_NAME works.
    """
    custom_build_agent_name = 'Agent Smith'

    env = dict(
        ALL_REQ_ENV_VARS.items() + [
            ('BUILD_AGENT_NAME', custom_build_agent_name)])

    with only_these_environment_variables_set(env):
        env_info = collect_env_info()

    eq_(env_info.build_agent_name, custom_build_agent_name)


###############################################################################
######################################################### Test Helper Utilities

def no_environment_variables_set():
    return StashEnviron()


def only_these_environment_variables_set(variables):
    return StashEnviron(variables)


class StashEnviron(object):
    def __init__(self, temp_vars=None):
        self.__temp_vars = temp_vars or {}

    def __enter__(self):
        self.__environ = os.environ
        os.environ = self.__temp_vars

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.environ = self.__environ


def dict_subtract(dictionary, keys_to_subtract):
    d = dict(dictionary)
    if isinstance(keys_to_subtract, basestring):
        keys_to_subtract = (keys_to_subtract,)
    for k in keys_to_subtract:
        del d[k]
    return d


ALL_REQ_ENV_VARS = {
    'MAJOR_VERSION': '5',
    'MINOR_VERSION': '5',
    'BUILD_NUMBER': '5',
    'BUILD_NAME': 'Foo',
    'TEAMCITY_BUILDCONF_NAME': 'Bar'}

ideal = ALL_REQ_ENV_VARS
ideal_build_version = '{}.{}.{}'.format(
    ideal['MAJOR_VERSION'], ideal['MINOR_VERSION'], ideal['BUILD_NUMBER'])
ideal_build_number = int(ideal['BUILD_NUMBER'])
ideal_build_agent_name = 'TeamCity'
ideal_build_agent_version = None

expected_using_build_name = EnvInfo(
    build_version=ideal_build_version,
    build_number=ideal_build_number,
    build_agent_name=ideal_build_agent_name,
    build_agent_version=ideal_build_agent_version,
    build_name=ideal['BUILD_NAME'])

expected_using_teamcity_buildconf_name = EnvInfo(
    build_version=ideal_build_version,
    build_number=ideal_build_number,
    build_agent_name=ideal_build_agent_name,
    build_agent_version=ideal_build_agent_version,
    build_name=ideal['TEAMCITY_BUILDCONF_NAME'])


def validate_env_info_against_ideal(actual, expected):
    eq_(actual.build_version, expected.build_version)
    eq_(actual.build_number, expected.build_number)
    eq_(actual.build_agent_name, expected.build_agent_name)
    eq_(actual.build_agent_version, expected.build_agent_version)
    eq_(actual.build_name, expected.build_name)

########NEW FILE########
__FILENAME__ = iso_time_tests
from datetime import datetime
from nose.tools import eq_
from daf_fruit_dist.iso_time import ISOTime
from mock import Mock


now_mock = Mock()
now_mock.return_value = datetime(2013, 4, 11, 11, 10, 46, 302000)


def _create_time_mock(daylight_savings):
    time_mock = Mock()
    time_mock.altzone = 82800   # +23 hours
    time_mock.timezone = 79200  # +22 hours
    time_mock.daylight = daylight_savings
    return time_mock


def test_daylight_savings_on():
    expected_result = '2013-04-11T11:10:46.302-2300'
    time_mock = _create_time_mock(daylight_savings=True)
    actual_result = ISOTime.now(now_fn=now_mock, time=time_mock).as_str
    eq_(actual_result, expected_result)


def test_daylight_savings_off():
    expected_result = '2013-04-11T11:10:46.302-2200'
    time_mock = _create_time_mock(daylight_savings=False)
    actual_result = ISOTime.now(now_fn=now_mock, time=time_mock).as_str
    eq_(actual_result, expected_result)

########NEW FILE########
__FILENAME__ = pip_package_path_finder_tests
import re
from nose.plugins.attrib import attr
from nose.tools import raises, eq_
from pip.exceptions import DistributionNotFound
import pkg_resources
from daf_fruit_dist.build.constants import PYTHON_GROUP_ID
from daf_fruit_dist.pip_package_path_finder import \
    PipPackagePathFinder, \
    _requirement_finder


@attr("integration")
def test_available_package_and_version():
    ################
    #Assemble test fixtures
    finder = PipPackagePathFinder()

    ############
    #Execute unit under test
    observed_file_path = finder.determine_file_path(
        pkg_name="nose",
        pkg_version="1.2.1")

    ###########
    #Assert results
    match_regex = r"{}/nose/nose.*1\.2\.1.*".format(PYTHON_GROUP_ID)
    path_as_expected = re.match(match_regex, observed_file_path)

    assert path_as_expected, \
        "match_regex: {} should match observed_file_path: {}".format(
            match_regex, observed_file_path)


@attr("integration")
@raises(DistributionNotFound)
def test_unavailable_version():
    finder = PipPackagePathFinder()
    finder.determine_file_path(pkg_name="nose", pkg_version="999.999.999")


@attr("integration")
@raises(DistributionNotFound)
def test_unavailable_package():
    finder = PipPackagePathFinder()
    finder.determine_file_path(
        pkg_name="non-existent-pkg-1234",
        pkg_version="1.2.1")


class FinderStub(object):
    def __init__(self, expected_reqs_and_rv_pairs):
        self.expected = FinderStub._parse_expected_reqs(
            expected_reqs_and_rv_pairs)
        self.times_called = 0

    @staticmethod
    def _parse_expected_reqs(expected_reqs_and_rv_pairs):
        expected_list = []

        for desired_req_str, return_value in expected_reqs_and_rv_pairs:
            expected_list.append((pkg_resources.Requirement.parse(
                desired_req_str), return_value))

        return tuple(expected_list)

    def find_requirement(self, req, upgrade):
        desired_req, return_value = self.expected[self.times_called]
        eq_(req.req, desired_req)

        self.times_called += 1

        if return_value is None:
            raise DistributionNotFound()
        else:
            return return_value


@raises(DistributionNotFound)
def test_nothing_matches():
    finder = FinderStub(expected_reqs_and_rv_pairs=(
        ('some-package_name==1.2.0', None),
        ('some-package-name==1.2.0', None),
        ('some_package_name==1.2.0', None),
    ))

    _requirement_finder(finder=finder, req_str='some-package_name==1.2.0')


def test_first_try_matches():
    dummy_link = 'dummy link'
    real_package_string = 'some-package_name==1.2.0'

    finder = FinderStub(expected_reqs_and_rv_pairs=(
        (real_package_string, dummy_link),
    ))

    actual_result = _requirement_finder(
        finder=finder,
        req_str=real_package_string)

    eq_(actual_result, dummy_link)


def test_second_try_matches():
    dummy_link = 'dummy link'
    real_package_string = 'some-package_name==1.2.0'

    finder = FinderStub(expected_reqs_and_rv_pairs=(
        (real_package_string, None),
        ('some-package-name==1.2.0', dummy_link),
    ))

    actual_result = _requirement_finder(
        finder=finder,
        req_str=real_package_string)

    eq_(actual_result, dummy_link)


def test_third_try_matches():
    dummy_link = 'dummy link'
    real_package_string = 'some-package_name==1.2.0'

    finder = FinderStub(expected_reqs_and_rv_pairs=(
        (real_package_string, None),
        ('some-package-name==1.2.0', None),
        ('some_package_name==1.2.0', dummy_link),
    ))

    actual_result = _requirement_finder(
        finder=finder,
        req_str=real_package_string)

    eq_(actual_result, dummy_link)

########NEW FILE########
__FILENAME__ = url_utils_tests
from nose.tools import eq_, raises
from daf_fruit_dist.url_utils import subtract_index_url


def validate_subtract_index_url(index_url, pkg_url, expected_tail):
    pip_tail = subtract_index_url(index_url=index_url, pkg_url=pkg_url)
    eq_(pip_tail, expected_tail)


@raises(RuntimeError)
def validate_subtract_index_url_failure(index_url, pkg_url):
    subtract_index_url(index_url=index_url, pkg_url=pkg_url)


def test_subtract_index_url_happy_path():
    index_url_pkg_url_pip_tail_tuples = (
        ('http://artifactory.defendagainstfruit.com:801'
         '/artifactory/team-fruit/python',
         'http://artifactory.defendagainstfruit.com:801'
         '/artifactory/team-fruit/python/nose/nose-1.2.1.tar.gz',
         'nose/nose-1.2.1.tar.gz'),

        ('http://artifactory.defendagainstfruit.com:801'
         '/artifactory/team-fruit/python/',
         'http://artifactory.defendagainstfruit.com:801'
         '/artifactory/team-fruit/python/nose/nose-1.2.1.tar.gz',
         'nose/nose-1.2.1.tar.gz'),

        ('http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python',
         'http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python/nose/nose-1.2.1.tar.gz',
         'nose/nose-1.2.1.tar.gz'),

        ('http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python/',
         'http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python/nose/nose-1.2.1.tar.gz',
         'nose/nose-1.2.1.tar.gz'),

        ('http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python',
         'http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python/nose-1.2.1.tar.gz',
         'nose-1.2.1.tar.gz'),

        ('http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python/',
         'http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python/nose-1.2.1.tar.gz',
         'nose-1.2.1.tar.gz'),

        ('http://artifactory.defendagainstfruit.com'
         '/team-fruit/python',
         'http://artifactory.defendagainstfruit.com'
         '/team-fruit/python/nose/nose-1.2.1.tar.gz',
         'nose/nose-1.2.1.tar.gz'),

        ('https://artifactory.defendagainstfruit.com:801'
         '/artifactory/team-fruit/python',
         'https://artifactory.defendagainstfruit.com:801'
         '/artifactory/team-fruit/python/nose/nose-1.2.1.tar.gz',
         'nose/nose-1.2.1.tar.gz')
    )
    for index_url, pkg_url, expected_tail in index_url_pkg_url_pip_tail_tuples:
        yield validate_subtract_index_url, index_url, pkg_url, expected_tail


def test_subtract_index_url_unhappy_path():
    index_url_pkg_url_tuples = (
        ('http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/ugly',
         'http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python/nose/nose-1.2.1.tar.gz'),

        ('http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python',
         'http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python'),

        ('http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python/',
         'http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python'),

        ('http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python',
         'http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python/'),

        ('artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python',
         'http://artifactory.defendagainstfruit.com'
         '/artifactory/team-fruit/python/nose/nose-1.2.1.tar.gz'),

        ('ladies and gentlemen',
         'hobos and tramps')
    )
    for index_url, pkg_url in index_url_pkg_url_tuples:
        yield validate_subtract_index_url_failure, index_url, pkg_url

########NEW FILE########
__FILENAME__ = utils_test
def typical_test():
    assert True, "Testing is fun"

########NEW FILE########
__FILENAME__ = url_utils
def subtract_index_url(index_url, pkg_url):
    """Subtract index_url from pkg_url and return remainder."""
    found_index = pkg_url.find(index_url)

    if found_index != 0:
        raise RuntimeError(
            "pkg_url of {pkg_url} does not start with index_url of "
            "{index_url}".format(
                index_url=index_url,
                pkg_url=pkg_url))
    else:
        tail = pkg_url[len(index_url):]

    stripped_tail = tail.lstrip('/')

    if not stripped_tail:
        raise RuntimeError(
            "pkg_url of {pkg_url} and index_url of {index_url} are "
            "effectively identical.".format(
                index_url=index_url,
                pkg_url=pkg_url))

    return stripped_tail

########NEW FILE########
__FILENAME__ = version_utils
import os

_DEFAULT_MAJOR_REVISION = 1
_DEFAULT_MINOR_REVISION = 1
_DEFAULT_BUILD_NUMBER = 0


class VersionUtils(object):
    def __init__(self, basedir=None):
        super(VersionUtils, self).__init__()
        self.basedir = basedir or os.getcwd()
        self.version_file = os.path.join(
            os.path.abspath(basedir), 'version.txt')

    def write_version(
            self,
            major_version=None,
            minor_version=None,
            build_number=None):

        if major_version is None:
            major_version = os.environ.get(
                'MAJOR_VERSION', _DEFAULT_MAJOR_REVISION)
        if minor_version is None:
            minor_version = os.environ.get(
                'MINOR_VERSION', _DEFAULT_MINOR_REVISION)
        if build_number is None:
            build_number = os.environ.get(
                'BUILD_NUMBER', _DEFAULT_BUILD_NUMBER)

        version = '{}.{}.{}'.format(major_version, minor_version, build_number)

        with open(self.version_file, "w") as f:
            f.write(version)

        return version

    def read_version(self):
        return self._read_text(self.version_file)

    def _read_text(self, filename):
        return (
            unicode(open(filename).read())
            if os.path.exists(filename)
            else None)

########NEW FILE########
__FILENAME__ = continuous_integration
import os
import sys


def integrate():
    # From the newly-included 'daf_fruit_dist' module, import the
    # standard CI run.
    from daf_fruit_dist.ci_utils import standard_sdist_run

    # Test this package, then create a source distribution of it.
    standard_sdist_run()


if __name__ == '__main__':
    # Change active directories to the one containing this file.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Include the co-bundled 'daf_fruit_dist' module in the search path.
    sys.path.insert(0, os.path.abspath(os.path.join('..', 'daf_fruit_dist')))

    integrate()

########NEW FILE########
__FILENAME__ = example_test
def test_typical_usage():
    pass

########NEW FILE########
__FILENAME__ = virtualenv_util
import argparse
import glob
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from textwrap import dedent

VIRTUALENV_PACKAGE_NAME = 'virtualenv'
VIRTUALENV_BOOTSTRAP_NAME = 'virtualenv-bootstrap'
VIRTUALENV_UTIL_PACKAGE_NAME = 'daf_fruit_orchard'

if sys.version_info >= (3, 0):
    # noinspection PyUnresolvedReferences
    import configparser
    # noinspection PyUnresolvedReferences
    import urllib.request as urllib
    # noinspection PyUnresolvedReferences
    import urllib.parse as urlparse
else:
    # noinspection PyUnresolvedReferences
    import ConfigParser as configparser
    # noinspection PyUnresolvedReferences
    import urllib2 as urllib
    # noinspection PyUnresolvedReferences
    import urlparse


def version():
    try:
        return open(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..',
                'version.txt'),
            'r').read()
    except IOError:
        return None


def get_python_version_string():
    return '{:d}.{:d}.{:d}'.format(
        sys.version_info[0],
        sys.version_info[1],
        sys.version_info[2])


def get_options_from_config_file_and_args(
        config_file_path=None,
        options_overrides=None):

    if options_overrides is None:
        options_overrides = {}

    if config_file_path is None and options_overrides.get('cfg_file', None):
        config_file_path = options_overrides['cfg_file']

    if config_file_path is not None:
        config = configparser.SafeConfigParser()
        config.read([config_file_path])
        config_file_global_settings = dict(config.items("global"))
    else:
        config_file_global_settings = {}

    parser = argparse.ArgumentParser(
        description='Setup and update a Python virtualenv for a firmware view')
    parser.add_argument(
        '--clean', '--veclean', action='store_true')
    parser.add_argument(
        '--run', default=None)
    parser.add_argument(
        '--script', default=None)
    parser.add_argument(
        '--noupdate', '--venoupdate', '-`', action='store_true')
    parser.add_argument(
        '--quiet', action='store_true')
    parser.add_argument(
        '--requirements_file', '-r', default=None)
    parser.add_argument(
        '--requirement_specifiers', default=None)
    parser.add_argument(
        '--installed_list_file', default=None)
    parser.add_argument(
        '--environment_variables', default={})
    parser.add_argument(
        '--pypi_pull_server', default='http://pypi.python.org/simple')
    parser.add_argument(
        '--pypi_pull_repo_id', default=None)
    parser.add_argument(
        '--pypi_push_server', default=None)
    parser.add_argument(
        '--pypi_push_username', default=None)
    parser.add_argument(
        '--pypi_push_password', default=None)
    parser.add_argument(
        '--pypi_push_repo_id', default=None)
    parser.add_argument(
        '--pypi_push_no_cert_verify', default=False)
    parser.add_argument(
        '--pypi_server_base', default=None)
    parser.add_argument(
        '--virtualenv_path', default='./_python_virtualenv')
    parser.add_argument(
        '--virtualenv_version', default=None)
    parser.add_argument(
        '--python_version', default=get_python_version_string())
    parser.add_argument(
        '--pip_install_args', default='--upgrade')
    parser.add_argument(
        '--download_dir', default=None)
    parser.add_argument(
        '--download_cache_dir', default=None)
    # Force type=bool since the config file will be a string
    parser.add_argument(
        '--sitepkg_install', type=int, default=0)
    parser.add_argument(
        '--helper_scripts', action='store_true', default=False)
    parser.set_defaults(**config_file_global_settings)

    if options_overrides.get('dont_parse_argv', False):
        # Don't actually parse anything from the command line if this
        # option override is set.
        options = parser.parse_args([])
    else:
        options = parser.parse_args()

    options.cfg_file = config_file_path

    if options.requirements_file is None:
        options.requirements_file = config_file_global_settings.get('', None)

    for key in options_overrides:
        setattr(options, key, options_overrides[key])

    update_path_options(options)

    return options


def update_path_options(options):
    path_options = [
        'virtualenv_path',
        'requirements_file',
        'installed_list_file']

    # If a config file is specified, paths should be relative to that.
    # Otherwise, paths should be relative to this file.
    root_path = (
        os.path.dirname(os.path.abspath(options.cfg_file))
        if options.cfg_file
        else os.path.dirname(os.path.abspath(__file__)))

    for path_option in path_options:
        if getattr(options, path_option, None) is not None:
            value = getattr(options, path_option)

            if value.startswith('.'):
                # relative path
                setattr(
                    options,
                    path_option,
                    os.path.abspath(os.path.join(root_path, value)))
            else:
                # absolute path
                setattr(options, path_option, os.path.abspath(value))

# TODO: Is this function ever called?


def parse_requirements_file(requirements_file_path, options):
    if not os.path.isfile(requirements_file_path):
        raise RuntimeError(
            'Requirements file {} is missing!'.format(requirements_file_path))

    python_version = None
    virtualenv_package_name = None
    virtualenv_version = None

    for line in file(requirements_file_path).readlines():
        if line.startswith('#python'):
            python_version = line.split('==')[1].strip()
        elif line.startswith('virtualenv'):
            virtualenv_package_name, virtualenv_version = line.split('==')
            virtualenv_package_name = virtualenv_package_name.strip()
            virtualenv_version = virtualenv_version.strip()

    if python_version is None:
        raise RuntimeError(
            'Requirements file {} does not list required python '
            'version!'.format(requirements_file_path))

    if virtualenv_package_name is None or virtualenv_version is None:
        raise RuntimeError(
            'Requirements file {} does not list required virtualenv '
            'package!'.format(requirements_file_path))

    return python_version, virtualenv_package_name, virtualenv_version


def handle_remove_readonly(func, path, exc):
    if func in (os.rmdir, os.remove):
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
        func(path)
    else:
        raise


def _install_req(tarball):
    '''Used to install distribute or pip to site-packages from the given
    source dist tarball.
    '''
    cwd = os.getcwd()
    # Copy to a temp directory
    d = tempfile.mkdtemp()
    t = None
    try:
        # Unpack to the temp dir
        t = tarfile.open(tarball, 'r:gz')
        t.extractall(d)
        # Change to extracted directory, and install (expect only 1 directory)
        extract_dir = os.listdir(d)[0]
        unpack_dir = os.path.join(d, extract_dir)
        os.chdir(unpack_dir)
        # Make sure setup.py exists
        if not os.path.isfile('setup.py'):
            raise RuntimeError(
                'Could not find setup.py for {}'.format(tarball))
        # Finally, run the installer
        print 'Running setup.py for {}'.format(tarball)
        with open(os.devnull, 'w') as tempf:
            subprocess.check_call(
                [sys.executable, 'setup.py', 'install'],
                stdout=tempf)
    finally:
        if t:
            t.close()
        os.chdir(cwd)
        shutil.rmtree(d)


def do_sitepkg_install(options):
    '''Install user specifications to local site-packages.
    '''
    # Set this to None in case it fails to get set in the try block
    temp_dir = None
    try:
        # Get the virtualenv package which has distribute and pip that we
        # will install to site-packages
        temp_dir = _stage_virtualenv(options, install_virtualenv=False)

        # Use the bootstrap virtualenv to install distribute and pip to
        # site-packages. We expect those packages to be in virtualenv_support.
        distribute_src = glob.glob(os.path.join(
            temp_dir, 'virtualenv-*/virtualenv_support/distribute-*.tar.gz'))
        pip_src = glob.glob(os.path.join(
            temp_dir, 'virtualenv-*/virtualenv_support/pip-*.tar.gz'))
        # Expect only one to be there
        if len(distribute_src) != 1 or len(pip_src) != 1:
            raise RuntimeError(
                'Expect exactly one version of distribute and '
                'pip in virtualenv_support. Found {}, {}'.format(
                    distribute_src, pip_src))
        # Install them both to site-packages
        _install_req(distribute_src[0])
        _install_req(pip_src[0])
    finally:
        if temp_dir:
            # Clean up the temp. virtual environment.
            pass  # _cleanup_virtualenv(temp_dir)


def do_virtualenv_install(options):
    print(
        'Creating new virtual environment at {}...'.format(
            options.virtualenv_path))

    # Remove any old virtualenv that may be sitting in the target virtualenv
    # directory.
    if os.path.isdir(options.virtualenv_path):
        shutil.rmtree(
            options.virtualenv_path,
            ignore_errors=False,
            onerror=handle_remove_readonly)

    # Set this to None in case it fails to get set in the try block
    temp_dir = None
    try:
        # Stage a virtual environment that will perform the real install
        temp_dir = _stage_virtualenv(options)
        bootstrap_vm_dir = os.path.join(temp_dir, VIRTUALENV_BOOTSTRAP_NAME)
        arguments = [
            os.path.join(
                bootstrap_vm_dir,
                'Scripts',
                'virtualenv'),
            '--distribute',
            options.virtualenv_path]

        # Use the bootstrap virtualenv to create the "real" virtualenv in the
        # view at the right location.
        # We have to be careful to get the python version correct this time.
        try:
            if options.quiet:
                subprocess.check_output(arguments, shell=True)
            else:
                subprocess.check_call(arguments, shell=True)
        except subprocess.CalledProcessError as e:
            if options.quiet:
                print e.output
            print ('Real virtual environment create fail, '
                   'return code {}'.format(e.returncode))
            raise
    finally:
        if temp_dir:
            # Clean up the temp. virtual environment.
            _cleanup_virtualenv(temp_dir)


def _get_newest_package_version_and_url(
        pypi_server, package_name, package_extension='.tar.gz'):
    '''Utility function that searches the pypi_server specified for
    the latest version of the package with the name specified.
    Will return the version of the newest package found and the
    url to the package file on the server.
    '''

    # If we are getting our packages from the local filesystem, we
    # need to get the directory listing specially.
    if urlparse.urlparse(pypi_server).scheme == 'file':
        filenames = os.listdir(urlparse.urlparse(pypi_server).path.lstrip('/'))
        url_dir = pypi_server
    else:
        url_dir = pypi_server + '/' + package_name

        try:
            f_remote = urllib.urlopen(url_dir)
            index = f_remote.read()

        # If we get a URL error, try the special case of a "flat"
        # directory structure.
        except urllib.URLError:
            url_dir = pypi_server

            f_remote = urllib.urlopen(url_dir)
            index = f_remote.read()

        # Very simple regex parser that finds all hyperlinks in the index
        # HTML... this may break in some cases, but we want to keep it super
        # simple in the bootstrap.
        filenames = re.findall('href="(.*?)"', str(index.lower()))

    # Get all hyperlinks that start with the virtualenv package name
    # and end with the package extension.
    versions = []
    for filename in filenames:
        looks_like_package = (
            filename.startswith(package_name + '-') and
            filename.endswith(package_extension))

        if looks_like_package:
            version = filename.split('-')[-1].replace(package_extension, '')
            versions.append(version)

    # Sort the versions from lowest to highest.
    # NOTE: This simple sort will work for most versions we expect to
    # use in the virtualenv_util package.  This could be enhanced.
    versions.sort()

    # Select the highest version.
    # Select the highest version.
    try:
        highest_version = versions[-1]
    except IndexError:
        raise RuntimeError(
            'Unable to find any version of package {} at URL {}'.format(
                package_name, pypi_server))

    return highest_version, '/'.join([
        url_dir,
        '{}-{}{}'.format(package_name, highest_version, package_extension)])


def _stage_virtualenv(options, install_virtualenv=True):
    '''Creates staging virtual environment in order to help with the "real"
    installation. Returns path to staged virtual env. If install_virtualenv is
    False, then unpack the virtual env. package, but don't actually create
    a virtual environment.
    '''
    # Create a temporary directory to put the virtual env. in.
    temp_dir = tempfile.mkdtemp()
    try:
        # Was a fixed virtualenv version specified?  If not, we need to check
        # the PyPI server for the latest version.
        if options.virtualenv_version is None:
            options.virtualenv_version, virtualenv_url = (
                _get_newest_package_version_and_url(
                    options.pypi_pull_server,
                    options.virtualenv_package_name))
        else:
            virtualenv_url = '/'.join([
                options.pypi_pull_server,
                options.virtualenv_package_name,
                '{}-{}.tar.gz'.format(
                    options.virtualenv_package_name,
                    options.virtualenv_version)])

        virtualenv_tar_filename = os.path.basename(
            urlparse.urlparse(virtualenv_url).path)

        f_remote = urllib.urlopen(virtualenv_url)
        f_local = open(os.path.join(temp_dir, virtualenv_tar_filename), 'wb')
        f_local.write(f_remote.read())
        f_local.close()

        # If a download dir or download cache directory was specified,
        # copy the virtualenv package file to that directory if it is not
        # already there.
        for directory in [options.download_dir, options.download_cache_dir]:
            if directory is None:
                directory = ''

            virtualenv_tar_exists = os.path.isfile(
                os.path.join(directory, virtualenv_tar_filename))

            if directory and not virtualenv_tar_exists:
                shutil.copy2(
                    os.path.join(temp_dir, virtualenv_tar_filename),
                    directory)

        # Unpack the tarball to the temporary directory.
        tarf = tarfile.open(
            os.path.join(temp_dir, virtualenv_tar_filename),
            'r:gz')
        tarf.extractall(temp_dir)
        tarf.close()
        unpacked_tar_directory = os.path.join(
            temp_dir, virtualenv_tar_filename.replace('.tar.gz', ''))
        bootstrap_vm_directory = os.path.join(
            temp_dir, VIRTUALENV_BOOTSTRAP_NAME)
        # Create the bootstrap virtualenv in the temporary directory using the
        # current python executable we are using plus the virtualenv stuff we
        # unpacked.
        if install_virtualenv:
            arguments = [sys.executable,
                         os.path.join(unpacked_tar_directory, 'virtualenv.py'),
                         '--distribute',
                         bootstrap_vm_directory]
            try:
                if options.quiet:
                    subprocess.check_output(arguments, shell=True)
                else:
                    subprocess.check_call(arguments, shell=True)
            except subprocess.CalledProcessError as e:
                if options.quiet:
                    print e.output
                print 'Bootstrap VM create failed, return code', e.returncode
                raise

            # Get the right options to pass to pip to install virtualenv
            # to the bootstrap environment.  Again, this is necessary because
            # pip does not support file:// index urls.
            if urlparse.urlparse(options.pypi_pull_server).scheme == 'file':
                install_options = [
                    '--no-index',
                    '--find-links',
                    options.pypi_pull_server]

            else:
                install_options = [
                    '-i',
                    options.pypi_pull_server]

            # Install virtualenv into this bootstrap environment using pip,
            # pointing at the right server.
            subprocess.check_call(
                [
                    os.path.join(bootstrap_vm_directory, 'Scripts', 'pip'),
                    'install'
                ]
                + install_options
                + [
                    '{}=={}'.format(
                        options.virtualenv_package_name,
                        options.virtualenv_version)
                ])

    except Exception:
        # Even though the calling code is normally responsible for cleaning
        # up the temp dir, if an exception occurs, we do it here because we
        # won't be able to return the temp_dir to the caller
        _cleanup_virtualenv(temp_dir)
        raise

    # Return the bootstrap vm dir that was created
    return temp_dir


def _cleanup_virtualenv(temp_dir):
    '''Cleans up the temp virtual folder and environment created by
    _stage_virtualenv().
    '''
    print('Cleaning up bootstrap environment')

    shutil.rmtree(
        temp_dir,
        ignore_errors=False,
        onerror=handle_remove_readonly)


def _write_pip_config(home_dir, options):
    virtualenv_util = os.path.basename(__file__)
    additional_global_options = ''

    # Pip is not happy with an index-url that is on the local filesystem
    # (i.e. file://).  It would be cool if pip would be enhanced to handle
    # this someday, but for now, we need to pass these things to pip via
    # the find-links option.
    if urlparse.urlparse(options.pypi_pull_server).scheme == 'file':
        additional_global_options = 'no_index=true\nfind_links={}'.format(
            options.pypi_pull_server)

    #
    # Create pip.ini
    pip_ini = dedent('''
        # This file was auto-generated by "{virtualenv_util}" from
        # "{virtualenv_util_cfg}".

        [global]
        index-url={index_url}
        {additional_global_options}

        [install]
        use-wheel=true
        ''').strip()

    pip_ini_contents = pip_ini.format(
        virtualenv_util=virtualenv_util,
        virtualenv_util_cfg=options.cfg_file,
        index_url=options.pypi_pull_server,
        additional_global_options=additional_global_options)

    _write_config_file(
        home_dir=home_dir,
        home_file_name='pip\pip.ini',
        contents=pip_ini_contents)


def _write_pydistutils_cfg(home_dir, options):
    virtualenv_util = os.path.basename(__file__)

    #
    # Create pydistutils.cfg
    pydistutils_cfg = dedent('''
        # This file was auto-generated by "{virtualenv_util}" from
        # "{virtualenv_util_cfg}".

        [easy_install]
        index_url={index_url}

        [artifactory]
        # Used for Artifactory API calls.
        repo_base_url={repo_base_url}
        repo_push_id={repo_push_id}
        repo_pull_id={repo_pull_id}
        username={username}
        password={password}
        no_cert_verify={no_cert_verify}

        [module_generator]
        no-cert-verify={no_cert_verify}
        ''').strip()

    pydistutils_cfg_contents = pydistutils_cfg.format(
        virtualenv_util=virtualenv_util,
        virtualenv_util_cfg=options.cfg_file,
        index_url=options.pypi_pull_server,
        repo_base_url=options.pypi_server_base,
        repo_push_id=options.pypi_push_repo_id,
        repo_pull_id=options.pypi_pull_repo_id,
        username=options.pypi_push_username,
        password=options.pypi_push_password,
        no_cert_verify='1' if options.pypi_push_no_cert_verify else '0')

    _write_config_file(
        home_dir=home_dir,
        home_file_name='pydistutils.cfg',
        contents=pydistutils_cfg_contents)


def _get_implicit_versions_string(options):
    s = '# __python=={}\n'.format(get_python_version_string())
    s += '# __{}=={}\n'.format(
        options.virtualenv_package_name,
        options.virtualenv_version)
    v = version()
    if v:
        s += '# __{}=={}\n'.format(VIRTUALENV_UTIL_PACKAGE_NAME, v)
    return s


def _write_version_file(home_dir, options):
    '''Write out some package version information to a text file in the home
    directory.'''

    home_versions_file_path = os.path.join(home_dir, 'virtualenv_versions.txt')
    f = open(home_versions_file_path, 'w')
    f.write(_get_implicit_versions_string(options))
    f.close()


def _create_env_file(home_dir, environment_variables):
    '''Create a file containing all the environment variable settings that
    should be made each time the virtual environment is used'''

    environment_variables['HOME'] = home_dir

    home_env_file_path = os.path.join(home_dir, '.env')
    if not os.path.isfile(home_env_file_path):
        with open(home_env_file_path, 'w') as f:
            f.write('[environment_variables]\n')
            for name in environment_variables.keys():
                f.write('{}={}\n'.format(name, environment_variables[name]))


def _populate_home_dir(options):
    if options.sitepkg_install:
        # For a sitepkg install, we need to write the config files in the
        # the correct system locations.
        # TODO: We could write to the user's %HOME% env variable, but it's
        # TODO: a pain to get it to persist. We've done this in ratools using
        # TODO: the _winreg and win32gui libraries, but win32gui is a third
        # TODO: party module that I'm not sure we want to try and install
        _write_pip_config(os.path.expanduser('~'), options)
        _write_pydistutils_cfg(os.path.join(
            sys.prefix, 'Lib/distutils/pydistutils.cfg'), options)
    else:
        # For a virtual env. install, we can neatly create a home directory
        # and put the config files there.
        home_dir = os.path.join(options.virtualenv_path, 'home')
        options.environment_variables['HOME'] = home_dir
        if not os.path.isdir(home_dir):
            os.mkdir(home_dir)
        _write_pip_config(home_dir, options)
        _write_pydistutils_cfg(home_dir, options)
        _create_env_file(
            home_dir=home_dir,
            environment_variables=options.environment_variables)
        _write_version_file(home_dir=home_dir, options=options)


def _write_config_file(home_dir, home_file_name, contents):
    home_file_path = os.path.join(home_dir, home_file_name)

    if not os.path.isdir(os.path.dirname(home_file_path)):
        os.makedirs(os.path.dirname(home_file_path))

    # TODO: Don't we want to overwrite this file? For now, I changed it do
    # overwrite. Not sure if/how we want to persist user changes, unless we
    # just write parts of the file we're concerned about.
    # if not os.path.isfile(home_file_path):
    with open(home_file_path, 'w') as f:
        f.write(contents)


def _get_pip_install_args(options):
    args = shlex.split(options.pip_install_args, posix=False)

    if options.download_cache_dir:
        args += ['--download-cache="{}"'.format(options.download_cache_dir)]

    if options.download_dir:
        args += ['--download="{}"'.format(options.download_dir)]

    return args


def _fix_download_cache_dir_filenames(options):
    for item in os.listdir(options.download_cache_dir):
        file_exists = os.path.isfile(
            os.path.join(options.download_cache_dir, item))

        if file_exists and '%2F' in item:
            shutil.move(
                os.path.join(
                    options.download_cache_dir, item),
                os.path.join(
                    options.download_cache_dir, item.split('%2F')[-1]))


def _create_ve_helper_scripts(options):
    '''This function drops some files that are useful for dealing with
    the virtual environment that was created in the root directory of
    the ve.  The files are platform specific since they need to make
    changes to the environment, among other things.

    Think of this as a lite version of virtualenvwrapper, without having
    to have a special package installed in your global site-packages,
    and without the restrictions on where / how your virtualenvs can be
    stored.'''

    # If we installed to the global site-packages (i.e. we didn't make a
    # virtualenv) then there is nothing to do.
    if options.sitepkg_install:
        return

    if os.name == 'nt':
        # Batch file to activate the virtualenv.  This does a little extra
        # magic, like restoring our environment variables
        f = open(os.path.join(options.virtualenv_path, 'activate.bat'), 'w')
        f.write(dedent(r'''
                @echo off
                %~dp0\Scripts\virtualenv_util_make_platform_helpers
                call %~dp0\home\virtualenv_util_activate.bat
                %~dp0\Scripts\activate.bat
                '''))
        f.close()

        # Batch file to deactivate the virtualenv.
        f = open(os.path.join(options.virtualenv_path, 'deactivate.bat'), 'w')
        f.write(dedent(r'''
                @echo off
                call %~dp0\home\virtualenv_util_deactivate.bat
                %~dp0\Scripts\deactivate.bat
                '''))
        f.close()

        # Batch file to open a command shell / prompt to the root of the
        # virtualenv, then activate it.  Good for messing around at the
        # command line.
        f = open(os.path.join(options.virtualenv_path, 'shell.bat'), 'w')
        f.write(dedent(r'''
                @echo off
                start cmd.exe /k "%~dp0\activate.bat"
                '''))
        f.close()
    else:
        print(
            'Creating virtualenv helper scripts not supported for OS {}, '
            'skipping'.format(os.name))


def read_and_update_environment_variables(options=None, home_dir=None):
    if home_dir is None and options:
        home_dir = os.path.join(options.virtualenv_path, 'home')

    home_env_file_path = os.path.join(home_dir, '.env')

    original_environment_variables = {}

    if not os.path.isfile(home_env_file_path):
        environment_variables = {}
    else:
        config = configparser.SafeConfigParser()
        config.read([home_env_file_path])
        environment_variables = dict(config.items("environment_variables"))

    for name in environment_variables.keys():
        if name.upper() in os.environ:
            original_environment_variables[name] = os.environ[name.upper()]
        else:
            original_environment_variables[name] = None

        os.environ[name.upper()] = environment_variables[name]

    return environment_variables, original_environment_variables


def make_platform_helpers():
    # Make sure we are running in a virtualenv...
    if not hasattr(sys, 'real_prefix'):
        return

    home_dir = os.path.join(sys.prefix, 'home')

    if not os.path.isdir(home_dir):
        return

    # Read the environment variables from the .env configuration file.
    new_env_vars, original_env_vars = read_and_update_environment_variables(
        home_dir=home_dir)

    if os.name == 'nt':
        f = open(os.path.join(home_dir, 'virtualenv_util_activate.bat'), 'w')
        for new_env_var in new_env_vars.keys():
            f.write(
                'set {}={}\n'.format(new_env_var.upper(),
                                     new_env_vars[new_env_var]))
        f.close()

        f = open(os.path.join(home_dir, 'virtualenv_util_deactivate.bat'), 'w')
        for original_env_var in original_env_vars.keys():
            if original_env_vars[original_env_var] is None:
                f.write('set {}=\n'.format(original_env_var.upper()))
            else:
                f.write(
                    'set {}={}\n'.format(original_env_var.upper(),
                                         original_env_vars[original_env_var]))
        f.close()


def _handle_run_script_nested_arguments(options):
    # Special case of "nested" arguments when doing a run or script.

    # Can pass in some arguments as an argument inside of --run or --script
    # and they will have the same effect as passing them directly to this
    # script.
    look_for_args = {
        '--veclean': 'clean',
        '--venoupdate': 'noupdate',
        '-`': 'noupdate',
        '--quiet': 'quiet'}

    run_script_args = (
        options.run
        if options.run is not None
        else options.script)

    # No --run or --script was specified.
    if run_script_args is None:
        return

    for look_for_arg in look_for_args.keys():
        if look_for_arg in run_script_args.split():
            setattr(options, look_for_args[look_for_arg], True)

        if options.run:
            options.run = options.run.replace(look_for_arg, '')

        if options.script:
            options.script = options.script.replace(look_for_arg, '')


def _exec_pip(options, pip_args=[], install=True, capture_output=False):
    # Choose the pip tool location based on if this is a virtualenv install
    # or a site-packages install
    if options.sitepkg_install:
        piptool = os.path.join(sys.prefix, 'Scripts', 'pip')
    else:
        piptool = os.path.join(options.virtualenv_path, 'Scripts', 'pip')

    if install:
        pip_args = ['install'] + _get_pip_install_args(options) + pip_args

    try:
        if options.quiet or capture_output:
            output = subprocess.check_output([piptool] + pip_args, shell=True)
        else:
            output = subprocess.check_call([piptool] + pip_args, shell=True)

    except subprocess.CalledProcessError as e:
        if options.quiet or capture_output:
            print e.output
        print('Error executing pip command {}, '
              'return code {}'.format(pip_args, e.returncode))
        raise

    if capture_output:
        return output


def main(config_file_path=None, options_overrides=None):
    if options_overrides is None:
        options_overrides = {}

    options = get_options_from_config_file_and_args(
        config_file_path, options_overrides)

    # Special case of "nested" arguments when doing a run or script.
    _handle_run_script_nested_arguments(options)

    # Set virtualenv package name to a default. Don't currently see a need
    # for this to be configurable
    options.virtualenv_package_name = VIRTUALENV_PACKAGE_NAME

    # If we are running from INSIDE a virtualenv already, assume that the
    # virtualenv already exists and we only need to update it.
    if hasattr(sys, 'real_prefix'):
        if options.sitepkg_install:
            raise RuntimeError(
                'Cannot install to site-packages from a virtual environment')
        # Otherwise, check that the version of Python in the virtualenv being
        # used is correct.  We cannot update this, so error if it is incorrect.
    else:
        # If the user wants a sitepkg install...
        if options.sitepkg_install:
            do_sitepkg_install(options)
        # Otherwise, we're giving them a virtualenv.
        # Does the virtualenv already exist?  If so, we just check to make
        # sure it is up to date.
        elif not options.clean and os.path.isfile(os.path.join(
                options.virtualenv_path, 'Scripts', 'python.exe')):
            # Check the version of Python in the virtualenv.  We cannot
            # update it after the virtualenv is created (we have to destroy and
            # recreate this virtualenv), so just show an error.
            pass
        else:
            do_virtualenv_install(options)

        # Write config files
        _populate_home_dir(options)

        if not options.sitepkg_install:
            read_and_update_environment_variables(options)

        if not options.noupdate:

            # Always install a copy of ourselves, even if no one asked for us.
            _exec_pip(
                options, ['{}=={}'.format(VIRTUALENV_UTIL_PACKAGE_NAME,
                          version())])

            # If requirements were specified as a list of requirements
            # specifiers separated by commas, install each package
            # individually.
            if options.requirement_specifiers:
                for requirement in options.requirement_specifiers.split(','):
                    _exec_pip(options, [requirement])

            # Run pip to install / update the required
            # tool packages listed in the requirements.txt file.
            if options.requirements_file:
                _exec_pip(options, ['-r', options.requirements_file])

        if options.installed_list_file:

            # Output the list of installed tools to a text file.
            output = _exec_pip(
                options,
                ['freeze'],
                install=False,
                capture_output=True)
            f = open(options.installed_list_file, 'w')
            f.write(_get_implicit_versions_string(options))
            f.write(output)
            f.close()

        if options.download_cache_dir:
            _fix_download_cache_dir_filenames(options)

        if options.helper_scripts:
            _create_ve_helper_scripts(options)

    if options.sitepkg_install:
        scripts_dir = os.path.join(sys.prefix, 'Scripts')
    else:
        scripts_dir = os.path.join(options.virtualenv_path, 'Scripts')

    if options.run is not None or options.script is not None:

        # Add Scripts directory to the path so those executables are
        # available to the item being executed.
        os.environ["PATH"] = scripts_dir + os.pathsep + os.environ["PATH"]

    if options.run is not None:
        if options.sitepkg_install:
            python_executable = sys.executable
        else:
            python_executable = os.path.join(scripts_dir, 'python.exe')

        args = [python_executable] + shlex.split(options.run, posix=False)

        sys.stdout.flush()
        sys.stderr.flush()
        returncode = subprocess.call(
            args,
            stdout=sys.stdout,
            stderr=sys.stderr)
        sys.stdout.flush()
        sys.stderr.flush()

        sys.exit(returncode)

    elif options.script is not None:

        # Run a script, assumed to be located in the Scripts directory.
        # Note that the script name cannot have any spaces using the logic
        # below.
        args = [os.path.join(scripts_dir, options.script.split()[0])]
        if len(options.script.split()) > 1:
            args += shlex.split(options.script.split(None, 1)[1], posix=False)

        # Note: Passing sys.stdout, sys.stderr explicitly to avoid issues with
        # missing output in some cases when output is redirected.
        # See http://comments.gmane.org/gmane.comp.python.buildbot.devel/2369.
        sys.stdout.flush()
        sys.stderr.flush()
        returncode = subprocess.call(
            args,
            stdout=sys.stdout,
            stderr=sys.stderr)
        sys.stdout.flush()
        sys.stderr.flush()

        sys.exit(returncode)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Create / update a Python virtualenv')
    parser.add_argument('--cfg_file')
    parsed, remaining_args = parser.parse_known_args(sys.argv[1:])
    sys.argv = [sys.argv[0]] + remaining_args

    main(parsed.cfg_file)

########NEW FILE########
__FILENAME__ = continuous_integration
import os
import sys


def integrate():
    # From the newly-included 'daf_fruit_dist' module, import the
    # standard CI run for a raw Python script.
    from daf_fruit_dist.ci_single_module_utils import standard_py_run

    # Execute the CI run against the bootstrap script.
    standard_py_run('virtualenv_util_bootstrap.py')


if __name__ == '__main__':
    # Change active directories to the one containing this file.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Include the co-bundled 'daf_fruit_dist' module in the search path.
    sys.path.insert(0, os.path.abspath(os.path.join('..', 'daf_fruit_dist')))

    integrate()

########NEW FILE########
__FILENAME__ = virtualenv_util_bootstrap
import imp
import os
import sys
if sys.version_info >= (3, 0):
    import configparser
    import urllib.request as urllib
    import urllib.parse as urlparse
else:
    import ConfigParser as configparser
    import urllib2 as urllib
    import urlparse
import argparse
import tarfile
import re
import shutil


ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_FILE_PATH = os.path.join(ROOT_PATH, 'virtualenv_util.cfg')
VIRTUALENV_UTIL_PACKAGE_NAME = 'daf_fruit_orchard'
VIRTUALENV_UTIL_PACKAGE_FILE_EXTENSION = '.tar.gz'
VIRTUALENV_UTIL_MODULE_NAME = 'virtualenv_util.py'


def _check_for_existing_package(
        bootstrap_directory,
        virtualenv_util_version=None):

    virtualenv_util_path = None

    # Look for something that appears like a virtualenv_util package
    # already in the bootstrap directory.  We do not attempt to re-bootstrap
    # (redownload the virtualenv_util package) if one of the correct version
    # already exists.
    for item in os.listdir(bootstrap_directory):
        possible_dir = os.path.join(
            bootstrap_directory,
            item,
            VIRTUALENV_UTIL_PACKAGE_NAME)

        item_looks_like_virtualenv_pkg = (
            item.startswith(VIRTUALENV_UTIL_PACKAGE_NAME))

        possible_dir_exists = os.path.isdir(possible_dir)

        if item_looks_like_virtualenv_pkg and possible_dir_exists:
            # Special case... if specific version was specified, make sure
            # it is the right version.
            is_correct_version = (
                virtualenv_util_version is None or (
                    virtualenv_util_version is not None and
                    item.split('-')[-1] == virtualenv_util_version))

            if is_correct_version:
                virtualenv_util_path = possible_dir
                virtualenv_util_version = item.split('-')[-1]

    return virtualenv_util_path, virtualenv_util_version


def _get_newest_package_version_and_url(
        pypi_server,
        package_name,
        package_extension='.tar.gz'):
    '''Utility function that searches the pypi_server specified for
    the latest version of the package with the name specified.
    Will return the version of the newest package found and the
    url to the package file on the server.
    '''

    # If we are getting our packages from the local filesystem, we
    # need to get the directory listing specially.
    if urlparse.urlparse(pypi_server).scheme == 'file':
        filenames = os.listdir(urlparse.urlparse(pypi_server).path.lstrip('/'))
        url_dir = pypi_server
    else:
        url_dir = pypi_server + '/' + package_name

        try:
            f_remote = urllib.urlopen(url_dir)
            index = f_remote.read()

        # If we get a URL error, try the special case of a "flat"
        # directory structure.
        except urllib.URLError:
            url_dir = pypi_server

            f_remote = urllib.urlopen(url_dir)
            index = f_remote.read()

        # Very simple regex parser that finds all hyperlinks in the index
        # HTML... this may break in some cases, but we want to keep it super
        # simple in the bootstrap.
        filenames = re.findall('href="(.*?)"', str(index.lower()))

    # Get all hyperlinks that start with the virtualenv package name
    # and end with the package extension.
    versions = []
    for filename in filenames:
        looks_like_package = (
            filename.startswith(package_name + '-') and
            filename.endswith(package_extension))

        if looks_like_package:
            version = filename.split('-')[-1].replace(package_extension, '')
            versions.append(version)

    # Sort the versions from lowest to highest.
    # NOTE: This simple sort will work for most versions we expect to
    # use in the virtualenv_util package.  This could be enhanced.
    versions.sort()

    # Select the highest version.
    # Select the highest version.
    try:
        highest_version = versions[-1]
    except IndexError:
        raise RuntimeError(
            'Unable to find any version of package {} at URL {}'.format(
                package_name, pypi_server))

    return highest_version, '/'.join([
        url_dir,
        '{}-{}{}'.format(
            package_name,
            highest_version,
            package_extension)])


def _download_package(
        virtualenv_util_url,
        virtualenv_util_version,
        bootstrap_directory):
    '''
    Downloads and unpacks the virtualenv_util package from the URL
    specified.
    '''
    virtualenv_util_tar_filename = os.path.basename(
        urlparse.urlparse(virtualenv_util_url).path)

    # Download the package source tar from the server.
    f_remote = urllib.urlopen(virtualenv_util_url)
    f_local_filename = os.path.join(ROOT_PATH, virtualenv_util_tar_filename)
    f_local = open(f_local_filename, 'wb')
    f_local.write(f_remote.read())
    f_local.close()
    f_remote.close()

    # Unpack the tarball to the current directory.
    tarf = tarfile.open(f_local_filename, 'r:gz')
    tarf.extractall(ROOT_PATH)
    tarf.close()

    virtualenv_util_path = os.path.join(
        ROOT_PATH,
        '{}-{}'.format(
            VIRTUALENV_UTIL_PACKAGE_NAME,
            virtualenv_util_version),
        VIRTUALENV_UTIL_PACKAGE_NAME)

    # Remove the tarball from the current directory.
    try:
        os.unlink(f_local_filename)
    except:
        pass

    return virtualenv_util_path


def _get_options(config_file_path=None, options_overrides=None):
    '''Parse the virtualenv_util config file, if present.
    Any settings in the options_override dictionary will override those given
    in the config file or on the command line.'''
    if options_overrides is None:
        options_overrides = {}

    if config_file_path is None and options_overrides.get('cfg_file', None):
        config_file_path = options_overrides['cfg_file']

    if config_file_path is not None:
        config = configparser.SafeConfigParser()
        config.read([config_file_path])
        config_file_global_settings = dict(config.items("global"))
    else:
        config_file_global_settings = {}

    parser = argparse.ArgumentParser(
        description='Bootstrap script for virtualenv_util')
    parser.add_argument(
        '--pypi_pull_server', default='http://pypi.python.org/simple')
    parser.add_argument(
        '--virtualenv_util_version', default=None)
    parser.add_argument(
        '--virtualenv_util_path', default=None)
    parser.add_argument(
        '--bootstrap_dir', default=ROOT_PATH)
    parser.add_argument(
        '--cfg_file', default=None)
    parser.add_argument(
        '--download_dir', default=None)
    parser.add_argument(
        '--download_cache_dir', default=None)

    parser.set_defaults(**config_file_global_settings)

    if options_overrides.get('dont_parse_argv', False):
        # Don't actually parse anything from the command line if this
        # option override is set.
        options, remaining_args = parser.parse_known_args([])
    else:
        options, remaining_args = parser.parse_known_args(sys.argv[1:])
        sys.argv = [sys.argv[0]] + remaining_args

    for key in options_overrides:
        setattr(options, key, options_overrides[key])

    options.cfg_file = config_file_path

    return options


def _import_and_execute_package(virtualenv_util_path, **args):
    package_script = os.path.join(
        virtualenv_util_path, VIRTUALENV_UTIL_MODULE_NAME)

    virtualenv_util = imp.load_source(
        VIRTUALENV_UTIL_PACKAGE_NAME, package_script)

    virtualenv_util.main(**args)


def main(config_file_path=None, options_overrides=None, verbose=True):
    '''
    Execute the bootstrap script using the configuration file and/or
    configuration options specified.  If necessary, will download the
    virtualenv package from the server.  The package is then imported
    and the module entry point (main) function is called.
    '''
    if options_overrides is None:
        options_overrides = {}

    options = _get_options(config_file_path, options_overrides)

    # If a download or download cache dir is specified, make a copy of
    # ourselves there.  That way, the bootstrap script will be available in
    # the download dir for offline use.
    for directory in [options.download_dir, options.download_cache_dir]:
        if directory is None:
            directory = ''

        if directory:
            try:
                shutil.copy2(__file__, directory)
            except:
                pass

    if options.virtualenv_util_path:

        virtualenv_util_path = os.path.normpath(options.virtualenv_util_path)

        virtualenv_module = os.path.join(
            virtualenv_util_path, VIRTUALENV_UTIL_MODULE_NAME)

        if not os.path.isfile(virtualenv_module):
            raise RuntimeError
        else:
            if verbose:
                print(
                    'Using local {} package at {}...'.format(
                        VIRTUALENV_UTIL_PACKAGE_NAME, virtualenv_util_path))

    elif options.download_dir is not None:
        # When the download_dir option is specified, ignore any existing
        # package and always download a fresh copy.
        virtualenv_util_path = None

    else:
        virtualenv_util_path, version = _check_for_existing_package(
            options.bootstrap_dir,
            options.virtualenv_util_version)

        if virtualenv_util_path is not None:
            if verbose:
                print(
                    'Using previously downloaded {} package version '
                    '{}...'.format(VIRTUALENV_UTIL_PACKAGE_NAME, version))

    # If we aren't using a previously downloaded or local version of the
    # package, try to download it.
    if virtualenv_util_path is None:
        # Must have a pypi server specified... if not, we have no way of
        # downloading the package.
        pypi_server = options.pypi_pull_server
        if not pypi_server:
            raise RuntimeError(
                'No PyPI server specified, cannot download {} '
                'package'.format(VIRTUALENV_UTIL_PACKAGE_NAME))

        if verbose:
            print('Checking for {} package on server {}...'.format(
                VIRTUALENV_UTIL_PACKAGE_NAME, pypi_server))

        # If a specific version of the package hasn't been specified, get
        # the latest version on the download server.
        if options.virtualenv_util_version is None:
            version, url = _get_newest_package_version_and_url(
                pypi_server,
                VIRTUALENV_UTIL_PACKAGE_NAME,
                VIRTUALENV_UTIL_PACKAGE_FILE_EXTENSION)
        else:
            version = options.virtualenv_util_version
            url = '/'.join([
                pypi_server,
                VIRTUALENV_UTIL_PACKAGE_NAME,
                '{}-{}{}'.format(
                    VIRTUALENV_UTIL_PACKAGE_NAME,
                    version,
                    VIRTUALENV_UTIL_PACKAGE_FILE_EXTENSION)])

        if verbose:
            print('Downloading {} package version {}...'.format(
                VIRTUALENV_UTIL_PACKAGE_NAME, version))

        virtualenv_util_path = _download_package(
            url,
            version,
            options.bootstrap_dir)

    if verbose:
        print('Importing script: {}'.format(os.path.join(
            virtualenv_util_path, VIRTUALENV_UTIL_MODULE_NAME)))

    _import_and_execute_package(
        virtualenv_util_path,
        options_overrides=vars(options))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Bootstrap script for the virtualenv_util module (will '
                    'attempt to download and execute the virtualenv_util main '
                    'routine')

    parser.add_argument('--cfg_file', default=DEFAULT_CONFIG_FILE_PATH)
    parsed, remaining_args = parser.parse_known_args(sys.argv[1:])
    sys.argv = [sys.argv[0]] + remaining_args

    main(config_file_path=parsed.cfg_file)

########NEW FILE########
__FILENAME__ = ci_bootstrap
#!/usr/bin/env python
import os
import sys

if sys.version_info[0] == 3:
    import configparser
    from urllib.request import urlretrieve
else:
    import ConfigParser as configparser
    from urllib import urlretrieve

config = configparser.SafeConfigParser()
config.read('ci_config/virtualenv_util.cfg')
bootstrap_url = config.get('global', 'bootstrap_url')
destination = os.path.basename(bootstrap_url)

if not os.path.exists(destination):
    urlretrieve(bootstrap_url, destination)

execfile(destination)

########NEW FILE########
__FILENAME__ = ci_run
import logging
from daf_fruit_dist.ci_utils import standard_sdist_run

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s')

    standard_sdist_run()

########NEW FILE########
__FILENAME__ = wicker_basket_test
from daf_basket.wicker_basket import WickerBasket


def feed_snow_white_test():
    my_basket = WickerBasket()
    did_she_dance_at_the_ball = my_basket.feed_snow_white()
    assert did_she_dance_at_the_ball, \
        "Snow White didn't dance in the ball"


def feed_dwarfs_test():
    my_basket = WickerBasket()
    did_the_dwarfs_sing_in_the_hall = my_basket.feed_dwarfs()
    assert did_the_dwarfs_sing_in_the_hall, \
        "The dwarfs didn't sing in the hall"

########NEW FILE########
__FILENAME__ = wicker_basket
from daf_apple.gala import Gala
from daf_citrus.pomelo import Pomelo


class WickerBasket(object):
    def __init__(self):
        pass

    def feed_dwarfs(self):
        my_fruit = Pomelo()
        is_good_day = my_fruit.fall()

        if is_good_day:
            print("Hi Ho Hi Ho its off to work we go.")
        else:
            print("That wicked witch put worms in our Pomelos.")

        return is_good_day

    def feed_snow_white(self):
        my_apple = Gala()
        is_good_day = my_apple.fall()

        if is_good_day:
            print("Prince charming is here. Even grumpy is happy!")
        else:
            print("I'm falling asleep. Darn that wicked witch!")

        return is_good_day

########NEW FILE########
__FILENAME__ = ci_bootstrap
#!/usr/bin/env python
import os
import sys

if sys.version_info[0] == 3:
    import configparser
    from urllib.request import urlretrieve
else:
    import ConfigParser as configparser
    from urllib import urlretrieve

config = configparser.SafeConfigParser()
config.read('ci_config/virtualenv_util.cfg')
bootstrap_url = config.get('global', 'bootstrap_url')
destination = os.path.basename(bootstrap_url)

if not os.path.exists(destination):
    urlretrieve(bootstrap_url, destination)

execfile(destination)

########NEW FILE########
__FILENAME__ = ci_run
import logging
from daf_fruit_dist.ci_utils import standard_sdist_run

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s')

    standard_sdist_run(submodule_order=('daf_apple', 'daf_citrus'))

########NEW FILE########
__FILENAME__ = continuous_integration
import os


def integrate():
    # From the newly-included 'daf_fruit_dist' module, import the
    # standard CI run.
    from daf_fruit_dist.ci_utils import standard_sdist_run

    # Test this package, then create a source distribution of it.
    standard_sdist_run()


if __name__ == '__main__':
    # Change active directories to the one containing this file.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    integrate()

########NEW FILE########
__FILENAME__ = gala
from daf_pest.worm import Worm


class Gala(object):
    def __init__(self):
        pass

    def fall(self):
        my_worm = Worm()
        is_good_day = my_worm.crawl()

        if is_good_day:
            print "Sum of the forces equals the " \
                  "change in momentum of the system"
        else:
            print "Any worm in my apple should at least be a happy worm. " \
                  "Time for beer!"

        return is_good_day

########NEW FILE########
__FILENAME__ = granny_smith
from daf_pest.worm import Worm


class GrannySmith(object):
    def __init__(self):
        pass

    def fall(self):
        my_worm = Worm()
        is_good_day = my_worm.crawl()

        if is_good_day:
            print "Sum of the forces equals the change in" \
                  " momentum of the system. Just ask your Granny."
        else:
            print "Any worm in my apple should at least be a happy worm. " \
                  "Time for granny smith apple beer!"

        return is_good_day

########NEW FILE########
__FILENAME__ = gala_test
from daf_apple.gala import Gala


def fall_test():
    my_fruit = Gala()
    did_it_fall = my_fruit.fall()
    assert did_it_fall, "Good day for Newtonian physics"

########NEW FILE########
__FILENAME__ = granny_smith_test
from daf_apple.granny_smith import GrannySmith


def fall_test():
    my_fruit = GrannySmith()
    did_it_fall = my_fruit.fall()
    assert did_it_fall, "Granny says it is a good day for Newtonian physics"

########NEW FILE########
__FILENAME__ = continuous_integration
import os


def integrate():
    # From the newly-included 'daf_fruit_dist' module, import the standard
    # CI run.
    from daf_fruit_dist.ci_utils import standard_sdist_run

    # Test this package, then create a source distribution of it.
    standard_sdist_run()


if __name__ == '__main__':
    # Change active directories to the one containing this file.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    integrate()

########NEW FILE########
__FILENAME__ = grapefruit
from daf_pest.worm import Worm


class Grapefruit(object):
    def __init__(self):
        pass

    def fall(self):
        my_worm = Worm()
        is_good_day = my_worm.crawl()

        if is_good_day:
            print("Grapefruits fall like any other fruit.")
        else:
            print("Wormy grapefruits are yucky!")

        return is_good_day

########NEW FILE########
__FILENAME__ = pomelo
from daf_pest.worm import Worm


class Pomelo(object):
    def __init__(self):
        pass

    def fall(self):
        my_worm = Worm()
        is_good_day = my_worm.crawl()

        if is_good_day:
            print "Messy juicy goodness in a vacuum falls the same " \
                  "as an apple in a vacuum"
        else:
            print("Worms in a Pomelo are nasty")

        return is_good_day

########NEW FILE########
__FILENAME__ = grapefruit_test
from daf_citrus.grapefruit import Grapefruit


def fall_test():
    my_fruit = Grapefruit()
    did_it_fall = my_fruit.fall()
    assert did_it_fall, \
        "Good day for Grapefruit inspired Newtonian physics"

########NEW FILE########
__FILENAME__ = pomelo_test
from daf_citrus.pomelo import Pomelo


def fall_test():
    my_fruit = Pomelo()
    did_it_fall = my_fruit.fall()

    assert did_it_fall, \
        "Juicy Pomelos make it a good day for Newtonian physics"

########NEW FILE########
__FILENAME__ = ci_bootstrap
#!/usr/bin/env python
import os
import sys

if sys.version_info[0] == 3:
    import configparser
    from urllib.request import urlretrieve
else:
    import ConfigParser as configparser
    from urllib import urlretrieve

config = configparser.SafeConfigParser()
config.read('ci_config/virtualenv_util.cfg')
bootstrap_url = config.get('global', 'bootstrap_url')
destination = os.path.basename(bootstrap_url)

if not os.path.exists(destination):
    urlretrieve(bootstrap_url, destination)

execfile(destination)

########NEW FILE########
__FILENAME__ = ci_run
import logging
from daf_fruit_dist.ci_utils import standard_sdist_run

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s')

    standard_sdist_run()

########NEW FILE########
__FILENAME__ = worm_test
from daf_pest.worm import Worm


def crawl_test():
    my_worm = Worm()
    did_it_crawl = my_worm.crawl()
    assert did_it_crawl, "Worm thinks it is a good day for crawling"

########NEW FILE########
__FILENAME__ = worm
import os


class Worm(object):
    def __init__(self):
        pass

    def crawl(self):
        be_happy_string = os.environ.get('BE_HAPPY', "true")
        is_good_day = be_happy_string.lower().strip() == "true"

        if is_good_day:
            print("I love to crawl")
        else:
            print("I don't want to crawl today")

        return is_good_day

########NEW FILE########
__FILENAME__ = process_config_templates
import argparse
from collections import namedtuple
import os
from string import Template
import sys
import textwrap


_OPTION_NAMES = (
    'pypi_server_base',
    'pypi_push_username',
    'pypi_push_password',
)


def _slurp_template_file(template_file):
    if not os.path.exists(template_file):
        raise IOError(
            "config template file: {} doesn't exist".format(template_file))
    with open(template_file, 'r') as f:
        whole_template = f.read()
    return whole_template


def _write_output_file(output_file, file_contents):
    with open(output_file, "w") as f:
        f.write(file_contents)


def _process_template(template_file, output_file, parsed_args):
    template_str = _slurp_template_file(template_file)

    template = Template(template_str)
    post_substitute = template.substitute(
        pypi_server_base=parsed_args.pypi_server_base,
        pypi_push_username=parsed_args.pypi_push_username,
        pypi_push_password=parsed_args.pypi_push_password
    )

    _write_output_file(output_file=output_file, file_contents=post_substitute)


def _process_ci_config_dir(relative_ci_config_dir_path, parsed_args):
    base_path = os.path.dirname(os.path.abspath(__file__))

    template_file_name = "virtualenv_util.cfg.template"
    output_file_name = "virtualenv_util.cfg"

    template_file = os.path.join(
        base_path, relative_ci_config_dir_path, template_file_name)

    output_file = os.path.join(
        base_path, relative_ci_config_dir_path, output_file_name)

    _process_template(
        template_file=template_file,
        output_file=output_file,
        parsed_args=parsed_args)


EnvTemplateValues = namedtuple('EnvTemplateValues', _OPTION_NAMES)


def _read_environment_for_defaults():
    pypi_server_base_env = os.environ.get('pypi_server_base'.upper(), None)
    pypi_push_username_env = os.environ.get('pypi_push_username'.upper(), None)
    pypi_push_password_env = os.environ.get('pypi_push_password'.upper(), None)

    return EnvTemplateValues(
        pypi_server_base=pypi_server_base_env,
        pypi_push_username=pypi_push_username_env,
        pypi_push_password=pypi_push_password_env)


def _log_values(parsed_args):
    def print_option_value(option, option_value):
        print('{}: {}'.format(option, option_value))

    def log_option_value(option):
        print_option_value(option, getattr(parsed_args, option, None))

    for option in ('pypi_server_base', 'pypi_push_username'):
        log_option_value(option)

    # Avoid printing password in plain text, but still log if there is a
    # None value
    password_value = getattr(parsed_args, 'pypi_push_password', None)
    if password_value:
        print_option_value('pypi_push_password', 'XXXXX')
    else:
        print_option_value('pypi_push_password', 'None')


def _parse_and_validate(parser, command_line_args):
    env_template_values = _read_environment_for_defaults()

    parsed_args = parser.parse_args(command_line_args)

    def handle_arg(key_name):
        opt_value = getattr(parsed_args, key_name, None)
        if not opt_value:
            opt_value = getattr(env_template_values, key_name, None)

        if not opt_value:
            msg = (
                "Error: {key_name} value must be provided.\n\n"
                "This can be done using the relevant command line argument\n"
                "or the corresponding environment variable: {env_name}\n\n"
                "{usage}".format(
                    key_name=key_name,
                    env_name=key_name.upper(),
                    usage=parser.format_usage()))
            print msg
            sys.exit(1)

        setattr(parsed_args, key_name, opt_value)

    for key_name in _OPTION_NAMES:
        handle_arg(key_name=key_name)

    return parsed_args


def _parse_args(args=None):
    parser = argparse.ArgumentParser(
        description='Configuration pre-processing tool.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
           Typical usage of the defend_against_fruit package would not
           use a configuration template processor such as this one,
           but would instead use hard-coded configuration files.

           Since this code is being shared on Github, its configuration
           files must avoid installation specific values.

           It is expected that your CI job will run this substitution
           before executing "ci --publish". A typical build config
           would be:

           Step 1: python process_config_templates.py \\
                   --pypi_server_base=http://artif.acme.com:8081/artifactory \\
                   --pypi_push_username=admin \\
                   --pypi_push_password=password

           Step 2: ci --publish'''))

    parser.add_argument(
        '--pypi-server-base',
        help='Base URL of the Artifactory repository manager')

    parser.add_argument(
        '--pypi-push-username',
        help='Username to be used when pushing to the Artifactory hosted '
             'PyPI server.')

    parser.add_argument(
        '--pypi-push-password',
        help='Password to be used when pushing to the Artifactory hosted '
             'PyPI server.')

    parsed_args = _parse_and_validate(parser=parser, command_line_args=args)

    return parsed_args


def run(command_line_args):
    parsed_args = _parse_args(command_line_args)
    _log_values(parsed_args)

    _process_ci_config_dir(
        relative_ci_config_dir_path=os.path.join(
            'defend_against_fruit', 'ci_config'),
        parsed_args=parsed_args)

    _process_ci_config_dir(
        relative_ci_config_dir_path=os.path.join(
            'examples', 'daf_basket', 'ci_config'),
        parsed_args=parsed_args)

    _process_ci_config_dir(
        relative_ci_config_dir_path=os.path.join(
            'examples', 'daf_fruit', 'ci_config'),
        parsed_args=parsed_args)

    _process_ci_config_dir(
        relative_ci_config_dir_path=os.path.join(
            'examples', 'daf_pest', 'ci_config'),
        parsed_args=parsed_args)

    _process_ci_config_dir(
        relative_ci_config_dir_path=os.path.join('pypi_redirect', 'ci_config'),
        parsed_args=parsed_args)


if __name__ == '__main__':
    command_line_args = sys.argv[1:]
    run(command_line_args)

########NEW FILE########
__FILENAME__ = ci_bootstrap
#!/usr/bin/env python
import os
import sys

if sys.version_info[0] == 3:
    import configparser
    from urllib.request import urlretrieve
else:
    import ConfigParser as configparser
    from urllib import urlretrieve

config = configparser.SafeConfigParser()
config.read('ci_config/virtualenv_util.cfg')
bootstrap_url = config.get('global', 'bootstrap_url')
destination = os.path.basename(bootstrap_url)

if not os.path.exists(destination):
    urlretrieve(bootstrap_url, destination)

execfile(destination)

########NEW FILE########
__FILENAME__ = ci_run
import logging
import os
import subprocess
from daf_fruit_dist.ci_utils import standard_sdist_run
from daf_fruit_dist.exec_utils import install_dev


def _path_from_here(*path):
    this_dir = os.path.dirname(os.path.abspath(__file__))
    rel_path = os.path.join(this_dir, *path)
    abs_path = os.path.abspath(rel_path)
    return abs_path


def _cwd_as(path):
    class Context(object):
        def __enter__(self):
            self.old_cwd = os.getcwd()
            os.chdir(path)

        def __exit__(self, exc_type, exc_val, exc_tb):
            os.chdir(self.old_cwd)

    return Context()


def _run_integration_tests():
    install_dev()

    test_dir = _path_from_here('..', 'pypi_redirect_integration', 'tests')

    with _cwd_as(test_dir):
        subprocess.check_call(['nosetests'])


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s')

    standard_sdist_run(integration_tests_fn=_run_integration_tests)

########NEW FILE########
__FILENAME__ = pypi_windows_service
from logging import handlers, DEBUG
import logging
import cherrypy
import win32serviceutil
import win32service
from ..server_app.launcher import run_server


class PyPIWindowsService(win32serviceutil.ServiceFramework):
    """NT Service."""
    _svc_name_ = "PyPIRedirectService"
    _svc_display_name_ = "PyPI Redirect Service"

    def SvcDoRun(self):
        svc_logger = _create_svc_logger()
        run_server(primordial_logger=svc_logger, enable_file_logging=True)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        cherrypy.engine.exit()

        self.ReportServiceStatus(win32service.SERVICE_STOPPED)
        # very important for use with py2exe
        # otherwise the Service Controller never knows that it is stopped !


def _create_svc_logger():
    svc_logger = logging.getLogger(PyPIWindowsService._svc_name_)
    svc_logger.setLevel(DEBUG)

    h = handlers.NTEventLogHandler(PyPIWindowsService._svc_display_name_)
    svc_logger.addHandler(h)
    return svc_logger


def main():
    win32serviceutil.HandleCommandLine(PyPIWindowsService)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = dependency_injection
import index_builder
import index_parser
from handler.file_handler import FileHandler
from handler.invalid_path_handler import InvalidPathHandler
from handler.pypi_index_handler import PyPIIndexHandler
from handler.root_index_handler import RootIndexHandler
from http._utils import http_get
from http.path_length_dispatcher import PathLengthDispatcher


def wire_dependencies():
    """
    PyPI redirect uses a dependency injection paradigm to better
    facilitate testing. Rather than use a dependency injection
    framework, we are manually injecting our dependencies here.
    """
    pypi_base_url = 'https://pypi.python.org/simple'

    root_index_handler = RootIndexHandler(
        build_index_fn=index_builder.build)

    pypi_index_handler = PyPIIndexHandler(
        pypi_base_url=pypi_base_url,
        http_get_fn=http_get,
        parse_index_fn=index_parser.parse,
        build_index_fn=index_builder.build)

    file_handler = FileHandler(
        pypi_base_url=pypi_base_url,
        http_get_fn=http_get,
        parse_index_fn=index_parser.parse)

    invalid_path_handler = InvalidPathHandler()

    root = PathLengthDispatcher(
        handlers_indexed_by_path_length=(
            root_index_handler.handle,  # len 0: ex: /
            pypi_index_handler.handle,  # len 1: ex: /python/
            pypi_index_handler.handle,  # len 2: ex: /python/nose/
            file_handler.handle),       # len 3: ex: /python/nose/nose-1.0.tgz
        invalid_path_handler=invalid_path_handler)

    return root

########NEW FILE########
__FILENAME__ = file_handler
import os
from _exception import http_404, http_302
from _utils import fetch_and_parse_index, ensure_python_dir


class FileHandler(object):
    def __init__(self, pypi_base_url, http_get_fn, parse_index_fn):
        self.pypi_base_url = pypi_base_url
        self.http_get_fn = http_get_fn
        self.parse_index_fn = parse_index_fn

    def _is_checksum_file(self, filename):
        return filename.lower().endswith(('.md5', '.sha1'))

    def _handle_checksum(self, checksum_filename, index_rows, response):
        filename_base, ext = os.path.splitext(checksum_filename)
        ext_no_dot = ext[1:].lower()
        _ensure_file_in_index(filename=filename_base, index_rows=index_rows)
        checksums = index_rows[filename_base].checksums

        return _get_checksum(
            checksums=checksums,
            checksum_ext=ext_no_dot,
            response_headers=response.headers)

    def _redirect_to_download_url(self, filename, index_rows):
        _ensure_file_in_index(filename=filename, index_rows=index_rows)
        download_url = index_rows[filename].download_url
        raise http_302(download_url)

    @ensure_python_dir
    def handle(self, path, request, response):
        py, package_name, filename = path

        index_url = '{}/{}/'.format(self.pypi_base_url, package_name)

        index_rows = fetch_and_parse_index(
            http_get_fn=self.http_get_fn,
            parse_index_fn=self.parse_index_fn,
            pypi_base_url=self.pypi_base_url,
            index_url=index_url,
            package_path=package_name)

        if self._is_checksum_file(filename=filename):
            return self._handle_checksum(
                checksum_filename=filename,
                index_rows=index_rows,
                response=response)

        self._redirect_to_download_url(
            filename=filename,
            index_rows=index_rows)


def _ensure_file_in_index(filename, index_rows):
    if filename not in index_rows:
        raise http_404('File "{}" does not exist'.format(filename))


def _get_checksum(checksums, checksum_ext, response_headers):
    checksum = getattr(checksums, checksum_ext)

    if not checksum:
        raise http_404('Checksum not available')

    response_headers['Content-Type'] = 'application/x-checksum'

    return checksum

########NEW FILE########
__FILENAME__ = invalid_path_handler
from _exception import http_404


class InvalidPathHandler(object):
    def handle(self, path, request, response):
        raise http_404('Invalid path of "{}"'.format('/'.join(path)))

########NEW FILE########
__FILENAME__ = pypi_index_handler
from _utils import fetch_and_parse_index, ensure_index, ensure_python_dir


class PyPIIndexHandler(object):
    def __init__(
            self,
            pypi_base_url,
            http_get_fn,
            parse_index_fn,
            build_index_fn):
        self.pypi_base_url = pypi_base_url
        self.http_get_fn = http_get_fn
        self.parse_index_fn = parse_index_fn
        self.build_index_fn = build_index_fn

    def _simple_pypi_or_package(self, path):
        """
        Determines whether the given path points to a specific package
        or to the root of the "simple" PyPI structure.
        """
        if len(path) == 2:
            py, package_name = path
            index_url = '{}/{}/'.format(self.pypi_base_url, package_name)
        else:
            package_name = 'python'
            index_url = '{}/'.format(self.pypi_base_url)
        return index_url, package_name

    @ensure_python_dir
    @ensure_index
    def handle(self, path, request, response):
        index_url, package_name = self._simple_pypi_or_package(path)

        index_rows = fetch_and_parse_index(
            http_get_fn=self.http_get_fn,
            parse_index_fn=self.parse_index_fn,
            pypi_base_url=self.pypi_base_url,
            index_url=index_url,
            package_path=package_name)

        rebuilt_html_str = self.build_index_fn(
            index_rows=index_rows)

        return rebuilt_html_str

########NEW FILE########
__FILENAME__ = root_index_handler
from collections import OrderedDict
from _utils import ensure_index


class RootIndexHandler(object):
    def __init__(self, build_index_fn):
        self.build_index_fn = build_index_fn

    @ensure_index
    def handle(self, path, request, response):
        html_str = self.build_index_fn(
            index_rows=OrderedDict([('python/', None)]))

        return html_str

########NEW FILE########
__FILENAME__ = _exception
from functools import partial
import sys
import cherrypy


class HandlerException(Exception):
    def __init__(self, wrapped_exception):
        self.wrapped_exception = wrapped_exception

    def raise_wrapped(self):
        """
        Raises the 'wrapped' exception, preserving the original
        traceback. This must be called from within an `except` block.
        """
        # The first item is a class instance, so the second item must
        # be None. The third item is the traceback object, which is why
        # this method must be called from within an `except` block.
        raise (
            self.wrapped_exception(),
            None,
            sys.exc_info()[2])


def http_301(download_url):
    return HandlerException(wrapped_exception=partial(
        cherrypy.HTTPRedirect,
        urls=download_url,
        status=301))


def http_302(download_url):
    return HandlerException(wrapped_exception=partial(
        cherrypy.HTTPRedirect,
        urls=download_url,
        status=302))


def http_404(message):
    return HandlerException(wrapped_exception=partial(
        cherrypy.HTTPError,
        status=404,
        message=message))

########NEW FILE########
__FILENAME__ = _utils
from functools import wraps
from lxml.etree import ParseError
from requests import RequestException
from _exception import http_404, http_301


def ensure_index(fn):
    """
    Decorator for the handle() method of any handler. Ensures that
    indexes requested without a trailing slash are redirected to a
    version with the trailing slash.
    """
    @wraps(fn)
    def wrapper(self, path, request, response):
        if not request.is_index:
            raise http_301((path[-1] + '/') if path else '/')
        return fn(self, path, request, response)
    return wrapper


def ensure_python_dir(fn):
    """
    Decorator for the handle() method of any handler. Ensures that
    indexes and files requested are all under the root python/
    directory.
    """
    @wraps(fn)
    def wrapper(self, path, request, response):
        if path[0] != 'python':
            raise http_404('Not under "python/" directory')
        return fn(self, path, request, response)
    return wrapper


def fetch_and_parse_index(
        http_get_fn,
        parse_index_fn,
        pypi_base_url,
        index_url,
        package_path):
    try:
        index_html_str = http_get_fn(url=index_url)
    except RequestException:
        raise http_404('Index "{}" cannot be reached'.format(index_url))

    try:
        index_rows = parse_index_fn(
            base_url=pypi_base_url,
            package_path=package_path,
            html_str=index_html_str)
    except ParseError:
        raise http_404('Index "{}" failed to be parsed'.format(index_url))

    return index_rows

########NEW FILE########
__FILENAME__ = path_length_dispatcher
import cherrypy
from ..handler._exception import HandlerException


class PathLengthDispatcher(object):
    def __init__(
            self,
            handlers_indexed_by_path_length,
            invalid_path_handler):
        self.handlers_indexed_by_path_length = handlers_indexed_by_path_length
        self.invalid_path_handler = invalid_path_handler

    @cherrypy.expose
    def default(self, *path):
        try:
            return self.handlers_indexed_by_path_length[len(path)](
                path=path,
                request=cherrypy.request,
                response=cherrypy.response)

        except IndexError:
            return self.invalid_path_handler(
                path=path,
                request=cherrypy.request,
                response=cherrypy.response)

        except HandlerException as e:
            e.raise_wrapped()

########NEW FILE########
__FILENAME__ = _utils
import requests


def http_get(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

########NEW FILE########
__FILENAME__ = index_builder
import cgi


def build(index_rows):
    html_rows = '\n'.join(
        '\n'.join(_rows_for_file(p, r)) for p, r in index_rows.iteritems())
    built = (
        '<html><body>\n'
        '{html_rows}\n'
        '</body></html>'.format(html_rows=html_rows))
    return built


def _rows_for_file(package_filename, index_row):
    yield _format_row(package_filename)
    if index_row:
        if index_row.checksums.md5:
            yield _format_row(package_filename + '.md5')
        if index_row.checksums.sha1:
            yield _format_row(package_filename + '.sha1')


def _format_row(filename):
    return '<a href="{}">{}</a><br/>'.format(
        _escape_for_html(filename, quote=True),
        _escape_for_html(filename))


def _escape_for_html(s, quote=False):
    return cgi.escape(s, quote=quote).encode('ascii', 'xmlcharrefreplace')

########NEW FILE########
__FILENAME__ = index_parser
from collections import namedtuple, OrderedDict
from lxml import etree
import urlparse


Checksums = namedtuple('Checksums', ('md5', 'sha1'))
IndexRow = namedtuple('IndexRow', ('download_url', 'checksums'))


def _all_internal_links_and_directories(html_root):
    return html_root.xpath(
        ".//a["
        "  @rel = 'internal'"
        "  or "
        "  ("
        "    substring(@href, 1, string-length(text())) = text()"
        "    and "
        "    substring(@href, string-length(@href)) = '/'"
        "  )"
        "]")


def parse(
        base_url,
        package_path,
        html_str,
        strict_html=True,
        find_links_fn=_all_internal_links_and_directories):
    html_root = _parse_html(html_str, strict_html)
    rows = _parse_internal_links(
        base_url,
        html_root,
        package_path,
        find_links_fn)
    return rows


def _parse_internal_links(base_url, html_root, package_path, find_links_fn):
    rows = OrderedDict()
    for link in find_links_fn(html_root):
        href = link.attrib['href']
        if not _is_ascii(href):
            continue
        if href.endswith('/'):
            if not _is_absolute_url(href):
                rows[href] = None
        else:
            rows[link.text.strip()] = IndexRow(
                download_url=_make_url_absolute(base_url, package_path, href),
                checksums=_determine_checksums(href))
    return rows


def _is_ascii(s):
    try:
        s.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False


def _parse_html(html_str, strict_html):
    parser = etree.HTMLParser(recover=not strict_html)
    html_root = etree.fromstring(html_str, parser)
    return html_root


def _is_absolute_url(url):
    return bool(urlparse.urlparse(url).scheme)


def _make_url_absolute(base_url, package_path, url):
    if _is_absolute_url(url):
        return url
    return '{}/{}/{}'.format(base_url, package_path, url)


def _determine_checksums(href):
    split_url = urlparse.urlsplit(href)
    fragment = split_url.fragment
    fragment_dict = dict((fragment.split('='),)) if fragment else {}

    checksums = Checksums(
        md5=fragment_dict.get('md5', None),
        sha1=fragment_dict.get('sha1', None))

    return checksums

########NEW FILE########
__FILENAME__ = launcher
from logging import handlers, DEBUG
import logging
import os
import shutil
import sys
import cherrypy
from dependency_injection import wire_dependencies


def run_server(primordial_logger=None, enable_file_logging=False):
    """
    Run the server which proxies requests from:
        python/<package>
    to:
        https://pypi.python.org/simple/<package>

    And requests from:
        python/<package>/<filename>
    to:
        https://pypi.python.org/<path-to-filename>
    """
    if primordial_logger is None:
        primordial_logger = _create_console_logger()

    root = wire_dependencies()

    cherrypy_config_path = _get_cherrypy_config_file(primordial_logger)

    app = cherrypy.tree.mount(
        root,
        script_name='/',
        config=cherrypy_config_path)

    cherrypy.config.update(cherrypy_config_path)

    if enable_file_logging:
        _enable_file_logging(app, primordial_logger=primordial_logger)

    cherrypy.engine.start()
    cherrypy.engine.block()


def _get_cherrypy_config_file(primordial_logger):
    cherrypy_config_path = _config_path('pypi_redirect.conf')

    if not os.path.exists(cherrypy_config_path):
        template_path = _config_path('pypi_redirect.conf.template')

        assert os.path.exists(template_path), \
            'Neither the CherryPy config file ("{}") nor a suitable ' \
            'template ("{}") were found.'.format(
                cherrypy_config_path,
                template_path)

        shutil.copyfile(template_path, cherrypy_config_path)

        primordial_logger.info(
            'Created CherryPy config file "{}" from template "{}"'.format(
                cherrypy_config_path,
                template_path))

    primordial_logger.info(
        'Using CherryPy config file "{}"'.format(cherrypy_config_path))

    return cherrypy_config_path


def _sys_prefix_path(*path):
    return os.path.join(sys.prefix, 'pypi_redirect', *path)


def _config_path(*path):
    return _sys_prefix_path('config', *path)


def _log_path(*path):
    return _sys_prefix_path('log', *path)


def _abs_log_path(log_filename):
    if not os.path.isabs(log_filename):
        return _log_path(log_filename)
    else:
        return log_filename


def _ensure_path_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)


def _enable_file_logging(app, primordial_logger):
    # Remove the default FileHandlers if present.
    app.log.error_file = ""
    app.log.access_file = ""

    _add_handler(
        app=app,
        logger=app.log.error_log,
        log_filename_config_attr='rot_error_file',
        log_filename_default_value='error.log',
        max_bytes_config_attr='rot_error_maxBytes',
        backup_count_config_attr='rot_error_backupCount',
        primordial_logger=primordial_logger)

    _add_handler(
        app=app,
        logger=app.log.access_log,
        log_filename_config_attr='rot_access_file',
        log_filename_default_value='access.log',
        max_bytes_config_attr='rot_access_maxBytes',
        backup_count_config_attr='rot_access_backupCount',
        primordial_logger=primordial_logger)


def _add_handler(
        app,
        logger,
        log_filename_config_attr,
        log_filename_default_value,
        max_bytes_config_attr,
        backup_count_config_attr,
        primordial_logger):

    def get_attr_and_log_value(attr, default_value):
        value = getattr(app.log, attr, default_value)
        primordial_logger.info(
            'log.{}: {!r} (default {!r})'.format(attr, value, default_value))
        return value

    max_bytes = get_attr_and_log_value(max_bytes_config_attr, 1000000)
    backup_count = get_attr_and_log_value(backup_count_config_attr, 4)
    fname = get_attr_and_log_value(
        log_filename_config_attr,
        log_filename_default_value)

    fname = _abs_log_path(fname)

    primordial_logger.info(
        'log.{} as abs path: {!r}'.format(log_filename_config_attr, fname))

    _ensure_path_exists(os.path.dirname(fname))

    h = handlers.RotatingFileHandler(fname, 'a', max_bytes, backup_count)
    h.setLevel(DEBUG)
    h.setFormatter(cherrypy._cplogging.logfmt)

    logger.addHandler(h)


def _create_console_logger():
    console_logger = logging.getLogger('PyPIRedirect')
    console_logger.setLevel(DEBUG)

    h = logging.StreamHandler()
    console_logger.addHandler(h)
    return console_logger

########NEW FILE########
__FILENAME__ = file_handler_test
from collections import OrderedDict, namedtuple
from functools import partial
from lxml.etree import ParseError
from nose.tools import eq_
from requests import RequestException
from ...server_app.handler.file_handler import FileHandler
from ...server_app.index_parser import IndexRow, Checksums
from _utils import FunctionStub, RequestStub, ResponseStub
from _utils import assert_http_redirect, assert_http_not_found


FileEntry = namedtuple('FileEntry', ('pkg_name', 'filename', 'index_row'))


def _generate_file_entry(has_md5=True, has_sha1=True):
    checksums = Checksums(
        md5='MD5-nose-1.2.1.tar.gz' if has_md5 else None,
        sha1='SHA1-nose-1.2.1.tar.gz' if has_sha1 else None)

    file_entry = FileEntry(
        pkg_name='nose',
        filename='nose-1.2.1.tar.gz',
        index_row=IndexRow(
            download_url='http://some_url.com/nose/nose-1.2.1.tar.gz',
            checksums=checksums))

    return file_entry


def handle_file_request_test():
    file_entry = _generate_file_entry()

    handler_runner = partial(
        _check_file_handler,
        file_entry=file_entry,
        file_requested=file_entry.filename)

    assert_http_redirect(
        run_handler_fn=handler_runner,
        expected_url=file_entry.index_row.download_url,
        expected_status=302,
        failure_description='Handler did not redirect')


def handle_md5_request_test():
    file_entry = _generate_file_entry()

    handler_runner = partial(
        _check_file_handler,
        file_entry=file_entry,
        file_requested=file_entry.filename + '.md5',
        expected_checksum=file_entry.index_row.checksums.md5)

    handler_runner()


def handle_sha1_request_test():
    file_entry = _generate_file_entry()

    handler_runner = partial(
        _check_file_handler,
        file_entry=file_entry,
        file_requested=file_entry.filename + '.sha1',
        expected_checksum=file_entry.index_row.checksums.sha1)

    handler_runner()


def handle_non_existent_file_request_test():
    file_entry = _generate_file_entry()

    handler_runner = partial(
        _check_file_handler,
        file_entry=file_entry,
        file_requested='non-existent.tar.gz')

    assert_http_not_found(
        run_handler_fn=handler_runner,
        failure_description='Failed to return 404 for non-existent file')


def handle_non_existent_md5_request_test():
    file_entry = _generate_file_entry(has_md5=False)

    handler_runner = partial(
        _check_file_handler,
        file_entry=file_entry,
        file_requested=file_entry.filename + '.md5')

    assert_http_not_found(
        run_handler_fn=handler_runner,
        failure_description='Failed to return 404 for non-existent file')


def handle_non_existent_sha1_request_test():
    file_entry = _generate_file_entry(has_sha1=False)

    handler_runner = partial(
        _check_file_handler,
        file_entry=file_entry,
        file_requested=file_entry.filename + '.sha1')

    assert_http_not_found(
        run_handler_fn=handler_runner,
        failure_description='Failed to return 404 for non-existent file')


def http_get_fn_exception_test():
    file_entry = _generate_file_entry()

    handler_runner = partial(
        _check_file_handler,
        file_entry=file_entry,
        file_requested=file_entry.filename,
        http_get_exception=RequestException())

    assert_http_not_found(
        run_handler_fn=handler_runner,
        failure_description='Failed to return 404 on failure to get index')


def parse_index_fn_exception_test():
    file_entry = _generate_file_entry()

    handler_runner = partial(
        _check_file_handler,
        file_entry=file_entry,
        file_requested=file_entry.filename,
        parse_index_exception=ParseError(None, None, None, None))

    assert_http_not_found(
        run_handler_fn=handler_runner,
        failure_description='Failed to return 404 on failure to parse index')


def non_python_root_path_test():
    file_entry = _generate_file_entry()

    handler_runner = partial(
        _check_file_handler,
        file_entry=file_entry,
        file_requested=file_entry.filename,
        root_dir='not_python')

    assert_http_not_found(
        run_handler_fn=handler_runner,
        failure_description='Failed to return 404 on non-"/python/" path')


def _check_file_handler(
        file_entry,
        file_requested,
        root_dir='python',
        expected_checksum=None,
        http_get_exception=None,
        parse_index_exception=None):

    pypi_base_url = 'http://dumb_url.com'

    parser_response = OrderedDict([
        ('nose-1.2.0.tar.gz', IndexRow(
            download_url='http://some_url.com/nose/nose-1.2.0.tar.gz',
            checksums=Checksums(
                md5='MD5-nose-1.2.0.tar.gz',
                sha1=None))),
        (file_entry.filename, file_entry.index_row),
        ('nose-1.2.1.egg', IndexRow(
            download_url='http://some_url.com/nose/nose-1.2.1.egg',
            checksums=Checksums(
                md5='MD5-nose-1.2.1.egg',
                sha1=None))),
    ])

    html_get_response = 'be dumb html'

    html_get_stub = FunctionStub(
        name='HTML Get',
        dummy_result=html_get_response,
        dummy_exception=http_get_exception)

    parser_stub = FunctionStub(
        name='Parser',
        dummy_result=parser_response,
        dummy_exception=parse_index_exception)

    handler = FileHandler(
        pypi_base_url=pypi_base_url,
        http_get_fn=html_get_stub,
        parse_index_fn=parser_stub)

    request = RequestStub(is_index=False)
    response = ResponseStub()

    # When not retrieving a checksum, we expect a redirection exception to be
    # thrown here. Asserting correct redirect behavior is performed in the
    # calling test function.
    response_str = handler.handle(
        path=[root_dir, file_entry.pkg_name, file_requested],
        request=request,
        response=response)

    expected_headers = {'Content-Type': 'application/x-checksum'}

    eq_(response.headers, expected_headers,
        msg='Response headers did not match the expected headers')

    eq_(response_str, expected_checksum,
        msg='Response checksum did not match the expected checksum')

    html_get_stub.assert_single_kw_call(expected_kwargs={
        'url': '{}/{}/'.format(pypi_base_url, file_entry.pkg_name)})

    parser_stub.assert_single_kw_call(expected_kwargs={
        'base_url': pypi_base_url,
        'package_path': file_entry.pkg_name,
        'html_str': html_get_response})

########NEW FILE########
__FILENAME__ = index_builder_test
from collections import OrderedDict
from nose.tools import eq_
from _utils import read_index
from ...server_app import index_builder
from ...server_app.index_parser import IndexRow, Checksums


def typical_index_test():
    index_rows = OrderedDict([
        ('Sphinx-0.6.4-py2.5.egg',
            IndexRow(
                download_url=(
                    'https://pypi.python.org/simple/Sphinx/'
                    '../../packages/2.5/S/Sphinx/Sphinx-0.6.4-py2.5.egg'
                    '#md5=b9e637ba15a27b31b7f94b8809cdebe3'),
                checksums=Checksums(
                    md5='b9e637ba15a27b31b7f94b8809cdebe3',
                    sha1=None))),
        ('Sphinx-0.1.61843.tar.gz',
            IndexRow(
                download_url=(
                    'http://pypi.acme.com/packages/source/S/Sphinx/'
                    'Sphinx-0.1.61843.tar.gz'),
                checksums=Checksums(
                    md5=None,
                    sha1=None))),
        ('Sphinx-0.6.5-py2.6.egg',
            IndexRow(
                download_url=(
                    'https://pypi.python.org/simple/Sphinx/'
                    '../../packages/2.6/S/Sphinx/'
                    'Sphinx-0.6.5-py2.6.egg'),
                checksums=Checksums(
                    md5=None,
                    sha1=None))),
        ('Sphinx-0.6b1-py2.5.egg',
            IndexRow(
                download_url=(
                    'https://pypi.python.org/simple/Sphinx/'
                    '../../packages/2.5/S/Sphinx/'
                    'Sphinx-0.6b1-py2.5.egg'
                    '#md5=b877f156e5c4b22257c47873021da3d2'),
                checksums=Checksums(
                    md5='b877f156e5c4b22257c47873021da3d2',
                    sha1=None))),
        ('Sphinx-0.1.61945-py2.5.egg',
            IndexRow(
                download_url=(
                    'https://pypi.python.org/simple/Sphinx/'
                    '../../packages/2.5/S/Sphinx/'
                    'Sphinx-0.1.61945-py2.5.egg'
                    '#md5=8139b5a66e41202b362bac270eef26ad'),
                checksums=Checksums(
                    md5='8139b5a66e41202b362bac270eef26ad',
                    sha1=None))),
        ('Sphinx-0.6-py2.5.egg',
            IndexRow(
                download_url=(
                    'https://pypi.python.org/simple/Sphinx/'
                    '../../packages/2.5/S/Sphinx/'
                    'Sphinx-0.6-py2.5.egg'
                    '#sha1=0000e1d327ab9524a006179aef4155a0d7a0'),
                checksums=Checksums(
                    md5=None,
                    sha1='0000e1d327ab9524a006179aef4155a0d7a0'))),
        ('Sphinx-1.0b2.tar.gz',
            IndexRow(
                download_url=(
                    'https://pypi.python.org/simple/Sphinx/'
                    '../../packages/source/S/Sphinx/'
                    'Sphinx-1.0b2.tar.gz'
                    '#sha1=00006bf13da4fd0542cc85705d1c4abd3c0a'),
                checksums=Checksums(
                    md5=None,
                    sha1='00006bf13da4fd0542cc85705d1c4abd3c0a'))),
        ('Sphinx-0.6.1-py2.4.egg',
            IndexRow(
                download_url=(
                    'http://pypi.acme.com/packages/2.4/S/Sphinx/'
                    'Sphinx-0.6.1-py2.4.egg'
                    '#md5=8b5d93be6d4f76e1c3d8c3197f84526f'),
                checksums=Checksums(
                    md5='8b5d93be6d4f76e1c3d8c3197f84526f',
                    sha1=None))),
        ('Sphinx-0.5.tar.gz',
            IndexRow(
                download_url=(
                    'https://pypi.python.org/simple/Sphinx/'
                    '../../packages/source/S/Sphinx/'
                    'Sphinx-0.5.tar.gz'
                    '#md5=55a33cc13b5096c8763cd4a933b30ddc'),
                checksums=Checksums(
                    md5='55a33cc13b5096c8763cd4a933b30ddc',
                    sha1=None))),
        ('subdir/', None),
    ])

    _assert_parse_results(
        index_rows=index_rows,
        output_file='typical_index_rebuilt.html')


def single_index_test():
    index_rows = OrderedDict([
        ('Sphinx-0.1.61843.tar.gz',
            IndexRow(
                download_url=(
                    'https://pypi.python.org/simple/Sphinx/'
                    '../../packages/source/S/Sphinx/'
                    'Sphinx-0.1.61843.tar.gz'
                    '#md5=69ab7befe60af790d24e22b4b46e8392'),
                checksums=Checksums(
                    md5='69ab7befe60af790d24e22b4b46e8392',
                    sha1=None)))])

    _assert_parse_results(
        index_rows=index_rows,
        output_file='single_index_rebuilt.html')


def empty_index_test():
    _assert_parse_results(
        index_rows=OrderedDict(),
        output_file='empty_index_rebuilt.html')


def directory_index_test():
    index_rows = OrderedDict([
        ('Sphinx/', None),
        ('nose/', None)])

    _assert_parse_results(
        index_rows=index_rows,
        output_file='directory_index_rebuilt.html')


def _assert_parse_results(index_rows, output_file):
    actual_html_str = index_builder.build(
        index_rows=index_rows)

    expected_html_str = read_index(output_file)

    eq_(actual_html_str, expected_html_str)

########NEW FILE########
__FILENAME__ = index_parser_test
from collections import OrderedDict
from nose.tools import eq_, raises
from lxml.etree import XMLSyntaxError
from _utils import read_index
from ...server_app import index_parser


def typical_index_test():
    expected = OrderedDict((
        ('Sphinx-0.6.4-py2.5.egg', index_parser.IndexRow(
            download_url='https://pypi.python.org/simple/Sphinx/../../packages'
                         '/2.5/S/Sphinx/Sphinx-0.6.4-py2.5.egg'
                         '#md5=b9e637ba15a27b31b7f94b8809cdebe3',
            checksums=index_parser.Checksums(
                md5='b9e637ba15a27b31b7f94b8809cdebe3',
                sha1=None))),
        ('Sphinx-0.1.61843.tar.gz', index_parser.IndexRow(
            download_url='http://pypi.acme.com/packages'
                         '/source/S/Sphinx/Sphinx-0.1.61843.tar.gz',
            checksums=index_parser.Checksums(
                md5=None,
                sha1=None))),
        ('Sphinx-0.6.5-py2.6.egg', index_parser.IndexRow(
            download_url='https://pypi.python.org/simple/Sphinx/../../packages'
                         '/2.6/S/Sphinx/Sphinx-0.6.5-py2.6.egg',
            checksums=index_parser.Checksums(
                md5=None,
                sha1=None))),
        ('Sphinx-0.6b1-py2.5.egg', index_parser.IndexRow(
            download_url='https://pypi.python.org/simple/Sphinx/../../packages'
                         '/2.5/S/Sphinx/Sphinx-0.6b1-py2.5.egg'
                         '#md5=b877f156e5c4b22257c47873021da3d2',
            checksums=index_parser.Checksums(
                md5='b877f156e5c4b22257c47873021da3d2',
                sha1=None))),
        ('Sphinx-0.1.61945-py2.5.egg', index_parser.IndexRow(
            download_url='https://pypi.python.org/simple/Sphinx/../../packages'
                         '/2.5/S/Sphinx/Sphinx-0.1.61945-py2.5.egg'
                         '#md5=8139b5a66e41202b362bac270eef26ad',
            checksums=index_parser.Checksums(
                md5='8139b5a66e41202b362bac270eef26ad',
                sha1=None))),
        ('Sphinx-0.6-py2.5.egg', index_parser.IndexRow(
            download_url='https://pypi.python.org/simple/Sphinx/../../packages'
                         '/2.5/S/Sphinx/Sphinx-0.6-py2.5.egg'
                         '#sha1=0000e1d327ab9524a006179aef4155a0d7a0',
            checksums=index_parser.Checksums(
                md5=None,
                sha1='0000e1d327ab9524a006179aef4155a0d7a0'))),
        ('Sphinx-1.0b2.tar.gz', index_parser.IndexRow(
            download_url='https://pypi.python.org/simple/Sphinx/../../packages'
                         '/source/S/Sphinx/Sphinx-1.0b2.tar.gz'
                         '#sha1=00006bf13da4fd0542cc85705d1c4abd3c0a',
            checksums=index_parser.Checksums(
                md5=None,
                sha1='00006bf13da4fd0542cc85705d1c4abd3c0a'))),
        ('Sphinx-0.6.1-py2.4.egg', index_parser.IndexRow(
            download_url='http://pypi.acme.com/packages'
                         '/2.4/S/Sphinx/Sphinx-0.6.1-py2.4.egg'
                         '#md5=8b5d93be6d4f76e1c3d8c3197f84526f',
            checksums=index_parser.Checksums(
                md5='8b5d93be6d4f76e1c3d8c3197f84526f',
                sha1=None))),
        ('Sphinx-0.5.tar.gz', index_parser.IndexRow(
            download_url='https://pypi.python.org/simple/Sphinx/../../packages'
                         '/source/S/Sphinx/Sphinx-0.5.tar.gz'
                         '#md5=55a33cc13b5096c8763cd4a933b30ddc',
            checksums=index_parser.Checksums(
                md5='55a33cc13b5096c8763cd4a933b30ddc',
                sha1=None))),
        ('subdir/', None)
    ))
    _assert_parse_results('typical_index.html', expected)


def single_index_test():
    expected = OrderedDict((
        ('Sphinx-0.1.61843.tar.gz', index_parser.IndexRow(
            download_url='https://pypi.python.org/simple/Sphinx/../../packages'
                         '/source/S/Sphinx/Sphinx-0.1.61843.tar.gz'
                         '#md5=69ab7befe60af790d24e22b4b46e8392',
            checksums=index_parser.Checksums(
                md5='69ab7befe60af790d24e22b4b46e8392',
                sha1=None))),
    ))
    _assert_parse_results('single_index.html', expected)


def empty_index_test():
    expected = OrderedDict()
    _assert_parse_results('empty_index.html', expected)


def directory_index_test():
    expected = OrderedDict((
        ('Sphinx/', None),
        ('nose/', None),
    ))
    _assert_parse_results('directory_index.html', expected)


@raises(XMLSyntaxError)
def bad_index_test():
    _assert_parse_results('bad_index.html')


def _assert_parse_results(index_filename, expected=None):
    html_str = read_index(index_filename)
    actual = index_parser.parse(
        base_url='https://pypi.python.org/simple',
        package_path='Sphinx',
        html_str=html_str)
    eq_(actual, expected)

########NEW FILE########
__FILENAME__ = invalid_path_handler_test
from _utils import assert_http_not_found
from ...server_app.handler.invalid_path_handler import InvalidPathHandler


def typical_usage_test():
    def handler_runner():
        InvalidPathHandler().handle(
            path=['path', 'little', 'too', 'long'],
            request=None,
            response=None)

    assert_http_not_found(
        run_handler_fn=handler_runner,
        failure_description='Failed to raise 404 on invalid path')

########NEW FILE########
__FILENAME__ = path_length_dispatcher_test
from nose.tools import eq_
from ...server_app.handler._exception import HandlerException
from ...server_app.http.path_length_dispatcher import PathLengthDispatcher
from _utils import FunctionStub


def test_all_permutations():
    permutations = (
        TestHelper(0, False, False),
        TestHelper(0, True, False),
        TestHelper(0, False, True),

        TestHelper(1, False, False),
        TestHelper(1, True, False),
        TestHelper(1, False, True),

        TestHelper(2, False, False),
        TestHelper(2, True, False),
        TestHelper(2, False, True),
    )

    for permutation in permutations:
        yield permutation.perform_assertions


class _UniqueException(Exception):
    pass


class TestHelper(object):
    def __init__(
            self,
            number_of_handlers,
            normal_handlers_do_throw_exceptions,
            exception_handler_does_throw_exception):

        self.number_of_handlers = number_of_handlers

        self.normal_handlers_do_throw_exceptions \
            = normal_handlers_do_throw_exceptions
        self.exception_handler_does_throw_exception \
            = exception_handler_does_throw_exception

        self.normal_handlers = _create_normal_handlers(
            number_of_handlers,
            normal_handlers_do_throw_exceptions)

        self.exception_handler = _create_exception_handler(
            exception_handler_does_throw_exception)

        self.dispatcher = PathLengthDispatcher(
            handlers_indexed_by_path_length=self.normal_handlers,
            invalid_path_handler=self.exception_handler)

    def _assert_normal_handler_behavior(self):
        for n in xrange(self.number_of_handlers):
            try:
                path = ['item'] * n
                actual_result = self.dispatcher.default(*path)
                eq_(actual_result, self.normal_handlers[n].dummy_result)

            except _UniqueException:
                assert self.normal_handlers_do_throw_exceptions, \
                    'Caught unexpected exception from normal handler'

    def _assert_exception_handler_behavior(self):
        try:
            path = ['item'] * self.number_of_handlers
            actual_result = self.dispatcher.default(*path)
            eq_(actual_result, self.exception_handler.dummy_result)

        except _UniqueException:
            assert self.exception_handler_does_throw_exception, \
                'Caught unexpected exception from invalid path handler'

    def perform_assertions(self):
        self._assert_normal_handler_behavior()
        self._assert_exception_handler_behavior()


def _create_normal_sad_handlers(number_of_handlers):
    handlers = []
    for n in xrange(number_of_handlers):
        handlers.append(FunctionStub(
            name='Path length {} handler'.format(n),
            dummy_exception=HandlerException(
                wrapped_exception=_UniqueException)))
    return handlers


def _create_normal_happy_handlers(number_of_handlers):
    handlers = []
    for n in xrange(number_of_handlers):
        handlers.append(FunctionStub(
            name='Path length {} handler'.format(n),
            dummy_result='Path length {} handler result'.format(n)))
    return handlers


def _create_sad_exception_handler():
    handler = FunctionStub(
        name='Invalid path handler',
        dummy_exception=_UniqueException)
    return handler


def _create_happy_exception_handler():
    handler = FunctionStub(
        name='Invalid path handler',
        dummy_result='Invalid path handler result')
    return handler


def _create_normal_handlers(
        number_of_handlers,
        normal_handlers_do_throw_exceptions):

    if normal_handlers_do_throw_exceptions:
        handlers = _create_normal_sad_handlers(number_of_handlers)
    else:
        handlers = _create_normal_happy_handlers(number_of_handlers)
    return handlers


def _create_exception_handler(
        exception_handler_does_throw_exception):

    if exception_handler_does_throw_exception:
        exception_handler = _create_sad_exception_handler()
    else:
        exception_handler = _create_happy_exception_handler()
    return exception_handler

########NEW FILE########
__FILENAME__ = pypi_index_handler_test
from functools import partial
from lxml.etree import ParseError
from nose.tools import eq_
from requests import RequestException
from _utils import RequestStub, ResponseStub, FunctionStub
from _utils import assert_http_redirect, assert_http_not_found
from ...server_app.handler.pypi_index_handler import PyPIIndexHandler


def typical_usage_as_index_test():
    _check_main_index_path(
        path=['python', 'nose'],
        is_index=True)


def typical_usage_not_index_test():
    handler_runner = partial(
        _check_main_index_path,
        path=['python', 'nose'],
        is_index=False)

    assert_http_redirect(
        run_handler_fn=handler_runner,
        expected_url='nose/',
        expected_status=301,
        failure_description='Index handler did not redirect to directory')


def http_get_fn_exception_test():
    handler_runner = partial(
        _check_main_index_path,
        path=['python', 'nose'],
        is_index=True,
        http_get_exception=RequestException())

    assert_http_not_found(
        run_handler_fn=handler_runner,
        failure_description='Failed to return 404 on failure to get index')


def parse_index_fn_exception_test():
    handler_runner = partial(
        _check_main_index_path,
        path=['python', 'nose'],
        is_index=True,
        parse_index_exception=ParseError(None, None, None, None))

    assert_http_not_found(
        run_handler_fn=handler_runner,
        failure_description='Failed to return 404 on failure to parse index')


def non_python_root_path_test():
    handler_runner = partial(
        _check_main_index_path,
        path=['not_python', 'nose'],
        is_index=True)

    assert_http_not_found(
        run_handler_fn=handler_runner,
        failure_description='Failed to return 404 on non-"/python/" path')


def _check_main_index_path(
        path,
        is_index,
        http_get_exception=None,
        parse_index_exception=None):

    pypi_base_url = 'http://dumb_url.com'
    builder_response = 'be dumb builder'
    parser_response = 'be dumb parser'
    html_get_response = 'be dumb html'
    py, package_path = path

    html_get_stub = FunctionStub(
        name='HTML Get',
        dummy_result=html_get_response,
        dummy_exception=http_get_exception)

    parser_stub = FunctionStub(
        name='Parser',
        dummy_result=parser_response,
        dummy_exception=parse_index_exception)

    builder_stub = FunctionStub(
        name='Builder',
        dummy_result=builder_response)

    handler = PyPIIndexHandler(
        pypi_base_url=pypi_base_url,
        http_get_fn=html_get_stub,
        parse_index_fn=parser_stub,
        build_index_fn=builder_stub)

    request = RequestStub(is_index=is_index)
    response = ResponseStub()

    response_str = handler.handle(
        path=path,
        request=request,
        response=response)

    eq_(response.headers, {},
        msg='Headers are expected to be unaffected')

    eq_(response_str, builder_response,
        msg='Handler did not return builder result')

    builder_stub.assert_single_kw_call(expected_kwargs={
        'index_rows': parser_response})

    parser_stub.assert_single_kw_call(expected_kwargs={
        'base_url': pypi_base_url,
        'package_path': package_path,
        'html_str': html_get_response})

########NEW FILE########
__FILENAME__ = root_index_handler_test
from collections import OrderedDict
from functools import partial
from nose.tools import eq_
from _utils import RequestStub, FunctionStub, ResponseStub
from _utils import assert_http_redirect
from ...server_app.handler.root_index_handler import RootIndexHandler


def empty_path_is_index_test():
    _check_root_path([], is_index=True)


def empty_path_not_index_test():
    handler_runner = partial(
        _check_root_path,
        path=[],
        is_index=False)

    assert_http_redirect(
        run_handler_fn=handler_runner,
        expected_url='/',
        expected_status=301,
        failure_description='Index handler did not redirect to directory')


def _check_root_path(path, is_index):
    dumb_response = "be dumb"

    builder_stub = FunctionStub(
        name='Builder',
        dummy_result=dumb_response)

    handler = RootIndexHandler(build_index_fn=builder_stub)
    request = RequestStub(is_index=is_index)
    response = ResponseStub()

    response_str = handler.handle(
        path=path,
        request=request,
        response=response)

    eq_(response.headers, {},
        msg='Headers are expected to be unaffected')

    eq_(response_str, dumb_response,
        msg='Handler did not return builder result')

    builder_stub.assert_single_kw_call(expected_kwargs={
        'index_rows': OrderedDict([('python/', None)])})

########NEW FILE########
__FILENAME__ = _utils
import os
from nose.tools import eq_
from ...server_app.handler._exception import HandlerException


def read_index(filename):
    index_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'resources', filename)

    with open(index_path) as f:
        return f.read()


class FunctionStub(object):
    def __init__(self, name, dummy_result=None, dummy_exception=None):
        self.name = name
        self.dummy_result = dummy_result
        self.dummy_exception = dummy_exception
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))

        if self.dummy_exception is not None:
            raise self.dummy_exception

        return self.dummy_result

    def assert_single_kw_call(self, expected_kwargs):
        eq_(len(self.calls), 1,
            msg='{} was called more than once'.format(self.name))

        eq_(len(self.calls[0][0]), 0,
            msg='{} was called with non-named arguments'.format(self.name))

        eq_(self.calls[0][1], expected_kwargs,
            msg='{} was not called with expected arguments'.format(self.name))


class RequestStub(object):
    def __init__(self, is_index):
        self.is_index = is_index


class ResponseStub(object):
    def __init__(self):
        self.headers = {}


def assert_http_not_found(run_handler_fn, failure_description):
    try:
        run_handler_fn()

    except HandlerException as e:
        kwargs = e.wrapped_exception.keywords

        assert 'status' in kwargs, \
            'No http status specified ' \
            '(expected `status` keyword)'

        eq_(kwargs['status'], 404,
            msg='Expected 404 http status')

    except:
        raise AssertionError('Failed to raise a HandlerException')

    else:
        raise AssertionError(failure_description)


def assert_http_redirect(
        run_handler_fn,
        expected_url,
        expected_status,
        failure_description):
    try:
        run_handler_fn()

    except HandlerException as e:
        kwargs = e.wrapped_exception.keywords

        assert 'urls' in kwargs, \
            'No URL specified for redirection ' \
            '(expected `urls` keyword argument)'

        assert 'status' in kwargs, \
            'No redirect status specified ' \
            '(expected `status` keyword argument)'

        eq_(kwargs['urls'], expected_url,
            msg='Incorrect redirection URL')

        eq_(kwargs['status'], expected_status,
            msg='Incorrect redirection status')

    except:
        raise AssertionError('Failed to raise a HandlerException')

    else:
        raise AssertionError(failure_description)

########NEW FILE########
__FILENAME__ = __main__
from server_app.launcher import run_server


if __name__ == '__main__':
    run_server()

########NEW FILE########
__FILENAME__ = artif_test
from nose.plugins.attrib import attr
from nose.tools import eq_, with_setup
from _fixture import create_fixture
from _utils import assert_sphinx_packages
from _proxy_test_helper import proxy_brought_down
import _assertion_helper


fixture = create_fixture()


def setup_module():
    fixture.artif.block_until_up()
    fixture.proxy.start()
    fixture.proxy.block_until_up()


def teardown_module():
    fixture.artif.flush_caches()
    fixture.proxy.stop()


@with_setup(setup=fixture.artif.flush_caches)
def artif_root_test():
    actual_result = fixture.artif.parse_listing()
    expected_result = ('python/',)
    eq_(actual_result, expected_result)


@with_setup(setup=fixture.artif.flush_caches)
def artif_pypi_root_no_slash_test():
    _assert_404_for_artif_path(path='python')


@attr('known_artif_bug')
@with_setup(setup=fixture.artif.flush_caches)
def artif_pypi_root_nothing_cached_test():
    _assert_404_for_artif_path(path='python/')


@attr('known_artif_bug')
@with_setup(setup=fixture.artif.flush_caches)
def artif_pypi_root_one_cached_test():
    fixture.artif.cache_packages(
        'python/Sphinx/Sphinx-1.1.3.tar.gz',
    )
    actual_result = fixture.artif.parse_listing(path='python/')

    eq_(len(actual_result), 2)
    assert '../' in actual_result
    assert 'Sphinx/' in actual_result


@attr('known_artif_bug')
@with_setup(setup=fixture.artif.flush_caches)
def artif_pypi_root_three_cached_test():
    fixture.artif.cache_packages(
        'python/3to2/3to2-1.0.tar.gz',
        'python/nose/nose-1.3.0.tar.gz',
        'python/Sphinx/Sphinx-1.1.3.tar.gz',
    )
    actual_result = fixture.artif.parse_listing(path='python/')

    eq_(len(actual_result), 4)
    assert '../' in actual_result
    assert '3to2/' in actual_result
    assert 'nose/' in actual_result
    assert 'Sphinx/' in actual_result


@with_setup(setup=fixture.artif.flush_caches)
def artif_uppercase_sphinx_no_slash_test():
    _assert_404_for_artif_path(path='python/Sphinx')


@with_setup(setup=fixture.artif.flush_caches)
def artif_lowercase_sphinx_no_slash_test():
    _assert_404_for_artif_path(path='python/sphinx')


@with_setup(setup=fixture.artif.flush_caches)
def artif_uppercase_sphinx_test():
    actual_result = fixture.artif.parse_listing(path='python/Sphinx/')
    assert_sphinx_packages(actual_result)


@with_setup(setup=fixture.artif.flush_caches)
def artif_lowercase_sphinx_test():
    actual_result = fixture.artif.parse_listing(path='python/sphinx/')
    assert_sphinx_packages(actual_result)


@with_setup(setup=fixture.artif.flush_caches)
def artif_invalid_package_test():
    _assert_404_for_artif_path(path='python/NotARealPackage/')


@with_setup(setup=fixture.artif.flush_caches)
def artif_invalid_file_test():
    _assert_404_for_artif_path(path='python/Sphinx/NotARealFile.tar.gz')


@with_setup(teardown=fixture.artif.flush_caches)
def get_uppercase_sphinx_package_test():
    _assert_package_retrieval_behavior(lowercase=False)


@with_setup(teardown=fixture.artif.flush_caches)
def get_lowercase_sphinx_package_test():
    _assert_package_retrieval_behavior(lowercase=True)


def _assert_404_for_artif_path(path):
    actual_result = fixture.artif.get_repo_url(path=path)
    eq_(actual_result.status_code, 404)


def _assert_package_retrieval_behavior(lowercase):
    helper = _assertion_helper.SphinxHelper(
        get_path_fn=fixture.artif.get_repo_url,
        lowercase=lowercase)

    _assertion_helper.perform_package_not_cached_assertions(helper)
    _assertion_helper.perform_package_cached_assertions(
        sphinx_helper=helper,
        expect_artifactory_specific_headers=True)

    with proxy_brought_down(fixture.proxy):
        _assertion_helper.perform_package_cached_assertions(
            sphinx_helper=helper,
            expect_artifactory_specific_headers=True)

        fixture.artif.flush_caches()
        _assertion_helper.perform_package_unavailable_assertions(helper)

########NEW FILE########
__FILENAME__ = proxy_test
from nose.tools import eq_
from _fixture import create_fixture
import _assertion_helper


fixture = create_fixture()


def setup_module():
    fixture.proxy.start()
    fixture.proxy.block_until_up()


def teardown_module():
    fixture.proxy.stop()


def proxy_root_trailing_slash_test():
    actual_result = fixture.proxy.parse_listing()
    expected_result = ('python/',)
    eq_(actual_result, expected_result)


def proxy_root_no_trailing_slash_test():
    _assert_redirect_for_proxy_path(
        from_path='python',
        to_path='python/',
        expected_code=301)


def proxy_python_trailing_slash_test():
    actual_result = fixture.proxy.parse_listing(path='python/')
    assert '3to2/' in actual_result
    assert 'nose/' in actual_result
    assert 'Sphinx/' in actual_result


def proxy_python_no_trailing_slash_test():
    _assert_redirect_for_proxy_path(
        from_path='python',
        to_path='python/',
        expected_code=301)


def proxy_nose_trailing_slash_test():
    actual_result = fixture.proxy.parse_listing(path='python/nose/')
    assert 'nose-1.2.1.tar.gz' in actual_result
    assert 'nose-1.3.0.tar.gz' in actual_result


def proxy_nose_no_trailing_slash_test():
    _assert_redirect_for_proxy_path(
        from_path='python/nose',
        to_path='python/nose/',
        expected_code=301)


def proxy_get_sphinx_uppercase_test():
    _assert_package_retrieval_behavior(lowercase=False)


def proxy_get_sphinx_lowercase_test():
    _assert_package_retrieval_behavior(lowercase=True)


def _assert_redirect_for_proxy_path(from_path, to_path, expected_code):
    expected_location = fixture.proxy.get_path(path=to_path)
    actual_result = fixture.proxy.get_url(path=from_path)

    eq_(len(actual_result.history), 1)
    eq_(actual_result.history[0].status_code, expected_code)
    eq_(actual_result.history[0].headers['location'], expected_location)
    eq_(actual_result.status_code, 200)


def _assert_404_for_proxy_path(path):
    actual_result = fixture.proxy.get_url(path=path)
    eq_(actual_result.status_code, 404)


def _assert_package_retrieval_behavior(lowercase):
    helper = _assertion_helper.SphinxHelper(
        get_path_fn=fixture.proxy.get_url,
        lowercase=lowercase)

    # The package cached assertions are the only ones relevant to
    # the proxy. Since Artifactory is out of the picture, the cache
    # within Artifactory is irrelevant.
    _assertion_helper.perform_package_cached_assertions(
        sphinx_helper=helper,
        expect_artifactory_specific_headers=False)

########NEW FILE########
__FILENAME__ = _artifactory_test_helper
import requests
from _utils import return_when_web_service_up, parse_listing


class ArtifactoryTestHelper(object):
    def __init__(self, base_url, pypi_repo_id, clean_credentials):
        self.base_url = base_url
        self.pypi_repo_id = pypi_repo_id
        self.pypi_cache_repo_id = pypi_repo_id + '-cache'
        self.clean_credentials = clean_credentials

    def __get_path(self, path):
        url = '/'.join((self.base_url, self.pypi_repo_id, path.lstrip('/')))
        return url

    def block_until_up(self, attempts=5):
        url = '/'.join((self.base_url, 'api/system/ping'))
        return_when_web_service_up(
            health_check_url=url,
            attempts=attempts)

    def flush_caches(self):
        url = '/'.join((self.base_url, self.pypi_cache_repo_id))
        result = requests.delete(url, auth=self.clean_credentials)

        # 404 is returned when there are no artifacts to remove - this is okay.
        if result.status_code != 404:
            # Otherwise, check the return status for an error.
            result.raise_for_status()

    def get_repo_url(self, path='', only_headers=False):
        url = self.__get_path(path)
        result = requests.head(url) if only_headers else requests.get(url)
        return result

    def parse_listing(self, path=''):
        url = self.__get_path(path)
        return parse_listing(url)

    def cache_packages(self, *paths):
        for p in paths:
            r = self.get_repo_url(path=p)
            r.raise_for_status()

########NEW FILE########
__FILENAME__ = _assertion_helper
from functools import partial
from nose.tools import eq_


def _validate_content_type(expected_type, result):
    eq_(result.headers['Content-Type'], expected_type)


def _validate_content_length(expected_length, result):
    eq_(int(result.headers['content-length']), expected_length)


def _validate_md5(expected_md5, result):
    eq_(result.headers['x-checksum-md5'], expected_md5)


def _validate_text(expected_text, result):
    eq_(result.text, expected_text)


def _validate_404(result):
    eq_(result.status_code, 404)


class SphinxHelper(object):
    def __init__(self, get_path_fn, lowercase=False):
        self._package_prefix = 'python/{}/'.format(
            'sphinx' if lowercase else 'Sphinx')

        self.get_path_fn = get_path_fn
        self.expected_md5_checksum = '8f55a6d4f87fc6d528120c5d1f983e98'

    def __get_path_and_perform_validations(self, path, validate_fn_list):
        result = self.get_path_fn(path)

        for v in validate_fn_list:
            v(result)

    def perform_md5_validations(self, validators):
        self.__get_path_and_perform_validations(
            self._package_prefix + '/Sphinx-1.1.3.tar.gz.md5',
            validators)

    def perform_sha1_validations(self, validators):
        self.__get_path_and_perform_validations(
            self._package_prefix + '/Sphinx-1.1.3.tar.gz.sha1',
            validators)

    def perform_primary_artifact_validations(self, validators):
        self.__get_path_and_perform_validations(
            self._package_prefix + '/Sphinx-1.1.3.tar.gz',
            validators)


def perform_package_not_cached_assertions(sphinx_helper):
    sphinx_helper.perform_md5_validations((_validate_404,))
    sphinx_helper.perform_sha1_validations((_validate_404,))
    sphinx_helper.perform_primary_artifact_validations(
        (partial(_validate_content_length, 2632059),
         partial(_validate_md5, '8f55a6d4f87fc6d528120c5d1f983e98'),)
    )


def perform_package_cached_assertions(
        sphinx_helper,
        expect_artifactory_specific_headers):

    sphinx_helper.perform_md5_validations((
        partial(_validate_text, sphinx_helper.expected_md5_checksum),
        partial(_validate_content_type, 'application/x-checksum'),
    ))

    sphinx_helper.perform_sha1_validations((_validate_404,))

    primary_artifact_validators = [
        partial(_validate_content_length, 2632059)]

    if expect_artifactory_specific_headers:
        primary_artifact_validators.append(
            partial(_validate_md5, sphinx_helper.expected_md5_checksum))

    sphinx_helper.perform_primary_artifact_validations(
        primary_artifact_validators)


def perform_package_unavailable_assertions(sphinx_helper):
    sphinx_helper.perform_md5_validations((_validate_404,))
    sphinx_helper.perform_sha1_validations((_validate_404,))
    sphinx_helper.perform_primary_artifact_validations((_validate_404,))

########NEW FILE########
__FILENAME__ = _fixture
from functools import partial
from _artifactory_test_helper import ArtifactoryTestHelper
from _proxy_test_helper import ProxyTestHelper


class Fixture(object):
    def __init__(
            self,
            artif_base_url,
            pypi_repo_id,
            proxy_base_url,
            clean_cache_auth):

        self.artif = ArtifactoryTestHelper(
            base_url=artif_base_url.strip('/'),
            pypi_repo_id=pypi_repo_id.strip('/'),
            clean_credentials=clean_cache_auth)

        self.proxy = ProxyTestHelper(
            base_url=proxy_base_url.strip('/'))


create_fixture = partial(
    Fixture,
    artif_base_url='http://localhost:8081/artifactory',
    pypi_repo_id='pypi-remote',
    proxy_base_url='http://localhost:9292',
    clean_cache_auth=('admin', 'password'))

########NEW FILE########
__FILENAME__ = _proxy_test_helper
import subprocess
import sys
import requests
from _utils import return_when_web_service_up, return_when_web_service_down
from _utils import parse_listing


class ProxyTestHelper(object):
    def __init__(self, base_url):
        self.base_url = base_url

    def start(self):
        self.process = subprocess.Popen(
            [sys.executable, '-m', 'pypi_redirect'])

    def stop(self):
        self.process.terminate()

    def block_until_up(self, attempts=10):
        return_when_web_service_up(
            health_check_url=self.base_url,
            attempts=attempts)

    def block_until_down(self, attempts=5):
        return_when_web_service_down(
            health_check_url=self.base_url,
            attempts=attempts)

    def get_path(self, path):
        url = '/'.join((self.base_url, path.lstrip('/')))
        return url

    def get_url(self, path='', only_headers=False):
        url = self.get_path(path)
        result = requests.head(url) if only_headers else requests.get(url)
        return result

    def parse_listing(self, path=''):
        url = self.get_path(path)
        return parse_listing(url)


def proxy_brought_down(proxy):
    class Context(object):
        def __enter__(self):
            proxy.stop()
            proxy.block_until_down()

        def __exit__(self, exc_type, exc_val, exc_tb):
            proxy.start()
            proxy.block_until_up()

    return Context()

########NEW FILE########
__FILENAME__ = _utils
from time import sleep
from pypi_redirect.server_app import index_parser
import requests


def return_when_web_service_up(health_check_url, attempts=5):
    while True:
        try:
            response = requests.get(health_check_url)
            response.raise_for_status()
        except requests.RequestException:
            pass
        else:
            break

        if attempts <= 0:
            raise AssertionError(
                'Failed to connect to {}'.format(health_check_url))

        attempts -= 1
        sleep(1)


def return_when_web_service_down(health_check_url, attempts=5):
    while True:
        try:
            response = requests.get(health_check_url)
            response.raise_for_status()
        except requests.RequestException:
            break

        if attempts <= 0:
            raise AssertionError(
                'Still connected to {}'.format(health_check_url))

        attempts -= 1
        sleep(1)


def find_all_links(html_root):
    return html_root.xpath(".//a")


def assert_sphinx_packages(listed_packages):
    assert 'Sphinx-1.1-py2.7.egg' in listed_packages
    assert 'Sphinx-1.1-py2.7.egg.md5' in listed_packages
    assert 'Sphinx-1.1.3.tar.gz' in listed_packages
    assert 'Sphinx-1.1.3.tar.gz.md5' in listed_packages


def parse_listing(url):
    result = requests.get(url)
    result.raise_for_status()

    html_str = result.text

    # Our index_parser.parse is very well unit-tested.
    rows = index_parser.parse(
        base_url=url,
        package_path='',
        html_str=html_str,
        strict_html=False,
        find_links_fn=find_all_links)

    return tuple(rows.iterkeys())

########NEW FILE########
