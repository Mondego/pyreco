__FILENAME__ = lizard
#!/usr/bin/env python
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  author: terry@odd-e.com
#
"""
lizard is a simple code complexity analyzer without caring about the C/C++
header files or Java imports.
Please find the README.rst for more information.
"""
from __future__ import print_function
import sys
if sys.version[0] == '2':
    from future_builtins import map, filter  # pylint: disable=W0622, F0401

import itertools
import re
import os
from fnmatch import fnmatch
import hashlib

VERSION = "1.8.3"

DEFAULT_CCN_THRESHOLD = 15


def analyze(paths, exclude_pattern=None, threads=1, extensions=None):
    '''
    returns an iterator of file infomation that contains function
    statistics.
    '''
    exclude_pattern = exclude_pattern or []
    extensions = extensions or []
    files = get_all_source_files(paths, exclude_pattern)
    file_analyzer = FileAnalyzer(extensions)
    return map_files_to_analyzer(files, file_analyzer, threads)


def create_command_line_parser(prog=None):
    from argparse import ArgumentParser
    parser = ArgumentParser(prog=prog)
    parser.add_argument('paths', nargs='*', default=['.'],
                        help='list of the filename/paths.')
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument("-V", "--verbose",
                        help="Output in verbose mode (long function name)",
                        action="store_true",
                        dest="verbose",
                        default=False)
    parser.add_argument("-C", "--CCN",
                        help='''Threshold for cyclomatic complexity number
                        warning. The default value is %d.
                        Functions with CCN bigger than it will generate warning
                        ''' % DEFAULT_CCN_THRESHOLD,
                        type=int,
                        dest="CCN",
                        default=DEFAULT_CCN_THRESHOLD)
    parser.add_argument("-a", "--arguments",
                        help="Limit for number of parameters",
                        type=int, dest="arguments", default=100)
    parser.add_argument("-w", "--warnings_only",
                        help='''Show warnings only, using clang/gcc's warning
                        format for printing warnings.
                        http://clang.llvm.org/docs/UsersManual.html#cmdoption-fdiagnostics-format
                        ''',
                        action="store_true",
                        dest="warnings_only",
                        default=False)
    parser.add_argument("-i", "--ignore_warnings",
                        help='''If the number of warnings is equal or less
                        than the number,
                        the tool will exit normally, otherwize it will generate
                        error. Useful in makefile for legacy code.''',
                        type=int,
                        dest="number",
                        default=0)
    parser.add_argument("-x", "--exclude",
                        help='''Exclude files that match this pattern. * matches
                        everything,
                        ? matches any single characoter, "./folder/*" exclude
                        everything in the folder recursively. Multiple patterns
                        can be specified. Don't forget to add "" around the
                        pattern.''',
                        action="append",
                        dest="exclude",
                        default=[])
    parser.add_argument("-X", "--xml",
                        help='''Generate XML in cppncss style instead of the
                        tabular output. Useful to generate report in Jenkins
                        server''',
                        action="store_true",
                        dest="xml",
                        default=None)
    parser.add_argument("-t", "--working_threads",
                        help='''number of working threads. The default
                        value is 1. Using a bigger
                        number can fully utilize the CPU and often faster.''',
                        type=int,
                        dest="working_threads",
                        default=1)
    parser.add_argument("-m", "--modified",
                        help="Calculate modified cyclomatic complexity number",
                        action="store_true",
                        dest="switchCasesAsOneCondition",
                        default=False)
    parser.add_argument("-E", "--extension",
                        help="under construction...",
                        action="append",
                        dest="extensions",
                        default=[])
    parser.add_argument("-s", "--sort",
                        help='''Sort the warning with field. The field can be
                        nloc, cyclomatic_complexity, token_count,
                        parameter_count, etc. Or an customized file.''',
                        action="append",
                        dest="sorting",
                        default=[])

    parser.usage = "lizard [options] [PATH or FILE] [PATH] ... "
    parser.description = __doc__
    return parser


class FunctionInfo(object):  # pylint: disable=R0902

    def __init__(self, name, filename, start_line=0, ccn=1):
        self.cyclomatic_complexity = ccn
        self.nloc = 1
        self.token_count = 1  # the first token
        self.name = name
        self.long_name = name
        self.start_line = start_line
        self.end_line = start_line
        self.parameter_count = 0
        self.filename = filename
        self.indent = -1

    location = property(lambda self:
                        " %(name)s@%(start_line)s-%(end_line)s@%(filename)s"
                        % self.__dict__)

    def add_to_function_name(self, app):
        self.name += app
        self.long_name += app

    def add_to_long_name(self, app):
        self.long_name += app

    def add_parameter(self, token):
        self.add_to_long_name(" " + token)

        if self.parameter_count == 0:
            self.parameter_count = 1
        if token == ",":
            self.parameter_count += 1

    def clang_format_warning(self):
        return (
            "%(filename)s:%(start_line)s: warning: %(name)s has" +
            " %(cyclomatic_complexity)d CCN and %(parameter_count)d" +
            " params (%(nloc)d NLOC, %(token_count)d tokens)") % self.__dict__


class FileInformation(object):  # pylint: disable=R0903

    def __init__(self, filename, nloc, function_list=None):
        self.filename = filename
        self.nloc = nloc
        self.function_list = function_list or []
        self.token_count = 0

    average_NLOC = property(lambda self: self.functions_average("nloc"))
    average_token = property(
        lambda self: self.functions_average("token_count"))
    average_CCN = property(
        lambda self: self.functions_average("cyclomatic_complexity"))
    CCN = property(
        lambda self:
        sum(fun.cyclomatic_complexity for fun in self.function_list))

    def functions_average(self, att):
        return (sum(getattr(fun, att) for fun in self.function_list)
                / len(self.function_list) if self.function_list else 0)


class CodeInfoContext(object):

    def __init__(self, filename):
        self.fileinfo = FileInformation(filename, 0)
        self.current_line = 0
        self.current_function = FunctionInfo('', '', 0)
        self.forgive = False
        self.newline = True

    def add_nloc(self, count):
        self.current_function.nloc += count
        self.fileinfo.nloc += count

    def start_new_function(self, name):
        self.current_function = FunctionInfo(
            name,
            self.fileinfo.filename,
            self.current_line)

    def add_condition(self, inc=1):
        self.current_function.cyclomatic_complexity += inc

    def add_to_long_function_name(self, app):
        self.current_function.add_to_long_name(app)

    def add_to_function_name(self, app):
        self.current_function.add_to_function_name(app)

    def parameter(self, token):
        self.current_function.add_parameter(token)

    def end_of_function(self):
        if not self.forgive:
            self.fileinfo.function_list.append(self.current_function)
        self.forgive = False
        self.current_function = FunctionInfo('', '', 0)


def preprocessing(tokens, reader):
    if hasattr(reader, "preprocess"):
        return reader.preprocess(tokens)
    else:
        return (t for t in tokens if not t.isspace() or t == '\n')


def comment_counter(tokens, reader):
    get_comment = reader.get_comment_from_token
    for token in tokens:
        comment = get_comment(token)
        if comment is not None:
            for _ in comment.splitlines()[1:]:
                yield '\n'
            if comment.strip().startswith("#lizard forgive"):
                reader.context.forgive = True
        else:
            yield token


def line_counter(tokens, reader):
    reader.context.current_line = 1
    for token in tokens:
        if token != "\n":
            count = token.count('\n')
            reader.context.current_line += count
            reader.context.add_nloc(count)
            yield token
        else:
            reader.context.current_line += 1
            reader.context.newline = True


def token_counter(tokens, reader):
    for token in tokens:
        reader.context.fileinfo.token_count += 1
        if reader.context.newline:
            reader.context.add_nloc(1)
            reader.context.newline = False
        reader.context.current_function.end_line = reader.context.current_line
        reader.context.current_function.token_count += 1
        yield token


def condition_counter(tokens, reader):
    if hasattr(reader, "conditions"):
        conditions = reader.conditions
    else:
        conditions = set(['if', 'for', 'while', '&&', '||', '?', 'catch',
                          'case'])
    for token in tokens:
        if token in conditions:
            reader.context.add_condition()
        yield token


def recount_switch_case(tokens, reader):
    for token in tokens:
        if token == 'switch':
            reader.context.add_condition()
        elif token == 'case':
            reader.context.add_condition(-1)
        yield token


class CodeReader(object):
    '''
    CodeReaders are used to parse functions structures from code of different
    language. Each language will need a subclass of CodeReader.
    '''
    def __init__(self, context):
        self.context = context
        self._state = lambda _: _

    @staticmethod
    def compile_file_extension_re(*exts):
        return re.compile(r".*\.(" + r"|".join(exts) + r")$", re.IGNORECASE)

    @staticmethod
    def get_reader(filename):
        # pylint: disable=E1101
        for lan in list(CodeReader.__subclasses__()):
            if CodeReader.compile_file_extension_re(*lan.ext).match(filename):
                return lan

    def state(self, token):
        self._state(token)

    def eof(self):
        pass

    @staticmethod
    def generate_tokens(source_code, addition=''):
        # DONOT put any sub groups in the regex. Good for performance
        _until_end = r"(?:\\\n|[^\n])*"
        combined_symbals = ["||", "&&", "===", "!==", "==", "!=", "<=", ">=",
                            "<<", ">>>", "++", ">>", "--", '+=', '-=',
                            '*=', '/=', '^=', '&=', '|=']
        token_pattern = re.compile(
            r"(?:\w+" +
            r"|/\*.*?\*/" +
            addition +
            r"|\"(?:\\.|[^\"])*\"" +
            r"|\'(?:\\.|[^\'])*?\'" +
            r"|//" + _until_end +
            r"|#" + _until_end +
            r"|:=|::|\*\*" +
            r"|" + r"|".join(re.escape(s) for s in combined_symbals) +
            r"|\n" +
            r"|[^\S\n]+" +
            r"|.)", re.M | re.S)
        return token_pattern.findall(source_code)


class CCppCommentsMixin(object):  # pylint: disable=R0903

    @staticmethod
    def get_comment_from_token(token):
        if token.startswith("/*") or token.startswith("//"):
            return token[2:]


try:
    # lizard.py can run as a stand alone script, without the extensions
    # The following langauages / extensions will not be supported in
    # stand alone script.
    # pylint: disable=W0611
    from lizard_ext import JavaScriptReader
    from lizard_ext import PythonReader
    from lizard_ext import xml_output
except ImportError:
    pass


class CLikeReader(CodeReader, CCppCommentsMixin):

    ''' This is the reader for C, C++ and Java. '''

    ext = ["c", "cpp", "cc", "mm", "cxx", "h", "hpp"]
    macro_pattern = re.compile(r"#\s*(\w+)\s*(.*)", re.M | re.S)

    def __init__(self, context):
        super(CLikeReader, self).__init__(context)
        self.bracket_stack = []
        self.br_count = 0
        self._state = self._state_global
        self._saved_tokens = []

    def preprocess(self, tokens):
        for token in tokens:
            if not token.isspace() or token == '\n':
                macro = self.macro_pattern.match(token)
                if macro:
                    if macro.group(1) in ('if', 'ifdef', 'elif'):
                        self.context.add_condition()
                    elif macro.group(1) == 'include':
                        yield "#include"
                        yield macro.group(2)
                    for _ in macro.group(2).splitlines()[1:]:
                        yield '\n'
                else:
                    yield token

    def _reset_to_global(self):
        self._state = self._state_global
        self.bracket_stack = []

    def _state_global(self, token):
        if token == 'typedef':
            self._state = self._state_typedef
        elif token[0].isalpha() or token[0] == '_':
            self.context.start_new_function(token)
            self._state = self._state_function
            if token == 'operator':
                self._state = self._state_operator

    def _state_typedef(self, token):
        if token == ';':
            self._state = self._state_global

    def _state_function(self, token):
        if token == '(':
            self.bracket_stack.append(token)
            self._state = self._state_dec
            self.context.add_to_long_function_name(token)
        elif token == '::':
            self._state = self._state_namespace
        elif token == '<':
            self._state = self._state_template_in_name
            self.bracket_stack.append(token)
            self.context.add_to_function_name(token)
        else:
            self._state = self._state_global
            self._state_global(token)

    def _state_template_in_name(self, token):
        if token == "<":
            self.bracket_stack.append(token)
        elif token in (">", ">>"):
            for _ in token:
                if self.bracket_stack.pop() != "<":
                    self._reset_to_global()
        if not self.bracket_stack:
            self._state = self._state_function
        self.context.add_to_function_name(token)

    def _state_operator(self, token):
        if token != '(':
            self._state = self._state_operator_next
        self.context.add_to_function_name(' ' + token)

    def _state_operator_next(self, token):
        if token == '(':
            self._state_function(token)
        else:
            self.context.add_to_function_name(' ' + token)

    def _state_namespace(self, token):
        self._state = self._state_operator\
            if token == 'operator' else self._state_function
        self.context.add_to_function_name("::" + token)

    def _state_dec(self, token):
        if token in ('(', "<"):
            self.bracket_stack.append(token)
        elif token in (')', ">", ">>"):
            for sub in token:
                if self.bracket_stack.pop() != {')': '(', '>': '<'}[sub]:
                    self._reset_to_global()
                    return
            if not self.bracket_stack:
                self._state = self._state_dec_to_imp
        elif len(self.bracket_stack) == 1:
            self.context.parameter(token)
            return
        self.context.add_to_long_function_name(" " + token)

    def _state_dec_to_imp(self, token):
        if token == 'const':
            self.context.add_to_long_function_name(" " + token)
        elif token == 'throw':
            self._state = self._state_throw
        elif token == '{':
            self.br_count += 1
            self._state = self._state_imp
        elif token == ":":
            self._state = self._state_initialization_list
        elif not token[0].isalpha() or token[0] == '_':
            self._state = self._state_global
        else:
            self._state = self._state_old_c_params
            self._saved_tokens = [token]

    def _state_throw(self, token):
        if token == ')':
            self._state = self._state_dec_to_imp

    def _state_old_c_params(self, token):
        self._saved_tokens.append(token)
        if token == ';':
            self._state = self._state_dec_to_imp
        elif token == '{':
            if len(self._saved_tokens) == 2:
                self._state_dec_to_imp(token)
                return
            self._state = self._state_global
            for token in self._saved_tokens:
                self._state(token)

    def _state_initialization_list(self, token):
        if token == '{':
            self.br_count += 1
            self._state = self._state_imp

    def _state_imp(self, token):
        if token == '{':
            self.br_count += 1
        elif token == '}':
            self.br_count -= 1
            if self.br_count == 0:
                self._state = self._state_global
                self.context.end_of_function()


class JavaReader(CLikeReader, CodeReader):

    ext = ['java']

    def _state_old_c_params(self, token):
        if token == '{':
            self._state_dec_to_imp(token)


class ObjCReader(CLikeReader, CodeReader):

    ext = ['m']

    def __init__(self, context):
        super(ObjCReader, self).__init__(context)

    def _state_global(self, token):
        super(ObjCReader, self)._state_global(token)
        if token == '(':
            self.bracket_stack.append(token)
            self._state = self._state_dec
            self.context.add_to_long_function_name(token)

    def _state_dec_to_imp(self, token):
        if token in ("+", "-"):
            self._state = self._state_global
        else:
            super(ObjCReader, self)._state_dec_to_imp(token)
            if self._state != self._state_imp:
                self._state = self._state_objc_dec_begin
                self.context.start_new_function(token)

    def _state_objc_dec_begin(self, token):
        if token == ':':
            self._state = self._state_objc_dec
            self.context.add_to_function_name(token)
        elif token == '{':
            self.br_count += 1
            self._state = self._state_imp
        else:
            self._state = self._state_global

    def _state_objc_dec(self, token):
        if token == '(':
            self._state = self._state_objc_param_type
            self.context.add_to_long_function_name(token)
        elif token == ',':
            pass
        elif token == '{':
            self.br_count += 1
            self._state = self._state_imp
        else:
            self._state = self._state_objc_dec_begin
            self.context.add_to_function_name(" " + token)

    def _state_objc_param_type(self, token):
        if token == ')':
            self._state = self._state_objc_param
        self.context.add_to_long_function_name(" " + token)

    def _state_objc_param(self, _):
        self._state = self._state_objc_dec


def token_processor_for_function(tokens, reader):
    ''' token_processor_for_function parse source code into functions. This is
    different from language to language. So token_processor_for_function need
    a language specific 'reader' to actually do the job.
    '''
    for token in tokens:
        reader.state(token)
        yield token
    reader.eof()


class FileAnalyzer(object):  # pylint: disable=R0903

    def __init__(self, extensions):
        self.processors = extensions

    def __call__(self, filename):
        try:
            return self.analyze_source_code(
                filename, open(filename, 'rU').read())
        except IOError:
            sys.stderr.write("Error: Fail to read source file '%s'\n"
                             % filename)

    def analyze_source_code(self, filename, code):
        context = CodeInfoContext(filename)
        reader = (CodeReader.get_reader(filename) or CLikeReader)(context)
        tokens = reader.generate_tokens(code)
        for processor in self.processors:
            tokens = processor(tokens, reader)
        for _ in tokens:
            pass
        return context.fileinfo


def warning_filter(option, module_infos):
    for file_info in module_infos:
        if file_info:
            for fun in file_info.function_list:
                if fun.cyclomatic_complexity > option.CCN or \
                        fun.parameter_count > option.arguments:
                    yield fun


def whitelist_filter(warnings, script=None):
    def _get_whitelist_item(script):
        white = {}
        pieces = script.replace('::', '##').split(':')
        if len(pieces) > 1:
            white['file_name'] = pieces[0]
            script = pieces[1]
        white['function_names'] = (
            [x.strip().replace('##', '::') for x in script.split(',')])
        return white

    def _in_list(warning):
        return any(_match_whitelist_item(white, warning)
                   for white in whitelist)

    def _match_whitelist_item(white, warning):
        return (warning.name in white['function_names'] and
                warning.filename == white.get('file_name', warning.filename))

    def get_whitelist():
        whitelist_filename = "whitelizard.txt"
        if os.path.isfile(whitelist_filename):
            return open(whitelist_filename, mode='r').read()
        return ''

    if not script:
        script = get_whitelist()
    whitelist = [
        _get_whitelist_item(line.split('#')[0])
        for line in script.splitlines()]
    for warning in warnings:
        if not _in_list(warning):
            yield warning


class OutputScheme(object):

    def __init__(self, ext):
        self.extensions = ext
        self.items = [
            {'caption': "  NLOC  ", 'value': "nloc"},
            {'caption': "  CCN  ", 'value': "cyclomatic_complexity"},
            {'caption': " token ", 'value': "token_count"},
            {'caption': " PARAM ", 'value': "parameter_count"},
        ] + [
            {
                'caption': ext.FUNCTION_CAPTION,
                'value': ext.FUNCTION_INFO_PART
            }
            for ext in self.extensions if hasattr(ext, "FUNCTION_CAPTION")]
        self.items.append({'caption': " location  ", 'value': 'location'})

    def captions(self):
        return "".join(item['caption'] for item in self.items)

    def function_info_head(self):
        captions = self.captions()
        return "\n".join(("=" * len(captions), captions, "-" * len(captions)))

    def function_info(self, fun):
        return ''.join(
            str(getattr(fun, item['value'])).rjust(len(item['caption']))
            for item in self.items)


def print_warnings(option, scheme, warnings):
    warning_count = 0
    if isinstance(option.sorting, list) and len(option.sorting) > 0:
        warnings = list(warnings)
        warnings.sort(reverse=True,
                      key=lambda x: getattr(x, option.sorting[0]))
    if not option.warnings_only:
        print(("\n" +
               "======================================\n" +
               "!!!! Warnings (CCN > %d) !!!!") % option.CCN)
        print(scheme.function_info_head())
    for warning in warnings:
        warning_count += 1
        if option.warnings_only:
            print(warning.clang_format_warning())
        else:
            print(scheme.function_info(warning))
    return warning_count


