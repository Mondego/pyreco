__FILENAME__ = directives

from docutils import nodes
from docutils.parsers.rst.directives import unchanged_required, unchanged, flag

import os
import sys
import copy
import fnmatch
import re
import textwrap
import collections
import subprocess

from docutils.parsers import rst
from docutils.statemachine import ViewList
from sphinx.domains.cpp import DefinitionParser

from breathe.finder.core import FinderFactory, NoMatchesError, MultipleMatchesError
from breathe.parser import DoxygenParserFactory, CacheFactory, ParserError, FileIOError
from breathe.renderer.rst.doxygen import DoxygenToRstRendererFactoryCreatorConstructor, RstContentCreator
from breathe.renderer.rst.doxygen import format_parser_error
from breathe.renderer.rst.doxygen.domain import DomainHandlerFactoryCreator, NullDomainHandler
from breathe.renderer.rst.doxygen.domain import CppDomainHelper, CDomainHelper
from breathe.renderer.rst.doxygen.filter import FilterFactory, GlobFactory
from breathe.renderer.rst.doxygen.target import TargetHandlerFactory
from breathe.finder.doxygen.core import DoxygenItemFinderFactoryCreator
from breathe.finder.doxygen.matcher import ItemMatcherFactory
from breathe.transforms import DoxygenTransform, DoxygenAutoTransform, TransformWrapper, IndexHandler
from breathe.nodes import DoxygenNode, DoxygenAutoNode
from breathe.process import DoxygenProcessHandle

import docutils.nodes
import sphinx.addnodes
import sphinx.ext.mathbase

# Somewhat outrageously, reach in and fix a Sphinx regex
import sphinx.domains.cpp
sphinx.domains.cpp._identifier_re = re.compile(r'(~?\b[a-zA-Z_][a-zA-Z0-9_]*)\b')

class BreatheError(Exception):
    pass

class NoMatchingFunctionError(BreatheError):
    pass

class UnableToResolveFunctionError(BreatheError):
    pass

class ProjectError(BreatheError):
    pass

class NoDefaultProjectError(ProjectError):
    pass

class NodeNotFoundError(BreatheError):
    pass

class BaseDirective(rst.Directive):

    def __init__(
            self,
            root_data_object,
            renderer_factory_creator_constructor,
            finder_factory,
            matcher_factory,
            project_info_factory,
            filter_factory,
            target_handler_factory,
            *args
            ):
        rst.Directive.__init__(self, *args)

        self.root_data_object = root_data_object
        self.renderer_factory_creator_constructor = renderer_factory_creator_constructor
        self.finder_factory = finder_factory
        self.matcher_factory = matcher_factory
        self.project_info_factory = project_info_factory
        self.filter_factory = filter_factory
        self.target_handler_factory = target_handler_factory

    def render(self, data_object, project_info, filter_, target_handler):
        "Standard render process used by subclasses"

        renderer_factory_creator = self.renderer_factory_creator_constructor.create_factory_creator(
                project_info,
                self.state.document,
                self.options,
                target_handler
                )

        try:
            renderer_factory = renderer_factory_creator.create_factory(
                    data_object,
                    self.state,
                    self.state.document,
                    filter_,
                    target_handler,
                    )
        except ParserError, e:
            return format_parser_error("doxygenclass", e.error, e.filename, self.state, self.lineno, True)
        except FileIOError, e:
            return format_parser_error("doxygenclass", e.error, e.filename, self.state, self.lineno)

        object_renderer = renderer_factory.create_renderer(self.root_data_object, data_object)
        node_list = object_renderer.render()

        return node_list

# Directives
# ----------

class DoxygenIndexDirective(BaseDirective):

    required_arguments = 0
    optional_arguments = 2
    option_spec = {
            "path": unchanged_required,
            "project": unchanged_required,
            "outline": flag,
            "no-link": flag,
            }
    has_content = False

    def run(self):

        try:
            project_info = self.project_info_factory.create_project_info(self.options)
        except ProjectError, e:
            warning = 'doxygenindex: %s' % e
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]

        handler = IndexHandler(
                "doxygenindex",
                project_info,
                self.options,
                self.state,
                self.lineno,
                self
                )

        return [DoxygenNode(handler)]

class AutoDoxygenIndexDirective(BaseDirective):

    required_arguments = 1
    final_argument_whitespace = True
    option_spec = {
            "source-path": unchanged_required,
            "source": unchanged_required,
            "outline": flag,
            "no-link": flag,
            }
    has_content = False

    def run(self):

        files = self.arguments[0].split()

        try:
            project_info = self.project_info_factory.create_auto_project_info(self.options)
        except ProjectError, e:
            warning = 'autodoxygenindex: %s' % e
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]

        return [DoxygenAutoNode(project_info, files, self.options, self, self.state, self.lineno)]


class DoxygenFunctionDirective(BaseDirective):

    required_arguments = 1
    option_spec = {
            "path": unchanged_required,
            "project": unchanged_required,
            "outline": flag,
            "no-link": flag,
            }
    has_content = False
    final_argument_whitespace = True

    def run(self):

        # Separate possible arguments (delimited by a "(") from the namespace::name
        match = re.match( r"([^(]*)(.*)", self.arguments[0] )
        namespaced_function, args = match.group(1), match.group(2)

        # Split the namespace and the function name
        try:
            (namespace, function_name) = namespaced_function.rsplit( "::", 1 )
        except ValueError:
            (namespace, function_name) = "", namespaced_function

        try:
            project_info = self.project_info_factory.create_project_info(self.options)
        except ProjectError, e:
            warning = 'doxygenfunction: %s' % e
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]

        finder = self.finder_factory.create_finder(project_info)

        # Extract arguments from the function name.
        args = self.parse_args(args)

        matcher_stack = self.matcher_factory.create_matcher_stack(
                {
                    "compound": self.matcher_factory.create_name_matcher(namespace),
                    "member": self.matcher_factory.create_name_type_matcher(function_name, "function")
                },
                "member"
            )

        results = finder.find(matcher_stack)

        try:
            data_object = self.resolve_function(results, args)
        except NoMatchingFunctionError:
            warning = ('doxygenfunction: Cannot find function "%s%s" in doxygen xml output '
                    'for project "%s" from directory: %s'
                    % (namespace, function_name, project_info.name(), project_info.project_path()))
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]
        except UnableToResolveFunctionError:
            warning = ('doxygenfunction: Unable to resolve multiple matches for function "%s%s" with arguments (%s) in doxygen xml output '
                    'for project "%s" from directory: %s.'
                    % (namespace, function_name, ", ".join(args), project_info.name(), project_info.project_path()))
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]

        target_handler = self.target_handler_factory.create_target_handler(self.options, project_info, self.state.document)
        filter_ = self.filter_factory.create_outline_filter(self.options)

        return self.render(data_object, project_info, filter_, target_handler)


    def parse_args(self, function_description):

        paren_index = function_description.find('(')
        if paren_index == -1:
            return []
        else:
            # Parse the function name string, eg. f(int, float) to
            # extract the types so we can use them for matching
            args = []
            num_open_brackets = -1;
            start = paren_index + 1
            for i in range(paren_index, len(function_description)):
                c = function_description[i]
                if c == '(' or c == '<':
                    num_open_brackets += 1
                elif c == ')' or c == '>':
                    num_open_brackets -= 1
                elif c == ',' and num_open_brackets == 0:
                    args.append(function_description[start:i].strip())
                    start = i + 1
            args.append(function_description[start:-1].strip())

            return args


    def resolve_function(self, matches, args):

        if not matches:
            raise NoMatchingFunctionError()

        if len(matches) == 1:
            return matches[0]

        data_object = None

        # Tries to match the args array agains the arguments listed in the
        # doxygen data
        # TODO: We don't have any doxygen xml dom accessing code at this level
        # this might benefit from being abstracted away at some point
        for entry in matches:
            if len(args) == len(entry.param):
                equal = True
                for i in range(len(args)):
                    param_type = entry.param[i].type_.content_[0].value
                    if not isinstance(param_type, unicode) :
                        param_type = param_type.valueOf_
                    if args[i] != param_type:
                        equal = False
                        break
                if equal:
                    data_object = entry
                    break

        if not data_object:
            raise UnableToResolveFunctionError()

        return data_object


class DoxygenClassDirective(BaseDirective):

    kind = "class"

    required_arguments = 1
    optional_arguments = 1
    option_spec = {
            "path": unchanged_required,
            "project": unchanged_required,
            "members": unchanged,
            "sections": unchanged,
            "show": unchanged_required,
            "outline": flag,
            "no-link": flag,
            }
    has_content = False

    def run(self):

        name = self.arguments[0]

        try:
            project_info = self.project_info_factory.create_project_info(self.options)
        except ProjectError, e:
            warning = 'doxygen%s: %s' % (self.kind, e)
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]

        finder = self.finder_factory.create_finder(project_info)

        matcher_stack = self.matcher_factory.create_matcher_stack(
                {
                    "compound": self.matcher_factory.create_name_type_matcher(name, self.kind)
                },
                "compound"
            )

        try:
            data_object = finder.find_one(matcher_stack)
        except NoMatchesError, e:
            warning = ('doxygen%s: Cannot find %s "%s" in doxygen xml output for project "%s" from directory: %s'
                    % (self.kind, self.kind, name, project_info.name(), project_info.project_path()))
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]

        target_handler = self.target_handler_factory.create_target_handler(self.options, project_info, self.state.document)
        filter_ = self.filter_factory.create_class_filter(self.options)

        return self.render(data_object, project_info, filter_, target_handler)


class DoxygenFileDirective(BaseDirective):

    kind = "file"

    required_arguments = 1
    optional_arguments = 1
    option_spec = {
            "path": unchanged_required,
            "project": unchanged_required,
            "no-link": flag,
            }
    has_content = False

    def run(self):

        name = self.arguments[0]

        try:
            project_info = self.project_info_factory.create_project_info(self.options)
        except ProjectError, e:
            warning = 'doxygenfile: %s' % e
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]

        finder = self.finder_factory.create_finder(project_info)

        finder_filter = self.filter_factory.create_file_finder_filter(name)

        matches = []
        finder.filter_(finder_filter, matches)

        if len(matches) > 1:
            warning = ('doxygenfile: Found multiple matches for file "%s" in doxygen xml output for project "%s" '
                    'from directory: %s' % (name, project_info.name(), project_info.project_path()))
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]

        elif not matches:
            warning = ('doxygenfile: Cannot find file "%s" in doxygen xml output for project "%s" from directory: %s'
                    % (name, project_info.name(), project_info.project_path()))
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]

        target_handler = self.target_handler_factory.create_target_handler(self.options, project_info, self.state.document)
        filter_ = self.filter_factory.create_file_filter(name, self.options)

        renderer_factory_creator = self.renderer_factory_creator_constructor.create_factory_creator(
                project_info,
                self.state.document,
                self.options,
                target_handler
                )
        node_list = []

        # Unpack the single entry in the matches list and render it
        (data_object,) = matches
        renderer_factory = renderer_factory_creator.create_factory(
                data_object,
                self.state,
                self.state.document,
                filter_,
                target_handler,
                )

        object_renderer = renderer_factory.create_renderer(self.root_data_object, data_object)
        node_list.extend(object_renderer.render())

        return node_list



class DoxygenGroupDirective(BaseDirective):

    kind = "group"

    required_arguments = 1
    optional_arguments = 1
    option_spec = {
            "path": unchanged_required,
            "project": unchanged_required,
            "content-only": flag,
            "no-link": flag,
            }
    has_content = False

    def run(self):

        name = self.arguments[0]

        try:
            project_info = self.project_info_factory.create_project_info(self.options)
        except ProjectError, e:
            warning = 'doxygengroup: %s' % e
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]

        finder = self.finder_factory.create_finder(project_info)

        finder_filter = self.filter_factory.create_group_finder_filter(name)

        matches = []
        finder.filter_(finder_filter, matches)

        if len(matches) > 1:
            warning = ('doxygengroup: Found multiple matches for group "%s" in doxygen xml output for project "%s" '
                    'from directory: %s' % (name, project_info.name(), project_info.project_path()))
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]

        elif not matches:
            warning = ('doxygengroup: Cannot find group "%s" in doxygen xml output for project "%s" from directory: %s'
                    % (name, project_info.name(), project_info.project_path()))
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]

        if self.options.has_key("content-only"):

            # Unpack the single entry in the matches list
            (data_object,) = matches

            filter_ = self.filter_factory.create_group_content_filter()

            # Having found the compound node for the group in the index we want to grab the contents
            # of
            contents_finder = self.finder_factory.create_finder_from_root(data_object, project_info)
            contents = []
            contents_finder.filter_(filter_, contents)

            # Replaces matches with our new starting points
            matches = contents

        target_handler = self.target_handler_factory.create_target_handler(self.options, project_info, self.state.document)
        filter_ = self.filter_factory.create_open_filter()

        renderer_factory_creator = self.renderer_factory_creator_constructor.create_factory_creator(
                project_info,
                self.state.document,
                self.options,
                target_handler
                )
        node_list = []

        for data_object in matches:
            renderer_factory = renderer_factory_creator.create_factory(
                    data_object,
                    self.state,
                    self.state.document,
                    filter_,
                    target_handler,
                    )

            object_renderer = renderer_factory.create_renderer(self.root_data_object, data_object)
            node_list.extend(object_renderer.render())

        return node_list


class DoxygenBaseDirective(BaseDirective):

    required_arguments = 1
    optional_arguments = 1
    option_spec = {
            "path": unchanged_required,
            "project": unchanged_required,
            "outline": flag,
            "no-link": flag,
            }
    has_content = False

    def run(self):

        try:
            namespace, name = self.arguments[0].rsplit("::", 1)
        except ValueError:
            namespace, name = "", self.arguments[0]

        try:
            project_info = self.project_info_factory.create_project_info(self.options)
        except ProjectError, e:
            warning = 'doxygen%s: %s' % (self.kind, e)
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]

        finder = self.finder_factory.create_finder(project_info)

        matcher_stack = self.create_matcher_stack(namespace, name)

        try:
            data_object = finder.find_one(matcher_stack)
        except NoMatchesError, e:
            display_name = "%s::%s" % (namespace, name) if namespace else name
            warning = ('doxygen%s: Cannot find %s "%s" in doxygen xml output for project "%s" from directory: %s'
                    % (self.kind, self.kind, display_name, project_info.name(), project_info.project_path()))
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]

        target_handler = self.target_handler_factory.create_target_handler(self.options, project_info, self.state.document)
        filter_ = self.filter_factory.create_outline_filter(self.options)

        return self.render(data_object, project_info, filter_, target_handler)


class DoxygenStructDirective(DoxygenBaseDirective):

    kind = "struct"

    def create_matcher_stack(self, namespace, name):

        # Structs are stored in the xml file with their fully namespaced name
        # We're using C++ namespaces here, it might be best to make this file
        # type dependent
        #
        xml_name = "%s::%s" % (namespace, name) if namespace else name

        return self.matcher_factory.create_matcher_stack(
                {
                    "compound": self.matcher_factory.create_name_type_matcher(xml_name, self.kind)
                },
                "compound"
            )


# This class was the same as the DoxygenBaseDirective above, except that it
# wraps the output in a definition_list before passing it back. This should be
# abstracted in a far nicely way to avoid repeating so much code
#
# Now we're removed the definition_list wrap so we really need to refactor this!
class DoxygenBaseItemDirective(BaseDirective):

    required_arguments = 1
    optional_arguments = 1
    option_spec = {
            "path": unchanged_required,
            "project": unchanged_required,
            "outline": flag,
            "no-link": flag,
            }
    has_content = False

    def run(self):

        try:
            namespace, name = self.arguments[0].rsplit("::", 1)
        except ValueError:
            namespace, name = "", self.arguments[0]

        try:
            project_info = self.project_info_factory.create_project_info(self.options)
        except ProjectError, e:
            warning = 'doxygen%s: %s' % (self.kind, e)
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]

        finder = self.finder_factory.create_finder(project_info)

        matcher_stack = self.create_matcher_stack(namespace, name)

        try:
            data_object = finder.find_one(matcher_stack)
        except NoMatchesError, e:
            display_name = "%s::%s" % (namespace, name) if namespace else name
            warning = ('doxygen%s: Cannot find %s "%s" in doxygen xml output for project "%s" from directory: %s'
                    % (self.kind, self.kind, display_name, project_info.name(), project_info.project_path()))
            return [docutils.nodes.warning("", docutils.nodes.paragraph("", "", docutils.nodes.Text(warning))),
                    self.state.document.reporter.warning(warning, line=self.lineno)]

        target_handler = self.target_handler_factory.create_target_handler(self.options, project_info, self.state.document)
        filter_ = self.filter_factory.create_outline_filter(self.options)

        return self.render(data_object, project_info, filter_, target_handler)


class DoxygenVariableDirective(DoxygenBaseItemDirective):

    kind = "variable"

    def create_matcher_stack(self, namespace, name):

        return self.matcher_factory.create_matcher_stack(
                {
                    "compound": self.matcher_factory.create_name_matcher(namespace),
                    "member": self.matcher_factory.create_name_type_matcher(name, self.kind)
                },
                "member"
            )

class DoxygenDefineDirective(DoxygenBaseItemDirective):

    kind = "define"

    def create_matcher_stack(self, namespace, name):

        return self.matcher_factory.create_matcher_stack(
                {
                    "compound": self.matcher_factory.create_name_matcher(namespace),
                    "member": self.matcher_factory.create_name_type_matcher(name, self.kind)
                },
                "member"
            )

class DoxygenEnumDirective(DoxygenBaseItemDirective):

    kind = "enum"

    def create_matcher_stack(self, namespace, name):

        return self.matcher_factory.create_matcher_stack(
                {
                    "compound": self.matcher_factory.create_name_matcher(namespace),
                    "member": self.matcher_factory.create_name_type_matcher(name, self.kind)
                },
                "member"
            )

class DoxygenTypedefDirective(DoxygenBaseItemDirective):

    kind = "typedef"

    def create_matcher_stack(self, namespace, name):

        return self.matcher_factory.create_matcher_stack(
                {
                    "compound": self.matcher_factory.create_name_matcher(namespace),
                    "member": self.matcher_factory.create_name_type_matcher(name, self.kind)
                },
                "member"
            )

class DoxygenUnionDirective(DoxygenBaseItemDirective):

    kind = "union"

    def create_matcher_stack(self, namespace, name):

        # Unions are stored in the xml file with their fully namespaced name
        # We're using C++ namespaces here, it might be best to make this file
        # type dependent
        #
        xml_name = "%s::%s" % (namespace, name) if namespace else name

        return self.matcher_factory.create_matcher_stack(
                {
                    "compound": self.matcher_factory.create_name_type_matcher(xml_name, self.kind)
                },
                "compound"
            )


# Setup Administration
# --------------------

class DirectiveContainer(object):

    def __init__(
            self,
            directive,
            *args
            ):

        self.directive = directive
        self.args = args

        # Required for sphinx to inspect
        self.required_arguments = directive.required_arguments
        self.optional_arguments = directive.optional_arguments
        self.option_spec = directive.option_spec
        self.has_content = directive.has_content
        self.final_argument_whitespace = directive.final_argument_whitespace

    def __call__(self, *args):

        call_args = []
        call_args.extend(self.args)
        call_args.extend(args)

        return self.directive(*call_args)


class AutoProjectInfo(object):

    def __init__(
            self,
            name,
            source_path,
            build_dir,
            reference,
            source_dir,
            domain_by_extension,
            domain_by_file_pattern,
            match
            ):

        self._name = name
        self._source_path = source_path
        self._build_dir = build_dir
        self._reference = reference
        self._source_dir = source_dir
        self._domain_by_extension = domain_by_extension
        self._domain_by_file_pattern = domain_by_file_pattern
        self._match = match

    def name(self):
        return self._name

    def build_dir(self):
        return self._build_dir

    def abs_path_to_source_file(self, file_):
        """
        Returns full path to the provide file assuming that the provide path is relative to the
        projects source directory as specified in the breathe_projects_source config variable.
        """

        if os.path.isabs(self._source_path):
            full_source_path = self._source_path
        else:
            full_source_path = os.path.realpath(self._source_path)

        return os.path.join(full_source_path, file_)

    def create_project_info(self, project_path):

        return ProjectInfo(
            self._name,
            project_path,
            self._source_path,
            self._reference,
            self._source_dir,
            self._domain_by_extension,
            self._domain_by_file_pattern,
            self._match
            )

class ProjectInfo(object):

    def __init__(
            self,
            name,
            path,
            source_path,
            reference,
            source_dir,
            domain_by_extension,
            domain_by_file_pattern,
            match
            ):

        self._name = name
        self._project_path = path
        self._source_path = source_path
        self._reference = reference
        self._source_dir = source_dir
        self._domain_by_extension = domain_by_extension
        self._domain_by_file_pattern = domain_by_file_pattern
        self._match = match

    def name(self):
        return self._name

    def project_path(self):
        return self._project_path

    def source_path(self):
        return self._source_path

    def relative_path_to_xml_file(self, file_):
        """
        Returns relative path from Sphinx documentation top-level source directory to the specified
        file assuming that the specified file is a path relative to the doxygen xml output directory.
        """
        if os.path.isabs(self._project_path):
            full_xml_project_path = self._project_path
        else:
            full_xml_project_path = os.path.realpath(self._project_path)

        return os.path.relpath(
                os.path.join(full_xml_project_path, file_),
                self._source_dir
                )

    def sphinx_abs_path_to_file(self, file_):
        """
        Prepends os.path.sep to the value returned by relative_path_to_file.

        This is to match Sphinx's concept of an absolute path which starts from the top-level source
        directory of the project.
        """
        return os.path.sep + self.relative_path_to_xml_file(file_)

    def reference(self):
        return self._reference

    def domain_for_file(self, file_):

        domain = ""
        extension = file_.split(".")[-1]

        try:
            domain = self._domain_by_extension[extension]
        except KeyError:
            pass

        for pattern, pattern_domain in self._domain_by_file_pattern.items():
            if self._match(file_, pattern):
                domain = pattern_domain

        return domain


class ProjectInfoFactory(object):

    def __init__(self, source_dir, build_dir, match):

        self.source_dir = source_dir
        self.build_dir = build_dir
        self.match = match

        self.projects = {}
        self.default_project = None
        self.domain_by_extension = {}
        self.domain_by_file_pattern = {}

        self.project_count = 0
        self.project_info_store = {}
        self.auto_project_info_store = {}

    def update(
            self,
            projects,
            default_project,
            domain_by_extension,
            domain_by_file_pattern,
            projects_source,
            build_dir
            ):

        self.projects = projects
        self.default_project = default_project
        self.domain_by_extension = domain_by_extension
        self.domain_by_file_pattern = domain_by_file_pattern
        self.projects_source = projects_source

        # If the breathe config values has a non-empty value for build_dir then use that otherwise
        # stick with the default
        if build_dir:
            self.build_dir = build_dir

    def default_path(self):

        if not self.default_project:
            raise NoDefaultProjectError(
                    "No breathe_default_project config setting to fall back on "
                    "for directive with no 'project' or 'path' specified."
                    )

        try:
            return self.projects[self.default_project]
        except KeyError:
            raise ProjectError(
                    ( "breathe_default_project value '%s' does not seem to be a valid key for the "
                      "breathe_projects dictionary" ) % self.default_project
                    )

    def create_project_info(self, options):

        name = ""

        if "project" in options:
            try:
                path = self.projects[options["project"]]
                name = options["project"]
            except KeyError, e:
                raise ProjectError( "Unable to find project '%s' in breathe_projects dictionary" % options["project"] )

        elif "path" in options:
            path = options["path"]

        else:
            path = self.default_path()

        try:
            return self.project_info_store[path]
        except KeyError:

            reference = name

            if not name:
                name = "project%s" % self.project_count
                reference = path
                self.project_count += 1

            project_info = ProjectInfo(
                    name,
                    path,
                    "NoSourcePath",
                    reference,
                    self.source_dir,
                    self.domain_by_extension,
                    self.domain_by_file_pattern,
                    self.match
                    )

            self.project_info_store[path] = project_info

            return project_info

    def create_auto_project_info(self, options):

        name = ""

        if "source" in options:
            try:
                source_path = self.projects_source[options["source"]]
                name = options["source"]
            except KeyError, e:
                raise ProjectError( "Unable to find project '%s' in breathe_projects_source dictionary" % options["source"] )

        elif "source-path" in options:
            source_path = options["source-path"]

        else:
            raise ProjectError( "Unable to find either :project: or :path: specified" )

        # Key off the name concenated with the source path so that users can force separate projects
        # by specifying different source names for different directives even if they have the same
        # source path. This allows the autodoxygenindex directive to be used to represent specific
        # parts of a project by providing the relevant files and then declaring a source name which
        # is different to other autodoxygenindex directives which might be using the same
        # source_path.
        key = source_path
        if name:
            key = "%s:%s" % (name, source_path)

        try:
            return self.auto_project_info_store[key]
        except KeyError:

            reference = name

            if not name:
                name = "project%s" % self.project_count
                reference = source_path
                self.project_count += 1

            auto_project_info = AutoProjectInfo(
                    name,
                    source_path,
                    self.build_dir,
                    reference,
                    self.source_dir,
                    self.domain_by_extension,
                    self.domain_by_file_pattern,
                    self.match
                    )

            self.auto_project_info_store[key] = auto_project_info

            return auto_project_info

class DoxygenDirectiveFactory(object):

    directives = {
            "doxygenindex": DoxygenIndexDirective,
            "doxygenfunction": DoxygenFunctionDirective,
            "doxygenstruct": DoxygenStructDirective,
            "doxygenclass": DoxygenClassDirective,
            "doxygenvariable": DoxygenVariableDirective,
            "doxygendefine": DoxygenDefineDirective,
            "doxygenenum": DoxygenEnumDirective,
            "doxygentypedef": DoxygenTypedefDirective,
            "doxygenunion": DoxygenUnionDirective,
            "doxygenfile": DoxygenFileDirective,
            "doxygengroup": DoxygenGroupDirective,
            "autodoxygenindex": AutoDoxygenIndexDirective,
            }

    def __init__(
            self,
            root_data_object,
            renderer_factory_creator_constructor,
            finder_factory,
            matcher_factory,
            project_info_factory,
            filter_factory,
            target_handler_factory
            ):
        self.root_data_object = root_data_object
        self.renderer_factory_creator_constructor = renderer_factory_creator_constructor
        self.finder_factory = finder_factory
        self.matcher_factory = matcher_factory
        self.project_info_factory = project_info_factory
        self.filter_factory = filter_factory
        self.target_handler_factory = target_handler_factory

    def create_index_directive_container(self):
        return self.create_directive_container("doxygenindex")

    def create_function_directive_container(self):
        return self.create_directive_container("doxygenfunction")

    def create_struct_directive_container(self):
        return self.create_directive_container("doxygenstruct")

    def create_enum_directive_container(self):
        return self.create_directive_container("doxygenenum")

    def create_typedef_directive_container(self):
        return self.create_directive_container("doxygentypedef")

    def create_union_directive_container(self):
        return self.create_directive_container("doxygenunion")

    def create_class_directive_container(self):
        return self.create_directive_container("doxygenclass")

    def create_file_directive_container(self):
        return self.create_directive_container("doxygenfile")

    def create_group_directive_container(self):
        return self.create_directive_container("doxygengroup")

    def create_variable_directive_container(self):
        return self.create_directive_container("doxygenvariable")

    def create_define_directive_container(self):
        return self.create_directive_container("doxygendefine")

    def create_auto_index_directive_container(self):
        return self.create_directive_container("autodoxygenindex")

    def create_directive_container(self, type_):

        return DirectiveContainer(
                self.directives[type_],
                self.root_data_object,
                self.renderer_factory_creator_constructor,
                self.finder_factory,
                self.matcher_factory,
                self.project_info_factory,
                self.filter_factory,
                self.target_handler_factory
                )

    def get_config_values(self, app):

        # All DirectiveContainers maintain references to this project info factory
        # so we can update this to update them
        self.project_info_factory.update(
                app.config.breathe_projects,
                app.config.breathe_default_project,
                app.config.breathe_domain_by_extension,
                app.config.breathe_domain_by_file_pattern,
                app.config.breathe_projects_source,
                app.config.breathe_build_directory
                )


