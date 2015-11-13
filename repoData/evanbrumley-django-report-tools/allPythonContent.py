__FILENAME__ = register
from report_tools.views import ReportView
from report_tools.api import register


class MyReportView(ReportView):
    ...

register(MyReportView, 'myreportview_api_key')

########NEW FILE########
__FILENAME__ = urls
url(r'^api/', include('report_tools.urls'))

########NEW FILE########
__FILENAME__ = view
# myapp/views.py

from django.shortcuts import render
from myapp.reports import MyReport
from report_tools.views import ReportView


class MyReportView(ReportView):
    def get_report(self, request):
        return MyReport()
        
    def get(self, request):
        template = 'myapp/my_report.html'
        context = {
            'report': self.get_report(request),
        }
        
        return render(request, template, context)

########NEW FILE########
__FILENAME__ = better_reporting_view
from report_tools import reports
from report_tools import charts
from report_tools.chart_data import ChartData


def better_reporting_view(request):
    # Gather data
    my_objects = MyObject.objects.all()

    # Generate report
    report = MyReport(my_objects)

    context = {
        'report': report
    }

    return render(request, 'mytemplate.html', context)


class MyReport(reports.Report):
    renderer = MyRenderer

    chart1 = charts.PieChart(title="A nice, simple pie chart")
    chart2 = ...
    chart3 = ...

    def __init__(self, my_objects, *args, **kwargs):
        super(MyReport, self).__init__(*args, **kwargs)
        self.my_objects = my_objects

        # Here you could do any expensive calculations that
        # are needed for multiple charts

    def get_data_for_chart1(self):
        data = ChartData()

        # TODO: Fill data

        return data

########NEW FILE########
__FILENAME__ = simple_reporting_view
def simple_reporting_view(request):
    # Gather data
    my_objects = MyObject.objects.all()

    # Generate chart 1
    chart1_data = gather_chart1_data(my_objects)
    chart1_options = {...}
    chart1_html = generate_chart_html(chart1_data, chart1_options)

    # Generate chart 2,3,4,5,6,7
    ...

    context = {
        'chart1': chart1,
        'chart2': chart2,
        ...
    }

    return render(request, 'mytemplate.html', context)

########NEW FILE########
__FILENAME__ = bar_chart_example
class MyReport(Report):
    renderer = GoogleChartsRenderer

    bar_chart = charts.BarChart(title="Pony Populations", width="500")
    multiseries_bar_chart = charts.BarChart(title="Pony Populations by Country", width="500")

    def get_data_for_bar_chart(self):
        data = ChartData()

        data.add_column("Pony Type")
        data.add_column("Population")

        data.add_row(["Blue", 20])
        data.add_row(["Pink", 20])
        data.add_row(["Magical", 1])

        return data

    def get_data_for_multiseries_bar_chart(self):
        data = ChartData()

        data.add_column("Pony Type")
        data.add_column("Australian Population")
        data.add_column("Switzerland Population")
        data.add_column("USA Population")

        data.add_row(["Blue", 5, 10, 5])
        data.add_row(["Pink", 10, 2, 8])
        data.add_row(["Magical", 1, 0, 0])

        return data
########NEW FILE########
__FILENAME__ = column_chart_example
class MyReport(Report):
    renderer = GoogleChartsRenderer

    column_chart = charts.ColumnChart(title="Pony Populations", width="500")
    multiseries_column_chart = charts.ColumnChart(title="Pony Populations by Country", width="500")

    def get_data_for_column_chart(self):
        data = ChartData()

        data.add_column("Pony Type")
        data.add_column("Population")

        data.add_row(["Blue", 20])
        data.add_row(["Pink", 20])
        data.add_row(["Magical", 1])

        return data

    def get_data_for_multiseries_column_chart(self):
        data = ChartData()

        data.add_column("Pony Type")
        data.add_column("Australian Population")
        data.add_column("Switzerland Population")
        data.add_column("USA Population")

        data.add_row(["Blue", 5, 10, 5])
        data.add_row(["Pink", 10, 2, 8])
        data.add_row(["Magical", 1, 0, 0])

        return data
########NEW FILE########
__FILENAME__ = line_chart_example
class MyReport(Report):
    renderer = GoogleChartsRenderer

    line_chart = charts.LineChart(title="Blue Pony Population - 2009-2012", width="500")
    multiseries_line_chart = charts.LineChart(title="Pony Populations - 2009-2012", width="500")

    def get_data_for_line_chart(self):
        data = ChartData()

        data.add_column("Test Period")
        data.add_column("Blue Pony Population")

        data.add_row(["2009-10", 20])
        data.add_row(["2010-11", 18])
        data.add_row(["2011-12", 100])

        return data

    def get_data_for_multiseries_line_chart(self):
        data = ChartData()

        data.add_column("Test Period")
        data.add_column("Blue Pony Population")
        data.add_column("Pink Pony Population")
        data.add_column("Magical Pony Population")

        data.add_row(["2009-10", 20, 10, 50])
        data.add_row(["2010-11", 18, 8, 60])
        data.add_row(["2011-12", 100, 120, 2])

        return data
########NEW FILE########
__FILENAME__ = pie_chart_example
class MyReport(Report):
    renderer = GoogleChartsRenderer

    pie_chart = charts.PieChart(width=400, height=300)

    def get_data_for_pie_chart(self):
        data = ChartData()

        data.add_column("Pony Type")
        data.add_column("Population")

        data.add_row(["Blue", 20])
        data.add_row(["Pink", 20])
        data.add_row(["Magical", 1])

        return data
########NEW FILE########
__FILENAME__ = template_chart_example
class MyReport(Report):
    template_chart = charts.TemplateChart(template="myapp/template_chart.html")

    def get_data_for_template_chart(self):
        pony_types = [
            ('Blue', 'Equus Caeruleus'),
            ('Pink', 'Equus Roseus'),
            ('Magical', 'Equus Magica')
        ]

        template_context = {
            'pony_types': pony_types
        }

        return template_context
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-report-tools documentation build configuration file, created by
# sphinx-quickstart on Thu Jan 12 14:58:42 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
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
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = []

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-report-tools'
copyright = u''

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.2.1'
# The full version, including alpha/beta/rc tags.
release = '0.2.1'

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
exclude_patterns = []

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
html_theme = 'nature'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['.']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = "logo.png"

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

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
htmlhelp_basename = 'django-report-tools-doc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-report-tools.tex', u'django-report-tools Documentation',
   u'Evan Brumley', 'manual'),
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
    ('index', 'report-tools', u'report-tools Documentation',
     [u'Report Tools'], 1)
]

########NEW FILE########
__FILENAME__ = example
class MyReport(Report):
    renderer = GoogleChartsRenderer

    pie_chart = charts.PieChart(
        title="A nice, simple pie chart",
        width=400,
        height=300
    )

    def get_data_for_pie_chart(self):
        data = ChartData()

        data.add_column("Pony Type")
        data.add_column("Population")

        data.add_row(["Blue", 20])
        data.add_row(["Pink", 20])
        data.add_row(["Magical", 1])

        return data

########NEW FILE########
__FILENAME__ = reports
# myapp/reports.py

from report_tools.reports import Report
from report_tools.chart_data import ChartData
from report_tools.renderers.googlecharts import GoogleChartsRenderer
from report_tools import charts


class MyReport(Report):
    renderer = GoogleChartsRenderer

    pie_chart = charts.PieChart(
        title="A nice, simple pie chart",
        width=400,
        height=300
    )

    def get_data_for_pie_chart(self):
        data = ChartData()

        data.add_column("Pony Type")
        data.add_column("Population")

        data.add_row(["Blue", 20])
        data.add_row(["Pink", 20])
        data.add_row(["Magical", 1])

        return data

########NEW FILE########
__FILENAME__ = views
# myapp/views.py

from django.shortcuts import render
from myapp.reports import MyReport


def my_report(request):
    # Initialise the report
    template = "myapp/my_report.html"
    report = MyReport()
    context = {'report': report}

    return render(request, template, context)

########NEW FILE########
__FILENAME__ = views_class
# myapp/views.py

from django.shortcuts import render
from myapp.reports import MyReport
from report_tools.views import ReportView


class MyReportView(ReportView):
    def get_report(self, request):
        return MyReport()
        
    def get(self, request):
        template = 'myapp/my_report.html'
        context = {
            'report': self.get_report(request),
        }
        
        return render(request, template, context)

########NEW FILE########
__FILENAME__ = basic_renderer_usage_example
class MyReport(Report):
    renderer = GoogleChartsRenderer

    column_chart = charts.ColumnChart(title="Pony Populations", width="500")

    def get_data_for_column_chart(self):
        ...

########NEW FILE########
__FILENAME__ = chart_renderer_example
from report_tools.renderers import ChartRenderer


class MyChartRenderer(ChartRenderer):
    @classmethod
    def render_piechart(cls, chart_id, options, data, renderer_options):
        return "<div id='%s' class='placeholder'>Pie Chart</div>" % chart_id

    @classmethod
    def render_columnchart(cls, chart_id, options, data, renderer_options):
        return "<div id='%s' class='placeholder'>Column Chart</div>" % chart_id

    @classmethod
    def render_barchart(cls, chart_id, options, data, renderer_options):
        return "<div id='%s' class='placeholder'>Bar Chart</div>" % chart_id

    @classmethod
    def render_linechart(cls, chart_id, options, data, renderer_options):
        return "<div id='%s' class='placeholder'>Line Chart</div>" % chart_id
########NEW FILE########
__FILENAME__ = chart_renderer_usage_example
class MyReport(Report):
    renderer = GoogleChartsRenderer

    column_chart = charts.ColumnChart(title="Pony Populations", width="500")

    column_chart_other_renderer = charts.ColumnChart(
        title="Pony Populations", 
        width="500", 
        renderer=SomeOtherRenderer
    )

    def get_data_for_column_chart(self):
        ...

    def get_data_for_column_chart_other_renderer(self):
        ...
########NEW FILE########
__FILENAME__ = googlecharts_renderer_example
class MyReport(Report):
    renderer = GoogleChartsRenderer

    stacked_column_chart = charts.ColumnChart(
        title="Pony Populations", 
        width="500",
        renderer_options={
            'isStacked': True,
            'legend': {
                'position': 'none',
            },
            'backgroundColor': '#f5f5f5',
            'series': [
                {'color': '#ff0000'},
                {'color': '#0000ff'},
            ],
        }

    )

    def get_data_for_stacked_column_chart(self):
        ...

########NEW FILE########
__FILENAME__ = renderer_options_example
class MyReport(Report):
    renderer = GoogleChartsRenderer

    column_chart = charts.ColumnChart(
        title="Pony Populations", 
        width="500",
        renderer_options={
            'backgroundColor': "#ff0000"
        }
    )

    def get_data_for_column_chart(self):
        ...

########NEW FILE########
__FILENAME__ = api
from copy import copy

from django.http import QueryDict



OVERRIDE_PARAMS__CHART_HEIGHT = '_height'
OVERRIDE_PARAMS__CHART_WIDTH = '_width'
OVERRIDE_PARAMS__CHART_TITLE = '_title'


class ReportAPIRegistry(object):
    def __init__(self):
        self.reports = {}

    @property
    def api_keys(self):
        return self.reports.keys()

    def register(self, report_view_class, api_key):
        if api_key not in self.reports:
            self.reports[api_key] = report_view_class
    
    def get_report_view_class(self, api_key):
        return self.reports.get(api_key, None)
    

report_api_registry = ReportAPIRegistry()


def register(report_view_class, api_key=None):
    if api_key:
        report_api_registry.register(report_view_class, api_key)
    else:
        report_api_registry.register(report_view_class, report_view_class.api_key)
    
    
def get_chart(request, api_key, chart_name, parameters=None, prefix=None):
    request = copy(request)
    if parameters is not None:
        new_get = QueryDict('', mutable=True)
        new_get.update(parameters)
        request.GET = new_get
    
    report_view_class = report_api_registry.get_report_view_class(api_key)

    if not report_view_class:
        raise ReportNotFoundError("Report not found for api key '%s'. Available reports are '%s'." %
            (api_key, ', '.join(report_api_registry.api_keys)))
    
    report_view = report_view_class()
    
    return report_view.get_chart(request, chart_name, prefix)


class ReportNotFoundError(Exception):
    pass


class ChartNotFoundError(Exception):
    pass

########NEW FILE########
__FILENAME__ = charts
from django.utils.encoding import smart_unicode
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe



class Chart(object):
    # Tracks each time a Chart instance is created. Used to retain order.
    creation_counter = 0
    name = None
    
    def __init__(self, title=None, renderer=None, renderer_options={}, attrs={}):
        if title is not None:
            title = smart_unicode(title)
            
        self.title = title
        
        self.renderer = renderer
        self.renderer_options = renderer_options
        self.attrs = attrs
        self.options = {}
        
        self.creation_counter = Chart.creation_counter
        Chart.creation_counter += 1
        
    def __unicode__(self):
        return self.name
        
    def render(self, chart_id, data, base_renderer=None):
        if not self.name:
            raise NotImplementedError
        
        if self.renderer:
            renderer = self.renderer
        else:
            renderer = base_renderer
        
        if renderer:
            render_method_name = 'render_' + self.name
            render_method = getattr(renderer, render_method_name, None)
            
            if render_method:
                return render_method(chart_id, self.options, data, self.renderer_options)
            else:
                raise NotImplementedError
        else:
            raise RendererRequiredError

    @classmethod
    def get_empty_data_object(cls, sort=None):
        raise NotImplementedError
    

class RendererRequiredError(Exception):
    pass


class DimensionedChart(Chart):
    def __init__(self, *args, **kwargs):
        width = kwargs.pop('width', None)
        height = kwargs.pop('height', None)

        super(DimensionedChart, self).__init__(*args, **kwargs)

        self.options['width'] = width
        self.options['height'] = height


class PieChart(DimensionedChart):
    name = 'piechart'


class BarChart(DimensionedChart):
    name = 'barchart'


class ColumnChart(DimensionedChart):
    name = 'columnchart'


class LineChart(DimensionedChart):
    name = 'linechart'


class TemplateChart(Chart):
    name = 'templatechart'
    
    def __init__(self, template, *args, **kwargs):
        self.template = template
        super(TemplateChart, self).__init__(*args, **kwargs)

    def render(self, chart_id, data={}, base_renderer=None):
        if 'chart_id' not in data:
            data['chart_id'] = chart_id
        
        html = render_to_string(self.template, data)
        return mark_safe(html)


class DummyChart(Chart):
    def render(self, chart_id, data, *args, **kwargs):
        return u'%s' % data

########NEW FILE########
__FILENAME__ = chart_data
from copy import copy



class ChartDataError(Exception):
    pass


class ChartDataColumn(object):
    def __init__(self, name, metadata=None):
        self.name = copy(name)

        if metadata is not None:
            self.metadata = copy(metadata)
        else:
            self.metadata = {}
        
    def get_metadata(self):
        return self.metadata
    
    def get_metadata_item(self, key):
        return self.metadata.get(key, None)


class ChartDataRow(object):
    def __init__(self, data, metadata=None):
        self.cells = []

        for datum in data:
            if type(datum) != ChartDataCell:
                if type(datum) in (list, tuple):
                    datum = ChartDataCell(datum[0], datum[1])
                else:
                    datum = ChartDataCell(datum)
            
            self.cells.append(datum)
        
        if metadata is not None:
            self.metadata = copy(metadata)
        else:
            self.metadata = {}
    
    def __iter__(self):
        for cell in self.cells:
            yield cell
            
    def __getitem__(self, index):
        return self.cells[index]


class ChartDataCell(object):
    def __init__(self, data, metadata=None):
        self.data = copy(data)

        if metadata is not None:
            self.metadata = copy(metadata)
        else:
            self.metadata = {}


class ChartData(object):
    
    def __init__(self):
        self.columns = []
        self.rows = []
    
    def get_columns(self):
        return self.columns
    
    def get_rows(self):
        return self.rows
    
    def add_column(self, name, metadata=None):
        if self.rows:
            raise ChartDataError("Cannot add columns after data has been entered")
        
        column = ChartDataColumn(name, metadata)
        self.columns.append(column)
    
    def add_columns(self, columns):
        for column in columns:
            if type(column) in (list, tuple):
                name = column[0]
                metadata = column[1]
            else:
                name = column
                metadata = {}
                
            self.add_column(name, metadata)
    
    def add_row(self, data, metadata=None):
        if len(data) < len(self.columns):
            raise ChartDataError("Not enough data points (%s) for the given number of columns (%s)" % (len(data), len(self.columns)))

        if len(data) > len(self.columns):
            raise ChartDataError("Too many data points (%s) for the given number of columns (%s)" % (len(data), len(self.columns)))
        
        row = ChartDataRow(data, metadata)
        self.rows.append(row)

    def add_rows(self, rows):
        for row in rows:
            if type(row) in (list, tuple):
                data = row[0]
                metadata = row[1]
            else:
                data = row
                metadata = {}
            
            self.add_row(data, metadata)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = gviz_api
#!/usr/bin/python
#
# Copyright (C) 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Converts Python data into data for Google Visualization API clients.

This library can be used to create a google.visualization.DataTable usable by
visualizations built on the Google Visualization API. Output formats are raw
JSON, JSON response, JavaScript, CSV, and HTML table.

