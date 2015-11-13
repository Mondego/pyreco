__FILENAME__ = batch
import uuid
import os
import dexy.data

class Batch(object):
    def __init__(self, wrapper):
        self.wrapper = wrapper
        self.docs = {}
        self.doc_keys = {}
        self.filters_used = []
        self.uuid = str(uuid.uuid4())
        self.start_time = None
        self.end_time = None

    def __repr__(self):
        return "Batch(%s)" % self.uuid

    def __iter__(self):
        for doc_key in self.docs:
            if self.docs[doc_key]['state'] in ('uncached',):
                continue
            yield self.output_data(doc_key)

    def add_doc(self, doc):
        """
        Adds a new doc to the batch of docs.
        """
        if hasattr(doc, 'batch_info'):
            doc_key = doc.key_with_class()
            storage_key = doc.output_data().storage_key
            self.doc_keys[storage_key] = doc_key
            self.update_doc_info(doc)
            self.filters_used.extend(doc.filter_aliases)

    def update_doc_info(self, doc):
        self.docs[doc.key_with_class()] = doc.batch_info()

    def output_data(self, doc_key):
        return self.data(doc_key, 'output')

    def input_data(self, doc_key):
        return self.data(doc_key, 'input')

    def doc_info(self, doc_key):
        return self.docs[doc_key]
   
    def doc_key(self, storage_key):
        return self.doc_keys[storage_key]

    def data_for_storage_key(self, storage_key, input_or_output='output'):
        """
        Retrieves a data object given the storage key (based on the the
        md5sum), rather than the canonical doc key based on the doc name.
        """
        doc_key = self.doc_key(storage_key)
        return self.data(doc_key, input_or_output)

    def data(self, doc_key, input_or_output='output'):
        """
        Retrieves a data object given the doc key.
        """
        doc_info = self.doc_info(doc_key)["%s-data" % input_or_output]
        args = list(doc_info)
        args.append(self.wrapper)
        data = dexy.data.Data.create_instance(*args)
        data.setup_storage()
        if hasattr(data.storage, 'connect'):
            data.storage.connect()
        return data

    def elapsed(self):
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        else:
            return 0

    def filename(self):
        return "%s.pickle" % self.uuid

    def filepath(self):
        return os.path.join(self.batch_dir(), self.filename())

    def most_recent_filename(self):
        return os.path.join(self.batch_dir(), 'most-recent-batch.txt')

    def batch_dir(self):
        return os.path.join(self.wrapper.artifacts_dir, 'batches')

    def to_dict(self):
        attr_names = ['docs', 'doc_keys', 'filters_used', 'uuid']
        return dict((k, getattr(self, k),) for k in attr_names)

    def save_to_file(self):
        try:
            os.makedirs(self.batch_dir())
        except OSError:
            pass

        with open(self.filepath(), 'w') as f:
            pickle = dexy.utils.pickle_lib(self.wrapper)
            pickle.dump(self.to_dict(), f)

        with open(self.most_recent_filename(), 'w') as f:
            f.write(self.uuid)

    def load_from_file(self):
        pickle = dexy.utils.pickle_lib(self.wrapper)
        with open(self.filepath(), 'r') as f:
            d = pickle.load(f)
            for k, v in d.iteritems():
                setattr(self, k, v)

    @classmethod
    def load_most_recent(klass, wrapper):
        """
        Retuns a batch instance representing the most recent batch as indicated
        by the UUID stored in most-recent-batch.txt.
        """
        batch = Batch(wrapper)
        try:
            with open(batch.most_recent_filename(), 'r') as f:
                most_recent_uuid = f.read()

            batch.uuid = most_recent_uuid
            batch.load_from_file()
            return batch
        except IOError:
            pass

########NEW FILE########
__FILENAME__ = cite
from dexy.version import DEXY_VERSION
import datetime
import dexy.exceptions

# TODO list available citation types

def cite_command(
        fmt='bibtex' # desired format of citation
        ):
    """
    How to cite dexy in papers.
    """
    if fmt == 'bibtex':
        cite_bibtex()
    else:
        msg = "Don't know how to provide citation in '%s' format"
        raise dexy.exceptions.UserFeedback(msg % fmt)

def bibtex_text():
    args = {
            'version' : DEXY_VERSION,
            'year' : datetime.date.today().year
            }

    return """@misc{Dexy,
    title = {Dexy: Reproducible Data Analysis and Document Automation Software, Version~%(version)s},
    author = {{Nelson, Ana}},
    year = {%(year)s},
    url = {http://www.dexy.it/},
    note = {http://orcid.org/0000-0003-2561-1564}
}""" % args

def cite_bibtex():
    print bibtex_text()

########NEW FILE########
__FILENAME__ = conf
from dexy.commands.utils import default_config
from dexy.utils import defaults
from dexy.utils import file_exists
import dexy.exceptions
import inspect
import json
import os
import yaml

def conf_command(
        conf=defaults['config_file'], # name of config file to write to
        p=False # whether to print to stdout rather than write to file
        ):
    """
    Write a config file containing dexy's defaults.
    """
    if file_exists(conf) and not p:
        print inspect.cleandoc("""Config file %s already exists,
        will print conf to stdout instead...""" % conf)
        p = True

    config = default_config()

    # Can't specify config file name in config file.
    del config['conf']

    yaml_help = inspect.cleandoc("""# YAML config file for dexy.
        # You can delete any lines you don't wish to customize.
        # Options are same as command line options,
        # for more info run 'dexy help -on dexy'.
        """)

    if p:
        print yaml.dump(config, default_flow_style=False)
    else:
        with open(conf, "wb") as f:
            if conf.endswith(".yaml") or conf.endswith(".conf"):
                f.write(yaml_help)
                f.write(os.linesep)
                f.write(yaml.dump(config, default_flow_style=False))
            elif conf.endswith(".json"):
                json.dump(config, f, sort_keys=True, indent=4)
            else:
                msg = "Don't know how to write config file '%s'"
                raise dexy.exceptions.UserFeedback(msg % conf)

        print "Config file has been written to '%s'" % conf

########NEW FILE########
__FILENAME__ = dirs
from dexy.commands.utils import init_wrapper
from dexy.utils import defaults

def reset_command(
        __cli_options=False,
        artifactsdir=defaults['artifacts_dir'], # Where dexy should store working files.
        logdir=defaults['log_dir'] # DEPRECATED
        ):
    """
    Clean out the contents of dexy's cache and reports directories.
    """
    wrapper = init_wrapper(locals())
    wrapper.remove_dexy_dirs()
    wrapper.remove_reports_dirs(keep_empty_dir=True)
    wrapper.create_dexy_dirs()

def cleanup_command(
        __cli_options=False,
        artifactsdir=defaults['artifacts_dir'], # Where dexy should store working files.
        logdir=defaults['log_dir'], # DEPRECATED
        reports=True # Whether directories generated by reports should also be removed.
        ):
    """
    Remove the directories which dexy created, including working directories
    and reports.
    """
    wrapper = init_wrapper(locals())
    wrapper.remove_dexy_dirs()
    wrapper.remove_reports_dirs(reports)

def setup_command(
        __cli_options=False,
        artifactsdir=defaults['artifacts_dir'], # Where dexy should store working files.
        **kwargs):
    """
    Create the directories dexy needs to run.
    """
    wrapper = init_wrapper(locals())
    wrapper.create_dexy_dirs()


########NEW FILE########
__FILENAME__ = env
from dexy.commands.utils import dummy_wrapper
import dexy.doc
import dexy.filter

def env_command():
    """
    Prints list of template plugins.
    """
    f = dexy.filter.Filter.create_instance("jinja")
    f.doc = dexy.doc.Doc('dummy', dummy_wrapper())
    jinja_template_filters = f.jinja_template_filters().keys()

    env = f.run_plugins()
    for k in sorted(env):
        try:
            helpstring, value = env[k]
        except Exception:
            print k
            print "Values should be a (docstring, value) tuple."
            raise

        if k in jinja_template_filters:
            print "*%s: %s" % (k, helpstring,)
        else:
            print "%s: %s" % (k, helpstring,)

    print ''
    print "* indicates the method can be used as a jinja template filter"
    print ''

def plugins_command():
    """
    Prints list of plugin-able classes.
    """
    for plugin_class in sorted(dexy.plugin.Plugin.__subclasses__()):
        print plugin_class.__name__

from pygments import highlight
from pygments.lexers import PythonLexer
import dexy.data
import dexy.exceptions
import inspect
import pygments.formatters
from dexy.utils import indent
import textwrap

def datas_command(
        alias=False, # Alias of data type to print detaile dinfo for.
        source=False, # Whether to print source code for methods.
        nocolor=False, # If printing source, whether to colorize it.
    ):
    """
    Prints list of data types.
    """
    wrapper = dummy_wrapper()
    settings = {
            'canonical-name' : 'foo'
            }

    nodoc_methods = ('clear_cache', 'clear_data', 'copy_from_file', 'data', 'has_data',
            'initialize_settings', 'initialize_settings_from_other_classes',
            'initialize_settings_from_parents', 'initialize_settings_from_raw_kwargs',
            'is_active', 'is_cached', 'args_to_data_init', 'json_as_dict', 'as_text',
            'load_data', 'save', 'setup', 'setup_storage', 'storage_class_alias',
            'transition', 'add_to_lookup_sections' ,'add_to_lookup_nodes'
            )

    print ""

    if not alias:
        for d in dexy.data.Data.__iter__("foo", ".txt", "foo", settings, wrapper):
            print d.alias

        print ""
        print "For more information about a particular data type,"
        print "use the -alias flag and specify the data type alias."
        print ""
    else:
        d = dexy.data.Data.create_instance(alias, "foo", ".txt", "foo", settings, wrapper)

        print alias
        print ""
        print d.setting('help')
        print ""

        print "Methods:"
        for k, v in inspect.getmembers(d):
            if k.startswith('_'):
                continue

            if inspect.ismethod(v) and not k in nodoc_methods:
                print "    %s" % k

                docs = inspect.getdoc(v)
                if not docs:
                    raise dexy.exceptions.InternalDexyProblem("Must provide docstring for %s" % k)

                print ""
                print indent(docs, 8)
                print ""

                args, varargs, keywords, defaults = inspect.getargspec(v)

                if not source and len(args) > 1:
                    print "        Takes arguments. Run with -source option to see source code."


                if source:
                    source_code = textwrap.dedent(inspect.getsource(v))
                    if nocolor:
                        print indent(source_code, 8)
                    else:
                        formatter = pygments.formatters.TerminalFormatter()
                        lexer = PythonLexer()
                        print indent(highlight(source_code, lexer, formatter), 8)

                print ""

########NEW FILE########
__FILENAME__ = fcmds
import dexy.filter
import inspect

def fcmds_command(
        alias=False # Only print commands defined by this alias.
        ):
    """
    Prints a list of available filter commands.
    """
    if alias:
        filter_instances = [dexy.filter.Filter.create_instance(alias)]
    else:
        filter_instances = dexy.filter.Filter

    for filter_instance in filter_instances:
        cmds = filter_instance.filter_commands()
        if cmds:
            print "filter alias:", filter_instance.alias
            for command_name in sorted(cmds):
                docs = inspect.getdoc(cmds[command_name])
                if docs:
                    doc = docs.splitlines()[0]
                    print "    %s   # %s" % (command_name, doc)
                else:
                    print "    %s" % command_name
            print ''

def fcmd_command(
        alias=None, # The alias of the filter which defines the custom command
        cmd=None, # The name of the command to run
        **kwargs # Additional arguments to be passed to the command
        ):
    """
    Run a filter command.
    """
    filter_instance = dexy.filter.Filter.create_instance(alias)
    cmd_name = "docmd_%s" % cmd

    if not cmd_name in dir(filter_instance):
        msg = "%s is not a valid command. There is no method %s defined in %s"
        msgargs = (cmd, cmd_name, filter_instance.__class__.__name__)
        raise dexy.exceptions.UserFeedback(msg % msgargs)

    else:
        instance_method = getattr(filter_instance, cmd_name)
        # TODO use try/catch instead of inspect.ismethod
        if inspect.ismethod(instance_method):
            try:
                instance_method.__func__(filter_instance, **kwargs)
            except TypeError as e:
                print e.message
                print inspect.getargspec(instance_method.__func__)
                print inspect.getdoc(instance_method.__func__)
                raise

        else:
            msg = "expected %s to be an instance method of %s"
            msgargs = (cmd_name, filter_instance.__class__.__name__)
            raise dexy.exceptions.InternalDexyProblem(msg % msgargs)

########NEW FILE########
__FILENAME__ = filters
from dexy.commands.utils import template_text
from pygments import highlight
from pygments.lexers import PythonLexer
import dexy.filter
import inspect
import pygments.formatters

extra_nodoc_aliases = ('-',)

def filters_command(
        alias="", # Print docs for this filter.
        example=False, # Whether to run included examples (slower).
        nocolor=False, # Skip syntax highlighting if showing source code.
        source=False, # Print source code of filter.
        versions=False # Print the installed version of external software (slower).
        ):
    """
    Prints list of available filters or docs for a particular filter.
    """
    if alias:
        help_for_filter(alias, example, source, nocolor)
    else:
        list_filters(versions)

def help_for_filter(alias, run_example, show_source, nocolor):
    instance = dexy.filter.Filter.create_instance(alias)

    print ''
    print instance.setting('help')

    print ''
    print "aliases: %s" % ", ".join(instance.setting('aliases'))
    print "tags: %s" % ", ".join(instance.setting('tags'))
    print ''

    print "Converts from file formats:"
    for ext in instance.setting('input-extensions'):
        print "   %s" % ext
    print ''

    print "Converts to file formats:"
    for ext in instance.setting('output-extensions'):
        print "   %s" % ext
    print ''

    print('Settings:')
    for k in sorted(instance._instance_settings):
        if k in dexy.filter.Filter.nodoc_settings:
            continue
        if k in ('aliases', 'tags'):
            continue

        tup = instance._instance_settings[k]
        print "    %s" % k

        for line in inspect.cleandoc(tup[0]).splitlines():
            print "        %s" % line

        print "        default value: %s" % tup[1]
        print ''

    examples = instance.setting('examples')
    example_templates = {}
    for alias in examples:
        try:
            template_instance = dexy.template.Template.create_instance(alias)
            example_templates[alias] = template_instance
        except dexy.exceptions.InactivePlugin:
            pass

    if examples:
        print ''
        print "Examples for this filter:"
        for alias, template in example_templates.iteritems():
            print ''
            print "  %s" % alias
            print "            %s" % inspect.getdoc(template.__class__)

        if run_example:
            for alias, template in example_templates.iteritems():
                print ''
                print ''
                print "Running example: %s" % template.setting('help')
                print ''
                print ''
                print template_text(template)

    print ''
    print "For online docs see http://dexy.it/filters/%s" % alias
    print ''
    print "If you have suggestions or feedback about this filter,"
    print "please contact info@dexy.it"
    print ''

    if show_source:
        print ''
        source_code = inspect.getsource(instance.__class__)
        if nocolor:
            print source_code
        else:
            formatter = pygments.formatters.TerminalFormatter()
            lexer = PythonLexer()
            print highlight(source_code, lexer, formatter)

def list_filters(versions):
        print "Installed filters:"
        for filter_instance in dexy.filter.Filter:
            # Should we show this filter?
            no_aliases = not filter_instance.setting('aliases')
            no_doc = filter_instance.setting('nodoc')
            not_dexy = not filter_instance.__class__.__module__.startswith("dexy.")
            exclude = filter_instance.alias in extra_nodoc_aliases

            if no_aliases or no_doc or not_dexy or exclude:
                continue

            # generate version message
            if versions:
                if hasattr(filter_instance, 'version'):
                    version = filter_instance.version()
                    if version:
                        version_message = "Installed version: %s" % version
                    else:
                        msg = "'%s' failed, filter may not be available."
                        msgargs = filter_instance.version_command()
                        version_message = msg % msgargs
                else:
                    version_message = ""


            filter_help = "  " + filter_instance.alias + \
                    " : " + filter_instance.setting('help').splitlines()[0]

            if versions and version_message:
                filter_help += " %s" % version_message

            print filter_help

        print ''
        print "For more information about a particular filter,"
        print "use the -alias flag and specify the filter alias."
        print ''


########NEW FILE########
__FILENAME__ = grep
from dexy.batch import Batch
from dexy.commands.utils import init_wrapper
from dexy.data import Generic
from dexy.data import KeyValue
from dexy.data import Sectioned
from dexy.utils import defaults
from operator import attrgetter
import dexy.exceptions
import json
import sys

def grep_command(
        __cli_options=False, # nodoc
        contents=False, # print out the contents of each matched file
        expr="", # An expression partially matching document name.
        key="", # An exact document key
        keyexpr="", # Only search for keys matching this expression
        keylimit=10, # Maximum number of matching keys to print
        keys=False, # List keys in documents
        limit=10, # Maximum number of matching documents to print
        lines=False, # maximum number of lines of content to print
        **kwargs
        ):
    """
    Search for documents and sections within documents.

    Dexy must have already run successfully.

    You can search for documents based on exact key or inexpect expression. The
    number of documents returned is controlled by --limit.

    You can print all keys in found documents by requesting --keys, number of
    results is controlled by --keylimit.

    You can search the section names/keys in found documents by passing a
    --keyexpr

    You can print contents of documents by requesting --contents, number of
    lines of content can be controlled by --lines.

    This does not search contents of documents, just document names and
    internal section names.
    """

    artifactsdir = kwargs.get('artifactsdir', defaults['artifacts_dir'])
    wrapper = init_wrapper(locals())
    batch = Batch.load_most_recent(wrapper)
   
    if not batch:
        print "you need to run dexy first"
        sys.exit(1)
    else:
        if expr:
            matches = sorted([data for data in batch if expr in data.key],
                    key=attrgetter('key'))
        elif key:
            matches = sorted([data for data in batch if key == data.key],
                    key=attrgetter('key'))
        else:
            raise dexy.exceptions.UserFeedback("Must specify either expr or key")

        n = len(matches)
        if n > limit:
            print "only printing first %s of %s total matches" % (limit, n)
            matches = matches[0:limit]

        for match in matches:
            print_match(match, keys, keyexpr, contents, keylimit, lines)

def print_match(match, keys, keyexpr, contents, keylimit, lines):
    print match.key, "\tcache key:", match.storage_key

    if hasattr(match, 'keys'):
        if keyexpr:
            print_keys([key for key in match.keys() if keyexpr in key], keylimit, lines)
        elif keys:
            print_keys(match.keys(), keylimit, lines)

    if contents:
        if isinstance(match, Sectioned):
            for section_name, section_contents in match.data().iteritems():
                print "  section: %s" % section_name
                print
                print_contents(section_contents, lines)
                print
        elif isinstance(match, KeyValue):
            pass
        elif isinstance(match, Generic):
            try:
                json.dumps(unicode(match))
                print_contents(unicode(match), lines)
            except UnicodeDecodeError:
                print "  not printable"

def print_keys(pkeys, keylimit, lines):
    n = len(pkeys)
    if n > keylimit:
        pkeys = pkeys[0:keylimit]
    
    for key in pkeys:
        print '  ', key

    if n > keylimit:
        print "  only printed first %s of %s total keys" % (keylimit, n)

def print_contents(text, lines):
    text_lines = text.splitlines()
    for i, line in enumerate(text_lines):
        if lines and i > lines-1:
            continue
        print "  ", line

    if lines and lines < len(text_lines):
        print "   only printed first %s of %s total lines" % (lines, len(text_lines))

########NEW FILE########
__FILENAME__ = info
from dexy.batch import Batch
from dexy.commands.utils import init_wrapper
from dexy.commands.utils import print_indented
from dexy.commands.utils import print_rewrapped
from dexy.utils import defaults
from operator import attrgetter
import dexy.exceptions
import sys

### "info-keys"
info_attrs = [
        'name',
        'ext',
        'key'
        ]

info_methods = [
        'title',
        'basename',
        'filesize',
        'baserootname',
        'parent_dir',
        'long_name',
        'web_safe_document_key'
        ]

storage_methods = []
### @end

def links_command(
        **kwargs
        ):
    """
    Print list of links and sections found in dexy documents.
    """
    artifactsdir = kwargs.get('artifactsdir', defaults['artifacts_dir'])
    wrapper = init_wrapper(locals())
    batch = Batch.load_most_recent(wrapper)

    if not batch:
        print "you need to run dexy first"
        sys.exit(1)

    wrapper.setup_log()
    wrapper.batch = batch

    wrapper.add_lookups()

    if wrapper.lookup_nodes:
        print_indented("Nodes:")
    for label in sorted(wrapper.lookup_nodes):
        nodes = wrapper.lookup_nodes[label]
        if len(nodes) > 1:
            print ''
            print_indented("'%s'" % label, 2)
            print_indented("Multiple nodes match %s:" % label, 4)
            for node in nodes:
                print_indented(">> %r" % node, 6)
        elif len(nodes) == 0:
            print_indented("'%s'" % label, 2)
            print_indented("NO nodes match %s" % label, 4)
        else:
            node = nodes[0]
            print_indented("'%s'" % label, 2)
            print_indented("%r" % node, 4)
        print ''

    print ''

    if wrapper.lookup_sections:
        print_indented("Sections:")
    for label in sorted(wrapper.lookup_sections):
        node = wrapper.lookup_sections[label][0]
        print_indented("'%s'" % label, 2)
        print_indented("%r" % node, 4)
        print ''

### "info-com"
def info_command(
        __cli_options=False,
        expr="", # An expression partially matching document name.
        key="", # The exact document key.
        ws=False, # Whether to print website reporter keys and values.
        **kwargs
        ):
    """
    Prints metadata about a dexy document.

    Dexy must have already run successfully.

    You can specify an exact document key or an expression which matches part
    of a document name/key. The `dexy grep` command is available to help you
    search for documents and print document contents.
    """
    artifactsdir = kwargs.get('artifactsdir', defaults['artifacts_dir'])
    wrapper = init_wrapper(locals())
    wrapper.setup_log()
    batch = Batch.load_most_recent(wrapper)
    wrapper.batch = batch

    if expr:
        print "search expr:", expr
        matches = sorted([data for data in batch if expr in data.key],
                key=attrgetter('key'))
    elif key:
        matches = sorted([data for data in batch if key == data.key],
                key=attrgetter('key'))
    else:
        raise dexy.exceptions.UserFeedback("Must specify either expr or key")

    for match in matches:
        print ""
        print "  Info for Document '%s'" % match.key
        print ""
        print "  document output data type:", match.alias
        print ""

        print_indented("settings:", 2)
        for k in sorted(match._instance_settings):
            if not k in ('aliases', 'help'):
                print_indented("%s: %s" % (k, match.setting(k)), 4)

        print ""
        print_indented("attributes:", 2)
        for fname in sorted(info_attrs):
            print_indented("%s: %s" % (fname, getattr(match, fname)), 4)
        print ""
    
        print_indented("methods:", 2)
        for fname in sorted(info_methods):
            print_indented("%s(): %s" % (fname, getattr(match, fname)()), 4)
        print ""

        if storage_methods:
            print_indented("storage methods:", 2)
            for fname in sorted(storage_methods):
                print_indented("%s(): %s" % (fname, getattr(match.storage, fname)), 4)
            print ''

        if ws:
            print_indented("website reporter methods:", 2)
            print ''
            reporter = dexy.reporter.Reporter.create_instance('ws')
            reporter.wrapper = wrapper
            reporter.setup_navobj()
            reporter.help(match)
            print ''
            print_indented("active template plugins are:", 2)
            print_indented(", ".join(reporter.setting('plugins')), 4)
            print ''


        else:
            print_indented("For website reporter tags, run this command with -ws option", 4)
            print ''


        print_rewrapped("""For more information about methods available on this
        data type run `dexy datas -alias %s`""" % match.alias)

########NEW FILE########
__FILENAME__ = it
from dexy.commands.utils import init_wrapper
from dexy.utils import defaults
from operator import attrgetter
import dexy.exceptions
import os
import subprocess
import sys
import time

def dexy_command(
        __cli_options=False,
        artifactsdir=defaults['artifacts_dir'], # location of directory in which to store artifacts
        conf=defaults['config_file'], # name to use for configuration file
        configs=defaults['configs'], # list of doc config files to parse
        debug=defaults['debug'], # Prints stack traces, other debug stuff.
        directory=defaults['directory'], # Allow processing just a subdirectory.
        dryrun=defaults['dry_run'], # if True, just parse config and print batch info, don't run dexyT
        encoding=defaults['encoding'], # Default encoding. Set to 'chardet' to use chardet auto detection.
        exclude=defaults['exclude'], # comma-separated list of directory names to exclude from dexy processing
        excludealso=defaults['exclude_also'], # comma-separated list of directory names to exclude from dexy processing
        full=defaults['full'], # Whether to do a full run including tasks marked default: False
        globals=defaults['globals'], # global values to make available within dexy documents, should be KEY=VALUE pairs separated by spaces
        help=False, #nodoc
        h=False, #nodoc
        hashfunction=defaults['hashfunction'], # What hash function to use, set to crc32 or adler32 for more speed but less reliability
        include=defaults['include'], # Locations to include which would normally be excluded.
        logdir=defaults['log_dir'], # DEPRECATED
        logfile=defaults['log_file'], # name of log file
        logformat=defaults['log_format'], # format of log entries
        loglevel=defaults['log_level'], # log level, valid options are DEBUG, INFO, WARN
        nocache=defaults['dont_use_cache'], # whether to force dexy not to use files from the cache
        noreports=False, # if true, don't run any reports
        outputroot=defaults['output_root'], # Subdirectory to use as root for output
        pickle=defaults['pickle'], # library to use for persisting info to disk, may be 'c', 'py', 'json'
        plugins=defaults['plugins'], # additional python packages containing dexy plugins
        profile=defaults['profile'], # whether to run with cProfile. Arg can be a boolean, in which case profile saved to 'dexy.prof', or a filename to save to.
        r=False, # whether to clear cache before running dexy
        recurse=defaults['recurse'], # whether to include doc config files in subdirectories
        reports=defaults['reports'], # reports to be run after dexy runs, enclose in quotes and separate with spaces
        reset=False, # whether to clear cache before running dexy
        silent=defaults['silent'], # Whether to not print any output when running dexy
        strace=defaults['strace'], # Run dexy using strace (VERY slow)
        uselocals=defaults['uselocals'], # use cached local copies of remote URLs, faster but might not be up to date, 304 from server will override this setting
        target=defaults['target'], # Which target to run. By default all targets are run, this allows you to run only 1 bundle (and its dependencies).
        version=False, # For people who type -version out of habit
        writeanywhere=defaults['writeanywhere'] # Whether dexy can write files outside of the dexy project root.
    ):
    """
    Runs Dexy.
    """
    if h or help:
        return dexy.commands.help_command()

    if version:
        return dexy.commands.version_command()

    if r or reset:
        dexy.commands.dirs.reset_command(artifactsdir=artifactsdir, logdir=logdir)

    if silent:
        print "sorry, -silent option not implemented yet https://github.com/ananelson/dexy/issues/33"

    wrapper = init_wrapper(locals())
    wrapper.assert_dexy_dirs_exist()
    run_reports = (not noreports)

    try:
        if profile:
            run_dexy_in_profiler(wrapper, profile)

        elif strace:
            run_dexy_in_strace(wrapper, strace)
            run_reports = False

        else:
            start = time.time()
            wrapper.run_from_new()
            elapsed = time.time() - start
            print "dexy run finished in %0.3f%s" % (elapsed, wrapper.state_message())

    except dexy.exceptions.UserFeedback as e:
        handle_user_feedback_exception(wrapper, e)

    except KeyboardInterrupt:
        handle_keyboard_interrupt()

    except Exception as e:
        log_and_print_exception(wrapper, e)
        raise

    if run_reports and hasattr(wrapper, 'batch'):
        start_time = time.time()
        wrapper.report()
        print "dexy reports finished in %0.3f" % (time.time() - start_time)

it_command = dexy_command

def log_and_print_exception(wrapper, e):
    if hasattr(wrapper, 'log'):
        wrapper.log.error("An error has occurred.")
        wrapper.log.error(e)
        wrapper.log.error(e.message)
    import traceback
    traceback.print_exc()

def handle_user_feedback_exception(wrapper, e):
    if hasattr(wrapper, 'log'):
        wrapper.log.error("A problem has occurred with one of your documents:")
        wrapper.log.error(e.message)
    sys.stderr.write("ERROR: Oops, there's a problem processing one of your documents. Here is the error message:" + os.linesep)
    for line in e.message.splitlines():
        sys.stderr.write("  " + line + "\n")
    if not e.message.endswith(os.linesep) or e.message.endswith("\n"):
        sys.stderr.write(os.linesep)

def handle_keyboard_interrupt():
    sys.stderr.write("""
    ok, stopping your dexy run
    you might want to 'dexy reset' before running again\n""")
    sys.exit(1)

def run_dexy_in_profiler(wrapper, profile):
    # profile may be a boolean or the name of a file to use
    if isinstance(profile, bool):
        profile_filename = os.path.join(wrapper.artifacts_dir, "dexy.prof")
    else:
        profile_filename = profile

    # run dexy in profiler
    import cProfile
    print "running dexy with cProfile, writing profile data to %s" % profile_filename
    cProfile.runctx("wrapper.run_from_new()", None, locals(), profile_filename)

    # print report
    import pstats
    stats_output_file = os.path.join(wrapper.artifacts_dir, "profile-report.txt")

    with open(stats_output_file, 'w') as f:
        stat = pstats.Stats(profile_filename, stream=f)
        stat.sort_stats("cumulative")
        stat.print_stats()

    print "Report is in %s, profile data is in %s." % (stats_output_file, profile_filename)

def run_dexy_in_strace(wrapper, strace):
    if isinstance(strace, bool):
        strace_filename = 'dexy.strace'
    else:
        strace_filename = strace

    def run_command(command):
        proc = subprocess.Popen(
                   command,
                   shell=True,
                   stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE
                   )
        stdout, stderr = proc.communicate()
        print stdout

    commands = ( 
            "strace dexy --reports \"\" 2> %s" % strace_filename, # TODO pass command line args except for --strace option
            "echo \"calls to stat:\" ; grep \"^stat(\" %s | wc -l" % strace_filename,
            "echo \"calls to read:\" ; grep \"^read(\" %s | wc -l" % strace_filename,
            "echo \"calls to write:\" ; grep \"^write(\" %s | wc -l" % strace_filename,
            "grep \"^stat(\" %s | sort | uniq -c | sort -r -n > strace-stats.txt" % strace_filename,
            "grep \"^read(\" %s | sort | uniq -c | sort -r -n > strace-reads.txt" % strace_filename,
            "grep \"^write(\" %s | sort | uniq -c | sort -r -n > strace-writes.txt" % strace_filename,
        )

    for command in commands:
        run_command(command)

def targets_command(
        full=False, # Whether to just print likely pretty target names, or all names.
        **kwargs):
    """
    Prints a list of available targets, which can be run via "dexy -target name".
    """
    wrapper = init_wrapper(locals())
    wrapper.assert_dexy_dirs_exist()
    wrapper.to_valid()
    wrapper.to_walked()

    print "Targets you can pass to -target option:"
    for doc in sorted(wrapper.bundle_docs(), key=attrgetter('key')):
        print "  ", doc.key

    if full:
        print
        print "These targets are also available, with lower priority:"
        for doc in sorted(wrapper.non_bundle_docs(), key=attrgetter('key')):
            print "  ", doc.key
        print
        print """Target names can be matched exactly or with the first few characters,
in which case all matching targets will be run."""
    else:
        print
        print "Run this command with --full option for additional available target names."

########NEW FILE########
__FILENAME__ = nodes
from dexy.node import Node
from dexy.commands.utils import dummy_wrapper
import inspect

def nodes_command(
        alias = False # Print docs for a particular node type.
        ):
    """
    Prints available node types and their settings.
    """

    if not alias:
        # list all plugins
        for alias in sorted(Node.plugins):
            print alias

        print "For info on a particular node type run `dexy nodes -alias doc`"
    else:
        print_node_info(alias)


def print_node_info(alias):
    print alias

    _, settings = Node.plugins[alias]

    instance = Node.create_instance(alias, "dummy", dummy_wrapper())
    instance.update_settings(settings)

    print ''
    print instance.setting('help')
    print ''

    if len(instance._instance_settings) > 2:
        print('Settings:')

    for k in sorted(instance._instance_settings):
        if k in ('aliases', 'help',):
            continue

        tup = instance._instance_settings[k]
        print "    %s" % k

        for line in inspect.cleandoc(tup[0]).splitlines():
            print "        %s" % line

        print "        default value: %s" % tup[1]
        print ''

########NEW FILE########
__FILENAME__ = parsers
from dexy.utils import defaults
from dexy.commands.utils import dummy_wrapper
from dexy.parser import AbstractSyntaxTree
from dexy.parser import Parser

def parsers_command():
    wrapper = dummy_wrapper()
    ast = AbstractSyntaxTree(wrapper)

    processed_aliases = set()

    for alias in sorted(Parser.plugins):
        if alias in processed_aliases:
            continue

        parser = Parser.create_instance(alias, ast, wrapper)

        for alias in parser.aliases:
            processed_aliases.add(alias)

        print "%s Parser" % parser.__class__.__name__
        print ''
        print parser.setting('help')
        print ''
        print "aliases:"
        for alias in parser.aliases:
            print "  %s" % alias
        print ''

    print "Default parsers are: " + defaults['parsers']
    print ''
    print "Dexy will only look for config files to parse in the root directory"
    print "of your project unless --recurse is specified."
    print ''

########NEW FILE########
__FILENAME__ = reporters
from dexy.commands.utils import print_indented
from dexy.commands.utils import print_rewrapped
import dexy.reporter

def reporters_command(
        alias=False, # Print detailed information about the specified reporter.
        simple=False, # Only print report aliases, without other information.
        ):
    """
    List available reports which dexy can run.
    """
    if simple:
        for reporter in dexy.reporter.Reporter:
            print reporter.alias

    elif alias:
        nodoc_settings = ('aliases', 'help',)

        reporter = dexy.reporter.Reporter.create_instance(alias)

        print_indented("%s Reporter" % reporter.__class__.__name__)
        print ''

        print_indented("settings:")
        print ''
        for name in sorted(reporter._instance_settings):
            if name in nodoc_settings:
                continue

            docs, default_value = reporter._instance_settings[name]
            print_indented(name, 2)
            print_rewrapped(docs, 4)
            print_indented("(default: %r)" % default_value, 4)
            print ''

        reporter.help()

        print ''

    else:
        FMT = "%-15s %-9s %s"
    
        print FMT % ('alias', 'default', 'info')
        for reporter in dexy.reporter.Reporter:
            help_text = reporter.setting('help').splitlines()[0]
            default_text = reporter.setting('default') and 'true' or 'false'
            print FMT % (reporter.alias, default_text, help_text)

########NEW FILE########
__FILENAME__ = serve
import SimpleHTTPServer
import SocketServer
import dexy.reporter
import socket
import os
import sys
from dexy.utils import file_exists
from dexy.commands.utils import init_wrapper
import dexy.load_plugins

NO_OUTPUT_MSG = """Please run dexy first, or specify a directory to serve. \
For help run 'dexy help -on serve'"""

class SimpleHTTPAuthRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        if self.headers.getheader('Authorization') == None:
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="%s"' % self.__class__.realm)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write("no authorization received")

        elif self.headers.getheader('Authorization') != "Basic %s" % self.__class__.authcode:
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="%s"' % self.__class__.realm)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write("not authenticated")

        else:
            path = self.translate_path(self.path)
            f = None
            if os.path.isdir(path):
                if not self.path.endswith('/'):
                    # redirect browser - doing basically what apache does
                    self.send_response(301)
                    self.send_header("Location", self.path + "/")
                    self.end_headers()
                    return None
                for index in "index.html", "index.htm":
                    index = os.path.join(path, index)
                    if os.path.exists(index):
                        path = index
                        break
                else:
                    return self.list_directory(path)
            ctype = self.guess_type(path)
            try:
                # Always read in binary mode. Opening files in text mode may cause
                # newline translations, making the actual size of the content
                # transmitted *less* than the content-length!
                f = open(path, 'rb')
            except IOError:
                self.send_error(404, "File not found")
                return None
            self.send_response(200)
            self.send_header("Content-type", ctype)
            fs = os.fstat(f.fileno())
            self.send_header("Content-Length", str(fs[6]))
            self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f

def serve_command(
        port=-1,
        reporters=['ws', 'output'], # Reporters whose output to try to serve (in order).
        username='', # http auth username to use (if provided)
        password='', # http auth password to use (if provided)
        realm='Dexy', # http auth realm to use (if username and password are provided)
        directory=False, # Custom directory to be served.
        **kwargs
        ):
    """
    Runs a simple web server on dexy-generated files.
    
    Will look first to see if the Website Reporter has run, if so this content
    is served. If not the standard output/ directory contents are served. You
    can also specify another directory to be served. The port defaults to 8085,
    this can also be customized. If a username and password are provided, uses
    HTTP auth to access pages.
    """

    if not directory:
        wrapper = init_wrapper(locals(), True)

        for alias in reporters:
            report_dir = dexy.reporter.Reporter.create_instance(alias).setting("dir")
            print "report dir", report_dir
            if report_dir and file_exists(report_dir):
                directory = report_dir
                break

    if not directory:
        print NO_OUTPUT_MSG
        sys.exit(1)

    os.chdir(directory)

    if port < 0:
        ports = range(8085, 8100)
    else:
        ports = [port]

    p = None
    for p in ports:
        try:
            if username and password:
                import base64
                authcode = base64.b64encode("%s:%s" % (username, password))
                Handler = SimpleHTTPAuthRequestHandler
                Handler.authcode = authcode
                Handler.realm = realm
            else:
                Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
            httpd = SocketServer.TCPServer(("", p), Handler)
        except socket.error:
            print "port %s already in use" % p
            p = None
        else:
            break

    if p:
        print "serving contents of %s on http://localhost:%s" % (directory, p)
        if username and password and Handler.authcode:
            print "username '%s' and password '%s' are required to access contents" % (username, password)
        print "type ctrl+c to stop"
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            sys.exit(1)
    else:
        print "could not find a free port to serve on, tried", ports
        sys.exit(1)

########NEW FILE########
__FILENAME__ = templates
from dexy.commands.utils import init_wrapper
from dexy.commands.utils import template_text
from dexy.utils import getdoc
import dexy.templates
import os
import sys
from dexy.utils import file_exists

DEFAULT_TEMPLATE = 'dexy:default'
def gen_command(
        plugins='', # extra python packages to load so plugins will register with dexy
        d=None,  # The directory to place generated files in, must not exist.
        t=False, # Shorter alternative to --template.
        template=DEFAULT_TEMPLATE, # The alias of the template to use.
        **kwargs # Additional kwargs passed to template's run() method.
        ):
    """
    Generate a new dexy project in the specified directory, using the template.
    """
    wrapper = init_wrapper(locals())

    if t and (template == DEFAULT_TEMPLATE):
        template = t
    elif t and template != DEFAULT_TEMPLATE:
        raise dexy.exceptions.UserFeedback("Only specify one of --t or --template, not both.")

    if not template in dexy.template.Template.plugins:
        print "Can't find a template named '%s'. Run 'dexy templates' for a list of templates." % template
        sys.exit(1)

    template_instance = dexy.template.Template.create_instance(template)
    template_instance.generate(d, **kwargs)

    # We run dexy setup. This will respect any dexy.conf file in the template
    # but passing command line options for 'setup' to 'gen' currently not supported.
    os.chdir(d)
    wrapper.create_dexy_dirs()
    print "Success! Your new dexy project has been created in directory '%s'" % d
    if file_exists("README"):
        print "\n--------------------------------------------------"
        with open("README", "r") as f:
            print f.read()
        print "\n--------------------------------------------------"
        print "\nThis information is in the 'README' file for future reference."

def template_command(
        alias=None
        ):
    print template_text(alias)

def templates_command(
        plugins='', # extra python packages to load so plugins will register with dexy
        simple=False, # Only print template names, without docstring or headers.
        validate=False, # Intended for developer use only, validate templates (runs and checks each template).
        key=False # Only print information which matches this search key.
        ):
    """
    List templates that can be used to generate new projects.
    """
    init_wrapper(locals())

    if not simple:
        FMT = "%-40s %s"
        print FMT % ("Alias", "Info")

    for i, template in enumerate(dexy.template.Template):
        if key:
            if not key in template.alias:
                continue

        if template.setting('nodoc'):
            continue

        if simple:
            print template.alias
        else:
            first_line_help = template.setting('help').splitlines()[0].strip()
            print FMT % (template.alias, first_line_help),
            if validate:
                print " validating...",
                print template.validate() and "OK" or "ERROR"
            else:
                print ''
    
    if i < 5:
        print "Run '[sudo] pip install dexy-templates' to install some more templates."

    if not simple:
        print "Run 'dexy help -on gen' for help on generating projects from templates."

########NEW FILE########
__FILENAME__ = utils
from dexy.utils import defaults
from dexy.utils import file_exists
from dexy.utils import parse_json
from dexy.utils import parse_yaml
from textwrap import TextWrapper
from textwrap import dedent
from inspect import cleandoc
import dexy.wrapper
import logging
import os
import yaml

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

RENAME_PARAMS = {
        'artifactsdir' : 'artifacts_dir',
        'conf' : 'config_file',
        'dbalias' : 'db_alias',
        'dbfile' : 'db_file',
        'disabletests' : 'disable_tests',
        'dryrun' : 'dry_run',
        'excludealso' : 'exclude_also',
        'ignore' : 'ignore_nonzero_exit',
        'logfile' : 'log_file',
        'logformat' : 'log_format',
        'loglevel' : 'log_level',
        'logdir' : 'log_dir',
        'nocache' : 'dont_use_cache',
        'outputroot' : 'output_root'
        }

def default_config():
    wrapper = dexy.wrapper.Wrapper()
    conf = wrapper.__dict__.copy()

    for k in conf.keys():
        if not k in defaults.keys():
            del conf[k]

    reverse_rename = dict((v,k) for k, v in RENAME_PARAMS.iteritems())
    for k in conf.keys():
        renamed_key = reverse_rename.get(k, k)
        if renamed_key != k:
            conf[renamed_key] = conf[k]
            del conf[k]

    return conf

def rename_params(kwargs):
    renamed_args = {}
    for k, v in kwargs.iteritems():
        renamed_key = RENAME_PARAMS.get(k, k)
        renamed_args[renamed_key] = v
    return renamed_args

def skip_params(kwargs):
    ok_params = {}
    for k, v in kwargs.iteritems():
        if k in defaults.keys():
            ok_params[k] = v
    return ok_params

def config_args(modargs):
    cliargs = modargs.get("__cli_options", {})
    kwargs = modargs.copy()

    config_file = modargs.get('conf', dexy.utils.defaults['config_file'])

    # Update from config file
    if file_exists(config_file):
        with open(config_file, "rb") as f:
            if config_file.endswith(".conf"):
                try:
                    conf_args = parse_yaml(f.read())
                except dexy.exceptions.UserFeedback as yaml_exception:
                    try:
                        conf_args = parse_json(f.read())
                    except dexy.exceptions.UserFeedback as json_exception:
                        print "--------------------------------------------------"
                        print "Tried to parse YAML:"
                        print yaml_exception
                        print "--------------------------------------------------"
                        print "Tried to parse JSON:"
                        print json_exception
                        print "--------------------------------------------------"
                        raise dexy.exceptions.UserFeedback("Unable to parse config file '%s' as YAML or as JSON." % config_file)

            elif config_file.endswith(".yaml"):
                conf_args = parse_yaml(f.read())
            elif config_file.endswith(".json"):
                conf_args = parse_json(f.read())
            else:
                raise dexy.exceptions.UserFeedback("Don't know how to load config from '%s'" % config_file)
            if conf_args:
                kwargs.update(conf_args)

    if cliargs: # cliargs may be False
        for k in cliargs.keys():
            try:
                kwargs[k] = modargs[k]
            except KeyError:
                msg = "This command does not take a '--%s' argument." % k
                raise dexy.exceptions.UserFeedback(msg)

    # TODO allow updating from env variables, e.g. DEXY_ARTIFACTS_DIR

    return kwargs

def import_plugins_from_local_yaml_file(import_target):
    if os.path.exists(import_target):
        with open(import_target, 'rb') as f:
            yaml_content = yaml.safe_load(f.read())

        for alias, info_dict in yaml_content.iteritems():
            if ":" in alias:
                prefix, alias = alias.split(":")
            else:
                prefix = 'filter'

            plugin_classes = dict((plugin_class.__name__.lower(), plugin_class)
                    for plugin_class in dexy.plugin.Plugin.__subclasses__())

            if not prefix in plugin_classes:
                msg = "'%s' not found, available aliases are %s"
                args = (prefix, ", ".join(plugin_classes.keys()))
                raise dexy.exceptions.UserFeedback(msg % args)

            cls = plugin_classes[prefix]

            if alias in cls.plugins:
                existing_plugin = cls.plugins[alias]
                plugin_settings = existing_plugin[1]
                plugin_settings.update(info_dict)
                cls.plugins[alias] = (existing_plugin[0], plugin_settings)
            else:
                cls.register_plugins_from_dict({alias : info_dict})

    else:
        # Don't raise exception if default files don't exist.
        if not import_target in defaults['plugins']:
            msg = "Could not find YAML file named '%s'" % import_target
            raise dexy.exceptions.UserFeedback(msg)

def import_plugins_from_local_python_file(import_target):
    if os.path.exists(import_target):
        import imp
        imp.load_source("custom_plugins", import_target)
    else:
        # Don't raise exception if default files don't exist.
        if not import_target in ('dexyplugin.py', 'dexyplugins.py',):
            msg = "Could not find python file named '%s'" % import_target
            raise dexy.exceptions.UserFeedback(msg)

def import_plugins_from_python_package(import_target):
    try:
        __import__(import_target)
    except ImportError:
        msg = "Could not find installed python package named '%s'" % import_target
        raise dexy.exceptions.UserFeedback(msg)

def import_extra_plugins(kwargs):
    if kwargs.get('plugins'):
        for import_target in kwargs.get('plugins').split():
            if import_target.endswith('.yaml'):
                import_plugins_from_local_yaml_file(import_target)
            elif import_target.endswith('.py'):
                import_plugins_from_local_python_file(import_target)
            else:
                import_plugins_from_python_package(import_target)

def init_wrapper(modargs, apply_defaults=False):
    if apply_defaults:
        modargs_with_defaults = defaults
        modargs_with_defaults.update(modargs)
    else:
        modargs_with_defaults = modargs
    
    kwargs = config_args(modargs_with_defaults)
    import_extra_plugins(kwargs)
    kwargs = rename_params(kwargs)
    kwargs = skip_params(kwargs)
    return dexy.wrapper.Wrapper(**kwargs)

def template_text(template):
    for wrapper in template.dexy(True):
        man_doc_key = 'doc:dexy.rst|jinja|rst2man'
        if man_doc_key in wrapper.nodes:
            man_doc = wrapper.nodes[man_doc_key].output_data().storage.data_file()

            import subprocess
            proc = subprocess.Popen(
                       ["man", man_doc],
                       stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT
                   )
            stdout, stderr = proc.communicate()
            return stdout
        else:
            return "no example found"

def dummy_wrapper():
    wrapper = dexy.wrapper.Wrapper()
    wrapper.log = logging.getLogger('dexy')
    wrapper.log.addHandler(NullHandler())
    wrapper.filemap = {}
    return wrapper

def rewrap_text(text, spaces=None, **kwargs):
    wrapper_args = {
            }

    if spaces:
        wrapper_args['initial_indent'] = ' ' * spaces
        wrapper_args['subsequent_indent'] = ' ' * spaces

    wrapper_args.update(kwargs)

    wrapper = TextWrapper(**wrapper_args)
    return wrapper.fill(cleandoc(text))

def indent_text(text, spaces):
    indented = []
    indent = " " * spaces
    for line in dedent(text).splitlines():
        indented.append("%s%s" % (indent, line))
    return "\n".join(indented)

def print_indented(text, spaces=0):
    print indent_text(text, spaces)

def print_rewrapped(text, spaces=0):
    print rewrap_text(text, spaces)

########NEW FILE########
__FILENAME__ = data
from dexy.exceptions import InternalDexyProblem
import dexy.plugin
import dexy.storage
import dexy.utils
import dexy.wrapper
import inflection
import os
import posixpath
import shutil
import urllib

class Data(dexy.plugin.Plugin):
    """
    Base class for types of Data.
    """
    __metaclass__ = dexy.plugin.PluginMeta
    _settings = {
            'shortcut' : ("A shortcut to refer to a file.", None),
            'storage-type' : ("Type of storage to use.", 'generic'),
            'canonical-output' : ("Whether this data type is canonical output.", None),
            'canonical-name' : ("The default name.", None),
            'output-name' : ("A custom name which overrides default name.", None),
            'title' : ("A custom title.", None),
            }

    state_transitions = (
            (None, 'new'),
            ('new', 'ready'),
            ('ready', 'ready')
            )

    def add_to_lookup_nodes(self):
        if self.setting('canonical-output'):
            self.wrapper.add_data_to_lookup_nodes(self.key, self)
            self.wrapper.add_data_to_lookup_nodes(self.output_name(), self)
            self.wrapper.add_data_to_lookup_nodes(self.title(), self)

    def add_to_lookup_sections(self):
        if self.setting('canonical-output'):
            for section_name in self.keys():
                if not section_name == '1':
                    self.wrapper.add_data_to_lookup_sections(section_name, self)

    def __init__(self, key, ext, storage_key, settings, wrapper):
        self.key = key
        self.ext = ext
        self.storage_key = storage_key

        self.wrapper = wrapper
        self.initialize_settings(**settings)
        self.update_settings(settings)

        self._data = None
        self.state = None
        self.name = self.setting('canonical-name')
        if not self.name:
            msg = "Document must provide canonical-name setting to data."
            raise InternalDexyProblem(msg)
        elif self.name.startswith("("):
            raise Exception()

        self.transition('new')
        
    def transition(self, new_state):
        """
        Transition between states in a state machine.
        """
        dexy.utils.transition(self, new_state)

    def args_to_data_init(self):
        """
        Returns tuple of attributes to pass to create_instance.
        """
        return (self.alias, self.key, self.ext, self.storage_key, self.setting_values())

    def setup(self):
        self.setup_storage()
        self.transition('ready')

    def setup_storage(self):
        storage_type = self.storage_class_alias(self.ext)
        instanceargs = (self.storage_key, self.ext, self.wrapper,)
        self.storage = dexy.storage.Storage.create_instance(storage_type, *instanceargs)

        self.storage.assert_location_is_in_project_dir(self.name)

        if self.output_name():
            self.storage.assert_location_is_in_project_dir(self.output_name())

        self.storage.setup()

    def storage_class_alias(self, file_ext):
        return self.setting('storage-type')

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self.key)

    def __lt__(self, other):
        """
        Sort data obejects by their output name.
        """
        return self.output_name() < other.output_name()

    def __str__(self):
        return unicode(self).encode("utf-8", errors="strict")

    def __getattr__(self, item):
        """
        Make setting values available as attributes.
        """
        try:
            return self._instance_settings[item]
        except KeyError:
            raise AttributeError

    def data(self):
        if (not self._data) or self._data == [{}]:
            self.load_data()
        return self._data

    def load_data(self, this=None):
        try:
            self._data = self.storage.read_data()
        except IOError:
            msg = "no data in file '%s' for %s (wrapper state '%s', data state '%s')"
            msgargs = (self.storage.data_file(), self.key,
                    self.wrapper.state, self.state)
            raise dexy.exceptions.InternalDexyProblem(msg % msgargs)

    def clear_data(self):
        self._data = None

    def clear_cache(self):
        self._size = None
        try:
            os.remove(self.storage.data_file())
        except os.error as e:
            self.wrapper.log.warn(unicode(e))

    def copy_from_file(self, filename):
        shutil.copyfile(filename, self.storage.data_file())

    def output_to_file(self, filepath):
        """
        Write canonical output to a file. Parent directory must exist already.
        """
        if not self.storage.copy_file(filepath):
            self.storage.write_data(self.data(), filepath)

    def has_data(self):
        has_loaded_data = (self._data) and (self._data != [{}])
        return has_loaded_data or self.is_cached()

    def set_data(self, data):
        """
        Shortcut to set and save data.
        """
        self._data = data
        self.save()

    def is_cached(self, this=None):
        if this is None:
            this = (self.wrapper.state in ('walked', 'running'))
        return self.storage.data_file_exists(this)

    # Filename-related Attributes

    def parent_dir(self):
        """
        The name of the directory containing the document.
        """
        return posixpath.dirname(self.name)

    def parent_output_dir(self):
        """
        The name of the directory containing the document based on final output
        name, which may be specified in a different directory.
        """
        return posixpath.dirname(self.output_name())

    def long_name(self):
        """
        A unique, but less canonical, name for the document.
        """
        if "|" in self.key:
            return "%s%s" % (self.key.replace("|", "-"), self.ext)
        else:
            return self.setting('canonical-name')

    def rootname(self):
        """
        Returns the file name, including path, without extension.
        """
        return os.path.splitext(self.name)[0]

    def basename(self):
        """
        Returns the local file name without path.
        """
        return posixpath.basename(self.name)

    def baserootname(self):
        """
        Returns local file name without extension or path.
        """
        return posixpath.splitext(self.basename())[0]

    def web_safe_document_key(self):
        """
        Returns document key with slashes replaced by double hypheens.
        """
        return self.long_name().replace("/", "--")

    def title(self):
        """
        Canonical title of document.

        Tries to guess from document name if `title` setting not provided.
        """
        if self.setting('title'):
            return self.setting('title')

        if self.is_index_page():
            subdir = posixpath.split(posixpath.dirname(self.name))[-1]
            if subdir == "/":
                return "Home"
            elif subdir:
                return inflection.titleize(subdir)
            else:
                return inflection.titleize(self.baserootname())
        else:
            return inflection.titleize(self.baserootname())

    def relative_path_to(self, relative_to):
        """
        Returns a relative path from this document to the passed other
        document.
        """
        return posixpath.relpath(relative_to, self.output_parent_dir())

    def strip(self):
        """
        Returns contents stripped of leading and trailing whitespace.
        """
        return unicode(self).strip()
    
    def splitlines(self, arg=None):
        """
        Returns a list of lines split at newlines or custom split.
        """
        return unicode(self).splitlines(arg)

    def url_quoted_name(self):
        """
        Applies urllib's quote method to name.
        """
        return urllib.quote(self.name)

    def output_name(self):
        """
        Canonical name to output to, relative to output root. Returns None if
        artifact not in output_root.
        """
        output_root = self.wrapper.output_root

        def relativize(path):
            if output_root == ".":
                return path
            elif os.path.abspath(output_root) in os.path.abspath(path):
                return os.path.relpath(path, output_root)

        output_name = self.setting('output-name')
        if output_name:
            return relativize(output_name)
        else:
            return relativize(self.name)

    def output_parent_dir(self):
        """
        Canonical output directory, taking into account custom outputroot and document name.
        """
        return os.path.dirname(self.output_name())
        
    def filesize(self, this=None):
        """
        Returns size of file stored on disk.
        """
        if this is None:
            this = (self.wrapper.state in ('walked', 'running'))
        return self.storage.data_file_size(this)

    def is_canonical_output(self):
        """
        Used by reports to determine if document should be written to output/
        directory.
        """
        return self.setting('canonical-output')

    def is_index_page(self):
        """
        Is this a website index page, i.e. named `index.html`.
        """
        return self.output_name() and self.output_name().endswith("index.html")

    def websafe_key(self):
        """
        Returns a web-friendly version of the key.
        """
        return self.key

    # Deprecated methods

    def as_text(self):
        """
        DEPRECATED. Instead call unicode.
        """
        return unicode(self)

class Generic(Data):
    """
    Data type representing generic binary or text-based data in a single blob.
    """
    aliases = ['generic']

    def save(self):
        if isinstance(self._data, unicode):
            self.storage.write_data(self._data.encode("utf-8"))
        else:
            if self._data == None:
                msg = "No data found for '%s', did you reference a file that doesn't exist?"
                raise dexy.exceptions.UserFeedback(msg % self.key)
            self.storage.write_data(self._data)

    def __unicode__(self):
        if isinstance(self.data(), unicode):
            return self.data()
        elif not self.data():
            return unicode(None)
        else:
            return self.wrapper.decode_encoded(self.data())

    def iteritems(self):
        """
        Iterable list of sections in document.
        """
        yield ('1', self.data())

    def items(self):
        """
        List of sections in document.
        """
        return [('1', self.data(),)]

    def keys(self):
        """
        List of keys (section names) in document.
        """
        return ['1']

    def __getitem__(self, key):
        if key == '1':
            return self.data()
        else:
            try:
                return self.data()[key]
            except TypeError:
                if self.ext == '.json':
                    return self.from_json()[key]
                elif self.ext == '.yaml':
                    return self.from_yaml()[key]
                else:
                    raise

    def from_json(self):
        """
        Attempts to load data using a JSON parser, returning whatever objects
        are defined in the JSON.
        """
        if self._data and isinstance(self._data, basestring):
            return dexy.utils.parse_json(self._data)
        elif self._data and not isinstance(self._data, basestring):
            raise Exception(self._data.__class__.__name__)
        else:
            with open(self.storage.data_file(), "r") as f:
                return dexy.utils.parse_json_from_file(f)

    def from_yaml(self):
        """
        Attempts to load data using a YAML parser, returning whatever objects
        are defined in the YAML.
        """
        if self._data and isinstance(self._data, basestring):
            return dexy.utils.parse_yaml(self._data)
        elif self._data and not isinstance(self._data, basestring):
            raise Exception(self._data.__class__.__name__)
        else:
            with open(self.storage.data_file(), "r") as f:
                return dexy.utils.parse_yaml(f.read())

    def json_as_dict(self):
        """
        DEPRECATED. Instead call from_json
        """
        return self.from_json()

class SectionValue(object):
    def __init__(self, data, parent, parentindex):
        assert isinstance(data, dict)
        self.data = data
        self.parent = parent
        self.parentindex = parentindex

    def __unicode__(self):
        return self.data['contents'] or u''

    def __str__(self):
        return self.data['contents'] or ''

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.parent.data()[self.parentindex+1][key] = value

    def splitlines(self):
        return unicode(self).splitlines()

class Sectioned(Data):
    """
    A document with named, ordered sections.

    Sections can also contain arbitrary metadata.
    """
    aliases = ['sectioned']

    _settings = {
            'storage-type' : 'jsonsectioned'
            }

    def setup(self):
        self.setup_storage()
        self._data = [{}]
        self.transition('ready')

    def save(self):
        try:
            self.storage.write_data(self._data)
        except Exception as e:
            msg = "Problem saving '%s': %s" % (self.key, str(e))
            raise dexy.exceptions.InternalDexyProblem(msg)

    def __unicode__(self):
        return u"\n".join(unicode(v) for v in self.values() if unicode(v))

    def __len__(self):
        """
        The number of sections.
        """
        return len(self.data())-1

    def __setitem__(self, key, value):
        keyindex = self.keyindex(key)
        if keyindex >= 0:
            # Existing section.
            assert self._data[keyindex+1]['name'] == key
            self._data[keyindex+1]['contents'] = value
        else:
            # New section.
            section_dict = {"name" : key, "contents" : value}
            self._data.append(section_dict)

    def __delitem__(self, key):
        index = self.keyindex(key)
        self.data().pop(index+1)

    def keys(self):
        return [a['name'] for a in self.data()[1:]]

    def values(self):
        return [SectionValue(a, self, i) for i, a in enumerate(self.data()[1:])]

    def output_to_file(self, filepath):
        """
        Write canonical (not structured) output to a file.
        """
        with open(filepath, "wb") as f:
            f.write(unicode(self).encode("utf-8"))

    def keyindex(self, key):
        if self._data == [{}]:
            return -1

        try:
            return self.keys().index(key)
        except ValueError:
            return -1

    def value(self, key):
        index = self.keyindex(key)
        if index > -1:
            return self.values()[index]
        else:
            try:
                return self.data()[0][key]
            except KeyError:
                msg = "No value for %s available in sections or metadata."
                msgargs = (key)
                raise dexy.exceptions.UserFeedback(msg % msgargs)

    def __getitem__(self, key):
        try:
            return self.data()[key+1]
        except TypeError:
            return self.value(key)

    def iteritems(self):
        """
        Iterable list of sections in document.
        """
        keys = self.keys()
        values = self.values()
        for i in range(len(keys)):
            yield (keys[i], values[i])

    def items(self):
        return [(key, value) for (key, value) in self.iteritems()]

class KeyValue(Data):
    """
    Data class for key-value data.
    """
    aliases  = ['keyvalue']
    _settings = {
            'storage-type' : 'sqlite3'
            }

    def __unicode__(self):
        return repr(self)

    def data(self):
        raise Exception("No data method for KeyValue type data.")

    def storage_class_alias(self, file_ext):
        if file_ext == '.sqlite3':
            return 'sqlite3'
        elif file_ext == '.json':
            return 'json'
        else:
            return self.setting('storage-type')

    def value(self, key):
        return self.storage[key]

    def like(self, key):
        try:
            return self.storage.like(key)
        except AttributeError:
            msg = "The `like()` method is not implemented for storage type '%s'"
            msgargs = self.storage.alias
            raise dexy.exceptions.UserFeedback(msg % msgargs)

    def __getitem__(self, key):
        return self.value(key)

    def append(self, key, value):
        self.storage.append(key, value)

    def query(self, query):
        return self.storage.query(query)

    def keys(self):
        return self.storage.keys()

    def items(self):
        """
        List of available keys.
        """
        return self.storage.items()

    def iteritems(self):
        """
        Iterable list of available keys.
        """
        return self.storage.iteritems()

    def save(self):
        try:
            self.storage.persist()
        except Exception as e:
            msg = u"Problem saving '%s': %s" % (self.key, unicode(e))
            raise dexy.exceptions.InternalDexyProblem(msg)

########NEW FILE########
__FILENAME__ = et
from dexy.data import Generic
import xml.etree.ElementTree as ET

class EtreeData(Generic):
    """
    Expose etree method to query XML using ElementTree.
    """
    aliases = ['etree']

    def etree(self):
        """
        Returns a tree root object.
        """
        if not hasattr(self, '_etree_root'):
            self._etree_root = ET.fromstring(self.data())
        return self._etree_root

########NEW FILE########
__FILENAME__ = h5
from dexy.data import Generic
from dexy.storage import GenericStorage
try:
    import tables
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

class H5(Generic):
    """
    Data type for reading HDF5 files using pytables.
    """
    aliases = ['h5']
    _settings = {
            'storage-type' : 'h5storage'
            }

    def is_active(self):
        return AVAILABLE

    def root(self):
        return self.data().root

    def walk_groups(self, path=None):
        if path:
            return self.data().walk_groups(path)
        else:
            return self.data().walk_groups()

    def walk_nodes(self, path=None, node_type=None):
        if path and node_type:
            return self.data().walk_nodes(path, node_type)
        elif path:
            return self.data().walk_nodes(path)
        else:
            return self.data().walk_nodes()

class H5Storage(GenericStorage):
    """
    Storage backend representing HDF5 files.
    """
    aliases = ['h5storage']

    def is_active(self):
        return AVAILABLE

    def read_data(self):
        return tables.open_file(self.data_file(read=True), "r")

if AVAILABLE:
    # Set custom exit hook so messages about closing files don't get printed to
    # stderr, per http://www.pytables.org/moin/UserDocuments/AtexitHooks
    def my_close_open_files(verbose):
        open_files = tables.file._open_files
        are_open_files = len(open_files) > 0
        if verbose and are_open_files:
            print >> sys.stderr, "Closing remaining open files:",
        for fileh in open_files.keys():
            if verbose:
                print >> sys.stderr, "%s..." % (open_files[fileh].filename,),
            open_files[fileh].close()
            if verbose:
                print >> sys.stderr, "done",
        if verbose and are_open_files:
            print >> sys.stderr
    import sys, atexit
    atexit.register(my_close_open_files, False)

########NEW FILE########
__FILENAME__ = soup
from dexy.data import Generic
try:
    from bs4 import BeautifulSoup
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

class BeautifulSoupData(Generic):
    """
    Allow querying HTML using BeautifulSoup.
    """
    aliases = ['bs4']

    def soup(self):
        """
        Returns a BeautifulSoup object initialized with contents.
        """
        if not hasattr(self, '_soup'):
            self._soup = BeautifulSoup(self.data())
        return self._soup

    def select(self, query):
        """
        Returns a list of results from a CSS query.
        """
        return self.soup().select(query) 

    def select_one(self, query):
        """
        Returns a single result from a CSS query. Result must be unique.
        """
        selects = self.select(query)
        if not len(selects) == 1:
            raise Exception("Select on '%s' was not unique.")
        return selects[0]

    def __getitem__(self, key):
        return self.select_one(key)

########NEW FILE########
__FILENAME__ = doc
import dexy.exceptions
import dexy.filter
import dexy.node
import os
import shutil
import stat
import time

class Doc(dexy.node.Node):
    """
    A single Dexy document.
    """
    aliases = ['doc']
    _settings = {
            'contents' : (
                "Custom contents for a virtual document.",
                None
                ),
            'ws-template' : (
                "custom website template to apply.",
                None
                ),
            'data-type' : (
                "Alias of custom data class to use to store document content.",
                None
                ),
            'shortcut' : (
                "A nickname for document so you don't have to use full key.",
                None
                ),
            'title' : (
                "Custom title.",
                None
                ),
            'output-name' : (
                "Override default canonical name.",
                None
                ),
            'output' : (
                "Whether document should be included in output/ and output-site/",
                None
                )
            }

    def name_args(self):
        name_args = self.setting_values()
        name_args['name'] = self.name
        name_args['dirname'] = os.path.dirname(self.name)
        name_args.update(self.safe_setting('environment', {}))
        return name_args

    def setup_output_name(self):
        """
        Applies string interpolation to %(foo)s settings in output name.
        """
        if not self.setting('output-name'):
            return

        name_args = self.name_args()
        output_name = self.setting('output-name')

        self.log_debug("Name interpolation variables:")
        for key, value in name_args.iteritems():
            self.log_debug("%s: %s" % (key, value))

        if not "/" in output_name:
            output_name = os.path.join(os.path.dirname(self.name), output_name)
        elif output_name.startswith("/"):
            output_name = output_name.lstrip("/")

        try:
            if '%' in output_name:
                updated_output_name = output_name % name_args
            elif '{' in self.setting('output-name'):
                updated_output_name = output_name.format(**name_args)
            else:
                updated_output_name = output_name

        except KeyError as e:
            msg = "Trying to process %s but '%s' is not a valid key. Valid keys are: %s"
            msgargs = (output_name, unicode(e), ", ".join(sorted(name_args)))
            raise dexy.exceptions.UserFeedback(msg % msgargs)

        self.update_settings({'output-name' : updated_output_name})

    def setup(self):
        self.update_settings(self.args)

        self.name = self.key.split("|")[0]
        self.ext = os.path.splitext(self.name)[1]
        self.filter_aliases = self.key.split("|")[1:]
        self.filters = []

        self.setup_output_name()
        self.setup_initial_data()

        for alias in self.filter_aliases:
            f = dexy.filter.Filter.create_instance(alias, self)
            self.filters.append(f)

        prev_filter = None
        for i, f in enumerate(self.filters):
            filter_aliases = self.filter_aliases[0:i+1]
            filter_key = "%s|%s" % (self.name, "|".join(filter_aliases))
            storage_key = "%s-%03d-%s" % (self.hashid, i+1, "-".join(filter_aliases))

            if i < len(self.filters) - 1:
                next_filter = self.filters[i+1]
            else:
                next_filter = None

            filter_settings_from_args = self.args.get(f.alias, {})
            f.setup(filter_key, storage_key, prev_filter,
                    next_filter, filter_settings_from_args)
            prev_filter = f

    def setup_datas(self):
        """
        Convenience function to ensure all datas are set up. Should not need to be called normally.
        """
        for d in self.datas():
            if d.state == 'new':
                d.setup()

    def setup_initial_data(self):
        storage_key = "%s-000" % self.hashid

        if self.setting('output') is not None:
            canonical_output = self.setting('output')
        else:
            if len(self.filter_aliases) == 0:
                canonical_output = True
            else:
                canonical_output = None

        settings = {
                'canonical-name' : self.name,
                'canonical-output' : canonical_output,
                'shortcut' : self.setting('shortcut'),
                'output-name' : self.setting('output-name'),
                'title' : self.setting('title')
                }

        self.initial_data = dexy.data.Data.create_instance(
                self.data_class_alias(),
                self.name, # key
                self.ext, #ext
                storage_key,
                settings,
                self.wrapper
                )

    def consolidate_cache_files(self):
        for node in self.input_nodes():
            node.consolidate_cache_files()

        if self.state == 'cached':
            self.setup_datas()

            # move cache files to new cache
            for d in self.datas():
                if os.path.exists(d.storage.last_data_file()):
                    shutil.move(d.storage.last_data_file(), d.storage.this_data_file())
                    self.log_debug("Moving %s from %s to %s" % (d.key, d.storage.last_data_file(), d.storage.this_data_file()))

            if os.path.exists(self.runtime_info_filename(False)):
                shutil.move(self.runtime_info_filename(False), self.runtime_info_filename(True))

            self.apply_runtime_info()

            for d in self.datas():
                if hasattr(d.storage, 'connect'):
                    d.storage.connect()
            self.transition('consolidated')

    def apply_runtime_info(self):
            runtime_info = self.load_runtime_info()
            if runtime_info:
                self.add_runtime_args(runtime_info['runtime-args'])
                self.load_additional_docs(runtime_info['additional-docs'])

    def datas(self):
        """
        Returns all associated `data` objects.
        """
        return [self.initial_data] + [f.output_data for f in self.filters]

    def update_setting(self, key, value):
        self.update_all_settings({key : value})

    def update_all_settings(self, new_settings):
        self.update_settings(new_settings)

        for data in self.datas():
            data.update_settings(new_settings)

        for f in self.filters:
            f.update_settings(new_settings)

    def check_cache_elements_present(self):
        """
        Returns a boolean to indicate whether all files are present in cache.
        """
        # Take this opportunity to ensure Data objects are in `setup` state.
        for d in self.datas():
            if d.state == 'new':
                d.setup()

        return all(
                os.path.exists(d.storage.last_data_file()) or
                os.path.exists(d.storage.this_data_file())
                for d in self.datas())

    def check_doc_changed(self):
        if self.name in self.wrapper.filemap:
            live_stat = self.wrapper.filemap[self.name]['stat']

            self.initial_data.setup()

            in_this_cache = os.path.exists(self.initial_data.storage.this_data_file())
            in_last_cache = os.path.exists(self.initial_data.storage.last_data_file())

            if in_this_cache or in_last_cache:
                # we have a file in the cache from a previous run, compare its
                # mtime to filemap to determine whether it has changed
                if in_this_cache:
                    cache_stat = os.stat(self.initial_data.storage.this_data_file())
                else:
                    cache_stat = os.stat(self.initial_data.storage.last_data_file())

                cache_mtime = cache_stat[stat.ST_MTIME]
                live_mtime = live_stat[stat.ST_MTIME]
                msg = "    cache mtime %s live mtime %s now %s changed (live gt cache) %s"
                msgargs = (cache_mtime, live_mtime, time.time(), live_mtime > cache_mtime)
                self.log_debug(msg % msgargs)
                return live_mtime > cache_mtime
            else:
                # there is no file in the cache, therefore it has 'changed'
                return True
        else:
            # TODO check hash of contents of virtual files
            return False

    def data_class_alias(self):
        data_class_alias = self.setting('data-type')

        if data_class_alias:
            return data_class_alias
        else:
            contents = self.get_contents()
            if isinstance(contents, dict):
                return 'keyvalue'
            elif isinstance(contents, list):
                return "sectioned"
            else:
                return 'generic'

    def get_contents(self):
        contents = self.setting('contents')
        return contents

    # Runtime Info
    def runtime_info_filename(self, this=True):
        name = "%s.runtimeargs.pickle" % self.hashid
        return os.path.join(self.initial_data.storage.storage_dir(this), name)

    def save_runtime_info(self):
        """
        Save runtime changes to metadata so they can be reapplied when node has
        been cached.
        """

        info = {
            'runtime-args' : self.runtime_args,
            'additional-docs' : self.additional_doc_info()
            }

        with open(self.runtime_info_filename(), 'wb') as f:
            pickle = self.wrapper.pickle_lib()
            pickle.dump(info, f)

    def load_runtime_info(self):
        info = None

        # Load from 'this' first
        try:
            with open(self.runtime_info_filename(), 'rb') as f:
                pickle = self.wrapper.pickle_lib()
                info = pickle.load(f)
        except IOError:
            pass

        # Load from 'last' if there's nothing in 'this'
        if not info:
            try:
                with open(self.runtime_info_filename(False), 'rb') as f:
                    pickle = self.wrapper.pickle_lib()
                    info = pickle.load(f)
            except IOError:
                pass

        return info

    def run(self):
        if self.wrapper.directory != '.':
            if not self.wrapper.directory in self.name:
                print "skipping", self.name, "not in", self.wrapper.directory
                return

        self.start_time = time.time()

        if self.name in self.wrapper.filemap:
            # This is a real file on the file system.
            if self.doc_changed or not self.initial_data.is_cached():
                self.initial_data.copy_from_file(self.name)
        else:
            is_dummy = self.initial_data.is_cached() and self.get_contents() == 'dummy contents'
            if is_dummy:
                self.initial_data.load_data()
            else:
                self.initial_data.set_data(self.get_contents())

        for f in self.filters:
            f.start_time = time.time()
            if f.output_data.state == 'new':
                f.output_data.setup()
            if hasattr(f.output_data.storage, 'connect'):
                f.output_data.storage.connect()
            f.process()
            f.finish_time = time.time()
            f.elapsed = f.finish_time - f.start_time

        self.finish_time = time.time()
        self.elapsed_time = self.finish_time - self.start_time
        self.wrapper.batch.add_doc(self)
        self.save_runtime_info()

        # Run additional docs
        for doc in self.additional_docs:
            doc.check_is_cached()
            for task in doc:
                task()

    def output_data(self):
        """
        Returns a reference to the final data object for this document.
        """
        if self.filters:
            return self.filters[-1].output_data
        else:
            return self.initial_data

    def batch_info(self):
        return {
                'input-data' : self.initial_data.args_to_data_init(),
                'output-data' : self.output_data().args_to_data_init(),
                'filters-data' : [f.output_data.args_to_data_init() for f in self.filters],
                # below are convenience attributes, not strictly necessary for dexy to run
                'title' : self.output_data().title(),
                'start_time' : self.start_time,
                'finish_time' : self.finish_time,
                'elapsed' : self.elapsed_time,
                'state' : self.state
                }

########NEW FILE########
__FILENAME__ = exceptions
from dexy.version import DEXY_VERSION
import dexy.utils
import platform
from cashew.exceptions import UserFeedback
from cashew.exceptions import InactivePlugin

class NoFilterOutput(UserFeedback):
    pass

class CircularDependency(UserFeedback):
    pass

class BlankAlias(UserFeedback):
    pass

class InvalidStateTransition(Exception):
    pass

class UnexpectedState(Exception):
    pass

class InternalDexyProblem(Exception):
    def __init__(self, message):
        self.message = dexy.utils.s("""
        Oops! You may have found a bug in Dexy.
        The developer would really appreciate if you copy and paste this entire message
        and the Traceback above it into an email and send to info@dexy.it
        Your version of Dexy is %s
        Your platform is %s""" % (DEXY_VERSION, platform.system()))
        self.message += "\n"
        self.message += message

    def __str__(self):
        return self.message

class DeprecatedException(InternalDexyProblem):
    pass

class TemplateException(InternalDexyProblem):
    pass

########NEW FILE########
__FILENAME__ = filter
from dexy.utils import copy_or_link
from dexy.utils import os_to_posix
from operator import attrgetter
import dexy.doc
import dexy.exceptions
import dexy.plugin
import dexy.utils
import os
import posixpath

class FilterException(Exception):
    pass

class Filter(dexy.plugin.Plugin):
    """
    Base class for types of filter.
    """
    __metaclass__ = dexy.plugin.PluginMeta

    TAGS = []
    _class_settings = {'max-docstring-length' : 75}
    nodoc_settings = [
            'help', 'nodoc'
            ]
    _settings = {
            'added-in-version' : (
                "Dexy version when this filter was first available.",
                ''),
            'add-new-files' : (
                "Boolean or list of extensions/patterns to match.",
                False),
            'exclude-add-new-files' : (
                "List of patterns to skip even if they match add-new-files.",
                []),
            'exclude-new-files-from-dir' : (
                "List of directories to skip when adding new files.",
                []),
            'additional-doc-filters' : (
                "Filters to apply to additional documents created as side effects.",
                {}),
            'additional-doc-settings' : (
                "Settings to apply to additional documents created as side effects.",
                {}),
            'examples' : (
                "Templates which should be used as examples for this filter.",
                []),
            'ext' : (
                'File extension to output.',
                None),
            'extension-map' : (
                "Dictionary mapping input extensions to default output extensions.",
                None),
            'help' : (
                'Help string for filter, if not already specified as a class docstring.',
                None),
            'input-extensions' : (
                "List of extensions which this filter can accept as input.",
                [".*"]),
            'keep-originals' : (
                """Whether, if additional-doc-filters are specified, the
                original unmodified docs should also be added.""",
                False),
            'mkdir' : (
                "A directory which should be created in working dir.",
                None),
            'mkdirs' : (
                "A list of directories which should be created in working dir.",
                []),
            'nodoc' : (
                "Whether filter should be excluded from documentation.",
                False),
            'output' : (
                """Whether to output results of this filter by default by
                reporters such as 'output' or 'website'.""",
                False),
            'data-type' : (
                "Alias of custom data class to use to store filter output.",
                "generic"),
            'output-extensions' : (
                "List of extensions which this filter can produce as output.",
                [".*"]),
            'preserve-prior-data-class' : (
                "Whether output data class should be set to match the input data class.",
                False),
            'require-output' : (
                "Should dexy raise an exception if no output is produced by this filter?",
                True),
            'tags' : (
                "Tags which describe the filter.",
                []),
            'variables' : (
                'A dictionary of variable names and values to make available to this filter.',
                {}),
            'vars' : (
                'A dictionary of variable names and values to make available to this filter.',
                {}),
            'workspace-exclude-filters' : (
                "Filters whose output should be excluded from workspace.",
                ['pyg']),
            'override-workspace-exclude-filters' : (
                """If True, document will be populated to other workspaces
                ignoring workspace-exclude-filters.""", False),
            'workspace-includes' : (
                """If set to a list of filenames or extensions, only these will
                be populated to working dir.""",
                None)
            }

    def __init__(self, doc=None):
        self.doc = doc

    def filter_commands(self):
        """
        Return dictionary of filter command canonical names and method objects.
        """
        fcmds = {}
        for m in dir(self):
            if m.startswith("docmd_"):
                key = m.replace("docmd_", "")
                fcmds[key] = getattr(self, m)
        return fcmds

    def final_ext(self):
        return self.doc.output_data().ext

    def data_class_alias(self, ext):
        if self.setting('preserve-prior-data-class'):
            return self.input_data.alias
        else:
            return self.setting('data-type')

    def add_runtime_args(self, new_args):
        self.doc.add_runtime_args(new_args)

    def update_all_args(self, new_args):
        self.doc.add_runtime_args(new_args)

    def setup(self, key, storage_key, prev_filter, next_filter, custom_settings):
        self.key = key
        self.storage_key = storage_key
        self.prev_filter = prev_filter
        self.next_filter = next_filter

        self.update_settings(custom_settings)

        if self.prev_filter:
            self.input_data = self.prev_filter.output_data
            self.prev_ext = self.prev_filter.ext
        else:
            self.input_data = self.doc.initial_data
            self.prev_ext = self.doc.initial_data.ext

        self.set_extension()

        settings = self.input_data.setting_values()

        del settings['storage-type']
        del settings['aliases']
        
        settings.update({
                'canonical-name' : self.calculate_canonical_name(),
                'canonical-output' : self.is_canonical_output()
                })

        self.output_data = dexy.data.Data.create_instance(
                self.data_class_alias(self.ext),
                self.key,
                self.ext,
                self.storage_key,
                settings,
                self.doc.wrapper
                )

    def is_canonical_output(self):
        if self.input_data.setting('canonical-output') == True:
            return True
        elif (self.input_data.setting('canonical-output') == False):
            return False
        elif self.setting('output'):
            return True
        else:
            return None

    def set_extension(self):
        i_accept = self.setting('input-extensions')
        i_output = self.setting('output-extensions')

        if self.prev_filter:
            prev_ext = self.prev_filter.ext
        else:
            prev_ext = self.doc.ext

        # Check that we can handle input extension
        if set([prev_ext, ".*"]).isdisjoint(set(i_accept)):
            msg = "Filter '%s' in '%s' can't handle file extension %s, supported extensions are %s"
            params = (self.alias, self.key, prev_ext, ", ".join(i_accept))
            raise dexy.exceptions.UserFeedback(msg % params)

        # Figure out output extension
        ext = self.setting('ext')
        if ext:
            # User has specified desired extension
            if not ext.startswith('.'):
                ext = '.%s' % ext

            # Make sure it's a valid one
            if (not ext in i_output) and (not ".*" in i_output):
                msg = "You have requested file extension %s in %s but filter %s can't generate that."
                raise dexy.exceptions.UserFeedback(msg % (ext, self.key, self.alias))

            self.ext = ext

        elif ".*" in i_output:
            self.ext = prev_ext

        else:
            # User has not specified desired extension, and we don't output wildcards,
            # figure out extension based on next filter in sequence, if any.
            ext_from_map = None
            if self.setting('extension-map'):
                ext_from_map = self.setting('extension-map')[prev_ext]

            next_filter_accepts = [".*"]
            if self.next_filter:
                next_filter_accepts = self.next_filter.setting('input-extensions')

            if ".*" in next_filter_accepts:
                if ext_from_map:
                    self.ext = ext_from_map
                else:
                    self.ext = i_output[0]

            elif ext_from_map:
                if not ext_from_map in next_filter_accepts:
                    msg = "Filter %s wants to output %s but %s doesn't accept this format."
                    msgargs = (self.alias, ext_from_map, self.next_filter.alias)
                    raise dexy.exceptions.UserFeedback(msg % msgargs)

                self.ext = ext_from_map

            else:
                if set(i_output).isdisjoint(set(next_filter_accepts)):
                    msg = "Filter %s can't go after filter %s, no file extensions in common."
                    raise dexy.exceptions.UserFeedback(msg % (self.next_filter.alias, self.alias))

                for e in i_output:
                    if e in next_filter_accepts:
                        self.ext = e

                if not self.ext:
                    msg = "no file extension found but checked already for disjointed, should not be here"
                    raise dexy.exceptions.InternalDexyProblem(msg)

    def templates(self):
        """
        List of dexy templates which refer to this filter.
        """
        import dexy.template
        templates = [dexy.template.Template.create_instance(a) for a in self.setting('examples')]
        return templates

    def key_with_class(self):
        return "%s:%s" % (self.__class__.__name__, self.key)

    def log_debug(self, message):
        self.doc.log_debug(message)

    def log_info(self, message):
        self.doc.log_info(message)

    def log_warn(self, message):
        self.doc.log_warn(message)

    def process(self):
        """
        Run the filter, converting input to output.
        """
        pass

    def calculate_canonical_name(self):
        name_without_ext = posixpath.splitext(self.doc.name)[0]
        return "%s%s" % (name_without_ext, self.ext)

    def output_filepath(self):
        return self.output_data.storage.data_file()

    def doc_arg(self, arg_name_hyphen, default=None):
        return self.doc.arg_value(arg_name_hyphen, default)

    def add_doc(self, doc_name, doc_contents=None, doc_args = None):
        """
        Creates a new Doc object for an on-the-fly document.
        """
        doc_name = os_to_posix(doc_name)
        if not posixpath.sep in doc_name:
            doc_name = posixpath.join(self.input_data.parent_dir(), doc_name)

        doc_ext = os.path.splitext(doc_name)[1]

        additional_doc_filters = self.setting('additional-doc-filters')
        self.log_debug("additional-doc-filters are %s" % additional_doc_filters)

        
        additional_doc_settings = self.setting('additional-doc-settings')

        settings = None
        if isinstance(additional_doc_settings, list):
            # figure out which settings to apply based on file extension
            for pattern, settings in additional_doc_settings:
                if doc_ext == pattern or pattern == ".*":
                    break
        elif isinstance(additional_doc_settings, dict):
            settings = additional_doc_settings

        else:
            raise Exception("Unexpected type %s" % type(settings))

        if doc_args:
            settings.update(doc_args)

        self.log_debug("additional-doc-settings are %s" % settings)


        def create_doc(name, filters, contents, args=None):
            if filters:
                doc_key = "%s|%s" % (name, filters)
            else:
                doc_key = name

            if not args:
                args = {}

            doc = dexy.doc.Doc(
                    doc_key,
                    self.doc.wrapper,
                    [],
                    contents=contents,
                    **args
                    )

            doc.output_data().setup()
            doc.output_data().storage.connect()

            self.doc.add_additional_doc(doc)
            return doc

        doc = None

        if isinstance(additional_doc_filters, basestring):
            doc = create_doc(doc_name,
                    additional_doc_filters, doc_contents, settings)

        elif isinstance(additional_doc_filters, list):
            for f in reversed(additional_doc_filters):
                doc = create_doc(doc_name, f, doc_contents, settings)

        elif isinstance(additional_doc_filters, dict):
            filters = additional_doc_filters.get(doc_ext)
            if isinstance(filters, list):
                for f in filters:
                    doc = create_doc(doc_name, f, doc_contents, settings)
            elif isinstance(filters, basestring):
                doc = create_doc(doc_name, filters, doc_contents, settings)
            elif filters is None:
                pass
            else:
                msg = "additional_doc_filters values should be list of string. Received %s"
                msgargs = filters.__class__.__name__
                raise Exception(msg % msgargs)

        else:
            msg = "additional-doc-filters should be string, list or dict. Received %s"
            msgargs = additional_doc_filters.__class__.__name__
            raise dexy.exceptions.InternalDexyProblem(msg % msgargs)

        if self.setting('keep-originals') or doc is None:
            doc = create_doc(doc_name, '', doc_contents, settings)

        return doc

    def workspace(self):
        """
        Directory in which all working files for this filter are stored.

        The `populate_workspace` method will populate this directory with
        inputs to this filter.
        """
        ws = self.doc.wrapper.work_cache_dir()
        return os.path.join(ws, self.storage_key[0:2], self.storage_key)

    def parent_work_dir(self):
        """
        Within the 'workspace', this is the parent directory of the file to be
        processed. This is the directory which subprocess/pexpect will 'cwd' to
        and execute processes.
        """
        return os.path.join(self.workspace(), self.output_data.parent_dir())

    def work_input_filename(self):
        """
        Name of work file to use input from. Processes will take this file name
        as input. Does not contain full path to file, just the file name. File
        will be in parent_work_dir() and processes should set their working
        directory to parent_work_dir() before running.
        """
        if self.ext and (self.ext == self.prev_ext):
            return "%s-work%s" % (self.input_data.baserootname(), self.prev_ext)
        else:
            return self.input_data.basename()

    def work_input_filepath(self):
        return os.path.join(self.parent_work_dir(), self.work_input_filename())

    def work_output_filename(self):
        """
        Name of work file to save output to. Processes will take this file name
        as output. Does not contain full path to file, just the file name. File
        will be in parent_work_dir() and processes should set their working
        directory to parent_work_dir() before running.
        """
        return self.output_data.basename()

    def work_output_filepath(self):
        return os.path.join(self.parent_work_dir(), self.work_output_filename())

    def include_input_in_workspace(self, inpt):
        """
        Whether to include the contents of the input file inpt in the workspace
        for this filter.
        """
        workspace_includes = self.setting('workspace-includes')

        if workspace_includes is not None:
            if inpt.ext in workspace_includes:
                self.log_debug("Including %s because file extension matches." % inpt)
                return True
            elif inpt.output_data().basename() in workspace_includes:
                self.log_debug("Including %s because base name matches." % inpt)
                return True
            else:
                self.log_debug("Excluding %s because does not match workspace-includes" % inpt)
                return False

        elif not inpt.filters:
            self.log_debug("Including because %s has no filters." % inpt)
            return True

        elif inpt.filters[-1].setting('override-workspace-exclude-filters'):
            self.log_debug("Including %s because override-workspace-exclude-filters is set." % inpt)
            return True

        else:
            workspace_exclude_filters = self.setting('workspace-exclude-filters')

            if workspace_exclude_filters is None:
                self.log_debug("Including because exclude_filters is None.")
                return True
            elif any(a in workspace_exclude_filters for a in inpt.filter_aliases):
                self.log_debug("Excluding %s because of workspace-exclude-filters" % inpt)
                return False
            else:
                self.log_debug("Including %s because not excluded" % inpt)
                return True

    def makedirs(self):
        mkdirs = self.setting('mkdirs')

        # mkdir should be a string, but handle either string or list
        mkdir = self.setting('mkdir')
        if mkdir:
            if isinstance(mkdir, basestring):
                mkdirs.append(mkdir)
            else:
                mkdirs.extend(mkdir)

        for d in mkdirs:
            dirpath = os.path.join(self.workspace(), d)
            self.log_debug("Creating directory %s" % dirpath)
            os.makedirs(dirpath)

    def populate_workspace(self):
        """
        Populates the workspace directory with inputs to the filter, under
        their canonical names.
        """
        self.log_debug("in populate_workspace method")
        already_created_dirs = set()
        wd = self.parent_work_dir()

        self._files_workspace_populated_with = set()

        self.doc.wrapper.trash(wd)

        try:
            os.makedirs(wd)
            already_created_dirs.add(wd)
        except OSError:
            msg = "workspace '%s' for filter '%s' already exists"
            msgargs = (os.path.abspath(wd), self.key,)
            raise dexy.exceptions.InternalDexyProblem(msg % msgargs)

        self.makedirs()

        self.log_debug("input docs %s" % list(self.doc.walk_input_docs()))
        for inpt in self.doc.walk_input_docs():
            if not self.include_input_in_workspace(inpt):
                self.log_debug("not populating workspace with input '%s'" % inpt.key)
                continue

            data = inpt.output_data()

            filepath = data.name

            # Ensure parent dir exists.
            parent_dir = os.path.join(self.workspace(), os.path.dirname(filepath))
            if not parent_dir in already_created_dirs:
                try:
                    os.makedirs(parent_dir)
                    already_created_dirs.add(parent_dir)
                except OSError:
                    pass

            # Save contents of file to workspace
            self.log_debug("populating workspace with %s for %s" % (filepath, inpt.key))
            file_dest = os.path.join(self.workspace(), filepath)

            try:
                copy_or_link(data, file_dest)

            except Exception as e:
                self.log_debug("problem populating working dir with input %s" % data.key)
                self.log_debug(e)

            self._files_workspace_populated_with.add(filepath)

        self.input_data.output_to_file(self.work_input_filepath())
        rel_path_to_work_file = os.path.join(os.path.dirname(self.key), self.work_input_filename())
        self._files_workspace_populated_with.add(rel_path_to_work_file)

        self.custom_populate_workspace()

    def custom_populate_workspace(self):
        """
        Allow filters to run the standard populate_workspace, and also do extra
        things to workspace after populate_workspace runs. Filters can also
        just override populate_workspace.
        """
        pass

    def resolve_conflict(self, doc, conflict_docs):
        """
        Return true if the doc wins the conflict and should be written to the canonical name, false if not.
        """
        conflict_docs = [d for d in conflict_docs if not (('pyg' in d.key) or ('idio' in d.key))]
        conflict_docs.sort()
        if len(conflict_docs) == 0:
            return True
        else:
            return doc in conflict_docs and conflict_docs.index(doc) == 0

    def is_part_of_script_bundle(self):
        if hasattr(self.doc, 'parent'):
            return hasattr(self.doc.parent, 'script_storage')

    def script_storage(self):
        if not self.is_part_of_script_bundle():
            msg = "%s must be part of script bundle to access script storage"
            raise dexy.exceptions.UserFeedback(msg % self.key)
        return self.doc.parent.script_storage

class DexyFilter(Filter):
    """
    Filter which implements some default behaviors.
    """
    aliases = ['dexy']

    def process(self):
        if hasattr(self, "process_text"):
            output = self.process_text(unicode(self.input_data))
            self.output_data.set_data(output)
        else:
            self.output_data.copy_from_file(self.input_data.storage.data_file())

class AliasFilter(DexyFilter):
    """
    Filter to be used when an Alias is specified. Should not change input.
    """
    aliases = ['-']
    _settings = {
            'preserve-prior-data-class' : True
            }

    def calculate_canonical_name(self):
        return self.input_data.name

def filters_by_tag():
    """
    Returns a dict with tags as keys and lists of corresponding filter instances as values.
    """
    tags_filters = {}
    for filter_instance in Filter:
        if filter_instance.setting('nodoc'):
            continue

        for tag in filter_instance.setting('tags'):
            if not tags_filters.has_key(tag):
                tags_filters[tag] = []
            tags_filters[tag].append(filter_instance)

    return tags_filters

def filter_aliases_by_tag():
    tags_filters = filters_by_tag()
    tags = sorted(tags_filters.keys())
    return [(tag,
            [(filter_instance.alias, filter_instance.setting('help'))
                for filter_instance in sorted(tags_filters[tag], key=attrgetter('alias'))])
            for tag in tags]

########NEW FILE########
__FILENAME__ = ansi
from dexy.filter import DexyFilter
from dexy.plugin import TemplatePlugin

# https://pypi.python.org/pypi/ansi2html
# https://github.com/ralphbean/ansi2html

try:
    from ansi2html import Ansi2HTMLConverter
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

class Ansi2HTMLTemplatePlugin(TemplatePlugin):
    """
    Expose ansi2html within templates.
    """
    aliases = ['ansi2html']

    def is_active(self):
        return AVAILABLE

    def convert(self, doc, font_size='normal'):
        conv = Ansi2HTMLConverter(inline=True, font_size=font_size)
        return conv.convert(unicode(doc), full=False)

    def run(self):
        return { 'ansi2html' : ("The convert method from ansi2html module.", self.convert) }

class Ansi2HTMLFilter(DexyFilter):
    """
    Generates HTML from ANSI color codes using ansi2html.
    """
    aliases = ['ansi2html']
    _settings = {
            'output-extensions' : ['.html'],
            'input-extensions' : ['.txt', '.sh-session'],
            'data-type' : 'sectioned',
            'pre' : ("Whether to wrap in <pre> tags.", True),
            'font-size' : ("CSS font size to be used.", "normal")
            }

    def is_active(self):
        return AVAILABLE

    def process(self):
        conv = Ansi2HTMLConverter(inline=True, font_size=self.setting('font-size'))
        if self.setting('pre'):
            s = "<pre>\n%s</pre>\n"
        else:
            s = "%s\n"

        for k, v in self.input_data.iteritems():
            self.output_data[k] = s % conv.convert(unicode(v), full=False)
        self.output_data.save()


########NEW FILE########
__FILENAME__ = api
import dexy.filter
import json
import os
from dexy.utils import file_exists

class ApiFilter(dexy.filter.DexyFilter):
    """
    Base class for filters which post content to a remote API.
    
    This class provides standard formats and locations for storing
    configuration and authentication information.

    Need to read config for the API in general, such as the base URL and an API
    key for authentication.

    Also need to read config for the particular task/document being uploaded.
    This could be stored in the .dexy config entry, but this has two drawbacks.
    First, it makes it difficult to bulk define documents according to a
    pattern. Secondly, it makes it very difficult for dexy to modify this
    configuration to add additional information, such as the returned id for a
    newly created document.

    So, it is preferable to define a local file (defined by a relative path to
    the document in question) which can be overridden per-document in which we
    just store the API-related config and which can be modified by dexy without
    concern about identifying the entry in a .dexy file or accidentally
    overwriting some unrelated information.
    """
    aliases = ['apis']

    _settings = {
            # Files to hold collections of API keys
            'master-api-key-file' : ("Master API key file for user.", "~/.dexyapis"),
            'project-api-key-file' : ("API key file for project.", ".dexyapis"),

            # Parameters to be stored in collection files
            'api-username' : ("The username to sign into the API with.", None),
            'api-password' : ("The password to sign into the API with.", None),
            'api-url' : ("The url of the API endpoint.", None),

            # Files to hold info about a single document
            'document-api-config-file' : ('Filename to store config for a file (can only have 1 per directory, dexy looks for suffix format first.', None),
            'document-api-config-postfix' : ('Suffix to attach to content filename to indicate this is the config for that file.', '-config.json'),

            'api-key-name' : ("The name of this API", None),
            }

    def api_key_locations(self):
        return [self.setting('project-api-key-file'), self.setting('master-api-key-file')]

    def docmd_create_keyfile(self):
        return self.create_keyfile('master-api-key-file')

    def create_keyfile(self, keyfilekey):
        """
        Creates a key file.
        """
        key_filename = os.path.expanduser(self.setting(keyfilekey))
        if file_exists(key_filename):
            raise dexy.exceptions.UserFeedback("File %s already exists!" % key_filename)

        keyfile_content = {}
        for filter_instance in dexy.filter.Filter:
            if isinstance(filter_instance, ApiFilter) and not filter_instance.__class__ == ApiFilter:
                api_key_name = filter_instance.setting('api-key-name')
                # We want to create a keyfile for this filter instance.
                keyfile_content[api_key_name] = {}

                # Get all the entries we want in the keyfile.
                for k, v in filter_instance.setting_values().iteritems():
                    if k.startswith("api_"):
                        keyfile_content[api_key_name][k.replace("api_", "")] = "TODO"

        with open(key_filename, "wb") as f:
            json.dump(keyfile_content, f, sort_keys = True, indent=4)

    def document_config_file(self):
        postfix_config_filename = "%s%s" % (os.path.splitext(self.output_data.name)[0], self.setting('document-api-config-postfix'))
        if file_exists(postfix_config_filename):
            return postfix_config_filename
        else:
            return os.path.join(self.output_data.parent_dir(), self.setting('document-api-config-file'))

    def read_document_config(self):
        document_config = self.document_config_file()
        if file_exists(document_config):
            with open(document_config, "r") as f:
                return json.load(f)
        else:
            msg = "Filter %s needs a file %s, couldn't find it."
            raise dexy.exceptions.UserFeedback(msg % (self.alias, document_config))

    def save_document_config(self, config):
        document_config = self.document_config_file()
        with open(document_config, "w") as f:
            json.dump(config, f, sort_keys=True, indent=4)

    def read_param(self, param_name):
        param_value = None

        for filename in self.api_key_locations():
            if "~" in filename:
                filename = os.path.expanduser(filename)

            if file_exists(filename):
                with open(filename, "r") as f:
                    params = json.load(f)
                    if params.has_key(self.setting('api-key-name')):
                        param_value = params[self.setting('api-key-name')].get(param_name)

            if param_value:
                break

        if param_value and isinstance(param_value, basestring) and param_value.startswith("$"):
            # need to get value of bash variable
            param_value_from_env = os.getenv(param_value.lstrip("$"))
            if not param_value_from_env:
                raise Exception("Bash variable %s not defined in this environment!" % param_value)
            param_value = param_value_from_env

        if param_value:
            return param_value
        else:
            msg = "Could not find %s for %s in: %s" % (param_name, self.setting('api-key-name'), ", ".join(self.api_key_locations()))
            raise Exception(msg)

########NEW FILE########
__FILENAME__ = archive
from dexy.filter import DexyFilter
import tarfile
import zipfile
import os

class UnprocessedDirectoryArchiveFilter(DexyFilter):
    """
    Create a .tgz archive containing the unprocessed files in a directory.
    """
    aliases = ['tgzdir']
    _settings = {
            'output' : True,
            'output-extensions' : ['.tgz'],
            'dir' : ("Directory in which to output the archive.", '')
            }

    def process(self):
        parent_dir = self.output_data.parent_dir()
        subdir = self.setting('dir')
        dir_to_archive = os.path.join(parent_dir, subdir)
        af = self.output_filepath()
        tar = tarfile.open(af, mode="w:gz")
        for fn in os.listdir(dir_to_archive):
            fp = os.path.join(dir_to_archive, fn)
            self.log_debug("Adding file %s to archive %s" % (fp, af))
            tar.add(fp, arcname=os.path.join(subdir, fn))
        tar.close()

class ArchiveFilter(DexyFilter):
    """
    Creates a .tgz archive of all input documents.

    The use-short-names option will store documents under their short
    (canonical) filenames.
    """
    aliases = ['archive', 'tgz']
    _settings = {
            'output' : True,
            'output-extensions' : ['.tgz'],
            'use-short-names' : ("Whether to use short, potentially non-unique names within the archive.", False),
            }

    def open_archive(self):
        self.archive = tarfile.open(self.output_filepath(), mode="w:gz")

    def add_to_archive(self, filepath, archivename):
        self.archive.add(filepath, arcname=archivename)

    def process(self):
        self.open_archive()

        # Place files in the archive within a directory with the same name as the archive.
        dirname = self.output_data.baserootname()

        # Figure out whether to use short names or longer, unambiguous names.
        use_short_names = self.setting("use-short-names")

        for doc in self.doc.walk_input_docs():
            if not doc.output_data().is_cached():
                raise Exception("File not on disk.")

            # Determine what this file's name within the archive should be.
            if use_short_names:
                arcname = doc.output_data().name
            else:
                arcname = doc.output_data().long_name()
            arcname = os.path.join(self.input_data.relative_path_to(arcname))
            arcname = os.path.join(dirname, arcname)

            # Add file to archive
            self.add_to_archive(doc.output_data().storage.data_file(), arcname)

        # Save the archive
        self.archive.close()

class ZipArchiveFilter(ArchiveFilter):
    """
    Creates a .zip archive of all input documents.

    The use-short-names option will store documents under their short
    (canonical) filenames.
    """
    aliases = ['zip']
    _settings = {
            'output-extensions' : ['.zip']
            }

    def open_archive(self):
        self.archive = zipfile.ZipFile(self.output_filepath(), mode="w")

    def add_to_archive(self, filepath, archivename):
        self.archive.write(filepath, arcname=archivename)

########NEW FILE########
__FILENAME__ = asciidoctor
from dexy.exceptions import InternalDexyProblem
from dexy.exceptions import UserFeedback
from dexy.filters.process import SubprocessExtToFormatFilter
from dexy.filters.process import SubprocessFilter
import os

class AsciidoctorFOPUB(SubprocessFilter):
    """
    Uses asciidoctor-fopub to generate PDF.
    """
    aliases = ['fopub','fopdf']

    _settings = {
            'fopub-dir' : ("Absolute path on file system to asciidoctor-fopub dir.", None)
            }

    def process(self):
        # make copy of fopub-dir (use hardlinks?)
        # copy working files including dependencies
        # run fopub
        # copy generated PDF
        pass

class Asciidoctor(SubprocessExtToFormatFilter):
    """
    Runs `asciidoctor`.
    """
    aliases = ['asciidoctor']
    _settings = {
            'tags' : ['asciidoc', 'html'],
            'examples' : ['asciidoctor'],
            'output' : True,
            'version-command' : "asciidoctor --version",
            'executable' : 'asciidoctor',
            'input-extensions' : ['.*'],
            'output-extensions': ['.html', '.xml', '.tex'],
            'stylesheet' : ("Custom asciidoctor stylesheet to use.", None),
            'format-specifier': '-b ',
            'ext-to-format' : {
                '.html' : 'html5',
                '.xml': 'docbook45',
                '.tex' : 'latex'
                },
            'command-string': '%(prog)s %(format)s %(args)s %(ss)s -o %(output_file)s %(script_file)s'
            }

    def command_string_args(self):
        args = super(Asciidoctor, self).command_string_args()

        stylesheet = self.setting('stylesheet')
        if stylesheet:
            stylesdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'asciidoctor'))

            if not os.path.exists(stylesdir):
                msg = "Asciidoctor stylesheet directory not found at '%s'"
                raise InternalDexyProblem(msg % stylesdir)

            args['ss'] = "-a stylesheet=%s -a stylesdir=%s" % (stylesheet, stylesdir)

            if not os.path.exists(os.path.join(stylesdir, stylesheet)):
                msg = "No stylesheet file named '%s' was found in directory '%s'. Files found: %s"
                stylesheets = os.listdir(stylesdir)
                raise UserFeedback(msg % (stylesheet, stylesdir, ", ".join(stylesheets)))

        else:
            args['ss'] = ''
        return args

########NEW FILE########
__FILENAME__ = aws
from datetime import datetime
from dexy.filters.api import ApiFilter
import dexy.exceptions
import getpass
import os
import urllib

try:
    import boto
    from boto.s3.key import Key
    BOTO_AVAILABLE = True
except ImportError:
    BOTO_AVAILABLE = False

class BotoUploadFilter(ApiFilter):
    """
    Uses boto library to upload content to S3, returns the URL.

    You can set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY variables in your
    system environment (the environment that runs the dexy command) or you can
    set defaults in your ~/.dexyapis file (these will override the
    environment):

    "AWS" : {
        "AWS_ACCESS_KEY_ID" : "AKIA...",
        "AWS_SECRET_ACCESS_KEY" : "hY6cw...",
        "AWS_BUCKET_NAME" : "my-unique-bucket-name"
    }

    You can also have a .dexyapis file in the directory in which you run Dexy,
    and this will override the user-wide .dexyapis file. You can use this to
    specify a per-project bucket.

    You can add a date to your bucket by specifying strftime codes in your
    bucket name, this is useful so you don't have to worry about all your
    filenames being unique.

    If you do not set bucket-name, it will default to a name based on your
    username. This may not be unique across all S3 buckets so it may be
    necessary for you to specify a name. You can use an existing S3 bucket,
    a new bucket will be created if your bucket does not already exist.
    """
    aliases = ['s3', 'botoup']
    _settings = {
            'api-key-name' : 'AWS',
            'output-extensions' : ['.txt'],
            }
    API_KEY_KEYS = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_BUCKET_NAME']

    def is_active(self):
        return BOTO_AVAILABLE

    def bucket_name(self):
        """
        Figure out which S3 bucket name to use and create the bucket if it doesn't exist.
        """
        bucket_name = self.read_param('AWS_BUCKET_NAME')
        if not bucket_name:
            try:
                username = getpass.getuser()
                bucket_name = "dexy-%s" % username
                return bucket_name
            except dexy.exceptions.UserFeedback:
                print "Can't automatically determine username. Please specify AWS_BUCKET_NAME for upload to S3."
                raise
        bucket_name = datetime.now().strftime(bucket_name)
        self.log_debug("S3 bucket name is %s" % bucket_name)
        return bucket_name

    def boto_connection(self):
        if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
            # use values defined in env
            return boto.connect_s3()
        else:
            # use values specified in .dexyapis
            aws_access_key_id = self.read_param('AWS_ACCESS_KEY_ID')
            aws_secret_access_key = self.read_param('AWS_SECRET_ACCESS_KEY')
            return boto.connect_s3(aws_access_key_id, aws_secret_access_key)

    def get_bucket(self):
        conn = self.boto_connection()
        return conn.create_bucket(self.bucket_name())

    def process(self):
        b = self.get_bucket()
        k = Key(b)
        k.key = self.input_data.web_safe_document_key()
        self.log_debug("Uploading contents of %s" % self.input_data.storage.data_file())
        k.set_contents_from_filename(self.input_data.storage.data_file())
        k.set_acl('public-read')
        url = "https://s3.amazonaws.com/%s/%s" % (self.bucket_name(), urllib.quote(k.key,))
        self.output_data.set_data(url)

########NEW FILE########
__FILENAME__ = deprecated
from dexy.filter import DexyFilter
import dexy.exceptions

class Deprecated(DexyFilter):
    """
    Base class for deprecated filters.
    """
    aliases = []

    def process(self):
        msg = "%s\n%s" % (self.artifact.key, self.__doc__)
        raise dexy.exceptions.UserFeedback(msg)

class FilenameFilter(Deprecated):
    """
    Deprecated. No longer needed.
    
    Dexy should now automatically detect new files that are created by your
    scripts if the add-new-files setting is true (which it is by default in
    many filters). You should remove '|fn' from your config and anywhere
    documents are referenced, and remove the 'dexy--' prefix from filenames in
    your scripts.
    """
    aliases = ['fn']

########NEW FILE########
__FILENAME__ = easy
# The easyhtml filter is defined in dexy.filters.fluid_html

from dexy.filter import DexyFilter
from pygments.formatters import LatexFormatter

class EasyLatex(DexyFilter):
    """
    Wraps your text in LaTeX article header/footer.
    Easy way to generate a document which can be compiled using LaTeX (includes
    Pygments syntax highlighting).
    """
    aliases = ['easylatex']
    _settings = {
            'input-extensions' : ['.tex'],
            'output-extensions' : ['.tex'],
            'documentclass' : ("The document class to generate.", "article"),
            'style' : ("The pygments style to use.", "default"),
            'title' : ("Title of article.", ""),
            'author' : ("Author of article.", ""),
            'date' : ("Date of article.", ""),
            'font' : ("The font size to use.", "11pt"),
            'papersize' : ("The document class to generate.", "a4paper"),
            "preamble" : ("Additional custom LaTeX content to include in header.", "")
            }

    def pygments_sty(self):
        formatter = LatexFormatter(style=self.setting('style'))
        return formatter.get_style_defs()

    def process_text(self, input_text):
        args = self.setting_values()
        args['input'] = input_text
        args['pygments'] = self.pygments_sty()

        if self.setting('title'):
            args['title'] = r"\title{%(title)s}" % args
            args['maketitle'] = r"\maketitle"
        else:
            args['title'] = ""
            args['maketitle'] = ""

        if self.setting('date'):
            args['date'] = r"\date{%(date)s}" % args

        if self.setting('author'):
            args['author'] = r"\author{%(author)s}" % args

        return self.template % args

    template = r"""\documentclass[%(font)s,%(papersize)s]{%(documentclass)s}
\usepackage{color}
\usepackage{fancyvrb}
%(pygments)s

%(preamble)s

%(title)s
%(author)s
%(date)s

\begin{document}

%(maketitle)s


%(input)s

\end{document}
"""

########NEW FILE########
__FILENAME__ = example
"""
DexyFilters written to be examples of how to write filters.
"""
from dexy.doc import Doc
from dexy.filter import DexyFilter
import os

class Example(DexyFilter):
    """
    Examples of how to write filters.
    """
    aliases = []
    NODOC = True

class KeyValueExample(Example):
    """
    Example of storing key value data.
    """
    aliases = ['keyvalueexample']

    _settings = {
            'data-type' : 'keyvalue',
            'output-extensions' : ['.sqlite3', '.json']
            }

    def process(self):
        assert self.output_data.state == 'ready'
        self.output_data.append("foo", "bar")
        self.output_data.save()

class AccessOtherDocuments(Example):
    """
    Example of accessing other documents.
    """
    aliases = ["others"]

    def process_text(self, input_text):
        info = []
        info.append("Here is a list of previous docs in this tree (not including %s)." % self.key)

        ### @export "access-other-docs-iterate"
        for doc in self.doc.walk_input_docs():
            assert isinstance(doc, Doc)

            ### @export "access-other-docs-lens"
            n_children = len(doc.children)
            n_inputs = len(doc.inputs)

            ### @export "access-other-docs-output-length"
            if doc.output_data().has_data():
                length = len(doc.output_data().data())
            else:
                length = len(doc.output_data().ordered_dict())

            ### @export "access-other-docs-finish"
            info.append("%s (%s children, %s inputs, length %s)" % (doc.key, n_children, n_inputs, length))
        s = "%s        " % os.linesep
        return s.join(info)
        ### @end

class AddNewDocument(Example):
    """
    A filter which adds an extra document to the tree.
    """
    aliases = ['newdoc']

    def process_text(self, input_text):
        self.add_doc("newfile.txt|processtext", "newfile")
        return "we added a new file"

class ConvertDict(Example):
    """
    Returns an ordered dict with a single element.
    """
    aliases = ['dict']

    def process(self, input_text):
        self.output_data['1'] = unicode(self.input_data)
        self.output_data.save()

class ExampleProcessTextMethod(Example):
    """
    Uses process_text method
    """
    aliases = ['processtext']

    def process_text(self, input_text):
        return "Dexy processed the text '%s'" % input_text

class ExampleProcessMethod(Example):
    """
    Calls `set_data` method to store output.
    """
    aliases = ['process']

    def process(self):
        output = "Dexy processed the text '%s'" % self.input_data
        self.output_data.set_data(output)

class ExampleProcessMethodManualWrite(Example):
    """
    Writes output directly to output file.
    """
    aliases = ['processmanual']

    def process(self):
        input_data = self.input_data
        output = "Dexy processed the text '%s'" % input_data
        with open(self.output_filepath(), "wb") as f:
            f.write(output)

class ExampleProcessWithDictMethod(Example):
    """
    Stores sectional data using `process` method.
    """
    aliases = ['processwithdict']
    _settings = {
            'data-type' : 'sectioned'
            }

    def process(self):
        self.output_data['1'] = "Dexy processed the text '%s'" % self.input_data
        self.output_data.save()

class AbcExtension(Example):
    """
    Only outputs extension .abc
    """
    aliases = ['outputabc']
    _settings = {
            'output-extensions' : ['.abc']
            }

    def process_text(self, input_text):
        return "Dexy processed the text '%s'" % input_text

class ExampleFilterArgs(Example):
    """
    Prints out the args it receives.
    """
    aliases = ['filterargs']

    _settings = {
            "abc" : ("The abc setting.", None),
            "foo" : ("The foo setting.", None),
            }

    def process_text(self, input_text):
        # Filter Settings
        result = ["Here are the filter settings:"]
        for k in sorted(self.setting_values()):
            v = self.setting_values()[k]
            result.append("  %s: %s" % (k, v))

        # Doc args
        result.append("Here are the document args:")
        for k in sorted(self.doc.args):
            v = self.doc.args[k]
            result.append("  %s: %s" % (k, v))

        return os.linesep.join(result)

########NEW FILE########
__FILENAME__ = fluid_html
from dexy.filter import DexyFilter

class FluidHtml(DexyFilter):
    """
    Wraps your text in HTML header/footer which includes Baseline CSS resets.
    Easy way to add styles (includes Pygments syntax highlighting).
    """
    aliases = ['easyhtml']
    _settings = {
            'input-extensions' : ['.html'],
            'output-extensions' : ['.html'],
            "css" : ("Custom CSS to include in header.", ""),
            "js" : ("Custom JS to include (please wrap in script tags).", ""),
            }

    def process_text(self, input_text):
        css = self.setting('css')
        if css:
            self.log_debug("custom css is %s" % css)

        js = self.setting('js')
        if js:
            self.log_debug("custom js is %s" % js)

        args = {
                'pygments_css' : PYGMENTS_CSS,
                'css_framework' : CSS_FRAMEWORK,
                'buttons' : CSS_BUTTONS,
                'custom_css' : css,
                'custom_js' : js,
                'content' : input_text
                }
        return """
<html>
    <head>
        <meta http-equiv="Content-type" content="text/html;charset=UTF-8" />
        <style type="text/css">
            %(css_framework)s
            %(buttons)s
            %(pygments_css)s

            /* custom css */
            %(custom_css)s
        </style>
        <!-- custom js -->
        %(custom_js)s
    </head>
    <body>
    <div id="content">
        <div class="g3">
%(content)s
        </div>
    </div>
    </body>
</html>
""" % args




PYGMENTS_CSS = """
.highlight .hll { background-color: #ffffcc }
.highlight .c { color: #888888 } /* Comment */
.highlight .err { color: #a61717; background-color: #e3d2d2 } /* Error */
.highlight .k { color: #008800; font-weight: bold } /* Keyword */
.highlight .cm { color: #888888 } /* Comment.Multiline */
.highlight .cp { color: #cc0000; font-weight: bold } /* Comment.Preproc */
.highlight .c1 { color: #888888 } /* Comment.Single */
.highlight .cs { color: #cc0000; font-weight: bold; background-color: #fff0f0 } /* Comment.Special */
.highlight .gd { color: #000000; background-color: #ffdddd } /* Generic.Deleted */
.highlight .ge { font-style: italic } /* Generic.Emph */
.highlight .gr { color: #aa0000 } /* Generic.Error */
.highlight .gh { color: #303030 } /* Generic.Heading */
.highlight .gi { color: #000000; background-color: #ddffdd } /* Generic.Inserted */
.highlight .go { color: #888888 } /* Generic.Output */
.highlight .gp { color: #555555 } /* Generic.Prompt */
.highlight .gs { font-weight: bold } /* Generic.Strong */
.highlight .gu { color: #606060 } /* Generic.Subheading */
.highlight .gt { color: #aa0000 } /* Generic.Traceback */
.highlight .kc { color: #008800; font-weight: bold } /* Keyword.Constant */
.highlight .kd { color: #008800; font-weight: bold } /* Keyword.Declaration */
.highlight .kn { color: #008800; font-weight: bold } /* Keyword.Namespace */
.highlight .kp { color: #008800 } /* Keyword.Pseudo */
.highlight .kr { color: #008800; font-weight: bold } /* Keyword.Reserved */
.highlight .kt { color: #888888; font-weight: bold } /* Keyword.Type */
.highlight .m { color: #0000DD; font-weight: bold } /* Literal.Number */
.highlight .s { color: #dd2200; background-color: #fff0f0 } /* Literal.String */
.highlight .na { color: #336699 } /* Name.Attribute */
.highlight .nb { color: #003388 } /* Name.Builtin */
.highlight .nc { color: #bb0066; font-weight: bold } /* Name.Class */
.highlight .no { color: #003366; font-weight: bold } /* Name.Constant */
.highlight .nd { color: #555555 } /* Name.Decorator */
.highlight .ne { color: #bb0066; font-weight: bold } /* Name.Exception */
.highlight .nf { color: #0066bb; font-weight: bold } /* Name.Function */
.highlight .nl { color: #336699; font-style: italic } /* Name.Label */
.highlight .nn { color: #bb0066; font-weight: bold } /* Name.Namespace */
.highlight .py { color: #336699; font-weight: bold } /* Name.Property */
.highlight .nt { color: #bb0066; font-weight: bold } /* Name.Tag */
.highlight .nv { color: #336699 } /* Name.Variable */
.highlight .ow { color: #008800 } /* Operator.Word */
.highlight .w { color: #bbbbbb } /* Text.Whitespace */
.highlight .mf { color: #0000DD; font-weight: bold } /* Literal.Number.Float */
.highlight .mh { color: #0000DD; font-weight: bold } /* Literal.Number.Hex */
.highlight .mi { color: #0000DD; font-weight: bold } /* Literal.Number.Integer */
.highlight .mo { color: #0000DD; font-weight: bold } /* Literal.Number.Oct */
.highlight .sb { color: #dd2200; background-color: #fff0f0 } /* Literal.String.Backtick */
.highlight .sc { color: #dd2200; background-color: #fff0f0 } /* Literal.String.Char */
.highlight .sd { color: #dd2200; background-color: #fff0f0 } /* Literal.String.Doc */
.highlight .s2 { color: #dd2200; background-color: #fff0f0 } /* Literal.String.Double */
.highlight .se { color: #0044dd; background-color: #fff0f0 } /* Literal.String.Escape */
.highlight .sh { color: #dd2200; background-color: #fff0f0 } /* Literal.String.Heredoc */
.highlight .si { color: #3333bb; background-color: #fff0f0 } /* Literal.String.Interpol */
.highlight .sx { color: #22bb22; background-color: #f0fff0 } /* Literal.String.Other */
.highlight .sr { color: #008800; background-color: #fff0ff } /* Literal.String.Regex */
.highlight .s1 { color: #dd2200; background-color: #fff0f0 } /* Literal.String.Single */
.highlight .ss { color: #aa6600; background-color: #fff0f0 } /* Literal.String.Symbol */
.highlight .bp { color: #003388 } /* Name.Builtin.Pseudo */
.highlight .vc { color: #336699 } /* Name.Variable.Class */
.highlight .vg { color: #dd7700 } /* Name.Variable.Global */
.highlight .vi { color: #3333bb } /* Name.Variable.Instance */
.highlight .il { color: #0000DD; font-weight: bold } /* Literal.Number.Integer.Long */
"""

CSS_FRAMEWORK = """
/*
    Fluid Baseline Grid v1.0.0
    Designed & Built by Josh Hopkins and 40 Horse, http://40horse.com
    Licensed under Unlicense, http://unlicense.org/

    Base stylesheet with CSS normalization, typographic baseline grid and progressive responsiveness
*/

/* HTML5 DECLARATIONS */
article, aside, details, figcaption, figure, footer, header, hgroup, menu, nav, section, dialog {display: block}
audio[controls],canvas,video {display: inline-block; *display: inline; zoom: 1}

/* BASE */
html {height: 100%; font-size: 100%; overflow-y: scroll; -webkit-text-size-adjust: 100%} /* Force scrollbar in non-IE and Remove iOS text size adjust without disabling user zoom */
body {margin: 0; min-height: 100%; -webkit-font-smoothing:antialiased; font-smoothing:antialiased; text-rendering:optimizeLegibility; background:url('../images/24px_grid_bg.gif') 0 1.1875em} /* Improve default text rendering, handling of kerning pairs and ligatures */

/* DEFAULT FONT SETTINGS */
/* 16px base font size with 150% (24px) friendly, unitless line height and margin for vertical rhythm */
/* Font-size percentage is based on 16px browser default size */
body, button, input, select, textarea {font: 100%/1.5 Georgia,Palatino,"Palatino Linotype",Times,"Times New Roman",serif; *font-size: 1em; color: #333} /* IE7 and older can't resize px based text */
p, blockquote, q, pre, address, hr, code, samp, dl, ol, ul, form, table, fieldset, menu, img {margin: 0 0 1.5em; padding: 0}

/* TYPOGRAPHY */
/* Composed to a scale of 12px, 14px, 16px, 18px, 21px, 24px, 36px, 48px, 60px and 72px */
h1, h2, h3, h4, h5, h6 {font-family:Futura, "Century Gothic", AppleGothic, sans-serif;color:#222;text-shadow:1px 1px 1px rgba(0,0,0,.10)}
h1 {margin: 0; font-size: 3.75em; line-height: 1.2em; margin-bottom: 0.4em} /* 60px / 72px */
h2 {margin: 0; font-size: 3em; line-height: 1em; margin-bottom: 0.5em} /* 48px / 48px */
h3 {margin: 0; font-size: 2.25em; line-height: 1.3333333333333333333333333333333em; margin-bottom: 0.6667em} /* 36px / 48px */ 
h4 {margin: 0; font-size: 1.5em; line-height: 1em; margin-bottom: 1em} /* 24px / 24px */
h5 {margin: 0; font-size: 1.3125em; line-height: 1.1428571428571428571428571428571em; margin-bottom: 1.1428571428571428571428571428571em} /* 21px / 24px */
h6 {margin: 0; font-size: 1.125em; line-height: 1.3333333333333333333333333333333em; margin-bottom: 1.3333333333333333333333333333333em} /* 18px / 24px */
p, ul, blockquote, pre, td, th, label {margin: 0; font-size: 1em; line-height: 1.5em; margin-bottom: 1.5em} /* 16px / 24px */
small, p.small {margin: 0; font-size: 0.875em; line-height: 1.7142857142857142857142857142857em; margin-bottom: 1.7142857142857142857142857142857em} /* 14px / 24px */

/* CODE */
pre {white-space: pre; white-space: pre-wrap; word-wrap: break-word} /* Allow line wrapping of 'pre' */
pre, code, kbd, samp {font-size: 1em; line-height: 1.5em; margin-bottom: 1.5em; font-family: Menlo, Consolas, 'DejaVu Sans Mono', Monaco, monospace}

/* TABLES */
table {border-collapse: collapse; border-spacing: 0; margin-bottom: 1.5em}
th {text-align: left}
tr, th, td {padding-right: 1.5em; border-bottom: 0 solid #333}

/* FORMS */
form {margin: 0}
fieldset {border: 0;padding: 0}
textarea {overflow: auto; vertical-align: top}
legend {*margin-left: -.75em}
button, input, select, textarea {vertical-align: baseline; *vertical-align: middle} /* IE7 and older */
button, input {line-height: normal; *overflow: visible}
button, input[type="button"], input[type="reset"], input[type="submit"] {cursor: pointer;-webkit-appearance: button}
input[type="checkbox"], input[type="radio"] {box-sizing: border-box}
input[type="search"] {-webkit-appearance: textfield; -moz-box-sizing: content-box; -webkit-box-sizing: content-box; box-sizing: content-box}
input[type="search"]::-webkit-search-decoration {-webkit-appearance: none}
button::-moz-focus-inner, input::-moz-focus-inner {border: 0; padding: 0}

/* QUOTES */
blockquote, q {quotes: none}
blockquote:before, blockquote:after, q:before, q:after {content: ''; content: none}
blockquote, q, cite {font-style: italic}
blockquote {padding-left: 1.5em; border-left: 3px solid #ccc}
blockquote > p {padding: 0}

/* LISTS */
ul, ol {list-style-position: inside; padding: 0}
li ul, li ol {margin: 0 1.5em}
dl dd {margin-left: 1.5em}
dt {font-family:Futura, "Century Gothic", AppleGothic, sans-serif}

/* HYPERLINKS */
a {text-decoration: none; color:#c47529}
a:hover {text-decoration: underline}
a:focus {outline: thin dotted}
a:hover, a:active {outline: none} /* Better CSS Outline Suppression */

/* MEDIA */
figure {margin: 0}
img, object, embed, video {max-width: 100%; _width: 100%} /* Fluid images */
img {border: 0; -ms-interpolation-mode: bicubic} /* Improve IE's resizing of images */
svg:not(:root) {overflow: hidden} /* Correct IE9 overflow */

/* ABBREVIATION */
abbr[title], dfn[title] {border-bottom: 1px dotted #333; cursor: help}

/* MARKED/INSERTED/DELETED AND SELECTED TEXT */
ins, mark {text-decoration: none}
mark {background: #c47529}
ins {background: #d49855}
del {text-decoration: line-through}
::-moz-selection {background: #c47529; color: #fff; text-shadow: none} /* selected text */
::selection {background: #c47529; color: #fff; text-shadow: none} /* selected text */

/* OTHERS */
strong, b, dt { font-weight: bold}
dfn {font-style: italic}
var, address {font-style: normal}
sub, sup {font-size: 75%; line-height: 0; position: relative; vertical-align: baseline} /* Position 'sub' and 'sup' without affecting line-height */
sup {top: -0.5em} /* Move superscripted text up */
sub {bottom: -0.25em} /* Move subscripted text down */
span.amp{font-family:Adobe Caslon Pro,Baskerville,"Goudy Old Style","Palatino","Palatino Linotype","Book Antiqua",Georgia,"Times New Roman",Times,serif;font-style:italic;font-size:110%;line-height:0;position:relative;vertical-align:baseline} /* Best available ampersand */

/* MICRO CLEARFIX HACK */
.cf:before, .cf:after {content:"";display:table} /* For modern browsers */
.cf:after {clear:both}
.cf {zoom:1} /* For IE 6/7 (trigger hasLayout) */

/* DEFAULT MOBILE STYLE */
body {width: 92%; margin: 0 auto} /* Center page without wrapper */
/* column grid */
.g1,.g2,.g3{display:block; position: relative; margin-left: 1%; margin-right: 1%}
/* 1 column grid */
.g1,.g2,.g3{width:98.0%}


/* media Queries

FOLDING FLUID GRID
< 767px         - 1-Column Fluid Grid
768px - 1023px  - 2-Column Fluid Grid
> 1024px            - 3-Column Fluid Grid
Change widths as necessary
------------------------------------------- */

/* MOBILE PORTRAIT */
@media only screen and (min-width: 320px) {
    body {
        
    }
}

/* MOBILE LANDSCAPE */
@media only screen and (min-width: 480px) {
    body {
        
    }
}

/* SMALL TABLET */
@media only screen and (min-width: 600px) {
    body {
        
    }
}

/* TABLET/NETBOOK */
@media only screen and (min-width: 768px) { 
    body {
        
    }
    
    /* COLUMN GRID */
    .g1,.g2,.g3 {display:inline; float: left}
    
    /* 2 COLUMN GRID */
    .g1 {width:48.0%}
    .g2 {width:48.0%}
    .g3 {width:98.0%}
}

/* LANDSCAPE TABLET/NETBOOK/LAPTOP */
@media only screen and (min-width: 1024px) { 
    body {

    }
    
    /* 3 COLUMN GRID */
    .g1 {width:31.333%}
    .g2 {width:64.667%;}
    .g3 {width:98.0%}
}

@media only screen and (min-width: 1280px) { 
/* DESKTOP */
        body {

    }
}

/* WIDESCREEN */
/* Increased body size for legibility */
@media only screen and (min-width: 1400px) { 
    body {font-size:116.75%; background:url('../images/28px_grid_bg.gif') 0 1.25em; max-width:1440px} /* 18.5px / 28px */
}


/* PRINT */
@media print {
  * {background: transparent !important; color: black !important; text-shadow: none !important; filter:none !important; -ms-filter: none !important} /* Black prints faster */
  a, a:visited {color: #444 !important; text-decoration: underline}
  a[href]:after {content: " (" attr(href) ")"}
  abbr[title]:after {content: " (" attr(title) ")"}
  .ir a:after, a[href^="javascript:"]:after, a[href^="#"]:after {content: ""}  /* Don't print links for images, javascript or internal links */
  pre, blockquote {border: 1px solid #999; page-break-inside: avoid; }
  thead {display: table-header-group; } /* Repeat header row at top of each printed page */
  tr, img {page-break-inside: avoid; }
  img {max-width: 100% !important; }
  @page {margin: 0.5cm}
  p, h2, h3 {orphans: 3; widows: 3}
  h2, h3{page-break-after: avoid}
}
"""

CSS_BUTTONS = """
/*
 * Copyright (c) 2013 Thibaut Courouble
 * http://www.cssflow.com
 *
 * Licensed under the MIT License:
 * http://www.opensource.org/licenses/mit-license.php
 */

.button {
  font: 10px/18px 'Lucida Grande', Arial, sans-serif;
  display: inline-block;
  vertical-align: top;
  position: relative;
  overflow: hidden;
  min-width: 96px;
  line-height: 30px;
  padding: 0 24px;
  font-size: 14px;
  color: white;
  text-align: center;
  text-decoration: none;
  text-shadow: 0 1px #154c86;
  background-color: #247edd;
  background-clip: padding-box;
  border: 1px solid;
  border-color: #1c65b2 #18589c #18589c;
  border-radius: 4px;
  -webkit-box-shadow: inset 0 1px rgba(255, 255, 255, 0.4), 0 1px 2px rgba(0, 0, 0, 0.2);
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.4), 0 1px 2px rgba(0, 0, 0, 0.2);
  background-image: -webkit-linear-gradient(top, rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0) 50%, rgba(0, 0, 0, 0.12) 51%, rgba(0, 0, 0, 0.04));
  background-image: -moz-linear-gradient(top, rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0) 50%, rgba(0, 0, 0, 0.12) 51%, rgba(0, 0, 0, 0.04));
  background-image: -o-linear-gradient(top, rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0) 50%, rgba(0, 0, 0, 0.12) 51%, rgba(0, 0, 0, 0.04));
  background-image: linear-gradient(to bottom, rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0) 50%, rgba(0, 0, 0, 0.12) 51%, rgba(0, 0, 0, 0.04));
}
.button:before {
  content: '';
  position: absolute;
  top: -25%;
  bottom: -25%;
  left: -20%;
  right: -20%;
  border-radius: 50%;
  background: transparent;
  -webkit-box-shadow: inset 0 0 38px rgba(255, 255, 255, 0.5);
  box-shadow: inset 0 0 38px rgba(255, 255, 255, 0.5);
}
.button:hover {
  background-color: #1a74d3;
  text-decoration: none;
}
.button:active {
  color: rgba(255, 255, 255, 0.9);
  text-shadow: 0 -1px #154c86;
  background: #1f71c8;
  border-color: #113f70 #154c86 #1c65b2;
  -webkit-box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.2), 0 1px rgba(255, 255, 255, 0.4);
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.2), 0 1px rgba(255, 255, 255, 0.4);
  background-image: -webkit-linear-gradient(top, #1a5da5, #3a8be0);
  background-image: -moz-linear-gradient(top, #1a5da5, #3a8be0);
  background-image: -o-linear-gradient(top, #1a5da5, #3a8be0);
  background-image: linear-gradient(to bottom, #1a5da5, #3a8be0);
}
.button:active:before {
  top: -50%;
  bottom: -125%;
  left: -15%;
  right: -15%;
  -webkit-box-shadow: inset 0 0 96px rgba(0, 0, 0, 0.2);
  box-shadow: inset 0 0 96px rgba(0, 0, 0, 0.2);
}

.button-green {
  text-shadow: 0 1px #0d4d09;
  background-color: #1ca913;
  border-color: #147b0e #11640b #11640b;
}
.button-green:hover {
  background-color: #159b0d;
}
.button-green:active {
  text-shadow: 0 -1px #0d4d09;
  background: #189210;
  border-color: #093606 #0d4d09 #147b0e;
  background-image: -webkit-linear-gradient(top, #126d0c, #20c016);
  background-image: -moz-linear-gradient(top, #126d0c, #20c016);
  background-image: -o-linear-gradient(top, #126d0c, #20c016);
  background-image: linear-gradient(to bottom, #126d0c, #20c016);
}

.button-red {
  text-shadow: 0 1px #72100d;
  background-color: #cd1d18;
  border-color: #9f1713 #891310 #891310;
}
.button-red:hover {
  background-color: #c01511;
}
.button-red:active {
  text-shadow: 0 -1px #72100d;
  background: #b61a15;
  border-color: #5b0d0b #72100d #9f1713;
  background-image: -webkit-linear-gradient(top, #921511, #e4201b);
  background-image: -moz-linear-gradient(top, #921511, #e4201b);
  background-image: -o-linear-gradient(top, #921511, #e4201b);
  background-image: linear-gradient(to bottom, #921511, #e4201b);
}
"""

########NEW FILE########
__FILENAME__ = git
from dexy.exceptions import UserFeedback, InternalDexyProblem
from dexy.filter import DexyFilter
import os
import tempfile
import json

try:
    import pygit2
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

def repo_from_path(path):
    """
    Initializes a pygit Repository instance from a local repo at 'path'
    """
    repo = pygit2.init_repository(path, False)
    if repo.is_empty:
        raise UserFeedback("no git repository was found at '%s'" % path)
    return repo, None

def repo_from_url(url, remote_name="origin"):
    """
    Initializes a pygit Repository instance from a remote repo at 'url'
    """
    tempdir = tempfile.mkdtemp() # TODO move to .dexy/persistent/tempdir
    repo = pygit2.init_repository(tempdir, False)
    remote = repo.create_remote(remote_name, url)
    remote.fetch()
    return repo, remote

def generate_commit_info(commit):
    # Currently this is diffing with nothing, so the 'diff' is a full printout
    # of the current contents of the repo.
    diff = commit.tree.diff_to_tree()

    patches = []
    for i, patch in enumerate(diff):
        patches.append({
            'old-file-path' : patch.old_file_path,
            'new-file-path' : patch.new_file_path,
            'hunks' : [ { 
                'old-start' : hunk.old_start,
                'old-lines' : hunk.old_lines,
                'new-start' : hunk.new_start,
                'new-lines' : hunk.new_lines,
                'lines' : hunk.lines
                } for hunk in patch.hunks]
            })

    commit_info = {
            'author-name' : commit.author.name,
            'author-email' : commit.author.email,
            'message' : commit.message.strip(),
            'hex' : commit.hex,
            'patch' : diff.patch.encode('ascii', 'ignore'),
            'patches' : json.dumps(patches).encode('ascii', 'ignore')
            }

    return commit_info

class GitBase(DexyFilter):
    """
    Base class for various git-related filters.
    """
    aliases = []
    _settings = {
            'reference' : ("The reference to use.", None),
            'revision' : ("The revision to use, see 'man gitrevisions'.", None),
            'url-prefixes' : ("""Tuple of strings which mean the specified repo
                should be treated as a URL.""", ("http", "git"))
            }

    def is_active(self):
        return AVAILABLE

    def is_url(self, input_text):
        """
        Should the input text be treated as the URL of a remote git repo?
        """
        return input_text.startswith(self.setting('url-prefixes'))

    def reference(self, repo):
        if self.setting('reference'):
            return repo.lookup_reference(self.setting('reference'))
        else:
            refs = repo.listall_references()
            return repo.lookup_reference(refs[0])

    def revision(self, repo):
        if self.setting('revision'):
            return repo.revparse_single(self.setting('revision'))

    def work(self, repo, remote, ref):
        return "do stuff here in subclass"

    def process_text(self, input_text):
        if self.is_url(input_text):
            repo, remote = repo_from_url(input_text)
        else:
            repo, remote = repo_from_path(input_text)

        ref = self.reference(repo)

        # TODO capture GitError class
        return self.work(repo, remote, ref)

class GitBaseKeyValue(GitBase):
    """
    A filter using key-value storage to manage content from a git repo.
    """
    _settings = {
            'data-type' : 'keyvalue',
            'output-extensions' : ['.sqlite3', '.json']
            }

    def process(self):
        input_text = unicode(self.input_data)
        if self.is_url(input_text):
            repo, remote = repo_from_url(input_text)
        else:
            repo, remote = repo_from_path(input_text)

        ref = self.reference(repo)

        # TODO capture GitError class
        self.work(repo, remote, ref)

        self.output_data.save()

class Git(GitBase):
    """
    What should be default?
    """
    aliases = ['git']

    def work(self, repo, remote, ref):
        return "done"

class GitRepo(GitBase):
    """
    Adds all files in a repo to the project tree as additional documents.

    Files can be filtered to limit which ones are added.
    """
    aliases = ['repo']

    def work(self, repo, remote, ref):
        parent_dir = self.output_data.parent_dir()

        print dir(ref)
        commit = repo[ref.target]
        tree = commit.tree

        def process_tree(tree, add_to_dir):
            for entry in tree:
                obj = repo[entry.oid]
                if obj.__class__.__name__ == 'Blob':
                    doc_key = os.path.join(add_to_dir, entry.name)
                    self.add_doc(doc_key, obj.data)
                elif obj.__class__.__name__ == 'Tree':
                    process_tree(obj, os.path.join(parent_dir, entry.name))
                else:
                    raise InternalDexyProblem(obj.__class__.__name__)

        process_tree(tree, parent_dir)
        # TODO return something more meaningful like a list of the files added.
        # doesn't matter that much since this repo is used for its side effects
        return "done"

class GitCommit(GitBaseKeyValue):
    """
    Returns key-value store information for the most recent commit, or the
    specified revision.
    """
    aliases = ['gitcommit']

    def work(self, repo, remote, ref):
        commit = repo[ref.target]
        commit_info = generate_commit_info(commit)

        for k, v in commit_info.iteritems():
            self.output_data.append(k, v)

class GitLog(GitBase):
    """
    Returns a simple commit log for the specified repository.
    """
    aliases = ['gitlog']
    _settings = {
            'output-extensions' : ['.txt']
            }

    def work(self, repo, remote, ref):
        log = ""
        for commit in repo.walk(ref.target, pygit2.GIT_SORT_TIME):
            log += "%s: %s\n" % (commit.hex, commit.message.strip())
        return log

########NEW FILE########
__FILENAME__ = id
from dexy.exceptions import UserFeedback, InternalDexyProblem
from dexy.filters.pyg import PygmentsFilter
from pygments import highlight
import ply.lex as lex
import ply.yacc as yacc

class LexError(InternalDexyProblem):
    pass

class ParseError(UserFeedback):
    pass

tokens = (
    'AMP',
    'AT',
    'CODE',
    'COLONS',
    'DBLQUOTE',
    'END',
    'IDIOCLOSE',
    'IDIOOPEN',
    'EXP',
    'IDIO',
    'NEWLINE',
    'SGLQUOTE',
    'WHITESPACE',
    'WORD',
)

states = (
    ('idiostart', 'exclusive',),
    ('idio', 'exclusive',),
)

class Id(PygmentsFilter):
    """
    Splits files into sections based on comments like ### "foo"

    Replacement for idiopidae. Should be fully backwards-compatible.

    For more information about the settings starting with ply-, see the PLY
    YACC parser documentation http://www.dabeaz.com/ply/ply.html#ply_nn36
    """
    aliases = ['idio', 'id', 'idiopidae', 'htmlsections']
    _settings = {
            'examples' : ['idio', 'htmlsections'],
            'highlight' : ("Whether to apply syntax highlighting to sectional output.", None),
            'skip-extensions' : ("Because |idio gets applied to *.*, need to make it easy to skip non-textual files.", (".odt")),
            'remove-leading' : ("If a document starts with empty section named '1', remove it.", False),
            'ply-debug' : ("The 'debug' setting to pass to PLY. A setting of 1 will produce very verbose output.", 0),
            'ply-optimize' : ("Whether to use optimized mode for the lexer.", 1),
            'ply-write-tables' : ("Whether to generate parser table files (which will be stored in ply-outputdir and named ply-tabmodule).", 1),
            'ply-outputdir' : ("Location relative to where you run dexy in which ply will store table files. Defaults to dexy's log directory.", None),
            'ply-parsetab' : ("Name of parser tabfile (.py extension will be added) to be stored in ply-outputdir if ply-write-tables set to 1.", 'id_parsetab'),
            'ply-lextab' : ("Name of lexer tabfile (.py extension will be added) to be stored in ply-outputdir if ply-optimize is set to 1.", 'id_lextab'),
            'output-extensions' : PygmentsFilter.MARKUP_OUTPUT_EXTENSIONS + PygmentsFilter.IMAGE_OUTPUT_EXTENSIONS
            }

    def process(self):
        try:
            input_text = unicode(self.input_data)
        except UnicodeDecodeError:
            self.output_data['1'] = "non textual"
            self.output_data.save()
            return

        lexer.outputdir = self.setting('ply-outputdir')
        lexer.errorlog = self.doc.wrapper.log
        lexer.remove_leading = self.setting('remove-leading')
        parser.outputdir = self.setting('ply-outputdir')
        parser.errorlog = self.doc.wrapper.log
        parser.write_tables = self.setting('ply-write-tables')

        _lexer = lexer.clone()
        _lexer.sections = []
        _lexer.level = 0
        start_new_section(_lexer, 0, 0, _lexer.level)

        parser.parse(input_text + "\n", lexer=_lexer)
        strip_trailing_newline(_lexer)
        parser_output = _lexer.sections

        pyg_lexer = self.create_lexer_instance()
        pyg_formatter = self.create_formatter_instance()

        # TODO fix file extension if highlight is set to false
        do_highlight = self.setting('highlight')
        if do_highlight is None:
            if self.alias in ('htmlsections',):
                do_highlight = False
                if self.output_data.setting('canonical-output') is None:
                    self.output_data.update_settings({'canonical-output' : True})
            else:
                do_highlight = True

        for section in parser_output:
            if do_highlight:
                section['contents'] = highlight(section['contents'], pyg_lexer, pyg_formatter)
            self.output_data._data.append(section)
        self.output_data.save()

def t_error(t):
    raise LexError("Problem lexing at position %s." % t.lexpos)

def t_idio_error(t):
    print "comment '%s'" % t.lexer.lexdata[t.lexer.comment_start_pos:]
    print "all '%s'" % t.lexer.lexdata
    print "char '%s'" % t.lexer.lexdata[t.lexpos-1:t.lexer.lexpos]
    raise LexError("Problem lexing in 'idio' state at position %s." % t.lexpos)

def t_idiostart_error(t):
    raise LexError("Problem lexing in 'idiostart' state at position %s." % t.lexpos)
        
def append_text(lexer, code):
    """
    Append to the currently active section.
    """
    set_current_section_contents(lexer, current_section_contents(lexer) + code)

def current_section_exists(lexer):
    return len(lexer.sections) > 0

def current_section_empty(lexer):
    return len(current_section_contents(lexer)) == 0

def current_section_contents(lexer):
    return lexer.sections[-1]['contents']

def set_current_section_contents(lexer, text):
    lexer.sections[-1]['contents'] = text

def strip_trailing_newline(lexer):
    set_current_section_contents(lexer, current_section_contents(lexer).rsplit("\n",1)[0])

def start_new_section(lexer, position, lineno, new_level, name=None):
    if name:
        if lexer.remove_leading:
            if len(lexer.sections) == 1 and current_section_empty(lexer):
                lexer.sections = []
    else:
        # Generate anonymous section name.
        name = unicode(len(lexer.sections)+1)

    try:
        change_level(lexer, new_level)
    except Exception:
        print name
        raise

    lexer.sections.append({
            'name' : name.rstrip(),
            'position' : position,
            'lineno' : lineno,
            'contents' : u'',
            'level' : lexer.level
            })

def change_level(lexer, new_level):
    if new_level == lexer.level:
        pass
    elif new_level < lexer.level:
        pass
    elif new_level == lexer.level + 1:
        pass
    elif new_level > (lexer.level + 1):
        msg = "attempting to indent more than 1 level to %s from previous level %s"
        msgargs = (new_level, lexer.level)
        raise Exception(msg % msgargs)
    elif new_level < 0:
        raise Exception("attepmting to indent to level below 0, does not exist")
    else:
        msg = "logic error! new level %s current level %s"
        msgargs = (new_level, lexer.level)
        raise Exception(msg % msgargs)

    lexer.level = new_level

def next_char(t):
    return t.lexer.lexdata[t.lexer.lexpos:t.lexer.lexpos+1]

def lookahead_n(t, n):
    # TODO what if n is too big?
    return t.lexer.lexdata[t.lexer.lexpos:t.lexer.lexpos+n]

def lookahead_for(t, word):
    return lookahead_n(t, len(word)) == word

def lookahead_for_any(t, words):
    any_found = False
    for word in words:
        if lookahead_for(t, word):
            any_found = True
            break
    return any_found

# Lexer tokens for idio state
def t_idio_AT(t):
    r'@'
    return t

def t_idio_AMP(t):
    r'&'
    return t

def t_idio_COLONS(t):
    r':+'
    return t

def t_idio_DBLQUOTE(t):
    r'"'
    return t

def t_idio_SGLQUOTE(t):
    r'\''
    return t

def t_idio_EXP(t):
    r'export|section'
    return t

def t_idio_END(t):
    r'end'
    return t

def t_idio_WHITESPACE(t):
    r'(\ |\t)+'
    return t

def t_idio_NEWLINE(t):
    r'\r\n|\n|\r'
    exit_idio_state(t)
    return t

def t_idio_IDIOCLOSE(t):
    r'(-->)|(\*/)'
    if not t.lexer.idio_expect_closing_block:
        raise UserFeedback("Unexpected code %s in an idio block" % t.value)
    return t

def t_idio_WORD(t):
    r'[0-9a-zA-Z-_]+'
    return t

def t_idio_OTHER(t):
    r'.'
    t.type = 'CODE'
    exit_idio_state(t)
    return t

def exit_idio_state(t):
    if not t.lexer.idio_expect_closing_block:
        t.lexer.pop_state()
    t.lexer.pop_state()

# Lexer tokens and helpers for idiostart state
def idiostart_incr_comment(t):
    if t.lexer.comment_char == t.value:
        t.lexer.comment_char_count += 1
    else:
        return idiostart_abort(t)

def idiostart_abort(t):
    t.value = t.lexer.lexdata[t.lexer.comment_start_pos:t.lexer.lexpos]
    t.type = "CODE"
    t.lexer.pop_state()
    return t

def t_idiostart_COMMENT(t):
    r'\#|%|;|/'
    return idiostart_incr_comment(t)

def t_idiostart_SPACE(t):
    r'\ +'
    if t.lexer.comment_char_count != 3:
        return idiostart_abort(t)
    else:   
        t.lexer.push_state('idio')
        t.value = t.lexer.lexdata[t.lexer.comment_start_pos:t.lexer.lexpos]
        t.type = 'IDIO'
        return t

def t_idiostart_ABORT(t):
    r'[^#;/% ]'
    return idiostart_abort(t)

# Lexer tokens and helpers for initial state
def start_idiostart(t):
    if next_char(t) == '\n':
        t.type = 'CODE'
        return t
    else:
        t.lexer.comment_char = t.value
        t.lexer.comment_char_count = 1
        t.lexer.comment_start_pos = t.lexer.lexpos - 1
        t.lexer.idio_expect_closing_block = False
        t.lexer.push_state('idiostart')

def t_IDIOOPEN(t):
    r'(<!--|/\*\*\*)\ +@?'
    if lookahead_for_any(t, ['export', 'section', 'end']):
        t.lexer.push_state('idio')
        t.lexer.idio_expect_closing_block = True
        return t
    else:
        t.type = 'CODE'
        return t

def t_COMMENT(t):
    r'\#|%|;|/'
    return start_idiostart(t)

def t_NEWLINE(t):
    r'\r\n|\n|\r'
    return t

def t_WHITESPACE(t):
    r'[\ \t]+'
    return t

def t_CODE(t):
    r'[^\#/\n\r]+'
    return t

def p_main(p):
    '''entries : entries entry
               | entry'''
    pass

def p_entry(p):
    '''entry : NEWLINE
             | falsestart
             | codes NEWLINE
             | codes inlineidio NEWLINE
             | idioline NEWLINE'''
    p.lexer.lineno += 1
    if len(p) == 2:
        append_text(p.lexer, p[1])
    elif len(p) == 3:
        if p[1]:
            append_text(p.lexer, p[1] + '\n')
        pass
    elif len(p) == 4:
        code_content = p[1]
        append_text(p.lexer, code_content + "\n")
        # TODO Process inlineidio directives @elide &tag
        # inlineidio_content = p[2]
    else:
        raise Exception("unexpected length " + len(p))

def p_sectionfalsestart(p):
    '''falsestart : IDIO words NEWLINE
                  | IDIO words IDIO NEWLINE
                  | IDIO quote words quote NEWLINE
                  | codes IDIO anythings NEWLINE
                  | WHITESPACE IDIO anythings IDIO NEWLINE
                  | WHITESPACE IDIO anythings NEWLINE'''
    p[0] = "".join(p[1:])

def p_anythings(p):
    '''anythings : anythings anything
                 | anything'''
    p[0] = ''.join(p[1:len(p)])

def p_anything(p):
    '''anything : WORD
                | WHITESPACE
                | CODE'''
    p[0] = p[1]

def p_codes(p):
    '''codes : codes codon
             | codon'''
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 3:
        if p[1]:
            p[0] = p[1] + p[2]
        else:
            p[0] = p[2]

def p_codon(p):
    '''codon : CODE 
             | WHITESPACE'''
    p[0] = p[1]

def p_inlineidio(p):
    '''inlineidio : IDIO AMP WORD'''
    p[0] = p[1] + p[2] + p[3]

def p_idioline(p):
    '''idioline : idio
                | idio WHITESPACE
                | WHITESPACE idio
                | WHITESPACE idio WHITESPACE'''
    pass

def p_linecontent(p):
    '''idio : export
            | exportq
            | exportql
            | sectionstart
            | closedcomment
            | closedcommentlevels
            | closedcommentq
            | closedcommentql
            | end '''
    pass

## Methods Defining Section Boundaries
def p_sectionstart(p):
    '''sectionstart : IDIO quote WORD quote
                    | IDIO quote COLONS WORD quote'''
    if len(p) == 5:
        # no colons, so level is 0
        start_new_section(p.lexer, p.lexpos(1), p.lineno(1), 0, p[3])
    elif len(p) == 6:
        start_new_section(p.lexer, p.lexpos(1), p.lineno(1), len(p[3]), p[4])
    else:
        raise Exception("unexpected length %s" % len(p))

def p_closed_comment(p):
    '''closedcomment : IDIOOPEN EXP WHITESPACE WORD IDIOCLOSE
                     | IDIOOPEN EXP WHITESPACE WORD WHITESPACE IDIOCLOSE'''
    assert len(p) in [6,7]
    start_new_section(p.lexer, p.lexpos(1), p.lineno(1), 0, p[4])

def p_closed_comment_levels(p):
    '''closedcommentlevels : IDIOOPEN EXP WHITESPACE COLONS WORD IDIOCLOSE
                           | IDIOOPEN EXP WHITESPACE COLONS WORD WHITESPACE IDIOCLOSE'''
    assert len(p) in [7,8]
    start_new_section(p.lexer, p.lexpos(1), p.lineno(1), len(p[4]), p[5])

def p_closed_comment_quoted(p):
    '''closedcommentq : IDIOOPEN EXP WHITESPACE quote words quote IDIOCLOSE
                      | IDIOOPEN EXP WHITESPACE quote words quote WHITESPACE IDIOCLOSE'''
    assert len(p) in [8,9]
    start_new_section(p.lexer, p.lexpos(1), p.lineno(1), 0, p[5])

def p_closed_comment_quoted_with_language(p):
    '''closedcommentql : IDIOOPEN EXP WHITESPACE quote words quote WHITESPACE WORD IDIOCLOSE
                       | IDIOOPEN EXP WHITESPACE quote words quote WHITESPACE WORD WHITESPACE IDIOCLOSE'''
    assert len(p) in [10,11]
    start_new_section(p.lexer, p.lexpos(1), p.lineno(1), 0, p[5])

## Old Idiopidae @export syntax
def p_export(p):
    '''export : IDIO AT EXP WHITESPACE words
              | IDIO AT EXP WHITESPACE words WHITESPACE'''
    assert len(p) in [6,7]
    start_new_section(p.lexer, p.lexpos(1), p.lineno(1), 0, p[5])

def p_export_quoted(p):
    '''exportq : IDIO AT EXP WHITESPACE quote words quote
               | IDIO AT EXP WHITESPACE quote words quote WHITESPACE'''
    assert len(p) in [8,9]
    start_new_section(p.lexer, p.lexpos(1), p.lineno(1), 0, p[6])

def p_export_quoted_with_language(p):
    '''exportql : IDIO AT EXP WHITESPACE quote words quote WHITESPACE words
                | IDIO AT EXP WHITESPACE quote words quote WHITESPACE words WHITESPACE'''
    assert len(p) in [10,11]
    start_new_section(p.lexer, p.lexpos(1), p.lineno(1), 0, p[6])

def p_end(p):
    '''end : IDIO AT END
           | IDIOOPEN END IDIOCLOSE
           | IDIOOPEN END WHITESPACE IDIOCLOSE
           | IDIOOPEN EXP WHITESPACE quote END quote WHITESPACE IDIOCLOSE'''
    start_new_section(p.lexer, p.lexpos(1), p.lineno(1), p.lexer.level)

def p_quote(p):
    '''quote : DBLQUOTE
             | SGLQUOTE'''
    p[0] = p[1]

def p_words(p):
    '''words : words WHITESPACE WORD
             | WORD'''
    if len(p) == 4:
        p[0] = p[1] + p[2] + p[3]
    elif len(p) == 2:
        p[0] = p[1]
    else:
        raise Exception("unexpected length %s" % len(p))

def p_error(p):
    if not p:
        raise ParseError("Reached EOF when parsing file using idioipdae.")

    lines = p.lexer.lexdata.splitlines()
    this_line = lines[p.lineno-1]

    # Add whole line.
    append_text(p.lexer, this_line+"\n")

    # Forward input to end of line
    while 1:
        tok = yacc.token()
        if not tok or tok.type == 'NEWLINE': break

    yacc.restart()

def tokenize(text, lexer):
    """
    Return array of lexed tokens (for debugging).
    """
    lexer.input(text)
    tokens = []
    while True:
        tok = lexer.token()
        if not tok: break      # No more input
        tokens.append(tok)
    return tokens

def token_info(text, lexer):
    """
    Returns debugging information about lexed tokens as a string.
    """
    def tok_info(tok):
        return "%03d %-15s %s" % (tok.lexpos, tok.type, tok.value.replace("\n",""))
    return "\n".join(tok_info(tok) for tok in tokenize(text, lexer))

# This is outside of the wrapper system so we aren't aware of user-specified
# artifacts directory. Just use .dexy if it's there and don't write files if not.

import os
if os.path.exists(".dexy"):
    outputdir=".dexy"
    lexer = lex.lex(optimize=1, lextab="id_lextab", outputdir=outputdir)
    parser = yacc.yacc(tabmodule="id_parsetab",debug=0, outputdir=outputdir)
else:
    lexer = lex.lex(optimize=0)
    parser = yacc.yacc(write_tables=0, debug=0)

########NEW FILE########
__FILENAME__ = ipynb
from dexy.filter import DexyFilter
import base64
import dexy.exceptions
import json
import urllib

try:
    import IPython.nbformat.current
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

class IPythonBase(DexyFilter):
    """
    Base class for IPython filters which work by loading notebooks into memory.
    """
    aliases = []

    def is_active(self):
        return AVAILABLE

    def load_notebook(self):
        nb = None
        with open(self.input_data.storage.data_file(), "r") as f:
            nb_fmt = self.input_data.ext.replace(".","")
            nb = IPython.nbformat.current.read(f, nb_fmt)
        return nb

    def enumerate_cells(self, nb=None):
        if not nb:
            nb = self.load_notebook()
        worksheet = nb['worksheets'][0]
        for j, cell in enumerate(worksheet['cells']):
            yield(j, cell)

class IPythonExport(IPythonBase):
    """
    Generates a static file based on an IPython notebook.
    """
    aliases = ['ipynbx']

    _settings = {
            'added-in-version' : "0.9.9.6",
            'input-extensions' : ['.ipynb'],
            'output' : True,
            'output-extensions' : ['.md', '.html'], # TODO add other formats
            }

    def process_html(self):
        nb = self.load_notebook()

    def process_md(self):
        output = ""
        for j, cell in self.enumerate_cells():
            cell_type = cell['cell_type']
            if cell_type == 'heading':
                output += "## %s\n" % cell['source']
            elif cell_type == 'markdown':
                output += "\n%s\n" % cell['source']
            elif cell_type == 'code':
                for k, cell_output in enumerate(cell['outputs']):
                    cell_output_type = cell_output['output_type']
                    del cell_output['output_type']
                    if cell_output_type == 'stream':
                        output += cell_output['text']
                    elif cell_output_type in ('pyout', 'pyerr',):
                        pass
                    elif cell_output_type == 'display_data':
                        for fmt, contents in cell_output.iteritems():
                            if fmt == "png":
                                cell_output_image_file = "cell-%s-output-%s.%s" % (j, k, fmt)
                                d = self.add_doc(cell_output_image_file, base64.decodestring(contents))
                                output += "\n![Description](%s)\n" % urllib.quote(cell_output_image_file)
                            elif fmt in ('metadata','text',):
                                pass
                            else:
                                raise dexy.exceptions.InternalDexyProblem(fmt)
                    else:
                        raise dexy.exceptions.InternalDexyProblem("unexpected cell output type %s" % cell_output_type)
            else:
                raise dexy.exceptions.InternalDexyProblem("Unexpected cell type %s" % cell_type)

        return output

    def process(self):
        if self.ext == '.html':
            output = self.process_html()
        elif self.ext == '.md':
            output = self.process_md()
        else:
            raise dexy.exceptions.InternalDexyProblem("Shouldn't get ext %s" % self.ext)

        self.output_data.set_data(output)

class IPythonNotebook(IPythonBase):
    """
    Get data out of an IPython notebook.
    """
    aliases = ['ipynb']

    _settings = {
            'added-in-version' : "0.9.9.6",
            'examples' : ['ipynb'],
            'input-extensions' : ['.ipynb', '.json', '.py'],
            'output-extensions' : ['.json'],
            }

    def process(self):
        output = {}
        nb = self.load_notebook()

        nb_fmt_string = "%s.%s" % (nb['nbformat'], nb['nbformat_minor']) # 3.0 currently
        output['nbformat'] = nb_fmt_string

        cells = []
        documents = []

        for j, cell in self.enumerate_cells(nb):
            # could also do: cell_key = "%s--%0.3d" % (self.input_data.rootname(), j)
            cell_key = "%s--%s" % (self.input_data.rootname(), j)
            cell_type = cell['cell_type']

            if cell_type == 'heading':
                # TODO implement
                # keys are [u'source', u'cell_type', u'level', u'metadata']
                pass

            elif cell_type == 'markdown':
                d = self.add_doc("%s.md" % cell_key, cell['source'], {'output':False})
                documents.append(d.key)
                d = self.add_doc("%s.md|pyg|h" % cell_key, cell['source'])
                d = self.add_doc("%s.md|pyg|l" % cell_key, cell['source'])

            elif cell_type == 'code':
                # keys are [u'cell_type', u'language', u'outputs', u'collapsed', u'prompt_number', u'input', u'metadata']

                # map languages to file extensions to create new doc(s) for each cell
                file_extensions = {
                    'python' : '.py'
                    }
                ext = file_extensions[cell['language']]

                d = self.add_doc("%s-input%s" % (cell_key, ext), cell['input'], {'output': False })
                documents.append(d.key)

                # Add pygments syntax highlighting in HTML and LaTeX formats.
                self.add_doc("%s-input%s|pyg|h" % (cell_key, ext), cell['input'], { 'output' : False })
                self.add_doc("%s-input%s|pyg|l" % (cell_key, ext), cell['input'], { 'output' : False })

                # process each output
                for k, cell_output in enumerate(cell['outputs']):
                    cell_output_type = cell_output['output_type']
                    del cell_output['output_type']

                    if cell_output_type == 'stream':
                        assert sorted(cell_output.keys()) == [u"stream", u"text"], "stream output keys"
                        d = self.add_doc(
                                "%s-output-%s.txt" % (cell_key, k),
                                cell_output['text'],
                                {'output' : False}
                                )
                        documents.append(d.key)

                    elif cell_output_type == 'pyout':
                        pass

                    elif cell_output_type == 'pyerr':
                        pass

                    elif cell_output_type == 'display_data':
                        for fmt, contents in cell_output.iteritems():
                            if fmt == "png":
                                d = self.add_doc(
                                        "%s-output-%s.%s" % (cell_key, k, fmt),
                                        base64.decodestring(contents)
                                        )
                                documents.append(d.key)
                                cell.outputs[k]['png'] = d.key
                            elif fmt == 'text':
                                pass
                            elif fmt == 'metadata':
                                pass
                            elif fmt == 'latex':
                                pass

                            else:
                                raise Exception("unexpected format in display_data %s" % fmt)

                    else:
                        raise Exception("unexpected output type %s" % cell_output_type)
            else:
                raise Exception("unexpected cell type '%s'" % cell_type)

            cells.append((cell_type, cell,))

        output["nbformat"] = nb_fmt_string
        output["cells"] = cells
        output["documents"] = documents
        for k, v in nb['metadata'].iteritems():
            output[k] = v

        self.output_data.set_data(json.dumps(output))

########NEW FILE########
__FILENAME__ = ipynbcasper
from dexy.exceptions import UserFeedback
from dexy.filters.process import SubprocessFilter
import os
import re
import subprocess
import json

try:
    import IPython.nbformat.current
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

class IPythonCasper(SubprocessFilter):
    """
    Launch IPython notebook and run a casperjs script against the server.
    """
    aliases = ['ipynbcasper']

    _settings = {
            'add-new-files' : True,
            'added-in-version' : "0.9.9.6",
            'examples' : ['ipynbcasper'],
            'args' : '--web-security=false --ignore-ssl-errors=true',
            'cell-timeout' : ("Timeout (in microseconds) for running individual notebook cells.", 5000),
            'command-string' : "%(prog)s %(test)s %(args)s %(script)s",
            'test' : ("Whether to run casperjs as 'test' mode.", False),
            'executable' : 'casperjs',
            'height' : ('Height of page to capture.', 5000),
            'image-ext' : ("File extension of images to capture.", ".png"),
            'input-extensions' : ['.ipynb'],
            'ipython-args' : ("Additional args to pass to ipython notebook command (list of string args).", None),
            'ipython-dir' : ("Directory in which to launch ipython, defaults to temp working dir.", None),
            'output-extensions' : ['.json', '.txt'],
            'script' : ("Canonical name of input document to use as casper script.", "full.js"),
            'timeout' : ("Timeout for the casperjs subprocess.", 10000),
            'version-command' : 'casperjs --version',
            'width' : ('Width of page to capture.', 800),
            }

    def is_active(self):
        return AVAILABLE

    def command_string_args(self):
        args = self.default_command_string_args()
        if self.setting('test'):
            args['test'] = 'test'
        else:
            args['test'] = ''
        return args

    def configure_casper_script(self, wd, port, cellmetas):
        scriptfile = os.path.join(wd, self.setting('script'))
        cellmetafile = os.path.join(wd, "%s-cellmetas.js" % self.input_data.baserootname())

        default_scripts_dir = os.path.join(os.path.dirname(__file__), "ipynbcasper")

        if not os.path.exists(scriptfile):
            # look for a matching default script
            script_setting = self.setting('script')

            filepath = os.path.join(default_scripts_dir, script_setting)
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    js = f.read()
            else:
                default_scripts = os.listdir(default_scripts_dir)
                args = (self.setting('script'), ", ".join(default_scripts),)
                raise UserFeedback("No script file named '%s' found.\nAvailable built-in scripts: %s" % args)

        else:
            with open(scriptfile, "r") as f:
                js = f.read()

        args = {
                'width' : self.setting('width'),
                'height' : self.setting('height'),
                'port' : port,
                'name' : self.input_data.baserootname(),
                'ext' : self.setting('image-ext'),
                'cell_timeout' : self.setting('cell-timeout')
                }

        with open(scriptfile, "w") as f:
            f.write(js % args)

        with open(cellmetafile, "w") as f:
            json.dump(cellmetas, f)

    def launch_ipython(self, env):
        command = ['ipython', 'notebook', '--no-browser']
        command.extend(self.parse_additional_ipython_args())

        if self.setting('ipython-dir'):
            wd = self.setting('ipython-dir')
        else:
            wd = self.parent_work_dir()

        self.log_debug("About to run ipython command: '%s' in '%s'" % (' '.join(command), wd))
        proc = subprocess.Popen(command, shell=False,
                                    cwd=wd,
                                    stdin=None,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    env=env)

        self.log_debug("Reading from stderr of ipython command...")
        count = 0
        while True:
            count += 1
            if count > 100:
                raise Exception("IPython notebook failed to start.")

            line = proc.stderr.readline()
            self.log_debug(line)

            if "The IPython Notebook is running" in line:
                m = re.search("([0-9\.]+):([0-9]{4})", line)
                port = m.groups()[1]

            if "Use Control-C to stop this server" in line:
                break

            if "ImportError" in line:
                raise Exception(line)

        # TODO if process is not running => throw exception
        return proc, port

    def parse_additional_ipython_args(self):
        raw_ipython_args = self.setting('ipython-args')
        if raw_ipython_args:
            if isinstance(raw_ipython_args, basestring):
                user_ipython_args = raw_ipython_args.split()
            elif isinstance(raw_ipython_args, list):
                assert isinstance(raw_ipython_args[0], basestring)
                user_ipython_args = raw_ipython_args
            else:
                raise UserFeedback("ipython-args must be a string or list of strings")
            return user_ipython_args
        else:
            return []

    def process(self):
        env = self.setup_env()

        wd = self.parent_work_dir()

        with open(self.input_data.storage.data_file(), "r") as f:
            nb = json.load(f)

        stdout = None
        output = {}
        output['cellmetas'] = []
        output['cellimages'] = []
        output['images-by-name'] = {}

        for cell in nb['worksheets'][0]['cells']:
            output['cellmetas'].append(cell['metadata'])

        ws = self.workspace()
        if os.path.exists(ws):
            self.log_debug("already have workspace '%s'" % os.path.abspath(ws))
        else:
            self.populate_workspace()

        # launch ipython notebook
        ipython_proc, port = self.launch_ipython(env)

        try:
            self.configure_casper_script(wd, port, output['cellmetas'])
    
            ## run casper script
            command = self.command_string()
            proc, stdout = self.run_command(command, self.setup_env())
            self.handle_subprocess_proc_return(command, proc.returncode, stdout)

        finally:
            # shut down ipython notebook
            os.kill(ipython_proc.pid, 9)


        if self.setting('add-new-files'):
            self.add_new_files()

        docname = self.doc.output_data().baserootname()
        i = 0
        for doc in sorted(self.doc.children):
            m = re.match("%s--([0-9]+)" % docname, doc.key)
            if m:
                assert i == int(m.groups()[0])
                output['cellimages'].append(doc.key)
                cellmeta_for_image = output['cellmetas'][i]
                if cellmeta_for_image.has_key('name'):
                    cellname = cellmeta_for_image['name']
                    output['images-by-name'][cellname] = doc.key
                i += 1

        if self.ext == ".txt":
            self.output_data.set_data(stdout)
        else:
            self.output_data.set_data(json.dumps(output))


########NEW FILE########
__FILENAME__ = java
from dexy.filters.pexp import PexpectReplFilter
from dexy.filters.process import SubprocessCompileFilter
from dexy.filters.process import SubprocessStdoutFilter
import os
import platform

class Scala(SubprocessCompileFilter):
    """
    Compiles and runs .scala files.
    """
    aliases = ['scala']
    _settings = {
            'executable' : 'scalac',
            'tags' : ['code', 'scala', 'compiled', 'jvm'],
            'compiler-command-string' : "%(prog)s %(compiler_args)s %(script_file)s",
            'compiled-extension' : '',
            'input-extensions' : ['.scala', '.txt'],
            'output-extensions' : ['.txt']
            }

    def run_command_string(self):
        args = self.default_command_string_args()
        args['compiled_filename'] = self.compiled_filename()
        return "scala %(compiled_filename)s %(args)s" % args

class CompileScala(Scala):
    """
    Compiles .scala code to .class files.
    """
    aliases = ['scalac']
    _settings = {
            'tags' : ['code', 'scala', 'compiled', 'jvm'],
            'output-extensions' : ['.class']
            }

    def process(self):
        # Compile the code
        command = self.compile_command_string()
        proc, stdout = self.run_command(command, self.setup_env())
        self.handle_subprocess_proc_return(command, proc.returncode, stdout)
        self.copy_canonical_file()

class JythonFilter(SubprocessStdoutFilter):
    """
    jython
    """
    aliases = ['jython']
    _settings = {
            'executable' : 'jython',
            'tags' : ['code', 'jython', 'jvm'],
            'input-extensions' : [".py", ".txt"],
            'output-extensions' : [".txt"],
            'version-command' : "jython --version"
            }

    def is_active(klass):
        if platform.system() in ('Linux', 'Windows'):
            return True
        elif platform.system() in ('Darwin'):
            if hasattr(klass, 'log'):
                klass.log.warn("The jython dexy filter should not be run on MacOS due to a serious bug. This filter is being disabled.")
            return False
        else:
            if hasattr(klass, 'log'):
                klass.log.warn("""Can't detect your system. If you see this message please report this to the dexy project maintainer, your platform.system() value is '%s'. The jython dexy filter should not be run on MacOS due to a serious bug.""" % platform.system())
            return True

class JythonInteractiveFilter(PexpectReplFilter):
    """
    jython in REPL
    """
    aliases = ['jythoni']
    _settings = {
            'check-return-code' : False,
            'tags' : ['code', 'jython', 'jvm', 'repl'],
            'executable' : 'jython -i',
            'initial-timeout' : 30,
            'input-extensions' : [".py", ".txt"],
            'output-extensions' : [".pycon"],
            'version-command' : "jython --version"
            }

    def is_active(klass):
        if platform.system() in ('Linux', 'Windows'):
            return True
        elif platform.system() in ('Darwin'):
            print "The jythoni dexy filter should not be run on MacOS due to a serious bug. This filter is being disabled."
            return False
        else:
            print """Can't detect your system. If you see this message please report this to the dexy project maintainer, your platform.system() value is '%s'. The jythoni dexy filter should not be run on MacOS due to a serious bug.""" % platform.system()
            return True

class JavaFilter(SubprocessCompileFilter):
    """
    Compiles java code and runs main method.
    """
    aliases = ['java']
    _settings = {
            'check-return-code' : True,
            'classpath' : ("Custom entries in classpath.", []),
            'tags' : ['code', 'java', 'jvm', 'compiled'],
            'executable' : 'javac',
            'input-extensions' : ['.java'],
            'output-extensions' : ['.txt'],
            'main' : ("Main method.", None),
            'version-command' : 'java -version',
            'compiled-extension' : ".class",
            'compiler-command-string' : "%(prog)s %(compiler_args)s %(classpath)s %(script_file)s"
            }

    def setup_cp(self):
        """
        Makes sure the current working directory is on the classpath, also adds
        any specified CLASSPATH elements. Assumes that CLASSPATH elements are either
        absolute paths, or paths relative to the artifacts directory. Also, if
        an input has been passed through the javac filter, its directory is
        added to the classpath.
        """
        self.log_debug("in setup_cp for %s" % self.key)

        classpath_elements = []

        working_dir = os.path.join(self.workspace(), self.output_data.parent_dir())
        abs_working_dir = os.path.abspath(working_dir)
        self.log_debug("Adding working dir %s to classpath" % abs_working_dir)
        classpath_elements.append(abs_working_dir)

        for doc in self.doc.walk_input_docs():
            if (doc.output_data().ext == ".class") and ("javac" in doc.key):
                classpath_elements.append(doc.output_data().parent_dir())

        for item in self.setting('classpath'):
            for x in item.split(":"):
                classpath_elements.append(x)

        env = self.setup_env()
        if env and env.has_key("CLASSPATH"):
            for x in env['CLASSPATH'].split(":"):
                classpath_elements.append(x)

        cp = ":".join(classpath_elements)
        self.log_debug("Classpath %s" % cp)
        return cp

    def compile_command_string(self):
        args = self.default_command_string_args()
        args['compiler_args'] = self.setting('compiler-args')

        # classpath
        cp = self.setup_cp()
        if len(cp) == 0:
            args['classpath'] = ''
        else:
            args['classpath'] = "-classpath %s" % cp

        return self.setting('compiler-command-string') % args

    def run_command_string(self):
        args = self.default_command_string_args()
        args['main_method'] = self.setup_main_method()

        # classpath
        cp = self.setup_cp()
        if len(cp) == 0:
            args['classpath'] = ''
        else:
            args['classpath'] = "-cp %s" % cp

        return "java %(args)s %(classpath)s %(main_method)s" % args

    def setup_main_method(self):
        basename = os.path.basename(self.input_data.name)
        default_main = os.path.splitext(basename)[0]
        if self.setting('main'):
            return self.setting('main')
        else:
            return default_main

class JavacFilter(JavaFilter):
    """
    Compiles java code and returns the .class object
    """
    aliases = ['javac']

    _settings = {
            'executable' : 'javac',
            'input-extensions' : ['.java'],
            'output-extensions' : ['.class'],
            'tags' : ['code', 'java', 'jvm', 'compiled'],
            'version-command' : 'java -version'
            }

    def process(self):
        # Compile the code
        command = self.compile_command_string()
        proc, stdout = self.run_command(command, self.setup_env())
        self.handle_subprocess_proc_return(command, proc.returncode, stdout)
        self.copy_canonical_file()

########NEW FILE########
__FILENAME__ = latex
from dexy.filters.process import SubprocessFilter
from dexy.utils import file_exists
import codecs
import dexy.exceptions
import dexy.utils
import os
import subprocess

class LatexFilter(SubprocessFilter):
    """
    Generates a PDF file from LaTeX source.
    """
    aliases = ['latex', 'pdflatex']
    _settings = {
            'executable' : 'pdflatex',
            'output' : True,
            'input-extensions' : ['.tex', '.txt'],
            'output-extensions' : ['.pdf'],
            'run-bibtex' : ("Should we run bibtex if a .bib file is an input?", True),
            'times-to-run-latex' : ("""How many times to run latex? (Latex is
                run one additional time if bibtex runs.)""", 2),
            'command-string' : "%(prog)s -interaction=batchmode %(args)s %(script_file)s"
            }

    def process(self):
        self.populate_workspace()

        wd = self.parent_work_dir()
        env = self.setup_env()

        latex_command = self.command_string()

        if any(doc.output_data().ext == '.bib' for doc in self.doc.walk_input_docs()):
            bibtex_command = "bibtex %s" % os.path.splitext(self.output_data.basename())[0]
        else:
            bibtex_command = None

        def run_cmd(command):
            self.log_debug("running %s in %s" % (command, os.path.abspath(wd)))
            proc = subprocess.Popen(command, shell=True,
                                    cwd=wd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    env=env)

            stdout, stderr = proc.communicate()
            self.log_debug(stdout)

        if bibtex_command and self.setting('run-bibtex'):
            run_cmd(latex_command) #generate aux
            run_cmd(bibtex_command) #generate bbl

        n = self.setting('times-to-run-latex')
        for i in range(n):
            self.log_debug("running latex time %s (out of %s)" % (i+1, n))
            run_cmd(latex_command)

        if not file_exists(os.path.join(wd, self.output_data.basename())):
            log_file_path = os.path.join(wd, self.output_data.basename().replace(".pdf", ".log"))

            if file_exists(log_file_path):
                msg = "Latex file not generated. Look for information in latex log %s"
                msgargs = log_file_path
            else:
                msg = "Latex file not generated. Look for information in latex log in %s directory."
                msgargs = os.path.abspath(wd)

            raise dexy.exceptions.UserFeedback(msg % msgargs)

        if self.setting('add-new-files'):
            self.log_debug("adding new files found in %s for %s" % (wd, self.key))
            self.add_new_files()

        self.copy_canonical_file()

class TikzPdfFilter(LatexFilter):
    """
    Renders Tikz code to PDF.
    """
    aliases = ['tikz']

    def process(self):
        latex_filename = self.output_data.basename().replace(self.ext, ".tex")

        # TODO allow setting tikz libraries per-document, or just include all of them?
        # TODO how to create a page size that just includes the content
        latex_header = """\documentclass[tikz]{standalone}
\usetikzlibrary{shapes.multipart}
\\begin{document}
        """
        latex_footer = "\n\end{document}"

        self.populate_workspace()
        wd = self.parent_work_dir()

        work_path = os.path.join(wd, latex_filename)
        self.log_debug("writing latex header + tikz content to %s" % work_path)
        with codecs.open(work_path, "w", encoding="utf-8") as f:
            f.write(latex_header)
            f.write(unicode(self.input_data))
            f.write(latex_footer)

        latex_command = "%s -interaction=batchmode %s" % (self.setting('executable'), latex_filename)

        def run_cmd(command):
            self.log_debug("about to run %s in %s" % (command, os.path.abspath(wd)))
            proc = subprocess.Popen(command, shell=True,
                                    cwd=wd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    env=self.setup_env())

            stdout, stderr = proc.communicate()

            if proc.returncode > 2: # Set at 2 for now as this is highest I've hit, better to detect whether PDF has been generated?
                raise dexy.exceptions.UserFeedback("latex error, look for information in %s" %
                                latex_filename.replace(".tex", ".log"))
            elif proc.returncode > 0:
                self.log_warn("""A non-critical latex error has occurred running %s,
                status code returned was %s, look for information in %s""" % (
                self.key, proc.returncode,
                latex_filename.replace(".tex", ".log")))

        run_cmd(latex_command)

        self.copy_canonical_file()

########NEW FILE########
__FILENAME__ = lyx
from dexy.filter import DexyFilter

class LyxJinjaFilter(DexyFilter):
    """
    Converts dexy:foo.txt|bar into << d['foo.txt|bar'] >>
    
    Makes it easier to compose documents with lyx and process them in dexy.
    This expects you to do doc.lyx|lyx|lyxjinja|jinja|latex
    """
    aliases = ['lyxjinja']
    _settings = {
            'input-extensions' : ['.tex'],
            'output-extensions' : ['.tex'],
            }

    def process_text(self, input_text):
        lines = []
        for line in input_text.splitlines():
            if line.startswith("dexy:"):
                _, clean_line = line.split("dexy:")
                if ":" in clean_line:
                    doc, section = clean_line.split(":")
                    lines.append("<< d['%s']['%s'] >>" % (doc, section,))
                else:
                    lines.append("<< d['%s'] >>" % clean_line)
            else:
                lines.append(line)
        return "\n".join(lines)

########NEW FILE########
__FILENAME__ = md
from dexy.filter import DexyFilter
import dexy.exceptions
import json
import logging
import markdown
import re

#safe_mode_docstring = """Whether to escape, remove or replace HTML blocks.
#
#Set to True or 'escape' to escape HTML, 'remove' to remove HTML, 'replace' to replace with replacement-text.
#"""
#            'safe-mode' : (safe_mode_docstring, False),
#            'replacement-text' : ("Text to replace HTML blocks if safe-mode is 'replace'.", None),

class MarkdownFilter(DexyFilter):
    """
    Runs a Markdown processor to convert markdown to HTML.

    Markdown extensions can be enabled in your config:
    http://packages.python.org/Markdown/extensions/index.html
    """
    aliases = ['markdown']
    _settings = {
            'examples' : ['markdown'],
            'input-extensions' : ['.*'],
            'output-extensions' : ['.html'],
            'extensions' : ("Which Markdown extensions to enable.", { 'toc' : {} }),
            }

    def capture_markdown_logger(self):
        markdown_logger = logging.getLogger('MARKDOWN')
        markdown_logger.addHandler(self.doc.wrapper.log.handlers[-1])

    def initialize_markdown(self):
        extension_configs = self.setting('extensions')
        extensions = extension_configs.keys()

        dbg = "Initializing Markdown with extensions: %s and extension configs: %s"
        self.log_debug(dbg % (json.dumps(extensions), json.dumps(extension_configs)))

        try:
            md = markdown.Markdown(
                    extensions=extensions,
                    extension_configs=extension_configs)
        except ValueError as e:
            self.log_debug(e.message)
            if "markdown.Extension" in e.message:
                raise dexy.exceptions.UserFeedback("There's a problem with the markdown extensions you specified.")
            else:
                raise
        except KeyError as e:
            raise dexy.exceptions.UserFeedback("Couldn't find a markdown extension option matching '%s'" % e.message)

        return md

    def process_text(self, input_text):
        self.capture_markdown_logger()
        md = self.initialize_markdown()
        return md.convert(input_text)

class MarkdownSlidesFilter(MarkdownFilter):
    """
    Converts paragraphs to HTML and wrap each slide in a header and footer.
    """
    aliases = ['slides']

    _settings = {
            'extensions' : { 'nl2br' : {} },
            'added-in-version': "0.9.9.6",
            'examples' : ['slides'],
            'comment-char' : (
                "Lines starting with this comment char will not show up in slides.",
                ';'),
            'split' : (
                "String to use to split slides.",
                "\n\n\n" # e.g. 2 blank lines.
                ),
            'slide-header' : (
                "Content to prepend to start of each slide.",
                """<section class="slide">"""
                ),
            'slide-footer' : (
                "Content to append to end of each slide.",
                """</section>"""
                ),
            }

    def process_text(self, input_text):
        self.capture_markdown_logger()
        md = self.initialize_markdown()

        slides = ""
        comment_regexp = "^%s(.*)$" % self.setting('comment-char')

        for counter, slide in enumerate(input_text.split(self.setting('split'))):
            slide = re.sub(comment_regexp, "", slide, flags=re.MULTILINE)
            html = md.convert(slide)

            # Variables to make available for string interpolation in header and footer.
            interp = {
                    'number' : (counter+1)
                    }

            header = self.setting('slide-header') % interp
            footer = self.setting('slide-footer')% interp

            slide_text = "\n%s\n%s\n%s\n" % (header, html, footer)
            slides += slide_text

        return slides

########NEW FILE########
__FILENAME__ = org
from dexy.filters.process import SubprocessFilter
import dexy.exceptions

class OrgModeFilter(SubprocessFilter):
    """
    Convert .org files to other formats.
    """
    aliases = ['org']
    _settings = {
            'executable' : 'emacs',
            'output' : True,
            'input-extensions' : ['.org', '.txt'],
            'output-extensions' : ['.txt', '.html', '.tex', '.pdf', '.odt'],
            'command-string' : """%(prog)s --batch %(args)s --eval "(progn \\
(find-file \\"%(script_file)s\\") \\
(%(export_command)s 1) \\
(kill-buffer) \\
)"
"""
            }

    def command_string_args(self):
        if self.ext == '.txt':
            export_command = "org-export-as-ascii"
        elif self.ext == '.html':
            export_command = "org-export-as-html"
        elif self.ext == '.tex':
            export_command = "org-export-as-latex"
        elif self.ext == '.pdf':
            export_command = "org-export-as-pdf"
        elif self.ext == '.odt':
            export_command = "org-export-as-odt"
        else:
            msg = "unsupported extension %s"
            msgargs = (self.ext)
            raise dexy.exceptions.InternalDexyProblem(msg % msgargs)

        args = self.default_command_string_args()
        args['export_command'] = export_command
        return args

########NEW FILE########
__FILENAME__ = pexp
from dexy.exceptions import InternalDexyProblem
from dexy.exceptions import UserFeedback
from dexy.exceptions import InactivePlugin
from dexy.filters.process import SubprocessFilter
import re
import os

try:
    import pexpect
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

class DexyEOFException(UserFeedback):
    pass

class PexpectReplFilter(SubprocessFilter):
    """
    Use pexpect to retrieve output line-by-line based on detecting prompts.
    """
    _settings = {
            'trim-prompt' : ("The closing prompt to be trimmed off.", '>>>'),
            'send-line-ending' : ("Line ending to transmit at the end of each input line.", "\n"),
            'line-ending' : ("The line ending returned by REPL.", "\n"),
            'save-vars-to-json-cmd' : ("Command to be run to save variables to a JSON file.", None),
            'ps1' : ('PS1', None),
            'ps2' : ('PS2', None),
            'ps3' : ('PS3', None),
            'ps4' : ('PS4', None),
            'term' : ('TERM', 'dumb'),
            'initial-prompt' : ("The initial prompt the REPL will display.", None),
            'prompt' : ("Single prompt to match exactly.", None),
            'prompts' : ("List of possible prompts to match exactly.", ['>>>', '...']),
            'prompt-regex' : ("A prompt regex to match.", None),
            'strip-regex' : ("Regex to strip", None),
            'data-type' : 'sectioned',
            'allow-match-prompt-without-newline' : ("Whether to require a newline before prompt.", False),
            }

    def is_active(klass):
        return AVAILABLE

    def prompt_search_terms(self):
        """
        Search first for the prompt (or prompts) following a line ending.
        Also optionally allow matching the prompt with no preceding line ending.
        """
        prompt_regex = self.setting('prompt-regex')
        prompt = self.setting('prompt')

        if prompt_regex:
            prompts = [prompt_regex]
        elif prompt:
            prompts = [prompt]
        else:
            prompts = self.setting('prompts')

        if self.setting('allow-match-prompt-without-newline'):
            return ["%s%s" % (self.setting('line-ending'), p) for p in prompts] + prompts
        else:
            return ["%s%s" % (self.setting('line-ending'), p) for p in prompts]

    def lines_for_section(self, section_text):
        """
        Take the section text and split it into lines which will be sent to the
        T
        differently, or if you don't want the extra newline at the end.
        """
        return section_text.splitlines() + ["\n"]

    def strip_trailing_prompts(self, section_transcript):
        lines = section_transcript.splitlines()
        while len(lines) > 0 and re.match("^\s*(%s)\s*$|^\s*$" % self.setting('trim-prompt'), lines[-1]):
            lines = lines[0:-1]
        return self.setting('line-ending').join(lines)

    def strip_newlines(self, line):
        return line.replace(" \r", "")

    def section_output(self):
        """
        Runs the code in sections and returns an iterator so we can do custom stuff.
        """
        input_sections = self.input_data.items()

        # If we want to automatically record values of local variables in the
        # script we are running, we add a section at the end of script
        do_record_vars = self.setting('record-vars')
        if do_record_vars:
            if not self.setting('save-vars-to-json-cmd'):
                raise UserFeedback("You specified record-vars but this option isn't available since SAVE_VARS_TO_JSON_CMD is not set for this filter.")

            section_text = self.setting('save-vars-to-json-cmd') % self.input_data.basename()
            self.log_debug("Adding save-vars-to-json-cmd code:\n%s" % section_text)
            input_sections.append(('dexy--save-vars', section_text))
            if not self.setting('add-new-files'):
                docstr = self._instance_settings['add-new-files'][0]
                self._instance_settings['add-new-files'] = (docstr, ".json")

        search_terms = self.prompt_search_terms()

        env = self.setup_env()

        if self.setting('ps1'):
            ps1 = self.setting('ps1')
            self.log_debug("Setting PS1 to %s" % ps1)
            env['PS1'] = ps1

        if self.setting('ps2'):
            ps2 = self.setting('PS2')
            self.log_debug("Setting PS2 to %s" % ps2)
            env['PS2'] = ps2

        if self.setting('ps3'):
            ps3 = self.arg_value('PS3')
            self.log_debug("Setting PS3 to %s" % ps3)
            env['PS3'] = ps3

        if self.setting('ps4'):
            ps4 = self.arg_value('PS4')
            self.log_debug("Setting PS4 to %s" % ps4)
            env['PS4'] = ps4

        env['TERM'] = self.setting('term')

        timeout = self.setup_timeout()
        initial_timeout = self.setup_initial_timeout()

        self.log_debug("timeout set to '%s'" % timeout)

        if self.setting('use-wd'):
            wd = self.parent_work_dir()
        else:
            wd = os.getcwd()

        executable = self.setting('executable')
        self.log_debug("about to spawn new process '%s' in '%s'" % (executable, wd))

        # Spawn the process
        try:
            proc = pexpect.spawn(
                    executable,
                    cwd=wd,
                    env=env)
        except pexpect.ExceptionPexpect as e:
            if "The command was not found" in unicode(e):
                raise InactivePlugin(self)
            else:
                raise

        self.log_debug("Capturing initial prompt...")
        initial_prompt = self.setting('initial-prompt')
        try:
            if initial_prompt:
                proc.expect(initial_prompt, timeout=initial_timeout)
            elif self.setting('prompt-regex'):
                proc.expect(search_terms, timeout=initial_timeout)
            else:
                proc.expect_exact(search_terms, timeout=initial_timeout)

        except pexpect.TIMEOUT:
            if self.setting('initial-prompt'):
                match = self.setting('initial-prompt')
            else:
                match = search_terms

            msg = "%s failed at matching initial prompt within %s seconds. " % (self.__class__.__name__, initial_timeout)
            msg += "Received '%s', tried to match with '%s'" % (proc.before, match)
            msg += "\nExact characters received:\n"
            for i, c in enumerate(proc.before):
                msg += "chr %02d: %s\n" % (i, ord(c))
            msg += "The developer might need to set a longer initial prompt timeout or the regexp may be wrong."
            raise InternalDexyProblem(msg)

        start = proc.before + proc.after

        self.log_debug(u"Initial prompt captured!")
        self.log_debug(unicode(start))

        for section_key, section_text in input_sections:
            section_transcript = start
            start = ""

            lines = self.lines_for_section(section_text)
            for l in lines:
                self.log_debug(u"Sending '%s'" % l)
                section_transcript += start
                proc.send(l.rstrip() + self.setting('send-line-ending'))
                try:
                    if self.setting('prompt-regex'):
                        proc.expect(search_terms, timeout=timeout)
                    else:
                        proc.expect_exact(search_terms, timeout=timeout)

                    self.log_debug(u"Received '%s'" % unicode(proc.before, errors='replace'))

                    section_transcript += self.strip_newlines(proc.before)
                    start = proc.after
                except pexpect.EOF:
                    self.log_debug("EOF occurred!")
                    raise DexyEOFException()
                except pexpect.TIMEOUT as e:
                    for c in proc.before:
                        print ord(c), ":", c
                    msg = "pexpect timeout error. failed at matching prompt within %s seconds. " % timeout
                    msg += "received '%s', tried to match with '%s'" % (proc.before, search_terms)
                    msg += "something may have gone wrong, or you may need to set a longer timeout"
                    self.log_warn(msg)
                    raise UserFeedback(msg)
                except pexpect.ExceptionPexpect as e:
                    raise UserFeedback(unicode(e))
                except pexpect.EOF as e:
                    raise UserFeedback(unicode(e))

            if self.setting('strip-regex'):
                section_transcript = re.sub(self.setting('strip-regex'), "", section_transcript)

            yield section_key, section_transcript

        if self.setting('add-new-files'):
            self.add_new_files()

        try:
            proc.close()
        except pexpect.ExceptionPexpect:
            msg = "process %s may not have closed for %s"
            msgargs = (proc.pid, self.key)
            raise UserFeedback(msg % msgargs)

        if proc.exitstatus and self.setting('check-return-code'):
            self.handle_subprocess_proc_return(self.setting('executable'), proc.exitstatus, section_transcript)

    def process(self):
        self.log_debug("about to populate_workspace")
        self.populate_workspace()

        for section_name, section_transcript in self.section_output():
            raw = self.strip_trailing_prompts(section_transcript)
            self.log_debug("About to append section %s" % section_name)
            self.output_data[section_name] = self.doc.wrapper.decode_encoded(raw)

        self.output_data.save()

try:
    import IPython
    IPYTHON_AVAILABLE = True
except ImportError:
    IPYTHON_AVAILABLE = False

class IpythonPexpectReplFilter(PexpectReplFilter):
    """
    Runs python code in the IPython console.
    """
    aliases = ['ipython']
    _settings = {
            'executable' : 'ipython --classic',
            'check-return-code' : False,
            'tags' : ['python', 'repl', 'code'],
            'input-extensions' : [".txt", ".py"],
            'output-extensions' : [".pycon"],
            'version-command' : 'ipython -Version'
            }

    def is_active(klass):
        return IPYTHON_AVAILABLE

class ClojureInteractiveFilter(PexpectReplFilter):
    """
    Runs clojure in REPL.
    """
    aliases = ['cljint']
    _settings = {
            'check-return-code' : False,
            'executable' : 'clojure -r',
            'tags' : ['code', 'clojure', 'repl'],
            'input-extensions' : [".clj", ".txt"],
            'output-extensions' : [".txt"],
            'prompt' : "user=> "
            }

    def lines_for_section(self, input_text):
        input_lines = []
        current_line = []
        in_indented_block = False
        for l in input_text.splitlines():
            if re.match("^\s+", l):
                in_indented_block = True
                current_line.append(l)
            else:
                if len(current_line) > 0:
                    input_lines.append("\n".join(current_line))
                if in_indented_block:
                    # we have reached the end of this indented block
                    in_indented_block = False
                current_line = [l]
        input_lines.append("\n".join(current_line))
        return input_lines

class PythonConsole(PexpectReplFilter):
    """
    Runs python code in python's REPL.
    """

    aliases = ['pycon', 'pyrepl']
    _settings = {
            'check-return-code' : False,
            'tags' : ['repl', 'python', 'code'],
            'executable' : 'python',
            'initial-prompt' : '>>>',
            'input-extensions' : [".txt", ".py"],
            'output-extensions' : ['.pycon'],
            'version-command' : 'python --version',
            'save-vars-to-json-cmd' : """import json
with open("%s-vars.json", "w") as dexy__vars_file:
    dexy__x = {}
    for dexy__k, dexy__v in locals().items():
        try:
            dexy__x[dexy__k] = json.dumps(dexy__v)
        except Exception:
            pass
    json.dump(dexy__x, dexy__vars_file)"""}


########NEW FILE########
__FILENAME__ = phantomjs
from dexy.filters.process import SubprocessFilter
import os

class CasperJsSvg2PdfFilter(SubprocessFilter):
    """
    Converts an SVG file to PDF by running it through casper js.

    # TODO convert this to phantomjs, no benefit to using casper here (js is
    # not user facing) and more restrictive
    """
    aliases = ['svg2pdf']
    _settings = {
            'add-new-files' : True,
            'executable' : 'casperjs',
            'version-command' : 'casperjs --version',
            "input-extensions" : ['.svg'],
            "output-extensions" : ['.pdf'],
            "width" : ("Width of page to capture.", 200),
            "height" : ("Height of page to capture.", 200),
            "command-string" : "%(prog)s %(args)s script.js"
            }

    def script_js(self, width, height):
        args = {
                'width' : width,
                'height' : height,
                'svgfile' : self.work_input_filename(),
                'pdffile' : self.work_output_filename()
                }
        return """
        var casper = require('casper').create({
             viewportSize : {width : %(width)s, height : %(height)s}
        });
        casper.start('%(svgfile)s', function() {
            this.capture('%(pdffile)s');
        });

        casper.run();
        """ % args

    def custom_populate_workspace(self):
        width = self.setting('width')
        height = self.setting('height')
        js = self.script_js(width, height)

        wd = self.parent_work_dir()
        scriptfile = os.path.join(wd, "script.js")

        self.log_debug("scriptfile: %s" % scriptfile)
        self.log_debug("js for scriptfile: %s" % js)

        with open(scriptfile, "w") as f:
            f.write(js)

class PhantomJsRenderSubprocessFilter(SubprocessFilter):
    """
    Renders HTML to PNG/PDF using phantom.js.
    
    If the HTML relies on local assets such as CSS or image files, these should
    be specified as inputs.
    """
    aliases = ['phrender']
    _settings = {
            'add-new-files' : True,
            'examples' : ['phrender'],
            'executable' :  'phantomjs',
            "width" : ("Width of page to capture.", 1024),
            "height" : ("Height of page to capture.", 768),
            'version-command' : 'phantomjs --version',
            'command-string' : "%(prog)s %(args)s script.js",
            'input-extensions' : [".html", ".htm", ".txt"],
            'output-extensions' : [".png", ".pdf"]
            }

    def custom_populate_workspace(self):
        width = self.setting('width')
        height = self.setting('height')

        timeout = self.setup_timeout()
        if not timeout:
            raise Exception("must have timeout")

        args = {
                'address' : self.work_input_filename(),
                'output' : self.work_output_filename(),
                'width' : width,
                'height' : height,
                'timeout' : timeout
                }

        js = """
        address = '%(address)s'
        output = '%(output)s'
        var page = new WebPage(),
            address, output, size;

        page.viewportSize = { width: %(width)s, height: %(height)s };
        page.open(address, function (status) {
            if (status !== 'success') {
                console.log('Unable to load the address!');
            } else {
                window.setTimeout(function () {
                page.render(output);
                phantom.exit();
                }, %(timeout)s);
            }
        });
        """ % args

        wd = self.parent_work_dir()
        scriptfile = os.path.join(wd, "script.js")
        self.log_debug("scriptfile: %s" % scriptfile)
        self.log_debug("js for scriptfile: %s" % js)
        with open(scriptfile, "w") as f:
            f.write(js)

########NEW FILE########
__FILENAME__ = process
from dexy.filter import Filter
from dexy.utils import file_exists
import dexy.exceptions
import fnmatch
import os
import platform
import subprocess

class SubprocessFilter(Filter):
    """
    Parent class for all filters which use the subprocess module.
    """
    aliases = []
    _settings = {
            'args' : ("Arguments to be passed to the executable.", ''),
            'check-return-code' : ("Whether to look for nonzero return code.", True),
            'clargs' : ("Arguments to be passed to the executable (same as 'args').", ''),
            'command-string' : ("The full command string.", """%(prog)s %(args)s "%(script_file)s" %(scriptargs)s "%(output_file)s" """),
            'env' : ("Dictionary of key-value pairs to be added to environment for runs.", {}),
            'executable' : ('The executable to be run', None),
            'initial-timeout' : ('', 10),
            'path-extensions' : ("strings to extend path with", []),
            'record-vars' : ("Whether to add code that will automatically record values of variables.", False),
            'scriptargs' : ("Arguments to be passed to the executable.", ''),
            'tags' : [],
            'timeout' : ('', 10),
            'use-wd' : ("Whether to use a custom working directory when running filter.", True),
            'version-command': ( "Command to call to return version of installed software.", None),
            'windows-version-command': ( "Command to call on windows to return version of installed software.", None),
            'write-stderr-to-stdout' : ("Should stderr be piped to stdout?", True),
            }

    def version_command(klass):
        if platform.system() == 'Windows':
            return klass.setting('windows-version-command') or klass.setting('version-command')
        else:
            return klass.setting('version-command')

    def version(klass):
        command = klass.version_command()
        if command:
            proc = subprocess.Popen(
                       command,
                       shell=True,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT
                   )

            stdout, stderr = proc.communicate()
            if proc.returncode > 0:
                return False
            else:
                return stdout.strip().split("\n")[0]

    def process(self):
        command = self.command_string()
        proc, stdout = self.run_command(command, self.setup_env())
        self.handle_subprocess_proc_return(command, proc.returncode, stdout)
        self.copy_canonical_file()

        if self.setting('add-new-files'):
            self.log_debug("adding new files found in %s for %s" % (self.workspace(), self.key))
            self.add_new_files()

    def command_string_args(self):
        return self.default_command_string_args()

    def default_command_string_args(self):
        args = {
                'args' : " ".join([self.setting('args'), self.setting('clargs')]),
                'prog' : self.setting('executable'),
                'script_file' : self.work_input_filename(),
                'output_file' : self.work_output_filename()
                }
        skip = ['args', 'clargs']
        args.update(self.setting_values(skip))
        return args

    def command_string(self):
        return self.setting('command-string') % self.command_string_args()

    def ignore_nonzero_exit(self):
        return self.doc.wrapper.ignore_nonzero_exit

    def clear_cache(self):
        self.output_data.clear_cache()

    def handle_subprocess_proc_return(self, command, exitcode, stderr, compiled=False):
        self.log_debug("exit code is '%s'" % exitcode)
        if exitcode is None:
            raise dexy.exceptions.InternalDexyProblem("no return code, proc not finished!")
        elif exitcode == 127 and not compiled:
            raise dexy.exceptions.InactivePlugin(self)
        elif exitcode != 0 and self.setting('check-return-code'):
            if self.ignore_nonzero_exit():
                self.log_warn("Nonzero exit status %s" % exitcode)
                self.log_warn("output from process: %s" % stderr)
            else:
                err_msg = "The command '%s' for %s exited with nonzero exit status %s." % (command, self.key, exitcode)
                if stderr:
                    err_msg += " Here is stderr:\n%s" % stderr
                self.output_data.clear_cache()
                raise dexy.exceptions.UserFeedback(err_msg)

    def setup_timeout(self):
        return self.setting('timeout')

    def setup_initial_timeout(self):
        return self.setting('initial-timeout')

    def setup_env(self):
        env = os.environ

        env.update(self.setting('env'))

        env['DEXY_ROOT'] = os.path.abspath(".")

        # Add parameters in wrapper's env dict
        if self.is_part_of_script_bundle():
            for key, value in self.script_storage().iteritems():
                if key.startswith("DEXY_"):
                    self.log_debug("Adding %s to env value is %s" % (key, value))
                    env[key] = value

        # Add any path extensions to PATH
        if self.setting('path-extensions'):
            paths = [env['PATH']] + self.setting('path-extensions')
            env['PATH'] = ":".join(paths)

        return env

    def add_new_files(self):
        """
        Walk working directory and add a new dexy document for every newly
        created file found.
        """
        wd = self.workspace()
        self.log_debug("adding new files found in %s for %s" % (wd, self.key))

        add_new_files = self.setting('add-new-files')
        if isinstance(add_new_files, basestring):
            add_new_files = [add_new_files]

        exclude = self.setting('exclude-add-new-files')
        skip_dirs = self.setting('exclude-new-files-from-dir')

        if isinstance(exclude, basestring):
            raise dexy.exceptions.UserFeedback("exclude-add-new-files should be a list, not a string")

        new_files_added = 0
        for dirpath, subdirs, filenames in os.walk(wd):
            # Prune subdirs which match exclude.
            subdirs[:] = [d for d in subdirs if d not in skip_dirs]

            # Iterate over files in directory.
            for filename in filenames:
                filepath = os.path.normpath(os.path.join(dirpath, filename))
                relpath = os.path.relpath(filepath, wd)
                self.log_debug("Processing %s" % filepath)

                if relpath in self._files_workspace_populated_with:
                    # already have this file
                    continue

                if isinstance(add_new_files, list):
                    is_valid_file_extension = False
                    for pattern in add_new_files:
                        if "*" in pattern:
                            if fnmatch.fnmatch(relpath, pattern):
                                is_valid_file_extension = True
                                continue
                        else:
                            if filename.endswith(pattern):
                                is_valid_file_extension = True
                                continue

                    if not is_valid_file_extension:
                        msg = "Not adding filename %s, does not match patterns: %s"
                        args = (filepath, ", ".join(add_new_files))
                        self.log_debug(msg % args)
                        continue

                elif isinstance(add_new_files, bool):
                    if not add_new_files:
                        msg = "add_new_files method should not be called if setting is False"
                        raise dexy.exceptions.InternalDexyProblem(msg)
                    is_valid_file_extension = True

                else:
                    msg = "add-new-files setting should be list or boolean. Type is %s value is %s"
                    args = (add_new_files.__class__, add_new_files,)
                    raise dexy.exceptions.InternalDexyProblem(msg % args)

                # Check if should be excluded.
                skip_because_excluded = False
                for skip_pattern in exclude:
                    if skip_pattern in filepath:
                        msg = "skipping adding new file %s because it matches exclude %s"
                        args = (filepath, skip_pattern,)
                        self.log_debug(msg % args)
                        skip_because_excluded = True
                        continue

                if skip_because_excluded:
                    continue

                if not is_valid_file_extension:
                    raise Exception("Should not get here unless is_valid_file_extension")

                with open(filepath, 'rb') as f:
                    contents = f.read()
                self.add_doc(relpath, contents)
                new_files_added += 1

        if new_files_added > 10:
            self.log_warn("%s additional files added" % (new_files_added))

    def run_command(self, command, env, input_text=None):
        if self.setting('use-wd'):
            ws = self.workspace()
            if os.path.exists(ws):
                self.log_debug("already have workspace '%s'" % os.path.abspath(ws))
            else:
                self.populate_workspace()

        stdout = subprocess.PIPE

        if input_text:
            stdin = subprocess.PIPE
        else:
            stdin = None

        if self.setting('write-stderr-to-stdout'):
            stderr = subprocess.STDOUT
        else:
            stderr = subprocess.PIPE

        if self.setting('use-wd'):
            wd = self.parent_work_dir()
        else:
            wd = os.getcwd()

        self.log_debug("about to run '%s' in '%s'" % (command, os.path.abspath(wd)))
        proc = subprocess.Popen(command, shell=True,
                                    cwd=wd,
                                    stdin=stdin,
                                    stdout=stdout,
                                    stderr=stderr,
                                    env=env)

        if input_text:
            self.log_debug("about to send input_text '%s'" % input_text)

        stdout, stderr = proc.communicate(input_text)
        self.log_debug(u"stdout is '%s'" % stdout.decode('utf-8'))

        if stderr:
            self.log_debug(u"stderr is '%s'" % stderr.decode('utf-8'))

        return (proc, stdout)

    def copy_canonical_file(self):
        canonical_file = os.path.join(self.workspace(), self.output_data.name)
        if not self.output_data.is_cached() and file_exists(canonical_file):
            self.output_data.copy_from_file(canonical_file)

class SubprocessStdoutFilter(SubprocessFilter):
    """
    Runs a command and returns the resulting stdout.
    """
    _settings = {
            'write-stderr-to-stdout' : False,
            'require-output' : False,
            'command-string' : '%(prog)s %(args)s "%(script_file)s" %(scriptargs)s'
            }

    def process(self):
        command = self.command_string()
        proc, stdout = self.run_command(command, self.setup_env())
        self.handle_subprocess_proc_return(command, proc.returncode, stdout)
        self.output_data.set_data(stdout)

        if self.setting('add-new-files'):
            self.add_new_files()

class SubprocessCompileFilter(SubprocessFilter):
    """
    Compiles code and runs the compiled executable.
    """
    _settings = {
            'add-new-files' : False,
            'check-return-code' : False,
            'compiled-extension' : ("Extension which compiled files end with.", ".o"),
            'compiler-command-string' : (
                "Command string to call compiler.",
                "%(prog)s %(compiler_args)s %(script_file)s -o %(compiled_filename)s"
                ),
            'compiler-args' : ("Args to pass to compiler.", '')
            }

    def compile_command_string(self):
        args = self.default_command_string_args()
        args['compiler_args'] = self.setting('compiler-args')
        args['compiled_filename'] = self.compiled_filename()
        return self.setting('compiler-command-string') % args

    def compiled_filename(self):
        basename = os.path.basename(self.input_data.name)
        nameroot = os.path.splitext(basename)[0]
        return "%s%s" % (nameroot, self.setting('compiled-extension'))

    def run_command_string(self):
        args = self.default_command_string_args()
        args['compiled_filename'] = self.compiled_filename()
        return "./%(compiled_filename)s %(args)s" % args

    def process(self):
        env = self.setup_env()

        # Compile the code
        command = self.compile_command_string()
        proc, stdout = self.run_command(command, env)

        # test exitcode from the *compiler*
        self.handle_subprocess_proc_return(command, proc.returncode, stdout)

        # Run the compiled code
        command = self.run_command_string()
        proc, stdout = self.run_command(command, env)

        # This tests exitcode from the compiled script.
        self.handle_subprocess_proc_return(command, proc.returncode, stdout, compiled=True)

        self.output_data.set_data(stdout)

        if self.setting('add-new-files'):
            msg = "adding new files found in %s for %s" 
            msgargs = (self.workspace(), self.key)
            self.log_debug(msg % msgargs)
            self.add_new_files()

class SubprocessInputFilter(SubprocessFilter):
    """
    Runs code which expects stdin.
    """
    _settings = {
            'data-type' : 'sectioned',
            'check-return-code' : False,
            'write-stderr-to-stdout' : False
            }

    def process(self):
        command = self.command_string()

        inputs = list(self.doc.walk_input_docs())

        if len(inputs) == 1:
            doc = inputs[0]
            for section_name, section_input in doc.output_data().iteritems():
                proc, stdout = self.run_command(command, self.setup_env(), unicode(section_input))
                self.output_data[section_name] = stdout
        else:
            for doc in inputs:
                proc, stdout = self.run_command(command, self.setup_env(), unicode(doc.output_data()))
                self.handle_subprocess_proc_return(command, proc.returncode, stdout)
                self.output_data[doc.key] = stdout

        self.output_data.save()

class SubprocessInputFileFilter(SubprocessFilter):
    """
    Runs code which expects input files.
    """
    _settings = {
            'data-type' : 'sectioned',
            'check-return-code' : False,
            'write-stderr-to-stdout' : False,
            'command-string' : """%(prog)s %(args)s %(input_text)s "%(script_file)s" """
            }

    def command_string_args(self, input_doc):
        args = self.default_command_string_args()
        args['input_text'] = input_doc.name
        return args
    
    def command_string_for_input(self, input_doc):
        return self.setting('command-string') % self.command_string_args(input_doc)

    def process(self):
        self.populate_workspace()

        for doc in self.doc.walk_input_docs():
            command = self.command_string_for_input(doc)
            proc, stdout = self.run_command(command, self.setup_env())
            self.handle_subprocess_proc_return(command, proc.returncode, stdout)
            self.output_data[doc.key] = stdout

        self.output_data.save()

class SubprocessCompileInputFilter(SubprocessCompileFilter):
    """
    Compiles code and runs executable with stdin.
    """
    _settings = {
            'data-type' : 'sectioned',
            'check-return-code' : False,
            'write-stderr-to-stdout' : False
            }

    def process(self):
        # Compile the code
        command = self.compile_command_string()
        proc, stdout = self.run_command(command, self.setup_env())
        self.handle_subprocess_proc_return(command, proc.returncode, stdout)

        command = self.run_command_string()

        inputs = list(self.doc.walk_input_docs())

        if len(inputs) == 1:
            doc = inputs[0]
            for section_name, section_input in doc.output_data().iteritems():
                proc, stdout = self.run_command(command, self.setup_env(), section_input)
                self.handle_subprocess_proc_return(command, proc.returncode, stdout)
                self.output_data[section_name] = stdout
        else:
            for doc in inputs:
                proc, stdout = self.run_command(command, self.setup_env(), unicode(doc.output_data()))
                self.handle_subprocess_proc_return(command, proc.returncode, stdout)
                self.output_data[doc.key] = stdout

        self.output_data.save()

class SubprocessFormatFlagFilter(SubprocessFilter):
    """
    Special handling of format flags based on file extensions.

    For example, ragel -R for ruby.
    """
    _settings = {
            'ext-to-format' : ("A dict of mappings from file extensions to format flags that need to be passed on the command line, e.g. for ragel with ruby host language .rb => -R", {})
            }

    def command_string_args(self):
        args = self.default_command_string_args()

        flags = self.setting('ext-to-format')

        if any(f in args['args'] for f in flags):
            # Already have specified the format manually.
            fmt = ''
        else:
            fmt = flags[self.ext]

        args['format'] = fmt
        return args

class SubprocessExtToFormatFilter(SubprocessFilter):
    """
    Subprocess filters which have ext-to-format param.
    """
    _settings = {
            'format-specifier' : ("The string used to specify the format switch, include trailing space if needed.", None),
            'ext-to-format' : ("A dict of mappings from file extensions to format parameters that need to be passed on the command line, e.g. for ghostscript .png => png16m", {})
            }

    def command_string_args(self):
        args = self.default_command_string_args()

        fmt_specifier = self.setting('format-specifier')
        if fmt_specifier and (fmt_specifier in args['args']):
            # Already have specified the format manually.
            fmt = ''
        else:
            fmt_setting = self.setting('ext-to-format')[self.ext]
            if fmt_setting:
                fmt = "%s%s" % (fmt_specifier, fmt_setting)
            else:
                fmt = ''

        args['format'] = fmt
        return args

class SubprocessStdoutTextFilter(SubprocessStdoutFilter):
    """
    Runs command with input passed on command line.
    """
    _settings = {
            'command-string' : "%(prog)s %(args)s \"%(text)s\"",
            'input-extensions' : ['.txt'],
            'output-extensions' : ['.txt']
            }

    def command_string_args(self):
        args = self.default_command_string_args()
        args['text'] = unicode(self.input_data)
        return args

########NEW FILE########
__FILENAME__ = pydoc
from dexy.exceptions import InternalDexyProblem
from dexy.exceptions import UserFeedback
from dexy.filter import DexyFilter
import imp
import inspect
import json
import os
import pkgutil
import sqlite3
import sys


# from https://nose.readthedocs.org/en/latest/plugins/skip.html
try:
    # 2.7
    from unittest.case import SkipTest
except ImportError:
    # 2.6 and below
    class SkipTest(Exception):
        """Raise this exception to mark a test as skipped.
        """
    pass

class PythonIntrospection(DexyFilter):
    """
    Base class for classes which use python introspection.
    """
    import_err_msg = "Could not import '%s' received err: %s"
    aliases = []
    _settings = {
            'error-on-import-fail' : (
                "Should an exception be raised if importing a specified module or file fails?",
                False
                ),
            'input-extensions' : ['.txt', '.py'],
            'data-type' : 'keyvalue',
            'output-extensions' : ['.sqlite3', '.json']
            }

    def add_workspace_to_sys_path(self):
        sys.path.append(self.parent_work_dir())
        sys.path.append(self.workspace())

    def handle_fail(self, name, e):
        msg = self.import_err_msg % (name, e)
        if self.setting('error-on-import-fail'):
            raise UserFeedback(msg)
        else:
            self.log_debug(e)

    def load_module(self, name):
        try:
            __import__(name)
            return sys.modules[name]
        except (ImportError, TypeError) as e:
            self.handle_fail(name, e)

    def load_source_file(self):
        self.populate_workspace()
        self.add_workspace_to_sys_path()

        name = self.input_data.name
        target = os.path.join(self.workspace(), name)
        try:
            return imp.load_source("dummy", target)
        except (ImportError, SkipTest) as e:
            self.handle_fail(name, e)

class Pydoc(PythonIntrospection):
    """
    Returns introspected python data in key-value storage format.

    Where input is a .txt file, this is assumed to be the name of an installed
    python module.

    Where input is a .py file, the file itself is loaded and parsed.
    """
    aliases = ["pydoc"]
    _settings = {
            'additional-dirs' : ("Additional source directories to load, relative to package root. Useful for tests/", [])
            }

    def append_item_content(self, key, item):
        self.log_debug("appending content for %s" % key)

        try:
            source = inspect.getsource(item)
            self.output_data.append("%s:source" % key, source)
        except (TypeError, IOError, sqlite3.ProgrammingError):
            pass

        try:
            doc = inspect.getdoc(item)
            self.output_data.append("%s:doc" % key, doc)
        except (TypeError, IOError, sqlite3.ProgrammingError):
            pass

        try:
            comment = inspect.getcomments(item)
            self.output_data.append("%s:comments" % key, comment)
        except (TypeError, IOError, sqlite3.ProgrammingError):
            pass

        try:
            value = json.dumps(item)
            self.output_data.append("%s:value" % key, value)
        except TypeError:
            pass

    def is_defined_in_module(self, mod, mod_name, item):
        if mod_name and hasattr(item, '__module__'):
            return item.__module__.startswith(mod_name)
        else:
            return True

    def process_members(self, mod):
        mod_name = mod.__name__

        if mod_name == 'dummy':
            mod_name = None

        for k, m in inspect.getmembers(mod):
            if mod_name:
                key = "%s.%s" % (mod_name, k)
            else:
                key = k

            is_class = inspect.isclass(m)
            is_def = self.is_defined_in_module(mod, mod_name, m)

            if not is_def:
                # this is something imported, not defined in the module
                # so we don't want to document it here
                self.log_debug("skipping %s for module %s" % (k, mod_name))
                continue

            if not is_class:
                self.append_item_content(key, m)

            else:
                self.append_item_content(key, m)
                for ck, cm in inspect.getmembers(m):
                    self.append_item_content("%s.%s" % (key, ck), cm)

    def process_module(self, package_name, name):
        self.log_debug("processing module %s" % name)
        mod = self.load_module(name)
        self.append_item_content(name, mod)
        if mod:
            self.process_members(mod)
        else:
            self.log_warn("no mod from %s" % name)

    def process_package(self, package):
        """
        Iterates over all modules included in the package and processes them.
        """
        self.log_debug("processing package %s" % package)
        package_name = package.__name__

        # Process top level package
        self.process_module(package_name, package_name)

        # Process sub-packages and modules
        if hasattr(package, '__path__'):
            path = package.__path__
            prefix = "%s." % package_name
            for loader, name, ispkg in pkgutil.walk_packages(path, prefix=prefix):
                self.process_module(package_name, name)

    def process_packages(self):
        package_names = unicode(self.input_data).split()
        packages = [__import__(name) for name in package_names]

        for package in packages:
            self.process_package(package)

    def process_file(self):
        mod = self.load_source_file()
        if mod:
            self.process_members(mod)

    def process(self):
        if self.prev_ext == '.txt':
            self.process_packages()
        elif self.prev_ext == '.py':
            self.process_file()
        else:
            raise InternalDexyProblem("Should not have ext %s" % self.prev_ext)

        self.output_data.save()

########NEW FILE########
__FILENAME__ = pyg
from dexy.filter import DexyFilter
from dexy.utils import indent
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.formatters import LatexFormatter
from pygments.formatters import get_formatter_for_filename
from pygments.lexers import LEXERS as PYGMENTS_LEXERS
from pygments.lexers import get_lexer_by_name
import dexy.commands
import dexy.exceptions
import posixpath
import pygments.lexers.web

pygments_lexer_cache = {}

file_ext_to_lexer_alias_cache = {
        '.pycon' : 'pycon',
        '.rbcon' : 'rbcon',
        '.Rd' : 'latex',
        '.svg' : 'xml',
        '.jinja' : 'jinja'
        }

# Add all pygments standard mappings.
for module_name, name, aliases, file_extensions, _ in PYGMENTS_LEXERS.itervalues():
    alias = aliases[0]
    for ext in file_extensions:
        ext = ext.lstrip("*")
        file_ext_to_lexer_alias_cache[ext] = alias

class SyntaxHighlightRstFilter(DexyFilter):
    """
    Surrounds code with highlighting instructions for ReST
    """
    aliases = ['pyg4rst']
    _settings = {
            'n' : ("Number of chars to indent.", 2),
            'data-type' : 'sectioned'
            }

    def process(self):
        n = self.setting('n')
        lexer_alias = file_ext_to_lexer_alias_cache[self.input_data.ext]

        for section_name, section_input in self.input_data.iteritems():
            with_spaces = indent(section_input, n)
            section_output = ".. code:: %s\n\n%s" % (lexer_alias, with_spaces)
            self.output_data[section_name] = section_output

        self.output_data.save()

class SyntaxHighlightAsciidoctor(DexyFilter):
    """
    Surrounds code with highlighting instructions for Asciidoctor
    """
    aliases = ['asciisyn']
    _settings = {
            'lexer' : ("Specify lexer if can't be detected fro mfilename.", None),
            'data-type' : 'sectioned'
            }

    def process(self):
        if self.setting('lexer'):
            lexer_alias = self.setting('lexer')
        elif self.prev_filter and self.prev_filter.alias == 'idio':
            lexer_alias = file_ext_to_lexer_alias_cache[self.prev_filter.prev_ext]
        else:
            lexer_alias = file_ext_to_lexer_alias_cache[self.input_data.ext]

        for section_name, section_input in self.input_data.iteritems():
            section_output = "[source,%s]\n----\n%s\n----\n" % (lexer_alias, section_input)
            self.output_data[section_name] = section_output

        self.output_data.save()

class PygmentsFilter(DexyFilter):
    """
    Apply Pygments <http://pygments.org/> syntax highlighting.
    
    Image output formats require PIL to be installed.
    """
    aliases = ['pyg', 'pygments']
    IMAGE_OUTPUT_EXTENSIONS = ['.png', '.bmp', '.gif', '.jpg']
    MARKUP_OUTPUT_EXTENSIONS = [".html", ".tex", ".svg", ".txt"] # make sure .html is first so it is default output format
    LEXER_ERR_MSG = """Pygments doesn't know how to syntax highlight files like '%s' (for '%s').\
    You might need to specify the lexer manually."""

    _settings = {
            'examples' : ['pygments', 'pygments-image', 'pygments-stylesheets'],
            'input-extensions' : [".*"],
            'output-extensions' : MARKUP_OUTPUT_EXTENSIONS + IMAGE_OUTPUT_EXTENSIONS + ['.css', '.sty'],

            'lexer' : ("""The name of the pygments lexer to use (will normally
            be determined automatically, only use this if you need to override
            the default setting or your filename isn't mapped to the lexer you
            want to use.""", None),
            'allow-unknown-ext' : ("""Whether to allow unknown file extensions
                to be parsed with the TextLexer by default instead of raising
                an exception.""", True),
            'allow-unprintable-input' : ("""Whether to allow unprintable input
                to be replaced with dummy text instead of raising an exception.""",
                True),
            'unprintable-input-text' : ("""Dummy text to use instead of
                unprintable binary input.""", 'not printable'),
            'lexer-args' : (
                "Dictionary of custom arguments to be passed directly to the lexer.",
                {}
                ),
            'lexer-settings' : (
                "List of all settings which will be passed to the lexer constructor.",
                []
            ),
            'formatter-settings' : (
                """List of all settings which will be passed to the formatter
                constructor.""", ['style', 'full', 'linenos', 'noclasses']
            ),

            'style' : ( "Formatter style to output.", 'default'),
            'noclasses' : ( "If set to true, token <span> tags will not use CSS classes, but inline styles.", None),
            'full' : ("""Pygments formatter option: output a 'full' document
                including header/footer tags.""", None),
            'linenos' : ("""Whether to include line numbers. May be set to
                'table' or 'inline'.""", None),
            'line-numbers' : ("""Alternative name for 'linenos'.""", None),
            }

    lexer_cache = {}

    def data_class_alias(klass, file_ext):
        if file_ext in klass.MARKUP_OUTPUT_EXTENSIONS:
            return 'sectioned'
        else:
            return 'generic'

    def docmd_css(klass, style='default'):
        """
        Prints out CSS for the specified style.
        """
        print klass.generate_css(style)

    def docmd_sty(klass, style='default'):
        """
        Prints out .sty file (latex) for the specified style.
        """
        print klass.generate_sty(style)

    def generate_css(self, style='default'):
        formatter = HtmlFormatter(style=style)
        return formatter.get_style_defs()

    def generate_sty(self, style='default'):
        formatter = LatexFormatter(style=style)
        return formatter.get_style_defs()

    def calculate_canonical_name(self):
        ext = self.prev_ext
        if ext in [".css", ".sty"] and self.ext == ext:
            return self.doc.name
        elif self.alias == 'htmlsections':
            name_without_ext = posixpath.splitext(self.doc.name)[0]
            return "%s%s" % (name_without_ext, self.ext)
        else:
            return "%s%s" % (self.doc.name, self.ext)

    def constructor_args(self, constructor_type, custom_args=None):
        if custom_args:
            args = custom_args
        else:
            args = {}

        for argname in self.setting("%s-settings" % constructor_type):
            if self.setting(argname):
                args[argname] = self.setting(argname)
        return args

    def lexer_alias(self, ext):
        if self.setting('lexer'):
            self.log_debug("custom lexer %s specified" % self.setting('lexer'))
            return self.setting('lexer')

        is_json_file = ext in ('.json', '.dexy') or self.output_data.name.endswith(".dexy")

        if is_json_file and (pygments.__version__ < '1.5'):
            return "javascript"
        elif is_json_file:
            return "json"

        if ext == '.Makefile' or (ext == '' and 'Makefile' in self.input_data.name):
            return 'makefile'

        try:
            return file_ext_to_lexer_alias_cache[ext]
        except KeyError:
            pass

    def create_lexer_instance(self):
        ext = self.prev_ext
        lexer_alias = self.lexer_alias(ext)
        lexer_args = self.constructor_args('lexer')
        lexer_args.update(self.setting('lexer-args'))

        if not lexer_alias:
            msg = self.LEXER_ERR_MSG
            msgargs = (self.input_data.name, self.key)

            if self.setting('allow-unknown-ext'):
                self.log_warn(msg % msgargs)
                lexer_alias = 'text'
            else:
                raise dexy.exceptions.UserFeedback(msg % msgargs)

        if lexer_alias in pygments_lexer_cache and not lexer_args:
            return pygments_lexer_cache[lexer_alias]
        else:
            lexer = get_lexer_by_name(lexer_alias, **lexer_args)
            if not lexer_args:
                pygments_lexer_cache[lexer_alias] = lexer
            return lexer

        return lexer

    def create_formatter_instance(self):
        if self.setting('line-numbers') and not self.setting('linenos'):
            self.update_settings({'linenos' : self.setting('line-numbers')})

        formatter_args = self.constructor_args('formatter', {
            'lineanchors' : self.output_data.web_safe_document_key() })
        self.log_debug("creating pygments formatter with args %s" % (formatter_args))

        return get_formatter_for_filename(self.output_data.name, **formatter_args)

    def process(self):
        if self.ext in self.IMAGE_OUTPUT_EXTENSIONS:
            try:
                import PIL
                PIL # because pyflakes
            except ImportError:
                print "python imaging library is required by pygments to create image output"
                raise dexy.exceptions.InactivePlugin('pyg')

        ext = self.prev_ext
        if ext in [".css", ".sty"] and self.ext == ext:
            # Special case if we get a virtual empty file, generate style file

            self.log_debug("creating a style file in %s" % self.key)
            if ext == '.css':
                output = self.generate_css(self.setting('style'))
            elif ext == '.sty':
                output = self.generate_sty(self.setting('style'))
            else:
                msg = "pyg filter doesn't know how to generate a stylesheet for %s extension"
                msgargs = (ext)
                raise dexy.commands.UserFeedback(msg % msgargs)

            self.output_data.set_data(output)
            self.update_all_args({'override-workspace-exclude-filters' : True })

        else:
            lexer = self.create_lexer_instance()

            if self.ext in self.IMAGE_OUTPUT_EXTENSIONS:
                # Place each section into an image.
                for k, v in self.input_data.iteritems():
                    formatter = self.create_formatter_instance()
                    output_for_section = highlight(unicode(v).decode("utf-8"), lexer, formatter)
                    new_doc_name = "%s--%s%s" % (self.doc.key.replace("|", "--"), k, self.ext)
                    self.add_doc(new_doc_name, output_for_section)

                # Place entire contents into main file.
                formatter = self.create_formatter_instance()
                self.update_all_args({'override-workspace-exclude-filters' : True })
                with open(self.output_filepath(), 'wb') as f:
                    f.write(highlight(unicode(self.input_data), lexer, formatter))

            else:
                formatter = self.create_formatter_instance()
                for section_name, section_input in self.input_data.iteritems():
                    try:
                        section_output = highlight(unicode(section_input).decode("utf-8"), lexer, formatter)
                    except UnicodeDecodeError:
                        if self.setting('allow-unprintable-input'):
                            section_input = self.setting('unprintable-input-text')
                            section_output = highlight(section_input, lexer, formatter)
                        else:
                            raise
                    self.output_data[section_name] = section_output
                self.output_data.save()


########NEW FILE########
__FILENAME__ = pyn
from dexy.filter import DexyFilter

try:
    import pynliner
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

class PynlinerFilter(DexyFilter):
    """
    Filter which exposes pynliner for inlining CSS styles into HTML.
    """
    aliases = ['pyn', 'pynliner']

    def is_active(self):
        return AVAILABLE

    def process_text(self, input_text):
        return pynliner.fromString(input_text)

########NEW FILE########
__FILENAME__ = pytest
from dexy.filters.pydoc import PythonIntrospection
import StringIO
import dexy.exceptions
import inspect
import os

try:
    import nose
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

class PythonTest(PythonIntrospection):
    """
    Runs the tests in the specified Python modules.

    Python modules must be installed on the system. Returns a key-value store
    with test results and source code.
    
    Many packages are installed without tests, so this won't work.
    """
    aliases = ['pytest']
    _settings = {
            'run-tests' : (
                "Whether to run tests or just return test source code.",
                True
                ),
            'test-passed-when-not-run' : (
                "Value which should be used for test_passed when tests are not run.",
                True
                ),
            'load-tests-mode' : (
                "'dir' to find tests by location relative to package dir, 'name' if tests are in their own module.",
                'dir'),
            'path-to-tests-dir' : (
                "Path from package dir to tests dir.",
                "../tests"),
            'chdir' : (
                "Path from package dir to chdir to.",
                None),
            'nose-argv' : (
                "Need to fake out argv since sys.argv will be args for dexy, not nose.",
                ['nosetests', '--stop', '--verbose'])
            }

    def is_active(self):
        return AVAILABLE

    def load_tests_from_dir(self, module_name):
        self.log_debug("Loading module '%s' to find its tests." % module_name)
        mod = self.load_module(module_name)

        self.mod_file_dir = os.path.dirname(mod.__file__)
        relpath = self.setting('path-to-tests-dir')
        tests_dir = os.path.normpath(os.path.join(self.mod_file_dir, relpath))
        self.log_debug("Attempting to load tests from dir '%s'" % tests_dir)

        loader = nose.loader.TestLoader()
        return loader.loadTestsFromDir(tests_dir)

    def load_tests_from_name(self, module_name):
        loader = nose.loader.TestLoader()
        return loader.loadTestsFromName(module_name)

    def load_tests(self, module_name):
        mode = self.setting('load-tests-mode')
        if mode == 'dir':
            return self.load_tests_from_dir(module_name)
        elif mode == 'name':
            return self.load_tests_from_name(module_name)
        else:
            msg = "Invalid load-tests-mode setting '%s'" % mode
            raise dexy.exceptions.UserFeedback(msg)

    def append_source(self, test, test_passed):
        for key in dir(test.context):
            member = test.context.__dict__[key]

            if inspect.ismethod(member) or inspect.isfunction(member):
                qualified_test_name = "%s.%s" % (test.context.__name__, member.__name__)
                source = inspect.getsource(member.__code__)

                if member.func_doc:
                    doc = inspect.cleandoc(member.func_doc)
                    self.output_data.append("%s:doc" % qualified_test_name, doc)

                comments = inspect.getcomments(member.__code__)

                self.output_data.append("%s:source" % qualified_test_name, source)
                self.output_data.append("%s:name" % qualified_test_name, member.func_name)
                self.output_data.append("%s:comments" % qualified_test_name, comments)
                self.output_data.append("%s:passed" % qualified_test_name, unicode(test_passed))

    def run_test(self, test):
        # TODO This isn't working... maybe because we're running this in a test
        noselogs = StringIO.StringIO()
        config = nose.config.Config(
                logStream = noselogs
                )

        if self.setting('run-tests'):
            self.log_debug("Running test suite %s" % test)
            test_passed = nose.core.run(
                    suite=test,
                    config=config,
                    argv=self.setting('nose-argv')
                    )
            self.log_debug("Passed: %s" % test_passed)
        else:
            test_passed = self.setting('test-passed-when-not-run')

        return test_passed

    def process(self):
        module_names = unicode(self.input_data).split()
        self.mod_file_dir = None
        orig_wd = os.path.abspath(".")
        chdir = self.setting('chdir')

        for module_name in module_names:
            tests = self.load_tests(module_name)

            if chdir:
                chdir = os.path.abspath(os.path.join(self.mod_file_dir, chdir))
                self.log_warn("Changing dir to %s for tests" % chdir)
                os.chdir(chdir)

            for test in tests:
                test_passed = self.run_test(test)
                self.append_source(test, test_passed)

            if chdir:
                self.log_warn("Changing dir back to %s" % orig_wd)
                os.chdir(orig_wd)

        self.output_data.save()

########NEW FILE########
__FILENAME__ = rst
from dexy.filter import DexyFilter
from docutils import core
from docutils.frontend import OptionParser
from docutils.parsers.rst import Parser
from docutils.transforms import Transformer, frontmatter
from docutils.utils import new_document
import StringIO
import dexy.exceptions
import docutils.writers
import os

def default_template(writer_name):
    """
    Set the default template correctly, in case there has been a change in working dir.
    """
    writer_class = docutils.writers.get_writer_class(writer_name)

    if os.path.isdir(writer_class.default_template_path):
        return os.path.abspath(os.path.join(writer_class.default_template_path, writer_class.default_template))
    else:
        return os.path.abspath(writer_class.default_template_path)

class RestructuredTextBase(DexyFilter):
    """ Base class for ReST filters using the docutils library.
    """
    aliases = []

    _settings = {
            "input-extensions" : [".rst", ".txt"],
            'output-extensions' : [".html", ".tex", ".xml", ".odt"],
            'output' : True,
            'writer' : ("Specify rst writer to use (not required: dexy will attempt to determine automatically from filename if not specified).", None),
            'stylesheet' : ("Stylesheet arg to pass to rst", None),
            'template' : ("Template arg to pass to rst", None),
            }

    def docutils_writer_name(self):
        if self.setting('writer'):
            return self.setting('writer')
        elif self.ext == ".html":
            return 'html'
        elif self.ext == ".tex":
            return 'latex2e'
        elif self.ext == ".xml":
            return 'docutils_xml'
        elif self.ext == ".odt":
            return 'odf_odt'
        else:
            raise Exception("unsupported extension %s" % self.ext)

class RestructuredText(RestructuredTextBase):
    """
    A 'native' ReST filter which uses the docutils library.

    Look for configuration options for writers here:
    http://docutils.sourceforge.net/docs/user/config.html
    """
    aliases = ['rst']
    skip_settings = 'settings-not-for-settings-overrides'
    _settings = {
            'allow-any-template-extension' : ("Whether to NOT raise an error if template extension does not match document extension.", False),
            skip_settings : (
                "Which of the settings should NOT be passed to settings_overrides.",
                ['writer']
                )
            }

    def process(self):
        def skip_setting(key):
            in_base_filter = key in DexyFilter._settings
            in_skip = key in self.setting(self.skip_settings) or key == self.skip_settings
            return in_base_filter or in_skip

        settings_overrides = dict((k.replace("-", "_"), v) for k, v in self.setting_values().iteritems() if v and not skip_setting(k))
        writer_name = self.docutils_writer_name()

        warning_stream = StringIO.StringIO()
        settings_overrides['warning_stream'] = warning_stream

        self.log_debug("settings for rst: %r" % settings_overrides)
        self.log_debug("rst writer: %s" % writer_name)

        # Check that template extension matches output.
        if 'template' in settings_overrides and not self.setting('allow-any-template-extension'):
            template = settings_overrides['template']
            template_ext = os.path.splitext(template)[1]
            if not template_ext == self.ext:
                msg = "You requested template '%s' with extension '%s' for %s, does not match document extension of '%s'"
                args = (template, template_ext, self.key, self.ext)
                raise dexy.exceptions.UserFeedback(msg % args)

        if not 'template' in settings_overrides:
            if hasattr(writer_name, 'default_template'):
                settings_overrides['template'] = default_template(writer_name)

        try:
            core.publish_file(
                    source_path = self.input_data.storage.data_file(),
                    destination_path = self.output_data.storage.data_file(),
                    writer_name=writer_name,
                    settings_overrides=settings_overrides
                    )
        except ValueError as e:
            if "Invalid placeholder in string" in e.message and 'template' in settings_overrides:
                self.log_warn("you are using template '%s'. is this correct?" % settings_overrides['template'])
            raise
        except Exception as e:
            self.log_warn("An error occurred while generating reStructuredText.")
            self.log_warn("source file %s" % (self.input_data.storage.data_file()))
            self.log_warn("settings for rst: %r" % settings_overrides)
            self.log_warn("rst writer: %s" % writer_name)
            raise

        self.log_debug("docutils warnings:\n%s\n" % warning_stream.getvalue())

class RstBody(RestructuredTextBase):
    """
    Returns just the body part of an ReST document.
    """
    aliases = ['rstbody']
    _settings = {
            'set-title' : ("Whether to set document title.", True),
            'output-extensions' : ['.html', '.tex']
            }

    def process_text(self, input_text):
        warning_stream = StringIO.StringIO()
        settings_overrides = {}
        settings_overrides['warning_stream'] = warning_stream

        writer_name = self.docutils_writer_name()
        self.log_debug("about to call publish_parts with writer '%s'" % writer_name)

        if not 'template' in settings_overrides:
            settings_overrides['template'] = default_template(writer_name)

        try:
            parts = core.publish_parts(
                input_text,
                writer_name=writer_name,
                settings_overrides=settings_overrides
                )
        except AttributeError as e:
            raise dexy.exceptions.InternalDexyProblem(unicode(e))

        if self.setting('set-title') and parts.has_key('title') and parts['title']:
            self.update_all_args({'title' : parts['title']})

        self.log_debug("docutils warnings:\n%s\n" % warning_stream.getvalue())

        return parts['body']

class RstMeta(RestructuredTextBase):
    """
    Extracts bibliographical metadata and makes this available to dexy.
    """
    aliases = ['rstmeta']
    _settings = {
            'output-extensions' : [".rst"]
            }

    def process_text(self, input_text):
        warning_stream = StringIO.StringIO()
        settings_overrides = {}
        settings_overrides['warning_stream'] = warning_stream

        # Parse the input text using default settings
        settings = OptionParser(components=(Parser,)).get_default_values()
        parser = Parser()
        document = new_document('rstinfo', settings)
        parser.parse(input_text, document)

        # Transform the parse tree so that the bibliographic data is
        # is promoted from a mere field list to a `docinfo` node
        t = Transformer(document)
        t.add_transforms([frontmatter.DocTitle, frontmatter.DocInfo])
        t.apply_transforms()

        info = {}

        # Process individual nodes which are not part of docinfo.
        single_nodes = [
                docutils.nodes.title,
                docutils.nodes.subtitle,
                ]
        for node in single_nodes:
            for doc in document.traverse(node):
                if not len(doc.children) == 1:
                    msg = "Expected node %s to only have 1 child."
                    raise dexy.exceptions.InternalDexyProblem(msg % node)
                info[doc.tagname] = doc.children[0].astext()

        # Find the `docinfo` node and extract its children. Non-standard
        # bibliographic fields will have the `tagname` 'field' and two
        # children, the name and the value.  Standard fields simply keep
        # the name as the `tagname`.
        for doc in document.traverse(docutils.nodes.docinfo):
            for element in doc.children:
                if element.tagname == 'field':
                    name, value = element.children
                    name, value = name.astext(), value.astext()
                else:
                    name, value = element.tagname, element.astext()
                info[name] = value

        self.log_debug("found info:\n%s\n" % info)
        self.update_all_args(info)
        self.log_debug("docutils warnings:\n%s\n" % warning_stream.getvalue())

        return input_text

class RstDocParts(DexyFilter):
    """
    Returns key-value storage of document parts.
    """
    aliases = ['rstdocparts']
    _settings = {
            'input-extensions' : [".rst", ".txt"],
            'data-type' : 'keyvalue',
            'output-extensions' : ['.sqlite3', '.json'],
            'writer' : ("Specify rst writer to use.", 'html')
            }

    def process(self):
        input_text = unicode(self.input_data)

        warning_stream = StringIO.StringIO()
        settings_overrides = {}
        settings_overrides['warning_stream'] = warning_stream

        writer_name = self.setting('writer')

        if not 'template' in settings_overrides:
            settings_overrides['template'] = default_template(writer_name)

        parts = core.publish_parts(
                input_text,
                writer_name=writer_name,
                settings_overrides=settings_overrides
                )

        self.log_debug("docutils warnings:\n%s\n" % warning_stream.getvalue())

        for k, v in parts.iteritems():
            self.output_data.append(k, v)
        self.output_data.save()

########NEW FILE########
__FILENAME__ = sanitize
from dexy.filter import DexyFilter

try:
    import bleach
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

class Bleach(DexyFilter):
    """
    Runs the Bleach HTML sanitizer. <https://github.com/jsocol/bleach>
    """
    aliases = ['bleach']

    _settings = {
            'added-in-version' : '0.9.9.6',
            'input-extensions' : ['.html', '.txt'],
            'output-extensions' : ['.html', '.txt']
            }

    def is_active(self):
        return AVAILABLE

    # TODO implement support for sections
    def process_text(self, input_text):
        return bleach.clean(input_text)

########NEW FILE########
__FILENAME__ = soup
from bs4 import BeautifulSoup
from dexy.filter import DexyFilter
import inflection
import re

class Customize(DexyFilter):
    """
    Add <script> tags or <link> tags to an HTML file's header.
    
    Uses BeautifulSoup.
    """
    aliases = ['customize']

    _settings = {
            'scripts' : ("Javascript files to add.", []),
            'stylesheets' : ("CSS files to add.", [])
            }

    def process_text(self, input_text):
        soup = BeautifulSoup(input_text)

        for js in self.setting('scripts'):
            js_tag = soup.new_tag("script", type="text/javascript", src=js)
            soup.head.append(js_tag)

        for css in self.setting('stylesheets'):
            css_tag = soup.new_tag("link", rel="stylesheet", type="text/css", href=css)
            soup.head.append(css_tag)

        return unicode(soup)

class SoupSections(DexyFilter):
    """
    Split a HTML file into nested sections based on header tags.
    """
    aliases = ['soups']

    _settings = {
            'data-type' : 'sectioned',
            'html-parser' : ("Name of html parser BeautifulSoup should use.", 'html.parser'),
            'initial-section-name' : ("Name to use for the initial section which currently holds all the contents.", u"Actual Document Contents"),
            }

    def append_current_section(self):
        section_dict = {
                "name" : self.current_section_name,
                "contents" : self.current_section_text,
                "level" : self.current_section_level,
                "id" : self.current_section_anchor
                }
        self.output_data._data.append(section_dict)

    def process(self):
        soup = BeautifulSoup(unicode(self.input_data), self.setting('html-parser'))

        for tag in soup.find_all(re.compile("^h[0-6]")):
            name = tag.text
            m = re.match("^h([0-6])$", tag.name)

            if not tag.attrs.has_key('id'):
                tag.attrs['id'] = inflection.parameterize(name)

            self.current_section_anchor = tag.attrs['id']
            self.current_section_text = None
            self.current_section_name = name
            self.current_section_level = int(m.groups()[0])

            self.append_current_section()

        self.current_section_text = unicode(soup)
        self.current_section_name = self.setting('initial-section-name')
        self.current_section_level = 1
        self.current_section_anchor = None

        self.append_current_section()

        self.output_data.save()

########NEW FILE########
__FILENAME__ = split
from dexy.filter import DexyFilter
import os
import re

class SplitHtmlFilter(DexyFilter):
    """
    Generate index page linking to multiple pages from single source.

    The split filter looks for specially formatted HTML comments in your
    document and splits your HTML into separate pages at each split comment.
    """
    aliases = ['split', 'splithtml']
    _settings = {
            'output' : True,
            'input-extensions' : ['.html'],
            'output-extensions' : ['.html'],
            'split-ul-class' : ("HTML class to apply to <ul> elements", None)
            }

    def process(self):
        input_text = unicode(self.input_data)

        if input_text.find("<!-- endsplit -->") > 0:
            rawbody, footer = re.split("<!-- endsplit -->", input_text, maxsplit=1)
           
            if rawbody.find("<!-- footer -->") > 0:
                body, index_footer_content = re.split("<!-- footer -->", rawbody, maxsplit=1) 
            else:
                body = rawbody
                index_footer_content = ""

            sections = re.split("<!-- split \"(.+)\" -->\n", body)
            header = sections[0]

            pages = {}
            index_top_content = ""
            for i in range(1, len(sections), 2):
                if sections[i] == 'index':
                    index_top_content = sections[i+1]
                else:
                    section_label = sections[i]
                    section_content = sections[i+1]

                    section_url = section_label.split(" ")[0]

                    if "<!-- content -->" in section_content:
                        section_description, section_content = section_content.split("<!-- content -->")
                    else:
                        section_description = ""

                    filename = "%s.html" % section_url

                    filepath = os.path.join(self.output_data.parent_dir(), filename)
                    pages[section_label] = (section_description, filename,)

                    new_page = self.add_doc(filepath, header + section_content + footer)
                    new_page.update_setting('title', re.sub("\s+\(.+\)\s*(<.*>\s*)*", "", section_label))

                    apply_ws_to_content = self.doc.safe_setting("apply-ws-to-content")
                    apply_ws_to_content_variable_start_string = self.doc.safe_setting("apply-ws-to-content-variable-start-string")
                    apply_ws_to_content_variable_end_string = self.doc.safe_setting("apply-ws-to-content-variable-end-string")
                    apply_ws_to_content_block_start_string = self.doc.safe_setting("apply-ws-to-content-block-start-string")
                    apply_ws_to_content_block_end_string = self.doc.safe_setting("apply-ws-to-content-block-end-string")

                    if apply_ws_to_content:
                        new_page.update_setting('apply-ws-to-content', apply_ws_to_content)
                    if apply_ws_to_content_variable_start_string:
                        new_page.update_setting('apply-ws-to-content-variable-start-string', apply_ws_to_content_variable_start_string)
                    if apply_ws_to_content_variable_end_string:
                        new_page.update_setting('apply-ws-to-content-variable-end-string', apply_ws_to_content_variable_end_string)
                    if apply_ws_to_content_block_start_string:
                        new_page.update_setting('apply-ws-to-content-block-start-string', apply_ws_to_content_block_start_string)
                    if apply_ws_to_content_block_end_string:
                        new_page.update_setting('apply-ws-to-content-block-end-string', apply_ws_to_content_block_end_string)

                    self.log_debug("added key %s to %s ; links to file %s" %
                              (filepath, self.key, new_page.name))

            index_items = ""
            for page_label in sorted(pages):
                page_description, filename = pages[page_label]
                index_items += """<li><a href="%s">%s</a></li>\n%s\n""" % (filename, page_label, page_description)

            output = header + index_top_content

            if self.setting("split-ul-class"):
                ul = "<ul class=\"%s\">" % self.setting('split-ul-class')
            else:
                ul = "<ul class=\"split\">"

            output += "%s\n%s\n</ul>" % (ul, index_items)
            output += index_footer_content + footer

        else:
            # No endsplit found, do nothing.
            output = input_text

        self.output_data.set_data(output)

########NEW FILE########
__FILENAME__ = standard
from dexy.filter import DexyFilter
from dexy.utils import indent
import copy
import dexy.exceptions
import json
import os
import re

class Resub(DexyFilter):
    """
    Runs re.sub on each line of input.
    """
    aliases = ['resub']
    _settings = {
            'expressions' : ("Tuples of (regexp, replacement) to apply.", []),
            }

    def process_text(self, input_text):
        for regexp, replacement in self.setting('expressions'):
            self.log_debug("Applying %s" % regexp)
            working_text = []

            for line in input_text.splitlines():
                working_text.append(re.sub(regexp, replacement, line))

            input_text = "\n".join(working_text)

        return input_text


class PreserveDataClassFilter(DexyFilter):
    """
    Sets PRESERVE_PRIOR_DATA_CLASS to True.
    """
    aliases = []
    _settings = {
            'preserve-prior-data-class' : True
            }

    def data_class_alias(self, ext):
        if self.setting('preserve-prior-data-class'):
            return self.input_data.alias
        else:
            return self.setting('data-type')

    def calculate_canonical_name(self):
        return self.prev_filter.calculate_canonical_name()

class ChangeExtensionManuallyFilter(PreserveDataClassFilter):
    """
    Dummy filter for allowing changing a file extension.
    """
    aliases = ['chext']

class KeyValueStoreFilter(DexyFilter):
    """
    Creates a new key-value store.

    The key-value store will be populated via side effects from other filters.
    """
    aliases = ['kv']
    _settings = {
            'data-type' : 'keyvalue'
            }

    def process(self):
        self.output_data.copy_from_file(self.input_data.storage.data_file())

        # Call setup() again since it will have created a new blank database.
        self.output_data.storage.setup()
        self.output_data.storage.connect()

class HeaderFilter(DexyFilter):
    """
    Apply another file to top of file.
    """
    aliases = ['hd']
    _settings = {
            'key-name' : ("Name of key to use.", 'header'),
            'header' : ("Document key of file to use as header.", None)
            }

    def find_input_in_parent_dir(self, matches):
        docs = list(self.doc.walk_input_docs())
        docs_d = dict((task.output_data().long_name(), task) for task in docs)

        key_name = self.setting('key-name')
        requested = self.setting(key_name)
        if requested:
            if docs_d.has_key(requested):
                matched_key = requested
            else:
                msg = "Couldn't find the %s file %s you requested" % (self.setting(key_name), requested)
                raise dexy.exceptions.UserFeedback(msg)
        else:
            matched_key = None
            for k in sorted(docs_d.keys()):
                if (os.path.dirname(k) in self.output_data.parent_dir()) and (matches in k):
                    matched_key = k

        if not matched_key:
            msg = "no %s input found for %s" 
            msgargs = (self.setting('key-name'), self.key)
            raise dexy.exceptions.UserFeedback(msg % msgargs)

        return docs_d[matched_key].output_data()

    def process_text(self, input_text):
        header_data = self.find_input_in_parent_dir("_header")
        return "%s\n%s" % (unicode(header_data), input_text)

class FooterFilter(HeaderFilter):
    """
    Apply another file to bottom of file.
    """
    aliases = ['ft']
    _settings = {
            'key-name' : 'footer',
            'footer' : ("Document key of file to use as footer.", None)
            }

    def process_text(self, input_text):
        footer_data = self.find_input_in_parent_dir("_footer")
        return "%s\n%s" % (input_text, unicode(footer_data))

class TemplateContentFilter(HeaderFilter):
    """
    Apply template to file. Template should specify %(content)s.
    """
    aliases = ['applytemplate']
    _settings = {
            'key-name' : 'template',
            'template' : ("Document key of file to use as footer.", None)
            }

    def process_text(self, input_text):
        template_data = self.find_input_in_parent_dir("_template")
        return unicode(template_data) % { 'content' : input_text }

class MarkupTagsFilter(DexyFilter):
    """
    Wrap text in specified HTML tags.
    """
    aliases = ['tags']
    _settings = {
            'tags' : ("Tags.", {})
            }

    def process_text(self, input_text):
        tags = copy.copy(self.setting('tags'))
        open_tags = "".join("<%s>" % t for t in tags)
        tags.reverse()
        close_tags = "".join("</%s>" % t for t in tags)

        return "%s\n%s\n%s" % (open_tags, input_text, close_tags)

class StartSpaceFilter(DexyFilter):
    """
    Add a blank space to the start of each line.

    Useful for passing syntax highlighted/preformatted code to mediawiki.
    """
    aliases = ['ss', 'startspace']
    _settings = {
            'n' : ("Number of spaces to prepend to each line.", 1),
            'data-type' : 'sectioned'
            }

    def process(self):
        n = self.setting('n')
        for section_name, section_input in self.input_data.iteritems():
            self.output_data[section_name] = indent(section_input, n)
        self.output_data.save()

class SectionsByLine(DexyFilter):
    """
    Returns each line in its own section.
    """
    aliases = ['lines']
    _settings = {
            'data-type' : 'sectioned'
            }

    def process(self):
        input_text = unicode(self.input_data)
        for i, line in enumerate(input_text.splitlines()):
            self.output_data["%s" % (i+1)] = line
        self.output_data.save()

class ClojureWhitespaceFilter(DexyFilter):
    """
    Parse clojure code into sections based on whitespace and try to guess a
    useful name for each section by looking for def, defn, deftest or a
    comment.
    """
    aliases = ['cljws']
    _settings = {
            'added-in-version' : '1.0.1',
            'data-type' : 'sectioned',
            'name-regex' : (
                """List of regular expressions including a match group
                representing the name of the section. Will be tried in
                order.""",
                [
                    "\(def ([a-z\-\?]+)",
                    "\(defn ([a-z\-\?]+)",
                    "\(defn= ([a-z\-\?]+)",
                    "\(deftest ([a-z\-\?]+)",
                ])
            }

    def process(self):
        input_text = unicode(self.input_data)
        for i, section in enumerate(input_text.split("\n\n")):
            section_name = self.parse_section_name(section)
            if section_name:
                self.output_data[section_name] = section
            else:
                self.output_data["%s" % (i+1)] = section

        self.output_data.save()

    def parse_section_name(self, section_text):
        """
        Parse a section name out of the section text.
        """
        if not section_text:
            return

        for line in section_text.splitlines():
            firstline = line
            if not line.strip().startswith(';'):
                break

        for regex in self.setting('name-regex'):
            m = re.match(regex, firstline)
            if m:
                return m.groups()[0]

class PrettyPrintJsonFilter(DexyFilter):
    """
    Pretty prints JSON input.
    """
    aliases = ['ppjson']
    _settings = {
            'output-extensions' : ['.json']
            }

    def process_text(self, input_text):
        json_content = json.loads(input_text)
        return json.dumps(json_content, sort_keys=True, indent=4)

class JoinFilter(DexyFilter):
    """
    Takes sectioned code and joins it into a single section. Some filters which
    don't preserve sections will raise an error if they receive multiple
    sections as input, so this forces acknowledgement that sections will be
    lost.
    """
    aliases = ['join']

    def process(self):
        joined_data = "\n".join(unicode(v) for v in self.input_data.values())
        print "joined data is", joined_data
        self.output_data.set_data(joined_data)

class HeadFilter(DexyFilter):
    """
    Returns just the first 10 lines of input.
    """
    aliases = ['head']

    def process_text(self, input_text):
        return "\n".join(input_text.split("\n")[0:10]) + "\n"

class WordWrapFilter(DexyFilter):
    """
    Wraps text after 79 characters (tries to preserve existing line breaks and
    spaces).
    """
    aliases = ['ww', 'wrap']
    _settings = {
            'width' : ("Width of text to wrap to.", 79)
            }

    #http://code.activestate.com/recipes/148061-one-liner-word-wrap-function/
    def wrap_text(self, text, width):
        """
        A word-wrap function that preserves existing line breaks
        and most spaces in the text. Expects that existing line
        breaks are posix newlines (\n).
        """
        return reduce(lambda line, word, width=width: '%s%s%s' %
                 (line,
                   ' \n'[(len(line)-line.rfind('\n')-1
                         + len(word.split('\n',1)[0]
                              ) >= width)],
                   word),
                  text.split(' ')
                 )

    def process_text(self, input_text):
        return self.wrap_text(input_text, self.setting('width'))

########NEW FILE########
__FILENAME__ = sub
from dexy.filters.process import SubprocessExtToFormatFilter
from dexy.filters.process import SubprocessFilter
from dexy.filters.process import SubprocessFormatFlagFilter
from dexy.filters.process import SubprocessInputFilter
from dexy.filters.process import SubprocessStdoutFilter
from dexy.utils import file_exists
import dexy.exceptions
import json
import os
import shutil

class Kramdown(SubprocessStdoutFilter):
    """
    Runs the kramdown markdown converter.

    http://kramdown.gettalong.org/
    """
    aliases = ['kramdown']
    _settings = {
            'added-in-version' : "1.0.5",
            'class' : 'SubprocessExtToFormatFilter',
            'executable' : 'kramdown',
            'version-command' : 'kramdown -version',
            'output' : True,
            'format-specifier' : '-o ',
            'ext-to-format' : {'.tex' : 'latex', '.html' : 'html', '.md' : 'kramdown', '.txt' : 'kramdown'},
            'input-extensions' : [".*"],
            'output-extensions' : [".html", ".tex", ".txt", ".md"],
            'require-output' : True,
            'command-string' : '%(prog)s %(format)s %(args)s "%(script_file)s"'
            }

    def command_string_args(self):
        args = self.default_command_string_args()

        fmt_specifier = self.setting('format-specifier')
        if fmt_specifier and (fmt_specifier in args['args']):
            # Already have specified the format manually.
            fmt = ''
        else:
            fmt_setting = self.setting('ext-to-format')[self.ext]
            if fmt_setting:
                fmt = "%s%s" % (fmt_specifier, fmt_setting)
            else:
                fmt = ''

        args['format'] = fmt
        return args

class Redcarpet(SubprocessStdoutFilter):
    """
    Converts github-flavored markdown to HTML using redcarpet.
    """
    aliases = ['redcarpet', 'ghmd']
    _settings = {
            'added-in-version' : '1.0.1',
            'executable' : 'redcarpet',
            'input-extensions' : [".md", ".txt"],
            'output-extensions' : [".html"],
            # parse options
            'parse-autolink' : ("autolink option from redcarpet", True),
            'parse-disabled-indented-code-blocks' : ("disabled-indented-code-blocks option from redcarpet", False),
            'parse-fenced-code-blocks' : ("fenced-code-blocks option from redcarpet", True),
            'parse-highlight' : ("highlight option from redcarpet", True),
            'parse-lax-spacing' : ("lax-spacing option from redcarpet", True),
            'parse-no-intra-emphasis' : ("no-intra-emphasis option from redcarpet", True),
            'parse-quotes' : ("quotes option from redcarpet", True),
            'parse-space-after-headers' : ("space-after-headers option from redcarpet", True),
            'parse-strikethrough' : ("strikethrough option from redcarpet", True),
            'parse-subscript' : ("subscript option from redcarpet", True),
            'parse-superscript' : ("superscript option from redcarpet", True),
            'parse-tables' : ("tables option from redcarpet", True),
            'parse-underline' : ("underline option from redcarpet", True),
            # render options
            'render-filter-html' : ("filter-html option from redcarpet", False),
            'render-no-images' : ("no-images option from redcarpet", False),
            'render-no-links' : ("no-links option from redcarpet", False),
            'render-no-styles' : ("no-styles option from redcarpet", False),
            'render-safe-links-only' : ("safe-links-only option from redcarpet", False),
            'render-with-toc-data' : ("with-toc-data option from redcarpet", False),
            'render-hard-wrap' : ("hard-wrap option from redcarpet", False),
            'render-prettify' : ("prettify option from redcarpet", False),
            'render-xhtml' : ("xhtml option from redcarpet", False),
            # other options
            'pygments' : ("Pygments syntax highlighting (requires ananelson/redcarpet fork).", False)
            }
  
    def command_string(self):
        args = self.command_string_args()

        args['parse_args'] = " ".join("--%s" % name for name in args if name.startswith("parse-") and args[name])
        args['render_args'] = " ".join("--%s" % name for name in args if name.startswith("render-") and args[name])

        other_args = ['pygments']
        args['other_args'] = " ".join("--%s" % name for name in other_args if args[name])

        return "%(prog)s %(parse_args)s %(render_args)s %(other_args)s %(script_file)s" % args

class TidyCheck(SubprocessFilter):
    """
    Runs `tidy` to check for valid HTML.

    This filter does not alter valid HTML. It raises an Exception if invalid
    HTML is found.
    """
    aliases = ['tidycheck']
    _settings = {
        'examples' : ['tidy'],
        'tags' : ['html'],
        'executable' : 'tidy',
        'command-string' : '%(prog)s -errors -quiet "%(script_file)s"',
        'input-extensions' : ['.html'],
        'output-extensions' : ['.txt']
        }

    def process(self):
        command = self.command_string()
        proc, stdout = self.run_command(command, self.setup_env())
        self.handle_subprocess_proc_return(command, proc.returncode, stdout)

        # If we get here, just return original input.
        self.output_data.copy_from_file(self.input_data.storage.data_file())

class PdfToCairo(SubprocessFormatFlagFilter):
    """
    Runs `pdftocairo` from the poppler library.

    Converts PDF input to various output formats inclusing SVG.
    """
    aliases = ['pdftocairo', 'pdf2cairo', 'pdf2svg', 'pdftosvg']
    _settings = {
        'command-string': '%(prog)s %(format)s %(args)s "%(script_file)s" "%(output_file)s"',
        'executable': 'pdftocairo',
        'tags' : ['pdf', 'image'],
        'input-extensions' : ['.pdf'],
        'output-extensions' : ['.svg', '.png', '.jpg', '.ps', '.eps', '.pdf'],
        'ext-to-format' : {
            '.png' : '-png',
            '.jpg' : '-jpeg',
            '.ps' : '-ps',
            '.eps' : '-eps',
            '.pdf' : '-pdf',
            '.svg' : '-svg'
            }
        }

    def process(self):
        command = self.command_string()
        proc, stdout = self.run_command(command, self.setup_env())
        self.handle_subprocess_proc_return(command, proc.returncode, stdout)

        if not self.output_data.is_cached():
            # Find the first page
            for pagenum in ('1', '01', '001', '0001',):
                basename = os.path.join(self.workspace(), self.output_data.name)
                first_page_file = "%s-%s.png" % (basename, pagenum)
                if file_exists(first_page_file):
                    print "Copy from '%s'" % first_page_file
                    self.output_data.copy_from_file(first_page_file)
                    break

        assert self.output_data.is_cached()

        if self.setting('add-new-files'):
            self.log_debug("adding new files found in %s for %s" % (self.workspace(), self.key))
            self.add_new_files()

class Pdf2ImgSubprocessFilter(SubprocessExtToFormatFilter):
    """
    Runs ghostscript to convert PDF files to images.

    An image file can only hold a single page of PDF, so this defaults to
    returning page 1. The `page` setting can be used to specify other pages.
    """
    aliases = ['pdf2img', 'pdftoimg', 'pdf2png']
    _settings = {
            'res' : ("Resolution of image.", 300),
            'page' : ("Which page of the PDF to return as an image", 1),
            'executable' : 'gs',
            'version-command' : 'gs --version',
            'tags' : ['pdf', 'gs'],
            'input-extensions' : ['.pdf'],
            'output-extensions' : ['.png'],
            'ext-to-format' : {
                '.png' : 'png16m',
                '.jpg' : 'jpeg'
                },
            'format-specifier' : '-sDEVICE=',
            'command-string' : '%(prog)s -dSAFER -dNOPAUSE -dBATCH %(format)s -r%(res)s -sOutputFile="%%d-%(output_file)s" "%(script_file)s"'
            }

    def process(self):
        self.populate_workspace()

        command = self.command_string()
        proc, stdout = self.run_command(command, self.setup_env())
        self.handle_subprocess_proc_return(command, proc.returncode, stdout)

        page = self.setting('page')
        page_file = "%s-%s" % (page, self.output_data.basename())

        wd = self.parent_work_dir()
        page_path = os.path.join(wd, page_file)
        shutil.copyfile(page_path, self.output_filepath())

class RIntBatchSectionsFilter(SubprocessFilter):
    """
    Experimental filter to run R in sections without using pexpect.
    """
    aliases = ['rintmock']

    _settings = {
            'add-new-files' : True,
            'executable' : 'R CMD BATCH --quiet --no-timing',
            'tags' : ['rstats', 'repl', 'stats'],
            'input-extensions' : ['.txt', '.r', '.R'],
            'output-extensions' : [".Rout", '.txt'],
            'version-command' : "R --version",
            'write-stderr-to-stdout' : False,
            'data-type' : 'sectioned',
            'command-string' : """%(prog)s %(args)s "%(script_file)s" %(scriptargs)s "%(output_file)s" """
            }

    def command_string(self, section_name, section_text, wd):
        br = self.input_data.baserootname()

        args = self.default_command_string_args()
        args['script_file'] = "%s-%s%s" % (br, section_name, self.input_data.ext)
        args['output_file'] = "%s-%s-out%s" % (br, section_name, self.output_data.ext)

        work_filepath = os.path.join(wd, args['script_file'])

        with open(work_filepath, "wb") as f:
            f.write(unicode(section_text))

        command = self.setting('command-string') %  args
        return command, args['output_file']

    def process(self):
        self.populate_workspace()
        wd = self.parent_work_dir()

        for section_name, section_text in self.input_data.iteritems():
            command, outfile = self.command_string(section_name, section_text, wd)
            proc, stdout = self.run_command(command, self.setup_env())
            self.handle_subprocess_proc_return(command, proc.returncode, stdout)

            with open(os.path.join(wd, outfile), "rb") as f:
                self.output_data[section_name] = f.read()

        if self.setting('add-new-files'):
            self.add_new_files()

        self.output_data.save()

class EmbedFonts(SubprocessFilter):
    """
    Runs ghostscript ps2pdf with prepress settings.

    Allegedly this helps embed fonts and makes documents friendly for printing.
    """
    aliases = ['embedfonts', 'prepress']
    _settings = {
            'input-extensions' : [".pdf"],
            'output-extensions' : [".pdf"],
            'executable' : 'ps2pdf',
            'tags' : ['pdf'],
            }

    def preprocess_command_string(self):
        pf = self.work_input_filename()
        af = self.work_output_filename()
        return "%s -dPDFSETTINGS=/prepress %s %s" % (self.setting('executable'), pf, af)

    def pdffonts_command_string(self):
        return "%s %s" % ("pdffonts", self.result().name)

    def process(self):
        env = self.setup_env()

        command = self.preprocess_command_string()
        proc, stdout = self.run_command(command, env)
        self.handle_subprocess_proc_return(command, proc.returncode, stdout)

        command = self.pdffonts_command_string()
        proc, stdout = self.run_command(command, env)
        self.handle_subprocess_proc_return(command, proc.returncode, stdout)

        self.copy_canonical_file()

class AbcFilter(SubprocessFormatFlagFilter):
    """
    Runs `abcm2ps` on .abc music files.
    """
    aliases = ['abc']
    _settings = {
            'command-string' : '%(prog)s %(args)s %(format)s -O %(output_file)s %(script_file)s',
            'add-new-files' : False,
            'output' : True,
            'tags' : ['music'],
            'examples' : ['abc'],
            'executable' : 'abcm2ps',
            'input-extensions' : ['.abc'],
            'output-extensions': ['.svg', '.html', '.xhtml', '.eps'],
            'ext-to-format': {
                '.eps' : '-E',
                '.svg' : '-g',
                '.svg1' : '-v', # dummy entry so we know -v is a format flag
                '.html' : '-X',
                '.xhtml' : '-X'
                }
            }

    def process(self):
        command = self.command_string()
        proc, stdout = self.run_command(command, self.setup_env())
        self.handle_subprocess_proc_return(command, proc.returncode, stdout)

        if self.ext in ('.svg', '.eps'):
            # Fix for abcm2ps adding 001 to file name.
            nameparts = os.path.splitext(self.output_data.name)
            output_filename = "%s001%s" % (nameparts[0], nameparts[1])
            output_filepath = os.path.join(self.workspace(), output_filename)
            self.output_data.copy_from_file(output_filepath)
        else:
            self.copy_canonical_file()

        if self.setting('add-new-files'):
            self.add_new_files()

class AbcMultipleFormatsFilter(SubprocessFilter):
    """
    Runs `abcm2ps` on .abc music files, generating all output formats.
    """
    aliases = ['abcm']
    _settings = {
            'input-extensions' : ['.abc'],
            'output-extensions' : ['.json'],
            'executable' : 'abcm2ps',
            'tags' : ['music'],
            'add-new-files' : False
            }

    def command_string(self, ext):
        clargs = self.command_line_args() or ''

        if any(x in clargs for x in ['-E', '-g', '-v', '-X']):
            raise dexy.exceptions.UserFeedback("Please do not pass any output format flags!")

        if ext in ('.eps'):
            output_flag = '-E'
        elif ext in ('.svg'):
            output_flag = '-g'
        elif ext in ('.html', '.xhtml'):
            output_flag = '-X'
        else:
            raise dexy.exceptions.InternalDexyProblem("bad ext '%s'" % ext)

        args = {
            'prog' : self.setting('executable'),
            'args' : clargs,
            'output_flag' : output_flag,
            'script_file' : self.work_input_filename(),
            'output_file' : self.output_workfile(ext)
        }
        return "%(prog)s %(args)s %(output_flag)s -O %(output_file)s %(script_file)s" % args

    def output_workfile(self, ext):
        return "%s%s" % (self.output_data.baserootname(), ext)

    def process(self):
        output = {}

        wd = self.parent_work_dir()

        for ext in ('.eps', '.svg', '.html', '.xhtml'):
            command = self.command_string(ext)
            proc, stdout = self.run_command(command, self.setup_env())
            self.handle_subprocess_proc_return(command, proc.returncode, stdout)

            if ext in ('.svg', '.eps'):
                # Fix for abcm2ps adding 001 to file name.
                nameparts = os.path.splitext(self.output_workfile(ext))
                output_filename = "%s001%s" % (nameparts[0], nameparts[1])
                output_filepath = os.path.join(wd, output_filename)
            else:
                output_filename = self.output_workfile(ext)
                output_filepath = os.path.join(wd, output_filename)

            with open(output_filepath, "r") as f:
                output[ext] = f.read()

        self.output_data.set_data(json.dumps(output))

class ManPage(SubprocessStdoutFilter):
    """
    Read command names from a file and fetch man pages for each.

    Returns a JSON dict whose keys are the program names and values are man
    pages.
    """
    aliases = ['man']

    _settings = {
            'executable' : 'man',
            'tags' : ['utils'],
            'version-command' : 'man --version',
            'input-extensions' : [".txt"],
            'output-extensions' : [".json"]
    }

    def command_string(self, prog_name):
        # Use bash rather than the default of sh (dash) so we can set pipefail.
        return "bash -c \"set -e; set -o pipefail; man %s | col -b | strings\"" % (prog_name)

    def process(self):
        man_info = {}
        for prog_name in unicode(self.input_data).split():
            command = self.command_string(prog_name)
            proc, stdout = self.run_command(command, self.setup_env())
            self.handle_subprocess_proc_return(command, proc.returncode, stdout)
            man_info[prog_name] = stdout

        self.output_data.set_data(json.dumps(man_info))

class ApplySed(SubprocessInputFilter):
    """
    Runs `sed` on the input file.

    Expects a sed script to be a dependency.
    """
    aliases = ['used']
    _settings = {
            'executable' : 'sed',
            'tags' : ['utils'],
            'data-type' : 'generic',
            }

    def process(self):
        for doc in self.doc.walk_input_docs():
            if doc.output_data().ext == ".sed":
                command = "%s -f %s" % (self.setting('executable'), doc.name)

        if not command:
            raise dexy.exceptions.UserFeedback("A .sed file must be passed as an input to %s" % self.key)

        proc, stdout = self.run_command(command, self.setup_env(), unicode(self.input_data))
        self.handle_subprocess_proc_return(command, proc.returncode, stdout)
        self.output_data.set_data(stdout)

class Sed(SubprocessInputFilter):
    """
    Runs a sed script.

    Any dependencies are assumed to be text files and they have the sed script
    applied to them.
    """
    aliases = ['sed']
    _settings = {
            'executable' : 'sed',
            'tags' : ['utils'],
            'input-extensions' : ['.sed'],
            'output-extensions' : ['.sed', '.txt'],
            }

    def command_string(self):
        return "%s -f %s" % (self.setting('executable'), self.work_input_filename())

class Taverna(SubprocessStdoutFilter):
    """
    Runs workflows in Taverna via command line tool.
    """
    aliases = ['taverna']
    _settings = {
            'executable' : 'taverna',
            'tags' : ['repro', 'workflow'],
            'add-new-files' : True,
            'input-extensions' : ['.t2flow'],
            'output-extensions' : ['.txt'],
            'taverna-home' : ("Location of taverna home directory.", "$TAVERNA_HOME"),
            'x-max' : ("Java -Xmx setting", '300m'),
            'x-perm-max' : ("Java -XX:MaxPermSize setting", '140m'),
            }

    def command_string(self):
        assert self.setting('taverna-home')

        return """java -Xmx%(x-max)s -XX:MaxPermSize=%(x-perm-max)s \\
                -Draven.profile=file://%(taverna-home)s/conf/current-profile.xml \\
                -Dtaverna.startup=%(taverna-home)s \\
                -Djava.system.class.loader=net.sf.taverna.raven.prelauncher.BootstrapClassLoader \\
                -Draven.launcher.app.main=net.sf.taverna.t2.commandline.CommandLineLauncher \\
                -Draven.launcher.show_splashscreen=false \\
                -Djava.awt.headless=true \\
                -jar "%(taverna-home)s/lib/"prelauncher-*.jar \\
                %(script_file)s""" % self.command_string_args()

########NEW FILE########
__FILENAME__ = templating
from dexy.filter import DexyFilter
from dexy.plugin import TemplatePlugin
from jinja2 import FileSystemLoader
from jinja2.exceptions import TemplateNotFound
from jinja2.exceptions import TemplateSyntaxError
from jinja2.exceptions import UndefinedError
import dexy.exceptions
import jinja2
import os
import re
import traceback

class PassThroughWhitelistUndefined(jinja2.StrictUndefined):
    call_whitelist = ('link', 'section',)

    def wrap_arg(self, arg):
        if isinstance(arg, basestring):
            return "\"%s\"" % unicode(arg)
        else:
            return unicode(arg)

    def __call__(self, *args, **kwargs):
        name = self._undefined_name

        if name in self.call_whitelist:
            msgargs = {
                    'name' : name,
                    'argstring' : ",".join(self.wrap_arg(a) for a in args)
                    }
            return "{{ %(name)s(%(argstring)s) }}" % msgargs
        else:
            self._fail_with_undefined_error(*args, **kwargs)

class TemplateFilter(DexyFilter):
    """
    Base class for templating system filters such as JinjaFilter. Templating
    systems are used to make generated artifacts available within documents.

    Plugins are used to prepare content.
    """
    aliases = ['template']

    _settings = {
            'output' : True,
            'variables' : ("Variables to be made available to document.", {}),
            'vars' : ("Variables to be made available to document.", {}),
            'plugins' : ("List of plugins for run_plugins to use.", []),
            'skip-plugins' : ("List of plugins which run_plugins should not use.", [])
            }

    def template_plugins(self):
        """
        Returns a list of plugin classes for run_plugins to use.
        """
        if self.setting('plugins'):
            return [TemplatePlugin.create_instance(alias, self)
                        for alias in self.setting('plugins')]
        else:
            return [instance for instance in TemplatePlugin.__iter__(self)
                        if not instance.alias in self.setting('skip-plugins')]

    def run_plugins(self):
        env = {}
        for plugin in self.template_plugins():
            self.log_debug("Running template plugin %s" % plugin.__class__.__name__)
            new_env_vars = plugin.run()
            if new_env_vars is None:
                msg = "%s did not return any values"
                raise dexy.exceptions.InternalDexyProblem(msg % plugin.alias)
            if any(v in env.keys() for v in new_env_vars):
                new_keys = ", ".join(sorted(new_env_vars))
                existing_keys = ", ".join(sorted(env))
                msg = "plugin class '%s' is trying to add new keys '%s', already have '%s'"
                raise dexy.exceptions.InternalDexyProblem(msg % (plugin.__class__.__name__, new_keys, existing_keys))
            env.update(new_env_vars)

        return env

    def template_data(self):
        plugin_output = self.run_plugins()

        template_data = {}

        for k, v in plugin_output.iteritems():
            if not isinstance(v, tuple) or len(v) != 2:
                msg = "Template plugin '%s' must return a tuple of length 2." % k
                raise dexy.exceptions.InternalDexyProblem(msg)
            template_data[k] = v[1]

        return template_data

    def process_text(self, input_text):
        template_data = self.template_data()
        return input_text % template_data

class JinjaFilter(TemplateFilter):
    """
    Runs the Jinja templating engine.
    """
    aliases = ['jinja']

    _settings = {
            'block-start-string' : ("Tag to indicate the start of a block.", "{%"),
            'block-end-string' : ("Tag to indicate the start of a block.", "%}"),
            'variable-start-string' : ("Tag to indicate the start of a variable.", "{{"),
            'variable-end-string' : ("Tag to indicate the start of a variable.", "}}"),
            'comment-start-string' : ("Tag to indicate the start of a comment.", "{#"),
            'comment-end-string' : ("Tag to indicate the start of a comment.", "#}"),
            'changetags' : ("Automatically change from { to < based tags for .tex and .wiki files.", True),
            'jinja-path' : ("List of additional directories to pass to jinja loader.", []),
            'workspace-includes' : [".jinja"],
            'assertion-passed-indicator' : (
                "Extra text to return with a passed assertion.",
                ""),
            'filters' : (
                "List of template plugins to make into jinja filters.",
                ['assertions', 'highlight', 'head', 'tail', 'rstcode', 'stripjavadochtml',
                    'replacejinjafilters', 'bs4']
                )
            }

    _not_jinja_settings = (
            'changetags',
            'jinja-path',
            'workspace-includes',
            'filters',
            'assertion-passed-indicator'
            )

    TEX_TAGS = {
            'block_start_string': '<%',
            'block_end_string': '%>',
            'variable_start_string': '<<',
            'variable_end_string': '>>',
            'comment_start_string': '<#',
            'comment_end_string': '#>'
            }

    LYX_TAGS = {
            'block_start_string': '<%',
            'block_end_string': '%>',
            'variable_start_string': '<<',
            'variable_end_string': '>>',
            'comment_start_string': '<<#',
            'comment_end_string': '#>>'
            }

    def setup_jinja_env(self, loader=None):
        env_attrs = {}

        for k, v in self.setting_values().iteritems():
            underscore_k = k.replace("-", "_")
            if k in self.__class__._settings and not k in self._not_jinja_settings:
                env_attrs[underscore_k] = v

        env_attrs['undefined'] = PassThroughWhitelistUndefined

        if self.ext in (".tex", ".wiki") and self.setting('changetags'):
            if 'lyxjinja' in self.doc.filter_aliases:
                tags = self.LYX_TAGS
            else:
                tags = self.TEX_TAGS

            self.log_debug("Changing tags to latex/wiki format: %s" % ' '.join(tags))

            for underscore_k, v in tags.iteritems():
                hyphen_k = underscore_k.replace("_", "-")
                if env_attrs[underscore_k] == self.__class__._settings[hyphen_k][1]:
                    self.log_debug("setting %s to %s" % (underscore_k, v))
                    env_attrs[underscore_k] = v

        if loader:
            env_attrs['loader'] = loader

        debug_attr_string = ", ".join("%s: %r" % (k, v) for k, v in env_attrs.iteritems())
        self.log_debug("creating jinja2 environment with: %s" % debug_attr_string)
        return jinja2.Environment(**env_attrs)

    def handle_jinja_exception(self, e, input_text, template_data):
        result = []
        input_lines = input_text.splitlines()

        # Try to parse line number from stack trace...
        if isinstance(e, UndefinedError) or isinstance(e, TypeError):
            # try to get the line number
            m = re.search(r"File \"<template>\", line ([0-9]+), in top\-level template code", traceback.format_exc())
            if m:
                e.lineno = int(m.groups()[0])
            else:
                e.lineno = 0
                self.log_warn("unable to parse line number from traceback")

        args = {
                'error_type' : e.__class__.__name__,
                'key' : self.key,
                'lineno' : e.lineno,
                'message' : e.message,
                'name' : self.output_data.name,
                'workfile' : self.input_data.storage.data_file()
                }

        result.append("a %(error_type)s problem was detected: %(message)s" % args)

        if isinstance(e, UndefinedError):
            match_has_no_attribute = re.match("^'[\w\s\.]+' has no attribute '(.+)'$", e.message)
            match_is_undefined = re.match("^'([\w\s]+)' is undefined$", e.message)

            if match_has_no_attribute:
                undefined_object = match_has_no_attribute.groups()[0]
                match_lines = []
                for i, line in enumerate(input_lines):
                    if (".%s" % undefined_object in line) or ("'%s'" % undefined_object in line) or ("\"%s\"" % undefined_object in line):
                        result.append("line %04d: %s" % (i+1, line))
                        match_lines.append(i)
                if len(match_lines) == 0:
                    self.log_info("Tried to automatically find source of error: %s. Could not find match for '%s'" % (e.message, undefined_object))

            elif match_is_undefined:
                undefined_object = match_is_undefined.groups()[0]
                for i, line in enumerate(input_lines):
                    if undefined_object in line:
                        result.append("line %04d: %s" % (i+1, line))
            else:
                self.log_debug("Tried to automatically find where the error was in the template, but couldn't.")

        else:
            result.append("line %04d: %s" % (e.lineno, input_lines[e.lineno-1]))

        raise dexy.exceptions.UserFeedback("\n".join(result))

    def jinja_template_filters(self):
        filters = {}
        for alias in self.setting('filters'):
            self.log_debug("  creating filters from template plugin %s" % alias)
            template_plugin = TemplatePlugin.create_instance(alias)

            if not template_plugin.is_active():
                self.log_debug("    skipping %s - not active" % alias)
                continue
        
            methods = template_plugin.run()

            for k, v in methods.iteritems():
                if not k in template_plugin.setting('no-jinja-filter'):
                    self.log_debug("    creating jinja filter for method %s" % k)
                    filters[k] = v[1]

        return filters

    def process(self):
        self.populate_workspace()

        wd = self.parent_work_dir()

        macro_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'macros'))
        dirs = ['.', wd, os.path.dirname(self.doc.name), macro_dir] + self.setting('jinja-path')
        self.log_debug("setting up jinja FileSystemLoader with dirs %s" % ", ".join(dirs))
        loader = FileSystemLoader(dirs)

        self.log_debug("setting up jinja environment")
        env = self.setup_jinja_env(loader=loader)
        self.log_debug("setting up jinja template filters")
        env.filters.update(self.jinja_template_filters())

        self.log_debug("initializing template")

        template_data = self.template_data()
        self.log_debug("jinja template data keys are %s" % ", ".join(sorted(template_data)))

        try:
            self.log_debug("about to create jinja template")
            template = env.get_template(self.work_input_filename())
            self.log_debug("about to process jinja template")
            template.stream(template_data).dump(self.output_filepath(), encoding="utf-8")
        except (TemplateSyntaxError, UndefinedError, TypeError) as e:
            try:
                self.log_debug("removing %s since jinja had an error" % self.output_filepath())
                os.remove(self.output_filepath())
            except os.error:
                pass
            self.handle_jinja_exception(e, unicode(self.input_data), template_data)
        except TemplateNotFound as e:
            msg = "Jinja couldn't find the template '%s', make sure this file is an input to %s" 
            msgargs = (e.message, self.doc.key)
            raise dexy.exceptions.UserFeedback(msg % msgargs)
        except Exception as e:
            try:
                self.log_debug("removing %s since jinja had an error" % self.output_filepath())
                os.remove(self.output_filepath())
            except os.error:
                pass
            self.log_debug(unicode(e))
            raise

########NEW FILE########
__FILENAME__ = templating_plugins
from bs4 import BeautifulSoup
from datetime import datetime
from dexy.exceptions import UserFeedback
from dexy.exceptions import InternalDexyProblem
from dexy.plugin import TemplatePlugin
from dexy.utils import levenshtein
from dexy.version import DEXY_VERSION
from pygments.styles import get_all_styles
import calendar
import dexy.commands
import dexy.commands.cite
import dexy.data
import dexy.exceptions
import dexy.plugin
import inflection
import inspect
import jinja2
import json
import markdown
import operator
import os
import pygments
import pygments.formatters
import re
import time
import uuid
import xml.etree.ElementTree as ET

class Etree(TemplatePlugin):
    """
    Exposes element tree as ET.
    """
    aliases = ['etree']
    def run(self):
        return { 'ET' : ("The xml.etree.ElementTree module.", ET,) }

class Markdown(TemplatePlugin):
    """
    Exposes markdown.
    """
    aliases = ['md', 'markdown']

    def run(self):
        md = markdown.Markdown()
        h = "Function which converts markdown to HTML."
        return {
                'markdown' : (h, md.convert),
                'md' : (h, md.convert)
                }

class Uuid(TemplatePlugin):
    """
    Exposes the UUID module.
    """
    aliases = ['uuid']
    def run(self):
        return { 'uuid' : ("The Python uuid module. http://docs.python.org/2/library/uuid.html", uuid) }

class Time(TemplatePlugin):
    """
    Exposes time module.
    """
    aliases = ['time']
    def run(self):
        return { 'time' : ("The Python time module.", time) }

class Operator(TemplatePlugin):
    """
    Exposes features of the operator module.
    """
    aliases = ['operator']
    keys = ['attrgetter', 'itemgetter']
    def run(self):
        d = {}
        for k in self.keys:
            fn = getattr(operator, k)
            d[k] = ("The %s method from Python's operator module." % k, fn)
        return d

class PrettyPrintHtml(TemplatePlugin):
    """
    Uses BeautifulSoup 4 to prettify HTML.
    """
    aliases = ['bs4']
    _settings = {
            'no-jinja-filter' : ['BeautifulSoup']
            }

    def prettify_html(self, html):
        soup = BeautifulSoup(unicode(html), 'html.parser')
        return soup.prettify()

    def run(self):
        return {
            'prettify_html' : ("Pretty-print HTML using BeautifulSoup", self.prettify_html),
            'BeautifulSoup' : ("The BeautifulSoup module.", BeautifulSoup)
            }

class LoadYaml(TemplatePlugin):
    """
    Loads YAML from a file.
    """
    aliases = ['loadyaml']

    def load_yaml(self, filename):
        import yaml
        with open(filename, 'rb') as f:
            return yaml.safe_load(f.read())

    def run(self):
        return {
                'load_yaml' : ("Safely load YAML from a file.", self.load_yaml,)
                }

class ParseYaml(TemplatePlugin):
    """
    Parse YAML from a string.
    """
    aliases = ['parseyaml']

    def parse_yaml(self, yamltext):
        import yaml
        return yaml.safe_load(unicode(yamltext))

    def run(self):
        return {
                'parse_yaml' : ("Safely load YAML from text.", self.parse_yaml,)
                }

class Debug(TemplatePlugin):
    """
    Adds debug() and throw() [a.k.a. raise()] methods to templates.
    """
    aliases = ['debug']

    def debug(self, debug_text, echo=True):
        if hasattr(self, 'filter_instance'):
            print "template debug from '%s': %s" % (self.filter_instance.key, debug_text)
        else:
            print "template debug: %s" % (debug_text)

        if echo:
            return debug_text
        else:
            return ""

    def throw(self, err_message):
        if hasattr(self, 'filter_instance'):
            raise UserFeedback("template throw from '%s': %s" % (self.filter_instance.key, err_message))
        else:
            raise UserFeedback("template throw: %s" % (err_message))

    def run(self):
        return {
                'debug' : ("A debugging method - prints content to command line stdout.", self.debug),
                'throw' : ("A debugging utility which raises exception with argument.", self.throw),
                'raise' : ("Alias for `throw`.", self.throw)
                }

class Bibtex(TemplatePlugin):
    """
    Produces a bibtex entry for dexy.
    """
    def run(self):
        return { 'dexy_bibtex' : dexy.commands.cite.bibtex_text() }

class Inflection(TemplatePlugin):
    """
    Exposes the inflection package for doing nice things with strings 
    """
    aliases = ['inflection']
    _settings = {
            'methods' : ("Methods of the inflection module to expose.",
                ['camelize', 'dasherize', 'humanize', 'ordinal',
                'ordinalize', 'parameterize', 'pluralize', 'singularize',
                'titleize', 'transliterate', 'underscore'])
            }

    def run(self):
        return dict((method, ("The %s method from Python inflection module." % method, getattr(inflection, method),)) for method in self.setting('methods'))

class StripJavadocHTML(TemplatePlugin):
    """
    Exposes javadoc2rst command which strips HTML tags from javadoc comments.
    """
    aliases = ['stripjavadochtml']
    _settings = {
            'escape' : ("Escape characters.", ['\\']),
            'remove' : ("Remove characters.", ['<p>', '<P>'])
            }

    def strip_javadoc_html(self, javadoc):
        for symbol in self.setting('escape'):
            javadoc = javadoc.replace(symbol, '\n')
        for word in self.setting('remove'):
            javadoc = javadoc.replace(word, "\\%s" % symbol)
        return javadoc

    def run(self):
        h = "Replace escape character with newlines and remove paragraph tags."
        return {
                'javadoc2rst' : (h, self.strip_javadoc_html),
                'strip_javadoc_html' : (h, self.strip_javadoc_html)
                }

class PrettyPrint(TemplatePlugin):
    """
    Exposes pprint (really pformat).
    """
    aliases = ['pp', 'pprint']

    def run(self):
        import pprint
        return {
            'pprint' : ("Pretty prints Python objects.", pprint.pformat,),
            'pformat' : ("Pretty prints Python objects.", pprint.pformat,)
         }

class PrettyPrintJson(TemplatePlugin):
    """
    Exposes ppjson command.
    """
    aliases = ['ppjson']

    def ppjson(self, json_string):
        return json.dumps(json.loads(json_string), sort_keys = True, indent = 4)

    def run(self):
        return {
            'ppjson' : ("Pretty prints valid JSON.", self.ppjson,)
         }

class ReplaceJinjaFilters(TemplatePlugin):
    """
    Replace some jinja filters so they call unicode() first.
    """
    aliases = ['replacejinjafilters']

    def do_indent(self, data, width=4, indentfirst=False):
        return jinja2.filters.do_indent(unicode(data), width, indentfirst)

    def run(self):
        return {
                'indent' : ("Jinja's indent function.", self.do_indent)
                }

class Assertions(TemplatePlugin):
    """
    Allow making assertions in documents.
    """
    aliases = ['assertions']

    def decorate_response(self, doc):
        if hasattr(self, 'filter_instance'):
            indicator = self.filter_instance.setting('assertion-passed-indicator')
        else:
            indicator = None

        if indicator:
            return unicode(doc) + indicator
        else:
            return doc

    def do_assert_equals(self, doc, expected):
        """
        Assert that input equals expected value.
        """
        assert unicode(doc) == expected, "input text did not equal '%s'" % expected
        return self.decorate_response(doc)

    def do_assert_contains(self, doc, contains):
        """
        Assert that input equals expected value.
        """
        assert contains in unicode(doc), "input text did not contain '%s'" % contains
        return self.decorate_response(doc)

    def do_assert_does_not_contain(self, doc, shouldnt_contain):
        """
        Assert that input equals expected value.
        """
        msg = "input text contained '%s'" % shouldnt_contain
        assert not shouldnt_contain in unicode(doc), msg
        return self.decorate_response(doc)

    def do_assert_startswith(self, doc, startswith):
        """
        Assert that the input starts with the specified value.
        """
        assert unicode(doc).startswith(startswith), "input text did not start with '%s'" % startswith
        return self.decorate_response(doc)

    def do_assert_matches(self, doc, regexp):
        """
        Assert that input matches the specified regular expressino.
        """
        assert re.match(regexp, unicode(doc)), "input text did not match regexp %s" % regexp
        return self.decorate_response(doc)

    def make_soup(self, doc):
        return BeautifulSoup(unicode(doc))

    def soup_select(self, doc, selector):
        soup = self.make_soup(doc)
        return soup.select(selector)

    def soup_select_unique(self, doc, selector):
        results = self.soup_select(doc, selector)

        n = len(results)
        if n == 0:
            msg = "no results found matching selector '%s'"
            msgargs = (selector,)
            raise AssertionError(msg % msgargs)

        elif n > 1:
            msg = "%s results found matching selector '%s', must be unique"
            msgargs = (n, selector,)
            raise AssertionError(msg % msgargs)

        return results[0]

    def do_assert_selector_text(self, doc, selector, expected_text):
        """
        Asserts that the contents of CSS selector matches the expected text.
        
        Leading/trailing whitespace is stripped before comparison.
        """
        element = self.soup_select_unique(doc, selector)
        err = "element '%s' did not contain '%s'" % (selector, expected_text)
        assert element.get_text().strip() == expected_text, err

    def run(self):
        methods = {}
        for name in dir(self):
            if name.startswith("do_"):
                method = getattr(self, name)
                docs = inspect.getdoc(method).splitlines()[0].strip()
                if not docs:
                    raise InternalDexyProblem("You must define docstring for %s" % name)
                methods[name.replace("do_", "")] = (docs, method)
        return methods

class Head(TemplatePlugin):
    """
    Provides a 'head' method.
    """
    aliases = ['head']

    def head(self, text, n=15):
        """
        Returns the first n lines of input string.
        """
        return "\n".join(unicode(text).splitlines()[0:n])

    def run(self):
        return {
                'head' : ("Returns the first n lines of input string.", self.head)
                }

class Tail(TemplatePlugin):
    """
    Provides a 'tail' method.
    """
    aliases = ['tail']

    def tail(self, text, n=15):
        """
        Returns the last n lines of input string.
        """
        return "\n".join(unicode(text).splitlines()[-n:])

    def run(self):
        return {
                'tail' : ("Returns the last n lines of inptu string.", self.tail)
                }

class RstCode(TemplatePlugin):
    """
    Indents code n spaces (defaults to 4) and wraps in .. code:: directive.
    """
    aliases = ['rstcode']

    def rstcode(self, text, n=4, language='python'):
        output = inspect.cleandoc("""
            .. code:: %s
            '   :class: highlight'
            """ % language)

        for line in unicode(text).splitlines():
            output += " " * n + line

        output += "\n"
        return output

class PythonDatetime(TemplatePlugin):
    """
    Exposes python datetime and calendar functions.
    """
    aliases = ['datetime', 'calendar']
    def run(self):
        today = datetime.today()
        month = today.month
        year = today.year
        cal = calendar.Calendar()
        caldates = list(cal.itermonthdates(year, month))

        return {
            "datetime" : ("The Python datetime module.", datetime),
            "calendar" : ("A Calendar instance from Python calendar module.", calendar),
            "caldates" : ("List of calendar dates in current month.", caldates),
            "cal" : ("Shortcut for `calendar`.", calendar),
            "today" : ("Result of datetime.today().", today),
            "month" : ("Current month.", month),
            "year" : ("Current year.", year)
            }

class DexyVersion(TemplatePlugin):
    """
    Exposes the current dexy version
    """
    aliases = ['dexyversion']
    def run(self):
        return { "DEXY_VERSION" : ("The active dexy version. Currently %s." % DEXY_VERSION, DEXY_VERSION) }

class SimpleJson(TemplatePlugin):
    """
    Exposes the json module.
    """
    aliases = ['json']
    def run(self):
        return { 'json' : ("The Python json module.", json,) }

class RegularExpressions(TemplatePlugin):
    """
    Exposes re_match and re_search.
    """
    aliases = ['regex']
    def run(self):
        return { 're' : ("The Python re module.", re,), }

class PythonBuiltins(TemplatePlugin):
    """
    Exposes python builtins.
    """
    aliases = ['builtins']
    # Intended to be all builtins that make sense to run within a document.
    PYTHON_BUILTINS = [abs, all, any, basestring, bin, bool, bytearray,
            callable, chr, cmp, complex, dict, dir, divmod, enumerate, filter,
            float, format, hex, id, int, isinstance, issubclass, iter, len,
            list, locals, long, map, hasattr, max, min, oct, ord, pow, range,
            reduce, repr, reversed, round, set, slice, sorted, str, sum, tuple,
            type, xrange, unicode, zip]

    def run(self):
        return dict((f.__name__, ("The python builtin function %s" % f.__name__, f,)) for f in self.PYTHON_BUILTINS)

class PygmentsStylesheet(TemplatePlugin):
    """
    Inserts pygments style codes.
    """
    aliases = ['pygments']

    # TODO rewrite this so it's a function rather than pre-generating all
    # of the stylesheets. Detect document format automatically.

    def generate_stylesheets(self):
        pygments_stylesheets = {}
        if hasattr(self, 'filter_instance') and self.filter_instance.doc.args.has_key('pygments'):
            formatter_args = self.filter_instance.doc.args['pygments']
        else:
            formatter_args = {}

        for style_name in get_all_styles():
            for formatter_class in [pygments.formatters.LatexFormatter, pygments.formatters.HtmlFormatter]:
                formatter_args['style'] = style_name
                pygments_formatter = formatter_class(**formatter_args)
                style_info = pygments_formatter.get_style_defs()

                for fn in pygments_formatter.filenames:
                    ext = fn.split(".")[1]
                    if ext == 'htm':
                        ext = 'css'
                    key = "%s.%s" % (style_name, ext)
                    pygments_stylesheets[key] = style_info

        return pygments_stylesheets

    def run(self):
        return {
            'pygments' : (
                "Dictionary of pygments stylesheets.",
                self.generate_stylesheets()
             )}

class PygmentsHighlight(TemplatePlugin):
    """
    Provides a 'highlight' function for applying syntax highlighting.
    """
    aliases = ['highlight']
    # TODO figure out default fmt based on document ext - document would need
    # to implement a "final_ext()" method

    def highlight(self, text, lexer_name, fmt='html', noclasses=False, lineanchors='l'):
        text = unicode(text)
        formatter_options = { "lineanchors" : lineanchors, "noclasses" : noclasses }
        lexer = pygments.lexers.get_lexer_by_name(lexer_name)
        formatter = pygments.formatters.get_formatter_by_name(fmt, **formatter_options)
        return pygments.highlight(text, lexer, formatter)

    def run(self):
        return {
                'highlight' : ("Pygments syntax highlighter.", self.highlight),
                'pygmentize' : ("Pygments syntax highlighter.", self.highlight)
                }

class Subdirectories(TemplatePlugin):
    """
    Show subdirectories under this document.
    """
    aliases = ['subdirectories']
    def run(self):
        if hasattr(self.filter_instance, 'output_data'):
            # The directory containing the document to be processed.
            doc_dir = os.path.dirname(self.filter_instance.output_data.name)

            # Get a list of subdirectories under this document's directory.
            subdirectories = [d for d in sorted(os.listdir(os.path.join(os.curdir, doc_dir))) if os.path.isdir(os.path.join(os.curdir, doc_dir, d))]
            return {'subdirectories' : ("List of subdirectories of this document.", subdirectories)}
        else:
            return {'subdirectories' : ("List of subdirectories of this document.", [])}

class Variables(TemplatePlugin):
    """
    Allow users to set variables in document args which will be available to an individual document.
    """
    aliases = ['variables']
    def run(self):
        variables = {}
        variables.update(self.filter_instance.setting('variables'))
        variables.update(self.filter_instance.setting('vars'))

        formatted_variables = {}
        for k, v in variables.iteritems():
            if isinstance(v, tuple):
                formatted_variables[k] = v
            elif isinstance(v, list) and len(v) == 2:
                formatted_variables[k] = v
            else:
                formatted_variables[k] = ("User-provided variable.", v)
        return formatted_variables

class Globals(TemplatePlugin):
    """
    Makes available the global variables specified on the dexy command line
    using the --globals option
    """
    aliases = ['globals']
    def run(self):
        raw_globals = self.filter_instance.doc.wrapper.globals
        env = {}
        for kvpair in raw_globals.split(","):
            if "=" in kvpair:
                k, v = kvpair.split("=")
                env[k] = ("Global variable %s" % k, v)
        return env

class Inputs(TemplatePlugin):
    """
    Populates the 'd' object.
    """
    aliases = ['inputs']

    def input_tasks(self):
        return self.filter_instance.doc.walk_input_docs()

    def run(self):
        input_docs = {}

        for doc in self.input_tasks():
            input_docs[doc.key] = doc

        d = D(self.filter_instance.doc, input_docs)

        if hasattr(self.filter_instance, 'output_data'):
            output_data = self.filter_instance.output_data
        else:
            output_data = None

        return {
            'a' : ("Another way to reference 'd'. Deprecated.", d),
            'args' : ("The document args.", self.filter_instance.doc.args),
            'd' : ("The 'd' object.", d),
            'f' : ("The filter instance for this document.", self.filter_instance),
            's' : ("The data instance for this document.", output_data),
            'w' : ("The wrapper for the dexy run.", self.filter_instance.doc.wrapper)
            }

class D(object):
    def __init__(self, doc, input_docs):
        self._artifact = doc
        self._parent_dir = doc.output_data().parent_dir()
        self._input_docs = input_docs.values()
        self._input_doc_keys = [d.key for d in self._input_docs]
        self._input_doc_names = [d.output_data().long_name() for d in self._input_docs]
        self._input_doc_titles = ["title:%s" % d.output_data().title() for d in self._input_docs]

        self._ref_cache = {}

    def keys(self):
        return self._input_doc_keys

    def key_or_name_index(self, ref):
        if ref in self._input_doc_keys:
            return self._input_doc_keys.index(ref)
        elif ref in self._input_doc_names:
            return self._input_doc_names.index(ref)

    def matching_keys(self, ref):
        return [(i, k) for (i, k) in enumerate(self._input_doc_keys) if k.startswith(ref)]

    def unique_matching_key(self, ref):
        """
        If the reference unambiguously identifies a single key, return it.
        """
        matching_keys = self.matching_keys(ref)
        if len(matching_keys) == 1:
            return matching_keys[0]

    def title_index(self, ref):
        if ref in self._input_doc_titles:
            return self._input_doc_titles[ref]

    def __getitem__(self, ref):
        try:
            return self._ref_cache[ref]
        except KeyError:
            pass

        doc = None
        path_to_ref = None
        index = None

        if ref.startswith("/"):
            path_to_ref = ref.lstrip("/")
            index = self.key_or_name_index(path_to_ref)

        elif ref.startswith('title:'):
            index = self.title_index(ref)

        else:
            if self._parent_dir:
                path_to_ref = os.path.normpath(os.path.join(self._parent_dir, ref))
            else:
                path_to_ref = ref

            index = self.key_or_name_index(path_to_ref)

        if index is not None:
            doc = self._input_docs[index]
        else:
            matching_key = self.unique_matching_key(ref)
            if matching_key:
                doc = self._input_docs[matching_key[0]]

        if doc:
            # store this reference in cache for next time
            self._ref_cache[ref] = doc.output_data()
            return doc.output_data()
        else:
            msg = "No document named '%s'\nis available as an input to '%s'.\n"

            closest_match_lev = 15 # if more than this, not worth mentioning
            closest_match = None

            self._artifact.log_warn("Listing documents which are available:")
            for k in sorted(self._input_doc_keys):
                lev = levenshtein(k, path_to_ref)
                if lev < closest_match_lev:
                    closest_match = k
                    closest_match_lev = lev
                self._artifact.log_warn("  %s" % k)

            msg += "There are %s input documents available, their keys have been written to dexy's log.\n" % len(self._input_doc_keys)
           
            if closest_match:
                msg += "Did you mean '%s'?" % closest_match

            msgargs = (ref, self._artifact.key)
            raise dexy.exceptions.UserFeedback(msg % msgargs)

########NEW FILE########
__FILENAME__ = utils
# Extra Pygments Lexers - will be submitted to Pygments and removed from here
# when available in a Pygments release

from pygments.lexers.templates import DjangoLexer
from pygments.lexer import DelegatingLexer
from pygments.lexers.text import RstLexer

class RstDjangoLexer(DelegatingLexer):
    """
    Subclass of the `DjangoLexer` that highlights unlexed data with the
    `RstLexer`.
    """

    name = 'ReStructuredText+Django/Jinja'
    aliases = ['rst+django', 'rst+jinja']
    filenames = ['*.rst']

    def __init__(self, **options):
        super(RstDjangoLexer, self).__init__(RstLexer, DjangoLexer, **options)

    def analyse_text(text):
        rv = DjangoLexer.analyse_text(text) - 0.01
        # TODO count how many times ".. " is in text
        if ".. " in text:
            rv += 0.4
        return rv

########NEW FILE########
__FILENAME__ = wordpress
from dexy.filters.api import ApiFilter
import dexy.exceptions
import json
import xmlrpclib

try:
    import mimetypes
    wp_aliases = ['wp', 'wordpress']
except UnicodeDecodeError:
    print "Unable to load mimetypes library. WordPressFilter will not work. See http://bugs.python.org/issue9291"
    mimetypes = None
    wp_aliases = []

class WordPressFilter(ApiFilter):
    """
    Posts to a WordPress blog.

    WordPress has a very confusing API setup since it implements its own API
    methods (under the wp namespace) and also supports the Blogger, metaWeblog
    and MovableType APIs. Unfortunately the wp namespace methods are
    incomplete, so you have to mix and match.

    Uses the WP XMLRPC API where possible:
    http://codex.wordpress.org/XML-RPC_wp

    Creating and editing blog posts uses the metaWeblog API:
    http://xmlrpc.scripting.com/metaWeblogApi.html

    If this filter is applied to a document with file extension in
    PAGE_CONTENT_EXTENSIONS (defined in ApiFilter class and inherited here)
    then the document will be uploaded to WordPress as a blog post.

    If not, then the document is assumed to be an image or other binary asset,
    and file upload will be used instead, so a new element will be added to the
    Media Library. If this is the case, then the URL is the resulting image is
    returned, so you can use that URL directly in your blog posts or other
    documents that need to link to the asset.

    IMPORTANT There is currently a frustrating bug in WP:
    http://core.trac.wordpress.org/ticket/17604
    which means that every time you run this filter, a *new* image asset will
    be created, even though we tell WordPress to overwrite the existing image
    of the same name. You will end up with dozens of copies of this image
    cluttering up your media library.

    For now, we recommend using an external site to host your images and
    assets, such as Amazon S3.
    """
    aliases = wp_aliases

    _settings = {
            'blog-id' : ("The wordpress blog id.", 0),
            'page-content-extensions' : ('', ['.md', '.txt', '.html']),
            'document-api-config-file' : 'wordpress.json',
            'api-key-name' : 'wordpress',
            'output-extensions' : ['.txt']
            }

    def docmd_create_keyfile(self):
        """
        Creates a key file for WordPress in the local directory.
        """
        self.create_keyfile("project-api-key-file")

    def api_url(self):
        base_url = self.read_param('url')
        if base_url.endswith("xmlrpc.php"):
            return base_url
        else:
            if not base_url.endswith("/"):
                base_url = "%s/" % base_url
            return "%sxmlrpc.php" % base_url

    def api(klass):
        if not hasattr(klass, "_api"):
            klass._api = xmlrpclib.ServerProxy(klass.api_url())
        return klass._api

    def docmd_list_methods(klass):
        """
        List API methods exposed by WordPress API.
        """
        for method in sorted(klass.api().system.listMethods()):
            print method

    def docmd_list_categories(self):
        """
        List available blog post categories.
        """
        username = self.read_param('username')
        password = self.read_param('password')
        headers = ['categoryName']
        print "\t".join(headers)
        for category_info in self.api().wp.getCategories(self.setting('blog-id'), username, password):
            print "\t".join(category_info[h] for h in headers)

    def upload_page_content(self):
        input_text = unicode(self.input_data)
        document_config = self.read_document_config()

        document_config['description'] = input_text
        post_id = document_config.get('postid')
        publish = document_config.get('publish', False)

        for key, value in document_config.iteritems():
            if not key == "description":
                self.log_debug("%s: %s" % (key, value))

        if post_id:
            self.log_debug("Making editPost API call.")
            self.api().metaWeblog.editPost(
                    post_id,
                    self.read_param('username'),
                    self.read_param('password'),
                    document_config,
                    publish
                    )
        else:
            self.log_debug("Making newPost API call.")
            post_id = self.api().metaWeblog.newPost(
                    self.setting('blog-id'),
                    self.read_param('username'),
                    self.read_param('password'),
                    document_config,
                    publish
                    )
            document_config['postid'] = post_id

        self.log_debug("Making getPost API call.")
        post_info = self.api().metaWeblog.getPost(
                post_id,
                self.read_param('username'),
                self.read_param('password')
                )

        for key, value in post_info.iteritems():
            if key in ('date_modified_gmt', 'dateCreated', 'date_modified', 'date_created_gmt',):
                post_info[key] = value.value

            if not key == "description":
                self.log_debug("%s: %s" % (key, value))

        del document_config['description']
        document_config['publish'] = publish
        self.save_document_config(document_config)

        if publish:
            self.output_data.set_data(post_info['permaLink'])
        else:
            self.output_data.set_data(json.dumps(post_info))

    def upload_image_content(self):
        with open(self.input_data.storage.data_file(), 'rb') as f:
            image_base_64 = xmlrpclib.Binary(f.read())

            upload_file = {
                     'name' : self.work_input_filename(),
                     'type' : mimetypes.types_map[self.prev_ext],
                     'bits' : image_base_64,
                     'overwrite' : 'true'
                     }

            upload_result = self.api().wp.uploadFile(
                     self.setting('blog-id'),
                     self.read_param('username'),
                     self.read_param('password'),
                     upload_file
                     )

            self.log_debug("wordpress upload results: %s" % upload_result)
            url = upload_result['url']
            self.log_debug("uploaded %s to %s" % (self.key, url))

        self.output_data.set_data(url)

    def process(self):
        try:
            if self.prev_ext in self.setting('page-content-extensions'):
                self.upload_page_content()
            else:
                self.upload_image_content()

        except xmlrpclib.Fault as e:
            raise dexy.exceptions.UserFeedback(unicode(e))

########NEW FILE########
__FILENAME__ = xxml
from dexy.filter import DexyFilter
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.formatters.latex import LatexFormatter
from pygments.lexers import get_lexer_for_filename
import json

try:
    from lxml import etree
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

class XmlSectionFilter(DexyFilter):
    """
    Stores all elements in the input XML document which have any of the
    attributes specified in unique-attributes or qualified-attributes.
    """
    aliases = ["xxml", "xmlsec"]
    _settings = {
            'input-extensions' : [".xml", ".html", ".txt"],
            'pygments' : ("Whether to apply pygments syntax highlighting", True),
            'unique-attributes' : ("Elements to be added if they have this attribute, to be treated as globally unique.", ["id"]),
            'qualified-attributes' : ("Elements to be added if they have this attribute, to be qualified by element type.", ["name"]),
            'data-type' : 'keyvalue',
            'output-extensions' :  [".json", ".sqlite3"]
            }

    def is_active(self):
        return AVAILABLE

    def append_element_attributes_with_key(self, element, element_key):
        source = etree.tostring(element, pretty_print=True).strip()
        inner_html = "\n".join(etree.tostring(child) for child in element.iterchildren())
        self.output_data.append("%s:lineno" % element_key, element.sourceline)
        self.output_data.append("%s:tail" % element_key, element.tail)
        self.output_data.append("%s:text" % element_key, element.text)
        self.output_data.append("%s:tag" % element_key, element.tag)
        self.output_data.append("%s:source" % element_key, source)
        self.output_data.append("%s:inner-html" % element_key, inner_html)

        safe_attrib = {}
        for k, v in element.attrib.iteritems():
            try:
                json.dumps(v)
                safe_attrib[k] = v
            except TypeError:
                pass

        self.output_data.append("%s:attrib" % element_key, json.dumps(safe_attrib))

        if self.setting('pygments'):
            self.output_data.append("%s:html-source" % element_key, highlight(source, self.lexer, self.html_formatter))
            self.output_data.append("%s:latex-source" % element_key, highlight(source, self.lexer, self.latex_formatter))

    def process(self):
        assert self.output_data.state == 'ready'

        if self.setting('pygments'):
            self.lexer = get_lexer_for_filename(self.input_data.storage.data_file())
            self.html_formatter = HtmlFormatter(lineanchors=self.output_data.web_safe_document_key())
            self.latex_formatter = LatexFormatter()

        if self.input_data.ext in ('.xml', '.txt'):
            parser = etree.XMLParser()
        elif self.input_data.ext == '.html':
            parser = etree.HTMLParser()
        else:
            raise Exception("Unsupported extension %s" % self.input_data.ext)

        tree = etree.parse(self.input_data.storage.data_file(), parser)

        for element in tree.iter("*"):
            element_keys = []
           
            for attribute_name in self.setting('unique-attributes'):
                if element.attrib.has_key(attribute_name):
                    element_keys.append(element.attrib[attribute_name])
            for attribute_name in self.setting('qualified-attributes'):
                if element.attrib.has_key(attribute_name):
                    element_keys.append(element.attrib[attribute_name])
                    element_keys.append("%s:%s" % (element.tag, element.attrib[attribute_name]))

            for element_key in element_keys:
                self.append_element_attributes_with_key(element, element_key)

        self.output_data.save()

########NEW FILE########
__FILENAME__ = yamlargs
from dexy.filter import DexyFilter
from dexy.utils import parse_yaml
import re

class YamlargsFilter(DexyFilter):
    """
    Specify attributes in YAML at top of file.
    """
    aliases = ['yamlargs']

    def process_text(self, input_text):
        regex = "\r?\n---\r?\n"
        if re.search(regex, input_text):
            self.log_debug("Found yaml content.")
            raw_yamlargs, content = re.split(regex, input_text)
            yamlargs = parse_yaml(raw_yamlargs)
            self.log_debug("Adding yaml: %s" % yamlargs)
            self.add_runtime_args(yamlargs)
            return content
        else:
            self.log_debug("No yaml content found.")
            return input_text

########NEW FILE########
__FILENAME__ = load_plugins
import dexy.filters
import dexy.reporters
import dexy.parsers
import dexy.datas

# Automatically register plugins in any python package named like dexy_*
import pkg_resources
for dist in pkg_resources.working_set:
    if dist.key.startswith("dexy-"):
        import_pkg = dist.egg_name().split("-")[0]
        try:
            __import__(import_pkg)
        except ImportError as e:
            print "plugin", import_pkg, "not registered because", e

########NEW FILE########
__FILENAME__ = node
from dexy.utils import md5_hash
from dexy.utils import os_to_posix
import dexy.doc
import dexy.plugin
import fnmatch
import json
import re

class Node(dexy.plugin.Plugin):
    """
    base class for Nodes
    """
    __metaclass__ = dexy.plugin.PluginMeta
    _settings = {}
    aliases = ['node']
    state_transitions = (
            ('new', 'cached'),
            ('cached', 'consolidated'),
            ('new', 'uncached'),
            ('uncached', 'running'),
            ('running', 'ran'),
            )

    def __init__(self, pattern, wrapper, inputs=None, **kwargs):
        self.key = os_to_posix(pattern)
        self.wrapper = wrapper
        self.args = kwargs
        if inputs:
            self.inputs = list(inputs)
        else:
            self.inputs = []

        self.initialize_settings(**kwargs)

        self.start_time = 0
        self.finish_time = 0
        self.elapsed_time = 0

        self.runtime_args = {}
        self.children = []
        self.additional_docs = []

        self.hashid = md5_hash(self.key)

        self.state = 'new'

        # Class-specific setup.
        self.setup()

    def setup(self):
        pass
   
    def check_doc_changed(self):
        return False

    def __repr__(self):
        return "%s(%s)" % ( self.__class__.__name__, self.key)

    def transition(self, new_state):
        dexy.utils.transition(self, new_state)

    def update_all_settings(self, new_args):
        pass

    def add_runtime_args(self, args):
        self.update_all_settings(args)
        self.runtime_args.update(args)
        self.wrapper.batch.update_doc_info(self)

    def arg_value(self, key, default=None):
        return self.args.get(key, default) or self.args.get(key.replace("-", "_"), default)

    def walk_inputs(self):
        """
        Yield all direct inputs and their inputs.
        """
        children = []
        def walk(inputs):
            for inpt in inputs:
                children.append(inpt)
                walk(inpt.inputs + inpt.children)

        if self.inputs:
            walk(self.inputs)
        elif hasattr(self, 'parent'):
            children = self.parent.walk_inputs()

        return children

    def walk_input_docs(self):
        """
        Yield all direct inputs and their inputs, if they are of class 'doc'
        """
        for node in self.walk_inputs():
            if node.__class__.__name__ == 'Doc':
                yield node

    def log_debug(self, message):
        self.wrapper.log.debug("(state:%s) %s %s: %s" % (self.wrapper.state, self.hashid, self.key_with_class(), message))

    def log_info(self, message):
        self.wrapper.log.info("(state:%s) %s %s: %s" % (self.wrapper.state, self.hashid, self.key_with_class(), message))

    def log_warn(self, message):
        self.wrapper.log.warn("(state:%s) %s %s: %s" % (self.wrapper.state, self.hashid, self.key_with_class(), message))

    def key_with_class(self):
        return "%s:%s" % (self.__class__.aliases[0], self.key)

    def check_args_changed(self):
        """
        Checks if args have changed by comparing calculated hash against the
        archived calculated hash from last run.
        """
        saved_args = self.wrapper.saved_args.get(self.key_with_class())
        if not saved_args:
            self.log_debug("no saved args, will return True for args_changed")
            return True
        else:
            self.log_debug("    saved args '%s' (%s)" % (saved_args, saved_args.__class__))
            self.log_debug("    sorted args '%s' (%s)" % (self.sorted_arg_string(), self.sorted_arg_string().__class__))
            self.log_debug("  args unequal: %s" % (saved_args != self.sorted_arg_string()))
            return saved_args != self.sorted_arg_string()

    def sorted_args(self, skip=['contents']):
        """
        Returns a list of args in sorted order.
        """
        if not skip:
            skip = []

        sorted_args = []
        for k in sorted(self.args):
            if not k in skip:
                sorted_args.append((k, self.args[k]))
        return sorted_args

    def sorted_arg_string(self):
        """
        Returns a string representation of args in sorted order.
        """
        return unicode(json.dumps(self.sorted_args()))

    def additional_doc_info(self):
        additional_doc_info = []
        for doc in self.additional_docs:
            info = (doc.key, doc.hashid, doc.setting_values())
            additional_doc_info.append(info)
        return additional_doc_info

    def load_additional_docs(self, additional_doc_info):
        for doc_key, hashid, doc_settings in additional_doc_info:
            new_doc = dexy.doc.Doc(doc_key,
                    self.wrapper,
                    [],
                    **doc_settings
                    )
            new_doc.contents = None
            new_doc.args_changed = False
            new_doc.state = 'cached'
            assert new_doc.hashid == hashid

            new_doc.check_is_cached()
            new_doc.consolidate_cache_files()

            new_doc.initial_data.load_data()
            new_doc.output_data().load_data()
            self.add_additional_doc(new_doc)

    def add_additional_doc(self, doc):
        self.log_debug("adding additional doc '%s'" % doc.key)
        doc.created_by_doc = self
        self.children.append(doc)
        self.wrapper.add_node(doc)
        self.wrapper.batch.add_doc(doc)
        self.additional_docs.append(doc)

    def check_cache_elements_present(self):
        """
        Verify that all expected cache files are in fact present.
        """
        return True

    def input_nodes(self, with_parent_inputs = False):
        input_nodes = self.inputs + self.children
        if with_parent_inputs and hasattr(self, 'parent'):
            if not self in self.parent.inputs:
                input_nodes.extend(self.parent.inputs)
        return input_nodes

    def check_is_cached(self):
        if self.state == 'new':
            self.log_debug("checking if %s is changed" % self.key)

            any_inputs_not_cached = False
            for node in self.input_nodes(True):
                node.check_is_cached()
                if not node.state == 'cached':
                    self.log_debug("    input node %s is not cached" % node.key_with_class())
                    any_inputs_not_cached = True

            self.args_changed = self.check_args_changed()
            self.doc_changed = self.check_doc_changed()
            cache_elements_present = self.check_cache_elements_present()
                
            self.log_debug("  doc changed %s" % self.doc_changed)
            self.log_debug("  args changed %s" % self.args_changed)
            self.log_debug("  any inputs not cached %s" % any_inputs_not_cached)
            # log the 'not' so we can search for 'True' in logs to find uncached items
            self.log_debug("  cache elements missing %s" % (not cache_elements_present))

            is_cached = not self.doc_changed and not self.args_changed and not any_inputs_not_cached

            if is_cached and cache_elements_present:
                self.transition('cached')
            else:
                self.transition('uncached')

            # do housekeeping stuff we need to do for every node
            self.wrapper.add_node(self)
            self.wrapper.batch.add_doc(self)

    def load_runtime_info(self):
        pass

    def consolidate_cache_files(self):
        for node in self.input_nodes():
            node.consolidate_cache_files()

        if self.state == 'cached':
            self.transition('consolidated')

    def __lt__(self, other):
        return self.key < other.key

    def __iter__(self):
        def next_task():
            if self.state == 'uncached':
                self.transition('running')
                self.log_info("running...")
                yield self
                self.transition('ran')

            elif self.state in ('consolidated',):
                self.log_info("using cache for self and any children")

            elif self.state in ('ran',):
                self.log_info("already ran in this batch")

            elif self.state == 'running':
                raise dexy.exceptions.CircularDependency(self.key)

            else:
                raise dexy.exceptions.UnexpectedState("%s in %s" % (self.state, self.key))

        return next_task()

    def __call__(self, *args, **kw):
        for inpt in self.inputs:
            for task in inpt:
                task()
        self.wrapper.current_task = self
        self.run()
        self.wrapper.current_task = None

    def run(self):
        """
        Method which processes node's content if not cached, also responsible
        for calling child nodes.
        """
        for child in self.children:
            for task in child:
                task()

class BundleNode(Node):
    """
    Acts as a wrapper for other nodes.
    """
    aliases = ['bundle']

class ScriptNode(BundleNode):
    """
    Represents a bundle of nodes which need to run in order.

    If any of the bundle siblings change, the whole bundle should be re-run.
    """
    aliases = ['script']

    def check_doc_changed(self):
        return any(i.doc_changed for i in self.inputs)

    def setup(self):
        self.script_storage = {}

        siblings = []
        for doc in self.inputs:
            doc.parent = self
            doc.inputs = doc.inputs + siblings
            siblings.append(doc)

#        self.doc_changed = self.check_doc_changed()
#
#        for doc in self.inputs:
#            if not self.doc_changed:
#                assert not doc.doc_changed
#            doc.doc_changed = self.doc_changed

class PatternNode(Node):
    """
    Represents a file matching pattern.

    Creates child Doc objects for each file which matches the pattern.
    """
    aliases = ['pattern']

    def check_doc_changed(self):
        return any(child.doc_changed for child in self.children)

    def setup(self):
        file_pattern = self.key.split("|")[0]
        filter_aliases = self.key.split("|")[1:]

        for filepath, fileinfo in self.wrapper.filemap.iteritems():
            if fnmatch.fnmatch(filepath, file_pattern):
                except_p = self.args.get('except')
                if except_p and re.search(except_p, filepath):
                    msg = "not creating child of patterndoc for file '%s' because it matches except '%s'"
                    msgargs = (filepath, except_p)
                    self.log_debug(msg % msgargs)
                else:
                    if len(filter_aliases) > 0:
                        doc_key = "%s|%s" % (filepath, "|".join(filter_aliases))
                    else:
                        doc_key = filepath

                    msg = "creating child of patterndoc %s: %s"
                    msgargs = (self.key, doc_key)
                    self.log_debug(msg % msgargs)
                    doc = dexy.doc.Doc(doc_key, self.wrapper, [], **self.args)
                    doc.parent = self
                    self.children.append(doc)
                    self.wrapper.add_node(doc)
                    self.wrapper.batch.add_doc(doc)

########NEW FILE########
__FILENAME__ = parser
import copy
import dexy.doc
import dexy.exceptions
import dexy.plugin
import posixpath

class AbstractSyntaxTree():
    def __init__(self, wrapper):
        self.wrapper = wrapper

        self.root_nodes_ordered = False

        self.lookup_table = {}
        self.tree = []

        # Lists of (directory, settings) tuples
        self.default_args_for_directory = []
        self.environment_for_directory = []

    def all_inputs(self):
        """
        Returns a set of all node keys identified as inputs of some other
        element.
        """
        all_inputs = set()
        for kwargs in self.lookup_table.values():
            inputs = kwargs['inputs']
            all_inputs.update(inputs)
        return all_inputs

    def clean_tree(self):
        """
        Removes tasks which are already represented as inputs (tree should
        only contain root nodes).
        """
        treecopy = copy.deepcopy(self.tree)
        all_inputs = self.all_inputs()
        for task in treecopy:
            if task in all_inputs:
                self.tree.remove(task)

    def add_node(self, node_key, **kwargs):
        """
        Adds the node and its kwargs to the tree and lookup table
        """
        node_key = self.wrapper.standardize_key(node_key)

        if not node_key in self.tree:
            self.tree.append(node_key)

        if not self.lookup_table.has_key(node_key):
            self.lookup_table[node_key] = {}

        self.lookup_table[node_key].update(kwargs)

        if not self.lookup_table[node_key].has_key('inputs'):
            self.lookup_table[node_key]['inputs'] = []

        self.clean_tree()
        return node_key

    def add_dependency(self, node_key, input_node_key):
        """
        Adds input_node_key to list of inputs for node_key (both nodes are
        also added to tree).
        """
        node_key = self.add_node(node_key)
        input_node_key = self.add_node(input_node_key)

        if not node_key == input_node_key:
            self.lookup_table[node_key]['inputs'].append(input_node_key)

        self.clean_tree()

    def args_for_node(self, node_key):
        """
        Returns the dict of kw args for a node
        """
        node_key = self.wrapper.standardize_key(node_key)
        args = copy.deepcopy(self.lookup_table[node_key])
        del args['inputs']
        return args

    def inputs_for_node(self, node_key):
        """
        Returns the list of inputs for a node
        """
        node_key = self.wrapper.standardize_key(node_key)
        return self.lookup_table[node_key]['inputs']

    def calculate_default_args_for_directory(self, path):
        dir_path = posixpath.dirname(posixpath.abspath(path))
        default_kwargs = {}

        for d, args in self.default_args_for_directory:
            if posixpath.abspath(d) in dir_path:
                default_kwargs.update(args)

        return default_kwargs

    def calculate_environment_for_directory(self, path):
        dir_path = posixpath.dirname(posixpath.abspath(path))
        env = {}

        for d, args in self.environment_for_directory:
            if posixpath.abspath(d) in dir_path:
                env.update(args)

        return env

    def walk(self):
        """
        Creates Node objects for all elements in tree. Returns a list of root
        nodes and a dict of all nodes referenced by qualified keys.
        """
        if self.wrapper.nodes:
            self.log_warn("nodes are not empty: %s" % ", ".join(self.wrapper.nodes))
        if self.wrapper.roots:
            self.log_warn("roots are not empty: %s" % ", ".join(self.wrapper.roots))

        def create_dexy_node(key, *inputs, **kwargs):
            """
            Stores already created nodes in nodes dict, if called more than
            once for the same key, returns already created node.
            """
            if not key in self.wrapper.nodes:
                alias, pattern = self.wrapper.qualify_key(key)
                node_environment = self.calculate_environment_for_directory(pattern)
                
                kwargs_with_defaults = self.calculate_default_args_for_directory(pattern)
                kwargs_with_defaults.update(kwargs)
                kwargs_with_defaults.update({'environment' : node_environment })

                self.wrapper.log.debug("creating node %s" % alias)
                node = dexy.node.Node.create_instance(
                        alias,
                        pattern,
                        self.wrapper,
                        inputs,
                        **kwargs_with_defaults)

                if node.inputs:
                    self.wrapper.log.debug("inputs are %s" % ", ".join(i.key for i in node.inputs))

                self.wrapper.nodes[key] = node

                for child in node.children:
                    self.wrapper.nodes[child.key_with_class()] = child

            return self.wrapper.nodes[key]

        def parse_item(key):
            inputs = self.inputs_for_node(key)
            kwargs = self.args_for_node(key)
            self.wrapper.log.debug("parsing item %s" % key)
            self.wrapper.log.debug("  inputs: %s" % ", ".join("%r" % inpt for inpt in inputs))
            self.wrapper.log.debug("  kwargs: %s" % ", ".join("%s: %r" % (k, v) for k, v in kwargs.iteritems()))

            if kwargs.get('inactive') or kwargs.get('disabled'):
                return

            matches_target = self.wrapper.target and key.startswith(self.wrapper.target)
            if not kwargs.get('default', True) and not self.wrapper.full and not matches_target:
                return

            input_nodes = [parse_item(i) for i in inputs if i]
            input_nodes = [i for i in input_nodes if i]
    
            return create_dexy_node(key, *input_nodes, **kwargs)

        for node_key in self.tree:
            root_node = parse_item(node_key)
            if root_node:
                self.wrapper.roots.append(root_node)

class Parser(dexy.plugin.Plugin):
    """
    Parse various types of config file.
    """
    aliases = []
    _settings = {}
    __metaclass__ = dexy.plugin.PluginMeta

    def __init__(self, wrapper, ast):
        self.wrapper = wrapper
        self.ast = ast

    def file_exists(self, directory, filename):
        filepath = self.wrapper.join_dir(directory, filename)
        return self.wrapper.file_available(filepath)

    def parse(self, directory, input_text):
        pass

########NEW FILE########
__FILENAME__ = doc
from dexy.parser import Parser
from dexy.utils import parse_json
from dexy.utils import parse_yaml
import dexy.exceptions
import re

class Yaml(Parser):
    """
    Parses YAML configs.
    """
    aliases = ["dexy.yaml", "docs.yaml"]

    def parse(self, directory, input_text):
        def parse_key_mapping(mapping):
            for original_node_key, v in mapping.iteritems():
                # handle things which aren't nodes
                if original_node_key == 'defaults':
                    self.ast.default_args_for_directory.append((directory, v,))
                    continue

                # handle nodes
                original_file = original_node_key.split("|")[0]

                orig_exists = self.file_exists(directory, original_file) 
                star_in_key = "*" in original_node_key
                dot_in_key = "." in original_node_key
                pipe_in_key = "|" in original_node_key

                treat_key_as_bundle_name = not orig_exists and not star_in_key and not dot_in_key and not pipe_in_key

                if treat_key_as_bundle_name:
                    node_key = original_node_key
                else:
                    node_key = self.wrapper.join_dir(directory, original_node_key)

                # v is a sequence whose members may be children or kwargs
                if not v:
                    raise dexy.exceptions.UserFeedback("Empty doc config for %s" % node_key)

                if hasattr(v, 'keys'):
                    raise dexy.exceptions.UserFeedback("You passed a dict to %s, please pass a sequence" % node_key)

                siblings = []
                for element in v:
                    if hasattr(element, 'keys'):
                        # This is a dict of length 1
                        kk = element.keys()[0]
                        vv = element[kk]

                        if isinstance(vv, list):
                            # This is a sequence. It probably represents a
                            # child task but if starts with 'args' or if it
                            # matches a filter alias for the parent doc, then
                            # it is nested complex kwargs.
                            if kk == "args" or (kk in node_key.split("|")):
                                # nested complex kwargs
                                for vvv in vv:
                                    self.ast.add_node(node_key, **vvv)

                            else:
                                # child task. we note the dependency, add
                                # dependencies on prior siblings, and recurse
                                # to process the child.
                                self.ast.add_dependency(node_key, self.wrapper.join_dir(directory, kk))

                                if self.wrapper.siblings:
                                    for s in siblings:
                                        self.ast.add_dependency(self.wrapper.join_dir(directory, kk), s)
                                    siblings.append(self.wrapper.join_dir(directory, kk))

                                parse_key_mapping(element)

                        else:
                            # This is a key:value argument for this task
                            self.ast.add_node(node_key, **element)

                    else:
                        # This is a child task with no args, we only have to
                        # note the dependencies
                        self.ast.add_dependency(node_key, self.wrapper.join_dir(directory, element))
                        if self.wrapper.siblings:
                            for s in siblings:
                                self.ast.add_dependency(self.wrapper.join_dir(directory, element), s)
                            siblings.append(self.wrapper.join_dir(directory, element))

        def parse_keys(data, top=False):
            if hasattr(data, 'keys'):
                parse_key_mapping(data)
            elif isinstance(data, basestring):
                self.ast.add_node(self.wrapper.join_dir(directory, data))
            elif isinstance(data, list):
                if top:
                    self.ast.root_nodes_ordered = True
                for element in data:
                    parse_keys(element)
            else:
                raise Exception("invalid input %s" % data)

        config = parse_yaml(input_text)
        parse_keys(config, top=True)

class TextFile(Parser):
    """
    parses plain text configs
    """
    aliases = ["dexy.txt", "docs.txt"]

    def parse(self, directory, input_text):
        for line in input_text.splitlines():
            line = line.strip()

            # Throw away comments.
            if "#" in line:
                if line.startswith("#"):
                    line = ''
                else:
                    line = line.split("#", 0)

            if not re.match("^\s*$", line):
                if "{" in line:
                    # We have a task + some JSON arguments
                    key, raw_args = line.split("{", 1)
                    key = key.strip()
                    kwargs = parse_json("{" + raw_args)
                else:
                    key = line
                    kwargs = {}

                node_key = self.wrapper.join_dir(directory, key)
                self.ast.add_node(node_key, **kwargs)
                # all tasks already in the ast are children
                for child_key in self.ast.lookup_table.keys():
                    child_node_key = self.wrapper.join_dir(directory, child_key)
                    self.ast.add_dependency(node_key, child_node_key)

class Original(Parser):
    """
    parses JSON config files like .dexy
    """
    aliases = ["dexy.json", "docs.json", ".dexy"]

    def parse(self, directory, input_text):
        data = parse_json(input_text)

        for task_key, v in data.iteritems():
            self.ast.add_node(self.wrapper.join_dir(directory, task_key))

            for kk, vv in v.iteritems():
                if kk == 'depends':
                    for child_key in vv:
                        self.ast.add_dependency(self.wrapper.join_dir(directory, task_key), self.wrapper.join_dir(directory, child_key))
                else:
                    task_kwargs = {kk : vv}
                    self.ast.add_node(self.wrapper.join_dir(directory, task_key), **task_kwargs)

        def children_for_allinputs(priority=None):
            children = []
            for k, v in self.ast.lookup_table.iteritems():
                if 'allinputs' in v:
                    if priority:
                        k_priority = v.get('priority', 10)
                        if k_priority < priority:
                            children.append(k)
                else:
                    children.append(k)
            return children

        # Make another pass to implement 'allinputs'
        for task_key, kwargs in self.ast.lookup_table.iteritems():
            if kwargs.get('allinputs', False):
                priority = kwargs.get('priority')
                for child_key in children_for_allinputs(priority):
                    # These keys are already adjusted for directory.
                    self.ast.add_dependency(task_key, child_key)

########NEW FILE########
__FILENAME__ = environment
from dexy.parser import Parser
from dexy.utils import parse_json

class Environment(Parser):
    """
    Parent class for environment parsers.
    """
    @classmethod
    def parse_environment_from_text(klass, text):
        pass

    def parse(self, parent_dir, config_text):
        config = self.parse_environment_from_text(config_text)
        self.ast.environment_for_directory.append((parent_dir, config,))

class JsonEnvironment(Environment):
    """
    Loads environment variables from a JSON file.
    """
    aliases = ['dexy-env.json']

    @classmethod
    def parse_environment_from_text(klass, text):
        return parse_json(text)

class PythonEnvironment(Environment):
    """
    Loads environment variables from a python script.
    """
    aliases = ['dexy-env.py']

    @classmethod
    def parse_environment_from_text(klass, text):
        env = {}
        skip = ('env', 'skip', 'self', 'parent_dir', 'env_text')

        exec text

        for k, v in locals().iteritems():
            if not k in skip:
                env[k] = v
        return env

########NEW FILE########
__FILENAME__ = plugin
import cashew
from cashew import Plugin

class PluginMeta(cashew.PluginMeta):
    """
    PluginMeta customized for dexy.
    """
    _store_other_class_settings = {} # allow plugins to define settings for other classes
    official_dexy_plugins = ("dexy_templates", "dexy_viewer", "dexy_filter_examples")

    def load_class_from_locals(cls, class_name):
        from dexy.template import Template
        from dexy.filters.pexp import PexpectReplFilter
        from dexy.filters.process import SubprocessCompileFilter
        from dexy.filters.process import SubprocessCompileInputFilter
        from dexy.filters.process import SubprocessExtToFormatFilter
        from dexy.filters.process import SubprocessFilter
        from dexy.filters.process import SubprocessFormatFlagFilter
        from dexy.filters.process import SubprocessInputFileFilter
        from dexy.filters.process import SubprocessInputFilter
        from dexy.filters.process import SubprocessStdoutFilter
        from dexy.filters.process import SubprocessStdoutTextFilter
        from dexy.filters.standard import PreserveDataClassFilter
        return locals()[class_name]

    def apply_prefix(cls, modname, alias):
        if modname.startswith("dexy_") and not modname in PluginMeta.official_dexy_plugins:
            prefix = modname.split(".")[0].replace("dexy_", "")
            return "%s:%s" % (prefix, alias)
        else:
            return alias 

    def adjust_alias(cls, alias):
        """
        All of '-' or '-foo' or '---' should map to '-' which is a registered alias.

        This way we can always create unique names by including arbitrary
        distinguishing content after a '-'.
        """
        if alias.startswith('-'):
            alias = '-'
        return alias

class Command(Plugin):
    """
    Parent class for custom dexy commands.
    """
    __metaclass__ = PluginMeta
    _settings = {}
    aliases = []
    default_cmd = None
    namespace = None

class TemplatePlugin(Plugin):
    """
    Parent class for template plugins.
    """
    __metaclass__ = PluginMeta
    aliases = []
    _settings = {
            'no-jinja-filter' : ("Listed entries should not be made into jinja filters.")
            }

    def is_active(self):
        return True

    def __init__(self, filter_instance=None):
        if filter_instance:
            self.filter_instance = filter_instance

    def run(self):
        return {}

########NEW FILE########
__FILENAME__ = reporter
from dexy.utils import file_exists
import dexy.plugin
import os
import shutil
import sys

class Reporter(dexy.plugin.Plugin):
    """
    Base class for types of reporter.
    """
    __metaclass__ = dexy.plugin.PluginMeta

    _settings = {
            "default" : ("""Whether to run this report by default. Should be
            False for reports with side effects.""", True),
            "dir" : ("""Directory where report output will be written.""",
                None),
            'filename' : ("""Name of report file to generate (used when the
                report consists of just a single file).""", None),
            "in-cache-dir" : ("""Whether to create report dir in the cache
                directory (instead of project root).""", False),
            'no-delete' : ("""List of file names not to delete when resetting
                report dir (only effective if report dir is cleaned
                element-wise).""", ['.git', '.nojekyll']),
            'plugins' : ("""List of template plugin aliases which should be
                included in jinja environment.""",
                ['debug', 'inflection', 'builtins', 'operator', 'datetime',
                    'pprint', 'pygments', 'markdown']
                ),
            "run-for-wrapper-states" : ("""Wrapper states for which report is
                valid.""", ["ran"]),
            "readme-filename" : ("Name of README file, or None to omit." ,
                "README.md"),
            "readme-contents" : ("Contents to be written to README file." ,
                "This directory was generated by the %(alias)s dexy reporter and may be deleted without notice.\n"),
            "safety-filename" : ("""Name of a file which will be created in
                generated dir to indicate it was created by dexy and is safe to
                auto-remove.""", ".dexy-generated"), }

    def is_active(self):
        return True

    def help(self):
        """
        Allow implementing custom help since reporters can have such different behavior.
        """
        pass

    def copy_template_files(self):
        # Copy template files (e.g. .css files)
        # TODO shouldn't need to copy this each time - can just overwrite files which change
        class_file = sys.modules[self.__module__].__file__
        template_parent_dir = os.path.dirname(class_file)
        template_dir = os.path.join(template_parent_dir, 'files')
        shutil.copytree(template_dir, self.report_dir())
        self.write_safety_file()

    def run_plugins(self):
        env = {}
        for alias in self.setting('plugins'):
            from dexy.filters.templating_plugins import TemplatePlugin
            plugin = TemplatePlugin.create_instance(alias)
            self.log_debug("Running template plugin %s" % plugin.__class__.__name__)

            try:
                new_env_vars = plugin.run()
            except Exception:
                print "error occurred processing template plugin '%s'" % alias
                raise

            if any(v in env.keys() for v in new_env_vars):
                new_keys = ", ".join(sorted(new_env_vars))
                existing_keys = ", ".join(sorted(env))
                msg = "plugin class '%s' is trying to add new keys '%s', already have '%s'"
                raise dexy.exceptions.InternalDexyProblem(msg % (plugin.__class__.__name__, new_keys, existing_keys))
            env.update(new_env_vars)
        return env

    def template_data(self):
        return dict((k, v[1]) for k, v in self.run_plugins().iteritems())

    def cache_reports_dir(self):
        return os.path.join(self.wrapper.artifacts_dir, "reports")

    def report_dir(self):
        """
        Returns path of report directory relative to dexy project root.
        """
        if not self.setting('dir'):
            return None
        elif self.setting('in-cache-dir'):
            return os.path.join(self.cache_reports_dir(), self.setting('dir'))
        else:
            return self.setting('dir')

    def report_file(self):
        if self.setting('dir'):
            return os.path.join(self.report_dir(), self.setting('filename'))
        else:
            if self.setting('in-cache-dir'):
                return os.path.join(self.cache_reports_dir(), self.setting('filename'))
            else:
                return self.setting('dir')

    def key_for_log(self):
        return "reporter:%s" % self.aliases[0]

    def log_debug(self, message):
        self.wrapper.log.debug("%s: %s" % (self.key_for_log(), message))

    def log_info(self, message):
        self.wrapper.log.info("%s: %s" % (self.key_for_log(), message))

    def log_warn(self, message):
        self.wrapper.log.warn("%s: %s" % (self.key_for_log(), message))

    def safety_filepath(self):
        return os.path.join(self.report_dir(), self.setting('safety-filename'))

    def readme_filepath(self):
        readme_filename = self.setting('readme-filename')
        if readme_filename and readme_filename != 'None':
            return os.path.join(self.report_dir(), readme_filename)

    def write_safety_file(self):
        with open(self.safety_filepath(), "w") as f:
            f.write("""
            This directory was generated by the %s Dexy Reporter and
            may be deleted without notice.\n\n""" % self.__class__.__name__)

    def write_readme_file(self):
        with open(self.readme_filepath(), "w") as f:
            f.write(self.setting('readme-contents') % self.settings_and_attributes())

    def create_cache_reports_dir(self):
        if not file_exists(self.cache_reports_dir()):
            os.makedirs(self.cache_reports_dir())

    def create_reports_dir(self):
        if not self.report_dir():
            return False

        if not file_exists(self.report_dir()):
            os.makedirs(self.report_dir())

        self.write_safety_file()
        if self.readme_filepath():
            self.write_readme_file()

    def remove_reports_dir(self, wrapper, keep_empty_dir=False):
        self.wrapper = wrapper
        if not self.report_dir():
            return False

        if file_exists(self.report_dir()) and not file_exists(self.safety_filepath()):
            msg = """Please remove directory %s, Dexy wants to write a report
            here but there's already a file or directory in this location."""
            msgargs = (os.path.abspath(self.report_dir()),)
            raise dexy.exceptions.UserFeedback(msg % msgargs)
        elif file_exists(self.report_dir()):
            if keep_empty_dir:
                # Does not remove the base directory, useful if you are running
                # a process (like 'dexy serve') from inside that directory
                for f in os.listdir(self.report_dir()):
                    if not f in self.setting('no-delete'):
                        path = os.path.join(self.report_dir(), f)
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                        else:
                            os.remove(path)
                self.write_safety_file()
            else:
                shutil.rmtree(self.report_dir())

    def run(self, wrapper):
        pass

########NEW FILE########
__FILENAME__ = graphviz
from dexy.reporter import Reporter

class Graphviz(Reporter):
    """
    Emits a graphviz graph of the network structure.
    """
    aliases = ['graphviz', 'nodegraph']
    _settings = {
            'in-cache-dir' : True,
            'filename' : 'graph.dot',
            "run-for-wrapper-states" : ["ran", "checked", "error"]
            }

    def run(self, wrapper):
        self.wrapper = wrapper
        def print_children(node, indent=0):
            content = []
            content.append(node.key)
            for child in node.children:
                for line in print_children(child, indent+1):
                    content.append(line)
            return content

        def print_inputs(node):
            content = []
            for child in node.inputs:
                content.extend(print_inputs(child))
                content.append("\"%s\" -> \"%s\";" % (node, child))
            return content

        graph = []
        graph.append("digraph G {")
        for node in wrapper.nodes.values():
            graph.extend(print_inputs(node))
        graph.append("}")

        self.create_cache_reports_dir()
        with open(self.report_file(), "w") as f:
            f.write("\n".join(graph))


########NEW FILE########
__FILENAME__ = text
from dexy.reporter import Reporter

class PlainTextGraph(Reporter):
    """
    Emits a plain text graph of the network structure.
    """
    aliases = ['graph']
    _settings = {
            'in-cache-dir' : True,
            'filename' : 'graph.txt',
            "run-for-wrapper-states" : ["ran", "checked"]
            }

    def run(self, wrapper):
        self.wrapper = wrapper

        def print_inputs(node, indent=0):
            content = []

            s = " " * indent * 4
            content.append("%s%s (%s)" % (s, node, node.state))

            for child in list(node.inputs) + node.children:
                content.extend(print_inputs(child, indent+1))
            return content

        graph = []
        for node in wrapper.roots:
            graph.extend(print_inputs(node))

        self.create_cache_reports_dir()
        with open(self.report_file(), "w") as f:
            f.write("\n".join(graph) + "\n")

########NEW FILE########
__FILENAME__ = output
from dexy.reporter import Reporter
import os

class Output(Reporter):
    """
    Creates canonical dexy output with files given short filenames.
    """
    aliases = ['output']
    _settings = {
            'dir' : 'output'
            }

    def write_canonical_data(self, doc):
        output_name = doc.output_data().output_name()

        if output_name:
            fp = os.path.join(self.setting('dir'), output_name)

            if fp in self.locations:
                self.log_warn("WARNING overwriting file %s" % fp)
            else:
                self.locations[fp] = []
            self.locations[fp].append(doc.key)

            parent_dir = os.path.dirname(fp)
            try:
                os.makedirs(parent_dir)
            except os.error:
                pass

            self.log_debug("  writing %s to %s" % (doc.key, fp))

            doc.output_data().output_to_file(fp)

    def run(self, wrapper):
        self.wrapper=wrapper
        self.locations = {}

        self.remove_reports_dir(self.wrapper, keep_empty_dir=True)
        self.create_reports_dir()
        for doc in wrapper.nodes.values():
            if not doc.key_with_class() in wrapper.batch.docs:
                continue
            if not doc.state in ('ran', 'consolidated'):
                continue
            if not hasattr(doc, 'output_data'):
                continue

            if doc.output_data().is_canonical_output():
                self.write_canonical_data(doc)

class LongOutput(Reporter):
    """
    Creates complete dexy output with files given long, unique filenames.
    """
    aliases = ['long']
    _settings = {
            'default' : False,
            'dir' : 'output-long'
            }

    def run(self, wrapper):
        self.wrapper=wrapper
        self.create_reports_dir()
        for doc in wrapper.nodes.values():
            if not doc.key_with_class() in wrapper.batch.docs:
                continue
            if not doc.state in ('ran', 'consolidated'):
                continue
            if not hasattr(doc, 'output_data'):
                continue

            fp = os.path.join(self.setting('dir'), doc.output_data().long_name())

            try:
                os.makedirs(os.path.dirname(fp))
            except os.error:
                pass

            self.log_debug("  writing %s to %s" % (doc.key, fp))
            doc.output_data().output_to_file(fp)

########NEW FILE########
__FILENAME__ = classes
from dexy.reporter import Reporter
from dexy.doc import Doc
from jinja2 import Environment
from jinja2 import FileSystemLoader
import operator
import os
import random
import shutil
import codecs

def link_to_doc(node):
    return """&nbsp;<a href="#%s">&darr; doc info</a>""" % node.output_data().websafe_key()

def link_to_doc_if_doc(node):
    if isinstance(node, Doc):
        return link_to_doc(node)
    else:
        return ""

class RunReporter(Reporter):
    """
    Returns info about a dexy run.
    """
    aliases = ['run']
    _settings = {
            'in-cache-dir' : True,
            'dir' : 'run',
            'filename' : 'index.html',
            'default' : True,
            "run-for-wrapper-states" : ["ran", "error"]
            }

    def run(self, wrapper):
        self.wrapper = wrapper
        self.remove_reports_dir(wrapper)
        self.copy_template_files()

        # If not too large, copy the log so it can be viewed in HTML
        self.wrapper.flush_logs()
        if os.path.getsize(self.wrapper.log_path()) < 500000:
            with codecs.open(self.wrapper.log_path(), 'r', encoding='UTF-8') as f:
                log_contents = f.read()
        else:
            log_contents = "Log file is too large to include in HTML. Look in %s" % self.wrapper.log_path()

        env_data = self.template_data()

        # add additional env elements - should these also be in plugins?
        env_data['wrapper'] = wrapper
        env_data['batch'] = wrapper.batch
        env_data['log_contents'] = log_contents

        def printable_args(args):
            return dict((k, v) for k, v in args.iteritems() if not k in ('contents', 'wrapper'))

        def print_children(node, indent=0, extra=""):
            rand_id = random.randint(10000000,99999999)
            spaces = " " * 4 * indent
            nbspaces = "&nbsp;" * 4 * indent
            content = ""

            node_div = """%s<div data-toggle="collapse" data-target="#%s">%s%s%s%s</div>"""
            node_div_args = (spaces, rand_id, nbspaces, extra,
                    node.key_with_class(), link_to_doc_if_doc(node),)

            content += node_div % node_div_args
            content += """  %s<div id="%s" class="collapse">""" % (spaces, rand_id)

            for child in list(node.inputs):
                if not "Artifact" in child.__class__.__name__:
                    content += print_children(child, indent+1, "&rarr;")

            for child in node.children:
                if not "Artifact" in child.__class__.__name__:
                    content += print_children(child, indent+1)

            content += "  %s</div>" % spaces
            return content 

        env_data['print_children'] = print_children
        env_data['printable_args'] = printable_args

        env = Environment()
        env.loader = FileSystemLoader(os.path.dirname(__file__))
        template = env.get_template('template.html')

        template.stream(env_data).dump(self.report_file(), encoding="utf-8")

########NEW FILE########
__FILENAME__ = classes
from dexy.commands.utils import print_indented
from dexy.reporters.output import Output
from dexy.utils import file_exists
from dexy.utils import iter_paths
from dexy.utils import reverse_iter_paths
from functools import partial
from jinja2 import Environment
from jinja2 import FileSystemLoader
import dexy.data
import dexy.exceptions
import dexy.filters.templating_plugins
import inspect
import jinja2
import os
import posixpath
import urlparse

class Website(Output):
    """
    Applies a template to create a website from your dexy output.

    Templates are applied to all files with .html extension which don't already
    contain "<head" or "<body" tags.
    """
    aliases = ['ws']
    _other_class_settings = {
        'doc' : {
            'apply-ws-to-content' : ("""
                If you want to put website-related content (like the link()
                function) in your content, set this to True so your content
                gets put through the jinja filter for the website reporter.
                """,
                False
            ),
            'apply-ws-to-content-var-start-string' : ("""
                Provide a custom jinja var-start-string to avoid clashes.
                """,
                None
            ),
            'apply-ws-to-content-var-end-string' : ("""
                Provide a custom jinja var-end-string to avoid clashes.
                """,
                None
                ),
            'ws-template' : (
                """
                Key of the template to apply for rendering in website.
                Setting of 'None' will use default template, 'False' will
                force no template to be used.
                """,
                None)
            },
        'data' : {
            'ws-template' : (
                """
                Key of the template to apply for rendering in website.
                Setting of 'None' will use default template, 'False' will
                force no template to be used.
                """,
                None)
            }
        }

    _settings = {
        "dir" : "output-site",
        "default-template" : ("Path to the default template to apply.", "_template.html"),
        "default" : False
    }

    def run(self, wrapper):
        self.wrapper=wrapper

        self.remove_reports_dir(self.wrapper, keep_empty_dir=True)
        self.create_reports_dir()

        self.setup()

        if self.wrapper.target:
            msg = "Not running website reporter because a target has been specified."
            self.log_warn(msg)
            return

        for doc in wrapper.nodes.values():
            if self.should_process(doc):
                self.process_doc(doc)

        self.log_debug("finished")

    def setup(self):
        self.keys_to_outfiles = []
        self.locations = {}
        self.create_reports_dir()
        self.setup_navobj()

    def setup_navobj(self):
        self._navobj = self.create_navobj()

    def should_process(self, doc):
        if not doc.key_with_class() in self.wrapper.batch.docs:
            return False
        elif not doc.state in ('ran', 'consolidated'):
            return False
        elif not hasattr(doc, 'output_data'):
            return False
        elif not doc.output_data().output_name():
            return False
        elif not doc.output_data().is_canonical_output():
            msg = "skipping %s - not canonical"
            self.log_debug(msg % doc.key)
            return False
        else:
            return True

    def process_doc(self, doc):
        self.log_debug("processing %s" % doc.key)

        output_ext = doc.output_data().ext

        if output_ext == ".html":
            self.process_html(doc)

        elif isinstance(doc.output_data(), dexy.data.Sectioned):
            assert output_ext == ".json"
            self.apply_and_render_template(doc)

        else:
            self.write_canonical_data(doc)

    def process_html(self, doc):
        if doc.setting('ws-template') == False:
            self.log_debug("  ws-template is False for %s" % doc.key)
            self.write_canonical_data(doc)

        elif self.detect_html_header(doc) and not doc.setting('ws-template'):
            self.log_debug("  found html tag in output of %s" % doc.key)
            self.write_canonical_data(doc)

        else:
            self.apply_and_render_template(doc)

    def detect_html_header(self, doc):
        fragments = ('<html', '<body', '<head')
        return any(html_fragment
                      in unicode(doc.output_data())
                      for html_fragment in fragments)

    def create_navobj(self):
        navobj = Navigation()
        navobj.populate_lookup_table(self.wrapper.batch)
        navobj.walk()
        return navobj

    def template_file_and_path(self, doc):
        ws_template = doc.setting('ws-template')
        if ws_template and not isinstance(ws_template, bool):
            template_file = ws_template
        else:
            template_file = self.setting('default-template')

        template_path = None
        for subpath in reverse_iter_paths(doc.name):
            template_path = os.path.join(subpath, template_file)
            if file_exists(template_path):
                break

        if not template_path:
            msg = "no template path for %s" % doc.key
            raise dexy.exceptions.UserFeedback(msg)
        else:
            msg = "  using template %s for %s"
            msgargs = (template_path, doc.key)
            self.log_debug(msg % msgargs)

        return (template_file, template_path,)

    def jinja_environment(self, template_path, additional_args=None):
        """
        Returns jinja Environment object.
        """
        args = {
                'undefined' : jinja2.StrictUndefined
                }

        if additional_args:
            args.update(additional_args)

        env = Environment(**args)

        dirs = [".", os.path.dirname(__file__), os.path.dirname(template_path)]
        env.loader = FileSystemLoader(dirs)

        return env

    def apply_jinja_to_page_content(self, doc, env_data):
        args = {
                'undefined' : jinja2.StrictUndefined
                }

        keys = ['variable_start_string', 'variable_end_string',
                'block_start_string', 'block_end_string']


        for k in keys:
            setting_name = "apply-ws-to-content-%s" % k.replace("_", "-")
            if doc.safe_setting(setting_name):
                args[k] = doc.setting(setting_name)

        env = Environment(**args)

        self.log_debug("Applying jinja to doc content %s" % doc.key)
        try:
            content_template = env.from_string(unicode(doc.output_data()))
            return content_template.render(env_data)
        except Exception:
            self.log_debug("Template:\n%s" % unicode(doc.output_data()))
            self.log_debug("Env args:\n%s" % args)
            raise

    def template_environment(self, doc, template_path):
        raw_env_data = self.run_plugins()
        raw_env_data.update(self.website_specific_template_environment(doc.output_data(), {
            'template_source' : ("The directory containing the template file used.",
                template_path)
            }))

        env_data = dict((k, v[1]) for k, v in raw_env_data.iteritems())

        if doc.safe_setting('apply-ws-to-content'):
            env_data['content'] = self.apply_jinja_to_page_content(doc, env_data)
        else:
            env_data['content'] = doc.output_data()

        return env_data

    def fix_ext(self, filename):
        basename, ext = os.path.splitext(filename)
        return "%s.html" % basename

    def apply_and_render_template(self, doc):
        template_info = self.template_file_and_path(doc)
        template_file, template_path = template_info
        env_data = self.template_environment(doc, template_path)

        self.log_debug("  creating jinja environment")
        env = self.jinja_environment(template_path)

        self.log_debug("  loading jinja template at %s" % template_path)
        template = env.get_template(template_path)
       
        output_file = self.fix_ext(doc.output_data().output_name())
        output_path = os.path.join(self.setting('dir'), output_file)

        try:
            os.makedirs(os.path.dirname(output_path))
        except os.error:
            pass

        self.log_debug("  writing to %s" % (output_path))
        template.stream(env_data).dump(output_path, encoding="utf-8")

    def help(self, data):
        nodoc = ('navobj', 'navigation',)
        print_indented("Website Template Environment Variables:", 4)
        print ''
        print_indented("Navigation and Content Related:", 6)
        env = self.website_specific_template_environment(data)
        for k in sorted(env):
            if k in nodoc:
                continue
            docs, value = env[k]
            print_indented("%s: %s" % (k, docs), 8)

        print ''
        navobj = env['navobj'][1]
        root = navobj.nodes['/']
        members = [(name, obj) for name, obj in inspect.getmembers(root)
                if not name.startswith('__')]

        print_indented("navobj Node attributes (using root node):", 6)
        print ''
        for member_name, member_obj in members:
            if not inspect.ismethod(member_obj):
                print_indented("%s: %r" % (member_name, member_obj), 8)
       
        print ''

        print_indented("navobj Node methods (using root node):", 6)
        print ''
        for member_name, member_obj in members:
            if inspect.ismethod(member_obj):
                print_indented("%s()" % (member_name), 8)
                print_indented("%s" % inspect.getdoc(member_obj), 10)
                print_indented("%s" % member_obj(), 10)
                print ''

        print ''
        print_indented("Variables From Plugins:", 6)
        env = self.run_plugins()
        for k in sorted(env):
            docs, value = env[k]
            print_indented("%s: %s" % (k, docs), 8)

        print ''
        print_indented("navobj Nodes:", 4)
        print_indented(navobj.debug(), 6)

    def website_specific_template_environment(self, data, initial_args=None):
        env_data = {}

        if initial_args:
            env_data.update(initial_args)

        current_dir = posixpath.dirname(data.output_name())
        parent_dir = os.path.split(current_dir)[0]

        env_data.update({
                'link' : ("Function to create link to other page.",
                    partial(self.link, data)),
                'section' : ("Function to create link to section on any page.",
                    partial(self.section, data)),
                'navigation' : ("DEPRECATED. 'navigation' object.",
                    {}),
                'nav' : ("The node for the current document's directory.",
                    self._navobj.nodes["/%s" % current_dir]),
                'root' : ("The root node of the navigation tree.",
                    self._navobj.nodes["/"]),
                'navobj' : ("DEPRECATED. Same as 'navtree'.",
                    self._navobj),
                'navtree' : ("The complete navigation tree for the website.",
                    self._navobj),
                'page_title' : ("Title of the current page.",
                    data.title()),
                'title' : ("Title of the current page.",
                    data.title()),
                'parent_dir' : ("The directory one level up from the document being processed.",
                    parent_dir),
                'current_dir' : ("The directory containing the document being processed.",
                    current_dir),
                's' : ("'%s' type data object representing the current doc." % data.alias,
                    data),
                'd' : ("'%s' type data object representing the current doc." % data.alias,
                    data),
                'source' : ("Output name of current doc.",
                    data.output_name()),
                'wrapper' : ("The current wrapper object.",
                    self.wrapper)
                })

        return env_data

    def section(self, data, section_name=None, url_base=None, link_text = None):
        """
        Returns an HTML link to section without needing to specify which
        document it is in (section name must be globally unique).
        """
        matching_nodes = self.wrapper.lookup_sections.get(section_name)

        if not matching_nodes:
            msg = "Trying to create a link in %s but no section found matching '%s'"
            msgargs = (data.key, section_name,)
            raise dexy.exceptions.UserFeedback(msg % msgargs)
        elif len(matching_nodes) > 1:
            # TODO make it an option to select a default where there is
            # more than one option
            msg = "Trying to create a link in %s to '%s' but multiple docs match."
            msgargs = (data.key, section_name,)
            raise dexy.exceptions.UserFeedback(msg % msgargs)

        assert len(matching_nodes) == 1
        link_to_data = matching_nodes[0]
        section = link_to_data[section_name]
        anchor = section['id']
        if not link_text:
            link_text = section_name

        return self.link_for(url_base, data.relative_path_to(link_to_data.output_name()), link_text, anchor)

    def link(self, data, doc_key, section_name=None, url_base=None, link_text = None, description=False):
        """
        Returns an HTML link to document, optionally with an anchor linking to section.
        """
        matching_nodes = self.wrapper.lookup_nodes.get(doc_key)

        if not matching_nodes:
            msg = "Trying to create a link in %s but no doc found matching '%s'"
            msgargs = (data.key, doc_key,)
            raise dexy.exceptions.UserFeedback(msg % msgargs)
        elif len(matching_nodes) > 1:
            # TODO make it an option to select a default where there is
            # more than one option
            msg = "Trying to create a link to '%s' but multiple docs match."
            msgargs = (doc_key,)
            raise dexy.exceptions.UserFeedback(msg % msgargs)

        assert len(matching_nodes) == 1
        link_to_data = matching_nodes[0]
        anchor = None

        if section_name:
            if section_name in link_to_data.keys():
                section = link_to_data[section_name]
                anchor = section['id']
                if not link_text:
                    link_text = section_name
            else:
                msg = "Did not find section named '%s' in '%s'"
                msgargs = (section_name, doc_key)
                raise dexy.exceptions.UserFeedback(msg % msgargs)
        else:
            if not link_text:
                link_text = link_to_data.title()


        relative_link_to = data.relative_path_to(link_to_data.output_name())

        link_html = self.link_for(url_base, relative_link_to, link_text, anchor)

        if description and link_to_data.safe_setting('description'):
            return "%s\n<p>%s</p>" % (link_html, link_to_data.setting('description'))
        else:
            return link_html

    def link_for(self, url_base, link, link_text, anchor=None):
        if url_base:
            url = urlparse.urljoin(url_base, link)
        else:
            url = link
        if anchor:
            return """<a href="%s#%s">%s</a>""" % (url, anchor, link_text)
        else:
            return """<a href="%s">%s</a>""" % (url, link_text)

class Navigation(object):
    def __init__(self):
        self.lookup_table = {}
        self.nodes = {}
        self.root = None

    def populate_lookup_table(self, batch):
        for data in batch:
            if not data.output_name():
                continue

            parent_dir = "/" + os.path.dirname(data.output_name())
            if not self.lookup_table.has_key(parent_dir):
                self.lookup_table[parent_dir] = {'docs' : []}

            if data.is_canonical_output():
                self.lookup_table[parent_dir]['docs'].append(data)

            if data.is_index_page():
                self.lookup_table[parent_dir]['index-page'] = data

    def walk(self):
        """
        Build nodes dict from already-populated lookup table.
        """
        for path, info in self.lookup_table.iteritems():
            parent = None
            ancestors = []
            level = 0
            for parent_path in iter_paths(path):
                if not self.nodes.has_key(parent_path):
                    node = Node(parent_path, parent, [])
                    node.level = level
                    self.nodes[parent_path] = node
                    if parent:
                        parent.children.append(node)

                    if not self.root and parent_path == '/':
                        self.root = node

                parent = self.nodes[parent_path]
                ancestors.append(parent)
                level += 1

            assert parent.location == path
            parent.ancestors = ancestors
            parent.docs = info['docs']
            if info.has_key('index-page'):
                parent.index_page = info['index-page']

    def debug(self):
        """
        Returns a dump of useful information.
        """
        info = []
        for path in sorted(self.nodes):
            node = self.nodes[path]

            info.append('')
            info.append("node: %s" % path)

            if node.index_page:
                info.append("  index-page:")
                info.append("    %s" % node.index_page.key)
                info.append('')
            else:
                info.append("  no index page.")
                info.append('')

            if node.docs:
                info.append("  docs:")
            for child in node.docs:
                info.append("    %s" % child.key)
            info.append('')

            if node.children:
                info.append("  children:")

            for child in node.children:
                info.append("    %s" % child.location)
            info.append('')
        return "\n".join(info)

class Node(object):
    """
    Wrapper class for a location in the site hierarchy.
    """
    def __init__(self, location, parent, children):
        if parent:
            assert isinstance(parent, Node)
        if children:
            assert isinstance(children[0], Node)
        self.location = location
        self.parent = parent
        self.children = children
        self.ancestors = []
        self.docs = []
        self.index_page = None

    def __lt__(self, other):
        return self.location < other.location

    def __repr__(self):
        return "Node(%s)" % self.location

    def has_children_with_index_pages(self):
        """
        Boolean value.
        """
        return any(node.index_page for node in self.children)

    def breadcrumbs(self, divider = " &gt; "):
        """
        Navigation breadcrumbs showing each parent directory.
        """
        return divider.join("""<a href="%s">%s</a>""" % (node.location, node.index_page.title()) for node in self.ancestors if node.index_page)

########NEW FILE########
__FILENAME__ = storage
from dexy.exceptions import UserFeedback
from dexy.exceptions import InternalDexyProblem
from dexy.utils import file_exists
import dexy.exceptions
import dexy.plugin
import os
import shutil
import sqlite3

class Storage(dexy.plugin.Plugin):
    """
    Base class for types of Storage.
    """
    __metaclass__ = dexy.plugin.PluginMeta
    _settings = {}

    def assert_location_is_in_project_dir(self, filepath):
        if not self.wrapper.is_location_in_project_dir(filepath):
            msg = "trying to write '%s' outside of '%s'"
            msgargs = (filepath, self.wrapper.project_root,)
            raise dexy.exceptions.UserFeedback(msg % msgargs)

    def __init__(self, storage_key, ext, wrapper):
        self.storage_key = storage_key
        self.ext = ext
        self.wrapper = wrapper
        self._size = None

    def setup(self):
        pass

    def connect(self):
        pass

class GenericStorage(Storage):
    """
    Default type of storage where content is stored in files.
    """
    aliases = ['generic']

    def data_file(self, read=True):
        """
        Location of data file.
        """
        if read:
            if os.path.exists(self.this_data_file()):
                return self.this_data_file()
            elif os.path.exists(self.last_data_file()):
                return self.last_data_file()
            else:
                return self.this_data_file()
        else:
            return self.this_data_file()

    def last_data_file(self):
        """
        Location of data file in last/ cache dir.
        """
        return os.path.join(self.storage_dir(False), "%s%s" % (self.storage_key, self.ext))

    def this_data_file(self):
        """
        Location of data file in this/ cache dir.
        """
        return os.path.join(self.storage_dir(True), "%s%s" % (self.storage_key, self.ext))

    def data_file_exists(self, this):
        if this:
            return os.path.exists(self.this_data_file())
        else:
            return os.path.exists(self.last_data_file())

    def data_file_size(self, this):
        if this:
            return os.path.getsize(self.this_data_file())
        else:
            return os.path.getsize(self.last_data_file())

    def storage_dir(self, this=None):
        if this is None:
            this = (self.wrapper.state in ('walked', 'running'))

        if this:
            cache_dir = self.wrapper.this_cache_dir()
        else:
            cache_dir = self.wrapper.last_cache_dir()
        
        return os.path.join(cache_dir, self.storage_key[0:2])

    def write_data(self, data, filepath=None):
        if not filepath:
            filepath = self.data_file(read=False)

        self.assert_location_is_in_project_dir(filepath)

        if os.path.exists(self.this_data_file()) and not filepath == self.this_data_file():
            shutil.copyfile(self.this_data_file(), filepath)
        else:
             with open(filepath, "wb") as f:
                 if not isinstance(data, unicode):
                     f.write(data)
                 else:
                     f.write(unicode(data).encode("utf-8"))

    def read_data(self):
        with open(self.data_file(read=True), "rb") as f:
            return f.read()

    def copy_file(self, filepath):
        """
        If data file exists, copy file and return true. Otherwise return false.
        """
        try:
            self.assert_location_is_in_project_dir(filepath)
            this = (self.wrapper.state in ('walked', 'running', 'ran',))
            shutil.copyfile(self.data_file(this), filepath)
            return True
        except:
            return False

# Sectioned Data
import json
class JsonSectionedStorage(GenericStorage):
    """
    Storage for sectional data using JSON.
    """
    aliases = ['jsonsectioned']

    def read_data(self, this=True):
        with open(self.data_file(this), "rb") as f:
            data = json.load(f)
            if hasattr(data, 'keys'):
                msg = "Data storage format has changed. Please clear your dexy cache by running dexy with '-r' option."
                raise UserFeedback(msg)
            return data

    def write_data(self, data, filepath=None):
        if not filepath:
            filepath = self.data_file()

        self.assert_location_is_in_project_dir(filepath)

        with open(filepath, "wb") as f:
            json.dump(data, f)

# Key Value Data
class JsonKeyValueStorage(GenericStorage):
    """
    Storage for key value data using JSON.
    """
    aliases = ['json']

    def setup(self):
        self._data = {}

    def append(self, key, value):
        self._data[key] = value

    def keys(self):
        return self.data().keys()

    def value(self, key):
        return self.data()[key]

    def __getitem__(self, key):
        return self.value(key)

    def items(self):
        return self.data().items()

    def iteritems(self):
        return self.data().iteritems()

    def read_data(self, this=True):
        with open(self.data_file(this), "rb") as f:
            return json.load(f)

    def data(self):
        if len(self._data) == 0:
            self._data = self.read_data()
        return self._data

    def persist(self):
        self.write_data(self._data)

    def write_data(self, data, filepath=None):
        if not filepath:
            filepath = self.data_file()

        self.assert_location_is_in_project_dir(filepath)

        with open(filepath, "wb") as f:
            json.dump(data, f)

class Sqlite3KeyValueStorage(GenericStorage):
    """
    Storage of key value storage in sqlite3 database files.
    """
    aliases = ['sqlite3']

    def working_file(self):
        sk = self.storage_key[0:2]
        pathargs = (
                self.wrapper.work_cache_dir(),
                sk,
                "%s.sqlite3" % self.storage_key,
                )
        return os.path.join(*pathargs)

    def connect(self):
        self._append_counter = 0
        if self.wrapper.state in ('walked', 'checked', 'running'):
            if file_exists(self.this_data_file()):
                self.connected_to = 'existing'
                self._storage = sqlite3.connect(self.this_data_file())
                self._cursor = self._storage.cursor()
            elif file_exists(self.last_data_file()):
                msg ="Should not only have last data file %s"
                msgargs=(self.last_data_file())
                raise dexy.exceptions.InternalDexyProblem(msg % msgargs)
            else:
                assert not os.path.exists(self.working_file())
                assert os.path.exists(os.path.dirname(self.working_file()))
                self.connected_to = 'working'
                self._storage = sqlite3.connect(self.working_file())
                self._cursor = self._storage.cursor()
                self._cursor.execute("CREATE TABLE kvstore (key TEXT, value TEXT)")
        elif self.wrapper.state == 'walked':
            raise dexy.exceptions.InternalDexyProblem("connect should not be called in 'walked' state")
        else:
            if file_exists(self.last_data_file()):
                self._storage = sqlite3.connect(self.last_data_file())
                self._cursor = self._storage.cursor()
            elif file_exists(self.this_data_file()):
                self._storage = sqlite3.connect(self.this_data_file())
                self._cursor = self._storage.cursor()
            else:
                raise dexy.exceptions.InternalDexyProblem("no data for %s" % self.storage_key)

    def append(self, key, value):
        self._cursor.execute("INSERT INTO kvstore VALUES (?, ?)", (key, value))
        self._append_counter += 1
        if self._append_counter > 1000:
            self.wrapper.log.debug("intermediate commit to sqlite db, resetting append counter to 0")
            self._storage.commit()
            self._append_counter = 0

    def keys(self):
        self._cursor.execute("SELECT key from kvstore")
        return [unicode(k[0]) for k in self._cursor.fetchall()]

    def iteritems(self):
        self._cursor.execute("SELECT key, value from kvstore")
        for k in self._cursor.fetchall():
            yield (unicode(k[0]), k[1])

    def items(self):
        return [(key, value) for (key, value) in self.iteritems()]

    def value(self, key):
        self._cursor.execute("SELECT value from kvstore where key = ?", (key,))
        row = self._cursor.fetchone()
        if not row:
            raise Exception("No value found for key '%s'" % key)
        else:
            return row[0]

    def like(self, key):
        self._cursor.execute("SELECT value from kvstore where key LIKE ?", (key,))
        row = self._cursor.fetchone()
        if not row:
            raise Exception("No value found for key '%s'" % key)
        else:
            return row[0]

    def query(self, query):
        if not '%' in query:
            query = "%%%s%%" % query
        self._cursor.execute("SELECT * from kvstore where key like ?", (query,))
        return self._cursor.fetchall()

    def __getitem__(self, key):
        return self.value(key)

    def persist(self):
        if self.connected_to == 'existing':
            assert os.path.exists(self.data_file(read=False))
        elif self.connected_to == 'working':
            self.assert_location_is_in_project_dir(self.data_file(read=False))
            self._storage.commit()
            shutil.copyfile(self.working_file(), self.data_file(read=False))
        else:
            msg = "Unexpected 'connected_to' value %s"
            msgargs = self.connected_to
            raise InternalDexyProblem(msg % msgargs)

########NEW FILE########
__FILENAME__ = template
from dexy.utils import s
import dexy.plugin
import dexy.utils
import dexy.wrapper
import os
import shutil
import sys

class Template(dexy.plugin.Plugin):
    """
    Parent class for templates.
    """
    __metaclass__ = dexy.plugin.PluginMeta
    _settings = {
            'contents-dir' : ("Directory containing contents of template.", None),
            'nodoc' : ("Whether to not document this template.", False),
            'copy-output-dir' : ("", False)
            }
    aliases = []
    filters_used = []

    def __init__(self):
        self.initialize_settings()

    def template_source_dir(self):
        if self.safe_setting('install-dir'):
            template_install_dir = self.setting('install-dir')
        else:
            template_install_dir = os.path.dirname(sys.modules[self.__module__].__file__)

        if self.setting('contents-dir'):
            contents_dirname = self.setting('contents-dir')
        else:
            if self.__class__.aliases:
                canonical_alias = self.__class__.aliases[0]
            else:
                canonical_alias = self.alias

            # default is to have contents in directory with same name as alias followed by "-template"
            contents_dirname = "%s-template" % canonical_alias

        return os.path.join(template_install_dir, contents_dirname)

    def generate(self, directory, **kwargs):
        """
        Generates the template, making a copy of the template's files in
        the specified directory. Does not run dexy.
        """
        if dexy.utils.file_exists(directory):
            msg = "directory '%s' already exists, aborting" % directory
            raise dexy.exceptions.UserFeedback(msg)

        # copy template files
        source = self.template_source_dir()
        shutil.copytree(source, directory)

        # remove template documentation unless 'meta' is specified
        if not kwargs.get('meta'):
            dexy_rst = os.path.join(directory, 'dexy.rst')
            if dexy.utils.file_exists(dexy_rst):
                os.remove(dexy_rst)

    def dexy(self, meta=True, additional_doc_keys=None):
        """
        Run dexy on this template's files in a temporary directory.

        Yields the batch object for the dexy run, so we can call methods on it
        while still in the tempdir.
        """
        meta_doc_keys = [
                ".*",
                "dexy.yaml|idio|t",
                "dexy.rst|idio|t",
                "dexy.rst|jinja|rst2html",
                "dexy.rst|jinja|rst2man"
                ]

        with dexy.utils.tempdir():
            # Copy template files to directory 'ex'
            self.generate("ex", meta=meta)

            # Run dexy in directory 'ex'
            os.chdir("ex")
            wrapper = dexy.wrapper.Wrapper()
            wrapper.create_dexy_dirs()
            wrapper = dexy.wrapper.Wrapper(log_level='DEBUG')
            wrapper.to_valid()
            wrapper.nodes = {}
            wrapper.roots = []
            wrapper.batch = dexy.batch.Batch(wrapper)
            wrapper.filemap = wrapper.map_files()

            ast = wrapper.parse_configs()
            if additional_doc_keys:
                for doc_key in additional_doc_keys:
                    ast.add_node(doc_key)

            if meta and dexy.utils.file_exists('dexy.rst'):
                for doc_key in meta_doc_keys:
                    ast.add_node(doc_key)
                    if 'jinja' in doc_key:
                        for task in ast.lookup_table.keys():
                            if not task in meta_doc_keys:
                                ast.add_dependency(doc_key, task)

            ast.walk()

            wrapper.transition('walked')
            wrapper.to_checked()

            try:
                wrapper.run()
            except (Exception, SystemExit,) as e:
                error = unicode(e)
                template_dir = os.path.abspath(".")
                msg = u"%s\npushd %s" % (error, template_dir)
                raise dexy.exceptions.TemplateException(msg)

            if wrapper.state == 'error':
                template_dir = os.path.abspath(".")
                msg = "pushd %s" % (template_dir)
                raise dexy.exceptions.TemplateException(msg)

            yield(wrapper)

    def validate(self):
        """
        Runs dexy and validates filter list.
        """
        for wrapper in self.dexy(False):
            filters_used = wrapper.batch.filters_used

            for f in self.__class__.filters_used:
                msg = "filter %s not used by %s" % (f, self.__class__.__name__)
                assert f in filters_used, msg
    
            for f in filters_used:
                if not f.startswith('-') and not f in self.__class__.filters_used:
                    msg = s("""filter %(filter)s used by %(template)s
                            but not listed in klass.filters_used,
                            adjust list to: filters_used = [%(list)s]""")
                    msgargs = {
                            'filter' : f,
                            'template' : self.__class__.__name__,
                            'list'  : ", ".join("'%s'" % f for f in filters_used)
                            }
                    print msg % msgargs

            return wrapper.state == 'ran'

########NEW FILE########
__FILENAME__ = standard
import dexy.template

class DefaultTemplate(dexy.template.Template):
    """
    A very boring default template that ships with dexy.
    """
    aliases = ['default']
    filters_used = ['jinja']

########NEW FILE########
__FILENAME__ = utils
import dexy.exceptions
import hashlib
import inspect
import json
import logging
import os
import platform
import posixpath
import re
import shutil
import tempfile
import time
import yaml

is_windows = platform.system() in ('Windows',)

def copy_or_link(data, destination, use_links=True, read_only_links=True):
    """
    Copies or makes a hard link. Will copy if on windows or if use_links is False.
    """
    if is_windows or not use_links:
        data.output_to_file(destination)
    else:
        os.link(data.storage.data_file(), destination)

defaults = {
    'artifacts_dir' : '.dexy',
    'config_file' : 'dexy.conf',
    'configs' : '',
    'debug' : False,
    'directory' : ".",
    'dont_use_cache' : False,
    'dry_run' : False,
    'encoding' : 'utf-8',
    'exclude' : '.git, .svn, tmp, cache, .trash, .ipynb_checkpoints',
    'exclude_also' : '',
    'full' : False,
    'globals' : '',
    'hashfunction' : 'md5',
    'ignore_nonzero_exit' : False,
    'include' : '',
    'log_dir' : '.dexy',
    'log_file' : 'dexy.log',
    'log_format' : "%(name)s - %(levelname)s - %(message)s",
    'log_level' : "INFO",
    'output_root' : '.',
    'parsers' : "dexy-env.json dexy.txt dexy.yaml",
    'pickle' : 'c',
    'plugins': 'dexyplugins.py dexyplugin.py dexyplugins.yaml dexyplugin.yaml',
    'profile' : False,
    'recurse' : True,
    'reports' : '',
    'safety_filename' : '.dexy-generated',
    'siblings' : False,
    'silent' : False,
    'strace' : False,
    'target' : False,
    'timing' : True,
    'uselocals' : False,
    'writeanywhere' : False
}

log_levels = {
    'DEBUG' : logging.DEBUG,
    'INFO' : logging.INFO,
    'WARN' : logging.WARN
}

def transition(obj, new_state):
    """
    Attempts to transition this object to the new state, if the transition
    from current state to new state is valid as per state_transitions list.
    """
    attempted_transition = (obj.state, new_state) 
    if not attempted_transition in obj.__class__.state_transitions:
        msg = "%s -> %s"
        raise dexy.exceptions.UnexpectedState(msg % attempted_transition)

    if not hasattr(obj, 'time_entered_current_state'):
        obj.time_entered_current_state = None
        obj.state_history = []
  
    if obj.time_entered_current_state:
        transition_time = time.time()

        time_in_prev_state = transition_time - obj.time_entered_current_state
        obj.state_history.append((obj.state, time_in_prev_state))

    obj.time_entered_current_state = time.time()
    obj.state = new_state

def pickle_lib(wrapper):
    if wrapper.pickle == 'c':
        import cPickle as pickle
        return pickle
    elif wrapper.pickle == 'py':
        import pickle
        return pickle
    else:
        msg = "'%s' is not a valid value for pickle" % wrapper.pickle
        raise dexy.exceptions.UserFeedback(msg)


def logging_log_level(log_level):
    try:
        return log_levels[log_level.upper()]
    except KeyError:
        msg = "'%s' is not a valid log level, check python logging module docs"
        raise dexy.exceptions.UserFeedback(msg % log_level)

def md5_hash(text):
    return hashlib.md5(text).hexdigest()

def dict_from_string(text):
    """
    Creates a dict from string like "key1=value1,k2=v2"
    """
    d = {}
    if text > 0:
        for pair in text.split(","):
            x, y = pair.split("=")
            d[x] = y
    return d

def file_exists(filepath, debug=False):
    if debug:
        print "calling file_exists on %s" % filepath
        frame = inspect.currentframe()
        for f in inspect.getouterframes(frame):
            print "   ", f[1], f[2], f[3]
        del frame
        del f
    return os.path.exists(filepath)

def iter_paths(path):
    """
    Iterate over all subpaths of path starting with root path.
    """
    path_elements = split_path(path)

    if path.startswith(os.sep):
        start = os.sep
    else:
        start = None

    for i in range(1, len(path_elements)+1):
        if start:
            yield os.path.join(start, *path_elements[0:i])
        else:
            yield os.path.join(*path_elements[0:i])

def reverse_iter_paths(path):
    """
    Iterate over all subpaths of path starting with path, ending with root path.
    """
    path_elements = split_path(path)
    for i in range(len(path_elements), 0, -1):
        yield os.path.join(*path_elements[0:i])
    yield "/"

def split_path(path):
    # TODO test that paths are normed and don't include empty or '.' components.
    tail = True
    path_elements = []
    body = path
    while tail:
        body, tail = os.path.split(body)
        if tail:
            path_elements.append(tail)
        elif path.startswith("/"):
            path_elements.append(tail)
            
    path_elements.reverse()
    return path_elements

class tempdir(object):
    def make_temp_dir(self):
        self.tempdir = tempfile.mkdtemp()
        self.location = os.path.abspath(os.curdir)
        os.chdir(self.tempdir)

    def remove_temp_dir(self):
        os.chdir(self.location)
        try:
            shutil.rmtree(self.tempdir)
        except Exception as e:
            print e
            print "was not able to remove tempdir '%s'" % self.tempdir

    def __enter__(self):
        self.make_temp_dir()

    def __exit__(self, type, value, traceback):
        if not isinstance(value, Exception):
            self.remove_temp_dir()

def value_for_hyphenated_or_underscored_arg(arg_dict, arg_name_hyphen, default=None):
    if not "-" in arg_name_hyphen and "_" in arg_name_hyphen:
        raise dexy.exceptions.InternalDexyProblem("arg_name_hyphen %s has underscores!" % arg_name_hyphen)

    arg_name_underscore = arg_name_hyphen.replace("-", "_")

    arg_value = arg_dict.get(arg_name_hyphen)

    if arg_value is None:
        arg_value = arg_dict.get(arg_name_underscore)

    if arg_value is None:
        return default
    else:
        return arg_value

def s(text):
    return re.sub('\s+', ' ', text)

def getdoc(element, firstline=True):
    docstring = inspect.getdoc(element)
    if docstring and firstline:
        docstring = docstring.splitlines()[0]

    if not docstring:
        docstring = ''

    return docstring

def os_to_posix(path):
    return posixpath.join(*os.path.split(path))

def parse_json(input_text):
    try:
        return json.loads(input_text)
    except ValueError as e:
        msg = inspect.cleandoc(u"""Was unable to parse the JSON you supplied.
        Here is information from the JSON parser:""")
        msg += u"\n"
        msg += unicode(e)
        raise dexy.exceptions.UserFeedback(msg)

def parse_json_from_file(f):
    try:
        return json.load(f)
    except ValueError as e:
        msg = inspect.cleandoc(u"""Was unable to parse the JSON you supplied.
        Here is information from the JSON parser:""")
        msg += u"\n"
        msg += unicode(e)
        raise dexy.exceptions.UserFeedback(msg)

def parse_yaml(input_text):
    """
    Parse a single YAML document.
    """
    try:
        return yaml.safe_load(input_text)
    except (yaml.scanner.ScannerError, yaml.parser.ParserError) as e:
        if "found character '\\t'" in unicode(e):
            msg = "You appear to have hard tabs in your yaml, this is not supported. Please change to using soft tabs instead (your text editor should have this option)."
            raise dexy.exceptions.UserFeedback(msg)
        else:
            msg = inspect.cleandoc(u"""Was unable to parse the YAML you supplied.
            Here is information from the YAML parser:""")
            msg += u"\n"
            msg += unicode(e)
            raise dexy.exceptions.UserFeedback(msg)

def parse_yamls(input_text):
    """
    Parse YAML content that may include more than 1 document.
    """
    try:
        return yaml.safe_load_all(input_text)
    except (yaml.scanner.ScannerError, yaml.parser.ParserError) as e:
        msg = inspect.cleandoc(u"""Was unable to parse the YAML you supplied.
        Here is information from the YAML parser:""")
        msg += u"\n"
        msg += unicode(e)
        raise dexy.exceptions.UserFeedback(msg)

def printable_for_char(c):
    if ord(c) >= ord('!'):
        return c
    elif ord(c) == 32:
        return "<space>"
    else:
        return ""

def char_diff(str1, str2):
    """
    Returns a char-by-char diff of two strings, highlighting differences.
    """
    msg = ""
    for i, c1 in enumerate(str1):
        if len(str2) > i:
            c2 = str2[i]

            if c1 == c2:
                flag = ""
            else:
                flag = " <---"

            p_c1 = printable_for_char(c1)
            p_c2 = printable_for_char(c2)

            msg = msg + "\n%5d: %8s\t%8s\t\t%s\t%s %s" % (i, p_c1, p_c2, ord(c1), ord(c2), flag)
        else:
            # str1 is longer than str2
            flag = " <---"
            p_c1 = printable_for_char(c1)
            msg = msg + "\n%5d: %8s\t%8s\t\t%s\t%s %s" % (i, p_c1, '  ', ord(c1), '  ', flag)

    # TODO add code for str2 longer than str1

    return msg

# http://code.activestate.com/recipes/576874-levenshtein-distance/
def levenshtein(s1, s2):
    l1 = len(s1)
    l2 = len(s2)

    matrix = [range(l1 + 1)] * (l2 + 1)
    for zz in range(l2 + 1):
      matrix[zz] = range(zz,zz + l1 + 1)
    for zz in range(0,l2):
      for sz in range(0,l1):
        if s1[sz] == s2[zz]:
          matrix[zz+1][sz+1] = min(matrix[zz+1][sz] + 1, matrix[zz][sz+1] + 1, matrix[zz][sz])
        else:
          matrix[zz+1][sz+1] = min(matrix[zz+1][sz] + 1, matrix[zz][sz+1] + 1, matrix[zz][sz] + 1)
    return matrix[l2][l1]

def indent(s, spaces=4):
    return "\n".join("%s%s" % (' ' * spaces, line)
            for line in s.splitlines())

########NEW FILE########
__FILENAME__ = version
DEXY_VERSION="1.0.7d"

########NEW FILE########
__FILENAME__ = wrapper
from dexy.exceptions import DeprecatedException
from dexy.exceptions import InternalDexyProblem
from dexy.exceptions import UserFeedback
from dexy.utils import file_exists
from dexy.utils import s
import chardet
import dexy.batch
import dexy.doc
import dexy.parser
import dexy.reporter
import dexy.utils
import logging
import logging.handlers
import os
import posixpath
import shutil
import sys
import textwrap
import time
import uuid

class Wrapper(object):
    """
    Class that manages run configuration and state and provides utilities such
    as logging and setting up/tearing down workspace on file system.
    """
    _required_dirs = ['artifacts_dir']

    state_transitions = (
            (None, 'new'),
            ('new', 'valid'),
            ('valid', 'valid'),
            ('valid', 'walked'),
            ('walked', 'checked'),
            ('checked', 'running'),
            ('running', 'error'),
            ('running', 'ran'),
            )

    def printmsg(self, msg):
        if self.silent:
            self.log.warn(msg)
        else:
            print msg

    def validate_state(self, state=None):
        """
        Checks that the instance is in the expected state, and validates
        attributes for the state.
        """
        if state:
            assert self.state == state
        else:
            state = self.state

        if state == 'new':
            assert not self.state_history
            assert self.project_root
        elif state == 'valid':
            pass
        elif state == 'walked':
            assert self.batch
            assert self.nodes
            assert self.roots
            assert self.filemap
            for node in self.nodes.values():
                assert node.state == 'new'
        elif state == 'checked':
            for node in self.nodes.values():
                assert node.state in ('uncached', 'consolidated', 'inactive',), node.state
        elif state == 'ran':
            for node in self.nodes.values():
                assert node.state in ('ran', 'consolidated', 'inactive'), node.state
        elif state == 'error':
            pass
        else:
            raise dexy.exceptions.InternalDexyProblem(state)

    def __init__(self, **kwargs):
        self.initialize_attribute_defaults()
        self.update_attributes_from_kwargs(kwargs)
        self.project_root = os.path.abspath(os.getcwd())
        self.project_root_ts = "%s%s" % (self.project_root, os.sep)
        self.state = None
        self.current_task = None
        self.lookup_nodes = {} # map of shortcuts/keys to all nodes which can match
        self.lookup_sections = {} # map of section names to nodes
        self.transition('new')

    def state_message(self):
        """
        A message to print at end of dexy run depending on the final wrapper state.
        """
        if self.state == 'error':
            return " WITH ERRORS"
        else:
            return ""

    def transition(self, new_state):
        dexy.utils.transition(self, new_state)

    def setup_for_valid(self):
        self.setup_log()

    def to_valid(self):
        if not self.dexy_dirs_exist():
            msg = "Should not attempt to enter 'valid' state unless dexy dirs exist."
            raise dexy.exceptions.InternalDexyProblem(msg)
        self.setup_for_valid()
        self.transition('valid')

    def walk(self):
        self.nodes = {}
        self.roots = []
        self.batch = dexy.batch.Batch(self)
        self.filemap = self.map_files()
        self.ast = self.parse_configs()
        self.ast.walk()

    def to_walked(self):
        self.walk()
        self.transition('walked')

    def check(self):
        # Clean and reset working dirs.
        self.reset_work_cache_dir()
        if not os.path.exists(self.this_cache_dir()):
            self.create_cache_dir_with_sub_dirs(self.this_cache_dir())

        # Load information about arguments from previous batch.
        self.load_node_argstrings()

        self.check_cache()
        self.consolidate_cache()

        # Save information about this batch's arguments for next time.
        self.save_node_argstrings()

    def check_cache(self):
        """
        Check whether all required files are already cached from a previous run
        """
        for node in self.roots:
            node.check_is_cached()

    def consolidate_cache(self):
        """
        Move all cache files from last/ cache to this/ cache
        """
        for node in self.roots:
            node.consolidate_cache_files()

        self.trash(self.last_cache_dir())

    def to_checked(self):
        self.check()
        self.transition('checked')

    # Cache dirs
    def this_cache_dir(self):
        return os.path.join(self.artifacts_dir, "this")

    def last_cache_dir(self):
        return os.path.join(self.artifacts_dir, "last")

    def work_cache_dir(self):
        return os.path.join(self.artifacts_dir, "work")

    def trash_dir(self):
        return os.path.join(self.project_root, ".trash")

    def create_cache_dir_with_sub_dirs(self, cache_dir):
        os.mkdir(cache_dir)
        hexes = ['0','1','2','3','4','5','6','7','8','9','a','b','c','d','e','f']
        for c in hexes:
            for d in hexes:
                os.mkdir(os.path.join(cache_dir, "%s%s" % (c,d)))

    def trash(self, d):
        """
        Move the passed file path (if it exists) into the .trash directory.
        """
        if not self.is_location_in_project_dir(d):
            msg = "trying to trash '%s', but this is not in project dir '%s"
            msgargs = (d, self.project_root)
            raise dexy.exceptions.InternalDexyProblem(msg % msgargs)

        trash_dir = self.trash_dir()

        try:
            os.mkdir(trash_dir)
        except OSError:
            pass

        move_to = os.path.join(trash_dir, str(uuid.uuid4()))

        try:
            shutil.move(d, move_to)
        except IOError:
            pass

    def empty_trash(self):
        try:
            shutil.rmtree(self.trash_dir())
        except OSError as e:
            if not "No such file or directory" in unicode(e):
                raise

    def reset_work_cache_dir(self):
        # remove work/ dir leftover from previous run (if any) and create a new
        # work/ dir for this run
        work_dir = self.work_cache_dir()
        self.trash(work_dir)
        self.create_cache_dir_with_sub_dirs(work_dir)

    def run(self):
        self.transition('running')

        self.batch.start_time = time.time()

        if self.target:
            matches = self.roots_matching_target()
        else:
            matches = self.roots

        try:
            for node in matches:
                for task in node:
                    task()

        except Exception as e:
            self.error = e
            self.transition('error')
            if self.debug:
                raise
            else:
                if self.current_task:
                    msg = u"ERROR while running %s: %s\n" % (self.current_task.key, unicode(e))
                else:
                    msg = u"ERROR: %s\n" % unicode(e)
                sys.stderr.write(msg)
                self.log.warn(msg)

        else:
            self.after_successful_run()

    def after_successful_run(self):
        self.transition('ran')
        self.batch.end_time = time.time()
        self.batch.save_to_file()
        shutil.move(self.this_cache_dir(), self.last_cache_dir())
        self.empty_trash()
        self.add_lookups()

    def add_lookups(self):
        for data in self.batch:
            data.add_to_lookup_sections()
            data.add_to_lookup_nodes()

    def bundle_docs(self):
        from dexy.node import BundleNode
        return [n for n in self.nodes.values() if isinstance(n, BundleNode)]

    def non_bundle_docs(self):
        from dexy.node import BundleNode
        return [n for n in self.nodes.values() if not isinstance(n, BundleNode)]

    def documents(self):
        from dexy.doc import Doc
        return [n for n in self.nodes.values() if isinstance(n, Doc)]

    def roots_matching_target(self):
        # First priority is to match any named bundles.
        matches = [n for n in self.bundle_docs() if n.key == self.target]
        if not matches:
            # Second priority is exact matches of any document key.
            matches = [n for n in self.non_bundle_docs() if n.key == self.target]
        if not matches:
            # Third priority is partial matches of any document key.
            matches = [n for n in self.nodes.values() if n.key.startswith(self.target)]

        if not matches:
            raise dexy.exceptions.UserFeedback("No matches found for '%s'" % self.target)

        self.log.debug("Documents matching target '%s' are: %s" % (self.target, ", ".join(m.key_with_class() for m in matches)))
        return matches

    def run_from_new(self):
        self.to_valid()
        self.to_walked()
        self.to_checked()
        if self.dry_run:
            self.printmsg("dry run only")
        else:
            self.run()

    def run_docs(self, *docs):
        self.to_valid()

        # do a custom walk() method
        self.roots = docs
        self.nodes = dict((node.key_with_class(), node) for node in self.roots)
        self.filemap = self.map_files()
        self.batch = dexy.batch.Batch(self)
        self.transition('walked')

        self.to_checked()
        self.run()

    # Attributes
    def initialize_attribute_defaults(self):
        """
        Applies the values in defaults dict to this wrapper instance.
        """
        for name, value in dexy.utils.defaults.iteritems():
            setattr(self, name, value)

    def update_attributes_from_kwargs(self, kwargs):
        """
        Updates instance values from a dictionary of kwargs, checking that the
        attribute names are also present in defaults dict.
        """
        for key, value in kwargs.iteritems():
            if not key in dexy.utils.defaults:
                msg = "invalid kwarg '%s' being passed to wrapper, not defined in defaults dict" 
                raise InternalDexyProblem(msg % key)
            setattr(self, key, value)

    # Store Args
    def pickle_lib(self):
        return dexy.utils.pickle_lib(self)

    def node_argstrings_filename(self):
        return os.path.join(self.artifacts_dir, 'batch.args.pickle')

    def save_node_argstrings(self):
        """
        Save string representation of node args to check if they have changed.
        """
        arg_info = {}

        for node in self.nodes.values():
            arg_info[node.key_with_class()] = node.sorted_arg_string()

        with open(self.node_argstrings_filename(), 'wb') as f:
            pickle = self.pickle_lib()
            pickle.dump(arg_info, f)

    def load_node_argstrings(self):
        """
        Load saved node arg strings into a hash so nodes can check if their
        args have changed.
        """
        try:
            with open(self.node_argstrings_filename(), 'rb') as f:
                pickle = self.pickle_lib()
                self.saved_args = pickle.load(f)
        except IOError:
            self.saved_args = {}

    # Dexy Dirs
    def iter_dexy_dirs(self):
        """
        Iterate over the required dirs (e.g. artifacts, logs)
        """
        for d in self.__class__._required_dirs:
            dirpath = self.__dict__[d]
            safety_filepath = os.path.join(dirpath, self.safety_filename)
            try:
                stat = os.stat(dirpath)
            except OSError:
                stat = None

            if stat:
                if not file_exists(safety_filepath):
                    msg = s("""You need to manually delete the '%s' directory
                    and then run 'dexy setup' to create new directories. This
                    should just be a once-off issue due to a change in dexy to
                    prevent accidentally deleting directories which dexy does
                    not create.
                    """) % dirpath
                    raise UserFeedback(msg)

            yield (dirpath, safety_filepath, stat)

    def dexy_dirs_exist(self):
        """
        Returns a boolean indicating whether dexy dirs exist.
        """
        return all(file_exists(d[0]) for d in self.iter_dexy_dirs())

    def assert_dexy_dirs_exist(self):
        """
        Raise a UserFeedback error if user has tried to run dexy without
        setting up necessary directories first.
        """
        self.detect_dot_dexy_files()
        self.update_cache_directory()

        if not self.dexy_dirs_exist():
            msg = "You need to run 'dexy setup' in this directory first."
            raise UserFeedback(msg)

        self.deprecate_logs_directory()

    def create_dexy_dirs(self):
        """
        Creates the directories needed for dexy to run. Does not complain if
        directories are already present.
        """
        for dirpath, safety_filepath, dirstat in self.iter_dexy_dirs():
            if not dirstat:
                os.mkdir(dirpath)
                with open(safety_filepath, 'w') as f:
                    f.write("This directory was created by dexy.")

    def detect_dot_dexy_files(self):
        if os.path.exists(".dexy") and os.path.isfile(".dexy"):
            msg = """\
            You have a file named '.dexy' in your project, this format is no longer supported.
            See http://dexy.it/guide/getting-started.html for updated tutorials.
            Please rename or remove this file to proceed."""
            raise dexy.exceptions.UserFeedback(textwrap.dedent(msg))

    def update_cache_directory(self):
        """
        Move .cache directories to be .dexy directories.
        """
        old_cache_dir = ".cache"
        safety_file = os.path.join(old_cache_dir, self.safety_filename)

        if self.artifacts_dir == old_cache_dir:
            msg = """\
            You may have a dexy.conf file present in which you specify
            'artifactsdir: .cache'
            
            Dexy's defaults have changed and the .cache directory is being
            renamed to .dexy

            The easiest way to never see this message again is to remove this
            line from your dexy.conf file (You should remove any entries in
            dexy.conf which you don't specifically want to customize.)
            
            If you really want the artifacts directory to be at .cache then you
            can leave your config in place and this message will disappear in a
            future dexy version.
            """
            print textwrap.dedent(msg)

        elif os.path.exists(old_cache_dir) and os.path.isdir(old_cache_dir) and os.path.exists(safety_file):
            if os.path.exists(self.artifacts_dir):
                if os.path.isdir(self.artifacts_dir):
                    msg = "You have a dexy '%s' directory and a '%s' directory. Please remove '%s' or at least '%s'."
                    msgargs = (old_cache_dir, self.artifacts_dir, old_cache_dir, safety_file)
                    raise dexy.exceptions.UserFeedback(msg % msgargs)
                else:
                    msg = "'%s' is not a dir!" % (self.artifacts_dir,)
                    raise dexy.exceptions.InternalDexyProblem(msg)

            print "Moving directory '%s' to new location '%s'" % (old_cache_dir, self.artifacts_dir)
            shutil.move(old_cache_dir, self.artifacts_dir)

    def deprecate_logs_directory(self):
        log_dir = 'logs'
        if self.log_dir != self.artifacts_dir:
            # user has set a custom log dir
            log_dir = self.log_dir

        safety_file = os.path.join(log_dir, self.safety_filename)
        deprecation_notice_file = os.path.join(log_dir, "WHERE-ARE-THE-LOGS.txt")

        if os.path.exists(log_dir) and os.path.exists(safety_file) and not os.path.exists(deprecation_notice_file):
            deprecation_notice = """\
            Dexy no longer has a separate '{log_dir}' directory for the log file.
            The logfile can now be found at: {log_path}\n""".format(
                    log_path = self.log_path(),
                    log_dir = log_dir)
            
            deprecation_notice = "\n".join(l.strip() for l in deprecation_notice.splitlines())
            self.printmsg("Deprecating %s/ directory" % log_dir)
            self.printmsg(deprecation_notice)
            self.printmsg("You can remove the %s/ directory" % log_dir)

            with open(deprecation_notice_file, 'w') as f:
                f.write(deprecation_notice + "\n\nYou can remove this directory.\n")
            self.trash(os.path.join(log_dir, "dexy.log"))

    def remove_dexy_dirs(self):
        for dirpath, safety_filepath, dirstat in self.iter_dexy_dirs():
            if dirstat:
                self.trash(dirpath)
        self.empty_trash()

    def remove_reports_dirs(self, reports=True, keep_empty_dir=False):
        if reports:
            if isinstance(reports, bool):
                # return an iterator over all reporters
                reports=dexy.reporter.Reporter

            for report in reports:
                report.remove_reports_dir(self, keep_empty_dir)

    # Logging
    def log_path(self):
        """
        Returns path to logfile.
        """
        return os.path.join(self.artifacts_dir, self.log_file)

    def setup_log(self):
        """
        Creates a logger and assigns it to 'log' attribute of wrapper.
        """
        formatter = logging.Formatter(self.log_format)
        log_level = dexy.utils.logging_log_level(self.log_level)

        handler = logging.handlers.RotatingFileHandler(
                self.log_path(),
                encoding="utf-8")

        handler.setFormatter(formatter)

        self.log = logging.getLogger('dexy')
        self.log.setLevel(log_level)
        self.log.addHandler(handler)
        self.log.info("starting logging for dexy")
        self.log_handler = handler

    def flush_logs(self):
        self.log_handler.flush()

    # Project files
    def exclude_dirs(self):
        """
        Returns list of directory names which should be excluded from dexy processing.
        """
        exclude_str = self.exclude
        if self.exclude_also:
            exclude_str += ",%s" % self.exclude_also

        exclude = [d.strip() for d in exclude_str.split(",")]
        exclude += self.reports_dirs()

        for d in self.iter_dexy_dirs():
            exclude += [d[0], "%s-old" % d[0]]

        return exclude

    def reports_dirs(self):
        """
        Returns list of directories which are written to by reporters.
        """
        dirs_and_nones = [i.setting('dir') for i in dexy.reporter.Reporter]
        return [d for d in dirs_and_nones if d]

    def map_files(self):
        """
        Generates a map of files present in the project directory.
        """
        exclude = self.exclude_dirs()
        filemap = {}

        for dirpath, dirnames, filenames in os.walk('.'):
            for x in exclude:
                if x in dirnames and not x in self.include:
                    dirnames.remove(x)

            if '.nodexy' in filenames:
                dirnames[:] = []
            elif 'pip-delete-this-directory.txt' in filenames:
                msg = s("""pip left an old build/ file lying around,
                please remove this before running dexy""")
                raise UserFeedback(msg)
            else:
                for filename in filenames:
                    filepath = posixpath.normpath(posixpath.join(dirpath, filename))
                    filemap[filepath] = {}
                    filemap[filepath]['stat'] = os.stat(os.path.join(dirpath, filename))
                    filemap[filepath]['ospath'] = os.path.normpath(os.path.join(dirpath, filename))
                    filemap[filepath]['dir'] = os.path.normpath(dirpath)

        return filemap

    def file_available(self, filepath):
        """
        Does the file exist and is it available to dexy?
        """
        return filepath in self.filemap

    # Running Dexy
    def add_node(self, node):
        """
        Add new nodes which are not children of other nodes.
        """
        key = node.key_with_class()
        self.nodes[key] = node

    def add_data_to_lookup_nodes(self, key, data):
        if not key in self.lookup_nodes:
            self.lookup_nodes[key] = []
        if not data in self.lookup_nodes[key]:
            self.lookup_nodes[key].append(data)

    def add_data_to_lookup_sections(self, key, data):
        if not key in self.lookup_sections:
            self.lookup_sections[key] = []
        if not data in self.lookup_sections[key]:
            self.lookup_sections[key].append(data)

    def qualify_key(self, key):
        """
        A full node key is of the form alias:pattern where alias indicates
        the type of node to be created. This method determines the alias if it
        is not specified explicitly, and returns the alias, pattern tuple.
        """
        if not key:
            msg = "trying to call qualify_key with key of '%s'!"
            raise DeprecatedException(msg % key)

        if ":" in key:
            # split qualified key into alias & pattern
            alias, pattern = key.split(":")
        else:
            # this is an unqualified key, figure out its alias
            pattern = key

            # Allow '.ext' instead of '*.ext', shorter + easier for YAML
            if pattern.startswith(".") and not pattern.startswith("./"):
                if not self.file_available(pattern):
                    pattern = "*%s" % pattern

            filepath = pattern.split("|")[0]
            if self.file_available(filepath):
                alias = 'doc'
            elif (not "." in pattern) and (not "|" in pattern):
                alias = 'bundle'
            elif "*" in pattern:
                alias = 'pattern'
            else:
                alias = 'doc'

        return alias, pattern

    def standardize_alias(self, alias):
        """
        Nodes can have multiple aliases, standardize on first one in list.
        """
        # TODO should we just make it so nodes only have 1 alias?
        node_class, _ = dexy.node.Node.plugins[alias]
        return node_class.aliases[0]

    def standardize_key(self, key):
        """
        Standardizes the key by making the alias explicit and standardized, so
        we don't create 2 entires in the AST for what turns out to be the same
        node/task.
        """
        alias, pattern = self.qualify_key(key)
        alias = self.standardize_alias(alias)
        return "%s:%s" % (alias, pattern)

    def join_dir(self, directory, key):
        if directory == ".":
            return key
        else:
            starts_with_dot = key.startswith(".") and not key.startswith("./")
            if starts_with_dot:
                path_to_key = os.path.join(directory, key)
                if not self.file_available(path_to_key):
                    key = "*%s" % key
            return posixpath.join(directory, key)

    def explicit_config_files(self):
        return [c.strip() for c in self.configs.split()]

    def is_explicit_config(self, filepath):
        return filepath in self.explicit_config_files()

    def parse_configs(self):
        """
        Look for document config files in current working tree and load them.
        Return an Abstract Syntax Tree with information about nodes to be
        processed.
        """
        ast = dexy.parser.AbstractSyntaxTree(self)

        processed_configs = []

        for alias in self.parsers.split():
            parser = dexy.parser.Parser.create_instance(alias, self, ast)

            for filepath, fileinfo in self.filemap.iteritems():
                if fileinfo['dir'] == '.' or self.recurse or self.is_explicit_config(filepath):
                    if os.path.split(filepath)[1] == alias:
                        self.log.info("using config file '%s'" % filepath)

                        config_file = fileinfo['ospath']
                        dirname = fileinfo['dir']

                        with open(config_file, "r") as f:
                            config_text = f.read()

                        try:
                            processed_configs.append(filepath)
                            parser.parse(dirname, config_text)
                        except UserFeedback:
                            sys.stderr.write("Problem occurred while parsing %s\n" % config_file)
                            raise

        if len(processed_configs) == 0:
            msg = "didn't find any document config files (like %s)"
            self.printmsg(msg % self.parsers)

        return ast

    def report(self):
        if self.reports:
            self.log.debug("generating user-specified reports '%s'" % self.reports)
            reporters = []
            for alias in self.reports.split():
                reporter = dexy.reporter.Reporter.create_instance(alias)
                reporters.append(reporter)
        else:
            msg = "no reports specified, running default reports"
            self.log.debug(msg)
            reporters = [i for i in dexy.reporter.Reporter if i.setting('default')]

        for reporter in reporters:
            if self.state in reporter.setting('run-for-wrapper-states'):
                self.log.debug("running reporter %s" % reporter.aliases[0])
                reporter.run(self)

    def is_location_in_project_dir(self, filepath):
        return self.writeanywhere or (self.project_root_ts in os.path.abspath(filepath))

    def decode_encoded(self, text):
        if self.encoding == 'chardet':
            encoding = chardet.detect(text)['encoding']
            if not encoding:
                return text.decode("utf-8")
            else:
                return text.decode(encoding)
        else:
            return text.decode(self.encoding)


########NEW FILE########
__FILENAME__ = issues
import requests
import json

api = "https://api.github.com"

def get_request(path, params=None):
    if not params:
        params = {}

    r = requests.get("%s%s" % (api, path), params=params)
    return r.json()


def save_issues_to_json(repo_owner, repo_name, filename):
    args = { 'owner' : repo_owner, 'name' : repo_name }
    path = "/repos/%(owner)s/%(name)s/issues" % args
    
    issues = {}
    
    raw_json_data = get_request(path, {'state' : 'open' })
    issues.update(dict((issue['number'], issue) for issue in raw_json_data))
    
    raw_json_data = get_request(path, {'state' : 'closed' })
    issues.update(dict((issue['number'], issue) for issue in raw_json_data))
    
    with open(filename, "wb") as f:
        json.dump(issues, f)

save_issues_to_json("dexy", "dexy", "issues.json")
save_issues_to_json("dexy", "dexy-user-guide", "docs-issues.json")

########NEW FILE########
__FILENAME__ = multiply
if __name__ == '__main__':
    ### @export "assign-variables"
    x = 6
    y = 7
    
    ### @export "multiply"
    print x*y
    
    
    ### @export "make-new-file"
    with open("foo.txt", "w") as f:
        f.write("hello!")

########NEW FILE########
__FILENAME__ = loop
for i in xrange(5):
    print i

########NEW FILE########
__FILENAME__ = test-idio
### @export "assign-variables"
x = 5
y = 7

### @export "multiply"
x * y


########NEW FILE########
__FILENAME__ = test_user_docs
from tests.utils import wrap
from dexy.node import DocNode

# Add New Files - Basic

def test_generated_files_not_added_by_default():
    with wrap() as wrapper:
        doc = DocNode("generate-data.py|py",
            contents = """with open("abc.txt", "w") as f: f.write("hello")""",
            wrapper=wrapper)
        wrapper.run_docs(doc)
        #assert not "Doc:abc.txt" in wrapper.batch.lookup_table

def test_generated_files_added_when_requested():
    with wrap() as wrapper:
        doc = DocNode("generate-data.py|py",
            contents = """with open("abc.txt", "w") as f: f.write("hello")""",
            py={"add-new-files" : True},
            wrapper=wrapper)
        wrapper.run_docs(doc)
        #assert "DocNode:abc.txt" in wrapper.batch.lookup_table

def test_generated_files_added_when_requested_underscore():
    with wrap() as wrapper:
        doc = DocNode("generate-data.py|py",
            contents = """with open("abc.txt", "w") as f: f.write("hello")""",
            py={"add_new_files" : True},
            wrapper=wrapper)
        wrapper.run_docs(doc)
        #assert "DocNode:abc.txt" in wrapper.batch.lookup_table

# Add New Files - Filter by Extension
LATEX = """\
\documentclass{article}
\\title{Hello, World!}
\\begin{document}
\maketitle
Hello!
\end{document}
"""

def test_generated_files_not_added_by_default_latex():
    with wrap() as wrapper:
        doc = DocNode("example.tex|latex",
            contents = LATEX,
            wrapper=wrapper)
        wrapper.run_docs(doc)
        #assert "DocNode:example.tex|latex" in wrapper.batch.lookup_table
        #assert not "DocNode:example.aux" in wrapper.batch.lookup_table
        #assert not "DocNode:example.log" in wrapper.batch.lookup_table
        #assert not "DocNode:example.pdf" in wrapper.batch.lookup_table

def test_generated_files_added_latex():
    with wrap() as wrapper:
        doc = DocNode("example.tex|latex",
            contents = LATEX,
            latex = {'add-new-files' : True},
            wrapper=wrapper)
        wrapper.run_docs(doc)
        #assert "DocNode:example.tex|latex" in wrapper.batch.lookup_table
        #assert "DocNode:example.aux" in wrapper.batch.lookup_table
        #assert "DocNode:example.log" in wrapper.batch.lookup_table
        #assert "DocNode:example.pdf" in wrapper.batch.lookup_table

def test_generated_files_added_latex_log_ext():
    with wrap() as wrapper:
        doc = DocNode("example.tex|latex",
            contents = LATEX,
            latex = {'add-new-files' : '.log'},
            wrapper=wrapper)
        wrapper.run_docs(doc)
        #assert "DocNode:example.tex|latex" in wrapper.batch.lookup_table
        #assert not "DocNode:example.aux" in wrapper.batch.lookup_table
        #assert "DocNode:example.log" in wrapper.batch.lookup_table
        #assert not "DocNode:example.pdf" in wrapper.batch.lookup_table

def test_generated_files_added_latex_log_ext_array():
    with wrap() as wrapper:
        doc = DocNode("example.tex|latex",
            contents = LATEX,
            latex = {'add-new-files' : ['.log']},
            wrapper=wrapper)
        wrapper.run_docs(doc)
        #assert "DocNode:example.tex|latex" in wrapper.batch.lookup_table
        #assert not "DocNode:example.aux" in wrapper.batch.lookup_table
        #assert "DocNode:example.log" in wrapper.batch.lookup_table
        #assert not "DocNode:example.pdf" in wrapper.batch.lookup_table

def test_generated_files_with_additional_filters():
    with wrap() as wrapper:
        doc = DocNode("example.tex|latex",
            contents = LATEX,
            latex = {'add-new-files' : ['.aux'], 'additional-doc-filters' : { '.aux' : 'wc' } },
            wrapper=wrapper)
        wrapper.run_docs(doc)
        #assert "DocNode:example.tex|latex" in wrapper.batch.lookup_table
        #assert "DocNode:example.aux" in wrapper.batch.lookup_table
        #assert "DocNode:example.aux|wc" in wrapper.batch.lookup_table
        #assert not "DocNode:example.log" in wrapper.batch.lookup_table
        #assert not "DocNode:example.pdf" in wrapper.batch.lookup_table

def test_generated_files_with_additional_filters_not_keeping_originals():
    with wrap() as wrapper:
        doc = DocNode("example.tex|latex",
            contents = LATEX,
            latex = {
                'add-new-files' : ['.aux'],
                'additional-doc-filters' : { '.aux' : 'wc' },
                'keep-originals' : False
                },
            wrapper=wrapper)
        wrapper.run_docs(doc)
        #assert "DocNode:example.tex|latex" in wrapper.batch.lookup_table
        #assert not "DocNode:example.aux" in wrapper.batch.lookup_table
        #assert "DocNode:example.aux|wc" in wrapper.batch.lookup_table
        #assert not "DocNode:example.log" in wrapper.batch.lookup_table
        #assert not "DocNode:example.pdf" in wrapper.batch.lookup_table

########NEW FILE########
__FILENAME__ = test_api_filters
from tests.utils import wrap
from mock import patch
import dexy.filter
import os

@patch('os.path.expanduser')
def test_docmd_create_keyfile(mod):
    mod.return_value = '.dexyapis'
    with wrap():
        assert not os.path.exists(".dexyapis")
        dexy.filter.Filter.create_instance("apis").docmd_create_keyfile()
        assert os.path.exists(".dexyapis")

########NEW FILE########
__FILENAME__ = test_archive_filters
from dexy.doc import Doc
from tests.utils import tempdir
from tests.utils import wrap
from dexy.wrapper import Wrapper
import os
import tarfile
import zipfile

def test_zip_archive_filter():
    with tempdir():
        with open("hello.py", "w") as f:
            f.write("print 'hello'")

        with open("hello.rb", "w") as f:
            f.write("puts 'hello'")

        wrapper = Wrapper()
        wrapper.create_dexy_dirs()
        wrapper = Wrapper()

        doc = Doc("archive.zip|zip",
                wrapper,
                [
                    Doc("hello.py", wrapper),
                    Doc("hello.rb", wrapper),
                    Doc("hello.py|pyg", wrapper),
                    Doc("hello.rb|pyg", wrapper)
                    ],
                contents=" ")

        wrapper.run_docs(doc)
        wrapper.report()

        path_exists = os.path.exists("output/archive.zip")
        assert path_exists
        z = zipfile.ZipFile("output/archive.zip", "r")
        names = z.namelist()
        assert "archive/hello.py" in names
        assert "archive/hello.rb" in names
        assert "archive/hello.py-pyg.html" in names
        assert "archive/hello.rb-pyg.html" in names
        z.close()

def test_archive_filter():
    with wrap() as wrapper:
        with open("hello.py", "w") as f:
            f.write("print 'hello'")

        with open("hello.rb", "w") as f:
            f.write("puts 'hello'")

        wrapper = Wrapper()
        wrapper.create_dexy_dirs()
        wrapper = Wrapper()

        doc = Doc("archive.tgz|archive",
                wrapper,
                [
                    Doc("hello.py", wrapper),
                    Doc("hello.rb", wrapper),
                    Doc("hello.py|pyg", wrapper),
                    Doc("hello.rb|pyg", wrapper)
                ],
                contents=" ")

        wrapper.run_docs(doc)
        wrapper.report()

        assert os.path.exists("output/archive.tgz")
        tar = tarfile.open("output/archive.tgz", mode="r:gz")
        names = tar.getnames()
        assert "archive/hello.py" in names
        assert "archive/hello.rb" in names
        assert "archive/hello.py-pyg.html" in names
        assert "archive/hello.rb-pyg.html" in names
        tar.close()

def test_archive_filter_with_short_names():
    with wrap() as wrapper:
        with open("hello.py", "w") as f:
            f.write("print 'hello'")

        with open("hello.rb", "w") as f:
            f.write("puts 'hello'")

        wrapper = Wrapper()
        wrapper.create_dexy_dirs()
        wrapper = Wrapper()

        doc = Doc("archive.tgz|archive",
                wrapper,
                [
                    Doc("hello.py", wrapper),
                    Doc("hello.rb", wrapper),
                    Doc("hello.py|pyg", wrapper),
                    Doc("hello.rb|pyg", wrapper)
                    ],
                contents=" ",
                archive={'use-short-names' : True}
                )

        wrapper.run_docs(doc)
        wrapper.report()


        assert os.path.exists("output/archive.tgz")
        tar = tarfile.open("output/archive.tgz", mode="r:gz")
        names = tar.getnames()
        assert "archive/hello.py" in names
        assert "archive/hello.rb" in names
        assert "archive/hello.py.html" in names
        assert "archive/hello.rb.html" in names
        tar.close()

def test_unprocessed_directory_archive_filter():
    with wrap() as wrapper:
        with open("abc.txt", "w") as f:
            f.write('this is abc')

        with open("def.txt", "w") as f:
            f.write('this is def')

        wrapper = Wrapper()
        wrapper.create_dexy_dirs()
        wrapper = Wrapper()

        doc = Doc("archive.tgz|tgzdir",
                wrapper,
                [],
                contents="ignore",
                tgzdir={'dir' : '.'}
                )
        wrapper.run_docs(doc)
        wrapper.report()

        assert os.path.exists("output/archive.tgz")
        tar = tarfile.open("output/archive.tgz", mode="r:gz")
        names = tar.getnames()

        assert ("./abc.txt" in names) or ("abc.txt" in names)
        assert ("./def.txt" in names) or ("def.txt" in names)
        tar.close()

########NEW FILE########
__FILENAME__ = test_calibre_filters
from tests.utils import wrap
from dexy.doc import Doc

HTML = """
<h1>Header</h1>
<p>This is some body.</p>
"""

def run_calibre(ext):
    with wrap() as wrapper:
        node = Doc("book.html|calibre",
                wrapper,
                [],
                calibre = { 'ext' : ext },
                contents = HTML
                )
        wrapper.run_docs(node)
        assert node.output_data().is_cached()

def test_calibre_mobi():
    run_calibre('.mobi')

def test_calibre_epub():
    run_calibre('.epub')

def test_calibre_fb2():
    run_calibre('.fb2')

def test_calibre_htmlz():
    run_calibre('.htmlz')

def test_calibre_lit():
    run_calibre('.lit')

def test_calibre_lrf():
    run_calibre('.lrf')

def test_calibre_pdf():
    run_calibre('.pdf')

def test_calibre_rtf():
    run_calibre('.rtf')

def test_calibre_snb():
    run_calibre('.snb')

def test_calibre_tcr():
    run_calibre('.tcr')

def test_calibre_txt():
    run_calibre('.txt')

def test_calibre_txtz():
    run_calibre('.txtz')

########NEW FILE########
__FILENAME__ = test_clang_filters
from tests.utils import assert_output
from tests.utils import wrap
from dexy.doc import Doc

FORTRAN_HELLO_WORLD = """program hello
   print *, "Hello World!"
end program hello
"""

CPP_HELLO_WORLD = """#include <iostream>
using namespace std;

int main()
{
	cout << "Hello, world!";

	return 0;

}
"""

C_HELLO_WORLD = """#include <stdio.h>

int main()
{
    printf("HELLO, world\\n");
}
"""

C_FUSSY_HELLO_WORLD = """#include <stdio.h>

int main()
{
    printf("HELLO, world\\n");
    return 0;
}
"""

C_WITH_INPUT = """#include <stdio.h>

int main()
{
    int c;

    c = getchar();
    while (c != EOF) {
        putchar(c);
        c = getchar();
    }
}
"""
def test_fortran_filter():
    assert_output('fortran', FORTRAN_HELLO_WORLD, "Hello, world!", ext=".f")

def test_cpp_filter():
    assert_output('cpp', CPP_HELLO_WORLD, "Hello, world!", ext=".cpp")

def test_clang_filter():
    assert_output('clang', C_HELLO_WORLD, "HELLO, world\n", ext=".c")

def test_c_filter():
    assert_output('gcc', C_HELLO_WORLD, "HELLO, world\n", ext=".c")
    assert_output('gcc', C_FUSSY_HELLO_WORLD, "HELLO, world\n", ext=".c")

def test_cfussy_filter():
    assert_output('cfussy', C_FUSSY_HELLO_WORLD, "HELLO, world\n", ext=".c")
    with wrap() as wrapper:
        wrapper.debug = False
        doc = Doc("hello.c|cfussy",
                contents=C_HELLO_WORLD,
                wrapper=wrapper)
        wrapper.run_docs(doc)
        assert wrapper.state == 'error'

def test_c_input():
    with wrap() as wrapper:
        node = Doc("copy.c|cinput",
                inputs = [
                Doc("input.txt",
                    contents = "hello, c",
                    wrapper=wrapper)
                ],
                contents = C_WITH_INPUT,
                wrapper=wrapper)

        wrapper.run_docs(node)
        assert str(node.output_data()) == "hello, c"

def test_clang_input():
    with wrap() as wrapper:
        node = Doc("copy.c|clanginput",
                inputs = [
                Doc("input.txt",
                    contents = "hello, c",
                    wrapper=wrapper)
                ],
                contents = C_WITH_INPUT,
                wrapper=wrapper)

        wrapper.run_docs(node)
        assert str(node.output_data()) == "hello, c"

def test_clang_multiple_inputs():
    with wrap() as wrapper:
        node = Doc("copy.c|clanginput",
                inputs = [
                    Doc("input1.txt",
                        contents = "hello, c",
                        wrapper=wrapper),
                    Doc("input2.txt",
                        contents = "more data",
                        wrapper=wrapper)
                ],
                contents = C_WITH_INPUT,
                wrapper=wrapper)

        wrapper.run_docs(node)
        assert unicode(node.output_data()['input1.txt']) == u'hello, c'
        assert unicode(node.output_data()['input2.txt']) == u'more data'

########NEW FILE########
__FILENAME__ = test_easyhtml_filters
from tests.utils import assert_in_output

def test_easyhtml_filter():
    some_html = "<p>This is some HTML</p>"
    assert_in_output("easyhtml", some_html, some_html, ".html")
    assert_in_output("easyhtml", some_html, "<html>", ".html")

########NEW FILE########
__FILENAME__ = test_example_filters
from dexy.doc import Doc
from tests.utils import assert_output
from tests.utils import runfilter
from tests.utils import wrap

def test_process_text_filter():
    assert_output("processtext", "hello", "Dexy processed the text 'hello'")

def test_process_method():
    assert_output("process", "hello", "Dexy processed the text 'hello'")

def test_process_method_manual_write():
    assert_output("processmanual", "hello", "Dexy processed the text 'hello'")

def test_process_method_with_dict():
    assert_output("processwithdict", "hello", {'1' : "Dexy processed the text 'hello'"})

def test_add_new_document():
    with runfilter("newdoc", "hello") as doc:
        assert doc.children[-1].key == "subdir/newfile.txt|processtext"
        assert str(doc.output_data()) == "we added a new file"

        assert "doc:subdir/example.txt|newdoc" in doc.wrapper.nodes
        assert "doc:subdir/newfile.txt|processtext" in doc.wrapper.nodes

def test_key_value_example():
    with wrap() as wrapper:
        doc = Doc(
                "hello.txt|keyvalueexample",
                wrapper,
                [],
                contents="hello"
                )

        wrapper.run_docs(doc)

        assert doc.output_data()["foo"] == "bar"
        assert str(doc.output_data()) == "KeyValue('hello.txt|keyvalueexample')"

def test_access_other_documents():
    with wrap() as wrapper:
        node = Doc("hello.txt|newdoc", wrapper, [], contents="hello")
        parent = Doc("test.txt|others",
                wrapper,
                [node],
                contents="hello"
                )
        wrapper.run_docs(parent)

        expected_items = [
            "Here is a list of previous docs in this tree (not including test.txt|others).",
            "newfile.txt|processtext (0 children, 0 inputs, length 33)",
            "hello.txt|newdoc (1 children, 0 inputs, length 19)"
            ]

        output = unicode(parent.output_data())

        for item in expected_items:
            assert item in output

########NEW FILE########
__FILENAME__ = test_git_filters
from dexy.exceptions import UserFeedback
from dexy.filters.git import repo_from_path
from dexy.filters.git import repo_from_url
from dexy.filters.git import generate_commit_info
from tests.utils import assert_in_output
from tests.utils import runfilter
from tests.utils import tempdir
from nose.exc import SkipTest
import os
import json

REMOTE_REPO_HTTPS = "https://github.com/ananelson/dexy-templates"
PATH_TO_LOCAL_REPO = os.path.expanduser("~/dev/testrepo")
# TODO use subprocess to check out a repo to a temp dir, or have a repo in data
# dir, or use [gasp] submodules.

try:
    import pygit2
    import urllib

    no_local_repo = not os.path.exists(PATH_TO_LOCAL_REPO)

    try:
        urllib.urlopen("http://google.com")
        no_internet = False
    except IOError:
        no_internet = True

    if no_local_repo:
        SKIP = (True, "No local repo at %s." % PATH_TO_LOCAL_REPO)
    elif no_internet:
        SKIP = (True, "Internet not available.")
    else:
        SKIP = (False, None)

except ImportError:
    SKIP = (True, "pygit2 not installed")

def skip():
    if SKIP[0]:
        raise SkipTest(SKIP[1])

skip()

def test_run_gitrepo():
    with runfilter("repo", REMOTE_REPO_HTTPS) as doc:
        assert len(doc.wrapper.nodes) > 20

def test_generate_commit_info():
    repo, remote = repo_from_url(REMOTE_REPO_HTTPS)

    refs = repo.listall_references()
    ref = repo.lookup_reference(refs[0])
    commit = repo[ref.target]
    commit_info = generate_commit_info(commit)

    assert commit_info['author-name'] == "Ana Nelson"
    assert commit_info['author-email'] == "ana@ananelson.com"

def test_git_commit():
    with runfilter("gitcommit", REMOTE_REPO_HTTPS) as doc:
        output = doc.output_data()
        patches = json.loads(output['patches'])
        assert output['author-name'] == "Ana Nelson"
        assert output['author-email'] == "ana@ananelson.com"
        #assert output['message'] == "Add README file."
        #assert output['hex'] == "2f15837e64a70e4d34b924f6f8c371a266d16845"

def test_git_log():
    assert_in_output("gitlog", PATH_TO_LOCAL_REPO,
            "Add README file.")

def test_git_log_remote():
    assert_in_output("gitlog", REMOTE_REPO_HTTPS,
            "Rename")

def test_repo_from_url():
    repo, remote = repo_from_url(REMOTE_REPO_HTTPS)
    assert remote.name == 'origin'
    assert remote.url == REMOTE_REPO_HTTPS

def test_repo_from_path():
    repo, remote = repo_from_path(PATH_TO_LOCAL_REPO)
    assert ".git" in repo.path
    #assert isinstance(repo.head, pygit2.Object)
    # assert "README" in repo.head.message

def test_repo_from_invalid_path():
    with tempdir():
        try:
            repo, remote = repo_from_path(".")
            assert False
        except UserFeedback as e:
            assert "no git repository was found at '.'" in str(e)

def test_run_git():
    with runfilter("git", PATH_TO_LOCAL_REPO) as doc:
        doc.output_data()

def test_run_git_remote():
    with runfilter("git", REMOTE_REPO_HTTPS) as doc:
        doc.output_data()

########NEW FILE########
__FILENAME__ = test_id_filters
from dexy.doc import Doc
from dexy.exceptions import UserFeedback
from dexy.filters.id import lexer as id_lexer
from dexy.filters.id import parser as id_parser
from dexy.filters.id import start_new_section, token_info
from tests.utils import TEST_DATA_DIR
from tests.utils import wrap
import os

def test_force_text():
    with wrap() as wrapper:
        node = Doc("example.py|idio|t",
                wrapper,
                [],
                contents="print 'hello'\n")

        wrapper.run_docs(node)
        assert str(node.output_data()) == "print 'hello'\n"

def setup_parser():
    with wrap() as wrapper:
        id_parser.outputdir = wrapper.log_dir
        id_parser.errorlog = wrapper.log
        id_lexer.outputdir = wrapper.log_dir
        id_lexer.errorlog = wrapper.log
        id_lexer.remove_leading = True
        id_parser.write_tables = False
        _lexer = id_lexer.clone()
        _lexer.sections = []
        _lexer.level = 0
        start_new_section(_lexer, 0, 0, _lexer.level)
        yield(id_parser, _lexer)

def parse(text):
    for id_parser, _lexer in setup_parser():
        id_parser.parse(text, lexer=_lexer)
        return _lexer.sections

def tokens(text):
    for id_parser, _lexer in setup_parser():
        return token_info(text, _lexer)

def test_parse_code():
    output = parse("foo\n")
    assert output[0]['contents'] == 'foo\n'

def test_parse_oldstyle_comments():
    for comment in ('###', '///', ';;;', '%%%'):
        text = "%s @export foo\nfoo\n" % comment
        output = parse(text)
        assert output[0]['name'] == 'foo'
        assert output[0]['contents'] == 'foo\n'

def test_parse_comments():
    for comment in ('###', '///', ';;;', '%%%'):
        text = "%s 'foo-bar'\nfoo\n" % comment
        output = parse(text)
        assert output[0]['name'] == 'foo-bar'
        assert output[0]['contents'] == 'foo\n'

def test_parse_closed_style_sections():
    comments = (
        "/*** @export foo1*/\n",
        "/*** @export foo1 */\n",
        "/*** @section foo1 */\n",
        "/*** @export 'foo1'*/\n",
        "/*** @export 'foo1' */\n",
        "/*** @export 'foo1' python*/\n",
        "/*** @export 'foo1' python */\n",
        """/*** @export "foo1" css */\n""",
        """/*** @export "foo1" python*/\n""",
        "<!-- @export foo1 -->\n",
        "<!-- @section foo1 -->\n"
        "<!-- section foo1 -->\n"
        "<!-- section 'foo1' -->\n"
        )

    for text in comments:
        output = parse(text)
        assert output[0]['contents'] == ''
        assert output[0]['name'] == 'foo1'

def test_parse_closed_style_end():
    comments = (
        "foo\n/*** @end */\nbar\n",
        "foo\n<!-- @end -->\nbar\n",
        "foo\n<!-- section 'end' -->\nbar\n"
        )
    for text in comments:
        output = parse(text)
        assert output[0]['contents'] == 'foo\n'
        assert output[1]['contents'] == 'bar\n'
        assert output[0]['name'] == '1'
        assert output[1]['name'] == '2'

def test_parse_closed_falsestart():
    comments = (
        "<!-- @bob -->\n",
        "/*** @bob */\n"
        )

    for text in comments:
        output = parse(text)
        assert output[0]['contents'] == text

def test_ignore_faux_comment():
    for comment in ('#', '/', '%', '##%', '//#', '%#%', '##', '//', '%%',
            '///', "foo;", "//;", ";#;"):
        text = "  %s foo bar\nfoo\n" % comment
        output = parse(text)
        assert output[0]['contents'] == text

def test_accidental_comment_in_string():
    for comment in ('###",', '%%%",', '"###",', '"%%%"', '"### (%%%)",'):
        text = "foo bar %s\n" % comment
        output = parse(text)
        assert output[0]['contents'] == text

def test_more_accidental_comments():
    for comment in ('###",', '%%%",', '"###",', '"%%%"', '"### (%%%)",'):
        text = "   %s foo bar %s\n" % (comment, comment)
        output = parse(text)
        print "INPUT IS", text
        print "OUTPUT IS", output[0]['contents']
        assert output[0]['contents'] == text

def test_malformatted_comment_does_not_throw_error():
    for comment in ('###', '///', '%%%'):
        # There should be no space in this style of section name
        text = "%s 'foo bar'\nfoo\n" % comment
        output = parse(text)
        assert output[0]['contents'] == text

def test_idio_invalid_input():
    with wrap() as wrapper:
        wrapper.debug = False
        doc = Doc("hello.py|idio",
                wrapper, [],
                contents="### @ ")
        wrapper.run_docs(doc)

def test_multiple_sections():
    with wrap() as wrapper:
        src = """
### @export "vars"
x = 6
y = 7

### @export "multiply"
x*y

"""
        doc = Doc("example.py|idio",
                wrapper,
                [],
                contents=src)

        wrapper.run_docs(doc)
        assert doc.output_data().keys() == ['1', 'vars', 'multiply']

def uest_force_latex():
    with wrap() as wrapper:
        doc = Doc("example.py|idio|l",
                wrapper,
                [],
                contents="print 'hello'\n")

        wrapper.run_docs(doc)

        assert "begin{Verbatim}" in str(doc.output_data())

def test_parse_docutils_latex():
    with open(os.path.join(TEST_DATA_DIR, "doc.tex"), "r") as f:
        latex = f.read()
    parse(latex)

def test_parse_php_mixed_tags():
    with open(os.path.join(TEST_DATA_DIR, "example.php"), "r") as f:
        php = f.read()

    output = parse(php)
    section_names = [info['name'] for info in output]

    assert "head" in section_names
    assert "assign-variables" in section_names
    assert "compare" in section_names
    assert "display-variables" in section_names

########NEW FILE########
__FILENAME__ = test_integration
from dexy.wrapper import Wrapper
from tests.utils import TEST_DATA_DIR
from tests.utils import tempdir
from tests.utils import wrap
import dexy.doc
import dexy.node
import inspect
import os
import random
import shutil

LOGLEVEL = "WARN"

def assert_node_state(node, expected, additional_info=''):
    msg = "'%s' not in state '%s',  in state '%s'. %s"
    msgargs = (node.key, expected, node.state, additional_info)
    assert node.state == expected, msg % msgargs

def test_example_project():
    with tempdir():
        def run_from_cache_a_bunch_of_times():
            n = random.randint(2, 10)
            print "running %s times:" % n
            for i in range(n):
                print '', i+1
                wrapper = Wrapper(log_level=LOGLEVEL, debug=True)
                wrapper.run_from_new()
    
                for node in wrapper.nodes.values():
                    assert_node_state(node, 'consolidated', "In iter %s" % i)

                wrapper.report()

        example_src = os.path.join(TEST_DATA_DIR, 'example')
        shutil.copytree(example_src, "example")
        os.chdir("example")

        wrapper = Wrapper(log_level=LOGLEVEL)
        wrapper.create_dexy_dirs()

        wrapper.run_from_new()
        wrapper.report()

        for node in wrapper.nodes.values():
            assert_node_state(node, 'ran', "in first run")

        run_from_cache_a_bunch_of_times()

        # touch this file so it triggers cache updating
        os.utime("multiply.py", None)

        unaffected_keys = ('latex', 'pygments.sty|pyg', 's1/loop.py|pycon', 's1/loop.py|py',
                'main.rst|idio|h', 'main.rst|idio|l', 'main.rst|pyg|l', 'main.rst|pyg|h',
                's1/loop.py|idio|h', 's1/loop.py|idio|l', 's1/loop.py|pyg|l', 's1/loop.py|pyg|h',
                'dexy.yaml|idio|h', 'dexy.yaml|idio|l', 'dexy.yaml|pyg|l', 'dexy.yaml|pyg|h',
                )

        affected_keys = ('code', 'docs', "*|pyg|l", "*|pyg|h", "*|idio|l", "*|idio|h",
                "main.rst|jinja|rst|latex", "*.rst|jinja|rst|latex",
                "*.py|pycon", "*.py|py", "main.rst|jinja|rstbody|easyhtml",
                "*.rst|jinja|rstbody|easyhtml", "foo.txt",
                "multiply.py|idio|h", "multiply.py|idio|l", "multiply.py|pycon", "multiply.py|py",
                "multiply.py|pyg|h", "multiply.py|pyg|l",
                )

        wrapper = Wrapper(log_level=LOGLEVEL)
        wrapper.run_from_new()
        wrapper.report()

        for node in wrapper.nodes.values():
            if node.key in unaffected_keys:
                assert_node_state(node, 'consolidated', "after touching multiply.py")
            else:
                assert node.key in affected_keys, node.key
                assert_node_state(node, 'ran', "after touchimg multiply.py")

        run_from_cache_a_bunch_of_times()

        import time
        time.sleep(0.5)

        with open("multiply.py", "r") as f:
            old_content = f.read()
        
        with open("multiply.py", "w") as f:
            f.write("raise")

        wrapper = Wrapper(log_level=LOGLEVEL)
        wrapper.run_from_new()
        assert wrapper.state == 'error'

        import time
        time.sleep(0.9)

        with open("multiply.py", "w") as f:
            f.write(old_content)

        wrapper = Wrapper(log_level=LOGLEVEL)
        wrapper.run_from_new()

        for node in wrapper.nodes.values():
            if node.key in unaffected_keys:
                assert_node_state(node, 'consolidated', "after restoring old multiply.py content")
            else:
                assert node.key in affected_keys, node.key
                assert_node_state(node, 'ran', "after restoring old multiply.py contnet")

        wrapper.remove_dexy_dirs()
        wrapper.remove_reports_dirs(keep_empty_dir=True)
        wrapper.create_dexy_dirs()

        assert len(os.listdir(".dexy")) == 1

        wrapper = Wrapper(log_level=LOGLEVEL, dry_run=True)
        wrapper.run_from_new()
        wrapper.report()

        assert len(os.listdir(".dexy")) == 6

        with open(".dexy/reports/graph.txt", "r") as f:
            graph_text = f.read()

        assert "BundleNode(docs) (uncached)" in graph_text

        os.chdir("..")

def test_ragel_state_chart_to_image():
    ragel = inspect.cleandoc("""
        %%{
          machine hello_and_welcome;
          main := ( 'h' @ { puts "hello world!" }
                  | 'w' @ { puts "welcome" }
                  )*;
        }%%
          data = 'whwwwwhw'
          %% write data;
          %% write init;
          %% write exec;
        """)
    with wrap() as wrapper:
        graph_png = dexy.doc.Doc("example.rl|rlrbd|dot",
                wrapper,
                [],
                contents=ragel
                )

        syntax = dexy.doc.Doc("example.rl|rlrbd|pyg",
                wrapper,
                [],
                contents=ragel
                )

        wrapper.run_docs(graph_png, syntax)
        assert graph_png.state == 'ran'
        assert syntax.state == 'ran'

########NEW FILE########
__FILENAME__ = test_java_filters
from dexy.doc import Doc
from tests.utils import assert_in_output
from tests.utils import assert_output
from tests.utils import wrap
from nose.exc import SkipTest

JAVA_SRC = """public class hello {
  public static void main(String args[]) {
    System.out.println("Java Hello World!");
  }
}"""

def test_javac_filter():
    # not using runfilter() because file has to be named 'hello.java'
    with wrap() as wrapper:
        doc = Doc("hello.java|javac",
                wrapper,
                [],
                contents=JAVA_SRC)
        wrapper.run_docs(doc)
        assert doc.output_data().is_cached()

def test_java_filter():
    # not using runfilter() because file has to be named 'hello.java'
    with wrap() as wrapper:
        doc = Doc("hello.java|java",
                wrapper,
                [],
                contents=JAVA_SRC)
        wrapper.run_docs(doc)
        assert str(doc.output_data()) == "Java Hello World!\n"

def test_jruby_filter():
    assert_output('jruby', "puts 1+1", "2\n")

def test_jirb_filter():
    assert_in_output('jirb', "puts 1+1",  ">> puts 1+1")

def test_jython_filter():
    assert_output('jython', "print 1+1", "2\n")

def test_jythoni_filter():
    raise SkipTest()
    assert_in_output('jythoni', "print 1+1",  ">>> print 1+1")

########NEW FILE########
__FILENAME__ = test_kramdown_filters
from tests.utils import TEST_DATA_DIR
from dexy.doc import Doc
from tests.utils import wrap
import os

markdown_file = os.path.join(TEST_DATA_DIR, "markdown-test.md")

def run_kramdown(ext):
    with open(markdown_file, 'r') as f:
        example_markdown = f.read()

    with wrap() as wrapper:
        node = Doc("markdown.md|kramdown",
                wrapper,
                [],
                kramdown = { 'ext' : ext },
                contents = example_markdown
                )
        wrapper.run_docs(node)
        assert node.output_data().is_cached()
        return node.output_data()

def test_kramdown_html():
    html = unicode(run_kramdown(".html"))
    assert """<h2 id="download">""" in html

def test_kramdown_tex():
    tex = unicode(run_kramdown(".tex"))
    assert u"\subsection" in tex

########NEW FILE########
__FILENAME__ = test_latex_filters
from tests.utils import runfilter
from tests.utils import wrap
from dexy.doc import Doc

def test_latex():
    with runfilter('latex', LATEX) as doc:
        assert ".pdf" in doc.output_data().name
        assert doc.output_data().is_cached()

def test_latex_dvi():
    with runfilter('latexdvi', LATEX) as doc:
        assert ".dvi" in doc.output_data().name
        assert doc.output_data().is_cached()

def test_tikz():
    with runfilter('tikz', TIKZ) as doc:
        assert ".pdf" in doc.output_data().name
        assert doc.output_data().is_cached()

def test_broken_latex():
    with wrap() as wrapper:
        wrapper.debug = False
        node = Doc("example.tex|latex",
                wrapper,
                [],
                contents = BROKEN_LATEX
                )
        wrapper.run_docs(node)
        assert wrapper.state == 'error'

TIKZ = """\
\\tikz \draw (0,0) -- (1,1)
{[rounded corners] -- (2,0) -- (3,1)}
-- (3,0) -- (2,1);
"""
LATEX = """\
\documentclass{article}
\\title{Hello, World!}
\\begin{document}
\maketitle
Hello!
\end{document}
"""

BROKEN_LATEX = """\
\documentclass{article}
"""

########NEW FILE########
__FILENAME__ = test_lyx_filters
from tests.utils import assert_output

def test_lyx():
    assert_output("lyxjinja",
            "dexy:foo.py|idio:multiply",
            "<< d['foo.py|idio']['multiply'] >>",
            ".tex")

########NEW FILE########
__FILENAME__ = test_pexpect_filters
from dexy.doc import Doc
from tests.utils import assert_in_output
from tests.utils import wrap
from nose.exc import SkipTest

def test_shint_filter():
    with wrap() as wrapper:
        src = """
### @export "touch"
touch newfile.txt

### @export "ls"
ls
"""
        doc = Doc("example.sh|idio|shint|pyg",
                wrapper,
                [],
                contents = src)
        wrapper.run_docs(doc)

        assert doc.output_data().keys() == ['1', 'touch', 'ls']

SCALA = """object HelloWorld {
    def main(args: Array[String]) {
      println("Hello, world!")
    }
  }
"""

def test_scala_repl():
    raise SkipTest()
    with wrap() as wrapper:
        doc = Doc("HelloWorld.scala|scalai",
                wrapper,
                [],
                contents = SCALA
                )
        wrapper.run_docs(doc)
        assert "defined module HelloWorld" in str(doc.output_data())

RUST = """fn main() {
    io::println("hello?");
}"""

def test_rust_interactive():
    raise SkipTest("Need to get rust interactive filter working.")
    with wrap() as wrapper:
        doc = Doc("example.rs|rusti",
                wrapper,
                [],
                contents = "1+1"
                )
        wrapper.run_docs(doc)
        assert "rusti> 1+1\n2" in str(doc.output_data())

def test_rust():
    with wrap() as wrapper:
        doc = Doc("example.rs|rustc",
                wrapper,
                [],
                contents = RUST
                )
        wrapper.run_docs(doc)
        assert str(doc.output_data()) == "hello?\n"

PYTHON_CONTENT = """
x = 6
y = 7
"""
def test_python_filter_record_vars():
    with wrap() as wrapper:
        doc = Doc("example.py|pycon",
                wrapper,
                [],
                pycon = { 'record-vars' :  True},
                contents = PYTHON_CONTENT
                )

        wrapper.run_docs(doc)
        assert "doc:example.py-vars.json" in wrapper.nodes

def test_matlab_filter():
    raise SkipTest()
    assert_in_output('matlabint', "fprintf (1, 'Hello, world\\n')\n", "< M A T L A B (R) >")

def test_clj_filter():
    assert_in_output('cljint', '1+1', "user=> 1+1")

def test_ksh_filter():
    assert_in_output('kshint', 'ls', "example.txt")

def test_php_filter():
    assert_in_output('phpint', '1+1', "php > 1+1")

def test_rhino_filter():
    assert_in_output('rhinoint', '1+1', "js> 1+1")

def test_irb_filter():
    assert_in_output('irb', "puts 'hello'", ">> puts 'hello'")

def test_pycon_filter_single_section():
    assert_in_output('pycon', "print 'hello'", ">>> print 'hello'")

def test_ipython_filter():
    assert_in_output('ipython', "print 'hello'", ">>> print 'hello'")

def test_r_filter():
    assert_in_output('r', '1+1', '> 1+1')

def test_pycon_filter():
    with wrap() as wrapper:
        src = """
### @export "vars"
x = 6
y = 7

### @export "multiply"
x*y

"""
        node = Doc("example.py|idio|pycon",
                wrapper,
                [],
                contents=src)

        wrapper.run_docs(node)

        assert node.output_data().keys() == ['1', 'vars', 'multiply']
        assert str(node.output_data()['vars']) == """
>>> x = 6
>>> y = 7"""

        assert str(node.output_data()['multiply']) == """
>>> x*y
42"""


########NEW FILE########
__FILENAME__ = test_phantomjs_filters
from dexy.doc import Doc
from tests.utils import TEST_DATA_DIR
from tests.utils import assert_output
from tests.utils import runfilter
from tests.utils import wrap
from nose.exc import SkipTest
import os
import shutil

def test_phantomjs_render_filter():
    with runfilter("phrender", "<p>hello</p>") as doc:
        assert doc.output_data().is_cached()

def test_phantomjs_stdout_filter():
    assert_output('phantomjs', PHANTOM_JS, "Hello, world!\n")

def test_casperjs_svg2pdf_filter():
    # TODO find smaller file - make test go faster?
    with wrap() as wrapper:
        orig = os.path.join(TEST_DATA_DIR, 'butterfly.svg')
        shutil.copyfile(orig, 'butterfly.svg')

        from dexy.wrapper import Wrapper
        wrapper = Wrapper()

        node = Doc("butterfly.svg|svg2pdf", wrapper)

        wrapper.run_docs(node)

        assert node.output_data().is_cached()
        assert node.output_data().filesize() > 1000

def test_casperjs_stdout_filter():
    with wrap() as wrapper:
        node = Doc("example.js|casperjs",
                wrapper,
                [],
                contents=CASPER_JS,
                casperjs={"add-new-files" : True }
                )

        wrapper.run_docs(node)

        try:
            assert 'doc:google.pdf' in wrapper.nodes
            assert 'doc:cookies.txt' in wrapper.nodes
        except AssertionError:
            pass

PHANTOM_JS = """
console.log('Hello, world!');
phantom.exit();
"""

CASPER_JS = """
var links = [];
var casper = require('casper').create();

casper.start('http://google.com/', function() {
    this.capture('google.pdf');
});

casper.run();
"""

########NEW FILE########
__FILENAME__ = test_process_filters
from dexy.doc import Doc
from dexy.filters.process import SubprocessFilter
from tests.utils import wrap
import dexy.exceptions
import os

def test_add_new_files():
    with wrap() as wrapper:
        node = Doc("example.sh|sh",
                wrapper,
                [],
                contents = "echo 'hello' > newfile.txt",
                sh = {
                    "add-new-files" : True,
                    "keep-originals" : True,
                    "additional-doc-filters" : { '.txt' : 'markdown' }
                    }
                )
        wrapper.run_docs(node)

        assert str(wrapper.nodes['doc:newfile.txt'].output_data()) == "hello" + os.linesep
        assert str(wrapper.nodes['doc:newfile.txt|markdown'].output_data()) == "<p>hello</p>"

def test_not_present_executable():
    # TODO modify test so we try to run this
    dexy.filter.Filter.create_instance('notreal')

class NotPresentExecutable(SubprocessFilter):
    """
    notreal
    """
    EXECUTABLE = 'notreal'
    aliases = ['notreal']

def test_command_line_args():
    with wrap() as wrapper:
        node = Doc("example.py|py",
                wrapper,
                [],
                py={"args" : "-B"},
                contents="print 'hello'"
                )
        wrapper.run_docs(node)

        assert str(node.output_data()) == "hello" + os.linesep

        command_used = node.filters[-1].command_string()
        assert command_used == "python -B  \"example.py\" "

def test_scriptargs():
    with wrap() as wrapper:
        node = Doc("example.py|py",
                wrapper,
                [],
                py={"scriptargs" : "--foo"},
                contents="""import sys\nprint "args are: '%s'" % sys.argv[1]"""
                )
        wrapper.run_docs(node)

        assert "args are: '--foo'" in str(node.output_data())

        command_used = node.filters[-1].command_string()
        assert command_used == "python   \"example.py\" --foo"

def test_custom_env_in_args():
    with wrap() as wrapper:
        node = Doc("example.py|py",
                wrapper,
                [],
                py={"env" : {"FOO" : "bar" }},
                contents="import os\nprint os.environ['FOO']"
                )
        wrapper.run_docs(node)

        assert str(node.output_data()) == "bar" + os.linesep

def test_nonzero_exit():
    with wrap() as wrapper:
        wrapper.debug = False
        node = Doc("example.py|py",
                wrapper,
                [],
                contents="import sys\nsys.exit(1)"
                )
        wrapper.run_docs(node)
        assert wrapper.state == 'error'

def test_ignore_nonzero_exit():
    with wrap() as wrapper:
        wrapper.ignore_nonzero_exit = True
        node = Doc("example.py|py",
                wrapper,
                [],
                contents="import sys\nsys.exit(1)"
                )
        wrapper.run_docs(node)
        assert True # no NonzeroExit was raised...

########NEW FILE########
__FILENAME__ = test_pydoc_filters
from tests.utils import wrap
from dexy.doc import Doc

def test_pydoc_filter_on_module_names():
    with wrap() as wrapper:
        doc = Doc("modules.txt|pydoc", wrapper, [], contents="os math")
        wrapper.run_docs(doc)
        data = doc.output_data()
        assert len(data.keys()) > 100
        assert data['math.e:value'].startswith("2.71828")

python_file_content = """
import math

# Comment for foo
def foo():
    '''
    docstring for foo
    '''
    return True

# Comment for bar
def bar():
    '''
    docstring for bar
    '''
    return False

"""

def test_pydoc_filter_on_python_files():
    with wrap() as wrapper:
        doc = Doc("source.py|pydoc", wrapper, [], contents=python_file_content)
        wrapper.run_docs(doc)

        data = doc.output_data()
        keys = data.keys()

        assert 'bar:source' in keys
        assert 'foo:source' in keys
        
        assert data['foo:doc'] == "docstring for foo"
        assert data['foo:comments'] == "# Comment for foo\n"

        assert data['bar:doc'] == "docstring for bar"
        assert data['bar:comments'] == "# Comment for bar\n"
        

########NEW FILE########
__FILENAME__ = test_pygments_filters
from dexy.doc import Doc
from tests.utils import assert_in_output
from tests.utils import assert_output
from tests.utils import assert_output_cached
from tests.utils import wrap

def test_pyg4rst():
    o = {}
    o['1'] = ".. code:: python\n\n  print 'hello'"
    assert_output("pyg4rst", "print 'hello'", o, ext=".py")

def test_html():
    assert_in_output("pyg|h", "print 'hello'", """<div class="highlight">""")

def test_png():
    assert_output_cached("pyg|pn", "print 'hello'")

def test_jpg():
    assert_output_cached("pyg|jn", "print 'hello'")

def test_gif():
    assert_output_cached("pyg|gn", "print 'hello'")

def test_pyg4rst_bad_file_extension():
    with wrap() as wrapper:
        wrapper.debug = False
        doc = Doc(
                "hello.xyz|pyg4rst",
                wrapper,
                [],
                contents=" ",
                pyg4rst = { 'allow_unknown_ext' : False }
                )
        wrapper.run_docs(doc)
        assert wrapper.state == 'error'

def test_pygments_bad_file_extension():
    with wrap() as wrapper:
        wrapper.debug = False
        doc = Doc(
                "hello.xyz|pyg",
                wrapper,
                [],
                contents=" ",
                pyg = { 'allow_unknown_ext' : False }
                )
        wrapper.run_docs(doc)
        assert wrapper.state == 'error'

def test_pygments_line_numbering():
    with wrap() as wrapper:
        doc = Doc(
                "hello.py|pyg",
                wrapper,
                [],
                contents=" ",
                pyg = { 'linenos' : True }
                )
        wrapper.run_docs(doc)
        assert "<pre>1</pre>" in str(doc.output_data())

def test_pygments_line_numbering_latex():
    with wrap() as wrapper:
        doc = Doc(
                "hello.py|pyg|l",
                wrapper,
                [],
                contents=" ",
                pyg = { 'linenos' : True }
                )
        wrapper.run_docs(doc)
        assert "firstnumber=1" in str(doc.output_data())

def test_pygments_line_numbering_latex_alt():
    with wrap() as wrapper:
        doc = Doc(
                "hello.py|pyg|l",
                wrapper,
                [],
                contents=" ",
                pyg = { 'line-numbers' : True }
                )
        wrapper.run_docs(doc)
        assert "firstnumber=1" in str(doc.output_data())

########NEW FILE########
__FILENAME__ = test_pytest_filters
from tests.utils import wrap
from dexy.doc import Doc
from nose.exc import SkipTest

def test_pytest_filter():
    raise SkipTest() # this is running dexy's tests, not cashew's tests
    with wrap() as wrapper:
        doc = Doc(
                "modules.txt|pytest",
                wrapper,
                [],
                contents="cashew"
                )
        wrapper.run_docs(doc)
        data = doc.output_data()

        testname = "test_cashew.test_standardize_alias_or_aliases"
        assert data[testname + ':doc'] == "docstring for test"
        assert data[testname + ':name'] == "test_standardize_alias_or_aliases"
        assert data[testname + ':comments'] == "# comment before test\n"
        assert bool(data[testname + ':passed'])
        assert "def test_standardize_alias_or_aliases():" in data[testname + ':source']

########NEW FILE########
__FILENAME__ = test_reporters
import os
from dexy.doc import Doc
from tests.utils import wrap

def test_output_reporter():
    with wrap() as wrapper:
        wrapper.reports = "output"
        doc = Doc("hello.txt", wrapper, [], contents="hello")
        wrapper.run_docs(doc)
        wrapper.report()
        assert os.path.exists("output")
        assert os.path.exists("output/hello.txt")

########NEW FILE########
__FILENAME__ = test_restructured_test_filters
from tests.utils import assert_output
from tests.utils import assert_in_output
from tests.utils import wrap
from dexy.doc import Doc

rst_meta = """
==========
Main Title
==========

---
Foo
---

:Author: J Random Hacker
:Authors: Bert & Ernie
:Contact: jrh@example.com
:Date: 2002-08-18
:Status: Work In Progress
:Version: 1
:Filename: $RCSfile$
:Copyright: This document has been placed in the public domain.

Here's some content.

"""
def test_rst_meta():
    with wrap() as wrapper:
        node = Doc("example.rst|rstmeta",
                wrapper, 
                [],
                contents = rst_meta
                )
        wrapper.run_docs(node)

        assert node.setting('author') == "J Random Hacker"
        assert node.setting('authors') == "Bert & Ernie"
        assert node.setting('subtitle') == "Foo"
        assert node.setting('title') == "Main Title"
        assert node.setting('date') == "2002-08-18"
        assert node.setting('status') == "Work In Progress"
        assert node.setting('version') == "1"
        assert node.setting('copyright') == "This document has been placed in the public domain."

RST = """
* a bullet point using "*"

  - a sub-list using "-"

    + yet another sub-list

  - another item
"""

def test_rst2odt():
    with wrap() as wrapper:
        node = Doc("example.txt|rst2odt",
                wrapper,
                [],
                contents=RST)
        wrapper.run_docs(node)
        assert node.output_data().filesize() > 8000

def test_rst2xml():
    assert_in_output('rst2xml', RST, """<list_item><paragraph>a sub-list using "-"</paragraph><bullet_list bullet="+"><list_item>""")

def test_rst2latex():
    assert_in_output('rst2latex', RST, "\item a bullet point using")
    assert_in_output('rst2latex', RST, "\\begin{document}")

def test_rst2html():
    assert_in_output('rst2html', RST, "<html xmlns")
    assert_in_output('rst2html', RST, "<li>a bullet point using &quot;*&quot;<ul>")

def test_rest_to_tex():
    with wrap() as wrapper:
        node = Doc("example.txt|rstbody",
                wrapper,
                [],
                contents=RST,
                rstbody={"ext" : ".tex"}
                )

        wrapper.run_docs(node)
        assert "\\begin{itemize}" in str(node.output_data())

def test_rest_to_html():
    expected = """\
<ul class="simple">
<li>a bullet point using &quot;*&quot;<ul>
<li>a sub-list using &quot;-&quot;<ul>
<li>yet another sub-list</li>
</ul>
</li>
<li>another item</li>
</ul>
</li>
</ul>
"""

    assert_output('rstbody', RST, expected)

def test_rstbody_latex():
    with wrap() as wrapper:
        node = Doc("example.rst|rstbody",
                wrapper, 
                [],
                rstbody = { 'ext' : '.tex' },
                contents = RST
                )
        wrapper.run_docs(node)
        output = unicode(node.output_data())
        assert "\\begin{itemize}" in output

########NEW FILE########
__FILENAME__ = test_r_filters
from tests.utils import TEST_DATA_DIR
from dexy.doc import Doc
from tests.utils import wrap
import os

sweave_file = os.path.join(TEST_DATA_DIR, "example-2.Snw")

def test_sweave_filter():
    with open(sweave_file, 'r') as f:
        sweave_content = f.read()

    with wrap() as wrapper:
        node = Doc("example.Snw|sweave",
                wrapper,
                [],
                contents = sweave_content
              )
        wrapper.run_docs(node)
        assert node.output_data().is_cached()
        assert "Coefficients:" in unicode(node.output_data())

########NEW FILE########
__FILENAME__ = test_sanitize_filters
from tests.utils import assert_output

def test_bleach_filter():
    assert_output("bleach", "an <script>evil()</script> example", u'an &lt;script&gt;evil()&lt;/script&gt; example')
    assert_output("bleach", "an <script>evil()</script> example", u'an &lt;script&gt;evil()&lt;/script&gt; example', ext=".html")

########NEW FILE########
__FILENAME__ = test_soup_filters
from tests.utils import runfilter

def test_nested_html():
    with runfilter('soups', nested_html) as doc:
        data = doc.output_data()
        assert unicode(data) == expected
        assert data.keys() == [u'First', u'Second', u'Actual Document Contents']

def test_markdown_output():
    with runfilter('markdown|soups', md) as doc:
        data = doc.output_data()

        assert data.keys() == [u'foo', u'bar', u'barbaz', u'Actual Document Contents']

        assert data['foo']['level'] == 1
        assert data['bar']['level'] == 1
        assert data['barbaz']['level'] == 2

        assert data['foo']['id'] == 'foo'
        assert data['bar']['id'] == 'bar'
        assert data['barbaz']['id'] == 'barbaz'

def test_soup_sections_filter():
    with runfilter('soups', html, ext='.html') as doc:
        data = doc.output_data()

        assert data.keys() == [u'The First Named Section',
                u'Nested In First Section', u'The 2nd Section',
                u'Actual Document Contents']

        first_section = data["The First Named Section"]
        assert first_section['contents'] == None
        assert first_section['level'] == 1

        nested_section = data["Nested In First Section"]
        assert nested_section['level'] == 2
        assert first_section['contents'] == None

        final_section = data["The 2nd Section"]
        assert final_section['level'] == 1
        assert final_section['contents'] == None

        contents_section = data['Actual Document Contents']
        assert contents_section['level'] == 1

def test_no_blank_anonymous_first_section():
    with runfilter('soups', "<h1>first</h1><p>foo</p><h1>second</h1>", ext=".html") as doc:
        assert doc.output_data().keys() == [u'first', u'second', u'Actual Document Contents']

nested_html = """<div>
<h1>First</h1>
<div>
<h2>Second</h2>
</div>
</div>"""

expected = u"""<div>
<h1 id="first">First</h1>
<div>
<h2 id="second">Second</h2>
</div>
</div>"""

md = """# foo

This is the foo section.

# bar

This is the bar section.

## barbaz

This is the barbaz section.

"""

html = """
<p>Text before the first section</p>
<H1>The First Named Section</H1>
<p>Some content in the first section.</p>
<h2>Nested In First Section</h2>
<p>Content in the nested section.</p>
<ul>
<li>list item the first</li>
<li>list item the second</li>
</ul>
<h1>The 2nd Section</h1>
<p>foo.</p>
"""

########NEW FILE########
__FILENAME__ = test_split_filters
from tests.utils import wrap
from dexy.doc import Doc

def test_split_html_filter():
    with wrap() as wrapper:
        contents="""
        <p>This is at the top.</p>
        <!-- split "index" -->
        index page content only
        <!-- split "a-page" -->
        some content on a page
        <!-- split "another-page" -->
        This is information about "another-page" which should appear on the index page.
        <!-- content -->
        some content on another page
        <!-- footer -->
        footer on index page only
        <!-- endsplit -->
        bottom
        """

        node = Doc("subdir/example.html|splithtml", wrapper, [], contents=contents)
        wrapper.run_docs(node)

        assert node.children[0].key == "subdir/a-page.html"
        assert node.children[1].key == "subdir/another-page.html"

        od = str(node.output_data())

        assert "<p>This is at the top.</p>" in od
        assert 'index page content only' in od
        assert '<a href="a-page.html">' in od
        assert '<a href="another-page.html">' in od
        assert "This is information about \"another-page\"" in od
        assert "bottom" in od

        od = str(node.children[0].output_data())
        assert "<p>This is at the top.</p>" in od
        assert not 'index page content only' in od
        assert "some content on a page" in od
        assert "bottom" in od

        od = str(node.children[1].output_data())
        assert "<p>This is at the top.</p>" in od
        assert "some content on another page" in od
        assert "bottom" in od

def test_split_html_additional_filters():
    with wrap() as wrapper:
        contents="""
        <p>This is at the top.</p>
        <!-- split "a-page" -->
        some content on a page
        <!-- split "another-page" -->
        some content on another page
        <!-- endsplit -->
        bottom
        """

        node = Doc("example.html|splithtml",
                wrapper,
                [],
                contents=contents,
                splithtml = { "keep-originals" : False, "additional-doc-filters" : "processtext" },
              )
        wrapper.run_docs(node)

        assert node.children[0].key == "a-page.html|processtext"
        assert node.children[1].key == "another-page.html|processtext"

        od = str(node.output_data())
        assert "<p>This is at the top.</p>" in od
        assert '<a href="a-page.html">' in od
        assert '<a href="another-page.html">' in od
        assert "bottom" in od

        a_page = node.children[0]
        a_page_data = str(a_page.output_data())
        assert "<p>This is at the top.</p>" in a_page_data
        assert "some content on a page" in a_page_data
        assert "bottom" in a_page_data
        assert "Dexy processed the text" in a_page_data

        another_page = node.children[1]
        another_page_data = str(another_page.output_data())
        assert "<p>This is at the top.</p>" in another_page_data
        assert "some content on another page" in another_page_data
        assert "bottom" in another_page_data
        assert "Dexy processed the text" in another_page_data

########NEW FILE########
__FILENAME__ = test_standard_filters
from dexy.doc import Doc
from tests.utils import assert_output
from tests.utils import wrap
import json
import os

def test_header_footer_filters():
    with wrap() as wrapper:
        os.makedirs('subdir/subsubdir')
        node = Doc("subdir/file.txt|hd|ft",
                wrapper,
                [
                    Doc("_header.txt", wrapper, [], contents="This is a header in parent dir."),
                    Doc("subdir/_header.txt|jinja", wrapper, [], contents="This is a header."),
                    Doc("subdir/_footer.txt|jinja", wrapper, [], contents="This is a footer."),
                    Doc("subdir/subsubdir/_header.txt", wrapper, [], contents="This is a header in a subdirectory.")
                    ],
                contents="These are main contents."
                )

        wrapper.run_docs(node)
        assert str(node.output_data()) == "This is a header.\nThese are main contents.\nThis is a footer."

def test_join_filter():
    contents = json.loads("""[{},
    {"name" : "1", "contents" : "section one" },
    {"name" : "2", "contents" : "section two" }
    ]""")
    assert_output("join", contents, "section one\nsection two")

def test_head_filter():
    assert_output("head", "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n", "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n")

def test_word_wrap_filter():
    with wrap() as wrapper:
        node = Doc("example.txt|wrap", wrapper, [], contents="this is a line of text", wrap={"width" : 5})
        wrapper.run_docs(node)
        assert str(node.output_data()) == "this\nis a\nline\nof\ntext"

def test_lines_filter():
    expected = {}
    expected['1'] = "line one"
    expected['2'] = "line two"
    assert_output("lines", "line one\nline two", expected)

def test_ppjson_filter():
    assert_output(
            "ppjson",
            '{"foo" :123, "bar" :456}',
            """{\n    "bar": 456, \n    "foo": 123\n}"""
            )

def test_start_space_filter():
    o = {}
    o['1'] = " abc\n def"
    assert_output("startspace", "abc\ndef", o)

def test_tags_filter():
    with wrap() as wrapper:
        node = Doc("example.txt|tags", wrapper, [], contents="<p>the text</p>", tags={"tags" : ["html", "body"]})
        wrapper.run_docs(node)
        assert str(node.output_data()) == "<html><body>\n<p>the text</p>\n</body></html>"


########NEW FILE########
__FILENAME__ = test_stdout_filters
from tests.utils import assert_in_output
from tests.utils import assert_output
from tests.utils import assert_output_matches
import inspect
import os

def test_node():
    assert_output("nodejs", "console.log('hello');", "hello\n")

def test_rd():
    rd = """
     \\name{load}
     \\alias{load}
     \\title{Reload Saved Datasets}
     \description{
       Reload the datasets written to a file with the function
       \code{save}.
     }
    """
    expected = u"Reload the datasets written to a file with the function \u2018save\u2019."
    assert_in_output('rdconv', rd, expected, ext=".Rd")

def test_redcloth():
    expected = "<p>hello <strong>bold</strong></p>" + os.linesep
    assert_output("redcloth", "hello *bold*", expected)

def test_redclothl():
    expected = "hello \\textbf{bold}" + os.linesep + os.linesep
    assert_output("redclothl", "hello *bold*", expected)

def test_lynxdump():
    assert_output_matches('lynxdump', "<p>hello</p>", "\s*hello\s*", ext=".html")

def test_strings():
    assert_output('strings', "hello\bmore", "hello\nmore\n")

def test_php():
    php = inspect.cleandoc("""<?php
    echo(1+1);
    ?>""")
    assert_output('php', php, "2")

def test_ragel_ruby_dot():
    ragel = inspect.cleandoc("""
        %%{
          machine hello_and_welcome;
          main := ( 'h' @ { puts "hello world!" }
                  | 'w' @ { puts "welcome" }
                  )*;
        }%%
          data = 'whwwwwhw'
          %% write data;
          %% write init;
          %% write exec;
        """)
    assert_in_output('ragelrubydot', ragel, "digraph hello_and_welcome", ext=".rl")

def test_python():
    assert_output('py', 'print 1+1', "2" + os.linesep)

def test_bash():
    assert_output('bash', 'echo "hello"', "hello\n")

def test_rhino():
    assert_output('rhino', "print(6*7)", "42\n")

def test_cowsay():
    assert_in_output('cowsay', 'hello', 'hello')

def test_cowthink():
    assert_in_output('cowthink', 'hello', 'hello')

def test_figlet():
    assert_in_output('figlet', 'hello', "| |__   ___| | | ___  ")

def test_man_page():
    assert_in_output('man', 'ls', 'list directory contents')

def test_ruby():
    assert_output('rb', 'puts "hello"', "hello\n")

def test_sloccount():
    assert_in_output('sloccount', 'puts "hello"', "ruby=1", ext=".rb")

def test_irb_subprocess_stdout_filter():
    assert_in_output('irbout', 'puts "hello"', '> puts "hello"')

def test_lua():
    assert_output('lua', 'print ("Hello")', "Hello\n")

def test_wiki2beamer():
    wiki = inspect.cleandoc("""==== A simple frame ====
    * with a funky
    * bullet list
    *# and two
    *# numbered sub-items
    """)

    assert_in_output('wiki2beamer', wiki, "\\begin{frame}")
    assert_in_output('wiki2beamer', wiki, "\\begin{enumerate}")

########NEW FILE########
__FILENAME__ = test_stdout_input_filters
from dexy.doc import Doc
from tests.utils import wrap
import json

REGETRON_INPUT_1 = "hello\n"
REGETRON_INPUT_2 = """\
this is some text
9
nine
this is 100 mixed text and numbers
"""

def test_regetron_filter():
    with wrap() as wrapper:
        wrapper.debug = False
        node = Doc("example.regex|regetron",
                wrapper,
                [
                    Doc("input1.txt",
                        wrapper,
                        [],
                        contents=REGETRON_INPUT_1),
                    Doc("input2.txt",
                        wrapper,
                        [],
                        contents=REGETRON_INPUT_2)
                    ],
                contents="^[a-z\s]+$"
                )

        wrapper.run_docs(node)
        
        if not wrapper.state == 'error':
            assert str(node.output_data()['input1.txt']) == """\
> ^[a-z\s]+$
0000: hello
> 

"""
            assert str(node.output_data()['input2.txt']) == """\
> ^[a-z\s]+$
0000: this is some text
0002: nine
> 

"""

def test_used_filter():
    with wrap() as wrapper:
        node = Doc("input.txt|used",
                wrapper,
                [
                    Doc("example.sed",
                        wrapper,
                        [],
                        contents="s/e/E/g")
                    ],
                contents="hello")

        wrapper.run_docs(node)
        assert str(node.output_data()) == "hEllo"

def test_sed_filter_single_simple_input_file():
    with wrap() as wrapper:
        node = Doc("example.sed|sed",
                wrapper,
                [
                    Doc("input.txt",
                        wrapper,
                        [],
                        contents="hello")
                    ],
                contents="s/e/E/g")

        wrapper.run_docs(node)
        assert str(node.output_data()) == "hEllo"

def test_sed_filter_single_input_file_with_sections():
    contents = json.loads("""[{},
    { "name" : "foo", "contents" : "hello" },
    { "name" : "bar", "contents" : "telephone" }
    ]""")

    with wrap() as wrapper:
        node = Doc("example.sed|sed",
                wrapper,
                [
                    Doc("input.txt",
                        wrapper,
                        [],
                        contents=contents,
                        data_class='sectioned'
                        )
                        ],
                contents="s/e/E/g")

        wrapper.run_docs(node)
        assert str(node.output_data()['foo']) == 'hEllo'
        assert str(node.output_data()['bar']) == 'tElEphonE'

def test_sed_filter_multiple_inputs():
    with wrap() as wrapper:
        node = Doc("example.sed|sed",
                wrapper,
                inputs = [
                    Doc("foo.txt",
                        wrapper,
                        [],
                        contents='hello'),
                    Doc("bar.txt",
                        wrapper,
                        [],
                        contents='telephone')
                    ],
                contents="s/e/E/g")

        wrapper.run_docs(node)
        assert str(node.output_data()['foo.txt']) == 'hEllo'
        assert str(node.output_data()['bar.txt']) == 'tElEphonE'

########NEW FILE########
__FILENAME__ = test_subprocess_filters
from dexy.doc import Doc
from dexy.wrapper import Wrapper
from nose.exc import SkipTest
from tests.plugins.test_pexpect_filters import SCALA
from tests.utils import TEST_DATA_DIR
from tests.utils import assert_in_output
from tests.utils import assert_output
from tests.utils import assert_output_cached
from tests.utils import wrap
import os
import shutil

C_HELLO_WORLD = """#include <stdio.h>

int main()
{
    printf("HELLO, world\\n");
}
"""

def test_mkdirs():
    with wrap() as wrapper:
        doc = Doc("hello.c|c",
                wrapper,
                contents = C_HELLO_WORLD,
                c = {'mkdir' : 'foo', 'mkdirs' : ['bar', 'baz']}
                )
        wrapper.run_docs(doc)
        dirs = os.listdir(doc.filters[-1].workspace())
        assert 'foo' in dirs
        assert 'bar' in dirs
        assert 'baz' in dirs

def test_taverna():
    raise SkipTest()
    with wrap() as wrapper:
        orig = os.path.join(TEST_DATA_DIR, 'simple_python_example_285475.t2flow')
        shutil.copyfile(orig, 'simple-python.t2flow')
        node = Doc("simple-python.t2flow|taverna",
                wrapper)
        wrapper.run_docs(node)

PYIN_CONTENTS = """import sys
i = 0
while True:
    i += 1
    line = sys.stdin.readline()
    if not line:
        break
    print "line %s has %s chars" % (i, len(line))
"""

def test_scalac():
    assert_output('scala', SCALA, "Hello, world!\n", ext=".scala", basename="HelloWorld")

def test_python_input():
    with wrap() as wrapper:
        node = Doc("hello.py|pyin",
                wrapper,
                [
                    Doc("input.in",
                        wrapper,
                        [],
                        contents="here is some input\nmore")
                    ],
                contents=PYIN_CONTENTS
                )
        wrapper.run_docs(node)
        assert str(node.output_data()) == """\
line 1 has 19 chars
line 2 has 4 chars
"""

def test_pandoc_filter_odt():
    # TODO Why isn't this checking for inactive filters?
    with wrap() as wrapper:
        node = Doc("hello.md|pandoc",
                wrapper,
                [],
                contents = "hello",
                pandoc = { "ext" : ".odt"}
                )
        wrapper.run_docs(node)
        wrapper.report()
        assert os.path.exists("output/hello.odt")

def test_pandoc_filter_pdf():
    with wrap() as wrapper:
        node = Doc("hello.md|pandoc",
                wrapper,
                [],
                contents = "hello",
                pandoc = { "ext" : ".pdf"}
                )
        wrapper.run_docs(node)
        wrapper.report()
        assert os.path.exists("output/hello.pdf")

def test_pandoc_filter_txt():
    with wrap() as wrapper:
        node = Doc("hello.md|pandoc",
            wrapper, [],
            contents = "hello",
            pandoc = { "ext" : ".txt"},
            )
        wrapper.run_docs(node)
        wrapper.report()
        assert os.path.exists("output/hello.txt")
        assert str(node.output_data()) == 'hello\n'

R_SECTIONS = """\
### @export "assign-vars"
x <- 6
y <- 7

### @export "multiply"
x * y
"""

def test_rint_mock():
    with wrap() as wrapper:
        node = Doc("example.R|idio|rintmock",
                wrapper,
                [],
                contents=R_SECTIONS
                )

        wrapper.run_docs(node)
        assert node.output_data().is_cached()
        assert unicode(node.output_data()['assign-vars']) == u"> x <- 6\n> y <- 7\n> \n"
        assert unicode(node.output_data()['multiply']) == u"> x * y\n[1] 42\n> \n"

def test_ht_latex():
    assert_output_cached("htlatex", LATEX, ext=".tex")

def test_r_batch():
    assert_output('rout', 'print(1+1)', "[1] 2\n")

def test_r_int_batch():
    assert_output('rintbatch', '1+1', "> 1+1\n[1] 2\n> \n")

def test_ragel_ruby_filter():
    assert_in_output('rlrb', RAGEL, "_keys = _hello_and_welcome_key_offsets[cs]", ext=".rl")

def test_ps2pdf_filter():
    with wrap() as wrapper:
        node = Doc("hello.ps|ps2pdf",
                wrapper, [],
                contents = PS)
        wrapper.run_docs(node)
        assert node.output_data().is_cached()
        assert node.output_data().filesize() > 1000

def test_html2pdf_filter():
    assert_output_cached("html2pdf", "<p>hello</p>", min_filesize=1000)

def test_dot_filter():
    assert_output_cached("dot", "digraph { a -> b }", min_filesize=1000, ext=".dot")

def test_pdf2img_filter():
    with wrap() as wrapper:
        orig = os.path.join(TEST_DATA_DIR, 'color-graph.pdf')
        shutil.copyfile(orig, 'example.pdf')
        wrapper=Wrapper()
        node = Doc("example.pdf|pdf2img", wrapper)
        wrapper.run_docs(node)
        assert node.output_data().is_cached()
        assert node.output_data().filesize() > 1000

def test_pdf2jpg_filter():
    with wrap() as wrapper:
        orig = os.path.join(TEST_DATA_DIR, 'color-graph.pdf')
        shutil.copyfile(orig, 'example.pdf')
        wrapper=Wrapper()
        node = Doc("example.pdf|pdf2jpg", wrapper)

        wrapper.run_docs(node)
        assert node.output_data().is_cached()

def test_bw_filter():
    with wrap() as wrapper:
        orig = os.path.join(TEST_DATA_DIR, 'color-graph.pdf')
        shutil.copyfile(orig, 'example.pdf')
        wrapper=Wrapper()
        node = Doc("example.pdf|bw", wrapper)

        wrapper.run_docs(node)
        assert node.output_data().is_cached()

def test_pdfcrop_filter():
    with wrap() as wrapper:
        orig = os.path.join(TEST_DATA_DIR, 'color-graph.pdf')
        shutil.copyfile(orig, 'example.pdf')
        wrapper=Wrapper()
        node = Doc("example.pdf|pdfcrop|pdfinfo", wrapper)

        wrapper.run_docs(node)
        assert node.output_data().is_cached()

def test_asciidoc_filter():
    assert_in_output("asciidoc", "hello", """<div class="paragraph"><p>hello</p></div>""")

def test_pandoc_filter():
    assert_output("pandoc", "hello", "<p>hello</p>\n", ext=".md")

def test_espeak_filter():
    assert_output_cached("espeak", "hello", min_filesize = 1000)

PS = """%!PS
1.00000 0.99083 scale
/Courier findfont 12 scalefont setfont
0 0 translate
/row 769 def
85 {/col 18 def 6 {col row moveto (Hello World)show /col col 90 add def}
repeat /row row 9 sub def} repeat
showpage save restore"""

RD = """
 \\name{load}
     \\alias{load}
     \\title{Reload Saved Datasets}
     \description{
       Reload the datasets written to a file with the function
       \code{save}.
     }
"""

RAGEL = """%%{
  machine hello_and_welcome;
  main := ( 'h' @ { puts "hello world!" }
          | 'w' @ { puts "welcome" }
          )*;
}%%
  data = 'whwwwwhw'
  %% write data;
  %% write init;
  %% write exec;
"""

LATEX = """\
\documentclass{article}
\\title{Hello, World!}
\\begin{document}
\maketitle
Hello!
\end{document}
"""

########NEW FILE########
__FILENAME__ = test_templates
from tests.utils import tempdir
from nose.exc import SkipTest

try:
    from dexy_filter_examples import Cowsay
except ImportError:
    raise SkipTest()

def test_cowsay():
    with tempdir():
        for batch in Cowsay().dexy():
            print batch

########NEW FILE########
__FILENAME__ = test_template_assertions
from tests.plugins.test_templating_filters import run_jinja_filter
from dexy.doc import Doc
from tests.utils import wrap
import inspect

def test_assert_equals():
    assert unicode(run_jinja_filter("{{ 'foo' | assert_equals('foo') }}")) == 'foo'

def test_assert_equals_invalid():
    try:
        unicode(run_jinja_filter("{{ 'foo' | assert_equals('bar') }}"))
        raise Exception("should raise AssertionError")
    except AssertionError as e:
        assert str(e) == "input text did not equal 'bar'"

def test_assert_contains():
    assert unicode(run_jinja_filter("{{ 'foo bar' | assert_contains('foo') }}")) == 'foo bar'

def test_assert_contains_invalid():
    try:
        unicode(run_jinja_filter("{{ 'foo bar' | assert_contains('baz') }}"))
        raise Exception("should raise AssertionError")
    except AssertionError as e:
        assert str(e) == "input text did not contain 'baz'"

def test_assert_does_not_contain():
    assert unicode(run_jinja_filter("{{ 'foo bar' | assert_does_not_contain('baz') }}")) == 'foo bar'

def test_assert_does_not_contain_invalid():
    try:
        unicode(run_jinja_filter("{{ 'foo bar baz' | assert_does_not_contain('baz') }}"))
        raise Exception("should raise AssertionError")
    except AssertionError as e:
        assert str(e) == "input text contained 'baz'"

def test_assert_startswith():
    assert unicode(run_jinja_filter("{{ 'foo bar' | assert_startswith('foo') }}")) == 'foo bar'

def test_assert_startswith_invalid():
    try:
        unicode(run_jinja_filter("{{ 'foo bar' | assert_startswith('bar') }}"))
        raise Exception("should raise AssertionError")
    except AssertionError as e:
        assert str(e) == "input text did not start with 'bar'"

def test_assert_matches():
    assert unicode(run_jinja_filter("{{ 'foo bar baz' | assert_matches('^foo') }}")) == 'foo bar baz'

def test_assert_matches_invalid():
    try:
        unicode(run_jinja_filter("{{ 'foo bar' | assert_matches('^baz') }}"))
        raise Exception("should raise AssertionError")
    except AssertionError as e:
        assert str(e) == "input text did not match regexp ^baz"

def test_assert_selector():
    with wrap() as wrapper:
        node = Doc("hello.txt|jinja",
                wrapper,
                [
                    Doc("input.html",
                        wrapper,
                        [],
                        contents = inspect.cleandoc("""
                        <div id="foo">
                        This is contents of foo div.
                        </div>
                        """
                        ))
                    ],
                contents = "{{ d['input.html'] | assert_selector_text('#foo', 'This is contents of foo div.') }}"
                )
        wrapper.run_docs(node)

def test_assert_selector_invalid():
    with wrap() as wrapper:
        node = Doc("hello.txt|jinja",
                wrapper,
                [
                    Doc("input.html",
                        wrapper,
                        [],
                        contents = inspect.cleandoc("""
                        <div id="foo">
                        This is contents of foo div.
                        </div>
                        """
                        ))
                    ],
                contents = "{{ d['input.html'] | assert_selector_text('#foo', 'Not right.') }}"
                )

        try:
            wrapper.run_docs(node)
            raise Exception("should raise AssertionError")
        except AssertionError as e:
            assert str(e) == "element '#foo' did not contain 'Not right.'"

########NEW FILE########
__FILENAME__ = test_templating_filters
from dexy.doc import Doc
from dexy.filters.templating import TemplateFilter
from dexy.filters.templating_plugins import TemplatePlugin
from tests.utils import wrap
from dexy.exceptions import UserFeedback

def test_jinja_invalid_attribute():
    def make_sections_doc(wrapper):
        return Doc("sections.txt",
                wrapper,
                [],
                contents = [{}, {"name" : "foo", "contents" : "This is foo."}]
                )

    with wrap() as wrapper:
        node = Doc("ok.txt|jinja",
                wrapper,
                [make_sections_doc(wrapper)],
                contents = """hello! foo contents are {{ d['sections.txt'].foo }}"""
                )

        wrapper.run_docs(node)
        assert str(node.output_data()) == """hello! foo contents are This is foo."""

    with wrap() as wrapper:
        node = Doc("broken.txt|jinja",
                wrapper,
                [make_sections_doc(wrapper)],
                contents = """There is no {{ d['sections.txt'].bar }}"""
                )
        try:
            wrapper.run_docs(node)
        except UserFeedback as e:
            assert str(e) == "No value for bar available in sections or metadata."

def test_jinja_pass_through():
    with wrap() as wrapper:
        with open("_template.html", "w") as f:
            f.write("{{ content }}")

        wrapper.reports = 'ws'
        contents = u"{{ link(\"input.txt\") }}"
        doc = Doc("lines.html|jinja",
                    wrapper,
                    [
                        Doc("input.txt",
                            wrapper,
                            [],
                            contents = "nothing to see here"
                            )
                        ],
                    contents=contents,
                    apply_ws_to_content = True
                    )
        wrapper.run_docs(doc)
        assert unicode(doc.output_data()) == contents

        wrapper.report()

        with open("output-site/lines.html", 'r') as f:
            lines_html = f.read()
            assert lines_html == """<a href="input.txt">Input</a>"""

def test_jinja_pass_through_fails_if_not_whitelisted():
    with wrap() as wrapper:
        contents = u"{{ linxxx('foo') }}"
        doc = Doc("lines.txt|jinja",
                    wrapper,
                    [],
                    contents=contents
                    )

        try:
            wrapper.run_docs(doc)
        except UserFeedback as e:
            assert "a UndefinedError problem" in str(e)
            assert "'linxxx' is undefined" in str(e)

def test_jinja_indent_function():
    with wrap() as wrapper:
        node = Doc("hello.txt|jinja",
                wrapper,
                [
                    Doc("lines.txt",
                        wrapper,
                        [],
                        contents = "line one\nline two"
                        )
                    ],
                contents = "lines are:\n   {{ d['lines.txt'] | indent(3) }}"
                )
        wrapper.run_docs(node)
        assert str(node.output_data()) == """lines are:
   line one
   line two"""

def run_jinja_filter(contents):
    with wrap() as wrapper:
        doc = Doc("hello.txt|jinja",
                wrapper,
                [],
                contents = contents
                )
        wrapper.run_docs(doc)
        data = doc.output_data()
        data.data() # make sure is loaded
        return data

def test_jinja_filters_bs4():
    data = run_jinja_filter("{{ '<p>foo</p>' | prettify_html }}")
    assert unicode(data) == "<p>\n foo\n</p>"

def test_beautiful_soup_should_not_be_available_as_filter():
    try:
        run_jinja_filter("{{ 'foo' | BeautifulSoup }}")
        assert False
    except UserFeedback as e:
        assert "no filter named 'BeautifulSoup'" in str(e)

def test_jinja_filters_head():
    data = run_jinja_filter("{{ 'foo\nbar\nbaz' | head(1) }}")
    assert unicode(data) == "foo"
    data = run_jinja_filter("{{ 'foo\nbar\nbaz' | head(2) }}")
    assert unicode(data) == "foo\nbar"

def test_jinja_filters_tail():
    data = run_jinja_filter("{{ 'foo\nbar\nbaz' | tail(1) }}")
    assert unicode(data) == "baz"
    data = run_jinja_filter("{{ 'foo\nbar\nbaz' | tail(2) }}")
    assert unicode(data) == "bar\nbaz"

def test_jinja_filters_highlight():
    data = run_jinja_filter("{{ '<p>foo</p>' | highlight('html') }}")
    assert unicode(data) == u"""<div class="highlight"><pre><a name="l-1"></a><span class="nt">&lt;p&gt;</span>foo<span class="nt">&lt;/p&gt;</span>\n</pre></div>\n"""

def test_jinja_filters_pygmentize():
    data = run_jinja_filter("{{ '<p>foo</p>' | pygmentize('html') }}")
    assert unicode(data) == u"""<div class="highlight"><pre><a name="l-1"></a><span class="nt">&lt;p&gt;</span>foo<span class="nt">&lt;/p&gt;</span>\n</pre></div>\n"""

def test_jinja_filters_combined():
    data = run_jinja_filter("{{ '<p>foo</p>' | prettify_html | highlight('html') }}")
    assert unicode(data) == u"""<div class="highlight"><pre><a name="l-1"></a><span class="nt">&lt;p&gt;</span>
<a name="l-2"></a> foo
<a name="l-3"></a><span class="nt">&lt;/p&gt;</span>
</pre></div>
"""

def test_jinja_kv():
    with wrap() as wrapper:
        node = Doc("hello.txt|jinja",
                wrapper,
                [
                    Doc("blank.txt|keyvalueexample",
                        wrapper,
                        [],
                        contents = " ")
                    ],
                contents = """value of foo is '{{ d['blank.txt|keyvalueexample']['foo'] }}'"""
                )
        wrapper.run_docs(node)
        assert str(node.output_data()) == "value of foo is 'bar'"

def test_jinja_sectioned_invalid_section():
    with wrap() as wrapper:
        wrapper.debug = False
        doc = Doc("hello.txt|jinja",
                wrapper,
                [
                    Doc("lines.txt|lines",
                        wrapper,
                        [],
                        contents = "line one\nline two"
                        )
                    ],
                contents = """first line is '{{ d['lines.txt|lines']['3'] }}'"""
                )
        wrapper.run_docs(doc)
        assert wrapper.state == 'error'

def test_jinja_sectioned():
    with wrap() as wrapper:
        node = Doc("hello.txt|jinja",
                wrapper,
                [
                    Doc("lines.txt|lines",
                        wrapper,
                        [],
                        contents = "line one\nline two")
                    ],
                contents = """first line is '{{ d['lines.txt|lines']['1'] }}'""")
        wrapper.run_docs(node)
        assert str(node.output_data()) == "first line is 'line one'"

def test_jinja_json():
    with wrap() as wrapper:
        node = Doc("hello.txt|jinja",
                wrapper,
                [
                    Doc("input.json",
                        wrapper, [],
                        contents = """{"foo":123}"""
                        )
                    ],
                contents = """foo is {{ d['input.json']['foo'] }}""")
        wrapper.run_docs(node)
        assert str(node.output_data()) == "foo is 123"

def test_jinja_undefined():
    with wrap() as wrapper:
        wrapper.debug = False
        node = Doc("template.txt|jinja",
                wrapper,
                [],
                contents = """{{ foo }}""")

        wrapper.run_docs(node)
        assert wrapper.state == 'error'

def test_jinja_syntax_error():
    with wrap() as wrapper:
        wrapper.debug = False
        node = Doc("template.txt|jinja",
                wrapper,
                [],
                contents = """{% < set foo = 'bar' -%}\nfoo is {{ foo }}\n"""
                )

        wrapper.run_docs(node)
        assert wrapper.state == 'error'

def test_jinja_filter_inputs():
    with wrap() as wrapper:
        node = Doc("template.txt|jinja",
                wrapper,
                [Doc("input.txt",
                    wrapper,
                    [],
                    contents = "I am the input.")
                ],
                contents = "The input is '{{ d['input.txt'] }}'")

        wrapper.run_docs(node)
        assert str(node.output_data()) == "The input is 'I am the input.'"

class TestSimple(TemplatePlugin):
    """
    test plugin
    """
    aliases = ['testtemplate']
    def run(self):
        return {'aaa' : ("docs", 1)}

class TestTemplateFilter(TemplateFilter):
    """
    test template
    """
    aliases = ['testtemplatefilter']

def test_template_filter_with_custom_filter_only():
    with wrap() as wrapper:
        node = Doc("hello.txt|testtemplatefilter",
                wrapper,
                [],
                contents = "aaa equals %(aaa)s",
                testtemplatefilter = { "plugins" : ["testtemplate"] }
                )

        wrapper.run_docs(node)
        assert node.output_data().as_text() == "aaa equals 1"
        plugins_used = node.filters[-1].template_plugins()
        assert len(plugins_used) == 1
        assert isinstance(plugins_used[0], TestSimple)

def test_jinja_filter():
    with wrap() as wrapper:
        node = Doc("template.txt|jinja",
                wrapper,
                [],
                contents = "1 + 1 is {{ 1+1 }}"
                )

        wrapper.run_docs(node)
        assert node.output_data().as_text() == "1 + 1 is 2"

def test_jinja_filter_tex_extension():
    with wrap() as wrapper:
        node = Doc("template.tex|jinja",
                wrapper,
                [],
                contents = "1 + 1 is << 1+1 >>")

        wrapper.run_docs(node)
        assert node.output_data().as_text() == "1 + 1 is 2"

def test_jinja_filter_custom_delims():
    with wrap() as wrapper:
        node = Doc("template.tex|jinja",
                wrapper,
                [],
                contents = "1 + 1 is %- 1+1 -%",
                jinja = {
                    "variable_start_string" : "%-",
                    "variable_end_string" : "-%"
                    }
                )

        wrapper.run_docs(node)
        assert node.output_data().as_text() == "1 + 1 is 2"

def test_jinja_filter_set_vars():
    with wrap() as wrapper:
        node = Doc("template.txt|jinja",
                wrapper,
                [],
                contents = """{% set foo = 'bar' -%}\nfoo is {{ foo }}\n"""
                )

        wrapper.run_docs(node)
        assert node.output_data().as_text() == "foo is bar"

def test_jinja_filter_using_inflection():
    with wrap() as wrapper:
        node = Doc("template.txt|jinja",
                wrapper,
                [],
                contents = """{{ humanize("abc_def") }}"""
                )

        wrapper.run_docs(node)
        assert node.output_data().as_text() == "Abc def"

########NEW FILE########
__FILENAME__ = test_templating_plugins
from dexy.doc import Doc
from dexy.filters.templating import TemplateFilter
from dexy.filters.templating_plugins import TemplatePlugin
from tests.utils import run_templating_plugin as run
from tests.utils import wrap
import dexy.filters.templating_plugins as plugin
import inspect
import os

def test_base():
    run(TemplatePlugin)

def test_ppjson():
    with run(plugin.PrettyPrintJson) as env:
        assert 'ppjson' in env
        assert hasattr(env['ppjson'][1], '__call__')

def test_python_datetime():
    with run(plugin.PythonDatetime) as env:
        assert inspect.ismodule(env['cal'][1])

def test_dexy_version():
    with run(plugin.DexyVersion) as env:
        assert env['DEXY_VERSION'][1]

def test_simple_json():
    with run(plugin.SimpleJson) as env:
        assert inspect.ismodule(env['json'][1])

def test_python_builtins():
    with run(plugin.PythonBuiltins) as env:
        assert 'hasattr' in env

def test_pygments():
    with run(plugin.PygmentsStylesheet) as env:
        assert 'pastie.tex' in env['pygments'][1].keys()
        assert 'pastie.css' in env['pygments'][1].keys()
        assert 'pastie.html' in env['pygments'][1].keys()

class TestSubdirectory(TemplateFilter):
    """
    test subdir
    """
    aliases = ['testsubdir']
    _settings = { 'plugins' : ['subdirectories'] }

def test_subdirectories():
    with wrap() as wrapper:
        os.makedirs("s1")
        os.makedirs("s2")

        node = Doc("file.txt|testsubdir",
                wrapper,
                [],
                contents="hello"
                )

        wrapper.run_docs(node)

        env = node.filters[-1].run_plugins()
        assert 's1' in env['subdirectories'][1]
        assert 's2' in env['subdirectories'][1]

class TestVariables(TemplateFilter):
    """
    test variables
    """
    aliases = ['testvars']
    _settings = { 'plugins' : ['variables'] }

def test_variables():
    with wrap() as wrapper:
        node = Doc("hello.txt|testvars",
                wrapper,
                [],
                contents = "hello",
                testvars = { "variables" : {"foo" : "bar", "x" : 123.4 } }
                )

        wrapper.run_docs(node)

        env = node.filters[-1].run_plugins()
        assert env['foo'][1] == 'bar'
        assert env['x'][1] == 123.4

class TestGlobals(TemplateFilter):
    """
    test globals
    """
    aliases = ['testglobals']
    _settings = { 'plugins' : ['globals'] }

def test_globals():
    with wrap() as wrapper:
        wrapper.globals = "foo=bar"
        node = Doc("hello.txt|testglobals",
                wrapper,
                [],
                contents = "hello"
                )

        wrapper.run_docs(node)
        env = node.filters[-1].run_plugins()
        assert env['foo'][1] == 'bar'

########NEW FILE########
__FILENAME__ = test_tidy_filters
from tests.utils import runfilter
from dexy.exceptions import UserFeedback

min_valid_html = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<TITLE></TITLE>
"""

invalid_html = "<html></html>"

def test_tidyerrors():
    with runfilter("tidyerrors", invalid_html, ext=".html") as doc:
        output = str(doc.output_data())
        assert "missing <!DOCTYPE>" in output
        assert "inserting missing 'title'" in output

def test_htmltidy_throws_error_on_invalid_html():
    try:
        with runfilter("htmltidy", invalid_html, ext=".html"):
            assert False, "should not get here"
    except UserFeedback as e:
        assert "missing <!DOCTYPE>" in str(e)
        assert "inserting missing 'title'" in str(e)

def test_htmltidy():
    with runfilter("htmltidy", min_valid_html, ext=".html") as doc:
        output = str(doc.output_data())
        assert "<body>" in output

def test_htmlcheck_on_valid_html():
    with runfilter("tidycheck", min_valid_html, ext=".html") as doc:
        output = str(doc.output_data())
        assert output == min_valid_html

def test_htmlcheck_on_invalid_html():
    try:
        with runfilter("tidycheck", invalid_html, ext=".html"):
            assert False, "should not get here"
    except UserFeedback as e:
        assert "missing <!DOCTYPE>" in str(e)
        assert "inserting missing 'title'" in str(e)

########NEW FILE########
__FILENAME__ = test_website_repoters
def test_nav_directories():
    pass

########NEW FILE########
__FILENAME__ = test_wordpress_filters
from dexy.doc import Doc
from tests.utils import TEST_DATA_DIR
from tests.utils import wrap
from tests.utils import capture_stdout
from mock import patch
import dexy.exceptions
import json
import os
import shutil
import dexy.filter
import dexy.wrapper

def test_docmd_create_keyfile():
    with wrap():
        assert not os.path.exists(".dexyapis")
        dexy.filter.Filter.create_instance("wp").docmd_create_keyfile()
        assert os.path.exists(".dexyapis")

def test_docmd_create_keyfile_if_exists():
    with wrap():
        with open(".dexyapis", "w") as f:
            f.write("{}")
        assert os.path.exists(".dexyapis")
        try:
            dexy.filter.Filter.create_instance("wp").docmd_create_keyfile()
            assert False, ' should raise exception'
        except dexy.exceptions.UserFeedback as e:
            assert ".dexyapis already exists" in e.message

def test_api_url_with_php_ending():
    with wrap():
        with open(".dexyapis", "wb") as f:
            json.dump({
                    "wordpress" : {"url" : "http://example.com/api/xmlrpc.php"}
                    }, f)

        url = dexy.filter.Filter.create_instance("wp").api_url()
        assert url == "http://example.com/api/xmlrpc.php"

def test_api_url_without_php_ending():
    with wrap():
        with open(".dexyapis", "wb") as f:
            json.dump({ "wordpress" : {"url" : "http://example.com/api"} }, f)

        url = dexy.filter.Filter.create_instance("wp").api_url()
        assert url == "http://example.com/api/xmlrpc.php"

def test_api_url_without_php_ending_with_trailing_slash():
    with wrap():
        with open(".dexyapis", "wb") as f:
            json.dump({ "wordpress" : {"url" : "http://example.com/api/"} }, f)

        url = dexy.filter.Filter.create_instance("wp").api_url()
        assert url == "http://example.com/api/xmlrpc.php"

def test_wordpress_without_doc_config_file():
    with wrap() as wrapper:
        wrapper.debug = False
        doc = Doc("hello.txt|wp",
                contents = "hello, this is a blog post",
                wrapper=wrapper
                )

        wrapper.run_docs(doc)
        assert wrapper.state == 'error'

def mk_wp_doc(wrapper):
    doc = Doc("hello.txt|wp",
            contents = "hello, this is a blog post",
            dirty = True,
            wrapper=wrapper
            )
    for d in doc.datas():
        d.setup()
    return doc

ATTRS = {
        'return_value.metaWeblog.newPost.return_value' : 42,
        'return_value.metaWeblog.getPost.return_value' : {
            'permaLink' : 'http://example.com/blog/42'
            },
        'return_value.wp.getCategories.return_value' : [
            { 'categoryName' : 'foo' },
            { 'categoryName' : 'bar' }
            ],
        'return_value.wp.uploadFile.return_value' : {
            'url' : 'http://example.com/example.pdf'
            }
        }

@patch('xmlrpclib.ServerProxy', **ATTRS)
def test_wordpress(MockXmlrpclib):
    with wrap():
        with open("wordpress.json", "wb") as f:
            json.dump({}, f)

        with open(".dexyapis", "wb") as f:
            json.dump({
                'wordpress' : {
                    'url' : 'http://example.com',
                    'username' : 'foo',
                    'password' : 'bar'
                    }}, f)

        # Create new (unpublished) draft
        wrapper = dexy.wrapper.Wrapper()
        doc = mk_wp_doc(wrapper)
        wrapper.run_docs(doc)

        with open("wordpress.json", "rb") as f:
            result = json.load(f)

        assert result['postid'] == 42
        assert result['publish'] == False

        # Update existing draft
        wrapper = dexy.wrapper.Wrapper()
        doc = mk_wp_doc(wrapper)
        wrapper.run_docs(doc)
        assert doc.output_data().json_as_dict().keys() == ['permaLink']

        result['publish'] = True
        with open("wordpress.json", "wb") as f:
            json.dump(result, f)

        # Publish existing draft
        wrapper = dexy.wrapper.Wrapper()
        doc = mk_wp_doc(wrapper)
        wrapper.run_docs(doc)
        assert "http://example.com/blog/42" in str(doc.output_data())

        # Now, separately, test an image upload.
        orig = os.path.join(TEST_DATA_DIR, 'color-graph.pdf')
        shutil.copyfile(orig, 'example.pdf')
        from dexy.wrapper import Wrapper
        wrapper = Wrapper()
        doc = Doc("example.pdf|wp",
                wrapper=wrapper)

        with open(".dexyapis", "wb") as f:
            json.dump({
                'wordpress' : {
                    'url' : 'http://example.com',
                    'username' : 'foo',
                    'password' : 'bar'
                    }}, f)

        wrapper.run_docs(doc)
        assert doc.output_data().as_text() == "http://example.com/example.pdf"

        # test list categories
        with capture_stdout() as stdout:
            dexy.filter.Filter.create_instance("wp").docmd_list_categories()
            assert stdout.getvalue() == "categoryName\nfoo\nbar\n"

########NEW FILE########
__FILENAME__ = test_xxml_filters
from tests.utils import runfilter
from tests.utils import wrap
from dexy.doc import Doc

XML = """
<element id="foo">foo</element>
"""

def test_xxml():
    with runfilter("xxml", XML) as doc:
        assert doc.output_data()['foo:source'] == '<element id="foo">foo</element>'
        assert doc.output_data()['foo:text'] == 'foo'
        assert '<div class="highlight">' in doc.output_data()['foo:html-source']

def test_xxml_no_pygments():
    with wrap() as wrapper:
        doc = Doc(
                "example.xml|xxml",
                wrapper,
                [],
                contents = XML,
                xxml = { 'pygments' : False, 'ext' : '.sqlite3' }
                )
        wrapper.run_docs(doc)

        assert "foo:source" in doc.output_data().keys()
        assert not "foo:html-source" in doc.output_data().keys()
        assert not "foo:latex-source" in doc.output_data().keys()

########NEW FILE########
__FILENAME__ = test_yamlargs_filters
from dexy.doc import Doc
from tests.utils import wrap
from dexy.wrapper import Wrapper

def test_yamlargs_with_caching():
    with wrap() as wrapper:
        doc = Doc("example.txt|yamlargs",
                wrapper,
                [],
                contents = "title: My Title\n---\r\nThis is the content."
                )
        wrapper.run_docs(doc)

        task = wrapper.nodes["doc:example.txt|yamlargs"]
        assert task.output_data().title() == "My Title"
        assert task.state == 'ran'

        wrapper = Wrapper()
        doc = Doc("example.txt|yamlargs",
                wrapper,
                [],
                contents = "title: My Title\n---\r\nThis is the content."
                )
        wrapper.run_docs(doc)
        task = wrapper.nodes["doc:example.txt|yamlargs"]
        assert task.output_data().title() == "My Title"
        assert task.state == 'consolidated'

        wrapper = Wrapper()
        doc = Doc("example.txt|yamlargs",
                wrapper,
                [],
                contents = "title: My Title\n---\r\nThis is the content."
                )
        wrapper.run_docs(doc)
        task = wrapper.nodes["doc:example.txt|yamlargs"]
        assert task.output_data().title() == "My Title"
        assert task.state == 'consolidated'

def test_yamlargs_no_yaml():
    with wrap() as wrapper:
        doc = Doc("example.txt|yamlargs",
                wrapper,
                [],
                contents = "This is the content.")

        wrapper.run_docs(doc)
        assert doc.output_data().as_text() == "This is the content."

def test_yamlargs():
    with wrap() as wrapper:
        doc = Doc("example.txt|yamlargs",
                wrapper,
                [],
                contents = "title: My Title\n---\r\nThis is the content."
                )

        wrapper.run_docs(doc)
        assert doc.output_data().title() == "My Title"
        assert doc.output_data().as_text() == "This is the content."

YAML = """filterargs:
  abc: xyz
  foo: 5
"""

def test_yamlargs_filterargs():
    with wrap() as wrapper:
        doc = Doc("example.txt|yamlargs|filterargs",
                wrapper,
                [],
                contents = "%s\n---\r\nThis is the content." % YAML,
                )

        wrapper.run_docs(doc)

        output = doc.output_data().as_text()
        assert "abc: xyz" in output
        assert "foo: 5" in output

        wrapper = Wrapper()
        doc = Doc("example.txt|yamlargs|filterargs",
                wrapper,
                [],
                contents = "%s\n---\r\nThis is the content." % YAML,
                )

        wrapper.run_docs(doc)

        output = doc.output_data().as_text()
        assert "abc: xyz" in output
        assert "foo: 5" in output

########NEW FILE########
__FILENAME__ = test_yaml_parser
from dexy.exceptions import UserFeedback
from dexy.parser import AbstractSyntaxTree
from dexy.parsers.doc import Yaml
from tests.utils import capture_stderr
from tests.utils import wrap
from dexy.wrapper import Wrapper
import dexy.batch
import os

def test_hard_tabs_in_config():
    with wrap():
        with capture_stderr() as stderr:
            os.makedirs("abc/def")
            with open("abc/def/dexy.yaml", "w") as f:
                f.write("""foo:\t- .txt""")

            wrapper = Wrapper()

            try:
                wrapper.run_from_new()
            except UserFeedback as e:
                assert "hard tabs" in str(e)

            assert "abc/def/dexy.yaml" in stderr.getvalue()

def test_subdir_config_with_bundle():
    with wrap():
        with open("dexy.yaml", "w") as f:
            f.write("""
            foo:
                - .txt
            """)

        os.makedirs("abc/def")
        with open("abc/def/dexy.yaml", "w") as f:
            f.write("""
            bar:
                - .py
            """)

        with open("abc/def/hello.py", "w") as f:
            f.write("print 'hello'")

        wrapper = Wrapper()
        wrapper.run_from_new()
        assert "doc:abc/def/hello.py" in wrapper.nodes

        wrapper = Wrapper(recurse=False)
        wrapper.run_from_new()
        assert not "doc:abc/def/hello.py" in wrapper.nodes

        wrapper = Wrapper(recurse=False, configs="abc/def/dexy.yaml")
        wrapper.run_from_new()
        assert "doc:abc/def/hello.py" in wrapper.nodes

def test_except_patterndoc():
    with wrap() as wrapper:
        with open("exceptme.abc", "w") as f:
            f.write("hello")

        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = Yaml(wrapper, ast)
        parser.parse('.', """.abc:\n  - except : 'exceptme.abc' """)
        ast.walk()

        assert len(wrapper.nodes) == 1

def test_except_patterndoc_pattern():
    with wrap() as wrapper:
        with open("exceptme.abc", "w") as f:
            f.write("hello")

        wrapper = Wrapper()
        wrapper.to_valid()

        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = Yaml(wrapper, ast)
        parser.parse('.', """.abc:\n  - except : 'exceptme.*' """)
        ast.walk()
        wrapper.transition('walked')
        wrapper.to_checked()

        wrapper.run()

        assert len(wrapper.nodes) == 1

def test_children_siblings_order():
    with wrap() as wrapper:
        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = Yaml(wrapper, ast)
        parser.parse('.', """
        p1:
            - c1
            - c2:
                - g1
                - g2
                - g3
            - c3
        """)
        ast.walk()
        wrapper.transition('walked')

        wrapper.to_checked()

        wrapper.run()

        p1 = wrapper.nodes['bundle:p1']
        assert [i.key_with_class() for i in p1.walk_inputs()] == [
                'bundle:c1',
                'bundle:c2',
                'bundle:g1',
                'bundle:g2',
                'bundle:g3',
                'bundle:c3'
                ]

        c1 = wrapper.nodes['bundle:c1']
        assert len(c1.inputs) == 0

        c2 = wrapper.nodes['bundle:c2']
        assert [i.key_with_class() for i in c2.walk_inputs()] == [
                'bundle:g1',
                'bundle:g2',
                'bundle:g3'
                ]

        c3 = wrapper.nodes['bundle:c3']
        assert len(c3.inputs) == 0

        g3 = wrapper.nodes['bundle:g3']
        assert len(g3.inputs) == 0

def test_single_file_doc():
    with wrap() as wrapper:
        with open("hello.txt", "w") as f:
            f.write("hello")

        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = Yaml(wrapper, ast)
        parser.parse('.', "hello.txt")
        ast.walk()
        wrapper.transition('walked')

        wrapper.to_checked()

        wrapper.run()
        assert "doc:hello.txt" in wrapper.nodes

def test_single_bundle_doc():
    with wrap() as wrapper:
        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = Yaml(wrapper, ast)
        parser.parse('.', "hello")
        ast.walk()
        wrapper.transition('walked')
        wrapper.to_checked()
        assert "bundle:hello" in wrapper.nodes

def test_single_bundle_doc_with_args():
    with wrap() as wrapper:
        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = Yaml(wrapper, ast)
        parser.parse('.', """
        more:
            - hello
            - one-more-task
            - foo: bar

        hello:
            - foo: bar
            - filter_fruit: orange
            - args:
                - ping: pong
            - another-task:
                - foo: baz
                - yet-another-task:
                    - foo: bar
            - one-more-task
        """)
        ast.walk()

        assert wrapper.roots[0].key_with_class() == "bundle:more"
        assert len(wrapper.nodes) == 5

def test_single_bundle_doc_with_args_2():
    with wrap() as wrapper:
        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = Yaml(wrapper, ast)
        parser.parse('.', """

      -  hello:
            - foo: bar
            - filter_fruit: orange
            - args:
                - ping: pong
            - another-task:
                - foo: baz
                - yet-another-task:
                    - foo: bar
            - one-more-task

      -  more:
            - hello
            - one-more-task
            - foo: bar

        """)

        ast.walk()

        assert wrapper.roots[0].key_with_class() == "bundle:more"
        assert len(wrapper.nodes) == 5

########NEW FILE########
__FILENAME__ = test_website
from dexy.reporters.website.classes import Navigation
from dexy.reporters.website.classes import Node

def test_navigation():
   nav = Navigation()
   assert nav.nodes["/"] == nav.root

def test_iter():
    nav = Navigation()
    n2 = Node("/foo", nav.root, [])
    n3 = Node("/foo/bar", n2, [])

    for n in [n2, n3]:
        nav.add_node(n)

########NEW FILE########
__FILENAME__ = test_abstract_syntax_tree
from dexy.parser import AbstractSyntaxTree
from tests.utils import wrap
import dexy.batch

def test_ast():
    with wrap() as wrapper:
        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)

        ast.add_node("abc.txt", foo='bar', contents = 'abc')
        ast.add_dependency("abc.txt", "def.txt")
        ast.add_node("def.txt", foo='baz', contents = 'def')

        assert ast.tree == ['doc:abc.txt']
        assert ast.args_for_node('doc:abc.txt')['foo'] == 'bar'
        assert ast.args_for_node('doc:def.txt')['foo'] == 'baz'
        assert ast.inputs_for_node('abc.txt') == ['doc:def.txt']
        assert not ast.inputs_for_node('def.txt')

        ast.walk()
        assert len(wrapper.roots) == 1
        assert len(wrapper.nodes) == 2

########NEW FILE########
__FILENAME__ = test_batch
from tests.utils import tempdir
from dexy.wrapper import Wrapper
import dexy.batch
import os

def test_batch():
    with tempdir():
        wrapper = Wrapper()
        wrapper.create_dexy_dirs()

        wrapper = Wrapper()
        batch = dexy.batch.Batch(wrapper)
        os.makedirs(batch.batch_dir())

        batch.save_to_file()
        assert batch.filename() in os.listdir(".dexy/batches")

        wrapper = Wrapper()
        batch = dexy.batch.Batch.load_most_recent(wrapper)

def test_batch_with_docs():
    with tempdir():
        wrapper = Wrapper(log_level='DEBUG', debug=True)
        wrapper.create_dexy_dirs()

        with open("hello.txt", "w") as f:
            f.write("hello")

        with open("dexy.yaml", "w") as f:
            f.write("hello.txt")

        wrapper = Wrapper()
        wrapper.run_from_new()

        batch = dexy.batch.Batch.load_most_recent(wrapper)
        assert batch

        for doc_key in batch.docs:
            assert batch.input_data(doc_key)
            assert batch.output_data(doc_key)

########NEW FILE########
__FILENAME__ = test_commands
from StringIO import StringIO
from dexy.version import DEXY_VERSION
from dexy.wrapper import Wrapper
from mock import patch
from nose.exc import SkipTest
from nose.tools import raises
from tests.utils import tempdir
from tests.utils import wrap
import dexy.commands
import os
import sys

def test_init_wrapper():
    with tempdir():
        with open("dexy.conf", "w") as f:
            f.write("artifactsdir: custom")

        modargs = {}
        wrapper = dexy.commands.utils.init_wrapper(modargs)
        assert wrapper.artifacts_dir == 'custom'

@patch.object(sys, 'argv', ['dexy', 'setup'])
def test_setup_with_dexy_conf_file():
    with tempdir():
        with open("dexy.conf", "w") as f:
            f.write("artifactsdir: custom")

        dexy.commands.run()
        assert os.path.exists("custom")
        assert os.path.isdir("custom")
        assert not os.path.exists("artifacts")

@raises(SystemExit)
@patch.object(sys, 'argv', ['dexy', 'grep', '-expr', 'hello'])
def test_grep():
    with wrap():
        dexy.commands.run()

@patch.object(sys, 'argv', ['dexy', 'grep'])
@patch('sys.stderr', new_callable=StringIO)
def test_grep_without_expr(stderr):
    raise SkipTest()
    try:
        dexy.commands.run()
    except SystemExit as e:
        assert e.message == 1
        assert 'Must specify either expr or key' in stderr.getvalue()

@patch.object(sys, 'argv', ['dexy'])
@patch('sys.stderr', new_callable=StringIO)
def test_run_with_userfeedback_exception(stderr):
    with wrap():
        with open("docs.txt", "w") as f:
            f.write("*.py|py")

        with open("hello.py", "w") as f:
            f.write("raise")

        dexy.commands.run()

@patch.object(sys, 'argv', ['dexy', 'invalid'])
@patch('sys.stdout', new_callable=StringIO)
def test_run_invalid_command(stdout):
    try:
        dexy.commands.run()
        assert False, 'should raise SystemExit'
    except SystemExit as e:
        assert e.message == 1

@patch.object(sys, 'argv', ['dexy', '--help'])
@patch('sys.stdout', new_callable=StringIO)
def test_run_help_old_syntax(stdout):
    dexy.commands.run()
    assert "Commands for running dexy:" in stdout.getvalue()

@patch.object(sys, 'argv', ['dexy', '--version'])
@patch('sys.stdout', new_callable=StringIO)
def test_run_version_old_syntax(stdout):
    dexy.commands.run()
    assert DEXY_VERSION in stdout.getvalue()

@patch.object(sys, 'argv', ['dexy', 'help'])
@patch('sys.stdout', new_callable=StringIO)
def test_run_help(stdout):
    dexy.commands.run()
    assert "Commands for running dexy:" in stdout.getvalue()

@patch.object(sys, 'argv', ['dexy', 'version'])
@patch('sys.stdout', new_callable=StringIO)
def test_run_version(stdout):
    dexy.commands.run()
    assert DEXY_VERSION in stdout.getvalue()

@patch.object(sys, 'argv', ['dexy'])
@patch('sys.stdout', new_callable=StringIO)
def test_run_dexy(stdout):
    with tempdir():
        wrapper = Wrapper()
        wrapper.create_dexy_dirs()
        dexy.commands.run()

### "viewer-ping"
@patch.object(sys, 'argv', ['dexy', 'viewer:ping'])
@patch('sys.stdout', new_callable=StringIO)
def test_viewer_command(stdout):
    dexy.commands.run()
    assert "pong" in stdout.getvalue()

### "conf"
@patch.object(sys, 'argv', ['dexy', 'conf'])
@patch('sys.stdout', new_callable=StringIO)
def test_conf_command(stdout):
    with tempdir():
        dexy.commands.run()
        assert os.path.exists("dexy.conf")
        assert "has been written" in stdout.getvalue()

@patch.object(sys, 'argv', ['dexy', 'conf'])
@patch('sys.stdout', new_callable=StringIO)
def test_conf_command_if_path_exists(stdout):
    with tempdir():
        with open("dexy.conf", "w") as f:
            f.write("foo")
        assert os.path.exists("dexy.conf")
        dexy.commands.run()
        assert "dexy.conf already exists" in stdout.getvalue()
        assert "artifactsdir" in stdout.getvalue()

@patch.object(sys, 'argv', ['dexy', 'conf', '-p'])
@patch('sys.stdout', new_callable=StringIO)
def test_conf_command_with_print_option(stdout):
    with tempdir():
        dexy.commands.run()
        assert not os.path.exists("dexy.conf")
        assert "artifactsdir" in stdout.getvalue()

### "filters"
@patch.object(sys, 'argv', ['dexy', 'filters'])
@patch('sys.stdout', new_callable=StringIO)
def test_filters_cmd(stdout):
    dexy.commands.run()
    assert "pyg : Apply Pygments" in stdout.getvalue()

@patch.object(sys, 'argv', ['dexy', 'filters', '-alias', 'pyg'])
@patch('sys.stdout', new_callable=StringIO)
def test_filters_cmd_alias(stdout):
    dexy.commands.run()
    assert "pyg, pygments" in stdout.getvalue()

@patch.object(sys, 'argv', ['dexy', 'filters', '-versions'])
@patch('sys.stdout', new_callable=StringIO)
def test_filters_text_versions__slow(stdout):
    dexy.commands.run()
    assert "Installed version: Python" in stdout.getvalue()

@patch.object(sys, 'argv', ['dexy', 'filters', '-alias', 'pyg', '-source'])
@patch('sys.stdout', new_callable=StringIO)
def test_filters_text_single_alias_source(stdout):
    dexy.commands.run()
    text = stdout.getvalue()
    assert "pyg, pygments" in text
    assert "class" in text
    assert "PygmentsFilter" in text
    assert not "class PygmentsFilter" in text

@patch.object(sys, 'argv', ['dexy', 'filters', '-alias', 'pyg', '-source', '-nocolor'])
@patch('sys.stdout', new_callable=StringIO)
def test_filters_text_single_alias_source_nocolor(stdout):
    dexy.commands.run()
    text = stdout.getvalue()
    assert "pyg, pygments" in text
    assert "class PygmentsFilter" in text

@patch.object(sys, 'argv', ['dexy', 'parsers'])
@patch('sys.stdout', new_callable=StringIO)
def test_parsers_text(stdout):
    dexy.commands.run()
    text = stdout.getvalue()
    assert "Yaml Parser" in text

@patch.object(sys, 'argv', ['dexy', 'nodes'])
@patch('sys.stdout', new_callable=StringIO)
def test_nodes_text(stdout):
    dexy.commands.run()
    text = stdout.getvalue()
    assert "bundle" in text

@patch.object(sys, 'argv', ['dexy', 'env'])
@patch('sys.stdout', new_callable=StringIO)
def test_env_text(stdout):
    dexy.commands.run()
    text = stdout.getvalue()
    assert "uuid" in text

########NEW FILE########
__FILENAME__ = test_data
from dexy.doc import Doc
from dexy.data import Data
from tests.utils import wrap
import dexy.data
import dexy.exceptions
import os

def test_sectioned_data_setitem_delitem():
    with wrap() as wrapper:
        contents=[
                {},
                {
                    "name" : "Welcome",
                    "contents" : "This is the first section."
                }
            ]

        doc = Doc("hello.txt",
                wrapper,
                [],
                data_type="sectioned",
                contents=contents
                )

        wrapper.run_docs(doc)
        data = doc.output_data()

        assert data.alias == 'sectioned'
        assert len(data) == 1

        # Add a new section
        data["Conclusions"] = "This is the final section."

        assert len(data) == 2
        
        assert unicode(data['Welcome']) == "This is the first section."
        assert unicode(data["Conclusions"]) == "This is the final section."

        # Modify an existing section
        data["Welcome"] = "This is the initial section."

        assert len(data) == 2

        assert unicode(data['Welcome']) == "This is the initial section."
        assert unicode(data["Conclusions"]) == "This is the final section."

        del data["Conclusions"]

        assert len(data) == 1
        assert data.keys() == ["Welcome"]

def test_generic_data_unicode():
    with wrap() as wrapper:
        doc = Doc("hello.txt",
                wrapper,
                [],
                contents=u"\u2042 we know\n"
                )

        wrapper.run_docs(doc)
        data = doc.output_data()

        assert data.alias == 'generic'
        assert unicode(data) == u"\u2042 we know\n"

        assert isinstance(str(data), str)
        assert isinstance(unicode(data), unicode)

def test_generic_data_stores_string():
    with wrap() as wrapper:
        doc = Doc("hello.txt",
                wrapper,
                [],
                contents="hello"
                )

        wrapper.run_docs(doc)
        data = doc.output_data()

        assert data.alias == 'generic'
        assert data._data == "hello"

def test_sectioned_data_stores_list_of_dicts():
    with wrap() as wrapper:
        contents=[
                {},
                {
                    "name" : "Welcome",
                    "contents" : "This is the first section."
                }
            ]

        doc = Doc("hello.txt",
                wrapper,
                [],
                data_type="sectioned",
                contents=contents
                )

        wrapper.run_docs(doc)
        data = doc.output_data()

        assert data.alias == 'sectioned'
        assert data._data == contents
        assert data['Welcome']['contents'] == "This is the first section."
        assert data[0]['contents'] == "This is the first section."

def test_keyvalue_data_stores_dict():
    with wrap() as wrapper:
        doc = Doc("hello.json",
                wrapper,
                [],
                data_type="keyvalue",
                contents="dummy contents"
                )

        wrapper.run_docs(doc)
        data = doc.output_data()

        assert data.alias == 'keyvalue'
        assert data.keys() == []

        data.append("foo", 123)
        data.append("bar", 456)

        assert sorted(data.keys()) == ["bar", "foo"]

def test_canonical_name():
    with wrap() as wrapper:
        doc = Doc("hello.txt",
                wrapper,
                [],
                contents="hello",
                output_name="yello.abc")

        wrapper.run_docs(doc)
        assert doc.output_data().output_name() == "yello.abc"
        wrapper.report()
        assert os.path.exists(os.path.join('output', 'yello.abc'))

def test_attempt_write_outside_project_root():
    with wrap() as wrapper:
        try:
            doc = Doc("../../example.txt",
                wrapper,
                [],
                contents = "hello")
            doc.setup()
            doc.setup_datas()
            assert False, 'should raise UserFeedback'
        except dexy.exceptions.UserFeedback as e:
            print str(e)
            assert 'trying to write' in str(e)

def test_key_value_data():
    with wrap() as wrapper:
        settings = {
                'canonical-name' : 'doc.json',
                'storage-type' : 'json'
                }
        data = dexy.data.KeyValue("doc.json", ".json", "doc.json", settings, wrapper)
        data.setup_storage()

        assert not data._data
        assert data.storage._data == {}

        # We use the append method to add key-value pairs.
        data.append('foo', 'bar')
        assert len(data.keys()) == 1

        assert data.value('foo') == 'bar'
        assert data.storage['foo'] == 'bar'

def test_key_value_data_sqlite():
    with wrap() as wrapper:
        wrapper.to_walked()
        wrapper.to_checked()

        settings = {
                'canonical-name' : 'doc.sqlite3'
                }

        data = dexy.data.KeyValue("doc.sqlite3", ".sqlite3", "abc000", settings, wrapper)
        data.setup_storage()
        data.storage.connect()

        data.append('foo', 'bar')
        assert len(data.keys()) == 1

        assert data.value('foo') == 'bar'
        assert ["%s: %s" % (k, v) for k, v in data.storage.iteritems()][0] == "foo: bar"

def test_generic_data():
    with wrap() as wrapper:
        wrapper.to_walked()
        wrapper.to_checked()

        CONTENTS = "contents go here"

        # Create a GenericData object
        settings = {
                'canonical-name' : 'doc.txt'
                }
        data = dexy.data.Generic("doc.txt", ".txt", "abc000", settings, wrapper)
        data.setup_storage()

        # Assign some text contents
        data._data = CONTENTS
        assert data.has_data()
        assert not data.is_cached(True)

        # Save data to disk
        data.save()
        assert data.has_data()
        assert data.is_cached(True)
        assert data.filesize(True) > 10

        # Clear data from memory
        data._data = None

        # Load it again from disk
        data.load_data(True)
        assert data._data == CONTENTS

        assert data.as_text() == CONTENTS

def test_init_data():
    with wrap() as wrapper:
        settings = {
                'canonical-name' : 'doc.abc'
                }
        data = dexy.data.Generic("doc.txt", ".abc", "def123", settings, wrapper)
        data.setup_storage()

        assert data.key == "doc.txt"
        assert data.name == "doc.abc"
        assert data.ext == ".abc"
        assert data.storage_key == "def123"

        assert not data.has_data()
        assert not data.is_cached()

########NEW FILE########
__FILENAME__ = test_doc
from dexy.data import Data
from dexy.doc import Doc
from dexy.exceptions import UserFeedback
from tests.utils import wrap
from nose.tools import raises

def test_create_doc_with_one_filter():
    with wrap() as wrapper:
        doc = Doc("foo.txt|dexy", wrapper, [], contents="foo")

        assert len(doc.filters) == 1
        f = doc.filters[0]

        assert f.doc == doc
        assert not f.prev_filter
        assert not f.next_filter

        wrapper.run_docs(doc)

def test_create_doc_with_two_filters():
    with wrap() as wrapper:
        doc = Doc("foo.txt|dexy|dexy", wrapper, [], contents="foo")
        assert len(doc.filters) == 2

        f1, f2 = doc.filters

        assert f1.doc == doc
        assert f2.doc == doc

        assert f1.next_filter == f2
        assert f2.prev_filter == f1

        assert not f1.prev_filter
        assert not f2.next_filter

@raises(UserFeedback)
def test_blank_alias():
    with wrap() as wrapper:
        Doc("abc.txt|", wrapper, [], contents='foo')

def test_output_is_data():
    with wrap() as wrapper:
        doc = Doc("abc.txt", wrapper, [], contents="these are the contents")
        wrapper.run_docs(doc)
        assert isinstance(doc.output_data(), Data)

def test_create_virtual_initial_artifact():
    with wrap() as wrapper:
        doc = Doc("abc.txt", wrapper, [], contents="these are the contents")
        wrapper.run_docs(doc)
        assert doc.output_data().__class__.__name__ == "Generic"

########NEW FILE########
__FILENAME__ = test_filter
from tests.utils import wrap
import dexy.filter

def test_filters_by_tag():
    tags_filters = dexy.filter.filters_by_tag()
    assert 'latex' in tags_filters.keys()

def test_filter_aliases_by_tag():
    first_expected_tag = 'R'
    first_actual = dexy.filter.filter_aliases_by_tag()[0][0]
    assert first_actual == first_expected_tag, first_actual

def test_filter_iter():
    for instance in dexy.filter.Filter:
        assert instance.setting('aliases')

def test_filter_args():
    with wrap() as wrapper:
        import dexy.node
        doc = dexy.node.Node.create_instance('doc',
                "hello.txt|filterargs",
                wrapper,
                [],
                contents="hello",
                foo="bar",
                filterargs={"abc" : 123, "foo" : "baz" }
                )

        wrapper.run_docs(doc)

        result = unicode(doc.output_data())

        assert "Here are the filter settings:" in result
        assert "abc: 123" in result
        assert "foo: baz" in result
        assert "foo: bar" in result


########NEW FILE########
__FILENAME__ = test_names
from dexy.doc import Doc
from tests.utils import wrap
import os

def test_output_name_with_filters():
    with wrap() as wrapper:
        doc = Doc(
                "data.md|markdown",
                wrapper,
                [],
                output_name="finished.bar",
                contents="foo"
                )
        wrapper.run_docs(doc)

        assert doc.initial_data.name == "data.md"
        assert doc.output_data().output_name() == "finished.bar"

def test_custom_name():
    with wrap() as wrapper:
        doc = Doc(
                "foo/data.txt",
                wrapper,
                [],
                output_name="data.abc",
                contents="12345.67"
                )
        wrapper.run_docs(doc)

        assert doc.output_data().output_name() == "foo/data.abc"

def test_custom_name_in_subdir():
    with wrap() as wrapper:
        doc = Doc(
                "data.txt",
                wrapper,
                [],
                output_name="subdir/data.abc",
                contents="12345.67"
                )
        wrapper.run_docs(doc)
        wrapper.report()

        assert doc.output_data().output_name() == "subdir/data.abc"
        assert doc.output_data().parent_output_dir() == "subdir"

def test_custom_name_with_args():
    with wrap() as wrapper:
        doc = Doc(
                "data.txt",
                wrapper,
                [],
                output_name="%(bar)s/data-%(foo)s.abc",
                foo='bar',
                bar='baz',
                contents="12345.67"
                )
        wrapper.run_docs(doc)
        wrapper.report()

        assert doc.output_data().output_name() == "baz/data-bar.abc"
        assert doc.output_data().parent_output_dir() == "baz"
        assert os.path.exists("output/baz/data-bar.abc")

def test_custom_name_with_leading_slash():
    with wrap() as wrapper:
        doc = Doc(
                "foobarbaz/data.txt",
                wrapper,
                [],
                output_name="/%(bar)s/data-%(foo)s.abc",
                foo='bar',
                bar='baz',
                contents="12345.67"
                )
        wrapper.run_docs(doc)
        assert doc.output_data().output_name() == "baz/data-bar.abc"

########NEW FILE########
__FILENAME__ = test_node
from dexy.doc import Doc
from dexy.node import Node
from dexy.node import PatternNode
from tests.utils import wrap
from dexy.wrapper import Wrapper
import dexy.doc
import dexy.node
import os
import time

def test_create_node():
    with wrap() as wrapper:
        node = dexy.node.Node.create_instance(
                "doc",
                "foo.txt",
                wrapper,
                [],
                # kwargs
                foo='bar',
                contents="these are contents"
                )

        assert node.__class__ == dexy.doc.Doc
        assert node.args['foo'] == 'bar'
        assert node.wrapper == wrapper
        assert node.inputs == []
        assert len(node.hashid) == 32

def test_node_arg_caching():
    with wrap() as wrapper:
        wrapper.nodes = {}
        node = dexy.node.Node("foo", wrapper, [], foo='bar', baz=123)
        wrapper.add_node(node)

        assert node.hashid == 'acbd18db4cc2f85cedef654fccc4a4d8'
        assert node.args['foo'] == 'bar'
        assert node.args['baz'] == 123
        assert node.sorted_arg_string() == '[["baz", 123], ["foo", "bar"]]'

        assert os.path.exists(wrapper.artifacts_dir)
        assert not os.path.exists(wrapper.node_argstrings_filename())
        wrapper.save_node_argstrings()
        assert os.path.exists(wrapper.node_argstrings_filename())
        wrapper.load_node_argstrings()
        assert not node.check_args_changed()

        node.args['baz'] = 456
        assert node.check_args_changed()
        wrapper.save_node_argstrings()
        wrapper.load_node_argstrings()
        assert not node.check_args_changed()

SCRIPT_YAML = """
script:scriptnode:
    - start.sh|shint
    - middle.sh|shint
    - end.sh|shint
"""

def test_script_node_caching__slow():
    with wrap():
        with open("start.sh", "w") as f:
            f.write("pwd")

        with open("middle.sh", "w") as f:
            f.write("echo `time`")

        with open("end.sh", "w") as f:
            f.write("echo 'done'")

        with open("dexy.yaml", "w") as f:
            f.write(SCRIPT_YAML)

        wrapper1 = Wrapper(log_level="DEBUG")
        wrapper1.run_from_new()

        for node in wrapper1.nodes.values():
            assert node.state == 'ran'

        wrapper2 = Wrapper()
        wrapper2.run_from_new()

        for node in wrapper2.nodes.values():
            assert node.state == 'consolidated'

        time.sleep(1.1)
        with open("middle.sh", "w") as f:
            f.write("echo 'new'")

        wrapper3 = Wrapper()
        wrapper3.run_from_new()

        for node in wrapper1.nodes.values():
            assert node.state == 'ran'

# TODO mock out os.stat to get different mtimes without having to sleep?

def test_node_caching__slow():
    with wrap() as wrapper:
        with open("hello.py", "w") as f:
            f.write("print 1+2\n")

        with open("doc.txt", "w") as f:
            f.write("1 + 1 = {{ d['hello.py|py'] }}")

        wrapper = Wrapper(log_level='DEBUG')
        hello_py = Doc("hello.py|py", wrapper)
        doc_txt = Doc("doc.txt|jinja",
                wrapper,
                [hello_py]
                )

        wrapper.run_docs(doc_txt)

        assert str(doc_txt.output_data()) == "1 + 1 = 3\n"
        assert str(hello_py.output_data()) == "3\n"

        assert hello_py.state == 'ran'
        assert doc_txt.state == 'ran'

        wrapper = Wrapper(log_level='DEBUG')
        hello_py = Doc("hello.py|py", wrapper)
        doc_txt = Doc("doc.txt|jinja",
                wrapper,
                [hello_py]
                )
        wrapper.run_docs(doc_txt)

        assert hello_py.state == 'consolidated'
        assert doc_txt.state == 'consolidated'

        time.sleep(1.1)
        with open("doc.txt", "w") as f:
            f.write("1 + 1 = {{ d['hello.py|py'] }}\n")

        wrapper = Wrapper(log_level='DEBUG')
        hello_py = Doc("hello.py|py", wrapper)
        doc_txt = Doc("doc.txt|jinja",
                wrapper,
                [hello_py]
                )
        wrapper.run_docs(doc_txt)

        assert hello_py.state == 'consolidated'
        assert doc_txt.state == 'ran'

        time.sleep(1.1)
        with open("hello.py", "w") as f:
            f.write("print 1+1\n")

        wrapper = Wrapper(log_level='DEBUG')
        hello_py = Doc("hello.py|py", wrapper)
        doc_txt = Doc("doc.txt|jinja",
                wrapper,
                [hello_py]
                )
        wrapper.run_docs(doc_txt)

        assert hello_py.state == 'ran'
        assert doc_txt.state == 'ran'

def test_node_init_with_inputs():
    with wrap() as wrapper:
        node = Node("foo.txt",
                wrapper,
                [Node("bar.txt", wrapper)]
                )
        assert node.key == "foo.txt"
        assert node.inputs[0].key == "bar.txt"

        expected = {
                0 : "bar.txt",
                1 : "foo.txt" 
            }
    
        for i, n in enumerate(node.walk_inputs()):
            assert expected[i] == n.key

def test_doc_node_populate():
    with wrap() as wrapper:
        node = Node.create_instance(
                'doc', "foo.txt", wrapper,
                [], contents='foo')

        assert node.key_with_class() == "doc:foo.txt"

def test_doc_node_with_filters():
    with wrap() as wrapper:
        node = Node.create_instance('doc',
                "foo.txt|outputabc", wrapper, [], contents='foo')
        assert node.key_with_class() == "doc:foo.txt|outputabc"

def test_pattern_node():
    with wrap() as wrapper:
        with open("foo.txt", "w") as f:
            f.write("foo!")

        with open("bar.txt", "w") as f:
            f.write("bar!")

        wrapper = Wrapper(log_level='DEBUG')
        wrapper.to_valid()

        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        node = PatternNode("*.txt", 
                wrapper,
                [],
                foo="bar")
        assert node.args['foo'] == 'bar'
        wrapper.run_docs(node)
        assert len(node.children) == 2

        for child in node.children:
            assert child.__class__.__name__ == "Doc"
            assert child.args['foo'] == 'bar'
            assert child.key_with_class() in ["doc:foo.txt", "doc:bar.txt"]
            assert child.filters == []

def test_pattern_node_multiple_filters():
    with wrap() as wrapper:
        with open("foo.txt", "w") as f:
            f.write("foo!")

        wrapper = Wrapper(log_level='DEBUG')
        wrapper.to_valid()

        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        node = PatternNode("*.txt|dexy|dexy|dexy", wrapper=wrapper)
        doc = node.children[0]
        assert doc.key == "foo.txt|dexy|dexy|dexy"
        assert doc.filter_aliases == ['dexy', 'dexy', 'dexy']
        assert doc.parent == node

def test_pattern_node_one_filter():
    with wrap() as wrapper:
        with open("foo.txt", "w") as f:
            f.write("foo!")

        wrapper = Wrapper(log_level='DEBUG')
        wrapper.to_valid()

        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        node = PatternNode("*.txt|dexy", wrapper=wrapper)
        doc = node.children[0]
        assert doc.key == "foo.txt|dexy"
        assert doc.filter_aliases == ['dexy']
        assert doc.parent == node

########NEW FILE########
__FILENAME__ = test_parser
from dexy.parser import AbstractSyntaxTree
from dexy.parsers.doc import Original
from dexy.parsers.doc import TextFile
from dexy.parsers.doc import Yaml
from tests.utils import wrap
from dexy.wrapper import Wrapper
import dexy.exceptions
import os

def test_text_parser():
    with wrap() as wrapper:
        with open("f1.py", "w") as f:
            f.write("print 'hello'")

        with open("f2.py", "w") as f:
            f.write("print 'hello'")

        with open("index.md", "w") as f:
            f.write("")

        wrapper = Wrapper()
        wrapper.to_valid()

        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = TextFile(wrapper, ast)
        parser.parse(".", """
        *.py
        *.py|pyg
        *.md|jinja
        """)
        ast.walk()
        assert len(wrapper.nodes) == 8

YAML_WITH_INACTIVE = """
foo:
    - inactive: True
"""

def test_parse_inactive():
    with wrap() as wrapper:
        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = Yaml(wrapper, ast)
        parser.parse('.', YAML_WITH_INACTIVE)
        ast.walk()
        assert len(wrapper.nodes) == 0

YAML_WITH_DEFAULT_OFF = """
foo:
    - default: False
"""

def test_parse_default():
    with wrap() as wrapper:
        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = Yaml(wrapper, ast)
        parser.parse('.', YAML_WITH_DEFAULT_OFF)
        ast.walk()
        assert len(wrapper.nodes) == 0

    with wrap() as wrapper:
        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        wrapper.full = True
        parser = Yaml(wrapper, ast)
        parser.parse('.', YAML_WITH_DEFAULT_OFF)
        ast.walk()
        assert len(wrapper.nodes) == 1

def test_yaml_with_defaults():
    with wrap() as wrapper:
        os.makedirs("s1/s2")

        with open("s1/s2/hello.txt", "w") as f:
            f.write("hello")

        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = Yaml(wrapper, ast)
        parser.parse('.', YAML_WITH_DEFAULTS)
        ast.walk()

        assert wrapper.roots[0].args['foo'] == 'bar'
    
def test_invalid_yaml():
    with wrap() as wrapper:
        ast = AbstractSyntaxTree(wrapper)
        parser = Yaml(wrapper, ast)
        try:
            parser.parse('.', INVALID_YAML)
            assert False, "should raise UserFeedback"
        except dexy.exceptions.UserFeedback as e:
            assert 'YAML' in e.message

def test_yaml_parser():
    with wrap() as wrapper:
        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = Yaml(wrapper, ast)
        parser.parse('.', YAML)
        for doc in wrapper.roots:
            assert doc.__class__.__name__ == 'BundleNode'
            assert doc.key in ['code', 'wordpress']

        wrapper.run_docs()

def test_text_parser_blank_lines():
    with wrap() as wrapper:
        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = TextFile(wrapper, ast)
        parser.parse('.', "\n\n")
        ast.walk()
        docs = wrapper.roots
        assert len(docs) == 0

def test_text_parser_comments():
    with wrap() as wrapper:
        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = TextFile(wrapper, ast)
        parser.parse('.', """
        valid.doc { "contents" : "foo" }
        # commented-out.doc
        """)
        ast.walk()

        assert len(wrapper.roots) == 1
        assert wrapper.roots[0].key == "valid.doc"

def test_text_parser_valid_json():
    with wrap() as wrapper:
        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = TextFile(wrapper, ast)
        parser.parse('.', """
        doc.txt { "contents" : "123" }
        """)
        ast.walk()

        docs = wrapper.roots
        assert docs[0].key == "doc.txt"
        assert docs[0].args['contents'] == "123"

def test_text_parser_invalid_json():
    with wrap() as wrapper:
        ast = AbstractSyntaxTree(wrapper)
        parser = TextFile(wrapper, ast)
        try:
            parser.parse('.', """
            doc.txt { "contents" : 123
            """)
            assert False, 'should raise UserFeedback'
        except dexy.exceptions.UserFeedback as e:
            assert 'unable to parse' in e.message

def test_text_parser_virtual_file():
    with wrap() as wrapper:
        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = TextFile(wrapper, ast)
        parser.parse('.', """
        virtual.txt { "contents" : "hello" }
        """)
        ast.walk()

        wrapper.transition('walked')
        wrapper.to_checked()

        wrapper.run()
        docs = wrapper.roots

        assert docs[0].key == "virtual.txt"
        assert str(docs[0].output_data()) == "hello"

def test_original_parser():
    with wrap() as wrapper:
        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        conf = """{
        "*.txt" : {}
        }"""
        ast = AbstractSyntaxTree(wrapper)
        parser = Original(wrapper, ast)
        parser.parse('.', conf)
        ast.walk()

        assert wrapper.roots[0].key_with_class() == "pattern:*.txt"

def test_original_parser_allinputs():
    with wrap() as wrapper:
        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        conf = """{
        "*.txt" : {},
        "hello.txt" : { "contents" : "Hello!" },
        "*.md|jinja" : { "allinputs" : true }
        }"""

        ast = AbstractSyntaxTree(wrapper)
        parser = Original(wrapper, ast)
        parser.parse('.', conf)
        ast.walk()

        assert len(wrapper.roots) == 1
        assert wrapper.roots[0].key_with_class() == "pattern:*.md|jinja"

INVALID_YAML = """
code:
    - abc
    def
"""

YAML = """
code:
    - .R|pyg:
         "pyg" : { "foo" : "bar" }
    - .R|idio

wordpress:
    - code
    - test.txt|jinja:
        - contents: 'test'
    - .md|jinja|markdown|wp
"""

YAML_WITH_DEFAULTS = """
defaults:
    pyg: { lexer : moin }
    foo: bar

code:
    - .R|pyg

s1/s2/hello.txt|jinja:
    code
"""

########NEW FILE########
__FILENAME__ = test_plugin
import dexy.plugin

class WidgetBase(dexy.plugin.Plugin):
    """
    Example of plugin.
    """
    __metaclass__ = dexy.plugin.PluginMeta
    _settings = {
            'foo' : ("Default value for foo", "bar"),
            'abc' : ("Default value for abc", 123)
            }

class Widget(WidgetBase):
    """
    Widget class.
    """
    aliases = ['widget']

class SubWidget(Widget):
    """
    Subwidget class.
    """
    aliases = ['sub']
    _settings = {
            'foo' : 'baz'
            }

class Fruit(dexy.plugin.Plugin):
    '''fruit class'''
    __metaclass__ = dexy.plugin.PluginMeta
    aliases = ['fruit']
    _settings = {}

class Starch(dexy.plugin.Plugin):
    '''starch class'''
    __metaclass__ = dexy.plugin.PluginMeta
    aliases = ['starch']
    _settings = {}
    _other_class_settings = {
            'fruit' : {
                    "color" : ("The color of the fruit", "red")
                }
            }

def test_plugin_meta():
    new_class = dexy.plugin.PluginMeta(
            "Foo",
            (dexy.plugin.Plugin,),
            {
                'aliases' : [],
                "__doc__" : 'help',
                '__metaclass__' : dexy.plugin.PluginMeta
                }
            )

    assert new_class.__name__ == 'Foo'
    assert new_class.__doc__ == 'help'
    assert new_class.aliases == []
    assert new_class.plugins == {}

def test_create_instance():
    widget = Widget.create_instance('widget')
    assert widget.setting('foo') == 'bar'

    sub = Widget.create_instance('sub')
    assert sub.setting('foo') == 'baz'
    assert sub.setting('abc') == 123
    assert sub.setting_values()['foo'] == 'baz'
    assert sub.setting_values()['abc'] == 123

def test_other_class_settings():
    fruit = Fruit()
    fruit.initialize_settings()
    assert fruit.setting('color') == 'red'

########NEW FILE########
__FILENAME__ = test_sectioned
from dexy.data import Sectioned
from dexy.exceptions import UserFeedback
from tests.utils import wrap
import os

def test_create_new_sectioned_dat():
    with wrap() as wrapper:
        settings = {
                'canonical-name' : "doc.txt"
                }
        data = Sectioned("doc.txt", ".txt", "def123", settings, wrapper)
        data.setup()

        data['alpha'] = "This is the first section."
        data['alpha']['abc'] = 123
        assert str(data['alpha']) == "This is the first section."

        data['beta'] = "This is the second section."
        data['beta']['def'] = 456

        assert str(data['alpha']) == "This is the first section."
        assert str(data['beta']) == "This is the second section."
        assert data['alpha']['abc'] == 123
        assert data['beta']['def'] == 456

        data['gamma'] = "This is the third section."
        del data['beta']
        assert data.keys() == ['alpha', 'gamma']

def test_load_json():
    with wrap() as wrapper:
        os.makedirs(".dexy/this/de")
        with open(".dexy/this/de/def123.txt", "w") as f:
            f.write("""
            [
                { "foo" : "bar" },
                { "name" : "alpha", "contents" : "This is the first section.", "abc" : 123 } ,
                { "name" : "beta", "contents" : "This is the second section.", "def" : 456 } 
            ]
            """)

        settings = {
                'canonical-name' : "doc.txt"
                }
        data = Sectioned("doc.txt", ".txt", "def123", settings, wrapper)
        data.setup_storage()

        assert data.keys() == ["alpha", "beta"]
        assert str(data) == "This is the first section.\nThis is the second section."
        assert unicode(data) == u"This is the first section.\nThis is the second section."
        assert data.keyindex("alpha") == 0
        assert data.keyindex("beta") == 1
        assert data.keyindex("gamma") == -1

        assert str(data["alpha"]) == "This is the first section."
        assert str(data["beta"]) == "This is the second section."
        assert unicode(data["alpha"]) == u"This is the first section."
        assert unicode(data["beta"]) == u"This is the second section."

        assert data["foo"] == "bar"

        assert data['alpha']['abc'] == 123
        assert data['beta']['def'] == 456

        try:
            data["zxx"]
            assert False, "should raise error"
        except UserFeedback as e:
            assert "No value for zxx" in str(e)

########NEW FILE########
__FILENAME__ = test_template
from dexy.templates.standard import DefaultTemplate
from tests.utils import tempdir
import os

def test_run():
    with tempdir():
        DefaultTemplate().generate("test")
        assert not os.path.exists("dexy.rst")

def test_dexy():
    for wrapper in DefaultTemplate().dexy():
        batch = wrapper.batch
        assert 'jinja' in batch.filters_used
        assert "doc:hello.txt|jinja" in batch.docs
        assert "doc:dexy.rst|jinja|rst2html" in batch.docs

def test_validate_default():
    DefaultTemplate().validate()

########NEW FILE########
__FILENAME__ = test_utils
from dexy.filter import Filter
from tests.utils import runfilter
from nose.exc import SkipTest
from nose.tools import raises
from dexy.utils import s
from dexy.utils import split_path
from dexy.utils import iter_paths

def test_iter_path():
    full_path = "/foo/bar/baz"

    expected_paths = {
            0 : '/',
            1 : '/foo',
            2 : '/foo/bar',
            3 : '/foo/bar/baz'
            }

    for i, path in enumerate(iter_paths(full_path)):
        assert expected_paths[i] == path

def test_split_path():
    path = "foo/bar/baz"
    assert split_path(path) == ['foo', 'bar', 'baz']

def test_split_path_with_root():
    path = "/foo/bar/baz"
    assert split_path(path) == ['', 'foo', 'bar', 'baz']

def test_s():
    text = """This is some text
    which goes onto
    many lines and has
    indents at the start."""
    assert s(text) == 'This is some text which goes onto many lines and has indents at the start.'

class InactiveDexyFilter(Filter):
    """
    filter which is always inactive, for testing
    """
    aliases = ['inactive']

    def is_active(self):
        return False

@raises(SkipTest)
def test_inactive_filters_skip():
    with runfilter("inactive", "hello"):
        pass

########NEW FILE########
__FILENAME__ = test_workspace

########NEW FILE########
__FILENAME__ = test_wrapper
from dexy.commands.utils import init_wrapper
from dexy.exceptions import InternalDexyProblem
from dexy.exceptions import UserFeedback
from dexy.parser import AbstractSyntaxTree
from dexy.parsers.doc import Yaml
from tests.utils import capture_stdout
from tests.utils import tempdir
from tests.utils import wrap
from dexy.wrapper import Wrapper
import dexy.batch
import os

def test_deprecated_dot_dexy_file():
    with tempdir():
        with open(".dexy", 'w') as f:
            f.write("{}")
        wrapper = Wrapper()
        try:
            wrapper.assert_dexy_dirs_exist()
        except UserFeedback as e:
            assert "this format is no longer supported" in str(e)

def test_cache_and_dexy_dirs_present():
    with tempdir():
        os.mkdir(".dexy")
        os.mkdir(".cache")
        with open(".dexy/.dexy-generated", 'w') as f:
            f.write("")
        with open(".cache/.dexy-generated", 'w') as f:
            f.write("")

        wrapper = Wrapper()

        try:
            wrapper.assert_dexy_dirs_exist()
        except UserFeedback as e:
            assert "Please remove '.cache'" in str(e)

        os.remove(".cache/.dexy-generated")
        wrapper.assert_dexy_dirs_exist()

        # Cache still exists but dexy just ignores it.
        assert os.path.exists(".cache")

        # Dexy uses .dexy dir
        assert os.path.exists(".dexy")

def test_move_cache_dir():
    with capture_stdout() as stdout:
        with tempdir():
            os.mkdir(".cache")
            with open(".cache/.dexy-generated", 'w') as f:
                f.write("")
    
            wrapper = Wrapper()
            wrapper.assert_dexy_dirs_exist()
    
            assert "Moving directory '.cache'" in stdout.getvalue()
            assert not os.path.exists(".cache")
            assert os.path.exists(".dexy")

def test_old_cache_dir_with_settings():
    with capture_stdout() as stdout:
        with tempdir():
            os.mkdir(".cache")

            with open(".cache/.dexy-generated", 'w') as f:
                f.write("")
    
            wrapper = Wrapper(artifacts_dir = ".cache")
            wrapper.assert_dexy_dirs_exist()

            assert os.path.exists(".cache")
            assert not os.path.exists(".dexy")
    
            assert "You may have a dexy.conf file" in stdout.getvalue()

def test_remove_trash_no_trash():
    with tempdir():
        wrapper = Wrapper()
        wrapper.empty_trash()

def test_remove_trash_with_trash():
    with tempdir():
        wrapper = Wrapper()
        os.mkdir(".trash")
        assert os.path.exists(".trash")
        wrapper.empty_trash()
        assert not os.path.exists(".trash")

def test_state_new_after_init():
    wrapper = Wrapper()
    wrapper.validate_state('new')

def test_error_if_to_valid_called_without_dirs_setup():
    with tempdir():
        wrapper = Wrapper()
        try:
            wrapper.to_valid()
            assert False, "should not get here"
        except InternalDexyProblem:
            assert True

def test_state_valid_after_to_valid():
    with tempdir():
        wrapper = Wrapper()
        wrapper.create_dexy_dirs()
        wrapper.to_valid()
        wrapper.validate_state('valid')

def test_walked():
    with tempdir():
        with open("dexy.yaml", "w") as f:
            f.write("foo.txt")

        with open("foo.txt", "w") as f:
            f.write("foo")

        wrapper = Wrapper()
        wrapper.create_dexy_dirs()
        wrapper.to_valid()
        wrapper.to_walked()
        wrapper.validate_state('walked')

def test_checked():
    with tempdir():
        with open("dexy.yaml", "w") as f:
            f.write("foo.txt")

        with open("foo.txt", "w") as f:
            f.write("foo")

        wrapper = Wrapper()
        wrapper.create_dexy_dirs()
        wrapper.to_valid()
        wrapper.to_walked()
        wrapper.to_checked()
        wrapper.validate_state('checked')

def test_ran():
    with tempdir():
        with open("dexy.yaml", "w") as f:
            f.write("foo.txt")

        with open("foo.txt", "w") as f:
            f.write("foo")

        wrapper = Wrapper()
        wrapper.create_dexy_dirs()
        wrapper.run_from_new()
        for node in wrapper.roots:
            assert node.state == 'ran'
        wrapper.validate_state('ran')

        wrapper = Wrapper()
        wrapper.run_from_new()
        for node in wrapper.roots:
            assert node.state == 'consolidated'
        wrapper.validate_state('ran')

def test_explicit_configs():
    wrapper = Wrapper()
    wrapper.configs = "foo.txt bar.txt   abc/def/foo.txt "
    assert wrapper.explicit_config_files() == ['foo.txt',
            'bar.txt', 'abc/def/foo.txt']

def test_parse_doc_configs_single_empty_config():
    with tempdir():
        wrapper = Wrapper()
        wrapper.create_dexy_dirs()

        with open("dexy.yaml", "w") as f:
            f.write("foo.txt")

        with open("foo.txt", "w") as f:
            f.write("foo")

        wrapper = Wrapper()
        wrapper.to_valid()
        wrapper.to_walked()

def test_parse_doc_configs_no_configs():
    with tempdir():
        with capture_stdout() as stdout:
            wrapper = Wrapper()
            wrapper.create_dexy_dirs()

            wrapper = Wrapper()
            wrapper.to_valid()
            wrapper.to_walked()
            value = stdout.getvalue()
        assert "didn't find any document config files" in value

def test_assert_dexy_dirs():
    with tempdir():
        wrapper = Wrapper()
        try:
            wrapper.assert_dexy_dirs_exist()
            assert False
        except UserFeedback:
            assert True

def test_create_remove_dexy_dirs():
    with tempdir():
        wrapper = Wrapper()
        wrapper.create_dexy_dirs()
        wrapper.to_valid()
        assert wrapper.dexy_dirs_exist()
        wrapper.remove_dexy_dirs()
        assert not wrapper.dexy_dirs_exist()

def test_init_wrapper_if_dexy_dirs_exist():
    with tempdir():
        wrapper = Wrapper()
        wrapper.create_dexy_dirs()

        with open("hello.txt", "w") as f:
            f.write("hello")

        wrapper = Wrapper()
        wrapper.to_valid()
        assert wrapper.project_root
        wrapper.to_walked()
        assert 'hello.txt' in wrapper.filemap
        assert 'dexy.log' in os.listdir('.dexy')
        assert not '.dexy/dexy.log' in wrapper.filemap

def test_nodexy_files():
    with tempdir():
        wrapper = Wrapper()
        wrapper.create_dexy_dirs()

        with open("hello.txt", "w") as f:
            f.write("hello")

        os.makedirs("s1/s2/s3")

        nodexy_path = "s1/s2/.nodexy"
        with open(nodexy_path, 'w') as f:
            f.write("dexy stop here")

        with open("s1/s2/ignore.txt", "w") as f:
            f.write("dexy should ignore this")

        with open("s1/s2/s3/ignore.txt", "w") as f:
            f.write("dexy should also ignore this")

        # Only the hello.txt file is visible to dexy
        wrapper = Wrapper()
        wrapper.to_valid()
        wrapper.to_walked()
        assert len(wrapper.filemap) == 1
        assert 'hello.txt' in wrapper.filemap

        os.remove(nodexy_path)

        # Now we can see all 3 text files.
        wrapper = Wrapper()
        wrapper.to_valid()
        wrapper.to_walked()
        assert len(wrapper.filemap) == 3
        assert 'hello.txt' in wrapper.filemap
        assert 's1/s2/ignore.txt' in wrapper.filemap
        assert 's1/s2/s3/ignore.txt' in wrapper.filemap

# old
def test_config_for_directory():
    with wrap() as wrapper:
        with open("dexy.yaml", "w") as f:
            f.write(""".abc""")

        with open("root.abc", "w") as f:
            f.write("hello")

        with open("root.def", "w") as f:
            f.write("hello")

        os.makedirs("s1")
        os.makedirs("s2")

        with open("s1/s1.abc", "w") as f:
            f.write("hello")

        with open("s1/s1.def", "w") as f:
            f.write("hello")

        with open("s2/s2.abc", "w") as f:
            f.write("hello")

        with open("s2/s2.def", "w") as f:
            f.write("hello")

        with open(os.path.join('s1', 'dexy.yaml'), 'w') as f:
            f.write(""".def|dexy""")

        wrapper = Wrapper()
        wrapper.to_valid()
        wrapper.to_walked()
        wrapper.to_checked()
        wrapper.run()

        assert len(wrapper.nodes) == 6

        p = wrapper.nodes["pattern:*.abc"]
        c = wrapper.nodes["doc:s2/s2.abc"]
        assert c in p.children

def test_config_file():
    with tempdir():
        with open("dexy.conf", "w") as f:
            f.write("""{ "logfile" : "a.log" }""")

        wrapper = init_wrapper({'conf' : 'dexy.conf'})
        assert wrapper.log_file == "a.log"

def test_kwargs_override_config_file():
    with tempdir():
        with open("dexy.conf", "w") as f:
            f.write("""{ "logfile" : "a.log" }""")

        wrapper = init_wrapper({
            '__cli_options' : { 'logfile' : 'b.log' },
            'logfile' : "b.log",
            'conf' : 'dexy.conf'
            })
        assert wrapper.log_file == "b.log"

def test_wrapper_init():
    wrapper = Wrapper()
    assert wrapper.artifacts_dir == '.dexy'

YAML = """foo:
    - bar
    - baz

foob:
    - foobar

xyz:
    - abc
    - def
"""

def run_yaml_with_target(target):
    with wrap() as wrapper:
        wrapper.nodes = {}
        wrapper.roots = []
        wrapper.batch = dexy.batch.Batch(wrapper)
        wrapper.filemap = wrapper.map_files()

        ast = AbstractSyntaxTree(wrapper)
        parser = Yaml(wrapper, ast)
        parser.parse('.', YAML)
        ast.walk()

        wrapper.transition('walked')
        wrapper.to_checked()

        assert len(wrapper.roots) == 3
        assert len(wrapper.nodes) == 8

        wrapper.target = target
        wrapper.run()

        yield wrapper

def test_run_target_foo():
    for wrapper in run_yaml_with_target("foo"):
        assert wrapper.nodes['bundle:foo'].state == 'ran'
        assert wrapper.nodes['bundle:bar'].state == 'ran'
        assert wrapper.nodes['bundle:baz'].state == 'ran'
        assert wrapper.nodes['bundle:foob'].state == 'uncached'
        assert wrapper.nodes['bundle:foobar'].state == 'uncached'
        assert wrapper.nodes['bundle:xyz'].state == 'uncached'

def test_run_target_fo():
    for wrapper in run_yaml_with_target("fo"):
        # foo and children have been run
        assert wrapper.nodes['bundle:foo'].state == 'ran'
        assert wrapper.nodes['bundle:bar'].state == 'ran'
        assert wrapper.nodes['bundle:baz'].state == 'ran'

        # foob and children have been run
        assert wrapper.nodes['bundle:foob'].state == 'ran'
        assert wrapper.nodes['bundle:foobar'].state == 'ran'

def test_run_target_bar():
    for wrapper in run_yaml_with_target("bar"):
        assert wrapper.nodes['bundle:foo'].state == 'uncached'
        assert wrapper.nodes['bundle:bar'].state == 'ran'
        assert wrapper.nodes['bundle:baz'].state == 'uncached'
        assert wrapper.nodes['bundle:foob'].state == 'uncached'
        assert wrapper.nodes['bundle:foobar'].state == 'uncached'

def test_run_target_ba():
    for wrapper in run_yaml_with_target("ba"):
        assert wrapper.nodes['bundle:foo'].state == 'uncached'
        assert wrapper.nodes['bundle:bar'].state == 'ran'
        assert wrapper.nodes['bundle:baz'].state == 'ran'
        assert wrapper.nodes['bundle:foob'].state == 'uncached'
        assert wrapper.nodes['bundle:foobar'].state == 'uncached'

########NEW FILE########
__FILENAME__ = utils
from StringIO import StringIO
from dexy.data import Sectioned
from dexy.doc import Doc
from dexy.exceptions import InactivePlugin
from dexy.utils import char_diff
from dexy.utils import tempdir
from mock import MagicMock
from nose.exc import SkipTest
import os
import re
import sys

import dexy.load_plugins

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def make_wrapper():
    from dexy.wrapper import Wrapper
    return Wrapper(log_level = 'DEBUG', debug=True)

class wrap(tempdir):
    """
    Create a temporary directory and initialize a dexy wrapper.
    """
    def __enter__(self):
        self.make_temp_dir()
        wrapper = make_wrapper()
        wrapper.create_dexy_dirs()
        wrapper = make_wrapper()
        wrapper.to_valid()
        return wrapper

    def __exit__(self, type, value, traceback):
        self.remove_temp_dir()
        if isinstance(value, InactivePlugin):
            print value.message
            raise SkipTest
            return True # swallow InactivePlugin error

class runfilter(wrap):
    """
    Create a temporary directory, initialize a doc and a wrapper, and run the doc.
    """
    def __init__(self, filter_alias, doc_contents, ext=".txt", basename=None):
        self.filter_alias = filter_alias
        self.doc_contents = doc_contents
        self.ext = ext
        self.basename = basename

    def __enter__(self):
        self.make_temp_dir()

        def run_example(doc_key, doc_contents):
            wrapper = make_wrapper()

            if isinstance(doc_contents, basestring):
                data_class = 'generic'
            else:
                data_class = 'sectioned'

            doc = Doc(
                    doc_key,
                    wrapper,
                    [],
                    contents = doc_contents,
                    data_class = data_class
                    )
            wrapper.run_docs(doc)
            return doc

        try:
            wrapper = make_wrapper()
            wrapper.create_dexy_dirs()

            if self.basename:
                filename = "%s%s" % (self.basename, self.ext)
            else:
                filename = "example%s" % self.ext

            doc_key = "subdir/%s|%s" % (filename, self.filter_alias)

            doc = run_example(doc_key, self.doc_contents)

        except InactivePlugin:
            raise SkipTest

        return doc

def assert_output(filter_alias, doc_contents, expected_output, ext=".txt", basename=None):
    if not ext.startswith("."):
        raise Exception("ext arg to assert_in_output must start with dot")

    if isinstance(doc_contents, dict):
        raise Exception("doc contents can't be dict")

    with runfilter(filter_alias, doc_contents, ext=ext, basename=basename) as doc:
        actual_output_data = doc.output_data()
        if isinstance(actual_output_data, Sectioned):
            for section_name, expected_section_contents in expected_output.iteritems():
                try:
                    actual_section_contents = unicode(actual_output_data[section_name])
                    assert actual_section_contents == expected_section_contents
                except AssertionError:
                    print "Sections %s are not the same" % section_name
                    print char_diff(actual_section_contents, expected_section_contents)
        else:
            actual_output_data = unicode(doc.output_data())
            try:
                assert actual_output_data == expected_output
            except AssertionError:
                print char_diff(actual_output_data, expected_output)

def assert_output_matches(filter_alias, doc_contents, expected_regex, ext=".txt"):
    if not ext.startswith("."):
        raise Exception("ext arg to assert_in_output must start with dot")

    with runfilter(filter_alias, doc_contents, ext=ext) as doc:
        if expected_regex:
            assert re.match(expected_regex, unicode(doc.output_data()))
        else:
            raise Exception(unicode(doc.output_data()))

def assert_output_cached(filter_alias, doc_contents, ext=".txt", min_filesize=None):
    if not ext.startswith("."):
        raise Exception("ext arg to assert_output_cached must start with dot")

    with runfilter(filter_alias, doc_contents, ext=ext) as doc:
        if doc.wrapper.state == 'ran':
            assert doc.output_data().is_cached()
            if min_filesize:
                assert doc.output_data().filesize() > min_filesize
        elif doc.wrapper.state == 'error':
            if isinstance(doc.wrapper.error, InactivePlugin):
                raise SkipTest()
            else:
                raise doc.wrapper.error
        else:
            raise Exception("state is '%s'" % doc.wrapper.state)

def assert_in_output(filter_alias, doc_contents, expected_output, ext=".txt"):
    if not ext.startswith("."):
        raise Exception("ext arg to assert_in_output must start with dot")

    with runfilter(filter_alias, doc_contents, ext=ext) as doc:
        if expected_output:
            actual_output = unicode(doc.output_data())
            msg = "did not find expected '%s' in actual output '%s'"
            assert expected_output in actual_output, msg % (expected_output, actual_output)
        else:
            raise Exception(unicode(doc.output_data()))

class capture_stdout():
    def __enter__(self):
        self.old_stdout = sys.stdout
        self.my_stdout = StringIO()
        sys.stdout = self.my_stdout
        return self.my_stdout

    def __exit__(self, type, value, traceback):
        sys.stdout = self.old_stdout
        self.my_stdout.close()

class capture_stderr():
    def __enter__(self):
        self.old_stderr = sys.stderr
        self.my_stderr = StringIO()
        sys.stderr = self.my_stderr
        return self.my_stderr

    def __exit__(self, type, value, traceback):
        sys.stderr = self.old_stderr
        self.my_stderr.close()

class run_templating_plugin():
    def __init__(self, klass, mock_attrs=None):
        if not mock_attrs:
            mock_attrs = {}
        self.f = MagicMock(**mock_attrs)
        self.plugin = klass(self.f)

    def __enter__(self):
        env = self.plugin.run()
        assert isinstance(env, dict)
        return env

    def __exit__(self, type, value, traceback):
        pass

########NEW FILE########