def print_total(warning_count, saved_result, option):
    file_infos = list(file_info for file_info in saved_result if file_info)
    all_fun = list(itertools.chain(*(file_info.function_list
                                     for file_info in file_infos)))
    cnt = len(all_fun)
    if cnt == 0:
        cnt = 1
    nloc_in_functions = sum([f.nloc for f in all_fun])
    if nloc_in_functions == 0:
        nloc_in_functions = 1
    total_info = (
        sum([f.nloc for f in file_infos]),
        nloc_in_functions / cnt,
        float(sum([f.cyclomatic_complexity for f in all_fun])) / cnt,
        float(sum([f.token_count for f in all_fun])) / cnt,
        cnt,
        warning_count,
        float(warning_count) / cnt,
        float(sum([f.nloc for f in all_fun
                   if f.cyclomatic_complexity > option.CCN]))
        / nloc_in_functions
    )

    if not option.warnings_only:
        print("=" * 90)
        print("Total nloc  Avg.nloc  Avg CCN  Avg token  Fun Cnt  Warning" +
              " cnt   Fun Rt   nloc Rt  ")
        print("-" * 90)
        print("%10d%10d%9.2f%11.2f%9d%13d%10.2f%8.2f" % total_info)


def print_and_save_modules(all_modules, extensions, scheme):
    all_functions = []
    print(scheme.function_info_head())
    for module_info in all_modules:
        for extension in extensions:
            if hasattr(extension, 'reduce'):
                extension.reduce(module_info)
        if module_info:
            all_functions.append(module_info)
            for fun in module_info.function_list:
                print(scheme.function_info(fun))

    print("--------------------------------------------------------------")
    print("%d file analyzed." % (len(all_functions)))
    print("==============================================================")
    print("NLOC    Avg.NLOC AvgCCN Avg.ttoken  function_cnt    file")
    print("--------------------------------------------------------------")
    for module_info in all_functions:
        print((
            "{module.nloc:7d}" +
            "{module.average_NLOC:7.0f}" +
            "{module.average_CCN:7.1f}" +
            "{module.average_token:10.0f}" +
            "{function_count:10d}" +
            "     {module.filename}").format(
                module=module_info,
                function_count=len(module_info.function_list)))

    return all_functions


def print_result(code_infos, option):
    scheme = OutputScheme(option.extensions)
    if not option.warnings_only:
        code_infos = print_and_save_modules(
            code_infos, option.extensions, scheme)
    warnings = warning_filter(option, code_infos)
    warnings = whitelist_filter(warnings)
    warning_count = print_warnings(option, scheme, warnings)
    print_total(warning_count, code_infos, option)
    for extension in option.extensions:
        if hasattr(extension, 'print_result'):
            extension.print_result()
    if option.number < warning_count:
        sys.exit(1)


def print_xml(results, options):
    print(xml_output(list(results), options.verbose))


def get_map_method(working_threads):
    try:
        if working_threads == 1:
            raise ImportError
        import multiprocessing
        pool = multiprocessing.Pool(processes=working_threads)
        return pool.imap_unordered
    except ImportError:
        return map


def map_files_to_analyzer(files, file_analyzer, working_threads):
    mapmethod = get_map_method(working_threads)
    return mapmethod(file_analyzer, files)


def md5_hash_file(full_path_name):
    ''' return md5 hash of a file '''
    try:
        with open(full_path_name, mode='r') as source_file:
            if sys.version_info[0] == 3:
                code_md5 = hashlib.md5(source_file.read().encode('utf-8'))
            else:
                code_md5 = hashlib.md5(source_file.read())
        return code_md5.hexdigest()
    except IOError:
        return None


def get_all_source_files(paths, exclude_patterns):
    '''
    Function counts md5 hash for the given file
    and checks if it isn't a duplicate using set
    of hashes for previous files
    '''
    hash_set = set()

    def _validate_file(pathname):
        return (
            pathname in paths or (
                CodeReader.get_reader(pathname) and all(
                    not fnmatch(
                        pathname,
                        p) for p in exclude_patterns)
                and _not_duplicate(pathname)))

    def _not_duplicate(full_path_name):
        fhash = md5_hash_file(full_path_name)
        if not fhash or fhash not in hash_set:
            hash_set.add(fhash)
            return True

    def all_listed_files(paths):
        for path in paths:
            if os.path.isfile(path):
                yield path
            else:
                for root, _, files in os.walk(path, topdown=False):
                    for filename in files:
                        yield os.path.join(root, filename)

    return filter(_validate_file, all_listed_files(paths))


def parse_args(argv):
    options = create_command_line_parser(argv[0]).parse_args(args=argv[1:])
    values = [
        item['value'] for item in OutputScheme([]).items]
    for sort_factor in options.sorting:
        if sort_factor not in values:
            error_message = "Wrong sorting field '%s'.\n" % sort_factor
            error_message += "Candidates are: " + ', '.join(values) + "\n"
            sys.stderr.write(error_message)
            sys.exit(2)
    return options


def get_extensions(extension_names, switch_case_as_one_condition=False):
    from importlib import import_module
    extensions = [
        preprocessing,
        comment_counter,
        line_counter,
        condition_counter,
        token_counter,
        token_processor_for_function,
    ]
    if switch_case_as_one_condition:
        extensions.append(recount_switch_case)

    return extensions +\
        [import_module('lizard_ext.lizard' + name.lower()).LizardExtension()
            if isinstance(name, str) else name for name in extension_names]

analyze_file = FileAnalyzer(get_extensions([]))  # pylint: disable=C0103


def lizard_main(argv):
    options = parse_args(argv)
    options.extensions = get_extensions(options.extensions,
                                        options.switchCasesAsOneCondition)
    printer = print_xml if options.xml else print_result
    result = analyze(
        options.paths,
        options.exclude,
        options.working_threads,
        options.extensions)
    printer(result, options)

if __name__ == "__main__":
    lizard_main(sys.argv)

########NEW FILE########
__FILENAME__ = javascript
'''
Language parser for JavaScript
'''

from lizard import CodeReader, CCppCommentsMixin
import re


class JavaScriptReader(CodeReader, CCppCommentsMixin):

    ext = ['js']

    @staticmethod
    def generate_tokens(source_code, _=None):
        regx_regx = r"|/(?:\\.|[^/])+?/[igm]*"
        regx_pattern = re.compile(regx_regx)
        word_pattern = re.compile(r'\w+')
        tokens = CodeReader.generate_tokens(source_code, regx_regx)
        leading_by_word = False
        for token in tokens:
            if leading_by_word and regx_pattern.match(token):
                for subtoken in CodeReader.generate_tokens(token):
                    yield subtoken
            else:
                yield token
            if not token.isspace():
                leading_by_word = word_pattern.match(token)

    def __init__(self, context):
        super(JavaScriptReader, self).__init__(context)
        # start from one, so global level will never count
        self.brace_count = 1
        self._state = self._global
        self.last_tokens = ''
        self.function_name = ''
        self.function_stack = []

    def _global(self, token):
        if token == 'function':
            self._state = self._function
        elif token in ('=', ':'):
            self.function_name = self.last_tokens
        elif token in '.':
            self._state = self._field
            self.last_tokens += token
        else:
            if token == '{':
                self.brace_count += 1
            elif token == '}':
                self.brace_count -= 1
                if self.brace_count == 0:
                    self._state = self._global
                    self._pop_function_from_stack()
            self.last_tokens = token
            self.function_name = ''

    def _pop_function_from_stack(self):
        self.context.end_of_function()
        if self.function_stack:
            self.context.current_function = self.function_stack.pop()
            self.brace_count = self.context.current_function.brace_count

    def _function(self, token):
        if token != '(':
            self.function_name = token
        else:
            self.context.current_function.brace_count = self.brace_count
            self.function_stack.append(self.context.current_function)
            self.brace_count = 0
            self.context.start_new_function(self.function_name or 'function')
            self._state = self._dec

    def _field(self, token):
        self.last_tokens += token
        self._state = self._global

    def _dec(self, token):
        if token == ')':
            self._state = self._global
        else:
            self.context.parameter(token)
            return
        self.context.add_to_long_function_name(" " + token)

########NEW FILE########
__FILENAME__ = lizarddependencycount
'''
This is an extension of lizard, that counts the amount of dependencies
within the code.
'''


class LizardExtension(object):  # pylint: disable=R0903
    FUNCTION_CAPTION = " dep cnt "
    FUNCTION_INFO_PART = "dependency_count"

    def __call__(self, tokens, reader):
        ignored_list = {','}
        dependency_type = {
            'null': 0,
            '#include': 1,
            'import': 2,
            'python_import_as_change': 3}
        expect_dependency = 0
        import_list = []
        import_as_list = []
        import_as_counter = 0
        for token in tokens:
            if not hasattr(reader.context.current_function,
                           "dependency_count"):
                reader.context.current_function.dependency_count = 0
            # this accounts for java, c, c++ and python's import
            if token == "import" or token == "#include":
                if import_as_list != []:
                    import_list.append(import_as_list)
                expect_dependency = dependency_type[token]
            elif expect_dependency == dependency_type['#include']:
                # gets rid of the <> or "" as well as the .h
                import_list += [token[1:len(token) - 3]]
                expect_dependency = dependency_type['null']
            elif expect_dependency == dependency_type['import']:
                if token == "as":
                    expect_dependency = dependency_type[
                        'python_import_as_change']
                    import_as_counter = len(import_as_list)
                    import_as_list = []
                elif import_as_counter > 4:
                    import_list += [import_as_list[0]]
                    import_as_list = []
                    import_as_counter = 0
                    expect_dependency = dependency_type['null']
                elif token not in ignored_list:
                    import_as_counter += 1
                    import_as_list += [token]
            elif (expect_dependency ==
                  dependency_type['python_import_as_change']
                  and token not in ignored_list):
                import_as_counter -= 1
                import_list += [token]
                if import_as_counter == 0:
                    expect_dependency = dependency_type['null']
            if token in import_list:
                reader.context.current_function.dependency_count += 1
            yield token

########NEW FILE########
__FILENAME__ = lizardexitcount
'''
This is an extension of lizard, that counts the 'exit points'
in every function.
'''


class LizardExtension(object):  # pylint: disable=R0903

    FUNCTION_CAPTION = " exits "
    FUNCTION_INFO_PART = "exit_count"

    def __call__(self, tokens, reader):
        first_return = False
        for token in tokens:
            if not hasattr(reader.context.current_function, "exit_count"):
                reader.context.current_function.exit_count = 1
                first_return = True
            if token == "return":
                if first_return:
                    first_return = False
                else:
                    reader.context.current_function.exit_count += 1
            yield token

########NEW FILE########
__FILENAME__ = lizardwordcount
'''
This is an extension to lizard. It count the reccurance of every identifier
in the source code (ignoring the comments and strings), and then generate
a tag cloud based on the popularity of the identifiers.
The tag cloud is generated on an HTML5 canvas. So it will eventually save
the result to an HTML file and open the browser to show it.
'''

import webbrowser
from os.path import abspath


class LizardExtension(object):

    HTML_FILENAME = "codecloud.html"
    ignoreList = set((
        '(',
        ')',
        '{',
        '}',
        ';',
        ',',
        '\n',
        '~',
        'static_cast',
        '&&',
        '#pragma',
        '!',
        'virtual',
        '++',
        'operator',
        '-',
        'private',
        'else',
        '+',
        '!=',
        '?',
        '/',
        ">=",
        "<=",
        "|=",
        "&=",
        "-=",
        "/=",
        "*=",
        'static',
        'inline',
        ']',
        '==',
        '+=',
        '[',
        '|',
        '||',
        'public',
        'struct',
        'typedef',
        'class',
        '<<',
        '#endif',
        '#if',
        'if',
        'for',
        'case',
        'break',
        'namespace',
        ':',
        '->',
        'return',
        'void',
        '*',
        '#include',
        '=',
        'const',
        '<',
        '>',
        '&',
        '\\',
        "\\\\\\",
        '.',
        '::',
    ))

    def __init__(self):
        self.result = {}

    @staticmethod
    def __call__(tokens, reader):
        '''
        The function will be used in multiple threading tasks.
        So don't store any data with an extension object.
        '''
        reader.context.fileinfo.wordCount = result = {}
        for token in tokens:
            if token not in LizardExtension.ignoreList\
                    and token[0] not in ('"', "'", '#'):
                result[token] = result.get(token, 0) + 1
            yield token

    def reduce(self, fileinfo):
        '''
        Combine the statistics from each file.
        Because the statistics came from multiple thread tasks. This function
        needs to be called to collect the combined result.
        '''
        for k, val in fileinfo.wordCount.items():
            self.result[k] = self.result.get(k, 0) + val

    def print_result(self):
        with open(self.HTML_FILENAME, 'w') as html_file:
            html_file.write('''
<html>
    <head>
        <meta name="viewport" content="width=device-width,
            initial-scale=1.0,maximum-scale=1.0" />
        <style type="text/css">
            canvas {
                border: 1px solid black;
                width: 700px;
                height: 700px;
            }
        </style>
        <script type="text/javascript">
        ''')
            html_file.write(self.TAG_CLOUD_JAVASCRIPT)
            html_file.write('''
        </script>
        <script type="application/javascript">
            function draw() {
                var canvas = document.getElementById("canvas");
                    if (canvas.getContext) {
                        var ctx = canvas.getContext("2d");
                        // scale 2x
                        if(window.devicePixelRatio == 2) {
                            canvas.setAttribute('width', canvas.width * 2);
                            canvas.setAttribute('height', canvas.height * 2);
                        }
                        var tagCloud = new TagCloud(canvas.width,
                            canvas.height, ctx);
                        tagCloud.render([''')
            tags = sorted(self.result, key=self.result.get, reverse=True)[:400]
            for k in tags:
                html_file.write(
                    ' ' * 40 + '["%s", %d],\n' % (
                        k.replace('"', '\\\"')
                        .replace("'", "\\\\'").replace("\\", "\\\\"),
                        self.result[k]))
            html_file.write('''
                                    ]);
                                }
                        }
                    </script>
                </head>
                <body onload="draw();">
                    <canvas id="canvas" width="700" height="700"></canvas>
                </body>
            </html>''')

            webbrowser.open("file://" + abspath(self.HTML_FILENAME))

    TAG_CLOUD_JAVASCRIPT = '''

function TagCloud(w, h, context) {
    "use strict";
    this.ctx = context;
    this.canvasWidth = w;
    this.canvasHeight = h;
    this.fontSize = this.canvasHeight / 3;
    this.shape = "rectangle";
}

TagCloud.prototype.setShape = function () {
    this.shape = "circle";
};

TagCloud.prototype.render = function (tags) {
    this.ctx.textBaseline = "top";
    tags.forEach(function (tag) {
        this.placeTag(tag[0]);
    }, this);
};

TagCloud.prototype.placeTag = function (tag) {
    var placement;
    while (!(placement = this._getNonOverlappingPlaceWithBestSize(
            this.fontSize, tag)))
        this.fontSize *= 0.9;

    this.ctx.fillStyle = this._getRandomColor();
    this.ctx.fillText(tag, placement.x, placement.y);
};

TagCloud.prototype._getNonOverlappingPlaceWithBestSize =
    function (fontSize, tag) {
    this.ctx.font = "" + fontSize + "pt " + "Arial";
    var lineHeight=this.getLineHeight(fontSize);
    var tagWidth = this.ctx.measureText(tag).width;

    var base = new BasePlacement(
        (this.canvasWidth - tagWidth) * Math.random(),
        (this.canvasHeight - lineHeight) * Math.random(),
        lineHeight
        );

    var placement;
    /* jshint ignore:start */
    while (placement = base.nextPlaceToTry()) {
        if (this._isPlaceEmpty(placement, tagWidth, lineHeight))
            break;
    }
    /* jshint ignore:end */
    return placement;
};

TagCloud.prototype.getLineHeight = function (fontSize) {
    return this.ctx.measureText('M').width * 1.2;
}

TagCloud.prototype._getRandomColor = function (){
    var colors = ["aqua", "black", "blue", "fuchsia", "gray", "green",
                  "lime", "maroon", "navy", "olive", "orange", "purple",
                  "red", "silver", "teal"];
    return colors[Math.floor(colors.length * Math.random())];
};

TagCloud.prototype._isPlaceEmpty = function (placement, width, height) {
    if (placement.x < 0 || placement.y < 0 || placement.x + width >
         this.canvasWidth || placement.y + height > this.canvasHeight)
        return false;

    var pix = this.ctx.getImageData(
                placement.x, placement.y, width, height).data;

    for (var i = 0, n = pix.length; i < n; i += 4)
        if (pix[i+3])
                return false;

    return [[placement.x, placement.y],
            [placement.x + width, placement.y],
            [placement.x, placement.y + height],
            [placement.x + width, placement.y + height]].every(
                function(pos) {
                    var a = this.canvasWidth / 2;
                    var b = this.canvasHeight / 2;
                    var X = pos[0] - a;
                    var Y = pos[1] - b;
                    return (X * X / a / a + Y * Y / b / b < 1);
                }, this);
};

TagCloud.prototype.getCoverage = function () {
    var pix = this.ctx.getImageData(
                0, 0, this.canvasWidth, this.canvasHeight).data;
    var pixCount = 0;
    for (var i = 0, n = pix.length; i < n; i += 4) {
        if (pix[i+3])
            pixCount++;
    }
    return pixCount * 100 / this.canvasWidth / this.canvasHeight;
};

function BasePlacement(x, y, h) {
    var baseX = x,
        baseY = y,
        scale = h,
        tryNumber = 0;

    this.nextPlaceToTry = function() {
        if (tryNumber < this._spiralOffsets.length)
            return {
                x : baseX + this._spiralOffsets[tryNumber][0] * scale,
                y : baseY + this._spiralOffsets[tryNumber++][1] * scale
            };
    };
}

function generateSpiralOffsets() {
    var spiralOffsets = [];
    var radius = 0;
    var dr = 0.2;
    for (var i = 0; radius < 40; i+=0.4, radius += dr) {
        spiralOffsets.push([
                   radius * Math.sin(i),
                   radius * Math.cos(i)
                ]);
    }
    return spiralOffsets;
}

BasePlacement.prototype._spiralOffsets = generateSpiralOffsets();

    '''

########NEW FILE########
__FILENAME__ = python
''' Language parser for Python '''

from lizard import CodeReader


class PythonReader(CodeReader):

    ext = ['py']
    conditions = set(['if', 'for', 'while', 'and', 'or',
                     'elif', 'except', 'finally'])

    def __init__(self, context):
        super(PythonReader, self).__init__(context)
        self._state = self._global
        self.function_stack = []
        self.current_indent = 0
        self.leading_space = True

    @staticmethod
    def generate_tokens(source_code, _=None):
        return CodeReader.generate_tokens(
            source_code,
            r"|\'\'\'.*?\'\'\'" + r'|\"\"\".*?\"\"\"')

    def preprocess(self, tokens):
        for token in tokens:
            if token != '\n':
                if self.leading_space:
                    if token.isspace():
                        self.current_indent = len(token.replace('\t', ' ' * 8))
                    else:
                        if not token.startswith('#'):
                            self._close_functions()
                        self.leading_space = False
            else:
                self.leading_space = True
                self.current_indent = 0
            if not token.isspace() or token == '\n':
                yield token

    @staticmethod
    def get_comment_from_token(token):
        if token.startswith("#"):
            return token[1:]

    def _global(self, token):
        if token == 'def':
            self._state = self._function

    def _function(self, token):
        if token != '(':
            self.function_stack.append(self.context.current_function)
            self.context.start_new_function(token)
            self.context.current_function.indent = self.current_indent
        else:
            self._state = self._dec

    def _dec(self, token):
        if token == ')':
            self._state = self._state_colon
        else:
            self.context.parameter(token)
            return
        self.context.add_to_long_function_name(" " + token)

    def _state_colon(self, token):
        self._state = self._state_first_line if token == ':' else self._global

    def _state_first_line(self, token):
        self._state = self._global
        if token.startswith('"""') or token.startswith("'''"):
            self.context.add_nloc(-token.count('\n') - 1)
        self._global(token)

    def eof(self):
        self.current_indent = 0
        self._close_functions()

    def _close_functions(self):
        while self.context.current_function.indent >= self.current_indent:
            endline = self.context.current_function.end_line
            self.context.end_of_function()
            self.context.current_function = self.function_stack.pop()
            self.context.current_function.end_line = endline

########NEW FILE########
__FILENAME__ = xmloutput
'''
Thanks for Holy Wen from Nokia Siemens Networks to let me use his code
to put the result into xml file that is compatible with cppncss.
Jenkens has plugin for cppncss format result to display the diagram.
'''


