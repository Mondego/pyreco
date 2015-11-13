__FILENAME__ = facet
#!/usr/bin/env python
"""
OpenRefine Facets, Engine, and Facet Responses.
"""

# Copyright (c) 2011 Paul Makepeace, Real Programmers. All rights reserved.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import json
import re


def to_camel(attr):
    """convert this_attr_name to thisAttrName."""
    # Do lower case first letter
    return (attr[0].lower() +
            re.sub(r'_(.)', lambda x: x.group(1).upper(), attr[1:]))


def from_camel(attr):
    """convert thisAttrName to this_attr_name."""
    # Don't add an underscore for capitalized first letter
    return re.sub(r'(?<=.)([A-Z])', lambda x: '_' + x.group(1), attr).lower()


class Facet(object):
    def __init__(self, column, facet_type, **options):
        self.type = facet_type
        self.name = column
        self.column_name = column
        for k, v in options.items():
            setattr(self, k, v)

    def as_dict(self):
        return dict([(to_camel(k), v) for k, v in self.__dict__.items()
                     if v is not None])


class TextFilterFacet(Facet):
    def __init__(self, column, query, **options):
        super(TextFilterFacet, self).__init__(
            column, query=query, case_sensitive=False, facet_type='text',
            mode='text', **options)


class TextFacet(Facet):
    def __init__(self, column, selection=None, expression='value',
                 omit_blank=False, omit_error=False, select_blank=False,
                 select_error=False, invert=False, **options):
        super(TextFacet, self).__init__(
            column,
            facet_type='list',
            omit_blank=omit_blank,
            omit_error=omit_error,
            select_blank=select_blank,
            select_error=select_error,
            invert=invert,
            **options)
        self.expression = expression
        self.selection = []
        if selection is None:
            selection = []
        elif not isinstance(selection, list):
            selection = [selection]
        for value in selection:
            self.include(value)

    def include(self, value):
        for s in self.selection:
            if s['v']['v'] == value:
                return
        self.selection.append({'v': {'v': value, 'l': value}})
        return self

    def exclude(self, value):
        self.selection = [s for s in self.selection
                          if s['v']['v'] != value]
        return self

    def reset(self):
        self.selection = []
        return self


class BoolFacet(TextFacet):
    def __init__(self, column, expression=None, selection=None):
        if selection is not None and not isinstance(selection, bool):
            raise ValueError('selection must be True or False.')
        if expression is None:
            raise ValueError('Missing expression')
        super(BoolFacet, self).__init__(
            column, expression=expression, selection=selection)


class StarredFacet(BoolFacet):
    def __init__(self, selection=None):
        super(StarredFacet, self).__init__(
            '', expression='row.starred', selection=selection)


class FlaggedFacet(BoolFacet):
    def __init__(self, selection=None):
        super(FlaggedFacet, self).__init__(
            '', expression='row.flagged', selection=selection)


class BlankFacet(BoolFacet):
    def __init__(self, column, selection=None):
        super(BlankFacet, self).__init__(
            column, expression='isBlank(value)', selection=selection)


class ReconJudgmentFacet(TextFacet):
    def __init__(self, column, **options):
        super(ReconJudgmentFacet, self).__init__(
            column,
            expression=('forNonBlank(cell.recon.judgment, v, v, '
                        'if(isNonBlank(value), "(unreconciled)", "(blank)"))'),
            **options)


# Capitalize 'From' to get around python's reserved word.
#noinspection PyPep8Naming
class NumericFacet(Facet):
    def __init__(self, column, From=None, to=None, expression='value',
                 select_blank=True, select_error=True, select_non_numeric=True,
                 select_numeric=True, **options):
        super(NumericFacet, self).__init__(
            column,
            From=From,
            to=to,
            expression=expression,
            facet_type='range',
            select_blank=select_blank,
            select_error=select_error,
            select_non_numeric=select_non_numeric,
            select_numeric=select_numeric,
            **options)

    def reset(self):
        self.From = None
        self.to = None
        return self


class FacetResponse(object):
    """Class for unpacking an individual facet response."""
    def __init__(self, facet):
        self.name = None
        for k, v in facet.items():
            if isinstance(k, bool) or isinstance(k, basestring):
                setattr(self, from_camel(k), v)
        self.choices = {}

        class FacetChoice(object):
            def __init__(self, c):
                self.count = c['c']
                self.selected = c['s']

        if 'choices' in facet:
            for choice in facet['choices']:
                self.choices[choice['v']['v']] = FacetChoice(choice)
            if 'blankChoice' in facet:
                self.blank_choice = FacetChoice(facet['blankChoice'])
            else:
                self.blank_choice = None
        if 'bins' in facet:
            self.bins = facet['bins']
            self.base_bins = facet['baseBins']


class FacetsResponse(object):
    """FacetsResponse unpacking the compute-facets response.

    It has two attributes: facets & mode. Mode is either 'row-based' or
    'record-based'. facets is a list of facets produced by compute-facets, in
    the same order as they were specified in the Engine. By coupling the engine
    object with a custom container it's possible to look up the computed facet
    by the original facet's object.
    """
    def __init__(self, engine, facets):
        class FacetResponseContainer(object):
            facets = None

            def __init__(self, facet_responses):
                self.facets = [FacetResponse(fr) for fr in facet_responses]

            def __iter__(self):
                for facet in self.facets:
                    yield facet

            def __getitem__(self, index):
                if not isinstance(index, int):
                    index = engine.facet_index_by_id[id(index)]
                assert self.facets[index].name == engine.facets[index].name
                return self.facets[index]

        self.facets = FacetResponseContainer(facets['facets'])
        self.mode = facets['mode']


class Engine(object):
    """An Engine keeps track of Facets, and responses to facet computation."""

    def __init__(self, *facets, **kwargs):
        self.facets = []
        self.facet_index_by_id = {}  # dict of facets by Facet object id
        self.set_facets(*facets)
        self.mode = kwargs.get('mode', 'row-based')

    def set_facets(self, *facets):
        """facets may be a Facet or list of Facets."""
        self.remove_all()
        for facet in facets:
            self.add_facet(facet)

    def facets_response(self, response):
        """Unpack a compute-facets response."""
        return FacetsResponse(self, response)

    def __len__(self):
        return len(self.facets)

    def as_json(self):
        """Return a JSON string suitable for use as a POST parameter."""
        return json.dumps({
            'facets': [f.as_dict() for f in self.facets],  # XXX how with json?
            'mode': self.mode,
        })

    def add_facet(self, facet):
        # Record the facet's object id so facet response can be looked up by id
        self.facet_index_by_id[id(facet)] = len(self.facets)
        self.facets.append(facet)

    def remove_all(self):
        """Remove all facets."""
        self.facet_index_by_id = {}
        self.facets = []

    def reset_all(self):
        """Reset all facets."""
        for facet in self.facets:
            facet.reset()


class Sorting(object):
    """Class representing the current sorting order for a project.

    Used in RefineProject.get_rows()"""
    def __init__(self, criteria=None):
        self.criteria = []
        if criteria is None:
            criteria = []
        if not isinstance(criteria, list):
            criteria = [criteria]
        for criterion in criteria:
            # A string criterion defaults to a string sort on that column
            if isinstance(criterion, basestring):
                criterion = {
                    'column': criterion,
                    'valueType': 'string',
                    'caseSensitive': False,
                }
            criterion.setdefault('reverse', False)
            criterion.setdefault('errorPosition', 1)
            criterion.setdefault('blankPosition', 2)
            self.criteria.append(criterion)

    def as_json(self):
        return json.dumps({'criteria': self.criteria})

    def __len__(self):
        return len(self.criteria)

########NEW FILE########
__FILENAME__ = history
#!/usr/bin/env python
"""
OpenRefine history: parsing responses.
"""

# Copyright (c) 2011 Paul Makepeace, Real Programmers. All rights reserved.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>


class HistoryEntry(object):
    # N.B. e.g. **response['historyEntry'] won't work as keys are unicode :-/
    #noinspection PyUnusedLocal
    def __init__(self, history_entry_id=None, time=None, description=None, **kwargs):
        if history_entry_id is None:
            raise ValueError('History entry id must be set')
        self.id = history_entry_id
        self.description = description
        self.time = time