See http://code.google.com/apis/visualization/ for documentation on the
Google Visualization API.
"""

__author__ = "Amit Weinstein, Misha Seltzer, Jacob Baskin"

import cgi
import cStringIO
import csv
import datetime
try:
  import json
except ImportError:
  import simplejson as json
import types



class DataTableException(Exception):
  """The general exception object thrown by DataTable."""
  pass


class DataTableJSONEncoder(json.JSONEncoder):
  """JSON encoder that handles date/time/datetime objects correctly."""

  def __init__(self):
    json.JSONEncoder.__init__(self,
                              separators=(",", ":"),
                              ensure_ascii=False)

  def encode(self, o):
    # Override JSONEncoder.encode because it has hacks for
    # performance that make things more complicated.
    chunks = self.iterencode(o)
    if self.ensure_ascii:
      return ''.join(chunks)
    else:
      return u''.join(chunks)

  # Added by Evan Brumley for django-report-tools
  # This code allows the datatable JSON to be safely rendered
  # into an html page without being screwed up by ampersands
  # and </script> tags
  def iterencode(self, o):
    chunks = super(DataTableJSONEncoder, self).iterencode(o)
    for chunk in chunks:
      chunk = chunk.replace('&', '\\u0026')
      chunk = chunk.replace('<', '\\u003c')
      chunk = chunk.replace('>', '\\u003e')
      yield chunk

  def default(self, o):
    if isinstance(o, datetime.datetime):
      if o.microsecond == 0:
        # If the time doesn't have ms-resolution, leave it out to keep
        # things smaller.
        return "Date(%d,%d,%d,%d,%d,%d)" % (
            o.year, o.month - 1, o.day, o.hour, o.minute, o.second)
      else:
        return "Date(%d,%d,%d,%d,%d,%d,%d)" % (
            o.year, o.month - 1, o.day, o.hour, o.minute, o.second,
            o.microsecond / 1000)
    elif isinstance(o, datetime.date):
      return "Date(%d,%d,%d)" % (o.year, o.month - 1, o.day)
    elif isinstance(o, datetime.time):
      return [o.hour, o.minute, o.second]
    else:
      return super(DataTableJSONEncoder, self).default(o)


class DataTable(object):
  """Wraps the data to convert to a Google Visualization API DataTable.

  Create this object, populate it with data, then call one of the ToJS...
  methods to return a string representation of the data in the format described.

  You can clear all data from the object to reuse it, but you cannot clear
  individual cells, rows, or columns. You also cannot modify the table schema
  specified in the class constructor.

  You can add new data one or more rows at a time. All data added to an
  instantiated DataTable must conform to the schema passed in to __init__().

  You can reorder the columns in the output table, and also specify row sorting
  order by column. The default column order is according to the original
  table_description parameter. Default row sort order is ascending, by column
  1 values. For a dictionary, we sort the keys for order.

  The data and the table_description are closely tied, as described here:

  The table schema is defined in the class constructor's table_description
  parameter. The user defines each column using a tuple of
  (id[, type[, label[, custom_properties]]]). The default value for type is
  string, label is the same as ID if not specified, and custom properties is
  an empty dictionary if not specified.

  table_description is a dictionary or list, containing one or more column
  descriptor tuples, nested dictionaries, and lists. Each dictionary key, list
  element, or dictionary element must eventually be defined as
  a column description tuple. Here's an example of a dictionary where the key
  is a tuple, and the value is a list of two tuples:
    {('a', 'number'): [('b', 'number'), ('c', 'string')]}

  This flexibility in data entry enables you to build and manipulate your data
  in a Python structure that makes sense for your program.

  Add data to the table using the same nested design as the table's
  table_description, replacing column descriptor tuples with cell data, and
  each row is an element in the top level collection. This will be a bit
  clearer after you look at the following examples showing the
  table_description, matching data, and the resulting table:

  Columns as list of tuples [col1, col2, col3]
    table_description: [('a', 'number'), ('b', 'string')]
    AppendData( [[1, 'z'], [2, 'w'], [4, 'o'], [5, 'k']] )
    Table:
    a  b   <--- these are column ids/labels
    1  z
    2  w
    4  o
    5  k

  Dictionary of columns, where key is a column, and value is a list of
  columns  {col1: [col2, col3]}
    table_description: {('a', 'number'): [('b', 'number'), ('c', 'string')]}
    AppendData( data: {1: [2, 'z'], 3: [4, 'w']}
    Table:
    a  b  c
    1  2  z
    3  4  w

  Dictionary where key is a column, and the value is itself a dictionary of
  columns {col1: {col2, col3}}
    table_description: {('a', 'number'): {'b': 'number', 'c': 'string'}}
    AppendData( data: {1: {'b': 2, 'c': 'z'}, 3: {'b': 4, 'c': 'w'}}
    Table:
    a  b  c
    1  2  z
    3  4  w
  """

  def __init__(self, table_description, data=None, custom_properties=None):
    """Initialize the data table from a table schema and (optionally) data.

    See the class documentation for more information on table schema and data
    values.

    Args:
      table_description: A table schema, following one of the formats described
                         in TableDescriptionParser(). Schemas describe the
                         column names, data types, and labels. See
                         TableDescriptionParser() for acceptable formats.
      data: Optional. If given, fills the table with the given data. The data
            structure must be consistent with schema in table_description. See
            the class documentation for more information on acceptable data. You
            can add data later by calling AppendData().
      custom_properties: Optional. A dictionary from string to string that
                         goes into the table's custom properties. This can be
                         later changed by changing self.custom_properties.

    Raises:
      DataTableException: Raised if the data and the description did not match,
                          or did not use the supported formats.
    """
    self.__columns = self.TableDescriptionParser(table_description)
    self.__data = []
    self.custom_properties = {}
    if custom_properties is not None:
      self.custom_properties = custom_properties
    if data:
      self.LoadData(data)

  @staticmethod
  def CoerceValue(value, value_type):
    """Coerces a single value into the type expected for its column.

    Internal helper method.

    Args:
      value: The value which should be converted
      value_type: One of "string", "number", "boolean", "date", "datetime" or
                  "timeofday".

    Returns:
      An item of the Python type appropriate to the given value_type. Strings
      are also converted to Unicode using UTF-8 encoding if necessary.
      If a tuple is given, it should be in one of the following forms:
        - (value, formatted value)
        - (value, formatted value, custom properties)
      where the formatted value is a string, and custom properties is a
      dictionary of the custom properties for this cell.
      To specify custom properties without specifying formatted value, one can
      pass None as the formatted value.
      One can also have a null-valued cell with formatted value and/or custom
      properties by specifying None for the value.
      This method ignores the custom properties except for checking that it is a
      dictionary. The custom properties are handled in the ToJSon and ToJSCode
      methods.
      The real type of the given value is not strictly checked. For example,
      any type can be used for string - as we simply take its str( ) and for
      boolean value we just check "if value".
      Examples:
        CoerceValue(None, "string") returns None
        CoerceValue((5, "5$"), "number") returns (5, "5$")
        CoerceValue(100, "string") returns "100"
        CoerceValue(0, "boolean") returns False

    Raises:
      DataTableException: The value and type did not match in a not-recoverable
                          way, for example given value 'abc' for type 'number'.
    """
    if isinstance(value, tuple):
      # In case of a tuple, we run the same function on the value itself and
      # add the formatted value.
      if (len(value) not in [2, 3] or
          (len(value) == 3 and not isinstance(value[2], dict))):
        raise DataTableException("Wrong format for value and formatting - %s." %
                                 str(value))
      if not isinstance(value[1], types.StringTypes + (types.NoneType,)):
        raise DataTableException("Formatted value is not string, given %s." %
                                 type(value[1]))
      js_value = DataTable.CoerceValue(value[0], value_type)
      return (js_value,) + value[1:]

    t_value = type(value)
    if value is None:
      return value
    if value_type == "boolean":
      return bool(value)

    elif value_type == "number":
      if isinstance(value, (int, long, float)):
        return value
      raise DataTableException("Wrong type %s when expected number" % t_value)

    elif value_type == "string":
      if isinstance(value, unicode):
        return value
      else:
        return str(value).decode("utf-8")

    elif value_type == "date":
      if isinstance(value, datetime.datetime):
        return datetime.date(value.year, value.month, value.day)
      elif isinstance(value, datetime.date):
        return value
      else:
        raise DataTableException("Wrong type %s when expected date" % t_value)

    elif value_type == "timeofday":
      if isinstance(value, datetime.datetime):
        return datetime.time(value.hour, value.minute, value.second)
      elif isinstance(value, datetime.time):
        return value
      else:
        raise DataTableException("Wrong type %s when expected time" % t_value)

    elif value_type == "datetime":
      if isinstance(value, datetime.datetime):
        return value
      else:
        raise DataTableException("Wrong type %s when expected datetime" %
                                 t_value)
    # If we got here, it means the given value_type was not one of the
    # supported types.
    raise DataTableException("Unsupported type %s" % value_type)

  @staticmethod
  def EscapeForJSCode(encoder, value):
    if value is None:
      return "null"
    elif isinstance(value, datetime.datetime):
      if value.microsecond == 0:
        # If it's not ms-resolution, leave that out to save space.
        return "new Date(%d,%d,%d,%d,%d,%d)" % (value.year,
                                                value.month - 1,  # To match JS
                                                value.day,
                                                value.hour,
                                                value.minute,
                                                value.second)
      else:
        return "new Date(%d,%d,%d,%d,%d,%d,%d)" % (value.year,
                                                   value.month - 1,  # match JS
                                                   value.day,
                                                   value.hour,
                                                   value.minute,
                                                   value.second,
                                                   value.microsecond / 1000)
    elif isinstance(value, datetime.date):
      return "new Date(%d,%d,%d)" % (value.year, value.month - 1, value.day)
    else:
      return encoder.encode(value)

  @staticmethod
  def ToString(value):
    if value is None:
      return "(empty)"
    elif isinstance(value, (datetime.datetime,
                            datetime.date,
                            datetime.time)):
      return str(value)
    elif isinstance(value, unicode):
      return value
    elif isinstance(value, bool):
      return str(value).lower()
    else:
      return str(value).decode("utf-8")

  @staticmethod
  def ColumnTypeParser(description):
    """Parses a single column description. Internal helper method.

    Args:
      description: a column description in the possible formats:
       'id'
       ('id',)
       ('id', 'type')
       ('id', 'type', 'label')
       ('id', 'type', 'label', {'custom_prop1': 'custom_val1'})
    Returns:
      Dictionary with the following keys: id, label, type, and
      custom_properties where:
        - If label not given, it equals the id.
        - If type not given, string is used by default.
        - If custom properties are not given, an empty dictionary is used by
          default.

    Raises:
      DataTableException: The column description did not match the RE, or
          unsupported type was passed.
    """
    if not description:
      raise DataTableException("Description error: empty description given")

    if not isinstance(description, (types.StringTypes, tuple)):
      raise DataTableException("Description error: expected either string or "
                               "tuple, got %s." % type(description))

    if isinstance(description, types.StringTypes):
      description = (description,)

    # According to the tuple's length, we fill the keys
    # We verify everything is of type string
    for elem in description[:3]:
      if not isinstance(elem, types.StringTypes):
        raise DataTableException("Description error: expected tuple of "
                                 "strings, current element of type %s." %
                                 type(elem))
    desc_dict = {"id": description[0],
                 "label": description[0],
                 "type": "string",
                 "custom_properties": {}}
    if len(description) > 1:
      desc_dict["type"] = description[1].lower()
      if len(description) > 2:
        desc_dict["label"] = description[2]
        if len(description) > 3:
          if not isinstance(description[3], dict):
            raise DataTableException("Description error: expected custom "
                                     "properties of type dict, current element "
                                     "of type %s." % type(description[3]))
          desc_dict["custom_properties"] = description[3]
          if len(description) > 4:
            raise DataTableException("Description error: tuple of length > 4")
    if desc_dict["type"] not in ["string", "number", "boolean",
                                 "date", "datetime", "timeofday"]:
      raise DataTableException(
          "Description error: unsupported type '%s'" % desc_dict["type"])
    return desc_dict

  @staticmethod
  def TableDescriptionParser(table_description, depth=0):
    """Parses the table_description object for internal use.

    Parses the user-submitted table description into an internal format used
    by the Python DataTable class. Returns the flat list of parsed columns.

    Args:
      table_description: A description of the table which should comply
                         with one of the formats described below.
      depth: Optional. The depth of the first level in the current description.
             Used by recursive calls to this function.

    Returns:
      List of columns, where each column represented by a dictionary with the
      keys: id, label, type, depth, container which means the following:
      - id: the id of the column
      - name: The name of the column
      - type: The datatype of the elements in this column. Allowed types are
              described in ColumnTypeParser().
      - depth: The depth of this column in the table description
      - container: 'dict', 'iter' or 'scalar' for parsing the format easily.
      - custom_properties: The custom properties for this column.
      The returned description is flattened regardless of how it was given.

    Raises:
      DataTableException: Error in a column description or in the description
                          structure.

    Examples:
      A column description can be of the following forms:
       'id'
       ('id',)
       ('id', 'type')
       ('id', 'type', 'label')
       ('id', 'type', 'label', {'custom_prop1': 'custom_val1'})
       or as a dictionary:
       'id': 'type'
       'id': ('type',)
       'id': ('type', 'label')
       'id': ('type', 'label', {'custom_prop1': 'custom_val1'})
      If the type is not specified, we treat it as string.
      If no specific label is given, the label is simply the id.
      If no custom properties are given, we use an empty dictionary.

      input: [('a', 'date'), ('b', 'timeofday', 'b', {'foo': 'bar'})]
      output: [{'id': 'a', 'label': 'a', 'type': 'date',
                'depth': 0, 'container': 'iter', 'custom_properties': {}},
               {'id': 'b', 'label': 'b', 'type': 'timeofday',
                'depth': 0, 'container': 'iter',
                'custom_properties': {'foo': 'bar'}}]

      input: {'a': [('b', 'number'), ('c', 'string', 'column c')]}
      output: [{'id': 'a', 'label': 'a', 'type': 'string',
                'depth': 0, 'container': 'dict', 'custom_properties': {}},
               {'id': 'b', 'label': 'b', 'type': 'number',
                'depth': 1, 'container': 'iter', 'custom_properties': {}},
               {'id': 'c', 'label': 'column c', 'type': 'string',
                'depth': 1, 'container': 'iter', 'custom_properties': {}}]

      input:  {('a', 'number', 'column a'): { 'b': 'number', 'c': 'string'}}
      output: [{'id': 'a', 'label': 'column a', 'type': 'number',
                'depth': 0, 'container': 'dict', 'custom_properties': {}},
               {'id': 'b', 'label': 'b', 'type': 'number',
                'depth': 1, 'container': 'dict', 'custom_properties': {}},
               {'id': 'c', 'label': 'c', 'type': 'string',
                'depth': 1, 'container': 'dict', 'custom_properties': {}}]

      input: { ('w', 'string', 'word'): ('c', 'number', 'count') }
      output: [{'id': 'w', 'label': 'word', 'type': 'string',
                'depth': 0, 'container': 'dict', 'custom_properties': {}},
               {'id': 'c', 'label': 'count', 'type': 'number',
                'depth': 1, 'container': 'scalar', 'custom_properties': {}}]

      input: {'a': ('number', 'column a'), 'b': ('string', 'column b')}
      output: [{'id': 'a', 'label': 'column a', 'type': 'number', 'depth': 0,
               'container': 'dict', 'custom_properties': {}},
               {'id': 'b', 'label': 'column b', 'type': 'string', 'depth': 0,
               'container': 'dict', 'custom_properties': {}}

      NOTE: there might be ambiguity in the case of a dictionary representation
      of a single column. For example, the following description can be parsed
      in 2 different ways: {'a': ('b', 'c')} can be thought of a single column
      with the id 'a', of type 'b' and the label 'c', or as 2 columns: one named
      'a', and the other named 'b' of type 'c'. We choose the first option by
      default, and in case the second option is the right one, it is possible to
      make the key into a tuple (i.e. {('a',): ('b', 'c')}) or add more info
      into the tuple, thus making it look like this: {'a': ('b', 'c', 'b', {})}
      -- second 'b' is the label, and {} is the custom properties field.
    """
    # For the recursion step, we check for a scalar object (string or tuple)
    if isinstance(table_description, (types.StringTypes, tuple)):
      parsed_col = DataTable.ColumnTypeParser(table_description)
      parsed_col["depth"] = depth
      parsed_col["container"] = "scalar"
      return [parsed_col]

    # Since it is not scalar, table_description must be iterable.
    if not hasattr(table_description, "__iter__"):
      raise DataTableException("Expected an iterable object, got %s" %
                               type(table_description))
    if not isinstance(table_description, dict):
      # We expects a non-dictionary iterable item.
      columns = []
      for desc in table_description:
        parsed_col = DataTable.ColumnTypeParser(desc)
        parsed_col["depth"] = depth
        parsed_col["container"] = "iter"
        columns.append(parsed_col)
      if not columns:
        raise DataTableException("Description iterable objects should not"
                                 " be empty.")
      return columns
    # The other case is a dictionary
    if not table_description:
      raise DataTableException("Empty dictionaries are not allowed inside"
                               " description")

    # To differentiate between the two cases of more levels below or this is
    # the most inner dictionary, we consider the number of keys (more then one
    # key is indication for most inner dictionary) and the type of the key and
    # value in case of only 1 key (if the type of key is string and the type of
    # the value is a tuple of 0-3 items, we assume this is the most inner
    # dictionary).
    # NOTE: this way of differentiating might create ambiguity. See docs.
    if (len(table_description) != 1 or
        (isinstance(table_description.keys()[0], types.StringTypes) and
         isinstance(table_description.values()[0], tuple) and
         len(table_description.values()[0]) < 4)):
      # This is the most inner dictionary. Parsing types.
      columns = []
      # We sort the items, equivalent to sort the keys since they are unique
      for key, value in sorted(table_description.items()):
        # We parse the column type as (key, type) or (key, type, label) using
        # ColumnTypeParser.
        if isinstance(value, tuple):
          parsed_col = DataTable.ColumnTypeParser((key,) + value)
        else:
          parsed_col = DataTable.ColumnTypeParser((key, value))
        parsed_col["depth"] = depth
        parsed_col["container"] = "dict"
        columns.append(parsed_col)
      return columns
    # This is an outer dictionary, must have at most one key.
    parsed_col = DataTable.ColumnTypeParser(table_description.keys()[0])
    parsed_col["depth"] = depth
    parsed_col["container"] = "dict"
    return ([parsed_col] +
            DataTable.TableDescriptionParser(table_description.values()[0],
                                             depth=depth + 1))

  @property
  def columns(self):
    """Returns the parsed table description."""
    return self.__columns

  def NumberOfRows(self):
    """Returns the number of rows in the current data stored in the table."""
    return len(self.__data)

  def SetRowsCustomProperties(self, rows, custom_properties):
    """Sets the custom properties for given row(s).

    Can accept a single row or an iterable of rows.
    Sets the given custom properties for all specified rows.

    Args:
      rows: The row, or rows, to set the custom properties for.
      custom_properties: A string to string dictionary of custom properties to
      set for all rows.
    """
    if not hasattr(rows, "__iter__"):
      rows = [rows]
    for row in rows:
      self.__data[row] = (self.__data[row][0], custom_properties)

  def LoadData(self, data, custom_properties=None):
    """Loads new rows to the data table, clearing existing rows.

    May also set the custom_properties for the added rows. The given custom
    properties dictionary specifies the dictionary that will be used for *all*
    given rows.

    Args:
      data: The rows that the table will contain.
      custom_properties: A dictionary of string to string to set as the custom
                         properties for all rows.
    """
    self.__data = []
    self.AppendData(data, custom_properties)

  def AppendData(self, data, custom_properties=None):
    """Appends new data to the table.

    Data is appended in rows. Data must comply with
    the table schema passed in to __init__(). See CoerceValue() for a list
    of acceptable data types. See the class documentation for more information
    and examples of schema and data values.

    Args:
      data: The row to add to the table. The data must conform to the table
            description format.
      custom_properties: A dictionary of string to string, representing the
                         custom properties to add to all the rows.

    Raises:
      DataTableException: The data structure does not match the description.
    """
    # If the maximal depth is 0, we simply iterate over the data table
    # lines and insert them using _InnerAppendData. Otherwise, we simply
    # let the _InnerAppendData handle all the levels.
    if not self.__columns[-1]["depth"]:
      for row in data:
        self._InnerAppendData(({}, custom_properties), row, 0)
    else:
      self._InnerAppendData(({}, custom_properties), data, 0)

  def _InnerAppendData(self, prev_col_values, data, col_index):
    """Inner function to assist LoadData."""
    # We first check that col_index has not exceeded the columns size
    if col_index >= len(self.__columns):
      raise DataTableException("The data does not match description, too deep")

    # Dealing with the scalar case, the data is the last value.
    if self.__columns[col_index]["container"] == "scalar":
      prev_col_values[0][self.__columns[col_index]["id"]] = data
      self.__data.append(prev_col_values)
      return

    if self.__columns[col_index]["container"] == "iter":
      if not hasattr(data, "__iter__") or isinstance(data, dict):
        raise DataTableException("Expected iterable object, got %s" %
                                 type(data))
      # We only need to insert the rest of the columns
      # If there are less items than expected, we only add what there is.
      for value in data:
        if col_index >= len(self.__columns):
          raise DataTableException("Too many elements given in data")
        prev_col_values[0][self.__columns[col_index]["id"]] = value
        col_index += 1
      self.__data.append(prev_col_values)
      return

    # We know the current level is a dictionary, we verify the type.
    if not isinstance(data, dict):
      raise DataTableException("Expected dictionary at current level, got %s" %
                               type(data))
    # We check if this is the last level
    if self.__columns[col_index]["depth"] == self.__columns[-1]["depth"]:
      # We need to add the keys in the dictionary as they are
      for col in self.__columns[col_index:]:
        if col["id"] in data:
          prev_col_values[0][col["id"]] = data[col["id"]]
      self.__data.append(prev_col_values)
      return

    # We have a dictionary in an inner depth level.
    if not data.keys():
      # In case this is an empty dictionary, we add a record with the columns
      # filled only until this point.
      self.__data.append(prev_col_values)
    else:
      for key in sorted(data):
        col_values = dict(prev_col_values[0])
        col_values[self.__columns[col_index]["id"]] = key
        self._InnerAppendData((col_values, prev_col_values[1]),
                              data[key], col_index + 1)

  def _PreparedData(self, order_by=()):
    """Prepares the data for enumeration - sorting it by order_by.

    Args:
      order_by: Optional. Specifies the name of the column(s) to sort by, and
                (optionally) which direction to sort in. Default sort direction
                is asc. Following formats are accepted:
                "string_col_name"  -- For a single key in default (asc) order.
                ("string_col_name", "asc|desc") -- For a single key.
                [("col_1","asc|desc"), ("col_2","asc|desc")] -- For more than
                    one column, an array of tuples of (col_name, "asc|desc").

    Returns:
      The data sorted by the keys given.

    Raises:
      DataTableException: Sort direction not in 'asc' or 'desc'
    """
    if not order_by:
      return self.__data

    proper_sort_keys = []
    if isinstance(order_by, types.StringTypes) or (
        isinstance(order_by, tuple) and len(order_by) == 2 and
        order_by[1].lower() in ["asc", "desc"]):
      order_by = (order_by,)
    for key in order_by:
      if isinstance(key, types.StringTypes):
        proper_sort_keys.append((key, 1))
      elif (isinstance(key, (list, tuple)) and len(key) == 2 and
            key[1].lower() in ("asc", "desc")):
        proper_sort_keys.append((key[0], key[1].lower() == "asc" and 1 or -1))
      else:
        raise DataTableException("Expected tuple with second value: "
                                 "'asc' or 'desc'")

    def SortCmpFunc(row1, row2):
      """cmp function for sorted. Compares by keys and 'asc'/'desc' keywords."""
      for key, asc_mult in proper_sort_keys:
        cmp_result = asc_mult * cmp(row1[0].get(key), row2[0].get(key))
        if cmp_result:
          return cmp_result
      return 0

    return sorted(self.__data, cmp=SortCmpFunc)

  def ToJSCode(self, name, columns_order=None, order_by=()):
    """Writes the data table as a JS code string.

    This method writes a string of JS code that can be run to
    generate a DataTable with the specified data. Typically used for debugging
    only.

    Args:
      name: The name of the table. The name would be used as the DataTable's
            variable name in the created JS code.
      columns_order: Optional. Specifies the order of columns in the
                     output table. Specify a list of all column IDs in the order
                     in which you want the table created.
                     Note that you must list all column IDs in this parameter,
                     if you use it.
      order_by: Optional. Specifies the name of the column(s) to sort by.
                Passed as is to _PreparedData.

    Returns:
      A string of JS code that, when run, generates a DataTable with the given
      name and the data stored in the DataTable object.
      Example result:
        "var tab1 = new google.visualization.DataTable();
         tab1.addColumn("string", "a", "a");
         tab1.addColumn("number", "b", "b");
         tab1.addColumn("boolean", "c", "c");
         tab1.addRows(10);
         tab1.setCell(0, 0, "a");
         tab1.setCell(0, 1, 1, null, {"foo": "bar"});
         tab1.setCell(0, 2, true);
         ...
         tab1.setCell(9, 0, "c");
         tab1.setCell(9, 1, 3, "3$");
         tab1.setCell(9, 2, false);"

    Raises:
      DataTableException: The data does not match the type.
    """

    encoder = DataTableJSONEncoder()

    if columns_order is None:
      columns_order = [col["id"] for col in self.__columns]
    col_dict = dict([(col["id"], col) for col in self.__columns])

    # We first create the table with the given name
    jscode = "var %s = new google.visualization.DataTable();\n" % name
    if self.custom_properties:
      jscode += "%s.setTableProperties(%s);\n" % (
          name, encoder.encode(self.custom_properties))

    # We add the columns to the table
    for i, col in enumerate(columns_order):
      jscode += "%s.addColumn(%s, %s, %s);\n" % (
          name,
          encoder.encode(col_dict[col]["type"]),
          encoder.encode(col_dict[col]["label"]),
          encoder.encode(col_dict[col]["id"]))
      if col_dict[col]["custom_properties"]:
        jscode += "%s.setColumnProperties(%d, %s);\n" % (
            name, i, encoder.encode(col_dict[col]["custom_properties"]))
    jscode += "%s.addRows(%d);\n" % (name, len(self.__data))

    # We now go over the data and add each row
    for (i, (row, cp)) in enumerate(self._PreparedData(order_by)):
      # We add all the elements of this row by their order
      for (j, col) in enumerate(columns_order):
        if col not in row or row[col] is None:
          continue
        value = self.CoerceValue(row[col], col_dict[col]["type"])
        if isinstance(value, tuple):
          cell_cp = ""
          if len(value) == 3:
            cell_cp = ", %s" % encoder.encode(row[col][2])
          # We have a formatted value or custom property as well
          jscode += ("%s.setCell(%d, %d, %s, %s%s);\n" %
                     (name, i, j,
                      self.EscapeForJSCode(encoder, value[0]),
                      self.EscapeForJSCode(encoder, value[1]), cell_cp))
        else:
          jscode += "%s.setCell(%d, %d, %s);\n" % (
              name, i, j, self.EscapeForJSCode(encoder, value))
      if cp:
        jscode += "%s.setRowProperties(%d, %s);\n" % (
            name, i, encoder.encode(cp))
    return jscode

  def ToHtml(self, columns_order=None, order_by=()):
    """Writes the data table as an HTML table code string.

    Args:
      columns_order: Optional. Specifies the order of columns in the
                     output table. Specify a list of all column IDs in the order
                     in which you want the table created.
                     Note that you must list all column IDs in this parameter,
                     if you use it.
      order_by: Optional. Specifies the name of the column(s) to sort by.
                Passed as is to _PreparedData.

    Returns:
      An HTML table code string.
      Example result (the result is without the newlines):
       <html><body><table border="1">
        <thead><tr><th>a</th><th>b</th><th>c</th></tr></thead>
        <tbody>
         <tr><td>1</td><td>"z"</td><td>2</td></tr>
         <tr><td>"3$"</td><td>"w"</td><td></td></tr>
        </tbody>
       </table></body></html>

    Raises:
      DataTableException: The data does not match the type.
    """
    table_template = "<html><body><table border=\"1\">%s</table></body></html>"
    columns_template = "<thead><tr>%s</tr></thead>"
    rows_template = "<tbody>%s</tbody>"
    row_template = "<tr>%s</tr>"
    header_cell_template = "<th>%s</th>"
    cell_template = "<td>%s</td>"

    if columns_order is None:
      columns_order = [col["id"] for col in self.__columns]
    col_dict = dict([(col["id"], col) for col in self.__columns])

    columns_list = []
    for col in columns_order:
      columns_list.append(header_cell_template %
                          cgi.escape(col_dict[col]["label"]))
    columns_html = columns_template % "".join(columns_list)

    rows_list = []
    # We now go over the data and add each row
    for row, unused_cp in self._PreparedData(order_by):
      cells_list = []
      # We add all the elements of this row by their order
      for col in columns_order:
        # For empty string we want empty quotes ("").
        value = ""
        if col in row and row[col] is not None:
          value = self.CoerceValue(row[col], col_dict[col]["type"])
        if isinstance(value, tuple):
          # We have a formatted value and we're going to use it
          cells_list.append(cell_template % cgi.escape(self.ToString(value[1])))
        else:
          cells_list.append(cell_template % cgi.escape(self.ToString(value)))
      rows_list.append(row_template % "".join(cells_list))
    rows_html = rows_template % "".join(rows_list)

    return table_template % (columns_html + rows_html)

  def ToCsv(self, columns_order=None, order_by=(), separator=","):
    """Writes the data table as a CSV string.

    Output is encoded in UTF-8 because the Python "csv" module can't handle
    Unicode properly according to its documentation.

    Args:
      columns_order: Optional. Specifies the order of columns in the
                     output table. Specify a list of all column IDs in the order
                     in which you want the table created.
                     Note that you must list all column IDs in this parameter,
                     if you use it.
      order_by: Optional. Specifies the name of the column(s) to sort by.
                Passed as is to _PreparedData.
      separator: Optional. The separator to use between the values.

    Returns:
      A CSV string representing the table.
      Example result:
       'a','b','c'
       1,'z',2
       3,'w',''

    Raises:
      DataTableException: The data does not match the type.
    """

    csv_buffer = cStringIO.StringIO()
    writer = csv.writer(csv_buffer, delimiter=separator)

    if columns_order is None:
      columns_order = [col["id"] for col in self.__columns]
    col_dict = dict([(col["id"], col) for col in self.__columns])

    writer.writerow([col_dict[col]["label"].encode("utf-8")
                     for col in columns_order])

    # We now go over the data and add each row
    for row, unused_cp in self._PreparedData(order_by):
      cells_list = []
      # We add all the elements of this row by their order
      for col in columns_order:
        value = ""
        if col in row and row[col] is not None:
          value = self.CoerceValue(row[col], col_dict[col]["type"])
        if isinstance(value, tuple):
          # We have a formatted value. Using it only for date/time types.
          if col_dict[col]["type"] in ["date", "datetime", "timeofday"]:
            cells_list.append(self.ToString(value[1]).encode("utf-8"))
          else:
            cells_list.append(self.ToString(value[0]).encode("utf-8"))
        else:
          cells_list.append(self.ToString(value).encode("utf-8"))
      writer.writerow(cells_list)
    return csv_buffer.getvalue()

  def ToTsvExcel(self, columns_order=None, order_by=()):
    """Returns a file in tab-separated-format readable by MS Excel.

    Returns a file in UTF-16 little endian encoding, with tabs separating the
    values.

    Args:
      columns_order: Delegated to ToCsv.
      order_by: Delegated to ToCsv.

    Returns:
      A tab-separated little endian UTF16 file representing the table.
    """
    return (self.ToCsv(columns_order, order_by, separator="\t")
            .decode("utf-8").encode("UTF-16LE"))

  def _ToJSonObj(self, columns_order=None, order_by=()):
    """Returns an object suitable to be converted to JSON.

    Args:
      columns_order: Optional. A list of all column IDs in the order in which
                     you want them created in the output table. If specified,
                     all column IDs must be present.
      order_by: Optional. Specifies the name of the column(s) to sort by.
                Passed as is to _PreparedData().

    Returns:
      A dictionary object for use by ToJSon or ToJSonResponse.
    """
    if columns_order is None:
      columns_order = [col["id"] for col in self.__columns]
    col_dict = dict([(col["id"], col) for col in self.__columns])

    # Creating the column JSON objects
    col_objs = []
    for col_id in columns_order:
      col_obj = {"id": col_dict[col_id]["id"],
                 "label": col_dict[col_id]["label"],
                 "type": col_dict[col_id]["type"]}
      if col_dict[col_id]["custom_properties"]:
        col_obj["p"] = col_dict[col_id]["custom_properties"]
      col_objs.append(col_obj)

    # Creating the rows jsons
    row_objs = []
    for row, cp in self._PreparedData(order_by):
      cell_objs = []
      for col in columns_order:
        value = self.CoerceValue(row.get(col, None), col_dict[col]["type"])
        if value is None:
          cell_obj = None
        elif isinstance(value, tuple):
          cell_obj = {"v": value[0]}
          if len(value) > 1 and value[1] is not None:
            cell_obj["f"] = value[1]
          if len(value) == 3:
            cell_obj["p"] = value[2]
        else:
          cell_obj = {"v": value}
        cell_objs.append(cell_obj)
      row_obj = {"c": cell_objs}
      if cp:
        row_obj["p"] = cp
      row_objs.append(row_obj)

    json_obj = {"cols": col_objs, "rows": row_objs}
    if self.custom_properties:
      json_obj["p"] = self.custom_properties

    return json_obj

  def ToJSon(self, columns_order=None, order_by=()):
    """Returns a string that can be used in a JS DataTable constructor.

    This method writes a JSON string that can be passed directly into a Google
    Visualization API DataTable constructor. Use this output if you are
    hosting the visualization HTML on your site, and want to code the data
    table in Python. Pass this string into the
    google.visualization.DataTable constructor, e.g,:
      ... on my page that hosts my visualization ...
      google.setOnLoadCallback(drawTable);
      function drawTable() {
        var data = new google.visualization.DataTable(_my_JSon_string, 0.6);
        myTable.draw(data);
      }

    Args:
      columns_order: Optional. Specifies the order of columns in the
                     output table. Specify a list of all column IDs in the order
                     in which you want the table created.
                     Note that you must list all column IDs in this parameter,
                     if you use it.
      order_by: Optional. Specifies the name of the column(s) to sort by.
                Passed as is to _PreparedData().

    Returns:
      A JSon constructor string to generate a JS DataTable with the data
      stored in the DataTable object.
      Example result (the result is without the newlines):
       {cols: [{id:"a",label:"a",type:"number"},
               {id:"b",label:"b",type:"string"},
              {id:"c",label:"c",type:"number"}],
        rows: [{c:[{v:1},{v:"z"},{v:2}]}, c:{[{v:3,f:"3$"},{v:"w"},{v:null}]}],
        p:    {'foo': 'bar'}}

    Raises:
      DataTableException: The data does not match the type.
    """

    encoder = DataTableJSONEncoder()
    return encoder.encode(
        self._ToJSonObj(columns_order, order_by)).encode("utf-8")

  def ToJSonResponse(self, columns_order=None, order_by=(), req_id=0,
                     response_handler="google.visualization.Query.setResponse"):
    """Writes a table as a JSON response that can be returned as-is to a client.

    This method writes a JSON response to return to a client in response to a
    Google Visualization API query. This string can be processed by the calling
    page, and is used to deliver a data table to a visualization hosted on
    a different page.

    Args:
      columns_order: Optional. Passed straight to self.ToJSon().
      order_by: Optional. Passed straight to self.ToJSon().
      req_id: Optional. The response id, as retrieved by the request.
      response_handler: Optional. The response handler, as retrieved by the
          request.

    Returns:
      A JSON response string to be received by JS the visualization Query
      object. This response would be translated into a DataTable on the
      client side.
      Example result (newlines added for readability):
       google.visualization.Query.setResponse({
          'version':'0.6', 'reqId':'0', 'status':'OK',
          'table': {cols: [...], rows: [...]}});

    Note: The URL returning this string can be used as a data source by Google
          Visualization Gadgets or from JS code.
    """

    response_obj = {
        "version": "0.6",
        "reqId": str(req_id),
        "table": self._ToJSonObj(columns_order, order_by),
        "status": "ok"
    }
    encoder = DataTableJSONEncoder()
    return "%s(%s);" % (response_handler,
                        encoder.encode(response_obj).encode("utf-8"))

  def ToResponse(self, columns_order=None, order_by=(), tqx=""):
    """Writes the right response according to the request string passed in tqx.

    This method parses the tqx request string (format of which is defined in
    the documentation for implementing a data source of Google Visualization),
    and returns the right response according to the request.
    It parses out the "out" parameter of tqx, calls the relevant response
    (ToJSonResponse() for "json", ToCsv() for "csv", ToHtml() for "html",
    ToTsvExcel() for "tsv-excel") and passes the response function the rest of
    the relevant request keys.

    Args:
      columns_order: Optional. Passed as is to the relevant response function.
      order_by: Optional. Passed as is to the relevant response function.
      tqx: Optional. The request string as received by HTTP GET. Should be in
           the format "key1:value1;key2:value2...". All keys have a default
           value, so an empty string will just do the default (which is calling
           ToJSonResponse() with no extra parameters).

    Returns:
      A response string, as returned by the relevant response function.

    Raises:
      DataTableException: One of the parameters passed in tqx is not supported.
    """
    tqx_dict = {}
    if tqx:
      tqx_dict = dict(opt.split(":") for opt in tqx.split(";"))
    if tqx_dict.get("version", "0.6") != "0.6":
      raise DataTableException(
          "Version (%s) passed by request is not supported."
          % tqx_dict["version"])

    if tqx_dict.get("out", "json") == "json":
      response_handler = tqx_dict.get("responseHandler",
                                      "google.visualization.Query.setResponse")
      return self.ToJSonResponse(columns_order, order_by,
                                 req_id=tqx_dict.get("reqId", 0),
                                 response_handler=response_handler)
    elif tqx_dict["out"] == "html":
      return self.ToHtml(columns_order, order_by)
    elif tqx_dict["out"] == "csv":
      return self.ToCsv(columns_order, order_by)
    elif tqx_dict["out"] == "tsv-excel":
      return self.ToTsvExcel(columns_order, order_by)
    else:
      raise DataTableException(
          "'out' parameter: '%s' is not supported" % tqx_dict["out"])

########NEW FILE########
__FILENAME__ = gviz_api_test
#!/usr/bin/python
#
# Copyright (C) 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the gviz_api module."""

__author__ = "Amit Weinstein"

from datetime import date
from datetime import datetime
from datetime import time
try:
  import json
except ImportError:
  import simplejson as json
import unittest

from gviz_api import DataTable
from gviz_api import DataTableException


class DataTableTest(unittest.TestCase):

  def testCoerceValue(self):
    # We first check that given an unknown type it raises exception
    self.assertRaises(DataTableException,
                      DataTable.CoerceValue, 1, "no_such_type")

    # If we give a type which does not match the value, we expect it to fail
    self.assertRaises(DataTableException,
                      DataTable.CoerceValue, "a", "number")
    self.assertRaises(DataTableException,
                      DataTable.CoerceValue, "b", "timeofday")
    self.assertRaises(DataTableException,
                      DataTable.CoerceValue, 10, "date")

    # A tuple for value and formatted value should be of length 2
    self.assertRaises(DataTableException,
                      DataTable.CoerceValue, (5, "5$", "6$"), "string")

    # Some good examples from all the different types
    self.assertEqual(True, DataTable.CoerceValue(True, "boolean"))
    self.assertEqual(False, DataTable.CoerceValue(False, "boolean"))
    self.assertEqual(True, DataTable.CoerceValue(1, "boolean"))
    self.assertEqual(None, DataTable.CoerceValue(None, "boolean"))
    self.assertEqual((False, u"a"),
                     DataTable.CoerceValue((False, "a"), "boolean"))

    self.assertEqual(1, DataTable.CoerceValue(1, "number"))
    self.assertEqual(1., DataTable.CoerceValue(1., "number"))
    self.assertEqual(-5, DataTable.CoerceValue(-5, "number"))
    self.assertEqual(None, DataTable.CoerceValue(None, "number"))
    self.assertEqual((5, u"5$"),
                     DataTable.CoerceValue((5, "5$"), "number"))

    self.assertEqual("-5", DataTable.CoerceValue(-5, "string"))
    self.assertEqual("abc", DataTable.CoerceValue("abc", "string"))
    self.assertEqual(None, DataTable.CoerceValue(None, "string"))

    self.assertEqual(date(2010, 1, 2),
                     DataTable.CoerceValue(date(2010, 1, 2), "date"))
    self.assertEqual(date(2001, 2, 3),
                     DataTable.CoerceValue(datetime(2001, 2, 3, 4, 5, 6),
                                           "date"))
    self.assertEqual(None, DataTable.CoerceValue(None, "date"))

    self.assertEqual(time(10, 11, 12),
                     DataTable.CoerceValue(time(10, 11, 12), "timeofday"))
    self.assertEqual(time(3, 4, 5),
                     DataTable.CoerceValue(datetime(2010, 1, 2, 3, 4, 5),
                                           "timeofday"))
    self.assertEqual(None, DataTable.CoerceValue(None, "timeofday"))

    self.assertEqual(datetime(2001, 2, 3, 4, 5, 6, 555000),
                     DataTable.CoerceValue(datetime(2001, 2, 3, 4, 5, 6,
                                                    555000),
                                           "datetime"))
    self.assertEqual(None, DataTable.CoerceValue(None, "datetime"))
    self.assertEqual((None, "none"),
                     DataTable.CoerceValue((None, "none"), "string"))

  def testDifferentStrings(self):
    # Checking escaping of strings in JSON output
    the_strings = ["new\nline",
                   r"one\slash",
                   r"two\\slash",
                   u"unicode eng",
                   u"unicode \u05e2\u05d1\u05e8\u05d9\u05ea",
                   u"unicode \u05e2\u05d1\u05e8\u05d9\u05ea".encode("utf-8"),
                   u'"\u05e2\u05d1\\"\u05e8\u05d9\u05ea"']
    table = DataTable([("a", "string")],
                      [[x] for x in the_strings])

    json_obj = json.loads(table.ToJSon())
    for i, row in enumerate(json_obj["rows"]):
      utf8_str = the_strings[i]
      if isinstance(utf8_str, unicode):
        utf8_str = utf8_str.encode("utf-8")

      out_str = row["c"][0]["v"]
      self.assertEqual(out_str.encode("utf-8"), utf8_str)

  def testColumnTypeParser(self):
    # Checking several wrong formats
    self.assertRaises(DataTableException,
                      DataTable.ColumnTypeParser, 5)
    self.assertRaises(DataTableException,
                      DataTable.ColumnTypeParser, ("a", 5, "c"))
    self.assertRaises(DataTableException,
                      DataTable.ColumnTypeParser, ("a", "blah"))
    self.assertRaises(DataTableException,
                      DataTable.ColumnTypeParser, ("a", "number", "c", "d"))

    # Checking several legal formats
    self.assertEqual({"id": "abc", "label": "abc", "type": "string",
                      "custom_properties": {}},
                     DataTable.ColumnTypeParser("abc"))
    self.assertEqual({"id": "abc", "label": "abc", "type": "string",
                      "custom_properties": {}},
                     DataTable.ColumnTypeParser(("abc",)))
    self.assertEqual({"id": "abc", "label": "bcd", "type": "string",
                      "custom_properties": {}},
                     DataTable.ColumnTypeParser(("abc", "string", "bcd")))
    self.assertEqual({"id": "a", "label": "b", "type": "number",
                      "custom_properties": {}},
                     DataTable.ColumnTypeParser(("a", "number", "b")))
    self.assertEqual({"id": "a", "label": "a", "type": "number",
                      "custom_properties": {}},
                     DataTable.ColumnTypeParser(("a", "number")))
    self.assertEqual({"id": "i", "label": "l", "type": "string",
                      "custom_properties": {"key": "value"}},
                     DataTable.ColumnTypeParser(("i", "string", "l",
                                                 {"key": "value"})))

  def testTableDescriptionParser(self):
    # We expect it to fail with empty lists or dictionaries
    self.assertRaises(DataTableException,
                      DataTable.TableDescriptionParser, {})
    self.assertRaises(DataTableException,
                      DataTable.TableDescriptionParser, [])
    self.assertRaises(DataTableException,
                      DataTable.TableDescriptionParser, {"a": []})
    self.assertRaises(DataTableException,
                      DataTable.TableDescriptionParser, {"a": {"b": {}}})

    # We expect it to fail if we give a non-string at the lowest level
    self.assertRaises(DataTableException,
                      DataTable.TableDescriptionParser, {"a": 5})
    self.assertRaises(DataTableException,
                      DataTable.TableDescriptionParser, [("a", "number"), 6])

    # Some valid examples which mixes both dictionaries and lists
    self.assertEqual(
        [{"id": "a", "label": "a", "type": "date",
          "depth": 0, "container": "iter", "custom_properties": {}},
         {"id": "b", "label": "b", "type": "timeofday",
          "depth": 0, "container": "iter", "custom_properties": {}}],
        DataTable.TableDescriptionParser([("a", "date"), ("b", "timeofday")]))

    self.assertEqual(
        [{"id": "a", "label": "a", "type": "string",
          "depth": 0, "container": "dict", "custom_properties": {}},
         {"id": "b", "label": "b", "type": "number",
          "depth": 1, "container": "iter", "custom_properties": {}},
         {"id": "c", "label": "column c", "type": "string",
          "depth": 1, "container": "iter", "custom_properties": {}}],
        DataTable.TableDescriptionParser({"a": [("b", "number"),
                                                ("c", "string", "column c")]}))

    self.assertEqual(
        [{"id": "a", "label": "column a", "type": "number", "depth": 0,
          "container": "dict", "custom_properties": {}},
         {"id": "b", "label": "column b", "type": "string", "depth": 0,
          "container": "dict", "custom_properties": {}}],
        DataTable.TableDescriptionParser({"a": ("number", "column a"),
                                          "b": ("string", "column b")}))

    self.assertEqual(
        [{"id": "a", "label": "column a", "type": "number",
          "depth": 0, "container": "dict", "custom_properties": {}},
         {"id": "b", "label": "b", "type": "number",
          "depth": 1, "container": "dict", "custom_properties": {}},
         {"id": "c", "label": "c", "type": "string",
          "depth": 1, "container": "dict", "custom_properties": {}}],
        DataTable.TableDescriptionParser({("a", "number", "column a"):
                                          {"b": "number", "c": "string"}}))

    self.assertEqual(
        [{"id": "a", "label": "column a", "type": "number",
          "depth": 0, "container": "dict", "custom_properties": {}},
         {"id": "b", "label": "column b", "type": "string",
          "depth": 1, "container": "scalar", "custom_properties": {}}],
        DataTable.TableDescriptionParser({("a", "number", "column a"):
                                          ("b", "string", "column b")}))

    # Cases that might create ambiguity
    self.assertEqual(
        [{"id": "a", "label": "column a", "type": "number", "depth": 0,
          "container": "dict", "custom_properties": {}}],
        DataTable.TableDescriptionParser({"a": ("number", "column a")}))
    self.assertRaises(DataTableException, DataTable.TableDescriptionParser,
                      {"a": ("b", "number")})

    self.assertEqual(
        [{"id": "a", "label": "a", "type": "string", "depth": 0,
          "container": "dict", "custom_properties": {}},
         {"id": "b", "label": "b", "type": "number", "depth": 1,
          "container": "scalar", "custom_properties": {}}],
        DataTable.TableDescriptionParser({"a": ("b", "number", "b", {})}))

    self.assertEqual(
        [{"id": "a", "label": "a", "type": "string", "depth": 0,
          "container": "dict", "custom_properties": {}},
         {"id": "b", "label": "b", "type": "number", "depth": 1,
          "container": "scalar", "custom_properties": {}}],
        DataTable.TableDescriptionParser({("a",): ("b", "number")}))

  def testAppendData(self):
    # We check a few examples where the format of the data does not match the
    # description and hen a few valid examples. The test for the content itself
    # is done inside the ToJSCode and ToJSon functions.
    table = DataTable([("a", "number"), ("b", "string")])
    self.assertEqual(0, table.NumberOfRows())
    self.assertRaises(DataTableException,
                      table.AppendData, [[1, "a", True]])
    self.assertRaises(DataTableException,
                      table.AppendData, {1: ["a"], 2: ["b"]})
    self.assertEquals(None, table.AppendData([[1, "a"], [2, "b"]]))
    self.assertEqual(2, table.NumberOfRows())
    self.assertEquals(None, table.AppendData([[3, "c"], [4]]))
    self.assertEqual(4, table.NumberOfRows())

    table = DataTable({"a": "number", "b": "string"})
    self.assertEqual(0, table.NumberOfRows())
    self.assertRaises(DataTableException,
                      table.AppendData, [[1, "a"]])
    self.assertRaises(DataTableException,
                      table.AppendData, {5: {"b": "z"}})
    self.assertEquals(None, table.AppendData([{"a": 1, "b": "z"}]))
    self.assertEqual(1, table.NumberOfRows())

    table = DataTable({("a", "number"): [("b", "string")]})
    self.assertEqual(0, table.NumberOfRows())
    self.assertRaises(DataTableException,
                      table.AppendData, [[1, "a"]])
    self.assertRaises(DataTableException,
                      table.AppendData, {5: {"b": "z"}})
    self.assertEquals(None, table.AppendData({5: ["z"], 6: ["w"]}))
    self.assertEqual(2, table.NumberOfRows())

    table = DataTable({("a", "number"): {"b": "string", "c": "number"}})
    self.assertEqual(0, table.NumberOfRows())
    self.assertRaises(DataTableException,
                      table.AppendData, [[1, "a"]])
    self.assertRaises(DataTableException,
                      table.AppendData, {1: ["a", 2]})
    self.assertEquals(None, table.AppendData({5: {"b": "z", "c": 6},
                                              7: {"c": 8},
                                              9: {}}))
    self.assertEqual(3, table.NumberOfRows())

  def testToJSCode(self):
    table = DataTable([("a", "number", "A'"), "b\"", ("c", "timeofday")],
                      [[1],
                       [None, "z", time(1, 2, 3)],
                       [(2, "2$"), "w", time(2, 3, 4)]])
    self.assertEqual(3, table.NumberOfRows())
    self.assertEqual((u"var mytab = new google.visualization.DataTable();\n"
                      u"mytab.addColumn(\"number\", \"A'\", \"a\");\n"
                      u"mytab.addColumn(\"string\", \"b\\\"\", \"b\\\"\");\n"
                      u"mytab.addColumn(\"timeofday\", \"c\", \"c\");\n"
                      u"mytab.addRows(3);\n"
                      u"mytab.setCell(0, 0, 1);\n"
                      u"mytab.setCell(1, 1, \"z\");\n"
                      u"mytab.setCell(1, 2, [1,2,3]);\n"
                      u"mytab.setCell(2, 0, 2, \"2$\");\n"
                      u"mytab.setCell(2, 1, \"w\");\n"
                      u"mytab.setCell(2, 2, [2,3,4]);\n"),
                     table.ToJSCode("mytab"))

    table = DataTable({("a", "number"): {"b": "date", "c": "datetime"}},
                      {1: {},
                       2: {"b": date(1, 2, 3)},
                       3: {"c": datetime(1, 2, 3, 4, 5, 6, 555000)},
                       4: {"c": datetime(1, 2, 3, 4, 5, 6)}})
    self.assertEqual(4, table.NumberOfRows())
    self.assertEqual(("var mytab2 = new google.visualization.DataTable();\n"
                      'mytab2.addColumn("datetime", "c", "c");\n'
                      'mytab2.addColumn("date", "b", "b");\n'
                      'mytab2.addColumn("number", "a", "a");\n'
                      'mytab2.addRows(4);\n'
                      'mytab2.setCell(0, 2, 1);\n'
                      'mytab2.setCell(1, 1, new Date(1,1,3));\n'
                      'mytab2.setCell(1, 2, 2);\n'
                      'mytab2.setCell(2, 0, new Date(1,1,3,4,5,6,555));\n'
                      'mytab2.setCell(2, 2, 3);\n'
                      'mytab2.setCell(3, 0, new Date(1,1,3,4,5,6));\n'
                      'mytab2.setCell(3, 2, 4);\n'),
                     table.ToJSCode("mytab2", columns_order=["c", "b", "a"]))

  def testToJSon(self):
    json_obj = {"cols":
                [{"id": "a", "label": "A", "type": "number"},
                 {"id": "b", "label": "b", "type": "string"},
                 {"id": "c", "label": "c", "type": "boolean"}],
                "rows":
                [{"c": [{"v": 1}, None, None]},
                 {"c": [None, {"v": "z"}, {"v": True}]},
                 {"c": [None, {"v": u"\u05d0"}, None]},
                 {"c": [None, {"v": u"\u05d1"}, None]}]}

    table = DataTable([("a", "number", "A"), "b", ("c", "boolean")],
                      [[1],
                       [None, "z", True],
                       [None, u"\u05d0"],
                       [None, u"\u05d1".encode("utf-8")]])
    self.assertEqual(4, table.NumberOfRows())
    self.assertEqual(json.dumps(json_obj,
                                separators=(",", ":"),
                                ensure_ascii=False).encode("utf-8"),
                     table.ToJSon())
    table.AppendData([[-1, "w", False]])
    self.assertEqual(5, table.NumberOfRows())
    json_obj["rows"].append({"c": [{"v": -1}, {"v": "w"}, {"v": False}]})
    self.assertEqual(json.dumps(json_obj,
                                separators=(",", ":"),
                                ensure_ascii=False).encode("utf-8"),
                     table.ToJSon())

    json_obj = {"cols":
                [{"id": "t", "label": "T", "type": "timeofday"},
                 {"id": "d", "label": "d", "type": "date"},
                 {"id": "dt", "label": "dt", "type": "datetime"}],
                "rows":
                [{"c": [{"v": [1, 2, 3]}, {"v": "Date(1,1,3)"}, None]}]}
    table = DataTable({("d", "date"): [("t", "timeofday", "T"),
                                       ("dt", "datetime")]})
    table.LoadData({date(1, 2, 3): [time(1, 2, 3)]})
    self.assertEqual(1, table.NumberOfRows())
    self.assertEqual(json.dumps(json_obj, separators=(",", ":")),
                     table.ToJSon(columns_order=["t", "d", "dt"]))

    json_obj["rows"] = [
        {"c": [{"v": [2, 3, 4], "f": "time 2 3 4"},
               {"v": "Date(2,2,4)"},
               {"v": "Date(1,1,3,4,5,6,555)"}]},
        {"c": [None, {"v": "Date(3,3,5)"}, None]}]

    table.LoadData({date(2, 3, 4): [(time(2, 3, 4), "time 2 3 4"),
                                    datetime(1, 2, 3, 4, 5, 6, 555000)],
                    date(3, 4, 5): []})
    self.assertEqual(2, table.NumberOfRows())

    self.assertEqual(json.dumps(json_obj, separators=(",", ":")),
                     table.ToJSon(columns_order=["t", "d", "dt"]))

    json_obj = {
        "cols": [{"id": "a\"", "label": "a\"", "type": "string"},
                 {"id": "b", "label": "bb\"", "type": "number"}],
        "rows": [{"c": [{"v": "a1"}, {"v": 1}]},
                 {"c": [{"v": "a2"}, {"v": 2}]},
                 {"c": [{"v": "a3"}, {"v": 3}]}]}
    table = DataTable({"a\"": ("b", "number", "bb\"", {})},
                      {"a1": 1, "a2": 2, "a3": 3})
    self.assertEqual(3, table.NumberOfRows())
    self.assertEqual(json.dumps(json_obj, separators=(",", ":")),
                     table.ToJSon())

  def testCustomProperties(self):
    # The json of the initial data we load to the table.
    json_obj = {"cols": [{"id": "a",
                          "label": "A",
                          "type": "number",
                          "p": {"col_cp": "col_v"}},
                         {"id": "b", "label": "b", "type": "string"},
                         {"id": "c", "label": "c", "type": "boolean"}],
                "rows": [{"c": [{"v": 1},
                                None,
                                {"v": None,
                                 "p": {"null_cp": "null_v"}}],
                          "p": {"row_cp": "row_v"}},
                         {"c": [None,
                                {"v": "z", "p": {"cell_cp": "cell_v"}},
                                {"v": True}]},
                         {"c": [{"v": 3}, None, None],
                          "p": {"row_cp2": "row_v2"}}],
                "p": {"global_cp": "global_v"}}
    jscode = ("var mytab = new google.visualization.DataTable();\n"
              "mytab.setTableProperties({\"global_cp\":\"global_v\"});\n"
              "mytab.addColumn(\"number\", \"A\", \"a\");\n"
              "mytab.setColumnProperties(0, {\"col_cp\":\"col_v\"});\n"
              "mytab.addColumn(\"string\", \"b\", \"b\");\n"
              "mytab.addColumn(\"boolean\", \"c\", \"c\");\n"
              "mytab.addRows(3);\n"
              "mytab.setCell(0, 0, 1);\n"
              "mytab.setCell(0, 2, null, null, {\"null_cp\":\"null_v\"});\n"
              "mytab.setRowProperties(0, {\"row_cp\":\"row_v\"});\n"
              "mytab.setCell(1, 1, \"z\", null, {\"cell_cp\":\"cell_v\"});\n"
              "mytab.setCell(1, 2, true);\n"
              "mytab.setCell(2, 0, 3);\n"
              "mytab.setRowProperties(2, {\"row_cp2\":\"row_v2\"});\n")

    table = DataTable([("a", "number", "A", {"col_cp": "col_v"}), "b",
                       ("c", "boolean")],
                      custom_properties={"global_cp": "global_v"})
    table.AppendData([[1, None, (None, None, {"null_cp": "null_v"})]],
                     custom_properties={"row_cp": "row_v"})
    table.AppendData([[None, ("z", None, {"cell_cp": "cell_v"}), True], [3]])
    table.SetRowsCustomProperties(2, {"row_cp2": "row_v2"})
    self.assertEqual(json.dumps(json_obj, separators=(",", ":")),
                     table.ToJSon())
    self.assertEqual(jscode, table.ToJSCode("mytab"))

  def testToCsv(self):
    init_data_csv = "\r\n".join(["A,\"b\"\"\",c",
                                 "1,,",
                                 ",zz'top,true",
                                 ""])
    table = DataTable([("a", "number", "A"), "b\"", ("c", "boolean")],
                      [[(1, "$1")], [None, "zz'top", True]])
    self.assertEqual(init_data_csv, table.ToCsv())
    table.AppendData([[-1, "w", False]])
    init_data_csv = "%s%s\r\n" % (init_data_csv, "-1,w,false")
    self.assertEquals(init_data_csv, table.ToCsv())

    init_data_csv = "\r\n".join([
        "T,d,dt",
        "01:02:03,1901-02-03,",
        "\"time \"\"2 3 4\"\"\",1902-03-04,1901-02-03 04:05:06",
        ",1903-04-05,",
        ""])
    table = DataTable({("d", "date"): [("t", "timeofday", "T"),
                                       ("dt", "datetime")]})
    table.LoadData({date(1901, 2, 3): [time(1, 2, 3)],
                    date(1902, 3, 4): [(time(2, 3, 4), 'time "2 3 4"'),
                                       datetime(1901, 2, 3, 4, 5, 6)],
                    date(1903, 4, 5): []})
    self.assertEqual(init_data_csv, table.ToCsv(columns_order=["t", "d", "dt"]))

  def testToTsvExcel(self):
    table = DataTable({("d", "date"): [("t", "timeofday", "T"),
                                       ("dt", "datetime")]})
    table.LoadData({date(1901, 2, 3): [time(1, 2, 3)],
                    date(1902, 3, 4): [(time(2, 3, 4), 'time "2 3 4"'),
                                       datetime(1901, 2, 3, 4, 5, 6)],
                    date(1903, 4, 5): []})
    self.assertEqual(table.ToCsv().replace(",", "\t").encode("UTF-16LE"),
                     table.ToTsvExcel())

  def testToHtml(self):
    html_table_header = "<html><body><table border=\"1\">"
    html_table_footer = "</table></body></html>"
    init_data_html = html_table_header + (
        "<thead><tr>"
        "<th>A&lt;</th><th>b&gt;</th><th>c</th>"
        "</tr></thead>"
        "<tbody>"
        "<tr><td>$1</td><td></td><td></td></tr>"
        "<tr><td></td><td>&lt;z&gt;</td><td>true</td></tr>"
        "</tbody>") + html_table_footer
    table = DataTable([("a", "number", "A<"), "b>", ("c", "boolean")],
                      [[(1, "$1")], [None, "<z>", True]])
    self.assertEqual(init_data_html.replace("\n", ""), table.ToHtml())

    init_data_html = html_table_header + (
        "<thead><tr>"
        "<th>T</th><th>d</th><th>dt</th>"
        "</tr></thead>"
        "<tbody>"
        "<tr><td>01:02:03</td><td>0001-02-03</td><td></td></tr>"
        "<tr><td>time 2 3 4</td><td>0002-03-04</td>"
        "<td>0001-02-03 04:05:06</td></tr>"
        "<tr><td></td><td>0003-04-05</td><td></td></tr>"
        "</tbody>") + html_table_footer
    table = DataTable({("d", "date"): [("t", "timeofday", "T"),
                                       ("dt", "datetime")]})
    table.LoadData({date(1, 2, 3): [time(1, 2, 3)],
                    date(2, 3, 4): [(time(2, 3, 4), "time 2 3 4"),
                                    datetime(1, 2, 3, 4, 5, 6)],
                    date(3, 4, 5): []})
    self.assertEqual(init_data_html.replace("\n", ""),
                     table.ToHtml(columns_order=["t", "d", "dt"]))

  def testOrderBy(self):
    data = [("b", 3), ("a", 3), ("a", 2), ("b", 1)]
    description = ["col1", ("col2", "number", "Second Column")]
    table = DataTable(description, data)

    table_num_sorted = DataTable(description,
                                 sorted(data, key=lambda x: (x[1], x[0])))

    table_str_sorted = DataTable(description,
                                 sorted(data, key=lambda x: x[0]))

    table_diff_sorted = DataTable(description,
                                  sorted(sorted(data, key=lambda x: x[1]),
                                         key=lambda x: x[0], reverse=True))

    self.assertEqual(table_num_sorted.ToJSon(),
                     table.ToJSon(order_by=("col2", "col1")))
    self.assertEqual(table_num_sorted.ToJSCode("mytab"),
                     table.ToJSCode("mytab", order_by=("col2", "col1")))

    self.assertEqual(table_str_sorted.ToJSon(), table.ToJSon(order_by="col1"))
    self.assertEqual(table_str_sorted.ToJSCode("mytab"),
                     table.ToJSCode("mytab", order_by="col1"))

    self.assertEqual(table_diff_sorted.ToJSon(),
                     table.ToJSon(order_by=[("col1", "desc"), "col2"]))
    self.assertEqual(table_diff_sorted.ToJSCode("mytab"),
                     table.ToJSCode("mytab",
                                    order_by=[("col1", "desc"), "col2"]))

  def testToJSonResponse(self):
    description = ["col1", "col2", "col3"]
    data = [("1", "2", "3"), ("a", "b", "c"), ("One", "Two", "Three")]
    req_id = 4
    table = DataTable(description, data)

    start_str_default = r"google.visualization.Query.setResponse"
    start_str_handler = r"MyHandlerFunction"

    json_str = table.ToJSon().strip()

    json_response = table.ToJSonResponse(req_id=req_id)

    self.assertEquals(json_response.find(start_str_default + "("), 0)

    json_response_obj = json.loads(json_response[len(start_str_default) + 1:-2])
    self.assertEquals(json_response_obj["table"], json.loads(json_str))
    self.assertEquals(json_response_obj["version"], "0.6")
    self.assertEquals(json_response_obj["reqId"], str(req_id))
    self.assertEquals(json_response_obj["status"], "ok")

    json_response = table.ToJSonResponse(req_id=req_id,
                                         response_handler=start_str_handler)

    self.assertEquals(json_response.find(start_str_handler + "("), 0)
    json_response_obj = json.loads(json_response[len(start_str_handler) + 1:-2])
    self.assertEquals(json_response_obj["table"], json.loads(json_str))

  def testToResponse(self):
    description = ["col1", "col2", "col3"]
    data = [("1", "2", "3"), ("a", "b", "c"), ("One", "Two", "Three")]
    table = DataTable(description, data)

    self.assertEquals(table.ToResponse(), table.ToJSonResponse())
    self.assertEquals(table.ToResponse(tqx="out:csv"), table.ToCsv())
    self.assertEquals(table.ToResponse(tqx="out:html"), table.ToHtml())
    self.assertRaises(DataTableException, table.ToResponse, tqx="version:0.1")
    self.assertEquals(table.ToResponse(tqx="reqId:4;responseHandler:handle"),
                      table.ToJSonResponse(req_id=4, response_handler="handle"))
    self.assertEquals(table.ToResponse(tqx="out:csv;reqId:4"), table.ToCsv())
    self.assertEquals(table.ToResponse(order_by="col2"),
                      table.ToJSonResponse(order_by="col2"))
    self.assertEquals(table.ToResponse(tqx="out:html",
                                       columns_order=("col3", "col2", "col1")),
                      table.ToHtml(columns_order=("col3", "col2", "col1")))
    self.assertRaises(ValueError, table.ToResponse, tqx="SomeWrongTqxFormat")
    self.assertRaises(DataTableException, table.ToResponse, tqx="out:bad")


if __name__ == "__main__":
  unittest.main()

########NEW FILE########
__FILENAME__ = reports
from copy import deepcopy

from django.db import models
from django.utils.datastructures import SortedDict
from django.utils.encoding import StrAndUnicode
from django.utils.safestring import mark_safe

from .charts import Chart

__all__ = ('BaseReport', 'Report')


def pretty_name(name):
    """Converts 'first_name' to 'First name'"""
    if not name:
        return u''
    return name.replace('_', ' ').capitalize()
    

def get_declared_charts(bases, attrs, with_base_charts=True):
    """
    Create a list of report chart instances from the passed in 'attrs', plus any
    similar charts on the base classes (in 'bases'). This is used by the Report
    metaclass.
    
    If 'with_base_charts' is True, all charts from the bases are used.
    Otherwise, only charts in the 'declared_charts' attribute on the bases are
    used.
    """
    charts = [(chart_name, attrs.pop(chart_name)) for chart_name, obj in attrs.items() if isinstance(obj, Chart)]
    
    charts.sort(key=lambda x: x[1].creation_counter)
    
    # If this class is subclassing another Report, add that Report's charts.
    # Note that we loop over the bases in *reverse*. This is necessary in order
    # to preserver the correct order of charts.
    if with_base_charts:
        for base in bases[::-1]:
            if hasattr(base, 'base_charts'):
                charts = base.base_charts.items() + charts
    else:
        for base in bases[::-1]:
            if hasattr(base, 'declared_charts'):
                charts = base.declared_charts.items() + charts
    
    return SortedDict(charts)


class DeclarativeChartsMetaclass(type):
    """
    Metaclass that converts Chart attributes to a dictionary called
    'base_charts', taking into account parent class 'base_charts' as well.
    """
    def __new__(cls, name, bases, attrs):
        attrs['base_charts'] = get_declared_charts(bases, attrs)
        new_class = super(DeclarativeChartsMetaclass,
                          cls).__new__(cls, name, bases, attrs)
        
        return new_class


class BaseReport(StrAndUnicode):
    def __init__(self, data=None, prefix=None):
        self.data = data or {}
        self.prefix = prefix
        
        # The base_charts class attribute is the *class-wide* definition of
        # charts. Because a particular *instance* of the class might want to
        # alter self.charts, we create self.charts here by copying base_charts.
        # Instances should always modify self.charts; they should not modify
        # self.base_charts
        self.charts = deepcopy(self.base_charts)
    
    def __unicode__(self):
        return "WHOLE REPORT PRINTING NOT YET IMPLEMENTED" # TODO
    
    def __iter__(self):
        for name, chart in self.charts.items():
            data = self._get_chart_data(name)
            yield BoundChart(self, chart, name, data)
            
    def __getitem__(self, name):
        "Returns a BoundChart with the given name"
        try:
            chart = self.charts[name]
        except KeyError:
            raise KeyError('Key %r not found in Report' % name)
            
        data = self._get_chart_data(name)
        return BoundChart(self, chart, name, data, self.prefix)
    
    def set_prefix(self, prefix):
        self.prefix = prefix
    
    def _get_chart_data(self, name):
        callback_name = 'get_data_for_%s' % name
        if name in self.data:
            data = self.data[name]
        elif hasattr(self, callback_name):
            data = getattr(self, callback_name)()
            self.data[name] = data
        else:
            data = None
            
        return data
    
    def setup(self, request):
        pass
    
    def api_setup(self, request):
        return self.setup(request)

        
class Report(BaseReport):
    "A collection of charts, plus their associated data."
    # This is a separate class from BaseReport in order to abstract the way
    # self.charts is specified. This class (Report) is the one that does the
    # fancy metaclass stuff purely for the semantic sugar -- it allows one to
    # define a report using declarative syntax.
    # BaseReport itself has no way of designating self.charts
    __metaclass__ = DeclarativeChartsMetaclass
    
    
class BoundChart(StrAndUnicode):
    "A chart plus data"
    def __init__(self, report, chart, name, data=None, prefix=None):
        self.report = report
        self.chart = chart
        self.name = name
        self.data = data
        self.prefix = prefix
        self.attrs = self.chart.attrs
        self.options = self.chart.options
        self.renderer_options = self.chart.renderer_options
        
        if self.chart.title is None:
            self.title = pretty_name(name)
        else:
            self.title = self.chart.title
        
    def __unicode__(self):
        """Renders this chart"""
        return self.render()
    
    @property
    def chart_id(self):
        if self.prefix:
            chart_id = 'chartid_%s_%s' % (self.prefix, self.name)
        else:
            chart_id = 'chartid_%s' % self.name
            
        return chart_id
    
    def render(self):
        base_renderer = getattr(self.report, 'renderer', None)
        
        return mark_safe(self.chart.render(self.chart_id, self.data, base_renderer=base_renderer))

########NEW FILE########
__FILENAME__ = reports
from report_tools.reports import Report
from report_tools.chart_data import ChartData
from report_tools.renderers.googlecharts import GoogleChartsRenderer
from report_tools import charts



class GenericReport(Report):
    template_chart = charts.TemplateChart(template="templates/examples/template_chart.html")

    def get_data_for_template_chart(self):
        template_context = {
            'pony_types': ["Blue", "Pink", "Magical"]
        }

        return template_context


class GoogleChartsReport(Report):
    renderer = GoogleChartsRenderer

    pie_chart = charts.PieChart(width="500")
    column_chart = charts.ColumnChart(width="500")
    line_chart = charts.LineChart(width="500")
    bar_chart = charts.BarChart(width="500")

    def get_single_series_data(self):
        data = ChartData()

        data.add_column("Pony Type")
        data.add_column("Population")

        data.add_row(["Blue", 20])
        data.add_row(["Pink", 20])
        data.add_row(["Magical", 1])

        return data

    def get_multi_series_data(self):
        data = ChartData()

        data.add_column("Pony Type")
        data.add_column("Australian Population")
        data.add_column("Switzerland Population")
        data.add_column("USA Population")

        data.add_row(["Blue", (5, {'formatted_value': "Five"}), 10, 5])
        data.add_row(["Pink", 10, 2, 8])
        data.add_row(["Magical", 1, 0, 0])

        return data

    def get_data_for_pie_chart(self):
        return self.get_single_series_data()

    def get_data_for_column_chart(self):
        return self.get_multi_series_data()

    def get_data_for_bar_chart(self):
        return self.get_multi_series_data()

    def get_data_for_line_chart(self):
        return self.get_multi_series_data()
########NEW FILE########
__FILENAME__ = test_all
from django.test import TestCase
from django.test.client import RequestFactory
from report_tools.tests.reports import GoogleChartsReport
from report_tools import api
from report_tools.tests.views import GoogleChartsReportView



class GoogleChartsTest(TestCase):
    def test_pie_chart(self):
        """
        Test google charts rendering of a pie chart
        """
        report = GoogleChartsReport()
        chart_html = u'%s' % report['pie_chart']

        self.assertRegexpMatches(chart_html, r'google\.visualization\.PieChart')

    def test_column_chart(self):
        """
        Test google chart rendering of a column chart
        """
        report = GoogleChartsReport()
        chart_html = u'%s' % report['column_chart']

        self.assertRegexpMatches(chart_html, r'google\.visualization\.ColumnChart')

    def test_line_chart(self):
        """
        Test google chart rendering of a column chart
        """
        report = GoogleChartsReport()
        chart_html = u'%s' % report['line_chart']

        self.assertRegexpMatches(chart_html, r'google\.visualization\.LineChart')

    def test_bar_chart(self):
        """
        Test google chart rendering of a bar chart
        """
        report = GoogleChartsReport()
        chart_html = u'%s' % report['bar_chart']

        self.assertRegexpMatches(chart_html, r'google\.visualization\.BarChart')


class APITest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')

        api.register(GoogleChartsReportView)

    def test_internal_api_get(self):
        """
        Test the internal get_chart function
        """
        chart = api.get_chart(self.request, 'google_charts_report', 'pie_chart')
        chart_html = u'%s' % chart
        self.assertRegexpMatches(chart_html, r'google\.visualization\.PieChart')

    def test_report_not_found(self):
        """
        Make sure asking for a non-existant report throws an appropriate error
        """
        with self.assertRaises(api.ReportNotFoundError):
            chart = api.get_chart(self.request, 'doogle_charts_report', 'pie_chart')

    def test_chart_not_found(self):
        """
        Make sure asking for a non-existant chart throws an appropriate error
        """
        with self.assertRaises(api.ChartNotFoundError):
            chart = api.get_chart(self.request, 'google_charts_report', 'delicious_pie_chart')

########NEW FILE########
__FILENAME__ = views
from report_tools.views import ReportView
from report_tools import api
from report_tools.tests.reports import GoogleChartsReport



class GoogleChartsReportView(ReportView):
    api_key = 'google_charts_report'

    def get_report(self, request):
        return GoogleChartsReport()

########NEW FILE########
__FILENAME__ = urls
from views import ReportAPIDispatchView

from django.conf.urls import *
from django.conf import settings



urlpatterns = patterns('',
    url(r'^(?P<report_api_key>\w+)/(?P<chart_name>\w+)/$', ReportAPIDispatchView.as_view(), name="reports-api-chart"),
)

########NEW FILE########
__FILENAME__ = views
import functools

try:
    import json
except ImportError:
    import simplejson as json

from django.http import HttpResponse, Http404
from django.views.generic import View
from django.utils.decorators import classonlymethod
from django.utils.safestring import mark_safe




from report_tools.api import (ChartNotFoundError, report_api_registry,
    OVERRIDE_PARAMS__CHART_HEIGHT, OVERRIDE_PARAMS__CHART_WIDTH,
    OVERRIDE_PARAMS__CHART_TITLE)


class ChartPermissionError(Exception):
    pass


class ReportView(View):
    def security_check(self, request):
        return True
    
    def get_report(self, request, prefix=None):
        raise NotImplementedError
    
    def _get_report(self, request, prefix=None):
        report = self.get_report(request)
        
        if prefix:
            report.set_prefix(prefix)
    
        chart_height = request.GET.get(OVERRIDE_PARAMS__CHART_HEIGHT, None)
        chart_width = request.GET.get(OVERRIDE_PARAMS__CHART_WIDTH, None)
        chart_title = request.GET.get(OVERRIDE_PARAMS__CHART_TITLE, None)
        
        for chart_name, chart in report.charts.iteritems():
            if chart_height is not None:
                chart.options['height'] = chart_height
            if chart_width is not None:
                chart.options['width'] = chart_width
            if chart_title is not None:
                chart.options['title'] = chart_title
                
        return report
    
    def get_chart(self, request, chart_name, prefix=None):
        if not self.security_check(request):
            raise ChartPermissionError("Chart access forbidden")
        
        report = self._get_report(request, prefix)

        try:
            chart = report[chart_name]
        except KeyError:
            raise ChartNotFoundError("Chart %s not found in this report" % chart_name)
        
        return chart
    
    def api_get(self, request, chart_name, prefix=None):
        chart = self.get_chart(request, chart_name, prefix)

        if chart:
            html = mark_safe(u'%s' % chart)
            attrs = chart.attrs
        else:
            html = mark_safe(self.security_failure_message)
            attrs = {}
        
        return_data = {
            'html': html,
            'attrs': attrs,
        }
        
        return HttpResponse(json.dumps(return_data), mimetype='application/javascript')

    @classonlymethod
    def as_api_view(cls, **initkwargs):
        """
        Main entry point for an api request-response process.
        """
        # sanitize keyword arguments
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError(u"You tried to pass in the %s method name as a "
                                u"keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError(u"%s() received an invalid keyword %r" % (
                    cls.__name__, key))

        def view(request, *args, **kwargs):
            self = cls(**initkwargs)
            return self.api_dispatch(request, *args, **kwargs)

        # take name and docstring from class
        functools.update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        functools.update_wrapper(view, cls.dispatch, assigned=())
        return view
    
    def dispatch(self, request, *args, **kwargs):
        # Try to dispatch to the right method; if a method doesn't exist,
        # defer to the error handler. Also defer to the error handler if the
        # request method isn't on the approved list.
        if request.method.lower() in self.http_method_names:
            if '_format' in request.GET:
                method_name = request.method.lower() + '_' + request.GET['_format'] + '_format'
            else:
                method_name = request.method.lower()
            handler = getattr(self, method_name, self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        self.request = request
        self.args = args
        self.kwargs = kwargs
        return handler(request, *args, **kwargs)
       
    def api_dispatch(self, request, *args, **kwargs):
        # Try to dispatch to the right api method; if a method doesn't exist,
        # defer to the error handler. Also defer to the error handler if the
        # request method isn't on the approved list.
        if request.method.lower() in self.http_method_names:
            method_name = 'api_' + request.method.lower()
            handler = getattr(self, method_name, self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        self.request = request
        self.args = args
        self.kwargs = kwargs
        return handler(request, *args, **kwargs)
    

class ReportAPIDispatchView(View):
    def dispatch(self, request, report_api_key, chart_name):
        report_view_class = report_api_registry.get_report_view_class(report_api_key)

        if not report_view_class:
            raise Http404
        
        report_view = report_view_class()
        return report_view.api_dispatch(request, chart_name)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproj.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = runtests
#This file mainly exists to allow python setup.py test to work.
import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'testproj.settings'
test_dir = os.path.dirname(__file__)
sys.path.insert(0, test_dir)

from django.test.utils import get_runner
from django.conf import settings

def runtests():
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, interactive=True)
    failures = test_runner.run_tests(['report_tools'])
    sys.exit(bool(failures))

if __name__ == '__main__':
    runtests()

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = reports
from report_tools.reports import Report
from report_tools.chart_data import ChartData
from report_tools.renderers.googlecharts import GoogleChartsRenderer
from report_tools import charts



class MyReport(Report):
    renderer = GoogleChartsRenderer

    pie_chart = charts.PieChart(title="Pony Populations", width="500")
    template_chart = charts.TemplateChart(title="Pony Types", template="core/template_chart.html")
    column_chart = charts.ColumnChart(title="Pony Populations", width="500")
    multiseries_column_chart = charts.ColumnChart(title="Pony Populations by Country", width="500")
    bar_chart = charts.BarChart(title="Pony Populations", width="500")
    multiseries_bar_chart = charts.BarChart(title="Pony Populations by Country", width="500")
    line_chart = charts.LineChart(title="Blue Pony Population - 2009-2012", width="500")
    multiseries_line_chart = charts.LineChart(title="Pony Populations - 2009-2012", width="500")
    naughty_pie_chart = charts.PieChart(title="Pony </script>Populations", width="500")

    def get_data_for_line_chart(self):
        data = ChartData()

        data.add_column("Test Period")
        data.add_column("Blue Pony Population")

        data.add_row(["2009-10", 20])
        data.add_row(["2010-11", 18])
        data.add_row(["2011-12", 100])

        return data

    def get_data_for_multiseries_line_chart(self):
        data = ChartData()

        data.add_column("Test Period")
        data.add_column("Blue Pony Population")
        data.add_column("Pink Pony Population")
        data.add_column("Magical Pony Population")

        data.add_row(["2009-10", 20, 10, 50])
        data.add_row(["2010-11", 18, 8, 60])
        data.add_row(["2011-12", 100, 120, 2])

        return data

    def get_data_for_bar_chart(self):
        data = ChartData()

        data.add_column("Pony Type")
        data.add_column("Population")

        data.add_row(["Blue", 20])
        data.add_row(["Pink", 20])
        data.add_row(["Magical", 1])

        return data

    def get_data_for_multiseries_bar_chart(self):
        data = ChartData()

        data.add_column("Pony Type")
        data.add_column("Australian Population")
        data.add_column("Switzerland Population")
        data.add_column("USA Population")

        data.add_row(["Blue", 5, 10, 5])
        data.add_row(["Pink", 10, 2, 8])
        data.add_row(["Magical", 1, 0, 0])

        return data

    def get_data_for_column_chart(self):
        data = ChartData()

        data.add_column("Pony Type")
        data.add_column("Population")

        data.add_row(["Blue", 20])
        data.add_row(["Pink", 20])
        data.add_row(["Magical", 1])

        return data

    def get_data_for_multiseries_column_chart(self):
        data = ChartData()

        data.add_column("Pony Type")
        data.add_column("Australian Population")
        data.add_column("Switzerland Population")
        data.add_column("USA Population")

        data.add_row(["Blue", 5, 10, 5])
        data.add_row(["Pink", 10, 2, 8])
        data.add_row(["Magical", 1, 0, 0])

        return data

    def get_data_for_pie_chart(self):
        data = ChartData()

        data.add_column("Pony Type")
        data.add_column("Population")

        data.add_row(["Blue", 20])
        data.add_row(["Pink", 20])
        data.add_row(["Magical", 1])

        return data

    def get_data_for_naughty_pie_chart(self):
        data = ChartData()

        data.add_column("Pony</script> &&&Type")
        data.add_column("Population")

        data.add_row(["Blue", 20])
        data.add_row(["Pink</script>&&&", 20])
        data.add_row(["Magical", 1])

        return data

    def get_data_for_template_chart(self):
        pony_types = [
            ('Blue', 'Equus Caeruleus'),
            ('Pink', 'Equus Roseus'),
            ('Magical', 'Equus Magica')
        ]

        template_context = {
            'pony_types': pony_types
        }

        return template_context

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
from django.shortcuts import render
from report_tools.views import ReportView
from report_tools import api
from reports import MyReport



class MyReportView(ReportView):
    api_key = 'my_report'

    def get_report(self, request):
        return MyReport()

    def get(self, request):
        template = "core/index.html"
        report = self.get_report(request)
        context = {'report': report}

        return render(request, template, context)

api.register(MyReportView)

########NEW FILE########
__FILENAME__ = settings
# Django settings for testproj project.
import os
import sys


PROJECT_ROOT = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "../../"))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'db.sqlite',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'pe$b$-144ojvq9tdij+l_-9#_l^rk%-8b=niqw%=cc-iq==4ze'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'testproj.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'testproj.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, "templates"),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'report_tools',
    'testproj.core',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from testproj.core.views import MyReportView

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testproj.views.home', name='home'),
    # url(r'^testproj/', include('testproj.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),

    url(r'^$', MyReportView.as_view(), name='index'),
    url(r'^api/', include('report_tools.urls')),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for testproj project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproj.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