def xml_output(result, verbose):
    import xml.dom.minidom

    impl = xml.dom.minidom.getDOMImplementation()
    doc = impl.createDocument(None, "cppncss", None)
    root = doc.documentElement

    processing_instruction = doc.createProcessingInstruction(
        'xml-stylesheet',
        'type="text/xsl" ' +
        'href="https://raw.github.com/terryyin/lizard/master/lizard.xsl"')
    doc.insertBefore(processing_instruction, root)

    root.appendChild(_create_function_measure(doc, result, verbose))
    root.appendChild(_create_file_measure(doc, result))

    return doc.toprettyxml()


def _create_function_measure(doc, result, verbose):
    measure = doc.createElement("measure")
    measure.setAttribute("type", "Function")
    measure.appendChild(_create_labels(doc, ["Nr.", "NCSS", "CCN"]))

    number = 0
    total_func_ncss = 0
    total_func_ccn = 0

    for source_file in result:
        file_name = source_file.filename
        for func in source_file.function_list:
            number += 1
            total_func_ncss += func.nloc
            total_func_ccn += func.cyclomatic_complexity
            measure.appendChild(
                _create_function_item(
                    doc, number, file_name, func, verbose))

        if number != 0:
            measure.appendChild(
                _create_labeled_value_item(
                    doc, 'average', "NCSS", str(total_func_ncss / number)))
            measure.appendChild(
                _create_labeled_value_item(
                    doc, 'average', "CCN", str(total_func_ccn / number)))
    return measure


def _create_file_measure(doc, result):
    measure = doc.createElement("measure")
    measure.setAttribute("type", "File")
    measure.appendChild(
        _create_labels(doc, ["Nr.", "NCSS", "CCN", "Functions"]))

    file_nr = 0
    file_total_ncss = 0
    file_total_ccn = 0
    file_total_funcs = 0

    for source_file in result:
        file_nr += 1
        file_total_ncss += source_file.nloc
        file_total_ccn += source_file.CCN
        file_total_funcs += len(source_file.function_list)
        measure.appendChild(
            _create_file_node(doc, source_file, file_nr))

    if file_nr != 0:
        file_summary = [("NCSS", file_total_ncss / file_nr),
                        ("CCN", file_total_ccn / file_nr),
                        ("Functions", file_total_funcs / file_nr)]
        for key, val in file_summary:
            measure.appendChild(
                _create_labeled_value_item(doc, 'average', key, val))

    summary = [("NCSS", file_total_ncss),
               ("CCN", file_total_ccn),
               ("Functions", file_total_funcs)]
    for key, val in summary:
        measure.appendChild(_create_labeled_value_item(doc, 'sum', key, val))
    return measure


def _create_label(doc, name):
    label = doc.createElement("label")
    text1 = doc.createTextNode(name)
    label.appendChild(text1)
    return label


def _create_labels(doc, label_name):
    labels = doc.createElement("labels")
    for label in label_name:
        labels.appendChild(_create_label(doc, label))

    return labels


def _create_function_item(doc, number, file_name, func, verbose):
    item = doc.createElement("item")
    if verbose:
        item.setAttribute(
            "name", "%s at %s:%s" %
            (func.long_name, file_name, func.start_line))
    else:
        item.setAttribute(
            "name", "%s(...) at %s:%s" %
            (func.name, file_name, func.start_line))
    value1 = doc.createElement("value")
    text1 = doc.createTextNode(str(number))
    value1.appendChild(text1)
    item.appendChild(value1)
    value2 = doc.createElement("value")
    text2 = doc.createTextNode(str(func.nloc))
    value2.appendChild(text2)
    item.appendChild(value2)
    value3 = doc.createElement("value")
    text3 = doc.createTextNode(str(func.cyclomatic_complexity))
    value3.appendChild(text3)
    item.appendChild(value3)
    return item


def _create_labeled_value_item(doc, name, label, value):
    average_ncss = doc.createElement(name)
    average_ncss.setAttribute("lable", label)
    average_ncss.setAttribute("value", str(value))
    return average_ncss


def _create_file_node(doc, source_file, file_nr):
    item = doc.createElement("item")
    item.setAttribute("name", source_file.filename)
    value1 = doc.createElement("value")
    text1 = doc.createTextNode(str(file_nr))
    value1.appendChild(text1)
    item.appendChild(value1)
    value2 = doc.createElement("value")
    text2 = doc.createTextNode(str(source_file.nloc))
    value2.appendChild(text2)
    item.appendChild(value2)
    value3 = doc.createElement("value")
    text3 = doc.createTextNode(str(source_file.CCN))
    value3.appendChild(text3)
    item.appendChild(value3)
    value4 = doc.createElement("value")
    text4 = doc.createTextNode(str(len(source_file.function_list)))
    value4.appendChild(text4)
    item.appendChild(value4)
    return item

########NEW FILE########
__FILENAME__ = mock
# mock.py
# Test tools for mocking and patching.
# Copyright (C) 2007-2012 Michael Foord & the mock team
# E-mail: fuzzyman AT voidspace DOT org DOT uk

# mock 0.8.0
# http://www.voidspace.org.uk/python/mock/

# Released subject to the BSD License
# Please see http://www.voidspace.org.uk/python/license.shtml

# Scripts maintained at http://www.voidspace.org.uk/python/index.shtml
# Comments, suggestions and bug reports welcome.


__all__ = (
    'Mock',
    'MagicMock',
    'mocksignature',
    'patch',
    'sentinel',
    'DEFAULT',
    'ANY',
    'call',
    'create_autospec',
    'FILTER_DIR',
    'NonCallableMock',
    'NonCallableMagicMock',
)


__version__ = '0.8.0'


import pprint
import sys

try:
    import inspect
except ImportError:
    # for alternative platforms that
    # may not have inspect
    inspect = None

try:
    from functools import wraps
except ImportError:
    # Python 2.4 compatibility
    def wraps(original):
        def inner(f):
            f.__name__ = original.__name__
            f.__doc__ = original.__doc__
            f.__module__ = original.__module__
            return f
        return inner

try:
    unicode
except NameError:
    # Python 3
    basestring = unicode = str

try:
    long
except NameError:
    # Python 3
    long = int

try:
    BaseException
except NameError:
    # Python 2.4 compatibility
    BaseException = Exception

try:
    next
except NameError:
    def next(obj):
        return obj.next()


BaseExceptions = (BaseException,)
if 'java' in sys.platform:
    # jython
    import java
    BaseExceptions = (BaseException, java.lang.Throwable)

try:
    _isidentifier = str.isidentifier
except AttributeError:
    # Python 2.X
    import keyword
    import re
    regex = re.compile(r'^[a-z_][a-z0-9_]*$', re.I)
    def _isidentifier(string):
        if string in keyword.kwlist:
            return False
        return regex.match(string)


inPy3k = sys.version_info[0] == 3

# Needed to work around Python 3 bug where use of "super" interferes with
# defining __class__ as a descriptor
_super = super

self = 'im_self'
builtin = '__builtin__'
if inPy3k:
    self = '__self__'
    builtin = 'builtins'

FILTER_DIR = True


def _is_instance_mock(obj):
    # can't use isinstance on Mock objects because they override __class__
    # The base class for all mocks is NonCallableMock
    return issubclass(type(obj), NonCallableMock)


def _is_exception(obj):
    return (
        isinstance(obj, BaseExceptions) or
        isinstance(obj, ClassTypes) and issubclass(obj, BaseExceptions)
    )


class _slotted(object):
    __slots__ = ['a']


DescriptorTypes = (
    type(_slotted.a),
    property,
)


# getsignature and mocksignature heavily "inspired" by
# the decorator module: http://pypi.python.org/pypi/decorator/
# by Michele Simionato

def _getsignature(func, skipfirst):
    if inspect is None:
        raise ImportError('inspect module not available')

    if inspect.isclass(func):
        func = func.__init__
        # will have a self arg
        skipfirst = True
    elif not (inspect.ismethod(func) or inspect.isfunction(func)):
        func = func.__call__

    regargs, varargs, varkwargs, defaults = inspect.getargspec(func)

    # instance methods need to lose the self argument
    if getattr(func, self, None) is not None:
        regargs = regargs[1:]

    _msg = ("_mock_ is a reserved argument name, can't mock signatures using "
            "_mock_")
    assert '_mock_' not in regargs, _msg
    if varargs is not None:
        assert '_mock_' not in varargs, _msg
    if varkwargs is not None:
        assert '_mock_' not in varkwargs, _msg
    if skipfirst:
        regargs = regargs[1:]

    signature = inspect.formatargspec(regargs, varargs, varkwargs, defaults,
                                      formatvalue=lambda value: "")
    return signature[1:-1], func


def _getsignature2(func, skipfirst, instance=False):
    if inspect is None:
        raise ImportError('inspect module not available')

    if isinstance(func, ClassTypes) and not instance:
        try:
            func = func.__init__
        except AttributeError:
            return
        skipfirst = True
    elif not isinstance(func, FunctionTypes):
        # for classes where instance is True we end up here too
        try:
            func = func.__call__
        except AttributeError:
            return

    try:
        regargs, varargs, varkwargs, defaults = inspect.getargspec(func)
    except TypeError:
        # C function / method, possibly inherited object().__init__
        return

    # instance methods and classmethods need to lose the self argument
    if getattr(func, self, None) is not None:
        regargs = regargs[1:]
    if skipfirst:
        # this condition and the above one are never both True - why?
        regargs = regargs[1:]

    signature = inspect.formatargspec(regargs, varargs, varkwargs, defaults,
                                      formatvalue=lambda value: "")
    return signature[1:-1], func


def _check_signature(func, mock, skipfirst, instance=False):
    if not _callable(func):
        return

    result = _getsignature2(func, skipfirst, instance)
    if result is None:
        return
    signature, func = result

    # can't use self because "self" is common as an argument name
    # unfortunately even not in the first place
    src = "lambda _mock_self, %s: None" % signature
    checksig = eval(src, {})
    _copy_func_details(func, checksig)
    type(mock)._mock_check_sig = checksig


def _copy_func_details(func, funcopy):
    funcopy.__name__ = func.__name__
    funcopy.__doc__ = func.__doc__
    #funcopy.__dict__.update(func.__dict__)
    funcopy.__module__ = func.__module__
    if not inPy3k:
        funcopy.func_defaults = func.func_defaults
        return
    funcopy.__defaults__ = func.__defaults__
    funcopy.__kwdefaults__ = func.__kwdefaults__


def _callable(obj):
    if isinstance(obj, ClassTypes):
        return True
    if getattr(obj, '__call__', None) is not None:
        return True
    return False


def _is_list(obj):
    # checks for list or tuples
    # XXXX badly named!
    return type(obj) in (list, tuple)


def _instance_callable(obj):
    """Given an object, return True if the object is callable.
    For classes, return True if instances would be callable."""
    if not isinstance(obj, ClassTypes):
        # already an instance
        return getattr(obj, '__call__', None) is not None

    klass = obj
    # uses __bases__ instead of __mro__ so that we work with old style classes
    if klass.__dict__.get('__call__') is not None:
        return True

    for base in klass.__bases__:
        if _instance_callable(base):
            return True
    return False


def _set_signature(mock, original, instance=False):
    # creates a function with signature (*args, **kwargs) that delegates to a
    # mock. It still does signature checking by calling a lambda with the same
    # signature as the original. This is effectively mocksignature2.
    if not _callable(original):
        return

    skipfirst = isinstance(original, ClassTypes)
    result = _getsignature2(original, skipfirst, instance)
    if result is None:
        # was a C function (e.g. object().__init__ ) that can't be mocked
        return

    signature, func = result

    src = "lambda %s: None" % signature
    context = {'_mock_': mock}
    checksig = eval(src, context)
    _copy_func_details(func, checksig)

    name = original.__name__
    if not _isidentifier(name):
        name = 'funcopy'
    context = {'checksig': checksig, 'mock': mock}
    src = """def %s(*args, **kwargs):
    checksig(*args, **kwargs)
    return mock(*args, **kwargs)""" % name
    exec (src, context)
    funcopy = context[name]
    _setup_func(funcopy, mock)
    return funcopy


def mocksignature(func, mock=None, skipfirst=False):
    """
    mocksignature(func, mock=None, skipfirst=False)

    Create a new function with the same signature as `func` that delegates
    to `mock`. If `skipfirst` is True the first argument is skipped, useful
    for methods where `self` needs to be omitted from the new function.

    If you don't pass in a `mock` then one will be created for you.

    The mock is set as the `mock` attribute of the returned function for easy
    access.

    Functions returned by `mocksignature` have many of the same attributes
    and assert methods as a mock object.

    `mocksignature` can also be used with classes. It copies the signature of
    the `__init__` method.

    When used with callable objects (instances) it copies the signature of the
    `__call__` method.
    """
    if mock is None:
        mock = Mock()
    signature, func = _getsignature(func, skipfirst)
    src = "lambda %(signature)s: _mock_(%(signature)s)" % {
        'signature': signature
    }

    funcopy = eval(src, dict(_mock_=mock))
    _copy_func_details(func, funcopy)
    _setup_func(funcopy, mock)
    return funcopy


def _setup_func(funcopy, mock):
    funcopy.mock = mock

    # can't use isinstance with mocks
    if not _is_instance_mock(mock):
        return

    def assert_called_with(*args, **kwargs):
        return mock.assert_called_with(*args, **kwargs)
    def assert_called_once_with(*args, **kwargs):
        return mock.assert_called_once_with(*args, **kwargs)
    def assert_has_calls(*args, **kwargs):
        return mock.assert_has_calls(*args, **kwargs)
    def assert_any_call(*args, **kwargs):
        return mock.assert_any_call(*args, **kwargs)
    def reset_mock():
        funcopy.method_calls = _CallList()
        funcopy.mock_calls = _CallList()
        mock.reset_mock()
        ret = funcopy.return_value
        if _is_instance_mock(ret) and not ret is mock:
            ret.reset_mock()

    funcopy.called = False
    funcopy.call_count = 0
    funcopy.call_args = None
    funcopy.call_args_list = _CallList()
    funcopy.method_calls = _CallList()
    funcopy.mock_calls = _CallList()

    funcopy.return_value = mock.return_value
    funcopy.side_effect = mock.side_effect
    funcopy._mock_children = mock._mock_children

    funcopy.assert_called_with = assert_called_with
    funcopy.assert_called_once_with = assert_called_once_with
    funcopy.assert_has_calls = assert_has_calls
    funcopy.assert_any_call = assert_any_call
    funcopy.reset_mock = reset_mock

    mock._mock_signature = funcopy


def _is_magic(name):
    return '__%s__' % name[2:-2] == name


class _SentinelObject(object):
    "A unique, named, sentinel object."
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'sentinel.%s' % self.name


class _Sentinel(object):
    """Access attributes to return a named object, usable as a sentinel."""
    def __init__(self):
        self._sentinels = {}

    def __getattr__(self, name):
        if name == '__bases__':
            # Without this help(mock) raises an exception
            raise AttributeError
        return self._sentinels.setdefault(name, _SentinelObject(name))


sentinel = _Sentinel()

DEFAULT = sentinel.DEFAULT


class OldStyleClass:
    pass
ClassType = type(OldStyleClass)


def _copy(value):
    if type(value) in (dict, list, tuple, set):
        return type(value)(value)
    return value


ClassTypes = (type,)
if not inPy3k:
    ClassTypes = (type, ClassType)

_allowed_names = set(
    [
        'return_value', '_mock_return_value', 'side_effect',
        '_mock_side_effect', '_mock_parent', '_mock_new_parent',
        '_mock_name', '_mock_new_name'
    ]
)


def _mock_signature_property(name):
    _allowed_names.add(name)
    _the_name = '_mock_' + name
    def _get(self, name=name, _the_name=_the_name):
        sig = self._mock_signature
        if sig is None:
            return getattr(self, _the_name)
        return getattr(sig, name)
    def _set(self, value, name=name, _the_name=_the_name):
        sig = self._mock_signature
        if sig is None:
            self.__dict__[_the_name] = value
        else:
            setattr(sig, name, value)

    return property(_get, _set)



class _CallList(list):

    def __contains__(self, value):
        if not isinstance(value, list):
            return list.__contains__(self, value)
        len_value = len(value)
        len_self = len(self)
        if len_value > len_self:
            return False

        for i in range(0, len_self - len_value + 1):
            sub_list = self[i:i+len_value]
            if sub_list == value:
                return True
        return False

    def __repr__(self):
        return pprint.pformat(list(self))


def _check_and_set_parent(parent, value, name, new_name):
    if not _is_instance_mock(value):
        return False
    if ((value._mock_name or value._mock_new_name) or
        (value._mock_parent is not None) or
        (value._mock_new_parent is not None)):
        return False

    _parent = parent
    while _parent is not None:
        # setting a mock (value) as a child or return value of itself
        # should not modify the mock
        if _parent is value:
            return False
        _parent = _parent._mock_new_parent

    if new_name:
        value._mock_new_parent = parent
        value._mock_new_name = new_name
    if name:
        value._mock_parent = parent
        value._mock_name = name
    return True



class Base(object):
    _mock_return_value = DEFAULT
    _mock_side_effect = None
    def __init__(self, *args, **kwargs):
        pass