########NEW FILE########
__FILENAME__ = refine
#!/usr/bin/env python
"""
Client library to communicate with a Refine server.
"""

# Copyright (c) 2011 Paul Makepeace, Real Programmers. All rights reserved.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import csv
import json
import gzip
import os
import re
import StringIO
import time
import urllib
import urllib2_file
import urllib2
import urlparse

from google.refine import facet
from google.refine import history

REFINE_HOST = os.environ.get('OPENREFINE_HOST', os.environ.get('GOOGLE_REFINE_HOST', '127.0.0.1'))
REFINE_PORT = os.environ.get('OPENREFINE_PORT', os.environ.get('GOOGLE_REFINE_PORT', '3333'))


class RefineServer(object):
    """Communicate with a Refine server."""

    @staticmethod
    def url():
        """Return the URL to the Refine server."""
        server = 'http://' + REFINE_HOST
        if REFINE_PORT != '80':
            server += ':' + REFINE_PORT
        return server

    def __init__(self, server=None):
        if server is None:
            server = self.url()
        self.server = server[:-1] if server.endswith('/') else server
        self.__version = None     # see version @property below

    def urlopen(self, command, data=None, params=None, project_id=None):
        """Open a Refine URL and with optional query params and POST data.

        data: POST data dict
        param: query params dict
        project_id: project ID as string

        Returns urllib2.urlopen iterable."""
        url = self.server + '/command/core/' + command
        if data is None:
            data = {}
        if params is None:
            params = {}
        if project_id:
            # XXX haven't figured out pattern on qs v body
            if 'delete' in command or data:
                data['project'] = project_id
            else:
                params['project'] = project_id
        if params:
            url += '?' + urllib.urlencode(params)
        req = urllib2.Request(url)
        if data:
            req.add_data(data)  # data = urllib.urlencode(data)
        #req.add_header('Accept-Encoding', 'gzip')
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            raise Exception('HTTP %d "%s" for %s\n\t%s' % (e.code, e.msg, e.geturl(), data))
        except urllib2.URLError as e:
            raise urllib2.URLError(
                '%s for %s. No Refine server reachable/running; ENV set?' %
                (e.reason, self.server))
        if response.info().get('Content-Encoding', None) == 'gzip':
            # Need a seekable filestream for gzip
            gzip_fp = gzip.GzipFile(fileobj=StringIO.StringIO(response.read()))
            # XXX Monkey patch response's filehandle. Better way?
            urllib.addbase.__init__(response, gzip_fp)
        return response

    def urlopen_json(self, *args, **kwargs):
        """Open a Refine URL, optionally POST data, and return parsed JSON."""
        response = json.loads(self.urlopen(*args, **kwargs).read())
        if 'code' in response and response['code'] not in ('ok', 'pending'):
            error_message = ('server ' + response['code'] + ': ' +
                             response.get('message', response.get('stack', response)))
            raise Exception(error_message)
        return response

    def get_version(self):
        """Return version data.

        {"revision":"r1836","full_version":"2.0 [r1836]",
         "full_name":"Google Refine 2.0 [r1836]","version":"2.0"}"""
        return self.urlopen_json('get-version')

    @property
    def version(self):
        if self.__version is None:
            self.__version = self.get_version()['version']
        return self.__version


class Refine:
    """Class representing a connection to a Refine server."""
    def __init__(self, server):
        if isinstance(server, RefineServer):
            self.server = server
        else:
            self.server = RefineServer(server)

    def list_projects(self):
        """Return a dict of projects indexed by id.

        {u'1877818633188': {
            'id': u'1877818633188', u'name': u'akg',
            u'modified': u'2011-04-07T12:30:07Z',
            u'created': u'2011-04-07T12:30:07Z'
        },
        """
        # It's tempting to add in an index by name but there can be
        # projects with the same name.
        return self.server.urlopen_json('get-all-project-metadata')['projects']

    def get_project_name(self, project_id):
        """Returns project name given project_id."""
        projects = self.list_projects()
        return projects[project_id]['name']

    def open_project(self, project_id):
        """Open a Refine project."""
        return RefineProject(self.server, project_id)

    # These aren't used yet but are included for reference
    new_project_defaults = {
        'text/line-based/*sv': {
            'encoding': '',
            'separator': ',',
            'ignore_lines': -1,
            'header_lines': 1,
            'skip_data_lines': 0,
            'limit': -1,
            'store_blank_rows': True,
            'guess_cell_value_types': True,
            'process_quotes': True,
            'store_blank_cells_as_nulls': True,
            'include_file_sources': False},
        'text/line-based': {
            'encoding': '',
            'lines_per_row': 1,
            'ignore_lines': -1,
            'limit': -1,
            'skip_data_lines': -1,
            'store_blank_rows': True,
            'store_blank_cells_as_nulls': True,
            'include_file_sources': False},
        'text/line-based/fixed-width': {
            'encoding': '',
            'column_widths': [20],
            'ignore_lines': -1,
            'header_lines': 0,
            'skip_data_lines': 0,
            'limit': -1,
            'guess_cell_value_types': False,
            'store_blank_rows': True,
            'store_blank_cells_as_nulls': True,
            'include_file_sources': False},
        'text/line-based/pc-axis': {
            'encoding': '',
            'limit': -1,
            'skip_data_lines': -1,
            'include_file_sources': False},
        'text/rdf+n3': {'encoding': ''},
        'text/xml/ods': {
            'sheets': [],
            'ignore_lines': -1,
            'header_lines': 1,
            'skip_data_lines': 0,
            'limit': -1,
            'store_blank_rows': True,
            'store_blank_cells_as_nulls': True,
            'include_file_sources': False},
        'binary/xls': {
            'xml_based': False,
            'sheets': [],
            'ignore_lines': -1,
            'header_lines': 1,
            'skip_data_lines': 0,
            'limit': -1,
            'store_blank_rows': True,
            'store_blank_cells_as_nulls': True,
            'include_file_sources': False}
    }

    def new_project(self, project_file=None, project_url=None, project_name=None, project_format='text/line-based/*sv',
                    encoding='',
                    separator=',',
                    ignore_lines=-1,
                    header_lines=1,
                    skip_data_lines=0,
                    limit=-1,
                    store_blank_rows=True,
                    guess_cell_value_types=True,
                    process_quotes=True,
                    store_blank_cells_as_nulls=True,
                    include_file_sources=False,
                    **opts):

        if (project_file and project_url) or (not project_file and not project_url):
            raise ValueError('One (only) of project_file and project_url must be set')

        def s(opt):
            if isinstance(opt, bool):
                return 'true' if opt else 'false'
            if opt is None:
                return ''
            return str(opt)
        options = {
            'format': project_format,
            'encoding': s(encoding),
            'separator': s(separator),
            'ignore-lines': s(ignore_lines),
            'header-lines': s(header_lines),
            'skip-data-lines': s(skip_data_lines),
            'limit': s(limit),
            'guess-value-type': s(guess_cell_value_types),
            'process-quotes': s(process_quotes),
            'store-blank-rows': s(store_blank_rows),
            'store-blank-cells-as-nulls': s(store_blank_cells_as_nulls),
            'include-file-sources': s(include_file_sources),
        }

        if project_url is not None:
            options['url'] = project_url
        elif project_file is not None:
            options['project-file'] = {
                'fd': open(project_file),
                'filename': project_file,
            }
        if project_name is None:
            # make a name for itself by stripping extension and directories
            project_name = (project_file or 'New project').rsplit('.', 1)[0]
            project_name = os.path.basename(project_name)
        options['project-name'] = project_name
        response = self.server.urlopen('create-project-from-upload', options)
        # expecting a redirect to the new project containing the id in the url
        url_params = urlparse.parse_qs(
            urlparse.urlparse(response.geturl()).query)
        if 'project' in url_params:
            project_id = url_params['project'][0]
            return RefineProject(self.server, project_id)
        else:
            raise Exception('Project not created')


