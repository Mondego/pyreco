__FILENAME__ = auth
# -*- coding: utf-8 -*-

import os.path
import json
from collections import namedtuple, defaultdict
from .extensions import Extensible
from .browser import Cell, cut_from_string, cut_from_dict, PointCut
from .browser import string_to_drilldown
from .errors import *
from .common import read_json_file, sorted_dependencies

__all__ = (
    "Authorizer",
    "SimpleAuthorizer",
    "NotAuthorized",
    "right_from_dict"
)

ALL_CUBES_WILDCARD = '*'

class NotAuthorized(UserError):
    """Raised when user is not authorized for the request."""
    # Note: This is not called NotAuthorizedError as it is not in fact an
    # error, it is just type of signal.


class Authorizer(Extensible):
    def authorize(self, token, cubes):
        """Returns list of authorized cubes from `cubes`. If none of the cubes
        are authorized an empty list is returned.

        Default implementation returs the same `cubes` list as provided.
        """
        return cubes

    def restricted_cell(self, token, cube, cell=None):
        """Restricts the `cell` for `cube` according to authorization by
        `token`. If no cell is provided or the cell is empty then returns
        the restriction cell. If there is no restriction, returns the original
        `cell` if provided or `None`.
        """
        return cell

    def hierarchy_limits(self, token, cube):
        """Returns a list of tuples: (`dimension`, `hierarchy`, `level`)."""
        # TODO: provisional feature, might change
        return []


class NoopAuthorizer(Authorizer):
    def __init__(self):
        super(NoopAuthorizer, self).__init__()


class _SimpleAccessRight(object):
    def __init__(self, roles, allowed_cubes, denied_cubes, cell_restrictions,
                 hierarchy_limits):
        self.roles = set(roles) if roles else set([])
        self.cell_restrictions = cell_restrictions or {}

        self.hierarchy_limits = defaultdict(list)

        if hierarchy_limits:
            for cube, limits in hierarchy_limits.items():
                for limit in limits:
                    if isinstance(limit, basestring):
                        limit = string_to_drilldown(limit)
                    self.hierarchy_limits[cube].append(limit)

        self.hierarchy_limits = dict(self.hierarchy_limits)

        self.allowed_cubes = set(allowed_cubes) if allowed_cubes else set([])
        self.denied_cubes = set(denied_cubes) if denied_cubes else set([])
        self._get_patterns()

    def _get_patterns(self):
        self.allowed_cube_suffix = []
        self.allowed_cube_prefix = []
        self.denied_cube_suffix = []
        self.denied_cube_prefix = []

        for cube in self.allowed_cubes:
            if cube.startswith("*"):
                self.allowed_cube_suffix.append(cube[1:])
            if cube.endswith("*"):
                self.allowed_cube_prefix.append(cube[:-1])

        for cube in self.denied_cubes:
            if cube.startswith("*"):
                self.denied_cube_suffix.append(cube[1:])
            if cube.endswith("*"):
                self.denied_cube_prefix.append(cube[:-1])

    def merge(self, other):
        """Merge `right` with the receiver:

        * `allowed_cubes` are merged (union)
        * `denied_cubes` are merged (union)
        * `cube_restrictions` from `other` with same cube replace restrictions
          from the receiver"""

        self.roles |= other.roles
        self.allowed_cubes |= other.allowed_cubes
        self.denied_cubes |= other.denied_cubes

        for cube, restrictions in other.cell_restrictions.iteritems():
            if not cube in self.cube_restrictions:
                self.cell_restrictions[cube] = restrictions
            else:
                self.cell_restrictions[cube] += restrictions

        for cube, limits  in other.hierarchy_limits.iteritems():
            if not cube in self.hierarchy_limits:
                self.hierarchy_limits[cube] = limits
            else:
                self.hierarchy_limits[cube] += limits

        self._get_patterns()

    def is_allowed(self, name, allow_after_denied=True):

        allow = False
        if self.allowed_cubes:
            if (name in self.allowed_cubes) or \
                        (ALL_CUBES_WILDCARD in self.allowed_cubes):
                allow = True

            if not allow and self.allowed_cube_prefix:
                allow = any(name.startswith(p) for p in self.allowed_cube_prefix)
            if not allow and self.allowed_cube_suffix:
                allow = any(name.endswith(p) for p in self.allowed_cube_suffix)

        deny = False
        if self.denied_cubes:
            if (name in self.denied_cubes) or \
                        (ALL_CUBES_WILDCARD in self.denied_cubes):
                deny = True

            if not deny and self.denied_cube_prefix:
                deny = any(name.startswith(p) for p in self.denied_cube_prefix)
            if not deny and self.denied_cube_suffix:
                deny = any(name.endswith(p) for p in self.denied_cube_suffix)

        """
        Four cases:
            - allow match, no deny match
              * allow_deny: allowed
              * deny_allow: allowed
            - no allow match, deny match
              * allow_deny: denied
              * deny_allow: denied
            - no match in either
              * allow_deny: denied
              * deny_allow: allowed
            - match in both
              * allow_deny: denied
              * deny_allow: allowed
        """

        # deny_allow
        if allow_after_denied:
            return allow or not deny
        # allow_deny
        else:
            return allow and not deny

    def to_dict(self):
        as_dict = {
            "roles": list(self.roles),
            "allowed_cubes": list(self.allowed_cubes),
            "denied_cubes": list(self.denied_cubes),
            "cell_restrictions": self.cell_restrictions,
            "hierarchy_limits": self.hierarchy_limits
        }

        return as_dict


def right_from_dict(info):
    return _SimpleAccessRight(
               roles=info.get('roles'),
               allowed_cubes=info.get('allowed_cubes'),
               denied_cubes=info.get('denied_cubes'),
               cell_restrictions=info.get('cell_restrictions'),
               hierarchy_limits=info.get('hierarchy_limits')
           )

class SimpleAuthorizer(Authorizer):
    __options__ = [
        {
            "name": "rights_file",
            "description": "JSON file with access rights",
            "type": "string"
        },
        {
            "name": "roles_file",
            "description": "JSON file with access right roles",
            "type": "string"
        },
        {
            "name": "order",
            "description": "Order of allow/deny",
            "type": "string",
            "values": ["allow_deny", "deny_allow"]
        },
        {
            "name": "guest",
            "description": "Name of the 'guest' role",
            "type": "string",
        },

    ]

    def __init__(self, rights_file=None, roles_file=None, roles=None,
                 rights=None, identity_dimension=None, order=None,
                 guest=None, **options):
        """Creates a simple JSON-file based authorizer. Reads data from
        `rights_file` and `roles_file` and merge them with `roles` and
        `rights` dictionaries respectively."""

        super(SimpleAuthorizer, self).__init__()

        roles = roles or {}
        rights = rights or {}

        if roles_file:
            content = read_json_file(roles_file, "access roles")
            roles.update(content)

        if rights_file:
            content = read_json_file(rights_file, "access rights")
            rights.update(content)

        self.roles = {}
        self.rights = {}
        self.guest = guest or None

        order = order or "deny_allow"

        if order == "allow_deny":
            self.allow_after_denied = False
        elif order == "deny_allow":
            self.allow_after_denied = True
        else:
            raise ConfigurationError("Unknown allow/deny order: %s" % order)

        # Process the roles
        for key, info in roles.items():
            role = right_from_dict(info)
            self.roles[key] = role

        deps = dict((name, role.roles) for name, role in self.roles.items())
        order = sorted_dependencies(deps)

        for name in order:
            role = self.roles[name]
            for parent_name in role.roles:
                parent = self.roles[parent_name]
                role.merge(parent)

        # Process rights
        for key, info in rights.items():
            right = right_from_dict(info)
            self.rights[key] = right

            for role_name in list(right.roles):
                role = self.roles[role_name]
                right.merge(role)

        if identity_dimension:
            if isinstance(identity_dimension, basestring):
                (dim, hier, _) = string_to_drilldown(identity_dimension)
            else:
                (dim, hier) = identity_dimension[:2]
            self.identity_dimension = dim
            self.identity_hierarchy = hier
        else:
            self.identity_dimension = None
            self.identity_hierarchy = None

    def right(self, token):
        try:
            right = self.rights[token]
        except KeyError:
            # if guest role exists, use it
            if self.guest and self.guest in self.roles:
                return self.roles[self.guest]
            else:
                raise NotAuthorized("Unknown access right '%s'" % token)

        return right

    def authorize(self, token, cubes):
        try:
            right = self.right(token)
        except NotAuthorized:
            return []

        authorized = []

        for cube in cubes:
            cube_name = str(cube)

            if right.is_allowed(cube_name, self.allow_after_denied):
                authorized.append(cube)

        return authorized

    def restricted_cell(self, identity, cube, cell):
        right = self.right(identity)

        cuts = right.cell_restrictions.get(cube.name)

        # Append cuts for "any cube"
        any_cuts = right.cell_restrictions.get(ALL_CUBES_WILDCARD, [])
        if any_cuts:
            cuts += any_cuts

        if cuts:
            restriction_cuts = []
            for cut in cuts:
                if isinstance(cut, basestring):
                    cut = cut_from_string(cut, cube)
                else:
                    cut = cut_from_dict(cut)
                cut.hidden = True
                restriction_cuts.append(cut)

            restriction = Cell(cube, restriction_cuts)
        else:
            restriction = Cell(cube)

        ident_dim = None
        if self.identity_dimension:
            try:
                ident_dim = cube.dimension(self.identity_dimension)
            except NoSuchDimensionError:
                # If cube has the dimension, then use it, otherwise just
                # ignore it
                pass

        if ident_dim:
            hier = ident_dim.hierarchy(self.identity_hierarchy)

            if len(hier) != 1:
                raise ConfigurationError("Identity hierarchy has to be flat "
                                         "(%s in dimension %s is not)"
                                         % (str(hier), str(ident_dim)))

            # TODO: set as hidden
            cut = PointCut(ident_dim, [identity], hierarchy=hier, hidden=True)
            restriction = restriction & Cell(cube, [cut])

        if cell:
            return cell & restriction
        else:
            return restriction

    def hierarchy_limits(self, token, cube):
        right = self.right(token)

        return right.hierarchy_limits.get(str(cube), [])



########NEW FILE########
__FILENAME__ = browser
# -*-coding=utf -*-

from ...browser import *
from .mapper import GoogleAnalyticsMapper
from ...logging import get_logger
from ...calendar import Calendar

# Google Python API Documentation:
# https://developers.google.com/api-client-library/python/start/get_started

_DEFAULT_START_DATE = (2005, 1, 1)

_TYPE_FUNCS = {
    'STRING': str,
    'INTEGER': int,
    'FLOAT': float,
    'PERCENT': lambda x: float(x) / 100.0,
    'TIME': float
}


def _type_func(ga_datatype):
    if ga_datatype is None:
        ga_datatype = 'STRING'
    return _TYPE_FUNCS.get(ga_datatype.upper(), str)


def date_string(path, default_date):
    """Converts YMD path into a YYYY-MM-DD date."""
    # TODO: use Calendar

    path = path or []

    (year, month, day) = tuple(path + [0] * (3 - len(path)))

    year = int(year) or default_date[0]
    month = int(month) or default_date[1]
    day = int(day) or default_date[2]

    return "%04d-%02d-%02d" % (year, month, day)


class GoogleAnalyticsBrowser(AggregationBrowser):
    __extension_name__ = "ga"

    def __init__(self, cube, store, locale=None, **options):

        self.store = store
        self.cube = cube
        self.locale = locale
        self.logger = get_logger()
        self.logger.setLevel("DEBUG")
        self.mapper = GoogleAnalyticsMapper(cube, locale)

        # Note: Make sure that we have our own calendar copy, not workspace
        # calendar (we don't want to rewrite anything shared)
        self.calendar = Calendar(timezone=self.store.timezone)


        self.default_start_date = self.store.default_start_date \
                                        or _DEFAULT_START_DATE
        self.default_end_date = self.store.default_end_date

    def featuers(self):
        return {
            "actions": ["aggregate"]
        }

    def provide_aggregate(self, cell, aggregates, drilldown, split, order,
                          page, page_size, **options):

        aggregate_names = [a.name for a in aggregates]
        native_aggregates = [a for a in aggregates if not a.function]
        native_aggregate_names = [a.name for a in native_aggregates]

        result = AggregationResult(cell=cell, aggregates=aggregates,
                                   drilldown=drilldown)

        #
        # Prepare the request:
        #
        filters = self.condition_for_cell(cell)
        start_date, end_date = self.time_condition_for_cell(cell)

        # Prepare drilldown:
        dimension_attrs = []
        for item in drilldown:
            dimension_attrs += [l.key for l in item.levels]

        refs = [self.mapper.physical(attr) for attr in dimension_attrs]
        dimensions = ",".join(refs)

        metrics = [self.mapper.physical(a) for a in aggregates]
        metrics = ",".join(metrics)

        if page is not None and page_size is not None:
            max_results = page_size
            start_index = (page * page_size) + 1
        else:
            max_results = None
            start_index = None

        self.logger.debug("GA query: date from %s to %s, dims:%s metrics:%s"
                          % (start_date, end_date, dimensions, metrics))

        response = self.store.get_data(start_date=start_date,
                                       end_date=end_date,
                                       filters=filters,
                                       dimensions=dimensions,
                                       metrics=metrics,
                                       start_index=start_index,
                                       max_results=max_results)

        # TODO: remove this debug once satisfied
        import json
        print "=== RESPONSE:"
        print json.dumps(response, indent=4)

        attributes = dimension_attrs + aggregates
        labels = [attr.ref() for attr in attributes]
        rows = response["rows"]
        data_types = [ _type_func(c.get('dataType')) for c in response['columnHeaders'] ]

        rows = [ map(lambda i: i[0](i[1]), zip(data_types, row)) for row in rows ]
        if drilldown:
            result.cells = [dict(zip(labels, row)) for row in rows]
            # TODO: Use totalsForAllResults
            result.summary = None
        else:
            result.summary = dict(zip(labels, rows[0]))

        # Set the result cells iterator (required)
        result.labels = labels

        result.total_cell_count = response["totalResults"]

        return result

    def condition_for_cell(self, cell):
        conditions = []

        for cut in cell.cuts:
            if str(cut.dimension) == "time":
                continue

            # TODO: we consider GA dims to be flat
            dim = self.mapper.physical(cut.dimension.all_attributes[0])

            if isinstance(cut, PointCut):
                condition = "%s%s%s" % (dim, "!=" if cut.invert else "==", cut.path[0])
            elif isinstance(cut, RangeCut):

                if cut.from_path:
                    cond_from = "%s%s%s" % (dim, "<" if cut.invert else ">=", cut.from_path[0])
                else:
                    cond_from = None

                if cut.to_path:
                    cond_to = "%s%s%s" % (dim, ">" if cut.invert else "<=", cut.to_path[0])
                else:
                    cond_to = None

                if cond_from and cond_to:
                    condition = "%s;%s" % (cond_to, cond_from)
                else:
                    condition = cond_to or cond_from

            elif isinstance(cut, SetCut):
                sublist = []
                for value in cut.paths:
                    cond = "%s%s%s" % (dim, "!=" if cut.invert else "==", value)
                    sublist.append(cond)
                condition = ",".join(sublist)

            conditions.append(condition)

        if conditions:
            return ";".join(conditions)
        else:
            return None

    def time_condition_for_cell(self, cell):
        cut = cell.cut_for_dimension("time")
        if not cut:
            from_path = None
            to_path = None
        else:
            if isinstance(cut, RangeCut):
                from_path = cut.from_path
                to_path = cut.to_path
            elif isinstance(cut, PointCut):
                from_path = cut.path
                to_path = cut.path
            else:
                raise ArgumentError("Unsupported time cut type %s"
                                    % str(type(cut)))

        units = ("year", "month", "day")
        start = date_string(from_path, self.default_start_date)

        if self.default_end_date:
            end = date_string(to_path, self.default_end_date)
        else:
            end = date_string(to_path, self.calendar.now_path(units))

        return (start, end)

########NEW FILE########
__FILENAME__ = mapper
# -*- coding=utf -*-

from ...mapper import Mapper
from ...errors import *

__all__ = (
    "GoogleAnalyticsMapper",
    "ga_id_to_identifier"
)

def ga_id_to_identifier(ga_id):
    """Convert GA attribute/object ID to identifier."""
    if ga_id.startswith("ga:"):
        return ga_id[3:]
    else:
        raise InternalInconsistencyError("Unexpected GA attribute name"
                                         % ga_id)

class GoogleAnalyticsMapper(Mapper):
    def __init__(self, cube, locale=None, **options):
        super(GoogleAnalyticsMapper, self).__init__(cube, locale, **options)
        # ... other initialization here ...
        self.mappings = cube.mappings or {}

    def physical(self, attribute, locale=None):
        # See also: ga_id_to_identifier
        logical = self.logical(attribute, locale)

        if logical in self.mappings:
            return self.mappings[logical]
        else:
            return "ga:" + attribute.name

########NEW FILE########
__FILENAME__ = store
# -*-coding=utf -*-

"""Google Analytics backend for Cubes

Required packages:

    pyopenssl
    google-api-python-client

"""

from ...errors import *
from ...logging import get_logger
from ...stores import Store
from ...providers import ModelProvider
from ...model import Cube, create_dimension, aggregate_list
from .mapper import ga_id_to_identifier
import pkgutil
import json
from collections import defaultdict

from apiclient.errors import HttpError
from apiclient.discovery import build
from oauth2client.client import AccessTokenRefreshError

from collections import OrderedDict

import re

try:
    from oauth2client.client import SignedJwtAssertionCredentials
except ImportError:
    from ...common import MissingPackage
    SignedJwtAssertionCredentials = MissingPackage("oauth2client.crypt",
        "Google Analytics Backend with SignedJwtAssertionCredentials; " +
        "you may need to install pyopenssl and OpenSSL")

try:
    import httplib2
except ImportError:
    from ...common import MissingPackage
    httplib2 = MissingPackage("httplib2", "Google Analytics Backend")


# .js file that contains structure with definition of GA cubes – relation
# between metrics and dimensions that can be used together in a query
# Note: this is kind-of workaround, since GA metadata API does not provide a
# way to get this information
_GA_CUBES_JS = "https://developers.google.com/apps/js/analytics_dm/analytics_dm_js-bundle.js"

GA_TIME_DIM_METADATA = {
    "name": "time",
    "role": "time",
    "levels": [
        { "name": "year", "label": "Year" },
        { "name": "month", "label": "Month", "info": { "aggregation_units": 3 }},
        { "name": "day", "label": "Day", "info": { "aggregation_units": 7 } },
    ],
    "hierarchies": [
        {"name": "ymd", "levels": ["year", "month", "day"]},
    ],
    "default_hierarchy_name": "ymd"
}


_MEASUREMENT_TYPES = {
    'PERCENT': 'percent'
    }

def is_dimension(item):
    return item["type"] == "DIMENSION"

def is_metric(item):
    return item["type"] == "METRIC"

class GoogleAnalyticsModelProvider(ModelProvider):
    __extension_name__ = "ga"
    def __init__(self, *args, **kwargs):
        super(GoogleAnalyticsModelProvider, self).__init__(*args, **kwargs)

        self.logger = get_logger()
        self.logger.setLevel("DEBUG")

        self.ga_concepts = {};
        self.ga_measures = {};
        self.ga_dimensions = {};
        self.ga_cubes = []
        self.cube_to_group = {}
        self.group_to_cube = {}

    def requires_store(self):
        return True

    def public_dimensions(self):
        return []

    def initialize_from_store(self):
        self._refresh_metadata()

    def _measurement_type_for(self, datatype):
        return _MEASUREMENT_TYPES.get(datatype, None)

    def _refresh_metadata(self):
        """Load GA metadata. Group metrics and dimensions by `group`"""
        # TODO: move this request to the store for potential re-authentication
        rq = self.store.service.metadata().columns()
        columns = rq.list(reportType='ga').execute()

        # Note: no Cubes model related logic should be here (such as name
        # mangling)

        self.ga_metrics = OrderedDict()
        self.ga_dimensions = OrderedDict()
        self.ga_concepts = OrderedDict()
        self.ga_group_metrics = OrderedDict()

        for item in columns["items"]:
            # Get the id from the "outer" dictionary and keep juts the "inner"
            # dictionary
            item_id = item["id"]
            item = item["attributes"]
            item["id"] = item_id

            if item.get('status') == 'DEPRECATED':
                self.logger.debug("Discarding deprecated item %s" % item_id)
                continue

            if item_id.find("XX") != -1:
                self.logger.debug("Discarding template item %s (not implemented)" % item_id)
                continue

            self.ga_concepts[item_id] = item

            group = item["group"]
            if group not in self.ga_group_metrics:
                self.ga_group_metrics[group] = []

            if is_metric(item):
                self.ga_group_metrics[group].append(item)
                self.ga_metrics[item_id] = item
            elif is_dimension(item):
                self.ga_dimensions[item_id] = item
            else:
                self.logger.debug("Unknown metadata item type: %s (id: %s)"
                                  % (item["type"], item["id"]))

        self.ga_group_dims = OrderedDict()

        # TODO: enable this for dimension filtering
        # self._get_ga_cubes()

        self.cube_to_group = {}
        self.group_to_cube = {}
        self.ga_cubes = []

        for group, items in self.ga_group_metrics.items():
            dims = OrderedDict(self.ga_dimensions)

            name = re.sub("[^\w0-9_]", "_", group.lower())
            self.cube_to_group[name] = group
            self.group_to_cube[group] = name
            self.ga_cubes.append(name)

            # TODO: filter the dimensions here using _ga_cubes


            # self.ga_group_dims[group] = dims
            # metrics = set(metric["id"] for metric in items)

            # print "=== GROUP: %s" % group

            # for cube, cube_items in self.cube_concepts.items():
            #     diff = metrics - cube_items
            #     if not diff:
            #         continue

            #     if len(diff) != len(metrics):
            #         dstr = ", ".join(list(diff))
            #         print "---    incompatible metrics: %s" % (dstr, )

            self.ga_group_dims[group] = dims.values()

    def _get_ga_cubes(self):
        """Download ga cubes"""
        # Fetch cubes
        http = httplib2.Http()
        (response, content) = http.request(_GA_CUBES_JS)
        # TODO: if this fails, get locally stored copy

        # Get the _ga.cubes = {} structure from the script:
        #
        #     _ga.cubes = {
        #       ... structure data ...
        #     }
        #
        result = re.search(r"(^_ga\.cubes = )(?P<struct>{.*^}$)",
                           content, re.MULTILINE | re.DOTALL)
        groups = result.groups()
        struct = result.group("struct")

        cube_concepts = defaultdict(set)
        self.ga_cubes = []
        # Convert the quotes and parse as JSON string
        cubes = json.loads(struct.replace("'", "\""))
        for cube, concepts in cubes.items():
            self.logger.debug("GA cube: %s" % cube)
            name = re.sub("^Cube:analytics/", "", cube)
            self.ga_cubes.append(name);

            for concept_name in concepts.keys():
                try:
                    concept = self.ga_concepts[concept_name]
                except KeyError:
                    continue

                if "cubes" not in concept:
                    concept["cubes"] = set()
                concept["cubes"].add(name)

                cube_concepts[name].add(concept["id"])

        self.cube_concepts = cube_concepts

    def cube(self, name, locale=None):
        """Create a GA cube:

        * cube is a GA group
        * GA metric is cube aggregate
        * GA dimension is cube dimension
        """

        # TODO: preliminary implementation

        try:
            metadata = self.cube_metadata(name)
        except NoSuchCubeError:
            metadata = {}

        group = self.cube_to_group[name]

        # Gather aggregates

        metrics = self.ga_group_metrics[group]

        aggregates = []
        for metric in metrics:
            aggregate = {
                "name": ga_id_to_identifier(metric["id"]),
                "label": metric["uiName"],
                "description": metric.get("description")
            }
            mtype = self._measurement_type_for(metric.get('dataType'))
            if mtype:
                aggregate['info'] = { 'measurement_type':  mtype }
            aggregates.append(aggregate)

        aggregates = aggregate_list(aggregates)

        dims = self.ga_group_dims[group]
        dims = [ga_id_to_identifier(d["id"]) for d in dims]
        dims = ["time"] + dims

        cube = Cube(name=name,
                    label=metadata.get("label", group),
                    aggregates=aggregates,
                    category=metadata.get("category", self.store.category),
                    info=metadata.get("info"),
                    dimension_links=dims,
                    datastore=self.store_name)

        return cube

    def dimension(self, name, templates=[], locale=None):
        try:
            metadata = self.dimension_metadata(name)
        except NoSuchDimensionError:
            metadata = {}

        if name == "time":
            return create_dimension(GA_TIME_DIM_METADATA)

        # TODO: this should be in the mapper
        ga_id = "ga:" + name

        try:
            ga_dim = self.ga_dimensions[ga_id]
        except KeyError:
            raise NoSuchDimensionError("No GA dimension %s" % name,
                                       name=name)

        dim = {
            "name": name,
            "label": metadata.get("label", ga_dim["uiName"]),
            "description": metadata.get("description", ga_dim["description"]),
            "category": metadata.get("category", ga_dim["group"])
        }

        return create_dimension(dim)

    def list_cubes(self):
        """List GA cubes – groups of metrics and dimensions."""
        # TODO: use an option how to look at GA – what are cubes?

        cubes = []
        for cube_name in self.ga_cubes:

            try:
                metadata = self.cube_metadata(cube_name)
            except NoSuchCubeError:
                metadata = {}

            label = self.cube_to_group[cube_name]
            cube = {
                "name": cube_name,
                "label": metadata.get("label", label),
                "category": metadata.get("category", self.store.category)
            }
            cubes.append(cube)

        return cubes


class GoogleAnalyticsStore(Store):
    __extension_name__ = "ga"
    related_model_provider = "ga"

    def __init__(self, email=None, key_file=None, account_id=None,
                 account_name=None, web_property=None,
                 category=None, view_id=None, **options):

        self.logger = get_logger()

        self.service = None
        self.credentials = None
        self.category = category

        if not email:
            raise ConfigurationError("Google Analytics: email is required")
        if not key_file:
            raise ConfigurationError("Google Analytics: key_file is required")

        if account_name and account_id:
            raise ConfigurationError("Both account_name and account_id "
                                     "provided. Use only one or none.")

        with open(key_file) as f:
            self.key = f.read()

        self.email = email

        self.account_id = account_id
        self.web_property_id = web_property
        self.web_property = None
        self.profile_id = view_id
        self.profile = None

        date = options.get("default_start_date")
        if date:
            self.default_start_date = date.split("-")
        else:
            self.default_start_date = None
        date = options.get("default_start_date")
        if date:
            self.default_end_date = date.split("-")
        else:
            self.default_end_date = None

        self.credentials = SignedJwtAssertionCredentials(self.email,
                              self.key,
                              scope="https://www.googleapis.com/auth/analytics.readonly")

        # TODO: make this lazy

        self._authorize()
        self._initialize_account(account_name, account_id)

    def _authorize(self):
        self.logger.debug("Authorizing GA")
        http = httplib2.Http()
        http = self.credentials.authorize(http)
        self.service = build('analytics', 'v3', http=http)

    def _initialize_account(self, account_name, account_id):

        accounts = self.service.management().accounts().list().execute()

        self.account = None
        if account_id:
            key = "id"
            value = account_id
        elif account_name:
            key = "name"
            value = account_name
        else:
            # If no ID or account name are provided, use the first account
            self.account = accounts["items"][0]

        if not self.account:
            for account in accounts['items']:
                if account[key] == value:
                    self.account = account
                    break

        if not self.account:
            raise ConfigurationError("Unknown GA account with %s='%s'" %
                                     (key, value))

        self.account_id = self.account["id"]

        # Get the web property ID and object
        # ---

        base = self.service.management().webproperties()
        props = base.list(accountId=self.account_id).execute()
        props = props["items"]
        self.web_property = None

        if self.web_property_id:
            for p in props:
                if p["id"] == self.web_property_id:
                    self.web_property = p
                    break
        else:
            self.web_property = props[0]
            self.web_property_id = props[0]["id"]

        if not self.web_property:
            raise ConfigurationError("Unknown GA property '%s'"
                                     % self.web_property_id)
        # Get the Profile/View ID and object
        # ---

        base = self.service.management().profiles()
        profiles = base.list(accountId=self.account_id,
                           webPropertyId=self.web_property_id).execute()

        profiles = profiles["items"]

        if self.profile_id:
            for p in profiles:
                if p["id"] == self.profile_id:
                    self.profile = p
                    break
        else:
            self.profile = profiles[0]
            self.profile_id = profiles[0]["id"]

        if not self.profile:
            raise ConfigurationError("Unknown GA profile/view '%s'"
                                     % self.profile_id)

        self.timezone = self.profile["timezone"]
        self.logger.debug("GA account:%s property:%s profile:%s"
                          % (self.account_id, self.web_property_id,
                             self.profile_id))

        if not self.category:
            self.category = "GA: %s / %s" % (self.web_property["name"],
                                           self.profile["name"])

    def get_data(self, **kwargs):
        # Documentation:
        # https://google-api-client-libraries.appspot.com/documentation/analytics/v3/python/latest/analytics_v3.data.ga.html
        ga = self.service.data().ga()

        try:
            response = ga.get(ids='ga:%s' % self.profile_id,
                              **kwargs).execute()
        except TypeError as e:
            raise ArgumentError("Google Analytics Error: %s"
                                % str(e))
        except HttpError as e:
            raise BrowserError("Google Analytics HTTP Error: %s"
                                % str(e))
        except AccessTokenRefreshError as e:
            raise NotImplementedError("Re-authorization not implemented yet")

        return response

########NEW FILE########
__FILENAME__ = aggregator
# -*- coding=utf -*-
from ...browser import *
from ...errors import *
from ...model import *

from .store import DEFAULT_TIME_HIERARCHY
from .utils import *

from collections import defaultdict
from datetime import datetime
import pytz

class _MixpanelResponseAggregator(object):
    def __init__(self, browser, responses, aggregate_names, drilldown, split,
                    actual_time_level):
        """Aggregator for multiple mixpanel responses (multiple dimensions)
        with drill-down post-aggregation.

        Arguments:

        * `browser` – owning browser
        * `reposnes` – mixpanel responses by `measure_names`
        * `aggregate_names` – list of collected measures
        * `drilldown` – a `Drilldown` object from the browser aggregation
          query
        * `split` - a split Cell object from the browser aggregation query

        Object attributes:

        * `aggregate_names` – list of measure names from the response
        * `aggregate_data` – a dictionary where keys are measure names and
          values are actual data points.

        * `time_cells` – an ordered dictionary of collected cells from the
          response. Key is time path, value is cell contents without the time
          dimension.
        """
        self.browser = browser
        self.logger = browser.logger
        self.drilldown = drilldown
        self.aggregate_names = aggregate_names
        self.actual_time_level = actual_time_level

        # Extract the data
        self.aggregate_data = {}
        for aggregate in aggregate_names:
            self.aggregate_data = responses[aggregate]["data"]["values"]

        # Get time drilldown levels, if we are drilling through time
        time_drilldowns = drilldown.drilldown_for_dimension("time")

        if time_drilldowns:
            time_drilldown = time_drilldowns[0]
            self.last_time_level = str(time_drilldown.levels[-1])
            self.time_levels = ["time."+str(l) for l in time_drilldown.levels]
            self.time_hierarchy = str(time_drilldown.hierarchy)
        else:
            time_drilldown = None
            self.last_time_level = None
            self.time_levels = []
            self.time_hierarchy = DEFAULT_TIME_HIERARCHY

        self.drilldown_on = None
        for obj in drilldown:
            if obj.dimension.name != "time":
                # this is a DrilldownItem object. represent it as 'dim.level' or just 'dim' if flat
                self.drilldown_on = ( "%s.%s" % (obj.dimension.name, obj.levels[-1].name) ) if ( not obj.dimension.is_flat ) else obj.dimension.name
                self.drilldown_on_value_func = lambda x: x

        if self.drilldown_on is None and split:
            self.drilldown_on = SPLIT_DIMENSION_NAME
            self.drilldown_on_value_func = lambda x: True if x == "true" else False

        # Time-keyed cells:
        #    (time_path, group) -> dictionary

        self.time_cells = {}
        self.cells = []

        # Do it:
        #
        # Collect, Map&Reduce, Order
        # ==========================
        #
        # Process the response. The methods are operating on the instance
        # variable `time_cells`

        self._collect_cells()
        # TODO: handle week
        if actual_time_level != self.last_time_level:
            self._reduce_cells()
        self._finalize_cells()

        # Result is stored in the `cells` instance variable.

    def _collect_cells(self):

        for aggregate in self.aggregate_names:
            self._collect_aggregate_cells(aggregate)

    def _collect_aggregate_cells(self, aggregate):
        """Collects the cells from the response in a time series dictionary
        `time_cells` where keys are tuples: `(time_path, group)`. `group` is
        drill-down key value for the cell, such as `New York` for `city`."""

        # Note: For no-drilldown this would be only one pass and group will be
        # a cube name

        # TODO: To add multiple drill-down dimensions in the future, add them
        # to the `group` part of the key tuple

        for group_key, group_series in self.aggregate_data.items():

            for time_key, value in group_series.items():
                time_path = time_to_path(time_key, self.last_time_level,
                                                        self.time_hierarchy)
                key = (time_path, group_key)

                # self.logger.debug("adding cell %s" % (key, ))
                cell = self.time_cells.setdefault(key, {})
                cell[aggregate] = value

                # FIXME: do this only on drilldown
                if self.drilldown_on:
                    cell[self.drilldown_on] = group_key

    def _reduce_cells(self):
        """Reduce the cells according to the time dimensions."""

        def reduce_cell(result, cell):
            # We assume only _sum aggergation
            # All measures should be prepared so we can to this
            for aggregate in self.aggregate_names:
                result[aggregate] = result.get(aggregate, 0) + \
                                   cell.get(aggregate, 0)
            return result

        # 1. Map cells to reduced time path
        #
        reduced_map = defaultdict(list)
        reduced_len = len(self.time_levels)

        for key, cell in self.time_cells.items():
            time_path = key[0]
            reduced_path = time_path[0:reduced_len]

            reduced_key = (reduced_path, key[1])

            # self.logger.debug("reducing %s -> %s" % (key, reduced_key))
            reduced_map[reduced_key].append(cell)

        self.browser.logger.debug("response cell count: %s reduced to: %s" %
                                    (len(self.time_cells), len(reduced_map)))

        # 2. Reduce the cells
        #
        # See the function reduce_cell() above for aggregation:
        #
        reduced_cells = {}
        for key, cells in reduced_map.items():
            # self.browser.logger.debug("Reducing: %s -> %s" % (key, cells))
            cell = reduce(reduce_cell, cells, {})

            reduced_cells[key] = cell

        self.time_cells = reduced_cells

    def _finalize_cells(self):
        """Orders the `time_cells` according to the time and "the other"
        dimension and puts the result into the `cells` instance variable.
        This method also adds the time dimension keys."""
        # Order by time (as path) and then drilldown dimension value (group)
        # The key[0] is a list of paths: time, another_drilldown

        order = lambda left, right: cmp(left[0], right[0])
        cells = self.time_cells.items()
        cells.sort(order)

        # compute the current datetime, convert to path
        current_time_path = time_to_path(
                pytz.timezone('UTC').localize(datetime.utcnow()).astimezone(self.browser.timezone).strftime("%Y-%m-%d %H:00:00"), 
                self.last_time_level, 
                self.time_hierarchy)

        self.cells = []
        for key, cell in cells:
            # If we are aggregating at finer granularity than "all":
            time_key = key[0]
            if time_key:
                # if time_key ahead of current time path, discard
                if time_key > current_time_path:
                    continue
                cell.update(zip(self.time_levels, time_key))

            # append the drilldown_on attribute ref
            if self.drilldown_on:
                cell[self.drilldown_on] = self.drilldown_on_value_func(key[1])

            self.cells.append(cell)


########NEW FILE########
__FILENAME__ = browser
# -*- coding=utf -*-
from ...browser import *
from ...errors import *
from ...model import *
from ...logging import get_logger
from ...statutils import *
from .aggregator import _MixpanelResponseAggregator
from .utils import *
from .mapper import MixpanelMapper

from ...statutils import calculators_for_aggregates, CALCULATED_AGGREGATIONS

from .store import DEFAULT_TIME_HIERARCHY

import datetime
import calendar
from collections import OrderedDict, defaultdict

_aggregate_param = {
        "total": "general",
        "unique": "unique",
        "average": "average"
    }

class MixpanelBrowser(AggregationBrowser):
    def __init__(self, cube, store, locale=None, **options):
        """Creates a Mixpanel aggregation browser.

        Requirements and limitations:

        * `time` dimension should always be present in the drilldown
        * only one other dimension is allowd for drilldown
        * range cuts assume numeric dimensions
        * unable to drill-down on `year` level, will default to `month`
        """
        self.store = store
        self.cube = cube
        self.options = options
        self.logger = get_logger()
        self.timezone = self.store.tz

        dim_names = [dim.name for dim in cube.dimensions]
        self.mapper = MixpanelMapper(cube, cube.mappings,
                                     property_dimensions=dim_names)

    def features(self):
        """Return SQL features. Currently they are all the same for every
        cube, however in the future they might depend on the SQL engine or
        other factors."""

        features = {
            "aggregate_functions": [],
            "post_aggregate_functions": available_calculators()
        }

        default_actions = ["aggregate", "facts", "cell"]
        cube_actions = self.cube.browser_options.get("actions")
        if cube_actions:
            cube_actions = set(default_actions) & set(cube_actions)
            features["actions"] = list(cube_actions)
        else:
            features["actions"] = default_actions

        return features

    def facts(self, cell, fields=None, page=None, page_size=None, order=None):

        cell = cell or Cell(self.cube)

        if not fields:
            attributes = self.cube.all_attributes
            self.logger.debug("facts: getting all fields: %s" % ([a.ref() for a in attributes], ))
        else:
            attributes = self.cube.get_attributes(fields)
            self.logger.debug("facts: getting fields: %s" % fields)

        # TODO: use mapper
        params = {"event":[self.cube.basename]}

        params.update(self.condition_for_cell(cell))
        response = self.store.request(["export"], params, is_data=True)

        result = MixpanelFacts(response, attributes, self.mapper)

        return result

    def provide_aggregate(self, cell, aggregates, drilldown, split, order,
                          page, page_size, **options):

        # All aggregates without a function can be considered as "native" as
        # they are handled specially.
        # If there is an explicit aggregate fucntion it is a post-aggregate
        # computation
        aggregate_names = [a.name for a in aggregates]
        native_aggregates = [a for a in aggregates if not a.function]
        native_aggregate_names = [a.name for a in native_aggregates]

        #
        # Prepare drilldown
        #

        time_drilldowns = drilldown.drilldown_for_dimension("time")
        if time_drilldowns and len(drilldown) > 2:
            raise ArgumentError("Can not drill down with more than one "
                                "non-time dimension in mixpanel")

        if split:
            if len(drilldown) > ( 1 if time_drilldowns else 0 ):
                raise BrowserError("split in mixpanel is not supported if a non-time drilldown is specified")

            if split.cut_for_dimension('time'):
                raise BrowserError("split in mixpanel is not supported for cuts containing time dimension")

        params = {}

        if time_drilldowns:
            time_level = time_drilldowns[0].levels[-1]
        else:
            time_level = None

        if time_level:
            time_level = str(time_level)

        # time_level - as requested by the caller
        # actual_time_level - time level in the result (dim.hierarchy
        #                     labeling)
        # mixpanel_unit - mixpanel request parameter

        if not time_level or time_level == "year":
            mixpanel_unit = actual_time_level = "month"
            # Get the default hierarchy
        elif time_level == "date":
            mixpanel_unit = "day"
            actual_time_level = "date"
        else:
            mixpanel_unit = actual_time_level = str(time_level)

        if time_level != actual_time_level:
            self.logger.debug("Time drilldown coalesced from %s to %s" % \
                                    (time_level, actual_time_level))

        if time_level and time_level not in self.cube.dimension("time").level_names:
            raise ArgumentError("Can not drill down time to '%s'" % time_level)

        # Get drill-down dimension (mixpanel "by" segmentation menu)
        # Assumption: first non-time

        drilldown_on = None
        for obj in drilldown:
            if obj.dimension.name != "time":
                drilldown_on = obj

        if drilldown_on:
            params["on"] = 'properties["%s"]' % \
                                    self._property(drilldown_on.dimension)
        elif split:
            params['on'] = self._condition_for_cell(split)


        #
        # The Conditions
        # ==============
        #
        # Create 'where' condition from cuts
        # Assumption: all dimensions are flat dimensions

        params.update(self.condition_for_cell(cell))

        if "limit" in options:
            params["limit"] = options["limit"]

        #
        # The request
        # ===========
        # Perform one request per measure aggregate.
        #
        # TODO: use mapper
        event_name = self.cube.basename

        # Collect responses for each measure aggregate
        #
        # Note: we are using `segmentation` MXP request by default except for
        # the `unique` measure at the `all` or `year` aggregation level.
        responses = {}

        for aggregate in native_aggregate_names:
            params["type"] = _aggregate_param[aggregate]

            if aggregate == "unique" and (not time_level or time_level == "year"):
                response = self._arb_funnels_request(event_name, params,
                                                     drilldown_on)
            else:
                response = self._segmentation_request(event_name, params,
                                                      mixpanel_unit)

            responses[aggregate] = response

        # TODO: get this: result.total_cell_count = None
        # TODO: compute summary

        #
        # The Result
        # ==========
        #

        result = AggregationResult(cell, aggregates)
        result.cell = cell

        aggregator = _MixpanelResponseAggregator(self, responses,
                                                 native_aggregate_names,
                                                 drilldown, split, actual_time_level)

        result.levels = drilldown.result_levels()
        if split:
            result.levels[SPLIT_DIMENSION_NAME] = SPLIT_DIMENSION_NAME

        labels = aggregator.time_levels[:]
        if drilldown_on:
            labels.append(drilldown_on.dimension.name)

        labels += aggregate_names
        result.labels = labels

        if drilldown or split:
            self.logger.debug("CALCULATED AGGS because drilldown or split")
            result.calculators = calculators_for_aggregates(self.cube,
                                                            aggregates,
                                                            drilldown,
                                                            split,
                                                            None)
            result.cells = aggregator.cells

        # add calculated measures w/o drilldown or split if no drilldown or split
        else:
            self.logger.debug("CALCULATED AGGS ON SUMMARY")
            result.summary = aggregator.cells[0]
            result.cells = []
            calculators = calculators_for_aggregates(self.cube,
                                                     aggregates,
                                                     drilldown,
                                                     split,
                                                     None)
            for calc in calculators:
                calc(result.summary)

        return result

    def is_builtin_function(self, function_name, aggregate):
        # Mixpanel has implicit functions for all aggregates. Therefore all
        # aggregates without a function name are considered built-in
        return aggregate.function is None

    def _segmentation_request(self, event_name, params, unit):
        """Perform Mixpanel request ``segmentation`` – this is the default
        request."""
        params = dict(params)
        params["event"] = event_name
        params["unit"] = unit

        response = self.store.request(["segmentation"], params)

        self.logger.debug(response['data'])
        return response

    def _arb_funnels_request(self, event_name, params, drilldown_on):
        """Perform Mixpanel request ``arb_funnels`` for measure `unique` with
        granularity of whole cube (all) or year."""
        params = dict(params)

        params["events"] = [{"event":event_name}]
        params["interval"] = 90
        params["type"] = _aggregate_param["unique"]

        response = self.store.request(["arb_funnels"], params)

        # TODO: remove this debug once satisfied (and below)
        # txt = dumps(response, indent=4)
        # self.logger.info("MXP response: \n%s" % (txt, ))

        # Convert the arb_funnels Mixpanel response to segmentation kind of
        # response.

        # Prepare the structure – only geys processed by the aggregator are
        # needed

        try:
            groups = response["meta"]["property_values"]
            is_drilldown = True
        except KeyError:
            groups = event_name
            is_drilldown = False

        result = { "data": {"values": {} } }

        for group in groups:
            values = result["data"]["values"].setdefault(group, {})

            point_key = group if is_drilldown else "steps"

            for date_key, data_point in response["data"].items():
                values[date_key] = data_point[point_key][0]["count"]

        # txt = dumps(result, indent=4)
        # self.logger.info("Converted response: \n%s" % (txt, ))

        return result

    def _property(self, dim):
        """Return correct property name from dimension."""
        dim = str(dim)
        return self.cube.mappings.get(dim, dim)

    def condition_for_cell(self, cell):
        #
        # Create from-to date range from time dimension cut
        #
        time_cut = cell.cut_for_dimension("time")
        time_hierarchy = time_cut.hierarchy if time_cut else DEFAULT_TIME_HIERARCHY

        if not time_cut:
            path_time_from = []
            path_time_to = []
        elif isinstance(time_cut, PointCut):
            path_time_from = time_cut.path or []
            path_time_to = time_cut.path or []
        elif isinstance(time_cut, RangeCut):
            path_time_from = time_cut.from_path or []
            path_time_to = time_cut.to_path or []
        else:
            raise ArgumentError("Mixpanel does not know how to handle cuts "
                                "of type %s" % type(time_cut))

        path_time_from = coalesce_date_path(path_time_from, 0, time_hierarchy)
        path_time_to = coalesce_date_path(path_time_to, 1, time_hierarchy)

        result = {
                "from_date": path_time_from.strftime("%Y-%m-%d"),
                "to_date": path_time_to.strftime("%Y-%m-%d")
            }

        #
        # Non-time condition
        #
        cuts = [cut for cut in cell.cuts if str(cut.dimension) != "time"]

        conditions = []
        for cut in cuts:
            if isinstance(cut, PointCut):
                condition = self._point_condition(cut.dimension, cut.path[0], cut.invert)
                conditions.append(condition)
            elif isinstance(cut, RangeCut):
                condition = self._range_condition(cut.dimension,
                                                  cut.from_path[0],
                                                  cut.to_path[0], cut.invert)
                conditions.append(condition)
            elif isinstance(cut, SetCut):
                set_conditions = []
                for path in cut.paths:
                    condition = self._point_condition(cut.dimension, path[0])
                    set_conditions.append(condition)
                condition = " or ".join(set_conditions)
                conditions.append(condition)

        if len(conditions) > 1:
            conditions = [ "(%s)" % cond for cond in conditions ]

        if conditions:
            result["where"] = " and ".join(conditions)

        return result

    def _point_condition(self, dim, value, invert):
        """Returns a point cut for flat dimension `dim`"""

        op = '!=' if invert else '=='
        condition = '(string(properties["%s"]) %s "%s")' % \
                        (self._property(dim), op, str(value))
        return condition

    def _range_condition(self, dim, from_value, to_value, invert):
        """Returns a point cut for flat dimension `dim`. Assumes number."""

        condition_tmpl = (
            '(number(properties["%s"]) >= %s and number(properties["%s"]) <= %s)' if not invert else
            '(number(properties["%s"]) < %s or number(properties["%s"]) > %s)'
            )

        condition = condition_tmpl % (self._property(dim), from_value, self._property(dim), to_value)
        return condition


class MixpanelFacts(Facts):
    def __init__(self, result, attributes, mapper):
        super(MixpanelFacts, self).__init__(result, attributes)

        self.mapper = mapper

    def __iter__(self):
        for i, record in enumerate(self.facts):
            record = record["properties"]

            fact = {"__id__": i}

            for attr in self.attributes:
                if attr.dimension.name != "time":
                    fact[attr.ref()] = record.get(self.mapper.physical(attr))

            # Populate time dimension attributes (only the requested ones)
            #
            time = timestamp_to_record(record["time"])
            for attr in self.attributes:
                if attr.dimension.name == "time":
                    fact[attr.ref()] = time.get(attr.ref())

            yield fact

########NEW FILE########
__FILENAME__ = mapper
# -*- coding=utf -*-

from ...mapper import Mapper
from ...errors import *

__all__ = (
    "MixpanelMapper",
)

def _mangle_dimension_name(name):
    """Return a dimension name from a mixpanel property name."""
    fixed_name = name.replace("$", "_")
    fixed_name = fixed_name.replace(" ", "_")

    return fixed_name

def cube_event_key(cube):
    """Returns key used for cube"""
    return "cube:%s" % cube

class MixpanelMapper(Mapper):
    def __init__(self, cube, locale=None, property_dimensions=None, **options):
        """Create a Mixpanel attribute mapper"""
        super(MixpanelMapper, self).__init__(cube, locale, **options)

        self.property_to_dimension = {}

        for dim_name in property_dimensions:
            try:
                prop = self.mappings[dim_name]
            except KeyError:
                pass
            else:
                self.property_to_dimension[prop] = dim_name

        self.event_name = self.mappings.get(cube_event_key(cube.name),
                                            cube.name)

    def physical(self, attr):
        phys = super(MixpanelMapper, self).physical(attr)
        if phys is None:
            return attr.ref()

    def logical_from_physical(self, physical):
        try:
            logical = self.property_to_dimension[physical]
        except KeyError:
            logical = _mangle_dimension_name(physical)

        return logical


########NEW FILE########
__FILENAME__ = mixpanel
#! /usr/bin/env python
#
# Mixpanel, Inc. -- http://mixpanel.com/
#
# Python API client library to consume mixpanel.com analytics data.

import hashlib
import urllib
import time
try:
    import json
except ImportError:
    import simplejson as json

class MixpanelError(Exception):
    pass

class Mixpanel(object):

    ENDPOINT = 'http://mixpanel.com/api'
    DATA_ENDPOINT = 'http://data.mixpanel.com/api'
    VERSION = '2.0'

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

    def request(self, methods, params, format='json', is_data=False):
        """
            methods - List of methods to be joined, e.g. ['events', 'properties', 'values']
                      will give us http://mixpanel.com/api/2.0/events/properties/values/
            params - Extra parameters associated with method
        """
        params['api_key'] = self.api_key
        params['expire'] = int(time.time()) + 600   # Grant this request 10 minutes.
        params['format'] = format
        if 'sig' in params: del params['sig']
        params['sig'] = self.hash_args(params)

        endpoint = self.DATA_ENDPOINT if is_data else self.ENDPOINT
        request_url = '/'.join([endpoint, str(self.VERSION)] + methods) + '/?' + self.unicode_urlencode(params)

        response = urllib.urlopen(request_url)

        # Standard response or error response is a JSON. Data response is one
        # JSON per line
        if not is_data or response.getcode() != 200:
            result = json.loads(response.read())
            if "error" in result:
                raise MixpanelError(result["error"])
            else:
                return result
        else:
            return _MixpanelDataIterator(response)

    def unicode_urlencode(self, params):
        """
            Convert lists to JSON encoded strings, and correctly handle any
            unicode URL parameters.
        """
        if isinstance(params, dict):
            params = params.items()
        for i, param in enumerate(params):
            if isinstance(param[1], list):
                params[i] = (param[0], json.dumps(param[1]),)

        return urllib.urlencode(
            [(k, isinstance(v, unicode) and v.encode('utf-8') or v) for k, v in params]
        )

    def hash_args(self, args, secret=None):
        """
            Hashes arguments by joining key=value pairs, appending a secret, and
            then taking the MD5 hex digest.
        """
        for a in args:
            if isinstance(args[a], list): args[a] = json.dumps(args[a])

        args_joined = ''
        for a in sorted(args.keys()):
            if isinstance(a, unicode):
                args_joined += a.encode('utf-8')
            else:
                args_joined += str(a)

            args_joined += '='

            if isinstance(args[a], unicode):
                args_joined += args[a].encode('utf-8')
            else:
                args_joined += str(args[a])

        hash = hashlib.md5(args_joined)

        if secret:
            hash.update(secret)
        elif self.api_secret:
            hash.update(self.api_secret)
        return hash.hexdigest()

class _MixpanelDataIterator(object):
    def __init__(self, data):
        self.line_iterator = iter(data)

    def __iter__(self):
        return self

    def next(self):
        # From Mixpanel Documentation:
        #
        # One event per line, sorted by increasing timestamp. Each line is a
        # JSON dict, but the file itself is not valid JSON because there is no
        # enclosing object. Timestamps are in project time but expressed as
        # Unix time codes (but from_date and to_date are still interpreted in
        # project time).
        #
        # Source: https://mixpanel.com/docs/api-documentation/exporting-raw-data-you-inserted-into-mixpanel
        #
        line = next(self.line_iterator)
        return json.loads(line)

if __name__ == '__main__':
    api = Mixpanel(
        api_key = 'YOUR KEY',
        api_secret = 'YOUR SECRET'
    )
    data = api.request(['events'], {
        'event' : ['pages',],
        'unit' : 'hour',
        'interval' : 24,
        'type': 'general'
    })
    print data

########NEW FILE########
__FILENAME__ = store
# -*- coding=utf -*-
from ...model import Cube, create_dimension
from ...model import aggregate_list
from ...browser import *
from ...stores import Store
from ...errors import *
from ...providers import ModelProvider
from ...logging import get_logger
from .mixpanel import *
from .mapper import cube_event_key
from string import capwords
import pkgutil
import time, pytz

DIMENSION_COUNT_LIMIT = 100

DEFAULT_TIME_HIERARCHY = "ymdh"

MXP_TIME_DIM_METADATA = {
    "name": "time",
    "role": "time",
    "levels": [
        { "name": "year", "label": "Year" },
        { "name": "month", "label": "Month", "info": { "aggregation_units": 3 }},
        { "name": "day", "label": "Day", "info": { "aggregation_units": 7 } },
        { "name": "hour", "label": "Hour", "info": { "aggregation_units": 6 } },
        { "name": "week", "label": "Week", "info": { "aggregation_units": 4 } },
        { "name": "date", "label": "Date", "info": { "aggregation_units": 7 } }
    ],
    "hierarchies": [
        {"name": "ymdh", "levels": ["year", "month", "day", "hour"]},
        {"name": "wdh", "levels": ["week", "date", "hour"]}
    ],
    "default_hierarchy_name": "ymdh",
    "info": {"is_date": True}
}

MXP_AGGREGATES_METADATA = [
    {
        "name": "total",
        "label": "Total"
    },
    {
        "name": "total_sma",
        "label": "Total Moving Average",
        "function": "sma",
        "measure": "total"
    },
    {
        "name": "unique",
        "label": "Unique"
    },
    {
        "name": "unique_sma",
        "label": "Unique Moving Average",
        "function": "sma",
        "measure": "unique"
    },
]


_time_dimension = create_dimension(MXP_TIME_DIM_METADATA)

def _mangle_dimension_name(name):
    """Return a dimension name from a mixpanel property name."""
    fixed_name = name.replace("$", "_")
    fixed_name = fixed_name.replace(" ", "_")

    return fixed_name

class MixpanelModelProvider(ModelProvider):
    def __init__(self, *args, **kwargs):
        super(MixpanelModelProvider, self).__init__(*args, **kwargs)

        # TODO: replace this with mixpanel mapper
        # Map properties to dimension (reverse mapping)
        self.property_to_dimension = {}
        self.event_to_cube = {}
        self.cube_to_event = {}

        mappings = self.metadata.get("mappings", {})

        # Move this into the Mixpanel Mapper
        for name in self.dimensions_metadata.keys():
            try:
                prop = mappings[name]
            except KeyError:
                pass
            else:
                self.property_to_dimension[prop] = name

        for name in self.cubes_metadata.keys():
            try:
                event = mappings[cube_event_key(name)]
            except KeyError:
                pass
            else:
                self.cube_to_event[name] = event
                self.event_to_cube[event] = name

    def default_metadata(self, metadata=None):
        """Return Mixpanel's default metadata."""

        model = pkgutil.get_data("cubes.backends.mixpanel", "mixpanel_model.json")
        metadata = json.loads(model)

        return metadata

    def requires_store(self):
        return True

    def public_dimensions(self):
        """Return an empty list. Mixpanel does not export any dimensions."""
        return []

    def cube(self, name, locale=None):
        """Creates a mixpanel cube with following variables:

        * `name` – cube name
        * `measures` – cube measures: `total` and `uniques`
        * `dimension_links` – list of linked dimension names
        * `mappings` – mapping of corrected dimension names

        Dimensions are Mixpanel's properties where ``$`` character is replaced
        by the underscore ``_`` character.
        """

        params = {
            "event": self.cube_to_event.get(name, name),
            "limit": DIMENSION_COUNT_LIMIT
        }

        result = self.store.request(["events", "properties", "top"], params)
        if not result:
            raise NoSuchCubeError("Unknown Mixpanel cube %s" % name, name)

        try:
            metadata = self.cube_metadata(name)
        except NoSuchCubeError:
            metadata = {}

        options = self.cube_options(name)
        allowed_dims = options.get("allowed_dimensions", [])
        denied_dims = options.get("denied_dimensions", [])

        dims = ["time"]
        mappings = {}

        for prop in result.keys():
            try:
                dim_name = self.property_to_dimension[prop]
            except KeyError:
                dim_name = _mangle_dimension_name(prop)

            # Skip not allowed dimensions
            if (allowed_dims and dim_name not in allowed_dims) or \
                    (denied_dims and dim_name in denied_dims):
                continue

            if dim_name != prop:
                mappings[dim_name] = prop

            dims.append(dim_name)

        aggregates = aggregate_list(MXP_AGGREGATES_METADATA)

        label = metadata.get("label", capwords(name.replace("_", " ")))
        category = metadata.get("category", self.store.category)

        cube = Cube(name=name,
                    aggregates=aggregates,
                    label=label,
                    description=category,
                    info=metadata.get("info"),
                    dimension_links=dims,
                    datastore=self.store_name,
                    mappings=mappings,
                    category=category)

        cube.info["required_drilldowns"] = ["time"]

        return cube

    def dimension(self, name, locale=None, templates=[]):
        if name == "time":
            return _time_dimension

        try:
            metadata = self.dimension_metadata(name)
        except NoSuchDimensionError:
            metadata = {"name": name}

        return create_dimension(metadata)

    def list_cubes(self):
        result = self.store.request(["events", "names"], {"type": "general", })
        cubes = []

        for event in result:
            name = self.event_to_cube.get(event, event)
            try:
                metadata = self.cube_metadata(name)
            except NoSuchCubeError:
                metadata = {}

            label = metadata.get("label", capwords(name.replace("_", " ")))
            category = metadata.get("category", self.store.category)

            cube = {
                "name": name,
                "label": label,
                "category": category
            }
            cubes.append(cube)

        return cubes


class MixpanelStore(Store):
    related_model_provider = "mixpanel"

    def __init__(self, api_key, api_secret, category=None, tz=None):
        self.mixpanel = Mixpanel(api_key, api_secret)
        self.category = category or "Mixpanel Events"
        if tz is not None:
            tz = pytz.timezone(tz)
        else:
            tz = pytz.timezone(time.strftime('%Z', time.localtime()))
        self.tz = tz
        self.logger = get_logger()

    def request(self, *args, **kwargs):
        """Performs a mixpanel HTTP request. Raises a BackendError when
        mixpanel returns `error` in the response."""

        self.logger.debug("Mixpanel request: %s" % (args,))

        try:
            response = self.mixpanel.request(*args, **kwargs)
        except MixpanelError as e:
            raise BackendError("Mixpanel request error: %s" % str(e))

        return response

########NEW FILE########
__FILENAME__ = utils
# -*- coding=utf -*-

import datetime
import calendar

__all__ = [
    "coalesce_date_path",
    "time_to_path",
    "timestamp_to_record"
]

def _week_value(dt, as_string=False):
    """
    Mixpanel weeks start on Monday. Given a datetime object or a date string of format YYYY-MM-DD,
    returns a YYYY-MM-DD string for the Monday of that week.
    """
    dt = datetime.datetime.strptime(dt, '%Y-%m-%d') if isinstance(dt, basestring) else dt
    dt = ( dt - datetime.timedelta(days=dt.weekday()) )
    return ( dt.strftime("%Y-%m-%d") if as_string else dt )

_week_path_readers = ( lambda v: datetime.datetime.strptime(v, '%Y-%m-%d'), lambda v: datetime.datetime.strptime(v, '%Y-%m-%d'), int )

_lower_date = datetime.datetime(2008, 1, 1)

def coalesce_date_path(path, bound, hier='ymdh'):
    if str(hier) == 'wdh':
        return _coalesce_date_wdh(path, bound)
    else:
        return _coalesce_date_ymdh(path, bound)

def _coalesce_date_wdh(path, bound):
    path = [ _week_path_readers[i](path[i]) for i, v in enumerate(list(path or [])) ]
    effective_dt = path[1] if len(path) > 1 else ( path[0] if len(path) else ( _lower_date if bound == 0 else datetime.datetime.today() ) )

    if bound == 0:
        # at week level, first monday
        if len(path) < 1:
            return _week_value(effective_dt)
        else:
            return effective_dt.replace(hour=0)
    else:
        # end of this week, sunday
        result = ( _week_value(effective_dt) + datetime.timedelta(days=6) ) if len(path) < 2 else effective_dt
        return min(result, datetime.datetime.today())


def _coalesce_date_ymdh(path, bound):
    # Bound: 0: lower, 1:upper

    # Convert path elements
    path = [ int(v) for v in list(path or []) ]

    length = len(path)

    # Lower bound:
    if bound == 0:
        lower = [_lower_date.year, _lower_date.month, _lower_date.day]
        result = path + lower[len(path):]
        return datetime.datetime(**(dict(zip(['year', 'month', 'day'], result))))

    # Upper bound requires special handling
    today = datetime.datetime.today()

    delta = datetime.timedelta(1)
    # Make path of length 4
    (year, month, day, hour) = tuple(path + [None]*(4-len(path)))

    # hours are ignored - Mixpanel does not allow to use hours for cuts

    if not year:
        return today

    elif year and month and day:
        date = datetime.date(year, month, day)

    elif year < today.year:
        date = datetime.date(year+1, 1, 1) - delta

    elif year == today.year and month and month < today.month:
        day = calendar.monthrange(year, month)[1]
        date = datetime.date(year, month, day)

    elif year == today.year and month == today.month and not day:
        date = datetime.date(year, month, today.day)

    elif year > today.year:
        month = month or 1
        day = calendar.monthrange(year, month)[1]
        date = datetime.date(year, month, day)

    else:
        date = today

    return date

def timestamp_to_record(timestamp):
    """Returns a path from `timestamp` in the ``ymdh`` hierarchy."""
    time = datetime.datetime.fromtimestamp(timestamp)
    record = {
        "time.year": time.year,
        "time.month": time.month,
        "time.day": time.day,
        "time.hour": time.hour
    }
    return record

def time_to_path(time_string, last_level, hier='ymdh'):
    """Converts `time_string` into a time path. `time_string` can have format:
        ``yyyy-mm-dd`` or ``yyyy-mm-dd hh:mm:ss``. Only hour is considered
        from the time."""

    split = time_string.split(" ")
    if len(split) > 1:
        date, time = split
    else:
        date = split[0]
        time = None

    if hier == 'wdh':
        if last_level == 'week':
            time_path = [ _week_value(date, True) ]
        else:
            time_path = [ _week_value(date, True), date ]
    else:
        time_path = [int(v) for v in date.split("-")]
    # Only hour is assumed
    if time:
        hour = time.split(":")[0]
        time_path.append(int(hour))

    return tuple(time_path)

########NEW FILE########
__FILENAME__ = browser
from ...logging import get_logger
from ...errors import *
from ...browser import *
from ...computation import *
from ...statutils import calculators_for_aggregates, available_calculators
from cubes import statutils
from .mapper import MongoCollectionMapper
from .datesupport import MongoDateSupport
from .functions import get_aggregate_function, available_aggregate_functions
from .util import to_json_safe, collapse_record

import collections
import copy
import pymongo
import bson
import re

from dateutil.relativedelta import relativedelta
from datetime import datetime
from itertools import groupby
from functools import partial
import pytz


tz_utc = pytz.timezone('UTC')


SO_FAR_DIMENSION_REGEX = re.compile(r"^.+_sf$", re.IGNORECASE)


def is_date_dimension(dim):
    if hasattr(dim, 'role') and (dim.role == 'time'):
        return True
    if hasattr(dim, 'info') and (dim.info.get('is_date')):
        return True
    return False


class MongoBrowser(AggregationBrowser):
    def __init__(self, cube, store, locale=None, calendar=None,
                 **options):

        super(MongoBrowser, self).__init__(cube, store)

        self.logger = get_logger()

        database = store.database
        if cube.browser_options.get('database'):
            database = cube.browser_options.get('database')

        collection = store.collection
        if cube.browser_options.get('collection'):
            collection = cube.browser_options.get('collection')

        self.data_store = store.client[database][collection]

        self.mapper = MongoCollectionMapper(cube, database, collection, locale)

        self.timezone = pytz.timezone(cube.browser_options.get('timezone') or options.get('timezone') or 'UTC')

        self.datesupport = MongoDateSupport(self.logger, calendar)

        if "__query__" in self.cube.mappings:
            self.logger.warn("mongo: __query__ in mappings is depreciated, "
                             "use browser_options.filter instead")

        self.query_filter = options.get("filter", None)

    def features(self):
        """Return SQL features."""

        features = {
            "facts": ["fields", "missing_values"],
            "aggregate_functions": available_aggregate_functions(),
            "post_aggregate_functions": available_calculators()
        }

        cube_actions = self.cube.browser_options.get("actions")

        default_actions = ["aggregate", "members", "fact", "facts", "cell"]
        cube_actions = self.cube.browser_options.get("actions")

        if cube_actions:
            cube_actions = set(default_actions) & set(cube_actions)
            features["actions"] = list(cube_actions)
        else:
            features["actions"] = default_actions

        return features

    def set_locale(self, locale):
        self.mapper.set_locale(locale)

    def provide_aggregate(self, cell, aggregates, drilldown, split, order,
                          page, page_size, **options):

        result = AggregationResult(cell=cell, aggregates=aggregates)

        drilldown_levels = None

        labels = []

        # Prepare the drilldown
        # FIXME: this is the exact code as in SQL browser - put it into a
        # separate method and share

        if drilldown or split:
            if not (page_size and page is not None):
                self.assert_low_cardinality(cell, drilldown)

            result.levels = drilldown.result_levels(include_split=bool(split))

            #
            # Find post-aggregation calculations and decorate the result
            #
            result.calculators = calculators_for_aggregates(self.cube,
                                                            aggregates,
                                                            drilldown,
                                                            split,
                                                            available_aggregate_functions())

        summary, items = self._do_aggregation_query(cell=cell,
                                                    aggregates=aggregates,
                                                    attributes=None,
                                                    drilldown=drilldown,
                                                    split=split, order=order,
                                                    page=page,
                                                    page_size=page_size)
        result.cells = iter(items)
        result.summary = summary or {}
        # add calculated measures w/o drilldown or split if no drilldown or split
        if not (drilldown or split):
            calculators = calculators_for_aggregates(self.cube,
                                                     aggregates,
                                                     drilldown,
                                                     split,
                                                     available_aggregate_functions())
            for calc in calculators:
                calc(result.summary)

        labels += [ str(m) for m in aggregates ]
        result.labels = labels
        return result

    def is_builtin_function(self, function_name, aggregate):
        return function_name in available_aggregate_functions()

    def facts(self, cell=None, fields=None, order=None, page=None, page_size=None,
              **options):
        """Return facts iterator."""

        cell = cell or Cell(self.cube)

        if not fields:
            attributes = self.cube.all_attributes
            self.logger.debug("facts: getting all fields")
        else:
            attributes = self.cube.get_attributes(fields)
            self.logger.debug("facts: getting fields: %s" % fields)

        # Prepare the query
        query_obj, fields_obj = self._build_query_and_fields(cell, [], for_project=False)

        # TODO include fields_obj, fully populated
        cursor = self.data_store.find(query_obj)

        order = self.prepare_order(order)
        if order:
            order_obj = self._order_to_sort_object(order)
            k, v = order_obj.iteritems().next()
            cursor = cursor.sort(k, pymongo.DESCENDING if v == -1 else pymongo.ASCENDING)

        if page_size and page > 0:
            cursor = cursor.skip(page * page_size)

        if page_size and page_size > 0:
            cursor = cursor.limit(page_size)

        facts = MongoFactsIterator(cursor, attributes, self.mapper,
                                   self.datesupport)

        return facts

    def fact(self, key):
        # TODO make it possible to have a fact key that is not an ObjectId
        key_field = self.mapper.physical(self.mapper.attribute(self.cube.key))
        key_value = key
        try:
            key_value = bson.objectid.ObjectId(key)
        except:
            pass
        item = self.data_store.find_one({key_field.field: key_value})
        if item is not None:
            item = to_json_safe(item)
        return item

    def provide_members(self, cell, dimension, depth=None, hierarchy=None,
                        levels=None, attributes=None, page=None,
                        page_size=None, order=None):
        """Provide dimension members. The arguments are already prepared by
        superclass `members()` method."""

        attributes = []
        for level in levels:
           attributes += level.attributes

        drilldown = Drilldown([(dimension, hierarchy, levels[-1])], cell)

        summary, cursor = self._do_aggregation_query(cell=cell,
                                                     aggregates=None,
                                                     attributes=attributes,
                                                     drilldown=drilldown,
                                                     split=None,
                                                     order=order,
                                                     page=page,
                                                     page_size=page_size)

        # TODO: return iterator
        data = []

        for item in cursor:
            new_item = {}
            for level in levels:
                for level_attr in level.attributes:
                    k = level_attr.ref()
                    if item.has_key(k):
                        new_item[k] = item[k]
            data.append(new_item)

        return data

    def _in_same_collection(self, physical_ref):
        return (physical_ref.database == self.mapper.database) and (physical_ref.collection == self.mapper.collection)

    def _build_query_and_fields(self, cell, attributes, for_project=False):
        """Returns a tuple (`query`, `fields`). If `for_project` is `True`,
        then the values are transformed using `project`, otherwise they are
        transformed usin the `match` expression."""

        find_clauses = []
        query = {}

        if not for_project:
            # TODO: __query__ is for backward compatibility, might be removed
            # later

            query_base = self.cube.mappings.get("__query__", self.query_filter)
            if query_base:
                query_base = copy.deepcopy(query_base)
                query.update(query_base)

        find_clauses = []
        for cut in cell.cuts:
            find_clauses += self._query_conditions_for_cut(cut, for_project)

        if find_clauses:
            query.update({"$and": find_clauses})

        fields = {}

        for attribute in attributes or []:
            phys = self.mapper.physical(attribute)
            if not self._in_same_collection(phys):
                raise ValueError("Cannot fetch field that is in different "
                                 "collection than this browser: %r" % phys)
            if for_project:
                expr = phys.project_expression()
            else:
                expr = phys.match_expression(True)

            fields[escape_level(attribute.ref())] = expr

        return query, fields

    def _do_aggregation_query(self, cell, aggregates, attributes, drilldown,
                              split, order, page, page_size):

        # determine query for cell cut
        query_obj, fields_obj = self._build_query_and_fields(cell, attributes)

        # If no drilldown or split, only one measure, and only aggregations to
        # do on it are count or identity, no aggregation pipeline needed.
        if (not drilldown and not split) \
                and len(aggregates) == 1 \
                and aggregates[0].function in ("count", "identity"):

            self.logger.debug("doing plain aggregation")
            return (self.data_store.find(query_obj).count(), [])

        # TODO: do we need this check here?
        # if not aggregates:
        #     raise ArgumentError("No aggregates provided.")


        group_id = {}

        # prepare split-related projection of complex boolean condition
        if split:
            split_query_like_obj, dummy = self._build_query_and_fields(split,
                                                                       [],
                                                                       for_project=True)
            if split_query_like_obj:
                fields_obj[escape_level(SPLIT_DIMENSION_NAME)] = split_query_like_obj
                group_id[escape_level(SPLIT_DIMENSION_NAME)] = "$%s" % escape_level(SPLIT_DIMENSION_NAME)

        # drilldown, fire up the pipeline

        timezone_shift_processing = False
        date_transform = lambda x:x

        sort_obj = bson.son.SON()

        if drilldown:
            for dditem in drilldown:
                dim, hier, levels = dditem.dimension, dditem.hierarchy, dditem.levels

                # Special Mongo Date Hack for TZ Support
                if dim and is_date_dimension(dim):
                    is_utc = (self.timezone == tz_utc)
                    phys = self.mapper.physical(levels[0].key)
                    date_idx = phys.project_expression()

                    # add to $match and $project expressions
                    query_obj.update(phys.match_expression(1, op='$exists'))
                    fields_obj[date_idx[1:]] = 1

                    if is_utc and not ([l for l in levels if l.name == 'week']):
                        possible_groups = {
                            'year': {'$year': date_idx},
                            'month': {'$month': date_idx},
                            'day': {'$dayOfMonth': date_idx},
                            'hour': {'$hour': date_idx},
                            'minute': {'$minute': date_idx}
                        }
                        for lvl in levels:
                            group_id[escape_level(lvl.key.ref())] = possible_groups[lvl.name]
                            sort_obj["_id." + escape_level(lvl.key.ref())] = 1

                    else:
                        timezone_shift_processing = True
                        group_id.update({
                            'year': {'$year': date_idx},
                            'month': {'$month': date_idx},
                            'day': {'$dayOfMonth': date_idx},
                            'hour': {'$hour': date_idx}
                        })
                        if levels[-1] == 'minute':
                            group_id['minute'] = { '$minute': date_idx }

                        def _date_transform(item, date_field):
                            date_dict = {}
                            for k in ['year', 'month', 'day', 'hour', 'minute']:
                                if item['_id'].has_key(k):
                                    date_dict[k] = item['_id'].pop(k)

                            date = datetime(**date_dict)
                            date = tz_utc.localize(date)
                            date = date.astimezone(tz=self.timezone) # convert to browser timezone

                            item['_id'][date_field] = date
                            return item

                        date_transform = partial(_date_transform, date_field=dim.name)

                else:
                    for level in levels:
                        key_phys = self.mapper.physical(level.key)
                        sort_obj["_id." + escape_level(level.key.ref())] = 1
                        query_obj.update(key_phys.match_expression(1, op='$exists'))
                        # this loop will include key
                        for attr in level.attributes:
                            fields_obj[escape_level(attr.ref())] = self.mapper.physical(attr).project_expression()
                            group_id[escape_level(attr.ref())] = "$%s" % escape_level(attr.ref())

        group_obj = { "_id": group_id }

        aggregate_fn_pairs = []

        for agg in aggregates or []:
            if agg.function:
                try:
                    function = get_aggregate_function(agg.function)
                except KeyError:
                    continue
            else:
                function = None

            phys = self.mapper.physical(agg)
            fields_obj[escape_level(agg.ref())] = phys.project_expression()

            if not self._in_same_collection(phys):
                raise BrowserError("Measure cannot be in different database "
                                   "or collection than browser: %r" % phys)

            aggregate_fn_pairs.append( ( escape_level(agg.ref()), sum ) )


            if phys.group:
                group = phys.group
            elif function:
                group_applicator = function["group_by"]
                group = group_applicator(escape_level(agg.ref()))
            else:
                raise ModelError("Neither function or mapping group specified "
                                 "for aggregate '%s' in cube '%s'"
                                 % (str(agg), str(self.cube)))

            group_obj[ escape_level(agg.ref()) ] = group

        pipeline = self.cube.mappings.get("__pipeline__")

        if pipeline:
            # Get a copy of pipeline
            pipeline = list(pipeline)
        else:
            pipeline = []

        pipeline.append({ "$match": query_obj })
        if fields_obj:
            pipeline.append({ "$project": fields_obj })
        pipeline.append({ "$group": group_obj })

        if not timezone_shift_processing:
            if order:
                obj = {
                    "$sort": self._order_to_sort_object(order)
                }
                pipeline.append(obj)
            elif len(sort_obj):
                pipeline.append({ "$sort": sort_obj })

        if not timezone_shift_processing and page and page > 0:
            pipeline.append({ "$skip": page * page_size })

        if not timezone_shift_processing and page_size and page_size > 0:
            pipeline.append({ "$limit": page_size })

        result_items = []
        self.logger.debug("PIPELINE: %s", pipeline)

        results = self.data_store.aggregate(pipeline).get('result', [])
        results = [date_transform(r) for r in results]

        if timezone_shift_processing:
            dategrouping = ['year', 'month', 'week', 'day', 'hour', 'minute']
            datenormalize = ['year', 'month', 'week', 'dow', 'day', 'hour', 'minute']

            date_field = None
            filter_so_far = False
            # calculate correct date:level
            for dditem in drilldown:
                if dditem.dimension and is_date_dimension(dditem.dimension):
                    date_field = dditem.dimension.name
                    dategrouping = [str(l).lower() for l in dditem.levels]
                    for dg in dategrouping:
                        datenormalize.remove(dg)

                    # TODO don't use magic _sf string for sofar
                    if SO_FAR_DIMENSION_REGEX.match(dditem.dimension.name):
                        filter_so_far = True
                    break

            def _date_key(item, dategrouping=['year', 'month', 'week', 'day', 'hour', 'minute']):
                # sort group on date
                dt = item['_id'][date_field]
                key = [self.datesupport.datepart_functions.get(dp)(dt) for dp in dategrouping]

                # add remainder elements to sort and group
                for k, v in sorted(item['_id'].items(), key=lambda x:x[0]):
                    if k != date_field:
                        key.append(v)
                return key

            if dategrouping[-1] == 'week' and 'year' in dategrouping:
                dategrouping.remove('year') # year included in week calc because week year might change


            if filter_so_far:
                filt = self.datesupport.so_far_filter(datetime.utcnow(), dategrouping[-1], key=lambda x:x['_id'][date_field])
                results = filter(filt, results)


            # sort and group [date_parts,...,non-date parts]
            results = sorted(results, key=partial(_date_key, dategrouping=[ ("dow_sort" if x == "dow" else x) for x in dategrouping ]))
            groups = groupby(results, key=partial(_date_key, dategrouping=dategrouping))

            def _date_norm(item, datenormalize, dategrouping):
                dt = item['_id'].pop(date_field)

                if dategrouping[-1] == 'week':
                    dt= self.datesupport.get_week_end_date(dt)

                for dp in dategrouping:
                    item['_id']['%s.%s' % (date_field, dp)] = self.datesupport.datepart_functions.get(dp)(dt)

                return item

            formatted_results = []
            for g in groups:
                item = {}
                items = [i for i in g[1]]

                item.update(items[0])

                for agg_fn_pair in aggregate_fn_pairs:
                    item[ agg_fn_pair[0] ] = agg_fn_pair[1]([d[ agg_fn_pair[0] ] for d in items])

                item = _date_norm(item, datenormalize, dategrouping)
                formatted_results.append(item)

            if order:
                formatted_results = complex_sorted(formatted_results, order)

            if page and page_size:
                idx = page*page_size
                formatted_results = formatted_results[idx:idx + page_size]

            results = formatted_results

        for item in results:
            new_item = {}
            for k, v in item['_id'].items():
                new_item[unescape_level(k)] = v
            for agg_fn_pair in aggregate_fn_pairs:
                new_item[ unescape_level(agg_fn_pair[0]) ] = item [ agg_fn_pair[0] ]
            result_items.append(new_item)

        return (None, result_items) if (drilldown or split) else (result_items[0], [])

    def _build_date_for_cut(self, hier, path, is_end=False):
        """Constructs a date from timestamp."""
        date_dict = {'month': 1, 'day': 1, 'hour': 0, 'minute': 0 }
        min_part = None

        date_levels = hier.levels[:len(path)]
        for val, date_part in zip(path, date_levels):
            physical = self.mapper.physical(date_part.key)
            date_dict[date_part.key.name] = physical.convert_value(val)
            min_part = date_part.key.name

        dt = None
        if 'year' in date_dict:
            dt = datetime(**date_dict)
            if is_end:
                dt += relativedelta(**{(min_part + 's'): 1})
        else:
            if 'week' not in date_dict:
                return None
            else:
                dt = datetime.strptime(date_dict['week'], '%Y-%m-%d')
                if is_end:
                    dt = self.datesupport.get_week_end_date(dt) + relativedelta(days=1)
                else:
                    dt = self.datesupport.get_week_start_date(dt)

        return self.timezone.localize(dt).astimezone(tz_utc)

    def _query_conditions_for_cut(self, cut, for_project=False):
        conds = []
        cut_dimension = self.cube.dimension(cut.dimension)
        cut_hierarchy = cut_dimension.hierarchy(cut.hierarchy)

        if isinstance(cut, PointCut):
            if is_date_dimension(cut.dimension):
                start = self._build_date_for_cut(cut_hierarchy, cut.path)
                if start is None:
                    return conds

                end = self._build_date_for_cut(cut_hierarchy, cut.path, is_end=True)

                if not cut.invert:
                    start_op = '$gte'
                    end_op = '$lt'
                else:
                    start_op = '$lt'
                    end_op = '$gt'

                key = cut_hierarchy.levels[0].key

                start_cond = self._query_condition_for_path_value(key, start, start_op, for_project)
                end_cond =self._query_condition_for_path_value(key, end, end_op, for_project)

                if not cut.invert:
                    conds.append(start_cond)
                    conds.append(end_cond)
                else:
                    conds.append({'$or':[start_cond, end_cond]})

            else:
                # one condition per path element
                for idx, p in enumerate(cut.path):
                    conds.append( self._query_condition_for_path_value(cut_hierarchy.levels[idx].key, p, "$ne" if cut.invert else '$eq', for_project) )

        elif isinstance(cut, SetCut):
            for path in cut.paths:
                path_conds = []
                for idx, p in enumerate(path):
                    path_conds.append( self._query_condition_for_path_value(cut_hierarchy.levels[idx].key, p, "$ne" if cut.invert else '$eq', for_project) )
                conds.append({ "$and" : path_conds })
            conds = [{ "$or" : conds }]
        # FIXME for multi-level range: it's { $or: [ level_above_me < value_above_me, $and: [level_above_me = value_above_me, my_level < my_value] }
        # of the level value.
        elif isinstance(cut, RangeCut):
            if is_date_dimension(cut.dimension):
                start_cond = None
                end_cond = None
                if cut.from_path:
                    start = self._build_date_for_cut(cut_hierarchy, cut.from_path)
                    if start is not None:
                        start_cond = self._query_condition_for_path_value(cut_hierarchy.levels[0].key, start, '$gte' if not cut.invert else '$lt', for_project)
                if cut.to_path:
                    end = self._build_date_for_cut(cut_hierarchy, cut.to_path, is_end=True)
                    if end is not None:
                        end_cond = self._query_condition_for_path_value(cut_hierarchy.levels[0].key, end, '$lt' if not cut.invert else '$gte', for_project)

                if not cut.invert:
                    if start_cond:
                        conds.append(start_cond)
                    if end_cond:
                        conds.append(end_cond)
                else:
                    if start_cond and end_cond:
                        conds.append({'$or':[start_cond, end_cond]})
                    elif start_cond:
                        conds.append(start_cond)
                    elif end_cond:
                        conds.append(end_cond)

            if False:
                raise ArgumentError("No support yet for non-date range cuts in mongo backend")
                if cut.from_path:
                    last_idx = len(cut.from_path) - 1
                    for idx, p in enumerate(cut.from_path):
                        op = ( ("$lt", "$ne") if cut.invert else ("$gte", "$eq") )[0 if idx == last_idx else 1]
                        conds.append( self._query_condition_for_path_value(cut.dimension, p, op, for_project))
                if cut.to_path:
                    last_idx = len(cut.to_path) - 1
                    for idx, p in enumerate(cut.to_path):
                        op = ( ("$gt", "$ne") if cut.invert else ("$lte", "$eq") )[0 if idx == last_idx else 1]
                        conds.append( self._query_condition_for_path_value(cut.dimension, p, "$gt" if cut.invert else "$lte", for_project) )
        else:
            raise ValueError("Unrecognized cut object: %r" % cut)
        return conds

    def _query_condition_for_path_value(self, attr, value, op=None, for_project=False):
        phys = self.mapper.physical(attr)
        return phys.match_expression(value, op, for_project)

    def _order_to_sort_object(self, order=None):
        """Prepares mongo sort object from `order`. `order` is expected to be
        result from `prepare_order()`"""

        if not order:
            return []

        order_by = collections.OrderedDict()
        # each item is a 2-tuple of (logical_attribute_name, sort_order_string)

        for attribute, direction in order:
            ref = attribute.ref()

            sort_order = -1 if direction == 'desc' else 1

            if ref not in order_by:
                esc = escape_level(ref)
                order_by[esc] = (esc, sort_order)

        self.logger.debug("=== ORDER: %s" % order_by)
        return dict(order_by.values())

    def test(self, aggregate=False, **options):
        """Tests whether the statement can be constructed."""
        cell = Cell(self.cube)

        attributes = self.cube.all_attributes

        facts = self.facts(cell, page=0, page_size=1)
        # TODO: do something useful with the facts result

        # TODO: this might be slow
        if aggregate:
            result = self.aggregate()


def complex_sorted(items, sortings):
    if not sortings or not items:
        return items

    idx, direction = sortings.pop(0)

    if sortings:
        items = complex_sorted(items, sortings)

    return sorted(items, key=lambda x:x.get(idx) or x['_id'].get(idx), reverse=direction in set(['reverse', 'desc', '-1', -1]))


def escape_level(ref):
    return ref.replace('.', '___')


def unescape_level(ref):
    return ref.replace('___', '.')


class MongoFactsIterator(Facts):
    def __init__(self, facts, attributes, mapper, datesupport):
        super(MongoFactsIterator, self).__init__(facts, attributes)
        self.mapper = mapper
        self.datesupport = datesupport

    def __iter__(self):
        for fact in self.facts:
            fact = to_json_safe(fact)
            fact = collapse_record(fact)

            record = {}

            for attribute in self.attributes:
                physical = self.mapper.physical(attribute)
                value = fact.get(physical.field, attribute.missing_value)

                if value and physical.is_date_part:
                    if physical.extract != "week":
                        value = getattr(value, physical.extract)
                    else:
                        value = self.datesupport.calc_week(value)

                record[attribute.ref()] = value

            yield record

########NEW FILE########
__FILENAME__ = datesupport
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from dateutil.tz import *

from functools import partial
import pytz


DATE_PARTS = ['year', 'month', 'day']
TIME_PARTS = ['hour', 'minute', 'second', 'microsecond']

ALL_NONWEEK_PARTS = ['year', 'month', 'day'] + TIME_PARTS
ALL_WEEK_PARTS = ['week', 'dow_sort'] + TIME_PARTS


def enum(**enums):
    return type('Enum', (), enums)


WEEK_DAY = enum( MONDAY=0, TUESDAY=1, WEDNESDAY=2, THRUSDAY=3, \
                  FRIDAY=4, SATURDAY=5, SUNDAY=6)


WEEK_DAY_NAMES = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')


class MongoDateSupport(object):
    def __init__(self, logger, calendar):
        self.logger = logger
        self.timezone = calendar.timezone_name

        # calnedar.first_weekday is guaranteed to be a number
        self.start_of_week_weekday = calendar.first_weekday

        if (self.start_of_week_weekday == 0):
            self.end_of_week_weekday = WEEK_DAY.SUNDAY
        else:
            self.end_of_week_weekday = (self.start_of_week_weekday - 1)

        self.logger.debug("DateSupport created with timezone %s and start_of_week_weekday %s and end_of_week_weekday %s", self.timezone, self.start_of_week_weekday, self.end_of_week_weekday)

        self.datepart_functions = {
            'year': lambda x:x.year,
            'month': lambda x:x.month,
            'dow': self.calc_dow,
            'dow_sort': self.calc_dow_sort,
            'week': self.calc_week,
            'day': lambda x:x.day,
            'hour': lambda x:x.hour,
            'minute': lambda x:x.minute,
            'second': lambda x:x.second,
            'microsecond': lambda x:x.microsecond,
        }


        self.date_norm_map = {
            'month': 1,
            'day': 1,
            'hour': 0,
            'minute': 0,
            'second': 0,
            'microsecond': 0,
        }


    # filter, given a datepart, determines a datetime object for the current data
    def so_far_filter(self, initial, datepart, key=lambda x:x):
        def _so_far_filter(dt, initial, datepart):
            dateparts = list(ALL_WEEK_PARTS if datepart == 'week' else ALL_NONWEEK_PARTS)

            dt = key(dt)

            def _print(header):
                self.logger.debug("%s %s %s %s %s", header, dp, str(dp_fn(dt)) + ':' + str(dp_fn(initial)),dt.isoformat(), initial.isoformat())

            # for dateparts at greater granularity, if value is > than initial, discard.
            for dp in dateparts[dateparts.index(datepart) + 1:]:
                dp_fn = self.datepart_functions.get(dp)
                if dp_fn(dt) > dp_fn(initial):
                    _print('DISCARDED')
                    return None
                elif dp_fn(dt) < dp_fn(initial):
                    _print('KEPT')
                    return dt
            _print('KEPT')
            return dt
        return partial(_so_far_filter, initial=initial, datepart=datepart)


    def date_as_utc(self, year, tzinfo=None, **kwargs):

        tzinfo = tzinfo or self.timezone

        dateparts = {'year': year}
        dateparts.update(kwargs)

        date = datetime(**dateparts)
        tzinfo.localize(date)

        return date.astimezone(tzutc())


    def get_date_for_week(self, year, week):
        if week < 1:
            raise ValueError('Week must be greater than 0')

        dt = datetime(year, 1, 1)

        while dt.weekday() != self.end_of_week_weekday:
            dt += timedelta(1)

        week -= 1
        dt += timedelta(7 * week)

        return dt

    def calc_week(self, dt):
        return self.get_week_end_date(dt).strftime('%Y-%m-%d')

    def calc_dow(self, dt):
        return WEEK_DAY_NAMES[ dt.weekday() ]

    def calc_dow_sort(self, dt):
        return dt.weekday() + (7 - self.start_of_week_weekday) if dt.weekday() < self.start_of_week_weekday else dt.weekday() - self.start_of_week_weekday

    def clear(self, dt, parts=TIME_PARTS):
        replace_dict = {}

        for p in parts:
            replace_dict[p] = self.date_norm_map.get(p)

        return dt.replace(**replace_dict)


    def get_week_end_date(self, dt):
        dr = self.clear(dt)
        while dr.weekday() != self.end_of_week_weekday:
            dr += timedelta(1)
        return dr

    def get_week_start_date(self, dt):
        dr = self.clear(dt)
        while dr.weekday() != self.start_of_week_weekday:
                dr -= timedelta(1)
        return dr



########NEW FILE########
__FILENAME__ = functions
# -*- coding=utf -*-

from collections import namedtuple
from ...errors import *

try:
    import sqlalchemy
    import sqlalchemy.sql as sql
    from sqlalchemy.sql.functions import ReturnTypeFromArgs
except ImportError:
    from cubes.common import MissingPackage
    sqlalchemy = sql = MissingPackage("sqlalchemy", "SQL aggregation browser")
    missing_error = MissingPackage("sqlalchemy", "SQL browser extensions")

    class ReturnTypeFromArgs(object):
        def __init__(*args, **kwargs):
            # Just fail by trying to call missing package
            missing_error()


__all__ = (
    "get_aggregate_function",
    "available_aggregate_functions"
)


_aggregate_functions = {
    'count': {
        'group_by': (lambda field: { '$sum': 1 }),
        'aggregate_fn': len,
    },
    'sum': {
        'group_by': (lambda field: { '$sum': "$%s" % field }),
        'aggregate_fn': sum,
    },
    'first': {
        'group_by': (lambda field: { '$first': "$%s" % field }),
        'aggregate_fn': None,                                       # Is this used?
    },
    'last': {
        'group_by': (lambda field: { '$last': "$%s" % field }),
        'aggregate_fn': None,                                       # Is this used?
    },
    'custom': {
        'group_by' : (lambda field: { '$sum': 1 }),
        'aggregate_fn': len
    }
}


class MongoAggregationFunction(object):
    def __init__(self, name, function, group_by):
        """Creates a MongoDB aggregation function. `name` is the function name,
        `function` is the function for aggregation and `group_by` is a callable
        object that """

        self.name = name
        self.function = function
        self.group_by = group_by


def get_aggregate_function(name):
    """Returns an aggregate function `name`. The returned function takes two
    arguments: `aggregate` and `context`. When called returns a labelled
    SQL expression."""

    name = name or "identity"
    return _aggregate_functions[name]

def available_aggregate_functions():
    """Returns a list of available aggregate function names."""
    return _aggregate_functions.keys()



########NEW FILE########
__FILENAME__ = mapper
# -*- coding: utf-8 -*-
"""Logical to Physical Mapper for MongoDB"""

import collections
import copy
from ...logging import get_logger
from ...errors import *
from ...mapper import Mapper
from bson.objectid import ObjectId
import datetime
from datetime import datetime

__all__ = (
    "MongoCollectionMapper"
)

DEFAULT_KEY_FIELD = "_id"

MONGO_TYPES = {
    'string': str,
    'str': str,
    'objectid': ObjectId,
    'oid': ObjectId,
    'integer': int,
    'int': int,
    'float': float,
    'double': float
}

MONGO_EVAL_NS = {
    'datetime': datetime
}

MONGO_DATE_PARTS = ["year", "month", "day", "week", "hour", "minute"]

"""Physical reference to a mongo document field."""
class MongoDocumentField(object):
    def __init__(self, database, collection, field, match, project, group,
                 encode, decode, type_name=None, extract=None):
        """Creates a mongo document field.

        If a cut applies to the dimension, then a $match expression will be
        used to implement the cut

        If a drilldown applies to the dimension field, then a $project
        expression, with a key matching the logical ref() of the level, will be
        used in the aggregation pipeline
        """

        self.database = database
        self.collection = collection
        self.field = field
        self.match = match
        self.project = project
        self.group = None
        self.extract = extract
        self.is_date_part = extract in MONGO_DATE_PARTS

        if group:
            self.group = copy.deepcopy(group)

        # TODO: is this used?
        if encode:
            self.encode = eval(compile(encode, '__encode__', 'eval'), copy.copy(MONGO_EVAL_NS))
        else:
            self.encode = lambda x: x

        # TODO: is this used?
        if decode:
            self.decode = eval(compile(decode, '__decode__', 'eval'), copy.copy(MONGO_EVAL_NS))
        else:
            self.decode = lambda x: x

        type_name = str('string' if type_name is None else type_name)
        self.value_type = MONGO_TYPES.get(type_name.lower(), str)

    def group_expression(self):
        return copy.deepcopy(self.group) if self.group else self.group

    def match_expression(self, value, op=None, for_project=False):
        value = self.encode(value)
        field_name = ("$%s" % self.field) if for_project else self.field

        if op is None or (op == '$eq' and not for_project):
            return { field_name : value }
        elif for_project:
            return { op : [ field_name, value ] }
        else:
            return { field_name : { op : value } }

    def project_expression(self):
        if self.project:
            return copy.deepcopy(self.project)
        else:
            return "$%s" % self.field

    def convert_value(self, value):
        """Convert `value` according to field type"""
        return self.value_type(value)


# Special mappings:
# __query__ – used for all queries

def coalesce_physical(mapper, ref):
    if isinstance(ref, basestring):
        return MongoDocumentField(mapper.database, mapper.collection, ref,
                                  None, None, None, None, None, None)
    elif isinstance(ref, dict):
        return MongoDocumentField(
            ref.get('database', mapper.database),
            ref.get('collection', mapper.collection),
            ref.get('field'),
            ref.get('match'),
            ref.get('project'),
            ref.get('group'),
            ref.get("encode"),
            ref.get("decode"),
            ref.get("type"),
            ref.get("extract")
            )
    else:
        raise BackendError("Number of items in mongo document field reference"
                           " should be 1 (field name) or a dict of (field, "
                           "match, project, encode, decode)")


class MongoCollectionMapper(Mapper):
    """Mapper is core clas for translating logical model to physical
    database schema.
    """
    def __init__(self, cube, database, collection, mappings=None, **options):

        """A mongo collection mapper for a cube. The mapper creates required
        fields, project and match expressions, and encodes/decodes using
        provided python lambdas.

        Attributes:

        * `cube` - mapped cube
        * `mappings` – dictionary containing mappings

        `mappings` is a dictionary where keys are logical attribute references
        and values are mongo document field references. The keys are mostly in the
        form:

        * ``attribute`` for measures and fact details
        * ``dimension.attribute`` for dimension attributes

        The values might be specified as strings in the form ``field``
        (covering most of the cases) or as a dictionary with keys ``database``,
        ``collection`` and ``field`` for more customized references.

        """

        super(MongoCollectionMapper, self).__init__(cube, **options)

        self.database = database
        self.collection = collection
        self.mappings = mappings or cube.mappings

    def physical(self, attribute, locale=None):
        """Returns physical reference as tuple for `attribute`, which should
        be an instance of :class:`cubes.model.Attribute`. If there is no
        dimension specified in attribute, then fact table is assumed. The
        returned object is a MongoDocumentField object.
        """

        reference = None
        dimension = attribute.dimension

        # Try to get mapping if exists
        if self.cube.mappings:
            logical = self.logical(attribute, locale)

            # TODO: should default to non-localized reference if no mapping
            # was found?
            mapped_ref = self.cube.mappings.get(logical)

            if mapped_ref:
                reference = coalesce_physical(self, mapped_ref)

        # No mappings exist or no mapping was found - we are going to create
        # default physical reference
        if not reference:
            field_name = attribute.name

            if locale:
                field_name += "_" + locale

            reference = coalesce_physical(self, field_name)

        return reference


########NEW FILE########
__FILENAME__ = store
# -*- coding=utf -*-
from ...stores import Store
import pymongo

__all__ = []

class MongoStore(Store):
    def __init__(self, url, database=None, collection=None, **options):
        self.client = pymongo.MongoClient(url, read_preference=pymongo.read_preferences.ReadPreference.SECONDARY)
        self.database = database
        self.collection = collection


########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
import bson

def to_json_safe(item):
    """Appropriates the `item` to be safely dumped as JSON."""
    result = {}
    for key, value in item.items():
        if isinstance(value, bson.objectid.ObjectId):
            result[key] = str(value)
        else:
            result[key] = value

    return result

def collapse_record(record, separator = '.', root=None):
    """Collapses the `record` dictionary. If a value is a dictionary, then its
    keys are merged with the higher level dictionary.

    Example::

        {
            "date": {
                "year": 2013,
                "month" 10,
                "day": 1
            }
        }

    Will become::

        {
            "date.year": 2013,
            "date.month" 10,
            "date.day": 1
        }
    """

    result = {}
    for key, value in list(record.items()):
        if root:
            collapsed_key = root + separator + key
        else:
            collapsed_key = key

        if type(value) == dict:
            collapsed = collapse_record(value, separator, collapsed_key)
            result.update(collapsed)
        else:
            result[collapsed_key] = value

    return result



########NEW FILE########
__FILENAME__ = browser
# -*- coding=utf -*-

import urllib2
import json
import logging
import urllib
from ...logging import get_logger
from ...browser import *

class SlicerBrowser(AggregationBrowser):
    """Aggregation browser for Cubes Slicer OLAP server."""

    def __init__(self, cube, store, locale=None, **options):
        """Browser for another Slicer server.
        """
        super(SlicerBrowser, self).__init__(cube, store, locale)

        self.logger = get_logger()
        self.cube = cube
        self.locale = locale
        self.store = store

    def features(self):

        # Get the original features as provided by the Slicer server.
        # They are stored in browser_options in the Slicer model provider's
        # cube().
        features = dict(self.cube.browser_options.get("features", {}))

        # Replace only the actions, as we are not just a simple proxy.
        features["actions"] = ["aggregate", "facts", "fact", "cell", "members"]

        return features

    def provide_aggregate(self, cell, aggregates, drilldown, split, order,
                          page, page_size, **options):

        params = {}

        if cell:
            params["cut"] = string_from_cuts(cell.cuts)

        if drilldown:
            params["drilldown"] = ",".join(drilldown.items_as_strings())

        if split:
            params["split"] = str(split)

        if aggregates:
            names = [a.name for a in aggregates]
            params["aggregates"] = ",".join(names)

        if order:
            params["order"] = self._order_param(order)

        if page is not None:
            params["page"] = str(page)

        if page_size is not None:
            params["page_size"] = str(page_size)


        response = self.store.cube_request("aggregate",
                                           self.cube.basename, params)

        result = AggregationResult()

        result.cells = response.get('cells', [])

        if "summary" in response:
            result.summary = response.get('summary')

        result.levels = response.get('levels', {})
        result.labels = response.get('labels', [])
        result.cell = cell
        result.aggregates = response.get('aggregates', [])

        return result

    def facts(self, cell=None, fields=None, order=None, page=None,
              page_size=None):

        cell = cell or Cell(self.cube)
        if fields:
            attributes = self.cube.get_attributes(fields)
        else:
            attributes = []

        order = self.prepare_order(order, is_aggregate=False)

        params = {}

        if cell:
            params["cut"] = string_from_cuts(cell.cuts)

        if order:
            params["order"] = self._order_param(order)

        if page is not None:
            params["page"] = str(page)

        if page_size is not None:
            params["page_size"] = str(page_size)

        if attributes:
            params["fields"] = ",".join(str(attr) for attr in attributes)

        params["format"] = "json_lines"

        response = self.store.cube_request("facts", self.cube.basename, params,
                                           is_lines=True)

        return Facts(response, attributes)

    def provide_members(self, cell=None, dimension=None, levels=None,
                        hierarchy=None, attributes=None, page=None,
                        page_size=None, order=None, **options):

        params = {}

        if cell:
            params["cut"] = string_from_cuts(cell.cuts)

        if order:
            params["order"] = self._order_param(order)

        if levels:
            params["level"] = str(levels[-1])

        if hierarchy:
            params["hierarchy"] = str(hierarchy)

        if page is not None:
            params["page"] = str(page)

        if page_size is not None:
            params["page_size"] = str(page_size)

        if attributes:
            params["fields"] = ",".join(str(attr) for attr in attributes)

        params["format"] = "json_lines"

        action = "/cube/%s/members/%s" % (self.cube.basename, str(dimension))
        response = self.store.request(action, params, is_lines=True)

        return response

    def cell_details(self, cell, dimension=None):
        cell = cell or Cell(self.cube)

        params = {}
        if cell:
            params["cut"] = string_from_cuts(cell.cuts)

        if dimension:
            params["dimension"] = str(dimension)

        response = self.store.cube_request("cell", self.cube.basename, params) 

        return response

    def fact(self, fact_id):
        action = "/cube/%s/fact/%s" % (self.cube.basename, str(fact_id))
        response = self.store.request(action)
        return response

    def _order_param(self, order):
        """Prepare an order string in form: ``attribute:direction``"""
        string = ",".join("%s:%s" % (o[0], o[1]) for o in order)
        return string


########NEW FILE########
__FILENAME__ = store
# -*- coding=utf -*-
from ...model import *
from ...browser import *
from ...stores import Store
from ...providers import ModelProvider
from ...errors import *
from ...logging import get_logger
import json
import urllib2
import urllib

DEFAULT_SLICER_URL = "http://localhost:5000"

class _default_opener:
    def __init__(self):
        pass

    def open(self, url, *args, **kwargs):
        return urllib2.urlopen(url, *args, **kwargs)

class SlicerStore(Store):
    related_model_provider = "slicer"

    def __init__(self, url=None, authentication=None,
                 auth_identity=None, auth_parameter=None,
                 **options):

        url = url or DEFAULT_SLICER_URL

        self.url = url
        self.logger = get_logger()

        if authentication and authentication not in ["pass_parameter", "none"]:
            raise ConfigurationError("Unsupported authentication method '%s'"
                                     % authentication)

        self.authentication = authentication
        self.auth_identity = auth_identity
        self.auth_parameter = auth_parameter or "api_key"

        if "username" in options and "password" in options:
            # make a basic auth-enabled opener
            _pmgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            _pmgr.add_password(None, self.url, options['username'], options['password'])
            self.opener = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(_pmgr))
            self.logger.info("Created slicer opener using basic auth credentials with username %s", options['username'])
        else:
            self.opener = _default_opener()

        # TODO: cube prefix
        # TODO: model mappings as in mixpanel

    def request(self, action, params=None, is_lines=False):
        """
        * `action` – server action (path)
        # `params` – request parameters
        """

        params = dict(params) if params else {}

        if self.authentication == "pass_parameter":
            params[self.auth_parameter] = self.auth_identity

        params_str = urllib.urlencode(params)
        request_url = '%s/%s' % (self.url, action)

        if params_str:
            request_url += '?' + params_str

        self.logger.debug("slicer request: %s" % (request_url, ))
        response = self.opener.open(request_url)

        if response.getcode() == 404:
            raise MissingObjectError
        elif response.getcode() != 200:
            raise BackendError("Slicer request error (%s): %s"
                               % (response.getcode(), response.read()))

        if is_lines:
            return _JSONLinesIterator(response)
        else:
            try:
                result = json.loads(response.read())
            except:
                result = {}

            return result

    def cube_request(self, action, cube, params=None, is_lines=False):
        action = "cube/%s/%s" % (cube, action)
        return self.request(action, params, is_lines)


class _JSONLinesIterator(object):
    def __init__(self, stream):
        self.stream = stream

    def __iter__(self):
        for line in self.stream:
            yield json.loads(line)


class SlicerModelProvider(ModelProvider):

    def requires_store(self):
        return True

    def list_cubes(self):
        return self.store.request('cubes')

    def cube(self, name, locale=None):
        params = {}
        if locale:
            params["lang"] = locale
        try:
            cube_desc = self.store.cube_request("model", name, params)
        except MissingObjectError:
            raise NoSuchCubeError("Unknown cube '%s'" % name, name)

        # create_cube() expects dimensions to be a list of names and linked
        # later, the Slicer returns whole dimension descriptions

        dimensions = cube_desc.pop("dimensions")
        features = cube_desc.pop("features")

        if features:
            # Note: if there are "features" in the browser options, they are
            # eaten here. Is this ok? They should not be there as they should
            # have been processed by the original browser/workspace.
            browser_options = cube_desc.pop("browser_options", {})
            browser_options["features"] = features
            cube_desc["browser_options"] = browser_options

        # Link the cube in-place
        cube_desc['store'] = self.store_name
        cube = create_cube(cube_desc)
        for dim in dimensions:
            dim = create_dimension(dim)
            cube.add_dimension(dim)

        return cube

    def dimension(self, name, locale=None, tempaltes=None):
        raise NoSuchDimensionError(name)

########NEW FILE########
__FILENAME__ = browser
# -*- coding=utf -*-
# Actually, this is a furry snowflake, not a nice star

from __future__ import absolute_import

from ...browser import *
from ...logging import get_logger
from ...statutils import calculators_for_aggregates, available_calculators
from ...errors import *
from .mapper import SnowflakeMapper, DenormalizedMapper
from .functions import get_aggregate_function, available_aggregate_functions
from .query import QueryBuilder

import itertools
import collections

try:
    import sqlalchemy
    import sqlalchemy.sql as sql

except ImportError:
    from cubes.common import MissingPackage
    sqlalchemy = sql = MissingPackage("sqlalchemy", "SQL aggregation browser")

__all__ = [
    "SnowflakeBrowser",
]


class SnowflakeBrowser(AggregationBrowser):
    __options__ = [
        {
            "name": "include_summary",
            "type": "bool"
        },
        {
            "name": "include_cell_count",
            "type": "bool"
        },
        {
            "name": "use_denormalization",
            "type": "bool"
        },
        {
            "name": "safe_labels",
            "type": "bool"
        }

    ]

    def __init__(self, cube, store, locale=None, debug=False, **options):
        """SnowflakeBrowser is a SQL-based AggregationBrowser implementation that
        can aggregate star and snowflake schemas without need of having
        explicit view or physical denormalized table.

        Attributes:

        * `cube` - browsed cube
        * `locale` - locale used for browsing
        * `metadata` - SQLAlchemy MetaData object
        * `debug` - output SQL to the logger at INFO level
        * `options` - passed to the mapper and context (see their respective
          documentation)

        Tuning:

        * `include_summary` - it ``True`` then summary is included in
          aggregation result. Turned on by default.
        * `include_cell_count` – if ``True`` then total cell count is included
          in aggregation result. Turned on by default.
          performance reasons

        Limitations:

        * only one locale can be used for browsing at a time
        * locale is implemented as denormalized: one column for each language

        """
        super(SnowflakeBrowser, self).__init__(cube, store)

        if not cube:
            raise ArgumentError("Cube for browser should not be None.")

        self.logger = get_logger()

        self.cube = cube
        self.locale = locale or cube.locale
        self.debug = debug

        # Database connection and metadata
        # --------------------------------

        self.connectable = store.connectable
        self.metadata = store.metadata or sqlalchemy.MetaData(bind=self.connectable)

        # Options
        # -------

        # TODO this should be done in the store
        # merge options
        the_options = {}
        the_options.update(store.options)
        the_options.update(options)
        options = the_options

        self.include_summary = options.get("include_summary", True)
        self.include_cell_count = options.get("include_cell_count", True)
        self.safe_labels = options.get("safe_labels", False)
        self.label_counter = 1

        # Whether to ignore cells where at least one aggregate is NULL
        self.exclude_null_agregates = options.get("exclude_null_agregates",
                                                 True)

        # Mapper
        # ------

        # Mapper is responsible for finding corresponding physical columns to
        # dimension attributes and fact measures. It also provides information
        # about relevant joins to be able to retrieve certain attributes.

        if options.get("use_denormalization"):
            mapper_class = DenormalizedMapper
        else:
            mapper_class = SnowflakeMapper

        self.logger.debug("using mapper %s for cube '%s' (locale: %s)" %
                          (str(mapper_class.__name__), cube.name, locale))

        self.mapper = mapper_class(cube, locale=self.locale, **options)
        self.logger.debug("mapper schema: %s" % self.mapper.schema)

    def features(self):
        """Return SQL features. Currently they are all the same for every
        cube, however in the future they might depend on the SQL engine or
        other factors."""

        features = {
            "actions": ["aggregate", "fact", "members", "facts", "cell"],
            "aggregate_functions": available_aggregate_functions(),
            "post_aggregate_functions": available_calculators()
        }

        return features

    def is_builtin_function(self, name, aggregate):
        return self.builtin_function(name, aggregate) is not None

    def set_locale(self, locale):
        """Change the browser's locale"""
        self.logger.debug("changing browser's locale to %s" % locale)
        self.mapper.set_locale(locale)
        self.locale = locale

    def fact(self, key_value, fields=None):
        """Get a single fact with key `key_value` from cube.

        Number of SQL queries: 1."""

        attributes = self.cube.get_attributes(fields)

        builder = QueryBuilder(self)
        builder.denormalized_statement(attributes=attributes,
                                       include_fact_key=True)

        builder.fact(key_value)

        cursor = self.execute_statement(builder.statement, "facts")
        row = cursor.fetchone()

        if row:
            # Convert SQLAlchemy object into a dictionary
            record = dict(zip(builder.labels, row))
        else:
            record = None

        cursor.close()

        return record

    def facts(self, cell=None, fields=None, order=None, page=None,
              page_size=None):
        """Return all facts from `cell`, might be ordered and paginated.

        Number of SQL queries: 1.
        """

        cell = cell or Cell(self.cube)

        attributes = self.cube.get_attributes(fields)

        builder = QueryBuilder(self)
        builder.denormalized_statement(cell,
                                       attributes,
                                       include_fact_key=True)
        builder.paginate(page, page_size)
        order = self.prepare_order(order, is_aggregate=False)
        builder.order(order)

        cursor = self.execute_statement(builder.statement,
                                        "facts")

        return ResultIterator(cursor, builder.labels)

    def test(self, aggregate=False, **options):
        """Tests whether the statement can be constructed."""
        cell = Cell(self.cube)

        attributes = self.cube.all_attributes

        builder = QueryBuilder(self)
        statement = builder.denormalized_statement(cell,
                                                   attributes)
        statement = statement.limit(1)
        result = self.connectable.execute(statement)
        result.close()

        if aggregate:
            result = self.aggregate()

    def provide_members(self, cell, dimension, depth=None, hierarchy=None,
                        levels=None, attributes=None, page=None,
                        page_size=None, order=None):
        """Return values for `dimension` with level depth `depth`. If `depth`
        is ``None``, all levels are returned.

        Number of database queries: 1.
        """
        if not attributes:
            attributes = []
            for level in levels:
                attributes += level.attributes

        builder = QueryBuilder(self)
        builder.members_statement(cell, attributes)
        builder.paginate(page, page_size)
        builder.order(order)

        result = self.execute_statement(builder.statement, "members")

        return ResultIterator(result, builder.labels)

    def path_details(self, dimension, path, hierarchy=None):
        """Returns details for `path` in `dimension`. Can be used for
        multi-dimensional "breadcrumbs" in a used interface.

        Number of SQL queries: 1.
        """
        dimension = self.cube.dimension(dimension)
        hierarchy = dimension.hierarchy(hierarchy)

        cut = PointCut(dimension, path, hierarchy=hierarchy)
        cell = Cell(self.cube, [cut])

        attributes = []
        for level in hierarchy.levels[0:len(path)]:
            attributes += level.attributes

        builder = QueryBuilder(self)
        builder.denormalized_statement(cell,
                                       attributes,
                                       include_fact_key=True)
        builder.paginate(0, 1)
        cursor = self.execute_statement(builder.statement,
                                        "path details")

        row = cursor.fetchone()

        if row:
            member = dict(zip(builder.labels, row))
        else:
            member = None

        return member

    def execute_statement(self, statement, label=None):
        """Execute the `statement`, optionally log it. Returns the result
        cursor."""
        self._log_statement(statement, label)
        return self.connectable.execute(statement)

    def provide_aggregate(self, cell, aggregates, drilldown, split, order,
                          page, page_size, **options):
        """Return aggregated result.

        Arguments:

        * `cell`: cell to be aggregated
        * `measures`: aggregates of these measures will be considered
        * `aggregates`: aggregates to be considered
        * `drilldown`: list of dimensions or list of tuples: (`dimension`,
          `hierarchy`, `level`)
        * `split`: an optional cell that becomes an extra drilldown segmenting
          the data into those within split cell and those not within
        * `attributes`: list of attributes from drilled-down dimensions to be
          returned in the result

        Query tuning:

        * `include_cell_count`: if ``True`` (``True`` is default) then
          `result.total_cell_count` is
          computed as well, otherwise it will be ``None``.
        * `include_summary`: if ``True`` (default) then summary is computed,
          otherwise it will be ``None``

        Result is paginated by `page_size` and ordered by `order`.

        Number of database queries:

        * without drill-down: 1 – summary
        * with drill-down (default): 3 – summary, drilldown, total drill-down
          record count

        Notes:

        * measures can be only in the fact table

        """

        result = AggregationResult(cell=cell, aggregates=aggregates)

        # Summary
        # -------

        if self.include_summary or not (drilldown or split):

            builder = QueryBuilder(self)
            builder.aggregation_statement(cell,
                                          aggregates=aggregates,
                                          drilldown=drilldown,
                                          summary_only=True)

            cursor = self.execute_statement(builder.statement,
                                            "aggregation summary")
            row = cursor.fetchone()

            # TODO: use builder.labels
            if row:
                # Convert SQLAlchemy object into a dictionary
                record = dict(zip(builder.labels, row))
            else:
                record = None

            cursor.close()
            result.summary = record


        # Drill-down
        # ----------
        #
        # Note that a split cell if present prepends the drilldown

        if drilldown or split:
            if not (page_size and page is not None):
                self.assert_low_cardinality(cell, drilldown)

            result.levels = drilldown.result_levels(include_split=bool(split))

            self.logger.debug("preparing drilldown statement")

            builder = QueryBuilder(self)
            builder.aggregation_statement(cell,
                                          drilldown=drilldown,
                                          aggregates=aggregates,
                                          split=split)
            builder.paginate(page, page_size)
            builder.order(order)

            cursor = self.execute_statement(builder.statement,
                                            "aggregation drilldown")

            #
            # Find post-aggregation calculations and decorate the result
            #
            result.calculators = calculators_for_aggregates(self.cube,
                                                            aggregates,
                                                            drilldown,
                                                            split,
                                                            available_aggregate_functions())
            result.cells = ResultIterator(cursor, builder.labels)
            result.labels = builder.labels

            # TODO: Introduce option to disable this

            if self.include_cell_count:
                count_statement = builder.statement.alias().count()
                row_count = self.execute_statement(count_statement).fetchone()
                total_cell_count = row_count[0]
                result.total_cell_count = total_cell_count

        elif result.summary is not None:
            # Do calculated measures on summary if no drilldown or split
            # TODO: should not we do this anyway regardless of
            # drilldown/split?
            calculators = calculators_for_aggregates(self.cube,
                                                     aggregates,
                                                    drilldown,
                                                    split,
                                                    available_aggregate_functions())
            for calc in calculators:
                calc(result.summary)

        # If exclude_null_aggregates is True then don't include cells where
        # at least one of the bult-in aggregates is NULL
        if result.cells is not None and self.exclude_null_agregates:
            afuncs = available_aggregate_functions()
            aggregates = [agg for agg in aggregates if not agg.function or agg.function in afuncs]
            names = [str(agg) for agg in aggregates]
            result.exclude_if_null = names

        return result

    def builtin_function(self, name, aggregate):
        """Returns a built-in function for `aggregate`"""
        try:
            function = get_aggregate_function(name)
        except KeyError:
            if name and not name in available_calculators():
                raise ArgumentError("Unknown aggregate function %s "
                                    "for aggregate %s" % \
                                    (name, str(aggregate)))
            else:
                # The function is post-aggregation calculation
                return None

        return function

    def _log_statement(self, statement, label=None):
        label = "SQL(%s):" % label if label else "SQL:"
        self.logger.debug("%s\n%s\n" % (label, str(statement)))

    def validate(self):
        """Validate physical representation of model. Returns a list of
        dictionaries with keys: ``type``, ``issue``, ``object``.

        Types might be: ``join`` or ``attribute``.

        The ``join`` issues are:

        * ``no_table`` - there is no table for join
        * ``duplicity`` - either table or alias is specified more than once

        The ``attribute`` issues are:

        * ``no_table`` - there is no table for attribute
        * ``no_column`` - there is no column for attribute
        * ``duplicity`` - attribute is found more than once

        """
        issues = []

        # Check joins

        tables = set()
        aliases = set()
        alias_map = {}
        #
        for join in self.mapper.joins:
            self.logger.debug("join: %s" % (join, ))

            if not join.master.column:
                issues.append(("join", "master column not specified", join))
            if not join.detail.table:
                issues.append(("join", "detail table not specified", join))
            elif join.detail.table == self.mapper.fact_name:
                issues.append(("join", "detail table should not be fact table", join))

            master_table = (join.master.schema, join.master.table)
            tables.add(master_table)

            detail_alias = (join.detail.schema, join.alias or join.detail.table)

            if detail_alias in aliases:
                issues.append(("join", "duplicate detail table %s" % detail_table, join))
            else:
                aliases.add(detail_alias)

            detail_table = (join.detail.schema, join.detail.table)
            alias_map[detail_alias] = detail_table

            if detail_table in tables and not join.alias:
                issues.append(("join", "duplicate detail table %s (no alias specified)" % detail_table, join))
            else:
                tables.add(detail_table)

        # Check for existence of joined tables:
        physical_tables = {}

        # Add fact table to support simple attributes
        physical_tables[(self.fact_table.schema, self.fact_table.name)] = self.fact_table
        for table in tables:
            try:
                physical_table = sqlalchemy.Table(table[1], self.metadata,
                                        autoload=True,
                                        schema=table[0] or self.mapper.schema)
                physical_tables[(table[0] or self.mapper.schema, table[1])] = physical_table
            except sqlalchemy.exc.NoSuchTableError:
                issues.append(("join", "table %s.%s does not exist" % table, join))

        # check attributes

        attributes = self.mapper.all_attributes()
        physical = self.mapper.map_attributes(attributes)

        for attr, ref in zip(attributes, physical):
            alias_ref = (ref.schema, ref.table)
            table_ref = alias_map.get(alias_ref, alias_ref)
            table = physical_tables.get(table_ref)

            if table is None:
                issues.append(("attribute", "table %s.%s does not exist for attribute %s" % (table_ref[0], table_ref[1], self.mapper.logical(attr)), attr))
            else:
                try:
                    c = table.c[ref.column]
                except KeyError:
                    issues.append(("attribute", "column %s.%s.%s does not exist for attribute %s" % (table_ref[0], table_ref[1], ref.column, self.mapper.logical(attr)), attr))

        return issues


class ResultIterator(object):
    """
    Iterator that returns SQLAlchemy ResultProxy rows as dictionaries
    """
    def __init__(self, result, labels):
        self.result = result
        self.batch = None
        self.labels = labels
        self.exclude_if_null = None

    def __iter__(self):
        while True:
            if not self.batch:
                many = self.result.fetchmany()
                if not many:
                    break
                self.batch = collections.deque(many)

            row = self.batch.popleft()

            if self.exclude_if_null \
                    and any(cell[agg] is None for agg in self.exclude_if_nul):
                continue

            yield dict(zip(self.labels, row))

########NEW FILE########
__FILENAME__ = functions
# -*- coding=utf -*-

from collections import namedtuple
from ...errors import *

try:
    import sqlalchemy
    import sqlalchemy.sql as sql
    from sqlalchemy.sql.functions import ReturnTypeFromArgs
except ImportError:
    from cubes.common import MissingPackage
    sqlalchemy = sql = MissingPackage("sqlalchemy", "SQL aggregation browser")
    missing_error = MissingPackage("sqlalchemy", "SQL browser extensions")

    class ReturnTypeFromArgs(object):
        def __init__(*args, **kwargs):
            # Just fail by trying to call missing package
            missing_error()


__all__ = (
    "get_aggregate_function",
    "available_aggregate_functions"
)


class AggregateFunction(object):
    requires_measure = True

    # if `True` then on `coalesce` the values are coalesced to 0 before the
    # aggregation. If `False` then the values are as they are and the result is
    # coalesced to 0.
    coalesce_values = True

    def __init__(self, name_, function_=None, *args, **kwargs):
        self.name = name_
        self.function = function_
        self.args = args
        self.kwargs = kwargs

    def __call__(self, aggregate, context, coalesce=False):
        """Applied the function on the aggregate and returns labelled
        expression. SQL expression label is the aggregate's name. This method
        calls `apply()` method which can be overriden by subclasses."""

        expression = self.apply(aggregate, context, coalesce)
        expression = expression.label(aggregate.name)
        return expression

    def coalesce_value(self, aggregate, value):
        """Coalesce the value before aggregation of `aggregate`. `value` is a
        SQLAlchemy expression. Default implementation does nothing, just
        returns the `value`."""
        return value

    def coalesce_aggregate(self, aggregate, value):
        """Coalesce the aggregated value of `aggregate`. `value` is a
        SQLAlchemy expression. Default implementation does nothing, just
        returns the `value`."""
        return value

    def required_measures(self, aggregate):
        """Returns a list of measure names that the `aggregate` depends on."""
        # Currently only one-attribute source is supported, therefore we just
        # return the attribute.
        if aggregate.measure:
            return [aggregate.measure]
        else:
            return []

    # TODO: use dict of name:measure from required_measures instead of context
    def apply(self, aggregate, context=None, coalesce=False):
        """Apply the function on the aggregate. Subclasses might override this
        method and use other `aggregates` and browser context.

        If `missing_value` is not `None`, then the aggregate's source value
        should be wrapped in ``COALESCE(column, missing_value)``.

        Returns a SQLAlchemy expression."""

        if not context:
            raise InternalError("No context provided for AggregationFunction")

        if not aggregate.measure:
            raise ModelError("No measure specified for aggregate %s, "
                             "required for aggregate function %s"
                             % (str(aggregate), self.name))

        try:
            source = context.cube.measure(aggregate.measure)
        except NoSuchAttributeError:
            source = context.cube.aggregate(aggregate.measure)

        column = context.column(source)

        if coalesce:
            column = self.coalesce_value(aggregate, column)

        expression = self.function(column, *self.args, **self.kwargs)

        if coalesce:
            expression = self.coalesce_aggregate(aggregate, expression)

        return expression

    def __str__(self):
        return self.name

class ValueCoalescingFunction(AggregateFunction):
    def coalesce_value(self, aggregate, value):
        """Coalesce the value before aggregation of `aggregate`. `value` is a
        SQLAlchemy expression.  Default implementation coalesces to zero 0."""
        # TODO: use measure's missing value (we need to get the measure object
        # somehow)
        return sql.functions.coalesce(value, 0)


class SummaryCoalescingFunction(AggregateFunction):
    def coalesce_aggregate(self, aggregate, value):
        """Coalesce the aggregated value of `aggregate`. `value` is a
        SQLAlchemy expression.  Default implementation does nothing."""
        # TODO: use aggregates's missing value
        return sql.functions.coalesce(value, 0)


class GenerativeFunction(AggregateFunction):
    def __init__(self, name, function=None, *args, **kwargs):
        """Creates a function that generates a value without using any of the
        measures."""
        super(GenerativeFunction, self).__init__(name, function)

    def apply(self, aggregate, context=None, coalesce=False):
        return self.function(*self.args, **self.kwargs)


class FactCountFunction(AggregateFunction):
    def __init__(self, name, function=None, *args, **kwargs):
        """Creates a function that provides fact (record) counts.  """
        super(FactCountFunction, self).__init__(name, function)

    def apply(self, aggregate, context=None, coalesce=False):
        """Count only existing facts. Assumption: every facts has an ID"""

        if coalesce:
            # TODO: pass the fact column somehow more nicely, maybe in a map:
            # aggregate: column
            column = context.fact_key_column()
            return sql.functions.count(column)
        else:
            return sql.functions.count(1)


class FactCountDistinctFunction(AggregateFunction):
    def __init__(self, name):
        """Creates a function that provides distinct fact (record) counts."""
        function = lambda x: sql.functions.count(sql.expression.distinct(x))
        super(FactCountDistinctFunction, self).__init__(name, function)


class avg(ReturnTypeFromArgs):
    pass


# Works with PostgreSQL
class stddev(ReturnTypeFromArgs):
    pass


class variance(ReturnTypeFromArgs):
    pass


_functions = (
    SummaryCoalescingFunction("sum", sql.functions.sum),
    SummaryCoalescingFunction("count_nonempty", sql.functions.count),
    FactCountFunction("count"),
    FactCountDistinctFunction("count_distinct"),
    ValueCoalescingFunction("min", sql.functions.min),
    ValueCoalescingFunction("max", sql.functions.max),
    ValueCoalescingFunction("avg", avg),
    ValueCoalescingFunction("stddev", stddev),
    ValueCoalescingFunction("variance", variance),
    ValueCoalescingFunction("custom", lambda c: c),
)

_function_dict = {}


def _create_function_dict():
    if not _function_dict:
        for func in _functions:
            _function_dict[func.name] = func


def get_aggregate_function(name):
    """Returns an aggregate function `name`. The returned function takes two
    arguments: `aggregate` and `context`. When called returns a labelled
    SQL expression."""

    _create_function_dict()
    return _function_dict[name]


def available_aggregate_functions():
    """Returns a list of available aggregate function names."""
    _create_function_dict()
    return _function_dict.keys()


########NEW FILE########
__FILENAME__ = logging
# -*- coding=utf -*-

from __future__ import absolute_import

from ...server.logging import RequestLogHandler, REQUEST_LOG_ITEMS
from sqlalchemy import create_engine, Table, MetaData, Column
from sqlalchemy import Integer, Sequence, DateTime, String, Float
from sqlalchemy.exc import NoSuchTableError
from ...browser import string_to_drilldown, Drilldown
from .store import create_sqlalchemy_engine

import logging

class SQLRequestLogHandler(RequestLogHandler):
    def __init__(self, url=None, table=None, dimensions_table=None, **options):

        self.url = url
        self.engine = create_sqlalchemy_engine(url, options)

        metadata = MetaData(bind=self.engine)

        logging.getLogger('sqlalchemy.engine').setLevel("DEBUG")
        logging.getLogger('sqlalchemy.pool').setLevel("DEBUG")

        try:
            self.table = Table(table, metadata, autoload=True)

        except NoSuchTableError:
            columns = [
                Column('id', Integer, Sequence(table+"_seq"),
                       primary_key=True),
                Column('timestamp', DateTime),
                Column('method', String(50)),
                Column('cube', String(250)),
                Column('cell', String(2000)),
                Column('identity', String(250)),
                Column('elapsed_time', Float),
                Column('attributes', String(2000)),
                Column('split', String(2000)),
                Column('drilldown', String(2000)),
                Column('page', Integer),
                Column('page_size', Integer),
                Column('format', String(50)),
                Column('header', String(50)),
            ]

            self.table = Table(table, metadata, extend_existing=True, *columns)
            self.table.create()

        # Dimensions table: use of dimensions
        # Used-as: cut, split, drilldown
        # Value:
        #     cut: cut value
        #     split: cut value

        if dimensions_table:
            try:
                self.dims_table = Table(dimensions_table, metadata, autoload=True)

            except NoSuchTableError:
                columns = [
                    Column('id', Integer, Sequence(table+"_seq"),
                           primary_key=True),
                    Column('query_id', Integer),
                    Column('dimension', String(250)),
                    Column('hierarchy', String(250)),
                    Column('level', String(250)),
                    Column('used_as', String(50)),
                    Column('value', String(2000)),
                ]

                self.dims_table = Table(dimensions_table, metadata, extend_existing=True, *columns)
                self.dims_table.create()
        else:
            self.dims_table = None

    def write_record(self, cube, cell, record):
        drilldown = record.get("drilldown")

        if drilldown is not None:
            if cell:
                drilldown = Drilldown(drilldown, cell)
                record["drilldown"] = str(drilldown)
            else:
                drilldown = []
                record["drilldown"] = None

        connection = self.engine.connect()
        trans = connection.begin()

        insert = self.table.insert().values(record)
        result = connection.execute(insert)
        query_id = result.inserted_primary_key[0]

        if self.dims_table is not None:
            uses = []

            cuts = cell.cuts if cell else []
            cuts = cuts or []

            for cut in cuts:
                dim = cube.dimension(cut.dimension)
                depth = cut.level_depth()
                if depth:
                    level = dim.hierarchy(cut.hierarchy)[depth-1]
                    level_name = str(level)
                else:
                    level_name = None

                use = {
                    "query_id": query_id,
                    "dimension": str(dim),
                    "hierarchy": str(cut.hierarchy),
                    "level": str(level_name),
                    "used_as": "cell",
                    "value": str(cut)
                }
                uses.append(use)

            if drilldown:
                for item in drilldown:
                    (dim, hier, levels) = item[0:3]
                    if levels:
                        level = str(levels[-1])
                    else:
                        level = None

                    use = {
                        "query_id": query_id,
                        "dimension": str(dim),
                        "hierarchy": str(hier),
                        "level": str(level),
                        "used_as": "drilldown",
                        "value": None
                    }
                    uses.append(use)


            if uses:
                insert = self.dims_table.insert().values(uses)
                connection.execute(insert)

        trans.commit()
        connection.close()


########NEW FILE########
__FILENAME__ = mapper
# -*- coding: utf-8 -*-
"""Logical to Physical Mappers"""

from ...logging import get_logger
from ...errors import *
from ...mapper import Mapper
from collections import namedtuple
from ...model import AttributeBase

__all__ = (
    "SnowflakeMapper",
    "DenormalizedMapper",
    "TableColumnReference",
    "TableJoin",
    "coalesce_physical",
    "PhysicalAttribute",
    "DEFAULT_KEY_FIELD"
)

DEFAULT_KEY_FIELD = "id"

"""Physical reference to a table column. Note that the table might be an
aliased table name as specified in relevant join."""
TableColumnReference = namedtuple("TableColumnReference",
                                    ["schema", "table", "column", "extract", "func", "expr", "condition"])

"""Table join specification. `master` and `detail` are TableColumnReference
tuples. `method` denotes which table members should be considered in the join:
*master* – all master members (left outer join), *detail* – all detail members
(right outer join) and *match* – members must match (inner join)."""
TableJoin = namedtuple("TableJoin",
                                    ["master", "detail", "alias", "method"])


SnowflakeTable = namedtuple("SnowflakeTable",
                            ["schema", "table", "outlets"])

_join_method_order = {"detail":0, "master":1, "match": 2}

# Note to developers: Used for internal purposes to represent a physical table
# column. Currently used only in the PTD condition.
class PhysicalAttribute(AttributeBase):
    def __init__(self, name, label=None, description=None, order=None,
                 info=None, format=None, table=None, missing_value=None,
                 **kwargs):
        super(PhysicalAttribute, self).__init__(name=name, label=label,
                                        description=description, order=order,
                                        info=info, format=format,
                                        missing_value=missing_value)
        self.table = table

    def ref(self, simplify=True, locale=None):
        if self.table is not None:
            return "%s.%s" % (self.table, self.name)
        else:
            return self.name

def coalesce_physical(ref, default_table=None, schema=None):
    """Coalesce physical reference `ref` which might be:

    * a string in form ``"table.column"``
    * a list in form ``(table, column)``
    * a list in form ``(schema, table, column)``
    * a dictionary with keys: ``schema``, ``table``, ``column``, ``extract``, ``func``, ``expr``, ``condition`` where
      ``column`` is required, the rest are optional

    Returns tuple (`schema`, `table`, `column`, `extract`, `func`, `expr`, `condition`), which is a named
    tuple `TableColumnReference`.

    If no table is specified in reference and `default_table` is not
    ``None``, then `default_table` will be used.

    .. note::

        The `table` element might be a table alias specified in list of joins.

    """

    if isinstance(ref, basestring):
        split = ref.split(".")

        if len(split) > 1:
            dim_name = split[0]
            attr_name = ".".join(split[1:])
            return TableColumnReference(schema, dim_name, attr_name, None, None, None, None)
        else:
            return TableColumnReference(schema, default_table, ref, None, None, None, None)
    elif isinstance(ref, dict):
        return TableColumnReference(ref.get("schema", schema),
                                 ref.get("table", default_table),
                                 ref.get("column"),
                                 ref.get("extract"),
                                 ref.get("func"),
                                 ref.get("expr"),
                                 ref.get("condition"))
    else:
        if len(ref) == 2:
            return TableColumnReference(schema, ref[0], ref[1], None, None, None, None)
        elif len(ref) == 3:
            return TableColumnReference(ref[0], ref[1], ref[2], None, None, None, None)
        else:
            raise BackendError("Number of items in table reference should "\
                               "be 2 (table, column) or 3 (schema, table, column)")


class SnowflakeMapper(Mapper):
    """Mapper is core clas for translating logical model to physical
    database schema.
    """
    # WARNING: do not put any SQL/engine/connection related stuff into this
    # class yet. It might be moved to the cubes as one of top-level modules
    # and subclassed here.

    def __init__(self, cube, mappings=None, locale=None, schema=None,
                 fact_name=None, dimension_prefix=None, dimension_suffix=None,
                 joins=None, dimension_schema=None, **options):

        """A snowflake schema mapper for a cube. The mapper creates required
        joins, resolves table names and maps logical references to tables and
        respective columns.

        Attributes:

        * `cube` - mapped cube
        * `mappings` – dictionary containing mappings
        * `simplify_dimension_references` – references for flat dimensions
          (with one level and no details) will be just dimension names, no
          attribute name. Might be useful when using single-table schema, for
          example, with couple of one-column dimensions.
        * `dimension_prefix` – default prefix of dimension tables, if
          default table name is used in physical reference construction
        * `dimension_suffix` – default suffix of dimension tables, if
          default table name is used in physical reference construction
        * `fact_name` – fact name, if not specified then `cube.name` is used
        * `schema` – default database schema
        * `dimension_schema` – schema whre dimension tables are stored (if
          different than fact table schema)

        `mappings` is a dictionary where keys are logical attribute references
        and values are table column references. The keys are mostly in the
        form:

        * ``attribute`` for measures and fact details
        * ``attribute.locale`` for localized fact details
        * ``dimension.attribute`` for dimension attributes
        * ``dimension.attribute.locale`` for localized dimension attributes

        The values might be specified as strings in the form ``table.column``
        (covering most of the cases) or as a dictionary with keys ``schema``,
        ``table`` and ``column`` for more customized references.

        .. In the future it might support automatic join detection.

        """

        super(SnowflakeMapper, self).__init__(cube, locale=locale, **options)

        self.mappings = mappings or cube.mappings
        self.dimension_prefix = dimension_prefix or ""
        self.dimension_suffix = dimension_suffix or ""
        self.dimension_schema = dimension_schema

        fact_prefix = options.get("fact_prefix") or ""
        fact_suffix = options.get("fact_suffix") or ""
        self.fact_name = fact_name or self.cube.fact or "%s%s%s" % \
                            (fact_prefix, self.cube.basename, fact_suffix)
        self.schema = schema

        self._collect_joins(joins or cube.joins)

    def _collect_joins(self, joins):
        """Collects joins and coalesce physical references. `joins` is a
        dictionary with keys: `master`, `detail` reffering to master and
        detail keys. `alias` is used to give alternative name to a table when
        two tables are being joined."""

        joins = joins or []

        self.joins = []

        for join in joins:
            master = coalesce_physical(join["master"],self.fact_name,schema=self.schema)
            detail = coalesce_physical(join["detail"],schema=self.schema)

            self.logger.debug("collecting join %s -> %s" % (tuple(master), tuple(detail)))
            method = join.get("method", "match").lower()

            self.joins.append(TableJoin(master, detail, join.get("alias"),
                                        method))

    def physical(self, attribute, locale=None):
        """Returns physical reference as tuple for `attribute`, which should
        be an instance of :class:`cubes.model.Attribute`. If there is no
        dimension specified in attribute, then fact table is assumed. The
        returned tuple has structure: (`schema`, `table`, `column`).

        The algorithm to find physicl reference is as follows::

            IF localization is requested:
                IF is attribute is localizable:
                    IF requested locale is one of attribute locales
                        USE requested locale
                    ELSE
                        USE default attribute locale
                ELSE
                    do not localize

            IF mappings exist:
                GET string for logical reference
                IF locale:
                    append '.' and locale to the logical reference

                IF mapping value exists for localized logical reference
                    USE value as reference

            IF no mappings OR no mapping was found:
                column name is attribute name

                IF locale:
                    append '_' and locale to the column name

                IF dimension specified:
                    # Example: 'date.year' -> 'date.year'
                    table name is dimension name

                    IF there is dimension table prefix
                        use the prefix for table name

                ELSE (if no dimension is specified):
                    # Example: 'date' -> 'fact.date'
                    table name is fact table name
        """

        schema = self.dimension_schema or self.schema

        if isinstance(attribute, PhysicalAttribute):
            reference = TableColumnReference(schema,
                                             attribute.table,
                                             attribute.name,
                                             None, None, None, None)
            return reference

        reference = None

        # Fix locale: if attribute is not localized, use none, if it is
        # localized, then use specified if exists otherwise use default
        # locale of the attribute (first one specified in the list)

        locale = locale or self.locale

        if attribute.is_localizable():
            locale = locale if locale in attribute.locales \
                                else attribute.locales[0]
        else:
            locale = None

        # Try to get mapping if exists
        if self.cube.mappings:
            logical = self.logical(attribute, locale)

            # TODO: should default to non-localized reference if no mapping
            # was found?
            mapped_ref = self.cube.mappings.get(logical)

            if mapped_ref:
                reference = coalesce_physical(mapped_ref, self.fact_name, self.schema)

        # No mappings exist or no mapping was found - we are going to create
        # default physical reference
        if not reference:
            column_name = attribute.name

            if locale:
                column_name += "_" + locale

            # TODO: temporarily preserved. it should be attribute.owner
            dimension = attribute.dimension
            if dimension and not (self.simplify_dimension_references \
                                   and (dimension.is_flat
                                        and not dimension.has_details)):
                table_name = "%s%s%s" % (self.dimension_prefix, dimension, self.dimension_suffix)
            else:
                table_name = self.fact_name

            reference = TableColumnReference(schema, table_name, column_name, None, None, None, None)

        return reference

    def table_map(self):
        """Return list of references to all tables. Keys are aliased
        tables: (`schema`, `aliased_table_name`) and values are
        real tables: (`schema`, `table_name`). Included is the fact table
        and all tables mentioned in joins.

        To get list of all physical tables where aliased tablesare included
        only once::

            finder = JoinFinder(cube, joins, fact_name)
            tables = set(finder.table_map().keys())
        """

        tables = {
            (self.schema, self.fact_name): (self.schema, self.fact_name)
        }

        for join in self.joins:
            if not join.detail.table or (join.detail.table == self.fact_name and not join.alias):
                raise BackendError("Detail table name should be present and should not be a fact table unless aliased.")

            ref = (join.master.schema, join.master.table)
            tables[ref] = ref

            ref = (join.detail.schema, join.alias or join.detail.table)
            tables[ref] = (join.detail.schema, join.detail.table)

        return tables

    def physical_references(self, attributes, expand_locales=False):
        """Convert `attributes` to physical attributes. If `expand_locales` is
        ``True`` then physical reference for every attribute locale is
        returned."""

        if expand_locales:
            physical_attrs = []

            for attr in attributes:
                if attr.is_localizable():
                    refs = [self.physical(attr, locale) for locale in attr.locales]
                else:
                    refs = [self.physical(attr)]
                physical_attrs += refs
        else:
            physical_attrs = [self.physical(attr) for attr in attributes]

        return physical_attrs

    def tables_for_attributes(self, attributes, expand_locales=False):
        """Returns a list of tables – tuples (`schema`, `table`) that contain
        `attributes`."""

        references = self.physical_references(attributes, expand_locales)
        tables = [(ref[0], ref[1]) for ref in references]
        return tables

    def relevant_joins(self, attributes, expand_locales=False):
        """Get relevant joins to the attributes - list of joins that
        are required to be able to acces specified attributes. `attributes`
        is a list of three element tuples: (`schema`, `table`, `attribute`).
        """

        # Attribute: (schema, table, column)
        # Join: ((schema, table, column), (schema, table, column), alias)

        # self.logger.debug("getting relevant joins for %s attributes" % len(attributes))

        if not self.joins:
            self.logger.debug("no joins to be searched for")

        tables_to_join = set(self.tables_for_attributes(attributes,
                                                        expand_locales))
        joined_tables = set()
        fact_table = (self.schema, self.fact_name)
        joined_tables.add( fact_table )

        joins = []
        # self.logger.debug("tables to join: %s" % list(tables_to_join))

        while tables_to_join:
            table = tables_to_join.pop()
            # self.logger.debug("joining table %s" % (table, ))

            joined = False
            for order, join in enumerate(self.joins):
                master = (join.master.schema, join.master.table)
                detail = (join.detail.schema, join.alias or join.detail.table)
                # self.logger.debug("testing join: %s->%s" % (master,detail))

                if table == detail:
                    # self.logger.debug("detail matches")
                    # Preserve join order
                    # TODO: temporary way of ordering according to match
                    method_order = _join_method_order.get(join.method, 99)
                    joins.append( (method_order, order, join) )

                    if master not in joined_tables:
                        # self.logger.debug("adding master %s to be joined" % (master, ))
                        tables_to_join.add(master)

                    # self.logger.debug("joined detail %s" % (detail, ) )
                    joined_tables.add(detail)
                    joined = True
                    break

            if joins and not joined and table != fact_table:
                self.logger.warn("No table joined for %s" % (table, ))

        # self.logger.debug("%s tables joined (of %s joins)" % (len(joins), len(self.joins)) )

        # Sort joins according to original order specified in the model
        joins.sort()
        self.logger.debug("joined tables: %s" % ([join[2].detail.table for join in
                                                                joins], ) )

        # Retrieve actual joins from tuples. Remember? We preserved order.
        joins = [join[2] for join in joins]
        return joins


class DenormalizedMapper(Mapper):
    def __init__(self, cube, locale=None, schema=None,
                    fact_name=None, denormalized_view_prefix=None,
                    denormalized_view_schema=None,
                    **options):

        """Creates a mapper for a cube that has data stored in a denormalized
        view/table.

        Attributes:

        * `denormalized_view_prefix` – default prefix used for constructing
           view name from cube name
        * `fact_name` – fact name, if not specified then `cube.name` is used
        * `schema` – schema where the denormalized view is stored
        * `fact_schema` – database schema for the original fact table
        """

        super(DenormalizedMapper, self).__init__(cube, locale=locale,
                                        schema=schema, fact_name=fact_name)

        dview_prefix = denormalized_view_prefix or ""

        # FIXME: this hides original fact name, we do not want that

        self.fact_name = options.get("denormalized_view") or dview_prefix + \
                            self.cube.basename
        self.fact_schema = self.schema
        self.schema = self.schema or denormalized_view_schema

    def physical(self, attribute, locale=None):
        """Returns same name as localized logical reference.
        """

        locale = locale or self.locale
        try:
            if attribute.locales:
                locale = locale if locale in attribute.locales \
                                    else attribute.locales[0]
            else:
                locale = None
        except:
            locale = None

        column_name = self.logical(attribute, locale)
        reference = TableColumnReference(self.schema,
                                          self.fact_name,
                                          column_name,
                                          None, None, None, None)

        return reference

    def relevant_joins(self, attributes):
        """Returns an empty list. No joins are necessary for denormalized
        view.
        """

        self.logger.debug("getting relevant joins: not needed for denormalized table")

        return []


########NEW FILE########
__FILENAME__ = query
# -*- coding=utf -*-

from ...browser import Drilldown, Cell, PointCut, SetCut, RangeCut
from ...browser import SPLIT_DIMENSION_NAME
from ...model import Attribute
from ...errors import *
from ...expr import evaluate_expression
from ...logging import get_logger
from collections import namedtuple, OrderedDict
from .mapper import DEFAULT_KEY_FIELD, PhysicalAttribute
from .utils import condition_conjunction, order_column
import datetime
import re

try:
    import sqlalchemy
    import sqlalchemy.sql as sql

except ImportError:
    from cubes.common import MissingPackage
    sqlalchemy = sql = MissingPackage("sqlalchemy", "SQL aggregation browser")


__all__ = [
        "SnowflakeSchema",
        "QueryBuilder"
        ]


SnowflakeAttribute = namedtuple("SnowflakeAttribute", ["attribute", "join"])


"""Product of join_expression"""
JoinedProduct = namedtuple("JoinedProduct",
        ["expression", "tables"])


_SQL_EXPR_CONTEXT = {
    "sqlalchemy": sqlalchemy,
    "sql": sql,
    "func": sql.expression.func,
    "case": sql.expression.case,
    "text": sql.expression.text,
    "datetime": datetime,
    "re": re,
    "extract": sql.expression.extract,
    "and_": sql.expression.and_,
    "or_": sql.expression.or_
}

def table_str(key):
    """Make (`schema`, `table`) tuple printable."""
    table, schema = key
    return "%s.%s" % (str(schema), (table)) if schema else str(table)


MATCH_MASTER_RSHIP = 1
OUTER_DETAIL_RSHIP = 2

class SnowflakeTable(object):
    def __init__(self, schema, name, alias=None, table=None, join=None):
        self.schema = schema
        self.name = name
        self.table = table
        self.alias = alias
        self.join = join
        self.detail_keys = set()

    @property
    def key(self):
        return (self.schema, self.aliased_name)

    @property
    def aliased_name(self):
        return self.alias or self.name

    def __str__(self):
        return "%s.%s" % (self.key)

# TODO: merge this with mapper
class SnowflakeSchema(object):
    def __init__(self, cube, mapper, metadata, safe_labels):
        self.cube = cube
        self.mapper = mapper
        self.metadata = metadata
        self.safe_labels = safe_labels

        # Initialize the shema information: tables, column maps, ...
        self.schema = self.mapper.schema

        # Prepare physical fact table - fetch from metadata
        #
        self.fact_key = self.cube.key or DEFAULT_KEY_FIELD
        self.fact_name = self.mapper.fact_name

        try:
            self.fact_table = sqlalchemy.Table(self.fact_name,
                                               self.metadata,
                                               autoload=True,
                                               schema=self.schema)
        except sqlalchemy.exc.NoSuchTableError:
            in_schema = (" in schema '%s'" % self.schema) if self.schema else ""
            msg = "No such fact table '%s'%s." % (self.fact_name, in_schema)
            raise WorkspaceError(msg)

        try:
            self.fact_key_column = self.fact_table.c[self.fact_key].label(self.fact_key)
        except KeyError:
            try:
                self.fact_key_column = list(self.fact_table.columns)[0]
            except Exception as e:
                raise ModelError("Unable to get key column for fact "
                                 "table '%s' in cube '%s'. Reason: %s"
                                 % (self.fact_name, self.cube.name, str(e)))

        # Collect all tables and their aliases.
        #
        # table_aliases contains mapping between aliased table name and real
        # table name with alias:
        #
        #       (schema, aliased_name) --> (schema, real_name, alias)
        #

        # Mapping where keys are attributes and values are columns
        self.logical_to_column = {}
        # Mapping where keys are column labels and values are attributes
        self.column_to_logical = {}

        # Collect tables from joins

        self.tables = {}
        # Table -> relationship type
        # Prepare maps of attributes -> relationship type
        self.fact_relationships = {}
        self.aggregated_fact_relationships = {}

        self._collect_tables()
        self._analyse_table_relationships()

    def _collect_tables(self):
        """Collect tables in the schema. Analyses their relationship towards
        the fact table.

        Stored information contains:

        * attribute ownership by a table
        * relationship type of tables towards the fact table: master/match or
          detail (outer)

        The rule for deciding the table relationship is as follows:

        * if a table is connected to a fact or other master/detail table by
          master/detail then it will be considered master/detail
        * if a table is connected to an outer detail it is considered to be
          outer detail (in relationship to the fact), regardless of it's join
          type
        * if a table is connected through outer detail to any kind of table,
          then it will stay as detail

        Input: schema, fact name, fact table, joins

        Output: tables[table_key] = SonwflakeTable()

        """

        # Collect the fact table as the root master table
        #
        table = SnowflakeTable(self.schema, self.fact_name,
                               table=self.fact_table)
        self.tables[table.key] = table

        # Collect all the detail tables
        # 
        for join in self.mapper.joins:
            # just ask for the table

            sql_table = sqlalchemy.Table(join.detail.table,
                                         self.metadata,
                                         autoload=True,
                                         schema=join.detail.schema)

            if join.alias:
                sql_table = sql_table.alias(join.alias)

            table = SnowflakeTable(schema=join.detail.schema,
                                   name=join.detail.table,
                                   alias=join.alias,
                                   join=join,
                                   table=sql_table)

            self.tables[table.key] = table

        # Collect detail keys:
        # 
        # Every table object has a set of keys `detail_keys` which are
        # columns that are used to join detail tables.
        #
        for join in self.mapper.joins:
            key = (join.master.schema, join.master.table)
            try:
                master = self.tables[key]
            except KeyError:
                raise ModelError("Unknown table (or join alias) '%s'"
                                 % table_str(key))
            master.detail_keys.add(join.master.column)

    def _analyse_table_relationships(self):

        # Analyse relationships
        # ---------------------

        # Dictionary of raw tables and their joined products
        # table-to-master relationships:
        #     MASTER_MATCH_RSHIP: either joined as "match" or "master"
        #     OUTER_DETAIL_RSHIP: joined as "detail"
        relationships = {}

        # Anchor the fact table
        key = (self.schema, self.fact_name)
        relationships[key] = MATCH_MASTER_RSHIP
        self.tables[key].relationship = MATCH_MASTER_RSHIP

        # Collect all the tables first:
        for join in self.mapper.joins:
            # Add master table to the list
            table = (join.master.schema, join.master.table)
            if table not in relationships:
                self.fact_relationships[table] = None

            # Add (aliased) detail table to the rist
            table = (join.detail.schema, join.alias or join.detail.table)
            if table not in relationships:
                relationships[table] = None
            else:
                raise ModelError("Joining detail table %s twice" % (table, ))

        # Analyse the joins
        for join in reversed(self.mapper.joins):
            master_key = (join.master.schema, join.master.table)
            detail_key = (join.detail.schema, join.alias or join.detail.table)

            if relationships.get(detail_key):
                raise InternalError("Detail %s already classified" % detail_key)

            master_rs = relationships[master_key]

            if master_rs is None:
                raise InternalError("Joining to unclassified master. %s->%s "
                                    "Hint: check your joins, their order or "
                                    "mappings." % (table_str(master_key),
                                                   table_str(detail_key)))
            elif master_rs == MATCH_MASTER_RSHIP \
                    and join.method in ("match", "master"):
                relationship = MATCH_MASTER_RSHIP
            elif master_rs == OUTER_DETAIL_RSHIP \
                    or join.method == "detail":
                relationship = OUTER_DETAIL_RSHIP
            else:
                raise InternalError("Unknown relationship combination for "
                                    "%s(%s)->%s(%s)"
                                    % (table_str(master_key), master_rs,
                                       table_str(detail_key), join.method))

            relationships[detail_key] = relationship
            self.tables[detail_key].relationship = relationship


        # Prepare relationships of attributes
        #
        # TODO: make SnowflakeAttribute class
        attributes = self.cube.get_attributes(aggregated=False)
        tables = self.mapper.tables_for_attributes(attributes)
        tables = dict(zip(attributes, tables))
        mapping = {}

        for attribute in attributes:
            try:
                table_ref = tables[attribute]
            except KeyError:
                raise ModelError("Unknown table for attribute %s. "
                                 "Missing mapping?" % attribute)
            try:
                mapping[attribute] = relationships[table_ref]
            except KeyError:
                attr, table = table_ref
                if table:
                    message = "Missing join for table '%s'?" % table
                else:
                    message = "Missing mapping or join?"

                raise ModelError("Can not determine to-fact relationship for "
                                 "attribute '%s'. %s"
                                 % (attribute.ref(), message))
        self.fact_relationships = mapping

        attributes = self.cube.get_attributes(aggregated=True)
        tables = self.mapper.tables_for_attributes(attributes)
        tables = dict(zip(attributes, tables))
        mapping = {}
        for attribute in attributes:
            mapping[attribute] = relationships[tables[attribute]]
        self.aggregated_fact_relationships = mapping

    def _collect_detail_keys(self):
        """Assign to each table which keys from the table are used by another
        detail table as master keys."""


    def is_outer_detail(self, attribute, for_aggregation=False):
        """Returns `True` if the attribute belongs to an outer-detail table."""
        if for_aggregation:
            lookup = self.aggregated_fact_relationships
        else:
            lookup = self.fact_relationships

        try:
            return lookup[attribute] == OUTER_DETAIL_RSHIP
        except KeyError:
            # Retry as raw table (used by internally generated attributes)
            ref = self.mapper.physical(attribute)
            key = (ref.schema, ref.table)
            return self.tables[key].relationship
        except KeyError:
            raise InternalError("No fact relationship for attribute %s "
                                "(aggregate: %s)"
                                % (attribute.ref(), for_aggregation))

    def join_expression(self, attributes, include_fact=True, master_fact=None,
                        master_detail_keys=None):
        """Create partial expression on a fact table with `joins` that can be
        used as core for a SELECT statement. `join` is a list of joins
        returned from mapper (most probably by `Mapper.relevant_joins()`)

        Returns a tuple: (`expression`, `tables`) where `expression` is
        QLAlchemy expression object and `tables` is a list of `SnowflakeTable`
        objects used in the join.

        If `include_fact` is ``True`` (default) then fact table is considered
        as starting point. If it is ``False`` The first detail table is
        considered as starting point for joins. This might be useful when
        getting values of a dimension without cell restrictions.

        `master_fact` is used for building a composed aggregated expression.
        `master_detail_keys` is a dictionary of aliased keys from the master
        fact exposed to the details.

        **Requirement:** joins should be ordered from the "tentacles" towards
        the center of the star/snowflake schema.

        **Algorithm:**

        * FOR ALL JOINS:
          1. get a join (order does not matter)
          2. get master and detail TABLES (raw, not joined)
          3. prepare the join condition on columns from the tables
          4. find join PRODUCTS based on the table keys (schema, table)
          5. perform join on the master/detail PRODUCTS:
             * match: left inner join
             * master: left outer join
             * detail: right outer join – swap master and detail tables and
                       do the left outer join
          6. remove the detail PRODUCT
          7. replace the master PRODUCT with the new one

        * IF there is more than one join product left then some joins are
          missing
        * Result: join products should contain only one item which is the
          final product of the joins
        """

        joins = self.mapper.relevant_joins(attributes)

        # Dictionary of raw tables and their joined products
        joined_products = {}

        master_detail_keys = master_detail_keys or {}

        tables = []

        fact_key = (self.schema, self.fact_name)

        if include_fact:
            if master_fact is not None:
                fact = master_fact
            else:
                fact = self.fact_table

            joined_products[fact_key] = fact
            tables.append(self.tables[fact_key])

        # Collect all the tables first:
        for join in joins:
            if not join.detail.table or (join.detail.table == self.fact_name and not join.alias):
                raise MappingError("Detail table name should be present and "
                                   "should not be a fact table unless aliased.")

            # 1. MASTER
            # Add master table to the list. If fact table (or statement) was
            # explicitly specified, use it instead of the original fact table

            if master_fact is not None and (join.master.schema, join.master.table) == fact_key:
                table = master_fact
            else:
                table = self.table(join.master.schema, join.master.table)
            joined_products[(join.master.schema, join.master.table)] = table

            # 2. DETAIL
            # Add (aliased) detail table to the rist. Add the detail to the
            # list of joined tables – will be used to determine "outlets" for
            # keys of outer detail joins

            table = self.table(join.detail.schema, join.alias or join.detail.table)
            key = (join.detail.schema, join.alias or join.detail.table)
            joined_products[key] = table
            tables.append(self.tables[key])

        # Perform the joins
        # =================
        #
        # 1. find the column
        # 2. construct the condition
        # 3. use the appropriate SQL JOIN
        # 
        for join in joins:
            # Prepare the table keys:
            # Key is a tuple of (schema, table) and is used to get a joined
            # product object
            master = join.master
            master_key = (master.schema, master.table)
            detail = join.detail
            detail_key = (detail.schema, join.alias or detail.table)

            # We need plain tables to get columns for prepare the join
            # condition
            # TODO: this is unreadable
            if master_fact is not None and (join.master.schema, join.master.table) == fact_key:
                key = (join.master.schema, join.master.table, join.master.column)
                try:
                   master_label = master_detail_keys[key]
                except KeyError:
                    raise InternalError("Missing fact column %s (has: %s)"
                                        % (key, master_detail_keys.keys()))
                master_column = master_fact.c[master_label]
            else:
                master_table = self.table(master.schema, master.table)

                try:
                    master_column = master_table.c[master.column]
                except KeyError:
                    raise ModelError('Unable to find master key (schema %s) '
                                     '"%s"."%s" ' % join.master[0:3])

            detail_table = self.table(join.detail.schema, join.alias or join.detail.table)
            try:
                detail_column = detail_table.c[detail.column]
            except KeyError:
                raise MappingError('Unable to find detail key (schema %s) "%s"."%s" ' \
                                    % join.detail[0:3])

            # The join condition:
            onclause = master_column == detail_column

            # Get the joined products – might be plain tables or already
            # joined tables
            try:
                master_table = joined_products[master_key]
            except KeyError:
                raise ModelError("Unknown master %s. Missing join or "
                                 "wrong join order?" % (master_key, ))
            detail_table = joined_products[detail_key]


            # Determine the join type based on the join method. If the method
            # is "detail" then we need to swap the order of the tables
            # (products), because SQLAlchemy provides inteface only for
            # left-outer join.
            if join.method == "match":
                is_outer = False
            elif join.method == "master":
                is_outer = True
            elif join.method == "detail":
                # Swap the master and detail tables to perform RIGHT OUTER JOIN
                master_table, detail_table = (detail_table, master_table)
                is_outer = True
            else:
                raise ModelError("Unknown join method '%s'" % join.method)

            product = sql.expression.join(master_table,
                                             detail_table,
                                             onclause=onclause,
                                             isouter=is_outer)

            del joined_products[detail_key]
            joined_products[master_key] = product

        if not joined_products:
            # This should not happen
            raise InternalError("No joined products left.")

        if len(joined_products) > 1:
            raise ModelError("Some tables are not joined: %s"
                             % (joined_products.keys(), ))

        # Return the remaining joined product
        result = joined_products.values()[0]

        return JoinedProduct(result, tables)

    def column(self, attribute, locale=None):
        """Return a column object for attribute.

        `locale` is explicit locale to be used. If not specified, then the
        current locale is used for localizable attributes.
        """

        logical = self.mapper.logical(attribute, locale)
        if logical in self.logical_to_column:
            return self.logical_to_column[logical]

        ref = self.mapper.physical(attribute, locale)
        table = self.table(ref.schema, ref.table)

        try:
            column = table.c[ref.column]
        except:
            avail = [str(c) for c in table.columns]
            raise BrowserError("Unknown column '%s' in table '%s' avail: %s"
                               % (ref.column, ref.table, avail))

        # Extract part of the date
        if ref.extract:
            column = sql.expression.extract(ref.extract, column)
        if ref.func:
            column = getattr(sql.expression.func, ref.func)(column)
        if ref.expr:
            # Provide columns for attributes (according to current state of
            # the query)
            context = dict(_SQL_EXPR_CONTEXT)
            getter = _TableGetter(self)
            context["table"] = getter
            getter = _AttributeGetter(self, attribute.dimension)
            context["dim"] = getter
            getter = _AttributeGetter(self, self.cube)
            context["fact"] = getter
            context["column"] = column


            column = evaluate_expression(ref.expr, context, 'expr', sql.expression.ColumnElement)

        if self.safe_labels:
            label = "a%d" % self.label_counter
            self.label_counter += 1
        else:
            label = logical

        if isinstance(column, basestring):
            raise ValueError("Cannot resolve %s to a column object: %r" % (attribute, column))

        column = column.label(label)

        self.logical_to_column[logical] = column
        self.column_to_logical[label] = logical

        return column

    def columns(self, attributes, expand_locales=False):
        """Returns list of columns.If `expand_locales` is True, then one
        column per attribute locale is added."""

        if expand_locales:
            columns = []
            for attr in attributes:
                if attr.is_localizable():
                    columns += [self.column(attr, locale) for locale in attr.locales]
                else: # if not attr.locales
                    columns.append(self.column(attr))
        else:
            columns = [self.column(attr) for attr in attributes]

        return columns

    def logical_labels(self, columns):
        """Returns list of logical attribute labels from list of columns
        or column labels.

        This method and additional internal references were added because some
        database dialects, such as Exasol, can not handle dots in column
        names, even when quoted.
        """

        # Should not this belong to the snowflake
        attributes = []

        for column in columns:
            attributes.append(self.column_to_logical.get(column.name,
                                                         column.name))

        return attributes

    def table(self, schema, table_name):
        """Return a SQLAlchemy Table instance. If table was already accessed,
        then existing table is returned. Otherwise new instance is created.

        If `schema` is ``None`` then browser's default schema is used.
        """

        key = (schema or self.mapper.schema, table_name)
        # Get real table reference
        try:
            return self.tables[key].table
        except KeyError:
            raise ModelError("Table with reference %s not found. "
                             "Missing join in cube '%s'?"
                             % (key, self.cube.name) )


class _StatementConfiguration(object):
    def __init__(self):
        self.attributes = []
        self.cuts = []
        self.cut_attributes = []
        self.other_attributes = []

        self.split_attributes = []
        self.split_cuts = []

        self.ptd_attributes = []

    @property
    def all_attributes(self):
        """All attributes that should be considered for a statement
        composition.  Mostly used to get the relevant joins."""

        return set(self.attributes) | set(self.cut_attributes) \
                | set(self.split_attributes) | set(self.other_attributes)

    def merge(self, other):
        self.attributes += other.attributes
        self.cuts += other.cuts
        self.cut_attributes += other.cut_attributes

        self.split_attributes += other.split_attributes
        self.split_cuts += other.split_cuts

        self.other_attributes += other.other_attributes
        self.ptd_attributes += other.ptd_attributes

    def is_empty(self):
        return not (bool(self.attributes) \
                    or bool(self.cut_attributes) \
                    or bool(self.other_attributes) \
                    or bool(self.split_attributes))

class QueryBuilder(object):
    def __init__(self, browser):
        """Creates a SQL query statement builder object – a controller-like
        object that incrementally constructs the statement.

        Result attributes:

        * `statement` – SQL query statement
        * `labels` – logical labels for the statement selection
        """

        self.browser = browser

        # Inherit
        # FIXME: really?
        self.logger = browser.logger
        self.mapper = browser.mapper
        self.cube = browser.cube

        self.snowflake = SnowflakeSchema(self.cube, self.mapper,
                                         self.browser.metadata,
                                         safe_labels=browser.safe_labels)

        self.master_fact = None

        # Intermediate results
        self.drilldown = None
        self.split = None

        # Output:
        self.statement = None
        self.labels = []

        # Semi-additive dimension
        # TODO: move this to model (this is ported from the original
        # SnapshotBrowser)

        # TODO: remove this later
        if "semiadditive" in self.cube.info:
            raise NotImplementedError("'semiadditive' in 'info' is not "
                                      "supported any more")

        for dim in self.cube.dimensions:
            if dim.nonadditive:
                raise NotImplementedError("Non-additive behavior for "
                                          "dimensions is not yet implemented."
                                          "(cube '%s', dimension '%s')" %
                                          (self.cube.name, dim.name))

    def aggregation_statement(self, cell, drilldown=None, aggregates=None,
                              split=None, attributes=None, summary_only=False):
        """Builds a statement to aggregate the `cell`.

        * `cell` – `Cell` to aggregate
        * `drilldown` – a `Drilldown` object
        * `aggregates` – list of aggregates to consider
        * `split` – split cell for split condition
        * `summary_only` – do not perform GROUP BY for the drilldown. The
        * drilldown is used only for choosing tables to join and affects outer
          detail joins in the result

        Algorithm description:

        All the tables have one of the two relationship to the fact:
        *master/match* or *detail*. Every table connected to a table that has
        "detail" relationship is considered also in the "detail" relationship
        towards the fact. Therefore we have two join zones: all master or
        detail tables from the core, directly connected to the fact table and
        rest of the table connected to the core through outer detail
        relationship.

        Depending on the query it is decided whether we are fine with just
        joining everything together into single join or we need to separate
        the fact master core from the outer details::

                        +------+           +-----+
                        | fact |--(match)--| dim +
                        +------+           +-----+
            Master Fact    |
            ===============|========================
            Outer Details  |               +-----+
                           +------(detail)-| dim |
                                           +-----+

        The outer details part is RIGHT OUTER JOINed to the fact. Since there
        are no tables any more, the original table keys for joins to the outer
        details were exposed and specially labeled as `__masterkeyXX` where XX
        is a sequence number of the key. The `join_expression` JOIN
        constructing method receives the map of the keys and replaces the
        original tables with connections to the columns already selected in
        the master fact.

        .. note::

            **Limitation:** we can not have a Cut (condition) where keys (path
            elements) are from both join zones. Whole cut should be within one
            zone: either the master fact or outer details.
        """

        if not aggregates:
            raise ArgumentError("List of aggregates sohuld not be empty")

        drilldown = drilldown or Drilldown()

        # Configuraion of statement parts
        master = _StatementConfiguration()
        detail = _StatementConfiguration()

        self.logger.debug("prepare aggregation statement. cell: '%s' "
                          "drilldown: '%s' summary only: %s" %
                          (",".join([str(cut) for cut in cell.cuts]),
                          drilldown, summary_only))

        # Analyse and Prepare
        # -------------------
        # Get the cell attributes and find whether we have some outer details
        #
        # Cut
        # ~~~

        mcuts, mattrs, dcuts, dattrs = self._split_cell_by_relationship(cell)
        master.cuts += mcuts
        master.cut_attributes += mattrs
        detail.cuts += dcuts
        detail.cut_attributes += dattrs

        # Split
        # ~~~~~
        # Same as Cut, just different target

        mcuts, mattrs, dcuts, dattrs = self._split_cell_by_relationship(split)
        master.split_cuts += mcuts
        master.split_attributes += mattrs
        detail.split_cuts += dcuts
        detail.split_attributes += dattrs

        # Drilldown
        # ~~~~~~~~~

        drilldown_attributes = drilldown.all_attributes()
        master.attributes, detail.attributes = \
                self._split_attributes_by_relationship(drilldown_attributes)

        # Period-to-date
        #
        # One thing we have to do later is to generate the PTD condition
        # (either for master or for detail) and assign it to the appropriate
        # list of conditions

        ptd_attributes = self._ptd_attributes(cell, drilldown)
        ptd_master, ptd_detail = self._split_attributes_by_relationship(ptd_attributes)
        if ptd_master and ptd_detail:
            raise InternalError("PTD attributes are spreading from master "
                                "to outer detail. This is not supported.")
        elif ptd_master:
            master.ptd_attributes = ptd_master
        elif ptd_detail:
            detail.ptd_attributes = ptd_detail

        # TODO: PTD workaround #2
        # We need to know which attributes have to be included for JOINs,
        # however we can know this only when "condition" in mapping is
        # evaluated, which can be evaluated only after joins and when the
        # master-fact is ready.
        required = self.cube.browser_options.get("ptd_master_required", [])

        if required:
            required = self.cube.get_attributes(required)
            master.ptd_attributes += required

        # Semi-additive attribute
        semiadditives = self.semiadditive_attributes(aggregates, drilldown)
        sa_master, sa_detail = self._split_attributes_by_relationship(semiadditives)
        master.other_attributes += sa_master
        detail.other_attributes += sa_detail

        # Pick the method:
        #
        # M - master, D - detail
        # C - condition, A - selection attributes (drilldown)
        #
        #    MA MC DA DC | method
        #    ============|=======
        #  0 -- -- -- -- | simple
        #  1 xx -- -- -- | simple
        #  2 -- xx -- -- | simple
        #  3 xx xx -- -- | simple
        #  4 -- -- xx -- | simple
        #  5 xx -- xx -- | simple
        #  6 -- xx xx -- | composed
        #  7 xx xx xx -- | composed
        #  8 -- -- -- xx | simple
        #  9 xx -- -- xx | simple
        # 10 -- -- xx xx | simple
        # 11 xx -- xx xx | simple
        # 12 -- xx -- xx | composed
        # 13 xx xx -- xx | composed
        # 14 -- xx xx xx | composed
        # 15 xx xx xx xx | composed
        # 

        # The master cut is in conflict with detail drilldown or detail cut 
        if master.cut_attributes and (detail.attributes or
                                        detail.cut_attributes):
            simple_method = False
        else:
            simple_method = True
            master.merge(detail)

        coalesce_measures = not detail.is_empty()

        master_conditions = self.conditions_for_cuts(master.cuts)

        if simple_method:
            self.logger.debug("statement: simple")

            # Drilldown – Group-by
            # --------------------
            #
            # SELECT – Prepare the master selection
            #     * master drilldown items

            selection = [self.column(a) for a in set(master.attributes)]
            group_by = selection[:]

            # SPLIT
            # -----
            if split:
                master_split = self._cell_split_column(master.split_cuts)
                group_by.append(master_split)
                selection.append(master_split)

            # WHERE
            # -----
            conditions = master_conditions
            ptd_attributes = master.ptd_attributes

            # JOIN
            # ----
            attributes = set(aggregates) \
                            | master.all_attributes \
                            | set(ptd_attributes)
            join = self.snowflake.join_expression(attributes)
            join_expression = join.expression

        else:
            self.logger.debug("statement: composed")

            # 1. MASTER FACT
            # ==============

            join = self.snowflake.join_expression(master.all_attributes)
            join_expression = join.expression

            # Store a map of joined columns for later
            # The map is: (schema, table, column) -> column

            # Expose fact master detail key outlets:
            master_detail_keys = {}
            master_detail_selection = []
            counter = 0
            for table in join.tables:
                for key in table.detail_keys:
                    column_key = (table.schema, table.aliased_name, key)
                    label = "__masterkey%d" % counter
                    master_detail_keys[column_key] = label

                    column = table.table.c[key].label(label)
                    master_detail_selection.append(column)
                    counter += 1

            # SELECT – Prepare the master selection
            #     * drilldown items
            #     * measures
            #     * aliased keys for outer detail joins

            # Note: Master selection is carried as first (we need to retrieve
            # it later by index)
            master_selection = [self.column(a) for a in set(master.attributes)]

            measures = self.measures_for_aggregates(aggregates)
            measure_selection = [self.column(m) for m in measures]

            selection = master_selection \
                            + measure_selection \
                            + master_detail_selection

            # SPLIT
            # -----
            if master.split_cuts:
                master_split = self._cell_split_column(master.split_cuts,
                                                       "__master_split")
                group_by.append(master_split)
                selection.append(master_split)
            else:
                master_split = None

            # Add the fact key – to properely handle COUNT()
            selection.append(self.snowflake.fact_key_column)

            # WHERE Condition
            # ---------------
            condition = condition_conjunction(master_conditions)

            # Add the PTD
            if master.ptd_attributes:
                ptd_condition = self._ptd_condition(master.ptd_attributes)
                condition = condition_conjunction([condition, ptd_condition])
                # TODO: PTD workaround #3:
                # Add the PTD attributes to the selection,so the detail part
                # of the join will be able to find them in the master
                cols = [self.column(a) for a in master.ptd_attributes]
                selection += cols

            # Prepare the master_fact statement:
            statement = sql.expression.select(selection,
                                              from_obj=join_expression,
                                              use_labels=True,
                                              whereclause=condition)

            # From now-on the self.column() method will return columns from
            # master_fact if applicable.
            self.master_fact = statement.alias("__master_fact")

            # Add drilldown – Group-by
            # ------------------------
            #

            # SELECT – Prepare the detail selection
            #     * master drilldown items (inherit)
            #     * detail drilldown items

            master_cols = list(self.master_fact.columns)
            master_selection = master_cols[0:len(master.attributes)]

            detail_selection = [self.column(a) for a in set(detail.attributes)]

            selection = master_selection + detail_selection
            group_by = selection[:]

            # SPLIT
            # -----
            if detail.split_cuts:
                if master_split:
                    # Merge the detail and master part of the split "dimension"
                    master_split = self.master_fact.c["__master_split"]
                    detail_split = self._cell_split_column(detail.split_cuts,
                                        "__detail_split")
                    split_condition = (master_split and detail_split)
                    detail_split = sql.expression.case([(split_condition, True)],
                                                       else_=False)
                    detail_split.label(SPLIT_DIMENSION_NAME)
                else:
                    # We have only detail split, no need to merge the
                    # condition
                    detail_split = self._cell_split_column(detail.split_cuts)

                selection.append(detail_split)
                group_by.append(detail_split)


            # WHERE
            # -----
            conditions = self.conditions_for_cuts(detail.cuts)
            ptd_attributes = detail.ptd_attributes

            # JOIN
            # ----
            # Replace the master-relationship tables with single master fact
            # Provide mapping between original table columns to the master
            # fact selection (with labelled columns)
            join = self.snowflake.join_expression(detail.all_attributes,
                                                  master_fact=self.master_fact,
                                                  master_detail_keys=master_detail_keys)

            join_expression = join.expression

        # The Final Statement
        # ===================
        #

        # WHERE
        # -----
        if ptd_attributes:
            ptd_condition = self._ptd_condition(ptd_attributes)
            self.logger.debug("adding PTD condition: %s" % str(ptd_condition))
            conditions.append(ptd_condition)

        condition = condition_conjunction(conditions)
        group_by = group_by if not summary_only else None

        # Include the semi-additive dimension, if required
        #
        if semiadditives:
            self.logger.debug("preparing semiadditive subquery for "
                              "attributes: %s"
                              % [a.name for a in semiadditives])

            join_expression = self._semiadditive_subquery(semiadditives,
                                                     selection,
                                                     from_obj=join_expression,
                                                     condition=condition,
                                                     group_by=group_by)

        aggregate_selection = self.builtin_aggregate_expressions(aggregates,
                                                       coalesce_measures=coalesce_measures)

        if summary_only:
            # Don't include the group-by part (see issue #157 for more
            # information)
            selection = aggregate_selection
        else:
            selection += aggregate_selection

        # condition = None
        statement = sql.expression.select(selection,
                                          from_obj=join_expression,
                                          use_labels=True,
                                          whereclause=condition,
                                          group_by=group_by)

        self.statement = statement
        self.labels = self.snowflake.logical_labels(selection)

        # Used in order
        self.drilldown = drilldown
        self.split = split

        return self.statement

    def _split_attributes_by_relationship(self, attributes):
        """Returns a tuple (`master`, `detail`) where `master` is a list of
        attributes that have master/match relationship towards the fact and
        `detail` is a list of attributes with outer detail relationship
        towards the fact."""

        if not attributes:
            return ([],[])

        master = []
        detail = []
        for attribute in attributes:
            if self.snowflake.is_outer_detail(attribute):
                detail.append(attribute)
            else:
                master.append(attribute)

        return (master, detail)

    def _split_cell_by_relationship(self, cell):
        """Returns a tuple of _StatementConfiguration objects (`master`,
        `detail`)"""

        if not cell:
            return ([], [], [], [])

        master_cuts = []
        master_cut_attributes = []
        detail_cuts = []
        detail_cut_attributes = []

        for cut, attributes in self.attributes_for_cell_cuts(cell):
            is_outer_detail = [self.snowflake.is_outer_detail(a) for a in attributes]

            if all(is_outer_detail):
                detail_cut_attributes += attributes
                detail_cuts.append(cut)
            elif any(is_outer_detail):
                raise InternalError("Cut %s is spreading from master to "
                                    "outer detail is not supported."
                                    % str(cut))
            else:
                master_cut_attributes += attributes
                master_cuts.append(cut)

        return (master_cuts, master_cut_attributes,
                detail_cuts, detail_cut_attributes)

    def _cell_split_column(self, cuts, label=None):
        """Create a column for a cell split from list of `cust`."""

        conditions = self.conditions_for_cuts(cuts)
        condition = condition_conjunction(conditions)
        split_column = sql.expression.case([(condition, True)],
                                           else_=False)

        label = label or SPLIT_DIMENSION_NAME

        return split_column.label(label)

    def semiadditive_attributes(self, aggregates, drilldown):
        """Returns an attribute from a semi-additive dimension, if defined for
        the cube. Cubes allows one semi-additive dimension. """

        nonadds = set(self.cube.nonadditive_type(agg) for agg in aggregates)
        # If there is no nonadditive aggregate, we skip
        if not any(nonaddtype for nonaddtype in nonadds):
            return None

        if None in nonadds:
            nonadds.remove(None)

        if "time" not in nonadds:
            raise NotImplementedError("Nonadditive aggregates for other than "
                                      "time dimension are not supported.")

        # Here we expect to have time-only nonadditive
        # TODO: What to do if we have more?

        # Find first time drill-down, if any
        items = [item for item in drilldown \
                       if item.dimension.role == "time"]

        attributes = []
        for item in drilldown:
            if item.dimension.role != "time":
                continue
            attribute = Attribute("__key__", dimension=item.dimension)
            attributes.append(attribute)

        if not attributes:
            time_dims = [ d for d in self.cube.dimensions if d.role == "time" ]
            if not time_dims:
                raise BrowserError("Cannot locate a time dimension to apply for semiadditive aggregates: %r" % nonadds)
            attribute = Attribute("__key__", dimension=time_dims[0])
            attributes.append(attribute)

        return attributes

    def _semiadditive_subquery(self, attributes, selection,
                               from_obj, condition, group_by):
        """Prepare the semi-additive subquery"""
        sub_selection = selection[:]

        semiadd_selection = []
        for attr in attributes:
            col = self.column(attr)
            # Only one function is supported for now: max()
            func = sql.expression.func.max
            col = func(col)
            semiadd_selection.append(col)

        sub_selection += semiadd_selection

        # This has to be the same as the final SELECT, except the subquery
        # selection
        sub_statement = sql.expression.select(sub_selection,
                                              from_obj=from_obj,
                                              use_labels=True,
                                              whereclause=condition,
                                              group_by=group_by)

        sub_statement = sub_statement.alias("__semiadditive_subquery")

        # Construct the subquery JOIN condition
        # Skipt the last subquery selection which we have created just
        # recently
        join_conditions = []

        for left, right in zip(selection, sub_statement.columns):
            join_conditions.append(left == right)

        remainder = list(sub_statement.columns)[len(selection):]
        for attr, right in zip(attributes, remainder):
            left = self.column(attr)
            join_conditions.append(left == right)

        join_condition = condition_conjunction(join_conditions)
        join_expression = from_obj.join(sub_statement, join_condition)

        return join_expression

    def denormalized_statement(self, cell=None, attributes=None,
                               expand_locales=False, include_fact_key=True):
        """Builds a statement for denormalized view. `whereclause` is same as
        SQLAlchemy `whereclause` for `sqlalchemy.sql.expression.select()`.
        `attributes` is list of logical references to attributes to be
        selected. If it is ``None`` then all attributes are used.
        `condition_attributes` contains list of attributes that are not going
        to be selected, but are required for WHERE condition.

        Set `expand_locales` to ``True`` to expand all localized attributes.
        """

        if attributes is None:
            attributes = self.cube.all_attributes

        join_attributes = set(attributes) | self.attributes_for_cell(cell)

        join_product = self.snowflake.join_expression(join_attributes)
        join_expression = join_product.expression

        columns = self.snowflake.columns(attributes, expand_locales=expand_locales)

        if include_fact_key:
            columns.insert(0, self.snowflake.fact_key_column)

        if cell is not None:
            condition = self.condition_for_cell(cell)
        else:
            condition = None

        statement = sql.expression.select(columns,
                                          from_obj=join_expression,
                                          use_labels=True,
                                          whereclause=condition)

        self.statement = statement
        self.labels = self.snowflake.logical_labels(statement.columns)

        return statement

    def members_statement(self, cell, attributes=None):
        """Prepares dimension members statement."""
        self.denormalized_statement(cell, attributes, include_fact_key=False)
        group_by = self.snowflake.columns(attributes)
        self.statement = self.statement.group_by(*group_by)
        return self.statement

    def fact(self, id_):
        """Selects only fact with given id"""
        condition = self.snowflake.fact_key_column == id_
        return self.append_condition(condition)

    def append_condition(self, condition):
        """Appends `condition` to the generated statement."""
        self.statement = self.statement.where(condition)
        return self.statement

    def measures_for_aggregates(self, aggregates):
        """Returns a list of measures for `aggregates`. This method is used in
        constructing the master fact."""

        measures = []

        aggregates = [agg for agg in aggregates if agg.function]

        for aggregate in aggregates:
            function_name = aggregate.function.lower()
            function = self.browser.builtin_function(function_name, aggregate)

            if not function:
                continue

            names = function.required_measures(aggregate)
            if names:
                measures += self.cube.get_attributes(names)

        return measures

    def builtin_aggregate_expressions(self, aggregates,
                                      coalesce_measures=False):
        """Returns list of expressions for aggregates from `aggregates` that
        are computed using the SQL statement.
        """

        expressions = []
        for agg in aggregates:
            exp = self.aggregate_expression(agg, coalesce_measures)
            if exp is not None:
                expressions.append(exp)

        return expressions

    def aggregate_expression(self, aggregate, coalesce_measure=False):
        """Returns an expression that performs the aggregation of measure
        `aggregate`. The result's label is the aggregate's name.  `aggregate`
        has to be `MeasureAggregate` instance.

        If aggregate function is post-aggregation calculation, then `None` is
        returned.

        Aggregation function names are case in-sensitive.

        If `coalesce_measure` is `True` then selected measure column is wrapped
        in ``COALESCE(column, 0)``.
        """
        # TODO: support aggregate.expression

        if aggregate.expression:
            raise NotImplementedError("Expressions are not yet implemented")

        # If there is no function specified, we consider the aggregate to be
        # computed in the mapping
        if not aggregate.function:
            # TODO: this should be depreciated in favor of aggreate.expression
            # TODO: Following expression should be raised instead:
            # raise ModelError("Aggregate '%s' has no function specified"
            #                 % str(aggregate))
            column = self.column(aggregate)
            return column

        function_name = aggregate.function.lower()
        function = self.browser.builtin_function(function_name, aggregate)

        if not function:
            return None

        expression = function(aggregate, self, coalesce_measure)

        return expression

    def attributes_for_cell(self, cell):
        """Returns a set of attributes included in the cell."""
        if not cell:
            return set()

        attributes = set()
        for cut, cut_attrs in self.attributes_for_cell_cuts(cell):
            attributes |= set(cut_attrs)
        return attributes

    def attributes_for_cell_cuts(self, cell):
        """Returns a list of tuples (`cut`, `attributes`) where `attributes`
        is list of attributes involved in the `cut`."""

        # Note: this method belongs here, not to the Cell class, as we might
        # discover that some other attributes might be required for the cell
        # (in the future...)

        result = []

        for cut in cell.cuts:
            depth = cut.level_depth()
            if depth:
                dim = self.cube.dimension(cut.dimension)
                hier = dim.hierarchy(cut.hierarchy)
                keys = [level.key for level in hier[0:depth]]
                result.append((cut, keys))

        return result

    def condition_for_cell(self, cell):
        """Returns a SQL condition for the `cell`."""
        conditions = self.conditions_for_cuts(cell.cuts)
        condition = condition_conjunction(conditions)
        return condition

    def conditions_for_cuts(self, cuts):
        """Constructs conditions for all cuts in the `cell`. Returns a list of
        SQL conditional expressions.
        """

        conditions = []

        for cut in cuts:
            dim = self.cube.dimension(cut.dimension)

            if isinstance(cut, PointCut):
                path = cut.path
                condition = self.condition_for_point(dim, path, cut.hierarchy,
                                                     cut.invert)

            elif isinstance(cut, SetCut):
                set_conds = []

                for path in cut.paths:
                    condition = self.condition_for_point(dim, path,
                                                         cut.hierarchy,
                                                         invert=False)
                    set_conds.append(condition)

                condition = sql.expression.or_(*set_conds)

                if cut.invert:
                    condition = sql.expression.not_(condition)

            elif isinstance(cut, RangeCut):
                condition = self.range_condition(cut.dimension,
                                                 cut.hierarchy,
                                                 cut.from_path,
                                                 cut.to_path, cut.invert)

            else:
                raise ArgumentError("Unknown cut type %s" % type(cut))

            conditions.append(condition)

        return conditions

    def condition_for_point(self, dim, path, hierarchy=None, invert=False):
        """Returns a `Condition` tuple (`attributes`, `conditions`,
        `group_by`) dimension `dim` point at `path`. It is a compound
        condition - one equality condition for each path element in form:
        ``level[i].key = path[i]``"""

        conditions = []

        levels = dim.hierarchy(hierarchy).levels_for_path(path)

        if len(path) > len(levels):
            raise ArgumentError("Path has more items (%d: %s) than there are levels (%d) "
                                "in dimension %s" % (len(path), path, len(levels), dim.name))

        for level, value in zip(levels, path):

            # Prepare condition: dimension.level_key = path_value
            column = self.column(level.key)
            conditions.append(column == value)

        condition = sql.expression.and_(*conditions)

        if invert:
            condition = sql.expression.not_(condition)

        return condition

    def range_condition(self, dim, hierarchy, from_path, to_path, invert=False):
        """Return a condition for a hierarchical range (`from_path`,
        `to_path`). Return value is a `Condition` tuple."""

        dim = self.cube.dimension(dim)

        lower = self._boundary_condition(dim, hierarchy, from_path, 0)
        upper = self._boundary_condition(dim, hierarchy, to_path, 1)

        conditions = []
        if lower is not None:
            conditions.append(lower)
        if upper is not None:
            conditions.append(upper)

        condition = condition_conjunction(conditions)

        if invert:
            condition = sql.expression.not_(condition)

        return condition

    def _boundary_condition(self, dim, hierarchy, path, bound, first=True):
        """Return a `Condition` tuple for a boundary condition. If `bound` is
        1 then path is considered to be upper bound (operators < and <= are
        used), otherwise path is considered as lower bound (operators > and >=
        are used )"""

        if not path:
            return None

        last = self._boundary_condition(dim, hierarchy,
                                        path[:-1],
                                        bound,
                                        first=False)

        levels = dim.hierarchy(hierarchy).levels_for_path(path)

        if len(path) > len(levels):
            raise ArgumentError("Path has more items (%d: %s) than there are levels (%d) "
                                "in dimension %s" % (len(path), path, len(levels), dim.name))

        conditions = []

        for level, value in zip(levels[:-1], path[:-1]):
            column = self.column(level.key)
            conditions.append(column == value)

        # Select required operator according to bound
        # 0 - lower bound
        # 1 - upper bound
        if bound == 1:
            # 1 - upper bound (that is <= and < operator)
            operator = sql.operators.le if first else sql.operators.lt
        else:
            # else - lower bound (that is >= and > operator)
            operator = sql.operators.ge if first else sql.operators.gt

        column = self.column(levels[-1].key)
        conditions.append(operator(column, path[-1]))
        condition = condition_conjunction(conditions)

        if last is not None:
            condition = sql.expression.or_(condition, last)

        return condition

    def _ptd_attributes(self, cell, drilldown):
        """Return attributes that are used for the PTD condition. Output of
        this function is used for master/detail fact composition and for the
        `_ptd_condition()`"""
        # Include every level only once
        levels = set()

        # For the cell:
        if cell:
            levels |= set(item[2] for item in cell.deepest_levels())

        # For drilldown:
        if drilldown:
            levels |= set(item[2] for item in drilldown.deepest_levels())

        attributes = []
        for level in levels:
            ref = self.mapper.physical(level.key)
            if ref.condition:
                attributes.append(level.key)

        return attributes

    def _ptd_condition(self, ptd_attributes):
        """Returns "periods to date" condition for `ptd_attributes` (which
        should be a result of `_ptd_attributes()`)"""

        # Collect the conditions
        #
        # Conditions are currently specified in the mappings as "condtition"
        # Collect relevant columns – those with conditions

        # Construct the conditions from the physical attribute expression
        conditions = []

        for attribute in ptd_attributes:
            # FIXME: this is a hack

            ref = self.mapper.physical(attribute)
            if not ref.condition:
                continue

            column = self.column(attribute)

            # Provide columns for attributes (according to current state of
            # the query)
            context = dict(_SQL_EXPR_CONTEXT)
            getter = _TableGetter(self)
            context["table"] = getter
            getter = _AttributeGetter(self, attribute.dimension)
            context["dim"] = getter
            getter = _AttributeGetter(self, self.cube)
            context["fact"] = getter
            context["column"] = column

            condition = evaluate_expression(ref.condition,
                                            context,
                                            'condition',
                                            sql.expression.ColumnElement)

            conditions.append(condition)

        # TODO: What about invert?
        return condition_conjunction(conditions)

    def fact_key_column(self):
        """Returns a column that represents the fact key."""
        # TODO: this is used only in FactCountFunction, suggestion for better
        # solution is in the comments there.
        if self.master_fact is not None:
            return self.master_fact.c[self.snowflake.fact_key]
        else:
            return self.snowflake.fact_key_column

    def column(self, attribute, locale=None):
        """Returns either a physical column for the attribute or a reference to
        a column from the master fact if it exists."""

        if self.master_fact is not None:
            ref = self.mapper.physical(attribute, locale)
            self.logger.debug("column %s (%s) from master fact" % (attribute.ref(), ref))
            try:
                return self.master_fact.c[ref.column]
            except KeyError:
                self.logger.debug("retry column %s from tables" % (attribute.ref(), ))
                return self.snowflake.column(attribute, locale)
        else:
            self.logger.debug("column %s from tables" % (attribute.ref(), ))
            return self.snowflake.column(attribute, locale)

    def paginate(self, page, page_size):
        """Returns paginated statement if page is provided, otherwise returns
        the same statement."""

        if page is not None and page_size is not None:
            self.statement = self.statement.offset(page * page_size).limit(page_size)

        return self.statement

    def order(self, order):
        """Returns a SQL statement which is ordered according to the `order`. If
        the statement contains attributes that have natural order specified, then
        the natural order is used, if not overriden in the `order`.

        `order` sohuld be prepared using
        :meth:`AggregationBrowser.prepare_order`.

        `dimension_levels` is list of considered dimension levels in form of
        tuples (`dimension`, `hierarchy`, `levels`). For each level it's sort
        key is used.
        """

        # Each attribute mentioned in the order should be present in the selection
        # or as some column from joined table. Here we get the list of already
        # selected columns and derived aggregates

        selection = OrderedDict()

        # Get logical attributes from column labels (see logical_labels method
        # description for more information why this step is necessary)
        for column, ref in zip(self.statement.columns, self.labels):
            selection[ref] = column

        # Make sure that the `order` is a list of of tuples (`attribute`,
        # `order`). If element of the `order` list is a string, then it is
        # converted to (`string`, ``None``).

        order = order or []

        drilldown = self.drilldown or []

        for dditem in drilldown:
            dim, hier, levels = dditem[0:3]
            for level in levels:
                level = dim.level(level)
                lvl_attr = level.order_attribute or level.key
                lvl_order = level.order or 'asc'
                order.append((lvl_attr, lvl_order))

        order_by = OrderedDict()

        if self.split:
            split_column = sql.expression.column(SPLIT_DIMENSION_NAME)
            order_by[SPLIT_DIMENSION_NAME] = split_column

        # Collect the corresponding attribute columns
        for attribute, order_dir in order:
            try:
                column = selection[attribute.ref()]
            except KeyError:
                attribute = self.mapper.attribute(attribute.ref())
                column = self.column(attribute)

            column = order_column(column, order_dir)

            if attribute.ref() not in order_by:
                order_by[attribute.ref()] = column

        # Collect natural order for selected columns
        for (name, column) in selection.items():
            try:
                # Backward mapping: get Attribute instance by name. The column
                # name used here is already labelled to the logical name
                attribute = self.mapper.attribute(name)
            except KeyError:
                # Since we are already selecting the column, then it should
                # exist this exception is raised when we are trying to get
                # Attribute object for an aggregate - we can safely ignore
                # this.

                # TODO: add natural ordering for measures (may be nice)
                attribute = None

            if attribute and attribute.order and name not in order_by.keys():
                order_by[name] = order_column(column, attribute.order)

        self.statement = self.statement.order_by(*order_by.values())

        return self.statement



# Used as a workaround for "condition" attribute mapping property
# TODO: temp solution
# Assumption: every other attribute is from the same dimension
class _AttributeGetter(object):
    def __init__(self, owner, context):
        self._context = context
        self._owner = owner

    def __getattr__(self, attr):
        return self._column(attr)

    def __getitem__(self, item):
        return self._column(item)

    def _column(self, name):
        attribute = self._context.attribute(name)
        return self._owner.column(attribute)

    # Backward-compatibility for table.c.foo
    @property
    def c(self):
        return self

class _TableGetter(object):
    def __init__(self, owner):
        self._owner = owner

    def __getattr__(self, attr):
        return self._table(attr)

    def __getitem__(self, item):
        return self._table(item)

    def _table(self, name):
        # Create a dummy attribute
        return _ColumnGetter(self._owner, name)


class _ColumnGetter(object):
    def __init__(self, owner, table):
        self._owner = owner
        self._table = table

    def __getattr__(self, attr):
        return self._column(attr)

    def __getitem__(self, item):
        return self._column(item)

    def _column(self, name):
        # Create a dummy attribute
        attribute = PhysicalAttribute(name, table=self._table)
        return self._owner.column(attribute)

    # Backward-compatibility for table.c.foo
    @property
    def c(self):
        return self


########NEW FILE########
__FILENAME__ = store
# -*- coding=utf -*-
from .browser import SnowflakeBrowser
from .mapper import SnowflakeMapper
from ...logging import get_logger
from ...common import coalesce_options
from ...stores import Store
from ...errors import *
from ...browser import *
from ...computation import *
from .query import QueryBuilder
from .utils import CreateTableAsSelect, InsertIntoAsSelect, CreateOrReplaceView

try:
    import sqlalchemy
    import sqlalchemy.sql as sql
    from sqlalchemy.engine import reflection
except ImportError:
    from cubes.common import MissingPackage
    reflection = sqlalchemy = sql = MissingPackage("sqlalchemy", "SQL aggregation browser")


__all__ = [
    "create_sqlalchemy_engine",
    "SQLStore"
]


# Data types of options passed to sqlalchemy.create_engine
# This is used to coalesce configuration string values into appropriate types
SQLALCHEMY_OPTION_TYPES = {
        "case_sensitive":"bool",
        "case_insensitive":"bool",
        "convert_unicode":"bool",
        "echo":"bool",
        "echo_pool":"bool",
        "implicit_returning":"bool",
        "label_length":"int",
        "max_overflow":"int",
        "pool_size":"int",
        "pool_recycle":"int",
        "pool_timeout":"int"
}

# Data types of options passed to the workspace, browser and mapper
# This is used to coalesce configuration string values
OPTION_TYPES = {
        "include_summary": "bool",
        "include_cell_count": "bool",
        "use_denormalization": "bool",
        "safe_labels": "bool"
}

####
# Backend related functions
###
def ddl_for_model(url, model, fact_prefix=None,
                  fact_suffix=None, dimension_prefix=None,
                  dimension_suffix=None, schema_type=None):
    """Create a star schema DDL for a model.

    Parameters:

    * `url` - database url – no connection will be created, just used by
       SQLAlchemy to determine appropriate engine backend
    * `cube` - cube to be described
    * `dimension_prefix` - prefix used for dimension tables
    * `dimension_suffix` - suffix used for dimension tables
    * `schema_type` - ``logical``, ``physical``, ``denormalized``

    As model has no data storage type information, following simple rule is
    used:

    * fact ID is an integer
    * all keys are strings
    * all attributes are strings
    * all measures are floats

    .. warning::

        Does not respect localized models yet.

    """
    raise NotImplementedError

def create_sqlalchemy_engine(url, options, prefix="sqlalchemy_"):
    """Create a SQLAlchemy engine from `options`. Options have prefix
    ``sqlalchemy_``"""
    sa_keys = [key for key in options.keys() if key.startswith(prefix)]
    sa_options = {}
    for key in sa_keys:
        sa_key = key[11:]
        sa_options[sa_key] = options.pop(key)

    sa_options = coalesce_options(sa_options, SQLALCHEMY_OPTION_TYPES)
    engine = sqlalchemy.create_engine(url, **sa_options)

    return engine

class SQLStore(Store):

    def model_provider_name(self):
        return 'default'

    default_browser_name = "snowflake"

    def __init__(self, url=None, engine=None, schema=None, **options):
        """
        The options are:

        Required (one of the two, `engine` takes precedence):

        * `url` - database URL in form of:
          ``backend://user:password@host:port/database``
        * `sqlalchemy_options` - this backend accepts options for SQLAlchemy in the form:
          ``option1=value1[&option2=value2]...``
        * `engine` - SQLAlchemy engine - either this or URL should be provided

        Optional:

        * `schema` - default schema, where all tables are located (if not
          explicitly stated otherwise)
        * `fact_prefix` - used by the snowflake mapper to find fact table for a
          cube, when no explicit fact table name is specified
        * `dimension_prefix` - used by snowflake mapper to find dimension tables
          when no explicit mapping is specified
        * `fact_suffix` - used by the snowflake mapper to find fact table for a
          cube, when no explicit fact table name is specified
        * `dimension_suffix` - used by snowflake mapper to find dimension tables
          when no explicit mapping is specified
        * `dimension_schema` – schema where dimension tables are stored, if
          different than common schema.

        Options for denormalized views:

        * `use_denormalization` - browser will use dernormalized view instead of
          snowflake
        * `denormalized_view_prefix` - if denormalization is used, then this
          prefix is added for cube name to find corresponding cube view
        * `denormalized_view_schema` - schema wehere denormalized views are
          located (use this if the views are in different schema than fact tables,
          otherwise default schema is going to be used)
        """
        if not engine and not url:
            raise ArgumentError("No URL or engine specified in options, "
                                "provide at least one")
        if engine and url:
            raise ArgumentError("Both engine and URL specified. Use only one.")

        # Create a copy of options, because we will be popping from it
        options = dict(options)

        if not engine:
            # Process SQLAlchemy options
            engine = create_sqlalchemy_engine(url, options)

        # TODO: get logger from workspace that opens this store
        self.logger = get_logger()

        self.connectable = engine
        self.schema = schema

        # Load metadata here. This might be too expensive operation to be
        # performed on every request, therefore it is recommended to have one
        # shared open store per process. SQLAlchemy will take care about
        # necessary connections.

        self.metadata = sqlalchemy.MetaData(bind=self.connectable,
                                            schema=self.schema)

        self.options = coalesce_options(options, OPTION_TYPES)

    def _drop_table(self, table, schema, force=False):
        """Drops `table` in `schema`. If table exists, exception is raised
        unless `force` is ``True``"""

        view_name = str(table)
        preparer = self.connectable.dialect.preparer(self.connectable.dialect)
        full_name = preparer.format_table(table)

        if table.exists() and not force:
            raise WorkspaceError("View or table %s (schema: %s) already exists." % \
                               (view_name, schema))

        inspector = sqlalchemy.engine.reflection.Inspector.from_engine(self.connectable)
        view_names = inspector.get_view_names(schema=schema)

        if view_name in view_names:
            # Table reflects a view
            drop_statement = "DROP VIEW %s" % full_name
            self.connectable.execute(drop_statement)
        else:
            # Table reflects a table
            table.drop(checkfirst=False)

    # TODO: broken
    def create_denormalized_view(self, cube, view_name=None, materialize=False,
                                 replace=False, create_index=False,
                                 keys_only=False, schema=None):
        """Creates a denormalized view named `view_name` of a `cube`. If
        `view_name` is ``None`` then view name is constructed by pre-pending
        value of `denormalized_view_prefix` from workspace options to the cube
        name. If no prefix is specified in the options, then view name will be
        equal to the cube name.

        Options:

        * `materialize` - whether the view is materialized (a table) or
          regular view
        * `replace` - if `True` then existing table/view will be replaced,
          otherwise an exception is raised when trying to create view/table
          with already existing name
        * `create_index` - if `True` then index is created for each key
          attribute. Can be used only on materialized view, otherwise raises
          an exception
        * `keys_only` - if ``True`` then only key attributes are used in the
          view, all other detail attributes are ignored
        * `schema` - target schema of the denormalized view, if not specified,
          then `denormalized_view_schema` from options is used if specified,
          otherwise default workspace schema is used (same schema as fact
          table schema).
        """

        # TODO: this method requires more attention, it is just appropriated
        # for recent cubes achanges

        engine = self.connectable

        # TODO: we actually don't need browser, we are just reusing its
        # __init__ for other objects. This should be recreated here.
        browser = SnowflakeBrowser(cube, self, schema=schema)
        builder = QueryBuilder(browser)

        key_attributes = []
        for dim in cube.dimensions:
            key_attributes += dim.key_attributes()

        if keys_only:
            statement = builder.denormalized_statement(attributes=key_attributes, expand_locales=True)
        else:
            statement = builder.denormalized_statement(expand_locales=True)

        schema = schema or self.options.get("denormalized_view_schema") or self.schema

        dview_prefix = self.options.get("denormalized_view_prefix","")
        view_name = view_name or dview_prefix + cube.name

        if browser.mapper.fact_name == view_name and schema == browser.mapper.schema:
            raise WorkspaceError("target denormalized view is the same as source fact table")

        table = sqlalchemy.Table(view_name, self.metadata,
                                 autoload=False, schema=schema)

        if table.exists():
            self._drop_table(table, schema, force=replace)

        if materialize:
            # TODO: Handle this differently for postgres
            create_view = CreateTableAsSelect(table, statement)
        else:
            create_view = CreateOrReplaceView(table, statement)

        self.logger.info("creating denormalized view %s (materialized: %s)" \
                                            % (str(table), materialize))
        # print("SQL statement:\n%s" % statement)
        engine.execute(create_view)

        if create_index:
            if not materialize:
                raise WorkspaceError("Index can be created only on a materialized view")

            # self.metadata.reflect(schema = schema, only = [view_name] )
            table = sqlalchemy.Table(view_name, self.metadata,
                                     autoload=True, schema=schema)

            insp = reflection.Inspector.from_engine(engine)
            insp.reflecttable(table, None)

            for attribute in key_attributes:
                label = attribute.ref()
                self.logger.info("creating index for %s" % label)
                column = table.c[label]
                name = "idx_%s_%s" % (view_name, label)
                index = sqlalchemy.schema.Index(name, column)
                index.create(engine)

        return statement

    def validate_model(self):
        """Validate physical representation of model. Returns a list of
        dictionaries with keys: ``type``, ``issue``, ``object``.

        Types might be: ``join`` or ``attribute``.

        The ``join`` issues are:

        * ``no_table`` - there is no table for join
        * ``duplicity`` - either table or alias is specified more than once

        The ``attribute`` issues are:

        * ``no_table`` - there is no table for attribute
        * ``no_column`` - there is no column for attribute
        * ``duplicity`` - attribute is found more than once

        """
        issues = []

        for cube in self.model.cubes:
            browser = self.browser(cube)
            issues += browser.validate()

        return issues

    ########################################################################
    ########################################################################
    ##
    ## Aggregates
    ##
    """
    Aggregate specification:
        * cube
        * dimensions, "grain" (levels) + required dimensions
        * aggregate schema
        * aggregate table
        * create_dimensions? flag

    Grain dimension:
        * Name: prefix_dimension_level
        * Attributes: all level attributes
        * NON-UNIQUE level key: join will have to be composed of multiple keys
        * UNIQUE level key: join might be based on level key
    """

    def _create_indexes(self, table, columns, schema=None):
        """Create indexes on `table` in `schema` for `columns`"""

        raise NotImplementedError

    def create_conformed_rollup(self, cube, dimension, level=None, hierarchy=None,
                                schema=None, dimension_prefix=None, dimension_suffix=None,
                                replace=False):
        """Extracts dimension values at certain level into a separate table.
        The new table name will be composed of `dimension_prefix`, dimension
        name and suffixed by dimension level. For example a product dimension
        at category level with prefix `dim_` will be called
        ``dim_product_category``

        Attributes:

        * `dimension` – dimension to be extracted
        * `level` – grain level
        * `hierarchy` – hierarchy to be used
        * `schema` – target schema
        * `dimension_prefix` – prefix used for the dimension table
        * `dimension_suffix` – suffix used for the dimension table
        * `replace` – if ``True`` then existing table will be replaced,
          otherwise an exception is raised if table already exists.
        """
        mapper = SnowflakeMapper(cube, cube.mappings, schema=schema, **self.options)
        context = QueryContext(cube, mapper, schema=schema, etadata=self.metadata)

        dimension = cube.dimension(dimension)
        hierarchy = dimension.hierarchy(hierarchy)
        if level:
            depth = hierarchy.level_index(dimension.level(level))+1
        else:
            depth = len(hierarchy)

        if depth == 0:
            raise ArgumentError("Depth for dimension values should not be 0")
        elif depth is not None:
            levels = hierarchy.levels[0:depth]


        attributes = []
        for level in levels:
            attributes.extend(level.attributes)

        statement = context.denormalized_statement(attributes=attributes,
                                                    include_fact_key=False)

        group_by = [context.column(attr) for attr in attributes]
        statement = statement.group_by(*group_by)

        table_name = "%s%s%s_%s" % (dimension_prefix or "", dimension_suffix or "",
                                    str(dimension), str(level))
        self.create_table_from_statement(table_name, statement, schema,
                                            replace, insert=True)

    def create_conformed_rollups(self, cube, dimensions, grain=None, schema=None,
                                 dimension_prefix=None, dimension_suffix=None,
                                 replace=False):
        """Extract multiple dimensions from a snowflake. See
        `extract_dimension()` for more information. `grain` is a dictionary
        where keys are dimension names and values are levels, if level is
        ``None`` then all levels are considered."""

        grain = grain or {}

        for dim in dimensions:
            dim = cube.dimension(dim)
            level = grain.get(str(dim))
            hierarchy = dim.hierarchy()
            if level:
                level_index = hierarchy.level_index(level)
            else:
                level_index = len(hierarchy)

            for depth in range(0,level_index):
                level = hierarchy[depth]
                self.create_conformed_rollup(cube, dim, level=level,
                                    schema=schema,
                                    dimension_prefix=dimension_prefix or "",
                                    dimension_suffix=dimension_suffix or "",
                                    replace=replace)

    def create_table_from_statement(self, table_name, statement, schema,
                                     replace=False, insert=False):
        """Creates or replaces a table from statement.

        Arguments:

        * `table_name` - name of target table
        * `schema` – target table schema
        * `statement` – SQL statement used to get structure of the new table
        * `insert` – if `True` then data are inserted from the statement,
          otherwise only empty table is created. Defaut is `False`
        * `replace` – if `True` old table will be dropped, otherwise if table
          already exists an exception is raised.
        """

        #
        # Create table
        #
        table = sqlalchemy.Table(table_name, self.metadata,
                                 autoload=False, schema=schema)

        if table.exists():
            self._drop_table(table, schema, force=replace)

        for col in statement.columns:
            # mysql backend requires default string length
            if self.connectable.name == "mysql" \
                    and isinstance(col.type, sqlalchemy.String) \
                    and not col.type.length:
                col_type = sqlalchemy.String(255)
            else:
                col_type = col.type

            new_col = sqlalchemy.Column(col.name, col_type)
            table.append_column(new_col)

        self.logger.info("creating table '%s'" % str(table))
        self.metadata.create_all(tables=[table])

        if insert:
            self.logger.debug("inserting into table '%s'" % str(table))
            insert_statement = InsertIntoAsSelect(table, statement,
                                                  columns=statement.columns)
            self.connectable.execute(insert_statement)

        return table

    def create_cube_aggregate(self, browser, table_name=None, dimensions=None,
                              dimension_links=None, schema=None,
                              replace=False):
        """Creates an aggregate table. If dimensions is `None` then all cube's
        dimensions are considered.

        Arguments:

        * `dimensions`: list of dimensions to use in the aggregated cuboid, if
          `None` then all cube dimensions are used
        * `dimension_links`: list of dimensions that are required for each
          aggregation (for example a date dimension in most of the cases). The
          list should be a subset of `dimensions`.
        * `aggregates_prefix`: aggregated table prefix
        * `aggregates_schema`: schema where aggregates are stored

        """

        if browser.store != self:
            raise ArgumentError("Can create aggregate table only within "
                                "the same store")

        schema = schema or self.options.get("aggregates_schema", self.schema)
        prefix = self.options.get("aggregates_prefix","")
        table_name = table_name or prefix + cube.name

        # Just a shortcut
        cube = browser.cube
        if dimensions:
            dimensions = [cube.dimension(dim) for dim in dimensions]
        else:
            dimensions = cube.dimensions

        # Collect keys that are going to be used for aggregations
        keys = []
        for dimension in dimensions:
            keys += [level.key for level in dimension.hierarchy().levels]

        builder = QueryBuilder(browser)

        if builder.snowflake.fact_name == table_name \
                and builder.snowflake.schema == schema:
            raise ArgumentError("target is the same as source fact table")

        drilldown = {}

        for dim in dimensions:
            level = dim.hierarchy().levels[-1]
            drilldown[str(dim)] = level

        cell = Cell(cube)
        drilldown = Drilldown(drilldown, cell)

        # Create dummy statement of all dimension level keys for
        # getting structure for table creation
        # TODO: attributes/keys?
        statement = builder.aggregation_statement(cell,
                                                  drilldown,
                                                  cube.aggregates)

        #
        # Create table
        #
        table = self.create_table_from_statement(table_name,
                                                  statement,
                                                  schema=schema,
                                                  replace=replace,
                                                  insert=False)

        cuboids = hierarchical_cuboids(dimensions,
                                        required=dimension_links)

        for cuboid in cuboids:

            # 'cuboid' is described as a list of ('dimension', 'level') tuples
            # where 'level' is deepest level to be considered

            self.logger.info("aggregating cuboid %s" % (cuboid, ) )

            dd = {}
            keys = None
            for dim, level in cuboid:
                dd[str(dim)] = level
                dim = cube.dimension(dim)
                hier = dim.hierarchy()
                levels = hier.levels_for_depth(hier.level_index(level)+1)
                keys = [l.key for l in levels]

            dd = Drilldown(dd, cell)

            statement = builder.aggregation_statement(cell,
                                                      aggregates=cube.aggregates,
                                                      attributes=keys,
                                                      drilldown=drilldown)
            self.logger.info("inserting")
            insert = InsertIntoAsSelect(table, statement,
                                        columns=statement.columns)
            self.connectable.execute(str(insert))

########NEW FILE########
__FILENAME__ = utils
"""Cubes SQL backend utilities, mostly to be used by the slicer command."""

from sqlalchemy.sql.expression import Executable, ClauseElement
from sqlalchemy.ext.compiler import compiles
import sqlalchemy.sql as sql

__all__ = [
    "CreateTableAsSelect",
    "InsertIntoAsSelect",
    "CreateOrReplaceView",
    "condition_conjunction",
    "order_column"
]

class CreateTableAsSelect(Executable, ClauseElement):
    def __init__(self, table, select):
        self.table = table
        self.select = select

@compiles(CreateTableAsSelect)
def visit_create_table_as_select(element, compiler, **kw):
    preparer = compiler.dialect.preparer(compiler.dialect)
    full_name = preparer.format_table(element.table)

    return "CREATE TABLE %s AS (%s)" % (
        element.table,
        compiler.process(element.select)
    )
@compiles(CreateTableAsSelect, "sqlite")
def visit_create_table_as_select(element, compiler, **kw):
    preparer = compiler.dialect.preparer(compiler.dialect)
    full_name = preparer.format_table(element.table)

    return "CREATE TABLE %s AS %s" % (
        element.table,
        compiler.process(element.select)
    )

class CreateOrReplaceView(Executable, ClauseElement):
    def __init__(self, view, select):
        self.view = view
        self.select = select

@compiles(CreateOrReplaceView)
def visit_create_or_replace_view(element, compiler, **kw):
    preparer = compiler.dialect.preparer(compiler.dialect)
    full_name = preparer.format_table(element.view)

    return "CREATE OR REPLACE VIEW %s AS (%s)" % (
        full_name,
        compiler.process(element.select)
    )

@compiles(CreateOrReplaceView, "sqlite")
def visit_create_or_replace_view(element, compiler, **kw):
    preparer = compiler.dialect.preparer(compiler.dialect)
    full_name = preparer.format_table(element.view)

    return "CREATE VIEW %s AS %s" % (
        full_name,
        compiler.process(element.select)
    )

@compiles(CreateOrReplaceView, "mysql")
def visit_create_or_replace_view(element, compiler, **kw):
    preparer = compiler.dialect.preparer(compiler.dialect)
    full_name = preparer.format_table(element.view)

    return "CREATE OR REPLACE VIEW %s AS %s" % (
        full_name,
        compiler.process(element.select)
    )

class InsertIntoAsSelect(Executable, ClauseElement):
    def __init__(self, table, select, columns=None):
        self.table = table
        self.select = select
        self.columns = columns


@compiles(InsertIntoAsSelect, "mysql")
def visit_insert_into_as_select(element, compiler, **kw):
    preparer = compiler.dialect.preparer(compiler.dialect)
    full_name = preparer.format_table(element.table)

    if element.columns:
        qcolumns = [preparer.format_column(c) for c in element.columns]
        col_list = "(%s) " % ", ".join([str(c) for c in qcolumns])
    else:
        col_list = ""

    stmt = "INSERT INTO %s %s %s" % (
        full_name,
        col_list,
        compiler.process(element.select)
    )

    return stmt


@compiles(InsertIntoAsSelect)
def visit_insert_into_as_select(element, compiler, **kw):
    preparer = compiler.dialect.preparer(compiler.dialect)
    full_name = preparer.format_table(element.table)

    if element.columns:
        qcolumns = [preparer.format_column(c) for c in element.columns]
        col_list = "(%s) " % ", ".join([str(c) for c in qcolumns])
    else:
        col_list = ""

    stmt = "INSERT INTO %s %s(%s)" % (
        full_name,
        col_list,
        compiler.process(element.select)
    )

    return stmt


def condition_conjunction(conditions):
    """Do conjuction of conditions if there are more than one, otherwise just
    return the single condition."""
    if not conditions:
        return None
    elif len(conditions) == 1:
        return conditions[0]
    else:
        return sql.expression.and_(*conditions)


def order_column(column, order):
    """Orders a `column` according to `order` specified as string."""

    if not order:
        return column
    elif order.lower().startswith("asc"):
        return column.asc()
    elif order.lower().startswith("desc"):
        return column.desc()
    else:
        raise ArgumentError("Unknown order %s for column %s") % (order, column)


########NEW FILE########
__FILENAME__ = browser
# -*- coding: utf-8 -*-

import copy
import re
from collections import namedtuple

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from cubes.errors import *
from .model import Dimension, Cube
from .common import IgnoringDictionary, to_unicode_string
from .logging import get_logger
from .extensions import Extensible
from .calendar import CalendarMemberConverter


__all__ = [
    "AggregationBrowser",
    "AggregationResult",
    "CalculatedResultIterator",
    "Facts",

    "Cell",
    "Cut",
    "PointCut",
    "RangeCut",
    "SetCut",

    "cuts_from_string",
    "string_from_cuts",
    "string_from_path",
    "string_from_hierarchy",
    "string_to_drilldown",
    "path_from_string",
    "cut_from_string",
    "cut_from_dict",

    "Drilldown",
    "DrilldownItem",
    "levels_from_drilldown",

    "TableRow",
    "CrossTable",
    "cross_table",
    "SPLIT_DIMENSION_NAME",
]

SPLIT_DIMENSION_NAME = '__within_split__'
NULL_PATH_VALUE = '__null__'


class AggregationBrowser(Extensible):
    """Class for browsing data cube aggregations

    :Attributes:
      * `cube` - cube for browsing

    """

    __extension_type__ = "browser"
    __extension_suffix__ = "Browser"

    builtin_functions = []

    def __init__(self, cube, store=None, locale=None, **options):
        """Creates and initializes the aggregation browser. Subclasses should
        override this method. """
        super(AggregationBrowser, self).__init__()

        if not cube:
            raise ArgumentError("No cube given for aggregation browser")

        self.cube = cube
        self.store = store
        self.calendar = None

    def features(self):
        """Returns a dictionary of available features for the browsed cube.
        Default implementation returns an empty dictionary.

        Standard keys that might be present:

        * `actions` – list of actions that can be done with the cube, such as
          ``facts``, ``aggregate``, ``members``, ...
        * `post_processed_aggregates` – list of aggregates that are computed
          after the result is fetched from the source (not natively).

        Subclasses are advised to override this method.
        """
        return {}

    def aggregate(self, cell=None, aggregates=None, drilldown=None, split=None,
                  order=None, page=None, page_size=None, **options):

        """Return aggregate of a cell.

        Arguments:

        * `cell` – cell to aggregate. Can be either a :class:`cubes.Cell`
          object or a string with same syntax as for the Slicer :doc:`server
          <server>`
        * `aggregates` - list of aggregate measures. By default all
          cube's aggregates are included in the result.
        * `drilldown` - dimensions and levels through which to drill-down
        * `split` – cell for alternate 'split' dimension. Same type of
          argument as `cell`.
        * `order` – attribute order specification (see below)
        * `page` – page index when requesting paginated results
        * `page_size` – number of result items per page

        Drill down can be specified in two ways: as a list of dimensions or as
        a dictionary. If it is specified as list of dimensions, then cell is
        going to be drilled down on the next level of specified dimension. Say
        you have a cell for year 2010 and you want to drill down by months,
        then you specify ``drilldown = ["date"]``.

        If `drilldown` is a dictionary, then key is dimension or dimension
        name and value is last level to be drilled-down by. If the cell is at
        `year` level and drill down is: ``{ "date": "day" }`` then both
        `month` and `day` levels are added.

        If there are no more levels to be drilled down, an exception is
        raised. Say your model has three levels of the `date` dimension:
        `year`, `month`, `day` and you try to drill down by `date` at the next
        level then ``ValueError`` will be raised.

        Retruns a :class:`AggregationResult` object.

        If `split` is specified, then virtual dimension named
        `__within_split__` will be created and will contain `true` value if
        the cell is within the split cell and `false` if the cell is outside
        of the split.

        Note: subclasses should implement `provide_aggregate()` method.
        """

        if "measures" in options:
            raise ArgumentError("measures in aggregate are depreciated")

        aggregates = self.prepare_aggregates(aggregates)
        order = self.prepare_order(order, is_aggregate=True)

        converters = {
            "time": CalendarMemberConverter(self.calendar)
        }

        if cell is None:
            cell = Cell(self.cube)
        elif isinstance(cell, basestring):
            cuts = cuts_from_string(self.cube, cell,
                                    role_member_converters=converters)
            cell = Cell(self.cube, cuts)

        if isinstance(split, basestring):
            cuts = cuts_from_string(self.cube, split,
                                    role_member_converters=converters)
            split = Cell(self.cube, cuts)

        drilldon = Drilldown(drilldown, cell)

        result = self.provide_aggregate(cell,
                                        aggregates=aggregates,
                                        drilldown=drilldon,
                                        split=split,
                                        order=order,
                                        page=page,
                                        page_size=page_size,
                                        **options)
        return result

    def provide_aggregate(self, cell=None, measures=None, aggregates=None,
                          drilldown=None, split=None, order=None, page=None,
                          page_size=None, **options):
        """Method to be implemented by subclasses. The arguments are prepared
        by the superclass. Arguments:

        * `cell` – cell to be drilled down. Guaranteed to be a `Cell` object
          even for an empty cell
        * `aggregates` – list of aggregates to aggregate. Contains list of cube
          aggregate attribute objects.
        * `drilldown` – `Drilldown` instance
        * `split` – `Cell` instance
        * `order` – list of tuples: (`attribute`, `order`)

        """
        raise NotImplementedError

    def prepare_aggregates(self, aggregates=None, measures=None):
        """Prepares the aggregate list for aggregatios. `aggregates` might be a
        list of aggregate names or `MeasureAggregate` objects.

        Aggregates that are used in post-aggregation calculations are included
        in the result. This method is using `is_builtin_function()` to check
        whether the aggregate is native to the backend or not.

        If `measures` are specified, then aggregates that refer tho the
        measures in the list are returned.

        If no aggregates are specified then all cube's aggregates are returned.

        .. note::

            Either specify `aggregates` or `measures`, not both.
        """

        # Coalesce measures - make sure that they are Attribute objects, not
        # strings. Strings are converted to corresponding Cube measure
        # attributes
        # TODO: perhaps we might merge (without duplicates)

        if aggregates and measures:
            raise ArgumentError("Only aggregates or measures can be "
                                "specified, not both")
        if aggregates:
            try:
                aggregates = self.cube.get_aggregates(aggregates)
            except KeyError as e:
                raise NoSuchAttributeError("No measure aggregate '%s' in cube '%s'"
                                           % (str(e), str(self.cube)))
        elif measures:
            aggregates = []
            for measure in measures:
                aggregates += self.cube.aggregates_for_measure(measure)

        # If no aggregate is specified, then all are used
        aggregates = aggregates or self.cube.aggregates

        seen = set(a.name for a in aggregates)
        dependencies = []

        # Resolve aggregate dependencies for non-builtin functions:
        for agg in aggregates:
            if agg.measure and \
                    not self.is_builtin_function(agg.function, agg) \
                    and agg.measure not in seen:
                seen.add(agg.measure)

                try:
                    aggregate = self.cube.measure_aggregate(agg.measure)
                except NoSuchAttributeError as e:
                    raise NoSuchAttributeError("Cube '%s' has no measure aggregate "
                                            "'%s' for '%s'" % (self.cube.name,
                                                               agg.measure,
                                                               agg.name))
                dependencies.append(aggregate)

        aggregates += dependencies
        return aggregates

    def prepare_order(self, order, is_aggregate=False):
        """Prepares an order list. Returns list of tuples (`attribute`,
        `order_direction`). `attribute` is cube's attribute object."""

        order = order or []
        new_order = []

        for item in order:
            if isinstance(item, basestring):
                name = item
                direction = None
            else:
                name, direction = item[0:2]

            attribute = None
            if is_aggregate:
                function = None
                try:
                    attribute = self.cube.measure_aggregate(name)
                    function = attribute.function
                except NoSuchAttributeError:
                    attribute = self.cube.attribute(name)

                if function and not self.is_builtin_function(function,
                                                             attribute):
                    # TODO: Temporary solution: get the original measure instead

                    try:
                        name = str(attribute.measure)
                        measure = self.cube.measure_aggregate(name)
                    except NoSuchAttributeError:
                        measure = self.cube.measure(name)

                    self.logger.warn("ordering of post-processed aggregate"
                                     " %s will be based on measure %s"
                                     % (attribute.name, measure.name))
                    attribute = measure
            else:
                attribute = self.cube.attribute(name)

            if attribute:
                new_order.append( (attribute, direction) )

        return new_order

    def assert_low_cardinality(self, cell, drilldown):
        """Raises `ArgumentError` when there is drilldown through high
        cardinality dimension or level and there is no condition in the cell
        for the level."""

        hc_levels = drilldown.high_cardinality_levels(cell)
        if hc_levels:
            names = [str(level) for level in hc_levels]
            names = ", ".join(names)
            raise ArgumentError("Can not drilldown on high-cardinality "
                                "levels (%s) without including both page_size "
                                "and page arguments, or else a point/set cut on the level"
                                % names)


    def is_builtin_function(self, function_name, aggregate):
        """Returns `True` if function `function_name` for `aggregate` is
        bult-in. Returns `False` if the browser can not compute the function
        and post-aggregation calculation should be used.

        Subclasses should override this method."""
        raise NotImplementedError

    def facts(self, cell=None, fields=None, **options):
        """Return an iterable object with of all facts within cell.
        `fields` is list of fields to be considered in the output.

        Subclasses overriding this method sould return a :class:`Facts` object
        and set it's `attributes` to the list of selected attributes."""

        raise NotImplementedError

    def fact(self, key):
        """Returns a single fact from cube specified by fact key `key`"""
        raise NotImplementedError

    def members(self, cell, dimension, depth=None, level=None, hierarchy=None,
                attributes=None, page=None, page_size=None, order=None,
                **options):
        """Return members of `dimension` with level depth `depth`. If `depth`
        is ``None``, all levels are returned. If no `hierarchy` is specified,
        then default dimension hierarchy is used.
        """
        order = self.prepare_order(order, is_aggregate=False)

        if cell is None:
            cell = Cell(self.cube)

        dimension = self.cube.dimension(dimension)
        hierarchy = dimension.hierarchy(hierarchy)

        if depth is not None and level:
            raise ArgumentError("Both depth and level used, provide only one.")

        if not depth and not level:
            levels = hierarchy.levels
        elif depth == 0:
            raise ArgumentError("Depth for dimension members should not be 0")
        elif depth:
            levels = hierarchy.levels_for_depth(depth)
        else:
            index = hierarchy.level_index(level)
            levels = hierarchy.levels_for_depth(index+1)

        result = self.provide_members(cell,
                                      dimension=dimension,
                                      hierarchy=hierarchy,
                                      levels=levels,
                                      attributes=attributes,
                                      order=order,
                                      page=page,
                                      page_size=page_size,
                                      **options)
        return result

    def values(self, *args, **kwargs):
        # TODO: depreciated
        self.logger.warn("values() is depreciated, use members()")
        return self.members(*args, **kwargs)

    def test(self, **options):
        """Tests whether the cube can be used. Refer to the backend's
        documentation for more information about what is being tested."""
        raise NotImplementedError

    def report(self, cell, queries):
        """Bundle multiple requests from `queries` into a single one.

        Keys of `queries` are custom names of queries which caller can later
        use to retrieve respective query result. Values are dictionaries
        specifying arguments of the particular query. Each query should
        contain at least one required value ``query`` which contains name of
        the query function: ``aggregate``, ``facts``, ``fact``, ``values`` and
        cell ``cell`` (for cell details). Rest of values are function
        specific, please refer to the respective function documentation for
        more information.

        Example::

            queries = {
                "product_summary" = { "query": "aggregate",
                                      "drilldown": "product" }
                "year_list" = { "query": "values",
                                "dimension": "date",
                                "depth": 1 }
            }

        Result is a dictionary where keys wil lbe the query names specified in
        report specification and values will be result values from each query
        call.::

            result = browser.report(cell, queries)
            product_summary = result["product_summary"]
            year_list = result["year_list"]

        This method provides convenient way to perform multiple common queries
        at once, for example you might want to have always on a page: total
        transaction count, total transaction amount, drill-down by year and
        drill-down by transaction type.

        Raises `cubes.ArgumentError` when there are no queries specified
        or if a query is of unknown type.

        .. `formatters` is a dictionary where keys are formatter names
        .. (arbitrary) and values are formatter instances.

        *Roll-up*

        Report queries might contain ``rollup`` specification which will
        result in "rolling-up" one or more dimensions to desired level. This
        functionality is provided for cases when you would like to report at
        higher level of aggregation than the cell you provided is in. It works
        in similar way as drill down in :meth:`AggregationBrowser.aggregate`
        but in the opposite direction (it is like ``cd ..`` in a UNIX shell).

        Example: You are reporting for year 2010, but you want to have a bar
        chart with all years. You specify rollup::

            ...
            "rollup": "date",
            ...

        Roll-up can be:

            * a string - single dimension to be rolled up one level
            * an array - list of dimension names to be rolled-up one level
            * a dictionary where keys are dimension names and values are
              levels to be rolled up-to

        *Future*

        In the future there might be optimisations added to this method,
        therefore it will become faster than subsequent separate requests.
        Also when used with Slicer OLAP service server number of HTTP call
        overhead is reduced.
        """

        # TODO: add this: cell_details=True, cell_details_key="_details"
        #
        # If `cell_details` is ``True`` then a key with name specified in
        # `cell_details_key` is added with cell details (see
        # `AggregationBrowser.cell_details() for more information). Default key
        # name is ``_cell``.

        report_result = {}

        for result_name, query in queries.items():
            query_type = query.get("query")
            if not query_type:
                raise ArgumentError("No report query for '%s'" % result_name)

            # FIXME: add: cell = query.get("cell")

            args = dict(query)
            del args["query"]

            # Note: we do not just convert name into function from symbol for possible future
            # more fine-tuning of queries as strings

            # Handle rollup
            rollup = query.get("rollup")
            if rollup:
                query_cell = cell.rollup(rollup)
            else:
                query_cell = cell

            if query_type == "aggregate":
                result = self.aggregate(query_cell, **args)

            elif query_type == "facts":
                result = self.facts(query_cell, **args)

            elif query_type == "fact":
                # Be more tolerant: by default we want "key", but "id" might be common
                key = args.get("key")
                if not key:
                    key = args.get("id")
                result = self.fact(key)

            elif query_type == "values":
                result = self.values(query_cell, **args)

            elif query_type == "details":
                # FIXME: depreciate this raw form
                result = self.cell_details(query_cell, **args)

            elif query_type == "cell":
                details = self.cell_details(query_cell, **args)
                cell_dict = query_cell.to_dict()

                for cut, detail in zip(cell_dict["cuts"], details):
                    cut["details"] = detail

                result = cell_dict
            else:
                raise ArgumentError("Unknown report query '%s' for '%s'" %
                                    (query_type, result_name))

            report_result[result_name] = result

        return report_result

    def cell_details(self, cell=None, dimension=None):
        """Returns details for the `cell`. Returned object is a list with one
        element for each cell cut. If `dimension` is specified, then details
        only for cuts that use the dimension are returned.

        Default implemenatation calls `AggregationBrowser.cut_details()` for
        each cut. Backends might customize this method to make it more
        efficient.

        .. warning:

            Return value of this method is not yet decided. Might be changed
            so that each element is a dictionary derived from cut (see
            `Cut.to_dict()` method of all Cut subclasses) and the details will
            be under the ``details`` key. Will depend on usability of current
            one.
        """

        # TODO: how we can add the cell as well?
        if not cell:
            return []

        if dimension:
            cuts = [cut for cut in cell.cuts
                    if str(cut.dimension) == str(dimension)]
        else:
            cuts = cell.cuts

        details = [self.cut_details(cut) for cut in cuts]

        return details

    def cut_details(self, cut):
        """Gets details for a `cut` which should be a `Cut` instance.

        * `PointCut` - all attributes for each level in the path
        * `SetCut` - list of `PointCut` results, one per path in the set
        * `RangeCut` - `PointCut`-like results for lower range (from) and
          upper range (to)

        """

        dimension = self.cube.dimension(cut.dimension)

        if isinstance(cut, PointCut):
            details = self._path_details(dimension, cut.path, cut.hierarchy)

        elif isinstance(cut, SetCut):
            details = [self._path_details(dimension, path, cut.hierarchy) for path in cut.paths]

        elif isinstance(cut, RangeCut):
            details = {
                "from": self._path_details(dimension, cut.from_path,
                                           cut.hierarchy),
                "to": self._path_details(dimension, cut.to_path, cut.hierarchy)
            }

        else:
            raise Exception("Unknown cut type %s" % cut)

        return details

    def _path_details(self, dimension, path, hierarchy=None):
        """Returns a list of details for a path. Each element of the list
        corresponds to one level of the path and is represented by a
        dictionary. The keys are dimension level attributes. Returns ``None``
        when there is no such path for the dimension.

        Two redundant keys are added: ``_label`` and ``_key`` representing
        level key and level label (based on `Level.label_attribute_key`).

        .. note::

            The behaviour should be configurable: we either return all the
            keys or just a label and a key.
        """

        hierarchy = dimension.hierarchy(hierarchy)
        details = self.path_details(dimension, path, hierarchy)

        if not details:
            return None

        if (dimension.is_flat and not dimension.has_details):
            name = dimension.all_attributes[0].name
            value = details.get(name)
            item = {name: value}
            item["_key"] = value
            item["_label"] = value
            result = [item]
        else:
            result = []
            for level in hierarchy.levels_for_path(path):
                item = {a.ref(): details.get(a.ref()) for a in
                        level.attributes}
                item["_key"] = details.get(level.key.ref())
                item["_label"] = details.get(level.label_attribute.ref())
                result.append(item)

        return result

    def path_details(self, dimension, path, hierarchy):
        """Returns empty path details. Default fall-back for backends that do
        not support the path details. The level key and label are the same
        derived from the key."""

        detail = {}
        for level, key in zip(hierarchy.levels, path):
            for attr in level.attributes:
                if attr == level.key or attr == level.label_attribute:
                    detail[attr.ref()] = key
                else:
                    detail[attr.ref()] = None

        return detail

class Facts(object):
    def __init__(self, facts, attributes):
        """A facts iterator object returned by the browser's `facts()`
        method."""

        self.facts = facts or []
        self.attributes = attributes

    def __iter__(self):
        return iter(self.facts)


class Cell(object):
    """Part of a cube determined by slicing dimensions. Immutable object."""
    def __init__(self, cube=None, cuts=None):
        if not isinstance(cube, Cube):
            raise ArgumentError("Cell cube should be sublcass of Cube, "
                                "provided: %s" % type(cube).__name__)
        self.cube = cube
        self.cuts = cuts if cuts is not None else []

    def __and__(self, other):
        """Returns a new cell that is a conjunction of the two provided
        cells. The cube has to match."""
        if self.cube != other.cube:
            raise ArgumentError("Can not combine two cells from different "
                                "cubes '%s' and '%s'."
                                % (self.name, other.name))
        cuts = self.cuts + other.cuts
        return Cell(self.cube, cuts=cuts)

    def to_dict(self):
        """Returns a dictionary representation of the cell"""
        result = {
            "cube": str(self.cube.name),
            "cuts": [cut.to_dict() for cut in self.cuts]
        }

        return result

    def slice(self, cut):
        """Returns new cell by slicing receiving cell with `cut`. Cut with
        same dimension as `cut` will be replaced, if there is no cut with the
        same dimension, then the `cut` will be appended.
        """

        # Fix for wrong early design decision:
        if isinstance(cut, Dimension) or isinstance(cut, basestring):
            raise CubesError("slice() should now be called with a cut (since v0.9.2). To get "
                             "original behaviour of one-dimension point cut, "
                             "use cell.slice(PointCut(dim,path))")

        cuts = self.cuts[:]
        index = self._find_dimension_cut(cut.dimension)
        if index is not None:
            cuts[index] = cut
        else:
            cuts.append(cut)

        return Cell(cube=self.cube, cuts=cuts)

    def _find_dimension_cut(self, dimension):
        """Returns index of first occurence of cut for `dimension`. Returns
        ``None`` if no cut with `dimension` is found."""
        names = [str(cut.dimension) for cut in self.cuts]

        try:
            index = names.index(str(dimension))
            return index
        except ValueError:
            return None

    def point_slice(self, dimension, path):
        """
        Create another cell by slicing receiving cell through `dimension`
        at `path`. Receiving object is not modified. If cut with dimension
        exists it is replaced with new one. If path is empty list or is none,
        then cut for given dimension is removed.

        Example::

            full_cube = Cell(cube)
            contracts_2010 = full_cube.point_slice("date", [2010])

        Returns: new derived cell object.

        .. warning::

            Depreiated. Use :meth:`cell.slice` instead with argument
            `PointCut(dimension, path)`

        """

        dimension = self.cube.dimension(dimension)
        cuts = self.dimension_cuts(dimension, exclude=True)
        if path:
            cut = PointCut(dimension, path)
            cuts.append(cut)
        return Cell(cube=self.cube, cuts=cuts)

    def drilldown(self, dimension, value, hierarchy=None):
        """Create another cell by drilling down `dimension` next level on
        current level's key `value`.

        Example::

            cell = cubes.Cell(cube)
            cell = cell.drilldown("date", 2010)
            cell = cell.drilldown("date", 1)

        is equivalent to:

            cut = cubes.PointCut("date", [2010, 1])
            cell = cubes.Cell(cube, [cut])

        Reverse operation is ``cubes.rollup("date")``

        Works only if the cut for dimension is `PointCut`. Otherwise the
        behaviour is undefined.

        If `hierarchy` is not specified (by default) then default dimension
        hierarchy is used.

        Returns new derived cell object.
        """
        dimension = self.cube.dimension(dimension)
        dim_cut = self.cut_for_dimension(dimension)

        old_path = dim_cut.path if dim_cut else []
        new_cut = PointCut(dimension, old_path + [value], hierarchy=hierarchy)

        cuts = [cut for cut in self.cuts if cut is not dim_cut]
        cuts.append(new_cut)

        return Cell(cube=self.cube, cuts=cuts)

    def multi_slice(self, cuts):
        """Create another cell by slicing through multiple slices. `cuts` is a
        list of `Cut` object instances. See also :meth:`Cell.slice`."""

        if isinstance(cuts, dict):
            raise CubesError("dict type is not supported any more, use list of Cut instances")

        cell = self
        for cut in cuts:
            cell = cell.slice(cut)

        return cell

    def cut_for_dimension(self, dimension):
        """Return first found cut for given `dimension`"""
        dimension = self.cube.dimension(dimension)

        cut_dimension = None
        for cut in self.cuts:
            cut_dimension = self.cube.dimension(cut.dimension)

            if cut_dimension == dimension:
                return cut

        return None

    def point_cut_for_dimension(self, dimension):
        """Return first point cut for given `dimension`"""

        dimension = self.cube.dimension(dimension)

        cutdim = None
        for cut in self.cuts:
            cutdim = self.cube.dimension(cut.dimension)
            if isinstance(cut, PointCut) and cutdim == dimension:
                return cut

        return None

    def rollup_dim(self, dimension, level=None, hierarchy=None):
        """Rolls-up cell - goes one or more levels up through dimension
        hierarchy. If there is no level to go up (we are at the top level),
        then the cut is removed.

        If no `hierarchy` is specified, then the default dimension's hierarchy
        is used.

        Returns new cell object.
        """

        # FIXME: make this the default roll-up
        # Reason:
        #     * simpler to use
        #     * can be used more nicely in Jinja templates

        dimension = self.cube.dimension(dimension)
        dim_cut = self.point_cut_for_dimension(dimension)

        if not dim_cut:
            return copy.copy(self)
            # raise ValueError("No cut to roll-up for dimension '%s'" % dimension.name)

        cuts = [cut for cut in self.cuts if cut is not dim_cut]

        hier = dimension.hierarchy(hierarchy)
        rollup_path = hier.rollup(dim_cut.path, level)

        # If the rollup path is empty, we are at the top level therefore we
        # are removing the cut for the dimension.

        if rollup_path:
            new_cut = PointCut(dimension, rollup_path, hierarchy=hierarchy)
            cuts.append(new_cut)

        return Cell(cube=self.cube, cuts=cuts)

    def rollup(self, rollup):
        """Rolls-up cell - goes one or more levels up through dimension
        hierarchy. It works in similar way as drill down in
        :meth:`AggregationBrowser.aggregate` but in the opposite direction (it
        is like ``cd ..`` in a UNIX shell).

        Roll-up can be:

            * a string - single dimension to be rolled up one level
            * an array - list of dimension names to be rolled-up one level
            * a dictionary where keys are dimension names and values are
              levels to be rolled up-to

        .. note::

                Only default hierarchy is currently supported.
        """

        # FIXME: rename this to something like really_complex_rollup :-)
        # Reason:
        #     * see reasons above for rollup_dim()
        #     * used only by Slicer server

        cuts = OrderedDict()
        for cut in self.cuts:
            dim = self.cube.dimension(cut.dimension)
            cuts[dim.name] = cut

        new_cuts = []

        # If it is a string, handle it as list of single string
        if isinstance(rollup, basestring):
            rollup = [rollup]

        if type(rollup) == list or type(rollup) == tuple:
            for dim_name in rollup:
                cut = cuts.get(dim_name)
                if cut is None:
                    continue
                #     raise ValueError("No cut to roll-up for dimension '%s'" % dim_name)
                if type(cut) != PointCut:
                    raise NotImplementedError("Only PointCuts are currently supported for "
                                              "roll-up (rollup dimension: %s)" % dim_name)

                dim = self.cube.dimension(cut.dimension)
                hier = dim.default_hierarchy

                rollup_path = hier.rollup(cut.path)

                cut = PointCut(cut.dimension, rollup_path)
                new_cuts.append(cut)

        elif isinstance(self.drilldown, dict):
            for (dim_name, level_name) in rollup.items():
                cut = cuts[dim_name]
                if not cut:
                    raise ArgumentError("No cut to roll-up for dimension '%s'" % dim_name)
                if type(cut) != PointCut:
                    raise NotImplementedError("Only PointCuts are currently supported for "
                                              "roll-up (rollup dimension: %s)" % dim_name)

                dim = selfcube.dimension(cut.dimension)
                hier = dim.default_hierarchy

                rollup_path = hier.rollup(cut.path, level_name)

                cut = PointCut(cut.dimension, rollup_path)
                new_cuts.append(cut)
        else:
            raise ArgumentError("Rollup is of unknown type: %s" % self.drilldown.__class__)

        cell = Cell(cube=self.cube, cuts=new_cuts)
        return cell

    def level_depths(self):
        """Returns a dictionary of dimension names as keys and level depths
        (index of deepest level)."""

        levels = {}

        for cut in self.cuts:
            level = cut.level_depth()
            dim = self.cube.dimension(cut.dimension)
            dim_name = str(dim)

            levels[dim_name] = max(level, levels.get(dim_name))

        return levels

    def deepest_levels(self, include_empty=False):
        """Returns a list of tuples: (`dimension`, `hierarchy`, `level`) where
        `level` is the deepest level specified in the respective cut. If no
        level is specified (empty path) and `include_empty` is `True`, then the
        level will be `None`. If `include_empty` is `True` then empty levels
        are not included in the result.

        This method is currently used for preparing the periods-to-date
        conditions.

        See also: :meth:`cubes.Drilldown.deepest_levels`
        """

        levels = []

        for cut in self.cuts:
            depth = cut.level_depth()
            dim = self.cube.dimension(cut.dimension)
            hier = dim.hierarchy(cut.hierarchy)
            if depth:
                item = (dim, hier, hier[depth-1])
            elif include_empty:
                item = (dim, hier, None)
            levels.append(item)

        return levels

    def is_base(self, dimension, hierarchy=None):
        """Returns ``True`` when cell is base cell for `dimension`. Cell
        is base if there is a point cut with path referring to the
        most detailed level of the dimension `hierarchy`."""

        hierarchy = dimension.hierarchy(hierarchy)
        cut = self.point_cut_for_dimension(dimension)
        if cut:
            return cut.level_depth() >= len(hierarchy)
        else:
            return False

    def contains_level(self, dim, level, hierarchy=None):
        """Returns `True` if one of the cuts contains `level` of dimension
        `dim`. If `hierarchy` is not specified, then dimension's default
        hierarchy is used."""

        dim = self.cube.dimension(dim)
        hierarchy = dim.hierarchy(hierarchy)

        for cut in self.dimension_cuts(dim):
            if str(cut.hierarchy) != str(hierarchy):
                continue
            if isinstance(cut, PointCut):
                if level in hierarchy.levels_for_path(cut.path):
                    return True
            if isinstance(cut, SetCut):
                for path in cut.paths:
                    if level in hierarchy.levels_for_path(path):
                        return True
        return False

    def dimension_cuts(self, dimension, exclude=False):
        """Returns cuts for `dimension`. If `exclude` is `True` then the
        effect is reversed: return all cuts except those with `dimension`."""
        dimension = self.cube.dimension(dimension)
        cuts = []
        for cut in self.cuts:
            cut_dimension = self.cube.dimension(cut.dimension)
            if (exclude and cut_dimension != dimension) \
                    or (not exclude and cut_dimension == dimension):
                cuts.append(cut)
        return cuts

    def public_cell(self):
        """Returns a cell that contains only non-hidden cuts. Hidden cuts are
        mostly generated cuts by a backend or an extension. Public cell is a
        cell to be presented to the front-end."""

        cuts = [cut for cut in self.cuts if not cut.hidden]

        return Cell(self.cube, cuts)

    def __eq__(self, other):
        """cells are considered equal if:
            * they refer to the same cube
            * they have same set of cuts (regardless of their order)
        """

        if self.cube != other.cube:
            return False
        elif len(self.cuts) != len(other.cuts):
            return False

        for cut in self.cuts:
            if cut not in other.cuts:
                return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def to_str(self):
        """Return string representation of the cell by using standard
        cuts-to-string conversion."""
        return string_from_cuts(self.cuts)

    def __str__(self):
        """Return string representation of the cell by using standard
        cuts-to-string conversion."""
        return string_from_cuts(self.cuts)

    def __repr__(self):
        return 'Cell(%s: %s)' % (str(self.cube), self.to_str() or 'All')

    def __nonzero__(self):
        """Returns `True` if the cell contains cuts."""
        return bool(self.cuts)

CUT_STRING_SEPARATOR_CHAR = "|"
DIMENSION_STRING_SEPARATOR_CHAR = ":"
PATH_STRING_SEPARATOR_CHAR = ","
RANGE_CUT_SEPARATOR_CHAR = "-"
SET_CUT_SEPARATOR_CHAR = ";"

CUT_STRING_SEPARATOR = re.compile(r'(?<!\\)\|')
DIMENSION_STRING_SEPARATOR = re.compile(r'(?<!\\):')
PATH_STRING_SEPARATOR = re.compile(r'(?<!\\),')
RANGE_CUT_SEPARATOR = re.compile(r'(?<!\\)-')
SET_CUT_SEPARATOR = re.compile(r'(?<!\\);')

PATH_ELEMENT = r"(?:\\.|[^:;|-])*"

RE_ELEMENT = re.compile(r"^%s$" % PATH_ELEMENT)
RE_POINT = re.compile(r"^%s$" % PATH_ELEMENT)
RE_SET = re.compile(r"^(%s)(;(%s))*$" % (PATH_ELEMENT, PATH_ELEMENT))
RE_RANGE = re.compile(r"^(%s)?-(%s)?$" % (PATH_ELEMENT, PATH_ELEMENT))

"""
point: date:2004
range: date:2004-2010
set: date:2004;2010;2011,04

"""


def cuts_from_string(cube, string, member_converters=None,
                     role_member_converters=None):
    """Return list of cuts specified in `string`. You can use this function to
    parse cuts encoded in a URL.

    Arguments:

    * `string` – string containing the cut descritption (see below)
    * `cube` – cube for which the cuts are being created
    * `member_converters` – callables converting single-item values into paths.
      Keys are dimension names.
    * `role_member_converters` – callables converting single-item values into
      paths. Keys are dimension role names (`Dimension.role`).

    Examples::

        date:2004
        date:2004,1
        date:2004,1|class=5
        date:2004,1,1|category:5,10,12|class:5

    Ranges are in form ``from-to`` with possibility of open range::

        date:2004-2010
        date:2004,5-2010,3
        date:2004,5-2010
        date:2004,5-
        date:-2010

    Sets are in form ``path1;path2;path3`` (none of the paths should be
    empty)::

        date:2004;2010
        date:2004;2005,1;2010,10

    Grammar::

        <list> ::= <cut> | <cut> '|' <list>
        <cut> ::= <dimension> ':' <path>
        <dimension> ::= <identifier>
        <path> ::= <value> | <value> ',' <path>

    The characters '|', ':' and ',' are configured in `CUT_STRING_SEPARATOR`,
    `DIMENSION_STRING_SEPARATOR`, `PATH_STRING_SEPARATOR` respectively.
    """

    if not string:
        return []

    cuts = []

    dim_cuts = CUT_STRING_SEPARATOR.split(string)
    for dim_cut in dim_cuts:
        cut = cut_from_string(dim_cut, cube, member_converters,
                              role_member_converters)
        cuts.append(cut)

    return cuts



def cut_from_string(string, cube=None, member_converters=None,
                    role_member_converters=None):
    """Returns a cut from `string` with dimension `dimension and assumed
    hierarchy `hierarchy`. The string should match one of the following
    patterns:

    * point cut: ``2010,2,4``
    * range cut: ``2010-2012``, ``2010,1-2012,3,5``, ``2010,1-`` (open range)
    * set cut: ``2010;2012``, ``2010,1;2012,3,5;2012,10``

    If the `string` does not match any of the patterns, then ArgumentError
    exception is raised.

    `dimension` can specify a hierarchy in form ``dimension@hierarchy`` such
    as ``date@dqmy``.
    """

    member_converters = member_converters or {}
    role_member_converters = role_member_converters or {}

    dim_hier_pattern = re.compile(r"(?P<invert>!)?"
                                   "(?P<dim>\w+)(@(?P<hier>\w+))?")

    try:
        (dimspec, string) = DIMENSION_STRING_SEPARATOR.split(string)
    except ValueError:
        raise ArgumentError("Wrong dimension cut string: '%s'" % string)

    match = dim_hier_pattern.match(dimspec)

    if match:
        d = match.groupdict()
        invert = (not not d["invert"])
        dimension = d["dim"]
        hierarchy = d["hier"]
    else:
        raise ArgumentError("Dimension spec '%s' does not match "
                            "pattern 'dimension@hierarchy'" % dimspec)

    converter = member_converters.get(dimension)
    if cube:
        role = cube.dimension(dimension).role
        converter = converter or role_member_converters.get(role)
        dimension = cube.dimension(dimension)
        hierarchy = dimension.hierarchy(hierarchy)

    # special case: completely empty string means single path element of ''
    # FIXME: why?
    if string == '':
        return PointCut(dimension, [''], hierarchy, invert)

    elif RE_POINT.match(string):
        path = path_from_string(string)

        if converter:
            path = converter(dimension, hierarchy, path)
        cut = PointCut(dimension, path, hierarchy, invert)

    elif RE_SET.match(string):
        paths = map(path_from_string, SET_CUT_SEPARATOR.split(string))

        if converter:
            converted = []
            for path in paths:
                converted.append(converter(dimension, hierarchy, path))
            paths = converted

        cut = SetCut(dimension, paths, hierarchy, invert)

    elif RE_RANGE.match(string):
        (from_path, to_path) = map(path_from_string, RANGE_CUT_SEPARATOR.split(string))

        if converter:
            from_path = converter(dimension, hierarchy, from_path)
            to_path = converter(dimension, hierarchy, to_path)

        cut = RangeCut(dimension, from_path, to_path, hierarchy, invert)

    else:
        raise ArgumentError("Unknown cut format (check that keys "
                            "consist only of alphanumeric characters and "
                            "underscore): %s" % string)

    return cut

def cut_from_dict(desc, cube=None):
    """Returns a cut from `desc` dictionary. If `cube` is specified, then the
    dimension is looked up in the cube and set as `Dimension` instances, if
    specified as strings."""

    cut_type = desc["type"].lower()

    dim = desc.get("dimension")

    if dim and cube:
        dim = cube.dimension(dim)

    if cut_type == "point":
        return PointCut(dim, desc.get("path"), desc.get("hierarchy"), desc.get('invert', False))
    elif cut_type == "set":
        return SetCut(dim, desc.get("paths"), desc.get("hierarchy"), desc.get('invert', False))
    elif cut_type == "range":
        return RangeCut(dim, desc.get("from"), desc.get("to"),
                        desc.get("hierarchy"), desc.get('invert', False))
    else:
        raise ArgumentError("Unknown cut type %s" % cut_type)


PATH_PART_ESCAPE_PATTERN = re.compile(r"([\\!|:;,-])")
PATH_PART_UNESCAPE_PATTERN = re.compile(r"\\([\\!|;,-])")


def _path_part_escape(path_part):
    if path_part is None:
        return NULL_PATH_VALUE
    return PATH_PART_ESCAPE_PATTERN.sub(r"\\\1", path_part)


def _path_part_unescape(path_part):
    if path_part == NULL_PATH_VALUE:
        return None
    return PATH_PART_UNESCAPE_PATTERN.sub(r"\1", path_part)


def string_from_cuts(cuts):
    """Returns a string represeting `cuts`. String can be used in URLs"""
    strings = [str(cut) for cut in cuts]
    string = CUT_STRING_SEPARATOR_CHAR.join(strings)
    return string


def string_from_path(path):
    """Returns a string representing dimension `path`. If `path` is ``None``
    or empty, then returns empty string. The ptah elements are comma ``,``
    spearated.

    Raises `ValueError` when path elements contain characters that are not
    allowed in path element (alphanumeric and underscore ``_``)."""

    if not path:
        return ""

    path = [_path_part_escape(to_unicode_string(s)) for s in path]

    if not all(map(RE_ELEMENT.match, path)):
        get_logger().warn("Can not convert path to string: "
                          "keys contain invalid characters "
                          "(should be alpha-numeric or underscore) '%s'" %
                          path)

    string = PATH_STRING_SEPARATOR_CHAR.join(path)
    return string


def string_from_hierarchy(dimension, hierarchy):
    """Returns a string in form ``dimension@hierarchy`` or ``dimension`` if
    `hierarchy` is ``None``"""
    if hierarchy:
        return "%s@%s" % (_path_part_escape(str(dimension)), _path_part_escape(str(hierarchy)))
    else:
        return _path_part_escape(str(dimension))


def path_from_string(string):
    """Returns a dimension point path from `string`. The path elements are
    separated by comma ``,`` character.

    Returns an empty list when string is empty or ``None``.
    """

    if not string:
        return []

    path = PATH_STRING_SEPARATOR.split(string)
    path = [_path_part_unescape(v) for v in path]

    return path


class Cut(object):
    def __init__(self, dimension, hierarchy=None, invert=False,
                 hidden=False):
        """Abstract class for a cell cut."""
        self.dimension = dimension
        self.hierarchy = hierarchy
        self.invert = invert
        self.hidden = hidden

    def to_dict(self):
        """Returns dictionary representation fo the receiver. The keys are:
        `dimension`."""
        d = OrderedDict()

        # Placeholder for 'type' to be at the beginning of the list
        d['type'] = None

        d["dimension"] = str(self.dimension)
        d["hierarchy"] = str(self.hierarchy) if self.hierarchy else None
        d["level_depth"] = self.level_depth()
        d["invert"] = self.invert
        d["hidden"] = self.hidden

        return d

    def level_depth(self):
        """Returns deepest level number. Subclasses should implement this
        method"""
        raise NotImplementedError

    def __repr__(self):
        return str(self.to_dict())


class PointCut(Cut):
    """Object describing way of slicing a cube (cell) through point in a
    dimension"""

    def __init__(self, dimension, path, hierarchy=None, invert=False,
                 hidden=False):
        super(PointCut, self).__init__(dimension, hierarchy, invert, hidden)
        self.path = path

    def to_dict(self):
        """Returns dictionary representation of the receiver. The keys are:
        `dimension`, `type`=``point`` and `path`."""
        d = super(PointCut, self).to_dict()
        d["type"] = "point"
        d["path"] = self.path
        return d

    def level_depth(self):
        """Returns index of deepest level."""
        return len(self.path)

    def __str__(self):
        """Return string representation of point cut, you can use it in
        URLs"""
        path_str = string_from_path(self.path)
        dim_str = string_from_hierarchy(self.dimension, self.hierarchy)
        string = ("!" if self.invert else "") + dim_str + DIMENSION_STRING_SEPARATOR_CHAR + path_str

        return string

    def __eq__(self, other):
        if not isinstance(other, PointCut):
            return False
        if self.dimension != other.dimension:
            return False
        elif self.path != other.path:
            return False
        elif self.invert != other.invert:
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)


class RangeCut(Cut):
    """Object describing way of slicing a cube (cell) between two points of a
    dimension that has ordered points. For dimensions with unordered points
    behaviour is unknown."""

    def __init__(self, dimension, from_path, to_path, hierarchy=None,
                 invert=False, hidden=False):
        super(RangeCut, self).__init__(dimension, hierarchy, invert, hidden)
        self.from_path = from_path
        self.to_path = to_path

    def to_dict(self):
        """Returns dictionary representation of the receiver. The keys are:
        `dimension`, `type`=``range``, `from` and `to` paths."""
        d = super(RangeCut, self).to_dict()
        d["type"] = "range"
        d["from"] = self.from_path
        d["to"] = self.to_path
        return d

    def level_depth(self):
        """Returns index of deepest level which is equivalent to the longest
        path."""
        if self.from_path and not self.to_path:
            return len(self.from_path)
        elif not self.from_path and self.to_path:
            return len(self.to_path)
        else:
            return max(len(self.from_path), len(self.to_path))

    def __str__(self):
        """Return string representation of point cut, you can use it in
        URLs"""
        if self.from_path:
            from_path_str = string_from_path(self.from_path)
        else:
            from_path_str = string_from_path([])

        if self.to_path:
            to_path_str = string_from_path(self.to_path)
        else:
            to_path_str = string_from_path([])

        range_str = from_path_str + RANGE_CUT_SEPARATOR_CHAR + to_path_str
        dim_str = string_from_hierarchy(self.dimension, self.hierarchy)
        string = ("!" if self.invert else "") + dim_str + DIMENSION_STRING_SEPARATOR_CHAR + range_str

        return string

    def __eq__(self, other):
        if not isinstance(other, RangeCut):
            return False
        if self.dimension != other.dimension:
            return False
        elif self.from_path != other.from_path:
            return False
        elif self.to_path != other.to_path:
            return False
        elif self.invert != other.invert:
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)


class SetCut(Cut):
    """Object describing way of slicing a cube (cell) between two points of a
    dimension that has ordered points. For dimensions with unordered points
    behaviour is unknown."""

    def __init__(self, dimension, paths, hierarchy=None, invert=False,
                 hidden=False):
        super(SetCut, self).__init__(dimension, hierarchy, invert, hidden)
        self.paths = paths

    def to_dict(self):
        """Returns dictionary representation of the receiver. The keys are:
        `dimension`, `type`=``range`` and `set` as a list of paths."""
        d = super(SetCut, self).to_dict()
        d["type"] = "set"
        d["paths"] = self.paths
        return d

    def level_depth(self):
        """Returns index of deepest level which is equivalent to the longest
        path."""
        return max([len(path) for path in self.paths])

    def __str__(self):
        """Return string representation of set cut, you can use it in URLs"""
        path_strings = []
        for path in self.paths:
            path_strings.append(string_from_path(path))

        set_string = SET_CUT_SEPARATOR_CHAR.join(path_strings)
        dim_str = string_from_hierarchy(self.dimension, self.hierarchy)
        string = ("!" if self.invert else "") + dim_str + DIMENSION_STRING_SEPARATOR_CHAR + set_string

        return string

    def __eq__(self, other):
        if not isinstance(other, SetCut):
            return False
        elif self.dimension != other.dimension:
            return False
        elif self.paths != other.paths:
            return False
        elif self.invert != other.invert:
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

TableRow = namedtuple("TableRow", ["key", "label", "path", "is_base", "record"])


class CalculatedResultIterator(object):
    """
    Iterator that decorates data items
    """
    def __init__(self, calculators, iterator):
        self.calculators = calculators
        self.iterator = iterator

    def __iter__(self):
        return self

    def next(self):
        # Apply calculators to the result record
        item = self.iterator.next()
        for calc in self.calculators:
            calc(item)
        return item


class AggregationResult(object):
    """Result of aggregation or drill down.

    Attributes:

    * `cell` – cell that this result is aggregate of
    * `summary` - dictionary of summary row fields
    * `cells` - list of cells that were drilled-down
    * `total_cell_count` - number of total cells in drill-down (after limit,
      before pagination)
    * `aggregates` – aggregate measures that were selected in aggregation
    * `remainder` - summary of remaining cells (not yet implemented)
    * `levels` – aggregation levels for dimensions that were used to drill-
      down

    .. note::

        Implementors of aggregation browsers should populate `cell`,
        `measures` and `levels` from the aggregate query.

    """
    def __init__(self, cell=None, aggregates=None, drilldown=None):
        super(AggregationResult, self).__init__()
        self.cell = cell
        self.aggregates = aggregates

        if drilldown:
            self.levels = drilldown.result_levels()
        else:
            self.levels = None

        self.summary = {}
        self._cells = []
        self.total_cell_count = None
        self.remainder = {}
        self.labels = []

        self.calculators = []

    @property
    def cells(self):
        return self._cells

    @cells.setter
    def cells(self, val):
        # decorate iterable with calcs if needed
        if self.calculators:
            val = CalculatedResultIterator(self.calculators, iter(val))
        self._cells = val

    @property
    def measures(self):
        return self.aggregates

    @measures.setter
    def measures(self, val):
        logger = get_logger()
        logger.warn("AggregationResult.measures is depreciated. Use "
                    "`aggregates`")
        return self.aggregates
        # decorate iterable with calcs if needed

    def to_dict(self):
        """Return dictionary representation of the aggregation result. Can be
        used for JSON serialisation."""

        d = IgnoringDictionary()

        d["summary"] = self.summary
        d["remainder"] = self.remainder
        d["cells"] = self.cells
        d["total_cell_count"] = self.total_cell_count

        d["aggregates"] = [str(m) for m in self.aggregates]

        # We want to set None
        d.set("cell", [cut.to_dict() for cut in self.cell.cuts])

        d["levels"] = self.levels

        return d

    def has_dimension(self, dimension):
        """Returns `True` if the result was drilled down by `dimension` (at
        any level)"""

        if not self.levels:
            return False

        return str(dimension) in self.levels

    def table_rows(self, dimension, depth=None, hierarchy=None):
        """Returns iterator of drilled-down rows which yields a named tuple with
        named attributes: (key, label, path, record). `depth` is last level of
        interest. If not specified (set to ``None``) then deepest level for
        `dimension` is used.

        * `key`: value of key dimension attribute at level of interest
        * `label`: value of label dimension attribute at level of interest
        * `path`: full path for the drilled-down cell
        * `is_base`: ``True`` when dimension element is base (can not drill
          down more)
        * `record`: all drill-down attributes of the cell

        Example use::

            for row in result.table_rows(dimension):
                print "%s: %s" % (row.label, row.record["fact_count"])

        `dimension` has to be :class:`cubes.Dimension` object. Raises
        `TypeError` when cut for `dimension` is not `PointCut`.
        """

        cut = self.cell.point_cut_for_dimension(dimension)

        path = cut.path if cut else []

        # FIXME: use hierarchy from cut (when implemented)
        dimension = self.cell.cube.dimension(dimension)
        hierarchy = dimension.hierarchy(hierarchy)

        if self.levels:
            # Convert "levels" to a dictionary:
            # all_levels = dict((dim, levels) for dim, levels in self.levels)
            dim_levels = self.levels.get(str(dimension), [])
            is_base = len(dim_levels) >= len(hierarchy)
        else:
            is_base = len(hierarchy) == 1

        if depth:
            current_level = hierarchy[depth - 1]
        else:
            levels = hierarchy.levels_for_path(path, drilldown=True)
            current_level = levels[-1]

        level_key = current_level.key.ref()
        level_label = current_level.label_attribute.ref()

        for record in self.cells:
            drill_path = path[:] + [record[level_key]]

            row = TableRow(record[level_key],
                           record[level_label],
                           drill_path,
                           is_base,
                           record)
            yield row

    def __iter__(self):
        """Return cells as iterator"""
        return iter(self.cells)

    def cached(self):
        """Return shallow copy of the receiver with cached cells. If cells are
        an iterator, they are all fetched in a list.

        .. warning::

            This might be expensive for large results.
        """

        result = AggregationResult()
        result.cell = self.cell
        result.aggregates = self.aggregates
        result.levels = self.levels
        result.summary = self.summary
        result.total_cell_count = self.total_cell_count
        result.remainder = self.remainder

        # Cache cells from an iterator
        result.cells = list(self.cells)
        return result

CrossTable = namedtuple("CrossTable", ["columns", "rows", "data"])


def cross_table(drilldown, onrows, oncolumns, aggregates):
    """
    Creates a cross table from a drilldown (might be any list of records).
    `onrows` contains list of attribute names to be placed at rows and
    `oncolumns` contains list of attribute names to be placet at columns.
    `aggregates` is a list of aggregate measures to be put into cells.

    Returns a named tuble with attributes:

    * `columns` - labels of columns. The tuples correspond to values of
      attributes in `oncolumns`.
    * `rows` - labels of rows as list of tuples. The tuples correspond to
      values of attributes in `onrows`.
    * `data` - list of aggregated measure data per row. Each row is a list of
      aggregate measure tuples.

    .. warning::

        Experimental implementation. Interface might change - either
        arguments or result object.

    """

    logger = get_logger()
    logger.warn("cross_table() is depreciated, use cross table formatter: "
                "create_formatter(\"cross_table\", ...)")
    matrix = {}
    row_hdrs = []
    column_hdrs = []

    for record in drilldown:
        hrow = tuple(record[f] for f in onrows)
        hcol = tuple(record[f] for f in oncolumns)

        if not hrow in row_hdrs:
            row_hdrs.append(hrow)
        if not hcol in column_hdrs:
            column_hdrs.append(hcol)

        matrix[(hrow, hcol)] = tuple(record[m] for m in aggregates)

    data = []
    for hrow in row_hdrs:
        row = [matrix.get((hrow, hcol)) for hcol in column_hdrs]
        data.append(row)

    return CrossTable(column_hdrs, row_hdrs, data)


def string_to_drilldown(astring):
    """Converts `astring` into a drilldown tuple (`dimension`, `hierarchy`,
    `level`). The string should have a format:
    ``dimension@hierarchy:level``. Hierarchy and level are optional.

    Raises `ArgumentError` when `astring` does not match expected pattern.
    """

    if not astring:
        raise ArgumentError("Drilldown string should not be empty")

    ident = r"[\w\d_]"
    pattern = r"(?P<dim>%s+)(@(?P<hier>%s+))?(:(?P<level>%s+))?" % (ident,
                                                                    ident,
                                                                    ident)
    match = re.match(pattern, astring)

    if match:
        d = match.groupdict()
        return (d["dim"], d["hier"], d["level"])
    else:
        raise ArgumentError("String '%s' does not match drilldown level "
                            "pattern 'dimension@hierarchy:level'" % astring)


class Drilldown(object):
    def __init__(self, drilldown=None, cell=None):
        """Creates a drilldown object for `drilldown` specifictation of `cell`.
        The drilldown object can be used by browsers for convenient access to
        various drilldown properties.

        Attributes:

        * `drilldown` – list of drilldown items (named tuples) with attributes:
           `dimension`, `hierarchy`, `levels` and `keys`
        * `dimensions` – list of dimensions used in this drilldown

        The `Drilldown` object can be accessed by item index ``drilldown[0]``
        or dimension name ``drilldown["date"]``. Iterating the object yields
        all drilldown items.
        """
        self.drilldown = levels_from_drilldown(cell, drilldown)
        self.dimensions = []
        self._contained_dimensions = set()

        for dd in self.drilldown:
            self.dimensions.append(dd.dimension)
            self._contained_dimensions.add(dd.dimension.name)

    def __str__(self):
        return ",".join(self.items_as_strings())

    def items_as_strings(self):
        """Returns drilldown items as strings: ``dimension@hierarchy:level``.
        If hierarchy is dimension's default hierarchy, then it is not included
        in the string: ``dimension:level``"""

        strings = []

        for item in self.drilldown:
            if item.hierarchy != item.dimension.hierarchy():
                hierstr = "@%s" % str(item.hierarchy)
            else:
                hierstr = ""

            ddstr = "%s%s:%s" % (item.dimension.name,
                                 hierstr,
                                 item.levels[-1].name)
            strings.append(ddstr)

        return strings

    def drilldown_for_dimension(self, dim):
        """Returns drilldown items for dimension `dim`."""
        items = []
        dimname = str(dim)
        for item in self.drilldown:
            if str(item.dimension) == dimname:
                items.append(item)

        return items

    def __getitem__(self, key):
        return self.drilldown[key]

    def deepest_levels(self):
        """Returns a list of tuples: (`dimension`, `hierarchy`, `level`) where
        `level` is the deepest level drilled down to.

        This method is currently used for preparing the periods-to-date
        conditions.

        See also: :meth:`cubes.Cell.deepest_levels`
        """

        levels = []

        for dditem in self.drilldown:
            item = (dditem.dimension, dditem.hierarchy, dditem.levels[-1])
            levels.append(item)

        return levels

        return levels

    def high_cardinality_levels(self, cell):
        """Returns list of levels in the drilldown that are of high
        cardinality and there is no cut for that level in the `cell`."""

        for item in self.drilldown:
            dim, hier, levels = item[0:3]
            not_contained = []

            for level in item.levels:
                if (level.cardinality == "high" or dim.cardinality == "high") \
                        and not cell.contains_level(dim, level, hier):
                    not_contained.append(level)

            if not_contained:
                return not_contained

        return []

    def result_levels(self, include_split=False):
        """Returns a dictionary where keys are dimension names and values are
        list of level names for the drilldown. Use this method to populate the
        result levels attribute.

        If `include_split` is `True` then split dimension is included."""
        result = {}

        for item in self.drilldown:
            dim, hier, levels = item[0:3]

            if dim.hierarchy().name == hier.name:
                dim_key = dim.name
            else:
                dim_key = "%s@%s" % (dim.name, hier.name)

            result[dim_key] = [str(level) for level in levels]

        if include_split:
            result[SPLIT_DIMENSION_NAME] = [SPLIT_DIMENSION_NAME]

        return result

    def all_attributes(self):
        """Returns attributes of all levels in the drilldown. Order is by the
        drilldown item, then by the levels and finally by the attribute in the
        level."""
        attributes = []
        for item in self.drilldown:
            for level in item.levels:
                attributes += level.attributes

        return attributes

    def has_dimension(self, dim):
        return str(dim) in self._contained_dimensions

    def __len__(self):
        return len(self.drilldown)

    def __iter__(self):
        return self.drilldown.__iter__()

    def __nonzero__(self):
        return len(self.drilldown) > 0

DrilldownItem = namedtuple("DrilldownItem",
                           ["dimension", "hierarchy", "levels", "keys"])


# TODO: move this to Drilldown
def levels_from_drilldown(cell, drilldown, simplify=True):
    """Converts `drilldown` into a list of levels to be used to drill down.
    `drilldown` can be:

    * list of dimensions
    * list of dimension level specifier strings
    * (``dimension@hierarchy:level``) list of tuples in form (`dimension`,
      `hierarchy`, `levels`, `keys`).

    If `drilldown is a list of dimensions or if the level is not specified,
    then next level in the cell is considered. The implicit next level is
    determined from a `PointCut` for `dimension` in the `cell`.

    For other types of cuts, such as range or set, "next" level is the first
    level of hierarachy.

    If `simplify` is `True` then dimension references are simplified for flat
    dimensions without details. Otherwise full dimension attribute reference
    will be used as `level_key`.

    Returns a list of drilldown items with attributes: `dimension`,
    `hierarchy` and `levels` where `levels` is a list of levels to be drilled
    down.
    """

    if not drilldown:
        return []

    result = []

    # If the drilldown is a list, convert it into a dictionary
    if isinstance(drilldown, dict):
        logger = get_logger()
        logger.warn("drilldown as dictionary is depreciated. Use a list of: "
                    "(dim, hierarchy, level) instead")
        drilldown = [(dim, None, level) for dim, level in drilldown.items()]

    for obj in drilldown:
        if isinstance(obj, basestring):
            obj = string_to_drilldown(obj)
        elif isinstance(obj, DrilldownItem):
            obj = (obj.dimension, obj.hierarchy, obj.levels[-1])
        elif len(obj) != 3:
            raise ArgumentError("Drilldown item should be either a string "
                                "or a tuple of three elements. Is: %s" %
                                (obj, ))

        dim, hier, level = obj
        dim = cell.cube.dimension(dim)

        hier = dim.hierarchy(hier)

        if level:
            index = hier.level_index(level)
            levels = hier[:index + 1]
        elif dim.is_flat:
            levels = hier[:]
        else:
            cut = cell.point_cut_for_dimension(dim)
            if cut:
                cut_hierarchy = dim.hierarchy(cut.hierarchy)
                depth = cut.level_depth()
                # inverted cut means not to auto-drill to the next level
                if cut.invert:
                    depth -= 1
                # a flat dimension means not to auto-drill to the next level
            else:
                cut_hierarchy = hier
                depth = 0

            if cut_hierarchy != hier:
                raise HierarchyError("Cut hierarchy %s for dimension %s is "
                                     "different than drilldown hierarchy %s. "
                                     "Can not determine implicit next level."
                                     % (hier, dim, cut_hierarchy))

            if depth >= len(hier):
                raise HierarchyError("Hierarchy %s in dimension %s has only "
                                     "%d levels, can not drill to %d" %
                                     (hier, dim, len(hier), depth + 1))

            levels = hier[:depth + 1]

        levels = tuple(levels)
        keys = [level.key.ref(simplify=simplify) for level in levels]
        result.append(DrilldownItem(dim, hier, levels, keys))

    return result


########NEW FILE########
__FILENAME__ = calendar
# -*- coding: utf-8 -*-
"""Date and time utilities."""

import re
from dateutil.relativedelta import relativedelta
from dateutil.relativedelta import MO, TU, WE, TH, FR, SA, SU
from dateutil.tz import *
from datetime import datetime, timedelta
from time import strftime, gmtime

from .model import Hierarchy
from .errors import *


__all__ = (
    "Calendar",
    "calendar_hierarchy_units"
)


_CALENDAR_UNITS = ["year", "quarter", "month", "day", "hour", "minute",
                    "weekday"]


UNIT_YEAR = 8
UNIT_QUARTER = 7
UNIT_MONTH = 6
UNIT_WEEK = 5
UNIT_DAY = 4
UNIT_HOUR = 3
UNIT_MINUTE = 2
UNIT_SECOND = 1


_UNIT_ORDER = {
    "year": UNIT_YEAR,
    "quarter": UNIT_QUARTER,
    "month": UNIT_MONTH,
    "week": UNIT_WEEK,
    "day": UNIT_DAY,
    "hour": UNIT_HOUR,
    "minute": UNIT_MINUTE,
    "second": UNIT_SECOND
}

_DATEUTIL_WEEKDAYS = { 0: MO, 1: TU, 2: WE, 3: TH, 4: FR, 5: SA, 6: SU }

_WEEKDAY_NUMBERS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6
}

RELATIVE_FINE_TIME_RX = re.compile(r"(?P<offset>\d+)?"
                                    "(?P<unit>\w+)"
                                    "(?P<direction>(ago|forward))")


RELATIVE_TRUNCATED_TIME_RX = re.compile(r"(?P<direction>(last|next))"
                                         "(?P<offset>\d+)?"
                                         "(?P<unit>\w+)")

month_to_quarter = lambda month: ((month - 1) / 3) + 1


def calendar_hierarchy_units(hierarchy):
    """Return time units for levels in the hierarchy. The hierarchy is
    expected to be a date/time hierarchy and every level should have a `role`
    property specified. If the role is not specified, then the role is
    determined from the level name.

    Roles/units: `year`, `quarter`, `month`, `day`, `hour`, `minute`,
    `weekday`

    If unknown role is encountered an exception is raised."""

    units = []

    for level in hierarchy.levels:
        role = level.role or level.name

        if role in _CALENDAR_UNITS:
            units.append(role)
        else:
            raise ArgumentError("Unknown time role '%s' for level '%s'"
                                % (role, str(level)))

    return units


def add_time_units(time, unit, amount):
    """Subtract `amount` number of `unit`s from datetime object `time`."""

    args = {}
    if unit == 'hour':
        args['hours'] = amount
    elif unit == 'day':
        args['days'] = amount
    elif unit == 'week':
        args['days'] = amount * 7
    elif unit == 'month':
        args['months'] = amount
    elif unit == 'quarter':
        args['months'] = amount * 3
    elif unit == 'year':
        args['years'] = amount
    else:
        raise ArgumentError("Unknown unit %s for subtraction.")

    return time + relativedelta(**args)


class Calendar(object):
    def __init__(self, first_weekday=0, timezone=None):
        """Creates a Calendar object for providing date/time paths and for
        relative date/time manipulation.

        Values for `first_weekday` are 0 for Monday, 6 for Sunday. Default is
        0."""

        if isinstance(first_weekday, basestring):
            try:
                self.first_weekday = _WEEKDAY_NUMBERS[first_weekday.lower()]
            except KeyError:
                raise ConfigurationError("Unknown weekday name %s" %
                                         first_weekday)
        else:
            value = int(first_weekday)
            if value < 0 or value >= 7:
                raise ConfigurationError("Invalid weekday number %s" %
                                         value)
            self.first_weekday = int(first_weekday)

        if timezone:
            self.timezone_name = timezone
            self.timezone = gettz(timezone) or tzstr(timezone)
        else:
            self.timezone_name = datetime.now(tzlocal()).tzname()
            self.timezone = tzlocal()

    def now(self):
        """Returns current date in the calendar's timezone."""
        return datetime.now(self.timezone)

    def path(self, time, units):
        """Returns a path from `time` containing date/time `units`. `units`
        can be a list of strings or a `Hierarchy` object."""

        if not units:
            return []

        if isinstance(units, Hierarchy):
            units = calendar_hierarchy_units(units)

        path = []

        for unit in units:
            if unit in ("year", "month", "day", "hour", "minute"):
                value = getattr(time, unit)
            elif unit == "quarter":
                value = month_to_quarter(time.month)
            elif unit == "weekday":
                value = (time.weekday() - self.first_weekday) % 7
            else:
                raise ArgumentError("Unknown calendar unit '%s'" % (unit, ))
            path.append(value)

        return path

    def now_path(self, units):
        """Returns a path representing current date and time with `units` as
        path items."""

        return self.path(self.now(), units)

    def truncate_time(self, time, unit):
        """Truncates the `time` to calendar unit `unit`. Consider week start
        day from the calendar."""

        unit_order = _UNIT_ORDER[unit]

        # Seconds are our finest granularity
        time = time.replace(microsecond=0)

        if unit_order > UNIT_MINUTE:
            time = time.replace(minute=0, second=0)
        elif unit_order > UNIT_SECOND:
            time = time.replace(second=0)

        if unit == 'hour':
            pass

        elif unit == 'day':
            time = time.replace(hour=0)

        elif unit == 'week':
            time = time.replace(hour=0)

            weekday = _DATEUTIL_WEEKDAYS[self.first_weekday]
            time = time + relativedelta(days=-6, weekday=weekday)

        elif unit == 'month':
            time = time.replace(day=1, hour=0)

        elif unit == 'quarter':
            month = (month_to_quarter(time.month) - 1) * 3 + 1
            time = time.replace(month=month, day=1, hour=0)

        elif unit == 'year':
            time = time.replace(month=1, day=1, hour=0)

        else:
            raise ValueError("Unrecognized unit: %s" % unit)

        return time

    def since_period_start(self, period, unit, time=None):
        """Returns distance between `time` and the nearest `period` start
        relative to `time` in `unit` units. For example: distance between
        today and start of this year."""

        if not time:
            time = self.now()

        start = self.truncate_time(time, period)
        diff = time - start

        if unit == "day":
            return diff.days
        elif unit == "hour":
            return diff.days * 24 + (diff.seconds / 3600)
        elif unit == "minute":
            return diff.days * 1440 + (diff.seconds / 60)
        elif unit == "second":
            return diff.days * 86400 + diff.seconds
        else:
            raise ValueError("Unrecognized period unit: %s" % unit)

    def named_relative_path(self, reference, units, date=None):
        """"""

        date = date or self.now()

        truncate = False
        relative_match = RELATIVE_FINE_TIME_RX.match(reference)
        if not relative_match:
            truncate = True
            relative_match = RELATIVE_TRUNCATED_TIME_RX.match(reference)

        if reference == "today":
            pass

        elif reference == "yesterday":
            date = date - relativedelta(days=1)

        elif reference == "tomorrow":
            date = date + relativedelta(days=1)

        elif relative_match:
            offset = relative_match.group("offset")
            if offset:
                try:
                    offset = int(offset)
                except ValueError:
                    raise ArgumentError("Relative time offset should be a "
                                        "number")
            else:
                offset = 1

            unit = relative_match.group("unit")
            if unit.endswith("s"):
                unit = unit[:-1]

            direction = relative_match.group("direction")

            if direction in ("ago", "last"):
                offset = -offset

            if truncate:
                date = self.truncate_time(date, unit)

            date = add_time_units(date, unit, offset)

        else:
            # TODO: UNITstart, UNITend
            raise ValueError(reference)

        return self.path(date, units)


class CalendarMemberConverter(object):
    def __init__(self, calendar):
        self.calendar = calendar

    def __call__(self, dimension, hierarchy, path):
        if len(path) != 1:
            return path

        units = hierarchy.level_names
        value = path[0]
        try:
            path = self.calendar.named_relative_path(value, units)
        except ValueError:
            return [value]

        return path


########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-

"""Utility functions for computing combinations of dimensions and hierarchy
levels"""

import itertools
import sys
import re
from collections import OrderedDict
import exceptions
import os.path
import json

from .errors import *

__all__ = [
    "IgnoringDictionary",
    "MissingPackage",
    "localize_common",
    "localize_attributes",
    "get_localizable_attributes",
    "decamelize",
    "to_identifier",
    "assert_instance",
    "assert_all_instances",
    "read_json_file",
    "sorted_dependencies"
]

class IgnoringDictionary(OrderedDict):
    """Simple dictionary extension that will ignore any keys of which values
    are empty (None/False)"""
    def __setitem__(self, key, value):
        if value is not None:
            super(IgnoringDictionary, self).__setitem__(key, value)

    def set(self, key, value):
        """Sets `value` for `key` even if value is null."""
        super(IgnoringDictionary, self).__setitem__(key, value)

    def __repr__(self):
        items = []
        for key, value in self.items():
            item = '%s: %s' % (repr(key), repr(value))
            items.append(item)

        return "{%s}" % ", ".join(items)

def assert_instance(obj, class_, label):
    """Raises ArgumentError when `obj` is not instance of `cls`"""
    if not isinstance(obj, class_):
        raise ModelInconsistencyError("%s should be sublcass of %s, "
                                      "provided: %s" % (label,
                                                        class_.__name__,
                                                        type(obj).__name__))


def assert_all_instances(list_, class_, label="object"):
    """Raises ArgumentError when objects in `list_` are not instances of
    `cls`"""
    for obj in list_ or []:
        assert_instance(obj, class_, label="object")


class MissingPackageError(Exception):
    """Exception raised when encountered a missing package."""
    pass

class MissingPackage(object):
    """Bogus class to handle missing optional packages - packages that are not
    necessarily required for Cubes, but are needed for certain features."""

    def __init__(self, package, feature = None, source = None, comment = None):
        self.package = package
        self.feature = feature
        self.source = source
        self.comment = comment

    def __call__(self, *args, **kwargs):
        self._fail()

    def __getattr__(self, name):
        self._fail()

    def _fail(self):
        if self.feature:
            use = " to be able to use: %s" % self.feature
        else:
            use = ""

        if self.source:
            source = " from %s" % self.source
        else:
            source = ""

        if self.comment:
            comment = ". %s" % self.comment
        else:
            comment = ""

        raise MissingPackageError("Optional package '%s' is not installed. "
                                  "Please install the package%s%s%s" %
                                      (self.package, source, use, comment))


def expand_dictionary(record, separator = '.'):
    """Return expanded dictionary: treat keys are paths separated by
    `separator`, create sub-dictionaries as necessary"""

    result = {}
    for key, value in record.items():
        current = result
        path = key.split(separator)
        for part in path[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[path[-1]] = value
    return result

def localize_common(obj, trans):
    """Localize common attributes: label and description"""

    if "label" in trans:
        obj.label = trans["label"]
    if "description" in trans:
        obj.description = trans["description"]

def localize_attributes(attribs, translations):
    """Localize list of attributes. `translations` should be a dictionary with
    keys as attribute names, values are dictionaries with localizable
    attribute metadata, such as ``label`` or ``description``."""

    for (name, atrans) in translations.items():
        attrib = attribs[name]
        localize_common(attrib, atrans)

def get_localizable_attributes(obj):
    """Returns a dictionary with localizable attributes of `obj`."""

    # FIXME: use some kind of class attribute to get list of localizable attributes

    locale = {}
    try:
        if obj.label:
            locale["label"] = obj.label
    except:
        pass

    try:
        if obj.description:
                locale["description"] = obj.description
    except:
        pass
    return locale


def decamelize(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1)


def to_identifier(name):
    return re.sub(r' ', r'_', name).lower()


def to_label(name, capitalize=True):
    """Converts `name` into label by replacing underscores by spaces. If
    `capitalize` is ``True`` (default) then the first letter of the label is
    capitalized."""

    label = name.replace("_", " ")
    if capitalize:
        label = label.capitalize()

    return label


def coalesce_option_value(value, value_type, label=None):
    """Convert string into an object value of `value_type`. The type might be:
        `string` (no conversion), `integer`, `float`, `list` – comma separated
        list of strings.
    """
    value_type = value_type.lower()

    try:
        if value_type in ('string', 'str'):
            return_value = str(value)
        elif value_type == 'list':
            if isinstance(value, basestring):
                return_value = value.split(",")
            else:
                return_value = list(value)
        elif value_type == "float":
            return_value = float(value)
        elif value_type in ["integer", "int"]:
            return_value = int(value)
        elif value_type in ["bool", "boolean"]:
            if not value:
                return_value = False
            elif isinstance(value, basestring):
                return_value = value.lower() in ["1", "true", "yes", "on"]
            else:
                return_value = bool(value)
        else:
            raise ArgumentError("Unknown option value type %s" % value_type)

    except ValueError:
        if label:
            label = "parameter %s " % label
        else:
            label = ""

        raise ArgumentError("Unable to convert %svalue '%s' into type %s" %
                                                (label, astring, value_type))
    return return_value

def coalesce_options(options, types):
    """Coalesce `options` dictionary according to types dictionary. Keys in
    `types` refer to keys in `options`, values of `types` are value types:
    string, list, float, integer or bool."""

    out = {}

    for key, value in options.items():
        if key in types:
            out[key] = coalesce_option_value(value, types[key], key)
        else:
            out[key] = value

    return out

def to_unicode_string(s):
    s = str(s)
    for enc in ('utf8', 'latin-1'):
        try:
            return unicode(s, enc)
        except exceptions.UnicodeDecodeError:
            get_logger().info("Cannot decode using %s: %s" % (enc, s))
    raise ValueError("Cannot decode for unicode using any of the available encodings: %s" % s)

def read_json_file(path, kind=None):
    """Read a JSON from `path`. This is convenience function that provides
    more descriptive exception handling."""

    kind = "%s " % str(kind) if kind else ""

    if not os.path.exists(path):
         raise ConfigurationError("Can not find %sfile '%s'"
                                 % (kind, path))

    try:
        f = open(path)
    except IOError:
        raise ConfigurationError("Can not open %sfile '%s'"
                                 % (kind, path))

    try:
        content = json.load(f)
    except ValueError as e:
        raise SyntaxError("Syntax error in %sfile %s: %s"
                          % (kind, path, str(e)))
    finally:
        f.close()

    return content


def sorted_dependencies(graph):
    """Return keys from `deps` ordered by dependency (topological sort).
    `deps` is a dictionary where keys are strings and values are list of
    strings where keys is assumed to be dependant on values.

    Example::

        A ---> B -+--> C
                  |
                  +--> D --> E

    Will be: ``{"A": ["B"], "B": ["C", "D"], "D": ["E"],"E": []}``
    """

    graph = dict((key, set(value)) for key, value in graph.items())

    # L ← Empty list that will contain the sorted elements
    L = []

    # S ← Set of all nodes with no dependencies (incoming edges)
    S = set(parent for parent, req in graph.items() if not req)

    while S:
        # remove a node n from S
        n = S.pop()
        # insert n into L
        L.append(n)

        # for each node m with an edge e from n to m do
        #                         (n that depends on m)
        parents = [parent for parent, req in graph.items() if n in req]

        for parent in parents:
            graph[parent].remove(n)
            # remove edge e from the graph
            # if m has no other incoming edges then insert m into S
            if not graph[parent]:
                S.add(parent)

    # if graph has edges then -> error
    nonempty = [k for k, v in graph.items() if v]

    if nonempty:
        raise ArgumentError("Cyclic dependency of: %s"
                            % ", ".join(nonempty))
    return L


########NEW FILE########
__FILENAME__ = computation
# -*- coding: utf-8 -*-

from cubes.errors import *
import itertools

__all__ = [
        "combined_cuboids",
        "combined_levels",
        "hierarchical_cuboids"
        ]

def combined_cuboids(dimensions, required=None):
    """Returns a list of all combinations of `dimensions` as tuples. For
    example, if `dimensions` is: ``['date', 'product']`` then it returns:

        ``[['date', 'cpv'], ['date'], ['cpv']]``
    """

    required = tuple(required) if required else ()

    for dim in required:
        if dim not in dimensions:
            raise ArgumentError("Required dimension '%s' is not in list of "
                                "dimensions to be combined." % str(dim))

    cuboids = []
    to_combine = [dim for dim in dimensions if not dim in required]

    for i in range(len(to_combine), 0, -1):
        combos = itertools.combinations(to_combine, i)
        combos = [required+combo for combo in combos]

        cuboids += tuple(combos)

    if required:
        cuboids = [required] + cuboids

    return cuboids

def combined_levels(dimensions, default_only=False):
    """Create a cartesian product of levels from all `dimensions`. For
    example, if dimensions are _date_, _product_ then result will be:
    levels of _date_ X levels of _product_. Each element of the returned list
    is a list of tuples (`dimension`, `level`)
    """
    groups = []
    for dim in dimensions:
        if default_only:
            levels = dim.hierarchy().levels
        else:
            levels = dim.levels

        group = [(str(dim), str(level)) for level in levels]
        groups.append(group)

    return tuple(itertools.product(*groups))


def hierarchical_cuboids(dimensions, required=None, default_only=False):
    """Returns a list of cuboids with all hierarchical level combinations."""
    cuboids = combined_cuboids(dimensions, required)

    result = []
    for cuboid in cuboids:
        result += list(combined_levels(cuboid, default_only))

    return result


########NEW FILE########
__FILENAME__ = errors
# -*- coding: utf-8 -*-
"""Exceptions used in Cubes.

The base exception calss is :class:`.CubesError`."""

from collections import OrderedDict

class CubesError(Exception):
    """Generic error class."""

class UserError(CubesError):
    """Superclass for all errors caused by the cubes and slicer users. Error
    messages from this error might be safely passed to the front-end. Do not
    include any information that you would not like to be public"""
    error_type = "unknown_user_error"

class InternalError(CubesError):
    """Superclass for all errors that happened internally: configuration
    issues, connection problems, model inconsistencies..."""
    error_type = "internal_error"

class ConfigurationError(InternalError):
    """Raised when there is a problem with workspace configuration assumed."""

class BackendError(InternalError):
    """Raised by a backend. Should be handled separately, for example: should
    not be passed to the client from the server due to possible internal
    schema exposure.
    """

class WorkspaceError(InternalError):
    """Backend Workspace related exception."""

class BrowserError(InternalError):
    """AggregationBrowser related exception."""
    pass

class ModelError(InternalError):
    """Model related exception."""

# TODO: necessary? or rename to PhysicalModelError
class MappingError(ModelError):
    """Raised when there are issues by mapping from logical model to physical
    database schema. """


# TODO: change all instances to ModelError
class ModelInconsistencyError(ModelError):
    """Raised when there is incosistency in model structure."""

class TemplateRequired(ModelError):
    """Raised by a model provider which can provide a dimension, but requires
    a template. Signals to the caller that the creation of a dimension should
    be retried when the template is available."""

    def __init__(self, template):
        self.template = template
    def __str__(self):
        return self.template

class MissingObjectError(UserError):
    error_type = "missing_object"
    object_type = None

    def __init__(self, message=None, name=None):
        self.message = message
        self.name = name

    def __str__(self):
        return self.message or self.name

    def to_dict(self):
        d = OrderedDict()
        d["object"] = self.name
        d["message"] = self.message
        if self.object_type:
            d["object_type"] = self.object_type

        return d

class NoSuchDimensionError(MissingObjectError):
    """Raised when an unknown dimension is requested."""
    object_type = "dimension"

class NoSuchCubeError(MissingObjectError):
    """Raised when an unknown cube is requested."""
    object_type = "cube"

class NoSuchAttributeError(UserError):
    """Raised when an unknown attribute, measure or detail requested."""
    object_type = "attribute"

class ArgumentError(UserError):
    """Raised when an invalid or conflicting function argument is supplied.
    """

class HierarchyError(UserError):
    """Raised when attemt to get level deeper than deepest level in a
    hierarchy"""
    error_type = "hierarchy"

class ExpressionError(ModelError):
    """Raised when attribute expression is invalid.
    """


########NEW FILE########
__FILENAME__ = expr
# -*- coding: utf-8 -*-

from .errors import ExpressionError

__all__ = [
    "evaluate_expression"
]


def evaluate_expression(expression, context=None, role='expr', expected=None):
    compiled_expr = compile(expression, ('__%s__' % role), 'eval')
    context = context or {}

    result = eval(compiled_expr, context)

    if expected is not None and not isinstance(result, expected):
        raise ExpressionError("Cannot evaluate a %s object from "
                              "reference's %s expression: %r"
                              % (expected, role, expression))
    return result

########NEW FILE########
__FILENAME__ = extensions
# -*- coding: utf-8 -*-
from .common import decamelize, to_identifier, coalesce_options
from .errors import *
from collections import defaultdict


# Known extension types.
# Keys:
#     base: extension base class name
#     suffix: extension class suffix to be removed for default name (same as
#         base class nameif not specified)
#     modules: a dictionary of extension names and module name to be loaded
#         laily

_default_modules = {
    "store": {
        "sql":"cubes.backends.sql.store",
        "mongo":"cubes.backends.mongo",
        "mixpanel":"cubes.backends.mixpanel.store",
        "slicer":"cubes.backends.slicer.store",
        "ga":"cubes.backends.ga.store",
    },
    "browser": {
        "snowflake":"cubes.backends.sql.browser",
        "snapshot": "cubes.backends.sql.browser",
        "mixpanel":"cubes.backends.mixpanel.browser",
        "slicer":"cubes.backends.slicer.browser",
        "ga":"cubes.backends.ga.browser",
    },
    "model_provider": {
        "mixpanel":"cubes.backends.mixpanel.store",
        "slicer":"cubes.backends.slicer.store",
        "ga":"cubes.backends.ga.store",
    },
    "request_log_handler": {
        "sql":"cubes.backends.sql.logging",
    },
}

_extension_bases = {
    "store": "Store",
    "model_provider": "ModelProvider",
    "browser": "AggregationBrowser",
    "authorizer": "Authorizer",
    "authenticator": "Authenticator",
    "request_log_handler": "RequestLogHandler",
}

_base_modules = {
    "store": "cubes.stores",
    "model_provider": "cubes.providers",
    "browser": "cubes.browser",
    "authorizer": "cubes.auth",
    "authenticator": "cubes.server.auth",
    "request_log_handler": "cubes.server.logging",
    "formatter": "cubes.formatters",
}

class Extensible(object):
    """For now just an extension superclass to find it's subclasses."""

    """Extension type, such as `store` or `browser`. Default is derived
    from the extension root class name."""
    __extension_type__ = None

    """Class name suffix to be stripped to get extension's base name. Default
    is the root class name"""
    __extension_suffix__ = None

    """Extension name, such as `sql`. Default is derived from the extension
    class name."""
    __extension_name__ = None
    __extension_aliases__ = []

    """List of extension options.  The options is a list of dictionaries with
    keys:

    * `name` – option name
    * `type` – option data type (default is ``string``)
    * `description` – description (optional)
    * `label` – human readable label (optional)
    * `values` – valid values for the option.
    """
    __options__ = None

class ExtensionsFactory(object):
    def __init__(self, root):
        """Creates an extension factory for extension root class `root`."""
        self.root = root
        name = root.__name__

        # Get extension collection name, such as 'stores', 'browsers', ...
        self.name = root.__extension_type__
        if not self.name:
            self.name = to_identifier(decamelize(name))

        self.suffix = root.__extension_suffix__
        if not self.suffix:
            self.suffix = name


        self.options = {}
        self.option_types = {}

        self.extensions = {}

        for option in root.__options__ or []:
            name = option["name"]
            self.options[name] = option
            self.option_types[name] = option.get("type", "string")

    def __call__(self, _extension_name, *args, **kwargs):
        return self.create(_extension_name, *args, **kwargs)

    def create(self, _extension_name, *args, **kwargs):
        """Creates an extension. First argument should be extension's name."""
        extension = self.get(_extension_name)

        option_types = dict(self.option_types)
        for option in extension.__options__ or []:
            name = option["name"]
            option_types[name] = option.get("type", "string")

        kwargs = coalesce_options(dict(kwargs), option_types)

        return extension(*args, **kwargs)


    def get(self, name):
        if name in self.extensions:
            return self.extensions[name]

        # Load module...
        modules = _default_modules.get(self.name)
        if modules and name in modules:
            # TODO don't load module twice (once for manager once here)
            _load_module(modules[name])

        self.discover()

        try:
            return self.extensions[name]
        except KeyError:
            raise ConfigurationError("Unknown extension '%s' of type %s"
                                     % (name, self.name))

    def discover(self):
        extensions = collect_subclasses(self.root, self.suffix)
        self.extensions.update(extensions)

        aliases = {}
        for name, ext in extensions.items():
            if ext.__extension_aliases__:
                for alias in ext.__extension_aliases__:
                    aliases[alias] = ext

        self.extensions.update(aliases)


class ExtensionsManager(object):
    def __init__(self):
        self.managers = {}
        self._is_initialized = False

    def __lazy_init__(self):
        for root in Extensible.__subclasses__():
            manager = ExtensionsFactory(root)
            self.managers[manager.name] = manager
        self._is_initialized = True

    def __getattr__(self, type_):
        if not self._is_initialized:
            self.__lazy_init__()

        if type_ in self.managers:
            return self.managers[type_]

        # Retry with loading the required base module

        _load_module(_base_modules[type_])
        self.__lazy_init__()

        try:
            return self.managers[type_]
        except KeyError:
            raise InternalError("Unknown extension type '%s'" % type_)

"""Extensions provider. Use::

    browser = extensions.browser("sql", ...)

"""
extensions = ExtensionsManager()


def collect_subclasses(parent, suffix=None):
    """Collect all subclasses of `parent` and return a dictionary where keys
    are object names. Obect name is decamelized class names transformed to
    identifiers and with `suffix` removed. If a class has class attribute
    `__identifier__` then the attribute is used as name."""

    subclasses = {}
    for c in subclass_iterator(parent):
        name = None
        if hasattr(c, "__extension_name__"):
            name = getattr(c, "__extension_name__")
        elif hasattr(c, "__identifier__"):
            # TODO: depreciated
            name = getattr(c, "__identifier__")

        if not name:
            name = c.__name__
            if suffix and name.endswith(suffix):
                name = name[:-len(suffix)]
            name = to_identifier(decamelize(name))

        subclasses[name] = c

    return subclasses


def subclass_iterator(cls, _seen=None):
    """
    Generator over all subclasses of a given class, in depth first order.

    Source: http://code.activestate.com/recipes/576949-find-all-subclasses-of-a-given-class/
    """

    if not isinstance(cls, type):
        raise TypeError('_subclass_iterator must be called with '
                        'new-style classes, not %.100r' % cls)

    _seen = _seen or set()

    try:
        subs = cls.__subclasses__()
    except TypeError: # fails only when cls is type
        subs = cls.__subclasses__(cls)
    for sub in subs:
        if sub not in _seen:
            _seen.add(sub)
            yield sub
            for sub in subclass_iterator(sub, _seen):
                yield sub

def _load_module(modulepath):
    mod = __import__(modulepath)
    path = []
    for token in modulepath.split(".")[1:]:
       path.append(token)
       mod = getattr(mod, token)
    return mod

########NEW FILE########
__FILENAME__ = formatter
# -*- coding: utf-8 -*-
from StringIO import StringIO
from collections import namedtuple

from .extensions import Extensible, extensions
from .errors import *

try:
    import jinja2
except ImportError:
    from .common import MissingPackage
    jinja2 = MissingPackage("jinja2", "Templating engine")

__all__ = [
            "TextTableFormatter",
            "SimpleDataTableFormatter",
            "SimpleHTMLTableFormatter",
            "CrossTableFormatter",
            "HTMLCrossTableFormatter",
            "create_formatter"
            ]

def create_formatter(type_, *args, **kwargs):
    """Creates a formatter of type `type`. Passes rest of the arguments to the
    formatters initialization method."""
    return extensions.formatter(type_, *args, **kwargs)


def _jinja_env():
    """Create and return cubes jinja2 environment"""
    loader = jinja2.PackageLoader('cubes', 'templates')
    env = jinja2.Environment(loader=loader)
    return env


def parse_format_arguments(formatter, args, prefix="f:"):
    """Parses dictionary of `args` for formatter"""


class Formatter(Extensible):
    """Empty class for the time being. Currently used only for finding all
    built-in subclasses"""
    def __call__(self, *args, **kwargs):
        return self.format(*args, **kwargs)


class TextTableFormatter(Formatter):
    parameters = [
                {
                    "name": "aggregate_format",
                    "type": "string",
                    "label": "Aggregate format"
                },
                {
                    "name": "dimension",
                    "type": "string",
                    "label": "Dimension to drill-down by"
                },
                {
                    "name": "measures",
                    "type": "list",
                    "label": "list of measures"
                }
            ]

    mime_type = "text/plain"

    def __init__(self, aggregate_format=None):
        super(TextTableFormatter, self).__init__()
        self.agg_format = aggregate_format or {}

    def format(self, result, dimension, aggregates=None, hierarchy=None):
        cube = result.cell.cube
        aggregates = cube.get_aggregates(aggregates)

        rows = []
        label_width = 0
        aggregate_widths = [0] * len(aggregates)

        for row in result.table_rows(dimension, hierarchy=hierarchy):
            display_row = []
            label_width = max(label_width, len(row.label))
            display_row.append( (row.label, '<') )

            for i, aggregate in enumerate(aggregates):
                if aggregate.function in ["count", "count_nonempty"]:
                    default_fmt = "d"
                else:
                    default_fmt = ".2f"

                fmt = self.agg_format.get(aggregate.ref(), default_fmt)
                text = format(row.record[aggregate.ref()], fmt)
                aggregate_widths[i] = max(aggregate_widths[i], len(text))
                display_row.append( (text, '>') )
            rows.append(display_row)

        widths = [label_width] + aggregate_widths
        stream = StringIO()

        for row in rows:
            for i, fvalue in enumerate(row):
                value = fvalue[0]
                alignment = fvalue[1]
                text = format(value, alignment + "%ds" % (widths[i]+1))
                stream.write(text)
            stream.write("\n")

        value = stream.getvalue()
        stream.close()

        return value


class SimpleDataTableFormatter(Formatter):

    parameters = [
                {
                    "name": "dimension",
                    "type": "string",
                    "label": "dimension to consider"
                },
                {
                    "name": "aggregates",
                    "short_name": "aggregates",
                    "type": "list",
                    "label": "list of aggregates"
                }
            ]

    mime_type = "application/json"

    def __init__(self, levels=None):
        """Creates a formatter that formats result into a tabular structure.
        """

        super(SimpleDataTableFormatter, self).__init__()

    def format(self, result, dimension, hierarchy=None, aggregates=None):

        cube = result.cell.cube
        aggregates = cube.get_aggregates(aggregates)

        dimension = cube.dimension(dimension)
        hierarchy = dimension.hierarchy(hierarchy)
        cut = result.cell.cut_for_dimension(dimension)

        if cut:
            rows_level = hierarchy[cut.level_depth()+1]
        else:
            rows_level = hierarchy[0]

        is_last = hierarchy.is_last(rows_level)

        rows = []

        for row in result.table_rows(dimension):
            rheader = { "label":row.label,
                        "key":row.key}
            # Get values for aggregated measures
            data = [row.record[str(agg)] for agg in aggregates]
            rows.append({"header":rheader, "data":data, "is_base": row.is_base})

        labels = [agg.label or agg.name for agg in aggregates]

        hierarchy = dimension.hierarchy()
        header = [rows_level.label or rows_level.name]
        header += labels

        data_table = {
                "header": header,
                "rows": rows
                }

        return data_table;

class TextTableFormatter2(Formatter):
    parameters = [
                {
                    "name": "measure_format",
                    "type": "string",
                    "label": "Measure format"
                },
                {
                    "name": "dimension",
                    "type": "string",
                    "label": "dimension to consider"
                },
                {
                    "name": "measures",
                    "type": "list",
                    "label": "list of measures"
                }
            ]

    mime_type = "text/plain"

    def __init__(self):
        super(TextTableFormatter, self).__init__()

    def format(self, result, dimension, measures):
        cube = result.cube
        dimension = cube.dimension(dimension)

        if not result.has_dimension(dimension):
            raise CubesError("Result was not drilled down by dimension "
                             "'%s'" % str(dimension))

        raise NotImplementedError
        table_formatter = SimpleDataTableFormatter()

CrossTable = namedtuple("CrossTable", ["columns", "rows", "data"])

class CrossTableFormatter(Formatter):
    parameters = [
                {
                    "name": "aggregates_on",
                    "type": "string",
                    "label": "Localtion of aggregates. Can be columns, rows or "
                             "cells",
                    "scope": "formatter",
                },
                {
                    "name": "onrows",
                    "type": "attributes",
                    "label": "List of dimension attributes to be put on rows"
                },
                {
                    "name": "oncolumns",
                    "type": "attributes",
                    "label": "List of attributes to be put on columns"
                },
                {
                    "name": "aggregates",
                    "short_name": "aggregates",
                    "type": "list",
                    "label": "list of aggregates"
                }
            ]

    mime_type = "application/json"

    def __init__(self, aggregates_on=None):
        """Creates a cross-table formatter.

        Arguments:

        * `aggregates_on` – specify how to put aggregates in the table. Might
          be one of ``rows``, ``columns`` or ``cells`` (default).

        If aggregates are put on rows or columns, then respective row or
        column is added per aggregate. The data contains single aggregate
        values.

        If aggregates are put in the table as cells, then the data contains
        tuples of aggregates in the order as specified in the `aggregates`
        argument of `format()` method.
        """

        super(CrossTableFormatter, self).__init__()

        self.aggregates_on = aggregates_on

    def format(self, result, onrows=None, oncolumns=None, aggregates=None,
               aggregates_on=None):
        """
        Creates a cross table from a drilldown (might be any list of records).
        `onrows` contains list of attribute names to be placed at rows and
        `oncolumns` contains list of attribute names to be placet at columns.
        `aggregates` is a list of aggregates to be put into cells. If
        aggregates are not specified, then only ``record_count`` is used.

        Returns a named tuble with attributes:

        * `columns` - labels of columns. The tuples correspond to values of
          attributes in `oncolumns`.
        * `rows` - labels of rows as list of tuples. The tuples correspond to
          values of attributes in `onrows`.
        * `data` - list of aggregate data per row. Each row is a list of
          aggregate tuples.

        """

        # Use formatter's default, if set
        aggregates_on = aggregates_on or self.aggregates_on
        cube = result.cell.cube
        aggregates = cube.get_aggregates(aggregates)

        matrix = {}
        row_hdrs = []
        column_hdrs = []

        labels = [agg.label for agg in aggregates]
        agg_refs = [agg.ref() for agg in aggregates]

        if aggregates_on is None or aggregates_on == "cells":
            for record in result.cells:
                # Get table coordinates
                hrow = tuple(record[f] for f in onrows)
                hcol = tuple(record[f] for f in oncolumns)

                if not hrow in row_hdrs:
                    row_hdrs.append(hrow)
                if not hcol in column_hdrs:
                    column_hdrs.append(hcol)

                matrix[(hrow, hcol)] = tuple(record[a] for a in agg_refs)

        else:
            for record in result.cells:
                # Get table coordinates
                base_hrow = [record[f] for f in onrows]
                base_hcol = [record[f] for f in oncolumns]

                for i, agg in enumerate(aggregates):

                    if aggregates_on == "rows":
                        hrow = tuple(base_hrow + [agg.label or agg.name])
                        hcol = tuple(base_hcol)

                    elif aggregates_on == "columns":
                        hrow = tuple(base_hrow)
                        hcol = tuple(base_hcol + [agg.label or agg.name])

                    if not hrow in row_hdrs:
                        row_hdrs.append(hrow)

                    if not hcol in column_hdrs:
                        column_hdrs.append(hcol)

                    matrix[(hrow, hcol)] = record[agg.ref()]

        data = []

        for hrow in row_hdrs:
            row = [matrix.get((hrow, hcol)) for hcol in column_hdrs]
            data.append(row)

        return CrossTable(column_hdrs, row_hdrs, data)

class HTMLCrossTableFormatter(CrossTableFormatter):
    parameters = [
                {
                    "name": "aggregates_on",
                    "type": "string",
                    "label": "Localtion of measures. Can be columns, rows or "
                             "cells",
                    "scope": "formatter",
                },
                {
                    "name": "onrows",
                    "type": "attributes",
                    "label": "List of dimension attributes to be put on rows"
                },
                {
                    "name": "oncolumns",
                    "type": "attributes",
                    "label": "List of attributes to be put on columns"
                },
                {
                    "name": "aggregates",
                    "short_name": "aggregates",
                    "type": "list",
                    "label": "list of aggregates"
                },
                {
                    "name": "table_style",
                    "description": "CSS style for the table"
                }
            ]
    mime_type = "text/html"

    def __init__(self, aggregates_on="cells", measure_labels=None,
            aggregation_labels=None, measure_label_format=None,
            count_label=None, table_style=None):
        """Create a simple HTML table formatter. See `CrossTableFormatter` for
        information about arguments."""

        if aggregates_on not in ["columns", "rows", "cells"]:
            raise ArgumentError("aggregates_on sohuld be either 'columns' "
                                "or 'rows', is %s" % aggregates_on)

        super(HTMLCrossTableFormatter, self).__init__(aggregates_on)

        self.env = _jinja_env()
        self.template = self.env.get_template("cross_table.html")
        self.table_style = table_style

    def format(self, result, onrows=None, oncolumns=None, aggregates=None):

        table = super(HTMLCrossTableFormatter, self).format(result,
                                                        onrows=onrows,
                                                        oncolumns=oncolumns,
                                                        aggregates=aggregates)
        output = self.template.render(table=table,
                                      table_style=self.table_style)
        return output


class SimpleHTMLTableFormatter(Formatter):

    parameters = [
                {
                    "name": "dimension",
                    "type": "string",
                    "label": "dimension to consider"
                },
                {
                    "name": "aggregates",
                    "short_name": "aggregates",
                    "type": "list",
                    "label": "list of aggregates"
                }
            ]

    mime_type = "text/html"

    def __init__(self, create_links=True, table_style=None):
        """Create a simple HTML table formatter"""

        super(SimpleHTMLTableFormatter, self).__init__()

        self.env = _jinja_env()
        self.formatter = SimpleDataTableFormatter()
        self.template = self.env.get_template("simple_table.html")
        self.create_links = create_links
        self.table_style = table_style

    def format(self, result, dimension, aggregates=None, hierarchy=None):
        cube = result.cell.cube
        dimension = cube.dimension(dimension)
        hierarchy = dimension.hierarchy(hierarchy)
        aggregates = cube.get_aggregates(aggregates)

        cut = result.cell.cut_for_dimension(dimension)

        if cut:
            is_last = cut.level_depth() >= len(hierarchy)
        else:
            is_last = False

        table = self.formatter.format(result, dimension, aggregates=aggregates)

        output = self.template.render(cell=result.cell,
                                      dimension=dimension,
                                      table=table,
                                      create_links=self.create_links,
                                      table_style=self.table_style,
                                      is_last=is_last)
        return output

class RickshawSeriesFormatter(Formatter):
    """Presenter for series to be used in Rickshaw JavaScript charting
    library.

    Library URL: http://code.shutterstock.com/rickshaw/"""

    def format(self, result, aggregate):
        data = []
        for x, row in enumerate(result):
            data.append({"x":x, "y":row[str(aggregate)]})
        return data

_default_ricshaw_palette = ["mediumorchid", "steelblue", "turquoise",
                            "mediumseagreen", "gold", "orange", "tomato"]

class RickshawMultiSeriesFormatter(Formatter):
    """Presenter for series to be used in Rickshaw JavaScript charting
    library.

    Library URL: http://code.shutterstock.com/rickshaw/"""

    def format(self, result, series_dimension, values_dimension,
                aggregate, color_map=None, color_palette=None):
        """Provide multiple series. Result is expected to be ordered.

        Arguments:
            * `result` – AggregationResult object
            * `series_dimension` – dimension used for split to series
            * `value_dimension` – dimension used to get values
            * `aggregated_measure` – measure attribute to be plotted
            * `color_map` – The dictionary is a map between dimension keys and
              colors, the map keys should be strings.
            * `color_palette` – List of colors that will be cycled for each
              series.

        Note: you should use either color_map or color_palette, not both.
        """

        if color_map and color_palette:
            raise CubesError("Use either color_map or color_palette, not both")

        color_map = color_map or {}
        color_palette = color_palette or _default_ricshaw_palette

        cube = result.cell.cube
        series_dimension = cube.dimension(series_dimension)
        values_dimension = cube.dimension(values_dimension)
        try:
            series_level = result.levels[str(series_dimension)][-1]
        except KeyError:
            raise CubesError("Result was not drilled down by dimension '%s'" \
                                % str(series_dimension))
        try:
            values_level = result.levels[str(values_dimension)][-1]
        except KeyError:
            raise CubesError("Result was not drilled down by dimension '%s'" \
                                % str(values_dimension))
        series = []
        rows = [series_level.key.ref(), series_level.label_attribute.ref()]
        columns = [values_level.key.ref(), values_level.label_attribute.ref()]

        cross_table = result.cross_table(onrows=rows,
                                         oncolumns=columns,
                                         aggregates=[aggregate])

        color_index = 0

        for head, row in zip(cross_table.rows, cross_table.data):
            data = []
            for x, value in enumerate(row):
                data.append({"x":x, "y":value[0]})

            # Series label is in row heading at index 1
            series_dict = {
                            "data": data,
                            "name": head[1]
                          }
            # Use dimension key for color
            if color_map:
                series_dict["color"] = color_map.get(str(head[0]))
            elif color_palette:
                color_index = (color_index + 1) % len(color_palette)
                series_dict["color"] = color_palette[color_index]

            series.append(series_dict)

        return series


########NEW FILE########
__FILENAME__ = logging
# -*- coding: utf-8 -*-

from __future__ import absolute_import

from logging import getLogger, Formatter, StreamHandler, FileHandler
from .errors import *

__all__ = [
           "logger_name",
           "get_logger",
           "create_logger",
           ]

logger_name = "cubes"
logger = None

def get_logger(path=None):
    """Get brewery default logger"""
    global logger

    if logger:
        return logger
    else:
        return create_logger(path)

def create_logger(path=None):
    """Create a default logger"""
    global logger
    logger = getLogger(logger_name)
    formatter = Formatter(fmt='%(asctime)s %(levelname)s %(message)s')

    if path:
        #create a logger which logs to a file
        handler = FileHandler(path)
    else:
        #create a default logger
        handler = StreamHandler()

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


########NEW FILE########
__FILENAME__ = mapper
# -*- coding: utf-8 -*-
"""Logical to Physical Mappers"""

import collections

from .logging import get_logger
from .errors import *

__all__ = (
    "Mapper",
)

class Mapper(object):
    """Mapper is core class for translating logical model to physical database
    schema.
    """
    # WARNING: do not put any SQL/engine/connection related stuff into this
    # class yet. It might be moved to the cubes as one of top-level modules
    # and subclassed here.

    def __init__(self, cube, locale=None, schema=None, fact_name=None,
                 **options):
        """Abstract class for mappers which maps logical references to
        physical references (tables and columns).

        Attributes:

        * `cube` - mapped cube
        * `simplify_dimension_references` – references for flat dimensions
          (with one level and no details) will be just dimension names, no
          attribute name. Might be useful when using single-table schema, for
          example, with couple of one-column dimensions.
        * `fact_name` – fact name, if not specified then `cube.name` is used
        * `schema` – default database schema

        """

        super(Mapper, self).__init__()

        if cube == None:
            raise Exception("Cube for mapper should not be None.")

        self.logger = get_logger()

        self.cube = cube
        # TODO: merge with mappings received as arguments
        self.mappings = self.cube.mappings
        self.locale = locale

        # TODO: remove this (should be in SQL only)

        if "simplify_dimension_references" in options:
            self.simplify_dimension_references = options["simplify_dimension_references"]
        else:
            self.simplify_dimension_references = True

        self._collect_attributes()

    def _collect_attributes(self):
        """Collect all cube attributes and create a dictionary where keys are
        logical references and values are `cubes.model.Attribute` objects.
        This method should be used after each cube or mappings change.
        """

        self.attributes = collections.OrderedDict()

        for attr in self.cube.all_attributes:
            self.attributes[self.logical(attr)] = attr

    def set_locale(self, locale):
        """Change the mapper's locale"""
        self.locale = locale
        self._collect_attributes()

    # TODO: depreciate in favor of Cube.all_attributes
    def all_attributes(self, expand_locales=False):
        """Return a list of all attributes of a cube. If `expand_locales` is
        ``True``, then localized logical reference is returned for each
        attribute's locale."""
        return self.attributes.values()

    # TODO: depreciate in favor of Cube.attribute
    def attribute(self, name):
        """Returns an attribute with logical reference `name`. """
        # TODO: If attribute is not found, returns `None` (yes or no?)

        return self.attributes[name]

    def logical(self, attribute, locale=None):
        """Returns logical reference as string for `attribute` in `dimension`.
        If `dimension` is ``Null`` then fact table is assumed. The logical
        reference might have following forms:

        * ``dimension.attribute`` - dimension attribute
        * ``attribute`` - fact measure or detail

        If `simplify_dimension_references` is ``True`` then references for
        flat dimensios without details is `dimension`.

        If `locale` is specified, then locale is added to the reference. This
        is used by backends and other mappers, it has no real use in end-user
        browsing.
        """

        reference = attribute.ref(self.simplify_dimension_references, locale)

        return reference

    def split_logical(self, reference):
        """Returns tuple (`dimension`, `attribute`) from `logical_reference` string. Syntax
        of the string is: ``dimensions.attribute``."""

        split = reference.split(".")

        if len(split) > 1:
            dim_name = split[0]
            attr_name = ".".join(split[1:])
            return (dim_name, attr_name)
        else:
            return (None, reference)

    def physical(self, attribute, locale=None):
        """Returns physical reference for attribute. Returned value is backend
        specific. Default implementation returns a value from the mapping
        dictionary.

        This method should be implemented by `Mapper` subclasses.
        """

        return self.mappings.get(self.logical(attribute, locale))


########NEW FILE########
__FILENAME__ = metadata
# -*- coding: utf-8 -*-
"""Functions for manipulating the model metadata in it's raw form –
dictionary:

    * Model metadata loading and writing
    * Expanding metadata – resolving defaults, converting strings to required
      structures
    * Simplifying metadata – removing defaults for better output readability
    * Metadata validation

Purpose of this module is to maintain compatibility between model metadata in
the future.

"""

import pkgutil
import urlparse
import urllib2
import shutil
import json
import os
import re

from collections import OrderedDict, namedtuple
from .errors import *

try:
    import jsonschema
except ImportError:
    from cubes.common import MissingPackage
    jsonschema = MissingPackage("jsonschema", "Model validation")

__all__ = (
    "read_model_metadata",
    "read_model_metadata_bundle",
    "write_model_metadata_bundle",

    "expand_cube_metadata",
    "expand_dimension_links",
    "expand_dimension_metadata",
    "expand_level_metadata",
    "expand_attribute_metadata",

    "validate_model",
)

# TODO: add the following:
#
# append_mappings(cube, mappings)
# append_joins(cube, joins)
# link_mappings(cube) -> link mappings with their respective attributes
# strip_mappings(cube) -> remove mappings from cube
# strip_mappings

def _json_from_url(url):
    """Opens `resource` either as a file with `open()`or as URL with
    `urllib2.urlopen()`. Returns opened handle. """

    parts = urlparse.urlparse(url)

    if parts.scheme in ('', 'file'):
        handle = open(parts.path)
    elif len(parts.scheme) == 1:
        # TODO: This is temporary hack which can be replaced by proper python
        # 3.4 functionality later
        handle = open(url)
    else:
        handle = urllib2.urlopen(url)

    try:
        desc = json.load(handle)
    except ValueError as e:
        raise SyntaxError("Syntax error in %s: %s" % (url, e.args))
    finally:
        handle.close()

    return desc


def read_model_metadata(source):
    """Reads a model description from `source` which can be a filename, URL,
    file-like object or a path to a directory. Returns a model description
    dictionary."""

    if isinstance(source, basestring):
        parts = urlparse.urlparse(source)
        if parts.scheme in ('', 'file') and os.path.isdir(parts.path):
            source = parts.path
            return read_model_metadata_bundle(source)
        elif len(parts.scheme) == 1 and os.path.isdir(source):
            # TODO: same hack as in _json_from_url
            return read_model_metadata_bundle(source)
        else:
            return _json_from_url(source)
    else:
        return json.load(source)


def read_model_metadata_bundle(path):
    """Load logical model a directory specified by `path`.  Returns a model
    description dictionary. Model directory bundle has structure:

    * ``model.cubesmodel/``
        * ``model.json``
        * ``dim_*.json``
        * ``cube_*.json``

    The dimensions and cubes lists in the ``model.json`` are concatenated with
    dimensions and cubes from the separate files.
    """

    if not os.path.isdir(path):
        raise ArgumentError("Path '%s' is not a directory.")

    info_path = os.path.join(path, 'model.json')

    if not os.path.exists(info_path):
        raise ModelError('main model info %s does not exist' % info_path)

    model = _json_from_url(info_path)

    # Find model object files and load them

    if not "dimensions" in model:
        model["dimensions"] = []

    if not "cubes" in model:
        model["cubes"] = []

    for dirname, dirnames, filenames in os.walk(path):
        for filename in filenames:
            if os.path.splitext(filename)[1] != '.json':
                continue

            split = re.split('_', filename)
            prefix = split[0]
            obj_path = os.path.join(dirname, filename)

            if prefix in ('dim', 'dimension'):
                desc = _json_from_url(obj_path)
                try:
                    name = desc["name"]
                except KeyError:
                    raise ModelError("Dimension file '%s' has no name key" %
                                                                     obj_path)
                if name in model["dimensions"]:
                    raise ModelError("Dimension '%s' defined multiple times " %
                                        "(in '%s')" % (name, obj_path) )
                model["dimensions"].append(desc)

            elif prefix == 'cube':
                desc = _json_from_url(obj_path)
                try:
                    name = desc["name"]
                except KeyError:
                    raise ModelError("Cube file '%s' has no name key" %
                                                                     obj_path)
                if name in model["cubes"]:
                    raise ModelError("Cube '%s' defined multiple times "
                                        "(in '%s')" % (name, obj_path) )
                model["cubes"].append(desc)

    return model


def write_model_metadata_bundle(path, metadata, replace=False):
    """Writes a model metadata bundle into new directory `target` from
    `metadata`. Directory should not exist."""

    if os.path.exists(path):
        if not os.path.isdir(path):
            raise CubesError("Target exists and is a file, "
                                "can not replace")
        elif not os.path.exists(os.path.join(path, "model.json")):
            raise CubesError("Target is not a model directory, "
                                "can not replace.")
        if replace:
            shutil.rmtree(path)
        else:
            raise CubesError("Target already exists. "
                                "Remove it or force replacement.")

    os.makedirs(path)

    metadata = dict(metadata)

    dimensions = metadata.pop("dimensions", [])
    cubes = metadata.pop("cubes", [])

    for dim in dimensions:
        name = dim["name"]
        filename = os.path.join(path, "dim_%s.json" % name)
        with open(filename, "w") as f:
            json.dump(dim, f, indent=4)

    for cube in cubes:
        name = cube["name"]
        filename = os.path.join(path, "cube_%s.json" % name)
        with open(filename, "w") as f:
            json.dump(cube, f, indent=4)

    filename = os.path.join(path, "model.json")
    with open(filename, "w") as f:
        json.dump(metadata, f, indent=4)


def expand_cube_metadata(metadata):
    """Expands `metadata` to be as complete as possible cube metadata.
    `metadata` should be a dictionary."""

    metadata = dict(metadata)

    if not "name" in metadata:
        raise ModelError("Cube has no name")

    links = metadata.get("dimensions", [])

    if links:
        links = expand_dimension_links(metadata["dimensions"])

    # TODO: depreciate this
    if "hierarchies" in metadata:
        dim_hiers = dict(metadata["hierarchies"])

        for link in links:
            try:
                hiers = dim_hiers.pop(link["name"])
            except KeyError:
                continue

            link["hierarchies"] = hiers

        if dim_hiers:
            raise ModelError("There are hierarchies specified for non-linked "
                             "dimensions: %s." % (dim_hiers.keys()))

    nonadditive = metadata.pop("nonadditive", None)
    if "measures" in metadata:
        measures = []
        for attr in metadata["measures"]:
            attr = expand_attribute_metadata(attr)
            if nonadditive:
                attr["nonadditive"] = attr.get("nonadditive", nonadditive)
            measures.append(attr)

        metadata["measures"] = measures

    # Replace the dimensions
    if links:
        metadata["dimensions"] = links

    return metadata


def expand_dimension_links(metadata):
    """Expands links to dimensions. `metadata` should be a list of strings or
    dictionaries (might be mixed). Returns a list of dictionaries with at
    least one key `name`. Other keys are: `hierarchies`,
    `default_hierarchy_name`, `nonadditive`, `cardinality`, `template`"""

    links = []

    for link in metadata:
        if isinstance(link, basestring):
            link = {"name": link}
        elif "name" not in link:
            raise ModelError("Dimension link has no name")

        links.append(link)

    return links


def expand_dimension_metadata(metadata, expand_levels=False):
    """
    Expands `metadata` to be as complete as possible dimension metadata. If
    `expand_levels` is `True` then levels metadata are expanded as well.
    """

    if isinstance(metadata, basestring):
        metadata = {"name":metadata, "levels": [metadata]}
    else:
        metadata = dict(metadata)

    if not "name" in metadata:
        raise ModelError("Dimension has no name")

    name = metadata["name"]

    # Fix levels
    levels = metadata.get("levels", [])
    if not levels and expand_levels:
        attributes = ["attributes", "key", "order_attribute", "order",
                      "label_attribute"]
        level = {}
        for attr in attributes:
            if attr in metadata:
                level[attr] = metadata[attr]

        level["cardinality"] = metadata.get("cardinality")

        # Default: if no attributes, then there is single flat attribute
        # whith same name as the dimension
        level["name"] = name
        level["label"] = metadata.get("label")

        levels = [level]

    if levels:
        levels = [expand_level_metadata(level) for level in levels]
        metadata["levels"] = levels

    # Fix hierarchies
    if "hierarchy" in metadata and "hierarchies" in metadata:
        raise ModelInconsistencyError("Both 'hierarchy' and 'hierarchies'"
                                      " specified. Use only one")

    hierarchy = metadata.get("hierarchy")
    if hierarchy:
        hierarchies = [{"name": "default", "levels": hierarchy}]
    else:
        hierarchies = metadata.get("hierarchies")

    if hierarchies:
        metadata["hierarchies"] = hierarchies

    return metadata


def expand_hierarchy_metadata(metadata):
    """Returns a hierarchy metadata as a dictionary. Makes sure that required
    properties are present. Raises exception on missing values."""

    try:
        name = metadata["name"]
    except KeyError:
        raise ModelError("Hierarchy has no name")

    if not "levels" in metadata:
        raise ModelError("Hierarchy '%s' has no levels" % name)

    return metadata

def expand_level_metadata(metadata):
    """Returns a level description as a dictionary. If provided as string,
    then it is going to be used as level name and as its only attribute. If a
    dictionary is provided and has no attributes, then level will contain only
    attribute with the same name as the level name."""
    if isinstance(metadata, basestring):
        metadata = {"name":metadata, "attributes": [metadata]}
    else:
        metadata = dict(metadata)

    try:
        name = metadata["name"]
    except KeyError:
        raise ModelError("Level has no name")

    attributes = metadata.get("attributes")

    if not attributes:
        attribute = {
            "name": name,
            "label": metadata.get("label")
        }

        attributes = [attribute]

    metadata["attributes"] = [expand_attribute_metadata(a) for a in attributes]

    # TODO: Backward compatibility – depreciate later
    if "cardinality" not in metadata:
        info = metadata.get("info", {})
        if "high_cardinality" in info:
            metadata["cardinality"] = "high"

    return metadata


def expand_attribute_metadata(metadata):
    """Fixes metadata of an attribute. If `metadata` is a string it will be
    converted into a dictionary with key `"name"` set to the string value."""
    if isinstance(metadata, basestring):
        metadata = {"name": metadata}

    return metadata


ValidationError = namedtuple("ValidationError",
                            ["severity", "scope", "object", "property", "message"])


def validate_model(metadata):
    """Validate model metadata."""

    validator = ModelMetadataValidator(metadata)
    return validator.validate()

class ModelMetadataValidator(object):
    def __init__(self, metadata):
        self.metadata = metadata

        data = pkgutil.get_data("cubes", "schemas/model.json")
        self.model_schema = json.loads(data)

        data = pkgutil.get_data("cubes", "schemas/cube.json")
        self.cube_schema = json.loads(data)

        data = pkgutil.get_data("cubes", "schemas/dimension.json")
        self.dimension_schema = json.loads(data)

    def validate(self):
        errors = []

        errors += self.validate_model()

        if "cubes" in self.metadata:
            for cube in self.metadata["cubes"]:
                errors += self.validate_cube(cube)

        if "dimensions" in self.metadata:
            for dim in self.metadata["dimensions"]:
                errors += self.validate_dimension(dim)

        return errors

    def _collect_errors(self, scope, obj, validator, metadata):
        errors = []

        for error in validator.iter_errors(metadata):
            if error.path:
                path = [str(item) for item in error.path]
                ref = ".".join(path)
            else:
                ref = None

            verror = ValidationError("error", scope, obj, ref, error.message)
            errors.append(verror)

        return errors

    def validate_model(self):
        validator = jsonschema.Draft4Validator(self.model_schema)
        errors = self._collect_errors("model", None, validator, self.metadata)

        dims = self.metadata.get("dimensions")
        if dims and isinstance(dims, list):
            for dim in dims:
                if isinstance(dim, basestring):
                    err = ValidationError("default", "model", None,
                                          "dimensions",
                                          "Dimension '%s' is not described, "
                                          "creating flat single-attribute "
                                          "dimension" % dim)
                    errors.append(err)

        return errors

    def validate_cube(self, cube):
        validator = jsonschema.Draft4Validator(self.cube_schema)
        name = cube.get("name")

        return self._collect_errors("cube", name, validator, cube)

    def validate_dimension(self, dim):
        validator = jsonschema.Draft4Validator(self.dimension_schema)
        name = dim.get("name")

        errors = self._collect_errors("dimension", name, validator, dim)

        if "default_hierarchy_name" not in dim:
            error = ValidationError("default", "dimension", name, None,
                                    "No default hierarchy name specified, "
                                    "using first one")
            errors.append(error)

        if "levels" not in dim and "attributes" not in dim:
            error = ValidationError("default", "dimension", name, None,
                                    "Neither levels nor attributes specified, "
                                    "creating flat dimension without details")
            errors.append(error)

        elif "levels" in dim and "attributes" in dim:
            error = ValidationError("error", "dimension", name, None,
                                    "Both levels and attributes specified")
            errors.append(error)

        return errors

########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-
"""Logical model."""

import copy

from collections import OrderedDict, defaultdict
from .common import IgnoringDictionary, to_label
from .common import assert_instance, assert_all_instances
from .logging import get_logger
from .errors import *
from .statutils import aggregate_calculator_labels
from .metadata import *

__all__ = [
    "Model",
    "Cube",
    "Dimension",
    "Hierarchy",
    "Level",
    "AttributeBase",
    "Attribute",
    "Measure",
    "MeasureAggregate",

    "create_cube",
    "create_dimension",
    "create_level",
    "create_attribute",
    "create_measure",
    "create_measure_aggregate",
    "attribute_list",
]


DEFAULT_FACT_COUNT_AGGREGATE = {
    "name": "fact_count",
    "label": "Count",
    "function": "count"
}


# TODO: make this configurable
IMPLICIT_AGGREGATE_LABELS = {
    "sum": u"Sum of {measure}",
    "count": u"Record Count",
    "count_nonempty": u"Non-empty count of {measure}",
    "min": u"{measure} Minimum",
    "max": u"{measure} Maximum",
    "avg": u"Average of {measure}",
}

IMPLICIT_AGGREGATE_LABELS.update(aggregate_calculator_labels())

_DEFAULT_LEVEL_ROLES = {
    "time": ("year", "quarter", "month", "day", "hour", "minute", "second",
             "week", "weeknum", "dow",
             "isoyear", "isoweek", "isoweekday")
}

class Model(object):
    def __init__(self, name=None, locale=None, label=None, description=None,
                 info=None, mappings=None, provider=None, metadata=None,
                 translations=None):
        """
        Logical representation of data. Base container for cubes and
        dimensions.

        Attributes:

        * `name` - model name
        * `dimensions` - list of `Dimension` instances
        * `locale` - locale code of the model
        * `label` - human readable name - can be used in an application
        * `description` - longer human-readable description of the model
        * `info` - custom information dictionary

        * `metadata` – a dictionary describing the model
        * `provider` – an object that creates model objects

        """
        # * `mappings` – model-wide mappings of logical-to-physical attributes

        # Basic information
        self.name = name
        self.label = label
        self.description = description
        self.locale = locale
        self.info = info or {}
        self.provider = provider
        self.metadata = metadata

        # Physical information
        self.mappings = mappings

        self.translations = translations or {}

    def __str__(self):
        return 'Model(%s)' % self.name

    def to_dict(self, **options):
        """Return dictionary representation of the model. All object
        references within the dictionary are name based

        * `full_attribute_names` - if set to True then attribute names will be
          written as ``dimension_name.attribute_name``
        """

        out = IgnoringDictionary()

        out["name"] = self.name
        out["label"] = self.label
        out["description"] = self.description
        out["info"] = self.info

        if options.get("with_mappings"):
            out["mappings"] = self.mappings

        return out

    def __eq__(self, other):
        if other is None or type(other) != type(self):
            return False
        if self.name != other.name or self.label != other.label \
                or self.description != other.description:
            return False
        elif self.info != other.info:
            return False
        return True

    def _add_translation(self, lang, translation):
        self.translations[lang] = translation

    # TODO: move to separate module
    def localize(self, translation):
        """Return localized version of the model.

        `translation` might be a string or a dicitonary. If it is a string,
        then it represents locale name from model's localizations provided on
        model creation. If it is a dictionary, it should contains full model
        translation that is going to be applied.


        Translation dictionary structure example::

            {
                "locale": "sk",
                "cubes": {
                    "sales": {
                        "label": "Predaje",
                        "measures":
                            {
                                "amount": "suma",
                                "discount": {"label": "zľava",
                                             "description": "uplatnená zľava"}
                            }
                    }
                },
                "dimensions": {
                    "date": {
                        "label": "Dátum"
                        "attributes": {
                            "year": "rok",
                            "month": {"label": "mesiac"}
                        },
                        "levels": {
                            "month": {"label": "mesiac"}
                        }
                    }
                }
            }

        .. note::

            Whenever master model changes, you should call this method to get
            actualized localization of the original model.
        """

        model = copy.deepcopy(self)

        if type(translation) == str or type(translation) == unicode:
            try:
                translation = self.translations[translation]
            except KeyError:
                raise ModelError("Model has no translation for %s" %
                                 translation)

        if "locale" not in translation:
            raise ValueError("No locale specified in model translation")

        model.locale = translation["locale"]
        localize_common(model, translation)

        if "cubes" in translation:
            for name, cube_trans in translation["cubes"].items():
                cube = model.cube(name)
                cube.localize(cube_trans)

        if "dimensions" in translation:
            dimensions = translation["dimensions"]
            for name, dim_trans in dimensions.items():
                # Use translation template if exists, similar to dimension
                # template
                template_name = dim_trans.get("template")

                if False and template_name:
                    try:
                        template = dimensions[template_name]
                    except KeyError:
                        raise ModelError("No translation template '%s' for "
                                "dimension '%s'" % (template_name, name))

                    template = dict(template)
                    template.update(dim_trans)
                    dim_trans = template

                dim = model.dimension(name)
                dim.localize(dim_trans)

        return model

    def localizable_dictionary(self):
        """Get model locale dictionary - localizable parts of the model"""
        locale = {}
        locale.update(get_localizable_attributes(self))
        clocales = {}
        locale["cubes"] = clocales
        for cube in self.cubes.values():
            clocales[cube.name] = cube.localizable_dictionary()

        dlocales = {}
        locale["dimensions"] = dlocales
        for dim in self.dimensions:
            dlocales[dim.name] = dim.localizable_dictionary()

        return locale


class ModelObject(object):
    """Base classs for all model objects."""

    def __init__(self, name=None, label=None, description=None, info=None):
        """Initializes model object basics. Assures that the `info` is a
        dictionary."""

        self.name = name
        self.label = label
        self.description = description
        self.info = info or {}

    def to_dict(self, create_label=None, **options):
        """Convert to a dictionary. If `with_mappings` is ``True`` (which is
        default) then `joins`, `mappings`, `fact` and `options` are included.
        Should be set to ``False`` when returning a dictionary that will be
        provided in an user interface or through server API.
        """

        out = IgnoringDictionary()

        out["name"] = self.name
        out["info"] = self.info

        if create_label:
            out["label"] = self.label or to_label(self.name)
        else:
            out["label"] = self.label

        out["description"] = self.description

        return out


class Cube(ModelObject):
    def __init__(self, name, dimensions=None, measures=None, aggregates=None,
                 label=None, details=None, mappings=None, joins=None,
                 fact=None, key=None, description=None, browser_options=None,
                 info=None, dimension_links=None, locale=None, category=None,
                 datastore=None, **options):

        """Create a new Cube model object.

        Properties:

        * `name`: cube name, used as identifier
        * `measures`: list of measures – numerical attributes
          aggregation functions or natively aggregated values
        * `label`: human readable cube label
        * `details`: list of detail attributes
        * `description` - human readable description of the cube
        * `key`: fact key field (if not specified, then backend default key
          will be used, mostly ``id`` for SLQ or ``_id`` for document based
          databases)
        * `info` - custom information dictionary, might be used to store
          application/front-end specific information
        * `locale`: cube's locale
        * `dimension_links` – dimensions to be linked after the cube is
          created

        There are two ways how to assign dimensions to the cube: specify them
        during cube initialization in `dimensions` by providing a list of
        `Dimension` objects. Alternatively you can set `dimension_links`
        list with dimension names and the link the dimension using
        :meth:`cubes.Cube.add_dimension()`.

        Physical properties of the cube are described in the following
        attributes. They are used by the backends:

        * `mappings` - backend-specific logical to physical mapping
          dictionary. Keys and values of this dictionary are interpreted by
          the backend.
        * `joins` - backend-specific join specification (used for example in
          the SQL backend). It should be a list of dictionaries.
        * `fact` - fact table (collection, dataset, ...) name
        * `datastore` - name of datastore where the cube belongs
        * `browser_options` - dictionary of other options used by the backend
          - refer to the backend documentation to see what options are used
          (for example SQL browser might look here for ``denormalized_view``
          in case of denormalized browsing)


        The dimension links are either dimension names or dictionaries
        specifying how the dimension will be linked to the cube. The keys of
        the link dictionary are:

        * `name` – name of the dimension to be linked
        * `hierarchies` – list of hierarchy names to be kept from the
          dimension
        * `nonadditive` – additivity of the linked dimension (overrides the
          dimension's value)
        * `cardinality` – cardinality of the linked dimension in the cube's
          context (overrides the dimension's value)
        * `default_hierarchy_name` – which hierarchy will be used as default
          in the linked dimension

        """

        super(Cube, self).__init__(name, label, description, info)

        self.locale = locale

        # backward compatibility
        self.category = category or self.info.get("category")

        # Physical properties
        self.mappings = mappings
        self.fact = fact
        self.joins = joins
        self.key = key
        self.browser_options = browser_options or {}
        self.datastore = datastore or options.get("datastore")
        self.browser = options.get("browser")

        # Be graceful here
        self.dimension_links = expand_dimension_links(dimension_links or [])

        # Used by workspace internally
        self.provider = None
        # Used by backends
        self.basename = None

        self._dimensions = OrderedDict()

        if dimensions:
            if all([isinstance(dim, Dimension) for dim in dimensions]):
                for dim in dimensions:
                    self.add_dimension(dim)
            else:
                raise ModelError("Dimensions for cube initialization should be "
                                 "a list of Dimension instances.")
        #
        # Prepare measures and aggregates
        #
        measures = measures or []
        assert_all_instances(measures, Measure, "Measure")
        self.measures = measures

        aggregates = aggregates or []
        assert_all_instances(aggregates, MeasureAggregate, "Aggregate")
        self.aggregates = aggregates

        details = details or []
        assert_all_instances(details, Attribute, "Detail")
        self.details = details

    @property
    def measures(self):
        return self._measures.values()

    @measures.setter
    def measures(self, measures):
        self._measures = OrderedDict()
        for measure in measures:
            if measure.name in self._measures:
                raise ModelError("Duplicate measure %s in cube %s" %
                                 (measure.name, self.name))
            self._measures[measure.name] = measure

    @property
    def aggregates(self):
        return self._aggregates.values()

    @aggregates.setter
    def aggregates(self, aggregates):
        self._aggregates = OrderedDict()
        for agg in aggregates:
            if agg.name in self._aggregates:
                raise ModelError("Duplicate aggregate %s in cube %s" %
                                 (agg.name, self.name))

            # TODO: check for conflicts
            self._aggregates[agg.name] = agg

    def aggregates_for_measure(self, name):
        """Returns aggregtates for measure with `name`. Only direct function
        aggregates are returned. If the measure is specified in an expression,
        the aggregate is not included in the returned list"""

        return [agg for agg in self.aggregates if agg.measure == name]

    def get_aggregates(self, names=None):
        """Get a list of aggregates with `names`"""
        if not names:
            return self.aggregates

        return [self._aggregates[str(name)] for name in names]

    def link_dimensions(self, dimensions):
        """Links `dimensions` according to cube's `dimension_links`. The
        `dimensions` should be a dictionary with keys as dimension names and
        values as `Dimension` instances."""

        for link in self.dimension_links:
            link = dict(link)
            # TODO: use template/rename as well
            dim_name = link.pop("name")
            dim = dimensions[dim_name]

            if link:
                dim = dim.clone(**link)

            self.add_dimension(dim)

    def add_dimension(self, dimension):
        """Add dimension to cube. Replace dimension with same name. Raises
        `ModelInconsistencyError` when dimension with same name already exists
        in the receiver. """

        if not isinstance(dimension, Dimension):
            raise ArgumentError("Dimension added to cube '%s' is not a "
                                "Dimension instance." % self.name)

        if dimension.name in self._dimensions:
            raise ModelError("Dimension with name %s already exits "
                             "in cube %s" % (dimension.name, self.name))

        self._dimensions[dimension.name] = dimension

    def remove_dimension(self, dimension):
        """Remove a dimension from receiver. `dimension` can be either
        dimension name or dimension object."""

        dim = self.dimension(dimension)
        del self._dimensions[dim.name]

    @property
    def dimensions(self):
        return self._dimensions.values()

    def dimension(self, obj):
        """Get dimension object. If `obj` is a string, then dimension with
        given name is returned, otherwise dimension object is returned if it
        belongs to the cube.

        Raises `NoSuchDimensionError` when there is no such dimension.
        """

        # FIXME: raise better exception if dimension does not exist, but is in
        # the list of required dimensions

        if not obj:
            raise NoSuchDimensionError("Requested dimension should not be none (cube '%s')" % \
                                self.name)

        if isinstance(obj, basestring):
            if obj in self._dimensions:
                return self._dimensions[obj]
            else:
                raise NoSuchDimensionError("cube '%s' has no dimension '%s'" %
                                    (self.name, obj))
        elif isinstance(obj, Dimension):
             return obj
        else:
            raise NoSuchDimensionError("Invalid dimension or dimension "
                                       "reference '%s' for cube '%s'" %
                                            (obj, self.name))

    def measure(self, name):
        """Get measure object. If `obj` is a string, then measure with given
        name is returned, otherwise measure object is returned if it belongs
        to the cube. Returned object is of `Measure` type.

        Raises `NoSuchAttributeError` when there is no such measure or when
        there are multiple measures with the same name (which also means that
        the model is not valid).
        """

        name = str(name)
        try:
            return self._measures[name]
        except KeyError:
            raise NoSuchAttributeError("Cube '%s' has no measure '%s'" %
                                            (self.name, name))
    def aggregate(self, name):
        """Get aggregate object. If `obj` is a string, then aggregate with
        given name is returned, otherwise aggregate object is returned if it
        belongs to the cube. Returned object is of `MeasureAggregate` type.

        Raises `NoSuchAttributeError` when there is no such aggregate or when
        there are multiple aggregates with the same name (which also means
        that the model is not valid).
        """

        name = str(name)
        try:
            return self._aggregates[name]
        except KeyError:
            raise NoSuchAttributeError("cube '%s' has no aggregate '%s'" %
                                            (self.name, name))

    def nonadditive_type(self, aggregate):
        """Returns non-additive type of `aggregate`'s measure. If aggregate
        has no measure specified or is unknown (backend-specific) then `None`
        is returned."""

        try:
            measure = self.measure(aggregate.measure)
        except NoSuchAttributeError:
            return None

        return measure.nonadditive


    def measure_aggregate(self, name):
        """Returns a measure aggregate by name."""
        name = str(name)
        try:
            return self._aggregates[name]
        except KeyError:
            raise NoSuchAttributeError("Cube '%s' has no measure aggregate "
                                            "'%s'" % (self.name, name))


    def get_measures(self, measures):
        """Get a list of measures as `Attribute` objects. If `measures` is
        `None` then all cube's measures are returned."""

        array = []

        for measure in measures or self.measures:
            array.append(self.measure(measure))

        return array

    @property
    def all_attributes(self):
        """All cube's attributes from the fact: attributes of dimensions,
        details and measures."""
        attributes = []
        for dim in self.dimensions:
            attributes += dim.all_attributes

        attributes += self.details

        attributes += self.measures

        return attributes

    @property
    def all_aggregate_attributes(self):
        """All cube's attributes for aggregation: attributes of dimensions and
        aggregates.  """

        attributes = []
        for dim in self.dimensions:
            attributes += dim.all_attributes

        attributes += self.aggregates

        return attributes

    def attribute(self, attribute):
        """Returns an attribute object (dimension attribute, measure or
        detail)."""

        for dim in self.dimensions:
            try:
                return dim.attribute(attribute, by_ref=True)
            except KeyError:
                continue

        attrname = str(attribute)
        for detail in self.details:
            if detail.name == attrname:
                return detail

        for measure in self.measures:
            if measure.name == attrname:
                return measure

        raise NoSuchAttributeError("Cube '%s' has no attribute '%s'"
                                   % (self.name, attribute))

    def get_attributes(self, attributes=None, simplify=True, aggregated=False):
        """Returns a list of cube's attributes. If `aggregated` is `True` then
        attributes after aggregation are returned, otherwise attributes for a
        fact are considered.

        Aggregated attributes contain: dimension attributes and aggregates.
        Fact attributes contain: dimension attributes, fact details and fact
        measures.

        If the list `attributes` is empty, all attributes are returned.

        If `simplified_references` is `True` then dimension attribute
        references in `attrubutes` are considered simplified, otherwise they
        are considered as full (dim.attribute)."""

        names = [str(attr) for attr in attributes or []]

        if aggregated:
            attributes = self.all_aggregate_attributes
        else:
            attributes = self.all_attributes

        if not names:
            return attributes

        attr_map = dict((a.ref(simplify), a) for a in attributes)

        result = []
        for name in names:
            try:
                attr = attr_map[name]
            except KeyError:
                raise NoSuchAttributeError("Unknown attribute '%s' in cube "
                                           "'%s'" % (name, self.name))
            result.append(attr)

        return result

    def to_dict(self, **options):
        """Convert to a dictionary. If `with_mappings` is ``True`` (which is
        default) then `joins`, `mappings`, `fact` and `options` are included.
        Should be set to ``False`` when returning a dictionary that will be
        provided in an user interface or through server API.
        """

        out = super(Cube, self).to_dict(**options)

        out["locale"] = self.locale
        out["category"] = self.category

        aggregates = [m.to_dict(**options) for m in self.aggregates]
        out["aggregates"] = aggregates

        measures = [m.to_dict(**options) for m in self.measures]
        out["measures"] = measures

        details = [a.to_dict(**options) for a in self.details]
        out["details"] = details

        if options.get("expand_dimensions"):
            limits = defaultdict(dict)

            # TODO: move this to metadata as strip_hierarchies()
            hierarchy_limits = options.get("hierarchy_limits")
            hierarchy_limits = hierarchy_limits or []

            for dim, hier, level in hierarchy_limits:
                limits[dim][hier] = level

            dims = []

            for dim in self.dimensions:
                limit = limits.get(dim.name)
                info = dim.to_dict(hierarchy_limits=limit)
                dims.append(info)

        else:
            dims = [dim.name for dim in self.dimensions]

        out["dimensions"] = dims

        if options.get("with_mappings"):
            out["mappings"] = self.mappings
            out["fact"] = self.fact
            out["joins"] = self.joins
            out["browser_options"] = self.browser_options

        out["key"] = self.key
        return out

    def __eq__(self, other):
        if other is None or type(other) != type(self):
            return False
        if self.name != other.name or self.label != other.label \
            or self.description != other.description:
            return False
        elif self.dimensions != other.dimensions \
                or self.measures != other.measures \
                or self.aggregates != other.aggregates \
                or self.details != other.details \
                or self.mappings != other.mappings \
                or self.joins != other.joins \
                or self.browser_options != other.browser_options \
                or self.info != other.info:
            return False
        return True

    def validate(self):
        """Validate cube. See Model.validate() for more information. """
        results = []

        # Check whether all attributes, measures and keys are Attribute objects
        # This is internal consistency chceck

        measures = set()

        for measure in self.measures:
            if not isinstance(measure, Attribute):
                results.append(('error',
                                 "Measure '%s' in cube '%s' is not instance"
                                 "of Attribute" % (measure, self.name)))
            else:
                measures.add(str(measure))

        details = set()
        for detail in self.details:
            if not isinstance(detail, Attribute):
                results.append( ('error', "Detail '%s' in cube '%s' is not instance of Attribute" % (detail, self.name)) )
            if str(detail) in details:
                results.append( ('error', "Duplicate detail '%s' in cube '%s'"\
                                            % (detail, self.name)) )
            elif str(detail) in measures:
                results.append( ('error', "Duplicate detail '%s' in cube '%s'"
                                          " - specified also as measure" \
                                            % (detail, self.name)) )
            else:
                details.add(str(detail))

        # 2. check whether dimension attributes are unique

        return results

    def localize(self, locale):
        # FIXME: this needs revision/testing – it might be broken
        localize_common(self,locale)

        attr_locales = locale.get("measures")
        if attr_locales:
            for attrib in self.measures:
                if attrib.name in attr_locales:
                    localize_common(attrib, attr_locales[attrib.name])

        attr_locales = locale.get("aggregates")
        if attr_locales:
            for attrib in self.aggregates:
                if attrib.name in attr_locales:
                    localize_common(attrib, attr_locales[attrib.name])

        attr_locales = locale.get("details")
        if attr_locales:
            for attrib in self.details:
                if attrib.name in attr_locales:
                    localize_common(attrib, attr_locales[attrib.name])

    def localizable_dictionary(self):
        # FIXME: this needs revision/testing – it might be broken
        locale = {}
        locale.update(get_localizable_attributes(self))

        mdict = {}
        locale["measures"] = mdict

        for measure in self.measures:
            mdict[measure.name] = measure.localizable_dictionary()

        mdict = {}
        locale["details"] = mdict

        for measure in self.details:
            mdict[measure.name] = measure.localizable_dictionary()

        return locale

    def __str__(self):
        return self.name


class Dimension(ModelObject):
    """
    Cube dimension.

    """
    special_roles = ["time"]

    def __init__(self, name, levels, hierarchies=None,
                 default_hierarchy_name=None, label=None, description=None,
                 info=None, role=None, cardinality=None, category=None,
                 master=None, nonadditive=None, **desc):

        """Create a new dimension

        Attributes:

        * `name`: dimension name
        * `levels`: list of dimension levels (see: :class:`cubes.Level`)
        * `hierarchies`: list of dimension hierarchies. If no hierarchies are
          specified, then default one is created from ordered list of `levels`.
        * `default_hierarchy_name`: name of a hierarchy that will be used when
          no hierarchy is explicitly specified
        * `label`: dimension name that will be displayed (human readable)
        * `description`: human readable dimension description
        * `info` - custom information dictionary, might be used to store
          application/front-end specific information (icon, color, ...)
        * `role` – one of recognized special dimension types. Currently
          supported is only ``time``.
        * `cardinality` – cardinality of the dimension members. Used
          optionally by the backends for load protection and frontends for
          better auto-generated front-ends. See :class:`Level` for more
          information, as this attribute is inherited by the levels, if not
          specified explicitly in the level.
        * `category` – logical dimension group (user-oriented metadata)
        * `nonadditive` – kind of non-additivity of the dimension. Possible
          values: `None` (fully additive, default), ``time`` (non-additive for
          time dimensions) or ``all`` (non-additive for any other dimension)

        Dimension class is not meant to be mutable. All level attributes will
        have new dimension assigned.

        Note that the dimension will claim ownership of levels and their
        attributes. You should make sure that you pass a copy of levels if you
        are cloning another dimension.


        Note: The hierarchy will be owned by the dimension.
        """

        super(Dimension, self).__init__(name, label, description, info)

        self.role = role
        self.cardinality = cardinality
        self.category = category

        # Master dimension – dimension that this one was derived from, for
        # example by limiting hierarchies
        # TODO: not yet documented
        # TODO: probably replace the limit using limits in-dimension instead
        # of replacement of instance variables with limited content (?)
        self.master = master

        # Note: synchronize with Measure.__init__ if relevant/necessary
        if not nonadditive or nonadditive == "none":
            self.nonadditive = None
        elif nonadditive in ["all", "any"]:
            self.nonadditive = "all"
        elif nonadditive != "time":
            raise ModelError("Unknown non-additive diension type '%s'"
                             % nonadditive)

        self.nonadditive = nonadditive

        if not levels:
            raise ModelError("No levels specified for dimension %s" % name)

        # Own the levels and their attributes
        self._levels = OrderedDict()
        self._attributes = OrderedDict()
        self._attributes_by_ref = OrderedDict()

        default_roles = _DEFAULT_LEVEL_ROLES.get(self.role)

        for level in levels:
            self._levels[level.name] = level
            if default_roles and level.name in default_roles:
                level.role = level.name

        # Collect attributes
        self._attributes = OrderedDict()
        for level in self.levels:
            for a in level.attributes:
                # Own the attribute
                if a.dimension is not None and a.dimension is not self:
                    raise ModelError("Dimension '%s' can not claim attribute "
                                     "'%s' because it is owned by another "
                                     "dimension '%s'."
                                     % (self.name, a.name, a.dimension.name))
                a.dimension = self
                self._attributes[a.name] = a
                self._attributes_by_ref[a.ref()] = a

        # The hierarchies receive levels with already owned attributes
        if hierarchies:
            self.hierarchies = OrderedDict((h.name, h) for h in hierarchies)
        else:
            hier = Hierarchy("default", self.levels)
            self.hierarchies = OrderedDict( [("default", hier)] )

        self._flat_hierarchy = None
        self.default_hierarchy_name = default_hierarchy_name

    def __eq__(self, other):
        if other is None or type(other) != type(self):
            return False
        if self.name != other.name \
                or self.role != other.role \
                or self.label != other.label \
                or self.description != other.description \
                or self.cardinality != other.cardinality \
                or self.category != other.category:
            return False

        elif self._default_hierarchy() != other._default_hierarchy():
            return False

        if self._levels != other._levels:
            return False

        if other.hierarchies != self.hierarchies:
            return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def has_details(self):
        """Returns ``True`` when each level has only one attribute, usually
        key."""

        if self.master:
            return self.master.has_details

        return any([level.has_details for level in self._levels.values()])

    @property
    def levels(self):
        """Get list of all dimension levels. Order is not guaranteed, use a
        hierarchy to have known order."""
        return self._levels.values()

    @property
    def level_names(self):
        """Get list of level names. Order is not guaranteed, use a hierarchy
        to have known order."""
        return self._levels.keys()

    def level(self, obj):
        """Get level by name or as Level object. This method is used for
        coalescing value"""
        if isinstance(obj, basestring):
            if obj not in self._levels:
                raise KeyError("No level %s in dimension %s" %
                               (obj, self.name))
            return self._levels[obj]
        elif isinstance(obj, Level):
            return obj
        else:
            raise ValueError("Unknown level object %s (should be a string "
                             "or Level)" % obj)

    def hierarchy(self, obj=None):
        """Get hierarchy object either by name or as `Hierarchy`. If `obj` is
        ``None`` then default hierarchy is returned."""

        if obj is None:
            return self._default_hierarchy()
        if isinstance(obj, basestring):
            if obj not in self.hierarchies:
                raise ModelError("No hierarchy %s in dimension %s" %
                                 (obj, self.name))
            return self.hierarchies[obj]
        elif isinstance(obj, Hierarchy):
            return obj
        else:
            raise ValueError("Unknown hierarchy object %s (should be a "
                             "string or Hierarchy instance)" % obj)

    def attribute(self, reference, by_ref=False):
        """Get dimension attribute from `reference`."""
        if by_ref:
            return self._attributes_by_ref[str(reference)]
        else:
            try:
                return self._attributes[str(reference)]
            except KeyError:
                raise NoSuchAttributeError("Unknown attribute '%s' "
                                           "in dimension '%s'"
                                           % (str(reference), self.name),
                                           str(reference))

    def _default_hierarchy(self):
        """Get default hierarchy specified by ``default_hierarchy_name``, if
        the variable is not set then get a hierarchy with name *default*"""

        if self.default_hierarchy_name:
            hierarchy_name = self.default_hierarchy_name
        else:
            hierarchy_name = "default"

        hierarchy = self.hierarchies.get(hierarchy_name)

        if not hierarchy:
            if self.hierarchies:
                hierarchy = self.hierarchies.values()[0]
            else:
                if len(self.levels) == 1:
                    if not self._flat_hierarchy:
                        self._flat_hierarchy = Hierarchy(name=level.name,
                                                         dimension=self,
                                                         levels=[levels[0]])

                    return self._flat_hierarchy
                elif len(self.levels) > 1:
                    raise ModelError("There are no hierarchies in dimenson %s "
                                     "and there are more than one level" %
                                     self.name)
                else:
                    raise ModelError("There are no hierarchies in dimenson "
                                     "%s and there are no levels to make "
                                     "hierarchy from" % self.name)

        return hierarchy

    @property
    def is_flat(self):
        """Is true if dimension has only one level"""
        if self.master:
            return self.master.is_flat

        return len(self.levels) == 1

    def key_attributes(self):
        """Return all dimension key attributes, regardless of hierarchy. Order
        is not guaranteed, use a hierarchy to have known order."""

        return [level.key for level in self._levels.values()]

    @property
    def all_attributes(self):
        """Return all dimension attributes regardless of hierarchy. Order is
        not guaranteed, use :meth:`cubes.Hierarchy.all_attributes` to get
        known order. Order of attributes within level is preserved."""

        return list(self._attributes.values())

    def clone(self, hierarchies=None, exclude_hierarchies=None,
              nonadditive=None, default_hierarchy_name=None, cardinality=None,
              alias=None, **extra):
        """Returns a clone of the receiver with some modifications. `master`
        of the clone is set to the receiver.

        * `hierarchies` – limit hierarchies only to those specified in
          `hierarchies`. If default hierarchy name is not in the new hierarchy
          list, then the first hierarchy from the list is used.
        * `exclude_hierarchies` – all hierarchies are preserved except the
          hierarchies in this list
        * `nonadditive` – non-additive value for the dimension
        * `alias` – name of the cloned dimension
        """

        if hierarchies == []:
            raise ModelInconsistencyError("Can not remove all hierarchies"
                                          "from a dimension (%s)."
                                          % self.name)

        if hierarchies:
            linked = []
            for name in hierarchies:
                linked.append(self.hierarchy(name))
        elif exclude_hierarchies:
            linked = []
            for hierarchy in self.hierarchies.values():
                if hierarchy.name not in exclude_hierarchies:
                    linked.append(hierarchy)
        else:
            linked = self.hierarchies.values()

        hierarchies = [copy.deepcopy(hier) for hier in linked]

        if not hierarchies:
            raise ModelError("No hierarchies to clone. %s")

        # Get relevant levels
        levels = []
        seen = set()

        # Get only levels used in the hierarchies
        for hier in hierarchies:
            for level in hier.levels:
                if level.name in seen:
                    continue

                levels.append(level)
                seen.add(level.name)

        # Dis-own the level attributes (we already have a copy)
        for level in levels:
            for attribute in level.attributes:
                attribute.dimension = None

        nonadditive = nonadditive or self.nonadditive
        cardinality = cardinality or self.cardinality

        # We are not checking whether the default hierarchy name provided is
        # valid here, as it was specified explicitly with user's knowledge and
        # we might fail later. However, we need to check the existing default
        # hierarchy name and replace it with first available hierarchy if it
        # is invalid.

        if not default_hierarchy_name:
            hier = self.default_hierarchy_name

            if any(hier.name == self.default_hierarchy_name for hier in hierarchies):
                default_hierarchy_name = self.default_hierarchy_name
            else:
                default_hierarchy_name = hierarchies[0].name

        # TODO: should we do deppcopy on info?
        name = alias or self.name

        return Dimension(name=name,
                         levels=levels,
                         hierarchies=hierarchies,
                         default_hierarchy_name=default_hierarchy_name,
                         label=self.label,
                         description=self.description,
                         info=self.info,
                         role=self.role,
                         cardinality=cardinality,
                         master=self,
                         nonadditive=nonadditive,
                         **extra)

    def to_dict(self, **options):
        """Return dictionary representation of the dimension"""

        out = super(Dimension, self).to_dict(**options)

        hierarchy_limits = options.get("hierarchy_limits")

        out["default_hierarchy_name"] = self.hierarchy().name

        out["role"] = self.role
        out["cardinality"] = self.cardinality
        out["category"] = self.category

        out["levels"] = [level.to_dict(**options) for level in self.levels]

        # Collect hierarchies and apply hierarchy depth restrictions
        hierarchies = []
        hierarchy_limits = hierarchy_limits or {}
        for name, hierarchy in self.hierarchies.items():
            if name in hierarchy_limits:
                level = hierarchy_limits[name]
                if level:
                    depth = hierarchy.level_index(level) + 1
                    restricted = hierarchy.to_dict(depth=depth, **options)
                    hierarchies.append(restricted)
                else:
                    # we ignore the hierarchy
                    pass
            else:
                hierarchies.append(hierarchy.to_dict(**options))

        out["hierarchies"] = hierarchies

        # Use only for reading, during initialization these keys are ignored,
        # as they are derived
        # They are provided here for convenience.
        out["is_flat"] = self.is_flat
        out["has_details"] = self.has_details

        return out

    def validate(self):
        """Validate dimension. See Model.validate() for more information. """
        results = []

        if not self.levels:
            results.append(('error', "No levels in dimension '%s'"
                            % (self.name)))
            return results

        if not self.hierarchies:
            msg = "No hierarchies in dimension '%s'" % (self.name)
            if self.is_flat:
                level = self.levels[0]
                results.append(('default',
                                msg + ", flat level '%s' will be used" %
                                      (level.name)))
            elif len(self.levels) > 1:
                results.append(('error',
                                msg + ", more than one levels exist (%d)" %
                                      len(self.levels)))
            else:
                results.append(('error', msg))
        else:  # if self.hierarchies
            if not self.default_hierarchy_name:
                if len(self.hierarchies) > 1 and \
                        not "default" in self.hierarchies:
                    results.append(('error',
                                    "No defaut hierarchy specified, there is "
                                    "more than one hierarchy in dimension "
                                    "'%s'" % self.name))

        if self.default_hierarchy_name \
                and not self.hierarchies.get(self.default_hierarchy_name):
            results.append(('error',
                            "Default hierarchy '%s' does not exist in "
                            "dimension '%s'" %
                            (self.default_hierarchy_name, self.name)))

        attributes = set()
        first_occurence = {}

        for level_name, level in self._levels.items():
            if not level.attributes:
                results.append(('error',
                                "Level '%s' in dimension '%s' has no "
                                "attributes" % (level.name, self.name)))
                continue

            if not level.key:
                attr = level.attributes[0]
                results.append(('default',
                                "Level '%s' in dimension '%s' has no key "
                                "attribute specified, first attribute will "
                                "be used: '%s'"
                                % (level.name, self.name, attr)))

            if level.attributes and level.key:
                if level.key.name not in [a.name for a in level.attributes]:
                    results.append(('error',
                                    "Key '%s' in level '%s' in dimension "
                                    "'%s' is not in level's attribute list"
                                    % (level.key, level.name, self.name)))

            for attribute in level.attributes:
                attr_name = attribute.ref()
                if attr_name in attributes:
                    first = first_occurence[attr_name]
                    results.append(('error',
                                    "Duplicate attribute '%s' in dimension "
                                    "'%s' level '%s' (also defined in level "
                                    "'%s')" % (attribute, self.name,
                                               level_name, first)))
                else:
                    attributes.add(attr_name)
                    first_occurence[attr_name] = level_name

                if not isinstance(attribute, Attribute):
                    results.append(('error',
                                    "Attribute '%s' in dimension '%s' is "
                                    "not instance of Attribute"
                                    % (attribute, self.name)))

                if attribute.dimension is not self:
                    results.append(('error',
                                    "Dimension (%s) of attribute '%s' does "
                                    "not match with owning dimension %s"
                                    % (attribute.dimension, attribute,
                                       self.name)))

        return results

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<dimension: {name: '%s', levels: %s}>" % (self.name,
                                                          self._levels.keys())

    def localize(self, locale):
        localize_common(self, locale)

        attr_locales = locale.get("attributes", {})

        for attrib in self.all_attributes:
            if attrib.name in attr_locales:
                localize_common(attrib, attr_locales[attrib.name])

        level_locales = locale.get("levels") or {}
        for level in self.levels:
            level_locale = level_locales.get(level.name)
            if level_locale:
                level.localize(level_locale)

        hier_locales = locale.get("hierarcies")
        if hier_locales:
            for hier in self.hierarchies:
                hier_locale = hier_locales.get(hier.name)
                hier.localize(hier_locale)

    def localizable_dictionary(self):
        locale = {}
        locale.update(get_localizable_attributes(self))

        ldict = {}
        locale["levels"] = ldict

        for level in self.levels:
            ldict[level.name] = level.localizable_dictionary()

        hdict = {}
        locale["hierarchies"] = hdict

        for hier in self.hierarchies.values():
            hdict[hier.name] = hier.localizable_dictionary()

        return locale


class Hierarchy(ModelObject):
    def __init__(self, name, levels, label=None, info=None, description=None):
        """Dimension hierarchy - specifies order of dimension levels.

        Attributes:

        * `name`: hierarchy name
        * `levels`: ordered list of levels or level names from `dimension`

        * `label`: human readable name
        * `description`: user description of the hierarchy
        * `info` - custom information dictionary, might be used to store
          application/front-end specific information

        Some collection operations might be used, such as ``level in hierarchy``
        or ``hierarchy[index]``. String value ``str(hierarchy)`` gives the
        hierarchy name.

        Note: The `levels` should have attributes already owned by a
        dimension.
        """

        super(Hierarchy, self).__init__(name, label, description, info)

        if not levels:
            raise ModelInconsistencyError("Hierarchy level list should not be "
                                          "empty (in %s)" % self.name)

        if any(isinstance(level, basestring) for level in levels):
            raise ModelInconsistencyError("Levels should not be provided as "
                                          "strings to Hierarchy.")

        self._levels = OrderedDict()
        for level in levels:
            self._levels[level.name] = level

    def __deepcopy__(self, memo):
        return Hierarchy(self.name,
                         label=self.label,
                         description=self.description,
                         info=copy.deepcopy(self.info, memo),
                         levels=copy.deepcopy(self._levels.values(), memo))

    @property
    def levels(self):
        return self._levels.values()

    @property
    def level_names(self):
        return self._levels.keys()

    def __eq__(self, other):
        if not other or type(other) != type(self):
            return False
        elif self.name != other.name or self.label != other.label:
            return False
        elif self.levels != other.levels:
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return self.name

    def __len__(self):
        return len(self.levels)

    def __getitem__(self, item):
        try:
            return self.levels[item]
        except IndexError:
            raise HierarchyError("Hierarchy '%s' has only %d levels, "
                                 "asking for deeper level"
                                 % (self.name, len(self._levels)))

    def __contains__(self, item):
        if item in self.levels:
            return True
        return item in [level.name for level in self.levels]

    def levels_for_path(self, path, drilldown=False):
        """Returns levels for given path. If path is longer than hierarchy
        levels, `cubes.ArgumentError` exception is raised"""

        depth = 0 if not path else len(path)
        return self.levels_for_depth(depth, drilldown)

    def levels_for_depth(self, depth, drilldown=False):
        """Returns levels for given `depth`. If `path` is longer than
        hierarchy levels, `cubes.ArgumentError` exception is raised"""

        depth = depth or 0
        extend = 1 if drilldown else 0

        if depth + extend > len(self.levels):
            raise HierarchyError("Depth %d is longer than hierarchy "
                                 "levels %s (drilldown: %s)" %
                                 (depth, self._levels.keys(), drilldown))

        return self.levels[0:depth + extend]

    def next_level(self, level):
        """Returns next level in hierarchy after `level`. If `level` is last
        level, returns ``None``. If `level` is ``None``, then the first level
        is returned."""

        if not level:
            return self.levels[0]

        index = self._levels.keys().index(str(level))
        if index + 1 >= len(self.levels):
            return None
        else:
            return self.levels[index + 1]

    def previous_level(self, level):
        """Returns previous level in hierarchy after `level`. If `level` is
        first level or ``None``, returns ``None``"""

        if level is None:
            return None

        index = self._levels.keys().index(str(level))
        if index == 0:
            return None
        else:
            return self.levels[index - 1]

    def level_index(self, level):
        """Get order index of level. Can be used for ordering and comparing
        levels within hierarchy."""
        try:
            return self._levels.keys().index(str(level))
        except ValueError:
            raise HierarchyError("Level %s is not part of hierarchy %s"
                                 % (str(level), self.name))

    def is_last(self, level):
        """Returns `True` if `level` is last level of the hierarchy."""

        return level == self.levels[-1]

    def rollup(self, path, level=None):
        """Rolls-up the path to the `level`. If `level` is ``None`` then path
        is rolled-up only one level.

        If `level` is deeper than last level of `path` the
        `cubes.HierarchyError` exception is raised. If `level` is the same as
        `path` level, nothing happens."""

        if level:
            last = self.level_index(level) + 1
            if last > len(path):
                raise HierarchyError("Can not roll-up: level '%s' – it is "
                                     "deeper than deepest element of path %s" %
                                     (str(level), path))
        else:
            if len(path) > 0:
                last = len(path) - 1
            else:
                last = None

        if last is None:
            return []
        else:
            return path[0:last]

    def path_is_base(self, path):
        """Returns True if path is base path for the hierarchy. Base path is a
        path where there are no more levels to be added - no drill down
        possible."""

        return path is not None and len(path) == len(self.levels)

    def key_attributes(self):
        """Return all dimension key attributes as a single list."""

        return [level.key for level in self.levels]

    @property
    def all_attributes(self):
        """Return all dimension attributes as a single list."""

        attributes = []
        for level in self.levels:
            attributes.extend(level.attributes)

        return attributes

    def to_dict(self, depth=None, **options):
        """Convert to dictionary. Keys:

        * `name`: hierarchy name
        * `label`: human readable label (localizable)
        * `levels`: level names

        """

        out = super(Hierarchy, self).to_dict(**options)

        levels = [str(l) for l in self.levels]

        if depth:
            out["levels"] = levels[0:depth]
        else:
            out["levels"] = levels
        out["info"] = self.info

        return out

    def localize(self, locale):
        localize_common(self, locale)

    def localizable_dictionary(self):
        locale = {}
        locale.update(get_localizable_attributes(self))

        return locale


class Level(ModelObject):
    """Object representing a hierarchy level. Holds all level attributes.

    This object is immutable, except localization. You have to set up all
    attributes in the initialisation process.

    Attributes:

    * `name`: level name
    * `attributes`: list of all level attributes. Raises `ModelError` when
      `attribute` list is empty.
    * `key`: name of level key attribute (for example: ``customer_number`` for
      customer level, ``region_code`` for region level, ``month`` for month
      level).  key will be used as a grouping field for aggregations. Key
      should be unique within level. If not specified, then the first
      attribute is used as key.
    * `order`: ordering of the level. `asc` for ascending, `desc` for
      descending or might be unspecified.
    * `order_attribute`: name of attribute that is going to be used for
      sorting, default is first attribute (usually key)
    * `label_attribute`: name of attribute containing label to be displayed
      (for example: ``customer_name`` for customer level, ``region_name`` for
      region level, ``month_name`` for month level)
    * `label`: human readable label of the level
    * `role`: role of the level within a special dimension
    * `info`: custom information dictionary, might be used to store
      application/front-end specific information
    * `cardinality` – approximation of the number of level's members. Used
      optionally by backends and front ends.
    * `nonadditive` – kind of non-additivity of the level. Possible
      values: `None` (fully additive, default), ``time`` (non-additive for
      time dimensions) or ``all`` (non-additive for any other dimension)

    Cardinality values:

    * ``tiny`` – few values, each value can have it's representation on the
      screen, recommended: up to 5.
    * ``low`` – can be used in a list UI element, recommended 5 to 50 (if sorted)
    * ``medium`` – UI element is a search/text field, recommended for more than 50
      elements
    * ``high`` – backends might refuse to yield results without explicit
      pagination or cut through this level.

    Note: the `attributes` are going to be owned by the `dimension`.

    """

    def __init__(self, name, attributes, key=None, order_attribute=None,
                 order=None, label_attribute=None, label=None, info=None,
                 cardinality=None, role=None, nonadditive=None,
                 description=None):

        super(Level, self).__init__(name, label, description, info)

        self.cardinality = cardinality
        self.role = role

        if not attributes:
            raise ModelError("Attribute list should not be empty")

        self.attributes = attribute_list(attributes)

        # Note: synchronize with Measure.__init__ if relevant/necessary
        if not nonadditive or nonadditive == "none":
            self.nonadditive = None
        elif nonadditive in ["all", "any"]:
            self.nonadditive = "all"
        elif nonadditive != "time":
            raise ModelError("Unknown non-additive diension type '%s'"
                             % nonadditive)
        self.nonadditive = nonadditive

        if key:
            self.key = self.attribute(key)
        elif len(self.attributes) >= 1:
            self.key = self.attributes[0]
        else:
            raise ModelInconsistencyError("Attribute list should not be empty")

        # Set second attribute to be label attribute if label attribute is not
        # set. If dimension is flat (only one attribute), then use the only
        # key attribute as label.

        if label_attribute:
            self.label_attribute = self.attribute(label_attribute)
        else:
            if len(self.attributes) > 1:
                self.label_attribute = self.attributes[1]
            else:
                self.label_attribute = self.key

        # Set first attribute to be order attribute if order attribute is not
        # set

        if order_attribute:
            try:
                self.order_attribute = self.attribute(order_attribute)
            except NoSuchAttributeError:
                raise NoSuchAttributeError("Unknown order attribute %s in "
                                           "dimension %s, level %s" %
                                           (order_attribute,
                                            str(self.dimension), self.name))
        else:
            self.order_attribute = self.attributes[0]

        self.order = order

        self.cardinality = cardinality

    def __eq__(self, other):
        if not other or type(other) != type(self):
            return False
        elif self.name != other.name \
                or self.label != other.label \
                or self.key != other.key \
                or self.cardinality != other.cardinality \
                or self.role != other.role \
                or self.label_attribute != other.label_attribute \
                or self.order_attribute != other.order_attribute \
                or self.nonadditive != other.nonadditive \
                or self.attributes != other.attributes:
            return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self.to_dict())

    def __deepcopy__(self, memo):
        if self.order_attribute:
            order_attribute = str(self.order_attribute)
        else:
            order_attribute = None

        return Level(self.name,
                     attributes=copy.deepcopy(self.attributes, memo),
                     key=self.key.name,
                     order_attribute=order_attribute,
                     order=self.order,
                     label_attribute=self.label_attribute.name,
                     info=copy.copy(self.info),
                     label=copy.copy(self.label),
                     cardinality=self.cardinality,
                     nonadditive=self.nonadditive,
                     role=self.role
                     )

    def to_dict(self, full_attribute_names=False, **options):
        """Convert to dictionary"""

        out = super(Level, self).to_dict(**options)

        out["role"] = self.role

        if full_attribute_names:
            out["key"] = self.key.ref()
            out["label_attribute"] = self.label_attribute.ref()
            out["order_attribute"] = self.order_attribute.ref()
        else:
            out["key"] = self.key.name
            out["label_attribute"] = self.label_attribute.name
            out["order_attribute"] = self.order_attribute.name

        out["order"] = self.order
        out["cardinality"] = self.cardinality
        out["nonadditive"] = self.nonadditive

        out["attributes"] = [attr.to_dict(**options) for attr in
                             self.attributes]
        return out

    def attribute(self, name):
        """Get attribute by `name`"""

        attrs = [attr for attr in self.attributes if attr.name == name]

        if attrs:
            return attrs[0]
        else:
            raise NoSuchAttributeError(name)

    @property
    def has_details(self):
        """Is ``True`` when level has more than one attribute, for all levels
        with only one attribute it is ``False``."""

        return len(self.attributes) > 1

    def localize(self, locale):
        localize_common(self, locale)

        if isinstance(locale, basestring):
            return

        attr_locales = locale.get("attributes")
        if attr_locales:
            logger = get_logger()
            logger.warn("'attributes' in localization dictionary of levels "
                        "is depreciated. Use list of `attributes` in "
                        "localization of dimension")

            for attrib in self.attributes:
                if attrib.name in attr_locales:
                    localize_common(attrib, attr_locales[attrib.name])

    def localizable_dictionary(self):
        locale = {}
        locale.update(get_localizable_attributes(self))

        adict = {}
        locale["attributes"] = adict

        for attribute in self.attributes:
            adict[attribute.name] = attribute.localizable_dictionary()

        return locale


class AttributeBase(ModelObject):
    ASC = 'asc'
    DESC = 'desc'

    def __init__(self, name, label=None, description=None, order=None,
                 info=None, format=None, missing_value=None, **kwargs):
        """Base class for dimension attributes, measures and measure
        aggregates.

        Attributes:

        * `name` - attribute name, used as identifier
        * `label` - attribute label displayed to a user
        * `order` - default order of this attribute. If not specified, then
          order is unexpected. Possible values are: ``'asc'`` or ``'desc'``.
          It is recommended and safe to use ``Attribute.ASC`` and
          ``Attribute.DESC``
        * `info` - custom information dictionary, might be used to store
          application/front-end specific information
        * `format` - application-specific display format information, useful
          for formatting numeric values of measure attributes
        * `missing_value` – value to be used when there is no value (``NULL``)
          in the data source. Support of this attribute property depends on the
          backend. Please consult the backend documentation for more
          information.

        String representation of the `AttributeBase` returns its `name`.

        `cubes.ArgumentError` is raised when unknown ordering type is
        specified.
        """
        super(AttributeBase, self).__init__(name, label, description, info)

        self.format = format
        self.missing_value = missing_value
        # TODO: temporarily preserved, this should be present only in
        # Attribute object, not all kinds of attributes
        self.dimension = None

        if order:
            self.order = order.lower()
            if self.order.startswith("asc"):
                self.order = Attribute.ASC
            elif self.order.startswith("desc"):
                self.order = Attribute.DESC
            else:
                raise ArgumentError("Unknown ordering '%s' for attributes"
                                    " '%s'" % (order, self.ref()))
        else:
            self.order = None

    def __str__(self):
        return self.name

    def __repr__(self):
        return repr(self.to_dict())

    def __eq__(self, other):
        if not isinstance(other, AttributeBase):
            return False

        # TODO: should we be this strict?
        return self.name == other.name \
            and self.label == other.label \
            and self.info == other.info \
            and self.description == other.description \
            and self.format == other.format \
            and self.missing_value == other.missing_value

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.ref())

    def to_dict(self, **options):
        d = super(AttributeBase, self).to_dict(**options)

        d["format"] = self.format
        d["order"] = self.order
        d["missing_value"] = self.missing_value

        d["ref"] = self.ref()

        return d

    def localizable_dictionary(self):
        locale = {}
        locale.update(get_localizable_attributes(self))

        return locale

    def is_localizable(self):
        return False

    def ref(self, simplify=None, locale=None):
        return self.name


class Attribute(AttributeBase):

    def __init__(self, name, label=None, description=None, order=None,
                 info=None, format=None, dimension=None, locales=None,
                 missing_value=None, **kwargs):
        """Dimension attribute object. Also used as fact detail.

        Attributes:

        * `name` - attribute name, used as identifier
        * `label` - attribute label displayed to a user
        * `locales` = list of locales that the attribute is localized to
        * `order` - default order of this attribute. If not specified, then
          order is unexpected. Possible values are: ``'asc'`` or ``'desc'``.
          It is recommended and safe to use ``Attribute.ASC`` and
          ``Attribute.DESC``
        * `info` - custom information dictionary, might be used to store
          application/front-end specific information
        * `format` - application-specific display format information, useful
          for formatting numeric values of measure attributes

        String representation of the `Attribute` returns its `name` (without
        dimension prefix).

        `cubes.ArgumentError` is raised when unknown ordering type is
        specified.
        """

        super(Attribute, self).__init__(name=name, label=label,
                                        description=description, order=order,
                                        info=info, format=format,
                                        missing_value=missing_value)

        self.dimension = dimension
        self.locales = locales or []

    def __deepcopy__(self, memo):
        return Attribute(self.name,
                         self.label,
                         dimension=self.dimension,
                         locales=copy.deepcopy(self.locales, memo),
                         order=copy.deepcopy(self.order, memo),
                         description=self.description,
                         info=copy.deepcopy(self.info, memo),
                         format=self.format,
                         missing_value=self.missing_value)

    def __eq__(self, other):
        if not super(Attribute, self).__eq__(other):
            return False

        return str(self.dimension) == str(other.dimension) \
               and self.locales == other.locales

    def to_dict(self, **options):
        # FIXME: Depreciated key "full_name" in favour of "ref"
        d = super(Attribute, self).to_dict(**options)

        d["locales"] = self.locales

        return d

    def ref(self, simplify=True, locale=None):
        """Return full attribute reference. Append `locale` if it is one of
        attribute's locales, otherwise raise `cubes.ArgumentError`. If
        `simplify` is ``True``, then reference to an attribute of flat
        dimension without details will be just the dimension name.
        """
        if locale:
            if not self.locales:
                raise ArgumentError("Attribute '%s' is not loalizable "
                                    "(localization %s requested)"
                                    % (self.name, locale))
            elif locale not in self.locales:
                raise ArgumentError("Attribute '%s' has no localization %s "
                                    "(has: %s)"
                                    % (self.name, locale, self.locales))
            else:
                locale_suffix = "." + locale
        else:
            locale_suffix = ""

        if self.dimension:
            if simplify and (self.dimension.is_flat
                             and not self.dimension.has_details):
                reference = self.dimension.name
            else:
                reference = self.dimension.name + '.' + str(self.name)
        else:
            reference = str(self.name)

        return reference + locale_suffix

    def is_localizable(self):
        return bool(self.locales)


def create_measure(md):
    """Create a measure object from metadata."""
    if isinstance(md, basestring):
        md = {"name": md}

    if not "name" in md:
        raise ModelError("Measure has no name.")

    md = dict(md)
    if "aggregations" in md:
        md["aggregates"] = md.pop("aggregations")

    return Measure(**md)


class Measure(AttributeBase):

    def __init__(self, name, label=None, description=None, order=None,
                 info=None, format=None, missing_value=None, aggregates=None,
                 formula=None, expression=None, nonadditive=None,
                 window_size=None, **kwargs):
        """Fact measure attribute.

        Properties in addition to the attribute base properties:

        * `formula` – name of a formula for the measure
        * `aggregates` – list of default (relevant) aggregate functions that
          can be applied to this measure attribute.
        * `nonadditive` – kind of non-additivity of the dimension. Possible
          values: `none` (fully additive, default), ``time`` (non-additive for
          time dimensions) or ``all`` (non-additive for any other dimension)

        Note that if the `formula` is specified, it should not refer to any
        other measure that refers to this one (no circular reference).

        The `aggregates` is an optional property and is used for:
        * measure aggergate object preparation
        * optional validation

        String representation of a `Measure` returns its `name`.
        """
        super(Measure, self).__init__(name=name, label=label,
                                      description=description, order=order,
                                      info=info, format=format, missing_value=None)

        self.expression = expression
        self.formula = formula
        self.aggregates = aggregates
        self.window_size = window_size

        # Note: synchronize with Dimension.__init__ if relevant/necessary
        if not nonadditive or nonadditive == "none":
            self.nonadditive = None
        elif nonadditive in ["all", "any"]:
            self.nonadditive = "any"
        elif nonadditive == "time":
            self.nonadditive = "time"
        else:
            raise ModelError("Unknown non-additive measure type '%s'"
                             % nonadditive)

    def __deepcopy__(self, memo):
        return Measure(self.name, self.label,
                       order=copy.deepcopy(self.order, memo),
                       description=self.description,
                       info=copy.deepcopy(self.info, memo),
                       format=self.format,
                       missing_value=self.missing_value,
                       aggregates=self.aggregates,
                       expression=self.expression,
                       formula=self.formula,
                       nonadditive=self.nonadditive,
                       window_size=self.window_size)

    def __eq__(self, other):
        if not super(Measure, self).__eq__(other):
            return False

        return self.aggregates == other.aggregates \
                and self.formula == other.formula \
                and self.window_size == other.window_size

    def to_dict(self, **options):
        d = super(Measure, self).to_dict(**options)
        d["formula"] = self.formula
        d["aggregates"] = self.aggregates
        d["expression"] = self.expression
        d["window_size"] = self.window_size

        return d

    def default_aggregates(self):
        """Creates default measure aggregates from a list of receiver's
        measures. This is just a convenience function, correct models should
        contain explicit list of aggregates. If no aggregates are specified,
        then the only aggregate `sum` is assumed.
        """

        aggregates = []

        for agg in (self.aggregates or ["sum"]):
            if agg == "identity":
                name = u"%s" % self.name
                measure = None
                function = None
            else:
                name = u"%s_%s" % (self.name, agg)
                measure = self.name
                function = agg

            aggregate = MeasureAggregate(name=name,
                                         label=None,
                                         description=self.description,
                                         order=self.order,
                                         info=self.info,
                                         format=self.format,
                                         measure=measure,
                                         function=function,
                                         window_size=self.window_size)

            aggregate.label = _measure_aggregate_label(aggregate, self)
            aggregates.append(aggregate)

        return aggregates


def create_measure_aggregate(md):
    if isinstance(md, basestring):
        md = {"name": md}

    if not "name" in md:
        raise ModelError("Measure aggregate has no name.")

    return MeasureAggregate(**md)


class MeasureAggregate(AttributeBase):

    def __init__(self, name, label=None, description=None, order=None,
                 info=None, format=None, missing_value=None, measure=None,
                 function=None, formula=None, expression=None,
                 nonadditive=None, window_size=None, **kwargs):
        """Masure aggregate

        Attributes:

        * `function` – aggregation function for the measure
        * `formula` – name of a formula that contains the arithemtic
          expression (optional)
        * `measure` – measure name for this aggregate (optional)
        * `expression` – arithmetic expression (only if bacend supported)
        * `nonadditive` – additive behavior for the aggregate (inherited from
          the measure in most of the times)
        """

        super(MeasureAggregate, self).__init__(name=name, label=label,
                                               description=description,
                                               order=order, info=info,
                                               format=format,
                                               missing_value=missing_value)

        self.function = function
        self.formula = formula
        self.expression = expression
        self.measure = measure
        self.nonadditive = nonadditive
        self.window_size = window_size

    def __deepcopy__(self, memo):
        return MeasureAggregate(self.name,
                                self.label,
                                order=copy.deepcopy(self.order, memo),
                                description=self.description,
                                info=copy.deepcopy(self.info, memo),
                                format=self.format,
                                missing_value=self.missing_value,
                                measure=self.measure,
                                function=self.function,
                                formula=self.formula,
                                expression=self.expression,
                                nonadditive=self.nonadditive,
                                window_size=self.window_size)

    def __eq__(self, other):
        if not super(Attribute, self).__eq__(other):
            return False

        return str(self.function) == str(other.function) \
            and self.measure == other.measure \
            and self.formula == other.formula \
            and self.expression == other.expression \
            and self.nonadditive == other.nonadditive \
            and self.window_size == other.window_size

    def to_dict(self, **options):
        d = super(MeasureAggregate, self).to_dict(**options)
        d["function"] = self.function
        d["formula"] = self.formula
        d["expression"] = self.expression
        d["measure"] = self.measure
        d["nonadditive"] = self.nonadditive
        d["window_size"] = self.window_size

        return d


def create_attribute(obj, class_=None):
    """Makes sure that the `obj` is an ``Attribute`` instance. If `obj` is a
    string, then new instance is returned. If it is a dictionary, then the
    dictionary values are used for ``Attribute`` instance initialization."""

    class_ = class_ or Attribute

    if isinstance(obj, basestring):
        return class_(obj)
    elif isinstance(obj, dict):
        return class_(**obj)
    else:
        return obj


def attribute_list(attributes, class_=None):
    """Create a list of attributes from a list of strings or dictionaries.
    see :func:`cubes.coalesce_attribute` for more information."""

    if not attributes:
        return []

    result = [create_attribute(attr, class_) for attr in attributes]

    return result


def aggregate_list(aggregates):
    """Create a list of aggregates from aggregate metadata dictionaries (or
    list of names)"""
    return attribute_list(aggregates, class_=MeasureAggregate)


def measure_list(measures):
    """Create a list of measures from list of measure metadata (dictionaries
    or strings). The function tries to maintain cetrain level of backward
    compatibility with older models."""

    result = []

    for md in measures or []:
        if isinstance(md, Measure):
            result.append(md)
            continue

        if isinstance(md, basestring):
            md = {"name": md}
        else:
            md = dict(md)

        if "aggregations" in md and "aggregates" in md:
            raise ModelError("Both 'aggregations' and 'aggregates' specified "
                             "in a measure. Use only 'aggregates'")

        if "aggregations" in md:
            logger = get_logger()
            logger.warn("'aggregations' is depreciated, use 'aggregates'")
            md["aggregates"] = md.pop("aggregations")

        # Add default aggregation for 'sum' (backward compatibility)
        if not "aggregates" in md:
            md["aggregates"] = ["sum"]

        result.append(create_measure(md))

    return result


def create_cube(metadata):
    """Create a cube object from `metadata` dictionary. The cube has no
    dimensions attached after creation. You should link the dimensions to the
    cube according to the `Cube.dimension_links` property using
    `Cube.add_dimension()`"""

    if "name" not in metadata:
        raise ModelError("Cube has no name")

    metadata = expand_cube_metadata(metadata)
    dimension_links = metadata.pop("dimensions", [])

    if "measures" not in metadata and "aggregates" not in metadata:
        metadata["aggregates"] = [DEFAULT_FACT_COUNT_AGGREGATE]

    # Prepare aggregate and measure lists, do implicit merging

    details = attribute_list(metadata.pop("details", []), Attribute)
    measures = measure_list(metadata.pop("measures", []))

    # Inherit the nonadditive property in each measure
    nonadditive = metadata.pop("nonadditive", None)
    if nonadditive:
        for measure in measures:
            measure.nonadditive = nonadditive

    aggregates = metadata.pop("aggregates", [])
    aggregates = aggregate_list(aggregates)
    aggregate_dict = dict((a.name, a) for a in aggregates)
    measure_dict = dict((m.name, m) for m in measures)

    # TODO: change this to False in the future?
    if metadata.get("implicit_aggregates", True):
        implicit_aggregates = []
        for measure in measures:
            implicit_aggregates += measure.default_aggregates()

        for aggregate in implicit_aggregates:
            # an existing aggregate either has the same name,
            existing = aggregate_dict.get(aggregate.name)
            if existing:
                if existing.function != aggregate.function:
                    raise ModelError("Aggregate '%s' function mismatch. "
                                     "Implicit function %s, explicit function:"
                                     " %s." % (aggregate.name,
                                               aggregate.function,
                                               existing.function))
                continue
            # or the same function and measure
            existing = [ agg for agg in aggregates if agg.function == aggregate.function and agg.measure == measure.name ]
            if existing:
                continue
            aggregates.append(aggregate)
            aggregate_dict[aggregate.name] = aggregate

    # Assign implicit aggregate labels
    # TODO: make this configurable

    for aggregate in aggregates:
        try:
            measure = measure_dict[aggregate.measure]
        except KeyError:
            measure = aggregate_dict.get(aggregate.measure)

        if aggregate.label is None:
            aggregate.label = _measure_aggregate_label(aggregate, measure)

        # Inherit nonadditive property from the measure
        if measure and aggregate.nonadditive is None:
            aggregate.nonadditive = measure.nonadditive

    return Cube(measures=measures,
                aggregates=aggregates,
                dimension_links=dimension_links,
                details=details,
                **metadata)

def _measure_aggregate_label(aggregate, measure):
    function = aggregate.function
    template = IMPLICIT_AGGREGATE_LABELS.get(function, "{measure}")

    if aggregate.label is None and template:

        if measure:
            measure_label = measure.label or measure.name
        else:
            measure_label = aggregate.measure

        label = template.format(measure=measure_label)

    return label


def create_dimension(metadata, templates=None):
    """Create a dimension from a `metadata` dictionary.
    Some rules:

    * ``levels`` might contain level names as strings – names of levels to
      inherit from the template
    * ``hierarchies`` might contain hierarchies as strings – names of
      hierarchies to inherit from the template
    * all levels that are not covered by hierarchies are not included in the
      final dimension
    """

    templates = templates or {}

    if "template" in metadata:
        template_name = metadata["template"]
        try:
            template = templates[template_name]
        except KeyError:
            raise TemplateRequired(template_name)

        levels = copy.deepcopy(template.levels)

        # Dis-own the level attributes
        for level in levels:
            for attribute in level.attributes:
                attribute.dimension = None

        # Create copy of template's hierarchies, but reference newly
        # created copies of level objects
        hierarchies = []
        level_dict = dict((level.name, level) for level in levels)

        for hier in template.hierarchies.values():
            hier_levels = [level_dict[level.name] for level in hier.levels]
            hier_copy = Hierarchy(hier.name,
                                  hier_levels,
                                  label=hier.label,
                                  info=copy.deepcopy(hier.info))
            hierarchies.append(hier_copy)

        default_hierarchy_name = template.default_hierarchy_name
        label = template.label
        description = template.description
        info = template.info
        cardinality = template.cardinality
        role = template.role
        category = template.category
        nonadditive = template.nonadditive
    else:
        template = None
        levels = []
        hierarchies = []
        default_hierarchy_name = None
        label = None
        description = None
        cardinality = None
        role = None
        category = None
        info = {}
        nonadditive = None

    # Fix the metadata, but don't create default level if the template
    # provides levels.
    metadata = expand_dimension_metadata(metadata,
                                         expand_levels=not bool(levels))

    name = metadata.get("name")

    label = metadata.get("label", label)
    description = metadata.get("description") or description
    info = metadata.get("info", info)
    role = metadata.get("role", role)
    category = metadata.get("category", category)
    nonadditive = metadata.get("nonadditive", nonadditive)

    # Backward compatibility with an experimental feature
    cardinality = metadata.get("cardinality", cardinality)

    # Backward compatibility with an experimental feature:
    if not cardinality:
        info = metadata.get("info", {})
        if "high_cardinality" in info:
           cardinality = "high"

    # Levels
    # ------

    # We are guaranteed to have "levels" key from expand_dimension_metadata()

    if "levels" in metadata:
        # Assure level inheritance
        levels = []
        for level_md in metadata["levels"]:
            if isinstance(level_md, basestring):
                if not template:
                    raise ModelError("Can not specify just a level name "
                                     "(%s) if there is no template for "
                                     "dimension %s" % (md, name))
                level = template.level(level_md)
            else:
                level = create_level(level_md)
                # raise NotImplementedError("Merging of levels is not yet supported")

            # Update the level's info dictionary
            if template:
                try:
                    templevel = template.level(level.name)
                except KeyError:
                    pass
                else:
                    new_info = copy.deepcopy(templevel.info)
                    new_info.update(level.info)
                    level.info = new_info

            levels.append(level)

    # Hierarchies
    # -----------
    if "hierarchies" in metadata:
        hierarchies_defined = True
        hierarchies = _create_hierarchies(metadata["hierarchies"],
                                          levels,
                                          template)
    else:
        hierarchies_defined = False
        # Keep only hierarchies which include existing levels
        level_names = set([level.name for level in levels])
        keep = []
        for hier in hierarchies:
            if any(level.name not in level_names for level in hier.levels):
                continue
            else:
                keep.append(hier)
        hierarchies = keep


    default_hierarchy_name = metadata.get("default_hierarchy_name",
                                          default_hierarchy_name)

    if not hierarchies:
        # Create single default hierarchy
        hierarchies = [Hierarchy("default", levels=levels)]

    # Recollect levels – keep only those levels that are present in
    # hierarchies. Retain the original level order
    used_levels = set()
    for hier in hierarchies:
        used_levels |= set(level.name for level in hier.levels)

    levels = [level for level in levels if level.name in used_levels]

    return Dimension(name=name,
                     levels=levels,
                     hierarchies=hierarchies,
                     default_hierarchy_name=default_hierarchy_name,
                     label=label,
                     description=description,
                     info=info,
                     cardinality=cardinality,
                     role=role,
                     category=category,
                     nonadditive=nonadditive
                    )

def _create_hierarchies(metadata, levels, template):
    """Create dimension hierarchies from `metadata` (a list of dictionaries or
    strings) and possibly inherit from `template` dimension."""

    # Convert levels do an ordered dictionary for access by name
    levels = OrderedDict((level.name, level) for level in levels)
    hierarchies = []

    # Construct hierarchies and assign actual level objects
    for md in metadata:
        if isinstance(md, basestring):
            if not template:
                raise ModelError("Can not specify just a hierarchy name "
                                 "(%s) if there is no template for "
                                 "dimension %s" % (md, name))
            hier = template.hierarchy(md)
        else:
            md = dict(md)
            level_names = md.pop("levels")
            hier_levels = [levels[level] for level in level_names]
            hier = Hierarchy(levels=hier_levels, **md)

        hierarchies.append(hier)

    return hierarchies

def create_level(metadata, name=None, dimension=None):
    """Create a level object from metadata. `name` can override level name in
    the metadata."""

    metadata = dict(expand_level_metadata(metadata))

    try:
        name = name or metadata.pop("name")
    except KeyError:
        raise ModelError("No name specified in level metadata")

    attributes = attribute_list(metadata.pop("attributes"))

    # TODO: this should be depreciated
    for attribute in attributes:
        attribute.dimension = dimension

    return Level(name=name,
                 attributes=attributes,
                 **metadata)


def localize_common(obj, trans):
    """Localize common attributes: label and description. `trans` should be a
    dictionary or a string. If it is just a string, then only `label` will be
    localized."""
    if isinstance(trans, basestring):
        obj.label = trans
    else:
        if "label" in trans:
            obj.label = trans["label"]
        if "description" in trans:
            obj.description = trans["description"]


def localize_attributes(attribs, translations):
    """Localize list of attributes. `translations` should be a dictionary with
    keys as attribute names, values are dictionaries with localizable
    attribute metadata, such as ``label`` or ``description``."""
    for (name, atrans) in translations.items():
        attrib = attribs[name]
        localize_common(attrib, atrans)


def get_localizable_attributes(obj):
    """Returns a dictionary with localizable attributes of `obj`."""

    # FIXME: use some kind of class attribute to get list of localizable
    # attributes

    locale = {}
    if hasattr(obj, "label"):
        locale["label"] = obj.label

    if hasattr(obj, "description"):
        locale["description"] = obj.description

    return locale


########NEW FILE########
__FILENAME__ = providers
# -*- coding: utf-8 -*-
"""Logical model model providers."""
import copy
import json
import re

from .logging import get_logger
from .errors import *
from .model import *
from .metadata import *
from .extensions import Extensible

__all__ = [
    "ModelProvider",
    "StaticModelProvider",

    # FIXME: Depreciated
    "load_model",
    "model_from_path",
    "create_model",
]


def load_model(resource, translations=None):
    raise Exception("load_model() was replaced by Workspace.import_model(), "
                    "please refer to the documentation for more information")


class ModelProvider(Extensible):
    """Abstract class. Currently empty and used only to find other model
    providers."""

    def __init__(self, metadata=None):
        """Base class for model providers. Initializes a model provider and
        sets `metadata` – a model metadata dictionary.

        Instance variable `store` might be populated after the
        initialization. If the model provider requires an open store, it
        should advertise it through `True` value returned by provider's
        `requires_store()` method.  Otherwise no store is opened for the model
        provider. `store_name` is also set.

        Subclasses should call this method at the beginning of the custom
        `__init__()`.

        If a model provider subclass has a metadata that should be pre-pended
        to the user-provided metadta, it should return it in
        `default_metadata()`.

        Subclasses should implement at least: :meth:`cubes.ModelProvider.cube`,
        :meth:`cubes.ModelProvider.dimension` and
        :meth:`cubes.ModelProvider.list_cubes`
        """

        self.store = None
        self.store_name = None

        # Get provider's defaults and pre-pend it to the user provided
        # metadtata.
        defaults = self.default_metadata()
        self.metadata = self._merge_metadata(defaults, metadata)

        # TODO: check for duplicates
        self.dimensions_metadata = {}
        for dim in self.metadata.get("dimensions", []):
            self.dimensions_metadata[dim["name"]] = dim

        self.cubes_metadata = {}
        for cube in self.metadata.get("cubes", []):
            self.cubes_metadata[cube["name"]] = cube

        # TODO: decide which one to use
        self.options = self.metadata.get("options", {})
        self.options.update(self.metadata.get("browser_options", {}))

    def _merge_metadata(self, metadata, other):
        """See `default_metadata()` for more information."""

        metadata = dict(metadata)
        other = dict(other)

        cubes = metadata.pop("cubes", []) + other.pop("cubes", [])
        if cubes:
            metadata["cubes"] = cubes

        dims = metadata.pop("dimensions", []) + other.pop("dimensions", [])
        if dims:
            metadata["dimensions"] = dims

        joins = metadata.pop("joins", []) + other.pop("joins",[])
        if joins:
            metadata["joins"] = joins

        mappings = metadata.pop("mappings", {})
        mappings.update(other.pop("mappings", {}))
        if mappings:
            metadata["mappings"] = mappings

        metadata.update(other)

        return metadata

    def default_metadata(self, metadata=None):
        """Returns metadata that are prepended to the provided model metadata.
        `metadata` is user-provided metadata and might be used to decide what
        kind of default metadata are returned.

        The metadata are merged as follows:

        * cube lists are concatenated (no duplicity checking)
        * dimension lists are concatenated (no duplicity checking)
        * joins are concatenated
        * default mappings are updated with the model's mappings

        Default implementation returns empty metadata.
        """

        return {}

    def requires_store(self):
        """Return `True` if the provider requires a store. Subclasses might
        override this method. Default implementation returns `False`"""
        return False

    def set_store(self, store, store_name):
        """Set's the provider's `store` and `store_name`. The store can be used
        to retrieve model's metadata. The store name is a handle that can be
        passed to the Cube objects for workspace to know where to find cube's
        data."""

        self.store = store
        self.store_name = store_name
        self.initialize_from_store()

    def initialize_from_store(self):
        """Sets provider's store and store name. This method is called after
        the provider's `store` and `store_name` were set. Override this method
        if you would like to perform post-initialization from the store."""
        pass

    def cube_options(self, cube_name):
        """Returns an options dictionary for cube `name`. The options
        dictoinary is merged model `options` metadata with cube's `options`
        metadata if exists. Cube overrides model's global (default)
        options."""

        options = dict(self.options)
        if cube_name in self.cubes_metadata:
            cube = self.cubes_metadata[cube_name]
            # TODO: decide which one to use
            options.update(cube.get("options", {}))
            options.update(cube.get("browser_options", {}))

        return options

    def dimension_metadata(self, name, locale=None):
        """Returns a metadata dictionary for dimension `name` and optional
        `locale`.

        Subclasses should override this method and call the super if they
        would like to merge metadata provided in a model file."""

        try:
            return self.dimensions_metadata[name]
        except KeyError:
            raise NoSuchDimensionError("No such dimension '%s'" % name, name)

    def cube_metadata(self, name, locale=None):
        """Returns a cube metadata by combining model's global metadata and
        cube's metadata. Merged metadata dictionaries: `browser_options`,
        `mappings`, `joins`.

        Subclasses should override this method and call the super if they
        would like to merge metadata provided in a model file.
        """

        if name in self.cubes_metadata:
            metadata = dict(self.cubes_metadata[name])
        else:
            raise NoSuchCubeError("No such cube '%s'" % name, name)

        # merge datastore from model if datastore not present
        if not metadata.get("datastore"):
            metadata['datastore'] = self.metadata.get("datastore",
                                                      self.store_name)

        # merge browser_options
        browser_options = self.metadata.get('browser_options', {})
        if metadata.get('browser_options'):
            browser_options.update(metadata.get('browser_options'))
        metadata['browser_options'] = browser_options

        # Merge model and cube mappings
        #
        model_mappings = self.metadata.get("mappings")
        cube_mappings = metadata.pop("mappings", {})

        if model_mappings:
            mappings = copy.deepcopy(model_mappings)
            mappings.update(cube_mappings)
        else:
            mappings = cube_mappings

        metadata["mappings"] = mappings

        # Merge model and cube joins
        #
        model_joins = self.metadata.get("joins", [])
        cube_joins = metadata.pop("joins", [])

        # model joins, if present, should be merged with cube's overrides.
        # joins are matched by the "name" key.
        if cube_joins and model_joins:
            model_join_map = {}
            for join in model_joins:
                try:
                    jname = join['name']
                except KeyError:
                    raise ModelError("Missing required 'name' key in "
                                     "model-level joins.")

                if jname in model_join_map:
                    raise ModelError("Duplicate model-level join 'name': %s" %
                                     jname)

                model_join_map[jname] = copy.deepcopy(join)

            # Merge cube's joins with model joins by their names.
            merged_joins = []

            for join in cube_joins:
                name = join.get('name')
                if name and model_join_map.has_key(name):
                    model_join = dict(model_join_map[name])
                else:
                    model_join = {}

                model_join.update(join)
                merged_joins.append(model_join)
        else:
            merged_joins = cube_joins

        # Validate joins:
        for join in merged_joins:
            if "master" not in join:
                raise ModelError("No master in join for cube '%s' "
                                 "(join name: %s)" % (name, join.get("name")))
            if "detail" not in join:
                raise ModelError("No detail in join for cube '%s' "
                                 "(join name: %s)" % (name, join.get("name")))

        metadata["joins"] = merged_joins

        return metadata

    def public_dimensions(self):
        """Returns a list of public dimension names. Default implementation
        returs all dimensions defined in the model metadata. If
        ``public_dimensions`` model property is set, then this list is used.

        Subclasses might override this method for alternative behavior. For
        example, if the backend uses dimension metadata from the model, but
        does not publish any dimension it can return an empty list."""
        # Get list of exported dimensions
        # By default all explicitly mentioned dimensions are exported.
        #
        try:
            return self.metadata["public_dimensions"]
        except KeyError:
            dimensions = self.metadata.get("dimensions", [])
            names = [dim["name"] for dim in dimensions]
            return names

    def list_cubes(self):
        """Get a list of metadata for cubes in the workspace. Result is a list
        of dictionaries with keys: `name`, `label`, `category`, `info`.

        The list is fetched from the model providers on the call of this
        method.

        Subclassees should implement this method.
        """
        raise NotImplementedError("Subclasses should implement list_cubes()")

    def cube(self, name, locale=None):
        """Returns a cube with `name` provided by the receiver. If receiver
        does not have the cube `NoSuchCube` exception is raised.

        Note: The returned cube will not have the dimensions assigned.
        It is up to the caller's responsibility to assign appropriate
        dimensions based on the cube's `dimension_links`.

        Subclasses of `ModelProvider` might override this method if they would
        like to create the `Cube` object directly.
        """

        metadata = self.cube_metadata(name, locale)
        return create_cube(metadata)

    def dimension(self, name, templates=[], locale=None):
        """Returns a dimension with `name` provided by the receiver.
        `dimensions` is a dictionary of dimension objects where the receiver
        can look for templates. If the dimension requires a template and the
        template is missing, the subclasses should raise
        `TemplateRequired(template)` error with a template name as an
        argument.

        If the receiver does not provide the dimension `NoSuchDimension`
        exception is raised.
        """
        metadata = self.dimension_metadata(name, locale)
        return create_dimension(metadata, templates)


class StaticModelProvider(ModelProvider):

    __extension_aliases__ = ["default"]

    def __init__(self, *args, **kwargs):
        super(StaticModelProvider, self).__init__(*args, **kwargs)
        # Initialization code goes here...

    def list_cubes(self):
        """Returns a list of cubes from the metadata."""
        cubes = []

        for cube in self.metadata.get("cubes", []):
            info = {
                    "name": cube["name"],
                    "label": cube.get("label", cube["name"]),
                    "category": (cube.get("category") or cube.get("info", {}).get("category")),
                    "info": cube.get("info", {})
                }
            cubes.append(info)

        return cubes


def create_model(source):
    raise NotImplementedError("create_model() is depreciated, use Workspace.add_model()")


def model_from_path(path):
    """Load logical model from a file or a directory specified by `path`.
    Returs instance of `Model`. """
    raise NotImplementedError("model_from_path is depreciated. use Workspace.add_model()")

########NEW FILE########
__FILENAME__ = app
# -*- coding: utf-8 -*-

import os
from .base import create_server
from .common import str_to_bool

# Set the configuration file
try:
    CONFIG_PATH = os.environ["SLICER_CONFIG"]
except KeyError:
    CONFIG_PATH = os.path.join(os.getcwd(), "slicer.ini")

application = create_server(CONFIG_PATH)

debug = os.environ.get("SLICER_DEBUG")
if debug and str_to_bool(debug):
    application.debug = True

########NEW FILE########
__FILENAME__ = auth
# -*- coding: utf-8 -*-
from ..extensions import Extensible
from ..errors import *
from flask import Response, redirect
import re

__all__ = (
    "Authenticator",
    "NotAuthenticated"
)

# IMPORTANT: This is provisional code. Might be changed or removed.
#

class NotAuthenticated(Exception):
    pass


class Authenticator(Extensible):
    def authenticate(self, request):
        raise NotImplementedError

    def info_dict(self, request):
        return { 'username' : self.authenticate(request) }

    def logout(self, request, identity):
        return "logged out"


class AbstractBasicAuthenticator(Authenticator):
    def __init__(self, realm=None):
        self.realm = realm or "Default"
        self.pattern = re.compile(r"^(http(?:s?)://)([^/]+.*)$", re.IGNORECASE)

    def logout(self, request, identity):
        headers = {"WWW-Authenticate": 'Basic realm="%s"' % self.realm}
        url_root = request.args.get('url', request.url_root)
        m = self.pattern.search(url_root)
        if m:
            url_root = m.group(1) + "__logout__@" + m.group(2)
            return redirect(url_root, code=302)
        else:
            return Response("logged out", status=401, headers=headers)

class AdminAdminAuthenticator(AbstractBasicAuthenticator):
    """Simple HTTP Basic authenticator for testing purposes. User name and
    password have to be the same. User name is passed as the authenticated
    identity."""
    def __init__(self, realm=None, **options):
        super(AdminAdminAuthenticator, self).__init__(realm=realm)

    def authenticate(self, request):
        auth = request.authorization
        if auth and auth.username == auth.password:
            return auth.username
        else:
            raise NotAuthenticated

        raise NotAuthenticated


class PassParameterAuthenticator(Authenticator):
    """Permissive authenticator that passes an URL parameter (default
    ``api_key``) as idenity."""
    def __init__(self, parameter=None, **options):
        super(PassParameterAuthenticator, self).__init__(**options)
        self.parameter_name = parameter or "api_key"

    def authenticate(self, request):
        return request.args.get(self.parameter_name)


class HTTPBasicProxyAuthenticator(AbstractBasicAuthenticator):
    def __init__(self, realm=None, **options):
        super(HTTPBasicProxyAuthenticator, self).__init__(realm=realm)
        self.realm = realm or "Default"
        self.pattern = re.compile(r"^(http(?:s?)://)([^/]+.*)$", re.IGNORECASE)

    def authenticate(self, request):
        """Permissive authenticator using HTTP Basic authentication that
        assumes the server to be behind a proxy, and that the proxy authenticated the user. 
        Does not check for a password, just passes the `username` as identity"""
        auth = request.authorization

        if auth:
            return auth.username

        raise NotAuthenticated(realm=self.realm)


########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
from .blueprint import slicer
from flask import Flask
import ConfigParser
import shlex

from .utils import *

__all__ = (
    "create_server",
    "run_server"
)

# Server Instantiation and Running
# ================================

def _read_config(config):
    if not config:
        return ConfigParser.SafeConfigParser()
    elif isinstance(config, basestring):
        try:
            path = config
            config = ConfigParser.SafeConfigParser()
            config.read(path)
        except Exception as e:
            raise Exception("Unable to load configuration: %s" % e)
    return config

def create_server(config=None):
    """Returns a Flask server application. `config` is a path to a
    ``slicer.ini`` file with Cubes workspace and server configuration."""

    config = read_server_config(config)

    # Load extensions

    if config.has_option("server", "modules"):
        modules = shlex.split(config.get("server", "modules"))
        for module in modules:
            e = __import__(module)

    app = Flask("slicer")
    app.register_blueprint(slicer, config=config)

    return app


def run_server(config, debug=False):
    """Run OLAP server with configuration specified in `config`"""

    config = read_server_config(config)
    app = create_server(config)

    if config.has_option("server", "host"):
        host = config.get("server", "host")
    else:
        host = "localhost"

    if config.has_option("server", "port"):
        port = config.getint("server", "port")
    else:
        port = 5000

    if config.has_option("server", "reload"):
        use_reloader = config.getboolean("server", "reload")
    else:
        use_reloader = False

    if config.has_option('server', 'processes'):
        processes = config.getint('server', 'processes')
    else:
        processes = 1

    app.run(host, port, debug=debug, processes=processes,
            use_reloader=use_reloader)


########NEW FILE########
__FILENAME__ = blueprint
# -*- coding: utf-8 -*-
from flask import Blueprint, Response, request, g, current_app
from flask import render_template
import json
from functools import wraps

from ..workspace import Workspace, SLICER_INFO_KEYS
from ..browser import Cell, SPLIT_DIMENSION_NAME, cut_from_dict
from ..errors import *
from ..extensions import extensions
from .logging import configured_request_log_handlers, RequestLogger
from .logging import AsyncRequestLogger
from .utils import *
from .errors import *
from .decorators import *
from .local import *
from .auth import NotAuthenticated

from collections import OrderedDict

from cubes import __version__

# TODO: missing features from the original Werkzeug Slicer:
# * /locales and localization
# * default cube: /aggregate
# * caching
# * root / index
# * response.headers.add("Access-Control-Allow-Origin", "*")

try:
    import cubes_search
except ImportError:
    cubes_search = None

__all__ = (
    "slicer",
    "API_VERSION"
)

API_VERSION = 2

# Cross-origin resource sharing – 20 days cache
CORS_MAX_AGE = 1728000

slicer = Blueprint("slicer", __name__, template_folder="templates")

# Before
# ------

def _store_option(config, option, default, type_=None, allowed=None,
                      section="server"):
    """Copies the `option` into the application config dictionary. `default`
    is a default value, if there is no such option in `config`. `type_` can be
    `bool`, `int` or `string` (default). If `allowed` is specified, then the
    option should be only from the list of allowed options, otherwise a
    `ConfigurationError` exception is raised.
    """

    if config.has_option(section, option):
        if type_ == "bool":
            value = config.getboolean(section, option)
        elif type_ == "int":
            value = config.getint(section, option)
        else:
            value = config.get(section, option)
    else:
        value = default

    if allowed and value not in allowed:
        raise ConfigurationError("Invalued value '%s' for option '%s'"
                                 % (value, option))

    setattr(current_app.slicer, option, value)

@slicer.record_once
def initialize_slicer(state):
    """Create the workspace and configure the application context from the
    ``slicer.ini`` configuration."""

    with state.app.app_context():
        config = state.options["config"]
        config = read_server_config(config)

        # Create workspace and other app objects
        # We avoid pollution of the current_app context, as we are a Blueprint
        params = CustomDict()
        current_app.slicer = params
        current_app.slicer.config = config
        current_app.cubes_workspace = Workspace(config)

        # Configure the application
        _store_option(config, "prettyprint", False, "bool")
        _store_option(config, "json_record_limit", 1000, "int")
        _store_option(config, "hide_private_cuts", False, "bool")
        _store_option(config, "allow_cors_origin", None, "str")

        _store_option(config, "authentication", "none")

        method = current_app.slicer.authentication
        if method is None or method == "none":
            current_app.slicer.authenticator = None
        else:
            if config.has_section("authentication"):
                options = dict(config.items("authentication"))
            else:
                options = {}

            current_app.slicer.authenticator = extensions.authenticator(method,
                                                                        **options)
        logger.debug("Server authentication method: %s" % (method or "none"))

        if not current_app.slicer.authenticator and workspace.authorizer:
            logger.warn("No authenticator specified, but workspace seems to "
                        "be using an authorizer")

        # Collect query loggers
        handlers = configured_request_log_handlers(config)

        if config.has_option('server', 'asynchronous_logging'):
            async_logging = config.getboolean("server", "asynchronous_logging")
        else:
            async_logging = False

        if async_logging:
            current_app.slicer.request_logger = AsyncRequestLogger(handlers)
        else:
            current_app.slicer.request_logger = RequestLogger(handlers)

# Before and After
# ================

@slicer.before_request
def process_common_parameters():
    # TODO: setup language

    # Copy from the application context
    g.json_record_limit = current_app.slicer.json_record_limit

    if "prettyprint" in request.args:
        g.prettyprint = str_to_bool(request.args.get("prettyprint"))
    else:
        g.prettyprint = current_app.slicer.prettyprint


@slicer.before_request
def prepare_authorization():
    if current_app.slicer.authenticator:
        try:
            identity = current_app.slicer.authenticator.authenticate(request)
        except NotAuthenticated as e:
            raise NotAuthenticatedError
    else:
        identity = None

    # Authorization
    # -------------
    g.auth_identity = identity


# Error Handler
# =============

@slicer.errorhandler(UserError)
def user_error_handler(e):
    error_type = e.__class__.error_type
    error = OrderedDict()
    error["error"] = error_type
    error["message"] = str(e)

    if hasattr(e, "hint") and e.hint:
        error["hint"] = e.hint

    if hasattr(e, "to_dict"):
        error.update(e.to_dict())

    code = server_error_codes.get(error_type, 400)

    return jsonify(error), code

@slicer.errorhandler(404)
def page_not_found(e):
    error = {
        "error": "not_found",
        "message": "The requested URL was not found on the server.",
        "hint": "If you entered the URL manually please check your "
                "spelling and try again."
    }
    return jsonify(error), 404

# Endpoints
# =========

@slicer.route("/")
def show_index():
    info = get_info()
    has_about = any(key in info for key in SLICER_INFO_KEYS)

    return render_template("index.html",
                           has_about=has_about,
                           **info)


@slicer.route("/version")
def show_version():
    info = {
        "version": __version__,
        # Backward compatibility key
        "server_version": __version__,
        "api_version": API_VERSION
    }
    return jsonify(info)


def get_info():
    if workspace.info:
        info = OrderedDict(workspace.info)
    else:
        info = OrderedDict()

    info["json_record_limit"] = current_app.slicer.json_record_limit
    info["cubes_version"] = __version__
    info["timezone"] = workspace.calendar.timezone_name
    info["first_weekday"] = workspace.calendar.first_weekday
    info["api_version"] = API_VERSION

    # authentication
    authinfo = {}

    authinfo["type"] = (current_app.slicer.authentication or "none")

    if g.auth_identity:
        authinfo['identity'] = g.auth_identity

    if current_app.slicer.authenticator:
        ainfo = current_app.slicer.authenticator.info_dict(request)
        authinfo.update(ainfo)

    info['authentication'] = authinfo

    return info

@slicer.route("/info")
def show_info():
    return jsonify(get_info())


@slicer.route("/cubes")
def list_cubes():
    cube_list = workspace.list_cubes(g.auth_identity)
    # TODO: cache per-identity
    return jsonify(cube_list)


@slicer.route("/cube/<cube_name>/model")
@requires_cube
def cube_model(cube_name):
    if workspace.authorizer:
        hier_limits = workspace.authorizer.hierarchy_limits(g.auth_identity,
                                                            cube_name)
    else:
        hier_limits = None

    response = g.cube.to_dict(expand_dimensions=True,
                              with_mappings=False,
                              full_attribute_names=True,
                              create_label=True,
                              hierarchy_limits=hier_limits)

    response["features"] = workspace.cube_features(g.cube)
    return jsonify(response)


@slicer.route("/cube/<cube_name>/aggregate")
@requires_browser
@log_request("aggregate", "aggregates")
def aggregate(cube_name):
    cube = g.cube

    output_format = validated_parameter(request.args, "format",
                                        values=["json", "csv"],
                                        default="json")

    header_type = validated_parameter(request.args, "header",
                                      values=["names", "labels", "none"],
                                      default="labels")

    fields_str = request.args.get("fields")
    if fields_str:
        fields = fields_str.lower().split(',')
    else:
        fields = None

    # Aggregates
    # ----------

    aggregates = []
    for agg in request.args.getlist("aggregates") or []:
        aggregates += agg.split("|")

    drilldown = []

    ddlist = request.args.getlist("drilldown")
    if ddlist:
        for ddstring in ddlist:
            drilldown += ddstring.split("|")

    prepare_cell("split", "split")

    result = g.browser.aggregate(g.cell,
                                 aggregates=aggregates,
                                 drilldown=drilldown,
                                 split=g.split,
                                 page=g.page,
                                 page_size=g.page_size,
                                 order=g.order)

    # Hide cuts that were generated internally (default: don't)
    if current_app.slicer.hide_private_cuts:
        result.cell = result.cell.public_cell()

    if output_format == "json":
        return jsonify(result)
    elif output_format != "csv":
        raise RequestError("unknown response format '%s'" % output_format)

    # csv
    if header_type == "names":
        header = result.labels
    elif header_type == "labels":
        header = []
        for l in result.labels:
            # TODO: add a little bit of polish to this
            if l == SPLIT_DIMENSION_NAME:
                header.append('Matches Filters')
            else:
                header += [ attr.label or attr.name for attr in cube.get_attributes([l], aggregated=True) ]
    else:
        header = None

    fields = result.labels
    generator = CSVGenerator(result,
                             fields,
                             include_header=bool(header),
                             header=header)

    headers = {"Content-Disposition": 'attachment; filename="aggregate.csv"'}
    return Response(generator.csvrows(),
                    mimetype='text/csv',
                    headers=headers)


@slicer.route("/cube/<cube_name>/facts")
@requires_browser
@log_request("facts", "fields")
def cube_facts(cube_name):
    # Request parameters
    fields_str = request.args.get("fields")
    if fields_str:
        fields = fields_str.split(',')
    else:
        fields = None

    # fields contain attribute names
    if fields:
        attributes = g.cube.get_attributes(fields)
    else:
        attributes = g.cube.all_attributes

    # Construct the field list
    fields = [attr.ref() for attr in attributes]

    # Get the result
    facts = g.browser.facts(g.cell,
                             fields=fields,
                             order=g.order,
                             page=g.page,
                             page_size=g.page_size)

    # Add cube key to the fields (it is returned in the result)
    fields.insert(0, g.cube.key or "id")

    # Construct the header
    labels = [attr.label or attr.name for attr in attributes]
    labels.insert(0, g.cube.key or "id")

    return formated_response(facts, fields, labels)

@slicer.route("/cube/<cube_name>/fact/<fact_id>")
@requires_browser
def cube_fact(cube_name, fact_id):
    fact = g.browser.fact(fact_id)

    if fact:
        return jsonify(fact)
    else:
        raise NotFoundError(fact_id, "fact",
                            message="No fact with id '%s'" % fact_id)


@slicer.route("/cube/<cube_name>/members/<dimension_name>")
@requires_browser
@log_request("members")
def cube_members(cube_name, dimension_name):
    # TODO: accept level name
    depth = request.args.get("depth")
    level = request.args.get("level")

    if depth and level:
        raise RequestError("Both depth and level provided, use only one "
                           "(preferably level)")

    if depth:
        try:
            depth = int(depth)
        except ValueError:
            raise RequestError("depth should be an integer")

    try:
        dimension = g.cube.dimension(dimension_name)
    except KeyError:
        raise NotFoundError(dimension_name, "dimension",
                            message="Dimension '%s' was not found" % dimension_name)

    hier_name = request.args.get("hierarchy")
    hierarchy = dimension.hierarchy(hier_name)

    if not depth and not level:
        depth = len(hierarchy)
    elif level:
        depth = hierarchy.level_index(level) + 1

    values = g.browser.members(g.cell,
                               dimension,
                               depth=depth,
                               hierarchy=hierarchy,
                               page=g.page,
                               page_size=g.page_size)

    result = {
        "dimension": dimension.name,
        "hierarchy": hierarchy.name,
        "depth": len(hierarchy) if depth is None else depth,
        "data": values
    }

    # Collect fields and labels
    attributes = []
    for level in hierarchy.levels_for_depth(depth):
        attributes += level.attributes

    fields = [attr.ref() for attr in attributes]
    labels = [attr.label or attr.name for attr in attributes]

    return formated_response(result, fields, labels, iterable=values)


@slicer.route("/cube/<cube_name>/cell")
@requires_browser
def cube_cell(cube_name):
    details = g.browser.cell_details(g.cell)

    if not g.cell:
        g.cell = Cell(g.cube)

    cell_dict = g.cell.to_dict()
    for cut, detail in zip(cell_dict["cuts"], details):
        cut["details"] = detail

    return jsonify(cell_dict)


@slicer.route("/cube/<cube_name>/report", methods=["GET", "POST"])
@requires_browser
def cube_report(cube_name):
    report_request = json.loads(request.data)

    try:
        queries = report_request["queries"]
    except KeyError:
        raise RequestError("Report request does not contain 'queries' key")

    cell_cuts = report_request.get("cell")

    if cell_cuts:
        # Override URL cut with the one in report
        cuts = [cut_from_dict(cut) for cut in cell_cuts]
        cell = Cell(g.cube, cuts)
        logger.info("using cell from report specification (URL parameters "
                    "are ignored)")

        if workspace.authorizer:
            cell = workspace.authorizer.restricted_cell(g.auth_identity,
                                                        cube=g.cube,
                                                        cell=cell)
    else:
        if not g.cell:
            cell = Cell(g.cube)
        else:
            cell = g.cell

    result = g.browser.report(cell, queries)

    return jsonify(result)


@slicer.route("/cube/<cube_name>/search")
def cube_search(cube_name):
    # TODO: this is ported from old Werkzeug slicer, requires revision

    config = current_app.config
    if config.has_section("search"):
        options = dict(config.items("search"))
        engine_name = options.pop("engine")
    else:
        raise ConfigurationError("Search engine is not configured.")

    logger.debug("using search engine: %s" % engine_name)

    search_engine = cubes_search.create_searcher(engine_name,
                                                 browser=g.browser,
                                                 locales=g.locales,
                                                 **options)
    dimension = request.args.get("dimension")
    if not dimension:
        raise RequestError("No search dimension provided")

    query = request.args.get("query")

    if not query:
        raise RequestError("No search query provided")

    locale = g.locale or g.locales[0]

    logger.debug("searching for '%s' in %s, locale %s"
                 % (query, dimension, locale))

    search_result = search_engine.search(query, dimension, locale=locale)

    result = {
        "matches": search_result.dimension_matches(dimension),
        "dimension": dimension,
        "total_found": search_result.total_found,
        "locale": locale
    }

    if search_result.error:
        result["error"] = search_result.error

    if search_result.warning:
        result["warning"] = search_result.warning

    return jsonify(result)


@slicer.route("/logout")
def logout():
    if current_app.slicer.authenticator:
        return current_app.slicer.authenticator.logout(request, g.auth_identity)
    else:
        return "logged out"

@slicer.after_request
def add_cors_headers(response):
    """Add Cross-origin resource sharing headers."""
    origin = current_app.slicer.allow_cors_origin
    if origin and len(origin):
        if request.method == 'OPTIONS':
            response.headers['Access-Control-Allow-Headers'] = 'X-Requested-With'
            # OPTIONS preflight requests need to receive origin back instead of wildcard
        if origin == '*':
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', origin)
        else:
            response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Max-Age'] = CORS_MAX_AGE
    return response

########NEW FILE########
__FILENAME__ = caching
# -*- coding: utf-8 -*-
import json
import logging
from functools import update_wrapper, wraps
from datetime import datetime, timedelta
from exceptions import BaseException
import cPickle as pickle
import types

from werkzeug.routing import Rule
from werkzeug.wrappers import Response


def _make_key_str(name, *args, **kwargs):
    key_str = name

    if args:
        key_str += '::' + '::'.join([str(a) for a in args])
    if kwargs:
        key_str += '::' + '::'.join(['%s=%s' % (str(k), str(v)) for k, v in sorted(kwargs.items(), key=lambda x: x[0])])

    return key_str


_NOOP = lambda x: x


def query_ttl_strategy(data):
    import chat2query
    import measures

    if 'q' in data:
        query = chat2query.parse(data['q'])
        config = measures.get_measure_manifest().get(query.measure, {})
        ttl = config.get('ttl', None)
        if ttl:
            logging.getLogger().debug('Using configured ttl: %s', ttl)
        return ttl

    return None


def _default_strategy(data):
    return None


def response_dumps(response):
    return {
        'data': response.data,
        'mimetype': response.content_type
    }


def response_loads(data):
    return Response(data['data'], mimetype=data['mimetype'])



def cacheable(fn):
    @wraps(fn)
    def _cache(self, *args, **kwargs):

        if not hasattr(self, 'cache'):
            logging.getLogger().warn('Object is not configured with cache for @cacheable function: %s', self)
            return fn(self, *args, **kwargs)

        additional_args = getattr(self, 'args', {})

        cache_impl = self.cache

        name = '%s.%s' % (self.__class__.__name__, fn.__name__)
        key = _make_key_str(name, *args, **dict(additional_args.items() + kwargs.items()))

        try:
            v = cache_impl.get(key)

            if not v:
                self.logger.debug('CACHE MISS')
                v = fn(self, *args, **kwargs)
                cache_impl.set(key, v)
            else:
                self.logger.debug('CACHE HIT')
            return v
        except Exception as e:
            self.logger.warn('ERROR, skipping cache')
            self.logger.exception(e)
            v = fn(self, *args, **kwargs)
            try:
                cache_impl.set(key, v)
            finally:
                return v

    return update_wrapper(_cache, fn)



class Cache(object):
    def __setitem__(self, key, value):
        return self.set(key, value)

    def __getitem__(self, key):
        return self.get(key)

    def __delitem__(self, key):
        return self.rem(key)


def trap(fn):
    def _trap(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except BaseException as e:
            logging.getLogger().error('%s: %s, %s', fn.__name__, args, kwargs)
            logging.getLogger().exception(e)
    return _trap


class MongoCache(Cache):

    def __init__(self, name, ds, ttl=60, ttl_strategy=_default_strategy, dumps=_NOOP, loads=_NOOP, logger=logging.getLogger(), **kwargs):
        self.ttl = ttl
        self.store = ds.Caches[name]
        self.dumps = dumps
        self.loads = loads
        self.ttl_strategy = ttl_strategy
        self.logger=logger

    @trap
    def set(self, key, val, ttl=None):
        t = ttl or self.ttl_strategy(val) or self.ttl
        n = datetime.utcnow() + timedelta(seconds=t)

        p = {
            '_id': key,
            't': n,
            'd': self.dumps(val)
        }

        self.logger.debug('Set: %s, ttl: %s', key, t)
        item = self.store.save(p)

        return item is not None

    @trap
    def get(self, key):
        n = datetime.utcnow()
        item = self.store.find_one({'_id':key})

        if item:

            item['d'] = self.loads(item['d'])
            exp = item['t']
            if exp >= n:
                self.logger.debug('Hit: %s', key)
                return item['d']
            else:
                self.logger.debug('Stale: %s', key)
                self.store.remove({'_id': key})
                return None
        else:
            self.logger.debug('Miss: %s', key)
            return None

    def rem(self, key):
        n = datetime.utcnow()
        item = self.store.find_one({'_id':key})

        if item:
            self.logger.debug('Remove: %s', key)
            self.store.remove(item)
            return True
        else:
            self.logger.debug('Miss: %s', key)
            return False

########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-
"""Common objects for slicer server"""

import json
import os.path
import decimal
import datetime
import csv
import codecs
import cStringIO

from .errors import *

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'templates')

API_VERSION = "2"

def str_to_bool(string):
    """Convert a `string` to bool value. Returns ``True`` if `string` is
    one of ``["true", "yes", "1", "on"]``, returns ``False`` if `string` is
    one of  ``["false", "no", "0", "off"]``, otherwise returns ``None``."""

    if string is not None:
        if string.lower() in ["true", "yes", "1", "on"]:
            return True
        elif string.lower() in["false", "no", "0", "off"]:
            return False

    return None


def validated_parameter(args, name, values=None, default=None, case_sensitive=False):
    """Return validated parameter `param` that has to be from the list of
    `values` if provided."""

    param = args.get(name)
    if param:
        param = param.lower()
    else:
        param = default

    if not values:
        return param
    else:
        if values and param not in values:
            list_str = ", ".join(values)
            raise RequestError("Parameter '%s' should be one of: %s"
                            % (name, list_str) )
        return param


class SlicerJSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        """Creates a JSON encoder that will convert some data values and also allows
        iterables to be used in the object graph.

        :Attributes:
        * `iterator_limit` - limits number of objects to be fetched from iterator. Default: 1000.
        """

        super(SlicerJSONEncoder, self).__init__(*args, **kwargs)

        self.iterator_limit = 1000

    def default(self, o):
        if type(o) == decimal.Decimal:
            return float(o)
        if type(o) == datetime.date or type(o) == datetime.datetime:
            return o.isoformat()
        if hasattr(o, "to_dict") and callable(getattr(o, "to_dict")):
            return o.to_dict()
        else:
            array = None
            try:
                # If it is an iterator, then try to construct array and limit number of objects
                iterator = iter(o)
                count = self.iterator_limit
                array = []
                for i, obj in enumerate(iterator):
                    array.append(obj)
                    if i >= count:
                        break
            except TypeError as e:
                # not iterable
                pass

            if array is not None:
                return array
            else:
                return json.JSONEncoder.default(self, o)


class CSVGenerator(object):
    def __init__(self, records, fields, include_header=True,
                header=None, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.records = records

        self.include_header = include_header
        self.header = header

        self.fields = fields
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.encoder = codecs.getincrementalencoder(encoding)()

    def csvrows(self):
        if self.include_header:
            yield self._row_string(self.header or self.fields)

        for record in self.records:
            row = []
            for field in self.fields:
                value = record.get(field)
                if type(value) == unicode or type(value) == str:
                    row.append(value.encode("utf-8"))
                elif value is not None:
                    row.append(unicode(value))
                else:
                    row.append(None)

            yield self._row_string(row)

    def _row_string(self, row):
        self.writer.writerow(row)
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # empty queue
        self.queue.truncate(0)

        return data


class UnicodeCSVWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.

    From: <http://docs.python.org/lib/csv-examples.html>
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        new_row = []
        for value in row:
            if type(value) == unicode or type(value) == str:
                new_row.append(value.encode("utf-8"))
            elif value:
                new_row.append(unicode(value))
            else:
                new_row.append(None)

        self.writer.writerow(new_row)
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

########NEW FILE########
__FILENAME__ = decorators
# -*- coding: utf-8 -*-
from flask import Blueprint, Flask, Response, request, g, current_app
from functools import wraps

import ConfigParser
from ..workspace import Workspace
from ..auth import NotAuthorized
from ..browser import Cell, cuts_from_string, SPLIT_DIMENSION_NAME
from ..errors import *
from .utils import *
from .errors import *
from .local import *
from ..calendar import CalendarMemberConverter

from contextlib import contextmanager

# Utils
# -----

def prepare_cell(argname="cut", target="cell", restrict=False):
    """Sets `g.cell` with a `Cell` object from argument with name `argname`"""
    # Used by prepare_browser_request and in /aggregate for the split cell


    # TODO: experimental code, for now only for dims with time role
    converters = {
        "time": CalendarMemberConverter(workspace.calendar)
    }

    cuts = []
    for cut_string in request.args.getlist(argname):
        cuts += cuts_from_string(g.cube, cut_string,
                                 role_member_converters=converters)

    if cuts:
        cell = Cell(g.cube, cuts)
    else:
        cell = None

    if restrict:
        if workspace.authorizer:
            cell = workspace.authorizer.restricted_cell(g.auth_identity,
                                                        cube=g.cube,
                                                        cell=cell)
    setattr(g, target, cell)


def requires_cube(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "lang" in request.args:
            g.locale = request.args.get("lang")
        else:
            g.locale = None

        cube_name = request.view_args.get("cube_name")
        try:
            g.cube = authorized_cube(cube_name, locale=g.locale)
        except NoSuchCubeError:
            raise NotFoundError(cube_name, "cube",
                                "Unknown cube '%s'" % cube_name)

        return f(*args, **kwargs)

    return wrapper

def requires_browser(f):
    """Prepares three global variables: `g.cube`, `g.browser` and `g.cell`.
    Also athorizes the cube using `authorize()`."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        if "lang" in request.args:
            g.locale = request.args.get("lang")
        else:
            g.locale = None

        cube_name = request.view_args.get("cube_name")
        if cube_name:
            cube = authorized_cube(cube_name, g.locale)
        else:
            cube = None

        g.cube = cube
        g.browser = workspace.browser(g.cube)

        prepare_cell(restrict=True)

        if "page" in request.args:
            try:
                g.page = int(request.args.get("page"))
            except ValueError:
                raise RequestError("'page' should be a number")
        else:
            g.page = None

        if "pagesize" in request.args:
            try:
                g.page_size = int(request.args.get("pagesize"))
            except ValueError:
                raise RequestError("'pagesize' should be a number")
        else:
            g.page_size = None

        # Collect orderings:
        # order is specified as order=<field>[:<direction>]
        #
        g.order = []
        for orders in request.args.getlist("order"):
            for order in orders.split(","):
                split = order.split(":")
                if len(split) == 1:
                    g.order.append( (order, None) )
                else:
                    g.order.append( (split[0], split[1]) )

        return f(*args, **kwargs)

    return wrapper


# Get authorized cube
# ===================

def authorized_cube(cube_name, locale):
    """Returns a cube `cube_name`. Handle cube authorization if required."""

    try:
        cube = workspace.cube(cube_name, g.auth_identity, locale=locale)
    except NotAuthorized:
        ident = "'%s'" % g.auth_identity if g.auth_identity \
                        else "unspecified identity"
        raise NotAuthorizedError("Authorization of cube '%s' failed for "
                                 "%s" % (cube_name, ident))
    return cube


# Query Logging
# =============

def log_request(action, attrib_field="attributes"):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            rlogger = current_app.slicer.request_logger

            # TODO: move this to request wrapper (same code as in aggregate)
            ddlist = request.args.getlist("drilldown")
            drilldown = []
            if ddlist:
                for ddstring in ddlist:
                    drilldown += ddstring.split("|")

            other = {
                "split": request.args.get("split"),
                "drilldown": drilldown,
                "page": g.page,
                "page_size": g.page_size,
                "format": request.args.get("format"),
                "header": request.args.get("header"),
                "attributes": request.args.get(attrib_field)
            }

            with rlogger.log_time(action, g.browser, g.cell, g.auth_identity,
                                  **other):
                retval = f(*args, **kwargs)

            return retval

        return wrapper

    return decorator


########NEW FILE########
__FILENAME__ = errors
# -*- coding: utf-8 -*-

import json

server_error_codes = {
    "unknown": 400,
    "missing_object": 404
}

try:
    from werkzeug.exceptions import HTTPException
except:
    # No need to bind objects here to dependency-sink, as the user
    # will be notified when he tries to use Slicer or run_server about
    # the missing package
    HTTPException = object


class ServerError(HTTPException):
    code = 500
    error_type = "default"
    def __init__(self, message=None, exception=None, **details):
        super(ServerError, self).__init__()
        self.message = message
        self.exception = exception
        self.details = details
        self.help = None

    def get_body(self, environ):
        error = {
            "message": self.message,
            "type": self.__class__.error_type
        }

        if self.exception:
            error["reason"] = str(self.exception)

        if self.details:
            error.update(self.details)

        string = json.dumps({"error": error}, indent=4)
        return string

    def get_headers(self, environ):
        """Get a list of headers."""
        return [('Content-Type', 'application/json')]


class RequestError(ServerError):
    error_type = "request"
    code = 400


class NotAuthorizedError(ServerError):
    code = 403
    error_type = "not_authorized"


class NotAuthenticatedError(ServerError):
    code = 401
    error_type = "not_authenticated"

    def __init__(self, message=None, exception=None, realm=None, **details):
        super(NotAuthenticatedError, self).__init__(message,
                                                    exception,
                                                    **details)
        self.message = message
        self.exception = exception
        self.details = details
        self.help = None
        self.realm = realm or "Default"

    def get_headers(self, environ):
        """Get a list of headers."""
        headers = super(NotAuthenticatedError, self).get_headers(environ)
        headers.append(('WWW-Authenticate', 'Basic realm="%s"' % self.realm))
        return headers


class NotFoundError(ServerError):
    code = 404
    error_type = "not_found"
    def __init__(self, obj, objtype=None, message=None):
        super(NotFoundError, self).__init__(message)
        self.details = { "object": obj }

        if objtype:
            self.details["object_type"] = objtype

        if not message:
            self.message = "Object '%s' of type '%s' was not found" % (obj, objtype)
        else:
            self.message = message



########NEW FILE########
__FILENAME__ = local
# -*- coding: utf-8 -*-
from flask import current_app
from werkzeug.local import LocalProxy

# Application Context
# ===================
#
# Readability proxies

def _get_workspace():
    return current_app.cubes_workspace

def _get_logger():
    return current_app.cubes_workspace.logger

workspace = LocalProxy(_get_workspace)
logger = LocalProxy(_get_logger)


########NEW FILE########
__FILENAME__ = logging
# -*- coding: utf-8 -*-
from contextlib import contextmanager
from collections import namedtuple
from threading import Thread
from Queue import Queue

import datetime
import time
import csv
import io
import json

from ..extensions import extensions, Extensible
from ..logging import get_logger
from ..errors import *
from ..browser import Drilldown

__all__ = [
    "create_request_log_handler",
    "configured_request_log_handlers",

    "RequestLogger",
    "AsyncRequestLogger",
    "RequestLogHandler",
    "DefaultRequestLogHandler",
    "CSVFileRequestLogHandler",
    "QUERY_LOG_ITEMS"
]


REQUEST_LOG_ITEMS = [
    "timestamp",
    "method",
    "cube",
    "cell",
    "identity",
    "elapsed_time",
    "attributes",
    "split",
    "drilldown",
    "page",
    "page_size",
    "format",
    "headers"
]


def configured_request_log_handlers(config, prefix="query_log",
                                    default_logger=None):
    """Returns configured query loggers as defined in the `config`."""

    handlers = []

    for section in config.sections():
        if section.startswith(prefix):
            options = dict(config.items(section))
            type_ = options.pop("type")
            if type_ == "default":
                logger = default_logger or get_logger()
                handler = extensions.request_log_handler("default", logger)
            else:
                handler = extensions.request_log_handler(type_, **options)

            handlers.append(handler)

    return handlers


class RequestLogger(object):
    def __init__(self, handlers=None):
        if handlers:
            self.handlers = list(handlers)
        else:
            self.handlers = []

        self.logger = get_logger()

    @contextmanager
    def log_time(self, method, browser, cell, identity=None, **other):
        start = time.time()
        yield
        elapsed = time.time() - start
        self.log(method, browser, cell, identity, elapsed, **other)

    def log(self, method, browser, cell, identity=None, elapsed=None, **other):

        record = {
            "timestamp": datetime.datetime.now(),
            "method": method,
            "cube": browser.cube,
            "identity": identity,
            "elapsed_time": elapsed or 0,
            "cell": cell
        }
        record.update(other)

        record = self._stringify_record(record)

        for handler in self.handlers:
            try:
                handler.write_record(browser.cube, cell, record)
            except Exception as e:
                self.logger.error("Server log handler error (%s): %s"
                                  % (type(handler).__name__, str(e)))


    def _stringify_record(self, record):
        """Return a log rectord with object attributes converted to strings"""
        record = dict(record)

        record["cube"] = str(record["cube"])

        cell = record.get("cell")
        record["cell"] = str(cell) if cell is not None else None

        split = record.get("split")
        record["split"] = str(split) if split is not None else None

        return record


class AsyncRequestLogger(RequestLogger):
    def __init__(self, handlers=None):
        super(AsyncRequestLogger, self).__init__(handlers)
        self.queue = Queue()
        self.thread = Thread(target=self.log_consumer,
                              name="slicer_logging")
        self.thread.daemon = True
        self.thread.start()

    def log(self, *args, **kwargs):
        self.queue.put( (args, kwargs) )

    def log_consumer(self):
        while True:
            (args, kwargs) = self.queue.get()
            super(AsyncRequestLogger, self).log(*args, **kwargs)

class RequestLogHandler(Extensible):
    def write_record(self, record):
        pass


class DefaultRequestLogHandler(RequestLogHandler):
    def __init__(self, logger=None, **options):
        self.logger = logger

    def write_record(self, cube, cell, record, **options):
        if cell:
            cell_str = "'%s'" % str(cell)
        else:
            cell_str = "none"

        if record.get("identity"):
            identity_str = "'%s'" % str(record["identity"])
        else:
            identity_str = "none"

        self.logger.info("method:%s cube:%s cell:%s identity:%s time:%s"
                         % (record["method"], record["cube"], cell_str,
                            identity_str, record["elapsed_time"]))


class CSVFileRequestLogHandler(RequestLogHandler):
    def __init__(self, path=None, **options):
        self.path = path

    def write_record(self, cube, cell, record):
        out = []

        for key in REQUEST_LOG_ITEMS:
            item = record.get(key)
            if item is not None:
                item = unicode(item)
            out.append(item)

        with io.open(self.path, 'ab') as f:
            writer = csv.writer(f)
            writer.writerow(out)

class JSONRequestLogHandler(RequestLogHandler):
    def __init__(self, path=None, **options):
        """Creates a JSON logger which logs requests in a JSON lines. It
        includes two lists: `cell_dimensions` and `drilldown_dimensions`."""
        self.path = path

    def write_record(self, cube, cell, record):
        out = []

        drilldown = record.get("drilldown")

        if drilldown is not None:
            if cell:
                drilldown = Drilldown(drilldown, cell)
                record["drilldown"] = str(drilldown)
            else:
                drilldown = []
                record["drilldown"] = None

        record["timestamp"] = record["timestamp"].isoformat()
        # Collect dimension uses
        uses = []

        cuts = cell.cuts if cell else []

        for cut in cuts:
            dim = cube.dimension(cut.dimension)
            depth = cut.level_depth()
            if depth:
                level = dim.hierarchy(cut.hierarchy)[depth-1]
                level_name = str(level)
            else:
                level_name = None

            use = {
                "dimension": str(dim),
                "hierarchy": str(cut.hierarchy),
                "level": str(level_name),
                "value": str(cut)
            }
            uses.append(use)

        record["cell_dimensions"] = uses

        uses = []

        for item in drilldown or []:
            (dim, hier, levels) = item[0:3]
            if levels:
                level = str(levels[-1])
            else:
                level = None

            use = {
                "dimension": str(dim),
                "hierarchy": str(hier),
                "level": str(level),
                "value": None
            }
            uses.append(use)

        record["drilldown_dimensions"] = uses
        line = json.dumps(record)

        with io.open(self.path, 'ab') as f:
            json.dump(record, f)
            f.write("\n")


########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from flask import Request, Response, request, g
from datetime import datetime

import ConfigParser
import cStringIO
import datetime
import decimal
import codecs
import json
import csv

from .errors import *


def str_to_bool(string):
    """Convert a `string` to bool value. Returns ``True`` if `string` is
    one of ``["true", "yes", "1", "on"]``, returns ``False`` if `string` is
    one of  ``["false", "no", "0", "off"]``, otherwise returns ``None``."""

    if string is not None:
        if string.lower() in ["true", "yes", "1", "on"]:
            return True
        elif string.lower() in["false", "no", "0", "off"]:
            return False

    return None


def validated_parameter(args, name, values=None, default=None,
                        case_sensitive=False):
    """Return validated parameter `param` that has to be from the list of
    `values` if provided."""

    param = args.get(name)
    if param:
        param = param.lower()
    else:
        param = default

    if not values:
        return param
    else:
        if values and param not in values:
            list_str = ", ".join(values)
            raise RequestError("Parameter '%s' should be one of: %s"
                            % (name, list_str) )
        return param


class SlicerJSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        """Creates a JSON encoder that will convert some data values and also allows
        iterables to be used in the object graph.

        :Attributes:
        * `iterator_limit` - limits number of objects to be fetched from
          iterator. Default: 1000.
        """

        super(SlicerJSONEncoder, self).__init__(*args, **kwargs)

        self.iterator_limit = 1000

    def default(self, o):
        if type(o) == decimal.Decimal:
            return float(o)
        if type(o) == datetime.date or type(o) == datetime.datetime:
            return o.isoformat()
        if hasattr(o, "to_dict") and callable(getattr(o, "to_dict")):
            return o.to_dict()
        else:
            array = None
            try:
                # If it is an iterator, then try to construct array and limit number of objects
                iterator = iter(o)
                count = self.iterator_limit
                array = []
                for i, obj in enumerate(iterator):
                    array.append(obj)
                    if i >= count:
                        break
            except TypeError as e:
                # not iterable
                pass

            if array is not None:
                return array
            else:
                return json.JSONEncoder.default(self, o)


class CSVGenerator(object):
    def __init__(self, records, fields, include_header=True,
                header=None, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.records = records

        self.include_header = include_header
        self.header = header

        self.fields = fields
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.encoder = codecs.getincrementalencoder(encoding)()

    def csvrows(self):
        if self.include_header:
            yield self._row_string(self.header or self.fields)

        for record in self.records:
            row = []
            for field in self.fields:
                value = record.get(field)
                if type(value) == unicode or type(value) == str:
                    row.append(value.encode("utf-8"))
                elif value is not None:
                    row.append(unicode(value))
                else:
                    row.append(None)

            yield self._row_string(row)

    def _row_string(self, row):
        self.writer.writerow(row)
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # empty queue
        self.queue.truncate(0)

        return data


class JSONLinesGenerator(object):
    def __init__(self, iterable, separator='\n'):
        """Creates a generator that yields one JSON record per record from
        `iterable` separated by a newline character.."""
        self.iterable = iterable
        self.separator = separator

        self.encoder = SlicerJSONEncoder(indent=None)

    def __iter__(self):
        for obj in self.iterable:
            string = self.encoder.encode(obj)
            yield "%s%s" % (string, self.separator)

class UnicodeCSVWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.

    From: <http://docs.python.org/lib/csv-examples.html>
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        new_row = []
        for value in row:
            if type(value) == unicode or type(value) == str:
                new_row.append(value.encode("utf-8"))
            elif value:
                new_row.append(unicode(value))
            else:
                new_row.append(None)

        self.writer.writerow(new_row)
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

class CustomDict(dict):
    def __getattr__(self, attr):
        try:
            return super(CustomDict, self).__getitem__(attr)
        except KeyError:
            return super(CustomDict, self).__getattribute__(attr)

    def __setattr__(self, attr, value):
        self.__setitem__(attr,value)


# Utils
# =====

def jsonify(obj):
    """Returns a ``application/json`` `Response` object with `obj` converted
    to JSON."""

    if g.prettyprint:
        indent = 4
    else:
        indent = None

    encoder = SlicerJSONEncoder(indent=indent)
    encoder.iterator_limit = g.json_record_limit
    data = encoder.iterencode(obj)

    return Response(data, mimetype='application/json')


def formated_response(response, fields, labels, iterable=None):
    """Wraps request which returns response that can be formatted. The
    `data_attribute` is name of data attribute or key in the response that
    contains formateable data."""

    output_format = validated_parameter(request.args, "format",
                                        values=["json", "json_lines", "csv"],
                                        default="json")

    header_type = validated_parameter(request.args, "header",
                                      values=["names", "labels", "none"],
                                      default="labels")

    # Construct the header
    if header_type == "names":
        header = fields
    elif header_type == "labels":
        header = labels
    else:
        header = None


    # If no iterable is provided, we assume the response to be iterable
    iterable = iterable or response

    if output_format == "json":
        return jsonify(response)
    elif output_format == "json_lines":
        return Response(JSONLinesGenerator(iterable),
                        mimetype='application/x-json-lines')
    elif output_format == "csv":
        generator = CSVGenerator(iterable,
                                 fields,
                                 include_header=bool(header),
                                 header=header)

        headers = {"Content-Disposition": 'attachment; filename="facts.csv"'}

        return Response(generator.csvrows(),
                        mimetype='text/csv',
                        headers=headers)

def read_server_config(config):
    if not config:
        return ConfigParser.SafeConfigParser()
    elif isinstance(config, basestring):
        try:
            path = config
            config = ConfigParser.SafeConfigParser()
            config.read(path)
        except Exception as e:
            raise Exception("Unable to load configuration: %s" % e)
    return config


########NEW FILE########
__FILENAME__ = wildcards
import re
from functools import partial
import pytz
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta, SA
from utils import now
import logging


_NOOP = lambda x: '||%s||' % x

# FIXME: Warning: this kills all multiple argument occurences
# This function removes all duplicates of query parameters that can be
# obtained through args.getlist() (such as "?drilldown=x&drilldown=y")
def proc_wildcards(args):
    copy = args.copy()
    for k, v in args.iterlists():
        k = op(k)
        v = [ op(ve) for ve in v ]
        copy.setlist(k, v)
    return copy


def op(target):
    matches = re.finditer(r'\|\|([\w\d]+)\|\|', target)
    for mk in matches:
        token = mk.group(1)
        new_val = transform_token(token)
        target = target.replace(mk.group(), new_val)
        logging.debug("Replaced wildcard with %s", target)
    return target


def truncated_now(unit):
    d = now()
    d = d.replace(minute=0, second=0, microsecond=0)
    if unit == 'hour':
        pass
    elif unit == 'day':
        d = d.replace(hour=0)
    elif unit == 'week':
        d = d.replace(hour=0)
        # calc most recent week beginning
        # TODO make week beginning configurable
        #d = d - timedelta(days=( d.weekday() + 2 if d.weekday() < 5 else d.weekday() - 5 ))
        d = d + relativedelta(days=-6, weekday=SA)
    elif unit == 'month':
        d = d.replace(day=1, hour=0)
    elif unit == 'quarter':
        d = d.replace(day=1, hour=0)
        # TODO calc most recent beginning of a quarter
        d = d - relativedelta(months=((d.month - 1) % 3))
    elif unit == 'year':
        d = d.replace(month=1, day=1, hour=0)
    else:
        raise ValueError("Unrecognized unit: %s" % unit)
    return d

def subtract_units(d, amt, unit):
    tdargs = {}
    if unit == 'hour':
        tdargs['hours'] = amt
    elif unit == 'day':
        tdargs['days'] = amt
    elif unit == 'week':
        tdargs['days'] = amt * 7
    elif unit == 'month':
        tdargs['months'] = amt 
    elif unit == 'quarter':
        tdargs['months'] = amt * 3
    elif unit == 'year':
        tdargs['years'] = amt 
    return d - relativedelta(**tdargs)

_the_n_regex = re.compile(r'^last(\d+)(\w+)?$')

_UNITS = set(['hour', 'day', 'week', 'month', 'quarter', 'year'])

def lastN(token, amt=14, unit="day", format='%Y,%m,%d', tzinfo='America/NewYork'):
    m = _the_n_regex.search(token)
    if m:
        munit = m.group(2).lower() if m.group(2) is not None else ''
        if munit in _UNITS:
            unit = munit
        elif munit[:-1] in _UNITS:
            unit = munit[:-1]
        mamt = int(m.group(1))
        if mamt >= 0:
            amt = mamt
    # start with now() truncated to most recent instance of the unit
    n = truncated_now(unit)
    n = subtract_units(n, amt, unit)
    if unit == 'hour':
        format = format + ",%H"
    return n.strftime(format)

def transform_token(token):
    if _wildcards.has_key(token):
        return _wildcards[token](token)
    for func in _regex_wildcards:
        tx = func(token)
        if tx is not None:
            return tx
    return _NOOP

_wildcards = {
    'today': partial(lastN, amt=0, unit='day', format='%Y,%m,%d'),
    'yesterday': partial(lastN, amt=1, unit='day', format='%Y,%m,%d')
}

_regex_wildcards = ( lastN, )

if __name__ == '__main__':
    cuts = (
        'event_date:||last7||-||yesterday||',
        'event_date:||last7weeks||-||today||',
        'event_date:||last0month||-||yesterday||',
        'event_date:||last7month||-||yesterday||',
        'event_date:||last7quarters||-||yesterday||',
        'event_date:||last7years||-||yesterday||',
    )
    for cut in cuts:
        a = { 'cut': cut }
        a2 = proc_wildcards(a)
        print "%-40s  %s" % (cut, a2)

########NEW FILE########
__FILENAME__ = statutils
# -*- coding: utf-8 -*-

from collections import deque
from .errors import *
from functools import partial
from math import sqrt

__all__ = [
        "CALCULATED_AGGREGATIONS",
        "calculators_for_aggregates",
        "available_calculators",
        "aggregate_calculator_labels"
]

def calculators_for_aggregates(cube, aggregates, drilldown_levels=None,
                               split=None, backend_functions=None):
    """Returns a list of calculator function objects that implements
    aggregations by calculating on retrieved results, given a particular
    drilldown. Only post-aggregation calculators are returned.

    Might return an empty list if there is no post-aggregation witin
    aggregate functions.

    `backend_functions` is a list of backend-specific functions.
    """
    backend_functions = backend_functions or []

    # If we have an aggregation function, then we consider the aggregate
    # already processed
    functions = []

    names = [a.name for a in aggregates]
    for aggregate in aggregates:
        # Ignore function if the backend already handles it
        if not aggregate.function or aggregate.function in backend_functions:
            continue

        try:
            factory = CALCULATED_AGGREGATIONS[aggregate.function]
        except KeyError:
            raise ArgumentError("Unknown post-calculation function '%s' for "
                                "aggregate '%s'" % (aggregate.function,
                                                    aggregate.name))

        if aggregate.measure:
            source = cube.measure_aggregate(aggregate.measure)
        else:
            raise InternalError("No measure specified for aggregate '%s' in "
                                "cube '%s'" % (aggregate.name, cube.name))

        func = factory(aggregate, source.ref(), drilldown_levels, split)
        functions.append(func)

    return functions

def weighted_moving_average(values):
    n = len(values)
    denom = n * (n + 1) / 2
    total = 0.0
    idx = 1
    for val in values:
        total += float(idx) * float(val)
        idx += 1
    return round(total / denom, 4)


def simple_moving_average(values):
    # use all the values
    return round(reduce(lambda i, c: float(c) + i, values, 0.0) / len(values), 2)

def simple_moving_sum(values):
    return reduce(lambda i, c: i + c, values, 0)


def _variance(values):
    n, mean, std = len(values), 0, 0
    for a in values:
        mean = mean + a
    mean = mean / float(n)
    if n < 2:
        return mean, 0
    for a in values:
        std = std + (a - mean)**2
    return mean, (std / float(n-1))

def simple_relative_stdev(values):
    mean, var = _variance(values)
    return round(((sqrt(var)/mean) if mean > 0 else 0), 4)

def simple_variance(values):
    mean, var = _variance(values)
    return round(var, 2)

def simple_stdev(values):
    mean, var = _variance(values)
    return round(sqrt(var), 2)

def _window_function_factory(aggregate, source, drilldown_paths, split_cell, window_function, label):
    """Returns a moving average window function. `aggregate` is the target
    aggergate. `window_function` is concrete window function."""

    # If the level we're drilling to doesn't have aggregation_units configured,
    # we're not doing any calculations

    key_drilldown_paths = []
    window_size = None
    drilldown_paths = drilldown_paths or []

    if aggregate.window_size:
        window_size = aggregate.window_size
    else:
        # TODO: this is the old depreciated way, remove when not needed
        for path in drilldown_paths:
            relevant_level = path.levels[-1]
            these_num_units = None
            if relevant_level.info:
                these_num_units = relevant_level.info.get('aggregation_units', None)
            if these_num_units is None:
                key_drilldown_paths.append(path)
            else:
                window_size = these_num_units

    if window_size is None:
        window_size = 1

    elif not isinstance(window_size, int) or window_size < 1:
        raise ModelError("window size for aggregate '%s' sohuld be an integer "
                         "greater than or equeal 1" % aggregate.name)

    # Create a composite key for grouping:
    #   * split dimension, if used
    #   * key from drilldown path levels
    #
    # If no key_drilldown_paths, the key is always the empty tuple.

    window_key = []
    if split_cell:
        from .browser import SPLIT_DIMENSION_NAME
        window_key.append(SPLIT_DIMENSION_NAME)
    for dditem in key_drilldown_paths:
        window_key += [level.key.ref() for level in dditem.levels]

    # TODO: this is temporary solution: for post-aggregate calculations we
    # consider the measure reference to be aggregated measure reference.
    # TODO: this does not work for implicit post-aggregate calculations

    function = WindowFunction(window_function, window_key,
                              target_attribute=aggregate.name,
                              source_attribute=source,
                              window_size=window_size,
                              label=label)
    return function

def get_key(record, composite_key):
    """Extracts a tuple of values from the `record` by `composite_key`"""
    return tuple(record.get(key) for key in composite_key)

class WindowFunction(object):
    def __init__(self, function, window_key, target_attribute,
                 source_attribute, window_size, label):
        """Creates a window function."""

        if not function:
            raise ArgumentError("No window function provided")
        if window_size < 1:
            raise ArgumentError("Window size should be >= 1")
        if not source_attribute:
            raise ArgumentError("Source attribute not specified")
        if not target_attribute:
            raise ArgumentError("Target attribute not specified")

        self.function = function
        self.window_key = tuple(window_key) if window_key else tuple()
        self.source_attribute = source_attribute
        self.target_attribute = target_attribute
        self.window_size = window_size
        self.window_values = {}
        self.label = label

    def __call__(self, record):
        """Collects the source value. If the window for the `window_key` is
        filled, then apply the window function and store the value in the
        `record` to key `target_attribute`."""

        key = get_key(record, self.window_key)

        # Get the window values by key. Create new if necessary.
        try:
            values = self.window_values[key]
        except KeyError:
            values = deque()
            self.window_values[key] = values

        value = record.get(self.source_attribute)

        # TODO: What about those window functions that would want to have empty
        # values?
        if value is not None:
            values.append(value)

        # Keep the window within the window size:
        while len(values) > self.window_size:
            values.popleft()

        # Compute, if we have the values
        if len(values) > 0:
            record[self.target_attribute] = self.function(values)



# TODO: make CALCULATED_AGGREGATIONS a namespace (see extensions.py)
CALCULATED_AGGREGATIONS = {
    "wma": partial(_window_function_factory, window_function=weighted_moving_average, label='Weighted Moving Avg. of {measure}'),
    "sma": partial(_window_function_factory, window_function=simple_moving_average, label='Simple Moving Avg. of {measure}'),
    "sms": partial(_window_function_factory, window_function=simple_moving_sum, label='Simple Moving Sum of {measure}'),
    "smstd": partial(_window_function_factory, window_function=simple_stdev, label='Moving Std. Deviation of {measure}'),
    "smrsd": partial(_window_function_factory, window_function=simple_relative_stdev, label='Moving Relative St. Dev. of {measure}'),
    "smvar": partial(_window_function_factory, window_function=simple_variance, label='Moving Variance of {measure}')
}

def available_calculators():
    """Returns a list of available calculators."""
    return CALCULATED_AGGREGATIONS.keys()

def aggregate_calculator_labels():
    return dict([(k, v.keywords['label']) for k, v in CALCULATED_AGGREGATIONS.iteritems()])

########NEW FILE########
__FILENAME__ = stores
# -*- coding: utf-8 -*-

from .errors import *
from .extensions import Extensible

__all__ = (
            "Store"
        )


class Store(Extensible):
    """Abstract class to find other stores through the class hierarchy."""

    """Name of a model provider type associated with this store."""
    related_model_provider = None

########NEW FILE########
__FILENAME__ = sql
# -*- coding: utf-8 -*-

import sqlalchemy
import csv
import csv, codecs, cStringIO

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

def create_table_from_csv(connectable, file_name, table_name, fields, create_id = False, schema = None):
    """Create a table with name `table_name` from a CSV file `file_name` with columns corresponding
    to `fields`. The `fields` is a list of two string tuples: (name, type) where type might be:
    ``integer``, ``float`` or ``string``.
    
    If `create_id` is ``True`` then a column with name ``id`` is created and will contain generated
    sequential record id.
    
    This is just small utility function for sandbox, play-around and testing purposes. It is not
    recommended to be used for serious CSV-to-table loadings. For more advanced CSV loadings use another
    framework, such as Brewery (http://databrewery.org).
    """

    metadata = sqlalchemy.MetaData(bind = connectable)

    table = sqlalchemy.Table(table_name, metadata, autoload=False, schema=schema)
    if table.exists():
        table.drop(checkfirst=False)

    type_map = { "integer": sqlalchemy.Integer,
                 "float":sqlalchemy.Numeric,
                 "string":sqlalchemy.String(256),
                 "text":sqlalchemy.Text,
                 "date":sqlalchemy.Text,
                 "boolean": sqlalchemy.Integer }

    if create_id:
        col = sqlalchemy.schema.Column('id', sqlalchemy.Integer, primary_key=True)
        table.append_column(col)
    
    field_names = []
    for (field_name, field_type) in fields:
        col = sqlalchemy.schema.Column(field_name, type_map[field_type.lower()])
        table.append_column(col)
        field_names.append(field_name)

    table.create()

    reader = UnicodeReader(open(file_name))
    
    # Skip header
    reader.next()

    insert_command = table.insert()
    
    for row in reader:
        record = dict(zip(field_names, row))
        insert_command.execute(record)

########NEW FILE########
__FILENAME__ = workspace
# -*- coding: utf-8 -*-

import sys
from .metadata import read_model_metadata
from .auth import NotAuthorized
from .model import Model
from .common import read_json_file
from .logging import get_logger
from .errors import *
from .calendar import Calendar
from .extensions import extensions
import os.path
import ConfigParser
from collections import OrderedDict

__all__ = [
    "Workspace",

    # Depreciated
    "get_backend",
    "create_workspace",
    "create_workspace_from_config",
    "config_items_to_dict",
]


SLICER_INFO_KEYS = (
    "name",
    "label",
    "description",  # Workspace model description
    "copyright",    # Copyright for the data
    "license",      # Data license
    "maintainer",   # Name (and maybe contact) of data maintainer
    "contributors", # List of contributors
    "visualizers",  # List of dicts with url and label of server's visualizers
    "keywords",     # List of keywords describing server's cubes
    "related"       # List of dicts with related servers
)


def config_items_to_dict(items):
    return dict([ (k, interpret_config_value(v)) for (k, v) in items ])


def interpret_config_value(value):
    if value is None:
        return value
    if isinstance(value, basestring):
        if value.lower() in ('yes', 'true', 'on'):
            return True
        elif value.lower() in ('no', 'false', 'off'):
            return False
    return value


def _get_name(obj, object_type="Object"):
    if isinstance(obj, basestring):
        name = obj
    else:
        try:
            name = obj["name"]
        except KeyError:
            raise ModelError("%s has no name" % object_type)

    return name

class Namespace(object):
    def __init__(self):
        self.namespaces = {}
        self.providers = []
        self.objects = {}

    def namespace(self, path, create=False):
        """Returns a tuple (`namespace`, `remainder`) where `namespace` is
        the deepest namespace in the namespace hierarchy and `remainder` is
        the remaining part of the path that has no namespace (is an object
        name or contains part of external namespace).

        If path is empty or not provided then returns self.
        """

        if not path:
            return (self, [])

        if isinstance(path, basestring):
            path = path.split(".")

        namespace = self
        found = False
        for i, element in enumerate(path):
            remainder = path[i+1:]
            if element in namespace.namespaces:
                namespace = namespace.namespaces[element]
                found = True
            else:
                remainder = path[i:]
                break

        if not create:
            return (namespace, remainder)
        else:
            for element in remainder:
                namespace = namespace.create_namespace(element)

            return (namespace, [])

    def create_namespace(self, name):
        """Create a namespace `name` in the receiver."""
        namespace = Namespace()
        self.namespaces[name] = namespace
        return namespace

    def namespace_for_cube(self, cube):
        """Returns a tuple (`namespace`, `relative_cube`) where `namespace` is
        a namespace conaining `cube` and `relative_cube` is a name of the
        `cube` within the `namespace`. For example: if cube is
        ``slicer.nested.cube`` and there is namespace ``slicer`` then that
        namespace is returned and the `relative_cube` will be ``nested.cube``"""

        cube = str(cube)
        split = cube.split(".")
        if len(split) > 1:
            path = split[0:-1]
            cube = split[-1]
        else:
            path = []
            cube = cube

        (namespace, remainder) = self.namespace(path)

        if remainder:
            relative_cube = "%s.%s" % (".".join(remainder), cube)
        else:
            relative_cube = cube

        return (namespace, relative_cube)

    def list_cubes(self, recursive=False):
        """Retursn a list of cube info dictionaries with keys: `name`,
        `label`, `description`, `category` and `info`."""

        all_cubes = []
        cube_names = set()
        for provider in self.providers:
            cubes = provider.list_cubes()
            # Cehck for duplicity
            for cube in cubes:
                name = cube["name"]
                if name in cube_names:
                    raise ModelError("Duplicate cube '%s'" % name)
                cube_names.add(name)

            all_cubes += cubes

        if recursive:
            for name, ns in self.namespaces.items():
                cubes = ns.list_cubes(recursive=True)
                for cube in cubes:
                    cube["name"] = "%s.%s" % (name, cube["name"])
                all_cubes += cubes

        return all_cubes

    def cube(self, name, locale=None, recursive=False):
        """Return cube named `name`.

        If `recursive` is ``True`` then look for cube in child namespaces.
        """
        cube = None

        for provider in self.providers:
            # TODO: use locale
            try:
                cube = provider.cube(name)
            except NoSuchCubeError:
                pass
            else:
                cube.provider = provider
                return cube

        if recursive:
            for key, namespace in self.namespaces.items():
                try:
                    cube = namespace.cube(name, locale, recursive=True)
                except NoSuchCubeError:
                    # Just continue with sibling
                    pass
                else:
                    return cube

        raise NoSuchCubeError("Unknown cube '%s'" % str(name), name)

    def dimension(self, name, locale=None, templates=None):
        dim = None

        # TODO: cache dimensions
        for provider in self.providers:
            # TODO: use locale
            try:
                dim = provider.dimension(name, locale=locale,
                                         templates=templates)
            except NoSuchDimensionError:
                pass
            else:
                return dim

        raise NoSuchDimensionError("Unknown dimension '%s'" % str(name), name)

    def add_provider(self, provider):
        self.providers.append(provider)


class ModelObjectInfo(object):
    def __init__(self, name, scope, metadata, provider, model_metadata,
                  locale, translations):
        self.name = name
        self.scope = scope
        self.metadata = metadata
        self.provider = provider
        self.model_metadata = model_metadata
        self.locale = locale
        self.translations = translations
        self.master = None
        self.instances = {}

    def add_instance(self, instance, locale=None, identity=None):
        key = (locale, identity)
        self.instances[key] = instance

    def instance(self, locale=None, identity=None):
        key = (locale, identity)
        return self.instances[key]


class Workspace(object):
    def __init__(self, config=None, stores=None, load_base_model=True):
        """Creates a workspace. `config` should be a `ConfigParser` or a
        path to a config file. `stores` should be a dictionary of store
        configurations, a `ConfigParser` or a path to a ``stores.ini`` file.
        """
        if isinstance(config, basestring):
            cp = ConfigParser.SafeConfigParser()
            try:
                cp.read(config)
            except Exception as e:
                raise ConfigurationError("Unable to load config %s. "
                                "Reason: %s" % (config, str(e)))

            config = cp

        elif not config:
            # Read ./slicer.ini
            config = ConfigParser.ConfigParser()

        self.store_infos = {}
        self.stores = {}

        # Logging
        # =======
        #Log to file or console
        if config.has_option("workspace", "log"):
            self.logger = get_logger(path=config.get("workspace", "log"))
        else:
            self.logger = get_logger()

        #Change to log level if necessary
        if config.has_option("workspace", "log_level"):
            self.logger.setLevel(config.get("workspace", "log_level").upper())


        # Set the default models path
        if config.has_option("workspace", "root_directory"):
            self.root_dir = config.get("workspace", "root_directory")
        else:
            self.root_dir = ""

        if config.has_option("workspace", "models_directory"):
            self.models_dir = config.get("workspace", "models_directory")
        elif config.has_option("workspace", "models_path"):
            self.models_dir = config.get("workspace", "models_path")
        else:
            self.models_dir = ""

        if self.root_dir and not os.path.isabs(self.models_dir):
            self.models_dir = os.path.join(self.root_dir, self.models_dir)

        if self.models_dir:
            self.logger.debug("Models root: %s" % self.models_dir)
        else:
            self.logger.debug("Models root set to current directory")

        # Namespaces and Model Objects
        # ============================

        self.namespace = Namespace()

        # Cache of created global objects
        self._cubes = {}
        # Note: providers are responsible for their own caching

        if config.has_option("workspace", "lookup_method"):
            method = config.get("workspace", "lookup_method")
            if method not in ["exact", "recursive"]:
                raise ConfigurationError("Unknown namespace lookup method '%s'"
                                         % method)
            self.lookup_method = method
        else:
            # TODO: make this "global"
            self.lookup_method = "recursive"

        # Info
        # ====

        self.info = OrderedDict()

        if config.has_option("workspace", "info_file"):
            path = config.get("workspace", "info_file")

            if self.root_dir and not os.path.isabs(path):
                path = os.path.join(self.root_dir, path)

            info = read_json_file(path, "Slicer info")
            for key in SLICER_INFO_KEYS:
                self.info[key] = info.get(key)

        elif config.has_section("info"):
            info = dict(config.items("info"))
            if "visualizer" in info:
                info["visualizers"] = [ {"label": info.get("label",
                                                info.get("name", "Default")),
                                         "url": info["visualizer"]} ]
            for key in SLICER_INFO_KEYS:
                self.info[key] = info.get(key)

        # Register stores from external stores.ini file or a dictionary
        if not stores and config.has_option("workspace", "stores_file"):
            stores = config.get("workspace", "stores_file")

            # Prepend the root directory if stores is relative
            if self.root_dir and not os.path.isabs(stores):
                stores = os.path.join(self.root_dir, stores)

        if isinstance(stores, basestring):
            store_config = ConfigParser.SafeConfigParser()
            try:
                store_config.read(stores)
            except Exception as e:
                raise ConfigurationError("Unable to read stores from %s. "
                                "Reason: %s" % (stores, str(e) ))

            for store in store_config.sections():
                self._register_store_dict(store,
                                          dict(store_config.items(store)))

        elif isinstance(stores, dict):
            for name, store in stores.items():
                self._register_store_dict(name, store)

        elif stores is not None:
            raise ConfigurationError("Unknown stores description object: %s" %
                                                    (type(stores)))

        # Calendar
        # ========

        if config.has_option("workspace", "timezone"):
            timezone = config.get("workspace", "timezone")
        else:
            timezone = None

        if config.has_option("workspace", "first_weekday"):
            first_weekday = config.get("workspace", "first_weekday")
        else:
            first_weekday = 0

        self.logger.debug("Workspace calendar timezone: %s first week day: %s"
                          % (timezone, first_weekday))
        self.calendar = Calendar(timezone=timezone,
                                 first_weekday=first_weekday)

        # Register Stores
        # ===============
        #
        # * Default store is [store] in main config file
        # * Stores are also loaded from main config file from sections with
        #   name [store_*] (not documented feature)

        default = None
        if config.has_section("store"):
            default = dict(config.items("store"))

        if default:
            self._register_store_dict("default",default)

        # Register [store_*] from main config (not documented)
        for section in config.sections():
            if section.startswith("store_"):
                name = section[6:]
                self._register_store_dict(name, dict(config.items(section)))

        if config.has_section("browser"):
            self.browser_options = dict(config.items("browser"))
        else:
            self.browser_options = {}

        if config.has_section("main"):
            self.options = dict(config.items("main"))
        else:
            self.options = {}

        # Authorizer
        # ==========

        if config.has_option("workspace", "authorization"):
            auth_type = config.get("workspace", "authorization")
            options = dict(config.items("authorization"))
            self.authorizer = extensions.authorizer(auth_type, **options)
        else:
            self.authorizer = None

        # Configure and load models
        # =========================

        # Load base model (default)
        import pkgutil
        if config.has_option("workspace", "load_base_model"):
            load_base = config.getboolean("workspace", "load_base_model")
        else:
            load_base = load_base_model

        if load_base:
            loader = pkgutil.get_loader("cubes")
            path = os.path.join(loader.filename, "models/base.cubesmodel")
            self.import_model(path)

        # TODO: remove this depreciation code
        if config.has_section("model"):
            self.logger.warn("Section [model] is depreciated. Use 'model' in "
                             "[workspace] for single default model or use "
                             "section [models] to list multiple models.")
            if config.has_option("model", "path"):
                source = config.get("model", "path")
                self.logger.debug("Loading model from %s" % source)
                self.import_model(source)

        models = []
        if config.has_option("workspace", "model"):
            models.append(config.get("workspace", "model"))
        if config.has_section("models"):
            models += [path for name, path in config.items("models")]

        for model in models:
            self.logger.debug("Loading model %s" % model)
            self.import_model(model)

    def _register_store_dict(self, name, info):
        info = dict(info)
        try:
            type_ = info.pop("type")
        except KeyError:
            try:
                type_ = info.pop("backend")
            except KeyError:
                raise ConfigurationError("Store '%s' has no type specified" % name)
            else:
                self.logger.warn("'backend' is depreciated, use 'type' for "
                                 "store (in %s)." % str(name))

        self.register_store(name, type_, **info)

    def register_default_store(self, type_, **config):
        """Convenience function for registering the default store. For more
        information see `register_store()`"""
        self.register_store("default", type_, **config)

    def register_store(self, name, type_, include_model=True, **config):
        """Adds a store configuration."""

        config = dict(config)

        if name in self.store_infos:
            raise ConfigurationError("Store %s already registered" % name)

        self.store_infos[name] = (type_, config)

        # Model and provider
        # ------------------

        # If store brings a model, then include it...
        if include_model and "model" in config:
            model = config.pop("model")
        else:
            model = None

        # Get related model provider or override it with configuration
        ext = extensions.store.get(type_)
        provider = ext.related_model_provider
        provider = config.pop("model_provider", provider)

        nsname = config.pop("namespace", None)

        if model:
            self.import_model(model, store=name, namespace=nsname,
                              provider=provider)
        elif provider:
            # Import empty model and register the provider
            self.import_model({}, store=name, namespace=nsname,
                              provider=provider)

    def _store_for_model(self, metadata):
        """Returns a store for model specified in `metadata`. """
        store_name = metadata.get("store")
        if not store_name and "info" in metadata:
            store_name = metadata["info"].get("store")

        store_name = store_name or "default"

        return store_name

    # TODO: This is new method, replaces add_model. "import" is more
    # appropriate as it denotes that objects are imported and the model is
    # "dissolved"
    def import_model(self, metadata=None, provider=None, store=None,
                     translations=None, namespace=None):

        """Registers the model `metadata` in the workspace. `metadata` can be
        a metadata dictionary, filename, path to a model bundle directory or a
        URL.

        If `namespace` is specified, then the model's objects are stored in 
        the namespace of that name.

        `store` is an optional name of data store associated with the model.
        If not specified, then the one from the metadata dictionary will be
        used.

        Model's provider is registered together with loaded metadata. By
        default the objects are registered in default global namespace.

        Note: No actual cubes or dimensions are created at the time of calling
        this method. The creation is deferred until
        :meth:`cubes.Workspace.cube` or :meth:`cubes.Workspace.dimension` is
        called.
        """

        if isinstance(metadata, basestring):
            self.logger.debug("Importing model from %s. "
                              "Provider: %s Store: %s NS: %s"
                              % (metadata, provider, store, namespace))
            path = metadata
            if self.models_dir and not os.path.isabs(path):
                path = os.path.join(self.models_dir, path)
            metadata = read_model_metadata(path)
        elif isinstance(metadata, dict):
            self.logger.debug("Importing model from dictionary. "
                              "Provider: %s Store: %s NS: %s"
                              % (provider, store, namespace))

        else:
            raise ConfigurationError("Unknown model '%s' "
                                     "(should be a filename or a dictionary)"
                                     % model)

        # Create a model provider if name is given. Otherwise assume that the
        # `provider` is a ModelProvider subclass instance
        # TODO: add translations
        if isinstance(provider, basestring):
            provider = extensions.model_provider(provider, metadata)

        if not provider:
            provider_name = metadata.get("provider", "default")
            provider = extensions.model_provider(provider_name, metadata)

        store = store or metadata.get("store")

        if store or provider.requires_store():
            if store and not isinstance(store, basestring):
                raise ArgumentError("Store should be a name, not an object")
            provider.set_store(self.get_store(store), store)

        # We are not getting list of cubes here, we are lazy

        if namespace:
            if isinstance(namespace, basestring):
                (ns, _) = self.namespace.namespace(namespace, create=True)
            else:
                ns = namepsace
        elif store != "default":
            # Store in store's namespace
            # TODO: use default namespace
            (ns, _) = self.namespace.namespace(store, create=True)
        else:
            ns = self.namespace

        ns.add_provider(provider)

    # TODO: depreciated
    def add_model(self, model, name=None, store=None, translations=None):
        self.logger.warn("add_model() is depreciated, use import_model()")
        return self.import_model(model, store=store, translations=translations)

    def add_slicer(self, name, url, **options):
        """Register a slicer as a model and data provider."""
        self.register_store(name, "slicer", url=url, **options)

        model = {
            "store": name,
            "provider": "slicer",
            "store": name
        }
        self.import_model(model)

    def list_cubes(self, identity=None):
        """Get a list of metadata for cubes in the workspace. Result is a list
        of dictionaries with keys: `name`, `label`, `category`, `info`.

        The list is fetched from the model providers on the call of this
        method.

        If the workspace has an authorizer, then it is used to authorize the
        cubes for `identity` and only authorized list of cubes is returned.
        """

        all_cubes = self.namespace.list_cubes(recursive=True)

        if self.authorizer:
            by_name = dict((cube["name"], cube) for cube in all_cubes)
            names = [cube["name"] for cube in all_cubes]

            authorized = self.authorizer.authorize(identity, names)
            all_cubes = [by_name[name] for name in authorized]

        return all_cubes

    def cube(self, name, identity=None, locale=None):
        """Returns a cube with `name`"""

        if not isinstance(name, basestring):
            raise TypeError("Name is not a string, is %s" % type(name))

        if self.authorizer:
            authorized = self.authorizer.authorize(identity, [name])
            if not authorized:
                raise NotAuthorized

        cube_key = (name, locale)
        if name in self._cubes:
            return self._cubes[cube_key]

        (ns, ns_cube) = self.namespace.namespace_for_cube(name)

        recursive = (self.lookup_method == "recursive")
        cube = ns.cube(ns_cube, locale=locale, recursive=recursive)

        # Set cube name to the full cube reference that includes namespace as
        # well
        cube.name = name
        cube.basename = name.split(".")[-1]

        self.link_cube(cube, ns)

        self._cubes[cube_key] = cube

        return cube

    def link_cube(self, cube, namespace):
        """Links dimensions to the cube in the context of `model` with help of
        `provider`."""

        # Assumption: empty cube

        if cube.provider:
            providers = [cube.provider]
        else:
            providers = []
        if namespace:
            providers.append(namespace)

        # Add the default namespace as the last look-up place, if not present
        providers.append(self.namespace)

        dimensions = {}
        for link in cube.dimension_links:
            dim_name = link["name"]
            try:
                dim = self.dimension(dim_name,
                                     locale=cube.locale,
                                     providers=providers)
            except TemplateRequired as e:
                raise ModelError("Dimension template '%s' missing" % dim_name)

            dimensions[dim_name] = dim

        cube.link_dimensions(dimensions)

    def _lookup_dimension(self, name, providers, templates):
        """Look-up a dimension `name` in chain of `providers` which might
        include a mix of providers and namespaces.

        `templates` is an optional dictionary with already instantiated
        dimensions that can be used as templates.
        """

        dimension = None
        required_template = None

        # FIXME: cube's provider might be hit at least twice: once as provider,
        # second time as part of cube's namespace

        for provider in providers:
            try:
                dimension = provider.dimension(name, templates=templates)
            except NoSuchDimensionError:
                pass
            else:
                return dimension
            # We are passing the TemplateRequired exception
        raise NoSuchDimensionError("Dimension '%s' not found" % name,
                                   name=name)

    def dimension(self, name, locale=None, providers=None):
        """Returns a dimension with `name`. Raises `NoSuchDimensionError` when
        no model published the dimension. Raises `RequiresTemplate` error when
        model provider requires a template to be able to provide the
        dimension, but such template is not a public dimension.

        The standard lookup is:

        1. look in the cube's provider
        2. look in the cube's namespace (all providers)
        3. look in the default (global) namespace
        """

        # Collected dimensions – to be used as templates
        templates = {}

        if providers:
            providers = list(providers)
        else:
            # If no providers are given then use the default namespace
            # (otherwise we would end up without any dimension)
            providers = [self.namespace]

        # Assumption: all dimensions that are to be used as templates should
        # be public dimensions. If it is a private dimension, then the
        # provider should handle the case by itself.
        missing = set( (name, ) )
        while missing:
            dimension = None
            deferred = set()

            name = missing.pop()

            # First give a chance to provider, then to namespace
            dimension = None
            required_template = None

            try:
                dimension = self._lookup_dimension(name, providers, templates)
            except TemplateRequired as e:
                required_template = e.template

            if required_template in templates:
                raise BackendError("Some model provider didn't make use of "
                                   "dimension template '%s' for '%s'"
                                   % (required_template, name))

            if required_template:
                missing.add(name)
                if required_template in missing:
                    raise ModelError("Dimension templates cycle in '%s'" %
                                     required_template)
                missing.add(required_template)

            # Store the created dimension to be used as template
            if dimension:
                templates[name] = dimension

        return dimension

    def _browser_options(self, cube):
        """Returns browser configuration options for `cube`. The options are
        taken from the configuration file and then overriden by cube's
        `browser_options` attribute."""

        options = dict(self.browser_options)
        if cube.browser_options:
            options.update(cube.browser_options)

        return options

    def browser(self, cube, locale=None, identity=None):
        """Returns a browser for `cube`."""

        # TODO: bring back the localization
        # model = self.localized_model(locale)

        if isinstance(cube, basestring):
            cube = self.cube(cube, identity=identity)

        locale = locale or cube.locale

        store_name = cube.datastore or "default"
        store = self.get_store(store_name)
        store_type = self.store_infos[store_name][0]
        store_info = self.store_infos[store_name][1]

        cube_options = self._browser_options(cube)

        # TODO: merge only keys that are relevant to the browser!
        options = dict(store_info)
        options.update(cube_options)

        # TODO: Construct options for the browser from cube's options dictionary and
        # workspece default configuration
        #

        browser_name = cube.browser
        if not browser_name and hasattr(store, "default_browser_name"):
            browser_name = store.default_browser_name
        if not browser_name:
            browser_name = store_type
        if not browser_name:
            raise ConfigurationError("No store specified for cube '%s'" % cube)

        browser = extensions.browser(browser_name, cube, store=store,
                                     locale=locale, calendar=self.calendar,
                                     **options)

        # TODO: remove this once calendar is used in all backends
        browser.calendar = self.calendar

        return browser

    def cube_features(self, cube, identity=None):
        """Returns browser features for `cube`"""
        # TODO: this might be expensive, make it a bit cheaper
        # recycle the feature-providing browser or something. Maybe use class
        # method for that
        return self.browser(cube, identity).features()

    def get_store(self, name=None):
        """Opens a store `name`. If the store is already open, returns the
        existing store."""

        name = name or "default"

        if name in self.stores:
            return self.stores[name]

        try:
            type_, options = self.store_infos[name]
        except KeyError:
            raise ConfigurationError("No info for store %s" % name)

        store = extensions.store(type_, **options)
        self.stores[name] = store
        return store

    def close(self):
        """Closes the workspace with all open stores and other associated
        resources."""

        for store in self.open_stores:
            store.close()


# TODO: Remove following depreciated functions

def get_backend(name):
    raise NotImplementedError("get_backend() is depreciated. "
                              "Use Workspace instead." )


def create_workspace(backend_name, model, **options):
    raise NotImplemented("create_workspace() is depreciated, "
                         "use Workspace(config) instead")


def create_workspace_from_config(config):
    raise NotImplemented("create_workspace_from_config() is depreciated, "
                         "use Workspace(config) instead")


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Cubes documentation build configuration file, created by
# sphinx-quickstart on Wed Dec 15 11:57:31 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo']
autoclass_content = 'init'
autodoc_default_flags = ['members']
# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

todo_include_todos = True

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Cubes'
copyright = u'2010-2014, Stefan Urbanek'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
# import cubes
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0alpha2'

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
htmlhelp_basename = 'Cubesdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
latex_paper_size = 'a4'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Cubes.tex', u'Cubes Documentation',
   u'Stefan Urbanek', 'manual'),
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

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'cubes', u'Cubes Documentation',
     [u'Stefan Urbanek'], 1)
]

########NEW FILE########
__FILENAME__ = application
"""Dimension Browser example

A Flask application for browsing cube's dimensions.

Requirements: run ``python prepare_data.py`` in ``../hello_world``.

Use::
    python application.py

Then navigate your browser to: ``http://localhost:5000``

You can also access the Slicer at ``http://localhost:5000/slicer``.
"""
from flask import Flask, render_template, request, make_response
from cubes import Workspace, Cell, cuts_from_string
from cubes.server import slicer, workspace
from flask import current_app

#
# The Flask Application
#
app = Flask(__name__)

# Cube we are going to browse (only one for this example)
#

CUBE_NAME="irbd_balance"

@app.route("/favicon.ico")
def favicon():
    return make_response("")

@app.route("/")
@app.route("/<dim_name>")
def report(dim_name=None):
    browser = workspace.browser(CUBE_NAME)
    cube = browser.cube

    if not dim_name:
        return render_template('report.html', dimensions=cube.dimensions)

    # First we need to get the hierarchy to know the order of levels. Cubes
    # supports multiple hierarchies internally.

    dimension = cube.dimension(dim_name)
    hierarchy = dimension.hierarchy()

    # Parse the`cut` request parameter and convert it to a list of 
    # actual cube cuts. Think of this as of multi-dimensional path, even that 
    # for this simple example, we are goint to use only one dimension for
    # browsing.

    cutstr = request.args.get("cut")
    cell = Cell(cube, cuts_from_string(cube, cutstr))

    # Get the cut of actually browsed dimension, so we know "where we are" -
    # the current dimension path
    cut = cell.cut_for_dimension(dimension)

    if cut:
        path = cut.path
    else:
        path = []

    #
    # Do the work, do the aggregation.
    #
    result = browser.aggregate(cell, drilldown=[dim_name])

    # If we have no path, then there is no cut for the dimension, # therefore
    # there is no corresponding detail.
    if path:
        details = browser.cell_details(cell, dimension)[0]
    else:
        details = []

    # Find what level we are on and what is going to be the drill-down level
    # in the hierarchy

    levels = hierarchy.levels_for_path(path)
    if levels:
        next_level = hierarchy.next_level(levels[-1])
    else:
        next_level = hierarchy.next_level(None)

    # Are we at the very detailed level?

    is_last = hierarchy.is_last(next_level)
    # Finally, we render it

    return render_template('report.html',
                            dimensions=cube.dimensions,
                            dimension=dimension,
                            levels=levels,
                            next_level=next_level,
                            result=result,
                            cell=cell,
                            is_last=is_last,
                            details=details)


if __name__ == "__main__":

    # Create a Slicer and register it at http://localhost:5000/slicer
    app.register_blueprint(slicer, url_prefix="/slicer", config="slicer.ini")
    app.run(debug=True)



########NEW FILE########
__FILENAME__ = table
# -*- coding=utf  -*-
# Formatters example
#
# Requirements:
#       Go to the ../hello_world directory and do: python prepare_data.py
#
# Instructions:
#
#       Just run this file:
#
#            python table.py
# Output:
#   * standard input – text table
#   * table.html
#   * cross_table.html
#

from cubes import Workspace, create_formatter

workspace = Workspace("slicer.ini")

# Create formatters
text_formatter = create_formatter("text_table")
html_formatter = create_formatter("simple_html_table")
html_cross_formatter = create_formatter("html_cross_table")

# Get the browser and data

browser = workspace.browser("irbd_balance")

result = browser.aggregate(drilldown=["item"])
result = result.cached()

#
# 1. Create text output
#
print "Text output"
print "-----------"

print text_formatter(result, "item")


#
# 2. Create HTML output (see table.html)
#
with open("table.html", "w") as f:
    data = html_formatter(result, "item")
    f.write(data)

#
# 3. Create cross-table to cross_table.html
#
result = browser.aggregate(drilldown=["item", "year"])
with open("cross_table.html", "w") as f:
    data = html_cross_formatter(result,
                                onrows=["year"],
                                oncolumns=["item.category_label"])
    f.write(data)

print "Check also table.html and cross_table.html files"

########NEW FILE########
__FILENAME__ = aggregate
from cubes import Workspace, Cell, PointCut

# 1. Create a workspace
workspace = Workspace()
workspace.register_default_store("sql", url="sqlite:///data.sqlite")
workspace.import_model("model.json")

# 2. Get a browser
browser = workspace.browser("irbd_balance")

# 3. Play with aggregates
result = browser.aggregate()

print "Total\n" \
      "----------------------"

print "Record count: %8d" % result.summary["record_count"]
print "Total amount: %8d" % result.summary["amount_sum"]

#
# 4. Drill-down through a dimension
#

print "\n" \
      "Drill Down by Category (top-level Item hierarchy)\n" \
      "================================================="
#
result = browser.aggregate(drilldown=["item"])
#
print ("%-20s%10s%10s\n"+"-"*40) % ("Category", "Count", "Total")
#
for row in result.table_rows("item"):
    print "%-20s%10d%10d" % ( row.label,
                              row.record["record_count"],
                              row.record["amount_sum"])

print "\n" \
      "Slice where Category = Equity\n" \
      "================================================="

cut = PointCut("item", ["e"])
cell = Cell(browser.cube, cuts = [cut])

result = browser.aggregate(cell, drilldown=["item"])

print ("%-20s%10s%10s\n"+"-"*40) % ("Sub-category", "Count", "Total")

for row in result.table_rows("item"):
    print "%-20s%10d%10d" % ( row.label,
                              row.record["record_count"],
                              row.record["amount_sum"])

########NEW FILE########
__FILENAME__ = prepare_data
# -*- coding: utf-8 -*-
# Data preparation for the hello_world example

from sqlalchemy import create_engine
from cubes.tutorial.sql import create_table_from_csv

# 1. Prepare SQL data in memory

FACT_TABLE = "irbd_balance"

print "preparing data..."

engine = create_engine('sqlite:///data.sqlite')

create_table_from_csv(engine,
                      "data.csv",
                      table_name=FACT_TABLE,
                      fields=[
                            ("category", "string"),
                            ("category_label", "string"),
                            ("subcategory", "string"),
                            ("subcategory_label", "string"),
                            ("line_item", "string"),
                            ("year", "integer"),
                            ("amount", "integer")],
                      create_id=True
                  )

print "done. file data.sqlite created"


########NEW FILE########
__FILENAME__ = application
"""Example model browser.

Use:

    python application.py [slicer.ini]

"""

from flask import Flask, render_template, request
from cubes import Workspace
import argparse
import ConfigParser

app = Flask(__name__)

#
# Data we aregoing to browse and logical model of the data
#

# Some global variables. We do not have to care about Flask provided thread
# safety here, as they are non-mutable.

workspace = None
model = None
cube_name = None

@app.route("/")
@app.route("/<dim_name>")
def report(dim_name=None):
    browser = get_browser()
    cube = browser.cube
    mapper = browser.mapper
    if dim_name:
        dimension = cube.dimension(dim_name)
        physical = {}
        for attribute in dimension.all_attributes:
            logical = attribute.ref()
            physical[logical] = mapper.physical(attribute)
    else:
        dimension = None
        physical = None

    return render_template('index.html',
                            dimensions=cube.dimensions,
                            dimension=dimension,
                            mapping=physical)

def get_browser():
    global cube_name
    if not cube_name:
        # Get the first cube in the list
        cubes = workspace.list_cubes()
        cube_name = cubes[0]["name"]

    return workspace.browser(cube_name)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Cubes model browser.')
    parser.add_argument('config', help='server confuguration .ini file')
    parser.add_argument('cube', nargs='?', default=None, help='cube name')
    args = parser.parse_args()

    config = ConfigParser.SafeConfigParser()
    try:
        config.read(args.config)
    except Exception as e:
        raise Exception("Unable to load config: %s" % e)

    cube_name = args.cube

    workspace = Workspace(config)

    app.debug = True
    app.run()

########NEW FILE########
__FILENAME__ = app
# -*- encoding: utf8 -*-

"""Cubes Modeler – experimental Flask app.

Note: Use only as local server with slicer:

    slicer model edit MODEL [TARGET]

"""

from flask import Flask, render_template, request
from cubes import Model, read_model_metadata, create_model_provider
from cubes import get_logger, write_model_metadata_bundle
from cubes import expand_dimension_metadata
import json
from collections import OrderedDict
from itertools import count
import argparse

__all__ = (
    "run_modeler",
    "ModelEditorSlicerCommand"
)

modeler = Flask(__name__, static_folder='static', static_url_path='')

# TODO: maybe we should not have these as globals
# Model:
CUBES = OrderedDict()
DIMENSIONS = OrderedDict()
MODEL = {}
SOURCE = None

cube_id_sequence = count(1)
dimension_id_sequence = count(1)

saved_model_filename = "saved_model.cubesmodel"

def import_model(path):
    # We need to use both: the metadata and the created model, as we do not
    # want to reproduce the model creation here
    global MODEL

    cube_id_sequence = count(1)
    dimension_id_sequence = count(1)

    logger = get_logger()
    logger.setLevel("INFO")
    logger.info("importing model from %s" % path)

    metadata = read_model_metadata(path)

    cube_list = metadata.pop("cubes", [])
    for i, cube in enumerate(cube_list):
        cube_id = cube_id_sequence.next()
        cube["id"] = cube_id
        CUBES[str(cube_id)] = cube

    dim_list = metadata.pop("dimensions", [])
    for i, dim in enumerate(dim_list):
        dim = expand_dimension_metadata(dim)

        dim_id = dimension_id_sequence.next()
        dim["id"] = dim_id
        DIMENSIONS[str(dim_id)] = dim

    MODEL = metadata

    # Convert joins (of known types)
    # TODO: currently we assume that all JOINS are SQL joins as we have no way
    # to determine actual store and therefore the backend used for
    # interpreting this model

    joins = metadata.pop("joins", [])

    for join in joins:
        if "detail" in join:
            join["detail"] = _fix_sql_join_value(join["detail"])
        if "master" in join:
            join["master"] = _fix_sql_join_value(join["master"])
        join["__type__"] = "sql"

    MODEL["joins"] = joins


def _fix_sql_join_value(value):
    if isinstance(value, basestring):
        split = value.split(".")
        if len(split) > 1:
            join = {
                "table": split[0],
                "column": ".".join(split[1:])
            }
        else:
            join = {"column":value}
        return join
    else:
        return value


def save_model():
    model = dict(MODEL)
    model["cubes"] = list(CUBES.values())
    model["dimensions"] = list(DIMENSIONS.values())

    # with open(SAVED_MODEL_FILENAME, "w") as f:
    #     json.dump(model, f, indent=4)

    write_model_metadata_bundle(saved_model_filename, model, replace=True)


@modeler.route("/")
def index():
    return render_template('index.html')


@modeler.route("/reset")
def reset_model():
    # This is just development reset
    print "Model reset"
    global MODEL, CUBES, DIMENSION
    global cube_id_sequence, dimension_id_sequence

    if SOURCE:
        import_model(SOURCE)
    else:
        cube_id_sequence = count(1)
        dimension_id_sequence = count(1)
        CUBES = OrderedDict()
        DIMENSIONS = OrderedDict()
        MODEL = {}

    return "ok"


@modeler.route("/model")
def get_model():
    # Note: this returns model metadata sans cubes/dimensions
    print MODEL
    return json.dumps(MODEL)


@modeler.route("/model", methods=["PUT"])
def save_model_rq():
    global MODEL
    print request.data
    MODEL = json.loads(request.data)
    save_model()

    return "ok"


@modeler.route("/cubes")
def list_cubes():
    # TODO: return just relevant info
    print json.dumps(CUBES.values())
    return json.dumps(CUBES.values())


def fix_attribute_list(attributes):
    if not attributes:
        return []

    fixed = []
    for attribute in attributes:
        if isinstance(attribute, basestring):
            attribute = {"name": attribute}
        fixed.append(attribute)

    return fixed


@modeler.route("/cube/<id>", methods=["PUT"])
def save_cube(id):
    cube = json.loads(request.data)
    CUBES[str(id)] = cube
    save_model()

    return "ok"


@modeler.route("/cube/<id>", methods=["GET"])
def get_cube(id):
    info = CUBES[str(id)]

    info["measures"] = fix_attribute_list(info.get("measures"))
    info["aggregates"] = fix_attribute_list(info.get("aggregates"))
    info["details"] = fix_attribute_list(info.get("details"))

    joins = info.pop("joins", [])

    for join in joins:
        if "detail" in join:
            join["detail"] = _fix_sql_join_value(join["detail"])
        if "master" in join:
            join["master"] = _fix_sql_join_value(join["master"])
        join["__type__"] = "sql"

    info["joins"] = joins

    return json.dumps(info)

@modeler.route("/new_cube", methods=["PUT"])
def new_cube():
    cube_id = cube_id_sequence.next()
    cube = {
        "id": cube_id,
        "name": "cube%d" % cube_id,
        "label": "New Cube %s" % cube_id,
        "dimensions": [],
        "aggregates": [],
        "measures": [],
        "mappings": {},
        "joins": [],
        "info": {}
    }

    CUBES[str(cube_id)] = cube

    return json.dumps(cube)


@modeler.route("/dimensions")
def list_dimensions():
    # TODO: return just relevant info
    return json.dumps(DIMENSIONS.values())


@modeler.route("/dimension/<id>", methods=["PUT"])
def save_dimension(id):
    dim = json.loads(request.data)
    DIMENSIONS[str(id)] = dim
    save_model()

    return "ok"


@modeler.route("/dimension/<id>", methods=["GET"])
def get_dimension(id):
    info = DIMENSIONS[str(id)]
    return json.dumps(info)

@modeler.route("/new_dimension", methods=["PUT"])
def new_cube():
    dim_id = dimension_id_sequence.next()
    level = {
        "name": "default",
        "attributes": [
            {"name":"attribute"}
        ]
    };
    hier = {"name":"default", "levels": ["default"]}
    dim = {
        "id": dim_id,
        "name": "dim%d" % dim_id,
        "label": "New Dimension %s" % dim_id,
        "levels": [level],
        "hierarchies": [hier]
    }

    DIMENSIONS[str(dim_id)] = dim

    return json.dumps(dim)


def run_modeler(source, target="saved_model.cubesmodel", port=5000):
    global saved_model_filename

    saved_model_filename = target

    global SOURCE
    if source:
        import_model(source)
        SOURCE = source

    modeler.run(host="0.0.0.0", port=port, debug=True)


# TODO: make slicer to be extensible with objects like this one:
class ModelEditorSlicerCommand(object):
    def configure_parser(self, parser):
        """Return argument parser for the modeler tool."""

        parser.add_argument('-p', '--port',
                                    dest='port',
                                    default=5000,
                                    help='port to run the editor web server on')
        parser.add_argument("-s", "--store-type",
                            dest="store_type", default="sql",
                            help="Store type for mappings and joins editors")
        parser.add_argument("model", nargs="?",
                            help="Path to the model to be edited")
        parser.add_argument("target", nargs="?",
                             help="optional target path to write model to "
                                  "(otherwise saved_model in current directory "
                                  "will be used)")
        return parser

    def __call__(self, args):
        """Run the modeler."""
        global saved_model_filename
        global SOURCE
        global MODEL

        saved_model_filename = args.target or "saved_model.cubesmodel"

        if args.model:
            import_model(args.model)
            SOURCE = args.model

        MODEL = MODEL or {}
        MODEL["__modeler_options__"] = {"store_type": args.store_type}

        modeler.run(host="0.0.0.0", port=args.port, debug=True)


if __name__ == '__main__':
    import sys
    import webbrowser

    command = ModelEditorSlicerCommand()
    parser = argparse.ArgumentParser(description='Cubes Model Editor')
    command.configure_parser(parser)
    args = parser.parse_args(sys.argv[1:])
    command(args)


########NEW FILE########
__FILENAME__ = auth
# -*- coding=utf -*-
import unittest
from cubes import *
from .common import CubesTestCaseBase

from json import dumps

def printable(obj):
    return dumps(obj, indent=4)

class AuthTestCase(CubesTestCaseBase):
    def setUp(self):
        self.sales_cube = Cube("sales")
        self.churn_cube = Cube("churn")

    def test_empty(self):
        self.auth = SimpleAuthorizer()
        self.assertEqual([], self.auth.authorize("john", [self.sales_cube]))

    def test_authorize(self):
        rights = {
            "john": {"allowed_cubes": ["sales"]}
        }
        self.auth = SimpleAuthorizer(rights=rights)

        self.assertEqual([self.sales_cube],
                         self.auth.authorize("john", [self.sales_cube]))
        self.assertEqual([], self.auth.authorize("ivana", [self.churn_cube]))

    def test_deny(self):
        rights = {
            "john": {"denied_cubes": ["sales"]}
        }
        self.auth = SimpleAuthorizer(rights=rights)

        self.assertEqual([self.churn_cube], self.auth.authorize("john", [self.churn_cube]))

        self.assertEqual([],
                         self.auth.authorize("john", [self.sales_cube]))
        self.assertEqual([], self.auth.authorize("ivana", [self.churn_cube]))

    def test_allow(self):
        rights = {
            "john": {"denied_cubes": ["sales"]},
            "ivana": {}
        }
        self.auth = SimpleAuthorizer(rights=rights)

        self.assertEqual([self.churn_cube],
                         self.auth.authorize("ivana", [self.churn_cube]))

    def test_order(self):
        rights = {
            "john": {
                "denied_cubes": ["sales"],
                "allowed_cubes": ["sales"]
            },
            "ivana": {
                "denied_cubes": ["sales"],
                "allowed_cubes": ["*"]
            },
            "fero": {
                "denied_cubes": ["*"],
                "allowed_cubes": ["sales"]
            },
            "magda": {
                "denied_cubes": ["*"],
                "allowed_cubes": ["*"]
            },
        }
        self.auth = SimpleAuthorizer(rights=rights)
        self.assertEqual([self.sales_cube],
                         self.auth.authorize("john", [self.sales_cube]))
        self.assertEqual([self.sales_cube],
                         self.auth.authorize("ivana", [self.sales_cube]))
        self.assertEqual([self.sales_cube],
                         self.auth.authorize("fero", [self.sales_cube]))
        self.assertEqual([self.sales_cube],
                         self.auth.authorize("magda", [self.sales_cube]))

        self.auth = SimpleAuthorizer(rights=rights, order="allow_deny")
        self.assertEqual([],
                         self.auth.authorize("john", [self.sales_cube]))
        self.assertEqual([],
                         self.auth.authorize("ivana", [self.sales_cube]))
        self.assertEqual([],
                         self.auth.authorize("fero", [self.sales_cube]))
        self.assertEqual([],
                         self.auth.authorize("magda", [self.sales_cube]))

    def test_role(self):
        roles = {
            "marketing": {"allowed_cubes": ["sales"]}
        }
        rights = {
            "john": {"roles": ["marketing"]}
        }
        self.auth = SimpleAuthorizer(rights=rights, roles=roles)

        self.assertEqual([self.sales_cube],
                         self.auth.authorize("john", [self.sales_cube]))

    def test_role_inheritance(self):
        roles = {
            "top": {"allowed_cubes": ["sales"]},
            "marketing": {"roles": ["top"]}
        }
        rights = {
            "john": {"roles": ["marketing"]}
        }
        self.auth = SimpleAuthorizer(rights=rights, roles=roles)

        self.assertEqual([self.sales_cube],
                         self.auth.authorize("john", [self.sales_cube]))


########NEW FILE########
__FILENAME__ = aggregates
# -*- coding=utf -*-
import unittest
from sqlalchemy import create_engine, MetaData, Table, Integer, String, Column
from cubes import *
from cubes.errors import *
from ...common import CubesTestCaseBase

from json import dumps

def printable(obj):
    return dumps(obj, indent=4)

class AggregatesTestCase(CubesTestCaseBase):
    sql_engine = "sqlite:///"

    def setUp(self):
        super(AggregatesTestCase, self).setUp()

        self.facts = Table("facts", self.metadata,
                        Column("id", Integer),
                        Column("year", Integer),
                        Column("amount", Integer),
                        Column("price", Integer),
                        Column("discount", Integer)
                        )
        self.metadata.create_all()

        data = [
            ( 1, 2010, 1, 100,  0),
            ( 2, 2010, 2, 200, 10),
            ( 3, 2010, 4, 300,  0),
            ( 4, 2010, 8, 400, 20),
            ( 5, 2011, 1, 500,  0),
            ( 6, 2011, 2, 600, 40),
            ( 7, 2011, 4, 700,  0),
            ( 8, 2011, 8, 800, 80),
            ( 9, 2012, 1, 100,  0),
            (10, 2012, 2, 200,  0),
            (11, 2012, 4, 300,  0),
            (12, 2012, 8, 400, 10),
            (13, 2013, 1, 500,  0),
            (14, 2013, 2, 600,  0),
            (15, 2013, 4, 700,  0),
            (16, 2013, 8, 800, 20),
        ]

        self.load_data(self.facts, data)
        self.workspace = self.create_workspace(model="aggregates.json")

    def test_unknown_function(self):
        browser = self.workspace.browser("unknown_function")

        with self.assertRaisesRegexp(ArgumentError, "Unknown.*function"):
            browser.aggregate()

    def test_explicit(self):
        browser = self.workspace.browser("default")
        result = browser.aggregate()
        summary = result.summary
        self.assertEqual(60, summary["amount_sum"])
        self.assertEqual(16, summary["count"])

    def test_post_calculation(self):
        browser = self.workspace.browser("postcalc_in_measure")

        result = browser.aggregate(drilldown=["year"])
        cells = list(result.cells)
        aggregates = sorted(cells[0].keys())
        self.assertSequenceEqual(['amount_sma', 'amount_sum', 'count', 'year'],
                                 aggregates)

########NEW FILE########
__FILENAME__ = browser
import unittest
import os
import json
import re
import sqlalchemy
import datetime

from ...common import CubesTestCaseBase
from sqlalchemy import Table, Column, Integer, Float, String, MetaData, ForeignKey
from sqlalchemy import create_engine
from cubes.backends.sql.mapper import coalesce_physical
from cubes.backends.sql.browser import *

from cubes import *
from cubes.errors import *

class StarSQLTestCase(CubesTestCaseBase):
    def setUp(self):
        super(StarSQLTestCase, self).setUp()

        self.engine = sqlalchemy.create_engine('sqlite://')
        metadata = sqlalchemy.MetaData(bind=self.engine)

        table = Table('sales', metadata,
                        Column('id', Integer, primary_key=True),
                        Column('amount', Float),
                        Column('discount', Float),
                        Column('fact_detail1', String),
                        Column('fact_detail2', String),
                        Column('flag', String),
                        Column('date_id', Integer),
                        Column('product_id', Integer),
                        Column('category_id', Integer)
                    )

        table = Table('dim_date', metadata,
                        Column('id', Integer, primary_key=True),
                        Column('day', Integer),
                        Column('month', Integer),
                        Column('month_name', String),
                        Column('month_sname', String),
                        Column('year', Integer)
                    )

        table = Table('dim_product', metadata,
                        Column('id', Integer, primary_key=True),
                        Column('category_id', Integer),
                        Column('product_name', String),
                    )

        table = Table('dim_category', metadata,
                        Column('id', Integer, primary_key=True),
                        Column('category_name_en', String),
                        Column('category_name_sk', String),
                        Column('subcategory_id', Integer),
                        Column('subcategory_name_en', String),
                        Column('subcategory_name_sk', String)
                    )

        self.metadata = metadata
        self.metadata.create_all(self.engine)

        self.workspace = self.create_workspace({"engine":self.engine},
                                               "sql_star_test.json")
        # self.workspace = Workspace()
        # self.workspace.register_default_store("sql", engine=self.engine)
        # self.workspace.add_model()
        self.cube = self.workspace.cube("sales")
        store = self.workspace.get_store("default")

        self.browser = SnowflakeBrowser(self.cube,store=store,
                                        dimension_prefix="dim_")
        self.browser.debug = True
        self.mapper = self.browser.mapper


@unittest.skip("Obsolete")
class QueryContextTestCase(StarSQLTestCase):
    def setUp(self):
        super(QueryContextTestCase, self).setUp()

    def test_denormalize(self):
        statement = self.browser.denormalized_statement()
        cols = [column.name for column in statement.columns]
        self.assertEqual(18, len(cols))

    def test_denormalize_locales(self):
        """Denormalized view should have all locales expanded"""
        statement = self.browser.denormalized_statement(expand_locales=True)
        cols = [column.name for column in statement.columns]
        self.assertEqual(20, len(cols))

    # TODO: move this to tests/browser.py
    def test_levels_from_drilldown(self):
        cell = Cell(self.cube)
        dim = self.cube.dimension("date")
        l_year = dim.level("year")
        l_month = dim.level("month")
        l_day = dim.level("day")

        drilldown = [("date", None, "year")]
        result = levels_from_drilldown(cell, drilldown)
        self.assertEqual(1, len(result))

        dd = result[0]
        self.assertEqual(dim, dd.dimension)
        self.assertEqual(dim.hierarchy(), dd.hierarchy)
        self.assertSequenceEqual([l_year], dd.levels)
        self.assertEqual(["date.year"], dd.keys)

        # Try "next level"

        cut = PointCut("date", [2010])
        cell = Cell(self.cube, [cut])

        drilldown = [("date", None, "year")]
        result = levels_from_drilldown(cell, drilldown)
        self.assertEqual(1, len(result))
        dd = result[0]
        self.assertEqual(dim, dd.dimension)
        self.assertEqual(dim.hierarchy(), dd.hierarchy)
        self.assertSequenceEqual([l_year], dd.levels)
        self.assertEqual(["date.year"], dd.keys)

        drilldown = ["date"]
        result = levels_from_drilldown(cell, drilldown)
        self.assertEqual(1, len(result))
        dd = result[0]
        self.assertEqual(dim, dd.dimension)
        self.assertEqual(dim.hierarchy(), dd.hierarchy)
        self.assertSequenceEqual([l_year, l_month], dd.levels)
        self.assertEqual(["date.year", "date.month"], dd.keys)

        # Try with range cell

        # cut = RangeCut("date", [2009], [2010])
        # cell = Cell(self.cube, [cut])

        # drilldown = ["date"]
        # expected = [(dim, dim.hierarchy(), [l_year, l_month])]
        # self.assertEqual(expected, levels_from_drilldown(cell, drilldown))

        # drilldown = [("date", None, "year")]
        # expected = [(dim, dim.hierarchy(), [l_year])]
        # self.assertEqual(expected, levels_from_drilldown(cell, drilldown))

        # cut = RangeCut("date", [2009], [2010, 1])
        # cell = Cell(self.cube, [cut])

        # drilldown = ["date"]
        # expected = [(dim, dim.hierarchy(), [l_year, l_month, l_day])]
        # self.assertEqual(expected, levels_from_drilldown(cell, drilldown))

        # Try "last level"

        cut = PointCut("date", [2010, 1,2])
        cell = Cell(self.cube, [cut])

        drilldown = [("date", None, "day")]
        result = levels_from_drilldown(cell, drilldown)
        dd = result[0]
        self.assertSequenceEqual([l_year, l_month, l_day], dd.levels)
        self.assertEqual(["date.year", "date.month", "date.id"], dd.keys)

        drilldown = ["date"]
        with self.assertRaisesRegexp(HierarchyError, "has only 3 levels"):
            levels_from_drilldown(cell, drilldown)


class RelevantJoinsTestCase(StarSQLTestCase):
    def setUp(self):
        super(RelevantJoinsTestCase, self).setUp()

        self.joins = [
                {"master":"fact.date_id", "detail": "dim_date.id"},
                {"master":["fact", "product_id"], "detail": "dim_product.id"},
                {"master":"fact.contract_date_id", "detail": "dim_date.id", "alias":"dim_contract_date"},
                {"master":"dim_product.subcategory_id", "detail": "dim_subcategory.id"},
                {"master":"dim_subcategory.category_id", "detail": "dim_category.id"}
            ]
        self.mapper._collect_joins(self.joins)
        self.mapper.mappings.update(
            {
                "product.subcategory": "dim_subcategory.subcategory_id",
                "product.subcategory_name.en": "dim_subcategory.subcategory_name_en",
                "product.subcategory_name.sk": "dim_subcategory.subcategory_name_sk"
            }
        )

    def attributes(self, *attrs):
        return self.cube.get_attributes(attrs)

    def test_basic_joins(self):
        relevant = self.mapper.relevant_joins(self.attributes("date.year"))
        self.assertEqual(1, len(relevant))
        self.assertEqual("dim_date", relevant[0].detail.table)
        self.assertEqual(None, relevant[0].alias)

        relevant = self.mapper.relevant_joins(self.attributes("product.name"))
        self.assertEqual(1, len(relevant))
        self.assertEqual("dim_product", relevant[0].detail.table)
        self.assertEqual(None, relevant[0].alias)

    @unittest.skip("missing model")
    def test_alias(self):
        relevant = self.mapper.relevant_joins(self.attributes("date.year"))
        self.assertEqual(1, len(relevant))
        self.assertEqual("dim_date", relevant[0].detail.table)
        self.assertEqual("dim_contract_date", relevant[0].alias)

    def test_snowflake(self):
        relevant = self.mapper.relevant_joins(self.attributes("product.subcategory"))

        self.assertEqual(2, len(relevant))
        test = sorted([r.detail.table for r in relevant])
        self.assertEqual(["dim_product","dim_subcategory"], test)
        self.assertEqual([None, None], [r.alias for r in relevant])

        relevant = self.mapper.relevant_joins(self.attributes("product.category_name"))

        self.assertEqual(3, len(relevant))
        test = sorted([r.detail.table for r in relevant])
        self.assertEqual(["dim_category", "dim_product","dim_subcategory"], test)
        self.assertEqual([None, None, None], [r.alias for r in relevant])


class MapperTestCase(unittest.TestCase):
    def test_coalesce_physical(self):
        def assertPhysical(expected, actual, default=None):
            ref = coalesce_physical(actual, default)
            self.assertEqual(expected, ref)

        assertPhysical((None, "table", "column", None, None, None, None),
                       "table.column")
        assertPhysical((None, "table", "column.foo", None, None, None, None),
                       "table.column.foo")
        assertPhysical((None, "table", "column", None, None, None, None),
                       ["table", "column"])
        assertPhysical(("schema", "table", "column", None, None, None, None),
                       ["schema", "table", "column"])
        assertPhysical((None, "table", "column", None, None, None, None),
                       {"column": "column"}, "table")
        assertPhysical((None, "table", "column", None, None, None, None),
                       {"table": "table", "column": "column"})
        assertPhysical(("schema", "table", "column", None, None, None, None),
                       {"schema": "schema", "table": "table", "column":
                        "column"})
        assertPhysical(("schema", "table", "column", "day", None, None, None),
                       {"schema": "schema", "table": "table", "column":
                        "column", "extract": "day"})


class StarSQLBrowserTestCase(StarSQLTestCase):
    def setUp(self):
        super(StarSQLBrowserTestCase, self).setUp()
        fact = {
            "id":1,
            "amount":100,
            "discount":20,
            "fact_detail1":"foo",
            "fact_detail2":"bar",
            "flag":1,
            "date_id":20120308,
            "product_id":1,
            "category_id":10
        }

        date = {
            "id": 20120308,
            "day": 8,
            "month": 3,
            "month_name": "March",
            "month_sname": "Mar",
            "year": 2012
        }

        product = {
            "id": 1,
            "category_id": 10,
            "product_name": "Cool Thing"
        }

        category = {
            "id": 10,
            "category_id": 10,
            "category_name_en": "Things",
            "category_name_sk": "Veci",
            "subcategory_id": 20,
            "subcategory_name_en": "Cool Things",
            "subcategory_name_sk": "Super Veci"
        }

        ftable = self.table("sales")
        self.engine.execute(ftable.insert(), fact)
        table = self.table("dim_date")
        self.engine.execute(table.insert(), date)
        ptable = self.table("dim_product")
        self.engine.execute(ptable.insert(), product)
        table = self.table("dim_category")
        self.engine.execute(table.insert(), category)

        for i in range(1, 10):
            record = dict(product)
            record["id"] = product["id"] + i
            record["product_name"] = product["product_name"] + str(i)
            self.engine.execute(ptable.insert(), record)

        for j in range(1, 10):
            for i in range(1, 10):
                record = dict(fact)
                record["id"] = fact["id"] + i + j *10
                record["product_id"] = fact["product_id"] + i
                self.engine.execute(ftable.insert(), record)

    def table(self, name):
        return sqlalchemy.Table(name, self.metadata,
                                autoload=True)

    def test_get_fact(self):
        """Get single fact"""
        self.assertEqual(True, self.mapper.simplify_dimension_references)
        fact = self.browser.fact(1)
        self.assertIsNotNone(fact)

        self.assertEqual(18, len(fact.keys()))
        self.assertEqual(len(self.browser.cube.all_attributes) + 1,
                         len(fact.keys()))

    def test_get_facts(self):
        """Get single fact"""
        # TODO: remove this when happy
        self.assertEqual(True, self.mapper.simplify_dimension_references)

        facts = list(self.browser.facts())

        result = self.engine.execute(self.table("sales").count())
        count = result.fetchone()[0]
        self.assertEqual(82, count)

        self.assertIsNotNone(facts)
        self.assertEqual(82, len(facts))

        self.assertEqual(18, len(facts[0]))
        self.assertEqual(len(self.browser.cube.all_attributes) + 1,
                         len(facts[0].keys()))

        attrs = ["date.year", "amount"]
        facts = list(self.browser.facts(fields=attrs))
        self.assertEqual(82, len(facts))

        # We get 3: fact key + 2
        self.assertEqual(3, len(facts[0]))

    def test_get_members(self):
        """Get dimension values"""
        members = list(self.browser.members(None,"product",1))
        self.assertIsNotNone(members)
        self.assertEqual(1, len(members))

        members = list(self.browser.members(None,"product",2))
        self.assertIsNotNone(members)
        self.assertEqual(1, len(members))

        members = list(self.browser.members(None,"product",3))
        self.assertIsNotNone(members)
        self.assertEqual(10, len(members))

    def test_cut_details(self):
        cut = PointCut("date", [2012])
        details = self.browser.cut_details(cut)
        self.assertEqual([{"date.year":2012, "_key":2012, "_label":2012}], details)

        cut = PointCut("date", [2013])
        details = self.browser.cut_details(cut)
        self.assertEqual(None, details)

        cut = PointCut("date", [2012,3])
        details = self.browser.cut_details(cut)
        self.assertEqual([{"date.year":2012, "_key":2012, "_label":2012},
                          {"date.month_name":"March",
                          "date.month_sname":"Mar",
                          "date.month":3,
                          "_key":3, "_label":"March"}], details)

    @unittest.skip("test model is not suitable")
    def test_cell_details(self):
        cell = Cell(self.cube, [PointCut("date", [2012])])
        details = self.browser.cell_details(cell)
        self.assertEqual(1, len(details))

        cell = Cell(self.cube, [PointCut("product", [10])])
        details = self.browser.cell_details(cell)
        self.assertEqual(1, len(details))

    @unittest.skip("this needs to be tested on non-sqlite database")
    def test_issue_157(self):
        cut = PointCut("date", [2000])
        cell = Cell(self.cube, [cut])
        result = self.browser.aggregate(cell, drilldown=["product:category"])
        # import pdb; pdb.set_trace()

    def test_aggregate(self):
        result = self.browser.aggregate()
        keys = sorted(result.summary.keys())
        self.assertEqual(4, len(keys))
        self.assertEqual(["amount_min", "amount_sum", "discount_sum", "record_count"], keys)

        aggregates = ["amount_min", "amount_sum"]
        result = self.browser.aggregate(None, aggregates=aggregates)
        keys = sorted(result.summary.keys())
        self.assertEqual(2, len(keys))
        self.assertEqual(["amount_min", "amount_sum"], keys)

        result = self.browser.aggregate(None, aggregates=["discount_sum"])
        keys = sorted(result.summary.keys())
        self.assertEqual(1, len(keys))
        self.assertEqual(["discount_sum"], keys)


class HierarchyTestCase(CubesTestCaseBase):
    def setUp(self):
        super(HierarchyTestCase, self).setUp()

        engine = create_engine("sqlite:///")
        metadata = MetaData(bind=engine)
        d_table = Table("dim_date", metadata,
                        Column('id', Integer, primary_key=True),
                        Column('year', Integer),
                        Column('quarter', Integer),
                        Column('month', Integer),
                        Column('week', Integer),
                        Column('day', Integer))

        f_table = Table("ft_cube", metadata,
                        Column('id', Integer, primary_key=True),
                        Column('date_id', Integer))
        metadata.create_all()

        start_date = datetime.date(2000, 1, 1)
        end_date = datetime.date(2001, 1,1)
        delta = datetime.timedelta(1)
        date = start_date

        d_insert = d_table.insert()
        f_insert = f_table.insert()

        i = 1
        while date < end_date:
            record = {
                        "id": int(date.strftime('%Y%m%d')),
                        "year": date.year,
                        "quarter": (date.month-1)//3+1,
                        "month": date.month,
                        "week": int(date.strftime("%U")),
                        "day": date.day
                    }

            engine.execute(d_insert.values(record))

            # For each date insert one fact record
            record = {"id": i,
                      "date_id": record["id"]
                      }
            engine.execute(f_insert.values(record))
            date = date + delta
            i += 1

        workspace = self.create_workspace({"engine": engine},
                                          "hierarchy.json")
        self.cube = workspace.cube("cube")
        self.browser = SnowflakeBrowser(self.cube,
                                        store=workspace.get_store("default"),
                                        dimension_prefix="dim_",
                                        fact_prefix="ft_")
        self.browser.debug = True

    def test_cell(self):
        cell = Cell(self.cube)
        result = self.browser.aggregate(cell)
        self.assertEqual(366, result.summary["fact_count"])

        cut = PointCut("date", [2000, 2])
        cell = Cell(self.cube, [cut])
        result = self.browser.aggregate(cell)
        self.assertEqual(29, result.summary["fact_count"])

        cut = PointCut("date", [2000, 2], hierarchy="ywd")
        cell = Cell(self.cube, [cut])
        result = self.browser.aggregate(cell)
        self.assertEqual(7, result.summary["fact_count"])

        cut = PointCut("date", [2000, 1], hierarchy="yqmd")
        cell = Cell(self.cube, [cut])
        result = self.browser.aggregate(cell)
        self.assertEqual(91, result.summary["fact_count"])

    def test_drilldown(self):
        cell = Cell(self.cube)
        result = self.browser.aggregate(cell, drilldown=["date"])
        self.assertEqual(1, result.total_cell_count)

        result = self.browser.aggregate(cell, drilldown=["date:month"])
        self.assertEqual(12, result.total_cell_count)

        result = self.browser.aggregate(cell,
                                        drilldown=[("date", None, "month")])
        self.assertEqual(12, result.total_cell_count)

        result = self.browser.aggregate(cell,
                                        drilldown=[("date", None, "day")])
        self.assertEqual(366, result.total_cell_count)

        # Test year-quarter-month-day
        hier = self.cube.dimension("date").hierarchy("yqmd")
        result = self.browser.aggregate(cell,
                                        drilldown=[("date", "yqmd", "day")])
        self.assertEqual(366, result.total_cell_count)

        result = self.browser.aggregate(cell,
                                        drilldown=[("date", "yqmd", "quarter")])
        self.assertEqual(4, result.total_cell_count)

    def test_range_drilldown(self):
        cut = RangeCut("date", [2000, 1], [2000,3])
        cell = Cell(self.cube, [cut])
        result = self.browser.aggregate(cell, drilldown=["date"])
        # This should test that it does not drilldown on range
        self.assertEqual(1, result.total_cell_count)

    def test_implicit_level(self):
        cut = PointCut("date", [2000])
        cell = Cell(self.cube, [cut])

        result = self.browser.aggregate(cell, drilldown=["date"])
        self.assertEqual(12, result.total_cell_count)
        result = self.browser.aggregate(cell, drilldown=["date:month"])
        self.assertEqual(12, result.total_cell_count)

        result = self.browser.aggregate(cell,
                                        drilldown=[("date", None, "month")])
        self.assertEqual(12, result.total_cell_count)

        result = self.browser.aggregate(cell,
                                        drilldown=[("date", None, "day")])
        self.assertEqual(366, result.total_cell_count)

    def test_hierarchy_compatibility(self):
        cut = PointCut("date", [2000])
        cell = Cell(self.cube, [cut])

        with self.assertRaises(HierarchyError):
            self.browser.aggregate(cell, drilldown=[("date", "yqmd", None)])

        cut = PointCut("date", [2000], hierarchy="yqmd")
        cell = Cell(self.cube, [cut])
        result = self.browser.aggregate(cell,
                                        drilldown=[("date", "yqmd", None)])

        self.assertEqual(4, result.total_cell_count)

        cut = PointCut("date", [2000], hierarchy="yqmd")
        cell = Cell(self.cube, [cut])
        self.assertRaises(HierarchyError, self.browser.aggregate,
                            cell, drilldown=[("date", "ywd", None)])

        cut = PointCut("date", [2000], hierarchy="ywd")
        cell = Cell(self.cube, [cut])
        result = self.browser.aggregate(cell,
                                        drilldown=[("date", "ywd", None)])

        self.assertEqual(54, result.total_cell_count)



class SQLBrowserTestCase(CubesTestCaseBase):
    sql_engine = "sqlite:///"

    def setUp(self):
        model = {
            "cubes": [
                {
                    "name": "facts",
                    "dimensions": ["date", "country"],
                    "measures": ["amount"]

                }
            ],
            "dimensions": [
                {
                    "name": "date",
                    "levels": ["year", "month", "day"]
                },
                {
                    "name": "country",
                },
            ],
            "mappings": {
                "date.year": "year",
                "date.month": "month",
                "date.day": "day"
            }
        }

        super(SQLBrowserTestCase, self).setUp()
        self.facts = Table("facts", self.metadata,
                        Column("id", Integer),
                        Column("year", Integer),
                        Column("month", Integer),
                        Column("day", Integer),
                        Column("country", String),
                        Column("amount", Integer)
                        )

        self.metadata.create_all()
        data = [
                ( 1,2012,1,1,"sk",10),
                ( 2,2012,1,2,"sk",10),
                ( 3,2012,2,3,"sk",10),
                ( 4,2012,2,4,"at",10),
                ( 5,2012,3,5,"at",10),
                ( 6,2012,3,1,"uk",100),
                ( 7,2012,4,2,"uk",100),
                ( 8,2012,4,3,"uk",100),
                ( 9,2012,5,4,"uk",100),
                (10,2012,5,5,"uk",100),
                (11,2013,1,1,"fr",1000),
                (12,2013,1,2,"fr",1000),
                (13,2013,2,3,"fr",1000),
                (14,2013,2,4,"fr",1000),
                (15,2013,3,5,"fr",1000)
            ]
        self.load_data(self.facts, data)

        workspace = self.create_workspace(model=model)
        self.browser = workspace.browser("facts")
        self.cube = self.browser.cube

    def test_aggregate_empty_cell(self):
        result = self.browser.aggregate()
        self.assertIsNotNone(result.summary)
        self.assertEqual(1, len(result.summary.keys()))
        self.assertEqual("amount_sum", result.summary.keys()[0])
        self.assertEqual(5550, result.summary["amount_sum"])

    def test_aggregate_condition(self):
        cut = PointCut("date", [2012])
        cell = Cell(self.cube, [cut])
        result = self.browser.aggregate(cell)

        self.assertIsNotNone(result.summary)
        self.assertEqual(1, len(result.summary.keys()))
        self.assertEqual("amount_sum", result.summary.keys()[0])
        self.assertEqual(550, result.summary["amount_sum"])

        cells = list(result.cells)
        self.assertEqual(0, len(cells))

    def test_aggregate_drilldown(self):
        drilldown = [("date", None, "year")]
        result = self.browser.aggregate(drilldown=drilldown)
        cells = list(result.cells)

        self.assertEqual(2, len(cells))

        self.assertItemsEqual(["date.year", "amount_sum"],
                              cells[0].keys())
        self.assertEqual(550, cells[0]["amount_sum"])
        self.assertEqual(2012, cells[0]["date.year"])
        self.assertEqual(5000, cells[1]["amount_sum"])
        self.assertEqual(2013, cells[1]["date.year"])

    def test_aggregate_drilldown_order(self):
        drilldown = [("country", None, "country")]
        result = self.browser.aggregate(drilldown=drilldown)

        cells = list(result.cells)
        self.assertEqual(4, len(cells))

        self.assertItemsEqual(["country", "amount_sum"],
                              cells[0].keys())
        values = [cell["country"] for cell in cells]
        self.assertSequenceEqual(["at", "fr", "sk", "uk"], values)

        order = [("country", "desc")]
        result = self.browser.aggregate(drilldown=drilldown, order=order)
        cells = list(result.cells)
        values = [cell["country"] for cell in cells]
        self.assertSequenceEqual(["uk", "sk", "fr", "at"], values)

    # test_drilldown_pagination
    # test_split
    # test_drilldown_selected_attributes
    # drilldown high cardinality
    # Test:

########NEW FILE########
__FILENAME__ = joins
# -*- coding=utf -*-
import unittest
from sqlalchemy import create_engine, MetaData, Table, Integer, String, Column
from cubes import *
from ...common import CubesTestCaseBase

from json import dumps

def printable(obj):
    return dumps(obj, indent=4)

class JoinsTestCaseBase(CubesTestCaseBase):
    sql_engine = "sqlite:///"

    def setUp(self):
        super(JoinsTestCaseBase, self).setUp()

        self.facts = Table("facts", self.metadata,
                        Column("id", Integer),
                        Column("id_date", Integer),
                        Column("id_city", Integer),
                        Column("amount", Integer)
                        )
        self.dim_date = Table("dim_date", self.metadata,
                        Column("id", Integer),
                        Column("year", Integer),
                        Column("month", Integer),
                        Column("day", Integer)
                        )
        self.dim_city = Table("dim_city", self.metadata,
                        Column("id", Integer),
                        Column("name", Integer),
                        Column("country_code", Integer)
                        )
        self.dim_country = Table("dim_country", self.metadata,
                        Column("code", String),
                        Column("name", Integer)
                        )
        self.metadata.create_all()

        data = [
                    # Master-detail Match
                    ( 1, 20130901, 1,   20),
                    ( 2, 20130902, 1,   20),
                    ( 3, 20130903, 1,   20),
                    ( 4, 20130910, 1,   20),
                    ( 5, 20130915, 1,   20),
                    #             --------
                    #             ∑    100
                    # No city dimension
                    ( 6, 20131001, 9,  200),
                    ( 7, 20131002, 9,  200),
                    ( 8, 20131004, 9,  200),
                    ( 9, 20131101, 7,  200),
                    (10, 20131201, 7,  200),
                    #             --------
                    #             ∑   1000
                    #             ========
                    #             ∑   1100

                ]

        self.load_data(self.facts, data)

        data = [
                    (1, "Bratislava", "sk"),
                    (2, "New York", "us")
                ]

        self.load_data(self.dim_city, data)

        data = [
                    ("sk", "Slovakia"),
                    ("us", "United States")
                ]

        self.load_data(self.dim_country, data)

        data = []
        for day in range(1, 31):
            row = (20130900+day, 2013, 9, day)
            data.append(row)

        self.load_data(self.dim_date, data)

        self.workspace = Workspace()
        self.workspace.register_default_store("sql", engine=self.engine,
                dimension_prefix="dim_")

        self.workspace.add_model(self.model_path("joins.json"))
        self.cube = self.workspace.cube("facts")


class JoinsTestCase(JoinsTestCaseBase):
    def setUp(self):
        super(JoinsTestCase, self).setUp()

        self.day_drilldown = [("date", "default", "day")]
        self.month_drilldown = [("date", "default", "month")]
        self.year_drilldown = [("date", "default", "year")]
        self.city_drilldown = [("city")]

    def test_empty(self):
        browser = self.workspace.browser("facts")
        result = browser.aggregate()

        self.assertEqual(1100, result.summary["amount_sum"])

    def aggregate_summary(self, cube, *args, **kwargs):
        browser = self.workspace.browser(cube)
        result = browser.aggregate(*args, **kwargs)
        return result.summary

    def aggregate_cells(self, cube, *args, **kwargs):
        browser = self.workspace.browser(cube)
        result = browser.aggregate(*args, **kwargs)
        return list(result.cells)

    def test_cell_count_match(self):
        cells = self.aggregate_cells("facts", drilldown=self.city_drilldown)

        self.assertEqual(1, len(cells))
        self.assertEqual(100, cells[0]["amount_sum"])
        self.assertEqual("Bratislava", cells[0]["city.name"])

    def test_cell_count_master(self):
        cells = self.aggregate_cells("facts_master", drilldown=self.city_drilldown)
        summary = self.aggregate_summary("facts_master", drilldown=self.city_drilldown)
        self.assertEqual(1100, summary["amount_sum"])

        cells = self.aggregate_cells("facts_master", drilldown=self.city_drilldown)

        self.assertEqual(2, len(cells))

        names = [cell["city.name"] for cell in cells]
        self.assertSequenceEqual([None, "Bratislava"], names)

        amounts = [cell["amount_sum"] for cell in cells]
        self.assertSequenceEqual([1000, 100], amounts)

    def test_cell_count_detail(self):
        summary = self.aggregate_summary("facts_detail_city",
                                         drilldown=self.city_drilldown)
        self.assertEqual(100, summary["amount_sum"])

        cells = self.aggregate_cells("facts_detail_city", drilldown=self.city_drilldown)

        self.assertEqual(2, len(cells))

        names = [cell["city.name"] for cell in cells]
        self.assertSequenceEqual(["Bratislava", "New York"], names)

        amounts = [cell["amount_sum"] for cell in cells]
        self.assertSequenceEqual([100, 0], amounts)

    def test_cell_count_detail_not_found(self):
        cube = self.workspace.cube("facts_detail_city")
        cell = Cell(cube, [PointCut("city", [2])])
        browser = self.workspace.browser(cube)
        result = browser.aggregate(cell, drilldown=[("city", None, "city")])
        cells = list(result.cells)

        # We have one cell – one city from dim (nothing from facts)
        self.assertEqual(1, len(cells))
        # ... however, we have no facts with that city. 
        self.assertEqual(0, result.summary["record_count"])
        # The summary should be coalesced to zero
        self.assertEqual(0, result.summary["amount_sum"])

        names = [cell["city.name"] for cell in cells]
        self.assertSequenceEqual(["New York"], names)

    def test_three_tables(self):
        summary = self.aggregate_summary("threetables",
                                         drilldown=self.city_drilldown)
        self.assertEqual(100, summary["amount_sum"])

        drilldown = self.city_drilldown+self.year_drilldown
        cells = self.aggregate_cells("threetables", drilldown=drilldown)
        self.assertEqual(1, len(cells))

    def test_condition_and_drilldown(self):
        cube = self.workspace.cube("condition_and_drilldown")
        cell = Cell(cube, [PointCut("city", [2])])
        dd = [("date", None, "day")]
        cells = self.aggregate_cells("condition_and_drilldown", cell=cell,
                                     drilldown=dd)

        # We want every day from the date table
        self.assertEqual(30, len(cells))

        self.assertIn("record_count", cells[0])
        self.assertIn("amount_sum", cells[0])
        self.assertIn("date.year", cells[0])
        self.assertIn("date.month", cells[0])
        self.assertIn("date.day", cells[0])
        self.assertNotIn("city.id", cells[0])

    def test_split(self):
        cube = self.workspace.cube("condition_and_drilldown")
        split = Cell(cube, [RangeCut("date", [2013, 9, 1],
                                             [2013, 9, 3])])
        cells = self.aggregate_cells("condition_and_drilldown",
                                     split=split)

        # We want every day from the date table
        self.assertEqual(2, len(cells))
        self.assertIn(SPLIT_DIMENSION_NAME, cells[0])

        # Both: master and detail split

        cube = self.workspace.cube("condition_and_drilldown")
        split = Cell(cube, [
                            RangeCut("date", [2013, 9, 1],
                                             [2013, 9, 3]),
                            PointCut("city", [1])
                           ])
        cells = self.aggregate_cells("condition_and_drilldown",
                                     split=split)

        # We want every day from the date table
        self.assertEqual(2, len(cells))
        self.assertIn(SPLIT_DIMENSION_NAME, cells[0])

@unittest.skip("not yet")
class JoinAggregateCompositionTestCase(JoinsTestCaseBase):
    def setUp(self):
        super(JoinAggregateCompositionTestCase, self).setUp()

        self.cube = self.workspace.cube("matchdetail")

        MD = [("date_master", "default", "day")]
        DD = [("date_detail", "default", "day")]

        MC = Cell(self.cube, [PointCut("city_master", [2])])
        DC = Cell(self.cube, [PointCut("city_detail", [2])])

        cases = [
            {
                "args": (None, None, None, None),
                "cells": 0
            },
            {
                "args": (  MD, None, None, None),
                "cells": 5
            },
            {
                "args": (None,   MC, None, None),
                "cells": 0
            },
            {
                "args": (  MD,   MC, None, None),
                "cells": 0
            },
            {
                "args": (None, None,   DD, None),
                "cells": 0
            },
            {
                "args": (  MD, None,   DD, None),
                "cells": 0
            },
            {
                "args": (None,   MC,   DD, None),
                "cells": 0
            },
            {
                "args": (  MD,   MC,   DD, None),
                "cells": 0
            },
            {
                "args": (None, None, None,   DC),
                "cells": 0
            },
            {
                "args": (  MD, None, None,   DC),
                "cells": 0
            },
            {
                "args": (None,   MC, None,   DC),
                "cells": 0
            },
            {
                "args": (  MD,   MC, None,   DC),
                "cells": 0
            },
            {
                "args": (None, None,   DD,   DC),
                "cells": 0
            },
            {
                "args": (  MD, None,   DD,   DC),
                "cells": 0
            },
            {
                "args": (None,   MC,   DD,   DC),
                "cells": 0
            },
            {
                "args": (  MD,   MC,   DD,   DC),
                "cells": 0
            }
        ]


    def test_all(self):
        pass

########NEW FILE########
__FILENAME__ = browser
import unittest

from cubes.browser import *
from cubes.errors import *

from common import CubesTestCaseBase


class CutsTestCase(CubesTestCaseBase):
    def setUp(self):
        super(CutsTestCase, self).setUp()

        self.workspace = self.create_workspace(model="browser_test.json")
        self.cube = self.workspace.cube("transactions")
        self.dim_date = self.cube.dimension("date")

    def test_cut_depth(self):
        dim = self.cube.dimension("date")
        self.assertEqual(1, PointCut(dim, [1]).level_depth())
        self.assertEqual(3, PointCut(dim, [1, 1, 1]).level_depth())
        self.assertEqual(1, RangeCut(dim, [1], [1]).level_depth())
        self.assertEqual(3, RangeCut(dim, [1, 1, 1], [1]).level_depth())
        self.assertEqual(1, SetCut(dim, [[1], [1]]).level_depth())
        self.assertEqual(3, SetCut(dim, [[1], [1], [1, 1, 1]]).level_depth())

    def test_cut_from_dict(self):
        # d = {"type":"point", "path":[2010]}
        # self.assertRaises(Exception, cubes.cut_from_dict, d)

        d = {"type": "point", "path": [2010], "dimension": "date",
             "level_depth": 1, "hierarchy": None, "invert": False,
             "hidden": False}

        cut = cut_from_dict(d)
        tcut = PointCut("date", [2010])
        self.assertEqual(tcut, cut)
        self.assertEqual(dict(d), tcut.to_dict())
        self._assert_invert(d, cut, tcut)

        d = {"type": "range", "from": [2010], "to": [2012, 10], "dimension":
             "date", "level_depth": 2, "hierarchy": None, "invert": False,
             "hidden": False}
        cut = cut_from_dict(d)
        tcut = RangeCut("date", [2010], [2012, 10])
        self.assertEqual(tcut, cut)
        self.assertEqual(dict(d), tcut.to_dict())
        self._assert_invert(d, cut, tcut)

        d = {"type": "set", "paths": [[2010], [2012, 10]], "dimension": "date",
             "level_depth": 2, "hierarchy": None, "invert": False,
             "hidden": False}
        cut = cut_from_dict(d)
        tcut = SetCut("date", [[2010], [2012, 10]])
        self.assertEqual(tcut, cut)
        self.assertEqual(dict(d), tcut.to_dict())
        self._assert_invert(d, cut, tcut)

        self.assertRaises(ArgumentError, cut_from_dict, {"type": "xxx"})

    def _assert_invert(self, d, cut, tcut):
        cut.invert = True
        tcut.invert = True
        d["invert"] = True
        self.assertEqual(tcut, cut)
        self.assertEqual(dict(d), tcut.to_dict())


class StringConversionsTestCase(unittest.TestCase):
    def test_cut_string_conversions(self):
        cut = PointCut("foo", ["10"])
        self.assertEqual("foo:10", str(cut))
        self.assertEqual(cut, cut_from_string("foo:10"))

        cut = PointCut("foo", ["123_abc_", "10", "_"])
        self.assertEqual("foo:123_abc_,10,_", str(cut))
        self.assertEqual(cut, cut_from_string("foo:123_abc_,10,_"))

        cut = PointCut("foo", ["123_ abc_"])
        self.assertEqual(r"foo:123_ abc_", str(cut))
        self.assertEqual(cut, cut_from_string("foo:123_ abc_"))

        cut = PointCut("foo", ["a-b"])
        self.assertEqual("foo:a\-b", str(cut))
        self.assertEqual(cut, cut_from_string("foo:a\-b"))

        cut = PointCut("foo", ["a+b"])
        self.assertEqual("foo:a+b", str(cut))
        self.assertEqual(cut, cut_from_string("foo:a+b"))

    def test_special_characters(self):
        self.assertEqual('\\:q\\-we,a\\\\sd\\;,100',
                         string_from_path([":q-we", "a\\sd;", 100]))

    def test_string_from_path(self):
        self.assertEqual('qwe,asd,100',
                         string_from_path(["qwe", "asd", 100]))
        self.assertEqual('', string_from_path([]))
        self.assertEqual('', string_from_path(None))

    def test_path_from_string(self):
        self.assertEqual(["qwe", "asd", "100"],
                         path_from_string('qwe,asd,100'))
        self.assertEqual([], path_from_string(''))
        self.assertEqual([], path_from_string(None))

    def test_set_cut_string(self):

        cut = SetCut("foo", [["1"], ["2", "3"], ["qwe", "asd", "100"]])
        self.assertEqual("foo:1;2,3;qwe,asd,100", str(cut))
        self.assertEqual(cut, cut_from_string("foo:1;2,3;qwe,asd,100"))

        # single-element SetCuts cannot go round trip, they become point cuts
        cut = SetCut("foo", [["a+b"]])
        self.assertEqual("foo:a+b", str(cut))
        self.assertEqual(PointCut("foo", ["a+b"]), cut_from_string("foo:a+b"))

        cut = SetCut("foo", [["a-b"]])
        self.assertEqual("foo:a\-b", str(cut))
        self.assertEqual(PointCut("foo", ["a-b"]), cut_from_string("foo:a\-b"))

    def test_range_cut_string(self):
        cut = RangeCut("date", ["2010"], ["2011"])
        self.assertEqual("date:2010-2011", str(cut))
        self.assertEqual(cut, cut_from_string("date:2010-2011"))

        cut = RangeCut("date", ["2010"], None)
        self.assertEqual("date:2010-", str(cut))
        cut = cut_from_string("date:2010-")
        if cut.to_path:
            self.fail('there should be no to path, is: %s' % (cut.to_path, ))

        cut = RangeCut("date", None, ["2010"])
        self.assertEqual("date:-2010", str(cut))
        cut = cut_from_string("date:-2010")
        if cut.from_path:
            self.fail('there should be no from path is: %s' % (cut.from_path, ))

        cut = RangeCut("date", ["2010", "11", "12"], ["2011", "2", "3"])
        self.assertEqual("date:2010,11,12-2011,2,3", str(cut))
        self.assertEqual(cut, cut_from_string("date:2010,11,12-2011,2,3"))

        cut = RangeCut("foo", ["a+b"], ["1"])
        self.assertEqual("foo:a+b-1", str(cut))
        self.assertEqual(cut, cut_from_string("foo:a+b-1"))

        cut = RangeCut("foo", ["a-b"], ["1"])
        self.assertEqual(r"foo:a\-b-1", str(cut))
        self.assertEqual(cut, cut_from_string(r"foo:a\-b-1"))

    def test_hierarchy_cut(self):
        cut = PointCut("date", ["10"], "dqmy")
        self.assertEqual("date@dqmy:10", str(cut))
        self.assertEqual(cut, cut_from_string("date@dqmy:10"))


class BrowserTestCase(CubesTestCaseBase):
    def setUp(self):
        super(BrowserTestCase, self).setUp()

        self.workspace = self.create_workspace(model="model.json")
        self.cube = self.workspace.cube("contracts")


class AggregationBrowserTestCase(BrowserTestCase):
    def setUp(self):
        super(AggregationBrowserTestCase, self).setUp()
        self.browser = AggregationBrowser(self.cube)

    def test_cutting(self):
        full_cube = Cell(self.cube)
        self.assertEqual(self.cube, full_cube.cube)
        self.assertEqual(0, len(full_cube.cuts))

        cell = full_cube.slice(PointCut("date", [2010]))
        self.assertEqual(1, len(cell.cuts))

        cell = cell.slice(PointCut("supplier", [1234]))
        cell = cell.slice(PointCut("cpv", [50, 20]))
        self.assertEqual(3, len(cell.cuts))
        self.assertEqual(self.cube, cell.cube)

        # Adding existing slice should result in changing the slice properties
        cell = cell.slice(PointCut("date", [2011]))
        self.assertEqual(3, len(cell.cuts))

    def test_multi_slice(self):
        full_cube = Cell(self.cube)

        cuts_list = (
            PointCut("date", [2010]),
            PointCut("cpv", [50, 20]),
            PointCut("supplier", [1234]))

        cell_list = full_cube.multi_slice(cuts_list)
        self.assertEqual(3, len(cell_list.cuts))

        self.assertRaises(CubesError, full_cube.multi_slice, {})

    def test_get_cell_dimension_cut(self):
        full_cube = Cell(self.cube)
        cell = full_cube.slice(PointCut("date", [2010]))
        cell = cell.slice(PointCut("supplier", [1234]))

        cut = cell.cut_for_dimension("date")
        self.assertEqual(str(cut.dimension), "date")

        self.assertRaises(NoSuchDimensionError, cell.cut_for_dimension, "someunknown")

        cut = cell.cut_for_dimension("cpv")
        self.assertEqual(cut, None)

    def test_hierarchy_path(self):
        dim = self.cube.dimension("cpv")
        hier = dim.hierarchy()

        levels = hier.levels_for_path([])
        self.assertEqual(len(levels), 0)
        levels = hier.levels_for_path(None)
        self.assertEqual(len(levels), 0)

        levels = hier.levels_for_path([1, 2, 3, 4])
        self.assertEqual(len(levels), 4)
        names = [level.name for level in levels]
        self.assertEqual(names, ['division', 'group', 'class', 'category'])

        self.assertRaises(HierarchyError, hier.levels_for_path,
                          [1, 2, 3, 4, 5, 6, 7, 8])

    def test_hierarchy_drilldown_levels(self):
        dim = self.cube.dimension("cpv")
        hier = dim.hierarchy()

        levels = hier.levels_for_path([], drilldown=True)
        self.assertEqual(len(levels), 1)
        self.assertEqual(levels[0].name, 'division')
        levels = hier.levels_for_path(None, drilldown=True)
        self.assertEqual(len(levels), 1)
        self.assertEqual(levels[0].name, 'division')

    def test_slice_drilldown(self):
        cut = PointCut("date", [])
        original_cell = Cell(self.cube, [cut])

        cell = original_cell.drilldown("date", 2010)
        self.assertEqual([2010], cell.cut_for_dimension("date").path)

        cell = cell.drilldown("date", 1)
        self.assertEqual([2010, 1], cell.cut_for_dimension("date").path)

        cell = cell.drilldown("date", 2)
        self.assertEqual([2010, 1, 2], cell.cut_for_dimension("date").path)


def test_suite():
    suite = unittest.TestSuite()

    suite.addTest(unittest.makeSuite(AggregationBrowserTestCase))
    suite.addTest(unittest.makeSuite(CellsAndCutsTestCase))

    return suite

########NEW FILE########
__FILENAME__ = combinations
import unittest
import cubes
import os

from common import DATA_PATH

@unittest.skip        
class CombinationsTestCase(unittest.TestCase):
	
    def setUp(self):
        self.nodea = ('a', (1,2,3))
        self.nodeb = ('b', (99,88))
        self.nodec = ('c',('x','y'))
        self.noded = ('d', ('m'))

    def test_levels(self):
        combos = cubes.common.combine_nodes([self.nodea])
        self.assertEqual(len(combos), 3)

        combos = cubes.common.combine_nodes([self.nodeb])
        self.assertEqual(len(combos), 2)

        combos = cubes.common.combine_nodes([self.noded])
        self.assertEqual(len(combos), 1)

    def test_combos(self):
        combos = cubes.common.combine_nodes([self.nodea, self.nodeb])
        self.assertEqual(len(combos), 11)

        combos = cubes.common.combine_nodes([self.nodea, self.nodeb, self.nodec])
        self.assertEqual(len(combos), 35)
	
    def test_required_one(self):
        nodes = [self.nodea, self.nodeb, self.nodec]
        required = [self.nodea]
        combos = cubes.common.combine_nodes(nodes, required)
        self.assertEqual(len(combos), 27)
        for combo in combos:
            flag = False
            for item in combo:
                if tuple(item[0]) == self.nodea:
                    flag = True
                    break
            self.assertTrue(flag, "All combinations should contain required node")

    def test_required_more(self):
        nodes = [self.nodea, self.nodeb, self.nodec, self.noded]
        required = [self.nodea, self.nodeb]
        combos = cubes.common.combine_nodes(nodes, required)
        self.assertEqual(len(combos), 36)
        for combo in combos:
            flag = False
            for item in combo:
                if tuple(item[0]) == self.nodea or tuple(item[0]) == self.nodeb:
                    flag = True
                    break
            self.assertTrue(flag, "All combinations should contain both required nodes")

@unittest.skip        
class CuboidsTestCase(unittest.TestCase):
    def setUp(self):
        self.model_path = os.path.join(DATA_PATH, 'model.json')
        self.model = cubes.model_from_path(self.model_path)
        self.cube = self.model.cubes.get("contracts")

    def test_combine_dimensions(self):
        dims = self.cube.dimensions
        results = cubes.common.all_cuboids(dims)
        # for r in results:
        #     print "=== COMBO:"
        #     for c in r:
        #         print "---     %s: %s" % (c[0][0].name, c[1])

        self.assertEqual(len(results), 863)

        dim = self.cube.dimension("date")
        results = cubes.common.all_cuboids(dims, [dim])
        self.assertEqual(len(results), 648)

    def test_should_not_accept_unknown_dimension(self):
        foo_desc = { "name": "foo", "levels": {"level": {"key": "boo"}}}
        foo_dim = cubes.create_dimension(foo_desc)

        self.assertRaises(AttributeError, cubes.common.all_cuboids,
                                          self.cube.dimensions, [foo_dim])

def test_suite():
    suite = unittest.TestSuite()

    suite.addTest(unittest.makeSuite(CombinationsTestCase))
    suite.addTest(unittest.makeSuite(CuboidsTestCase))

    return suite


########NEW FILE########
__FILENAME__ = common
import os
import unittest
from cubes import Workspace
from sqlalchemy import create_engine, MetaData
import json

TESTS_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(TESTS_PATH, 'data')

class CubesTestCaseBase(unittest.TestCase):
    sql_engine = None

    def setUp(self):
        self._models_path = os.path.join(TESTS_PATH, 'models')
        self._data_path = os.path.join(TESTS_PATH, 'data')

        if self.sql_engine:
            self.engine = create_engine(self.sql_engine)
            self.metadata = MetaData(bind=self.engine)
        else:
            self.engine = None
            self.metadata = None


    def model_path(self, model):
        return os.path.join(self._models_path, model)

    def model_metadata(self, model):
        path = self.model_path(model)
        with open(path) as f:
            md = json.load(f)
        return md

    def data_path(self, file):
        return os.path.join(self._data_path, file)

    def create_workspace(self, store=None, model=None):
        """Create shared workspace. Add default store specified in `store` as
        a dictionary and `model` which can be a filename relative to
        ``tests/models`` or a moel dictionary. If no store is provided but
        class has an engine or `sql_engine` set, then the existing engine will
        be used as the default SQL store."""

        workspace = Workspace()

        if store:
            store = dict(store)
            store_type = store.pop("type", "sql")
            workspace.register_default_store(store_type, **store)
        elif self.engine:
            workspace.register_default_store("sql", engine=self.engine)

        if model:
            if isinstance(model, basestring):
                model = self.model_path(model)
            workspace.add_model(model)

        return workspace

    def load_data(self, table, data):
        self.engine.execute(table.delete())
        for row in data:
            insert = table.insert().values(row)
            self.engine.execute(insert)


########NEW FILE########
__FILENAME__ = mapper
import unittest
from cubes.backends.sql.mapper import SnowflakeMapper
from cubes.model import *
from .common import CubesTestCaseBase

class MapperTestCase(CubesTestCaseBase):
    def setUp(self):
        super(MapperTestCase, self).setUp()

        self.modelmd = self.model_metadata("mapper_test.json")
        self.workspace = self.create_workspace(model=self.modelmd)

        self.cube = self.workspace.cube("sales")
        self.mapper = SnowflakeMapper(self.cube, dimension_prefix='dim_', dimension_suffix="_dim")

        self.mapper.mappings = {
            "product.name": "product.product_name",
            "product.category": "product.category_id",
            "subcategory.name.en": "subcategory.subcategory_name_en",
            "subcategory.name.sk": "subcategory.subcategory_name_sk"
        }

    def test_logical_reference(self):

        dim = self.workspace.dimension("date")
        attr = Attribute("month", dimension=dim)
        self.assertEqual("date.month", self.mapper.logical(attr))

        attr = Attribute("month", dimension=dim)
        dim = self.workspace.dimension("product")
        attr = Attribute("category", dimension=dim)
        self.assertEqual("product.category", self.mapper.logical(attr))

        self.assertEqual(True, self.mapper.simplify_dimension_references)
        dim = self.workspace.dimension("flag")
        attr = Attribute("flag", dimension=dim)
        self.assertEqual("flag", self.mapper.logical(attr))

        attr = Attribute("measure", dimension=None)
        self.assertEqual("measure", self.mapper.logical(attr))

    def test_logical_reference_as_string(self):
        self.assertRaises(AttributeError, self.mapper.logical, "amount")

    def test_dont_simplify_dimension_references(self):
        self.mapper.simplify_dimension_references = False

        dim = self.workspace.dimension("flag")
        attr = Attribute("flag", dimension=dim)
        self.assertEqual("flag.flag", self.mapper.logical(attr))

        attr = Attribute("measure", dimension=None)
        self.assertEqual("measure", self.mapper.logical(attr))

    def test_logical_split(self):
        split = self.mapper.split_logical

        self.assertEqual(('foo', 'bar'), split('foo.bar'))
        self.assertEqual(('foo', 'bar.baz'), split('foo.bar.baz'))
        self.assertEqual((None, 'foo'), split('foo'))

    def assertMapping(self, expected, logical_ref, locale=None):
        """Create string reference by concatentanig table and column name.
        No schema is expected (is ignored)."""

        attr = self.mapper.attributes[logical_ref]
        ref = self.mapper.physical(attr, locale)
        sref = ref[1] + "." + ref[2]
        self.assertEqual(expected, sref)

    def test_physical_refs_dimensions(self):
        """Testing correct default mappings of dimensions (with and without
        explicit default prefix) in physical references."""

        # No dimension prefix
        self.mapper.dimension_prefix = ""
        self.mapper.dimension_suffix = ""
        self.assertMapping("date.year", "date.year")
        self.assertMapping("sales.flag", "flag")
        self.assertMapping("sales.amount", "amount")
        # self.assertEqual("fact.flag", sref("flag.flag"))

        # With prefix
        self.mapper.dimension_prefix = "dm_"
        self.assertMapping("dm_date.year", "date.year")
        self.assertMapping("dm_date.month_name", "date.month_name")
        self.assertMapping("sales.flag", "flag")
        self.assertMapping("sales.amount", "amount")
        self.mapper.dimension_prefix = ""
        self.mapper.dimension_suffix = ""

    def test_physical_refs_flat_dims(self):
        self.cube.fact = None
        self.assertMapping("sales.flag", "flag")

    def test_physical_refs_facts(self):
        """Testing correct mappings of fact attributes in physical references"""

        fact = self.cube.fact
        self.cube.fact = None
        self.assertMapping("sales.amount", "amount")
        # self.assertEqual("sales.flag", sref("flag.flag"))
        self.cube.fact = fact

    def test_physical_refs_with_mappings_and_locales(self):
        """Testing correct mappings of mapped attributes and localized
        attributes in physical references"""

        # Test defaults
        self.assertMapping("dim_date_dim.month_name", "date.month_name")
        self.assertMapping("dim_category_dim.category_name_en",
                           "product.category_name")
        self.assertMapping("dim_category_dim.category_name_sk",
                           "product.category_name", "sk")
        self.assertMapping("dim_category_dim.category_name_en",
                           "product.category_name", "de")

        # Test with mapping
        self.assertMapping("dim_product_dim.product_name", "product.name")
        self.assertMapping("dim_product_dim.category_id", "product.category")
        self.assertMapping("dim_product_dim.product_name", "product.name", "sk")
        self.assertMapping("dim_category_dim.subcategory_name_en",
                           "product.subcategory_name")
        self.assertMapping("dim_category_dim.subcategory_name_sk",
                           "product.subcategory_name", "sk")
        self.assertMapping("dim_category_dim.subcategory_name_en",
                           "product.subcategory_name", "de")


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MapperTestCase))

    return suite

########NEW FILE########
__FILENAME__ = model
import unittest
import os
import re
import cubes
from cubes.errors import *
from cubes.model import *
from cubes.providers import create_cube

import copy
from common import TESTS_PATH, CubesTestCaseBase

DIM_DATE_DESC = {
    "name": "date",
    "levels": [
        {"name": "year"},
        {"name": "month", "attributes": ["month", "month_name"]},
        {"name": "day"}
    ],
    "hierarchies": [
        {"name": "ymd", "levels": ["year", "month", "day"]},
        {"name": "ym", "levels": ["year", "month"]},
    ]
}

DIM_FLAG_DESC = {"name": "flag"}

DIM_PRODUCT_DESC = {
    "name": "product",
    "levels": [
        {"name": "category", "attributes": ["key", "name"]},
        {"name": "subcategory", "attributes": ["key", "name"]},
        {"name": "product", "attributes": ["key", "name", "description"]}
    ]
}


class ModelTestCaseBase(unittest.TestCase):
    def setUp(self):
        self.models_path = os.path.join(TESTS_PATH, 'models')

    def model_path(self, model):
        return os.path.join(self.models_path, model)


class AttributeTestCase(unittest.TestCase):
    """docstring for AttributeTestCase"""
    def test_basics(self):
        """Attribute creation and attribute references"""
        attr = cubes.Attribute("foo")
        self.assertEqual("foo", attr.name)
        self.assertEqual("foo", str(attr))
        self.assertEqual("foo", attr.ref())
        self.assertEqual("foo", attr.ref(simplify=False))
        self.assertEqual("foo", attr.ref(simplify=True))

    def test_locale(self):
        """References to localizable attributes"""

        attr = cubes.Attribute("foo")
        self.assertRaises(ArgumentError, attr.ref, locale="xx")

        attr = cubes.Attribute("foo", locales=["en", "sk"])
        self.assertEqual("foo", attr.name)
        self.assertEqual("foo", str(attr))
        self.assertEqual("foo", attr.ref())
        self.assertEqual("foo.en", attr.ref(locale="en"))
        self.assertEqual("foo.sk", attr.ref(locale="sk"))
        self.assertRaises(ArgumentError, attr.ref, locale="xx")

    def test_simplify(self):
        """Simplification of attribute reference (with and without details)"""

        level = cubes.Level("name", attributes=["name"])
        dim = cubes.Dimension("group", levels=[level])
        attr = dim.attribute("name")
        self.assertEqual("name", attr.name)
        self.assertEqual("name", str(attr))
        self.assertEqual("group", attr.ref())
        self.assertEqual("group.name", attr.ref(simplify=False))
        self.assertEqual("group", attr.ref(simplify=True))

        level = cubes.Level("name", attributes=["key", "name"])
        dim = cubes.Dimension("group", levels=[level])
        attr = dim.attribute("name")
        self.assertEqual("name", attr.name)
        self.assertEqual("name", str(attr))
        self.assertEqual("group.name", attr.ref())
        self.assertEqual("group.name", attr.ref(simplify=False))
        self.assertEqual("group.name", attr.ref(simplify=True))

    def test_create_attribute(self):
        """Coalesce attribute object (string or Attribute instance)"""

        level = cubes.Level("name", attributes=["key", "name"])
        dim = cubes.Dimension("group", levels=[level])

        obj = cubes.create_attribute("name")
        self.assertIsInstance(obj, cubes.Attribute)
        self.assertEqual("name", obj.name)

        obj = cubes.create_attribute({"name": "key"})
        obj.dimension = dim
        self.assertIsInstance(obj, cubes.Attribute)
        self.assertEqual("key", obj.name)
        self.assertEqual(dim, obj.dimension)

        attr = dim.attribute("key")
        obj = cubes.create_attribute(attr)
        obj.dimension = dim
        self.assertIsInstance(obj, cubes.Attribute)
        self.assertEqual("key", obj.name)
        self.assertEqual(obj, attr)

    def test_attribute_list(self):
        """Create attribute list from strings or Attribute instances"""
        self.assertEqual([], cubes.attribute_list([]))

        names = ["name", "key"]
        attrs = cubes.attribute_list(names)

        for name, attr in zip(names, attrs):
            self.assertIsInstance(attr, cubes.Attribute)
            self.assertEqual(name, attr.name)


class MeasuresTestsCase(CubesTestCaseBase):
    def setUp(self):
        super(MeasuresTestsCase, self).setUp()
        self.metadata = self.model_metadata("measures.json")

        self.cubes_md = {}

        for cube in self.metadata["cubes"]:
            self.cubes_md[cube["name"]] = cube

    def cube(self, name):
        """Create a cube object `name` from measures test model."""
        return create_cube(self.cubes_md[name])

    def test_basic(self):
        md = {}
        with self.assertRaises(ModelError):
            measure = create_measure(md)

        measure = create_measure("amount")
        self.assertIsInstance(measure, Measure)
        self.assertEqual("amount", measure.name)

        md = {"name": "amount"}
        measure = create_measure(md)
        self.assertEqual("amount", measure.name)

    def test_copy(self):
        md = {"name": "amount"}
        measure = create_measure(md)
        measure2 = copy.deepcopy(measure)
        self.assertEqual(measure, measure2)

    def test_aggregate(self):
        md = {}
        with self.assertRaises(ModelError):
            measure = create_measure_aggregate(md)

        measure = create_measure_aggregate("amount_sum")
        self.assertIsInstance(measure, MeasureAggregate)
        self.assertEqual("amount_sum", measure.name)

    def test_create_default_aggregates(self):
        measure = create_measure("amount")
        aggs = measure.default_aggregates()
        self.assertEqual(1, len(aggs))
        agg = aggs[0]
        self.assertEqual("amount_sum", agg.name)
        self.assertEqual("amount", agg.measure)
        self.assertEqual("sum", agg.function)
        self.assertIsNone(agg.formula)

        md = {"name": "amount", "aggregates": ["sum", "min"]}
        measure = create_measure(md)
        aggs = measure.default_aggregates()
        self.assertEqual(2, len(aggs))
        self.assertEqual("amount_sum", aggs[0].name)
        self.assertEqual("amount", aggs[0].measure)
        self.assertEqual("sum", aggs[0].function)
        self.assertIsNone(aggs[0].formula)

        self.assertEqual("amount_min", aggs[1].name)
        self.assertEqual("amount", aggs[1].measure)
        self.assertEqual("min", aggs[1].function)
        self.assertIsNone(aggs[1].formula)

    def test_fact_count(self):
        md = {"name": "count", "function": "count"}
        agg = create_measure_aggregate(md)

        self.assertEqual("count", agg.name)
        self.assertIsNone(agg.measure)
        self.assertEqual("count", agg.function)
        self.assertIsNone(agg.formula)

    def test_empty2(self):
        """No measures in metadata should yield count measure with record
        count"""
        cube = self.cube("empty")
        self.assertIsInstance(cube, Cube)
        self.assertEqual(0, len(cube.measures))
        self.assertEqual(1, len(cube.aggregates))

        aggregate = cube.aggregates[0]
        self.assertEqual("fact_count", aggregate.name)
        self.assertEqual("count", aggregate.function)
        self.assertIsNone(aggregate.measure)

    def test_amount_default(self):
        """Plain measure definition should yield measure_sum aggregate"""
        cube = self.cube("amount_default")
        measures = cube.measures
        self.assertEqual(1, len(measures))
        self.assertEqual("amount", measures[0].name)
        self.assertIsNone(measures[0].expression)

        aggregates = cube.aggregates
        self.assertEqual(1, len(aggregates))
        self.assertEqual("amount_sum", aggregates[0].name)
        self.assertEqual("amount", aggregates[0].measure)
        self.assertIsNone(aggregates[0].expression)

    def test_fact_count2(self):
        cube = self.cube("fact_count")
        measures = cube.measures
        self.assertEqual(0, len(measures))

        aggregates = cube.aggregates
        self.assertEqual(1, len(aggregates))
        self.assertEqual("total_events", aggregates[0].name)
        self.assertIsNone(aggregates[0].measure)
        self.assertIsNone(aggregates[0].expression)

    def test_amount_sum(self):
        cube = self.cube("amount_sum")
        measures = cube.measures
        self.assertEqual(1, len(measures))
        self.assertEqual("amount", measures[0].name)
        self.assertIsNone(measures[0].expression)

        aggregates = cube.aggregates
        self.assertEqual(1, len(aggregates))
        self.assertEqual("amount_sum", aggregates[0].name)
        self.assertEqual("sum", aggregates[0].function)
        self.assertEqual("amount", aggregates[0].measure)
        self.assertIsNone(aggregates[0].expression)

    def test_explicit_implicit_combined(self):
        # Test explicit aggregates
        #
        cube = self.cube("amount_sum_explicit")
        measures = cube.measures
        self.assertEqual(1, len(measures))
        self.assertEqual("amount", measures[0].name)
        self.assertIsNone(measures[0].expression)

        aggregates = cube.aggregates
        self.assertEqual(1, len(aggregates))
        self.assertEqual("total", aggregates[0].name)
        self.assertEqual("amount", aggregates[0].measure)
        self.assertIsNone(aggregates[0].expression)

        cube = self.cube("amount_sum_combined")
        measures = cube.measures
        self.assertEqual(1, len(measures))
        self.assertEqual("amount", measures[0].name)
        self.assertIsNone(measures[0].expression)

        aggregates = cube.aggregates
        self.assertEqual(3, len(aggregates))
        names = [a.name for a in aggregates]
        self.assertSequenceEqual(["total",
                                  "amount_min",
                                  "amount_max"], names)

    def test_backend_provided(self):
        cube = self.cube("backend_provided_aggregate")
        measures = cube.measures
        self.assertEqual(0, len(measures))

        aggregates = cube.aggregates
        self.assertEqual(1, len(aggregates))
        self.assertEqual("total", aggregates[0].name)
        self.assertIsNone(aggregates[0].measure)
        self.assertIsNone(aggregates[0].expression)

    def measure_expression(self):
        cube = self.cube("measure_expression")
        measures = cube.measures
        self.assertEqual(3, len(measures))

        self.assertEqual("price", measures[0].name)
        self.assertIsNone(measures[0].expression)
        self.assertEqual("costs", measures[1].name)
        self.assertIsNone(measures[2].expression)

        self.assertEqual("revenue", measures[2].name)
        self.assertEqual("price - costs", measures[2].expression)

        aggregates = cube.aggregates
        self.assertEqual(3, len(aggregates))
        self.assertEqual("price_sum", aggregates[0].name)
        self.assertEqual("price", aggregates[0].measure)
        self.assertEqual("costs_sum", aggregates[0].name)
        self.assertEqual("costs", aggregates[0].measure)
        self.assertEqual("revenue_sum", aggregates[0].name)
        self.assertEqual("revenue", aggregates[0].measure)

    # TODO: aggregate_expression, aggregate_expression_error
    # TODO: measure_expression, invalid_expression

    def test_implicit(self):
        # TODO: this should be in model.py tests
        cube = self.cube("default_aggregates")
        aggregates = [a.name for a in cube.aggregates]
        self.assertSequenceEqual(["amount_sum",
                                  "amount_min",
                                  "amount_max"
                                  ],
                                  aggregates)

    def test_explicit(self):
        cube = self.cube("explicit_aggregates")
        aggregates = [a.name for a in cube.aggregates]
        self.assertSequenceEqual(["amount_sum",
                                  "amount_wma",
                                  "count",
                                  ],
                                  aggregates)

    def test_explicit_conflict(self):
        with self.assertRaisesRegexp(ModelError, "function mismatch"):
            cube = self.cube("explicit_aggregates_conflict")


class LevelTestCase(unittest.TestCase):
    """docstring for LevelTestCase"""
    def test_initialization(self):
        """Empty attribute list for new level should raise an exception """
        self.assertRaises(ModelError, cubes.Level, "month", [])

    def test_has_details(self):
        """Level "has_details" flag"""
        attrs = cubes.attribute_list(["year"])
        level = cubes.Level("year", attrs)
        self.assertFalse(level.has_details)

        attrs = cubes.attribute_list(["month", "month_name"])
        level = cubes.Level("month", attrs)
        self.assertTrue(level.has_details)

    def test_operators(self):
        """Level to string conversion"""
        self.assertEqual("date", str(cubes.Level("date", ["foo"])))

    def test_create(self):
        """Create level from a dictionary"""
        desc = "year"
        level = cubes.create_level(desc)
        self.assertIsInstance(level, cubes.Level)
        self.assertEqual("year", level.name)
        self.assertEqual(["year"], [str(a) for a in level.attributes])

        # Test default: Attributes
        desc = {"name": "year"}
        level = cubes.create_level(desc)
        self.assertIsInstance(level, cubes.Level)
        self.assertEqual("year", level.name)
        self.assertEqual(["year"], [str(a) for a in level.attributes])

        # Test default: Attributes
        desc = {"name": "year", "attributes": ["key"]}
        level = cubes.create_level(desc)
        self.assertIsInstance(level, cubes.Level)
        self.assertEqual("year", level.name)
        self.assertEqual(["key"], [str(a) for a in level.attributes])
        self.assertFalse(level.has_details)

        desc = {"name": "year", "attributes": ["key", "label"]}
        level = cubes.create_level(desc)
        self.assertTrue(level.has_details)
        self.assertEqual(["key", "label"], [str(a) for a in level.attributes])

        # Level from description with full details
        desc = {
            "name": "month",
            "attributes": [
                {"name": "month"},
                {"name": "month_name", "locales": ["en", "sk"]},
                {"name": "month_sname", "locales": ["en", "sk"]}
            ]
        }

        level = cubes.create_level(desc)
        self.assertTrue(level.has_details)
        self.assertEqual(3, len(level.attributes))
        names = [str(a) for a in level.attributes]
        self.assertEqual(["month", "month_name", "month_sname"], names)

    def test_key_label_attributes(self):
        """Test key and label attributes - explicit and implicit"""

        attrs = cubes.attribute_list(["code"])
        level = cubes.Level("product", attrs)
        self.assertIsInstance(level.key, cubes.Attribute)
        self.assertEqual("code", str(level.key))
        self.assertIsInstance(level.label_attribute, cubes.Attribute)
        self.assertEqual("code", str(level.label_attribute))

        attrs = cubes.attribute_list(["code", "name"])
        level = cubes.Level("product", attrs)
        self.assertIsInstance(level.key, cubes.Attribute)
        self.assertEqual("code", str(level.key))
        self.assertIsInstance(level.label_attribute, cubes.Attribute)
        self.assertEqual("name", str(level.label_attribute))

        attrs = cubes.attribute_list(["info", "code", "name"])
        level = cubes.Level("product", attrs, key="code",
                            label_attribute="name")
        self.assertIsInstance(level.key, cubes.Attribute)
        self.assertEqual("code", str(level.key))
        self.assertIsInstance(level.label_attribute, cubes.Attribute)
        self.assertEqual("name", str(level.label_attribute))

        # Test key/label in full desc
        desc = {
            "name": "product",
            "attributes": ["info", "code", "name"],
            "label_attribute": "name",
            "key": "code"
        }

        level = cubes.create_level(desc)
        self.assertIsInstance(level.key, cubes.Attribute)
        self.assertEqual("code", str(level.key))
        self.assertIsInstance(level.label_attribute, cubes.Attribute)
        self.assertEqual("name", str(level.label_attribute))

    def test_level_inherit(self):
        desc = {
            "name": "product_type",
            "label": "Product Type"
        }

        level = cubes.create_level(desc)
        self.assertEqual(1, len(level.attributes))

        attr = level.attributes[0]
        self.assertEqual("product_type", attr.name)
        self.assertEqual("Product Type", attr.label)


    def test_comparison(self):
        """Comparison of level instances"""

        attrs = cubes.attribute_list(["info", "code", "name"])
        level1 = cubes.Level("product", attrs, key="code",
                             label_attribute="name")
        level2 = cubes.Level("product", attrs, key="code",
                             label_attribute="name")
        level3 = cubes.Level("product", attrs)
        attrs = cubes.attribute_list(["month", "month_name"])
        level4 = cubes.Level("product", attrs)

        self.assertEqual(level1, level2)
        self.assertNotEqual(level2, level3)
        self.assertNotEqual(level2, level4)


class HierarchyTestCase(unittest.TestCase):
    def setUp(self):
        self.levels = [
            cubes.Level("year", attributes=["year"]),
            cubes.Level("month",
                        attributes=["month", "month_name", "month_sname"]),
            cubes.Level("day", attributes=["day"]),
            cubes.Level("week", attributes=["week"])
        ]
        self.level_names = [level.name for level in self.levels]
        self.dimension = cubes.Dimension("date", levels=self.levels)
        levels = [self.levels[0], self.levels[1], self.levels[2]]
        self.hierarchy = cubes.Hierarchy("default",
                                         levels,
                                         self.dimension)

    def test_initialization(self):
        """No dimension on initialization should raise an exception."""
        with self.assertRaises(ModelError):
            cubes.Hierarchy("default", [], self.dimension)

        with self.assertRaisesRegexp(ModelInconsistencyError, "not be empty"):
            cubes.Hierarchy("default", [])

        with self.assertRaisesRegexp(ModelInconsistencyError, "as strings"):
            cubes.Hierarchy("default", ["iamastring"])

    def test_operators(self):
        """Hierarchy operators len(), hier[] and level in hier"""
        # __len__
        self.assertEqual(3, len(self.hierarchy))

        # __getitem__ by name
        self.assertEqual(self.levels[1], self.hierarchy[1])

        # __contains__ by name or level
        self.assertTrue(self.levels[1] in self.hierarchy)
        self.assertTrue("year" in self.hierarchy)
        self.assertFalse("flower" in self.hierarchy)

    def test_levels_for(self):
        """Levels for depth"""
        levels = self.hierarchy.levels_for_depth(0)
        self.assertEqual([], levels)

        levels = self.hierarchy.levels_for_depth(1)
        self.assertEqual([self.levels[0]], levels)

        self.assertRaises(HierarchyError, self.hierarchy.levels_for_depth, 4)

    def test_level_ordering(self):
        """Ordering of levels (next, previous)"""
        self.assertEqual(self.levels[0], self.hierarchy.next_level(None))
        self.assertEqual(self.levels[1],
                         self.hierarchy.next_level(self.levels[0]))
        self.assertEqual(self.levels[2],
                         self.hierarchy.next_level(self.levels[1]))
        self.assertEqual(None, self.hierarchy.next_level(self.levels[2]))

        self.assertEqual(None, self.hierarchy.previous_level(None))
        self.assertEqual(None, self.hierarchy.previous_level(self.levels[0]))
        self.assertEqual(self.levels[0],
                         self.hierarchy.previous_level(self.levels[1]))
        self.assertEqual(self.levels[1],
                         self.hierarchy.previous_level(self.levels[2]))

        self.assertEqual(0, self.hierarchy.level_index(self.levels[0]))
        self.assertEqual(1, self.hierarchy.level_index(self.levels[1]))
        self.assertEqual(2, self.hierarchy.level_index(self.levels[2]))

        self.assertRaises(cubes.HierarchyError, self.hierarchy.level_index,
                          self.levels[3])

    def test_rollup(self):
        """Path roll-up for hierarchy"""
        path = [2010, 1, 5]

        self.assertEqual([2010, 1], self.hierarchy.rollup(path))
        self.assertEqual([2010, 1], self.hierarchy.rollup(path, "month"))
        self.assertEqual([2010], self.hierarchy.rollup(path, "year"))
        self.assertRaises(HierarchyError, self.hierarchy.rollup,
                          [2010], "month")
        self.assertRaises(HierarchyError, self.hierarchy.rollup,
                          [2010], "unknown")

    def test_base_path(self):
        """Test base paths"""
        self.assertTrue(self.hierarchy.path_is_base([2012, 1, 5]))
        self.assertFalse(self.hierarchy.path_is_base([2012, 1]))
        self.assertFalse(self.hierarchy.path_is_base([2012]))
        self.assertFalse(self.hierarchy.path_is_base([]))

    def test_attributes(self):
        """Collecting attributes and keys"""
        keys = [a.name for a in self.hierarchy.key_attributes()]
        self.assertEqual(["year", "month", "day"], keys)

        attrs = [a.name for a in self.hierarchy.all_attributes]
        self.assertEqual(["year", "month", "month_name", "month_sname", "day"],
                         attrs)

    def test_copy(self):
        class DummyDimension(object):
            def __init__(self):
                self.name = "dummy"
                self.is_flat = False

        left = self.hierarchy.levels[0].attributes[0]
        left.dimension = DummyDimension()

        clone = copy.deepcopy(self.hierarchy)

        left = self.hierarchy.levels[0].attributes[0]
        right = clone.levels[0].attributes[0]
        # Make sure that the dimension is not copied
        self.assertIsNotNone(right.dimension)
        self.assertIs(left.dimension, right.dimension)

        self.assertEqual(self.hierarchy.levels, clone.levels)
        self.assertEqual(self.hierarchy, clone)


class DimensionTestCase(unittest.TestCase):
    def setUp(self):
        self.levels = [
            cubes.Level("year", attributes=["year"]),
            cubes.Level("month", attributes=["month", "month_name",
                                             "month_sname"]),
            cubes.Level("day", attributes=["day"]),
            cubes.Level("week", attributes=["week"])
        ]
        self.level_names = [level.name for level in self.levels]
        self.dimension = cubes.Dimension("date", levels=self.levels)

        levels = [self.levels[0], self.levels[1], self.levels[2]]
        self.hierarchy = cubes.Hierarchy("default", levels)

    def test_create(self):
        """Dimension from a dictionary"""
        dim = cubes.create_dimension("year")
        self.assertIsInstance(dim, cubes.Dimension)
        self.assertEqual("year", dim.name)
        self.assertEqual(["year"], [str(a) for a in dim.all_attributes])

        # Test default: explicit level attributes
        desc = {"name": "date", "levels": ["year"]}
        dim = cubes.create_dimension(desc)
        self.assertTrue(dim.is_flat)
        self.assertFalse(dim.has_details)
        self.assertIsInstance(dim, cubes.Dimension)
        self.assertEqual("date", dim.name)
        self.assertEqual(["year"], [str(a) for a in dim.all_attributes])

        desc = {"name": "date", "levels": ["year", "month", "day"]}
        dim = cubes.create_dimension(desc)
        self.assertIsInstance(dim, cubes.Dimension)
        self.assertEqual("date", dim.name)
        names = [str(a) for a in dim.all_attributes]
        self.assertEqual(["year", "month", "day"], names)
        self.assertFalse(dim.is_flat)
        self.assertFalse(dim.has_details)
        self.assertEqual(3, len(dim.levels))
        for level in dim.levels:
            self.assertIsInstance(level, cubes.Level)
        self.assertEqual(1, len(dim.hierarchies))
        self.assertEqual(3, len(dim.hierarchy()))

        # Test default: implicit single level attributes
        desc = {"name": "product", "attributes": ["code", "name"]}
        dim = cubes.create_dimension(desc)
        names = [str(a) for a in dim.all_attributes]
        self.assertEqual(["code", "name"], names)
        self.assertEqual(1, len(dim.levels))
        self.assertEqual(1, len(dim.hierarchies))

    def test_flat_dimension(self):
        """Flat dimension and 'has details' flags"""
        dim = cubes.create_dimension("foo")
        self.assertTrue(dim.is_flat)
        self.assertFalse(dim.has_details)
        self.assertEqual(1, len(dim.levels))

        level = dim.level("foo")
        self.assertIsInstance(level, cubes.Level)
        self.assertEqual("foo", level.name)
        self.assertEqual(1, len(level.attributes))
        self.assertEqual("foo", str(level.key))

        attr = level.attributes[0]
        self.assertIsInstance(attr, cubes.Attribute)
        self.assertEqual("foo", attr.name)

    def test_comparisons(self):
        """Comparison of dimension instances"""

        dim1 = cubes.create_dimension(DIM_DATE_DESC)
        dim2 = cubes.create_dimension(DIM_DATE_DESC)

        self.assertListEqual(dim1.levels, dim2.levels)
        self.assertListEqual(dim1.hierarchies.items(),
                             dim2.hierarchies.items())

        self.assertEqual(dim1, dim2)

    def test_to_dict(self):
        desc = self.dimension.to_dict()
        dim = cubes.create_dimension(desc)

        self.assertEqual(self.dimension.hierarchies, dim.hierarchies)
        self.assertEqual(self.dimension.levels, dim.levels)
        self.assertEqual(self.dimension, dim)

    def test_template(self):
        dims = {"date": self.dimension}
        desc = {"template": "date", "name": "date"}

        dim = cubes.create_dimension(desc, dims)
        self.assertEqual(self.dimension, dim)
        hier = dim.hierarchy()
        self.assertEqual(4, len(hier.levels))

        desc["hierarchy"] = ["year", "month"]
        dim = cubes.create_dimension(desc, dims)
        self.assertEqual(1, len(dim.hierarchies))
        hier = dim.hierarchy()
        self.assertEqual(2, len(hier.levels))

        template = self.dimension.to_dict()
        template["hierarchies"] = [
            {"name": "ym", "levels": ["year", "month"]},
            {"name": "ymd", "levels": ["year", "month", "day"]}
        ]

        template["default_hierarchy_name"] = "ym"
        template = cubes.create_dimension(template)
        dims = {"date": template}
        desc = {"template": "date", "name":"another_date"}
        dim = cubes.create_dimension(desc, dims)
        self.assertEqual(2, len(dim.hierarchies))
        self.assertEqual(["ym", "ymd"],
                         [hier.name for hier in dim.hierarchies.values()])

    def test_template_hierarchies(self):
        md = {
            "name": "time",
            "levels": ["year", "month", "day", "hour"],
            "hierarchies": [
                {"name": "full", "levels": ["year", "month", "day", "hour"]},
                {"name": "ymd", "levels": ["year", "month", "day"]},
                {"name": "ym", "levels": ["year", "month"]},
                {"name": "y", "levels": ["year"]},
            ]
        }
        dim_time = cubes.create_dimension(md)
        templates = {"time": dim_time}
        md = {
            "name": "date",
            "template": "time",
            "hierarchies": [
                "ymd", "ym", "y"
            ]
        }

        dim_date = cubes.create_dimension(md, templates)

        self.assertEqual(dim_date.name, "date")
        self.assertEqual(len(dim_date.hierarchies), 3)
        names = [h.name for h in dim_date.hierarchies.values()]
        self.assertEqual(["ymd", "ym", "y"], names)

    def test_template_info(self):
        md = {
            "name": "template",
            "levels": [
                { "name": "one", "info": {"units":"$", "format": "foo"}}
            ]
        }
        tempdim = cubes.create_dimension(md)

        md = {
            "name": "dim",
            "levels": [
                { "name": "one", "info": {"units":"USD"}}
            ],
            "template": "template"
        }

        templates = {"template": tempdim}
        dim = cubes.create_dimension(md, templates)

        level = dim.level("one")
        self.assertIn("units", level.info)
        self.assertIn("format", level.info)
        self.assertEqual(level.info["units"], "USD")
        self.assertEqual(level.info["format"], "foo")

class CubeTestCase(unittest.TestCase):
    def setUp(self):
        a = [DIM_DATE_DESC, DIM_PRODUCT_DESC, DIM_FLAG_DESC]
        self.measures = cubes.attribute_list(["amount", "discount"], Measure)
        self.details = cubes.attribute_list(["detail"], Attribute)
        self.dimensions = [cubes.create_dimension(desc) for desc in a]
        self.cube = cubes.Cube("contracts",
                                dimensions=self.dimensions,
                                measures=self.measures,
                                details=self.details)

    def test_create_cube(self):
        cube = {
                "name": "cube",
                "dimensions": ["date"],
                "aggregates": ["record_count"],
                "details": ["some_detail", "another_detail"]
        }
        cube = create_cube(cube)

        self.assertEqual(cube.name, "cube")
        self.assertEqual(len(cube.aggregates), 1)
        self.assertEqual(len(cube.details), 2)

    def test_get_dimension(self):
        self.assertListEqual(self.dimensions, self.cube.dimensions)

        self.assertEqual("date", self.cube.dimension("date").name)
        self.assertEqual("product", self.cube.dimension("product").name)
        self.assertEqual("flag", self.cube.dimension("flag").name)
        self.assertRaises(NoSuchDimensionError, self.cube.dimension, "xxx")

    def test_get_measure(self):
        self.assertListEqual(self.measures, self.cube.measures)

        self.assertEqual("amount", self.cube.measure("amount").name)
        self.assertEqual("discount", self.cube.measure("discount").name)
        self.assertRaises(NoSuchAttributeError, self.cube.measure, "xxx")

    def test_attributes(self):
        all_attributes = self.cube.all_attributes

        refs = [a.ref() for a in all_attributes]
        expected = [
            'date.year',
            'date.month',
            'date.month_name',
            'date.day',
            'product.key',
            'product.name',
            'product.description',
            'flag',
            'detail',
            'amount',
            'discount']
        self.assertSequenceEqual(expected, refs)

        attributes = self.cube.get_attributes(["date.year", "product.name"])
        refs = [a.ref() for a in attributes]
        expected = ['date.year', 'product.name']
        self.assertSequenceEqual(expected, refs)

        attributes = self.cube.get_attributes(["amount"])
        refs = [a.ref() for a in attributes]
        self.assertSequenceEqual(["amount"], refs)

        with self.assertRaises(NoSuchAttributeError):
            self.cube.get_attributes(["UNKNOWN"])

    @unittest.skip("deferred (needs workspace)")
    def test_to_dict(self):
        desc = self.cube.to_dict()
        dims = dict((dim.name, dim) for dim in self.dimensions)
        cube = cubes.create_cube(desc, dims)
        self.assertEqual(self.cube.dimensions, cube.dimensions)
        self.assertEqual(self.cube.measures, cube.measures)
        self.assertEqual(self.cube, cube)

    def test_links(self):
        dims = dict((d.name, d) for d in self.dimensions)

        links = [{"name": "date"}]
        cube = cubes.Cube("contracts",
                          dimension_links=links,
                          measures=self.measures)
        cube.link_dimensions(dims)
        self.assertEqual(len(cube.dimensions), 1)
        dim = cube.dimension("date")
        self.assertEqual(len(dim.hierarchies), 2)

        links = [{"name": "date"}, "product", "flag"]
        cube = cubes.Cube("contracts",
                          dimension_links=links,
                          measures=self.measures)
        cube.link_dimensions(dims)
        self.assertEqual(len(cube.dimensions), 3)
        self.assertIsInstance(cube.dimension("flag"), Dimension)

    def test_link_hierarchies(self):
        dims = dict((d.name, d) for d in self.dimensions)

        links = [{"name": "date"}]
        cube = cubes.Cube("contracts",
                          dimension_links=links,
                          measures=self.measures)
        cube.link_dimensions(dims)
        dim = cube.dimension("date")
        self.assertEqual(len(dim.hierarchies), 2)
        self.assertEqual(dim.hierarchy().name, "ymd")

        links = [{"name": "date", "nonadditive":None}]
        cube = cubes.Cube("contracts",
                          dimension_links=links,
                          measures=self.measures)
        cube.link_dimensions(dims)
        dim = cube.dimension("date")
        self.assertEqual(len(dim.hierarchies), 2)
        self.assertEqual(dim.hierarchy().name, "ymd")

        links = [{"name": "date", "hierarchies": ["ym"]}]
        cube = cubes.Cube("contracts",
                          dimension_links=links,
                          measures=self.measures)
        cube.link_dimensions(dims)
        dim = cube.dimension("date")
        self.assertEqual(len(dim.hierarchies), 1)
        self.assertEqual(dim.hierarchy().name, "ym")

    def test_inherit_nonadditive(self):
        dims = [DIM_DATE_DESC, DIM_PRODUCT_DESC, DIM_FLAG_DESC]

        cube = {
            "name": "contracts",
            "dimensions": ["date", "product"],
            "nonadditive": "time",
            "measures": ["amount", "discount"]
        }

        dims = [cubes.create_dimension(md) for md in dims]
        dims = dict((dim.name, dim) for dim in dims)

        cube = cubes.create_cube(cube)

        measures = cube.measures
        self.assertEqual(measures[0].nonadditive, "time")

class OldModelValidatorTestCase(unittest.TestCase):
    def setUp(self):
        self.model = cubes.Model('test')
        self.date_levels = [ {"name":"year", "key": "year" }, {"name":"month", "key": "month" } ]
        self.date_levels2 = [ { "name":"year", "key": "year" }, {"name":"month", "key": "month" }, {"name":"day", "key":"day"} ]
        self.date_hiers = [ { "name":"ym", "levels": ["year", "month"] } ]
        self.date_hiers2 = [ {"name":"ym", "levels": ["year", "month"] },
                             {"name":"ymd", "levels": ["year", "month", "day"] } ]
        self.date_desc = { "name": "date", "levels": self.date_levels , "hierarchies": self.date_hiers }

    def test_dimension_validation(self):
        date_desc = { "name": "date",
                      "levels": [
                            {"name": "year", "attributes": ["year"]}
                         ]
                    }
        dim = cubes.create_dimension(date_desc)
        self.assertEqual(1, len(dim.levels))
        results = dim.validate()
        self.assertValidation(results, "No levels")
        self.assertValidation(results, "No defaut hierarchy")

        # FIXME: uncomment this after implementing https://github.com/Stiivi/cubes/issues/8
        # self.assertValidationError(results, "No hierarchies in dimension", expected_type = "default")

        date_desc = { "name": "date", "levels": self.date_levels}
        dim = cubes.create_dimension(date_desc)
        results = dim.validate()

        # FIXME: uncomment this after implementing https://github.com/Stiivi/cubes/issues/8
        # self.assertValidationError(results, "No hierarchies in dimension.*more", expected_type = "error")

        date_desc = { "name": "date", "levels": self.date_levels , "hierarchies": self.date_hiers }
        dim = cubes.create_dimension(date_desc)
        results = dim.validate()

        self.assertValidation(results, "No levels in dimension", "Dimension is invalid without levels")
        self.assertValidation(results, "No hierarchies in dimension", "Dimension is invalid without hierarchies")
        # self.assertValidationError(results, "No default hierarchy name")

        dim.default_hierarchy_name = 'foo'
        results = dim.validate()
        self.assertValidationError(results, "Default hierarchy .* does not")
        self.assertValidation(results, "No default hierarchy name")

        dim.default_hierarchy_name = 'ym'
        results = dim.validate()
        self.assertValidation(results, "Default hierarchy .* does not")

        date_desc = { "name": "date", "levels": self.date_levels2 , "hierarchies": self.date_hiers2 }
        dim = cubes.create_dimension(date_desc)
        results = dim.validate()
        self.assertValidationError(results, "No defaut hierarchy .* more than one")

    def assertValidation(self, results, expected, message = None):
        if not message:
            message = "Validation pass expected (match: '%s')" % expected

        for result in results:
            if re.match(expected, result[1]):
                self.fail(message)

    def assertValidationError(self, results, expected, message = None, expected_type = None):
        if not message:
            if expected_type:
                message = "Validation %s expected (match: '%s')" % (expected_type, expected)
            else:
                message = "Validation fail expected (match: '%s')" % expected

        for result in results:
            if re.match(expected, result[1]):
                if not expected_type or (expected_type and expected_type == result[0]):
                    return
        self.fail(message)


class ReadModelDescriptionTestCase(ModelTestCaseBase):
    def setUp(self):
        super(ReadModelDescriptionTestCase, self).setUp()

    def test_from_file(self):
        path = self.model_path("model.json")
        desc = cubes.read_model_metadata(path)

        self.assertIsInstance(desc, dict)
        self.assertTrue("cubes" in desc)
        self.assertTrue("dimensions" in desc)
        self.assertEqual(1, len(desc["cubes"]))
        self.assertEqual(6, len(desc["dimensions"]))

    def test_from_bundle(self):
        path = self.model_path("test.cubesmodel")
        desc = cubes.read_model_metadata(path)

        self.assertIsInstance(desc, dict)
        self.assertTrue("cubes" in desc)
        self.assertTrue("dimensions" in desc)
        self.assertEqual(1, len(desc["cubes"]))
        self.assertEqual(6, len(desc["dimensions"]))

        with self.assertRaises(ArgumentError):
            path = self.model_path("model.json")
            desc = cubes.read_model_metadata_bundle(path)

class BaseModelTestCase(ModelTestCaseBase):
    def test_base_ignorance(self):
        ws = cubes.Workspace(load_base_model=False)
        with self.assertRaises(NoSuchDimensionError):
            ws.dimension("base_time")

    def test_base_existence(self):
        ws = cubes.Workspace()
        dim = ws.dimension("base_time")
        self.assertEqual(dim.name, "base_time")

    def test_select_hierarchies(self):
        ws = cubes.Workspace()
        dim_time = ws.dimension("base_time")
        dim_date = ws.dimension("base_date")
        self.assertLess(len(dim_date.hierarchies), len(dim_time.hierarchies))

def test_suite():
    suite = unittest.TestSuite()

    suite.addTest(unittest.makeSuite(AttributeTestCase))
    suite.addTest(unittest.makeSuite(LevelTestCase))
    suite.addTest(unittest.makeSuite(HierarchyTestCase))
    suite.addTest(unittest.makeSuite(DimensionTestCase))
    suite.addTest(unittest.makeSuite(CubeTestCase))
    suite.addTest(unittest.makeSuite(ModelTestCase))

    suite.addTest(unittest.makeSuite(OldModelValidatorTestCase))

    return suite

########NEW FILE########
__FILENAME__ = namespace
import unittest
from cubes.workspace import Namespace
from .common import CubesTestCaseBase

class NamespaceTestCase(CubesTestCaseBase):
    def test_create(self):
        ns = Namespace()
        ns.create_namespace("slicer")
        self.assertIn("slicer", ns.namespaces)
        self.assertIsInstance(ns.namespaces["slicer"], Namespace)

    def test_get_namespace(self):
        base = Namespace()
        slicerns = base.create_namespace("slicer")

        self.assertEqual((base, []), base.namespace(""))
        self.assertEqual((slicerns, []), base.namespace("slicer"))
        self.assertEqual((base, ["unknown"]), base.namespace("unknown"))
        self.assertEqual((base, ["one", "two"]), base.namespace("one.two"))

    def test_get_namespace_create(self):
        base = Namespace()
        slicerns = base.create_namespace("slicer")

        self.assertEqual((base, []), base.namespace("", create=True))
        self.assertEqual((slicerns, []), base.namespace("slicer", create=True))

        (ns, remainder) = base.namespace("new", create=True)
        self.assertEqual([], remainder)
        self.assertEqual((ns, []), base.namespace("new"))

        (last, remainder) = base.namespace("one.two.three", create=True)
        self.assertEqual([], remainder)

        self.assertIn("one", base.namespaces)
        (ns, remainder) = base.namespace("one")
        self.assertEqual([], remainder)

        self.assertIn("two", ns.namespaces)
        (ns, remainder) = ns.namespace("two")
        self.assertEqual([], remainder)

        self.assertIn("three", ns.namespaces)
        (ns, remainder) = ns.namespace("three")
        self.assertEqual([], remainder)

        (last, remainder) = base.namespace("one.two.three.four.five")
        self.assertEqual(["four", "five"], remainder)

    def test_namespace_for_cube(self):
        base = Namespace()

        (ns, relative) = base.namespace_for_cube("cube")
        self.assertEqual(ns, base)
        self.assertEqual(relative, "cube")

        (ns, relative) = base.namespace_for_cube("extern.cube")
        self.assertEqual(ns, base)
        self.assertEqual(relative, "extern.cube")

        (ns, relative) = base.namespace_for_cube("even.deeper.extern.cube")
        self.assertEqual(ns, base)
        self.assertEqual(relative, "even.deeper.extern.cube")

        extern = base.create_namespace("extern")
        (ns, relative) = base.namespace_for_cube("extern.cube")
        self.assertEqual(ns, extern)
        self.assertEqual(relative, "cube")

        (ns, relative) = base.namespace_for_cube("extern.deeper.cube")
        # import pdb; pdb.set_trace()
        self.assertEqual(ns, extern)
        self.assertEqual(relative, "deeper.cube")

        (deep, remainder) = base.namespace("even.deeper.extern", create=True)
        (ns, relative) = base.namespace_for_cube("even.deeper.extern.cube")
        self.assertEqual(ns, deep)
        self.assertEqual(relative, "cube")


########NEW FILE########
__FILENAME__ = server
# -*- coding=utf -*-
import unittest
from cubes import __version__
import json
from .common import CubesTestCaseBase
from sqlalchemy import MetaData, Table, Column, Integer, String

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from cubes.server import create_server

import csv

class SlicerTestCaseBase(CubesTestCaseBase):
    def setUp(self):
        super(SlicerTestCaseBase, self).setUp()

        self.slicer = create_server()
        self.slicer.debug = True
        self.server = Client(self.slicer, BaseResponse)
        self.logger = self.slicer.logger
        self.logger.setLevel("DEBUG")

    def get(self, path, *args, **kwargs):
        if not path.startswith("/"):
            path = "/" + path

        response = self.server.get(path, *args, **kwargs)

        try:
            result = json.loads(response.data)
        except ValueError:
            result = response.data

        return (result, response.status_code)

    def assertHasKeys(self, d, keys):
        for key in keys:
            self.assertIn(key, d)


class SlicerTestCase(SlicerTestCaseBase):
    def test_version(self):
        response, status = self.get("version")
        self.assertEqual(200, status)
        self.assertIsInstance(response, dict)
        self.assertIn("version", response)
        self.assertEqual(__version__, response["version"])

    def test_unknown(self):
        response, status = self.get("this_is_unknown")
        self.assertEqual(404, status)

class SlicerModelTestCase(SlicerTestCaseBase):
    sql_engine = "sqlite:///"

    def setUp(self):
        super(SlicerModelTestCase, self).setUp()

        ws = self.create_workspace()
        self.slicer.cubes_workspace = ws

        # Satisfy browser with empty tables
        # TODO: replace this once we have data
        store = ws.get_store("default")
        table = Table("sales", store.metadata)
        table.append_column(Column("id", Integer))
        table.create()

        ws.add_model(self.model_path("model.json"))
        ws.add_model(self.model_path("sales_no_date.json"))

    def test_cube_list(self):
        response, status = self.get("cubes")
        self.assertIsInstance(response, list)
        self.assertEqual(2, len(response))

        for info in response:
            self.assertIn("name", info)
            self.assertIn("label", info)
            self.assertNotIn("dimensions", info)

        names = [c["name"] for c in response]
        self.assertItemsEqual(["contracts", "sales"], names)

    def test_no_cube(self):
        response, status = self.get("cube/unknown_cube/model")
        self.assertEqual(404, status)
        self.assertIsInstance(response, dict)
        self.assertIn("error", response)
        # self.assertRegexpMatches(response["error"]["message"], "Unknown cube")

    def test_get_cube(self):
        response, status = self.get("cube/sales/model")
        self.assertEqual(200, status)
        self.assertIsInstance(response, dict)
        self.assertNotIn("error", response)

        self.assertIn("name", response)
        self.assertIn("measures", response)
        self.assertIn("aggregates", response)
        self.assertIn("dimensions", response)

        # We should not get internal info
        self.assertNotIn("mappings", response)
        self.assertNotIn("joins", response)
        self.assertNotIn("options", response)
        self.assertNotIn("browser_options", response)
        self.assertNotIn("fact", response)

        # Propert content
        aggregates = response["aggregates"]
        self.assertIsInstance(aggregates, list)
        self.assertEqual(4, len(aggregates))
        names = [a["name"] for a in aggregates]
        self.assertItemsEqual(["amount_sum", "amount_min", "discount_sum",
                               "record_count"], names)

    def test_cube_dimensions(self):
        response, status = self.get("cube/sales/model")
        # Dimensions
        dims = response["dimensions"]
        self.assertIsInstance(dims, list)
        self.assertIsInstance(dims[0], dict)

        for dim in dims:
            self.assertIn("name", dim)
            self.assertIn("levels", dim)
            self.assertIn("default_hierarchy_name", dim)
            self.assertIn("hierarchies", dim)
            self.assertIn("is_flat", dim)
            self.assertIn("has_details", dim)

        names = [d["name"] for d in dims]
        self.assertItemsEqual(["date", "flag", "product"], names)

        # Test dim flags
        self.assertEqual(True, dims[1]["is_flat"])
        self.assertEqual(False, dims[1]["has_details"])

        self.assertEqual(False, dims[0]["is_flat"])
        self.assertEqual(True, dims[0]["has_details"])


class SlicerAggregateTestCase(SlicerTestCaseBase):
    sql_engine = "sqlite:///"
    def setUp(self):
        super(SlicerAggregateTestCase, self).setUp()

        self.workspace = self.create_workspace(model="server.json")
        self.cube = self.workspace.cube("aggregate_test")
        self.slicer.cubes_workspace = self.workspace

        self.facts = Table("facts", self.metadata,
                        Column("id", Integer),
                        Column("id_date", Integer),
                        Column("id_item", Integer),
                        Column("amount", Integer)
                        )

        self.dim_date = Table("date", self.metadata,
                        Column("id", Integer),
                        Column("year", Integer),
                        Column("month", Integer),
                        Column("day", Integer)
                        )

        self.dim_item = Table("item", self.metadata,
                        Column("id", Integer),
                        Column("name", String)
                        )

        self.metadata.create_all()

        data = [
                    # Master-detail Match
                    ( 1, 20130901, 1,   20),
                    ( 2, 20130902, 1,   20),
                    ( 3, 20130903, 1,   20),
                    ( 4, 20130910, 1,   20),
                    ( 5, 20130915, 1,   20),
                    #             --------
                    #             ∑    100
                    # No city dimension
                    ( 6, 20131001, 2,  200),
                    ( 7, 20131002, 2,  200),
                    ( 8, 20131004, 2,  200),
                    ( 9, 20131101, 3,  200),
                    (10, 20131201, 3,  200),
                    #             --------
                    #             ∑   1000
                    #             ========
                    #             ∑   1100

                ]

        self.load_data(self.facts, data)

        data = [
                    (1, "apple"),
                    (2, "pear"),
                    (3, "garlic"),
                    (4, "carrod")
                ]

        self.load_data(self.dim_item, data)

        data = []
        for day in range(1, 31):
            row = (20130900+day, 2013, 9, day)
            data.append(row)

        self.load_data(self.dim_date, data)

    def test_aggregate_csv_headers(self):
        # Default = labels
        url = "cube/aggregate_test/aggregate?drilldown=date&format=csv"
        response, status = self.get(url)

        reader = csv.reader(response.split("\n"))
        header = reader.next()
        self.assertSequenceEqual(["Year", "Total Amount", "Item Count"],
                                 header)

        # Labels - explicit
        url = "cube/aggregate_test/aggregate?drilldown=date&format=csv&header=labels"
        response, status = self.get(url)

        reader = csv.reader(response.split("\n"))
        header = reader.next()
        self.assertSequenceEqual(["Year", "Total Amount", "Item Count"],
                                 header)
        # Names
        url = "cube/aggregate_test/aggregate?drilldown=date&format=csv&header=names"
        response, status = self.get(url)

        reader = csv.reader(response.split("\n"))
        header = reader.next()
        self.assertSequenceEqual(["date.year", "amount_sum", "count"],
                                 header)
        # None
        url = "cube/aggregate_test/aggregate?drilldown=date&format=csv&header=none"
        response, status = self.get(url)

        reader = csv.reader(response.split("\n"))
        header = reader.next()
        self.assertSequenceEqual(["2013", "100", "5"],
                                 header)

########NEW FILE########
__FILENAME__ = slicertest
import unittest
import traceback
import os

from cubes import Workspace
from cubes.errors import *
import cubes.browser

@unittest.skipIf("TEST_SLICER" not in os.environ,
                 "No TEST_SLICER environment variable set.")

class SlicerTestCase(unittest.TestCase):
    def setUp(self):
        self.w = Workspace()
        self.w.add_slicer("myslicer", "http://localhost:5010", username=os.environ.get("SLICER_USERNAME"), password=os.environ.get("SLICER_PASSWORD"))

        self.cube_list = self.w.list_cubes()

    def first_date_dim(self, cube):
        for d in cube.dimensions:
            if ( d.info.get('is_date') ):
                return d
        raise BrowserError("No date dimension in cube %s" % cube.name)

    def test_basic(self):
        for c in self.cube_list:
            if c.get('category') is not None and 'Mix' in c.get('category', ''):
                continue
            print ("Doing %s..." % c.get('name')),
            cube = self.w.cube(c.get('name'))
            date_dim = self.first_date_dim(cube)
            cut = cubes.browser.RangeCut(date_dim, [ 2013, 9, 25 ], None)
            cell = cubes.browser.Cell(cube, [ cut ])
            drill_levels = [ l for l in date_dim.hierarchy().levels if l.name in ('day', 'date') ]
            if not drill_levels:
                print "Skipping cube %s with no day/date drilldown available." % c.get('name')
                continue
            drill = cubes.browser.Drilldown([(date_dim, None, date_dim.level(drill_levels[0]))], cell)
            b = self.w.browser(cube)
            try:
                attr_dim = cube.dimension("attr")
                split = cubes.browser.PointCut(attr_dim, ['paid', 'pnb'])
            except:
                split = None
            try:
                kw = {}
                if cube.aggregates:
                    kw['aggregates'] = [cube.aggregates[0]]
                elif cube.measures:
                    kw['measures'] = [ cube.measures[0] ]
                else:
                    raise ValueError("Cube has neither aggregates nor measures")
                result = b.aggregate(cell, drilldown=drill, split=split, **kw)
                print result.cells
            except:
                traceback.print_exc()


########NEW FILE########
__FILENAME__ = time
# -*- coding=utf -*-
from common import CubesTestCaseBase
from cubes.errors import *
from cubes.calendar import *
from datetime import datetime


class DateTimeTestCase(CubesTestCaseBase):
    def setUp(self):
        super(DateTimeTestCase,self).setUp()

        self.workspace = self.create_workspace(model="datetime.json")
        self.cal = Calendar()

    def test_empty(self):
        dim = self.workspace.dimension("default_date")

        self.assertEqual("date", dim.role)
        self.assertIsNone(dim.level("year").role)

    def test_implicit_roles(self):
        dim = self.workspace.dimension("default_date")

        elements = calendar_hierarchy_units(dim.hierarchy("ymd"))
        self.assertSequenceEqual(["year", "month", "day"], elements)

    def test_explicit_roles(self):
        dim = self.workspace.dimension("explicit_date")

        elements = calendar_hierarchy_units(dim.hierarchy("ymd"))
        self.assertSequenceEqual(["year", "month", "day"], elements)

    def test_no_roles(self):
        dim = self.workspace.dimension("invalid_date")

        with self.assertRaises(ArgumentError):
            calendar_hierarchy_units(dim.hierarchy("ymd"))

    def test_time_path(self):
        date = datetime(2012, 12, 24)

        self.assertEqual([], self.cal.path(date, []))
        self.assertEqual([2012], self.cal.path(date, ["year"]))
        self.assertEqual([12, 24], self.cal.path(date, ["month", "day"]))
        self.assertEqual([2012, 4], self.cal.path(date, ["year", "quarter"]))

    def test_path_weekday(self):
        # This is monday:
        date = datetime(2013, 10, 21)
        self.assertEqual([0], self.cal.path(date, ["weekday"]))

        # Week start: Sunday
        self.cal.first_weekday = 6
        self.assertEqual([1], self.cal.path(date, ["weekday"]))

        # Week start: Saturday
        self.cal.first_weekday = 5
        self.assertEqual([2], self.cal.path(date, ["weekday"]))

    # Reference for the named relative test
    #                              2012
    # 
    #     Január            Február           Marec             Apríl
    # po     2  9 16 23 30     6 13 20 27        5*12 19 26        2  9 16 23 30
    # ut     3 10 17 24 31     7 14 21 28        6 13 20 27        3 10 17 24
    # st     4 11 18 25     1  8 15 22 29        7 14 21 28        4 11 18 25
    # št     5 12 19 26     2  9 16 23       *1  8 15 22 29        5 12 19 26
    # pi     6 13 20 27     3 10 17 24        2  9 16 23 30        6 13 20 27
    # so     7 14 21 28     4 11 18 25        3 10 17 24 31        7 14 21 28
    # ne  1  8 15 22 29     5 12 19 26        4 11 18 25        1  8 15 22 29

    def test_named_relative(self):
        date = datetime(2012, 3, 1)

        units = ["year", "month", "day"]
        path = self.cal.named_relative_path("tomorrow", units, date)
        self.assertEqual([2012, 3, 2], path)

        path = self.cal.named_relative_path("yesterday", units, date)
        self.assertEqual([2012, 2, 29], path)

        path = self.cal.named_relative_path("weekago", units, date)
        self.assertEqual([2012, 2, 23], path)

        path = self.cal.named_relative_path("3weeksago", units, date)
        self.assertEqual([2012, 2, 9], path)

        date = datetime(2012, 3, 12)

        path = self.cal.named_relative_path("monthago", units, date)
        self.assertEqual([2012, 2, 12], path)

        path = self.cal.named_relative_path("12monthsago", units, date)
        self.assertEqual([2011, 3, 12], path)

        path = self.cal.named_relative_path("monthforward", units, date)
        self.assertEqual([2012, 4, 12], path)

        path = self.cal.named_relative_path("12monthsforward", units, date)
        self.assertEqual([2013, 3, 12], path)

    def test_named_relative_truncated(self):
        date = datetime(2012, 3, 1, 10, 30)

        units = ["year", "month", "day", "hour"]

        path = self.cal.named_relative_path("lastweek", units, date)
        self.assertEqual([2012, 2, 20, 0], path)

        path = self.cal.named_relative_path("last3weeks", units, date)
        self.assertEqual([2012, 2, 6, 0], path)

        date = datetime(2012, 3, 12)

        path = self.cal.named_relative_path("lastmonth", units, date)
        self.assertEqual([2012, 2, 1, 0], path)

        path = self.cal.named_relative_path("last12months", units, date)
        self.assertEqual([2011, 3, 1, 0], path)

        path = self.cal.named_relative_path("nextmonth", units, date)
        self.assertEqual([2012, 4, 1, 0], path)

        path = self.cal.named_relative_path("next12months", units, date)
        self.assertEqual([2013, 3, 1,0 ], path)

        path = self.cal.named_relative_path("lastquarter", units, date)
        self.assertEqual([2011,10, 1, 0], path)

        path = self.cal.named_relative_path("lastyear", units, date)
        self.assertEqual([2011, 1, 1,0 ], path)

    def test_distance(self):
        # Meniny (SK): Anna/Hana
        time = datetime(2012, 7, 26, 12, 5)

        self.assertEqual(207, self.cal.since_period_start("year", "day", time))
        self.assertEqual(25, self.cal.since_period_start("quarter", "day", time))
        self.assertEqual(25, self.cal.since_period_start("month", "day", time))
        self.assertEqual(612, self.cal.since_period_start("month", "hour", time))
        self.assertEqual(12, self.cal.since_period_start("day", "hour", time))

        time = datetime(2012, 1, 1, 1, 1)

        self.assertEqual(0, self.cal.since_period_start("year", "day", time))
        self.assertEqual(0, self.cal.since_period_start("quarter", "day", time))
        self.assertEqual(0, self.cal.since_period_start("month", "day", time))
        self.assertEqual(1, self.cal.since_period_start("month", "hour", time))
        self.assertEqual(1, self.cal.since_period_start("day", "hour", time))

########NEW FILE########
__FILENAME__ = workspace
import unittest
import os
import json
import re
from cubes.errors import *
from cubes.workspace import *
from cubes.stores import Store
from cubes.model import *

from common import CubesTestCaseBase
# FIXME: remove this once satisfied

class WorkspaceTestCaseBase(CubesTestCaseBase):
    def default_workspace(self, model_name=None):
        model_name = model_name or "model.json"
        ws = Workspace(config=self.data_path("slicer.ini"))
        ws.add_model(self.model_path("model.json"))
        return ws

class WorkspaceStoresTestCase(WorkspaceTestCaseBase):
    def test_empty(self):
        """Just test whether we can create empty workspace"""
        ws = Workspace()
        self.assertEqual(0, len(ws.store_infos))

    def test_stores(self):
        class ImaginaryStore(Store):
            pass

        ws = Workspace(stores={"default":{"type":"imaginary"}})
        self.assertTrue("default" in ws.store_infos)

        ws = Workspace(stores=self.data_path("stores.ini"))
        self.assertEqual(3, len(ws.store_infos) )

        ws = Workspace(config=self.data_path("slicer.ini"))
        self.assertEqual(2, len(ws.store_infos))

        self.assertTrue("default" in ws.store_infos)
        self.assertTrue("production" in ws.store_infos)

    def test_duplicate_store(self):
        with self.assertRaises(CubesError):
            ws = Workspace(config=self.data_path("slicer.ini"),
                           stores=self.data_path("stores.ini"))


class WorkspaceModelTestCase(WorkspaceTestCaseBase):
    def test_get_cube(self):
        ws = self.default_workspace()
        cube = ws.cube("contracts")

        self.assertEqual("contracts", cube.name)
        # self.assertEqual(6, len(cube.dimensions))
        self.assertEqual(1, len(cube.measures))

    def test_get_namespace_cube(self):
        ws = Workspace()
        ws.import_model(self.model_path("model.json"), namespace="local")

        # This should pass
        cube = ws.cube("contracts")

        self.assertIsInstance(cube, Cube)
        self.assertEqual(cube.name, "contracts")
        ws.lookup_method = "exact"

        with self.assertRaises(NoSuchCubeError):
            cube = ws.cube("contracts")

        cube = ws.cube("local.contracts")
        self.assertEqual("local.contracts", cube.name)

    def test_get_dimension(self):
        ws = self.default_workspace()
        dim = ws.dimension("date")
        self.assertEqual("date", dim.name)

    def test_template(self):
        ws = Workspace()
        ws.add_model(self.model_path("templated_dimension.json"))

        dim = ws.dimension("date")
        self.assertEqual("date", dim.name)
        self.assertEqual(3, len(dim.levels))

        dim = ws.dimension("start_date")
        self.assertEqual("start_date", dim.name)
        self.assertEqual(3, len(dim.levels))

        dim = ws.dimension("end_date")
        self.assertEqual("end_date", dim.name)

    def test_external_template(self):
        ws = Workspace()
        ws.add_model(self.model_path("templated_dimension.json"))
        ws.add_model(self.model_path("templated_dimension_ext.json"))

        dim = ws.dimension("another_date")
        self.assertEqual("another_date", dim.name)
        self.assertEqual(3, len(dim.levels))

    @unittest.skip("We are lazy now, we don't want to ping the provider for "
                   "nothing")
    def test_duplicate_dimension(self):
        ws = Workspace()
        ws.add_model(self.model_path("templated_dimension.json"))

        model = {"dimensions": [{"name": "date"}]}
        with self.assertRaises(ModelError):
            ws.add_model(model)

    def test_local_dimension(self):
        # Test whether we can use local dimension with the same name as the
        # public one
        ws = Workspace()
        ws.import_model(self.model_path("model_public_dimensions.json"))
        ws.import_model(self.model_path("model_private_dimensions.json"))

        dim = ws.dimension("date")
        self.assertEqual(3, len(dim.levels))
        self.assertEqual(["year", "month", "day"], dim.level_names)


        cube = ws.cube("events")
        dim = cube.dimension("date")
        self.assertEqual(["year", "month", "day"], dim.level_names)

        cube = ws.cube("lonely_yearly_events")
        dim = cube.dimension("date")
        self.assertEqual(["lonely_year"], dim.level_names)


########NEW FILE########