class NonCallableMock(Base):
    """A non-callable version of `Mock`"""

    def __new__(cls, *args, **kw):
        # every instance has its own class
        # so we can create magic methods on the
        # class without stomping on other mocks
        new = type(cls.__name__, (cls,), {'__doc__': cls.__doc__})
        instance = object.__new__(new)
        return instance


    def __init__(
            self, spec=None, wraps=None, name=None, spec_set=None,
            parent=None, _spec_state=None, _new_name='', _new_parent=None,
            **kwargs
        ):
        if _new_parent is None:
            _new_parent = parent

        __dict__ = self.__dict__
        __dict__['_mock_parent'] = parent
        __dict__['_mock_name'] = name
        __dict__['_mock_new_name'] = _new_name
        __dict__['_mock_new_parent'] = _new_parent

        if spec_set is not None:
            spec = spec_set
            spec_set = True

        self._mock_add_spec(spec, spec_set)

        __dict__['_mock_children'] = {}
        __dict__['_mock_wraps'] = wraps
        __dict__['_mock_signature'] = None

        __dict__['_mock_called'] = False
        __dict__['_mock_call_args'] = None
        __dict__['_mock_call_count'] = 0
        __dict__['_mock_call_args_list'] = _CallList()
        __dict__['_mock_mock_calls'] = _CallList()

        __dict__['method_calls'] = _CallList()

        if kwargs:
            self.configure_mock(**kwargs)

        _super(NonCallableMock, self).__init__(
            spec, wraps, name, spec_set, parent,
            _spec_state
        )


    def attach_mock(self, mock, attribute):
        """
        Attach a mock as an attribute of this one, replacing its name and
        parent. Calls to the attached mock will be recorded in the
        `method_calls` and `mock_calls` attributes of this one."""
        mock._mock_parent = None
        mock._mock_new_parent = None
        mock._mock_name = ''
        mock._mock_new_name = None

        setattr(self, attribute, mock)


    def mock_add_spec(self, spec, spec_set=False):
        """Add a spec to a mock. `spec` can either be an object or a
        list of strings. Only attributes on the `spec` can be fetched as
        attributes from the mock.

        If `spec_set` is True then only attributes on the spec can be set."""
        self._mock_add_spec(spec, spec_set)


    def _mock_add_spec(self, spec, spec_set):
        _spec_class = None

        if spec is not None and not _is_list(spec):
            if isinstance(spec, ClassTypes):
                _spec_class = spec
            else:
                _spec_class = _get_class(spec)

            spec = dir(spec)

        __dict__ = self.__dict__
        __dict__['_spec_class'] = _spec_class
        __dict__['_spec_set'] = spec_set
        __dict__['_mock_methods'] = spec


    def __get_return_value(self):
        ret = self._mock_return_value
        if self._mock_signature is not None:
            ret = self._mock_signature.return_value

        if ret is DEFAULT:
            ret = self._get_child_mock(
                _new_parent=self, _new_name='()'
            )
            self.return_value = ret
        return ret


    def __set_return_value(self, value):
        if self._mock_signature is not None:
            self._mock_signature.return_value = value
        else:
            self._mock_return_value = value
            _check_and_set_parent(self, value, None, '()')

    __return_value_doc = "The value to be returned when the mock is called."
    return_value = property(__get_return_value, __set_return_value,
                            __return_value_doc)


    @property
    def __class__(self):
        if self._spec_class is None:
            return type(self)
        return self._spec_class

    called = _mock_signature_property('called')
    call_count = _mock_signature_property('call_count')
    call_args = _mock_signature_property('call_args')
    call_args_list = _mock_signature_property('call_args_list')
    mock_calls = _mock_signature_property('mock_calls')


    def __get_side_effect(self):
        sig = self._mock_signature
        if sig is None:
            return self._mock_side_effect
        return sig.side_effect

    def __set_side_effect(self, value):
        value = _try_iter(value)
        sig = self._mock_signature
        if sig is None:
            self._mock_side_effect = value
        else:
            sig.side_effect = value

    side_effect = property(__get_side_effect, __set_side_effect)


    def reset_mock(self):
        "Restore the mock object to its initial state."
        self.called = False
        self.call_args = None
        self.call_count = 0
        self.mock_calls = _CallList()
        self.call_args_list = _CallList()
        self.method_calls = _CallList()

        for child in self._mock_children.values():
            child.reset_mock()

        ret = self._mock_return_value
        if _is_instance_mock(ret) and ret is not self:
            ret.reset_mock()


    def configure_mock(self, **kwargs):
        """Set attributes on the mock through keyword arguments.

        Attributes plus return values and side effects can be set on child
        mocks using standard dot notation and unpacking a dictionary in the
        method call:

        >>> attrs = {'method.return_value': 3, 'other.side_effect': KeyError}
        >>> mock.configure_mock(**attrs)"""
        for arg, val in sorted(kwargs.items(),
                               # we sort on the number of dots so that
                               # attributes are set before we set attributes on
                               # attributes
                               key=lambda entry: entry[0].count('.')):
            args = arg.split('.')
            final = args.pop()
            obj = self
            for entry in args:
                obj = getattr(obj, entry)
            setattr(obj, final, val)


    def __getattr__(self, name):
        if name == '_mock_methods':
            raise AttributeError(name)
        elif self._mock_methods is not None:
            if name not in self._mock_methods or name in _all_magics:
                raise AttributeError("Mock object has no attribute %r" % name)
        elif _is_magic(name):
            raise AttributeError(name)

        result = self._mock_children.get(name)
        if result is None:
            wraps = None
            if self._mock_wraps is not None:
                # XXXX should we get the attribute without triggering code
                # execution?
                wraps = getattr(self._mock_wraps, name)

            result = self._get_child_mock(
                parent=self, name=name, wraps=wraps, _new_name=name,
                _new_parent=self
            )
            self._mock_children[name]  = result

        elif isinstance(result, _SpecState):
            result = create_autospec(
                result.spec, result.spec_set, result.instance,
                result.parent, result.name
            )
            self._mock_children[name]  = result

        return result


    def __repr__(self):
        _name_list = [self._mock_new_name]
        _parent = self._mock_new_parent
        last = self

        dot = '.'
        if _name_list == ['()']:
            dot = ''
        seen = set()
        while _parent is not None:
            last = _parent

            _name_list.append(_parent._mock_new_name + dot)
            dot = '.'
            if _parent._mock_new_name == '()':
                dot = ''

            _parent = _parent._mock_new_parent

            # use ids here so as not to call __hash__ on the mocks
            if id(_parent) in seen:
                break
            seen.add(id(_parent))

        _name_list = list(reversed(_name_list))
        _first = last._mock_name or 'mock'
        if len(_name_list) > 1:
            if _name_list[1] not in ('()', '().'):
                _first += '.'
        _name_list[0] = _first
        name = ''.join(_name_list)

        name_string = ''
        if name not in ('mock', 'mock.'):
            name_string = ' name=%r' % name

        spec_string = ''
        if self._spec_class is not None:
            spec_string = ' spec=%r'
            if self._spec_set:
                spec_string = ' spec_set=%r'
            spec_string = spec_string % self._spec_class.__name__
        return "<%s%s%s id='%s'>" % (
            type(self).__name__,
            name_string,
            spec_string,
            id(self)
        )


    def __dir__(self):
        """Filter the output of `dir(mock)` to only useful members.
        XXXX
        """
        extras = self._mock_methods or []
        from_type = dir(type(self))
        from_dict = list(self.__dict__)

        if FILTER_DIR:
            from_type = [e for e in from_type if not e.startswith('_')]
            from_dict = [e for e in from_dict if not e.startswith('_') or
                         _is_magic(e)]
        return sorted(set(extras + from_type + from_dict +
                          list(self._mock_children)))


    def __setattr__(self, name, value):
        if name in _allowed_names:
            # property setters go through here
            return object.__setattr__(self, name, value)
        elif (self._spec_set and self._mock_methods is not None and
            name not in self._mock_methods and
            name not in self.__dict__):
            raise AttributeError("Mock object has no attribute '%s'" % name)
        elif name in _unsupported_magics:
            msg = 'Attempting to set unsupported magic method %r.' % name
            raise AttributeError(msg)
        elif name in _all_magics:
            if self._mock_methods is not None and name not in self._mock_methods:
                raise AttributeError("Mock object has no attribute '%s'" % name)

            if not _is_instance_mock(value):
                setattr(type(self), name, _get_method(name, value))
                original = value
                real = lambda *args, **kw: original(self, *args, **kw)
                value = mocksignature(value, real, skipfirst=True)
            else:
                # only set _new_name and not name so that mock_calls is tracked
                # but not method calls
                _check_and_set_parent(self, value, None, name)
                setattr(type(self), name, value)
        else:
            if _check_and_set_parent(self, value, name, name):
                self._mock_children[name] = value
        return object.__setattr__(self, name, value)


    def __delattr__(self, name):
        if name in _all_magics and name in type(self).__dict__:
            delattr(type(self), name)
            if name not in self.__dict__:
                # for magic methods that are still MagicProxy objects and
                # not set on the instance itself
                return

        return object.__delattr__(self, name)


    def _format_mock_call_signature(self, args, kwargs):
        name = self._mock_name or 'mock'
        return _format_call_signature(name, args, kwargs)


    def _format_mock_failure_message(self, args, kwargs):
        message = 'Expected call: %s\nActual call: %s'
        expected_string = self._format_mock_call_signature(args, kwargs)
        call_args = self.call_args
        if len(call_args) == 3:
            call_args = call_args[1:]
        actual_string = self._format_mock_call_signature(*call_args)
        return message % (expected_string, actual_string)


    def assert_called_with(_mock_self, *args, **kwargs):
        """assert that the mock was called with the specified arguments.

        Raises an AssertionError if the args and keyword args passed in are
        different to the last call to the mock."""
        self = _mock_self
        if self.call_args is None:
            expected = self._format_mock_call_signature(args, kwargs)
            raise AssertionError('Expected call: %s\nNot called' % (expected,))

        if self.call_args != (args, kwargs):
            msg = self._format_mock_failure_message(args, kwargs)
            raise AssertionError(msg)


    def assert_called_once_with(_mock_self, *args, **kwargs):
        """assert that the mock was called exactly once and with the specified
        arguments."""
        self = _mock_self
        if not self.call_count == 1:
            msg = ("Expected to be called once. Called %s times." %
                   self.call_count)
            raise AssertionError(msg)
        return self.assert_called_with(*args, **kwargs)


    def assert_has_calls(self, calls, any_order=False):
        """assert the mock has been called with the specified calls.
        The `mock_calls` list is checked for the calls.

        If `any_order` is False (the default) then the calls must be
        sequential. There can be extra calls before or after the
        specified calls.

        If `any_order` is True then the calls can be in any order, but
        they must all appear in `mock_calls`."""
        if not any_order:
            if calls not in self.mock_calls:
                raise AssertionError(
                    'Calls not found.\nExpected: %r\n'
                    'Actual: %r' % (calls, self.mock_calls)
                )
            return

        all_calls = list(self.mock_calls)

        not_found = []
        for kall in calls:
            try:
                all_calls.remove(kall)
            except ValueError:
                not_found.append(kall)
        if not_found:
            raise AssertionError(
                '%r not all found in call list' % (tuple(not_found),)
            )


    def assert_any_call(self, *args, **kwargs):
        """assert the mock has been called with the specified arguments.

        The assert passes if the mock has *ever* been called, unlike
        `assert_called_with` and `assert_called_once_with` that only pass if
        the call is the most recent one."""
        kall = call(*args, **kwargs)
        if kall not in self.call_args_list:
            expected_string = self._format_mock_call_signature(args, kwargs)
            raise AssertionError(
                '%s call not found' % expected_string
            )


    def _get_child_mock(self, **kw):
        """Create the child mocks for attributes and return value.
        By default child mocks will be the same type as the parent.
        Subclasses of Mock may want to override this to customize the way
        child mocks are made.

        For non-callable mocks the callable variant will be used (rather than
        any custom subclass)."""
        _type = type(self)
        if not issubclass(_type, CallableMixin):
            if issubclass(_type, NonCallableMagicMock):
                klass = MagicMock
            elif issubclass(_type, NonCallableMock) :
                klass = Mock
        else:
            klass = _type.__mro__[1]
        return klass(**kw)



def _try_iter(obj):
    if obj is None:
        return obj
    if _is_exception(obj):
        return obj
    if _callable(obj):
        return obj
    try:
        return iter(obj)
    except TypeError:
        # XXXX backwards compatibility
        # but this will blow up on first call - so maybe we should fail early?
        return obj



class CallableMixin(Base):

    def __init__(self, spec=None, side_effect=None, return_value=DEFAULT,
                 wraps=None, name=None, spec_set=None, parent=None,
                 _spec_state=None, _new_name='', _new_parent=None, **kwargs):
        self.__dict__['_mock_return_value'] = return_value

        _super(CallableMixin, self).__init__(
            spec, wraps, name, spec_set, parent,
            _spec_state, _new_name, _new_parent, **kwargs
        )

        self.side_effect = side_effect


    def _mock_check_sig(self, *args, **kwargs):
        # stub method that can be replaced with one with a specific signature
        pass


    def __call__(_mock_self, *args, **kwargs):
        # can't use self in-case a function / method we are mocking uses self
        # in the signature
        _mock_self._mock_check_sig(*args, **kwargs)
        return _mock_self._mock_call(*args, **kwargs)


    def _mock_call(_mock_self, *args, **kwargs):
        self = _mock_self
        self.called = True
        self.call_count += 1
        self.call_args = _Call((args, kwargs), two=True)
        self.call_args_list.append(_Call((args, kwargs), two=True))

        _new_name = self._mock_new_name
        _new_parent = self._mock_new_parent
        self.mock_calls.append(_Call(('', args, kwargs)))

        seen = set()
        skip_next_dot = _new_name == '()'
        do_method_calls = self._mock_parent is not None
        name = self._mock_name
        while _new_parent is not None:
            this_mock_call = _Call((_new_name, args, kwargs))
            if _new_parent._mock_new_name:
                dot = '.'
                if skip_next_dot:
                    dot = ''

                skip_next_dot = False
                if _new_parent._mock_new_name == '()':
                    skip_next_dot = True

                _new_name = _new_parent._mock_new_name + dot + _new_name

            if do_method_calls:
                if _new_name == name:
                    this_method_call = this_mock_call
                else:
                    this_method_call = _Call((name, args, kwargs))
                _new_parent.method_calls.append(this_method_call)

                do_method_calls = _new_parent._mock_parent is not None
                if do_method_calls:
                    name = _new_parent._mock_name + '.' + name

            _new_parent.mock_calls.append(this_mock_call)
            _new_parent = _new_parent._mock_new_parent

            # use ids here so as not to call __hash__ on the mocks
            _new_parent_id = id(_new_parent)
            if _new_parent_id in seen:
                break
            seen.add(_new_parent_id)

        ret_val = DEFAULT
        effect = self.side_effect
        if effect is not None:
            if _is_exception(effect):
                raise effect

            if not _callable(effect):
                return next(effect)

            ret_val = effect(*args, **kwargs)
            if ret_val is DEFAULT:
                ret_val = self.return_value

        if (self._mock_wraps is not None and
             self._mock_return_value is DEFAULT):
            return self._mock_wraps(*args, **kwargs)
        if ret_val is DEFAULT:
            ret_val = self.return_value
        return ret_val



class Mock(CallableMixin, NonCallableMock):
    """
    Create a new `Mock` object. `Mock` takes several optional arguments
    that specify the behaviour of the Mock object:

    * `spec`: This can be either a list of strings or an existing object (a
      class or instance) that acts as the specification for the mock object. If
      you pass in an object then a list of strings is formed by calling dir on
      the object (excluding unsupported magic attributes and methods). Accessing
      any attribute not in this list will raise an `AttributeError`.

      If `spec` is an object (rather than a list of strings) then
      `mock.__class__` returns the class of the spec object. This allows mocks
      to pass `isinstance` tests.

    * `spec_set`: A stricter variant of `spec`. If used, attempting to *set*
      or get an attribute on the mock that isn't on the object passed as
      `spec_set` will raise an `AttributeError`.

    * `side_effect`: A function to be called whenever the Mock is called. See
      the `side_effect` attribute. Useful for raising exceptions or
      dynamically changing return values. The function is called with the same
      arguments as the mock, and unless it returns `DEFAULT`, the return
      value of this function is used as the return value.

      Alternatively `side_effect` can be an exception class or instance. In
      this case the exception will be raised when the mock is called.

      If `side_effect` is an iterable then each call to the mock will return
      the next value from the iterable.

    * `return_value`: The value returned when the mock is called. By default
      this is a new Mock (created on first access). See the
      `return_value` attribute.

    * `wraps`: Item for the mock object to wrap. If `wraps` is not None
      then calling the Mock will pass the call through to the wrapped object
      (returning the real result and ignoring `return_value`). Attribute
      access on the mock will return a Mock object that wraps the corresponding
      attribute of the wrapped object (so attempting to access an attribute that
      doesn't exist will raise an `AttributeError`).

      If the mock has an explicit `return_value` set then calls are not passed
      to the wrapped object and the `return_value` is returned instead.

    * `name`: If the mock has a name then it will be used in the repr of the
      mock. This can be useful for debugging. The name is propagated to child
      mocks.

    Mocks can also be called with arbitrary keyword arguments. These will be
    used to set attributes on the mock after it is created.
    """



def _dot_lookup(thing, comp, import_path):
    try:
        return getattr(thing, comp)
    except AttributeError:
        __import__(import_path)
        return getattr(thing, comp)


def _importer(target):
    components = target.split('.')
    import_path = components.pop(0)
    thing = __import__(import_path)

    for comp in components:
        import_path += ".%s" % comp
        thing = _dot_lookup(thing, comp, import_path)
    return thing


def _is_started(patcher):
    # XXXX horrible
    return hasattr(patcher, 'is_local')


class _patch(object):

    attribute_name = None

    def __init__(
            self, getter, attribute, new, spec, create,
            mocksignature, spec_set, autospec, new_callable, kwargs
        ):
        if new_callable is not None:
            if new is not DEFAULT:
                raise ValueError(
                    "Cannot use 'new' and 'new_callable' together"
                )
            if autospec is not False:
                raise ValueError(
                    "Cannot use 'autospec' and 'new_callable' together"
                )

        self.getter = getter
        self.attribute = attribute
        self.new = new
        self.new_callable = new_callable
        self.spec = spec
        self.create = create
        self.has_local = False
        self.mocksignature = mocksignature
        self.spec_set = spec_set
        self.autospec = autospec
        self.kwargs = kwargs
        self.additional_patchers = []


    def copy(self):
        patcher = _patch(
            self.getter, self.attribute, self.new, self.spec,
            self.create, self.mocksignature, self.spec_set,
            self.autospec, self.new_callable, self.kwargs
        )
        patcher.attribute_name = self.attribute_name
        patcher.additional_patchers = [
            p.copy() for p in self.additional_patchers
        ]
        return patcher


    def __call__(self, func):
        if isinstance(func, ClassTypes):
            return self.decorate_class(func)
        return self.decorate_callable(func)


    def decorate_class(self, klass):
        for attr in dir(klass):
            if not attr.startswith(patch.TEST_PREFIX):
                continue

            attr_value = getattr(klass, attr)
            if not hasattr(attr_value, "__call__"):
                continue

            patcher = self.copy()
            setattr(klass, attr, patcher(attr_value))
        return klass


    def decorate_callable(self, func):
        if hasattr(func, 'patchings'):
            func.patchings.append(self)
            return func

        @wraps(func)
        def patched(*args, **keywargs):
            # don't use a with here (backwards compatability with Python 2.4)
            extra_args = []
            entered_patchers = []

            # can't use try...except...finally because of Python 2.4
            # compatibility
            try:
                try:
                    for patching in patched.patchings:
                        arg = patching.__enter__()
                        entered_patchers.append(patching)
                        if patching.attribute_name is not None:
                            keywargs.update(arg)
                        elif patching.new is DEFAULT:
                            extra_args.append(arg)

                    args += tuple(extra_args)
                    return func(*args, **keywargs)
                except:
                    if (patching not in entered_patchers and
                        _is_started(patching)):
                        # the patcher may have been started, but an exception
                        # raised whilst entering one of its additional_patchers
                        entered_patchers.append(patching)
                    # re-raise the exception
                    raise
            finally:
                for patching in reversed(entered_patchers):
                    patching.__exit__()

        patched.patchings = [self]
        if hasattr(func, 'func_code'):
            # not in Python 3
            patched.compat_co_firstlineno = getattr(
                func, "compat_co_firstlineno",
                func.func_code.co_firstlineno
            )
        return patched


    def get_original(self):
        target = self.getter()
        name = self.attribute

        original = DEFAULT
        local = False

        try:
            original = target.__dict__[name]
        except (AttributeError, KeyError):
            original = getattr(target, name, DEFAULT)
        else:
            local = True

        if not self.create and original is DEFAULT:
            raise AttributeError(
                "%s does not have the attribute %r" % (target, name)
            )
        return original, local


    def __enter__(self):
        """Perform the patch."""
        new, spec, spec_set = self.new, self.spec, self.spec_set
        autospec, kwargs = self.autospec, self.kwargs
        new_callable = self.new_callable
        self.target = self.getter()

        original, local = self.get_original()

        if new is DEFAULT and autospec is False:
            inherit = False
            if spec_set == True:
                spec_set = original
            elif spec == True:
                # set spec to the object we are replacing
                spec = original

            if (spec or spec_set) is not None:
                if isinstance(original, ClassTypes):
                    # If we're patching out a class and there is a spec
                    inherit = True

            Klass = MagicMock
            _kwargs = {}
            if new_callable is not None:
                Klass = new_callable
            elif (spec or spec_set) is not None:
                if not _callable(spec or spec_set):
                    Klass = NonCallableMagicMock

            if spec is not None:
                _kwargs['spec'] = spec
            if spec_set is not None:
                _kwargs['spec_set'] = spec_set

            # add a name to mocks
            if (isinstance(Klass, type) and
                issubclass(Klass, NonCallableMock) and self.attribute):
                _kwargs['name'] = self.attribute

            _kwargs.update(kwargs)
            new = Klass(**_kwargs)

            if inherit and _is_instance_mock(new):
                # we can only tell if the instance should be callable if the
                # spec is not a list
                if (not _is_list(spec or spec_set) and not
                    _instance_callable(spec or spec_set)):
                    Klass = NonCallableMagicMock

                _kwargs.pop('name')
                new.return_value = Klass(_new_parent=new, _new_name='()',
                                         **_kwargs)
        elif autospec is not False:
            # spec is ignored, new *must* be default, spec_set is treated
            # as a boolean. Should we check spec is not None and that spec_set
            # is a bool? mocksignature should also not be used. Should we
            # check this?
            if new is not DEFAULT:
                raise TypeError(
                    "autospec creates the mock for you. Can't specify "
                    "autospec and new."
                )
            spec_set = bool(spec_set)
            if autospec is True:
                autospec = original

            new = create_autospec(autospec, spec_set=spec_set,
                                  _name=self.attribute, **kwargs)
        elif kwargs:
            # can't set keyword args when we aren't creating the mock
            # XXXX If new is a Mock we could call new.configure_mock(**kwargs)
            raise TypeError("Can't pass kwargs to a mock we aren't creating")

        new_attr = new
        if self.mocksignature:
            new_attr = mocksignature(original, new)

        self.temp_original = original
        self.is_local = local
        setattr(self.target, self.attribute, new_attr)
        if self.attribute_name is not None:
            extra_args = {}
            if self.new is DEFAULT:
                extra_args[self.attribute_name] =  new
            for patching in self.additional_patchers:
                arg = patching.__enter__()
                if patching.new is DEFAULT:
                    extra_args.update(arg)
            return extra_args

        return new


    def __exit__(self, *_):
        """Undo the patch."""
        if not _is_started(self):
            raise RuntimeError('stop called on unstarted patcher')

        if self.is_local and self.temp_original is not DEFAULT:
            setattr(self.target, self.attribute, self.temp_original)
        else:
            delattr(self.target, self.attribute)
            if not self.create and not hasattr(self.target, self.attribute):
                # needed for proxy objects like django settings
                setattr(self.target, self.attribute, self.temp_original)

        del self.temp_original
        del self.is_local
        del self.target
        for patcher in reversed(self.additional_patchers):
            if _is_started(patcher):
                patcher.__exit__()

    start = __enter__
    stop = __exit__