def RowsResponseFactory(column_index):
    """Factory for the parsing the output from get_rows().

    Uses the project's model's row cell index so that a row can be used
    as a dict by column name."""

    class RowsResponse(object):
        class RefineRows(object):
            class RefineRow(object):
                def __init__(self, row_response):
                    self.flagged = row_response['flagged']
                    self.starred = row_response['starred']
                    self.index = row_response['i']
                    self.row = [c['v'] if c else None
                                for c in row_response['cells']]

                def __getitem__(self, column):
                    # Trailing nulls seem to be stripped from row data
                    try:
                        return self.row[column_index[column]]
                    except IndexError:
                        return None

            def __init__(self, rows_response):
                self.rows_response = rows_response

            def __iter__(self):
                for row_response in self.rows_response:
                    yield self.RefineRow(row_response)

            def __getitem__(self, index):
                return self.RefineRow(self.rows_response[index])

            def __len__(self):
                return len(self.rows_response)

        def __init__(self, response):
            self.mode = response['mode']
            self.filtered = response['filtered']
            self.start = response['start']
            self.limit = response['limit']
            self.total = response['total']
            self.rows = self.RefineRows(response['rows'])

    return RowsResponse


class RefineProject:
    """An OpenRefine project."""

    def __init__(self, server, project_id=None):
        if not isinstance(server, RefineServer):
            if '/project?project=' in server:
                server, project_id = server.split('/project?project=')
                server = RefineServer(server)
            elif re.match(r'\d+$', server):     # just digits => project ID
                server, project_id = RefineServer(), server
            else:
                server = RefineServer(server)
        self.server = server
        if not project_id:
            raise Exception('Missing Refine project ID')
        self.project_id = project_id
        self.engine = facet.Engine()
        self.sorting = facet.Sorting()
        self.history_entry = None
        # following filled in by get_models()
        self.key_column = None
        self.has_records = False
        self.columns = None
        self.column_order = {}  # map of column names to order in UI
        self.rows_response_factory = None   # for parsing get_rows()
        self.get_models()
        # following filled in by get_reconciliation_services
        self.recon_services = None

    def project_name(self):
        return Refine(self.server).get_project_name(self.project_id)

    def project_url(self):
        """Return a URL to the project."""
        return '%s/project?project=%s' % (self.server.server, self.project_id)

    def do_raw(self, command, data):
        """Issue a command to the server & return a response object."""
        return self.server.urlopen(command, project_id=self.project_id,
                                   data=data)

    def do_json(self, command, data=None, include_engine=True):
        """Issue a command to the server, parse & return decoded JSON."""
        if include_engine:
            if data is None:
                data = {}
            data['engine'] = self.engine.as_json()
        response = self.server.urlopen_json(command,
                                            project_id=self.project_id,
                                            data=data)
        if 'historyEntry' in response:
            # **response['historyEntry'] won't work as keys are unicode :-/
            he = response['historyEntry']
            self.history_entry = history.HistoryEntry(he['id'], he['time'],
                                                      he['description'])
        return response

    def get_models(self):
        """Fill out column metadata.

        Column structure is a list of columns in their order.
        The cellIndex is an index for that column's data into the list returned
        from get_rows()."""
        response = self.do_json('get-models', include_engine=False)
        column_model = response['columnModel']
        column_index = {}   # map of column name to index into get_rows() data
        self.columns = [column['name'] for column in column_model['columns']]
        for i, column in enumerate(column_model['columns']):
            name = column['name']
            self.column_order[name] = i
            column_index[name] = column['cellIndex']
        self.key_column = column_model['keyColumnName']
        self.has_records = response['recordModel'].get('hasRecords', False)
        self.rows_response_factory = RowsResponseFactory(column_index)
        # TODO: implement rest
        return response

    def get_preference(self, name):
        """Returns the (JSON) value of a given preference setting."""
        response = self.server.urlopen_json('get-preference',
                                            params={'name': name})
        return json.loads(response['value'])

    def wait_until_idle(self, polling_delay=0.5):
        while True:
            response = self.do_json('get-processes', include_engine=False)
            if 'processes' in response and len(response['processes']) > 0:
                time.sleep(polling_delay)
            else:
                return

    def apply_operations(self, file_path, wait=True):
        json_data = open(file_path).read()
        response_json = self.do_json('apply-operations', {'operations': json_data})
        if response_json['code'] == 'pending' and wait:
            self.wait_until_idle()
            return 'ok'
        return response_json['code']  # can be 'ok' or 'pending'

    def export(self, export_format='tsv'):
        """Return a fileobject of a project's data."""
        url = ('export-rows/' + urllib.quote(self.project_name()) + '.' +
               export_format)
        return self.do_raw(url, data={'format': export_format})

    def export_rows(self, **kwargs):
        """Return an iterable of parsed rows of a project's data."""
        return csv.reader(self.export(**kwargs), dialect='excel-tab')

    def delete(self):
        response_json = self.do_json('delete-project', include_engine=False)
        return 'code' in response_json and response_json['code'] == 'ok'

    def compute_facets(self, facets=None):
        """Compute facets as per the project's engine.

        The response object has two attributes, mode & facets. mode is one of
        'row-based' or 'record-based'. facets is a magic list of facets in the
        same order as they were specified in the Engine. Magic allows the
        original Engine's facet as index into the response, e.g.,

        name_facet = TextFacet('name')
        response = project.compute_facets(name_facet)
        response.facets[name_facet]     # same as response.facets[0]
        """
        if facets:
            self.engine.set_facets(facets)
        response = self.do_json('compute-facets')
        return self.engine.facets_response(response)

    def get_rows(self, facets=None, sort_by=None, start=0, limit=10):
        if facets:
            self.engine.set_facets(facets)
        if sort_by is not None:
            self.sorting = facet.Sorting(sort_by)
        response = self.do_json('get-rows', {'sorting': self.sorting.as_json(),
                                             'start': start, 'limit': limit})
        return self.rows_response_factory(response)

    def reorder_rows(self, sort_by=None):
        if sort_by is not None:
            self.sorting = facet.Sorting(sort_by)
        response = self.do_json('reorder-rows',
                                {'sorting': self.sorting.as_json()})
        # clear sorting
        self.sorting = facet.Sorting()
        return response

    def remove_rows(self, facets=None):
        if facets:
            self.engine.set_facets(facets)
        return self.do_json('remove-rows')

    def text_transform(self, column, expression, on_error='set-to-blank',
                       repeat=False, repeat_count=10):
        response = self.do_json('text-transform', {
            'columnName': column, 'expression': expression,
            'onError': on_error, 'repeat': repeat,
            'repeatCount': repeat_count})
        return response

    def edit(self, column, edit_from, edit_to):
        edits = [{'from': [edit_from], 'to': edit_to}]
        return self.mass_edit(column, edits)

    def mass_edit(self, column, edits, expression='value'):
        """edits is [{'from': ['foo'], 'to': 'bar'}, {...}]"""
        edits = json.dumps(edits)
        response = self.do_json('mass-edit', {
            'columnName': column, 'expression': expression, 'edits': edits})
        return response

    clusterer_defaults = {
        'binning': {
            'type': 'binning',
            'function': 'fingerprint',
            'params': {},
        },
        'knn': {
            'type': 'knn',
            'function': 'levenshtein',
            'params': {
                'radius': 1,
                'blocking-ngram-size': 6,
            },
        },
    }

    def compute_clusters(self, column, clusterer_type='binning',
                         function=None, params=None):
        """Returns a list of clusters of {'value': ..., 'count': ...}."""
        clusterer = self.clusterer_defaults[clusterer_type]
        if params is not None:
            clusterer['params'] = params
        if function is not None:
            clusterer['function'] = function
        clusterer['column'] = column
        response = self.do_json('compute-clusters', {
            'clusterer': json.dumps(clusterer)})
        return [[{'value': x['v'], 'count': x['c']} for x in cluster]
                for cluster in response]

    def annotate_one_row(self, row, annotation, state=True):
        if annotation not in ('starred', 'flagged'):
            raise ValueError('annotation must be one of starred or flagged')
        state = 'true' if state is True else 'false'
        return self.do_json('annotate-one-row', {'row': row.index,
                                                 annotation: state})

    def flag_row(self, row, flagged=True):
        return self.annotate_one_row(row, 'flagged', flagged)

    def star_row(self, row, starred=True):
        return self.annotate_one_row(row, 'starred', starred)

    def add_column(self, column, new_column, expression='value',
                   column_insert_index=None, on_error='set-to-blank'):
        if column_insert_index is None:
            column_insert_index = self.column_order[column] + 1
        response = self.do_json('add-column', {
            'baseColumnName': column, 'newColumnName': new_column,
            'expression': expression, 'columnInsertIndex': column_insert_index,
            'onError': on_error})
        self.get_models()
        return response

    def split_column(self, column, separator=',', mode='separator',
                     regex=False, guess_cell_type=True,
                     remove_original_column=True):
        response = self.do_json('split-column', {
            'columnName': column, 'separator': separator, 'mode': mode,
            'regex': regex, 'guessCellType': guess_cell_type,
            'removeOriginalColumn': remove_original_column})
        self.get_models()
        return response

    def rename_column(self, column, new_column):
        response = self.do_json('rename-column', {'oldColumnName': column,
                                                  'newColumnName': new_column})
        self.get_models()
        return response

    def reorder_columns(self, new_column_order):
        """Takes an array of column names in the new order."""
        response = self.do_json('reorder-columns', {
            'columnNames': new_column_order})
        self.get_models()
        return response

    def move_column(self, column, index):
        """Move column to a new position."""
        if index == 'end':
            index = len(self.columns) - 1
        response = self.do_json('move-column', {'columnName': column,
                                                'index': index})
        self.get_models()
        return response

    def blank_down(self, column):
        response = self.do_json('blank-down', {'columnName': column})
        self.get_models()
        return response

    def fill_down(self, column):
        response = self.do_json('fill-down', {'columnName': column})
        self.get_models()
        return response

    def transpose_columns_into_rows(
            self, start_column, column_count,
            combined_column_name, separator=':', prepend_column_name=True,
            ignore_blank_cells=True):

        response = self.do_json('transpose-columns-into-rows', {
            'startColumnName': start_column, 'columnCount': column_count,
            'combinedColumnName': combined_column_name,
            'prependColumnName': prepend_column_name,
            'separator': separator, 'ignoreBlankCells': ignore_blank_cells})
        self.get_models()
        return response

    def transpose_rows_into_columns(self, column, row_count):
        response = self.do_json('transpose-rows-into-columns', {
            'columnName': column, 'rowCount': row_count})
        self.get_models()
        return response

    # Reconciliation
    # http://code.google.com/p/google-refine/wiki/ReconciliationServiceApi
    def guess_types_of_column(self, column, service):
        """Query the reconciliation service for what it thinks this column is.

        service: reconciliation endpoint URL

        Returns [
           {"id":"/domain/type","name":"Type Name","score":10.2,"count":18},
           ...
        ]
        """
        response = self.do_json('guess-types-of-column', {
            'columnName': column, 'service': service}, include_engine=False)
        return response['types']

    def get_reconciliation_services(self):
        response = self.get_preference('reconciliation.standardServices')
        self.recon_services = response
        return response

    def get_reconciliation_service_by_name_or_url(self, name):
        recon_services = self.get_reconciliation_services()
        for recon_service in recon_services:
            if recon_service['name'] == name or recon_service['url'] == name:
                return recon_service
        return None

    def reconcile(self, column, service, reconciliation_type=None,
                  reconciliation_config=None):
        """Perform a reconciliation asynchronously.

        config: {
            "mode": "standard-service",
            "service": "http://.../reconcile/",
            "identifierSpace": "http://.../ns/authority",
            "schemaSpace": "http://.../ns/type",
            "type": {
                "id": "/domain/type",
                "name": "Type Name"
            },
            "autoMatch": true,
            "columnDetails": []
        }

        Returns typically {'code': 'pending'}; call wait_until_idle() to wait
        for reconciliation to complete.
        """
        # Create a reconciliation config by looking up recon service info
        if reconciliation_config is None:
            service = self.get_reconciliation_service_by_name_or_url(service)
            if reconciliation_type is None:
                raise ValueError('Must have at least one of config or type')
            reconciliation_config = {
                'mode': 'standard-service',
                'service': service['url'],
                'identifierSpace': service['identifierSpace'],
                'schemaSpace': service['schemaSpace'],
                'type': {
                    'id': reconciliation_type['id'],
                    'name': reconciliation_type['name'],
                },
                'autoMatch': True,
                'columnDetails': [],
            }
        return self.do_json('reconcile', {
            'columnName': column, 'config': json.dumps(reconciliation_config)})