class NodeFactory(object):

    def __init__(self, *args):

        self.sources = args

    def __getattr__(self, node_name):

        for source in self.sources:
            try:
                return getattr(source, node_name)
            except AttributeError:
                pass

        raise NodeNotFoundError(node_name)


class RootDataObject(object):

    node_type = "root"


class PathHandler(object):

    def __init__(self, sep, basename, join):

        self.sep = sep
        self.basename = basename
        self.join = join

    def includes_directory(self, file_path):

        return bool( file_path.count( self.sep ) )

def write_file(directory, filename, content):

    # Check the directory exists
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Write the file with the provided contents
    with open(os.path.join(directory, filename), "w") as f:
        f.write(content)

class MTimer(object):

    def __init__(self, getmtime):
        self.getmtime = getmtime

    def get_mtime(self, filename):
        return self.getmtime(filename)

class FileStateCache(object):
    """
    Stores the modified time of the various doxygen xml files against the
    reStructuredText file that they are referenced from so that we know which
    reStructuredText files to rebuild if the doxygen xml is modified.

    We store the information in the environment object so that it is pickled
    down and stored between builds as Sphinx is designed to do.
    """

    def __init__(self, mtimer, app):

        self.app = app
        self.mtimer = mtimer

    def update(self, source_file):

        if not hasattr( self.app.env, "breathe_file_state" ):
            self.app.env.breathe_file_state = {}

        new_mtime = self.mtimer.get_mtime(source_file)

        mtime, docnames = self.app.env.breathe_file_state.setdefault(source_file, (new_mtime, set()))

        docnames.add(self.app.env.docname)

        self.app.env.breathe_file_state[source_file] = (new_mtime, docnames)

    def get_outdated(self, app, env, added, changed, removed):

        if not hasattr( self.app.env, "breathe_file_state" ):
            return []

        stale = []

        for filename, info in self.app.env.breathe_file_state.iteritems():
            old_mtime, docnames = info
            if self.mtimer.get_mtime(filename) > old_mtime:
                stale.extend(docnames)

        return list(set(stale).difference(removed))

    def purge_doc(self, app, env, docname):

        if not hasattr( self.app.env, "breathe_file_state" ):
            return

        toremove = []

        for filename, info in self.app.env.breathe_file_state.iteritems():

            _, docnames = info
            docnames.discard(docname)
            if not docnames:
                toremove.append(filename)

        for filename in toremove:
            del self.app.env.breathe_file_state[filename]

# Setup
# -----

def setup(app):

    cache_factory = CacheFactory()
    cache = cache_factory.create_cache()
    path_handler = PathHandler(os.sep, os.path.basename, os.path.join)
    mtimer = MTimer(os.path.getmtime)
    file_state_cache = FileStateCache(mtimer, app)
    parser_factory = DoxygenParserFactory(cache, path_handler, file_state_cache)
    matcher_factory = ItemMatcherFactory()
    item_finder_factory_creator = DoxygenItemFinderFactoryCreator(parser_factory, matcher_factory)
    index_parser = parser_factory.create_index_parser()
    finder_factory = FinderFactory(index_parser, item_finder_factory_creator)

    # Create a math_nodes object with a displaymath member for the displaymath
    # node so that we can treat it in the same way as the nodes & addnodes
    # modules in the NodeFactory
    math_nodes = collections.namedtuple("MathNodes", ["displaymath"])
    math_nodes.displaymath = sphinx.ext.mathbase.displaymath
    node_factory = NodeFactory(docutils.nodes, sphinx.addnodes, math_nodes)

    cpp_domain_helper = CppDomainHelper(DefinitionParser, re.sub)
    c_domain_helper = CDomainHelper()
    domain_helpers = {"c": c_domain_helper, "cpp": cpp_domain_helper}
    domain_handler_factory_creator = DomainHandlerFactoryCreator(node_factory, domain_helpers)

    rst_content_creator = RstContentCreator(ViewList, textwrap.dedent)
    default_domain_handler = NullDomainHandler()
    renderer_factory_creator_constructor = DoxygenToRstRendererFactoryCreatorConstructor(
            node_factory,
            parser_factory,
            default_domain_handler,
            domain_handler_factory_creator,
            rst_content_creator
            )

    # Assume general build directory is the doctree directory without the last component. We strip
    # off any trailing slashes so that dirname correctly drops the last part. This can be overriden
    # with the breathe_build_directory config variable
    build_dir = os.path.dirname(app.doctreedir.rstrip(os.sep))
    project_info_factory = ProjectInfoFactory(app.srcdir, build_dir, fnmatch.fnmatch)
    glob_factory = GlobFactory(fnmatch.fnmatch)
    filter_factory = FilterFactory(glob_factory, path_handler)
    target_handler_factory = TargetHandlerFactory(node_factory)

    root_data_object = RootDataObject()

    directive_factory = DoxygenDirectiveFactory(
            root_data_object,
            renderer_factory_creator_constructor,
            finder_factory,
            matcher_factory,
            project_info_factory,
            filter_factory,
            target_handler_factory
            )

    app.add_directive(
            "doxygenindex",
            directive_factory.create_index_directive_container(),
            )

    app.add_directive(
            "doxygenfunction",
            directive_factory.create_function_directive_container(),
            )

    app.add_directive(
            "doxygenstruct",
            directive_factory.create_struct_directive_container(),
            )

    app.add_directive(
            "doxygenenum",
            directive_factory.create_enum_directive_container(),
            )

    app.add_directive(
            "doxygentypedef",
            directive_factory.create_typedef_directive_container(),
            )

    app.add_directive(
            "doxygenunion",
            directive_factory.create_union_directive_container(),
            )

    app.add_directive(
            "doxygenclass",
            directive_factory.create_class_directive_container(),
            )

    app.add_directive(
            "doxygenfile",
            directive_factory.create_file_directive_container(),
            )

    app.add_directive(
            "doxygengroup",
            directive_factory.create_group_directive_container(),
            )

    app.add_directive(
            "doxygenvariable",
            directive_factory.create_variable_directive_container(),
            )

    app.add_directive(
            "doxygendefine",
            directive_factory.create_define_directive_container(),
            )

    app.add_directive(
            "autodoxygenindex",
            directive_factory.create_auto_index_directive_container(),
            )

    doxygen_handle = DoxygenProcessHandle(path_handler, subprocess.check_call, write_file)
    app.add_transform(TransformWrapper(DoxygenAutoTransform, doxygen_handle))

    app.add_transform(DoxygenTransform)

    app.add_node(DoxygenNode)

    app.add_config_value("breathe_projects", {}, True)
    app.add_config_value("breathe_default_project", "", True)
    app.add_config_value("breathe_domain_by_extension", {}, True)
    app.add_config_value("breathe_domain_by_file_pattern", {}, True)
    app.add_config_value("breathe_projects_source", {}, True)
    app.add_config_value("breathe_build_directory", '', True)

    app.add_stylesheet("breathe.css")

    app.connect("builder-inited", directive_factory.get_config_values)

    app.connect("env-get-outdated", file_state_cache.get_outdated)

    app.connect("env-purge-doc", file_state_cache.purge_doc)


########NEW FILE########
__FILENAME__ = core

class FinderError(Exception):
    pass

class MultipleMatchesError(FinderError):
    pass

class NoMatchesError(FinderError):
    pass

class FakeParentNode(object):

    node_type = "fakeparent"

class Finder(object):

    def __init__(self, root, item_finder_factory):

        self._root = root
        self.item_finder_factory = item_finder_factory

    def find(self, matcher_stack):

        item_finder = self.item_finder_factory.create_finder(self._root)

        return item_finder.find(matcher_stack)

    def filter_(self, filter_, matches):
        "Adds all nodes which match the filter into the matches list"

        item_finder = self.item_finder_factory.create_finder(self._root)
        item_finder.filter_(FakeParentNode(), filter_, matches)

    def find_one(self, matcher_stack):

        results = self.find(matcher_stack)

        count = len(results)
        if count == 1:
            return results[0]
        elif count > 1:
            # Multiple matches can easily happen as same thing
            # can be present in both file and group sections
            return results[0]
        elif count < 1:
            raise NoMatchesError(matcher_stack)


    def root(self):

        return self._root


class FinderFactory(object):

    def __init__(self, parser, item_finder_factory_creator):

        self.parser = parser
        self.item_finder_factory_creator = item_finder_factory_creator


    def create_finder(self, project_info):

        root = self.parser.parse(project_info)
        item_finder_factory = self.item_finder_factory_creator.create_factory(project_info)

        return Finder(root, item_finder_factory)

    def create_finder_from_root(self, root, project_info):

        item_finder_factory = self.item_finder_factory_creator.create_factory(project_info)

        return Finder(root, item_finder_factory)



########NEW FILE########
__FILENAME__ = base

class ItemFinder(object):

    def __init__(self, project_info, data_object, item_finder_factory):

        self.data_object = data_object
        self.item_finder_factory = item_finder_factory
        self.project_info = project_info



########NEW FILE########
__FILENAME__ = compound

from breathe.finder.doxygen.base import ItemFinder 

class DoxygenTypeSubItemFinder(ItemFinder):

    def find(self, matcher_stack):
        "Search with MatcherStack functionality - deprecated in favour of the filter approach"

        compound_finder = self.item_finder_factory.create_finder(self.data_object.compounddef)
        return compound_finder.find(matcher_stack)

    def filter_(self, parent, filter_, matches):
        "Find nodes which match the filter. Doesn't test this node, only its children"

        compound_finder = self.item_finder_factory.create_finder(self.data_object.compounddef)
        compound_finder.filter_(self.data_object, filter_, matches)


class CompoundDefTypeSubItemFinder(ItemFinder):

    def find(self, matcher_stack):
        "Search with MatcherStack functionality - deprecated in favour of the filter approach"

        results = []
        for sectiondef in self.data_object.sectiondef:
            finder = self.item_finder_factory.create_finder(sectiondef)
            results.extend(finder.find(matcher_stack))

        return results

    def filter_(self, parent, filter_, matches):
        "Finds nodes which match the filter and continues checks to children"

        if filter_.allow(parent, self.data_object):
            matches.append(self.data_object)

        for sectiondef in self.data_object.sectiondef:
            finder = self.item_finder_factory.create_finder(sectiondef)
            finder.filter_(self.data_object, filter_, matches)

        for innerclass in self.data_object.innerclass:
            finder = self.item_finder_factory.create_finder(innerclass)
            finder.filter_(self.data_object, filter_, matches)

class SectionDefTypeSubItemFinder(ItemFinder):

    def find(self, matcher_stack):
        "Search with MatcherStack functionality - deprecated in favour of the filter approach"

        results = []
        for memberdef in self.data_object.memberdef:
            finder = self.item_finder_factory.create_finder(memberdef)
            results.extend(finder.find(matcher_stack))

        return results

    def filter_(self, parent, filter_, matches):
        "Find nodes which match the filter. Doesn't test this node, only its children"

        if filter_.allow(parent, self.data_object):
            matches.append(self.data_object)

        for memberdef in self.data_object.memberdef:
            finder = self.item_finder_factory.create_finder(memberdef)
            finder.filter_(self.data_object, filter_, matches)


class MemberDefTypeSubItemFinder(ItemFinder):

    def find(self, matcher_stack):
        "Search with MatcherStack functionality - deprecated in favour of the filter approach"

        if matcher_stack.match("member", self.data_object):
            return [self.data_object]
        else:
            return []

    def filter_(self, parent, filter_, matches):

        if filter_.allow(parent, self.data_object):
            matches.append(self.data_object)


class RefTypeSubItemFinder(ItemFinder):

    def filter_(self, parent, filter_, matches):

        if filter_.allow(parent, self.data_object):
            matches.append(self.data_object)

########NEW FILE########
__FILENAME__ = core

from breathe.finder.doxygen import index as indexfinder
from breathe.finder.doxygen import compound as compoundfinder

from breathe.parser.doxygen import index, compound

class CreateCompoundTypeSubFinder(object):

    def __init__(self, parser_factory, matcher_factory):

        self.parser_factory = parser_factory
        self.matcher_factory = matcher_factory

    def __call__(self, project_info, *args):

        compound_parser = self.parser_factory.create_compound_parser(project_info)
        return indexfinder.CompoundTypeSubItemFinder(self.matcher_factory, compound_parser, project_info, *args)


class DoxygenItemFinderFactory(object):

    def __init__(self, finders, project_info):

        self.finders = finders
        self.project_info = project_info

    def create_finder(self, data_object):

        return self.finders[data_object.node_type](self.project_info, data_object, self)


class DoxygenItemFinderFactoryCreator(object):

    def __init__(self, parser_factory, matcher_factory):

        self.parser_factory = parser_factory
        self.matcher_factory = matcher_factory

    def create_factory(self, project_info):

        finders = {
            "doxygen" : indexfinder.DoxygenTypeSubItemFinder,
            "compound" : CreateCompoundTypeSubFinder(self.parser_factory, self.matcher_factory),
            "member" : indexfinder.MemberTypeSubItemFinder,
            "doxygendef" : compoundfinder.DoxygenTypeSubItemFinder,
            "compounddef" : compoundfinder.CompoundDefTypeSubItemFinder,
            "sectiondef" : compoundfinder.SectionDefTypeSubItemFinder,
            "memberdef" : compoundfinder.MemberDefTypeSubItemFinder,
            "ref" : compoundfinder.RefTypeSubItemFinder,
            }

        return DoxygenItemFinderFactory(finders, project_info)




########NEW FILE########
__FILENAME__ = index

from breathe.finder.doxygen.base import ItemFinder 

class DoxygenTypeSubItemFinder(ItemFinder):

    def find(self, matcher_stack):

        compounds = self.data_object.get_compound()

        results = []

        for compound in compounds:

            if matcher_stack.match("compound", compound):
                compound_finder = self.item_finder_factory.create_finder(compound)
                results.extend(compound_finder.find(matcher_stack))

        return results


    def filter_(self, parent, filter_, matches):
        "Find nodes which match the filter. Doesn't test this node, only its children"

        compounds = self.data_object.get_compound()

        for compound in compounds:

            compound_finder = self.item_finder_factory.create_finder(compound)
            compound_finder.filter_(self.data_object, filter_, matches)

class CompoundTypeSubItemFinder(ItemFinder):

    def __init__(self, matcher_factory, compound_parser, *args):
        ItemFinder.__init__(self, *args)

        self.matcher_factory = matcher_factory
        self.compound_parser = compound_parser

    def find(self, matcher_stack):

        members = self.data_object.get_member()

        member_results = []

        for member in members:
            if matcher_stack.match("member", member):
                member_finder = self.item_finder_factory.create_finder(member)
                member_results.extend(member_finder.find(matcher_stack))

        results = []

        # If there are members in this compound that match the criteria 
        # then load up the file for this compound and get the member data objects
        if member_results:

            file_data = self.compound_parser.parse(self.data_object.refid)
            finder = self.item_finder_factory.create_finder(file_data)

            for member_data in member_results:
                ref_matcher_stack = self.matcher_factory.create_ref_matcher_stack("", member_data.refid)
                # TODO: Fix this! Should be ref_matcher_stack!
                results.extend(finder.find(matcher_stack))

        elif matcher_stack.full_match("compound", self.data_object):
            results.append(self.data_object)

        return results


    def filter_(self, parent, filter_, matches):
        """Finds nodes which match the filter and continues checks to children

        Requires parsing the xml files referenced by the children for which we use the compound
        parser and continue at the top level of that pretending that this node is the parent of the
        top level node of the compound file.
        """

        if filter_.allow(parent, self.data_object):
            matches.append(self.data_object)

        file_data = self.compound_parser.parse(self.data_object.refid)
        finder = self.item_finder_factory.create_finder(file_data)

        finder.filter_(self.data_object, filter_, matches)

class MemberTypeSubItemFinder(ItemFinder):

    def find(self, matcher_stack):

        if matcher_stack.full_match("member", self.data_object):
            return [self.data_object]
        else:
            return []



########NEW FILE########
__FILENAME__ = matcher

class MissingLevelError(Exception):
    pass

class Matcher(object):
    pass

class ItemMatcher(Matcher):

    def __init__(self, name, type_):
        self.name = name
        self.type_ = type_

    def match(self, data_object):
        return self.name == data_object.name and self.type_ == data_object.kind

    def __repr__(self):
        return "<ItemMatcher - name:%s, type_:%s>" % (self.name, self.type_)

class NameMatcher(Matcher):

    def __init__(self, name):
        self.name = name

    def match(self, data_object):
        return self.name == data_object.name


class RefMatcher(Matcher):

    def __init__(self, refid):

        self.refid = refid

    def match(self, data_object):
        return self.refid == data_object.refid

class AnyMatcher(Matcher):

    def match(self, data_object):
        return True


class MatcherStack(object):

    def __init__(self, matchers, lowest_level):

        self.matchers = matchers
        self.lowest_level = lowest_level

    def match(self, level, data_object):

        try:
            return self.matchers[level].match(data_object)
        except KeyError:
            return False

    def full_match(self, level, data_object):

        try:
            return self.matchers[level].match(data_object) and level == self.lowest_level
        except KeyError:
            raise MissingLevelError(level)


class ItemMatcherFactory(Matcher):

    def create_name_type_matcher(self, name, type_):

        return ItemMatcher(name, type_)

    def create_name_matcher(self, name):

        return NameMatcher(name) if name else AnyMatcher()

    def create_ref_matcher(self, ref):

        return RefMatcher(ref)

    def create_matcher_stack(self, matchers, lowest_level):

        return MatcherStack(matchers, lowest_level)

    def create_ref_matcher_stack(self, class_, ref):

        matchers = {
                "compound" : ItemMatcher(class_, "class") if class_ else AnyMatcher(),
                "member" : RefMatcher(ref),
                }

        return MatcherStack(matchers, "member")



########NEW FILE########
__FILENAME__ = nodes

from docutils import nodes

class DoxygenNode(nodes.Element):

    def __init__(self, handler):

        nodes.Element.__init__(self, rawsource='', children=[], attributes={})

        self.handler = handler

class DoxygenAutoNode(nodes.Element):

    def __init__(self, auto_project_info, files, options, factories, state, lineno):

        nodes.Element.__init__(self, rawsource='', children=[], attributes={})

        self.auto_project_info = auto_project_info
        self.files = files
        self.options = options
        self.factories = factories
        self.state = state
        self.lineno = lineno


########NEW FILE########
__FILENAME__ = compound
#!/usr/bin/env python

"""
Generated Mon Feb  9 19:08:05 2009 by generateDS.py.
"""

from xml.dom import minidom
from xml.dom import Node
from xml.parsers.expat import ExpatError

from docutils import nodes

import compoundsuper as supermod
from compoundsuper import MixedContainer


class DoxygenTypeSub(supermod.DoxygenType):

    node_type = "doxygendef"

    def __init__(self, version=None, compounddef=None):
        supermod.DoxygenType.__init__(self, version, compounddef)
supermod.DoxygenType.subclass = DoxygenTypeSub
# end class DoxygenTypeSub


class compounddefTypeSub(supermod.compounddefType):
    
    node_type = "compounddef"

    def __init__(self, kind=None, prot=None, id=None, compoundname='', title='', basecompoundref=None, derivedcompoundref=None, includes=None, includedby=None, incdepgraph=None, invincdepgraph=None, innerdir=None, innerfile=None, innerclass=None, innernamespace=None, innerpage=None, innergroup=None, templateparamlist=None, sectiondef=None, briefdescription=None, detaileddescription=None, inheritancegraph=None, collaborationgraph=None, programlisting=None, location=None, listofallmembers=None):
        supermod.compounddefType.__init__(self, kind, prot, id, compoundname, title, basecompoundref, derivedcompoundref, includes, includedby, incdepgraph, invincdepgraph, innerdir, innerfile, innerclass, innernamespace, innerpage, innergroup, templateparamlist, sectiondef, briefdescription, detaileddescription, inheritancegraph, collaborationgraph, programlisting, location, listofallmembers)
supermod.compounddefType.subclass = compounddefTypeSub
# end class compounddefTypeSub


class listofallmembersTypeSub(supermod.listofallmembersType):

    node_type = "listofallmembers"


    def __init__(self, member=None):
        supermod.listofallmembersType.__init__(self, member)
supermod.listofallmembersType.subclass = listofallmembersTypeSub
# end class listofallmembersTypeSub


class memberRefTypeSub(supermod.memberRefType):

    node_type = "memberref"

    def __init__(self, virt=None, prot=None, refid=None, ambiguityscope=None, scope='', name=''):
        supermod.memberRefType.__init__(self, virt, prot, refid, ambiguityscope, scope, name)
supermod.memberRefType.subclass = memberRefTypeSub
# end class memberRefTypeSub