def _get_target(target):
    try:
        target, attribute = target.rsplit('.', 1)
    except (TypeError, ValueError):
        raise TypeError("Need a valid target to patch. You supplied: %r" %
                        (target,))
    getter = lambda: _importer(target)
    return getter, attribute


def _patch_object(
        target, attribute, new=DEFAULT, spec=None,
        create=False, mocksignature=False, spec_set=None, autospec=False,
        new_callable=None, **kwargs
    ):
    """
    patch.object(target, attribute, new=DEFAULT, spec=None, create=False,
                 mocksignature=False, spec_set=None, autospec=False,
                 new_callable=None, **kwargs)

    patch the named member (`attribute`) on an object (`target`) with a mock
    object.

    `patch.object` can be used as a decorator, class decorator or a context
    manager. Arguments `new`, `spec`, `create`, `mocksignature`, `spec_set`,
    `autospec` and `new_callable` have the same meaning as for `patch`. Like
    `patch`, `patch.object` takes arbitrary keyword arguments for configuring
    the mock object it creates.

    When used as a class decorator `patch.object` honours `patch.TEST_PREFIX`
    for choosing which methods to wrap.
    """
    getter = lambda: target
    return _patch(
        getter, attribute, new, spec, create, mocksignature,
        spec_set, autospec, new_callable, kwargs
    )


def _patch_multiple(target, spec=None, create=False,
        mocksignature=False, spec_set=None, autospec=False,
        new_callable=None, **kwargs
    ):
    """Perform multiple patches in a single call. It takes the object to be
    patched (either as an object or a string to fetch the object by importing)
    and keyword arguments for the patches::

        with patch.multiple(settings, FIRST_PATCH='one', SECOND_PATCH='two'):
            ...

    Use `DEFAULT` as the value if you want `patch.multiple` to create
    mocks for you. In this case the created mocks are passed into a decorated
    function by keyword, and a dictionary is returned when `patch.multiple` is
    used as a context manager.

    `patch.multiple` can be used as a decorator, class decorator or a context
    manager. The arguments `spec`, `spec_set`, `create`, `mocksignature`,
    `autospec` and `new_callable` have the same meaning as for `patch`. These
    arguments will be applied to *all* patches done by `patch.multiple`.

    When used as a class decorator `patch.multiple` honours `patch.TEST_PREFIX`
    for choosing which methods to wrap.
    """
    if type(target) in (unicode, str):
        getter = lambda: _importer(target)
    else:
        getter = lambda: target

    if not kwargs:
        raise ValueError(
            'Must supply at least one keyword argument with patch.multiple'
        )
    # need to wrap in a list for python 3, where items is a view
    items = list(kwargs.items())
    attribute, new = items[0]
    patcher = _patch(
        getter, attribute, new, spec, create, mocksignature, spec_set,
        autospec, new_callable, {}
    )
    patcher.attribute_name = attribute
    for attribute, new in items[1:]:
        this_patcher = _patch(
            getter, attribute, new, spec, create, mocksignature, spec_set,
            autospec, new_callable, {}
        )
        this_patcher.attribute_name = attribute
        patcher.additional_patchers.append(this_patcher)
    return patcher


def patch(
        target, new=DEFAULT, spec=None, create=False,
        mocksignature=False, spec_set=None, autospec=False,
        new_callable=None, **kwargs
    ):
    """
    `patch` acts as a function decorator, class decorator or a context
    manager. Inside the body of the function or with statement, the `target`
    (specified in the form `'package.module.ClassName'`) is patched
    with a `new` object. When the function/with statement exits the patch is
    undone.

    The `target` is imported and the specified attribute patched with the new
    object, so it must be importable from the environment you are calling the
    decorator from. The target is imported when the decorated function is
    executed, not at decoration time.

    If `new` is omitted, then a new `MagicMock` is created and passed in as an
    extra argument to the decorated function.

    The `spec` and `spec_set` keyword arguments are passed to the `MagicMock`
    if patch is creating one for you.

    In addition you can pass `spec=True` or `spec_set=True`, which causes
    patch to pass in the object being mocked as the spec/spec_set object.

    `new_callable` allows you to specify a different class, or callable object,
    that will be called to create the `new` object. By default `MagicMock` is
    used.

    A more powerful form of `spec` is `autospec`. If you set `autospec=True`
    then the mock with be created with a spec from the object being replaced.
    All attributes of the mock will also have the spec of the corresponding
    attribute of the object being replaced. Methods and functions being mocked
    will have their arguments checked and will raise a `TypeError` if they are
    called with the wrong signature (similar to `mocksignature`). For mocks
    replacing a class, their return value (the 'instance') will have the same
    spec as the class.

    Instead of `autospec=True` you can pass `autospec=some_object` to use an
    arbitrary object as the spec instead of the one being replaced.

    If `mocksignature` is True then the patch will be done with a function
    created by mocking the one being replaced. If the object being replaced is
    a class then the signature of `__init__` will be copied. If the object
    being replaced is a callable object then the signature of `__call__` will
    be copied.

    By default `patch` will fail to replace attributes that don't exist. If
    you pass in `create=True`, and the attribute doesn't exist, patch will
    create the attribute for you when the patched function is called, and
    delete it again afterwards. This is useful for writing tests against
    attributes that your production code creates at runtime. It is off by by
    default because it can be dangerous. With it switched on you can write
    passing tests against APIs that don't actually exist!

    Patch can be used as a `TestCase` class decorator. It works by
    decorating each test method in the class. This reduces the boilerplate
    code when your test methods share a common patchings set. `patch` finds
    tests by looking for method names that start with `patch.TEST_PREFIX`.
    By default this is `test`, which matches the way `unittest` finds tests.
    You can specify an alternative prefix by setting `patch.TEST_PREFIX`.

    Patch can be used as a context manager, with the with statement. Here the
    patching applies to the indented block after the with statement. If you
    use "as" then the patched object will be bound to the name after the
    "as"; very useful if `patch` is creating a mock object for you.

    `patch` takes arbitrary keyword arguments. These will be passed to
    the `Mock` (or `new_callable`) on construction.

    `patch.dict(...)`, `patch.multiple(...)` and `patch.object(...)` are
    available for alternate use-cases.
    """
    getter, attribute = _get_target(target)
    return _patch(
        getter, attribute, new, spec, create, mocksignature,
        spec_set, autospec, new_callable, kwargs
    )


class _patch_dict(object):
    """
    Patch a dictionary, or dictionary like object, and restore the dictionary
    to its original state after the test.

    `in_dict` can be a dictionary or a mapping like container. If it is a
    mapping then it must at least support getting, setting and deleting items
    plus iterating over keys.

    `in_dict` can also be a string specifying the name of the dictionary, which
    will then be fetched by importing it.

    `values` can be a dictionary of values to set in the dictionary. `values`
    can also be an iterable of `(key, value)` pairs.

    If `clear` is True then the dictionary will be cleared before the new
    values are set.

    `patch.dict` can also be called with arbitrary keyword arguments to set
    values in the dictionary::

        with patch.dict('sys.modules', mymodule=Mock(), other_module=Mock()):
            ...

    `patch.dict` can be used as a context manager, decorator or class
    decorator. When used as a class decorator `patch.dict` honours
    `patch.TEST_PREFIX` for choosing which methods to wrap.
    """

    def __init__(self, in_dict, values=(), clear=False, **kwargs):
        if isinstance(in_dict, basestring):
            in_dict = _importer(in_dict)
        self.in_dict = in_dict
        # support any argument supported by dict(...) constructor
        self.values = dict(values)
        self.values.update(kwargs)
        self.clear = clear
        self._original = None


    def __call__(self, f):
        if isinstance(f, ClassTypes):
            return self.decorate_class(f)
        @wraps(f)
        def _inner(*args, **kw):
            self._patch_dict()
            try:
                return f(*args, **kw)
            finally:
                self._unpatch_dict()

        return _inner


    def decorate_class(self, klass):
        for attr in dir(klass):
            attr_value = getattr(klass, attr)
            if (attr.startswith(patch.TEST_PREFIX) and
                 hasattr(attr_value, "__call__")):
                decorator = _patch_dict(self.in_dict, self.values, self.clear)
                decorated = decorator(attr_value)
                setattr(klass, attr, decorated)
        return klass


    def __enter__(self):
        """Patch the dict."""
        self._patch_dict()


    def _patch_dict(self):
        values = self.values
        in_dict = self.in_dict
        clear = self.clear

        try:
            original = in_dict.copy()
        except AttributeError:
            # dict like object with no copy method
            # must support iteration over keys
            original = {}
            for key in in_dict:
                original[key] = in_dict[key]
        self._original = original

        if clear:
            _clear_dict(in_dict)

        try:
            in_dict.update(values)
        except AttributeError:
            # dict like object with no update method
            for key in values:
                in_dict[key] = values[key]


    def _unpatch_dict(self):
        in_dict = self.in_dict
        original = self._original

        _clear_dict(in_dict)

        try:
            in_dict.update(original)
        except AttributeError:
            for key in original:
                in_dict[key] = original[key]


    def __exit__(self, *args):
        """Unpatch the dict."""
        self._unpatch_dict()
        return False

    start = __enter__
    stop = __exit__


def _clear_dict(in_dict):
    try:
        in_dict.clear()
    except AttributeError:
        keys = list(in_dict)
        for key in keys:
            del in_dict[key]


patch.object = _patch_object
patch.dict = _patch_dict
patch.multiple = _patch_multiple
patch.TEST_PREFIX = 'test'

magic_methods = (
    "lt le gt ge eq ne "
    "getitem setitem delitem "
    "len contains iter "
    "hash str sizeof "
    "enter exit "
    "divmod neg pos abs invert "
    "complex int float index "
    "trunc floor ceil "
)

numerics = "add sub mul div floordiv mod lshift rshift and xor or pow "
inplace = ' '.join('i%s' % n for n in numerics.split())
right = ' '.join('r%s' % n for n in numerics.split())
extra = ''
if inPy3k:
    extra = 'bool next '
else:
    extra = 'unicode long nonzero oct hex truediv rtruediv '

# not including __prepare__, __instancecheck__, __subclasscheck__
# (as they are metaclass methods)
# __del__ is not supported at all as it causes problems if it exists

_non_defaults = set('__%s__' % method for method in [
    'cmp', 'getslice', 'setslice', 'coerce', 'subclasses',
    'format', 'get', 'set', 'delete', 'reversed',
    'missing', 'reduce', 'reduce_ex', 'getinitargs',
    'getnewargs', 'getstate', 'setstate', 'getformat',
    'setformat', 'repr', 'dir'
])


def _get_method(name, func):
    "Turns a callable object (like a mock) into a real function"
    def method(self, *args, **kw):
        return func(self, *args, **kw)
    method.__name__ = name
    return method


_magics = set(
    '__%s__' % method for method in
    ' '.join([magic_methods, numerics, inplace, right, extra]).split()
)

_all_magics = _magics | _non_defaults

_unsupported_magics = set([
    '__getattr__', '__setattr__',
    '__init__', '__new__', '__prepare__'
    '__instancecheck__', '__subclasscheck__',
    '__del__'
])

_calculate_return_value = {
    '__hash__': lambda self: object.__hash__(self),
    '__str__': lambda self: object.__str__(self),
    '__sizeof__': lambda self: object.__sizeof__(self),
    '__unicode__': lambda self: unicode(object.__str__(self)),
}

_return_values = {
    '__int__': 1,
    '__contains__': False,
    '__len__': 0,
    '__exit__': False,
    '__complex__': 1j,
    '__float__': 1.0,
    '__bool__': True,
    '__nonzero__': True,
    '__oct__': '1',
    '__hex__': '0x1',
    '__long__': long(1),
    '__index__': 1,
}


def _get_eq(self):
    def __eq__(other):
        ret_val = self.__eq__._mock_return_value
        if ret_val is not DEFAULT:
            return ret_val
        return self is other
    return __eq__

def _get_ne(self):
    def __ne__(other):
        if self.__ne__._mock_return_value is not DEFAULT:
            return DEFAULT
        return self is not other
    return __ne__

def _get_iter(self):
    def __iter__():
        ret_val = self.__iter__._mock_return_value
        if ret_val is DEFAULT:
            return iter([])
        # if ret_val was already an iterator, then calling iter on it should
        # return the iterator unchanged
        return iter(ret_val)
    return __iter__

_side_effect_methods = {
    '__eq__': _get_eq,
    '__ne__': _get_ne,
    '__iter__': _get_iter,
}



def _set_return_value(mock, method, name):
    fixed = _return_values.get(name, DEFAULT)
    if fixed is not DEFAULT:
        method.return_value = fixed
        return

    return_calulator = _calculate_return_value.get(name)
    if return_calulator is not None:
        try:
            return_value = return_calulator(mock)
        except AttributeError:
            # XXXX why do we return AttributeError here?
            #      set it as a side_effect instead?
            return_value = AttributeError(name)
        method.return_value = return_value
        return

    side_effector = _side_effect_methods.get(name)
    if side_effector is not None:
        method.side_effect = side_effector(mock)



class MagicMixin(object):
    def __init__(self, *args, **kw):
        _super(MagicMixin, self).__init__(*args, **kw)
        self._mock_set_magics()


    def _mock_set_magics(self):
        these_magics = _magics

        if self._mock_methods is not None:
            these_magics = _magics.intersection(self._mock_methods)

            remove_magics = set()
            remove_magics = _magics - these_magics

            for entry in remove_magics:
                if entry in type(self).__dict__:
                    # remove unneeded magic methods
                    delattr(self, entry)

        # don't overwrite existing attributes if called a second time
        these_magics = these_magics - set(type(self).__dict__)

        _type = type(self)
        for entry in these_magics:
            setattr(_type, entry, MagicProxy(entry, self))



class NonCallableMagicMock(MagicMixin, NonCallableMock):
    """A version of `MagicMock` that isn't callable."""
    def mock_add_spec(self, spec, spec_set=False):
        """Add a spec to a mock. `spec` can either be an object or a
        list of strings. Only attributes on the `spec` can be fetched as
        attributes from the mock.

        If `spec_set` is True then only attributes on the spec can be set."""
        self._mock_add_spec(spec, spec_set)
        self._mock_set_magics()



class MagicMock(MagicMixin, Mock):
    """
    MagicMock is a subclass of Mock with default implementations
    of most of the magic methods. You can use MagicMock without having to
    configure the magic methods yourself.

    If you use the `spec` or `spec_set` arguments then *only* magic
    methods that exist in the spec will be created.

    Attributes and the return value of a `MagicMock` will also be `MagicMocks`.
    """
    def mock_add_spec(self, spec, spec_set=False):
        """Add a spec to a mock. `spec` can either be an object or a
        list of strings. Only attributes on the `spec` can be fetched as
        attributes from the mock.

        If `spec_set` is True then only attributes on the spec can be set."""
        self._mock_add_spec(spec, spec_set)
        self._mock_set_magics()



class MagicProxy(object):
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent

    def __call__(self, *args, **kwargs):
        m = self.create_mock()
        return m(*args, **kwargs)

    def create_mock(self):
        entry = self.name
        parent = self.parent
        m = parent._get_child_mock(name=entry, _new_name=entry,
                                   _new_parent=parent)
        setattr(parent, entry, m)
        _set_return_value(parent, m, entry)
        return m

    def __get__(self, obj, _type=None):
        return self.create_mock()



class _ANY(object):
    "A helper object that compares equal to everything."

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    def __repr__(self):
        return '<ANY>'

ANY = _ANY()



def _format_call_signature(name, args, kwargs):
    message = '%s(%%s)' % name
    formatted_args = ''
    args_string = ', '.join([repr(arg) for arg in args])
    kwargs_string = ', '.join([
        '%s=%r' % (key, value) for key, value in kwargs.items()
    ])
    if args_string:
        formatted_args = args_string
    if kwargs_string:
        if formatted_args:
            formatted_args += ', '
        formatted_args += kwargs_string

    return message % formatted_args



class _Call(tuple):
    """
    A tuple for holding the results of a call to a mock, either in the form
    `(args, kwargs)` or `(name, args, kwargs)`.

    If args or kwargs are empty then a call tuple will compare equal to
    a tuple without those values. This makes comparisons less verbose::

        _Call(('name', (), {})) == ('name',)
        _Call(('name', (1,), {})) == ('name', (1,))
        _Call(((), {'a': 'b'})) == ({'a': 'b'},)

    The `_Call` object provides a useful shortcut for comparing with call::

        _Call(((1, 2), {'a': 3})) == call(1, 2, a=3)
        _Call(('foo', (1, 2), {'a': 3})) == call.foo(1, 2, a=3)

    If the _Call has no name then it will match any name.
    """
    def __new__(cls, value=(), name=None, parent=None, two=False,
                from_kall=True):
        name = ''
        args = ()
        kwargs = {}
        _len = len(value)
        if _len == 3:
            name, args, kwargs = value
        elif _len == 2:
            first, second = value
            if isinstance(first, basestring):
                name = first
                if isinstance(second, tuple):
                    args = second
                else:
                    kwargs = second
            else:
                args, kwargs = first, second
        elif _len == 1:
            value, = value
            if isinstance(value, basestring):
                name = value
            elif isinstance(value, tuple):
                args = value
            else:
                kwargs = value

        if two:
            return tuple.__new__(cls, (args, kwargs))

        return tuple.__new__(cls, (name, args, kwargs))


    def __init__(self, value=(), name=None, parent=None, two=False,
                 from_kall=True):
        self.name = name
        self.parent = parent
        self.from_kall = from_kall


    def __eq__(self, other):
        if other is ANY:
            return True
        try:
            len_other = len(other)
        except TypeError:
            return False

        self_name = ''
        if len(self) == 2:
            self_args, self_kwargs = self
        else:
            self_name, self_args, self_kwargs = self

        other_name = ''
        if len_other == 0:
            other_args, other_kwargs = (), {}
        elif len_other == 3:
            other_name, other_args, other_kwargs = other
        elif len_other == 1:
            value, = other
            if isinstance(value, tuple):
                other_args = value
                other_kwargs = {}
            elif isinstance(value, basestring):
                other_name = value
                other_args, other_kwargs = (), {}
            else:
                other_args = ()
                other_kwargs = value
        else:
            # len 2
            # could be (name, args) or (name, kwargs) or (args, kwargs)
            first, second = other
            if isinstance(first, basestring):
                other_name = first
                if isinstance(second, tuple):
                    other_args, other_kwargs = second, {}
                else:
                    other_args, other_kwargs = (), second
            else:
                other_args, other_kwargs = first, second

        if self_name and other_name != self_name:
            return False

        # this order is important for ANY to work!
        return (other_args, other_kwargs) == (self_args, self_kwargs)


    def __ne__(self, other):
        return not self.__eq__(other)


    def __call__(self, *args, **kwargs):
        if self.name is None:
            return _Call(('', args, kwargs), name='()')

        name = self.name + '()'
        return _Call((self.name, args, kwargs), name=name, parent=self)


    def __getattr__(self, attr):
        if self.name is None:
            return _Call(name=attr, from_kall=False)
        name = '%s.%s' % (self.name, attr)
        return _Call(name=name, parent=self, from_kall=False)


    def __repr__(self):
        if not self.from_kall:
            name = self.name or 'call'
            if name.startswith('()'):
                name = 'call%s' % name
            return name

        if len(self) == 2:
            name = 'call'
            args, kwargs = self
        else:
            name, args, kwargs = self
            if not name:
                name = 'call'
            elif not name.startswith('()'):
                name = 'call.%s' % name
            else:
                name = 'call%s' % name
        return _format_call_signature(name, args, kwargs)


    def call_list(self):
        """For a call object that represents multiple calls, `call_list`
        returns a list of all the intermediate calls as well as the
        final call."""
        vals = []
        thing = self
        while thing is not None:
            if thing.from_kall:
                vals.append(thing)
            thing = thing.parent
        return _CallList(reversed(vals))