########NEW FILE########
__FILENAME__ = refine
#!/usr/bin/env python
"""
Script to provide a command line interface to a Refine server.

Examples,

refine --list    # show list of Refine projects, ID: name
refine --export 1234... > project.tsv
refine --export --output=project.xls 1234...
refine --apply trim.json 1234...
"""

# Copyright (c) 2011 Paul Makepeace, Real Programmers. All rights reserved.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>


import optparse
import os
import sys
import time

from google.refine import refine


PARSER = optparse.OptionParser(
    usage='usage: %prog [--help | OPTIONS] [project ID/URL]')
PARSER.add_option('-H', '--host', dest='host',
                  help='OpenRefine hostname')
PARSER.add_option('-P', '--port', dest='port',
                  help='OpenRefine port')
PARSER.add_option('-o', '--output', dest='output',
                  help='Output filename')
# Options that are more like commands
PARSER.add_option('-l', '--list', dest='list', action='store_true',
                  help='List projects')
PARSER.add_option('-E', '--export', dest='export', action='store_true',
                  help='Export project')
PARSER.add_option('-f', '--apply', dest='apply',
                  help='Apply a JSON commands file to a project')


def list_projects():
    """Query the Refine server and list projects by ID: name."""
    projects = refine.Refine(refine.RefineServer()).list_projects().items()

    def date_to_epoch(json_dt):
        """Convert a JSON date time into seconds-since-epoch."""
        return time.mktime(time.strptime(json_dt, '%Y-%m-%dT%H:%M:%SZ'))
    projects.sort(key=lambda v: date_to_epoch(v[1]['modified']), reverse=True)
    for project_id, project_info in projects:
        print('{0:>14}: {1}'.format(project_id, project_info['name']))


def export_project(project, options):
    """Dump a project to stdout or options.output file."""
    export_format = 'tsv'
    if options.output:
        ext = os.path.splitext(options.output)[1][1:]     # 'xls'
        if ext:
            export_format = ext.lower()
        output = open(options.output, 'wb')
    else:
        output = sys.stdout
    output.writelines(project.export(export_format=export_format))
    output.close()


#noinspection PyPep8Naming
def main():
    """Main."""
    options, args = PARSER.parse_args()

    if options.host:
        refine.REFINE_HOST = options.host
    if options.port:
        refine.REFINE_PORT = options.port

    if not options.list and len(args) != 1:
        PARSER.print_usage()
    if options.list:
        list_projects()
    if args:
        project = refine.RefineProject(args[0])
        if options.apply:
            response = project.apply_operations(options.apply)
            if response != 'ok':
                print >>sys.stderr, 'Failed to apply %s: %s' % (options.apply,
                                                                response)
        if options.export:
            export_project(project, options)

        return project

if __name__ == '__main__':
    # return project so that it's available interactively, python -i refine.py
    refine_project = main()

########NEW FILE########
__FILENAME__ = refinetest
#!/usr/bin/env python
"""
refinetest.py

RefineTestCase is a base class that loads Refine projects specified by
the class's 'project_file' attribute and provides a 'project' object.

These tests require a connection to a Refine server either at
http://127.0.0.1:3333/ or by specifying environment variables REFINE_HOST
and REFINE_PORT.
"""

# Copyright (c) 2011 Paul Makepeace, Real Programmers. All rights reserved.

import os
import unittest

from google.refine import refine

PATH_TO_TEST_DATA = os.path.join(os.path.dirname(__file__), 'data')


#noinspection PyPep8Naming
class RefineTestCase(unittest.TestCase):
    project_file = None
    project_format = 'text/line-based/*sv'
    project_options = {}
    project = None
    # Section "2. Exploration using Facets": {1}, {2}

    def project_path(self):
        return os.path.join(PATH_TO_TEST_DATA, self.project_file)

    def setUp(self):
        self.server = refine.RefineServer()
        self.refine = refine.Refine(self.server)
        if self.project_file:
            self.project = self.refine.new_project(
                project_file=self.project_path(), project_format=self.project_format, **self.project_options)

    def tearDown(self):
        if self.project:
            self.project.delete()
            self.project = None

    def assertInResponse(self, expect):
        desc = None
        try:
            desc = self.project.history_entry.description
            self.assertTrue(expect in desc)
        except AssertionError:
            raise AssertionError('Expecting "%s" in "%s"' % (expect, desc))

