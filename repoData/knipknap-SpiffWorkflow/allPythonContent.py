__FILENAME__ = conf
# -*- coding: utf-8 -*-
from __future__ import division
# -*- coding: utf-8 -*-
#
# Sphinx documentation build configuration file, created by
# sphinx-quickstart.py on Sat Mar  8 21:47:50 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys, os, re

# If your extensions are in another directory, add it here.
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.addons.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'SpiffWorkflow'
copyright = '2012 ' + ', '.join(open('../AUTHORS').readlines())

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
import SpiffWorkflow
version = SpiffWorkflow.__version__
# The full version, including alpha/beta/rc tags.
release = version

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

show_authors = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'friendly'


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'sphinxdoc.css'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['figures']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Content template for the index page.
html_index = 'index.html'

# Custom sidebar templates, maps page names to templates.
html_sidebars = {'index': 'indexsidebar.html'}

# Additional templates that should be rendered to pages, maps page names to
# templates.
html_additional_pages = {'index': 'index.html'}

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

html_use_opensearch = 'http://sphinx.pocoo.org'

# Output file base name for HTML help builder.
htmlhelp_basename = 'Sphinxdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [('contents', 'sphinx.tex', 'Sphinx Documentation',
                    'Georg Brandl', 'manual', 1)]

latex_logo = '_static/sphinx.png'

#latex_use_parts = True

# Additional stuff for the LaTeX preamble.
latex_elements = {
    'fontpkg': '\\usepackage{palatino}'
}

# Documents to append as an appendix to all manuals.
#latex_appendices = []


# Extension interface
# -------------------

from sphinx import addnodes

dir_sig_re = re.compile(r'\.\. ([^:]+)::(.*)$')

def parse_directive(env, sig, signode):
    if not sig.startswith('.'):
        dec_sig = '.. %s::' % sig
        signode += addnodes.desc_name(dec_sig, dec_sig)
        return sig
    m = dir_sig_re.match(sig)
    if not m:
        signode += addnodes.desc_name(sig, sig)
        return sig
    name, args = m.groups()
    dec_name = '.. %s::' % name
    signode += addnodes.desc_name(dec_name, dec_name)
    signode += addnodes.desc_addname(args, args)
    return name


def parse_role(env, sig, signode):
    signode += addnodes.desc_name(':%s:' % sig, ':%s:' % sig)
    return sig


event_sig_re = re.compile(r'([a-zA-Z-]+)\s*\((.*)\)')

def parse_event(env, sig, signode):
    m = event_sig_re.match(sig)
    if not m:
        signode += addnodes.desc_name(sig, sig)
        return sig
    name, args = m.groups()
    signode += addnodes.desc_name(name, name)
    plist = addnodes.desc_parameterlist()
    for arg in args.split(','):
        arg = arg.strip()
        plist += addnodes.desc_parameter(arg, arg)
    signode += plist
    return name


def setup(app):
    from sphinx.ext.autodoc import cut_lines
    app.connect('autodoc-process-docstring', cut_lines(4, what=['module']))
    app.add_description_unit('directive', 'dir', 'pair: %s; directive', parse_directive)
    app.add_description_unit('role', 'role', 'pair: %s; role', parse_role)
    app.add_description_unit('confval', 'confval', 'pair: %s; configuration value')
    app.add_description_unit('event', 'event', 'pair: %s; event', parse_event)
########NEW FILE########
__FILENAME__ = BpmnScriptEngine
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.operators import Operator

class BpmnScriptEngine(object):
    """
    Used during execution of a BPMN workflow to evaluate condition / value expressions. These are used by
    Gateways, and by Catching Events (non-message ones).

    Also used to execute scripts.

    If you are uncomfortable with the use of eval() and exec, then you should provide a specialised
    subclass that parses and executes the scripts / expressions in a mini-language of your own.
    """

    def evaluate(self, task, expression):
        """
        Evaluate the given expression, within the context of the given task and return the result.
        """
        if isinstance(expression, Operator):
            return expression._matches(task)
        else:
            return self._eval(task, expression, **task.data)

    def execute(self, task, script):
        """
        Execute the script, within the context of the specified task
        """
        exec(script)

    def _eval(self, task, expression, **kwargs):
        locals().update(kwargs)
        return eval(expression)


########NEW FILE########
__FILENAME__ = BpmnWorkflow
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.Task import Task
from SpiffWorkflow.Workflow import Workflow
from SpiffWorkflow.bpmn.BpmnScriptEngine import BpmnScriptEngine

class BpmnWorkflow(Workflow):
    """
    The engine that executes a BPMN workflow. This specialises the standard Spiff Workflow class
    with a few extra methods and attributes.
    """

    def __init__(self, workflow_spec, name=None, script_engine=None, read_only=False, **kwargs):
        """
        Constructor.

        :param script_engine: set to an instance of BpmnScriptEngine if you need a specialised
        version. Defaults to a new BpmnScriptEngine instance.

        :param read_only: If this parameter is set then the workflow state cannot change. It
        can only be queried to find out about the current state. This is used in conjunction with
        the CompactWorkflowSerializer to provide read only access to a previously saved workflow.
        """
        super(BpmnWorkflow, self).__init__(workflow_spec, **kwargs)
        self.name = name or workflow_spec.name
        self.script_engine = script_engine or BpmnScriptEngine()
        self._busy_with_restore = False
        self.read_only = read_only

    def accept_message(self, message):
        """
        Indicate to the workflow that a message has been received. The message will be processed
        by any waiting Intermediate or Boundary Message Events, that are waiting for the message.
        """
        assert not self.read_only
        self.refresh_waiting_tasks()
        self.do_engine_steps()
        for my_task in Task.Iterator(self.task_tree, Task.WAITING):
            my_task.task_spec.accept_message(my_task, message)

    def do_engine_steps(self):
        """
        Execute any READY tasks that are engine specific (for example, gateways or script tasks).
        This is done in a loop, so it will keep completing those tasks until there are only
        READY User tasks, or WAITING tasks left.
        """
        assert not self.read_only
        engine_steps = list([t for t in self.get_tasks(Task.READY) if self._is_engine_task(t.task_spec)])
        while engine_steps:
            for task in engine_steps:
                task.complete()
            engine_steps = list([t for t in self.get_tasks(Task.READY) if self._is_engine_task(t.task_spec)])

    def refresh_waiting_tasks(self):
        """
        Refresh the state of all WAITING tasks. This will, for example, update Catching Timer Events
        whose waiting time has passed.
        """
        assert not self.read_only
        for my_task in self.get_tasks(Task.WAITING):
            my_task.task_spec._update_state(my_task)

    def get_ready_user_tasks(self):
        """
        Returns a list of User Tasks that are READY for user action
        """
        return [t for t in self.get_tasks(Task.READY) if not self._is_engine_task(t.task_spec)]

    def get_waiting_tasks(self):
        """
        Returns a list of all WAITING tasks
        """
        return self.get_tasks(Task.WAITING)

    def _is_busy_with_restore(self):
        if self.outer_workflow == self:
            return self._busy_with_restore
        return self.outer_workflow._is_busy_with_restore()

    def _is_engine_task(self, task_spec):
        return not hasattr(task_spec, 'is_engine_task') or task_spec.is_engine_task()

    def _task_completed_notify(self, task):
        assert (not self.read_only) or self._is_busy_with_restore()
        super(BpmnWorkflow, self)._task_completed_notify(task)

    def _task_cancelled_notify(self, task):
        assert (not self.read_only) or self._is_busy_with_restore()



########NEW FILE########
__FILENAME__ = BpmnParser
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import glob
from SpiffWorkflow.bpmn.BpmnWorkflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException
from SpiffWorkflow.bpmn.specs.BoundaryEvent import BoundaryEvent
from SpiffWorkflow.bpmn.specs.CallActivity import CallActivity
from SpiffWorkflow.bpmn.specs.ExclusiveGateway import ExclusiveGateway
from SpiffWorkflow.bpmn.specs.InclusiveGateway import InclusiveGateway
from SpiffWorkflow.bpmn.specs.IntermediateCatchEvent import IntermediateCatchEvent
from SpiffWorkflow.bpmn.specs.ManualTask import ManualTask
from SpiffWorkflow.bpmn.specs.NoneTask import NoneTask
from SpiffWorkflow.bpmn.specs.ParallelGateway import ParallelGateway
from SpiffWorkflow.bpmn.specs.ScriptTask import ScriptTask
from SpiffWorkflow.bpmn.specs.StartEvent import StartEvent
from SpiffWorkflow.bpmn.specs.UserTask import UserTask
from SpiffWorkflow.bpmn.specs.EndEvent import EndEvent
from SpiffWorkflow.bpmn.parser.ProcessParser import ProcessParser
from SpiffWorkflow.bpmn.parser.util import *
from SpiffWorkflow.bpmn.parser.task_parsers import *
import xml.etree.ElementTree as ET

class BpmnParser(object):
    """
    The BpmnParser class is a pluggable base class that manages the parsing of a set of BPMN files.
    It is intended that this class will be overriden by an application that implements a BPMN engine.

    Extension points:
    OVERRIDE_PARSER_CLASSES provides a map from full BPMN tag name to a TaskParser and Task class.
    PROCESS_PARSER_CLASS provides a subclass of ProcessParser
    WORKFLOW_CLASS provides a subclass of BpmnWorkflow

    """

    PARSER_CLASSES = {
        full_tag('startEvent')          : (StartEventParser, StartEvent),
        full_tag('endEvent')            : (EndEventParser, EndEvent),
        full_tag('userTask')            : (UserTaskParser, UserTask),
        full_tag('task')                : (NoneTaskParser, NoneTask),
        full_tag('manualTask')          : (ManualTaskParser, ManualTask),
        full_tag('exclusiveGateway')    : (ExclusiveGatewayParser, ExclusiveGateway),
        full_tag('parallelGateway')     : (ParallelGatewayParser, ParallelGateway),
        full_tag('inclusiveGateway')     : (InclusiveGatewayParser, InclusiveGateway),
        full_tag('callActivity')        : (CallActivityParser, CallActivity),
        full_tag('scriptTask')                  : (ScriptTaskParser, ScriptTask),
        full_tag('intermediateCatchEvent')      : (IntermediateCatchEventParser, IntermediateCatchEvent),
        full_tag('boundaryEvent')               : (BoundaryEventParser, BoundaryEvent),
        }

    OVERRIDE_PARSER_CLASSES = {}

    PROCESS_PARSER_CLASS = ProcessParser
    WORKFLOW_CLASS = BpmnWorkflow

    def __init__(self):
        """
        Constructor.
        """
        self.process_parsers = {}
        self.process_parsers_by_name = {}

    def _get_parser_class(self, tag):
        if tag in self.OVERRIDE_PARSER_CLASSES:
            return self.OVERRIDE_PARSER_CLASSES[tag]
        elif tag in self.PARSER_CLASSES:
            return self.PARSER_CLASSES[tag]
        return None, None

    def get_process_parser(self, process_id_or_name):
        """
        Returns the ProcessParser for the given process ID or name. It matches by name first.
        """
        if process_id_or_name in self.process_parsers_by_name:
            return self.process_parsers_by_name[process_id_or_name]
        else:
            return self.process_parsers[process_id_or_name]

    def add_bpmn_file(self, filename):
        """
        Add the given BPMN filename to the parser's set.
        """
        self.add_bpmn_files([filename])

    def add_bpmn_files_by_glob(self, g):
        """
        Add all filenames matching the provided pattern (e.g. *.bpmn) to the parser's set.
        """
        self.add_bpmn_files(glob.glob(g))

    def add_bpmn_files(self, filenames):
        """
        Add all filenames in the given list to the parser's set.
        """
        for filename in filenames:
            f = open(filename, 'r')
            try:
                self.add_bpmn_xml(ET.parse(f), filename=filename)
            finally:
                f.close()

    def add_bpmn_xml(self, bpmn, svg=None, filename=None):
        """
        Add the given lxml representation of the BPMN file to the parser's set.

        :param svg: Optionally, provide the text data for the SVG of the BPMN file
        :param filename: Optionally, provide the source filename.
        """
        xpath = xpath_eval(bpmn)

        processes = xpath('.//bpmn:process')
        for process in processes:
            process_parser = self.PROCESS_PARSER_CLASS(self, process, svg, filename=filename, doc_xpath=xpath)
            if process_parser.get_id() in self.process_parsers:
                raise ValidationException('Duplicate process ID', node=process, filename=filename)
            if process_parser.get_name() in self.process_parsers_by_name:
                raise ValidationException('Duplicate process name', node=process, filename=filename)
            self.process_parsers[process_parser.get_id()] = process_parser
            self.process_parsers_by_name[process_parser.get_name()] = process_parser

    def _parse_condition(self, outgoing_task, outgoing_task_node, sequence_flow_node, task_parser=None):
        xpath = xpath_eval(sequence_flow_node)
        condition_expression_node = conditionExpression = first(xpath('.//bpmn:conditionExpression'))
        if conditionExpression is not None:
            conditionExpression = conditionExpression.text
        return self.parse_condition(conditionExpression, outgoing_task, outgoing_task_node, sequence_flow_node, condition_expression_node, task_parser)

    def parse_condition(self, condition_expression, outgoing_task, outgoing_task_node, sequence_flow_node, condition_expression_node, task_parser):
        """
        Pre-parse the given condition expression, and return the parsed version. The returned version will be passed to the Script Engine
        for evaluation.
        """
        return condition_expression

    def _parse_documentation(self, node, task_parser=None, xpath=None):
        xpath = xpath or xpath_eval(node)
        documentation_node = first(xpath('.//bpmn:documentation'))
        return self.parse_documentation(documentation_node, node, xpath, task_parser=task_parser)

    def parse_documentation(self, documentation_node, node, node_xpath, task_parser=None):
        """
        Pre-parse the documentation node for the given node and return the text.
        """
        return None if documentation_node is None else documentation_node.text

    def get_spec(self, process_id_or_name):
        """
        Parses the required subset of the BPMN files, in order to provide an instance of BpmnProcessSpec (i.e. WorkflowSpec)
        for the given process ID or name. The Name is matched first.
        """
        return self.get_process_parser(process_id_or_name).get_spec()




########NEW FILE########
__FILENAME__ = ProcessParser
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException
from SpiffWorkflow.bpmn.specs.BpmnProcessSpec import BpmnProcessSpec
from SpiffWorkflow.bpmn.parser.util import *

class ProcessParser(object):
    """
    Parses a single BPMN process, including all of the tasks within that process.
    """

    def __init__(self, p, node, svg=None, filename=None, doc_xpath=None):
        """
        Constructor.

        :param p: the owning BpmnParser instance
        :param node: the XML node for the process
        :param svg: the SVG representation of this process as a string (optional)
        :param filename: the source BPMN filename (optional)

        """
        self.parser = p
        self.node = node
        self.doc_xpath = doc_xpath
        self.xpath = xpath_eval(node)
        self.spec = BpmnProcessSpec(name=self.get_id(), description=self.get_name(), svg=svg, filename=filename)
        self.parsing_started = False
        self.is_parsed = False
        self.parsed_nodes = {}
        self.svg = svg
        self.filename = filename
        self.id_to_lane_lookup = None
        self._init_lane_lookup()

    def get_id(self):
        """
        Returns the process ID
        """
        return self.node.get('id')

    def get_name(self):
        """
        Returns the process name (or ID, if no name is included in the file)
        """
        return self.node.get('name', default=self.get_id())

    def parse_node(self,node):
        """
        Parses the specified child task node, and returns the task spec.
        This can be called by a TaskParser instance, that is owned by this ProcessParser.
        """

        if node.get('id') in self.parsed_nodes:
            return self.parsed_nodes[node.get('id')]

        (node_parser, spec_class) = self.parser._get_parser_class(node.tag)
        if not node_parser or not spec_class:
            raise ValidationException("There is no support implemented for this task type.", node=node, filename=self.filename)
        np = node_parser(self, spec_class, node)
        task_spec = np.parse_node()

        return task_spec

    def get_lane(self, id):
        """
        Return the name of the lane that contains the specified task
        """
        return self.id_to_lane_lookup.get(id, None)

    def _init_lane_lookup(self):
        self.id_to_lane_lookup = {}
        for lane in self.xpath('.//bpmn:lane'):
            name = lane.get('name')
            if name:
                for ref in xpath_eval(lane)('bpmn:flowNodeRef'):
                    id = ref.text
                    if id:
                        self.id_to_lane_lookup[id] = name

    def _parse(self):
        start_node_list = self.xpath('.//bpmn:startEvent')
        if not start_node_list:
            raise ValidationException("No start event found", node=self.node, filename=self.filename)
        elif len(start_node_list) != 1:
            raise ValidationException("Only one Start Event is supported in each process", node=self.node, filename=self.filename)
        self.parsing_started = True
        self.parse_node(start_node_list[0])
        self.is_parsed = True

    def get_spec(self):
        """
        Parse this process (if it has not already been parsed), and return the workflow spec.
        """
        if self.is_parsed:
            return self.spec
        if self.parsing_started:
            raise NotImplementedError('Recursive call Activities are not supported.')
        self._parse()
        return self.get_spec()

########NEW FILE########
__FILENAME__ = TaskParser
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import logging
import sys
import traceback
from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException
from SpiffWorkflow.bpmn.specs.BoundaryEvent import _BoundaryEventParent
from SpiffWorkflow.bpmn.parser.util import *

LOG = logging.getLogger(__name__)

class TaskParser(object):
    """
    This class parses a single BPMN task node, and returns the Task Spec for that node.

    It also results in the recursive parsing of connected tasks, connecting all
    outgoing transitions, once the child tasks have all been parsed.
    """

    def __init__(self, process_parser, spec_class, node):
        """
        Constructor.

        :param process_parser: the owning process parser instance
        :param spec_class: the type of spec that should be created. This allows a subclass of BpmnParser to
        provide a specialised spec class, without extending the TaskParser.
        :param node: the XML node for this task
        """
        self.parser = process_parser.parser
        self.process_parser = process_parser
        self.spec_class = spec_class
        self.process_xpath = self.process_parser.xpath
        self.spec = self.process_parser.spec
        self.node = node
        self.xpath = xpath_eval(node)

    def parse_node(self):
        """
        Parse this node, and all children, returning the connected task spec.
        """

        try:
            self.task = self.create_task()

            self.task.documentation = self.parser._parse_documentation(self.node, xpath=self.xpath, task_parser=self)

            boundary_event_nodes = self.process_xpath('.//bpmn:boundaryEvent[@attachedToRef="%s"]' % self.get_id())
            if boundary_event_nodes:
                parent_task = _BoundaryEventParent(self.spec, '%s.BoundaryEventParent' % self.get_id(), self.task, lane=self.task.lane)
                self.process_parser.parsed_nodes[self.node.get('id')] = parent_task

                parent_task.connect_outgoing(self.task, '%s.FromBoundaryEventParent' % self.get_id(), None, None)
                for boundary_event in boundary_event_nodes:
                    b = self.process_parser.parse_node(boundary_event)
                    parent_task.connect_outgoing(b, '%s.FromBoundaryEventParent' % boundary_event.get('id'), None, None)
            else:
                self.process_parser.parsed_nodes[self.node.get('id')] = self.task


            children = []
            outgoing = self.process_xpath('.//bpmn:sequenceFlow[@sourceRef="%s"]' % self.get_id())
            if len(outgoing) > 1 and not self.handles_multiple_outgoing():
                raise ValidationException('Multiple outgoing flows are not supported for tasks of type', node=self.node, filename=self.process_parser.filename)
            for sequence_flow in outgoing:
                target_ref = sequence_flow.get('targetRef')
                target_node = one(self.process_xpath('.//*[@id="%s"]' % target_ref))
                c = self.process_parser.parse_node(target_node)
                children.append((c, target_node, sequence_flow))

            if children:
                default_outgoing = self.node.get('default')
                if not default_outgoing:
                    (c, target_node, sequence_flow) = children[0]
                    default_outgoing = sequence_flow.get('id')

                for (c, target_node, sequence_flow) in children:
                    self.connect_outgoing(c, target_node, sequence_flow, sequence_flow.get('id') == default_outgoing)

            return parent_task if boundary_event_nodes else self.task
        except ValidationException as vx:
            raise
        except Exception as ex:
            exc_info = sys.exc_info()
            tb =  "".join(traceback.format_exception(exc_info[0], exc_info[1], exc_info[2]))
            LOG.error("%r\n%s", ex, tb)
            raise ValidationException("%r"%(ex), node=self.node, filename=self.process_parser.filename)

    def get_lane(self):
        """
        Return the name of the lane that contains this task
        """
        return self.process_parser.get_lane(self.get_id())


    def get_task_spec_name(self, target_ref=None):
        """
        Returns a unique task spec name for this task (or the targeted one)
        """
        return target_ref or self.get_id()

    def get_id(self):
        """
        Return the node ID
        """
        return self.node.get('id')

    def create_task(self):
        """
        Create an instance of the task appropriately. A subclass can override this method to get extra information from the node.
        """
        return self.spec_class(self.spec, self.get_task_spec_name(), lane=self.get_lane(), description=self.node.get('name', None))

    def connect_outgoing(self, outgoing_task, outgoing_task_node, sequence_flow_node, is_default):
        """
        Connects this task to the indicating outgoing task, with the details in the sequence flow.
        A subclass can override this method to get extra information from the node.
        """
        self.task.connect_outgoing(outgoing_task, sequence_flow_node.get('id'), sequence_flow_node.get('name', None), self.parser._parse_documentation(sequence_flow_node, task_parser=self))

    def handles_multiple_outgoing(self):
        """
        A subclass should override this method if the task supports multiple outgoing sequence flows.
        """
        return False

########NEW FILE########
__FILENAME__ = task_parsers
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException
from SpiffWorkflow.bpmn.parser.TaskParser import TaskParser
from SpiffWorkflow.bpmn.parser.util import *
from SpiffWorkflow.bpmn.specs.event_definitions import TimerEventDefinition, MessageEventDefinition
import xml.etree.ElementTree as ET

class StartEventParser(TaskParser):
    """
    Parses a Start Event, and connects it to the internal spec.start task.
    """

    def create_task(self):
        t = super(StartEventParser, self).create_task()
        self.spec.start.connect(t)
        return t

    def handles_multiple_outgoing(self):
        return True

class EndEventParser(TaskParser):
    """
    Parses and End Event. This also checks whether it should be a terminating end event.
    """

    def create_task(self):

        terminateEventDefinition = self.xpath('.//bpmn:terminateEventDefinition')
        task = self.spec_class(self.spec, self.get_task_spec_name(), is_terminate_event=terminateEventDefinition, description=self.node.get('name', None))
        task.connect_outgoing(self.spec.end, '%s.ToEndJoin'%self.node.get('id'), None, None)
        return task

class UserTaskParser(TaskParser):
    """
    Base class for parsing User Tasks
    """
    pass

class ManualTaskParser(UserTaskParser):
    """
    Base class for parsing Manual Tasks. Currently assumes that Manual Tasks should be treated the same way as User Tasks.
    """
    pass

class NoneTaskParser(UserTaskParser):
    """
    Base class for parsing unspecified Tasks. Currently assumes that such Tasks should be treated the same way as User Tasks.
    """
    pass

class ExclusiveGatewayParser(TaskParser):
    """
    Parses an Exclusive Gateway, setting up the outgoing conditions appropriately.
    """

    def connect_outgoing(self, outgoing_task, outgoing_task_node, sequence_flow_node, is_default):
        if is_default:
            super(ExclusiveGatewayParser, self).connect_outgoing(outgoing_task, outgoing_task_node, sequence_flow_node, is_default)
        else:
            cond = self.parser._parse_condition(outgoing_task, outgoing_task_node, sequence_flow_node, task_parser=self)
            if cond is None:
                raise ValidationException('Non-default exclusive outgoing sequence flow without condition', sequence_flow_node, self.process_parser.filename)
            self.task.connect_outgoing_if(cond, outgoing_task, sequence_flow_node.get('id'), sequence_flow_node.get('name', None), self.parser._parse_documentation(sequence_flow_node, task_parser=self))

    def handles_multiple_outgoing(self):
        return True

class ParallelGatewayParser(TaskParser):
    """
    Parses a Parallel Gateway.
    """

    def handles_multiple_outgoing(self):
        return True

class InclusiveGatewayParser(TaskParser):
    """
    Parses an Inclusive Gateway.
    """

    def handles_multiple_outgoing(self):
        """
        At the moment I haven't implemented support for diverging inclusive gateways
        """
        return False

class CallActivityParser(TaskParser):
    """
    Parses a CallActivity node. This also supports the not-quite-correct BPMN that Signavio produces (which does not have a calledElement attribute).
    """

    def create_task(self):
        wf_spec = self.get_subprocess_parser().get_spec()
        return self.spec_class(self.spec, self.get_task_spec_name(), wf_spec=wf_spec, wf_class=self.parser.WORKFLOW_CLASS, description=self.node.get('name', None))

    def get_subprocess_parser(self):
        calledElement = self.node.get('calledElement', None)
        if not calledElement:
            raise ValidationException('No "calledElement" attribute for Call Activity.', node=self.node, filename=self.process_parser.filename)
        return self.parser.get_process_parser(calledElement)

class ScriptTaskParser(TaskParser):
    """
    Parses a script task
    """

    def create_task(self):
        script = self.get_script()
        return self.spec_class(self.spec, self.get_task_spec_name(), script, description=self.node.get('name', None))

    def get_script(self):
        """
        Gets the script content from the node. A subclass can override this method, if the script needs
        to be pre-parsed. The result of this call will be passed to the Script Engine for execution.
        """
        return one(self.xpath('.//bpmn:script')).text

class IntermediateCatchEventParser(TaskParser):
    """
    Parses an Intermediate Catch Event. This currently onlt supports Message and Timer event definitions.
    """

    def create_task(self):
        event_definition = self.get_event_definition()
        return self.spec_class(self.spec, self.get_task_spec_name(), event_definition, description=self.node.get('name', None))

    def get_event_definition(self):
        """
        Parse the event definition node, and return an instance of Event
        """
        messageEventDefinition = first(self.xpath('.//bpmn:messageEventDefinition'))
        if messageEventDefinition is not None:
            return self.get_message_event_definition(messageEventDefinition)

        timerEventDefinition = first(self.xpath('.//bpmn:timerEventDefinition'))
        if timerEventDefinition is not None:
            return self.get_timer_event_definition(timerEventDefinition)

        raise NotImplementedError('Unsupported Intermediate Catch Event: %r', ET.tostring(self.node) )

    def get_message_event_definition(self, messageEventDefinition):
        """
        Parse the messageEventDefinition node and return an instance of MessageEventDefinition
        """
        messageRef = first(self.xpath('.//bpmn:messageRef'))
        message = messageRef.get('name') if messageRef is not None else self.node.get('name')
        return MessageEventDefinition(message)

    def get_timer_event_definition(self, timerEventDefinition):
        """
        Parse the timerEventDefinition node and return an instance of TimerEventDefinition

        This currently only supports the timeDate node for specifying an expiry time for the timer.
        """
        timeDate = first(self.xpath('.//bpmn:timeDate'))
        return TimerEventDefinition(self.node.get('name', timeDate.text), self.parser.parse_condition(timeDate.text, None, None, None, None, self))


class BoundaryEventParser(IntermediateCatchEventParser):
    """
    Parse a Catching Boundary Event. This extends the IntermediateCatchEventParser in order to parse the event definition.
    """

    def create_task(self):
        event_definition = self.get_event_definition()
        cancel_activity = self.node.get('cancelActivity', default='false').lower() == 'true'
        return self.spec_class(self.spec, self.get_task_spec_name(), cancel_activity=cancel_activity, event_definition=event_definition, description=self.node.get('name', None))

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


BPMN_MODEL_NS='http://www.omg.org/spec/BPMN/20100524/MODEL'

def one(nodes,or_none=False):
    """
    Assert that there is exactly one node in the give list, and return it.
    """
    if not nodes and or_none:
        return None
    assert len(nodes) == 1, 'Expected 1 result. Received %d results.' % (len(nodes))
    return nodes[0]

def first(nodes):
    """
    Return the first node in the given list, or None, if the list is empty.
    """
    if len(nodes) >= 1:
        return nodes[0]
    else:
        return None

def xpath_eval(node, extra_ns=None):
    """
    Returns an XPathEvaluator, with namespace prefixes 'bpmn' for http://www.omg.org/spec/BPMN/20100524/MODEL,
    and additional specified ones
    """
    namespaces = {'bpmn':BPMN_MODEL_NS}
    if extra_ns:
        namespaces.update(extra_ns)
    return lambda path: node.findall(path, namespaces)

def full_tag(tag):
    """
    Return the full tag name including namespace for the given BPMN tag.
    In other words, the name with namespace http://www.omg.org/spec/BPMN/20100524/MODEL
    """
    return '{%s}%s' % (BPMN_MODEL_NS, tag)
########NEW FILE########
__FILENAME__ = ValidationException
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.bpmn.parser.util import BPMN_MODEL_NS

class ValidationException(Exception):
    """
    A ValidationException should be thrown with enough information for the user
    to diagnose the problem and sort it out.

    If available, please provide the offending XML node and filename.
    """

    def __init__(self, msg, node = None, filename = None, *args, **kwargs):
        if node is not None:
            self.tag = self._shorten_tag(node.tag)
            self.id = node.get('id', '<Unknown>')
            self.name = node.get('name', '<Unknown>')
            self.sourceline = getattr(node, 'sourceline', '<Unknown>')
        else:
            self.tag = '<Unknown>'
            self.id = '<Unknown>'
            self.name = '<Unknown>'
            self.sourceline = '<Unknown>'
        self.filename = filename or '<Unknown File>'
        message = '%s\nSource Details: %s (id:%s), name \'%s\', line %s in %s' % (
            msg, self.tag, self.id, self.name, self.sourceline, self.filename)

        super(ValidationException, self).__init__(message, *args, **kwargs)

    @classmethod
    def _shorten_tag(cls, tag):
        prefix = '{%s}' % BPMN_MODEL_NS
        if tag.startswith(prefix):
            return 'bpmn:' + tag[len(prefix):]
        return tag


########NEW FILE########
__FILENAME__ = BoundaryEvent
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.specs.BpmnSpecMixin import BpmnSpecMixin
from SpiffWorkflow.bpmn.specs.IntermediateCatchEvent import IntermediateCatchEvent

class _BoundaryEventParent(BpmnSpecMixin):

    def __init__(self, parent, name, main_child_task_spec, lane=None, **kwargs):
        super(_BoundaryEventParent, self).__init__(parent, name, lane=lane, **kwargs)
        self.main_child_task_spec = main_child_task_spec

    def _child_complete_hook(self, child_task):
        if child_task.task_spec == self.main_child_task_spec or self._should_cancel(child_task.task_spec):
            for sibling in child_task.parent.children:
                if sibling != child_task:
                    if sibling.task_spec == self.main_child_task_spec or (isinstance(sibling.task_spec, BoundaryEvent) and not sibling._is_finished()):
                        sibling.cancel()
            for t in child_task.workflow._get_waiting_tasks():
                t.task_spec._update_state(t)

    def _predict_hook(self, my_task):
        # We default to MAYBE
        # for all it's outputs except the main child, which is
        # FUTURE, if my task is definite, otherwise, my own state.
        my_task._sync_children(self.outputs, state=Task.MAYBE)

        if my_task._is_definite():
            state = Task.FUTURE
        else:
            state = my_task.state

        for child in my_task.children:
            if child.task_spec == self.main_child_task_spec:
                child._set_state(state)

    def _should_cancel(self, task_spec):
        return issubclass(task_spec.__class__, BoundaryEvent) and task_spec._cancel_activity

class BoundaryEvent(IntermediateCatchEvent):
    """
    Task Spec for a bpmn:boundaryEvent node.
    """

    def __init__(self, parent, name, cancel_activity=None, event_definition=None, **kwargs):
        """
        Constructor.

        :param cancel_activity: True if this is a Cancelling boundary event.
        """
        super(BoundaryEvent, self).__init__(parent, name, event_definition=event_definition, **kwargs)
        self._cancel_activity = cancel_activity

########NEW FILE########
__FILENAME__ = BpmnProcessSpec
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import logging
from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.specs.UnstructuredJoin import UnstructuredJoin
from SpiffWorkflow.specs.Simple import Simple
from SpiffWorkflow.specs.WorkflowSpec import WorkflowSpec
import xml.etree.ElementTree as ET

class _EndJoin(UnstructuredJoin):

    def _try_fire_unstructured(self, my_task, force=False):
        # Look at the tree to find all ready and waiting tasks (excluding ourself).
        # The EndJoin waits for everyone!
        waiting_tasks = []
        for task in my_task.workflow.get_tasks(Task.READY | Task.WAITING):
            if task.thread_id != my_task.thread_id:
                continue
            if task.task_spec == my_task.task_spec:
                continue

            is_mine = False
            w = task.workflow
            if w == my_task.workflow:
                is_mine = True
            while w and w.outer_workflow != w:
                w = w.outer_workflow
                if w == my_task.workflow:
                    is_mine = True
            if is_mine:
                waiting_tasks.append(task)

        if len(waiting_tasks)==0:
            logging.debug('Endjoin Task ready: %s (ready/waiting tasks: %s)', my_task, list(my_task.workflow.get_tasks(Task.READY | Task.WAITING)))

        return force or len(waiting_tasks) == 0, waiting_tasks

    def _on_complete_hook(self, my_task):
        super(_EndJoin, self)._on_complete_hook(my_task)
        my_task.workflow.data.update(my_task.data)


class BpmnProcessSpec(WorkflowSpec):
    """
    This class represents the specification of a BPMN process workflow. This specialises the
    standard Spiff WorkflowSpec class with a few extra methods and attributes.
    """

    def __init__(self, name=None, description=None, filename=None, svg=None):
        """
        Constructor.

        :param svg: This provides the SVG representation of the workflow as an LXML node. (optional)
        """
        super(BpmnProcessSpec, self).__init__(name=name, filename=filename)
        self.end = _EndJoin(self, '%s.EndJoin' % (self.name))
        end = Simple(self, 'End')
        end.follow(self.end)
        self.svg = svg
        self.description = description

    def get_all_lanes(self):
        """
        Returns a set of the distinct lane names used in the process (including called activities)
        """

        done = set()
        lanes = set()

        def recursive_find(task_spec):
            if task_spec in done:
                return

            done.add(task_spec)

            if hasattr(task_spec, 'lane') and task_spec.lane:
                lanes.add(task_spec.lane)

            if hasattr(task_spec, 'spec'):
                recursive_find(task_spec.spec.start)

            for t in task_spec.outputs:
                recursive_find(t)

        recursive_find(self.start)

        return lanes

    def get_specs_depth_first(self):
        """
        Get the specs for all processes (including called ones), in depth first order.
        """

        done = set()
        specs = [self]

        def recursive_find(task_spec):
            if task_spec in done:
                return

            done.add(task_spec)

            if hasattr(task_spec, 'spec'):
                specs.append(task_spec.spec)
                recursive_find(task_spec.spec.start)

            for t in task_spec.outputs:
                recursive_find(t)

        recursive_find(self.start)

        return specs

    def to_html_string(self):
        """
        Returns an etree HTML node with a document describing the process. This is only supported
        if the editor provided an SVG representation.
        """
        html = ET.Element('html')
        head = ET.SubElement(html, 'head')
        title = ET.SubElement(head, 'title')
        title.text = self.description
        body = ET.SubElement(html, 'body')
        h1 = ET.SubElement(body, 'h1')
        h1.text = self.description
        span = ET.SubElement(body, 'span')
        span.text = '___CONTENT___'

        html_text = ET.tostring(html)

        svg_content = ''
        svg_done = set()
        for spec in self.get_specs_depth_first():
            if spec.svg and not spec.svg in svg_done:
                svg_content += '<p>' + spec.svg + "</p>"
                svg_done.add(spec.svg)
        return html_text.replace('___CONTENT___',svg_content)





########NEW FILE########
__FILENAME__ = BpmnSpecMixin
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.Task import Task
from SpiffWorkflow.operators import Operator
from SpiffWorkflow.specs.TaskSpec import TaskSpec

class _BpmnCondition(Operator):

    def __init__(self, *args):
        if len(args) > 1:
            raise TypeError("Too many arguments")
        super(_BpmnCondition, self).__init__(*args)

    def _matches(self, task):
        return task.workflow.script_engine.evaluate(task, self.args[0])

class SequenceFlow(object):
    """
    Keeps information relating to a sequence flow
    """

    def __init__(self, id, name, documentation, target_task_spec):
        """
        Constructor.
        """
        self.id = id
        self.name = name.strip() if name else name
        self.documentation = documentation
        self.target_task_spec = target_task_spec

class BpmnSpecMixin(TaskSpec):
    """
    All BPMN spec classes should mix this superclass in. It adds a number of methods that are
    BPMN specific to the TaskSpec.
    """

    def __init__(self, parent, name, lane=None, **kwargs):
        """
        Constructor.

        :param lane: Indicates the name of the lane that this task belongs to (optional).
        """
        super(BpmnSpecMixin, self).__init__(parent, name, **kwargs)
        self.outgoing_sequence_flows = {}
        self.outgoing_sequence_flows_by_id = {}
        self.lane = lane
        self.documentation = None

    def connect_outgoing(self, taskspec, sequence_flow_id, sequence_flow_name, documentation):
        """
        Connect this task spec to the indicated child.

        :param sequence_flow_id: The ID of the connecting sequenceFlow node.
        :param sequence_flow_name: The name of the connecting sequenceFlow node.
        """
        self.connect(taskspec)
        s = SequenceFlow(sequence_flow_id, sequence_flow_name, documentation, taskspec)
        self.outgoing_sequence_flows[taskspec.name] = s
        self.outgoing_sequence_flows_by_id[sequence_flow_id] = s

    def connect_outgoing_if(self, condition, taskspec, sequence_flow_id, sequence_flow_name, documentation):
        """
        Connect this task spec to the indicated child, if the condition evaluates to true.
        This should only be called if the task has a connect_if method (e.g. ExclusiveGateway).

        :param sequence_flow_id: The ID of the connecting sequenceFlow node.
        :param sequence_flow_name: The name of the connecting sequenceFlow node.
        """
        self.connect_if(_BpmnCondition(condition), taskspec)
        s = SequenceFlow(sequence_flow_id, sequence_flow_name, documentation, taskspec)
        self.outgoing_sequence_flows[taskspec.name] = s
        self.outgoing_sequence_flows_by_id[sequence_flow_id] = s

    def get_outgoing_sequence_flow_by_spec(self, task_spec):
        """
        Returns the outgoing SequenceFlow targeting the specified task_spec.
        """
        return self.outgoing_sequence_flows[task_spec.name]

    def get_outgoing_sequence_flow_by_id(self, id):
        """
        Returns the outgoing SequenceFlow with the specified ID.
        """
        return self.outgoing_sequence_flows_by_id[id]

    def has_outgoing_sequence_flow(self, id):
        """
        Returns true if the SequenceFlow with the specified ID is leaving this task.
        """
        return id in self.outgoing_sequence_flows_by_id

    def get_outgoing_sequence_names(self):
        """
        Returns a list of the names of outgoing sequences. Some may be None.
        """
        return sorted([s.name for s in self.outgoing_sequence_flows_by_id.values()])

    def get_outgoing_sequences(self):
        """
        Returns a list of the names of outgoing sequences. Some may be None.
        """
        return iter(self.outgoing_sequence_flows_by_id.values())

    def accept_message(self, my_task, message):
        """
        A subclass should override this method if they want to be notified of the receipt of a message
        when in a WAITING state.

        Returns True if the task did process the message.
        """
        return False

    ######### Hooks for Custom BPMN tasks ##########

    def entering_waiting_state(self, my_task):
        """
        Called when a task enters the WAITING state.

        A subclass may override this method to do work when this happens.
        """
        pass

    def entering_ready_state(self, my_task):
        """
        Called when a task enters the READY state.

        A subclass may override this method to do work when this happens.
        """
        pass

    def entering_complete_state(self, my_task):
        """
        Called when a task enters the COMPLETE state.

        A subclass may override this method to do work when this happens.
        """
        pass

    def entering_cancelled_state(self, my_task):
        """
        Called when a task enters the CANCELLED state.

        A subclass may override this method to do work when this happens.
        """
        pass

    ################################################

    def _on_complete_hook(self, my_task):
        super(BpmnSpecMixin, self)._on_complete_hook(my_task)
        if isinstance(my_task.parent.task_spec, BpmnSpecMixin):
            my_task.parent.task_spec._child_complete_hook(my_task)
        if not my_task.workflow._is_busy_with_restore():
            self.entering_complete_state(my_task)

    def _child_complete_hook(self, child_task):
        pass

    def _on_cancel(self, my_task):
        super(BpmnSpecMixin, self)._on_cancel(my_task)
        my_task.workflow._task_cancelled_notify(my_task)
        if not my_task.workflow._is_busy_with_restore():
            self.entering_cancelled_state(my_task)

    def _update_state_hook(self, my_task):
        prev_state = my_task.state
        super(BpmnSpecMixin, self)._update_state_hook(my_task)
        if prev_state != Task.WAITING and my_task.state == Task.WAITING and not my_task.workflow._is_busy_with_restore():
            self.entering_waiting_state(my_task)

    def _on_ready_before_hook(self, my_task):
        super(BpmnSpecMixin, self)._on_ready_before_hook(my_task)
        if not my_task.workflow._is_busy_with_restore():
            self.entering_ready_state(my_task)



########NEW FILE########
__FILENAME__ = CallActivity
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.bpmn.specs.BpmnSpecMixin import BpmnSpecMixin
from SpiffWorkflow.specs.SubWorkflow import SubWorkflow
from SpiffWorkflow.specs.TaskSpec import TaskSpec

class CallActivity(SubWorkflow, BpmnSpecMixin):
    """
    Task Spec for a bpmn:callActivity node.
    """

    def __init__(self, parent, name, wf_spec=None, wf_class=None, **kwargs):
        """
        Constructor.

        :param wf_spec: the BpmnProcessSpec for the sub process.
        :param wf_class: the BpmnWorkflow class to instantiate
        """
        super(CallActivity, self).__init__(parent, name, None, **kwargs)
        self.spec = wf_spec
        self.wf_class = wf_class

    def test(self):
        TaskSpec.test(self)

    def _create_subworkflow(self, my_task):
        return self.get_workflow_class()(self.spec, name=self.name,
            read_only = my_task.workflow.read_only,
            script_engine=my_task.workflow.outer_workflow.script_engine,
            parent = my_task.workflow.outer_workflow)

    def get_workflow_class(self):
        """
        Returns the workflow class to instantiate for the sub workflow
        """
        return self.wf_class

    def _on_subworkflow_completed(self, subworkflow, my_task):
        super(CallActivity,self)._on_subworkflow_completed(subworkflow, my_task)
        if isinstance(my_task.parent.task_spec, BpmnSpecMixin):
            my_task.parent.task_spec._child_complete_hook(my_task)

########NEW FILE########
__FILENAME__ = EndEvent
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.bpmn.specs.BpmnSpecMixin import BpmnSpecMixin
from SpiffWorkflow.Task import Task

class EndEvent(BpmnSpecMixin):
    """
    Task Spec for a bpmn:endEvent node.

    From the specification of BPMN (http://www.omg.org/spec/BPMN/2.0/PDF - document number:formal/2011-01-03):
    For a "terminate" End Event, the Process is abnormally terminated - no other ongoing Process instances are
    affected.

    For all other End Events, the behavior associated with the Event type is performed, e.g., the associated Message is
    sent for a Message End Event, the associated signal is sent for a Signal End Event, and so on. The Process
    instance is then completed, if and only if the following two conditions hold:
     * All start nodes of the Process have been visited. More precisely, all Start Events have been triggered, and for all
    starting Event-Based Gateways, one of the associated Events has been triggered.
     * There is no token remaining within the Process instance.
    """

    def __init__(self, parent, name, is_terminate_event=False, **kwargs):
        """
        Constructor.

        :param is_terminate_event: True if this is a terminating end event
        """
        super(EndEvent, self).__init__(parent, name, **kwargs)
        self.is_terminate_event = is_terminate_event

    def _on_complete_hook(self, my_task):
        if self.is_terminate_event:
            #Cancel other branches in this workflow:
            for active_task in my_task.workflow.get_tasks(Task.READY | Task.WAITING):
                if active_task.task_spec == my_task.workflow.spec.end:
                    continue
                elif active_task.workflow == my_task.workflow:
                    active_task.cancel()
                else:
                    active_task.workflow.cancel()
                    for start_sibling in active_task.workflow.task_tree.children[0].parent.children:
                        if not start_sibling._is_finished():
                            start_sibling.cancel()

            my_task.workflow.refresh_waiting_tasks()

        super(EndEvent, self)._on_complete_hook(my_task)
########NEW FILE########
__FILENAME__ = event_definitions
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import datetime

class CatchingEventDefinition(object):
    """
    The CatchingEventDefinition class is used by Catching Intermediate and Boundary Event tasks to know whether
    to proceed.
    """

    def has_fired(self, my_task):
        """
        This should return True if the event has occurred (i.e. the task may move from WAITING
        to READY). This will be called multiple times.
        """
        return my_task._get_internal_data('event_fired', False)

    def _accept_message(self, my_task, message):
        return False

    def _fire(self, my_task):
        my_task._set_internal_data(event_fired=True)

class ThrowingEventDefinition(object):
    """
    This class is for future functionality. It will define the methods needed on an event definition
    that can be Thrown.
    """

class MessageEventDefinition(CatchingEventDefinition, ThrowingEventDefinition):
    """
    The MessageEventDefinition is the implementation of event definition used for Message Events.
    """

    def __init__(self, message):
        """
        Constructor.

        :param message: The message to wait for.
        """
        self.message = message

    def has_fired(self, my_task):
        """
        Returns true if the message was received while the task was in a WAITING state.
        """
        return my_task._get_internal_data('event_fired', False)

    def _accept_message(self, my_task, message):
        if message != self.message:
            return False
        self._fire(my_task)
        return True


class TimerEventDefinition(CatchingEventDefinition):
    """
    The TimerEventDefinition is the implementation of event definition used for Catching Timer Events
    (Timer events aren't thrown).
    """

    def __init__(self, label, dateTime):
        """
        Constructor.

        :param label: The label of the event. Used for the description.
        :param dateTime: The dateTime expression for the expiry time. This is passed to the Script Engine and
        must evaluate to a datetime.datetime instance.
        """
        self.label = label
        self.dateTime = dateTime

    def has_fired(self, my_task):
        """
        The Timer is considered to have fired if the evaluated dateTime expression is before datetime.datetime.now()
        """
        dt = my_task.workflow.script_engine.evaluate(my_task, self.dateTime)
        if dt is None:
            return False
        if dt.tzinfo:
            tz = dt.tzinfo
            now =  tz.fromutc(datetime.datetime.utcnow().replace(tzinfo=tz))
        else:
            now = datetime.datetime.now()
        return now > dt

########NEW FILE########
__FILENAME__ = ExclusiveGateway
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from SpiffWorkflow.exceptions import WorkflowException

from SpiffWorkflow.bpmn.specs.BpmnSpecMixin import BpmnSpecMixin
from SpiffWorkflow.specs.TaskSpec import TaskSpec
from SpiffWorkflow.specs.ExclusiveChoice import ExclusiveChoice

class ExclusiveGateway(ExclusiveChoice, BpmnSpecMixin):
    """
    Task Spec for a bpmn:exclusiveGateway node.
    """
    def test(self):
        """
        Checks whether all required attributes are set. Throws an exception
        if an error was detected.
        """
        #This has been overidden to allow a single default flow out (without a condition) - useful for
        #the converging type
        TaskSpec.test(self)
#        if len(self.cond_task_specs) < 1:
#            raise WorkflowException(self, 'At least one output required.')
        for condition, name in self.cond_task_specs:
            if name is None:
                raise WorkflowException(self, 'Condition with no task spec.')
            task_spec = self._parent.get_task_spec_from_name(name)
            if task_spec is None:
                msg = 'Condition leads to non-existent task ' + repr(name)
                raise WorkflowException(self, msg)
            if condition is None:
                continue
        if self.default_task_spec is None:
            raise WorkflowException(self, 'A default output is required.')
########NEW FILE########
__FILENAME__ = InclusiveGateway
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from collections import deque

import logging
from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.specs.UnstructuredJoin import UnstructuredJoin

LOG = logging.getLogger(__name__)



class InclusiveGateway(UnstructuredJoin):
    """
    Task Spec for a bpmn:parallelGateway node.
    From the specification of BPMN (http://www.omg.org/spec/BPMN/2.0/PDF - document number:formal/2011-01-03):

    The Inclusive Gateway is activated if
     * At least one incoming Sequence Flow has at least one token and
     * For every directed path formed by sequence flow that
        * starts with a Sequence Flow f of the diagram that has a token,
        * ends with an incoming Sequence Flow of the inclusive gateway that has no token, and
        * does not visit the Inclusive Gateway.
     * There is also a directed path formed by Sequence Flow that
        * starts with f,
        * ends with an incoming Sequence Flow of the inclusive gateway that has a token, and
        * does not visit the Inclusive Gateway.

    Upon execution, a token is consumed from each incoming Sequence Flow that has a token. A token will be
    produced on some of the outgoing Sequence Flows.

    TODO: Not implemented: At the moment, we can't handle having more than one token at a single incoming sequence
    TODO: At the moment only converging Inclusive Gateways are supported.

    In order to determine the outgoing Sequence Flows that receive a token,
    all conditions on the outgoing Sequence Flows are evaluated. The evaluation
    does not have to respect a certain order.

    For every condition which evaluates to true, a token MUST be passed on
    the respective Sequence Flow.

    If and only if none of the conditions evaluates to true, the token is passed
    on the default Sequence Flow.

    In case all conditions evaluate to false and a default flow has not been
    specified, the Inclusive Gateway throws an exception.

    """

    def _try_fire_unstructured(self, my_task, force=False):

        # Look at the tree to find all ready and waiting tasks (excluding ones that are our completed inputs).
        tasks = []
        for task in my_task.workflow.get_tasks(Task.READY | Task.WAITING):
            if task.thread_id != my_task.thread_id:
                continue
            if task.workflow != my_task.workflow:
                continue
            if task.task_spec == my_task.task_spec:
                continue
            tasks.append(task)

        inputs_with_tokens, waiting_tasks = self._get_inputs_with_tokens(my_task)
        inputs_without_tokens = [i for i in self.inputs if i not in inputs_with_tokens]

        waiting_tasks = []
        for task in tasks:
            if self._has_directed_path_to(task, self, without_using_sequence_flow_from=inputs_with_tokens):
                if not self._has_directed_path_to(task, self, without_using_sequence_flow_from=inputs_without_tokens):
                    waiting_tasks.append(task)

        return force or len(waiting_tasks) == 0, waiting_tasks

    def _has_directed_path_to(self, task, task_spec, without_using_sequence_flow_from=None):
        q = deque()
        done = set()

        without_using_sequence_flow_from = set(without_using_sequence_flow_from or [])

        q.append(task.task_spec)
        while q:
            n = q.popleft()
            if n == task_spec:
                return True
            for child in n.outputs:
                if child not in done and not (n in without_using_sequence_flow_from and child==task_spec):
                    done.add(child)
                    q.append(child)
        return False

########NEW FILE########
__FILENAME__ = IntermediateCatchEvent
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.specs.BpmnSpecMixin import BpmnSpecMixin
from SpiffWorkflow.specs.Simple import Simple

class IntermediateCatchEvent(Simple, BpmnSpecMixin):
    """
    Task Spec for a bpmn:intermediateCatchEvent node.
    """

    def __init__(self, parent, name, event_definition=None, **kwargs):
        """
        Constructor.

        :param event_definition: the EventDefinition that we must wait for.
        """
        super(IntermediateCatchEvent, self).__init__(parent, name, **kwargs)
        self.event_definition = event_definition

    def _update_state_hook(self, my_task):
        target_state = getattr(my_task, '_bpmn_load_target_state', None)
        if target_state == Task.READY or (not my_task.workflow._is_busy_with_restore() and self.event_definition.has_fired(my_task)):
            super(IntermediateCatchEvent, self)._update_state_hook(my_task)
        else:
            if not my_task.parent._is_finished():
                return
            if not my_task.state == Task.WAITING:
                my_task._set_state(Task.WAITING)
                if not my_task.workflow._is_busy_with_restore():
                    self.entering_waiting_state(my_task)

    def _on_ready_hook(self, my_task):
        self._predict(my_task)

    def accept_message(self, my_task, message):
        if my_task.state == Task.WAITING and self.event_definition._accept_message(my_task, message):
            self._update_state(my_task)
            return True
        return False
########NEW FILE########
__FILENAME__ = ManualTask
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.bpmn.specs.UserTask import UserTask

class ManualTask(UserTask):
    """
    Task Spec for a bpmn:manualTask node.
    """
    pass
########NEW FILE########
__FILENAME__ = NoneTask
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.bpmn.specs.UserTask import UserTask

class NoneTask(UserTask):
    """
    Task Spec for a bpmn:task node. In the base framework, it is assumed that a task with an unspecified type
    is actually a user task
    """
    pass
########NEW FILE########
__FILENAME__ = ParallelGateway
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from collections import deque

import logging
from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.specs.UnstructuredJoin import UnstructuredJoin

LOG = logging.getLogger(__name__)

class ParallelGateway(UnstructuredJoin):
    """
    Task Spec for a bpmn:parallelGateway node.
    From the specification of BPMN (http://www.omg.org/spec/BPMN/2.0/PDF - document number:formal/2011-01-03):
        The Parallel Gateway is activated if there is at least one token on each incoming Sequence Flow.
        The Parallel Gateway consumes exactly one token from each incoming
        Sequence Flow and produces exactly one token at each outgoing Sequence Flow.

        TODO: Not implemented:
        If there are excess tokens at an incoming Sequence Flow, these tokens
        remain at this Sequence Flow after execution of the Gateway.

    Essentially, this means that we must wait until we have a completed parent task on each incoming sequence.

    """

    def _try_fire_unstructured(self, my_task, force=False):
        completed_inputs, waiting_tasks = self._get_inputs_with_tokens(my_task)

        # If the threshold was reached, get ready to fire.
        return force or len(completed_inputs) >= len(self.inputs), waiting_tasks

########NEW FILE########
__FILENAME__ = ScriptTask
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.bpmn.specs.BpmnSpecMixin import BpmnSpecMixin
from SpiffWorkflow.specs.Simple import Simple

class ScriptTask(Simple, BpmnSpecMixin):
    """
    Task Spec for a bpmn:scriptTask node.
    """

    def __init__(self, parent, name, script, **kwargs):
        """
        Constructor.

        :param script: the script that must be executed by the script engine.
        """
        super(ScriptTask, self).__init__(parent, name, **kwargs)
        self.script = script

    def _on_complete_hook(self, task):
        if task.workflow._is_busy_with_restore():
            return
        assert not task.workflow.read_only
        task.workflow.script_engine.execute(task, self.script)
        super(ScriptTask, self)._on_complete_hook(task)


########NEW FILE########
__FILENAME__ = StartEvent
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.bpmn.specs.BpmnSpecMixin import BpmnSpecMixin
from SpiffWorkflow.specs.Simple import Simple

class StartEvent(Simple, BpmnSpecMixin):
    """
    Task Spec for a bpmn:startEvent node.
    """
    def __init__(self, parent, name, **kwargs):
        super(StartEvent, self).__init__(parent, name, **kwargs)
########NEW FILE########
__FILENAME__ = UnstructuredJoin
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from collections import deque

import logging
from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.specs.BpmnSpecMixin import BpmnSpecMixin
from SpiffWorkflow.specs.Join import Join

LOG = logging.getLogger(__name__)

class UnstructuredJoin(Join, BpmnSpecMixin):
    """
    A helper subclass of Join that makes it work in a slightly friendlier way for the BPMN style threading
    """

    def _try_fire_unstructured(self, my_task, force=False):
        raise NotImplementedError("Please implement this in the subclass")

    def _get_inputs_with_tokens(self, my_task):
        # Look at the tree to find all places where this task is used.
        tasks = []
        for task in my_task.workflow.task_tree:
            if task.thread_id != my_task.thread_id:
                continue
            if task.workflow != my_task.workflow:
                continue
            if task.task_spec != self:
                continue
            if task._is_finished():
                continue
            tasks.append(task)

        # Look up which tasks have parent's completed.
        waiting_tasks = []
        completed_inputs = set()
        for task in tasks:
            if task.parent._has_state(Task.COMPLETED) and (task._has_state(Task.WAITING) or task == my_task):
                if task.parent.task_spec in completed_inputs:
                    raise NotImplementedError("Unsupported looping behaviour: two threads waiting on the same sequence flow.")
                completed_inputs.add(task.parent.task_spec)
            else:
                waiting_tasks.append(task.parent)

        return completed_inputs, waiting_tasks

    def _do_join(self, my_task):
        # Copied from Join parent class
        #  This has some minor changes

        # One Join spec may have multiple corresponding Task objects::
        #
        #     - Due to the MultiInstance pattern.
        #     - Due to the ThreadSplit pattern.
        #
        # When using the MultiInstance pattern, we want to join across
        # the resulting task instances. When using the ThreadSplit
        # pattern, we only join within the same thread. (Both patterns
        # may also be mixed.)
        #
        # We are looking for all task instances that must be joined.
        # We limit our search by starting at the split point.
        if self.split_task:
            split_task = my_task.workflow.get_task_spec_from_name(self.split_task)
            split_task = my_task._find_ancestor(split_task)
        else:
            split_task = my_task.workflow.task_tree

        # Identify all corresponding task instances within the thread.
        # Also remember which of those instances was most recently changed,
        # because we are making this one the instance that will
        # continue the thread of control. In other words, we will continue
        # to build the task tree underneath the most recently changed task.
        last_changed = None
        thread_tasks = []
        for task in split_task._find_any(self):
            # Ignore tasks from other threads.
            if task.thread_id != my_task.thread_id:
                continue
            # Ignore tasks from other subprocesses:
            if task.workflow != my_task.workflow:
                continue

            # Ignore my outgoing branches.
            if task._is_descendant_of(my_task):
                continue
            # Ignore completed tasks (this is for loop handling)
            if task._is_finished():
                continue

            #For an inclusive join, this can happen - it's a future join
            if not task.parent._is_finished():
                continue

            # We have found a matching instance.
            thread_tasks.append(task)

            # Check whether the state of the instance was recently
            # changed.
            changed = task.parent.last_state_change
            if last_changed is None\
            or changed > last_changed.parent.last_state_change:
                last_changed = task

        # Mark the identified task instances as COMPLETED. The exception
        # is the most recently changed task, for which we assume READY.
        # By setting the state to READY only, we allow for calling
        # L{Task.complete()}, which leads to the task tree being
        # (re)built underneath the node.
        for task in thread_tasks:
            if task == last_changed:
                self.entered_event.emit(my_task.workflow, my_task)
                task._ready()
            else:
                task.state = Task.COMPLETED
                task._drop_children()


    def _update_state_hook(self, my_task):

        if my_task._is_predicted():
            self._predict(my_task)
        if not my_task.parent._is_finished():
            return

        target_state = getattr(my_task, '_bpmn_load_target_state', None)
        if target_state == Task.WAITING:
            my_task._set_state(Task.WAITING)
            return

        logging.debug('UnstructuredJoin._update_state_hook: %s (%s) - Children: %s', self.name, self.description, len(my_task.children))
        super(UnstructuredJoin, self)._update_state_hook(my_task)
########NEW FILE########
__FILENAME__ = UserTask
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.bpmn.specs.BpmnSpecMixin import BpmnSpecMixin
from SpiffWorkflow.specs.Simple import Simple

class UserTask(Simple, BpmnSpecMixin):
    """
    Task Spec for a bpmn:userTask node.
    """
    def is_engine_task(self):
        return False

########NEW FILE########
__FILENAME__ = BpmnSerializer
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.util.compat import configparser
from io import BytesIO, TextIOWrapper
import xml.etree.ElementTree as ET
import zipfile
import os
from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnParser
from SpiffWorkflow.bpmn.storage.Packager import Packager
from SpiffWorkflow.storage.Serializer import Serializer

class BpmnSerializer(Serializer):
    """
    The BpmnSerializer class provides support for deserializing a Bpmn Workflow Spec from a BPMN package.
    The BPMN package must have been created using the Packager class (from SpiffWorkflow.bpmn.storage.Packager).

    It will also use the appropriate subclass of BpmnParser, if one is included in the metadata.ini file.
    """

    def serialize_workflow_spec(self, wf_spec, **kwargs):
        raise NotImplementedError("The BpmnSerializer class cannot be used to serialize. BPMN authoring should be done using a supported editor.")

    def serialize_workflow(self, workflow, **kwargs):
        raise NotImplementedError("The BPMN standard does not provide a specification for serializing a running workflow.")

    def deserialize_workflow(self, s_state, **kwargs):
        raise NotImplementedError("The BPMN standard does not provide a specification for serializing a running workflow.")

    def deserialize_workflow_spec(self, s_state, filename=None):
        """
        :param s_state: a byte-string with the contents of the packaged workflow archive, or a file-like object.
        :param filename: the name of the package file.
        """
        if isinstance(s_state, (str, bytes)):
            s_state = BytesIO(s_state)

        package_zip = zipfile.ZipFile(s_state, "r", compression=zipfile.ZIP_DEFLATED)
        config = configparser.SafeConfigParser()
        ini_fp = TextIOWrapper(package_zip.open(Packager.METADATA_FILE), encoding="UTF-8")
        try:
            config.readfp(ini_fp)
        finally:
            ini_fp.close()

        parser_class = BpmnParser

        try:
            parser_class_module = config.get('MetaData', 'parser_class_module', fallback=None)
        except TypeError:
            # unfortunately the fallback= does not exist on python 2
            parser_class_module = config.get('MetaData', 'parser_class_module', None)

        if parser_class_module:
            mod = __import__(parser_class_module, fromlist=[config.get('MetaData', 'parser_class')])
            parser_class = getattr(mod, config.get('MetaData', 'parser_class'))

        parser = parser_class()

        for info in package_zip.infolist():
            parts = os.path.split(info.filename)
            if len(parts) == 2 and not parts[0] and parts[1].lower().endswith('.bpmn'):
                #It is in the root of the ZIP and is a BPMN file
                try:
                    svg = package_zip.read(info.filename[:-5]+'.svg')
                except KeyError as e:
                    svg = None

                bpmn_fp = package_zip.open(info)
                try:
                    bpmn = ET.parse(bpmn_fp)
                finally:
                    bpmn_fp.close()

                parser.add_bpmn_xml(bpmn, svg=svg, filename='%s:%s' % (filename, info.filename))

        return parser.get_spec(config.get('MetaData', 'entry_point_process'))



########NEW FILE########
__FILENAME__ = CompactWorkflowSerializer
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from collections import deque
import json
import logging
from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.BpmnWorkflow import BpmnWorkflow
from SpiffWorkflow.specs import SubWorkflow
from SpiffWorkflow.storage.Serializer import Serializer

try:
    basestring
except:
    basestring = str


class UnrecoverableWorkflowChange(Exception):
    """
    This is thrown if the workflow cannot be restored because the workflow spec has changed, and the
    identified transitions no longer exist.
    """
    pass

class _RouteNode(object):
    """
    Private helper class
    """
    def __init__(self, task_spec, outgoing_route_node=None):
        self.task_spec = task_spec
        self.outgoing = [outgoing_route_node] if outgoing_route_node else []
        self.state = None

    def get_outgoing_by_spec(self, task_spec):
        m = [r for r in self.outgoing if r.task_spec == task_spec]
        return m[0] if m else None

    def to_list(self):
        l = []
        n = self
        while n.outgoing:
            assert len(n.outgoing) == 1, "to_list(..) cannot be called after a merge"
            l.append(n.task_spec)
            n = n.outgoing[0]
        l.append(n.task_spec)
        return l

    def contains(self, other_route):
        if isinstance(other_route, list):
            return self.to_list()[0:len(other_route)]==other_route

        #This only works before merging
        assert len(other_route.outgoing) <= 1, "contains(..) cannot be called after a merge"
        assert len(self.outgoing) <= 1, "contains(..) cannot be called after a merge"

        if other_route.task_spec == self.task_spec:
            if other_route.outgoing and self.outgoing:
                return self.outgoing[0].contains(other_route.outgoing[0])
            elif self.outgoing:
                return True
            elif not other_route.outgoing:
                return True
        return False

class _BpmnProcessSpecState(object):
    """
    Private helper class
    """

    def __init__(self, spec):
        self.spec = spec
        self.route = None

    def get_path_to_transition(self, transition, state, workflow_parents, taken_routes=None):
        #find a route passing through each task:
        route = [self.spec.start]
        route_to_parent_complete = None
        for task_name in workflow_parents:
            route = self._breadth_first_task_search(task_name, route)
            if route is None:
                raise UnrecoverableWorkflowChange('No path found for route \'%s\'' % transition)
            route_to_parent_complete = route + [route[-1].outputs[0]]
            route = route + [route[-1].spec.start]
        route = self._breadth_first_transition_search(transition, route, taken_routes=taken_routes)
        if route is None:
            raise UnrecoverableWorkflowChange('No path found for route \'%s\'' % transition)
        outgoing_route_node = None
        for spec in reversed(route):
            outgoing_route_node = _RouteNode(spec, outgoing_route_node)
            outgoing_route_node.state = state
        return outgoing_route_node, route_to_parent_complete

    def add_route(self, outgoing_route_node):
        if self.route:
            self._merge_routes(self.route, outgoing_route_node)
        else:
            self.route = outgoing_route_node

    def dump(self):
        print(self.get_dump())

    def get_dump(self):
        def recursive_dump(route_node, indent, verbose=False):

            task_spec = route_node.task_spec
            dump = '%s (%s:%s)' % (task_spec.name, task_spec.__class__.__name__, hex(id(task_spec))) + '\n'
            if verbose:
                if task_spec.inputs:
                    dump += indent + '-  IN: ' + ','.join(['%s (%s)' % (t.name, hex(id(t))) for t in task_spec.inputs]) + '\n'
                if task_spec.outputs:
                    dump += indent + '- OUT: ' + ','.join(['%s (%s)' % (t.name, hex(id(t))) for t in task_spec.outputs]) + '\n'

            for i, t in enumerate(route_node.outgoing):
                dump += indent + '   --> ' + recursive_dump(t,indent+('   |   ' if i+1 < len(route_node.outgoing) else '       '))
            return dump

        dump = recursive_dump(self.route, '')
        return dump

    def go(self, workflow):
        leaf_tasks = []
        self._go(workflow.task_tree.children[0], self.route, leaf_tasks)
        logging.debug('Leaf tasks after load, before _update_state: %s', leaf_tasks)
        for task in sorted(leaf_tasks, key=lambda t: 0 if getattr(t, '_bpmn_load_target_state', Task.READY) == Task.READY else 1):
            task.task_spec._update_state(task)
            task._inherit_data()
            if hasattr(task, '_bpmn_load_target_state'):
                delattr(task, '_bpmn_load_target_state')

    def _go(self, task, route_node, leaf_tasks):
        assert task.task_spec == route_node.task_spec
        if not route_node.outgoing:
            assert route_node.state is not None
            setattr(task, '_bpmn_load_target_state', route_node.state)
            leaf_tasks.append(task)
        else:
            if not task._is_finished():
                if issubclass(task.task_spec.__class__, SubWorkflow) and task.task_spec.spec.start in [o.task_spec for o in route_node.outgoing]:
                    self._go_in_to_subworkflow(task, [n.task_spec for n in route_node.outgoing])
                else:
                    self._complete_task_silent(task, [n.task_spec for n in route_node.outgoing])
            for n in route_node.outgoing:
                matching_child = [t for t in task.children if t.task_spec == n.task_spec]
                assert len(matching_child) == 1
                self._go(matching_child[0], n, leaf_tasks)

    def _complete_task_silent(self, task, target_children_specs):
        #This method simulates the completing of a task, but without hooks being called, and targeting a specific
        #subset of the children
        if task._is_finished():
            return
        task._set_state(Task.COMPLETED)

        task.children = []
        for task_spec in target_children_specs:
            task._add_child(task_spec)

    def _go_in_to_subworkflow(self, my_task, target_children_specs):
        #This method simulates the entering of a subworkflow, but without hooks being called, and targeting a specific
        #subset of the entry tasks in the subworkflow. It creates the new workflow instance and merges it in to the tree
        #This is based on SubWorkflow._on_ready_before_hook(..)
        if my_task._is_finished():
            return

        subworkflow    = my_task.task_spec._create_subworkflow(my_task)
        subworkflow.completed_event.connect(my_task.task_spec._on_subworkflow_completed, my_task)

        # Create the children (these are the tasks that follow the subworkflow, on completion:
        my_task.children = []
        my_task._sync_children(my_task.task_spec.outputs, Task.FUTURE)
        for t in my_task.children:
            t.task_spec._predict(t)


        # Integrate the tree of the subworkflow into the tree of this workflow.
        for child in subworkflow.task_tree.children:
            if child.task_spec in target_children_specs:
                my_task.children.insert(0, child)
                child.parent = my_task

        my_task._set_internal_data(subworkflow = subworkflow)

        my_task._set_state(Task.COMPLETED)

    def _merge_routes(self, target, src):
        assert target.task_spec == src.task_spec
        for out_route in src.outgoing:
            target_out_route = target.get_outgoing_by_spec(out_route.task_spec)
            if target_out_route:
                self._merge_routes(target_out_route, out_route)
            else:
                target.outgoing.append(out_route)

    def _breadth_first_transition_search(self, transition_id, starting_route, taken_routes=None):
        return self._breadth_first_search(starting_route, transition_id=transition_id, taken_routes=taken_routes)

    def _breadth_first_task_search(self, task_name, starting_route):
        return self._breadth_first_search(starting_route, task_name=task_name)

    def _breadth_first_search(self, starting_route, task_name=None, transition_id=None, taken_routes=None):
        q = deque()
        done = set()
        q.append(starting_route)
        while q:
            route = q.popleft()
            if not route[-1] == starting_route[-1]:
                if task_name and route[-1].name == task_name:
                    return route
                if transition_id and hasattr(route[-1], 'has_outgoing_sequence_flow') and route[-1].has_outgoing_sequence_flow(transition_id):
                    spec = route[-1].get_outgoing_sequence_flow_by_id(transition_id).target_task_spec
                    if taken_routes:
                        final_route = route + [spec]
                        for taken in taken_routes:
                            t = taken.to_list() if not isinstance(taken, list) else taken
                            if final_route[0:len(t)]==t:
                                spec = None
                                break
                    if spec:
                        route.append(spec)
                        return route
            for child in route[-1].outputs:
                new_route = route + [child]
                if len(new_route) > 10000:
                    raise ValueError('Maximum looping limit exceeded searching for path to %s' % (task_name or transition_id))
                new_route_r = tuple(new_route)
                if new_route_r not in done:
                    done.add(new_route_r)
                    q.append(new_route)
        return None


class CompactWorkflowSerializer(Serializer):
    """
    This class provides an implementation of serialize_workflow and deserialize_workflow that produces a
    compact representation of the workflow state, that can be stored in a database column or reasonably small
    size.

    It records ONLY enough information to identify the transition leading in to each WAITING or READY state,
    along with the state of that task. This is generally enough to resurrect a running BPMN workflow instance,
    with some limitations.

    Limitations:
    1. The compact representation does not include any workflow or task data. It is the responsibility of the
    calling application to record whatever data is relevant to it, and set it on the restored workflow.
    2. The restoring process will not produce exactly the same workflow tree - it finds the SHORTEST route to
    the saved READY and WAITING tasks, not the route that was actually taken. This means that the tree cannot be
    interrogated for historical information about the workflow. However, the workflow does follow the same logic
    paths as would have been followed by the original workflow.

    """

    STATE_SPEC_VERSION = 1

    def serialize_workflow_spec(self, wf_spec, **kwargs):
        raise NotImplementedError("The CompactWorkflowSerializer only supports workflow serialization.")

    def deserialize_workflow_spec(self, s_state, **kwargs):
        raise NotImplementedError("The CompactWorkflowSerializer only supports workflow serialization.")

    def serialize_workflow(self, workflow, include_spec=False,**kwargs):
        """
        :param workflow: the workflow instance to serialize
        :param include_spec: Always set to False (The CompactWorkflowSerializer only supports workflow serialization)
        """
        if include_spec:
            raise NotImplementedError('Including the spec serialization with the workflow state is not implemented.')
        return self._get_workflow_state(workflow)

    def deserialize_workflow(self, s_state, workflow_spec=None, read_only=False, **kwargs):
        """
        :param s_state: the state of the workflow as returned by serialize_workflow
        :param workflow_spec: the Workflow Spec of the workflow (CompactWorkflowSerializer only supports workflow serialization)
        :param read_only: (Optional) True if the workflow should be restored in READ ONLY mode

        NB: Additional kwargs passed to the deserialize_workflow method will be passed to the new_workflow method.
        """
        if workflow_spec is None:
            raise NotImplementedError('Including the spec serialization with the workflow state is not implemented. A \'workflow_spec\' must be provided.')
        workflow = self.new_workflow(workflow_spec, read_only=read_only, **kwargs)
        self._restore_workflow_state(workflow, s_state)
        return workflow

    def new_workflow(self, workflow_spec, read_only=False, **kwargs):
        """
        Create a new workflow instance from the given spec and arguments.

        :param workflow_spec: the workflow spec to use
        :param read_only: this should be in read only mode
        :param kwargs: Any extra kwargs passed to the deserialize_workflow method will be passed through here
        """
        return BpmnWorkflow(workflow_spec, read_only=read_only)

    def _get_workflow_state(self, workflow):
        active_tasks = workflow.get_tasks(state=(Task.READY | Task.WAITING))
        states = []

        for task in active_tasks:
            transition = task.parent.task_spec.get_outgoing_sequence_flow_by_spec(task.task_spec).id
            w = task.workflow
            workflow_parents = []
            while w.outer_workflow and w.outer_workflow != w:
                workflow_parents.append(w.name)
                w = w.outer_workflow
            state = ("W" if task.state == Task.WAITING else "R")
            states.append([transition, workflow_parents, state])

        compacted_states = []
        for state in sorted(states, key=lambda s:",".join([s[0], s[2], (':'.join(s[1]))])):
            if state[-1] == 'R':
                state.pop()
            if state[-1] == []:
                state.pop()
            if len(state) == 1:
                state = state[0]
            compacted_states.append(state)

        state_list = compacted_states+[self.STATE_SPEC_VERSION]
        state_s = json.dumps(state_list)[1:-1]
        return state_s

    def _restore_workflow_state(self, workflow, state):
        state_list = json.loads('['+state+']')

        self._check_spec_version(state_list[-1])

        s = _BpmnProcessSpecState(workflow.spec)

        routes = []
        for state in state_list[:-1]:
            if isinstance(state, basestring):
                state = [state]
            transition = state[0]
            workflow_parents = state[1] if len(state)>1 else []
            state = (Task.WAITING if len(state)>2 and state[2] == 'W' else Task.READY)

            route, route_to_parent_complete = s.get_path_to_transition(transition, state, workflow_parents)
            routes.append((route, route_to_parent_complete, transition, state, workflow_parents))

        retry=True
        retry_count = 0
        while (retry):
            if retry_count>100:
                raise ValueError('Maximum retry limit exceeded searching for unique paths')
            retry = False

            for i in range(len(routes)):
                route, route_to_parent_complete, transition, state, workflow_parents = routes[i]

                for j in range(len(routes)):
                    if i == j:
                        continue
                    other_route = routes[j][0]
                    route_to_parent_complete = routes[j][1]
                    if route.contains(other_route) or (route_to_parent_complete and route.contains(route_to_parent_complete)):
                        taken_routes = [r for r in routes if r[0]!=route]
                        taken_routes = [r for r in [r[0] for r in taken_routes] + [r[1] for r in taken_routes] if r]
                        route, route_to_parent_complete = s.get_path_to_transition(transition, state, workflow_parents, taken_routes=taken_routes)
                        for r in taken_routes:
                            assert not route.contains(r)
                        routes[i] = route, route_to_parent_complete, transition, state, workflow_parents
                        retry=True
                        retry_count += 1
                        break
                if retry:
                    break

        for r in routes:
            s.add_route(r[0])

        workflow._busy_with_restore = True
        try:
            if len(state_list) <= 1:
                workflow.cancel(success=True)
                return
            s.go(workflow)
        finally:
            workflow._busy_with_restore = False

    def _check_spec_version(self, v):
        #We only have one version right now:
        assert v == self.STATE_SPEC_VERSION

########NEW FILE########
__FILENAME__ = Packager
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from SpiffWorkflow.util.compat import configparser
try:
    # need to be lax on python 2; although io.StringIO exists,
    # it does not accept type str!
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import glob
import hashlib
import inspect
import xml.etree.ElementTree as ET
import zipfile
from optparse import OptionParser, OptionGroup
import os
from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnParser
from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException
from SpiffWorkflow.bpmn.parser.util import *

SIGNAVIO_NS='http://www.signavio.com'
CONFIG_SECTION_NAME = "Packager Options"

def md5hash(data):
    if not isinstance(data, bytes):
        data = data.encode('UTF-8')

    return hashlib.md5(data).hexdigest().lower()


class Packager(object):
    """
    The Packager class pre-parses a set of BPMN files (together with their SVG representation),
    validates the contents and then produces a ZIP-based archive containing the pre-parsed
    BPMN and SVG files, the source files (for reference) and a metadata.ini file that contains
    enough information to create a BpmnProcessSpec instance from the archive (e.g. the ID of the
    entry point process).

    This class can be extended and any public method overridden to do additional validation / parsing
    or to package additional metadata.

    Extension point:
    PARSER_CLASS: provide the class that should be used to parse the BPMN files. The fully-qualified
    name will be included in the metadata.ini file, so that the BpmnSerializer can instantiate the right
    parser to deal with the package.

    Editor hooks:
    package_for_editor_<editor name>(self, spec, filename): Called once for each BPMN file. Should add any additional files to the archive.

    """

    METADATA_FILE = "metadata.ini"
    MANIFEST_FILE = "manifest.ini"
    PARSER_CLASS = BpmnParser

    def __init__(self, package_file, entry_point_process, meta_data=None, editor=None):
        """
        Constructor.

        :param package_file: a file-like object where the contents of the package must be written to
        :param entry_point_process: the name or ID of the entry point process
        :param meta_data: A list of meta-data tuples to include in the metadata.ini file (in addition to the standard ones)
        :param editor: The name of the editor used to create the source BPMN / SVG files. This activates additional hook method calls. (optional)
        """
        self.package_file = package_file
        self.entry_point_process = entry_point_process
        self.parser = self.PARSER_CLASS()
        self.meta_data = meta_data or []
        self.input_files = []
        self.input_path_prefix = None
        self.editor = editor
        self.manifest = {}

    def add_bpmn_file(self, filename):
        """
        Add the given BPMN filename to the packager's set.
        """
        self.add_bpmn_files([filename])

    def add_bpmn_files_by_glob(self, g):
        """
        Add all filenames matching the provided pattern (e.g. *.bpmn) to the packager's set.
        """
        self.add_bpmn_files(glob.glob(g))

    def add_bpmn_files(self, filenames):
        """
        Add all filenames in the given list to the packager's set.
        """
        self.input_files += filenames

    def create_package(self):
        """
        Creates the package, writing the data out to the provided file-like object.
        """

        #Check that all files exist (and calculate the longest shared path prefix):
        self.input_path_prefix = None
        for filename in self.input_files:
            if not os.path.isfile(filename):
                raise ValueError('%s does not exist or is not a file' % filename)
            if self.input_path_prefix:
                full = os.path.abspath(os.path.dirname(filename))
                while not full.startswith(self.input_path_prefix) and self.input_path_prefix:
                    self.input_path_prefix = self.input_path_prefix[:-1]
            else:
                self.input_path_prefix = os.path.abspath(os.path.dirname(filename))

        #Parse all of the XML:
        self.bpmn = {}
        for filename in self.input_files:
            bpmn = ET.parse(filename)
            self.bpmn[os.path.abspath(filename)] = bpmn

        #Now run through pre-parsing and validation:
        for filename, bpmn in self.bpmn.items():
            bpmn = self.pre_parse_and_validate(bpmn, filename)
            self.bpmn[os.path.abspath(filename)] = bpmn

        #Now check that we can parse it fine:
        for filename, bpmn in self.bpmn.items():
            self.parser.add_bpmn_xml(bpmn, filename=filename)

        self.wf_spec = self.parser.get_spec(self.entry_point_process)

        #Now package everything:
        self.package_zip = zipfile.ZipFile(self.package_file, "w", compression=zipfile.ZIP_DEFLATED)

        done_files = set()
        for spec in self.wf_spec.get_specs_depth_first():
            filename = spec.file
            if not filename in done_files:
                done_files.add(filename)

                bpmn = self.bpmn[os.path.abspath(filename)]
                self.write_to_package_zip("%s.bpmn" % spec.name, ET.tostring(bpmn.getroot()))

                self.write_file_to_package_zip("src/" + self._get_zip_path(filename), filename)

                self._call_editor_hook('package_for_editor', spec, filename)

        self.write_meta_data()
        self.write_manifest()

        self.package_zip.close()

    def write_file_to_package_zip(self, filename, src_filename):
        """
        Writes a local file in to the zip file and adds it to the manifest dictionary
        :param filename: The zip file name
        :param src_filename: the local file name

        """
        f = open(src_filename)
        with f:
            data = f.read()
        self.manifest[filename] = md5hash(data)
        self.package_zip.write(src_filename, filename)

    def write_to_package_zip(self, filename, data):
        """
        Writes data to the zip file and adds it to the manifest dictionary
        :param filename: The zip file name
        :param data: the data

        """
        self.manifest[filename] = md5hash(data)
        self.package_zip.writestr(filename, data)

    def write_manifest(self):
        """
        Write the manifest content to the zip file. It must be a predictable order.
        """
        config = configparser.SafeConfigParser()

        config.add_section('Manifest')

        for f in sorted(self.manifest.keys()):
            config.set('Manifest', f.replace('\\', '/').lower(), self.manifest[f])

        ini = StringIO()
        config.write(ini)
        self.manifest_data = ini.getvalue()
        self.package_zip.writestr(self.MANIFEST_FILE, self.manifest_data)


    def pre_parse_and_validate(self, bpmn, filename):
        """
        A subclass can override this method to provide additional parseing or validation.
        It should call the parent method first.

        :param bpmn: an lxml tree of the bpmn content
        :param filename: the source file name

        This must return the updated bpmn object (or a replacement)
        """
        bpmn = self._call_editor_hook('pre_parse_and_validate', bpmn, filename) or bpmn

        return bpmn

    def pre_parse_and_validate_signavio(self, bpmn, filename):
        """
        This is the Signavio specific editor hook for pre-parsing and validation.

        A subclass can override this method to provide additional parseing or validation.
        It should call the parent method first.

        :param bpmn: an lxml tree of the bpmn content
        :param filename: the source file name

        This must return the updated bpmn object (or a replacement)
        """
        self._check_for_disconnected_boundary_events_signavio(bpmn, filename)
        self._fix_call_activities_signavio(bpmn, filename)
        return bpmn

    def _check_for_disconnected_boundary_events_signavio(self, bpmn, filename):
        #signavio sometimes disconnects a BoundaryEvent from it's owning task
        #They then show up as intermediateCatchEvents without any incoming sequence flows
        xpath = xpath_eval(bpmn)
        for catch_event in xpath('.//bpmn:intermediateCatchEvent'):
            incoming = xpath('.//bpmn:sequenceFlow[@targetRef="%s"]' % catch_event.get('id'))
            if not incoming:
                raise ValidationException('Intermediate Catch Event has no incoming sequences. This might be a Boundary Event that has been disconnected.',
                node=catch_event, filename=filename)

    def _fix_call_activities_signavio(self, bpmn, filename):
        """
        Signavio produces slightly invalid BPMN for call activity nodes... It is supposed to put a reference to the id of the called process
        in to the calledElement attribute. Instead it stores a string (which is the name of the process - not its ID, in our interpretation)
        in an extension tag.

        This code gets the name of the 'subprocess reference', finds a process with a matching name, and sets the calledElement attribute
        to the id of the process.

        """
        for node in xpath_eval(bpmn)(".//bpmn:callActivity"):
            calledElement = node.get('calledElement', None)
            if not calledElement:
                signavioMetaData = xpath_eval(node, extra_ns={'signavio':SIGNAVIO_NS})('.//signavio:signavioMetaData[@metaKey="entry"]')
                if not signavioMetaData:
                    raise ValidationException('No Signavio "Subprocess reference" specified.', node=node, filename=filename)
                subprocess_reference = one(signavioMetaData).get('metaValue')
                matches = []
                for b in self.bpmn.values():
                    for p in xpath_eval(b)(".//bpmn:process"):
                        if p.get('name', p.get('id', None)) == subprocess_reference:
                            matches.append(p)
                if not matches:
                    raise ValidationException("No matching process definition found for '%s'." % subprocess_reference, node=node, filename=filename)
                if len(matches) != 1:
                    raise ValidationException("More than one matching process definition found for '%s'." % subprocess_reference, node=node, filename=filename)

                node.set('calledElement', matches[0].get('id'))

    def _call_editor_hook(self, hook, *args, **kwargs):
        if self.editor:
            hook_func = getattr(self, "%s_%s" % (hook, self.editor), None)
            if hook_func:
                return hook_func(*args, **kwargs)
        return None

    def package_for_editor_signavio(self, spec, filename):
        """
        Adds the SVG files to the archive for this BPMN file.
        """
        signavio_file = filename[:-len('.bpmn20.xml')] + '.signavio.xml'
        if os.path.exists(signavio_file):
            self.write_file_to_package_zip("src/" + self._get_zip_path(signavio_file), signavio_file)

            f = open(signavio_file, 'r')
            try:
                signavio_tree = ET.parse(f)
            finally:
                f.close()
            svg_node = one(signavio_tree.findall('.//svg-representation'))
            self.write_to_package_zip("%s.svg" % spec.name, svg_node.text)

    def write_meta_data(self):
        """
        Writes the metadata.ini file to the archive.
        """
        config = configparser.SafeConfigParser()

        config.add_section('MetaData')
        config.set('MetaData', 'entry_point_process', self.wf_spec.name)
        if self.editor:
            config.set('MetaData', 'editor', self.editor)

        for k, v in self.meta_data:
            config.set('MetaData', k, v)

        if not self.PARSER_CLASS == BpmnParser:
            config.set('MetaData', 'parser_class_module', inspect.getmodule(self.PARSER_CLASS).__name__)
            config.set('MetaData', 'parser_class', self.PARSER_CLASS.__name__)

        ini = StringIO()
        config.write(ini)
        self.write_to_package_zip(self.METADATA_FILE, ini.getvalue())

    def _get_zip_path(self, filename):
        p = os.path.abspath(filename)[len(self.input_path_prefix):].replace(os.path.sep, '/')
        while p.startswith('/'):
            p = p[1:]
        return p

    @classmethod
    def get_version(cls):
        try:
            import pkg_resources  # part of setuptools
            version = pkg_resources.require("SpiffWorkflow")[0].version
        except Exception as ex:
            version = 'DEV'
        return version

    @classmethod
    def create_option_parser(cls):
        """
        Override in subclass if required.
        """
        return OptionParser(
            usage="%prog [options] -o <package file> -p <entry point process> <input BPMN files ...>",
            version="SpiffWorkflow BPMN Packager %s" % (cls.get_version()))

    @classmethod
    def add_main_options(cls, parser):
        """
        Override in subclass if required.
        """
        parser.add_option("-o", "--output", dest="package_file",
            help="create the BPMN package in the specified file")
        parser.add_option("-p", "--process", dest="entry_point_process",
            help="specify the entry point process")
        parser.add_option("-c", "--config-file", dest="config_file",
            help="specify a config file to use")
        parser.add_option("-i", "--initialise-config-file", action="store_true", dest="init_config_file", default=False,
            help="create a new config file from the specified options")

        group = OptionGroup(parser, "BPMN Editor Options",
            "These options are not required, but may be provided to activate special features of supported BPMN editors.")
        group.add_option("--editor", dest="editor",
            help="editors with special support: signavio")
        parser.add_option_group(group)

    @classmethod
    def add_additional_options(cls, parser):
        """
        Override in subclass if required.
        """
        group = OptionGroup(parser, "Target Engine Options",
            "These options are not required, but may be provided if a specific BPMN application engine is targeted.")
        group.add_option("-e", "--target-engine", dest="target_engine",
            help="target the specified BPMN application engine")
        group.add_option("-t", "--target-version", dest="target_engine_version",
            help="target the specified version of the BPMN application engine")
        parser.add_option_group(group)

    @classmethod
    def check_args(cls, config, options, args, parser, package_file=None):
        """
        Override in subclass if required.
        """
        if not args:
            parser.error("no input files specified")
        if not (package_file or options.package_file):
            parser.error("no package file specified")
        if not options.entry_point_process:
            parser.error("no entry point process specified")


    @classmethod
    def merge_options_and_config(cls, config, options, args):
        """
        Override in subclass if required.
        """
        if args:
            config.set(CONFIG_SECTION_NAME, 'input_files', ','.join(args))
        elif config.has_option(CONFIG_SECTION_NAME, 'input_files'):
            for i in config.get(CONFIG_SECTION_NAME, 'input_files').split(','):
                if not os.path.isabs(i):
                    i = os.path.abspath(os.path.join(os.path.dirname(options.config_file), i))
                args.append(i)

        cls.merge_option_and_config_str('package_file', config, options)
        cls.merge_option_and_config_str('entry_point_process', config, options)
        cls.merge_option_and_config_str('target_engine', config, options)
        cls.merge_option_and_config_str('target_engine_version', config, options)
        cls.merge_option_and_config_str('editor', config, options)

    @classmethod
    def merge_option_and_config_str(cls, option_name, config, options):
        """
        Utility method to merge an option and config, with the option taking precedence
        """

        opt = getattr(options, option_name, None)
        if opt:
            config.set(CONFIG_SECTION_NAME, option_name, opt)
        elif config.has_option(CONFIG_SECTION_NAME, option_name):
            setattr(options, option_name, config.get(CONFIG_SECTION_NAME, option_name))

    @classmethod
    def create_meta_data(cls, options, args, parser):
        """
        Override in subclass if required.
        """
        meta_data = []
        meta_data.append(('spiff_version', cls.get_version()))
        if options.target_engine:
            meta_data.append(('target_engine', options.target_engine))
        if options.target_engine:
            meta_data.append(('target_engine_version', options.target_engine_version))
        return meta_data

    @classmethod
    def main(cls, argv=None, package_file=None):
        parser = cls.create_option_parser()

        cls.add_main_options(parser)

        cls.add_additional_options(parser)

        (options, args) = parser.parse_args(args=argv)

        config = configparser.SafeConfigParser()
        if options.config_file:
            config.read(options.config_file)
        if not config.has_section(CONFIG_SECTION_NAME):
            config.add_section(CONFIG_SECTION_NAME)

        cls.merge_options_and_config(config, options, args)
        if options.init_config_file:
            if not options.config_file:
                parser.error("no config file specified - cannot initialise config file")
            f = open(options.config_file, "w")
            with f:
                config.write(f)
                return

        cls.check_args(config, options, args, parser, package_file)

        meta_data = cls.create_meta_data(options, args, parser)

        packager = cls(package_file=package_file or options.package_file, entry_point_process=options.entry_point_process, meta_data=meta_data, editor=options.editor)
        for a in args:
            packager.add_bpmn_files_by_glob(a)
        packager.create_package()

        return packager

def main(packager_class=None):
    """
    :param packager_class: The Packager class to use. Default: Packager.
    """

    if not packager_class:
        packager_class = Packager

    packager_class.main()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


class WorkflowException(Exception):
    """
    Base class for all SpiffWorkflow-generated exceptions.
    """

    def __init__(self, sender, error):
        """
        Standard exception class.

        :param sender: the task that threw the exception.
        :type sender: Task
        :param error: a human readable error message
        :type error: string
        """
        Exception.__init__(self, '%s: %s' % (sender.name, error))
        self.sender = sender # Points to the Task that generated the exception.


class StorageException(Exception):
    pass

########NEW FILE########
__FILENAME__ = operators
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import logging
import re

LOG = logging.getLogger(__name__)

try:
    unicode
except:
    unicode = str


class Attrib(object):
    """
    Used for marking a value such that it is recognized to be an
    attribute name by valueof().
    """
    def __init__(self, name):
        self.name = name

    def serialize(self, serializer):
        """
        Serializes the instance using the provided serializer.

        :type  serializer: L{SpiffWorkflow.storage.Serializer}
        :param serializer: The serializer to use.
        :rtype:  object
        :returns: The serialized object.
        """
        return serializer._serialize_attrib(self)

    @classmethod
    def deserialize(cls, serializer, s_state):
        """
        Serializes the instance using the provided serializer.

        :type  serializer: L{SpiffWorkflow.storage.Serializer}
        :param serializer: The serializer to use.
        :rtype:  object
        :returns: The serialized object.
        """
        return serializer._deserialize_attrib(cls, s_state)


class PathAttrib(object):
    """
    Used for marking a value such that it is recognized to be an
    attribute obtained by evaluating a path by valueof().
    """
    def __init__(self, path):
        self.path = path

    def serialize(self, serializer):
        """
        Serializes the instance using the provided serializer.

        :type  serializer: L{SpiffWorkflow.storage.Serializer}
        :param serializer: The serializer to use.
        :rtype:  object
        :returns: The serialized object.
        """
        return serializer._serialize_pathattrib(self)

    @classmethod
    def deserialize(cls, serializer, s_state):
        """
        Serializes the instance using the provided serializer.

        :type  serializer: L{SpiffWorkflow.storage.Serializer}
        :param serializer: The serializer to use.
        :rtype:  object
        :returns: The serialized object.
        """
        return serializer._deserialize_pathattrib(cls, s_state)


class Assign(object):
    """
    Assigns a new value to an attribute. The source may be either
    a static value, or another attribute.
    """

    def __init__(self,
                 left_attribute,
                 right_attribute=None,
                 right=None,
                 **kwargs):
        """
        Constructor.

        :type  left_attribute: str
        :param left_attribute: The name of the attribute to which the value
                               is assigned.
        :type  right: object
        :param right: A static value that, when given, is assigned to
                      left_attribute.
        :type  right_attribute: str
        :param right_attribute: When given, the attribute with the given
                                name is used as the source (instead of the
                                static value).
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.TaskSpec}.
        """
        if not right_attribute and not right:
            raise ValueError('require argument: right_attribute or right')
        assert left_attribute is not None
        self.left_attribute = left_attribute
        self.right_attribute = right_attribute
        self.right = right

    def assign(self, from_obj, to_obj):
        # Fetch the value of the right expression.
        if self.right is not None:
            right = self.right
        else:
            right = from_obj.get_data(self.right_attribute)
        to_obj.set_data(**{unicode(self.left_attribute): right})


def valueof(scope, op):
    if op is None:
        return None
    elif isinstance(op, Attrib):
        if op.name not in scope.data:
            LOG.debug("Attrib('%s') not present in task '%s' data" %
                    (op.name, scope.get_name()))
        return scope.get_data(op.name)
    elif isinstance(op, PathAttrib):
        if not op.path:
            return None
        parts = op.path.split('/')
        data = scope.data
        for part in parts:
            if part not in data:
                LOG.debug("PathAttrib('%s') not present in task '%s' "
                        "data" % (op.path, scope.get_name()),
                        extra=dict(data=scope.data))
                return None
            data = data[part]  # move down the path
        return data
    else:
        return op


class Operator(object):
    """
    Abstract base class for all operators.
    """

    def __init__(self, *args):
        """
        Constructor.
        """
        if len(args) == 0:
            raise TypeError("Too few arguments")
        self.args = args

    def _get_values(self, task):
        values = []
        for arg in self.args:
            values.append(unicode(valueof(task, arg)))
        return values

    def _matches(self, task):
        raise Exception("Abstract class, do not call")

    def serialize(self, serializer):
        """
        Serializes the instance using the provided serializer.

        :type  serializer: L{SpiffWorkflow.storage.Serializer}
        :param serializer: The serializer to use.
        :rtype:  object
        :returns: The serialized object.
        """
        return serializer._serialize_operator(self)

    @classmethod
    def deserialize(cls, serializer, s_state):
        """
        Serializes the instance using the provided serializer.

        :type  serializer: L{SpiffWorkflow.storage.Serializer}
        :param serializer: The serializer to use.
        :rtype:  object
        :returns: The serialized object.
        """
        return serializer._deserialize_operator(s_state)


class Equal(Operator):
    """
    This class represents the EQUAL operator.
    """
    def _matches(self, task):
        values = self._get_values(task)
        last = values[0]
        for value in values:
            if value != last:
                return False
            last = value
        return True

    def serialize(self, serializer):
        return serializer._serialize_operator_equal(self)

    @classmethod
    def deserialize(cls, serializer, s_state):
        return serializer._deserialize_operator_equal(s_state)


class NotEqual(Operator):
    """
    This class represents the NOT EQUAL operator.
    """
    def _matches(self, task):
        values = self._get_values(task)
        last = values[0]
        for value in values:
            if value != last:
                return True
            last = value
        return False

    def serialize(self, serializer):
        return serializer._serialize_operator_not_equal(self)

    @classmethod
    def deserialize(cls, serializer, s_state):
        return serializer._deserialize_operator_not_equal(s_state)


class GreaterThan(Operator):
    """
    This class represents the GREATER THAN operator.
    """
    def __init__(self, left, right):
        """
        Constructor.
        """
        Operator.__init__(self, left, right)

    def _matches(self, task):
        left, right = self._get_values(task)
        return int(left) > int(right)

    def serialize(self, serializer):
        return serializer._serialize_operator_greater_than(self)

    @classmethod
    def deserialize(cls, serializer, s_state):
        return serializer._deserialize_operator_greater_than(s_state)


class LessThan(Operator):
    """
    This class represents the LESS THAN operator.
    """
    def __init__(self, left, right):
        """
        Constructor.
        """
        Operator.__init__(self, left, right)

    def _matches(self, task):
        left, right = self._get_values(task)
        return int(left) < int(right)

    def serialize(self, serializer):
        return serializer._serialize_operator_less_than(self)

    @classmethod
    def deserialize(cls, serializer, s_state):
        return serializer._deserialize_operator_less_than(s_state)


class Match(Operator):
    """
    This class represents the regular expression match operator.
    """
    def __init__(self, regex, *args):
        """
        Constructor.
        """
        Operator.__init__(self, *args)
        self.regex = re.compile(regex)

    def _matches(self, task):
        for value in self._get_values(task):
            if not self.regex.search(value):
                return False
        return True

    def serialize(self, serializer):
        return serializer._serialize_operator_match(self)

    @classmethod
    def deserialize(cls, serializer, s_state):
        return serializer._deserialize_operator_match(s_state)

########NEW FILE########
__FILENAME__ = AcquireMutex
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,MA  02110-1301  USA
from SpiffWorkflow.Task import Task
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.specs.TaskSpec import TaskSpec

class AcquireMutex(TaskSpec):
    """
    This class implements a task that acquires a mutex (lock), protecting
    a section of the workflow from being accessed by other sections.
    If more than one input is connected, the task performs an implicit
    multi merge.
    If more than one output is connected, the task performs an implicit
    parallel split.
    """

    def __init__(self, parent, name, mutex, **kwargs):
        """
        Constructor.

        :type  parent: TaskSpec
        :param parent: A reference to the parent task spec.
        :type  name: str
        :param name: The name of the task spec.
        :type  mutex: str
        :param mutex: The name of the mutex that should be acquired.
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.TaskSpec}.
        """
        assert mutex is not None
        TaskSpec.__init__(self, parent, name, **kwargs)
        self.mutex = mutex

    def _update_state_hook(self, my_task):
        mutex = my_task.workflow._get_mutex(self.mutex)
        if mutex.testandset():
            self.entered_event.emit(my_task.workflow, my_task)
            my_task._ready()
            return
        my_task._set_state(Task.WAITING)

    def serialize(self, serializer):
        return serializer._serialize_acquire_mutex(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer._deserialize_acquire_mutex(wf_spec, s_state)

########NEW FILE########
__FILENAME__ = Cancel
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.specs.TaskSpec import TaskSpec

class Cancel(TaskSpec):
    """
    This class cancels a complete workflow.
    If more than one input is connected, the task performs an implicit
    multi merge.
    If more than one output is connected, the task performs an implicit
    parallel split.
    """

    def __init__(self, parent, name, success = False, **kwargs):
        """
        Constructor.

        :type  parent: TaskSpec
        :param parent: A reference to the parent task spec.
        :type  name: str
        :param name: The name of the task spec.
        :type  success: bool
        :param success: Whether to cancel successfully or unsuccessfully.
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.TaskSpec}.
        """
        TaskSpec.__init__(self, parent, name, **kwargs)
        self.cancel_successfully = success

    def test(self):
        """
        Checks whether all required attributes are set. Throws an exception
        if an error was detected.
        """
        TaskSpec.test(self)
        if len(self.outputs) > 0:
            raise WorkflowException(self, 'Cancel with an output.')

    def _on_complete_hook(self, my_task):
        my_task.workflow.cancel(self.cancel_successfully)
        TaskSpec._on_complete_hook(self, my_task)

    def serialize(self, serializer):
        return serializer._serialize_cancel(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer._deserialize_cancel(wf_spec, s_state)

########NEW FILE########
__FILENAME__ = CancelTask
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from SpiffWorkflow import Task
from SpiffWorkflow.specs.TaskSpec import TaskSpec
from SpiffWorkflow.specs.Trigger import Trigger

class CancelTask(Trigger):
    """
    This class implements a trigger that cancels another task (branch).
    If more than one input is connected, the task performs an implicit
    multi merge.
    If more than one output is connected, the task performs an implicit
    parallel split.
    """

    def _on_complete_hook(self, my_task):
        for task_name in self.context:
            cancel_tasks = my_task.workflow.get_task_spec_from_name(task_name)
            for cancel_task in my_task._get_root()._find_any(cancel_tasks):
                cancel_task.cancel()
        TaskSpec._on_complete_hook(self, my_task)

    def serialize(self, serializer):
        return serializer._serialize_cancel_task(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer._deserialize_cancel_task(wf_spec, s_state)

########NEW FILE########
__FILENAME__ = Celery
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import logging

from SpiffWorkflow.Task import Task
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.specs.TaskSpec import TaskSpec
from SpiffWorkflow.operators import valueof, Attrib, PathAttrib
from SpiffWorkflow.util import merge_dictionary

try:
    from celery.app import default_app
    from celery.result import AsyncResult
except ImportError:
    have_celery = False
else:
    have_celery = True

LOG = logging.getLogger(__name__)


def _eval_args(args, my_task):
    """Parses args and evaluates any Attrib entries"""
    results = []
    for arg in args:
        if isinstance(arg, Attrib) or isinstance(arg, PathAttrib):
            results.append(valueof(my_task, arg))
        else:
            results.append(arg)
    return results


def _eval_kwargs(kwargs, my_task):
    """Parses kwargs and evaluates any Attrib entries"""
    results = {}
    for kwarg, value in kwargs.items():
        if isinstance(value, Attrib) or isinstance(value, PathAttrib):
            results[kwarg] = valueof(my_task, value)
        else:
            results[kwarg] = value
    return results


def Serializable(o):
    """Make sure an object is JSON-serializable
    Use this to return errors and other info that does not need to be
    deserialized or does not contain important app data. Best for returning
    error info and such"""
    if type(o) in [basestring, dict, int, long]:
        return o
    else:
        try:
            s = json.dumps(o)
            return o
        except:
            LOG.debug("Got a non-serilizeable object: %s" % o)
            return o.__repr__()


class Celery(TaskSpec):
    """This class implements a celeryd task that is sent to the celery queue for
    completion."""

    def __init__(self, parent, name, call, call_args=None, result_key=None,
                 merge_results=False, **kwargs):
        """Constructor.

        The args/kwargs arguments support Attrib classes in the parameters for
        delayed evaluation of inputs until run-time. Example usage:
        task = Celery(wfspec, 'MyTask', 'celery.call',
                 call_args=['hello', 'world', Attrib('number')],
                 any_param=Attrib('result'))

        For serialization, the celery task_id is stored in internal_attributes,
        but the celery async call is only storred as an attr of the task (since
        it is not always serializable). When deserialized, the async_call attr
        is reset in the _try_fire call.

        :type  parent: TaskSpec
        :param parent: A reference to the parent task spec.
        :type  name: str
        :param name: The name of the task spec.
        :type  call: str
        :param call: The name of the celery task that needs to be called.
        :type  call_args: list
        :param call_args: args to pass to celery task.
        :type  result_key: str
        :param result_key: The key to use to store the results of the call in
                task.attributes. If None, then dicts are expanded into
                attributes and values are stored in 'result'.
        :param merge_results: merge the results in instead of overwriting existing
                fields.
        :type  kwargs: dict
        :param kwargs: kwargs to pass to celery task.
        """
        if not have_celery:
            raise Exception("Unable to import python-celery imports.")
        assert parent  is not None
        assert name    is not None
        assert call is not None
        TaskSpec.__init__(self, parent, name, **kwargs)
        self.description = kwargs.pop('description', '')
        self.call = call
        self.args = call_args
        self.merge_results = merge_results
        skip = 'data', 'defines', 'pre_assign', 'post_assign', 'lock'
        self.kwargs = dict(i for i in kwargs.items() if i[0] not in skip)
        self.result_key = result_key
        LOG.debug("Celery task '%s' created to call '%s'" % (name, call))

    def _send_call(self, my_task):
        """Sends Celery asynchronous call and stores async call information for
        retrieval laster"""
        arg, kwargs = None, None
        if self.args:
            args = _eval_args(self.args, my_task)
        if self.kwargs:
            kwargs = _eval_kwargs(self.kwargs, my_task)
        LOG.debug("%s (task id %s) calling %s" % (self.name, my_task.id,
                self.call), extra=dict(data=dict(args=args, kwargs=kwargs)))
        async_call = default_app.send_task(self.call, args=args, kwargs=kwargs)
        my_task._set_internal_attribute(task_id=async_call.task_id)
        my_task.async_call = async_call
        LOG.debug("'%s' called: %s" % (self.call, my_task.async_call.task_id))

    def _retry_fire(self, my_task):
        """ Abort celery task and retry it"""
        if not my_task._has_state(Task.WAITING):
            raise WorkflowException(my_task, "Cannot refire a task that is not"
                    "in WAITING state")
        # Check state of existing call and abort it (save history)
        if my_task._get_internal_attribute('task_id') is not None:
            if not hasattr(my_task, 'async_call'):
                task_id = my_task._get_internal_attribute('task_id')
                my_task.async_call = default_app.AsyncResult(task_id)
                my_task.deserialized = True
                my_task.async_call.state  # manually refresh
            async_call = my_task.async_call
            if async_call.state == 'FAILED':
                pass
            elif async_call.state in ['RETRY', 'PENDING', 'STARTED']:
                async_call.revoke()
                LOG.info("Celery task '%s' was in %s state and was revoked" % (
                    async_call.state, async_call))
            elif async_call.state == 'SUCCESS':
                LOG.warning("Celery task '%s' succeeded, but a refire was "
                        "requested" % async_call)
            self._clear_celery_task_data(my_task)
        # Retrigger
        return self._try_fire(my_task)

    def _clear_celery_task_data(self, my_task):
        """ Clear celery task data """
        # Save history
        if 'task_id' in my_task.internal_attributes:
            # Save history for diagnostics/forensics
            history = my_task._get_internal_attribute('task_history', [])
            history.append(my_task._get_internal_attribute('task_id'))
            del my_task.internal_attributes['task_id']
            my_task._set_internal_attribute(task_history=history)
        if 'task_state' in my_task.internal_attributes:
            del my_task.internal_attributes['task_state']
        if 'error' in my_task.attributes:
            del my_task.attributes['error']
        if hasattr(my_task, 'async_call'):
            delattr(my_task, 'async_call')
        if hasattr(my_task, 'deserialized'):
            delattr(my_task, 'deserialized')

    def _try_fire(self, my_task, force=False):
        """Returns False when successfully fired, True otherwise"""

        # Deserialize async call if necessary
        if not hasattr(my_task, 'async_call') and \
                my_task._get_internal_attribute('task_id') is not None:
            task_id = my_task._get_internal_attribute('task_id')
            my_task.async_call = default_app.AsyncResult(task_id)
            my_task.deserialized = True
            LOG.debug("Reanimate AsyncCall %s" % task_id)

        # Make the call if not already done
        if not hasattr(my_task, 'async_call'):
            self._send_call(my_task)

        # Get call status (and manually refresh if deserialized)
        if getattr(my_task, "deserialized", False):
            my_task.async_call.state  # must manually refresh if deserialized
        if my_task.async_call.state == 'FAILURE':
            LOG.debug("Async Call for task '%s' failed: %s" % (
                    my_task.get_name(), my_task.async_call.info))
            info = {}
            info['traceback'] = my_task.async_call.traceback
            info['info'] = Serializable(my_task.async_call.info)
            info['state'] = my_task.async_call.state
            my_task._set_internal_attribute(task_state=info)
        elif my_task.async_call.state == 'RETRY':
            info = {}
            info['traceback'] = my_task.async_call.traceback
            info['info'] = Serializable(my_task.async_call.info)
            info['state'] = my_task.async_call.state
            my_task._set_internal_attribute(task_state=info)
        elif my_task.async_call.ready():
            result = my_task.async_call.result
            if isinstance(result, Exception):
                LOG.warn("Celery call %s failed: %s" % (self.call, result))
                my_task._set_internal_attribute(error=Serializable(result))
                return False
            LOG.debug("Completed celery call %s with result=%s" % (self.call,
                    result))
            # Format result
            if self.result_key:
                data = {self.result_key: result}
            else:
                if isinstance(result, dict):
                    data = result
                else:
                    data = {'result': result}
            # Load formatted result into attributes
            if self.merge_results:
                merge_dictionary(my_task.attributes, data)
            else:
                my_task.set_attribute(**data)
            return True
        else:
            LOG.debug("async_call.ready()=%s. TryFire for '%s' "
                    "returning False" % (my_task.async_call.ready(),
                            my_task.get_name()))
            return False

    def _update_state_hook(self, my_task):
        if not self._try_fire(my_task):
            if not my_task._has_state(Task.WAITING):
                LOG.debug("'%s' going to WAITING state" % my_task.get_name())
                my_task.state = Task.WAITING
            return
        super(Celery, self)._update_state_hook(my_task)

    def serialize(self, serializer):
        return serializer._serialize_celery(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        spec = serializer._deserialize_celery(wf_spec, s_state)
        return spec

########NEW FILE########
__FILENAME__ = Choose
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from SpiffWorkflow import Task
from SpiffWorkflow.specs.TaskSpec import TaskSpec
from SpiffWorkflow.specs.Trigger import Trigger

class Choose(Trigger):
    """
    This class implements a task that causes an associated MultiChoice
    task to select the tasks with the specified name.
    If more than one input is connected, the task performs an implicit
    multi merge.
    If more than one output is connected, the task performs an implicit
    parallel split.
    """

    def __init__(self, parent, name, context, choice = None, **kwargs):
        """
        Constructor.

        :type  parent: TaskSpec
        :param parent: A reference to the parent task spec.
        :type  name: str
        :param name: The name of the task spec.
        :type  context: str
        :param context: The name of the MultiChoice that is instructed to
                        select the specified outputs.
        :type  choice: list(TaskSpec)
        :param choice: The list of task specs that is selected.
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.TaskSpec}.
        """
        assert parent is not None
        assert name is not None
        assert context is not None
        #HACK: inherit from TaskSpec (not Trigger) on purpose.
        TaskSpec.__init__(self, parent, name, **kwargs)
        self.context = context
        self.choice  = choice is not None and choice or []

    def _on_complete_hook(self, my_task):
        context = my_task.workflow.get_task_spec_from_name(self.context)
        triggered = []
        for task in my_task.workflow.task_tree:
            if task.thread_id != my_task.thread_id:
                continue
            if task.task_spec == context:
                task.trigger(self.choice)
                triggered.append(task)
        for task in triggered:
            context._predict(task)
        TaskSpec._on_complete_hook(self, my_task)

    def serialize(self, serializer):
        return serializer._serialize_choose(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer._deserialize_choose(wf_spec, s_state)

########NEW FILE########
__FILENAME__ = ExclusiveChoice
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import re
from SpiffWorkflow.Task import Task
from SpiffWorkflow.exceptions import WorkflowException
from .MultiChoice import MultiChoice

class ExclusiveChoice(MultiChoice):
    """
    This class represents an exclusive choice (an if condition) task
    where precisely one outgoing task is selected. If none of the
    given conditions matches, a default task is selected.
    It has one or more inputs and two or more outputs.
    """
    def __init__(self, parent, name, **kwargs):
        """
        Constructor.
        
        :type  parent: TaskSpec
        :param parent: A reference to the parent task spec.
        :type  name: str
        :param name: The name of the task spec.
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.TaskSpec}.
        """
        super(ExclusiveChoice, self).__init__(parent, name, **kwargs)
        self.default_task_spec = None

    def connect(self, task_spec):
        """
        Connects the task spec that is executed if no other condition
        matches.

        :type  task_spec: TaskSpec
        :param task_spec: The following task spec.
        """
        assert self.default_task_spec is None
        self.outputs.append(task_spec)
        self.default_task_spec = task_spec.name
        task_spec._connect_notify(self)

    def test(self):
        """
        Checks whether all required attributes are set. Throws an exception
        if an error was detected.
        """
        MultiChoice.test(self)
        if self.default_task_spec is None:
            raise WorkflowException(self, 'A default output is required.')

    def _predict_hook(self, my_task):
        # If the task's status is not predicted, we default to MAYBE
        # for all it's outputs except the default choice, which is
        # LIKELY.
        # Otherwise, copy my own state to the children.
        my_task._sync_children(self.outputs)
        spec = self._parent.get_task_spec_from_name(self.default_task_spec)
        my_task._set_likely_task(spec)

    def _on_complete_hook(self, my_task):
        # Find the first matching condition.
        output = self._parent.get_task_spec_from_name(self.default_task_spec)
        for condition, spec_name in self.cond_task_specs:
            if condition is None or condition._matches(my_task):
                output = self._parent.get_task_spec_from_name(spec_name)
                break

        my_task._sync_children([output], Task.FUTURE)
        for child in my_task.children:
            child.task_spec._update_state(child)

    def serialize(self, serializer):
        return serializer._serialize_exclusive_choice(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer._deserialize_exclusive_choice(wf_spec, s_state)

########NEW FILE########
__FILENAME__ = Execute
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
import subprocess

from SpiffWorkflow.Task import Task
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.specs.TaskSpec import TaskSpec


class Execute(TaskSpec):
    """
    This class executes an external process, goes into WAITING until the
    process is complete, and returns the results of the execution.

    Usage:

    task = Execute(spec, 'Ping', args=["ping", "-t", "1", "127.0.0.1"])
        ... when workflow complete
    print workflow.get_task('Ping').results
    """

    def __init__(self, parent, name, args=None, **kwargs):
        """
        Constructor.

        :type  parent: TaskSpec
        :param parent: A reference to the parent task spec.
        :type  name: str
        :param name: The name of the task spec.
        :type  args: list
        :param args: args to pass to process (first arg is the command).
        :type  kwargs: dict
        :param kwargs: kwargs to pass-through to TaskSpec initializer.
        """
        assert parent  is not None
        assert name    is not None
        TaskSpec.__init__(self, parent, name, **kwargs)
        self.args = args

    def _try_fire(self, my_task, force = False):
        """Returns False when successfully fired, True otherwise"""
        if (not hasattr(my_task, 'subprocess')) or my_task.subprocess is None:
            my_task.subprocess = subprocess.Popen(self.args,
                                               stderr=subprocess.STDOUT,
                                               stdout=subprocess.PIPE)

        if my_task.subprocess:
            my_task.subprocess.poll()
            if my_task.subprocess.returncode is None:
                # Still waiting
                return False
            else:
                results = my_task.subprocess.communicate()
                my_task.results = results
                return True
        return False

    def _update_state_hook(self, my_task):
        if not self._try_fire(my_task):
            my_task.state = Task.WAITING
            return
        super(Execute, self)._update_state_hook(my_task)

    def serialize(self, serializer):
        return serializer._serialize_execute(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        spec = serializer._deserialize_execute(wf_spec, s_state)
        return spec

########NEW FILE########
__FILENAME__ = Gate
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from SpiffWorkflow.Task import Task
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.specs.TaskSpec import TaskSpec

class Gate(TaskSpec):
    """
    This class implements a task that can only execute when another
    specified task is completed.
    If more than one input is connected, the task performs an implicit
    multi merge.
    If more than one output is connected, the task performs an implicit
    parallel split.
    """

    def __init__(self, parent, name, context, **kwargs):
        """
        Constructor.

        :type  parent: TaskSpec
        :param parent: A reference to the parent task spec.
        :type  name: str
        :param name: The name of the task spec.
        :type  context: str
        :param context: The name of the task that needs to complete before
                        this task can execute.
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.TaskSpec}.
        """
        assert parent  is not None
        assert name    is not None
        assert context is not None
        TaskSpec.__init__(self, parent, name, **kwargs)
        self.context = context

    def _update_state_hook(self, my_task):
        context_task = my_task.workflow.get_task_spec_from_name(self.context)
        root_task    = my_task.workflow.task_tree
        for task in root_task._find_any(context_task):
            if task.thread_id != my_task.thread_id:
                continue
            if not task._has_state(Task.COMPLETED):
                my_task._set_state(Task.WAITING)
                return
        super(Gate, self)._update_state_hook(my_task)

    def serialize(self, serializer):
        return serializer._serialize_gate(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer._deserialize_gate(wf_spec, s_state)

########NEW FILE########
__FILENAME__ = Join
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from SpiffWorkflow.Task import Task
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.specs.TaskSpec import TaskSpec
from SpiffWorkflow.operators import valueof


class Join(TaskSpec):
    """
    A task for synchronizing branches that were previously split using a
    conditional task, such as MultiChoice. It has two or more incoming
    branches and one or more outputs.

    Keep in mind that each Join spec may have multiple corresponding
    Task objects::

        - When using the MultiInstance task
        - When using the ThreadSplit task

    When using the MultiInstance pattern, Join works across all
    the resulting task instances. When using the ThreadSplit
    pattern, Join ignores instances from another thread.

    A Join task may enter the following states::

        - FUTURE, LIKELY, or MAYBE: These are the initial predicted states.

        - WAITING: This state is reached as soon as at least one of the
        predecessors has completed.

        - READY: All predecessors have completed. If multiple tasks within
        the thread reference the same Join (e.g. if MultiInstance is used),
        this state is only reached on one of the tasks; all other tasks go
        directly from WAITING to completed.

        - COMPLETED: All predecessors have completed, and
        L{Task.complete()} was called.

    The state may also change directly from WAITING to COMPLETED if the
    Trigger pattern is used.
    """

    def __init__(self,
                 parent,
                 name,
                 split_task=None,
                 threshold=None,
                 cancel=False,
                 **kwargs):
        """
        Constructor.

        :type  parent: L{SpiffWorkflow.specs.WorkflowSpec}
        :param parent: A reference to the parent (usually a workflow).
        :type  name: string
        :param name: A name for the task.
        :type  split_task: str or None
        :param split_task: The name of the task spec that was previously
                           used to split the branch. If this is None,
                           the most recent branch split is merged.
        :type  threshold: int or L{SpiffWorkflow.operators.Attrib}
        :param threshold: Specifies how many incoming branches need to
                          complete before the task triggers. When the limit
                          is reached, the task fires but still expects all
                          other branches to complete.
                          You may also pass an attribute, in which case
                          the value is resolved at runtime.
        :type  cancel: bool
        :param cancel: When True, any remaining incoming branches are
                       cancelled as soon as the discriminator is activated.
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.TaskSpec}.
        """
        super(Join, self).__init__(parent, name, **kwargs)
        self.split_task = split_task
        self.threshold = threshold
        self.cancel_remaining = cancel

    def _branch_is_complete(self, my_task):
        # Determine whether that branch is now completed by checking whether
        # it has any waiting items other than myself in it.
        skip = None
        for task in Task.Iterator(my_task, my_task.NOT_FINISHED_MASK):
            # If the current task is a child of myself, ignore it.
            if skip is not None and task._is_descendant_of(skip):
                continue
            if task.task_spec == self:
                skip = task
                continue
            return False
        return True

    def _branch_may_merge_at(self, task):
        for child in task:
            # Ignore tasks that were created by a trigger.
            if child.triggered:
                continue
            # Merge found.
            if child.task_spec == self:
                return True
            # If the task is predicted with less outputs than he has
            # children, that means the prediction may be incomplete (for
            # example, because a prediction is not yet possible at this time).
            if not child._is_definite() \
                and len(child.task_spec.outputs) > len(child.children):
                return True
        return False

    def _try_fire_unstructured(self, my_task, force=False):
        # The default threshold is the number of inputs.
        threshold = valueof(my_task, self.threshold)
        if threshold is None:
            threshold = len(self.inputs)

        # Look at the tree to find all places where this task is used.
        tasks = []
        for input in self.inputs:
            for task in my_task.workflow.task_tree:
                if task.thread_id != my_task.thread_id:
                    continue
                if task.task_spec != input:
                    continue
                tasks.append(task)

        # Look up which tasks have already completed.
        waiting_tasks = []
        completed = 0
        for task in tasks:
            if task.parent is None or task._has_state(Task.COMPLETED):
                completed += 1
            else:
                waiting_tasks.append(task)

        # If the threshold was reached, get ready to fire.
        return force or completed >= threshold, waiting_tasks

    def _try_fire_structured(self, my_task, force=False):
        # Retrieve a list of all activated tasks from the associated
        # task that did the conditional parallel split.
        split_task = my_task._find_ancestor_from_name(self.split_task)
        if split_task is None:
            msg = 'Join with %s, which was not reached' % self.split_task
            raise WorkflowException(self, msg)
        tasks = split_task.task_spec._get_activated_tasks(split_task, my_task)

        # The default threshold is the number of branches that were started.
        threshold = valueof(my_task, self.threshold)
        if threshold is None:
            threshold = len(tasks)

        # Look up which tasks have already completed.
        waiting_tasks = []
        completed     = 0
        for task in tasks:
            # Refresh path prediction.
            task.task_spec._predict(task)

            if not self._branch_may_merge_at(task):
                completed += 1
            elif self._branch_is_complete(task):
                completed += 1
            else:
                waiting_tasks.append(task)

        # If the threshold was reached, get ready to fire.
        return force or completed >= threshold, waiting_tasks

    def _try_fire(self, my_task, force=False):
        """
        Checks whether the preconditions for going to READY state are met.
        Returns True if the threshold was reached, False otherwise.
        Also returns the list of tasks that yet need to be completed.
        """
        # If the threshold was already reached, there is nothing else to do.
        if my_task._has_state(Task.COMPLETED):
            return True, None
        if my_task._has_state(Task.READY):
            return True, None

        # Check whether we may fire.
        if self.split_task is None:
            return self._try_fire_unstructured(my_task, force)
        return self._try_fire_structured(my_task, force)

    def _update_state_hook(self, my_task):
        # Check whether enough incoming branches have completed.
        may_fire, waiting_tasks = self._try_fire(my_task)
        if not may_fire:
            my_task._set_state(Task.WAITING)
            return

        # If this is a cancelling join, cancel all incoming branches,
        # except for the one that just completed.
        if self.cancel_remaining:
            for task in waiting_tasks:
                task.cancel()

        # We do NOT set the task state to COMPLETED, because in
        # case all other incoming tasks get cancelled (or never reach
        # the Join for other reasons, such as reaching a stub branch),
        # we need to revisit it.
        my_task._ready()

        # Update the state of our child objects.
        self._do_join(my_task)

    def _do_join(self, my_task):
        # One Join spec may have multiple corresponding Task objects::
        #
        #     - Due to the MultiInstance pattern.
        #     - Due to the ThreadSplit pattern.
        #
        # When using the MultiInstance pattern, we want to join across
        # the resulting task instances. When using the ThreadSplit
        # pattern, we only join within the same thread. (Both patterns
        # may also be mixed.)
        #
        # We are looking for all task instances that must be joined.
        # We limit our search by starting at the split point.
        if self.split_task:
            split_task = my_task.workflow.get_task_spec_from_name(self.split_task)
            split_task = my_task._find_ancestor(split_task)
        else:
            split_task = my_task.workflow.task_tree

        # Identify all corresponding task instances within the thread.
        # Also remember which of those instances was most recently changed,
        # because we are making this one the instance that will
        # continue the thread of control. In other words, we will continue
        # to build the task tree underneath the most recently changed task.
        last_changed = None
        thread_tasks = []
        for task in split_task._find_any(self):
            # Ignore tasks from other threads.
            if task.thread_id != my_task.thread_id:
                continue
            # Ignore my outgoing branches.
            if self.split_task and task._is_descendant_of(my_task):
                continue

            # We have found a matching instance.
            thread_tasks.append(task)

            # Check whether the state of the instance was recently
            # changed.
            changed = task.parent.last_state_change
            if last_changed is None \
              or changed > last_changed.parent.last_state_change:
                last_changed = task

        # Mark the identified task instances as COMPLETED. The exception
        # is the most recently changed task, for which we assume READY.
        # By setting the state to READY only, we allow for calling
        # L{Task.complete()}, which leads to the task tree being
        # (re)built underneath the node.
        for task in thread_tasks:
            if task == last_changed:
                self.entered_event.emit(my_task.workflow, my_task)
                task._ready()
            else:
                task.state = Task.COMPLETED
                task._drop_children()

    def _on_trigger(self, my_task):
        """
        May be called to fire the Join before the incoming branches are
        completed.
        """
        for task in my_task.workflow.task_tree._find_any(self):
            if task.thread_id != my_task.thread_id:
                continue
            self._do_join(task)

    def serialize(self, serializer):
        return serializer._serialize_join(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer._deserialize_join(wf_spec, s_state)

########NEW FILE########
__FILENAME__ = Merge
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import logging

from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.specs.Join import Join
from SpiffWorkflow.util import merge_dictionary

LOG = logging.getLogger(__name__)


class Merge(Join):
    """Same as Join, but merges all input data instead of just parents'

    Note: data fields that have conflicting names will be overwritten"""
    def _do_join(self, my_task):
        # Merge all inputs (in order)
        for input_spec in self.inputs:
            tasks = [task for task in my_task.workflow.task_tree
                    if task.task_spec is input_spec]
            for task in tasks:
                LOG.debug("Merging %s (%s) into %s" % (task.get_name(),
                        task.get_state_name(), self.name),
                        extra=dict(data=task.data))
                _log_overwrites(my_task.data, task.data)
                merge_dictionary(my_task.data, task.data)
        return super(Merge, self)._do_join(my_task)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer._deserialize_merge(wf_spec, s_state)


def _log_overwrites(dst, src):
    # Temporary: We log when we overwrite during debugging
    for k, v in src.items():
        if k in dst:
            if isinstance(v, dict) and isinstance(dst[k], dict):
                log_overwrites(v, dst[k])
            else:
                if v != dst[k]:
                    LOG.warning("Overwriting %s=%s with %s" % (k, dst[k], v))

########NEW FILE########
__FILENAME__ = MultiChoice
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import re
from SpiffWorkflow.Task import Task
from SpiffWorkflow.exceptions import WorkflowException
from .TaskSpec import TaskSpec

class MultiChoice(TaskSpec):
    """
    This class represents an if condition where multiple conditions may match
    at the same time, creating multiple outgoing branches.
    This task has one or more inputs, and one or more incoming branches.
    This task has one or more outputs.
    """

    def __init__(self, parent, name, **kwargs):
        """
        Constructor.
        
        :type  parent: TaskSpec
        :param parent: A reference to the parent task spec.
        :type  name: str
        :param name: The name of the task spec.
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.TaskSpec}.
        """
        super(MultiChoice, self).__init__(parent, name, **kwargs)
        self.cond_task_specs = []
        self.choice          = None

    def connect(self, task_spec):
        """
        Convenience wrapper around connect_if() where condition is set to None.
        """
        return self.connect_if(None, task_spec)

    def connect_if(self, condition, task_spec):
        """
        Connects a taskspec that is executed if the condition DOES match.
        
        condition -- a condition (Condition)
        taskspec -- the conditional task spec
        """
        assert task_spec is not None
        self.outputs.append(task_spec)
        self.cond_task_specs.append((condition, task_spec.name))
        task_spec._connect_notify(self)

    def test(self):
        """
        Checks whether all required attributes are set. Throws an exception
        if an error was detected.
        """
        TaskSpec.test(self)
        if len(self.cond_task_specs) < 1:
            raise WorkflowException(self, 'At least one output required.')
        for condition, name in self.cond_task_specs:
            if name is None:
                raise WorkflowException(self, 'Condition with no task spec.')
            task_spec = self._parent.get_task_spec_from_name(name)
            if task_spec is None:
                msg = 'Condition leads to non-existent task ' + repr(name)
                raise WorkflowException(self, msg)
            if condition is None:
                continue

    def _on_trigger(self, my_task, choice):
        """
        Lets a caller narrow down the choice by using a Choose trigger.
        """
        self.choice = choice
        # The caller needs to make sure that predict() is called.

    def _predict_hook(self, my_task):
        if self.choice:
            outputs = [self._parent.get_task_spec_from_name(o)
                       for o in self.choice]
        else:
            outputs = self.outputs

        # Default to MAYBE for all conditional outputs, default to LIKELY
        # for unconditional ones. We can not default to FUTURE, because
        # a call to trigger() may override the unconditional paths.
        my_task._sync_children(outputs)
        if not my_task._is_definite():
            best_state = my_task.state
        else:
            best_state = Task.LIKELY

        # Collect a list of all unconditional outputs.
        outputs = []
        for condition, output in self.cond_task_specs:
            if condition is None:
                outputs.append(self._parent.get_task_spec_from_name(output))

        for child in my_task.children:
            if child._is_definite():
                continue
            if child.task_spec in outputs:
                child._set_state(best_state)

    def _on_complete_hook(self, my_task):
        """
        Runs the task. Should not be called directly.
        Returns True if completed, False otherwise.
        """
        # Find all matching conditions.
        outputs = []
        for condition, output in self.cond_task_specs:
            if self.choice is not None and output not in self.choice:
                continue
            if condition is None:
                outputs.append(self._parent.get_task_spec_from_name(output))
                continue
            if not condition._matches(my_task):
                continue
            outputs.append(self._parent.get_task_spec_from_name(output))

        my_task._sync_children(outputs, Task.FUTURE)
        for child in my_task.children:
            child.task_spec._update_state(child)

    def serialize(self, serializer):
        return serializer._serialize_multi_choice(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer._deserialize_multi_choice(wf_spec, s_state)

########NEW FILE########
__FILENAME__ = MultiInstance
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from SpiffWorkflow.Task import Task
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.specs.TaskSpec import TaskSpec
from SpiffWorkflow.operators import valueof

class MultiInstance(TaskSpec):
    """
    When executed, this task performs a split on the current task.
    The number of outgoing tasks depends on the runtime value of a
    specified data field.
    If more than one input is connected, the task performs an implicit
    multi merge.

    This task has one or more inputs and may have any number of outputs.
    """

    def __init__(self, parent, name, times = None, **kwargs):
        """
        Constructor.
        
        :type  parent: TaskSpec
        :param parent: A reference to the parent task spec.
        :type  name: str
        :param name: The name of the task spec.
        :type  times: int
        :param times: The number of tasks to create.
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.TaskSpec}.
        """
        TaskSpec.__init__(self, parent, name, **kwargs)
        self.times = times

    def _find_my_task(self, task):
        for thetask in task.workflow.task_tree:
            if thetask.thread_id != task.thread_id:
                continue
            if thetask.task_spec == self:
                return thetask
        return None

    def _on_trigger(self, task_spec):
        """
        May be called after execute() was already completed to create an
        additional outbound task.
        """
        # Find a Task for this TaskSpec.
        my_task = self._find_my_task(task_spec)
        if my_task._has_state(Task.COMPLETED):
            state = Task.READY
        else:
            state = Task.FUTURE
        for output in self.outputs:
            new_task = my_task._add_child(output, state)
            new_task.triggered = True
            output._predict(new_task)

    def _get_predicted_outputs(self, my_task):
        split_n = my_task._get_internal_data('splits', 1)

        # Predict the outputs.
        outputs = []
        for i in range(split_n):
            outputs += self.outputs
        return outputs

    def _predict_hook(self, my_task):
        split_n = valueof(my_task, self.times)
        if split_n is None:
            return
        my_task._set_internal_data(splits = split_n)

        # Create the outgoing tasks.
        outputs = []
        for i in range(split_n):
            outputs += self.outputs
        if my_task._is_definite():
            my_task._sync_children(outputs, Task.FUTURE)
        else:
            my_task._sync_children(outputs, Task.LIKELY)

    def _on_complete_hook(self, my_task):
        outputs = self._get_predicted_outputs(my_task)
        my_task._sync_children(outputs, Task.FUTURE)
        for child in my_task.children:
            child.task_spec._update_state(child)

    def serialize(self, serializer):
        return serializer._serialize_multi_instance(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer._deserialize_multi_instance(wf_spec, s_state)

########NEW FILE########
__FILENAME__ = ReleaseMutex
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from SpiffWorkflow import Task
from SpiffWorkflow.exceptions import WorkflowException
from .TaskSpec import TaskSpec

class ReleaseMutex(TaskSpec):
    """
    This class implements a task that releases a mutex (lock), protecting
    a section of the workflow from being accessed by other sections.
    If more than one input is connected, the task performs an implicit
    multi merge.
    If more than one output is connected, the task performs an implicit
    parallel split.
    """

    def __init__(self, parent, name, mutex, **kwargs):
        """
        Constructor.

        :type  parent: TaskSpec
        :param parent: A reference to the parent task spec.
        :type  name: str
        :param name: The name of the task spec.
        :type  mutex: str
        :param mutex: The name of the mutex that should be released.
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.TaskSpec}.
        """
        assert mutex is not None
        TaskSpec.__init__(self, parent, name, **kwargs)
        self.mutex = mutex

    def _on_complete_hook(self, my_task):
        mutex = my_task.workflow._get_mutex(self.mutex)
        mutex.unlock()
        TaskSpec._on_complete_hook(self, my_task)

    def serialize(self, serializer):
        return serializer._serialize_release_mutex(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer._deserialize_release_mutex(wf_spec, s_state)

########NEW FILE########
__FILENAME__ = Simple
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from SpiffWorkflow.specs.TaskSpec import TaskSpec


class Simple(TaskSpec):
    """
    This class implements a task with one or more inputs and
    any number of outputs.
    If more than one input is connected, the task performs an implicit
    multi merge.
    If more than one output is connected, the task performs an implicit
    parallel split.
    """
    def serialize(self, serializer):
        return serializer._serialize_simple(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer._deserialize_simple(wf_spec, s_state)

########NEW FILE########
__FILENAME__ = StartTask
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.specs.TaskSpec import TaskSpec


class StartTask(TaskSpec):
    """
    This class implements the task the is placed at the beginning
    of each workflow. The task has no inputs and at least one output.
    If more than one output is connected, the task does an implicit
    parallel split.
    """

    def __init__(self, parent, **kwargs):
        """
        Constructor. The name of this task is *always* 'Start'.

        :type  parent: TaskSpec
        :param parent: A reference to the parent task spec.
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.TaskSpec}.
        """
        TaskSpec.__init__(self, parent, 'Start', **kwargs)

    def _connect_notify(self, task_spec):
        """
        Called by the previous task to let us know that it exists.
        """
        raise WorkflowException(self, 'StartTask can not have any inputs.')

    def test(self):
        """
        Checks whether all required attributes are set. Throws an exception
        if an error was detected.
        """
        if len(self.inputs) != 0:
            raise WorkflowException(self, 'StartTask with an input.')
        elif len(self.outputs) < 1:
            raise WorkflowException(self, 'No output task connected.')

    def serialize(self, serializer):
        return serializer._serialize_start_task(self)

    @classmethod
    def deserialize(cls, serializer, wf_spec, s_state):
        return serializer._deserialize_start_task(wf_spec, s_state)

########NEW FILE########
__FILENAME__ = SubWorkflow
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import os
from SpiffWorkflow.Task import Task
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.operators import valueof
from SpiffWorkflow.specs.TaskSpec import TaskSpec
import SpiffWorkflow

class SubWorkflow(TaskSpec):
    """
    A SubWorkflow is a task that wraps a WorkflowSpec, such that you can
    re-use it in multiple places as if it were a task.
    If more than one input is connected, the task performs an implicit
    multi merge.
    If more than one output is connected, the task performs an implicit
    parallel split.
    """

    def __init__(self,
                 parent,
                 name,
                 file,
                 in_assign = None,
                 out_assign = None,
                 **kwargs):
        """
        Constructor.

        :type  parent: TaskSpec
        :param parent: A reference to the parent task spec.
        :type  name: str
        :param name: The name of the task spec.
        :type  file: str
        :param file: The name of a file containing a workflow.
        :type  in_assign: list(str)
        :param in_assign: The names of data fields to carry over.
        :type  out_assign: list(str)
        :param out_assign: The names of data fields to carry back.
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.TaskSpec}.
        """
        assert parent is not None
        assert name is not None
        super(SubWorkflow, self).__init__(parent, name, **kwargs)
        self.file       = None
        self.in_assign  = in_assign is not None and in_assign or []
        self.out_assign = out_assign is not None and out_assign or []
        if file is not None:
            dirname   = os.path.dirname(parent.file)
            self.file = os.path.join(dirname, file)

    def test(self):
        TaskSpec.test(self)
        if self.file is not None and not os.path.exists(self.file):
            raise WorkflowException(self, 'File does not exist: %s' % self.file)

    def _predict_hook(self, my_task):
        outputs = [task.task_spec for task in my_task.children]
        for output in self.outputs:
            if output not in outputs:
                outputs.insert(0, output)
        if my_task._is_definite():
            my_task._sync_children(outputs, Task.FUTURE)
        else:
            my_task._sync_children(outputs, my_task.state)

    def _create_subworkflow(self, my_task):
        from SpiffWorkflow.storage import XmlSerializer
        from SpiffWorkflow.specs import WorkflowSpec
        file           = valueof(my_task, self.file)
        serializer     = XmlSerializer()
        xml            = open(file).read()
        wf_spec        = WorkflowSpec.deserialize(serializer, xml, filename = file)
        outer_workflow = my_task.workflow.outer_workflow
        return SpiffWorkflow.Workflow(wf_spec, parent = outer_workflow)

    def _on_ready_before_hook(self, my_task):
        subworkflow    = self._create_subworkflow(my_task)
        subworkflow.completed_event.connect(self._on_subworkflow_completed, my_task)

        # Integrate the tree of the subworkflow into the tree of this workflow.
        my_task._sync_children(self.outputs, Task.FUTURE)
        for child in my_task.children:
            child.task_spec._update_state(child)
            child._inherit_data()
        for child in subworkflow.task_tree.children:
            my_task.children.insert(0, child)
            child.parent = my_task

        my_task._set_internal_data(subworkflow = subworkflow)

    def _on_ready_hook(self, my_task):
        # Assign variables, if so requested.
        subworkflow = my_task._get_internal_data('subworkflow')
        for child in subworkflow.task_tree.children:
            for assignment in self.in_assign:
                assignment.assign(my_task, child)

        self._predict(my_task)
        for child in subworkflow.task_tree.children:
            child.task_spec._update_state(child)

    def _on_subworkflow_completed(self, subworkflow, my_task):
        # Assign variables, if so requested.
        for child in my_task.children:
            if child.task_spec in self.outputs:
                for assignment in self.out_assign:
                    assignment.assign(subworkflow, child)

                # Alright, abusing that hook is just evil but it works.
                child.task_spec._update_state_hook(child)

    def _on_complete_hook(self, my_task):
        for child in my_task.children:
            if child.task_spec in self.outputs:
                continue
            child.task_spec._update_state(child)

    def serialize(self, serializer):
        return serializer._serialize_sub_workflow(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer._deserialize_sub_workflow(wf_spec, s_state)

########NEW FILE########
__FILENAME__ = TaskSpec
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import logging

from SpiffWorkflow.util.event import Event
from SpiffWorkflow.Task import Task
from SpiffWorkflow.exceptions import WorkflowException


LOG = logging.getLogger(__name__)


class TaskSpec(object):
    """
    This class implements an abstract base type for all tasks.

    Tasks provide the following signals:
      - **entered**: called when the state changes to READY or WAITING, at a
        time where spec data is not yet initialized.
      - **reached**: called when the state changes to READY or WAITING, at a
        time where spec data is already initialized using data_assign
        and pre-assign.
      - **ready**: called when the state changes to READY, at a time where
        spec data is already initialized using data_assign and
        pre-assign.
      - **completed**: called when the state changes to COMPLETED, at a time
        before the post-assign variables are assigned.
      - **cancelled**: called when the state changes to CANCELLED, at a time
        before the post-assign variables are assigned.
      - **finished**: called when the state changes to COMPLETED or CANCELLED,
        at the last possible time after the post-assign variables are
        assigned and mutexes are released.

    Event sequence is: entered -> reached -> ready -> completed -> finished
        (cancelled may happen at any time)

    The only events where implementing something other than state tracking
    may be useful are the following:
      - Reached: You could mess with the pre-assign variables here, for
        example. Other then that, there is probably no need in a real
        application.
      - Ready: This is where a task could implement custom code, for example
        for triggering an external system. This is also the only event where a
        return value has a meaning (returning non-True will mean that the
        post-assign procedure is skipped.)
    """

    def __init__(self, parent, name, **kwargs):
        """
        Constructor.

        The difference between the assignment of a data value using
        the data argument versus pre_assign and post_assign is that
        changes made using data are task-local, i.e. they are
        not visible to other tasks.
        Similarly, "defines" are spec data fields that, once defined, can
        no longer be modified.

        :type  parent: L{SpiffWorkflow.specs.WorkflowSpec}
        :param parent: A reference to the parent (usually a workflow).
        :type  name: string
        :param name: A name for the task.
        :type  lock: list(str)
        :param lock: A list of mutex names. The mutex is acquired
                     on entry of execute() and released on leave of
                     execute().
        :type  data: dict((str, object))
        :param data: name/value pairs
        :type  defines: dict((str, object))
        :param defines: name/value pairs
        :type  pre_assign: list((str, object))
        :param pre_assign: a list of name/value pairs
        :type  post_assign: list((str, object))
        :param post_assign: a list of name/value pairs
        """
        assert parent is not None
        assert name   is not None
        self._parent     = parent
        self.id          = None
        self.name        = str(name)
        self.description = kwargs.get('description', '')
        self.inputs      = []
        self.outputs     = []
        self.manual      = False
        self.internal    = False  # Only for easing debugging.
        self.data        = kwargs.get('data',        {})
        self.defines     = kwargs.get('defines',     {})
        self.pre_assign  = kwargs.get('pre_assign',  [])
        self.post_assign = kwargs.get('post_assign', [])
        self.locks       = kwargs.get('lock',        [])
        self.lookahead   = 2  # Maximum number of MAYBE predictions.

        # Events.
        self.entered_event   = Event()
        self.reached_event   = Event()
        self.ready_event     = Event()
        self.completed_event = Event()
        self.cancelled_event = Event()
        self.finished_event  = Event()

        self._parent._add_notify(self)
        self.data.update(self.defines)
        assert self.id is not None

    def _connect_notify(self, taskspec):
        """
        Called by the previous task to let us know that it exists.

        :type  taskspec: TaskSpec
        :param taskspec: The task by which this method is executed.
        """
        self.inputs.append(taskspec)

    def ancestors(self):
        """Returns list of ancestor task specs based on inputs"""
        results = []

        def recursive_find_ancestors(task, stack):
            for input in task.inputs:
                if input not in stack:
                    stack.append(input)
                    recursive_find_ancestors(input, stack)
        recursive_find_ancestors(self, results)

        return results

    def _get_activated_tasks(self, my_task, destination):
        """
        Returns the list of tasks that were activated in the previous
        call of execute(). Only returns tasks that point towards the
        destination task, i.e. those which have destination as a
        descendant.

        :type  my_task: Task
        :param my_task: The associated task in the task tree.
        :type  destination: Task
        :param destination: The destination task.
        """
        return my_task.children

    def _get_activated_threads(self, my_task):
        """
        Returns the list of threads that were activated in the previous
        call of execute().

        :type  my_task: Task
        :param my_task: The associated task in the task tree.
        """
        return my_task.children

    def set_data(self, **kwargs):
        """
        Defines the given data field(s) using the given name/value pairs.
        """
        for key in kwargs:
            if key in self.defines:
                msg = "Spec data %s can not be modified" % key
                raise WorkflowException(self, msg)
        self.data.update(kwargs)

    def get_data(self, name, default=None):
        """
        Returns the value of the data field with the given name, or the
        given default value if the data was not defined.

        :type  name: string
        :param name: The name of the data field.
        :type  default: string
        :param default: Returned if the data field is not defined.
        """
        return self.data.get(name, default)

    def connect(self, taskspec):
        """
        Connect the *following* task to this one. In other words, the
        given task is added as an output task.

        :type  taskspec: TaskSpec
        :param taskspec: The new output task.
        """
        self.outputs.append(taskspec)
        taskspec._connect_notify(self)

    def follow(self, taskspec):
        """
        Make this task follow the provided one. In other words, this task is
        added to the given task outputs.

        This is an alias to connect, just easier to understand when reading
        code - ex: my_task.follow(the_other_task)
        Adding it after being confused by .connect one times too many!

        :type  taskspec: TaskSpec
        :param taskspec: The task to follow.
        """
        taskspec.connect(self)

    def test(self):
        """
        Checks whether all required attributes are set. Throws an exception
        if an error was detected.
        """
        if self.id is None:
            raise WorkflowException(self, 'TaskSpec is not yet instanciated.')
        if len(self.inputs) < 1:
            raise WorkflowException(self, 'No input task connected.')

    def _predict(self, my_task, seen=None, looked_ahead=0):
        """
        Updates the branch such that all possible future routes are added.

        Should NOT be overwritten! Instead, overwrite _predict_hook().

        :type  my_task: Task
        :param my_task: The associated task in the task tree.
        :type  seen: list[taskspec]
        :param seen: A list of already visited tasks.
        :type  looked_ahead: integer
        :param looked_ahead: The depth of the predicted path so far.
        """
        if my_task._is_finished():
            return
        if seen is None:
            seen = []
        elif self in seen:
            return
        if not my_task._is_finished():
            self._predict_hook(my_task)
        if not my_task._is_definite():
            if looked_ahead + 1 >= self.lookahead:
                return
            seen.append(self)
        for child in my_task.children:
            child.task_spec._predict(child, seen[:], looked_ahead + 1)

    def _predict_hook(self, my_task):
        # If the task's status is not predicted, we default to FUTURE
        # for all it's outputs.
        # Otherwise, copy my own state to the children.
        if my_task._is_definite():
            best_state = Task.FUTURE
        else:
            best_state = my_task.state

        my_task._sync_children(self.outputs, best_state)
        for child in my_task.children:
            if not child._is_definite():
                child._set_state(best_state)

    def _update_state(self, my_task):
        """
        Called whenever any event happens that may affect the
        state of this task in the workflow. For example, if a predecessor
        completes it makes sure to call this method so we can react.
        """
        my_task._inherit_data()
        self._update_state_hook(my_task)

    def _update_state_hook(self, my_task):
        """
        Typically this method should perform the following actions::

            - Update the state of the corresponding task.
            - Update the predictions for its successors.

        Returning non-False will cause the task to go into READY.
        Returning any other value will cause no action.
        """
        if my_task._is_predicted():
            self._predict(my_task)
        LOG.debug("'%s'._update_state_hook says parent (%s, state=%s) "
                "is_finished=%s" % (self.name, my_task.parent.get_name(),
                my_task.parent.get_state_name(),
                my_task.parent._is_finished()))
        if not my_task.parent._is_finished():
            return
        self.entered_event.emit(my_task.workflow, my_task)
        my_task._ready()

    def _on_ready(self, my_task):
        """
        Return True on success, False otherwise.

        :type  my_task: Task
        :param my_task: The associated task in the task tree.
        """
        assert my_task is not None
        self.test()

        # Acquire locks, if any.
        for lock in self.locks:
            mutex = my_task.workflow._get_mutex(lock)
            if not mutex.testandset():
                return

        # Assign variables, if so requested.
        for assignment in self.pre_assign:
            assignment.assign(my_task, my_task)

        # Run task-specific code.
        self._on_ready_before_hook(my_task)
        self.reached_event.emit(my_task.workflow, my_task)
        self._on_ready_hook(my_task)

        # Run user code, if any.
        if self.ready_event.emit(my_task.workflow, my_task):
            # Assign variables, if so requested.
            for assignment in self.post_assign:
                assignment.assign(my_task, my_task)

        # Release locks, if any.
        for lock in self.locks:
            mutex = my_task.workflow._get_mutex(lock)
            mutex.unlock()

        self.finished_event.emit(my_task.workflow, my_task)

    def _on_ready_before_hook(self, my_task):
        """
        A hook into _on_ready() that does the task specific work.

        :type  my_task: Task
        :param my_task: The associated task in the task tree.
        """
        pass

    def _on_ready_hook(self, my_task):
        """
        A hook into _on_ready() that does the task specific work.

        :type  my_task: Task
        :param my_task: The associated task in the task tree.
        """
        pass

    def _on_cancel(self, my_task):
        """
        May be called by another task to cancel the operation before it was
        completed.

        :type  my_task: Task
        :param my_task: The associated task in the task tree.
        """
        self.cancelled_event.emit(my_task.workflow, my_task)

    def _on_trigger(self, my_task):
        """
        May be called by another task to trigger a task-specific
        event.

        :type  my_task: Task
        :param my_task: The associated task in the task tree.
        :rtype:  boolean
        :returns: True on success, False otherwise.
        """
        raise NotImplementedError("Trigger not supported by this task.")

    def _on_complete(self, my_task):
        """
        Return True on success, False otherwise. Should not be overwritten,
        overwrite _on_complete_hook() instead.

        :type  my_task: Task
        :param my_task: The associated task in the task tree.
        :rtype:  boolean
        :returns: True on success, False otherwise.
        """
        assert my_task is not None

        if my_task.workflow.debug:
            print("Executing task:", my_task.get_name())

        self._on_complete_hook(my_task)

        # Notify the Workflow.
        my_task.workflow._task_completed_notify(my_task)

        if my_task.workflow.debug:
            if hasattr(my_task.workflow, "outer_workflow"):
                my_task.workflow.outer_workflow.task_tree.dump()

        self.completed_event.emit(my_task.workflow, my_task)
        return True

    def _on_complete_hook(self, my_task):
        """
        A hook into _on_complete() that does the task specific work.

        :type  my_task: Task
        :param my_task: The associated task in the task tree.
        :rtype:  bool
        :returns: True on success, False otherwise.
        """
        # If we have more than one output, implicitly split.
        for child in my_task.children:
            child.task_spec._update_state(child)

    def serialize(self, serializer, **kwargs):
        """
        Serializes the instance using the provided serializer.

        .. note::

            The events of a TaskSpec are not serialized. If you
            use them, make sure to re-connect them once the spec is
            deserialized.

        :type  serializer: L{SpiffWorkflow.storage.Serializer}
        :param serializer: The serializer to use.
        :type  kwargs: dict
        :param kwargs: Passed to the serializer.
        :rtype:  object
        :returns: The serialized object.
        """
        return serializer._serialize_task_spec(self, **kwargs)

    @classmethod
    def deserialize(cls, serializer, wf_spec, s_state, **kwargs):
        """
        Deserializes the instance using the provided serializer.

        .. note::

            The events of a TaskSpec are not serialized. If you
            use them, make sure to re-connect them once the spec is
            deserialized.

        :type  serializer: L{SpiffWorkflow.storage.Serializer}
        :param serializer: The serializer to use.
        :type  wf_spec: L{SpiffWorkflow.spec.WorkflowSpec}
        :param wf_spec: An instance of the WorkflowSpec.
        :type  s_state: object
        :param s_state: The serialized task specification object.
        :type  kwargs: dict
        :param kwargs: Passed to the serializer.
        :rtype:  TaskSpec
        :returns: The task specification instance.
        """
        instance = cls(wf_spec, s_state['name'])
        return serializer._deserialize_task_spec(wf_spec,
                                                 s_state,
                                                 instance,
                                                 **kwargs)

########NEW FILE########
__FILENAME__ = ThreadMerge
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from SpiffWorkflow.Task import Task
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.specs.TaskSpec import TaskSpec
from SpiffWorkflow.operators import valueof
from SpiffWorkflow.specs import Join

class ThreadMerge(Join):
    """
    This class represents a task for synchronizing branches that were
    previously split using a a ThreadSplit.
    It has two or more incoming branches and one or more outputs.
    """

    def __init__(self,
                 parent,
                 name,
                 split_task,
                 **kwargs):
        """
        Constructor.
        
        :type  parent: L{SpiffWorkflow.specs.WorkflowSpec}
        :param parent: A reference to the parent (usually a workflow).
        :type  name: string
        :param name: A name for the task.
        :type  split_task: str
        :param split_task: The name of the task spec that was previously
                           used to split the branch.
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.Join}.
        """
        assert split_task is not None
        Join.__init__(self, parent, name, split_task, **kwargs)

    def _try_fire(self, my_task):
        # If the threshold was already reached, there is nothing else to do.
        if my_task._has_state(Task.COMPLETED):
            return False
        if my_task._has_state(Task.READY):
            return True

        # Retrieve a list of all activated tasks from the associated
        # task that did the conditional parallel split.
        split_task = my_task._find_ancestor_from_name(self.split_task)
        if split_task is None:
            msg = 'Join with %s, which was not reached' % self.split_task
            raise WorkflowException(self, msg)
        tasks = split_task.task_spec._get_activated_threads(split_task)

        # The default threshold is the number of threads that were started.
        threshold = valueof(my_task, self.threshold)
        if threshold is None:
            threshold = len(tasks)

        # Look up which tasks have already completed.
        waiting_tasks = []
        completed     = 0
        for task in tasks:
            # Refresh path prediction.
            task.task_spec._predict(task)

            if self._branch_is_complete(task):
                completed += 1
            else:
                waiting_tasks.append(task)

        # If the threshold was reached, get ready to fire.
        if completed >= threshold:
            # If this is a cancelling join, cancel all incoming branches,
            # except for the one that just completed.
            if self.cancel_remaining:
                for task in waiting_tasks:
                    task.cancel()
            return True

        # We do NOT set the task state to COMPLETED, because in
        # case all other incoming tasks get cancelled (or never reach
        # the ThreadMerge for other reasons, such as reaching a stub branch),
        # we need to revisit it.
        return False

    def _update_state_hook(self, my_task):
        if not self._try_fire(my_task):
            my_task._set_state(Task.WAITING)
            return

        split_task_spec = my_task.workflow.get_task_spec_from_name(self.split_task)
        split_task      = my_task._find_ancestor(split_task_spec)

        # Find the inbound task that was completed last.
        last_changed = None
        tasks        = []
        for task in split_task._find_any(self):
            if self.split_task and task._is_descendant_of(my_task):
                continue
            changed = task.parent.last_state_change
            if last_changed is None \
              or changed > last_changed.parent.last_state_change:
                last_changed = task
            tasks.append(task)

        # Mark all tasks in this thread that reference this task as 
        # completed, except for the first one, which should be READY.
        for task in tasks:
            if task == last_changed:
                self.entered_event.emit(my_task.workflow, my_task)
                task._ready()
            else:
                task.state = Task.COMPLETED
                task._drop_children()

    def serialize(self, serializer):
        return serializer._serialize_thread_merge(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer._deserialize_thread_merge(wf_spec, s_state)

########NEW FILE########
__FILENAME__ = ThreadSplit
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from SpiffWorkflow.Task import Task
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.specs.TaskSpec import TaskSpec
from SpiffWorkflow.specs.ThreadStart import ThreadStart

class ThreadSplit(TaskSpec):
    """
    When executed, this task performs a split on the current my_task.
    The number of outgoing my_tasks depends on the runtime value of a
    specified data field.
    If more than one input is connected, the task performs an implicit
    multi merge.

    This task has one or more inputs and may have any number of outputs.
    """

    def __init__(self,
                 parent,
                 name,
                 times = None,
                 times_attribute = None,
                 suppress_threadstart_creation = False,
                 **kwargs):
        """
        Constructor.
        
        :type  parent: L{SpiffWorkflow.specs.WorkflowSpec}
        :param parent: A reference to the parent (usually a workflow).
        :type  name: string
        :param name: A name for the task.
        :type  times: int or None
        :param times: The number of tasks to create.
        :type  times_attribute: str or None
        :param times_attribute: The name of a data field that specifies
                                the number of outgoing tasks.
        :type  suppress_threadstart_creation: bool
        :param suppress_threadstart_creation: Don't create a ThreadStart, because
                                              the deserializer is about to.
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.TaskSpec}.
        """
        if not times_attribute and not times:
            raise ValueError('require times or times_attribute argument')
        TaskSpec.__init__(self, parent, name, **kwargs)
        self.times_attribute = times_attribute
        self.times           = times
        if not suppress_threadstart_creation:
            self.thread_starter  = ThreadStart(parent, **kwargs)
            self.outputs.append(self.thread_starter)
            self.thread_starter._connect_notify(self)
        else:
            self.thread_starter = None

    def connect(self, task_spec):
        """
        Connect the *following* task to this one. In other words, the
        given task is added as an output task.

        task -- the task to connect to.
        """
        self.thread_starter.outputs.append(task_spec)
        task_spec._connect_notify(self.thread_starter)

    def _find_my_task(self, workflow):
        for task in workflow.branch_tree:
            if task.thread_id != my_task.thread_id:
                continue
            if task.task == self:
                return task
        return None

    def _get_activated_tasks(self, my_task, destination):
        """
        Returns the list of tasks that were activated in the previous 
        call of execute(). Only returns tasks that point towards the
        destination task, i.e. those which have destination as a 
        descendant.

        my_task -- the task of this TaskSpec
        destination -- the child task
        """
        task = destination._find_ancestor(self.thread_starter)
        return self.thread_starter._get_activated_tasks(task, destination)

    def _get_activated_threads(self, my_task):
        """
        Returns the list of threads that were activated in the previous 
        call of execute().

        my_task -- the task of this TaskSpec
        """
        return my_task.children

    def _on_trigger(self, my_task):
        """
        May be called after execute() was already completed to create an
        additional outbound task.
        """
        # Find a Task for this task.
        my_task = self._find_my_task(my_task.workflow)
        for output in self.outputs:
            new_task = my_task.add_child(output, Task.READY)
            new_task.triggered = True

    def _predict_hook(self, my_task):
        split_n = my_task.get_data('split_n', self.times)
        if split_n is None:
            split_n = my_task.get_data(self.times_attribute, 1)

        # if we were created with thread_starter suppressed, connect it now.
        if self.thread_starter is None:
            self.thread_starter = self.outputs[0]

        # Predict the outputs.
        outputs = []
        for i in range(split_n):
            outputs.append(self.thread_starter)
        if my_task._is_definite():
            my_task._sync_children(outputs, Task.FUTURE)
        else:
            my_task._sync_children(outputs, Task.LIKELY)

    def _on_complete_hook(self, my_task):
        # Split, and remember the number of splits in the context data.
        split_n = self.times
        if split_n is None:
            split_n = my_task.get_data(self.times_attribute)

        # Create the outgoing tasks.
        outputs = []
        for i in range(split_n):
            outputs.append(self.thread_starter)
        my_task._sync_children(outputs, Task.FUTURE)
        for child in my_task.children:
            child.task_spec._update_state(child)

    def serialize(self, serializer):
        return serializer._serialize_thread_split(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer._deserialize_thread_split(wf_spec, s_state)

########NEW FILE########
__FILENAME__ = ThreadStart
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from SpiffWorkflow.Task import Task
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.specs.TaskSpec import TaskSpec

class ThreadStart(TaskSpec):
    """
    This class implements the task the is placed at the beginning
    of each thread. It is NOT supposed to be used by in the API, it is
    used internally only (by the ThreadSplit task).
    The task has no inputs and at least one output.
    If more than one output is connected, the task does an implicit
    parallel split.
    """

    def __init__(self, parent, **kwargs):
        """
        Constructor. The name of this task is *always* 'ThreadStart'.
        
        :type  parent: TaskSpec
        :param parent: A reference to the parent task spec.
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.TaskSpec}.
        """
        TaskSpec.__init__(self, parent, 'ThreadStart', **kwargs)
        self.internal = True

    def _on_complete_hook(self, my_task):
        my_task._assign_new_thread_id()
        TaskSpec._on_complete_hook(self, my_task)

    def serialize(self, serializer):
        return serializer._serialize_thread_start(self)

    @classmethod
    def deserialize(self, serializer, wf_spec, s_state):
        return serializer._deserialize_thread_start(wf_spec, s_state)

########NEW FILE########
__FILENAME__ = Transform
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
import logging

from SpiffWorkflow.specs.TaskSpec import TaskSpec

LOG = logging.getLogger(__name__)


class Transform(TaskSpec):
    """
    This class implements a task that transforms input/output data.
    """

    def __init__(self, parent, name, transforms=None, **kwargs):
        """
        Constructor.

        :type  parent: TaskSpec
        :param parent: A reference to the parent task spec.
        :type  name: str
        :param name: The name of the task spec.
        :type  transforms: list
        :param transforms: The commands that this task will execute to
                        transform data. The commands will be executed using the
                        python 'exec' function. Accessing inputs and outputs is
                        achieved by referencing the my_task.* and self.*
                        variables'
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.TaskSpec}.
        """
        assert parent  is not None
        assert name    is not None
        TaskSpec.__init__(self, parent, name, **kwargs)
        self.transforms = transforms

    def _update_state_hook(self, my_task):
        if self.transforms:
            for transform in self.transforms:
                LOG.debug("Executing transform", extra=dict(data=transform))
                exec(transform)
        super(Transform, self)._update_state_hook(my_task)

    def serialize(self, serializer):
        s_state = serializer._serialize_simple(self)
        s_state['transforms'] = self.transforms
        return s_state

    @classmethod
    def deserialize(cls, serializer, wf_spec, s_state):
        spec = Transform(wf_spec, s_state['name'])
        serializer._deserialize_task_spec(wf_spec, s_state, spec=spec)
        spec.transforms = s_state['transforms']
        return spec

########NEW FILE########
__FILENAME__ = Trigger
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
from SpiffWorkflow.Task import Task
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.specs.TaskSpec import TaskSpec

class Trigger(TaskSpec):
    """
    This class implements a task that triggers an event on another 
    task.
    If more than one input is connected, the task performs an implicit
    multi merge.
    If more than one output is connected, the task performs an implicit
    parallel split.
    """

    def __init__(self, parent, name, context, times = 1, **kwargs):
        """
        Constructor.

        :type  parent: TaskSpec
        :param parent: A reference to the parent task spec.
        :type  name: str
        :param name: The name of the task spec.
        :type  context: list(str)
        :param context: A list of the names of tasks that are to be triggered.
        :type  times: int or None
        :param times: The number of signals before the trigger fires.
        :type  kwargs: dict
        :param kwargs: See L{SpiffWorkflow.specs.TaskSpec}.
        """
        assert parent  is not None
        assert name    is not None
        assert context is not None
        assert type(context) == type([])
        TaskSpec.__init__(self, parent, name, **kwargs)
        self.context = context
        self.times   = times
        self.queued  = 0

    def _on_trigger(self, my_task):
        """
        Enqueue a trigger, such that this tasks triggers multiple times later
        when _on_complete() is called.
        """
        self.queued += 1
        # All tasks that have already completed need to be put back to
        # READY.
        for thetask in my_task.workflow.task_tree:
            if thetask.thread_id != my_task.thread_id:
                continue
            if thetask.task_spec == self and thetask._has_state(Task.COMPLETED):
                thetask._set_state(Task.FUTURE, True)
                thetask._ready()

    def _on_complete_hook(self, my_task):
        """
        A hook into _on_complete() that does the task specific work.

        :type  my_task: Task
        :param my_task: A task in which this method is executed.
        :rtype:  bool
        :returns: True on success, False otherwise.
        """
        for i in range(self.times + self.queued):
            for task_name in self.context:
                task = my_task.workflow.get_task_spec_from_name(task_name)
                task._on_trigger(my_task)
        self.queued = 0
        TaskSpec._on_complete_hook(self, my_task)

    def serialize(self, serializer):
        return serializer._serialize_trigger(self)

    @classmethod
    def deserialize(cls, serializer, wf_spec, s_state, **kwargs):
        """
        Deserializes the trigger using the provided serializer.
        """
        return serializer._deserialize_trigger(wf_spec,
                                               s_state,
                                               **kwargs)

########NEW FILE########
__FILENAME__ = WorkflowSpec
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import logging

from SpiffWorkflow.specs import StartTask

LOG = logging.getLogger(__name__)


class WorkflowSpec(object):
    """
    This class represents the specification of a workflow.
    """

    def __init__(self, name=None, filename=None):
        """
        Constructor.
        """
        self.name = name or ''
        self.description = ''
        self.file = filename
        self.task_specs = dict()
        self.start = StartTask(self)

    def _add_notify(self, task_spec):
        """
        Called by a task spec when it was added into the workflow.
        """
        if task_spec.name in self.task_specs:
            raise KeyError('Duplicate task spec name: ' + task_spec.name)
        self.task_specs[task_spec.name] = task_spec
        task_spec.id = len(self.task_specs)

    def get_task_spec_from_name(self, name):
        """
        Returns the task with the given name.

        :type  name: str
        :param name: The name of the task spec.
        :rtype:  TaskSpec
        :returns: The task spec with the given name.
        """
        return self.task_specs[name]

    def validate(self):
        """Checks integrity of workflow and reports any problems with it.

        Detects:
        - loops (tasks that wait on each other in a loop)
        :returns: empty list if valid, a list of errors if not
        """
        results = []
        from SpiffWorkflow.specs import Join

        def recursive_find_loop(task, history):
            current = history[:]
            current.append(task)
            if isinstance(task, Join):
                if task in history:
                    msg = "Found loop with '%s': %s then '%s' again" % (
                            task.name, '->'.join([p.name for p in history]),
                            task.name)
                    raise Exception(msg)
                for predecessor in task.inputs:
                    recursive_find_loop(predecessor, current)

            for parent in task.inputs:
                recursive_find_loop(parent, current)

        for task_id, task in self.task_specs.items():
            # Check for cyclic waits
            try:
                recursive_find_loop(task, [])
            except Exception as exc:
                results.append(exc.__str__())

            # Check for disconnected tasks
            if not task.inputs and task.name not in ['Start', 'Root']:
                if task.outputs:
                    results.append("Task '%s' is disconnected (no inputs)" %
                        task.name)
                else:
                    LOG.debug("Task '%s' is not being used" % task.name)

        return results

    def serialize(self, serializer, **kwargs):
        """
        Serializes the instance using the provided serializer.

        :type  serializer: L{SpiffWorkflow.storage.Serializer}
        :param serializer: The serializer to use.
        :type  kwargs: dict
        :param kwargs: Passed to the serializer.
        :rtype:  object
        :returns: The serialized object.
        """
        return serializer.serialize_workflow_spec(self, **kwargs)

    @classmethod
    def deserialize(cls, serializer, s_state, **kwargs):
        """
        Deserializes a WorkflowSpec instance using the provided serializer.

        :type  serializer: L{SpiffWorkflow.storage.Serializer}
        :param serializer: The serializer to use.
        :type  s_state: object
        :param s_state: The serialized workflow specification object.
        :type  kwargs: dict
        :param kwargs: Passed to the serializer.
        :rtype:  WorkflowSpec
        :returns: The resulting instance.
        """
        return serializer.deserialize_workflow_spec(s_state, **kwargs)

    def get_dump(self, verbose=False):
        done = set()

        def recursive_dump(task_spec, indent):
            if task_spec in done:
                return  '[shown earlier] %s (%s:%s)' % (task_spec.name, task_spec.__class__.__name__, hex(id(task_spec))) + '\n'

            done.add(task_spec)
            dump = '%s (%s:%s)' % (task_spec.name, task_spec.__class__.__name__, hex(id(task_spec))) + '\n'
            if verbose:
                if task_spec.inputs:
                    dump += indent + '-  IN: ' + ','.join(['%s (%s)' % (t.name, hex(id(t))) for t in task_spec.inputs]) + '\n'
                if task_spec.outputs:
                    dump += indent + '- OUT: ' + ','.join(['%s (%s)' % (t.name, hex(id(t))) for t in task_spec.outputs]) + '\n'
            sub_specs = ([task_spec.spec.start] if hasattr(task_spec, 'spec') else []) + task_spec.outputs
            for i, t in enumerate(sub_specs):
                dump += indent + '   --> ' + recursive_dump(t,indent+('   |   ' if i+1 < len(sub_specs) else '       '))
            return dump


        dump = recursive_dump(self.start, '')

        return dump

    def dump(self):
        print(self.get_dump())

########NEW FILE########
__FILENAME__ = DictionarySerializer
# -*- coding: utf-8 -*-
from __future__ import division
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import pickle
from base64 import b64encode, b64decode
from SpiffWorkflow import Workflow
from SpiffWorkflow.util.impl import get_class
from SpiffWorkflow.Task import Task
from SpiffWorkflow.operators import *
from SpiffWorkflow.specs.TaskSpec import TaskSpec
from SpiffWorkflow.specs import *
from SpiffWorkflow.storage.Serializer import Serializer
from SpiffWorkflow.storage.exceptions import TaskNotSupportedError
import warnings

class DictionarySerializer(Serializer):
    def _serialize_dict(self, thedict):
        return dict(
            (k, b64encode(pickle.dumps(v, protocol=pickle.HIGHEST_PROTOCOL)))
            for k, v in thedict.items())

    def _deserialize_dict(self, s_state):
        return dict((k, pickle.loads(b64decode(v)))
                    for k, v in s_state.items())

    def _serialize_list(self, thelist):
        return [b64encode(pickle.dumps(v, protocol=pickle.HIGHEST_PROTOCOL))
                for v in thelist]

    def _deserialize_list(self, s_state):
        return [pickle.loads(b64decode(v)) for v in s_state]

    def _serialize_attrib(self, attrib):
        return attrib.name

    def _deserialize_attrib(self, s_state):
        return Attrib(s_state)

    def _serialize_pathattrib(self, pathattrib):
        return pathattrib.path

    def _deserialize_pathattrib(self, s_state):
        return PathAttrib(s_state)

    def _serialize_operator(self, op):
        return [self._serialize_arg(a) for a in op.args]

    def _serialize_operator_equal(self, op):
        return self._serialize_operator(op)

    def _deserialize_operator_equal(self, s_state):
        return Equal(*[self._deserialize_arg(c) for c in s_state])

    def _serialize_operator_not_equal(self, op):
        return self._serialize_operator(op)

    def _deserialize_operator_not_equal(self, s_state):
        return NotEqual(*[self._deserialize_arg(c) for c in s_state])

    def _serialize_operator_greater_than(self, op):
        return self._serialize_operator(op)

    def _deserialize_operator_greater_than(self, s_state):
        return GreaterThan(*[self._deserialize_arg(c) for c in s_state])

    def _serialize_operator_less_than(self, op):
        return self._serialize_operator(op)

    def _deserialize_operator_less_than(self, s_state):
        return LessThan(*[self._deserialize_arg(c) for c in s_state])

    def _serialize_operator_match(self, op):
        return self._serialize_operator(op)

    def _deserialize_operator_match(self, s_state):
        return Match(*[self._deserialize_arg(c) for c in s_state])

    def _serialize_arg(self, arg):
        if isinstance(arg, Attrib):
            return 'Attrib', self._serialize_attrib(arg)
        elif isinstance(arg, PathAttrib):
            return 'PathAttrib', self._serialize_pathattrib(arg)
        elif isinstance(arg, Operator):
            module = arg.__class__.__module__
            arg_type = module + '.' + arg.__class__.__name__
            return arg_type, arg.serialize(self)
        return 'value', arg

    def _deserialize_arg(self, s_state):
        arg_type, arg = s_state
        if arg_type == 'Attrib':
            return self._deserialize_attrib(arg)
        elif arg_type == 'PathAttrib':
            return self._deserialize_pathattrib(arg)
        elif arg_type == 'value':
            return arg
        arg_cls = get_class(arg_type)
        return arg_cls.deserialize(self, arg)

    def _serialize_task_spec(self, spec):
        s_state = dict(id = spec.id,
                       name = spec.name,
                       description = spec.description,
                       manual = spec.manual,
                       internal = spec.internal,
                       lookahead = spec.lookahead)
        module_name = spec.__class__.__module__
        s_state['class'] = module_name + '.' + spec.__class__.__name__
        s_state['inputs'] = [t.name for t in spec.inputs]
        s_state['outputs'] = [t.name for t in spec.outputs]
        s_state['data'] = self._serialize_dict(spec.data)
        s_state['defines'] = self._serialize_dict(spec.defines)
        s_state['pre_assign'] = self._serialize_list(spec.pre_assign)
        s_state['post_assign'] = self._serialize_list(spec.post_assign)
        s_state['locks'] = spec.locks[:]

        # Note: Events are not serialized; this is documented in
        # the TaskSpec API docs.

        return s_state

    def _deserialize_task_spec(self, wf_spec, s_state, spec):
        spec.id = s_state['id']
        spec.description = s_state['description']
        spec.manual = s_state['manual']
        spec.internal = s_state['internal']
        spec.lookahead = s_state['lookahead']
        spec.data = self._deserialize_dict(s_state['data'])
        spec.defines = self._deserialize_dict(s_state['defines'])
        spec.pre_assign = self._deserialize_list(s_state['pre_assign'])
        spec.post_assign = self._deserialize_list(s_state['post_assign'])
        spec.locks = s_state['locks'][:]
        # We can't restore inputs and outputs yet because they may not be
        # deserialized yet. So keep the names, and resolve them in the end.
        spec.inputs = s_state['inputs'][:]
        spec.outputs = s_state['outputs'][:]
        return spec

    def _serialize_acquire_mutex(self, spec):
        s_state = self._serialize_task_spec(spec)
        s_state['mutex'] = spec.mutex
        return s_state

    def _deserialize_acquire_mutex(self, wf_spec, s_state):
        spec = AcquireMutex(wf_spec, s_state['name'], s_state['mutex'])
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        spec.mutex = s_state['mutex']
        return spec

    def _serialize_cancel(self, spec):
        s_state = self._serialize_task_spec(spec)
        s_state['cancel_successfully'] = spec.cancel_successfully
        return s_state

    def _deserialize_cancel(self, wf_spec, s_state):
        spec = Cancel(wf_spec, s_state['name'],
                      success=s_state['cancel_successfully'])
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec

    def _serialize_cancel_task(self, spec):
        return self._serialize_trigger(spec)

    def _deserialize_cancel_task(self, wf_spec, s_state):
        spec = CancelTask(wf_spec,
                          s_state['name'],
                          s_state['context'],
                          times=s_state['times'])
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec

    def _serialize_celery(self, spec):
        args = self._serialize_list(spec.args)
        kwargs = self._serialize_dict(spec.kwargs)
        s_state = self._serialize_task_spec(spec)
        s_state['call'] = spec.call
        s_state['args'] = args
        s_state['kwargs'] = kwargs
        s_state['result_key'] = spec.result_key
        return s_state

    def _deserialize_celery(self, wf_spec, s_state):
        args = self._deserialize_list(s_state['args'])
        kwargs = self._deserialize_dict(s_state.get('kwargs', {}))
        spec = Celery(wf_spec, s_state['name'], s_state['call'],
                      call_args=args,
                      result_key=s_state['result_key'],
                      **kwargs)
        self._deserialize_task_spec(wf_spec, s_state, spec)
        return spec

    def _serialize_choose(self, spec):
        s_state = self._serialize_task_spec(spec)
        s_state['context'] = spec.context
        # despite the various documentation suggesting that choice ought to be
        # a collection of objects, here it is a collection of strings. The
        # handler in MultiChoice.py converts it to TaskSpecs. So instead of:
        #s_state['choice'] = [c.name for c in spec.choice]
        # we have:
        s_state['choice'] = spec.choice
        return s_state

    def _deserialize_choose(self, wf_spec, s_state):
        spec = Choose(wf_spec,
                      s_state['name'],
                      s_state['context'],
                      s_state['choice'])
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec

    def _serialize_exclusive_choice(self, spec):
        s_state = self._serialize_multi_choice(spec)
        s_state['default_task_spec'] = spec.default_task_spec
        return s_state

    def _deserialize_exclusive_choice(self, wf_spec, s_state):
        spec = ExclusiveChoice(wf_spec, s_state['name'])
        self._deserialize_multi_choice(wf_spec, s_state, spec=spec)
        spec.default_task_spec = s_state['default_task_spec']
        return spec

    def _serialize_execute(self, spec):
        s_state = self._serialize_task_spec(spec)
        s_state['args'] = spec.args
        return s_state

    def _deserialize_execute(self, wf_spec, s_state):
        spec = Execute(wf_spec, s_state['name'], s_state['args'])
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec

    def _serialize_gate(self, spec):
        s_state = self._serialize_task_spec(spec)
        s_state['context'] = spec.context
        return s_state

    def _deserialize_gate(self, wf_spec, s_state):
        spec = Gate(wf_spec, s_state['name'], s_state['context'])
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec

    def _serialize_join(self, spec):
        s_state = self._serialize_task_spec(spec)
        s_state['split_task'] = spec.split_task
        s_state['threshold'] = b64encode(
            pickle.dumps(spec.threshold, protocol=pickle.HIGHEST_PROTOCOL))
        s_state['cancel_remaining'] = spec.cancel_remaining
        return s_state

    def _deserialize_join(self, wf_spec, s_state):
        spec = Join(wf_spec,
                    s_state['name'],
                    split_task = s_state['split_task'],
                    threshold = pickle.loads(b64decode(s_state['threshold'])),
                    cancel = s_state['cancel_remaining'])
        self._deserialize_task_spec(wf_spec, s_state, spec = spec)
        return spec

    def _serialize_multi_choice(self, spec):
        s_state = self._serialize_task_spec(spec)
        s_state['cond_task_specs'] = thestate = []
        for condition, spec_name in spec.cond_task_specs:
            cond = self._serialize_arg(condition)
            thestate.append((cond, spec_name))
        # spec.choice is actually a list of strings in MultiChoice: see
        # _predict_hook. So, instead of
        #s_state['choice'] = spec.choice and spec.choice.name or None
        s_state['choice'] = spec.choice or None
        return s_state

    def _deserialize_multi_choice(self, wf_spec, s_state, spec=None):
        if spec is None:
            spec = MultiChoice(wf_spec, s_state['name'])
        if s_state.get('choice') is not None:
            # this is done in _predict_hook: it's kept as a string for now.
            # spec.choice = wf_spec.get_task_spec_from_name(s_state['choice'])
            spec.choice = s_state['choice']
        for cond, spec_name in s_state['cond_task_specs']:
            condition = self._deserialize_arg(cond)
            spec.cond_task_specs.append((condition, spec_name))
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec

    def _serialize_multi_instance(self, spec):
        s_state = self._serialize_task_spec(spec)
        s_state['times'] = spec.times
        return s_state

    def _deserialize_multi_instance(self, wf_spec, s_state):
        spec = MultiInstance(wf_spec,
                             s_state['name'],
                             times=s_state['times'])
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec

    def _serialize_release_mutex(self, spec):
        s_state = self._serialize_task_spec(spec)
        s_state['mutex'] = spec.mutex
        return s_state

    def _deserialize_release_mutex(self, wf_spec, s_state):
        spec = ReleaseMutex(wf_spec, s_state['name'], s_state['mutex'])
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec

    def _serialize_simple(self, spec):
        assert isinstance(spec, TaskSpec)
        return self._serialize_task_spec(spec)

    def _deserialize_simple(self, wf_spec, s_state):
        assert isinstance(wf_spec, WorkflowSpec)
        spec = Simple(wf_spec, s_state['name'])
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec

    def _serialize_start_task(self, spec):
        return self._serialize_task_spec(spec)

    def _deserialize_start_task(self, wf_spec, s_state):
        spec = StartTask(wf_spec)
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec

    def _serialize_sub_workflow(self, spec):
        warnings.warn("SubWorkflows cannot be safely serialized as they only" +
                      " store a reference to the subworkflow specification " +
                      " as a path to an external XML file.")
        s_state = self._serialize_task_spec(spec)
        s_state['file'] = spec.file
        s_state['in_assign'] = self._serialize_list(spec.in_assign)
        s_state['out_assign'] = self._serialize_list(spec.out_assign)
        return s_state

    def _deserialize_sub_workflow(self, wf_spec, s_state):
        warnings.warn("SubWorkflows cannot be safely deserialized as they " +
                      "only store a reference to the subworkflow " +
                      "specification as a path to an external XML file.")
        spec = SubWorkflow(wf_spec, s_state['name'], s_state['file'])
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        spec.in_assign = self._deserialize_list(s_state['in_assign'])
        spec.out_assign = self._deserialize_list(s_state['out_assign'])
        return spec

    def _serialize_thread_merge(self, spec):
        return self._serialize_join(spec)

    def _deserialize_thread_merge(self, wf_spec, s_state):
        spec = ThreadMerge(wf_spec, s_state['name'], s_state['split_task'])
        # while ThreadMerge is a Join, the _deserialise_join isn't what we want
        # here: it makes a join from scratch which we don't need (the
        # ThreadMerge constructor does it all). Just task_spec it.
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec

    def _serialize_thread_split(self, spec):
        s_state = self._serialize_task_spec(spec)
        s_state['times'] = spec.times
        s_state['times_attribute'] = spec.times_attribute
        return s_state

    def _deserialize_thread_split(self, wf_spec, s_state):
        spec = ThreadSplit(wf_spec,
                           s_state['name'],
                           s_state['times'],
                           s_state['times_attribute'],
                           suppress_threadstart_creation=True)
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec

    def _serialize_thread_start(self, spec):
        return self._serialize_task_spec(spec)

    def _deserialize_thread_start(self, wf_spec, s_state):
        # specs/__init__.py deliberately hides this: forcibly import it
        from SpiffWorkflow.specs.ThreadStart import ThreadStart
        spec = ThreadStart(wf_spec)
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec

    def _deserialize_merge(self, wf_spec, s_state):
        spec = Merge(wf_spec, s_state['name'], s_state['split_task'])
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec

    def _serialize_trigger(self, spec):
        s_state = self._serialize_task_spec(spec)
        s_state['context'] = spec.context
        s_state['times'] = spec.times
        s_state['queued'] = spec.queued
        return s_state

    def _deserialize_trigger(self, wf_spec, s_state):
        spec = Trigger(wf_spec,
                       s_state['name'],
                       s_state['context'],
                       times=s_state['times'])
        self._deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec

    def serialize_workflow_spec(self, spec, **kwargs):
        s_state = dict(name=spec.name,
                       description=spec.description,
                       file=spec.file)
        s_state['task_specs'] = dict((k, v.serialize(self))
                                     for k, v in spec.task_specs.items())
        return s_state

    def deserialize_workflow_spec(self, s_state, **kwargs):
        spec = WorkflowSpec(s_state['name'], filename=s_state['file'])
        spec.description = s_state['description']
        # Handle Start Task
        spec.start = None
        del spec.task_specs['Start']
        start_task_spec_state = s_state['task_specs']['Start']
        start_task_spec = StartTask.deserialize(self, spec, start_task_spec_state)
        spec.start = start_task_spec
        spec.task_specs['Start'] = start_task_spec

        for name, task_spec_state in s_state['task_specs'].items():
            if name == 'Start':
                continue
            task_spec_cls = get_class(task_spec_state['class'])
            task_spec = task_spec_cls.deserialize(self, spec, task_spec_state)
            spec.task_specs[name] = task_spec
        for name, task_spec in spec.task_specs.items():
            task_spec.inputs = [spec.get_task_spec_from_name(t)
                                for t in task_spec.inputs]
            task_spec.outputs = [spec.get_task_spec_from_name(t)
                                 for t in task_spec.outputs]
        assert spec.start is spec.get_task_spec_from_name('Start')
        return spec

    def serialize_workflow(self, workflow, **kwargs):
        assert isinstance(workflow, Workflow)
        s_state = dict()
        s_state['wf_spec'] = self.serialize_workflow_spec(workflow.spec,
                **kwargs)

        # data
        s_state['data'] =  self._serialize_dict(workflow.data)

        # last_node
        value = workflow.last_task
        s_state['last_task'] = value.id if not value is None else None

        # outer_workflow
        #s_state['outer_workflow'] = workflow.outer_workflow.id

        #success
        s_state['success'] = workflow.success

        #task_tree
        s_state['task_tree'] = self._serialize_task(workflow.task_tree)

        return s_state

    def deserialize_workflow(self, s_state, **kwargs):
        wf_spec = self.deserialize_workflow_spec(s_state['wf_spec'], **kwargs)
        workflow = Workflow(wf_spec)

        # data
        workflow.data = self._deserialize_dict(s_state['data'])

        # outer_workflow
        #workflow.outer_workflow =  find_workflow_by_id(remap_workflow_id(s_state['outer_workflow']))

        # success
        workflow.success = s_state['success']

        # workflow
        workflow.spec = wf_spec

        # task_tree
        workflow.task_tree = self._deserialize_task(workflow, s_state['task_tree'])

        # Re-connect parents
        for task in workflow.get_tasks():
            task.parent = workflow.get_task(task.parent)

        # last_task
        workflow.last_task = workflow.get_task(s_state['last_task'])

        return workflow

    def _serialize_task(self, task, skip_children=False):
        assert isinstance(task, Task)

        if isinstance(task.task_spec, SubWorkflow):
            raise TaskNotSupportedError(
                "Subworkflow tasks cannot be serialized (due to their use of" +
                " internal_data to store the subworkflow).")
        
        s_state = dict()

        # id
        s_state['id'] = task.id

        # workflow
        #s_state['workflow'] = task.workflow.id

        # parent
        s_state['parent'] = task.parent.id if not task.parent is None else None

        # children
        if not skip_children:
            s_state['children'] = [self._serialize_task(child) for child in task.children]

        # state
        s_state['state'] = task.state
        s_state['triggered'] = task.triggered

        # task_spec
        s_state['task_spec'] = task.task_spec.name

        # last_state_change
        s_state['last_state_change'] = task.last_state_change

        # data
        s_state['data'] =  self._serialize_dict(task.data)

        # internal_data
        s_state['internal_data'] = task.internal_data

        return s_state

    def _deserialize_task(self, workflow, s_state):
        assert isinstance(workflow, Workflow)
        # task_spec
        task_spec = workflow.get_task_spec_from_name(s_state['task_spec'])
        task = Task(workflow, task_spec)

        # id
        task.id = s_state['id']

        # parent
        # as the task_tree might not be complete yet
        # keep the ids so they can be processed at the end
        task.parent = s_state['parent']

        # children
        task.children = [self._deserialize_task(workflow, c) for c in s_state['children']]

        # state
        task._state = s_state['state']
        task.triggered = s_state['triggered']

        # last_state_change
        task.last_state_change = s_state['last_state_change']

        # data
        task.data = self._deserialize_dict(s_state['data'])

        # internal_data
        task.internal_data = s_state['internal_data']

        return task

########NEW FILE########
__FILENAME__ = exceptions
class TaskSpecNotSupportedError(ValueError):
    pass

class TaskNotSupportedError(ValueError):
    pass

########NEW FILE########
__FILENAME__ = JSONSerializer
# -*- coding: utf-8 -*-
from __future__ import division
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import json
import uuid
from SpiffWorkflow.storage import DictionarySerializer
from SpiffWorkflow.storage.Serializer import Serializer
from SpiffWorkflow.operators import Attrib

_dictserializer = DictionarySerializer()

def object_hook(dct):
    if '__uuid__' in dct:
        return uuid.UUID(dct['__uuid__'])

    if '__bytes__' in dct:
        return dct['__bytes__'].encode('ascii')
    
    if '__attrib__' in dct:
        return Attrib(dct['__attrib__'])

    return dct

def default(obj):
    if isinstance(obj, uuid.UUID):
        return {'__uuid__': obj.hex}

    if isinstance(obj, bytes):
        return {'__bytes__': obj.decode('ascii') }
        
    if isinstance(obj, Attrib):
        return {'__attrib__': obj.name}

    raise TypeError('%r is not JSON serializable' % obj)

def loads(text):
    return json.loads(text, object_hook=object_hook)

def dumps(dct):
    return json.dumps(dct, default=default)

class JSONSerializer(Serializer):
    def serialize_workflow_spec(self, wf_spec, **kwargs):
        thedict = _dictserializer.serialize_workflow_spec(wf_spec, **kwargs)
        return dumps(thedict)

    def deserialize_workflow_spec(self, s_state, **kwargs):
        thedict = loads(s_state)
        return _dictserializer.deserialize_workflow_spec(thedict, **kwargs)

    def serialize_workflow(self, workflow, **kwargs):
        thedict = _dictserializer.serialize_workflow(workflow, **kwargs)
        return dumps(thedict)

    def deserialize_workflow(self, s_state, **kwargs):
        thedict = loads(s_state)
        return _dictserializer.deserialize_workflow(thedict, **kwargs)

########NEW FILE########
__FILENAME__ = OpenWfeXmlSerializer
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import os
import sys
import xml.dom.minidom as minidom
from SpiffWorkflow import operators, specs
from SpiffWorkflow.exceptions import StorageException
from SpiffWorkflow.storage.Serializer import Serializer

_spec_tags = ('task',
              'concurrence',
              'if',
              'sequence')
_op_map = {'equals':       operators.Equal,
           'not-equals':   operators.NotEqual,
           'less-than':    operators.LessThan,
           'greater-than': operators.GreaterThan,
           'matches':      operators.Match}

class OpenWfeXmlSerializer(Serializer):
    """
    Parses OpenWFE XML into a workflow object.
    """
    def _read_condition(self, node):
        """
        Reads the logical tag from the given node, returns a Condition object.

        node -- the xml node (xml.dom.minidom.Node)
        """
        term1 = node.getAttribute('field-value')
        op    = node.nodeName.lower()
        term2 = node.getAttribute('other-value')
        if op not in _op_map:
            raise StorageException('Invalid operator in XML file')
        return _op_map[op](operators.Attrib(term1),
                           operators.Attrib(term2))

    def _read_if(self, workflow, start_node):
        """
        Reads the sequence from the given node.

        workflow -- the workflow with which the concurrence is associated
        start_node -- the xml structure (xml.dom.minidom.Node)
        """
        assert start_node.nodeName.lower() == 'if'
        name = start_node.getAttribute('name').lower()

        # Collect all information.
        match     = None
        nomatch   = None
        condition = None
        for node in start_node.childNodes:
            if node.nodeType != minidom.Node.ELEMENT_NODE:
                continue
            if node.nodeName.lower() in _spec_tags:
                if match is None:
                    match = self._read_spec(workflow, node)
                elif nomatch is None:
                    nomatch = self._read_spec(workflow, node)
                else:
                    assert False # Only two tasks in "if" allowed.
            elif node.nodeName.lower() in _op_map:
                if condition is None:
                    condition = self._read_condition(node)
                else:
                    assert False # Multiple conditions not yet supported.
            else:
                print("Unknown type:", type)
                assert False # Unknown tag.

        # Model the if statement.
        assert condition is not None
        assert match     is not None
        choice = specs.ExclusiveChoice(workflow, name)
        end    = specs.Simple(workflow, name + '_end')
        if nomatch is None:
            choice.connect(end)
        else:
            choice.connect(nomatch[0])
            nomatch[1].connect(end)
        choice.connect_if(condition, match[0])
        match[1].connect(end)

        return (choice, end)

    def _read_sequence(self, workflow, start_node):
        """
        Reads the children of the given node in sequential order.
        Returns a tuple (start, end) that contains the stream of objects
        that model the behavior.

        workflow -- the workflow with which the concurrence is associated
        start_node -- the xml structure (xml.dom.minidom.Node)
        """
        assert start_node.nodeName.lower() == 'sequence'
        name  = start_node.getAttribute('name').lower()
        first = None
        last  = None
        for node in start_node.childNodes:
            if node.nodeType != minidom.Node.ELEMENT_NODE:
                continue
            if node.nodeName.lower() in _spec_tags:
                (start, end) = self._read_spec(workflow, node)
                if first is None:
                    first = start
                else:
                    last.connect(start)
                last = end
            else:
                print("Unknown type:", type)
                assert False # Unknown tag.
        return (first, last)

    def _read_concurrence(self, workflow, start_node):
        """
        Reads the concurrence from the given node.

        workflow -- the workflow with which the concurrence is associated
        start_node -- the xml structure (xml.dom.minidom.Node)
        """
        assert start_node.nodeName.lower() == 'concurrence'
        name = start_node.getAttribute('name').lower()
        multichoice = specs.MultiChoice(workflow, name)
        synchronize = specs.Join(workflow, name + '_end', name)
        for node in start_node.childNodes:
            if node.nodeType != minidom.Node.ELEMENT_NODE:
                continue
            if node.nodeName.lower() in _spec_tags:
                (start, end) = self._read_spec(workflow, node)
                multichoice.connect_if(None, start)
                end.connect(synchronize)
            else:
                print("Unknown type:", type)
                assert False # Unknown tag.
        return (multichoice, synchronize)

    def _read_spec(self, workflow, start_node):
        """
        Reads the task spec from the given node and returns a tuple
        (start, end) that contains the stream of objects that model
        the behavior.

        workflow -- the workflow with which the task spec is associated
        start_node -- the xml structure (xml.dom.minidom.Node)
        """
        type = start_node.nodeName.lower()
        name = start_node.getAttribute('name').lower()
        assert type in _spec_tags

        if type == 'concurrence':
            return self._read_concurrence(workflow, start_node)
        elif type == 'if':
            return self._read_if(workflow, start_node)
        elif type == 'sequence':
            return self._read_sequence(workflow, start_node)
        elif type == 'task':
            spec = specs.Simple(workflow, name)
            return spec, spec
        else:
            print("Unknown type:", type)
            assert False # Unknown tag.

    def _read_workflow(self, start_node):
        """
        Reads the workflow specification from the given workflow node
        and returns a list of WorkflowSpec objects.

        start_node -- the xml structure (xml.dom.minidom.Node)
        """
        name = start_node.getAttribute('name')
        assert name is not None
        workflow_spec = specs.WorkflowSpec(name)
        last_spec     = workflow_spec.start
        for node in start_node.childNodes:
            if node.nodeType != minidom.Node.ELEMENT_NODE:
                continue
            if node.nodeName == 'description':
                pass
            elif node.nodeName.lower() in _spec_tags:
                (start, end) = self._read_spec(workflow_spec, node)
                last_spec.connect(start)
                last_spec = end
            else:
                print("Unknown type:", type)
                assert False # Unknown tag.

        last_spec.connect(specs.Simple(workflow_spec, 'End'))
        return workflow_spec

    def deserialize_workflow_spec(self, s_state, **kwargs):
        """
        Reads the workflow from the given XML structure and returns a
        workflow object.
        """
        dom  = minidom.parseString(s_state)
        node = dom.getElementsByTagName('process-definition')[0]
        return self._read_workflow(node)

########NEW FILE########
__FILENAME__ = Serializer
# -*- coding: utf-8 -*-
from __future__ import division
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


class Serializer(object):
    def serialize_workflow_spec(self, wf_spec, **kwargs):
        raise NotImplementedError("You must implement the serialize_workflow_spec method.")

    def deserialize_workflow_spec(self, s_state, **kwargs):
        raise NotImplementedError("You must implement the deserialize_workflow_spec method.")

    def serialize_workflow(self, workflow, **kwargs):
        raise NotImplementedError("You must implement the serialize_workflow method.")

    def deserialize_workflow(self, s_state, **kwargs):
        raise NotImplementedError("You must implement the deserialize_workflow method.")

########NEW FILE########
__FILENAME__ = XmlSerializer
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007-2012 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import os
import re
import xml.dom.minidom as minidom
from SpiffWorkflow import operators, specs
from SpiffWorkflow.exceptions import StorageException
from SpiffWorkflow.storage.Serializer import Serializer

# Create a list of tag names out of the spec names.
_spec_map = dict()
for name in dir(specs):
    if name.startswith('_'):
        continue
    module = specs.__dict__[name]
    name   = re.sub(r'(.)([A-Z])', r'\1-\2', name).lower()
    _spec_map[name] = module
_spec_map['task'] = specs.Simple

_op_map = {'equals':       operators.Equal,
           'not-equals':   operators.NotEqual,
           'less-than':    operators.LessThan,
           'greater-than': operators.GreaterThan,
           'matches':      operators.Match}

_exc = StorageException

class XmlSerializer(Serializer):
    """
    Parses XML into a WorkflowSpec object.
    """
    def _deserialize_assign(self, workflow, start_node):
        """
        Reads the "pre-assign" or "post-assign" tag from the given node.
        
        start_node -- the xml node (xml.dom.minidom.Node)
        """
        name   = start_node.getAttribute('name')
        attrib = start_node.getAttribute('field')
        value  = start_node.getAttribute('value')
        kwargs = {}
        if name == '':
            _exc('name attribute required')
        if attrib != '' and value != '':
            _exc('Both, field and right-value attributes found')
        elif attrib == '' and value == '':
            _exc('field or value attribute required')
        elif value != '':
            kwargs['right'] = value
        else:
            kwargs['right_attribute'] = attrib
        return operators.Assign(name, **kwargs)

    def _deserialize_data(self, workflow, start_node):
        """
        Reads a "data" or "define" tag from the given node.
        
        start_node -- the xml node (xml.dom.minidom.Node)
        """
        name   = start_node.getAttribute('name')
        value  = start_node.getAttribute('value')
        return name, value

    def _deserialize_assign_list(self, workflow, start_node):
        """
        Reads a list of assignments from the given node.
        
        workflow -- the workflow
        start_node -- the xml structure (xml.dom.minidom.Node)
        """
        # Collect all information.
        assignments = []
        for node in start_node.childNodes:
            if node.nodeType != minidom.Node.ELEMENT_NODE:
                continue
            if node.nodeName.lower() == 'assign':
                assignments.append(self._deserialize_assign(workflow, node))
            else:
                _exc('Unknown node: %s' % node.nodeName)
        return assignments

    def _deserialize_logical(self, node):
        """
        Reads the logical tag from the given node, returns a Condition object.
        
        node -- the xml node (xml.dom.minidom.Node)
        """
        term1_attrib = node.getAttribute('left-field')
        term1_value  = node.getAttribute('left-value')
        op           = node.nodeName.lower()
        term2_attrib = node.getAttribute('right-field')
        term2_value  = node.getAttribute('right-value')
        kwargs       = {}
        if op not in _op_map:
            _exc('Invalid operator')
        if term1_attrib != '' and term1_value != '':
            _exc('Both, left-field and left-value attributes found')
        elif term1_attrib == '' and term1_value == '':
            _exc('left-field or left-value attribute required')
        elif term1_value != '':
            left = term1_value
        else:
            left = operators.Attrib(term1_attrib)
        if term2_attrib != '' and term2_value != '':
            _exc('Both, right-field and right-value attributes found')
        elif term2_attrib == '' and term2_value == '':
            _exc('right-field or right-value attribute required')
        elif term2_value != '':
            right = term2_value
        else:
            right = operators.Attrib(term2_attrib)
        return _op_map[op](left, right)

    def _deserialize_condition(self, workflow, start_node):
        """
        Reads the conditional statement from the given node.
        
        workflow -- the workflow with which the concurrence is associated
        start_node -- the xml structure (xml.dom.minidom.Node)
        """
        # Collect all information.
        condition = None
        spec_name = None
        for node in start_node.childNodes:
            if node.nodeType != minidom.Node.ELEMENT_NODE:
                continue
            if node.nodeName.lower() == 'successor':
                if spec_name is not None:
                    _exc('Duplicate task name %s' % spec_name)
                if node.firstChild is None:
                    _exc('Successor tag without a task name')
                spec_name = node.firstChild.nodeValue
            elif node.nodeName.lower() in _op_map:
                if condition is not None:
                    _exc('Multiple conditions are not yet supported')
                condition = self._deserialize_logical(node)
            else:
                _exc('Unknown node: %s' % node.nodeName)

        if condition is None:
            _exc('Missing condition in conditional statement')
        if spec_name is None:
            _exc('A %s has no task specified' % start_node.nodeName)
        return condition, spec_name

    def _deserialize_task_spec(self, workflow, start_node, read_specs):
        """
        Reads the task from the given node and returns a tuple
        (start, end) that contains the stream of objects that model
        the behavior.
        
        workflow -- the workflow with which the task is associated
        start_node -- the xml structure (xml.dom.minidom.Node)
        """
        # Extract attributes from the node.
        nodetype        = start_node.nodeName.lower()
        name            = start_node.getAttribute('name').lower()
        context         = start_node.getAttribute('context').lower()
        mutex           = start_node.getAttribute('mutex').lower()
        cancel          = start_node.getAttribute('cancel').lower()
        success         = start_node.getAttribute('success').lower()
        times           = start_node.getAttribute('times').lower()
        times_field     = start_node.getAttribute('times-field').lower()
        threshold       = start_node.getAttribute('threshold').lower()
        threshold_field = start_node.getAttribute('threshold-field').lower()
        file            = start_node.getAttribute('file').lower()
        file_field      = start_node.getAttribute('file-field').lower()
        kwargs          = {'lock':        [],
                           'data':        {},
                           'defines':     {},
                           'pre_assign':  [],
                           'post_assign': []}
        if nodetype not in _spec_map:
            _exc('Invalid task type "%s"' % nodetype)
        if nodetype == 'start-task':
            name = 'start'
        if name == '':
            _exc('Invalid task name "%s"' % name)
        if name in read_specs:
            _exc('Duplicate task name "%s"' % name)
        if cancel != '' and cancel != u'0':
            kwargs['cancel'] = True
        if success != '' and success != u'0':
            kwargs['success'] = True
        if times != '':
            kwargs['times'] = int(times)
        if times_field != '':
            kwargs['times'] = operators.Attrib(times_field)
        if threshold != '':
            kwargs['threshold'] = int(threshold)
        if threshold_field != '':
            kwargs['threshold'] = operators.Attrib(threshold_field)
        if file != '':
            kwargs['file'] = file
        if file_field != '':
            kwargs['file'] = operators.Attrib(file_field)
        if nodetype == 'choose':
            kwargs['choice'] = []
        if nodetype == 'trigger':
            context = [context]
        if mutex != '':
            context = mutex

        # Walk through the children of the node.
        successors  = []
        for node in start_node.childNodes:
            if node.nodeType != minidom.Node.ELEMENT_NODE:
                continue
            if node.nodeName == 'description':
                kwargs['description'] = node.firstChild.nodeValue
            elif node.nodeName == 'successor' \
              or node.nodeName == 'default-successor':
                if node.firstChild is None:
                    _exc('Empty %s tag' % node.nodeName)
                successors.append((None, node.firstChild.nodeValue))
            elif node.nodeName == 'conditional-successor':
                successors.append(self._deserialize_condition(workflow, node))
            elif node.nodeName == 'define':
                key, value = self._deserialize_data(workflow, node)
                kwargs['defines'][key] = value
            # "property" tag exists for backward compatibility.
            elif node.nodeName == 'data' or node.nodeName == 'property':
                key, value = self._deserialize_data(workflow, node)
                kwargs['data'][key] = value
            elif node.nodeName == 'pre-assign':
                kwargs['pre_assign'].append(self._deserialize_assign(workflow, node))
            elif node.nodeName == 'post-assign':
                kwargs['post_assign'].append(self._deserialize_assign(workflow, node))
            elif node.nodeName == 'in':
                kwargs['in_assign'] = self._deserialize_assign_list(workflow, node)
            elif node.nodeName == 'out':
                kwargs['out_assign'] = self._deserialize_assign_list(workflow, node)
            elif node.nodeName == 'cancel':
                if node.firstChild is None:
                    _exc('Empty %s tag' % node.nodeName)
                if context == '':
                    context = []
                elif type(context) != type([]):
                    context = [context]
                context.append(node.firstChild.nodeValue)
            elif node.nodeName == 'lock':
                if node.firstChild is None:
                    _exc('Empty %s tag' % node.nodeName)
                kwargs['lock'].append(node.firstChild.nodeValue)
            elif node.nodeName == 'pick':
                if node.firstChild is None:
                    _exc('Empty %s tag' % node.nodeName)
                kwargs['choice'].append(node.firstChild.nodeValue)
            else:
                _exc('Unknown node: %s' % node.nodeName)

        # Create a new instance of the task spec.
        module = _spec_map[nodetype]
        if nodetype == 'start-task':
            spec = module(workflow, **kwargs)
        elif nodetype == 'multi-instance' or nodetype == 'thread-split':
            if times == '' and times_field == '':
                _exc('Missing "times" or "times-field" in "%s"' % name)
            elif times != '' and times_field != '':
                _exc('Both, "times" and "times-field" in "%s"' % name)
            spec = module(workflow, name, **kwargs)
        elif context == '':
            spec = module(workflow, name, **kwargs)
        else:
            spec = module(workflow, name, context, **kwargs)

        read_specs[name] = spec, successors

    def deserialize_workflow_spec(self, s_state, filename=None):
        """
        Reads the workflow from the given XML structure and returns a
        WorkflowSpec instance.
        """
        dom  = minidom.parseString(s_state)
        node = dom.getElementsByTagName('process-definition')[0]
        name = node.getAttribute('name')
        if name == '':
            _exc('%s without a name attribute' % node.nodeName)

        # Read all task specs and create a list of successors.
        workflow_spec = specs.WorkflowSpec(name, filename)
        del workflow_spec.task_specs['Start']
        end           = specs.Simple(workflow_spec, 'End'), []
        read_specs    = dict(end = end)
        for child_node in node.childNodes:
            if child_node.nodeType != minidom.Node.ELEMENT_NODE:
                continue
            if child_node.nodeName == 'name':
                workflow_spec.name = child_node.firstChild.nodeValue
            elif child_node.nodeName == 'description':
                workflow_spec.description = child_node.firstChild.nodeValue
            elif child_node.nodeName.lower() in _spec_map:
                self._deserialize_task_spec(workflow_spec, child_node, read_specs)
            else:
                _exc('Unknown node: %s' % child_node.nodeName)

        # Remove the default start-task from the workflow.
        workflow_spec.start = read_specs['start'][0]

        # Connect all task specs.
        for name in read_specs:
            spec, successors = read_specs[name]
            for condition, successor_name in successors:
                if successor_name not in read_specs:
                    _exc('Unknown successor: "%s"' % successor_name)
                successor, foo = read_specs[successor_name]
                if condition is None:
                    spec.connect(successor)
                else:
                    spec.connect_if(condition, successor)
        return workflow_spec

########NEW FILE########
__FILENAME__ = Task
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import logging
import time
from uuid import uuid4
from SpiffWorkflow.exceptions import WorkflowException

LOG = logging.getLogger(__name__)


class Task(object):
    """
    Used internally for composing a tree that represents the path that
    is taken (or predicted) within the workflow.

    Each Task has a state. For an explanation, consider the following task
    specification::

                                    ,-> Simple (default choice)
        StartTask -> ExclusiveChoice
                                    `-> Simple

    The initial task tree for this specification looks like so::

                                                   ,-> Simple LIKELY
        StartTask WAITING -> ExclusiveChoice FUTURE
                                                   `-> Simple MAYBE

    The following states may exist::

        - FUTURE: The task will definitely be reached in the future,
        regardless of which choices the user makes within the workflow.

        - LIKELY: The task may or may not be reached in the future. It
        is likely because the specification lists it as the default
        option for the ExclusiveChoice.

        - MAYBE: The task may or may not be reached in the future. It
        is not LIKELY, because the specification does not list it as the
        default choice for the ExclusiveChoice.

        - WAITING: The task is still waiting for an event before it
        completes. For example, a Join task will be WAITING until all
        predecessors are completed.

        - READY: The conditions for completing the task are now satisfied.
        Usually this means that all predecessors have completed and the
        task may now be completed using
        L{Workflow.complete_task_from_id()}.

        - CANCELLED: The task was cancelled by a CancelTask or
        CancelWorkflow task.

        - COMPLETED: The task was regularily completed.

    Note that the LIKELY and MAYBE tasks are merely predicted/guessed, so
    those tasks may be removed from the tree at runtime later. They are
    created to allow for visualizing the workflow at a time where
    the required decisions have not yet been made.
    """
    # Note: The states in this list are ordered in the sequence in which
    # they may appear. Do not change.
    MAYBE     =  1
    LIKELY    =  2
    FUTURE    =  4
    WAITING   =  8
    READY     = 16
    COMPLETED = 32
    CANCELLED = 64

    FINISHED_MASK      = CANCELLED | COMPLETED
    DEFINITE_MASK      = FUTURE | WAITING | READY | FINISHED_MASK
    PREDICTED_MASK     = FUTURE | LIKELY | MAYBE
    NOT_FINISHED_MASK  = PREDICTED_MASK | WAITING | READY
    ANY_MASK           = FINISHED_MASK | NOT_FINISHED_MASK

    state_names = {FUTURE:    'FUTURE',
                   WAITING:   'WAITING',
                   READY:     'READY',
                   CANCELLED: 'CANCELLED',
                   COMPLETED: 'COMPLETED',
                   LIKELY:    'LIKELY',
                   MAYBE:     'MAYBE'}

    class Iterator(object):
        """
        This is a tree iterator that supports filtering such that a client
        may walk through all tasks that have a specific state.
        """
        def __init__(self, current, filter=None):
            """
            Constructor.
            """
            self.filter = filter
            self.path = [current]

        def __iter__(self):
            return self

        def _next(self):
            # Make sure that the end is not yet reached.
            if len(self.path) == 0:
                raise StopIteration()

            # If the current task has children, the first child is the next item.
            # If the current task is LIKELY, and predicted tasks are not
            # specificly searched, we can ignore the children, because predicted
            # tasks should only have predicted children.
            current = self.path[-1]
            ignore_task = False
            if self.filter is not None:
                search_predicted = self.filter & Task.LIKELY != 0
                is_predicted = current.state & Task.LIKELY != 0
                ignore_task = is_predicted and not search_predicted
            if current.children and not ignore_task:
                self.path.append(current.children[0])
                if self.filter is not None and current.state & self.filter == 0:
                    return None
                return current

            # Ending up here, this task has no children. Crop the path until we
            # reach a task that has unvisited children, or until we hit the end.
            while True:
                old_child = self.path.pop(-1)
                if len(self.path) == 0:
                    break

                # If this task has a sibling, choose it.
                parent = self.path[-1]
                pos = parent.children.index(old_child)
                if len(parent.children) > pos + 1:
                    self.path.append(parent.children[pos + 1])
                    break
            if self.filter is not None and current.state & self.filter == 0:
                return None
            return current

        def next(self):
            # By using this loop we avoid an (expensive) recursive call.
            while True:
                next = self._next()
                if next is not None:
                    return next

        # Python 3 iterator protocol
        __next__ = next

    # Pool for assigning a unique thread id to every new Task.
    thread_id_pool = 0

    def __init__(self, workflow, task_spec, parent=None, state=MAYBE):
        """
        Constructor.
        """
        assert workflow  is not None
        assert task_spec is not None
        self.workflow = workflow
        self.parent = parent
        self.children = []
        self._state = state
        self.triggered = False
        self.state_history = [state]
        self.log = []
        self.task_spec = task_spec
        self.id = uuid4()
        self.thread_id = self.__class__.thread_id_pool
        self.last_state_change = time.time()
        self.data = {}
        self.internal_data = {}
        if parent is not None:
            self.parent._child_added_notify(self)

    def __repr__(self):
        return '<Task object (%s) in state %s at %s>' % (
            self.task_spec.name,
            self.get_state_name(),
            hex(id(self)))

    def _getstate(self):
        return self._state

    def _setstate(self, value, force=False):
        """
        Setting force to True allows for changing a state after it
        COMPLETED. This would otherwise be invalid.
        """
        if self._state == value:
            return
        if value < self._state and not force:
            raise WorkflowException(self.task_spec,
                                    'state went from %s to %s!' % (
                                        self.get_state_name(),
                                        self.state_names[value]))
        if __debug__:
            old = self.get_state_name()
        self._state = value
        if __debug__:
            self.log.append("Moving '%s' from %s to %s" % (self.get_name(),
                    old, self.get_state_name()))
        self.state_history.append(value)
        LOG.debug("Moving '%s' (spec=%s) from %s to %s" % (self.get_name(),
                    self.task_spec.name, old, self.get_state_name()))

    def _delstate(self):
        del self._state

    state = property(_getstate, _setstate, _delstate, "State property.")

    def __iter__(self):
        return Task.Iterator(self)

    def __setstate__(self, dict):
        self.__dict__.update(dict)
        # If unpickled in the same Python process in which a workflow
        # (Task) is built through the API, we need to make sure
        # that there will not be any ID collisions.
        if dict['thread_id'] >= self.__class__.thread_id_pool:
            self.__class__.thread_id_pool = dict['thread_id']

    def _get_root(self):
        """
        Returns the top level parent.
        """
        if self.parent is None:
            return self
        return self.parent._get_root()

    def _get_depth(self):
        depth = 0
        task = self.parent
        while task is not None:
            depth += 1
            task = task.parent
        return depth

    def _child_added_notify(self, child):
        """
        Called by another Task to let us know that a child was added.
        """
        assert child is not None
        self.children.append(child)

    def _drop_children(self):
        drop = []
        for child in self.children:
            if not child._is_finished():
                drop.append(child)
            else:
                child._drop_children()
        for task in drop:
            self.children.remove(task)

    def _set_state(self, state, force=True):
        """
        Setting force to True allows for changing a state after it
        COMPLETED. This would otherwise be invalid.
        """
        self._setstate(state, True)
        self.last_state_change = time.time()

    def _has_state(self, state):
        """
        Returns True if the Task has the given state flag set.
        """
        return (self.state & state) != 0

    def _is_finished(self):
        return self._has_state(self.FINISHED_MASK)

    def _is_predicted(self):
        return self._has_state(self.PREDICTED_MASK)

    def _is_definite(self):
        return self._has_state(self.DEFINITE_MASK)

    def _add_child(self, task_spec, state=MAYBE):
        """
        Adds a new child and assigns the given TaskSpec to it.

        :type  task_spec: TaskSpec
        :param task_spec: The task spec that is assigned to the new child.
        :type  state: integer
        :param state: The bitmask of states for the new child.
        :rtype:  Task
        :returns: The new child task.
        """
        if task_spec is None:
            raise ValueError(self, '_add_child() requires a TaskSpec')
        if self._is_predicted() and state & self.PREDICTED_MASK == 0:
            msg = 'Attempt to add non-predicted child to predicted task'
            raise WorkflowException(self.task_spec, msg)
        task = Task(self.workflow, task_spec, self, state=state)
        task.thread_id = self.thread_id
        if state == self.READY:
            task._ready()
        return task

    def _assign_new_thread_id(self, recursive=True):
        """
        Assigns a new thread id to the task.

        :type  recursive: boolean
        :param recursive: Whether to assign the id to children recursively.
        :rtype:  boolean
        :returns: The new thread id.
        """
        self.__class__.thread_id_pool += 1
        self.thread_id = self.__class__.thread_id_pool
        if not recursive:
            return self.thread_id
        for child in self:
            child.thread_id = self.thread_id
        return self.thread_id

    def _sync_children(self, task_specs, state=MAYBE):
        """
        This method syncs up the task's children with the given list of task
        specs. In other words::

            - Add one child for each given TaskSpec, unless that child already
              exists.
            - Remove all children for which there is no spec in the given list,
              unless it is a "triggered" task.

        .. note::

           It is an error if the task has a non-predicted child that is
           not given in the TaskSpecs.

        :type  task_specs: list(TaskSpec)
        :param task_specs: The list of task specs that may become children.
        :type  state: integer
        :param state: The bitmask of states for the new children.
        """
        LOG.debug("Updating children for %s" % self.get_name())
        if task_specs is None:
            raise ValueError('"task_specs" argument is None')
        add = task_specs[:]

        # Create a list of all children that are no longer needed.
        remove = []
        for child in self.children:
            # Triggered tasks are never removed.
            if child.triggered:
                continue

            # Check whether the task needs to be removed.
            if child.task_spec in add:
                add.remove(child.task_spec)
                continue

            # Non-predicted tasks must not be removed, so they HAVE to be in
            # the given task spec list.
            if child._is_definite():
                raise WorkflowException(self.task_spec,
                    'removal of non-predicted child %s' % repr(child))
            remove.append(child)

        # Remove and add the children accordingly.
        for child in remove:
            self.children.remove(child)
        for task_spec in add:
            self._add_child(task_spec, state)

    def _set_likely_task(self, task_specs):
        if not isinstance(task_specs, list):
            task_specs = [task_specs]
        for task_spec in task_specs:
            for child in self.children:
                if child.task_spec != task_spec:
                    continue
                if child._is_definite():
                    continue
                child._set_state(self.LIKELY)
                return

    def _is_descendant_of(self, parent):
        """
        Returns True if parent is in the list of ancestors, returns False
        otherwise.

        :type  parent: Task
        :param parent: The parent that is searched in the ancestors.
        :rtype:  boolean
        :returns: Whether the parent was found.
        """
        if self.parent is None:
            return False
        if self.parent == parent:
            return True
        return self.parent._is_descendant_of(parent)

    def _find_child_of(self, parent_task_spec):
        """
        Returns the ancestor that has a task with the given task spec
        as a parent.
        If no such ancestor was found, the root task is returned.

        :type  parent_task_spec: TaskSpec
        :param parent_task_spec: The wanted ancestor.
        :rtype:  Task
        :returns: The child of the given ancestor.
        """
        if self.parent is None:
            return self
        if self.parent.task_spec == parent_task_spec:
            return self
        return self.parent._find_child_of(parent_task_spec)

    def _find_any(self, task_spec):
        """
        Returns any descendants that have the given task spec assigned.

        :type  task_spec: TaskSpec
        :param task_spec: The wanted task spec.
        :rtype:  list(Task)
        :returns: The tasks objects that are attached to the given task spec.
        """
        tasks = []
        if self.task_spec == task_spec:
            tasks.append(self)
        for child in self:
            if child.task_spec != task_spec:
                continue
            tasks.append(child)
        return tasks

    def _find_ancestor(self, task_spec):
        """
        Returns the ancestor that has the given task spec assigned.
        If no such ancestor was found, the root task is returned.

        :type  task_spec: TaskSpec
        :param task_spec: The wanted task spec.
        :rtype:  Task
        :returns: The ancestor.
        """
        if self.parent is None:
            return self
        if self.parent.task_spec == task_spec:
            return self.parent
        return self.parent._find_ancestor(task_spec)

    def _find_ancestor_from_name(self, name):
        """
        Returns the ancestor that has a task with the given name assigned.
        Returns None if no such ancestor was found.

        :type  name: str
        :param name: The name of the wanted task.
        :rtype:  Task
        :returns: The ancestor.
        """
        if self.parent is None:
            return None
        if self.parent.get_name() == name:
            return self.parent
        return self.parent._find_ancestor_from_name(name)

    def _ready(self):
        """
        Marks the task as ready for execution.
        """
        if self._has_state(self.COMPLETED) or self._has_state(self.CANCELLED):
            return
        self._set_state(self.READY)
        self.task_spec._on_ready(self)

    def get_name(self):
        return str(self.task_spec.name)

    def get_description(self):
        return str(self.task_spec.description)

    def get_state(self):
        """
        Returns this Task's state.
        """
        return self.state

    def get_state_name(self):
        """
        Returns a textual representation of this Task's state.
        """
        state_name = []
        for state, name in self.state_names.items():
            if self._has_state(state):
                state_name.append(name)
        return '|'.join(state_name)

    def get_spec_data(self, name=None, default=None):
        """
        Returns the value of the spec data with the given name, or the given
        default value if the spec data does not exist.

        :type  name: str
        :param name: The name of the spec data field.
        :type  default: obj
        :param default: Return this value if the spec data does not exist.
        :rtype:  obj
        :returns: The value of the spec data.
        """
        return self.task_spec.get_data(name, default)

    def _set_internal_data(self, **kwargs):
        """
        Defines the given attribute/value pairs.
        """
        self.internal_data.update(kwargs)

    def _get_internal_data(self, name, default=None):
        return self.internal_data.get(name, default)

    def set_data(self, **kwargs):
        """
        Defines the given attribute/value pairs.
        """
        self.data.update(kwargs)

    def _inherit_data(self):
        """
        Inherits the data from the parent.
        """
        LOG.debug("'%s' inheriting data from '%s'" % (self.get_name(),
                self.parent.get_name()),
                extra=dict(data=self.parent.data))
        self.set_data(**self.parent.data)

    def get_data(self, name, default=None):
        """
        Returns the value of the data field with the given name, or the given
        default value if the data field does not exist.

        :type  name: str
        :param name: A data field name.
        :type  default: obj
        :param default: Return this value if the data field does not exist.
        :rtype:  obj
        :returns: The value of the data field
        """
        return self.data.get(name, default)

    def cancel(self):
        """
        Cancels the item if it was not yet completed, and removes
        any children that are LIKELY.
        """
        if self._is_finished():
            for child in self.children:
                child.cancel()
            return
        self._set_state(self.CANCELLED)
        self._drop_children()
        self.task_spec._on_cancel(self)

    def complete(self):
        """
        Called by the associated task to let us know that its state
        has changed (e.g. from FUTURE to COMPLETED.)
        """
        self._set_state(self.COMPLETED)
        return self.task_spec._on_complete(self)

    def trigger(self, *args):
        """
        If recursive is True, the state is applied to the tree recursively.
        """
        self.task_spec._on_trigger(self, *args)

    def get_dump(self, indent=0, recursive=True):
        """
        Returns the subtree as a string for debugging.

        :rtype:  str
        :returns: The debug information.
        """
        dbg  = (' ' * indent * 2)
        dbg += '%s/'           % self.id
        dbg += '%s:'           % self.thread_id
        dbg += ' Task of %s'   % self.get_name()
        if self.task_spec.description:
            dbg += ' (%s)'   % self.get_description()
        dbg += ' State: %s'    % self.get_state_name()
        dbg += ' Children: %s' % len(self.children)
        if recursive:
            for child in self.children:
                dbg += '\n' + child.get_dump(indent + 1)
        return dbg

    def dump(self, indent=0):
        """
        Prints the subtree as a string for debugging.
        """
        print(self.get_dump())

########NEW FILE########
__FILENAME__ = compat
try:
    # python 2
    from mutex import mutex
    import ConfigParser as configparser

except ImportError:
    # python 3
    import configparser
    from threading import Lock

    class mutex(object):
        def __init__(self):
            self.lock = Lock()

        def lock(self):
            raise NotImplementedError

        def test(self):
            has = self.lock.acquire(blocking=False)
            if has:
                self.lock.release()

            return has

        def testandset(self):
            return self.lock.acquire(blocking=False)

        def unlock(self):
            self.lock.release()

########NEW FILE########
__FILENAME__ = event
# -*- coding: utf-8 -*-
from __future__ import division
################################################
# DO NOT EDIT THIS FILE.
# THIS CODE IS TAKE FROM Exscript.util:
#   https://github.com/knipknap/exscript/tree/master/src/Exscript/util
################################################

# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
A simple signal/event mechanism.
"""
from threading     import Lock
from SpiffWorkflow.util import weakmethod

class Event(object):
    """
    A simple signal/event mechanism, to be used like this::

        def mycallback(arg, **kwargs):
            print arg, kwargs['foo']

        myevent = Event()
        myevent.connect(mycallback)
        myevent.emit('test', foo = 'bar')
        # Or just: myevent('test', foo = 'bar')
    """

    def __init__(self):
        """
        Constructor.
        """
        # To save memory, we do NOT init the subscriber attributes with
        # lists. Unfortunately this makes a lot of the code in this class
        # more messy than it should be, but events are used so widely in
        # Exscript that this change makes a huge difference to the memory
        # footprint.
        self.lock             = None
        self.weak_subscribers = None
        self.hard_subscribers = None

    def __call__(self, *args, **kwargs):
        """
        Like emit().
        """
        return self.emit(*args, **kwargs)

    def connect(self, callback, *args, **kwargs):
        """
        Connects the event with the given callback.
        When the signal is emitted, the callback is invoked.

        .. note::

            The signal handler is stored with a hard reference, so you
            need to make sure to call L{disconnect()} if you want the handler
            to be garbage collected.

        :type  callback: object
        :param callback: The callback function.
        :type  args: tuple
        :param args: Optional arguments passed to the callback.
        :type  kwargs: dict
        :param kwargs: Optional keyword arguments passed to the callback.
        """
        if self.is_connected(callback):
            raise AttributeError('callback is already connected')
        if self.hard_subscribers is None:
            self.hard_subscribers = []
        self.hard_subscribers.append((callback, args, kwargs))

    def listen(self, callback, *args, **kwargs):
        """
        Like L{connect()}, but uses a weak reference instead of a
        normal reference.
        The signal is automatically disconnected as soon as the handler
        is garbage collected.

        .. note::

            Storing signal handlers as weak references means that if
            your handler is a local function, it may be garbage collected. To
            prevent this, use L{connect()} instead.

        :type  callback: object
        :param callback: The callback function.
        :type  args: tuple
        :param args: Optional arguments passed to the callback.
        :type  kwargs: dict
        :param kwargs: Optional keyword arguments passed to the callback.
        :rtype:  L{Exscript.util.weakmethod.WeakMethod}
        :returns: The newly created weak reference to the callback.
        """
        if self.lock is None:
            self.lock = Lock()
        with self.lock:
            if self.is_connected(callback):
                raise AttributeError('callback is already connected')
            if self.weak_subscribers is None:
                self.weak_subscribers = []
            ref = weakmethod.ref(callback, self._try_disconnect)
            self.weak_subscribers.append((ref, args, kwargs))
        return ref

    def n_subscribers(self):
        """
        Returns the number of connected subscribers.

        :rtype:  int
        :returns: The number of subscribers.
        """
        hard = self.hard_subscribers and len(self.hard_subscribers) or 0
        weak = self.weak_subscribers and len(self.weak_subscribers) or 0
        return hard + weak

    def _hard_callbacks(self):
        return [s[0] for s in self.hard_subscribers]

    def _weakly_connected_index(self, callback):
        if self.weak_subscribers is None:
            return None
        weak = [s[0].get_function() for s in self.weak_subscribers]
        try:
            return weak.index(callback)
        except ValueError:
            return None

    def is_connected(self, callback):
        """
        Returns True if the event is connected to the given function.

        :type  callback: object
        :param callback: The callback function.
        :rtype:  bool
        :returns: Whether the signal is connected to the given function.
        """
        index = self._weakly_connected_index(callback)
        if index is not None:
            return True
        if self.hard_subscribers is None:
            return False
        return callback in self._hard_callbacks()

    def emit(self, *args, **kwargs):
        """
        Emits the signal, passing the given arguments to the callbacks.
        If one of the callbacks returns a value other than None, no further
        callbacks are invoked and the return value of the callback is
        returned to the caller of emit().

        :type  args: tuple
        :param args: Optional arguments passed to the callbacks.
        :type  kwargs: dict
        :param kwargs: Optional keyword arguments passed to the callbacks.
        :rtype:  object
        :returns: Returns None if all callbacks returned None. Returns
                 the return value of the last invoked callback otherwise.
        """
        if self.hard_subscribers is not None:
            for callback, user_args, user_kwargs in self.hard_subscribers:
                kwargs.update(user_kwargs)
                result = callback(*args + user_args, **kwargs)
                if result is not None:
                    return result

        if self.weak_subscribers is not None:
            for callback, user_args, user_kwargs in self.weak_subscribers:
                kwargs.update(user_kwargs)

                # Even though WeakMethod notifies us when the underlying
                # function is destroyed, and we remove the item from the
                # the list of subscribers, there is no guarantee that
                # this notification has already happened because the garbage
                # collector may run while this loop is executed.
                # Disabling the garbage collector temporarily also does
                # not work, because other threads may be trying to do
                # the same, causing yet another race condition.
                # So the only solution is to skip such functions.
                function = callback.get_function()
                if function is None:
                    continue
                result = function(*args + user_args, **kwargs)
                if result is not None:
                    return result

    def _try_disconnect(self, ref):
        """
        Called by the weak reference when its target dies.
        In other words, we can assert that self.weak_subscribers is not
        None at this time.
        """
        with self.lock:
            weak = [s[0] for s in self.weak_subscribers]
            try:
                index = weak.index(ref)
            except ValueError:
                # subscriber was already removed by a call to disconnect()
                pass
            else:
                self.weak_subscribers.pop(index)

    def disconnect(self, callback):
        """
        Disconnects the signal from the given function.

        :type  callback: object
        :param callback: The callback function.
        """
        if self.weak_subscribers is not None:
            with self.lock:
                index = self._weakly_connected_index(callback)
                if index is not None:
                    self.weak_subscribers.pop(index)[0]
        if self.hard_subscribers is not None:
            try:
                index = self._hard_callbacks().index(callback)
            except ValueError:
                pass
            else:
                self.hard_subscribers.pop(index)

    def disconnect_all(self):
        """
        Disconnects all connected functions from all signals.
        """
        self.hard_subscribers = None
        self.weak_subscribers = None

########NEW FILE########
__FILENAME__ = impl
# -*- coding: utf-8 -*-
from __future__ import division
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import sys

def get_class(full_class_name):
    parts = full_class_name.rsplit('.', 1)
    module_name = parts[0]
    class_name = parts[1]
    __import__(module_name)
    return getattr(sys.modules[module_name], class_name)

########NEW FILE########
__FILENAME__ = weakmethod
# -*- coding: utf-8 -*-
from __future__ import division
################################################
# DO NOT EDIT THIS FILE.
# THIS CODE IS TAKE FROM Exscript.util:
#   https://github.com/knipknap/exscript/tree/master/src/Exscript/util
################################################

# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Weak references to bound and unbound methods.
"""
import weakref

class DeadMethodCalled(Exception):
    """
    Raised by L{WeakMethod} if it is called when the referenced object
    is already dead.
    """
    pass

class WeakMethod(object):
    """
    Do not create this class directly; use L{ref()} instead.
    """
    __slots__ = 'name', 'callback'

    def __init__(self, name, callback):
        """
        Constructor. Do not use directly, use L{ref()} instead.
        """
        self.name     = name
        self.callback = callback

    def _dead(self, ref):
        if self.callback is not None:
            self.callback(self)

    def get_function(self):
        """
        Returns the referenced method/function if it is still alive.
        Returns None otherwise.

        :rtype:  callable|None
        :returns: The referenced function if it is still alive.
        """
        raise NotImplementedError()

    def isalive(self):
        """
        Returns True if the referenced function is still alive, False
        otherwise.

        :rtype:  bool
        :returns: Whether the referenced function is still alive.
        """
        return self.get_function() is not None

    def __call__(self, *args, **kwargs):
        """
        Proxied to the underlying function or method. Raises L{DeadMethodCalled}
        if the referenced function is dead.

        :rtype:  object
        :returns: Whatever the referenced function returned.
        """
        method = self.get_function()
        if method is None:
            raise DeadMethodCalled('method called on dead object ' + self.name)
        method(*args, **kwargs)

class _WeakMethodBound(WeakMethod):
    __slots__ = 'name', 'callback', 'f', 'c'

    def __init__(self, f, callback):
        name = f.__self__.__class__.__name__ + '.' + f.__func__.__name__
        WeakMethod.__init__(self, name, callback)
        self.f = f.__func__
        self.c = weakref.ref(f.__self__, self._dead)

    def get_function(self):
        cls = self.c()
        if cls is None:
            return None
        return getattr(cls, self.f.__name__)

class _WeakMethodFree(WeakMethod):
    __slots__ = 'name', 'callback', 'f'

    def __init__(self, f, callback):
        WeakMethod.__init__(self, f.__class__.__name__, callback)
        self.f = weakref.ref(f, self._dead)

    def get_function(self):
        return self.f()

def ref(function, callback = None):
    """
    Returns a weak reference to the given method or function.
    If the callback argument is not None, it is called as soon
    as the referenced function is garbage deleted.

    :type  function: callable
    :param function: The function to reference.
    :type  callback: callable
    :param callback: Called when the function dies.
    """
    try:
        function.__func__
    except AttributeError:
        return _WeakMethodFree(function, callback)
    return _WeakMethodBound(function, callback)

########NEW FILE########
__FILENAME__ = version
# -*- coding: utf-8 -*-
from __future__ import division
"""
Warning: This file is automatically generated.
"""
__version__ = 'DEVELOPMENT'

########NEW FILE########
__FILENAME__ = Workflow
# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2007 Samuel Abels
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
import logging
from .util.compat import mutex

from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow import specs
from SpiffWorkflow.util.event import Event
from .Task import Task

LOG = logging.getLogger(__name__)

class Workflow(object):
    """
    The engine that executes a workflow.
    It is a essentially a facility for managing all branches.
    A Workflow is also the place that holds the data of a running workflow.
    """

    def __init__(self, workflow_spec, deserializing=False, **kwargs):
        """
        Constructor.

        :param deserializing: set to true when deserializing to avoid
        generating tasks twice (and associated problems with multiple
        hierarchies of tasks)
        """
        assert workflow_spec is not None
        LOG.debug("__init__ Workflow instance: %s" % self.__str__())
        self.spec = workflow_spec
        self.data = {}
        self.outer_workflow = kwargs.get('parent', self)
        self.locks = {}
        self.last_task = None
        if deserializing:
            assert 'Root' in workflow_spec.task_specs
            root = workflow_spec.task_specs['Root']  # Probably deserialized
        else:
            if 'Root' in workflow_spec.task_specs:
                root = workflow_spec.task_specs['Root']
            else:
                root = specs.Simple(workflow_spec, 'Root')
        self.task_tree = Task(self, root)
        self.success = True
        self.debug = False

        # Events.
        self.completed_event = Event()

        # Prevent the root task from being executed.
        self.task_tree.state = Task.COMPLETED
        start = self.task_tree._add_child(self.spec.start, state=Task.FUTURE)

        self.spec.start._predict(start)
        if 'parent' not in kwargs:
            start.task_spec._update_state(start)
        #start.dump()

    def is_completed(self):
        """
        Returns True if the entire Workflow is completed, False otherwise.
        """
        mask = Task.NOT_FINISHED_MASK
        iter = Task.Iterator(self.task_tree, mask)
        try:
            iter.next()
        except:
            # No waiting tasks found.
            return True
        return False

    def _get_waiting_tasks(self):
        waiting = Task.Iterator(self.task_tree, Task.WAITING)
        return [w for w in waiting]

    def _task_completed_notify(self, task):
        if task.get_name() == 'End':
            self.data.update(task.data)
        # Update the state of every WAITING task.
        for thetask in self._get_waiting_tasks():
            thetask.task_spec._update_state(thetask)
        if self.completed_event.n_subscribers() == 0:
            # Since is_completed() is expensive it makes sense to bail
            # out if calling it is not necessary.
            return
        if self.is_completed():
            self.completed_event(self)

    def _get_mutex(self, name):
        if name not in self.locks:
            self.locks[name] = mutex()
        return self.locks[name]

    def get_data(self, name, default=None):
        """
        Returns the value of the data field with the given name, or the given
        default value if the data field does not exist.

        :type  name: string
        :param name: A data field name.
        :type  default: obj
        :param default: Return this value if the data field does not exist.
        :rtype:  obj
        :returns: The value of the data field.
        """
        return self.data.get(name, default)

    def cancel(self, success=False):
        """
        Cancels all open tasks in the workflow.

        :type  success: boolean
        :param success: Whether the Workflow should be marked as successfully
                        completed.
        """
        self.success = success
        cancel = []
        mask = Task.NOT_FINISHED_MASK
        for task in Task.Iterator(self.task_tree, mask):
            cancel.append(task)
        for task in cancel:
            task.cancel()

    def get_task_spec_from_name(self, name):
        """
        Returns the task spec with the given name.

        :type  name: string
        :param name: The name of the task.
        :rtype:  TaskSpec
        :returns: The task spec with the given name.
        """
        return self.spec.get_task_spec_from_name(name)

    def get_task(self, id):
        """
        Returns the task with the given id.

        :type id:integer
        :param id: The id of a task.
        :rtype: Task
        :returns: The task with the given id.
        """
        tasks = [task for task in self.get_tasks() if task.id == id]
        return tasks[0] if len(tasks) == 1 else None

    def get_tasks_from_spec_name(self, name):
        """
        Returns all tasks whose spec has the given name.

        @type name: str
        @param name: The name of a task spec.
        @rtype: Task
        @return: The task that relates to the spec with the given name.
        """
        return [task for task in self.get_tasks()
                if task.task_spec.name == name]

    def get_tasks(self, state=Task.ANY_MASK):
        """
        Returns a list of Task objects with the given state.

        :type  state: integer
        :param state: A bitmask of states.
        :rtype:  list[Task]
        :returns: A list of tasks.
        """
        return [t for t in Task.Iterator(self.task_tree, state)]

    def complete_task_from_id(self, task_id):
        """
        Runs the task with the given id.

        :type  task_id: integer
        :param task_id: The id of the Task object.
        """
        if task_id is None:
            raise WorkflowException(self.spec, 'task_id is None')
        for task in self.task_tree:
            if task.id == task_id:
                return task.complete()
        msg = 'A task with the given task_id (%s) was not found' % task_id
        raise WorkflowException(self.spec, msg)

    def complete_next(self, pick_up=True):
        """
        Runs the next task.
        Returns True if completed, False otherwise.

        :type  pick_up: boolean
        :param pick_up: When True, this method attempts to choose the next
                        task not by searching beginning at the root, but by
                        searching from the position at which the last call
                        of complete_next() left off.
        :rtype:  boolean
        :returns: True if all tasks were completed, False otherwise.
        """
        # Try to pick up where we left off.
        blacklist = []
        if pick_up and self.last_task is not None:
            try:
                iter = Task.Iterator(self.last_task, Task.READY)
                next = iter.next()
            except:
                next = None
            self.last_task = None
            if next is not None:
                if next.complete():
                    self.last_task = next
                    return True
                blacklist.append(next)

        # Walk through all ready tasks.
        for task in Task.Iterator(self.task_tree, Task.READY):
            for blacklisted_task in blacklist:
                if task._is_descendant_of(blacklisted_task):
                    continue
            if task.complete():
                self.last_task = task
                return True
            blacklist.append(task)

        # Walk through all waiting tasks.
        for task in Task.Iterator(self.task_tree, Task.WAITING):
            task.task_spec._update_state(task)
            if not task._has_state(Task.WAITING):
                self.last_task = task
                return True
        return False

    def complete_all(self, pick_up=True):
        """
        Runs all branches until completion. This is a convenience wrapper
        around complete_next(), and the pick_up argument is passed along.

        :type  pick_up: boolean
        :param pick_up: Passed on to each call of complete_next().
        """
        while self.complete_next(pick_up):
            pass

    def get_dump(self):
        """
        Returns a complete dump of the current internal task tree for
        debugging.

        :rtype:  string
        :returns: The debug information.
        """
        return self.task_tree.get_dump()

    def dump(self):
        """
        Like get_dump(), but prints the output to the terminal instead of
        returning it.
        """
        print(self.task_tree.dump())

    def serialize(self, serializer, **kwargs):
        """
        Serializes a Workflow instance using the provided serializer.

        :type  serializer: L{SpiffWorkflow.storage.Serializer}
        :param serializer: The serializer to use.
        :type  kwargs: dict
        :param kwargs: Passed to the serializer.
        :rtype:  object
        :returns: The serialized workflow.
        """
        return serializer.serialize_workflow(self, **kwargs)

    @classmethod
    def deserialize(cls, serializer, s_state, **kwargs):
        """
        Deserializes a Workflow instance using the provided serializer.

        :type  serializer: L{SpiffWorkflow.storage.Serializer}
        :param serializer: The serializer to use.
        :type  s_state: object
        :param s_state: The serialized workflow.
        :type  kwargs: dict
        :param kwargs: Passed to the serializer.
        :rtype:  Workflow
        :returns: The workflow instance.
        """
        return serializer.deserialize_workflow(s_state, **kwargs)

########NEW FILE########
__FILENAME__ = ActionManagementTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import unittest
import datetime
import time
from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.BpmnWorkflow import BpmnWorkflow
from tests.SpiffWorkflow.bpmn.BpmnWorkflowTestCase import BpmnWorkflowTestCase

__author__ = 'matth'

class ActionManagementTest(BpmnWorkflowTestCase):
    def setUp(self):
        self.spec = self.load_spec()
        self.workflow = BpmnWorkflow(self.spec)

        start_time = datetime.datetime.now() + datetime.timedelta(seconds=0.5)
        finish_time = datetime.datetime.now() + datetime.timedelta(seconds=1.5)

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.workflow.get_tasks(Task.READY)[0].set_data(start_time=start_time, finish_time=finish_time)

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/*.bpmn20.xml', 'Action Management')

    def testRunThroughHappy(self):
        self.do_next_exclusive_step("Review Action", choice='Approve')
        self.workflow.do_engine_steps()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals('NEW ACTION', self.workflow.get_tasks(Task.READY)[0].get_data('script_output'))
        self.assertEquals('Cancel Action (if necessary)', self.workflow.get_tasks(Task.READY)[0].task_spec.description)

        time.sleep(0.6)
        self.workflow.refresh_waiting_tasks()
        self.workflow.do_engine_steps()
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))
        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step("Start Work")
        self.workflow.do_engine_steps()

        self.do_next_named_step("Complete Work", choice="Done")
        self.workflow.do_engine_steps()

        self.assertTrue(self.workflow.is_completed())

    def testRunThroughOverdue(self):
        self.do_next_exclusive_step("Review Action", choice='Approve')
        self.workflow.do_engine_steps()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals('Cancel Action (if necessary)', self.workflow.get_tasks(Task.READY)[0].task_spec.description)

        time.sleep(0.6)
        self.workflow.refresh_waiting_tasks()
        self.workflow.do_engine_steps()
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))
        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step("Start Work")
        self.workflow.do_engine_steps()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))
        self.assertEquals('Finish Time', self.workflow.get_tasks(Task.WAITING)[0].task_spec.description)
        time.sleep(1.1)
        self.workflow.refresh_waiting_tasks()
        self.workflow.do_engine_steps()
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))
        self.assertNotEquals('Finish Time', self.workflow.get_tasks(Task.WAITING)[0].task_spec.description)

        overdue_escalation_task = [t for t in self.workflow.get_tasks() if t.task_spec.description=='Overdue Escalation']
        self.assertEquals(1, len(overdue_escalation_task))
        overdue_escalation_task = overdue_escalation_task[0]
        self.assertEquals(Task.COMPLETED, overdue_escalation_task.state)
        self.assertEquals('ACTION OVERDUE', overdue_escalation_task.get_data('script_output'))

        self.do_next_named_step("Complete Work", choice="Done")
        self.workflow.do_engine_steps()

        self.assertTrue(self.workflow.is_completed())

    def testRunThroughCancel(self):

        self.do_next_exclusive_step("Review Action", choice='Cancel')
        self.workflow.do_engine_steps()

        self.assertTrue(self.workflow.is_completed())

    def testRunThroughCancelAfterApproved(self):
        self.do_next_exclusive_step("Review Action", choice='Approve')
        self.workflow.do_engine_steps()

        self.do_next_named_step("Cancel Action (if necessary)")
        self.workflow.do_engine_steps()

        self.assertTrue(self.workflow.is_completed())
        self.assertEquals('ACTION CANCELLED', self.workflow.get_data('script_output'))

    def testRunThroughCancelAfterWorkStarted(self):
        self.do_next_exclusive_step("Review Action", choice='Approve')
        self.workflow.do_engine_steps()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        time.sleep(0.6)
        self.workflow.refresh_waiting_tasks()
        self.workflow.do_engine_steps()
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))
        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step("Start Work")
        self.workflow.do_engine_steps()

        self.do_next_named_step("Cancel Action (if necessary)")
        self.workflow.do_engine_steps()

        self.assertTrue(self.workflow.is_completed())
        self.assertEquals('ACTION CANCELLED', self.workflow.get_data('script_output'))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ActionManagementTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = ApprovalsTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import unittest
from SpiffWorkflow.bpmn.BpmnWorkflow import BpmnWorkflow
from tests.SpiffWorkflow.bpmn.BpmnWorkflowTestCase import BpmnWorkflowTestCase

__author__ = 'matth'

class ApprovalsTest(BpmnWorkflowTestCase):
    def setUp(self):
        self.spec = self.load_workflow1_spec()

    def load_workflow1_spec(self):
        #Start (StartTask:0xb6b4204cL)
        #   --> Approvals.First_Approval_Wins (CallActivity)
        #          --> Start (StartTask:0xb6b4266cL)
        #          |      --> First_Approval_Wins.Supervisor_Approval (ManualTask)
        #          |      |      --> First_Approval_Wins.Supervisor_Approved (EndEvent)
        #          |      |             --> First_Approval_Wins.EndJoin (EndJoin)
        #          |      |                    --> End (Simple)
        #          |      --> First_Approval_Wins.Manager_Approval (ManualTask)
        #          |             --> First_Approval_Wins.Manager_Approved (EndEvent)
        #          |                    --> [shown earlier] First_Approval_Wins.EndJoin (EndJoin)
        #          --> Approvals.First_Approval_Wins_Done (ManualTask)
        #                 --> Approvals.Gateway4 (ParallelGateway)
        #                        --> Approvals.Manager_Approval__P_ (ManualTask)
        #                        |      --> Approvals.Gateway5 (ParallelGateway)
        #                        |             --> Approvals.Parallel_Approvals_Done (ManualTask)
        #                        |                    --> Approvals.Parallel_SP (CallActivity)
        #                        |                           --> Start (StartTask)
        #                        |                           |      --> Parallel_Approvals_SP.Step1 (ManualTask)
        #                        |                           |      |      --> Parallel_Approvals_SP.Supervisor_Approval (ManualTask)
        #                        |                           |      |             --> Parallel_Approvals_SP.End2 (EndEvent)
        #                        |                           |      |                    --> Parallel_Approvals_SP.EndJoin (EndJoin)
        #                        |                           |      |                           --> End (Simple)
        #                        |                           |      --> Parallel_Approvals_SP.Manager_Approval (ManualTask)
        #                        |                           |             --> [shown earlier] Parallel_Approvals_SP.End2 (EndEvent)
        #                        |                           --> Approvals.Parallel_SP_Done (ManualTask)
        #                        |                                  --> Approvals.End1 (EndEvent)
        #                        |                                         --> Approvals.EndJoin (EndJoin)
        #                        |                                                --> End (Simple)
        #                        --> Approvals.Supervisor_Approval__P_ (ManualTask)
        #                               --> [shown earlier] Approvals.Gateway5 (ParallelGateway)
        return self.load_workflow_spec('Approvals.bpmn', 'Approvals')

    def testRunThroughHappy(self):

        self.workflow = BpmnWorkflow(self.spec)

        self.do_next_named_step('First_Approval_Wins.Manager_Approval')
        self.do_next_exclusive_step('Approvals.First_Approval_Wins_Done')

        self.do_next_named_step('Approvals.Manager_Approval__P_')
        self.do_next_named_step('Approvals.Supervisor_Approval__P_')
        self.do_next_exclusive_step('Approvals.Parallel_Approvals_Done')

        self.do_next_named_step('Parallel_Approvals_SP.Step1')
        self.do_next_named_step('Parallel_Approvals_SP.Manager_Approval')
        self.do_next_named_step('Parallel_Approvals_SP.Supervisor_Approval')
        self.do_next_exclusive_step('Approvals.Parallel_SP_Done')

    def testRunThroughHappyOtherOrders(self):

        self.workflow = BpmnWorkflow(self.spec)

        self.do_next_named_step('First_Approval_Wins.Supervisor_Approval')
        self.do_next_exclusive_step('Approvals.First_Approval_Wins_Done')

        self.do_next_named_step('Approvals.Supervisor_Approval__P_')
        self.do_next_named_step('Approvals.Manager_Approval__P_')
        self.do_next_exclusive_step('Approvals.Parallel_Approvals_Done')

        self.do_next_named_step('Parallel_Approvals_SP.Manager_Approval')
        self.do_next_named_step('Parallel_Approvals_SP.Step1')
        self.do_next_named_step('Parallel_Approvals_SP.Supervisor_Approval')
        self.do_next_exclusive_step('Approvals.Parallel_SP_Done')

    def testSaveRestore(self):

        self.workflow = BpmnWorkflow(self.spec)

        self.do_next_named_step('First_Approval_Wins.Manager_Approval')
        self.save_restore()
        self.do_next_exclusive_step('Approvals.First_Approval_Wins_Done')

        self.save_restore()
        self.do_next_named_step('Approvals.Supervisor_Approval__P_')
        self.do_next_named_step('Approvals.Manager_Approval__P_')
        self.do_next_exclusive_step('Approvals.Parallel_Approvals_Done')

        self.save_restore()
        self.do_next_named_step('Parallel_Approvals_SP.Manager_Approval')
        self.do_next_exclusive_step('Parallel_Approvals_SP.Step1')
        self.do_next_exclusive_step('Parallel_Approvals_SP.Supervisor_Approval')
        self.do_next_exclusive_step('Approvals.Parallel_SP_Done')


    def testSaveRestoreWaiting(self):

        self.workflow = BpmnWorkflow(self.spec)

        self.do_next_named_step('First_Approval_Wins.Manager_Approval')
        self.save_restore()
        self.do_next_exclusive_step('Approvals.First_Approval_Wins_Done')

        self.save_restore()
        self.do_next_named_step('Approvals.Supervisor_Approval__P_')
        self.save_restore()
        self.do_next_named_step('Approvals.Manager_Approval__P_')
        self.save_restore()
        self.do_next_exclusive_step('Approvals.Parallel_Approvals_Done')

        self.save_restore()
        self.do_next_named_step('Parallel_Approvals_SP.Manager_Approval')
        self.save_restore()
        self.do_next_exclusive_step('Parallel_Approvals_SP.Step1')
        self.save_restore()
        self.do_next_exclusive_step('Parallel_Approvals_SP.Supervisor_Approval')
        self.save_restore()
        self.do_next_exclusive_step('Approvals.Parallel_SP_Done')

    def testReadonlyWaiting(self):

        self.workflow = BpmnWorkflow(self.spec)

        self.do_next_named_step('First_Approval_Wins.Manager_Approval')

        readonly = self.get_read_only_workflow()
        self.assertEquals(1, len(readonly.get_ready_user_tasks()))
        self.assertEquals('Approvals.First_Approval_Wins_Done', readonly.get_ready_user_tasks()[0].task_spec.name)
        self.assertRaises(AssertionError, readonly.do_engine_steps)
        self.assertRaises(AssertionError, readonly.refresh_waiting_tasks)
        self.assertRaises(AssertionError, readonly.accept_message, 'Cheese')
        self.assertRaises(AssertionError, readonly.get_ready_user_tasks()[0].complete)

        self.do_next_exclusive_step('Approvals.First_Approval_Wins_Done')

        readonly = self.get_read_only_workflow()
        self.assertEquals(2, len(readonly.get_ready_user_tasks()))
        self.assertEquals(['Approvals.Manager_Approval__P_', 'Approvals.Supervisor_Approval__P_'], sorted(t.task_spec.name for t in readonly.get_ready_user_tasks()))
        self.assertRaises(AssertionError, readonly.get_ready_user_tasks()[0].complete)

        self.do_next_named_step('Approvals.Supervisor_Approval__P_')

        readonly = self.get_read_only_workflow()
        self.assertEquals(1, len(readonly.get_ready_user_tasks()))
        self.assertEquals('Approvals.Manager_Approval__P_', readonly.get_ready_user_tasks()[0].task_spec.name)
        self.assertRaises(AssertionError, readonly.get_ready_user_tasks()[0].complete)
        self.do_next_named_step('Approvals.Manager_Approval__P_')

        readonly = self.get_read_only_workflow()
        self.assertEquals(1, len(readonly.get_ready_user_tasks()))
        self.assertEquals('Approvals.Parallel_Approvals_Done', readonly.get_ready_user_tasks()[0].task_spec.name)
        self.assertRaises(AssertionError, readonly.get_ready_user_tasks()[0].complete)
        self.do_next_exclusive_step('Approvals.Parallel_Approvals_Done')

        readonly = self.get_read_only_workflow()
        self.assertEquals(2, len(readonly.get_ready_user_tasks()))
        self.assertEquals(['Parallel_Approvals_SP.Manager_Approval', 'Parallel_Approvals_SP.Step1'], sorted(t.task_spec.name for t in readonly.get_ready_user_tasks()))
        self.assertRaises(AssertionError, readonly.get_ready_user_tasks()[0].complete)
        self.do_next_named_step('Parallel_Approvals_SP.Manager_Approval')

        readonly = self.get_read_only_workflow()
        self.assertEquals(1, len(readonly.get_ready_user_tasks()))
        self.assertEquals('Parallel_Approvals_SP.Step1', readonly.get_ready_user_tasks()[0].task_spec.name)
        self.assertRaises(AssertionError, readonly.get_ready_user_tasks()[0].complete)
        self.do_next_exclusive_step('Parallel_Approvals_SP.Step1')

        readonly = self.get_read_only_workflow()
        self.assertEquals(1, len(readonly.get_ready_user_tasks()))
        self.assertEquals('Parallel_Approvals_SP.Supervisor_Approval', readonly.get_ready_user_tasks()[0].task_spec.name)
        self.assertRaises(AssertionError, readonly.get_ready_user_tasks()[0].complete)
        self.do_next_exclusive_step('Parallel_Approvals_SP.Supervisor_Approval')

        readonly = self.get_read_only_workflow()
        self.assertEquals(1, len(readonly.get_ready_user_tasks()))
        self.assertEquals('Approvals.Parallel_SP_Done', readonly.get_ready_user_tasks()[0].task_spec.name)
        self.assertRaises(AssertionError, readonly.get_ready_user_tasks()[0].complete)
        self.do_next_exclusive_step('Approvals.Parallel_SP_Done')

        readonly = self.get_read_only_workflow()
        self.assertEquals(0, len(readonly.get_ready_user_tasks()))
        self.assertEquals(0, len(readonly.get_waiting_tasks()))


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ApprovalsTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = BpmnLoaderForTests
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
from SpiffWorkflow.bpmn.specs.CallActivity import CallActivity
from SpiffWorkflow.bpmn.specs.EndEvent import EndEvent
from SpiffWorkflow.bpmn.specs.ExclusiveGateway import ExclusiveGateway
from SpiffWorkflow.bpmn.specs.UserTask import UserTask
from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnParser
from SpiffWorkflow.bpmn.parser.task_parsers import UserTaskParser, EndEventParser, CallActivityParser
from SpiffWorkflow.bpmn.parser.util import full_tag
from SpiffWorkflow.operators import Assign

__author__ = 'matth'

#This provides some extensions to the BPMN parser that make it easier to implement testcases

class TestUserTask(UserTask):

    def get_user_choices(self):
        if not self.outputs:
            return []
        assert len(self.outputs) == 1
        next_node = self.outputs[0]
        if isinstance(next_node, ExclusiveGateway):
            return next_node.get_outgoing_sequence_names()
        return self.get_outgoing_sequence_names()

    def do_choice(self, task, choice):
        task.set_data(choice=choice)
        task.complete()

class TestEndEvent(EndEvent):

    def _on_complete_hook(self, my_task):
        my_task.set_data(end_event=self.description)
        super(TestEndEvent, self)._on_complete_hook(my_task)

class TestCallActivity(CallActivity):

    def __init__(self, parent, name, **kwargs):
        super(TestCallActivity, self).__init__(parent, name, out_assign=[Assign('choice', 'end_event')], **kwargs)

class TestBpmnParser(BpmnParser):
    OVERRIDE_PARSER_CLASSES = {
        full_tag('userTask')            : (UserTaskParser, TestUserTask),
        full_tag('endEvent')            : (EndEventParser, TestEndEvent),
        full_tag('callActivity')        : (CallActivityParser, TestCallActivity),
        }

    def parse_condition(self, condition_expression, outgoing_task, outgoing_task_node, sequence_flow_node, condition_expression_node, task_parser):
        cond = super(TestBpmnParser, self).parse_condition(condition_expression,outgoing_task, outgoing_task_node, sequence_flow_node, condition_expression_node, task_parser)
        if cond is not None:
            return cond
        return "choice == '%s'" % sequence_flow_node.get('name', None)

########NEW FILE########
__FILENAME__ = BpmnWorkflowTestCase
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import logging
import os
import unittest
from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.storage.BpmnSerializer import BpmnSerializer
from SpiffWorkflow.bpmn.storage.CompactWorkflowSerializer import CompactWorkflowSerializer
from tests.SpiffWorkflow.bpmn.PackagerForTests import PackagerForTests

__author__ = 'matth'


class BpmnWorkflowTestCase(unittest.TestCase):

    def load_workflow_spec(self, filename, process_name):
        f = os.path.join(os.path.dirname(__file__), 'data', filename)

        return BpmnSerializer().deserialize_workflow_spec(
            PackagerForTests.package_in_memory(process_name, f))

    def do_next_exclusive_step(self, step_name, with_save_load=False, set_attribs=None, choice=None):
        if with_save_load:
            self.save_restore()

        self.workflow.do_engine_steps()
        tasks = self.workflow.get_tasks(Task.READY)
        self._do_single_step(step_name, tasks, set_attribs, choice)

    def do_next_named_step(self, step_name, with_save_load=False, set_attribs=None, choice=None, only_one_instance=True):
        if with_save_load:
            self.save_restore()

        self.workflow.do_engine_steps()
        step_name_path = step_name.split("|")
        def is_match(t):
            if not (t.task_spec.name == step_name_path[-1] or t.task_spec.description == step_name_path[-1]):
                return False
            for parent_name in step_name_path[:-1]:
                p = t.parent
                found = False
                while (p and p != p.parent):
                    if (p.task_spec.name == parent_name or p.task_spec.description == parent_name):
                        found = True
                        break
                    p = p.parent
                if not found:
                    return False
            return True

        tasks = list([t for t in self.workflow.get_tasks(Task.READY) if is_match(t)])

        self._do_single_step(step_name_path[-1], tasks, set_attribs, choice, only_one_instance=only_one_instance)

    def assertTaskNotReady(self, step_name):
        tasks = list([t for t in self.workflow.get_tasks(Task.READY) if t.task_spec.name == step_name or t.task_spec.description == step_name])
        self.assertEquals([], tasks)

    def _do_single_step(self, step_name, tasks, set_attribs=None, choice=None, only_one_instance=True):

        if only_one_instance:
            self.assertEqual(len(tasks), 1, 'Did not find one task for \'%s\' (got %d)' % (step_name, len(tasks)))
        else:
            self.assertNotEqual(len(tasks), 0, 'Did not find any tasks for \'%s\'' % (step_name))

        self.assertTrue(tasks[0].task_spec.name == step_name or tasks[0].task_spec.description == step_name,
            'Expected step %s, got %s (%s)' % (step_name, tasks[0].task_spec.description, tasks[0].task_spec.name))
        if not set_attribs:
            set_attribs = {}

        if choice:
            set_attribs['choice'] = choice

        if set_attribs:
            tasks[0].set_data(**set_attribs)
        tasks[0].complete()

    def save_restore(self):
        state = self._get_workflow_state()
        logging.debug('Saving state: %s', state)
        before_dump = self.workflow.get_dump()
        self.restore(state)
        #We should still have the same state:
        after_dump = self.workflow.get_dump()
        after_state = self._get_workflow_state()
        if state != after_state:
            logging.debug("Before save:\n%s", before_dump)
            logging.debug("After save:\n%s", after_dump)
        self.assertEquals(state, after_state)

    def restore(self, state):
        self.workflow = CompactWorkflowSerializer().deserialize_workflow(state, workflow_spec=self.spec)

    def get_read_only_workflow(self):
        state = self._get_workflow_state()
        return CompactWorkflowSerializer().deserialize_workflow(state, workflow_spec=self.spec, read_only=True)

    def _get_workflow_state(self):
        self.workflow.do_engine_steps()
        self.workflow.refresh_waiting_tasks()
        return CompactWorkflowSerializer().serialize_workflow(self.workflow, include_spec=False)

########NEW FILE########
__FILENAME__ = InvalidWorkflowsTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import unittest
from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException
from tests.SpiffWorkflow.bpmn.BpmnWorkflowTestCase import BpmnWorkflowTestCase

__author__ = 'matth'

class InvalidWorkflowsTest(BpmnWorkflowTestCase):

    def testDisconnectedBoundaryEvent(self):
        try:
            self.load_workflow_spec('Invalid-Workflows/Disconnected-Boundary-Event.bpmn20.xml', 'Disconnected Boundary Event')
            self.fail("self.load_workflow_spec('Invalid-Workflows/Disconnected-Boundary-Event.bpmn20.xml', 'Disconnected Boundary Event') should fail.")
        except ValidationException as ex:
            self.assertTrue('This might be a Boundary Event that has been disconnected' in ('%r'%ex),
                '\'This might be a Boundary Event that has been disconnected\' should be a substring of error message: \'%r\'' % ex)
#            self.assertTrue('line 64' in ('%r'%ex),
#                '\'line 64\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('Disconnected-Boundary-Event.bpmn20.xml' in ('%r'%ex),
                '\'Disconnected-Boundary-Event.bpmn20.xml\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('intermediateCatchEvent' in ('%r'%ex),
                '\'intermediateCatchEvent\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('sid-84C7CE67-D0B6-486A-B097-486DA924FF9D' in ('%r'%ex),
                '\'sid-84C7CE67-D0B6-486A-B097-486DA924FF9D\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('Test Message' in ('%r'%ex),
                '\'Test Message\' should be a substring of error message: \'%r\'' % ex)

    def testNoStartEvent(self):
        try:
            self.load_workflow_spec('Invalid-Workflows/No-Start-Event.bpmn20.xml', 'No Start Event')
            self.fail("self.load_workflow_spec('Invalid-Workflows/No-Start-Event.bpmn20.xml', 'No Start Event') should fail.")
        except ValidationException as ex:
            self.assertTrue('No start event found' in ('%r'%ex),
                '\'No start event found\' should be a substring of error message: \'%r\'' % ex)
#            self.assertTrue('line 10' in ('%r'%ex),
#                '\'line 10\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('No-Start-Event.bpmn20.xml' in ('%r'%ex),
                '\'No-Start-Event.bpmn20.xml\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('process' in ('%r'%ex),
                '\'process\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('sid-669ddebf-4196-41ee-8b04-bcc90bc5f983' in ('%r'%ex),
                '\'sid-669ddebf-4196-41ee-8b04-bcc90bc5f983\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('No Start Event' in ('%r'%ex),
                '\'No Start Event\' should be a substring of error message: \'%r\'' % ex)

    def testMultipleStartEvents(self):
        try:
            self.load_workflow_spec('Invalid-Workflows/Multiple-Start-Events.bpmn20.xml', 'Multiple Start Events')
            self.fail("self.load_workflow_spec('Invalid-Workflows/Multiple-Start-Events.bpmn20.xml', 'Multiple Start Events') should fail.")
        except ValidationException as ex:
            self.assertTrue('Only one Start Event is supported in each process' in ('%r'%ex),
                '\'Only one Start Event is supported in each process\' should be a substring of error message: \'%r\'' % ex)
#            self.assertTrue('line 10' in ('%r'%ex),
#                '\'line 10\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('Multiple-Start-Events.bpmn20.xml' in ('%r'%ex),
                '\'Multiple-Start-Events.bpmn20.xml\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('process' in ('%r'%ex),
                '\'process\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('sid-1e457abc-2ee3-4d60-a4df-d2ddf5b18c2b' in ('%r'%ex),
                '\'sid-1e457abc-2ee3-4d60-a4df-d2ddf5b18c2b\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('Multiple Start Events' in ('%r'%ex),
                '\'Multiple Start Events\' should be a substring of error message: \'%r\'' % ex)

    def testSubprocessNotFound(self):
        try:
            self.load_workflow_spec('Invalid-Workflows/Subprocess-Not-Found.bpmn20.xml', 'Subprocess Not Found')
            self.fail("self.load_workflow_spec('Invalid-Workflows/Subprocess-Not-Found.bpmn20.xml', 'Subprocess Not Found') should fail.")
        except ValidationException as ex:
            self.assertTrue('No matching process definition found for \'Missing subprocess\'.' in ('%r'%ex),
                '\'No matching process definition found for \'Missing subprocess\'.\' should be a substring of error message: \'%r\'' % ex)
#            self.assertTrue('line 35' in ('%r'%ex),
#                '\'line 35\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('Subprocess-Not-Found.bpmn20.xml' in ('%r'%ex),
                '\'Subprocess-Not-Found.bpmn20.xml\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('callActivity' in ('%r'%ex),
                '\'callActivity\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('sid-617B0E1F-42DB-4D40-9B4C-ED631BF6E43A' in ('%r'%ex),
                '\'sid-617B0E1F-42DB-4D40-9B4C-ED631BF6E43A\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('Subprocess for Subprocess Not Found' in ('%r'%ex),
                '\'Subprocess for Subprocess Not Found\' should be a substring of error message: \'%r\'' % ex)

    def testRecursiveSubprocesses(self):
        try:
            self.load_workflow_spec('Invalid-Workflows/Recursive-Subprocesses.bpmn20.xml', 'Recursive Subprocesses')
            self.fail("self.load_workflow_spec('Invalid-Workflows/Recursive-Subprocesses.bpmn20.xml', 'Recursive Subprocesses') should fail.")
        except ValidationException as ex:
            self.assertTrue('Recursive call Activities are not supported' in ('%r'%ex),
                '\'Recursive call Activities are not supported\' should be a substring of error message: \'%r\'' % ex)
#            self.assertTrue('line 97' in ('%r'%ex),
#                '\'line 97\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('Recursive-Subprocesses.bpmn20.xml' in ('%r'%ex),
                '\'Recursive-Subprocesses.bpmn20.xml\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('callActivity' in ('%r'%ex),
                '\'callActivity\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('sid-10515BFA-0CEC-4B8B-B3BE-E717DEBA6D89' in ('%r'%ex),
                '\'sid-10515BFA-0CEC-4B8B-B3BE-E717DEBA6D89\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('Recursive Subprocesses (callback!)' in ('%r'%ex),
                '\'Recursive Subprocesses (callback!)\' should be a substring of error message: \'%r\'' % ex)

    def testUnsupportedTask(self):
        try:
            self.load_workflow_spec('Invalid-Workflows/Unsupported-Task.bpmn20.xml', 'Unsupported Task')
            self.fail("self.load_workflow_spec('Invalid-Workflows/Unsupported-Task.bpmn20.xml', 'Unsupported Task') should fail.")
        except ValidationException as ex:
            self.assertTrue('There is no support implemented for this task type' in ('%r'%ex),
                '\'There is no support implemented for this task type\' should be a substring of error message: \'%r\'' % ex)
#            self.assertTrue('line 63' in ('%r'%ex),
#                '\'line 63\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('Unsupported-Task.bpmn20.xml' in ('%r'%ex),
                '\'Unsupported-Task.bpmn20.xml\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('businessRuleTask' in ('%r'%ex),
                '\'businessRuleTask\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('sid-75EEAB28-3B69-4282-B91A-0F3C97931834' in ('%r'%ex),
                '\'sid-75EEAB28-3B69-4282-B91A-0F3C97931834\' should be a substring of error message: \'%r\'' % ex)
            self.assertTrue('Business Rule Task' in ('%r'%ex),
                '\'Business Rule Task\' should be a substring of error message: \'%r\'' % ex)
def suite():
    return unittest.TestLoader().loadTestsFromTestCase(InvalidWorkflowsTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
########NEW FILE########
__FILENAME__ = MessageInterruptsSpTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import unittest
import datetime
import time
from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.BpmnWorkflow import BpmnWorkflow
from tests.SpiffWorkflow.bpmn.BpmnWorkflowTestCase import BpmnWorkflowTestCase

__author__ = 'matth'

class MessageInterruptsSpTest(BpmnWorkflowTestCase):
    def setUp(self):
        self.spec = self.load_spec()

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/*.bpmn20.xml', 'Message Interrupts SP')

    def testRunThroughHappySaveAndRestore(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.save_restore()

        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.do_next_exclusive_step('Do Something In a Subprocess')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.do_next_exclusive_step('Ack Subprocess Done')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testRunThroughInterruptSaveAndRestore(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.save_restore()

        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.workflow.accept_message('Test Message')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.do_next_exclusive_step('Acknowledge  SP Interrupt Message')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(MessageInterruptsSpTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = MessageInterruptsTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import unittest
import datetime
import time
from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.BpmnWorkflow import BpmnWorkflow
from tests.SpiffWorkflow.bpmn.BpmnWorkflowTestCase import BpmnWorkflowTestCase

__author__ = 'matth'


class MessageInterruptsTest(BpmnWorkflowTestCase):
    def setUp(self):
        self.spec = self.load_spec()
        #self.spec.dump()

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/*.bpmn20.xml', 'Test Workflows')

    def testRunThroughHappySaveAndRestore(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.save_restore()
        self.do_next_exclusive_step('Select Test', choice='Message Interrupts')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.do_next_exclusive_step('Do Something That Takes A Long Time')
        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.WAITING)))

        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))


    def testRunThroughMessageInterruptSaveAndRestore(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.save_restore()
        self.do_next_exclusive_step('Select Test', choice='Message Interrupts')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.workflow.accept_message('Test Message')
        self.save_restore()

        self.workflow.do_engine_steps()
        self.save_restore()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.WAITING)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_exclusive_step('Acknowledge Interrupt Message')
        self.save_restore()

        self.workflow.do_engine_steps()
        self.save_restore()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))


    def testRunThroughHappy(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.do_next_exclusive_step('Select Test', choice='Message Interrupts')
        self.workflow.do_engine_steps()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.do_next_exclusive_step('Do Something That Takes A Long Time')

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.WAITING)))

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))


    def testRunThroughMessageInterrupt(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.do_next_exclusive_step('Select Test', choice='Message Interrupts')
        self.workflow.do_engine_steps()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.workflow.accept_message('Test Message')

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.WAITING)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_exclusive_step('Acknowledge Interrupt Message')

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(MessageInterruptsTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = MessageNonInterruptsSpTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import unittest
import datetime
import time
from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.BpmnWorkflow import BpmnWorkflow
from tests.SpiffWorkflow.bpmn.BpmnWorkflowTestCase import BpmnWorkflowTestCase

__author__ = 'matth'

class MessageNonInterruptsSpTest(BpmnWorkflowTestCase):
    def setUp(self):
        self.spec = self.load_spec()

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/*.bpmn20.xml', 'Message Non Interrupt SP')

    def testRunThroughHappySaveAndRestore(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.save_restore()

        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.do_next_exclusive_step('Do Something In a Subprocess')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.do_next_exclusive_step('Ack Subprocess Done')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testRunThroughMessageSaveAndRestore(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.save_restore()

        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.workflow.accept_message('Test Message')

        self.do_next_named_step('Do Something In a Subprocess')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.do_next_named_step('Ack Subprocess Done')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.do_next_named_step('Acknowledge SP Parallel Message')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testRunThroughMessageOrder2SaveAndRestore(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.save_restore()

        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.workflow.accept_message('Test Message')

        self.do_next_named_step('Do Something In a Subprocess')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.do_next_named_step('Acknowledge SP Parallel Message')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.do_next_named_step('Ack Subprocess Done')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testRunThroughMessageOrder3SaveAndRestore(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.save_restore()

        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.workflow.accept_message('Test Message')

        self.do_next_named_step('Acknowledge SP Parallel Message')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.do_next_named_step('Do Something In a Subprocess')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.do_next_named_step('Ack Subprocess Done')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(MessageNonInterruptsSpTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = MessageNonInterruptTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import unittest
import datetime
import time
from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.BpmnWorkflow import BpmnWorkflow
from tests.SpiffWorkflow.bpmn.BpmnWorkflowTestCase import BpmnWorkflowTestCase

__author__ = 'matth'

class MessageNonInterruptTest(BpmnWorkflowTestCase):
    def setUp(self):
        self.spec = self.load_spec()
        #self.spec.dump()

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/*.bpmn20.xml', 'Test Workflows')

    def testRunThroughHappySaveAndRestore(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.save_restore()
        self.do_next_exclusive_step('Select Test', choice='Message Non Interrupt')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.do_next_exclusive_step('Do Something That Takes A Long Time')
        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.WAITING)))

        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))


    def testRunThroughMessageInterruptSaveAndRestore(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.save_restore()
        self.do_next_exclusive_step('Select Test', choice='Message Non Interrupt')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.workflow.accept_message('Test Message')
        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.WAITING)))
        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Acknowledge Non-Interrupt Message')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Do Something That Takes A Long Time')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))


    def testRunThroughHappy(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.do_next_exclusive_step('Select Test', choice='Message Non Interrupt')
        self.workflow.do_engine_steps()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.do_next_exclusive_step('Do Something That Takes A Long Time')

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.WAITING)))

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))


    def testRunThroughMessageInterrupt(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.do_next_exclusive_step('Select Test', choice='Message Non Interrupt')
        self.workflow.do_engine_steps()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.workflow.accept_message('Test Message')

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.WAITING)))
        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Acknowledge Non-Interrupt Message')

        self.workflow.do_engine_steps()
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.do_next_named_step('Do Something That Takes A Long Time')

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testRunThroughMessageInterruptOtherOrder(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.do_next_exclusive_step('Select Test', choice='Message Non Interrupt')
        self.workflow.do_engine_steps()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.workflow.accept_message('Test Message')

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.WAITING)))
        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Do Something That Takes A Long Time')

        self.workflow.do_engine_steps()
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Acknowledge Non-Interrupt Message')

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testRunThroughMessageInterruptOtherOrderSaveAndRestore(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.save_restore()
        self.do_next_exclusive_step('Select Test', choice='Message Non Interrupt')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.workflow.accept_message('Test Message')
        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.WAITING)))
        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Do Something That Takes A Long Time')
        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Acknowledge Non-Interrupt Message')
        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(MessageNonInterruptTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = MessagesTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import unittest
import datetime
import time
from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.BpmnWorkflow import BpmnWorkflow
from tests.SpiffWorkflow.bpmn.BpmnWorkflowTestCase import BpmnWorkflowTestCase

__author__ = 'matth'


class MessagesTest(BpmnWorkflowTestCase):
    def setUp(self):
        self.spec = self.load_spec()

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/*.bpmn20.xml', 'Test Workflows')

    def testRunThroughHappy(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.do_next_exclusive_step('Select Test', choice='Messages')
        self.workflow.do_engine_steps()
        self.assertEquals([], self.workflow.get_tasks(Task.READY))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))
        self.workflow.accept_message('Wrong Message')
        self.assertEquals([], self.workflow.get_tasks(Task.READY))
        self.workflow.accept_message('Test Message')
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))

        self.assertEquals('Test Message', self.workflow.get_tasks(Task.READY)[0].task_spec.description)

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testRunThroughSaveAndRestore(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.do_next_exclusive_step('Select Test', choice='Messages')
        self.workflow.do_engine_steps()

        self.save_restore()

        self.assertEquals([], self.workflow.get_tasks(Task.READY))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))
        self.workflow.accept_message('Wrong Message')
        self.assertEquals([], self.workflow.get_tasks(Task.READY))
        self.workflow.accept_message('Test Message')

        self.save_restore()

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(MessagesTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = PackagerForTests
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division

from io import BytesIO

from SpiffWorkflow.bpmn.storage.Packager import Packager, main
from tests.SpiffWorkflow.bpmn.BpmnLoaderForTests import TestBpmnParser

__author__ = 'matth'

class PackagerForTests(Packager):

    PARSER_CLASS = TestBpmnParser

    @classmethod
    def package_in_memory(cls, workflow_name, workflow_files, editor='signavio'):
        s = BytesIO()
        p = cls(s, workflow_name, meta_data=[], editor=editor)
        p.add_bpmn_files_by_glob(workflow_files)
        p.create_package()
        return s.getvalue()

if __name__ == '__main__':
    main(packager_class=PackagerForTests)

########NEW FILE########
__FILENAME__ = ParallelTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import unittest
import logging
import sys
from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.BpmnWorkflow import BpmnWorkflow
from tests.SpiffWorkflow.bpmn.BpmnWorkflowTestCase import BpmnWorkflowTestCase

__author__ = 'matth'


class ParallelJoinLongTest(BpmnWorkflowTestCase):
    def setUp(self):
        self.spec = self.load_spec()

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/Parallel-Join-Long.bpmn20.xml', 'Parallel Join Long')

    def testRunThroughAlternating(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Thread 1 - Choose', choice='Yes', with_save_load=True)
        self.workflow.do_engine_steps()
        self.do_next_named_step('Thread 2 - Choose', choice='Yes', with_save_load=True)
        self.workflow.do_engine_steps()

        for i in range(1,13):
            self.do_next_named_step('Thread 1 - Task %d' % i, with_save_load=True)
            self.workflow.do_engine_steps()
            self.do_next_named_step('Thread 2 - Task %d' % i, with_save_load=True)
            self.workflow.do_engine_steps()

        self.do_next_named_step('Done', with_save_load=True)
        self.workflow.do_engine_steps()

        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testRunThroughThread1First(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Thread 1 - Choose', choice='Yes', with_save_load=True)
        self.workflow.do_engine_steps()
        for i in range(1,13):
            self.do_next_named_step('Thread 1 - Task %d' % i)
            self.workflow.do_engine_steps()

        self.assertRaises(AssertionError, self.do_next_named_step, 'Done')
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.do_next_named_step('Thread 2 - Choose', choice='Yes', with_save_load=True)
        self.workflow.do_engine_steps()
        for i in range(1,13):
            self.do_next_named_step('Thread 2 - Task %d' % i, with_save_load=True)
            self.workflow.do_engine_steps()

        self.do_next_named_step('Done', with_save_load=True)
        self.workflow.do_engine_steps()

        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

class ParallelJoinLongInclusiveTest(ParallelJoinLongTest):
    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/Parallel-Join-Long-Inclusive.bpmn20.xml', 'Parallel Join Long Inclusive')

    def testRunThroughThread1FirstThenNo(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Thread 1 - Choose', choice='Yes', with_save_load=True)
        self.workflow.do_engine_steps()
        for i in range(1,13):
            self.do_next_named_step('Thread 1 - Task %d' % i)
            self.workflow.do_engine_steps()

        self.assertRaises(AssertionError, self.do_next_named_step, 'Done')
        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        self.do_next_named_step('Thread 2 - Choose', choice='No', with_save_load=True)
        self.workflow.do_engine_steps()
        self.do_next_named_step('Done', with_save_load=True)
        self.workflow.do_engine_steps()
        self.do_next_named_step('Thread 2 - No Task', with_save_load=True)
        self.workflow.do_engine_steps()


        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))


    def testNoFirstThenThread1(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Thread 2 - Choose', choice='No', with_save_load=True)
        self.workflow.do_engine_steps()

        self.do_next_named_step('Thread 1 - Choose', choice='Yes', with_save_load=True)
        self.workflow.do_engine_steps()
        for i in range(1,13):
            self.do_next_named_step('Thread 1 - Task %d' % i)
            self.workflow.do_engine_steps()

        self.do_next_named_step('Done', with_save_load=True)
        self.workflow.do_engine_steps()

        self.do_next_named_step('Thread 2 - No Task', with_save_load=True)
        self.workflow.do_engine_steps()


        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

class ParallelMultipleSplitsTest(BpmnWorkflowTestCase):
    def setUp(self):
        self.spec = self.load_spec()

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/Parallel-Multiple-Splits.bpmn20.xml', 'Parallel Multiple Splits')

    def testRunThroughAlternating(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Do First')
        self.workflow.do_engine_steps()
        self.do_next_named_step('SP 1 - Choose', choice='Yes')
        self.workflow.do_engine_steps()
        self.do_next_named_step('SP 2 - Choose', choice='Yes')
        self.workflow.do_engine_steps()
        self.do_next_named_step('SP 3 - Choose', choice='Yes')
        self.workflow.do_engine_steps()
        self.do_next_named_step('SP 1 - Yes Task')
        self.workflow.do_engine_steps()
        self.do_next_named_step('SP 2 - Yes Task')
        self.workflow.do_engine_steps()
        self.do_next_named_step('SP 3 - Yes Task')
        self.workflow.do_engine_steps()

        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()

        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

class ParallelThenExlusiveTest(BpmnWorkflowTestCase):
    def setUp(self):
        self.spec = self.load_spec()

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/Parallel-Then-Exclusive.bpmn20.xml', 'Parallel Then Exclusive')

    def testRunThroughParallelTaskFirst(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Parallel Task')
        self.workflow.do_engine_steps()
        self.assertRaises(AssertionError, self.do_next_named_step, 'Done')
        self.do_next_named_step('Choice 1', choice='Yes')
        self.workflow.do_engine_steps()
        self.do_next_named_step('Yes Task')
        self.workflow.do_engine_steps()

        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()

        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testRunThroughChoiceFirst(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Choice 1', choice='Yes')
        self.workflow.do_engine_steps()
        self.do_next_named_step('Parallel Task')
        self.workflow.do_engine_steps()
        self.assertRaises(AssertionError, self.do_next_named_step, 'Done')
        self.do_next_named_step('Yes Task')
        self.workflow.do_engine_steps()

        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()

        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testRunThroughChoiceThreadCompleteFirst(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Choice 1', choice='Yes')
        self.workflow.do_engine_steps()
        self.do_next_named_step('Yes Task')
        self.workflow.do_engine_steps()
        self.assertRaises(AssertionError, self.do_next_named_step, 'Done')
        self.do_next_named_step('Parallel Task')
        self.workflow.do_engine_steps()

        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()

        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

class ParallelThenExlusiveNoInclusiveTest(ParallelThenExlusiveTest):

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/Parallel-Then-Exclusive-No-Inclusive.bpmn20.xml', 'Parallel Then Exclusive No Inclusive')

class ParallelThroughSameTaskTest(BpmnWorkflowTestCase):
    def setUp(self):
        self.spec = self.load_spec()

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/Parallel-Through-Same-Task.bpmn20.xml', 'Parallel Through Same Task')

    def testRunThroughFirstRepeatTaskFirst(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Repeated Task')
        self.workflow.do_engine_steps()
        #The inclusive gateway allows this to pass through (since there is a route to it on the same sequence flow)
        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()
        self.do_next_named_step('Choice 1', choice='Yes')
        self.workflow.do_engine_steps()
        self.do_next_named_step('Yes Task')
        self.workflow.do_engine_steps()
        self.assertRaises(AssertionError, self.do_next_named_step, 'Done')
        self.do_next_named_step('Repeated Task')
        self.workflow.do_engine_steps()

        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()

        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testRepeatTasksReadyTogether(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Choice 1', choice='Yes')
        self.workflow.do_engine_steps()
        self.do_next_named_step('Yes Task')
        self.workflow.do_engine_steps()
        self.assertRaises(AssertionError, self.do_next_named_step, 'Done')
        ready_tasks = self.workflow.get_tasks(Task.READY)
        self.assertEquals(2, len(ready_tasks))
        self.assertEquals('Repeated Task', ready_tasks[0].task_spec.description)
        ready_tasks[0].complete()
        self.workflow.do_engine_steps()
        #The inclusive gateway allows us through here, because there is no route for the other thread
        #that doesn't use the same sequence flow
        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()
        self.do_next_named_step('Repeated Task')
        self.workflow.do_engine_steps()

        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()

        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testRepeatTasksReadyTogetherSaveRestore(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Choice 1', choice='Yes')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.do_next_named_step('Yes Task')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.assertRaises(AssertionError, self.do_next_named_step, 'Done')
        ready_tasks = self.workflow.get_tasks(Task.READY)
        self.assertEquals(2, len(ready_tasks))
        self.assertEquals('Repeated Task', ready_tasks[0].task_spec.description)
        ready_tasks[0].complete()
        self.workflow.do_engine_steps()
        self.save_restore()
        #The inclusive gateway allows us through here, because there is no route for the other thread
        #that doesn't use the same sequence flow
        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.do_next_named_step('Repeated Task')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))


    def testNoRouteRepeatTaskFirst(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Repeated Task')
        self.workflow.do_engine_steps()
        self.save_restore()
        #The inclusive gateway allows this to pass through (since there is a route to it on the same sequence flow)
        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.do_next_named_step('Choice 1', choice='No')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.do_next_named_step('No Task')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testNoRouteNoTaskFirst(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Choice 1', choice='No')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.do_next_named_step('No Task')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.assertRaises(AssertionError, self.do_next_named_step, 'Done')
        self.do_next_named_step('Repeated Task')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testNoRouteNoFirstThenRepeating(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Choice 1', choice='No')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.assertRaises(AssertionError, self.do_next_named_step, 'Done')
        self.do_next_named_step('Repeated Task')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.assertRaises(AssertionError, self.do_next_named_step, 'Done')
        self.do_next_named_step('No Task')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()
        self.save_restore()

        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

class ParallelOnePathEndsTest(BpmnWorkflowTestCase):
    def setUp(self):
        self.spec = self.load_spec()

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/Parallel-One-Path-Ends.bpmn20.xml', 'Parallel One Path Ends')

    def testRunThroughParallelTaskFirst(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Parallel Task')
        self.workflow.do_engine_steps()
        self.assertRaises(AssertionError, self.do_next_named_step, 'Done')
        self.do_next_named_step('Choice 1', choice='No')
        self.workflow.do_engine_steps()

        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()

        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testRunThroughChoiceFirst(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Choice 1', choice='No')
        self.workflow.do_engine_steps()
        self.assertRaises(AssertionError, self.do_next_named_step, 'Done')
        self.do_next_named_step('Parallel Task')
        self.workflow.do_engine_steps()

        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()

        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testRunThroughParallelTaskFirstYes(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()

        self.assertEquals(2, len(self.workflow.get_tasks(Task.READY)))

        self.do_next_named_step('Parallel Task')
        self.workflow.do_engine_steps()
        self.assertRaises(AssertionError, self.do_next_named_step, 'Done')
        self.do_next_named_step('Choice 1', choice='Yes')
        self.workflow.do_engine_steps()
        self.assertRaises(AssertionError, self.do_next_named_step, 'Done')
        self.do_next_named_step('Yes Task')
        self.workflow.do_engine_steps()

        self.do_next_named_step('Done')
        self.workflow.do_engine_steps()

        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

class AbstractParallelTest(BpmnWorkflowTestCase):
    def _do_test(self, order, only_one_instance=True, save_restore=False):
        self.workflow = BpmnWorkflow(self.spec)
        self.workflow.do_engine_steps()
        for s in order:
            choice = None
            if isinstance(s, tuple):
                s,choice = s
            if s.startswith('!'):
                logging.info("Checking that we cannot do '%s'", s[1:])
                self.assertRaises(AssertionError, self.do_next_named_step, s[1:], choice=choice)
            else:
                if choice is not None:
                    logging.info("Doing step '%s' (with choice='%s')", s, choice)
                else:
                    logging.info("Doing step '%s'", s)
                #logging.debug(self.workflow.get_dump())
                self.do_next_named_step(s, choice=choice,only_one_instance=only_one_instance)
            self.workflow.do_engine_steps()
            if save_restore:
                #logging.debug("Before SaveRestore: \n%s" % self.workflow.get_dump())
                self.save_restore()

        self.workflow.do_engine_steps()
        unfinished = self.workflow.get_tasks(Task.READY | Task.WAITING)
        if unfinished:
            logging.debug("Unfinished tasks: %s", unfinished)
            logging.debug(self.workflow.get_dump())
        self.assertEquals(0, len(unfinished))

class ParallelMultipleSplitsAndJoinsTest(AbstractParallelTest):
    def setUp(self):
        self.spec = self.load_spec()

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/Parallel-Multiple-Splits-And-Joins.bpmn20.xml', 'Parallel Multiple Splits And Joins')

    def test1(self):
        self._do_test(['1', '!Done', '2', '1A', '!Done', '2A', '1B', '2B', '!Done', '1 Done', '!Done', '2 Done', 'Done'], save_restore=True)

    def test2(self):
        self._do_test(['1', '!Done', '1A', '1B', '1 Done', '!Done', '2', '2A', '2B', '2 Done', 'Done'], save_restore=True)

    def test3(self):
        self._do_test(['1', '2', '!Done', '1B', '2B', '!2 Done', '1A', '!Done', '2A', '1 Done', '!Done', '2 Done', 'Done'], save_restore=True)

    def test4(self):
        self._do_test(['1', '1B', '1A', '1 Done', '!Done', '2', '2B', '2A', '2 Done', 'Done'], save_restore=True)


class ParallelLoopingAfterJoinTest(AbstractParallelTest):
    def setUp(self):
        self.spec = self.load_spec()

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/Parallel-Looping-After-Join.bpmn20.xml', 'Parallel Looping After Join')

    def test1(self):
        self._do_test(['Go', '1', '2', '2A', '2B', '2 Done', ('Retry?', 'No'), 'Done'], save_restore=True)

    def test2(self):
        self._do_test(['Go', '1', '2', '2A', '2B', '2 Done', ('Retry?', 'Yes'), 'Go', '1', '2', '2A', '2B', '2 Done', ('Retry?', 'No'), 'Done'], save_restore=True)


class ParallelManyThreadsAtSamePointTest(AbstractParallelTest):
    def setUp(self):
        self.spec = self.load_spec()

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/Parallel-Many-Threads-At-Same-Point.bpmn20.xml', 'Parallel Many Threads At Same Point')

    def test1(self):
        self._do_test(['1', '2', '3', '4', 'Done', 'Done', 'Done', 'Done'], only_one_instance=False, save_restore=True)

    def test2(self):
        self._do_test(['1', 'Done', '2', 'Done', '3', 'Done',  '4', 'Done'], only_one_instance=False, save_restore=True)

    def test2(self):
        self._do_test(['1', '2', 'Done', '3', '4', 'Done', 'Done', 'Done'], only_one_instance=False, save_restore=True)


class ParallelManyThreadsAtSamePointTestNested(AbstractParallelTest):
    def setUp(self):
        self.spec = self.load_spec()

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/Parallel-Many-Threads-At-Same-Point-Nested.bpmn20.xml', 'Parallel Many Threads At Same Point Nested')

    def test_depth_first(self):
        instructions = []
        for split1 in ['SP 1','SP 2']:
            for sp in ['A', 'B']:
                for split2 in ['1','2']:
                    for t in ['A', 'B']:
                        instructions.append(split1+sp+"|"+split2+t)
                    instructions.append(split1+sp+"|"+'Inner Done')
                    instructions.append("!"+split1+sp+"|"+'Inner Done')
                if sp =='A':
                    instructions.append("!Outer Done")

            instructions.append('Outer Done')
            instructions.append("!Outer Done")

        logging.info('Doing test with instructions: %s', instructions)
        self._do_test(instructions, only_one_instance=False, save_restore=True)

    def test_breadth_first(self):
        instructions = []
        for t in ['A', 'B']:
            for split2 in ['1','2']:
                for sp in ['A', 'B']:
                    for split1 in ['SP 1','SP 2']:
                        instructions.append(split1+sp+"|"+split2+t)

        for split1 in ['SP 1','SP 2']:
            for sp in ['A', 'B']:
                for split2 in ['1','2']:
                    instructions += [split1+sp+"|"+'Inner Done']

        for split1 in ['SP 1','SP 2']:
            instructions += ['Outer Done']

        logging.info('Doing test with instructions: %s', instructions)
        self._do_test(instructions, only_one_instance=False, save_restore=True)



def suite():
    return unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = Signavio2Html
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import sys
from SpiffWorkflow.bpmn.storage.BpmnSerializer import BpmnSerializer
from tests.SpiffWorkflow.bpmn.PackagerForTests import PackagerForTests

__author__ = 'matth'

def main():
    workflow_files = sys.argv[1]
    workflow_name = sys.argv[2]
    output_file = sys.argv[3]

    spec = BpmnSerializer().deserialize_workflow_spec(
        PackagerForTests.package_in_memory(workflow_name, workflow_files))

    f = open(output_file, 'w')
    try:
        f.write(spec.to_html_string())
    finally:
        f.close()

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = TimerIntermediateTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import unittest
import datetime
import time
from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.BpmnWorkflow import BpmnWorkflow
from tests.SpiffWorkflow.bpmn.BpmnWorkflowTestCase import BpmnWorkflowTestCase

__author__ = 'matth'

class TimerIntermediateTest(BpmnWorkflowTestCase):
    def setUp(self):
        self.spec = self.load_spec()

    def load_spec(self):
        return self.load_workflow_spec('Test-Workflows/*.bpmn20.xml', 'Timer Intermediate')

    def testRunThroughHappy(self):

        self.workflow = BpmnWorkflow(self.spec)

        due_time = datetime.datetime.now() + datetime.timedelta(seconds=0.5)

        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.workflow.get_tasks(Task.READY)[0].set_data(due_time=due_time)

        self.workflow.do_engine_steps()

        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))

        time.sleep(0.6)

        self.assertEquals(1, len(self.workflow.get_tasks(Task.WAITING)))
        self.workflow.refresh_waiting_tasks()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.WAITING)))
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))

        self.workflow.do_engine_steps()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TimerIntermediateTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = workflow1
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
from SpiffWorkflow.specs import *
from SpiffWorkflow.operators import *

class TestWorkflowSpec(WorkflowSpec):
    def __init__(self):
        WorkflowSpec.__init__(self)
        # Build one branch.
        a1 = Simple(self, 'task_a1')
        self.start.connect(a1)

        a2 = Simple(self, 'task_a2')
        a1.connect(a2)

        # Build another branch.
        b1 = Simple(self, 'task_b1')
        self.start.connect(b1)

        b2 = Simple(self, 'task_b2')
        b1.connect(b2)

        # Merge both branches (synchronized).
        synch_1 = Join(self, 'synch_1')
        a2.connect(synch_1)
        b2.connect(synch_1)

        # If-condition that does not match.
        excl_choice_1 = ExclusiveChoice(self, 'excl_choice_1')
        synch_1.connect(excl_choice_1)

        c1 = Simple(self, 'task_c1')
        excl_choice_1.connect(c1)

        c2 = Simple(self, 'task_c2')
        cond = Equal(Attrib('test_attribute1'), Attrib('test_attribute2'))
        excl_choice_1.connect_if(cond, c2)

        c3 = Simple(self, 'task_c3')
        excl_choice_1.connect_if(cond, c3)

        # If-condition that matches.
        excl_choice_2 = ExclusiveChoice(self, 'excl_choice_2')
        c1.connect(excl_choice_2)
        c2.connect(excl_choice_2)
        c3.connect(excl_choice_2)

        d1 = Simple(self, 'task_d1')
        excl_choice_2.connect(d1)

        d2 = Simple(self, 'task_d2')
        excl_choice_2.connect_if(cond, d2)

        d3 = Simple(self, 'task_d3')
        cond = Equal(Attrib('test_attribute1'), Attrib('test_attribute1'))
        excl_choice_2.connect_if(cond, d3)

        # If-condition that does not match.
        multichoice = MultiChoice(self, 'multi_choice_1')
        d1.connect(multichoice)
        d2.connect(multichoice)
        d3.connect(multichoice)

        e1 = Simple(self, 'task_e1')
        multichoice.connect_if(cond, e1)

        e2 = Simple(self, 'task_e2')
        cond = Equal(Attrib('test_attribute1'), Attrib('test_attribute2'))
        multichoice.connect_if(cond, e2)

        e3 = Simple(self, 'task_e3')
        cond = Equal(Attrib('test_attribute2'), Attrib('test_attribute2'))
        multichoice.connect_if(cond, e3)

        # StructuredSynchronizingMerge
        syncmerge = Join(self, 'struct_synch_merge_1', 'multi_choice_1')
        e1.connect(syncmerge)
        e2.connect(syncmerge)
        e3.connect(syncmerge)

        # Implicit parallel split.
        f1 = Simple(self, 'task_f1')
        syncmerge.connect(f1)

        f2 = Simple(self, 'task_f2')
        syncmerge.connect(f2)

        f3 = Simple(self, 'task_f3')
        syncmerge.connect(f3)

        # Discriminator
        discrim_1 = Join(self,
                         'struct_discriminator_1',
                         'struct_synch_merge_1',
                         threshold = 1)
        f1.connect(discrim_1)
        f2.connect(discrim_1)
        f3.connect(discrim_1)

        # Loop back to the first exclusive choice.
        excl_choice_3 = ExclusiveChoice(self, 'excl_choice_3')
        discrim_1.connect(excl_choice_3)
        cond = NotEqual(Attrib('excl_choice_3_reached'), Attrib('two'))
        excl_choice_3.connect_if(cond, excl_choice_1)

        # Split into 3 branches, and implicitly split twice in addition.
        multi_instance_1 = MultiInstance(self, 'multi_instance_1', times = 3)
        excl_choice_3.connect(multi_instance_1)

        # Parallel tasks.
        g1 = Simple(self, 'task_g1')
        g2 = Simple(self, 'task_g2')
        multi_instance_1.connect(g1)
        multi_instance_1.connect(g2)

        # StructuredSynchronizingMerge
        syncmerge2 = Join(self, 'struct_synch_merge_2', 'multi_instance_1')
        g1.connect(syncmerge2)
        g2.connect(syncmerge2)

        # Add a final task.
        last = Simple(self, 'last')
        syncmerge2.connect(last)

        # Add another final task :-).
        end = Simple(self, 'End')
        last.connect(end)

########NEW FILE########
__FILENAME__ = ExecuteProcessMock
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
#!/usr/bin/python
import time

def main():
    time.sleep(0.5)
    print("127.0.0.1")

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = PatternTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import sys, unittest, re, os, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from SpiffWorkflow.specs import *
from SpiffWorkflow import Task
from SpiffWorkflow.storage import XmlSerializer
from xml.parsers.expat import ExpatError
from util import run_workflow

class PatternTest(unittest.TestCase):
    def setUp(self):
        Task.id_pool = 0
        Task.thread_id_pool = 0
        self.xml_path = ['data/spiff/control-flow',
                         'data/spiff/data',
                         'data/spiff/resource',
                         'data/spiff']
        self.serializer = XmlSerializer()

    def run_pattern(self, filename):
        # Load the .path file.
        path_file = os.path.splitext(filename)[0] + '.path'
        if os.path.exists(path_file):
            expected_path = open(path_file).read()
        else:
            expected_path = None

        # Load the .data file.
        data_file = os.path.splitext(filename)[0] + '.data'
        if os.path.exists(data_file):
            expected_data = open(data_file, 'r').read()
        else:
            expected_data = None

        # Test patterns that are defined in XML format.
        if filename.endswith('.xml'):
            xml     = open(filename).read()
            wf_spec = WorkflowSpec.deserialize(self.serializer, xml, filename = filename)
            run_workflow(self, wf_spec, expected_path, expected_data)

        # Test patterns that are defined in Python.
        if filename.endswith('.py') and not filename.endswith('__.py'):
            code    = compile(open(filename).read(), filename, 'exec')
            thedict = {}
            result  = eval(code, thedict)
            wf_spec = thedict['TestWorkflowSpec']()
            run_workflow(self, wf_spec, expected_path, expected_data)

    def testPattern(self):
        for basedir in self.xml_path:
            dirname = os.path.join(os.path.dirname(__file__), basedir)

            for filename in os.listdir(dirname):
                if not filename.endswith(('.xml', '.py')):
                    continue
                filename = os.path.join(dirname, filename)
                print(filename)
                self.run_pattern(filename)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(PatternTest)
if __name__ == '__main__':
    if len(sys.argv) == 2:
        test = PatternTest('run_pattern')
        test.setUp()
        test.run_pattern(sys.argv[1])
        sys.exit(0)
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = PersistSmallWorkflowTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import sys, unittest, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from SpiffWorkflow import Workflow
from SpiffWorkflow.specs import *
from SpiffWorkflow.operators import *
from SpiffWorkflow.Task import *
from SpiffWorkflow.specs.Simple import Simple
from SpiffWorkflow.storage import DictionarySerializer


class ASmallWorkflow(WorkflowSpec):
    def __init__(self):
        super(ASmallWorkflow, self).__init__(name="asmallworkflow")

        multichoice = MultiChoice(self, 'multi_choice_1')
        self.start.connect(multichoice)

        a1 = Simple(self, 'task_a1')
        multichoice.connect(a1)

        a2 = Simple(self, 'task_a2')
        cond = Equal(Attrib('test_attribute1'), PathAttrib('test/attribute2'))
        multichoice.connect_if(cond, a2)

        syncmerge = Join(self, 'struct_synch_merge_1', 'multi_choice_1')
        a1.connect(syncmerge)
        a2.connect(syncmerge)

        end = Simple(self, 'End')
        syncmerge.connect(end)


class PersistSmallWorkflowTest(unittest.TestCase):
    """Runs persistency tests agains a small and easy to inspect workflowdefinition"""
    def setUp(self):
        self.wf_spec = ASmallWorkflow()
        self.workflow = self._advance_to_a1(self.wf_spec)

    def _advance_to_a1(self, wf_spec):
        workflow = Workflow(wf_spec)

        tasks = workflow.get_tasks(Task.READY)
        task_start = tasks[0]
        workflow.complete_task_from_id(task_start.id)

        tasks = workflow.get_tasks(Task.READY)
        multichoice = tasks[0]
        workflow.complete_task_from_id(multichoice.id)

        tasks = workflow.get_tasks(Task.READY)
        task_a1 = tasks[0]
        workflow.complete_task_from_id(task_a1.id)
        return workflow

    def testDictionarySerializer(self):
        """
        Tests the SelectivePickler serializer for persisting Workflows and Tasks.
        """
        old_workflow = self.workflow
        serializer = DictionarySerializer()
        serialized_workflow = old_workflow.serialize(serializer)

        serializer = DictionarySerializer()
        new_workflow = Workflow.deserialize(serializer, serialized_workflow)

        before = old_workflow.get_dump()
        after = new_workflow.get_dump()
        self.assert_(before == after, 'Before:\n' + before + '\n' \
                                    + 'After:\n' + after + '\n')

    def testDeserialization(self):
        """
        Tests the that deserialized workflow matches the original workflow
        """
        old_workflow = self.workflow
        old_workflow.spec.start.set_data(marker=True)
        serializer = DictionarySerializer()
        serialized_workflow = old_workflow.serialize(serializer)

        serializer = DictionarySerializer()
        new_workflow = Workflow.deserialize(serializer, serialized_workflow)

        self.assertEqual(len(new_workflow.get_tasks()), len(old_workflow.get_tasks()))
        self.assertEqual(new_workflow.spec.start.get_data('marker'), old_workflow.spec.start.get_data('marker'))
        self.assertEqual(1, len([t for t in new_workflow.get_tasks() if t.task_spec.name == 'Start']))
        self.assertEqual(1, len([t for t in new_workflow.get_tasks() if t.task_spec.name == 'Root']))

    def testDeserialization(self):
        """
        Tests the that deserialized workflow can be completed.
        """
        old_workflow = self.workflow

        old_workflow.complete_next()
        self.assertEquals('task_a2', old_workflow.last_task.get_name())
        serializer = DictionarySerializer()
        serialized_workflow = old_workflow.serialize(serializer)

        serializer = DictionarySerializer()
        new_workflow = Workflow.deserialize(serializer, serialized_workflow)
        self.assertEquals('task_a2', old_workflow.last_task.get_name())
        new_workflow.complete_all()
        self.assertEquals('task_a2', old_workflow.last_task.get_name())


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(PersistSmallWorkflowTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = run_suite
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
#!/usr/bin/python
import os, sys, unittest, glob, fnmatch, re
from inspect import isfunction, ismodule, isclass

def uppercase(match):
    return match.group(1).upper()

correlated = dict()

def correlate_class(theclass):
    """
    Checks the given testcase for missing test methods.
    """
    if not hasattr(theclass, 'CORRELATE'):
        return

    # Collect all functions in the class or module.
    for name, value in theclass.CORRELATE.__dict__.items():
        if not isfunction(value):
            continue
        elif name == '__init__':
            name = 'Constructor'
        elif name.startswith('_'):
            continue

        # Format the function names.
        testname   = re.sub(r'_(\w)',  uppercase, name)
        testname   = re.sub(r'(\d\w)', uppercase, testname)
        testname   = 'test' + re.sub(r'^(\w)', uppercase, testname)
        testmethod = theclass.__name__ + '.' + testname
        method     = theclass.CORRELATE.__name__ + '.' + name
        both       = testmethod + ' (' + method + ')'

        # Throw an error if the function does not have a test.
        if testname in dir(theclass):
            continue
        if ismodule(theclass.CORRELATE) and \
          value.__module__ != theclass.CORRELATE.__name__:
            continue # function was imported.
        if both in correlated:
            continue
        correlated[both] = True
        if ismodule(theclass.CORRELATE):
            sys.stderr.write('!!!! WARNING: Untested function: ' + both + '\n')
        elif isclass(theclass.CORRELATE):
            sys.stderr.write('!!!! WARNING: Untested method: ' + both + '\n')

def correlate_module(module):
    """
    Checks all testcases in the module for missing test methods.
    """
    for name, item in module.__dict__.items():
        if isclass(item):
            correlate_class(item)

def find(dirname, pattern):
    output = []
    for root, dirs, files in os.walk(dirname):
        for file in files:
            if fnmatch.fnmatchcase(file, pattern):
                output.append(os.path.join(root, file))
    return output

def load_suite(files):
    modules    = [os.path.splitext(f)[0] for f in files]
    all_suites = []
    for name in modules:
        name   = name.lstrip('.').lstrip('/').replace('/', '.')
        module = __import__(name, globals(), locals(), [''])
        all_suites.append(module.suite())
        correlate_module(module)
    if correlated:
        sys.stderr.write('Error: Untested methods found.\n')
        sys.exit(1)
    return unittest.TestSuite(all_suites)

def suite():
    pattern = os.path.join(os.path.dirname(__file__), '*Test.py')
    files   = glob.glob(pattern)
    return load_suite([os.path.basename(f) for f in files])

def recursive_suite():
    return load_suite(find('.', '*Test.py'))

if __name__ == '__main__':
    # Parse CLI options.
    if len(sys.argv) == 1:
        verbosity = 2
    elif len(sys.argv) == 2:
        verbosity = int(sys.argv[1])
    else:
        print('Syntax:', sys.argv[0], '[verbosity]')
        print('Default verbosity is 2')
        sys.exit(2)

    # Run.
    results = unittest.TextTestRunner(verbosity = verbosity).run(recursive_suite())
    sys.exit(0 if results.wasSuccessful() else 1)

########NEW FILE########
__FILENAME__ = CeleryTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import os
import sys
import unittest
import pickle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from .TaskSpecTest import TaskSpecTest
from SpiffWorkflow.specs import Celery, WorkflowSpec
from SpiffWorkflow.operators import Attrib
from SpiffWorkflow.storage import DictionarySerializer
from base64 import b64encode

class CeleryTest(TaskSpecTest):
    CORRELATE = Celery

    def create_instance(self):
        if 'testtask' in self.wf_spec.task_specs:
            del self.wf_spec.task_specs['testtask']
        return Celery(self.wf_spec,
                       'testtask', 'call.name',
                       call_args=[Attrib('the_attribute'), 1],
                       description='foo',
                       named_kw=[],
                       dict_kw={}
                       )

    def testTryFire(self):
        pass

    def testRetryFire(self):
        pass

    def testSerializationWithoutKwargs(self):
        new_wf_spec = WorkflowSpec()
        serializer = DictionarySerializer()
        nokw = Celery(self.wf_spec, 'testnokw', 'call.name',
                call_args=[Attrib('the_attribute'), 1])
        data = nokw.serialize(serializer)
        nokw2 = Celery.deserialize(serializer, new_wf_spec, data)
        self.assertDictEqual(nokw.kwargs, nokw2.kwargs)

        kw = Celery(self.wf_spec, 'testkw', 'call.name',
                call_args=[Attrib('the_attribute'), 1],
                some_arg={"key": "value"})
        data = kw.serialize(serializer)
        kw2 = Celery.deserialize(serializer, new_wf_spec, data)
        self.assertDictEqual(kw.kwargs, kw2.kwargs)

        # Has kwargs, but they belong to TaskSpec
        kw_defined = Celery(self.wf_spec, 'testkwdef', 'call.name',
                call_args=[Attrib('the_attribute'), 1],
                some_ref=Attrib('value'),
                defines={"key": "value"})
        data = kw_defined.serialize(serializer)
        kw_defined2 = Celery.deserialize(serializer, new_wf_spec, data)
        self.assertIsInstance(kw_defined2.kwargs['some_ref'], Attrib)


        args = [b64encode(pickle.dumps(v)) for v in [Attrib('the_attribute'), u'ip', u'dc455016e2e04a469c01a866f11c0854']]

        data = { u'R': b64encode(pickle.dumps(u'1'))}
        # Comes from live data. Bug not identified, but there we are...
        data = {u'inputs': [u'Wait:1'], u'lookahead': 2, u'description': u'',
                u'outputs': [], u'args': args,
          u'manual': False,
          u'data': data, u'locks': [], u'pre_assign': [],
          u'call': u'call.x',
          u'internal': False, u'post_assign': [], u'id': 8,
          u'result_key': None, u'defines': data,
          u'class': u'SpiffWorkflow.specs.Celery.Celery',
          u'name': u'RS1:1'}
        Celery.deserialize(serializer, new_wf_spec, data)

def suite():
    try:
        import celery
    except ImportError:
        print("WARNING: Celery not found, not all tests are running!")
        return lambda x: None
    else:
        return unittest.TestLoader().loadTestsFromTestCase(CeleryTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = ExecuteTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import os
import sys
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from tests.SpiffWorkflow.util import run_workflow
from .TaskSpecTest import TaskSpecTest
from SpiffWorkflow import Task
from SpiffWorkflow.specs import Execute


class ExecuteTest(TaskSpecTest):
    CORRELATE = Execute

    def create_instance(self):
        if 'testtask' in self.wf_spec.task_specs:
            del self.wf_spec.task_specs['testtask']
        return Execute(self.wf_spec,
                       'testtask',
                       description='foo',
                       args=self.cmd_args)

    def setUp(self):
        self.cmd_args = ["python", "ExecuteProcessMock.py"]
        TaskSpecTest.setUp(self)

    def testConstructor(self):
        TaskSpecTest.testConstructor(self)
        self.assertEqual(self.spec.args, self.cmd_args)

    def testPattern(self):
        """
        Tests that we can create a task that executes an shell command
        and that the workflow can be called to complete such tasks.
        """
        self.wf_spec.start.connect(self.spec)
        expected = 'Start\n  testtask\n'
        workflow = run_workflow(self, self.wf_spec, expected, '')
        task = workflow.get_tasks_from_spec_name('testtask')[0]
        self.assertEqual(task.state_history, [Task.FUTURE,
                                              Task.WAITING,
                                              Task.READY,
                                              Task.COMPLETED])
        self.assert_(b'127.0.0.1' in task.results[0])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ExecuteTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = JoinTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import os
import sys
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from .TaskSpecTest import TaskSpecTest
from SpiffWorkflow.specs import Join
from SpiffWorkflow import Workflow


class JoinTest(TaskSpecTest):
    CORRELATE = Join

    def create_instance(self):
        if 'testtask' in self.wf_spec.task_specs:
            del self.wf_spec.task_specs['testtask']

        return Join(self.wf_spec,
                       'testtask',
                       description='foo')

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(JoinTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = MergeTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import os
import sys
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from .JoinTest import JoinTest
from SpiffWorkflow.specs import Merge, WorkflowSpec, Simple
from SpiffWorkflow import Workflow


class MergeTest(JoinTest):
    CORRELATE = Merge

    def create_instance(self):
        if 'testtask' in self.wf_spec.task_specs:
            del self.wf_spec.task_specs['testtask']

        return Merge(self.wf_spec,
                       'testtask',
                       description='foo')

    def test_Merge_data_merging(self):
        """Test that Merge task actually merges data"""
        wf_spec = WorkflowSpec()
        first = Simple(wf_spec, 'first')
        second = Simple(wf_spec, 'second')
        third = Simple(wf_spec, 'third')
        bump = Simple(wf_spec, 'bump')
        fourth = Simple(wf_spec, 'fourth')
        merge1 = Merge(wf_spec, 'merge 1')
        simple1 = Simple(wf_spec, 'simple 1')
        merge2 = Merge(wf_spec, 'merge 2')
        simple2 = Simple(wf_spec, 'simple 2')
        unmerged = Simple(wf_spec, 'unmerged')

        wf_spec.start.connect(first)
        wf_spec.start.connect(second)
        wf_spec.start.connect(third)
        wf_spec.start.connect(bump)
        bump.connect(fourth)  # Test join at different depths in tree

        first.connect(merge1)
        second.connect(merge1)
        second.connect(unmerged)

        first.connect(merge2)
        second.connect(merge2)
        third.connect(merge2)
        fourth.connect(merge2)

        merge1.connect(simple1)
        merge2.connect(simple2)

        workflow = Workflow(wf_spec)
        workflow.task_tree.set_data(everywhere=1)
        for task in workflow.get_tasks():
            task.set_data(**{'name': task.get_name(), task.get_name(): 1})
        workflow.complete_all()
        self.assertTrue(workflow.is_completed())
        found = {}
        for task in workflow.get_tasks():
            if task.task_spec is simple1:
                self.assert_('first' in task.data)
                self.assert_('second' in task.data)
                self.assertEqual(task.data, {'Start': 1,
                        'merge 1': 1, 'name': 'Start', 'simple 1': 1,
                        'second': 1, 'first': 1})
                found['simple1'] = task
            if task.task_spec is simple2:
                self.assert_('first' in task.data)
                self.assert_('second' in task.data)
                self.assert_('third' in task.data)
                self.assert_('fourth' in task.data)
                self.assertEqual(task.data, {'merge 2': 1,
                        'simple 2': 1, 'name': 'Start', 'third': 1, 'bump': 1,
                        'Start': 1, 'second': 1, 'first': 1, 'fourth': 1})
                found['simple2'] = task
            if task.task_spec is unmerged:
                self.assertEqual(task.data, {'Start': 1,
                        'second': 1, 'name': 'Start', 'unmerged': 1})
                found['unmerged'] = task
        self.assert_('simple1' in found)
        self.assert_('simple2' in found)
        self.assert_('unmerged' in found)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(MergeTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = SubWorkflowTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import sys
import unittest
import re
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from SpiffWorkflow.specs import WorkflowSpec, Simple, Join
from SpiffWorkflow.specs.SubWorkflow import SubWorkflow
from SpiffWorkflow.storage import XmlSerializer
from SpiffWorkflow.Task import Task
from SpiffWorkflow.Workflow import Workflow

class TaskSpecTest(unittest.TestCase):
    CORRELATE = SubWorkflow

    def testConstructor(self):
        pass #FIXME

    def testSerialize(self):
        pass #FIXME

    def testTest(self):
        pass #FIXME

    def load_workflow_spec(self, folder, f):
        file = os.path.join(os.path.dirname(__file__), '..', 'data', 'spiff', folder, f)
        serializer    = XmlSerializer()
        xml           = open(file).read()
        self.wf_spec  = WorkflowSpec.deserialize(serializer, xml, filename = file)
        self.workflow = Workflow(self.wf_spec)

    def do_next_unique_task(self, name):
        #This method asserts that there is only one ready task! The specified one - and then completes it
        ready_tasks = self.workflow.get_tasks(Task.READY)
        self.assertEquals(1, len(ready_tasks))
        task = ready_tasks[0]
        self.assertEquals(name, task.task_spec.name)
        task.complete()

    def do_next_named_step(self, name, other_ready_tasks):
        #This method completes a single task from the specified set of ready tasks
        ready_tasks = self.workflow.get_tasks(Task.READY)
        all_tasks = sorted([name] + other_ready_tasks)
        self.assertEquals(all_tasks, sorted([t.task_spec.name for t in ready_tasks]))
        task = list([t for t in ready_tasks if t.task_spec.name==name])[0]
        task.complete()


    def test_block_to_subworkflow(self):
        self.load_workflow_spec('data', 'block_to_subworkflow.xml')
        self.do_next_unique_task('Start')
        self.do_next_unique_task('first')
        self.do_next_unique_task('sub_workflow_1')
        #Inner:
        self.do_next_unique_task('Start')
        self.do_next_unique_task('first')
        self.do_next_unique_task('last')
        self.do_next_unique_task('End')
        #Back to outer:
        self.do_next_unique_task('last')
        self.do_next_unique_task('End')

    def test_subworkflow_to_block(self):
        self.load_workflow_spec('data', 'subworkflow_to_block.xml')
        self.do_next_unique_task('Start')
        self.do_next_unique_task('first')
        self.do_next_unique_task('sub_workflow_1')
        #Inner:
        self.do_next_unique_task('Start')
        self.do_next_unique_task('first')
        self.do_next_unique_task('last')
        self.do_next_unique_task('End')
        #Back to outer:
        self.do_next_unique_task('last')
        self.do_next_unique_task('End')

    def test_subworkflow_to_join(self):
        self.load_workflow_spec('control-flow', 'subworkflow_to_join.xml')
        self.do_next_unique_task('Start')
        self.do_next_unique_task('first')
        self.do_next_named_step('second', ['sub_workflow_1'])
        self.do_next_unique_task('sub_workflow_1')
        #Inner:
        self.do_next_unique_task('Start')
        self.do_next_unique_task('first')
        self.do_next_unique_task('last')
        self.do_next_unique_task('End')
        #Back to outer:
        self.do_next_unique_task('join')
        self.do_next_unique_task('last')
        self.do_next_unique_task('End')

    def test_subworkflow_to_join_refresh_waiting(self):
        self.load_workflow_spec('control-flow', 'subworkflow_to_join.xml')
        self.do_next_unique_task('Start')
        self.do_next_unique_task('first')
        self.do_next_named_step('second', ['sub_workflow_1'])
        self.do_next_unique_task('sub_workflow_1')
        #Inner:
        self.do_next_unique_task('Start')
        self.do_next_unique_task('first')

        #Now refresh waiting tasks:
        # Update the state of every WAITING task.
        for thetask in self.workflow._get_waiting_tasks():
            thetask.task_spec._update_state(thetask)

        self.do_next_unique_task('last')
        self.do_next_unique_task('End')
        #Back to outer:
        self.do_next_unique_task('join')
        self.do_next_unique_task('last')
        self.do_next_unique_task('End')


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TaskSpecTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = TaskSpecTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import sys
import unittest
import re
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from SpiffWorkflow.specs import WorkflowSpec, Simple, Join
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.specs.TaskSpec import TaskSpec
from SpiffWorkflow.storage import DictionarySerializer


class TaskSpecTest(unittest.TestCase):
    CORRELATE = TaskSpec

    def create_instance(self):
        if 'testtask' in self.wf_spec.task_specs:
            del self.wf_spec.task_specs['testtask']
        return TaskSpec(self.wf_spec, 'testtask', description='foo')

    def setUp(self):
        self.wf_spec = WorkflowSpec()
        self.spec = self.create_instance()

    def testConstructor(self):
        self.assertEqual(self.spec.name, 'testtask')
        self.assertEqual(self.spec.description, 'foo')
        self.assertEqual(self.spec.data, {})
        self.assertEqual(self.spec.defines, {})
        self.assertEqual(self.spec.pre_assign, [])
        self.assertEqual(self.spec.post_assign, [])
        self.assertEqual(self.spec.locks, [])

    def testSetData(self):
        self.assertEqual(self.spec.get_data('foo'), None)
        self.assertEqual(self.spec.get_data('foo', 'bar'), 'bar')
        self.spec.set_data(foo='foobar')
        self.assertEqual(self.spec.get_data('foo'), 'foobar')
        self.assertEqual(self.spec.get_data('foo', 'bar'), 'foobar')

    def testGetData(self):
        return self.testSetData()

    def testConnect(self):
        self.assertEqual(self.spec.outputs, [])
        self.assertEqual(self.spec.inputs, [])
        spec = self.create_instance()
        self.spec.connect(spec)
        self.assertEqual(self.spec.outputs, [spec])
        self.assertEqual(spec.inputs, [self.spec])

    def testFollow(self):
        self.assertEqual(self.spec.outputs, [])
        self.assertEqual(self.spec.inputs, [])
        spec = self.create_instance()
        self.spec.follow(spec)
        self.assertEqual(spec.outputs, [self.spec])
        self.assertEqual(self.spec.inputs, [spec])

    def testTest(self):
        # Should fail because the TaskSpec has no id yet.
        spec = self.create_instance()
        self.assertRaises(WorkflowException, spec.test)

        # Should fail because the task has no inputs.
        self.spec.id = 1
        self.assertRaises(WorkflowException, spec.test)

        # Connect another task to make sure that it has an input.
        self.spec.connect(spec)
        self.assertEqual(spec.test(), None)

    def testSerialize(self):
        serializer = DictionarySerializer()
        spec = self.create_instance()
        serialized = spec.serialize(serializer)
        self.assert_(isinstance(serialized, dict))

        new_wf_spec = WorkflowSpec()
        new_spec = spec.__class__.deserialize(serializer, new_wf_spec,
                serialized)
        before = spec.serialize(serializer)
        after = new_spec.serialize(serializer)
        self.assertEqual(before, after, 'Before:\n%s\nAfter:\n%s\n' % (before,
                after))

    def testAncestors(self):
        T1 = Simple(self.wf_spec, 'T1')
        T2A = Simple(self.wf_spec, 'T2A')
        T2B = Simple(self.wf_spec, 'T2B')
        M = Join(self.wf_spec, 'M')
        T3 = Simple(self.wf_spec, 'T3')

        T1.follow(self.wf_spec.start)
        T2A.follow(T1)
        T2B.follow(T1)
        T2A.connect(M)
        T2B.connect(M)
        T3.follow(M)

        self.assertEquals(T1.ancestors(), [self.wf_spec.start])
        self.assertEquals(T2A.ancestors(), [T1, self.wf_spec.start])
        self.assertEquals(T2B.ancestors(), [T1, self.wf_spec.start])
        self.assertEquals(M.ancestors(), [T2A, T1, self.wf_spec.start, T2B])
        self.assertEqual(len(T3.ancestors()), 5)

    def test_ancestors_cyclic(self):
        T1 = Join(self.wf_spec, 'T1')
        T2 = Simple(self.wf_spec, 'T2')

        T1.follow(self.wf_spec.start)
        T2.follow(T1)
        T1.connect(T2)

        self.assertEquals(T1.ancestors(), [self.wf_spec.start])
        self.assertEquals(T2.ancestors(), [T1, self.wf_spec.start])


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TaskSpecTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = TransformTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import os
import sys
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from tests.SpiffWorkflow.util import run_workflow
from .TaskSpecTest import TaskSpecTest
from SpiffWorkflow.specs import Transform, Simple


class TransformTest(TaskSpecTest):
    CORRELATE = Transform

    def create_instance(self):
        if 'testtask' in self.wf_spec.task_specs:
            del self.wf_spec.task_specs['testtask']

        return Transform(self.wf_spec,
                       'testtask',
                       description='foo',
                       transforms=[''])

    def testPattern(self):
        """
        Tests that we can create a task that executes an shell command
        and that the workflow can be called to complete such tasks.
        """
        task1 = Transform(self.wf_spec, 'First', transforms=[
            "my_task.set_data(foo=1)"])
        self.wf_spec.start.connect(task1)
        task2 = Transform(self.wf_spec, 'Second', transforms=[
            "my_task.set_data(foo=my_task.data['foo']+1)",
            "my_task.set_data(copy=my_task.data['foo'])"
            ])
        task1.connect(task2)
        task3 = Simple(self.wf_spec, 'Last')
        task2.connect(task3)

        expected = 'Start\n  First\n    Second\n      Last\n'
        workflow = run_workflow(self, self.wf_spec, expected, '')
        first = workflow.get_tasks_from_spec_name('First')[0]
        last = workflow.get_tasks_from_spec_name('Last')[0]
        self.assertEqual(first.data.get('foo'), 1)
        self.assertEqual(last.data.get('foo'), 2)
        self.assertEqual(last.data.get('copy'), 2)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TransformTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = WorkflowSpecTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import os
import sys
import unittest
data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import pickle
from random import randint
try:
    from util import track_workflow
except ImportError as e:
    from tests.SpiffWorkflow.util import track_workflow
from SpiffWorkflow import Workflow
from SpiffWorkflow.specs import Join, WorkflowSpec
from SpiffWorkflow.storage import XmlSerializer

serializer = XmlSerializer()
data_file = 'data.pkl'

class WorkflowSpecTest(unittest.TestCase):
    CORRELATE = WorkflowSpec

    def setUp(self):
        self.wf_spec = WorkflowSpec()

    def testConstructor(self):
        spec = WorkflowSpec('my spec')
        self.assertEqual('my spec', spec.name)

    def testGetTaskSpecFromName(self):
        pass #FIXME

    def testGetDump(self):
        pass #FIXME

    def testDump(self):
        pass #FIXME

    def doPickleSingle(self, workflow, expected_path):
        taken_path = track_workflow(workflow.spec)

        # Execute a random number of steps.
        for i in range(randint(0, len(workflow.spec.task_specs))):
            workflow.complete_next()

        # Store the workflow instance in a file.
        output = open(data_file, 'wb')
        pickle.dump(workflow, output, -1)
        output.close()
        before = workflow.get_dump()

        # Load the workflow instance from a file and delete the file.
        input = open(data_file, 'rb')
        workflow = pickle.load(input)
        input.close()
        os.remove(data_file)
        after = workflow.get_dump()

        # Make sure that the state of the workflow did not change.
        self.assert_(before == after, 'Before:\n' + before + '\n' \
                                    + 'After:\n'  + after  + '\n')

        # Re-connect signals, because the pickle dump now only contains a
        # copy of taken_path.
        taken_path = track_workflow(workflow.spec, taken_path)

        # Run the rest of the workflow.
        workflow.complete_all()
        after = workflow.get_dump()
        self.assert_(workflow.is_completed(), 'Workflow not complete:' + after)
        #taken_path = '\n'.join(taken_path) + '\n'
        if taken_path != expected_path:
            for taken, expected in zip(taken_path, expected_path):
                print("TAKEN:   ", taken)
                print("EXPECTED:", expected)
        self.assertEqual(expected_path, taken_path)

    def testSerialize(self):
        # Read a complete workflow spec.
        xml_file      = os.path.join(data_dir, 'spiff', 'workflow1.xml')
        xml           = open(xml_file).read()
        path_file     = os.path.splitext(xml_file)[0] + '.path'
        expected_path = open(path_file).read().strip().split('\n')
        wf_spec       = WorkflowSpec.deserialize(serializer, xml)

        for i in range(5):
            workflow = Workflow(wf_spec)
            self.doPickleSingle(workflow, expected_path)

    def testValidate(self):
        """
        Tests that we can detect when two wait taks are waiting on each
        other.
        """
        task1 = Join(self.wf_spec, 'First')
        self.wf_spec.start.connect(task1)
        task2 = Join(self.wf_spec, 'Second')
        task1.connect(task2)

        task2.follow(task1)
        task1.follow(task2)

        results = self.wf_spec.validate()
        self.assert_("Found loop with 'Second': Second->First then 'Second' "
                "again" in results)
        self.assert_("Found loop with 'First': First->Second then 'First' "
                "again" in results)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(WorkflowSpecTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = DictionarySerializerTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import sys, unittest, re, os
dirname = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(dirname, '..', '..', '..'))

from SpiffWorkflow.storage import DictionarySerializer
from .SerializerTest import SerializerTest, SerializeEveryPatternTest
from SpiffWorkflow import Workflow
import uuid

class DictionarySerializerTest(SerializerTest):
    CORRELATE = DictionarySerializer

    def setUp(self):
        SerializerTest.setUp(self)
        self.serializer = DictionarySerializer()
        self.serial_type = dict

    def compareSerialization(self, item1, item2, exclude_dynamic=False, exclude_items=[]):
        if exclude_dynamic:
            if 'last_state_change' not in exclude_items:
                exclude_items.append('last_state_change')
            if 'last_task' not in exclude_items:
                exclude_items.append('last_task')
            if uuid.UUID not in exclude_items:
                exclude_items.append(uuid.UUID)

        if isinstance(item1, dict):
            if not isinstance(item2, dict):
                raise Exception(": companion item is not a dict (is a " + str(type(item2)) + "): " + str(item1) + " v " + str(item2))
            for key, value in item1.items():
                if key not in item2:
                    raise Exception("Missing Key: " + key + " (in 1, not 2)")

                if key in exclude_items:
                    continue
                try:
                    self.compareSerialization(value, item2[key], exclude_dynamic=exclude_dynamic, exclude_items=exclude_items)
                except Exception as e:
                    raise Exception(key + '/' + str(e))

            for key, _ in item2.items():
                if key not in item1:
                    raise Exception("Missing Key: " + key + " (in 2, not 1)")
                
        elif isinstance(item1, list):
            if not isinstance(item2, list):
                raise Exception(": companion item is not a list (is a " + str(type(item2)) + ")")
            if not len(item1) == len(item2):
                raise Exception(": companion list is not the same length: " + str(len(item1)) + " v " + str(len(item2)))
            for i, listitem in enumerate(item1):
                try:
                    self.compareSerialization(listitem, item2[i], exclude_dynamic=exclude_dynamic, exclude_items=exclude_items)
                except Exception as e:
                    raise Exception('[' + str(i) + ']/' + str(e))

        elif isinstance(item1, Workflow):
            raise Exception("Item is a Workflow")
        
        else:
            if type(item1) != type(item2):
                raise Exception(": companion item is not the same type (is a " + str(type(item2)) + "): " + str(item1) + " v " + str(item2))
            if type(item1) in exclude_items:
                return
            if item1 != item2:
                raise Exception("Unequal: " + repr(item1) \
                                + " vs " + repr(item2)) 
        

    def testConstructor(self):
        DictionarySerializer()


class DictionarySerializeEveryPatternTest(SerializeEveryPatternTest):

    def setUp(self):
        super(DictionarySerializeEveryPatternTest, self).setUp()
        self.serializerTestClass = DictionarySerializerTest(methodName='testConstructor')
        self.serializerTestClass.setUp()


def suite():
    tests = unittest.defaultTestLoader.loadTestsFromTestCase(DictionarySerializerTest)
    tests.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(DictionarySerializeEveryPatternTest))
    return tests
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = JSONSerializerTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import sys, unittest, re, os
dirname = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(dirname, '..', '..', '..'))

from SpiffWorkflow.storage import JSONSerializer
from .SerializerTest import SerializerTest, SerializeEveryPatternTest
from .DictionarySerializerTest import DictionarySerializerTest
import json

class JSONSerializerTest(SerializerTest):
    CORRELATE = JSONSerializer

    def setUp(self):
        SerializerTest.setUp(self)
        self.serializer = JSONSerializer()
        self.serial_type = str

    def testConstructor(self):
        JSONSerializer()

    def compareSerialization(self, s1, s2, exclude_dynamic=False):
        obj1 = json.loads(s1)
        obj2 = json.loads(s2)
        #print(s1)
        #print(s2)
        if exclude_dynamic:
            exclude_items = ['__uuid__']
        else:
            exclude_items = []
        DictionarySerializerTest(methodName='testConstructor').compareSerialization(obj1, obj2,
                                                                                    exclude_dynamic=exclude_dynamic,
                                                                                    exclude_items=exclude_items)

class JSONSerializeEveryPatternTest(SerializeEveryPatternTest):

    def setUp(self):
        super(JSONSerializeEveryPatternTest, self).setUp()
        self.serializerTestClass = JSONSerializerTest(methodName='testConstructor')
        self.serializerTestClass.setUp()


def suite():
    tests = unittest.defaultTestLoader.loadTestsFromTestCase(JSONSerializerTest)
    tests.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(JSONSerializeEveryPatternTest))
    return tests
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = OpenWfeXmlSerializerTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import sys, unittest, re, os
dirname = os.path.dirname(__file__)
data_dir = os.path.join(dirname, '..', 'data')
sys.path.insert(0, os.path.join(dirname, '..'))
sys.path.insert(0, os.path.join(dirname, '..', '..', '..'))

from SpiffWorkflow.storage import OpenWfeXmlSerializer
from xml.parsers.expat import ExpatError
from .SerializerTest import SerializerTest
from PatternTest import run_workflow
from SpiffWorkflow.specs import WorkflowSpec

class OpenWfeXmlSerializerTest(SerializerTest):
    CORRELATE = OpenWfeXmlSerializer

    def setUp(self):
        SerializerTest.setUp(self)
        self.serializer = OpenWfeXmlSerializer()
        self.serial_type = str

    def testConstructor(self):
        OpenWfeXmlSerializer()

    def testSerializeWorkflowSpec(self):
        pass # Serialization not yet supported.

    def testDeserializeWorkflowSpec(self):
        xml_file  = os.path.join(data_dir, 'openwfe', 'workflow1.xml')
        xml       = open(xml_file).read()
        path_file = os.path.splitext(xml_file)[0] + '.path'
        path      = open(path_file).read()
        wf_spec   = WorkflowSpec.deserialize(self.serializer, xml)

        run_workflow(self, wf_spec, path, None)

    def testSerializeWorkflow(self):
        pass # Serialization not yet supported.

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(OpenWfeXmlSerializerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = SerializerTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import sys, unittest, re, os
dirname = os.path.dirname(__file__)
data_dir = os.path.join(dirname, '..', 'data')
sys.path.insert(0, os.path.join(dirname, '..'))

from PatternTest import run_workflow, PatternTest
from SpiffWorkflow.storage.Serializer import Serializer
from SpiffWorkflow.specs import WorkflowSpec
from SpiffWorkflow import Workflow
from SpiffWorkflow.storage.exceptions import TaskSpecNotSupportedError, \
     TaskNotSupportedError
from data.spiff.workflow1 import TestWorkflowSpec
import warnings
from uuid import UUID


class SerializerTest(unittest.TestCase):
    CORRELATE = Serializer

    def setUp(self):
        self.wf_spec = TestWorkflowSpec()
        self.serializer = None
        self.serial_type = None

    def testConstructor(self):
        Serializer()

    def testSerializeWorkflowSpec(self, path_file=None, data=None):
        if self.serializer is None:
            return

        # Back to back testing.
        try:
            serialized1 = self.wf_spec.serialize(self.serializer)
            wf_spec     = WorkflowSpec.deserialize(self.serializer, serialized1)
            serialized2 = wf_spec.serialize(self.serializer)
        except TaskSpecNotSupportedError as e:
            pass
        else:
            self.assert_(isinstance(serialized1, self.serial_type))
            self.assert_(isinstance(serialized2, self.serial_type))
            self.compareSerialization(serialized1, serialized2)

            # Test whether the restored workflow still works.
            if path_file is None:
                path_file = os.path.join(data_dir, 'spiff', 'workflow1.path')
                path      = open(path_file).read()
            elif os.path.exists(path_file):
                path = open(path_file).read()
            else:
                path = None

            run_workflow(self, wf_spec, path, data)

    def compareSerialization(self, s1, s2, exclude_dynamic=False):
        if exclude_dynamic:
            warnings.warn("Asked to exclude dynamic in a compareSerialization that does not support it. The result may be wrong.")
        self.assertEqual(s1, s2)

    def testDeserializeWorkflowSpec(self):
        pass # Already covered in testSerializeWorkflowSpec()

    def testSerializeWorkflow(self, path_file=None, data=None):
        if self.serializer is None:
            return
        
        if path_file is None:
            path_file = os.path.join(data_dir, 'spiff', 'workflow1.path')
            path      = open(path_file).read()
        elif os.path.exists(path_file):
            path = open(path_file).read()
        else:
            path = None

        # run a workflow fresh from the spec to completion, see if it
        # serialises and deserialises correctly.
        workflow_without_save  = run_workflow(self, self.wf_spec, path, data)
        try:
            serialized1 = workflow_without_save.serialize(self.serializer)
            restored_wf = Workflow.deserialize(self.serializer, serialized1)
            serialized2 = restored_wf.serialize(self.serializer)
        except TaskNotSupportedError as e:
            return
        else:
            self.assert_(isinstance(serialized1, self.serial_type))
            self.assert_(isinstance(serialized2, self.serial_type))
            self.compareSerialization(serialized1, serialized2)

        # try an freshly started workflow, see if it serialises and
        # deserialiases correctly. (no longer catch for exceptions: if they
        # were going to happen they should have happened already.)
        workflow = Workflow(self.wf_spec)
        serialized1 = workflow.serialize(self.serializer)
        restored_wf = Workflow.deserialize(self.serializer, serialized1)
        serialized2 = restored_wf.serialize(self.serializer)
        self.assert_(isinstance(serialized1, self.serial_type))
        self.assert_(isinstance(serialized2, self.serial_type))
        self.compareSerialization(serialized1, serialized2)
        self.assertFalse(restored_wf.is_completed())

        # Run it to completion, see if it serialises and deserialises correctly
        # also check if the restored and unrestored ones are the same after
        # being run through.
        workflow_unrestored = run_workflow(self, self.wf_spec, path, data, workflow=workflow)
        workflow_restored = run_workflow(self, self.wf_spec, path, data, workflow=restored_wf)

        serialized1 = workflow_restored.serialize(self.serializer)
        restored_wf = Workflow.deserialize(self.serializer, serialized1)
        serialized2 = restored_wf.serialize(self.serializer)
        self.assert_(isinstance(serialized1, self.serial_type))
        self.assert_(isinstance(serialized2, self.serial_type))
        self.compareSerialization(serialized1, serialized2)
        serialized_crosscheck = workflow_unrestored.serialize(self.serializer)
        self.assert_(isinstance(serialized_crosscheck, self.serial_type))
        # compare the restored and unrestored completed ones. Because they ran
        # separately, exclude the last_state_change time. Because you can have
        # dynamically created tasks, don't compare (uu)ids.
        self.compareSerialization(serialized_crosscheck, serialized2,
                                  exclude_dynamic=True)
        

    def testDeserializeWorkflow(self):
        pass # Already covered in testSerializeWorkflow()


class SerializeEveryPatternTest(PatternTest):
    def setUp(self):
        super(SerializeEveryPatternTest, self).setUp()
        self.serializerTestClass = SerializerTest(methodName='testConstructor')
        self.serializerTestClass.setUp()
        # we don't set self.serializer - that's set by the superclass to the
        # XML (de)serializer.

    def run_pattern(self, filename):
        # Load the .path file.
        path_file = os.path.splitext(filename)[0] + '.path'
        

        # Load the .data file.
        data_file = os.path.splitext(filename)[0] + '.data'
        if os.path.exists(data_file):
            expected_data = open(data_file, 'r').read()
        else:
            expected_data = None

        # Test patterns that are defined in XML format.
        if filename.endswith('.xml'):
            xml     = open(filename).read()
            wf_spec = WorkflowSpec.deserialize(self.serializer, xml, filename = filename)
            self.serializerTestClass.wf_spec = wf_spec
            self.serializerTestClass.testSerializeWorkflowSpec(path_file=path_file,
                                                               data=expected_data)
            self.serializerTestClass.testSerializeWorkflow(path_file=path_file,
                                                           data=expected_data)

        # Test patterns that are defined in Python.
        if filename.endswith('.py') and not filename.endswith('__.py'):
            code    = compile(open(filename).read(), filename, 'exec')
            thedict = {}
            result  = eval(code, thedict)
            wf_spec = thedict['TestWorkflowSpec']()
            self.serializerTestClass.wf_spec = wf_spec
            self.serializerTestClass.testSerializeWorkflowSpec(path_file=path_file,
                                                               data=expected_data)
            self.serializerTestClass.testSerializeWorkflow(path_file=path_file,
                                                           data=expected_data)

        
def suite():
    tests = unittest.defaultTestLoader.loadTestsFromTestCase(SerializerTest)
    # explicitly *don't* load the Every Pattern tester here - it creates lots of
    # totally useless output
    #tests.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(SerializeEveryPatternTest))
    return tests
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = XmlSerializerTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import sys, unittest, re, os
dirname = os.path.dirname(__file__)
data_dir = os.path.join(dirname, '..', 'data')
sys.path.insert(0, os.path.join(dirname, '..', '..', '..'))

from SpiffWorkflow.storage import XmlSerializer
from xml.parsers.expat import ExpatError
from .SerializerTest import SerializerTest
from PatternTest import run_workflow
from SpiffWorkflow.specs import WorkflowSpec

class XmlSerializerTest(SerializerTest):
    CORRELATE = XmlSerializer

    def setUp(self):
        SerializerTest.setUp(self)
        self.serializer = XmlSerializer()
        self.serial_type = str

    def testConstructor(self):
        XmlSerializer()

    def testSerializeWorkflowSpec(self):
        pass # Serialization not yet supported.

    def testDeserializeWorkflowSpec(self):
        xml_file  = os.path.join(data_dir, 'spiff', 'workflow1.xml')
        xml       = open(xml_file).read()
        path_file = os.path.splitext(xml_file)[0] + '.path'
        path      = open(path_file).read()
        wf_spec   = WorkflowSpec.deserialize(self.serializer, xml)

        run_workflow(self, wf_spec, path, None)

    def testSerializeWorkflow(self):
        pass # Serialization not yet supported.
        
def suite():
    return unittest.TestLoader().loadTestsFromTestCase(XmlSerializerTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = TaskTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from SpiffWorkflow import Task
from SpiffWorkflow.specs import WorkflowSpec, Simple
from SpiffWorkflow.exceptions import WorkflowException

class MockWorkflow(object):
    pass

class TaskTest(unittest.TestCase):
    def setUp(self):
        Task.id_pool = 0
        Task.thread_id_pool = 0

    def testTree(self):
        # Build a tree.
        spec     = WorkflowSpec()
        workflow = MockWorkflow()
        task1    = Simple(spec, 'Simple 1')
        task2    = Simple(spec, 'Simple 2')
        task3    = Simple(spec, 'Simple 3')
        task4    = Simple(spec, 'Simple 4')
        task5    = Simple(spec, 'Simple 5')
        task6    = Simple(spec, 'Simple 6')
        task7    = Simple(spec, 'Simple 7')
        task8    = Simple(spec, 'Simple 8')
        task9    = Simple(spec, 'Simple 9')
        root     = Task(workflow, task1)
        c1       = root._add_child(task2)
        c11      = c1._add_child(task3)
        c111     = c11._add_child(task4)
        c1111    = Task(workflow, task5, c111)
        c112     = Task(workflow, task6, c11)
        c12      = Task(workflow, task7, c1)
        c2       = Task(workflow, task8, root)
        c3       = Task(workflow, task9, root)
        c3.state = Task.COMPLETED

        # Check whether the tree is built properly.
        expected = """!/0: Task of Simple 1 State: MAYBE Children: 3
  !/0: Task of Simple 2 State: MAYBE Children: 2
    !/0: Task of Simple 3 State: MAYBE Children: 2
      !/0: Task of Simple 4 State: MAYBE Children: 1
        !/0: Task of Simple 5 State: MAYBE Children: 0
      !/0: Task of Simple 6 State: MAYBE Children: 0
    !/0: Task of Simple 7 State: MAYBE Children: 0
  !/0: Task of Simple 8 State: MAYBE Children: 0
  !/0: Task of Simple 9 State: COMPLETED Children: 0"""
        expected = re.compile(expected.replace('!', r'([0-9a-f\-]+)'))
        self.assert_(expected.match(root.get_dump()),
                     'Expected:\n' + repr(expected.pattern) + '\n' + \
                     'but got:\n'  + repr(root.get_dump()))

        # Now remove one line from the expected output for testing the
        # filtered iterator.
        expected2 = ''
        for line in expected.pattern.split('\n'):
            if line.find('Simple 9') >= 0:
                continue
            expected2 += line.lstrip() + '\n'
        expected2 = re.compile(expected2)

        # Run the iterator test.
        result = ''
        for thetask in Task.Iterator(root, Task.MAYBE):
            result += thetask.get_dump(0, False) + '\n'
        self.assert_(expected2.match(result),
                     'Expected:\n' + repr(expected2.pattern) + '\n' + \
                     'but got:\n'  + repr(result))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TaskTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import time
from SpiffWorkflow import Workflow, Task

def on_reached_cb(workflow, task, taken_path):
    reached_key = "%s_reached" % str(task.get_name())
    n_reached   = task.get_data(reached_key, 0) + 1
    task.set_data(**{reached_key:       n_reached,
                     'two':             2,
                     'three':           3,
                     'test_attribute1': 'false',
                     'test_attribute2': 'true'})

    # Collect a list of all data.
    atts = []
    for key, value in task.data.items():
        if key in ['data',
                   'two',
                   'three',
                   'test_attribute1',
                   'test_attribute2']:
            continue
        if key.endswith('reached'):
            continue
        atts.append('='.join((key, str(value))))

    # Collect a list of all task data.
    props = []
    for key, value in task.task_spec.data.items():
        props.append('='.join((key, str(value))))
    #print "REACHED:", task.get_name(), atts, props

    # Store the list of data in the workflow.
    atts  = ';'.join(atts)
    props = ';'.join(props)
    old   = task.get_data('data', '')
    data  = task.get_name() + ': ' + atts + '/' + props + '\n'
    task.set_data(data = old + data)

    # In workflows that load a subworkflow, the newly loaded children
    # will not have on_reached_cb() assigned. By using this function, we
    # re-assign the function in every step, thus making sure that new
    # children also call on_reached_cb().
    for child in task.children:
        track_task(child.task_spec, taken_path)
    return True

def on_complete_cb(workflow, task, taken_path):
    # Record the path.
    indent = '  ' * (task._get_depth() - 1)
    taken_path.append('%s%s' % (indent, task.get_name()))
    return True

def track_task(task_spec, taken_path):
    if task_spec.reached_event.is_connected(on_reached_cb):
        task_spec.reached_event.disconnect(on_reached_cb)
    task_spec.reached_event.connect(on_reached_cb, taken_path)
    if task_spec.completed_event.is_connected(on_complete_cb):
        task_spec.completed_event.disconnect(on_complete_cb)
    task_spec.completed_event.connect(on_complete_cb, taken_path)

def track_workflow(wf_spec, taken_path = None):
    if taken_path is None:
        taken_path = []
    for name in wf_spec.task_specs:
        track_task(wf_spec.task_specs[name], taken_path)
    return taken_path

def run_workflow(test, wf_spec, expected_path, expected_data, workflow=None):
    # Execute all tasks within the Workflow.
    if workflow is None:
        taken_path = track_workflow(wf_spec)
        workflow   = Workflow(wf_spec)
    else:
        taken_path = track_workflow(workflow.spec)
        
    test.assert_(not workflow.is_completed(), 'Workflow is complete before start')
    try:
        # We allow the workflow to require a maximum of 5 seconds to
        # complete, to allow for testing long running tasks.
        for i in range(10):
            workflow.complete_all(False)
            if workflow.is_completed():
                break
            time.sleep(0.5)
    except:
        workflow.task_tree.dump()
        raise

    #workflow.task_tree.dump()
    test.assert_(workflow.is_completed(),
                 'complete_all() returned, but workflow is not complete\n'
               + workflow.task_tree.get_dump())

    # Make sure that there are no waiting tasks left in the tree.
    for thetask in Task.Iterator(workflow.task_tree, Task.READY):
        workflow.task_tree.dump()
        raise Exception('Task with state READY: %s' % thetask.name)

    # Check whether the correct route was taken.
    if expected_path is not None:
        taken_path = '\n'.join(taken_path) + '\n'
        error      = 'Expected:\n'
        error     += '%s\n'        % expected_path
        error     += 'but got:\n'
        error     += '%s\n'        % taken_path
        test.assert_(taken_path == expected_path, error)

    # Check data availibility.
    if expected_data is not None:
        result   = workflow.get_data('data', '')
        error    = 'Expected:\n'
        error   += '%s\n'        % expected_data
        error   += 'but got:\n'
        error   += '%s\n'        % result
        test.assert_(result == expected_data, error)

    return workflow

########NEW FILE########
__FILENAME__ = WorkflowTest
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
import sys, unittest, re, os
data_dir = os.path.join(os.path.dirname(__file__), 'data')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from SpiffWorkflow import Workflow
from SpiffWorkflow.specs import *
from SpiffWorkflow.operators import *
from SpiffWorkflow.Task import *
from SpiffWorkflow.storage import XmlSerializer

class WorkflowTest(unittest.TestCase):
    def testConstructor(self):
        wf_spec = WorkflowSpec()
        wf_spec.start.connect(Cancel(wf_spec, 'name'))
        workflow = Workflow(wf_spec)

    def testBeginWorkflowStepByStep(self):
        """
        Simulates interactive calls, as would be issued by a user.
        """
        xml_file = os.path.join(data_dir, 'spiff', 'workflow1.xml')
        xml      = open(xml_file).read()
        wf_spec  = WorkflowSpec.deserialize(XmlSerializer(), xml)
        workflow = Workflow(wf_spec)

        tasks = workflow.get_tasks(Task.READY)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].task_spec.name, 'Start')
        workflow.complete_task_from_id(tasks[0].id)
        self.assertEqual(tasks[0].state, Task.COMPLETED)

        tasks = workflow.get_tasks(Task.READY)
        self.assertEqual(len(tasks), 2)
        task_a1 = tasks[0]
        task_b1 = tasks[1]
        self.assertEqual(task_a1.task_spec.__class__, Simple)
        self.assertEqual(task_a1.task_spec.name, 'task_a1')
        self.assertEqual(task_b1.task_spec.__class__, Simple)
        self.assertEqual(task_b1.task_spec.name, 'task_b1')
        workflow.complete_task_from_id(task_a1.id)
        self.assertEqual(task_a1.state, Task.COMPLETED)

        tasks = workflow.get_tasks(Task.READY)
        self.assertEqual(len(tasks), 2)
        self.assertTrue(task_b1 in tasks)
        task_a2 = tasks[0]
        self.assertEqual(task_a2.task_spec.__class__, Simple)
        self.assertEqual(task_a2.task_spec.name, 'task_a2')
        workflow.complete_task_from_id(task_a2.id)

        tasks = workflow.get_tasks(Task.READY)
        self.assertEqual(len(tasks), 1)
        self.assertTrue(task_b1 in tasks)

        workflow.complete_task_from_id(task_b1.id)
        tasks = workflow.get_tasks(Task.READY)
        self.assertEqual(len(tasks), 1)
        workflow.complete_task_from_id(tasks[0].id)

        tasks = workflow.get_tasks(Task.READY)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].task_spec.name, 'synch_1')
        # haven't reached the end of the workflow, but stopping at "synch_1"

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(WorkflowTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())

########NEW FILE########