call = _Call(from_kall=False)



def create_autospec(spec, spec_set=False, instance=False, _parent=None,
                    _name=None, **kwargs):
    """Create a mock object using another object as a spec. Attributes on the
    mock will use the corresponding attribute on the `spec` object as their
    spec.

    Functions or methods being mocked will have their arguments checked in a
    similar way to `mocksignature` to check that they are called with the
    correct signature.

    If `spec_set` is True then attempting to set attributes that don't exist
    on the spec object will raise an `AttributeError`.

    If a class is used as a spec then the return value of the mock (the
    instance of the class) will have the same spec. You can use a class as the
    spec for an instance object by passing `instance=True`. The returned mock
    will only be callable if instances of the mock are callable.

    `create_autospec` also takes arbitrary keyword arguments that are passed to
    the constructor of the created mock."""
    if _is_list(spec):
        # can't pass a list instance to the mock constructor as it will be
        # interpreted as a list of strings
        spec = type(spec)

    is_type = isinstance(spec, ClassTypes)

    _kwargs = {'spec': spec}
    if spec_set:
        _kwargs = {'spec_set': spec}
    elif spec is None:
        # None we mock with a normal mock without a spec
        _kwargs = {}

    _kwargs.update(kwargs)

    Klass = MagicMock
    if type(spec) in DescriptorTypes:
        # descriptors don't have a spec
        # because we don't know what type they return
        _kwargs = {}
    elif not _callable(spec):
        Klass = NonCallableMagicMock
    elif is_type and instance and not _instance_callable(spec):
        Klass = NonCallableMagicMock

    _new_name = _name
    if _parent is None:
        # for a top level object no _new_name should be set
        _new_name = ''

    mock = Klass(parent=_parent, _new_parent=_parent, _new_name=_new_name,
                 name=_name, **_kwargs)

    if isinstance(spec, FunctionTypes):
        # should only happen at the top level because we don't
        # recurse for functions
        mock = _set_signature(mock, spec)
    else:
        _check_signature(spec, mock, is_type, instance)

    if _parent is not None and not instance:
        _parent._mock_children[_name] = mock

    if is_type and not instance and 'return_value' not in kwargs:
        # XXXX could give a name to the return_value mock?
        mock.return_value = create_autospec(spec, spec_set, instance=True,
                                            _name='()', _parent=mock)

    for entry in dir(spec):
        if _is_magic(entry):
            # MagicMock already does the useful magic methods for us
            continue

        if isinstance(spec, FunctionTypes) and entry in FunctionAttributes:
            # allow a mock to actually be a function from mocksignature
            continue

        # XXXX do we need a better way of getting attributes without
        # triggering code execution (?) Probably not - we need the actual
        # object to mock it so we would rather trigger a property than mock
        # the property descriptor. Likewise we want to mock out dynamically
        # provided attributes.
        # XXXX what about attributes that raise exceptions on being fetched
        # we could be resilient against it, or catch and propagate the
        # exception when the attribute is fetched from the mock
        original = getattr(spec, entry)

        kwargs = {'spec': original}
        if spec_set:
            kwargs = {'spec_set': original}

        if not isinstance(original, FunctionTypes):
            new = _SpecState(original, spec_set, mock, entry, instance)
            mock._mock_children[entry] = new
        else:
            parent = mock
            if isinstance(spec, FunctionTypes):
                parent = mock.mock

            new = MagicMock(parent=parent, name=entry, _new_name=entry,
                            _new_parent=parent, **kwargs)
            mock._mock_children[entry] = new
            skipfirst = _must_skip(spec, entry, is_type)
            _check_signature(original, new, skipfirst=skipfirst)

        # so functions created with mocksignature become instance attributes,
        # *plus* their underlying mock exists in _mock_children of the parent
        # mock. Adding to _mock_children may be unnecessary where we are also
        # setting as an instance attribute?
        if isinstance(new, FunctionTypes):
            setattr(mock, entry, new)

    return mock


def _must_skip(spec, entry, is_type):
    if not isinstance(spec, ClassTypes):
        if entry in getattr(spec, '__dict__', {}):
            # instance attribute - shouldn't skip
            return False
        # can't use type because of old style classes
        spec = spec.__class__
    if not hasattr(spec, '__mro__'):
        # old style class: can't have descriptors anyway
        return is_type

    for klass in spec.__mro__:
        result = klass.__dict__.get(entry, DEFAULT)
        if result is DEFAULT:
            continue
        if isinstance(result, (staticmethod, classmethod)):
            return False
        return is_type

    # shouldn't get here unless function is a dynamically provided attribute
    # XXXX untested behaviour
    return is_type


def _get_class(obj):
    try:
        return obj.__class__
    except AttributeError:
        # in Python 2, _sre.SRE_Pattern objects have no __class__
        return type(obj)


class _SpecState(object):

    def __init__(self, spec, spec_set=False, parent=None,
                 name=None, ids=None, instance=False):
        self.spec = spec
        self.ids = ids
        self.spec_set = spec_set
        self.parent = parent
        self.instance = instance
        self.name = name


FunctionTypes = (
    # python function
    type(create_autospec),
    # instance method
    type(ANY.__eq__),
    # unbound method
    type(_ANY.__eq__),
)

FunctionAttributes = set([
    'func_closure',
    'func_code',
    'func_defaults',
    'func_dict',
    'func_doc',
    'func_globals',
    'func_name',
])

########NEW FILE########
__FILENAME__ = testApplication
import unittest
from test.mock import patch
import lizard
from lizard import lizard_main
import os


@patch('lizard.md5_hash_file')
@patch('lizard.open', create=True)
@patch.object(os, 'walk')
@patch.object(lizard, 'print_result')
class TestApplication(unittest.TestCase):

    def testEmptyResult(self, print_result, os_walk, mock_open, _):

        def check_empty_result(result, options):
            self.assertEqual([], list(result))

        os_walk.return_value = [('.', [], [])]
        print_result.side_effect = check_empty_result
        lizard_main(['lizard'])

    def testFilesWithFunction(self, print_result, os_walk, mock_open, _):
        def check_result(result, options):
            fileInfos = list(result)
            self.assertEqual(1, len(fileInfos))
            self.assertEqual('foo', fileInfos[0].function_list[0].name)
        os_walk.return_value = [('.', [], ['a.cpp'])]
        mock_open.return_value.read.return_value = "void foo(){}"
        print_result.side_effect = check_result
        lizard_main(['lizard'])


class IntegrationTests(unittest.TestCase):

    def setUp(self):
        self.source_code = '''
        void foo() {
        #if
        #endif
            if(bar)
            {
            }
            switch(bar)
            {
              case 0: break;
              case 1: break;
              case 2: break;
              case 3: break;
            }
        }
        '''

    @patch('lizard.open', create=True)
    @patch.object(lizard, 'print_result')
    def run_with_mocks(self, argv, src, print_result, mock_open):
        def store_result(result, options):
            self.fileInfos = list(result)
        mock_open.return_value.read.return_value = src
        print_result.side_effect = store_result
        lizard_main(argv)
        return self.fileInfos

    @patch('lizard.md5_hash_file')
    @patch.object(os, 'walk')
    def runApplicationWithArgv(self, argv, os_walk, _):
        os_walk.return_value = [('.', [], ['a.cpp'])]
        return self.run_with_mocks(argv, self.source_code)

    def test_with_preprocessor_counted_in_CCN(self):
        self.runApplicationWithArgv(['lizard'])
        self.assertEqual(7, self.fileInfos[0].function_list[0].cyclomatic_complexity)

    def test_using_the_WordCount_plugin(self):
        self.runApplicationWithArgv(['lizard', '-EWordCount'])
        self.assertEqual(1, self.fileInfos[0].wordCount["foo"])

    def test_using_modified_ccn(self):
        self.runApplicationWithArgv(['lizard', '--modified'])
        self.assertEqual(4, self.fileInfos[0].function_list[0].cyclomatic_complexity)

########NEW FILE########
__FILENAME__ = testBasicFunctionInfo
import unittest
from test.mock import Mock, patch
from .testHelpers import get_cpp_fileinfo, get_cpp_function_list

class Test_Token_Count(unittest.TestCase):

    def test_non_function_tokens_are_counted(self):
        fileinfo = get_cpp_fileinfo("int i, j;")
        self.assertEqual(5, fileinfo.token_count)

    def test_include_is_counted_as_2(self):
        fileinfo = get_cpp_fileinfo("#include \"abc.h\"")
        self.assertEqual(2, fileinfo.token_count)

    def test_include_with_lg_and_gg_is_counted_as_2(self):
        fileinfo = get_cpp_fileinfo("#include <abc.h>")
        self.assertEqual(2, fileinfo.token_count)

    def test_one_function_with_no_token(self):
        result = get_cpp_function_list("int fun(){}")
        self.assertEqual(5, result[0].token_count)

    def test_one_function_with_one_token(self):
        result = get_cpp_function_list("int fun(){;}")
        self.assertEqual(6, result[0].token_count)

    def test_one_function_with_content(self):
        result = get_cpp_function_list("int fun(){if(a){xx;}}")
        self.assertEqual(13, result[0].token_count)

    def test_one_function_with_comments_only(self):
        result = get_cpp_function_list("int fun(){/**/}")
        self.assertEqual(5, result[0].token_count)

class TestNLOC(unittest.TestCase):

    def test_one_function_with_content(self):
        result = get_cpp_function_list("int fun(){if(a){xx;}}")
        self.assertEqual(1, result[0].nloc)

    def test_nloc_of_empty_function(self):
        result = get_cpp_function_list("int fun(){}")
        self.assertEqual(1, result[0].nloc)

    def test_nloc(self):
        result = get_cpp_function_list("int fun(){\n\n\n}")
        self.assertEqual(2, result[0].nloc)

    def test_nloc_with_new_line_in_comment(self):
        result = get_cpp_function_list("int fun(){/*\n*/}")
        self.assertEqual(2, result[0].nloc)

    def test_nloc_with_comment_between_new_lines(self):
        result = get_cpp_function_list("int fun(){\n/*\n*/\n}")
        self.assertEqual(2, result[0].nloc)

    def test_nloc2(self):
        result = get_cpp_function_list("int fun(){aa();\n\n\n\nbb();\n\n\n}")
        self.assertEqual(3, result[0].nloc)
        self.assertEqual(1, result[0].start_line)
        self.assertEqual(8, result[0].end_line)

    def check_file_nloc(self, expect, source):
        fileinfo = get_cpp_fileinfo(source)
        self.assertEqual(expect, fileinfo.nloc)

    def test_last_line_without_return_should_be_counted_in_fileinfo(self):
        self.check_file_nloc(1, ";\n")
        self.check_file_nloc(2, ";\n\n;\n")
        self.check_file_nloc(2, ";\n;")
        self.check_file_nloc(1, "fun(){}")
        self.check_file_nloc(1, "fun(){};\n")


class TestLOC(unittest.TestCase):

    def test_having_empty_line(self):
        result = get_cpp_function_list("\nint fun(){}")
        self.assertEqual(2, result[0].start_line)

    def test_newline_in_macro(self):
        result = get_cpp_function_list("#define a\\\nb\nint fun(){}")
        self.assertEqual(3, result[0].start_line)

    def test_having_empty_line_that_has_spaces(self):
        result = get_cpp_function_list("  \nint fun(){}")
        self.assertEqual(2, result[0].start_line)

    def test_having_multiple_line_comments(self):
        result = get_cpp_function_list('''int fun(){
        /*2
          3
          4*/
                }''')
        self.assertEqual(5, result[0].end_line)


########NEW FILE########
__FILENAME__ = testCAndCPP
import unittest
from lizard import CLikeReader, CLikeReader
from mock import Mock
from .testHelpers import get_cpp_fileinfo, get_cpp_function_list

class Test_C_Token_extension(unittest.TestCase):

    def test_connecting_marcro(self):
        extended = CLikeReader(None).preprocess(("a##b c", ))
        #tbd

class Test_c_cpp_lizard(unittest.TestCase):
    def test_empty(self):
        result = get_cpp_function_list("")
        self.assertEqual(0, len(result))

    def test_no_function(self):
        result = get_cpp_function_list("#include <stdio.h>\n")
        self.assertEqual(0, len(result))

    def test_one_function(self):
        result = get_cpp_function_list("int fun(){}")
        self.assertEqual(1, len(result))
        self.assertEqual("fun", result[0].name)
    
    def test_two_function(self):
        result = get_cpp_function_list("int fun(){}\nint fun1(){}\n")
        self.assertEqual(2, len(result))
        self.assertEqual("fun", result[0].name)
        self.assertEqual("fun1", result[1].name)
        self.assertEqual(1, result[0].start_line)
        self.assertEqual(1, result[0].end_line)
        self.assertEqual(2, result[1].start_line)
        self.assertEqual(2, result[1].end_line)
    
    def test_function_with_content(self):
        result = get_cpp_function_list("int fun(xx oo){int a; a= call(p1,p2);}")
        self.assertEqual(1, len(result))
        self.assertEqual("fun", result[0].name)
        self.assertEqual("fun( xx oo )", result[0].long_name)

    def test_old_style_c_function(self):
        result = get_cpp_function_list("""int fun(param) int praram; {}""")
        self.assertEqual(1, len(result))

    def test_complicated_c_function(self):
        result = get_cpp_function_list("""int f(int(*)()){}""")
        self.assertEqual('f', result[0].name)

    def test_function_dec_with_throw(self):
        result = get_cpp_function_list("""int fun() throw();void foo(){}""")
        self.assertEqual(1, len(result))

    def test_function_dec_followed_with_one_word_is_ok(self):
        result = get_cpp_function_list("""int fun() no_throw {}""")
        self.assertEqual(1, len(result))

    def test_function_declaration_is_not_counted(self):
        result = get_cpp_function_list("""int fun();class A{};""")
        self.assertEqual(0, len(result))

    def test_old_style_c_function_has_semicolon(self):
        result = get_cpp_function_list("""{(void*)a}{}""")
        self.assertEqual(0, len(result))

    def test_typedef_is_not_old_style_c_function(self):
        result = get_cpp_function_list('''typedef T() nT; foo(){}''')
        self.assertEqual("foo", result[0].name)

    def test_stupid_macro_before_function(self):
        result = get_cpp_function_list('''T() foo(){}''')
        self.assertEqual("foo", result[0].name)

    def test_only_word_can_be_function_name(self):
        result = get_cpp_function_list("""[(){}""")
        self.assertEqual(0, len(result))

    def test_double_slash_within_string(self):
        result = get_cpp_function_list("""int fun(){char *a="\\\\";}""")
        self.assertEqual(1, len(result))
    
    def test_function_with_no_param(self):
        result = get_cpp_function_list("int fun(){}")
        self.assertEqual(0, result[0].parameter_count)
    
    def test_function_with_1_param(self):
        result = get_cpp_function_list("int fun(aa * bb){}")
        self.assertEqual(1, result[0].parameter_count)
    
    def test_function_with_param(self):
        result = get_cpp_function_list("int fun(aa * bb, cc dd){}")
        self.assertEqual(2, result[0].parameter_count)
    
    def test_function_with_strang_param(self):
        result = get_cpp_function_list("int fun(aa<mm, nn> bb){}")
        self.assertEqual(1, result[0].parameter_count)
    
    def test_one_function_with_namespace(self):
        result = get_cpp_function_list("int abc::fun(){}")
        self.assertEqual(1, len(result))
        self.assertEqual("abc::fun", result[0].name)
        self.assertEqual("abc::fun( )", result[0].long_name)
    
    def test_one_function_with_const(self):
        result = get_cpp_function_list("int abc::fun()const{}")
        self.assertEqual(1, len(result))
        self.assertEqual("abc::fun", result[0].name)
        self.assertEqual("abc::fun( ) const", result[0].long_name)

    def test_one_function_in_class(self):
        result = get_cpp_function_list("class c {~c(){}}; int d(){}")
        self.assertEqual(2, len(result))
        self.assertEqual("c", result[0].name)
        self.assertEqual("d", result[1].name)

    def test_template_as_reference(self):
        result = get_cpp_function_list("abc::def(a<b>& c){}")
        self.assertEqual(1, len(result))

    def test_less_then_is_not_template(self):
        result = get_cpp_function_list("def(<); foo(){}")
        self.assertEqual(1, len(result))

    def test_template_with_pointer(self):
        result = get_cpp_function_list("abc::def (a<b*> c){}")
        self.assertEqual(1, len(result))

    def test_nested_template(self):
        result = get_cpp_function_list("abc::def (a<b<c>> c){}")
        self.assertEqual(1, len(result))

    def test_template_with_reference(self):
        result = get_cpp_function_list("void fun(t<int &>b){} ")
        self.assertEqual(1, len(result))

    def test_template_with_reference_as_reference(self):
        result = get_cpp_function_list("void fun(t<const int&>&b){} ")
        self.assertEqual(1, len(result))

    def test_template_as_part_of_function_name(self):
        result = get_cpp_function_list("void fun<a,b<c>>(){} ")
        self.assertEqual('fun<a,b<c>>', result[0].name)

    def test_operator_overloading(self):
        result = get_cpp_function_list("bool operator +=(int b){}")
        self.assertEqual("operator +=", result[0].name)

    def test_operator_with_complicated_name(self):
        result = get_cpp_function_list("operator MyStruct&(){}")
        self.assertEqual("operator MyStruct &", result[0].name)

    def test_operator_overloading_with_namespace(self):
        result = get_cpp_function_list("bool TC::operator !(int b){}")
        self.assertEqual(1, len(result))
        self.assertEqual("TC::operator !", result[0].name)
                
    def test_function_operator(self):
        result = get_cpp_function_list("bool TC::operator ()(int b){}")
        self.assertEqual(1, len(result))
        self.assertEqual("TC::operator ( )", result[0].name)

    def test_constructor_initialization_list(self):
        result = get_cpp_function_list('''A::A():a(1){}''')
        self.assertEqual(1, len(result))
        self.assertEqual("A::A", result[0].name)

    def test_brakets_before_function(self):
        result = get_cpp_function_list('''()''')
        self.assertEqual(0, len(result))
        

class Test_Preprocessing(unittest.TestCase):

    def test_content_macro_should_be_ignored(self):
        result = get_cpp_function_list(r'''
                    #define MTP_CHEC                    \
                       int foo () {                     \
                        }
               ''')
        self.assertEqual(0, len(result))
    
   
    def test_preprocessors_should_be_ignored_outside_function_implementation(self):
        result = get_cpp_function_list('''
                      #ifdef MAGIC
                      #endif
                      void foo()
                      {}
                    ''')
        self.assertEqual(1, len(result))

    def test_preprocessor_is_not_function(self):
        result = get_cpp_function_list('''
                #ifdef A
                #elif (defined E)
                #endif
                ''')
        self.assertEqual(0, len(result))


########NEW FILE########
__FILENAME__ = testCommentOptions
import unittest
from test.mock import Mock, patch
from .testHelpers import get_cpp_function_list

class TestCommentOptions(unittest.TestCase):

    def test_function_with_coment_option_should_be_forgiven(self):
        function_list = get_cpp_function_list("void foo(){/* #lizard forgives*/}")
        self.assertEqual(0, len(function_list))

    def test_function_with_coment_option_before_it_should_be_forgiven(self):
        function_list = get_cpp_function_list("/* #lizard forgives*/void foo(){}")
        self.assertEqual(0, len(function_list))

    def test_function_after_coment_option_should_not_be_forgiven(self):
        function_list = get_cpp_function_list("/* #lizard forgives*/void foo(){}void bar(){}")
        self.assertEqual(1, len(function_list))


########NEW FILE########
__FILENAME__ = testCyclomaticComplexity
import unittest
from .testHelpers import get_cpp_fileinfo, get_cpp_function_list