########NEW FILE########
__FILENAME__ = test_facet
#!/usr/bin/env python
"""
test_facet.py
"""

# Copyright (c) 2011 Paul Makepeace, Real Programmers. All rights reserved.

import json
import unittest

from google.refine.facet import *


class CamelTest(unittest.TestCase):
    def test_to_camel(self):
        pairs = (
            ('this', 'this'),
            ('this_attr', 'thisAttr'),
            ('From', 'from'),
        )
        for attr, camel_attr in pairs:
            self.assertEqual(to_camel(attr), camel_attr)

    def test_from_camel(self):
        pairs = (
            ('this', 'this'),
            ('This', 'this'),
            ('thisAttr', 'this_attr'),
            ('ThisAttr', 'this_attr'),
            ('From', 'from'),
        )
        for camel_attr, attr in pairs:
            self.assertEqual(from_camel(camel_attr), attr)


class FacetTest(unittest.TestCase):
    def test_init(self):
        facet = TextFacet('column name')
        engine = Engine(facet)
        self.assertEqual(facet.selection, [])
        self.assertTrue(str(engine))
        facet = NumericFacet('column name', From=1, to=5)
        self.assertEqual(facet.to, 5)
        self.assertEqual(facet.From, 1)
        facet = StarredFacet()
        self.assertEqual(facet.expression, 'row.starred')
        facet = StarredFacet(True)
        self.assertEqual(facet.selection[0]['v']['v'], True)
        facet = FlaggedFacet(False)
        self.assertEqual(facet.selection[0]['v']['v'], False)
        self.assertRaises(ValueError, FlaggedFacet, 'false')    # no strings
        facet = TextFilterFacet('column name', 'query')
        self.assertEqual(facet.query, 'query')

    def test_selections(self):
        facet = TextFacet('column name')
        facet.include('element')
        self.assertEqual(len(facet.selection), 1)
        facet.include('element 2')
        self.assertEqual(len(facet.selection), 2)
        facet.exclude('element')
        self.assertEqual(len(facet.selection), 1)
        facet.reset()
        self.assertEqual(len(facet.selection), 0)
        facet.include('element').include('element 2')
        self.assertEqual(len(facet.selection), 2)


class EngineTest(unittest.TestCase):
    def test_init(self):
        engine = Engine()
        self.assertEqual(engine.mode, 'row-based')
        engine.mode = 'record-based'
        self.assertEqual(engine.mode, 'record-based')
        engine.set_facets(BlankFacet)
        self.assertEqual(engine.mode, 'record-based')
        engine.set_facets(BlankFacet, BlankFacet)
        self.assertEqual(len(engine), 2)

    def test_serialize(self):
        engine = Engine()
        engine_json = engine.as_json()
        self.assertEqual(engine_json, '{"facets": [], "mode": "row-based"}')
        facet = TextFacet(column='column')
        self.assertEqual(facet.as_dict(), {'selectError': False, 'name': 'column', 'selection': [], 'expression': 'value', 'invert': False, 'columnName': 'column', 'selectBlank': False, 'omitBlank': False, 'type': 'list', 'omitError': False})
        facet = NumericFacet(column='column', From=1, to=5)
        self.assertEqual(facet.as_dict(), {'from': 1, 'to': 5, 'selectBlank': True, 'name': 'column', 'selectError': True, 'expression': 'value',  'selectNumeric': True, 'columnName': 'column', 'selectNonNumeric': True, 'type': 'range'})

    def test_add_facet(self):
        facet = TextFacet(column='Party Code')
        engine = Engine(facet)
        engine.add_facet(TextFacet(column='Ethnicity'))
        self.assertEqual(len(engine.facets), 2)
        self.assertEqual(len(engine), 2)

    def test_reset_remove(self):
        text_facet1 = TextFacet('column name')
        text_facet1.include('element')
        text_facet2 = TextFacet('column name 2')
        text_facet2.include('element 2')
        engine = Engine(text_facet1, text_facet2)
        self.assertEqual(len(engine), 2)
        self.assertEqual(len(text_facet1.selection), 1)
        engine.reset_all()
        self.assertEqual(len(text_facet1.selection), 0)
        self.assertEqual(len(text_facet2.selection), 0)
        engine.remove_all()
        self.assertEqual(len(engine), 0)


class SortingTest(unittest.TestCase):
    def test_sorting(self):
        sorting = Sorting()
        self.assertEqual(sorting.as_json(), '{"criteria": []}')
        sorting = Sorting('email')
        c = sorting.criteria[0]
        self.assertEqual(c['column'], 'email')
        self.assertEqual(c['valueType'], 'string')
        self.assertEqual(c['reverse'], False)
        self.assertEqual(c['caseSensitive'], False)
        self.assertEqual(c['errorPosition'], 1)
        self.assertEqual(c['blankPosition'], 2)
        sorting = Sorting(['email', 'gender'])
        self.assertEqual(len(sorting), 2)
        sorting = Sorting(['email', {'column': 'date', 'valueType': 'date'}])
        self.assertEqual(len(sorting), 2)
        c = sorting.criteria[1]
        self.assertEqual(c['column'], 'date')
        self.assertEqual(c['valueType'], 'date')


class FacetsResponseTest(unittest.TestCase):
    response = """{"facets":[{"name":"Party Code","expression":"value","columnName":"Party Code","invert":false,"choices":[{"v":{"v":"D","l":"D"},"c":3700,"s":false},{"v":{"v":"R","l":"R"},"c":1613,"s":false},{"v":{"v":"N","l":"N"},"c":15,"s":false},{"v":{"v":"O","l":"O"},"c":184,"s":false}],"blankChoice":{"s":false,"c":1446}}],"mode":"row-based"}"""

    def test_facet_response(self):
        party_code_facet = TextFacet('Party Code')
        engine = Engine(party_code_facet)
        facets = engine.facets_response(json.loads(self.response)).facets
        self.assertEqual(facets[0].choices['D'].count, 3700)
        self.assertEqual(facets[0].blank_choice.count, 1446)
        self.assertEqual(facets[party_code_facet], facets[0])
        # test iteration
        facet = [f for f in facets][0]
        self.assertEqual(facet, facets[0])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_history
#!/usr/bin/env python
"""
test_history.py
"""

# Copyright (c) 2011 Paul Makepeace, Real Programmers. All rights reserved.

import unittest

from google.refine.history import *


class HistoryTest(unittest.TestCase):
    def test_init(self):
        response = {
            u"code": "ok",
            u"historyEntry": {
                u"id": 1303851435223,
                u"description": "Split 4 cells",
                u"time": "2011-04-26T16:45:08Z"
            }
        }
        he = response['historyEntry']
        entry = HistoryEntry(he['id'], he['time'], he['description'])
        self.assertEqual(entry.id, 1303851435223)
        self.assertEqual(entry.description, 'Split 4 cells')
        self.assertEqual(entry.time, '2011-04-26T16:45:08Z')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_refine
#!/usr/bin/env python
"""
test_refine.py

These tests require a connection to a Refine server either at
http://127.0.0.1:3333/ or by specifying environment variables
OPENREFINE_HOST and OPENREFINE_PORT.
"""

# Copyright (c) 2011 Paul Makepeace, Real Programmers. All rights reserved.

import csv
import unittest

from google.refine import refine
from tests import refinetest


class RefineServerTest(refinetest.RefineTestCase):
    def test_init(self):
        server_url = 'http://' + refine.REFINE_HOST
        if refine.REFINE_PORT != '80':
            server_url += ':' + refine.REFINE_PORT
        self.assertEqual(self.server.server, server_url)
        self.assertEqual(refine.RefineServer.url(), server_url)
        # strip trailing /
        server = refine.RefineServer('http://refine.example/')
        self.assertEqual(server.server, 'http://refine.example')

    def test_list_projects(self):
        projects = self.refine.list_projects()
        self.assertTrue(isinstance(projects, dict))

    def test_get_version(self):
        version_info = self.server.get_version()
        for item in ('revision', 'version', 'full_version', 'full_name'):
            self.assertTrue(item in version_info)

    def test_version(self):
        self.assertTrue(self.server.version in ('2.0', '2.1', '2.5'))