class compoundRefTypeSub(supermod.compoundRefType):

    node_type = "compoundref"

    def __init__(self, virt=None, prot=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.compoundRefType.__init__(self, mixedclass_, content_)
supermod.compoundRefType.subclass = compoundRefTypeSub
# end class compoundRefTypeSub


class reimplementTypeSub(supermod.reimplementType):

    node_type = "reimplement"

    def __init__(self, refid=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.reimplementType.__init__(self, mixedclass_, content_)
supermod.reimplementType.subclass = reimplementTypeSub
# end class reimplementTypeSub


class incTypeSub(supermod.incType):

    node_type = "inc"

    def __init__(self, local=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.incType.__init__(self, mixedclass_, content_)
supermod.incType.subclass = incTypeSub
# end class incTypeSub


class refTypeSub(supermod.refType):

    node_type = "ref"

    def __init__(self, node_name, prot=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.refType.__init__(self, mixedclass_, content_)

        self.node_name = node_name

supermod.refType.subclass = refTypeSub


class refTextTypeSub(supermod.refTextType):

    node_type = "reftex"

    def __init__(self, refid=None, kindref=None, external=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.refTextType.__init__(self, mixedclass_, content_)

supermod.refTextType.subclass = refTextTypeSub
# end class refTextTypeSub

class sectiondefTypeSub(supermod.sectiondefType):

    node_type = "sectiondef"

    def __init__(self, kind=None, header='', description=None, memberdef=None):
        supermod.sectiondefType.__init__(self, kind, header, description, memberdef)
supermod.sectiondefType.subclass = sectiondefTypeSub
# end class sectiondefTypeSub


class memberdefTypeSub(supermod.memberdefType):

    node_type = "memberdef" 

    def __init__(self, initonly=None, kind=None, volatile=None, const=None, raise_=None, virt=None, readable=None, prot=None, explicit=None, new=None, final=None, writable=None, add=None, static=None, remove=None, sealed=None, mutable=None, gettable=None, inline=None, settable=None, id=None, templateparamlist=None, type_=None, definition='', argsstring='', name='', read='', write='', bitfield='', reimplements=None, reimplementedby=None, param=None, enumvalue=None, initializer=None, exceptions=None, briefdescription=None, detaileddescription=None, inbodydescription=None, location=None, references=None, referencedby=None):
        supermod.memberdefType.__init__(self, initonly, kind, volatile, const, raise_, virt, readable, prot, explicit, new, final, writable, add, static, remove, sealed, mutable, gettable, inline, settable, id, templateparamlist, type_, definition, argsstring, name, read, write, bitfield, reimplements, reimplementedby, param, enumvalue, initializer, exceptions, briefdescription, detaileddescription, inbodydescription, location, references, referencedby)

        self.parameterlist = supermod.docParamListType.factory()
        self.parameterlist.kind = "param"


    def buildChildren(self, child_, nodeName_):
        supermod.memberdefType.buildChildren(self, child_, nodeName_)
        
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'param':

            # Get latest param
            param = self.param[-1]

            # If it doesn't have a description we're done
            if not param.briefdescription:
                return

            # Construct our own param list from the descriptions stored inline
            # with the parameters
            paramdescription = param.briefdescription
            paramname = supermod.docParamName.factory()

            # Add parameter name
            obj_ = paramname.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', param.declname)
            paramname.content_.append(obj_)

            paramnamelist = supermod.docParamNameList.factory()
            paramnamelist.parametername.append(paramname)

            paramlistitem = supermod.docParamListItem.factory()
            paramlistitem.parameternamelist.append(paramnamelist)

            # Add parameter description
            paramlistitem.parameterdescription = paramdescription

            self.parameterlist.parameteritem.append(paramlistitem)

        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'detaileddescription':

            if not self.parameterlist.parameteritem:
                # No items in our list
                return


            # Assume supermod.memberdefType.buildChildren has already built the
            # description object, we just want to slot our parameterlist in at
            # a reasonable point

            if not self.detaileddescription:
                # Create one if it doesn't exist
                self.detaileddescription = supermod.descriptionType.factory()

            detaileddescription = self.detaileddescription

            para = supermod.docParaType.factory()
            para.parameterlist.append(self.parameterlist)

            obj_ = detaileddescription.mixedclass_(MixedContainer.CategoryComplex, MixedContainer.TypeNone, 'para', para)

            index = 0
            detaileddescription.content_.insert( index, obj_ )



supermod.memberdefType.subclass = memberdefTypeSub
# end class memberdefTypeSub

class descriptionTypeSub(supermod.descriptionType):
    
    node_type = "description"

    def __init__(self, title='', para=None, sect1=None, internal=None, mixedclass_=None, content_=None):
        supermod.descriptionType.__init__(self, mixedclass_, content_)
supermod.descriptionType.subclass = descriptionTypeSub
# end class descriptionTypeSub


class enumvalueTypeSub(supermod.enumvalueType):

    node_type = "enumvalue"

    def __init__(self, prot=None, id=None, name='', initializer=None, briefdescription=None, detaileddescription=None, mixedclass_=None, content_=None):
        supermod.enumvalueType.__init__(self, mixedclass_, content_)
        
        self.initializer = None

    def buildChildren(self, child_, nodeName_):
        # Get text from <name> child and put it in self.name
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'name':
            value_ = []
            for text_ in child_.childNodes:
                value_.append(text_.nodeValue)
            valuestr_ = ''.join(value_)
            self.name = valuestr_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'briefdescription':
            obj_ = supermod.descriptionType.factory()
            obj_.build(child_)
            self.set_briefdescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'detaileddescription':
            obj_ = supermod.descriptionType.factory()
            obj_.build(child_)
            self.set_detaileddescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'initializer':
            childobj_ = supermod.linkedTextType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'initializer', childobj_)
            self.set_initializer(obj_)
            self.content_.append(obj_)

supermod.enumvalueType.subclass = enumvalueTypeSub
# end class enumvalueTypeSub


class templateparamlistTypeSub(supermod.templateparamlistType):

    node_type = "templateparamlist"

    def __init__(self, param=None):
        supermod.templateparamlistType.__init__(self, param)
supermod.templateparamlistType.subclass = templateparamlistTypeSub
# end class templateparamlistTypeSub


class paramTypeSub(supermod.paramType):

    node_type = "param"

    def __init__(self, type_=None, declname='', defname='', array='', defval=None, briefdescription=None):
        supermod.paramType.__init__(self, type_, declname, defname, array, defval, briefdescription)
supermod.paramType.subclass = paramTypeSub
# end class paramTypeSub


class linkedTextTypeSub(supermod.linkedTextType):

    node_type = "linkedtext"

    def __init__(self, ref=None, mixedclass_=None, content_=None):
        supermod.linkedTextType.__init__(self, mixedclass_, content_)
supermod.linkedTextType.subclass = linkedTextTypeSub
# end class linkedTextTypeSub


class graphTypeSub(supermod.graphType):

    node_type = "graph"

    def __init__(self, node=None):
        supermod.graphType.__init__(self, node)
supermod.graphType.subclass = graphTypeSub
# end class graphTypeSub


class nodeTypeSub(supermod.nodeType):

    node_type = "node"

    def __init__(self, id=None, label='', link=None, childnode=None):
        supermod.nodeType.__init__(self, id, label, link, childnode)
supermod.nodeType.subclass = nodeTypeSub
# end class nodeTypeSub


class childnodeTypeSub(supermod.childnodeType):

    node_type = "childnode"

    def __init__(self, relation=None, refid=None, edgelabel=None):
        supermod.childnodeType.__init__(self, relation, refid, edgelabel)
supermod.childnodeType.subclass = childnodeTypeSub
# end class childnodeTypeSub


class linkTypeSub(supermod.linkType):

    node_type = "link"

    def __init__(self, refid=None, external=None, valueOf_=''):
        supermod.linkType.__init__(self, refid, external)
supermod.linkType.subclass = linkTypeSub
# end class linkTypeSub


class listingTypeSub(supermod.listingType):

    node_type = "listing"

    def __init__(self, codeline=None):
        supermod.listingType.__init__(self, codeline)
supermod.listingType.subclass = listingTypeSub
# end class listingTypeSub


class codelineTypeSub(supermod.codelineType):

    node_type = "codeline"

    def __init__(self, external=None, lineno=None, refkind=None, refid=None, highlight=None):
        supermod.codelineType.__init__(self, external, lineno, refkind, refid, highlight)
supermod.codelineType.subclass = codelineTypeSub
# end class codelineTypeSub


class highlightTypeSub(supermod.highlightType):

    node_type = "highlight"

    def __init__(self, class_=None, sp=None, ref=None, mixedclass_=None, content_=None):
        supermod.highlightType.__init__(self, mixedclass_, content_)
supermod.highlightType.subclass = highlightTypeSub
# end class highlightTypeSub


class referenceTypeSub(supermod.referenceType):

    node_type = "reference"

    def __init__(self, endline=None, startline=None, refid=None, compoundref=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.referenceType.__init__(self, mixedclass_, content_)
supermod.referenceType.subclass = referenceTypeSub
# end class referenceTypeSub


class locationTypeSub(supermod.locationType):

    node_type = "location"

    def __init__(self, bodystart=None, line=None, bodyend=None, bodyfile=None, file=None, valueOf_=''):
        supermod.locationType.__init__(self, bodystart, line, bodyend, bodyfile, file)
supermod.locationType.subclass = locationTypeSub
# end class locationTypeSub


class docSect1TypeSub(supermod.docSect1Type):

    node_type = "docsect1"

    def __init__(self, id=None, title='', para=None, sect2=None, internal=None, mixedclass_=None, content_=None):
        supermod.docSect1Type.__init__(self, mixedclass_, content_)
supermod.docSect1Type.subclass = docSect1TypeSub
# end class docSect1TypeSub


class docSect2TypeSub(supermod.docSect2Type):

    node_type = "docsect2"

    def __init__(self, id=None, title='', para=None, sect3=None, internal=None, mixedclass_=None, content_=None):
        supermod.docSect2Type.__init__(self, mixedclass_, content_)
supermod.docSect2Type.subclass = docSect2TypeSub
# end class docSect2TypeSub


class docSect3TypeSub(supermod.docSect3Type):

    node_type = "docsect3"

    def __init__(self, id=None, title='', para=None, sect4=None, internal=None, mixedclass_=None, content_=None):
        supermod.docSect3Type.__init__(self, mixedclass_, content_)
supermod.docSect3Type.subclass = docSect3TypeSub
# end class docSect3TypeSub


class docSect4TypeSub(supermod.docSect4Type):

    node_type = "docsect4"

    def __init__(self, id=None, title='', para=None, internal=None, mixedclass_=None, content_=None):
        supermod.docSect4Type.__init__(self, mixedclass_, content_)
supermod.docSect4Type.subclass = docSect4TypeSub
# end class docSect4TypeSub


class docInternalTypeSub(supermod.docInternalType):

    node_type = "docinternal"

    def __init__(self, para=None, sect1=None, mixedclass_=None, content_=None):
        supermod.docInternalType.__init__(self, mixedclass_, content_)
supermod.docInternalType.subclass = docInternalTypeSub
# end class docInternalTypeSub


class docInternalS1TypeSub(supermod.docInternalS1Type):

    node_type = "docinternals1"

    def __init__(self, para=None, sect2=None, mixedclass_=None, content_=None):
        supermod.docInternalS1Type.__init__(self, mixedclass_, content_)
supermod.docInternalS1Type.subclass = docInternalS1TypeSub
# end class docInternalS1TypeSub


class docInternalS2TypeSub(supermod.docInternalS2Type):

    node_type = "docinternals2"

    def __init__(self, para=None, sect3=None, mixedclass_=None, content_=None):
        supermod.docInternalS2Type.__init__(self, mixedclass_, content_)
supermod.docInternalS2Type.subclass = docInternalS2TypeSub
# end class docInternalS2TypeSub


class docInternalS3TypeSub(supermod.docInternalS3Type):

    node_type = "docinternals3"

    def __init__(self, para=None, sect3=None, mixedclass_=None, content_=None):
        supermod.docInternalS3Type.__init__(self, mixedclass_, content_)
supermod.docInternalS3Type.subclass = docInternalS3TypeSub
# end class docInternalS3TypeSub


class docInternalS4TypeSub(supermod.docInternalS4Type):

    node_type = "docinternals4"

    def __init__(self, para=None, mixedclass_=None, content_=None):
        supermod.docInternalS4Type.__init__(self, mixedclass_, content_)
supermod.docInternalS4Type.subclass = docInternalS4TypeSub
# end class docInternalS4TypeSub


class docURLLinkSub(supermod.docURLLink):

    node_type = "docurllink"

    def __init__(self, url=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docURLLink.__init__(self, mixedclass_, content_)
supermod.docURLLink.subclass = docURLLinkSub
# end class docURLLinkSub


class docAnchorTypeSub(supermod.docAnchorType):

    node_type = "docanchor"

    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docAnchorType.__init__(self, mixedclass_, content_)
supermod.docAnchorType.subclass = docAnchorTypeSub
# end class docAnchorTypeSub


class docFormulaTypeSub(supermod.docFormulaType):

    node_type = "docformula"

    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docFormulaType.__init__(self, mixedclass_, content_)
supermod.docFormulaType.subclass = docFormulaTypeSub
# end class docFormulaTypeSub


class docIndexEntryTypeSub(supermod.docIndexEntryType):

    node_type = "docindexentry"

    def __init__(self, primaryie='', secondaryie=''):
        supermod.docIndexEntryType.__init__(self, primaryie, secondaryie)
supermod.docIndexEntryType.subclass = docIndexEntryTypeSub
# end class docIndexEntryTypeSub


class docListTypeSub(supermod.docListType):

    node_type = "doclist"

    def __init__(self, listitem=None, subtype=""):
        self.node_subtype = "itemized"
        if subtype is not "":
            self.node_subtype = subtype
        supermod.docListType.__init__(self, listitem)
supermod.docListType.subclass = docListTypeSub
# end class docListTypeSub


class docListItemTypeSub(supermod.docListItemType):

    node_type = "doclistitem"

    def __init__(self, para=None):
        supermod.docListItemType.__init__(self, para)
supermod.docListItemType.subclass = docListItemTypeSub
# end class docListItemTypeSub


class docSimpleSectTypeSub(supermod.docSimpleSectType):

    node_type = "docsimplesect"

    def __init__(self, kind=None, title=None, para=None):
        supermod.docSimpleSectType.__init__(self, kind, title, para)
supermod.docSimpleSectType.subclass = docSimpleSectTypeSub
# end class docSimpleSectTypeSub


class docVarListEntryTypeSub(supermod.docVarListEntryType):

    node_type = "docvarlistentry"

    def __init__(self, term=None):
        supermod.docVarListEntryType.__init__(self, term)
supermod.docVarListEntryType.subclass = docVarListEntryTypeSub
# end class docVarListEntryTypeSub


class docRefTextTypeSub(supermod.docRefTextType):

    node_type = "docreftext"

    def __init__(self, refid=None, kindref=None, external=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docRefTextType.__init__(self, mixedclass_, content_)

        self.para = []

    def buildChildren(self, child_, nodeName_):
        supermod.docRefTextType.buildChildren(self, child_, nodeName_)

        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            obj_ = supermod.docParaType.factory()
            obj_.build(child_)
            self.para.append(obj_)

supermod.docRefTextType.subclass = docRefTextTypeSub
# end class docRefTextTypeSub


class docTableTypeSub(supermod.docTableType):

    node_type = "doctable"

    def __init__(self, rows=None, cols=None, row=None, caption=None):
        supermod.docTableType.__init__(self, rows, cols, row, caption)
supermod.docTableType.subclass = docTableTypeSub
# end class docTableTypeSub


class docRowTypeSub(supermod.docRowType):

    node_type = "docrow"

    def __init__(self, entry=None):
        supermod.docRowType.__init__(self, entry)
supermod.docRowType.subclass = docRowTypeSub
# end class docRowTypeSub


class docEntryTypeSub(supermod.docEntryType):

    node_type = "docentry"

    def __init__(self, thead=None, para=None):
        supermod.docEntryType.__init__(self, thead, para)
supermod.docEntryType.subclass = docEntryTypeSub
# end class docEntryTypeSub


class docHeadingTypeSub(supermod.docHeadingType):

    node_type = "docheading"

    def __init__(self, level=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docHeadingType.__init__(self, mixedclass_, content_)
supermod.docHeadingType.subclass = docHeadingTypeSub
# end class docHeadingTypeSub


class docImageTypeSub(supermod.docImageType):

    node_type = "docimage"

    def __init__(self, width=None, type_=None, name=None, height=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docImageType.__init__(self, mixedclass_, content_)
supermod.docImageType.subclass = docImageTypeSub
# end class docImageTypeSub


class docDotFileTypeSub(supermod.docDotFileType):

    node_type = "docdocfile"

    def __init__(self, name=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docDotFileType.__init__(self, mixedclass_, content_)
supermod.docDotFileType.subclass = docDotFileTypeSub
# end class docDotFileTypeSub


class docTocItemTypeSub(supermod.docTocItemType):

    node_type = "doctocitem"

    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        supermod.docTocItemType.__init__(self, mixedclass_, content_)
supermod.docTocItemType.subclass = docTocItemTypeSub
# end class docTocItemTypeSub


class docTocListTypeSub(supermod.docTocListType):

    node_type = "doctoclist"

    def __init__(self, tocitem=None):
        supermod.docTocListType.__init__(self, tocitem)
supermod.docTocListType.subclass = docTocListTypeSub
# end class docTocListTypeSub


class docLanguageTypeSub(supermod.docLanguageType):

    node_type = "doclanguage"

    def __init__(self, langid=None, para=None):
        supermod.docLanguageType.__init__(self, langid, para)
supermod.docLanguageType.subclass = docLanguageTypeSub
# end class docLanguageTypeSub


class docParamListTypeSub(supermod.docParamListType):

    node_type = "docparamlist"

    def __init__(self, kind=None, parameteritem=None):
        supermod.docParamListType.__init__(self, kind, parameteritem)
supermod.docParamListType.subclass = docParamListTypeSub
# end class docParamListTypeSub


class docParamListItemSub(supermod.docParamListItem):

    node_type = "docparamlistitem"

    def __init__(self, parameternamelist=None, parameterdescription=None):
        supermod.docParamListItem.__init__(self, parameternamelist, parameterdescription)
supermod.docParamListItem.subclass = docParamListItemSub
# end class docParamListItemSub


class docParamNameListSub(supermod.docParamNameList):

    node_type = "docparamnamelist"

    def __init__(self, parametername=None):
        supermod.docParamNameList.__init__(self, parametername)
supermod.docParamNameList.subclass = docParamNameListSub
# end class docParamNameListSub


class docParamNameSub(supermod.docParamName):

    node_type = "docparamname"

    def __init__(self, direction=None, ref=None, mixedclass_=None, content_=None):
        supermod.docParamName.__init__(self, mixedclass_, content_)
supermod.docParamName.subclass = docParamNameSub
# end class docParamNameSub


class docXRefSectTypeSub(supermod.docXRefSectType):

    node_type = "docxrefsect"

    def __init__(self, id=None, xreftitle=None, xrefdescription=None):
        supermod.docXRefSectType.__init__(self, id, xreftitle, xrefdescription)
supermod.docXRefSectType.subclass = docXRefSectTypeSub
# end class docXRefSectTypeSub


class docCopyTypeSub(supermod.docCopyType):

    node_type = "doccopy"

    def __init__(self, link=None, para=None, sect1=None, internal=None):
        supermod.docCopyType.__init__(self, link, para, sect1, internal)
supermod.docCopyType.subclass = docCopyTypeSub
# end class docCopyTypeSub


class docCharTypeSub(supermod.docCharType):

    node_type = "docchar"

    def __init__(self, char=None, valueOf_=''):
        supermod.docCharType.__init__(self, char)
supermod.docCharType.subclass = docCharTypeSub
# end class docCharTypeSub


class verbatimTypeSub(object):
    """
    New node type. Structure is largely pillaged from other nodes in order to
    match the set.
    """

    node_type = "verbatim"

    def __init__(self, valueOf_='', mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
        self.text = ""
    def factory(*args, **kwargs):
        return verbatimTypeSub(*args, **kwargs)
    factory = staticmethod(factory)
    def buildAttributes(self, attrs):
        pass
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.text += child_.nodeValue

class docParaTypeSub(supermod.docParaType):

    node_type = "docpara"

    def __init__(self, char=None, valueOf_=''):
        supermod.docParaType.__init__(self, char)

        self.parameterlist = []
        self.simplesects = []
        self.content = []
        self.programlisting =[]
        self.images =[]

    def buildChildren(self, child_, nodeName_):
        supermod.docParaType.buildChildren(self, child_, nodeName_)

        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
                nodeName_ == "ref":
            obj_ = supermod.docRefTextType.factory()
            obj_.build(child_)
            self.content.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
                nodeName_ == 'parameterlist':
            obj_ = supermod.docParamListType.factory()
            obj_.build(child_)
            self.parameterlist.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
                nodeName_ == 'simplesect':
            obj_ = supermod.docSimpleSectType.factory()
            obj_.build(child_)
            self.simplesects.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
                nodeName_ == 'programlisting':
            obj_ = supermod.listingType.factory()
            obj_.build(child_)
            self.programlisting.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
                nodeName_ == 'image':
            obj_ = supermod.docImageType.factory()
            obj_.build(child_)
            self.images.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and (
                nodeName_ == 'bold' or
                nodeName_ == 'emphasis' or
                nodeName_ == 'computeroutput' or
                nodeName_ == 'subscript' or
                nodeName_ == 'superscript' or
                nodeName_ == 'center' or
                nodeName_ == 'small'):
            obj_ = supermod.docMarkupType.factory()
            obj_.build(child_)
            obj_.type_ = nodeName_
            self.content.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'verbatim':
            childobj_ = verbatimTypeSub.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'verbatim', childobj_)
            self.content.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'formula':
            childobj_ = docFormulaTypeSub.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'formula', childobj_)
            self.content.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
                nodeName_ == "itemizedlist":
            obj_ = supermod.docListType.factory(subtype="itemized")
            obj_.build(child_)
            self.content.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == "orderedlist":
            obj_ = supermod.docListType.factory(subtype="ordered")
            obj_.build(child_)
            self.content.append(obj_)

supermod.docParaType.subclass = docParaTypeSub
# end class docParaTypeSub


class docMarkupTypeSub(supermod.docMarkupType):

    node_type = "docmarkup"

    def __init__(self, valueOf_='', mixedclass_=None, content_=None):
        supermod.docMarkupType.__init__(self, valueOf_, mixedclass_, content_)
        self.type_ = None

    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'ref':
            childobj_ = supermod.docRefTextType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'ref', childobj_)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
supermod.docMarkupType.subclass = docMarkupTypeSub
# end class docMarkupTypeSub


class docTitleTypeSub(supermod.docTitleType):

    node_type = "doctitle"
    
    def __init__(self, valueOf_='', mixedclass_=None, content_=None):
        supermod.docTitleType.__init__(self, valueOf_, mixedclass_, content_)
        self.type_ = None
supermod.docTitleType.subclass = docTitleTypeSub
# end class docTitleTypeSub


class ParseError(Exception):
    pass

class FileIOError(Exception):
    pass

def parse(inFilename):

    try:
        doc = minidom.parse(inFilename)
    except IOError, e:
        raise FileIOError(e)
    except ExpatError, e:
        raise ParseError(e)

    rootNode = doc.documentElement
    rootObj = supermod.DoxygenType.factory()
    rootObj.build(rootNode)
    return rootObj



########NEW FILE########
__FILENAME__ = compoundsuper
#!/usr/bin/env python

#
# Generated Thu Jun 11 18:44:25 2009 by generateDS.py.
#

import sys
import getopt
from xml.dom import minidom
from xml.dom import Node

#
# User methods
#
# Calls to the methods in these classes are generated by generateDS.py.
# You can replace these methods by re-implementing the following class
#   in a module named generatedssuper.py.

try:
    from generatedssuper import GeneratedsSuper
except ImportError, exp:

    class GeneratedsSuper:
        def format_string(self, input_data, input_name=''):
            return input_data
        def format_integer(self, input_data, input_name=''):
            return '%d' % input_data
        def format_float(self, input_data, input_name=''):
            return '%f' % input_data
        def format_double(self, input_data, input_name=''):
            return '%e' % input_data
        def format_boolean(self, input_data, input_name=''):
            return '%s' % input_data


#
# If you have installed IPython you can uncomment and use the following.
# IPython is available from http://ipython.scipy.org/.
#

## from IPython.Shell import IPShellEmbed
## args = ''
## ipshell = IPShellEmbed(args,
##     banner = 'Dropping into IPython',
##     exit_msg = 'Leaving Interpreter, back to program.')

# Then use the following line where and when you want to drop into the
# IPython shell:
#    ipshell('<some message> -- Entering ipshell.\nHit Ctrl-D to exit')

#
# Globals
#

ExternalEncoding = 'ascii'

#
# Support/utility functions.
#

def showIndent(outfile, level):
    for idx in range(level):
        outfile.write('    ')

def quote_xml(inStr):
    s1 = (isinstance(inStr, basestring) and inStr or
          '%s' % inStr)
    s1 = s1.replace('&', '&amp;')
    s1 = s1.replace('<', '&lt;')
    s1 = s1.replace('>', '&gt;')
    return s1

def quote_attrib(inStr):
    s1 = (isinstance(inStr, basestring) and inStr or
          '%s' % inStr)
    s1 = s1.replace('&', '&amp;')
    s1 = s1.replace('<', '&lt;')
    s1 = s1.replace('>', '&gt;')
    if '"' in s1:
        if "'" in s1:
            s1 = '"%s"' % s1.replace('"', "&quot;")
        else:
            s1 = "'%s'" % s1
    else:
        s1 = '"%s"' % s1
    return s1

def quote_python(inStr):
    s1 = inStr
    if s1.find("'") == -1:
        if s1.find('\n') == -1:
            return "'%s'" % s1
        else:
            return "'''%s'''" % s1
    else:
        if s1.find('"') != -1:
            s1 = s1.replace('"', '\\"')
        if s1.find('\n') == -1:
            return '"%s"' % s1
        else:
            return '"""%s"""' % s1


class MixedContainer:

    node_type = "mixedcontainer"

    # Constants for category:
    CategoryNone = 0
    CategoryText = 1
    CategorySimple = 2
    CategoryComplex = 3
    # Constants for content_type:
    TypeNone = 0
    TypeText = 1
    TypeString = 2
    TypeInteger = 3
    TypeFloat = 4
    TypeDecimal = 5
    TypeDouble = 6
    TypeBoolean = 7
    def __init__(self, category, content_type, name, value):
        self.category = category
        self.content_type = content_type
        self.name = name
        self.value = value
    def getCategory(self):
        return self.category
    def getContenttype(self, content_type):
        return self.content_type
    def getValue(self):
        return self.value
    def getName(self):
        return self.name


class _MemberSpec(object):
    def __init__(self, name='', data_type='', container=0):
        self.name = name
        self.data_type = data_type
        self.container = container
    def set_name(self, name): self.name = name
    def get_name(self): return self.name
    def set_data_type(self, data_type): self.data_type = data_type
    def get_data_type(self): return self.data_type
    def set_container(self, container): self.container = container
    def get_container(self): return self.container


#
# Data representation classes.
#

class DoxygenType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, version=None, compounddef=None):
        self.version = version
        self.compounddef = compounddef
    def factory(*args_, **kwargs_):
        if DoxygenType.subclass:
            return DoxygenType.subclass(*args_, **kwargs_)
        else:
            return DoxygenType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_compounddef(self): return self.compounddef
    def set_compounddef(self, compounddef): self.compounddef = compounddef
    def get_version(self): return self.version
    def set_version(self, version): self.version = version
    def hasContent_(self):
        if (
            self.compounddef is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('version'):
            self.version = attrs.get('version').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'compounddef':
            obj_ = compounddefType.factory()
            obj_.build(child_)
            self.set_compounddef(obj_)
# end class DoxygenType


class compounddefType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, prot=None, id=None, compoundname=None, title=None, basecompoundref=None, derivedcompoundref=None, includes=None, includedby=None, incdepgraph=None, invincdepgraph=None, innerdir=None, innerfile=None, innerclass=None, innernamespace=None, innerpage=None, innergroup=None, templateparamlist=None, sectiondef=None, briefdescription=None, detaileddescription=None, inheritancegraph=None, collaborationgraph=None, programlisting=None, location=None, listofallmembers=None):
        self.kind = kind
        self.prot = prot
        self.id = id
        self.compoundname = compoundname
        self.title = title
        if basecompoundref is None:
            self.basecompoundref = []
        else:
            self.basecompoundref = basecompoundref
        if derivedcompoundref is None:
            self.derivedcompoundref = []
        else:
            self.derivedcompoundref = derivedcompoundref
        if includes is None:
            self.includes = []
        else:
            self.includes = includes
        if includedby is None:
            self.includedby = []
        else:
            self.includedby = includedby
        self.incdepgraph = incdepgraph
        self.invincdepgraph = invincdepgraph
        if innerdir is None:
            self.innerdir = []
        else:
            self.innerdir = innerdir
        if innerfile is None:
            self.innerfile = []
        else:
            self.innerfile = innerfile
        if innerclass is None:
            self.innerclass = []
        else:
            self.innerclass = innerclass
        if innernamespace is None:
            self.innernamespace = []
        else:
            self.innernamespace = innernamespace
        if innerpage is None:
            self.innerpage = []
        else:
            self.innerpage = innerpage
        if innergroup is None:
            self.innergroup = []
        else:
            self.innergroup = innergroup
        self.templateparamlist = templateparamlist
        if sectiondef is None:
            self.sectiondef = []
        else:
            self.sectiondef = sectiondef
        self.briefdescription = briefdescription
        self.detaileddescription = detaileddescription
        self.inheritancegraph = inheritancegraph
        self.collaborationgraph = collaborationgraph
        self.programlisting = programlisting
        self.location = location
        self.listofallmembers = listofallmembers
        self.namespaces = []
    def factory(*args_, **kwargs_):
        if compounddefType.subclass:
            return compounddefType.subclass(*args_, **kwargs_)
        else:
            return compounddefType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_compoundname(self): return self.compoundname
    def set_compoundname(self, compoundname): self.compoundname = compoundname
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_basecompoundref(self): return self.basecompoundref
    def set_basecompoundref(self, basecompoundref): self.basecompoundref = basecompoundref
    def add_basecompoundref(self, value): self.basecompoundref.append(value)
    def insert_basecompoundref(self, index, value): self.basecompoundref[index] = value
    def get_derivedcompoundref(self): return self.derivedcompoundref
    def set_derivedcompoundref(self, derivedcompoundref): self.derivedcompoundref = derivedcompoundref
    def add_derivedcompoundref(self, value): self.derivedcompoundref.append(value)
    def insert_derivedcompoundref(self, index, value): self.derivedcompoundref[index] = value
    def get_includes(self): return self.includes
    def set_includes(self, includes): self.includes = includes
    def add_includes(self, value): self.includes.append(value)
    def insert_includes(self, index, value): self.includes[index] = value
    def get_includedby(self): return self.includedby
    def set_includedby(self, includedby): self.includedby = includedby
    def add_includedby(self, value): self.includedby.append(value)
    def insert_includedby(self, index, value): self.includedby[index] = value
    def get_incdepgraph(self): return self.incdepgraph
    def set_incdepgraph(self, incdepgraph): self.incdepgraph = incdepgraph
    def get_invincdepgraph(self): return self.invincdepgraph
    def set_invincdepgraph(self, invincdepgraph): self.invincdepgraph = invincdepgraph
    def get_innerdir(self): return self.innerdir
    def set_innerdir(self, innerdir): self.innerdir = innerdir
    def add_innerdir(self, value): self.innerdir.append(value)
    def insert_innerdir(self, index, value): self.innerdir[index] = value
    def get_innerfile(self): return self.innerfile
    def set_innerfile(self, innerfile): self.innerfile = innerfile
    def add_innerfile(self, value): self.innerfile.append(value)
    def insert_innerfile(self, index, value): self.innerfile[index] = value
    def get_innerclass(self): return self.innerclass
    def set_innerclass(self, innerclass): self.innerclass = innerclass
    def add_innerclass(self, value): self.innerclass.append(value)
    def insert_innerclass(self, index, value): self.innerclass[index] = value
    def get_innernamespace(self): return self.innernamespace
    def set_innernamespace(self, innernamespace): self.innernamespace = innernamespace
    def add_innernamespace(self, value): self.innernamespace.append(value)
    def insert_innernamespace(self, index, value): self.innernamespace[index] = value
    def get_innerpage(self): return self.innerpage
    def set_innerpage(self, innerpage): self.innerpage = innerpage
    def add_innerpage(self, value): self.innerpage.append(value)
    def insert_innerpage(self, index, value): self.innerpage[index] = value
    def get_innergroup(self): return self.innergroup
    def set_innergroup(self, innergroup): self.innergroup = innergroup
    def add_innergroup(self, value): self.innergroup.append(value)
    def insert_innergroup(self, index, value): self.innergroup[index] = value
    def get_templateparamlist(self): return self.templateparamlist
    def set_templateparamlist(self, templateparamlist): self.templateparamlist = templateparamlist
    def get_sectiondef(self): return self.sectiondef
    def set_sectiondef(self, sectiondef): self.sectiondef = sectiondef
    def add_sectiondef(self, value): self.sectiondef.append(value)
    def insert_sectiondef(self, index, value): self.sectiondef[index] = value
    def get_briefdescription(self): return self.briefdescription
    def set_briefdescription(self, briefdescription): self.briefdescription = briefdescription
    def get_detaileddescription(self): return self.detaileddescription
    def set_detaileddescription(self, detaileddescription): self.detaileddescription = detaileddescription
    def get_inheritancegraph(self): return self.inheritancegraph
    def set_inheritancegraph(self, inheritancegraph): self.inheritancegraph = inheritancegraph
    def get_collaborationgraph(self): return self.collaborationgraph
    def set_collaborationgraph(self, collaborationgraph): self.collaborationgraph = collaborationgraph
    def get_programlisting(self): return self.programlisting
    def set_programlisting(self, programlisting): self.programlisting = programlisting
    def get_location(self): return self.location
    def set_location(self, location): self.location = location
    def get_listofallmembers(self): return self.listofallmembers
    def set_listofallmembers(self, listofallmembers): self.listofallmembers = listofallmembers
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def hasContent_(self):
        if (
            self.compoundname is not None or
            self.title is not None or
            self.basecompoundref is not None or
            self.derivedcompoundref is not None or
            self.includes is not None or
            self.includedby is not None or
            self.incdepgraph is not None or
            self.invincdepgraph is not None or
            self.innerdir is not None or
            self.innerfile is not None or
            self.innerclass is not None or
            self.innernamespace is not None or
            self.innerpage is not None or
            self.innergroup is not None or
            self.templateparamlist is not None or
            self.sectiondef is not None or
            self.briefdescription is not None or
            self.detaileddescription is not None or
            self.inheritancegraph is not None or
            self.collaborationgraph is not None or
            self.programlisting is not None or
            self.location is not None or
            self.listofallmembers is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'compoundname':
            compoundname_ = ''
            for text__content_ in child_.childNodes:
                compoundname_ += text__content_.nodeValue
            self.compoundname = compoundname_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            obj_ = docTitleType.factory()
            obj_.build(child_)
            self.set_title(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'basecompoundref':
            obj_ = compoundRefType.factory()
            obj_.build(child_)
            self.basecompoundref.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'derivedcompoundref':
            obj_ = compoundRefType.factory()
            obj_.build(child_)
            self.derivedcompoundref.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'includes':
            obj_ = incType.factory()
            obj_.build(child_)
            self.includes.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'includedby':
            obj_ = incType.factory()
            obj_.build(child_)
            self.includedby.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'incdepgraph':
            obj_ = graphType.factory()
            obj_.build(child_)
            self.set_incdepgraph(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'invincdepgraph':
            obj_ = graphType.factory()
            obj_.build(child_)
            self.set_invincdepgraph(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innerdir':
            obj_ = refType.factory(nodeName_)
            obj_.build(child_)
            self.innerdir.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innerfile':
            obj_ = refType.factory(nodeName_)
            obj_.build(child_)
            self.innerfile.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innerclass':
            obj_ = refType.factory(nodeName_)
            obj_.build(child_)
            self.innerclass.append(obj_)
            self.namespaces.append(obj_.content_[0].getValue())
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innernamespace':
            obj_ = refType.factory(nodeName_)
            obj_.build(child_)
            self.innernamespace.append(obj_)
            self.namespaces.append(obj_.content_[0].getValue())
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innerpage':
            obj_ = refType.factory(nodeName_)
            obj_.build(child_)
            self.innerpage.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'innergroup':
            obj_ = refType.factory(nodeName_)
            obj_.build(child_)
            self.innergroup.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'templateparamlist':
            obj_ = templateparamlistType.factory()
            obj_.build(child_)
            self.set_templateparamlist(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sectiondef':
            obj_ = sectiondefType.factory()
            obj_.build(child_)
            self.sectiondef.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'briefdescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_briefdescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'detaileddescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_detaileddescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'inheritancegraph':
            obj_ = graphType.factory()
            obj_.build(child_)
            self.set_inheritancegraph(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'collaborationgraph':
            obj_ = graphType.factory()
            obj_.build(child_)
            self.set_collaborationgraph(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'programlisting':
            obj_ = listingType.factory()
            obj_.build(child_)
            self.set_programlisting(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'location':
            obj_ = locationType.factory()
            obj_.build(child_)
            self.set_location(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'listofallmembers':
            obj_ = listofallmembersType.factory()
            obj_.build(child_)
            self.set_listofallmembers(obj_)
# end class compounddefType


class listofallmembersType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, member=None):
        if member is None:
            self.member = []
        else:
            self.member = member
    def factory(*args_, **kwargs_):
        if listofallmembersType.subclass:
            return listofallmembersType.subclass(*args_, **kwargs_)
        else:
            return listofallmembersType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_member(self): return self.member
    def set_member(self, member): self.member = member
    def add_member(self, value): self.member.append(value)
    def insert_member(self, index, value): self.member[index] = value
    def hasContent_(self):
        if (
            self.member is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'member':
            obj_ = memberRefType.factory()
            obj_.build(child_)
            self.member.append(obj_)
# end class listofallmembersType


class memberRefType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, virt=None, prot=None, refid=None, ambiguityscope=None, scope=None, name=None):
        self.virt = virt
        self.prot = prot
        self.refid = refid
        self.ambiguityscope = ambiguityscope
        self.scope = scope
        self.name = name
    def factory(*args_, **kwargs_):
        if memberRefType.subclass:
            return memberRefType.subclass(*args_, **kwargs_)
        else:
            return memberRefType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_scope(self): return self.scope
    def set_scope(self, scope): self.scope = scope
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_virt(self): return self.virt
    def set_virt(self, virt): self.virt = virt
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def get_ambiguityscope(self): return self.ambiguityscope
    def set_ambiguityscope(self, ambiguityscope): self.ambiguityscope = ambiguityscope
    def hasContent_(self):
        if (
            self.scope is not None or
            self.name is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('virt'):
            self.virt = attrs.get('virt').value
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
        if attrs.get('ambiguityscope'):
            self.ambiguityscope = attrs.get('ambiguityscope').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'scope':
            scope_ = ''
            for text__content_ in child_.childNodes:
                scope_ += text__content_.nodeValue
            self.scope = scope_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'name':
            name_ = ''
            for text__content_ in child_.childNodes:
                name_ += text__content_.nodeValue
            self.name = name_
# end class memberRefType


class scope(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if scope.subclass:
            return scope.subclass(*args_, **kwargs_)
        else:
            return scope(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class scope


class name(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if name.subclass:
            return name.subclass(*args_, **kwargs_)
        else:
            return name(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class name


class compoundRefType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, virt=None, prot=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        self.virt = virt
        self.prot = prot
        self.refid = refid
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if compoundRefType.subclass:
            return compoundRefType.subclass(*args_, **kwargs_)
        else:
            return compoundRefType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_virt(self): return self.virt
    def set_virt(self, virt): self.virt = virt
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('virt'):
            self.virt = attrs.get('virt').value
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class compoundRefType


class reimplementType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, refid=None, valueOf_='', mixedclass_=None, content_=None):
        self.refid = refid
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if reimplementType.subclass:
            return reimplementType.subclass(*args_, **kwargs_)
        else:
            return reimplementType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class reimplementType


class incType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, local=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        self.local = local
        self.refid = refid
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if incType.subclass:
            return incType.subclass(*args_, **kwargs_)
        else:
            return incType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_local(self): return self.local
    def set_local(self, local): self.local = local
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('local'):
            self.local = attrs.get('local').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class incType


class refType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, prot=None, refid=None, valueOf_='', mixedclass_=None, content_=None):
        self.prot = prot
        self.refid = refid
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if refType.subclass:
            return refType.subclass(*args_, **kwargs_)
        else:
            return refType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class refType


class refTextType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, refid=None, kindref=None, external=None, valueOf_='', mixedclass_=None, content_=None):
        self.refid = refid
        self.kindref = kindref
        self.external = external
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if refTextType.subclass:
            return refTextType.subclass(*args_, **kwargs_)
        else:
            return refTextType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def get_kindref(self): return self.kindref
    def set_kindref(self, kindref): self.kindref = kindref
    def get_external(self): return self.external
    def set_external(self, external): self.external = external
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
        if attrs.get('kindref'):
            self.kindref = attrs.get('kindref').value
        if attrs.get('external'):
            self.external = attrs.get('external').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class refTextType


class sectiondefType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, header=None, description=None, memberdef=None):
        self.kind = kind
        self.header = header
        self.description = description
        if memberdef is None:
            self.memberdef = []
        else:
            self.memberdef = memberdef
    def factory(*args_, **kwargs_):
        if sectiondefType.subclass:
            return sectiondefType.subclass(*args_, **kwargs_)
        else:
            return sectiondefType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_header(self): return self.header
    def set_header(self, header): self.header = header
    def get_description(self): return self.description
    def set_description(self, description): self.description = description
    def get_memberdef(self): return self.memberdef
    def set_memberdef(self, memberdef): self.memberdef = memberdef
    def add_memberdef(self, value): self.memberdef.append(value)
    def insert_memberdef(self, index, value): self.memberdef[index] = value
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def hasContent_(self):
        if (
            self.header is not None or
            self.description is not None or
            self.memberdef is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'header':
            header_ = ''
            for text__content_ in child_.childNodes:
                header_ += text__content_.nodeValue
            self.header = header_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'description':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_description(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'memberdef':
            obj_ = memberdefType.factory()
            obj_.build(child_)
            self.memberdef.append(obj_)
# end class sectiondefType


class memberdefType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, initonly=None, kind=None, volatile=None, const=None, raisexx=None, virt=None, readable=None, prot=None, explicit=None, new=None, final=None, writable=None, add=None, static=None, remove=None, sealed=None, mutable=None, gettable=None, inline=None, settable=None, id=None, templateparamlist=None, type_=None, definition=None, argsstring=None, name=None, read=None, write=None, bitfield=None, reimplements=None, reimplementedby=None, param=None, enumvalue=None, initializer=None, exceptions=None, briefdescription=None, detaileddescription=None, inbodydescription=None, location=None, references=None, referencedby=None):
        self.initonly = initonly
        self.kind = kind
        self.volatile = volatile
        self.const = const
        self.raisexx = raisexx
        self.virt = virt
        self.readable = readable
        self.prot = prot
        self.explicit = explicit
        self.new = new
        self.final = final
        self.writable = writable
        self.add = add
        self.static = static
        self.remove = remove
        self.sealed = sealed
        self.mutable = mutable
        self.gettable = gettable
        self.inline = inline
        self.settable = settable
        self.id = id
        self.templateparamlist = templateparamlist
        self.type_ = type_
        self.definition = definition
        self.argsstring = argsstring
        self.name = name
        self.read = read
        self.write = write
        self.bitfield = bitfield
        if reimplements is None:
            self.reimplements = []
        else:
            self.reimplements = reimplements
        if reimplementedby is None:
            self.reimplementedby = []
        else:
            self.reimplementedby = reimplementedby
        if param is None:
            self.param = []
        else:
            self.param = param
        if enumvalue is None:
            self.enumvalue = []
        else:
            self.enumvalue = enumvalue
        self.initializer = initializer
        self.exceptions = exceptions
        self.briefdescription = briefdescription
        self.detaileddescription = detaileddescription
        self.inbodydescription = inbodydescription
        self.location = location
        if references is None:
            self.references = []
        else:
            self.references = references
        if referencedby is None:
            self.referencedby = []
        else:
            self.referencedby = referencedby
    def factory(*args_, **kwargs_):
        if memberdefType.subclass:
            return memberdefType.subclass(*args_, **kwargs_)
        else:
            return memberdefType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_templateparamlist(self): return self.templateparamlist
    def set_templateparamlist(self, templateparamlist): self.templateparamlist = templateparamlist
    def get_type(self): return self.type_
    def set_type(self, type_): self.type_ = type_
    def get_definition(self): return self.definition
    def set_definition(self, definition): self.definition = definition
    def get_argsstring(self): return self.argsstring
    def set_argsstring(self, argsstring): self.argsstring = argsstring
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_read(self): return self.read
    def set_read(self, read): self.read = read
    def get_write(self): return self.write
    def set_write(self, write): self.write = write
    def get_bitfield(self): return self.bitfield
    def set_bitfield(self, bitfield): self.bitfield = bitfield
    def get_reimplements(self): return self.reimplements
    def set_reimplements(self, reimplements): self.reimplements = reimplements
    def add_reimplements(self, value): self.reimplements.append(value)
    def insert_reimplements(self, index, value): self.reimplements[index] = value
    def get_reimplementedby(self): return self.reimplementedby
    def set_reimplementedby(self, reimplementedby): self.reimplementedby = reimplementedby
    def add_reimplementedby(self, value): self.reimplementedby.append(value)
    def insert_reimplementedby(self, index, value): self.reimplementedby[index] = value
    def get_param(self): return self.param
    def set_param(self, param): self.param = param
    def add_param(self, value): self.param.append(value)
    def insert_param(self, index, value): self.param[index] = value
    def get_enumvalue(self): return self.enumvalue
    def set_enumvalue(self, enumvalue): self.enumvalue = enumvalue
    def add_enumvalue(self, value): self.enumvalue.append(value)
    def insert_enumvalue(self, index, value): self.enumvalue[index] = value
    def get_initializer(self): return self.initializer
    def set_initializer(self, initializer): self.initializer = initializer
    def get_exceptions(self): return self.exceptions
    def set_exceptions(self, exceptions): self.exceptions = exceptions
    def get_briefdescription(self): return self.briefdescription
    def set_briefdescription(self, briefdescription): self.briefdescription = briefdescription
    def get_detaileddescription(self): return self.detaileddescription
    def set_detaileddescription(self, detaileddescription): self.detaileddescription = detaileddescription
    def get_inbodydescription(self): return self.inbodydescription
    def set_inbodydescription(self, inbodydescription): self.inbodydescription = inbodydescription
    def get_location(self): return self.location
    def set_location(self, location): self.location = location
    def get_references(self): return self.references
    def set_references(self, references): self.references = references
    def add_references(self, value): self.references.append(value)
    def insert_references(self, index, value): self.references[index] = value
    def get_referencedby(self): return self.referencedby
    def set_referencedby(self, referencedby): self.referencedby = referencedby
    def add_referencedby(self, value): self.referencedby.append(value)
    def insert_referencedby(self, index, value): self.referencedby[index] = value
    def get_initonly(self): return self.initonly
    def set_initonly(self, initonly): self.initonly = initonly
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def get_volatile(self): return self.volatile
    def set_volatile(self, volatile): self.volatile = volatile
    def get_const(self): return self.const
    def set_const(self, const): self.const = const
    def get_raise(self): return self.raisexx
    def set_raise(self, raisexx): self.raisexx = raisexx
    def get_virt(self): return self.virt
    def set_virt(self, virt): self.virt = virt
    def get_readable(self): return self.readable
    def set_readable(self, readable): self.readable = readable
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_explicit(self): return self.explicit
    def set_explicit(self, explicit): self.explicit = explicit
    def get_new(self): return self.new
    def set_new(self, new): self.new = new
    def get_final(self): return self.final
    def set_final(self, final): self.final = final
    def get_writable(self): return self.writable
    def set_writable(self, writable): self.writable = writable
    def get_add(self): return self.add
    def set_add(self, add): self.add = add
    def get_static(self): return self.static
    def set_static(self, static): self.static = static
    def get_remove(self): return self.remove
    def set_remove(self, remove): self.remove = remove
    def get_sealed(self): return self.sealed
    def set_sealed(self, sealed): self.sealed = sealed
    def get_mutable(self): return self.mutable
    def set_mutable(self, mutable): self.mutable = mutable
    def get_gettable(self): return self.gettable
    def set_gettable(self, gettable): self.gettable = gettable
    def get_inline(self): return self.inline
    def set_inline(self, inline): self.inline = inline
    def get_settable(self): return self.settable
    def set_settable(self, settable): self.settable = settable
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def hasContent_(self):
        if (
            self.templateparamlist is not None or
            self.type_ is not None or
            self.definition is not None or
            self.argsstring is not None or
            self.name is not None or
            self.read is not None or
            self.write is not None or
            self.bitfield is not None or
            self.reimplements is not None or
            self.reimplementedby is not None or
            self.param is not None or
            self.enumvalue is not None or
            self.initializer is not None or
            self.exceptions is not None or
            self.briefdescription is not None or
            self.detaileddescription is not None or
            self.inbodydescription is not None or
            self.location is not None or
            self.references is not None or
            self.referencedby is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('initonly'):
            self.initonly = attrs.get('initonly').value
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
        if attrs.get('volatile'):
            self.volatile = attrs.get('volatile').value
        if attrs.get('const'):
            self.const = attrs.get('const').value
        if attrs.get('raise'):
            self.raisexx = attrs.get('raise').value
        if attrs.get('virt'):
            self.virt = attrs.get('virt').value
        if attrs.get('readable'):
            self.readable = attrs.get('readable').value
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('explicit'):
            self.explicit = attrs.get('explicit').value
        if attrs.get('new'):
            self.new = attrs.get('new').value
        if attrs.get('final'):
            self.final = attrs.get('final').value
        if attrs.get('writable'):
            self.writable = attrs.get('writable').value
        if attrs.get('add'):
            self.add = attrs.get('add').value
        if attrs.get('static'):
            self.static = attrs.get('static').value
        if attrs.get('remove'):
            self.remove = attrs.get('remove').value
        if attrs.get('sealed'):
            self.sealed = attrs.get('sealed').value
        if attrs.get('mutable'):
            self.mutable = attrs.get('mutable').value
        if attrs.get('gettable'):
            self.gettable = attrs.get('gettable').value
        if attrs.get('inline'):
            self.inline = attrs.get('inline').value
        if attrs.get('settable'):
            self.settable = attrs.get('settable').value
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'templateparamlist':
            obj_ = templateparamlistType.factory()
            obj_.build(child_)
            self.set_templateparamlist(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'type':
            obj_ = linkedTextType.factory()
            obj_.build(child_)
            self.set_type(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'definition':
            definition_ = ''
            for text__content_ in child_.childNodes:
                definition_ += text__content_.nodeValue
            self.definition = definition_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'argsstring':
            argsstring_ = ''
            for text__content_ in child_.childNodes:
                argsstring_ += text__content_.nodeValue
            self.argsstring = argsstring_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'name':
            name_ = ''
            for text__content_ in child_.childNodes:
                name_ += text__content_.nodeValue
            self.name = name_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'read':
            read_ = ''
            for text__content_ in child_.childNodes:
                read_ += text__content_.nodeValue
            self.read = read_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'write':
            write_ = ''
            for text__content_ in child_.childNodes:
                write_ += text__content_.nodeValue
            self.write = write_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'bitfield':
            bitfield_ = ''
            for text__content_ in child_.childNodes:
                bitfield_ += text__content_.nodeValue
            self.bitfield = bitfield_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'reimplements':
            obj_ = reimplementType.factory()
            obj_.build(child_)
            self.reimplements.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'reimplementedby':
            obj_ = reimplementType.factory()
            obj_.build(child_)
            self.reimplementedby.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'param':
            obj_ = paramType.factory()
            obj_.build(child_)
            self.param.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'enumvalue':
            obj_ = enumvalueType.factory()
            obj_.build(child_)
            self.enumvalue.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'initializer':
            obj_ = linkedTextType.factory()
            obj_.build(child_)
            self.set_initializer(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'exceptions':
            obj_ = linkedTextType.factory()
            obj_.build(child_)
            self.set_exceptions(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'briefdescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_briefdescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'detaileddescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_detaileddescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'inbodydescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_inbodydescription(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'location':
            obj_ = locationType.factory()
            obj_.build(child_)
            self.set_location(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'references':
            obj_ = referenceType.factory()
            obj_.build(child_)
            self.references.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'referencedby':
            obj_ = referenceType.factory()
            obj_.build(child_)
            self.referencedby.append(obj_)
# end class memberdefType


class definition(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if definition.subclass:
            return definition.subclass(*args_, **kwargs_)
        else:
            return definition(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class definition


class argsstring(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if argsstring.subclass:
            return argsstring.subclass(*args_, **kwargs_)
        else:
            return argsstring(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='argsstring', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='argsstring')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class argsstring


class read(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if read.subclass:
            return read.subclass(*args_, **kwargs_)
        else:
            return read(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class read


class write(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if write.subclass:
            return write.subclass(*args_, **kwargs_)
        else:
            return write(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class write


class bitfield(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if bitfield.subclass:
            return bitfield.subclass(*args_, **kwargs_)
        else:
            return bitfield(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class bitfield


class descriptionType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, title=None, para=None, sect1=None, internal=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if descriptionType.subclass:
            return descriptionType.subclass(*args_, **kwargs_)
        else:
            return descriptionType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect1(self): return self.sect1
    def set_sect1(self, sect1): self.sect1 = sect1
    def add_sect1(self, value): self.sect1.append(value)
    def insert_sect1(self, index, value): self.sect1[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None or
            self.sect1 is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            childobj_ = docTitleType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'title', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect1':
            childobj_ = docSect1Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect1', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            childobj_ = docInternalType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'internal', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class descriptionType


class enumvalueType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, prot=None, id=None, name=None, initializer=None, briefdescription=None, detaileddescription=None, mixedclass_=None, content_=None):
        self.prot = prot
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if enumvalueType.subclass:
            return enumvalueType.subclass(*args_, **kwargs_)
        else:
            return enumvalueType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_initializer(self): return self.initializer
    def set_initializer(self, initializer): self.initializer = initializer
    def get_briefdescription(self): return self.briefdescription
    def set_briefdescription(self, briefdescription): self.briefdescription = briefdescription
    def get_detaileddescription(self): return self.detaileddescription
    def set_detaileddescription(self, detaileddescription): self.detaileddescription = detaileddescription
    def get_prot(self): return self.prot
    def set_prot(self, prot): self.prot = prot
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def hasContent_(self):
        if (
            self.name is not None or
            self.initializer is not None or
            self.briefdescription is not None or
            self.detaileddescription is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('prot'):
            self.prot = attrs.get('prot').value
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'name':
            value_ = []
            for text_ in child_.childNodes:
                value_.append(text_.nodeValue)
            valuestr_ = ''.join(value_)
            obj_ = self.mixedclass_(MixedContainer.CategorySimple,
                MixedContainer.TypeString, 'name', valuestr_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'initializer':
            childobj_ = linkedTextType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'initializer', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'briefdescription':
            childobj_ = descriptionType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'briefdescription', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'detaileddescription':
            childobj_ = descriptionType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'detaileddescription', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class enumvalueType


class templateparamlistType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, param=None):
        if param is None:
            self.param = []
        else:
            self.param = param
    def factory(*args_, **kwargs_):
        if templateparamlistType.subclass:
            return templateparamlistType.subclass(*args_, **kwargs_)
        else:
            return templateparamlistType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_param(self): return self.param
    def set_param(self, param): self.param = param
    def add_param(self, value): self.param.append(value)
    def insert_param(self, index, value): self.param[index] = value
    def hasContent_(self):
        if (
            self.param is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'param':
            obj_ = paramType.factory()
            obj_.build(child_)
            self.param.append(obj_)
# end class templateparamlistType


class paramType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, type_=None, declname=None, defname=None, array=None, defval=None, briefdescription=None):
        self.type_ = type_
        self.declname = declname
        self.defname = defname
        self.array = array
        self.defval = defval
        self.briefdescription = briefdescription
    def factory(*args_, **kwargs_):
        if paramType.subclass:
            return paramType.subclass(*args_, **kwargs_)
        else:
            return paramType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_type(self): return self.type_
    def set_type(self, type_): self.type_ = type_
    def get_declname(self): return self.declname
    def set_declname(self, declname): self.declname = declname
    def get_defname(self): return self.defname
    def set_defname(self, defname): self.defname = defname
    def get_array(self): return self.array
    def set_array(self, array): self.array = array
    def get_defval(self): return self.defval
    def set_defval(self, defval): self.defval = defval
    def get_briefdescription(self): return self.briefdescription
    def set_briefdescription(self, briefdescription): self.briefdescription = briefdescription
    def hasContent_(self):
        if (
            self.type_ is not None or
            self.declname is not None or
            self.defname is not None or
            self.array is not None or
            self.defval is not None or
            self.briefdescription is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'type':
            obj_ = linkedTextType.factory()
            obj_.build(child_)
            self.set_type(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'declname':
            declname_ = ''
            for text__content_ in child_.childNodes:
                declname_ += text__content_.nodeValue
            self.declname = declname_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'defname':
            defname_ = ''
            for text__content_ in child_.childNodes:
                defname_ += text__content_.nodeValue
            self.defname = defname_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'array':
            array_ = ''
            for text__content_ in child_.childNodes:
                array_ += text__content_.nodeValue
            self.array = array_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'defval':
            obj_ = linkedTextType.factory()
            obj_.build(child_)
            self.set_defval(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'briefdescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_briefdescription(obj_)
# end class paramType


class declname(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if declname.subclass:
            return declname.subclass(*args_, **kwargs_)
        else:
            return declname(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class declname


class defname(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if defname.subclass:
            return defname.subclass(*args_, **kwargs_)
        else:
            return defname(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class defname


class array(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if array.subclass:
            return array.subclass(*args_, **kwargs_)
        else:
            return array(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class array


class linkedTextType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, ref=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if linkedTextType.subclass:
            return linkedTextType.subclass(*args_, **kwargs_)
        else:
            return linkedTextType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_ref(self): return self.ref
    def set_ref(self, ref): self.ref = ref
    def add_ref(self, value): self.ref.append(value)
    def insert_ref(self, index, value): self.ref[index] = value
    def hasContent_(self):
        if (
            self.ref is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'ref':
            childobj_ = docRefTextType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'ref', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class linkedTextType


class graphType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, node=None):
        if node is None:
            self.node = []
        else:
            self.node = node
    def factory(*args_, **kwargs_):
        if graphType.subclass:
            return graphType.subclass(*args_, **kwargs_)
        else:
            return graphType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_node(self): return self.node
    def set_node(self, node): self.node = node
    def add_node(self, value): self.node.append(value)
    def insert_node(self, index, value): self.node[index] = value
    def hasContent_(self):
        if (
            self.node is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'node':
            obj_ = nodeType.factory()
            obj_.build(child_)
            self.node.append(obj_)
# end class graphType


class nodeType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, label=None, link=None, childnode=None):
        self.id = id
        self.label = label
        self.link = link
        if childnode is None:
            self.childnode = []
        else:
            self.childnode = childnode
    def factory(*args_, **kwargs_):
        if nodeType.subclass:
            return nodeType.subclass(*args_, **kwargs_)
        else:
            return nodeType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_label(self): return self.label
    def set_label(self, label): self.label = label
    def get_link(self): return self.link
    def set_link(self, link): self.link = link
    def get_childnode(self): return self.childnode
    def set_childnode(self, childnode): self.childnode = childnode
    def add_childnode(self, value): self.childnode.append(value)
    def insert_childnode(self, index, value): self.childnode[index] = value
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def hasContent_(self):
        if (
            self.label is not None or
            self.link is not None or
            self.childnode is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'label':
            label_ = ''
            for text__content_ in child_.childNodes:
                label_ += text__content_.nodeValue
            self.label = label_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'link':
            obj_ = linkType.factory()
            obj_.build(child_)
            self.set_link(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'childnode':
            obj_ = childnodeType.factory()
            obj_.build(child_)
            self.childnode.append(obj_)
# end class nodeType


class label(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if label.subclass:
            return label.subclass(*args_, **kwargs_)
        else:
            return label(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class label


class childnodeType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, relation=None, refid=None, edgelabel=None):
        self.relation = relation
        self.refid = refid
        if edgelabel is None:
            self.edgelabel = []
        else:
            self.edgelabel = edgelabel
    def factory(*args_, **kwargs_):
        if childnodeType.subclass:
            return childnodeType.subclass(*args_, **kwargs_)
        else:
            return childnodeType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_edgelabel(self): return self.edgelabel
    def set_edgelabel(self, edgelabel): self.edgelabel = edgelabel
    def add_edgelabel(self, value): self.edgelabel.append(value)
    def insert_edgelabel(self, index, value): self.edgelabel[index] = value
    def get_relation(self): return self.relation
    def set_relation(self, relation): self.relation = relation
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def export(self, outfile, level, namespace_='', name_='childnodeType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='childnodeType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='childnodeType'):
        if self.relation is not None:
            outfile.write(' relation=%s' % (quote_attrib(self.relation), ))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='childnodeType'):
        for edgelabel_ in self.edgelabel:
            showIndent(outfile, level)
            outfile.write('<%sedgelabel>%s</%sedgelabel>\n' % (namespace_, self.format_string(quote_xml(edgelabel_).encode(ExternalEncoding), input_name='edgelabel'), namespace_))
    def hasContent_(self):
        if (
            self.edgelabel is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('relation'):
            self.relation = attrs.get('relation').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'edgelabel':
            edgelabel_ = ''
            for text__content_ in child_.childNodes:
                edgelabel_ += text__content_.nodeValue
            self.edgelabel.append(edgelabel_)
# end class childnodeType


class edgelabel(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if edgelabel.subclass:
            return edgelabel.subclass(*args_, **kwargs_)
        else:
            return edgelabel(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='edgelabel', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='edgelabel')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='edgelabel'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='edgelabel'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class edgelabel


class linkType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, refid=None, external=None, valueOf_=''):
        self.refid = refid
        self.external = external
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if linkType.subclass:
            return linkType.subclass(*args_, **kwargs_)
        else:
            return linkType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def get_external(self): return self.external
    def set_external(self, external): self.external = external
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='linkType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='linkType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='linkType'):
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
        if self.external is not None:
            outfile.write(' external=%s' % (self.format_string(quote_attrib(self.external).encode(ExternalEncoding), input_name='external'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='linkType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
        if attrs.get('external'):
            self.external = attrs.get('external').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class linkType


class listingType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, codeline=None):
        if codeline is None:
            self.codeline = []
        else:
            self.codeline = codeline
    def factory(*args_, **kwargs_):
        if listingType.subclass:
            return listingType.subclass(*args_, **kwargs_)
        else:
            return listingType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_codeline(self): return self.codeline
    def set_codeline(self, codeline): self.codeline = codeline
    def add_codeline(self, value): self.codeline.append(value)
    def insert_codeline(self, index, value): self.codeline[index] = value
    def export(self, outfile, level, namespace_='', name_='listingType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='listingType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='listingType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='listingType'):
        for codeline_ in self.codeline:
            codeline_.export(outfile, level, namespace_, name_='codeline')
    def hasContent_(self):
        if (
            self.codeline is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'codeline':
            obj_ = codelineType.factory()
            obj_.build(child_)
            self.codeline.append(obj_)
# end class listingType


class codelineType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, external=None, lineno=None, refkind=None, refid=None, highlight=None):
        self.external = external
        self.lineno = lineno
        self.refkind = refkind
        self.refid = refid
        if highlight is None:
            self.highlight = []
        else:
            self.highlight = highlight
    def factory(*args_, **kwargs_):
        if codelineType.subclass:
            return codelineType.subclass(*args_, **kwargs_)
        else:
            return codelineType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_highlight(self): return self.highlight
    def set_highlight(self, highlight): self.highlight = highlight
    def add_highlight(self, value): self.highlight.append(value)
    def insert_highlight(self, index, value): self.highlight[index] = value
    def get_external(self): return self.external
    def set_external(self, external): self.external = external
    def get_lineno(self): return self.lineno
    def set_lineno(self, lineno): self.lineno = lineno
    def get_refkind(self): return self.refkind
    def set_refkind(self, refkind): self.refkind = refkind
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def export(self, outfile, level, namespace_='', name_='codelineType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='codelineType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='codelineType'):
        if self.external is not None:
            outfile.write(' external=%s' % (quote_attrib(self.external), ))
        if self.lineno is not None:
            outfile.write(' lineno="%s"' % self.format_integer(self.lineno, input_name='lineno'))
        if self.refkind is not None:
            outfile.write(' refkind=%s' % (quote_attrib(self.refkind), ))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='codelineType'):
        for highlight_ in self.highlight:
            highlight_.export(outfile, level, namespace_, name_='highlight')
    def hasContent_(self):
        if (
            self.highlight is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('external'):
            self.external = attrs.get('external').value
        if attrs.get('lineno'):
            try:
                self.lineno = int(attrs.get('lineno').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (lineno): %s' % exp)
        if attrs.get('refkind'):
            self.refkind = attrs.get('refkind').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'highlight':
            obj_ = highlightType.factory()
            obj_.build(child_)
            self.highlight.append(obj_)
# end class codelineType


class highlightType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, classxx=None, sp=None, ref=None, mixedclass_=None, content_=None):
        self.classxx = classxx
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if highlightType.subclass:
            return highlightType.subclass(*args_, **kwargs_)
        else:
            return highlightType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_sp(self): return self.sp
    def set_sp(self, sp): self.sp = sp
    def add_sp(self, value): self.sp.append(value)
    def insert_sp(self, index, value): self.sp[index] = value
    def get_ref(self): return self.ref
    def set_ref(self, ref): self.ref = ref
    def add_ref(self, value): self.ref.append(value)
    def insert_ref(self, index, value): self.ref[index] = value
    def get_class(self): return self.classxx
    def set_class(self, classxx): self.classxx = classxx
    def export(self, outfile, level, namespace_='', name_='highlightType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='highlightType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='highlightType'):
        if self.classxx is not None:
            outfile.write(' class=%s' % (quote_attrib(self.classxx), ))
    def exportChildren(self, outfile, level, namespace_='', name_='highlightType'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.sp is not None or
            self.ref is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('class'):
            self.classxx = attrs.get('class').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sp':
            value_ = []
            for text_ in child_.childNodes:
                value_.append(text_.nodeValue)
            # We make this unicode so that our unicode renderer catch-all picks it up
            # otherwise it would go through as 'str' and we'd have to pick it up too
            valuestr_ = u' '
            obj_ = self.mixedclass_(MixedContainer.CategorySimple,
                MixedContainer.TypeString, 'sp', valuestr_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'ref':
            childobj_ = docRefTextType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'ref', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class highlightType


class sp(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if sp.subclass:
            return sp.subclass(*args_, **kwargs_)
        else:
            return sp(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='sp', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='sp')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='sp'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='sp'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class sp


class referenceType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, endline=None, startline=None, refid=None, compoundref=None, valueOf_='', mixedclass_=None, content_=None):
        self.endline = endline
        self.startline = startline
        self.refid = refid
        self.compoundref = compoundref
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if referenceType.subclass:
            return referenceType.subclass(*args_, **kwargs_)
        else:
            return referenceType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_endline(self): return self.endline
    def set_endline(self, endline): self.endline = endline
    def get_startline(self): return self.startline
    def set_startline(self, startline): self.startline = startline
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def get_compoundref(self): return self.compoundref
    def set_compoundref(self, compoundref): self.compoundref = compoundref
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='referenceType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='referenceType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='referenceType'):
        if self.endline is not None:
            outfile.write(' endline="%s"' % self.format_integer(self.endline, input_name='endline'))
        if self.startline is not None:
            outfile.write(' startline="%s"' % self.format_integer(self.startline, input_name='startline'))
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
        if self.compoundref is not None:
            outfile.write(' compoundref=%s' % (self.format_string(quote_attrib(self.compoundref).encode(ExternalEncoding), input_name='compoundref'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='referenceType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('endline'):
            try:
                self.endline = int(attrs.get('endline').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (endline): %s' % exp)
        if attrs.get('startline'):
            try:
                self.startline = int(attrs.get('startline').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (startline): %s' % exp)
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
        if attrs.get('compoundref'):
            self.compoundref = attrs.get('compoundref').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class referenceType


class locationType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, bodystart=None, line=None, bodyend=None, bodyfile=None, file=None, valueOf_=''):
        self.bodystart = bodystart
        self.line = line
        self.bodyend = bodyend
        self.bodyfile = bodyfile
        self.file = file
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if locationType.subclass:
            return locationType.subclass(*args_, **kwargs_)
        else:
            return locationType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_bodystart(self): return self.bodystart
    def set_bodystart(self, bodystart): self.bodystart = bodystart
    def get_line(self): return self.line
    def set_line(self, line): self.line = line
    def get_bodyend(self): return self.bodyend
    def set_bodyend(self, bodyend): self.bodyend = bodyend
    def get_bodyfile(self): return self.bodyfile
    def set_bodyfile(self, bodyfile): self.bodyfile = bodyfile
    def get_file(self): return self.file
    def set_file(self, file): self.file = file
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='locationType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='locationType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='locationType'):
        if self.bodystart is not None:
            outfile.write(' bodystart="%s"' % self.format_integer(self.bodystart, input_name='bodystart'))
        if self.line is not None:
            outfile.write(' line="%s"' % self.format_integer(self.line, input_name='line'))
        if self.bodyend is not None:
            outfile.write(' bodyend="%s"' % self.format_integer(self.bodyend, input_name='bodyend'))
        if self.bodyfile is not None:
            outfile.write(' bodyfile=%s' % (self.format_string(quote_attrib(self.bodyfile).encode(ExternalEncoding), input_name='bodyfile'), ))
        if self.file is not None:
            outfile.write(' file=%s' % (self.format_string(quote_attrib(self.file).encode(ExternalEncoding), input_name='file'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='locationType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('bodystart'):
            try:
                self.bodystart = int(attrs.get('bodystart').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (bodystart): %s' % exp)
        if attrs.get('line'):
            try:
                self.line = int(attrs.get('line').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (line): %s' % exp)
        if attrs.get('bodyend'):
            try:
                self.bodyend = int(attrs.get('bodyend').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (bodyend): %s' % exp)
        if attrs.get('bodyfile'):
            self.bodyfile = attrs.get('bodyfile').value
        if attrs.get('file'):
            self.file = attrs.get('file').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class locationType


class docSect1Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, title=None, para=None, sect2=None, internal=None, mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docSect1Type.subclass:
            return docSect1Type.subclass(*args_, **kwargs_)
        else:
            return docSect1Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect2(self): return self.sect2
    def set_sect2(self, sect2): self.sect2 = sect2
    def add_sect2(self, value): self.sect2.append(value)
    def insert_sect2(self, index, value): self.sect2[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='docSect1Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docSect1Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docSect1Type'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docSect1Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None or
            self.sect2 is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            childobj_ = docTitleType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'title', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect2':
            childobj_ = docSect2Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect2', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            childobj_ = docInternalS1Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'internal', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docSect1Type


class docSect2Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, title=None, para=None, sect3=None, internal=None, mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docSect2Type.subclass:
            return docSect2Type.subclass(*args_, **kwargs_)
        else:
            return docSect2Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect3(self): return self.sect3
    def set_sect3(self, sect3): self.sect3 = sect3
    def add_sect3(self, value): self.sect3.append(value)
    def insert_sect3(self, index, value): self.sect3[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='docSect2Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docSect2Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docSect2Type'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docSect2Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None or
            self.sect3 is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            childobj_ = docTitleType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'title', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect3':
            childobj_ = docSect3Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect3', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            childobj_ = docInternalS2Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'internal', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docSect2Type


class docSect3Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, title=None, para=None, sect4=None, internal=None, mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docSect3Type.subclass:
            return docSect3Type.subclass(*args_, **kwargs_)
        else:
            return docSect3Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect4(self): return self.sect4
    def set_sect4(self, sect4): self.sect4 = sect4
    def add_sect4(self, value): self.sect4.append(value)
    def insert_sect4(self, index, value): self.sect4[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='docSect3Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docSect3Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docSect3Type'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docSect3Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None or
            self.sect4 is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            childobj_ = docTitleType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'title', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect4':
            childobj_ = docSect4Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect4', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            childobj_ = docInternalS3Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'internal', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docSect3Type


class docSect4Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, title=None, para=None, internal=None, mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docSect4Type.subclass:
            return docSect4Type.subclass(*args_, **kwargs_)
        else:
            return docSect4Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='docSect4Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docSect4Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docSect4Type'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docSect4Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            childobj_ = docTitleType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'title', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            childobj_ = docInternalS4Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'internal', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docSect4Type


class docInternalType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None, sect1=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docInternalType.subclass:
            return docInternalType.subclass(*args_, **kwargs_)
        else:
            return docInternalType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect1(self): return self.sect1
    def set_sect1(self, sect1): self.sect1 = sect1
    def add_sect1(self, value): self.sect1.append(value)
    def insert_sect1(self, index, value): self.sect1[index] = value
    def export(self, outfile, level, namespace_='', name_='docInternalType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docInternalType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docInternalType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docInternalType'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.para is not None or
            self.sect1 is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect1':
            childobj_ = docSect1Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect1', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docInternalType


class docInternalS1Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None, sect2=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docInternalS1Type.subclass:
            return docInternalS1Type.subclass(*args_, **kwargs_)
        else:
            return docInternalS1Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect2(self): return self.sect2
    def set_sect2(self, sect2): self.sect2 = sect2
    def add_sect2(self, value): self.sect2.append(value)
    def insert_sect2(self, index, value): self.sect2[index] = value
    def export(self, outfile, level, namespace_='', name_='docInternalS1Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docInternalS1Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docInternalS1Type'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docInternalS1Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.para is not None or
            self.sect2 is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect2':
            childobj_ = docSect2Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect2', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docInternalS1Type


class docInternalS2Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None, sect3=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docInternalS2Type.subclass:
            return docInternalS2Type.subclass(*args_, **kwargs_)
        else:
            return docInternalS2Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect3(self): return self.sect3
    def set_sect3(self, sect3): self.sect3 = sect3
    def add_sect3(self, value): self.sect3.append(value)
    def insert_sect3(self, index, value): self.sect3[index] = value
    def export(self, outfile, level, namespace_='', name_='docInternalS2Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docInternalS2Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docInternalS2Type'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docInternalS2Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.para is not None or
            self.sect3 is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect3':
            childobj_ = docSect3Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect3', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docInternalS2Type


class docInternalS3Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None, sect3=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docInternalS3Type.subclass:
            return docInternalS3Type.subclass(*args_, **kwargs_)
        else:
            return docInternalS3Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect3(self): return self.sect3
    def set_sect3(self, sect3): self.sect3 = sect3
    def add_sect3(self, value): self.sect3.append(value)
    def insert_sect3(self, index, value): self.sect3[index] = value
    def export(self, outfile, level, namespace_='', name_='docInternalS3Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docInternalS3Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docInternalS3Type'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docInternalS3Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.para is not None or
            self.sect3 is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect3':
            childobj_ = docSect4Type.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'sect3', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docInternalS3Type


class docInternalS4Type(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None, mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docInternalS4Type.subclass:
            return docInternalS4Type.subclass(*args_, **kwargs_)
        else:
            return docInternalS4Type(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def export(self, outfile, level, namespace_='', name_='docInternalS4Type', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docInternalS4Type')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docInternalS4Type'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docInternalS4Type'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.para is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            childobj_ = docParaType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'para', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docInternalS4Type


class docTitleType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_='', mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docTitleType.subclass:
            return docTitleType.subclass(*args_, **kwargs_)
        else:
            return docTitleType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docTitleType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docTitleType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docTitleType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docTitleType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docTitleType


class docParaType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_='', mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docParaType.subclass:
            return docParaType.subclass(*args_, **kwargs_)
        else:
            return docParaType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docParaType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docParaType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docParaType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docParaType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docParaType


class docMarkupType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_='', mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docMarkupType.subclass:
            return docMarkupType.subclass(*args_, **kwargs_)
        else:
            return docMarkupType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docMarkupType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docMarkupType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docMarkupType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docMarkupType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docMarkupType


class docURLLink(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, url=None, valueOf_='', mixedclass_=None, content_=None):
        self.url = url
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docURLLink.subclass:
            return docURLLink.subclass(*args_, **kwargs_)
        else:
            return docURLLink(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_url(self): return self.url
    def set_url(self, url): self.url = url
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docURLLink', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docURLLink')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docURLLink'):
        if self.url is not None:
            outfile.write(' url=%s' % (self.format_string(quote_attrib(self.url).encode(ExternalEncoding), input_name='url'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docURLLink'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('url'):
            self.url = attrs.get('url').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docURLLink


class docAnchorType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docAnchorType.subclass:
            return docAnchorType.subclass(*args_, **kwargs_)
        else:
            return docAnchorType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docAnchorType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docAnchorType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docAnchorType'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docAnchorType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docAnchorType


class docFormulaType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docFormulaType.subclass:
            return docFormulaType.subclass(*args_, **kwargs_)
        else:
            return docFormulaType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docFormulaType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docFormulaType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docFormulaType'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docFormulaType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docFormulaType


class docIndexEntryType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, primaryie=None, secondaryie=None):
        self.primaryie = primaryie
        self.secondaryie = secondaryie
    def factory(*args_, **kwargs_):
        if docIndexEntryType.subclass:
            return docIndexEntryType.subclass(*args_, **kwargs_)
        else:
            return docIndexEntryType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_primaryie(self): return self.primaryie
    def set_primaryie(self, primaryie): self.primaryie = primaryie
    def get_secondaryie(self): return self.secondaryie
    def set_secondaryie(self, secondaryie): self.secondaryie = secondaryie
    def export(self, outfile, level, namespace_='', name_='docIndexEntryType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docIndexEntryType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docIndexEntryType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docIndexEntryType'):
        if self.primaryie is not None:
            showIndent(outfile, level)
            outfile.write('<%sprimaryie>%s</%sprimaryie>\n' % (namespace_, self.format_string(quote_xml(self.primaryie).encode(ExternalEncoding), input_name='primaryie'), namespace_))
        if self.secondaryie is not None:
            showIndent(outfile, level)
            outfile.write('<%ssecondaryie>%s</%ssecondaryie>\n' % (namespace_, self.format_string(quote_xml(self.secondaryie).encode(ExternalEncoding), input_name='secondaryie'), namespace_))
    def hasContent_(self):
        if (
            self.primaryie is not None or
            self.secondaryie is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'primaryie':
            primaryie_ = ''
            for text__content_ in child_.childNodes:
                primaryie_ += text__content_.nodeValue
            self.primaryie = primaryie_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'secondaryie':
            secondaryie_ = ''
            for text__content_ in child_.childNodes:
                secondaryie_ += text__content_.nodeValue
            self.secondaryie = secondaryie_
# end class docIndexEntryType


class docListType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, listitem=None):
        if listitem is None:
            self.listitem = []
        else:
            self.listitem = listitem
    def factory(*args_, **kwargs_):
        if docListType.subclass:
            return docListType.subclass(*args_, **kwargs_)
        else:
            return docListType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_listitem(self): return self.listitem
    def set_listitem(self, listitem): self.listitem = listitem
    def add_listitem(self, value): self.listitem.append(value)
    def insert_listitem(self, index, value): self.listitem[index] = value
    def export(self, outfile, level, namespace_='', name_='docListType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docListType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docListType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docListType'):
        for listitem_ in self.listitem:
            listitem_.export(outfile, level, namespace_, name_='listitem')
    def hasContent_(self):
        if (
            self.listitem is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'listitem':
            obj_ = docListItemType.factory()
            obj_.build(child_)
            self.listitem.append(obj_)
# end class docListType


class docListItemType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, para=None):
        if para is None:
            self.para = []
        else:
            self.para = para
    def factory(*args_, **kwargs_):
        if docListItemType.subclass:
            return docListItemType.subclass(*args_, **kwargs_)
        else:
            return docListItemType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def export(self, outfile, level, namespace_='', name_='docListItemType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docListItemType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docListItemType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docListItemType'):
        for para_ in self.para:
            para_.export(outfile, level, namespace_, name_='para')
    def hasContent_(self):
        if (
            self.para is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            obj_ = docParaType.factory()
            obj_.build(child_)
            self.para.append(obj_)
# end class docListItemType


class docSimpleSectType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, title=None, para=None):
        self.kind = kind
        self.title = title
        if para is None:
            self.para = []
        else:
            self.para = para
    def factory(*args_, **kwargs_):
        if docSimpleSectType.subclass:
            return docSimpleSectType.subclass(*args_, **kwargs_)
        else:
            return docSimpleSectType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_title(self): return self.title
    def set_title(self, title): self.title = title
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def export(self, outfile, level, namespace_='', name_='docSimpleSectType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docSimpleSectType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docSimpleSectType'):
        if self.kind is not None:
            outfile.write(' kind=%s' % (quote_attrib(self.kind), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docSimpleSectType'):
        if self.title:
            self.title.export(outfile, level, namespace_, name_='title')
        for para_ in self.para:
            para_.export(outfile, level, namespace_, name_='para')
    def hasContent_(self):
        if (
            self.title is not None or
            self.para is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'title':
            obj_ = docTitleType.factory()
            obj_.build(child_)
            self.set_title(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            obj_ = docParaType.factory()
            obj_.build(child_)
            self.para.append(obj_)
# end class docSimpleSectType


class docVarListEntryType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, term=None):
        self.term = term
    def factory(*args_, **kwargs_):
        if docVarListEntryType.subclass:
            return docVarListEntryType.subclass(*args_, **kwargs_)
        else:
            return docVarListEntryType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_term(self): return self.term
    def set_term(self, term): self.term = term
    def export(self, outfile, level, namespace_='', name_='docVarListEntryType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docVarListEntryType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docVarListEntryType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docVarListEntryType'):
        if self.term:
            self.term.export(outfile, level, namespace_, name_='term', )
    def hasContent_(self):
        if (
            self.term is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'term':
            obj_ = docTitleType.factory()
            obj_.build(child_)
            self.set_term(obj_)
# end class docVarListEntryType


class docVariableListType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if docVariableListType.subclass:
            return docVariableListType.subclass(*args_, **kwargs_)
        else:
            return docVariableListType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docVariableListType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docVariableListType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docVariableListType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docVariableListType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docVariableListType


class docRefTextType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, refid=None, kindref=None, external=None, valueOf_='', mixedclass_=None, content_=None):
        self.refid = refid
        self.kindref = kindref
        self.external = external
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docRefTextType.subclass:
            return docRefTextType.subclass(*args_, **kwargs_)
        else:
            return docRefTextType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def get_kindref(self): return self.kindref
    def set_kindref(self, kindref): self.kindref = kindref
    def get_external(self): return self.external
    def set_external(self, external): self.external = external
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docRefTextType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docRefTextType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docRefTextType'):
        if self.refid is not None:
            outfile.write(' refid=%s' % (self.format_string(quote_attrib(self.refid).encode(ExternalEncoding), input_name='refid'), ))
        if self.kindref is not None:
            outfile.write(' kindref=%s' % (quote_attrib(self.kindref), ))
        if self.external is not None:
            outfile.write(' external=%s' % (self.format_string(quote_attrib(self.external).encode(ExternalEncoding), input_name='external'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docRefTextType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
        if attrs.get('kindref'):
            self.kindref = attrs.get('kindref').value
        if attrs.get('external'):
            self.external = attrs.get('external').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docRefTextType


class docTableType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, rows=None, cols=None, row=None, caption=None):
        self.rows = rows
        self.cols = cols
        if row is None:
            self.row = []
        else:
            self.row = row
        self.caption = caption
    def factory(*args_, **kwargs_):
        if docTableType.subclass:
            return docTableType.subclass(*args_, **kwargs_)
        else:
            return docTableType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_row(self): return self.row
    def set_row(self, row): self.row = row
    def add_row(self, value): self.row.append(value)
    def insert_row(self, index, value): self.row[index] = value
    def get_caption(self): return self.caption
    def set_caption(self, caption): self.caption = caption
    def get_rows(self): return self.rows
    def set_rows(self, rows): self.rows = rows
    def get_cols(self): return self.cols
    def set_cols(self, cols): self.cols = cols
    def export(self, outfile, level, namespace_='', name_='docTableType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docTableType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docTableType'):
        if self.rows is not None:
            outfile.write(' rows="%s"' % self.format_integer(self.rows, input_name='rows'))
        if self.cols is not None:
            outfile.write(' cols="%s"' % self.format_integer(self.cols, input_name='cols'))
    def exportChildren(self, outfile, level, namespace_='', name_='docTableType'):
        for row_ in self.row:
            row_.export(outfile, level, namespace_, name_='row')
        if self.caption:
            self.caption.export(outfile, level, namespace_, name_='caption')
    def hasContent_(self):
        if (
            self.row is not None or
            self.caption is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('rows'):
            try:
                self.rows = int(attrs.get('rows').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (rows): %s' % exp)
        if attrs.get('cols'):
            try:
                self.cols = int(attrs.get('cols').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (cols): %s' % exp)
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'row':
            obj_ = docRowType.factory()
            obj_.build(child_)
            self.row.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'caption':
            obj_ = docCaptionType.factory()
            obj_.build(child_)
            self.set_caption(obj_)
# end class docTableType


class docRowType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, entry=None):
        if entry is None:
            self.entry = []
        else:
            self.entry = entry
    def factory(*args_, **kwargs_):
        if docRowType.subclass:
            return docRowType.subclass(*args_, **kwargs_)
        else:
            return docRowType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_entry(self): return self.entry
    def set_entry(self, entry): self.entry = entry
    def add_entry(self, value): self.entry.append(value)
    def insert_entry(self, index, value): self.entry[index] = value
    def export(self, outfile, level, namespace_='', name_='docRowType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docRowType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docRowType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docRowType'):
        for entry_ in self.entry:
            entry_.export(outfile, level, namespace_, name_='entry')
    def hasContent_(self):
        if (
            self.entry is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'entry':
            obj_ = docEntryType.factory()
            obj_.build(child_)
            self.entry.append(obj_)
# end class docRowType


class docEntryType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, thead=None, para=None):
        self.thead = thead
        if para is None:
            self.para = []
        else:
            self.para = para
    def factory(*args_, **kwargs_):
        if docEntryType.subclass:
            return docEntryType.subclass(*args_, **kwargs_)
        else:
            return docEntryType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_thead(self): return self.thead
    def set_thead(self, thead): self.thead = thead
    def export(self, outfile, level, namespace_='', name_='docEntryType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docEntryType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docEntryType'):
        if self.thead is not None:
            outfile.write(' thead=%s' % (quote_attrib(self.thead), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docEntryType'):
        for para_ in self.para:
            para_.export(outfile, level, namespace_, name_='para')
    def hasContent_(self):
        if (
            self.para is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('thead'):
            self.thead = attrs.get('thead').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            obj_ = docParaType.factory()
            obj_.build(child_)
            self.para.append(obj_)
# end class docEntryType


class docCaptionType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_='', mixedclass_=None, content_=None):
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docCaptionType.subclass:
            return docCaptionType.subclass(*args_, **kwargs_)
        else:
            return docCaptionType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docCaptionType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docCaptionType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docCaptionType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docCaptionType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docCaptionType


class docHeadingType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, level=None, valueOf_='', mixedclass_=None, content_=None):
        self.level = level
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docHeadingType.subclass:
            return docHeadingType.subclass(*args_, **kwargs_)
        else:
            return docHeadingType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_level(self): return self.level
    def set_level(self, level): self.level = level
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docHeadingType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docHeadingType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docHeadingType'):
        if self.level is not None:
            outfile.write(' level="%s"' % self.format_integer(self.level, input_name='level'))
    def exportChildren(self, outfile, level, namespace_='', name_='docHeadingType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('level'):
            try:
                self.level = int(attrs.get('level').value)
            except ValueError, exp:
                raise ValueError('Bad integer attribute (level): %s' % exp)
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docHeadingType


class docImageType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, width=None, type_=None, name=None, height=None, valueOf_='', mixedclass_=None, content_=None):
        self.width = width
        self.type_ = type_
        self.name = name
        self.height = height
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docImageType.subclass:
            return docImageType.subclass(*args_, **kwargs_)
        else:
            return docImageType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_width(self): return self.width
    def set_width(self, width): self.width = width
    def get_type(self): return self.type_
    def set_type(self, type_): self.type_ = type_
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_height(self): return self.height
    def set_height(self, height): self.height = height
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docImageType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docImageType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docImageType'):
        if self.width is not None:
            outfile.write(' width=%s' % (self.format_string(quote_attrib(self.width).encode(ExternalEncoding), input_name='width'), ))
        if self.type_ is not None:
            outfile.write(' type=%s' % (quote_attrib(self.type_), ))
        if self.name is not None:
            outfile.write(' name=%s' % (self.format_string(quote_attrib(self.name).encode(ExternalEncoding), input_name='name'), ))
        if self.height is not None:
            outfile.write(' height=%s' % (self.format_string(quote_attrib(self.height).encode(ExternalEncoding), input_name='height'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docImageType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('width'):
            self.width = attrs.get('width').value
        if attrs.get('type'):
            self.type_ = attrs.get('type').value
        if attrs.get('name'):
            self.name = attrs.get('name').value
        if attrs.get('height'):
            self.height = attrs.get('height').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docImageType


class docDotFileType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, name=None, valueOf_='', mixedclass_=None, content_=None):
        self.name = name
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docDotFileType.subclass:
            return docDotFileType.subclass(*args_, **kwargs_)
        else:
            return docDotFileType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docDotFileType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docDotFileType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docDotFileType'):
        if self.name is not None:
            outfile.write(' name=%s' % (self.format_string(quote_attrib(self.name).encode(ExternalEncoding), input_name='name'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docDotFileType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('name'):
            self.name = attrs.get('name').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docDotFileType


class docTocItemType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, valueOf_='', mixedclass_=None, content_=None):
        self.id = id
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docTocItemType.subclass:
            return docTocItemType.subclass(*args_, **kwargs_)
        else:
            return docTocItemType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docTocItemType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docTocItemType')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docTocItemType'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docTocItemType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docTocItemType


class docTocListType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, tocitem=None):
        if tocitem is None:
            self.tocitem = []
        else:
            self.tocitem = tocitem
    def factory(*args_, **kwargs_):
        if docTocListType.subclass:
            return docTocListType.subclass(*args_, **kwargs_)
        else:
            return docTocListType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_tocitem(self): return self.tocitem
    def set_tocitem(self, tocitem): self.tocitem = tocitem
    def add_tocitem(self, value): self.tocitem.append(value)
    def insert_tocitem(self, index, value): self.tocitem[index] = value
    def export(self, outfile, level, namespace_='', name_='docTocListType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docTocListType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docTocListType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docTocListType'):
        for tocitem_ in self.tocitem:
            tocitem_.export(outfile, level, namespace_, name_='tocitem')
    def hasContent_(self):
        if (
            self.tocitem is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'tocitem':
            obj_ = docTocItemType.factory()
            obj_.build(child_)
            self.tocitem.append(obj_)
# end class docTocListType


class docLanguageType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, langid=None, para=None):
        self.langid = langid
        if para is None:
            self.para = []
        else:
            self.para = para
    def factory(*args_, **kwargs_):
        if docLanguageType.subclass:
            return docLanguageType.subclass(*args_, **kwargs_)
        else:
            return docLanguageType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_langid(self): return self.langid
    def set_langid(self, langid): self.langid = langid
    def export(self, outfile, level, namespace_='', name_='docLanguageType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docLanguageType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docLanguageType'):
        if self.langid is not None:
            outfile.write(' langid=%s' % (self.format_string(quote_attrib(self.langid).encode(ExternalEncoding), input_name='langid'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docLanguageType'):
        for para_ in self.para:
            para_.export(outfile, level, namespace_, name_='para')
    def hasContent_(self):
        if (
            self.para is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('langid'):
            self.langid = attrs.get('langid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            obj_ = docParaType.factory()
            obj_.build(child_)
            self.para.append(obj_)
# end class docLanguageType


class docParamListType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, parameteritem=None):
        self.kind = kind
        if parameteritem is None:
            self.parameteritem = []
        else:
            self.parameteritem = parameteritem
    def factory(*args_, **kwargs_):
        if docParamListType.subclass:
            return docParamListType.subclass(*args_, **kwargs_)
        else:
            return docParamListType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_parameteritem(self): return self.parameteritem
    def set_parameteritem(self, parameteritem): self.parameteritem = parameteritem
    def add_parameteritem(self, value): self.parameteritem.append(value)
    def insert_parameteritem(self, index, value): self.parameteritem[index] = value
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def export(self, outfile, level, namespace_='', name_='docParamListType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docParamListType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docParamListType'):
        if self.kind is not None:
            outfile.write(' kind=%s' % (quote_attrib(self.kind), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docParamListType'):
        for parameteritem_ in self.parameteritem:
            parameteritem_.export(outfile, level, namespace_, name_='parameteritem')
    def hasContent_(self):
        if (
            self.parameteritem is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'parameteritem':
            obj_ = docParamListItem.factory()
            obj_.build(child_)
            self.parameteritem.append(obj_)
# end class docParamListType


class docParamListItem(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, parameternamelist=None, parameterdescription=None):
        if parameternamelist is None:
            self.parameternamelist = []
        else:
            self.parameternamelist = parameternamelist
        self.parameterdescription = parameterdescription
    def factory(*args_, **kwargs_):
        if docParamListItem.subclass:
            return docParamListItem.subclass(*args_, **kwargs_)
        else:
            return docParamListItem(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_parameternamelist(self): return self.parameternamelist
    def set_parameternamelist(self, parameternamelist): self.parameternamelist = parameternamelist
    def add_parameternamelist(self, value): self.parameternamelist.append(value)
    def insert_parameternamelist(self, index, value): self.parameternamelist[index] = value
    def get_parameterdescription(self): return self.parameterdescription
    def set_parameterdescription(self, parameterdescription): self.parameterdescription = parameterdescription
    def export(self, outfile, level, namespace_='', name_='docParamListItem', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docParamListItem')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docParamListItem'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docParamListItem'):
        for parameternamelist_ in self.parameternamelist:
            parameternamelist_.export(outfile, level, namespace_, name_='parameternamelist')
        if self.parameterdescription:
            self.parameterdescription.export(outfile, level, namespace_, name_='parameterdescription', )
    def hasContent_(self):
        if (
            self.parameternamelist is not None or
            self.parameterdescription is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'parameternamelist':
            obj_ = docParamNameList.factory()
            obj_.build(child_)
            self.parameternamelist.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'parameterdescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_parameterdescription(obj_)
# end class docParamListItem


class docParamNameList(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, parametername=None):
        if parametername is None:
            self.parametername = []
        else:
            self.parametername = parametername
    def factory(*args_, **kwargs_):
        if docParamNameList.subclass:
            return docParamNameList.subclass(*args_, **kwargs_)
        else:
            return docParamNameList(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_parametername(self): return self.parametername
    def set_parametername(self, parametername): self.parametername = parametername
    def add_parametername(self, value): self.parametername.append(value)
    def insert_parametername(self, index, value): self.parametername[index] = value
    def export(self, outfile, level, namespace_='', name_='docParamNameList', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docParamNameList')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docParamNameList'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docParamNameList'):
        for parametername_ in self.parametername:
            parametername_.export(outfile, level, namespace_, name_='parametername')
    def hasContent_(self):
        if (
            self.parametername is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'parametername':
            obj_ = docParamName.factory()
            obj_.build(child_)
            self.parametername.append(obj_)
# end class docParamNameList


class docParamName(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, direction=None, ref=None, mixedclass_=None, content_=None):
        self.direction = direction
        if mixedclass_ is None:
            self.mixedclass_ = MixedContainer
        else:
            self.mixedclass_ = mixedclass_
        if content_ is None:
            self.content_ = []
        else:
            self.content_ = content_
    def factory(*args_, **kwargs_):
        if docParamName.subclass:
            return docParamName.subclass(*args_, **kwargs_)
        else:
            return docParamName(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_ref(self): return self.ref
    def set_ref(self, ref): self.ref = ref
    def get_direction(self): return self.direction
    def set_direction(self, direction): self.direction = direction
    def export(self, outfile, level, namespace_='', name_='docParamName', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docParamName')
        outfile.write('>')
        self.exportChildren(outfile, level + 1, namespace_, name_)
        outfile.write('</%s%s>\n' % (namespace_, name_))
    def exportAttributes(self, outfile, level, namespace_='', name_='docParamName'):
        if self.direction is not None:
            outfile.write(' direction=%s' % (quote_attrib(self.direction), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docParamName'):
        for item_ in self.content_:
            item_.export(outfile, level, item_.name, namespace_)
    def hasContent_(self):
        if (
            self.ref is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('direction'):
            self.direction = attrs.get('direction').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'ref':
            childobj_ = docRefTextType.factory()
            childobj_.build(child_)
            obj_ = self.mixedclass_(MixedContainer.CategoryComplex,
                MixedContainer.TypeNone, 'ref', childobj_)
            self.content_.append(obj_)
        elif child_.nodeType == Node.TEXT_NODE:
            obj_ = self.mixedclass_(MixedContainer.CategoryText,
                MixedContainer.TypeNone, '', child_.nodeValue)
            self.content_.append(obj_)
# end class docParamName


class docXRefSectType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, id=None, xreftitle=None, xrefdescription=None):
        self.id = id
        if xreftitle is None:
            self.xreftitle = []
        else:
            self.xreftitle = xreftitle
        self.xrefdescription = xrefdescription
    def factory(*args_, **kwargs_):
        if docXRefSectType.subclass:
            return docXRefSectType.subclass(*args_, **kwargs_)
        else:
            return docXRefSectType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_xreftitle(self): return self.xreftitle
    def set_xreftitle(self, xreftitle): self.xreftitle = xreftitle
    def add_xreftitle(self, value): self.xreftitle.append(value)
    def insert_xreftitle(self, index, value): self.xreftitle[index] = value
    def get_xrefdescription(self): return self.xrefdescription
    def set_xrefdescription(self, xrefdescription): self.xrefdescription = xrefdescription
    def get_id(self): return self.id
    def set_id(self, id): self.id = id
    def export(self, outfile, level, namespace_='', name_='docXRefSectType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docXRefSectType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docXRefSectType'):
        if self.id is not None:
            outfile.write(' id=%s' % (self.format_string(quote_attrib(self.id).encode(ExternalEncoding), input_name='id'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docXRefSectType'):
        for xreftitle_ in self.xreftitle:
            showIndent(outfile, level)
            outfile.write('<%sxreftitle>%s</%sxreftitle>\n' % (namespace_, self.format_string(quote_xml(xreftitle_).encode(ExternalEncoding), input_name='xreftitle'), namespace_))
        if self.xrefdescription:
            self.xrefdescription.export(outfile, level, namespace_, name_='xrefdescription', )
    def hasContent_(self):
        if (
            self.xreftitle is not None or
            self.xrefdescription is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('id'):
            self.id = attrs.get('id').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'xreftitle':
            xreftitle_ = ''
            for text__content_ in child_.childNodes:
                xreftitle_ += text__content_.nodeValue
            self.xreftitle.append(xreftitle_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'xrefdescription':
            obj_ = descriptionType.factory()
            obj_.build(child_)
            self.set_xrefdescription(obj_)
# end class docXRefSectType


class docCopyType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, link=None, para=None, sect1=None, internal=None):
        self.link = link
        if para is None:
            self.para = []
        else:
            self.para = para
        if sect1 is None:
            self.sect1 = []
        else:
            self.sect1 = sect1
        self.internal = internal
    def factory(*args_, **kwargs_):
        if docCopyType.subclass:
            return docCopyType.subclass(*args_, **kwargs_)
        else:
            return docCopyType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_para(self): return self.para
    def set_para(self, para): self.para = para
    def add_para(self, value): self.para.append(value)
    def insert_para(self, index, value): self.para[index] = value
    def get_sect1(self): return self.sect1
    def set_sect1(self, sect1): self.sect1 = sect1
    def add_sect1(self, value): self.sect1.append(value)
    def insert_sect1(self, index, value): self.sect1[index] = value
    def get_internal(self): return self.internal
    def set_internal(self, internal): self.internal = internal
    def get_link(self): return self.link
    def set_link(self, link): self.link = link
    def export(self, outfile, level, namespace_='', name_='docCopyType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docCopyType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docCopyType'):
        if self.link is not None:
            outfile.write(' link=%s' % (self.format_string(quote_attrib(self.link).encode(ExternalEncoding), input_name='link'), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docCopyType'):
        for para_ in self.para:
            para_.export(outfile, level, namespace_, name_='para')
        for sect1_ in self.sect1:
            sect1_.export(outfile, level, namespace_, name_='sect1')
        if self.internal:
            self.internal.export(outfile, level, namespace_, name_='internal')
    def hasContent_(self):
        if (
            self.para is not None or
            self.sect1 is not None or
            self.internal is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('link'):
            self.link = attrs.get('link').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'para':
            obj_ = docParaType.factory()
            obj_.build(child_)
            self.para.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'sect1':
            obj_ = docSect1Type.factory()
            obj_.build(child_)
            self.sect1.append(obj_)
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'internal':
            obj_ = docInternalType.factory()
            obj_.build(child_)
            self.set_internal(obj_)
# end class docCopyType


class docCharType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, char=None, valueOf_=''):
        self.char = char
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if docCharType.subclass:
            return docCharType.subclass(*args_, **kwargs_)
        else:
            return docCharType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_char(self): return self.char
    def set_char(self, char): self.char = char
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docCharType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docCharType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docCharType'):
        if self.char is not None:
            outfile.write(' char=%s' % (quote_attrib(self.char), ))
    def exportChildren(self, outfile, level, namespace_='', name_='docCharType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('char'):
            self.char = attrs.get('char').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docCharType


class docEmptyType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, valueOf_=''):
        self.valueOf_ = valueOf_
    def factory(*args_, **kwargs_):
        if docEmptyType.subclass:
            return docEmptyType.subclass(*args_, **kwargs_)
        else:
            return docEmptyType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def getValueOf_(self): return self.valueOf_
    def setValueOf_(self, valueOf_): self.valueOf_ = valueOf_
    def export(self, outfile, level, namespace_='', name_='docEmptyType', namespacedef_=''):
        showIndent(outfile, level)
        outfile.write('<%s%s %s' % (namespace_, name_, namespacedef_, ))
        self.exportAttributes(outfile, level, namespace_, name_='docEmptyType')
        if self.hasContent_():
            outfile.write('>\n')
            self.exportChildren(outfile, level + 1, namespace_, name_)
            showIndent(outfile, level)
            outfile.write('</%s%s>\n' % (namespace_, name_))
        else:
            outfile.write(' />\n')
    def exportAttributes(self, outfile, level, namespace_='', name_='docEmptyType'):
        pass
    def exportChildren(self, outfile, level, namespace_='', name_='docEmptyType'):
        if self.valueOf_.find('![CDATA')>-1:
            value=quote_xml('%s' % self.valueOf_)
            value=value.replace('![CDATA','<![CDATA')
            value=value.replace(']]',']]>')
            outfile.write(value)
        else:
            outfile.write(quote_xml('%s' % self.valueOf_))
    def hasContent_(self):
        if (
            self.valueOf_ is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        self.valueOf_ = ''
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        pass
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.TEXT_NODE:
            self.valueOf_ += child_.nodeValue
        elif child_.nodeType == Node.CDATA_SECTION_NODE:
            self.valueOf_ += '![CDATA['+child_.nodeValue+']]'
# end class docEmptyType


USAGE_TEXT = """
Usage: python <Parser>.py [ -s ] <in_xml_file>
Options:
    -s        Use the SAX parser, not the minidom parser.
"""

def usage():
    print USAGE_TEXT
    sys.exit(1)


def parse(inFileName):
    doc = minidom.parse(inFileName)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('<?xml version="1.0" ?>\n')
    rootObj.export(sys.stdout, 0, name_="doxygen",
        namespacedef_='')
    return rootObj


def parseString(inString):
    doc = minidom.parseString(inString)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('<?xml version="1.0" ?>\n')
    rootObj.export(sys.stdout, 0, name_="doxygen",
        namespacedef_='')
    return rootObj


def parseLiteral(inFileName):
    doc = minidom.parse(inFileName)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('from compound import *\n\n')
    sys.stdout.write('rootObj = doxygen(\n')
    rootObj.exportLiteral(sys.stdout, 0, name_="doxygen")
    sys.stdout.write(')\n')
    return rootObj


def main():
    args = sys.argv[1:]
    if len(args) == 1:
        parse(args[0])
    else:
        usage()


if __name__ == '__main__':
    main()
    #import pdb
    #pdb.run('main()')


########NEW FILE########
__FILENAME__ = index
#!/usr/bin/env python

"""
Generated Mon Feb  9 19:08:05 2009 by generateDS.py.
"""

from xml.dom import minidom
from xml.parsers.expat import ExpatError


import indexsuper as supermod

class DoxygenTypeSub(supermod.DoxygenType):

    node_type = "doxygen"

    def __init__(self, version=None, compound=None):
        supermod.DoxygenType.__init__(self, version, compound)
supermod.DoxygenType.subclass = DoxygenTypeSub
# end class DoxygenTypeSub


class CompoundTypeSub(supermod.CompoundType):
    
    node_type = "compound"

    def __init__(self, kind=None, refid=None, name='', member=None):
        supermod.CompoundType.__init__(self, kind, refid, name, member)
supermod.CompoundType.subclass = CompoundTypeSub
# end class CompoundTypeSub


class MemberTypeSub(supermod.MemberType):

    node_type = "member"

    def __init__(self, kind=None, refid=None, name=''):
        supermod.MemberType.__init__(self, kind, refid, name)
supermod.MemberType.subclass = MemberTypeSub
# end class MemberTypeSub


class ParseError(Exception):
    pass

class FileIOError(Exception):
    pass

def parse(inFilename):

    try:
        doc = minidom.parse(inFilename)
    except IOError, e:
        raise FileIOError(e)
    except ExpatError, e:
        raise ParseError(e)

    rootNode = doc.documentElement
    rootObj = supermod.DoxygenType.factory()
    rootObj.build(rootNode)

    return rootObj


########NEW FILE########
__FILENAME__ = indexsuper
#!/usr/bin/env python

#
# Generated Thu Jun 11 18:43:54 2009 by generateDS.py.
#

import sys
import getopt
from xml.dom import minidom
from xml.dom import Node

#
# User methods
#
# Calls to the methods in these classes are generated by generateDS.py.
# You can replace these methods by re-implementing the following class
#   in a module named generatedssuper.py.

try:
    from generatedssuper import GeneratedsSuper
except ImportError, exp:

    class GeneratedsSuper:
        def format_string(self, input_data, input_name=''):
            return input_data
        def format_integer(self, input_data, input_name=''):
            return '%d' % input_data
        def format_float(self, input_data, input_name=''):
            return '%f' % input_data
        def format_double(self, input_data, input_name=''):
            return '%e' % input_data
        def format_boolean(self, input_data, input_name=''):
            return '%s' % input_data


#
# If you have installed IPython you can uncomment and use the following.
# IPython is available from http://ipython.scipy.org/.
#

## from IPython.Shell import IPShellEmbed
## args = ''
## ipshell = IPShellEmbed(args,
##     banner = 'Dropping into IPython',
##     exit_msg = 'Leaving Interpreter, back to program.')

# Then use the following line where and when you want to drop into the
# IPython shell:
#    ipshell('<some message> -- Entering ipshell.\nHit Ctrl-D to exit')

#
# Globals
#

ExternalEncoding = 'ascii'

#
# Support/utility functions.
#

def showIndent(outfile, level):
    for idx in range(level):
        outfile.write('    ')

def quote_xml(inStr):
    s1 = (isinstance(inStr, basestring) and inStr or
          '%s' % inStr)
    s1 = s1.replace('&', '&amp;')
    s1 = s1.replace('<', '&lt;')
    s1 = s1.replace('>', '&gt;')
    return s1

def quote_attrib(inStr):
    s1 = (isinstance(inStr, basestring) and inStr or
          '%s' % inStr)
    s1 = s1.replace('&', '&amp;')
    s1 = s1.replace('<', '&lt;')
    s1 = s1.replace('>', '&gt;')
    if '"' in s1:
        if "'" in s1:
            s1 = '"%s"' % s1.replace('"', "&quot;")
        else:
            s1 = "'%s'" % s1
    else:
        s1 = '"%s"' % s1
    return s1

def quote_python(inStr):
    s1 = inStr
    if s1.find("'") == -1:
        if s1.find('\n') == -1:
            return "'%s'" % s1
        else:
            return "'''%s'''" % s1
    else:
        if s1.find('"') != -1:
            s1 = s1.replace('"', '\\"')
        if s1.find('\n') == -1:
            return '"%s"' % s1
        else:
            return '"""%s"""' % s1


class MixedContainer:
    # Constants for category:
    CategoryNone = 0
    CategoryText = 1
    CategorySimple = 2
    CategoryComplex = 3
    # Constants for content_type:
    TypeNone = 0
    TypeText = 1
    TypeString = 2
    TypeInteger = 3
    TypeFloat = 4
    TypeDecimal = 5
    TypeDouble = 6
    TypeBoolean = 7
    def __init__(self, category, content_type, name, value):
        self.category = category
        self.content_type = content_type
        self.name = name
        self.value = value
    def getCategory(self):
        return self.category
    def getContenttype(self, content_type):
        return self.content_type
    def getValue(self):
        return self.value
    def getName(self):
        return self.name


class _MemberSpec(object):
    def __init__(self, name='', data_type='', container=0):
        self.name = name
        self.data_type = data_type
        self.container = container
    def set_name(self, name): self.name = name
    def get_name(self): return self.name
    def set_data_type(self, data_type): self.data_type = data_type
    def get_data_type(self): return self.data_type
    def set_container(self, container): self.container = container
    def get_container(self): return self.container


#
# Data representation classes.
#

class DoxygenType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, version=None, compound=None):
        self.version = version
        if compound is None:
            self.compound = []
        else:
            self.compound = compound
    def factory(*args_, **kwargs_):
        if DoxygenType.subclass:
            return DoxygenType.subclass(*args_, **kwargs_)
        else:
            return DoxygenType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_compound(self): return self.compound
    def set_compound(self, compound): self.compound = compound
    def add_compound(self, value): self.compound.append(value)
    def insert_compound(self, index, value): self.compound[index] = value
    def get_version(self): return self.version
    def set_version(self, version): self.version = version
    def hasContent_(self):
        if (
            self.compound is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('version'):
            self.version = attrs.get('version').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'compound':
            obj_ = CompoundType.factory()
            obj_.build(child_)
            self.compound.append(obj_)
# end class DoxygenType


class CompoundType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, refid=None, name=None, member=None):
        self.kind = kind
        self.refid = refid
        self.name = name
        if member is None:
            self.member = []
        else:
            self.member = member
    def factory(*args_, **kwargs_):
        if CompoundType.subclass:
            return CompoundType.subclass(*args_, **kwargs_)
        else:
            return CompoundType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_member(self): return self.member
    def set_member(self, member): self.member = member
    def add_member(self, value): self.member.append(value)
    def insert_member(self, index, value): self.member[index] = value
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'name':
            name_ = ''
            for text__content_ in child_.childNodes:
                name_ += text__content_.nodeValue
            self.name = name_
        elif child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'member':
            obj_ = MemberType.factory()
            obj_.build(child_)
            self.member.append(obj_)
# end class CompoundType


class MemberType(GeneratedsSuper):
    subclass = None
    superclass = None
    def __init__(self, kind=None, refid=None, name=None):
        self.kind = kind
        self.refid = refid
        self.name = name
    def factory(*args_, **kwargs_):
        if MemberType.subclass:
            return MemberType.subclass(*args_, **kwargs_)
        else:
            return MemberType(*args_, **kwargs_)
    factory = staticmethod(factory)
    def get_name(self): return self.name
    def set_name(self, name): self.name = name
    def get_kind(self): return self.kind
    def set_kind(self, kind): self.kind = kind
    def get_refid(self): return self.refid
    def set_refid(self, refid): self.refid = refid
    def hasContent_(self):
        if (
            self.name is not None
            ):
            return True
        else:
            return False
    def build(self, node_):
        attrs = node_.attributes
        self.buildAttributes(attrs)
        for child_ in node_.childNodes:
            nodeName_ = child_.nodeName.split(':')[-1]
            self.buildChildren(child_, nodeName_)
    def buildAttributes(self, attrs):
        if attrs.get('kind'):
            self.kind = attrs.get('kind').value
        if attrs.get('refid'):
            self.refid = attrs.get('refid').value
    def buildChildren(self, child_, nodeName_):
        if child_.nodeType == Node.ELEMENT_NODE and \
            nodeName_ == 'name':
            name_ = ''
            for text__content_ in child_.childNodes:
                name_ += text__content_.nodeValue
            self.name = name_
# end class MemberType


USAGE_TEXT = """
Usage: python <Parser>.py [ -s ] <in_xml_file>
Options:
    -s        Use the SAX parser, not the minidom parser.
"""

def usage():
    print USAGE_TEXT
    sys.exit(1)


def parse(inFileName):
    doc = minidom.parse(inFileName)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('<?xml version="1.0" ?>\n')
    rootObj.export(sys.stdout, 0, name_="doxygenindex",
        namespacedef_='')
    return rootObj


def parseString(inString):
    doc = minidom.parseString(inString)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('<?xml version="1.0" ?>\n')
    rootObj.export(sys.stdout, 0, name_="doxygenindex",
        namespacedef_='')
    return rootObj


def parseLiteral(inFileName):
    doc = minidom.parse(inFileName)
    rootNode = doc.documentElement
    rootObj = DoxygenType.factory()
    rootObj.build(rootNode)
    # Enable Python to collect the space used by the DOM.
    doc = None
    sys.stdout.write('from index import *\n\n')
    sys.stdout.write('rootObj = doxygenindex(\n')
    rootObj.exportLiteral(sys.stdout, 0, name_="doxygenindex")
    sys.stdout.write(')\n')
    return rootObj


def main():
    args = sys.argv[1:]
    if len(args) == 1:
        parse(args[0])
    else:
        usage()




if __name__ == '__main__':
    main()
    #import pdb
    #pdb.run('main()')


########NEW FILE########
__FILENAME__ = process

AUTOCFG_TEMPLATE = r"""
PROJECT_NAME     = "{project_name}"
OUTPUT_DIRECTORY = {output_dir}
GENERATE_LATEX   = NO
GENERATE_MAN     = NO
GENERATE_RTF     = NO
CASE_SENSE_NAMES = NO
INPUT            = {input}
ENABLE_PREPROCESSING = YES
QUIET            = YES
JAVADOC_AUTOBRIEF = YES
JAVADOC_AUTOBRIEF = NO
GENERATE_HTML = NO
GENERATE_XML = YES
ALIASES = "rst=\verbatim embed:rst"
ALIASES += "endrst=\endverbatim"
""".strip()

class DoxygenProcessHandle(object):

    def __init__(self, path_handler, run_process, write_file):

        self.path_handler = path_handler
        self.run_process = run_process
        self.write_file = write_file

    def process(self, auto_project_info, files):

        name = auto_project_info.name()
        cfgfile = "%s.cfg" % name

        full_paths = map(lambda x: auto_project_info.abs_path_to_source_file(x), files)

        cfg = AUTOCFG_TEMPLATE.format(
                project_name=name,
                output_dir=name,
                input=" ".join(full_paths)
                )

        build_dir = self.path_handler.join(
                auto_project_info.build_dir(),
                "breathe",
                "doxygen"
                )

        self.write_file(build_dir, cfgfile, cfg)

        self.run_process(['doxygen', cfgfile], cwd=build_dir)

        return self.path_handler.join(build_dir, name, "xml")


########NEW FILE########
__FILENAME__ = base

class Renderer(object):

    def __init__(self,
            project_info,
            data_object,
            renderer_factory,
            node_factory,
            state,
            document,
            domain_handler,
            target_handler
            ):

        self.project_info = project_info
        self.data_object = data_object
        self.renderer_factory = renderer_factory
        self.node_factory = node_factory
        self.state = state
        self.document = document
        self.domain_handler = domain_handler
        self.target_handler = target_handler



########NEW FILE########
__FILENAME__ = compound

from .base import Renderer
from .index import render_compound

class DoxygenTypeSubRenderer(Renderer):

    def render(self):

        compound_renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.compounddef)
        return compound_renderer.render()


class CompoundDefTypeSubRenderer(Renderer):

    # We store both the identified and appropriate title text here as we want to define the order
    # here and the titles for the SectionDefTypeSubRenderer but we don't want the repetition of
    # having two lists in case they fall out of sync
    sections = [
                ("user-defined", "User Defined"),
                ("public-type", "Public Type"),
                ("public-func", "Public Functions"),
                ("public-attrib", "Public Members"),
                ("public-slot", "Public Slot"),
                ("signal", "Signal"),
                ("dcop-func",  "DCOP Function"),
                ("property",  "Property"),
                ("event",  "Event"),
                ("public-static-func", "Public Static Functions"),
                ("public-static-attrib", "Public Static Attributes"),
                ("protected-type",  "Protected Types"),
                ("protected-func",  "Protected Functions"),
                ("protected-attrib",  "Protected Attributes"),
                ("protected-slot",  "Protected Slots"),
                ("protected-static-func",  "Protected Static Functions"),
                ("protected-static-attrib",  "Protected Static Attributes"),
                ("package-type",  "Package Types"),
                ("package-func", "Package Functions"),
                ("package-attrib", "Package Attributes"),
                ("package-static-func", "Package Static Functions"),
                ("package-static-attrib", "Package Static Attributes"),
                ("private-type", "Private Types"),
                ("private-func", "Private Functions"),
                ("private-attrib", "Private Members"),
                ("private-slot",  "Private Slots"),
                ("private-static-func", "Private Static Functions"),
                ("private-static-attrib",  "Private Static Attributes"),
                ("friend",  "Friends"),
                ("related",  "Related"),
                ("define",  "Defines"),
                ("prototype",  "Prototypes"),
                ("typedef",  "Typedefs"),
                ("enum",  "Enums"),
                ("func",  "Functions"),
                ("var",  "Variables"),
                ]

    def render(self):

        nodelist = []    

        if self.data_object.briefdescription:
            renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.briefdescription)
            nodelist.extend(renderer.render())

        if self.data_object.detaileddescription:
            renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.detaileddescription)
            nodelist.extend(renderer.render())

        section_nodelists = {}

        # Get all sub sections
        for sectiondef in self.data_object.sectiondef:
            kind = sectiondef.kind
            node = self.node_factory.desc()
            node.document = self.state.document
            node['objtype'] = kind
            renderer = self.renderer_factory.create_renderer(self.data_object, sectiondef)
            node.extend(renderer.render())
            try:
                # As "user-defined" can repeat
                section_nodelists[kind] += [node]
            except KeyError:
                section_nodelists[kind] = [node]

        # Order the results in an appropriate manner
        for kind, _ in self.sections:
            nodelist.extend(section_nodelists.get(kind, []))

        # Take care of innerclasses
        for innerclass in self.data_object.innerclass:
            renderer = self.renderer_factory.create_renderer(self.data_object, innerclass)
            nodelist.extend(renderer.render())

        for innernamespace in self.data_object.innernamespace:
            renderer = self.renderer_factory.create_renderer(self.data_object, innernamespace)
            nodelist.extend(renderer.render())

        return nodelist


class SectionDefTypeSubRenderer(Renderer):

    section_titles = dict(CompoundDefTypeSubRenderer.sections)

    def render(self):

        node_list = []

        if self.data_object.description:
            renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.description)
            node_list.extend(renderer.render())

        # Get all the memberdef info
        for memberdef in self.data_object.memberdef:
            renderer = self.renderer_factory.create_renderer(self.data_object, memberdef)
            node_list.extend(renderer.render())

        if node_list:

            contentnode = self.node_factory.desc_content()
            contentnode.extend(node_list)

            text = self.section_titles[self.data_object.kind]

            # Override default name for user-defined sections. Use "Unnamed
            # Group" if the user didn't name the section
            # This is different to Doxygen which will track the groups and name
            # them Group1, Group2, Group3, etc.
            if self.data_object.kind == "user-defined":
                if self.data_object.header:
                    text = self.data_object.header
                else:
                    text = "Unnamed Group"
            title = self.node_factory.emphasis(text=text)

            signode = self.node_factory.desc_signature()
            signode.append(title)

            return [signode, contentnode]

        return []


class MemberDefTypeSubRenderer(Renderer):

    def create_doxygen_target(self):
        """Can be overridden to create a target node which uses the doxygen refid information
        which can be used for creating links between internal doxygen elements.

        The default implementation should suffice most of the time.
        """

        refid = "%s%s" % (self.project_info.name(), self.data_object.id)
        return self.target_handler.create_target(refid)

    def create_domain_target(self):
        """Should be overridden to create a target node which uses the Sphinx domain information so
        that it can be linked to from Sphinx domain roles like cpp:func:`myFunc`

        Returns a list so that if there is no domain active then we simply return an empty list
        instead of some kind of special null node value"""

        return []

    def title(self):

        nodes = []

        # Variable type or function return type
        if self.data_object.type_:
            renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.type_)
            nodes.extend(renderer.render())

        if nodes: nodes.append(self.node_factory.Text(" "))
        nodes.append(self.node_factory.desc_name(text=self.data_object.name))

        return nodes

    def description(self):

        nodes = []

        if self.data_object.briefdescription:
            renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.briefdescription)
            nodes.extend(renderer.render())

        if self.data_object.detaileddescription:
            renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.detaileddescription)
            nodes.extend(renderer.render())

        return nodes


    def render(self):

        # Build targets for linking
        signode = self.node_factory.desc_signature()
        signode.extend(self.create_domain_target())
        signode.extend(self.create_doxygen_target())

        # Build title nodes
        signode.extend(self.title())

        # Build description nodes
        contentnode = self.node_factory.desc_content()
        contentnode.extend(self.description())

        node = self.node_factory.desc()
        node.document = self.state.document
        node['objtype'] = self.data_object.kind
        node.append(signode)
        node.append(contentnode)

        return [node]


class FuncMemberDefTypeSubRenderer(MemberDefTypeSubRenderer):

    def create_domain_target(self):

        return self.domain_handler.create_function_target(self.data_object)

    def title(self):

        nodes = []

        # Handle any template information
        if self.data_object.templateparamlist:
            renderer = self.renderer_factory.create_renderer(
                    self.data_object,
                    self.data_object.templateparamlist
                    )
            template_nodes = []
            template_nodes.append(self.node_factory.Text("template <"))
            template_nodes.extend(renderer.render())
            template_nodes.append(self.node_factory.Text("> "))
            nodes.append(self.node_factory.line("", *template_nodes))

        # Get the function type and name
        nodes.extend(MemberDefTypeSubRenderer.title(self))

        # Get the function arguments
        paramlist = self.node_factory.desc_parameterlist()
        for i, parameter in enumerate(self.data_object.param):
            param = self.node_factory.desc_parameter('', '', noemph=True)
            renderer = self.renderer_factory.create_renderer(self.data_object, parameter)
            param.extend(renderer.render())
            paramlist.append(param)
        nodes.append(paramlist)

        return nodes


class DefineMemberDefTypeSubRenderer(MemberDefTypeSubRenderer):

    def title(self):

        title = []

        title.append(self.node_factory.strong(text=self.data_object.name))

        if self.data_object.param:
            title.append(self.node_factory.Text("("))
            for i, parameter in enumerate(self.data_object.param):
                if i: title.append(self.node_factory.Text(", "))
                renderer = self.renderer_factory.create_renderer(self.data_object, parameter)
                title.extend(renderer.render())
            title.append(self.node_factory.Text(")"))

        return title

    def description(self):

        return MemberDefTypeSubRenderer.description(self)


class EnumMemberDefTypeSubRenderer(MemberDefTypeSubRenderer):

    def title(self):

        if self.data_object.name.startswith("@"):
            # Assume anonymous enum
            return [self.node_factory.strong(text="Anonymous enum")]

        name = self.node_factory.strong(text="%s enum" % self.data_object.name)
        return [name]

    def description(self):

        description_nodes = MemberDefTypeSubRenderer.description(self)

        name = self.node_factory.emphasis("", self.node_factory.Text("Values:"))
        title = self.node_factory.paragraph("", "", name)
        description_nodes.append(title)

        enums = []
        for item in self.data_object.enumvalue:
            renderer = self.renderer_factory.create_renderer(self.data_object, item)
            enums.extend(renderer.render())

        description_nodes.append(self.node_factory.bullet_list("", classes=["breatheenumvalues"], *enums))

        return description_nodes


class TypedefMemberDefTypeSubRenderer(MemberDefTypeSubRenderer):

    def title(self):

        args = [self.node_factory.Text("typedef ")]
        args.extend(MemberDefTypeSubRenderer.title(self))

        if self.data_object.argsstring:
            renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.argsstring)
            args.extend(renderer.render())

        return args


class VariableMemberDefTypeSubRenderer(MemberDefTypeSubRenderer):

    def title(self):

        args = MemberDefTypeSubRenderer.title(self)

        if self.data_object.argsstring:
            renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.argsstring)
            args.extend(renderer.render())

        return args


class EnumvalueTypeSubRenderer(Renderer):

    def render(self):

        name = self.node_factory.literal(text=self.data_object.name)
        description_nodes = [name]

        if self.data_object.initializer:
            renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.initializer)
            nodelist = [self.node_factory.Text(" = ")]
            nodelist.extend(renderer.render())
            description_nodes.append(self.node_factory.literal("", "", *nodelist))

        separator = self.node_factory.Text(" - ")
        description_nodes.append(separator)

        if self.data_object.briefdescription:
            renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.briefdescription)
            description_nodes.extend(renderer.render())

        if self.data_object.detaileddescription:
            renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.detaileddescription)
            description_nodes.extend(renderer.render())

        # Build the list item
        return [self.node_factory.list_item("", *description_nodes)]

class DescriptionTypeSubRenderer(Renderer):

    def render(self):

        nodelist = []
        
        # Get description in rst_nodes if possible
        for item in self.data_object.content_:
            renderer = self.renderer_factory.create_renderer(self.data_object, item)
            nodelist.extend(renderer.render())

        return nodelist


class LinkedTextTypeSubRenderer(Renderer):

    def render(self):

        nodelist = []

        # Recursively process where possible
        for i, entry in enumerate(self.data_object.content_):
            if i:
                nodelist.append(self.node_factory.Text(" "))
            renderer = self.renderer_factory.create_renderer(self.data_object, entry)
            nodelist.extend(renderer.render())

        return nodelist


class ParamTypeSubRenderer(Renderer):

    def __init__(
            self,
            output_defname,
            *args
            ):

        Renderer.__init__( self, *args )

        self.output_defname = output_defname

    def render(self):

        nodelist = []

        # Parameter type
        if self.data_object.type_:
            renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.type_)
            nodelist.extend(renderer.render())

        # Parameter name
        if self.data_object.declname:
            if nodelist: nodelist.append(self.node_factory.Text(" "))
            nodelist.append(self.node_factory.emphasis(text=self.data_object.declname))

        if self.output_defname and self.data_object.defname:
            if nodelist: nodelist.append(self.node_factory.Text(" "))
            nodelist.append(self.node_factory.Text(self.data_object.defname))

        # Default value
        if self.data_object.defval:
            nodelist.append(self.node_factory.Text(" = "))
            renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.defval)
            nodelist.extend(renderer.render())

        return nodelist



class DocRefTextTypeSubRenderer(Renderer):

    def render(self):

        nodelist = []

        for item in self.data_object.content_:
            renderer = self.renderer_factory.create_renderer(self.data_object, item)
            nodelist.extend(renderer.render())

        for item in self.data_object.para:
            renderer = self.renderer_factory.create_renderer(self.data_object, item)
            nodelist.extend(renderer.render())

        refid = "%s%s" % (self.project_info.name(), self.data_object.refid)
        nodelist = [
                self.node_factory.pending_xref(
                    "",
                    reftype="ref",
                    refdomain="std",
                    refexplicit=True,
                    refid=refid, 
                    reftarget=refid,
                    *nodelist
                    )
                ]

        return nodelist


class DocParaTypeSubRenderer(Renderer):
    """
    <para> tags in the Doxygen output tend to contain either text or a single other tag of interest.
    So whilst it looks like we're combined descriptions and program listings and other things, in
    the end we generally only deal with one per para tag. Multiple neighbouring instances of these
    things tend to each be in a separate neighbouring para tag.
    """

    def render(self):

        nodelist = []
        for item in self.data_object.content:              # Description
            renderer = self.renderer_factory.create_renderer(self.data_object, item)
            nodelist.extend(renderer.render())

        for item in self.data_object.programlisting:       # Program listings
            renderer = self.renderer_factory.create_renderer(self.data_object, item)
            nodelist.extend(renderer.render())

        for item in self.data_object.images:               # Images
            renderer = self.renderer_factory.create_renderer(self.data_object, item)
            nodelist.extend(renderer.render())

        definition_nodes = []
        for item in self.data_object.simplesects:          # Returns, user par's, etc
            renderer = self.renderer_factory.create_renderer(self.data_object, item)
            definition_nodes.extend(renderer.render())

        for entry in self.data_object.parameterlist:       # Parameters/Exceptions
            renderer = self.renderer_factory.create_renderer(self.data_object, entry)
            definition_nodes.extend(renderer.render())

        if definition_nodes:
            definition_list = self.node_factory.definition_list("", *definition_nodes)
            nodelist.append(definition_list)

        return [self.node_factory.paragraph("", "", *nodelist)]


class DocImageTypeSubRenderer(Renderer):
    "Output docutils image node using name attribute from xml as the uri"

    def render(self):

        path_to_image = self.project_info.sphinx_abs_path_to_file(
                self.data_object.name
                )

        options = { "uri" : path_to_image }

        return [self.node_factory.image("", **options)]

class DocMarkupTypeSubRenderer(Renderer):

    def __init__(
            self,
            creator,
            *args
            ):

        Renderer.__init__( self, *args )

        self.creator = creator

    def render(self):

        nodelist = []

        for item in self.data_object.content_:
            renderer = self.renderer_factory.create_renderer(self.data_object, item)
            nodelist.extend(renderer.render())

        return [self.creator("", "", *nodelist)]


class DocParamListTypeSubRenderer(Renderer):
    "Parameter/Exception documentation"

    lookup = {
            "param" : "Parameters",
            "exception" : "Exceptions",
            "templateparam" : "Templates",
            "retval" : "Return Value",
            }

    def render(self):

        nodelist = []
        for entry in self.data_object.parameteritem:
            renderer = self.renderer_factory.create_renderer(self.data_object, entry)
            nodelist.extend(renderer.render())

        # Fild list entry
        nodelist_list = self.node_factory.bullet_list("", classes=["breatheparameterlist"], *nodelist)

        term_text = self.lookup[self.data_object.kind]
        term = self.node_factory.term("", "", self.node_factory.strong( "", term_text ) )
        definition = self.node_factory.definition('', nodelist_list)

        return [self.node_factory.definition_list_item('', term, definition)]



class DocParamListItemSubRenderer(Renderer):
    """ Paramter Description Renderer  """

    def render(self):

        nodelist = []
        for entry in self.data_object.parameternamelist:
            renderer = self.renderer_factory.create_renderer(self.data_object, entry)
            nodelist.extend(renderer.render())

        term = self.node_factory.literal("","", *nodelist)

        separator = self.node_factory.Text(" - ")

        nodelist = []

        if self.data_object.parameterdescription:
            renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.parameterdescription)
            nodelist.extend(renderer.render())

        return [self.node_factory.list_item("", term, separator, *nodelist)]

class DocParamNameListSubRenderer(Renderer):
    """ Parameter Name Renderer """

    def render(self):

        nodelist = []
        for entry in self.data_object.parametername:
            renderer = self.renderer_factory.create_renderer(self.data_object, entry)
            nodelist.extend(renderer.render())

        return nodelist

class DocParamNameSubRenderer(Renderer):

    def render(self):

        nodelist = []
        for item in self.data_object.content_:
            renderer = self.renderer_factory.create_renderer(self.data_object, item)
            nodelist.extend(renderer.render())

        return nodelist

class DocSect1TypeSubRenderer(Renderer):

    def render(self):

        return []


class DocSimpleSectTypeSubRenderer(Renderer):
    "Other Type documentation such as Warning, Note, Returns, etc"

    def title(self):

        text = self.node_factory.Text(self.data_object.kind.capitalize())

        return [self.node_factory.strong( "", text )]

    def render(self):

        nodelist = []
        for item in self.data_object.para:
            renderer = self.renderer_factory.create_renderer(self.data_object, item)
            nodelist.append(self.node_factory.paragraph("", "", *renderer.render()))

        term = self.node_factory.term("", "", *self.title())
        definition = self.node_factory.definition("", *nodelist)

        return [self.node_factory.definition_list_item("", term, definition)]


class ParDocSimpleSectTypeSubRenderer(DocSimpleSectTypeSubRenderer):

    def title(self):

        renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.title)

        return [self.node_factory.strong( "", *renderer.render() )]


class DocTitleTypeSubRenderer(Renderer):

    def render(self):

        nodelist = []

        for item in self.data_object.content_:
            renderer = self.renderer_factory.create_renderer(self.data_object, item)
            nodelist.extend(renderer.render())

        return nodelist


class DocForumlaTypeSubRenderer(Renderer):

    def render(self):

        nodelist = []

        for item in self.data_object.content_:

            latex = item.getValue()

            # Somewhat hacky if statements to strip out the doxygen markup that slips through

            node = None

            # Either inline
            if latex.startswith("$") and latex.endswith("$"):
                latex = latex[1:-1]

                # If we're inline create a math node like the :math: role
                node = self.node_factory.math()
            else:
                # Else we're multiline
                node = self.node_factory.displaymath()

            # Or multiline
            if latex.startswith("\[") and latex.endswith("\]"):
                latex = latex[2:-2:]

            # Here we steal the core of the mathbase "math" directive handling code from:
            #    sphinx.ext.mathbase
            node["latex"] = latex

            # Required parameters which we don't have values for
            node["label"] = None
            node["nowrap"] = False
            node["docname"] = self.state.document.settings.env.docname

            nodelist.append(node)

        return nodelist


class ListingTypeSubRenderer(Renderer):

    def render(self):

        lines = []
        nodelist = []
        for i, entry in enumerate(self.data_object.codeline):
            # Put new lines between the lines. There must be a more pythonic way of doing this
            if i:
                nodelist.append(self.node_factory.Text("\n"))
            renderer = self.renderer_factory.create_renderer(self.data_object, entry)
            nodelist.extend(renderer.render())

        # Add blank string at the start otherwise for some reason it renders
        # the pending_xref tags around the kind in plain text
        block = self.node_factory.literal_block(
                "",
                "",
                *nodelist
                )

        return [block]

class CodeLineTypeSubRenderer(Renderer):

    def render(self):

        nodelist = []
        for entry in self.data_object.highlight:
            renderer = self.renderer_factory.create_renderer(self.data_object, entry)
            nodelist.extend(renderer.render())

        return nodelist

class HighlightTypeSubRenderer(Renderer):

    def render(self):

        nodelist = []
        for entry in self.data_object.content_:
            renderer = self.renderer_factory.create_renderer(self.data_object, entry)
            nodelist.extend(renderer.render())

        return nodelist

class TemplateParamListRenderer(Renderer):

    def render(self):

        nodelist = []

        for i, param in enumerate(self.data_object.param):
            if i:
                nodelist.append(self.node_factory.Text(", "))
            renderer = self.renderer_factory.create_renderer(self.data_object, param)
            nodelist.extend(renderer.render())

        return nodelist

class IncTypeSubRenderer(Renderer):

    def render(self):

        if self.data_object.local == u"yes":
            text = '#include "%s"' % self.data_object.content_[0].getValue()
        else:
            text = '#include <%s>' % self.data_object.content_[0].getValue()

        return [self.node_factory.emphasis(text=text)]

class RefTypeSubRenderer(Renderer):

    def __init__(self, compound_parser, *args):
        Renderer.__init__(self, *args)

        self.compound_parser = compound_parser

    def render(self):

        # Read in the corresponding xml file and process
        file_data = self.compound_parser.parse(self.data_object.refid)

        data_renderer = self.renderer_factory.create_renderer(self.data_object, file_data)
        child_nodes = data_renderer.render()

        if not child_nodes:
            return []

        refid = "%s%s" % (self.project_info.name(), self.data_object.refid)

        name = self.data_object.content_[0].getValue()
        name = name.rsplit("::", 1)[-1]

        # Defer to function for details
        return render_compound(
                name,
                file_data.compounddef.kind,
                file_data,
                child_nodes,
                self.renderer_factory,
                self.node_factory,
                [], # No domain reference
                self.target_handler.create_target(refid),
                self.state.document
                )


class VerbatimTypeSubRenderer(Renderer):

    def __init__(self, content_creator, *args):
        Renderer.__init__(self, *args)

        self.content_creator = content_creator

    def render(self):

        if not self.data_object.text.strip().startswith("embed:rst"):

            # Remove trailing new lines. Purely subjective call from viewing results
            text = self.data_object.text.rstrip()

            # Handle has a preformatted text
            return [self.node_factory.literal_block(text, text)]

        # do we need to strip leading asterisks?
        # NOTE: We could choose to guess this based on every line starting with '*'.
        #   However This would have a side-effect for any users who have an rst-block
        #   consisting of a simple bullet list.
        #   For now we just look for an extended embed tag
        if self.data_object.text.strip().startswith("embed:rst:leading-asterisk"):

            lines = self.data_object.text.splitlines()
            # Replace the first * on each line with a blank space
            lines = map( lambda text: text.replace( "*", " ", 1 ), lines )
            self.data_object.text = "\n".join( lines )

        rst = self.content_creator(self.data_object.text)

        # Parent node for the generated node subtree
        node = self.node_factory.paragraph()
        node.document = self.state.document

        # Generate node subtree
        self.state.nested_parse(rst, 0, node)

        return node


class MixedContainerRenderer(Renderer):

    def render(self):

        renderer = self.renderer_factory.create_renderer(self.data_object, self.data_object.getValue())
        return renderer.render()


class DocListNestedRenderer(object):
    """
        Decorator for the list type renderer.

        Creates the proper docutils node based on the sub-type
        of the underlying data object. Takes care of proper numbering
        for deeply nested enumerated lists.
    """

    numeral_kind = ['arabic', 'loweralpha', 'lowerroman', 'upperalpha', 'upperroman']

    def __init__(self, f):
        self.__render = f
        self.__nesting_level = 0

    def __get__(self, obj, objtype):
        """ Support instance methods. """
        import functools
        return functools.partial(self.__call__, obj)

    def __call__(self, rend_self):
        """ Call the wrapped render function. Update the nesting level for the enumerated lists. """
        rend_instance = rend_self
        if rend_instance.data_object.node_subtype is "itemized":
            val = self.__render(rend_instance)
            return DocListNestedRenderer.render_unordered(rend_instance, children=val)
        elif rend_instance.data_object.node_subtype is "ordered":
            self.__nesting_level += 1
            val = self.__render(rend_instance)
            self.__nesting_level -= 1
            return DocListNestedRenderer.render_enumerated(rend_instance, children=val,
                                                           nesting_level=self.__nesting_level)

        return []

    @staticmethod
    def render_unordered(renderer, children):
        nodelist_list = renderer.node_factory.bullet_list("", *children)

        return [nodelist_list]

    @staticmethod
    def render_enumerated(renderer, children, nesting_level):
        nodelist_list = renderer.node_factory.enumerated_list("", *children)
        idx = nesting_level % len(DocListNestedRenderer.numeral_kind)
        nodelist_list['enumtype'] = DocListNestedRenderer.numeral_kind[idx]
        nodelist_list['prefix'] = ''
        nodelist_list['suffix'] = '.'

        return [nodelist_list]


class DocListTypeSubRenderer(Renderer):
    """
        List renderer.
        The specifics of the actual list rendering are handled by the
        decorator around the generic render function.
    """

    @DocListNestedRenderer
    def render(self):
        """ Render all the children depth-first. """
        nodelist = []
        for entry in self.data_object.listitem:
            renderer = self.renderer_factory.create_renderer(self.data_object, entry)
            nodelist.extend(renderer.render())

        return nodelist


class DocListItemTypeSubRenderer(Renderer):
    """
        List item renderer.
    """

    def render(self):
        """ Render all the children depth-first.
            Upon return expand the children node list into a docutils list-item.
        """
        nodelist = []
        for entry in self.data_object.para:
            renderer = self.renderer_factory.create_renderer(self.data_object, entry)
            nodelist.extend(renderer.render())

        return [self.node_factory.list_item("", *nodelist)]

########NEW FILE########
__FILENAME__ = domain


class DomainHelper(object):
    pass

class NullDomainHelper(DomainHelper):
    pass

class CppDomainHelper(DomainHelper):

    def __init__(self, definition_parser, substitute):

        self.definition_parser = definition_parser
        self.substitute = substitute

        self.duplicates = {}

    def check_cache(self, _id):
        try:
            return True, self.duplicates[_id]
        except KeyError:
            return False, ""

    def cache(self, _id, project_info):
        self.duplicates[_id] = project_info

    def remove_word(self, word, definition):
        return self.substitute(r"(\s*\b|^)%s\b\s*" % word, "", definition)


class CDomainHelper(DomainHelper):

    def __init__(self):

        self.duplicates = set()

    def is_duplicate(self, name):
        return name in self.duplicates

    def remember(self, name):
        self.duplicates.add(name)



class DomainHandler(object):

    def __init__(self, node_factory, document, env, helper, project_info, target_handler):

        self.node_factory = node_factory
        self.document = document
        self.env = env
        self.helper = helper
        self.project_info = project_info
        self.target_handler = target_handler

class NullDomainHandler(DomainHandler):

    def __init__(self):
        pass

    def create_function_id(self, data_object):
        return ""

    def create_function_target(self, data_object):
        return []

    def create_class_id(self, data_object):
        return ""

    def create_class_target(self, data_object):
        return []

class CDomainHandler(DomainHandler):

    def create_function_id(self, data_object):

        name = data_object.definition.split()[-1]

        return name

    def create_function_target(self, data_object):

        name = data_object.definition.split()[-1]

        return self._create_target(name, "function")

    def _create_target(self, name, type_):

        if self.helper.is_duplicate(name):
            print ( "Warning: Ignoring duplicate '%s'. As C does not support overloaded "
                    "functions. Perhaps you should be using the cpp domain?" % name )
            return

        self.helper.remember(name)

        # Create target node. This is required for LaTeX output as target nodes are converted to the
        # appropriate \phantomsection & \label for in document LaTeX links
        (target,) = self.target_handler.create_target(name)

        inv = self.env.domaindata['c']['objects']
        if name in inv:
            self.env.warn(
                self.env.docname,
                'duplicate C object description of %s, ' % name +
                'other instance in ' + self.env.doc2path(inv[name][0]),
                self.lineno)
        inv[name] = (self.env.docname, "function")

        return [target]


class CppDomainHandler(DomainHandler):

    def create_class_id(self, data_object):

        def_ = data_object.name

        parser = self.helper.definition_parser(def_)
        sigobj = parser.parse_class()

        return sigobj.get_id()

    def create_class_target(self, data_object):

        id_ = self.create_class_id(data_object)
        name = data_object.name

        return self._create_target(name, "class", id_)

    def create_function_id(self, data_object):

        definition = self.helper.remove_word("virtual", data_object.definition)
        argstring = data_object.argsstring

        explicit = "explicit " if data_object.explicit == "yes" else ""

        def_ = "%(explicit)s%(definition)s%(argstring)s" % {
                        "explicit" : explicit,
                        "definition" : definition,
                        "argstring" : argstring,
                    }

        parser = self.helper.definition_parser(def_)
        sigobj = parser.parse_function()

        return sigobj.get_id()

    def create_function_target(self, data_object):

        id_ = self.create_function_id(data_object)

        name = data_object.definition.split()[-1]

        return self._create_target(name, "function", id_)

    def _create_target(self, name, type_, id_):
        """Creates a target node and registers it with the appropriate domain
        object list in a style which matches Sphinx's behaviour for the domain
        directives like cpp:function"""

        # Check if we've already got this id
        in_cache, project = self.helper.check_cache(id_)
        if in_cache:
            print "Warning: Ignoring duplicate domain reference '%s'. " \
                  "First found in project '%s'" % (id_, project.reference())
            return []

        self.helper.cache(id_, self.project_info)

        # Create target node. This is required for LaTeX output as target nodes are converted to the
        # appropriate \phantomsection & \label for in document LaTeX links
        (target,) = self.target_handler.create_target(id_)

        # Register object with the sphinx objects registry
        self.document.settings.env.domaindata['cpp']['objects'].setdefault(name,
                (self.document.settings.env.docname, type_, id_))

        return [target]


class DomainHandlerFactory(object):

    def __init__(self, project_info, node_factory, document, env, target_handler, helpers):

        self.project_info = project_info
        self.node_factory = node_factory
        self.document = document
        self.env = env
        self.target_handler = target_handler
        self.domain_helpers = helpers

    def create_null_domain_handler(self):

        return NullDomainHandler()

    def create_domain_handler(self, file_):

        domains_handlers = {
                "c" : CDomainHandler,
                "cpp" : CppDomainHandler,
                }

        domain = self.project_info.domain_for_file(file_)

        try:
            helper = self.domain_helpers[domain]
        except KeyError:
            helper = NullDomainHelper()

        try:
            return domains_handlers[domain](self.node_factory, self.document, self.env, helper,
                    self.project_info, self.target_handler)
        except KeyError:
            return NullDomainHandler()

class NullDomainHandlerFactory(object):

    def create_null_domain_handler(self):

        return NullDomainHandler()

    def create_domain_handler(self, file_):

        return NullDomainHandler()

class DomainHandlerFactoryCreator(object):

    def __init__(self, node_factory, helpers):

        self.node_factory = node_factory
        self.helpers = helpers

    def create_domain_handler_factory(self, project_info, document, env, options, target_handler):

        if "no-link" in options:
            return NullDomainHandlerFactory()

        return DomainHandlerFactory(
                project_info,
                self.node_factory,
                document,
                env,
                target_handler,
                self.helpers
                )


########NEW FILE########
__FILENAME__ = filter

class Selecter(object):
    pass

class Parent(Selecter):

    def __call__(self, parent_data_object, child_data_object):
        return parent_data_object

class Child(Selecter):

    def __call__(self, parent_data_object, child_data_object):
        return child_data_object


class Accessor(object):

    def __init__(self, selecter):
        self.selecter = selecter

class NameAccessor(Accessor):

    def __call__(self, parent_data_object, child_data_object):
        return self.selecter(parent_data_object, child_data_object).name

class NodeNameAccessor(Accessor):
    """Check the .node_name member which is declared on refTypeSub nodes

    It distinguishes between innerclass, innernamespace, etc.
    """

    def __call__(self, parent_data_object, child_data_object):
        return self.selecter(parent_data_object, child_data_object).node_name

class NodeTypeAccessor(Accessor):

    def __call__(self, parent_data_object, child_data_object):

        data_object = self.selecter(parent_data_object, child_data_object)
        try:
            return data_object.node_type
        except AttributeError, e:

            # Horrible hack to silence errors on filtering unicode objects
            # until we fix the parsing
            if type(data_object) == unicode:
                return "unicode"
            else:
                raise e

class KindAccessor(Accessor):

    def __call__(self, parent_data_object, child_data_object):
        return self.selecter(parent_data_object, child_data_object).kind

class LambdaAccessor(Accessor):

    def __init__(self, selecter, func):
        Accessor.__init__(self, selecter)

        self.func = func

    def __call__(self, parent_data_object, child_data_object):
        return self.func(self.selecter(parent_data_object, child_data_object))

class NamespaceAccessor(Accessor):

    def __call__(self, parent_data_object, child_data_object):
        return self.selecter(parent_data_object, child_data_object).namespaces

class NameFilter(object):

    def __init__(self, accessor, members):

        self.accessor = accessor
        self.members = members

    def allow(self, parent_data_object, child_data_object):

        name = self.accessor(parent_data_object, child_data_object)

        return name in self.members

class GlobFilter(object):

    def __init__(self, accessor, glob):

        self.accessor = accessor
        self.glob = glob

    def allow(self, parent_data_object, child_data_object):

        text = self.accessor(parent_data_object, child_data_object)
        return self.glob.match(text)


class FilePathFilter(object):

    def __init__(self, accessor, target_file, path_handler):

        self.accessor = accessor
        self.target_file = target_file
        self.path_handler = path_handler

    def allow(self, parent_data_object, child_data_object):

        location = self.accessor(parent_data_object, child_data_object).file

        if self.path_handler.includes_directory(self.target_file):
            # If the target_file contains directory separators then
            # match against the same length at the ned of the location
            #
            location_match = location[-len(self.target_file):]
            return location_match == self.target_file

        else:
            # If there are not separators, match against the whole filename
            # at the end of the location
            # 
            # This is to prevent "Util.cpp" matching "PathUtil.cpp"
            #
            location_basename = self.path_handler.basename(location)
            return location_basename == self.target_file

class NamespaceFilter(object):

    def __init__(self, namespace_accessor, name_accessor):

        self.namespace_accessor = namespace_accessor
        self.name_accessor = name_accessor

    def allow(self, parent_data_object, child_data_object):

        namespaces = self.namespace_accessor(parent_data_object, child_data_object)
        name = self.name_accessor(parent_data_object, child_data_object)

        try:
            namespace, name = name.rsplit("::", 1)
        except ValueError:
            namespace, name = "", name

        return namespace in namespaces

class OpenFilter(object):

    def allow(self, parent_data_object, child_data_object):

        return True

class ClosedFilter(object):

    def allow(self, parent_data_object, child_data_object):

        return False

class NotFilter(object):

    def __init__(self, child_filter):
        self.child_filter = child_filter

    def allow(self, parent_data_object, child_data_object):

        return not self.child_filter.allow(parent_data_object, child_data_object)

class AndFilter(object):

    def __init__(self, first_filter, second_filter):

        self.first_filter = first_filter
        self.second_filter = second_filter

    def allow(self, parent_data_object, child_data_object):

        return self.first_filter.allow(parent_data_object, child_data_object) \
                and self.second_filter.allow(parent_data_object, child_data_object)

class OrFilter(object):
    "Provides a short-cutted 'or' operation between two filters"

    def __init__(self, first_filter, second_filter):

        self.first_filter = first_filter
        self.second_filter = second_filter

    def allow(self, parent_data_object, child_data_object):

        return self.first_filter.allow(parent_data_object, child_data_object) \
                or self.second_filter.allow(parent_data_object, child_data_object)

class Glob(object):

    def __init__(self, method, pattern):

        self.method = method
        self.pattern = pattern

    def match(self, name):

        return self.method(name, self.pattern)

class GlobFactory(object):

    def __init__(self, method):

        self.method = method

    def create(self, pattern):

        return Glob(self.method, pattern)

class Gather(object):

    def __init__(self, accessor, names):

        self.accessor = accessor
        self.names = names

    def allow(self, parent_data_object, child_data_object):

        self.names.extend( self.accessor(parent_data_object, child_data_object) )

        return False



class FilterFactory(object):

    def __init__(self, globber_factory, path_handler):

        self.globber_factory = globber_factory
        self.path_handler = path_handler

    def create_class_filter(self, options):

        return AndFilter(
                self.create_members_filter(options),
                AndFilter(
                    self.create_outline_filter(options),
                    self.create_show_filter(options),
                    )
                )

    def create_show_filter(self, options):
        """
        Currently only handles the header-file entry
        """

        try:
            text = options["show"]
        except KeyError:
            # Allow through everything except the header-file includes nodes
            return OrFilter(
                    NotFilter(NameFilter(NodeTypeAccessor(Parent()), ["compounddef"])),
                    NotFilter(NameFilter(NodeTypeAccessor(Child()), ["inc"]))
                    )

        if text == "header-file":
            # Allow through everything, including header-file includes
            return OpenFilter()

        # Allow through everything except the header-file includes nodes
        return OrFilter(
                NotFilter(NameFilter(NodeTypeAccessor(Parent()), ["compounddef"])),
                NotFilter(NameFilter(NodeTypeAccessor(Child()), ["inc"]))
                )


    def create_members_filter(self, options):

        section = options.get("sections", "")

        if not section.strip():
            section_filter = GlobFilter(KindAccessor(Child()), self.globber_factory.create("public*"))
        else:
            sections = set([x.strip() for x in section.split(",")])

            section_filter = GlobFilter(
                    KindAccessor(Child()),
                    self.globber_factory.create(sections.pop())
                    )
            while len(sections) > 0:
                section_filter = OrFilter(
                        section_filter,
                        GlobFilter(
                            KindAccessor(Child()),
                            self.globber_factory.create(sections.pop())
                            )
                        )

        if "members" not in options:
            return OrFilter(
                    NotFilter(NameFilter(NodeTypeAccessor(Parent()), ["sectiondef"])),
                    NotFilter(NameFilter(NodeTypeAccessor(Child()), ["memberdef"]))
                    )

        text = options["members"]
        if not text.strip():
            return OrFilter(
                    NotFilter(NameFilter(NodeTypeAccessor(Child()), ["sectiondef"])),
                    OrFilter(
                        section_filter,
                        NameFilter(KindAccessor(Child()), ["user-defined"])
                        )
                    )

        # Matches sphinx-autodoc behaviour of comma separated values
        members = set([x.strip() for x in text.split(",")])

        # Accept any nodes which don't have a "sectiondef" as a parent or, if they do, only accept
        # them if their names are in the members list or they are of type description. This accounts
        # for the actual description of the sectiondef
        return OrFilter(
                NotFilter(NameFilter(NodeTypeAccessor(Parent()),["sectiondef"])),
                OrFilter(
                    NameFilter(NodeTypeAccessor(Child()), ["description"]),
                    NameFilter(NameAccessor(Child()), members),
                    )
                )

    def create_outline_filter(self, options):

        if options.has_key("outline"):
            return NotFilter(NameFilter(NodeTypeAccessor(Child()), ["description"]))
        else:
            return OpenFilter()

    def create_file_filter(self, filename, options):

        valid_names = []

        filter_ = AndFilter(
                AndFilter(
                    AndFilter(
                        NotFilter(
                            # Gather the "namespaces" attribute from the
                            # compounddef for the file we're rendering and
                            # store the information in the "valid_names" list
                            #
                            # Gather always returns false, so, combined with
                            # the NotFilter this chunk always returns true and
                            # so does not affect the result of the filtering
                            AndFilter(
                                AndFilter(
                                    AndFilter(
                                        NameFilter(NodeTypeAccessor(Child()), ["compounddef"]),
                                        NameFilter(KindAccessor(Child()), ["file"])
                                    ),
                                    FilePathFilter(
                                        LambdaAccessor(Child(), lambda x: x.location), filename, self.path_handler
                                        )
                                    ),
                                Gather(LambdaAccessor(Child(), lambda x: x.namespaces), valid_names)
                                )
                            ),
                        NotFilter(
                            # Take the valid_names and everytime we handle an
                            # innerclass or innernamespace, check that its name
                            # was one of those initial valid names so that we
                            # never end up rendering a namespace or class that
                            # wasn't in the initial file. Notably this is
                            # required as the location attribute for the
                            # namespace in the xml is unreliable.
                            AndFilter(
                                NameFilter(NodeTypeAccessor(Parent()), ["compounddef"]),
                                AndFilter(
                                    AndFilter(
                                        NameFilter(NodeTypeAccessor(Child()),["ref"]),
                                        NameFilter(NodeNameAccessor(Child()),["innerclass", "innernamespace"])
                                        ),
                                    NotFilter(NameFilter(
                                        LambdaAccessor(Child(), lambda x: x.content_[0].getValue()),
                                        valid_names
                                        ))
                                    )
                                )
                            )
                        ),
                 NotFilter(
                     # Ignore innerclasses and innernamespaces that are inside a
                     # namespace that is going to be rendered as they will be
                     # rendered with that namespace and we don't want them twice
                     AndFilter(
                         NameFilter(NodeTypeAccessor(Parent()), ["compounddef"]),
                         AndFilter(
                             AndFilter(
                                 NameFilter(NodeTypeAccessor(Child()),["ref"]),
                                 NameFilter(NodeNameAccessor(Child()),["innerclass", "innernamespace"])
                                 ),
                             NamespaceFilter(
                                 NamespaceAccessor(Parent()),
                                 LambdaAccessor(Child(), lambda x: x.content_[0].getValue())
                                 )
                             )
                         )
                     ),
                ),
                AndFilter(
                    NotFilter(
                        # Ignore memberdefs from files which are different to
                        # the one we're rendering. This happens when we have to
                        # cross into a namespace xml file which has entries
                        # from multiple files in it
                        AndFilter(
                            NameFilter(NodeTypeAccessor(Child()), ["memberdef"]),
                            NotFilter(
                                FilePathFilter(LambdaAccessor(Child(), lambda x: x.location), filename, self.path_handler)
                                )
                            )
                        ),
                    NotFilter(
                        # Ignore compounddefs which are from another file
                        # (normally means classes and structs which are in a
                        # namespace that we have other interests in) but only
                        # check it if the compounddef is not a namespace
                        # itself, as for some reason compounddefs for
                        # namespaces are registered with just a single file
                        # location even if they namespace is spread over
                        # multiple files
                        AndFilter(
                            AndFilter(
                                NameFilter(NodeTypeAccessor(Child()), ["compounddef"]),
                                NotFilter(NameFilter(KindAccessor(Child()), ["namespace"]))
                                ),
                            NotFilter(
                                FilePathFilter(LambdaAccessor(Child(), lambda x: x.location), filename, self.path_handler)
                                )
                            )
                        )
                    )
                )

        return AndFilter(
                self.create_outline_filter(options),
                filter_
                )

    def create_group_content_filter(self):
        """Returns a filter which matches the contents of the group but not the group name or
        description.

        This allows the groups to be used to structure sections of the documentation rather than to
        structure and further document groups of documentation
        """

        # Display the contents of the sectiondef nodes and any innerclass or innernamespace
        # references
        return OrFilter(
                NameFilter(NodeTypeAccessor(Parent()), ["sectiondef"]),
                AndFilter(
                    NameFilter(NodeTypeAccessor(Child()), ["ref"]),
                    NameFilter(NodeNameAccessor(Child()), ["innerclass", "innernamespace"]),
                    )
                )

    def create_index_filter(self, options):

        filter_ = AndFilter(
                NotFilter(
                    AndFilter(
                        NameFilter(NodeTypeAccessor(Parent()), ["compounddef"]),
                        AndFilter(
                            NameFilter(NodeTypeAccessor(Child()),["ref"]),
                            NameFilter(NodeNameAccessor(Child()),["innerclass", "innernamespace"])
                            )
                        )
                    ),
                NotFilter(
                    AndFilter(
                        AndFilter(
                            NameFilter(NodeTypeAccessor(Parent()), ["compounddef"]),
                            NameFilter(KindAccessor(Parent()), ["group"])
                            ),
                        AndFilter(
                            NameFilter(NodeTypeAccessor(Child()),["sectiondef"]),
                            NameFilter(KindAccessor(Child()),["func"])
                            )
                        )
                    )
                )


        return AndFilter(
                self.create_outline_filter(options),
                filter_
                )

    def create_open_filter(self):
        """Returns a completely open filter which matches everything"""

        return OpenFilter()

    def create_file_finder_filter(self, filename):

        filter_ = AndFilter(
                AndFilter(
                    NameFilter(NodeTypeAccessor(Child()), ["compounddef"]),
                    NameFilter(KindAccessor(Child()), ["file"]),
                    ),
                FilePathFilter(LambdaAccessor(Child(), lambda x: x.location), filename, self.path_handler)
                )

        return filter_

    def create_group_finder_filter(self, name):
        """Returns a filter which looks for the compound node from the index which is a group node
        (kind=group) and has the appropriate name

        The compound node should reference the group file which we can parse for the group
        contents."""

        filter_ = AndFilter(
                AndFilter(
                    NameFilter(NodeTypeAccessor(Child()), ["compound"]),
                    NameFilter(KindAccessor(Child()), ["group"])
                    ),
                NameFilter(NameAccessor(Child()), [name])
                )

        return filter_

########NEW FILE########
__FILENAME__ = index

from breathe.renderer.rst.doxygen.base import Renderer

class DoxygenTypeSubRenderer(Renderer):

    def render(self):

        nodelist = []

        # Process all the compound children
        for compound in self.data_object.get_compound():
            compound_renderer = self.renderer_factory.create_renderer(self.data_object, compound)
            nodelist.extend(compound_renderer.render())

        return nodelist


# Used below in CompoundTypeSubRenderer and in RefTypeSubRenderer in compound.py so we have split it
# out in a helper function. This feels fairly ugly due to the number of arguments. A forced
# refactoring for the sake of refactoring rather than a beautiful reuse of code.
def render_compound(
    name,
    kind,
    file_data,
    rendered_data,
    renderer_factory,
    node_factory,
    domain_target,
    doxygen_target,
    document
    ):

    # Build targets for linking
    signode = node_factory.desc_signature()
    signode.extend(domain_target)
    signode.extend(doxygen_target)

    # Check if there is template information and format it as desired
    if file_data.compounddef.templateparamlist:
        renderer = renderer_factory.create_renderer(
                file_data.compounddef,
                file_data.compounddef.templateparamlist
                )
        template_nodes = []
        template_nodes.append(node_factory.Text("template <"))
        template_nodes.extend(renderer.render())
        template_nodes.append(node_factory.Text(">"))
        signode.append(node_factory.line("", *template_nodes))

    # Set up the title and a reference for it (refid)
    signode.append(node_factory.emphasis(text=kind))
    signode.append(node_factory.Text(" "))
    signode.append(node_factory.desc_name(text=name))

    contentnode = node_factory.desc_content()

    if file_data.compounddef.includes:
        for include in file_data.compounddef.includes:
            renderer = renderer_factory.create_renderer(
                    file_data.compounddef,
                    include
                    )
            contentnode.extend(renderer.render())

    contentnode.extend(rendered_data)

    node = node_factory.desc()
    node.document = document
    node['objtype'] = name
    node.append(signode)
    node.append(contentnode)

    return [node]


class CompoundTypeSubRenderer(Renderer):

    def __init__(self, compound_parser, *args):
        Renderer.__init__(self, *args)

        self.compound_parser = compound_parser

    def create_doxygen_target(self):
        """Can be overridden to create a target node which uses the doxygen refid information
        which can be used for creating links between internal doxygen elements.

        The default implementation should suffice most of the time.
        """

        refid = "%s%s" % (self.project_info.name(), self.data_object.refid)
        return self.target_handler.create_target(refid)

    def create_domain_target(self):
        """Should be overridden to create a target node which uses the Sphinx domain information so
        that it can be linked to from Sphinx domain roles like cpp:func:`myFunc`

        Returns a list so that if there is no domain active then we simply return an empty list
        instead of some kind of special null node value"""

        return []


    def render(self):

        # Read in the corresponding xml file and process
        file_data = self.compound_parser.parse(self.data_object.refid)

        data_renderer = self.renderer_factory.create_renderer(self.data_object, file_data)

        # Defer to function for details
        return render_compound(
                self.data_object.name,
                self.data_object.kind,
                file_data,
                data_renderer.render(),
                self.renderer_factory,
                self.node_factory,
                self.create_domain_target(),
                self.create_doxygen_target(),
                self.state.document
                )


class ClassCompoundTypeSubRenderer(CompoundTypeSubRenderer):

    def create_domain_target(self):

        return self.domain_handler.create_class_target(self.data_object)


########NEW FILE########
__FILENAME__ = target

class TargetHandler(object):

    def __init__(self, project_info, node_factory, document):

        self.project_info = project_info
        self.node_factory = node_factory
        self.document = document

    def create_target(self, id_):
        """Creates a target node and registers it with the document and returns it in a list"""

        target = self.node_factory.target(ids=[id_], names=[id_])

        try:
            self.document.note_explicit_target(target)
        except Exception:
            # TODO: We should really return a docutils warning node here
            print "Duplicate target detected: %s" % id_

        return [target]

class NullTargetHandler(object):

    def create_target(self, refid):
        return []

class TargetHandlerFactory(object):

    def __init__(self, node_factory):

        self.node_factory = node_factory

    def create_target_handler(self, options, project_info, document):

        if options.has_key("no-link"):
            return NullTargetHandler()

        return TargetHandler(project_info, self.node_factory, document)


########NEW FILE########
__FILENAME__ = transforms

from docutils.transforms import Transform
from docutils import nodes

from breathe.parser import ParserError, FileIOError
from breathe.nodes import DoxygenNode, DoxygenAutoNode
from breathe.renderer.rst.doxygen import format_parser_error

import textwrap

class IndexHandler(object):
    """
    Replaces a DoxygenNode with the rendered contents of the doxygen xml's index.xml file

    This used to be carried out in the doxygenindex directive implementation but we have this level
    of indirection to support the autodoxygenindex directive and share the code.
    """

    def __init__(self, name, project_info, options, state, lineno, factories):

        self.name = name
        self.project_info = project_info
        self.options = options
        self.state = state
        self.lineno = lineno
        self.factories = factories

    def render(self):

        try:
            finder = self.factories.finder_factory.create_finder(self.project_info)
        except ParserError, e:
            return format_parser_error(self.name, e.error, e.filename, self.state, self.lineno, True)
        except FileIOError, e:
            return format_parser_error(self.name, e.error, e.filename, self.state, self.lineno)

        data_object = finder.root()

        target_handler = self.factories.target_handler_factory.create_target_handler(self.options, self.project_info, self.state.document)
        filter_ = self.factories.filter_factory.create_index_filter(self.options)

        renderer_factory_creator = self.factories.renderer_factory_creator_constructor.create_factory_creator(
                self.project_info,
                self.state.document,
                self.options,
                target_handler
                )
        renderer_factory = renderer_factory_creator.create_factory(
                data_object,
                self.state,
                self.state.document,
                filter_,
                target_handler,
                )
        object_renderer = renderer_factory.create_renderer(self.factories.root_data_object, data_object)

        try:
            node_list = object_renderer.render()
        except ParserError, e:
            return format_parser_error(self.name, e.error, e.filename, self.state, self.lineno, True)
        except FileIOError, e:
            return format_parser_error(self.name, e.error, e.filename, self.state, self.lineno)

        return node_list


class ProjectData(object):
    "Simple handler for the files and project_info for each project"

    def __init__(self, auto_project_info, files):

        self.auto_project_info = auto_project_info
        self.files = files

class DoxygenAutoTransform(Transform):

    default_priority = 209

    def __init__(self, doxygen_handle, *args, **kwargs):
        Transform.__init__(self, *args, **kwargs)

        self.doxygen_handle = doxygen_handle

    def apply(self):
        """
        Iterate over all the DoxygenAutoNodes and:

        - Collect the information from them regarding what files need to be processed by doxygen and
          in what projects
        - Process those files with doxygen
        - Replace the nodes with DoxygenNodes which can be picked up by the standard rendering
          mechanism
        """

        project_files = {}

        # First collect together all the files which need to be doxygen processed for each project
        for node in self.document.traverse(DoxygenAutoNode):
            try:
                project_files[node.auto_project_info.name()].files.extend(node.files)
            except KeyError:
                project_files[node.auto_project_info.name()] = ProjectData(node.auto_project_info, node.files)

        per_project_project_info = {}
        
        # Iterate over the projects and generate doxygen xml output for the files for each one into
        # a directory in the Sphinx build area 
        for project_name, data in project_files.items():

            project_path = self.doxygen_handle.process(data.auto_project_info, data.files) 

            project_info = data.auto_project_info.create_project_info(project_path)
            per_project_project_info[data.auto_project_info.name()] = project_info

        # Replace each DoxygenAutoNode in the document with a properly prepared DoxygenNode which
        # can then be processed by the DoxygenTransform just as if it had come from a standard
        # doxygenindex directive
        for node in self.document.traverse(DoxygenAutoNode):

            handler = IndexHandler(
                    "autodoxygenindex",
                    per_project_project_info[node.auto_project_info.name()],
                    node.options,
                    node.state,
                    node.lineno,
                    node.factories
                    )

            standard_index_node = DoxygenNode(handler)

            node.replace_self(standard_index_node)

class DoxygenTransform(Transform):

    default_priority = 210

    def apply(self):
        "Iterate over all DoxygenNodes in the document and extract their handlers to replace them"

        for node in self.document.traverse(DoxygenNode):
            handler = node.handler

            # Replaces "node" in document with the renderer contents
            node.replace_self(handler.render())


class TransformWrapper(object):

    def __init__(self, transform, doxygen_handle):

        self.transform = transform
        self.doxygen_handle = doxygen_handle

        # Set up default_priority so sphinx/docutils can read it from this instance
        self.default_priority = transform.default_priority

    def __call__(self, *args, **kwargs):

        return self.transform(self.doxygen_handle, *args, **kwargs)


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# BreatheExample documentation build configuration file, created by
# sphinx-quickstart on Tue Feb  3 18:20:48 2009.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# General configuration
# ---------------------

sys.path.append( "../" )

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [ "breathe", "sphinx.ext.mathjax" ]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Breathe'
copyright = u'2009-2014, Michael Jones'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.2'
# The full version, including alpha/beta/rc tags.
release = '1.2.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = []

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

# Options for breathe extension
# -----------------------------

breathe_projects = {
    "class":"../examples/doxygen/class/xml/",
    "structcmd":"../examples/doxygen/structcmd/xml/",
    "tinyxml":"../examples/tinyxml/tinyxml/xml/",
    "restypedef":"../examples/doxygen/restypedef/xml/",
    "nutshell":"../examples/specific/nutshell/xml/",
    "rst":"../examples/specific/rst/xml/",
    "c_file":"../examples/specific/c_file/xml/",
    "namespacefile":"../examples/specific/namespacefile/xml/",
    "userdefined":"../examples/specific/userdefined/xml/",
    "template_function":"../examples/specific/template_function/xml/",
    "template_class":"../examples/specific/template_class/xml/",
    "template_class_non_type":
        "../examples/specific/template_class_non_type/xml/",
    "latexmath":"../examples/specific/latexmath/xml/",
    "functionOverload":"../examples/specific/functionOverload/xml/",
    "programlisting":"../examples/specific/programlisting/xml/",
    "image":"../examples/specific/image/xml/",
    "lists":"../examples/specific/lists/xml/",
    "group":"../examples/specific/group/xml/",
    "union":"../examples/specific/union/xml/",
    }

breathe_projects_source = {
    "class" : "../examples/doxygen"
    }

breathe_default_project = "tinyxml"

breathe_domain_by_extension = {
        "h" : "cpp",
        }

breathe_domain_by_file_pattern = {
        "*/class.h" : "cpp",
        "*/alias.h" : "c",
        }


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
# html_style = 'default.css'

html_theme = "haiku"

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'BreatheExampledoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'BreatheExample.tex', ur'BreatheExample Documentation',
   ur'Michael Jones', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

# *Cough*, ahem, borrowed from the Sphinx docs
def setup(app):
    app.add_object_type('confval', 'confval',
                             objname='configuration value',
                             indextemplate='pair: %s; configuration value')



########NEW FILE########
__FILENAME__ = docstring
"""@package docstring
Documentation for this module.

More details.
"""

def func():
    """Documentation for a function.

    More details.
    """
    pass

class PyClass:
    """Documentation for a class.

    More details.
    """
   
    def __init__(self):
        """The constructor."""
        self._memVar = 0;
   
    def PyMethod(self):
        """Documentation for a method."""
        pass
     

########NEW FILE########
__FILENAME__ = pyexample
## @package pyexample
#  Documentation for this module.
#
#  More details.

## Documentation for a function.
#
#  More details.
def func():
    pass

## Documentation for a class.
#
#  More details.
class PyClass:
   
    ## The constructor.
    def __init__(self):
        self._memVar = 0;
   
    ## Documentation for a method.
    #  @param self The object pointer.
    def PyMethod(self):
        pass
     
    ## A class variable.
    classVar = 0;

    ## @var _memVar
    #  a member variable

########NEW FILE########