class TestCyclomaticComplexity(unittest.TestCase):

    def test_one_function_with_no_condition(self):
        result = get_cpp_function_list("int fun(){}")
        self.assertEqual(1, result[0].cyclomatic_complexity)

    def test_one_function_with_one_condition(self):
        result = get_cpp_function_list("int fun(){if(a){xx;}}")
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_one_function_with_question_mark(self):
        result = get_cpp_function_list("int fun(){return (a)?b:c;}")
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_one_function_with_forever_loop(self):
        result = get_cpp_function_list("int fun(){for(;;){dosomething();}}")
        self.assertEqual(2, result[0].cyclomatic_complexity)

    def test_one_function_with_and(self):
        result = get_cpp_function_list("int fun(){if(a&&b){xx;}}")
        self.assertEqual(3, result[0].cyclomatic_complexity)

    def test_one_function_with_else_if(self):
        result = get_cpp_function_list("int fun(){if(a)b;else if (c) d;}")
        self.assertEqual(3, result[0].cyclomatic_complexity)

    def test_sharp_if_and_sharp_elif_counts_in_cc_number(self):
        result = get_cpp_function_list('''
                int main(){
                #ifdef A
                #elif (defined E)
                #endif
                }''')
        self.assertEqual(1, len(result))
        self.assertEqual(3, result[0].cyclomatic_complexity)


########NEW FILE########
__FILENAME__ = testFilesFilter
import unittest
import sys
from mock import patch, Mock
from lizard import get_all_source_files
import os

class TestFilesFilter(unittest.TestCase):

    @patch.object(os, "walk")
    def test_no_matching(self, mock_os_walk):
        mock_os_walk.return_value = []
        files = get_all_source_files(["dir"], [])
        self.assertEqual(0, len(list(files)))

    @patch.object(os.path, "isfile")
    def test_explicit_file_names(self, mock_isfile):
        mock_isfile.return_value = True
        files = get_all_source_files(["dir/file.c"], [])
        self.assertEqual(["dir/file.c"], list(files))

    @patch.object(os.path, "isfile")
    def test_specific_filenames_should_not_be_excluded(self, mock_isfile):
        mock_isfile.return_value = True
        files = get_all_source_files(["dir/file.log"], [])
        self.assertEqual(["dir/file.log"], list(files))

    @patch('lizard.md5_hash_file')
    @patch.object(os, "walk")
    def test_exclude_file_name(self, mock_os_walk, md5):
        mock_os_walk.return_value = (['.', 
                                      None,
                                      ['temp.log', 'useful.cpp']],)
        files = get_all_source_files(["dir"], ["*.log"])
        self.assertEqual(["./useful.cpp"], list(files))

    @patch.object(os, "walk")
    def test_exclude_folder(self, mock_os_walk):
        mock_os_walk.return_value = (['ut', 
                                      None,
                                      ['useful.cpp']],)
        files = get_all_source_files(["dir"], ["ut/*"])
        self.assertEqual([], list(files))

    @patch.object(os, "walk")
    def test_exclude_folder_recursively(self, mock_os_walk):
        mock_os_walk.return_value = (['ut/something', 
                                      None,
                                      ['useful.cpp']],)
        files = get_all_source_files(["dir"], ["ut/*"])
        self.assertEqual([], list(files))

    @patch.object(os, "walk")
    def test_exclude_none_supported_files(self, mock_os_walk):
        mock_os_walk.return_value = (['.', 
                                      None,
                                      ['useful.txt']],)
        files = get_all_source_files(["dir"],['exclude_me'])
        self.assertEqual([], list(files))

    @patch.object(os, "walk")
    @patch("lizard.open", create=True)
    def test_duplicates(self, mock_open, mock_os_walk):
        mock_os_walk.return_value = (['.',
                                      None,
                                      ['f1.cpp', 'f2.cpp']],)
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.read.return_value = "int foo(){haha();\n}"
        files = get_all_source_files(["dir"], [])
        self.assertEqual(['./f1.cpp'], list(files))

    @patch.object(os, "walk")
    @patch("lizard.open", create=True)
    def test_nonduplicates(self, mock_open, mock_os_walk):
        mock_os_walk.return_value = (['.',
                                      None,
                                      ['f1.cpp', 'f2.cpp']],)
        file_handle = mock_open.return_value.__enter__.return_value
        outs = ["int foo(){{haha({param});\n}}".format(param=i) for i in range(2)]
        file_handle.read.side_effect = lambda: outs.pop()
        files = get_all_source_files(["dir"], [])
        self.assertEqual(["./f1.cpp", "./f2.cpp"], list(files))

    @patch.object(os, "walk")
    @patch("lizard.open", create=True)
    def test_fail_to_open_file_should_be_allowed(self, mock_open, mock_os_walk):
        mock_os_walk.return_value = (['.',
                                      None,
                                      ['f1.cpp', 'f2.cpp']],)
        file_handle = mock_open.side_effect = IOError
        files = get_all_source_files(["dir"], [])
        self.assertEqual(['./f1.cpp', './f2.cpp'], list(files))



########NEW FILE########
__FILENAME__ = testFunctionDependencyCount
import unittest
from .testHelpers import get_cpp_function_list_with_extnesion
from lizard_ext.lizarddependencycount import LizardExtension as DependencyCounter


class TestFunctionDependencyCount(unittest.TestCase):

    def test_no_return(self):
        result = get_cpp_function_list_with_extnesion(
            "int fun(){}",
            DependencyCounter())
        self.assertEqual(0, result[0].dependency_count)

    def test_import_dependency(self):
        result = get_cpp_function_list_with_extnesion(
            "import library; int fun(){library.callMethod()}",
            DependencyCounter())
        self.assertEqual(1, result[0].dependency_count)

    def test_python_import_as(self):
        result = get_cpp_function_list_with_extnesion(
            "import python as py; int fun(){py.callMethod() py.version = 99}",
            DependencyCounter())
        self.assertEqual(2, result[0].dependency_count)
        result = get_cpp_function_list_with_extnesion(
            "import candy int fun(){candy.callMethod() py.version = 99}",
            DependencyCounter())
        self.assertEqual(1, result[0].dependency_count)
        result = get_cpp_function_list_with_extnesion(
            "import kok as www import tree, java as monster, coffee import java public class board { private void function() { java += 1; java.tree = green; www.yay(0); teacher.lecture(0); }",
            DependencyCounter())
        self.assertEqual(3, result[0].dependency_count)

########NEW FILE########
__FILENAME__ = testFunctionExitCount
import unittest
from .testHelpers import get_cpp_function_list_with_extnesion
from lizard_ext.lizardexitcount import LizardExtension as ExitCounter

class TestFunctionExitCount(unittest.TestCase):

    def test_no_return_should_count_as_1(self):
        result = get_cpp_function_list_with_extnesion("int fun(){}", ExitCounter())
        self.assertEqual(1, result[0].exit_count)

    def test_one_return_should_count_as_1(self):
        result = get_cpp_function_list_with_extnesion("int fun(){return 0;}", ExitCounter())
        self.assertEqual(1, result[0].exit_count)

    def test_two_returns_should_count_as_2(self):
        result = get_cpp_function_list_with_extnesion("int fun(){return 0;return 1;}", ExitCounter())
        self.assertEqual(2, result[0].exit_count)


########NEW FILE########
__FILENAME__ = testHelpers
from lizard import  analyze_file, FileAnalyzer, get_extensions

def get_cpp_fileinfo(source_code):
    return analyze_file.analyze_source_code("a.cpp", source_code)

def get_cpp_function_list_with_extnesion(source_code, extension):
    return FileAnalyzer(get_extensions([extension])).analyze_source_code("a.cpp", source_code).function_list

def get_cpp_function_list(source_code):
    return get_cpp_fileinfo(source_code).function_list


########NEW FILE########
__FILENAME__ = testJava
import unittest
from lizard import CLikeReader, CLikeReader, analyze_file


def get_java_fileinfo(source_code):
    return analyze_file.analyze_source_code("a.java", source_code)


def get_java_function_list(source_code):
    return get_java_fileinfo(source_code).function_list


class TestJava(unittest.TestCase):

    def test_function_with_throws(self):
        result = get_java_function_list("void fun() throws e1, e2{}")
        self.assertEqual(1, len(result))

########NEW FILE########
__FILENAME__ = testJavaScript
import unittest
from lizard import  analyze_file, FileAnalyzer, get_extensions
from lizard_ext import JavaScriptReader


def get_js_function_list(source_code):
    return analyze_file.analyze_source_code("a.js", source_code).function_list


class Test_tokenizing_JavaScript(unittest.TestCase):

    def check_tokens(self, expect, source):
        tokens = list(JavaScriptReader.generate_tokens(source))
        self.assertEqual(expect, tokens)

    def test_tokenizing_javascript_regular_expression(self):
        self.check_tokens(['/ab/'], '/ab/')
        self.check_tokens([r'/\//'], r'/\//')
        self.check_tokens([r'/a/igm'], r'/a/igm')

    def test_should_not_confuse_division_as_regx(self):
        self.check_tokens(['a','/','b',',','a','/','b'], 'a/b,a/b')
        self.check_tokens(['3453',' ','/','b',',','a','/','b'], '3453 /b,a/b')

    def test_tokenizing_javascript_regular_expression(self):
        self.check_tokens(['a', '=', '/ab/'], 'a=/ab/')

    def test_tokenizing_javascript_comments(self):
        self.check_tokens(['/**a/*/'], '''/**a/*/''')

class Test_parser_for_JavaScript(unittest.TestCase):

    def test_simple_function(self):
        functions = get_js_function_list("function foo(){}")
        self.assertEqual("foo", functions[0].name)

    def test_simple_function_complexity(self):
        functions = get_js_function_list("function foo(){m;if(a);}")
        self.assertEqual(2, functions[0].cyclomatic_complexity)

    def test_parameter_count(self):
        functions = get_js_function_list("function foo(a, b){}")
        self.assertEqual(2, functions[0].parameter_count)

    def test_function_assigning_to_a_name(self):
        functions = get_js_function_list("a = function (a, b){}")
        self.assertEqual('a', functions[0].name)

    def test_not_a_function_assigning_to_a_name(self):
        functions = get_js_function_list("abc=3; function (a, b){}")
        self.assertEqual('function', functions[0].name)

    def test_function_without_name_assign_to_field(self):
        functions = get_js_function_list("a.b.c = function (a, b){}")
        self.assertEqual('a.b.c', functions[0].name)

    def test_function_in_a_object(self):
        functions = get_js_function_list("var App={a:function(){};}")
        self.assertEqual('a', functions[0].name)

    def test_function_in_a_function(self):
        functions = get_js_function_list("function a(){function b(){}}")
        self.assertEqual('b', functions[0].name)
        self.assertEqual('a', functions[1].name)

    def test_global(self):
        functions = get_js_function_list("{}")
        self.assertEqual(0, len(functions))


########NEW FILE########
__FILENAME__ = testLanguages
import unittest
from lizard import CodeReader, CLikeReader, JavaReader, ObjCReader, JavaScriptReader


class TestLanguageChooser(unittest.TestCase):

    def test_not_case_sensitive(self):
        self.assertEqual(CLikeReader, CodeReader.get_reader("a.Cpp"))

    def test_java(self):
        self.assertEqual(JavaReader, CodeReader.get_reader("a.java"))

    def test_objectiveC(self):
        self.assertEqual(ObjCReader, CodeReader.get_reader("a.m"))

    def test_c_cpp(self):
        for name in ("a.cpp", ".cxx", ".h", ".hpp"):
            self.assertEqual(CLikeReader, CodeReader.get_reader(name),
                             "File name '%s' is not recognized as c/c++ file" % name);

    def test_JavaScript(self):
        self.assertEqual(JavaScriptReader, CodeReader.get_reader("a.js"))

    def test_unknown_extension(self):
        self.assertEqual(None, CodeReader.get_reader("a.unknown"));

    def test_new_reader_should_be_found(self):
        class NewReader(CodeReader):
            ext = ['ext']

        self.assertEqual(NewReader, CodeReader.get_reader("a.ext"));
        del NewReader



########NEW FILE########
__FILENAME__ = testObjC
import unittest
from lizard import  analyze_file


class Test_objc_lizard(unittest.TestCase):

    def create_objc_lizard(self, source_code):
        return analyze_file.analyze_source_code("a.m", source_code).function_list

    def test_empty(self):
        result = self.create_objc_lizard("")
        self.assertEqual(0, len(result))

    def test_no_function(self):
        result = self.create_objc_lizard("#import <unistd.h>\n")
        self.assertEqual(0, len(result))

    def test_one_c_function(self):
        result = self.create_objc_lizard("int fun(int a, int b) {}")
        self.assertEqual("fun", result[0].name)

    def test_one_objc_function(self):
        result = self.create_objc_lizard("-(void) foo {}")
        self.assertEqual("foo", result[0].name)

    def test_one_objc_function_with_param(self):
        result = self.create_objc_lizard("-(void) replaceScene: (CCScene*) scene {}")
        self.assertEqual("replaceScene:", result[0].name)
        self.assertEqual("replaceScene:( CCScene * )", result[0].long_name)

    def test_one_objc_functio_nwith_two_param(self):
        result = self.create_objc_lizard("- (BOOL)scanJSONObject:(id *)outObject error:(NSError **)outError {}")
        self.assertEqual("scanJSONObject: error:", result[0].name)
        self.assertEqual("scanJSONObject:( id * ) error:( NSError ** )", result[0].long_name)

    def test_one_objc_function_with_three_param(self):
        result = self.create_objc_lizard("- (id)initWithRequest:(NSURLRequest *)request delegate:(id <NSURLConnectionDelegate>)delegate startImmediately:(BOOL)startImmediately{}")
        self.assertEqual("initWithRequest: delegate: startImmediately:", result[0].name)
        self.assertEqual("initWithRequest:( NSURLRequest * ) delegate:( id < NSURLConnectionDelegate > ) startImmediately:( BOOL )", result[0].long_name)

    def test_implementation(self):
        code = """
            @implementation classname(xx)
            + (return_type)classMethod
            {
                if (failure){

                     //wefailed

                 }
            }
            - (return_type)instanceMethod
            {
                // implementation
            }
            @end
            """
        result = self.create_objc_lizard(code)
        self.assertEqual(2, len(result))
        self.assertEqual("classMethod", result[0].name)



########NEW FILE########
__FILENAME__ = testOutput
import unittest
from test.mock import Mock, patch
import sys
import os
from lizard import print_warnings, print_and_save_modules, FunctionInfo, FileInformation,\
    print_result, get_extensions, OutputScheme
from lizard_ext import xml_output

class StreamStdoutTestCase(unittest.TestCase):
    def setUp(self):
        self.savedStdout = sys.stdout 
        sys.stdout = self.StreamForTest()

    def tearDown(self):
        sys.stdout = self.savedStdout

    class StreamForTest:

        def __init__(self):
            self.stream = ""

        def write(self, x):
            self.stream += str(x)

        def __getattr__(self, attr):
            return getattr(self.stream, attr)

class TestFunctionOutput(StreamStdoutTestCase):

    def setUp(self):
        StreamStdoutTestCase.setUp(self)
        self.extensions = get_extensions([])
        self.scheme = OutputScheme(self.extensions)
        self.foo = FunctionInfo("foo", 'FILENAME', 100)

    def test_function_info_header_should_have_a_box(self):
        print_and_save_modules([], self.extensions, self.scheme)
        self.assertIn("=" * 20, sys.stdout.stream.splitlines()[0])

    def test_function_info_header_should_have_the_captions(self):
        print_and_save_modules([], self.extensions, self.scheme)
        self.assertEquals("  NLOC    CCN   token  PARAM  location  ", sys.stdout.stream.splitlines()[1])

    def test_function_info_header_should_have_the_captions_of_external_extensions(self):
        external_extension = Mock(FUNCTION_CAPTION = "*external_extension*")
        extensions = get_extensions([external_extension])
        scheme = OutputScheme(extensions)
        print_and_save_modules([], extensions, scheme)
        self.assertEquals("  NLOC    CCN   token  PARAM *external_extension* location  ", sys.stdout.stream.splitlines()[1])

    def test_print_fileinfo(self):
        self.foo.end_line = 100
        self.foo.cyclomatic_complexity = 16
        fileStat = FileInformation("FILENAME", 1, [self.foo])
        print_and_save_modules([fileStat], self.extensions, self.scheme)
        self.assertEquals("       1     16      1      0 foo@100-100@FILENAME", sys.stdout.stream.splitlines()[3])

class TestWarningOutput(StreamStdoutTestCase):

    def setUp(self):
        StreamStdoutTestCase.setUp(self)
        self.option = Mock(warnings_only=False, CCN=15, extensions = [])
        self.foo = FunctionInfo("foo", 'FILENAME', 100)
        self.scheme = Mock()

    def test_should_have_header_when_warning_only_is_off(self):
        print_warnings(self.option, self.scheme, [])
        self.assertIn("Warnings (CCN > 15)", sys.stdout.stream)

    def test_no_news_is_good_news(self):
        self.option.warnings_only = True
        print_warnings(self.option, self.scheme, [])
        self.assertEqual('', sys.stdout.stream)

    def test_should_not_have_header_when_warning_only_is_on(self):
        self.option = Mock(warnings_only=True, CCN=15)
        print_warnings(self.option, self.scheme, [])
        self.assertNotIn("Warnings (CCN > 15)", sys.stdout.stream)

    def test_should_use_clang_format_for_warning(self):
        self.option = Mock(display_fn_end_line = False, extensions = get_extensions([]))
        print_warnings(self.option, self.scheme, [self.foo])
        self.assertIn("FILENAME:100: warning: foo has 1 CCN and 0 params (1 NLOC, 1 tokens)\n", sys.stdout.stream)

    def test_sort_warning(self):
        self.option.sorting = ['cyclomatic_complexity']
        self.foo.cyclomatic_complexity = 10
        bar = FunctionInfo("bar", '', 100)
        bar.cyclomatic_complexity = 15
        print_warnings(self.option, self.scheme, [self.foo, bar])
        self.assertEqual('bar', self.scheme.function_info.call_args_list[0][0][0].name)

    def test_sort_warning_with_generator(self):
        self.option.sorting = ['cyclomatic_complexity']
        print_warnings(self.option, self.scheme, (x for x in []))


class TestFileOutput(StreamStdoutTestCase):

    def test_print_and_save_detail_information(self):
        fileSummary = FileInformation("FILENAME", 123, [])
        print_and_save_modules([fileSummary], [], Mock())
        self.assertIn("    123      0    0.0         0         0     FILENAME", sys.stdout.stream)

    def test_print_file_summary_only_once(self):
        print_and_save_modules(
                            [FileInformation("FILENAME1", 123, []), 
                             FileInformation("FILENAME2", 123, [])], [], Mock())
        self.assertEqual(1, sys.stdout.stream.count("FILENAME1"))


class TestAllOutput(StreamStdoutTestCase):

    def setUp(self):
        StreamStdoutTestCase.setUp(self)
        self.foo = FunctionInfo("foo", 'FILENAME', 100)

    def test_print_extension_results(self):
        file_infos = []
        extension = Mock()
        option = Mock(CCN=15, number = 0, extensions = [extension], whitelist='')
        print_result(file_infos, option)
        self.assertEqual(1, extension.print_result.call_count)

    def test_should_not_print_extension_results_when_not_implemented(self):
        file_infos = []
        option = Mock(CCN=15, number = 0, extensions = [object()], whitelist='')
        print_result(file_infos, option)

    @patch.object(sys, 'exit')
    def test_print_result(self, mock_exit):
        file_infos = [FileInformation('f1.c', 1, []), FileInformation('f2.c', 1, [])]
        option = Mock(CCN=15, number = 0, extensions=[], whitelist='')
        print_result(file_infos, option)
        self.assertEqual(0, mock_exit.call_count)

    @patch.object(os.path, 'isfile')
    @patch('lizard.open', create=True)
    def check_whitelist(self, script, mock_open, mock_isfile):
        mock_isfile.return_value = True
        mock_open.return_value.read.return_value = script
        file_infos = [FileInformation('f1.c', 1, [self.foo])]
        option = Mock(CCN=15, number = 0, arguments=100, extensions=[])
        print_result(file_infos, option)

    @patch.object(sys, 'exit')
    def test_exit_with_non_zero_when_more_warning_than_ignored_number(self, mock_exit):
        self.foo.cyclomatic_complexity = 16
        self.check_whitelist('')
        mock_exit.assert_called_with(1)

    @patch.object(sys, 'exit')
    def test_whitelist(self, mock_exit):
        self.foo.cyclomatic_complexity = 16
        self.check_whitelist('foo')
        self.assertEqual(0, mock_exit.call_count)

    def test_null_result(self):
        self.check_whitelist('')