class RefineTest(refinetest.RefineTestCase):
    project_file = 'duplicates.csv'

    def test_new_project(self):
        self.assertTrue(isinstance(self.project, refine.RefineProject))

    def test_wait_until_idle(self):
        self.project.wait_until_idle()  # should just return

    def test_get_models(self):
        self.assertEqual(self.project.key_column, 'email')
        self.assertTrue('email' in self.project.columns)
        self.assertTrue('email' in self.project.column_order)
        self.assertEqual(self.project.column_order['name'], 1)

    def test_delete_project(self):
        self.assertTrue(self.project.delete())

    def test_open_export(self):
        fp = refine.RefineProject(self.project.project_url()).export()
        line = fp.next()
        self.assertTrue('email' in line)
        for line in fp:
            self.assertTrue('M' in line or 'F' in line)
        fp.close()

    def test_open_export_csv(self):
        fp = refine.RefineProject(self.project.project_url()).export()
        csv_fp = csv.reader(fp, dialect='excel-tab')
        row = csv_fp.next()
        self.assertTrue(row[0] == 'email')
        for row in csv_fp:
            self.assertTrue(row[3] == 'F' or row[3] == 'M')
        fp.close()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_refine_small
#!/usr/bin/env python
"""
test_refine_small.py
"""

# Copyright (c) 2011 Paul Makepeace, Real Programmers. All rights reserved.

import unittest

from google.refine import refine


class RefineRowsTest(unittest.TestCase):
    def test_rows_response(self):
        rr = refine.RowsResponseFactory({
            u'gender': 3, u'state': 2, u'purchase': 4, u'email': 0,
            u'name': 1})
        response = rr({
            u'rows': [{
                u'i': 0,
                u'cells': [
                    {u'v': u'danny.baron@example1.com'},
                    {u'v': u'Danny Baron'},
                    {u'v': u'CA'},
                    {u'v': u'M'},
                    {u'v': u'TV'}
                ],
                u'starred': False,
                u'flagged': False
            }],
            u'start': 0,
            u'limit': 1,
            u'mode': u'row-based',
            u'filtered': 10,
            u'total': 10,
        })
        self.assertEqual(len(response.rows), 1)
        # test iteration
        rows = [row for row in response.rows]
        self.assertEqual(rows[0]['name'], 'Danny Baron')
        # test indexing
        self.assertEqual(response.rows[0]['name'], 'Danny Baron')


class RefineProjectTest(unittest.TestCase):
    def setUp(self):
        # Mock out get_models so it doesn't attempt to connect to a server
        self._get_models = refine.RefineProject.get_models
        refine.RefineProject.get_models = lambda me: me
        # Save REFINE_{HOST,PORT} as tests overwrite it
        self._refine_host_port = refine.REFINE_HOST, refine.REFINE_PORT
        refine.REFINE_HOST, refine.REFINE_PORT = '127.0.0.1', '3333'

    def test_server_init(self):
        RP = refine.RefineProject
        p = RP('http://127.0.0.1:3333/project?project=1658955153749')
        self.assertEqual(p.server.server, 'http://127.0.0.1:3333')
        self.assertEqual(p.project_id, '1658955153749')
        p = RP('http://127.0.0.1:3333', '1658955153749')
        self.assertEqual(p.server.server, 'http://127.0.0.1:3333')
        self.assertEqual(p.project_id, '1658955153749')
        p = RP('http://server/varnish/project?project=1658955153749')
        self.assertEqual(p.server.server, 'http://server/varnish')
        self.assertEqual(p.project_id, '1658955153749')
        p = RP('1658955153749')
        self.assertEqual(p.server.server, 'http://127.0.0.1:3333')
        self.assertEqual(p.project_id, '1658955153749')
        refine.REFINE_HOST = '10.0.0.1'
        refine.REFINE_PORT = '80'
        p = RP('1658955153749')
        self.assertEqual(p.server.server, 'http://10.0.0.1')

    def tearDown(self):
        # Restore mocked get_models
        refine.RefineProject.get_models = self._get_models
        # Restore values for REFINE_{HOST,PORT}
        refine.REFINE_HOST, refine.REFINE_PORT = self._refine_host_port


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_tutorial
#!/usr/bin/env python
"""
test_tutorial.py

The tests here are based on David Huynh's Refine tutorial at
http://davidhuynh.net/spaces/nicar2011/tutorial.pdf The tests perform all the
Refine actions given in the tutorial (except the web scraping) and verify the
changes expected to be observed explained in the tutorial.

These tests require a connection to a Refine server either at
http://127.0.0.1:3333/ or by specifying environment variables
OPENREFINE_HOST and OPENREFINE_PORT.
"""

# Copyright (c) 2011 Paul Makepeace, Real Programmers. All rights reserved.

import unittest

from google.refine import facet
from tests import refinetest


class TutorialTestFacets(refinetest.RefineTestCase):
    project_file = 'louisiana-elected-officials.csv'
    project_options = {'guess_cell_value_types': True}

    def test_get_rows(self):
        # Section "2. Exploration using Facets": {3}
        response = self.project.get_rows(limit=10)
        self.assertEqual(len(response.rows), 10)
        self.assertEqual(response.limit, 10)
        self.assertEqual(response.total, 6958)
        self.assertEqual(response.filtered, 6958)
        for row in response.rows:
            self.assertFalse(row.flagged)
            self.assertFalse(row.starred)

    def test_facet(self):
        # Section "2. Exploration using Facets": {4}
        party_code_facet = facet.TextFacet(column='Party Code')
        response = self.project.compute_facets(party_code_facet)
        pc = response.facets[0]
        # test look by index same as look up by facet object
        self.assertEqual(pc, response.facets[party_code_facet])
        self.assertEqual(pc.name, 'Party Code')
        self.assertEqual(pc.choices['D'].count, 3700)
        self.assertEqual(pc.choices['N'].count, 15)
        self.assertEqual(pc.blank_choice.count, 1446)
        # {5}, {6}
        engine = facet.Engine(party_code_facet)
        ethnicity_facet = facet.TextFacet(column='Ethnicity')
        engine.add_facet(ethnicity_facet)
        self.project.engine = engine
        response = self.project.compute_facets()
        e = response.facets[ethnicity_facet]
        self.assertEqual(e.choices['B'].count, 1255)
        self.assertEqual(e.choices['W'].count, 4469)
        # {7}
        ethnicity_facet.include('B')
        response = self.project.get_rows()
        self.assertEqual(response.filtered, 1255)
        indexes = [row.index for row in response.rows]
        self.assertEqual(indexes, [1, 2, 3, 4, 6, 12, 18, 26, 28, 32])
        # {8}
        response = self.project.compute_facets()
        pc = response.facets[party_code_facet]
        self.assertEqual(pc.name, 'Party Code')
        self.assertEqual(pc.choices['D'].count, 1179)
        self.assertEqual(pc.choices['R'].count, 11)
        self.assertEqual(pc.blank_choice.count, 46)
        # {9}
        party_code_facet.include('R')
        response = self.project.compute_facets()
        e = response.facets[ethnicity_facet]
        self.assertEqual(e.choices['B'].count, 11)
        # {10}
        party_code_facet.reset()
        ethnicity_facet.reset()
        response = self.project.get_rows()
        self.assertEqual(response.filtered, 6958)
        # {11}
        office_title_facet = facet.TextFacet('Office Title')
        self.project.engine.add_facet(office_title_facet)
        response = self.project.compute_facets()
        self.assertEqual(len(response.facets[2].choices), 76)
        # {12} - XXX not sure how to interpret bins & baseBins yet
        office_level_facet = facet.NumericFacet('Office Level')
        self.project.engine.add_facet(office_level_facet)
        # {13}
        office_level_facet.From = 300   # from reserved word
        office_level_facet.to = 320
        response = self.project.get_rows()
        self.assertEqual(response.filtered, 1907)
        response = self.project.compute_facets()
        ot = response.facets[office_title_facet]
        self.assertEqual(len(ot.choices), 21)
        self.assertEqual(ot.choices['Chief of Police'].count, 2)
        self.assertEqual(ot.choices['Chief of Police          '].count, 211)
        # {14}
        self.project.engine.remove_all()
        response = self.project.get_rows()
        self.assertEqual(response.filtered, 6958)
        # {15}
        phone_facet = facet.TextFacet('Phone', expression='value[0, 3]')
        self.project.engine.add_facet(phone_facet)
        response = self.project.compute_facets()
        p = response.facets[phone_facet]
        self.assertEqual(p.expression, 'value[0, 3]')
        self.assertEqual(p.choices['318'].count, 2331)
        # {16}
        commissioned_date_facet = facet.NumericFacet(
            'Commissioned Date',
            expression='value.toDate().datePart("year")')
        self.project.engine.add_facet(commissioned_date_facet)
        response = self.project.compute_facets()
        cd = response.facets[commissioned_date_facet]
        self.assertEqual(cd.error_count, 959)
        self.assertEqual(cd.numeric_count, 5999)
        # {17}
        office_description_facet = facet.NumericFacet(
            'Office Description',
            expression=r'value.match(/\D*(\d+)\w\w Rep.*/)[0].toNumber()')
        self.project.engine.add_facet(office_description_facet)
        response = self.project.compute_facets()
        od = response.facets[office_description_facet]
        self.assertEqual(od.min, 0)
        self.assertEqual(od.max, 110)
        self.assertEqual(od.numeric_count, 548)


class TutorialTestEditing(refinetest.RefineTestCase):
    project_file = 'louisiana-elected-officials.csv'
    project_options = {'guess_cell_value_types': True}

    def test_editing(self):
        # Section "3. Cell Editing": {1}
        self.project.engine.remove_all()    # redundant due to setUp
        # {2}
        self.project.text_transform(column='Zip Code 2',
                                    expression='value.toString()[0, 5]')
        self.assertInResponse('transform on 6067 cells in column Zip Code 2')
        # {3} - XXX history
        # {4}
        office_title_facet = facet.TextFacet('Office Title')
        self.project.engine.add_facet(office_title_facet)
        response = self.project.compute_facets()
        self.assertEqual(len(response.facets[office_title_facet].choices), 76)
        self.project.text_transform('Office Title', 'value.trim()')
        self.assertInResponse('6895')
        response = self.project.compute_facets()
        self.assertEqual(len(response.facets[office_title_facet].choices), 67)
        # {5}
        self.project.edit('Office Title', 'Councilmen', 'Councilman')
        self.assertInResponse('13')
        response = self.project.compute_facets()
        self.assertEqual(len(response.facets[office_title_facet].choices), 66)
        # {6}
        response = self.project.compute_clusters('Office Title')
        self.assertTrue(not response)
        # {7}
        clusters = self.project.compute_clusters('Office Title', 'knn')
        self.assertEqual(len(clusters), 7)
        first_cluster = clusters[0]
        self.assertEqual(len(first_cluster), 2)
        self.assertEqual(first_cluster[0]['value'], 'RSCC Member')
        self.assertEqual(first_cluster[0]['count'], 233)
        # Not strictly necessary to repeat 'Council Member' but a test
        # of mass_edit, and it's also what the front end sends.
        self.project.mass_edit('Office Title', [{
            'from': ['Council Member', 'Councilmember'],
            'to': 'Council Member'
        }])
        self.assertInResponse('372')
        response = self.project.compute_facets()
        self.assertEqual(len(response.facets[office_title_facet].choices), 65)

        # Section "4. Row and Column Editing, Batched Row Deletion"
        # Test doesn't strictly follow the tutorial as the "Browse this
        # cluster" performs a text facet which the server can't complete
        # as it busts its max facet count. The useful work is done with
        # get_rows(). Also, we can facet & select in one; the UI can't.
        # {1}, {2}, {3}, {4}
        clusters = self.project.compute_clusters('Candidate Name')
        for cluster in clusters[0:3]:   # just do a few
            for match in cluster:
                # {2}
                if match['value'].endswith(', '):
                    response = self.project.get_rows(
                        facet.TextFacet('Candidate Name', match['value']))
                    self.assertEqual(len(response.rows), 1)
                    for row in response.rows:
                        self.project.star_row(row)
                        self.assertInResponse(str(row.index + 1))
        # {5}, {6}, {7}
        response = self.project.compute_facets(facet.StarredFacet(True))
        self.assertEqual(len(response.facets[0].choices), 2)    # true & false
        self.assertEqual(response.facets[0].choices[True].count, 3)
        self.project.remove_rows()
        self.assertInResponse('3 rows')


class TutorialTestDuplicateDetection(refinetest.RefineTestCase):
    project_file = 'duplicates.csv'

    def test_duplicate_detection(self):
        # Section "4. Row and Column Editing,
        #             Duplicate Row Detection and Deletion"
        # {7}, {8}
        response = self.project.get_rows(sort_by='email')
        indexes = [row.index for row in response.rows]
        self.assertEqual(indexes, [4, 9, 8, 3, 0, 2, 5, 6, 1, 7])
        # {9}
        self.project.reorder_rows()
        self.assertInResponse('Reorder rows')
        response = self.project.get_rows()
        indexes = [row.index for row in response.rows]
        self.assertEqual(indexes, range(10))
        # {10}
        self.project.add_column(
            'email', 'count', 'facetCount(value, "value", "email")')
        self.assertInResponse('column email by filling 10 rows')
        response = self.project.get_rows()
        self.assertEqual(self.project.column_order['email'], 0)  # i.e. 1st
        self.assertEqual(self.project.column_order['count'], 1)  # i.e. 2nd
        counts = [row['count'] for row in response.rows]
        self.assertEqual(counts, [2, 2, 1, 1, 3, 3, 3, 1, 2, 2])
        # {11}
        self.assertFalse(self.project.has_records)
        self.project.blank_down('email')
        self.assertInResponse('Blank down 4 cells')
        self.assertTrue(self.project.has_records)
        response = self.project.get_rows()
        emails = [1 if row['email'] else 0 for row in response.rows]
        self.assertEqual(emails, [1, 0, 1, 1, 1, 0, 0, 1, 1, 0])
        # {12}
        blank_facet = facet.BlankFacet('email', selection=True)
        # {13}
        self.project.remove_rows(blank_facet)
        self.assertInResponse('Remove 4 rows')
        self.project.engine.remove_all()
        response = self.project.get_rows()
        email_counts = [(row['email'], row['count']) for row in response.rows]
        self.assertEqual(email_counts, [
            (u'arthur.duff@example4.com', 2),
            (u'ben.morisson@example6.org', 1),
            (u'ben.tyler@example3.org', 1),
            (u'danny.baron@example1.com', 3),
            (u'jean.griffith@example5.org', 1),
            (u'melanie.white@example2.edu', 2)
        ])


class TutorialTestTransposeColumnsIntoRows(refinetest.RefineTestCase):
    project_file = 'us_economic_assistance.csv'

    def test_transpose_columns_into_rows(self):
        # Section "5. Structural Editing, Transpose Columns into Rows"
        # {1}, {2}, {3}
        self.project.transpose_columns_into_rows('FY1946', 64, 'pair')
        self.assertInResponse('64 column(s) starting with FY1946')
        # {4}
        self.project.add_column('pair', 'year', 'value[2,6].toNumber()')
        self.assertInResponse('filling 26185 rows')
        # {5}
        self.project.text_transform(
            column='pair', expression='value.substring(7).toNumber()')
        self.assertInResponse('transform on 26185 cells')
        # {6}
        self.project.rename_column('pair', 'amount')
        self.assertInResponse('Rename column pair to amount')
        # {7}
        self.project.fill_down('country_name')
        self.assertInResponse('Fill down 23805 cells')
        self.project.fill_down('program_name')
        self.assertInResponse('Fill down 23805 cells')
        # spot check of last row for transforms and fill down
        response = self.project.get_rows()
        row10 = response.rows[9]
        self.assertEqual(row10['country_name'], 'Afghanistan')
        self.assertEqual(row10['program_name'],
                         'Department of Defense Security Assistance')
        self.assertEqual(row10['amount'], 113777303)