import xml.etree.ElementTree as ET
class TestXMLOutput(unittest.TestCase):
    foo = FunctionInfo("foo", '', 100)
    foo.cyclomatic_complexity = 16
    file_infos = [FileInformation('f1.c', 1, [foo])]
    xml = xml_output(file_infos, True)

    def test_xml_output(self):
        root = ET.fromstring(self.xml)
        item = root.findall('''./measure[@type="Function"]/item[0]''')[0]
        self.assertEqual('''foo at f1.c:100''', item.get("name"))

    def test_xml_stylesheet(self):
        self.assertIn('''<?xml-stylesheet type="text/xsl" href="https://raw.github.com/terryyin/lizard/master/lizard.xsl"?>''', self.xml)

########NEW FILE########
__FILENAME__ = testPython
import unittest
import inspect
from lizard import  analyze_file, FileAnalyzer, get_extensions


def get_python_function_list(source_code):
    return analyze_file.analyze_source_code("a.py", source_code).function_list


class Test_parser_for_Python(unittest.TestCase):

    def test_empty_source_should_return_no_function(self):
        functions = get_python_function_list("")
        self.assertEqual(0, len(functions))

    def test_simple_python_function(self):
        class namespace1:
            def simple_function():
                if IamOnEarth:
                    return toMars()
        functions = get_python_function_list(inspect.getsource(namespace1))
        self.assertEqual(1, len(functions))
        self.assertEqual("simple_function", functions[0].name)
        self.assertEqual(2, functions[0].cyclomatic_complexity)
        self.assertEqual(4, functions[0].end_line)

    def test_parameter_count(self):
        class namespace2:
            def function_with_2_parameters(a, b):
                pass
        functions = get_python_function_list(inspect.getsource(namespace2))
        self.assertEqual(2, functions[0].parameter_count)

    def test_function_end(self):
        class namespace3:
            def simple_function(self):
                pass

            blah = 42
        functions = get_python_function_list(inspect.getsource(namespace3))
        self.assertEqual(1, len(functions))
        self.assertEqual("simple_function", functions[0].name)
        self.assertEqual(3, functions[0].end_line)

    def test_top_level_functions(self):
        functions = get_python_function_list(inspect.getsource(top_level_function_for_test))
        self.assertEqual(1, len(functions))

    def test_2_top_level_functions(self):
        functions = get_python_function_list('''
def a():
    pass
def b():
    pass
''')
        self.assertEqual(2, len(functions))
        self.assertEqual("a", functions[0].name)

    def test_2_functions(self):
        class namespace4:
            def function1(a, b):
                pass
            def function2(a, b):
                pass
        functions = get_python_function_list(inspect.getsource(namespace4))
        self.assertEqual(2, len(functions))

    def test_nested_functions(self):
        class namespace5:
            def function1(a, b):
                def function2(a, b):
                    pass
                a = 1 if b == 2 else 3
        functions = get_python_function_list(inspect.getsource(namespace5))
        self.assertEqual(2, len(functions))
        self.assertEqual("function2", functions[0].name)
        self.assertEqual(4, functions[0].end_line)
        self.assertEqual("function1", functions[1].name)
        self.assertEqual(5, functions[1].end_line)
        self.assertEqual(2, functions[1].cyclomatic_complexity)

    def test_nested_functions_ended_at_eof(self):
        class namespace6:
            def function1(a, b):
                def function2(a, b):
                    pass
        functions = get_python_function_list(inspect.getsource(namespace6))
        self.assertEqual(2, len(functions))
        self.assertEqual("function2", functions[0].name)
        self.assertEqual(4, functions[0].end_line)
        self.assertEqual("function1", functions[1].name)
        self.assertEqual(4, functions[1].end_line)

    def test_nested_functions_ended_at_same_line(self):
        class namespace7:
            def function1(a, b):
                def function2(a, b):
                    pass
            def function3():
                pass
        functions = get_python_function_list(inspect.getsource(namespace7))
        self.assertEqual(3, len(functions))
        self.assertEqual("function2", functions[0].name)
        self.assertEqual(4, functions[0].end_line)
        self.assertEqual("function1", functions[1].name)
        self.assertEqual(4, functions[1].end_line)

    def test_one_line_functions(self):
        class namespace8:
            def a( ):pass
            def b( ):pass
        functions = get_python_function_list(inspect.getsource(namespace8))
        self.assertEqual("a", functions[0].name)
        self.assertEqual("b", functions[1].name)

    def test_comment_is_not_counted_in_nloc(self):
        def function_with_comments():

            # comment
            pass
        functions = get_python_function_list(inspect.getsource(function_with_comments))
        self.assertEqual(2, functions[0].nloc)

    def test_odd_blank_line(self):
        code =  "class c:\n" + \
                "    def f():\n" +\
                "  \n" +\
                "         pass\n"
        functions = get_python_function_list(code)
        self.assertEqual(4, functions[0].end_line)

    def test_odd_line_with_comment(self):
        code =  "class c:\n" + \
                "    def f():\n" +\
                "  #\n" +\
                "         pass\n"
        functions = get_python_function_list(code)
        self.assertEqual(4, functions[0].end_line)

    def test_tab_is_same_as_8_spaces(self):
        code =  ' ' * 7 + "def a():\n" + \
                '\t'    +  "pass\n"
        functions = get_python_function_list(code)
        self.assertEqual(2, functions[0].end_line)

    def test_if_elif_and_or_for_while_except_finally(self):
        code =  'def a():\n' + \
                '    if elif and or for while except finally\n'
        functions = get_python_function_list(code)
        self.assertEqual(9, functions[0].cyclomatic_complexity)

    def test_block_string_is_one_token(self):
        code =  'def a():\n' + \
                "    a = '''\n" +\
                "a b c d e f g h i'''\n"+\
                "    return a\n"
        functions = get_python_function_list(code)
        self.assertEqual(9, functions[0].token_count)
        self.assertEqual(4, functions[0].end_line)

    def check_function_info(self, source, expect_token_count, expect_nloc, expect_endline):
        functions = get_python_function_list(source)
        self.assertEqual(expect_token_count, functions[0].token_count)
        self.assertEqual(expect_nloc, functions[0].nloc)
        self.assertEqual(expect_endline, functions[0].end_line)

    def test_block_string(self):
        self.check_function_info('def f(): a="""block string"""', 7, 1, 1)
        self.check_function_info("def f(): a='''block string'''", 7, 1, 1)
        self.check_function_info("def f():\n a='''block string'''", 7, 2, 2)
        self.check_function_info("def f():\n a='''block\n string'''", 7, 3, 3)
        self.check_function_info("def f():\n a='''block\n '''", 7, 3, 3)

    def test_docstring_is_not_counted_in_nloc(self):
        self.check_function_info("def f():\n '''block\n '''\n pass", 6, 2, 4)

    #global complexity


def top_level_function_for_test():
    pass


########NEW FILE########
__FILENAME__ = testTokenizer
import unittest
from lizard import CodeReader
generate_tokens = CodeReader.generate_tokens


class Test_generate_tonken(unittest.TestCase):

    def check_tokens(self, source, *expect):
        tokens = generate_tokens(source)
        self.assertEqual(list(expect), tokens)

    def test_empty_string(self):
        self.check_tokens("")

    def test_spaces(self):
        self.check_tokens("\n", "\n")
        self.check_tokens("\n\n", "\n", "\n")
        self.check_tokens(" \n", " ", "\n")

    def test_digits(self):
        self.check_tokens("1", "1")
        self.check_tokens("123", "123")

    def test_operators(self):
        self.check_tokens("-;", '-', ';')
        self.check_tokens("-=", '-=')
        self.check_tokens(">=", '>=')
        self.check_tokens("<=", '<=')
        self.check_tokens("||", '||')

    def test_more(self):
        self.check_tokens("int a{}", 'int', ' ', "a", "{", "}")

    def test_string(self):
        self.check_tokens(r'""', '""')
        self.check_tokens(r'"x\"xx")', '"x\\"xx"', ')')
        self.check_tokens("'\\''", "'\\''")

    def test_line_number(self):
        self.check_tokens(r'abc', 'abc')

    def test_line_number2(self):
        tokens = generate_tokens('abc\ndef')
        self.assertTrue('def' in tokens)

    def test_with_mutiple_line_string(self):
        tokens = generate_tokens('"sss\nsss" t')
        self.assertTrue('t' in tokens)


class Test_generate_tonken_for_marcos(unittest.TestCase):

    def test_define(self):
        define =  '''#define xx()\
                       abc'''
        tokens = generate_tokens(define+'''
                    int''')
        self.assertEqual([define, '\n', ' ' * 20, 'int'], tokens)

    def test_if(self):
        tokens = generate_tokens('''#if abc\n''')
        self.assertEqual(['#if abc', '\n'], tokens)

    def test_ifdef(self):
        tokens = generate_tokens('''#ifdef abc\n''')
        self.assertEqual(['#ifdef abc', '\n'], tokens)

    def test_with_line_continuer_define(self):
        tokens = generate_tokens('#define a \\\nb\n t')
        self.assertTrue('t' in tokens)

    def test_define2(self):
        tokens = generate_tokens(r''' # define yyMakeArray(ptr, count, size)     { MakeArray (ptr, count, size); \
                       yyCheckMemory (* ptr); }
                       t
                    ''')
        self.assertTrue('t' in tokens)


class Test_generate_tonken_for_comments(unittest.TestCase):

    def test_c_style_comment(self):
        tokens = generate_tokens("/***\n**/")
        self.assertEqual(["/***\n**/"], tokens)

    def test_cpp_style_comment(self):
        tokens = generate_tokens("//aaa\n")
        self.assertEqual(['//aaa', '\n'], tokens)

    def test_cpp_style_comment_with_multiple_lines(self):
        tokens = generate_tokens("//a\\\nb")
        self.assertEqual(['//a\\\nb'], tokens)

    def test_commentedComment(self):
        tokens = generate_tokens(" /*/*/")
        self.assertEqual([' ', "/*/*/"], tokens)

    def test_with_cpp_comments(self):
        tokens = generate_tokens('//abc\n t')
        self.assertTrue('t' in tokens)

    def test_with_c_comments(self):
        tokens = generate_tokens('/*abc\n*/ t')
        self.assertTrue('t' in tokens)

    def test_with_c_comments_with_backslash_in_it(self):
        comment = '/**a/*/'
        tokens = generate_tokens(comment)
        self.assertListEqual([comment], tokens)


########NEW FILE########
__FILENAME__ = testWordCountPlugin
import unittest
from test.mock import patch
from lizard_ext.lizardwordcount import LizardExtension


class FakeReader(object):

    class FI(object) : pass

    def __init__(self):
        self.fileinfo = self.FI()
        self.context = self
    def get_word_map(self):
        return self.fileinfo.wordCount


class TestWordCountPlugin(unittest.TestCase):

    def setUp(self):
        self.reader = FakeReader()
        self.ext = LizardExtension()

    def test_count_one_word(self):
        list(self.ext(["a", "b"], self.reader))
        self.assertEqual(1, self.reader.get_word_map()['a'])
        self.assertEqual(1, self.reader.get_word_map()['b'])

    def test_count_one_word_multiple_times(self):
        list(self.ext(["a", "a"], self.reader))
        self.assertEqual(2, self.reader.get_word_map()['a'])

    def test_count_one_word_multiple_times(self):
        list(self.ext(["a", "a"], self.reader))
        self.assertEqual(2, self.reader.get_word_map()['a'])

    def test_should_not_count_keywords(self):
        list(self.ext(["for"], self.reader))
        self.assertNotIn('for', self.reader.get_word_map())

    def test_should_count_non_keyword(self):
        list(self.ext(["For"], self.reader))
        self.assertIn('For', self.reader.get_word_map())

    def test_should_not_count_string(self):
        list(self.ext(["\"\""], self.reader))
        self.assertEqual(0, len(self.reader.get_word_map()))

    def test_reduce_the_result(self):
        list(self.ext(["a"], self.reader))
        self.ext.reduce(self.reader.fileinfo)
        self.ext.reduce(self.reader.fileinfo)
        self.assertEqual(2, self.ext.result['a'])

class TestWordCountOutput(unittest.TestCase):

    def setUp(self):
        self.buf = ''

    def write_to_buffer(self, txt):
            self.buf += txt

    @patch('webbrowser.open')
    @patch('lizard_ext.lizardwordcount.open', create=True)
    def test_should_output_html(self, mock_open, browser_open):
        buf = ""
        mock_open.return_value.__enter__.return_value.write.side_effect = self.write_to_buffer
        ext = LizardExtension()
        ext.result = {'a':123}
        ext.print_result()
        mock_open.assert_called_once_with('codecloud.html', 'w')
        self.assertIn('<html>', self.buf)
        self.assertIn('["a", 123]', self.buf)

    @patch('webbrowser.open')
    @patch('lizard_ext.lizardwordcount.open', create=True)
    def test_should_open_the_browser(self, mock_open, browser_open):
        import os
        ext = LizardExtension()
        ext.result = {'a':123}
        ext.print_result()
        browser_open.assert_called_with('file://' + os.path.abspath('codecloud.html'));


########NEW FILE########
__FILENAME__ = test_analyzer
#
# Unit Test
#
import unittest
import sys
from mock import patch, Mock
from lizard import CLikeReader, map_files_to_analyzer, FunctionInfo, analyze_file, CodeInfoContext


def analyzer_mock(filename):
    return filename

class Test_analyze_files(unittest.TestCase):
    def test_NoFiles(self):
        call_count = 0
        def analyzer(filename):
            call_count += 1
        map_files_to_analyzer([], analyzer, 1)
        self.assertEqual(0, call_count)

    def test_NoFilesMultipleThread(self):
        call_count = 0
        def analyzer(filename):
            call_count += 1
        map_files_to_analyzer([], analyzer, 2)
        self.assertEqual(0, call_count)
        
    def test_OneFile(self):
        analyzer = analyzer_mock
        r = map_files_to_analyzer(["filename"], analyzer, 1)
        self.assertEqual(["filename"], [x for x in r])
        
    def test_OneFileMultipleThread(self):
        analyzer = analyzer_mock
        r = map_files_to_analyzer(["filename"], analyzer, 2)
        self.assertEqual(["filename"], [x for x in r])
    
    def test_MoreFiles(self):
        analyzer = analyzer_mock
        r = map_files_to_analyzer(["f1", "f2"], analyzer, 1)
        self.assertEqual(["f1", "f2"], [x for x in r])

    def test_MoreFilesMultipleThread(self):
        analyzer = analyzer_mock
        r = map_files_to_analyzer(["f1", "f2"], analyzer, 2)
        self.assertSetEqual(set(["f1", "f2"]), set(x for x in r))


@patch('lizard.open', create=True)
class Test_FileAnalyzer(unittest.TestCase):
    
    def setUp(self):
        self.analyzer = analyze_file
        
    def test_analyze_c_file(self, mock_open):
        file_handle = mock_open.return_value.read.return_value = "int foo(){haha();\n}"
        r = map_files_to_analyzer(["f1.c"], self.analyzer, 1)
        self.assertEqual(1, len([x for x in r]))
        
    def test_analyze_c_file_with_multiple_thread(self, mock_open):
        file_handle = mock_open.return_value.read.return_value = "int foo(){haha();\n}"
        r = map_files_to_analyzer(["f1.c"], self.analyzer, 2)
        self.assertEqual(1, len([x for x in r]))
    
    def test_fileInfomation(self, mock_open):
        mock_open.return_value.read.return_value = "int foo(){haha();\n}"
        r = map_files_to_analyzer(["f1.c"], self.analyzer, 1)
        fileInfo = list(r)[0]
        self.assertEqual(2, fileInfo.nloc)
        self.assertEqual(2, fileInfo.average_NLOC)
        self.assertEqual(1, fileInfo.average_CCN)
        self.assertEqual(9, fileInfo.average_token)

    @patch.object(sys, 'stderr')
    def test_should_report_when_having_other_problem_and_continue(self, mock_stderr, mock_open):
        mock_open.side_effect = IOError("[Errno 2] No such file or directory")
        analyze_file("f1.c")
        self.assertEqual(1, mock_stderr.write.call_count)
        error_message = mock_stderr.write.call_args[0][0]
        self.assertEqual("Error: Fail to read source file 'f1.c'\n", error_message)

class Test_Picklability(unittest.TestCase):

    def test_FunctionInfo_ShouldBePicklable(self):
        import pickle
        pickle.dumps(FunctionInfo("a", '', 1))

    def test_FileInfo_ShouldBePicklable(self):
        import pickle
        pickle.dumps(CodeInfoContext("a"))


from lizard import warning_filter, FileInformation, whitelist_filter

class TestWarningFilter(unittest.TestCase):

    def setUp(self):
        complex_fun = FunctionInfo("complex", '', 100)
        complex_fun.cyclomatic_complexity = 16
        simple_fun = FunctionInfo("simple", '', 100)
        simple_fun.cyclomatic_complexity = 15
        self.fileStat = FileInformation("FILENAME", 1, [complex_fun, simple_fun])

    def test_should_filter_the_warnings(self):
        option = Mock(CCN=15, arguments=10)
        warnings = list(warning_filter(option, [self.fileStat]))
        self.assertEqual(1, len(warnings))
        self.assertEqual("complex", warnings[0].name)

class TestWarningFilterWithWhitelist(unittest.TestCase):

    WARNINGS = [FunctionInfo("foo", 'filename'),
             FunctionInfo("bar", 'filename'),
             FunctionInfo("foo", 'anotherfile')]

    def test_should_filter_out_the_whitelist(self):
        warnings = whitelist_filter(self.WARNINGS, "foo")
        self.assertEqual(1, len(list(warnings)))

    def test_should_filter_function_in_the_right_file_when_specified(self):
        warnings = whitelist_filter(self.WARNINGS, 'filename:foo')
        self.assertEqual(2, len(list(warnings)))

    def test_should_work_with_class_member(self):
        warnings = whitelist_filter([FunctionInfo("class::foo", 'filename')], 'class::foo')
        self.assertEqual(0, len(list(warnings)))

    def test_should_filter_mutiple_functions_defined_on_one_line(self):
        warnings = whitelist_filter(self.WARNINGS, 'foo, bar')
        self.assertEqual(0, len(list(warnings)))

    def test_should_filter_mutiple_lines_of_whitelist(self):
        warnings = whitelist_filter(self.WARNINGS, 'foo\n bar')
        self.assertEqual(0, len(list(warnings)))

    def test_should_ignore_comments_in_whitelist(self):
        warnings = whitelist_filter(self.WARNINGS, 'foo  #,bar\ni#,bar')
        self.assertEqual(1, len(list(warnings)))



########NEW FILE########
__FILENAME__ = test_options
import unittest
from lizard import parse_args
from test.mock import patch
import sys
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class TestOptionParsing(unittest.TestCase):

    def test_should_use_current_folder_as_default_path(self):
        options = parse_args(['lizard'])
        self.assertEqual(['.'], options.paths)

    def test_default_sorting(self):
        options = parse_args(['lizard'])
        self.assertEqual(0, len(options.sorting))

    def test_sorting_factor(self):
        options = parse_args(['lizard', '-snloc'])
        self.assertEqual("nloc", options.sorting[0])

    @patch.object(sys, 'exit')
    @patch('sys.stderr')
    def test_sorting_factor_does_not_exist(self, _, mock_exit):
        options = parse_args(['lizard', '-sdoesnotexist'])
        mock_exit.assert_called_with(2)

    @patch.object(sys, 'exit')
    @patch('sys.stderr', new_callable=StringIO)
    def test_sorting_factor_does_not_exist_error_message(self, mock_stderr, mock_exit):
        options = parse_args(['lizard', '-sdoesnotexist'])
        self.assertEqual("Wrong sorting field 'doesnotexist'.\nCandidates are: nloc, cyclomatic_complexity, token_count, parameter_count, location\n", mock_stderr.getvalue())

########NEW FILE########