class TutorialTestTransposeFixedNumberOfRowsIntoColumns(
        refinetest.RefineTestCase):
    project_file = 'fixed-rows.csv'
    project_format = 'text/line-based'
    project_options = {'header_lines': 0}

    def test_transpose_fixed_number_of_rows_into_columns(self):
        if self.server.version not in ('2.0', '2.1'):
            self.project.rename_column('Column 1', 'Column')
        # Section "5. Structural Editing,
        #             Transpose Fixed Number of Rows into Columns"
        # {1}
        self.assertTrue('Column' in self.project.column_order)
        # {8}
        self.project.transpose_rows_into_columns('Column', 4)
        self.assertInResponse('Transpose every 4 cells in column Column')
        # {9} - renaming column triggers a bug in Refine <= 2.1
        if self.server.version not in ('2.0', '2.1'):
            self.project.rename_column('Column 2', 'Address')
            self.project.rename_column('Column 3', 'Address 2')
            self.project.rename_column('Column 4', 'Status')
        # {10}
        self.project.add_column(
            'Column 1', 'Transaction',
            'if(value.contains(" sent "), "send", "receive")')
        self.assertInResponse('Column 1 by filling 4 rows')
        # {11}
        transaction_facet = facet.TextFacet(column='Transaction',
                                            selection='send')
        self.project.engine.add_facet(transaction_facet)
        self.project.compute_facets()
        # {12}, {13}, {14}
        self.project.add_column(
            'Column 1', 'Sender',
            'value.partition(" sent ")[0]')
        # XXX resetting the facet shows data in rows with Transaction=receive
        #     which shouldn't have been possible with the facet.
        self.project.add_column(
            'Column 1', 'Recipient',
            'value.partition(" to ")[2].partition(" on ")[0]')
        self.project.add_column(
            'Column 1', 'Amount',
            'value.partition(" sent ")[2].partition(" to ")[0]')
        # {15}
        transaction_facet.reset().include('receive')
        self.project.get_rows()
        # XXX there seems to be some kind of bug where the model doesn't
        #     match get_rows() output - cellIndex being returned that are
        #     out of range.
        #self.assertTrue(a_row['Sender'] is None)
        #self.assertTrue(a_row['Recipient'] is None)
        #self.assertTrue(a_row['Amount'] is None)
        # {16}
        for column, expression in (
            ('Sender',
             'cells["Column 1"].value.partition(" from ")[2].partition(" on ")[0]'),
            ('Recipient',
             'cells["Column 1"].value.partition(" received ")[0]'),
            ('Amount',
             'cells["Column 1"].value.partition(" received ")[2].partition(" from ")[0]')
        ):
            self.project.text_transform(column, expression)
            self.assertInResponse('2 cells')
        # {17}
        transaction_facet.reset()
        # {18}
        self.project.text_transform('Column 1', 'value.partition(" on ")[2]')
        self.assertInResponse('4 cells')
        # {19}
        self.project.reorder_columns(['Transaction', 'Amount', 'Sender',
                                      'Recipient'])
        self.assertInResponse('Reorder columns')


class TutorialTestTransposeVariableNumberOfRowsIntoColumns(
        refinetest.RefineTestCase):
    project_file = 'variable-rows.csv'
    project_format = 'text/line-based'
    project_options = {'header_lines': 0}

    def test_transpose_variable_number_of_rows_into_columns(self):
        # {20}, {21}
        if self.server.version not in ('2.0', '2.1') :
            self.project.rename_column('Column 1', 'Column')
        self.project.add_column(
            'Column', 'First Line', 'if(value.contains(" on "), value, null)')
        self.assertInResponse('Column by filling 4 rows')
        response = self.project.get_rows()
        first_names = [row['First Line'][0:10] if row['First Line'] else None
                       for row in response.rows]
        self.assertEqual(first_names, [
            'Tom Dalton', None, None, None,
            'Morgan Law', None, None, None, None, 'Eric Batem'])
        # {22}
        self.project.move_column('First Line', 0)
        self.assertInResponse('Move column First Line to position 0')
        self.assertEqual(self.project.column_order['First Line'], 0)
        # {23}
        self.project.engine.mode = 'record-based'
        response = self.project.get_rows()
        self.assertEqual(response.mode, 'record-based')
        self.assertEqual(response.filtered, 4)
        # {24}
        self.project.add_column(
            'Column', 'Status', 'row.record.cells["Column"].value[-1]')
        self.assertInResponse('filling 18 rows')
        # {25}
        self.project.text_transform(
            'Column', 'row.record.cells["Column"].value[1, -1].join("|")')
        self.assertInResponse('18 cells')
        # {26}
        self.project.engine.mode = 'row-based'
        # {27}
        blank_facet = facet.BlankFacet('First Line', selection=True)
        self.project.remove_rows(blank_facet)
        self.assertInResponse('Remove 14 rows')
        self.project.engine.remove_all()
        # {28}
        self.project.split_column('Column', separator='|')
        self.assertInResponse('Split 4 cell(s) in column Column')


class TutorialTestWebScraping(refinetest.RefineTestCase):
    project_file = 'eli-lilly.csv'

    filter_expr_1 = """
        forEach(
            value[2,-2].replace("&#160;", " ").split("), ("),
            v,
            v[0,-1].partition(", '", true).join(":")
        ).join("|")
    """
    filter_expr_2 = """
        filter(
            value.split("|"), p, p.partition(":")[0].toNumber() == %d
        )[0].partition(":")[2]
    """

    def test_web_scraping(self):
        # Section "6. Web Scraping"
        # {1}, {2}
        self.project.split_column('key', separator=':')
        self.assertInResponse('Split 5409 cell(s) in column key')
        self.project.rename_column('key 1', 'page')
        self.assertInResponse('Rename column key 1 to page')
        self.project.rename_column('key 2', 'top')
        self.assertInResponse('Rename column key 2 to top')
        self.project.move_column('line', 'end')
        self.assertInResponse('Move column line to position 2')
        # {3}
        self.project.sorting = facet.Sorting([
            {'column': 'page', 'valueType': 'number'},
            {'column': 'top',  'valueType': 'number'},
        ])
        self.project.reorder_rows()
        self.assertInResponse('Reorder rows')
        first_row = self.project.get_rows(limit=1).rows[0]
        self.assertEqual(first_row['page'], 1)
        self.assertEqual(first_row['top'], 24)
        # {4}
        filter_facet = facet.TextFilterFacet('line', 'ahman')
        rows = self.project.get_rows(filter_facet).rows
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['top'], 106)
        filter_facet.query = 'alvarez'
        rows = self.project.get_rows().rows
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[-1]['top'], 567)
        self.project.engine.remove_all()
        # {5} - tutorial says 'line'; it means 'top'
        line_facet = facet.NumericFacet('top')
        line_facet.to = 100
        self.project.remove_rows(line_facet)
        self.assertInResponse('Remove 775 rows')
        line_facet.From = 570
        line_facet.to = 600
        self.project.remove_rows(line_facet)
        self.assertInResponse('Remove 71 rows')
        line_facet.reset()
        response = self.project.get_rows()
        self.assertEqual(response.filtered, 4563)
        # {6}
        page_facet = facet.TextFacet('page', 1)   # 1 not '1'
        self.project.engine.add_facet(page_facet)
        # {7}
        rows = self.project.get_rows().rows
        # Look for a row with a name in it by skipping HTML
        name_row = [row for row in rows if '<b>' not in row['line']][0]
        self.assertTrue('WELLNESS' in name_row['line'])
        self.assertEqual(name_row['top'], 161)
        line_facet.From = 20
        line_facet.to = 160
        self.project.remove_rows()
        self.assertInResponse('Remove 9 rows')
        self.project.engine.remove_all()
        # {8}
        self.project.text_transform('line', expression=self.filter_expr_1)
        self.assertInResponse('Text transform on 4554 cells in column line')
        # {9} - XXX following is generating Java exceptions
        #filter_expr = self.filter_expr_2 % 16
        #self.project.add_column('line', 'Name', expression=filter_expr)
        # {10} to the final {19} - nothing new in terms of exercising the API.


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
